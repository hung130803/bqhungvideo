# -*- coding: utf-8 -*-
"""Tái hiện ĐÚNG khối quyết định `_khong_loi` của `generate_highlights`
trên sandbox e2e — dùng chính `get_analysis` + `db` của app.

    .venv\\Scripts\\python _ra_khongloi2.py <sandbox_e2e>
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

sb = Path(sys.argv[1])
_TD = Path(tempfile.mkdtemp(prefix="ra_kl2_"))
for e in ("", "-wal", "-shm"):
    try:
        shutil.copy(str(sb / "studio.db") + e, str(_TD / "studio.db") + e)
    except OSError:
        pass
os.environ["BQ_DATA_DIR"] = str(_TD)
os.environ["BQ_DB_PATH"] = str(_TD / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_TD / "s.ini")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.ai import chon_doan as _cd_mod  # noqa: E402
from app.core.analysis import get_analysis  # noqa: E402
from app.database.db import db  # noqa: E402

print(f"{'kênh':<28} {'dur DB':>7} {'segs':>5} {'words':>6}  _khong_loi")
for v in db.query("SELECT v.id, p.name kenh FROM videos v "
                  "JOIN projects p ON p.id=v.project_id ORDER BY v.id"):
    # ---- Y HỆT m1_highlight.generate_highlights ----
    transcript = get_analysis(v["id"], "transcript") or {}
    vrow = db.query_one("SELECT duration, src_path FROM videos WHERE id=?",
                        (v["id"],))
    duration = float(vrow["duration"] or 0) if vrow else 0.0
    _khong_loi = False
    _vs = ""
    try:
        _co, _vs, _mds = _cd_mod.co_loi_noi_that(transcript, duration)
        if not _co:
            _khong_loi = True
    except Exception as e:      # noqa: BLE001
        _vs = f"NÉM LỖI: {type(e).__name__}: {e}"
    print(f"{v['kenh'][:28]:<28} {duration:7.1f} "
          f"{len(transcript.get('segments') or []):5d} "
          f"{len(transcript.get('words') or []):6d}  "
          f"{_khong_loi}  {_vs[:44]}")
shutil.rmtree(_TD, ignore_errors=True)
