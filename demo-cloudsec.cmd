@echo off
setlocal
title CloudSec Copilot Demo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\demo.ps1" -Approve -OpenDocs
set "DEMO_EXIT=%ERRORLEVEL%"
echo.
if "%DEMO_EXIT%"=="0" (
  echo Demo completed successfully.
) else (
  echo Demo stopped with exit code %DEMO_EXIT%.
  echo Leave this window open and review the error above.
)
pause
exit /b %DEMO_EXIT%
