@echo off
chcp 65001 >nul
title BQ Hung Video (ban moi - chay tu ma nguon)
cd /d "%~dp0"
rem ================================================================
rem  CHAY BAN DA TOI UU, DUNG CHUNG DU LIEU VOI BAN .EXE
rem  - Cung kenh, cung video, cung cai dat, cung key (.env) voi
rem    D:\BQHungVideo\BQHungVideo.exe  -> khong phai cai lai gi.
rem  - Muon quay lai ban cu: tat cua so nay, mo BQHungVideo.exe nhu
rem    binh thuong. KHONG mo 2 ban cung luc (app tu chan).
rem ================================================================
if not exist ".venv\Scripts\python.exe" (
    echo Thieu moi truong Python ^(.venv^). Bam dup setup.bat truoc.
    pause
    exit /b 1
)
set "BQ_DATA_DIR=%LOCALAPPDATA%\BQHungVideo"
set "FFMPEG_PATH=%~dp0bin\ffmpeg.exe"
set "FFPROBE_PATH=%~dp0bin\ffprobe.exe"
set "PATH=%~dp0bin;%PATH%"
echo Dang mo BQ Hung Video ban moi...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo [App da dong hoac co loi] Chup man hinh phan loi ben tren gui lai.
    pause
)
