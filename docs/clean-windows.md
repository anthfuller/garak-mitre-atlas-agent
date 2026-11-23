# Clean Windows checkout test

Use a separate new directory. Do not extract over the working lab, reuse its private configuration, import its evidence or change its environments. The supplied Git bundle has one fresh source commit and no earlier lab history. No remote is required.

Extract the preparation ZIP into its own folder. In File Explorer open the extracted folder containing `garak-playbook.bundle`, then open Windows PowerShell there. Prerequisites are Git for Windows and Python 3.11. If either is missing, stop and report it. All commands below belong in Windows PowerShell.

```powershell
Get-Command git -ErrorAction Stop
py -3.11 --version
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 prerequisite missing.' }
$checkRoot = Join-Path $env:LOCALAPPDATA ('GarakPlaybook-check-' + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $checkRoot -ErrorAction Stop | Out-Null
$bundle = (Resolve-Path -LiteralPath '.\garak-playbook.bundle' -ErrorAction Stop).Path
git clone $bundle "$checkRoot\garak-playbook"
if ($LASTEXITCODE -ne 0) { throw 'Clone failed.' }
py -3.11 -m venv "$checkRoot\test-env"
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed.' }
$testPython = "$checkRoot\test-env\Scripts\python.exe"
& $testPython -m pip install -r "$checkRoot\garak-playbook\requirements-research.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $testPython "$checkRoot\garak-playbook\tools\run_tests.py" --out "$checkRoot\test-results"
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Preserve the receipt and log.' }
$repo = Join-Path $checkRoot 'garak-playbook'
$changes = git -C $repo status --short
if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Checkout inspection failed or checkout is dirty.' }
```

Expected: passed status with zero failures/errors/skips; final Git status empty. The receipt records the commit and actual OS/Python versions. A Linux result does not count as Windows validation. Synthetic local HTTP endpoints do not contact actual Ollama/Langflow services. Some tests use a real inert subprocess; desktop actions are mocked.

This test wrapper's receipt does not fix R-01 in research_index.py. Runtime modules remain unchanged. Test-only portability fixes close Chroma clients through the public API, compare path names independent of separators and allow actual Windows taskkill to stop the inert regression child.

## Separate scanner installation acceptance

Continue in the same PowerShell session using the checkout created above. Capture each integration's output and check its exit code immediately.

```powershell
$repo = Join-Path $checkRoot 'garak-playbook'
$scannerEnv = Join-Path $checkRoot 'scanner-env'
if (Test-Path -LiteralPath $scannerEnv) { throw 'Use a fresh scanner environment.' }
py -3.11 -m venv $scannerEnv
if ($LASTEXITCODE -ne 0) { throw 'Scanner environment creation failed.' }
$scannerPython = Join-Path $scannerEnv 'Scripts\python.exe'
& $scannerPython -m pip install -r "$repo\requirements-scanner.txt"
if ($LASTEXITCODE -ne 0) { throw 'Scanner dependency installation failed.' }
& $scannerPython -m pip freeze > "$checkRoot\scanner-freeze.txt"
if ($LASTEXITCODE -ne 0) { throw 'Unable to record scanner dependencies.' }
foreach ($test in 'integration_catalog', 'integration_stub', 'integration_openai') {
    & $scannerPython "$repo\tests\$test.py" *> "$checkRoot\$test.log"
    if ($LASTEXITCODE -ne 0) { throw "Scanner check failed. See $checkRoot\$test.log" }
}
```

These checks use the installed scanner with synthetic targets and transports. A live provider compatibility result requires separate evidence. Preserve the logs and test receipt outside the checkout.
