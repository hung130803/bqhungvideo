# -*- coding: utf-8 -*-
"""Soi tiến độ 1 sandbox đang chạy — CHỈ ĐỌC (chép DB + WAL ra chỗ khác rồi mở).

    .venv\\Scripts\\python _ra_soi.py <thu_muc_sandbox>

BÀI HỌC: copy file .db mà KHÔNG kèm -wal thì đọc thiếu dòng và tưởng "DB trống".
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def main() -> int:
    sb = Path(sys.argv[1])
    p = sb / "studio.db"
    t = Path(tempfile.mktemp(suffix=".db"))
    for e in ("", "-wal", "-shm"):
        try:
            shutil.copy(str(p) + e, str(t) + e)
        except OSError:
            pass
    c = sqlite3.connect(t)
    c.row_factory = sqlite3.Row
    print("── job ──")
    for r in c.execute("SELECT type,status,COUNT(*) n FROM jobs "
                       "GROUP BY type,status ORDER BY type,status"):
        print(f"  {r['type']:16s} {r['status']:9s} {r['n']}")
    print("── đang chạy ──")
    for r in c.execute("SELECT id,type,progress,message FROM jobs "
                       "WHERE status='running'"):
        print(f"  #{r['id']} {r['type']} {r['progress']:.2f} "
              f"{(r['message'] or '')[:70]}")
    print("── sổ dây chuyền ──")
    for r in c.execute("SELECT status,COUNT(*) n FROM pipeline_files "
                       "GROUP BY status"):
        print(f"  {r['status']:8s} {r['n']}")
    try:
        n = c.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        na = c.execute("SELECT COUNT(*) FROM clips WHERE "
                       "signals LIKE '%\"llm_used\": true%'").fetchone()[0]
        print(f"── clip: {n} (llm_used=true: {na})")
    except sqlite3.Error as e:
        print("  clip:", e)
    print("── job lỗi ──")
    for r in c.execute("SELECT id,type,status,error FROM jobs "
                       "WHERE error IS NOT NULL AND error!='' LIMIT 8"):
        print(f"  #{r['id']} {r['type']} {r['status']}: {(r['error'] or '')[:150]}")
    n_part = len(list(sb.rglob("Part *.mp4")))
    print(f"── Part đã xuất: {n_part}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
