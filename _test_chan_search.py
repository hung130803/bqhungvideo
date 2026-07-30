# -*- coding: utf-8 -*-
# Ô 🔎 LỌC KÊNH ở màn hình chính (anh Hùng 30/07: "dò từng kênh mệt quá").
#
# BÀI HỌC v2.6.10-11: lần đầu tôi biến chính combo Kênh thành ô-gõ (editable
# + completer) => anh Hùng MẤT danh sách bấm mở và không thấy tên kênh đang
# chọn ("này k mở được"). Nay tách đôi: combo VẪN là danh sách bấm mở, ô 🔎
# RIÊNG bên cạnh chỉ lọc bớt. Test canh đúng 2 điều đó + bất biến sống còn:
# LỌC KHÔNG ĐƯỢC ĐỔI KÊNH ĐANG LÀM.
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="chan_filter_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication, QLineEdit  # noqa: E402

qapp = QApplication(sys.argv)

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


TEN = ("Alpha News", "Beta Pickers", "Gamma Cars", "Delta Cook",
       "Alpha Sports", "Epsilon Cars")
for i, ten in enumerate(TEN, 1):
    db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,'')",
               (ten, os.path.join(T, f"a{i}")))

pg = StudioPage(AppState())
cb, ed = pg.proj, pg.proj_filter


def ten_dang_hien():
    return [cb.itemText(i) for i in range(cb.count())]


print("== 1. combo VẪN là danh sách bấm mở được (không thành ô gõ) ==")
kiem(not cb.isEditable(),
     "combo Kênh KHÔNG editable (bấm là mở danh sách như cũ)")
kiem(cb.count() == 6, "danh sách có đủ 6 kênh", str(cb.count()))
kiem(cb.currentText().endswith(TEN[0]),
     "ô hiện ĐÚNG TÊN kênh đang chọn (không phải chữ mờ gợi ý)",
     cb.currentText())
kiem(isinstance(ed, QLineEdit) and ed is not cb.lineEdit(),
     "ô lọc là widget RIÊNG, không phải ô nhập của combo")

print("== 2. gõ ô lọc -> danh sách chỉ còn kênh khớp ==")
pid_dau = pg.state.project_id
ed.setText("cars")
qapp.processEvents()
con = ten_dang_hien()
kiem(any("Gamma Cars" in t for t in con) and any("Epsilon Cars" in t for t in con),
     "lọc 'cars' ra ĐÚNG 2 kênh có chữ Cars", str(con))
kiem(not any("Beta Pickers" in t for t in con),
     "kênh không khớp bị ẩn khỏi danh sách", str(con))
kiem(len(con) <= 3, "danh sách gọn lại (2 khớp + tối đa kênh đang chọn)",
     str(con))

print("== 3. BẤT BIẾN: lọc KHÔNG được đổi kênh đang làm ==")
kiem(pg.state.project_id == pid_dau,
     "gõ lọc xong vẫn ở NGUYÊN kênh đang làm",
     f"{pid_dau} -> {pg.state.project_id}")
kiem(any(cb.itemData(i) == pid_dau for i in range(cb.count())),
     "kênh đang chọn LUÔN còn trong danh sách dù không khớp chữ lọc")
kiem(cb.currentData() == pid_dau, "combo vẫn trỏ đúng kênh đang làm",
     f"{cb.currentData()}")

print("== 4. không phân biệt hoa/thường + xoá chữ hiện lại hết ==")
ed.setText("ALPHA")
qapp.processEvents()
kiem(sum("Alpha" in t for t in ten_dang_hien()) == 2,
     "gõ HOA vẫn khớp 2 kênh Alpha", str(ten_dang_hien()))
ed.clear()
qapp.processEvents()
kiem(cb.count() == 6, "xoá ô lọc -> hiện lại ĐỦ 6 kênh", str(cb.count()))

print("== 5. đổi kênh bằng danh sách vẫn chạy (_on_proj) ==")
cb.setCurrentIndex(2)
qapp.processEvents()
kiem(pg.state.project_id == cb.currentData(),
     "chọn kênh trong danh sách -> app chuyển kênh ĐÚNG",
     f"state={pg.state.project_id} combo={cb.currentData()}")

print("== 6. lọc KHÔNG khớp gì -> vẫn còn kênh đang chọn, không rỗng ==")
ed.setText("zzzz-khong-co")
qapp.processEvents()
kiem(cb.count() == 1 and cb.currentData() == pg.state.project_id,
     "không kênh nào khớp -> danh sách còn đúng kênh đang làm",
     f"{cb.count()} item")
ed.clear()
qapp.processEvents()

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — danh sách mở được + ô lọc riêng, không đổi kênh oan")
os._exit(0)
