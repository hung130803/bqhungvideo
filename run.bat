@echo off
chcp 65001 >nul
title BQ Hung Video
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay bam dup vao file  setup.bat  truoc.
    pause
    exit /b 1
)

echo Dang mo BQ Hung Video...
REM KHONG xoa cache .pyc nua (26/10/2026): Python TU biet file .py nao doi
REM (so ngay sua + kich thuoc) va chi dich lai dung file do. Xoa het moi lan
REM mo bat app dich lai ~2 MB ma nguon -> mo cham hon, bam Thay giong lan dau
REM cung cham. Neu nghi chay nham ma cu: chay run.bat sach  hoac xoa tay.
if /i "%~1"=="sach" for /d /r "app" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo [App da dong hoac co loi] Chup man hinh phan loi ben tren gui lai.
    pause
)
