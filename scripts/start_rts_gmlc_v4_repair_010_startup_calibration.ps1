[CmdletBinding()]
param(
    [string]$PythonExe = "D:\conda_envs\compute\python.exe",
    [string]$Config = "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_010_calibration_v2.yaml"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = (Resolve-Path -LiteralPath $PythonExe).Path
$ConfigPath = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot $Config)).Path
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUNBUFFERED = "1"

& $PythonPath `
    -u `
    -B `
    -m experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal `
    --config $ConfigPath `
    --stage launch-startup-calibration
exit $LASTEXITCODE
