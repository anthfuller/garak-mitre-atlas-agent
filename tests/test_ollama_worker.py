"""Offline HTTP/control-flow tests. Fake SDK; real adapter checked separately."""
import base64
import io
import json
import os
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


def windows_denial(number=5):
    error = PermissionError(13, 'SYNTHETIC Windows file replacement denial')
    error.winerror = number
    return error


class SessionWriteTests(unittest.TestCase):
    """Fault injection, not evidence of native Windows filesystem behavior."""

    def test_transient_windows_denials_retry_only_complete_snapshot(self):
        for number in (5, 32, 33):
            with self.subTest(winerror=number), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'ollama-session.json'
                old = b'{"status":"scanning","http_requests":0}\n'
                path.write_bytes(old)
                value = {'status': 'scan_returned', 'text': 'exact café 漢字\nline 2'}
                expected = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                original_replace = os.replace
                pending = []

                def replace(source, destination):
                    self.assertEqual(destination, path)
                    self.assertEqual(path.read_bytes(), old)
                    self.assertEqual(Path(source).read_bytes(), expected)
                    pending.append(source)
                    if len(pending) <= 2:
                        raise windows_denial(number)
                    original_replace(source, destination)

                with patch.object(w.os, 'replace', side_effect=replace), \
                     patch.object(w.time, 'sleep') as sleep, patch('sys.stderr', new=io.StringIO()) as console:
                    w.save(path, value)
                self.assertEqual(path.read_bytes(), expected)
                self.assertEqual(len(set(pending)), 1)
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [0.05, 0.10])
                self.assertFalse(list(Path(tmp).glob('*.tmp')))
                self.assertIn('recovered after 2', console.getvalue())

    def test_persistent_denial_is_bounded_and_preserves_both_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ollama-session.json'
            old = b'original evidence\n'
            path.write_bytes(old)
            error = windows_denial()
            value = {'text': 'exact café 漢字\nline 2'}
            with patch.object(w.os, 'replace', side_effect=error) as replace, \
                 patch.object(w.time, 'sleep') as sleep, patch('sys.stderr', new=io.StringIO()):
                with self.assertRaises(PermissionError) as raised:
                    w.save(path, value)
            self.assertIs(raised.exception, error)
            self.assertEqual(replace.call_count, 6)
            self.assertEqual([c.args[0] for c in sleep.call_args_list], list(w.FILE_REPLACE_DELAYS))
            self.assertAlmostEqual(sum(c.args[0] for c in sleep.call_args_list), 1.55)
            self.assertEqual(path.read_bytes(), old)
            pending = list(Path(tmp).glob('*.tmp'))
            self.assertEqual(len(pending), 1)
            self.assertEqual(json.loads(pending[0].read_text(encoding='utf-8')), value)

    def test_other_file_errors_are_not_retried(self):
        for error in (PermissionError(13, 'SYNTHETIC non-Windows denial'),
                      windows_denial(112), FileNotFoundError('SYNTHETIC missing destination')):
            with self.subTest(error=repr(error)), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'ollama-session.json'
                with patch.object(w.os, 'replace', side_effect=error) as replace, \
                     patch.object(w.time, 'sleep') as sleep:
                    with self.assertRaises(type(error)):
                        w.save(path, {'status': 'scanning'})
                self.assertEqual(replace.call_count, 1)
                sleep.assert_not_called()


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

    def test_recovered_response_save_does_not_repeat_http(self):
        original_replace = os.replace
        denied, requests = [], []
        raw = b'{"message":{"content":"SYNTHETIC exact response"},"done":true}'

        def replace(source, destination):
            # Initial save + request save succeed; deny only response publication.
            transport = self.root / 'ollama-transport.jsonl'
            if transport.exists() and len(self.rows()) == 2 and len(denied) < 2:
                denied.append(source)
                raise windows_denial()
            original_replace(source, destination)

        def response(request):
            requests.append(request.read())
            return httpx.Response(200, content=raw)

        with patch.object(w.os, 'replace', side_effect=replace), patch.object(w.time, 'sleep'):
            code, console = self.invoke(response)
        self.assertEqual((code, len(requests), len(denied)), (0, 1, 2))
        self.assertEqual(json.loads(requests[0]), self.payload)
        self.assertEqual(base64.b64decode(self.rows()[1]['body_base64']), raw)
        self.assertEqual(p.read_json(self.root / 'ollama-session.json')['status'], 'scan_returned')
        self.assertEqual(w.quality_gaps(self.root), [])
        self.assertIn('No HTTP request repeated', console)

    def test_persistent_response_save_failure_stops_before_next_http(self):
        original_replace, original_run = os.replace, w.run
        denied, requests = [], []
        raw = b'{"message":{"content":"SYNTHETIC exact response"},"done":true}'

        def replace(source, destination):
            transport = self.root / 'ollama-transport.jsonl'
            if transport.exists() and len(self.rows()) >= 2:
                denied.append(source)
                raise windows_denial()
            original_replace(source, destination)

        def response(request):
            requests.append(request.read())
            return httpx.Response(200, content=raw)

        def scan(args):
            client = self.sdk.Client(host=self.endpoint, timeout=120)
            client.chat(**self.payload)
            client.chat(**self.payload)  # Must never be reached.

        with patch.dict(sys.modules, {'ollama': self.sdk}), patch.dict('os.environ', {}, clear=True), \
             patch.object(w.os, 'replace', side_effect=replace), patch.object(w.time, 'sleep'), \
             patch('sys.stderr', new=io.StringIO()), \
             patch.object(w, 'run', side_effect=lambda args: original_run(
                 args, test_transport=httpx.MockTransport(response), scan=scan)):
            code = w.main(self.args)
        self.assertEqual((code, len(requests)), (2, 1))
        # Six replacement attempts each for response snapshot and final failure snapshot.
        self.assertEqual(len(denied), 12)
        self.assertEqual(base64.b64decode(self.rows()[1]['body_base64']), raw)
        self.assertEqual(p.read_json(self.root / 'ollama-session.json')['status'], 'scanning')
        self.assertTrue(w.quality_gaps(self.root))
        self.assertEqual(len(list(self.root.glob('ollama-session.json.*.tmp'))), 2)
        self.assertIs(self.sdk.Client, FakeClient)

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
        self.assertEqual(self.manifest['ollama_session_write_policy'], w.FILE_WRITE_POLICY)
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
