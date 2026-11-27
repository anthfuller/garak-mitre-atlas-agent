# 0.2.1: return from probe review

**Historical version 0.2.1 notes.** Procedures and validation below describe that version. Use the [current Windows install guide](install-and-verify.md) and [release record](release-v1.md) for current setup and later results. Do not apply old patch ZIPs to a current checkout.

The supported-probe review screen now offers:

```text
RUN: Start scan | B: Back | Enter: Cancel and exit:
```

`B` (or `b`) returns to the same search results and page, without repeating target selection, refreshing the inventory, creating a run directory, calling preflight or launching Garak. Select another probe directly. Only the exact confirmation `RUN` starts an interactive scan. Enter, other responses, Ctrl+C and EOF retain their existing cancellation behavior. Explicit unattended `--yes` behavior is unchanged.

The existing campaigns, workload limits, settings, evidence handling, ATLAS renderer and Copy/Notepad actions are unchanged.

## Apply in Windows PowerShell

Save `Garak_Playbook_0_2_1_Back_Fix.zip` beside the existing `garak-playbook` folder. From that parent directory:

```powershell
Expand-Archive -LiteralPath .\Garak_Playbook_0_2_1_Back_Fix.zip -DestinationPath . -Force -ErrorAction Stop
```

Then launch your existing `playbook.py menu --config <private-config-path>` command. This is a cumulative source/test/documentation patch: use this ZIP alone over the existing working installation, even if the 0.2.0 browser ZIP has not been applied. It includes the browser helper and support policy. It does not contain or overwrite private configuration, campaigns, the source audit, installed environments, models, databases or prior scan evidence.

## Validation

88 offline tests passed on Linux. The new regression searches a synthetic inventory, navigates to page two, selects one probe, backs out, and selects a different probe without restarting. It verifies that Back starts no preflight or scan and creates no run folder. Only `RUN` for the second probe reaches the mocked scanner; its synthetic report completes the existing evidence and ATLAS handoff flow. Cancellation cases verify that other answers do not launch.

The test uses mocked inventory, preflight and scanner execution. This is navigation/accounting validation, not a real-model scan or actual Windows validation. Earlier 0.2.0 real Garak CLI tests against a synthetic endpoint remain documented as prior validation.
