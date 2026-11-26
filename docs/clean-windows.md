# Clean Windows checkout validation

Extract the preparation ZIP into its own folder. Use **normal Windows PowerShell**, opened in the extracted folder containing `garak-playbook.bundle` and `source`. Do not activate Garak, Ollama or Langflow environments. No model service needs to be running. Prerequisites are Git for Windows and Python 3.11 available through `py -3.11`.

The helper creates a new checkout and two new environments under `%LOCALAPPDATA%\GarakPlaybook-check-<timestamp>`. It does not use the working lab's private configuration, evidence or environments. Dependency installation requires internet access and can take time. No live model generation, API key or paid call is part of this validation.

Python stdout/stderr use UTF-8 during validation so Garak's Unicode log markers can be captured on Windows. The helper restores the prior `PYTHONIOENCODING` value on exit. It does not change the machine locale, Python file-reading defaults or generation settings.

After reviewing the supplied script, run:

```powershell
Unblock-File -LiteralPath '.\source\tools\Validate-CleanWindows.ps1'
& '.\source\tools\Validate-CleanWindows.ps1' -BundlePath '.\garak-playbook.bundle'
```

Unblock applies only to this downloaded script. It does not lower the system execution policy; managed policy may still require signing. Administrator elevation is not required.

The helper performs these steps and stops on failure:

1. Clone the bundle into a new directory and record its SHA-256 and exact commit.
2. Create a fresh Python 3.11 test environment, install `requirements-research.txt`, and record all resolved package versions.
3. Run the complete synthetic suite, including real embedded Chroma 1.5.9. Require zero failures, errors, expected failures and skips, on the cloned commit.
4. Create a separate fresh scanner environment, install `requirements-scanner.txt`, and record resolved package versions.
5. Run the configuration/plan smoke check with network denied, then the installed-registry, Ollama stub, OpenAI mock and two batch integrations (success and authentication failure). The batch check exercises the actual parent/child key pipe and separate evidence archives with synthetic HTTP responses.
6. Require an unchanged Git checkout. Write `windows-validation.json` and individual logs outside it, including a failure receipt if a validation step fails.

Expected final output: `Windows validation: passed` followed by the receipt directory. Preserve that directory and share `windows-validation.json` for review. If it fails, share the indicated failing log; do not repeat the successful steps in the working lab.

**Earned checkpoint:** the supplied Windows receipt passed every listed check on November 26, 2026 at commit `09e812807924e9c55c9d96a507fe0beac637f752`, using the recorded environments from the earlier fresh installations with unchanged requirements and package inventories. This is retained evidence, not a requirement to reinstall because a reviewer changed. Later candidate changes have their own checks in [release-v1.md](release-v1.md); the old receipt is not relabeled as a full Windows pass for a newer commit. Linux results do not establish Windows compatibility. Desktop clipboard/editor/browser actions remain mocked even when the suite runs on Windows; actual batch console control and live probe/model compatibility require their own evidence. This helper's receipt does not repair the separate research failure-receipt gap R-01.

## Reuse successful dependency installations after a failed check

If an earlier validation directory has successful test and scanner installation receipts, add `-ReuseEnvironmentsFrom 'C:\Path\To\EarlierValidation'` to the helper command. The helper still clones the supplied bundle into a new directory and reruns the checks on that commit, but uses the earlier validation interpreters without running pip install or recreating environments. It requires identical requirements files and package inventories. The new receipt records the earlier directory and receipt hash. Existing logs, the previous checkout and the working lab are preserved. If either installation did not succeed, this option refuses reuse.

This is a resumed checkout check using documented environments from the earlier fresh installation, not a second independent fresh installation.

The OpenAI synthetic integration runs Garak in its own test process. It closes
logging handlers before deleting its temporary directory, including when an
assertion fails. Its PASS line is printed only after cleanup succeeds. This
test-only correction addresses the observed Windows sharing violation on
`garak.log`; it does not change the runner, model requests or scan settings.

The bundle retains the sanitized preparation history plus the Builder's batch/error-handling and checkpoint updates. Inspect it with `git log` in the fresh checkout. No GitHub remote or public release is required for this check.

## Candidate-only Windows delta check

For this candidate, reuse the passed 09e8128 receipt with the targeted helper. It clones the candidate separately, verifies unchanged requirements and the recorded test-package inventory, runs release-profile/headroom/OpenAI unit checks plus the public CLI quick start, and saves a new commit-specific receipt. No dependency installation, model call or repeat of the full old validator occurs.

```powershell
& '.\source\tools\Validate-ReleaseDelta.ps1' `
  -BundlePath '.\garak-playbook.bundle' `
  -WindowsReceipt 'C:\Path\To\PassedCheck\windows-validation.json'
```

The companion review package supplies a launcher pointing at the operator's known receipt. Keep that private launcher and actual receipt out of Git.
