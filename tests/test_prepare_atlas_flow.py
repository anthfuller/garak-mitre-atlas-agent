"""Offline setup checks with synthetic components; no Langflow or model calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "prepare_atlas_flow.py"
spec = importlib.util.spec_from_file_location("prepare_atlas_flow", SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def fixture():
    def node(kind, template):
        return {"id": kind, "data": {"type": kind, "node": {"template": template}}}
    model = {name: {"value": ""} for name in ("model_name", "api_base", "api_key", "model_kwargs")}
    model["code"] = {"value": "parameters = {" + prepare.OLD_PARAMETER + "}"}
    return {"name": "Synthetic flow", "data": {
        "nodes": [node("vLLMModel", model), node("Agent", {"instructions": {"value": "Preserve me"}}),
                  node("File", {"path": {"file_path": ["old-account/contract.md"], "value": "old"}}),
                  node("CSVPythonREPL", {"csv_file": {"file_path": "old-account/data.csv", "value": "old"},
                                         "code": {"value": "synthetic tool code"}})],
        "edges": [{"source": "vLLMModel", "target": "Agent"}], "viewport": {"zoom": 1}}}


class PrepareFlowTests(unittest.TestCase):
    def test_model_patch_preserves_original_tools_instructions_and_wires(self):
        original = fixture()
        before = copy.deepcopy(original)
        result = prepare.prepare(original)
        self.assertEqual(original, before)
        self.assertEqual(result["data"]["edges"], original["data"]["edges"])
        self.assertEqual(result["data"]["viewport"], original["data"]["viewport"])
        model = result["data"]["nodes"][0]["data"]["node"]["template"]
        self.assertIn('"use_responses_api": True', model["code"]["value"])
        self.assertIn('"reasoning_effort": "medium"', model["code"]["value"])
        self.assertNotIn('"temperature":', model["code"]["value"])
        self.assertEqual(model["model_name"]["value"], "gpt-6.1-sol")
        self.assertEqual(model["api_key"]["value"], "")
        self.assertEqual(result["data"]["nodes"][1], original["data"]["nodes"][1])
        self.assertEqual(result["data"]["nodes"][2]["data"]["node"]["template"]["path"]["file_path"], [])
        sandbox = result["data"]["nodes"][3]["data"]["node"]["template"]
        self.assertEqual(sandbox["code"]["value"], "synthetic tool code")
        self.assertEqual(sandbox["csv_file"]["file_path"], "")

    def test_existing_output_reused_only_if_identical_and_source_unchanged(self):
        document = fixture()
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        with tempfile.TemporaryDirectory() as folder, patch.object(prepare, "UPSTREAM_SHA256", hashlib.sha256(canonical).hexdigest()):
            source, output = Path(folder) / "source.json", Path(folder) / "output.json"
            source.write_text(json.dumps(document, indent=2), encoding="utf-8")
            before = source.read_bytes()
            prepare.prepare_file(source, output)
            saved = output.read_bytes()
            prepare.prepare_file(source, output)
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(source.read_bytes(), before)
            output.write_bytes(b"existing work")
            with self.assertRaisesRegex(ValueError, "different content"):
                prepare.prepare_file(source, output)
            self.assertEqual(output.read_bytes(), b"existing work")

    def test_unpinned_source_cannot_create_or_replace_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "source.json", Path(folder) / "output.json"
            source.write_text(json.dumps(fixture()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from MITRE revision"):
                prepare.prepare_file(source, output)
            self.assertFalse(output.exists())

    def test_missing_or_ambiguous_model_and_unexpected_code_are_rejected(self):
        original = fixture()
        for nodes in (original["data"]["nodes"][1:], original["data"]["nodes"] * 2):
            changed = copy.deepcopy(original)
            changed["data"]["nodes"] = nodes
            with self.assertRaisesRegex(ValueError, "one vLLM"):
                prepare.prepare(changed)
        original["data"]["nodes"][0]["data"]["node"]["template"]["code"]["value"] = "unexpected"
        with self.assertRaisesRegex(ValueError, "tested version"):
            prepare.prepare(original)
