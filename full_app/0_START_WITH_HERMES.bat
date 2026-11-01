@echo off
chcp 65001 > nul
cd /d "%~dp0"
title YouTube Content Consultant + Hermes Docker

echo ==================================================
echo YouTube Content Consultant + Hermes (Docker)
echo ==================================================

if not exist ".venv\Scripts\python.exe" (
    echo First run: installing the original app dependencies...
    call 1_SETUP_ONCE.bat
    if errorlevel 1 goto fail
)
if not exist ".env" (
    echo Please add YOUTUBE_API_KEY and OPENAI_API_KEY to .env first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
python -c "import streamlit, pandas, numpy, openai, googleapiclient, youtube_transcript_api, dotenv"
if errorlevel 1 (
    echo Missing app packages. Repairing installation...
    call 1_SETUP_ONCE.bat
    if errorlevel 1 goto fail
)
python "hermes_integration\launcher.py" start
if errorlevel 1 goto fail
set "YRA_CRITIC_BACKEND=hermes"
python -m streamlit run app.py
exit /b %errorlevel%

:fail
echo.
echo Hermes startup failed. The original 0_START_HERE.bat is unchanged and still works.
pause
exit /b 1
