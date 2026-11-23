# 0.3.1 — run-scoped Kumu graph instructions

This targeted patch applies over an existing Garak Playbook 0.3.0 installation.
It changes the shared ATLAS handoff renderer and version label, and supplies
matching tests. It does not install dependencies or alter scan settings.

Every newly generated `atlas_handoff.md` now contains the reviewer's graph
instruction block immediately after the investigation paragraph and before
the run facts. Both scan completion and `handoff --regenerate` use this renderer.
The agent is asked to verify run-associated AML IDs, include candidate mappings,
exclude other runs and rejected mappings, and show one-hop relationships.
Neighboring ATLAS nodes remain context, not additional findings for the run.
The requested fallback is one focused link per mapped ID if a combined view
cannot be rendered, or no graph if there are no supported mappings.

This adds instructions for the ATLAS Agent. The runner does not call Langflow,
generate a Kumu URL, send evidence, or open the graph. Actual Graph Visualizer
behavior, including support for combined views, has not been validated here.
Existing Copy/Notepad actions and unattended handoff behavior are unchanged.

## Apply in Windows PowerShell

Save `Garak_Playbook_0_3_1_Kumu_Handoff.zip` in
`D:\AI-Lab\projects`. Run this from any PowerShell directory, with no
scan currently running:

```powershell
Expand-Archive -LiteralPath 'D:\AI-Lab\projects\Garak_Playbook_0_3_1_Kumu_Handoff.zip' -DestinationPath 'D:\AI-Lab\projects' -Force -ErrorAction Stop
```

The ZIP replaces `garak-playbook\playbook.py` and
`garak-playbook\tests\test_handoff_prompt.py`, and adds this patch note.
No private configuration, model, database, campaign, or scan evidence is in
the ZIP. Older patch ZIPs do not need to be applied again.

## Update an existing run without scanning

Future scans include the block automatically. To regenerate one saved handoff,
use the actual run directory with the existing command, in Windows PowerShell:

```powershell
& 'C:\AI-Lab\garak-env\Scripts\python.exe' 'D:\AI-Lab\projects\garak-playbook\playbook.py' handoff --run-dir '<FULL EXISTING RUN DIRECTORY>' --regenerate
```

The run directory must contain `scan.report.jsonl`, `manifest.json`, and
`summary.json`. Regeneration checks their consistency, preserves the previous
handoff and checksum index under `handoff-revisions`, writes the revised
handoff, and refreshes the checksum index. It does not rerun Garak, make API
requests, change the scan outcome, or modify original evidence. Select `1` to
copy the complete revised prompt or `2` to open that same file in Notepad;
either action returns to PowerShell. Add `--yes` for no prompt or desktop action.

## Offline validation

105 standard-library tests passed in the builder's Linux workspace. These
include the real renderer through simulated scan completion and the existing-run
CLI, exact inclusion of the graph block, distinct run IDs, unchanged selected
evidence and counts, prior-revision preservation, and no second scanner launch.
Clipboard/Notepad tests use mocks; this is not new Windows or live ATLAS validation.

An additional comparison with the 0.3.0 renderer confirmed that removing only
the inserted graph block yields byte-identical prompts for both zero-flag and
flagged synthetic evidence. Existing prompt size bounds still apply to the
original content; the requested block adds 952 UTF-8 bytes plus two newlines.

No Garak scan, paid API request, or live Graph Visualizer call was made for
this patch. The user's Windows run folder was not accessed here; the Windows
command performs regeneration against that saved evidence.
