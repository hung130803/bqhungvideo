"""DỌN desktop.ini mà bản v1.62 từng tạo trong thư mục xuất.

v1.62 thử ghim 'loại thư mục' Explorer bằng desktop.ini (chống Windows reset
sắp xếp Date created) — nhưng user thấy desktop.ini hiện trong mọi thư mục
(máy bật 'hiện file hệ thống') + nghi làm nút Mở thư mục trượt. ĐÃ GỠ tính
năng; module này chỉ còn nhiệm vụ DỌN SẠCH những gì đã tạo: xoá desktop.ini
(đúng nội dung của app, không đụng ini của user/hệ thống) + bỏ cờ READONLY
trên thư mục. Chạy im lặng, mọi lỗi nuốt (không cản luồng app).
"""
from __future__ import annotations

import os
from pathlib import Path

_MARK = "FolderType=Generic"          # dấu nhận diện ini DO APP tạo

_FILE_ATTRIBUTE_READONLY = 0x01


def _unpin_one(d: Path) -> None:
    """Xoá desktop.ini của app (nếu có) + bỏ cờ READONLY trên `d`."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        ini = d / "desktop.ini"
        if ini.is_file():
            try:
                txt = ini.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                txt = ""
            # CHỈ xoá ini do app tạo (ngắn + đúng dấu hiệu) — không phá ini
            # tuỳ biến của user/Windows (icon thư mục...).
            if _MARK in txt and len(txt) < 200:
                k32.SetFileAttributesW(str(ini), 0x80)   # NORMAL để xoá được
                ini.unlink(missing_ok=True)
        attrs = k32.GetFileAttributesW(str(d))
        if attrs != 0xFFFFFFFF and (attrs & _FILE_ATTRIBUTE_READONLY):
            k32.SetFileAttributesW(str(d), attrs & ~_FILE_ATTRIBUTE_READONLY)
    except Exception:  # noqa: BLE001
        pass


def cleanup_folder_pins(root: str | Path, depth: int = 2) -> None:
    """Dọn desktop.ini của app trong `root` + thư mục con tới `depth` cấp
    (Đã xuất -> Kênh -> Video). Không phải Windows -> bỏ qua."""
    if os.name != "nt":
        return
    try:
        r = Path(root)
        if not r.is_dir():
            return
        _unpin_one(r)
        if depth <= 0:
            return
        for c1 in r.iterdir():
            if not c1.is_dir():
                continue
            _unpin_one(c1)
            if depth >= 2:
                for c2 in c1.iterdir():
                    if c2.is_dir():
                        _unpin_one(c2)
    except Exception:  # noqa: BLE001
        pass
