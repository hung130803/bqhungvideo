@echo off
rem Dong goi ban moi va cap nhat D:\BQHungVideo - xem tools\dong_goi_cap_nhat.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dong_goi_cap_nhat.ps1" %*
echo.
pause
