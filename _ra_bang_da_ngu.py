# -*- coding: utf-8 -*-
"""SINH BẢNG ``app/core/da_ngu.py`` TỪ PHÉP ĐO — đừng gõ tay.

Đọc `bq_do_5_tieng/cache.json`, chấm bằng `_ra_bang_5_tieng.phan_xu` (hai
thước phải đồng ý), rồi in ra đúng dạng dòng Python để dán vào
``da_ngu.BANG``. Cùng khuôn ``nhan_nha.BANG`` (sinh từ ``_do_nhan_nha_*``):
**bảng số trong app phải có một nguồn duy nhất là phép đo.**

Chạy: .venv\\Scripts\\python -u _ra_bang_da_ngu.py [--ghi]
      --ghi: ghi thẳng vào `app/core/da_ngu.py` (thay khối BANG)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

from _ra_bang_5_tieng import (NN5, chon_cot, gom, nap,           # noqa: E402
                              nguong, phan_xu)

DICH = REPO / "app" / "core" / "da_ngu.py"


def bang() -> dict[str, dict[str, bool | None]]:
    g = gom(nap())
    NG = {"tr": nguong(g, "tr"), "cau": nguong(g, "cau")}
    chon_cot(NG["tr"], NG["cau"])          # in ra cảnh báo chồng lấn nếu có
    ra: dict[str, dict[str, bool | None]] = {}
    for v in g.values():
        kq, _ly = phan_xu(v, v["nn"], NG)
        ra.setdefault(v["voice"], {})[v["nn"]] = (
            True if kq == "CÓ" else False if kq == "KHÔNG" else None)
    return ra


def dong(b: dict) -> list[str]:
    """Dòng Python, sắp theo SỐ TIẾNG ĐỌC ĐƯỢC giảm dần rồi theo mã."""
    def khoa(kv):
        return (-sum(1 for x in kv[1].values() if x is True), kv[0])
    ra = []
    for ma, d in sorted(b.items(), key=khoa):
        cai = ", ".join(f'"{n}": {d[n]}' for n in NN5 if n in d)
        ra.append(f'    "{ma}": {{{cai}}},')
    return ra


def main() -> int:
    b = bang()
    ds = dong(b)
    print(f"{len(b)} giọng đã đo · "
          f"{sum(1 for d in b.values() if sum(1 for x in d.values() if x) >= 2)}"
          f" giọng đọc được >= 2 tiếng")
    print("\n".join(ds))
    if "--ghi" in sys.argv:
        s = DICH.read_text(encoding="utf-8")
        m = re.search(r"(BANG: dict\[str, dict\[str, bool \| None\]\] = \{\n)"
                      r".*?(\n\}\n)", s, re.S)
        if not m:
            print("KHÔNG tìm thấy khối BANG trong da_ngu.py -> KHÔNG ghi.")
            return 2
        s2 = s[:m.start(1)] + m.group(1) + "\n".join(ds) + m.group(2) + \
            s[m.end(2):]
        DICH.write_text(s2, encoding="utf-8", newline="")
        print(f"\n-> đã ghi {len(ds)} dòng vào {DICH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
