param(
    [Parameter(Mandatory = $true)]
    [string]$BundlePath,
    [string]$CheckRoot = (Join-Path $env:LOCALAPPDATA ('GarakPlaybook-check-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this validation in Windows PowerShell on Windows.' }
Get-Command git -ErrorAction Stop | Out-Null
Get-Command py -ErrorAction Stop | Out-Null
$BundlePath = (Resolve-Path -LiteralPath $BundlePath).Path
if (Test-Path -LiteralPath $CheckRoot) { throw 'Choose a new check directory; existing environments will not be reused.' }
New-Item -ItemType Directory -Path $CheckRoot -ErrorAction Stop | Out-Null
$CheckRoot = (Resolve-Path -LiteralPath $CheckRoot).Path
$repo = Join-Path $CheckRoot 'garak-playbook'
$receipt = [ordered]@{
    status = 'incomplete'
    started_at = (Get-Date).ToUniversalTime().ToString('o')
    platform = [Environment]::OSVersion.VersionString
    powershell = $PSVersionTable.PSVersion.ToString()
    bundle_sha256 = (Get-FileHash -LiteralPath $BundlePath -Algorithm SHA256).Hash.ToLowerInvariant()
    commit = $null
    checks = @()
    live_model_calls = $false
    paid_calls = $false
    note = 'Fresh test/scanner environments; dependency downloads; synthetic model/MCP responses. Native desktop actions remain mocked.'
}
$savedPythonPath = $env:PYTHONPATH
$savedPythonHome = $env:PYTHONHOME
$env:PYTHONPATH = $null
$env:PYTHONHOME = $null
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments, [string]$LogName)
    $log = Join-Path $CheckRoot $LogName
    Write-Host "Checking $LogName ..."
    # Windows PowerShell can treat native stderr (including ordinary pip/git
    # progress) as an error record. Judge native commands by their exit status.
    $priorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    # Native processes write the global automatic variable. A local variable
    # with the same name would shadow that result and cause a false failure.
    $global:LASTEXITCODE = $null
    try {
        & $Executable @Arguments *> $log
        $code = $global:LASTEXITCODE
    } finally {
        $ErrorActionPreference = $priorPreference
    }
    $receipt.checks += [pscustomobject]@{ log = $LogName; exit_code = $code }
    if ($null -eq $code -or $code -ne 0) { throw "Validation step failed (exit $code). See $log" }
}
try {
    Invoke-Checked -Executable 'py' -Arguments @('-3.11', '--version') -LogName 'python-version.log'
    Invoke-Checked -Executable 'git' -Arguments @('clone', $BundlePath, $repo) -LogName 'clone.log'
    $receipt.commit = (& git -C $repo rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not identify checkout commit.' }
    $testEnv = Join-Path $CheckRoot 'test-env'
    $scannerEnv = Join-Path $CheckRoot 'scanner-env'
    Invoke-Checked -Executable 'py' -Arguments @('-3.11', '-m', 'venv', $testEnv) -LogName 'test-env.log'
    $testPython = Join-Path $testEnv 'Scripts\python.exe'
    Invoke-Checked -Executable $testPython -Arguments @('-m', 'pip', 'install', '-r', "$repo\requirements-research.txt") -LogName 'test-install.log'
    Invoke-Checked -Executable $testPython -Arguments @('-m', 'pip', 'freeze') -LogName 'test-freeze.txt'
    Invoke-Checked -Executable $testPython -Arguments @("$repo\tools\run_tests.py", '--out', "$CheckRoot\test-results") -LogName 'test-console.log'
    $tests = Get-Content -LiteralPath "$CheckRoot\test-results\test-result.json" -Raw | ConvertFrom-Json
    if ($tests.status -ne 'passed' -or $tests.skipped -ne 0 -or $tests.commit -ne $receipt.commit) {
        throw 'Complete tests must pass with zero skips on the cloned commit.'
    }
    Invoke-Checked -Executable 'py' -Arguments @('-3.11', '-m', 'venv', $scannerEnv) -LogName 'scanner-env.log'
    $scannerPython = Join-Path $scannerEnv 'Scripts\python.exe'
    Invoke-Checked -Executable $scannerPython -Arguments @('-m', 'pip', 'install', '-r', "$repo\requirements-scanner.txt") -LogName 'scanner-install.log'
    Invoke-Checked -Executable $scannerPython -Arguments @('-m', 'pip', 'freeze') -LogName 'scanner-freeze.txt'
    foreach ($name in @('integration_quickstart', 'integration_catalog', 'integration_stub', 'integration_openai', 'integration_batch')) {
        Invoke-Checked -Executable $scannerPython -Arguments @("$repo\tests\$name.py") -LogName "$name.log"
    }
    Invoke-Checked -Executable $scannerPython -Arguments @("$repo\tests\integration_batch.py", 'auth-failure') -LogName 'integration_batch-auth-failure.log'
    $changes = & git -C $repo status --porcelain
    if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Validation checkout is dirty or Git status failed.' }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'
    $receipt['error'] = $_.Exception.Message
    Write-Host $receipt.error
} finally {
    $env:PYTHONPATH = $savedPythonPath
    $env:PYTHONHOME = $savedPythonHome
    $receipt['finished_at'] = (Get-Date).ToUniversalTime().ToString('o')
    $receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $CheckRoot 'windows-validation.json') -Encoding UTF8
    Write-Host "Windows validation: $($receipt.status)"
    Write-Host "Receipt and logs: $CheckRoot"
    Write-Host 'No live model scan, API key, Langflow session, or paid request is part of this check.'
}
if ($receipt.status -ne 'passed') { exit 2 }
