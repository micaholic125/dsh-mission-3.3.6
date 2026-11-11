@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
if not exist "_internal\install.ps1" (
  echo [ERROR] _internal\install.ps1 not found.
  echo Do not move files out of this folder. Re-extract the zip and try again.
  echo.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "_internal\install.ps1"
echo.
pause
