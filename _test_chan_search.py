# -*- coding: utf-8 -*-
# Ô KÊNH GÕ-ĐỂ-TÌM ở màn hình chính (anh Hùng 30/07: "dò từng kênh mệt quá,
# thêm tìm kiếm ở ngoài"). Rủi ro: combo thành editable có thể phá _on_proj
# (đổi kênh) hoặc kẹt chữ lạ trong ô. Test đúng các nguy cơ đó.
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="chan_search_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

import app.queue.jobs  # noqa: F401,E402

from PyQt6.QtWidgets import QApplication, QCompleter  # noqa: E402

qapp = QApplication(sys.argv)

from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage, _ChanCombo  # noqa: E402

FAIL: list = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# 5 kênh giả để có cái mà tìm
for i, ten in enumerate(("Alpha News", "Beta Pickers", "Gamma Cars",
                         "Delta Cook", "Alpha Sports"), 1):
    db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,'')",
               (ten, os.path.join(T, f"a{i}")))

pg = StudioPage(AppState())
combo = pg.proj

print("== 1. combo có khả năng gõ-tìm ==")
kiem(isinstance(combo, _ChanCombo), "combo Kênh là _ChanCombo")
kiem(combo.isEditable(), "combo cho GÕ (editable)")
comp = combo.completer()
kiem(isinstance(comp, QCompleter), "có completer")
from PyQt6.QtCore import Qt
kiem(comp.filterMode() == Qt.MatchFlag.MatchContains,
     "khớp CHỨA-chuỗi (gõ 'car' ra 'Gamma Cars')")
kiem(comp.caseSensitivity() == Qt.CaseSensitivity.CaseInsensitive,
     "không phân biệt hoa/thường")

print("== 2. đổi kênh vẫn chạy (currentData -> _on_proj) ==")
n = combo.count()
kiem(n == 5, "nạp đủ 5 kênh", f"{n}")
# chọn kênh thứ 3 bằng index (như completer chọn xong sẽ làm)
combo.setCurrentIndex(2)
pid = combo.currentData()
kiem(pid is not None, "currentData trả pid sau khi chọn", str(pid))
kiem(pg.state.project_id == int(pid),
     "state.project_id đổi ĐÚNG theo kênh chọn (_on_proj chạy)",
     f"state={pg.state.project_id} pid={pid}")

print("== 3. gõ chữ LẠ rồi rời ô -> không kẹt, không đổi kênh ==")
truoc = pg.state.project_id
le = combo.lineEdit()
le.setText("xyz không có kênh nào")
le.editingFinished.emit()          # giả lập rời ô
kiem(le.text() == combo.itemText(combo.currentIndex()),
     "ô tự trả về tên kênh đang chọn (không kẹt chữ lạ)", le.text())
kiem(pg.state.project_id == truoc,
     "gõ bừa KHÔNG đổi kênh đang chọn", f"{truoc}->{pg.state.project_id}")

print("== 4. nạp lại danh sách (đổi nhóm) không mất khả năng tìm ==")
pg._reload_projects()
kiem(combo.isEditable() and isinstance(combo.completer(), QCompleter),
     "sau reload vẫn editable + còn completer")
kiem(combo.completer().model() is combo.model(),
     "completer vẫn trỏ đúng model của combo (tìm được kênh mới)")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — gõ tìm kênh ngay ở màn chính, không phá đổi kênh")
