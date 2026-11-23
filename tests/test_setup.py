import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "configure.py"
spec = importlib.util.spec_from_file_location("configure", SCRIPT)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class SetupTests(unittest.TestCase):
    def test_private_configs_outside_source_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            root = Path(td)
            files = c.configure(root, sys.executable, sys.executable, openai_model="synthetic-model")
            self.assertEqual(len(files), 2)
            before = {p: p.read_bytes() for p in files}
            with self.assertRaisesRegex(ValueError, "already exists"):
                c.configure(root, sys.executable, sys.executable)
            self.assertEqual(before, {p: p.read_bytes() for p in files})
            import playbook
            config = playbook.load_config(root / "garak-playbook-private" / "config.private.json")
            self.assertEqual(config["targets"]["openai-reasoning"]["model"], "synthetic-model")

    def test_inside_checkout_rejected_without_writes(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            c.configure(c.ROOT / "private", sys.executable)

    def test_missing_interpreter_rejected(self):
        with tempfile.TemporaryDirectory() as td, self.assertRaisesRegex(ValueError, "does not exist"):
            c.configure(Path(td), Path(td) / "missing-python.exe")
