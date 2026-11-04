@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
rem Don Part + video goc dai trong thu muc kenh (giu video shorts) - xem tools\don_video_kenh.py
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0tools\don_video_kenh.py"
) else (
  echo Khong thay .venv - chay setup.bat truoc.
)
echo.
pause
