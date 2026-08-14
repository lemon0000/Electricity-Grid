@echo off
REM Auto-chain: wait for ifocus3 prepare PID then run generate.
D:\conda_envs\compute\python.exe -u -B "%~dp0wait_ifocus3_prepare_then_generate.py"
exit /b %ERRORLEVEL%
