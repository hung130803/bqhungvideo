"""
Hộp thoại "Cài đặt Reup thuyết minh" (nút ⚙ cạnh nút 🎙 ở màn hình chính).

Cài đặt TOÀN CỤC cho mọi kênh (lưu QSettings — không dính vào mẫu template):
  - recap_voice : giọng KỂ. "" = tự chọn theo ngôn ngữ video (khuyên dùng);
                  hoặc chọn cứng 1 giọng (🌟 Gemini / ⭐ giọng hot edge-tts).
                  Mẫu template KHÔNG còn quyết định giọng thuyết minh —
                  dub_voice của mẫu chỉ dành cho dịch lồng tiếng thường.
  - recap_style : phong cách kể (đồng bộ 2 CHIỀU với combo cạnh nút 🎙 —
                  cùng key QSettings, studio_page nạp lại sau khi đóng).
  - recap_ratio : tỉ lệ % thời lượng AI kể (30-80, mặc định 55) -> prompt.
  - recap_pace  : nhịp kể slow/normal/fast -> rate edge-tts -3%/0%/+4%
                  (giọng Gemini: prepend chỉ dẫn kể chuyện vào text TTS).

Nút "🔊 Nghe thử": synth câu demo kiểu kể chuyện (có "...") bằng giọng + nhịp
đang chọn — synth ở thread nền, phát bằng winsound (như editor._dub_preview).
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
    QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSlider, QVBoxLayout,
)

from app.ai.recap import DEFAULT_STYLE, STYLES

# Câu demo NGHE THỬ kiểu kể chuyện (có "..." tạo khựng đúng vibe narrator).
_DEMO_NARR = {
    "vi": "Không ai ngờ nổi... điều gã này sắp làm. Kể cả tôi.",
    "en": "Nobody saw this coming... not even him. And then... it happened.",
}

# Nhịp kể: (nhãn, key QSettings). Key -> rate edge-tts ở dubbing.RECAP_PACES.
_PACES = [("Thong thả", "slow"), ("Vừa", "normal"), ("Dồn dập", "fast")]

_AUTO_VOICE_LABEL = "Tự chọn theo ngôn ngữ video (khuyên dùng)"

# cache danh sách giọng cho phiên chạy (đỡ gọi mạng mỗi lần mở dialog)
_VOICE_CACHE: list = []


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
            "video.\nChọn cứng 1 giọng (🌟 Gemini nét nhất — cần key; ⭐ đa "
            "ngữ đọc được mọi thứ tiếng) nếu muốn mọi clip cùng giọng.")
        self.voice.addItem(_AUTO_VOICE_LABEL, "")
        vrow.addWidget(self.voice, 1)
        self.prev_btn = QPushButton("🔊 Nghe thử")
        self.prev_btn.setToolTip("Đọc thử 1 câu kể chuyện bằng giọng + nhịp "
                                 "đang chọn.")
        self.prev_btn.clicked.connect(self._preview)
        vrow.addWidget(self.prev_btn)
        lay.addLayout(vrow)

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
        self.ratio.setRange(30, 80)
        self.ratio.setToolTip(
            "AI kể chiếm bao nhiêu % thời lượng clip (phần còn lại giữ "
            "tiếng gốc).\nÍt = tôn tiếng gốc; nhiều = kể dày như kênh recap.")
        self.ratio.valueChanged.connect(self._ratio_changed)
        lay.addWidget(self.ratio)

        # ---- Nhịp kể ----
        lay.addWidget(QLabel("<b>Nhịp kể</b> — tốc độ giọng đọc"))
        self.pace = QComboBox()
        for label, key in _PACES:
            self.pace.addItem(label, key)
        self.pace.setToolTip("Thong thả = chậm rãi kịch tính · Dồn dập = "
                             "nhanh giữ nhịp TikTok.")
        lay.addWidget(self.pace)

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

    # ------------------------------------------------------------------
    # Nạp / lưu QSettings
    # ------------------------------------------------------------------
    def _load(self) -> None:
        style = str(self._s.value("recap_style", DEFAULT_STYLE) or DEFAULT_STYLE)
        self.style.setCurrentIndex(max(0, self.style.findData(style)))
        try:
            ratio = int(self._s.value("recap_ratio", 55))
        except (TypeError, ValueError):
            ratio = 55
        self.ratio.setValue(min(80, max(30, ratio)))
        self._ratio_changed(self.ratio.value())
        pace = str(self._s.value("recap_pace", "normal") or "normal")
        self.pace.setCurrentIndex(max(0, self.pace.findData(pace)))
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
        self.accept()

    def _ratio_changed(self, v: int) -> None:
        self.ratio_lbl.setText(
            f"<b>Tỉ lệ AI kể</b> — khoảng <b>{int(v)}%</b> thời lượng clip "
            "là giọng AI (còn lại giữ tiếng gốc)")

    # ------------------------------------------------------------------
    # Danh sách giọng (mạng) — nạp ở thread nền, poll bằng QTimer
    # ------------------------------------------------------------------
    def _fill_voices_bg(self) -> None:
        if _VOICE_CACHE:
            self._fill_voices(_VOICE_CACHE[0])
            return
        out: list = []

        def bg():
            try:
                from app.core.dubbing import list_recap_voices
                out.append(list_recap_voices())
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
                _VOICE_CACHE.clear()
                _VOICE_CACHE.append(out[0])
            self._fill_voices(out[0])

        timer.timeout.connect(poll)
        timer.start(150)

    def _fill_voices(self, voices: list) -> None:
        want = self.voice.currentData() or self._want_voice
        self.voice.blockSignals(True)
        self.voice.clear()
        self.voice.addItem(_AUTO_VOICE_LABEL, "")
        for label, vid in voices or []:
            self.voice.addItem(label, vid)
        if want:
            i = self.voice.findData(want)
            if i < 0:                    # giọng lưu cũ không còn trong list
                self.voice.addItem(want, want)
                i = self.voice.count() - 1
            self.voice.setCurrentIndex(i)
        self.voice.blockSignals(False)

    # ------------------------------------------------------------------
    # 🔊 Nghe thử (pattern editor._dub_preview — winsound, thread nền)
    # ------------------------------------------------------------------
    def _preview(self) -> None:
        voice = self.voice.currentData() or ""
        if not voice:                     # "Tự chọn" -> demo giọng hot mặc định
            voice = "en-US-AndrewMultilingualNeural"
        pace = self.pace.currentData() or "normal"
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
                    synth_demo,
                )
                if voice.startswith("gemini:"):
                    lang = "vi"
                    txt = gemini_narrate_prefix(lang) + _DEMO_NARR[lang]
                else:
                    lang = norm_lang(voice.split("-")[0])
                    txt = _DEMO_NARR.get(lang) or _DEMO_NARR["en"]
                if not synth_demo(voice, mp3, text=txt,
                                  rate=recap_pace_rate(pace)):
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
