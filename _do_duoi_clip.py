# -*- coding: utf-8 -*-
r"""SOI 12 KHUNG CUỐI: vì sao bản CÓ hiệu ứng khác bản TẮT ở 0,25 s cuối?"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_doduoi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ["BQ_FFMPEG_SLOTS"] = "1"
os.environ.setdefault("BQ_TEST", "1")
import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from config import settings                       # noqa: E402
from app.core import hieu_ung as HU               # noqa: E402
from app.core import ffmpeg_utils as FU           # noqa: E402

FF = settings.FFMPEG_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0


def yavg(p, td: Path, ten: str) -> list[float]:
    out = td / f"y_{ten}.txt"
    subprocess.run([str(x) for x in
                    [FF, "-y", "-v", "error", "-i", p, "-vf",
                     "signalstats,metadata=print:file='"
                     + str(out).replace("\\", "/").replace(":", "\\:") + "'",
                     "-an", "-f", "null", "-"]],
                   capture_output=True, creationflags=_NOWIN)
    ds = []
    for ln in out.read_text(encoding="utf-8", errors="replace").splitlines():
        if "lavfi.signalstats.YAVG" in ln:
            ds.append(float(ln.split("=")[1]))
    return ds


def main() -> int:
    HU.dat_frei0r_path()
    td = Path(tempfile.mkdtemp(prefix="_doduoi_", dir=str(_SB)))
    src = REPO / "_clip_that" / "nguon.mp4"
    segs = [(2.0, 8.0), (12.0, 18.0)]
    files = {}
    for ten, hu, fade in (("tat", "tat", True), ("co_hu", None, True),
                          ("tat_khongfade", "tat", False),
                          ("co_hu_khongfade", None, False)):
        if hu is None:
            hu = [{"bat": 3.0, "het": 3.5, "khoa": "rung_lac",
                   "dam": HU.DAM_MAX}]
        p = td / f"{ten}.mp4"
        FU.export_canvas_clip(str(src), str(p), segs, (0.5, 0.42, 1.0),
                              bg="blur", out_w=540, out_h=960,
                              encoder="libx264", hieu_ung=hu,
                              fx_whoosh=False, chuyen_canh="tat",
                              fx_fade=fade)
        files[ten] = p
    ys = {k: yavg(v, td, k) for k, v in files.items()}
    print(f"{'khung':>6}{'giây':>8}" + "".join(f"{k:>18}" for k in ys))
    n = min(len(v) for v in ys.values())
    for i in range(n - 14, n):
        print(f"{i:>6}{i/30:>8.2f}" +
              "".join(f"{ys[k][i]:>18.2f}" for k in ys))
    print("\nsố khung: " + " · ".join(f"{k}={len(v)}" for k, v in ys.items()))
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
