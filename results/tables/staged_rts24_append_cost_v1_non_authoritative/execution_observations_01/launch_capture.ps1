param(
    [Parameter(Mandatory=$true)][ValidateSet('preparation','measurement')][string]$Role,
    [string]$RegistrationSha
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../../..')).Path
$scriptRelative = 'results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/launch_capture.ps1'
$costBase = Split-Path -Parent $PSScriptRoot
$roleRoot = Join-Path $PSScriptRoot ($Role + '_01')
$ownerPath = Join-Path $PSScriptRoot ($Role + '_01.owner')
function Get-CostPin([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Nonregular observation file.' }
    return @{ bytes=$item.Length; sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
function Write-CostJson([string]$Path,$Value) {
    $data = [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 12 -Compress) + "`n")
    $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try { $stream.Write($data,0,$data.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}
$scriptPin = Get-CostPin $PSCommandPath
if ($Role -eq 'measurement' -and $RegistrationSha -notmatch '^[0-9a-f]{64}$') { throw 'Exact registration SHA required.' }
$requestPath = Join-Path $costBase 'cost_preparation_01/request.json'
if ($Role -eq 'measurement') {
    $priorRequest = Get-Content -LiteralPath $requestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($priorRequest.pins.direct.$scriptRelative.sha256 -ne $scriptPin.sha256) { throw 'Prepared capture script differs.' }
}
# A retained create-new owner prevents both duplicate launch and log overwrite.
$owner = [IO.File]::Open($ownerPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
try { $owner.WriteByte(1); $owner.Flush($true) } finally { $owner.Dispose() }
if (Test-Path -LiteralPath $roleRoot) { throw 'External role directory already exists.' }
[void][IO.Directory]::CreateDirectory($roleRoot)
$costArguments = @('-B','-s','experiments/staged_rts24_append_cost_probe_v1.py')
if ($Role -eq 'preparation') { $costArguments += '--prepare-registration'; $targetName = 'cost_preparation_01' }
else { $costArguments += @('--launch','--registration-sha',$RegistrationSha); $targetName = 'cost_probe_01' }
$logPath = Join-Path $roleRoot 'stdout.log'
$logStream = [IO.File]::Open($logPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$logWriter = [IO.StreamWriter]::new($logStream,[Text.UTF8Encoding]::new($false))
$intentPath = Join-Path $roleRoot 'intent.json'
Write-CostJson $intentPath @{ authority='DRAFT_NONAUTHORITATIVE'; role=$Role; script_relative=$scriptRelative;
    script_pin=$scriptPin; executable='D:/Miniconda3/envs/compute/python.exe'; argv=$costArguments;
    cwd=$repoRoot; controller_timing_path=($targetName + '/controller_timings.json'); log='stdout.log';
    no_retry=$true; native_authorized=$false; created_utc=[DateTime]::UtcNow.ToString('o') }
$startedUtc = [DateTime]::UtcNow.ToString('o')
$costExit = 255
$captureError = $null
$costClock = [Diagnostics.Stopwatch]::StartNew()
Push-Location -LiteralPath $repoRoot
try {
    $ErrorActionPreference = 'Continue'
    & 'D:/Miniconda3/envs/compute/python.exe' @costArguments 2>&1 | ForEach-Object {
        $logWriter.WriteLine([string]$_)
        Write-Output $_
    }
    $costExit = $LASTEXITCODE
} catch { $captureError = $_.Exception.Message }
finally {
    $ErrorActionPreference = 'Stop'
    $costClock.Stop()
    Pop-Location
    $logWriter.Flush(); $logStream.Flush($true); $logWriter.Dispose()
}
$timingPin = $null
$accepted = $false
try {
    if ((Get-CostPin $PSCommandPath).sha256 -ne $scriptPin.sha256) { throw 'Capture script changed during execution.' }
    $timingPath = Join-Path $costBase ($targetName + '/controller_timings.json')
    if (Test-Path -LiteralPath $timingPath) { $timingPin = Get-CostPin $timingPath }
    if ($costExit -eq 0) {
        if ($null -eq $timingPin) { throw 'Python exit0 without final controller timing.' }
        $timing = Get-Content -LiteralPath $timingPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($timing.accepted_success -ne $true) { throw 'Controller timing did not accept success.' }
        $request = Get-Content -LiteralPath $requestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($request.pins.direct.$scriptRelative.sha256 -ne $scriptPin.sha256) { throw 'Preparation request did not bind capture script.' }
        $accepted = $true
    }
} catch { $captureError = $_.Exception.Message }
$externalExit = $costExit
if (-not $accepted -and $externalExit -eq 0) { $externalExit = 90 }
$capture = @{
    authority='DRAFT_NONAUTHORITATIVE'; role=$Role; started_utc=$startedUtc; finished_utc=[DateTime]::UtcNow.ToString('o');
    executable='D:/Miniconda3/envs/compute/python.exe'; argv=$costArguments; python_exit_code=$costExit; exit_code=$externalExit;
    accepted_success=$accepted; external_wall_seconds=$costClock.Elapsed.TotalSeconds; capture_error=$captureError;
    timing_scope='PowerShell pipeline before Python startup through return and stdout capture completion';
    capture_excludes='post-process validation, log flush/dispose, hashing and publication of this external observation';
    controller_timing_pin=$timingPin; script_pin=$scriptPin; intent_pin=(Get-CostPin $intentPath); log_pin=(Get-CostPin $logPath);
    native_authorized=$false; formal_result=$false
}
Write-CostJson (Join-Path $roleRoot 'capture.json') $capture
Write-Output ($capture | ConvertTo-Json -Depth 8 -Compress)
exit $externalExit
