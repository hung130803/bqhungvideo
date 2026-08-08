# -*- coding: utf-8 -*-
"""Vì sao ca KHÔNG LỜI của lượt e2e KHÔNG đi đường XEM HÌNH? — đo trên dữ liệu THẬT.

    .venv\\Scripts\\python _ra_khongloi.py <sandbox_e2e>

Nạp ĐÚNG bản chép lời + độ dài mà app đã lưu, rồi gọi thẳng
`chon_doan.co_loi_noi_that()` — cửa quyết định duy nhất.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_kl_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "t.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.ai import chon_doan as CD  # noqa: E402


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
    print(f"{'kênh':<28} {'dài':>6} {'từ':>5} {'từ/giây':>8}  kết luận")
    for v in c.execute("SELECT v.id, v.duration, p.name kenh FROM videos v "
                       "JOIN projects p ON p.id=v.project_id ORDER BY v.id"):
        a = c.execute("SELECT data FROM analysis WHERE video_id=? AND "
                      "kind='transcript'", (v["id"],)).fetchone()
        tr = json.loads(a["data"]) if a and a["data"] else {}
        dur = float(v["duration"] or 0)
        co, ly_do, mds = CD.co_loi_noi_that(tr, dur)
        nw = len(tr.get("words") or [])
        print(f"{v['kenh'][:28]:<28} {dur:6.0f} {nw:5d} {mds:8.3f}  "
              f"{'CÓ lời' if co else 'KHÔNG lời -> ' + ly_do[:44]}")
    print("\n── đối chứng: `duration=0` (nếu app gọi TRƯỚC khi lưu độ dài) ──")
    a = c.execute("SELECT data FROM analysis WHERE kind='transcript' "
                  "ORDER BY video_id LIMIT 1").fetchone()
    tr = json.loads(a["data"]) if a and a["data"] else {}
    print("  co_loi_noi_that(tr, 0.0) ->", CD.co_loi_noi_that(tr, 0.0))
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
