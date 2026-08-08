# -*- coding: utf-8 -*-
"""Tìm VIDEO NHẬT THẬT trong `C:\\Users\\Admin\\Downloads\\thùng rác`.

VÌ SAO PHẢI CÓ FILE NÀY (bẫy đã sập 07/08/2026): tên file Nhật trên đĩa ở dạng
**NFD** (`コ` + dấu ゛ rời) còn chuỗi gõ trong mã nguồn là **NFC** (`ゴ`) ->
`os.path.exists()` trả **False** dù file có thật. Đừng gõ tên file Nhật vào code;
luôn QUÉT thư mục rồi lấy tên đúng như đĩa trả về.
"""
from __future__ import annotations

import os
import unicodedata

THUNG_RAC = r"C:\Users\Admin\Downloads\thùng rác"
DUOI = (".mp4", ".mkv", ".webm", ".mov")


def _co_cjk(s: str) -> bool:
    for c in s:
        o = ord(c)
        if 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF:
            return True
    return False


def liet_ke(chi_nhat: bool = True, goc: str = "") -> list[str]:
    """Danh sách video (đường dẫn tuyệt đối), lớn -> nhỏ. chi_nhat=True: chỉ
    những đường dẫn có ký tự CJK (kênh Nhật của anh Hùng)."""
    base = goc or THUNG_RAC
    ra: list[tuple[int, str]] = []
    for root, _d, files in os.walk(base):
        for f in files:
            if not f.lower().endswith(DUOI):
                continue
            p = os.path.join(root, f)
            if chi_nhat and not _co_cjk(p):
                continue
            try:
                ra.append((os.path.getsize(p), p))
            except OSError:
                continue
    ra.sort(reverse=True)
    return [p for _s, p in ra]


def mot(tu_khoa: str = "", chi_nhat: bool = True) -> str:
    """1 video: khớp `tu_khoa` (so sánh đã CHUẨN HOÁ NFC nên gõ NFC vẫn khớp)."""
    ds = liet_ke(chi_nhat)
    if tu_khoa:
        k = unicodedata.normalize("NFC", tu_khoa)
        for p in ds:
            if k in unicodedata.normalize("NFC", p):
                return p
    return ds[0] if ds else ""


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for i, p in enumerate(liet_ke()):
        print(i, os.path.getsize(p) // 1_000_000, "MB", p)
