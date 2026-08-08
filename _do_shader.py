# -*- coding: utf-8 -*-
r"""ĐO 6 SHADER `libplacebo` TRÊN VIDEO THẬT — nối được hay phải gỡ?

CÂU HỎI PHẢI TRẢ LỜI BẰNG SỐ (không đoán):
  1. `libplacebo` có chạy thật không, hay lại là bẫy "rc=0 mà 0 khung" như
     `xfade_opencl`?  -> ĐẾM KHUNG bằng ffprobe sau MỌI lần xuất.
  2. `libplacebo` KHÔNG có `enable` -> áp là áp TOÀN CLIP (đúng như hồ sơ ghi).
     Cách vòng qua: `split` + nhánh shader + **`overlay` CÓ timeline `enable`**.
     Phải chứng minh: khung NGOÀI cửa sổ **y hệt gốc**, khung TRONG cửa sổ ĐỔI.
  3. Shader có làm loè màu không -> lệch U/V < 3,0 (`hieu_ung.UV_MAX`).
  4. Shader có THẤY ĐƯỢC không -> % pixel |dY| > 12 phải vượt `nguong_thay`.
  5. Độ đậm chỉnh được không -> alpha `colorchannelmixer=aa=` trên nhánh shader.

CHẠY: `.venv\Scripts\python.exe _do_shader.py`
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _test_guard          # noqa: E402,F401 - KHÔNG mở Explorer, dọn %TEMP%

REPO = os.path.dirname(os.path.abspath(__file__))
FF = os.path.join(REPO, "bin", "ffmpeg.exe")
FP = os.path.join(REPO, "bin", "ffprobe.exe")
SHD = os.path.join(REPO, "app", "assets", "hieu_ung", "shaders")
#: Thư mục đo TỰ DỌN. Đừng đổi sang đường dẫn cố định trên ổ đĩa: phép đo này
#: đẻ ~270 MB mỗi lượt, mà ổ C của anh Hùng đã từng đầy 100% (31/07/2026).
TD = os.path.join(tempfile.gettempdir(), f"do_shader_{os.getpid()}")
CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def chay(args: list) -> tuple[int, float]:
    t0 = time.perf_counter()
    r = subprocess.run([FF, "-y", "-hide_banner", "-v", "error", *args],
                       capture_output=True, text=True, errors="replace",
                       creationflags=CNW)
    return r.returncode, time.perf_counter() - t0


def dem_khung(p: str) -> int:
    try:
        r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                            "-count_frames", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", p],
                           capture_output=True, text=True, creationflags=CNW)
        s = (r.stdout or "").strip().splitlines()
        return int(s[0]) if s and s[0].strip().isdigit() else 0
    except Exception:                                        # noqa: BLE001
        return 0


def khung(vid: str, t: float, ra: str) -> str:
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error", "-ss", f"{t:.3f}",
                    "-i", vid, "-frames:v", "1", ra],
                   capture_output=True, creationflags=CNW)
    return ra


def do_2_khung(a: str, b: str) -> dict:
    """So 2 ảnh: % pixel |dY|>12 · PSNR · lệch U/V trung bình (luật 3)."""
    import cv2
    import numpy as np
    ia, ib = cv2.imread(a), cv2.imread(b)
    if ia is None or ib is None or ia.shape != ib.shape:
        return {"pct": -1.0, "psnr": -1.0, "du": -1.0, "dv": -1.0}
    ya = cv2.cvtColor(ia, cv2.COLOR_BGR2YUV).astype(float)
    yb = cv2.cvtColor(ib, cv2.COLOR_BGR2YUV).astype(float)
    pct = float(np.mean(np.abs(ya[:, :, 0] - yb[:, :, 0]) > 12)) * 100.0
    mse = float(np.mean((ia.astype(float) - ib.astype(float)) ** 2))
    psnr = 99.0 if mse < 1e-9 else float(10 * np.log10(255 * 255 / mse))
    return {"pct": round(pct, 2), "psnr": round(psnr, 2),
            "du": round(float(np.mean(yb[:, :, 1]) - np.mean(ya[:, :, 1])), 2),
            "dv": round(float(np.mean(yb[:, :, 2]) - np.mean(ya[:, :, 2])), 2)}


# --------------------------------------------------------------- NGUỒN THẬT
def nguon() -> str:
    """3 giây phim THẬT, cắt về ĐÚNG khung dọc sản xuất 1080x1920.

    Mốc 100s chứ không phải 20s: hồ sơ cổng 36 — nguồn Nhật ở giây 20 sáng
    trung bình chỉ 3,3/255 (gần đen) nên mọi phép đếm pixel ra ~0 và FAIL OAN.
    """
    import _nguon_nhat
    ds = _nguon_nhat.liet_ke()
    if not ds:
        print("KHÔNG có video Nhật thật -> dừng (không bịa bằng lavfi)")
        sys.exit(2)
    src = ds[9] if len(ds) > 9 else ds[0]
    ra = os.path.join(TD, "goc.mkv")
    rc, _ = chay(["-ss", "100", "-t", "3", "-i", src,
                  "-vf", "crop=ih*9/16:ih,scale=1080:1920,setsar=1",
                  "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                  "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode:v", "cfr",
                  "-an", ra])
    n = dem_khung(ra)
    print(f"NGUỒN: {os.path.basename(src)[:40]}… -> 1080x1920, "
          f"{n} khung, {os.path.getsize(ra) / 1e6:.2f} MB (rc={rc})")
    if n < 80:
        sys.exit(2)
    return ra


def graph(sh: str, aa: float, a: float, b: float) -> str:
    """split -> nhánh shader (GPU) -> alpha -> overlay CÓ `enable` -> hợp lại."""
    return (f"[0:v]split[b][f];"
            f"[f]hwupload,libplacebo=custom_shader_path='{esc(sh)}',"
            f"hwdownload,format=yuv420p,format=yuva420p,"
            f"colorchannelmixer=aa={aa:g}[f2];"
            f"[b][f2]overlay=x=0:y=0:eof_action=pass:"
            f"enable='between(t,{a:.3f},{b:.3f})',format=yuv420p[v]")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(TD, exist_ok=True)
    src = nguon()
    g_ngoai = khung(src, 0.30, os.path.join(TD, "g_ngoai.png"))
    g_trong = khung(src, 1.25, os.path.join(TD, "g_trong.png"))

    # ĐỐI CHỨNG BẮT BUỘC: libplacebo KHÔNG shader. Nếu chính nó đã đổi màu thì
    # mọi số của 6 shader bên dưới là số của libplacebo, không phải của shader.
    dc = os.path.join(TD, "_doi_chung.mkv")
    rc, gy = chay(["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk",
                   "-i", src, "-filter_complex",
                   "[0:v]format=yuv420p,hwupload[x];[x]libplacebo[o];"
                   "[o]hwdownload,format=yuv420p[v]", "-map", "[v]",
                   "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                   "-pix_fmt", "yuv420p", dc])
    n = dem_khung(dc)
    d = do_2_khung(g_trong, khung(dc, 1.25, os.path.join(TD, "dc.png")))
    print(f"\nĐỐI CHỨNG libplacebo KHÔNG shader: rc={rc} · {n} khung · "
          f"{gy:.2f}s · PSNR {d['psnr']} dB · dU {d['du']} dV {d['dv']} · "
          f"%pixel {d['pct']}%")

    hooks = sorted(f for f in os.listdir(SHD) if f.endswith(".hook"))
    print(f"\n{'shader':<14} {'aa':>5} {'rc':>3} {'khung':>6} {'MB':>6} "
          f"{'giây':>6} | TRONG cửa sổ: {'%pixel':>7} {'PSNR':>6} "
          f"{'dU':>6} {'dV':>6} | NGOÀI: {'%pixel':>7} {'PSNR':>6}")
    print("-" * 118)
    ket = {}
    for h in hooks:
        for aa in (0.60, 0.80, 1.00):
            out = os.path.join(TD, f"{h[:-5]}_{aa:g}.mkv")
            rc, gy = chay(["-init_hw_device", "vulkan=vk",
                           "-filter_hw_device", "vk", "-i", src,
                           "-filter_complex",
                           graph(os.path.join(SHD, h), aa, 1.0, 1.5),
                           "-map", "[v]", "-c:v", "libx264",
                           "-preset", "ultrafast", "-crf", "16",
                           "-pix_fmt", "yuv420p", out])
            n = dem_khung(out)
            mb = os.path.getsize(out) / 1e6 if os.path.exists(out) else 0.0
            if n < 1:
                print(f"{h[:-5]:<14} {aa:>5.2f} {rc:>3} {n:>6} {mb:>6.2f} "
                      f"{gy:>6.2f} | ** 0 KHUNG / KHÔNG RA FILE **")
                continue
            tr = do_2_khung(g_trong, khung(out, 1.25,
                                           os.path.join(TD, "_t.png")))
            ng = do_2_khung(g_ngoai, khung(out, 0.30,
                                           os.path.join(TD, "_n.png")))
            print(f"{h[:-5]:<14} {aa:>5.2f} {rc:>3} {n:>6} {mb:>6.2f} "
                  f"{gy:>6.2f} | {tr['pct']:>16.2f} {tr['psnr']:>6.2f} "
                  f"{tr['du']:>6.2f} {tr['dv']:>6.2f} | "
                  f"{ng['pct']:>14.2f} {ng['psnr']:>6.2f}")
            ket[(h, aa)] = (tr, ng)

    print("\nMỐC: THẤY ĐƯỢC = %pixel TRONG >= 8,0 · KHÔNG LOÈ = |dU|,|dV| < 3,0"
          " · KHÔNG RÒ = %pixel NGOÀI = 0,00 và PSNR NGOÀI >= 50 dB")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(TD, ignore_errors=True)
