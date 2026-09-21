@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -B tools\restore_database.py
) else (
  py -3.12 -B tools\restore_database.py
)
pause
