"""Real embedded Chroma 1.5.9 with synthetic evidence/vectors. No real LLM or Windows UI."""
import argparse
import contextlib
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research_index as r
import playbook as p
import atlas_mcp as a
import test_kumu_mcp as kg


class FakeOllama:
    calls = 0
    digest = "a" * 64

    def __init__(self, cfg):
        self.requests = []

    def identity(self):
        return {"model": "embeddinggemma:latest", "digest": self.digest, "endpoint": "http://127.0.0.1:11434",
                "embedding_policy": "explicit_api_embed_raw_text_truncate_false_v1"}

    def embed(self, text):
        type(self).calls += 1
        self.requests.append({"route": "/api/embed", "synthetic": True})
        # Deterministic synthetic vectors test plumbing, not semantic quality.
        return [1.0, 0.2, 0.3] if "base64" in text.lower() else [0.2, 1.0, 0.1]


@unittest.skipUnless(importlib.util.find_spec("chromadb"), "Requires isolated chromadb==1.5.9 test interpreter")
class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = kg.KumuTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.run = self.fixture.run
        self.source = self.fixture.source
        p.write_json(self.source / "submission.json", self.fixture.saved)
        self.fixture.rehash()
        self.cfg = {"schema_version": 1, "python": sys.executable, "storage_root": str(self.root / "research"),
                    "ollama_endpoint": "http://127.0.0.1:11434", "embedding_model": "embeddinggemma:latest"}
        self.config = self.root / "research.private.json"
        p.write_json(self.config, self.cfg)
        self.args = argparse.Namespace(run_dir=self.run, atlas_submission=self.source, graph_dir=None,
                                       graph_validation=None, screenshot=None)
        self.before = {str(x): x.read_bytes() for x in self.run.rglob("*") if x.is_file()}
        FakeOllama.calls = 0
        self.fake = patch.object(r, "Ollama", FakeOllama)
        self.fake.start()
        self.clients = []
        native_client = r.client
        def tracked_client(cfg):
            db = native_client(cfg)
            self.clients.append(db)
            return db
        self.client_patch = patch.object(r, "client", side_effect=tracked_client)
        self.client_patch.start()
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None)
        self.fake.stop()
        self.client_patch.stop()
        for db in reversed(self.clients):
            db.close()  # Public Chroma 1.5.9 API; release SQLite handles before Windows cleanup.
        self.fixture.tearDown()

    def db_collection(self):
        return r.collection(r.client(self.cfg), FakeOllama(self.cfg).identity(), False)

    def receipt(self):
        files = list((self.root / "research" / "receipts").glob("*.json"))
        return sorted([a.read_json(f) for f in files], key=lambda x: x["created_at"])[-1]

    def test_index_twice_exact_counts_no_duplicates_no_second_embedding(self):
        self.assertEqual(r.index(self.args, self.cfg), 0)
        self.assertEqual(r.index(self.args, self.cfg), 0)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "unchanged")
        self.assertEqual(receipt["collection_count_before"], 1)
        self.assertEqual(receipt["collection_count_after"], 1)
        self.assertTrue(receipt["original_evidence_unchanged"])
        self.assertEqual(FakeOllama.calls, 1)
        c = self.db_collection()
        row = c.get(include=["metadatas", "documents"])
        record = r.read_record(Path(self.cfg["storage_root"]), row["metadatas"][0])
        self.assertEqual(record["evaluated_response_count"], 31)
        self.assertEqual(record["flagged_response_count"], 28)
        self.assertEqual(record["summary"]["detectors"][0]["unscorable"], 1)
        self.assertEqual(record["execution_status"], "complete_with_gaps")
        self.assertEqual(record["atlas"]["review_status"], "unreviewed")
        self.assertEqual(record["attack_success"], "unverified")
        self.assertEqual(record["search_document"], row["documents"][0])
        for path, raw in self.before.items():
            self.assertEqual(Path(path).read_bytes(), raw)

    def test_revision_preserved_when_screenshot_reference_added(self):
        r.index(self.args, self.cfg)
        first = self.receipt()
        screenshot = self.root / "synthetic.png"
        screenshot.write_bytes(b"synthetic reference only, not an image render test")
        self.args.screenshot = [screenshot]
        r.index(self.args, self.cfg)
        second = self.receipt()
        self.assertEqual(second["status"], "updated_revision")
        self.assertEqual(second["collection_count_after"], 1)
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertTrue(Path(first["record_path"]).is_file())
        self.assertTrue(Path(second["record_path"]).is_file())
        r.index(self.args, self.cfg)
        self.assertEqual(self.receipt()["status"], "unchanged")

    def test_search_filters_and_no_match_does_not_embed(self):
        r.index(self.args, self.cfg)
        c = self.db_collection()
        original = c.get(include=["metadatas", "documents"])
        # Distinct, explicitly synthetic distractor with a matching revision snapshot.
        record = r.read_record(Path(self.cfg["storage_root"]), original["metadatas"][0])
        record.update(run_id="synthetic-other-run", model="other:only", probe="encoding.InjectBase64")
        meta = dict(original["metadatas"][0], run_id=record["run_id"], model=record["model"], probe=record["probe"])
        revision = a.digest(r.encoded(record))
        snapshot = Path(self.cfg["storage_root"]) / "records" / "synthetic-other" / (revision + ".json")
        r.save_new(snapshot, record)
        meta.update(revision=revision, record_path=str(snapshot))
        c.add(ids=["run:synthetic-other-run"], embeddings=[[1.0, 0.2, 0.3]], documents=[record["search_document"]], metadatas=[meta])
        args = argparse.Namespace(query="roleplay jailbreak attempts", model=None, probe=None, limit=5)
        r.search(args, self.cfg)
        self.assertEqual(len(self.receipt()["results"]), 2)
        for model, probe in [("synthetic:only", None), (None, "dan.DanInTheWild"), ("synthetic:only", "dan.DanInTheWild")]:
            args.model, args.probe = model, probe
            r.search(args, self.cfg)
            self.assertEqual([x["run_id"] for x in self.receipt()["results"]], ["synthetic-run-only"])
        args.model = "does-not-exist"
        before = FakeOllama.calls
        r.search(args, self.cfg)
        self.assertEqual(self.receipt()["results"], [])
        self.assertEqual(FakeOllama.calls, before)

    def test_refuse_existing_nonempty_db_and_preserve_files(self):
        root = Path(self.cfg["storage_root"])
        root.mkdir()
        existing = root / "chroma.sqlite3"
        existing.write_bytes(b"existing unrelated database")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            r.index(self.args, self.cfg)
        self.assertEqual(existing.read_bytes(), b"existing unrelated database")

    def test_digest_change_rejected_without_new_embedding(self):
        r.index(self.args, self.cfg)
        with patch.object(FakeOllama, "digest", "b" * 64), self.assertRaisesRegex(ValueError, "digest/policy"):
            r.index(self.args, self.cfg)
        self.assertEqual(FakeOllama.calls, 1)

    def test_corrupted_original_rejected_before_database_creation(self):
        (self.run / "scan.report.jsonl").write_text("modified")
        with self.assertRaises(a.AtlasError):
            r.index(self.args, self.cfg)
        self.assertFalse(Path(self.cfg["storage_root"]).exists())

    def test_source_change_during_embedding_prevents_insert(self):
        def changed(instance, text):
            (self.run / "atlas_handoff.md").write_text("changed")
            return [0.1, 0.2, 0.3]
        with patch.object(FakeOllama, "embed", changed), self.assertRaisesRegex(ValueError, "changed before insertion"):
            r.index(self.args, self.cfg)
        self.assertEqual(self.db_collection().count(), 0)

    def test_missing_original_visible_on_search_and_open_rejected(self):
        r.index(self.args, self.cfg)
        (self.run / "summary.json").unlink()
        r.search(argparse.Namespace(query="roleplay", model=None, probe=None, limit=5), self.cfg)
        self.assertFalse(self.receipt()["results"][0]["source_hashes_match"])
        with patch.object(r.subprocess, "Popen") as editor, self.assertRaises(ValueError):
            r.open_evidence(argparse.Namespace(run_id="synthetic-run-only", evidence="summary"), self.cfg)
        editor.assert_not_called()

    def test_notepad_is_explicit_and_stdio_isolated_mocked_windows(self):
        r.index(self.args, self.cfg)
        # Only mock the platform check after pathlib has resolved its concrete class.
        with patch.object(r, "os", wraps=os) as platform, patch.object(r.subprocess, "Popen") as editor:
            platform.name = "nt"
            with patch.object(r.subprocess, "DETACHED_PROCESS", 8, create=True), patch.object(r.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, create=True):
                r.open_evidence(argparse.Namespace(run_id="synthetic-run-only", evidence="summary"), self.cfg)
        args, kw = editor.call_args
        self.assertEqual(Path(args[0][0]).name, "notepad.exe")
        self.assertEqual(args[0][1], str(self.run / "summary.json"))
        for stream in ("stdin", "stdout", "stderr"):
            self.assertEqual(kw[stream], r.subprocess.DEVNULL)

    def test_graph_reference_is_candidate_and_bound_to_saved_validation(self):
        folder = self.run / "kumu-submissions" / "synthetic-graph"
        folder.mkdir(parents=True)
        gr = {"run_id": "synthetic-run-only", "source_submission_id": self.fixture.saved["submission_id"], "selected_ids": kg.IDS}
        p.write_json(folder / "submission.json", gr)
        p.write_json(folder / "response.json", kg.response_for(kg.envelope(gr["run_id"], kg.IDS)))
        (folder / "kumu_url.txt").write_text(kg.envelope(gr["run_id"], kg.IDS)["graph_result"]["url"])
        p.checksums(folder)
        vfolder = self.run / "kumu-validations" / "synthetic-validation"
        vfolder.mkdir(parents=True)
        report = {"run_id": gr["run_id"], "graph_archive": str(folder), "status": "validation_passed",
                  "selected_ids": kg.IDS, "source_files_unchanged": True, "expected_target": kg.TARGET,
                  "graph_files_sha256": {x.name: a.file_hash(x) for x in folder.iterdir()}}
        p.write_json(vfolder / "validation.json", report)
        p.checksums(vfolder)
        self.args.graph_dir, self.args.graph_validation = folder, vfolder / "validation.json"
        r.index(self.args, self.cfg)
        record = a.read_json(Path(self.receipt()["record_path"]))
        self.assertEqual(record["graph"]["selected_ids"], kg.IDS)
        self.assertEqual(record["graph"]["mapping_status"], "candidate_pending_analyst_review")
        self.assertIn("not_independently", record["graph"]["browser_rendering"])
        report["run_id"] = "wrong-run"
        p.write_json(vfolder / "validation.json", report)
        p.checksums(vfolder)
        with self.assertRaisesRegex(ValueError, "not a passing"):
            r.index(self.args, self.cfg)

    def test_runner_routes_to_research_python_without_scan(self):
        argv = ["research-search", "--research-config", str(self.config), "--query", "roleplay"]
        args = argparse.Namespace(research_config=self.config)
        with patch.object(r.subprocess, "run") as child:
            child.return_value.returncode = 0
            self.assertEqual(r.launch(args, argv), 0)
        command = child.call_args.args[0]
        self.assertEqual(command[0], str(Path(sys.executable).absolute()))
        self.assertEqual(command[2:], argv)

    def test_actual_runner_worker_cli_real_chroma_fake_local_ollama(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.reply({"version": "synthetic-only"} if self.path == "/api/version" else
                           {"models": [{"name": "embeddinggemma:latest", "digest": "c" * 64}]})
            def do_POST(self):
                seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.reply({"model": "embeddinggemma:latest", "embeddings": [[0.1, 0.2, 0.3]], "prompt_eval_count": 5})
            def reply(self, obj):
                raw = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.cfg["ollama_endpoint"] = "http://127.0.0.1:" + str(server.server_port)
                p.write_json(self.config, self.cfg)
                cmd = [sys.executable, str(Path(p.__file__)), "research-index", "--research-config", str(self.config),
                       "--run-dir", str(self.run), "--atlas-submission", str(self.source)]
                for expected in ("Research index: indexed", "Research index: unchanged"):
                    result = r.subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    self.assertIn(expected, result.stdout)
                self.assertEqual(len(seen), 1)
                cmd = cmd[:2] + ["research-search", "--research-config", str(self.config), "--query", "roleplay jailbreak",
                                  "--model", "synthetic:only", "--probe", "dan.DanInTheWild"]
                result = r.subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn("Found 1 of 1 matching indexed runs", result.stdout)
                self.assertEqual(len(seen), 2)
            finally:
                server.shutdown()
                thread.join()


class LocalHTTPTests(unittest.TestCase):
    def test_embed_request_truncation_disabled_and_digest_recorded(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.reply({"version": "synthetic-only"} if self.path == "/api/version" else
                           {"models": [{"name": "embeddinggemma:latest", "digest": "a" * 64}]})
            def do_POST(self):
                seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.reply({"model": "embeddinggemma:latest", "embeddings": [[0.1, 0.2, 0.3]], "prompt_eval_count": 5})
            def reply(self, obj):
                raw = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                o = r.Ollama({"ollama_endpoint": "http://127.0.0.1:" + str(server.server_port), "embedding_model": "embeddinggemma:latest"})
                self.assertEqual(o.identity()["digest"], "a" * 64)
                self.assertEqual(o.embed("synthetic only"), [0.1, 0.2, 0.3])
                self.assertEqual(seen, [{"model": "embeddinggemma:latest", "input": "synthetic only", "truncate": False}])
            finally:
                server.shutdown()
                thread.join()

    def test_invalid_embedding_values_rejected(self):
        o = r.Ollama({"ollama_endpoint": "http://127.0.0.1:11434", "embedding_model": "embeddinggemma:latest"})
        for vectors in ([], [[float("nan")]], [[0, 0]], [[True]], [[1], [2]]):
            with patch.object(o, "call", return_value={"model": o.model, "embeddings": vectors}), self.assertRaises(ValueError):
                o.embed("test")


if __name__ == "__main__":
    unittest.main()
