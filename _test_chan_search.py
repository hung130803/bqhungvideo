# -*- coding: utf-8 -*-
# TÌM KÊNH — 3 lần sửa, ghi lại để đừng lặp (anh Hùng, 30-31/07):
#   v2.6.10: biến combo Kênh thành ô-gõ (editable+completer) => MẤT danh sách
#            bấm mở, không thấy tên kênh đang chọn ("này k mở được").
#   v2.6.12: tách ô "Lọc kênh" RIÊNG bên cạnh => vẫn sai, vì nó chỉ lọc TRONG
#            NHÓM đang chọn; 100 kênh nằm ở 3 nhóm nên gõ tên kênh nhóm khác
#            không ra gì ("có hoạt động đâu").
#   v2.6.18 (bản này): BẤM combo -> popup gồm [Ô TÌM] + [DANH SÁCH]; gõ là tìm
#            TRÊN MỌI NHÓM; chọn kênh nhóm khác thì TỰ ĐỔI NHÓM theo.
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="chan_pick_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

import app.queue.jobs  # noqa: F401,E402
from PyQt6.QtCore import QEvent, Qt  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QLineEdit,  # noqa: E402
                             QListWidget, QPushButton)

qapp = QApplication(sys.argv)
from app.database.db import db  # noqa: E402
from app import services  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# 3 nhóm — GIỐNG máy anh Hùng (kênh cần tìm nằm ở nhóm KHÁC nhóm đang chọn)
KENH = [("Utah Armwrestling", "Mỹ"), ("Bodycam Decoded Review", "Mỹ"),
        ("camX", "Mỹ"), ("Pepe's Towing Service", "Mỹ mới"),
        ("WhistlinDiesel", "Mỹ mới"), ("Ron Pratt", "Nhật")]
for ten, grp in KENH:
    db.execute("INSERT INTO projects(name,assets_dir,grp) VALUES(?,?,?)",
               (ten, os.path.join(T, ten), grp))

pg = StudioPage(AppState())
pg.show()
qapp.processEvents()
cb = pg.proj

print("== 1. combo VẪN là danh sách bấm mở (không phải ô gõ) ==")
kiem(not cb.isEditable(), "combo Kênh KHÔNG editable")
kiem(cb.currentText().strip() != "", "ô hiện ĐÚNG tên kênh đang chọn",
     repr(cb.currentText()))
kiem(not hasattr(pg, "proj_filter"),
     "đã BỎ ô 'Lọc kênh' rời bên ngoài (thứ anh Hùng nói không hoạt động)")

print("== 2. services.search_channels: tìm TRÊN MỌI NHÓM ==")
r = services.search_channels("cam")
tens = [x["name"] for x in r]
kiem("camX" in tens and "Bodycam Decoded Review" in tens,
     "gõ 'cam' ra cả camX lẫn Bodycam (khớp chứa-chuỗi)", str(tens))
kiem(tens and tens[0] == "camX",
     "kênh BẮT ĐẦU bằng chuỗi tìm xếp TRƯỚC", str(tens))
r2 = services.search_channels("PEPE")
kiem([x["name"] for x in r2] == ["Pepe's Towing Service"],
     "gõ HOA vẫn ra (không phân biệt hoa/thường)", str(r2))
kiem((r2[0]["grp"] if r2 else "") == "Mỹ mới",
     "trả kèm TÊN NHÓM để hiện cho user biết kênh ở nhóm nào")
kiem(services.search_channels("") == [], "chuỗi rỗng -> [] (không quét vô ích)")
kiem(services.search_channels("zzz-khong-co") == [],
     "không khớp -> [] (không trả bừa)")

print("== 3. BẤM combo -> popup có Ô TÌM + DANH SÁCH ==")
pop = pg._open_chan_picker()
qapp.processEvents()
ed, lst = pg._chan_pop_ed, pg._chan_pop_lst
kiem(isinstance(ed, QLineEdit) and isinstance(lst, QListWidget),
     "popup có ô nhập + danh sách")
kiem("tìm" in (ed.placeholderText() or "").lower(),
     "ô tìm nằm NGAY TRÊN ĐẦU danh sách", ed.placeholderText())
n_grp = len([1 for _, g in KENH if g == "Mỹ"])
kiem(lst.count() == n_grp,
     f"chưa gõ gì -> hiện đúng {n_grp} kênh của nhóm đang chọn",
     f"{lst.count()} dòng")

print("== 4. gõ vào popup -> ra kênh Ở NHÓM KHÁC (điểm anh Hùng cần) ==")
ed.setText("pepe")
qapp.processEvents()
kiem(lst.count() == 1, "tìm ra đúng 1 kênh", f"{lst.count()}")
from PyQt6.QtWidgets import QLabel as _QL


def _nhan_dong(l, i):
    w = l.itemWidget(l.item(i))
    if w is None:
        return l.item(i).text()
    lbs = w.findChildren(_QL)
    return lbs[0].text() if lbs else ""


nhan = _nhan_dong(lst, 0)
kiem("Pepe" in nhan, "đúng kênh Pepe's Towing Service", nhan)
kiem("nhóm Mỹ mới" in nhan,
     "nhãn nói rõ kênh này Ở NHÓM KHÁC (Mỹ mới)", nhan)

print("== 5. chọn kênh nhóm khác -> TỰ ĐỔI NHÓM + chọn đúng kênh ==")
pid_pepe = lst.item(0).data(Qt.ItemDataRole.UserRole)
lst.itemClicked.emit(lst.item(0))          # giả lập bấm chuột
qapp.processEvents()
kiem(pg.state.project_id == pid_pepe,
     "app đã chuyển sang ĐÚNG kênh vừa chọn",
     f"state={pg.state.project_id} pepe={pid_pepe}")
kiem(pg._cur_group() == "Mỹ mới", "NHÓM tự đổi sang 'Mỹ mới'",
     str(pg._cur_group()))
kiem(cb.currentData() == pid_pepe, "combo trỏ đúng kênh mới",
     str(cb.currentData()))

print("== 6. không khớp gì -> báo rõ, không rỗng trơ ==")
pop = pg._open_chan_picker()
qapp.processEvents()
pg._chan_pop_ed.setText("zzz-khong-co-that")
qapp.processEvents()
kiem(pg._chan_pop_lst.count() == 1
     and "không có kênh nào khớp" in pg._chan_pop_lst.item(0).text(),
     "hiện dòng '(không có kênh nào khớp)'",
     pg._chan_pop_lst.item(0).text() if pg._chan_pop_lst.count() else "(rỗng)")
pop.close()

print("== 7. Enter chọn dòng đầu (khỏi phải bấm chuột) ==")
pop = pg._open_chan_picker()
qapp.processEvents()
pg._chan_pop_ed.setText("whistlin")
qapp.processEvents()
pid_w = pg._chan_pop_lst.item(0).data(Qt.ItemDataRole.UserRole)
pg._chan_pop_ed.returnPressed.emit()
qapp.processEvents()
kiem(pg.state.project_id == pid_w, "Enter -> chọn luôn kênh khớp đầu tiên",
     f"state={pg.state.project_id} w={pid_w}")


print("== 8. popup KHÔNG tự đóng khi mất focus / sang app khác ==")
pop = pg._open_chan_picker()
qapp.processEvents()
kiem(pop.isVisible(), "popup đang mở")
fl = pop.windowFlags()
_kieu = fl & Qt.WindowType.WindowType_Mask
kiem(_kieu != Qt.WindowType.Popup,
     "KIỂU cửa sổ KHÔNG phải Qt.Popup (kiểu đó Qt tự đóng khi mất focus — "
     "đúng lỗi anh Hùng báo)", str(_kieu))
kiem(_kieu == Qt.WindowType.Tool, "kiểu Tool: cửa sổ con đi theo app, "
     "không tự đóng", str(_kieu))
# giả lập: bấm sang widget khác trong app + app mất/được focus lại
from PyQt6.QtWidgets import QLineEdit as _LE2
khac = _LE2(pg); khac.show(); khac.setFocus(); qapp.processEvents()
kiem(pop.isVisible(), "bấm sang chỗ khác TRONG app -> popup VẪN mở")
pg.window().activateWindow(); qapp.processEvents()
from PyQt6.QtGui import QFocusEvent as _FE
qapp.sendEvent(pop, _FE(QEvent.Type.WindowDeactivate))
qapp.processEvents()
kiem(pop.isVisible(), "app mất focus (sang trình duyệt) -> popup VẪN mở")
qapp.sendEvent(pop, _FE(QEvent.Type.WindowActivate)); qapp.processEvents()
kiem(pop.isVisible(), "quay lại app -> popup VẪN còn đó (không phải mở lại)")

print("== 9. đóng CHỦ ĐỘNG: Esc + nút ✕ ==")
from PyQt6.QtGui import QKeySequence as _KS, QShortcut as _SC
sc = [c for c in pop.findChildren(_SC)
      if c.key() == _KS("Esc")]
kiem(bool(sc), "có phím tắt Esc để đóng")
xb = [b for b in pop.findChildren(QPushButton) if b.text() == "Đóng"]
kiem(len(xb) == 1, "có đúng 1 nút Đóng (CHỮ)", str(len(xb)))
xb[0].click(); qapp.processEvents()
kiem(not pop.isVisible(), "bấm Đóng -> popup đóng")

print("== 10. NÚT COPY tên kênh ở TỪNG dòng ==")
pop = pg._open_chan_picker(); qapp.processEvents()
lst = pg._chan_pop_lst
n_row = lst.count()
kiem(n_row >= 2, f"có {n_row} dòng kênh (nhóm hiện tại)")
w0 = lst.itemWidget(lst.item(0))
kiem(w0 is not None, "dòng đầu có widget riêng (nhãn + nút copy)")
cps = [b for b in w0.findChildren(QPushButton) if b.text() == "Copy"]
kiem(len(cps) == 1, "mỗi dòng có ĐÚNG 1 nút Copy (CHỮ, không emoji)", str(len(cps)))
thieu = [i for i in range(n_row)
         if not [b for b in (lst.itemWidget(lst.item(i)) or w0).findChildren(
             QPushButton) if b.text() == "Copy"]]
kiem(not thieu, "MỌI dòng đều có nút Copy", f"dòng thiếu: {thieu}")

print("== 11. bấm copy: đúng TÊN GỐC, không đổi kênh, không đóng ==")
QApplication.clipboard().clear()
pid_truoc, n_truoc = pg.state.project_id, lst.count()
ten_goc = lst.item(0).data(Qt.ItemDataRole.UserRole + 1)
cps[0].click(); qapp.processEvents()
kiem(QApplication.clipboard().text() == ten_goc,
     f"clipboard = tên gốc kênh ({ten_goc!r})",
     repr(QApplication.clipboard().text()))
kiem("." not in QApplication.clipboard().text().split()[0]
     or not QApplication.clipboard().text()[0].isdigit(),
     "tên copy KHÔNG kèm số thứ tự '1. '", QApplication.clipboard().text())
kiem("⏳" not in QApplication.clipboard().text()
     and "✅" not in QApplication.clipboard().text(),
     "tên copy KHÔNG kèm đuôi trạng thái", QApplication.clipboard().text())
kiem(pg.state.project_id == pid_truoc, "bấm copy KHÔNG đổi kênh đang làm")
kiem(pop.isVisible(), "bấm copy KHÔNG đóng danh sách")
kiem(lst.count() == n_truoc, "danh sách không bị dựng lại")

print("== 12. copy ở dòng tìm được (kênh nhóm khác) ==")
pg._chan_pop_ed.setText("pepe"); qapp.processEvents()
w = lst.itemWidget(lst.item(0))
cp = [b for b in w.findChildren(QPushButton) if b.text() == "Copy"][0]
QApplication.clipboard().clear(); cp.click(); qapp.processEvents()
kiem(QApplication.clipboard().text() == "Pepe's Towing Service",
     "copy đúng tên kênh ở nhóm khác (không kèm '· nhóm Mỹ mới')",
     repr(QApplication.clipboard().text()))

print("== 13. chọn kênh vẫn chạy + không rò rỉ widget sau 30 lần ==")
lst.itemClicked.emit(lst.item(0)); qapp.processEvents()
kiem(not pop.isVisible(), "chọn kênh -> popup đóng")
kiem(pg._cur_group() == "Mỹ mới", "vẫn tự đổi nhóm khi chọn kênh nhóm khác",
     str(pg._cur_group()))
import gc
from PyQt6.QtWidgets import QFrame as _QF
for _ in range(30):
    p2 = pg._open_chan_picker(); qapp.processEvents(); p2.close(); qapp.processEvents()
gc.collect(); qapp.processEvents()
n_pop = len([w for w in pg.findChildren(_QF) if w.objectName() == "chanPick"])
kiem(n_pop <= 2, f"30 lần mở/đóng -> chỉ {n_pop} popup (dùng lại, không rò rỉ)",
     str(n_pop))


print("== 14. nút trong popup KHÔNG được dùng emoji (máy thiếu glyph = ô đen) ==")
pop = pg._open_chan_picker(); qapp.processEvents()
_emoji_xau = ("📋", "✕", "❌", "🗑", "📄", "⧉")
_nut = [b.text() for b in pop.findChildren(QPushButton)]
_co_emoji = [t for t in _nut if any(e in t for e in _emoji_xau)]
kiem(not _co_emoji, "mọi nút trong popup là CHỮ, không emoji dễ thiếu font",
     f"còn emoji: {_co_emoji}")
kiem("Copy" in _nut and "Đóng" in _nut,
     "có nút 'Copy' + 'Đóng' bằng chữ", str(sorted(set(_nut))))
_w0 = pg._chan_pop_lst.itemWidget(pg._chan_pop_lst.item(0))
_cp0 = [b for b in _w0.findChildren(QPushButton) if b.text() == "Copy"][0]
kiem(_cp0.width() >= 40 and "color" in (_cp0.styleSheet() or ""),
     "nút Copy đủ rộng + có màu chữ rõ (không chìm vào nền)",
     f"w={_cp0.width()} style={(_cp0.styleSheet() or '')[:40]}")
pop.close()

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — ô tìm nằm trong danh sách, tìm được mọi nhóm")
sys.stdout.flush()
os._exit(0)
