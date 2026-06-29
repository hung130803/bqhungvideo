@echo off
chcp 65001 >nul
title AI Content Studio
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay bam dup vao file  setup.bat  truoc.
    pause
    exit /b 1
)

echo Dang mo AI Content Studio...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo [App da dong hoac co loi] Chup man hinh phan loi ben tren gui lai.
    pause
)
