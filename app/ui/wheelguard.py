"""Chặn CUỘN CHUỘT vô tình làm đổi giá trị ComboBox / ô Số / Slider.

Lỗi Qt mặc định: lăn chuột khi con trỏ ĐANG Ở TRÊN một QComboBox/QSpinBox/
QSlider (dù chưa bấm vào) sẽ đổi giá trị của nó — user cuộn trang lên/xuống
là các ô "Chế độ", "Video/ngày", "Nhóm"... tự nhảy lung tung.

Bộ lọc này (cài 1 lần lên QApplication → áp MỌI màn hình):
  • Cuộn trên widget đó (hoặc widget CON của nó — vd ô nhập của combo
    sửa-được) khi CHƯA focus → KHÔNG đổi giá trị; đẩy cú cuộn sang vùng
    cuộn gần nhất (bảng/scroll) để trang vẫn cuộn.
  • Đã bấm chọn (widget có focus) rồi mới cuộn → đổi giá trị như thường.

Chỉ đụng QComboBox / QAbstractSpinBox / QSlider — KHÔNG đụng QScrollBar
(để thanh cuộn vẫn hoạt động).
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication,
                             QComboBox, QSlider, QSpinBox)


# --- Widget TỰ CHẶN cuộn (chắc chắn 100%, không phụ thuộc bộ lọc toàn cục):
#     Qt LUÔN gọi wheelEvent của lớp con. Dùng cho các ô hay bị cuộn nhầm. ---
class NoWheelComboBox(QComboBox):
    """ComboBox: LĂN CHUỘT KHÔNG BAO GIỜ đổi giá trị (kể cả đang focus) — chỉ
    đổi bằng CLICK hoặc phím. Trước đây còn ngoại lệ hasFocus(): sau khi bấm
    chọn 1 dòng, combo giữ focus; cuộn xuống xem dòng khác mà con trỏ lướt qua
    combo -> value nhảy lung tung. User yêu cầu 'khoá cuộn' hẳn."""
    def wheelEvent(self, e):  # noqa: N802
        e.ignore()  # nuốt: nhường cuộn cho vùng cuộn cha, KHÔNG đổi giá trị


class NoWheelSpinBox(QSpinBox):
    """SpinBox: cuộn KHÔNG đổi giá trị (kể cả đang focus); vẫn bấm ▲▼ / gõ số."""
    def wheelEvent(self, e):  # noqa: N802
        e.ignore()

# Các loại widget "giá trị" cần chặn cuộn-vô-tình.
_VALUE_WIDGETS = (QComboBox, QAbstractSpinBox, QSlider)


def _value_ancestor(w):
    """Trèo ngược tối đa 4 cấp cha: nếu widget (hoặc cha gần) là ô giá trị
    thì trả về nó (bắt cả QLineEdit con của combo sửa-được / spinbox)."""
    depth = 0
    while w is not None and depth < 4:
        if isinstance(w, _VALUE_WIDGETS):
            return w
        w = w.parentWidget() if hasattr(w, "parentWidget") else None
        depth += 1
    return None


def _scroll_area(w):
    """Vùng cuộn (bảng/scroll) gần nhất tính từ w trở lên."""
    while w is not None:
        if isinstance(w, QAbstractScrollArea):
            return w
        w = w.parentWidget() if hasattr(w, "parentWidget") else None
    return None


class _WheelGuard(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Cờ chống ĐỆ QUY: sendEvent bên dưới lại đi qua chính filter này;
        # thiếu cờ -> gửi lặp vô hạn -> tràn stack -> APP SẬP TỨC THÌ
        # (đúng ca: cuộn khi dropdown Kênh đang mở).
        self._resending = False

    def eventFilter(self, obj, ev):  # noqa: N802 (Qt signature)
        if ev.type() == QEvent.Type.Wheel:
            if self._resending:          # event do chính mình gửi lại -> cho qua
                return False
            target = _value_ancestor(obj)
            # Combo & ô Số: KHOÁ cuộn HẲN (kể cả đang focus) — user yêu cầu chỉ
            # đổi bằng click/phím. QSlider: chỉ khoá khi CHƯA focus (kéo/cuộn
            # slider có chủ đích thì cho phép).
            block = target is not None and (
                isinstance(target, (QComboBox, QAbstractSpinBox))
                or not target.hasFocus())
            if block:
                # POPUP của combo đang MỞ -> user đang cuộn DANH SÁCH lựa chọn:
                # để Qt xử lý tự nhiên (cuộn list, không đổi giá trị). Trước
                # đây nuốt + gửi lại vào chính list -> đệ quy vô hạn -> crash.
                if isinstance(target, QComboBox):
                    view = target.view()
                    if view is not None and view.isVisible():
                        return False
                sa = _scroll_area(obj)
                # CHỈ chuyển cú cuộn cho vùng cuộn NGOÀI target (vùng cuộn nằm
                # trong target -> gửi lại là tự bắn vào chân -> đệ quy).
                if sa is not None and not target.isAncestorOf(sa):
                    self._resending = True
                    try:
                        QApplication.sendEvent(sa.viewport(), ev)
                    finally:
                        self._resending = False
                return True  # NUỐT: không cho đổi giá trị
        return False


def install(app: QApplication) -> None:
    """Cài bộ chặn cuộn lên QApplication (giữ tham chiếu chống bị dọn rác)."""
    if getattr(app, "_wheel_guard", None) is not None:
        return
    g = _WheelGuard(app)
    app.installEventFilter(g)
    app._wheel_guard = g  # noqa: SLF001 - giữ sống
