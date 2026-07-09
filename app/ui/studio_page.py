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
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from app import services
from app.core.ffmpeg_utils import extract_frame
from app.database import db
from app.ui.editor import EditorDialog, render_overlay_png
from app.ui.state import AppState
from app.ui.theme import (
    ACCENT, BASE, BORDER, DANGER, MUTED, SUCCESS, SURFACE, TEXT, WARN,
)

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
                  "cap_hook": False, "cap_hook_dur": 6.0,   # HOOK opt-in (mặc định TẮT)
                  "hook_nx": 0.5, "hook_ny": 0.10, "hook_size": 0.072}

# MẪU PRO sẵn (giống ViralCut): nền đen gọn, HOOK giật tít đầu clip, phụ đề vàng
# nhảy karaoke dưới, font Anton đậm, KHÔNG lớp chữ tĩnh (Hook lo phần tiêu đề).
PRO_LAYOUT = {"video_rect": (0.5, 0.5, 1.0), "bg": "black", "layers": [],
              "captions": True, "cap_font": "Anton", "cap_size": 0.055,
              "cap_color": "", "cap_ny": 0.82, "cap_preset": "Vàng nhảy (TikTok)",
              "cap_delay": 0.12, "cap_hook": True, "cap_hook_dur": 6.0,
              "hook_nx": 0.5, "hook_ny": 0.10, "hook_size": 0.072}
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
    dl_one = pyqtSignal(str, str, str)  # 1 video TRONG LOẠT xong (path, lỗi, url)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.layout_tpl = copy.deepcopy(DEFAULT_LAYOUT)
        self._thumb_busy = False
        self._warned_no_ai = False    # popup "chưa có key Groq" 1 lần/phiên (luồng tải)
        self._pending_export = {}     # job_id phân tích -> video_id (chờ tự xuất)
        self._hashtag_cache = {}      # video_id -> " #a #b" (sinh 1 lần/video)
        self._settings = QSettings("AIContentStudio", "studio")
        self.thumbs_ready.connect(self._rebuild_rows)
        self.setAcceptDrops(True)        # KÉO-THẢ video vào app

        # nội dung GIÃN theo cửa sổ (màn rộng dùng đủ bề ngang, không bó giữa)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        outer.addWidget(content, 1)
        root = QVBoxLayout(content)
        root.setContentsMargins(8, 16, 8, 12)
        root.setSpacing(14)

        # ===== THẺ điều khiển (gom các nút vào 1 khối có viền cho dễ nhận biết) =====
        panel = QWidget(); panel.setObjectName("ctlPanel")
        panel.setStyleSheet(f"#ctlPanel{{background:{BASE}; border:1px solid {BORDER};"
                            f"border-radius:12px;}}")
        plw = QVBoxLayout(panel); plw.setContentsMargins(16, 8, 16, 14); plw.setSpacing(8)
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
        self.lib_btn = QPushButton("Kho video"); self.lib_btn.setProperty("ghost", True)
        self.lib_btn.clicked.connect(self._pick_lib_root); srcrow.addWidget(self.lib_btn)
        self._update_lib_tooltip()   # tooltip hiện ĐƯỜNG DẪN kho đang dùng
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
        plw.addWidget(self._sec_hdr("Nguồn video", num=1))
        plw.addLayout(srcrow)

        # ===== Hàng tải từ LINK YOUTUBE thẳng vào kênh =====
        ytrow = QHBoxLayout(); ytrow.setSpacing(8)
        ytrow.addWidget(self._tag("Link YT"))
        self.yt_url = QLineEdit()
        self.yt_url.setPlaceholderText("Dán link YouTube vào đây để tải thẳng về kênh...")
        ytrow.addWidget(self.yt_url, 1)
        self.yt_btn = QPushButton("Tải về"); self.yt_btn.setProperty("primary", True)
        self.yt_btn.setMinimumHeight(40); self.yt_btn.setMinimumWidth(110)
        self.yt_btn.setToolTip("Tải video 1080p từ link vào kênh đang chọn (yt-dlp).")
        self.yt_btn.clicked.connect(self._download_youtube)
        ytrow.addWidget(self.yt_btn)
        self.yt_many_btn = QPushButton("Tải nhiều"); self.yt_many_btn.setProperty("ghost", True)
        self.yt_many_btn.setToolTip("Dán NHIỀU link (mỗi link 1 dòng) -> tải hết + "
                                    "tự phân tích/cắt từng cái (bật 'tự xuất' thì xuất luôn).")
        self.yt_many_btn.clicked.connect(self._download_many)
        ytrow.addWidget(self.yt_many_btn)
        self.ck_btn = QPushButton("Cookie"); self.ck_btn.setProperty("ghost", True)
        self.ck_btn.clicked.connect(self._on_cookie_btn)
        ytrow.addWidget(self.ck_btn)
        self._refresh_cookie_btn_tip()
        plw.addLayout(ytrow)
        self.dl_done.connect(self._on_dl_done)
        self.dl_progress.connect(lambda m: self.status.setText(m))
        self.dl_one.connect(self._on_batch_one)

        # ===== Hàng 2: HÀNH ĐỘNG tạo clip + công tắc tự xuất =====
        plw.addWidget(self._sec_hdr("Tạo clip", num=2))
        actrow = QHBoxLayout(); actrow.setSpacing(8)
        self.auto_btn = QPushButton("Tạo clip")
        self.auto_btn.setProperty("primary", True)
        self.auto_btn.setMinimumHeight(40); self.auto_btn.setMinimumWidth(160)
        self.auto_btn.setToolTip("Phân tích (nếu chưa) + AI tự tìm và cắt các đoạn "
                                 "hay nhất của VIDEO đang chọn.")
        self.auto_btn.clicked.connect(self._auto); actrow.addWidget(self.auto_btn)
        self.auto_all_btn = QPushButton("Tất cả video")
        self.auto_all_btn.setProperty("ghost", True); self.auto_all_btn.setMinimumHeight(32)
        self.auto_all_btn.setToolTip("Đưa MỌI video chưa làm trong kênh vào hàng đợi.")
        self.auto_all_btn.clicked.connect(self._auto_all); actrow.addWidget(self.auto_all_btn)
        self.pick_btn = QPushButton("Chọn nhiều")
        self.pick_btn.setProperty("ghost", True); self.pick_btn.setMinimumHeight(32)
        self.pick_btn.setToolTip("Tích chọn nhiều video cụ thể để tạo clip cùng lúc.")
        self.pick_btn.clicked.connect(self._pick_videos); actrow.addWidget(self.pick_btn)
        self.mixed_btn = QPushButton("Mixed-Cut")
        self.mixed_btn.setProperty("ghost", True); self.mixed_btn.setMinimumHeight(32)
        self.mixed_btn.setToolTip(
            "Ghép các KHOẢNH KHẮC hay nhất KHẮP video thành 1 clip dài (~1-2 "
            "phút) — kiểu 'best moments'. Khác 'Tạo clip' (mỗi clip 1 câu chuyện).")
        self.mixed_btn.clicked.connect(self._auto_mixed)
        actrow.addWidget(self.mixed_btn)
        # 🎙 REUP THUYẾT MINH: AI viết kịch bản thuyết minh xen kẽ tiếng gốc
        self.recap_btn = QPushButton("🎙 Reup thuyết minh")
        self.recap_btn.setProperty("ghost", True); self.recap_btn.setMinimumHeight(32)
        self.recap_btn.setToolTip(
            "AI hiểu nội dung video rồi TỰ SÁNG TÁC lời KỂ CHUYỆN kiểu kênh "
            "recap: đoạn GIỮ TIẾNG GỐC (khoảnh khắc đắt) xen kẽ đoạn GIỌNG "
            "AI kể (video tắt tiếng) — kể bằng ĐÚNG ngôn ngữ video. Giọng "
            "kể/tỉ lệ/nhịp chỉnh ở nút ⚙ bên cạnh.")
        self.recap_btn.clicked.connect(self._auto_recap)
        actrow.addWidget(self.recap_btn)
        from app.ai.recap import STYLES as _RECAP_STYLES
        self.recap_style = QComboBox()
        self.recap_style.setToolTip("Phong cách thuyết minh cho nút 🎙 Reup.")
        for key, (label, _hint) in _RECAP_STYLES.items():
            self.recap_style.addItem(label, key)
        _rs = self._settings.value("recap_style", "story") or "story"
        self.recap_style.setCurrentIndex(max(0, self.recap_style.findData(_rs)))
        self.recap_style.currentIndexChanged.connect(
            lambda _i: self._settings.setValue(
                "recap_style", self.recap_style.currentData() or "story"))
        actrow.addWidget(self.recap_style)
        # ⚙ CÀI ĐẶT RIÊNG cho Reup thuyết minh: giọng kể / phong cách /
        # tỉ lệ AI kể / nhịp kể (QSettings toàn cục — không dính vào mẫu)
        self.recap_cfg_btn = QPushButton("⚙")
        self.recap_cfg_btn.setProperty("ghost", True)
        self.recap_cfg_btn.setFixedWidth(34)
        self.recap_cfg_btn.setMinimumHeight(32)
        self.recap_cfg_btn.setToolTip(
            "Cài đặt Reup thuyết minh: giọng kể, phong cách, tỉ lệ AI kể, "
            "nhịp kể.")
        self.recap_cfg_btn.clicked.connect(self._recap_settings)
        actrow.addWidget(self.recap_cfg_btn)
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

        # ===== Hàng 3: MẪU + XUẤT (cấu hình + nút xuất chính) =====
        plw.addWidget(self._sec_hdr("Mẫu & Xuất", num=3))
        cfgrow = QHBoxLayout(); cfgrow.setSpacing(8)
        cfgrow.addWidget(self._tag("Mẫu"))
        self.tmpl_box = QComboBox(); self.tmpl_box.setMinimumWidth(190)
        self.tmpl_box.setToolTip("Mẫu khung/chữ áp khi xuất. Nhớ mẫu đã chọn lần sau.")
        self.tmpl_box.currentIndexChanged.connect(self._on_template_pick)
        cfgrow.addWidget(self.tmpl_box)
        self.tmpl_edit_btn = QPushButton("Chỉnh mẫu")
        self.tmpl_edit_btn.setProperty("ghost", True)
        self.tmpl_edit_btn.setToolTip(
            "Sửa mẫu đang chọn: khung video, nền, chữ, phụ đề, logo, nhạc nền...")
        self.tmpl_edit_btn.clicked.connect(self._edit_template)
        cfgrow.addWidget(self.tmpl_edit_btn)
        cut = QPushButton("Tùy chỉnh cắt"); cut.setProperty("ghost", True)
        cut.setToolTip("Ngôn ngữ, độ dài Min/Max clip, mục đích & phong cách cắt.")
        cut.clicked.connect(self._cut_settings); cfgrow.addWidget(cut)
        aiset = QPushButton("Cài đặt AI"); aiset.setProperty("ghost", True)
        aiset.setToolTip("Chọn AI máy/mây + key; Nghe-chép Local/Groq.")
        aiset.clicked.connect(self._ai_settings); cfgrow.addWidget(aiset)
        self.ai_status = QLabel("")
        self.ai_status.setToolTip("AI đang dùng. Bấm vào nhãn này để mở Cài đặt AI.")
        # nhãn CLICK ĐƯỢC: đang đỏ "chưa có key!" -> bấm là mở luôn Cài đặt AI
        self.ai_status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_status.mousePressEvent = lambda _e: self._ai_settings()
        cfgrow.addWidget(self.ai_status)
        cfgrow.addStretch(1)
        self.dl_chan = QPushButton("Xuất cả kênh")
        self.dl_chan.setProperty("ghost", True)
        self.dl_chan.setToolTip("Xuất clip của MỌI video trong kênh, 1 phát "
                                "(đúng thứ tự Part từng video).")
        self.dl_chan.clicked.connect(self._export_all_channel)
        cfgrow.addWidget(self.dl_chan)
        self.dl_all = QPushButton("Xuất video này")
        self.dl_all.setProperty("primary", True)
        self.dl_all.setMinimumHeight(40); self.dl_all.setMinimumWidth(150)
        self.dl_all.setToolTip("Xuất clip của VIDEO đang chọn.")
        self.dl_all.clicked.connect(self._export_all)
        cfgrow.addWidget(self.dl_all)
        plw.addLayout(cfgrow)
        self._update_ai_status()

        # ===== Hàng kết quả: đếm clip + mở thư mục =====
        headrow = QHBoxLayout(); headrow.setSpacing(8)
        self.count_lbl = QLabel("Chưa có clip")
        self.count_lbl.setStyleSheet("font-size:16px; font-weight:600;")
        headrow.addWidget(self.count_lbl)
        headrow.addStretch(1)
        op = QPushButton("Mở thư mục"); op.setProperty("ghost", True)
        op.setToolTip("Mở thư mục 'Đã xuất' chứa clip của kênh/video đang chọn "
                      "trong Kho video.")
        op.clicked.connect(self._open_dir); headrow.addWidget(op)
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
        self.timer.timeout.connect(self._poll_done)     # job video đang chọn XONG -> báo ✓
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

    def _sec_hdr(self, text, color=ACCENT, num=None):
        """Tiêu đề BƯỚC: số tròn màu accent + chữ to đậm (phân cấp rõ ràng)."""
        w = QWidget(); w.setStyleSheet("background:transparent;")
        r = QHBoxLayout(w)
        r.setContentsMargins(0, 8, 0, 0); r.setSpacing(9)
        if num is not None:
            dot = QLabel(str(num)); dot.setFixedSize(22, 22)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setStyleSheet(f"background:{ACCENT}; color:white; border-radius:11px;"
                              "font-size:12px; font-weight:800;")
            lab = QLabel(text)
            lab.setStyleSheet(f"color:{TEXT}; font-size:15px; font-weight:700;")
        else:
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

    # ---- CHẶN SỚM khi chưa có cách chép lời (không key Groq, không whisper máy) ----
    _NO_AI_MSG = ("Chưa có cách chép lời. Bấm nút 'Cài đặt AI' dán key Groq "
                  "(miễn phí, console.groq.com/keys) rồi thử lại.")

    def _ai_ready(self) -> bool:
        """Có cách chép lời chưa? Kiểm được thì trả đúng; kiểm lỗi thì cho
        chạy — job phân tích sẽ tự báo lỗi rõ (không chặn oan)."""
        try:
            from app.core import transcribe
            return bool(transcribe.provider_ready())
        except Exception:  # noqa: BLE001
            return True

    def _require_ai(self) -> bool:
        """Nút bấm TAY (Tạo clip/Tất cả/Chọn nhiều/Mixed-Cut): chưa sẵn sàng
        -> popup hướng dẫn ngay, KHÔNG enqueue (đỡ job chạy rồi mới báo lỗi)."""
        if self._ai_ready():
            return True
        QMessageBox.warning(self, "Chưa có cách chép lời", self._NO_AI_MSG)
        return False

    def _require_ai_after_dl(self) -> bool:
        """Luồng TỰ chạy sau khi tải link: popup chỉ 1 LẦN ĐẦU trong phiên
        (tải nhiều link mà popup dồn dập thì phiền), các lần sau báo ⚠ status."""
        if self._ai_ready():
            return True
        if not self._warned_no_ai:
            self._warned_no_ai = True
            QMessageBox.warning(self, "Chưa có cách chép lời", self._NO_AI_MSG)
        self.status.setText("⚠ Video đã tải về nhưng CHƯA phân tích — "
                            + self._NO_AI_MSG)
        return False

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
            services.delete_project(int(pid), self.state.pool)
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

        # ----- TRỎ FILE KEY (mỗi dòng 1 key) — cho HÀNG TRĂM key -----
        # Trạng thái đường dẫn file giữ trong 1 ô [list] để đóng closure sửa được.
        gfile = [settings.GROQ_KEYS_FILE or ""]
        gnote = QLabel("Dán vài key vào ô, hoặc trỏ file .txt cho HÀNG TRĂM key. "
                       "App gộp cả hai.")
        gnote.setWordWrap(True)
        gnote.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        lay.addWidget(gnote)
        gfrow = QHBoxLayout()
        gfbtn = QPushButton("📄 Chọn file key (mỗi dòng 1 key)")
        gfbtn.setProperty("ghost", True)
        gfclear = QPushButton("Bỏ"); gfclear.setProperty("ghost", True)
        gfrow.addWidget(gfbtn); gfrow.addWidget(gfclear); gfrow.addStretch(1)
        lay.addLayout(gfrow)
        gflbl = QLabel("")
        gflbl.setWordWrap(True)
        gflbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gflbl.setStyleSheet(f"color:{TEXT}; font-size:11px;")
        lay.addWidget(gflbl)

        def _refresh_gfile():
            p = gfile[0]
            if p:
                n = len(Settings._read_keys_file(p))
                gflbl.setText(f"📄 {p}  ·  {n} key trong file")
                gfclear.setEnabled(True)
            else:
                gflbl.setText("(chưa trỏ file — chỉ dùng key ở ô dán)")
                gfclear.setEnabled(False)

        def pick_gfile():
            start = gfile[0] or str(getattr(settings, "DATA_DIR", "") or "")
            fn, _ = QFileDialog.getOpenFileName(
                dlg, "Chọn file key Groq (.txt — mỗi dòng 1 key)", start,
                "Text (*.txt);;Tất cả (*.*)")
            if fn:
                gfile[0] = fn
                _refresh_gfile()

        def clear_gfile():
            gfile[0] = ""
            _refresh_gfile()

        gfbtn.clicked.connect(pick_gfile)
        gfclear.clicked.connect(clear_gfile)
        _refresh_gfile()

        # ----- NÚT "KIỂM TRA TẤT CẢ KEY GROQ" (sống/hết hạn/sai) -----
        # Chạy THREAD NỀN + ThreadPool(8): test từng key bằng GET /models
        # (KHÔNG tốn token). Tiến độ + tổng kết bắn về qua QTimer poll (không
        # chặn UI). Gộp key ô dán + file để kiểm tra đúng tập đang dùng.
        gckrow = QHBoxLayout()
        gckbtn = QPushButton("Kiểm tra tất cả key Groq")
        gckbtn.setProperty("ghost", True)
        gckbtn.setToolTip("Test từng key sống/hết hạn/sai bằng call rẻ (không "
                          "tốn token). Chạy song song, có tiến độ.")
        gckrow.addWidget(gckbtn); gckrow.addStretch(1)
        lay.addLayout(gckrow)
        gckstat = QLabel("")
        gckstat.setObjectName("groq_check_label")
        gckstat.setWordWrap(True)
        gckstat.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gckstat.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        lay.addWidget(gckstat)
        # nút xoá key chết khỏi ô dán (chỉ hiện khi có key 401)
        gckdel = QPushButton("Xoá key chết khỏi ô dán")
        gckdel.setProperty("ghost", True)
        gckdel.setVisible(False)
        lay.addWidget(gckdel)

        def _keys_to_check():
            # gộp ô dán + file (dedup giữ thứ tự) — giống config.groq_keys()
            pasted = [k.strip() for k in gkeys.toPlainText()
                      .replace(",", "\n").splitlines() if k.strip()]
            from_file = Settings._read_keys_file(gfile[0])
            out, seen = [], set()
            for k in pasted + from_file:
                if k and k not in seen:
                    seen.add(k); out.append(k)
            return out

        def check_all_groq():
            keys = _keys_to_check()
            if not keys:
                gckstat.setText("Chưa có key Groq nào — dán key hoặc trỏ file "
                                "rồi bấm lại.")
                return
            gckbtn.setEnabled(False)
            gckdel.setVisible(False)
            # box chia sẻ giữa thread nền và poll (thread-safe đủ cho dict/list)
            box = {"done": 0, "total": len(keys), "result": None, "err": None}
            gckstat.setText(f"Đang kiểm tra 0/{box['total']}...")

            def prog(done, total):
                box["done"] = done

            def bg():
                try:
                    box["result"] = llm.check_groq_keys(
                        keys, progress=prog, max_workers=8)
                except Exception as e:  # noqa: BLE001
                    box["err"] = str(e)

            threading.Thread(target=bg, daemon=True).start()
            gcktimer = QTimer(dlg)

            def poll():
                if box["result"] is None and box["err"] is None:
                    gckstat.setText(f"Đang kiểm tra {box['done']}/"
                                    f"{box['total']}...")
                    return
                gcktimer.stop()
                gckbtn.setEnabled(True)
                if box["err"] is not None:
                    gckstat.setText(f"⚠ Lỗi kiểm tra: {box['err']}")
                    return
                r = box["result"]
                c = r["counts"]
                summary = (f"✅ Sống: {c['ok']} · ⏳ Hết hạn mức: {c['limited']} "
                           f"· ❌ Sai: {c['invalid']} · ⚠ Lỗi mạng: {c['error']}")
                bad = r["invalid"]
                if bad:
                    masked = ", ".join("…" + k[-4:] for k in bad[:20])
                    more = f" (+{len(bad) - 20} nữa)" if len(bad) > 20 else ""
                    summary += f"\nKey sai: {masked}{more}"
                    gckdel.setVisible(True)
                    gckdel._bad = bad  # nhớ để xoá khi bấm
                gckstat.setText(summary)

            gcktimer.timeout.connect(poll)
            gcktimer.start(250)

        gckbtn.clicked.connect(check_all_groq)

        def del_dead_keys():
            bad = set(getattr(gckdel, "_bad", []) or [])
            if not bad:
                return
            kept = [k.strip() for k in gkeys.toPlainText()
                    .replace(",", "\n").splitlines()
                    if k.strip() and k.strip() not in bad]
            gkeys.setPlainText("\n".join(kept))
            gckdel.setVisible(False)
            gckstat.setText(f"Đã xoá {len(bad)} key sai khỏi ô dán. Bấm Lưu để "
                            "áp. (Key sai trong FILE phải sửa trong file .txt.)")

        gckdel.clicked.connect(del_dead_keys)

        # ----- ElevenLabs TTS (giọng lồng tiếng/thuyết minh CAO CẤP) -----
        # Tùy chọn — user tự cắm key. Có key -> nhóm giọng 🎧 ElevenLabs mở
        # khóa trong Cài đặt Reup + combo giọng lồng tiếng. Free 10k ký tự/
        # tháng, hết hạn mức tự lùi về edge-tts.
        lay.addWidget(QLabel("ElevenLabs API key — giọng lồng tiếng/thuyết minh "
                             "CAO CẤP (tùy chọn, nhiều key mỗi dòng 1):"))
        elkeys = QPlainTextEdit((settings.ELEVENLABS_API_KEYS
                                 or settings.ELEVENLABS_API_KEY or ""))
        elkeys.setPlaceholderText("Để TRỐNG nếu chỉ dùng edge-tts (miễn phí). "
                                  "Dán key từ elevenlabs.io -> mở khóa giọng "
                                  "🎧 Adam...")
        elkeys.setToolTip(
            "Giọng ElevenLabs chất lượng cao nhất cho Reup thuyết minh + lồng "
            "tiếng.\nFree 10.000 ký tự/tháng — hết hạn mức app TỰ lùi về giọng "
            "edge-tts.\nElevenLabs không chỉnh được nhịp/tông (bỏ qua 2 mục "
            "đó); tốc độ vẫn khớp khung tự động.")
        elkeys.setFixedHeight(50); lay.addWidget(elkeys)

        # Nút "Kiểm tra" credit ElevenLabs: gọi GET /user/subscription cho
        # TỪNG key ở THREAD NỀN -> hiện "Key …abc: còn 8.230/10.000 ký tự
        # (free, reset 15/07)"; key lỗi hiện "SAI KEY"/lý do nguyên văn.
        elrow = QHBoxLayout()
        elbtn = QPushButton("Kiểm tra credit ElevenLabs")
        elbtn.setProperty("ghost", True)
        elbtn.setToolTip("Xem từng key còn bao nhiêu ký tự TTS (gói, ngày "
                         "reset). Key sai/bị chặn sẽ báo rõ lý do.")
        elrow.addWidget(elbtn); elrow.addStretch(1)
        lay.addLayout(elrow)
        elstat = QLabel("")
        elstat.setObjectName("eleven_credit_label")
        elstat.setWordWrap(True)
        elstat.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        elstat.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        lay.addWidget(elstat)

        def check_eleven():
            keys = [k.strip() for k in elkeys.toPlainText()
                    .replace(",", "\n").splitlines() if k.strip()]
            if not keys:
                elstat.setText("Chưa nhập key ElevenLabs — dán key ở ô trên "
                               "rồi bấm lại.")
                return
            elbtn.setEnabled(False)
            elstat.setText(f"Đang kiểm tra credit {len(keys)} key...")
            res: list = []

            def bg():
                from app.core import dubbing
                lines = []
                for k in keys:
                    try:
                        lines.append(dubbing.eleven_key_status_line(k))
                    except Exception as e:  # noqa: BLE001 — không sập dialog
                        lines.append(f"⚠️ Key …{k[-6:]}: lỗi {e}")
                res.append("\n".join(lines))

            threading.Thread(target=bg, daemon=True).start()
            eltimer = QTimer(dlg)

            def poll():
                if not res:
                    return
                eltimer.stop()
                elbtn.setEnabled(True)
                elstat.setText(res[0])

            eltimer.timeout.connect(poll)
            eltimer.start(200)

        elbtn.clicked.connect(check_eleven)

        # ----- Trạng thái key (thời gian thực) — chỉ đọc SỔ trong RAM, -----
        # ----- KHÔNG gọi mạng; QTimer 2s cập nhật, dừng khi đóng dialog. -----
        lay.addWidget(QLabel("Trạng thái key (thời gian thực):"))
        kstat = QLabel("")
        kstat.setObjectName("key_status_label")
        kstat.setWordWrap(True)
        kstat.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        kstat.setStyleSheet(f"color:{TEXT}; background:{SURFACE}; border:1px solid "
                            f"{BORDER}; border-radius:8px; padding:8px 10px; "
                            "font-size:12px; line-height:1.5;")
        lay.addWidget(kstat)

        def _fmt_wait(sec: float) -> str:
            s = int(round(sec))
            h, s = divmod(s, 3600)
            m, s = divmod(s, 60)
            if h:
                return f"{h}h{m:02d}m"
            if m:
                return f"{m}m{s:02d}s"
            return f"{s}s"

        def refresh_keys():
            lines = []
            try:
                for st in llm.key_status("groq"):
                    if st["state"] == "invalid":
                        lines.append(f"🔑 {st['key_masked']} — SAI KEY (kiểm tra "
                                     "lại: xóa dấu cách thừa / dán key đúng)")
                    elif st["state"] == "limited":
                        lines.append(f"⛔ {st['key_masked']} — hết lượt, thử lại "
                                     f"sau {_fmt_wait(st['wait_left'])}")
                    elif st["in_use"]:
                        lines.append(f"🔵 {st['key_masked']} — ĐANG DÙNG · đã gọi "
                                     f"{st['calls']} lần")
                    else:
                        lines.append(f"🟢 {st['key_masked']} — sẵn sàng · đã gọi "
                                     f"{st['calls']} lần")
                # key vừa DÁN nhưng chưa lưu -> nhắc bấm Lưu (không có trong sổ)
                saved = set(settings.llm_keys_for("groq"))
                typed = [k.strip() for k in gkeys.toPlainText()
                         .replace(",", "\n").splitlines() if k.strip()]
                for k in typed:
                    if k not in saved:
                        lines.append(f"⚪ …{k[-6:]} — (bấm Lưu để áp)")
            except Exception as e:  # noqa: BLE001 - trạng thái chỉ để xem, không sập dialog
                lines = [f"(không đọc được trạng thái: {e})"]
            kstat.setText("\n".join(lines) or "Chưa có key Groq nào — dán key ở "
                                              "ô trên rồi bấm Lưu.")

        ktimer = QTimer(dlg)
        ktimer.setObjectName("key_status_timer")
        ktimer.timeout.connect(refresh_keys)
        ktimer.start(2000)
        dlg.finished.connect(ktimer.stop)     # đóng dialog -> timer dừng
        refresh_keys()

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
            Settings.GROQ_KEYS_FILE = gfile[0]
            Settings.ELEVENLABS_API_KEYS = elkeys.toPlainText().strip()

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
            # Gọi LLM ở THREAD NỀN: gọi đồng bộ trên UI thread sẽ treo toàn bộ
            # app tới 2 phút nếu mạng chậm/timeout.
            tb.setEnabled(False)
            res: list = []

            def bg():
                try:
                    r = llm.complete_text("Trả lời đúng 1 từ: OK", provider=prov)
                    res.append(("ok", r))
                except Exception as e:  # noqa: BLE001
                    res.append(("err", str(e)))

            threading.Thread(target=bg, daemon=True).start()
            from PyQt6.QtCore import QTimer
            timer = QTimer(dlg)

            def poll():
                if not res:
                    return
                timer.stop()
                tb.setEnabled(True)
                kind, val = res[0]
                if kind == "ok":
                    name = {"gemini": "Gemini (mây)", "groq": "Groq (mây)",
                            "ollama": "Ollama (máy)"}.get(prov, prov)
                    set_note("ok", f"AI ĐANG HOẠT ĐỘNG — {name} trả lời: "
                                   f"“{val.strip()[:30]}”. Bấm Lưu để dùng.")
                else:
                    set_note("err", "KHÔNG KẾT NỐI ĐƯỢC — " + friendly(val))

            timer.timeout.connect(poll)
            timer.start(200)

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
                        "GROQ_API_KEYS": gkeys.toPlainText().strip(),
                        "GROQ_KEYS_FILE": gfile[0],
                        "ELEVENLABS_API_KEYS": elkeys.toPlainText().strip()})
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

    def _lib_sub(self, name):
        """Thư mục con trong kho. Kho trỏ ổ đã rút (USB/ổ mạng) -> mkdir nổ
        OSError làm SẬP app khi bấm nút thường — lùi về kho mặc định + báo."""
        d = self._lib_root() / name
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            from config import DATA_DIR
            d = DATA_DIR / "KhoVideo" / name
            d.mkdir(parents=True, exist_ok=True)
            self.status.setText(
                "⚠ Kho video đã chọn không truy cập được (ổ đã rút?) — "
                "tạm dùng kho mặc định. Chọn lại ở nút 'Kho video'.")
        return d

    def _dl_dir(self):
        return self._lib_sub("Đã tải")

    def _export_root(self):
        return self._lib_sub("Đã xuất")

    def _update_lib_tooltip(self):
        """Tooltip nút 'Kho video' luôn hiện ĐƯỜNG DẪN đang dùng — trả lời câu
        'app đang lưu ở đâu?' mà không cần bấm gì."""
        root = self._lib_root()
        self.lib_btn.setToolTip(
            "Đổi thư mục GỐC lưu mọi thứ.\n"
            f"Đang lưu tại: {root}\n"
            f"• Video tải về: {root / 'Đã tải'}\n"
            f"• Clip xuất ra: {root / 'Đã xuất'}\\<Kênh>\\<Video>")

    def _pick_lib_root(self):
        """Chọn THƯ MỤC GỐC chung (chứa 'Đã tải' và 'Đã xuất')."""
        cur = str(self._lib_root())
        d = QFileDialog.getExistingDirectory(
            self, "Chọn KHO VIDEO gốc (sẽ tự tạo 'Đã tải' và 'Đã xuất' bên trong)",
            cur)
        if d:
            self._settings.setValue("lib_root", d)
            self._update_lib_tooltip()
            self.status.setText(f"Kho video: {d}  →  Đã tải / Đã xuất nằm trong đây")
            # XÁC NHẬN RÕ nơi lưu mới — user từng không biết app lưu ở đâu
            QMessageBox.information(
                self, "Đã đổi Kho video",
                f"Từ giờ mọi thứ lưu tại:\n{d}\n\n"
                f"• Video tải về:  {Path(d) / 'Đã tải'}\n"
                f"• Clip xuất ra:  {Path(d) / 'Đã xuất'}\\<Kênh>\\<Video>\n\n"
                "File cũ ở kho trước KHÔNG tự chuyển sang.")

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

    def _video_status_marks(self) -> dict:
        """Đuôi trạng thái cho MỖI video trong combo — 2 query GỘP cho cả kênh
        (không query từng video kẻo chậm khi nhiều video).
        Ưu tiên: có clip -> '✂ N clip'; đang có job chạy -> '⏳ đang xử lý'."""
        marks = {}
        if not self.state.project_id:
            return marks
        try:
            for r in db.query(
                    "SELECT c.video_id AS vid, COUNT(*) AS n FROM clips c "
                    "JOIN videos v ON v.id = c.video_id "
                    "WHERE v.project_id=? GROUP BY c.video_id",
                    (self.state.project_id,)):
                marks[r["vid"]] = f'  ✂ {r["n"]} clip'
            for r in db.query(
                    "SELECT DISTINCT video_id AS vid FROM jobs "
                    "WHERE project_id=? AND video_id IS NOT NULL "
                    "AND status IN ('pending','running')",
                    (self.state.project_id,)):
                if r["vid"] not in marks:
                    marks[r["vid"]] = "  ⏳ đang xử lý"
        except Exception:  # noqa: BLE001 - nhãn trạng thái lỗi không được sập app
            pass
        return marks

    def _video_busy(self, vid) -> bool:
        """Video này ĐANG có job chạy/chờ (phân tích/cắt/xuất)? 1 query nhẹ."""
        if not vid:
            return False
        try:
            return bool(db.query_one(
                "SELECT 1 FROM jobs WHERE video_id=? "
                "AND status IN ('pending','running') LIMIT 1", (vid,)))
        except Exception:  # noqa: BLE001
            return False

    def _reload_videos(self, select_id=None):
        """Nạp lại danh sách video. GIỮ NGUYÊN video đang chọn (nếu còn) —
        nếu không, mỗi lần 1 video trong loạt tải xong sẽ nhảy về video đầu,
        mất chỗ user đang làm việc. select_id: ép chọn video này (vd vừa tải)."""
        cur = select_id if select_id is not None else self.vid.currentData()
        self.vid.blockSignals(True); self.vid.clear()
        if self.state.project_id:
            marks = self._video_status_marks()   # trạng thái TỪNG video (query gộp)
            for v in services.list_videos(self.state.project_id):
                mark = marks.get(v["id"], "  · chưa tạo clip")
                self.vid.addItem(f'{Path(v["src_path"]).name}{mark}', v["id"])
        if cur is not None:
            i = self.vid.findData(cur)
            if i >= 0:
                self.vid.setCurrentIndex(i)
        self.vid.blockSignals(False)
        if self.vid.count():
            self._on_vid(self.vid.currentIndex())
        else:
            self.state.video_id = None
            self._refresh_clips(force=True)
        self._refresh_cookie_btn_tip()

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
        """Import danh sách file video vào kênh đang chọn (nút + kéo-thả).

        CHẠY NỀN: import_video = ffprobe + hash 2MB MỖI file — thêm nhiều file
        (nhất là trên ổ mạng/OneDrive) trên UI thread làm đơ app. Thread nền
        import lần lượt, status báo 'Đang nhập video i/n...', xong mới
        _reload_videos + báo lỗi gộp (giữ nguyên cách gom lỗi OSError cũ)."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh",
                                   "Tạo/chọn kênh trước khi thêm video.")
            return
        vids = [p for p in paths
                if os.path.isfile(p) and p.lower().endswith(self._VIDEO_EXT)]
        if not vids:
            if paths:
                self.status.setText("Không có file video hợp lệ (mp4/mov/mkv...).")
            return
        if getattr(self, "_import_busy", False):
            self.status.setText("Đang nhập loạt video trước — chờ xong rồi "
                                "thêm tiếp nhé.")
            return
        self._import_busy = True
        pid = self.state.project_id      # NHỚ kênh lúc bấm (user có thể đổi kênh)
        n = len(vids)
        self.status.setText(f"Đang nhập video 1/{n}...")
        res = {"ok": 0, "fails": [], "done": 0, "finished": False}

        def bg():
            for f in vids:
                # file OneDrive online-only/USB rút/đang khóa -> OSError; lỗi
                # khác cũng phải bắt: thread nền chết im lặng sẽ kẹt _import_busy
                try:
                    services.import_video(pid, f)
                    res["ok"] += 1
                except Exception as e:  # noqa: BLE001
                    res["fails"].append(f"{Path(f).name}: {e}")
                res["done"] += 1
            res["finished"] = True

        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not res["finished"]:
                if res["done"] < n:
                    self.status.setText(f"Đang nhập video {res['done'] + 1}/{n}...")
                return
            timer.stop()
            self._import_busy = False
            ok, fails = res["ok"], res["fails"]
            if ok:
                self._reload_videos()
                self.status.setText(f"Đã thêm {ok} video vào kênh.")
            if fails:
                QMessageBox.warning(
                    self, "Một số file không đọc được",
                    "Không import được:\n" + "\n".join(fails[:8])
                    + ("\n…" if len(fails) > 8 else ""))

        timer.timeout.connect(poll)
        timer.start(150)

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
        """Arg cookie cho yt-dlp: hồ sơ đang chọn > trình duyệt (user chọn rõ)
        > file cũ (bản trước)."""
        st = QSettings("AIContentStudio", "studio")
        name = st.value("yt_cookie_active", "")
        if name:
            p = self._cookie_profile_path(name)
            try:
                if p.exists() and p.stat().st_size > 40:
                    return ["--cookies", str(p)]
            except Exception:  # noqa: BLE001
                pass
        # user CHỦ ĐỘNG chọn lấy từ trình duyệt (đã bỏ hồ sơ) -> ưu tiên trước
        # file cookie cũ, nếu không cookie hết hạn cũ sẽ che mãi nhánh này
        br = st.value("yt_cookie_browser", "")
        if br:
            return ["--cookies-from-browser", str(br)]
        old = self._cookie_file()
        try:
            if old.exists() and old.stat().st_size > 40:
                return ["--cookies", str(old)]
        except Exception:  # noqa: BLE001
            pass
        return []

    # cookie đăng nhập quan trọng — hết 1 trong số này là coi như phải đăng nhập lại
    _COOKIE_KEYS = ("SID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID",
                    "LOGIN_INFO", "__Secure-3PSIDTS")

    @classmethod
    def _cookie_health(cls, path):
        """Đọc file cookie Netscape, xét các cookie đăng nhập quan trọng.

        Trả (state, msg):
          "ok"      — còn hạn (msg = còn ~N ngày theo cookie hết SỚM NHẤT trong
                       nhóm quan trọng, bỏ qua expiry=0/session).
          "expired" — có cookie quan trọng nhưng đã hết hạn.
          "empty"   — chưa có/không đủ cookie đăng nhập.
          "session" — chỉ có cookie quan trọng dạng session (expiry=0) — chết nhanh.
        """
        import time
        keys = cls._COOKIE_KEYS
        found = 0                 # số cookie quan trọng tìm thấy
        session_only = 0          # cookie quan trọng nhưng expiry=0 (session)
        exps = []                 # expiry > 0 của cookie quan trọng
        try:
            p = Path(path)
            if not p.exists():
                return "empty", "Chưa có cookie đăng nhập"
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            return "empty", "Chưa có cookie đăng nhập"

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            # dòng #HttpOnly_ vẫn là cookie hợp lệ; các # khác là comment
            if line.startswith("#") and not line.startswith("#HttpOnly_"):
                continue
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            name = parts[5].strip()
            if name not in keys:
                continue
            found += 1
            try:
                exp = int(float(parts[4].strip()))
            except (ValueError, IndexError):
                exp = 0
            if exp <= 0:
                session_only += 1
            else:
                exps.append(exp)

        if found == 0:
            return "empty", "Chưa có cookie đăng nhập"
        if not exps:                       # chỉ toàn session cookie
            return "session", "Chỉ có cookie tạm (session)"
        now = time.time()
        soonest = min(exps)
        if soonest <= now:
            return "expired", "Cookie đã hết hạn"
        days = int((soonest - now) // 86400)
        return "ok", f"Còn ~{days} ngày"

    def _active_cookie_health(self):
        """Sức khỏe cookie của hồ sơ đang chọn (không có hồ sơ -> empty)."""
        st = QSettings("AIContentStudio", "studio")
        name = st.value("yt_cookie_active", "")
        if not name:
            return "empty", "Chưa có cookie đăng nhập"
        return self._cookie_health(self._cookie_profile_path(name))

    @staticmethod
    def _cookie_health_label(state, msg):
        """(text hiển thị icon, màu theme) cho một trạng thái cookie."""
        if state == "ok":
            return f"🟢 Cookie còn hạn ({msg})", SUCCESS
        if state == "expired":
            return "🔴 Cookie ĐÃ HẾT HẠN — cần dán cookie mới", DANGER
        if state == "session":
            return ("🟡 Chỉ có cookie tạm (đóng trình duyệt là mất) — "
                    "nên export lại"), WARN
        return "⚪ Chưa có cookie đăng nhập", MUTED

    def _cookie_fail_hint(self):
        """Dòng thêm cho popup lỗi tải: chỉ hiện khi cookie đang dùng đã hết
        hạn/chưa có -> nhắc user dán cookie MỚI."""
        state, _msg = self._active_cookie_health()
        if state in ("expired", "empty"):
            return ("\n\n⚠ Cookie hiện tại đã hết hạn/chưa có — hãy dán cookie "
                    "MỚI (xuất từ cửa sổ ẩn danh).")
        return ""

    def _refresh_cookie_btn_tip(self):
        """Tooltip nút Cookie = trạng thái cookie hiện tại (gọi khi mở/tải/lưu)."""
        btn = getattr(self, "ck_btn", None)
        if btn is None:
            return
        state, msg = self._active_cookie_health()
        text, _col = self._cookie_health_label(state, msg)
        btn.setToolTip(
            text + "\nBấm để dán/đổi cookie YouTube (lưu 1 lần dùng mãi).")

    def _on_cookie_btn(self):
        self._refresh_cookie_btn_tip()
        self._youtube_cookie()

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
            "<b>Lấy cookie ĐÚNG CÁCH (theo yt-dlp, cookie sống lâu):</b><br>"
            "1. Cài tiện ích <b>“Get cookies.txt LOCALLY”</b>.<br>"
            "2. Mở <b>cửa sổ ẨN DANH</b> (Ctrl+Shift+N) → đăng nhập "
            "youtube.com → vào <b>youtube.com/robots.txt</b> (chỉ mở đúng 1 "
            "tab ẩn danh này) → Export cookie → <b>ĐÓNG NGAY cửa sổ ẩn danh</b>.<br>"
            "3. Dán/nạp cookie vào ô dưới → <b>Lưu</b>.<br><br>"
            "<b>⚠ Để cookie KHÔNG chết sau 1 lần tải:</b> sau khi lưu, "
            "<b>ĐỪNG mở YouTube bằng tài khoản đó trên trình duyệt nữa</b> — "
            "YouTube xoay cookie liên tục trên tab đang mở, làm cookie trong "
            "app hết hạn ngay. Mỗi tài khoản chỉ dùng ở 1 nơi (app HOẶC trình "
            "duyệt); muốn xem YouTube thì dùng tài khoản/trình duyệt khác.")
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

        # --- CHỈ BÁO TÌNH TRẠNG cookie của hồ sơ đang chọn ---
        health = QLabel(""); health.setWordWrap(True)
        health.setStyleSheet("font-size:13px; font-weight:600;")
        v.addWidget(health)

        def refresh_health():
            name = pcb.currentText().strip()
            if not name:
                state, msg = "empty", ""
            else:
                state, msg = self._cookie_health(self._cookie_profile_path(name))
            text, col = self._cookie_health_label(state, msg)
            health.setStyleSheet(
                f"color:{col}; font-size:13px; font-weight:600;")
            health.setText(text)

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
            refresh_health()

        def on_pick():
            if pcb.currentText():
                load_box(pcb.currentText())
            refresh_health()
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
            txt = box.toPlainText().strip()
            br = bcb.currentText()
            st.setValue("yt_cookie_browser", "" if br == "(không)" else br)
            # Chọn TRÌNH DUYỆT + không dán cookie -> ý user là dùng cookie
            # trình duyệt: phải BỎ hồ sơ active, nếu không _cookie_args luôn
            # ưu tiên hồ sơ cũ (hết hạn) và nhánh trình duyệt không bao giờ chạy.
            if br != "(không)" and not txt:
                st.setValue("yt_cookie_active", "")
                note.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")
                note.setText(f"Sẽ lấy cookie từ trình duyệt '{br}'. "
                             "(Lưu ý: nên ĐÓNG trình duyệt trước khi tải.)")
                dlg.accept()
                return
            name = pcb.currentText().strip()
            if not name:                       # chưa có hồ sơ -> tạo Mặc định
                name = "Mặc định"
                self._cookie_profile_path(name).write_text(
                    "# Netscape HTTP Cookie File\n", encoding="utf-8")
            if txt and "# Netscape HTTP Cookie File" not in txt:
                txt = "# Netscape HTTP Cookie File\n" + txt
            self._cookie_profile_path(name).write_text(
                (txt + "\n") if txt else "# Netscape HTTP Cookie File\n",
                encoding="utf-8")
            st.setValue("yt_cookie_active", name)
            refresh_health()
            self._refresh_cookie_btn_tip()
            note.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")
            note.setText(f"Đã lưu & chọn hồ sơ '{name}'. Giờ bấm Tải lại nhé.")
            dlg.accept()
        sv.clicked.connect(do_save)
        cancel.clicked.connect(dlg.reject)

        refresh_combo()
        dlg.exec()

    # ---- tải video từ link YouTube (yt-dlp) ----
    def _yt_ready(self):
        """Kiểm tra sẵn sàng tải. Trả (exe, dl, ff_dir) hoặc None (kèm cảnh báo)."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return None
        from config import settings, bundled_exe
        exe = bundled_exe("yt-dlp") or shutil.which("yt-dlp")   # ưu tiên bản đóng gói
        if not exe:
            QMessageBox.warning(self, "Thiếu yt-dlp",
                                "Máy chưa có yt-dlp. Cài: pip install yt-dlp")
            return None
        dl = self._dl_dir()                  # KHO chung: <gốc>/Đã tải (giữ mãi)
        ffmpeg = bundled_exe("ffmpeg") or shutil.which("ffmpeg") or settings.FFMPEG_PATH
        ff_dir = os.path.dirname(ffmpeg) if os.path.sep in str(ffmpeg) else ""
        return exe, dl, ff_dir

    def _potoken(self):
        try:
            from app.core import ytdlp_potoken
            return ytdlp_potoken.ensure_running()
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _is_multi_url(u: str) -> bool:
        """Link playlist/kênh (yt-dlp sẽ tải HÀNG LOẠT thay vì 1 video)."""
        import re as _re
        u = u.lower()
        if "watch" in u and "v=" in u:
            return False                     # watch?v=..&list=.. -> --no-playlist lo
        return ("/playlist" in u
                or ("list=" in u and "v=" not in u)
                or bool(_re.search(r"/(channel|c|user)/", u))
                or ("/@" in u))

    def _run_ytdlp(self, url, exe, dl, ff_dir, cookie_args, pot_args, prefix="",
                   extra_args=None):
        """Tải 1 URL (gọi trong thread). Trả (path, err); hiện % qua dl_progress.
        Lỗi HTTP 403 / fragment / timed out / connection reset (YouTube chặn
        chữ ký-bot theo client hoặc mạng chập chờn) -> TỰ thử lại theo CHUỖI
        tối đa 3 lượt: mặc định+potoken -> default,web_safari -> android,tv
        (nghỉ 2s giữa các lượt) trước khi báo lỗi."""
        import re as _re
        import time as _time
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
        # [%(id)s] để tên file LUÔN duy nhất: 2 video trùng 80 ký tự đầu tiêu đề
        # -> yt-dlp thấy file đã có, KHÔNG tải, âm thầm dùng lại video cũ.
        out_tmpl = str(dl / "%(title).70s [%(id)s].%(ext)s")
        from config import settings as _st
        base = [exe, "--no-warnings", "--newline", "--no-quiet", "--progress",
                "--user-agent", ua, "-f",
                "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--merge-output-format", "mp4", "--no-playlist",
                # TĂNG TỐC TẢI: kéo NHIỀU MẢNH song song (yt-dlp có sẵn, không
                # cần cài gì) — né throttle của YouTube, nhanh gấp 3-5 lần.
                # Tiết kiệm máy -> 4 mảnh (đỡ CPU giải nén + băng thông).
                "--concurrent-fragments", "4" if _st.ECO_MODE else "8",
                "--http-chunk-size", "10M",
                # bỏ qua kiểm SSL cert lỗi vặt + retry mảnh lỗi (mạng VN chập chờn)
                "--retries", "10", "--fragment-retries", "10",
                "--print", "after_move:filepath", "-o", out_tmpl,
                # bật thêm node (deno vẫn mặc định): yt-dlp ≥2025.11 cần JS
                # runtime giải nsig — máy nào sẵn node thì tận dụng luôn
                "--js-runtimes", "node"]
        base += pot_args + list(extra_args or [])
        if ff_dir:
            base += ["--ffmpeg-location", ff_dir]

        # --- BẢO VỆ file cookie hồ sơ ---
        # yt-dlp GHI ĐÈ file --cookies khi thoát (write-back cookie đã được
        # YouTube rotate). Điều đó CÓ LỢI khi tải THÀNH CÔNG (giữ rotation,
        # cookie sống lâu), nhưng lượt FAIL bot-check/403 có thể ghi đè bộ
        # cookie hỏng lên hồ sơ tốt -> các lần tải sau chết luôn, user phải
        # xuất cookie mới. FIX: mỗi lượt chạy trên BẢN COPY tạm; chỉ khi lượt
        # đó THÀNH CÔNG mới merge write-back về hồ sơ; lượt fail vứt bản tạm,
        # lượt retry sau copy lại từ hồ sơ gốc (chưa bị đụng tới).
        import shutil as _sh
        import tempfile as _tmpmod
        cookie_src = ""
        if (len(cookie_args) == 2 and cookie_args[0] == "--cookies"
                and os.path.isfile(cookie_args[1])):
            cookie_src = cookie_args[1]

        def cookie_for_attempt():
            """Trả (args, tmp_path). Không phải file --cookies -> giữ nguyên."""
            if not cookie_src:
                return list(cookie_args), ""
            try:
                fd, tmp = _tmpmod.mkstemp(prefix="ytdlp_cookies_",
                                          suffix=".txt")
                os.close(fd)
                _sh.copyfile(cookie_src, tmp)
                return ["--cookies", tmp], tmp
            except Exception:  # noqa: BLE001 - lỗi tạo temp thì dùng thẳng file
                return list(cookie_args), ""

        def merge_back(tmp, success):
            if not tmp:
                return
            try:
                if success and os.path.getsize(tmp) > 40:
                    _sh.copyfile(tmp, cookie_src)   # giữ cookie đã rotate
            except Exception:  # noqa: BLE001
                pass
            try:
                os.remove(tmp)
            except Exception:  # noqa: BLE001
                pass

        def run_once(cmd):
            t0 = _time.time()
            try:
                # 0x40 = IDLE_PRIORITY_CLASS: tải/ghép chạy dài -> luôn nhường
                # app khác, máy không giật (tải là I/O mạng nên không chậm đi).
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=0x0800_0000 | 0x0000_0040)
            except Exception as e:  # noqa: BLE001
                return "", str(e)[:200]
            # đăng ký để đóng app giết được yt-dlp (không tải tiếp sau khi app tắt)
            from app.core.ffmpeg_utils import register_proc, unregister_proc
            register_proc(proc)
            path, tail, diag = "", [], []
            try:
                for line in proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    tail.append(line); tail[:] = tail[-8:]
                    # BẮT ĐÚNG LÝ DO THẬT: dòng "ERROR:" của yt-dlp (hoặc câu
                    # chẩn đoán quan trọng) hay bị đẩy khỏi 8 dòng tail cuối ->
                    # giữ riêng để hiện cho user thay vì tail cắt cụt vô nghĩa.
                    low = line.lower()
                    if (line.startswith("ERROR:")
                            or "sign in to confirm" in low
                            or "not a bot" in low
                            or "n challenge solving failed" in low
                            or "no supported javascript runtime" in low
                            or "drm protected" in low
                            or "requested format is not available" in low
                            or "failed to extract" in low
                            or "unable to extract" in low):
                        diag.append(line); diag[:] = diag[-4:]
                    if os.path.exists(line):
                        path = line
                    # video ĐÃ TẢI TRƯỚC ĐÓ: yt-dlp bỏ qua, không in filepath
                    # qua --print -> bắt từ dòng "... has already been downloaded"
                    elif line.endswith("has already been downloaded"):
                        cand = line[len("[download] "):] if line.startswith(
                            "[download] ") else line
                        cand = cand[: -len(" has already been downloaded")].strip()
                        if os.path.exists(cand):
                            path = cand
                    m = _re.search(r"\[download\]\s+([0-9.]+)%", line)
                    if m:
                        self.dl_progress.emit(
                            f"① {prefix}Đang tải... {m.group(1)}%")
                    elif "Merg" in line or "Fixup" in line:
                        self.dl_progress.emit(
                            f"① {prefix}Đang ghép hình + tiếng...")
                proc.wait()
            finally:
                unregister_proc(proc)
            if proc.returncode != 0:
                # ƯU TIÊN dòng ERROR:/chẩn đoán thật (lý do user cần đọc), chỉ
                # dùng tail khi không bắt được dòng nào -> không còn cắt cụt.
                msg = "\n".join(diag) if diag else "\n".join(tail)
                return "", (msg or "lỗi tải")[-500:]
            if not path or not os.path.exists(path):
                # fallback: CHỈ nhận file tạo SAU lúc bắt đầu tải — file mp4 "mới
                # nhất" trong kho chung có thể là của lượt tải khác/video cũ
                fs = sorted(
                    (p for p in dl.glob("*.mp4") if p.stat().st_mtime >= t0),
                    key=lambda p: p.stat().st_mtime)
                path = str(fs[-1]) if fs else ""
            if not path:
                # fallback CUỐI: tìm theo VIDEO ID trong tên file (template có
                # "[id]") — phủ ca "đã tải trước đó" mà không bắt được dòng log
                m = _re.search(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})", url)
                if m:
                    fs = sorted(dl.glob(f"*[[]{m.group(1)}[]]*.mp4"),
                                key=lambda p: p.stat().st_mtime)
                    path = str(fs[-1]) if fs else ""
            return path, "" if path else "Không thấy file tải."

        def retryable(e: str) -> bool:
            low = (e or "").lower()
            return any(s in low for s in (
                "403", "forbidden", "fragment", "timed out", "timeout",
                "connection reset",
                # MÁY KHÔNG CÓ node/deno (bản .exe): client tv/web cần chữ ký JS
                # (nsig) -> "n challenge solving failed" -> chỉ còn format DRM
                # -> "DRM protected"/"format is not available". Các lỗi này
                # SỬA được bằng lượt sau ép client android (KHÔNG cần JS runtime).
                "drm protected", "n challenge", "javascript runtime",
                "requested format is not available"))

        def run_attempt(extra):
            ck, tmp = cookie_for_attempt()
            p, e = run_once(base + ck + extra + [url])
            merge_back(tmp, success=bool(p and not e))
            return p, e

        # CHUỖI FALLBACK tối đa 3 lượt: (1) mặc định + potoken ->
        # (2) android_vr,android,ios,tv_simply -> (3) android,ios (nhẹ nhất).
        # QUAN TRỌNG: mọi client fallback KHÔNG cần JS runtime (nsig) — máy
        # khách bản .exe không kèm node/deno; client tv/web_safari (chain cũ)
        # đòi giải nsig-js nên trên máy khách chỉ còn format DRM -> FAIL. Các
        # client android/ios/tv_simply vẫn cho tới 1080p mà khỏi JS runtime.
        path, err = run_attempt([])
        fallbacks = ["youtube:player_client=android_vr,android,ios,tv_simply",
                     "youtube:player_client=android,ios"]
        for k, client in enumerate(fallbacks, start=2):
            if not err or not retryable(err):
                break
            self.dl_progress.emit(
                f"① {prefix}Thử cách tải khác ({k}/3)...")
            _time.sleep(2)                 # giãn nhịp -> đỡ bị chặn tiếp
            path, err = run_attempt(["--extractor-args", client])
        return path, err

    def _dl_busy(self) -> bool:
        """Đang có lượt tải chạy? 2 yt-dlp ghi cùng thư mục sẽ loạn tiến trình
        + fallback vớ nhầm file của lượt kia."""
        if getattr(self, "_dl_active", 0) > 0:
            QMessageBox.information(
                self, "Đang tải",
                "Đang có lượt tải chạy — chờ xong rồi tải tiếp nhé.")
            return True
        return False

    def _set_dl_active(self, on: bool):
        self._dl_active = 1 if on else 0
        self.yt_btn.setEnabled(not on)
        self.yt_many_btn.setEnabled(not on)

    def _download_youtube(self):
        url = self.yt_url.text().strip()
        if not url:
            QMessageBox.information(self, "Chưa có link", "Dán link YouTube vào ô.")
            return
        if self._is_multi_url(url):
            QMessageBox.warning(
                self, "Link playlist/kênh",
                "Đây là link PLAYLIST hoặc KÊNH — sẽ tải hàng loạt không kiểm "
                "soát.\nHãy dán link VIDEO đơn (youtube.com/watch?v=... hoặc "
                "youtu.be/...),\nhoặc dùng nút 'Tải nhiều' và dán từng link "
                "video một dòng.")
            return
        if self._dl_busy():
            return
        ready = self._yt_ready()
        if not ready:
            return
        exe, dl, ff_dir = ready
        # VIDEO ĐÃ TẢI TRƯỚC ĐÓ? -> HỎI user: dùng lại file có sẵn (nhanh)
        # hay tải mới đè lên (file hỏng/muốn chất lượng khác) hay thôi.
        extra_args = []
        existing = self._find_downloaded(url, dl)
        if existing:
            box = QMessageBox(self)
            box.setWindowTitle("Video này đã tải trước đó")
            box.setText(f"Đã có sẵn trong kho:\n{os.path.basename(existing)}\n\n"
                        "Bạn muốn làm gì?")
            b_use = box.addButton("Dùng file có sẵn (nhanh)",
                                  QMessageBox.ButtonRole.AcceptRole)
            b_new = box.addButton("Tải lại mới (ghi đè)",
                                  QMessageBox.ButtonRole.DestructiveRole)
            box.addButton("Hủy", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is b_use:
                self._dl_pid = self.state.project_id
                self._set_dl_active(True)
                self._on_dl_done(existing, "")     # nhập + phân tích như tải xong
                return
            if box.clickedButton() is b_new:
                extra_args = ["--force-overwrites"]
            else:
                return
        cookie_args = self._cookie_args()
        self._dl_pid = self.state.project_id      # NHỚ kênh lúc bấm (tránh đổi giữa chừng)
        self._set_dl_active(True)
        self.status.setText("① Đang tải video từ YouTube... "
                            "(tải xong sẽ TỰ ② phân tích & cắt)")

        def work():
            pot = self._potoken()
            path, err = self._run_ytdlp(url, exe, dl, ff_dir, cookie_args, pot,
                                        extra_args=extra_args)
            self.dl_done.emit(path, err)
        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _find_downloaded(url: str, dl) -> str:
        """File đã tải sẵn của video này trong kho (theo [video_id] trong tên)."""
        import re as _re
        m = _re.search(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})", url or "")
        if not m:
            return ""
        fs = sorted(Path(dl).glob(f"*[[]{m.group(1)}[]]*.mp4"),
                    key=lambda p: p.stat().st_mtime)
        return str(fs[-1]) if fs else ""

    def _download_many(self):
        """Dán NHIỀU link -> tải hết -> mỗi video tự phân tích + cắt (+ tự xuất)."""
        ready = self._yt_ready()
        if not ready:
            return
        exe, dl, ff_dir = ready
        dlg = QDialog(self); dlg.setWindowTitle("Tải nhiều link (tự cắt hàng loạt)")
        dlg.resize(540, 440)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Dán NHIỀU link YouTube — MỖI LINK 1 DÒNG:"))
        box = QPlainTextEdit()
        box.setPlaceholderText("https://youtu.be/aaa\nhttps://youtu.be/bbb\n...")
        v.addWidget(box, 1)
        hint = QLabel("Tải xong từng video sẽ TỰ phân tích + cắt clip. Muốn xuất luôn "
                      "thì bật ô 'Phân tích xong tự động xuất' ở mục Tạo clip.")
        hint.setWordWrap(True); hint.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(hint)
        rowb = QHBoxLayout(); rowb.addStretch(1)
        ok = QPushButton("Tải hết"); ok.setProperty("primary", True)
        ok.clicked.connect(dlg.accept)
        cc = QPushButton("Hủy"); cc.setProperty("ghost", True); cc.clicked.connect(dlg.reject)
        rowb.addWidget(cc); rowb.addWidget(ok); v.addLayout(rowb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        import re as _re
        urls = [u for u in _re.split(r"[\s,]+", box.toPlainText())
                if u.strip().startswith("http")]
        if not urls:
            QMessageBox.information(self, "Chưa có link", "Dán ít nhất 1 link hợp lệ.")
            return
        multi = [u for u in urls if self._is_multi_url(u)]
        if multi:
            QMessageBox.warning(
                self, "Có link playlist/kênh",
                f"{len(multi)} link là PLAYLIST/KÊNH (tải hàng loạt không kiểm "
                "soát) — đã BỎ QUA:\n" + "\n".join(multi[:5])
                + ("\n…" if len(multi) > 5 else "")
                + "\n\nHãy dán link VIDEO đơn, mỗi link 1 dòng.")
            urls = [u for u in urls if not self._is_multi_url(u)]
            if not urls:
                return
        if self._dl_busy():
            return
        cookie_args = self._cookie_args()
        self._batch_remaining = len(urls)
        self._batch_ok = 0
        self._batch_fails = []                    # [(url, lỗi)] để báo cuối loạt
        self._batch_pid = self.state.project_id   # NHỚ kênh lúc bấm (cố định cả loạt)
        self._set_dl_active(True)
        n = len(urls)

        def work():
            import time
            pot = self._potoken()
            for k, url in enumerate(urls, 1):
                self.dl_progress.emit(f"① Tải video {k}/{n}...")
                path, err = self._run_ytdlp(url, exe, dl, ff_dir, cookie_args, pot,
                                            prefix=f"({k}/{n}) ")
                self.dl_one.emit(path, err, url)
                if k < n:                  # GIÃN NHỊP giữa các video -> đỡ bị chặn
                    self.dl_progress.emit(f"Nghỉ chút trước video {k + 1}/{n} "
                                          "(tránh YouTube chặn)...")
                    time.sleep(5)
        threading.Thread(target=work, daemon=True).start()

    def _on_batch_one(self, path, err, url=""):
        """1 video trong loạt tải xong -> import + tự phân tích/cắt.
        GOM LỖI để báo cuối loạt — trước đây nuốt im lặng, cả 10 link fail
        vẫn báo 'Đã tải xong cả loạt'."""
        pid = getattr(self, "_batch_pid", None) or self.state.project_id
        if path and not err and pid:
            try:
                vid = services.import_video(pid, path)
                # CHẶN SỚM: chưa có cách chép lời -> vẫn giữ video đã tải,
                # nhưng KHÔNG tự chạy job phân tích (chắc chắn fail).
                if self._require_ai_after_dl():
                    jid = services.enqueue_auto(self.state.pool, vid, pid,
                                                self._cut_preset())
                    self._track_auto(jid, vid)
                self._batch_ok = getattr(self, "_batch_ok", 0) + 1
                self._reload_videos()
            except Exception as e:  # noqa: BLE001
                self._batch_fails = getattr(self, "_batch_fails", [])
                self._batch_fails.append((url, f"import lỗi: {e}"))
        else:
            self._batch_fails = getattr(self, "_batch_fails", [])
            self._batch_fails.append((url, (err or "không rõ")[:160]))
        self._batch_remaining = getattr(self, "_batch_remaining", 1) - 1
        if self._batch_remaining <= 0:
            self._set_dl_active(False)
            ok = getattr(self, "_batch_ok", 0)
            fails = getattr(self, "_batch_fails", [])
            if fails:
                self.status.setText(
                    f"Tải xong {ok} video, LỖI {len(fails)} link.")
                low = " ".join(e for _, e in fails).lower()
                cookie_hint = ("sign in" in low or "not a bot" in low
                               or "cookie" in low or "confirm" in low)
                QMessageBox.warning(
                    self, "Một số link tải lỗi",
                    f"Tải được {ok}, lỗi {len(fails)} link:\n\n"
                    + "\n".join(f"• {u}\n   {e}" for u, e in fails[:6])
                    + ("\n…" if len(fails) > 6 else "")
                    + ("\n\n👉 YouTube đòi cookie: bấm nút <b>Cookie</b> cạnh "
                       "nút Tải → dán cookie → Lưu → tải lại các link lỗi."
                       if cookie_hint else "")
                    + ("\n\n👉 Lỗi 403 = YouTube chặn tạm thời — thử lại sau "
                       "vài phút, dán cookie mới (nút Cookie), hoặc cập nhật "
                       "app (yt-dlp mới)."
                       if ("403" in low or "forbidden" in low) else "")
                    + ("\n\n👉 DRM/chữ ký JS = YouTube tạm khóa định dạng — thử "
                       "TẢI LẠI các link lỗi 1-2 lần (thường lần sau qua), hoặc "
                       "chờ vài phút / cập nhật app."
                       if ("drm protected" in low
                           or "n challenge" in low
                           or "javascript runtime" in low) else "")
                    + (self._cookie_fail_hint()
                       if (cookie_hint or "403" in low or "forbidden" in low)
                       else ""))
            elif ok:
                if not self._ai_ready():
                    # đã tải nhưng KHÔNG tự phân tích (chưa có key Groq)
                    self.status.setText(
                        f"⚠ Đã tải {ok} video nhưng CHƯA phân tích — "
                        + self._NO_AI_MSG)
                    return
                extra = " + tự xuất" if self.auto_export_chk.isChecked() else ""
                self.status.setText(
                    f"✓ ① Tải xong cả loạt ({ok} video) → ② Đang phân tích & "
                    f"cắt từng video{extra} (xem Tiến trình dưới). Xong clip "
                    "TỰ hiện ở danh sách dưới.")
            else:
                self.status.setText("Loạt tải kết thúc: không có video nào.")

    def _on_dl_done(self, path, err):
        self._set_dl_active(False)
        if err or not path:
            low = (err or "").lower()
            if ("sign in" in low or "not a bot" in low or "confirm" in low
                    or "cookies" in low or "cookie" in low):
                msg = ("YouTube đòi đăng nhập/cookie cho video này.\n\n"
                       "Cách sửa (1 lần dùng mãi): bấm nút <b>Cookie</b> cạnh nút "
                       "Tải → làm theo hướng dẫn dán cookie → Lưu → Tải lại."
                       + self._cookie_fail_hint())
                QMessageBox.warning(self, "YouTube đòi cookie", msg)
                self.status.setText("Tải LỖI: YouTube đòi cookie — bấm nút Cookie.")
            elif "403" in low or "forbidden" in low:
                QMessageBox.warning(
                    self, "YouTube chặn tạm thời (403)",
                    "YouTube đang chặn tải video này (HTTP 403).\n\n"
                    "Cách sửa:\n"
                    "• Thử lại sau vài phút (chặn thường tự hết).\n"
                    "• Bấm nút <b>Cookie</b> cạnh nút Tải → dán cookie mới → "
                    "tải lại.\n"
                    "• Cập nhật app lên bản mới nhất (kèm yt-dlp mới vá lỗi "
                    "này)."
                    + self._cookie_fail_hint())
                self.status.setText(
                    "Tải LỖI 403: YouTube chặn tạm thời — thử lại sau vài phút "
                    "hoặc dán cookie mới.")
            elif ("drm protected" in low or "n challenge solving failed" in low
                  or "javascript runtime" in low
                  or "requested format is not available" in low):
                QMessageBox.warning(
                    self, "YouTube đổi cách bảo vệ (thử lại)",
                    "YouTube tạm khóa định dạng video này (DRM/chữ ký JS).\n\n"
                    "Cách sửa:\n"
                    "• Bấm <b>Tải về</b> lại 1-2 lần (thường lần sau qua được).\n"
                    "• Thử lại sau vài phút.\n"
                    "• Dán cookie mới (nút <b>Cookie</b>).\n"
                    "• Cập nhật app lên bản mới nhất (kèm yt-dlp mới).\n\n"
                    "Chi tiết lỗi:\n" + (err or "không rõ")[:400])
                self.status.setText(
                    "Tải LỖI (DRM/chữ ký): thử Tải lại 1-2 lần hoặc sau vài phút. "
                    + (err or "")[:200])
            else:
                QMessageBox.warning(
                    self, "Tải YouTube lỗi",
                    "Không tải được video. Chi tiết lỗi từ yt-dlp:\n\n"
                    + (err or "không rõ")[:500])
                self.status.setText("Tải YouTube LỖI: " + (err or "không rõ")[:200])
            return
        pid = getattr(self, "_dl_pid", None) or self.state.project_id
        if not pid:
            self.status.setText("Đã tải xong nhưng chưa có kênh để thêm vào.")
            return
        try:
            vid = services.import_video(pid, path)
        except Exception as e:  # noqa: BLE001 - kênh vừa bị xóa/file lỗi -> không sập app
            self.status.setText(f"Tải xong nhưng import lỗi: {str(e)[:160]}")
            return
        self.yt_url.clear()
        self._reload_videos(select_id=vid)   # chọn đúng video VỪA TẢI
        # CHẶN SỚM: chưa có cách chép lời thì đừng tự chạy job (chắc chắn fail)
        if not self._require_ai_after_dl():
            return
        # TỰ ĐỘNG phân tích luôn (dán link -> tải -> phân tích -> tự xuất nếu bật)
        jid = services.enqueue_auto(self.state.pool, vid, pid, self._cut_preset())
        self._track_auto(jid, vid)
        extra = " → xong TỰ XUẤT" if self.auto_export_chk.isChecked() else ""
        self.status.setText(
            f"✓ ① Tải xong → ② Đang phân tích & cắt clip (xem % ở khu Tiến "
            f"trình dưới){extra}... Xong clip sẽ TỰ hiện ở danh sách dưới.")

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

        # PHÒNG HỜ: máy nào QMediaPlayer lỗi (thiếu codec/backend hỏng) ->
        # báo rõ + mở video bằng trình phát mặc định (vẫn cắt tay được theo
        # số giây xem ở trình phát ngoài).
        _err_once = []

        def _on_player_err(_e, msg):
            if _err_once:
                return
            _err_once.append(1)
            QMessageBox.warning(
                dlg, "Trình phát trong app lỗi",
                f"Không phát được video trong app ({msg or 'không rõ'}).\n"
                "Sẽ mở bằng trình phát mặc định của Windows — xem mốc giây "
                "ở đó rồi quay lại đây đặt ĐẦU/CUỐI bằng thanh kéo.")
            try:
                os.startfile(vrow["src_path"])
            except OSError:
                pass
        player.errorOccurred.connect(_on_player_err)

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
        # KÉO: chỉ đổi nhãn giờ; THẢ mới tua thật -> không tua liên tục (đỡ lag video)
        sld.sliderMoved.connect(
            lambda v: tlb.setText(fmt(int(v / 1000 * (player.duration() or 0)))))
        sld.sliderReleased.connect(
            lambda: player.setPosition(int(sld.value() / 1000 * (player.duration() or 0))))

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

        def save_trim() -> bool:
            if trim[1] - trim[0] < 1.0:
                QMessageBox.information(dlg, "Đoạn quá ngắn", "Đầu/cuối chưa hợp lý.")
                return False
            nsig = dict(sig)
            nsig["segments"] = [[round(trim[0], 2), round(trim[1], 2)]]
            nsig["n_seg"] = 1
            nsig["speed"] = float(spcb.currentText().rstrip("x"))
            db.execute("UPDATE clips SET start_sec=?, end_sec=?, signals=? WHERE id=?",
                       (round(trim[0], 2), round(trim[1], 2), db.dumps(nsig), c["id"]))
            self._refresh_clips(force=True)
            self.status.setText("Đã lưu cắt tay + tốc độ cho clip.")
            return True
        sv.clicked.connect(save_trim)

        def do_export():
            if not save_trim():      # trim không hợp lệ -> KHÔNG được xuất tiếp
                return
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
            services.delete_video(int(vid), self.state.pool)
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
                services.delete_video(int(vid), self.state.pool)
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
                services.delete_project(int(pid), self.state.pool)
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
        if not self._require_ai():
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
        self.status.setText(f"② Đang phân tích & cắt clip{extra}... "
                            "(xem % ở khu Tiến trình dưới — xong TỰ hiện ở đây)")

    def _auto_mixed(self):
        """Mixed-Cut: ghép các khoảnh khắc hay nhất khắp video thành 1 clip."""
        if not self.state.video_id:
            QMessageBox.information(self, "Chưa chọn video",
                                    "Thêm/chọn 1 video trước đã.")
            return
        if not self._require_ai():
            return
        services.enqueue_auto_mixed(self.state.pool, self.state.video_id,
                                    self.state.project_id, self._cut_preset())
        self.status.setText("Đang phân tích & ghép Mixed-Cut... clip sẽ hiện "
                            "trong danh sách khi xong (xem tiến trình dưới).")

    def _recap_settings(self):
        """⚙ mở 'Cài đặt Reup thuyết minh' rồi ĐỒNG BỘ lại combo phong cách
        ngoài màn hình chính (dialog + combo dùng chung key QSettings)."""
        from app.ui.recap_settings import RecapSettingsDialog
        dlg = RecapSettingsDialog(self)
        if dlg.exec():
            style = str(self._settings.value("recap_style", "story") or "story")
            i = self.recap_style.findData(style)
            if i >= 0 and i != self.recap_style.currentIndex():
                # setCurrentIndex sẽ bắn signal -> ghi lại QSettings cùng giá
                # trị (vô hại), không cần blockSignals
                self.recap_style.setCurrentIndex(i)
            self.status.setText("Đã lưu cài đặt Reup thuyết minh (áp dụng "
                                "cho mọi kênh).")

    def _recap_volume(self) -> float:
        """Hệ số 'Âm lượng giọng kể' từ ⚙ Cài đặt Reup (QSettings
        recap_volume 80-200%, mặc định 115) -> 0.8-2.0 cho build_recap_track
        (nhân THÊM sau auto-match loudness với tiếng gốc)."""
        try:
            v = int(self._settings.value("recap_volume", 115))
        except (TypeError, ValueError):
            v = 115
        return min(200, max(80, v)) / 100.0

    def _auto_recap(self):
        """🎙 Reup thuyết minh: AI viết kịch bản thuyết minh xen kẽ tiếng gốc."""
        if not self.state.video_id:
            QMessageBox.information(self, "Chưa chọn video",
                                    "Thêm/chọn 1 video trước đã.")
            return
        if not self._require_ai():
            return
        preset = self._cut_preset()
        preset["recap_style"] = self.recap_style.currentData() or "story"
        try:                            # tỉ lệ AI kể từ ⚙ Cài đặt Reup
            preset["recap_ratio"] = int(self._settings.value("recap_ratio", 30))
        except (TypeError, ValueError):
            preset["recap_ratio"] = 30
        # MIGRATE NHẸ: 55 = mặc định CŨ chưa ai đổi -> dùng mặc định mới 30
        # (chỉ đúng giá trị 55; giá trị khác là user tự chọn -> giữ nguyên).
        if preset["recap_ratio"] == 55:
            preset["recap_ratio"] = 30
        preset["recap_ratio"] = min(80, max(15, preset["recap_ratio"]))
        try:                            # số clip thuyết minh từ ⚙
            # 0 = "Tự động theo độ dài" (mặc định) — m2_recap tự tính theo
            # duration; 1-3 = user chọn tay.
            preset["recap_count"] = min(3, max(0, int(
                self._settings.value("recap_count", 0))))
        except (TypeError, ValueError):
            preset["recap_count"] = 0
        # Độ dài mỗi clip Reup (giây) từ ⚙ Cài đặt Reup — OVERRIDE 'Tùy chỉnh
        # cắt' chung cho ĐƯỜNG RECAP (m2.generate_recap đọc min_len/max_len).
        # Thiếu key (phòng xa) -> giữ nguyên min_len/max_len từ _cut_preset().
        try:
            lmin = int(self._settings.value("recap_min_sec", 25))
        except (TypeError, ValueError):
            lmin = 25
        try:
            lmax = int(self._settings.value("recap_max_sec", 80))
        except (TypeError, ValueError):
            lmax = 80
        lmin = min(180, max(10, lmin))
        lmax = max(lmin, min(600, max(15, lmax)))
        preset["min_len"] = float(lmin)
        preset["max_len"] = float(lmax)
        # Số cảnh ghép GIỜ LUÔN do AI tự quyết (m2 bound rộng 2-8 + prompt
        # không gò cứng) — bỏ set recap_win_* vào preset.
        # 🎭 Giọng cảm xúc (audio tag v3) — MẶC ĐỊNH BẬT; đưa vào preset để
        # prompt biết mà chèn tag cảm xúc vào lời narrate.
        preset["recap_emotion"] = str(
            self._settings.value("recap_emotion", True)).strip().lower() \
            not in ("false", "0", "no", "off")
        services.enqueue_auto_recap(self.state.pool, self.state.video_id,
                                    self.state.project_id, preset)
        self.status.setText(
            "🎙 Đang phân tích & viết kịch bản thuyết minh "
            f"({self.recap_style.currentText()})... clip sẽ hiện trong danh "
            "sách khi xong (xem tiến trình dưới).")

    def _auto_all(self):
        """Đưa MỌI video chưa có clip trong kênh vào hàng đợi (chạy song song)."""
        if not self.state.project_id:
            QMessageBox.information(self, "Chưa có kênh", "Tạo/chọn kênh trước.")
            return
        vids = services.list_videos(self.state.project_id)
        if not vids:
            QMessageBox.information(self, "Chưa có video", "Thêm video vào kênh trước.")
            return
        if not self._require_ai():
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
        if not self._require_ai():
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
    def _a_frame_bg(self):
        """Lấy 1 khung hình để chỉnh mẫu (clip đầu hoặc giữa video) — CHẠY NỀN.

        Trả None NGAY nếu chưa chọn video/thiếu dữ liệu (mở editor với ảnh mẫu),
        ngược lại trả (src_path, t, frame_path) để thread nền extract_frame:
        ffmpeg đọc file trên ổ mạng/OneDrive có thể treo tới 30s — chạy trên
        UI thread sẽ ĐƠ CẢ APP (đã gặp)."""
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
        return (vrow["src_path"], t, frame)

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
        """Bấm 'Chỉnh mẫu': lấy khung hình Ở THREAD NỀN rồi mới mở editor —
        extract_frame trên UI thread từng làm đơ app 30s với file OneDrive."""
        job = self._a_frame_bg()
        if job is None:                     # chưa chọn video -> ảnh mẫu, mở luôn
            self._open_editor(self._sample_frame())
            return
        src, t, frame = job
        self.tmpl_edit_btn.setEnabled(False)   # chặn bấm đúp khi đang chờ
        self.status.setText("Đang lấy khung hình xem trước...")
        out: list = []

        def bg():
            try:
                out.append(str(frame) if extract_frame(src, t, frame, 360)
                           else "")
            except Exception:  # noqa: BLE001 - lỗi gì cũng phải trả lời poll
                out.append("")

        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop()
            self.tmpl_edit_btn.setEnabled(True)
            self.status.setText("")
            self._open_editor(out[0] or self._sample_frame())

        timer.timeout.connect(poll)
        timer.start(100)

    def _open_editor(self, frame):
        dlg = EditorDialog(frame, self.layout_tpl, self,
                           current_name=self.tmpl_box.currentData() or "")
        accepted = bool(dlg.exec() and dlg.layout_result)
        # NẠP LẠI cả khi user bấm Lưu/Lưu mới/Xóa rồi đóng bằng Hủy/X: DB đã
        # đổi mà layout_tpl trong RAM còn bản CŨ -> mở lại editor / xuất clip
        # sẽ dùng sai mẫu (vd tắt HOOK, bấm Lưu, đóng -> HOOK bật lại).
        if not (accepted or getattr(dlg, "_db_changed", False)):
            return                       # không lưu gì -> giữ nguyên
        name = getattr(dlg, "_current_name", "") or ""
        # làm mới + CHỌN đúng mẫu vừa sửa, rồi NẠP LẠI TỪ DB để layout dùng
        # khi xuất KHỚP 100% với mẫu đã lưu (tránh lưu 1 nơi xuất 1 nơi).
        self._populate_templates(name)
        self._settings.setValue("last_template", name)
        self._apply_selected_template()
        if accepted and getattr(dlg, "_save_failed", False):
            # DB lưu lỗi nhưng dialog đã hứa "layout vẫn áp cho phiên này"
            # -> dùng bản vừa chỉnh trong RAM thay vì bản cũ từ DB.
            self.layout_tpl = dlg.layout_result
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
    def _poll_done(self):
        """Định kỳ (theo timer): job của VIDEO ĐANG CHỌN vừa chạy XONG ->
        báo '✓ Xong — N clip' + cập nhật đuôi trạng thái combo. So sánh
        chữ ký busy trước/sau nên KHÔNG rebuild gì khi không có thay đổi."""
        self._update_job_progress()   # % + message job đang chạy (cùng timer 1.5s)
        vid = self.state.video_id
        busy = self._video_busy(vid)
        prev_vid, prev_busy = getattr(self, "_job_watch", (None, False))
        self._job_watch = (vid, busy)
        if vid is None or vid != prev_vid or busy or not prev_busy:
            return                        # không phải chuyển busy -> xong
        n = len(services.list_clips(vid))
        # cập nhật đuôi '✂ N clip' ở combo, GIỮ video đang chọn (không giật)
        self._reload_videos(select_id=vid)   # tự gọi _refresh_clips(force)
        if n:
            self.status.setText(
                f"✓ ③ Xong — {n} clip đã sẵn sàng ở danh sách bên dưới.")
        else:
            self.status.setText(
                "⚠ Xử lý xong nhưng chưa có clip — xem khu Tiến trình bên "
                "dưới có báo lỗi không.")

    def _refresh_clips(self, force=False):
        vid = self.state.video_id
        clips = services.list_clips(vid) if vid else []
        busy = self._video_busy(vid)      # để empty-state đổi khi job chạy/xong
        if not force and getattr(self, "_n", -1) == len(clips) \
                and getattr(self, "_busy", None) == busy \
                and all(getattr(self, "_st", {}).get(c["id"]) == c["status"]
                        for c in clips):
            return
        self._n = len(clips)
        self._busy = busy
        self._st = {c["id"]: c["status"] for c in clips}
        self._cur_clips = clips
        self._cur_vrow = db.query_one(
            "SELECT v.src_path, p.assets_dir FROM videos v "
            "JOIN projects p ON p.id=v.project_id WHERE v.id=?", (vid,)) if vid else None
        self._rebuild_rows()

    def _rebuild_rows(self):
        clips = getattr(self, "_cur_clips", [])
        vrow = getattr(self, "_cur_vrow", None)
        self._job_bar = self._job_lbl = None   # widget cũ sắp bị gỡ khỏi list
        while self.list_box.count() > 1:
            w = self.list_box.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.count_lbl.setText(f"{len(clips)} clip đề xuất" if clips else "")
        if not clips:
            self.list_box.insertWidget(self.list_box.count() - 1, self._empty_state())
            return
        # clip ĐÃ có nhưng job đang chạy lại (phân tích/xuất) -> thanh tiến độ
        # NHỎ trên đầu danh sách (không che clip, video khác vẫn thao tác được)
        if getattr(self, "_busy", False):
            self.list_box.insertWidget(0, self._job_progress_widget(compact=True))
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

    # ---- tiến độ job của video đang chọn (hiện NGAY vùng clip) ----
    def _job_progress_row(self, vid):
        """Job đang CHẠY (ưu tiên) hoặc đang chờ của video: progress + message."""
        if not vid:
            return None
        try:
            return (db.query_one(
                "SELECT progress, message, status FROM jobs WHERE video_id=? "
                "AND status='running' ORDER BY id DESC LIMIT 1", (vid,))
                or db.query_one(
                "SELECT progress, message, status FROM jobs WHERE video_id=? "
                "AND status='pending' ORDER BY id LIMIT 1", (vid,)))
        except Exception:  # noqa: BLE001
            return None

    def _job_progress_widget(self, compact=False):
        """Thanh % + dòng trạng thái job. compact=True: dải nhỏ đầu danh sách
        clip; False: to hơn, căn giữa trong empty-state."""
        w = QWidget()
        lay = QVBoxLayout(w); lay.setSpacing(4)
        lay.setContentsMargins(12, 8 if compact else 0, 12, 8 if compact else 0)
        bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(0)
        bar.setFixedHeight(14 if compact else 20)
        bar.setTextVisible(True)
        row = QHBoxLayout()
        if compact:
            row.addWidget(bar, 1)
        else:
            bar.setFixedWidth(520)
            row.addStretch(1); row.addWidget(bar); row.addStretch(1)
        lay.addLayout(row)
        lbl = QLabel("Đang xử lý…")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        if not compact:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        self._job_bar, self._job_lbl = bar, lbl
        self._update_job_progress()   # điền giá trị ngay, khỏi chờ nhịp timer
        return w

    def _update_job_progress(self):
        """Cập nhật thanh tiến độ theo NHỊP TIMER 1.5s sẵn có (gọi từ
        _poll_done) — không tạo timer mới, không rebuild danh sách."""
        bar = getattr(self, "_job_bar", None)
        lbl = getattr(self, "_job_lbl", None)
        if bar is None or lbl is None:
            return
        r = self._job_progress_row(self.state.video_id)
        if not r:
            return
        try:
            pct = int(max(0.0, min(1.0, float(r["progress"] or 0))) * 100)
            if r["status"] == "pending":
                msg = r["message"] or "Đang chờ đến lượt trong hàng đợi…"
            else:
                msg = r["message"] or "Đang xử lý…"
            bar.setValue(pct)
            lbl.setText(msg)
        except RuntimeError:          # widget vừa bị gỡ khi rebuild danh sách
            self._job_bar = self._job_lbl = None

    def _empty_state(self):
        """Vùng danh sách khi CHƯA có clip: nói rõ đang ở bước nào —
        đang xử lý ngầm (job chạy) / chưa tạo clip / chưa có video."""
        vid = self.state.video_id
        busy = bool(vid) and getattr(self, "_busy", False)
        if busy:
            ic, ic_col = "⏳", WARN
            head = "Đang phân tích & cắt clip video này…"
            sub = ("Tiến độ hiện ngay bên dưới. Xong clip sẽ TỰ hiện "
                   "tại đây — video khác vẫn xem/thao tác bình thường.")
        elif vid:
            ic, ic_col = "✂", ACCENT
            head = "Chưa có clip"
            sub = "Bấm nút ② Tạo clip để AI phân tích & cắt video này."
        else:
            ic, ic_col = "+", ACCENT
            head = "Chưa có clip nào"
            sub = ("KÉO-THẢ video vào đây (hoặc “+ Thêm video”), rồi bấm "
                   "“Tạo clip”.")
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 60, 0, 0)
        lay.setSpacing(10)
        icon = QLabel(ic)
        icon.setStyleSheet(f"font-size:46px; font-weight:700; color:{ic_col};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)
        t1 = QLabel(head)
        t1.setStyleSheet("font-size:18px; font-weight:600;")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t1)
        t2 = QLabel(sub)
        t2.setWordWrap(True)
        t2.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t2)
        if busy:
            # thanh % + message của job (cập nhật qua timer 1.5s sẵn có)
            lay.addSpacing(8)
            lay.addWidget(self._job_progress_widget(compact=False))
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
        if (sig.get("recap") or {}).get("parts"):
            # 🎙 clip CÓ kịch bản thuyết minh -> xuất sẽ tự dựng giọng AI
            rc = sig["recap"]
            n_nar = sum(1 for p in rc["parts"] if p.get("mode") == "narrate")
            rc_lbl = QLabel("🎙 Thuyết minh")
            rc_lbl.setStyleSheet(f"color:{ACCENT}; font-size:11px; "
                                 "font-weight:700; border:none;")
            rc_lbl.setToolTip(
                f"Kịch bản thuyết minh AI: {len(rc['parts'])} đoạn "
                f"({n_nar} đoạn giọng AI, còn lại giữ tiếng gốc). Khi xuất, "
                "tiếng gốc TẮT trong các đoạn thuyết minh.")
            info.addWidget(_shrinkable(rc_lbl))
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
        # Mixed-Cut lưu key KHÁC (moments/n) so với clip AI (segments/n_seg/dur).
        # Đọc nhầm -> card hiện SPAN đầu-cuối (vd 93s) + không có thanh đoạn nên
        # nhìn như 1 clip liền, dù file xuất ra ĐÃ ghép đúng các moment rời.
        if sig.get("mode") == "mixed":
            segs = [[m["start"], m["end"]] for m in (sig.get("moments") or [])]
            total = sum(e - s for s, e in segs) or (c["end_sec"] - c["start_sec"])
            nseg = sig.get("n", len(segs) or 1)
        else:
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

        # ---- điểm viral: BADGE TRÒN màu theo mức (>=80 xanh, >=60 vàng, <60 xám) ----
        score = int(c["score"] or 0)
        scol = SUCCESS if score >= 80 else (WARN if score >= 60 else MUTED)
        sc = QLabel(str(score))
        sc.setFixedSize(38, 38)
        sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.setStyleSheet(f"background:{SURFACE}; color:{scol}; border:1px solid {scol};"
                         "border-radius:19px; font-size:13px; font-weight:700;")
        sc.setToolTip("Điểm tiềm năng viral (0–100) — AI chấm theo nội dung + hình ảnh")
        lay.addWidget(sc)

        pv = QPushButton("Xem & sửa"); pv.setFixedWidth(92); pv.setProperty("ghost", True)
        pv.setFixedHeight(28)
        pv.setToolTip("Phát video, chỉnh tốc độ, cắt tay đầu/cuối rồi xuất.")
        pv.clicked.connect(lambda _, cc=c, n=part_no: self._review_clip(cc, n))
        lay.addWidget(pv)
        cap = QPushButton("Caption"); cap.setFixedWidth(78); cap.setProperty("ghost", True)
        cap.setFixedHeight(28)
        cap.setToolTip("AI viết TIÊU ĐỀ + CAPTION + HASHTAG đăng bài cho clip "
                       "này — copy dán thẳng lên TikTok/Reels/Shorts.")
        cap.clicked.connect(lambda _, cc=c: self._write_caption(cc))
        lay.addWidget(cap)
        if c["status"] == "exported" and c["export_path"]:
            mo = QPushButton("Mở"); mo.setFixedWidth(56); mo.setProperty("ghost", True)
            mo.setFixedHeight(28)
            mo.setToolTip("Phát file clip đã xuất.")
            mo.clicked.connect(lambda _, p=c["export_path"]: self._open_file(p))
            lay.addWidget(mo)
            label = "Xuất lại"
        else:
            label = "Xuất"
        dl = QPushButton(label); dl.setFixedWidth(80); dl.setProperty("primary", True)
        dl.setFixedHeight(32)
        dl.setToolTip("Xuất clip này ra file MP4 (Kho video > Đã xuất).")
        dl.clicked.connect(
            lambda _, cid=c["id"]: self._export_video(self.state.video_id, cid))
        lay.addWidget(dl)
        rm = QPushButton("Xóa"); rm.setFixedWidth(52); rm.setProperty("danger", True)
        rm.setFixedHeight(28)
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

    # ---- AI viết caption + hashtag đăng bài ----
    def _write_caption(self, c):
        from app.ai import llm as _llm
        if not _llm.is_configured():
            QMessageBox.information(
                self, "Chưa bật AI",
                "Vào 'Cài đặt AI' dán key Groq (miễn phí) hoặc Gemini trước đã.")
            return
        # Lời thoại CỦA CLIP: ưu tiên cột transcript; rỗng (clip AI) thì cắt
        # từ transcript video theo segments của clip.
        from app.core.analysis import get_analysis
        tr = get_analysis(c["video_id"], "transcript") or {}
        text = (c["transcript"] or "").strip()
        if not text:
            segs = ((db.loads(c["signals"], {}) or {}).get("segments")
                    or [[c["start_sec"], c["end_sec"]]])
            parts = []
            for s in tr.get("segments", []):
                try:
                    if any(float(s["start"]) < e and float(s["end"]) > b
                           for b, e in segs):
                        parts.append(s["text"])
                except (KeyError, TypeError, ValueError):
                    continue
            text = " ".join(parts)
        chrow = db.query_one("SELECT name FROM projects WHERE id=?",
                             (self.state.project_id,))
        chname = (chrow["name"] if chrow else "") or ""
        self.status.setText("✍ AI đang viết caption + hashtag...")
        out: list = []

        def bg():
            try:
                from app.ai import social
                out.append(("ok", social.write_post(
                    c["title"] or "", text, tr.get("language", ""), chname)))
            except Exception as e:  # noqa: BLE001
                out.append(("err", str(e)))

        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop()
            kind, val = out[0]
            if kind == "err":
                self.status.setText("Viết caption lỗi.")
                QMessageBox.warning(self, "AI viết caption lỗi", str(val)[:400])
                return
            self.status.setText("✓ Đã viết xong caption.")
            self._show_caption_dialog(c, val)

        timer.timeout.connect(poll)
        timer.start(200)

    def _show_caption_dialog(self, c, post):
        from app.ai.social import format_post
        dlg = QDialog(self)
        dlg.setWindowTitle("Caption đăng bài: " + (c["title"] or "clip"))
        dlg.resize(560, 460)
        v = QVBoxLayout(dlg)
        hint = QLabel("Sửa thoải mái rồi bấm <b>Copy</b> — dán thẳng vào ô đăng "
                      "TikTok/Reels/Shorts.")
        hint.setWordWrap(True); v.addWidget(hint)
        box = QPlainTextEdit(); box.setPlainText(format_post(post))
        v.addWidget(box, 1)
        row = QHBoxLayout(); row.addStretch(1)
        if c["export_path"]:
            sv = QPushButton("Lưu .txt cạnh clip"); sv.setProperty("ghost", True)

            def save_txt():
                try:
                    p = Path(c["export_path"]).with_suffix(".txt")
                    p.write_text(box.toPlainText(), encoding="utf-8")
                    self.status.setText(f"Đã lưu caption: {p}")
                except OSError as e:
                    QMessageBox.warning(dlg, "Không lưu được", str(e))
            sv.clicked.connect(save_txt)
            row.addWidget(sv)
        cp = QPushButton("Copy"); cp.setProperty("primary", True)

        def do_copy():
            QApplication.clipboard().setText(box.toPlainText())
            cp.setText("Đã copy ✓")
        cp.clicked.connect(do_copy)
        row.addWidget(cp)
        cl = QPushButton("Đóng"); cl.clicked.connect(dlg.accept); row.addWidget(cl)
        v.addLayout(row)
        dlg.exec()

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
        # LOGO kênh (nếu mẫu có) — vẽ cùng PNG lớp chữ
        logo = None
        lp = self.layout_tpl.get("logo_path", "")
        if lp and os.path.exists(lp):
            logo = {"path": lp,
                    "pos": self.layout_tpl.get("logo_pos", "tr"),
                    "size": float(self.layout_tpl.get("logo_size", 0.14)),
                    "opacity": float(self.layout_tpl.get("logo_op", 0.9))}
        if (not layers and not logo) or not pid:
            return None
        # mỗi clip 1 PNG riêng (theo cid) vì tiêu đề khác nhau — để trong _cache
        png = os.path.join(services.project_cache_dir(pid),
                           f"_ovl_{cid or part_no}.png")
        return (png if render_overlay_png(
            layers, part_no, 1080, 1920, png, title, title_vi, video_px,
            logo=logo,
            # KIỂU CHỮ HOA lớp overlay (từ mẫu): Part -> part_case; tiêu đề/
            # hook/cố định -> hook_case.
            part_case=self.layout_tpl.get("part_case", "") or "",
            hook_case=self.layout_tpl.get("hook_case", "") or "")
                else None)

    _MUSIC_EXT = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac")

    def _pick_bgm(self) -> str:
        """Chọn file NHẠC NỀN theo mẫu: '' = không nhạc.
        random = mỗi clip 1 bài ngẫu nhiên từ thư mục nhạc của user."""
        mode = self.layout_tpl.get("bgm_mode", "off")
        if mode == "fixed":
            f = self.layout_tpl.get("bgm_file", "")
            return f if f and os.path.exists(f) else ""
        if mode == "random":
            d = self.layout_tpl.get("bgm_dir", "")
            try:
                files = [str(p) for p in Path(d).iterdir()
                         if p.suffix.lower() in self._MUSIC_EXT]
            except OSError:
                return ""
            import random
            return random.choice(files) if files else ""
        return ""

    def _pick_sfx_dir(self) -> str:
        """Thư mục tiếng động chuyển đoạn của user (tùy chọn). '' = dùng bộ
        tiếng TỔNG HỢP đa dạng trong ffmpeg. Chỉ trả khi thư mục tồn tại (việc
        chọn file ngẫu nhiên/validate để ffmpeg_utils lo, an toàn fallback)."""
        d = self.layout_tpl.get("fx_sfx_dir", "") or ""
        return d if d and os.path.isdir(d) else ""

    def _video_hashtags(self, video_id, clips) -> str:
        """Sinh 3-4 hashtag (đúng ngôn ngữ nội dung) CHUNG cho MỌI Part của video.

        Sinh 1 LẦN/video rồi cache theo video_id -> mọi part dùng chung, không
        tốn nhiều lượt LLM. Không có key / lỗi -> trả '' (tên file bỏ hashtag).
        Trả chuỗi có sẵn khoảng trắng đầu, vd ' #a #b #c'; '' nếu không có.
        """
        if video_id in self._hashtag_cache:
            return self._hashtag_cache[video_id]
        tags_str = ""
        try:
            from app.ai import llm as _llm, social
            from app.core.analysis import get_analysis
            if _llm.is_configured():
                tr = get_analysis(video_id, "transcript") or {}
                lang = tr.get("language", "") or ""
                # tiêu đề tổng + lời thoại: gom transcript các clip (đại diện video)
                title = ""
                text = ""
                for c in clips:
                    if not title:
                        title = (c["title"] or "").strip()
                    t = (c["transcript"] or "").strip()
                    if t:
                        text += " " + t
                if not text.strip():
                    text = " ".join(s.get("text", "")
                                    for s in tr.get("segments", []))
                tags = social.write_hashtags(title, text, lang, max_tags=4)
            else:
                tags = []
        except Exception:  # noqa: BLE001 - lỗi/không key -> bỏ hashtag, không sập
            tags = []
        # _safe_name sẽ chạy trên toàn out_name ở export_clip; ở đây chỉ ghép
        if tags:
            tags_str = " " + " ".join(t for t in tags if t)
        self._hashtag_cache[video_id] = tags_str
        return tags_str

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
        # KHO 'Đã xuất' / <tên KÊNH> / <tên video> -> không lẫn giữa các kênh
        chrow = db.query_one("SELECT name FROM projects WHERE id=?", (pid,))
        import re as _re
        chname = _re.sub(r'[<>:"/\\|?*]', "_",
                         ((chrow["name"] if chrow else "") or "Kenh"))
        chname = chname.strip().strip(". ") or "Kenh"   # bỏ chấm/cách cuối (Windows kỵ)
        out_root = str(self._export_root() / chname)
        vr = self.layout_tpl.get("video_rect")
        bg = self.layout_tpl.get("bg", "blur")
        tb = self.layout_tpl.get("trim_black", False)
        vpx = self._video_px_for(vrow)
        # HASHTAG chung cho MỌI Part của video (sinh 1 lần, cache theo video_id)
        tags_str = self._video_hashtags(video_id, clips)
        n = 0
        jids = []
        # Xuất 1 clip cụ thể ('Xuất lại'/'Xuất clip này') = user CHỦ ĐỘNG muốn
        # file mới -> ép xuất lại kể cả job cũ đã done (vd file bị xóa tay).
        force_one = bool(only_clip_id)
        for i, c in enumerate(clips):
            no = i + 1                         # số Part = vị trí trong video này
            if only_clip_id and c["id"] != only_clip_id:
                continue
            sig = db.loads(c["signals"], {}) or {}
            vi = (c["title"] or "").strip()
            en = ((sig.get("title_en") or vi)).strip()
            label = en or vi or self._fixed_label()
            # tên gọn "Part 1 <tiêu đề> #tag1 #tag2" — hashtag CHUNG toàn video,
            # đúng ngôn ngữ nội dung. _safe_name ở export_clip giữ '#'/ký tự có dấu.
            out_name = f"Part {no} {label}".strip() + tags_str
            jid = services.enqueue_export(
                self.state.pool, c["id"], video_id, pid,
                out_dir=out_root,   # <gốc>/Đã xuất/<KÊNH>/<video>/Part N.mp4
                video_rect=vr, bg=bg, trim_black=tb, part_no=no, out_name=out_name,
                captions=bool(self.layout_tpl.get("captions", True)),
                cap_style={
                    "font": self.layout_tpl.get("cap_font", "Anton"),
                    "size": self.layout_tpl.get("cap_size", 0),
                    "color": self.layout_tpl.get("cap_color", ""),
                    # màu viền / độ dày viền TÙY CHỌN cho phụ đề gốc (Chỉnh mẫu
                    # khu Phụ đề); ''/0 -> theo preset.
                    "cap_outline": self.layout_tpl.get("cap_outline", "") or "",
                    "cap_ow": float(self.layout_tpl.get("cap_ow", 0.0) or 0.0),
                    "ny": self.layout_tpl.get("cap_ny", 0.78),
                    "preset": self.layout_tpl.get("cap_preset",
                                                  "Trắng đơn giản"),
                    "delay": self.layout_tpl.get("cap_delay", 0.12),
                    "hook_on": self.layout_tpl.get("cap_hook", False),
                    "hook_dur": self.layout_tpl.get("cap_hook_dur", 6.0),
                    # vị trí/cỡ ô HOOK user kéo trong Chỉnh mẫu
                    "hook_nx": self.layout_tpl.get("hook_nx", 0.5),
                    "hook_ny": self.layout_tpl.get("hook_ny", 0.10),
                    "hook_size": self.layout_tpl.get("hook_size", 0.0),
                    # 🎙 CHỮ AI ĐỌC (thuyết minh) — từ MẪU (Chỉnh mẫu), chỉ
                    # ảnh hưởng cue narrate (Style Narrate) của clip recap;
                    # clip thường / đoạn gốc bỏ qua.
                    "narr_color": self.layout_tpl.get("narr_color", ""),
                    "narr_outline": self.layout_tpl.get("narr_outline", "")
                    or "",
                    "narr_ow": float(self.layout_tpl.get("narr_ow", 0.0)
                                     or 0.0),
                    # KIỂU chạy chữ RIÊNG cho chữ AI ('(giống phụ đề gốc)' =
                    # Style Default). narr_same giữ cho tương thích.
                    "narr_preset": self.layout_tpl.get("narr_preset", "") or "",
                    "narr_italic": bool(self.layout_tpl.get("narr_italic", True)),
                    "narr_same": bool(self.layout_tpl.get("narr_same", False)),
                    "narr_ny": float(self.layout_tpl.get("narr_ny", 0.0) or 0.0),
                    "narr_size": float(self.layout_tpl.get("narr_size", 0.0)
                                       or 0.0),
                    # KIỂU CHỮ HOA từng phần (từ mẫu)
                    "cap_case": self.layout_tpl.get("cap_case", "") or "",
                    "narr_case": self.layout_tpl.get("narr_case", "") or "",
                    "hook_case": self.layout_tpl.get("hook_case", "") or ""},
                blur_amt=int(self.layout_tpl.get("blur_amt", 22)),
                speed=float(sig.get("speed", self.layout_tpl.get("speed", 1.0))),
                pitch=float(self.layout_tpl.get("pitch", 1.0)),
                hook_first=bool(self.layout_tpl.get("hook_first")),
                bgm_path=self._pick_bgm(),
                bgm_vol=float(self.layout_tpl.get("bgm_vol", 0.15)),
                orig_vol=float(self.layout_tpl.get("orig_vol", 1.0)),
                dub_lang=self.layout_tpl.get("dub_lang", "") or "",
                dub_voice=self.layout_tpl.get("dub_voice", "") or "",
                dub_mute=bool(self.layout_tpl.get("dub_mute", False)),
                dub_mode=self.layout_tpl.get("dub_mode", "natural") or "natural",
                # 🎙 giọng + nhịp KỂ từ ⚙ Cài đặt Reup (toàn cục, KHÔNG theo
                # mẫu) — chỉ clip có signals.recap dùng; clip thường bỏ qua
                recap_voice=str(self._settings.value("recap_voice", "") or ""),
                recap_pace=str(self._settings.value("recap_pace", "normal")
                               or "normal"),
                recap_pitch=str(self._settings.value("recap_pitch", "normal")
                                or "normal"),
                # 🎭 emotion: BẬT + giọng ElevenLabs -> model v3 đọc audio
                # tag; ảnh hưởng model TTS -> vào sig dedup (đổi -> xuất lại).
                recap_emotion=str(
                    self._settings.value("recap_emotion", True)).strip()
                .lower() not in ("false", "0", "no", "off"),
                recap_volume=self._recap_volume(),
                # (CHỮ AI ĐỌC giờ lấy từ MẪU qua cap_style, không còn ở ⚙)
                fx_fade=bool(self.layout_tpl.get("fx_fade", True)),
                fx_whoosh=bool(self.layout_tpl.get("fx_whoosh", True)),
                fx_sfx_dir=self._pick_sfx_dir(),
                flip_h=bool(self.layout_tpl.get("flip_h", False)),
                fit_src=bool(self.layout_tpl.get("fit_src", False)),
                overlay_png=self._render_png(no, en, c["id"], vi, vpx, pid),
                force=force_one)
            if jid:
                jids.append(jid)
            n += 1
            QApplication.processEvents()   # nhả cho UI đỡ đơ khi vẽ ảnh chữ hàng loạt
        if n and not jids:
            # mọi clip đều bị smart-skip (đã xuất y hệt trước đó) -> BÁO RÕ,
            # không để user chờ file mới mà không có job nào chạy
            self.status.setText(
                "Các clip này đã xuất trước đó (không đổi gì) — không tạo job "
                "mới. Muốn xuất lại 1 clip: bấm 'Xuất lại' ở clip đó.")
        return len(jids)

    def _export_all(self):
        """Tải tất cả clip của VIDEO đang chọn (theo Part)."""
        if not self.state.video_id:
            return
        if not services.list_clips(self.state.video_id):
            QMessageBox.information(self, "Chưa có clip",
                                    "Bấm nút 'Tạo clip' để AI cắt clip trước.")
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
                                    "Kênh chưa có clip nào. Bấm 'Tất cả video' "
                                    "để tạo clip cho cả kênh trước.")

    def _open_dir(self):
        # mở KHO 'Đã xuất' (theo thư mục gốc hiện tại). Nếu đang chọn video ->
        # mở thẳng thư mục con của video đó. Tên folder phải làm sạch Y HỆT lúc
        # xuất (_export_video + m1_highlight._safe_name) kẻo mở trượt sang cha.
        base = self._export_root()
        target = base
        import re
        # mở thẳng folder KÊNH đang chọn nếu có (sạch tên GIỐNG _export_video)
        if self.state.project_id:
            chrow = db.query_one("SELECT name FROM projects WHERE id=?",
                                 (self.state.project_id,))
            ch = re.sub(r'[<>:"/\\|?*]', "_",
                        ((chrow["name"] if chrow else "") or "Kenh"))
            ch = ch.strip().strip(". ") or "Kenh"
            if (base / ch).is_dir():
                target = base / ch
        if self.state.video_id:                     # có video -> vào sâu folder video
            vrow = db.query_one("SELECT src_path FROM videos WHERE id=?",
                                (self.state.video_id,))
            if vrow and vrow["src_path"]:
                # folder video đặt tên bằng _safe_name lúc xuất -> dùng đúng hàm đó
                from app.modules.m1_highlight import _safe_name
                stem = (_safe_name(Path(vrow["src_path"]).stem)
                        or f"video_{self.state.video_id}")
                sub = target / stem
                if sub.is_dir():
                    target = sub
        try:
            os.startfile(str(target))  # noqa: S606
        except Exception:  # noqa: BLE001
            pass

    def _open_file(self, p):
        if p and os.path.isfile(p):
            os.startfile(p)  # noqa: S606
