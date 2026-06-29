@echo off
chcp 65001 >nul
title AI Content Studio - Cai dat
cd /d "%~dp0"

echo ============================================================
echo   AI CONTENT STUDIO - CAI DAT (chi can chay 1 lan)
echo ============================================================
echo.

REM --- Tao moi truong ao bang Python 3.12 ---
echo [1/4] Tao moi truong ao (.venv) bang Python 3.12...
py -3.12 -m venv .venv
if errorlevel 1 (
    echo.
    echo [LOI] Khong tao duoc moi truong ao voi Python 3.12.
    echo       Kiem tra: mo PowerShell go "py -3.12 --version"
    pause
    exit /b 1
)

REM --- Nang cap pip ---
echo [2/4] Nang cap pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

REM --- Cai thu vien ---
echo [3/4] Cai thu vien (lan dau hoi lau, vui long cho)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [LOI] Cai thu vien that bai. Chup man hinh loi gui lai.
    pause
    exit /b 1
)

REM --- Tao file .env neu chua co ---
echo [4/4] Chuan bi file cau hinh .env...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo     Da tao .env. Hay mo bang Notepad de dien API key.
) else (
    echo     Da co .env tu truoc, giu nguyen.
)

echo.
echo ============================================================
echo   XONG! Kiem tra moi truong:
echo ============================================================
".venv\Scripts\python.exe" check_env.py
echo.
echo De mo app: bam dup vao file  run.bat
echo.
pause
