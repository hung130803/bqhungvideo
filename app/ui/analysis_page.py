"""
Bước 2 — LÕI PHÂN TÍCH: xem trạng thái từng bước nền tảng cho video đang chọn,
xem nhanh transcript, và "Làm lại" nếu cần (human-in-the-loop).
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from app import services
from app.core.analysis import STEPS, analysis_status, get_analysis
from app.ui.state import AppState

_STATUS_ICON = {
    "done": "✅", "running": "⏳", "failed": "❌",
    "skipped": "➖", "pending": "•",
}


class AnalysisPage(QWidget):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        state.video_changed.connect(lambda _: self.refresh())

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        lay.addWidget(QLabel("<h2>Bước 2 — Lõi phân tích</h2>"))
        lay.addWidget(QLabel(
            "<span style='color:#9A9AA8'>Chạy MỘT LẦN cho mỗi video và lưu lại. "
            "Mọi bước sau (cắt highlight, phụ đề, dịch…) đọc lại từ đây.</span>"))

        from app.ui.theme import card_style
        steps_card = QWidget()
        steps_card.setStyleSheet(card_style())
        sc = QVBoxLayout(steps_card)
        sc.setContentsMargins(16, 14, 16, 14)
        sc.setSpacing(10)
        self.step_labels: dict[str, QLabel] = {}
        for kind, label in STEPS:
            l = QLabel(f"•  {label}")
            l.setStyleSheet("font-size:14px;")
            self.step_labels[kind] = l
            sc.addWidget(l)
        lay.addWidget(steps_card)

        lay.addWidget(QLabel("<b>Xem nhanh lời thoại (transcript):</b>"))
        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        lay.addWidget(self.transcript_view, 1)

        brow = QHBoxLayout()
        self.rerun_btn = QPushButton("↻ Phân tích lại video này")
        self.rerun_btn.clicked.connect(self._rerun)
        brow.addWidget(self.rerun_btn)
        brow.addStretch(1)
        lay.addLayout(brow)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self):
        vid = self.state.video_id
        if vid is None:
            for kind, label in STEPS:
                self.step_labels[kind].setText(f"•  {label}")
            self.transcript_view.setPlainText("(Chưa chọn video)")
            return
        status = analysis_status(vid)
        for kind, label in STEPS:
            st = status.get(kind, "pending")
            self.step_labels[kind].setText(
                f"{_STATUS_ICON.get(st, '•')}  {label}  — {st}")
        tr = get_analysis(vid, "transcript")
        if tr and tr.get("text"):
            self.transcript_view.setPlainText(tr["text"])
        elif "transcript" in status and status["transcript"] == "skipped":
            self.transcript_view.setPlainText(
                "(Bỏ qua transcript — chưa cài faster-whisper)")
        else:
            self.transcript_view.setPlainText("(Chưa có transcript)")

    def _rerun(self):
        if self.state.video_id and self.state.project_id:
            services.enqueue_analysis(
                self.state.pool, self.state.video_id,
                self.state.project_id, force=True)
            self.state.data_changed.emit()
