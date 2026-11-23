"""Synthetic/local MCP only. No live Langflow, LLM or browser validation."""
import contextlib
import copy
import html
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_mcp as a
import kumu_mcp as k
import playbook as p
import test_atlas_mcp as base

IDS = ["AML.T0054", "AML.T0051.000"]
TARGET = {"expected_project_id": "synthetic-project", "expected_map_name": "atlas"}


def envelope(run_id, ids):
    focus = "1" if len(ids) == 1 else urllib.parse.quote(", ".join("#" + x.lower().replace(".", "-") + " out 1" for x in ids), safe="")
    url = "https://embed.kumu.io/synthetic-project#atlas/" + ids[0].lower().replace(".", "-") + "?focus=" + focus
    return {"run_id": run_id, "verified_ids": ids, "graph_result": {
        "status": "success", "ids": ids, "anchor": ids[0],
        "focus_mode": "single_anchor" if len(ids) == 1 else "multi_anchor_outbound_one_hop",
        "duplicates_removed": [], "invalid_ids": [], "url": url,
        "iframe": '<iframe src="' + html.escape(url, quote=True) + '" width="600" height="400" frameborder="0" loading="lazy" referrerpolicy="no-referrer" title="MITRE ATLAS focused graph"></iframe>'}}


def response_for(obj):
    # Reproduce two MCP text blocks differing only in whitespace.
    return {"content": [{"type": "text", "text": json.dumps(obj, indent=2)},
                        {"type": "text", "text": "```json\n" + json.dumps(obj) + "\n```"}], "isError": False}


class KumuTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base.AtlasTests()
        self.fixture.setUp()
        self.run, self.root, self.summary = self.fixture.run, self.fixture.root, self.fixture.summary
        self.config = self.root / "kumu.private.json"
        p.write_json(self.config, TARGET)
        self.source = self.run / "atlas-submissions" / "synthetic-analysis"
        self.source.mkdir(parents=True)
        self.hand = (self.run / "atlas_handoff.md").read_bytes()
        text = "Candidate mappings for this synthetic test: AML.T0054 and AML.T0051.000.\nNot a real finding."
        self.saved_response = {"content": [{"type": "text", "text": text}, {"type": "text", "text": text.replace('\n', '\n\n')}], "isError": False}
        self.saved = {"status": "response_received_unreviewed", "source_files_unchanged": True,
            "run_id": self.summary["garak_run_id"], "submission_id": "synthetic-atlas-submission", "conversation_id": "prior-synthetic-session",
            "agent_provider": "Synthetic provider", "agent_model": "synthetic-model", "source_files_sha256": self.fixture.before}
        p.write_json(self.source / "request.json", {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": a.TOOL, "arguments": {"input_value": self.hand.decode(), "session_id": self.saved["conversation_id"]}}})
        p.write_json(self.source / "response.json", self.saved_response)
        (self.source / "handoff.submitted.md").write_bytes(self.hand)
        (self.source / "atlas_response.md").write_text(text)
        p.write_json(self.source / "mcp-exchanges.json", [])

    def tearDown(self):
        self.fixture.tearDown()

    def bind(self, server):
        discovery = self.fixture.discovery(server)
        self.saved["connection"] = a.load_discovery(discovery)
        p.write_json(self.source / "submission.json", self.saved)
        self.rehash()
        server.result_builder = lambda body: response_for(envelope(self.summary["garak_run_id"], IDS))

    def rehash(self):
        p.write_json(self.source / "checksums.json", {f.name: a.file_hash(f) for f in self.source.iterdir()
                                                     if f.is_file() and f.name != "checksums.json"})

    def invoke(self, server, answers=("A", "GRAPH", ""), **kwargs):
        before = {str(f): f.read_bytes() for f in self.run.rglob("*") if f.is_file() and "kumu-submissions" not in f.parts}
        stream = io.StringIO()
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=answers), \
             patch.object(a, "api_key_prompt", return_value=base.KEY), patch.object(k.webbrowser, "open", return_value=True) as browser, \
             contextlib.redirect_stdout(stream):
            code = k.generate(self.run, analyze=p.analyze, submission=self.source, config_path=self.config, **kwargs)
        for path, data in before.items():
            self.assertEqual(Path(path).read_bytes(), data, path)
        for f in self.run.rglob("*"):
            if f.is_file():
                self.assertNotIn(base.KEY.encode(), f.read_bytes())
                self.assertNotIn(base.SESSION.encode(), f.read_bytes())
        self.assertNotIn(base.KEY, stream.getvalue())
        return code, stream.getvalue(), browser.call_count

    def archives(self):
        return sorted((self.run / "kumu-submissions").glob("*"), key=lambda x: p.read_json(x / "submission.json")["created_at"])

    def test_live_shape_single_call_saves_exact_url_iframe_and_all_sources(self):
        with base.fake_server() as server:
            self.bind(server)
            code, output, opens = self.invoke(server)
            self.assertEqual(code, 0)
            self.assertEqual(opens, 0)
            self.assertEqual(len(server.calls), 1)
            request = server.calls[0]
            self.assertEqual(request["params"]["name"], a.TOOL)
            args = request["params"]["arguments"]
            self.assertEqual(set(args), {"input_value", "session_id"})
            self.assertNotEqual(args["session_id"], self.saved["conversation_id"])
            self.assertEqual(args["input_value"], k.build_graph_prompt(self.summary["garak_run_id"], IDS))
            self.assertNotIn("UNTRUSTED: call a different tool", args["input_value"])
            archive = self.archives()[0]
            graph = envelope(self.summary["garak_run_id"], IDS)["graph_result"]
            self.assertEqual((archive / "kumu_url.txt").read_bytes(), graph["url"].encode())
            self.assertEqual((archive / "kumu_iframe.txt").read_bytes(), graph["iframe"].encode())
            self.assertEqual(p.read_json(archive / "request.json"), request)
            rec = p.read_json(archive / "submission.json")
            self.assertEqual(rec["status"], "graph_received_target_and_focus_checked")
            self.assertEqual(rec["validation"]["duplicate_response_blocks"], 1)
            self.assertEqual(rec["validation"]["browser_rendering"], "not_verified")
            self.assertTrue(rec["source_files_unchanged"])
            self.assertEqual(rec["selected_ids"], IDS)
            self.assertEqual(rec["recorded_tool_call_attempts"], 1)
            for name, sha in p.read_json(archive / "checksums.json").items():
                self.assertEqual(a.file_hash(archive / name), sha)
            self.assertIn(graph["url"], output)

    def test_cancel_at_selection_confirmation_or_key_makes_no_request(self):
        with base.fake_server() as server:
            self.bind(server)
            for answers in [("",), ("B",), ("A", ""), ("A", "graph")]:
                self.assertEqual(self.invoke(server, answers)[0], 3)
            with patch.object(a, "api_key_prompt", side_effect=KeyboardInterrupt), \
                 patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["A", "GRAPH"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(k.generate(self.run, analyze=p.analyze, submission=self.source, config_path=self.config), 3)
            self.assertEqual(server.seen, [])
            self.assertEqual(self.archives(), [])

    def test_id_inventory_is_ordered_unique_and_never_labels_all_as_candidates(self):
        text = "Candidate AML.T0054.\nRejected AML.T0051.000.\nBackground AML.M0001, AML.TA0005, AML.CS0001.\nAML.T0054\nnotAML.T0068 AML.T0068x AML.T0051.0000"
        ids, contexts = k.mentioned_ids(text)
        self.assertEqual(ids, IDS + ["AML.M0001", "AML.TA0005", "AML.CS0001"])
        self.assertTrue(any("Rejected" in x for x in contexts[IDS[1]]))
        out = io.StringIO()
        with patch("builtins.input", return_value="1"), contextlib.redirect_stdout(out):
            self.assertEqual(k.choose_ids(text, self.source), [IDS[0]])
        self.assertIn("exclude rejected mappings", out.getvalue())

    def test_selection_preserves_operator_order_and_rejects_unknown_indices(self):
        with patch("builtins.input", return_value="2,1,2"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(k.choose_ids(" ".join(IDS), self.source), list(reversed(IDS)))
        for answer in ["0", "3", "1;2", "AML.T0054"]:
            with patch("builtins.input", return_value=answer), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(a.AtlasError):
                k.choose_ids(" ".join(IDS), self.source)

    def test_single_selected_id_uses_single_anchor(self):
        with base.fake_server() as server:
            self.bind(server)
            server.result_builder = lambda body: response_for(envelope(self.summary["garak_run_id"], [IDS[1]]))
            code, _, _ = self.invoke(server, ("2", "GRAPH", ""))
            self.assertEqual(code, 0)
            self.assertIn("?focus=1", (self.archives()[0] / "kumu_url.txt").read_text())

    def test_missing_second_focus_is_rejected_even_when_metadata_claims_both(self):
        with base.fake_server() as server:
            self.bind(server)
            obj = envelope(self.summary["garak_run_id"], IDS)
            graph = obj["graph_result"]
            graph["url"] = graph["url"].split("?focus=")[0] + "?focus=%23aml-t0054"
            graph["iframe"] = '<iframe src="' + graph["url"] + '"></iframe>'
            server.result_builder = lambda body: response_for(obj)
            code, out, opens = self.invoke(server, ("A", "GRAPH"))
            self.assertEqual(code, 2)
            self.assertEqual(opens, 0)
            self.assertEqual(len(server.calls), 1)
            archive = self.archives()[0]
            self.assertEqual(p.read_json(archive / "submission.json")["status"], "graph_reply_not_validated")
            self.assertFalse((archive / "kumu_url.txt").exists())
            self.assertTrue((archive / "response.json").exists())
            self.assertIn("focus does not contain exactly", out)

    def test_bad_run_ids_anchor_extra_ids_and_conflicting_blocks_rejected(self):
        obj = envelope("run", IDS)
        cases = []
        for field, value in [("ids", IDS[:1]), ("anchor", IDS[1]), ("invalid_ids", ["AML.T9999"]),
                             ("duplicates_removed", IDS), ("focus_mode", "single_anchor")]:
            bad = copy.deepcopy(obj)
            bad["graph_result"][field] = value
            cases.append(response_for(bad))
        bad = copy.deepcopy(obj); bad["run_id"] = "wrong"; cases.append(response_for(bad))
        bad = copy.deepcopy(obj); bad["verified_ids"] = IDS[:1]; cases.append(response_for(bad))
        cases.append({"content": [response_for(obj)["content"][0], response_for(bad)["content"][0]]})
        for response in cases:
            with self.subTest(response=response), self.assertRaises(a.AtlasError):
                k.validate_graph(response, "run", IDS, target=TARGET)

    def test_url_and_iframe_checks_block_unexpected_navigation_or_markup(self):
        good = envelope("run", IDS)
        original = good["graph_result"]["url"]
        for url in [original.replace("https:", "http:"), original.replace("embed.kumu.io", "evil.invalid"),
                    original.replace("embed.kumu.io", "embed.kumu.io@evil.invalid"), original + "&other=1",
                    original.replace("out%201", "out%202"), original.replace("%2C", "%2C%20%23aml-t9999%20out%201%2C", 1),
                    original + "\n", original.replace("aml-t0054?", "aml-t0051-000?")]:
            with self.subTest(url=url), self.assertRaises(a.AtlasError):
                k.check_url(url, IDS, target=TARGET)
        for iframe in ['<iframe src="javascript:alert(1)"></iframe>', '<iframe src="' + original + '" onload="x"></iframe>',
                       '<script>x</script>', '<iframe src="' + original + '" srcdoc="x"></iframe>',
                       '<iframe src="' + original + '"></iframe><iframe></iframe>']:
            with self.subTest(iframe=iframe), self.assertRaises(a.AtlasError):
                k.check_iframe(iframe, original)

    def test_empty_error_plaintext_and_nontext_replies_are_not_success(self):
        for response in [{"content": []}, {"content": [{"type": "text", "text": "https://embed.kumu.io/example"}]},
                         {"content": [{"type": "resource", "resource": {"uri": "https://example.invalid"}}]},
                         {"isError": True, "content": []}, response_for({"run_id": "run", "verified_ids": [], "graph_result": {"status": "error"}})]:
            with self.subTest(response=response), self.assertRaises(a.AtlasError):
                k.validate_graph(response, "run", IDS, target=TARGET)

    def test_schema_auth_redirect_fail_before_tool_and_disconnect_not_retried(self):
        for mode in ["auth_error", "wrong_schema", "redirect", "disconnect"]:
            with self.subTest(mode=mode), base.fake_server(mode) as server:
                self.bind(server)
                code, _, opens = self.invoke(server, ("A", "GRAPH"))
                self.assertEqual(code, 2)
                self.assertEqual(opens, 0)
                rec = p.read_json(self.archives()[-1] / "submission.json")
                self.assertEqual(rec["automatic_retries"], 0)
                self.assertEqual(len(server.calls), int(mode == "disconnect"))
                self.assertEqual(rec["status"], "execution_unknown" if mode == "disconnect" else "failed_before_tool_call")

    def test_explicit_repeat_has_new_sessions_and_keeps_prior_graph_bytes(self):
        with base.fake_server() as server:
            self.bind(server)
            self.assertEqual(self.invoke(server)[0], 0)
            first = self.archives()[0]
            saved = {x.name: x.read_bytes() for x in first.iterdir()}
            self.assertEqual(self.invoke(server)[0], 0)
            for name, data in saved.items(): self.assertEqual((first / name).read_bytes(), data)
            sessions = [x["params"]["arguments"]["session_id"] for x in server.calls]
            self.assertEqual(len(set(sessions)), 2)
            self.assertEqual(len(self.archives()), 2)

    def test_open_only_after_explicit_choice_and_error_does_not_change_status(self):
        with base.fake_server() as server:
            self.bind(server)
            code, _, opens = self.invoke(server, ("A", "GRAPH", "1"))
            self.assertEqual((code, opens), (0, 1))
        for answer in ["", "2", "B"]:
            with patch("builtins.input", return_value=answer), patch.object(k.webbrowser, "open") as browser:
                k.offer_open("https://embed.kumu.io/synthetic#atlas/aml-t0054?focus=1")
                browser.assert_not_called()
        with patch("builtins.input", return_value="1"), patch.object(k.webbrowser, "open", side_effect=OSError("synthetic")), contextlib.redirect_stdout(io.StringIO()):
            k.offer_open("https://embed.kumu.io/synthetic#atlas/aml-t0054?focus=1")

    def test_source_tamper_and_other_run_are_blocked_before_network(self):
        with base.fake_server() as server:
            self.bind(server)
            (self.source / "response.json").write_text('{}')
            with self.assertRaises(a.AtlasError): self.invoke(server)
            self.assertEqual(server.seen, [])
            self.rehash()
            self.saved["run_id"] = "other-run"
            p.write_json(self.source / "submission.json", self.saved); self.rehash()
            with self.assertRaises(a.AtlasError): self.invoke(server)

    def test_multiple_saved_analyses_require_selection_and_allow_cancel(self):
        p.write_json(self.source / "submission.json", self.saved)
        other = self.source.parent / "another-synthetic-analysis"
        other.mkdir()
        p.write_json(other / "submission.json", {})
        with patch("builtins.input", return_value=""), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(k.choose_submission(self.run))
        choices = sorted([other, self.source])
        number = str(choices.index(self.source) + 1)
        with patch("builtins.input", return_value=number), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(k.choose_submission(self.run), self.source)

    def test_changed_analysis_after_confirmation_blocks_all_requests(self):
        with base.fake_server() as server:
            self.bind(server)
            def edit_then_key():
                (self.source / "atlas_response.md").write_text("Changed after review")
                return base.KEY
            with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["A", "GRAPH"]), \
                 patch.object(a, "api_key_prompt", side_effect=edit_then_key), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(a.AtlasError):
                k.generate(self.run, analyze=p.analyze, submission=self.source, config_path=self.config)
            self.assertEqual(server.seen, [])
            self.assertEqual(self.archives(), [])

    def test_archive_failure_before_dispatch_prevents_call_after_reply_keeps_uncertainty_distinct(self):
        for after in [False, True]:
            with self.subTest(after=after), base.fake_server() as server:
                self.bind(server)
                original = a.atomic_json
                def fail_write(path, data):
                    if path.name == ("kumu_result.json" if after else "request.json"):
                        raise OSError("synthetic disk failure")
                    return original(path, data)
                with patch.object(a, "atomic_json", side_effect=fail_write):
                    code, _, opens = self.invoke(server, ("A", "GRAPH"))
                self.assertEqual((code, opens), (2, 0))
                self.assertEqual(len(server.calls), int(after))
                status = p.read_json(self.archives()[-1] / "submission.json")["status"]
                self.assertEqual(status, "archive_incomplete_after_response" if after else "failed_before_tool_call")

    def test_sse_graph_reply_preserved(self):
        with base.fake_server("sse") as server:
            self.bind(server)
            self.assertEqual(self.invoke(server)[0], 0)
            exchanges = p.read_json(self.archives()[0] / "mcp-exchanges.json")
            self.assertIn("notifications/progress", exchanges[-1]["response_body_utf8"])
            self.assertTrue(exchanges[-1]["response_body_complete"])

    def test_private_target_binding_correct_wrong_project_wrong_map_missing_second(self):
        good = envelope("run", IDS)
        accepted, checked = k.validate_graph(response_for(good), "run", IDS, target=TARGET)
        self.assertEqual(accepted, good)
        self.assertEqual(checked["target_binding"], "matched_independent_private_configuration")
        for label in ["project", "map", "second_id"]:
            bad = copy.deepcopy(good)
            graph = bad["graph_result"]
            if label == "project": graph["url"] = graph["url"].replace("/synthetic-project#", "/other-project#")
            elif label == "map": graph["url"] = graph["url"].replace("#atlas/", "#other-map/")
            else: graph["url"] = graph["url"].split("?focus=")[0] + "?focus=%23aml-t0054%20out%201"
            graph["iframe"] = '<iframe src="' + graph["url"] + '"></iframe>'
            with self.subTest(label=label), self.assertRaises(a.AtlasError):
                k.validate_graph(response_for(bad), "run", IDS, target=TARGET)

    def test_wrong_target_is_archived_without_acceptance_opening_or_config_updates(self):
        for field in ["project", "map"]:
            with self.subTest(field=field), base.fake_server() as server:
                self.bind(server)
                obj = envelope(self.summary["garak_run_id"], IDS)
                g = obj["graph_result"]
                g["url"] = g["url"].replace("synthetic-project", "other-project") if field == "project" else g["url"].replace("#atlas/", "#other-map/")
                g["iframe"] = '<iframe src="' + g["url"] + '"></iframe>'
                server.result_builder = lambda body: response_for(obj)
                before = self.config.read_bytes()
                code, out, opens = self.invoke(server, ("A", "GRAPH"))
                self.assertEqual((code, opens), (2, 0))
                archive = self.archives()[-1]
                self.assertEqual(p.read_json(archive / "response.json"), response_for(obj))
                record = p.read_json(archive / "submission.json")
                self.assertEqual(record["status"], "graph_reply_not_validated")
                self.assertIn("independently configured", record["validation_error"])
                self.assertFalse((archive / "kumu_url.txt").exists())
                self.assertEqual(self.config.read_bytes(), before)
                self.assertIn("selected IDs plus one-hop research context", out)

    def test_missing_or_malformed_private_config_blocks_before_network_or_key(self):
        for value in [None, {}, {"expected_project_id": "x", "expected_map_name": "ATLAS"},
                      {"expected_project_id": "https://embed.kumu.io/x", "expected_map_name": "atlas"}]:
            if value is None: self.config.unlink(missing_ok=True)
            else: p.write_json(self.config, value)
            with self.subTest(value=value), patch("sys.stdin.isatty", return_value=True), \
                 patch.object(a, "api_key_prompt") as key, patch.object(a, "Client") as client, self.assertRaises(a.AtlasError):
                k.generate(self.run, analyze=p.analyze, submission=self.source, config_path=self.config)
            client.assert_not_called(); key.assert_not_called()

    def test_config_change_after_confirmation_blocks_before_requests(self):
        with base.fake_server() as server:
            self.bind(server)
            def changed_key():
                p.write_json(self.config, {**TARGET, "expected_project_id": "other-project"})
                return base.KEY
            with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["A", "GRAPH"]), \
                 patch.object(a, "api_key_prompt", side_effect=changed_key), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(a.AtlasError):
                k.generate(self.run, analyze=p.analyze, submission=self.source, config_path=self.config)
            self.assertEqual(server.seen, [])

    def test_offline_validation_accepts_041_archive_without_network_or_rewriting(self):
        with base.fake_server() as server:
            self.bind(server)
            self.assertEqual(self.invoke(server)[0], 0)
        archive = self.archives()[0]
        rec = p.read_json(archive / "submission.json")
        rec["runner_version"], rec["status"] = "0.4.1", "graph_received_focus_checked"
        rec.pop("expected_target", None)
        rec["validation"].pop("expected_target", None)
        rec["validation"].pop("target_binding", None)
        p.write_json(archive / "submission.json", rec)
        p.write_json(archive / "checksums.json", {f.name: a.file_hash(f) for f in archive.iterdir() if f.name != "checksums.json"})
        before = {str(f): f.read_bytes() for f in self.run.rglob("*") if f.is_file()}
        out = io.StringIO()
        with patch.object(a, "Client") as client, patch.object(k.webbrowser, "open") as browser, \
             patch("builtins.input") as inp, patch.object(a, "api_key_prompt") as key, contextlib.redirect_stdout(out):
            self.assertEqual(k.validate_saved(self.run, archive, analyze=p.analyze, config_path=self.config), 0)
        client.assert_not_called(); browser.assert_not_called(); inp.assert_not_called(); key.assert_not_called()
        for name, data in before.items(): self.assertEqual(Path(name).read_bytes(), data)
        reports = list((self.run / "kumu-validations").glob("*/validation.json"))
        self.assertEqual(len(reports), 1)
        result = p.read_json(reports[0])
        self.assertEqual(result["status"], "validation_passed")
        self.assertEqual(result["original_graph_status"], "graph_received_focus_checked")
        self.assertEqual(result["network_requests"], 0)
        self.assertTrue(result["source_files_unchanged"])
        self.assertIn("Offline Kumu validation: PASSED", out.getvalue())

    def test_offline_validation_rejects_wrong_private_target_and_keeps_original_reply(self):
        with base.fake_server() as server:
            self.bind(server)
            self.assertEqual(self.invoke(server)[0], 0)
        archive = self.archives()[0]
        raw = (archive / "response.json").read_bytes()
        p.write_json(self.config, {**TARGET, "expected_project_id": "different-expected-project"})
        with patch.object(a, "Client") as client, patch.object(k.webbrowser, "open") as browser, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(k.validate_saved(self.run, archive, analyze=p.analyze, config_path=self.config), 2)
        client.assert_not_called(); browser.assert_not_called()
        report = p.read_json(next((self.run / "kumu-validations").glob("*/validation.json")))
        self.assertEqual(report["status"], "validation_failed")
        self.assertIn("independently configured", report["rejection_reason"])
        self.assertEqual((archive / "response.json").read_bytes(), raw)

    def test_offline_cli_routes_without_scans_or_paid_calls(self):
        with patch.object(sys, "argv", ["playbook.py", "kumu-validate", "--run-dir", str(self.run),
                                         "--graph-dir", str(self.source), "--kumu-config", str(self.config)]), \
             patch.object(k, "validate_saved", return_value=0) as check, patch.object(k, "generate") as paid, patch.object(p, "execute") as scan:
            self.assertEqual(p.main(), 0)
            check.assert_called_once_with(self.run, self.source, analyze=p.analyze, config_path=self.config)
            paid.assert_not_called(); scan.assert_not_called()

    def test_no_id_no_saved_submission_and_noninteractive_start_no_requests(self):
        with patch("builtins.input") as inp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(k.choose_ids("No supported mapping.", self.source), [])
            inp.assert_not_called()
        with patch("sys.stdin.isatty", return_value=False), self.assertRaises(a.AtlasError):
            k.generate(self.run, analyze=p.analyze)
        empty = self.root / "empty"; empty.mkdir()
        with self.assertRaises(a.AtlasError): k.choose_submission(empty)
        with self.assertRaises(a.AtlasError): k.choose_submission(self.run, self.root)

    def test_menu_and_cli_routes_do_not_scan_or_regenerate_and_yes_is_rejected(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="5"), \
             patch.object(k, "generate", return_value=0) as generate, patch.object(p, "execute") as scan, contextlib.redirect_stdout(io.StringIO()):
            p.present_results(self.run, self.summary, interactive=True)
            generate.assert_called_once_with(self.run.resolve(), analyze=p.analyze)
            scan.assert_not_called()
        with patch.object(k, "generate") as generate, patch("builtins.input") as inp, contextlib.redirect_stdout(io.StringIO()):
            p.present_results(self.run, self.summary, interactive=False)
            generate.assert_not_called(); inp.assert_not_called()
        with patch.object(sys, "argv", ["playbook.py", "kumu", "--run-dir", str(self.run), "--submission", str(self.source)]), \
             patch.object(k, "generate", return_value=0) as generate, patch.object(p, "execute") as scan, patch.object(p, "regenerate_handoff") as regen:
            self.assertEqual(p.main(), 0)
            self.assertEqual(generate.call_args.kwargs["submission"], self.source)
            scan.assert_not_called(); regen.assert_not_called()
        with patch.object(sys, "argv", ["playbook.py", "kumu", "--run-dir", str(self.run), "--yes"]), \
             patch.object(k, "generate") as generate, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            p.main()
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
