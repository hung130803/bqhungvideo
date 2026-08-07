# -*- coding: utf-8 -*-
"""CỔNG 32 — LƯỚI AN TOÀN: video có clip mà KHÔNG AI XUẤT thì phải tự xuất tiếp.

Anh Hùng 07/08/2026: "tự out ra vào lại nó k tự xuất ra nữa".
Gốc: sổ theo dõi `_pending_export` chỉ nằm trong BỘ NHỚ. `_pipe_resume_taken`
có hồi phục lúc mở app nhưng chạy ĐÚNG MỘT LẦN và vẫn hụt:
  - user bấm "Xóa lịch sử" -> job phân tích bị xoá -> hồi phục tưởng chưa phân
    tích nên xếp job phân tích MỚI (đốt lại lượt Groq) thay vì xuất;
  - app chết NGAY LÚC đang xuất -> mất sổ, mà hồi phục đã chạy xong rồi.
Nay `_quet_bo_sot_xuat()` quét ĐỊNH KỲ (60s) theo SỰ THẬT TRONG DB.

BẤT BIẾN SỐNG CÒN: **HUỶ VẪN LÀ HUỶ** — video mà user đã huỷ job xuất thì
TUYỆT ĐỐI không được tự xuất lại (bất biến cổng 7 `_test_cancel_persist`).
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="luoi_")
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
        print(f"  OK  {ten}" + (f" - {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} - {ct}")
        print(f"  SAI {ten} - {ct}")


from PyQt6.QtWidgets import QApplication, QPushButton, QWidget  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

pid = services.create_project("Kênh Lưới", "M")


def _video(ten: str) -> int:
    return db.execute("INSERT INTO videos(project_id,src_path,duration) "
                      "VALUES(?,?,?)", (pid, os.path.join(T, ten),
                                        600.0)).lastrowid


def _clip(vid: int, tt="suggested"):
    return db.execute(
        "INSERT INTO clips(video_id,title,start_sec,end_sec,status,signals) "
        "VALUES(?,?,?,?,?,?)",
        (vid, "Đoạn hay", 10.0, 80.0, tt,
         db.dumps({"segments": [[10.0, 80.0]]}))).lastrowid


def _so(vid: int, tt="taken"):
    return db.execute(
        "INSERT INTO pipeline_files(project_id,file_name,status,video_id) "
        "VALUES(?,?,?,?)", (pid, f"v{vid}.mp4", tt, vid)).lastrowid


def _job(vid: int, kieu: str, tt: str):
    return db.execute(
        "INSERT INTO jobs(type,status,project_id,video_id,priority,progress) "
        "VALUES(?,?,?,?,?,0)", (kieu, tt, pid, vid, 3)).lastrowid


# ── dựng 6 ca, mỗi ca 1 video ──
v_sot = _video("bo-sot.mp4")          # CÓ clip, KHÔNG job nào -> PHẢI xuất
_clip(v_sot); _so(v_sot)
v_xoa_ls = _video("xoa-lich-su.mp4")  # job phân tích bị "Xóa lịch sử" -> PHẢI xuất
_clip(v_xoa_ls); _so(v_xoa_ls)
v_huy = _video("da-huy.mp4")          # user ĐÃ HUỶ job xuất -> KHÔNG được xuất
_clip(v_huy); _so(v_huy); _job(v_huy, "m1_export_clip", "canceled")
v_dang_chay = _video("dang-xuat.mp4")  # đang có job xuất -> KHÔNG xen ngang
_clip(v_dang_chay); _so(v_dang_chay); _job(v_dang_chay, "m1_export_clip", "running")
v_dang_pt = _video("dang-phan-tich.mp4")  # đang phân tích -> chưa tới lượt
_clip(v_dang_pt); _so(v_dang_pt); _job(v_dang_pt, "auto", "pending")
v_xong = _video("xong-roi.mp4")       # clip đã xuất -> KHÔNG xuất lại
_clip(v_xong, "exported"); _so(v_xong)
v_ngoai = _video("khong-day-chuyen.mp4")  # KHÔNG có dòng sổ -> lưới bỏ qua
_clip(v_ngoai)

sp = StudioPage.__new__(StudioPage)
QWidget.__init__(sp)


class _St:
    project_id = pid
    video_id = None


sp.state = _St()
sp.status = QPushButton("")
sp.layout_tpl = {"cap_preset": "Trắng đơn giản"}
sp._pending_export = {}
sp._pipe_report = []
sp._pipe_log = lambda s: sp._pipe_report.append(s)
_da_xuat: list = []
sp._export_video = lambda vid, only_clip_id=None, tpl=None: (
    _da_xuat.append(int(vid)), 1)[1]

print("\n=== 1. Lưới quét ĐÚNG video bị bỏ sót ===")
n = sp._quet_bo_sot_xuat()
ok(v_sot in _da_xuat, "1a video CÓ clip mà không job nào -> ĐƯỢC xuất tiếp")
ok(v_xoa_ls in _da_xuat,
   "1b video bị 'Xóa lịch sử' job -> ĐƯỢC xuất (không phân tích lại)")
ok(n == 2, "1c đúng 2 video được xuất", f"n={n} · {_da_xuat}")

print("\n=== 2. HUỶ VẪN LÀ HUỶ + không xen ngang việc đang chạy ===")
ok(v_huy not in _da_xuat,
   "2a video user ĐÃ HUỶ xuất -> TUYỆT ĐỐI không tự xuất lại (bất biến cổng 7)")
ok(v_dang_chay not in _da_xuat, "2b đang có job xuất chạy -> không xen ngang")
ok(v_dang_pt not in _da_xuat, "2c đang phân tích -> chưa tới lượt xuất")
ok(v_xong not in _da_xuat, "2d clip đã xuất rồi -> không xuất lại")
ok(v_ngoai not in _da_xuat,
   "2e video KHÔNG thuộc dây chuyền -> lưới không đụng (tránh xuất bừa)")

print("\n=== 3. Chạy lại lưới KHÔNG được xuất trùng ===")
_da_xuat.clear()
_job(v_sot, "m1_export_clip", "running")        # lượt 1 đã xếp job xuất
_job(v_xoa_ls, "m1_export_clip", "pending")
n2 = sp._quet_bo_sot_xuat()
ok(n2 == 0 and not _da_xuat,
   "3a lượt sau: đã có job xuất -> lưới im, không xuất trùng", f"n={n2}")

print("\n=== 4. Đang có sổ dõi trong bộ nhớ -> lưới không đụng ===")
db.execute("DELETE FROM jobs WHERE video_id=?", (v_sot,))
sp._pending_export = {999: v_sot}
_da_xuat.clear()
sp._quet_bo_sot_xuat()
ok(v_sot not in _da_xuat, "4a video đang được sổ RAM dõi -> lưới bỏ qua")

print("\n=== 5. Có báo cho user biết (không âm thầm) ===")
sp._pending_export = {}
_da_xuat.clear()
sp._pipe_report.clear()
sp._quet_bo_sot_xuat()
ok(any("LƯỚI AN TOÀN" in s for s in sp._pipe_report),
   "5a ghi 1 dòng nhật ký nêu rõ lý do", " | ".join(sp._pipe_report)[:110])

print("\n=== 6. DB lỗi / bảng thiếu -> không được sập ===")
db.execute("DROP TABLE IF EXISTS pipeline_files")
try:
    r = sp._quet_bo_sot_xuat()
    ok(r == 0, "6a thiếu bảng -> trả 0, không nổ", f"n={r}")
except Exception as e:  # noqa: BLE001
    ok(False, "6a thiếu bảng -> trả 0, không nổ", f"{type(e).__name__}: {e}")

print("\n=== 7. Được móc vào nhịp poll (nếu không thì vô dụng) ===")
from pathlib import Path  # noqa: E402

_src = Path(REPO, "app", "ui", "studio_page.py").read_text(
    encoding="utf-8", errors="replace")
ok("_quet_bo_sot_xuat()" in _src.split("def _quet_bo_sot_xuat")[0],
   "7a có lời gọi trong nhịp poll (trước cả định nghĩa hàm)")
ok("_act_tick % 40" in _src, "7b quét mỗi ~60 giây")
ok("gap_wal_dinh_ky" in _src, "7c vẫn giữ việc gấp sổ tạm WAL cùng nhịp")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  SAI {x}")
    sys.exit(1)
print("CỔNG 32 ĐẠT — không còn video nằm im sau khi app tắt đột ngột")
