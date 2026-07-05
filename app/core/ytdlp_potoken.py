"""
Né màn "Sign in to confirm you're not a bot" của YouTube mà KHÔNG cần cookie.

Cơ chế giống hệt tool tải BQHungDown của bạn: chạy một PO-token provider
(server cục bộ 127.0.0.1:4416, ~46MB) + cài plugin "bgutil" cho yt-dlp.
yt-dlp sẽ tự xin PO token từ server này -> qua được tường chặn bot.

Tất cả best-effort: nếu tải/khởi động provider lỗi thì yt-dlp vẫn tải bình
thường (chỉ là không có token). PO token KHÔNG đổi IP -> tải số lượng cực
lớn vẫn cần proxy, nhưng cho nhu cầu thường ngày là đủ.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from config import DATA_DIR

PORT = 4416
# Provider (Windows x86_64) khớp phiên bản plugin. Đổi cả 2 cùng lúc.
PROVIDER_URL = ("https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs/"
                "releases/download/v0.8.1/bgutil-pot-windows-x86_64.exe")

_POTOKEN_DIR = DATA_DIR / "_potoken"
_PLUGIN_DST = _POTOKEN_DIR / "yt_dlp_plugins" / "extractor"
_PROVIDER_DST = _POTOKEN_DIR / "bgutil-pot.exe"

# Plugin .py đi KÈM trong repo (chạy được trên MỌI máy, không phụ thuộc tool khác).
_BUNDLED_PLUGINS = Path(__file__).resolve().parent / "potoken_plugins"
# Tái dùng provider 46MB nếu máy này tình cờ đã cài BQHungDown (khỏi tải lại).
_PRODOWN_PROVIDER = Path(
    os.path.expandvars(r"%APPDATA%\com.prodown.app\po\bgutil-pot.exe"))


def _port_open(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _install_plugin() -> bool:
    """Chép 2 file plugin .py vào _potoken/yt_dlp_plugins/extractor/."""
    try:
        _PLUGIN_DST.mkdir(parents=True, exist_ok=True)
        if (_PLUGIN_DST / "getpot_bgutil.py").exists() and \
           (_PLUGIN_DST / "getpot_bgutil_http.py").exists():
            return True
        srcs = list(_BUNDLED_PLUGINS.glob("getpot_bgutil*.py"))
        if not srcs:
            return False
        for s in srcs:
            shutil.copy2(s, _PLUGIN_DST / s.name)
        return True
    except Exception:  # noqa: BLE001
        return (_PLUGIN_DST / "getpot_bgutil.py").exists()


def _ensure_provider() -> str:
    """Đường dẫn provider exe (tái dùng > chép > tải). '' nếu thất bại."""
    if _PROVIDER_DST.exists() and _PROVIDER_DST.stat().st_size > 1_000_000:
        return str(_PROVIDER_DST)
    _POTOKEN_DIR.mkdir(parents=True, exist_ok=True)
    # 1) Tái dùng cái BQHungDown đã tải sẵn
    if _PRODOWN_PROVIDER.exists() and \
       _PRODOWN_PROVIDER.stat().st_size > 1_000_000:
        try:
            shutil.copy2(_PRODOWN_PROVIDER, _PROVIDER_DST)
            return str(_PROVIDER_DST)
        except Exception:  # noqa: BLE001
            return str(_PRODOWN_PROVIDER)
    # 2) Tải mới (chỉ lần đầu, máy khác chưa có tool kia)
    global _DOWNLOAD_FAILED
    if _DOWNLOAD_FAILED:
        return ""            # vừa fail trong phiên này -> đừng tải lại 46MB mỗi lần bấm
    tmp = _PROVIDER_DST.with_suffix(".part")
    try:
        # urlretrieve KHÔNG có timeout -> mạng nghẽn sẽ treo thread tải VĨNH VIỄN
        # (nút Tải bị disable mãi tới khi restart app). Đọc chunk với timeout.
        req = urllib.request.Request(PROVIDER_URL,
                                     headers={"User-Agent": "bqhungvideo"})
        with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        tmp.replace(_PROVIDER_DST)
        return str(_PROVIDER_DST)
    except Exception:  # noqa: BLE001
        _DOWNLOAD_FAILED = True
        try:
            tmp.unlink(missing_ok=True)      # dọn file .part tải dở
        except OSError:
            pass
        return ""


_DOWNLOAD_FAILED = False
_PROVIDER_PROC = None       # handle server MÌNH spawn (để tắt khi thoát app)


def _kill_provider() -> None:
    """Tắt provider CHÍNH APP NÀY spawn (server có sẵn của tool khác thì
    không đụng — _port_open() ở lần sau vẫn tái dùng được)."""
    global _PROVIDER_PROC
    p = _PROVIDER_PROC
    if p is not None and p.poll() is None:
        try:
            p.kill()
        except OSError:
            pass
    _PROVIDER_PROC = None


def _spawn_provider(exe: str) -> None:
    global _PROVIDER_PROC
    flags = 0x0800_0000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    try:
        _PROVIDER_PROC = subprocess.Popen(
            [exe, "server", "--host", "127.0.0.1", "--port", str(PORT)],
            creationflags=flags,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # không tắt thì bgutil-pot.exe (~46MB RAM) sống vĩnh viễn sau khi đóng app
        import atexit
        atexit.register(_kill_provider)
    except Exception:  # noqa: BLE001
        pass


def ensure_running() -> list:
    """Bảo đảm plugin + provider sẵn sàng trước khi tải.

    Trả về list arg thêm cho yt-dlp: ['--plugin-dirs', <dir>] khi plugin có
    sẵn, [] nếu không dùng được (yt-dlp vẫn tải bình thường, chỉ kém né bot).
    """
    ok_plugin = _install_plugin()
    if not _port_open():
        exe = _ensure_provider()
        if exe:
            _spawn_provider(exe)
            for _ in range(30):           # chờ server lên (tối đa ~6s)
                if _port_open():
                    break
                time.sleep(0.2)
    return ["--plugin-dirs", str(_POTOKEN_DIR)] if ok_plugin else []
