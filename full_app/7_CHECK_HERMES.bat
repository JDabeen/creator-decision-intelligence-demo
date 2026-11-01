@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Hermes API Diagnostics
if not exist ".venv\Scripts\python.exe" (
    echo 기존 Python 설치가 보이지 않습니다. 먼저 0_START_HERE.bat 설치를 확인하세요.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "hermes_integration\diagnose.py"
echo.
echo 위 진단 결과만 복사하거나 캡처해 주세요. API KEY는 전송하지 마세요.
pause
