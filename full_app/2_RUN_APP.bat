@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ==================================================
echo YouTube Content Consultant v2.2 Market First
echo Running from: %CD%
echo ==================================================

if not exist ".venv\Scripts\python.exe" (
    echo Please run 1_SETUP_ONCE.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo .env is missing. Please copy your .env into this folder.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m streamlit run app.py
pause
