"""
Né màn "Sign in to confirm you're not a bot" của YouTube mà KHÔNG cần cookie.

Cơ chế: chạy PO-token provider (server cục bộ 127.0.0.1:4416, ~46MB, bản Rust
jim60105/bgutil-ytdlp-pot-provider-rs) + plugin bgutil cho yt-dlp dạng ZIP
(bgutil-ytdlp-pot-provider-rs.zip đặt THẲNG trong _potoken/ — yt-dlp ≥2025.03
đọc zip trực tiếp từ --plugin-dirs). yt-dlp sẽ tự xin PO token từ server này.

LƯU Ý version: plugin zip và server exe PHẢI cùng release (plugin từ chối
server lệch major). Vì vậy cả 2 được tải từ CÙNG một tag GitHub và ghi lại
trong file release.tag; plugin được làm mới ~30 ngày/lần (kèm exe nếu đổi tag).

Tất cả best-effort: nếu tải/khởi động lỗi thì yt-dlp vẫn tải bình thường
(chỉ là không có token). PO token KHÔNG đổi IP -> IP bị YouTube gắn cờ nặng
thì một số video vẫn đòi cookie đăng nhập.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from config import DATA_DIR

PORT = 4416
# Repo phát hành CẢ server exe lẫn plugin zip trong cùng 1 release.
_REPO = "jim60105/bgutil-ytdlp-pot-provider-rs"
# Tag dự phòng khi không hỏi được GitHub (khớp bản exe/zip bundle theo app).
_FALLBACK_TAG = "v0.8.1"
_PLUGIN_ZIP_NAME = "bgutil-ytdlp-pot-provider-rs.zip"
_PLUGIN_TTL = 30 * 86400          # ~30 ngày mới kiểm tra bản mới 1 lần

_POTOKEN_DIR = DATA_DIR / "_potoken"
_PLUGIN_ZIP = _POTOKEN_DIR / _PLUGIN_ZIP_NAME
_PROVIDER_DST = _POTOKEN_DIR / "bgutil-pot.exe"
_TAG_FILE = _POTOKEN_DIR / "release.tag"   # tag của cặp zip+exe đang cài

# Plugin zip đi KÈM trong repo/app (máy khách offline lần đầu vẫn chạy được).
_BUNDLED_PLUGINS = Path(__file__).resolve().parent / "potoken_plugins"
# Tái dùng provider 46MB nếu máy này tình cờ đã cài BQHungDown (khỏi tải lại).
_PRODOWN_PROVIDER = Path(
    os.path.expandvars(r"%APPDATA%\com.prodown.app\po\bgutil-pot.exe"))

_UA = "bqhungvideo"
_REFRESH_FAILED = False     # đã fail tải trong phiên này -> đừng thử lại mãi
_DOWNLOAD_FAILED = False    # như trên, riêng cho exe 46MB


def _provider_url(tag: str) -> str:
    return (f"https://github.com/{_REPO}/releases/download/{tag}/"
            "bgutil-pot-windows-x86_64.exe")


def _plugin_url(tag: str) -> str:
    return (f"https://github.com/{_REPO}/releases/download/{tag}/"
            f"{_PLUGIN_ZIP_NAME}")


def _port_open(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _download(url: str, dst: Path, timeout: int = 30) -> bool:
    """Tải url -> dst qua file .part (đọc chunk có timeout, không treo)."""
    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as r, \
                open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
        tmp.replace(dst)
        return True
    except Exception:  # noqa: BLE001
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _latest_tag() -> str:
    """Tag release mới nhất trên GitHub; '' nếu không hỏi được."""
    url = f"https://api.github.com/repos/{_REPO}/releases/latest"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _UA,
                          "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return str(json.load(r).get("tag_name") or "")
    except Exception:  # noqa: BLE001
        return ""


def _current_tag() -> str:
    try:
        t = _TAG_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    except OSError:
        pass
    # cài từ đời trước (chưa có file tag): exe cũ là bản v0.8.1
    return _FALLBACK_TAG if _PROVIDER_DST.exists() else ""


def _cleanup_legacy() -> None:
    """Dọn plugin ĐỜI CŨ (framework GetPOT trước yt-dlp 2025.03): thư mục
    yt_dlp_plugins/ với getpot_bgutil*.py — để lại sẽ đè module trong zip."""
    try:
        old = _POTOKEN_DIR / "yt_dlp_plugins"
        if old.exists():
            shutil.rmtree(old, ignore_errors=True)
        # zip của Brainicism (đòi server Node 1.x, không khớp exe Rust)
        (_POTOKEN_DIR / "bgutil-ytdlp-pot-provider.zip").unlink(
            missing_ok=True)
    except OSError:
        pass


def _refresh_provider(tag: str) -> None:
    """Tải lại server exe CÙNG tag với plugin (best-effort; nếu exe đang chạy
    thì Windows khóa file -> giữ bản cũ, lần khởi động sau sẽ thay được)."""
    exe_new = _PROVIDER_DST.with_suffix(".new")
    if not _download(_provider_url(tag), exe_new, timeout=120):
        return
    try:
        exe_new.replace(_PROVIDER_DST)
    except OSError:                      # file đang bị khóa (server đang chạy)
        pass


def _install_plugin() -> bool:
    """Bảo đảm zip plugin nằm trong _potoken/ (yt-dlp nạp zip trực tiếp).

    Ưu tiên: zip sẵn còn "tươi" (<30 ngày) > tải bản mới nhất từ GitHub
    (kèm exe cùng tag nếu đổi version) > zip cũ sẵn có > zip bundle theo app.
    """
    global _REFRESH_FAILED
    try:
        _POTOKEN_DIR.mkdir(parents=True, exist_ok=True)
        _cleanup_legacy()
        have = _PLUGIN_ZIP.exists() and _PLUGIN_ZIP.stat().st_size > 1000
        if have and time.time() - _PLUGIN_ZIP.stat().st_mtime < _PLUGIN_TTL:
            return True
        if not _REFRESH_FAILED:
            tag = _latest_tag()
            cur = _current_tag()
            if tag and have and tag == cur:
                os.utime(_PLUGIN_ZIP)              # còn mới nhất -> reset TTL
                return True
            if tag and _download(_plugin_url(tag), _PLUGIN_ZIP):
                if tag != cur:
                    _refresh_provider(tag)   # server phải CÙNG release
                try:
                    _TAG_FILE.write_text(tag, encoding="utf-8")
                except OSError:
                    pass
                return True
            _REFRESH_FAILED = True          # đừng gọi GitHub mỗi lần bấm Tải
        if have:
            return True                     # cũ nhưng vẫn dùng được
        # offline / GitHub lỗi: dùng zip đóng gói kèm app
        bundled = _BUNDLED_PLUGINS / _PLUGIN_ZIP_NAME
        if bundled.exists():
            shutil.copy2(bundled, _PLUGIN_ZIP)
        return _PLUGIN_ZIP.exists()
    except Exception:  # noqa: BLE001
        return _PLUGIN_ZIP.exists()


def _ensure_provider() -> str:
    """Đường dẫn provider exe (sẵn có > tái dùng BQHungDown > tải). '' nếu fail."""
    global _DOWNLOAD_FAILED
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
    # 2) Tải mới (chỉ lần đầu) — cùng tag với plugin đang cài
    if _DOWNLOAD_FAILED:
        return ""            # vừa fail trong phiên này -> đừng tải lại 46MB mỗi lần
    tag = _current_tag() or _FALLBACK_TAG
    if _download(_provider_url(tag), _PROVIDER_DST, timeout=120):
        return str(_PROVIDER_DST)
    _DOWNLOAD_FAILED = True
    return ""


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
