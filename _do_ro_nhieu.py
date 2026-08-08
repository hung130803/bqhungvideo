# -*- coding: utf-8 -*-
r"""ĐO RÒ HIỆU ỨNG RA NGOÀI CỬA SỔ — soi từng kiểu trên ĐƯỜNG XUẤT THẬT.

Cổng 43 quét từng kiểu bằng `-vf` TRẦN (1 lệnh ffmpeg, không nền mờ, không
overlay, không chuyển cảnh). Ở đây đo trên `export_canvas_clip` — đúng ống dẫn
anh Hùng dùng — vì rò chỉ lộ ra khi có ĐỦ các tầng.

    .venv\Scripts\python.exe _do_ro_nhieu.py <khoá> [<khoá> ...]
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_dorohu_{os.getpid()}"
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
FPS = 30
BAT, HET = 3.00, 3.50


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def doi(a, b, td: Path) -> list[float]:
    out = td / "d.txt"
    subprocess.run([str(x) for x in
                    [FF, "-y", "-v", "error", "-i", a, "-i", b,
                     "-filter_complex",
                     "[0:v][1:v]blend=all_mode=difference,"
                     "lutyuv=y='if(gt(val,12),255,0)',signalstats,"
                     f"metadata=print:file='{_esc(str(out))}'",
                     "-an", "-f", "null", "-"]],
                   capture_output=True, creationflags=_NOWIN)
    ds = []
    for ln in out.read_text(encoding="utf-8", errors="replace").splitlines():
        if "lavfi.signalstats.YAVG" in ln:
            try:
                ds.append(float(ln.split("=")[1]) / 2.55)
            except (ValueError, IndexError):
                pass
    return ds


def main() -> int:
    HU.dat_frei0r_path()
    ks = sys.argv[1:] or ["nhieu_analog", "hat_nhieu", "o_vuong", "zoom_nhoi"]
    td = Path(tempfile.mkdtemp(prefix="_dorohu_", dir=str(_SB)))
    src = REPO / "_clip_that" / "nguon.mp4"
    if not src.exists():
        print("thiếu _clip_that/nguon.mp4 — chạy _kiem_clip_that.py --giu trước")
        return 2
    segs = [(2.0, 8.0), (12.0, 18.0)]
    base = td / "base.mp4"
    FU.export_canvas_clip(str(src), str(base), segs, (0.5, 0.42, 1.0),
                          bg="blur", out_w=540, out_h=960, encoder="libx264",
                          hieu_ung="tat", fx_whoosh=False, chuyen_canh="tat")
    print(f"{'khoá':<16}{'trong cửa sổ':>14}{'ngoài cửa sổ':>14}   khung rò (>1%)")
    print("-" * 78)
    for k in ks:
        dst = td / f"{k}.mp4"
        hu = [{"bat": BAT, "het": HET, "khoa": k, "dam": HU.DAM_MAX}]
        try:
            FU.export_canvas_clip(str(src), str(dst), segs, (0.5, 0.42, 1.0),
                                  bg="blur", out_w=540, out_h=960,
                                  encoder="libx264", hieu_ung=hu,
                                  fx_whoosh=False, chuyen_canh="tat")
        except Exception as e:                     # noqa: BLE001
            print(f"{k:<16}  LỖI: {str(e)[:60]}")
            continue
        dd = doi(str(base), str(dst), td)
        i0, i1 = int(BAT * FPS), int(HET * FPS)
        trong = max(dd[i0 + 1:i1] or [0.0])
        ngoai_i = [i for i in range(len(dd)) if i < i0 - 1 or i > i1 + 1]
        ngoai = max((dd[i] for i in ngoai_i), default=0.0)
        ro = [i for i in ngoai_i if dd[i] > 1.0]
        print(f"{k:<16}{trong:>13.2f}%{ngoai:>13.2f}%   {len(ro)} khung "
              f"{[round(i/FPS, 2) for i in ro[:8]]}")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
