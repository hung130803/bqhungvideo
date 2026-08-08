# -*- coding: utf-8 -*-
r"""AI CÒN ĐANG SINH 397 LUỒNG? — soi MỌI ffmpeg TRÊN MÁY kèm DÒNG LỆNH.

    .venv\Scripts\python _ra_luong_toan_may.py [--giay 900]

Chạy SONG SONG với 1 lượt dây chuyền thật (hoặc `_ra_e2e.py`) ở cửa sổ khác.
Nó KHÔNG chạy gì nặng, chỉ lấy mẫu 20 lần/giây MỌI tiến trình tên `ffmpeg`
(kể cả cháu chắt của tiến trình con phân tích — `_run_analyze` chạy ffmpeg ở
TIẾN TRÌNH CHÁU nên bộ đếm theo `children()` của chính mình sẽ bỏ sót ngữ cảnh).

Ghi lại: đỉnh tổng luồng · lệnh nào đang chạy lúc đỉnh · xếp hạng theo lệnh.

BẪY: lọc theo `p.name()`, KHÔNG theo cmdline (cmdline của chính lệnh kiểm có
chữ 'ffmpeg' -> luôn tự đếm mình).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import psutil  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def nhan(cmd: list) -> str:
    s = " ".join(cmd)
    for k, v in (("astats", "ĐO: nghe astats"),
                 ("tblend", "ĐO: xem chuyển động"),
                 ("signalstats", "ĐO: signalstats"),
                 ("libmp3lame", "CHÉP LỜI: cắt cửa sổ mp3"),
                 ("-ac 1", "CHÉP LỜI: tách tiếng"),
                 ("pcm_s16le", "TÁCH TIẾNG wav"),
                 ("xfade", "XUẤT: chuyển cảnh"),
                 ("subtitles", "XUẤT: đốt .ass"),
                 ("frei0r", "XUẤT: hiệu ứng"),
                 ("gblur", "XUẤT: nền mờ"), ("boxblur", "XUẤT: nền mờ"),
                 ("-c copy", "copy"), ("select=", "trích khung"),
                 ("scdet", "ĐO: scdet")):
        if k in s:
            return v
    if "-f null" in s:
        return "ĐO khác (-f null)"
    if "-vn" in s:
        return "tách tiếng (-vn)"
    return "khác"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giay", type=float, default=900.0)
    a = ap.parse_args()
    cores = os.cpu_count() or 1
    print(f"soi MỌI ffmpeg trên máy trong {a.giay:.0f}s · "
          f"nhân {cores} · ngân sách 2× = {2*cores}\n")
    theo: dict[str, list[int]] = {}
    tong_mau: list[int] = []
    dinh, dinh_luc, dinh_chi_tiet = 0, "", ""
    t0 = time.time()
    while time.time() - t0 < a.giay:
        tong = 0
        hien = []
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info["name"] or "").lower() not in ("ffmpeg.exe", "ffmpeg"):
                    continue
                n = p.num_threads()
                tong += n
                hien.append((nhan(p.cmdline()), n, p.pid))
            except psutil.Error:
                continue
        if hien:
            tong_mau.append(tong)
            for k, n, _ in hien:
                theo.setdefault(k, []).append(n)
            if tong > dinh:
                dinh = tong
                dinh_luc = " + ".join(f"{k}={n}" for k, n, _ in hien)
                try:
                    dinh_chi_tiet = " ".join(
                        psutil.Process(hien[0][2]).cmdline())[:400]
                except psutil.Error:
                    pass
                print(f"  [đỉnh mới] {dinh} luồng ({dinh/cores:.2f}× nhân) "
                      f"· {dinh_luc}")
                sys.stdout.flush()
        time.sleep(0.05)

    print(f"\n{'lệnh':<26} {'mẫu':>6} {'TB':>7} {'ĐỈNH':>6}")
    for k, v in sorted(theo.items(), key=lambda x: -max(x[1])):
        print(f"{k:<26} {len(v):6d} {statistics.mean(v):7.1f} {max(v):6d}")
    print(f"\nĐỈNH TỔNG {dinh} ({dinh/cores:.2f}× nhân) lúc: {dinh_luc}")
    print(f"TB TỔNG   {statistics.mean(tong_mau):.1f}" if tong_mau else "")
    print(f"\nlệnh của tiến trình đầu lúc đỉnh:\n  {dinh_chi_tiet}")
    (REPO / "_ket__ra_luong_toan_may.json").write_text(json.dumps(
        {"dinh": dinh, "dinh_x": round(dinh/cores, 2), "dinh_luc": dinh_luc,
         "theo_lenh": {k: {"tb": round(statistics.mean(v), 1), "dinh": max(v)}
                       for k, v in theo.items()},
         "lenh_dinh": dinh_chi_tiet}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
