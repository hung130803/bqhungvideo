"""Chặn CUỘN CHUỘT vô tình làm đổi giá trị ComboBox / ô Số.

Lỗi Qt mặc định: lăn chuột khi con trỏ ĐANG Ở TRÊN một QComboBox/QSpinBox
(dù chưa bấm vào) sẽ đổi giá trị của nó — user cuộn trang lên/xuống là các
ô "Chế độ", "Video/ngày"... tự nhảy lung tung. Bộ lọc này:

  • Nếu widget CHƯA được focus (user chưa bấm chọn) → KHÔNG cho cuộn đổi
    giá trị; thay vào đó đẩy cú cuộn sang vùng cuộn (bảng/scroll) gần nhất
    để trang vẫn cuộn bình thường.
  • Nếu widget ĐANG focus (user chủ động bấm vào rồi) → cuộn đổi giá trị
    như thường.

Cài 1 lần lên QApplication là áp cho MỌI màn hình.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication,
                             QComboBox)


class _WheelGuard(QObject):
    def eventFilter(self, obj, ev):  # noqa: N802 (Qt signature)
        if ev.type() == QEvent.Type.Wheel and isinstance(
                obj, (QComboBox, QAbstractSpinBox)):
            if not obj.hasFocus():
                # Đẩy cú cuộn sang vùng cuộn gần nhất (bảng/scroll area) để
                # trang vẫn cuộn, rồi NUỐT sự kiện gốc (không đổi giá trị).
                w = obj.parentWidget()
                while w is not None:
                    if isinstance(w, QAbstractScrollArea):
                        QApplication.sendEvent(w.viewport(), ev)
                        break
                    w = w.parentWidget()
                return True
        return False


def install(app: QApplication) -> None:
    """Cài bộ chặn cuộn lên QApplication (giữ tham chiếu chống bị dọn rác)."""
    if getattr(app, "_wheel_guard", None) is not None:
        return
    g = _WheelGuard(app)
    app.installEventFilter(g)
    app._wheel_guard = g  # noqa: SLF001 - giữ sống
