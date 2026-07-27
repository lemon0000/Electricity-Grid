[CmdletBinding()]
param(
    [string]$PythonExe = "D:\conda_envs\compute\python.exe",
    [string]$Config = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_006.yaml",
    [ValidateSet("generate-candidates", "run-joint-ac")]
    [string]$Stage = "generate-candidates",
    [string]$AttemptId = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonExe).Path
$ConfigPath = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot $Config)).Path

if (-not $AttemptId) {
    $Prefix = if ($Stage -eq "run-joint-ac") { "joint_repair_006_" } else { "formal_repair_006_" }
    $AttemptId = $Prefix + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
}
if ($AttemptId -notmatch "^[A-Za-z0-9_.-]+$") {
    throw "AttemptId contains unsupported characters: $AttemptId"
}

$LogRoot = Join-Path $ProjectRoot "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_006"
$AttemptRoot = Join-Path $LogRoot $AttemptId
$ProgressPath = Join-Path $AttemptRoot "progress.jsonl"
$StdoutPath = Join-Path $AttemptRoot "launcher.stdout.log"
$StderrPath = Join-Path $AttemptRoot "launcher.stderr.log"
$RequestPath = Join-Path $AttemptRoot "launcher.request.json"
$StartedPath = Join-Path $AttemptRoot "launcher.started.json"
$OutputRoot = Join-Path $ProjectRoot "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_006"
$PreregistrationManifest = Join-Path $OutputRoot "preregistration/SHA256SUMS"
$CandidateFrontierManifest = Join-Path $OutputRoot "candidate_frontier/SHA256SUMS"

if (Test-Path -LiteralPath $ProgressPath) {
    throw "Attempt progress log already exists: $ProgressPath"
}
if ((Test-Path -LiteralPath $StdoutPath) -or (Test-Path -LiteralPath $StderrPath)) {
    throw "Attempt launcher logs already exist: $AttemptRoot"
}
if (-not $DryRun -and -not (Test-Path -LiteralPath $PreregistrationManifest)) {
    throw "repair-006 preregistration is missing: $PreregistrationManifest"
}
if (-not $DryRun -and $Stage -eq "run-joint-ac" -and -not (Test-Path -LiteralPath $CandidateFrontierManifest)) {
    throw "repair-006 candidate frontier is missing: $CandidateFrontierManifest"
}

$Arguments = @(
    "-B",
    "-m",
    "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_006_formal",
    "--config",
    $Config,
    "--stage",
    $Stage,
    "--attempt-id",
    $AttemptId
)
$Record = [ordered]@{
    schema = "rts_gmlc_v4_repair_006_launcher_v1"
    attempt_id = $AttemptId
    stage = $Stage
    requested_utc = [DateTime]::UtcNow.ToString("o")
    project_root = $ProjectRoot
    python_executable = $PythonPath
    config_path = $ConfigPath
    progress_path = $ProgressPath
    stdout_path = $StdoutPath
    stderr_path = $StderrPath
    request_path = $RequestPath
    started_path = $StartedPath
    dry_run = [bool]$DryRun
    pid = $null
}

if ($DryRun) {
    $Record | ConvertTo-Json -Depth 3
    exit 0
}

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
New-Item -ItemType Directory -Path $AttemptRoot | Out-Null
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $RequestPath,
    ($Record | ConvertTo-Json -Depth 3) + [Environment]::NewLine,
    $Utf8NoBom
)
$Process = Start-Process `
    -FilePath $PythonPath `
    -ArgumentList $Arguments `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -WindowStyle Hidden `
    -PassThru
$Record.pid = $Process.Id
$Record["started_utc"] = [DateTime]::UtcNow.ToString("o")
[System.IO.File]::WriteAllText(
    $StartedPath,
    ($Record | ConvertTo-Json -Depth 3) + [Environment]::NewLine,
    $Utf8NoBom
)
$Record | ConvertTo-Json -Depth 3
