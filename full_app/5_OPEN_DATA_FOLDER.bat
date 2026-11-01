@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" open_data_folder.py
) else (
  py open_data_folder.py
)
