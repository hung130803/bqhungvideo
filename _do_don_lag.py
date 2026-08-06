# -*- coding: utf-8 -*-
"""ĐO ĐỘ ĐƠ khi chạy HÀNG TRĂM KÊNH — tìm đúng thứ ăn hết nhịp giao diện.

Anh Hùng 06/08/2026: "chạy hàng trăm kênh 1 lúc cực kỳ đơ luôn".
Bài học cũ (30/07): lần trước "đơ" tưởng do UI, đo ra là bão đọc đĩa vì DB vỡ.
Nên lần này ĐO TỪNG PHẦN chứ không tối ưu bừa:
  - bảng HÀNG ĐỢI job (nhịp 400ms) — dựng lại bao nhiêu dòng, mất bao lâu
  - từng việc trong nhịp poll 1.5s của trang chính
  - các query DB ở quy mô thật
Chạy:  python _do_don_lag.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="dolag_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui import theme  # noqa: E402

_app.setStyleSheet(theme.QSS)

N_KENH, N_VIDEO, N_JOB = 200, 400, 900
print(f"=== DỰNG CẢNH: {N_KENH} kênh · {N_VIDEO} video · {N_JOB} job ===")
con = db.conn()
for i in range(N_KENH):
    con.execute("INSERT INTO projects(name,assets_dir,grp) VALUES(?,?,?)",
                (f"Kênh số {i}", os.path.join(T, f"k{i}"),
                 "Mỹ" if i % 2 else "Việt"))
for i in range(N_VIDEO):
    con.execute("INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)",
                ((i % N_KENH) + 1, os.path.join(T, f"video so {i}.mp4"), 900.0))
# job: 40 đang chạy, 260 chờ, còn lại xong/lỗi — giống lúc chạy 200 kênh
for i in range(N_JOB):
    st = ("running" if i < 40 else "pending" if i < 300 else
          ("failed" if i % 17 == 0 else "done"))
    con.execute(
        "INSERT INTO jobs(type,status,project_id,video_id,priority,progress,"
        "message) VALUES(?,?,?,?,?,?,?)",
        ("auto" if i % 3 else "export", st, (i % N_KENH) + 1,
         (i % N_VIDEO) + 1, 10 if i % 3 else 3, (i % 100) / 100.0,
         "đang phân tích…"))
con.commit()
print(f"    xong. job đang chạy 40 · chờ 260 · còn lại xong/lỗi\n")


def do(nhan, fn, lan=5):
    fn()                                    # 1 lượt khởi động (nạp cache)
    t = []
    for _ in range(lan):
        t0 = time.perf_counter()
        fn()
        t.append((time.perf_counter() - t0) * 1000)
    t.sort()
    print(f"  {nhan:52s} {t[len(t)//2]:7.1f} ms  (xấu nhất {t[-1]:7.1f})")
    return t[len(t)//2]


print("=== A. QUERY DB ở quy mô thật ===")
do("services.list_jobs(limit=200)  [bản CŨ]", lambda: services.list_jobs(limit=200))
do("services.list_jobs_top(24,12) [bản MỚI]",
   lambda: services.list_jobs_top(24, 12))
do("services.queue_counts()", lambda: services.queue_counts())
do("services.list_projects()", lambda: services.list_projects())
do("services.job_states(50 job)",
   lambda: services.job_states(list(range(1, 51))))

print("\n=== B. BẢNG HÀNG ĐỢI (nhịp 400ms — nghi phạm chính) ===")
from app.ui.queue_panel import QueuePanel  # noqa: E402

from app.ui.state import AppState  # noqa: E402
qp = QueuePanel(AppState())
qp.timer.stop()                             # tự gọi tay để đo
qp.resize(520, 800)
qp.show()
_app.processEvents()
qp.refresh()
_app.processEvents()
print(f"    số dòng đang vẽ: {len(qp._rows)} · nhịp {qp.timer.interval()}ms")
print(f"    trong đó: {sum(1 for r in services.list_jobs_top(24,12)[0])} đang chạy/chờ + "
      f"{sum(1 for r in services.list_jobs_top(24,12)[1])} vừa xong/lỗi")


def _nhip_khong_doi():
    qp.refresh()
    _app.processEvents()


def _nhip_co_job_doi():
    """Mô phỏng ĐÚNG cảnh chạy trăm kênh: mỗi nhịp có job đổi trạng thái ->
    chữ ký đổi -> code hiện tại ĐẬP CẢ DANH SÁCH rồi dựng lại."""
    global _dem
    _dem += 1
    db.execute("UPDATE jobs SET status='done' WHERE id=?", (300 + _dem,))
    db.execute("UPDATE jobs SET status='running' WHERE id=?", (350 + _dem,))
    qp.refresh()
    _app.processEvents()


_dem = 0
t_yen = do("1 nhịp — KHÔNG job nào đổi trạng thái", _nhip_khong_doi)
t_doi = do("1 nhịp — CÓ job đổi trạng thái (cảnh thật)", _nhip_co_job_doi)
print(f"    -> nhịp 400ms mà 1 nhịp mất {t_doi:.0f}ms = chiếm "
      f"{t_doi/400*100:.0f}% thời gian máy CHỈ để vẽ lại bảng job")

print("\n=== C. Từng việc trong nhịp poll 1.5s của TRANG CHÍNH ===")
from app.ui.studio_page import StudioPage  # noqa: E402
from PyQt6.QtWidgets import QWidget  # noqa: E402

sp = StudioPage.__new__(StudioPage)
QWidget.__init__(sp)
sp._pending_export = {}
sp._pipe_cut = {}
sp._pipe_by_vid = {}
sp._act_tick = 0
try:
    do("services.channel_activity() (nhãn hoạt động kênh)",
       lambda: services.channel_activity())
except Exception as e:  # noqa: BLE001
    print(f"  (bỏ qua channel_activity: {type(e).__name__})")
do("_check_auto_export_inner (0 job đang dõi)",
   lambda: sp._check_auto_export_inner())

print("\n=== D. ffmpeg/CPU: có bao nhiêu nhân, ngân sách encoder ===")
from config import settings  # noqa: E402

print(f"    số nhân CPU: {os.cpu_count()} · ECO_MODE={settings.ECO_MODE} "
      f"· LIGHT_MODE={settings.LIGHT_MODE}")
print(f"    MAX_PARALLEL/luồng phân tích: "
      f"{getattr(settings, 'MAX_WORKERS', '?')} · "
      f"ngân sách threads x264: {getattr(settings, 'FFMPEG_THREADS', '?')}")

print(f"\n(sandbox {T})")
