"""Optional integration test: real Garak CLI + synthetic Ollama protocol server.

No real model is used. This is a runner/transport test, not adversarial evidence.
Run only in a test environment with Garak 0.17.0 and its required dependencies.
"""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p

requests_seen = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def respond(self, value):
        data = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/version":
            self.respond({"version": "synthetic-test-server"})
        elif self.path == "/api/tags":
            self.respond({"models": [{"name": "synthetic:only", "model": "synthetic:only", "digest": "0" * 64}]})
        else:
            self.send_error(404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            self.respond({"system": "SYNTHETIC FIXTURE", "template": "SYNTHETIC FIXTURE", "parameters": "SYNTHETIC FIXTURE"})
        elif self.path == "/api/chat":
            requests_seen.append(body)
            self.respond({"model": "synthetic:only", "message": {"role": "assistant", "content": "SYNTHETIC protocol-test reply. No real model was called."}, "done": True})
        else:
            self.send_error(404)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"schema_version": 1, "garak_python": sys.executable,
                   "evidence_root": str(Path(tmp) / "evidence"), "xdg_data_home": str(Path(tmp) / "data"),
                   "targets": {"synthetic": {"provider": "ollama", "model": "synthetic:only", "endpoint": f"http://127.0.0.1:{server.server_port}"}}}
            catalog = p.installed_inventory(cfg)
            selected = []
            for name, count in (("probes.encoding.InjectBase32", 32), ("probes.goodside.WhoIsRiley", 6),
                                ("probes.goodside.Tag", 32), ("probes.goodside.Davidjl", 4)):
                row = next(r for r in catalog["probes"] if r["name"] == name)
                selected.append((p.probe_catalog.campaign_for(row, cfg["targets"]["synthetic"], catalog), count))
            for campaign, expected_count in [("base64-32", 32), ("dan-wild-32", 32), *selected]:
                requests_seen.clear()
                before = set((Path(tmp) / "evidence").glob("*"))
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code = p.execute(cfg, "synthetic", campaign, yes=True)
                folder = (set((Path(tmp) / "evidence").glob("*")) - before).pop()
                summary = p.read_json(folder / "summary.json")
                if code != 0:
                    print(stream.getvalue())
                    print(json.dumps(summary, indent=2))
                    raise AssertionError("Synthetic integration failed")
                assert summary["attempts"] == expected_count, summary
                assert summary["valid_response_count"] == expected_count, summary
                assert len(requests_seen) == expected_count, len(requests_seen)
                if isinstance(campaign, dict):
                    manifest = p.read_json(folder / "manifest.json")
                    assert manifest["campaign"] == campaign
                    assert {d["probe"] for d in summary["detectors"]} == {campaign["spec"].removeprefix("probes.")}
                    assert {d["detector"] for d in summary["detectors"]} == {campaign["detector"]}
                for request in requests_seen:
                    assert request["options"]["num_predict"] == 256, request
                    assert request["options"]["temperature"] == 0.0, request
                    assert request["options"]["seed"] == 42, request
                    assert request["model"] == "synthetic:only"
                    assert request["messages"]
                assert (folder / "atlas_handoff.md").is_file()
                assert (folder / "checksums.json").is_file()
                console = stream.getvalue()
                assert str(folder / "atlas_handoff.md") in console
                assert f"evaluated responses {expected_count}; detector flags " in console
                assert "[3] Return to PowerShell" not in console  # --yes has no completion prompt.
                label = campaign["spec"] if isinstance(campaign, dict) else campaign
                print(f"PASS {label}: real Garak 0.17.0 CLI, synthetic protocol server, {expected_count} recorded requests; options and evidence outputs verified. No real model tested.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__": main()
