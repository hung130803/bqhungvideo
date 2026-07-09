"""
Hộp thoại "Cài đặt Reup thuyết minh" (nút ⚙ cạnh nút 🎙 ở màn hình chính).

Cài đặt TOÀN CỤC cho mọi kênh (lưu QSettings — không dính vào mẫu template):
  - recap_voice : giọng KỂ. "" = tự chọn theo ngôn ngữ video (khuyên dùng);
                  hoặc chọn cứng 1 giọng (🌟 Gemini / ⭐ giọng hot edge-tts).
                  Mẫu template KHÔNG còn quyết định giọng thuyết minh —
                  dub_voice của mẫu chỉ dành cho dịch lồng tiếng thường.
  - recap_style : phong cách kể (đồng bộ 2 CHIỀU với combo cạnh nút 🎙 —
                  cùng key QSettings, studio_page nạp lại sau khi đóng).
  - recap_ratio : tỉ lệ % thời lượng AI kể (15-80, mặc định 30 — ít = tập
                  trung video gốc) -> prompt + ép cứng sau validate. Giá
                  trị 55 lưu cũ (mặc định cũ chưa ai đổi) tự migrate -> 30.
  - recap_pace  : nhịp kể slow/normal/fast -> rate edge-tts -3%/0%/+4%
                  (giọng Gemini: prepend chỉ dẫn kể chuyện vào text TTS).
  - recap_pitch : TÔNG GIỌNG low/normal/high -> pitch edge-tts -18Hz/+0Hz/
                  +18Hz (Trầm/Vừa/Cao). Giọng Gemini không hỗ trợ -> bỏ qua.
  - recap_volume: "Âm lượng giọng kể" 80-200% (mặc định 115%) — nhân THÊM
                  sau khi build_recap_track auto-match loudness với tiếng
                  gốc video.
  - recap_win_min / recap_win_max : nhóm "Cắt ghép" — số CẢNH (window) AI
                  nên ghép trong 1 clip (Min 2-6, Max 3-8, mặc định 3-6,
                  Min<=Max tự ép) -> prompt đạo diễn + trần validate_windows.
  - recap_count : số clip (Part) mỗi video. 0 = "Tự động theo độ dài" (MẶC ĐỊNH:
                  <4 phút 1 clip, 4-12 phút 2, >12 phút 3 — m2_recap tính từ
                  duration); 1-3 = chọn tay — m2_recap chia video thành K
                  chương, mỗi chương 1 clip độc lập Part 1..K.

Danh sách giọng (dubbing.list_recap_voices) NHÓM THEO NGÔN NGỮ: dòng có
voice_id RỖNG là nhãn nhóm/thông báo (vd "🇻🇳 Tiếng Việt", dòng Gemini khi
chưa có key) -> item bị DISABLE, không chọn được. Nhóm "🔥 ĐỀ XUẤT — mượt &
hot nhất" (curate tay, có mô tả) nằm ngay dưới Gemini. Checkbox "Hiện tất cả
giọng (~500)" -> list_recap_voices(all=True) trả TOÀN BỘ kho edge-tts; ô
"🔎 Tìm giọng" lọc theo tên/ngôn ngữ/voice_id (không phân biệt hoa thường,
nhóm rỗng tự ẩn).

Nút "🔊 Nghe thử": synth câu demo kiểu kể chuyện (có "...") bằng giọng + nhịp
+ tông đang chọn — synth ở thread nền, phát bằng winsound (như
editor._dub_preview).
"""
from __future__ import annotations

import glob
import os
import subprocess
import tempfile
import threading
import uuid

from PyQt6.QtCore import Qt, QTimer, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout,
)

from app.ai.recap import DEFAULT_STYLE, STYLES

# Câu demo NGHE THỬ kiểu kể chuyện (có "..." tạo khựng đúng vibe narrator).
_DEMO_NARR = {
    "vi": "Không ai ngờ nổi... điều gã này sắp làm. Kể cả tôi.",
    "en": "Nobody saw this coming... not even him. And then... it happened.",
}

# Nhịp kể: (nhãn, key QSettings). Key -> rate edge-tts ở dubbing.RECAP_PACES.
_PACES = [("Thong thả", "slow"), ("Vừa", "normal"), ("Dồn dập", "fast")]

# Tông giọng: (nhãn, key QSettings). Key -> pitch edge-tts ở
# dubbing.RECAP_PITCHES (-18Hz/+0Hz/+18Hz). Gemini không hỗ trợ -> bỏ qua.
_PITCHES = [("Trầm", "low"), ("Vừa", "normal"), ("Cao", "high")]

_AUTO_VOICE_LABEL = "Tự chọn theo ngôn ngữ video (khuyên dùng)"

# cache danh sách giọng cho phiên chạy (đỡ gọi mạng mỗi lần mở dialog):
# {False: list gọn (đề xuất/hot), True: full ~500 giọng}
_VOICE_CACHE: dict = {}


class RecapSettingsDialog(QDialog):
    """Cài đặt riêng cho 🎙 Reup thuyết minh. exec() -> Accepted = đã lưu."""

    _demo_ready = pyqtSignal(str)   # đường dẫn wav demo ("" = lỗi)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt Reup thuyết minh")
        self.setMinimumWidth(460)
        self._s = QSettings("AIContentStudio", "studio")
        self._demo_ready.connect(self._play_demo)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # ---- Giọng kể ----
        lay.addWidget(QLabel("<b>Giọng kể</b> — giọng AI đọc lời thuyết minh"))
        vrow = QHBoxLayout()
        self.voice = QComboBox()
        self.voice.setMinimumWidth(280)
        self.voice.setToolTip(
            "Để 'Tự chọn' thì app dùng giọng hot nhất của ĐÚNG ngôn ngữ "
            "video.\nChọn cứng 1 giọng nếu muốn mọi clip cùng giọng:\n"
            "· 🔥 ĐỀ XUẤT = mượt & hot nhất, có mô tả từng giọng\n"
            "· 🎧 ElevenLabs = chất lượng CAO NHẤT (cần key, free 10k ký tự/"
            "tháng — không chỉnh nhịp/tông, hết hạn mức tự lùi edge-tts)\n"
            "· giọng 'đa ngôn ngữ' đọc được MỌI thứ tiếng\n"
            "· 🌟 Gemini nét nhất (cần key, hạn mức free thấp).")
        self.voice.addItem(_AUTO_VOICE_LABEL, "")
        vrow.addWidget(self.voice, 1)
        self.prev_btn = QPushButton("🔊 Nghe thử")
        self.prev_btn.setToolTip(
            "Đọc thử 1 câu kể chuyện bằng giọng + nhịp đang chọn — nghe "
            "trước khi lưu, khỏi xuất clip mới biết giọng dở.")
        self.prev_btn.clicked.connect(self._preview)
        vrow.addWidget(self.prev_btn)
        lay.addLayout(vrow)

        # Dòng credit ElevenLabs — CHỈ hiện khi đang chọn giọng el: (nạp
        # NỀN khi mở dialog/đổi giọng, dubbing cache quota 5 phút).
        self.el_credit = QLabel("")
        self.el_credit.setStyleSheet("color: #8a8f98; font-size: 11px;")
        self.el_credit.setVisible(False)
        lay.addWidget(self.el_credit)
        self.voice.currentIndexChanged.connect(self._update_el_credit)

        # ---- Tìm giọng + hiện toàn bộ kho (~500 giọng) ----
        self._voices: list = []          # list thô của chế độ đang chọn
        srow = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔎 Tìm giọng...")
        self.search.setToolTip(
            "Lọc danh sách giọng theo tên / ngôn ngữ / mã giọng — không "
            "phân biệt hoa thường.\nVí dụ: 'andrew', 'việt', 'vi-VN', "
            "'nữ'. Xóa chữ để hiện lại đầy đủ.")
        self.search.textChanged.connect(self._rebuild_voice_combo)
        srow.addWidget(self.search, 1)
        self.all_chk = QCheckBox("Hiện tất cả giọng (~500)")
        self.all_chk.setToolTip(
            "TẮT (mặc định): chỉ hiện giọng 🔥 đề xuất + ⭐ hot (đã kiểm "
            "chứng mượt).\nBẬT: hiện TOÀN BỘ kho ~500 giọng edge-tts của "
            "mọi ngôn ngữ (tải lần đầu cần mạng, có cache 7 ngày).")
        self.all_chk.toggled.connect(self._all_toggled)
        srow.addWidget(self.all_chk)
        lay.addLayout(srow)
        self.count_lbl = QLabel("")
        self.count_lbl.setToolTip("Số giọng chọn được trong danh sách.")
        self.count_lbl.setStyleSheet("color: #8a8f98; font-size: 11px;")
        lay.addWidget(self.count_lbl)
        hint = QLabel("💡 Mẹo: giọng 'đa ngôn ngữ' đọc được mọi thứ tiếng — "
                      "hợp kênh reup nhiều nguồn. Bấm 🔊 nghe thử trước khi "
                      "chốt.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8a8f98; font-size: 11px;")
        lay.addWidget(hint)

        # ---- Âm lượng giọng kể ----
        self.vol_lbl = QLabel()
        lay.addWidget(self.vol_lbl)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(80, 200)
        self.volume.setToolTip(
            "Nhân THÊM sau khi app tự cân giọng kể to ngang tiếng gốc video."
            "\n100% = đúng mức tự cân · 115% (khuyên dùng) = nhỉnh hơn nền "
            "một chút · 150-200% = to hẳn (có chống rè).")
        self.volume.valueChanged.connect(self._volume_changed)
        lay.addWidget(self.volume)

        # ---- Số clip thuyết minh ----
        crow = QHBoxLayout()
        # ghi rõ "(Part)" để khỏi lẫn với "Số cảnh ghép" bên dưới
        crow.addWidget(QLabel("<b>Số clip (Part) mỗi video</b> — chia video "
                              "thành từng chương"))
        self.count = QSpinBox()
        self.count.setRange(0, 3)
        # giá trị 0 hiện thành option "Tự động theo độ dài" (mặc định)
        self.count.setSpecialValueText("Tự động theo độ dài (khuyên dùng)")
        self.count.setMinimumWidth(220)
        self.count.setToolTip(
            "Mỗi lần bấm 🎙 tạo bao nhiêu clip.\n"
            "Tự động theo độ dài (khuyên dùng): video dưới 4 phút = 1 clip, "
            "4-12 phút = 2 clip, trên 12 phút = 3 clip.\n"
            "Hoặc chọn tay 1-3. App chia video thành K chương bằng nhau, "
            "mỗi chương 1 clip Part riêng (hook + kết riêng).\n"
            "Video ngắn dưới 2,5 phút luôn tự rút về 1 clip.")
        crow.addWidget(self.count)
        crow.addStretch(1)
        lay.addLayout(crow)

        # ---- Cắt ghép: min/max số cảnh ghép mỗi clip ----
        lay.addWidget(QLabel("<b>Cắt ghép</b> — mỗi clip ghép từ bao nhiêu "
                             "cảnh của video gốc"))
        wrow = QHBoxLayout()
        wrow.addWidget(QLabel("Số cảnh ghép mỗi clip:  Min"))
        self.win_min = QSpinBox()
        self.win_min.setRange(2, 6)
        self.win_min.setToolTip(
            "Số KHUNG CẢNH tối thiểu AI nên cắt ghép trong 1 clip.\n"
            "Đây là mong muốn — kịch bản ít cảnh hơn (nhưng đủ dài) vẫn "
            "được nhận, không bị vứt.")
        wrow.addWidget(self.win_min)
        wrow.addWidget(QLabel("–  Max"))
        self.win_max = QSpinBox()
        self.win_max.setRange(3, 8)
        self.win_max.setToolTip(
            "Số KHUNG CẢNH tối đa mỗi clip — AI trả thừa thì app tự cắt "
            "bớt, giữ lại các cảnh dài/đắt hơn.")
        wrow.addWidget(self.win_max)
        wrow.addStretch(1)
        # Min <= Max tự ép 2 chiều (kéo Min quá Max -> Max nhích theo và
        # ngược lại) — không bao giờ lưu được cặp ngược.
        self.win_min.valueChanged.connect(self._win_min_changed)
        self.win_max.valueChanged.connect(self._win_max_changed)
        lay.addLayout(wrow)

        # ---- Phong cách ----
        lay.addWidget(QLabel("<b>Phong cách kể</b>"))
        self.style = QComboBox()
        for key, (label, _hint) in STYLES.items():
            self.style.addItem(label, key)
        self.style.setToolTip("Đồng bộ với combo cạnh nút 🎙 ở màn hình "
                              "chính (là một).")
        lay.addWidget(self.style)

        # ---- Tỉ lệ AI kể ----
        self.ratio_lbl = QLabel()
        lay.addWidget(self.ratio_lbl)
        self.ratio = QSlider(Qt.Orientation.Horizontal)
        self.ratio.setRange(15, 80)
        self.ratio.setToolTip(
            "AI kể chiếm bao nhiêu % thời lượng clip (phần còn lại giữ "
            "tiếng gốc).\nÍt = tập trung video gốc (AI chỉ mở đầu + vài cầu "
            "nối ngắn); nhiều = kể dày như kênh recap.\nApp ÉP CỨNG: AI kể "
            "vượt tỉ lệ này quá 12% sẽ bị cắt bớt phần kể giữa clip.")
        self.ratio.valueChanged.connect(self._ratio_changed)
        lay.addWidget(self.ratio)

        # ---- Nhịp kể + Tông giọng ----
        prow = QHBoxLayout()
        pcol1 = QVBoxLayout()
        pcol1.addWidget(QLabel("<b>Nhịp kể</b> — tốc độ giọng đọc"))
        self.pace = QComboBox()
        for label, key in _PACES:
            self.pace.addItem(label, key)
        self.pace.setToolTip("Thong thả = chậm rãi kịch tính · Dồn dập = "
                             "nhanh giữ nhịp TikTok.")
        pcol1.addWidget(self.pace)
        prow.addLayout(pcol1, 1)
        pcol2 = QVBoxLayout()
        pcol2.addWidget(QLabel("<b>Tông giọng</b> — trầm / cao"))
        self.pitch = QComboBox()
        for label, key in _PITCHES:
            self.pitch.addItem(label, key)
        self.pitch.setToolTip(
            "Trầm = ấm, hợp kể phim kịch tính · Cao = tươi sáng, năng "
            "lượng.\nChỉ áp cho giọng edge-tts (🔥/⭐) — giọng 🌟 Gemini "
            "KHÔNG hỗ trợ chỉnh tông (giữ tông gốc).")
        pcol2.addWidget(self.pitch)
        prow.addLayout(pcol2, 1)
        lay.addLayout(prow)

        # ---- 🎭 Giọng cảm xúc (audio tag ElevenLabs v3) ----
        self.emotion = QCheckBox(
            "🎭 Giọng cảm xúc (nhấn nhá như người thật)")
        self.emotion.setToolTip(
            "AI đạo diễn TỰ chèn cảm xúc vào lời kể (hào hứng, thì thầm, "
            "ngừng kịch tính, nhấn từ khoá gây sốc) để giọng lên xuống như "
            "người thật.\n"
            "· Phát huy TỐI ĐA với giọng 🎧 ElevenLabs (model v3 hiểu audio "
            "tag).\n"
            "· Giọng khác (🔥/⭐ edge, 🌟 Gemini) vẫn hoạt động — tag tự bị "
            "bỏ, giọng đọc bình thường.\n"
            "· Phụ đề LUÔN sạch (không bao giờ hiện [excited] hay CHỮ HOA "
            "nhấn).")
        lay.addWidget(self.emotion)

        # ---- Nút ----
        brow = QHBoxLayout()
        brow.addStretch(1)
        cancel = QPushButton("Hủy")
        cancel.clicked.connect(self.reject)
        brow.addWidget(cancel)
        save = QPushButton("Lưu")
        save.setProperty("primary", True)
        save.setDefault(True)
        save.clicked.connect(self._save)
        brow.addWidget(save)
        lay.addLayout(brow)

        self._load()
        self._fill_voices_bg()
        self._update_el_credit()

    # ------------------------------------------------------------------
    # Nạp / lưu QSettings
    # ------------------------------------------------------------------
    def _load(self) -> None:
        style = str(self._s.value("recap_style", DEFAULT_STYLE) or DEFAULT_STYLE)
        self.style.setCurrentIndex(max(0, self.style.findData(style)))
        try:
            ratio = int(self._s.value("recap_ratio", 45))
        except (TypeError, ValueError):
            ratio = 45
        # MIGRATE NHẸ: 55 (mặc định rất cũ) và 30 (mặc định v1.25 auto-set,
        # user chê nói ÍT quá) -> đều là giá trị KHÔNG do user chủ động chọn
        # -> dùng mặc định mới 45 (giảm vừa phải, không cắt trụi). Giá trị
        # khác giữ nguyên (user tự chọn).
        if ratio in (55, 30):
            ratio = 45
        self.ratio.setValue(min(80, max(15, ratio)))
        self._ratio_changed(self.ratio.value())
        pace = str(self._s.value("recap_pace", "normal") or "normal")
        self.pace.setCurrentIndex(max(0, self.pace.findData(pace)))
        pitch = str(self._s.value("recap_pitch", "normal") or "normal")
        self.pitch.setCurrentIndex(max(0, self.pitch.findData(pitch)))
        # 🎭 Giọng cảm xúc — MẶC ĐỊNH BẬT (QSettings trả chuỗi -> so "false")
        self.emotion.setChecked(
            str(self._s.value("recap_emotion", True)).strip().lower()
            not in ("false", "0", "no", "off"))
        try:                             # âm lượng giọng kể (80-200%)
            vol = int(self._s.value("recap_volume", 115))
        except (TypeError, ValueError):
            vol = 115
        self.volume.setValue(min(200, max(80, vol)))
        self._volume_changed(self.volume.value())
        try:                             # số clip: 0 = Tự động (mặc định)
            cnt = int(self._s.value("recap_count", 0))
        except (TypeError, ValueError):
            cnt = 0
        self.count.setValue(min(3, max(0, cnt)))
        try:                             # min/max số cảnh ghép (mặc định 3-6)
            wmin = int(self._s.value("recap_win_min", 3))
        except (TypeError, ValueError):
            wmin = 3
        try:
            wmax = int(self._s.value("recap_win_max", 6))
        except (TypeError, ValueError):
            wmax = 6
        # set Max TRƯỚC rồi Min: nếu Min lưu > Max lưu, handler tự đẩy Max
        self.win_max.setValue(min(8, max(3, wmax)))
        self.win_min.setValue(min(6, max(2, wmin)))
        # giọng đã lưu: đưa vào combo ngay (list đầy đủ nạp nền sẽ giữ chọn)
        self._want_voice = str(self._s.value("recap_voice", "") or "")
        if self._want_voice:
            self.voice.addItem(self._want_voice, self._want_voice)
            self.voice.setCurrentIndex(self.voice.count() - 1)

    def _save(self) -> None:
        self._s.setValue("recap_voice", self.voice.currentData() or "")
        self._s.setValue("recap_style", self.style.currentData() or DEFAULT_STYLE)
        self._s.setValue("recap_ratio", int(self.ratio.value()))
        self._s.setValue("recap_pace", self.pace.currentData() or "normal")
        self._s.setValue("recap_pitch", self.pitch.currentData() or "normal")
        self._s.setValue("recap_emotion", bool(self.emotion.isChecked()))
        self._s.setValue("recap_volume", int(self.volume.value()))
        self._s.setValue("recap_count", int(self.count.value()))
        wmin, wmax = int(self.win_min.value()), int(self.win_max.value())
        self._s.setValue("recap_win_min", wmin)
        self._s.setValue("recap_win_max", max(wmin, wmax))  # ép Min<=Max
        self.accept()

    def _update_el_credit(self, _i: int = 0) -> None:
        """Đang chọn giọng 🎧 el: -> hiện '🎧 ElevenLabs: còn ~N ký tự'
        (tổng các key, dubbing.eleven_quota cache 5 phút — nạp ở THREAD
        NỀN, không khựng dialog). Giọng khác -> ẩn dòng."""
        vid = str(self.voice.currentData() or "")
        if not vid.startswith("el:"):
            self.el_credit.setVisible(False)
            return
        self.el_credit.setVisible(True)
        self.el_credit.setText("🎧 ElevenLabs: đang kiểm tra credit...")
        out: list = []

        def bg():
            try:
                from app.core.dubbing import eleven_credit_remain
                out.append(eleven_credit_remain())
            except Exception:  # noqa: BLE001 — offline/lỗi -> hiện không rõ
                out.append(None)

        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop()
            timer.deleteLater()
            cur = str(self.voice.currentData() or "")
            if not cur.startswith("el:"):    # user đã đổi giọng trong lúc chờ
                self.el_credit.setVisible(False)
                return
            r = out[0]
            if r is None:
                self.el_credit.setText(
                    "🎧 ElevenLabs: không kiểm tra được credit (mạng/key — "
                    "xem nút 'Kiểm tra credit' trong Cài đặt AI)")
            else:
                self.el_credit.setText(
                    "🎧 ElevenLabs: còn ~{} ký tự (tổng các key)".format(
                        f"{int(r):,}".replace(",", ".")))

        timer.timeout.connect(poll)
        timer.start(200)

    def _win_min_changed(self, v: int) -> None:
        """Kéo Min vượt Max -> Max nhích theo (giữ Min <= Max)."""
        if v > self.win_max.value():
            self.win_max.setValue(v)

    def _win_max_changed(self, v: int) -> None:
        """Hạ Max xuống dưới Min -> Min tụt theo (giữ Min <= Max)."""
        if v < self.win_min.value():
            self.win_min.setValue(min(6, v))

    def _ratio_changed(self, v: int) -> None:
        self.ratio_lbl.setText(
            f"<b>Tỉ lệ AI kể</b> — khoảng <b>{int(v)}%</b> thời lượng clip "
            "là giọng AI (còn lại giữ tiếng gốc) <span style='color:#8a8f98'>"
            "(ít = tập trung video gốc)</span>")

    def _volume_changed(self, v: int) -> None:
        self.vol_lbl.setText(
            f"<b>Âm lượng giọng kể</b> — <b>{int(v)}%</b> so với mức tự cân "
            "theo tiếng gốc video (115% = khuyên dùng)")

    # ------------------------------------------------------------------
    # Danh sách giọng (mạng) — nạp ở thread nền, poll bằng QTimer
    # ------------------------------------------------------------------
    def _fill_voices_bg(self) -> None:
        """Nạp danh sách giọng theo chế độ checkbox 'Hiện tất cả' — cache
        theo phiên chạy; chưa có cache thì gọi mạng ở thread nền."""
        show_all = self.all_chk.isChecked()
        if show_all in _VOICE_CACHE:
            self._set_voices(_VOICE_CACHE[show_all])
            return
        self.count_lbl.setText("Đang tải danh sách giọng...")
        out: list = []

        def bg():
            try:
                from app.core.dubbing import list_recap_voices
                out.append(list_recap_voices(all=show_all))
            except Exception:  # noqa: BLE001 — offline -> giữ combo tối thiểu
                out.append([])

        threading.Thread(target=bg, daemon=True).start()
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop()
            timer.deleteLater()
            if out[0]:
                _VOICE_CACHE[show_all] = out[0]
            # user đã đổi chế độ trong lúc tải -> kết quả cũ, bỏ (lượt
            # _fill_voices_bg của chế độ mới tự lo)
            if self.all_chk.isChecked() == show_all:
                self._set_voices(out[0])

        timer.timeout.connect(poll)
        timer.start(150)

    def _set_voices(self, voices: list) -> None:
        self._voices = list(voices or [])
        self._rebuild_voice_combo()

    def _all_toggled(self, _checked: bool = False) -> None:
        """Bật/tắt 'Hiện tất cả giọng' -> nạp list tương ứng (giữ giọng
        đang chọn)."""
        self._fill_voices_bg()

    def _filtered_voices(self) -> list:
        """List giọng sau khi lọc theo ô 🔎 (khớp nhãn HOẶC voice_id, không
        phân biệt hoa thường). Nhãn nhóm khớp -> giữ CẢ nhóm; nhóm không
        còn giọng nào khớp -> ẩn luôn nhãn nhóm."""
        q = (self.search.text() or "").strip().lower()
        voices = self._voices or []
        if not q:
            return list(voices)
        out: list = []
        hdr = None                       # nhãn nhóm đang chờ (chưa ghi ra)
        hdr_match = False
        for lbl, vid in voices:
            if not vid:                  # dòng nhãn nhóm / thông báo
                hdr, hdr_match = (lbl, vid), q in lbl.lower()
                continue
            if hdr_match or q in lbl.lower() or q in vid.lower():
                if hdr is not None:      # ghi nhãn nhóm 1 lần khi có khớp
                    out.append(hdr)
                    hdr = None
                out.append((lbl, vid))
        return out

    def _rebuild_voice_combo(self, _text: str = "") -> None:
        """Dựng lại combo giọng từ list thô + bộ lọc; giữ giọng đang chọn
        (kể cả khi bị lọc khuất — thêm lại item để không mất lựa chọn)."""
        voices = self._filtered_voices()
        want = self.voice.currentData() or self._want_voice
        self.voice.blockSignals(True)
        self.voice.clear()
        self.voice.addItem(_AUTO_VOICE_LABEL, "")
        for label, vid in voices:
            self.voice.addItem(label, vid)
            if not vid:
                # voice_id rỗng = NHÃN NHÓM ngôn ngữ / dòng thông báo (vd
                # "🌟 Giọng Gemini: dán key... để mở khóa") -> DISABLE,
                # user thấy nhưng không chọn được.
                try:
                    it = self.voice.model().item(self.voice.count() - 1)
                    if it is not None:
                        it.setEnabled(False)
                except AttributeError:   # model lạ (an toàn phòng xa)
                    pass
        if want:
            i = self.voice.findData(want)
            if i <= 0:                   # giọng lưu cũ/bị lọc khuất -> thêm lại
                self.voice.addItem(want, want)
                i = self.voice.count() - 1
            self.voice.setCurrentIndex(i)
        self.voice.blockSignals(False)
        # Đếm giọng chọn được: "Đang có N giọng" / "Khớp M/N giọng" khi lọc
        n = sum(1 for _l, v in (self._voices or []) if v)
        m = sum(1 for _l, v in voices if v)
        if not self._voices:
            self.count_lbl.setText("")
        elif m != n:
            self.count_lbl.setText(f"Khớp {m}/{n} giọng")
        else:
            self.count_lbl.setText(f"Đang có {n} giọng")
        # combo rebuild với blockSignals -> currentIndexChanged không bắn;
        # tự cập nhật dòng credit ElevenLabs theo giọng đang chọn.
        if hasattr(self, "el_credit"):
            self._update_el_credit()

    # ------------------------------------------------------------------
    # 🔊 Nghe thử (pattern editor._dub_preview — winsound, thread nền)
    # ------------------------------------------------------------------
    def _preview(self) -> None:
        voice = self.voice.currentData() or ""
        if not voice:                     # "Tự chọn" -> demo giọng hot mặc định
            voice = "en-US-AndrewMultilingualNeural"
        pace = self.pace.currentData() or "normal"
        pitch = self.pitch.currentData() or "normal"
        emotion = bool(self.emotion.isChecked())
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except (ImportError, RuntimeError):
            pass
        self.prev_btn.setEnabled(False)
        self.prev_btn.setText("Đang đọc…")
        tmp = tempfile.gettempdir()
        for old in glob.glob(os.path.join(tmp, "_recapdemo_*.*")):
            try:
                os.remove(old)
            except OSError:
                pass
        uid = uuid.uuid4().hex[:8]
        mp3 = os.path.join(tmp, f"_recapdemo_{uid}.mp3")
        wav = os.path.join(tmp, f"_recapdemo_{uid}.wav")

        def work():
            try:
                from app.core.dubbing import (
                    gemini_narrate_prefix, norm_lang, recap_pace_rate,
                    recap_pitch_hz, synth_demo,
                )
                if voice.startswith("gemini:"):
                    lang = "vi"
                    txt = gemini_narrate_prefix(lang) + _DEMO_NARR[lang]
                else:
                    lang = norm_lang(voice.split("-")[0])
                    txt = _DEMO_NARR.get(lang) or _DEMO_NARR["en"]
                # nghe thử áp CẢ nhịp kể + tông giọng đang chọn (Gemini
                # bỏ qua cả 2 — synth_demo tự xử)
                # 🎭 emotion CHỈ áp giọng ElevenLabs (v3 hiểu tag); giọng
                # khác synth_demo tự bỏ qua.
                if not synth_demo(voice, mp3, text=txt,
                                  rate=recap_pace_rate(pace),
                                  pitch=recap_pitch_hz(pitch),
                                  emotion=emotion):
                    self._demo_ready.emit("")
                    return
                import shutil
                from config import settings
                from app.core.ffmpeg_utils import _CREATE_NO_WINDOW
                ff = (shutil.which("ffmpeg") or settings.FFMPEG_PATH
                      or r"C:\ffmpeg\ffmpeg.exe")
                r = subprocess.run(
                    [ff, "-nostdin", "-y", "-i", mp3, wav],
                    capture_output=True, timeout=60,
                    creationflags=_CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL)
                ok = (r.returncode == 0 and os.path.exists(wav)
                      and os.path.getsize(wav) > 5000)
                self._demo_ready.emit(wav if ok else "")
            except Exception:  # noqa: BLE001
                self._demo_ready.emit("")

        threading.Thread(target=work, daemon=True).start()

    def _play_demo(self, path: str) -> None:
        self.prev_btn.setText("🔊 Nghe thử")
        self.prev_btn.setEnabled(True)
        if not path or not os.path.exists(path):
            QMessageBox.information(
                self, "Nghe thử lỗi",
                "Không đọc thử được giọng này (kiểm tra mạng + ffmpeg rồi "
                "thử lại).")
            return
        try:
            import winsound
            winsound.PlaySound(
                path, winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
        except (ImportError, RuntimeError) as e:
            QMessageBox.warning(
                self, "Nghe thử lỗi",
                f"Không phát được âm thanh trên máy này:\n{e}")
