# -*- coding: utf-8 -*-
r"""A/B: siết luồng cho `chon_doan.chuyen_dong` / `nang_luong` có làm CHẬM không?

    .venv\Scripts\python _ra_ab_chuyen_dong.py [--lap 3]

BỐI CẢNH: lượt tổng rà soát e2e đo tổng luồng ffmpeg **203 (8,46x nhân)**, vượt
mốc "<= 2x nhân". Truy ra: **`chuyen_dong` một mình ăn 70 luồng (2,92x nhân)** —
nó `subprocess.run` trần, KHÔNG núm luồng nào. (`do_nhip` đã siết từ trước,
`nang_luong` 24 luồng.)

TRƯỚC KHI SỬA PHẢI ĐO — bài học repo: pha 1 hạ giải mã về 1 làm **chậm THẬT**
(nvenc +30%, libx264 +155%). `chuyen_dong` là bước THUẦN GIẢI MÃ (không encode)
nên đúng là chỗ siết luồng CÓ THỂ đắt.

**ĐAN XEN các cấu hình** (bài học `do-ab-tren-may-anh-hung-phai-dan-xen`): máy
có thể bận lại giữa chừng, đo liền mạch từng cấu hình đã ra kết luận sai 2 lần.
Đo bằng **CPU-GIÂY** của tiến trình con, không chỉ wall-time.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_ab_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))

import psutil  # noqa: E402

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_NO_WIN = 0x08000000
THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")
# nguồn vừa phải để lặp được nhiều lần (653s, 60fps, 263 MB)
DUOI = "デザイナーズ秘密基地を内見！.mp4"


def tim() -> Path | None:
    for p in THUNG.rglob("*.mp4"):
        if p.name.endswith(DUOI):
            return p
    return None


def chay(ff: str, src: Path, luong: str | None,
         hw: str = "") -> tuple[float, float, int]:
    """Chạy đúng lệnh `chuyen_dong`. luong=None -> như HIỆN TẠI (không núm).
    hw: 'cuda'/'d3d11va'... -> giải mã trên GPU (máy anh Hùng GPU đang rảnh).
    Trả (wall, CPU-giây, đỉnh luồng)."""
    pre = []
    if hw:
        pre += ["-hwaccel", hw]
    if luong is not None:
        pre += ["-threads", luong, "-filter_threads", luong]
    cmd = [ff, "-hide_banner", "-nostats", *pre, "-i", str(src), "-an",
           "-vf", "fps=4,scale=160:-2,format=gray,"
                  "tblend=all_mode=difference,signalstats,"
                  "metadata=print:key=lavfi.signalstats.YAVG:file=-",
           "-f", "null", os.devnull]
    dinh = [0]
    cpu = [0.0]
    stop = threading.Event()
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=_NO_WIN)

    def _soi() -> None:
        try:
            pr = psutil.Process(p.pid)
        except psutil.Error:
            return
        while not stop.is_set():
            try:
                dinh[0] = max(dinh[0], pr.num_threads())
                ct = pr.cpu_times()
                cpu[0] = float(ct.user) + float(ct.system)
            except psutil.Error:
                return
            time.sleep(0.05)

    th = threading.Thread(target=_soi, daemon=True)
    th.start()
    p.wait()
    stop.set()
    th.join(timeout=2)
    return time.perf_counter() - t0, cpu[0], dinh[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lap", type=int, default=3)
    a = ap.parse_args()
    src = tim()
    if not src:
        print("DỪNG: không thấy nguồn.")
        return 2
    from config import settings
    ff = settings.FFMPEG_PATH
    cores = os.cpu_count() or 1
    print(f"nguồn: {src.name} ({src.stat().st_size/1024/1024:.0f} MB)")
    print(f"nhân {cores} · ngân sách 2x = {2*cores} luồng · lặp {a.lap} ĐAN XEN\n")

    ca = [("HIỆN TẠI (không núm)", None, ""), ("giải mã 4", "4", ""),
          ("giải mã 2", "2", ""), ("giải mã 1", "1", ""),
          ("GPU cuda + giải mã 4", "4", "cuda"),
          ("GPU d3d11va + giải mã 4", "4", "d3d11va")]
    kq: dict[str, list] = {t: [] for t, _, _ in ca}
    for i in range(a.lap):
        for ten, lv, hw in ca:           # ĐAN XEN: mỗi vòng chạy đủ mọi cấu hình
            w, c, d = chay(ff, src, lv, hw)
            kq[ten].append((w, c, d))
            print(f"  vòng {i+1} · {ten:22s} wall {w:6.2f}s · "
                  f"CPU-giây {c:6.2f} · đỉnh {d:3d} luồng")
            sys.stdout.flush()

    print("\n" + "=" * 72)
    print(f"{'cấu hình':<24} {'wall(tv)':>9} {'CPU-giây':>9} {'đỉnh luồng':>11} "
          f"{'so nhân':>8}  so HIỆN TẠI")
    goc = statistics.median(x[0] for x in kq["HIỆN TẠI (không núm)"])
    ra = {}
    for ten, _, _ in ca:
        w = statistics.median(x[0] for x in kq[ten])
        c = statistics.median(x[1] for x in kq[ten])
        d = max(x[2] for x in kq[ten])
        ra[ten] = {"wall": round(w, 2), "cpu_giay": round(c, 2), "luong": d,
                   "nhan_x": round(d / cores, 2), "so_goc": round(w / goc, 2)}
        print(f"{ten:<24} {w:9.2f} {c:9.2f} {d:11d} {d/cores:7.2f}x  "
              f"{w/goc:.2f}x {'✅' if d <= 2*cores else '❌ VƯỢT MỐC'}")
    (REPO / "_ket__ra_ab_chuyen_dong.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n[đã ghi] _ket__ra_ab_chuyen_dong.json")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
