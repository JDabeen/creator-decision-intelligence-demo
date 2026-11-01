@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First install the app using 0_START_WITH_HERMES.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" enable_daily_tracking.py
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" echo Scheduled job was NOT installed. Existing app/data unchanged.
pause
exit /b %CODE%
