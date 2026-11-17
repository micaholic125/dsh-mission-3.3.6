@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem ============================================================
rem  一键恢复原版（备份 -> 删除游戏目录下的 rulesmo.ini -> 确认）
rem  恢复前请完全退出游戏（脚本也会检查并拒绝）
rem  游戏目录默认自动探测；也可以指定，例如：
rem     一键恢复原版.bat --game-dir "D:\Mental Omega"
rem  或先设置环境变量：set MO_GAME_DIR=D:\Mental Omega
rem ============================================================

set "PY="
if defined PYTHON call :trypy "%PYTHON%"
if not defined PY call :trypy python
if not defined PY call :trypy py
if not defined PY call :findpy

if not defined PY (
  echo.
  echo  [错误] 没有找到 Python。
  echo  本工具需要 Python 3.8 或更高版本，下载地址：https://www.python.org/downloads/
  echo  安装时请勾选 "Add Python to PATH"；或设置环境变量 PYTHON 指向 python.exe。
  echo.
  pause
  exit /b 1
)

set PYTHONIOENCODING=utf-8
echo  使用的 Python: %PY%
echo.
"%PY%" tools\deploy.py rollback %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo  恢复未完成（退出码 %RC%）。请检查上面的提示；如果是找不到游戏目录，可以这样指定：
  echo     一键恢复原版.bat --game-dir "D:\Mental Omega"
  echo  或先设置环境变量：set MO_GAME_DIR=D:\Mental Omega
)
echo.
pause
exit /b %RC%

:trypy
"%~1" -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=%~1"
exit /b 0

:findpy
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined PY call :trypy "%%~fD\python.exe"
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do if not defined PY call :trypy "%%~fD\python.exe"
for /d %%D in ("%ProgramFiles%\Python3*") do if not defined PY call :trypy "%%~fD\python.exe"
if not defined PY call :trypy "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
exit /b 0
