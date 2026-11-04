"""Chuyển động NHẸ dùng chung: thanh tiến trình trôi mượt, thông báo nổi (toast)
không chặn, mờ dần khi đổi trang.

Nguyên tắc (đo trên máy 2 nhân + màn 400 ms/nhịp của hàng đợi):
  · KHÔNG QGraphicsOpacityEffect lên cây widget lớn (bắt render lại cả cây vào
    pixmap mỗi khung hình). Chỉ dùng cho widget NHỎ (toast) hoặc lớp phủ trơn.
  · KHÔNG animate geometry của widget nằm trong layout.
  · Cửa sổ ẩn / thu nhỏ -> nhảy thẳng tới đích (không tốn khung hình nào).
  · Tắt toàn bộ: biến môi trường BQ_NO_ANIM=1 (hoặc anim.ENABLED = False).
"""
from __future__ import annotations

import os

from PyQt6.QtCore import (QEasingCurve, QEvent, QObject, QPoint,
                          QPropertyAnimation, Qt, QTimer, QVariantAnimation)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout,
                             QLabel, QProgressBar, QWidget)

ENABLED = os.environ.get("BQ_NO_ANIM", "") not in ("1", "true", "yes")
DUR_FAST = 160
DUR_BASE = 300


def _alive(w) -> bool:
    try:
        w.objectName()
        return True
    except RuntimeError:            # đối tượng C++ đã bị huỷ
        return False


def _onscreen(w) -> bool:
    """Có ai đang nhìn widget này không (hiện + cửa sổ không thu nhỏ)."""
    try:
        return bool(ENABLED and w.isVisible() and not w.window().isMinimized())
    except RuntimeError:
        return False


# ---------------------------------------------------------------------------
# Thanh tiến trình trôi mượt
# ---------------------------------------------------------------------------
class SmoothProgressBar(QProgressBar):
    """QProgressBar có phần VẼ trôi mượt tới giá trị mới (~300 ms OutCubic).

    `value()` (phía Python) trả NGAY giá trị ĐÍCH -> code/test đọc lại vẫn đúng
    như QProgressBar thường; chỉ phần hiển thị là trôi. Giảm giá trị (thử lại,
    về 0), lệch quá nhỏ, hoặc không ai nhìn -> nhảy thẳng, không animate.
    Animation là con của thanh -> thanh bị huỷ thì animation chết theo.
    """

    def __init__(self, parent=None, duration: int = DUR_BASE):
        super().__init__(parent)
        self._target = super().value()
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def value(self) -> int:  # noqa: D401 - giữ API QProgressBar
        return self._target

    def displayed_value(self) -> int:
        return super().value()

    def setValue(self, v: int) -> None:  # noqa: N802
        v = int(max(self.minimum(), min(self.maximum(), v)))
        if v == self._target:
            return
        self._target = v
        cur = super().value()
        if (not _onscreen(self) or v < cur or abs(v - cur) < 1
                or cur < self.minimum()):
            self._anim.stop()
            super().setValue(v)
            return
        self._anim.stop()
        self._anim.setStartValue(cur)
        self._anim.setEndValue(v)
        self._anim.start()

    def reset(self) -> None:
        self._anim.stop()
        super().reset()
        self._target = super().value()

    def hideEvent(self, e):  # noqa: N802
        # ẩn giữa chừng -> chốt luôn giá trị đích (khỏi chạy khung hình vô ích)
        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
            super().setValue(self._target)
        super().hideEvent(e)


def smooth_set_value(bar: QProgressBar, v: int, duration: int = DUR_BASE) -> None:
    """Cho QProgressBar THƯỜNG (đã dựng sẵn ở file khác): trôi tới v.
    Lưu ý: với thanh thường `bar.value()` sẽ trễ theo animation — nếu code đọc
    lại value() ngay, dùng SmoothProgressBar thay vì hàm này."""
    if isinstance(bar, SmoothProgressBar):
        bar.setValue(v)
        return
    if not _onscreen(bar) or v < bar.value():
        an = getattr(bar, "_bq_anim", None)
        if an is not None:
            an.stop()
        bar.setValue(v)
        return
    an = getattr(bar, "_bq_anim", None)
    if an is None:
        an = QPropertyAnimation(bar, b"value", bar)
        an.setEasingCurve(QEasingCurve.Type.OutCubic)
        bar._bq_anim = an
    an.stop()
    an.setDuration(duration)
    an.setStartValue(bar.value())
    an.setEndValue(int(v))
    an.start()


# ---------------------------------------------------------------------------
# Toast — thông báo nổi KHÔNG chặn (thay QMessageBox.information)
# ---------------------------------------------------------------------------
_ICON = {"info": "i", "success": "✓", "warn": "!", "error": "✕"}


class _ToastHost(QObject):
    """Xếp chồng các toast ở góc dưới-phải cửa sổ, tự xếp lại khi đổi cỡ."""

    MAX = 4

    def __init__(self, win: QWidget):
        super().__init__(win)
        self.win = win
        self.items: list[Toast] = []
        win.installEventFilter(self)

    def eventFilter(self, obj, ev):  # noqa: N802
        if obj is self.win and ev.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.relayout(animate=False)
        return False

    def add(self, t: "Toast") -> None:
        self.items.append(t)
        while len(self.items) > self.MAX:
            self.items[0].dismiss()
            self.items.pop(0)
        self.relayout(animate=True)

    def remove(self, t: "Toast") -> None:
        if t in self.items:
            self.items.remove(t)
        self.relayout(animate=True)

    def relayout(self, animate: bool) -> None:
        if not _alive(self.win):
            return
        margin = 16
        y = self.win.height() - margin
        for t in reversed(self.items):
            if not _alive(t):
                continue
            t.adjustSize()
            y -= t.height()
            pos = QPoint(self.win.width() - t.width() - margin, y)
            t.move_to(pos, animate and t.isVisible())
            y -= 8


class Toast(QFrame):
    """1 thông báo: chữ + (tuỳ chọn) nút hành động. Bấm vào = đóng."""

    def __init__(self, win: QWidget, text: str, kind: str = "info",
                 action: tuple | None = None):
        super().__init__(win)
        self.setObjectName("toast")
        self.setProperty("kind", kind if kind in _ICON else "info")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(10)
        ic = QLabel(_ICON.get(kind, "i"))
        ic.setProperty("tone", {"success": "success", "error": "danger",
                                "warn": "warn"}.get(kind, "accent"))
        ic.setProperty("role", "value")
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(360)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lay.addWidget(self.label, 1)
        if action:
            from PyQt6.QtWidgets import QPushButton
            txt, fn = action
            b = QPushButton(txt)
            b.setProperty("variant", "ghost")
            b.setProperty("density", "compact")
            b.clicked.connect(lambda: (fn(), self.dismiss()))
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        self._eff = QGraphicsOpacityEffect(self)   # widget NHỎ -> rẻ
        self._eff.setOpacity(0.0)
        self.setGraphicsEffect(self._eff)
        self._fade = QPropertyAnimation(self._eff, b"opacity", self)
        self._fade.setDuration(DUR_FAST + 60)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._move = QPropertyAnimation(self, b"pos", self)
        self._move.setDuration(DUR_FAST + 60)
        self._move.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._closing = False

    def move_to(self, pos: QPoint, animate: bool) -> None:
        if animate and ENABLED:
            self._move.stop()
            self._move.setStartValue(self.pos())
            self._move.setEndValue(pos)
            self._move.start()
        else:
            self.move(pos)

    def appear(self, ms: int) -> None:
        self.show()
        self.raise_()
        if ENABLED:
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        else:
            self._eff.setOpacity(1.0)
        if ms > 0:
            QTimer.singleShot(ms, self.dismiss)

    def dismiss(self) -> None:
        if self._closing or not _alive(self):
            return
        self._closing = True
        host = getattr(self.parent(), "_bq_toasts", None)
        if host is not None:
            host.remove(self)
        if ENABLED and self.isVisible():
            self._fade.stop()
            self._fade.setStartValue(self._eff.opacity())
            self._fade.setEndValue(0.0)
            self._fade.finished.connect(self.deleteLater)
            self._fade.start()
        else:
            self.deleteLater()

    def mousePressEvent(self, e):  # noqa: N802
        self.dismiss()


def toast(parent: QWidget | None, text: str, kind: str = "info",
          ms: int = 3500, action: tuple | None = None) -> Toast | None:
    """Hiện thông báo nổi ở góc dưới-phải CỬA SỔ chứa `parent`, tự tắt sau ms.

    kind: info | success | warn | error. action=("Mở", callable) -> thêm nút.
    Không có cửa sổ (parent None) -> trả None, không làm gì (an toàn khi gọi
    từ chỗ chưa có UI). KHÔNG chặn luồng như QMessageBox.
    """
    if parent is None:
        return None
    try:
        win = parent.window()
    except RuntimeError:
        return None
    host = getattr(win, "_bq_toasts", None)
    if host is None:
        host = _ToastHost(win)
        win._bq_toasts = host
    t = Toast(win, text, kind, action)
    t.adjustSize()
    t.move(win.width() - t.width() - 16, win.height() - t.height() - 16)
    host.add(t)
    t.appear(ms)
    return t


# ---------------------------------------------------------------------------
# Mờ dần khi đổi trang (lớp phủ TRƠN, không opacity-effect lên trang thật)
# ---------------------------------------------------------------------------
class _FadeCover(QWidget):
    """Lớp phủ màu nền trơn, trong dần. Animation là CON của lớp phủ và nối vào
    METHOD của chính nó (không closure + QTimer: closure Python gắn vào timer
    con từng làm sập app khi lớp phủ bị huỷ giữa chừng — đo 26/10/2026)."""

    def __init__(self, over: QWidget, color, duration: int):
        super().__init__(over)
        self._c = QColor(color)
        self._a = 0.85
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setGeometry(over.rect())
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.85)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)
        self._anim.finished.connect(self.deleteLater)
        over.installEventFilter(self)      # trang đổi cỡ (dock ẩn/hiện) -> phủ theo

    def eventFilter(self, obj, ev):  # noqa: N802
        if ev.type() == QEvent.Type.Resize and obj is self.parent():
            self.setGeometry(obj.rect())
        return False

    def _on_value(self, v) -> None:
        self._a = float(v)
        self.update()

    def start(self) -> None:
        self.show()
        self.raise_()
        self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self.hide()
        self.deleteLater()

    def paintEvent(self, e):  # noqa: N802
        from PyQt6.QtGui import QPainter
        c = QColor(self._c)
        c.setAlphaF(max(0.0, min(1.0, self._a)))
        p = QPainter(self)
        p.fillRect(self.rect(), c)
        p.end()


def fade_in(widget: QWidget, color: str, duration: int = DUR_FAST) -> None:
    """Trang vừa hiện 'hiện dần' từ màu nền: phủ 1 lớp màu nền rồi làm trong
    dần trong ~160 ms. Chỉ 1 lớp phủ trơn + ~10 khung hình -> rẻ."""
    if not _onscreen(widget):
        return
    old = getattr(widget, "_bq_fade", None)
    widget._bq_fade = None
    if old is not None and _alive(old):
        old.stop()
    cov = _FadeCover(widget, color, duration)
    widget._bq_fade = cov
    cov.start()
