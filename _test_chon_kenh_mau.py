# -*- coding: utf-8 -*-
"""CỔNG 29 — SAU KHI LƯU MẪU: chọn ĐÚNG kênh muốn đổi, đừng đổi hết.

Anh Hùng 06/08/2026 (kèm ảnh hộp thoại "19 kênh đang gán mẫu RIÊNG…"):
"những nhóm tôi k muốn chỉnh thay cái mẫu đó thì làm như nào hay những kênh
trong đó k muốn thay cái mẫu mới thì sao".

Hộp cảnh báo bản đầu chỉ có 2 đường: GÁN HẾT / ĐỂ NGUYÊN. Với 200+ kênh chia
nhiều nhóm thì gán hết là phá mẫu nhóm khác. Nay có đường thứ 3: TÍCH Ô từng
kênh, có ô tìm theo nhóm, 2 nút chọn nhanh CHỈ ĐỤNG PHẦN ĐANG LỌC.

Kèm 1 lỗi thật của bản đầu: nó tra id kênh THEO TÊN -> 2 kênh TRÙNG TÊN là gán
mẫu cho kênh SAI.
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="chonkenh_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  ✅ {ten}" + (f" — {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} — {ct}")
        print(f"  ❌ {ten} — {ct}")


from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDialog, QLineEdit,  # noqa: E402
                             QListWidget, QMessageBox, QPushButton)

# CHẶN mọi hộp thoại modal (không có thì test treo vĩnh viễn)
_DLG: list = []
QDialog.exec = lambda self: (_DLG.append(self), 0)[1]
_MB: list = []
QMessageBox.exec = lambda self: (_MB.append(self), 0)[1]
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.information = staticmethod(lambda *a, **k: 0)

_app = QApplication.instance() or QApplication([])
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

_app.setStyleSheet(theme.QSS)      # QSS THẬT (bài học cổng 9: QSS bóp widget)

# ── dựng cảnh giống máy anh Hùng: 3 nhóm, có 2 kênh TRÙNG TÊN ──
for ten_m in ("chữ mới eng", "Chữ kiểu mới", "Mẫu nhóm Việt"):
    services.save_template(ten_m, {"cap_preset": "Trắng đơn giản",
                                   "video_rect": [0, 0, 1, 1]})
KENH = []
for i in range(8):        # nhóm Mỹ, đang dùng "Chữ kiểu mới"
    KENH.append((services.create_project(f"US Channel {i}", "Mỹ"),
                 "Mỹ", "Chữ kiểu mới"))
for i in range(6):        # nhóm Việt, đang dùng "Mẫu nhóm Việt"
    KENH.append((services.create_project(f"Kênh Việt {i}", "Việt"),
                 "Việt", "Mẫu nhóm Việt"))
# 2 kênh TRÙNG TÊN, khác nhóm, khác mẫu -> bẫy "tra id theo tên"
p_trung_a = services.create_project("Prison Doc", "Mỹ")
p_trung_b = services.create_project("Prison Doc", "Việt")
KENH.append((p_trung_a, "Mỹ", "Chữ kiểu mới"))
KENH.append((p_trung_b, "Việt", "Mẫu nhóm Việt"))
for pid, _g, tpl in KENH:
    services.set_project_template(pid, tpl)
GOC = {pid: tpl for pid, _g, tpl in KENH}
MOI = "chữ mới eng"

sp = StudioPage.__new__(StudioPage)
# PHẢI gọi QWidget.__init__ (không dựng UI đầy đủ vì chậm/treo trong sandbox,
# nhưng thiếu bước này thì QMessageBox(self) nổ "super-class __init__ never
# called").
from PyQt6.QtWidgets import QWidget as _QW  # noqa: E402
_QW.__init__(sp)
sp.layout_tpl = {"cap_preset": "Trắng đơn giản"}
sp.status = QPushButton("")
sp._pipe_fill = lambda: None


def _dat_lai():
    for pid, tpl in GOC.items():
        services.set_project_template(pid, tpl)


def _dem_moi():
    return sum(1 for pid in GOC
               if (services.project_template_name(pid) or "") == MOI)


def _mo_canh_bao():
    """Gọi hộp cảnh báo, trả về QMessageBox vừa dựng (đã chặn exec)."""
    _MB.clear()
    _DLG.clear()
    sp._canh_bao_mau_khong_ap(MOI)
    return _MB[-1] if _MB else None


def _nut(mb, chua: str):
    for b in mb.buttons():
        if chua.lower() in b.text().lower():
            return b
    return None


print("\n=== 1. Hộp cảnh báo phải có ĐỦ 3 đường ===")
mb = _mo_canh_bao()
ok(mb is not None, "1a hộp cảnh báo bật lên khi có kênh gán mẫu khác")
ok(_nut(mb, "chọn từng kênh") is not None, "1b có nút 'Chọn từng kênh…'")
ok(_nut(mb, "gán cho cả") is not None, "1c có nút 'Gán cho cả N kênh'")
ok(_nut(mb, "để nguyên") is not None, "1d có nút 'Để nguyên'")
ok(mb.defaultButton() is _nut(mb, "chọn từng kênh"),
   "1e nút MẶC ĐỊNH là đường AN TOÀN (bấm Enter không đổi hết)")
ok(f"{len(GOC)} kênh" in mb.text(),
   "1f nêu đúng SỐ kênh đang gán mẫu khác", f"{len(GOC)} kênh")
ok("Chọn từng kênh" in mb.text() and "GIỮ NGUYÊN" in mb.text(),
   "1g lời hộp thoại GIẢI THÍCH cả 3 đường (user không phải đoán)")

print("\n=== 2. 'Để nguyên' -> KHÔNG đụng kênh nào ===")
_dat_lai()
mb = _mo_canh_bao()
# vá clickedButton NGAY TRONG exec để mô phỏng "user bấm nút X"
_QMB_exec_goc = QMessageBox.exec


def _exec_bam(nhan):
    def _f(self):
        _MB.append(self)
        b = _nut(self, nhan)
        if b is not None:
            self.clickedButton = lambda: b
        return 0
    return _f


QMessageBox.exec = _exec_bam("để nguyên")
_dat_lai()
sp._canh_bao_mau_khong_ap(MOI)
ok(_dem_moi() == 0, "2a bấm 'Để nguyên' -> 0 kênh bị đổi", f"{_dem_moi()} kênh")

print("\n=== 3. 'Gán cho cả N kênh' -> đổi hết, đúng id (kênh TRÙNG TÊN) ===")
QMessageBox.exec = _exec_bam("gán cho cả")
_dat_lai()
sp._canh_bao_mau_khong_ap(MOI)
ok(_dem_moi() == len(GOC), "3a đổi đủ mọi kênh", f"{_dem_moi()}/{len(GOC)}")
ok((services.project_template_name(p_trung_a) or "") == MOI
   and (services.project_template_name(p_trung_b) or "") == MOI,
   "3b CẢ HAI kênh trùng tên đều đổi (bản cũ tra theo tên -> gán sai/thiếu)")

print("\n=== 4. 'Chọn từng kênh…' -> chỉ đổi kênh ĐÃ TÍCH ===")
QMessageBox.exec = _exec_bam("chọn từng kênh")
_dat_lai()
_DLG.clear()
sp._canh_bao_mau_khong_ap(MOI)
dlg = _DLG[-1] if _DLG else None
ok(dlg is not None, "4a hộp chọn kênh bật lên")
lst = dlg.findChild(QListWidget)
oti = dlg.findChild(QLineEdit)
ok(lst is not None and lst.count() == len(GOC),
   "4b liệt kê đủ kênh đang gán mẫu khác", f"{lst.count() if lst else 0} dòng")
ok(all(lst.item(i).checkState() == Qt.CheckState.Unchecked
       for i in range(lst.count())),
   "4c mặc định KHÔNG tích gì (an toàn)")
ok(oti is not None, "4d có Ô TÌM (200 kênh phải gõ-lọc được)")
_t0 = lst.item(0).text()
ok("nhóm" in _t0 and "đang dùng" in _t0,
   "4e mỗi dòng ghi rõ NHÓM + MẪU ĐANG DÙNG", _t0[:70])

print("\n=== 5. Lọc theo NHÓM rồi 'Chọn hết đang hiện' ===")
oti.setText("việt")
_app.processEvents()
_hien = [i for i in range(lst.count()) if not lst.item(i).isHidden()]
ok(len(_hien) == 7, "5a gõ 'việt' -> chỉ hiện 7 kênh nhóm Việt",
   f"{len(_hien)} dòng")
b_het = None
for b in dlg.findChildren(QPushButton):
    if "chọn hết đang hiện" in b.text().lower():
        b_het = b
b_het.click()
_tick = [i for i in range(lst.count())
         if lst.item(i).checkState() == Qt.CheckState.Checked]
ok(sorted(_tick) == sorted(_hien),
   "5b chỉ tích ĐÚNG phần đang hiện, nhóm Mỹ KHÔNG bị tích",
   f"tích {len(_tick)} = hiện {len(_hien)}")
oti.setText("")            # xoá lọc -> tích vẫn giữ nguyên 7 dòng
_app.processEvents()
_tick2 = [i for i in range(lst.count())
          if lst.item(i).checkState() == Qt.CheckState.Checked]
ok(len(_tick2) == 7, "5c xoá ô tìm -> vẫn đúng 7 kênh được tích",
   f"{len(_tick2)}")

print("\n=== 6. Áp dụng -> ĐÚNG 7 kênh đổi, phần còn lại NGUYÊN ===")
b_ok = None
for b in dlg.findChildren(QPushButton):
    if "đổi mẫu cho kênh đã tích" in b.text().lower():
        b_ok = b
b_ok.click()
_dem = _dem_moi()
ok(_dem == 7, "6a đúng 7 kênh đổi sang mẫu mới", f"{_dem} kênh")
_my_nguyen = all((services.project_template_name(pid) or "") == "Chữ kiểu mới"
                 for pid, g, _t in KENH if g == "Mỹ")
ok(_my_nguyen, "6b 9 kênh nhóm Mỹ GIỮ NGUYÊN mẫu «Chữ kiểu mới»")
ok((services.project_template_name(p_trung_b) or "") == MOI
   and (services.project_template_name(p_trung_a) or "") == "Chữ kiểu mới",
   "6c 2 kênh TRÙNG TÊN: chỉ kênh nhóm Việt đổi, kênh nhóm Mỹ nguyên "
   "(bản cũ tra theo tên sẽ sai chỗ này)")
ok("giữ mẫu cũ" in sp.status.text().lower(),
   "6d báo rõ cho user là kênh không chọn vẫn giữ mẫu cũ", sp.status.text())

print("\n=== 7. Không tích gì / bấm Đóng -> KHÔNG đổi ===")
_dat_lai()
QMessageBox.exec = _exec_bam("chọn từng kênh")
_DLG.clear()
sp._canh_bao_mau_khong_ap(MOI)
dlg2 = _DLG[-1]
for b in dlg2.findChildren(QPushButton):
    if "đổi mẫu cho kênh đã tích" in b.text().lower():
        b.click()          # chưa tích gì -> phải hỏi lại, không đổi
ok(_dem_moi() == 0, "7a chưa tích mà bấm Đổi -> KHÔNG đổi kênh nào",
   f"{_dem_moi()} kênh")
for b in dlg2.findChildren(QPushButton):
    if "đóng" in b.text().lower():
        b.click()
ok(_dem_moi() == 0, "7b bấm Đóng -> giữ nguyên tất cả")

print("\n=== 8. Không có kênh nào gán mẫu khác -> KHÔNG quấy user ===")
for pid in GOC:
    services.set_project_template(pid, MOI)
_MB.clear()
sp._canh_bao_mau_khong_ap(MOI)
ok(not _MB, "8a mọi kênh đã dùng mẫu đó -> không bật hộp thoại")
_MB.clear()
sp._canh_bao_mau_khong_ap("")
ok(not _MB, "8b tên mẫu rỗng -> không bật hộp thoại")

print("\n=== 9. Nhãn nút không dùng emoji dễ thiếu font ===")
_xau = [b.text() for b in dlg.findChildren(QPushButton)
        if any(ch in b.text() for ch in "👍👎📋✕")]
ok(not _xau, "9a nút trong hộp chọn kênh đều là CHỮ", str(_xau))

QMessageBox.exec = _QMB_exec_goc
print(f"\n{'='*60}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 29 ĐẠT — chọn đúng kênh/nhóm để đổi mẫu, không đổi bừa")
