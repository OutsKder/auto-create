@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-byte-dev.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] One-click launcher failed.
  echo Please check the error above.
  pause
  exit /b 1
)
