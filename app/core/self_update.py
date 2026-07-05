"""TỰ CẬP NHẬT bản .exe (PyInstaller onedir) — tải zip từ GitHub Release,
giải nén, rồi hoán đổi file khi app đóng.

Luồng:
  1. download(url, ...)      — tải zip về DATA_DIR/updates/ (có callback tiến độ)
  2. extract(zip)            — giải nén, tìm thư mục app mới (chứa file .exe)
  3. launch_swap_script(...) — viết + chạy script .bat nền: đợi app thoát,
                               copy _internal mới cạnh bản cũ, hoán đổi bằng
                               2 lần đổi tên (nhanh, có KHÔI PHỤC nếu lỗi),
                               chép file lẻ (exe...), mở lại app, dọn rác.
  Caller (UI) sau bước 3 chỉ việc thoát app.

Chỉ hỗ trợ khi chạy bản đóng gói (sys.frozen). Bản dev -> UI mở trang tải.
"""
from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from config import DATA_DIR

ProgressFn = Optional[Callable[[int, int], None]]   # (đã_tải_bytes, tổng_bytes)

UPDATES_DIR = DATA_DIR / "updates"


class UpdateCanceled(Exception):
    """Người dùng bấm hủy giữa lúc tải."""


def can_auto_update() -> bool:
    """Chỉ tự cập nhật được khi đang chạy bản .exe đóng gói (onedir)."""
    if not getattr(sys, "frozen", False):
        return False
    app_dir = Path(sys.executable).parent
    return (app_dir / "_internal").is_dir()


def cleanup_leftovers() -> None:
    """Dọn rác của lần cập nhật trước (gọi lúc khởi động, best-effort).

    KHÔNG xóa apply_update.bat/update.log: ngay sau khi cập nhật, script .bat
    có thể VẪN đang chạy phần dọn dẹp (cmd đọc file .bat từ đĩa từng dòng —
    xóa giữa chừng sẽ làm hỏng script). Bat tự xóa khi xong; zip/thư mục
    giải nén/_internal.old thì dọn ở đây phòng khi bat thất bại giữa chừng.
    """
    import shutil
    try:
        if UPDATES_DIR.exists():
            for p in UPDATES_DIR.iterdir():
                if p.suffix == ".zip":
                    try:
                        p.unlink()
                    except OSError:
                        pass
                elif p.is_dir() and p.name == "new":
                    shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass
    if getattr(sys, "frozen", False):
        old = Path(sys.executable).parent / "_internal.old"
        if old.is_dir():
            try:
                shutil.rmtree(old, ignore_errors=True)
            except OSError:
                pass


def download(url: str, tag: str, on_progress: ProgressFn = None,
             is_canceled: Optional[Callable[[], bool]] = None) -> Path:
    """Tải zip bản mới về UPDATES_DIR. Trả đường dẫn zip. Ném lỗi nếu thất bại."""
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPDATES_DIR / f"update_{tag}.zip"
    req = urllib.request.Request(url, headers={
        "User-Agent": "ai-content-studio-updater",
        "Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=30) as r:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as f:
            while True:
                if is_canceled and is_canceled():
                    raise UpdateCanceled()
                chunk = r.read(1 << 18)          # 256KB
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if on_progress:
                    on_progress(got, total)
    if dest.stat().st_size < 1 << 20:            # < 1MB chắc chắn không phải bản app
        raise RuntimeError("File tải về quá nhỏ, có thể lỗi mạng.")
    return dest


def extract(zip_path: Path) -> Path:
    """Giải nén zip, trả thư mục app MỚI (thư mục chứa file .exe)."""
    out = UPDATES_DIR / "new"
    import shutil
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)
    # zip của release là "BQHungVideo-vX.zip" chứa 1 thư mục "BQHungVideo/"
    exes = sorted(out.rglob("*.exe"))
    for e in exes:
        if (e.parent / "_internal").is_dir():
            return e.parent
    raise RuntimeError("Gói cập nhật không đúng định dạng (không thấy app bên trong).")


def launch_swap_script(new_dir: Path, zip_path: Path) -> None:
    """Viết + chạy script .bat NỀN thực hiện hoán đổi sau khi app thoát.

    Script chỉ dùng ASCII (tránh lỗi codepage cmd). Trình tự an toàn:
      - robocopy _internal mới -> <app>/_internal.new (copy xong mới đụng bản cũ)
      - đợi app (PID) thoát hẳn
      - ren _internal -> _internal.old ; ren _internal.new -> _internal
        (lỗi ở đâu -> đổi tên ngược lại, mở bản cũ, KHÔNG mất app)
      - copy file lẻ tầng trên (exe mới...)
      - mở lại app, dọn thư mục tạm
    """
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)
    app_dir = Path(sys.executable).parent
    exe_name = Path(sys.executable).name
    pid = os.getpid()
    bat = UPDATES_DIR / "apply_update.bat"
    log = UPDATES_DIR / "update.log"

    script = f"""@echo off
rem BQ Hung Video auto-update (generated) - safe swap with rollback
rem chcp 65001: doc phan con lai cua file theo UTF-8 -> duong dan co dau OK
chcp 65001 >nul
set SRC={new_dir}
set DST={app_dir}
set EXE={exe_name}
set PID={pid}
set UPD={UPDATES_DIR}
set tries=0

echo [1/5] copy new files... > "{log}"
robocopy "%SRC%\\_internal" "%DST%\\_internal.new" /E /R:3 /W:1 >> "{log}" 2>&1
if errorlevel 8 goto fail_apprunning

echo [2/5] wait for app exit (pid %PID%)... >> "{log}"
:wait
rem da loc theo PID -> chi can thay ten exe la app con chay
tasklist /FI "PID eq %PID%" /NH 2>nul | findstr /I /C:"%EXE%" >nul 2>&1
if errorlevel 1 goto exited
set /a tries+=1
if %tries% GEQ 240 goto fail_apprunning
ping -n 2 127.0.0.1 >nul
goto wait
:exited
ping -n 2 127.0.0.1 >nul

echo [3/5] swap _internal... >> "{log}"
if exist "%DST%\\_internal.old" rmdir /S /Q "%DST%\\_internal.old" >nul 2>&1
ren "%DST%\\_internal" "_internal.old" >> "{log}" 2>&1
if errorlevel 1 goto fail
ren "%DST%\\_internal.new" "_internal" >> "{log}" 2>&1
if errorlevel 1 goto rollback

echo [4/5] copy top-level files... >> "{log}"
robocopy "%SRC%" "%DST%" /R:3 /W:1 >> "{log}" 2>&1
if errorlevel 8 goto rollback2

echo [5/5] relaunch + cleanup >> "{log}"
start "" "%DST%\\%EXE%"
rmdir /S /Q "%DST%\\_internal.old" >nul 2>&1
rmdir /S /Q "%UPD%\\new" >nul 2>&1
del /Q "{zip_path}" >nul 2>&1
del /Q "%~f0" >nul 2>&1
exit /b 0

:rollback2
rem file tang tren loi -> tra _internal cu ve cho cu
ren "%DST%\\_internal" "_internal.new" >> "{log}" 2>&1
:rollback
ren "%DST%\\_internal.old" "_internal" >> "{log}" 2>&1
:fail
rem app DA thoat -> don dep roi mo lai BAN CU (khong mat app)
echo UPDATE FAILED - restart old version >> "{log}"
if exist "%DST%\\_internal.new" rmdir /S /Q "%DST%\\_internal.new" >nul 2>&1
start "" "%DST%\\%EXE%"
exit /b 1

:fail_apprunning
rem app CON DANG chay (copy loi / doi qua lau) -> chi don dep, KHONG mo them app
echo UPDATE FAILED while app still running - cleanup only >> "{log}"
if exist "%DST%\\_internal.new" rmdir /S /Q "%DST%\\_internal.new" >nul 2>&1
exit /b 1
"""
    # UTF-8 KHÔNG BOM: cmd đọc dòng đầu (@echo off) dạng ASCII, sau chcp 65001
    # mọi đường dẫn unicode (tên user có dấu...) được đọc đúng.
    bat.write_text(script, encoding="utf-8", newline="\r\n")
    # CREATE_NO_WINDOW: cmd + mọi lệnh con (robocopy/ping) dùng chung console ẨN
    # (KHÔNG dùng DETACHED_PROCESS — sẽ làm mỗi lệnh con nháy 1 cửa sổ đen).
    # Tiến trình con Windows KHÔNG chết theo app cha -> script sống sau khi app thoát.
    flags = 0
    if sys.platform == "win32":
        flags = (subprocess.CREATE_NO_WINDOW
                 | subprocess.CREATE_NEW_PROCESS_GROUP)
    subprocess.Popen(["cmd.exe", "/c", str(bat)], cwd=str(UPDATES_DIR),
                     creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
