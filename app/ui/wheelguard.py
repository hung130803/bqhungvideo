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
                             QComboBox, QSlider)

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
    def eventFilter(self, obj, ev):  # noqa: N802 (Qt signature)
        if ev.type() == QEvent.Type.Wheel:
            target = _value_ancestor(obj)
            if target is not None and not target.hasFocus():
                sa = _scroll_area(obj)
                if sa is not None:
                    QApplication.sendEvent(sa.viewport(), ev)
                return True  # NUỐT: không cho đổi giá trị
        return False


def install(app: QApplication) -> None:
    """Cài bộ chặn cuộn lên QApplication (giữ tham chiếu chống bị dọn rác)."""
    if getattr(app, "_wheel_guard", None) is not None:
        return
    g = _WheelGuard(app)
    app.installEventFilter(g)
    app._wheel_guard = g  # noqa: SLF001 - giữ sống
