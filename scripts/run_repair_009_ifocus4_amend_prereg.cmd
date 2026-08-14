@echo off
REM Repair-009 ifocus4: amend preregistration after implementation-hash-only runner fix.
REM Requires published candidate_frontier and no joint_ac directory.

setlocal
cd /d "%~dp0.."
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set PYTHONPATH=%CD%

set CONFIG=configs\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml
set RUNNER=experiments\run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py
set PYTHON=D:\conda_envs\compute\python.exe
set OUTPUT_ROOT=results\tables\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4
set LOG_DIR=results\logs\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4
set FRONTIER=%OUTPUT_ROOT%\candidate_frontier\summary.json

if not exist "%FRONTIER%" (
  echo ERROR: candidate frontier missing: %FRONTIER%
  exit /b 1
)

if exist "%OUTPUT_ROOT%\joint_ac" (
  echo ERROR: joint_ac already exists under %OUTPUT_ROOT%
  exit /b 1
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set LOG=%LOG_DIR%\amend_prereg_%STAMP%.log

echo Starting amend-preregistration-implementation
echo CONFIG=%CONFIG%
echo OUTPUT_ROOT=%OUTPUT_ROOT%
echo LOG=%LOG%

"%PYTHON%" -u -B "%RUNNER%" --config "%CONFIG%" --stage "amend-preregistration-implementation" 1>"%LOG%" 2>&1
set EXITCODE=%ERRORLEVEL%
echo Exit code: %EXITCODE%
echo Log: %LOG%
exit /b %EXITCODE%
