@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Start the app once to set up Python.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" export_public_portfolio.py
set "EXITCODE=%ERRORLEVEL%"
pause
exit /b %EXITCODE%
