"""Offline HTTP/control-flow tests. Fake SDK; real adapter checked separately."""
import base64
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ollama_worker as w
import playbook as p
import coverage_batch as b


class FakeClient:
    def __init__(self, host, **kwargs):
        self.client = httpx.Client(base_url=host, **kwargs)

    def chat(self, **payload):
        return self.client.post('/api/chat', json=payload)


class OllamaWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.endpoint = 'http://127.0.0.1:11434'
        self.cfg = {'schema_version': 1, 'garak_python': sys.executable,
                    'evidence_root': str(self.root / 'evidence'), 'xdg_data_home': str(self.root / 'data'),
                    'targets': {'local': {'provider': 'ollama', 'model': 'synthetic:only', 'endpoint': self.endpoint}}}
        self.manifest = p.plan(self.cfg, 'local', 'dan-wild-32', self.root)
        p.write_json(self.root / 'garak-config.json', self.manifest['resolved_garak_config'])
        self.args = self.manifest['command_argv'][2:]
        self.sdk = types.ModuleType('ollama')
        self.sdk.Client = FakeClient
        self.payload = {'model': 'synthetic:only', 'messages': [{'role': 'user', 'content': 'EXACT\nsynthetic π'}],
                        'options': {'temperature': 0.0, 'num_predict': 256, 'seed': 42}, 'stream': False}

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, response, scan=None):
        def default_scan(args):
            client = self.sdk.Client(host=self.endpoint, timeout=120)
            client.chat(**self.payload)
        with patch.dict(sys.modules, {'ollama': self.sdk}), patch.dict('os.environ', {}, clear=True), \
             patch('sys.stderr', new=io.StringIO()) as out:
            code = w.run(self.args, test_transport=httpx.MockTransport(response), scan=scan or default_scan)
        self.assertIs(self.sdk.Client, FakeClient)
        return code, out.getvalue()

    def rows(self):
        return [json.loads(line) for line in (self.root / 'ollama-transport.jsonl').read_text().splitlines()]

    def test_http_500_aborts_retry_wrapper_once_and_preserves_error_bytes(self):
        raw = b'{"error":"SYNTHETIC server failure\\nwith details"}\n'
        calls = []
        def response(request):
            calls.append(request)
            return httpx.Response(500, content=raw)
        def scan(args):
            client = self.sdk.Client(host=self.endpoint, timeout=120)
            # Emulate an Exception-based retry boundary. AbortRun must escape it.
            for _ in range(5):
                try:
                    client.chat(**self.payload)
                except Exception:
                    continue
        code, console = self.invoke(response, scan)
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 1)
        self.assertIn('HTTP 500', console)
        self.assertIn('SYNTHETIC server failure', console)
        self.assertEqual(base64.b64decode(self.rows()[1]['body_base64']), raw)
        self.assertEqual(p.read_json(self.root / 'ollama-session.json')['status'], 'failed')
        self.assertTrue(any('HTTP 500' in s for s in w.quality_gaps(self.root)))

    def test_success_retains_exact_request_and_response(self):
        raw = '{"model":"synthetic:only","message":{"role":"assistant","content":"A\\nπ"},"done":true,"done_reason":"stop"}'.encode()
        requests, received = [], []
        def response(request):
            requests.append(request.read())
            return httpx.Response(200, content=raw)
        def scan(args):
            client = self.sdk.Client(host=self.endpoint, timeout=120)
            received.append(client.chat(**self.payload).content)
        code, _ = self.invoke(response, scan)
        self.assertEqual(code, 0)
        self.assertEqual(received, [raw])
        self.assertEqual(json.loads(requests[0]), self.payload)
        rows = self.rows()
        self.assertEqual(base64.b64decode(rows[0]['body_base64']), requests[0])
        self.assertEqual(base64.b64decode(rows[1]['body_base64']), raw)
        self.assertEqual(w.quality_gaps(self.root), [])

    def test_timeout_stops_without_retry(self):
        calls = []
        def response(request):
            calls.append(request)
            raise httpx.ReadTimeout('SYNTHETIC timeout', request=request)
        code, text = self.invoke(response)
        self.assertEqual((code, len(calls)), (2, 1))
        self.assertIn('ReadTimeout', text)
        self.assertEqual(self.rows()[1]['entry_type'], 'transport_error')

    def test_body_read_timeout_is_recorded(self):
        class BrokenBody(httpx.SyncByteStream):
            def __iter__(self):
                raise httpx.ReadTimeout('SYNTHETIC body timeout')
                yield b''
        code, _ = self.invoke(lambda request: httpx.Response(200, stream=BrokenBody()))
        self.assertEqual(code, 2)
        self.assertEqual(self.rows()[1]['error_type'], 'ReadTimeout')

    def test_redirect_not_followed(self):
        calls = []
        def response(request):
            calls.append(request)
            return httpx.Response(302, headers={'Location': 'https://example.invalid/'}, content=b'')
        self.assertEqual(self.invoke(response)[0], 2)
        self.assertEqual(len(calls), 1)

    def test_non_json_error_body_is_lossless(self):
        raw = b'SYNTHETIC \xff error'
        self.assertEqual(self.invoke(lambda r: httpx.Response(500, content=raw))[0], 2)
        self.assertEqual(base64.b64decode(self.rows()[1]['body_base64']), raw)

    def test_wrong_model_blocked_before_http(self):
        self.payload['model'] = 'wrong:only'
        self.assertEqual(self.invoke(lambda r: self.fail('No HTTP request allowed'))[0], 2)
        self.assertEqual(p.read_json(self.root / 'ollama-session.json')['http_requests'], 0)

    def test_unexpected_destination_blocked(self):
        def scan(args):
            client = self.sdk.Client(host='http://127.0.0.1:11435', timeout=120)
            client.chat(**self.payload)
        self.assertEqual(self.invoke(lambda r: self.fail('No HTTP request allowed'), scan)[0], 2)

    def test_operator_interrupt_preserved(self):
        def scan(args):
            raise KeyboardInterrupt
        self.assertEqual(self.invoke(lambda r: self.fail('No HTTP request allowed'), scan)[0], 130)
        self.assertEqual(p.read_json(self.root / 'ollama-session.json')['status'], 'interrupted')

    def test_local_plan_discloses_transport_change_before_run(self):
        self.assertTrue(self.manifest['command_argv'][1].endswith('ollama_worker.py'))
        self.assertIn('not an exact reproduction', self.manifest['experimental_effect'])
        self.assertEqual(self.manifest['resolved_garak_config']['plugins']['generators']['ollama']['OllamaGeneratorChat']['max_tokens'], 256)

    def test_batch_report_includes_local_http_error_without_response_text(self):
        self.invoke(lambda r: httpx.Response(500, json={'error': 'SYNTHETIC private payload'}))
        diag = b.transport_diagnostics(self.root)
        self.assertEqual(diag['http_statuses'], {'500': 1})
        self.assertEqual(diag['errors'][0]['http_status'], 500)
        self.assertNotIn('private payload', json.dumps(diag))

    def test_batch_completion_repeats_actionable_local_error(self):
        self.invoke(lambda r: httpx.Response(500, json={'error': 'SYNTHETIC cause'}))
        manifest = dict(self.manifest, process_status='exited', exit_code=2)
        reason = b.stop_reason({'manifest': manifest, 'folder': str(self.root)})
        self.assertIn('HTTP 500', reason)
        self.assertIn('SYNTHETIC cause', reason)

    def test_missing_outcome_is_gap(self):
        p.write_json(self.root / 'ollama-session.json', {'status': 'scanning', 'http_requests': 1})
        (self.root / 'ollama-transport.jsonl').write_text('{"entry_type":"request","sequence":1}\n')
        self.assertTrue(any('no unique recorded outcome' in s for s in w.quality_gaps(self.root)))


if __name__ == '__main__':
    unittest.main()
