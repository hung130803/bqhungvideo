# -*- coding: utf-8 -*-
r"""ĐO lỗi 2 (`vien_net` đổi màu TOÀN CLIP) — KHÔNG QUA ENCODER.

Xuất thẳng rawvideo yuv444p (không nén) nên MỌI chênh lệch đo được là do
FILTER, không phải do rate-control của encoder. Đây là cách đo đúng: đo qua
mp4/nvenc thì nhiễu nén ~0,02 che mất (hoặc phóng đại) lệch thật.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _nguon_nhat  # noqa: E402

FF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
W, H = 540, 960
A, B = 1.20, 1.55
NGOAI, TRONG = 0.30, 1.35
_NOWIN = 0x08000000


def raw(td: str, ten: str, src: str, hieu: str) -> np.ndarray:
    """Dựng ĐÚNG khuôn graph thật (nền mờ + overlay) rồi ghi rawvideo."""
    nen = (f"[0:v]split=2[bv][fv];"
           f"[bv]scale={W//4}:{H//4}:force_original_aspect_ratio=increase,"
           f"crop={W//4}:{H//4},boxblur=5:1,scale={W}:{H},setsar=1[base];"
           f"[fv]scale={W}:-2:flags=lanczos,setsar=1[fg];"
           f"[base][fg]overlay=x='0.5*W-w/2':y='0.5*H-h/2'[vv]")
    g = nen + (f";[vv]{hieu}[vo]" if hieu else "")
    out_lab = "[vo]" if hieu else "[vv]"
    p = os.path.join(td, ten + ".raw")
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-ss", "100", "-t", "3.0", "-i", src,
         "-an", "-filter_complex", g, "-map", out_lab,
         "-pix_fmt", "yuv444p", "-r", "30", "-fps_mode:v", "cfr",
         "-f", "rawvideo", p],
        capture_output=True, text=True, errors="replace", creationflags=_NOWIN)
    if r.returncode != 0:
        print("   LOI:", (r.stderr or "")[-300:])
        return None
    d = np.fromfile(p, dtype=np.uint8)
    n = W * H * 3
    return d[: (d.size // n) * n].reshape(-1, 3, H, W).astype(np.int16)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    src = _nguon_nhat.mot("JP")
    print("[nguồn]", os.path.basename(src), "· rawvideo, KHÔNG encoder")
    en = f":enable='between(t,{A},{B})'"
    cach = [
        ("HIỆN TẠI colormix", f"edgedetect=mode=colormix:high=0.23{en}"),
        ("canny planes=y", f"edgedetect=mode=canny:planes=y:high=0.23:low=0.08{en}"),
        ("sobel planes=1 sc0.35", f"sobel=planes=1:scale=0.35{en}"),
        ("quang_sang (đối chứng)", f"frei0r=filter_name=glow:filter_params=0.3{en}"),
    ]
    with tempfile.TemporaryDirectory(prefix="_vn_") as td:
        os.environ.setdefault(
            "FREI0R_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "app", "assets", "hieu_ung", "frei0r"))
        goc = raw(td, "goc", src, "")
        if goc is None:
            return
        i_ng, i_tr = int(NGOAI * 30), int(TRONG * 30)
        print(f"{'cách dựng':<26}{'|dU| ngoài':>11}{'|dV| ngoài':>11}"
              f"{'%pxY ngoài':>12}{'%pxY trong':>12}")
        print("-" * 74)
        print(f"{'GỐC':<26}{0.0:>11.3f}{0.0:>11.3f}{0.0:>11.2f}%{0.0:>11.2f}%")
        for ten, ch in cach:
            a = raw(td, ten.replace(" ", "_"), src, ch)
            if a is None or a.shape[0] < max(i_ng, i_tr) + 1:
                print(f"{ten:<26} KHÔNG dựng được"); continue
            du = abs(float(a[i_ng, 1].mean()) - float(goc[i_ng, 1].mean()))
            dv = abs(float(a[i_ng, 2].mean()) - float(goc[i_ng, 2].mean()))
            png = float((np.abs(a[i_ng, 0] - goc[i_ng, 0]) > 12).mean()) * 100
            ptr = float((np.abs(a[i_tr, 0] - goc[i_tr, 0]) > 12).mean()) * 100
            print(f"{ten:<26}{du:>11.3f}{dv:>11.3f}{png:>11.2f}%{ptr:>11.2f}%")


if __name__ == "__main__":
    main()
