"""Vòng đời app: cờ ĐANG ĐÓNG + gọi-về-UI an toàn từ luồng nền.

VÌ SAO CÓ FILE NÀY (crash thật của anh Hùng, Windows WER ghi 8 lần trong
3 ngày 28-30/07/2026): `Exception code 0xc0000005` (truy cập bộ nhớ sai)
trong `python312.dll`, offset CỐ ĐỊNH 0x83929, KHÔNG có traceback Python
trong logs/error.log dù app đã có sys.excepthook.

Cơ chế: app có 19 luồng nền daemon (tạo ảnh thu nhỏ, tải YouTube, kiểm
key, demo giọng...). Chúng gọi `signal.emit()` về UI. Khi user đóng app:
Qt phá huỷ widget + CPython finalize interpreter, trong khi luồng daemon
VẪN đang chạy bytecode -> nó chạm vào đối tượng đã bị giải phóng =>
access violation. Không phải exception Python nên không log được, và
`_bg_thumbs` từng để lại chứng cứ:
    RuntimeError: wrapped C/C++ object of type StudioPage has been deleted

Cách chữa 3 lớp:
  1. `set_closing()` ngay đầu closeEvent -> mọi luồng nền im lặng dừng.
  2. `safe_emit(lambda: ...)` -> emit không bao giờ làm sập (bắt cả
     RuntimeError của sip khi C++ object đã xoá).
  3. main.py thoát bằng os._exit() sau khi dọn -> KHÔNG finalize
     interpreter khi luồng daemon còn chạy (nguồn 0xc0000005).
"""
from __future__ import annotations

from typing import Callable

_CLOSING = False


def set_closing() -> None:
    """Gọi NGAY khi bắt đầu đóng app/cửa sổ (trước khi phá widget)."""
    global _CLOSING
    _CLOSING = True


def is_closing() -> bool:
    """Luồng nền hỏi câu này trước mỗi bước dài / trước khi chạm UI."""
    return _CLOSING


def alive(obj) -> bool:
    """Đối tượng Qt còn sống (C++ chưa bị xoá) VÀ app chưa đóng?"""
    if _CLOSING:
        return False
    try:
        from PyQt6 import sip
        return not sip.isdeleted(obj)
    except (ImportError, TypeError, RuntimeError):
        return True          # không xác định được -> để safe_emit lo


def safe_emit(fn: Callable, *args) -> bool:
    """Gọi `fn(*args)` từ LUỒNG NỀN mà KHÔNG BAO GIỜ làm sập app.

    `fn` PHẢI là lambda (vd `lambda: self.dl_done.emit(a, b)`) — truy cập
    thuộc tính signal cũng phải nằm TRONG try, vì chính nó ném RuntimeError
    khi C++ object đã bị xoá.

    Trả False nếu app đang đóng / đối tượng đã chết (đã bỏ qua an toàn).
    """
    if _CLOSING:
        return False
    try:
        fn(*args)
        return True
    except RuntimeError:
        return False         # widget đã bị xoá — bỏ qua, KHÔNG sập
