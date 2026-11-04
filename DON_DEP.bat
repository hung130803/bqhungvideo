@echo off
rem Don dep an toan du an - xem tools\don_dep.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\don_dep.ps1" %*
echo.
pause
