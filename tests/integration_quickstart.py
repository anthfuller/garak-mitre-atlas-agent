"""Exercise public configuration and plan commands with network access denied.

No model access, credentials or scanner generation. Intended for the clean
Windows checkout as well as the Builder's Linux preparation check.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import runpy, sys
def deny(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'):
        raise RuntimeError('Network forbidden in quick-start smoke check')
sys.addaudithook(deny)
sys.argv = sys.argv[1:]
sys.path.insert(0, str(__import__('pathlib').Path(sys.argv[0]).resolve().parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def run(script, *args):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('OPENAI_', 'OLLAMA_', 'LANGFLOW_')):
            del env[key]
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run([sys.executable, '-c', BOOTSTRAP, str(ROOT / script), *map(str, args)],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def main():
    with tempfile.TemporaryDirectory(prefix='garak-quickstart-') as temp:
        data = Path(temp) / 'data with spaces'
        configured = run('tools/configure.py', '--data-root', data,
                         '--garak-python', sys.executable, '--openai-model', 'synthetic-model')
        assert configured.returncode == 0, configured.stderr
        config = data / 'garak-playbook-private' / 'config.private.json'
        before = hashlib.sha256(config.read_bytes()).hexdigest()
        for target, provider in [('openai-reasoning', 'openai'), ('ollama-local', 'ollama')]:
            result = run('playbook.py', 'plan', '--config', config,
                         '--target', target, '--campaign', 'base64-32')
            assert result.returncode == 0, result.stderr
            plan = json.loads(result.stdout)
            assert plan['target_profile'] == target
            assert plan['target']['provider'] == provider
            if provider == 'openai':
                assert plan['target']['model'] == 'synthetic-model'
                assert plan['campaign']['max_completion_tokens'] == 1500
        repeat = run('tools/configure.py', '--data-root', data, '--garak-python', sys.executable)
        assert repeat.returncode != 0 and 'already exists' in repeat.stderr
        assert hashlib.sha256(config.read_bytes()).hexdigest() == before
        assert not (data / 'evidence').exists()
        # A separate explicit model profile exercises the new release default through the public CLI.
        release_data = Path(temp) / 'release profile'
        configured = run('tools/configure.py', '--data-root', release_data,
                         '--garak-python', sys.executable, '--openai-model', 'gpt-5.6-sol')
        assert configured.returncode == 0, configured.stderr
        release_config = release_data / 'garak-playbook-private' / 'config.private.json'
        for campaign, expected_limit in [('base64-32', 20000), ('dan-wild-32', 1500)]:
            result = run('playbook.py', 'plan', '--config', release_config,
                         '--target', 'openai-reasoning', '--campaign', campaign)
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)['campaign']['max_completion_tokens'] == expected_limit
        assert not (release_data / 'evidence').exists()
        print('PASS quick-start CLI: new private configuration; both plan paths; paths with spaces; existing config preserved; network denied; zero model requests.')


if __name__ == '__main__':
    main()
