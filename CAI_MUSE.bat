@echo off
chcp 65001 >nul
setlocal
echo ==== CAI MuseAI-API (khong dung vao app BQ Hung Video) ====
echo.

where git >nul 2>nul || (echo [LOI] May chua co Git. Cai tai https://git-scm.com roi chay lai. & pause & exit /b 1)
py -3.12 --version >nul 2>nul || (echo [LOI] May chua co Python 3.12. Cai tai https://www.python.org roi chay lai. & pause & exit /b 1)

if not exist "D:\MuseAI-API\.git" (
  echo [1/4] Tai ma ve D:\MuseAI-API ...
  git clone https://github.com/minhquan130599/MuseAI-API.git "D:\MuseAI-API" || (echo [LOI] Tai that bai. & pause & exit /b 1)
) else (
  echo [1/4] Da co D:\MuseAI-API - giu nguyen ban da soat, KHONG cap nhat.
)

cd /d "D:\MuseAI-API"
if not exist ".venv\Scripts\python.exe" (
  echo [2/4] Tao moi truong rieng ...
  py -3.12 -m venv .venv || (echo [LOI] Khong tao duoc moi truong. & pause & exit /b 1)
)

echo [3/4] Cai goi ...
".venv\Scripts\python.exe" -m pip install -U pip >nul
".venv\Scripts\python.exe" -m pip install -U -e ".[dev]" || (echo [LOI] Cai goi that bai. & pause & exit /b 1)

echo.
echo [4/4] Dang nhap Muse - ma OTP se gui ve email cua anh.
set /p EMAIL=Nhap email tai khoan Muse:
".venv\Scripts\muse-ai.exe" --state-dir "D:\MuseAI-API\.muse-state" login --email "%EMAIL%"

echo.
echo ==== Kiem tra ket noi ====
".venv\Scripts\muse-ai.exe" --state-dir "D:\MuseAI-API\.muse-state" ping
echo.
echo Neu dong tren co HTTP 200 la XONG. Nhan "xong" cho Claude.
pause
