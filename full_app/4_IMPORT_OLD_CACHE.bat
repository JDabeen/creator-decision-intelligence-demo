@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Please run 1_SETUP_ONCE.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python import_old_cache.py
pause
