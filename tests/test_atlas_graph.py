"""Synthetic same-SEND analysis/graph checks. No external requests or browser."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_graph as g
import atlas_mcp as a
import kumu_mcp as k
import playbook as p
import research_index as research
import test_atlas_mcp as base
from test_kumu_mcp import envelope, response_for, TARGET


def reply(run_id="synthetic-run-only", ids=None, analysis=None):
    ids = ids or ["AML.T0068"]
    obj = envelope(run_id, ids)
    obj["analysis_markdown"] = analysis or "Candidate AML.T0068. Detector flag only; attack success unverified."
    return obj


class GraphReplyTests(unittest.TestCase):
    def inspect(self, obj):
        return g.describe_response(response_for(obj), "synthetic-run-only", TARGET)

    def test_full_url_and_all_discussed_ids_are_checked(self):
        ids = ["AML.T0068", "AML.M0001", "AML.T0054", "AML.TA0005", "AML.CS0001"]
        obj = reply(ids=ids, analysis="Candidate AML.T0068; related AML.M0001. Rejected AML.T0054. Context AML.TA0005 / AML.CS0001.")
        status, analysis, notes, check = self.inspect(obj)
        self.assertEqual(status, "response_received_unreviewed")
        self.assertEqual(check["status"], "graph_received_target_and_coverage_checked")
        self.assertEqual(check["discussed_ids"], ids)
        self.assertIn(obj["graph_result"]["url"], g.render_graph(check))
        self.assertEqual(check["browser_rendering"], "not_verified")
        self.assertIn("Rejected AML.T0054", analysis)

    def test_plain_url_sufficient_without_iframe(self):
        obj = reply()
        del obj["graph_result"]["iframe"]
        self.assertEqual(self.inspect(obj)[3]["status"], "graph_received_target_and_coverage_checked")

    def test_omitted_added_or_reordered_ids_fail_without_losing_analysis(self):
        for ids in (["AML.T0068"], ["AML.T0054", "AML.T0068"], ["AML.T0068", "AML.T0054", "AML.M0001"]):
            with self.subTest(ids=ids):
                obj = reply(ids=ids, analysis="Candidate AML.T0068; rejected AML.T0054.")
                status, analysis, _, check = self.inspect(obj)
                self.assertEqual(status, "response_received_unreviewed")
                self.assertEqual(analysis, obj["analysis_markdown"])
                self.assertEqual(check["status"], "graph_validation_failed")
                self.assertNotIn("url", check)

    def test_wrong_project_map_host_anchor_or_focus_is_rejected(self):
        for old, new in (("synthetic-project", "other-project"), ("#atlas/", "#other/"),
                         ("embed.kumu.io", "evil.invalid"), ("aml-t0068", "aml-t0054"),
                         ("focus=1", "focus=2"), ("https:", "http:"), ("focus=1", "focus=1&focus=1")):
            with self.subTest(change=new):
                obj = reply()
                obj["graph_result"]["url"] = obj["graph_result"]["url"].replace(old, new)
                check = self.inspect(obj)[3]
                self.assertEqual(check["status"], "graph_validation_failed")
                self.assertNotIn("url", check)

    def test_agent_reported_failure_retains_analysis_and_reason(self):
        obj = reply()
        obj["graph_result"] = {"status": "error", "url": "", "error": {"message": "Synthetic tool failure"}}
        _, analysis, _, check = self.inspect(obj)
        self.assertEqual(analysis, obj["analysis_markdown"])
        self.assertEqual(check["status"], "graph_generation_failed")
        self.assertIn("Synthetic tool failure", g.render_graph(check))

    def test_malformed_or_nontext_reply_preserves_available_analysis(self):
        plain = "Candidate AML.T0068. Graph tool unavailable."
        for response in ({"content": [{"type": "text", "text": plain}]},
                         {"content": [{"type": "text", "text": json.dumps(reply())}, {"type": "resource", "resource": {"uri": "https://do-not-fetch.invalid"}}]}):
            status, text, _, check = g.describe_response(response, "synthetic-run-only", TARGET)
            self.assertEqual(status, "response_received_unreviewed")
            self.assertIn("Candidate AML.T0068", text)
            self.assertEqual(check["status"], "graph_validation_failed")

    def test_conflicting_replies_preserve_both_analyses_without_selecting_graph(self):
        first, second = reply(), reply(analysis="Rejected AML.T0068; insufficient evidence.")
        response = {"content": [{"type": "text", "text": json.dumps(x)} for x in (first, second)]}
        _, analysis, _, check = g.describe_response(response, "synthetic-run-only", TARGET)
        self.assertIn("Candidate AML.T0068", analysis)
        self.assertIn("Rejected AML.T0068", analysis)
        self.assertEqual(check["status"], "graph_validation_failed")

    def test_blank_line_duplicate_is_displayed_once(self):
        analysis = "| ID | Interpretation |\n|---|---|\n| AML.T0068 | Candidate only |"
        first = reply(analysis=analysis)
        second = copy.deepcopy(first)
        second["analysis_markdown"] = analysis.replace("|\n|", "|\n\n|")
        response = {"content": [{"type": "text", "text": json.dumps(x)} for x in (second, first)]}
        _, text, _, check = g.describe_response(response, "synthetic-run-only", TARGET)
        self.assertEqual(text, analysis)
        self.assertEqual(check["status"], "graph_received_target_and_coverage_checked")

    def test_wrong_run_error_flag_missing_ids_and_invalid_modes_fail(self):
        for change in (lambda x: x.update(run_id="other"), lambda x: x.update(verified_ids=[]),
                       lambda x: x["graph_result"].update(focus_mode="all"),
                       lambda x: x["graph_result"].update(invalid_ids=["invalid"]),
                       lambda x: x.update(analysis_markdown="Evidence insufficient; no mapping."),
                       lambda x: x.update(analysis_markdown="Malformed AML.T00680.")):
            obj = reply(); change(obj)
            self.assertEqual(self.inspect(obj)[3]["status"], "graph_validation_failed")
        response = response_for(reply()); response["isError"] = True
        self.assertEqual(g.describe_response(response, "synthetic-run-only", TARGET)[3]["status"], "graph_validation_failed")

    def test_id_limit_case_and_uniqueness(self):
        self.assertEqual(g.analysis_ids("Candidate aml.t0068. Again AML.T0068."), ["AML.T0068"])
        with self.assertRaisesRegex(a.AtlasError, "more than 50"):
            g.analysis_ids(" ".join(f"AML.T{i:04d}" for i in range(51)))

    def test_default_binding_is_independent_of_returned_url(self):
        target = g.load_target()
        self.assertEqual(target["expected_project_id"], "99b02113875c5b03b510b4b6968b2566")
        self.assertEqual(target["expected_map_name"], "atlas")
        self.assertEqual(target["provenance"], "pinned_mitre_flow_default")


class SameSendTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base.AtlasTests(); self.fixture.setUp()
        self.run, self.root = self.fixture.run, self.fixture.root
        self.config = self.root / "kumu.private.json"
        p.write_json(self.config, TARGET)

    def tearDown(self):
        self.fixture.tearDown()

    def send(self, server, **kwargs):
        return self.fixture.send(server, include_graph=True, kumu_config=self.config, **kwargs)

    def test_one_send_saves_analysis_url_exact_request_raw_reply_and_source(self):
        obj = reply()
        response = response_for(obj)
        with base.fake_server() as server:
            server.result_builder = lambda request: response
            code, out = self.send(server)
            self.assertEqual(code, 0)
            self.assertEqual(len(server.calls), 1)
            archive = self.fixture.archives()[0]
            record = p.read_json(archive / "submission.json")
            self.assertEqual(record["automatic_retries"], 0)
            self.assertEqual(record["recorded_tool_call_attempts"], 1)
            self.assertEqual(record["request_format"], g.REQUEST_FORMAT)
            self.assertEqual(p.read_json(archive / "response.json"), response)
            handoff = (self.run / "atlas_handoff.md").read_bytes()
            self.assertEqual((archive / "handoff.submitted.md").read_bytes(), handoff)
            prompt = g.build_prompt(record["run_id"], handoff.decode(), record["expected_kumu_target"])
            self.assertEqual((archive / "request_prompt.md").read_bytes(), prompt.encode())
            self.assertEqual(server.calls[0]["params"]["arguments"]["input_value"], prompt)
            self.assertIn(json.dumps(handoff.decode(), ensure_ascii=True), prompt)
            markdown = (archive / "atlas_response.md").read_text()
            self.assertIn(obj["analysis_markdown"], markdown)
            self.assertIn(obj["graph_result"]["url"], markdown)
            self.assertIn("UNREVIEWED", markdown)
            self.assertIn("Kumu status: graph_received_target_and_coverage_checked", out)
            for name, checksum in p.read_json(archive / "checksums.json").items():
                self.assertEqual(p.sha(archive / name), checksum)
            saved, text, hashes = k.load_submission(archive.resolve(), self.fixture.summary, self.fixture.before)
            self.assertEqual(text, obj["analysis_markdown"])
            self.assertIn("request_prompt.md", hashes)
            self.assertFalse((self.run / "kumu-submissions").exists())
            prepared = research.prepare_record(SimpleNamespace(
                run_dir=self.run, atlas_submission=archive, graph_dir=None,
                graph_validation=None, screenshot=None))
            self.assertEqual(prepared["atlas"]["mentioned_ids"], ["AML.T0068"])
            self.assertIn("Candidate AML.T0068", prepared["search_document"])
            self.assertTrue(research.unchanged(prepared["evidence_references"]))

    def test_graph_failure_saves_analysis_returns_failure_and_never_retries(self):
        obj = reply(); obj["graph_result"]["url"] = "https://evil.invalid/"
        with base.fake_server() as server:
            server.result_builder = lambda request: response_for(obj)
            code, out = self.send(server)
            self.assertEqual(code, 2)
            self.assertEqual(len(server.calls), 1)
            archive = self.fixture.archives()[0]
            markdown = (archive / "atlas_response.md").read_text()
            self.assertIn(obj["analysis_markdown"], markdown)
            self.assertIn("Kumu graph unavailable", markdown)
            self.assertNotIn("https://evil.invalid/", markdown)
            self.assertEqual(p.read_json(archive / "submission.json")["status"], "response_received_unreviewed")

    def test_new_submission_never_changes_existing_archive(self):
        with base.fake_server() as server:
            server.result_builder = lambda request: response_for(reply())
            self.send(server)
            first = {path: path.read_bytes() for path in self.fixture.archives()[0].iterdir()}
            self.send(server)
            self.assertEqual(first, {path: path.read_bytes() for path in first})

    def test_cancel_or_auth_failure_never_calls_agent(self):
        with base.fake_server() as server:
            self.assertEqual(self.send(server, answer="")[0], 3)
            self.assertEqual(server.seen, [])
        with base.fake_server("auth_error") as server:
            self.assertEqual(self.send(server)[0], 2)
            self.assertEqual(server.calls, [])

    def test_changed_expected_destination_rejects_graph_after_response(self):
        def result(request):
            p.write_json(self.config, {**TARGET, "expected_map_name": "changed"})
            return response_for(reply())
        with base.fake_server() as server:
            server.result_builder = result
            code, out = self.send(server)
            self.assertEqual(code, 2)
            self.assertIn("configuration changed", out)
            self.assertEqual(len(server.calls), 1)

    def test_changed_request_prompt_is_rejected_when_reading_new_archive(self):
        with base.fake_server() as server:
            server.result_builder = lambda request: response_for(reply())
            self.send(server)
            archive = self.fixture.archives()[0]
            (archive / "request_prompt.md").write_text("changed")
            with self.assertRaisesRegex(a.AtlasError, "preserved prompt"):
                k.load_submission(archive.resolve(), self.fixture.summary, self.fixture.before)
