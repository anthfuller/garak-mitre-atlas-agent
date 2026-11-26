"""Offline control-flow, credential and cost tests; no model or paid API."""
import copy
from datetime import date
from decimal import Decimal
import getpass
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import openai_profile as profile
import openai_cost as cost
import openai_worker as worker
from test_probe_browser import inventory_fixture, report_fixture


class OpenAITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cfg = {"schema_version": 1, "garak_python": sys.executable,
                    "evidence_root": str(self.root / "evidence"), "xdg_data_home": str(self.root / "data"),
                    "targets": {"local": {"provider": "ollama", "model": "synthetic:only", "endpoint": "http://127.0.0.1:11434"}}}
        self.inventory = inventory_fixture()
        row = next(r for r in self.inventory["probes"] if r["name"] == "probes.goodside.WhoIsRiley")
        self.campaign = p.probe_catalog.campaign_for(row, profile.TARGET, self.inventory)
        self.campaign["input_estimate"] = {"max_input_units_per_request": 100}
        # Exercise this price record within its verified validity window.
        verified = date.fromisoformat(p.read_json(p.ROOT / "openai-pricing.json")["verified_on"])
        self.campaign["pricing"] = cost.published_rates("gpt-5.6-sol", verified)

    def tearDown(self):
        self.temp.cleanup()

    def test_openai_is_second_without_rewriting_private_config(self):
        original = copy.deepcopy(self.cfg)
        with patch("builtins.input", side_effect=["2", "3"]), patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(p.menu(self.cfg), 0)
        self.assertIn("1. local", out.getvalue())
        self.assertIn("2. openai-reasoning", out.getvalue())
        self.assertIn("unverified", out.getvalue())
        self.assertEqual(original, self.cfg)

    def test_multiple_openai_choices_and_no_request_cap_by_default(self):
        rows = p.probe_catalog.supported_rows(self.inventory, profile.TARGET)
        self.assertEqual(len(rows), 14)
        for row in rows:
            campaign = p.probe_catalog.campaign_for(row, profile.TARGET, self.inventory)
            self.assertIsNone(campaign["workload"]["http_request_limit"])
            headroom = row["name"] in {
                "probes.encoding.InjectAscii85", "probes.encoding.InjectBase32",
                "probes.encoding.InjectBase64",
            }
            self.assertEqual(campaign["max_completion_tokens"], 20000 if headroom else 1500)

    def test_reasoning_config_has_real_limit_not_max_tokens_or_temperature(self):
        config = p.garak_config(profile.TARGET, self.campaign)
        generator = config["plugins"]["generators"]["openai"]["OpenAIReasoningGenerator"]
        self.assertEqual(generator["max_completion_tokens"], 1500)
        self.assertNotIn("max_tokens", generator)
        self.assertNotIn("temperature", generator)
        self.assertIsNone(generator["seed"])
        self.assertTrue({"temperature", "max_tokens", "seed", "n", "stop"}.issubset(generator["suppressed_params"]))

    def test_credentials_never_enter_config_command_or_inherited_child_env(self):
        dummy = "sk-DUMMY-ENVIRONMENT-KEY"
        with patch.dict(os.environ, {"OPENAI_API_KEY": dummy, "OPENAI_BASE_URL": "https://wrong.invalid", "OPENAI_LOG": "debug"}):
            env = p.child_env(self.cfg, self.root)
            plan = p.plan(self.cfg, profile.NAME, self.campaign)
            self.assertFalse(any(k.upper().startswith("OPENAI_") for k in env))
            self.assertEqual(os.environ["OPENAI_API_KEY"], dummy)
        self.assertNotIn(dummy, json.dumps(plan))
        self.assertIn("openai_worker.py", plan["command_argv"][1])
        self.assertIn("openai.OpenAIReasoningGenerator", plan["command_argv"])

    def test_hidden_key_cancel_and_refuse_echo_fallback(self):
        with patch("sys.stdin.isatty", return_value=True), patch.object(getpass, "getpass", return_value="sk-DUMMY") as ask:
            self.assertEqual(profile.read_session_key(), "sk-DUMMY")
            self.assertIn("hidden", ask.call_args.args[0])
        for result in ("", EOFError(), KeyboardInterrupt()):
            with patch("sys.stdin.isatty", return_value=True), patch.object(getpass, "getpass", side_effect=[result]):
                self.assertIsNone(profile.read_session_key())
        def echo_fallback(*args):
            warnings.warn("echo fallback", getpass.GetPassWarning)
            self.fail("Echoing fallback must not proceed")
        with patch("sys.stdin.isatty", return_value=True), patch.object(getpass, "getpass", side_effect=echo_fallback):
            self.assertIsNone(profile.read_session_key())

    def test_split_secret_console_and_exception_logging_are_redacted(self):
        import logging
        key = "sk-DUMMY-SECRET-TO-REDACT"
        out = io.StringIO()
        stream = worker.SecretStream(out, key)
        stream.write("before " + key[:8]); stream.flush()
        stream.write(key[8:] + " after"); stream.finish()
        self.assertNotIn(key, out.getvalue())
        self.assertIn("[REDACTED_API_KEY]", out.getvalue())
        record = logging.LogRecord("test", 40, "test", 1, "error " + key, (), None)
        with worker.secret_output(key):
            value = logging.Formatter().format(record)
        self.assertNotIn(key, value)

    def test_token_cap_alert_and_manual_rate_edits_are_ephemeral(self):
        for action, choices in (("r", ["4"]), ("a", ["0.50"]), ("p", ["4", "20"])):
            with patch("builtins.input", side_effect=choices):
                p.edit_cloud_controls(self.campaign, action, profile.TARGET["model"])
        self.assertEqual(self.campaign["workload"]["http_request_limit"], 4)
        self.assertEqual(self.campaign["spending_alert_usd"], "0.50")
        self.assertIn("Operator-supplied", self.campaign["pricing"]["source"])
        with patch("builtins.input", return_value="0"):
            p.edit_cloud_controls(self.campaign, "r", profile.TARGET["model"])
            p.edit_cloud_controls(self.campaign, "a", profile.TARGET["model"])
        self.assertIsNone(self.campaign["workload"]["http_request_limit"])
        self.assertIsNone(self.campaign["spending_alert_usd"])

    def test_cost_includes_compatibility_and_full_completion_allowance(self):
        estimate = cost.estimate(self.campaign)
        self.assertEqual(estimate["requests"], 7)
        self.assertEqual(estimate["completion_token_ceiling"], 10500)
        self.assertEqual(Decimal(estimate["estimated_usd"]), Decimal("0.2128"))
        self.campaign["workload"]["http_request_limit"] = 10
        self.assertEqual(cost.estimate(self.campaign)["requests"], 10)

    def test_expired_unknown_and_missing_pricing_show_unavailable(self):
        self.assertIsNone(cost.published_rates("gpt-5.6-sol", date(2026, 12, 1)))
        self.assertIsNone(cost.published_rates("unknown", date(2026, 11, 22)))
        self.campaign["pricing"] = None
        with patch("sys.stdout", new=io.StringIO()) as out:
            p.show_cloud_cost(self.campaign, profile.TARGET)
        self.assertIn("Estimate unavailable", out.getvalue())
        self.assertIn("RUN is still allowed", out.getvalue())

    def test_running_cost_counts_compatibility_retries_and_missing_usage(self):
        tracker = cost.Tracker(self.root, self.campaign)
        with patch("sys.stdout", new=io.StringIO()) as out:
            tracker.after_response({"usage": {"prompt_tokens": 10, "completion_tokens": 3}}, 1, "compatibility")
            tracker.after_response({"usage": {"prompt_tokens": 10, "completion_tokens": 3}}, 2, "scan")
            tracker.after_response({}, 3, "scan")
        self.assertEqual(tracker.total, Decimal("0.0002"))
        self.assertEqual(tracker.missing, 1)
        self.assertIn("Running estimated API total", out.getvalue())

    def test_optional_alert_continue_raise_stop_and_off(self):
        self.campaign["spending_alert_usd"] = "0.001"
        for choices, stopped, new_alert in ((["1"], False, "0.001"), (["2", "2"], False, "2"), (["3"], True, "0.001")):
            with self.subTest(choices=choices):
                tracker = cost.Tracker(self.root, self.campaign)
                tracker.total = Decimal("0.01")
                with patch("builtins.input", side_effect=choices), patch("sys.stdout", new=io.StringIO()):
                    if stopped:
                        with self.assertRaises(cost.StopRequested): tracker.before_request()
                    else: tracker.before_request()
                self.assertEqual(tracker.alert, Decimal(new_alert))
        self.campaign["spending_alert_usd"] = None
        tracker = cost.Tracker(self.root, self.campaign)
        tracker.total = Decimal("500")
        with patch("builtins.input", side_effect=AssertionError("No optional alert configured")):
            tracker.before_request()

    def test_missing_rates_do_not_block_or_trigger_uncalculable_alert(self):
        self.campaign.update({"pricing": None, "spending_alert_usd": "0.1"})
        tracker = cost.Tracker(self.root, self.campaign)
        with patch("builtins.input", side_effect=AssertionError("No calculated cost")), patch("sys.stdout", new=io.StringIO()) as out:
            tracker.after_response({"usage": {"prompt_tokens": 10, "completion_tokens": 3}}, 1, "compatibility")
            tracker.before_request()
        self.assertIn("Estimate unavailable", out.getvalue())

    def test_openai_yes_fails_without_prompt_or_paid_request(self):
        with patch("builtins.input", side_effect=AssertionError("Unattended")), patch.object(p.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(p.PlaybookError, "--yes"):
                p.execute(self.cfg, profile.NAME, self.campaign, yes=True)
        launch.assert_not_called()

    def test_review_changes_limit_and_cancels_without_scan(self):
        choices = ["L", "900", "L", "bad", "R", "5", "R", "0", "A", "0.25", ""]
        with patch.object(p, "estimate_cloud_workload", return_value=self.campaign["input_estimate"]), \
             patch("builtins.input", side_effect=choices), patch("sys.stdin.isatty", return_value=True), \
             patch("sys.stdout", new=io.StringIO()) as out, patch.object(p.subprocess, "Popen") as launch:
            self.assertEqual(p.execute(self.cfg, profile.NAME, self.campaign, allow_back=True), 0)
        text = out.getvalue()
        self.assertIn("Effective max_completion_tokens: 900", text)
        self.assertIn("Estimated total cost before RUN:", text)
        self.assertIn("Optional HTTP request cap: OFF", text)
        self.assertIn("Optional spending alert: $0.25", text)
        launch.assert_not_called()
        self.assertFalse(Path(self.cfg["evidence_root"]).exists())

    def test_cloud_menu_run_uses_selected_settings_and_existing_handoff(self):
        folders = []
        def scanner(argv, **kwargs):
            folder = Path(kwargs["cwd"]); folders.append(folder)
            config = p.read_json(folder / "garak-config.json")
            self.assertEqual(config["plugins"]["generators"]["openai"]["OpenAIReasoningGenerator"]["max_completion_tokens"], 900)
            self.assertNotIn("stdin", kwargs)  # inherited terminal supports hidden entry and optional pauses
            self.assertFalse(any(k.startswith("OPENAI_") for k in kwargs["env"]))
            p.write_jsonl(folder / "scan.report.jsonl", report_fixture("probes.goodside.WhoIsRiley", "goodside.RileyIsnt", 6))
            p.write_json(folder / "openai-session.json", {"status": "scan_returned", "model_access": "confirmed by this request", "http_requests": 7})
            transport = []
            for seq in range(1, 8):
                stage = "compatibility" if seq == 1 else "scan"
                transport.extend([{"entry_type": "request", "sequence": seq, "stage": stage},
                    {"entry_type": "response", "sequence": seq, "stage": stage, "http_status": 200,
                     "body": {"choices": [{"finish_reason": "stop", "message": {"content": "SYNTHETIC"}}]}}])
            p.write_jsonl(folder / "openai-transport.jsonl", transport)
            child = MagicMock(returncode=0, stdout=io.BytesIO(b"SYNTHETIC cloud worker\n"))
            child.poll.return_value = child.wait.return_value = 0
            return child
        with patch.object(p, "installed_inventory", return_value=self.inventory), \
             patch.object(p, "estimate_cloud_workload", return_value=self.campaign["input_estimate"]), \
             patch("builtins.input", side_effect=["2", "2", "s", "WhoIsRiley", "1", "L", "900", "RUN", "3"]), \
             patch("sys.stdin.isatty", return_value=True), patch("sys.stdout", new=io.StringIO()), \
             patch.object(p, "preflight", return_value={"status": "passed", "model_access": "unverified"}), \
             patch.object(p.subprocess, "Popen", side_effect=scanner) as launch:
            self.assertEqual(p.menu(self.cfg), 0)
        launch.assert_called_once()
        manifest = p.read_json(folders[0] / "manifest.json")
        self.assertEqual(manifest["target"]["model"], "gpt-5.6-sol")
        self.assertIsNone(manifest["campaign"]["workload"]["http_request_limit"])
        self.assertIn("evaluated responses: 6; detector flags: 0", (folders[0] / "atlas_handoff.md").read_text())


if __name__ == "__main__":
    unittest.main()
