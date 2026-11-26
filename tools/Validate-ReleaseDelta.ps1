param(
    [Parameter(Mandatory = $true)][string]$BundlePath,
    [Parameter(Mandatory = $true)][string]$WindowsReceipt,
    [string]$CheckRoot = (Join-Path $env:LOCALAPPDATA ('GarakPlaybook-delta-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run in normal Windows PowerShell on Windows.' }
$BundlePath = (Resolve-Path -LiteralPath $BundlePath).Path
$WindowsReceipt = (Resolve-Path -LiteralPath $WindowsReceipt).Path
if (Test-Path -LiteralPath $CheckRoot) { throw 'Check directory already exists; existing evidence is preserved.' }
New-Item -ItemType Directory -Path $CheckRoot | Out-Null
$repo = Join-Path $CheckRoot 'garak-playbook'
$receipt = [ordered]@{
    status = 'incomplete'; started_at = (Get-Date).ToUniversalTime().ToString('o')
    platform = [Environment]::OSVersion.VersionString; powershell = $PSVersionTable.PSVersion.ToString()
    base_commit = '09e812807924e9c55c9d96a507fe0beac637f752'; candidate_commit = $null
    base_receipt_sha256 = (Get-FileHash -LiteralPath $WindowsReceipt -Algorithm SHA256).Hash.ToLowerInvariant()
    bundle_sha256 = (Get-FileHash -LiteralPath $BundlePath -Algorithm SHA256).Hash.ToLowerInvariant()
    checks = @(); live_model_calls = $false; paid_calls = $false; dependency_installation = $false
    scope = 'New release-profile, headroom and OpenAI unit checks plus public quick-start CLI. Not a rerun of the original full Windows validator.'
}
$savedPythonPath = $env:PYTHONPATH
$savedPythonHome = $env:PYTHONHOME
$savedPythonIOEncoding = $env:PYTHONIOENCODING
$savedBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONPATH = $null
$env:PYTHONHOME = $null
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments, [string]$LogName)
    $log = Join-Path $CheckRoot $LogName
    Write-Host "Checking $LogName ..."
    $priorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    $global:LASTEXITCODE = $null
    try {
        & $Executable @Arguments *> $log
        $code = $global:LASTEXITCODE
    } finally { $ErrorActionPreference = $priorPreference }
    $receipt.checks += [pscustomobject]@{ log = $LogName; exit_code = $code }
    if ($null -eq $code -or $code -ne 0) { throw "Delta step failed (exit $code). See $log" }
}
try {
    $previous = Get-Content -LiteralPath $WindowsReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($previous.status -ne 'passed' -or $previous.commit -ne $receipt.base_commit) {
        throw 'Expected the passed Windows receipt for 09e8128; no environment or scan changed.'
    }
    $previousFolder = Split-Path -Parent $WindowsReceipt
    $environmentRoot = if ($previous.reused_environments_from) { $previous.reused_environments_from } else { $previousFolder }
    $testPython = Join-Path $environmentRoot 'test-env\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $testPython -PathType Leaf)) { throw 'The recorded test environment is unavailable; no installation attempted.' }
    $receipt['test_environment'] = $environmentRoot
    Invoke-Checked -Executable 'git' -Arguments @('clone', $BundlePath, $repo) -LogName 'clone.log'
    $candidate = & git -C $repo rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Could not identify candidate commit.' }
    $receipt.candidate_commit = $candidate.Trim()
    Invoke-Checked -Executable 'git' -Arguments @('-C', $repo, 'diff', '--exit-code', $receipt.base_commit, 'HEAD', '--', 'requirements-scanner.txt', 'requirements-research.txt') -LogName 'requirements-unchanged.log'
    Invoke-Checked -Executable $testPython -Arguments @('-m', 'pip', 'freeze') -LogName 'test-freeze.txt'
    $oldFreeze = Get-Content -LiteralPath (Join-Path $previousFolder 'test-freeze.txt') | Sort-Object
    $newFreeze = Get-Content -LiteralPath (Join-Path $CheckRoot 'test-freeze.txt') | Sort-Object
    if (Compare-Object $oldFreeze $newFreeze) { throw 'Recorded test packages changed; no install or automatic repair attempted.' }
    Push-Location $repo
    try {
        foreach ($test in @('test_release_profile.py', 'test_headroom.py', 'test_openai.py')) {
            Invoke-Checked -Executable $testPython -Arguments @('-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-p', $test, '-v') -LogName ($test + '.log')
        }
        Invoke-Checked -Executable $testPython -Arguments @('-X', 'utf8', 'tests\integration_quickstart.py') -LogName 'quickstart.log'
    } finally { Pop-Location }
    $changes = & git -C $repo status --porcelain
    if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Candidate checkout changed during checks.' }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'; $receipt['error'] = $_.Exception.Message
    Write-Host $receipt.error
} finally {
    $env:PYTHONPATH = $savedPythonPath
    $env:PYTHONHOME = $savedPythonHome
    $env:PYTHONIOENCODING = $savedPythonIOEncoding
    $env:PYTHONDONTWRITEBYTECODE = $savedBytecode
    $receipt['finished_at'] = (Get-Date).ToUniversalTime().ToString('o')
    $receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $CheckRoot 'windows-delta-validation.json') -Encoding UTF8
    Write-Host "Windows delta validation: $($receipt.status)"
    Write-Host "Receipt and logs: $CheckRoot"
    Write-Host 'No dependency installation, live scan, API key, Langflow session or paid request.'
}
if ($receipt.status -ne 'passed') { exit 2 }
