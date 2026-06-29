"""
Nạp các font đẹp (kiểu CapCut) đi kèm app vào Qt để dùng cho lớp chữ overlay.
Font đặt trong app/assets/fonts/*.ttf (đã tải sẵn, hỗ trợ tiếng Việt).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFontDatabase

from config import ROOT_DIR

_DIR = ROOT_DIR / "app" / "assets" / "fonts"
_done = False


def load_fonts() -> None:
    """Nạp mọi .ttf trong assets/fonts vào QFontDatabase (gọi 1 lần lúc khởi động)."""
    global _done
    if _done:
        return
    _done = True
    if not _DIR.is_dir():
        return
    for ttf in _DIR.glob("*.ttf"):
        try:
            QFontDatabase.addApplicationFont(str(ttf))
        except Exception:  # noqa: BLE001
            pass
