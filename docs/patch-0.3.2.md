# 0.3.2 — remove automatic Kumu instructions

Apply this targeted patch over Garak Playbook 0.3.1 or 0.3.0. It removes only
the automatic Kumu instruction block from the shared handoff renderer and
updates the version label and matching tests. Run facts, evidence selection,
candidate mapping analysis, and Copy/Notepad behavior remain unchanged.
Request a Kumu view separately after the ATLAS Agent returns its analysis.

## Apply in Windows PowerShell

Save `Garak_Playbook_0_3_2_Remove_Auto_Kumu.zip` in
`D:\AI-Lab\projects`. At an idle PowerShell prompt, run:

```powershell
Expand-Archive -LiteralPath 'D:\AI-Lab\projects\Garak_Playbook_0_3_2_Remove_Auto_Kumu.zip' -DestinationPath 'D:\AI-Lab\projects' -Force -ErrorAction Stop
```

This ZIP replaces `garak-playbook\playbook.py` and
`garak-playbook\tests\test_handoff_prompt.py`, and adds this patch note.
It contains no private configuration, scan settings, models, databases, or
scan evidence. No other patch ZIP needs to be applied again.

## Regenerate the saved run without a rescan

In Windows PowerShell:

```powershell
& 'C:\AI-Lab\garak-env\Scripts\python.exe' 'D:\AI-Lab\projects\garak-playbook\playbook.py' handoff --run-dir 'D:\AI-Lab\evaluations\garak-playbook\<existing-run-folder>' --regenerate
```

This checks the existing native report, manifest, and summary for consistency,
regenerates `atlas_handoff.md`, and preserves its previous revision and checksum
index under `handoff-revisions`. It does not rerun Garak or contact a model.
Original evidence, settings, and scan outcome are preserved. Select `2` to inspect
the revised prompt in Notepad, or `1` to copy it. Either returns to PowerShell.
The investigation paragraph should now lead directly into `Run facts:` with
no automatic Kumu request. Future scan handoffs use the same corrected renderer.

## Validation and limits

105 offline tests passed in the builder's Linux workspace. They exercise the
shared renderer through simulated scan completion and existing-run regeneration,
preserve the prior handoff containing the Kumu block, confirm its removal from
the new handoff, and check original evidence, counts, and settings remain intact.
Clipboard/Notepad tests use mocks; they are not actual Windows validation.

The updated runner is byte-identical to the pre-Kumu 0.3.0 runner except for
the version label. No scanner or provider logic changed. The user's T: drive
was not accessed here; the regeneration test uses saved synthetic evidence.
The command above performs regeneration for the actual saved Windows run.
