"""Offline menu/catalog/workload tests. No actual model or desktop is used."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p


def transport_fixture(folder, count):
    """Synthetic companion records for fake-scanner UI tests; no HTTP occurs."""
    p.write_json(folder / "ollama-session.json", {"status": "scan_returned", "http_requests": count})
    rows = []
    for seq in range(1, count + 1):
        rows.extend([{"entry_type": "request", "sequence": seq, "stage": "scan", "body": {"synthetic": True}},
                     {"entry_type": "response", "sequence": seq, "stage": "scan", "http_status": 200,
                      "body": {"message": {"content": "SYNTHETIC UI fixture"}, "done": True, "done_reason": "stop"}}])
    p.write_jsonl(folder / "ollama-transport.jsonl", rows)
import probe_catalog as c


def inventory_fixture():
    rules = c.policy()
    rows, hashes = [], dict(rules["common_source_checks"])
    for checks in rules.get("provider_source_checks", {}).values():
        hashes.update(checks)
    for name, rule in rules["probes"].items():
        hashes.update(rule["source_checks"])
        rows.append({"name": name, "active": name != "probes.goodside.Davidjl",
                     "metadata": {"description": "SYNTHETIC description for " + name,
                                  "goal": "SYNTHETIC test objective", "modality": {"in": ["text"]},
                                  "primary_detector": rule["detector"], "extra_dependency_names": []}})
    for i in range(45):
        rows.append({"name": f"probes.unreviewed.Example{i:02}", "active": bool(i % 2),
                     "metadata": {"description": f"SYNTHETIC unreviewed probe {i}", "modality": {"in": ["text"]}}})
    return {"garak_version": "0.17.0", "probes": rows, "source_sha256": hashes,
            "inventory_method": "SYNTHETIC fixture", "generation_requests": 0}


def report_fixture(probe, detector, count, empty=False):
    rows = [{"entry_type": "start_run setup", "run.eval_threshold": 0.5, "run.generations": 1},
            {"entry_type": "init", "garak_version": "0.17.0", "run": "SYNTHETIC-BROWSER-RUN"}]
    for i in range(count):
        rows.append({"entry_type": "attempt", "uuid": f"SYNTHETIC-{i}", "status": 2,
                     "probe_classname": probe.removeprefix("probes."), "prompt": f"SYNTHETIC input {i}",
                     "outputs": [None if empty else {"text": f"SYNTHETIC response {i}"}],
                     "detector_results": {detector: [None if empty else 0.0]}})
    rows.extend([{"entry_type": "eval", "probe": probe.removeprefix("probes."), "detector": detector,
                  "passed": 0 if empty else count, "fails": 0, "total_evaluated": 0 if empty else count,
                  "nones": count if empty else 0},
                 {"entry_type": "completion", "run": "SYNTHETIC-BROWSER-RUN"}])
    return rows


class ProbeBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cfg = {"schema_version": 1, "garak_python": sys.executable,
                    "evidence_root": str(self.root / "evidence"), "xdg_data_home": str(self.root / "data"),
                    "targets": {"local": {"provider": "ollama", "model": "synthetic:only", "endpoint": "http://127.0.0.1:11434"}}}
        self.inventory = inventory_fixture()
        self.target = self.cfg["targets"]["local"]

    def tearDown(self):
        self.temp.cleanup()

    def row(self, name):
        return next(r for r in self.inventory["probes"] if r["name"] == name)

    def campaign(self, name="probes.goodside.WhoIsRiley"):
        return c.campaign_for(self.row(name), self.target, self.inventory)

    def test_full_registry_includes_inactive_and_unreviewed_entries(self):
        pairs = [(r["name"], r["active"]) for r in self.inventory["probes"]]
        fake = SimpleNamespace(enumerate_plugins=MagicMock(return_value=pairs),
                               plugin_info=MagicMock(side_effect=lambda name: self.row(name)["metadata"]),
                               load_plugin=MagicMock(side_effect=AssertionError("No plugin construction")))
        dist = SimpleNamespace(locate_file=lambda name: self.root / "absent")
        with patch.dict(sys.modules, {"garak": SimpleNamespace(_plugins=fake)}), \
             patch.object(c.importlib.metadata, "version", return_value="0.17.0"), \
             patch.object(c.importlib.metadata, "distribution", return_value=dist), \
             patch.object(c.sys, "addaudithook") as hook:
            result = c.collect()
        self.assertEqual(result["probes"], self.inventory["probes"])
        fake.enumerate_plugins.assert_called_once_with("probes")
        fake.load_plugin.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            hook.call_args.args[0]("socket.connect", ())

    def test_inventory_uses_configured_python_and_removes_temporary_cache(self):
        self.cfg["garak_python"] = str(self.root / "configured-garak-python.exe")
        result = subprocess.CompletedProcess([], 0, json.dumps(self.inventory), "")
        with patch.object(p.subprocess, "run", return_value=result) as run:
            actual = p.installed_inventory(self.cfg)
        self.assertEqual(actual, self.inventory)
        self.assertEqual(run.call_args.args[0], [self.cfg["garak_python"], str(p.ROOT / "probe_catalog.py"), "--collect"])
        kwargs = run.call_args.kwargs
        self.assertFalse(kwargs["shell"])
        self.assertNotIn("HTTP_PROXY", kwargs["env"])
        self.assertFalse(Path(kwargs["env"]["XDG_CACHE_HOME"]).exists())

    def test_bad_inventory_or_child_failure_is_not_an_empty_catalog(self):
        for result in (subprocess.CompletedProcess([], 2, "", "synthetic inventory failure"),
                       subprocess.CompletedProcess([], 0, "not JSON", "")):
            with self.subTest(result=result), patch.object(p.subprocess, "run", return_value=result):
                with self.assertRaises(p.PlaybookError):
                    p.installed_inventory(self.cfg)

    def test_twenty_per_page_and_all_rows_reachable_without_duplicates(self):
        seen = []
        for page in range(3):
            rows, total, actual, pages = c.page_rows(self.inventory["probes"], page=page)
            self.assertEqual((total, actual, pages), (59, page, 3))
            self.assertEqual(len(rows), 20 if page < 2 else 19)
            seen.extend(r["name"] for r in rows)
        self.assertEqual(seen, sorted(r["name"] for r in self.inventory["probes"]))
        self.assertEqual(c.page_rows(self.inventory["probes"], page=-1)[2], 0)
        self.assertEqual(c.page_rows(self.inventory["probes"], page=99)[2], 2)

    def test_search_is_case_insensitive_by_family_or_class(self):
        rows, total, page, pages = c.page_rows(self.inventory["probes"], "GOODSIDE")
        self.assertEqual(total, 4)
        self.assertTrue(all("goodside" in r["name"] for r in rows))
        self.assertEqual(c.page_rows(self.inventory["probes"], "WhoIsRiley")[1], 1)
        self.assertEqual(c.page_rows(self.inventory["probes"], "absent")[0], [])

    def test_supported_inactive_probe_is_selectable(self):
        row = self.row("probes.goodside.Davidjl")
        self.assertFalse(row["active"])
        self.assertTrue(c.assess(row, self.target, self.inventory)[0])
        self.assertEqual(self.campaign(row["name"])["workload"]["expected_attempts"], 4)

    def test_base_detector_uses_exact_primary_via_auto_without_extended_detectors(self):
        for name in ("probes.goodside.Tag", "probes.lmrc.Deadnaming"):
            campaign = self.campaign(name)
            plan = p.plan(self.cfg, "local", campaign)
            argv = plan["command_argv"]
            self.assertEqual(argv[argv.index("--detectors") + 1], "auto")
            self.assertEqual(campaign["detector"], "base.TriggerListDetector")
            self.assertFalse(plan["resolved_garak_config"]["plugins"]["extended_detectors"])
            self.assertIn("garak/harnesses/probewise.py", campaign["source_checks"])

    def test_preflight_rechecks_selected_probe_source_before_target_access(self):
        campaign = self.campaign()
        inspected = {"packages": {"garak": "0.17.0", "ollama": "synthetic"},
                     "source_sha256": dict(campaign["source_checks"])}
        inspected["source_sha256"]["garak/probes/goodside.py"] = "CHANGED_AFTER_BROWSING"
        result = subprocess.CompletedProcess([], 0, json.dumps(inspected), "")
        folder = self.root / "preflight"
        folder.mkdir()
        with patch.object(p.subprocess, "run", return_value=result), \
             patch.object(p, "get_api", side_effect=AssertionError("No target access")):
            with self.assertRaisesRegex(p.PlaybookError, "differs"):
                p.preflight(self.cfg, "local", campaign, folder)
        self.assertIn("garak/probes/goodside.py", p.read_json(folder / "source-differences.json"))

    def test_unavailable_reasons_cover_requirements_version_and_source_changes(self):
        row = copy.deepcopy(self.row("probes.unreviewed.Example00"))
        self.assertIn("not been validated", c.assess(row, self.target, self.inventory)[1])
        row["metadata"]["extra_dependency_names"] = ["synthetic_extra"]
        self.assertIn("synthetic_extra", c.assess(row, self.target, self.inventory)[1])
        row["metadata"]["modality"] = {"in": ["image"]}
        self.assertIn("non-text", c.assess(row, self.target, self.inventory)[1])
        row = self.row("probes.goodside.Tag")
        self.assertIn("Ollama", c.assess(row, {"provider": "unconfigured"}, self.inventory)[1])
        changed = copy.deepcopy(self.inventory)
        changed["garak_version"] = "other"
        self.assertIn("version differs", c.assess(row, self.target, changed)[1])
        changed = copy.deepcopy(self.inventory)
        changed["source_sha256"]["garak/probes/goodside.py"] = "changed"
        self.assertIn("source differs", c.assess(row, self.target, changed)[1])
        with self.assertRaises(ValueError):
            c.campaign_for(row, self.target, changed)
        row = copy.deepcopy(row)
        row["metadata"]["primary_detector"] = "different.Detector"
        self.assertIn("primary detector differs", c.assess(row, self.target, self.inventory)[1])

    def test_browser_navigation_search_clear_and_back(self):
        with patch.object(p, "installed_inventory", return_value=self.inventory), \
             patch("builtins.input", side_effect=["n", "p", "s", "GOODSide", "a", "b"]), \
             patch("sys.stdout", new=io.StringIO()) as out:
            self.assertIsNone(p.browse_probes(self.cfg, "local"))
        text = out.getvalue()
        self.assertIn("Available probes: 14 | Matches: 14 | Page 1/1", text)
        self.assertIn("Matches: 4 | Page 1/1", text)
        self.assertIn("SYNTHETIC description", text)
        self.assertNotIn("UNAVAILABLE", text)
        self.assertNotIn("probes.unreviewed.", text)
        self.assertIn("SUPPORTED", text)

    def test_unavailable_probes_are_absent_from_search_and_page_counts(self):
        with patch.object(p, "installed_inventory", return_value=self.inventory), \
             patch("builtins.input", side_effect=["s", "unreviewed.Example00", "1", "b"]), \
             patch("sys.stdout", new=io.StringIO()) as out, \
             patch.object(p, "execute", side_effect=AssertionError("No scan")):
            self.assertIsNone(p.browse_probes(self.cfg, "local"))
        self.assertIn("Available probes: 14 | Matches: 0 | Page 1/1", out.getvalue())
        self.assertIn("Invalid selection; no scan started.", out.getvalue())
        self.assertNotIn("probes.unreviewed.Example00", out.getvalue())
        self.assertNotIn("UNAVAILABLE", out.getvalue())

    def test_exit_back_and_interrupt_start_no_scan(self):
        for choices in ([""], ["1", "3"], ["1", "1", "b", "3"], ["1", "2", "b", "3"],
                        ["1", "2", "s", "missing", "1", "b", "3"], [KeyboardInterrupt()]):
            with self.subTest(choices=choices), patch.object(p, "installed_inventory", return_value=self.inventory), \
                 patch("builtins.input", side_effect=choices), patch("sys.stdout", new=io.StringIO()), \
                 patch.object(p, "execute", side_effect=AssertionError("No scan")):
                self.assertEqual(p.menu(self.cfg), 0)

    def test_existing_campaigns_remain_available(self):
        for index, name in (("1", "base64-32"), ("2", "dan-wild-32")):
            with patch("builtins.input", side_effect=["1", "1", index]), \
                 patch("sys.stdout", new=io.StringIO()), patch.object(p, "execute", return_value=0) as execute:
                self.assertEqual(p.menu(self.cfg), 0)
            execute.assert_called_once_with(dict(self.cfg, targets=p.openai_profile.targets(self.cfg)), "local", name)

    def test_cancel_at_review_creates_no_run_and_does_not_launch_scanner(self):
        for confirmation in ("", "no", "run", "yes", "1", "RUN now", KeyboardInterrupt(), EOFError()):
            choices = ["1", "2", "s", "WhoIsRiley", "1", confirmation]
            with self.subTest(confirmation=confirmation), patch.object(p, "installed_inventory", return_value=self.inventory), \
                 patch("builtins.input", side_effect=choices), patch("sys.stdin.isatty", return_value=True), \
                 patch("sys.stdout", new=io.StringIO()) as out, \
                 patch.object(p, "preflight", side_effect=AssertionError("No preflight")), \
                 patch.object(p.subprocess, "Popen", side_effect=AssertionError("No scan")):
                self.assertEqual(p.menu(self.cfg), 0)
            text = out.getvalue()
            for expected in ("synthetic:only", "probes.goodside.WhoIsRiley", "goodside.RileyIsnt", "Expected attempts: 6",
                             "Temperature: 0.0", "Seed: 42", "256 tokens", "1800 seconds", "Extra dependencies", "API use"):
                self.assertIn(expected, text)
            self.assertFalse(Path(self.cfg["evidence_root"]).exists())

    def test_review_back_preserves_search_page_and_runs_only_second_selection(self):
        # Twenty matching rows precede the four supported Goodside probes.
        # This makes resetting either the search or page observable.
        rules = copy.deepcopy(c.policy())
        for i in range(20):
            rules["probes"][f"probes.goodside.AAA{i:02}"] = copy.deepcopy(rules["probes"]["probes.goodside.Davidjl"])
            self.inventory["probes"].append({
                "name": f"probes.goodside.AAA{i:02}", "active": True,
                "metadata": {"description": "SYNTHETIC pagination row", "modality": {"in": ["text"]}, "primary_detector": "goodside.Glitch"}})
        choices = iter(["1", "2", "s", "goodside", "n", "1", "B", "4", "RUN", "3"])
        review_prompts, folders = [], []

        def choose(prompt):
            answer = next(choices)
            if answer in ("B", "RUN"):
                review_prompts.append(prompt)
                self.assertIn("B: Back", prompt)
            if answer == "4":
                # Back must not create a run, preflight, launch, or restart menus.
                preflight.assert_not_called()
                launch.assert_not_called()
                self.assertFalse(Path(self.cfg["evidence_root"]).exists())
                redisplay = out.getvalue().split("Returning to the same probe list; no scan started.", 1)[1]
                self.assertIn("Matches: 24 | Page 2/2", redisplay)
                self.assertIn("Search: goodside", redisplay)
                self.assertIn("[1] probes.goodside.Davidjl", redisplay)
                self.assertIn("[4] probes.goodside.WhoIsRiley", redisplay)
                self.assertNotIn("Target/model profile", redisplay)
                self.assertNotIn("[1] Existing campaigns", redisplay)
            return answer

        def scanner(argv, **kwargs):
            self.assertEqual(len(review_prompts), 2)
            self.assertEqual(argv[argv.index("--spec") + 1], "probes.goodside.WhoIsRiley")
            self.assertEqual(argv[argv.index("--detectors") + 1], "goodside.RileyIsnt")
            folder = Path(kwargs["cwd"])
            folders.append(folder)
            p.write_jsonl(folder / "scan.report.jsonl",
                          report_fixture("probes.goodside.WhoIsRiley", "goodside.RileyIsnt", 6))
            transport_fixture(folder, 6)
            child = MagicMock(returncode=0, stdout=io.BytesIO(b"SYNTHETIC scanner\n"))
            child.poll.return_value = child.wait.return_value = 0
            return child

        with patch.object(c, "policy", return_value=rules), \
             patch.object(p, "installed_inventory", return_value=self.inventory) as inventory, \
             patch("builtins.input", side_effect=choose), patch("sys.stdin.isatty", return_value=True), \
             patch("sys.stdout", new=io.StringIO()) as out, \
             patch.object(p, "preflight", return_value={"status": "passed"}) as preflight, \
             patch.object(p.subprocess, "Popen", side_effect=scanner) as launch:
            self.assertEqual(p.menu(self.cfg), 0)
        inventory.assert_called_once_with(dict(self.cfg, targets=p.openai_profile.targets(self.cfg)))
        preflight.assert_called_once()
        launch.assert_called_once()
        text = out.getvalue()
        self.assertEqual(text.count("Target/model profile"), 1)
        self.assertEqual(text.count("[1] Existing campaigns"), 1)
        self.assertEqual(text.count("Matches: 24 | Page 2/2"), 2)
        folder = folders[0]
        self.assertEqual(list(Path(self.cfg["evidence_root"]).iterdir()), [folder])
        self.assertEqual(p.read_json(folder / "manifest.json")["campaign_profile"],
                         "installed:probes.goodside.WhoIsRiley")
        summary = p.read_json(folder / "summary.json")
        self.assertEqual((summary["execution_status"], summary["attempts"]), ("completed", 6))
        self.assertIn("evaluated responses: 6; detector flags: 0", (folder / "atlas_handoff.md").read_text())

    def test_new_probe_flows_through_menu_execution_evidence_and_handoff(self):
        campaign = self.campaign()
        expected_rows = report_fixture(campaign["spec"], campaign["detector"], 6)
        folders = []
        def scanner(argv, **kwargs):
            folder = Path(kwargs["cwd"])
            folders.append(folder)
            self.assertEqual(argv[argv.index("--spec") + 1], "probes.goodside.WhoIsRiley")
            self.assertEqual(argv[argv.index("--detectors") + 1], "goodside.RileyIsnt")
            p.write_jsonl(folder / "scan.report.jsonl", expected_rows)
            transport_fixture(folder, 6)
            child = MagicMock(returncode=0, stdout=io.BytesIO(b"SYNTHETIC scanner\n"))
            child.poll.return_value = child.wait.return_value = 0
            return child
        with patch.object(p, "installed_inventory", return_value=self.inventory), \
             patch("builtins.input", side_effect=["1", "2", "s", "WhoIsRiley", "1", "RUN", "3"]), \
             patch("sys.stdin.isatty", return_value=True), patch("sys.stdout", new=io.StringIO()) as out, \
             patch.object(p, "preflight", return_value={"status": "passed"}), \
             patch.object(p.subprocess, "Popen", side_effect=scanner) as launch:
            self.assertEqual(p.menu(self.cfg), 0)
        launch.assert_called_once()
        folder = folders[0]
        saved = p.read_json(folder / "manifest.json")
        self.assertEqual(saved["campaign"], campaign)
        self.assertEqual(saved["campaign_profile"], "installed:probes.goodside.WhoIsRiley")
        self.assertEqual(saved["resolved_garak_config"]["run"]["soft_probe_prompt_cap"], 32)
        summary = p.read_json(folder / "summary.json")
        self.assertEqual((summary["execution_status"], summary["attempts"]), ("completed", 6))
        self.assertEqual(summary["coverage_gaps"], [])
        text = (folder / "atlas_handoff.md").read_text()
        self.assertIn("evaluated responses: 6; detector flags: 0", text)
        self.assertIn("goodside.WhoIsRiley", text)
        self.assertIn("Attack success: unverified", text)
        self.assertEqual(text.count("- Attempt "), 5)
        self.assertIn("[2] Open ATLAS prompt in Notepad", out.getvalue())
        before = (folder / "scan.report.jsonl").read_bytes()
        with patch.object(p.subprocess, "Popen", side_effect=AssertionError("No scan")):
            p.regenerate_handoff(folder)
        self.assertEqual((folder / "atlas_handoff.md").read_text(), text)
        self.assertEqual((folder / "scan.report.jsonl").read_bytes(), before)

    def test_cap_is_upper_limit_not_expected_count(self):
        campaign = self.campaign("probes.encoding.InjectBase32")
        self.assertIsNone(campaign["workload"]["expected_attempts"])
        report = self.root / "report.jsonl"
        p.write_jsonl(report, report_fixture(campaign["spec"], campaign["detector"], 5))
        summary, _ = p.analyze(report, {"campaign": campaign, "process_status": "exited", "exit_code": 0})
        self.assertEqual(summary["execution_status"], "completed")
        self.assertEqual(summary["attempts"], 5)

    def test_cap_exceeded_and_fixed_count_shortfall_are_gaps(self):
        for campaign, count, message in ((self.campaign("probes.encoding.InjectBase32"), 33, "limit is 32"),
                                         (self.campaign(), 5, "planned 6")):
            report = self.root / "report.jsonl"
            p.write_jsonl(report, report_fixture(campaign["spec"], campaign["detector"], count))
            summary, _ = p.analyze(report, {"campaign": campaign, "process_status": "exited", "exit_code": 0})
            self.assertEqual(summary["execution_status"], "complete_with_gaps")
            self.assertTrue(any(message in gap for gap in summary["coverage_gaps"]))

    def test_missing_outputs_remain_gaps_for_new_probe(self):
        campaign = self.campaign()
        report = self.root / "report.jsonl"
        p.write_jsonl(report, report_fixture(campaign["spec"], campaign["detector"], 6, empty=True))
        summary, _ = p.analyze(report, {"campaign": campaign, "process_status": "exited", "exit_code": 0})
        self.assertEqual(summary["execution_status"], "complete_with_gaps")
        self.assertEqual(summary["detectors"][0]["unscorable"], 6)

    def test_unknown_legacy_probe_does_not_treat_cap_as_expected(self):
        report = self.root / "report.jsonl"
        p.write_jsonl(report, report_fixture("probes.goodside.WhoIsRiley", "goodside.RileyIsnt", 6))
        summary, _ = p.analyze(report, {"campaign": {"spec": "probes.goodside.WhoIsRiley", "prompt_cap": 32},
                                        "process_status": "exited", "exit_code": 0})
        self.assertEqual(summary["execution_status"], "completed")


if __name__ == "__main__":
    unittest.main()
