# -*- coding: utf-8 -*-
"""CỔNG 30 — CHẠY HÀNG TRĂM KÊNH PHẢI MƯỢT (ngân sách thời gian mỗi nhịp).

Anh Hùng 06/08/2026: "chạy hàng trăm kênh 1 lúc cực kỳ đơ luôn".
ĐO RA (cảnh 200 kênh / 900 job): mọi query DB <= 1,5 ms · nhịp poll trang chính
0,8 ms — KHÔNG phải nguyên nhân. Thủ phạm là **bảng HÀNG ĐỢI**: nhịp 400 ms mà
1 nhịp mất **246 ms** (= 61% thời gian máy) vì mỗi lần có job đổi trạng thái nó
`_clear()` rồi dựng lại CẢ 200 dòng (~1.200 widget).
SỬA: (a) trần số dòng vẽ 24 đang-chạy + 12 vừa-xong, phần dư gộp 1 dòng "…còn
N việc"; (b) cập nhật SAI KHÁC thay vì đập cả danh sách; (c) 2 query riêng nên
việc "✅ Xong" không bị việc đang chạy chiếm hết chỗ; (d) việc LỖI xếp trước.
SAU SỬA: **13 ms/nhịp (3%)** — nhanh 19 lần.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="muot_")
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


from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui import theme  # noqa: E402
from app.ui.queue_panel import _MAX_CHAY, _MAX_XONG, QueuePanel  # noqa: E402
from app.ui.state import AppState  # noqa: E402

_app.setStyleSheet(theme.QSS)        # QSS THẬT (không có thì đo ra nhẹ giả)

# ── cảnh THẬT lúc chạy 200 kênh ──
N_KENH, N_VIDEO, N_JOB = 200, 400, 900
con = db.conn()
for i in range(N_KENH):
    con.execute("INSERT INTO projects(name,assets_dir,grp) VALUES(?,?,?)",
                (f"Kênh số {i}", os.path.join(T, f"k{i}"),
                 "Mỹ" if i % 2 else "Việt"))
for i in range(N_VIDEO):
    con.execute("INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)",
                ((i % N_KENH) + 1, os.path.join(T, f"video so {i}.mp4"), 900.0))
for i in range(N_JOB):
    st = ("running" if i < 40 else "pending" if i < 300 else
          ("failed" if i % 17 == 0 else "done"))
    con.execute(
        "INSERT INTO jobs(type,status,project_id,video_id,priority,progress,"
        "message,error) VALUES(?,?,?,?,?,?,?,?)",
        ("auto" if i % 3 else "m1_export_clip", st, (i % N_KENH) + 1,
         (i % N_VIDEO) + 1, 10 if i % 3 else 3, (i % 100) / 100.0,
         "đang phân tích…", "Groq 500" if st == "failed" else None))
con.commit()
print(f"=== cảnh: {N_KENH} kênh · {N_VIDEO} video · {N_JOB} job "
      f"(40 chạy / 260 chờ) ===")

qp = QueuePanel(AppState())
qp.timer.stop()
qp.resize(560, 900)
qp.show()
_app.processEvents()
qp.refresh()
_app.processEvents()


def _do(fn, lan=5):
    fn()
    t = []
    for _ in range(lan):
        t0 = time.perf_counter()
        fn()
        t.append((time.perf_counter() - t0) * 1000)
    t.sort()
    return t[len(t) // 2], t[-1]


print("\n=== 1. NGÂN SÁCH: 1 nhịp bảng hàng đợi < 40 ms ===")
_dem = {"n": 0}


def _nhip_doi():
    """Cảnh thật: mỗi nhịp có job đổi trạng thái -> chữ ký đổi."""
    _dem["n"] += 1
    db.execute("UPDATE jobs SET status='done' WHERE id=?", (300 + _dem["n"],))
    db.execute("UPDATE jobs SET status='running' WHERE id=?", (350 + _dem["n"],))
    qp.refresh()
    _app.processEvents()


t_yen, x_yen = _do(lambda: (qp.refresh(), _app.processEvents()))
t_doi, x_doi = _do(_nhip_doi)
ok(t_doi < 40.0, "1a nhịp CÓ job đổi trạng thái < 40 ms",
   f"{t_doi:.1f} ms (xấu nhất {x_doi:.1f}) — trước sửa: 246 ms")
ok(t_yen < 40.0, "1b nhịp KHÔNG có gì đổi < 40 ms",
   f"{t_yen:.1f} ms — trước sửa: 30,5 ms")
ok(t_doi / 400 < 0.15,
   "1c chiếm < 15% thời gian máy (nhịp 400 ms)", f"{t_doi/400*100:.0f}%")

print("\n=== 2. TRẦN SỐ DÒNG + không mất việc nào khỏi báo cáo ===")
ok(len(qp._rows) <= _MAX_CHAY + _MAX_XONG,
   f"2a chỉ vẽ tối đa {_MAX_CHAY}+{_MAX_XONG} dòng", f"{len(qp._rows)} dòng")
_chay, _xong = services.list_jobs_top(_MAX_CHAY, _MAX_XONG)
ok(len(_xong) > 0,
   "2b việc VỪA XONG/LỖI vẫn hiện dù có 300 việc đang chạy/chờ "
   "(lỗi cũ: bị chiếm hết chỗ)", f"{len(_xong)} dòng")
ok(any(j["status"] == "failed" for j in _xong),
   "2c việc LỖI có mặt (xếp trước việc xong -> user thấy để Thử lại)",
   str([j["status"] for j in _xong][:6]))
_lb = getattr(qp, "_lb_con", None)
ok(_lb is not None and "còn" in _lb.text(),
   "2d có dòng '…còn N việc' để user biết danh sách bị cắt trần",
   _lb.text()[:60] if _lb else "(không có)")

print("\n=== 3. CẬP NHẬT SAI KHÁC: không đập cả danh sách ===")
_w_truoc = {jid: id(r["w"]) for jid, r in qp._rows.items()}
_nhip_doi()
_giu = sum(1 for jid, r in qp._rows.items()
           if _w_truoc.get(jid) == id(r["w"]))
ok(_giu >= len(_w_truoc) - 4,
   "3a dòng cũ GIỮ NGUYÊN widget (không tạo lại -> không nhấp nháy)",
   f"giữ {_giu}/{len(_w_truoc)} dòng")
_bar = list(qp._rows.values())[0]["bar"]
_id_bar = id(_bar)
_nhip_doi()
ok(any(id(r["bar"]) == _id_bar for r in qp._rows.values()),
   "3b thanh tiến trình KHÔNG bị xoá/tạo lại (lỗi cũ: 'mất rồi lại có')")

print("\n=== 4. Việc chạy XONG HẾT -> bảng về trạng thái trống, không nổ ===")
db.execute("UPDATE jobs SET status='done' WHERE status IN "
           "('running','pending')")
qp.refresh()
_app.processEvents()
ok(len(qp._rows) <= _MAX_XONG, "4a chỉ còn phần 'vừa xong'",
   f"{len(qp._rows)} dòng")
db.execute("DELETE FROM jobs")
qp.refresh()
_app.processEvents()
ok(not qp._rows and getattr(qp, "empty", None) is not None,
   "4b xoá hết job -> hiện 'Chưa có việc nào đang chạy.'")
ok(getattr(qp, "_lb_con", None) is None,
   "4c hết việc -> dòng '…còn N việc' tự biến mất")
con.execute("INSERT INTO jobs(type,status,project_id,video_id,priority,"
            "progress) VALUES('auto','running',1,1,10,0.5)")
con.commit()
qp.refresh()
_app.processEvents()
ok(len(qp._rows) == 1 and getattr(qp, "empty", None) is None,
   "4d có việc mới -> dòng trống biến đi, vẽ đúng 1 dòng",
   f"{len(qp._rows)} dòng")

print("\n=== 5. NHỊP THÍCH ỨNG không phá cái gì ===")
qp.timer.start(400)
qp.refresh()
ok(qp.timer.interval() in (400, 900),
   "5a nhịp hợp lệ", f"{qp.timer.interval()} ms")
ok(qp.timer.isActive(), "5b timer vẫn chạy sau khi đổi nhịp")

print("\n=== 6. QUERY: bản mới phải NHẸ HƠN bản cũ ===")
for i in range(500):
    con.execute("INSERT INTO jobs(type,status,project_id,video_id,priority,"
                "progress) VALUES('auto','pending',?,?,10,0)",
                ((i % N_KENH) + 1, (i % N_VIDEO) + 1))
con.commit()
t_cu, _ = _do(lambda: services.list_jobs(limit=200))
t_moi, _ = _do(lambda: services.list_jobs_top(_MAX_CHAY, _MAX_XONG))
ok(t_moi <= t_cu, "6a list_jobs_top nhẹ hơn list_jobs(200)",
   f"{t_moi:.2f} ms vs {t_cu:.2f} ms")
ok(t_moi < 5.0, "6b query < 5 ms với 1.400 job", f"{t_moi:.2f} ms")

print("\n=== 7. Nhịp poll TRANG CHÍNH vẫn trong ngân sách ===")
t_q, _ = _do(lambda: services.queue_counts())
t_p, _ = _do(lambda: services.list_projects())
ok(t_q < 10 and t_p < 10, "7a đếm job + liệt kê 200 kênh < 10 ms mỗi cái",
   f"đếm {t_q:.1f} ms · kênh {t_p:.1f} ms")

print(f"\n{'='*62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 30 ĐẠT — chạy hàng trăm kênh, giao diện còn trong ngân sách")
