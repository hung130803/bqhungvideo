# -*- coding: utf-8 -*-
"""In gọn kết quả `_ra_luong_toan_may.py` (JSON) — dùng để đọc bảng luồng."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

p = Path(sys.argv[1] if len(sys.argv) > 1 else "_ket__ra_luong_toan_may.json")
d = json.load(io.open(p, encoding="utf-8"))
print(f"ĐỈNH {d['dinh']} = {d['dinh_x']}× nhân   lúc: {d['dinh_luc']}\n")
for k, v in sorted(d["theo_lenh"].items(), key=lambda x: -x[1]["dinh"]):
    print(f"{k:<28} TB {v['tb']:>7}  ĐỈNH {v['dinh']:>4}")
print("\nLỆNH LÚC ĐỈNH:\n" + (d.get("lenh_dinh") or "")[:700])
