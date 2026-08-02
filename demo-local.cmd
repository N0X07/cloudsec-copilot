@echo off
setlocal
title CloudSec Copilot Local Demo - No Docker Download

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\demo.ps1" -Local -Approve -OpenDocs -BaseUri "http://127.0.0.1:8000"
set "DEMO_EXIT=%ERRORLEVEL%"

if "%DEMO_EXIT%"=="0" (
  echo Local demo completed successfully.
  echo Keep the API running for Swagger, then use stop-local-demo.cmd.
) else (
  echo Local demo stopped with exit code %DEMO_EXIT%.
  echo Leave this window open and review the error above.
)

pause
exit /b %DEMO_EXIT%
