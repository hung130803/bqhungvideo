"""
Màn hình chính DUY NHẤT (kiểu Opus Clip):
  chọn video -> "Tạo clip tự động" (phân tích + cắt tự chạy) -> danh sách clip có
  điểm -> mỗi clip Tải/Mở, hoặc "Tải tất cả → Part 1,2,3". Chỉnh mẫu (nền+video+chữ)
  trong hộp thoại riêng. Mọi thứ kỹ thuật chạy ngầm.
"""
from __future__ import annotations

import copy
import os
import shutil
import subprocess
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QVBoxLayout, QWidget,
)

from app import services
from app.core.ffmpeg_utils import extract_frame
from app.database import db
from app.ui.editor import EditorDialog, render_overlay_png
from app.ui.state import AppState
from app.ui.theme import ACCENT, BASE, BORDER, DANGER, MUTED, SUCCESS, SURFACE, WARN

# Mẫu MẶC ĐỊNH: sẵn 2 lớp chữ TỰ ĐỘNG — "Part n" (trên) + tiêu đề AI ({title})
# ngay dưới. Vào "Chỉnh mẫu" để đổi vị trí/cỡ/màu; app tự điền khi xuất từng clip.
_DEF_PART = {"text": "Part {n}", "size": 0.055, "font": "Montserrat", "color": "#FFFFFF",
             "bg": True, "bg_color": "#000000", "radius": 50, "is_part": True,
             "nx": 0.5, "ny": 0.07}
_DEF_TITLE = {"text": "{title}", "size": 0.045, "font": "Montserrat", "color": "#FFFFFF",
              "bg": True, "bg_color": "#000000", "radius": 28, "is_part": False,
              "nx": 0.5, "ny": 0.20}
DEFAULT_LAYOUT = {"video_rect": (0.5, 0.5, 1.0), "bg": "blur",
                  "layers": [_DEF_PART, _DEF_TITLE], "captions": True,
                  "cap_font": "Montserrat", "cap_size": 0.05,
                  "cap_color": "", "cap_ny": 0.78,
                  "cap_preset": "Trắng đơn giản", "cap_delay": 0.12,
                  "cap_hook": True, "cap_hook_dur": 6.0}

# MẪU PRO sẵn (giống ViralCut): nền đen gọn, HOOK giật tít đầu clip, phụ đề vàng
# nhảy karaoke dưới, font Anton đậm, KHÔNG lớp chữ tĩnh (Hook lo phần tiêu đề).
PRO_LAYOUT = {"video_rect": (0.5, 0.5, 1.0), "bg": "black", "layers": [],
              "captions": True, "cap_font": "Anton", "cap_size": 0.055,
              "cap_color": "", "cap_ny": 0.82, "cap_preset": "Vàng nhảy (TikTok)",
              "cap_delay": 0.12, "cap_hook": True, "cap_hook_dur": 6.0}
PRO_NAME = "Pro (giật tít + phụ đề vàng)"
_OLD_PRO_NAME = "⭐ Pro (giật tít + phụ đề vàng)"   # tên cũ có emoji tofu -> dọn


def _dur(s):
    s = int(s or 0)
    return f"{s // 60}:{s % 60:02d}"


class _SegBar(QWidget):
    """Thanh nhỏ cho THẤY AI giữ đoạn nào (xanh) / bỏ đoạn nào (khoảng trống)."""

    def __init__(self, segments):
        super().__init__()
        self.segs = [list(s) for s in (segments or [])]
        self.setFixedHeight(7)
        self.setToolTip("Xanh = AI giữ · trống = AI bỏ đoạn thừa (đã ghép lại)")

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QColor
        if not self.segs:
            return
        s0, s1 = self.segs[0][0], self.segs[-1][1]
        span = max(0.1, s1 - s0)
        w, h = self.width(), self.height()
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(SURFACE)); p.drawRoundedRect(0, 0, w, h, 3, 3)
        p.setBrush(QColor(ACCENT))
        for a, b in self.segs:
            x = int((a - s0) / span * w)
            ww = max(2, int((b - a) / span * w))
            p.drawRoundedRect(x, 0, ww, h, 3, 3)
        p.end()


class StudioPage(QWidget):
    thumbs_ready = pyqtSignal()  # báo đã tạo xong thumbnail (chạy ngầm)
    dl_done = pyqtSignal(str, str)  # (đường-dẫn-file, lỗi) khi tải YouTube xong
    dl_progress = pyqtSignal(str)   # thông điệp tiến trình tải (hiện % cho user)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.layout_tpl = copy.deepcopy(DEFAULT_LAYOUT)
        self._thumb_busy = False
        self._pending_export = {}     # job_id phân tích -> video_id (chờ tự xuất)
        self._settings = QSettings("AIContentStudio", "studio")
        self.thumbs_ready.connect(self._rebuild_rows)
        self.setAcceptDrops(True)        # KÉO-THẢ video vào app

        # nội dung giới hạn bề rộng + căn giữa cho cân đối (không kéo dàn mép)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)
        content = QWidget()
        content.setMaximumWidth(1060)
        outer.addWidget(content, 30)   # ưu tiên rộng tới max rồi mới chừa lề 2 bên
        outer.addStretch(1)
        root = QVBoxLayout(content)
        root.setContentsMargins(8, 16, 8, 12)
        root.setSpacing(14)

        # ===== THẺ điều khiển (gom các nút vào 1 khối có viền cho dễ nhận biết) =====
        panel = QWidget(); panel.setObjectName("ctlPanel")
        panel.setStyleSheet(f"#ctlPanel{{background:{BASE}; border:1px solid {BORDER};"
                            f"border-radius:14px;}}")
        plw = QVBoxLayout(panel); plw.setContentsMargins(14, 12, 14, 12); plw.setSpacing(10)
        root.addWidget(panel)

        # ===== Hàng 1: chọn KÊNH + VIDEO =====
        srcrow = QHBoxLayout(); srcrow.setSpacing(8)
        srcrow.addWidget(self._tag("Kênh"))
        self.proj = QComboBox(); self.proj.setMinimumWidth(180)
        self.proj.setToolTip("Mỗi kênh = 1 thư mục riêng. Clip xuất vào đúng thư mục "
                             "kênh.\nChuột phải để XÓA kênh.")
        self.proj.currentIndexChanged.connect(self._on_proj)
        self.proj.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.proj.customContextMenuRequested.connect(self._proj_menu)
        srcrow.addWidget(self.proj)
        np = QPushButton("+ Kênh"); np.setProperty("ghost", True)
        np.clicked.connect(self._new_proj); srcrow.addWidget(np)
        sfd = QPushButton("Kho video"); sfd.setProperty("ghost", True)
        sfd.setToolTip("Chọn 1 thư mục GỐC chung. Trong đó tự có 'Đã tải' "
                       "(video YouTube) và 'Đã xuất' (clip theo từng video).")
        sfd.clicked.connect(self._pick_lib_root); srcrow.addWidget(sfd)
        srcrow.addSpacing(16)
        srcrow.addWidget(self._tag("Video"))
        self.vid = QComboBox(); self.vid.setMinimumWidth(200)
        self.vid.setToolTip("Chuột phải để xóa video / quản lý xóa nhiều video.")
        self.vid.currentIndexChanged.connect(self._on_vid)
        self.vid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.vid.customContextMenuRequested.connect(self._vid_menu)
        srcrow.addWidget(self.vid, 1)
        av = QPushButton("+ Thêm video"); av.setProperty("ghost", True)
        av.clicked.connect(self._add_video); srcrow.addWidget(av)
        mgv = QPushButton("Quản lý video"); mgv.setProperty("ghost", True)
        mgv.setToolTip("Xem danh sách video, tích chọn nhiều rồi xóa cùng lúc.")
        mgv.clicked.connect(self._manage_videos); srcrow.addWidget(mgv)
        plw.addWidget(self._sec_hdr("Nguồn video", "#5B8CFF"))
        plw.addLayout(srcrow)

        # ===== Hàng tải từ LINK YOUTUBE thẳng vào kênh =====
        ytrow = QHBoxLayout(); ytrow.setSpacing(8)
        ytrow.addWidget(self._tag("Link YT"))
        self.yt_url = QLineEdit()
        self.yt_url.setPlaceholderText("Dán link YouTube vào đây để tải thẳng về kênh...")
        ytrow.addWidget(self.yt_url, 1)
        self.yt_btn = QPushButton("Tải về"); self.yt_btn.setProperty("ghost", True)
        self.yt_btn.setToolTip("Tải video 1080p từ link vào kênh đang chọn (yt-dlp).")
        self.yt_btn.clicked.connect(self._download_youtube)
        ytrow.addWidget(self.yt_btn)
        ck_btn = QPushButton("Cookie"); ck_btn.setProperty("ghost", True)
        ck_btn.setToolTip("Dán cookie YouTube (khi bị đòi đăng nhập). Lưu 1 lần dùng mãi.")
        ck_btn.clicked.connect(self._youtube_cookie)
        ytrow.addWidget(ck_btn)
        plw.addLayout(ytrow)
        self.dl_done.connect(self._on_dl_done)
        self.dl_progress.connect(lambda m: self.status.setText(m))

        # ===== Hàng 2: HÀNH ĐỘNG tạo clip + công tắc tự xuất =====
        plw.addWidget(self._sec_hdr("Tạo clip", "#3DD68C"))
        actrow = QHBoxLayout(); actrow.setSpacing(8)
        self.auto_btn = QPushButton("Tạo clip")
        self.auto_btn.setProperty("primary", True)
        self.auto_btn.setMinimumHeight(40); self.auto_btn.setMinimumWidth(160)
        self.auto_btn.clicked.connect(self._auto); actrow.addWidget(self.auto_btn)
        self.auto_all_btn = QPushButton("Tất cả video")
        self.auto_all_btn.setProperty("ghost", True); self.auto_all_btn.setMinimumHeight(40)
        self.auto_all_btn.setToolTip("Đưa MỌI video chưa làm trong kênh vào hàng đợi.")
        self.auto_all_btn.clicked.connect(self._auto_all); actrow.addWidget(self.auto_all_btn)
        self.pick_btn = QPushButton("Chọn nhiều")
        self.pick_btn.setProperty("ghost", True); self.pick_btn.setMinimumHeight(40)
        self.pick_btn.setToolTip("Tích chọn nhiều video cụ thể để tạo clip cùng lúc.")
        self.pick_btn.clicked.connect(self._pick_videos); actrow.addWidget(self.pick_btn)
        actrow.addStretch(1)
        self.auto_export_chk = QCheckBox("Phân tích xong tự động xuất")
        self.auto_export_chk.setToolTip(
            "BẬT: phân tích + AI cắt xong là tự xuất hết clip vào thư mục kênh.\n"
            "TẮT: xem/sửa clip rồi tự bấm Xuất.")
        self.auto_export_chk.setChecked(
            self._settings.value("auto_export", False, type=bool))
        self.auto_export_chk.toggled.connect(
            lambda v: self._settings.setValue("auto_export", v))
        actrow.addWidget(self.auto_export_chk)
        plw.addLayout(actrow)

        # ===== Hàng 3: CẤU HÌNH (mẫu + cài đặt) =====
        plw.addWidget(self._sec_hdr("Mẫu & cài đặt", "#F5B544"))
        cfgrow = QHBoxLayout(); cfgrow.setSpacing(8)
        cfgrow.addWidget(self._tag("Mẫu"))
        self.tmpl_box = QComboBox(); self.tmpl_box.setMinimumWidth(190)
        self.tmpl_box.setToolTip("Mẫu khung/chữ áp khi xuất. Nhớ mẫu đã chọn lần sau.")
        self.tmpl_box.currentIndexChanged.connect(self._on_template_pick)
        cfgrow.addWidget(self.tmpl_box)
        edit = QPushButton("Chỉnh mẫu"); edit.setProperty("ghost", True)
        edit.clicked.connect(self._edit_template); cfgrow.addWidget(edit)
        cfgrow.addStretch(1)
        cut = QPushButton("Tùy chỉnh cắt"); cut.setProperty("ghost", True)
        cut.setToolTip("Ngôn ngữ, độ dài Min/Max clip, mục đích & phong cách cắt.")
        cut.clicked.connect(self._cut_settings); cfgrow.addWidget(cut)
        aiset = QPushButton("Cài đặt AI"); aiset.setProperty("ghost", True)
        aiset.setToolTip("Chọn AI máy/mây + key; Nghe-chép Local/Groq.")
        aiset.clicked.connect(self._ai_settings); cfgrow.addWidget(aiset)
        self.ai_status = QLabel("")
        self.ai_status.setToolTip("AI đang dùng. Bấm 'Cài đặt AI' để đổi/kiểm tra.")
        cfgrow.addWidget(self.ai_status)
        plw.addLayout(cfgrow)
        self._update_ai_status()

        # ===== Hàng 3: kết quả + tải tất cả =====
        headrow = QHBoxLayout(); headrow.setSpacing(8)
        self.count_lbl = QLabel("Chưa có clip")
        self.count_lbl.setStyleSheet("font-size:16px; font-weight:600;")
        headrow.addWidget(self.count_lbl)
        headrow.addStretch(1)
        op = QPushButton("Mở thư mục"); op.setProperty("ghost", True)
        op.clicked.connect(self._open_dir); headrow.addWidget(op)
        self.dl_chan = QPushButton("Xuất cả kênh")
        self.dl_chan.setProperty("ghost", True)
        self.dl_chan.setToolTip("Xuất clip của MỌI video trong kênh, 1 phát "
                                "(đúng thứ tự Part từng video).")
        self.dl_chan.clicked.connect(self._export_all_channel)
        headrow.addWidget(self.dl_chan)
        self.dl_all = QPushButton("Xuất video này")
        self.dl_all.setProperty("primary", True)
        self.dl_all.setToolTip("Xuất clip của VIDEO đang chọn.")
        self.dl_all.clicked.connect(self._export_all)
        headrow.addWidget(self.dl_all)
        root.addLayout(headrow)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        # ---- danh sách clip ----
        self.list_box = QVBoxLayout(); self.list_box.setSpacing(8)
        self.list_box.addStretch(1)
        host = QWidget(); host.setLayout(self.list_box)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
        # KHÔNG cuộn ngang (tránh "kéo sang" lạ); chỉ cuộn dọc khi nhiều clip
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(sc, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_clips)
        self.timer.timeout.connect(self._check_auto_export)   # phân tích xong -> tự xuất
        self.timer.start(1500)
        self._reload_projects()
        self._ensure_builtin_templates()      # tạo sẵn mẫu Pro nếu chưa có
        self._populate_templates(self._settings.value("last_template", "") or "")
        self._apply_selected_template()

    def _ensure_builtin_templates(self):
        """Tạo sẵn MẪU PRO (giống ViralCut) nếu chưa có, để user chọn ngay."""
        try:
            if services.get_template(_OLD_PRO_NAME):   # xóa mẫu Pro tên cũ (tofu)
                services.delete_template(_OLD_PRO_NAME)
            if not services.get_template(PRO_NAME):
                services.save_template(PRO_NAME, copy.deepcopy(PRO_LAYOUT))
        except Exception:  # noqa: BLE001
            pass

    def _tag(self, text):
        """Nhãn nhỏ mờ cho ô chọn (Kênh/Video/Mẫu)."""
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{MUTED}; font-size:13px; font-weight:600;")
        return lbl

    def _sec_hdr(self, text, color=ACCENT):
        """Tiêu đề KHU (chia bố cục thành phần rõ ràng): chấm màu + chữ hoa nhỏ."""
        w = QWidget(); r = QHBoxLayout(w)
        r.setContentsMargins(0, 6, 0, 0); r.setSpacing(8)
        dot = QLabel(); dot.setFixedSize(9, 9)
        dot.setStyleSheet(f"background:{color}; border-radius:4px;")
        lab = QLabel(text.upper())
        lab.setStyleSheet(f"color:{MUTED}; font-size:11px; font-weight:800;"
                          "letter-spacing:1px;")
        r.addWidget(dot); r.addWidget(lab); r.addStretch(1)
        return w

    def _update_ai_status(self):
        """Nhãn AI đang dùng trên màn chính: Gemini có/chưa key, hay Ollama."""
        from config import settings
        p = settings.LLM_PROVIDER
        if p == "gemini":
            txt, col = (("AI: Gemini (có key)", SUCCESS)
                        if settings.GEMINI_API_KEY else
                        ("AI: Gemini (chưa có key!)", DANGER))
        elif p == "groq":
            txt, col = (("AI: Groq (mây, free)", SUCCESS)
                        if settings.groq_keys() else
                        ("AI: Groq (chưa có key!)", DANGER))
        else:
            txt, col = "AI: Ollama (máy)", MUTED
        self.ai_status.setText(txt)
        self.ai_status.setStyleSheet(f"color:{col}; font-size:12px; font-weight:700;")

    # ---- Tùy chỉnh cắt (ngôn ngữ / Min-Max / mục đích / phong cách) ----
    def _cut_preset(self) -> dict:
        """Đọc tùy chỉnh cắt từ QSettings -> preset truyền vào job tạo clip."""
        s = self._settings
        return {
            "min_len": float(s.value("cut_min", 60, type=int)),
            "max_len": float(s.value("cut_max", 0, type=int)),
            "count": int(s.value("cut_count", 0, type=int)),
            "purpose": s.value("cut_purpose", "") or "",
            "style": s.value("cut_style", "") or "",
        }

    def _cut_settings(self):
        from config import update_env, Settings, settings
        s = self._settings
        dlg = QDialog(self); dlg.setWindowTitle("Tùy chỉnh cắt"); dlg.resize(440, 380)
        lay = QVBoxLayout(dlg); lay.setSpacing(8)
        lay.addWidget(QLabel("Ngôn ngữ video (nghe-chép chính xác hơn nếu chọn đúng):"))
        lang = QComboBox()
        for label, code in (("Tự động nhận", ""), ("Tiếng Việt", "vi"),
                            ("English", "en"), ("Tiếng Nhật", "ja"),
                            ("Tiếng Hàn", "ko"), ("Tiếng Trung", "zh"),
                            ("Tiếng Thái", "th"), ("Tây Ban Nha", "es")):
            lang.addItem(label, code)
        i = lang.findData(settings.WHISPER_LANGUAGE or "")
        lang.setCurrentIndex(i if i >= 0 else 0)
        lay.addWidget(lang)
        row = QHBoxLayout()
        row.addWidget(QLabel("Dài tối thiểu (giây):"))
        mn = QSpinBox(); mn.setRange(0, 600); mn.setValue(s.value("cut_min", 60, type=int))
        mn.setToolTip("0 = NGẪU NHIÊN (AI tự quyết độ dài theo nội dung)")
        row.addWidget(mn)
        row.addWidget(QLabel("Tối đa:"))
        mx = QSpinBox(); mx.setRange(0, 900); mx.setValue(s.value("cut_max", 0, type=int))
        mx.setToolTip("0 = không giới hạn trên"); row.addWidget(mx)
        lay.addLayout(row)
        lay.addWidget(QLabel("(Bỏ trống = đặt 0 thì độ dài NGẪU NHIÊN theo nội dung)"))
        # Số clip muốn cắt
        crow = QHBoxLayout()
        crow.addWidget(QLabel("Số clip muốn cắt:"))
        cnt = QSpinBox(); cnt.setRange(0, 20); cnt.setValue(s.value("cut_count", 0, type=int))
        cnt.setToolTip("0 = tự động/ngẫu nhiên (AI tự chọn 3-6 clip).")
        crow.addWidget(cnt)
        crow.addWidget(QLabel("(0 = ngẫu nhiên)"))
        crow.addStretch(1)
        lay.addLayout(crow)
        lay.addWidget(QLabel("Mục đích cắt:"))
        purpose = QComboBox()
        for label, key in (("Tự động", ""), ("Compilation (nhiều khoảnh khắc)", "compilation"),
                          ("Khoảnh khắc đỉnh", "peak"), ("Teaser (nhử)", "teaser"),
                          ("Arc câu chuyện", "story"), ("Highlights reel", "highlight")):
            purpose.addItem(label, key)
        purpose.setCurrentIndex(max(0, purpose.findData(s.value("cut_purpose", "") or "")))
        lay.addWidget(purpose)
        lay.addWidget(QLabel("Phong cách:"))
        style = QComboBox()
        for label, key in (("Tự động", ""), ("Hài hước", "funny"),
                         ("Kịch tính", "drama"), ("Thông tin/Tips", "info"),
                         ("Nhẹ nhàng", "calm"), ("Đánh giá", "review"),
                         ("Tình tiết/Story", "story")):
            style.addItem(label, key)
        style.setCurrentIndex(max(0, style.findData(s.value("cut_style", "") or "")))
        lay.addWidget(style); lay.addStretch(1)
        rowb = QHBoxLayout(); rowb.addStretch(1)
        sv = QPushButton("Lưu"); sv.setProperty("primary", True)

        def save():
            s.setValue("cut_min", mn.value()); s.setValue("cut_max", mx.value())
            s.setValue("cut_count", cnt.value())
            s.setValue("cut_purpose", purpose.currentData() or "")
            s.setValue("cut_style", style.currentData() or "")
            # ngôn ngữ -> .env để tiến trình phân tích (chạy riêng) đọc được
            update_env({"WHISPER_LANGUAGE": lang.currentData() or ""})
            self.status.setText("Đã lưu tùy chỉnh cắt. Áp dụng cho clip tạo MỚI.")
            dlg.accept()
        sv.clicked.connect(save); rowb.addWidget(sv)
        cancel = QPushButton("Hủy"); cancel.setProperty("ghost", True)
        cancel.clicked.connect(dlg.reject); rowb.addWidget(cancel)
        lay.addLayout(rowb)
        dlg.exec()

    # ---- kênh (project) / video ----
    def _reload_projects(self):
        self.proj.blockSignals(True); self.proj.clear()
        for p in services.list_projects():
            self.proj.addItem(p["name"], p["id"])
        self.proj.blockSignals(False)
        if self.proj.count():
            self._on_proj(self.proj.currentIndex())
        else:
            self._new_proj(first=True)

    def _del_proj(self):
        pid = self.proj.currentData()
        if pid is None:
            return
        name = self.proj.currentText()
        if QMessageBox.question(
            self, "Xóa kênh",
            f"Xóa kênh “{name}” (cả video, clip, file đã xuất)? Không hoàn tác được."
        ) == QMessageBox.StandardButton.Yes:
            services.delete_project(int(pid))
            self.state.project_id = None
            self._reload_projects()
            self.status.setText(f"Đã xóa kênh “{name}”.")

    def _ai_settings(self):
        """Hộp thoại chọn nguồn AI (máy/Gemini) + nhập key + chọn model + kiểm tra."""
        from PyQt6.QtWidgets import QApplication
        from config import settings, Settings, update_env
        from app.ai import llm
        dlg = QDialog(self); dlg.setWindowTitle("Cài đặt AI"); dlg.resize(500, 600)
        lay = QVBoxLayout(dlg); lay.setSpacing(7)
        lay.addWidget(QLabel("Nguồn AI:"))
        src = QComboBox()
        src.addItem("Groq — mây (FREE, khôn, nhẹ — khuyên dùng)", "groq")
        src.addItem("Gemini — mây (khôn nhất, có phí nhẹ)", "gemini")
        i = src.findData(settings.LLM_PROVIDER or "groq")
        src.setCurrentIndex(i if i >= 0 else 0)
        lay.addWidget(src)
        lay.addWidget(QLabel("Gemini API key (nhiều key thì mỗi dòng 1 key — tự xoay "
                             "vòng khi hết lượt):"))
        key = QPlainTextEdit(settings.GEMINI_API_KEY or "")
        key.setPlaceholderText("Dán 1 hoặc NHIỀU key, mỗi dòng 1 key")
        key.setFixedHeight(60); lay.addWidget(key)
        lay.addWidget(QLabel("Model Gemini:"))
        mdl = QComboBox()
        mdl.addItem("Gemini 2.5 Flash — nhanh, rẻ (khuyên)", "gemini-2.5-flash")
        mdl.addItem("Gemini 2.5 Pro — khôn nhất, chậm/đắt hơn", "gemini-2.5-pro")
        j = mdl.findData(settings.GEMINI_MODEL)
        mdl.setCurrentIndex(j if j >= 0 else 0)
        lay.addWidget(mdl)
        # ----- Nghe-chép (Whisper): Máy hay Groq (mây) -----
        lay.addWidget(QLabel("Nghe-chép lời (Whisper):"))
        wsrc = QComboBox()
        wsrc.addItem("Máy này — Local (cần GPU mới nhanh)", "local")
        wsrc.addItem("Groq — mây (FREE, máy yếu vẫn nhanh)", "groq")
        wi = wsrc.findData(settings.WHISPER_PROVIDER or "local")
        wsrc.setCurrentIndex(wi if wi >= 0 else 0)
        lay.addWidget(wsrc)
        lay.addWidget(QLabel("Groq API key (console.groq.com/keys — nhiều key mỗi "
                             "dòng 1):"))
        gkeys = QPlainTextEdit(settings.GROQ_API_KEYS or "")
        gkeys.setPlaceholderText("Để TRỐNG nếu chép lời bằng Máy")
        gkeys.setFixedHeight(50); lay.addWidget(gkeys)
        note = QLabel(""); note.setWordWrap(True)
        lay.addWidget(note); lay.addStretch(1)

        def set_note(kind, text):
            # kind: ok(xanh) / err(đỏ) / wait(vàng) / info(xám)
            c = {"ok": SUCCESS, "err": DANGER, "wait": WARN, "info": MUTED}[kind]
            bg = {"ok": "rgba(61,214,140,0.14)", "err": "rgba(255,107,116,0.14)",
                  "wait": "rgba(245,181,68,0.14)", "info": "transparent"}[kind]
            note.setStyleSheet(f"color:{c}; background:{bg}; border-radius:8px;"
                               f"padding:9px 11px; font-size:13px; font-weight:600;")
            note.setText(text)

        def friendly(err):
            e = err.lower()
            if any(s in e for s in ("api key not valid", "api_key_invalid",
                                    "invalid api key", "api key expired")):
                return "Key SAI hoặc hết hạn → hãy THAY key Gemini khác."
            if any(s in e for s in ("429", "quota", "resource_exhausted",
                                    "rate limit")):
                return "Hết lượt miễn phí (quota) → chờ mai, hoặc nạp tiền / đổi key."
            if "permission" in e or "403" in e:
                return "Key không có quyền dùng model này → đổi key/model."
            if "not found" in e or "404" in e:
                return "Không thấy model → chọn model Gemini khác."
            if any(s in e for s in ("connect", "timeout", "getaddrinfo",
                                    "network", "ssl", "max retries")):
                return "Lỗi MẠNG → kiểm tra internet rồi thử lại."
            return err[:150]

        def apply_live():
            Settings.LLM_PROVIDER = src.currentData()
            Settings.GEMINI_API_KEY = key.toPlainText().strip()
            Settings.GEMINI_MODEL = mdl.currentData()
            Settings.GROQ_API_KEYS = gkeys.toPlainText().strip()

        def do_test():
            apply_live()
            prov = src.currentData()
            if prov == "gemini" and not key.toPlainText().strip():
                set_note("err", "CHƯA NHẬP KEY — dán key Gemini vào ô trên rồi bấm "
                                "Kiểm tra.")
                return
            if prov == "groq" and not gkeys.toPlainText().strip():
                set_note("err", "CHƯA NHẬP KEY GROQ — dán key Groq ở ô dưới (mục "
                                "Nghe-chép) rồi bấm Kiểm tra.")
                return
            set_note("wait", "Đang kiểm tra kết nối...")
            QApplication.processEvents()
            try:
                r = llm.complete_text("Trả lời đúng 1 từ: OK", provider=prov)
                name = {"gemini": "Gemini (mây)", "groq": "Groq (mây)",
                        "ollama": "Ollama (máy)"}.get(prov, prov)
                set_note("ok", f"AI ĐANG HOẠT ĐỘNG — {name} trả lời: "
                               f"“{r.strip()[:30]}”. Bấm Lưu để dùng.")
            except Exception as e:  # noqa: BLE001
                set_note("err", "KHÔNG KẾT NỐI ĐƯỢC — " + friendly(str(e)))

        # gợi ý trạng thái ban đầu (chưa test) cho người dùng biết đang ở đâu
        set_note("info", "Dán key (Groq free hoặc Gemini) rồi bấm “Kiểm tra kết nối” "
                         "để xem AI có chạy không.")

        row = QHBoxLayout()
        tb = QPushButton("Kiểm tra kết nối"); tb.setProperty("ghost", True)
        tb.clicked.connect(do_test); row.addWidget(tb); row.addStretch(1)
        sv = QPushButton("Lưu"); sv.setProperty("primary", True)

        def do_save():
            update_env({"LLM_PROVIDER": src.currentData(),
                        "GEMINI_API_KEY": key.toPlainText().strip(),
                        "GEMINI_MODEL": mdl.currentData(),
                        "WHISPER_PROVIDER": wsrc.currentData(),
                        "GROQ_API_KEYS": gkeys.toPlainText().strip()})
            self._update_ai_status()
            self.status.setText(f"Đã lưu cài đặt AI: {src.currentText()} · nghe-chép "
                                f"{wsrc.currentText().split('—')[0].strip()}")
            dlg.accept()
        sv.clicked.connect(do_save); row.addWidget(sv)
        lay.addLayout(row)
        dlg.exec()

    # ---- KHO VIDEO chung: <gốc>/Đã tải + <gốc>/Đã xuất/<tên video> ----
    def _lib_root(self):
        from config import DATA_DIR
        p = self._settings.value("lib_root", "") or str(DATA_DIR / "KhoVideo")
        return Path(p)

    def _dl_dir(self):
        d = self._lib_root() / "Đã tải"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _export_root(self):
        d = self._lib_root() / "Đã xuất"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _pick_lib_root(self):
        """Chọn THƯ MỤC GỐC chung (chứa 'Đã tải' và 'Đã xuất')."""
        cur = str(self._lib_root())
        d = QFileDialog.getExistingDirectory(
            self, "Chọn KHO VIDEO gốc (sẽ tự tạo 'Đã tải' và 'Đã xuất' bên trong)",
            cur)
        if d:
            self._settings.setValue("lib_root", d)
            self.status.setText(f"Kho video: {d}  →  Đã tải / Đã xuất nằm trong đây")

    def _new_proj(self, first=False):
        name, ok = QInputDialog.getText(self, "Kênh mới",
                                        "Tên kênh (vd tên kênh TikTok):")
        if ok and name.strip():
            pid = services.create_project(name.strip())
            self._reload_projects()
            i = self.proj.findData(pid)
            if i >= 0:
                self.proj.setCurrentIndex(i)
        elif first:
            pass

    def _on_proj(self, _i):
        pid = self.proj.currentData()
        if pid is None:
            return
        self.state.set_project(int(pid))
        self._reload_videos()

    def _reload_videos(self):
        self.vid.blockSignals(True); self.vid.clear()
        if self.state.project_id:
            for v in services.list_videos(self.state.project_id):
                mark = "  • đã phân tích" if services.video_analyzed(v["id"]) else ""
                self.vid.addItem(f'{Path(v["src_path"]).name}{mark}', v["id"])
        self.vid.blockSignals(False)
        if self.vid.count():
            self._on_vid(self.vid.currentIndex())
        else:
            self.state.video_id = None
            self._refresh_clips(force=True)

    _VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".ts")

    def _add_video(self):
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo kênh trước.")
            return
        start = str(self._dl_dir()) if self._dl_dir().is_dir() else ""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn video (chọn nhiều cùng lúc được)", start,
            "Video (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.flv *.ts)")
        self._import_paths(files)

    def _import_paths(self, paths):
        """Import danh sách file video vào kênh đang chọn (dùng cho cả nút + kéo-thả)."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh",
                                   "Tạo/chọn kênh trước khi thêm video.")
            return
        vids = [p for p in paths
                if os.path.isfile(p) and p.lower().endswith(self._VIDEO_EXT)]
        for f in vids:
            services.import_video(self.state.project_id, f)
        if vids:
            self._reload_videos()
            self.status.setText(f"Đã thêm {len(vids)} video vào kênh.")
        elif paths:
            self.status.setText("Không có file video hợp lệ (mp4/mov/mkv...).")

    # ---- COOKIE YouTube: dán 1 lần, lưu file, tự dùng khi tải ----
    def _cookie_file(self):
        from config import DATA_DIR
        return DATA_DIR / "_potoken" / "youtube_cookies.txt"

    def _cookie_dir(self):
        from config import DATA_DIR
        d = DATA_DIR / "_potoken" / "cookies"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _cookie_profile_path(self, name):
        import re
        safe = re.sub(r"[^\w\-. ]", "_", str(name)).strip() or "cookie"
        return self._cookie_dir() / (safe + ".txt")

    def _list_cookie_profiles(self):
        return sorted(p.stem for p in self._cookie_dir().glob("*.txt"))

    def _migrate_old_cookie(self):
        """Chuyển file cookie đơn cũ -> hồ sơ 'Mặc định' (nếu chưa có hồ sơ)."""
        old = self._cookie_file()
        try:
            if old.exists() and not self._list_cookie_profiles():
                dst = self._cookie_profile_path("Mặc định")
                dst.write_text(old.read_text(encoding="utf-8", errors="ignore"),
                               encoding="utf-8")
                QSettings("AIContentStudio", "studio").setValue(
                    "yt_cookie_active", "Mặc định")
        except Exception:  # noqa: BLE001
            pass

    def _cookie_args(self):
        """Arg cookie cho yt-dlp: hồ sơ đang chọn > file cũ > trình duyệt."""
        st = QSettings("AIContentStudio", "studio")
        name = st.value("yt_cookie_active", "")
        if name:
            p = self._cookie_profile_path(name)
            try:
                if p.exists() and p.stat().st_size > 40:
                    return ["--cookies", str(p)]
            except Exception:  # noqa: BLE001
                pass
        old = self._cookie_file()
        try:
            if old.exists() and old.stat().st_size > 40:
                return ["--cookies", str(old)]
        except Exception:  # noqa: BLE001
            pass
        br = st.value("yt_cookie_browser", "")
        if br:
            return ["--cookies-from-browser", str(br)]
        return []

    def _youtube_cookie(self):
        from PyQt6.QtWidgets import QInputDialog
        self._migrate_old_cookie()
        st = QSettings("AIContentStudio", "studio")
        dlg = QDialog(self); dlg.setWindowTitle("Cookie YouTube (chống đòi đăng nhập)")
        dlg.resize(640, 600)
        v = QVBoxLayout(dlg)
        guide = QLabel(
            "<b>Khi YouTube đòi đăng nhập/cookie.</b> Có thể lưu NHIỀU hồ sơ "
            "cookie (mỗi tài khoản 1 hồ sơ) rồi chọn cái đang dùng — sau đổi "
            "tài khoản chỉ cần chọn lại hoặc thêm mới.<br><br>"
            "<b>Lấy cookie:</b> cài tiện ích <b>“Get cookies.txt LOCALLY”</b> → mở "
            "<b>youtube.com</b> (đã đăng nhập) → Export → copy hết file → dán vào "
            "ô dưới → <b>Lưu</b>.")
        guide.setWordWrap(True)
        guide.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        v.addWidget(guide)

        # --- hàng CHỌN HỒ SƠ cookie ---
        prow = QHBoxLayout()
        prow.addWidget(QLabel("Hồ sơ cookie:"))
        pcb = QComboBox(); pcb.setMinimumWidth(220)
        prow.addWidget(pcb, 1)
        addb = QPushButton("Thêm mới"); addb.setProperty("ghost", True)
        delb = QPushButton("Xóa hồ sơ"); delb.setProperty("ghost", True)
        prow.addWidget(addb); prow.addWidget(delb)
        v.addLayout(prow)

        # nút nạp THẲNG từ file cookies.txt (khỏi copy-paste)
        frow = QHBoxLayout()
        filb = QPushButton("Nạp từ file cookies.txt..."); filb.setProperty("ghost", True)
        filb.setToolTip("Chọn file .txt bạn vừa Export từ tiện ích — tự đổ vào ô dưới.")
        frow.addWidget(filb); frow.addStretch(1)
        v.addLayout(frow)

        box = QPlainTextEdit()
        box.setPlaceholderText("# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\t...\n"
                               "(hoặc bấm 'Nạp từ file cookies.txt...' ở trên)")
        v.addWidget(box, 1)

        brow = QHBoxLayout()
        brow.addWidget(QLabel("Hoặc lấy từ trình duyệt:"))
        bcb = QComboBox()
        bcb.addItems(["(không)", "chrome", "edge", "firefox", "brave", "chromium"])
        cur = st.value("yt_cookie_browser", "")
        if cur:
            i = bcb.findText(str(cur))
            if i >= 0:
                bcb.setCurrentIndex(i)
        brow.addWidget(bcb); brow.addStretch(1)
        v.addLayout(brow)

        note = QLabel(""); note.setWordWrap(True)
        note.setStyleSheet("font-size:12px;"); v.addWidget(note)

        rowb = QHBoxLayout(); rowb.addStretch(1)
        sv = QPushButton("Lưu"); sv.setProperty("primary", True)
        cancel = QPushButton("Đóng"); cancel.setProperty("ghost", True)
        rowb.addWidget(cancel); rowb.addWidget(sv)
        v.addLayout(rowb)

        def load_box(name):
            p = self._cookie_profile_path(name)
            try:
                box.setPlainText(p.read_text(encoding="utf-8", errors="ignore")
                                 if p.exists() else "")
            except Exception:  # noqa: BLE001
                box.setPlainText("")

        def refresh_combo(select=None):
            pcb.blockSignals(True); pcb.clear()
            profs = self._list_cookie_profiles()
            pcb.addItems(profs)
            tgt = select or st.value("yt_cookie_active", "") or (profs[0] if profs else "")
            if tgt:
                i = pcb.findText(str(tgt))
                if i >= 0:
                    pcb.setCurrentIndex(i)
            pcb.blockSignals(False)
            load_box(pcb.currentText()) if pcb.count() else box.clear()

        def on_pick():
            if pcb.currentText():
                load_box(pcb.currentText())
        pcb.currentTextChanged.connect(lambda _t: on_pick())

        def do_load_file():
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                dlg, "Chọn file cookies.txt", "",
                "Cookie/Text (*.txt *.cookies);;Tất cả (*.*)")
            if not path:
                return
            try:
                txt = open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception as e:  # noqa: BLE001
                note.setStyleSheet(f"color:{DANGER}; font-size:12px;")
                note.setText("Đọc file lỗi: " + str(e)[:120]); return
            box.setPlainText(txt)
            note.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")
            note.setText("Đã nạp file. Bấm Lưu để dùng.")
        filb.clicked.connect(do_load_file)

        def do_add():
            name, ok = QInputDialog.getText(dlg, "Thêm hồ sơ cookie",
                                            "Tên (vd: Acc chính, Acc reup 2):")
            if ok and name.strip():
                self._cookie_profile_path(name.strip()).write_text(
                    "# Netscape HTTP Cookie File\n", encoding="utf-8")
                refresh_combo(select=name.strip())
                note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
                note.setText("Đã tạo hồ sơ. Dán cookie vào ô rồi bấm Lưu.")
        addb.clicked.connect(do_add)

        def do_del():
            name = pcb.currentText()
            if not name:
                return
            try:
                self._cookie_profile_path(name).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
            if st.value("yt_cookie_active", "") == name:
                st.setValue("yt_cookie_active", "")
            refresh_combo()
            note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            note.setText("Đã xóa hồ sơ.")
        delb.clicked.connect(do_del)

        def do_save():
            name = pcb.currentText().strip()
            if not name:                       # chưa có hồ sơ -> tạo Mặc định
                name = "Mặc định"
                self._cookie_profile_path(name).write_text(
                    "# Netscape HTTP Cookie File\n", encoding="utf-8")
            txt = box.toPlainText().strip()
            if txt and "# Netscape HTTP Cookie File" not in txt:
                txt = "# Netscape HTTP Cookie File\n" + txt
            self._cookie_profile_path(name).write_text(
                (txt + "\n") if txt else "# Netscape HTTP Cookie File\n",
                encoding="utf-8")
            st.setValue("yt_cookie_active", name)
            br = bcb.currentText()
            st.setValue("yt_cookie_browser", "" if br == "(không)" else br)
            note.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")
            note.setText(f"Đã lưu & chọn hồ sơ '{name}'. Giờ bấm Tải lại nhé.")
            dlg.accept()
        sv.clicked.connect(do_save)
        cancel.clicked.connect(dlg.reject)

        refresh_combo()
        dlg.exec()

    # ---- tải video từ link YouTube (yt-dlp) ----
    def _download_youtube(self):
        url = self.yt_url.text().strip()
        if not url:
            QMessageBox.information(self, "Chưa có link", "Dán link YouTube vào ô.")
            return
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        exe = shutil.which("yt-dlp")
        if not exe:
            QMessageBox.warning(self, "Thiếu yt-dlp",
                                "Máy chưa có yt-dlp. Cài: pip install yt-dlp")
            return
        from config import settings
        dl = self._dl_dir()                  # KHO chung: <gốc>/Đã tải (giữ mãi)
        ff_dir = os.path.dirname(shutil.which("ffmpeg") or settings.FFMPEG_PATH
                                 or r"C:\ffmpeg\ffmpeg.exe")
        out_tmpl = str(dl / "%(title).80s.%(ext)s")
        cookie_args = self._cookie_args()
        self.yt_btn.setEnabled(False)
        self.status.setText("Đang tải video từ YouTube... (xem chờ chút)")

        def work():
            try:
                # Né "Sign in to confirm you're not a bot" KHÔNG cần cookie:
                # bật PO-token provider giống tool BQHungDown (best-effort).
                pot_args = []
                try:
                    from app.core import ytdlp_potoken
                    pot_args = ytdlp_potoken.ensure_running()
                except Exception:  # noqa: BLE001
                    pot_args = []
                ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/136.0.0.0 Safari/537.36")
                # --newline + --no-quiet --progress: ép yt-dlp in % theo từng dòng
                # (vì có --print nên mặc định nó im) -> đọc để hiện tiến trình.
                cmd = [exe, "--no-warnings", "--newline", "--no-quiet", "--progress",
                       "--user-agent", ua, "-f",
                       "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                       "--merge-output-format", "mp4", "--no-playlist",
                       "--print", "after_move:filepath", "-o", out_tmpl]
                cmd += pot_args
                cmd += cookie_args
                if ff_dir:
                    cmd += ["--ffmpeg-location", ff_dir]
                cmd.append(url)
                import re as _re
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=0x0800_0000)
                path, tail = "", []
                for line in proc.stdout:        # đọc từng dòng -> hiện %
                    line = line.strip()
                    if not line:
                        continue
                    tail.append(line); tail[:] = tail[-8:]
                    if os.path.exists(line):    # dòng after_move:filepath = đường dẫn
                        path = line
                    m = _re.search(r"\[download\]\s+([0-9.]+)%", line)
                    if m:
                        self.dl_progress.emit(f"Đang tải video... {m.group(1)}%")
                    elif "Merg" in line or "Fixup" in line:
                        self.dl_progress.emit("Đang ghép hình + tiếng...")
                    elif "[ExtractAudio]" in line or "Destination" in line:
                        self.dl_progress.emit("Đang xử lý...")
                proc.wait()
                if proc.returncode != 0:
                    self.dl_done.emit("", ("\n".join(tail) or "lỗi tải")[-300:])
                    return
                if not path or not os.path.exists(path):   # dự phòng: mp4 mới nhất
                    fs = sorted(dl.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
                    path = str(fs[-1]) if fs else ""
                self.dl_done.emit(path, "" if path else "Không thấy file tải.")
            except Exception as e:  # noqa: BLE001
                self.dl_done.emit("", str(e)[:300])

        threading.Thread(target=work, daemon=True).start()

    def _on_dl_done(self, path, err):
        self.yt_btn.setEnabled(True)
        if err or not path:
            low = (err or "").lower()
            if ("sign in" in low or "not a bot" in low or "confirm" in low
                    or "cookies" in low or "cookie" in low):
                msg = ("YouTube đòi đăng nhập/cookie cho video này.\n\n"
                       "Cách sửa (1 lần dùng mãi): bấm nút <b>Cookie</b> cạnh nút "
                       "Tải → làm theo hướng dẫn dán cookie → Lưu → Tải lại.")
                QMessageBox.warning(self, "YouTube đòi cookie", msg)
                self.status.setText("Tải LỖI: YouTube đòi cookie — bấm nút Cookie.")
            else:
                self.status.setText("Tải YouTube LỖI: " + (err or "không rõ"))
            return
        vid = services.import_video(self.state.project_id, path)
        self.yt_url.clear()
        self._reload_videos()
        # TỰ ĐỘNG phân tích luôn (dán link -> tải -> phân tích -> tự xuất nếu bật)
        jid = services.enqueue_auto(self.state.pool, vid, self.state.project_id,
                                    self._cut_preset())
        self._track_auto(jid, vid)
        extra = " → xong TỰ XUẤT" if self.auto_export_chk.isChecked() else ""
        self.status.setText(f"Đã tải xong → đang phân tích & cắt clip{extra}...")

    # ---- XEM & SỬA: phát video + cắt tay + tốc độ + xuất ----
    def _review_clip(self, c, part_no=1):
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        from PyQt6.QtCore import QUrl
        from PyQt6.QtWidgets import QSlider
        vrow = db.query_one("SELECT src_path FROM videos WHERE id=?", (c["video_id"],))
        if not vrow or not os.path.exists(vrow["src_path"]):
            QMessageBox.information(self, "Không xem được",
                                   "Không tìm thấy file video gốc (có thể đã xóa)."); return
        sig = db.loads(c["signals"], {}) or {}
        segs = sig.get("segments") or [[c["start_sec"], c["end_sec"]]]
        try:                                  # chống segments dị dạng
            trim = [float(segs[0][0]), float(segs[-1][1])]
        except (IndexError, TypeError, ValueError):
            trim = [float(c["start_sec"] or 0), float(c["end_sec"] or 0)]

        dlg = QDialog(self); dlg.setWindowTitle("Xem & sửa: " + (c["title"] or "clip"))
        dlg.resize(760, 680)
        lay = QVBoxLayout(dlg)
        vw = QVideoWidget(); vw.setMinimumHeight(380); lay.addWidget(vw, 1)
        player = QMediaPlayer(); ao = QAudioOutput()
        player.setAudioOutput(ao); player.setVideoOutput(vw)
        player.setSource(QUrl.fromLocalFile(vrow["src_path"]))
        dlg._player = player; dlg._ao = ao          # giữ tham chiếu

        # thanh thời gian + nút phát
        sld = QSlider(Qt.Orientation.Horizontal); sld.setRange(0, 1000)
        tlb = QLabel("0:00"); tlb.setFixedWidth(56)
        lay.addWidget(sld)
        row = QHBoxLayout()
        pb = QPushButton("Phát"); pb.setFixedWidth(80); pb.setProperty("primary", True)
        row.addWidget(pb); row.addWidget(tlb); row.addStretch(1)
        row.addWidget(QLabel("Tốc độ"))
        spcb = QComboBox()
        for t in ("1.0x", "1.1x", "1.2x", "1.3x", "1.5x"):
            spcb.addItem(t)
        cur_sp = float(sig.get("speed", self.layout_tpl.get("speed", 1.0)))
        for i in range(spcb.count()):
            if abs(float(spcb.itemText(i).rstrip("x")) - cur_sp) < 0.01:
                spcb.setCurrentIndex(i); break
        row.addWidget(spcb)
        lay.addLayout(row)

        # cắt tay: đặt đầu/cuối tại vị trí đang xem
        info = QLabel(); info.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        lay.addWidget(info)
        cutrow = QHBoxLayout()
        bin_ = QPushButton("Đặt ĐẦU tại đây"); bin_.setProperty("ghost", True)
        bout = QPushButton("Đặt CUỐI tại đây"); bout.setProperty("ghost", True)
        bjump = QPushButton("Tới đầu clip"); bjump.setProperty("ghost", True)
        cutrow.addWidget(bin_); cutrow.addWidget(bout); cutrow.addWidget(bjump)
        cutrow.addStretch(1)
        lay.addLayout(cutrow)

        def upd_info():
            d = trim[1] - trim[0]
            info.setText(f"Đoạn giữ: {_dur(trim[0])} → {_dur(trim[1])}  "
                         f"(dài {d:.1f}s)")
        upd_info()

        def fmt(ms):
            s = int(ms / 1000); return f"{s // 60}:{s % 60:02d}"

        def on_pos(ms):
            dur = player.duration() or 1
            sld.blockSignals(True); sld.setValue(int(ms / dur * 1000)); sld.blockSignals(False)
            tlb.setText(fmt(ms))
        player.positionChanged.connect(on_pos)
        sld.sliderMoved.connect(
            lambda v: player.setPosition(int(v / 1000 * (player.duration() or 0))))

        def toggle():
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause(); pb.setText("Phát")
            else:
                player.play(); pb.setText("Tạm dừng")
        pb.clicked.connect(toggle)
        spcb.currentIndexChanged.connect(
            lambda: player.setPlaybackRate(float(spcb.currentText().rstrip("x"))))
        bjump.clicked.connect(lambda: player.setPosition(int(trim[0] * 1000)))
        bin_.clicked.connect(lambda: (trim.__setitem__(0, player.position() / 1000.0),
                                      upd_info()))
        bout.clicked.connect(lambda: (trim.__setitem__(1, player.position() / 1000.0),
                                      upd_info()))
        player.setPosition(int(trim[0] * 1000))

        rowb = QHBoxLayout()
        sv = QPushButton("Lưu cắt"); sv.setProperty("ghost", True)
        rowb.addWidget(sv); rowb.addStretch(1)
        xb = QPushButton("Xuất clip này"); xb.setProperty("primary", True)
        rowb.addWidget(xb)
        cb = QPushButton("Đóng"); cb.setProperty("ghost", True); rowb.addWidget(cb)
        lay.addLayout(rowb)

        def save_trim():
            if trim[1] - trim[0] < 1.0:
                QMessageBox.information(dlg, "Đoạn quá ngắn", "Đầu/cuối chưa hợp lý.")
                return
            nsig = dict(sig)
            nsig["segments"] = [[round(trim[0], 2), round(trim[1], 2)]]
            nsig["n_seg"] = 1
            nsig["speed"] = float(spcb.currentText().rstrip("x"))
            db.execute("UPDATE clips SET start_sec=?, end_sec=?, signals=? WHERE id=?",
                       (round(trim[0], 2), round(trim[1], 2), db.dumps(nsig), c["id"]))
            self._refresh_clips(force=True)
            self.status.setText("Đã lưu cắt tay + tốc độ cho clip.")
        sv.clicked.connect(save_trim)

        def do_export():
            save_trim()
            player.stop()
            dlg.accept()
            self._export_video(self.state.video_id, c["id"])
        xb.clicked.connect(do_export)
        cb.clicked.connect(lambda: (player.stop(), dlg.reject()))
        dlg.exec()
        player.stop()

    # ---- kéo-thả video ----
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        self._import_paths(paths)
        e.acceptProposedAction()

    def _on_vid(self, _i):
        vid = self.vid.currentData()
        if vid is not None:
            self.state.set_video(int(vid))
            self._refresh_clips(force=True)

    def _del_video(self):
        vid = self.state.video_id
        if not vid:
            return
        if QMessageBox.question(
            self, "Xóa video",
            "Xóa video này khỏi kênh (cả dữ liệu phân tích + clip đã tạo)?"
        ) == QMessageBox.StandardButton.Yes:
            services.delete_video(int(vid))
            self.state.video_id = None
            self._reload_videos()
            self.status.setText("Đã xóa video.")

    # ---- menu chuột phải: xóa kênh / video ----
    def _proj_menu(self, pos):
        m = QMenu(self)
        if self.proj.currentData() is not None:
            m.addAction("Xóa kênh này", self._del_proj)
        m.addAction("Quản lý / Xóa nhiều kênh…", self._manage_projects)
        m.exec(self.proj.mapToGlobal(pos))

    def _vid_menu(self, pos):
        m = QMenu(self)
        if self.vid.currentData() is not None:
            m.addAction("Xóa video đang chọn", self._del_video)
        m.addAction("Quản lý / Xóa nhiều video…", self._manage_videos)
        m.exec(self.vid.mapToGlobal(pos))

    def _delete_picker(self, title, hint, rows, do_delete):
        """Hộp TÍCH Ô chọn nhiều mục rồi xóa. rows=[(id, text)];
        do_delete(ids)->số đã xóa. Tích ô (không cần giữ Ctrl)."""
        dlg = QDialog(self); dlg.setWindowTitle(title); dlg.resize(560, 520)
        lay = QVBoxLayout(dlg)
        h = QLabel(hint); h.setWordWrap(True); lay.addWidget(h)
        lst = QListWidget()
        for oid, text in rows:
            it = QListWidgetItem(text)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, oid)
            lst.addItem(it)
        lay.addWidget(lst, 1)

        def checked():
            return [lst.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(lst.count())
                    if lst.item(i).checkState() == Qt.CheckState.Checked]

        def run():
            ids = checked()
            if not ids:
                QMessageBox.information(dlg, "Chưa chọn", "Hãy TÍCH ô mục cần xóa.")
                return
            if QMessageBox.question(
                dlg, title, f"Xóa {len(ids)} mục đã chọn? Không hoàn tác được."
            ) != QMessageBox.StandardButton.Yes:
                return
            n = do_delete(ids)
            dlg.accept()
            self.status.setText(f"Đã xóa {n} mục.")

        def set_all(state):
            for i in range(lst.count()):
                lst.item(i).setCheckState(state)

        rowb = QHBoxLayout()
        ca = QPushButton("Chọn tất cả"); ca.setProperty("ghost", True)
        ca.clicked.connect(lambda: set_all(Qt.CheckState.Checked))
        cn = QPushButton("Bỏ chọn"); cn.setProperty("ghost", True)
        cn.clicked.connect(lambda: set_all(Qt.CheckState.Unchecked))
        rowb.addWidget(ca); rowb.addWidget(cn); rowb.addStretch(1)
        delb = QPushButton("Xóa mục đã chọn"); delb.setProperty("danger", True)
        delb.clicked.connect(run); rowb.addWidget(delb)
        close = QPushButton("Đóng"); close.setProperty("ghost", True)
        close.clicked.connect(dlg.reject); rowb.addWidget(close)
        lay.addLayout(rowb)
        dlg.exec()

    def _manage_videos(self):
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        vids = services.list_videos(self.state.project_id)
        if not vids:
            QMessageBox.information(self, "Chưa có video", "Kênh chưa có video nào.")
            return
        rows = [(v["id"], Path(v["src_path"]).name
                 + ("   (đã có clip)" if services.list_clips(v["id"]) else ""))
                for v in vids]

        def do(ids):
            for vid in ids:
                services.delete_video(int(vid))
                if self.state.video_id == int(vid):
                    self.state.video_id = None
            self._reload_videos()
            return len(ids)

        self._delete_picker("Xóa video", "Tích ô các video cần xóa rồi bấm "
                            "<b>Xóa mục đã chọn</b> (xóa cả phân tích + clip + file).",
                            rows, do)

    def _manage_projects(self):
        projs = services.list_projects()
        if not projs:
            QMessageBox.information(self, "Chưa có kênh", "Chưa có kênh nào.")
            return
        rows = [(p["id"], f'{p["name"]}   ({len(services.list_videos(p["id"]))} video)')
                for p in projs]

        def do(ids):
            for pid in ids:
                services.delete_project(int(pid))
                if self.state.project_id == int(pid):
                    self.state.project_id = None
            self._reload_projects()
            return len(ids)

        self._delete_picker("Xóa kênh", "Tích ô các kênh cần xóa rồi bấm "
                            "<b>Xóa mục đã chọn</b> (xóa cả video + clip + file).",
                            rows, do)

    # ---- tạo clip ----
    def _track_auto(self, job_id, video_id):
        """Nếu BẬT tự-động-xuất: ghi nhớ job phân tích này để xong thì tự xuất."""
        if job_id and self.auto_export_chk.isChecked():
            self._pending_export[job_id] = video_id

    def _check_auto_export(self):
        """Định kỳ: job phân tích nào XONG -> tự xuất hết clip của video đó."""
        if not self._pending_export:
            return
        ready, total = 0, 0
        for jid in list(self._pending_export):
            st = services.job_state(jid)
            if st == "done":
                vid = self._pending_export.pop(jid)
                try:
                    total += self._export_video(vid)
                    ready += 1
                except Exception:  # noqa: BLE001
                    pass
            elif st in ("failed", "canceled", "skipped", ""):
                self._pending_export.pop(jid, None)   # lỗi/mất -> thôi, không xuất
        if ready:
            self.status.setText(
                f"Phân tích xong {ready} video — đang TỰ ĐỘNG xuất {total} clip "
                "vào thư mục kênh (đúng thứ tự Part)...")

    def _auto(self):
        if not (self.state.project_id and self.state.video_id):
            QMessageBox.information(self, "Chưa chọn video", "Hãy thêm/chọn video.")
            return
        # ĐÃ có clip -> hỏi CẮT LẠI với cài đặt cắt hiện tại (nhanh: khỏi chép lời lại)
        if services.list_clips(self.state.video_id):
            if QMessageBox.question(
                self, "Cắt lại?",
                "Video này đã có clip.\n\nCẮT LẠI theo cài đặt hiện tại "
                "(độ dài Min/Max, mục đích, kiểu)? Nhanh — KHÔNG chép lời lại, "
                "clip cũ (chưa xuất) sẽ thay bằng clip mới.\n\n"
                "Bấm No để giữ nguyên clip cũ.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            ) != QMessageBox.StandardButton.Yes:
                self.status.setText("Giữ nguyên clip cũ.")
                return
        jid = services.enqueue_auto(self.state.pool, self.state.video_id,
                                    self.state.project_id, self._cut_preset())
        self._track_auto(jid, self.state.video_id)
        extra = " → xong sẽ TỰ xuất" if self.auto_export_chk.isChecked() else ""
        self.status.setText(f"Đang phân tích & cắt clip{extra}... (xem tiến trình dưới)")

    def _auto_all(self):
        """Đưa MỌI video chưa có clip trong kênh vào hàng đợi (chạy song song)."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        vids = services.list_videos(self.state.project_id)
        if not vids:
            QMessageBox.information(self, "Chưa có video", "Thêm video vào kênh trước.")
            return
        n = 0
        for v in vids:
            if services.list_clips(v["id"]):   # đã có clip -> bỏ qua, khỏi làm lại
                continue
            jid = services.enqueue_auto(self.state.pool, v["id"],
                                        self.state.project_id, self._cut_preset())
            self._track_auto(jid, v["id"])
            n += 1
        if n:
            extra = " (xong tự xuất luôn)" if self.auto_export_chk.isChecked() else ""
            self.status.setText(
                f"Đã đưa {n} video vào hàng đợi — chạy song song{extra}. Bạn có thể "
                "chuyển KÊNH khác rồi bấm 'Tất cả' tiếp để gộp hàng đợi.")
        else:
            self.status.setText("Mọi video trong kênh đều đã có clip rồi.")

    def _pick_videos(self):
        """Hộp thoại TÍCH CHỌN nhiều video cụ thể trong kênh để tạo clip cùng lúc."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        vids = services.list_videos(self.state.project_id)
        if not vids:
            QMessageBox.information(self, "Chưa có video", "Thêm video vào kênh trước.")
            return
        dlg = QDialog(self); dlg.setWindowTitle("Chọn nhiều video để tạo clip")
        dlg.resize(480, 500)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Tích các video muốn tạo clip:"))
        lst = QListWidget()
        for v in vids:
            done = bool(services.list_clips(v["id"]))
            it = QListWidgetItem(("(đã có clip) " if done else "") + Path(v["src_path"]).name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked if done else Qt.CheckState.Checked)
            it.setData(Qt.ItemDataRole.UserRole, v["id"])
            lst.addItem(it)
        lay.addWidget(lst, 1)
        rowb = QHBoxLayout()
        ball = QPushButton("Chọn tất cả"); ball.setProperty("ghost", True)
        ball.clicked.connect(lambda: [lst.item(i).setCheckState(Qt.CheckState.Checked)
                                      for i in range(lst.count())])
        bnone = QPushButton("Bỏ chọn"); bnone.setProperty("ghost", True)
        bnone.clicked.connect(lambda: [lst.item(i).setCheckState(Qt.CheckState.Unchecked)
                                       for i in range(lst.count())])
        rowb.addWidget(ball); rowb.addWidget(bnone); rowb.addStretch(1)
        ok = QPushButton("Tạo clip"); ok.setProperty("primary", True)
        ok.clicked.connect(dlg.accept); rowb.addWidget(ok)
        lay.addLayout(rowb)
        if not dlg.exec():
            return
        ids = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
               if lst.item(i).checkState() == Qt.CheckState.Checked]
        for vid in ids:
            jid = services.enqueue_auto(self.state.pool, vid,
                                        self.state.project_id, self._cut_preset())
            self._track_auto(jid, vid)
        extra = " — xong tự xuất luôn" if self.auto_export_chk.isChecked() else ""
        self.status.setText(f"Đã đưa {len(ids)} video vào hàng đợi (chạy song song){extra}."
                            if ids else "Chưa chọn video nào.")

    # ---- mẫu ----
    def _a_frame(self):
        """Lấy 1 khung hình để chỉnh mẫu (clip đầu hoặc giữa video)."""
        vid = self.state.video_id
        if not vid:
            return None
        vrow = db.query_one(
            "SELECT v.src_path, v.duration, p.assets_dir FROM videos v "
            "JOIN projects p ON p.id=v.project_id WHERE v.id=?", (vid,))
        if not vrow:
            return None
        clips = services.list_clips(vid)
        t = (clips[0]["start_sec"] + clips[0]["end_sec"]) / 2 if clips \
            else (vrow["duration"] or 4) / 2
        frame = Path(services.cache_dir(vrow["assets_dir"])) / "_preview.jpg"
        return str(frame) if extract_frame(vrow["src_path"], t, frame, 360) else None

    def _sample_frame(self):
        """Ảnh nền MẪU khi chưa chọn video — để Chỉnh mẫu không bắt phải có video."""
        from config import DATA_DIR
        from PyQt6.QtGui import (QImage, QPainter, QLinearGradient, QColor, QFont)
        d = DATA_DIR / "_cache"; d.mkdir(parents=True, exist_ok=True)
        out = d / "_tpl_sample.jpg"
        img = QImage(360, 640, QImage.Format.Format_RGB888)
        g = QLinearGradient(0, 0, 0, 640)
        g.setColorAt(0.0, QColor("#2A3550")); g.setColorAt(1.0, QColor("#0E1320"))
        pt = QPainter(img); pt.fillRect(img.rect(), g)
        pt.setPen(QColor("#9AA6BF")); pt.setFont(QFont("Arial", 13))
        pt.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter,
                    "XEM TRƯỚC MẪU\n(chưa chọn video)")
        pt.end(); img.save(str(out), "JPG", 90)
        return str(out)

    def _edit_template(self):
        frame = self._a_frame() or self._sample_frame()   # có video thì dùng, không thì ảnh mẫu
        dlg = EditorDialog(frame, self.layout_tpl, self,
                           current_name=self.tmpl_box.currentData() or "")
        if dlg.exec() and dlg.layout_result:
            name = (getattr(dlg, "_current_name", "")
                    or self.tmpl_box.currentData() or "")
            # làm mới + CHỌN đúng mẫu vừa sửa, rồi NẠP LẠI TỪ DB để layout dùng
            # khi xuất KHỚP 100% với mẫu đã lưu (tránh lưu 1 nơi xuất 1 nơi).
            self._populate_templates(name)
            self._settings.setValue("last_template", name)
            self._apply_selected_template()
            self.status.setText(f"Đã lưu & đang dùng mẫu: {name or 'Mặc định'}. "
                                "Bấm Tải để xuất theo mẫu này.")

    # ---- chọn / nhớ mẫu (hiện ngoài màn chính) ----
    def _populate_templates(self, select_name: str = ""):
        """Đổ danh sách mẫu vào combo, chọn lại theo tên (KHÔNG áp lại layout)."""
        self.tmpl_box.blockSignals(True)
        self.tmpl_box.clear()
        self.tmpl_box.addItem("Mặc định (không mẫu)", "")
        for t in services.list_templates():
            self.tmpl_box.addItem(t["name"], t["name"])
        i = self.tmpl_box.findData(select_name)
        self.tmpl_box.setCurrentIndex(i if i >= 0 else 0)
        self.tmpl_box.blockSignals(False)

    def _apply_selected_template(self):
        """Nạp layout của mẫu đang chọn vào layout_tpl (dùng khi xuất)."""
        name = self.tmpl_box.currentData() or ""
        tpl = services.get_template(name) if name else None
        self.layout_tpl = tpl if tpl else copy.deepcopy(DEFAULT_LAYOUT)

    def _on_template_pick(self):
        name = self.tmpl_box.currentData() or ""
        self._settings.setValue("last_template", name)  # nhớ cho lần sau
        self._apply_selected_template()
        self.status.setText(f"Đang dùng mẫu: {self.tmpl_box.currentText()}. "
                            "Bấm Tải/Tải tất cả để xuất theo mẫu này.")

    # ---- danh sách clip ----
    def _refresh_clips(self, force=False):
        vid = self.state.video_id
        clips = services.list_clips(vid) if vid else []
        if not force and getattr(self, "_n", -1) == len(clips) \
                and all(getattr(self, "_st", {}).get(c["id"]) == c["status"]
                        for c in clips):
            return
        self._n = len(clips)
        self._st = {c["id"]: c["status"] for c in clips}
        self._cur_clips = clips
        self._cur_vrow = db.query_one(
            "SELECT v.src_path, p.assets_dir FROM videos v "
            "JOIN projects p ON p.id=v.project_id WHERE v.id=?", (vid,)) if vid else None
        self._rebuild_rows()

    def _rebuild_rows(self):
        clips = getattr(self, "_cur_clips", [])
        vrow = getattr(self, "_cur_vrow", None)
        while self.list_box.count() > 1:
            w = self.list_box.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.count_lbl.setText(f"{len(clips)} clip đề xuất" if clips else "")
        if not clips:
            self.list_box.insertWidget(self.list_box.count() - 1, self._empty_state())
            return
        missing = []
        for i, c in enumerate(clips):
            self.list_box.insertWidget(self.list_box.count() - 1,
                                       self._clip_row(c, vrow, i + 1))
            if vrow:
                tp = Path(services.cache_dir(vrow["assets_dir"])) / f"_thumb_{c['id']}.jpg"
                if not tp.exists():
                    missing.append(dict(c))
        # tạo thumbnail còn thiếu CHẠY NGẦM (không chặn giao diện)
        if missing and vrow and not self._thumb_busy:
            self._thumb_busy = True
            import threading
            threading.Thread(target=self._bg_thumbs, args=(missing, vrow),
                             daemon=True).start()

    def _bg_thumbs(self, clips, vrow):
        for c in clips:
            tp = Path(services.cache_dir(vrow["assets_dir"])) / f"_thumb_{c['id']}.jpg"
            if tp.exists():
                continue
            sig = db.loads(c["signals"], {}) or {}
            segs = sig.get("segments")
            t = ((segs[0][0] + segs[0][1]) / 2 if segs and len(segs[0]) >= 2
                 else (c["start_sec"] + c["end_sec"]) / 2)
            try:
                extract_frame(vrow["src_path"], t, tp, width=232)
            except Exception:  # noqa: BLE001
                pass
        self._thumb_busy = False
        self.thumbs_ready.emit()

    def _empty_state(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 60, 0, 0)
        lay.setSpacing(10)
        icon = QLabel("+")
        icon.setStyleSheet(f"font-size:46px; font-weight:700; color:{ACCENT};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)
        t1 = QLabel("Chưa có clip nào")
        t1.setStyleSheet("font-size:18px; font-weight:600;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t1)
        t2 = QLabel("KÉO-THẢ video vào đây (hoặc “+ Thêm video”), rồi bấm "
                    "“Tạo clip”.")
        t2.setStyleSheet(f"color:{MUTED};")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t2)
        return w

    def _clip_row(self, c, vrow=None, part_no=1):
        sig = db.loads(c["signals"], {}) or {}
        w = QWidget(); w.setObjectName("clipCard")
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # thẻ KHÔNG viền — phân biệt bằng nền + sáng lên khi rê chuột
        w.setStyleSheet(f"#clipCard{{background:{BASE}; border-radius:14px;}}"
                        f"#clipCard:hover{{background:{SURFACE};}}")
        lay = QHBoxLayout(w); lay.setContentsMargins(12, 10, 16, 10); lay.setSpacing(14)

        # ---- SỐ THỨ TỰ PART (đầu thẻ, theo thứ tự danh sách = thứ tự xuất) ----
        pw = QWidget(); pw.setFixedWidth(48)
        pcol = QVBoxLayout(pw); pcol.setContentsMargins(0, 0, 0, 0); pcol.setSpacing(0)
        cap = QLabel("PART"); cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap.setStyleSheet(f"color:{MUTED}; font-size:9px; font-weight:700;")
        num = QLabel(str(part_no)); num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(f"color:{ACCENT}; font-size:26px; font-weight:800;")
        pcol.addWidget(cap); pcol.addWidget(num)
        lay.addWidget(pw)

        # ---- thumbnail (ảnh đại diện) ----
        thumb = QLabel(); thumb.setFixedSize(132, 74)
        thumb.setStyleSheet("background:#000; border-radius:9px;")
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = self._thumb(c, sig, vrow)
        if pm:
            thumb.setPixmap(pm)
        lay.addWidget(thumb)

        info = QVBoxLayout(); info.setSpacing(2)

        def _shrinkable(lbl):
            # cho nhãn CO LẠI được, không đẩy thẻ rộng ra (tránh tràn/cuộn ngang)
            lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            return lbl

        title = QLabel(("[Ghép] " if sig.get("mode") == "mixed" else "")
                       + (c["title"] or "Clip"))
        title.setStyleSheet("font-size:16px; font-weight:500; border:none;")
        title.setToolTip("Tiêu đề tiếng Việt — để đọc hiểu nội dung")
        info.addWidget(_shrinkable(title))
        en = (sig.get("title_en") or "").strip()
        if en:  # tiêu đề tiếng Anh (nhỏ, mờ) = cái sẽ GẮN LÊN video
            en_lbl = QLabel(en)
            en_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px; border:none;")
            en_lbl.setToolTip("Tiêu đề tiếng Anh — sẽ gắn lên video khi xuất")
            info.addWidget(_shrinkable(en_lbl))
        # ---- BÁO RÕ AI nào đã phân tích clip này ----
        ai = sig.get("ai") or ""
        if sig.get("llm_used"):
            aname = sig.get("ai_name") or {"gemini": "Gemini",
                                           "ollama": "Ollama (máy)"}.get(ai, "AI")
            btxt = "Phân tích bằng " + aname + (" + xem hình"
                                                if sig.get("vision") else "")
            bcol = SUCCESS if ai == "gemini" else ACCENT
        else:
            btxt = "Cắt cơ bản (chưa qua AI)"
            bcol = WARN
        ai_lbl = QLabel(btxt)
        ai_lbl.setStyleSheet(f"color:{bcol}; font-size:11px; font-weight:700; "
                             "border:none;")
        info.addWidget(_shrinkable(ai_lbl))
        total = sig.get("dur") or (c["end_sec"] - c["start_sec"])
        segs = sig.get("segments") or []
        nseg = sig.get("n_seg", len(segs) or 1)
        seg_note = f" · ghép {nseg} đoạn hay" if nseg and nseg > 1 else ""
        sub = QLabel(f'{_dur(total)}{seg_note} · {c["reason"] or ""}'[:100])
        sub.setStyleSheet(f"color:{MUTED}; font-size:13px; border:none;")
        info.addWidget(_shrinkable(sub))
        if len(segs) > 1:                 # CHO THẤY AI giữ/bỏ đoạn nào
            info.addWidget(_SegBar(segs))
        lay.addLayout(info, 1)

        # ---- điểm viral (nhỏ, phía sau, chỉ tham khảo) ----
        sc = QLabel(str(int(c["score"] or 0)))
        sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.setStyleSheet(f"background:{SURFACE}; color:{MUTED}; border-radius:9px; "
                         "padding:2px 9px; font-size:12px; font-weight:600;")
        sc.setToolTip("Điểm tiềm năng viral (0–100) — AI chấm theo nội dung + hình ảnh")
        lay.addWidget(sc)

        pv = QPushButton("Xem & sửa"); pv.setFixedWidth(92); pv.setProperty("ghost", True)
        pv.setToolTip("Phát video, chỉnh tốc độ, cắt tay đầu/cuối rồi xuất.")
        pv.clicked.connect(lambda _, cc=c, n=part_no: self._review_clip(cc, n))
        lay.addWidget(pv)
        if c["status"] == "exported" and c["export_path"]:
            mo = QPushButton("Mở"); mo.setFixedWidth(64); mo.setProperty("ghost", True)
            mo.clicked.connect(lambda _, p=c["export_path"]: self._open_file(p))
            lay.addWidget(mo)
            label = "Tải lại"
        else:
            label = "Tải"
        dl = QPushButton(label); dl.setFixedWidth(80); dl.setProperty("primary", True)
        dl.clicked.connect(
            lambda _, cid=c["id"]: self._export_video(self.state.video_id, cid))
        lay.addWidget(dl)
        rm = QPushButton("Xóa"); rm.setFixedWidth(64); rm.setProperty("danger", True)
        rm.clicked.connect(lambda _, cid=c["id"]: self._del_clip(cid))
        lay.addWidget(rm)
        return w

    def _thumb(self, c, sig, vrow):
        """Trả QPixmap thumbnail từ CACHE (đã tạo). Chưa có -> None (tạo ngầm sau)."""
        if not vrow:
            return None
        tp = Path(services.cache_dir(vrow["assets_dir"])) / f"_thumb_{c['id']}.jpg"
        if tp.exists():
            pm = QPixmap(str(tp))
            if not pm.isNull():
                return pm.scaled(132, 74, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        return None

    def _del_clip(self, cid):
        services.delete_clip(cid)
        self._refresh_clips(force=True)

    # ---- xuất ----
    def _video_px_for(self, vrow):
        """Vùng KHỐI VIDEO trong khung 1080x1920 (để chữ tránh, không đè video)."""
        vr = self.layout_tpl.get("video_rect")
        if not vr or not vrow or not vrow["width"] or not vrow["height"]:
            return None
        cx, cy, sw = vr
        ow, oh = 1080, 1920
        vw = sw * ow
        vh = vw * (float(vrow["height"]) / float(vrow["width"]))
        return (cx * ow - vw / 2, cy * oh - vh / 2, vw, vh)

    def _fixed_label(self):
        """Chữ cố định đầu tiên trong mẫu (khi clip không có tiêu đề AI)."""
        for ly in self.layout_tpl.get("layers", []):
            t = (ly.get("text") or "").strip()
            if (t and not ly.get("is_part")
                    and not any(k in t for k in ("{title}", "{title_vi}", "{n}"))):
                return t
        return ""

    def _render_png(self, part_no, title="", cid=0, title_vi="", video_px=None,
                    project_id=None):
        layers = self.layout_tpl.get("layers", [])
        pid = project_id or self.state.project_id
        if not layers or not pid:
            return None
        # mỗi clip 1 PNG riêng (theo cid) vì tiêu đề khác nhau — để trong _cache
        png = os.path.join(services.project_cache_dir(pid),
                           f"_ovl_{cid or part_no}.png")
        return (png if render_overlay_png(layers, part_no, 1080, 1920, png,
                                          title, title_vi, video_px) else None)

    def _export_video(self, video_id, only_clip_id=None):
        """
        Xuất clip của 1 video THEO ĐÚNG THỨ TỰ: Part = vị trí trong danh sách
        clip (sắp theo thời gian). part_no gán cố định nên dù chạy đa luồng/hàng
        loạt vẫn đúng (vd1 Part1,2; vd2 Part1..5...). Tên file: "<video> - Part N <tiêu đề>".
        only_clip_id != None -> chỉ xuất 1 clip đó (giữ đúng số Part của nó).
        Trả số clip đã đưa vào hàng đợi.
        """
        clips = services.list_clips(video_id)
        if not clips:
            return 0
        vrow = db.query_one(
            "SELECT v.src_path, v.width, v.height, v.project_id FROM videos v "
            "WHERE v.id=?", (video_id,))
        if not vrow:
            return 0
        pid = vrow["project_id"] or self.state.project_id   # đúng KÊNH của video
        vr = self.layout_tpl.get("video_rect")
        bg = self.layout_tpl.get("bg", "blur")
        tb = self.layout_tpl.get("trim_black", False)
        vpx = self._video_px_for(vrow)
        n = 0
        jids = []
        for i, c in enumerate(clips):
            no = i + 1                         # số Part = vị trí trong video này
            if only_clip_id and c["id"] != only_clip_id:
                continue
            sig = db.loads(c["signals"], {}) or {}
            vi = (c["title"] or "").strip()
            en = ((sig.get("title_en") or vi)).strip()
            label = en or vi or self._fixed_label()
            # tên gọn "Part 1 <tiêu đề>" — đã nhóm theo folder video nên không lẫn
            out_name = f"Part {no} {label}".strip()
            jid = services.enqueue_export(
                self.state.pool, c["id"], video_id, pid,
                out_dir=str(self._export_root()),   # KHO chung: <gốc>/Đã xuất/<video>
                video_rect=vr, bg=bg, trim_black=tb, part_no=no, out_name=out_name,
                captions=bool(self.layout_tpl.get("captions", True)),
                cap_style={
                    "font": self.layout_tpl.get("cap_font", "Anton"),
                    "size": self.layout_tpl.get("cap_size", 0),
                    "color": self.layout_tpl.get("cap_color", ""),
                    "ny": self.layout_tpl.get("cap_ny", 0.78),
                    "preset": self.layout_tpl.get("cap_preset",
                                                  "Trắng đơn giản"),
                    "delay": self.layout_tpl.get("cap_delay", 0.12),
                    "hook_on": self.layout_tpl.get("cap_hook", True),
                    "hook_dur": self.layout_tpl.get("cap_hook_dur", 6.0)},
                blur_amt=int(self.layout_tpl.get("blur_amt", 22)),
                speed=float(sig.get("speed", self.layout_tpl.get("speed", 1.0))),
                pitch=float(self.layout_tpl.get("pitch", 1.0)),
                overlay_png=self._render_png(no, en, c["id"], vi, vpx, pid))
            if jid:
                jids.append(jid)
            n += 1
            QApplication.processEvents()   # nhả cho UI đỡ đơ khi vẽ ảnh chữ hàng loạt
        return n

    def _export_all(self):
        """Tải tất cả clip của VIDEO đang chọn (theo Part)."""
        if not self.state.video_id:
            return
        if not services.list_clips(self.state.video_id):
            QMessageBox.information(self, "Chưa có clip", "Bấm 'Tạo clip tự động' trước.")
            return
        n = self._export_video(self.state.video_id)
        self.status.setText(f"Đang xuất {n} clip (video này) theo thứ tự Part...")

    def _export_all_channel(self):
        """Xuất TẤT CẢ clip của MỌI video trong kênh — đúng thứ tự Part từng video."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        vids = services.list_videos(self.state.project_id)
        total = sum(self._export_video(v["id"]) for v in vids)
        if total:
            self.status.setText(
                f"Đang xuất {total} clip của CẢ KÊNH (theo thứ tự Part từng "
                "video, chạy song song)...")
        else:
            QMessageBox.information(self, "Chưa có clip",
                                   "Kênh chưa có clip nào. Bấm 'Tất cả' để tạo trước.")

    def _open_dir(self):
        # mở KHO 'Đã xuất' (theo thư mục gốc hiện tại). Nếu đang chọn video ->
        # mở thẳng thư mục con của video đó.
        base = self._export_root()
        target = base
        if self.state.video_id:
            vrow = db.query_one("SELECT src_path FROM videos WHERE id=?",
                                (self.state.video_id,))
            if vrow and vrow["src_path"]:
                import re
                stem = re.sub(r'[<>:"/\\|?*]', "_", Path(vrow["src_path"]).stem)
                sub = base / stem
                if sub.is_dir():
                    target = sub
        try:
            os.startfile(str(target))  # noqa: S606
        except Exception:  # noqa: BLE001
            pass

    def _open_file(self, p):
        if p and os.path.isfile(p):
            os.startfile(p)  # noqa: S606
