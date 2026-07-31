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
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QLineEdit, QListWidget  # noqa: E402

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
nhan = lst.item(0).text()
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

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — ô tìm nằm trong danh sách, tìm được mọi nhóm")
sys.stdout.flush()
os._exit(0)
