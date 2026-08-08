# -*- coding: utf-8 -*-
r"""ĐO NỀN của video THẬT — chọn 3 nguồn nền YÊN / TRUNG BÌNH / ỒN.

Cổng 44 chỉ đo trên MỘT nguồn nền yên (-23,6 dBFS) nên không thấy lỗi "tiếng
động không nghe được trên clip ồn". Script này quét kho video thật, đo cho mỗi
video một cửa sổ 16 s:

    mean_volume  (cách CŨ `_muc_nen_dB` dùng — clip ồn thì đây CHÍNH LÀ mức lời)
    bpv20        (bách phân vị 20 của đường bao RMS 50 ms = NỀN thật)
    bpv50 / bpv90(mức lời)

    .venv\Scripts\python.exe _do_nen_clip.py
"""
from __future__ import annotations

import array
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_donen_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from config import settings                    # noqa: E402

FF = settings.FFMPEG_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0
HZ = 8000
CUA = 0.05


def pcm(path: str, ss: float, t: float) -> array.array:
    r = subprocess.run(
        [FF, "-v", "error", "-nostdin", "-threads", "1",
         "-ss", f"{ss:.3f}", "-t", f"{t:.3f}", "-i", path,
         "-vn", "-ac", "1", "-ar", str(HZ), "-f", "s16le", "-"],
        capture_output=True, creationflags=_NOWIN, timeout=300)
    a = array.array("h")
    a.frombytes(r.stdout or b"")
    return a


def bao_rms(a) -> list[float]:
    n = int(HZ * CUA)
    out = []
    for i in range(0, len(a) - n + 1, n):
        s = 0
        for v in a[i:i + n]:
            s += v * v
        out.append(math.sqrt(s / n))
    return out


def dB(x: float) -> float:
    return 20 * math.log10(max(x, 1e-7) / 32768.0)


def bpv(rs: list, q: float) -> float:
    y = sorted(rs)
    return y[min(len(y) - 1, int(len(y) * q))] if y else 0.0


def main() -> int:
    kho = Path("D:/video test/Đã tải")
    if not kho.is_dir():
        print("không có kho video thật")
        return 2
    vids = sorted(p for p in kho.iterdir()
                  if p.suffix.lower() in (".mp4", ".mkv", ".webm"))
    print(f"{len(vids)} video · đo cửa sổ 16 s từ giây 240\n")
    print(f"{'video':<44}{'mean':>8}{'bpv20':>8}{'bpv50':>8}{'bpv90':>8}"
          f"{'lời-nền':>9}")
    print("-" * 85)
    ket = []
    for p in vids:
        a = pcm(str(p), 240.0, 16.0)
        if len(a) < HZ * 8:
            a = pcm(str(p), 20.0, 16.0)
        if len(a) < HZ * 8:
            continue
        rs = bao_rms(a)
        if not rs:
            continue
        mean = dB(math.sqrt(sum(float(v) * v for v in a) / len(a)))
        b20, b50, b90 = dB(bpv(rs, .20)), dB(bpv(rs, .50)), dB(bpv(rs, .90))
        ket.append((p.name, mean, b20, b50, b90))
        print(f"{p.name[:43]:<44}{mean:>8.1f}{b20:>8.1f}{b50:>8.1f}"
              f"{b90:>8.1f}{b90-b20:>9.1f}")
    ket.sort(key=lambda x: x[2])
    print("\n== XẾP THEO NỀN (bpv20) — chọn 3 mốc YÊN / TRUNG BÌNH / ỒN ==")
    for ten, mean, b20, b50, b90 in ket:
        print(f"  nền {b20:6.1f} · mean {mean:6.1f} · lời {b90:6.1f}  {ten[:50]}")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
