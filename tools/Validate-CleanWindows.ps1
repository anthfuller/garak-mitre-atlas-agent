param(
    [Parameter(Mandatory = $true)]
    [string]$BundlePath,
    [string]$CheckRoot = (Join-Path $env:LOCALAPPDATA ('GarakPlaybook-check-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))),
    [string]$ReuseEnvironmentsFrom
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
$savedPythonIOEncoding = $env:PYTHONIOENCODING
$env:PYTHONPATH = $null
$env:PYTHONHOME = $null
# Redirected Python output otherwise uses the Windows legacy code page, which
# cannot represent Garak's Unicode log markers. File-reading defaults are unchanged.
$env:PYTHONIOENCODING = 'utf-8'
$receipt['python_io_encoding'] = 'utf-8'
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
    if ($ReuseEnvironmentsFrom) {
        $previous = (Resolve-Path -LiteralPath $ReuseEnvironmentsFrom).Path
        $previousReceiptPath = Join-Path $previous 'windows-validation.json'
        $previousReceipt = Get-Content -LiteralPath $previousReceiptPath -Raw | ConvertFrom-Json
        foreach ($step in @('test-install.log', 'scanner-install.log')) {
            $passed = @($previousReceipt.checks | Where-Object { $_.log -eq $step -and $_.exit_code -eq 0 })
            if ($passed.Count -ne 1) { throw "Previous checkpoint has no successful $step receipt." }
        }
        foreach ($name in @('requirements-research.txt', 'requirements-scanner.txt')) {
            $oldHash = (Get-FileHash -LiteralPath (Join-Path "$previous\garak-playbook" $name) -Algorithm SHA256).Hash
            $newHash = (Get-FileHash -LiteralPath (Join-Path $repo $name) -Algorithm SHA256).Hash
            if ($oldHash -ne $newHash) { throw "Requirements changed: $name. Environment reuse refused." }
        }
        $testEnv = Join-Path $previous 'test-env'
        $scannerEnv = Join-Path $previous 'scanner-env'
        foreach ($environment in @($testEnv, $scannerEnv)) {
            if (-not (Test-Path -LiteralPath (Join-Path $environment 'Scripts\python.exe') -PathType Leaf)) {
                throw "Previous validation Python is missing: $environment"
            }
        }
        $receipt['reused_environments_from'] = $previous
        $receipt['previous_receipt_sha256'] = (Get-FileHash -LiteralPath $previousReceiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $receipt.note = 'Fresh checkout; test/scanner environments reused from recorded successful installations with unchanged requirements/package inventories. UTF-8 output; synthetic responses only; desktop actions mocked.'
        Write-Host 'Reusing both installed validation environments. No dependency installation; previous checkout and receipts preserved.'
    } else {
        Invoke-Checked -Executable 'py' -Arguments @('-3.11', '-m', 'venv', $testEnv) -LogName 'test-env.log'
    }
    $testPython = Join-Path $testEnv 'Scripts\python.exe'
    if (-not $ReuseEnvironmentsFrom) {
        Invoke-Checked -Executable $testPython -Arguments @('-m', 'pip', 'install', '-r', "$repo\requirements-research.txt") -LogName 'test-install.log'
    }
    Invoke-Checked -Executable $testPython -Arguments @('-m', 'pip', 'freeze') -LogName 'test-freeze.txt'
    if ($ReuseEnvironmentsFrom) {
        $before = @(Get-Content -LiteralPath "$previous\test-freeze.txt")
        $after = @(Get-Content -LiteralPath "$CheckRoot\test-freeze.txt")
        if (Compare-Object -ReferenceObject $before -DifferenceObject $after) { throw 'Test package inventory changed; reuse refused.' }
    }
    Invoke-Checked -Executable $testPython -Arguments @("$repo\tools\run_tests.py", '--out', "$CheckRoot\test-results") -LogName 'test-console.log'
    $tests = Get-Content -LiteralPath "$CheckRoot\test-results\test-result.json" -Raw | ConvertFrom-Json
    if ($tests.status -ne 'passed' -or $tests.skipped -ne 0 -or $tests.commit -ne $receipt.commit) {
        throw 'Complete tests must pass with zero skips on the cloned commit.'
    }
    if (-not $ReuseEnvironmentsFrom) {
        Invoke-Checked -Executable 'py' -Arguments @('-3.11', '-m', 'venv', $scannerEnv) -LogName 'scanner-env.log'
    }
    $scannerPython = Join-Path $scannerEnv 'Scripts\python.exe'
    if (-not $ReuseEnvironmentsFrom) {
        Invoke-Checked -Executable $scannerPython -Arguments @('-m', 'pip', 'install', '-r', "$repo\requirements-scanner.txt") -LogName 'scanner-install.log'
    }
    Invoke-Checked -Executable $scannerPython -Arguments @('-m', 'pip', 'freeze') -LogName 'scanner-freeze.txt'
    if ($ReuseEnvironmentsFrom) {
        $before = @(Get-Content -LiteralPath "$previous\scanner-freeze.txt")
        $after = @(Get-Content -LiteralPath "$CheckRoot\scanner-freeze.txt")
        if (Compare-Object -ReferenceObject $before -DifferenceObject $after) { throw 'Scanner package inventory changed; reuse refused.' }
    }
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
    $env:PYTHONIOENCODING = $savedPythonIOEncoding
    $receipt['finished_at'] = (Get-Date).ToUniversalTime().ToString('o')
    $receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $CheckRoot 'windows-validation.json') -Encoding UTF8
    Write-Host "Windows validation: $($receipt.status)"
    Write-Host "Receipt and logs: $CheckRoot"
    Write-Host 'No live model scan, API key, Langflow session, or paid request is part of this check.'
}
if ($receipt.status -ne 'passed') { exit 2 }
