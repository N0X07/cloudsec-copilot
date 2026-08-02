@echo off
setlocal
title Stop CloudSec Copilot Local Demo

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-local-demo.ps1"
set "STOP_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %STOP_EXIT%
