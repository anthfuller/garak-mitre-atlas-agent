# 0.3.2: remove automatic Kumu instructions

**Historical version 0.3.2 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

Version 0.3.2 applied to Garak Playbook 0.3.1 or 0.3.0. It removed only
the automatic Kumu instruction block from the shared handoff renderer and
updates the version label and matching tests. Run facts, evidence selection,
candidate mapping analysis, and Copy/Notepad behavior remain unchanged.
At that version, Kumu views required a separate request after analysis. The current workflow requests analysis and the Kumu link together; the separate action remains optional.

## Historical application

The original instructions used a version-specific patch archive and optional handoff regeneration. Use the [current install guide](install-and-verify.md) and [operator guide](operator-guide.md#optional-handoff-regeneration) instead. Existing evidence remains unchanged unless derived handoff regeneration is explicitly requested.

## Validation and limits

105 offline tests passed on Linux. They exercise the
shared renderer through simulated scan completion and existing-run regeneration,
preserve the prior handoff containing the Kumu block, confirm its removal from
the new handoff, and check original evidence, counts, and settings remain intact.
Clipboard/Notepad tests use mocks; they are not actual Windows validation.

The updated runner is byte-identical to the pre-Kumu 0.3.0 runner except for
the version label. No scanner or provider logic changed. No private Windows run directory was accessed during the synthetic regeneration tests.
