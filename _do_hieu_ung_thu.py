# -*- coding: utf-8 -*-
"""THỬ NHANH từng chuỗi filter ứng viên trên VIDEO NHẬT THẬT.

Mỗi ứng viên: render 1,2s ở mốc SÁNG, trích khung ở giữa cửa sổ hiệu ứng, so với
bản KHÔNG hiệu ứng: %pixel đổi (|dY|>12), mean|dY|, lệch U, lệch V.
Lỗi filter -> in LOI (không im lặng).

Chạy: .venv\\Scripts\\python _do_hieu_ung_thu.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
FF = os.path.join(ROOT, "bin", "ffmpeg.exe")
os.environ.setdefault("FREI0R_PATH", r"C:\Users\Admin\AppData\Local\Temp\f0r\stage")

import _nguon_nhat
SRC = _nguon_nhat.mot("JP")

MOC = 200.0          # giây — cảnh SÁNG (bài học: giây 20 gần đen -> FAIL oan)
DAI = 1.2            # độ dài đoạn render
A, B = 0.35, 0.85    # cửa sổ hiệu ứng trong đoạn
GIUA = 0.60          # mốc trích khung (giữa cửa sổ)

# (tên, chuỗi filter) — {en} = mệnh đề enable
UV = [
    ("goc", ""),
    # ---- THUẦN ffmpeg ----
    ("flash_trang", "eq=brightness=0.22:contrast=1.06{en}"),
    ("toi_sup", "eq=brightness=-0.30{en}"),
    ("nhay_sang", "eq=brightness='0.18*sin(3.14159*8*t)'{en}"),
    ("mo_nhanh", "gblur=sigma=9{en}"),
    ("net_gat", "unsharp=5:5:1.6:5:5:0.0{en}"),
    ("hat_nhieu", "noise=alls=26:allf=t+u{en}"),
    ("o_vuong", "pixelize=w=24:h=24{en}"),
    ("lech_rgb", "rgbashift=rh=-7:bh=7{en}"),
    ("toi_vien", "vignette=a=PI/3.6{en}"),
    ("phoi_sang", "exposure=exposure=0.5{en}"),
    ("tuong_phan", "eq=contrast=1.5:saturation=1.0{en}"),
    ("vet_mo", "lagfun=decay=0.88{en}"),
    ("bong_kep", "tblend=all_mode=lighten{en}"),
    ("tron_khung", "tmix=frames=5{en}"),
    ("gan_via", "gradfun=strength=40{en}"),
    ("vien_sang", "edgedetect=mode=colormix:high=0.2{en}"),
    ("no_hat", "dilation=coordinates=255{en}"),
    ("xao_pixel", f"shufflepixels=direction=inverse:mode=horizontal:width=40:height=40{{en}}"),
    # zoom: scale/crop KHÔNG có timeline -> dùng zoompan, cổng thời gian NẰM
    # TRONG biểu thức (bẫy đã sập: scale không nhận biểu thức theo t)
    ("zoom_nhoi",
     "zoompan=z='if(between(it,{a},{b}),1.14,1)':d=1:"
     "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=WxH:fps=SFPS"),
    ("zoom_gian",
     "zoompan=z='if(between(it,{a},{b}),1+0.14*(it-{a})/({b}-{a}),1)':d=1:"
     "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=WxH:fps=SFPS"),
    ("rung_lac",
     "crop=w=iw-24:h=ih-24:x='12+10*sin(28*t)':y='12+10*cos(23*t)',scale=WxH"),
    # ---- frei0r ----
    ("f_glow", "frei0r=filter_name=glow:filter_params=0.5{en}"),
    ("f_softglow", "frei0r=filter_name=softglow:filter_params=0.5|0.6|0.5|0.5{en}"),
    ("f_filmgrain", "frei0r=filter_name=filmgrain:filter_params=0.6{en}"),
    ("f_gateweave", "frei0r=filter_name=gateweave:filter_params=0.8|0.8|0.8{en}"),
    ("f_ntsc", "frei0r=filter_name=ntsc:filter_params=0.6|0.6|0.6{en}"),
    ("f_glitch", "frei0r=filter_name=glitch0r:filter_params=0.5|0.3|0.5|0{en}"),
    ("f_rgbsplit", "frei0r=filter_name=rgbsplit0r:filter_params=0.55|0.55{en}"),
    ("f_pixeliz", "frei0r=filter_name=pixeliz0r:filter_params=0.06|0.06{en}"),
    ("f_sharp", "frei0r=filter_name=sharpness:filter_params=0.7|0.5{en}"),
    ("f_iirblur", "frei0r=filter_name=IIRblur:filter_params=0.3|0|0{en}"),
    ("f_letterbox", "frei0r=filter_name=letterb0xed:filter_params=0.12|1{en}"),
    ("f_vertigo", "frei0r=filter_name=vertigo:filter_params=0.03|1.02{en}"),
    ("f_distort", "frei0r=filter_name=distort0r:filter_params=0.03|0.3|0.5|0.5{en}"),
    ("f_emboss", "frei0r=filter_name=emboss:filter_params=0.5|0.5|0.3{en}"),
    ("f_tehroxx", "frei0r=filter_name=tehroxx0r:filter_params=0.3{en}"),
    ("f_dither", "frei0r=filter_name=dither:filter_params=0.3|0.2{en}"),
    ("f_posterize", "frei0r=filter_name=posterize:filter_params=0.25{en}"),
    ("f_halftone", "frei0r=filter_name=colorhalftone:filter_params=0.3|0.2|0.4|0.6{en}"),
    ("f_medians", "frei0r=filter_name=medians:filter_params=0.2|0.4{en}"),
    ("f_squareblur", "frei0r=filter_name=squareblur:filter_params=0.25{en}"),
    ("f_normaliz", "frei0r=filter_name=normaliz0r:filter_params=0.5|0.5|0|0|0{en}"),
    ("f_sigmoid", "frei0r=filter_name=sigmoidaltransfer:filter_params=0.6|0.5{en}"),
    ("f_cluster", "frei0r=filter_name=cluster:filter_params=0.3|0.3{en}"),
    ("f_defish", "frei0r=filter_name=defish0r:filter_params=0.6|0.5|0.5|0.5|0.5|0.5|0.5|0.5|0.5|0.5|0.5{en}"),
    ("f_lenscorr", "frei0r=filter_name=lenscorrection:filter_params=0.5|0.5|0.6|0.5|0.5{en}"),
    ("f_perspective", "frei0r=filter_name=perspective:filter_params=0.05|0.05|0.95|0.05{en}"),
    ("f_bw", "frei0r=filter_name=bw0r{en}"),
    ("f_luminance", "frei0r=filter_name=luminance{en}"),
    ("f_hueshift", "frei0r=filter_name=hueshift0r:filter_params=0.55{en}"),
    ("f_satur", "frei0r=filter_name=saturat0r:filter_params=0.65{en}"),
    ("f_contrast", "frei0r=filter_name=contrast0r:filter_params=0.62{en}"),
    ("f_gamma", "frei0r=filter_name=gamma:filter_params=0.65{en}"),
    ("f_bright", "frei0r=filter_name=brightness:filter_params=0.62{en}"),
    ("f_threshold", "frei0r=filter_name=threshold0r:filter_params=0.5{en}"),
    ("f_colorize", "frei0r=filter_name=colorize:filter_params=0.1|0.3|0.5{en}"),
    ("f_tint", "frei0r=filter_name=tint0r:filter_params=0.1|0.9|0.6{en}"),
    ("f_rgbnoise", "frei0r=filter_name=rgbnoise:filter_params=0.25{en}"),
    ("f_hqdn3d", "frei0r=filter_name=denoise_hqdn3d:filter_params=0.6|0.6{en}"),
    ("f_flippo", "frei0r=filter_name=flippo:filter_params=1|0{en}"),
    ("f_colortap", "frei0r=filter_name=colortap:filter_params=0.4{en}"),
    ("f_3pbal", "frei0r=filter_name=three_point_balance:filter_params=0.5|0.5|0.5|0.5|0.5{en}"),
    ("f_curves", "frei0r=filter_name=curves:filter_params=0.5{en}"),
    ("f_levels", "frei0r=filter_name=levels:filter_params=0.5|0.3|0.7|0.5|0.5|0.5|0|0{en}"),
    ("f_3dflippo", "frei0r=filter_name=3dflippo:filter_params=0.5|0.5|0.55|0.5|0.5|0.5|0.5|0.5|0.5|0.5|0.5{en}"),
]

W, H = 540, 960          # nhỏ cho nhanh — chỉ để SOI, không phải để đo chi phí
FPS = 30


def render(chain: str, dst: str) -> tuple[int, str]:
    vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1"
          % (W, H, W, H))
    if chain:
        vf += "," + chain
    cmd = [FF, "-y", "-hide_banner", "-nostats", "-ss", f"{MOC:.3f}",
           "-t", f"{DAI:.3f}", "-i", SRC, "-an", "-vf", vf,
           "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast",
           "-crf", "16", "-pix_fmt", "yuv420p", dst]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       timeout=180,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return p.returncode, (p.stderr or "")[-400:]


def khung(path: str, t: float) -> "np.ndarray | None":
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, fr = cap.read()
    cap.release()
    return fr if ok else None


def main() -> int:
    if not os.path.exists(SRC):
        print("KHONG CO NGUON:", SRC)
        return 2
    td = tempfile.mkdtemp(prefix="_hu_thu_")
    goc_p = os.path.join(td, "goc.mp4")
    rc, log = render("", goc_p)
    if rc != 0:
        print("render GOC loi:", log)
        return 2
    g = khung(goc_p, GIUA)
    if g is None:
        print("khong doc duoc khung goc")
        return 2
    gy = cv2.cvtColor(g, cv2.COLOR_BGR2YUV)
    print(f"[goc] sang TB Y={gy[:, :, 0].mean():.1f} U={gy[:, :, 1].mean():.1f} "
          f"V={gy[:, :, 2].mean():.1f}")
    print(f"{'ten':<16}{'ms':>6}{'%px':>7}{'|dY|':>7}{'dU':>7}{'dV':>7}  ghi chu")
    for ten, mau in UV:
        if not mau:
            continue
        chain = (mau.replace("{en}", f":enable='between(t,{A},{B})'")
                    .replace("{a}", f"{A}").replace("{b}", f"{B}")
                    .replace("WxH", f"{W}x{H}").replace("SFPS", str(FPS)))
        dst = os.path.join(td, ten + ".mp4")
        t0 = time.time()
        rc, log = render(chain, dst)
        ms = (time.time() - t0) * 1000
        if rc != 0 or not os.path.exists(dst) or os.path.getsize(dst) < 1000:
            dong = [x for x in log.splitlines() if x.strip()][-1:] or [""]
            print(f"{ten:<16}{ms:6.0f}   LOI  {dong[0][:74]}")
            continue
        f = khung(dst, GIUA)
        if f is None or f.shape != g.shape:
            print(f"{ten:<16}{ms:6.0f}   LOI  khung {None if f is None else f.shape}")
            continue
        fy = cv2.cvtColor(f, cv2.COLOR_BGR2YUV)
        dy = np.abs(fy[:, :, 0].astype(np.int16) - gy[:, :, 0].astype(np.int16))
        pct = float((dy > 12).mean() * 100)
        print(f"{ten:<16}{ms:6.0f}{pct:7.1f}{dy.mean():7.1f}"
              f"{fy[:, :, 1].mean() - gy[:, :, 1].mean():7.2f}"
              f"{fy[:, :, 2].mean() - gy[:, :, 2].mean():7.2f}")
    print("\nthu muc:", td)
    return 0


if __name__ == "__main__":
    sys.exit(main())
