# -*- coding: utf-8 -*-
r"""ĐO: chuẩn hoá theo ĐỈNH RMS 50 ms + HẠN ĐỈNH (`alimiter`) giữ được bao
nhiêu độ to?

Câu hỏi phải trả lời bằng SỐ trước khi sửa `tinh_gain_sfx`:
  1. Kho có hệ số đỉnh ngắn hạn (max − rms50) trung vị 11,2 dB. Muốn lớp tiếng
     động đạt đỉnh RMS `dich` mà đỉnh MẪU vẫn <= trần thì phải nén đỉnh. Nén
     xong đỉnh RMS còn lại bao nhiêu — tức mất bao nhiêu dB so với `dich`?
  2. Sau khi nén, các file KHÁC NHAU có ra CÙNG một độ to không (hết nhấp nháy)?

    .venv\Scripts\python.exe _do_han_dinh.py
"""
from __future__ import annotations


import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"_dohd_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_TEST", "1")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as FU      # noqa: E402
from config import settings                  # noqa: E402

FF = settings.FFMPEG_PATH
NOWIN = 0x08000000 if os.name == "nt" else 0
DICH = -11.0                 # đỉnh RMS 50 ms mong muốn của lớp tiếng động


def do_ra(af: str, src: str) -> tuple[float, float]:
    """(đỉnh RMS 50 ms, đỉnh MẪU) dBFS sau khi qua chuỗi filter `af`."""
    r = subprocess.run(
        [FF, "-hide_banner", "-v", "error", "-nostdin", "-i", src, "-vn",
         "-af", af + ",aresample=8000,aformat=channel_layouts=mono,"
                     "asetnsamples=n=400,astats=metadata=1:reset=1,"
                     "ametadata=print:key=lavfi.astats.Overall.RMS_level:"
                     "file=-", "-f", "null", "-"],
        capture_output=True, creationflags=NOWIN, timeout=120)
    vals = []
    for ln in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if "RMS_level=" in ln:
            try:
                v = float(ln.split("=")[1])
            except (ValueError, IndexError):
                continue
            if v > -200:
                vals.append(v)
    r2 = subprocess.run(
        [FF, "-hide_banner", "-v", "info", "-nostdin", "-i", src, "-vn",
         "-af", af + ",volumedetect", "-f", "null", "-"],
        capture_output=True, creationflags=NOWIN, timeout=120)
    mx = -99.0
    for ln in (r2.stderr or b"").decode("utf-8", "replace").splitlines():
        if "max_volume:" in ln:
            mx = float(ln.split("max_volume:")[1].split("dB")[0])
    return (max(vals) if vals else -99.0), mx


def main() -> int:
    bang = FU._sfx_bang_muc()
    kho = FU._assets_sfx_dir()
    ms = [(k, v) for k, v in bang.items()
          if isinstance(v, list) and len(v) >= 3]
    cr = sorted(v[1] - v[2] for _k, v in ms)
    print(f"kho {len(ms)} file · hệ số đỉnh NGẮN HẠN (max − rms50): "
          f"min {cr[0]:.1f} · bpv25 {cr[len(cr)//4]:.1f} · trung vị "
          f"{cr[len(cr)//2]:.1f} · bpv75 {cr[3*len(cr)//4]:.1f} · "
          f"max {cr[-1]:.1f} dB")

    # chọn 8 file trải đều theo hệ số đỉnh ngắn hạn
    ms.sort(key=lambda kv: kv[1][1] - kv[1][2])
    idx = [int(i * (len(ms) - 1) / 7) for i in range(8)]
    print(f"\n{'file':<42}{'crest':>7}{'g dB':>7}"
          f"{'—KHÔNG hạn—':>16}{'—CÓ hạn (-4)—':>17}")
    print(f"{'':<42}{'':>7}{'':>7}{'rms50':>8}{'đỉnh':>8}"
          f"{'rms50':>9}{'đỉnh':>8}")
    print("-" * 92)
    mat_kh, mat_ch = [], []
    for i in idx:
        k, v = ms[i]
        p = str(kho / k)
        if not os.path.exists(p):
            continue
        mx, st = v[1], v[2]
        g = DICH - st
        a1 = f"volume={10**(g/20):.5f}"
        a2 = a1 + ",alimiter=limit=0.631:level=0:attack=1:release=60"
        s1, p1 = do_ra(a1, p)
        s2, p2 = do_ra(a2, p)
        mat_kh.append(s1 - DICH)
        mat_ch.append(s2 - DICH)
        print(f"{k[:41]:<42}{mx-st:>7.1f}{g:>7.1f}"
              f"{s1:>8.1f}{p1:>8.1f}{s2:>9.1f}{p2:>8.1f}")
    print(f"\nKHÔNG hạn đỉnh: lệch so đích {min(mat_kh):+.1f}..{max(mat_kh):+.1f}"
          f" dB (trải {max(mat_kh)-min(mat_kh):.1f})")
    print(f"CÓ hạn đỉnh -4 dBFS: lệch {min(mat_ch):+.1f}..{max(mat_ch):+.1f} dB"
          f" (trải {max(mat_ch)-min(mat_ch):.1f})")
    print(f"  -> hạn đỉnh làm MẤT trung vị {statistics.median(mat_ch):.1f} dB "
          f"độ to, ĐỔI LẠI đỉnh mẫu về đúng trần")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
