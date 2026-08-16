# -*- coding: utf-8 -*-
"""HỘP THAY GIỌNG NÓI — thay lời thoại cả THƯ MỤC video sang tiếng khác.

Anh Hùng dùng thật v2.26.0 rồi báo 4 điều, bản này sửa đúng 4 điều đó:

1. *"ấn chạy thì nó chỉ hiện cái thanh tiến trình, không hiện gì cả, xong hay
   gì cũng không báo, hay đang phân tích như nào cũng không thấy"* -> **BẢNG
   TIẾN ĐỘ SỐNG**: bấm Chạy là MỖI VIDEO MỘT DÒNG hiện ngay (kể cả video chưa
   tới lượt = "Đang chờ"), trạng thái đổi theo BƯỚC THẬT (`tg_so
   .buoc_tu_tien_trinh` đọc tiến trình + lời nhắn của chính
   `thay_giong_video`), cột tiến trình ghi `% · bước mấy/mấy`, xong cả lượt thì
   có DÒNG TỔNG KẾT + hộp báo.
2. *"cho tôi tự chọn thư mục ĐẦU VÀO thư mục ĐẦU RA đi, KHÔNG CẦN cái thùng
   rác phân tích thay giọng rồi tự xoá đâu nhé"* -> **2 ô thư mục**, video gốc
   **KHÔNG BAO GIỜ bị đụng tới**; ô "đưa vào Thùng rác" và đường
   `delete_or_recycle` đã bỏ hẳn khỏi luồng này.
3. *"nếu cái nào phân tích thay lỗi phải có mục CHẠY LẠI"* -> chuột phải vào
   dòng: **Làm lại video này · Làm lại tất cả · Bỏ qua video này**; video LỖI
   thì lượt Chạy sau TỰ làm lại (lỗi ≠ đã xong).
4. *"ấn chạy chỉ chạy những video CHƯA chạy xong thôi"* -> sổ trạng thái
   `app/core/tg_so.py` ghi RA ĐĨA (tắt app/tự cập nhật vẫn nhớ).

BA CHỐT AN TOÀN CỦA MÀN NÀY (đừng gỡ cái nào):

1. **THIẾU BỘ TÁCH GIỌNG -> CHẶN, KHÔNG LÙI.** Bản `.exe` không gói
   torch/demucs (`requirements-build.txt` ghi thẳng "KHÔNG gói torch") nên
   máy nhân viên KHÔNG chạy được. App tự dò; thiếu thì hiện nút
   `Tải bộ tách giọng (khoảng 2 GB)` và **KHOÁ nút Chạy**. TUYỆT ĐỐI không
   tự lui sang "cách nhẹ": đã đo rò rỉ lời **100% (Trung) · 86,3% (Anh)** —
   giọng cũ còn NGUYÊN chồng lên giọng mới, ffmpeg vẫn trả mã 0, không một
   dòng báo. Trên 200-300 kênh là hỏng hàng loạt không ai biết.

2. **KHÔNG ĐỤNG VIDEO GỐC.** Bản mới ghi sang THƯ MỤC ĐÍCH; nguồn trùng đích
   thì CẢNH BÁO và không xếp job nào (ghi đè = mất gốc). Thư mục làm việc tạm
   cũng nằm trong thư mục ĐÍCH, để thư mục nguồn sạch đúng như anh Hùng dặn.

3. **ĐA LUỒNG ĐI QUA BỘ ĐIỀU PHỐI**, làn RIÊNG `worker.LAN_TG` — mỗi video
   một job nên tắt app giữa chừng vẫn chạy tiếp được, và bấm Huỷ được từng
   video. Không tự đẻ ThreadPool trong UI.

**NHÃN TIẾNG VIỆT, KHÔNG EMOJI** — máy anh Hùng thiếu glyph nên emoji ra Ô
ĐEN. Danh sách giọng tái dùng `dubbing.list_recap_voices()` của hộp Cài đặt
Reup nhưng phải đi qua `bo_emoji()` vì nhãn gốc có cờ/biểu tượng.
"""
from __future__ import annotations

import json
import os
import threading
import unicodedata
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from app.core import tg_chay, tg_so
from app.core import thay_giong as TG
from app.database import db
from app.ui.appsettings import app_settings
from app.ui.theme import (
    ACCENT, BASE, BORDER, DANGER, MUTED, SUCCESS, SURFACE, TEXT, WARN,
)

#: Khoá QSettings — đủ để mở lại hộp là thấy y nguyên lần trước.
K_THUMUC = "tg_thu_muc"
K_THUMUC_RA = "tg_thu_muc_ra"
K_NGON_NGU = "tg_ngon_ngu"
K_GIONG = "tg_giong"
K_LUONG = "tg_luong"
K_CHE_CHU = "tg_che_chu"
K_CHE_CACH = "tg_che_cach"
K_CHE_MUC = "tg_che_muc"
K_VIET_CHU = "tg_viet_chu"

#: Nhãn mục đầu combo giọng. Phải NÓI RA mặc định thật, không ghi trơn
#: "(tự chọn)" — bài học cổng 16 v2.6.25a: user tưởng là CHƯA chọn gì.
NHAN_GIONG_TU = "Tự chọn theo ngôn ngữ đích (khuyên dùng)"

#: Trạng thái hiện ở cột 2 khi video bị BỎ QUA vì đã xong (anh Hùng phải đọc
#: được LÝ DO nó không chạy, không phải im lặng bỏ).
CHU_DA_XONG = "Đã xong — bỏ qua"

#: cache danh sách giọng cho cả phiên chạy (đỡ gọi mạng mỗi lần mở hộp)
_CACHE_GIONG: list = []


def bo_emoji(s: str) -> str:
    """Bỏ emoji/cờ/ký hiệu khỏi nhãn — máy anh Hùng thiếu font, ra Ô ĐEN.

    Giữ nguyên chữ có dấu tiếng Việt (loại `Lo`/`Ll`... đều giữ), chỉ vứt
    nhóm `So` (Symbol, other = emoji + cờ) và các ký tự ngoài BMP.
    """
    ra = []
    for c in s or "":
        if ord(c) > 0xFFFF:                     # emoji/cờ ngoài BMP
            continue
        if unicodedata.category(c) == "So":     # ký hiệu (⭐ 🔥 …)
            continue
        ra.append(c)
    return " ".join("".join(ra).split())


def giong_dung_duoc(ds: list) -> list:
    """Lọc danh sách giọng về ĐÚNG cái `thay_giong` đọc được (edge-tts).

    `doc_ban_dich` gọi thẳng `dubbing._synth_all` — hàm này CHỈ biết edge-tts.
    Đưa id `gemini:` / `el:` vào là câu nào cũng hỏng mà UI vẫn khoe có chọn.
    Nhãn nhóm (voice_id rỗng) giữ lại để combo còn phân nhóm ngôn ngữ.
    """
    ra: list = []
    for nhan, vid in ds or []:
        v = str(vid or "")
        if v.startswith("gemini:") or v.startswith("el:"):
            continue
        ra.append((bo_emoji(str(nhan)), v))

    # ---- BIẾN THỂ GIỌNG VIỆT (đổi `pitch`) ----
    # edge-tts chỉ có 2 giọng tiếng Việt; `thay_giong.BIEN_THE_PITCH` sinh
    # thêm mức cao độ ĐÃ ĐO (xem `_do_bien_the_giong.py`). Chèn NGAY SAU giọng
    # gốc tương ứng để combo đọc theo cụm, và BỎ QUA mức `+0Hz` — mã của nó
    # trùng đúng id giọng gốc đã có ở trên, thêm nữa là hai dòng y hệt nhau.
    bt: dict[str, list] = {}
    for ma, nhan in TG.bien_the_giong():
        goc = TG.tach_giong_pitch(ma)[0]
        if ma != goc:                       # `+0Hz` -> mã == giọng gốc -> bỏ
            bt.setdefault(goc, []).append((nhan, ma))
    mo_rong: list = []
    for nhan, vid in ra:
        mo_rong.append((nhan, vid))
        mo_rong.extend(bt.get(vid, []))

    # ---- GIỌNG PIPER — LỰA CHỌN THỨ HAI, chạy hẳn trên máy ----
    # CHỈ MỘT giọng được phép có mặt: `vais1000` (trọng số MIT + dữ liệu
    # CC BY 4.0 -> bán được, ghi công ở `LICENSES.txt` mục 4). Hai giọng Việt
    # còn lại của Piper BỊ CẤM: `vivos` là CC BY-NC-SA (cấm thương mại) và
    # thiếu dấu thanh; `25hours_single` ghi "License: Unknown" — im lặng
    # KHÔNG phải là cho phép. Cổng 64 quét đúng hai cái tên đó.
    #
    # Chèn NGAY SAU cụm giọng Việt để anh Hùng thấy cùng chỗ. Nhãn nói THẲNG
    # khi chưa tải, vì lúc đó app LÙI về edge-tts — người chọn phải biết
    # trước, không để họ tưởng đang nghe Piper.
    try:
        from app.core import piper_tts
        nhan_p = piper_tts.NHAN_GIONG
        if not piper_tts.co_piper():
            nhan_p += " — chưa tải, sẽ dùng giọng thường"
        cuoi_vi = max((i for i, (_n, v) in enumerate(mo_rong)
                       if str(v).startswith("vi-VN")), default=-1)
        mo_rong.insert(cuoi_vi + 1, (nhan_p, piper_tts.MA_GIONG))
    except Exception:  # noqa: BLE001
        pass                                # thiếu module -> combo y hệt cũ

    # nhóm rỗng (bị lọc sạch) thì bỏ luôn nhãn nhóm, đừng để dòng trơ
    gon: list = []
    for i, (nhan, vid) in enumerate(mo_rong):
        if vid:
            gon.append((nhan, vid))
            continue
        con = any(v for _n, v in mo_rong[i + 1:i + 2])
        if con:
            gon.append((nhan, vid))
    return gon


class ThayGiongDialog(QDialog):
    """Chọn thư mục vào/ra · ngôn ngữ · giọng · số luồng -> xếp job, xem tiến
    độ TỪNG VIDEO, chuột phải để làm lại."""

    _giong_xong = pyqtSignal()          # danh sách giọng nạp xong (thread nền)
    _cai_xong = pyqtSignal(bool, str)   # tải bộ tách giọng xong (ok, lời)
    _piper_xong = pyqtSignal(bool, str)  # tải giọng Piper xong (ok, lời)
    #: (đường dẫn video, trạng thái, tiến trình 0..1) — bắn MỖI LẦN một dòng
    #: ĐỔI trạng thái. Cổng test bắt tín hiệu này để đo "bảng có sống không"
    #: thay vì nhìn bằng mắt.
    doi_trang_thai = pyqtSignal(str, str, float)
    #: (số xong, số lỗi, số huỷ, số bỏ qua) — bắn ĐÚNG MỘT LẦN khi cả lượt kết
    #: thúc. Anh Hùng: "xong hay gì cũng không báo".
    xong_ca_luot = pyqtSignal(int, int, int, int)

    def __init__(self, pool, parent=None, thung_rac: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Thay giọng nói cho cả thư mục")
        self.resize(1000, 660)
        self._pool = pool
        self._s = app_settings()
        # `thung_rac` GIỮ LẠI trong chữ ký cho lối gọi cũ (studio_page) nhưng
        # KHÔNG dùng nữa: luồng này không xoá/dọn video gốc nữa.
        self._thung_rac = thung_rac
        self._jobs: dict[str, int] = {}     # đường dẫn video -> job id
        self._xong_id: dict[int, dict] = {}  # job đã kết thúc -> khỏi hỏi DB
        self._tt_dong: dict[str, str] = {}   # dòng -> trạng thái ĐANG hiện
        self._dang_cai = False
        self._dang_cai_piper = False
        self._tt_piper: dict = {}
        self._giong_tho: list = []
        self._da_bao_xong = True            # chưa chạy lượt nào -> không báo
        self._bo_qua_luot = 0               # số video bỏ qua ở lượt vừa bấm

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(9)

        gt = QLabel(
            "Thay LỜI THOẠI của video sang tiếng khác, GIỮ NGUYÊN nhạc nền và "
            "tiếng động hiện trường. Video MỚI ghi vào Thư mục đích — video "
            "gốc GIỮ NGUYÊN, app không xoá/không di chuyển gì cả.")
        gt.setWordWrap(True)
        gt.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        lay.addWidget(gt)

        # ---- hàng 1: THƯ MỤC NGUỒN ----
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Thư mục nguồn:"))
        self.ed_thu_muc = QLineEdit(str(self._s.value(K_THUMUC, "") or ""))
        self.ed_thu_muc.setPlaceholderText(
            "Chọn thư mục chứa video cần thay giọng")
        self.ed_thu_muc.textChanged.connect(self._doi_thu_muc)
        h1.addWidget(self.ed_thu_muc, 1)
        b_chon = QPushButton("Chọn thư mục nguồn...")
        b_chon.clicked.connect(self._chon_thu_muc)
        h1.addWidget(b_chon)
        lay.addLayout(h1)

        # ---- hàng 1b: THƯ MỤC ĐÍCH ----
        h1b = QHBoxLayout()
        h1b.addWidget(QLabel("Thư mục đích:"))
        self.ed_thu_muc_ra = QLineEdit(
            str(self._s.value(K_THUMUC_RA, "") or ""))
        self.ed_thu_muc_ra.setPlaceholderText(
            "Để trống = tự tạo thư mục _da_thay_tieng bên trong thư mục nguồn")
        self.ed_thu_muc_ra.textChanged.connect(self._doi_thu_muc_ra)
        h1b.addWidget(self.ed_thu_muc_ra, 1)
        b_chon_ra = QPushButton("Chọn thư mục đích...")
        b_chon_ra.clicked.connect(self._chon_thu_muc_ra)
        h1b.addWidget(b_chon_ra)
        lay.addLayout(h1b)

        self.lb_dich = QLabel("")
        self.lb_dich.setWordWrap(True)
        self.lb_dich.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        lay.addWidget(self.lb_dich)

        # ---- hàng 2: ngôn ngữ · giọng · số luồng ----
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Ngôn ngữ đích:"))
        self.cb_nn = QComboBox()
        for nhan, ma in TG.NGON_NGU_DICH:
            self.cb_nn.addItem(nhan, ma)
        i = self.cb_nn.findData(str(self._s.value(K_NGON_NGU, "en") or "en"))
        self.cb_nn.setCurrentIndex(max(0, i))
        self.cb_nn.currentIndexChanged.connect(self._doi_ngon_ngu)
        h2.addWidget(self.cb_nn)

        h2.addSpacing(8)
        h2.addWidget(QLabel("Giọng đọc:"))
        self.cb_giong = QComboBox()
        self.cb_giong.setMinimumWidth(300)
        self.cb_giong.addItem(NHAN_GIONG_TU, "")
        h2.addWidget(self.cb_giong, 1)

        h2.addSpacing(8)
        h2.addWidget(QLabel("Số luồng:"))
        self.sp_luong = QSpinBox()
        self.sp_luong.setRange(1, 4)
        self.sp_luong.setToolTip(
            "Số video làm CÙNG LÚC. Bộ tách giọng ăn khoảng 1,3 GB RAM mỗi "
            "video nên quá 4 là máy đảo trang, chậm hơn chứ không nhanh hơn.\n"
            "Đo thật: 2 video / 2 luồng = 74,97 giây (chạy lần lượt ~120 "
            "giây).")
        try:
            self.sp_luong.setValue(int(self._s.value(K_LUONG, 2) or 2))
        except (TypeError, ValueError):
            self.sp_luong.setValue(2)
        h2.addWidget(self.sp_luong)
        lay.addLayout(h2)

        # ---- hàng 3: CHE CHỮ CHÁY SẴN TRONG HÌNH ----
        # Ô này CỐ Ý đặt Ở ĐÂY chứ không bắt sang "Chỉnh mẫu": thay tiếng và
        # xuất clip là HAI ĐƯỜNG KHÁC NHAU (anh Hùng 14/08/2026 bật ô bên kia
        # rồi tưởng đã bật, chữ vẫn còn nguyên). Nhãn TIẾNG VIỆT, KHÔNG EMOJI.
        h3 = QHBoxLayout()
        self.ck_che = QCheckBox("Làm mờ chữ cháy sẵn trong hình")
        self.ck_che.setToolTip(
            "Video nguồn (Douyin/reup) thường ĐỐT phụ đề THẲNG VÀO KHUNG "
            "hình — gỡ ra không được, thay tiếng xong dòng chữ cũ vẫn nằm "
            "đó.\nBật ô này để app dò dải chữ ở đáy khung rồi che đi.\n\n"
            "Đã đo: dò đúng 96,7% · che oan 0/76 video sạch · bỏ sót 9,1%.\n"
            "LƯU Ý: bật ô này thì phải MÃ HOÁ LẠI luồng hình (tắt thì chép "
            "nguyên, không đụng tới hình), nên lượt chạy lâu hơn.")
        self.ck_che.setChecked(
            str(self._s.value(K_CHE_CHU, "0")) in ("1", "true", "True"))
        h3.addWidget(self.ck_che)

        h3.addSpacing(8)
        h3.addWidget(QLabel("Cách che:"))
        self.cb_che_cach = QComboBox()
        self.cb_che_cach.addItem("Làm mờ (ít lộ)", "mo")
        self.cb_che_cach.addItem("Phủ khối đặc (chắc chắn, nhưng lộ)", "khoi")
        i = self.cb_che_cach.findData(str(self._s.value(K_CHE_CACH, "mo")))
        self.cb_che_cach.setCurrentIndex(max(0, i))
        h3.addWidget(self.cb_che_cach)

        h3.addSpacing(8)
        h3.addWidget(QLabel("Mức mờ:"))
        self.sp_che_muc = QDoubleSpinBox()
        # SÀN 0,60 là SÀN CỨNG trong mã (`che_chu.chuan_muc_mo`) — đặt sàn ở
        # đây nữa để anh Hùng không kéo xuống chỗ mắt vẫn đọc được chữ (mức
        # 0,40 đo ra "sạch" theo máy mà PNG vẫn đọc rõ 这时医生灵机一动).
        self.sp_che_muc.setRange(0.60, 2.00)
        self.sp_che_muc.setSingleStep(0.10)
        self.sp_che_muc.setToolTip(
            "Càng cao càng mờ. Dưới 0,60 mắt vẫn đọc được chữ (đã đo) nên "
            "app KHÔNG cho hạ thấp hơn.")
        try:
            self.sp_che_muc.setValue(float(self._s.value(K_CHE_MUC, 1.0) or 1.0))
        except (TypeError, ValueError):
            self.sp_che_muc.setValue(1.0)
        h3.addWidget(self.sp_che_muc)
        h3.addStretch(1)
        lay.addLayout(h3)

        # ---- hàng 3b: VIẾT LẠI BẢN DỊCH THEO MỐC GIỌNG ----
        # Lỗi anh Hùng nghe+xem 14/08/2026: "chữ dịch ở dưới vẫn chạy mà trên
        # đáng lý ra phải nói mà k có nói, 1 lúc sau nó lại tự nói". Chữ cháy
        # sẵn chạy theo NGƯỜI NÓI GỐC, giọng mới chạy theo bản chép lời — đo
        # ra 24,2% thời lượng video là "chữ chạy mà không ai nói".
        h3b = QHBoxLayout()
        self.ck_viet = QCheckBox("Viết lại bản dịch theo đúng lúc giọng nói")
        self.ck_viet.setToolTip(
            "Sau khi che dòng chữ cũ, app viết BẢN DỊCH vào đúng dải đó, mốc "
            "lấy từ CHÍNH FILE GIỌNG vừa sinh ra (đo bằng silencedetect).\n"
            "Giọng nói ở đâu thì chữ hiện ở đó — không thể lệch nhau nữa.\n\n"
            "Đã đo trên video thật: TẮT ô này thì 12,96% số dòng chữ hiện lên "
            "trước tiếng quá 150 ms, dòng tệ nhất chờ 5.057 ms.\n"
            "Chỉ dùng được khi ô 'Làm mờ chữ cháy sẵn' đang BẬT — không che "
            "mà viết là hai lớp chữ chồng nhau.")
        self.ck_viet.setChecked(
            str(self._s.value(K_VIET_CHU, "1")) in ("1", "true", "True"))
        h3b.addWidget(self.ck_viet)
        h3b.addStretch(1)
        lay.addLayout(h3b)

        self.ck_che.toggled.connect(self._doi_che_chu)
        self._doi_che_chu(self.ck_che.isChecked())

        # ---- hàng 4: TÌNH TRẠNG BỘ TÁCH GIỌNG (chốt an toàn số 1) ----
        h4 = QHBoxLayout()
        self.lb_demucs = QLabel("")
        self.lb_demucs.setWordWrap(True)
        h4.addWidget(self.lb_demucs, 1)
        self.b_tai = QPushButton(TG.NHAN_TAI_DEMUCS)
        self.b_tai.setToolTip(
            "Tải bộ tách giọng (Demucs + torch) vào thư mục riêng _lib.\n"
            "Chỉ tải khi BẠN bấm — app không bao giờ tự tải sau lưng.")
        self.b_tai.clicked.connect(self._tai_demucs)
        h4.addWidget(self.b_tai)
        lay.addLayout(h4)
        self.pb_tai = QProgressBar()
        self.pb_tai.setRange(0, 100)
        self.pb_tai.setVisible(False)
        lay.addWidget(self.pb_tai)

        # ---- hàng 4b: GIỌNG PIPER (lựa chọn thứ hai, chạy trên máy) ----
        # KHÁC hẳn hàng Demucs ở trên: thiếu Demucs là CHẶN (lùi ra video
        # hỏng), còn thiếu Piper chỉ là LÙI ÊM về edge-tts (video vẫn đúng,
        # chỉ khác giọng). Nên hàng này KHÔNG khoá nút Chạy.
        h4b = QHBoxLayout()
        self.lb_piper = QLabel("")
        self.lb_piper.setWordWrap(True)
        h4b.addWidget(self.lb_piper, 1)
        self.b_tai_piper = QPushButton("Tải giọng Việt chạy trên máy")
        # DUNG LƯỢNG LÀ SỐ ĐO, KHÔNG PHẢI ƯỚC BỪA (bài học cổng 58: nhãn
        # Demucs từng ghi "khoảng 2 GB" trong khi lượng tải thật là 154 MB —
        # gấp 13 lần). Chạy thật `cai_piper` vào hộp cát: **36,8 giây**, chiếm
        # **212,4 MB** trên đĩa (bộ đọc + onnxruntime + numpy + giọng 63 MB).
        self.b_tai_piper.setToolTip(
            "Tải bộ đọc Piper + giọng vais1000 về thư mục riêng.\n"
            "Đo thật: 212 MB trên đĩa, khoảng 37 giây.\n"
            "Chỉ tải khi BẠN bấm — app không bao giờ tự tải sau lưng.\n"
            "Tải THẲNG từ kho GitHub của tác giả Piper.")
        self.b_tai_piper.clicked.connect(self._tai_piper)
        h4b.addWidget(self.b_tai_piper)
        lay.addLayout(h4b)
        self._do_piper()

        # ---- bảng tiến độ ----
        self.bang = QTableWidget(0, 4)
        self.bang.setHorizontalHeaderLabels(
            ["Video", "Trạng thái", "Tiến trình", "Ghi chú"])
        self.bang.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bang.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.bang.verticalHeader().setVisible(False)
        self.bang.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.bang.customContextMenuRequested.connect(self._menu_dong)
        self.bang.setStyleSheet(
            f"QTableWidget {{ background:{BASE}; border:1px solid {BORDER};"
            f" border-radius:8px; gridline-color:{BORDER}; color:{TEXT}; }}"
            f"QTableWidget::item {{ padding:3px 8px; }}"
            f"QTableWidget::item:selected {{ background:{ACCENT};"
            f" color:white; }}"
            f"QHeaderView::section {{ background:{SURFACE}; color:{TEXT};"
            f" padding:6px 8px; border:none;"
            f" border-bottom:1px solid {BORDER}; font-weight:600; }}")
        hh = self.bang.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        self.bang.setColumnWidth(0, 300)
        self.bang.setColumnWidth(1, 150)
        self.bang.setColumnWidth(2, 130)
        lay.addWidget(self.bang, 1)

        lb_meo = QLabel(
            "Mẹo: bấm CHUỘT PHẢI vào một dòng để Làm lại video đó · Làm lại "
            "tất cả · Bỏ qua video đó.")
        lb_meo.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        lay.addWidget(lb_meo)

        # ---- hàng cuối: nút ----
        h5 = QHBoxLayout()
        self.lb_tt = QLabel("")
        self.lb_tt.setWordWrap(True)
        self.lb_tt.setStyleSheet(f"color:{MUTED};")
        h5.addWidget(self.lb_tt, 1)
        self.b_chay = QPushButton("Chạy")
        self.b_chay.setProperty("primary", True)
        # lambda: nút bắn kèm cờ `checked` -> vào thẳng tham số `lam_lai`
        self.b_chay.clicked.connect(lambda: self._chay())
        h5.addWidget(self.b_chay)
        self.b_lam_lai = QPushButton("Làm lại tất cả")
        self.b_lam_lai.setToolTip(
            "Quên hết trạng thái đã lưu của các video ĐANG HIỆN rồi chạy lại "
            "từ đầu. Video gốc vẫn không bị đụng tới.")
        self.b_lam_lai.clicked.connect(lambda: self._lam_lai_tat_ca())
        h5.addWidget(self.b_lam_lai)
        self.b_dung = QPushButton("Dừng tất cả")
        self.b_dung.clicked.connect(self._dung)
        h5.addWidget(self.b_dung)
        b_dong = QPushButton("Đóng")
        b_dong.clicked.connect(self.reject)
        h5.addWidget(b_dong)
        lay.addLayout(h5)

        self._giong_xong.connect(self._dung_combo_giong)
        self._cai_xong.connect(self._cai_demucs_xong)
        self._piper_xong.connect(self._tai_piper_xong)

        self._do_demucs()
        self._nap_giong_nen()
        self._doi_thu_muc()

        # Nhịp riêng của hộp — hộp mở bằng exec() nên vòng lặp sự kiện của nó
        # vẫn chạy timer bình thường.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._nhip)
        self._timer.start(700)

    # ------------------------------------------------------------------
    # BỘ TÁCH GIỌNG
    # ------------------------------------------------------------------
    def _do_demucs(self) -> dict:
        """Dò bộ tách giọng rồi cập nhật nhãn + KHOÁ/MỞ nút Chạy."""
        tt = TG.tinh_trang_demucs()
        self._tt_demucs = tt
        # Nút phải bám `thieu` (sự thật của `_lib`) chứ KHÔNG bám `co` (máy này
        # chạy được không). Bám `co` chính là cách bản cũ giấu mất việc `_lib`
        # thiếu torch: máy dev mượn được của `.venv` -> nút biến mất -> không ai
        # bấm -> bản `.exe` mãi mãi thiếu torch.
        thieu = list(tt.get("thieu") or [])
        ngoai = list(tt.get("ngoai_lib") or [])
        nguon = dict(tt.get("nguon") or {})
        du_lib = bool(tt.get("du_lib", tt["co"] and not thieu))
        self.b_tai.setText(TG.nhan_nut_tai(tt))
        # Đang lấy TỪ ĐÂU — hiện luôn, đừng bắt người dùng đoán.
        chi_tiet = ("\nNguồn từng gói: "
                    + " · ".join(f"{g}: {nguon.get(g) or 'KHÔNG CÓ'}"
                                 for g in TG.GOI_TACH_GIONG)
                    + f"\nThư mục _lib: {tt.get('lib', '')}") if nguon else ""
        if du_lib:
            # `thiet_bi` = '' nghĩa là CHƯA BIẾT (hộp này chạy trong tiến
            # trình đã nạp Qt nên KHÔNG được import torch để hỏi — xem
            # `thay_giong.thiet_bi_tach`). Chưa biết thì ĐỪNG ĐOÁN: ghi "CPU"
            # bừa là máy có card vẫn đọc thành "chạy trên CPU".
            _tb = {"cuda": " (chạy trên card đồ hoạ)",
                   "cpu": " (chạy trên CPU)"}.get(tt["thiet_bi"], "")
            self.lb_demucs.setText(
                f"Bộ tách giọng: ĐÃ CÓ ĐỦ trong _lib{_tb}." + chi_tiet)
            self.lb_demucs.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai.setVisible(False)
        elif tt["co"]:
            # CÀI DỞ: máy này chạy được vì đang MƯỢN gói của môi trường hệ
            # thống, nhưng `_lib` thiếu -> bản .exe trên máy nhân viên sẽ báo
            # "chưa có bộ tách giọng". Phải nói THẲNG, đây đúng là ca đã lừa
            # anh Hùng một lần (app báo "đã cài" trong khi thiếu torch).
            self.lb_demucs.setText(
                "Bộ tách giọng CÀI DỞ: " + ", ".join(thieu)
                + " KHÔNG nằm trong _lib"
                + (" (đang mượn của môi trường hệ thống: "
                   + ", ".join(ngoai) + ")" if ngoai else "")
                + ".\nMáy NÀY vẫn chạy được, nhưng bản .exe trên máy nhân viên "
                  "sẽ báo THIẾU vì ở đó không có gì để mượn. Bấm '"
                + TG.NHAN_CAI_TIEP + "' để lấy nốt." + chi_tiet)
            self.lb_demucs.setStyleSheet(f"color:{WARN}; font-size:11px;")
            self.b_tai.setVisible(True)
            self.b_tai.setEnabled(bool(tt["cai_duoc"]) and not self._dang_cai)
        else:
            self.lb_demucs.setText(
                "Máy này CHƯA có bộ tách giọng (thiếu: "
                + ", ".join(tt["thieu"]) + ") nên KHÔNG chạy được tính năng "
                "này. Bấm nút bên phải để tải về (chỉ tải 1 lần).\n"
                "Không có nó thì giọng cũ vẫn còn nguyên chồng lên giọng mới "
                "— đã đo: sót 86-100% lời gốc. Vì vậy app CHẶN, không làm bừa."
                + ("" if tt["cai_duoc"] else
                   "\nMáy này không có Python/pip nên app không tự tải được: "
                   "cài Python 3 rồi bấm lại, hoặc copy thư mục _lib từ máy "
                   "đã cài sang.") + chi_tiet)
            self.lb_demucs.setStyleSheet(f"color:{WARN}; font-size:11px;")
            self.b_tai.setVisible(True)
            self.b_tai.setEnabled(bool(tt["cai_duoc"]) and not self._dang_cai)
        self._cap_nhat_nut_chay()
        return tt

    def _cap_nhat_nut_chay(self) -> None:
        co = bool(getattr(self, "_tt_demucs", {}).get("co"))
        co_tm = bool(self._video_trong_thu_muc())
        self.b_chay.setEnabled(co and co_tm and not self._dang_cai)
        self.b_lam_lai.setEnabled(co and co_tm and not self._dang_cai)
        if not co:
            self.b_chay.setToolTip(
                "Chưa có bộ tách giọng — bấm '" + TG.NHAN_TAI_DEMUCS
                + "' trước. App KHÔNG chạy cách nhẹ vì nó để lọt 86-100% "
                  "lời gốc (video ra nghe cả giọng cũ lẫn giọng mới).")
        elif not co_tm:
            self.b_chay.setToolTip("Chưa chọn thư mục có video.")
        else:
            self.b_chay.setToolTip(
                "Chỉ chạy những video CHƯA xong. Video đã xong thì bỏ qua "
                "(chuột phải vào dòng để làm lại).")

    def _tai_demucs(self) -> None:
        """NGƯỜI DÙNG BẤM thì mới tải. Chạy ở thread nền, báo qua tín hiệu."""
        if self._dang_cai:
            return
        if QMessageBox.question(
                self, "Tải bộ tách giọng",
                "Sẽ tải khoảng 2 GB về thư mục:\n" + self._tt_demucs["lib"]
                + "\n\nChỉ tải 1 lần. Trong lúc tải vẫn dùng app bình thường "
                  "được. Tải bây giờ?") != QMessageBox.StandardButton.Yes:
            return
        self._dang_cai = True
        self.b_tai.setEnabled(False)
        self.pb_tai.setVisible(True)
        self.pb_tai.setValue(1)
        self._cap_nhat_nut_chay()
        buoc = {"p": 0.0, "m": "Đang tải..."}
        self._buoc_cai = buoc

        def bg():
            r = TG.cai_demucs(
                on_progress=lambda p, m: buoc.update({"p": p, "m": m}))
            self._cai_xong.emit(bool(r.get("ok")),
                                str(r.get("loi") or "")[:400])

        threading.Thread(target=bg, daemon=True).start()

    def _cai_demucs_xong(self, ok: bool, loi: str) -> None:
        self._dang_cai = False
        self.pb_tai.setVisible(False)
        tt = self._do_demucs()
        # Mừng theo `du_lib` chứ KHÔNG theo `co`: `co` True nhờ MƯỢN gói của
        # `.venv` thì `_lib` vẫn rỗng torch, và hộp "Đã cài xong" lúc đó đúng
        # là câu đã lừa anh Hùng lần trước.
        if ok and tt.get("du_lib", tt["co"]):
            QMessageBox.information(
                self, "Xong",
                "Đã cài xong bộ tách giọng vào _lib.\n" + str(tt.get("lib", "")))
        else:
            QMessageBox.warning(
                self, "Chưa cài được",
                "Chưa cài được bộ tách giọng.\n\n" + (loi or "")
                + "\n\nApp vẫn CHẶN tính năng này — không chạy cách nhẹ vì "
                  "nó cho ra video còn nguyên giọng cũ.")

    # ------------------------------------------------------------------
    # GIỌNG PIPER — LỰA CHỌN THỨ HAI (không chặn gì)
    # ------------------------------------------------------------------
    def _do_piper(self) -> dict:
        """Dò Piper rồi cập nhật nhãn. KHÔNG khoá nút Chạy.

        Thiếu Piper thì `dubbing._synth_all_words` tự LÙI về edge-tts, video
        vẫn ra đúng — chỉ khác giọng. Vì vậy đây là thông tin, không phải
        chốt chặn (khác hẳn Demucs ở hàng trên).
        """
        from app.core import piper_tts as PT
        tt = PT.tinh_trang_piper()
        self._tt_piper = tt
        if tt["co"]:
            self.lb_piper.setText(
                "Giọng Việt chạy trên máy (Piper): ĐÃ CÓ. "
                "Chọn trong ô Giọng đọc để dùng.")
            self.lb_piper.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai_piper.setVisible(False)
        else:
            self.lb_piper.setText(
                "Giọng Việt chạy trên máy (Piper): CHƯA TẢI (212 MB) — chọn "
                "giọng này thì app vẫn chạy nhưng sẽ đọc bằng giọng thường "
                "(edge-tts).")
            self.lb_piper.setStyleSheet("color:#B0B0B0; font-size:11px;")
            self.b_tai_piper.setVisible(True)
        return tt

    def _tai_piper(self) -> None:
        """NGƯỜI DÙNG BẤM thì mới tải — app không tự tải sau lưng.

        Tải THẲNG từ kho GitHub của tác giả: người tải là NGƯỜI DÙNG, app chỉ
        chỉ đường. Tự dựng máy chủ chứa bản sao Piper là app trở thành NGƯỜI
        PHÁT HÀNH và nghĩa vụ GPL quay lại đủ.
        """
        from app.core import piper_tts as PT
        if getattr(self, "_dang_cai_piper", False):
            return
        if QMessageBox.question(
                self, "Tải giọng chạy trên máy",
                "Sẽ tải bộ đọc Piper + giọng vais1000 về:\n"
                + str(self._tt_piper.get("thu_muc", ""))
                + "\n\nBộ đọc Piper theo giấy phép GPL-3.0, tải thẳng từ kho "
                  "của tác giả. Giọng vais1000 dùng thương mại được (xem "
                  "LICENSES.txt).\n\nTải bây giờ?"
                ) != QMessageBox.StandardButton.Yes:
            return
        self._dang_cai_piper = True
        self.b_tai_piper.setEnabled(False)
        self.b_tai_piper.setText("Đang tải...")

        def bg():
            r = PT.cai_piper()
            self._piper_xong.emit(bool(r.get("ok")),
                                  str(r.get("loi") or "")[:400])

        threading.Thread(target=bg, daemon=True).start()

    def _tai_piper_xong(self, ok: bool, loi: str) -> None:
        self._dang_cai_piper = False
        self.b_tai_piper.setEnabled(True)
        tt = self._do_piper()
        if ok and tt["co"]:
            QMessageBox.information(
                self, "Xong",
                "Đã tải xong giọng chạy trên máy.\n" + str(tt.get("thu_muc", ""))
                + "\n\nChọn lại trong ô Giọng đọc để dùng.")
        else:
            QMessageBox.warning(
                self, "Chưa tải được",
                "Chưa tải được giọng chạy trên máy.\n\n" + (loi or "")
                + "\n\nApp vẫn dùng được bình thường bằng giọng thường "
                  "(edge-tts).")

    # ------------------------------------------------------------------
    # DANH SÁCH GIỌNG (tái dùng của hộp Cài đặt Reup)
    # ------------------------------------------------------------------
    def _nap_giong_nen(self) -> None:
        """Nạp ở THREAD NỀN: `list_recap_voices` có thể gọi mạng (edge-tts).

        Gọi thẳng trong `__init__` là hộp treo vài giây trên máy mạng chậm —
        và làm treo cả cổng test dựng UI.
        """
        if _CACHE_GIONG:
            self._giong_tho = list(_CACHE_GIONG)
            self._dung_combo_giong()
            return
        # DỰNG COMBO NGAY với những gì đang có (rỗng) để GIỌNG ĐÃ LƯU hiện ra
        # tức thì. Không có bước này thì mở hộp -> lưu (chưa kịp tải xong) là
        # ghi đè giọng user đã chọn bằng "" — đúng loại lỗi "chọn X ra Y".
        self._dung_combo_giong()
        ra: list = []
        self._ra_giong = ra

        def bg():
            try:
                from app.core.dubbing import list_recap_voices
                ra.append(list_recap_voices())
            except Exception:  # noqa: BLE001 - offline -> combo tối thiểu
                ra.append([])
            self._giong_xong.emit()

        threading.Thread(target=bg, daemon=True).start()

    def _dung_combo_giong(self) -> None:
        ra = getattr(self, "_ra_giong", None)
        if ra:
            self._giong_tho = list(ra[0] or [])
            if self._giong_tho:
                _CACHE_GIONG[:] = self._giong_tho
        muon = str(self._s.value(K_GIONG, "") or "")
        self.cb_giong.blockSignals(True)
        self.cb_giong.clear()
        self.cb_giong.addItem(NHAN_GIONG_TU, "")
        for nhan, vid in giong_dung_duoc(self._giong_tho):
            self.cb_giong.addItem(nhan, vid)
            if not vid:                     # nhãn NHÓM ngôn ngữ -> không chọn
                it = self.cb_giong.model().item(self.cb_giong.count() - 1)
                if it is not None:
                    it.setEnabled(False)
        if muon:
            i = self.cb_giong.findData(muon)
            if i < 0:                       # giọng đã lưu nhưng list chưa có
                self.cb_giong.addItem(muon, muon)
                i = self.cb_giong.count() - 1
            self.cb_giong.setCurrentIndex(i)
        self.cb_giong.blockSignals(False)

    def _doi_ngon_ngu(self) -> None:
        self._cap_nhat_nut_chay()

    # ------------------------------------------------------------------
    # THƯ MỤC VÀO / RA
    # ------------------------------------------------------------------
    def _chon_thu_muc(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục video cần thay giọng",
            self.ed_thu_muc.text().strip())
        if d:
            self.ed_thu_muc.setText(d)

    def _chon_thu_muc_ra(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục ĐÍCH (nơi ghi video đã thay giọng)",
            self.ed_thu_muc_ra.text().strip()
            or self.ed_thu_muc.text().strip())
        if d:
            self.ed_thu_muc_ra.setText(d)

    def thu_muc_dich(self) -> str:
        """Thư mục đích THẬT SỰ dùng: ô trống thì lấy mặc định.

        Một nguồn sự thật cho cả nhãn, cảnh báo trùng và lúc xếp job — ba chỗ
        tự đoán riêng là hiện một đằng ghi một nẻo.
        """
        ra = self.ed_thu_muc_ra.text().strip()
        if ra:
            return ra
        tm = self.ed_thu_muc.text().strip()
        return tg_so.thu_muc_dich_mac_dinh(tm) if tm else ""

    def trung_thu_muc(self) -> bool:
        """Nguồn và đích có TRÙNG nhau không (ghi đè = mất video gốc)."""
        tm = self.ed_thu_muc.text().strip()
        ra = self.thu_muc_dich()
        return bool(tm and ra and tg_so.trung_thu_muc(tm, ra))

    def _doi_thu_muc_ra(self) -> None:
        self._cap_nhat_nhan_dich()

    def _cap_nhat_nhan_dich(self) -> None:
        ra = self.thu_muc_dich()
        if not ra:
            self.lb_dich.setText("")
            return
        if self.trung_thu_muc():
            self.lb_dich.setText(
                "CẢNH BÁO: Thư mục đích ĐANG TRÙNG thư mục nguồn — làm vậy là "
                "GHI ĐÈ LÊN VIDEO GỐC. Hãy chọn thư mục đích khác (hoặc để "
                "trống để app tự dùng " + tg_so.thu_muc_dich_mac_dinh(
                    self.ed_thu_muc.text().strip()) + ").")
            self.lb_dich.setStyleSheet(
                f"color:{DANGER}; font-size:11px; font-weight:600;")
        else:
            self.lb_dich.setText("Video mới sẽ nằm ở: " + ra
                                 + " · video gốc GIỮ NGUYÊN.")
            self.lb_dich.setStyleSheet(f"color:{MUTED}; font-size:11px;")

    def _video_trong_thu_muc(self) -> list:
        tm = self.ed_thu_muc.text().strip()
        if not tm or not os.path.isdir(tm):
            return []
        return TG.liet_ke_video(tm)

    def _doi_thu_muc(self) -> None:
        """Dựng lại bảng theo thư mục + SỔ TRẠNG THÁI đã lưu trên đĩa."""
        vids = self._video_trong_thu_muc()
        self._jobs.clear()
        self._xong_id.clear()
        self.bang.setRowCount(len(vids))
        for r, v in enumerate(vids):
            it = QTableWidgetItem(v.name)
            it.setData(Qt.ItemDataRole.UserRole, str(v))
            it.setToolTip(str(v))
            self.bang.setItem(r, 0, it)
            self._ve_theo_so(r, str(v))
        self._nhan_lai_job_dang_chay()
        self._cap_nhat_nhan_dich()
        self._cap_nhat_nut_chay()
        self._dem_lai()
        self._nhip()

    def _nhan_lai_job_dang_chay(self) -> int:
        """NHẬN LẠI job thay giọng đang chạy/đang chờ của đúng video trong bảng.

        Đóng hộp rồi mở lại (hoặc tắt app giữa chừng rồi mở lên) thì việc VẪN
        CHẠY ở nền — không nhận lại thì bảng hiện "Chưa chạy" trong khi máy
        đang làm, đúng cái anh Hùng kêu *"không hiện gì cả"*. Sự thật nằm ở
        bảng `jobs` chứ không ở hộp, nên dựng lại được (bài học "sổ chỉ ở RAM,
        phải hồi phục").
        """
        try:
            rows = db.query(
                "SELECT id, payload FROM jobs WHERE type='thay_giong' "
                "AND status IN ('pending','running')")
        except Exception:  # noqa: BLE001 - DB vỡ thì đừng làm sập hộp
            return 0
        theo_duong: dict[str, int] = {}
        for r in rows:
            try:
                p = json.loads(r["payload"] or "{}")
            except (ValueError, TypeError):
                continue
            v = str(p.get("video") or "")
            if v:
                theo_duong[os.path.normcase(os.path.abspath(v))] = int(r["id"])
        n = 0
        for r in range(self.bang.rowCount()):
            d = self._duong_dong(r)
            if not d:
                continue
            jid = theo_duong.get(os.path.normcase(os.path.abspath(d)))
            if not jid:
                continue
            self._jobs[d] = jid
            self._dat_o(r, 1, "Đang chờ", MUTED)
            self._dat_o(r, 2, f"0% · bước 0/{len(tg_so.TEN_BUOC)}")
            self._dat_o(r, 3, "Việc này đang chạy ở nền (nhận lại từ hàng đợi)")
            n += 1
        if n:
            self._da_bao_xong = False   # còn việc chạy -> xong phải BÁO
        return n

    def _ve_theo_so(self, r: int, duong: str) -> None:
        """Vẽ 3 cột còn lại của một dòng theo SỔ (chưa chạy lượt nào)."""
        m = tg_so.tra(duong)
        tt = m.get("trang_thai") or ""
        if tt == tg_so.XONG:
            self._dat_o(r, 1, CHU_DA_XONG, SUCCESS)
            self._dat_o(r, 2, "100%")
            self._dat_o(r, 3, "Đã làm xong lần trước — bấm Chạy sẽ bỏ qua. "
                              "Chuột phải để làm lại.")
        elif tt == tg_so.LOI:
            self._dat_o(r, 1, "Lỗi", DANGER)
            self._dat_o(r, 2, "-")
            self._dat_o(r, 3, tg_so.loi_doc_hieu(str(m.get("loi") or ""))
                        + " (bấm Chạy sẽ tự làm lại)")
        elif tt == tg_so.BO_QUA:
            self._dat_o(r, 1, "Bỏ qua", MUTED)
            self._dat_o(r, 2, "-")
            self._dat_o(r, 3, "Bạn đã chọn bỏ qua video này. Chuột phải để "
                              "làm lại.")
        else:
            self._dat_o(r, 1, "Chưa chạy", MUTED)
            self._dat_o(r, 2, "-")
            self._dat_o(r, 3, "")

    def _duong_dong(self, r: int) -> str:
        it = self.bang.item(r, 0)
        if it is None:
            return ""
        return str(it.data(Qt.ItemDataRole.UserRole) or "")

    def _dong_theo_duong(self, duong: str) -> int:
        for r in range(self.bang.rowCount()):
            if self._duong_dong(r) == duong:
                return r
        return -1

    def _dem_lai(self) -> None:
        """Nhãn dưới cùng khi KHÔNG chạy lượt nào: đếm theo sổ."""
        if self._jobs:
            return
        vids = [self._duong_dong(r) for r in range(self.bang.rowCount())]
        t = tg_so.tom_tat(vids)
        self.lb_tt.setStyleSheet(f"color:{MUTED};")
        self.lb_tt.setText(
            f"{len(vids)} video trong thư mục · đã xong {t['xong']} · "
            f"lỗi {t['loi']} · bỏ qua {t['bo_qua']} · chưa chạy {t['chua']}")

    # ------------------------------------------------------------------
    # CHẠY
    # ------------------------------------------------------------------
    def luu_cai_dat(self) -> None:
        """Ghi mọi lựa chọn vào QSettings — mở lại hộp là thấy y nguyên."""
        self._s.setValue(K_THUMUC, self.ed_thu_muc.text().strip())
        self._s.setValue(K_THUMUC_RA, self.ed_thu_muc_ra.text().strip())
        self._s.setValue(K_NGON_NGU, self.cb_nn.currentData() or "en")
        self._s.setValue(K_GIONG, self.cb_giong.currentData() or "")
        self._s.setValue(K_LUONG, int(self.sp_luong.value()))
        self._s.setValue(K_CHE_CHU, "1" if self.ck_che.isChecked() else "0")
        self._s.setValue(K_CHE_CACH, self.cb_che_cach.currentData() or "mo")
        self._s.setValue(K_CHE_MUC, float(self.sp_che_muc.value()))
        self._s.setValue(K_VIET_CHU, "1" if self.ck_viet.isChecked() else "0")

    def _doi_che_chu(self, bat: bool) -> None:
        """Bật/tắt 2 ô con theo ô chính — tắt mà vẫn chỉnh được là gây hiểu
        nhầm 'đã bật' (đúng cái đã làm anh Hùng tưởng che chữ đang chạy)."""
        self.cb_che_cach.setEnabled(bool(bat))
        self.sp_che_muc.setEnabled(bool(bat))
        # Viết chữ dịch CHỈ có nghĩa khi đang che: viết đè lên chữ cũ mà không
        # che là HAI LỚP CHỮ chồng nhau, tệ hơn hẳn để nguyên.
        self.ck_viet.setEnabled(bool(bat))

    def _chay(self, lam_lai: list | None = None) -> int:
        """Xếp job cho video CHƯA XONG. Trả SỐ JOB đã xếp.

        `lam_lai` = danh sách đường dẫn phải chạy BẤT KỂ sổ nói gì (chuột phải
        -> Làm lại). Trả số job để cổng test đếm được thẳng, không phải đoán
        qua DB.
        """
        ep = {str(x) for x in (lam_lai or [])}
        tt = self._do_demucs()
        if not tt["co"]:
            QMessageBox.warning(
                self, "Chưa có bộ tách giọng",
                TG.THIEU_DEMUCS + "\n\nBấm '" + TG.NHAN_TAI_DEMUCS + "'.")
            return 0
        vids = self._video_trong_thu_muc()
        if not vids:
            QMessageBox.information(self, "Chưa có video",
                                    "Thư mục này không có video nào.")
            return 0
        # CHỐT: nguồn trùng đích -> KHÔNG xếp job nào. Ghi đè = mất video gốc.
        if self.trung_thu_muc():
            self._cap_nhat_nhan_dich()
            QMessageBox.warning(
                self, "Thư mục đích trùng thư mục nguồn",
                "Thư mục đích đang TRÙNG thư mục nguồn.\n\nLàm vậy là GHI ĐÈ "
                "LÊN VIDEO GỐC (mất bản gốc vĩnh viễn), nên app KHÔNG chạy.\n"
                "Hãy chọn thư mục đích khác, hoặc để trống ô đó để app tự "
                "dùng:\n" + tg_so.thu_muc_dich_mac_dinh(
                    self.ed_thu_muc.text().strip()))
            return 0
        self.luu_cai_dat()
        if self._pool is not None:
            self._pool.set_limits(max_tg=int(self.sp_luong.value()))
        ra = self.thu_muc_dich()
        try:
            os.makedirs(ra, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Không tạo được thư mục đích",
                                f"{ra}\n\n{e}")
            return 0
        nn = str(self.cb_nn.currentData() or "en")
        giong = str(self.cb_giong.currentData() or "")
        cc = bool(self.ck_che.isChecked())
        cc_cach = str(self.cb_che_cach.currentData() or "mo")
        cc_muc = float(self.sp_che_muc.value())
        cc_viet = bool(self.ck_viet.isChecked())

        self._jobs.clear()
        self._xong_id.clear()
        self._da_bao_xong = False
        self._bo_qua_luot = 0
        loi_xep: list[str] = []
        for r in range(self.bang.rowCount()):
            duong = self._duong_dong(r)
            if not duong:
                continue
            buoc_lai = duong in ep
            # BỎ QUA video đã xong — CHỐT CHÍNH của việc 3. Gỡ nó ra là mỗi
            # lần bấm Chạy lại làm lại từ đầu cả 300 video.
            if not buoc_lai and not tg_chay.can_chay(duong):
                self._bo_qua_luot += 1
                self._ve_theo_so(r, duong)
                continue
            try:
                jid = tg_chay.xep_mot(
                    self._pool, duong, nn, voice=giong, thu_muc_ra=ra,
                    kenh=Path(duong).parent.name, lam_lai=buoc_lai,
                    che_chu=cc, che_chu_cach=cc_cach, che_chu_muc=cc_muc,
                    viet_chu=cc_viet)
            except (ValueError, OSError) as e:   # noqa: PERF203
                loi_xep.append(f"{Path(duong).name}: {e}")
                self._dat_o(r, 1, "Lỗi", DANGER)
                self._dat_o(r, 3, tg_so.loi_doc_hieu(str(e)))
                continue
            if jid:
                self._jobs[duong] = int(jid)
                self._dat_o(r, 1, "Đang chờ", MUTED)
                self._dat_o(r, 2, f"0% · bước 0/{len(tg_so.TEN_BUOC)}")
                self._dat_o(r, 3, "Đã xếp hàng, chờ tới lượt")
                self.doi_trang_thai.emit(duong, "Đang chờ", 0.0)
            else:
                # không có bộ điều phối (hộp mở rời) -> nói thẳng, đừng im
                self._dat_o(r, 1, "Chưa chạy được", WARN)
                self._dat_o(r, 3, "Không nối được bộ điều phối việc — mở lại "
                                  "app rồi thử lại")
        if loi_xep:
            QMessageBox.warning(self, "Có video không xếp được",
                                "\n".join(loi_xep[:8]))
        if not self._jobs:
            self._da_bao_xong = True     # không có việc nào -> không báo xong
            self.lb_tt.setStyleSheet(f"color:{SUCCESS};")
            self.lb_tt.setText(
                f"Không có video nào cần chạy — {self._bo_qua_luot} video đã "
                f"xong nên bỏ qua. Muốn làm lại: chuột phải vào dòng hoặc bấm "
                f"'Làm lại tất cả'.")
        self._nhip()
        return len(self._jobs)

    def _lam_lai_tat_ca(self) -> int:
        """Quên sổ của MỌI video ĐANG HIỆN rồi chạy lại từ đầu."""
        vids = [self._duong_dong(r) for r in range(self.bang.rowCount())]
        vids = [v for v in vids if v]
        if not vids:
            return 0
        if QMessageBox.question(
                self, "Làm lại tất cả",
                f"Chạy lại TỪ ĐẦU {len(vids)} video đang hiện trong bảng?\n\n"
                "Video gốc vẫn KHÔNG bị đụng tới; bản cũ trong thư mục đích "
                "sẽ bị ghi đè.") != QMessageBox.StandardButton.Yes:
            return 0
        tg_so.xoa_nhieu(vids)
        return self._chay(lam_lai=vids)

    def _menu_dong(self, pos) -> None:
        """Chuột phải vào dòng: Làm lại video này · Làm lại tất cả · Bỏ qua."""
        r = self.bang.rowAt(pos.y())
        duong = self._duong_dong(r) if r >= 0 else ""
        m = QMenu(self)
        a1 = QAction("Làm lại video này", self)
        a1.setEnabled(bool(duong))
        a1.triggered.connect(lambda: self._lam_lai_mot(duong))
        m.addAction(a1)
        a2 = QAction("Làm lại tất cả", self)
        a2.triggered.connect(self._lam_lai_tat_ca)
        m.addAction(a2)
        m.addSeparator()
        a3 = QAction("Bỏ qua video này", self)
        a3.setEnabled(bool(duong))
        a3.triggered.connect(lambda: self._bo_qua_mot(duong))
        m.addAction(a3)
        m.exec(self.bang.viewport().mapToGlobal(pos))

    def _lam_lai_mot(self, duong: str) -> int:
        """Chạy lại ĐÚNG MỘT video (bỏ qua sổ). Trả số job đã xếp."""
        if not duong:
            return 0
        tg_so.xoa(duong)
        r = self._dong_theo_duong(duong)
        if r >= 0:
            self._ve_theo_so(r, duong)
        return self._chay(lam_lai=[duong])

    def _bo_qua_mot(self, duong: str) -> None:
        """Đánh dấu BỎ QUA — lượt Chạy sau không đụng tới video này nữa."""
        if not duong:
            return
        tg_so.ghi(duong, tg_so.BO_QUA)
        r = self._dong_theo_duong(duong)
        if r >= 0:
            self._ve_theo_so(r, duong)
        self._jobs.pop(duong, None)
        self._dem_lai()

    def _dung(self) -> None:
        if self._pool is None or not self._jobs:
            return
        for jid in list(self._jobs.values()):
            try:
                self._pool.cancel(int(jid))
            except Exception:  # noqa: BLE001
                pass
        self._nhip()

    # ------------------------------------------------------------------
    # NHỊP CẬP NHẬT BẢNG (đọc thẳng bảng `jobs`, không giữ sổ RAM riêng)
    # ------------------------------------------------------------------
    _KET_THUC = ("done", "failed", "canceled")
    _CHU = {"pending": "Đang chờ", "done": "Xong", "failed": "Lỗi",
            "canceled": "Đã dừng"}
    _MAU = {"done": SUCCESS, "failed": DANGER, "canceled": MUTED,
            "running": WARN, "pending": MUTED}

    def _nhip(self) -> None:
        if self._dang_cai:
            b = getattr(self, "_buoc_cai", {"p": 0.0, "m": ""})
            self.pb_tai.setValue(int(max(1, min(100, b["p"] * 100))))
            self.lb_tt.setText(str(b["m"])[:150])
            return
        if not self._jobs:
            return
        # CHỈ HỎI DB những job CHƯA kết thúc — thư mục 300 video là 300 id,
        # hỏi lại cả đống mỗi 0,7 giây là tự làm đơ máy đang chạy sản xuất.
        con = [j for j in self._jobs.values() if j not in self._xong_id]
        theo_id: dict = dict(self._xong_id)
        if con:
            cho = ",".join("?" * len(con))
            try:
                rows = db.query(
                    f"SELECT id, status, progress, message, error FROM jobs "
                    f"WHERE id IN ({cho})", tuple(con))
            except Exception:  # noqa: BLE001 - DB vỡ thì đừng làm sập hộp
                return
            for r in rows:
                d = {"status": str(r["status"] or ""),
                     "progress": float(r["progress"] or 0),
                     "message": str(r["message"] or ""),
                     "error": str(r["error"] or "")}
                theo_id[int(r["id"])] = d
                if d["status"] in self._KET_THUC:
                    self._xong_id[int(r["id"])] = d
                    dv = self._duong_theo_job(int(r["id"]))
                    if d["status"] == "failed" and dv:
                        # ghi sổ ở đây nữa: lỗi NÉM TRƯỚC khi vào handler (vd
                        # thiếu Demucs) thì handler không kịp ghi.
                        tg_so.ghi(dv, tg_so.LOI,
                                  loi=(d["error"] or d["message"])[:300])

        xong = loi = huy = chay = 0
        for r in range(self.bang.rowCount()):
            duong = self._duong_dong(r)
            jid = self._jobs.get(duong)
            row = theo_id.get(int(jid)) if jid else None
            if row is None:
                continue
            tt = row["status"]
            p = row["progress"]
            if tt == "running":
                nhan, b, tong = tg_so.buoc_tu_tien_trinh(p, row["message"])
                self._dat_o(r, 1, nhan, WARN)
                self._dat_o(r, 2, f"{p * 100:.0f}% · bước {b}/{tong}")
                self._dat_o(r, 3, row["message"][:200])
            else:
                self._dat_o(r, 1, self._CHU.get(tt, tt), self._MAU.get(tt))
                if tt == "done":
                    self._dat_o(r, 2, "100%")
                    self._dat_o(r, 3, "Xong — video mới ở thư mục đích "
                                      "(gốc giữ nguyên)")
                elif tt == "failed":
                    self._dat_o(r, 2, f"{p * 100:.0f}%")
                    self._dat_o(r, 3, tg_so.loi_doc_hieu(
                        row["error"] or row["message"])
                        + " · bấm Chạy để làm lại")
                elif tt == "canceled":
                    self._dat_o(r, 2, f"{p * 100:.0f}%")
                    self._dat_o(r, 3, "Bạn đã dừng — bấm Chạy để làm lại "
                                      "(video gốc không bị đụng)")
                else:
                    self._dat_o(r, 2, f"{p * 100:.0f}% · bước 0/{len(tg_so.TEN_BUOC)}")
                    self._dat_o(r, 3, "Đã xếp hàng, chờ tới lượt")
            moi = self.bang.item(r, 1).text() if self.bang.item(r, 1) else ""
            if moi != self._tt_dong.get(duong):
                self._tt_dong[duong] = moi
                self.doi_trang_thai.emit(duong, moi, p)
            xong += tt == "done"
            loi += tt == "failed"
            huy += tt == "canceled"
            chay += tt in ("running", "pending")

        if chay:
            self.lb_tt.setStyleSheet(f"color:{MUTED};")
            self.lb_tt.setText(
                f"Đang chạy: còn {chay} video · xong {xong} · lỗi {loi}"
                + (f" · dừng {huy}" if huy else "")
                + (f" · bỏ qua {self._bo_qua_luot}"
                   if self._bo_qua_luot else ""))
        elif not self._da_bao_xong:
            self._da_bao_xong = True
            self._bao_xong(xong, loi, huy)

    def _duong_theo_job(self, jid: int) -> str:
        for d, j in self._jobs.items():
            if int(j) == int(jid):
                return d
        return ""

    def _bao_xong(self, xong: int, loi: int, huy: int) -> None:
        """DÒNG TỔNG KẾT + hộp báo — anh Hùng: "xong hay gì cũng không báo"."""
        chu = (f"XONG CẢ LƯỢT: {xong} video xong · {loi} lỗi"
               + (f" · {huy} bị dừng" if huy else "")
               + (f" · {self._bo_qua_luot} bỏ qua (đã xong từ trước)"
                  if self._bo_qua_luot else ""))
        self.lb_tt.setStyleSheet(
            f"color:{DANGER if loi else SUCCESS}; font-weight:600;")
        self.lb_tt.setText(chu)
        self.xong_ca_luot.emit(xong, loi, huy, self._bo_qua_luot)
        them = ""
        if loi:
            them = ("\n\nVideo LỖI sẽ TỰ CHẠY LẠI ở lần bấm Chạy sau. Cột "
                    "'Ghi chú' ghi rõ lý do từng video.")
        QMessageBox.information(
            self, "Thay giọng nói: xong cả lượt",
            chu + "\n\nVideo mới nằm ở: " + self.thu_muc_dich()
            + "\nVideo gốc GIỮ NGUYÊN, app không xoá gì cả." + them)

    def _dat_o(self, r: int, c: int, chu: str, mau: str = "") -> None:
        it = self.bang.item(r, c)
        if it is None:
            it = QTableWidgetItem()
            self.bang.setItem(r, c, it)
        if it.text() != chu:
            it.setText(chu)
        if mau:
            it.setForeground(QColor(mau))

    # ------------------------------------------------------------------
    def closeEvent(self, e):  # noqa: N802 - Qt
        self.luu_cai_dat()
        try:
            self._timer.stop()
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(e)

    def reject(self):  # noqa: D102 - Qt
        self.luu_cai_dat()
        try:
            self._timer.stop()
        except Exception:  # noqa: BLE001
            pass
        super().reject()


def mo_hop_thay_giong(parent, pool, thung_rac: str = "") -> ThayGiongDialog:
    """Mở hộp Thay giọng nói. Trả hộp để cổng test soi được widget bên trong."""
    dlg = ThayGiongDialog(pool, parent, thung_rac=thung_rac)
    dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
    dlg.exec()
    return dlg
