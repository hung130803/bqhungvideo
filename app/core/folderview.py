"""GHIM 'loại thư mục' của Windows Explorer cho thư mục xuất.

Bệnh Windows: thư mục chứa video/ảnh bị Explorer TỰ ĐOÁN LẠI "loại thư mục"
(General items -> Videos...) mỗi khi nội dung thay đổi (thêm kênh/clip mới)
-> kiểu xem + SẮP XẾP user đã chọn (vd Date created) bị RESET về mặc định.
User báo thật: xếp 'Đã xuất' theo Date created, cứ tạo kênh mới là mất.

Chữa chuẩn tài liệu MS: ghi desktop.ini với FolderType=Generic (khoá template,
Explorer thôi đoán lại) + đặt thuộc tính để Windows chịu đọc desktop.ini:
  - desktop.ini: HIDDEN|SYSTEM (ẩn, không hiện trong Explorer)
  - thư mục: READ_ONLY (Windows coi là 'thư mục có tuỳ biến' — KHÔNG cản
    ghi/xoá file bên trong, chỉ là cờ đánh dấu).
Sau đó user chỉnh sắp xếp 1 lần là Explorer NHỚ (không bị template reset).

Chỉ chạy trên Windows; mọi lỗi nuốt im (tính năng phụ, không được cản xuất).
"""
from __future__ import annotations

import os
from pathlib import Path

_INI = "[ViewState]\r\nMode=\r\nVid=\r\nFolderType=Generic\r\n"

_FILE_ATTRIBUTE_READONLY = 0x01
_FILE_ATTRIBUTE_HIDDEN = 0x02
_FILE_ATTRIBUTE_SYSTEM = 0x04


def pin_folder_view(folder: str | Path) -> bool:
    """Ghim loại thư mục = Generic cho `folder` (idempotent). True nếu đã ghim
    (hoặc ghim từ trước), False nếu không phải Windows/lỗi."""
    if os.name != "nt":
        return False
    try:
        d = Path(folder)
        if not d.is_dir():
            return False
        ini = d / "desktop.ini"
        if not ini.exists() or "FolderType=Generic" not in ini.read_text(
                encoding="utf-8", errors="ignore"):
            # desktop.ini cũ có thể đang HIDDEN|SYSTEM -> bỏ cờ mới ghi được
            import ctypes
            k32 = ctypes.windll.kernel32
            if ini.exists():
                k32.SetFileAttributesW(str(ini), 0x80)   # NORMAL
            ini.write_text(_INI, encoding="utf-8")
            k32.SetFileAttributesW(
                str(ini), _FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM)
        # thư mục cần cờ READONLY để Explorer đọc desktop.ini (không cản ghi)
        import ctypes
        k32 = ctypes.windll.kernel32
        attrs = k32.GetFileAttributesW(str(d))
        if attrs != 0xFFFFFFFF and not (attrs & _FILE_ATTRIBUTE_READONLY):
            k32.SetFileAttributesW(str(d), attrs | _FILE_ATTRIBUTE_READONLY)
        return True
    except Exception:  # noqa: BLE001 - tính năng phụ, không cản luồng xuất
        return False
