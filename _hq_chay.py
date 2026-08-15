# -*- coding: utf-8 -*-
"""CHẠY HỒI QUY, IN MÃ THOÁT THẬT.

**KHÔNG nối `| tail`** — làm vậy thì mã thoát thành của `tail`, LUÔN BẰNG 0,
và cổng đỏ đọc thành cổng xanh. Ở đây chạy bằng `subprocess` rồi in
`returncode` của CHÍNH tiến trình cổng.

Ép `PYTHONIOENCODING=utf-8` cho mọi tiến trình con: chạy hồi quy là ghi ra
FILE, lúc đó Python lấy cp1252 và dòng `print` tiếng Việt ĐẦU TIÊN ném
`UnicodeEncodeError` -> cổng báo mã 1 trong khi mã app không sai chỗ nào
(đo 14/08/2026: `_test_lane_starve.py` chết đúng kiểu đó trong 1 giây).

  .venv\\Scripts\\python -u _hq_chay.py <ten_cong.py> [...]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def chay(ten: str) -> tuple[int, float, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("BQ_FFMPEG_SLOTS", "1")
    # MỐC ĐỐI CHỨNG: `main` giờ CHÍNH LÀ bản đang test -> mọi cổng so với
    # `main` sẽ PASS OAN vĩnh viễn. Dùng thẻ đã phát hành.
    env.setdefault("BQ_MOC_REF", "v2.26.0")
    t0 = time.time()
    log = REPO / f"_hq_{Path(ten).stem}.txt"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        r = subprocess.run([sys.executable, "-u", str(REPO / ten)],
                           cwd=str(REPO), env=env, stdout=f,
                           stderr=subprocess.STDOUT, timeout=5400)
    giay = time.time() - t0
    txt = log.read_text(encoding="utf-8", errors="replace")
    # đuôi có ích: dòng tổng kết (ĐẠT n · HỎNG m / n OK · m FAIL / TẤT CẢ ĐẠT)
    tk = ""
    for d in reversed(txt.splitlines()):
        if re.search(r"(ĐẠT\s+\d+|OK\b.*FAIL|TẤT CẢ ĐẠT|HỎNG\s+\d+)", d):
            tk = d.strip()
            break
    if not tk:
        tk = (txt.strip().splitlines() or ["(không có output)"])[-1][:120]
    return r.returncode, giay, tk


def main(argv: list[str]) -> int:
    print(f"{'CỔNG':<32} {'MÃ':>4} {'GIÂY':>7}  TỔNG KẾT")
    print("-" * 100)
    xau = 0
    for ten in argv:
        try:
            ma, giay, tk = chay(ten)
        except subprocess.TimeoutExpired:
            ma, giay, tk = 124, -1.0, "QUÁ GIỜ (timeout 5400s)"
        if ma != 0:
            xau += 1
        print(f"{ten:<32} {ma:>4} {giay:>7.1f}  {tk}")
        sys.stdout.flush()
    print("-" * 100)
    print(f"{len(argv)} cổng · {xau} cổng mã thoát KHÁC 0")
    return 1 if xau else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
