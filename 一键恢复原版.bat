@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set "PY="
call :trypy python
if not defined PY call :trypy py
if not defined PY call :trypy "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if not defined PY call :trypy "D:\DeepSeek-Harness\home\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

if not defined PY (
  echo.
  echo  [ERROR] Python not found on this machine.
  echo  Workaround: open DSH and run  python tools\deploy.py rollback
  echo.
  pause
  exit /b 1
)

set PYTHONIOENCODING=utf-8
echo   using python: %PY%
echo.
"%PY%" tools\deploy.py rollback
echo.
pause
exit /b 0

:trypy
%~1 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=%~1"
exit /b 0
