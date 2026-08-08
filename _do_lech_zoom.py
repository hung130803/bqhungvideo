# -*- coding: utf-8 -*-
r"""ZOOM NHỒI CÓ LÀM LỆCH TIMELINE KHÔNG? (`zoompan` + `fps=` là chỗ hay lệch)

Đo 3 thứ trên ĐƯỜNG XUẤT THẬT, cùng nguồn, chỉ khác 1 hiệu ứng:
  1. số khung + độ dài;
  2. hồ sơ % pixel đổi TỪNG KHUNG (rò ở đâu);
  3. NẾU rò ở đuôi -> thử DỊCH 1 khung xem có khớp lại không (dịch khung =
     lệch tiếng-hình, đúng loại lỗi v1.87).

    .venv\Scripts\python.exe _do_lech_zoom.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_dolechzoom_{os.getpid()}"
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

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0
FPS = 30


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def dem(p) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       text=True, creationflags=_NOWIN)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return -1


def doi(a, b, td: Path, ten: str, loc_b: str = "") -> list[float]:
    out = td / f"d_{ten}.txt"
    fb = f"[1:v]{loc_b}[bb];[0:v][bb]" if loc_b else "[0:v][1:v]"
    subprocess.run([str(x) for x in
                    [FF, "-y", "-v", "error", "-i", a, "-i", b,
                     "-filter_complex",
                     fb + "blend=all_mode=difference,"
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
    td = Path(tempfile.mkdtemp(prefix="_lechzoom_", dir=str(_SB)))
    src = REPO / "_clip_that" / "nguon.mp4"
    if not src.exists():
        print("thiếu _clip_that/nguon.mp4"); return 2
    segs = [(2.0, 8.0), (12.0, 18.0)]      # 12 giây, 1 điểm nối ở 6,00 s
    base = td / "base.mp4"
    FU.export_canvas_clip(str(src), str(base), segs, (0.5, 0.42, 1.0),
                          bg="blur", out_w=540, out_h=960, encoder="libx264",
                          hieu_ung="tat", fx_whoosh=False, chuyen_canh="tat")
    print(f"base: {dem(base)} khung")
    for k, bat, het in (("zoom_nhoi", 3.00, 3.50),
                        ("zoom_nhoi", 0.12, 0.57),
                        ("zoom_day", 3.00, 3.70),
                        ("rung_lac", 3.00, 3.50)):
        dst = td / f"{k}_{bat}.mp4"
        FU.export_canvas_clip(
            str(src), str(dst), segs, (0.5, 0.42, 1.0), bg="blur",
            out_w=540, out_h=960, encoder="libx264",
            hieu_ung=[{"bat": bat, "het": het, "khoa": k,
                       "dam": HU.DAM_MAX}],
            fx_whoosh=False, chuyen_canh="tat")
        dd = doi(base, dst, td, f"{k}{bat}")
        i0, i1 = int(bat * FPS), int(het * FPS)
        ngoai = [(i, dd[i]) for i in range(len(dd))
                 if (i < i0 - 1 or i > i1 + 1) and dd[i] > 1.0]
        # thử DỊCH 1 khung: nếu khớp lại thì đây là LỆCH KHUNG
        dd1 = doi(base, dst, td, f"{k}{bat}_s1", loc_b="setpts=PTS-1/30/TB")
        ngoai1 = [i for i in range(len(dd1))
                  if (i < i0 - 1 or i > i1 + 1) and dd1[i] > 1.0]
        print(f"\n{k} @ {bat}-{het}s · {dem(dst)} khung "
              f"(base {dem(base)})")
        print(f"   trong cửa sổ: {max(dd[i0+1:i1] or [0]):.2f}%")
        print(f"   NGOÀI cửa sổ: {len(ngoai)} khung rò, cao nhất "
              f"{max((v for _i, v in ngoai), default=0):.2f}%")
        if ngoai:
            print("      giây rò: " +
                  ", ".join(f"{i/FPS:.2f}s={v:.1f}%" for i, v in ngoai[:10]))
        print(f"   sau khi DỊCH 1 khung: {len(ngoai1)} khung rò "
              f"-> {'LỆCH KHUNG' if len(ngoai1) < len(ngoai) / 2 else 'không phải lệch khung'}")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
