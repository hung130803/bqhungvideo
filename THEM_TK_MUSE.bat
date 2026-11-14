@echo off
chcp 65001 >nul
setlocal
echo ==== THEM TAI KHOAN MUSE (app tu nhan, khong can sua cai dat) ====
if not exist "D:\MuseAI-API\.venv\Scripts\muse-ai.exe" (echo [LOI] Chua cai MuseAI-API. Chay CAI_MUSE.bat truoc. & pause & exit /b 1)
set /p TEN=Dat ten ngan cho tai khoan (vd tk2, chi chu va so): 
if "%TEN%"=="" (echo [LOI] Chua nhap ten. & pause & exit /b 1)
set "DIR=D:\MuseAI-API\.muse-state-%TEN%"
if exist "%DIR%\cookies.json" echo Tai khoan "%TEN%" da co - se dang nhap lai.
set /p EMAIL=Nhap email tai khoan Muse: 
"D:\MuseAI-API\.venv\Scripts\muse-ai.exe" --state-dir "%DIR%" login --email "%EMAIL%"
echo.
"D:\MuseAI-API\.venv\Scripts\muse-ai.exe" --state-dir "%DIR%" ping
echo.
echo Neu co HTTP 200 la XONG. Mo lai app de dung them tai khoan nay.
pause
