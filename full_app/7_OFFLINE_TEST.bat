@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Install dependencies first with 0_START_WITH_HERMES.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" validate_release.py
set "EXITCODE=%ERRORLEVEL%"
pause
exit /b %EXITCODE%
