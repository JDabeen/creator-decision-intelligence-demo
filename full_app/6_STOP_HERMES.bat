@echo off
chcp 65001 > nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "hermes_integration\launcher.py" stop
) else (
  echo Python environment not found; open Docker Desktop to stop the container.
)
pause
