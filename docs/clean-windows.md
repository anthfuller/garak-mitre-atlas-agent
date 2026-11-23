# Clean Windows checkout validation

Extract the preparation ZIP into its own folder. Use **normal Windows PowerShell**, opened in the extracted folder containing `garak-playbook.bundle` and `source`. Do not activate Garak, Ollama or Langflow environments. No model service needs to be running. Prerequisites are Git for Windows and Python 3.11 available through `py -3.11`.

The helper creates a new checkout and two new environments under `%LOCALAPPDATA%\GarakPlaybook-check-<timestamp>`. It does not use the working lab's private configuration, evidence or environments. Dependency installation requires internet access and can take time. No live model generation, API key or paid call is part of this validation.

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
5. Run the installed-registry, Ollama stub, OpenAI mock and two batch integrations (success and authentication failure). The batch check exercises the actual parent/child key pipe and separate evidence archives with synthetic HTTP responses.
6. Require an unchanged Git checkout. Write `windows-validation.json` and individual logs outside it, including a failure receipt if a validation step fails.

Expected final output: `Windows validation: passed` followed by the receipt directory. Preserve that directory and share `windows-validation.json` for review. If it fails, share the indicated failing log; do not repeat the successful steps in the working lab.

This is **pending native Windows execution** in the candidate. Linux results do not establish Windows compatibility. Desktop clipboard/editor/browser actions remain mocked even when the suite runs on Windows; actual batch console control and live probe/model compatibility require their own evidence. This helper's receipt does not repair the separate research failure-receipt gap R-01.

The bundle retains the sanitized preparation history plus the Builder's batch integration commit. Inspect it with `git log` in the fresh checkout. No GitHub remote or public release is required for this check.
