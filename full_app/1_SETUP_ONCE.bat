@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================
echo YouTube Content Consultant v2.2 - first setup
echo ================================================

if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/3] Installing packages...
python -m pip install --upgrade pip
if errorlevel 1 goto install_failed
python -m pip install -r requirements.txt
if errorlevel 1 goto install_failed
python -m pip check
if errorlevel 1 goto install_failed

if not exist ".env" (
    echo [3/3] Creating .env file...
    copy .env.example .env > nul
    echo.
    echo .env was created. Put your API keys in it, then run 2_RUN_APP.bat.
    notepad .env
) else (
    echo [3/3] .env already exists.
)

echo.
echo Setup finished.
pause
exit /b 0

:install_failed
echo.
echo [ERROR] Python package setup failed. Hermes will NOT be started.
pause
exit /b 1
