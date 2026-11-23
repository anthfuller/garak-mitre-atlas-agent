"""Read-only result access tests; no model or real desktop actions are used."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p


class HandoffAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.handoff = self.root / "atlas_handoff.md"
        self.handoff.write_text("# Existing handoff\nUnicode: café 漢字\n$(not_a_command) `literal`\n", encoding="utf-8")
        self.summary = {
            "execution_status": "completed", "flagged_response_count": 0,
            "detectors": [{"probe": "encoding.InjectBase64", "detector": "encoding.DecodeMatch",
                           "evaluated": 32, "flags": 0, "unscorable": 0}],
        }
        p.write_json(self.root / "summary.json", self.summary)
        p.write_json(self.root / "manifest.json", {"process_status": "exited", "exit_code": 0})
        p.checksums(self.root)
        self.before = self.file_hashes()

    def tearDown(self):
        self.temp.cleanup()

    def file_hashes(self):
        return {str(f.relative_to(self.root)): p.sha(f) for f in self.root.rglob("*") if f.is_file()}

    def run_cli(self, extra=(), choices=None):
        out = io.StringIO()
        with patch.object(sys, "argv", ["playbook.py", "handoff", "--run-dir", str(self.root), *extra]), \
             patch("sys.stdout", new=out), patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=choices or AssertionError("Unexpected input")), \
             patch.object(p, "execute", side_effect=AssertionError("No scan")), \
             patch.object(p, "render_outputs", side_effect=AssertionError("No regeneration")), \
             patch.object(p, "get_api", side_effect=AssertionError("No network")):
            code = p.main()
        return code, out.getvalue()

    def test_unattended_existing_run_prints_summary_and_full_path_only(self):
        with patch.object(p, "copy_handoff", side_effect=AssertionError("No clipboard")), \
             patch.object(p, "open_handoff", side_effect=AssertionError("No applications")):
            code, text = self.run_cli(extra=("--yes",))
        self.assertEqual(code, 0)
        self.assertIn("Execution status: completed", text)
        self.assertIn("evaluated responses 32; detector flags 0", text)
        self.assertIn(str(self.handoff), text)
        self.assertNotIn("[1]", text)
        self.assertEqual(self.file_hashes(), self.before)

    def test_each_selection_returns_without_a_second_prompt(self):
        for choice in ("1", "2", "3", "", "   ", "invalid"):
            with self.subTest(choice=choice), patch.object(p, "copy_handoff") as copier, patch.object(p, "open_handoff") as opener:
                code, text = self.run_cli(choices=[choice, AssertionError("A second prompt is forbidden")])
                self.assertEqual(code, 0)
                self.assertEqual(copier.call_count, int(choice == "1"))
                self.assertEqual(opener.call_count, int(choice == "2"))
                self.assertEqual(text.count("[3] Return to PowerShell"), 1)
                if choice == "1":
                    self.assertEqual(text.count("ATLAS prompt copied."), 1)
                    copier.assert_called_once_with(self.handoff)
                if choice == "2":
                    self.assertEqual(text.count("Notepad launch requested."), 1)
                    opener.assert_called_once_with(self.handoff)
                self.assertEqual(self.file_hashes(), self.before)

    def test_action_errors_exit_preserving_files_and_recorded_outcome(self):
        for choice, action, error in (("1", "copy_handoff", p.PlaybookError("Clipboard unavailable")),
                                      ("2", "open_handoff", OSError("Notepad unavailable"))):
            with self.subTest(choice=choice), patch.object(p, action, side_effect=error):
                code, text = self.run_cli(choices=[choice, AssertionError("No retry prompt")])
                self.assertEqual(code, 0)
                self.assertIn(str(error), text)
                self.assertEqual(text.count("File: " + str(self.handoff)), 1)
                self.assertEqual(text.count("[3] Return to PowerShell"), 1)
                self.assertEqual(self.file_hashes(), self.before)

    def test_clipboard_timeout_does_not_change_scan_outcome(self):
        with patch.object(p, "copy_handoff", side_effect=subprocess.TimeoutExpired("powershell", 15)):
            code, text = self.run_cli(choices=["1", AssertionError("No retry prompt")])
        self.assertEqual(code, 0)
        self.assertIn("timed out", text)
        self.assertIn(str(self.handoff), text)
        self.assertEqual(self.file_hashes(), self.before)

    def test_eof_or_interrupt_finishes_without_modifying_evidence(self):
        for error in (EOFError(), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                code, text = self.run_cli(choices=error)
                self.assertEqual(code, 0)
                self.assertIn("Recorded scan outcome is unchanged", text)
                self.assertEqual(self.file_hashes(), self.before)

    def test_nonterminal_input_never_prompts(self):
        with patch("sys.stdin.isatty", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("No input")), \
             patch("sys.stdout", new=io.StringIO()), \
             patch.object(p, "copy_handoff", side_effect=AssertionError("No clipboard")), \
             patch.object(p, "open_handoff", side_effect=AssertionError("No applications")):
            p.present_results(self.root, self.summary, interactive=True)
        self.assertEqual(self.file_hashes(), self.before)

    def test_incomplete_run_keeps_its_status_and_exit_code(self):
        self.summary["execution_status"] = "incomplete"
        p.write_json(self.root / "summary.json", self.summary)
        before = self.file_hashes()
        code, text = self.run_cli(choices=["3"])
        self.assertEqual(code, 2)
        self.assertIn("Execution status: incomplete", text)
        self.assertEqual(self.file_hashes(), before)

    def test_counts_stay_separate_for_multiple_detectors(self):
        self.summary["flagged_response_count"] = 1
        self.summary["detectors"][0]["flags"] = 1
        other = copy.deepcopy(self.summary["detectors"][0])
        other["detector"] = "other.Detector"
        self.summary["detectors"].append(other)
        out = io.StringIO()
        with patch("sys.stdout", new=out):
            p.present_results(self.root, self.summary)
        text = out.getvalue()
        self.assertIn("Responses flagged by at least one detector: 1", text)
        self.assertEqual(text.count("evaluated responses 32; detector flags 1"), 2)
        self.assertNotIn("evaluated responses 64", text)

    def test_missing_handoff_is_reported_without_regeneration(self):
        self.handoff.unlink()
        before = self.file_hashes()
        with patch("sys.stderr", new=io.StringIO()) as err:
            code, _ = self.run_cli(extra=("--yes",))
        self.assertEqual(code, 2)
        self.assertIn("atlas_handoff.md are required", err.getvalue())
        self.assertEqual(self.file_hashes(), before)

    def test_windows_clipboard_passes_path_as_data_to_fixed_command(self):
        special = self.root / "path with spaces ' $(literal) [test]"
        special.mkdir()
        handoff = special / "atlas_handoff.md"
        handoff.write_bytes(self.handoff.read_bytes())
        before = p.sha(handoff)
        with patch.object(sys, "platform", "win32"), \
             patch.object(p.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            p.copy_handoff(handoff)
        argv = run.call_args.args[0]
        kwargs = run.call_args.kwargs
        self.assertIn("-STA", argv)
        self.assertIn("-NoProfile", argv)
        self.assertIn("-NonInteractive", argv)
        self.assertIn("ReadAllText", argv[-1])
        self.assertIn("Encoding]::UTF8", argv[-1])
        self.assertIn("Set-Clipboard -Value", argv[-1])
        self.assertNotIn(str(handoff), argv[-1])
        self.assertNotIn("not_a_command", argv[-1])
        self.assertEqual(kwargs["env"]["GARAK_PLAYBOOK_HANDOFF"], str(handoff))
        self.assertIs(kwargs["shell"], False)
        self.assertEqual(kwargs["timeout"], 15)
        self.assertEqual(p.sha(handoff), before)

    def test_windows_clipboard_nonzero_error_is_surfaced(self):
        with patch.object(sys, "platform", "win32"), \
             patch.object(p.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "Clipboard locked")):
            with self.assertRaisesRegex(p.PlaybookError, "Clipboard locked"):
                p.copy_handoff(self.handoff)

    def test_windows_notepad_is_nonblocking_with_isolated_standard_streams(self):
        with patch.object(sys, "platform", "win32"), \
             patch.object(p.os, "startfile", side_effect=AssertionError("No file association"), create=True), \
             patch.object(p.subprocess, "DETACHED_PROCESS", 0x00000008, create=True), \
             patch.object(p.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200, create=True), \
             patch.object(p.subprocess, "Popen") as launch, \
             patch.object(p.subprocess, "run", side_effect=AssertionError("Do not wait for editor")):
            child = p.open_handoff(self.handoff)
        argv = launch.call_args.args[0]
        kwargs = launch.call_args.kwargs
        self.assertEqual(Path(argv[0]).name, "notepad.exe")
        self.assertEqual(argv[1:], [str(self.handoff)])
        for stream in ("stdin", "stdout", "stderr"):
            self.assertEqual(kwargs[stream], subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["creationflags"], 0x00000208)
        child.wait.assert_not_called()
        child.communicate.assert_not_called()
        self.assertEqual(self.file_hashes(), self.before)

    def test_desktop_actions_on_unsupported_platform_report_failure(self):
        with patch.object(sys, "platform", "linux"):
            for action in (p.copy_handoff, p.open_handoff):
                with self.subTest(action=action.__name__), self.assertRaisesRegex(p.PlaybookError, "requires Windows"):
                    action(self.handoff)

    def test_execute_offers_access_only_after_artifacts_are_saved(self):
        cfg = {"schema_version": 1, "garak_python": sys.executable,
               "evidence_root": str(self.root / "runs"), "xdg_data_home": str(self.root / "data"),
               "targets": {"local": {"provider": "ollama", "model": "synthetic:only", "endpoint": "http://127.0.0.1:11434"}}}

        def render(report, folder, manifest):
            p.write_json(folder / "summary.json", self.summary)
            (folder / "atlas_handoff.md").write_bytes(self.handoff.read_bytes())
            return copy.deepcopy(self.summary)

        def fail_copy_after_saved(path):
            saved = p.read_json(path.parent / "checksums.json")
            self.assertIn("summary.json", saved)
            self.assertEqual(saved["atlas_handoff.md"], p.sha(path))
            raise OSError("Synthetic clipboard failure after saving")

        for unattended in (False, True):
            with self.subTest(unattended=unattended):
                process = MagicMock(returncode=0, stdout=io.BytesIO(b"Synthetic scanner output\n"))
                process.poll.return_value = 0
                process.wait.return_value = 0
                out = io.StringIO()
                with patch.object(p, "preflight", return_value={"status": "passed"}), \
                     patch.object(p.subprocess, "Popen", return_value=process) as launch, \
                     patch.object(p, "render_outputs", side_effect=render) as renderer, \
                     patch("sys.stdin.isatty", return_value=True), patch("sys.stdout", new=out), \
                     patch("builtins.input", side_effect=AssertionError("No unattended input") if unattended else ["RUN", "1", AssertionError("No second action prompt")]), \
                     patch.object(p, "copy_handoff", side_effect=fail_copy_after_saved) as copier, \
                     patch.object(p, "open_handoff", side_effect=AssertionError("No open")):
                    code = p.execute(cfg, "local", "base64-32", yes=unattended)
                self.assertEqual(code, 0)
                self.assertEqual(launch.call_count, 1)
                self.assertEqual(renderer.call_count, 1)
                self.assertEqual(copier.call_count, 0 if unattended else 1)
                folder = renderer.call_args.args[1]
                self.assertEqual(p.read_json(folder / "summary.json")["execution_status"], "completed")
                self.assertEqual(p.read_json(folder / "manifest.json")["process_status"], "exited")
                for name, digest in p.read_json(folder / "checksums.json").items():
                    self.assertEqual(p.sha(folder / name), digest)
                self.assertIn(str(folder / "atlas_handoff.md"), out.getvalue())
                self.assertEqual(out.getvalue().count("[3] Return to PowerShell"), int(not unattended))


if __name__ == "__main__":
    unittest.main()
