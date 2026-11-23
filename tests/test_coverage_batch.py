"""Offline batch regressions: synthetic model reports, dummy keys, no paid calls."""
import argparse
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import coverage_batch as b
import openai_worker as w
from test_probe_browser import inventory_fixture, report_fixture


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = {"schema_version": 1, "garak_python": sys.executable, "evidence_root": str(self.root / "evidence"),
                    "xdg_data_home": str(self.root / "data"), "targets": {
                        "local": {"provider": "ollama", "model": "synthetic:only", "endpoint": "http://127.0.0.1:11434"}}}
        self.inv = inventory_fixture()
        self.args = argparse.Namespace(action="batch", target=["local"], probe=None, completion_tokens=1500,
                                       request_cap=None, spending_alert=None, retry_failed=False)
        self.out = io.StringIO()
        self.enter_context = self.enterContext if hasattr(self, "enterContext") else None
        self.addCleanup(patch.stopall)
        patch("sys.stdout", self.out).start()
        patch.object(p, "installed_inventory", return_value=self.inv).start()
        patch.object(p, "estimate_cloud_workload", side_effect=lambda cfg, c: {
            "probe": c["spec"], "sampled_prompt_count": c["workload"]["expected_attempts"] or 32,
            "max_input_units_per_request": 250, "sample_sha256": "SYNTHETIC"}).start()
        patch.object(b.sys.stdin, "isatty", return_value=True).start()
        patch.object(p.openai_cost, "published_rates", return_value={"model": "gpt-5.6-sol", "input_usd_per_million": "4", "output_usd_per_million": "20", "source": "SYNTHETIC rates"}).start()

    def campaign(self, name="probes.encoding.InjectAscii85", target="local"):
        row = next(x for x in self.inv["probes"] if x["name"] == name)
        return p.probe_catalog.campaign_for(row, p.openai_profile.targets(self.cfg)[target], self.inv)

    def saved(self, name="probes.encoding.InjectAscii85", target="local", empty=False, missing=False):
        folder = p.new_folder(self.cfg, "scan")
        c = self.campaign(name, target)
        manifest = p.plan(self.cfg, target, c, folder)
        manifest.update(process_status="exited", exit_code=0, runner_run_id=folder.name)
        p.write_json(folder / "manifest.json", manifest)
        if not missing:
            count = c["workload"]["expected_attempts"] or 32
            rows = report_fixture(name, c["detector"], count)
            if empty:
                rows[2]["outputs"] = [None]
            p.write_jsonl(folder / "scan.report.jsonl", rows)
        summary = p.render_outputs(folder / "scan.report.jsonl", folder, manifest)
        p.checksums(folder)
        return {"folder": str(folder), "summary": summary, "manifest": manifest, "exit_code": 0}

    def test_all_inventory_rows_and_both_targets_are_retained(self):
        self.args.target = None
        d = b.make_plan(self.cfg, self.args)
        self.assertEqual(len(d["rows"]), len(self.inv["probes"]) * 2)
        self.assertEqual(len(d["plans"]), 28)
        excluded = [r for r in d["rows"] if not r["runner_enabled"]]
        self.assertTrue(all(r["requirements"] for r in excluded))
        self.assertTrue(all(r["evidence_state"] == "untested" for r in excluded))

    def test_scored_gaps_and_completed_are_credited_without_rescan(self):
        a = self.saved()
        z = self.saved("probes.encoding.InjectBase64", empty=True)
        before = {str(path): p.sha(path) for path in Path(self.cfg["evidence_root"]).rglob("*") if path.is_file()}
        d = b.make_plan(self.cfg, self.args)
        self.assertEqual(len(d["plans"]), 12)
        runs = [run for row in d["rows"] for run in row["runs"]]
        self.assertEqual({r["recorded_summary"]["execution_status"] for r in runs}, {"completed", "complete_with_gaps"})
        self.assertTrue(all(r["credited_live_evidence"] for r in runs))
        self.assertEqual(before, {str(path): p.sha(path) for path in Path(self.cfg["evidence_root"]).rglob("*") if path.is_file()})

    def test_other_model_evidence_does_not_skip_pair(self):
        result = self.saved()
        manifest = result["manifest"]
        manifest["target"]["model"] = "different:only"
        p.write_json(Path(result["folder"]) / "manifest.json", manifest)
        p.checksums(Path(result["folder"]))
        self.assertEqual(len(b.make_plan(self.cfg, self.args)["plans"]), 14)

    def test_failed_zero_attempt_run_requires_explicit_retry_option(self):
        self.saved(missing=True)
        self.assertEqual(len(b.make_plan(self.cfg, self.args)["plans"]), 13)
        self.args.retry_failed = True
        self.assertEqual(len(b.make_plan(self.cfg, self.args)["plans"]), 14)

    def test_changed_evidence_not_credited_and_visible_in_report(self):
        result = self.saved()
        path = Path(result["folder"]) / "scan.report.jsonl"
        with path.open("a") as f:
            f.write('{"entry_type":"extra"}\n')
        d = b.make_plan(self.cfg, self.args)
        r = next(row for row in d["rows"] if row["probe_id"] == "probes.encoding.InjectAscii85")
        self.assertEqual(r["evidence_state"], "recorded_failure_or_unverified_evidence")
        self.assertTrue(r["runs"][0]["integrity_warnings"])

    def test_cancel_starts_no_scan_or_key_entry(self):
        for choice in ("", "RUN ALL", "3"):
            with patch("builtins.input", return_value=choice), patch.object(p, "run_selected") as execute, patch.object(p.openai_profile, "read_session_key") as key:
                self.assertEqual(b.dispatch(self.args, self.cfg), 0)
                execute.assert_not_called(); key.assert_not_called()

    def test_nonterminal_requires_confirmation(self):
        with patch.object(b.sys.stdin, "isatty", return_value=False), patch.object(p, "run_selected") as execute:
            with self.assertRaisesRegex(ValueError, "interactive"):
                b.dispatch(self.args, self.cfg)
            execute.assert_not_called()

    def test_unknown_and_disabled_probe_selections_do_not_execute(self):
        for name in ("probes.unknown.X", "probes.unreviewed.Example00"):
            self.args.probe = [name]
            with self.assertRaises(ValueError):
                b.make_plan(self.cfg, self.args)

    def test_one_confirmation_runs_two_probes_with_existing_handoff_workflow(self):
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.goodside.ThreatenJSON"]
        def execute(cfg, target, campaign, **kwargs):
            self.assertFalse(kwargs["interactive"])
            self.assertTrue(kwargs["batch_id"])
            return self.saved(campaign["spec"], target, empty=campaign["spec"].endswith("Ascii85"))
        with patch("builtins.input", return_value="RUN") as confirm, patch.object(p, "run_selected", side_effect=execute) as run:
            self.assertEqual(b.dispatch(self.args, self.cfg), 0)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(confirm.call_count, 1)
        folders = list(Path(self.cfg["evidence_root"]).glob("*-scan-*"))
        self.assertEqual(len(folders), 2)
        for folder in folders:
            self.assertTrue((folder / "atlas_handoff.md").is_file())
        batch = next(Path(self.cfg["evidence_root"]).glob("*-batch-*"))
        d = p.read_json(batch / "batch.json")
        self.assertEqual([r["execution_status"] for r in d["results"]], ["complete_with_gaps", "completed"])
        self.assertTrue((batch / "probe-coverage.csv").is_file())
        self.assertEqual(len(b.make_plan(self.cfg, self.args)["plans"]), 0)

    def test_failed_auth_stops_batch_key_not_persisted(self):
        self.args.target = [p.openai_profile.NAME]
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.encoding.InjectBase64"]
        key = "dummy-never-persist-this-key-987654"
        def fail(cfg, target, campaign, **kwargs):
            self.assertEqual(kwargs["session_key"], key)
            result = self.saved(campaign["spec"], target, missing=True)
            folder = Path(result["folder"])
            p.write_json(folder / "openai-session.json", {"status": "failed", "error": "OpenAI returned HTTP 401"})
            p.checksums(folder)
            return result
        with patch("builtins.input", return_value="RUN"), patch.object(p.openai_profile, "read_session_key", return_value=key) as readkey, patch.object(p, "run_selected", side_effect=fail) as run:
            self.assertEqual(b.dispatch(self.args, self.cfg), 2)
            self.assertEqual(run.call_count, 1); readkey.assert_called_once()
        for path in Path(self.cfg["evidence_root"]).rglob("*"):
            if path.is_file():
                self.assertNotIn(key, path.read_text(encoding="utf-8-sig"))
        self.assertNotIn(key, self.out.getvalue())

    def test_missing_price_allows_run_review_and_request_count_includes_compatibility(self):
        self.args.target = [p.openai_profile.NAME]
        with patch.object(p.openai_cost, "published_rates", return_value=None):
            d = b.make_plan(self.cfg, self.args)
        b.show_plan(d)
        self.assertIn("Estimate unavailable", self.out.getvalue())
        self.assertTrue(all(x["campaign"]["workload"]["planned_http_requests"] == x["constructed_prompts"] + 1 for x in d["plans"]))

    def test_local_timeout_and_nonzero_exit_stop_before_second_probe(self):
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.encoding.InjectBase64"]
        self.args.retry_failed = True
        for status, code in (("timed_out", -15), ("exited", 1), ("exited", None)):
            with self.subTest(status=status, code=code):
                self.cfg["evidence_root"] = str(self.root / (status + str(code)))
                def execute(cfg, target, campaign, **kwargs):
                    result = self.saved(campaign["spec"], target)
                    result["manifest"].update(process_status=status, exit_code=code)
                    folder = Path(result["folder"])
                    p.write_json(folder / "manifest.json", result["manifest"])
                    result["summary"] = p.render_outputs(folder / "scan.report.jsonl", folder, result["manifest"])
                    p.checksums(folder)
                    return result
                with patch("builtins.input", return_value="RUN"), patch.object(p, "run_selected", side_effect=execute) as run:
                    self.assertEqual(b.dispatch(self.args, self.cfg), 2)
                    self.assertEqual(run.call_count, 1)
                batch = next(Path(self.cfg["evidence_root"]).glob("*-batch-*"))
                self.assertEqual(p.read_json(batch / "batch.json")["status"], "stopped")

    def test_new_run_reconciliation_warning_stops_before_second_probe(self):
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.encoding.InjectBase64"]
        def execute(cfg, target, campaign, **kwargs):
            result = self.saved(campaign["spec"], target)
            folder = Path(result["folder"])
            with (folder / "scan.report.jsonl").open("a", encoding="utf-8") as f:
                f.write('{"entry_type":"unexpected_change"}\n')
            return result
        with patch("builtins.input", return_value="RUN"), patch.object(p, "run_selected", side_effect=execute) as run:
            self.assertEqual(b.dispatch(self.args, self.cfg), 2)
            self.assertEqual(run.call_count, 1)
        batch = next(Path(self.cfg["evidence_root"]).glob("*-batch-*"))
        self.assertIn("reconciliation", p.read_json(batch / "batch.json")["stop_reason"])

    def test_missing_native_completion_stops_before_second_probe(self):
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.encoding.InjectBase64"]
        with patch("builtins.input", return_value="RUN"), patch.object(p, "run_selected", side_effect=lambda cfg, target, campaign, **kw: self.saved(campaign["spec"], target, missing=True)) as run:
            self.assertEqual(b.dispatch(self.args, self.cfg), 2)
            self.assertEqual(run.call_count, 1)

    def test_explicit_token_limit_used_without_changing_source_configuration(self):
        self.args.target = [p.openai_profile.NAME]
        self.args.completion_tokens = 2300
        d = b.make_plan(self.cfg, self.args)
        self.assertTrue(all(x["campaign"]["max_completion_tokens"] == 2300 for x in d["plans"]))
        self.assertEqual(p.openai_profile.COMPLETION_LIMIT, 1500)

    def test_saved_transport_reports_finish_reason_and_usage_without_transcripts(self):
        folder = self.root / "transport"; folder.mkdir()
        p.write_jsonl(folder / "openai-transport.jsonl", [{"entry_type": "response", "stage": "scan", "sequence": 3, "http_status": 200,
            "body": {"choices": [{"finish_reason": "length", "message": {"content": "", "refusal": None}}],
                     "usage": {"completion_tokens": 1500, "completion_tokens_details": {"reasoning_tokens": 1500}}}}])
        d = b.transport_diagnostics(folder)
        self.assertEqual(d["finish_reasons"], {"length": 1})
        self.assertEqual(d["scan_response_issues"][0]["reasoning_tokens"], 1500)
        self.assertNotIn("content", json.dumps(d))

    def test_coverage_only_never_constructs_workload_or_generates(self):
        self.args.action = "coverage"
        with patch.object(p, "run_selected") as run, patch.object(p, "estimate_cloud_workload") as estimate:
            self.assertEqual(b.dispatch(self.args, self.cfg), 0)
            run.assert_not_called(); estimate.assert_not_called()

    def test_interrupt_creates_receipt_and_starts_no_second_run(self):
        self.args.probe = ["probes.encoding.InjectAscii85", "probes.encoding.InjectBase64"]
        with patch("builtins.input", return_value="RUN"), patch.object(p, "run_selected", side_effect=KeyboardInterrupt) as run:
            self.assertEqual(b.dispatch(self.args, self.cfg), 2)
            self.assertEqual(run.call_count, 1)
        batch = next(Path(self.cfg["evidence_root"]).glob("*-batch-*"))
        self.assertEqual(p.read_json(batch / "batch.json")["status"], "interrupted")


class PipeCredentialTests(unittest.TestCase):
    def test_pipe_accepts_key_without_echo(self):
        self.assertEqual(w.read_pipe_key(io.StringIO('"dummy-secret"\n')), "dummy-secret")

    def test_invalid_pipe_values_are_not_disclosed(self):
        for value in ('dummy-secret\n', '"dummy secret"\n', '{}\n', '""\n', '"dummy-secret"'):
            with self.assertRaises(ValueError) as ctx:
                w.read_pipe_key(io.StringIO(value))
            self.assertNotIn(value, str(ctx.exception))

    def test_actual_subprocess_stdin_pipe_dummy_key_and_no_network(self):
        source = "import openai_worker as w; w.run=lambda args,key: 0 if key=='dummy-subprocess-secret' and args==['--example'] else 7; raise SystemExit(w.main(['--key-stdin','--example']))"
        result = subprocess.run([sys.executable, "-c", source], input='"dummy-subprocess-secret"\n',
                                text=True, capture_output=True, cwd=p.ROOT, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("dummy-subprocess-secret", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
