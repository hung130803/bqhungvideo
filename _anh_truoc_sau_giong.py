# -*- coding: utf-8 -*-
"""ẢNH TRƯỚC/SAU của Ô DANH SÁCH GIỌNG — để NGƯỜI TỰ MỞ RA NHÌN.

Vì sao phải có file này dù cổng 84 đã xanh: cổng 84 chấm bằng SỐ ĐO
(`fontMetrics().horizontalAdvance(nhãn) > chỗ cho chữ`). Số đó **không phát
hiện được ô vuông tofu** — đo được tofu 2.431 px vs chữ thật 517 px, tức tofu
còn ăn NHIỀU HƠN chữ thật, nên một ảnh toàn ô vuông vẫn cho ra "0 nhãn bị cắt".
Cách duy nhất là mở ảnh ra xem.

**BA CHỐT BẮT BUỘC, thiếu một cái là ảnh vô giá trị:**

1. `QT_QPA_FONTDIR` trỏ `C:\\Windows\\Fonts`. Qt offscreen mặc định có **0 họ
   phông** -> mọi chữ ra ô vuông. Script DỪNG (mã 2) nếu đếm được ít họ.
2. `qapp.setStyleSheet(theme.QSS)` — QSS THẬT. QSS chung có
   `QListWidget::item{padding:9px 10px;margin:2px}` và `* {color: TEXT}` (đè lên
   `setForeground` của item). Chụp mà không áp nó là chụp một giao diện KHÔNG
   TỒN TẠI trên máy anh Hùng (lỗi thật v2.6.22).
3. **CHỤP ĐÚNG WIDGET USER THẤY.** `ComboGiong.showPopup` nay CHUYỂN HƯỚNG sang
   hộp tìm, nên `cb.showPopup()` rồi render `cb.view()` là chụp một widget
   **KHÔNG BAO GIỜ HIỆN** -> ra ảnh TRỐNG TRƠN. (Bản đầu của script này đã ra
   đúng hai ảnh trống, và số đo "0 nhãn bị cắt" vẫn xanh bên cạnh — nếu tin số
   mà không mở ảnh thì đã báo cáo một bức ảnh rỗng là bằng chứng.) Muốn chụp
   popup mặc định (nay là **đường LÙI** khi hộp tìm lỗi) phải gọi thẳng
   `QComboBox.showPopup(cb)`.

Bản TRƯỚC nạp **CHÍNH MÃ BẢN MỐC** `19de32e` (commit ngay TRƯỚC 4 bản vá) bằng
`git show`, chứ không phải "gỡ bản vá bằng monkey-patch" và cũng không đi tìm
ảnh cũ trên đĩa: ảnh cũ không biết chụp ở bề rộng nào, bằng bản mã nào, có QSS
hay không — so hai thứ khác điều kiện thì cái "khác nhau" đọc được có thể chỉ
là khác điều kiện chụp. Đã kiểm `19de32e` KHÔNG hề có `nhan_gon` /
`to_nhan_nhom` / `rong_vua_chu` / `_noi_rong_popup` (grep ra 0), tức mốc đúng
là bản chưa mang bản vá nào.

    .venv\\Scripts\\python -u _anh_truoc_sau_giong.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)      # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

#: Commit NGAY TRƯỚC 4 bản vá đang tự kiểm (4332367 · 8156dac · 574731c ·
#: e6738b3). **KHÔNG dùng `main`/`HEAD`** — sau khi gộp thì mốc chính là bản
#: đang test, ảnh TRƯỚC và SAU sẽ giống nhau và phép so mất hết ý nghĩa.
MOC = os.environ.get("BQ_MOC_GIONG", "19de32e").strip()

T = Path(tempfile.mkdtemp(prefix="anhgiong_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _test_guard  # noqa: E402,F401 - CẤM mở Explorer/trình phát

from PyQt6.QtCore import QSize  # noqa: E402
from PyQt6.QtGui import QFontDatabase, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QComboBox, QMessageBox,
)

for _n in ("warning", "information", "critical"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))
QMessageBox.exec = lambda self: 0                          # type: ignore

app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
app.setStyleSheet(theme.QSS)                # QSS THẬT — chốt số 2

import app.ui.thay_giong_dialog as TGD  # noqa: E402
from app.core.dubbing import list_recap_voices  # noqa: E402

ho = len(QFontDatabase.families())
print(f"họ phông: {ho}")
if ho <= 20:
    print("DỪNG: 0 họ phông -> ảnh sẽ toàn ô vuông tofu, chụp ra là số rác.")
    sys.exit(2)

TGD._CACHE_GIONG[:] = list_recap_voices()
print(f"danh sách giọng thật: {len(TGD._CACHE_GIONG)} dòng")

NEN = 0xFF101827


def _luu(target, ten: str, cao: int = 620) -> int:
    """Render widget ra PNG, trả về SỐ ĐIỂM ẢNH KHÁC MÀU NỀN.

    Con số đó là chốt chống "ảnh trống trơn": nó KHÔNG thay được việc mở ảnh ra
    nhìn (không phân biệt được chữ thật với ô vuông tofu) nhưng nó bắt được ca
    chụp nhầm widget chưa bao giờ hiện.
    """
    img = QImage(QSize(max(target.width(), 1), min(target.height(), cao)),
                 QImage.Format.Format_ARGB32)
    img.fill(NEN)
    p = QPainter(img)
    target.render(p)
    p.end()
    img.save(str(Path(REPO) / ten))
    n = sum(1 for y in range(0, img.height(), 2)
            for x in range(0, img.width(), 2) if img.pixel(x, y) != NEN)
    return n


def _dem_cat(cb, rong: int) -> list[str]:
    fm = cb.view().fontMetrics()
    return [cb.itemText(k) for k in range(cb.count())
            if fm.horizontalAdvance(cb.itemText(k)) > rong]


def chup(lop, ten: str, nn: str, picker: bool = False) -> None:
    dlg = lop(None, None)
    dlg.show()
    i = dlg.cb_nn.findData(nn)
    if i >= 0:
        dlg.cb_nn.setCurrentIndex(i)
    app.processEvents()
    cb = dlg.cb_giong
    if picker:
        # ĐƯỜNG USER THẬT SỰ ĐI sau VIỆC 2: bấm combo -> hộp [ô tìm + danh sách]
        pop = dlg._mo_chon_giong()
        app.processEvents()
        n = _luu(pop, ten)
        print(f"{ten}: hộp tìm {pop.width()}x{pop.height()} · "
              f"điểm khác nền {n}")
        pop.close()
    else:
        # popup MẶC ĐỊNH của combo. Phải gọi THẲNG hàm của lớp cha, vì
        # `ComboGiong.showPopup` đã chuyển hướng sang hộp tìm.
        QComboBox.showPopup(cb)
        app.processEvents()
        vw = cb.view()
        n = _luu(vw, ten)
        cho = vw.width() - 6            # lề chữ QCommonStyle chừa 2 bên
        cat = _dem_cat(cb, cho)
        print(f"{ten}: popup {vw.width()} px · chỗ cho chữ {cho} px · "
              f"NHÃN BỊ CẮT {len(cat)}/{cb.count()} · điểm khác nền {n}"
              + (f"\n    tệ nhất: «{cat[0][:78]}»" if cat else ""))
        cb.hidePopup()
    dlg.close()
    app.processEvents()


# ── nạp lớp hộp thoại của BẢN MỐC ──────────────────────────────────────────
r = subprocess.run(["git", "show", f"{MOC}:app/ui/thay_giong_dialog.py"],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", cwd=REPO, timeout=120)
if r.returncode != 0 or not (r.stdout or "").strip():
    print("DỪNG: không đọc được bản mốc " + MOC + " — " + (r.stderr or "")[-200:])
    sys.exit(2)
if (r.stdout or "").replace("\r\n", "\n") == \
        Path(REPO, "app/ui/thay_giong_dialog.py").read_text(
            encoding="utf-8").replace("\r\n", "\n"):
    # chốt chống so-nó-với-chính-nó
    print("DỪNG: mốc " + MOC + " TRÙNG bản đang test -> ảnh TRƯỚC/SAU vô nghĩa.")
    sys.exit(2)
f_moc = T / "_tgd_moc.py"
f_moc.write_text(r.stdout, encoding="utf-8")
spec = importlib.util.spec_from_file_location("_tgd_moc", str(f_moc))
MOCMOD = importlib.util.module_from_spec(spec)
sys.modules["_tgd_moc"] = MOCMOD
spec.loader.exec_module(MOCMOD)
MOCMOD._CACHE_GIONG[:] = list(TGD._CACHE_GIONG)
print(f"bản mốc {MOC} nạp xong\n")

for nn in ("en", "vi"):
    print(f"── ngôn ngữ đích: {nn} ──")
    chup(MOCMOD.ThayGiongDialog, f"_ANH_TRUOC_{nn}.png", nn)
    chup(TGD.ThayGiongDialog, f"_ANH_SAU_{nn}.png", nn)
    chup(TGD.ThayGiongDialog, f"_ANH_SAU_TIM_{nn}.png", nn, picker=True)

import shutil  # noqa: E402
shutil.rmtree(T, ignore_errors=True)
sys.stdout.flush()
# `os._exit`: nhiều hộp thoại parent `None` + cửa sổ `Tool` con làm Qt nổ trong
# C++ lúc trình thông dịch dọn dẹp (đo được mã thoát 139 = SEGFAULT ở cổng 84).
os._exit(0)
