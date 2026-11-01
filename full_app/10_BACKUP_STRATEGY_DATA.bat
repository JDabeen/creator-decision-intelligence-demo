@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run 0_START_WITH_HERMES.bat once to install requirements.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" backup_strategy.py
pause
