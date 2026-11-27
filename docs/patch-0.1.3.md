# Version 0.1.3: readable prompt and immediate return

**Historical version 0.1.3 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

This update replaces the previous looping completion menu and file-association opener. It requires the existing installation; no package upgrade, scan or settings change is needed.

## Changed behavior

The menu is shown once at interactive scan completion and by the existing-run `handoff` command:

```text
[1] Copy ATLAS prompt and return to PowerShell
[2] Open ATLAS prompt in Notepad and return to PowerShell
[3] Return to PowerShell
```

- Option 1 copies only the entire prompt file, prints one confirmation and exits.
- Option 2 explicitly launches `System32\notepad.exe`, prints one launch confirmation and exits without waiting for Notepad to close. No `.md` file association or VS Code invocation is used. All three standard streams are redirected to DEVNULL; the process is detached with a new process group and extra handles are closed.
- Enter, 3, EOF or Ctrl+C exits. Invalid input prints a message and exits. There is no retry loop. Copy/open errors print the error and file path, then exit with the scan's existing outcome unchanged.
- Unattended `--yes` behavior is unchanged: status/counts/path are printed, without prompts or desktop actions.

The prompt has short investigation instructions, a compact run summary, sampling/interpretation limits, and labeled **Attempt ID / Input / Response / Detector result** sections. Inputs and responses appear once in fenced text blocks with actual line breaks. Roles and order are retained for multiple turns. Comparison targets remain part of detector context. There are no JSON wrappers, duplicated conversations, technical configuration dumps or operator instructions.

Text writing explicitly avoids newline conversion. Unicode, whitespace, mixed line endings, literal backslash sequences and embedded backticks are preserved. Fences are longer than embedded backtick runs; the newline separating evidence from the closing fence is framing, not a change to the retained native record.

## Apply the update in Windows PowerShell

1. Exit an active handoff menu first. In the previous version, choose 3 or press Ctrl+C. Keep the previous distribution or source folder for rollback.
2. Save `Garak_Playbook_0_1_3_Fix.zip` in your existing projects parent directory.
3. Extract it into that same parent directory, replacing matching `garak-playbook` files. Do not nest a second `garak-playbook` directory.
4. Run `playbook.py --version` with your existing Garak Python. Expected: `0.1.3`.

Example paths below are placeholders; use your existing locations:

```powershell
Expand-Archive -LiteralPath "D:\AI-Lab\projects\Garak_Playbook_0_1_3_Fix.zip" -DestinationPath "D:\AI-Lab\projects" -Force

& "C:\AI-Lab\garak-env\Scripts\python.exe" "D:\AI-Lab\projects\garak-playbook\playbook.py" --version

& "C:\AI-Lab\garak-env\Scripts\python.exe" "D:\AI-Lab\projects\garak-playbook\playbook.py" handoff --run-dir "D:\AI-Lab\evaluations\<existing-run-folder>" --regenerate
```

The last command regenerates only the derived prompt using the saved native report and manifest, checks agreement with the saved summary, preserves the previous handoff and checksum index under `handoff-revisions`, and offers the new menu. It does not invoke Garak or a model. Native evidence, settings and recorded outcome remain unchanged. Omit `--regenerate` on later access to use the saved prompt without rewriting it. Add `--yes` for noninteractive use.

## Verification and limits

- 62 offline tests passed, including immediate exit after each choice, Enter/3/EOF/Ctrl+C, error/timeout exits without outcome changes, unattended behavior, exact raw evidence and line-ending preservation, metadata exclusion, regeneration history and original-record preservation.
- Notepad launch tests are **mocked on Linux**. They assert the explicit executable and file argument, detached process flags, DEVNULL for stdin/stdout/stderr, closed extra handles, `shell=False`, and no `wait()` or `communicate()` call. Clipboard tests also use a mocked Windows boundary.
- Both real-Garak/synthetic-endpoint integrations passed; they verify scanner invocation, settings, output parsing/artifacts and unattended completion. They use no real model.
- All five uploaded real-run inputs, responses and comparison targets were checked character-for-character in the new fenced text format. IDs and detector scores are preserved once; the run summary remains **32 evaluated responses and zero flags**. The full native report remains on the operator computer and is reconciled there during regeneration.
- At the 0.1.3 checkpoint, Windows desktop validation was incomplete: confirm that option 1 copies the readable prompt and returns the PowerShell prompt; invoke `handoff` again and confirm option 2 opens Notepad, leaves no editor output in the terminal and returns without waiting for editor closure. These checks require no new scan. These checks were not performed on Windows for this patch.

## Patch contents

```text
garak-playbook/playbook.py
garak-playbook/README.md
garak-playbook/docs/evidence.md
garak-playbook/docs/patch-0.1.3.md
garak-playbook/docs/public-file-list.txt
garak-playbook/docs/validation.md
garak-playbook/tests/integration_stub.py
garak-playbook/tests/test_handoff_access.py
garak-playbook/tests/test_handoff_prompt.py
```

The archive contains public source/tests/documentation only. It includes no private configuration, model data, database files or real scan evidence.
