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
import re
import threading
import unicodedata
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction, QColor, QFont, QFontMetrics, QKeySequence, QShortcut,
    QStandardItem,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QStyledItemDelegate, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core import che_chu as TG_CC
from app.core import giong_hang as GH
from app.core import giong_kokoro as KK
from app.core import giong_vieneu as VN_C
from app.core import tg_chay, tg_so
from app.core import thay_giong as TG
from app.core.captions import CAPTION_PRESETS
from app.database import db
from app.ui.appsettings import app_settings
from app.core import giong_bang as GB
from app.core import nhan_nha as NN
from app.ui.editor import nut_chon_mau
from app.ui.theme import (
    ACCENT, BASE, BORDER, DANGER, MUTED, SUCCESS, SURFACE, SURFACE_HOVER, TEXT,
    WARN,
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
#: CÁCH TRỘN TIẾNG — `"tach"` = thay hẳn giọng (tách nhạc, hành vi CŨ, MẶC ĐỊNH)
#: · `"de"` = đè giọng lên tiếng gốc, KHÔNG tách.
#: **MẶC ĐỊNH PHẢI LÀ `"tach"`**: đổi mặc định là đổi tiếng của MỌI video từ nay
#: trên 200-300 kênh đang chạy sản xuất. Anh Hùng nghe cả hai rồi mới quyết.
K_TRON_CACH = "tg_tron_cach"
#: HAI Ô ÂM LƯỢNG (dB) — anh Hùng 20/08/2026: *"cái phần âm thanh gốc nó nói bé
#: k tuỳ chỉnh âm thanh đc à chứ to quá"*.
#: **MẶC ĐỊNH PHẢI LÀ 0,0** = app tự đo tự quyết y như mọi bản trước. Số khác 0
#: mới sinh khoá trong payload + đuôi trong khoá chống trùng, nên để mặc định là
#: 200-300 kênh đang chạy KHÔNG bị xuất lại một video nào.
K_MUC_NEN = "tg_muc_nen_db"
K_MUC_GIONG = "tg_muc_giong_db"
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

# ---------------------------------------------------------------------------
# BỘ LỌC HỘP CHỌN GIỌNG (VIỆC 1)
# ---------------------------------------------------------------------------
# Anh Hùng 19/08/2026: *"thêm phần tìm kiếm giọng với lọc phân loại lại sao hợp
# lý chứ hiển thị bảng nhỏ mà tận mấy trăm giọng tìm rất khó"*.
#
# Ô TÌM ĐÃ CÓ từ cổng 84, và nó CHỈ tra theo CHỮ -> anh Hùng phải BIẾT TRƯỚC gõ
# gì. Với 364 dòng thì "biết trước gõ gì" là điều kiện không đáp ứng được: muốn
# một giọng nữ tiếng Hàn miễn phí thì không có từ nào gõ ra được nhóm đó. Bộ lọc
# dưới đây là đường ĐI NGƯỢC LẠI: bấm điều kiện, danh sách tự co.
#
# BA LUẬT BẤT BIẾN CỦA CẢ KHỐI NÀY:
#
# 1. **LỌC LÀ VIỆC CỦA USER BẤM, APP KHÔNG TỰ BỎ GIỌNG NÀO.** Mặc định mọi ô
#    đều `(tất cả)`, tức lần mở đầu tiên danh sách y hệt bản trước. Anh Hùng đã
#    chốt *"cứ thêm hết, tôi tự trải nghiệm"*.
# 2. **DỮ LIỆU LẤY TỪ MODULE ĐÃ ĐO, KHÔNG ĐOÁN LẠI Ở ĐÂY.** Tiếng lấy từ
#    `da_ngu.doc_duoc` (bảng ĐO ĐƯỢC + suy theo bộ đọc), tiền/chỗ-chạy lấy từ
#    `giong_bang.mien_phi`/`tren_may`. Viết bảng riêng trong file UI là đẻ bản
#    sao thứ hai rồi hai bên trôi khác nhau — đúng bẫy `_TIEN_TO` đã sập 2 lần.
# 3. **CHƯA ĐO THÌ GIỮ, KHÔNG LOẠI** (xem `_khop_tieng`). Quy tắc chung của repo
#    này: *không xác định được thì GIỮ* (cổng 20, `dbmaint._thoi_diem`).

#: Khoá QSettings của bộ lọc + cỡ hộp. Nhớ qua các lần mở để anh Hùng không
#: phải bấm lại/kéo lại — 300 kênh thì mỗi lần bấm lại là một lần phí.
K_GP_TIENG = "tg_gp_loc_tieng"
K_GP_GIOI = "tg_gp_loc_gioi"
K_GP_TIEN = "tg_gp_loc_tien"
K_GP_MAY = "tg_gp_loc_may"
K_GP_RONG = "tg_gp_rong"
K_GP_CAO = "tg_gp_cao"

#: Nhãn mục "không lọc". MỘT hằng số dùng cho CẢ 4 hàng — 4 chỗ gõ tay
#: `"(tất cả)"` là 4 chỗ có thể lệch nhau một dấu cách rồi `findData` trượt.
LOC_TAT_CA = "(tất cả)"

# ---------------------------------------------------------------------------
# CỠ HỘP CHỌN GIỌNG (VIỆC 2 — "bảng nhỏ mà tận mấy trăm giọng")
# ---------------------------------------------------------------------------
#: Cỡ MẶC ĐỊNH khi anh Hùng chưa kéo lần nào. Bản trước cao cứng **460** và
#: rộng vừa-nhãn; với 364 dòng thì 460 px chỉ đọc được ~19 dòng = **5% danh
#: sách**, còn 2 hàng nút lọc mới thêm lại ăn thêm ~52 px của phần đó. 560 px
#: đưa về ~19 dòng SAU khi đã trừ nút lọc, tức giữ nguyên số dòng đọc được rồi
#: mới cộng thêm phần lọc.
GP_CAO_CHUAN = 560
#: Rộng SÀN. Hai hàng nút lọc cần chỗ: hàng "Tiếng" có 7 nút + nhãn, hàng dưới
#: 9 nút + 3 nhãn. Hẹp hơn số này là nút xuống dòng/bị cắt chữ (bài học "nút
#: Copy bị cắt chữ" ở bản .exe v2.29.0).
GP_RONG_CHUAN = 640
#: SÀN CỨNG cho cỡ đọc từ QSettings — cài đặt rác/âm/0 không được biến hộp
#: thành một vệt không bấm được.
GP_RONG_TOI_THIEU = 420
GP_CAO_TOI_THIEU = 260
#: Cửa sổ chính cao hơn thì hộp cao theo tỉ lệ này (màn hình lớn = xem được
#: nhiều dòng hơn, không lý gì khoá cứng ở 560).
GP_TY_LE_CAO = 0.86
#: Số dòng popup MẶC ĐỊNH của combo được phép hiện. Chỉ dùng ở đường LÙI (khi
#: `_mo_chon_giong` ném lỗi, `ComboGiong.showPopup` gọi `super()`); mặc định Qt
#: là 10 dòng — với 364 dòng thì đường lùi đó vô dụng.
GP_SO_DONG_COMBO = 28

#: HÀNG TIẾNG — `(nhãn, mã)`. 5 tiếng đầu đúng bộ `da_ngu.NN5` (bộ DUY NHẤT có
#: số đo thật), cộng ô `dangu` cho giọng đọc-được-mọi-thứ-tiếng. Không thêm
#: tiếng thứ 6: `da_ngu` chưa đo tiếng nào khác nên ô đó sẽ lọc bằng phép SUY,
#: mà lọc bằng phép suy thì lúc nó bỏ sót giọng không ai biết vì sao.
LOC_TIENG: tuple[tuple[str, str], ...] = (
    (LOC_TAT_CA, ""),
    ("Việt", "vi"),
    ("Anh", "en"),
    ("Hàn", "ko"),
    ("Nhật", "ja"),
    ("Trung", "zh"),
    ("Đa ngôn ngữ", "dangu"),
)
LOC_GIOI: tuple[tuple[str, str], ...] = (
    (LOC_TAT_CA, ""), ("Nam", "nam"), ("Nữ", "nu"))
LOC_TIEN: tuple[tuple[str, str], ...] = (
    (LOC_TAT_CA, ""), ("Miễn phí", "mp"), ("Trả tiền", "tt"))
LOC_MAY: tuple[tuple[str, str], ...] = (
    (LOC_TAT_CA, ""), ("Trên máy", "may"), ("Qua mạng", "mang"))

#: DÒ GIỚI TÍNH TỪ NHÃN — **suy từ CHỮ ĐÃ CÓ, KHÔNG suy từ mã giọng.**
#: Vì sao không suy từ mã: mã `en-US-JennyNeural` không mang giới tính ở đâu cả,
#: nên "suy từ mã" thực chất là **đoán theo TÊN NGƯỜI** — 364 dòng gồm cả tên
#: Ả Rập/Thái/Swahili thì bảng tên nào cũng sai, mà sai kiểu im lặng.
#: Nhãn thì NÓI THẲNG, và đó là chữ chính anh Hùng đang đọc trên dòng.
#:
#: BỐN DẠNG CÓ THẬT TRONG DỮ LIỆU (đo `_do_loc_giong.py` trên 364 dòng, không
#: bịa dạng nào):
#:   · `Ryan (Nam) - nhấn nhá 5,4 ...`            <- 335 dòng edge-tts
#:   · `William (Nam, đa ngữ) - ...`              <- 12 dòng đa ngôn ngữ
#:   · `Andrew — Nam trầm ấm (tiếng Anh) - ...`   <- nhóm ĐỀ XUẤT của dubbing
#:   · `HN - Anh Khôi (nam, giọng kể chuyện) ...` <- Vbee, chữ THƯỜNG
#: nên `(nam` phải khớp cả `(Nam)` `(Nam,` `(nam,`.
#:
#: **BẪY "Nam Minh" — ĐÃ ĐO, ĐỪNG NỚI LỎNG HAI BIỂU THỨC NÀY.** `vi-VN-NamMinh`
#: có nhãn biến thể `Nam Minh — hơi cao`: chữ `Nam` ở đây là TÊN NGƯỜI, không
#: phải giới tính. Vì vậy dạng thứ ba đòi `—`/`-` NGAY TRƯỚC chữ Nam (trong
#: `Nam Minh — hơi cao` thì sau `—` là `hơi`, không khớp) và **không** có dạng
#: "bắt đầu dòng bằng Nam". 8 dòng biến thể cao độ vì thế ra KHÔNG RÕ ở phép dò
#: chữ, và được `gioi_giong` cứu bằng cách tra NHÃN CỦA GIỌNG GỐC.
_RE_GIOI_NU = re.compile(r"\([Nn]ữ[,)]|[—-]\s*Nữ\b")
_RE_GIOI_NAM = re.compile(r"\([Nn]am[,)]|[—-]\s*Nam\b")


def gioi_tu_nhan(nhan: str) -> str:
    """`"Ryan (Nam) - ..."` -> `"nam"`. Không đọc ra được -> `""`.

    Hàm THUẦN (chỉ chữ vào, chữ ra) để cổng test chấm được từng nhãn một, không
    phải dựng cả hộp thoại rồi suy ngược.

    Khớp CẢ HAI biểu thức -> trả `""`: nhãn nói hai chuyện thì thà không biết
    còn hơn chọn bừa một bên rồi lọc sai. (Đo trên 364 dòng: **0 dòng** khớp cả
    hai — chốt này là lưới cho dữ liệu SAU này, không phải cho hôm nay.)
    """
    s = str(nhan or "")
    a, b = bool(_RE_GIOI_NU.search(s)), bool(_RE_GIOI_NAM.search(s))
    if a == b:
        return ""
    return "nu" if a else "nam"


def gioi_giong(vid: str, nhan: str, nhan_goc: str = "") -> str:
    """Giới tính của một dòng giọng: đọc nhãn của nó, hụt thì đọc nhãn GIỌNG GỐC.

    `nhan_goc` = nhãn của mã sau khi bỏ hậu tố cao độ. Có nó thì 8 dòng biến thể
    (`Nam Minh — hơi cao`, `Hoài My — trầm`...) vẫn lọc đúng, vì giọng gốc
    `vi-VN-NamMinhNeural` mang nhãn `Nam Minh — Nam chuẩn (tiếng Việt)`.
    Biến thể cao độ KHÔNG đổi giới tính người đọc, nên tra sang gốc là đúng
    nghĩa chứ không phải mẹo.
    """
    g = gioi_tu_nhan(nhan)
    if g:
        return g
    return gioi_tu_nhan(nhan_goc) if nhan_goc else ""


def _khop_tieng(vid: str, ma: str) -> bool:
    """Giọng `vid` có lọt ô tiếng `ma` không (`ma` rỗng = không lọc).

    `dangu` -> hỏi `giong_bang.da_ngu` (giọng `*Multilingual*` của edge-tts).
    Còn lại -> hỏi `da_ngu.doc_duoc`, và **`None` (chưa đo) thì GIỮ**: loại một
    giọng vì mình chưa đo nó là giấu giọng đó khỏi anh Hùng mà không nói lý do.
    Đo được có `None`: tiếng Việt 10 dòng (2 edge · 5 OmniVoice · 3 Vbee) — 3
    dòng Vbee đúng là giọng Việt thật, loại đi là lọc SAI.
    """
    if not ma:
        return True
    if ma == "dangu":
        return bool(GB.da_ngu(vid))
    try:
        from app.core import da_ngu as _DN
        return _DN.doc_duoc(vid, ma) is not False
    except Exception:  # noqa: BLE001 - thiếu module -> đừng lọc mất giọng nào
        return True


def chua_do_tieng(vid: str, ma: str) -> bool:
    """Dòng này lọt ô tiếng `ma` vì CHƯA AI ĐO, chứ không vì đã đo là đọc được.

    Tách hẳn khỏi `_khop_tieng` để nhãn nói được ra chỗ mình chưa biết. `None`
    của `da_ngu.doc_duoc` nghĩa là *chưa đo / chưa kết luận* — chính module đó
    dặn: *"None KHÔNG PHẢI 'KHÔNG' ... nơi gọi phải phân biệt"*.
    """
    if not ma or ma == "dangu":
        return False
    try:
        from app.core import da_ngu as _DN
        return _DN.doc_duoc(vid, ma) is None
    except Exception:  # noqa: BLE001
        return False


def khop_loc(vid: str, nhan: str, loc: dict, nhan_goc: str = "") -> bool:
    """Một dòng giọng có lọt CẢ BỘ điều kiện đang bấm không.

    Hàm THUẦN, tách hẳn khỏi widget — cổng test gọi thẳng nó với từng tổ hợp,
    không phải đọc ngược từ số dòng trên màn hình.

    `loc` = `{"tieng": .., "gioi": .., "tien": .., "may": ..}`, giá trị rỗng =
    ô đó đang `(tất cả)`. Các ô CỘNG DỒN (AND) với nhau, và cộng dồn tiếp với ô
    TÌM ở nơi gọi.
    """
    v = str(vid or "")
    if not _khop_tieng(v, str(loc.get("tieng") or "")):
        return False
    gi = str(loc.get("gioi") or "")
    if gi and gioi_giong(v, nhan, nhan_goc) != gi:
        return False
    ti = str(loc.get("tien") or "")
    if ti:
        mp = bool(GB.mien_phi(v))
        if (ti == "mp") is not mp:
            return False
    ma = str(loc.get("may") or "")
    if ma:
        tm = bool(GB.tren_may(v))
        if (ma == "may") is not tm:
            return False
    return True

# ---------------------------------------------------------------------------
# BỀ RỘNG Ô DANH SÁCH GIỌNG
# ---------------------------------------------------------------------------
#: Ô danh sách không bao giờ hẹp hơn số này (nhãn nhóm ngắn nhất vẫn phải đọc
#: hết được).
RONG_TOI_THIEU = 420
#: Chỗ KHÔNG dùng được cho chữ trong một ô danh sách, đo thật trên hộp chọn
#: giọng: 16 lề hộp + 2 viền + ~20 **thanh cuộn** + 6 lề chữ trong dòng = 44,
#: cộng 12 px dự phòng. Thanh cuộn phải tính vào: ô danh sách giọng LUÔN dài hơn
#: màn hình nên nó LUÔN có, không phải trường hợp hiếm.
#:
#: **12 px dự phòng là số phải có, không phải cẩn thận quá mức.** Đo lần đầu với
#: 44 px: chỗ cho chữ ra **711 px** và nhãn dài nhất cũng đúng **711 px** — 0 px
#: dư. Lúc đó cổng chỉ cần phông nhích 1 px (máy khác, DPI khác, bản Qt khác) là
#: quay lại "nhãn bị cắt" mà số đo trên máy này vẫn 0.
LE_TRAN = 56


def rong_toi_da(w) -> int:
    """Trần bề rộng ô danh sách: KHÔNG quá CỬA SỔ, KHÔNG quá MÀN HÌNH.

    Vì sao phải có TRẦN CỬA SỔ chứ không chỉ trần màn hình: nhãn giọng
    OmniVoice dài **610 ký tự = 3.733 px** (đo 19/08/2026) nên "nới vừa nội
    dung" mà không chặn là ô danh sách phủ hết màn hình rồi vẫn còn thiếu. Trần
    cửa sổ giữ nó không rộng hơn cái hộp nó mọc ra từ đó.

    Vì sao vẫn phải có TRẦN MÀN HÌNH: cửa sổ có thể to hơn màn hình (anh Hùng
    kéo hộp rộng ra, hoặc máy nhân viên màn hình nhỏ hơn) — lúc đó nới theo cửa
    sổ là đẩy chữ ra ngoài mép màn hình, đúng cái vừa đi chữa chỉ khác chiều.
    """
    ung = []
    try:
        cs = w.window()
        if cs is not None and cs.width() > 0:
            ung.append(cs.width())
    except (AttributeError, RuntimeError):   # noqa: PERF203 - widget đã bị xoá
        pass
    try:
        mh = w.screen()
        if mh is not None:
            ung.append(mh.availableGeometry().width())
    except (AttributeError, RuntimeError):
        pass
    tran = min(ung) if ung else 900
    return max(RONG_TOI_THIEU, tran - LE_TRAN)


def tran_nhan(w) -> int:
    """Bề rộng TỐI ĐA cho CHỮ của một dòng (dùng cho `nhan_gon`).

    Hẹp hơn `rong_toi_da` đúng một lần `LE_TRAN`, và đó KHÔNG phải cẩn thận quá
    mức mà là số học: khi nhãn dài hơn trần, `rong_vua_chu` kẹp ô danh sách về
    `rong_toi_da`, rồi Qt còn trừ tiếp viền + thanh cuộn. Lấy cùng một số cho cả
    hai chỗ là để lại đúng `LE_TRAN` px thiếu -> nhãn vẫn bị elide, tức VIỆC 3
    làm xong mà số nhãn bị cắt KHÔNG về 0 và rất khó nhìn ra vì sao.
    """
    return max(300, rong_toi_da(w) - LE_TRAN)


def rong_vua_chu(fm, nhan_ds, tran: int) -> int:
    """Bề rộng vừa nhãn DÀI NHẤT, cộng chỗ thanh cuộn, chặn ở `tran`.

    Đo bằng ``fontMetrics().horizontalAdvance`` — bề rộng chữ THẬT với đúng
    phông đang dùng. **Đừng đoán theo số ký tự**: nhãn tiếng Việt có dấu, chữ
    hoa `KHÔNG ĐỌC ĐƯỢC` rộng hơn chữ thường cùng số ký tự.
    """
    if not nhan_ds:
        return max(RONG_TOI_THIEU, min(RONG_TOI_THIEU, tran))
    can = max(fm.horizontalAdvance(str(n or "")) for n in nhan_ds)
    return max(RONG_TOI_THIEU, min(int(can) + LE_TRAN, tran))


# ---------------------------------------------------------------------------
# VIỆC 3 — NHÃN NGẮN LẠI, PHẦN DÀI ĐẨY VÀO TOOLTIP
# ---------------------------------------------------------------------------
#: Thay cho `giong_bang.DAU_LOI_TAT` (" [lối tắt — cùng giọng ở nhóm dưới]",
#: 38 ký tự) — nó lặp trên MỌI dòng nhóm "Khuyên dùng" và ăn hết bề rộng, mà đó
#: là thứ đọc MỘT LẦN là hiểu. Nói một lần ở TIÊU ĐỀ NHÓM (`GHI_CHU_LOI_TAT`),
#: mỗi dòng chỉ còn dấu ngắn này, chi tiết nằm trong tooltip.
DAU_LOI_TAT_GON = " · lối tắt"
#: Ghi chú dán MỘT LẦN vào tiêu đề nhóm "Khuyên dùng".
GHI_CHU_LOI_TAT = " (mấy giọng này còn nằm ở nhóm dưới)"
#: Dán vào dòng bị rút gọn — user phải BIẾT là còn chữ chưa đọc, không thì rút
#: gọn thành giấu thông tin.
DAU_CON_CHU = " · rê chuột xem thêm"

#: Tách nhãn thành các PHẦN. Chỉ tách ở " - " / " · " CÓ KHOẢNG TRẮNG hai bên:
#: `đọc được Việt·Anh·Hàn·Nhật·Trung` dùng `·` KHÔNG có khoảng trắng nên không
#: bị xé, còn `cùng-một-mã` và `0,61-0,63` cũng vậy. KHÔNG tách ở gạch dài `—`
#: (nó nằm GIỮA TÊN: `Nam Minh — Nam chuẩn`).
_RE_TACH = re.compile(r"\s+[-·]\s+")

#: PHẦN PHẢI GIỮ LẠI trên dòng — đúng 5 câu anh Hùng cần trả lời ngay: **nó có
#: đọc sai chữ không** · nó đọc có cảm xúc không · nó đọc được tiếng gì · tốn
#: tiền không · phải tải gì. Phần nào KHÔNG khớp bộ này mà nhãn lại quá dài thì
#: đẩy vào tooltip.
#:
#: **CÂU CẢNH BÁO ĐỌC SAI PHẢI CÓ TRONG BỘ NÀY, nếu không thì bản vá 19/08/2026
#: coi như KHÔNG LÀM.** Đo được: nhãn VieNeu đi tới **mức 3** của `nhan_gon`
#: (cắt cả phần TÊN), tức mọi phần không khớp `_RE_GIU` đều bị đẩy im lặng vào
#: tooltip — cảnh báo *"ĐỌC SAI NHIỀU: 26,4% từ"* sẽ nằm ở chỗ phải rê chuột
#: mới thấy, đúng lúc nó cần đứng trên dòng. Lấy chữ mở đầu từ chính
#: `nhan_nha.DAU_DOC_SAI` (hằng số CÔNG KHAI, như `GB.DAU_LOI_TAT` đã dùng ở
#: hàm này) chứ KHÔNG chép tay: chép tay thì bên kia sửa một chữ là mục này im
#: lặng hết khớp.
_RE_GIU = (
    re.compile(re.escape(NN.DAU_DOC_SAI)),
    re.compile(r"(?:nhấn nhá\s|chưa đo nhấn nhá)"),
    re.compile(r"(?:đọc được|chỉ đọc tiếng|chỉ tiếng|chưa đo đọc"
               r"|chưa đo tiếng|KHÔNG đọc được|TIẾNG ANH)"),
    re.compile(r"(?:miễn phí|TỐN TIỀN|tốn hạn mức|cần key|phải tải|cần tải)"),
)


def _phan_giu(p: str) -> bool:
    """Phần này có phải thứ người dùng CẦN thấy ngay không?"""
    t = p.strip()
    return bool(t) and any(rx.match(t) for rx in _RE_GIU)


def nhan_gon(nhan: str, fm, tran: int) -> str:
    """Nhãn NGẮN cho một dòng giọng — phần dài đẩy vào tooltip.

    Anh Hùng 19/08/2026: ``[lối tắt — cùng giọng ở nhóm dưới]`` lặp 5 lần và
    **ăn hết bề rộng**. Nặng hơn (đo được, không có trong lời anh ấy nhưng cùng
    một bệnh): nhãn giọng OmniVoice dài **591-610 ký tự = tới 3.733 px**, tức
    KHÔNG BỀ RỘNG NÀO đủ — nới ô danh sách (VIỆC 1) một mình không bao giờ đưa
    được số nhãn bị cắt về 0.

    **KHÔNG BỎ GIỌNG NÀO, chỉ đổi cách BÀY** (anh Hùng đã chốt *"trùng lặp cũng
    được, cứ thêm"*) — hàm này chỉ đụng CHỮ HIỂN THỊ, mã giọng đi kèm không đổi
    một ký tự, nên round-trip lưu/đọc lại không thể lệch.

    Ba mức, theo thứ tự nhẹ tay dần:

    1. **Vừa rồi thì KHÔNG SỬA GÌ** (sau khi thay dấu lối tắt): giữ nguyên từng
       byte cho ~98% dòng, tức bản vá này gần như không có mặt ở chúng.
    2. Không vừa -> giữ phần TÊN + đúng 4 phần phải-thấy-ngay (`_RE_GIU`), mọi
       phần khác đẩy vào tooltip và dán ``DAU_CON_CHU`` để user biết còn chữ.
    3. Vẫn không vừa -> ép chính phần TÊN, **giữ nguyên cái đuôi tiền/tải**:
       cắt tên còn khó chịu chứ cắt mất "TỐN TIỀN" là bấm nhầm mất tiền thật.
    """
    s = str(nhan or "")
    lt = GB.DAU_LOI_TAT in s
    if lt:
        s = s.replace(GB.DAU_LOI_TAT, "")
    if fm.horizontalAdvance(s + (DAU_LOI_TAT_GON if lt else "")) <= tran:
        return s + (DAU_LOI_TAT_GON if lt else "")

    # tách phần, GIỮ ĐÚNG vị trí để cắt được nguyên văn (đừng ghép lại phần
    # TÊN bằng " · " — nhãn Vbee "HN - Anh Khôi ..." sẽ thành "HN · Anh Khôi")
    moc: list[tuple[int, int, str]] = []
    i = 0
    for m in _RE_TACH.finditer(s):
        moc.append((i, m.start(), s[i:m.start()]))
        i = m.end()
    moc.append((i, len(s), s[i:]))

    k = [j for j, (_a, _b, p) in enumerate(moc) if _phan_giu(p)]
    if not k:                       # nhãn lạ, không nhận ra phần nào -> ép thẳng
        return fm.elidedText(s + (DAU_LOI_TAT_GON if lt else ""),
                             Qt.TextElideMode.ElideRight, tran)
    ten = s[:moc[k[0] - 1][1]] if k[0] > 0 else ""
    duoi = "".join(f" · {moc[j][2].strip()}" for j in k)
    if lt:
        duoi += DAU_LOI_TAT_GON
    # CÓ PHẦN BỊ ĐẨY VÀO TOOLTIP THÌ PHẢI NÓI RA — nhưng chỉ đếm phần nằm SAU
    # phần-phải-giữ đầu tiên. **BẢN ĐẦU ĐẾM SAI VÀ ĐÃ ĐO RA:** nhãn VieNeu
    # `Xuân Vĩnh — Nam · Nam · Phong cách tự nhiên (VieNeu)` tự nó đã có 2 dấu
    # ` · ` nên bị tính thành 3 "phần bị bỏ", trong khi cả 3 đều nằm trong phần
    # TÊN và được giữ nguyên -> dòng dán "rê chuột xem thêm" trong khi KHÔNG bỏ
    # gì, tức nói với anh Hùng một câu không đúng rồi còn ăn 130 px bề rộng.
    if any(j > k[0] and j not in k for j in range(len(moc))):
        duoi += DAU_CON_CHU
    con = tran - fm.horizontalAdvance(duoi)
    if con < 120:                   # đuôi đã kín chỗ -> ép cả dòng, thà cụt tên
        return fm.elidedText(s, Qt.TextElideMode.ElideRight, tran)
    return fm.elidedText(ten, Qt.TextElideMode.ElideRight, con) + duoi


#: Vai trò dữ liệu đánh dấu "dòng này là TIÊU ĐỀ NHÓM". Phải là cờ RIÊNG, không
#: được suy từ "mã giọng rỗng": dòng ĐẦU (`NHAN_GIONG_TU`) cũng có mã rỗng mà nó
#: là một LỰA CHỌN THẬT — coi nó là tiêu đề nhóm là khoá mất lựa chọn mặc định.
VAI_NHOM = int(Qt.ItemDataRole.UserRole) + 7


def to_nhan_nhom(it) -> None:
    """VIỆC 2 — đánh dấu TIÊU ĐỀ NHÓM: KHÔNG CHỌN ĐƯỢC + cho bộ vẽ biết.

    **`setEnabled(False)` KHÔNG PHẢI "không chọn được".** Nó chỉ gỡ
    ``ItemIsEnabled``; cờ ``ItemIsSelectable`` **VẪN CÒN**, nên dòng tiêu đề vẫn
    chọn được bằng bàn phím/mã. Phải gỡ SẠCH bằng ``NoItemFlags`` — và cổng 84
    kiểm CHÍNH CỜ ĐÓ chứ không chỉ kiểm màu: đổi màu mà vẫn chọn được thì bấm
    vào tiêu đề là app nhận một "giọng" tên
    *"MIỄN PHÍ (edge-tts) - giọng Tiếng Việt"*.

    **VÌ SAO KHÔNG `setForeground`/`setFont` — ĐÃ THỬ VÀ ĐO RA LÀ VÔ TÁC DỤNG.**
    QSS chung của app mở đầu bằng ``* {{ color: TEXT; font-family: ...;
    font-size: 13px }}``; bộ vẽ item của `QStyleSheetStyle` lấy màu/phông từ QSS
    và **đè lên** màu/phông đặt trên từng item. Soi điểm ảnh bản dùng
    `setForeground(ACCENT)` (#4C8DFF): màu chữ dòng tiêu đề đo ra **#E8EDF7** —
    tức vẫn là màu TEXT, xanh không hề tới. Đây đúng họ bẫy đã cắn repo này một
    lần (QSS chung bóp widget con còn ~0 => "dòng trống trơn trên máy user mà
    test không QSS vẫn PASS"). Nên việc VẼ giao cho `VeDongGiong` — nó tự tô,
    không xin phép QSS.

    Nhận cả ``QStandardItem`` (combo) lẫn ``QListWidgetItem`` (ô tìm giọng) —
    hai chỗ bày CÙNG một danh sách thì phải trông GIỐNG NHAU, nên chỉ MỘT hàm
    này. **Hai lớp đó đảo NGƯỢC thứ tự tham số của `setData`** (QStandardItem:
    `(giá trị, vai)` · QListWidgetItem: `(vai, giá trị)`) và gọi sai thì KHÔNG
    nổ lỗi — `True` tự thành `int` 1 = `DecorationRole`, tức dòng im lặng mất
    dấu nhóm. Vì vậy phải `isinstance`, đừng `try/except TypeError`.
    """
    it.setFlags(Qt.ItemFlag.NoItemFlags)      # thật sự không chọn được
    if isinstance(it, QStandardItem):
        it.setData(True, VAI_NHOM)
    else:
        it.setData(VAI_NHOM, True)


class VeDongGiong(QStyledItemDelegate):
    """Bộ vẽ dòng cho ô danh sách giọng — tiêu đề nhóm KHÁC HẲN dòng giọng.

    Tự vẽ chứ không nhờ `setForeground`/`setFont`: xem lý do đo được ở
    `to_nhan_nhom`. Ba dấu hiệu cùng lúc, để không phụ thuộc một thứ nào:

    * **VẠCH MÀU** dày 4 px ở lề trái — đọc được cả khi người dùng mù màu;
    * **NỀN SÁNG HƠN** cả dải (`SURFACE_HOVER`) — tách nhóm bằng khối, không
      chỉ bằng chữ;
    * **CHỮ ĐẬM + MÀU ACCENT**.

    Dòng giọng để `QStyledItemDelegate` vẽ y như cũ — không đụng gì.
    """

    def paint(self, painter, option, index):    # noqa: N802 - API Qt
        if not index.data(VAI_NHOM):
            super().paint(painter, option, index)
            return
        painter.save()
        r = option.rect
        painter.fillRect(r, QColor(SURFACE_HOVER))
        painter.fillRect(r.left(), r.top(), 4, r.height(), QColor(ACCENT))
        f = QFont(option.font)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor(ACCENT))
        o = r.adjusted(12, 0, -6, 0)
        painter.drawText(
            o, int(Qt.AlignmentFlag.AlignVCenter),
            QFontMetrics(f).elidedText(str(index.data() or ""),
                                       Qt.TextElideMode.ElideRight, o.width()))
        painter.restore()


def bo_dau(s: str) -> str:
    """`Hoài My` -> `hoai my` — để gõ KHÔNG DẤU vẫn tìm ra giọng.

    Anh Hùng gõ nhanh và không bỏ dấu; bắt gõ đúng "Hoài My" thì ô tìm chỉ chạy
    được với giọng tên tiếng Anh. Bỏ dấu bằng NFD rồi vứt nhóm dấu `Mn`, giữ
    được cả `đ` -> `d` nhờ bảng thay riêng (NFD KHÔNG tách `đ`).
    """
    t = unicodedata.normalize("NFD", str(s or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t.replace("đ", "d").replace("Đ", "d")


class ComboGiong(QComboBox):
    """Combo giọng — bấm vào là mở DANH SÁCH CÓ Ô TÌM, không phải popup thường.

    Cùng khuôn `studio_page._ChanCombo`: `picker` gán từ ngoài, lỗi thì **LÙI
    về popup mặc định** chứ không để user bấm mà không có gì mở ra.

    **VẪN LÀ COMBO, KHÔNG BIẾN THÀNH Ô-GÕ** — bẫy này đã sập với ô tìm kênh ở
    v2.6.10 (anh Hùng: *"này không mở được"*): đổi combo thành `QLineEdit` là
    mất luôn cái danh sách bấm-để-xem.
    """

    picker = None                       # gán từ ngoài: callable không tham số

    def showPopup(self):                # noqa: N802 - API Qt
        if callable(self.picker):
            try:
                self.picker()
                return
            except Exception:  # noqa: BLE001 - hỏng thì vẫn phải mở được cái gì
                pass
        super().showPopup()


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

    # ---- GIỌNG CỦA ANH HÙNG — NHÂN BẢN TỪ MẪU, LƯU LẠI DÙNG MÃI ----
    # Anh Hùng: *"ném giọng đọc của tôi khoảng mấy giây Reference Audio, sau đó
    # dán bao nhiêu ký tự dùng giọng đó cũng được... không lấy của bất kỳ ai
    # nữa, tự động lấy của mình luôn"*.
    #
    # **CA THỨ NĂM CỦA CÙNG MỘT BỆNH** sau `giong_bang`, `giong_chatter`,
    # `giong_vbee`, `giong_kokoro`: `app/core/nhan_ban_giong.py` dựng xong 564
    # dòng (kiểm mẫu · sổ ra đĩa · chép mẫu vào DATA_DIR · xoá/đổi tên) mà
    # **không một dòng nào trong `app/ui/` gọi tới** — đo trước khi vá:
    # `grep -rn "nhan_ban_giong" app/ui/` -> **0 dòng**. Tức tính năng coi như
    # KHÔNG TỒN TẠI với người không đọc mã.
    #
    # ═══ VÌ SAO KHÔNG ĐẺ TIỀN TỐ `toi:` — ĐO ĐƯỢC, KHÔNG PHẢI SỞ THÍCH ═══
    # Mã giọng ở đây là `vnb:<đường dẫn mẫu>` (VieNeu) / `cb:<lang>|<mẫu>`
    # (Chatterbox), tức TIỀN TỐ NGUYÊN BẢN CỦA MÁY. Thêm một quy ước thứ ba là
    # thêm một chỗ để quên, và chỗ quên đó ĐO ĐƯỢC: `giong_bang.nguon("toi:x")`
    # trả **`'edge'`** — tức một tiền tố chưa đăng ký sẽ bị coi là edge-tts và
    # cả nhóm giọng rơi vào bẫy "chọn X ra Y" mà `ov:nu_am` / `vn:` / `cb:` /
    # `kk:` đã sập BỐN lần. Ngược lại `vnb:` đã đăng ký ĐỦ: `giong_bang.
    # _TIEN_TO` biết nó (đứng TRƯỚC `vn:` vì dài hơn), và **CẢ HAI** cửa đọc
    # `dubbing._synth_all` + `_synth_all_words` đều rẽ đúng — kiểm bằng AST
    # (cả hai thân hàm gọi `_vieneu_hay_khong`) VÀ bằng cách GỌI THẬT rồi xem
    # `giong_vieneu.doc_loat` có nhận `vnb:` không. Cổng 81 CA 7h canh đúng
    # quyết định này.
    #
    # `chi_chay_duoc=False` (mặc định): giọng mà máy CHƯA cài được máy nhân bản
    # vẫn HIỆN, nhãn tự mang "CHƯA CHẠY ĐƯỢC (thiếu torch, torchaudio)" — tiền
    # lệ Piper/VieNeu/Kokoro. Giấu đi thì anh Hùng không biết giọng mình đã lưu
    # còn đó; hiện kèm lý do thì biết phải bấm gì.
    try:
        from app.core import nhan_ban_giong
        cuoi_vi4 = max((i for i, (_n, v) in enumerate(mo_rong)
                        if str(v).startswith("vi-VN")
                        or str(v).startswith("piper:")
                        or str(v).startswith("ov:")
                        or str(v).startswith("ix:")
                        or str(v).startswith("vn:")), default=-1)
        for j, (ma_g, nhan_g) in enumerate(nhan_ban_giong.danh_sach()):
            mo_rong.insert(cuoi_vi4 + 1 + j, (nhan_g, ma_g))
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

    # ---- GIỌNG KOKORO — 28 GIỌNG, Apache 2.0, chạy trên máy ----
    # Ca thứ TƯ của cùng một bệnh sau `giong_bang`, `giong_chatter` và
    # `giong_vbee`: `app/core/giong_kokoro.py` dựng xong (hàm đọc + hàm cài +
    # 28 giọng đã dò giấy phép) mà **combo không có một dòng `kk:` nào** — đo
    # trước khi vá: `grep -c "kk:" thay_giong_dialog.py` -> **0**. Tức tính
    # năng coi như KHÔNG TỒN TẠI với người không đọc mã.
    #
    # ĐIỀU KIỆN TIÊN QUYẾT ĐÃ LÀM TRƯỚC, ĐỪNG ĐẢO THỨ TỰ: `dubbing._synth_all`
    # VÀ `_synth_all_words` đều đã biết `kk:` (kiểm bằng `inspect.getsource`,
    # không phải đọc mắt). Đưa mã vào combo mà **một** trong hai cửa chưa nhận
    # thì video ra HAI GIỌNG TRỘN mà `rc` vẫn 0 — đúng bẫy `ov:nu_am` / `vn:` /
    # `cb:` đã sập BA lần.
    #
    # **HIỆN ĐỦ 28 DÒNG KỂ CẢ KHI CHƯA TẢI**, nhãn tự mang cụm "CHƯA TẢI" của
    # `giong_kokoro.dau_chua_tai` (app TỰ TẢI được 538 MB) — tiền lệ
    # Piper/VieNeu, khác OmniVoice 6,1 GB phải giấu vì app không tự tải nổi.
    # `danh_sach_giong()` tự dò tình trạng MỘT LẦN cho cả 28 dòng.
    try:
        from app.core import giong_kokoro
        for ma_g, nhan_g in giong_kokoro.danh_sach_giong():
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


class HopGiongToi(QDialog):
    """GIỌNG CỦA ANH HÙNG — đưa file mẫu vài giây vào, ra một giọng dùng mãi.

    Anh Hùng: *"ném giọng đọc của tôi khoảng mấy giây Reference Audio, sau đó
    dán bao nhiêu ký tự dùng giọng đó cũng được... đảm bảo giọng đó lưu được
    với thêm được nhiều giọng"*.

    ═══ "LƯU ĐƯỢC" NGHĨA LÀ GÌ — NÓI CHÍNH XÁC, ĐỪNG HỨA QUÁ ═══
    VieNeu nhân bản **tại lúc đọc** (zero-shot), nên "lưu" ở đây là: chọn file
    MỘT LẦN, đặt tên, rồi mãi mãi chỉ chọn cái tên đó. App KHÔNG nén giọng
    thành một file nhỏ — nói khác đi là hứa một thứ không có. Đổi lại có một
    thứ bảo đảm thật: **mẫu được CHÉP VÀO `DATA_DIR`**, nên anh Hùng xoá/di
    chuyển/đổi tên file gốc thì giọng vẫn chạy.

    ═══ HAI NÚT NGHE THỬ, CỐ Ý KHÁC NHAU ═══
      · **"Nghe thử mẫu"** — phát THẲNG file mẫu vừa chọn. Tức thời, không nạp
        model. Để trả lời *"tôi có chọn đúng file không"*.
      · **"Nghe thử giọng"** — chạy NHÂN BẢN THẬT qua `thay_giong.doc_thu`,
        tức đúng cửa lượt xuất đi. Đo được: **~38 giây** cho câu đầu (phần lớn
        là nạp model) nên nút phải khoá lại và nói "Đang đọc...", nếu không
        anh Hùng bấm tiếp 3 lần rồi tưởng app treo.
    Gộp hai nút làm một là mất cái rẻ hoặc mất cái thật.

    **KHÔNG đụng widget từ thread nền** — mọi kết quả về qua tín hiệu, đúng
    khuôn `ThayGiongDialog._nghe_xong`. Nhãn TIẾNG VIỆT, **KHÔNG EMOJI** (bài
    học v2.6.22: máy anh Hùng thiếu glyph nên nút ra Ô ĐEN).
    """

    #: (đường dẫn wav, nguồn giọng THẬT, lời lỗi, cảnh báo)
    _nghe_xong = pyqtSignal(str, str, str, str)
    #: bắn khi sổ giọng ĐỔI -> hộp cha dựng lại combo
    so_doi = pyqtSignal()
    #: tải phần nhân bản (torch + torchaudio) xong (ok, lời)
    _nb_xong = pyqtSignal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Giọng của tôi — nhân bản từ file mẫu")
        self.setMinimumWidth(700)
        self._mau = ""                       # file mẫu đang chọn
        lay = QVBoxLayout(self)

        # ---- CẢNH BÁO PHÁP LÝ: ngay tại chỗ chọn file, KHÔNG giấu vào tài
        # liệu. Đây là rủi ro nặng nhất của cả tính năng và nó không phải rủi
        # ro kỹ thuật — anh Hùng BÁN app nên người chịu là anh ấy.
        from app.core import nhan_ban_giong as NB
        lb_pl = QLabel("LƯU Ý PHÁP LÝ: " + NB.CANH_BAO_PHAP_LY)
        lb_pl.setWordWrap(True)
        lb_pl.setStyleSheet("color:#FFB86C")
        lay.addWidget(lb_pl)

        lay.addWidget(QLabel("Giọng đã lưu:"))
        self.ds = QListWidget()
        self.ds.setMinimumHeight(150)
        lay.addWidget(self.ds, 1)

        # ---- hàng TẢI PHẦN NHÂN BẢN ----
        # Đặt NGAY DƯỚI danh sách, cố ý: dòng "CHƯA CHẠY ĐƯỢC (thiếu torch,
        # torchaudio)" hiện ở danh sách ngay trên, nên đường sửa phải nằm sát
        # nó. Trước lượt này nhãn đó nói thật mà **không có nút nào để bấm** —
        # tính năng thật thà báo hỏng rồi bỏ người dùng ở đó.
        self._dang_cai_nb = False
        h_nb = QHBoxLayout()
        self.lb_nb = QLabel("")
        self.lb_nb.setWordWrap(True)
        h_nb.addWidget(self.lb_nb, 1)
        self.b_tai_nb = QPushButton(VN_C.nhan_tai_nhan_ban())
        self.b_tai_nb.clicked.connect(self._tai_nhan_ban)
        h_nb.addWidget(self.b_tai_nb)
        lay.addLayout(h_nb)
        self.pb_nb = QProgressBar()
        self.pb_nb.setVisible(False)
        lay.addWidget(self.pb_nb)

        # ---- hàng THÊM GIỌNG ----
        h1 = QHBoxLayout()
        self.b_chon = QPushButton("Chọn file mẫu...")
        self.b_chon.setToolTip(
            "File tiếng của anh, 5-30 giây, CHỈ MỘT NGƯỜI nói, không nhạc "
            "nền.\nNhận wav / mp3 / m4a / video — app tự đổi sang dạng nó "
            "dùng được.")
        self.b_chon.clicked.connect(self._chon_mau)
        h1.addWidget(self.b_chon)
        self.lb_mau = QLabel("(chưa chọn file mẫu)")
        self.lb_mau.setWordWrap(True)
        h1.addWidget(self.lb_mau, 1)
        lay.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Tên giọng:"))
        self.o_ten = QLineEdit()
        self.o_ten.setPlaceholderText("ví dụ: Giọng của tôi")
        self.o_ten.setToolTip(
            "Tên anh tự đặt, tiếng Việt có dấu cũng được. Đây là thứ anh sẽ "
            "thấy trong ô Giọng đọc.")
        h2.addWidget(self.o_ten, 1)
        self.b_nghe_mau = QPushButton("Nghe thử mẫu")
        self.b_nghe_mau.setToolTip(
            "Phát THẲNG file mẫu vừa chọn — để chắc anh chọn đúng file.\n"
            "Không nạp model nên nghe được ngay.")
        self.b_nghe_mau.clicked.connect(self._nghe_mau)
        h2.addWidget(self.b_nghe_mau)
        self.b_luu = QPushButton("Lưu giọng này")
        self.b_luu.clicked.connect(self._luu)
        h2.addWidget(self.b_luu)
        lay.addLayout(h2)

        # ---- hàng SỬA GIỌNG ĐÃ LƯU ----
        h3 = QHBoxLayout()
        self.b_nghe_giong = QPushButton("Nghe thử giọng")
        self.b_nghe_giong.setToolTip(
            "Đọc một câu mẫu bằng CHÍNH giọng đã lưu, đi đúng cửa mà lượt "
            "xuất thật đi.\nLượt đầu mất khoảng 40 giây vì phải nạp model "
            "(đo thật) — đừng bấm lại, nút sẽ tự mở khi xong.")
        self.b_nghe_giong.clicked.connect(self._nghe_giong)
        h3.addWidget(self.b_nghe_giong)
        self.b_doi_ten = QPushButton("Đổi tên")
        self.b_doi_ten.setToolTip(
            "Đổi tên hiển thị. KHÔNG đụng file mẫu nên mã giọng không đổi — "
            "kênh nào đang gán giọng này vẫn đúng.")
        self.b_doi_ten.clicked.connect(self._doi_ten)
        h3.addWidget(self.b_doi_ten)
        self.b_xoa = QPushButton("Xoá giọng")
        self.b_xoa.clicked.connect(self._xoa)
        h3.addWidget(self.b_xoa)
        h3.addStretch(1)
        b_dong = QPushButton("Đóng")
        b_dong.clicked.connect(self.accept)
        h3.addWidget(b_dong)
        lay.addLayout(h3)

        self.lb_tt = QLabel("")
        self.lb_tt.setWordWrap(True)
        lay.addWidget(self.lb_tt)

        self._nghe_xong.connect(self._nghe_giong_xong)
        self._nb_xong.connect(self._tai_nhan_ban_xong)
        # Nhịp vẽ tiến độ. CHỈ chạy trong lúc tải (`start()` ở `_tai_nhan_ban`)
        # — timer chạy suốt trong một hộp thoại là tự làm đơ máy đang chạy sản
        # xuất, và làm cổng test dựng UI phải chờ vô ích.
        self._dong_ho_nb = QTimer(self)
        self._dong_ho_nb.setInterval(700)
        self._dong_ho_nb.timeout.connect(self._nhip)
        self._nap()
        self._do_nhan_ban()

    # ------------------------------------------------------------------
    def _nap(self) -> None:
        """Đổ lại danh sách giọng đã lưu. Giữ dòng đang chọn nếu còn."""
        from app.core import nhan_ban_giong as NB
        cu = self._ten_dang_chon()
        self.ds.clear()
        so = NB._doc_so()
        for ten in sorted(so):
            it = QListWidgetItem(NB.nhan(ten))
            it.setData(Qt.ItemDataRole.UserRole, ten)
            self.ds.addItem(it)
        if not so:
            self.lb_tt.setText(
                "Chưa có giọng nào. Bấm «Chọn file mẫu...», đặt tên, rồi "
                "«Lưu giọng này».")
        for i in range(self.ds.count()):
            if self.ds.item(i).data(Qt.ItemDataRole.UserRole) == cu:
                self.ds.setCurrentRow(i)
                break
        # MẤT FILE MẪU thì BÁO, KHÔNG tự xoá khỏi sổ: mẫu có thể chỉ tạm không
        # thấy (ổ ngoài chưa cắm), mà tự xoá là mất luôn cấu hình kênh đang
        # trỏ vào nó. Cùng luật `_canh_bao_mau_mat` của mẫu-theo-kênh.
        mat = NB.sua_mau_mat()
        if mat:
            self.lb_tt.setText(
                "MẤT FILE MẪU của: " + ", ".join(mat[:5])
                + ". Giọng vẫn còn trong sổ (không tự xoá) nhưng chọn nó thì "
                  "app sẽ LÙI về giọng thường. Thêm lại mẫu để dùng tiếp.")

    def _ten_dang_chon(self) -> str:
        it = self.ds.currentItem()
        return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

    # ------------------------------------------------------------------
    # PHẦN NHÂN BẢN (torch + torchaudio) — dò, hiện nút, tải
    # ------------------------------------------------------------------
    def _do_nhan_ban(self) -> dict:
        """Dò phần nhân bản rồi cập nhật nhãn + nút. KHÔNG khoá gì cả.

        ═══ NÚT BÁM `thieu`, KHÔNG BÁM "chạy được" ═══
        Đây là **chính cái bẫy đã đẻ ra việc này**, và nó đã sập hai lần rồi
        (cổng 58 với `_lib` của Demucs, rồi hàng Kokoro). Bám cờ "máy này chạy
        được không" thì trên máy dev — nơi `_giong_vieneu/venv` ĐÃ có torch —
        nút **BIẾN MẤT**, không ai bấm thử, và bản `.exe` của anh Hùng (venv ở
        `%LOCALAPPDATA%` KHÔNG có torch) **mãi mãi thiếu**. `thieu` là câu trả
        lời của ĐÚNG cái bản `.exe` nhìn thấy, vì nó dò bằng FILE CÓ TỒN TẠI
        KHÔNG trong site-packages của đúng python đó.

        Thiếu phần này chỉ LÙI ÊM về giọng thường nên **KHÔNG khoá nút nào** —
        khác Demucs (thiếu là CHẶN, vì lùi ra video HỎNG).

        ═══ BỘ DÒ HỎNG THÌ NGHIÊNG VỀ **HIỆN NÚT**, và đó là quyết định ═══
        Hộp này KHÔNG được chết vì một lượt dò hỏng (ổ mạng rút, `config` lạ).
        Nhưng hướng lùi phải chọn đúng: **ẩn nút** là chính cái đã giết tính
        năng một lần, nên hỏng thì vẫn HIỆN + bấm được, và nói ra là chưa dò
        được. `cai_nhan_ban()` không bao giờ ném nên bấm vào cũng chỉ ra một
        lời lỗi đọc được, còn ẩn đi thì người dùng không còn đường nào.
        """
        try:
            tt = VN_C.tinh_trang_nhan_ban()
        except Exception as e:  # noqa: BLE001 - dò hỏng KHÔNG được giết hộp
            tt = {"thieu": ["không dò được"], "co": False, "cai_duoc": True,
                  "vi_sao": f"Chưa dò được phần nhân bản ({type(e).__name__}: "
                            f"{e}) — bấm thử vẫn được, app sẽ báo lý do rõ.",
                  "nhan": "Tải phần nhân bản giọng", "mb_tai": 0.0,
                  "cuda": False, "python": "", "thu_muc": ""}
        self._tt_nb = tt
        thieu = list(tt.get("thieu") or [])
        if not thieu:
            self.lb_nb.setText(
                "Phần nhân bản giọng: ĐÃ CÓ (torch, torchaudio). Giọng nhân "
                "bản trong danh sách trên đọc được ngay.")
            self.lb_nb.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai_nb.setVisible(False)
            self.pb_nb.setVisible(False)
            return tt
        # Nói ĐÍCH DANH gói còn thiếu — "chưa cài" trơn thì người dùng không
        # biết bấm gì (bài học cổng 58: hộp Demucs phải nêu tên từng gói).
        self.lb_nb.setText(
            "Phần nhân bản giọng: CHƯA CHẠY ĐƯỢC — thiếu "
            + ", ".join(thieu[:4]) + ("..." if len(thieu) > 4 else "")
            + ".\n20 giọng VieNeu dựng sẵn VẪN chạy (chúng không cần torch); "
              "chỉ giọng nhân bản của anh là chưa. Chọn nó bây giờ thì app đọc "
              "bằng giọng thường."
            + (("\n" + str(tt.get("vi_sao") or "")) if tt.get("vi_sao") else ""))
        self.lb_nb.setStyleSheet("color:#B0B0B0; font-size:11px;")
        self.b_tai_nb.setVisible(True)
        # Nhãn đọc lại MỖI LẦN DÒ: ca CÀI DỞ (còn 1 trong 2 sau lượt đứt mạng)
        # phải trông KHÁC ca chưa cài lần nào, và số MB phải theo đúng bản sẽ
        # tải (cắm/rút GPU giữa phiên thì đổi theo).
        self.b_tai_nb.setText(str(tt.get("nhan") or ""))
        # Nút xám KHÔNG MỘT LỜI là câu đố (bài học cổng 58/16/51) — `vi_sao`
        # đã in ra nhãn ở trên, nên ở đây chỉ cần khoá.
        self.b_tai_nb.setEnabled(
            bool(tt.get("cai_duoc")) and not self._dang_cai_nb)
        self.b_tai_nb.setToolTip(
            "Tải "
            + ", ".join(thieu[:4])
            + f" vào môi trường Python RIÊNG của VieNeu:\n{tt.get('thu_muc')}"
            + "\n\nKHÔNG cài vào môi trường app đang chạy."
            + f"\nLượng tải đo thật: khoảng {self._mb_nb()} MB."
            + (("\n\n" + str(tt.get("vi_sao") or "")) if tt.get("vi_sao")
               else ""))
        return tt

    def _mb_nb(self) -> str:
        """Số MB cho nhãn/tooltip/hộp xác nhận — MỘT phép đo, ba chỗ đọc.

        Chép tay ba chỗ là đúng lỗi cổng 58: nút ghi 155 MB rồi hộp xác nhận
        doạ 2 GB, hai con số cho cùng một lượt tải.

        Định dạng đi qua `VN_C.so_mb()` — CÙNG hàm với nhãn nút, nên dấu nghìn
        không thể lệch nhau giữa ba chỗ.
        """
        try:
            return VN_C.so_mb(VN_C.mb_nhan_ban())
        except Exception:  # noqa: BLE001
            return "?"

    def _tai_nhan_ban(self) -> None:
        """NGƯỜI DÙNG BẤM thì mới tải — app không tải 2,5 GB sau lưng."""
        if self._dang_cai_nb:
            return
        tt = getattr(self, "_tt_nb", None) or VN_C.tinh_trang_nhan_ban()
        if not tt.get("cai_duoc"):
            QMessageBox.information(
                self, "Chưa tải được",
                str(tt.get("vi_sao")
                    or "Máy này chưa cài được phần nhân bản."))
            return
        thieu = ", ".join(list(tt.get("thieu") or [])[:4])
        if QMessageBox.question(
                self, "Tải phần nhân bản giọng",
                f"Sẽ tải khoảng {self._mb_nb()} MB ({thieu}) vào môi trường "
                "Python RIÊNG của VieNeu:\n"
                + str(tt.get("thu_muc", ""))
                + "\n\nKHÔNG cài vào môi trường app đang chạy.\n"
                + ("Máy có GPU NVIDIA nên lấy bản CUDA — CHƯA ĐO là nó có "
                   "nhanh hơn bản CPU hay không.\n" if tt.get("cuda") else "")
                + "\nTải bây giờ?"
                ) != QMessageBox.StandardButton.Yes:
            return
        self._dang_cai_nb = True
        self.b_tai_nb.setEnabled(False)
        self.b_tai_nb.setText("Đang tải...")
        self.pb_nb.setVisible(True)
        self.pb_nb.setValue(1)
        # KHUÔN HÀNG DEMUCS/KOKORO: thread nền chỉ ghi vào một dict THƯỜNG,
        # `_nhip` (timer của luồng UI) mới đọc ra và vẽ. **KHÔNG đụng widget từ
        # thread nền** — luật `shutdown.safe_emit` của cả repo (gốc: 8 lần
        # crash 0xc0000005). Dict RIÊNG chứ không dùng chung với lượt tải khác:
        # hai tiến trình pip song song thì ghi lẫn số của nhau.
        buoc = {"p": 0.0, "m": "Đang tải..."}
        self._buoc_nhan_ban = buoc
        self._dong_ho_nb.start()

        def bg() -> None:
            try:
                r = VN_C.cai_nhan_ban(
                    on_progress=lambda p, m: buoc.update({"p": p, "m": m}))
                ok, loi = bool(r.get("ok")), str(r.get("loi") or "")[:400]
            except Exception as e:  # noqa: BLE001 - thread nền KHÔNG được chết
                ok, loi = False, f"{type(e).__name__}: {e}"[:400]
            self._nb_xong.emit(ok, loi)

        threading.Thread(target=bg, daemon=True).start()

    def _nhip(self) -> None:
        """Vẽ tiến độ. Chạy ở LUỒNG GIAO DIỆN (timer) nên đụng widget mới an
        toàn. Không có nhánh này thì thanh đứng im ở 1% suốt vài phút — đúng
        cái anh Hùng đã kêu ở hộp bên ("chỉ hiện thanh tiến trình, không hiện
        gì cả")."""
        if not self._dang_cai_nb:
            return
        b = getattr(self, "_buoc_nhan_ban", {"p": 0.0, "m": ""})
        self.pb_nb.setValue(int(max(1, min(100, float(b.get("p") or 0) * 100))))
        self.lb_tt.setText(str(b.get("m") or "")[:150])

    def _tai_nhan_ban_xong(self, ok: bool, loi: str) -> None:
        self._dang_cai_nb = False
        self._dong_ho_nb.stop()
        self.pb_nb.setVisible(False)
        self.b_tai_nb.setEnabled(True)
        # MỪNG THEO `thieu`, KHÔNG THEO `ok` của pip: pip trả mã 0 mà gói vẫn
        # nằm ngoài môi trường đích là chuyện ĐÃ xảy ra thật (cổng 58).
        tt = self._do_nhan_ban()
        # Dòng giọng trong danh sách mang tiền tố "CHƯA CHẠY ĐƯỢC" -> nạp lại
        # để nó biến đi. **CỐ Ý KHÔNG gọi `_dung_combo_giong` của hộp cha**:
        # hàm đó đặt lại combo theo giá trị ĐÃ LƯU nên nuốt mất lựa chọn user
        # vừa bấm mà chưa lưu — đúng họ lỗi "chọn X ra Y" mà `_tai_gh_xong` và
        # `_tai_kokoro_xong` đã ghi rõ vì sao chúng không làm.
        self._nap()
        if ok and not tt.get("thieu"):
            QMessageBox.information(
                self, "Xong",
                "Đã cài xong phần nhân bản giọng.\n"
                + str(tt.get("thu_muc", ""))
                + "\n\nGiọng nhân bản của anh đọc được ngay bây giờ — bấm "
                  "«Nghe thử giọng» để kiểm.")
        else:
            QMessageBox.warning(
                self, "Chưa xong",
                "Chưa cài xong phần nhân bản giọng.\n"
                + ("Còn thiếu: " + ", ".join(list(tt.get("thieu") or [])[:4])
                   if tt.get("thieu") else "")
                + (("\n\n" + loi) if loi else "")
                + "\n\nApp vẫn chạy bình thường: 20 giọng VieNeu dựng sẵn "
                  "không cần phần này, và giọng nhân bản sẽ đọc bằng giọng "
                  "thường. Bấm lại để cài tiếp phần còn thiếu.\n"
                  "Chi tiết ở logs/giong_vieneu_<ngày>.log")

    # ------------------------------------------------------------------
    def _chon_mau(self) -> None:
        p, _ = QFileDialog.getOpenFileName(
            self, "Chọn file mẫu giọng", "",
            "Tiếng và video (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus "
            "*.mp4 *.mkv *.mov);;Tất cả (*.*)")
        if not p:
            return
        from app.core import nhan_ban_giong as NB
        self._mau = p
        kt = NB.kiem_mau(p)
        self.lb_mau.setText(Path(p).name)
        if not kt.get("ok"):
            # MẪU HỎNG THÌ BÁO TỬ TẾ, đừng để tới lúc xuất 30 video mới biết.
            self.lb_tt.setText("MẪU KHÔNG DÙNG ĐƯỢC: " + (kt.get("loi") or ""))
            self.lb_mau.setText(Path(p).name + "  — KHÔNG DÙNG ĐƯỢC")
            return
        cb = "  ".join(kt.get("canh_bao") or [])
        self.lb_tt.setText(
            f"Mẫu dài {kt['giay']:.1f} giây · "
            f"{100 * kt['ty_le_tieng']:.0f}% thời lượng có tiếng"
            + (("  |  LƯU Ý: " + cb) if cb else ""))

    def _nghe_mau(self) -> None:
        """Phát THẲNG file mẫu. Đổi sang wav trước vì `winsound` chỉ nhận wav."""
        if not self._mau or not Path(self._mau).is_file():
            QMessageBox.information(
                self, "Nghe thử mẫu",
                "Chưa chọn file mẫu. Bấm «Chọn file mẫu...» trước.")
            return
        import subprocess
        import tempfile
        import uuid
        from config import settings as _st
        w = Path(tempfile.gettempdir()) / f"_bqmau_{uuid.uuid4().hex[:8]}.wav"
        try:
            r = subprocess.run(
                [_st.FFMPEG_PATH, "-y", "-v", "error", "-i", self._mau,
                 "-vn", "-ac", "1", "-ar", "24000", str(w)],
                capture_output=True, timeout=300,
                creationflags=(0x08000000 if os.name == "nt" else 0))
            # ffmpeg TRẢ MÃ 0 MÀ FILE RỖNG là chuyện đã xảy ra nhiều lần trong
            # repo này -> kiểm KÍCH THƯỚC, đừng tin mã thoát.
            if r.returncode != 0 or not w.exists() or w.stat().st_size < 1024:
                raise OSError("ffmpeg không đọc được file mẫu")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Nghe thử mẫu",
                                f"Không phát được file mẫu này:\n{e}")
            return
        self._phat(str(w))

    def _nghe_giong(self) -> None:
        """NHÂN BẢN THẬT qua `thay_giong.doc_thu` — đúng cửa lượt xuất đi.

        **KHÔNG gọi thẳng `dubbing._synth_all_words`**: cổng 63 đếm ĐÚNG 3 chỗ
        gọi hàm đó và sẽ ĐỎ nếu mọc thêm chỗ thứ 4 (bản đầu của nút nghe thử ở
        cổng 65 đã sập đúng vậy). Đi cửa trên còn được thêm: tự tách `pitch`,
        tự cắt lề im, và tự NÓI RA khi app lùi về giọng thường.
        """
        import threading
        ten = self._ten_dang_chon()
        if not ten:
            QMessageBox.information(
                self, "Nghe thử giọng",
                "Chọn một giọng trong danh sách trước đã.")
            return
        from app.core import nhan_ban_giong as NB
        ma = NB.ma_giong(ten)
        if not ma:
            QMessageBox.warning(
                self, "Nghe thử giọng",
                f"Giọng «{ten}» không dùng được — file mẫu của nó không còn "
                f"trên đĩa. Thêm lại mẫu rồi thử lại.")
            return
        self._ngat_tieng()
        self.b_nghe_giong.setEnabled(False)
        self.b_nghe_giong.setText("Đang đọc...")
        self.lb_tt.setText(
            "Đang nhân bản giọng — lượt đầu mất khoảng 40 giây vì phải nạp "
            "model. Không phải app treo.")
        import tempfile
        import uuid
        wav = str(Path(tempfile.gettempdir())
                  / f"_bqtoi_{uuid.uuid4().hex[:8]}.wav")

        def bg() -> None:
            try:
                from app.core import thay_giong as TGC
                kq = TGC.doc_thu(ma, wav, nn="vi")
                self._nghe_xong.emit(kq.get("ra") or "", kq.get("nguon") or "",
                                     kq.get("loi") or "",
                                     kq.get("canh_bao") or "")
            except Exception as e:  # noqa: BLE001
                self._nghe_xong.emit("", "", str(e), "")

        threading.Thread(target=bg, daemon=True).start()

    def _nghe_giong_xong(self, wav: str, nguon: str, loi: str,
                         canh_bao: str = "") -> None:
        """Chạy ở LUỒNG GIAO DIỆN (qua tín hiệu) -> đụng widget mới an toàn."""
        self.b_nghe_giong.setEnabled(True)
        self.b_nghe_giong.setText("Nghe thử giọng")
        if loi or not wav or not Path(wav).exists():
            QMessageBox.warning(
                self, "Nghe thử giọng không được",
                f"Không đọc thử được giọng này.\n\nLý do: {loi or 'không rõ'}"
                "\n\nGiọng nhân bản cần bộ VieNeu ĐÃ TẢI và có torch — xem "
                "dòng «CHƯA CHẠY ĐƯỢC» trong danh sách.")
            return
        # NGUỒN THẬT, không phải cái vừa chọn: thiếu model thì app LÙI ÊM về
        # edge-tts, không nói ra thì anh Hùng tưởng đang nghe giọng của mình
        # rồi gán nó cho 300 kênh.
        self.lb_tt.setText(
            f"Nghe thử: nguồn THẬT = {nguon or 'không rõ'}"
            + (f"  |  LƯU Ý: {canh_bao}" if canh_bao else ""))
        self._phat(wav)

    def _phat(self, wav: str) -> None:
        try:
            import winsound
            winsound.PlaySound(
                wav, winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Không phát được",
                                f"Máy này không phát được âm thanh:\n{e}")

    def _ngat_tieng(self) -> None:
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def _luu(self) -> None:
        from app.core import nhan_ban_giong as NB
        ten = self.o_ten.text().strip()
        if not ten:
            QMessageBox.information(self, "Lưu giọng",
                                    "Đặt tên cho giọng trước đã.")
            return
        if not self._mau:
            QMessageBox.information(self, "Lưu giọng",
                                    "Chọn file mẫu trước đã.")
            return
        r = NB.them_giong(ten, self._mau, lang="vi",
                          nguon="anh Hùng tự khai qua hộp Giọng của tôi")
        if not r.get("ok"):
            QMessageBox.warning(self, "Không lưu được",
                                str(r.get("loi") or "không rõ lý do"))
            return
        cb = "  ".join(r.get("canh_bao") or [])
        self.o_ten.clear()
        self._mau = ""
        self.lb_mau.setText("(chưa chọn file mẫu)")
        self._nap()
        self.lb_tt.setText(
            f"Đã lưu giọng «{ten}». Nó có trong ô Giọng đọc ngay bây giờ."
            + (("  |  LƯU Ý: " + cb) if cb else ""))
        self.so_doi.emit()

    def _doi_ten(self) -> None:
        from app.core import nhan_ban_giong as NB
        cu = self._ten_dang_chon()
        if not cu:
            QMessageBox.information(self, "Đổi tên",
                                    "Chọn một giọng trong danh sách trước đã.")
            return
        moi = self.o_ten.text().strip()
        if not moi:
            QMessageBox.information(
                self, "Đổi tên",
                f"Gõ TÊN MỚI vào ô «Tên giọng» rồi bấm Đổi tên.\n\n"
                f"Đang chọn: {cu}")
            return
        if not NB.doi_ten(cu, moi):
            QMessageBox.warning(
                self, "Không đổi được tên",
                f"Không đổi được «{cu}» thành «{moi}» — có thể tên mới đã "
                f"có rồi.")
            return
        self.o_ten.clear()
        self._nap()
        self.lb_tt.setText(f"Đã đổi tên «{cu}» thành «{moi}».")
        self.so_doi.emit()

    def _xoa(self) -> None:
        from app.core import nhan_ban_giong as NB
        ten = self._ten_dang_chon()
        if not ten:
            QMessageBox.information(self, "Xoá giọng",
                                    "Chọn một giọng trong danh sách trước đã.")
            return
        # Nút MẶC ĐỊNH là KHÔNG: bấm Enter theo phản xạ thì không mất giọng.
        h = QMessageBox(self)
        h.setWindowTitle("Xoá giọng")
        h.setText(f"Xoá giọng «{ten}» khỏi danh sách?\n\n"
                  f"App sẽ xoá luôn FILE MẪU mà nó đã chép vào thư mục dữ "
                  f"liệu. File gốc của anh KHÔNG bị đụng.\n\n"
                  f"Kênh nào đang gán giọng này sẽ lùi về giọng thường.")
        h.setStandardButtons(QMessageBox.StandardButton.Yes
                             | QMessageBox.StandardButton.No)
        h.setDefaultButton(QMessageBox.StandardButton.No)
        if h.exec() != QMessageBox.StandardButton.Yes:
            return
        if not NB.xoa(ten):
            QMessageBox.warning(self, "Không xoá được",
                                f"Không ghi được sổ giọng nên «{ten}» vẫn còn.")
            return
        self._nap()
        self.lb_tt.setText(f"Đã xoá giọng «{ten}».")
        self.so_doi.emit()


class ThayGiongDialog(QDialog):
    """Chọn thư mục vào/ra · ngôn ngữ · giọng · số luồng -> xếp job, xem tiến
    độ TỪNG VIDEO, chuột phải để làm lại."""

    _giong_xong = pyqtSignal()          # danh sách giọng nạp xong (thread nền)
    _cai_xong = pyqtSignal(bool, str)   # tải bộ tách giọng xong (ok, lời)
    _piper_xong = pyqtSignal(bool, str)  # tải giọng Piper xong (ok, lời)
    _kokoro_xong = pyqtSignal(bool, str)  # tải giọng Kokoro xong (ok, lời)
    _gh_xong = pyqtSignal(bool, str)    # tải bộ gióng hàng xong (ok, lời)
    #: (đường dẫn wav, nguồn giọng THẬT, lời lỗi, CẢNH BÁO) — nghe thử sinh
    #: xong ở thread nền. Phải qua tín hiệu: đụng widget từ thread nền là sập
    #: app. `canh_bao` là vế thứ tư THÊM 19/08/2026: giọng chỉ đọc được tiếng
    #: Việt mà ngôn ngữ đích là tiếng Anh thì tiếng ra NGHE LẠ, và anh Hùng
    #: kết luận "giọng hỏng". `doc_thu` biết điều đó nhưng trước đây không có
    #: đường nào nói lên giao diện.
    _nghe_xong = pyqtSignal(str, str, str, str)
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
        self._dang_cai_kokoro = False
        self._tt_piper: dict = {}
        self._tt_kokoro: dict = {}
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
        # VIỆC 4 — 392 mã giọng thì cuộn tay là không dùng được. Bấm combo mở
        # popup [ô tìm + danh sách] (`_mo_chon_giong`), đúng mẫu đã chạy được
        # của `studio_page._open_chan_picker`.
        self.cb_giong = ComboGiong()
        self.cb_giong.setMinimumWidth(300)
        # Đường LÙI (picker ném lỗi -> popup Qt mặc định) chỉ hiện 10 dòng, vô
        # dụng với 364 giọng. Không sửa được "bảng nhỏ" ở đường chính mà bỏ
        # đường lùi thì vẫn còn một cửa bày ra bảng nhỏ.
        self.cb_giong.setMaxVisibleItems(GP_SO_DONG_COMBO)
        self.cb_giong.setToolTip(
            "Bấm để mở danh sách giọng — có Ô TÌM và HÀNG NÚT LỌC ở trên.\n"
            "Gõ tên giọng là tìm trên MỌI nhóm (gõ không dấu cũng ra); bấm nút "
            "lọc để thu theo tiếng · giới · tiền · chỗ chạy.\n"
            "Ô tìm và nút lọc CỘNG DỒN với nhau, và dòng ngay trên danh sách "
            "luôn ghi đang hiện bao nhiêu trên tổng bao nhiêu.")
        self.cb_giong.addItem(NHAN_GIONG_TU, "")
        self.cb_giong.picker = self._mo_chon_giong
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

        # GIỌNG CỦA ANH HÙNG — cửa vào hộp nhân bản. Đặt NGAY CẠNH ô Giọng đọc
        # chứ không nhét vào menu: đây là thứ anh Hùng hỏi đích danh, mà mọi
        # tính năng phải-đi-tìm-mới-thấy thì coi như không tồn tại (đúng ca
        # `nhan_ban_giong` vừa nằm chết 564 dòng vì không có nút nào).
        # Nhãn KHÔNG EMOJI + NGẮN (cổng 84: hàng này đã sát mép).
        self.b_giong_toi = QPushButton("Giọng của tôi...")
        self.b_giong_toi.setToolTip(
            "Đưa vào một file tiếng của anh (5-30 giây, một người nói) — app "
            "tạo một giọng mới đọc bằng chất giọng đó.\n"
            "Lưu lại được, thêm được nhiều giọng, và mẫu được CHÉP vào thư "
            "mục dữ liệu nên xoá file gốc thì giọng vẫn chạy.\n"
            "CHỈ dùng giọng anh có quyền — xem lời nhắc trong hộp.")
        self.b_giong_toi.clicked.connect(self._mo_giong_toi)
        h2.addWidget(self.b_giong_toi)

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

        # ---- hàng 3bc: CÁCH TRỘN TIẾNG (đè giọng / thay hẳn giọng) ----
        # Anh Hùng 19/08/2026: *"thêm tính năng KHÔNG tách nhạc nền, chỉ GIẢM
        # tiếng video gốc rồi ĐÈ giọng lồng tiếng vào, để không bị mất mấy tiếng
        # của video"*.
        # MỤC ĐẦU LÀ CÁCH CŨ — CÓ CHỦ Ý, và đây là quyết định quan trọng nhất
        # của cả ô này: đổi mặc định là đổi tiếng của MỌI video từ nay trên
        # 200-300 kênh đang chạy sản xuất. Anh Hùng phải nghe THỬ CẢ HAI rồi mới
        # duyệt cái nào làm mặc định.
        # NHÃN NÓI RÕ ĐÁNH ĐỔI CỦA CẢ HAI BÊN, không khoe một bên: ô chọn chỉ
        # khoe cái được thì đó không phải một lựa chọn có thông tin.
        h3bc = QHBoxLayout()
        h3bc.addWidget(QLabel("Cách trộn tiếng:"))
        self.cb_tron = QComboBox()
        # Nhãn lấy từ `thay_giong.NHAN_CACH_TRON` — MỘT NGUỒN DUY NHẤT, để nhật
        # ký/cổng test và cái người dùng thấy không viết tay hai lần rồi lệch.
        self.cb_tron.addItem(TG.NHAN_CACH_TRON["tach"], "tach")
        self.cb_tron.addItem(TG.NHAN_CACH_TRON["de"], "de")
        self.cb_tron.setToolTip(
            "THAY HẲN GIỌNG (tách nhạc) — cách app vẫn làm từ trước:\n"
            "  · tiếng gốc bị BỎ HẲN, chỉ còn nhạc nền + tiếng động\n"
            "  · NHƯNG cần bộ tách giọng khoảng 4,3 GB, nên có card NVIDIA,\n"
            "    và câu nào bộ chép lời bỏ qua thì thành khoảng TRỐNG — đo\n"
            "    ghép cặp trên video của anh: còn mất 14,75 s / 1,62%.\n\n"
            "ĐÈ GIỌNG (không tách) — cách mới:\n"
            "  · giữ NGUYÊN tiếng gốc, chỉ hạ nó xuống rồi đè giọng lồng lên\n"
            "  · KHÔNG mất tiếng chỗ nào (không bỏ gì thì không mất gì), KHÔNG\n"
            "    cần tải bộ tách giọng, KHÔNG cần card, và nhanh hơn hẳn vì bỏ\n"
            "    được cả bước tách\n"
            "  · ĐÁNH ĐỔI: tiếng gốc VẪN NGHE ĐƯỢC ở dưới giọng lồng.\n\n"
            "Nhạc/tiếng gốc chỉ bị hạ ĐÚNG LÚC giọng lồng đang nói (ducking), "
            "không hạ đều cả bài.")
        _it = self.cb_tron.findData(
            TG.chuan_cach_tron(self._s.value(K_TRON_CACH, "tach")))
        self.cb_tron.setCurrentIndex(max(0, _it))
        h3bc.addWidget(self.cb_tron)
        h3bc.addStretch(1)
        lay.addLayout(h3bc)
        # Đổi cách trộn -> phải tính lại nút Chạy NGAY: cách "đè" không dùng bộ
        # tách giọng nên nó chạy được trên máy CHƯA có Demucs. Không nối tín
        # hiệu này thì user chọn "đè giọng" mà nút Chạy vẫn xám = tính năng
        # KHÔNG với tới được đúng cái máy nó được làm ra để phục vụ.
        self.cb_tron.currentIndexChanged.connect(
            lambda *_: self._cap_nhat_nut_chay())

        # ---- hàng 3bd: HAI Ô ÂM LƯỢNG (dB) ----
        # Anh Hùng 20/08/2026: *"cái phần âm thanh gốc nó nói bé k tuỳ chỉnh âm
        # thanh đc à chứ to quá"*. Tới v2.41.1 hộp này KHÔNG có một điều khiển
        # âm lượng nào (`grep -c "muc_giong_db\|slider" ` = 0): app đo rồi tự
        # quyết bằng `DICH_GIONG_TREN_NHAC_DB` = 6 và `HA_NHAC_TOI_DA_DB` = 8.
        # Phép đo đúng cho ca trung bình, nhưng "muốn nghe tiếng gốc nhiều hay
        # ít" là LỰA CHỌN, không phải phép đo — app không có quyền quyết hộ.
        #
        # DÙNG SPIN BOX, KHÔNG SLIDER — ba lý do, không phải sở thích:
        #   · hộp này đã có 4 spin/9 combo, thêm slider là bộ điều khiển thứ ba
        #     cho cùng một loại việc (đúng chỗ cổng 86 mục 8k đang canh);
        #   · dB là con số anh Hùng cần ĐỌC ĐƯỢC rồi nói lại cho tôi, slider
        #     không hiện số;
        #   · slider chỉ bị wheelguard khoá KHI CHƯA focus, còn QComboBox/
        #     QAbstractSpinBox bị khoá HẲN (xem `wheelguard._WheelGuard`) — mà
        #     việc #150 là "khoá cuộn chuột đổi giá trị" cho toàn app.
        # `QDoubleSpinBox` là ĐÚNG lớp `sp_che_muc`/`sp_kc_co`/`sp_kc_dovien`
        # đang dùng và nằm trong `_VALUE_WIDGETS` của bộ lọc cài trên
        # QApplication (`main.py` + `main_window.py`), nên KHÔNG phải widget
        # trần: cuộn chuột lên nó không đổi giá trị.
        h3bd = QHBoxLayout()
        h3bd.addWidget(QLabel("Tiếng gốc / nhạc nền:"))
        self.sp_muc_nen = self._o_dB(
            K_MUC_NEN,
            "Cộng thêm bấy nhiêu dB vào LỚP NỀN — tức nhạc nền (cách 'thay "
            "hẳn giọng') hoặc CẢ TIẾNG GỐC (cách 'đè giọng').\n\n"
            "0,0 dB = MẶC ĐỊNH: app tự đo rồi tự quyết, y như mọi bản trước.\n"
            "Số DƯƠNG = nghe rõ tiếng gốc hơn (đúng cái anh đang cần). Số ÂM = "
            "dìm tiếng gốc xuống cho lời lồng nổi hơn.\n\n"
            "Đo thật: app đang tự hạ nền tối đa 8,0 dB, nên +6 chỉ là trả nền "
            "về gần mức GỐC của nó, không đẩy vượt bản gốc.\n"
            "LƯU Ý: kéo dương nhiều thì giọng lồng chìm dần — trên +3 dB là bắt "
            "đầu đi về phía bệnh 'chỗ có chỗ không nghe không được'.\n"
            "Độ to CẢ VIDEO không đổi (app vẫn chuẩn hoá về -14 LUFS ở bước "
            "cuối) — hai ô này chỉ đổi TỈ LỆ giữa lời lồng và nền.")
        h3bd.addWidget(self.sp_muc_nen)

        h3bd.addSpacing(8)
        h3bd.addWidget(QLabel("Giọng lồng tiếng:"))
        self.sp_muc_giong = self._o_dB(
            K_MUC_GIONG,
            "Cộng thêm bấy nhiêu dB vào GIỌNG LỒNG TIẾNG (giọng máy đọc bản "
            "dịch).\n\n"
            "0,0 dB = MẶC ĐỊNH: app tự đo rồi tự quyết, y như mọi bản trước.\n"
            "Số ÂM = hạ lời lồng xuống cho tiếng gốc nghe rõ hơn. Số DƯƠNG = "
            "lời lồng nổi hơn.\n\n"
            "TRẦN AN TOÀN: phần TĂNG bị chặn theo ĐỈNH ĐO ĐƯỢC của chính lớp "
            "giọng (không vượt -1,0 dBFS). Trên mức đó thì bộ hạn đỉnh phải gọt "
            "NGAY TRÊN TIẾNG NÓI — đã đo một lần: nâng quá tay làm số mẫu chạm "
            "trần nhảy từ 36 lên 1.577. App tự dừng ở trần và ghi vào nhật ký, "
            "KHÔNG đổi tiếng lấy con số.\n"
            "Muốn lời lồng nổi hơn mà đã chạm trần: hạ ô 'Tiếng gốc / nhạc "
            "nền' xuống, hiệu quả y hệt mà không gọt tiếng.")
        h3bd.addWidget(self.sp_muc_giong)

        h3bd.addSpacing(8)
        #: Nhãn NÓI RA số hiện tại + đâu là mặc định. Spin box tự hiện số của
        #: nó, nhưng "0,0 nghĩa là gì" thì không — gập/đọc nhanh mà không có
        #: dòng này là anh Hùng phải đoán (đúng bài học nhãn "(mẫu đang chọn)"
        #: trơn ở cổng 16 v2.6.25a: thiếu chữ là user hiểu ngược).
        self.lb_muc_tt = QLabel("")
        self.lb_muc_tt.setWordWrap(True)
        h3bd.addWidget(self.lb_muc_tt, 1)
        lay.addLayout(h3bd)
        for _o in (self.sp_muc_nen, self.sp_muc_giong):
            _o.valueChanged.connect(lambda *_: self._ve_tt_muc())
        self._ve_tt_muc()

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

        # ---- hàng 4b2: GIỌNG KOKORO (28 giọng, Apache 2.0) ----
        # CÙNG LUẬT hàng Piper, KHÁC hàng Demucs: thiếu Kokoro chỉ là LÙI ÊM về
        # edge-tts (video vẫn đúng, chỉ khác giọng) nên hàng này **KHÔNG khoá
        # nút Chạy**. Thiếu Demucs mới phải chặn, vì lùi ra video HỎNG.
        #
        # Trước hôm nay: `giong_kokoro.cai_kokoro()` viết xong đủ mọi chốt mà
        # **không có một nút nào bấm được nó** — 28 dòng giọng nằm trong combo
        # sẽ lặng lẽ đọc bằng edge-tts trên mọi máy chưa tải. Nút này là chỗ duy
        # nhất người dùng bắt đầu được.
        h4b2 = QHBoxLayout()
        self.lb_kokoro = QLabel("")
        self.lb_kokoro.setWordWrap(True)
        h4b2.addWidget(self.lb_kokoro, 1)
        self.b_tai_kokoro = QPushButton(KK.NHAN_TAI)
        # DUNG LƯỢNG LÀ SỐ ĐO (bài học cổng 58: nhãn Demucs từng ghi "khoảng
        # 2 GB" trong khi lượng tải thật 154 MB — gấp 13 lần, và bấm nút ghi
        # 155 MB rồi bị hộp doạ 2 GB). Số 538 MB ở đây do `mb_se_tai()` đo bằng
        # `pip install --dry-run --report` (KHÔNG tải thật) — đo lại được:
        # `nhan_tai()` và `mb_se_tai()` đọc CÙNG một phép đo, không phải hai
        # con số chép tay cạnh nhau.
        self.b_tai_kokoro.setToolTip(
            "Tải bộ giọng Kokoro (28 giọng, 8 thứ tiếng) về môi trường "
            "Python RIÊNG.\n"
            "Đo thật bằng pip --dry-run: khoảng 538 MB tải về.\n"
            "KHÔNG cài vào .venv đang chạy sản xuất.\n"
            "Giấy phép Apache 2.0 — dùng thương mại được.\n"
            "KHÔNG có tiếng Việt và KHÔNG có mốc từng chữ (cần bộ gióng "
            "hàng).\n"
            "Chỉ tải khi BẠN bấm — app không bao giờ tự tải sau lưng.")
        self.b_tai_kokoro.clicked.connect(self._tai_kokoro)
        h4b2.addWidget(self.b_tai_kokoro)
        lay.addLayout(h4b2)
        self._do_kokoro()

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
        self._kokoro_xong.connect(self._tai_kokoro_xong)
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
    # GIỌNG CỦA ANH HÙNG (nhân bản từ mẫu)
    # ------------------------------------------------------------------
    def _mo_giong_toi(self) -> None:
        """Mở hộp nhân bản; sổ đổi thì dựng lại combo NGAY.

        `giu_dang_chon=True` là chốt chống lỗi "chọn X ra Y": người dùng vừa
        lưu một giọng nhưng CHƯA bấm Chạy, nên QSettings còn là giọng CŨ. Dựng
        lại combo theo setting là **nuốt mất lựa chọn đang hiện** — đúng lỗi
        thật của cổng 55 (combo dựng sau thread nền ghi đè giọng user bằng "").
        """
        h = HopGiongToi(self)
        h.so_doi.connect(lambda: self._dung_combo_giong(giu_dang_chon=True))
        h.exec()
        self._ngat_tieng()               # hộp con có thể còn đang phát tiếng

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

        # NGÔN NGỮ ĐÍCH lấy từ **WIDGET ĐANG HIỆN**, không lấy từ QSettings:
        # hộp chỉ ghi cài đặt lúc Chạy/đóng nên setting là lựa chọn CŨ (đúng
        # lỗi "chạy dây chuyền lấy nhóm từ setting nên chạy sai nhóm").
        nn = str(self.cb_nn.currentData() or "")

        def bg() -> None:
            try:
                from app.core import thay_giong as TGC
                kq = TGC.doc_thu(voice, wav, nn=nn)
                self._nghe_xong.emit(kq.get("ra") or "", kq.get("nguon") or "",
                                     kq.get("loi") or "",
                                     kq.get("canh_bao") or "")
            except Exception as e:  # noqa: BLE001
                self._nghe_xong.emit("", "", str(e), "")

        threading.Thread(target=bg, daemon=True).start()

    def _ngat_tieng(self) -> None:
        """Ngắt tiếng nghe thử đang kêu (nếu có). Máy không có winsound thì im."""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:  # noqa: BLE001
            pass

    def _goi_y_nghe_thu(self) -> str:
        """Câu GỢI Ý phải khớp GIỌNG ĐANG CHỌN, không phải câu chung.

        LỖI THẬT anh Hùng gặp 20/08/2026 (có ảnh): anh chọn giọng NHÂN BẢN của
        mình rồi bấm Nghe thử trong lúc phần nhân bản **đang tải 5%**, và hộp
        báo lại khuyên *"Giọng thường (edge-tts) cần MẠNG; giọng Piper cần đã
        tải về máy"* — **hai thứ chẳng liên quan gì tới giọng anh chọn**. Câu
        chung đó đẩy anh đi kiểm mạng và kiểm Piper, tức lời báo lỗi **tự tay
        gửi người đọc sang hướng sai**.

        Cùng họ bẫy cả repo này chống ("phép đo hỏng phát chứng nhận"), chỉ khác
        là ở đây thứ phát chứng nhận sai là **lời khuyên**. Xem thêm cổng 74:
        lời lỗi *"không phải JSON hợp lệ"* đúng phần NGỌN nên người đọc đi soi
        prompt trong khi bệnh ở trần token.
        """
        try:
            ma = str(self.cb_giong.currentData() or "")
        except Exception:  # noqa: BLE001
            ma = ""
        # Giọng NHÂN BẢN: nói đúng cái đang thiếu, và nói cả chuyện ĐANG TẢI —
        # thiếu vế đó thì anh Hùng bấm lại liên tục trong lúc pip còn chạy.
        if ma.startswith("vnb:"):
            try:
                from app.core import nhan_ban_giong as NB
                thieu = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
            except Exception:  # noqa: BLE001
                thieu = []
            if thieu:
                # CỐ Ý nói CẢ HAI vế (chưa bấm / đang tải) thay vì đọc cờ
                # `_dang_cai_nb` — cờ đó thuộc hộp «Giọng của tôi`, KHÔNG phải
                # hộp này, nên `getattr` ở đây luôn ra False và câu "đang tải"
                # sẽ không bao giờ hiện. Thà nói hai vế còn hơn đoán sai một vế:
                # anh Hùng gặp đúng cảnh ĐANG TẢI 5% và bấm Nghe thử.
                return ("Giọng NHÂN BẢN chưa chạy được vì còn thiếu: "
                        + ", ".join(thieu[:4]) + "."
                        + "\nMở hộp «Giọng của tôi» rồi bấm nút Tải phần nhân "
                          "bản giọng. NẾU ĐANG TẢI thì chờ thanh tiến độ xong "
                          "hẳn rồi bấm lại — đừng bấm nhiều lần."
                        + "\n\n20 giọng VieNeu dựng sẵn KHÔNG cần phần này — "
                          "chọn một giọng trong nhóm đó thì nghe thử được ngay.")
            return ("Giọng nhân bản đã đủ phần cần thiết, nên lỗi này là chuyện "
                    "KHÁC — xem logs/giong_vieneu_<ngày>.log. Kiểm cả file mẫu: "
                    "phải là audio đọc được, một người nói, không nhạc nền.")
        return ("Giọng thường (edge-tts) cần MẠNG; giọng Piper cần đã tải "
                "về máy. Kiểm rồi bấm lại.")

    def _nghe_thu_xong(self, wav: str, nguon: str, loi: str,
                       canh_bao: str = "") -> None:
        """Chạy ở LUỒNG GIAO DIỆN (qua tín hiệu) -> đụng widget mới an toàn."""
        self.b_nghe.setEnabled(True)
        self.b_nghe.setText("Nghe thử")
        if loi or not wav or not Path(wav).exists():
            QMessageBox.warning(
                self, "Nghe thử không được",
                f"Không đọc thử được giọng này.\n\nLý do: {loi or 'không rõ'}"
                "\n\n" + self._goi_y_nghe_thu())
            return
        # NGUỒN THẬT, không phải cái vừa chọn: Piper chưa tải thì app LÙI ÊM
        # về edge-tts — không nói ra thì anh Hùng tưởng đang nghe Piper.
        if canh_bao:
            # Cảnh báo NẶNG HƠN dòng nguồn nên nó thắng chỗ hiển thị: đây đúng
            # là lúc tiếng nghe ra sẽ LẠ, mà không nói thì người nghe kết luận
            # "giọng hỏng" rồi bỏ luôn một giọng dùng được.
            self.lb_tt.setText(f"Nghe thử — LƯU Ý: {canh_bao}")
        elif "lùi" in nguon:
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

    def _de_giong(self) -> bool:
        """User đang chọn ĐÈ GIỌNG (không tách) hay không.

        Đọc từ COMBO ĐANG HIỆN, không đọc QSettings — bài học "chạy dây chuyền:
        đọc combo, không đọc setting". `getattr` vì hàm này bị gọi từ
        `_do_demucs()` có thể chạy TRƯỚC lúc combo được dựng.
        """
        cb = getattr(self, "cb_tron", None)
        return cb is not None and TG.chuan_cach_tron(cb.currentData()) == "de"

    def _cap_nhat_nut_chay(self) -> None:
        # CHẾ ĐỘ ĐÈ GIỌNG KHÔNG CẦN BỘ TÁCH -> KHÔNG được khoá nút Chạy.
        # Đây là nửa còn lại của tính năng: nó được làm ra cho đúng cái máy
        # CHƯA có Demucs, mà nút Chạy vẫn xám thì user không với tới được.
        de = self._de_giong()
        co = de or bool(getattr(self, "_tt_demucs", {}).get("co"))
        co_tm = bool(self._video_trong_thu_muc())
        self.b_chay.setEnabled(co and co_tm and not self._dang_cai)
        self.b_lam_lai.setEnabled(co and co_tm and not self._dang_cai)
        if not co:
            self.b_chay.setToolTip(
                "Chưa có bộ tách giọng — bấm '" + TG.NHAN_TAI_DEMUCS
                + "' trước, HOẶC đổi ô 'Cách trộn tiếng' sang '"
                + TG.NHAN_CACH_TRON["de"] + "' (cách đó KHÔNG cần bộ tách "
                  "giọng).\nApp KHÔNG chạy cách nhẹ vì nó để lọt 86-100% "
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

    # ------------------------------------------------------------------
    # GIỌNG KOKORO — 28 GIỌNG, Apache 2.0 (không chặn gì)
    # ------------------------------------------------------------------
    def _do_kokoro(self) -> dict:
        """Dò Kokoro rồi cập nhật nhãn. KHÔNG khoá nút Chạy.

        **NÚT BÁM `thieu`, KHÔNG BÁM `co`** — đây là bài học cổng 58 và nó là
        lý do cả tính năng có thể chết âm thầm: bám `co` thì trên máy dev (mượn
        được gói của `.venv`) nút BIẾN MẤT, không ai bấm, và bản `.exe` mãi mãi
        thiếu. Ở module này `co == du_venv` do xây dựng (bước đọc chạy bằng
        python CỦA môi trường riêng nên không mượn được gì), nhưng vẫn bám
        `thieu` để nếu sau này ai đổi cách dò thì chỗ này không hỏng theo.
        """
        try:
            tt = KK.tinh_trang()
        except Exception as e:  # noqa: BLE001 - hộp thoại KHÔNG được chết vì dò
            tt = {"co": False, "thieu": [f"không dò được ({type(e).__name__})"],
                  "cai_duoc": False, "vi_sao": str(e)[:200], "thu_muc": ""}
        self._tt_kokoro = tt
        thieu = list(tt.get("thieu") or [])
        if not thieu:
            self.lb_kokoro.setText(
                f"Giọng Kokoro ({tt.get('so_giong', 0)} giọng, 8 thứ tiếng): "
                "ĐÃ CÓ. Chọn trong ô Giọng đọc để dùng.\n"
                "Lưu ý đã đo: bộ này KHÔNG có tiếng Việt, và KHÔNG tự trả mốc "
                "từng chữ — cần bộ gióng hàng ở hàng dưới thì chữ mới bám lời.")
            self.lb_kokoro.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
            self.b_tai_kokoro.setVisible(False)
        else:
            # NÊU ĐÍCH DANH gói còn thiếu (cổng 58): câu "chưa cài" trơn thì
            # không ai biết đang thiếu gì, và ca CÀI DỞ (thiếu 1 gói sau lượt
            # tải đứt mạng) trông y hệt ca chưa cài lần nào.
            vi_sao = str(tt.get("vi_sao") or "")
            self.lb_kokoro.setText(
                "Giọng Kokoro: CHƯA TẢI — chọn giọng này thì app vẫn chạy "
                "nhưng sẽ đọc bằng giọng thường (edge-tts).\n"
                "Còn thiếu: " + ", ".join(thieu[:6])
                + ("..." if len(thieu) > 6 else "")
                + ("" if tt.get("cai_duoc") else
                   "\nApp không tự tải được: "
                   + (vi_sao or "máy chưa cài Python 3 (python.org)")))
            self.lb_kokoro.setStyleSheet("color:#B0B0B0; font-size:11px;")
            self.b_tai_kokoro.setVisible(True)
            # Nhãn nút đổi theo máy: có GPU NVIDIA thì `nhan_tai()` trả bản
            # CUDA kèm chữ "CHƯA ĐO có nhanh hơn" — nói thẳng là chưa đo, đừng
            # hứa nhanh.
            try:
                self.b_tai_kokoro.setText(KK.nhan_tai())
            except Exception:  # noqa: BLE001
                self.b_tai_kokoro.setText(KK.NHAN_TAI)
            self.b_tai_kokoro.setEnabled(
                bool(tt.get("cai_duoc")) and not self._dang_cai_kokoro)
        return tt

    def _tai_kokoro(self) -> None:
        """NGƯỜI DÙNG BẤM thì mới tải — app không tự tải sau lưng.

        Hộp xác nhận phải ghi ĐÚNG con số của nút (bài học cổng 58: nút ghi
        155 MB rồi hộp doạ 2 GB). Vì vậy nó lấy số từ CHÍNH `mb_se_tai()` chứ
        không chép tay.
        """
        if self._dang_cai_kokoro:
            return
        tt = self._tt_kokoro or {}
        try:
            mb = f"{float(tt.get('mb_tai') or KK.mb_se_tai()):,.0f}".replace(
                ",", ".")
        except Exception:  # noqa: BLE001
            mb = "538"
        if QMessageBox.question(
                self, "Tải giọng Kokoro",
                f"Sẽ tải khoảng {mb} MB về môi trường Python RIÊNG:\n"
                + str(tt.get("thu_muc", ""))
                + "\n\nKHÔNG cài vào môi trường app đang chạy.\n"
                  "Kokoro theo giấy phép Apache 2.0 — dùng thương mại được.\n\n"
                  "Bộ này KHÔNG có tiếng Việt và KHÔNG tự trả mốc từng chữ.\n\n"
                  "Tải bây giờ?"
                ) != QMessageBox.StandardButton.Yes:
            return
        self._dang_cai_kokoro = True
        self.b_tai_kokoro.setEnabled(False)
        self.b_tai_kokoro.setText("Đang tải...")
        self.pb_tai.setVisible(True)
        self.pb_tai.setValue(1)
        # THEO ĐÚNG KHUÔN HÀNG DEMUCS: thread nền chỉ ghi vào một dict thường,
        # `_nhip` (timer của luồng UI) mới đọc ra và vẽ. **KHÔNG đụng widget từ
        # thread nền** — đó là luật `shutdown.safe_emit` của cả repo (gốc: 8
        # lần crash 0xc0000005 hồi 28-30/07). Dùng dict RIÊNG chứ không dùng
        # chung `_buoc_cai` của Demucs: hai lượt tải chạy song song thì hai
        # tiến trình pip ghi lẫn số của nhau.
        buoc = {"p": 0.0, "m": "Đang tải..."}
        self._buoc_kokoro = buoc

        def bg():
            try:
                r = KK.cai_kokoro(
                    on_progress=lambda p, m: buoc.update({"p": p, "m": m}))
                ok, loi = bool(r.get("ok")), str(r.get("loi") or "")[:400]
            except Exception as e:  # noqa: BLE001 - thread nền KHÔNG được chết
                ok, loi = False, f"{type(e).__name__}: {e}"[:400]
            self._kokoro_xong.emit(ok, loi)

        threading.Thread(target=bg, daemon=True).start()

    def _tai_kokoro_xong(self, ok: bool, loi: str) -> None:
        self._dang_cai_kokoro = False
        self.pb_tai.setVisible(False)
        self.b_tai_kokoro.setEnabled(True)
        tt = self._do_kokoro()
        # MỪNG THEO `thieu`, KHÔNG THEO `ok`: pip trả 0 mà gói vẫn nằm ngoài
        # môi trường riêng là chuyện đã xảy ra thật (cổng 58). Hậu kiểm là
        # `tinh_trang()` chứ không phải mã thoát của pip.
        if ok and not tt.get("thieu"):
            QMessageBox.information(
                self, "Xong",
                f"Đã tải xong {tt.get('so_giong', 0)} giọng Kokoro.\n"
                + str(tt.get("thu_muc", ""))
                + "\n\nChọn lại trong ô Giọng đọc để dùng.")
        else:
            QMessageBox.warning(
                self, "Chưa xong",
                "Tải giọng Kokoro CHƯA xong.\n"
                + ("Còn thiếu: " + ", ".join(list(tt.get("thieu") or [])[:6])
                   if tt.get("thieu") else "")
                + (("\n\n" + loi) if loi else "")
                + "\n\nApp vẫn chạy bình thường: chọn giọng Kokoro thì nó đọc "
                  "bằng giọng thường (edge-tts). Bấm lại để tải tiếp phần còn "
                  "thiếu.\nChi tiết ở logs/kokoro_<ngày>.log")
        # **CỐ Ý KHÔNG dựng lại combo giọng** — bản đầu của tôi có gọi
        # `_dung_combo_giong()` ở đây cho nhãn 28 dòng thôi khoe "CHƯA TẢI", và
        # đó là SAI: hàm đó đặt lại combo theo giá trị ĐÃ LƯU, tức nuốt mất
        # lựa chọn user vừa bấm mà chưa lưu — đúng họ lỗi "chọn X ra Y" mà
        # `_tai_gh_xong` đã ghi rõ vì sao nó không làm. Nhãn tự đúng ở lần mở
        # hộp sau, vì `danh_sach_giong()` hỏi lại máy mỗi lần dựng combo.

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

    def _dung_combo_giong(self, giu_dang_chon: bool = False) -> None:
        """Dựng lại combo giọng.

        ``giu_dang_chon=True`` -> giữ giọng ĐANG HIỆN trên combo thay vì đọc
        lại giá trị ĐÃ LƯU. Cố ý phải nói ra bằng tham số, không mặc định:
          · đường thường (nạp xong danh sách nền) phải lấy giá trị ĐÃ LƯU —
            đó là lựa chọn của anh Hùng từ lượt trước;
          · đường "vừa thêm giọng của tôi" thì KHÔNG: người dùng vừa lưu một
            giọng và chưa bấm Chạy nên setting còn là giọng CŨ, đọc setting là
            **nuốt mất giọng vừa thêm** — đúng họ lỗi "chọn X ra Y" mà
            `_tai_gh_xong`/`_tai_kokoro_xong` đã cố ý không gọi hàm này để né.
        """
        ra = getattr(self, "_ra_giong", None)
        if ra:
            self._giong_tho = list(ra[0] or [])
            if self._giong_tho:
                _CACHE_GIONG[:] = self._giong_tho
        muon = (str(self.cb_giong.currentData() or "") if giu_dang_chon
                else str(self._s.value(K_GIONG, "") or ""))
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
        ds = GB.gom_nhom(giong_dung_duoc(self._giong_tho), nn, loi_tat=True)
        # VIỆC 3 — ghi chú lối tắt nói MỘT LẦN ở tiêu đề nhóm, thay vì lặp 38 ký
        # tự trên cả 5 dòng. Dò bằng "tiêu đề nhóm ĐỨNG NGAY TRƯỚC dòng lối tắt
        # đầu tiên", KHÔNG so với `giong_bang._NHAN_NHOM[N_KHUYEN]`: đó là tên
        # riêng tư của module khác (đang có luồng khác giữ), so vào là nhãn bên
        # đó sửa một chữ thì ghi chú này im lặng biến mất.
        # VIỆC 3 — ĐẾM SỐ GIỌNG CỦA TỪNG NGUỒN TRÊN CHÍNH DANH SÁCH ĐANG BÀY,
        # để tooltip nói được *"dùng chung cho cả 20 giọng"* mà không ai phải
        # ghi cứng số 20 vào hằng số (ghi cứng = lần thêm giọng kế tiếp nhãn
        # thành lời khai sai, không cổng nào kêu).
        # **ĐẾM THEO MÃ GIỌNG DUY NHẤT, KHÔNG ĐẾM DÒNG:** nhóm lối tắt bày lại
        # đúng những giọng đã có ở nhóm dưới, đếm dòng là ra 25 cho 20 giọng —
        # tức đi chữa một con số sai bằng một con số sai khác.
        _ma_theo_nguon: dict[str, set] = {}
        for _n, _v in ds:
            if _v:
                _ma_theo_nguon.setdefault(GB.nguon(str(_v)), set()).add(str(_v))
        self._so_cung_bo = {k: len(s) for k, s in _ma_theo_nguon.items()}
        i_lt = next((j for j, (n, v) in enumerate(ds)
                     if v and GB.DAU_LOI_TAT in n), -1)
        i_tieu_de_lt = max((j for j, (_n, v) in enumerate(ds)
                            if not v and j < i_lt), default=-1)
        fm = self.cb_giong.view().fontMetrics()
        tr = tran_nhan(self.cb_giong)
        for j, (nhan, vid) in enumerate(ds):
            if not vid:                     # nhãn NHÓM -> không cho chọn
                self.cb_giong.addItem(
                    nhan + (GHI_CHU_LOI_TAT if j == i_tieu_de_lt else ""), vid)
                it = self.cb_giong.model().item(self.cb_giong.count() - 1)
                if it is not None:
                    to_nhan_nhom(it)        # đậm + màu khác + NoItemFlags
                continue
            # NHÃN NGẮN lên dòng, NHÃN ĐẦY ĐỦ vào tooltip. Mã giọng (`vid`) là
            # thứ đi vào QSettings và payload job — nó KHÔNG đổi, nên rút gọn
            # chữ không thể làm lệch giọng đã chọn.
            self.cb_giong.addItem(nhan_gon(nhan, fm, tr), vid)
            it = self.cb_giong.model().item(self.cb_giong.count() - 1)
            if it is not None:
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
        self._noi_rong_popup()
        self._ve_goi_y()

    def _noi_rong_popup(self) -> None:
        """VIỆC 1 — nới Ô DANH SÁCH cho VỪA CHỮ, chặn trần ở bề rộng cửa sổ.

        Anh Hùng 19/08/2026 (ảnh v2.39.0): *"nhiều giọng hơn mà không có phân
        chia gì à, LOẠN QUÁ"*. Nhóm CHẠY ĐÚNG rồi, chỗ hỏng là **ô danh sách
        hẹp bằng chính combo (300 px) nên nhãn bị cắt GIỮA CÂU** — và
        `QComboBox` elide kiểu **ElideMiddle** (đo được:
        `view().textElideMode()` = `ElideMiddle`), tức nó ăn đúng khúc GIỮA
        mang thông tin: `KHUYÊN DÙNG cho Tiế...phí, chạy được ngay`.

        ĐO TRƯỚC KHI SỬA (`_do_combo_giong.py`, 371 dòng, phông thật): ở bề
        rộng combo 300 px thì **359/371 nhãn bị cắt (96,8%)**.

        Cách nới: `view().setMinimumWidth(...)` — bề rộng popup của
        `QComboBox` bám theo minimumWidth của VIEW (đo: popup 290 -> 630 px khi
        đặt 640). **KHÔNG đo bằng `itemDelegate().sizeHint()`**: view của combo
        dùng `QComboBoxDelegate` trả bề rộng ĐỒNG NHẤT cho mọi dòng (đo 851 px
        cho cả dòng 1 ký tự lẫn dòng 600 ký tự) nên thước đó luôn nói "cắt
        100%", một con số không có thật.
        """
        try:
            view = self.cb_giong.view()
            fm = view.fontMetrics()
            view.setMinimumWidth(rong_vua_chu(
                fm,
                [self.cb_giong.itemText(i)
                 for i in range(self.cb_giong.count())],
                rong_toi_da(self.cb_giong)))
            # VIỆC 2: bộ vẽ riêng cho tiêu đề nhóm. Giữ MỘT thực thể trên hộp
            # (đặt lại mỗi lần đổi ngôn ngữ là đẻ delegate rác, mà Qt KHÔNG sở
            # hữu delegate -> Python thu hồi trong lúc view còn trỏ tới = sập).
            if getattr(self, "_ve_dong", None) is None:
                self._ve_dong = VeDongGiong(self)
                view.setItemDelegate(self._ve_dong)
        except (AttributeError, RuntimeError):
            pass            # popup chỉ là đường LÙI (đường chính là ô tìm)

    # ------------------------------------------------------------------
    # VIỆC 4 — Ô TÌM GIỌNG
    # ------------------------------------------------------------------
    def _giong_phang(self) -> list[tuple[int, str, str, str]]:
        """Cả combo dàn thành MỘT danh sách phẳng `(chỉ số, nhãn, mã, nhóm)`.

        Đây là chỗ bảo đảm mệnh đề *"gõ tên giọng ở nhóm KHÁC cũng phải ra"*:
        nguồn tìm là TOÀN BỘ combo, không phải "nhóm đang chọn". Bẫy này đã sập
        với ô tìm kênh ở v2.6.12 (anh Hùng: *"có hoạt động đâu"*) vì ô lọc chỉ
        lọc trong nhóm hiện tại.
        """
        ra: list[tuple[int, str, str, str]] = []
        nhom = ""
        for i in range(self.cb_giong.count()):
            nhan = str(self.cb_giong.itemText(i))
            vid = str(self.cb_giong.itemData(i) or "")
            it = self.cb_giong.model().item(i)
            if it is not None and it.data(VAI_NHOM):
                nhom = nhan
                ra.append((i, nhan, "", nhan))
                continue
            ra.append((i, nhan, vid, nhom))
        return ra

    #: Khoá hàng lọc -> khoá QSettings. Một bảng, để `_gp_loc` (đọc) và
    #: `_gp_luu_loc` (ghi) không bao giờ đi hai đường khác nhau.
    _GP_KHOA_LOC = {"tieng": K_GP_TIENG, "gioi": K_GP_GIOI,
                    "tien": K_GP_TIEN, "may": K_GP_MAY}

    def _gp_hang_loc(self, hang, khoa: str, ten: str, bo) -> list:
        """Một hàng nút lọc BẤM ĐƯỢC, loại trừ nhau trong cùng hàng.

        Dùng `QPushButton` checkable + `QButtonGroup(exclusive)` chứ KHÔNG dùng
        `QComboBox`: combo phải bấm-rồi-mở-rồi-chọn (3 động tác cho 1 lựa chọn)
        và nó **giấu mất các lựa chọn còn lại**. Cả vấn đề anh Hùng nêu là "tìm
        rất khó", nên mọi lựa chọn phải NHÌN THẤY và bấm MỘT nhát là xong.

        NHÃN LÀ CHỮ, KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen, v2.6.22).
        Nút đang bấm tô màu ACCENT để phân biệt được ở khoảng cách một liếc mắt
        — QSS RIÊNG cho nút này, vì QSS chung của app không có kiểu "đang chọn".
        """
        from PyQt6.QtWidgets import QButtonGroup
        lb = QLabel(ten)
        lb.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        hang.addWidget(lb)
        nhom = QButtonGroup(self)
        nhom.setExclusive(True)
        # GIỮ THAM CHIẾU: `QButtonGroup` cha là `self` nên nó sống, nhưng giữ
        # thêm ở đây để cổng test soi được, và để không ai "dọn gọn" mất.
        if not hasattr(self, "_gp_bgroup"):
            self._gp_bgroup = {}
        self._gp_bgroup[khoa] = nhom
        cu = str(self._s.value(self._GP_KHOA_LOC[khoa], "") or "")
        co = {m for _n, m in bo}
        if cu not in co:
            cu = ""                     # cài đặt cũ/rác -> về (tất cả)
        ra = []
        for nhan, ma in bo:
            b = QPushButton(nhan)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{SURFACE};color:{MUTED};"
                f"border:1px solid {BORDER};border-radius:6px;"
                f"padding:2px 8px;font-size:11px;}}"
                f"QPushButton:hover{{color:{TEXT};border-color:{MUTED};}}"
                f"QPushButton:checked{{background:{ACCENT};color:white;"
                f"border-color:{ACCENT};font-weight:600;}}")
            b.setChecked(ma == cu)
            b.setProperty("ma_loc", ma)
            nhom.addButton(b)
            hang.addWidget(b)
            ra.append((ma, b))
            # `toggled` chứ không `clicked`: bấm nút B thì nút A bị nhóm loại ra
            # KHÔNG phát `clicked`, mà `fill` phải chạy đúng MỘT lần cho lượt
            # đó -> chỉ nghe vế BẬT.
            b.toggled.connect(
                lambda on, _k=khoa: (self._gp_doi_loc() if on else None))
        return ra

    def _nhan_giong_goc(self, vid: str) -> str:
        """NHÃN ĐẦY ĐỦ của giọng GỐC (bỏ hậu tố cao độ) — "" nếu không phải biến thể.

        Dùng cho phép dò giới tính: 8 dòng biến thể cao độ mang nhãn `Nam Minh —
        hơi cao` / `Hoài My — trầm`, không có chữ nào nói giới tính, nên phải
        tra sang giọng gốc `vi-VN-NamMinhNeural` (`Nam Minh — Nam chuẩn`).
        Biến thể cao độ KHÔNG đổi người đọc nên tra sang gốc là đúng nghĩa.

        Nhận ra biến thể bằng `giong_bang.la_bien_the` (hàm CÔNG KHAI đã có) —
        đừng tự cắt ở `|`: nguồn Chatterbox dùng `|` cho việc KHÁC (đường dẫn
        mẫu), cắt là mất giọng nhân bản.
        """
        v = str(vid or "")
        try:
            if not GB.la_bien_the(v):
                return ""
            goc = v.split("|", 1)[0]
        except Exception:  # noqa: BLE001
            return ""
        i = self.cb_giong.findData(goc)
        if i < 0:
            return ""
        it = self.cb_giong.model().item(i)
        return str(self.cb_giong.itemText(i)) + "\n" + (
            it.toolTip() if it is not None else "")

    def _gp_loc(self) -> dict:
        """Bộ lọc ĐANG BẤM, đọc từ CHÍNH các nút đang hiện.

        **ĐỌC WIDGET, KHÔNG ĐỌC QSettings.** Cài đặt chỉ được ghi lúc đóng hộp
        nên nó là lựa chọn CŨ; đọc nó là lặp đúng lỗi *"chạy dây chuyền lấy
        nhóm từ setting nên chạy sai nhóm"* (bài học `pipe_run_group_from_combo`
        và cổng 85).
        """
        ra = {}
        for khoa, cap in (getattr(self, "_gp_nut", None) or {}).items():
            ra[khoa] = ""
            for ma, b in cap:
                try:
                    if b.isChecked():
                        ra[khoa] = ma
                        break
                except RuntimeError:      # widget Qt đã xoá
                    pass
        return ra

    def _gp_doi_loc(self) -> None:
        """Bấm một nút lọc -> vẽ lại danh sách, GIỮ NGUYÊN chữ trong ô tìm."""
        fill = getattr(self, "_gp_fill", None)
        if fill is None:
            return
        try:
            fill(self._gp_ed.text())
        except RuntimeError:
            pass

    def _gp_luu_loc(self) -> None:
        """Ghi lựa chọn lọc + CỠ HỘP vào QSettings (nhớ cho lần mở sau).

        Anh Hùng dùng 300 kênh: bắt bấm lại 4 ô lọc và kéo lại cỡ hộp mỗi lần
        mở là phí thật, đo bằng số lần bấm.
        """
        try:
            for khoa, ma in self._gp_loc().items():
                self._s.setValue(self._GP_KHOA_LOC[khoa], ma)
            pop = getattr(self, "_gp_pop", None)
            if pop is not None:
                self._s.setValue(K_GP_RONG, int(pop.width()))
                self._s.setValue(K_GP_CAO, int(pop.height()))
        except (RuntimeError, AttributeError, ValueError):
            pass                          # nhớ cỡ hộp KHÔNG được làm sập app

    def _mo_chon_giong(self):
        """DANH SÁCH GIỌNG có Ô TÌM ngay trên đầu — thay popup mặc định.

        **DÙNG LẠI MẪU ĐÃ CHẠY ĐƯỢC** `studio_page._open_chan_picker` (cổng 9),
        kể cả 4 bài học đã trả giá ở đó:

        1. **VẪN LÀ COMBO** — bấm là mở danh sách. Biến nó thành ô-gõ là lặp
           v2.6.10 (*"này không mở được"*).
        2. **TÌM TRÊN TOÀN DANH SÁCH**, nhãn ghi rõ giọng đó thuộc nhóm nào. Lọc
           trong-nhóm-đang-chọn là lặp v2.6.12 (*"có hoạt động đâu"*).
        3. **KHÔNG `Qt.WindowType.Popup`** — kiểu đó Qt TỰ ĐÓNG khi mất focus,
           anh Hùng sang trình duyệt rồi quay lại là mất danh sách (v2.6.21).
           Dùng `Tool | FramelessWindowHint`: cửa sổ con ĐI THEO app, không tự
           đóng. Đóng bằng: chọn giọng · nút Đóng · Esc · bấm ra ngoài.
        4. **NÚT LÀ CHỮ, KHÔNG EMOJI** — máy anh Hùng thiếu glyph nên nút ra Ô
           ĐEN (v2.6.22: *"xấu quá tự nhiên có cái ô đen"*).

        Kèm QSS RIÊNG cho danh sách này: QSS chung có
        `QListWidget::item{padding:9px 10px;margin:2px}` — padding đó cộng vào
        mỗi dòng thì 371 dòng cao thêm hẳn một màn hình. Ghi đè về `padding:0`
        và tự đặt chiều cao dòng.
        """
        cu = getattr(self, "_gp_pop", None)
        # bấm lại vào combo khi đang mở -> ĐÓNG (bật/tắt như dropdown thường).
        # Không có nhánh này thì bộ lọc bấm-ra-ngoài đóng rồi `showPopup` mở lại
        # ngay = tưởng bấm không ăn.
        if cu is not None and cu.isVisible():
            cu.close()
            return cu
        if cu is not None and getattr(self, "_gp_fill", None) is not None:
            try:
                self._gp_ed.clear()
                self._gp_fill("")
                self._gp_dat_cho(cu)
                cu.show()
                cu.raise_()
                self._gp_ed.setFocus()
                return cu
            except RuntimeError:
                pass                # widget cũ Qt đã xoá -> dựng lại bên dưới

        pop = QFrame(self, Qt.WindowType.Tool
                     | Qt.WindowType.FramelessWindowHint)
        pop.setObjectName("giongPick")
        pop.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        pop.setStyleSheet(
            f"#giongPick{{background:{BASE};border:1px solid {BORDER};"
            f"border-radius:10px;}}")
        lay = QVBoxLayout(pop)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        hrow = QHBoxLayout()
        hrow.setSpacing(6)
        ed = QLineEdit()
        ed.setPlaceholderText(
            "Gõ tên giọng để tìm trên MỌI nhóm (gõ không dấu cũng ra)...")
        ed.setClearButtonEnabled(True)
        hrow.addWidget(ed, 1)
        xb = QPushButton("Đóng")          # NÚT CHỮ, KHÔNG EMOJI
        xb.setFixedWidth(58)
        xb.setToolTip("Đóng danh sách (hoặc bấm Esc, hoặc bấm ra ngoài)")
        xb.setStyleSheet(
            f"QPushButton{{background:{SURFACE};color:{MUTED};"
            f"border:1px solid {BORDER};border-radius:6px;padding:3px 6px;"
            f"font-size:12px;}}"
            f"QPushButton:hover{{color:{TEXT};border-color:{MUTED};}}")
        xb.clicked.connect(pop.close)
        hrow.addWidget(xb)
        lay.addLayout(hrow)

        # ---- VIỆC 1: HÀNG NÚT LỌC ----
        # Ô tìm một mình đòi anh Hùng BIẾT TRƯỚC gõ gì; mấy nút này đi NGƯỢC
        # LẠI (bấm điều kiện, danh sách tự co) và **cộng dồn với ô tìm**.
        # Mặc định đều `(tất cả)` -> lần mở đầu danh sách y hệt bản trước.
        #
        # ĐÚNG **HAI** HÀNG, không phải bốn — mỗi hàng nút ăn ~26 px chiều cao,
        # mà chiều cao là thứ đang thiếu (anh Hùng: *"hiển thị bảng nhỏ"*). Ba
        # ô Giới/Tiền/Chạy chỉ có 3 nút mỗi ô nên xếp chung một hàng vẫn đọc
        # được, trong khi tách ra là mất thêm 52 px của DANH SÁCH.
        self._gp_nut = {}                  # khoá hàng -> [(mã, nút)]
        r1 = QHBoxLayout()
        r1.setSpacing(4)
        self._gp_nut["tieng"] = self._gp_hang_loc(r1, "tieng", "Tiếng:",
                                                  LOC_TIENG)
        r1.addStretch(1)
        lay.addLayout(r1)
        r2 = QHBoxLayout()
        r2.setSpacing(4)
        for khoa, ten, bo in (("gioi", "Giới:", LOC_GIOI),
                              ("tien", "Tiền:", LOC_TIEN),
                              ("may", "Chạy ở:", LOC_MAY)):
            self._gp_nut[khoa] = self._gp_hang_loc(r2, khoa, ten, bo)
            r2.addSpacing(8)
        r2.addStretch(1)
        lay.addLayout(r2)

        lb = QLabel("")
        lb.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        lb.setWordWrap(True)
        lay.addWidget(lb)

        lst = QListWidget()
        lst.setAlternatingRowColors(False)
        lst.setUniformItemSizes(True)     # 371 dòng: đo chiều cao 1 lần
        lst.setStyleSheet(
            f"QListWidget{{background:{SURFACE};border:1px solid {BORDER};"
            f"border-radius:8px;color:{TEXT};}}"
            f"QListWidget::item{{padding:2px 4px;margin:0px;}}"
            f"QListWidget::item:hover{{background:{SURFACE_HOVER};}}"
            f"QListWidget::item:selected{{background:{ACCENT};color:white;}}")
        # CÙNG bộ vẽ với popup combo -> tiêu đề nhóm trông y hệt ở hai chỗ
        if getattr(self, "_ve_dong", None) is None:
            self._ve_dong = VeDongGiong(self)
        lst.setItemDelegate(self._ve_dong)
        lay.addWidget(lst, 1)
        QShortcut(QKeySequence("Esc"), pop, pop.close)
        self._gp_pop, self._gp_ed, self._gp_lst, self._gp_lb = pop, ed, lst, lb

        def fill(q: str = "") -> None:
            lst.clear()
            ds = self._giong_phang()
            tu = [bo_dau(t) for t in str(q or "").split() if t.strip()]
            loc = self._gp_loc()
            # CÓ LỌC hay CÓ GÕ -> bày PHẲNG (dán "ở nhóm: X" vào từng dòng).
            # Giữ tiêu đề nhóm lúc đang lọc thì đa số tiêu đề trở thành nhãn
            # RỖNG treo trên không (nhóm bị lọc sạch), tức đúng cái "loạn quá"
            # mà cổng 84 vừa chữa. Bày phẳng dùng LẠI y đường của ô tìm.
            co_loc = any(loc.values())
            phang = bool(tu) or co_loc
            # TỔNG = số GIỌNG, không tính tiêu đề nhóm và KHÔNG tính dòng 0
            # ("Tự chọn theo ngôn ngữ đích" là một LỰA CHỌN, không phải một
            # giọng). Đếm lẫn dòng 0 vào `hien` mà không lẫn vào `tong` thì
            # lúc không lọc gì nhãn ra `đang hiện 365 / 364` — một con số vô lý
            # nằm ngay chỗ anh Hùng phải TIN để biết bộ lọc có ăn hay không.
            tong = sum(1 for _i, _n, v, _g in ds if v)
            so_nhom = sum(1 for i, _n, v, _g in ds if not v and i > 0)
            hien = 0
            chua_do = 0                   # lọt vì CHƯA ĐO, không vì đã đo đạt
            for i, nhan, vid, nhom in ds:
                if phang and not vid:
                    continue              # đang lọc/tìm -> bỏ tiêu đề nhóm
                if vid and co_loc:
                    # NHÃN ĐẦY ĐỦ nằm ở tooltip (dòng đã bị `nhan_gon` rút) —
                    # phép dò giới tính phải đọc bản ĐẦY ĐỦ, không thì 335 dòng
                    # edge-tts bị rút mất khúc "(Nam)" rồi lọc ra 0 dòng.
                    it0 = self.cb_giong.model().item(i)
                    tt = it0.toolTip() if it0 is not None else ""
                    if not khop_loc(vid, f"{nhan}\n{tt}", loc,
                                    self._nhan_giong_goc(vid)):
                        continue
                    if chua_do_tieng(vid, str(loc.get("tieng") or "")):
                        chua_do += 1
                if tu:
                    it0 = self.cb_giong.model().item(i)
                    kho = bo_dau(" ".join((
                        nhan, vid, nhom,
                        it0.toolTip() if it0 is not None else "")))
                    if not all(t in kho for t in tu):
                        continue
                if phang and vid:
                    # NHÃN GHI RÕ NHÓM — chọn được giọng nhóm khác thì phải biết
                    # mình vừa lấy ở nhóm nào (đúng cách `_open_chan_picker` ghi
                    # "· nhóm X").
                    chu = f"{nhan}   ·  ở nhóm: {nhom}" if nhom else nhan
                else:
                    chu = nhan
                it = QListWidgetItem(chu)
                it.setData(Qt.ItemDataRole.UserRole, i)
                if not vid and not phang and i > 0:
                    to_nhan_nhom(it)      # tiêu đề nhóm: đậm + màu + không chọn
                else:
                    it0 = self.cb_giong.model().item(i)
                    if it0 is not None and it0.toolTip():
                        it.setToolTip(it0.toolTip())
                    if vid:               # dòng 0 hiện nhưng KHÔNG phải giọng
                        hien += 1
                lst.addItem(it)
            # ---- SỐ DÒNG ĐANG THẤY: `đang hiện 37 / 364` ----
            # Không có con số này thì anh Hùng KHÔNG BIẾT bộ lọc có ăn hay
            # không — bấm một nút, danh sách đổi, mà đổi bao nhiêu thì phải tự
            # đếm bằng mắt trên 364 dòng. Luôn hiện CẢ HAI vế (đang thấy /
            # tổng) kể cả lúc không lọc gì, để con số không "mọc ra" rồi biến
            # mất tuỳ trạng thái.
            dang = [f"đang hiện {hien} / {tong} giọng"]
            if not hien:
                # LỌC RA 0 DÒNG THÌ PHẢI NÓI, đừng để bảng trắng trơn: bảng
                # trắng đọc ra y như "app hỏng / danh sách mất rồi".
                lst.addItem(QListWidgetItem(
                    "Không giọng nào khớp — bấm (tất cả) ở các ô trên để xem "
                    "lại, hoặc xoá chữ trong ô tìm."))
                dang = ["Không giọng nào khớp — bấm (tất cả) để xem lại"
                        f" (tổng {tong} giọng)"]
            elif co_loc and tu:
                dang.append("đang LỌC và đang TÌM cùng lúc")
            elif co_loc:
                dang.append("đang lọc: " + " · ".join(
                    n for bo in (LOC_TIENG, LOC_GIOI, LOC_TIEN, LOC_MAY)
                    for n, m in bo if m and m in loc.values()))
            if hien and chua_do:
                # NÓI RA CHỖ MÌNH CHƯA BIẾT, đừng để nó trông như đã đo.
                # Ô tiếng giữ lại cả giọng CHƯA ĐO tiếng đó (luật "không xác
                # định được thì GIỮ"), nên trong danh sách có dòng lọt vào vì
                # KHÔNG AI ĐO chứ không vì nó đọc được. Đo được: 8 dòng như thế
                # ở mỗi ô tiếng (5 OmniVoice · 3 Vbee). Im lặng thì anh Hùng
                # thấy một giọng Vbee tiếng Việt nằm trong ô "Hàn" và kết luận
                # bộ lọc hỏng.
                dang.append(f"trong đó {chua_do} giọng CHƯA ĐO tiếng này "
                            "(giữ lại cho anh tự thử, không phải đã đo đạt)")
            elif tu:
                dang.append("bấm để chọn, Enter lấy dòng đầu")
            else:
                dang.append(f"{so_nhom} nhóm"
                            " — gõ ở ô tìm hoặc bấm nút lọc ở trên")
            lb.setText(" — ".join(dang))
            # về ĐẦU danh sách + chọn dòng chọn-được đầu tiên (Enter dùng nó)
            for r in range(lst.count()):
                if lst.item(r).flags() & Qt.ItemFlag.ItemIsSelectable:
                    lst.setCurrentRow(r)
                    break
            lst.scrollToTop()

        def chon(item=None) -> None:
            it = item or lst.currentItem()
            if it is None:
                return
            i = it.data(Qt.ItemDataRole.UserRole)
            if i is None:
                return
            pop.close()
            self.cb_giong.setCurrentIndex(int(i))

        ed.textChanged.connect(fill)
        ed.returnPressed.connect(lambda: chon())
        lst.itemClicked.connect(chon)
        lst.itemActivated.connect(chon)
        self._gp_fill = fill

        # ĐÓNG KHI BẤM RA NGOÀI. Cửa sổ Tool KHÔNG tự đóng (đó là điều anh Hùng
        # muốn khi sang app khác), nên phải tự bắt cú bấm. BỎ QUA cú bấm vào
        # chính combo — nó tự bật/tắt ở trên.
        from PyQt6.QtCore import QEvent
        from PyQt6.QtCore import QObject as _QObj
        from PyQt6.QtWidgets import QApplication as _QApp

        class _BamRaNgoai(_QObj):
            def __init__(self, hop, popup):
                super().__init__(popup)
                self.hop, self.popup = hop, popup

            def eventFilter(self, obj, ev):      # noqa: N802 - API Qt
                try:
                    if (ev.type() == QEvent.Type.MouseButtonPress
                            and self.popup.isVisible()
                            and isinstance(obj, QWidget)):
                        cb = self.hop.cb_giong
                        if obj is cb or cb.isAncestorOf(obj):
                            return False         # combo tự lo bật/tắt
                        if obj is not self.popup \
                                and not self.popup.isAncestorOf(obj):
                            self.popup.close()
                except RuntimeError:
                    pass                         # widget đã bị xoá -> bỏ qua
                return False                     # KHÔNG chặn sự kiện của app

        self._gp_filter = _BamRaNgoai(self, pop)
        _QApp.instance().installEventFilter(self._gp_filter)
        # ---- VIỆC 2: KÉO ĐƯỢC CỠ HỘP + NHỚ CỠ ----
        # Hộp là `QFrame` không viền nên KHÔNG có mép để kéo; `QSizeGrip` là
        # cái tay cầm duy nhất. Không có nó thì "nhớ cỡ hộp" thành vô nghĩa —
        # anh Hùng không có cách nào đặt ra một cỡ để mà nhớ.
        from PyQt6.QtWidgets import QSizeGrip
        gr = QHBoxLayout()
        gr.setContentsMargins(0, 0, 0, 0)
        gr.addStretch(1)
        gr.addWidget(QSizeGrip(pop), 0, Qt.AlignmentFlag.AlignBottom
                     | Qt.AlignmentFlag.AlignRight)
        lay.addLayout(gr)
        # GHI CỠ + LỰA CHỌN LỌC LÚC ĐÓNG. Bắt `closeEvent` chứ không nhờ nút
        # Đóng: hộp còn đóng bằng Esc / bấm ra ngoài / chọn giọng — nối vào một
        # cửa là 3 cửa kia mất cài đặt mà không ai biết.
        _dong_cu = pop.closeEvent

        def _dong(ev, _c=_dong_cu):
            self._gp_luu_loc()
            _c(ev)
        pop.closeEvent = _dong           # type: ignore[method-assign]
        fill("")
        self._gp_dat_cho(pop)
        pop.show()
        pop.raise_()
        ed.setFocus()
        return pop

    def _gp_dat_cho(self, pop) -> None:
        """Đặt hộp chọn giọng ngay dưới combo, RỘNG VỪA NHÃN + CAO RA TẤM RA MIẾNG.

        VIỆC 2 (anh Hùng: *"hiển thị bảng nhỏ mà tận mấy trăm giọng tìm rất
        khó"*). Ba mức, ưu tiên giảm dần:

        1. **CỠ ANH HÙNG ĐÃ KÉO** (QSettings) — cao nhất, vì đó là lựa chọn
           tường minh của người dùng.
        2. chưa kéo lần nào -> `GP_RONG_CHUAN` × `GP_CAO_CHUAN`, hoặc **theo tỉ
           lệ CỬA SỔ CHÍNH** nếu cửa sổ đó lớn (`GP_TY_LE_CAO`) — máy anh Hùng
           màn hình lớn thì hộp nên lớn theo, đừng khoá cứng ở một số nhỏ.
        3. luôn kẹp trong MÀN HÌNH và không hẹp hơn nhãn dài nhất.

        **BỀ CAO PHẢI KẸP THEO MÀN HÌNH, KHÔNG CHỈ THEO SỐ CHUẨN** — hộp mọc từ
        combo nằm ở GIỮA hộp thoại nên nó đi XUỐNG; cao 560 trên màn hình 768 là
        đáy hộp rơi ra ngoài mép dưới, tức thêm chiều cao mà **đọc được ÍT
        HƠN**. Vì vậy còn có bước dời lên (`y` âm dần) khi thiếu chỗ.
        """
        from PyQt6.QtCore import QPoint
        fm = self._gp_lst.fontMetrics()
        w = rong_vua_chu(
            fm, [self.cb_giong.itemText(i)
                 for i in range(self.cb_giong.count())],
            rong_toi_da(self.cb_giong))
        w = max(w, self.cb_giong.width(), GP_RONG_CHUAN)
        # cao chuẩn, hoặc theo tỉ lệ cửa sổ chính nếu cửa sổ lớn hơn
        h = GP_CAO_CHUAN
        try:
            cs = self.window()
            if cs is not None and cs.height() > 0:
                h = max(h, int(cs.height() * GP_TY_LE_CAO))
        except (AttributeError, RuntimeError):
            pass
        # cỡ anh Hùng đã kéo -> ưu tiên nhất
        try:
            rw = int(self._s.value(K_GP_RONG, 0) or 0)
            rh = int(self._s.value(K_GP_CAO, 0) or 0)
        except (TypeError, ValueError):
            rw = rh = 0
        if rw >= GP_RONG_TOI_THIEU:
            w = rw
        if rh >= GP_CAO_TOI_THIEU:
            h = rh
        # KẸP TRONG MÀN HÌNH (cả rộng lẫn cao) rồi mới đặt chỗ
        goc = self.cb_giong.mapToGlobal(QPoint(0, self.cb_giong.height() + 2))
        x, y = goc.x(), goc.y()
        try:
            mh = self.cb_giong.screen()
            if mh is not None:
                r = mh.availableGeometry()
                w = min(w, max(GP_RONG_TOI_THIEU, r.width() - 24))
                h = min(h, max(GP_CAO_TOI_THIEU, r.height() - 24))
                x = min(max(r.left() + 4, x), max(r.left() + 4,
                                                  r.right() - w - 4))
                if y + h > r.bottom() - 4:
                    # không đủ chỗ bên dưới -> dời LÊN, thà che combo còn hơn
                    # để mất đuôi danh sách ra ngoài mép màn hình
                    y = max(r.top() + 4, r.bottom() - h - 4)
        except (AttributeError, RuntimeError):
            pass
        pop.resize(int(w), int(h))
        pop.move(int(x), int(y))

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

        `nhan` truyền vào phải là **NHÃN ĐẦY ĐỦ** (bản trước khi `nhan_gon` rút
        gọn) — đây là chỗ DUY NHẤT còn giữ nguyên văn 610 ký tự cảnh báo giấy
        phép của giọng OmniVoice. Truyền nhãn đã rút vào đây là rút gọn biến
        thành **xoá thông tin**.
        """
        dong = []
        if GB.DAU_LOI_TAT in str(nhan or ""):
            # dòng LỐI TẮT: nói thẳng ở ĐẦU tooltip, vì trên dòng nó chỉ còn
            # đúng hai chữ "lối tắt".
            dong.append("LỐI TẮT — vẫn đúng giọng này, nó còn nằm trong nhóm "
                        "ngôn ngữ ở phía dưới. Chọn dòng nào cũng như nhau.")
        dong.append(nhan)
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
            # VIỆC 3 — nói RÕ "một bộ, tải một lần, dùng chung N giọng".
            # Đuôi trên DÒNG chỉ dám ghi "bộ dùng chung" (hết chỗ, và số ghi
            # cứng sẽ nói sai ngay lần thêm giọng kế tiếp); con số nói ở ĐÂY vì
            # tooltip đọc TỪNG DÒNG MỘT nên không dựng lại được ảo giác nhân.
            # `_so_cung_bo` do `_dung_combo_giong` ĐẾM TRÊN DANH SÁCH ĐANG BÀY.
            bo = GB.ghi_chu_bo_chung(
                vid, (getattr(self, "_so_cung_bo", None) or {}).get(
                    GB.nguon(vid), 0))
            if bo:
                dong.append(bo)
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
        # Qua `chuan_cach_tron` TRƯỚC KHI GHI: bản sau đổi tên cách trộn thì
        # giá trị cũ trong QSettings không âm thầm biến thành cách MỚI.
        self._s.setValue(K_TRON_CACH,
                         TG.chuan_cach_tron(self.cb_tron.currentData()))
        # HAI Ô ÂM LƯỢNG: ghi số ĐÃ chuẩn hoá (qua `muc_am_luong`), không ghi
        # `.value()` thô — mở lại hộp là thấy ĐÚNG số app sẽ áp, không phải số
        # rồi bị làm tròn khác đi lúc chạy.
        _nen, _giong = self.muc_am_luong()
        self._s.setValue(K_MUC_NEN, _nen)
        self._s.setValue(K_MUC_GIONG, _giong)
        self._s.setValue(K_KC_PRESET, self.cb_kc_preset.currentData() or "")
        self._s.setValue(K_KC_FONT, self.cb_kc_font.currentData() or "")
        self._s.setValue(K_KC_CO, float(self.sp_kc_co.value()))
        self._s.setValue(K_KC_DAM, self.cb_kc_dam.currentData() or "")
        self._s.setValue(K_KC_NGHIENG, self.cb_kc_nghieng.currentData() or "")
        self._s.setValue(K_KC_MAU, self._kc_mau)
        self._s.setValue(K_KC_VIEN, self._kc_vien)
        self._s.setValue(K_KC_DOVIEN, float(self.sp_kc_dovien.value()))
        self._s.setValue(K_KC_VITRI, self.cb_kc_vitri.currentData() or "")

    def _o_dB(self, khoa: str, chu_dan: str) -> QDoubleSpinBox:
        """Dựng MỘT ô dB. Hai ô đi qua CÙNG hàm này nên không lệch nhau được.

        Trần lấy từ `TG.TRAN_MUC_TAY_DB`, bước từ `TG.BUOC_MUC_TAY_DB` — **MỘT
        NGUỒN DUY NHẤT** với `chuan_muc_db` (cửa kẹp/làm tròn thật). Viết tay
        6.0 ở đây là đẻ nguồn sự thật thứ hai rồi lệch khi ai đó đổi hằng số.

        `setSuffix(" dB")` để đơn vị nằm NGAY TRONG ô — nhãn bên ngoài đã dài,
        thêm chữ "dB" nữa là dài gấp đôi mà vẫn không rõ ô nào của ai.
        """
        o = QDoubleSpinBox()
        o.setRange(-TG.TRAN_MUC_TAY_DB, TG.TRAN_MUC_TAY_DB)
        o.setSingleStep(0.5)
        o.setDecimals(1)
        o.setSuffix(" dB")
        # **KHÔNG dùng `setSpecialValueText`**: nó chỉ áp cho giá trị NHỎ NHẤT
        # (-6,0 dB), không áp cho 0,0 — đặt nó ở đây là ô hiện chữ lạ đúng lúc
        # anh Hùng kéo hết về đáy. Việc "nói ra 0,0 là mặc định" do nhãn
        # `lb_muc_tt` lo (xem `_ve_tt_muc`).
        o.setToolTip(chu_dan)
        o.setMinimumWidth(96)
        # ĐỌC LẠI QUA `chuan_muc_db`: file .ini có thể mang rác (sửa tay, bản
        # trước ghi kiểu khác, số ngoài trần) -> lùi êm về 0,0 = mặc định, chứ
        # KHÔNG nổ hộp thoại và cũng không nhận một hệ số bịa.
        o.setValue(TG.chuan_muc_db(self._s.value(khoa, 0.0)))
        return o

    def muc_am_luong(self) -> tuple[float, float]:
        """(nền dB, giọng dB) đọc từ CHÍNH HAI Ô ĐANG HIỆN — cửa DUY NHẤT.

        Đọc widget, **KHÔNG đọc QSettings** (bài học "chạy dây chuyền: đọc
        combo, không đọc setting": widget bị `blockSignals` thì setting lệch với
        cái user đang nhìn -> chạy sai cấu hình). Và đi qua `chuan_muc_db` để
        UI · payload · khoá chống trùng · bước trộn cùng một phép làm tròn.

        `(0.0, 0.0)` = để mặc định -> `xep_mot` KHÔNG ghi khoá nào vào payload.
        """
        return (TG.chuan_muc_db(self.sp_muc_nen.value()),
                TG.chuan_muc_db(self.sp_muc_giong.value()))

    def _ve_tt_muc(self) -> None:
        """Nhãn cạnh hai ô: đang mặc định, hay đã kéo mấy dB.

        Đếm bằng CHÍNH `muc_am_luong()` — cửa duy nhất quyết định cái gì đi vào
        payload. Tự đọc lại từng ô ở đây là đẻ nguồn sự thật thứ hai rồi lệch
        (đúng bài học `_ve_tt_kc` ngay dưới).
        """
        if not hasattr(self, "lb_muc_tt"):
            return
        nen, giong = self.muc_am_luong()
        if nen == 0.0 and giong == 0.0:
            self.lb_muc_tt.setText("(đang để MẶC ĐỊNH 0,0 dB — app tự đo tự "
                                   "quyết, y như bản trước)")
            self.lb_muc_tt.setStyleSheet("color:#8A93A6")
        else:
            self.lb_muc_tt.setText(
                f"(đã đổi: nền {nen:+.1f} dB · giọng {giong:+.1f} dB — mặc "
                f"định là 0,0)".replace(".", ","))
            self.lb_muc_tt.setStyleSheet("color:#7CC4FF")

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
        # CÁCH TRỘN cũng đọc từ COMBO ĐANG HIỆN, và đi qua `chuan_cach_tron` —
        # cửa DUY NHẤT chuẩn hoá: không nhận ra thì lùi về cách CŨ, không lùi về
        # cách mới (lùi về cái mới là âm thầm đổi tiếng của video người ta).
        cc_de = TG.chuan_cach_tron(self.cb_tron.currentData()) == "de"
        # HAI Ô ÂM LƯỢNG cũng đọc từ Ô ĐANG HIỆN (cùng lý do trên), qua cửa
        # duy nhất `muc_am_luong`. (0,0 · 0,0) = mặc định -> `xep_mot` KHÔNG
        # ghi khoá nào vào payload, khoá chống trùng giống TỪNG KÝ TỰ bản trước.
        cc_nen_db, cc_giong_db = self.muc_am_luong()

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
                    hinh_theo_giong=cc_hinh, de_giong=cc_de,
                    muc_nen_db=cc_nen_db, muc_giong_db=cc_giong_db)
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
        # Lượt tải Kokoro cũng phải thấy được tiến độ. KHÔNG có nhánh này thì
        # thanh hiện ra rồi ĐỨNG IM ở 1% suốt vài phút — đúng cái anh Hùng đã
        # kêu ở hộp này ("ấn chạy thì chỉ hiện thanh tiến trình, không hiện gì
        # cả"), chỉ đổi chỗ.
        if self._dang_cai_kokoro:
            b = getattr(self, "_buoc_kokoro", {"p": 0.0, "m": ""})
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
