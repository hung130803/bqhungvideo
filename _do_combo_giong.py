# -*- coding: utf-8 -*-
"""ĐO Ô DANH SÁCH GIỌNG: BAO NHIÊU NHÃN BỊ CẮT · CHỤP ẢNH ĐỂ NHÌN TẬN MẮT.

 · `BQ_DO_KIEU=combo`  -> popup MẶC ĐỊNH của combo (đường của bản TRƯỚC)
 · `BQ_DO_KIEU=picker` -> hộp CHỌN GIỌNG có ô tìm (đường của bản SAU)

THƯỚC "BỊ CẮT" — VÀ VÌ SAO KHÔNG DÙNG `sizeHint` CỦA DELEGATE:
bản đầu của phép đo này hỏi `itemDelegate().sizeHint(opt, idx).width()`, vì
`QStyledItemDelegate` elide chữ khi ô hẹp hơn sizeHint. **SAI Ở COMBO**: view
của `QComboBox` dùng `QComboBoxDelegate` trả bề rộng ĐỒNG NHẤT cho mọi dòng —
đo ra **851 px cho CẢ dòng 1 ký tự LẪN dòng 600 ký tự**, tức 100% dòng "bị
cắt" cho một lý do không có thật. Thước đúng là bề rộng chữ THẬT:
`fontMetrics().horizontalAdvance(nhãn)` so với chỗ còn cho chữ trong ô. Phép đo
có mục **TỰ KIỂM BỘ DÒ** (một nhãn ngắn phải KHÔNG bị cắt, một nhãn 600 ký tự
phải BỊ cắt) — thiếu nó thì bảng số chỉ là con dấu.

ĐO Ở HAI BỀ RỘNG, cố ý:
 · `THAT`  = bề rộng ô danh sách ĐANG hiện trong phép đo này (màn hình ảo của
   Qt offscreen chỉ 800x800 nên số này bị TRẦN màn hình chặn);
 · `CHUAN` = bề rộng app CÓ THỂ dùng trên máy anh Hùng (cửa sổ hộp 946 px trừ
   lề) — số này KHÔNG phụ thuộc màn hình ảo nên hai bản so được với nhau.

BẪY ĐÃ BIẾT, ĐÃ TRÁNH: offscreen Qt có 0 họ phông -> ảnh ra Ô VUÔNG TOFU (phải
trỏ `QT_QPA_FONTDIR`, và đếm điểm ảnh KHÔNG phát hiện được tofu -> phải MỞ ẢNH
RA NHÌN) · PHẢI ÁP QSS THẬT (QSS đổi padding, padding là phần trừ vào chỗ chữ).

    .venv\\Scripts\\python -u _do_combo_giong.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
T = Path(tempfile.mkdtemp(prefix="docombo_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _test_guard  # noqa: E402,F401

from PyQt6.QtCore import QSize  # noqa: E402
from PyQt6.QtGui import QFontDatabase, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QMessageBox.exec = lambda self: 0                          # type: ignore
QMessageBox.warning = staticmethod(lambda *a, **k: 0)      # type: ignore
QMessageBox.information = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.critical = staticmethod(lambda *a, **k: 0)     # type: ignore

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
_app.setStyleSheet(theme.QSS)                    # QSS THẬT (bài học cổng 9)

import app.ui.thay_giong_dialog as TGD  # noqa: E402
from app.core.dubbing import list_recap_voices  # noqa: E402

KIEU = os.environ.get("BQ_DO_KIEU", "combo")
NHAN_ANH = os.environ.get("BQ_DO_ANH", f"_ANH_GIONG_{KIEU.upper()}.png")

#: Lề mà `QCommonStyle` chừa hai bên chữ trong một dòng danh sách.
LE_CHU = 6
#: Bề rộng "CHUẨN" = cửa sổ hộp Thay giọng (946 px trên máy anh Hùng) trừ lề.
RONG_CHUAN = 906 - LE_CHU

print(f"họ phông offscreen: {len(QFontDatabase.families())} "
      f"(0 = ảnh sẽ ra ô vuông tofu)")

TGD._CACHE_GIONG[:] = list_recap_voices()
print(f"danh sách giọng thật: {len(TGD._CACHE_GIONG)} dòng")

dlg = TGD.ThayGiongDialog(None, None)
dlg.show()
_app.processEvents()
print(f"hộp thoại: {dlg.width()}x{dlg.height()} · combo giọng rộng "
      f"{dlg.cb_giong.width()} px · màn hình ảo "
      f"{_app.primaryScreen().availableGeometry().width()} px")

if KIEU == "combo":
    cb = dlg.cb_giong
    cb.showPopup()
    _app.processEvents()
    view = cb.view()
    nhan = [cb.itemText(i) for i in range(cb.count())]
else:
    pop = dlg._mo_chon_giong()
    _app.processEvents()
    view = dlg._gp_lst
    nhan = [view.item(i).text() for i in range(view.count())]
    print(f"hộp chọn giọng: {pop.width()}x{pop.height()} px")

fm = view.fontMetrics()
# **BỀ RỘNG APP BẢO ĐẢM** — con số duy nhất so được giữa hai bản mã.
# Màn hình ảo của Qt offscreen chỉ 800x800, mà `QComboBox` tự nới popup tới
# TRẦN MÀN HÌNH; nên đo "bề rộng popup đang hiện" là đo MÀN HÌNH ẢO, không đo
# bản vá. Cái bản vá đổi là con số app TỰ ĐẶT: `view().setMinimumWidth(...)`.
# Bản TRƯỚC không đặt gì -> minimumWidth = 0 -> popup bám theo WIDGET (300 px),
# đúng bề rộng trong ảnh anh Hùng chụp (nhãn nhóm 53 ký tự bị cắt giữa câu chỉ
# xảy ra ở bề rộng đó).
if KIEU == "combo":
    bao_dam = max(view.minimumWidth(), dlg.cb_giong.width()) - LE_CHU
    print(f"  view().minimumWidth() = {view.minimumWidth()} px "
          f"(0 = app không đặt gì -> popup bám theo combo)")
else:
    bao_dam = view.viewport().width() - LE_CHU
rong = {
    # Chỗ cho chữ mà app BẢO ĐẢM có, trên MÁY NÀY.
    "BẢO ĐẢM": bao_dam,
    # Chỗ cho chữ trên MÁY ANH HÙNG (màn hình rộng -> trần là CỬA SỔ 946 px).
    "MÁY A.HÙNG": RONG_CHUAN,
}

# ---- TỰ KIỂM BỘ DÒ: thiếu mục này thì bảng số dưới chỉ là con dấu ----
tk_ngan = fm.horizontalAdvance("Nam Minh") <= min(rong.values())
tk_dai = fm.horizontalAdvance("x" * 600) > max(rong.values())
print(f"\nTỰ KIỂM BỘ DÒ: nhãn ngắn KHÔNG cắt = {tk_ngan} · "
      f"nhãn 600 ký tự BỊ cắt = {tk_dai} "
      f"({'DÙNG ĐƯỢC' if tk_ngan and tk_dai else 'BỘ DÒ HỎNG'})")

print(f"\nKIỂU ĐO: {KIEU} · {len(nhan)} dòng")
for ten, r in rong.items():
    cat = [n for n in nhan if fm.horizontalAdvance(n) > r]
    print(f"  [{ten}] chỗ cho chữ {r:4d} px -> BỊ CẮT {len(cat):3d}/{len(nhan)}"
          f" ({100.0 * len(cat) / max(1, len(nhan)):5.1f}%)")
    for n in sorted(cat, key=lambda s: -fm.horizontalAdvance(s))[:4]:
        print(f"      thiếu {fm.horizontalAdvance(n) - r:5d} px · {len(n):3d} "
              f"ký tự · {n[:88]}")
tu_rut = [n for n in nhan if "…" in n]
print(f"  dòng app TỰ rút gọn (có dấu …, chi tiết ở tooltip): {len(tu_rut)}")
print(f"  dòng có ghi 'rê chuột xem thêm': "
      f"{sum(1 for n in nhan if 'rê chuột xem thêm' in n)}")
print(f"  nhãn dài nhất: {max(len(n) for n in nhan)} ký tự · "
      f"{max(fm.horizontalAdvance(n) for n in nhan)} px")

# CHẤM `nhan_gon` Ở TRẦN CỦA MÁY ANH HÙNG — màn hình ảo 800 px của phép đo này
# ép trần hẹp hơn máy thật, nên số "app tự rút gọn" ở trên nói NẶNG hơn sự thật.
# Gọi thẳng hàm thuần ở trần 858 px (cửa sổ 946 - 44 lề - 44 chỗ thanh cuộn).
from app.core import giong_bang as GB  # noqa: E402
goc = [n for n, v in GB.gom_nhom(
    TGD.giong_dung_duoc(TGD._CACHE_GIONG),
    str(dlg.cb_nn.currentData() or "en"), loi_tat=True) if v]
for tr in (858, RONG_CHUAN - 44):
    g = [TGD.nhan_gon(n, fm, tr) for n in goc]
    print(f"  [nhan_gon ở trần {tr} px] {len(goc)} dòng giọng -> "
          f"bị Qt cắt {sum(1 for x in g if fm.horizontalAdvance(x) > tr)} · "
          f"app tự rút {sum(1 for x in g if '…' in x)} · "
          f"dài nhất {max(fm.horizontalAdvance(x) for x in g)} px")

# ẢNH: render viewport ra PNG để NGƯỜI TỰ NHÌN
kh = view.viewport()
h = min(kh.height(), 620)
img = QImage(QSize(kh.width(), h), QImage.Format.Format_ARGB32)
img.fill(0xFF101827)
p = QPainter(img)
kh.render(p)
p.end()
img.save(str(Path(REPO) / NHAN_ANH))
print(f"\nảnh: {NHAN_ANH} ({kh.width()}x{h})")
