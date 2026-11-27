# Maintainer Windows validation

For ordinary installation, use the [Install on Windows and open your first ATLAS reply](install-and-verify.md). The procedures here reproduce maintainer checks; they are not extra steps every researcher must run.

## Recorded validation

- The full Windows validator passed at `09e812807924e9c55c9d96a507fe0beac637f752` on November 26, 2026. It reused recorded environments from the earlier fresh installations with unchanged requirements and package inventories.
- The seven targeted Windows delta checks passed at `4fedd3f008088a408825a39ec284c5b3bbcdaf7e` the same day. The exact candidate and bundle hash matched the delivered source; the prior Windows receipt hash also matched. No model call, paid request or dependency installation was recorded.
- Later reply-formatting, prepared-flow and inline Kumu code changes have their own offline evidence in the [release record](release-v1.md); they are not documentation-only changes after `4fedd3f`.
- The assisted Windows walkthrough passed, including the observed saved reply and AML.T0068 Kumu view. An independent guide-only install remains unverified. Chat assistance and a manual model-component edit were used; the generated-flow import has not received an independent installation pass.
- Later editorial corrections include four Python display strings and documentation. Their offline checks are separate from the Windows receipts; scan behavior, dependencies and profiles remain unchanged.

Receipts/logs remain private. These checkpoints are not relabeled as a full Windows run for every later commit. Desktop clipboard/editor/browser actions remain mocked in the automated suite; actual model compatibility and native UI behavior need their own evidence. See the [release record](release-v1.md).

## Reproduce the full synthetic validation when needed

Use **normal Windows PowerShell** in a clean `main` checkout cloned from `https://github.com/anthfuller/garak-mitre-atlas-agent.git`. Git for Windows and Python 3.11 (`py -3.11`) are prerequisites. No Garak/Ollama/Langflow environment activation, model service or API key is needed.

The existing validator accepts a local Git bundle so it can test a fixed snapshot independently. Generate that input locally, outside the checkout; it is private validation input and must not be committed or attached to a GitHub release. No downloaded private review ZIP is required.

```powershell
# From the clean main checkout containing playbook.py and tools.
$validationInput = Join-Path $env:LOCALAPPDATA ('GarakPlaybook-validation-input-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $validationInput) { throw 'Choose a new validation input directory.' }
New-Item -ItemType Directory -Path $validationInput -ErrorAction Stop | Out-Null
$bundle = Join-Path $validationInput 'source.bundle'
git bundle create $bundle main HEAD
if ($LASTEXITCODE -ne 0) { throw 'Snapshot creation failed.' }
& '.\tools\Validate-CleanWindows.ps1' -BundlePath $bundle
```

The helper creates a separate checkout and two validation environments under `%LOCALAPPDATA%\GarakPlaybook-check-<timestamp>`. Dependency installation needs internet access and can take time. The working lab's configuration, evidence and environments are not used. No live model generation or paid call is part of this validation.

The helper stops on failure and records each step:

1. Clone the fixed snapshot and record its hash and commit.
2. Create the Python 3.11 test environment, install `requirements-research.txt` and record resolved packages.
3. Run the complete synthetic suite, including real embedded Chroma 1.5.9; require zero failures, errors, expected failures and skips on the cloned commit.
4. Create the separate scanner environment, install `requirements-scanner.txt` and record resolved packages.
5. Run public configuration/plan and installed-registry checks, then synthetic Ollama, OpenAI and batch success/auth-failure integrations using real Garak. These do not test real model responses.
6. Require an unchanged checkout; save `windows-validation.json` and logs outside it, including a failure receipt if a step fails.

Python stdout/stderr use UTF-8 during validation; the helper restores the prior `PYTHONIOENCODING` afterward. It does not change the machine locale or generation settings. The OpenAI synthetic integration closes logging handlers before temporary-directory cleanup; its PASS line follows successful cleanup.

Expected final output is `Windows validation: passed` and the receipt directory. Preserve that directory privately. On failure, inspect the named log before proposing a change or rerun. These checks do not repair the separate research failure-receipt gap R-01.

## Reuse recorded installations

If an earlier validation directory has successful test and scanner installation receipts, add `-ReuseEnvironmentsFrom 'C:\Path\To\EarlierValidation'` to the full-validator command. It still clones the snapshot into a new directory but uses the recorded interpreters without running pip install. It requires identical requirements and package inventories, records the earlier directory/receipt hash, and preserves the old checkout and logs. Failed installations are not reusable. This is a resumed checkout check, not a second independent fresh installation.

## Reproduce the targeted delta check

This check passed for `4fedd3f`. Use it to reproduce that checkpoint or check a later relevant change.

Using a local snapshot created above and the original passed `09e8128` receipt, run in **normal Windows PowerShell**:

```powershell
& '.\tools\Validate-ReleaseDelta.ps1' `
  -BundlePath $bundle `
  -WindowsReceipt 'C:\Path\To\PassedCheck\windows-validation.json'
```

It clones separately, checks unchanged requirements and the recorded test-package inventory, runs release-profile/headroom/OpenAI unit checks plus the public quick-start CLI, and saves a commit-specific receipt. It installs no dependencies and invokes no live model. Keep any private launcher, original receipt, generated bundle and resulting logs outside Git and GitHub release attachments.
