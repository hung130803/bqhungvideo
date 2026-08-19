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
   `Tải bộ tách giọng (tải khoảng 155 MB)` và **KHOÁ nút Chạy**. TUYỆT ĐỐI không
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
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core import che_chu as TG_CC
from app.core import giong_hang as GH
from app.core import tg_chay, tg_so
from app.core import thay_giong as TG
from app.core.captions import CAPTION_PRESETS
from app.database import db
from app.ui.appsettings import app_settings
from app.core import giong_bang as GB
from app.core import nhan_nha as NN
from app.ui.editor import nut_chon_mau
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
#: CÁCH KHỚP TIẾNG VỚI HÌNH — "" = ép giọng (y như mọi bản trước) · "hinh" =
#: chỉnh video theo giọng.
K_KHOP_CACH = "tg_khop_cach"
#: KIỂU CHỮ của dòng chữ mới (chỉ dùng khi đang che + viết chữ).
K_KC_PRESET = "tg_kc_preset"
K_KC_FONT = "tg_kc_font"
K_KC_CO = "tg_kc_co"
K_KC_DAM = "tg_kc_dam"
K_KC_NGHIENG = "tg_kc_nghieng"
K_KC_MAU = "tg_kc_mau"
K_KC_VIEN = "tg_kc_vien"
K_KC_DOVIEN = "tg_kc_dovien"
K_KC_VITRI = "tg_kc_vitri"

#: Nhãn mục ĐẦU của các ô kiểu chữ. Phải NÓI RA mặc định thật (bài học cổng 16
#: v2.6.25a) — ghi trơn "(tự)" thì user tưởng ô chưa được đặt.
NHAN_CO_TU = "Theo chữ cũ trong hình"
NHAN_PHONG_TU = "Theo mặc định"
NHAN_KIEU_TU = "Kiểu mặc định (trắng viền đen)"
NHAN_VITRI_TU = "Đúng chỗ chữ cũ"
NHAN_DAM_TU = "Theo kiểu chữ (đang ĐẬM)"
NHAN_NGHIENG_TU = "Theo kiểu chữ (KHÔNG nghiêng)"
NHAN_VIEN_TU = "Theo kiểu chữ"

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
    """Lọc danh sách giọng về ĐÚNG cái `thay_giong` đọc được.

    LỊCH SỬ, ĐỌC TRƯỚC KHI SỬA: tới v2.31.0 hàm này lọc bỏ CẢ `el:` LẪN
    `gemini:`, lý do ghi thẳng trong mã là *"`doc_ban_dich` gọi thẳng
    `dubbing._synth_all` — hàm này CHỈ biết edge-tts"*. Lý do đó ĐÚNG vào lúc
    ấy. v2.32.0 đã nối ElevenLabs vào **cửa chung** `_synth_all`/
    `_synth_all_words` (xem `dubbing._eleven_hay_khong`) nên `el:` chạy được
    thật -> BỎ lọc `el:`.

    **`gemini:` VẪN CHẶN, và đây là lý do bằng số chứ không phải quên:**
    Gemini TTS **KHÔNG trả word boundary** (`dubbing.py` ghi rõ ở nhánh
    `_synth_all_gemini`), mà đường thay tiếng DỰNG CHỮ THEO MỐC TỪNG TỪ (cổng
    60: "nói đến đâu chữ hiện đến đó"). Đưa `gemini:` vào là mất mốc -> chữ
    quay lại kiểu đổ cả cụm, đúng cái anh Hùng đã kêu. Ngoài ra
    `_synth_all_gemini` có thể TỰ ĐỔI CẢ TRACK sang edge-tts khi hết hạn mức
    mà không hỏi ai. Nối được `gemini:` thì phải giải hai chuyện đó trước.

    Nhãn nhóm (voice_id rỗng) giữ lại để combo còn phân nhóm ngôn ngữ.
    """
    ra: list = []
    for nhan, vid in ds or []:
        v = str(vid or "")
        if v.startswith("gemini:"):
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

    # ---- GIỌNG NGOÀI (OmniVoice) — MỘT GIỌNG ĐỌC ĐƯỢC 4 THỨ TIẾNG ----
    # **NHÃN PHẢI GHI THẲNG GIẤY PHÉP.** Trọng số OmniVoice là **CC-BY-NC =
    # CẤM DÙNG THƯƠNG MẠI** (nguyên văn model card gốc), kèm lớp thứ ba
    # Boson Higgs Audio 2 / Meta Llama 3. Anh Hùng BÁN app và dùng app kiếm
    # tiền; anh ấy đã được trình bày rõ và vẫn bảo "thêm hết vào cho tôi" —
    # đó là quyết định kinh doanh của anh ấy, nhưng nhãn vẫn phải nói ra để
    # anh ấy biết mình đang chọn gì, không phải nhớ. Cùng lý lẽ đã dùng cho
    # Piper (nói thẳng đánh đổi ngay trong nhãn, cổng 64) và cho edge-tts ở
    # `LICENSES.txt` mục 5.
    #
    # Nhãn còn ghi CHẤT LƯỢNG ĐO ĐƯỢC: tiếng Việt nó đọc sai 16,9% so với
    # edge-tts 6,8% (lượt 7), và mốc từng chữ phải dò lại bằng Groq nên kém
    # khớp hơn edge-tts. Đây đúng tiền lệ Piper: tệ hơn edge-tts thì GHI
    # CẢNH BÁO, đừng để người dùng tự phát hiện sau 300 video.
    #
    # `danh_sach_giong()` CHỈ trả giọng máy này chạy được — thiếu model thì
    # combo KHÔNG có dòng nào (khác Piper: Piper app tự tải được nên còn hiện
    # dòng "chưa tải"; OmniVoice 6,1 GB thì app không tự tải).
    try:
        from app.core import giong_ngoai
        cuoi_vi2 = max((i for i, (_n, v) in enumerate(mo_rong)
                        if str(v).startswith("vi-VN")
                        or str(v).startswith("piper:")), default=-1)
        for j, (ma_g, nhan_g) in enumerate(giong_ngoai.danh_sach_giong()):
            mo_rong.insert(cuoi_vi2 + 1 + j, (nhan_g, ma_g))
    except Exception:  # noqa: BLE001
        pass                                # thiếu module -> combo y hệt cũ

    # ---- GIỌNG VieNeu — 20 GIỌNG VIỆT DỰNG SẴN, CHẠY TRÊN MÁY ----
    # `app/core/giong_vieneu.py` xong từ `a95e0e6` nhưng **chưa ai gọi tới** —
    # y hệt ca `giong_bang`. Nối vào đây thì anh Hùng mới thấy chúng.
    #
    # ĐIỀU KIỆN TIÊN QUYẾT ĐÃ LÀM TRƯỚC, ĐỪNG ĐẢO THỨ TỰ: `dubbing._synth_all`
    # và `_synth_all_words` phải BIẾT `vn:`/`vnb:` trước đã (xem
    # `dubbing._vieneu_hay_khong`). Đưa mã giọng vào combo mà cửa đọc không
    # nhận thì chọn "Minh Đức" sẽ ra giọng khác — đúng bẫy "chọn X ra Y" mà
    # `ov:nu_am` đã sập một lần.
    #
    # `du_chua_tai=True`: hiện ĐỦ 20 giọng kể cả khi máy chưa tải model, nhãn
    # mang tiền tố "CHƯA TẢI (250 MB)". Theo tiền lệ Piper chứ không phải
    # OmniVoice — app TỰ TẢI được VieNeu (250 MB) nên giấu đi là người dùng
    # không bao giờ biết có thứ đó; OmniVoice 6,1 GB app không tự tải nên nó
    # mới phải giấu.
    try:
        from app.core import giong_vieneu
        cuoi_vi3 = max((i for i, (_n, v) in enumerate(mo_rong)
                        if str(v).startswith("vi-VN")
                        or str(v).startswith("piper:")
                        or str(v).startswith("ov:")
                        or str(v).startswith("ix:")), default=-1)
        # `ngan=True`: nhãn đầy đủ dài 364-521 ký tự (đo thật) nên trong combo
        # nó vừa không đọc được vừa che mất mọi dòng khác. Phần cảnh báo đầy
        # đủ đi vào TOOLTIP — xem `_dung_combo_giong`.
        for j, (ma_g, nhan_g) in enumerate(
                giong_vieneu.danh_sach_giong(du_chua_tai=True, ngan=True)):
            mo_rong.insert(cuoi_vi3 + 1 + j, (nhan_g, ma_g))
    except Exception:  # noqa: BLE001
        pass                                # thiếu module -> combo y hệt cũ

    # ---- GIỌNG Vbee — 3 GIỌNG VIỆT TRẢ TIỀN, HIỆN KỂ CẢ KHI CHƯA CÓ KEY ----
    # Ca thứ BA của cùng một bệnh sau `giong_bang` và `giong_chatter`:
    # `app/core/giong_vbee.py` dựng xong 948 dòng, `danh_sach_giong()` sẵn
    # sàng, mà **không một dòng nào trong combo gọi tới**. Đo trước khi vá:
    # combo có 0 mã `vbee:`.
    #
    # ĐIỀU KIỆN TIÊN QUYẾT ĐÃ LÀM TRƯỚC, ĐỪNG ĐẢO THỨ TỰ: `dubbing._synth_all`
    # và `_synth_all_words` phải BIẾT `vbee:` trước đã (xem
    # `dubbing._vbee_hay_khong`). Đưa mã vào combo mà cửa đọc không nhận thì
    # chọn "Ngọc Huyền (Vbee)" sẽ ra giọng khác — đúng bẫy "chọn X ra Y" mà
    # `ov:nu_am` và `vn:` đã sập hai lần.
    #
    # **HIỆN KỂ CẢ KHI CHƯA CÓ KEY** (`danh_sach_giong` luôn trả đủ 3): thứ
    # còn thiếu chỉ là một dòng key dán vào Cài đặt, giấu đi thì anh Hùng
    # không bao giờ biết có đường này để mua. Nhãn tự mang chữ
    # `cần key Vbee, xem vbee.vn`, và `giong_bang._DO_TRUNG[VBEE]` đã dò đúng
    # chữ đó nên `duoi_dong` KHÔNG dán thêm "TỐN TIỀN" lần thứ hai.
    # Theo tiền lệ Piper/VieNeu (hiện + nói thẳng đang thiếu gì), khác
    # OmniVoice (6,1 GB app không tự tải được nên mới giấu).
    try:
        from app.core import giong_vbee
        for ma_g, nhan_g in giong_vbee.danh_sach_giong():
            mo_rong.append((nhan_g, ma_g))
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
    _gh_xong = pyqtSignal(bool, str)    # tải bộ gióng hàng xong (ok, lời)
    #: (đường dẫn wav, nguồn giọng THẬT, lời lỗi) — nghe thử sinh xong ở
    #: thread nền. Phải qua tín hiệu: đụng widget từ thread nền là sập app.
    _nghe_xong = pyqtSignal(str, str, str)
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
        self._dang_cai_gh = False
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

        # NGHE THỬ — anh Hùng 16/08: *"không có phần nghe thử à"*. Trước đây
        # muốn biết giọng nghe ra sao phải chạy HẾT CẢ VIDEO (hàng phút) rồi mở
        # file ra nghe. Nhãn KHÔNG EMOJI (bài học v2.6.22: máy anh Hùng thiếu
        # glyph nên nút ra Ô ĐEN — "xấu quá tự nhiên có cái ô đen").
        self.b_nghe = QPushButton("Nghe thử")
        self.b_nghe.setToolTip(
            "Đọc một câu mẫu bằng ĐÚNG giọng và ĐÚNG cao độ đang chọn.\n"
            "Đi đúng cửa mà lượt xuất thật đi, nên nghe sao là ra vậy.")
        self.b_nghe.clicked.connect(self._nghe_thu)
        h2.addWidget(self.b_nghe)

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

        # ---- GỢI Ý GIỌNG NHIỀU CẢM XÚC ----
        # Anh Hùng 18/08/2026: *"giọng chả có hồn gì, không có cảm xúc, rất là
        # trơ"*. Combo trước đây chỉ hiện TÊN, nên không có cách nào biết giọng
        # nào sinh động hơn — đó là lỗi TRÌNH BÀY của tôi, không phải của anh
        # ấy. Nay mỗi giọng ĐÃ ĐO mang kèm số nhấn nhá, và dòng này gợi ý giọng
        # cao nhất cho ngôn ngữ đang chọn. Giọng CHƯA ĐO thì KHÔNG hiện số.
        self.lb_goi_y = QLabel("")
        self.lb_goi_y.setWordWrap(True)
        self.lb_goi_y.setStyleSheet("color:#7CC4FF")
        lay.addWidget(self.lb_goi_y)

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

        # ---- hàng 3bb: KHỚP TIẾNG VỚI HÌNH THEO CHIỀU NÀO ----
        # Anh Hùng 18/08/2026: *"giọng cứ lúc nhanh lúc chậm không đều —
        # **đáng nhẽ chỉ chỉnh video sao cho khớp giọng nói chứ**"*. Anh ấy
        # ĐÚNG: tới v2.37.0 đường này chỉ có MỘT chiều là ép tiếng vừa khung
        # câu gốc (`atempo`/`rubberband`), nên mỗi câu một hệ số ép -> tốc độ
        # đọc nhấp nhô. Mục ĐẦU giữ đúng hành vi cũ (không ai bị đổi sau lưng).
        h3bb = QHBoxLayout()
        h3bb.addWidget(QLabel("Khớp tiếng với hình:"))
        self.cb_khop = QComboBox()
        self.cb_khop.addItem("Ép giọng vừa video (có thể méo tiếng)", "")
        self.cb_khop.addItem(
            "Chỉnh video theo giọng (tiếng đều, khuyên dùng)", "hinh")
        self.cb_khop.setToolTip(
            "Ép giọng vừa video: giữ NGUYÊN độ dài video, câu nào đọc dài hơn "
            "khung thì bị ép nhanh lại — đó là chỗ sinh ra 'lúc nhanh lúc "
            "chậm' và tiếng bị méo.\n\n"
            "Chỉnh video theo giọng: giọng đọc ở tốc độ TỰ NHIÊN (hệ số ép "
            "1,000 cho MỌI câu), app làm CHẬM hình lại cho khớp. Hình không bị "
            "mã hoá lại một khung nào (dùng -itsscale) nên không mất chất "
            "lượng.\n"
            "GIÁ PHẢI TRẢ: video dài ra, và nhịp hình tụt theo hệ số — app tự "
            "chặn ở mức giữ >= 20 khung/giây, nguồn 23,976 fps thì tối đa "
            "chậm 1,199 lần. Cần chậm hơn mức đó thì phần dư vẫn phải ép "
            "tiếng, nhưng ít hơn hẳn.")
        _i = self.cb_khop.findData(str(self._s.value(K_KHOP_CACH, "") or ""))
        self.cb_khop.setCurrentIndex(max(0, _i))
        h3bb.addWidget(self.cb_khop)
        h3bb.addStretch(1)
        lay.addLayout(h3bb)

        # ---- hàng 3c + 3d: KIỂU CHỮ của dòng chữ mới ----
        # Anh Hùng 17/08/2026: *"phần chữ sub trong video tôi không điều chỉnh
        # được cỡ chữ, kiểu chữ, hay in nghiêng đậm, hay chỉnh viền gì được ạ"*.
        # Đường CẮT THƯỜNG đã có đủ trong Chỉnh mẫu; đường THAY GIỌNG thì
        # `grep "Fontsize|FontName|Outline|Bold|Italic" app/core/thay_giong.py`
        # ra 0 — cứng hết. Các ô dưới đây đi vào ĐƠN THUỐC `kieu_chu`
        # (`che_chu.KHOA_KIEU_CHU`) rồi xuống `captions.kieu_chu_ass` — CÙNG
        # MỘT CỬA với đường cắt thường, nên đặt cùng tham số là ra cùng kiểu.
        # BẤT BIẾN: ô nào để MẶC ĐỊNH thì KHÔNG vào đơn thuốc (`don_kieu_chu`
        # bỏ hẳn khoá đó) -> payload job giống TỪNG KHOÁ bản trước, không đẻ
        # job xuất lại cho 200-300 kênh.
        # ---- NÚT GẬP: 9 ô kiểu chữ nằm SAU nút này, mặc định GẬP ----
        # Anh Hùng 18/08/2026: *"cái phần edit chữ kia nhiều quá, không gom vào
        # làm 1 được à, hiển thị rối mắt quá"*. LỖI CỦA TÔI ở v2.32.0: thêm
        # đúng 9 ô vào giữa hộp, thành 2 hàng dày đặc chen giữa những thứ dùng
        # HẰNG NGÀY (thư mục · ngôn ngữ · giọng · số luồng · 2 ô tích · Chạy).
        #
        # GỘP bằng cách GẬP, **KHÔNG bằng cách bỏ ô nào** — mọi ô vẫn còn đủ,
        # vẫn cùng đối tượng widget, nên `don_kieu_chu` / `_luu` / `_o_kieu_chu`
        # KHÔNG phải sửa một dòng nào và round-trip lưu-đọc-lại giữ nguyên.
        #
        # Chọn "khu gập" chứ không "hộp thoại con": hộp con phải chuyển quyền
        # sở hữu widget + chép lại đường lưu/đọc = đúng chỗ đẻ ra lỗi "chọn X
        # ra Y" mà repo này đã sửa nhiều lần.
        h3kc = QHBoxLayout()
        self.b_kc_gap = QPushButton("")
        self.b_kc_gap.setCheckable(True)
        self.b_kc_gap.setChecked(False)      # MẶC ĐỊNH GẬP
        self.b_kc_gap.setToolTip(
            "Mở ra để chỉnh kiểu chữ của dòng chữ mới (kiểu · phông · cỡ · vị "
            "trí · đậm · nghiêng · màu chữ · màu viền · độ dày viền).\n"
            "Gập lại thì các ô vẫn giữ nguyên giá trị đã chọn — gập chỉ là ẩn "
            "đi cho hộp gọn, không phải trả về mặc định.")
        h3kc.addWidget(self.b_kc_gap)
        #: Nhãn TÓM TẮT — nói ra đang để mặc định hay đã đổi mấy mục, để anh
        #: Hùng biết mà không phải mở ra xem (gập mà không nói gì thì thành
        #: che mất thông tin, tệ hơn hiện cả 9 ô).
        self.lb_kc_tt = QLabel("")
        h3kc.addWidget(self.lb_kc_tt)
        h3kc.addStretch(1)
        lay.addLayout(h3kc)

        #: Khung chứa 9 ô — ẩn/hiện CẢ KHỐI theo nút gập.
        self._khung_kc = QWidget()
        _lkc = QVBoxLayout(self._khung_kc)
        _lkc.setContentsMargins(18, 0, 0, 0)   # thụt vào cho thấy nó thuộc nút

        h3c = QHBoxLayout()
        h3c.addWidget(QLabel("Kiểu chữ:"))
        self.cb_kc_preset = QComboBox()
        # Mục đầu phải NÓI RA mặc định thật (bài học cổng 16 v2.6.25a).
        self.cb_kc_preset.addItem(NHAN_KIEU_TU, "")
        for _t in CAPTION_PRESETS:
            self.cb_kc_preset.addItem(_t, _t)
        self.cb_kc_preset.setToolTip(
            "Dùng THẲNG các kiểu chữ có sẵn của 'Chỉnh mẫu' (màu chữ · màu "
            "viền · độ dày viền · bóng · nền hộp).\nĐể mục đầu là dùng kiểu "
            "mặc định y như bản trước.")
        _i = self.cb_kc_preset.findData(str(self._s.value(K_KC_PRESET, "") or ""))
        self.cb_kc_preset.setCurrentIndex(max(0, _i))
        h3c.addWidget(self.cb_kc_preset)

        h3c.addSpacing(8)
        h3c.addWidget(QLabel("Phông:"))
        self.cb_kc_font = QComboBox()
        self.cb_kc_font.addItem(NHAN_PHONG_TU, "")
        for _f in TG_CC.PHONG_UNG:
            self.cb_kc_font.addItem(_f, _f)
        self.cb_kc_font.setToolTip(
            "Danh sách này ĐÃ ĐO TỪNG CÁI (vẽ thật rồi so với phông bịa), "
            "không phải chép: phông nào libass không tìm ra thì nó lùi im "
            "lặng về phông mặc định mà ffmpeg vẫn trả mã 0.\n"
            "9 phông đầu đóng gói kèm app nên máy nhân viên chắc chắn có; 4 "
            "cái cuối là phông Windows.")
        _i = self.cb_kc_font.findData(str(self._s.value(K_KC_FONT, "") or ""))
        self.cb_kc_font.setCurrentIndex(max(0, _i))
        h3c.addWidget(self.cb_kc_font)

        h3c.addSpacing(8)
        h3c.addWidget(QLabel("Cỡ chữ:"))
        self.sp_kc_co = QDoubleSpinBox()
        # TỈ LỆ CHIỀU CAO KHUNG, không phải điểm ảnh: video thay giọng giữ
        # nguyên khung nguồn nên mỗi video một cỡ. Nhắc bẫy cổng 45(c): để lọt
        # tỉ lệ xuống .ass là `Fontsize: 0.055` = chữ dưới 1 điểm ảnh.
        self.sp_kc_co.setRange(0.0, 15.0)
        self.sp_kc_co.setSingleStep(0.5)
        self.sp_kc_co.setDecimals(1)
        self.sp_kc_co.setSuffix(" % cao khung")
        self.sp_kc_co.setSpecialValueText(NHAN_CO_TU)
        self.sp_kc_co.setToolTip(
            "Cỡ chữ tính theo PHẦN TRĂM chiều cao khung hình (video dọc "
            "1920 thì 8,5% = 163 điểm ảnh).\nĐể 0 thì app tự lấy theo bề cao "
            "dòng chữ CŨ vừa che — chữ mới to bằng chữ cũ.\n"
            "ĐÃ ĐO: từ khoảng 11% trở lên, dòng thứ hai bị CẮT ĐÁY KHUNG với "
            "nguồn có chữ sát mép dưới.")
        try:
            self.sp_kc_co.setValue(float(self._s.value(K_KC_CO, 0.0) or 0.0))
        except (TypeError, ValueError):
            self.sp_kc_co.setValue(0.0)
        h3c.addWidget(self.sp_kc_co)

        h3c.addSpacing(8)
        h3c.addWidget(QLabel("Vị trí:"))
        self.cb_kc_vitri = QComboBox()
        self.cb_kc_vitri.addItem(NHAN_VITRI_TU, "")
        self.cb_kc_vitri.addItem("Trên khung", "tren")
        self.cb_kc_vitri.addItem("Giữa khung", "giua")
        self.cb_kc_vitri.addItem("Dưới khung", "duoi")
        self.cb_kc_vitri.setToolTip(
            "Để mục đầu thì chữ mới nằm ĐÚNG CHỖ dòng chữ cũ vừa được che "
            "(khỏi lộ vệt che trống).\nChọn trên/giữa/dưới là đặt theo khung "
            "hình, không theo chữ cũ nữa.")
        _i = self.cb_kc_vitri.findData(str(self._s.value(K_KC_VITRI, "") or ""))
        self.cb_kc_vitri.setCurrentIndex(max(0, _i))
        h3c.addWidget(self.cb_kc_vitri)
        h3c.addStretch(1)
        _lkc.addLayout(h3c)

        h3d = QHBoxLayout()
        # ĐẬM/NGHIÊNG là BA trạng thái, không phải hai (xem `gon_kieu_chu`):
        # mục đầu = "theo kiểu chữ" (KHÔNG vào đơn thuốc), còn Có/Không là
        # lựa chọn THẬT của user. Dùng combo chứ không QCheckBox vì checkbox
        # chỉ có 2 trạng thái -> mọi job đều mọc thêm khoá `dam`/`nghieng`.
        h3d.addWidget(QLabel("In đậm:"))
        self.cb_kc_dam = QComboBox()
        self.cb_kc_dam.addItem(NHAN_DAM_TU, "")
        self.cb_kc_dam.addItem("Có", "1")
        self.cb_kc_dam.addItem("Không", "0")
        self.cb_kc_dam.setToolTip(
            "Mục đầu = giữ y như bản trước (chữ ĐANG in đậm).")
        _i = self.cb_kc_dam.findData(str(self._s.value(K_KC_DAM, "") or ""))
        self.cb_kc_dam.setCurrentIndex(max(0, _i))
        h3d.addWidget(self.cb_kc_dam)

        h3d.addSpacing(8)
        h3d.addWidget(QLabel("In nghiêng:"))
        self.cb_kc_nghieng = QComboBox()
        self.cb_kc_nghieng.addItem(NHAN_NGHIENG_TU, "")
        self.cb_kc_nghieng.addItem("Có", "1")
        self.cb_kc_nghieng.addItem("Không", "0")
        self.cb_kc_nghieng.setToolTip(
            "Mục đầu = giữ y như bản trước (chữ KHÔNG nghiêng).")
        _i = self.cb_kc_nghieng.findData(
            str(self._s.value(K_KC_NGHIENG, "") or ""))
        self.cb_kc_nghieng.setCurrentIndex(max(0, _i))
        h3d.addWidget(self.cb_kc_nghieng)

        # MÀU: dùng ĐÚNG cái nút anh Hùng đã quen trong Chỉnh mẫu (ô vuông
        # màu, chuột phải = về mặc định) — `editor.nut_chon_mau` đã tách ra
        # mức module đúng để chỗ này dùng lại, khỏi đẻ bộ điều khiển thứ hai.
        self._kc_mau = str(self._s.value(K_KC_MAU, "") or "")
        self._kc_vien = str(self._s.value(K_KC_VIEN, "") or "")
        h3d.addSpacing(8)
        h3d.addWidget(QLabel("Màu chữ:"))
        self.b_kc_mau, self._ve_kc_mau = nut_chon_mau(
            self, lambda: self._kc_mau, self._dat_kc_mau,
            "Màu chữ của dòng chữ mới", "theo kiểu chữ")
        h3d.addWidget(self.b_kc_mau)

        h3d.addSpacing(8)
        h3d.addWidget(QLabel("Màu viền:"))
        self.b_kc_vien, self._ve_kc_vien = nut_chon_mau(
            self, lambda: self._kc_vien, self._dat_kc_vien,
            "Màu viền của dòng chữ mới", "theo kiểu chữ")
        h3d.addWidget(self.b_kc_vien)

        h3d.addSpacing(8)
        h3d.addWidget(QLabel("Độ dày viền:"))
        self.sp_kc_dovien = QDoubleSpinBox()
        # TỈ LỆ so với CỠ CHỮ (giống khoá `ow` của preset), không phải px.
        self.sp_kc_dovien.setRange(0.0, 30.0)
        self.sp_kc_dovien.setSingleStep(1.0)
        self.sp_kc_dovien.setDecimals(0)
        self.sp_kc_dovien.setSuffix(" % cỡ chữ")
        self.sp_kc_dovien.setSpecialValueText(NHAN_VIEN_TU)
        self.sp_kc_dovien.setToolTip(
            "Độ dày viền tính theo PHẦN TRĂM CỠ CHỮ (các kiểu có sẵn dùng "
            "11-16%).\nĐể 0 thì lấy theo kiểu chữ đang chọn.")
        try:
            self.sp_kc_dovien.setValue(
                float(self._s.value(K_KC_DOVIEN, 0.0) or 0.0))
        except (TypeError, ValueError):
            self.sp_kc_dovien.setValue(0.0)
        h3d.addWidget(self.sp_kc_dovien)
        h3d.addStretch(1)
        _lkc.addLayout(h3d)
        lay.addWidget(self._khung_kc)

        #: Mọi ô kiểu chữ — bật/tắt theo ô "Viết lại bản dịch" (không viết chữ
        #: thì không có chữ nào để tạo kiểu).
        self._o_kieu_chu = [
            self.cb_kc_preset, self.cb_kc_font, self.sp_kc_co,
            self.cb_kc_vitri, self.cb_kc_dam, self.cb_kc_nghieng,
            self.b_kc_mau, self.b_kc_vien, self.sp_kc_dovien,
        ]

        self.ck_che.toggled.connect(self._doi_che_chu)
        self.ck_viet.toggled.connect(self._doi_viet_chu)
        self.b_kc_gap.toggled.connect(self._doi_gap_kc)
        # Mọi ô kiểu chữ đổi giá trị -> cập nhật lại nhãn tóm tắt, để lúc GẬP
        # anh Hùng vẫn thấy "đã đổi mấy mục".
        for _o in self._o_kieu_chu:
            for _sig in ("currentIndexChanged", "valueChanged", "clicked"):
                _s = getattr(_o, _sig, None)
                if _s is not None:
                    try:
                        _s.connect(lambda *_a: self._ve_tt_kc())
                    except (TypeError, RuntimeError):
                        pass
                    break
        self._doi_gap_kc(False)
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

        # ---- hàng 4c: BỘ GIÓNG HÀNG (mốc từng chữ cho MỌI máy đọc) ----
        # Cùng luật hàng Piper: thiếu thì LÙI ÊM (mốc kém chính xác hơn,
        # video vẫn đúng) nên KHÔNG khoá nút Chạy. Trước hôm nay anh Hùng và
        # nhân viên phải TỰ đặt file 1,18 GB vào `_giong_hang/` — không có
        # đường nào trong app tải được, tức tính năng coi như không tồn tại
        # với người không đọc mã.
        h4c = QHBoxLayout()
        self.lb_gh = QLabel("")
        self.lb_gh.setWordWrap(True)
        h4c.addWidget(self.lb_gh, 1)
        self.b_tai_gh = QPushButton(GH.NHAN_TAI_GH)
        self.b_tai_gh.setToolTip(
            "Tải bộ gióng hàng (torchaudio + uroman + model MMS_FA) về thư "
            "mục riêng.\n"
            "Đo thật: model 1.203,6 MB trên đĩa.\n"
            "Dùng CHUNG torch với bộ tách giọng — phải tải bộ tách giọng "
            "trước.\n"
            "Chỉ tải khi BẠN bấm — app không bao giờ tự tải sau lưng.")
        self.b_tai_gh.clicked.connect(self._tai_gh)
        h4c.addWidget(self.b_tai_gh)
        lay.addLayout(h4c)
        self._do_gh()

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
        # SÀN CHIỀU CAO CỦA BẢNG — **KHÔNG PHẢI CHO ĐẸP.** Hộp cao cố định
        # 1000x660 (`self.resize`), bảng lấy phần dôi bằng stretch=1. Mỗi lần
        # thêm một hàng điều khiển ở trên, phần dôi hụt đi; bảng KHÔNG có sàn nên
        # nó bị bóp TRƯỚC TIÊN. Đo 18/08/2026 sau khi thêm ô gợi ý giọng + ô
        # "Chỉnh video theo giọng": **viewport còn 1288x2 px** — 3 dòng CÓ THẬT
        # trong bảng mà anh Hùng KHÔNG THẤY GÌ, đúng câu anh ấy từng kêu *"ấn
        # chạy thì chỉ hiện thanh tiến trình, không hiện gì cả"* (cổng 57 ra đời
        # vì câu đó, và chính nó bắt lại được: 256 -> 0 điểm ảnh chữ).
        # 150 px = tiêu đề (~32) + 4 dòng (~29) -> luôn thấy ít nhất 4 video.
        self.bang.setMinimumHeight(150)
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
        self._gh_xong.connect(self._tai_gh_xong)
        self._nghe_xong.connect(self._nghe_thu_xong)

        self._do_demucs()
        self._nap_giong_nen()
        self._doi_thu_muc()

        # Nhịp riêng của hộp — hộp mở bằng exec() nên vòng lặp sự kiện của nó
        # vẫn chạy timer bình thường.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._nhip)
        self._timer.start(700)

    # ------------------------------------------------------------------
    # NGHE THỬ GIỌNG
    # ------------------------------------------------------------------
    def _nghe_thu(self) -> None:
        """Đọc câu mẫu bằng giọng đang chọn -> phát ra loa. KHÔNG chặn hộp.

        Phát bằng `winsound` (WAV, thư viện chuẩn) chứ KHÔNG `QMediaPlayer`:
        backend QtMultimedia trên nhiều máy Windows (wheel PyQt6 thiếu DLL
        FFmpeg) chết IM LẶNG — bấm không kêu gì mà cũng không báo gì. Cùng lý
        do `editor._dub_preview` đã chọn winsound.

        BẤM LIÊN TIẾP KHÔNG ĐƯỢC CHỒNG TIẾNG: khoá nút trong lúc sinh, và
        `SND_PURGE` ngắt tiếng cũ trước khi phát tiếng mới.
        """
        import threading

        voice = self.cb_giong.currentData() or ""
        if not voice:
            QMessageBox.information(
                self, "Nghe thử",
                "Mục đang chọn là “tự chọn theo ngôn ngữ đích” nên chưa biết "
                "giọng nào. Chọn một giọng cụ thể rồi bấm lại.")
            return
        self._ngat_tieng()
        self.b_nghe.setEnabled(False)
        self.b_nghe.setText("Đang đọc...")

        import tempfile
        import uuid
        wav = str(Path(tempfile.gettempdir())
                  / f"_bqnghe_{uuid.uuid4().hex[:8]}.wav")

        def bg() -> None:
            try:
                from app.core import thay_giong as TGC
                kq = TGC.doc_thu(voice, wav)
                self._nghe_xong.emit(kq.get("ra") or "", kq.get("nguon") or "",
                                     kq.get("loi") or "")
            except Exception as e:  # noqa: BLE001
                self._nghe_xong.emit("", "", str(e))

        threading.Thread(target=bg, daemon=True).start()

    def _ngat_tieng(self) -> None:
        """Ngắt tiếng nghe thử đang kêu (nếu có). Máy không có winsound thì im."""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:  # noqa: BLE001
            pass

    def _nghe_thu_xong(self, wav: str, nguon: str, loi: str) -> None:
        """Chạy ở LUỒNG GIAO DIỆN (qua tín hiệu) -> đụng widget mới an toàn."""
        self.b_nghe.setEnabled(True)
        self.b_nghe.setText("Nghe thử")
        if loi or not wav or not Path(wav).exists():
            QMessageBox.warning(
                self, "Nghe thử không được",
                f"Không đọc thử được giọng này.\n\nLý do: {loi or 'không rõ'}"
                "\n\nGiọng thường (edge-tts) cần MẠNG; giọng Piper cần đã tải "
                "về máy. Kiểm rồi bấm lại.")
            return
        # NGUỒN THẬT, không phải cái vừa chọn: Piper chưa tải thì app LÙI ÊM
        # về edge-tts — không nói ra thì anh Hùng tưởng đang nghe Piper.
        if "lùi" in nguon:
            self.lb_tt.setText(f"Nghe thử: {nguon}")
        try:
            import winsound
            winsound.PlaySound(
                wav, winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(
                self, "Nghe thử không được",
                f"Máy này không phát được âm thanh:\n{e}")

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
        # DUNG LƯỢNG PHẢI KHỚP ĐƯỜNG SẼ ĐI. 155 MB là SỐ ĐO của bản CPU
        # (cổng 58); máy có GPU NVIDIA thì `cai_demucs` lấy chỉ mục CUDA và
        # lượng tải là 2,5 GB (đo HTTP HEAD). Ghi cứng một con số là lặp lại
        # đúng lỗi cũ, chỉ đổi chiều: trước là nút ghi 155 MB mà hộp doạ 2 GB,
        # nay sẽ là hộp hứa 155 MB rồi tải 2,5 GB.
        gpu = TG.co_gpu_nvidia()
        if QMessageBox.question(
                self, "Tải bộ tách giọng",
                ("Máy này có GPU NVIDIA nên sẽ tải BẢN GPU: khoảng 2,5 GB, "
                 "về thư mục:\n" + self._tt_demucs["lib"]
                 + "\n\nĐÃ ĐO trên máy này: tách nhanh hơn 3,15 lần cả lượt "
                   "(60 giây tiếng: 29,3 giây -> 9,3 giây), chất lượng tách "
                   "KHÔNG đổi.\nMuốn bản nhẹ 155 MB thì tắt card NVIDIA rồi "
                   "bấm lại."
                 if gpu else
                 "Sẽ tải khoảng 155 MB về thư mục:\n" + self._tt_demucs["lib"])
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
            # DÒNG NÀY PHẢI ĐỔI THEO MÁY, KHÔNG PHẢI CÂU CỐ ĐỊNH. Đánh đổi cũ
            # ("mốc SUY RA nên rung gấp 1,53x edge-tts, 42% chữ hiện muộn")
            # CHỈ CÒN ĐÚNG khi máy chưa có bộ gióng hàng. Đo lại trên CÙNG 14
            # câu, cùng cửa `_synth_all_words` (`_do_piper_moc_that.py` +
            # `BQ_GIONG_HANG=0/1`):
            #     rung   51,8 -> 29,5 ms  (edge-tts đo cùng lượt: 38,6)
            #     trôi trong câu 42,0 -> 15,5 ms  <- đây mới là bệnh thật
            # Tức CÓ gióng hàng thì Piper bám lời SÁT HƠN cả giọng thường.
            # In câu cũ cho máy đã có gióng hàng là doạ người dùng bỏ một lựa
            # chọn đang tốt; in câu mới cho máy chưa có là hứa hão.
            from app.core import giong_hang as GH
            if GH.co_giong_hang():
                self.lb_piper.setText(
                    "Giọng Việt chạy trên máy (Piper): ĐÃ CÓ. "
                    "Chọn trong ô Giọng đọc để dùng.\n"
                    "Đã đo: máy này có bộ gióng hàng nên chữ bám lời còn "
                    "sát hơn giọng thường (lệch 29,5 ms so với 38,6 ms của "
                    "edge-tts). Mốc rơi sau tiếng khoảng 20 ms.")
            else:
                self.lb_piper.setText(
                    "Giọng Việt chạy trên máy (Piper): ĐÃ CÓ. "
                    "Chọn trong ô Giọng đọc để dùng.\n"
                    "Lưu ý đã đo: máy này CHƯA có bộ gióng hàng nên app phải "
                    "SUY RA mốc từng chữ — chữ chạy theo lời lệch gấp ~1,4 "
                    "lần so với giọng thường (edge-tts) và trôi dần về cuối "
                    "câu. Cần chữ bám sát lời thì dùng giọng thường.")
            self.lb_piper.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai_piper.setVisible(False)
        else:
            # Máy không có Python 3 -> `cai_piper()` chắc chắn trả lỗi, nên
            # KHOÁ nút y như nút Demucs (trước đây nút vẫn bấm được, user bấm
            # xong mới nhận lời báo). Khoá thì phải NÓI VÌ SAO, không thì nút
            # xám là câu đố.
            self.lb_piper.setText(
                "Giọng Việt chạy trên máy (Piper): CHƯA TẢI (212 MB) — chọn "
                "giọng này thì app vẫn chạy nhưng sẽ đọc bằng giọng thường "
                "(edge-tts)."
                + ("" if tt.get("cai_duoc", True) else
                   "\nMáy này chưa cài Python 3 nên app không tự tải được: "
                   "cài Python 3 (python.org) rồi bấm lại."))
            self.lb_piper.setStyleSheet("color:#B0B0B0; font-size:11px;")
            self.b_tai_piper.setVisible(True)
            self.b_tai_piper.setEnabled(
                bool(tt.get("cai_duoc", True)) and not self._dang_cai_piper)
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
    # BỘ GIÓNG HÀNG — MỐC TỪNG CHỮ CHO MỌI MÁY ĐỌC (không chặn gì)
    # ------------------------------------------------------------------
    def _do_gh(self) -> dict:
        """Dò bộ gióng hàng rồi cập nhật nhãn. KHÔNG khoá nút Chạy.

        Thiếu thì `dubbing._moc_giong_hang` trả nguyên mốc cũ — video vẫn ra
        đúng, chỉ mốc chữ kém chính xác hơn. Vì vậy đây là thông tin, không
        phải chốt chặn (khác hẳn Demucs ở hàng trên).
        """
        tt = GH.tinh_trang_giong_hang()
        self._tt_gh = tt
        if tt["co"]:
            self.lb_gh.setText(
                "Bộ gióng hàng mốc từng chữ: ĐÃ CÓ. Mọi giọng không tự trả "
                "mốc (Piper, giọng ngoài) sẽ lấy mốc bằng bộ này thay vì nhờ "
                "máy nghe chép ngược.")
            self.lb_gh.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai_gh.setVisible(False)
        else:
            # Nút xám mà không nói vì sao chỉ là câu đố — `vi_sao_khong_cai`
            # nói ĐÍCH DANH thứ còn thiếu (bài học cổng 58/16/51).
            self.lb_gh.setText(
                "Bộ gióng hàng mốc từng chữ: CHƯA TẢI (1,2 GB) — thiếu: "
                + ", ".join(tt["thieu"]) + ".\nKhông có nó thì giọng Piper và "
                "giọng ngoài phải nhờ máy nghe dò lại mốc: chữ chạy lệch tiếng "
                "hơn và tốn lượt mạng."
                + ("\n" + tt["vi_sao_khong_cai"]
                   if tt.get("vi_sao_khong_cai") else ""))
            self.lb_gh.setStyleSheet("color:#B0B0B0; font-size:11px;")
            self.b_tai_gh.setVisible(True)
            self.b_tai_gh.setEnabled(
                bool(tt.get("cai_duoc", True)) and not self._dang_cai_gh)
        return tt

    def _tai_gh(self) -> None:
        """NGƯỜI DÙNG BẤM thì mới tải — app không tự tải 1,2 GB sau lưng."""
        if getattr(self, "_dang_cai_gh", False):
            return
        if QMessageBox.question(
                self, "Tải bộ gióng hàng",
                "Sẽ tải torchaudio + uroman + model MMS_FA về:\n"
                + str(self._tt_gh.get("thu_muc", ""))
                + "\n\nRiêng model khoảng 1,18 GB (đo thật 1.203,6 MB), tải "
                  "một lần. Dùng CHUNG torch với bộ tách giọng nên không tải "
                  "thêm torch.\n\nTải bây giờ?"
                ) != QMessageBox.StandardButton.Yes:
            return
        self._dang_cai_gh = True
        self.b_tai_gh.setEnabled(False)
        self.b_tai_gh.setText("Đang tải...")

        def bg():
            r = GH.cai_giong_hang()
            self._gh_xong.emit(bool(r.get("ok")), str(r.get("loi") or "")[:400])

        threading.Thread(target=bg, daemon=True).start()

    def _tai_gh_xong(self, ok: bool, loi: str) -> None:
        self._dang_cai_gh = False
        self.b_tai_gh.setText(GH.NHAN_TAI_GH)
        self.b_tai_gh.setEnabled(True)
        tt = self._do_gh()
        # Nhãn Piper ĐỔI THEO việc có gióng hàng hay không -> phải dựng lại.
        # CỐ Ý KHÔNG dựng lại combo giọng: `_dung_combo_giong` đặt lại combo
        # theo giá trị ĐÃ LƯU, tức nuốt mất lựa chọn user vừa bấm mà chưa lưu
        # (đúng họ lỗi "chọn X ra Y"). Nhãn giọng ngoài tự đúng ở lần mở hộp
        # sau vì `nhan_giong()` hỏi lại máy mỗi lần dựng combo.
        self._do_piper()
        if ok and tt["co"]:
            QMessageBox.information(
                self, "Xong",
                "Đã tải xong bộ gióng hàng.\n" + str(tt.get("thu_muc", ""))
                + "\n\nTừ giờ giọng Piper và giọng ngoài lấy mốc bằng bộ này.")
        else:
            QMessageBox.warning(
                self, "Chưa tải được",
                "Chưa tải được bộ gióng hàng.\n\n" + (loi or "")
                + "\n\nApp vẫn dùng được bình thường — mốc chữ lấy theo cách "
                  "cũ.")

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
        # NGÔN NGỮ ĐÍCH quyết định thứ tự nhóm: chọn Tiếng Việt thì giọng Việt
        # phải lên đầu, không bị chôn dưới 47 giọng Anh. `_doi_ngon_ngu` đã
        # gọi lại hàm này mỗi lần đổi ngôn ngữ.
        nn = str(self.cb_nn.currentData() or "en")
        self.cb_giong.blockSignals(True)
        self.cb_giong.clear()
        self.cb_giong.addItem(NHAN_GIONG_TU, "")
        # GOM NHÓM (`app/core/giong_bang.py`, cổng 79). Trước v2.38.0 module
        # đó đã xong và có cổng xanh nhưng **KHÔNG MỘT AI GỌI** — anh Hùng mở
        # app vẫn thấy đúng cái danh sách "rất lung tung" của v2.37.0. Đây là
        # chỗ nối nó vào.
        #
        # `loi_tat=True` = luật anh Hùng chốt 19/08: nhóm "Khuyên dùng" ở đầu
        # GIỮ LẠI như một lối tắt (giọng vẫn còn trong nhóm gốc của nó), và
        # dòng lối tắt tự ghi "cùng giọng ở nhóm dưới" để không ai tưởng đó là
        # hai giọng khác nhau. Xem `giong_bang.gom_nhom`.
        #
        # SỐ NHẤN NHÁ nay do `gom_nhom` gắn (`giong_bang.duoi_nhan_nha`), UI
        # KHÔNG gắn thêm lần nữa — dán hai lần thì dòng ra "... nhấn nhá 4,0
        # ... nhấn nhá 4,0 ...".
        for nhan, vid in GB.gom_nhom(giong_dung_duoc(self._giong_tho), nn,
                                     loi_tat=True):
            self.cb_giong.addItem(nhan, vid)
            it = self.cb_giong.model().item(self.cb_giong.count() - 1)
            if not vid:                     # nhãn NHÓM -> không cho chọn
                if it is not None:
                    it.setEnabled(False)
            elif it is not None:
                # TOOLTIP = phần chữ dài không nhét vào dòng được (giấy phép,
                # điểm yếu đo được, việc phải tải). Nhờ nó mà nhãn VieNeu rút
                # từ 521 xuống ~60 ký tự mà KHÔNG mất một cảnh báo nào.
                it.setToolTip(self._chu_thich(vid, nhan))
        if muon:
            i = self.cb_giong.findData(muon)
            if i < 0:                       # giọng đã lưu nhưng list chưa có
                self.cb_giong.addItem(muon, muon)
                i = self.cb_giong.count() - 1
            self.cb_giong.setCurrentIndex(i)
        self.cb_giong.blockSignals(False)
        self._ve_goi_y()

    def _ve_goi_y(self) -> None:
        """Dòng gợi ý giọng nhiều cảm xúc nhất cho NGÔN NGỮ ĐANG CHỌN.

        Rỗng khi ngôn ngữ đó chưa có giọng nào trong bảng đo — thà không gợi ý
        còn hơn gợi ý một giọng chưa ai đo (bịa số cạnh tên giọng thì user sẽ
        tin mà chọn).

        Dựng THẲNG từ `nhan_nha.BANG` chứ không gọi một hàm gợi-ý riêng: bảng
        đó là NGUỒN DUY NHẤT của mọi con số nhấn nhá, nên dòng gợi ý và cái số
        hiện cạnh tên giọng không bao giờ nói hai chuyện khác nhau.
        """
        if not hasattr(self, "lb_goi_y"):
            return
        self.lb_goi_y.setText("")
        try:
            nn = str(self.cb_nn.currentData() or "en").split("-")[0].lower()
            # chỉ xét giọng ĐANG CÓ trong combo -> không gợi ý thứ không chọn
            # được (giọng bị lọc bỏ, hoặc ngôn ngữ khác đang không hiện).
            co = {self.cb_giong.itemData(i)
                  for i in range(self.cb_giong.count())}
            ung = [(v, m) for v, m in NN.BANG.items()
                   if v in co and str(v).lower().startswith(nn + "-")]
            if ung:
                ma, m = max(ung, key=lambda x: x[1])
                self.lb_goi_y.setText(
                    f"Giọng nhiều cảm xúc nhất đã đo: {self._ten_giong(ma)}"
                    f" ({NN.nhan(ma).lstrip(' -')})")
        except Exception:  # noqa: BLE001
            self.lb_goi_y.setText("")
        self.lb_goi_y.setVisible(bool(self.lb_goi_y.text()))

    def _chu_thich(self, vid: str, nhan: str) -> str:
        """Chữ hiện khi rê chuột lên một dòng giọng.

        Dòng trong combo cố ý NGẮN (đọc được khi combo đóng); mọi thứ dài mà
        vẫn phải nói ra — giấy phép, điểm yếu đã đo, phải tải bao nhiêu — nằm
        ở đây. Không giấu gì, chỉ đổi CHỖ ĐẶT.
        """
        dong = [nhan]
        try:
            from app.core import giong_vieneu
            if giong_vieneu.la_giong_vieneu(vid):
                dong.append(giong_vieneu.nhan_giong(vid))
        except Exception:  # noqa: BLE001
            pass
        try:
            can = GB.can_tai(vid)
            dong.append(f"Nguồn: {GB.TEN_NGUON.get(GB.nguon(vid), '?')}"
                        + (f" · phải tải {can}" if can else "")
                        + (" · miễn phí" if GB.mien_phi(vid)
                           else " · TỐN TIỀN/HẠN MỨC"))
            ms = GB.khop_ms(vid)
            if ms:
                dong.append(f"Chữ chạy lệch lời: {ms}")
        except Exception:  # noqa: BLE001
            pass
        return "\n".join(d for d in dong if d)

    def _ten_giong(self, ma: str) -> str:
        """Tên hiển thị của một mã giọng, lấy từ CHÍNH combo đang có."""
        i = self.cb_giong.findData(ma)
        if i >= 0:
            return str(self.cb_giong.itemText(i)).split("  ·  ")[0]
        return ma

    def _doi_ngon_ngu(self) -> None:
        # Nhãn nhấn nhá bám theo NGÔN NGỮ (số của corpus tiếng Việt không nói
        # được gì về giọng đọc tiếng khác) -> đổi ngôn ngữ phải dựng lại combo.
        self._dung_combo_giong()
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
        self._s.setValue(K_KHOP_CACH, self.cb_khop.currentData() or "")
        self._s.setValue(K_KC_PRESET, self.cb_kc_preset.currentData() or "")
        self._s.setValue(K_KC_FONT, self.cb_kc_font.currentData() or "")
        self._s.setValue(K_KC_CO, float(self.sp_kc_co.value()))
        self._s.setValue(K_KC_DAM, self.cb_kc_dam.currentData() or "")
        self._s.setValue(K_KC_NGHIENG, self.cb_kc_nghieng.currentData() or "")
        self._s.setValue(K_KC_MAU, self._kc_mau)
        self._s.setValue(K_KC_VIEN, self._kc_vien)
        self._s.setValue(K_KC_DOVIEN, float(self.sp_kc_dovien.value()))
        self._s.setValue(K_KC_VITRI, self.cb_kc_vitri.currentData() or "")

    def _dat_kc_mau(self, hexv: str) -> None:
        self._kc_mau = str(hexv or "")

    def _dat_kc_vien(self, hexv: str) -> None:
        self._kc_vien = str(hexv or "")

    def don_kieu_chu(self) -> dict:
        """ĐƠN THUỐC KIỂU CHỮ đọc từ các ô — CHỈ gồm ô user THẬT SỰ ĐẶT.

        Ô để mặc định thì **KHÔNG có khoá trong dict**, chứ không phải mang
        giá trị rỗng: `tg_chay.gon_kieu_chu` coi `None` là "không đặt" nhưng
        coi `dam=False` là lựa chọn THẬT, nên trả bừa `dam=False` cho ô chưa
        đụng tới là vừa đổi kiểu chữ vừa đổi khoá chống trùng của MỌI job.

        Dict rỗng -> `xep_mot` không ghi khoá `kieu_chu` vào payload -> job ra
        giống TỪNG KHOÁ bản trước.
        """
        kc: dict = {}
        if self.cb_kc_preset.currentData():
            kc["preset"] = str(self.cb_kc_preset.currentData())
        if self.cb_kc_font.currentData():
            kc["font"] = str(self.cb_kc_font.currentData())
        if float(self.sp_kc_co.value()) > 0:
            # ô ghi PHẦN TRĂM cho người đọc, đơn thuốc nhận TỈ LỆ.
            kc["co_chu"] = float(self.sp_kc_co.value()) / 100.0
        for khoa, o in (("dam", self.cb_kc_dam),
                        ("nghieng", self.cb_kc_nghieng)):
            v = str(o.currentData() or "")
            if v:
                kc[khoa] = (v == "1")
        if self._kc_mau:
            kc["mau"] = self._kc_mau
        if self._kc_vien:
            kc["vien"] = self._kc_vien
        if float(self.sp_kc_dovien.value()) > 0:
            kc["do_vien"] = float(self.sp_kc_dovien.value()) / 100.0
        if self.cb_kc_vitri.currentData():
            kc["vi_tri"] = str(self.cb_kc_vitri.currentData())
        return kc

    def _doi_che_chu(self, bat: bool) -> None:
        """Bật/tắt 2 ô con theo ô chính — tắt mà vẫn chỉnh được là gây hiểu
        nhầm 'đã bật' (đúng cái đã làm anh Hùng tưởng che chữ đang chạy)."""
        self.cb_che_cach.setEnabled(bool(bat))
        self.sp_che_muc.setEnabled(bool(bat))
        # Viết chữ dịch CHỈ có nghĩa khi đang che: viết đè lên chữ cũ mà không
        # che là HAI LỚP CHỮ chồng nhau, tệ hơn hẳn để nguyên.
        self.ck_viet.setEnabled(bool(bat))
        self._doi_viet_chu(self.ck_viet.isChecked())

    def _doi_gap_kc(self, mo: bool) -> None:
        """Mở/gập khu 9 ô kiểu chữ. GẬP KHÔNG ĐỔI GIÁ TRỊ NÀO.

        Sau khi ẩn/hiện phải `adjustSize()` — không thì hộp giữ nguyên chiều
        cao cũ và chỗ vừa gập thành một khoảng TRỐNG, tức gập mà hộp không gọn
        đi (đúng thứ anh Hùng đang chê).
        """
        self._khung_kc.setVisible(bool(mo))
        self.b_kc_gap.setText("Chỉnh chữ — thu lại" if mo else "Chỉnh chữ...")
        self._ve_tt_kc()
        # Chỉ CO khi gập: mở ra thì để layout tự giãn, còn gập thì phải ép co
        # (Qt không tự thu cửa sổ khi widget con biến mất).
        if not mo:
            self.adjustSize()

    def _ve_tt_kc(self) -> None:
        """Nhãn tóm tắt cạnh nút gập: đang mặc định, hay đã đổi mấy mục.

        Đếm bằng CHÍNH `don_kieu_chu()` — cửa duy nhất quyết định cái gì đi vào
        đơn thuốc. Đếm bằng cách tự đọc lại từng ô là đẻ ra nguồn sự thật thứ
        hai rồi lệch nhau (bài học "chọn X ra Y").
        """
        try:
            n = len(self.don_kieu_chu())
        except Exception:  # noqa: BLE001
            n = 0
        if not hasattr(self, "lb_kc_tt"):
            return
        if n:
            self.lb_kc_tt.setText(f"(đã đổi {n} mục)")
            self.lb_kc_tt.setStyleSheet("color:#7CC4FF")
        else:
            self.lb_kc_tt.setText("(đang để mặc định — chữ trắng viền đen)")
            self.lb_kc_tt.setStyleSheet("color:#8A93A6")

    def _doi_viet_chu(self, bat: bool) -> None:
        """Ô kiểu chữ chỉ sống khi ĐANG CHE **và** ĐANG VIẾT chữ mới.

        Phải xét CẢ HAI: `ck_viet` vẫn giữ dấu tích khi bị `setEnabled(False)`
        nên chỉ nhìn nó thôi là các ô kiểu chữ vẫn sáng trong khi cả nhánh
        viết chữ đang tắt — đúng kiểu hiểu nhầm 'đã bật' mà chốt trên đang
        chống.
        """
        song = bool(bat) and bool(self.ck_che.isChecked())
        for o in self._o_kieu_chu:
            o.setEnabled(song)
        # Nút gập cũng phải tắt theo: mở ra 9 ô xám ngoét thì vừa rối vừa gây
        # hiểu nhầm "chỉnh được".
        if hasattr(self, "b_kc_gap"):
            self.b_kc_gap.setEnabled(song)

    def _duyet_chi_phi(self, vids: list) -> bool:
        """Hiện ước lượng ký tự + hạn mức còn lại, hỏi có chạy không.

        True = chạy tiếp. Mặc định nút được chọn sẵn là **KHÔNG** — bấm Enter
        theo phản xạ thì không tiêu tiền của anh Hùng.

        `BQ_TG_BO_QUA_CHI_PHI=1` bỏ qua hộp này (cổng test dùng, để khỏi phải
        gọi mạng và khỏi treo ở hộp thoại).
        """
        if os.environ.get("BQ_TG_BO_QUA_CHI_PHI") == "1":
            return True
        try:
            uoc = tg_so.uoc_ky_tu(vids)
            from app.core.dubbing import eleven_credit_remain
            con = eleven_credit_remain()
        except Exception as e:  # noqa: BLE001
            # Ước lượng hỏng KHÔNG được chặn việc — nhưng phải nói ra.
            return QMessageBox.question(
                self, "Không ước lượng được chi phí",
                f"Không ước lượng được số ký tự ElevenLabs sẽ tiêu ({e}).\n\n"
                "Vẫn chạy?") == QMessageBox.StandardButton.Yes
        loi = tg_so.loi_chi_phi(uoc, con)
        h = QMessageBox(self)
        h.setWindowTitle("Giọng ElevenLabs — kiểm chi phí trước khi chạy")
        h.setIcon(QMessageBox.Icon.Warning)
        h.setText(loi)
        h.setInformativeText("Chạy mẻ này?")
        h.addButton("Chạy", QMessageBox.ButtonRole.AcceptRole)
        khong = h.addButton("Không chạy", QMessageBox.ButtonRole.RejectRole)
        h.setDefaultButton(khong)          # Enter = KHÔNG tiêu tiền
        h.exec()
        return h.clickedButton() is not khong

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
        # CHI PHÍ: giọng trả phí + chạy CẢ THƯ MỤC = dễ cạn hạn mức giữa mẻ.
        # Nói TRƯỚC, và để anh Hùng tự quyết (mặc định là KHÔNG chạy).
        if giong.startswith("el:") and not self._duyet_chi_phi(vids):
            return 0
        cc = bool(self.ck_che.isChecked())
        cc_cach = str(self.cb_che_cach.currentData() or "mo")
        cc_muc = float(self.sp_che_muc.value())
        cc_viet = bool(self.ck_viet.isChecked())
        # ĐƠN THUỐC KIỂU CHỮ đọc từ CHÍNH các ô đang hiện (không đọc QSettings
        # — bài học "chạy dây chuyền: đọc combo, không đọc setting": widget bị
        # blockSignals thì setting lệch với cái user đang nhìn).
        cc_kieu = self.don_kieu_chu()
        # ĐỌC TỪ COMBO ĐANG HIỆN, không đọc QSettings (cùng lý do trên).
        cc_hinh = str(self.cb_khop.currentData() or "") == "hinh"

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
                    viet_chu=cc_viet, kieu_chu=cc_kieu,
                    hinh_theo_giong=cc_hinh)
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
        self._ngat_tieng()      # đóng hộp -> tắt tiếng nghe thử còn kêu dở
        try:
            self._timer.stop()
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(e)

    def reject(self):  # noqa: D102 - Qt
        self.luu_cai_dat()
        self._ngat_tieng()
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
