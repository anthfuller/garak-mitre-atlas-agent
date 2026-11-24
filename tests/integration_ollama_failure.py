"""Real Garak 0.17.0 + synthetic local server: fail at request 23, no retries.

No real model, paid API, GPU, or live Ollama server is used.
"""
import base64
import contextlib
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import coverage_batch as b
from integration_stub import Handler

ERROR_BODY = b'{"error":"SYNTHETIC failure at request 23"}\n'


class FailAt23(Handler):
    requests = []

    def do_POST(self):
        if self.path != '/api/chat':
            return super().do_POST()
        raw = self.rfile.read(int(self.headers['Content-Length']))
        self.requests.append(raw)
        if len(self.requests) == 23:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(ERROR_BODY)))
            self.end_headers()
            self.wfile.write(ERROR_BODY)
        else:
            self.respond({'model': 'synthetic:only', 'message': {'role': 'assistant', 'content': 'SYNTHETIC response'}, 'done': True})


def main():
    FailAt23.requests.clear()
    server = ThreadingHTTPServer(('127.0.0.1', 0), FailAt23)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {'schema_version': 1, 'garak_python': sys.executable,
                   'evidence_root': str(Path(tmp) / 'evidence'), 'xdg_data_home': str(Path(tmp) / 'data'),
                   'targets': {'synthetic': {'provider': 'ollama', 'model': 'synthetic:only',
                       'endpoint': f'http://127.0.0.1:{server.server_port}'}}}
            captured = io.StringIO()
            start = time.monotonic()
            with contextlib.redirect_stdout(captured):
                result = p.run_selected(cfg, 'synthetic', 'dan-wild-32')
            elapsed = time.monotonic() - start
            folder = Path(result['folder'])
            manifest = result['manifest']
            summary = result['summary']
            session = p.read_json(folder / 'ollama-session.json')
            rows = [json.loads(line) for line in (folder / 'ollama-transport.jsonl').read_text().splitlines()]
            assert len(FailAt23.requests) == 23, len(FailAt23.requests)
            assert session['status'] == 'failed' and session['http_requests'] == 23, session
            assert base64.b64decode(rows[-1]['body_base64']) == ERROR_BODY
            assert manifest['process_status'] == 'exited' and manifest['exit_code'] == 2, manifest
            assert summary['execution_status'] == 'incomplete', summary
            assert elapsed < 60, elapsed
            assert (folder / 'atlas_handoff.md').is_file()
            assert 'HTTP 500' in captured.getvalue(), captured.getvalue()
            assert 'HTTP 500' in b.stop_reason(result)
            reconciled = b.read_run(folder)
            assert not reconciled['integrity_warnings'], reconciled['integrity_warnings']
            assert reconciled['diagnostics']['http_statuses'] == {'200': 22, '500': 1}
            # Every server-received body was retained exactly; no extra requests.
            recorded = [r for r in rows if r['entry_type'] == 'request']
            assert [base64.b64decode(r['body_base64']) for r in recorded] == FailAt23.requests
            for raw in FailAt23.requests:
                body = json.loads(raw)
                assert body['options']['num_predict'] == 256 and body['options']['temperature'] == 0.0 and body['options']['seed'] == 42
            print(json.dumps({'status': 'passed', 'synthetic_http_requests': 23, 'success_responses': 22,
                'error_responses': 1, 'error_retries': 0, 'execution_status': summary['execution_status'],
                'process_exit_code': manifest['exit_code'], 'elapsed_seconds': round(elapsed, 3),
                'exact_request_and_error_bytes_preserved': True, 'original_generation_options_preserved': True,
                'live_models': False, 'platform': sys.platform}, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
