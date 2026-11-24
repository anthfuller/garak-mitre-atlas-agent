"""Real subprocess/Garak batch with synthetic HTTP responses; no live model calls.

Requires the audited Garak/OpenAI packages on PYTHONPATH or installed locally.
Tests the actual parent->child secret pipe and independent native run artifacts.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import coverage_batch as b

BOOTSTRAP = '''import sys
sys.path.insert(0, RUNNER_ROOT)
def deny(event, args):
    if event in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto"):
        raise AssertionError("Offline integration forbids network")
sys.addaudithook(deny)
import httpx
import openai_worker as w
calls = 0
def response(request):
    global calls
    calls += 1
    if FAIL:
        return httpx.Response(401, json={"error":{"message":"synthetic authentication failure"}})
    return httpx.Response(200, headers={"x-request-id": "SYNTHETIC"}, json={
        "id":"SYNTHETIC", "object":"chat.completion", "created":1, "model":"gpt-5.6-sol",
        "choices":[{"index":0,"message":{"role":"assistant","content":"SYNTHETIC response"},"finish_reason":"stop"}],
        "usage":{"prompt_tokens":10,"completion_tokens":3,"total_tokens":13}})
original = w.run
w.run = lambda args,key: original(args,key,test_transport=httpx.MockTransport(response))
raise SystemExit(w.main())
'''


def main(fail=False, legacy=False):
    key = "sk-DUMMY-BATCH-PIPE-NOT-A-REAL-CREDENTIAL"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        cfg = {"schema_version":1, "garak_python":sys.executable, "evidence_root":str(root / "evidence"),
               "xdg_data_home":str(root / "data"), "targets":{p.openai_profile.NAME:dict(p.openai_profile.TARGET)}}
        old = None
        if legacy:
            old = p.new_folder(cfg, "scan")
            manifest = p.plan(cfg, p.openai_profile.NAME, "base64-32", old)
            manifest.update(process_status="interrupted", exit_code=None, runner_run_id=old.name)
            p.write_json(old / "manifest.json", manifest)
            (old / "console.log").write_text("SYNTHETIC legacy interrupted run; summary never written.")
            old_bytes = {str(path.relative_to(old)): path.read_bytes() for path in old.rglob("*") if path.is_file()}
        script = root / "mock_worker.py"
        script.write_text(BOOTSTRAP.replace("RUNNER_ROOT", repr(str(p.ROOT))).replace("FAIL", repr(fail)))
        args = argparse.Namespace(action="batch", target=[p.openai_profile.NAME],
            probe=["probes.goodside.ThreatenJSON", "probes.goodside.WhoIsRiley"],
            completion_tokens=1500, request_cap=None, spending_alert=None, retry_failed=False)
        real_command = p.command
        def command(*values):
            result = real_command(*values)
            result[1] = str(script)
            return result
        with patch.object(p, "command", side_effect=command), patch.object(p.sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="RUN"), patch.object(p.openai_profile, "read_session_key", return_value=key):
            code = b.dispatch(args, cfg)
        batch = next(Path(cfg["evidence_root"]).glob("*-batch-*"))
        doc = p.read_json(batch / "batch.json")
        folders = [Path(item["folder"]) for item in doc["results"]]
        assert code == (2 if fail else 0), (code, doc)
        assert len(folders) == (1 if fail else 2)
        calls = 0
        for folder in folders:
            session = p.read_json(folder / "openai-session.json")
            calls += session["http_requests"]
            if not fail:
                assert (folder / "scan.report.jsonl").is_file()
                assert (folder / "atlas_handoff.md").is_file()
                assert p.read_json(folder / "summary.json")["execution_status"] == "completed"
        assert calls == (1 if fail else 9), calls
        if old is not None:
            assert not doc["history_read_errors"], doc["history_read_errors"]
            assert old_bytes == {str(path.relative_to(old)): path.read_bytes() for path in old.rglob("*") if path.is_file()}
            old_run = next(run for row in doc["rows"] for run in row["runs"] if run["evidence_folder"] == str(old))
            assert old_run["recorded_summary"] is None and not old_run["credited_live_evidence"]
            assert "summary.json missing" in (batch / "batch-summary.md").read_text()
        for path in root.rglob("*"):
            if path.is_file():
                assert key.encode() not in path.read_bytes(), str(path)
        assert len(doc["rows"]) == 191
        print(f"PASS batch real subprocess integration: fail={fail}; legacy_missing_summary={legacy}; {len(folders)} independent runs; {calls} synthetic HTTP responses; zero live model calls; key absent from artifacts.")


if __name__ == "__main__":
    main(fail="auth-failure" in sys.argv[1:], legacy="legacy-history" in sys.argv[1:])
