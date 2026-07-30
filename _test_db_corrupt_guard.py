# -*- coding: utf-8 -*-
"""NGẮT MẠCH khi DB vỡ giữa lúc chạy — nguyên nhân app ĐƠN NẶNG.

ĐO THẬT trên máy anh Hùng 30/07 (app v2.6.x đang chạy, studio.db malformed):
  BQHungVideo.exe: đọc đĩa 24.704 KB/s · 6.176 lệnh đọc/s · ~50% CPU
  trong khi app ĐỨNG YÊN (không chạy job nào).
Vì mọi truy vấn ném "database disk image is malformed" nhưng KHÔNG AI ngắt —
poll 1,5s + dispatcher 0,5s + hồi phục cứ nã tiếp → bão I/O → đơ cả UI.

Test: DB vỡ -> query trả rỗng NGAY, KHÔNG đụng đĩa, có cờ cho UI dừng poll.
Chạy: .venv\\Scripts\\python _test_db_corrupt_guard.py
"""
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="dbguard_"))
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
sys.path.insert(0, r"D:\claude\ai-content-studio")

from app.database.db import Database  # noqa: E402

FAIL: list = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


print("== 1. DB lành: chạy bình thường ==")
d = Database(T / "t.db")
d.execute("INSERT INTO projects(name, assets_dir) VALUES('K1', ?)", (str(T),))
rows = d.query("SELECT name FROM projects")
kiem(len(rows) == 1, "query đọc được dữ liệu", str(len(rows)))
kiem(d.corrupt_live is False, "cờ corrupt_live = False khi DB lành")

print("\n== 2. nhận diện chuỗi lỗi VỠ (không nhầm lỗi khác) ==")
for m in ("database disk image is malformed", "file is not a database",
          "file is encrypted or is not a database"):
    kiem(Database._is_corrupt_err(sqlite3.DatabaseError(m)),
         f"nhận VỠ: {m[:38]!r}")
for m in ("database is locked", "disk I/O error", "no such table: x"):
    kiem(not Database._is_corrupt_err(sqlite3.DatabaseError(m)),
         f"KHÔNG nhầm: {m[:38]!r}")

print("\n== 3. DB VỠ GIỮA LÚC CHẠY -> ngắt mạch ==")
# PHÁ ĐÚNG KIỂU "ổ đĩa đầy lúc đang ghi": giữ 16 byte header để SQLite vẫn
# nhận là file DB, nhưng đập nát phần TRANG dữ liệu -> đọc bảng là malformed.
# (Ghi rác lệch 4096 KHÔNG đủ: DB nhỏ, page 1 còn nguyên nên vẫn đọc được —
# đó là lý do lần chạy đầu của test này 6 ca FAIL.)
d.close_all() if hasattr(d, "close_all") else None
try:
    d._local.conn.close()
except Exception:
    pass
d._local.conn = None
raw = bytearray(open(T / "t.db", "rb").read())
for i in range(16, len(raw)):
    raw[i] = 0x5A
open(T / "t.db", "wb").write(bytes(raw))
for suf in ("-wal", "-shm"):
    p = Path(str(T / "t.db") + suf)
    try:                      # Windows còn giữ handle -> ghi rỗng thay vì xoá
        if p.exists():
            open(p, "wb").close()
    except OSError:
        pass

r = d.query("SELECT name FROM projects")
kiem(r == [], "query trên DB vỡ trả RỖNG (không ném lỗi ra UI)", str(r)[:40])
kiem(d.corrupt_live is True, "cờ corrupt_live = True (UI dừng poll được)")

print("\n== 4. sau khi ngắt mạch: KHÔNG đụng đĩa nữa (chống bão I/O) ==")
# đo: 3000 query phải xong tức thì vì trả rỗng ngay, không mở file
t0 = time.perf_counter()
for _ in range(3000):
    d.query("SELECT * FROM jobs WHERE status='pending'")
    d.query_one("SELECT id FROM videos WHERE id=1")
ms = (time.perf_counter() - t0) * 1000
kiem(ms < 200, f"6.000 truy vấn sau ngắt mạch chỉ {ms:.0f} ms (đáng lẽ bão I/O)",
     f"{ms:.0f} ms")
kiem(d.query_one("SELECT 1") is None, "query_one trả None khi đã ngắt mạch")

print("\n== 5. execute (ghi) ném lỗi RÕ, không âm thầm mất dữ liệu ==")
try:
    d.execute("INSERT INTO projects(name, assets_dir) VALUES('X', 'y')")
    kiem(False, "execute phải ném lỗi khi DB vỡ")
except sqlite3.DatabaseError as e:
    kiem("ngắt mạch" in str(e) or "hỏng" in str(e),
         "execute ném lỗi có hướng dẫn khởi động lại", str(e)[:60])

print("\n== 6. mở app LẦN SAU trên file vỡ -> tự sao lưu + tạo DB mới ==")
d2 = Database(T / "t.db")
kiem(d2.corrupt_live is False, "DB mới dùng được ngay (cờ vỡ = False)")
d2.execute("INSERT INTO projects(name, assets_dir) VALUES('K2', 'z')")
kiem(len(d2.query("SELECT name FROM projects")) == 1, "ghi/đọc lại bình thường")
backups = list(T.glob("*backup*")) + list(T.glob("*corrupt*"))
kiem(bool(backups), "file vỡ được SAO LƯU (không xoá vĩnh viễn)",
     str([p.name for p in T.iterdir()])[:120])

print("\n== 7. PRAGMA tối ưu độ mượt có hiệu lực ==")
c = d2.conn()
autock = c.execute("PRAGMA wal_autocheckpoint").fetchone()[0]
sync = c.execute("PRAGMA synchronous").fetchone()[0]
kiem(int(autock) == 256, f"wal_autocheckpoint = {autock} (WAL không phình)")
kiem(int(sync) == 1, f"synchronous = NORMAL ({sync}) — bớt fsync, UI mượt")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — DB vỡ không còn làm app đơ")
