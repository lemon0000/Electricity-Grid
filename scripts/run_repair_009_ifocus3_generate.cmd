@echo off
REM Repair-009 ifocus3 generate-candidates (ASCII only; no PowerShell script).
REM Run ONLY after prepare has published:
REM   results\tables\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus3\preregistration\registration.json
REM Expected wall time ~9h after prepare.

setlocal
cd /d "%~dp0.."
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set PYTHONPATH=%CD%

set CONFIG=configs\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml
set RUNNER=experiments\run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py
set PYTHON=D:\conda_envs\compute\python.exe
set OUTPUT_ROOT=results\tables\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus3
set LOG_DIR=results\logs\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus3
set PREREG=%OUTPUT_ROOT%\preregistration\registration.json

if not exist "%PREREG%" (
  echo ERROR: preregistration missing: %PREREG%
  echo Run prepare first.
  exit /b 1
)

if exist results\tables\__pycache__ (
  echo ERROR: unexpected __pycache__ under results\tables - remove before formal run
  exit /b 1
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG=%LOG_DIR%\generate_%STAMP%.log

echo Starting generate-candidates
echo CONFIG=%CONFIG%
echo OUTPUT_ROOT=%OUTPUT_ROOT%
echo LOG=%LOG%

"%PYTHON%" -u -B "%RUNNER%" --config "%CONFIG%" --stage generate-candidates 1>"%LOG%" 2>&1
set EXITCODE=%ERRORLEVEL%
echo Exit code: %EXITCODE%
echo Log: %LOG%
exit /b %EXITCODE%
