# -*- coding: utf-8 -*-
"""CHẠY ĐỦ 6 BƯỚC trên 1 video THẬT rồi in mọi số đo (bước 2-6).

    python _tg/do_e2e.py --video _tg/asset/zh60.mp4 --sang en
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(REPO / "_tg/asset/zh60.mp4"))
    ap.add_argument("--sang", default="en")
    ap.add_argument("--cach", default="auto")
    ap.add_argument("--ten", default="")
    a = ap.parse_args()

    from app.core import thay_giong as tg

    ten = a.ten or Path(a.video).stem
    lam = REPO / f"_tg/e2e_{ten}_{a.sang}"
    t0 = time.time()

    def prog(p: float, m: str) -> None:
        print(f"  [{p * 100:5.1f}%] {m}", flush=True)

    kq = tg.thay_giong_video(a.video, dich_sang=a.sang, thu_muc_lam=lam,
                             cach_tach=a.cach, on_progress=prog)
    kq["_wall"] = round(time.time() - t0, 2)
    print(json.dumps(kq, ensure_ascii=False, indent=1))
    out = REPO / f"_tg/ket_e2e_{ten}_{a.sang}.json"
    out.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nĐã ghi {out}")
    return 0 if kq.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
