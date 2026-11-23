# Version 0.1.2: ATLAS prompt and completion access

This patch addresses the two reviewer requests together. It updates the existing 0.1.1 source tree; no installation or dependency upgrade is required.

## Behavior

- `atlas_handoff.md` is one self-contained investigation prompt: instructions/answer format, concise scan context, and exact selected evidence once with attempt IDs and detector results. It has no manifest/configuration dump, commands, installation paths, proxy/preflight details, duplicated conversations, empty transport metadata or operator instructions.
- The existing selection remains the first five flagged responses, otherwise the first five observations, in retained report order. Selection is declared. Quoted prompt/response text is preserved, including Unicode, spacing, line breaks and embedded backticks. Detector trigger strings are retained as comparison targets. No candidate ATLAS mapping is asserted by the runner.
- After artifacts are saved, execution status, per-detector evaluated-response/flag/unscorable counts, unique flagged responses and the full handoff path are printed.
- Interactive completion offers `[1] Copy ATLAS handoff contents to clipboard`, `[2] Open ATLAS handoff`, and `[3] Finish`. Copy and open use the same existing prompt file and return to the menu. Copy includes only file contents. EOF/Ctrl+C finishes the access menu without changing the recorded scan outcome.
- Windows PowerShell handles clipboard text. Opening requests the associated Windows `.md` application; a missing association or other reported failure is shown with the path. The runner cannot independently confirm that the application rendered the file after accepting the request.
- Copy/open failure or timeout leaves scan status and evidence unchanged. `--yes` disables prompts, application opening and clipboard changes. No automatic ATLAS submission occurs.

## Updating an existing installation

1. Finish any current runner session. Keep the previous distribution for rollback; optionally copy the existing source folder as a backup.
2. Extract this archive into the existing **projects parent directory**. Its top-level folder is `garak-playbook`. Replace matching files; do not extract into a second nested `garak-playbook` folder.
3. Run `playbook.py --version` using the existing Garak environment's Python. Expected version: `0.1.2`.

Files supplied:

```text
garak-playbook/playbook.py
garak-playbook/README.md
garak-playbook/docs/evidence.md
garak-playbook/docs/patch-0.1.2.md
garak-playbook/docs/public-file-list.txt
garak-playbook/docs/validation.md
garak-playbook/tests/integration_stub.py
garak-playbook/tests/test_handoff_access.py
garak-playbook/tests/test_handoff_prompt.py
```

Private configuration, campaigns, models, databases and original scan evidence are not in the archive. Garak configuration generation, scanner process cleanup, native evidence analysis and source-audit expectations are unchanged.

## Use existing evidence without another scan

These commands belong in **Windows PowerShell**. Substitute your existing paths:

```powershell
$labPython = "C:\AI-Lab\garak-env\Scripts\python.exe"
$runnerPath = "D:\AI-Lab\projects\garak-playbook\playbook.py"
$runFolder = "D:\AI-Lab\evaluations\<existing-run-folder>"

& $labPython $runnerPath --version
& $labPython $runnerPath handoff --run-dir $runFolder --regenerate
```

Regeneration requires `scan.report.jsonl`, `manifest.json` and `summary.json` from that run. It re-analyzes the native evidence using the saved settings and requires agreement with the saved summary. A discrepancy stops before writing anything. Only the derived handoff and checksum index are replaced; their previous bytes and a revision record are retained under `handoff-revisions/<unique-revision>/`. It does not call Ollama, Garak, OpenAI, Langflow or Chroma, and it does not change scan settings or recorded outcome.

After regeneration choose **1**, paste into the ATLAS Agent, and choose **3** when finished with the menu. Option **2** opens the same prompt file. On later access, omit `--regenerate` to read/open/copy the current file without rewriting anything. Add `--yes` for an unattended regeneration or print-only access; no desktop action or prompt occurs.

## Validation and remaining limits

- 61 offline standard-library tests passed: the existing 37 plus 24 focused handoff tests. These cover selection, exact text/roles/scores, omitted metadata, known/unknown settings, menu loops, no unattended desktop actions, errors, timeouts, preserving outcomes, historical handoff retention, unchanged native records, summary discrepancies and rollback after a checksum-write failure.
- Both real-Garak/synthetic-endpoint integrations passed with 32 requests each. They verify invocation, settings, parsing, artifacts and the unattended completion output. No real model is used by these integrations.
- For the operator's supplied run, the new renderer was compared against all five uploaded prompt/response examples, IDs, detector scores and triggers. Every selected value matched exactly, and the prompt records the supplied **32 evaluated responses / zero detector flags**. The builder has not inspected the other 27 native responses. Local regeneration reads the full retained native report and reconciles it with the saved summary.
- Windows clipboard round-trip and associated-application opening are not yet exercised on the operator's desktop; their adapters are mocked in offline tests. The existing-run command above allows that check without another model scan.
- Original limitations remain, including missing per-response token counts/stop reasons, uncertain truncation and untested Windows process-tree cancellation. No model vulnerability, broad resistance or mitigation effectiveness is claimed.

The public source and tests contain synthetic fixtures only; real operator evidence is not packaged in this patch.
