@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ==================================================
echo YouTube Content Consultant - CURRENT COMPLETE
echo ==================================================

if not exist ".venv\Scripts\python.exe" (
    echo First run detected. Running setup...
    call 1_SETUP_ONCE.bat
)

if not exist ".env" (
    echo .env is missing. Please put your API keys in .env and run this file again.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m streamlit run app.py
pause
