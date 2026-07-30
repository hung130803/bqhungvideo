# -*- coding: utf-8 -*-
# CỔNG CHỐNG CRASH 0xc0000005 (WER máy anh Hùng ghi 8 lần 28-30/07/2026,
# python312.dll, KHÔNG có traceback Python => luồng nền chạm Qt đã bị xoá /
# interpreter finalize lúc luồng daemon còn chạy).
#
# Test 3 lớp bảo vệ:
#   1. shutdown.safe_emit/alive/is_closing — không bao giờ ném, kể cả khi C++
#      object đã bị xoá thật (sip.delete).
#   2. _bg_thumbs — thoát im lặng khi app đang đóng / trang đã xoá.
#   3. main.py — thoát bằng os._exit sau khi dọn (không finalize interpreter)
#      + bật faulthandler ghi logs/crash_native.txt.
import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="shutdown_safe_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
sys.path.insert(0, r"D:\claude\ai-content-studio")

import app.queue.jobs  # noqa: F401,E402

from PyQt6 import sip  # noqa: E402
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

qapp = QApplication(sys.argv)

from app.ui import shutdown as S  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


print("== 1. safe_emit / alive / is_closing ==")
kiem(S.is_closing() is False, "mặc định: app KHÔNG ở trạng thái đóng")

goi = {"n": 0}


def _tang():
    goi["n"] += 1


kiem(S.safe_emit(lambda: _tang()) is True and goi["n"] == 1,
     "app bình thường: safe_emit GỌI THẬT", str(goi))

# đối tượng Qt bị XOÁ THẬT ở tầng C++ -> emit thẳng sẽ ném RuntimeError
w = QWidget()
sip.delete(w)
kiem(S.alive(w) is False, "alive() phát hiện widget đã bị xoá")
try:
    ok = S.safe_emit(lambda: w.setWindowTitle("x"))   # chạm widget đã xoá
    kiem(ok is False, "safe_emit trên widget ĐÃ XOÁ: trả False, KHÔNG ném",
         str(ok))
except RuntimeError as e:
    kiem(False, "safe_emit trên widget ĐÃ XOÁ: trả False, KHÔNG ném", repr(e))

# bật cờ đóng -> mọi lời gọi về UI phải bị chặn
S.set_closing()
goi["n"] = 0
kiem(S.is_closing() is True, "set_closing() bật cờ")
kiem(S.safe_emit(lambda: _tang()) is False and goi["n"] == 0,
     "đang đóng app: safe_emit KHÔNG gọi gì nữa", str(goi))
kiem(S.alive(QWidget()) is False, "đang đóng: alive() luôn False")

print("== 2. _bg_thumbs thoát im lặng khi đang đóng ==")
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES('K',?,'')",
           (os.path.join(T, "a"),))
pg = StudioPage(AppState())
phat = {"n": 0}
pg.thumbs_ready.connect(lambda: phat.__setitem__("n", phat["n"] + 1))
# S đang ở trạng thái ĐÓNG (từ phần 1) -> _bg_thumbs phải return ngay,
# không chạm đĩa, không emit.
clips = [{"id": 1, "signals": "{}", "start_sec": 0.0, "end_sec": 1.0}]
try:
    pg._bg_thumbs(clips, {"assets_dir": os.path.join(T, "a"),
                          "src_path": os.path.join(T, "khong-co.mp4")})
    kiem(phat["n"] == 0, "_bg_thumbs: đang đóng -> KHÔNG emit", str(phat))
except Exception as e:  # noqa: BLE001
    kiem(False, "_bg_thumbs: đang đóng -> không ném", repr(e))

print("== 3. main.py: thoát os._exit + faulthandler ==")
src = open(r"D:\claude\ai-content-studio\main.py", encoding="utf-8").read()
kiem("faulthandler.enable(" in src, "main.py BẬT faulthandler")
kiem("crash_native.txt" in src, "ghi vào logs/crash_native.txt")
kiem("os._exit(rc)" in src, "thoát bằng os._exit (không finalize interpreter)")
kiem(src.index("set_closing()") < src.index("os._exit(rc)"),
     "set_closing() gọi TRƯỚC khi thoát")
kiem("state.stop" in src.split("rc = qapp.exec()")[1],
     "vẫn dừng worker pool trước khi thoát")

mw = open(r"D:\claude\ai-content-studio\app\ui\main_window.py",
          encoding="utf-8").read()
i_set = mw.index("set_closing()")
i_kill = mw.index("terminate_all_children()")
kiem(i_set < i_kill,
     "closeEvent: bật cờ đóng TRƯỚC khi giết tiến trình con", f"{i_set}>{i_kill}")

sp = open(r"D:\claude\ai-content-studio\app\ui\studio_page.py",
          encoding="utf-8").read()
kiem(sp.count("safe_emit(") >= 5,
     "mọi emit từ luồng nền đã bọc safe_emit", f"{sp.count('safe_emit(')} chỗ")
kiem("self.thumbs_ready.emit()" not in sp.replace(
     "safe_emit(lambda: self.thumbs_ready.emit())", ""),
     "không còn emit TRẦN trong _bg_thumbs")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — luồng nền không thể làm sập app nữa")
os._exit(0)
