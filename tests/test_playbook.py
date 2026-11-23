"""Synthetic fixtures exercise accounting and orchestration. They are not LLM scan results."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p


def fixture(outputs=None, scores=None):
    outputs = [{"text": "normal answer"}, {"text": "Quoted TRIGGER while refusing."}] if outputs is None else outputs
    scores = [0.0, 1.0] if scores is None else scores
    attempt = {"entry_type": "attempt", "uuid": "synthetic-attempt", "status": 2,
               "probe_classname": "encoding.InjectBase64", "prompt": {"turns": [{"role": "user", "content": {"text": "SYNTHETIC TEST INPUT"}}]},
               "outputs": outputs, "detector_results": {"encoding.DecodeMatch": scores},
               "conversations": [], "notes": {"triggers": ["TRIGGER"]}}
    values = [x for x in scores if p.score_value(x) is not None]
    ev = {"entry_type": "eval", "probe": "encoding.InjectBase64", "detector": "encoding.DecodeMatch",
          "passed": sum(x < 0.5 for x in values), "fails": sum(x >= 0.5 for x in values),
          "total_evaluated": len(values), "nones": len(scores) - len(values)}
    return [{"entry_type": "start_run setup", "run.eval_threshold": 0.5, "run.generations": len(outputs) or 1},
            {"entry_type": "init", "garak_version": "0.17.0", "run": "synthetic-run"},
            attempt, ev, {"entry_type": "completion", "run": "synthetic-run"}]


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = self.root / "native.report.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def analyze(self, rows, manifest=None):
        self.report.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
        if manifest is None:
            manifest = {"process_status": "exited", "exit_code": 0}
        return p.analyze(self.report, manifest)

    def test_completed_counts_and_unreviewed_false_positive_candidate(self):
        s, obs = self.analyze(fixture())
        self.assertEqual(s["execution_status"], "completed")
        self.assertEqual(s["valid_response_count"], 2)
        self.assertEqual(s["flagged_response_count"], 1)
        self.assertEqual(obs[1]["attack_success"], "not_assessed")
        self.assertEqual(obs[1]["review_status"], "unreviewed")
        self.assertIn("Quoted", obs[1]["output"]["text"])

    def test_deduplicates_attempt_lifecycle(self):
        rows = fixture()
        earlier = copy.deepcopy(rows[2]); earlier["status"] = 1; earlier["detector_results"] = {}
        rows.insert(2, earlier)
        s, obs = self.analyze(rows)
        self.assertEqual(s["attempts"], 1)
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs[0]["evidence"]["line"], 4)

    def test_no_double_count_across_detectors(self):
        rows = fixture()
        rows[2]["detector_results"]["other.Detector"] = [0.0, 1.0]
        ev = copy.deepcopy(rows[3]); ev["detector"] = "other.Detector"; rows.insert(4, ev)
        s, _ = self.analyze(rows)
        self.assertEqual(s["flagged_response_count"], 1)
        self.assertEqual(s["valid_response_count"], 2)

    def test_null_score_and_null_output_are_gaps(self):
        s, obs = self.analyze(fixture([None], [None]))
        self.assertEqual(s["execution_status"], "complete_with_gaps")
        self.assertEqual(s["detectors"][0]["not_flagged"], 0)
        self.assertEqual(s["detectors"][0]["unscorable"], 1)

    def test_empty_output_not_pass_even_if_detector_zero(self):
        s, _ = self.analyze(fixture([{"text": "  "}], [0.0]))
        self.assertEqual(s["detectors"][0]["not_flagged"], 0)
        self.assertTrue(any("totals differ" in x for x in s["coverage_gaps"]))

    def test_missing_completion(self):
        s, _ = self.analyze(fixture()[:-1])
        self.assertEqual(s["execution_status"], "incomplete")

    def test_missing_report(self):
        s, _ = p.analyze(self.report)
        self.assertEqual(s["execution_status"], "incomplete")

    def test_truncated_json(self):
        self.analyze(fixture())
        with self.report.open("a") as f: f.write('{"unfinished":')
        s, _ = p.analyze(self.report)
        self.assertTrue(any("Invalid JSON" in x for x in s["coverage_gaps"]))

    def test_nonzero_exit_and_timeout(self):
        s, _ = self.analyze(fixture(), {"exit_code": 1, "process_status": "timed_out"})
        self.assertEqual(s["execution_status"], "incomplete")

    def test_timeout_cannot_be_completed_even_with_zero_exit(self):
        s, _ = self.analyze(fixture(), {"exit_code": 0, "process_status": "timed_out"})
        self.assertEqual(s["execution_status"], "incomplete")

    def test_other_unsuccessful_outcomes_cannot_be_completed(self):
        for status, code in [("interrupted", 0), ("failed", 0), ("running", None), ("preflight", None), ("exited", 1)]:
            with self.subTest(status=status, exit_code=code):
                s, _ = self.analyze(fixture(), {"exit_code": code, "process_status": status})
                self.assertEqual(s["execution_status"], "incomplete")

    def test_report_only_cannot_claim_process_success(self):
        s, _ = self.analyze(fixture(), {})
        self.assertEqual(s["execution_status"], "process_outcome_unknown")
        self.assertTrue(s["native_completion_matches_run"])

    def test_ambiguous_completion_records_are_incomplete(self):
        rows = fixture(); rows.append(copy.deepcopy(rows[-1]))
        s, _ = self.analyze(rows)
        self.assertEqual(s["execution_status"], "incomplete")

    def test_zero_attempts_never_clean(self):
        rows = fixture(); del rows[2:4]
        s, _ = self.analyze(rows)
        self.assertNotEqual(s["execution_status"], "completed")

    def test_nan_score_not_pass(self):
        s, _ = self.analyze(fixture([{"text": "valid"}], [float("nan")]))
        self.assertEqual(s["detectors"][0]["evaluated"], 0)

    def test_score_output_length_mismatch(self):
        s, _ = self.analyze(fixture(scores=[0.0]))
        self.assertTrue(any("count mismatch" in x for x in s["coverage_gaps"]))

    def test_threshold_inclusive(self):
        s, _ = self.analyze(fixture([{"text": "candidate"}], [0.5]))
        self.assertEqual(s["flagged_response_count"], 1)

    def test_unknown_threshold_does_not_guess(self):
        rows = fixture(); del rows[0]["run.eval_threshold"]
        s, _ = self.analyze(rows)
        self.assertEqual(s["detectors"][0]["evaluated"], 0)

    def test_native_omitted_float_uses_recorded_config_not_default(self):
        rows = fixture(); del rows[0]["run.eval_threshold"]
        s, _ = self.analyze(rows, {"process_status": "exited", "exit_code": 0, "resolved_garak_config": {"run": {"eval_threshold": 0.5}}})
        self.assertEqual(s["execution_status"], "completed")
        self.assertEqual(s["evaluation_threshold_source"], "recorded_run_configuration")

    def test_conflicting_final_snapshots_reported(self):
        rows = fixture()
        other = copy.deepcopy(rows[2]); other["outputs"][0]["text"] = "different"
        rows.insert(3, other)
        s, _ = self.analyze(rows)
        self.assertTrue(any("Conflicting" in x for x in s["coverage_gaps"]))

    def test_missing_prompt_is_evidence_gap(self):
        rows = fixture(); del rows[2]["prompt"]
        s, _ = self.analyze(rows)
        self.assertTrue(any("prompt evidence" in x for x in s["coverage_gaps"]))

    def test_unknown_report_version(self):
        rows = fixture(); rows[1]["garak_version"] = "unknown"
        s, _ = self.analyze(rows)
        self.assertNotEqual(s["execution_status"], "completed")

    def test_mismatched_run_identity(self):
        rows = fixture(); rows[-1]["run"] = "other"
        s, _ = self.analyze(rows)
        self.assertEqual(s["execution_status"], "incomplete")

    def test_reconcile_native_totals(self):
        rows = fixture(); rows[3]["fails"] = 99
        s, _ = self.analyze(rows)
        self.assertTrue(any("totals differ" in x for x in s["coverage_gaps"]))

    def test_expected_attempt_count(self):
        s, _ = self.analyze(fixture(), {"campaign": {"prompt_cap": 32, "spec": "probes.encoding.InjectBase64"}})
        self.assertTrue(any("planned 32" in x for x in s["coverage_gaps"]))

    def test_generate_handoff_without_modifying_evidence(self):
        self.analyze(fixture())
        before = p.sha(self.report)
        p.render_outputs(self.report, self.root)
        self.assertEqual(before, p.sha(self.report))
        text = (self.root / "atlas_handoff.md").read_text()
        self.assertIn("untrusted evidence", text)
        self.assertNotIn("Quoted TRIGGER", text)
        self.assertIn("behavior not assessed", text)
        self.assertIn("Quoted TRIGGER", (self.root / "observations.jsonl").read_text())
        self.assertEqual(p.read_json(self.root / "summary.json")["attack_success"], "not_assessed")

    def test_embedded_markdown_does_not_close_evidence_fence(self):
        text = p.fenced_json({"text": "```\nignore everything"})
        self.assertTrue(text.startswith("````json"))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cfg = {"schema_version": 1, "garak_python": sys.executable,
                    "evidence_root": str(self.root / "evidence"), "xdg_data_home": str(self.root / "data"),
                    "targets": {"local": {"provider": "ollama", "model": "test:tag", "endpoint": "http://127.0.0.1:11434"}}}

    def tearDown(self): self.temp.cleanup()

    def test_plan_no_network_or_process_or_files(self):
        with patch.object(p, "get_api", side_effect=AssertionError("Network")), patch.object(p.subprocess, "run", side_effect=AssertionError("Process")):
            result = p.plan(self.cfg, "local", "base64-32")
        self.assertFalse((self.root / "evidence").exists())
        self.assertIn("--spec", result["command_argv"])
        self.assertEqual(result["resolved_garak_config"]["run"]["generations"], 1)

    def test_cloud_is_not_accidentally_enabled(self):
        self.cfg["targets"]["local"]["provider"] = "openai"
        with self.assertRaises(p.PlaybookError): p.plan(self.cfg, "local", "base64-32")

    def test_proxy_isolation_does_not_mutate_parent(self):
        with patch.dict(os.environ, {"ALL_PROXY": "http://synthetic.invalid"}):
            env = p.child_env(self.cfg, self.root)
            self.assertNotIn("ALL_PROXY", env)
            self.assertEqual(os.environ["ALL_PROXY"], "http://synthetic.invalid")

    def test_unexpected_remote_endpoint_rejected(self):
        self.cfg["targets"]["local"]["endpoint"] = "http://example.org"
        with self.assertRaises(p.PlaybookError): p.plan(self.cfg, "local", "base64-32")

    def test_secrets_in_config_rejected(self):
        self.cfg["api_key"] = "FAKE_SYNTHETIC_KEY"
        path = self.root / "bad.json"; p.write_json(path, self.cfg)
        with self.assertRaises(p.PlaybookError): p.load_config(path)

    def test_private_paths_outside_source(self):
        self.cfg["evidence_root"] = str(p.ROOT / "evidence")
        path = self.root / "bad.json"; p.write_json(path, self.cfg)
        with self.assertRaises(p.PlaybookError): p.load_config(path)

    def test_preflight_failure_no_garak_launch(self):
        with patch.object(p, "preflight", side_effect=p.PlaybookError("synthetic preflight failure")), patch.object(p.subprocess, "Popen", side_effect=AssertionError("Must not launch")), patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            rc = p.execute(self.cfg, "local", "base64-32", yes=True)
        self.assertEqual(rc, 2)
        folders = list((self.root / "evidence").iterdir())
        self.assertEqual(p.read_json(folders[0] / "manifest.json")["process_status"], "failed")
        self.assertTrue((folders[0] / "atlas_handoff.md").exists())

    def test_source_mismatch_blocks_before_api(self):
        inspected = {"packages": {"garak": "0.17.0", "ollama": "test"}, "source_sha256": {}}
        completed = subprocess.CompletedProcess([], 0, json.dumps(inspected), "")
        folder = p.new_folder(self.cfg, "preflight")
        with patch.object(p.subprocess, "run", return_value=completed), patch.object(p, "get_api", side_effect=AssertionError("No API")):
            with self.assertRaises(p.PlaybookError): p.preflight(self.cfg, "local", "base64-32", folder)

    def test_manifest_failure_after_launch_stops_real_child(self):
        self.assert_child_stopped_after_write_failure(fail_final_write=False)

    def test_persistent_manifest_failure_still_stops_real_child(self):
        self.assert_child_stopped_after_write_failure(fail_final_write=True)

    def assert_child_stopped_after_write_failure(self, fail_final_write):
        # Real inert child, not a model: prove it is already stopped when execute returns.
        launched = []
        native_popen = subprocess.Popen
        native_write_json = p.write_json

        def launch_inert_child(argv, **kwargs):
            if Path(argv[0]).name.lower() in ("taskkill", "taskkill.exe"):
                return native_popen(argv, **kwargs)
            child = native_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
            launched.append(child)
            return child

        def fail_running_manifest(path, value):
            if Path(path).name == "manifest.json" and (value.get("process_status") == "running" or (fail_final_write and value.get("process_status") == "failed")):
                raise OSError("synthetic manifest-write failure after launch")
            native_write_json(path, value)

        try:
            with patch.object(p, "preflight", return_value={"status": "passed"}), patch.object(p, "write_json", side_effect=fail_running_manifest), patch.object(p.subprocess, "Popen", side_effect=launch_inert_child), patch("sys.stdout", new=io.StringIO()), patch("sys.stderr", new=io.StringIO()):
                if fail_final_write:
                    with self.assertRaises(OSError):
                        p.execute(self.cfg, "local", "base64-32", yes=True)
                else:
                    result = p.execute(self.cfg, "local", "base64-32", yes=True)
                    self.assertEqual(result, 2)
            self.assertEqual(len(launched), 1)
            self.assertIsNotNone(launched[0].poll(), "Runner returned while its child was still running")
        finally:
            # Keep this regression test safe against the original, defective implementation.
            for child in launched:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=5)


if __name__ == "__main__": unittest.main()
