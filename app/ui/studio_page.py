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
    ACCENT, BASE, BORDER, DANGER, ELEV, MUTED, SUCCESS, SURFACE, TEXT, WARN,
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


class _ChanCombo(QComboBox):
    """Combo có đuôi trạng thái (dùng cho cả Kênh lẫn Video): NGAY TRƯỚC khi
    mở dropdown gọi callback refresh đuôi từng item ('Tên · 🟢3 · ✅12ph' /
    'Tên.mp4 · 🟢 đang cắt') — userData (project_id/video_id) giữ nguyên."""
    on_popup = None            # gán từ ngoài: callable không tham số

    def showPopup(self):
        cb = self.on_popup
        if cb:
            try:
                cb()
            except Exception:  # noqa: BLE001 - đuôi trạng thái lỗi không chặn mở
                pass
        super().showPopup()


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

        # ===== Hàng 1: chọn NHÓM + KÊNH + VIDEO =====
        srcrow = QHBoxLayout(); srcrow.setSpacing(8)
        # combo NHÓM kênh (user reup hàng chục kênh nhiều quốc gia -> lọc
        # combo Kênh theo nhóm cho đỡ dài). Kênh chưa nhóm ở 'Chưa phân nhóm'.
        srcrow.addWidget(self._tag("Nhóm"))
        self.grp = QComboBox(); self.grp.setMinimumWidth(110)
        self.grp.setToolTip("Lọc kênh theo NHÓM (quốc gia, chủ đề...).\n"
                            "Kênh chưa gán nhóm hiện ở mục 'Chưa phân nhóm'.\n"
                            "Tạo / sửa / xoá nhóm và chuyển KÊNH sang nhóm khác "
                            "(hàng loạt): bấm nút ⚙ Quản lý nhóm bên cạnh.")
        # DỒN kênh chưa nhóm vào 'Mỹ' 1 LẦN (bỏ 'Tất cả' -> mọi kênh phải nằm
        # trong 1 nhóm; các dự án làm dở grp='' gom về 'Mỹ'). Chạy TRƯỚC
        # _reload_groups để combo nạp ngay danh sách đúng.
        self._migrate_default_group()
        self._reload_groups(self._settings.value("chan_group", "") or "")
        self.grp.currentIndexChanged.connect(self._on_grp)
        self.grp.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grp.customContextMenuRequested.connect(self._grp_menu)
        srcrow.addWidget(self.grp)
        gman = QPushButton("⚙"); gman.setProperty("ghost", True)
        gman.setFixedWidth(38)
        gman.setToolTip("Quản lý nhóm & kênh: thêm/sửa/xoá nhóm, chuyển nhiều "
                        "kênh sang nhóm khác cùng lúc.")
        gman.clicked.connect(self._manage_groups)
        srcrow.addWidget(gman)
        srcrow.addWidget(self._tag("Kênh"))
        self.proj = _ChanCombo(); self.proj.setMinimumWidth(180)
        self.proj.on_popup = self._refresh_proj_marks
        self.proj.setToolTip("Mỗi kênh = 1 thư mục riêng. Clip xuất vào đúng thư mục "
                             "kênh.\nChuột phải để SỬA TÊN / XÓA kênh.")
        self.proj.currentIndexChanged.connect(self._on_proj)
        self.proj.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.proj.customContextMenuRequested.connect(self._proj_menu)
        srcrow.addWidget(self.proj)
        np = QPushButton("+ Kênh"); np.setProperty("ghost", True)
        np.clicked.connect(self._new_proj); srcrow.addWidget(np)
        ren = QPushButton("✏"); ren.setProperty("ghost", True)
        ren.setFixedWidth(38)
        ren.setToolTip("Sửa tên kênh đang chọn (tạo sai tên sửa lại được).\n"
                       "Lưu ý: clip xuất MỚI sẽ vào thư mục theo tên mới.")
        # lambda: clicked truyền checked=False -> đừng để lọt vào tham số pid
        ren.clicked.connect(lambda: self._rename_proj())
        srcrow.addWidget(ren)
        dash = QPushButton("📊"); dash.setProperty("ghost", True)
        dash.setFixedWidth(38)
        dash.setToolTip("Tình hình các kênh: đang chạy / đợi / lỗi 24h / "
                        "xong gần nhất / số clip đã xuất.")
        dash.clicked.connect(self._channel_dashboard); srcrow.addWidget(dash)
        self.lib_btn = QPushButton("Kho video"); self.lib_btn.setProperty("ghost", True)
        self.lib_btn.clicked.connect(self._pick_lib_root); srcrow.addWidget(self.lib_btn)
        self._update_lib_tooltip()   # tooltip hiện ĐƯỜNG DẪN kho đang dùng
        srcrow.addSpacing(16)
        srcrow.addWidget(self._tag("Video"))
        self.vid = _ChanCombo(); self.vid.setMinimumWidth(200)
        self.vid.on_popup = self._refresh_vid_marks   # mở dropdown -> đuôi mới
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
        # NHÃN hoạt động của KÊNH ĐANG CHỌN (user chạy nhiều kênh cùng lúc,
        # cần biết kênh này đang chạy gì / vừa xong bao lâu ngay tại chỗ).
        self.chan_lbl = QLabel("")
        self.chan_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        plw.addWidget(self.chan_lbl)

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
        self._act_tick = 0     # nhãn kênh chỉ query mỗi 3 tick (~4.5s) cho nhẹ
        self.timer.timeout.connect(self._poll_chan_activity)
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

    # ---- NHÓM kênh (lọc combo Kênh theo projects.grp) ----
    def _migrate_default_group(self) -> None:
        """MIGRATION 1 LẦN (guard QSettings 'grp_default_done'): mọi kênh đang
        grp='' (dự án làm dở, chưa phân nhóm) -> gom vào nhóm 'Mỹ' + thêm 'Mỹ'
        vào nhóm rỗng đã lưu. Đặt cờ để KHÔNG chạy lại — nếu về sau user cố ý
        gỡ 1 kênh khỏi nhóm (grp='') thì nó ở lại 'Chưa phân nhóm', không bị
        kéo về 'Mỹ' nữa. DB TRỐNG (chưa kênh nào) vẫn set cờ + thêm 'Mỹ' để
        khi tạo kênh đầu có nhóm sẵn."""
        try:
            done = str(self._settings.value("grp_default_done", "")).strip()
        except Exception:  # noqa: BLE001
            done = ""
        if done in ("1", "true", "True", "yes"):
            return
        try:
            rows = db.query("SELECT id FROM projects WHERE grp='' OR grp IS NULL")
            for r in rows:
                services.set_project_group(int(r["id"]), "Mỹ")
            # 'Mỹ' luôn có mặt trong combo kể cả khi DB trống (nhóm rỗng đã tạo)
            self._save_extra_groups(self._extra_groups() + ["Mỹ"])
        except Exception:  # noqa: BLE001 - DB lỗi hiếm -> đừng chặn mở app
            return
        self._settings.setValue("grp_default_done", "1")

    def _cur_group(self) -> str:
        """Nhóm đang chọn ở combo Nhóm. Item 'Chưa phân nhóm' mang data=''
        -> trả '' (list_projects('') = kênh chưa nhóm). Không còn 'Tất cả'."""
        g = getattr(self, "grp", None)
        if g is None:
            return ""
        d = g.currentData()
        return d if isinstance(d, str) else ""

    def _extra_groups(self) -> list:
        """Nhóm user TỰ TẠO còn RỖNG (chưa có kênh) — lưu QSettings để không
        biến mất khi nạp lại (nhóm có kênh thì tự có mặt qua DB)."""
        import json
        try:
            v = json.loads(self._settings.value("chan_groups_extra", "") or "[]")
            return [str(x) for x in v if str(x).strip()]
        except Exception:  # noqa: BLE001
            return []

    def _save_extra_groups(self, lst) -> None:
        import json
        self._settings.setValue(
            "chan_groups_extra", json.dumps(sorted(set(lst)), ensure_ascii=False))

    def _reload_groups(self, select: str = ""):
        """Nạp combo Nhóm CHỈ ĐỂ LỌC — KHÔNG còn 'Tất cả' (thừa) và KHÔNG dòng
        lệnh (＋/✏/🗑, đã chuyển sang dialog '⚙ Quản lý nhóm'). Danh sách =
        các nhóm (DB ∪ nhóm rỗng đã tạo), sort a-z.
        CHỐNG TÀNG HÌNH: nếu CÒN kênh grp='' (vd user vừa dissolve 1 nhóm) ->
        chèn item 'Chưa phân nhóm' (data='') ở ĐẦU để kênh đó vẫn thấy được;
        hết kênh '' thì KHÔNG hiện item này.
        CHỌN MẶC ĐỊNH: `select` nếu CÒN tồn tại; không thì item ĐẦU tiên (không
        còn 'Tất cả' để rơi về). Ghi QSettings để mở app lại vào đúng nhóm."""
        self.grp.blockSignals(True)
        self.grp.clear()
        has_ungrouped = bool(services.list_projects(""))
        if has_ungrouped:
            self.grp.addItem("Chưa phân nhóm", "")
        names = sorted(set(services.list_groups()) | set(self._extra_groups()))
        for g in names:
            self.grp.addItem(g, g)
        # select='' chỉ khớp item 'Chưa phân nhóm' (nếu có); nhóm tên khớp theo
        # data. Không tìm thấy -> item đầu tiên (index 0).
        i = self.grp.findData(select)
        self.grp.setCurrentIndex(i if i >= 0 else 0)
        self.grp.blockSignals(False)
        self._settings.setValue("chan_group", self._cur_group())

    def _on_grp(self, _i):
        # dropdown giờ CHỈ lọc — không còn dòng lệnh. Lưu nhóm đang chọn để
        # mở app lại giữ nguyên + nạp lại danh sách kênh theo nhóm.
        self._settings.setValue("chan_group", self._cur_group())
        self._reload_projects()

    def _grp_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        g = self._cur_group()
        m = QMenu(self)
        a1 = m.addAction("✏ Sửa tên nhóm...")
        a1.setEnabled(bool(g))
        a1.triggered.connect(lambda: self._rename_group())
        a2 = m.addAction("🗑 Xoá nhóm này...")
        a2.setEnabled(bool(g))
        a2.triggered.connect(lambda: self._del_group())
        m.exec(self.grp.mapToGlobal(pos))

    def _rename_group(self):
        """Đổi tên nhóm ĐANG CHỌN: mọi kênh trong nhóm đi theo tên mới; tên
        mới trùng nhóm sẵn có -> GỘP 2 nhóm (hỏi trước)."""
        old = self._cur_group()
        if not old:
            return
        new, ok = QInputDialog.getText(
            self, "Sửa tên nhóm", f"Tên mới cho nhóm “{old}”:", text=old)
        new = (new or "").strip()
        if not ok or not new or new == old:
            return
        if new in set(services.list_groups()) | set(self._extra_groups()):
            if QMessageBox.question(
                self, "Gộp nhóm",
                f"Nhóm “{new}” đã tồn tại — GỘP mọi kênh của “{old}” vào "
                f"“{new}”?") != QMessageBox.StandardButton.Yes:
                return
        err = services.rename_group(old, new)
        if err:
            QMessageBox.warning(self, "Không đổi được", err)
            return
        # cập nhật danh sách nhóm rỗng đã lưu (old -> new)
        self._save_extra_groups(
            [new if x == old else x for x in self._extra_groups()])
        self._reload_groups(new)
        self._reload_projects()
        self.status.setText(f"Đã đổi nhóm “{old}” → “{new}”.")

    def _del_group(self):
        """Xoá nhóm ĐANG CHỌN theo ý muốn: kênh trong nhóm KHÔNG mất — chỉ về
        'Chưa phân nhóm' (item cùng tên xuất hiện ở đầu combo). Hỏi xác nhận
        nếu nhóm còn kênh."""
        g = self._cur_group()
        if not g:
            return
        n = len(services.list_projects(g))
        if n and QMessageBox.question(
            self, "Xoá nhóm",
            f"Nhóm “{g}” đang có {n} kênh. Xoá nhóm sẽ đưa {n} kênh về "
            "'Chưa phân nhóm' (KHÔNG xoá kênh/video/clip nào). Tiếp tục?"
        ) != QMessageBox.StandardButton.Yes:
            return
        services.dissolve_group(g)
        self._save_extra_groups([x for x in self._extra_groups() if x != g])
        self._reload_groups("")
        self._reload_projects()
        self.status.setText(
            f"Đã xoá nhóm “{g}”" + (f" — {n} kênh về 'Chưa phân nhóm'."
                                    if n else "."))

    # ---- Dialog QUẢN LÝ NHÓM & KÊNH (⚙ cạnh combo Nhóm) ----
    def _all_group_names(self) -> list:
        """Tên nhóm: DB (nhóm có kênh) ∪ nhóm rỗng đã tạo (QSettings), sort."""
        return sorted(set(services.list_groups()) | set(self._extra_groups()))

    def _manage_groups(self):
        """Mở dialog quản lý; đóng xong -> nạp lại combo Nhóm + kênh (giữ nhóm
        đang chọn nếu còn)."""
        keep = self._cur_group()
        self._build_manage_groups().exec()
        # nhóm đang chọn có thể vừa bị đổi tên/xoá -> chỉ giữ nếu còn
        if keep and keep not in self._all_group_names():
            keep = ""
        self._reload_groups(keep)
        self._reload_projects()

    def _build_manage_groups(self) -> QDialog:
        """QDialog 'Quản lý nhóm & kênh' — 2 khu:
        - KHU NHÓM: QListWidget các nhóm + [＋ Thêm] [✏ Sửa tên] [🗑 Xoá].
        - KHU KÊNH: QTableWidget [☑ | Tên kênh | Nhóm hiện tại] chọn nhiều dòng,
          dưới cùng chuyển các kênh đã tích vào 1 nhóm (hoặc 'Chưa phân nhóm').
        Tách khỏi exec() để test offscreen thao tác từng bước."""
        from PyQt6.QtWidgets import (QAbstractItemView, QHeaderView,
                                     QTableWidget, QTableWidgetItem)
        dlg = QDialog(self); dlg.setWindowTitle("Quản lý nhóm & kênh")
        dlg.resize(720, 520)
        self._mg_dlg = dlg                    # giữ ref cho test offscreen
        root = QHBoxLayout(dlg); root.setSpacing(12)
        root.setContentsMargins(14, 14, 14, 14)

        # ===== KHU 1: NHÓM =====
        left = QVBoxLayout(); left.setSpacing(8)
        h1 = QLabel("Nhóm")
        h1.setStyleSheet(f"color:{TEXT}; font-size:15px; font-weight:800;")
        left.addWidget(h1)
        s1 = QLabel("Nhóm để phân loại kênh (quốc gia, chủ đề...).")
        s1.setWordWrap(True); s1.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        left.addWidget(s1)
        glist = QListWidget(); glist.setMinimumWidth(220)
        self._mg_glist = glist
        left.addWidget(glist, 1)
        brow = QHBoxLayout(); brow.setSpacing(6)
        add_b = QPushButton("＋ Thêm nhóm"); add_b.setProperty("ghost", True)
        ren_b = QPushButton("✏ Sửa tên"); ren_b.setProperty("ghost", True)
        del_b = QPushButton("🗑 Xoá"); del_b.setProperty("ghost", True)
        brow.addWidget(add_b); brow.addWidget(ren_b); brow.addWidget(del_b)
        left.addLayout(brow)
        root.addLayout(left, 0)

        # ===== KHU 2: KÊNH =====
        right = QVBoxLayout(); right.setSpacing(8)
        h2 = QLabel("Kênh")
        h2.setStyleSheet(f"color:{TEXT}; font-size:15px; font-weight:800;")
        right.addWidget(h2)
        s2 = QLabel("Tích ô các kênh cần chuyển, chọn nhóm đích bên dưới rồi bấm "
                    "Chuyển. Nháy đúp 1 dòng để đổi nhanh nhóm dòng đó.")
        s2.setWordWrap(True); s2.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        right.addWidget(s2)
        tbl = QTableWidget(0, 4)
        self._mg_tbl = tbl
        tbl.setHorizontalHeaderLabels(
            ["", "Tên kênh", "Nhóm hiện tại", "Thư mục lưu"])
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        tbl.verticalHeader().setVisible(False)
        tbl.setStyleSheet(
            f"QTableWidget {{ background:{BASE}; border:1px solid {BORDER};"
            f" border-radius:8px; gridline-color:{BORDER}; color:{TEXT}; }}"
            f"QTableWidget::item {{ padding:3px 8px; }}"
            f"QTableWidget::item:selected {{ background:{ACCENT};"
            f" color:white; }}"
            f"QHeaderView::section {{ background:{SURFACE}; color:{TEXT};"
            f" padding:6px 8px; border:none;"
            f" border-bottom:1px solid {BORDER}; font-weight:600; }}"
            f"QTableCornerButton::section {{ background:{SURFACE};"
            f" border:none; }}")
        hh = tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        right.addWidget(tbl, 1)

        # hàng ĐẶT THƯ MỤC LƯU RIÊNG cho (các) kênh đã chọn
        drow = QHBoxLayout(); drow.setSpacing(6)
        drow.addWidget(self._tag("Thư mục lưu riêng:"))
        setdir_b = QPushButton("📁 Đặt thư mục lưu...")
        setdir_b.setProperty("ghost", True)
        cleardir_b = QPushButton("Về mặc định")
        cleardir_b.setProperty("ghost", True)
        drow.addWidget(setdir_b); drow.addWidget(cleardir_b); drow.addStretch(1)
        right.addLayout(drow)

        # hàng chuyển hàng loạt
        mrow = QHBoxLayout(); mrow.setSpacing(6)
        mrow.addWidget(self._tag("Chuyển các kênh đã chọn vào:"))
        dest = QComboBox(); dest.setMinimumWidth(160)
        self._mg_dest = dest
        mrow.addWidget(dest, 1)
        move_b = QPushButton("Chuyển"); move_b.setProperty("primary", True)
        mrow.addWidget(move_b)
        right.addLayout(mrow)
        # nút dưới cùng
        frow = QHBoxLayout()
        refresh_b = QPushButton("Làm mới"); refresh_b.setProperty("ghost", True)
        frow.addWidget(refresh_b); frow.addStretch(1)
        close_b = QPushButton("Đóng"); close_b.setProperty("ghost", True)
        frow.addWidget(close_b)
        right.addLayout(frow)
        root.addLayout(right, 1)

        # ---- nạp dữ liệu ----
        def fill_groups(select: str = None):
            if select is None:
                cur = glist.currentItem()
                select = cur.text() if cur else None
            glist.blockSignals(True); glist.clear()
            for g in self._all_group_names():
                glist.addItem(g)
            glist.blockSignals(False)
            if select is not None:
                for i in range(glist.count()):
                    if glist.item(i).text() == select:
                        glist.setCurrentRow(i); break
            # combo nhóm đích: '(Chưa phân nhóm)' + các nhóm
            keep = dest.currentData()
            dest.blockSignals(True); dest.clear()
            dest.addItem("(Chưa phân nhóm)", "")
            for g in self._all_group_names():
                dest.addItem(g, g)
            di = dest.findData(keep) if isinstance(keep, str) else -1
            dest.setCurrentIndex(di if di > 0 else 0)
            dest.blockSignals(False)

        def fill_channels():
            projs = services.list_projects()          # TẤT CẢ kênh
            tbl.setRowCount(len(projs))
            for r, p in enumerate(projs):
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable
                             | Qt.ItemFlag.ItemIsEnabled
                             | Qt.ItemFlag.ItemIsSelectable)
                chk.setCheckState(Qt.CheckState.Unchecked)
                chk.setData(Qt.ItemDataRole.UserRole, int(p["id"]))
                tbl.setItem(r, 0, chk)
                nm = QTableWidgetItem(p["name"])
                nm.setData(Qt.ItemDataRole.UserRole, int(p["id"]))
                tbl.setItem(r, 1, nm)
                g = (p["grp"] or "").strip()
                tbl.setItem(r, 2, QTableWidgetItem(g or "· Chưa phân nhóm"))
                ed = (p["export_dir"] or "").strip()
                di = QTableWidgetItem(ed or "· mặc định (Đã xuất chung)")
                if ed:
                    di.setToolTip(ed)
                tbl.setItem(r, 3, di)

        def refill():
            fill_groups()
            fill_channels()

        refill()

        # ---- KHU NHÓM: thêm / sửa / xoá ----
        def add_group():
            name, ok = QInputDialog.getText(
                dlg, "Thêm nhóm", "Tên nhóm mới (vd: Mỹ, Nhật, Hàn...):")
            name = (name or "").strip()
            if not ok or not name:
                return
            if name in self._all_group_names():
                QMessageBox.information(dlg, "Đã có", f"Nhóm “{name}” đã tồn tại.")
                return
            # nhóm RỖNG -> lưu QSettings (chưa có kênh nào)
            self._save_extra_groups(self._extra_groups() + [name])
            fill_groups(name)

        def rename_group():
            it = glist.currentItem()
            if it is None:
                QMessageBox.information(dlg, "Chưa chọn", "Chọn 1 nhóm để sửa tên.")
                return
            old = it.text()
            new, ok = QInputDialog.getText(
                dlg, "Sửa tên nhóm", f"Tên mới cho nhóm “{old}”:", text=old)
            new = (new or "").strip()
            if not ok or not new or new == old:
                return
            if new in self._all_group_names():
                if QMessageBox.question(
                    dlg, "Gộp nhóm",
                    f"Nhóm “{new}” đã tồn tại — GỘP mọi kênh của “{old}” vào "
                    f"“{new}”?") != QMessageBox.StandardButton.Yes:
                    return
            err = services.rename_group(old, new)
            if err:
                QMessageBox.warning(dlg, "Không đổi được", err)
                return
            self._save_extra_groups(
                [new if x == old else x for x in self._extra_groups()])
            refill(); fill_groups(new)

        def del_group():
            it = glist.currentItem()
            if it is None:
                QMessageBox.information(dlg, "Chưa chọn", "Chọn 1 nhóm để xoá.")
                return
            g = it.text()
            n = len(services.list_projects(g))
            if n and QMessageBox.question(
                dlg, "Xoá nhóm",
                f"Nhóm “{g}” đang có {n} kênh. Xoá nhóm sẽ đưa {n} kênh về "
                "'Chưa phân nhóm' (KHÔNG xoá kênh/video/clip nào). Tiếp tục?"
            ) != QMessageBox.StandardButton.Yes:
                return
            services.dissolve_group(g)
            self._save_extra_groups([x for x in self._extra_groups() if x != g])
            refill()

        # ---- KHU KÊNH: chuyển hàng loạt / nháy đúp ----
        def move_checked():
            g = dest.currentData()
            g = g if isinstance(g, str) else ""
            ids = []
            for r in range(tbl.rowCount()):
                c = tbl.item(r, 0)
                if c and c.checkState() == Qt.CheckState.Checked:
                    ids.append(int(c.data(Qt.ItemDataRole.UserRole)))
            if not ids:
                QMessageBox.information(
                    dlg, "Chưa chọn kênh", "Tích ô các kênh cần chuyển trước.")
                return
            for pid in ids:
                services.set_project_group(pid, g)
            refill()

        def _checked_or_selected_ids():
            """ID kênh: ưu tiên ô ĐÃ TÍCH; không tích nào -> dòng đang chọn."""
            ids = []
            for r in range(tbl.rowCount()):
                c = tbl.item(r, 0)
                if c and c.checkState() == Qt.CheckState.Checked:
                    ids.append(int(c.data(Qt.ItemDataRole.UserRole)))
            if not ids:
                for r in {i.row() for i in tbl.selectedItems()}:
                    it = tbl.item(r, 1)
                    if it is not None:
                        ids.append(int(it.data(Qt.ItemDataRole.UserRole)))
            return ids

        def set_export_dir():
            ids = _checked_or_selected_ids()
            if not ids:
                QMessageBox.information(
                    dlg, "Chưa chọn kênh",
                    "Tích ô (hoặc chọn dòng) kênh cần đặt thư mục lưu trước.")
                return
            # gợi ý mở tại thư mục hiện có của kênh đầu tiên (nếu có)
            cur0 = services.project_export_dir(ids[0])
            d = QFileDialog.getExistingDirectory(
                dlg, "Chọn THƯ MỤC LƯU RIÊNG cho kênh "
                     "(clip cắt xong vào THẲNG đây)", cur0 or "")
            if not d:
                return
            for pid in ids:
                services.set_project_export_dir(pid, d)
            fill_channels()
            QMessageBox.information(
                dlg, "Đã đặt thư mục lưu",
                f"{len(ids)} kênh sẽ lưu clip THẲNG vào:\n{d}\n\n"
                "(Không tạo thư mục con theo tên video.)")

        def clear_export_dir():
            ids = _checked_or_selected_ids()
            if not ids:
                QMessageBox.information(
                    dlg, "Chưa chọn kênh",
                    "Tích ô (hoặc chọn dòng) kênh cần đưa về mặc định trước.")
                return
            for pid in ids:
                services.set_project_export_dir(pid, "")
            fill_channels()
            self.status.setText(
                f"{len(ids)} kênh về mặc định (lưu vào 'Đã xuất' chung).")

        def dbl(row, _col):
            it = tbl.item(row, 1)
            if it is None:
                return
            pid = int(it.data(Qt.ItemDataRole.UserRole))
            cur = services.project_group(pid)
            items = ["(Chưa phân nhóm)"] + self._all_group_names()
            cur_lbl = cur if cur else "(Chưa phân nhóm)"
            idx = items.index(cur_lbl) if cur_lbl in items else 0
            g, ok = QInputDialog.getItem(
                dlg, "Chuyển nhóm",
                "Nhóm (chọn có sẵn hoặc gõ tên MỚI):", items, idx, True)
            if not ok:
                return
            g = (g or "").strip()
            if g == "(Chưa phân nhóm)":
                g = ""
            if g == (cur or ""):
                return
            services.set_project_group(pid, g)
            refill()

        add_b.clicked.connect(add_group)
        ren_b.clicked.connect(rename_group)
        del_b.clicked.connect(del_group)
        move_b.clicked.connect(move_checked)
        setdir_b.clicked.connect(set_export_dir)
        cleardir_b.clicked.connect(clear_export_dir)
        refresh_b.clicked.connect(refill)
        close_b.clicked.connect(dlg.accept)
        tbl.cellDoubleClicked.connect(dbl)
        return dlg

    def _select_project(self, pid) -> None:
        """Chọn kênh `pid` trong combo Kênh. Nếu kênh KHÔNG thuộc nhóm đang
        lọc (vd nhảy từ 📊 sang kênh nhóm khác) -> tự chuyển combo Nhóm về
        nhóm của kênh đó để kênh hiện được — KHÔNG để combo trống/lệch."""
        if pid is None:
            return
        i = self.proj.findData(pid)
        if i < 0:
            self._reload_groups(services.project_group(int(pid)))
            self._reload_projects()
            i = self.proj.findData(pid)
        if i >= 0 and i != self.proj.currentIndex():
            self.proj.setCurrentIndex(i)

    # ---- kênh (project) / video ----
    def _reload_projects(self):
        grp = self._cur_group()
        self.proj.blockSignals(True); self.proj.clear()
        # TÊN GỐC từng kênh (không đuôi trạng thái) — text item có thể mang đuôi
        # '· 🟢3' nên MỌI chỗ cần tên kênh phải lấy từ đây/DB, ĐỪNG currentText()
        self._proj_names = {}
        for p in services.list_projects(grp or None):
            self._proj_names[int(p["id"])] = p["name"]
            self.proj.addItem(p["name"], p["id"])
        self.proj.blockSignals(False)
        if self.proj.count():
            self._on_proj(self.proj.currentIndex())
        elif grp:
            # nhóm đang lọc KHÔNG có kênh (nhóm mới trống) -> không popup tạo
            # kênh; dọn trạng thái + gợi ý ('+ Kênh' bây giờ tạo vào nhóm này)
            self.state.project_id = None
            self.state.video_id = None
            self.vid.blockSignals(True); self.vid.clear()
            self.vid.blockSignals(False)
            self._refresh_chan_label()
            self.status.setText(f"Nhóm “{grp}” chưa có kênh — bấm + Kênh để thêm.")
        else:
            self._new_proj(first=True)

    def _del_proj(self):
        pid = self.proj.currentData()
        if pid is None:
            return
        # tên từ DB, KHÔNG currentText() — text combo có thể mang đuôi '· 🟢3'
        row = db.query_one("SELECT name FROM projects WHERE id=?", (int(pid),))
        name = (row["name"] if row
                else getattr(self, "_proj_names", {}).get(int(pid), ""))
        if QMessageBox.question(
            self, "Xóa kênh",
            f"Xóa kênh “{name}” (cả video, clip, file đã xuất)? Không hoàn tác được."
        ) == QMessageBox.StandardButton.Yes:
            services.delete_project(int(pid), self.state.pool)
            self.state.project_id = None
            self._reload_groups(self._cur_group())  # nhóm có thể vừa hết kênh
            self._reload_projects()
            self.status.setText(f"Đã xóa kênh “{name}”.")

    def _ai_settings(self):
        """Hộp thoại chọn nguồn AI (máy/Gemini) + nhập key + chọn model + kiểm tra."""
        from PyQt6.QtWidgets import QApplication
        from config import settings, Settings, update_env
        from app.ai import llm
        dlg = QDialog(self); dlg.setWindowTitle("Cài đặt AI")
        # NHIỀU mục (Gemini/Groq/file key/ElevenLabs/trạng thái key) -> nội dung
        # DÀI hơn màn hình -> CUỘN được + cao vừa màn hình + nút Lưu GHIM dưới
        # (trước đây tràn màn hình, che mất nút Lưu/Kiểm tra).
        from PyQt6.QtWidgets import QFrame, QScrollArea, QWidget
        _outer = QVBoxLayout(dlg); _outer.setContentsMargins(0, 0, 0, 0)
        _outer.setSpacing(0)
        _scroll = QScrollArea(); _scroll.setWidgetResizable(True)
        _scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        _outer.addWidget(_scroll, 1)
        _content = QWidget(); _scroll.setWidget(_content)
        lay = QVBoxLayout(_content); lay.setSpacing(12)
        lay.setContentsMargins(18, 16, 18, 16)
        try:
            _sh = self.screen().availableGeometry().height()
        except Exception:  # noqa: BLE001
            _sh = 800
        dlg.resize(580, min(720, max(460, int(_sh) - 90)))

        # ---- Tiêu đề dialog + mô tả ngắn ----
        _hdr = QLabel("Cài đặt AI")
        _hdr.setStyleSheet(f"color:{TEXT}; font-size:19px; font-weight:800;")
        lay.addWidget(_hdr)
        _sub = QLabel("Cấu hình AI cho toàn bộ app — dán key rồi bấm Kiểm tra.")
        _sub.setWordWrap(True)
        _sub.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(_sub)

        # ---- Nhà máy THẺ: QFrame bo góc 10px, nền nổi hơn nền dialog, viền mảnh,
        # có TIÊU ĐỀ (icon) + mô tả MUTED. Trả về body-layout để nhét control.
        def _card(title, desc=""):
            fr = QFrame()
            fr.setObjectName("aiCard")
            fr.setStyleSheet(
                f"#aiCard{{background:{ELEV}; border:1px solid {BORDER};"
                f"border-radius:10px;}}"
                f"#aiCard QLabel{{background:transparent;}}")
            cl = QVBoxLayout(fr)
            cl.setContentsMargins(15, 13, 15, 14)
            cl.setSpacing(9)
            t = QLabel(title)
            t.setStyleSheet(f"color:{TEXT}; font-size:14px; font-weight:700;")
            cl.addWidget(t)
            if desc:
                d = QLabel(desc); d.setWordWrap(True)
                d.setStyleSheet(f"color:{MUTED}; font-size:11px;")
                cl.addWidget(d)
            lay.addWidget(fr)
            return cl

        def _flabel(text):
            """Nhãn phụ (mô tả field) — MUTED nhỏ, canh sát control bên dưới."""
            x = QLabel(text); x.setWordWrap(True)
            x.setStyleSheet(f"color:{MUTED}; font-size:11px;")
            return x

        # ============ THẺ 1: 🧠 Bộ não AI ============
        c_brain = _card(
            "🧠 Bộ não AI",
            "Chọn AI viết kịch bản / chọn đoạn hay. Groq miễn phí, Gemini khôn "
            "nhất.")
        c_brain.addWidget(_flabel("Nguồn AI"))
        src = QComboBox()
        src.addItem("Groq — mây (FREE, khôn, nhẹ — khuyên dùng)", "groq")
        src.addItem("Gemini — mây (khôn nhất, có phí nhẹ)", "gemini")
        i = src.findData(settings.LLM_PROVIDER or "groq")
        src.setCurrentIndex(i if i >= 0 else 0)
        c_brain.addWidget(src)
        c_brain.addWidget(_flabel(
            "Gemini API key (nhiều key mỗi dòng 1 — tự xoay vòng khi hết lượt)"))
        key = QPlainTextEdit(settings.GEMINI_API_KEY or "")
        key.setPlaceholderText("Dán 1 hoặc NHIỀU key, mỗi dòng 1 key")
        key.setFixedHeight(60); c_brain.addWidget(key)
        c_brain.addWidget(_flabel("Model Gemini"))
        mdl = QComboBox()
        mdl.addItem("Gemini 2.5 Flash — nhanh, rẻ (khuyên)", "gemini-2.5-flash")
        mdl.addItem("Gemini 2.5 Pro — khôn nhất, chậm/đắt hơn", "gemini-2.5-pro")
        j = mdl.findData(settings.GEMINI_MODEL)
        mdl.setCurrentIndex(j if j >= 0 else 0)
        c_brain.addWidget(mdl)

        # ============ THẺ 2: 🔑 Key Groq ============
        c_groq = _card(
            "🔑 Key Groq",
            "Key Groq dùng cho AI (nếu chọn Groq) và nghe-chép lời trên mây. "
            "Lấy free tại console.groq.com/keys.")
        c_groq.addWidget(_flabel("Groq API key (nhiều key mỗi dòng 1)"))
        gkeys = QPlainTextEdit(settings.GROQ_API_KEYS or "")
        gkeys.setPlaceholderText("Để TRỐNG nếu chép lời bằng Máy")
        gkeys.setFixedHeight(50); c_groq.addWidget(gkeys)

        # ----- TRỎ FILE KEY (mỗi dòng 1 key) — cho HÀNG TRĂM key -----
        # Trạng thái đường dẫn file giữ trong 1 ô [list] để đóng closure sửa được.
        gfile = [settings.GROQ_KEYS_FILE or ""]
        gnote = QLabel("Dán vài key vào ô, hoặc trỏ file .txt cho HÀNG TRĂM key. "
                       "App gộp cả hai.")
        gnote.setWordWrap(True)
        gnote.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        c_groq.addWidget(gnote)
        gfrow = QHBoxLayout()
        gfbtn = QPushButton("📄 Chọn file key (mỗi dòng 1 key)")
        gfbtn.setProperty("ghost", True)
        gfclear = QPushButton("Bỏ"); gfclear.setProperty("ghost", True)
        gfrow.addWidget(gfbtn); gfrow.addWidget(gfclear); gfrow.addStretch(1)
        c_groq.addLayout(gfrow)
        gflbl = QLabel("")
        gflbl.setWordWrap(True)
        gflbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gflbl.setStyleSheet(f"color:{TEXT}; font-size:11px;")
        c_groq.addWidget(gflbl)

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

        # ----- GIẢI THÍCH hạn mức theo TÀI KHOẢN (không theo key) -----
        gwarn = QLabel(
            "⚠ Groq giới hạn theo TÀI KHOẢN, KHÔNG theo key — nhiều key CÙNG 1 "
            "nick dùng CHUNG hạn mức (không tăng). Muốn nhiều lượt hơn: tạo key "
            "từ NHIỀU nick khác nhau. Hạn mức reset mỗi ngày.")
        gwarn.setWordWrap(True)
        gwarn.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        c_groq.addWidget(gwarn)

        # ----- NÚT "KIỂM TRA TẤT CẢ KEY GROQ" (còn lượt/hết lượt/sai) -----
        # Chạy THREAD NỀN + ThreadPool(6): mỗi key gọi POST /chat/completions
        # max_tokens=1 -> ĐỌC HẠN MỨC THẬT còn lại (tốn ~1 lượt/key). Tiến độ +
        # tổng kết bắn về qua QTimer poll (không chặn UI). Gộp key ô dán + file.
        gckrow = QHBoxLayout()
        gckbtn = QPushButton("Kiểm tra key + hạn mức (tốn ~1 lượt/key)")
        gckbtn.setProperty("ghost", True)
        gckbtn.setToolTip("Đọc HẠN MỨC THẬT còn lại của từng key (còn bao nhiêu "
                          "request/token hôm nay) — phát hiện key HẾT LƯỢT dù "
                          "vẫn hợp lệ. Tốn ~1 lượt/key. Chạy song song, có tiến độ.")
        gckrow.addWidget(gckbtn); gckrow.addStretch(1)
        c_groq.addLayout(gckrow)
        gckstat = QLabel("")
        gckstat.setObjectName("groq_check_label")
        gckstat.setWordWrap(True)
        gckstat.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gckstat.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        c_groq.addWidget(gckstat)
        # nút xoá key chết khỏi ô dán (chỉ hiện khi có key 401)
        gckdel = QPushButton("Xoá key chết khỏi ô dán")
        gckdel.setProperty("ghost", True)
        gckdel.setVisible(False)
        c_groq.addWidget(gckdel)

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
                        keys, progress=prog, max_workers=6)
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
                tot = r.get("total_remaining_requests", 0)
                summary = (
                    f"✅ Còn lượt: {c['ok']} · ⏳ Hết lượt hôm nay: "
                    f"{c.get('exhausted', 0)} · ❌ Sai: {c['invalid']} · "
                    f"⚠ Lỗi: {c['error']} · Tổng còn ~{tot} request")
                # vài dòng chi tiết từng key kèm hạn mức còn lại
                lines = []
                for k, info in r.get("results", [])[:8]:
                    tag = "…" + k[-5:]
                    kind = info.get("kind")
                    if kind == "ok":
                        rr, lr = (info.get("remaining_requests"),
                                  info.get("limit_requests"))
                        detail = (f"còn {rr}/{lr} req" if rr is not None
                                  and lr is not None else "còn lượt")
                        lines.append(f"🟢 {tag}: {detail}")
                    elif kind == "exhausted":
                        lines.append(f"⏳ {tag}: {info.get('note') or 'hết lượt'}")
                    elif kind == "invalid":
                        lines.append(f"❌ {tag}: sai key")
                    else:
                        lines.append(f"⚠ {tag}: {info.get('note') or 'lỗi'}")
                extra = (len(r.get("results", [])) - 8)
                if extra > 0:
                    lines.append(f"… (+{extra} key nữa)")
                if lines:
                    summary += "\n" + "\n".join(lines)
                bad = r["invalid"]
                if bad:
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

        # ============ THẺ 3: 🎧 Giọng cao cấp ElevenLabs ============
        # Tùy chọn — user tự cắm key. Có key -> nhóm giọng 🎧 ElevenLabs mở
        # khóa trong Cài đặt Reup + combo giọng lồng tiếng. Free 10k ký tự/
        # tháng, hết hạn mức tự lùi về edge-tts.
        c_eleven = _card(
            "🎧 Giọng cao cấp ElevenLabs (tùy chọn)",
            "Giọng lồng tiếng / thuyết minh chất lượng cao nhất. Bỏ trống nếu "
            "chỉ dùng edge-tts miễn phí. Hết hạn mức app tự lùi về edge-tts.")
        c_eleven.addWidget(_flabel("ElevenLabs API key (nhiều key mỗi dòng 1)"))
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
        elkeys.setFixedHeight(50); c_eleven.addWidget(elkeys)

        # Nút "Kiểm tra" credit ElevenLabs: gọi GET /user/subscription cho
        # TỪNG key ở THREAD NỀN -> hiện "Key …abc: còn 8.230/10.000 ký tự
        # (free, reset 15/07)"; key lỗi hiện "SAI KEY"/lý do nguyên văn.
        elrow = QHBoxLayout()
        elbtn = QPushButton("Kiểm tra credit ElevenLabs")
        elbtn.setProperty("ghost", True)
        elbtn.setToolTip("Xem từng key còn bao nhiêu ký tự TTS (gói, ngày "
                         "reset). Key sai/bị chặn sẽ báo rõ lý do.")
        elrow.addWidget(elbtn); elrow.addStretch(1)
        c_eleven.addLayout(elrow)
        elstat = QLabel("")
        elstat.setObjectName("eleven_credit_label")
        elstat.setWordWrap(True)
        elstat.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        elstat.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        c_eleven.addWidget(elstat)

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

        # ============ THẺ 4: 🎙 Nghe-chép lời (Whisper) ============
        c_wsp = _card(
            "🎙 Nghe-chép lời (Whisper)",
            "Bóc lời thoại trong video thành phụ đề. Máy cần GPU mới nhanh; "
            "Groq chạy trên mây, máy yếu vẫn nhanh (dùng key Groq ở trên).")
        c_wsp.addWidget(_flabel("Chép lời bằng"))
        wsrc = QComboBox()
        wsrc.addItem("Máy này — Local (cần GPU mới nhanh)", "local")
        wsrc.addItem("Groq — mây (FREE, máy yếu vẫn nhanh)", "groq")
        wi = wsrc.findData(settings.WHISPER_PROVIDER or "local")
        wsrc.setCurrentIndex(wi if wi >= 0 else 0)
        c_wsp.addWidget(wsrc)

        # ============ THẺ 5: 📊 Trạng thái key (thời gian thực) ============
        # chỉ đọc SỔ trong RAM, KHÔNG gọi mạng; QTimer 2s cập nhật, dừng khi
        # đóng dialog.
        c_stat = _card(
            "📊 Trạng thái key (thời gian thực)",
            "Theo dõi từng key Groq: sẵn sàng / đang dùng / hết lượt / sai.")
        kstat = QLabel("")
        kstat.setObjectName("key_status_label")
        kstat.setWordWrap(True)
        kstat.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        kstat.setStyleSheet(f"color:{TEXT}; background:{SURFACE}; border:1px solid "
                            f"{BORDER}; border-radius:8px; padding:8px 10px; "
                            "font-size:12px; line-height:1.5;")
        c_stat.addWidget(kstat)

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
        # note nằm SÁT mép trong vùng cuộn -> nhìn như banner dưới các thẻ

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
        # GHIM hàng nút NGOÀI vùng cuộn -> luôn thấy dù nội dung dài
        _btnbar = QWidget(); _bl = QVBoxLayout(_btnbar)
        _bl.setContentsMargins(14, 6, 14, 10); _bl.addLayout(row)
        _outer.addWidget(_btnbar)
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
        # 🧹 DỌN desktop.ini bản v1.62 từng tạo (đã GỠ tính năng ghim — user
        # không muốn thấy file này) + bỏ cờ READONLY: chạy 1 lần mỗi phiên.
        if not getattr(self, "_pins_cleaned", None):
            self._pins_cleaned = set()
        if str(d) not in self._pins_cleaned:
            self._pins_cleaned.add(str(d))
            from app.core.folderview import cleanup_folder_pins
            cleanup_folder_pins(d)
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
        grp = self._cur_group()          # kênh mới vào NHÓM đang lọc
        hint = f" — vào nhóm “{grp}”" if grp else ""
        name, ok = QInputDialog.getText(self, "Kênh mới",
                                        f"Tên kênh (vd tên kênh TikTok){hint}:")
        if ok and name.strip():
            pid = services.create_project(name.strip(), grp)
            self._reload_groups(grp)     # nhóm trống tạm -> thành nhóm thật
            self._reload_projects()
            i = self.proj.findData(pid)
            if i >= 0:
                self.proj.setCurrentIndex(i)
        elif first:
            pass

    def _build_edit_proj_dialog(self, pid) -> QDialog | None:
        """Dialog 'Sửa kênh' 2 trường: TÊN + NHÓM (combo gõ được -> tạo nhóm
        mới ngay tại chỗ). Tách khỏi exec() để test offscreen thao tác được:
        dlg._t = {name, grp, apply} — apply() ghi DB + cập nhật UI, trả True
        nếu CÓ đổi (tên hoặc nhóm)."""
        row = db.query_one("SELECT name, grp FROM projects WHERE id=?",
                           (int(pid),))
        if not row:
            return None
        old = row["name"]
        old_grp = row["grp"] or ""
        dlg = QDialog(self); dlg.setWindowTitle("Sửa kênh")
        lay = QVBoxLayout(dlg); lay.setSpacing(8)
        lay.addWidget(QLabel("Tên kênh:"))
        name_ed = QLineEdit(old); lay.addWidget(name_ed)
        lay.addWidget(QLabel("Nhóm (chọn có sẵn hoặc gõ tên nhóm MỚI;\n"
                             "để trống = chưa phân nhóm):"))
        grp_box = QComboBox(); grp_box.setEditable(True)
        grp_box.addItem("")               # '' = chưa phân nhóm
        for g in services.list_groups():
            grp_box.addItem(g)
        grp_box.setCurrentText(old_grp)
        lay.addWidget(grp_box)
        rowb = QHBoxLayout(); rowb.addStretch(1)
        okb = QPushButton("Lưu"); okb.setProperty("primary", True)
        okb.clicked.connect(dlg.accept); rowb.addWidget(okb)
        cab = QPushButton("Hủy"); cab.setProperty("ghost", True)
        cab.clicked.connect(dlg.reject); rowb.addWidget(cab)
        lay.addLayout(rowb)
        name_ed.setFocus()

        def apply() -> bool:
            name = (name_ed.text() or "").strip()
            new_grp = (grp_box.currentText() or "").strip()
            renamed = False
            if name and name != old:
                err = services.rename_project(int(pid), name)  # chặn rỗng/trùng
                if err:
                    QMessageBox.warning(self, "Không đổi được tên kênh", err)
                    return False
                renamed = True
            moved = new_grp != old_grp
            if moved:
                services.set_project_group(int(pid), new_grp)
            if not (renamed or moved):
                return False
            keep = self.proj.currentData()  # GIỮ kênh đang chọn sau reload
            self._reload_groups(self._cur_group())  # nhóm có thể vừa thêm/mất
            self._reload_projects()
            self._select_project(keep)
            if renamed:
                self.status.setText(f"Đã đổi tên kênh “{old}” → “{name}”.")
                # ĐƯỜNG XUẤT '<gốc>/Đã xuất/<Kênh>/...' dựng từ TÊN KÊNH lúc
                # xuất -> báo rõ kẻo user đi tìm clip mới trong thư mục tên cũ.
                QMessageBox.information(
                    self, "Đã đổi tên kênh",
                    f"Đã đổi “{old}” → “{name}”.\n\n"
                    f"Clip xuất MỚI sẽ nằm trong thư mục:  Đã xuất\\{name}\\...\n"
                    f"Thư mục cũ “Đã xuất\\{old}” (nếu có) vẫn giữ nguyên — "
                    "file cũ KHÔNG tự chuyển sang.")
            else:
                self.status.setText(
                    f"Đã chuyển kênh “{old}” vào nhóm "
                    f"“{new_grp or 'Chưa phân nhóm'}”.")
            return True

        dlg._t = {"name": name_ed, "grp": grp_box, "apply": apply}
        return dlg

    def _rename_proj(self, pid=None) -> bool:
        """Sửa kênh: TÊN + NHÓM (nút ✏ / chuột phải combo / chuột phải bảng
        📊). pid=None -> kênh đang chọn. Tên hiện tại lấy từ DB, KHÔNG
        currentText() (text combo mang đuôi trạng thái '· 🟢3'). Trả True
        nếu ĐÃ đổi — bảng 📊 dựa vào đó để vẽ lại."""
        pid = self.proj.currentData() if pid is None else pid
        if pid is None:
            return False
        dlg = self._build_edit_proj_dialog(int(pid))
        if dlg is None:
            return False
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        return dlg._t["apply"]()

    def _on_proj(self, _i):
        pid = self.proj.currentData()
        if pid is None:
            return
        self.state.set_project(int(pid))
        self._reload_videos()
        self._refresh_chan_label()      # nhãn hoạt động đổi NGAY theo kênh mới

    # ---- hoạt động theo KÊNH (nhãn + đuôi combo + bảng tình hình) ----
    def _chan_activity(self) -> dict:
        try:
            return services.channel_activity()
        except Exception:  # noqa: BLE001 - nhãn phụ, lỗi không được sập app
            return {}

    def _poll_chan_activity(self):
        """Móc vào timer 1.5s sẵn có nhưng CHỈ query mỗi 3 tick (~4.5s) —
        chung 1 bộ đếm cho cả channel_activity lẫn video_activity (nhãn
        'Kênh: ... | Video này: ...'); dropdown đóng thì KHÔNG query thêm."""
        self._act_tick += 1
        if self._act_tick % 3:
            return
        self._refresh_chan_label()

    def _refresh_chan_label(self, act: dict | None = None):
        """1 dòng gọn: 'Kênh: 🟢 đang chạy 3 · ⏳ đợi 2  |  Video này: 🟢 đang
        cắt' — phần nào =0 thì ẩn; kênh im ắng -> 'chưa có hoạt động'; chưa
        chọn video thì chỉ có vế Kênh (không tiền tố)."""
        pid = self.state.project_id
        if not pid:
            self.chan_lbl.setText("")
            return
        a = (act if act is not None else self._chan_activity()).get(int(pid))
        parts = []
        if a:
            if a["running"]:
                parts.append(f"🟢 đang chạy {a['running']}")
            if a["pending"]:
                parts.append(f"⏳ đợi {a['pending']}")
            if a["failed_recent"]:
                parts.append(f"🔴 lỗi {a['failed_recent']} (24h)")
            if a["last_done"]:
                parts.append(f"✅ xong {services.rel_time_vi(a['last_done'])}")
        chan_txt = " · ".join(parts) or "chưa có hoạt động"
        vid = self.state.video_id
        if vid:      # gộp vắn tắt VIDEO ĐANG CHỌN vào cùng dòng (không thêm nhãn)
            va = self._video_activity().get(int(vid))
            self.chan_lbl.setText(
                f"Kênh: {chan_txt}  |  Video này: {self._vid_mark(va)}")
        else:
            self.chan_lbl.setText(chan_txt)

    def _refresh_proj_marks(self):
        """Gọi khi user MỞ dropdown Kênh: đổi TEXT từng item thành
        'Tên · 🟢3 · ⏳2 · ✅12ph' (kênh im ắng -> chỉ tên). userData giữ
        nguyên project_id nên chọn kênh không đổi hành vi."""
        act = self._chan_activity()
        names = getattr(self, "_proj_names", {})
        self.proj.blockSignals(True)
        try:
            for i in range(self.proj.count()):
                pid = self.proj.itemData(i)
                if pid is None:
                    continue
                name = names.get(int(pid), self.proj.itemText(i))
                a = act.get(int(pid))
                parts = []
                if a:
                    if a["running"]:
                        parts.append(f"🟢{a['running']}")
                    if a["pending"]:
                        parts.append(f"⏳{a['pending']}")
                    if a["last_done"]:
                        parts.append(
                            "✅" + services.rel_time_vi(a["last_done"],
                                                        short=True))
                self.proj.setItemText(
                    i, name + ((" · " + " · ".join(parts)) if parts else ""))
        finally:
            self.proj.blockSignals(False)

    def _channel_dashboard(self):
        self._build_channel_dashboard().exec()

    def _build_channel_dashboard(self) -> QDialog:
        """Dialog 'Tình hình các kênh' 2 TRANG (QStackedWidget):
        - Trang kênh: mỗi kênh 1 dòng, đang chạy/mới xong lên đầu; nháy đúp
          1 kênh -> mở trang CHI TIẾT VIDEO của kênh đó (không đóng dialog).
        - Trang video: mỗi video 1 dòng (chạy/đợi/clip/đã xuất/gần nhất);
          nháy đúp 1 video -> chuyển app sang kênh + video đó rồi đóng;
          nút '← Quay lại danh sách kênh' trở về trang kênh.
        Tách khỏi exec() để test offscreen thao tác được từng bước."""
        from PyQt6.QtWidgets import (QAbstractItemView, QHeaderView,
                                     QStackedWidget, QTableWidget,
                                     QTableWidgetItem)
        dlg = QDialog(self); dlg.setWindowTitle("Tình hình các kênh")
        dlg.resize(880, 460)
        lay = QVBoxLayout(dlg); lay.setSpacing(8)
        stack = QStackedWidget(); lay.addWidget(stack, 1)
        cur = {"pid": None, "name": ""}      # kênh đang xem ở trang video

        def _mk_table(headers):
            t = QTableWidget(0, len(headers))
            t.setHorizontalHeaderLabels(headers)
            t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            t.setSelectionBehavior(
                QAbstractItemView.SelectionBehavior.SelectRows)
            t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            t.verticalHeader().setVisible(False)
            # QSS TƯỜNG MINH cho bảng + THANH TIÊU ĐỀ CỘT: theme tối toàn cục
            # không style QHeaderView -> Windows vẽ header nền SÁNG mặc định
            # nhưng chữ vẫn ăn '* {color: TEXT}' (chữ sáng trên nền sáng =
            # không đọc được). Chỉ định rõ nền tối / chữ sáng đồng bộ theme.
            t.setStyleSheet(
                f"QTableWidget {{ background:{BASE}; border:1px solid {BORDER};"
                f" border-radius:8px; gridline-color:{BORDER};"
                f" color:{TEXT}; }}"
                f"QTableWidget::item {{ padding:3px 8px; }}"
                f"QTableWidget::item:selected {{ background:{ACCENT};"
                f" color:white; }}"
                f"QHeaderView::section {{ background:{SURFACE}; color:{TEXT};"
                f" padding:6px 8px; border:none;"
                f" border-bottom:1px solid {BORDER}; font-weight:600; }}"
                f"QTableCornerButton::section {{ background:{SURFACE};"
                f" border:none; }}")
            hh = t.horizontalHeader()
            # cột TÊN (0) co giãn hết chỗ trống, các cột SỐ ôm theo nội dung
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for c in range(1, len(headers)):
                hh.setSectionResizeMode(c,
                                        QHeaderView.ResizeMode.ResizeToContents)
            return t

        # ===== Trang 1: DANH SÁCH KÊNH =====
        pg1 = QWidget(); l1 = QVBoxLayout(pg1)
        l1.setContentsMargins(0, 0, 0, 0); l1.setSpacing(8)
        hd = QLabel("📊 Tình hình các kênh")
        hd.setStyleSheet(f"color:{TEXT}; font-size:16px; font-weight:800;")
        l1.addWidget(hd)
        sub = QLabel("Nháy đúp 1 kênh để xem CHI TIẾT TỪNG VIDEO của kênh đó. "
                     "Chuột phải 1 kênh để ✏ sửa tên. "
                     "Kênh đang chạy / vừa xong mới nhất nằm trên cùng.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        l1.addWidget(sub)
        # lọc bảng theo NHÓM kênh ('Tất cả' + nhóm distinct — nạp lại mỗi fill)
        frow = QHBoxLayout(); frow.setSpacing(8)
        gl = QLabel("Nhóm:"); gl.setStyleSheet(f"color:{MUTED};")
        frow.addWidget(gl)
        gflt = QComboBox(); gflt.setMinimumWidth(150)
        frow.addWidget(gflt); frow.addStretch(1)
        l1.addLayout(frow)
        tbl = _mk_table(
            ["Kênh", "Nhóm", "Video", "Đang chạy", "Đợi", "Lỗi 24h",
             "Clip đã tạo", "Đã xuất", "Xong gần nhất"])
        l1.addWidget(tbl, 1)
        stack.addWidget(pg1)

        # ===== Trang 2: VIDEO TRONG 1 KÊNH =====
        pg2 = QWidget(); l2 = QVBoxLayout(pg2)
        l2.setContentsMargins(0, 0, 0, 0); l2.setSpacing(8)
        row2 = QHBoxLayout(); row2.setSpacing(8)
        back = QPushButton("← Quay lại danh sách kênh")
        back.setProperty("ghost", True)
        row2.addWidget(back)
        hd2 = QLabel("")
        hd2.setStyleSheet(f"color:{TEXT}; font-size:15px; font-weight:800;")
        row2.addWidget(hd2, 1)
        l2.addLayout(row2)
        sub2 = QLabel("Nháy đúp 1 video để CHUYỂN app sang kênh + video đó. "
                      "Video đang chạy / hoạt động mới nhất nằm trên cùng.")
        sub2.setWordWrap(True)
        sub2.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        l2.addWidget(sub2)
        vtbl = _mk_table(["Video", "Đang chạy", "Đợi", "Clip đã tạo",
                          "Đã xuất", "Hoạt động gần nhất"])
        l2.addWidget(vtbl, 1)
        stack.addWidget(pg2)

        def fill():
            # nạp lại combo lọc NHÓM (giữ lựa chọn cũ; nhóm có thể vừa đổi
            # qua ✏ sửa kênh) — blockSignals để không gọi fill đệ quy
            sel = gflt.currentData()
            sel = sel if isinstance(sel, str) else ""
            gflt.blockSignals(True); gflt.clear()
            gflt.addItem("Tất cả", "")
            for g in services.list_groups():
                gflt.addItem(g, g)
            gi = gflt.findData(sel)
            gflt.setCurrentIndex(gi if gi > 0 else 0)
            gflt.blockSignals(False)
            flt = gflt.currentData() or ""
            act = self._chan_activity()
            rows = []
            for p in services.list_projects():
                pg = p["grp"] or ""
                if flt and pg != flt:
                    continue
                a = act.get(int(p["id"])) or {
                    "running": 0, "pending": 0, "failed_recent": 0,
                    "exported": 0, "videos": 0, "clips": 0,
                    "last_done": None, "last_done_type": ""}
                rows.append((p["name"], pg, int(p["id"]), a))
            # đang chạy trước, rồi last_done mới nhất (chuỗi UTC so sánh
            # lexicographic là đúng thứ tự thời gian), None xuống cuối
            rows.sort(key=lambda r: (r[3]["running"] > 0,
                                     r[3]["last_done"] or ""), reverse=True)
            tbl.setRowCount(len(rows))
            for i, (name, pg, pid, a) in enumerate(rows):
                it = QTableWidgetItem(name)
                it.setData(Qt.ItemDataRole.UserRole, pid)
                tbl.setItem(i, 0, it)
                gx = QTableWidgetItem(pg or "·")
                gx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tbl.setItem(i, 1, gx)
                done_txt = services.rel_time_vi(a["last_done"]) or "—"
                if a["last_done"] and a["last_done_type"]:
                    done_txt += f" ({a['last_done_type']})"
                cells = (str(a.get("videos", 0)) if a.get("videos") else "·",
                         f"🟢 {a['running']}" if a["running"] else "·",
                         f"⏳ {a['pending']}" if a["pending"] else "·",
                         (f"🔴 {a['failed_recent']}"
                          if a["failed_recent"] else "·"),
                         str(a.get("clips", 0)) if a.get("clips") else "·",
                         str(a["exported"]) if a["exported"] else "·",
                         done_txt)
                for c, txt in enumerate(cells, start=2):
                    x = QTableWidgetItem(txt)
                    x.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    tbl.setItem(i, c, x)

        def fill_videos(pid, name=""):
            cur["pid"], cur["name"] = int(pid), name
            try:
                act = services.video_activity(int(pid))
            except Exception:  # noqa: BLE001 - bảng phụ, lỗi không sập app
                act = {}
            rows = []
            for v in services.list_videos(int(pid)):
                a = act.get(int(v["id"])) or {
                    "running": 0, "run_export": 0, "pending": 0,
                    "failed_recent": 0, "clips": 0, "exported": 0,
                    "last_done": None, "last_done_type": ""}
                rows.append((Path(v["src_path"]).name, int(v["id"]), a))
            rows.sort(key=lambda r: (r[2]["running"] > 0,
                                     r[2]["last_done"] or ""), reverse=True)
            # TỔNG ngay trên tiêu đề trang: 'Kênh X — N video · M clip · K đã
            # xuất' -> nhìn 1 phát biết kênh này ra được bao nhiêu clip.
            tot_c = sum(r[2]["clips"] for r in rows)
            tot_e = sum(r[2]["exported"] for r in rows)
            hd2.setText(f"📊 {name or 'Kênh'} — {len(rows)} video · "
                        f"{tot_c} clip đã tạo · {tot_e} đã xuất")
            vtbl.setRowCount(len(rows))
            for i, (name_v, vid_id, a) in enumerate(rows):
                it = QTableWidgetItem(name_v)
                it.setData(Qt.ItemDataRole.UserRole, vid_id)
                vtbl.setItem(i, 0, it)
                run_txt = "·"
                if a["running"]:
                    run_txt = ("🟢 đang xuất" if a["run_export"]
                               else "🟢 đang cắt")
                done_txt = services.rel_time_vi(a["last_done"]) or "—"
                if a["failed_recent"]:
                    done_txt += f" · 🔴 lỗi {a['failed_recent']} (24h)"
                cells = (run_txt,
                         f"⏳ {a['pending']}" if a["pending"] else "·",
                         str(a["clips"]) if a["clips"] else "·",
                         str(a["exported"]) if a["exported"] else "·",
                         done_txt)
                for c, txt in enumerate(cells, start=1):
                    x = QTableWidgetItem(txt)
                    x.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    vtbl.setItem(i, c, x)

        def drill(row, _col):
            """Nháy đúp 1 KÊNH -> trang chi tiết video của kênh đó."""
            it = tbl.item(row, 0)
            pid = it.data(Qt.ItemDataRole.UserRole) if it else None
            if pid is None:
                return
            fill_videos(int(pid), it.text())
            stack.setCurrentIndex(1)

        def jump_video(row, _col):
            """Nháy đúp 1 VIDEO -> chuyển app sang kênh + video đó, đóng."""
            it = vtbl.item(row, 0)
            vid_id = it.data(Qt.ItemDataRole.UserRole) if it else None
            pid = cur["pid"]
            if vid_id is None or pid is None:
                return
            # kênh đích có thể KHÁC nhóm đang lọc -> _select_project tự chuyển
            # combo Nhóm về nhóm của kênh đó (không để combo trống/lệch)
            self._select_project(int(pid))       # -> _on_proj nạp video kênh mới
            j = self.vid.findData(vid_id)
            if j >= 0:
                self.vid.setCurrentIndex(j)      # -> _on_vid chọn đúng video
            dlg.accept()

        def go_back():
            fill()                    # số liệu kênh có thể đổi trong lúc xem
            stack.setCurrentIndex(0)

        def rename_row(row):
            """✏ Sửa tên kênh ở dòng `row` (tái dùng _rename_proj) rồi vẽ lại
            bảng cho tên mới hiện ngay."""
            it = tbl.item(row, 0)
            pid = it.data(Qt.ItemDataRole.UserRole) if it else None
            if pid is not None and self._rename_proj(int(pid)):
                fill()

        def chan_menu(pos):
            # pos của QAbstractScrollArea là tọa độ VIEWPORT (theo Qt docs)
            row = tbl.indexAt(pos).row()
            if row < 0:
                return
            m = QMenu(dlg)
            m.addAction("✏ Sửa tên", lambda: rename_row(row))
            m.exec(tbl.viewport().mapToGlobal(pos))

        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tbl.customContextMenuRequested.connect(chan_menu)
        gflt.currentIndexChanged.connect(lambda _i: fill())
        tbl.cellDoubleClicked.connect(drill)
        vtbl.cellDoubleClicked.connect(jump_video)
        back.clicked.connect(go_back)
        btns = QHBoxLayout(); btns.addStretch(1)
        rf = QPushButton("Làm mới"); rf.setProperty("ghost", True)
        rf.clicked.connect(lambda: (fill_videos(cur["pid"], cur["name"])
                                    if stack.currentIndex() else fill()))
        btns.addWidget(rf)
        cl = QPushButton("Đóng"); cl.setProperty("primary", True)
        cl.clicked.connect(dlg.accept); btns.addWidget(cl)
        lay.addLayout(btns)
        fill()
        # móc cho test offscreen thao tác từng bước (không ảnh hưởng chạy thật)
        dlg._t = {"tbl": tbl, "vtbl": vtbl, "stack": stack, "back": back,
                  "fill": fill, "rename_row": rename_row, "hd2": hd2,
                  "gflt": gflt}
        return dlg

    def _video_activity(self) -> dict:
        """services.video_activity của kênh đang chọn — lỗi trả {} (nhãn phụ,
        không được sập app)."""
        if not self.state.project_id:
            return {}
        try:
            return services.video_activity(int(self.state.project_id))
        except Exception:  # noqa: BLE001 - nhãn trạng thái lỗi không được sập app
            return {}

    @staticmethod
    def _vid_mark(a) -> str:
        """Đuôi trạng thái 1 video từ dict video_activity: ưu tiên ĐANG chạy >
        đợi > có clip (kèm bao lâu) > lỗi 24h > chưa làm gì."""
        if not a:
            return "chưa tạo clip"
        if a["running"]:
            return "🟢 đang xuất" if a["run_export"] else "🟢 đang cắt"
        if a["pending"]:
            return "⏳ đợi"
        if a["clips"]:
            parts = [f"✅ {a['clips']} clip"]
            t = services.rel_time_vi(a["last_done"], short=True)
            if t:
                parts.append(t)
            if a["failed_recent"]:
                parts.append(f"🔴 lỗi {a['failed_recent']}")
            return " · ".join(parts)
        if a["failed_recent"]:
            return f"🔴 lỗi {a['failed_recent']} (24h)"
        return "chưa tạo clip"

    def _refresh_vid_marks(self):
        """Gọi khi user MỞ dropdown Video: đổi TEXT từng item thành
        'Tên.mp4 · 🟢 đang cắt' / '· ✅ 4 clip · 12ph'... userData giữ nguyên
        video_id nên chọn video không đổi hành vi. TÊN GỐC lấy từ _vid_names
        (KHÔNG tách lại từ text — text đang mang đuôi)."""
        act = self._video_activity()
        names = getattr(self, "_vid_names", {})
        self.vid.blockSignals(True)
        try:
            for i in range(self.vid.count()):
                vid = self.vid.itemData(i)
                if vid is None:
                    continue
                name = names.get(int(vid))
                if not name:            # thiếu tên gốc (khó xảy ra) -> giữ text
                    continue
                self.vid.setItemText(
                    i, f"{name} · {self._vid_mark(act.get(int(vid)))}")
        finally:
            self.vid.blockSignals(False)

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
        # TÊN GỐC từng video (không đuôi trạng thái) — text item mang đuôi
        # '· 🟢 đang cắt' nên MỌI chỗ cần tên video phải lấy từ đây/DB (src_path),
        # ĐỪNG currentText() (bài học vụ tên kênh dính đuôi).
        self._vid_names = {}
        if self.state.project_id:
            act = self._video_activity()     # trạng thái TỪNG video (query gộp)
            for v in services.list_videos(self.state.project_id):
                name = Path(v["src_path"]).name
                self._vid_names[int(v["id"])] = name
                self.vid.addItem(
                    f'{name} · {self._vid_mark(act.get(int(v["id"])))}', v["id"])
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
                    res["last_vid"] = services.import_video(pid, f)
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
                # TỰ NHẢY sang video VỪA THÊM (file cuối) — user khỏi bấm tay
                self._reload_videos(select_id=res.get("last_vid"))
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
                # TỰ NHẢY sang video vừa tải xong — user khỏi bấm tay
                self._reload_videos(select_id=vid)
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
            self._refresh_chan_label()   # vế 'Video này:' đổi NGAY theo video mới

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
            # lambda: triggered truyền checked=False -> đừng lọt vào tham số pid
            m.addAction("✏ Sửa tên kênh", lambda: self._rename_proj())
            m.addAction("Chuyển nhóm...", lambda: self._move_group())
            m.addAction("📁 Thư mục lưu riêng...",
                        lambda: self._set_export_dir_for_current())
            m.addAction("Xóa kênh này", self._del_proj)
        m.addAction("Quản lý / Xóa nhiều kênh…", self._manage_projects)
        m.exec(self.proj.mapToGlobal(pos))

    def _move_group(self, pid=None):
        """Chuột phải combo Kênh -> 'Chuyển nhóm...': chọn nhóm có sẵn hoặc
        gõ tên nhóm MỚI (getItem editable). Để trống = bỏ nhóm."""
        pid = self.proj.currentData() if pid is None else pid
        if pid is None:
            return
        cur = services.project_group(int(pid))
        items = [""] + services.list_groups()
        idx = items.index(cur) if cur in items else 0
        g, ok = QInputDialog.getItem(
            self, "Chuyển nhóm",
            "Nhóm (chọn có sẵn hoặc gõ tên MỚI; để trống = bỏ nhóm):",
            items, idx, True)
        if not ok:
            return
        g = (g or "").strip()
        if g == cur:
            return
        services.set_project_group(int(pid), g)
        # ĐI THEO kênh sang nhóm mới ('' -> 'Chưa phân nhóm') — kênh đang chọn phải
        # luôn hiện được trong combo, không để trống/lệch
        self._reload_groups(g)
        self._reload_projects()
        self._select_project(int(pid))
        name = getattr(self, "_proj_names", {}).get(int(pid), "")
        self.status.setText(f"Đã chuyển kênh “{name}” vào nhóm "
                            f"“{g or 'Chưa phân nhóm'}”.")

    def _set_export_dir_for_current(self, pid=None):
        """Chuột phải combo Kênh -> '📁 Thư mục lưu riêng...': đặt thư mục lưu
        cho kênh ĐANG CHỌN. Chọn hủy hộp thoại -> giữ nguyên; muốn về mặc định
        thì dùng dialog 'Quản lý nhóm & kênh' (nút 'Về mặc định')."""
        pid = self.proj.currentData() if pid is None else pid
        if pid is None:
            return
        cur = services.project_export_dir(int(pid))
        d = QFileDialog.getExistingDirectory(
            self, "Chọn THƯ MỤC LƯU RIÊNG cho kênh này "
                  "(clip cắt xong vào THẲNG đây, không tạo folder con)",
            cur or "")
        if not d:
            return
        services.set_project_export_dir(int(pid), d)
        name = getattr(self, "_proj_names", {}).get(int(pid), "")
        self.status.setText(f"Kênh “{name}” sẽ lưu clip vào: {d}")
        QMessageBox.information(
            self, "Đã đặt thư mục lưu",
            f"Kênh “{name}” sẽ lưu clip THẲNG vào:\n{d}\n\n"
            "(Không tạo thư mục con theo tên video.)")

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
        # Trạng thái + hoạt động gần nhất từng video (1 lượt query gộp cho cả
        # kênh — trước đây list_clips TỪNG video, kênh nhiều video bị chậm).
        act = self._video_activity()
        rows = []
        for v in vids:
            a = act.get(int(v["id"]))
            txt = f'{Path(v["src_path"]).name}   ·  {self._vid_mark(a)}'
            if a and a["last_done"] and (a["running"] or a["pending"]):
                # đang chạy/đợi thì _vid_mark không kèm thời gian -> bổ sung
                txt += f' · ✅ {services.rel_time_vi(a["last_done"])}'
            rows.append((v["id"], txt))

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
            self._reload_groups(self._cur_group())  # nhóm có thể vừa hết kênh
            self._reload_projects()
            return len(ids)

        self._delete_picker("Xóa kênh", "Tích ô các kênh cần xóa rồi bấm "
                            "<b>Xóa mục đã chọn</b> (xóa cả video + clip + file).",
                            rows, do)

    # ---- tạo clip ----
    def _track_auto(self, job_id, video_id):
        """Nếu BẬT tự-động-xuất: ghi nhớ job phân tích này để xong thì tự xuất.
        🔒 CHỐT MẪU: chụp lại MẪU ĐANG CHỌN lúc bấm (deepcopy) gắn với job —
        phân tích xong dù user đã đổi sang mẫu khác, video này VẪN xuất bằng
        đúng mẫu lúc bấm (không ăn nhầm mẫu mới)."""
        if job_id and self.auto_export_chk.isChecked():
            self._pending_export[job_id] = video_id
            if not hasattr(self, "_auto_tpl"):
                self._auto_tpl = {}
            self._auto_tpl[job_id] = copy.deepcopy(self.layout_tpl)

    def _check_auto_export(self):
        """Định kỳ: job phân tích nào XONG -> tự xuất hết clip của video đó
        bằng ĐÚNG MẪU đã chốt lúc bấm (không phải mẫu hiện tại)."""
        if not self._pending_export:
            return
        auto_tpl = getattr(self, "_auto_tpl", {})
        ready, total = 0, 0
        # 1 query GỘP cho mọi job đang theo dõi (thay vì N query mỗi 1.5s)
        states = services.job_states(list(self._pending_export))
        for jid in list(self._pending_export):
            st = states.get(jid, "")
            if st == "done":
                vid = self._pending_export.pop(jid)
                tpl_snap = auto_tpl.pop(jid, None)
                try:
                    if tpl_snap is not None:
                        # tạm dùng MẪU ĐÃ CHỐT của job này để build payload
                        # (mọi self.layout_tpl.get trong _export_video/_render_png
                        # /_pick_bgm... đọc snapshot); khôi phục mẫu hiện tại sau.
                        saved = self.layout_tpl
                        self.layout_tpl = tpl_snap
                        try:
                            total += self._export_video(vid)
                        finally:
                            self.layout_tpl = saved
                    else:
                        total += self._export_video(vid)
                    ready += 1
                except Exception:  # noqa: BLE001
                    pass
            elif st in ("failed", "canceled", "skipped", ""):
                self._pending_export.pop(jid, None)   # lỗi/mất -> thôi, không xuất
                auto_tpl.pop(jid, None)
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

    def _recap_dim(self) -> float:
        """🔦 Mức 'Làm tối video khi AI kể' từ ⚙ Cài đặt Reup (QSettings
        recap_dim 0-40%, mặc định 14) -> 0.0-0.40 cho export_canvas_clip
        (chỉ áp cho clip recap; clip thường bỏ qua)."""
        try:
            v = int(self._settings.value("recap_dim", 14))
        except (TypeError, ValueError):
            v = 14
        return min(40, max(0, v)) / 100.0

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
            # duration; 1-8 = user chọn tay (khớp dải spin 0-8 ở dialog Cài
            # đặt Reup — trước đây kẹp min(3,..) chặn oan lựa chọn 4-8).
            preset["recap_count"] = min(8, max(0, int(
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
        jid = services.enqueue_auto_recap(self.state.pool, self.state.video_id,
                                          self.state.project_id, preset)
        # BẬT "Phân tích xong tự động xuất" -> reup xong TỰ xuất luôn (clip
        # recap mang signals.recap -> _export_video xuất bình thường). Trước
        # đây nhánh reup KHÔNG track nên bật ô mà reup vẫn không tự xuất.
        if jid:
            self._track_auto(jid, self.state.video_id)
        extra = " → xong TỰ xuất" if self.auto_export_chk.isChecked() else ""
        self.status.setText(
            "🎙 Đang phân tích & viết kịch bản thuyết minh "
            f"({self.recap_style.currentText()}){extra}... clip sẽ hiện trong "
            "danh sách khi xong (xem tiến trình dưới).")

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
    # màu + icon theo GIAI ĐOẠN của job (khớp queue_panel): phân tích/AI = tím,
    # cắt/xuất video = xanh ngọc.
    _PHASE_ANALYZE_COLOR = "#A78BFA"
    _PHASE_EXPORT_COLOR = "#14B8A6"
    _EXPORT_TYPES = {"m1_export_clip"}

    @classmethod
    def _job_phase(cls, jtype: str) -> tuple:
        """(icon, tên-bước-mặc-định, màu) theo loại job — dùng khi message rỗng
        và cho icon + màu của khối tiến trình lớn."""
        if jtype in cls._EXPORT_TYPES:
            return "✂", "Đang cắt & xuất clip 9:16", cls._PHASE_EXPORT_COLOR
        if jtype == "auto_recap":
            return "🎙", "Đang viết kịch bản thuyết minh", cls._PHASE_ANALYZE_COLOR
        if jtype in ("auto_mixed", "m1_mixed_cut"):
            return "🎬", "Đang ghép Mixed-Cut", cls._PHASE_EXPORT_COLOR
        if jtype == "m1_highlights":
            return "🔍", "Đang tìm & chọn đoạn hay", cls._PHASE_ANALYZE_COLOR
        return "🔍", "Đang phân tích video", cls._PHASE_ANALYZE_COLOR

    def _job_progress_row(self, vid):
        """Job đang CHẠY (ưu tiên) hoặc đang chờ của video: type+progress+message.
        Kèm 'others' = SỐ việc khác đang chạy/chờ trong hàng đợi (để hiện
        'còn N việc trong hàng')."""
        if not vid:
            return None
        try:
            r = (db.query_one(
                "SELECT type, progress, message, status FROM jobs WHERE video_id=? "
                "AND status='running' ORDER BY id DESC LIMIT 1", (vid,))
                or db.query_one(
                "SELECT type, progress, message, status FROM jobs WHERE video_id=? "
                "AND status='pending' ORDER BY id LIMIT 1", (vid,)))
            if r is None:
                return None
            oth = db.query_one(
                "SELECT COUNT(*) AS n FROM jobs WHERE status IN "
                "('running','pending') AND (video_id IS NULL OR video_id<>?)",
                (vid,))
            return {"type": r["type"], "progress": r["progress"],
                    "message": r["message"], "status": r["status"],
                    "others": int(oth["n"]) if oth else 0}
        except Exception:  # noqa: BLE001
            return None

    def _job_progress_widget(self, compact=False):
        """KHỐI TIẾN TRÌNH NỔI BẬT: icon + tên bước TO, thanh % dày, số % chữ
        LỚN, và 'còn N việc trong hàng'. compact=True: dải gọn hơn ở đầu danh
        sách clip (khi đã có clip); False: khối lớn giữa empty-state."""
        w = QWidget(); w.setObjectName("jobProgBox")
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        w.setStyleSheet(
            f"#jobProgBox{{background:{BASE}; border:1px solid {BORDER}; "
            f"border-radius:14px;}}")
        lay = QVBoxLayout(w); lay.setSpacing(10)
        m = 14 if compact else 22
        lay.setContentsMargins(m + 4, m, m + 4, m)

        # ---- hàng 1: icon + tên bước (TO, đậm) ----- căn trái để dễ đọc
        head = QHBoxLayout(); head.setSpacing(10)
        icon = QLabel("🔍")
        icon.setStyleSheet("font-size:26px; background:transparent;")
        head.addWidget(icon)
        step = QLabel("Đang xử lý…")
        step.setWordWrap(True)
        step.setStyleSheet("font-size:18px; font-weight:700; background:transparent;")
        step.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        head.addWidget(step, 1)
        # số % CHỮ LỚN bên phải
        pctlbl = QLabel("0%")
        pctlbl.setStyleSheet("font-size:30px; font-weight:800; "
                             "background:transparent;")
        pctlbl.setAlignment(Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(pctlbl)
        lay.addLayout(head)

        # ---- hàng 2: thanh % DÀY ----
        bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(0)
        bar.setFixedHeight(18 if compact else 24)
        bar.setTextVisible(False)     # số % đã hiện TO ở trên
        lay.addWidget(bar)

        # ---- hàng 3: dòng phụ 'còn N việc trong hàng' ----
        sub = QLabel("")
        sub.setStyleSheet(f"color:{MUTED}; font-size:12px; background:transparent;")
        lay.addWidget(sub)

        self._job_bar = bar
        self._job_lbl = step
        self._job_icon = icon
        self._job_pct = pctlbl
        self._job_sub = sub
        self._update_job_progress()   # điền giá trị ngay, khỏi chờ nhịp timer
        return w

    def _update_job_progress(self):
        """Cập nhật KHỐI TIẾN TRÌNH theo NHỊP TIMER 1.5s sẵn có (gọi từ
        _poll_done) — không tạo timer mới, không rebuild danh sách."""
        bar = getattr(self, "_job_bar", None)
        step = getattr(self, "_job_lbl", None)
        if bar is None or step is None:
            return
        r = self._job_progress_row(self.state.video_id)
        if not r:
            return
        try:
            pct = int(max(0.0, min(1.0, float(r["progress"] or 0))) * 100)
            jtype = r["type"] or ""
            icon, default_step, color = self._job_phase(jtype)
            msg = (r["message"] or "").strip()
            if r["status"] == "pending":
                # đang chờ: icon đồng hồ cát, nói rõ đang xếp hàng
                icon = "⏳"
                step_txt = msg or "Đang chờ đến lượt trong hàng đợi…"
                color = WARN
            else:
                step_txt = msg or default_step
            bar.setValue(pct)
            bar.setStyleSheet(
                f"QProgressBar{{background:{SURFACE}; border:none; "
                f"border-radius:6px;}} "
                f"QProgressBar::chunk{{background:{color}; border-radius:6px;}}")
            step.setText(step_txt)
            ic = getattr(self, "_job_icon", None)
            if ic is not None:
                ic.setText(icon)
            pl = getattr(self, "_job_pct", None)
            if pl is not None:
                pl.setText(f"{pct}%")
                pl.setStyleSheet(f"color:{color}; font-size:30px; "
                                 "font-weight:800; background:transparent;")
            sub = getattr(self, "_job_sub", None)
            if sub is not None:
                n = int(r.get("others", 0) or 0)
                sub.setText(f"⋯ còn {n} việc khác trong hàng đợi"
                            if n > 0 else "")
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
            # ƯU TIÊN hashtag đã được JOB PHÂN TÍCH sinh sẵn (worker, chạy nền):
            # đọc DB tức thì -> KHÔNG gọi LLM trên UI thread (trước đây gọi mạng
            # ngay trong timer 1.5s lúc tự-xuất -> app đơ vài giây đúng lúc đang
            # encode). Thiếu (video cũ/heuristic) mới lùi về gọi LLM như cũ.
            pre = get_analysis(video_id, "hashtags") or {}
            tags = [t for t in (pre.get("tags") or []) if t]
            if not tags and _llm.is_configured():
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
        chrow = db.query_one("SELECT name, export_dir FROM projects WHERE id=?",
                             (pid,))
        import re as _re
        chname = _re.sub(r'[<>:"/\\|?*]', "_",
                         ((chrow["name"] if chrow else "") or "Kenh"))
        chname = chname.strip().strip(". ") or "Kenh"   # bỏ chấm/cách cuối (Windows kỵ)
        # KÊNH CÓ THƯ MỤC LƯU RIÊNG -> xuất THẲNG vào đó (flat, KHÔNG nối <Kênh>
        # cũng KHÔNG tạo folder con theo tên video). Không đặt -> giữ y cũ.
        ch_export_dir = ((chrow["export_dir"] if chrow else "") or "").strip()
        if ch_export_dir:
            out_root = ch_export_dir
            flat_export = True
        else:
            out_root = str(self._export_root() / chname)
            flat_export = False
        vr = self.layout_tpl.get("video_rect")
        bg = self.layout_tpl.get("bg", "blur")
        tb = self.layout_tpl.get("trim_black", False)
        vpx = self._video_px_for(vrow)
        # HASHTAG chung cho MỌI Part của video (sinh 1 lần, cache theo video_id)
        tags_str = self._video_hashtags(video_id, clips)
        # NGÔN NGỮ video: tra 1 LẦN cho CẢ video (transcript word-level có thể
        # nặng vài MB — trước đây parse lại cho TỪNG clip ngay trên UI thread
        # -> góp phần làm app khựng lúc bấm xuất/tự-xuất hàng loạt).
        _vid_is_vi = None       # None = chưa tra; True/False = kết quả; 'err' = lỗi
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
            en = (sig.get("title_en") or "").strip()
            # 🌐 TÊN FILE THEO NGÔN NGỮ VIDEO: title_en (title_pub — đúng ngôn
            # ngữ video) ưu tiên; THIẾU thì chỉ lùi về tiêu đề Việt khi video
            # LÀ tiếng Việt — video Nhật/Anh... không gắn tên tiếng Việt nữa
            # (user báo video Nhật ra file tên Việt). Không còn gì -> "Part N".
            if not en:
                try:
                    from app.ai import recap as _rec
                    if _vid_is_vi is None:
                        from app.core.analysis import get_analysis as _ga
                        _tr = _ga(video_id, "transcript") or {}
                        _vid_is_vi = _rec._is_vi_lang(_rec.resolve_lang(
                            _tr.get("language", ""), _tr.get("text", "") or ""))
                    if _vid_is_vi is True or not _rec.looks_vietnamese(vi):
                        en = vi        # video Việt / tiêu đề không phải Việt
                except Exception:  # noqa: BLE001 - lỗi tra cứu -> giữ vi như cũ
                    _vid_is_vi = "err"
                if _vid_is_vi == "err":
                    en = vi
            label = en or self._fixed_label()
            # tên gọn "Part 1 <tiêu đề> #tag1 #tag2" — hashtag CHUNG toàn video,
            # đúng ngôn ngữ nội dung. _safe_name ở export_clip giữ '#'/ký tự có dấu.
            out_name = f"Part {no} {label}".strip() + tags_str
            jid = services.enqueue_export(
                self.state.pool, c["id"], video_id, pid,
                out_dir=out_root,   # <gốc>/Đã xuất/<KÊNH>/<video>/Part N.mp4
                                    # HOẶC thư mục riêng của kênh (flat)
                flat_export=flat_export,
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
                    # FONT chữ AI kể ('(giống phụ đề gốc)'/rỗng -> font phụ đề gốc)
                    "narr_font": self.layout_tpl.get("narr_font", "") or "",
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
                # 🔦 làm tối hình khi AI kể (spotlight) — toàn cục từ ⚙
                recap_dim=self._recap_dim(),
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
        # KÊNH CÓ THƯ MỤC LƯU RIÊNG -> mở THẲNG đó (flat: không nối <Kênh>/<video>).
        ch_export_dir = ""
        if self.state.project_id:
            chrow = db.query_one(
                "SELECT name, export_dir FROM projects WHERE id=?",
                (self.state.project_id,))
            ch_export_dir = ((chrow["export_dir"] if chrow else "") or "").strip()
            if ch_export_dir:
                target = Path(ch_export_dir)
            else:
                # mở thẳng folder KÊNH đang chọn nếu có (sạch tên GIỐNG _export_video)
                ch = re.sub(r'[<>:"/\\|?*]', "_",
                            ((chrow["name"] if chrow else "") or "Kenh"))
                ch = ch.strip().strip(". ") or "Kenh"
                if (base / ch).is_dir():
                    target = base / ch
        if not ch_export_dir and self.state.video_id:  # có video -> vào sâu folder video
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
        # Thư mục có thể CHƯA tồn tại (chưa xuất clip nào) -> tạo rồi mở,
        # đừng im lặng không làm gì (user tưởng nút hỏng).
        try:
            Path(target).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        try:
            os.startfile(str(target))  # noqa: S606
            self.status.setText(f"Đã mở: {target}")
        except Exception:  # noqa: BLE001 - startfile lỗi -> thử explorer.exe
            import subprocess
            try:
                subprocess.Popen(["explorer", str(target)])
                self.status.setText(f"Đã mở: {target}")
            except Exception:  # noqa: BLE001
                self.status.setText(f"⚠ Không mở được thư mục: {target}")

    def _open_file(self, p):
        if p and os.path.isfile(p):
            os.startfile(p)  # noqa: S606
