"""Synthetic localhost-server tests. No Langflow/model calls or real credentials."""
import contextlib
import importlib.util
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import warnings

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "inspect_atlas_mcp.py"
spec = importlib.util.spec_from_file_location("inspect_atlas_mcp", SCRIPT)
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)
KEY = "dummy-key-NOT-A-CREDENTIAL-88291"
SESSION = "dummy-session-92713"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body=b"", kind="application/json", **headers):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_DELETE(self):
        self.server.seen.append(("DELETE", dict(self.headers), None))
        self.reply(204 if self.headers.get("x-api-key") == KEY else 403)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.seen.append(("POST", dict(self.headers), body))
        mode = self.server.mode
        if mode == "redirect":
            self.reply(307, Location=self.server.endpoint + "/other")
            return
        if mode in ("401", "403"):
            self.reply(int(mode), KEY.encode())
            return
        if mode != "anonymous" and self.headers.get("x-api-key") != KEY:
            self.reply(401)
            return
        method = body["method"]
        if method == "notifications/initialized":
            self.reply(202)
            return
        headers = {}
        if method == "initialize":
            result = {"protocolVersion": "wrong" if mode == "protocol" else mcp.PROTOCOL,
                      "serverInfo": {"name": "synthetic", "version": "test"},
                      "capabilities": {"tools": {}}}
            headers["Mcp-Session-Id"] = SESSION
        elif method == "tools/list":
            if mode == "rpc_error":
                self.reply(200, json.dumps({"jsonrpc": "2.0", "id": body["id"],
                    "error": {"code": -1, "message": KEY + " " + SESSION}}).encode())
                return
            page = 2 if body.get("params", {}).get("cursor") else 1
            result = {"tools": [{"name": "ATLAS_AGENT_V110" if page == 1 else "another_fixture",
                       "description": KEY + " " + SESSION if mode == "reflect" else "test only",
                       "inputSchema": {"type": "object", "properties": {"fixture_text": {"type": "string"}}}}]}
            if mode == "pages" and page == 1:
                result["nextCursor"] = "next"
            if mode == "repeat":
                result = {"tools": [], "nextCursor": "same"}
        else:
            raise AssertionError("Forbidden MCP method: " + method)
        response = {"jsonrpc": "2.0", "id": body["id"], "result": result}
        raw = json.dumps(response).encode()
        if mode == "sse":
            raw = (b'data: {"jsonrpc":"2.0","method":"notifications/message","params":{}}\n\n'
                   + b"data: " + raw + b"\n\n")
            self.reply(200, raw, kind="text/event-stream", **headers)
        else:
            self.reply(200, raw, **headers)


@contextlib.contextmanager
def server(mode):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.mode, srv.seen = mode, []
    srv.endpoint = f"http://127.0.0.1:{srv.server_port}/streamable"
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join()


class DiscoveryTests(unittest.TestCase):
    def run_main(self, url, key=KEY, key_prompt=True):
        with tempfile.TemporaryDirectory() as directory:
            argv = [str(SCRIPT), "--url", url, "--output-dir", directory]
            if key_prompt:
                argv.append("--api-key-prompt")
            output = io.StringIO()
            with patch("sys.argv", argv), patch.object(mcp.getpass, "getpass", return_value=key), contextlib.redirect_stdout(output):
                code = mcp.main()
            files = list(Path(directory).glob("*.json"))
            raw = files[0].read_text() if files else ""
        self.assertNotIn(KEY, raw + output.getvalue())
        self.assertNotIn(SESSION, raw + output.getvalue())
        return code, json.loads(raw) if raw else None, output.getvalue()

    def assert_methods(self, srv):
        for verb, headers, body in srv.seen:
            if body:
                self.assertIn(body["method"], mcp.ALLOWED_METHODS)
                self.assertNotIn(KEY, json.dumps(body))
                self.assertNotIn("tools/call", json.dumps(body))

    def test_authenticated_json_pages_and_cleanup(self):
        with server("pages") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 0)
            self.assertEqual(len(report["tools"]), 2)
            self.assertTrue(report["authentication_sent"])
            self.assertEqual(report["session_cleanup_http_status"], 204)
            for _, headers, _ in srv.seen:
                self.assertEqual({k.lower(): v for k, v in headers.items()}["x-api-key"], KEY)
            self.assert_methods(srv)

    def test_sse_notifications(self):
        with server("sse") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 0)
            self.assertEqual(report["tools"][0]["inputSchema"]["properties"], {"fixture_text": {"type": "string"}})
            self.assert_methods(srv)

    def test_metadata_reflection_redacted(self):
        with server("reflect") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 0)
            self.assertTrue(report["credential_redaction_applied"])
            self.assertEqual(report["tools"][0]["description"], "[REDACTED] [REDACTED]")

    def test_rpc_error_reflection_redacted(self):
        with server("rpc_error") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 2)
            self.assertEqual(report["status"], "incomplete")
            self.assertTrue(report["credential_redaction_applied"])

    def test_bad_credentials_stop_without_retry(self):
        for status in ("401", "403"):
            with self.subTest(status=status), server(status) as srv:
                code, report, _ = self.run_main(srv.endpoint)
                self.assertEqual(code, 2)
                self.assertEqual(len(srv.seen), 1)
                self.assertEqual(report["tool_invocations"], 0)
                self.assertIn("not accepted or lacks access", report["error"])

    def test_redirect_not_followed(self):
        with server("redirect") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 2)
            self.assertEqual(len(srv.seen), 1)
            self.assertIn("Redirect refused", report["error"])

    def test_invalid_urls_are_not_saved(self):
        for url in (f"http://{KEY}@localhost:7861/", f"http://localhost:7861/?key={KEY}",
                    "http://example.com:7861/", "http://localhost/path", "http://localhost:wrong/"):
            with self.subTest(url=url):
                code, report, _ = self.run_main(url)
                self.assertEqual(code, 2)
                self.assertIsNone(report)

    def test_cancel_sends_nothing(self):
        with server("pages") as srv, patch.object(mcp, "prompt_api_key", side_effect=KeyboardInterrupt):
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 2)
            self.assertEqual(srv.seen, [])
            self.assertFalse(report["authentication_sent"])

    def test_placeholder_blank_and_header_controls_send_nothing(self):
        with server("pages") as srv:
            for key in ("", "YOUR_API_KEY", "REDACTED", " key ", "dummy\r\nheader", "nonascii-\u00e9"):
                with self.subTest(key=key):
                    code, report, _ = self.run_main(srv.endpoint, key=key)
                    self.assertEqual(code, 2)
                    self.assertEqual(report["exchanges"], [])
            self.assertEqual(srv.seen, [])

    def test_getpass_fallback_fails_closed(self):
        def echo_unavailable(*args):
            warnings.warn("unavailable", mcp.getpass.GetPassWarning)
        with patch.object(mcp.getpass, "getpass", side_effect=echo_unavailable):
            with self.assertRaisesRegex(mcp.DiscoveryError, "Hidden input is unavailable"):
                mcp.prompt_api_key()

    def test_protocol_mismatch_is_incomplete(self):
        with server("protocol") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 2)
            self.assertEqual(report["status"], "incomplete")
            self.assertEqual([b["method"] for _, _, b in srv.seen if b], ["initialize"])

    def test_repeated_cursor_is_incomplete(self):
        with server("repeat") as srv:
            code, report, _ = self.run_main(srv.endpoint)
            self.assertEqual(code, 2)
            self.assertIn("repeated discovery cursor", report["error"])

    def test_anonymous_mode_remains_available(self):
        with server("anonymous") as srv:
            code, report, _ = self.run_main(srv.endpoint, key_prompt=False)
            self.assertEqual(code, 0)
            self.assertFalse(report["authentication_sent"])
            for _, headers, _ in srv.seen:
                self.assertNotIn("x-api-key", {k.lower() for k in headers})


if __name__ == "__main__":
    unittest.main(verbosity=2)
