# -*- coding: utf-8 -*-
r"""SOI MỐC THỜI GIAN đầu ra của `xfade_opencl` — vì sao ra 0 KHUNG / PHÌNH RAM.

## VÌ SAO CÓ FILE NÀY (2 triệu chứng đo được, cùng 1 gốc)
- Không có `fps=` sau `hwdownload`: file ra **0 khung** (ffprobe đếm được -1/0).
- Có `fps=30` sau `hwdownload`: ffmpeg **KHÔNG BAO GIỜ DỪNG** — đo thật
  08/08/2026: **19,1 GB RSS + 364 CPU-giây trong 9 phút** rồi vẫn chạy, phải
  giết tay. Đây là cùng loại tai nạn "1 lệnh trim+concat phình 19,6 GB" đã có
  trong hồ sơ. **Tuyệt đối không để lọt ra máy anh Hùng.**

Cả 2 triệu chứng đều chỉ về MỐC THỜI GIAN (PTS) đầu ra. File này in PTS thật.

## AN TOÀN — MỌI LỆNH Ở ĐÂY ĐỀU CÓ 3 KHOÁ, ĐỪNG GỠ
1. `-frames:v` chặn CỨNG số khung ffmpeg được phép xuất;
2. `timeout=` của subprocess;
3. `-f null` (không ghi file) cho ca soi PTS.
Thiếu 1 trong 3 là lặp lại đúng vụ 19 GB.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="goroi6_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402
from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF = settings.FFMPEG_PATH
td = tempfile.mkdtemp(prefix="goroi6_")
src = _nguon_nhat.mot("JP")
D = 0.30
FPS = 30
TRAN = 120          # trần khung tuyệt đối (4 giây @30fps) — vượt là CÓ BỆNH


def seg(moc: float, ten: str) -> str:
    p = os.path.join(td, ten + ".mp4")
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", f"{D:.3f}", "-i", src, "-an",
                    "-vf", "scale=480:854:force_original_aspect_ratio=increase,"
                           f"crop=480:854,setsar=1,fps={FPS}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", p],
                   capture_output=True, timeout=180, creationflags=CNW)
    return p


def pts(nhan: str, graph: str, ra_map: str = "[v]") -> None:
    """In PTS của tối đa TRAN khung đầu ra. `-f null` + `-frames:v` = an toàn.

    `showinfo` là thứ IN ra `pts_time` — thiếu nó thì cột PTS trống trơn ở MỌI
    ca, kể cả ca đối chứng CPU đang chạy đúng (sập 1 lần lúc 06:58).
    """
    graph = graph.replace(f"{ra_map}", "[vsi];[vsi]showinfo[v]", 1) \
        if graph.endswith(ra_map) else graph
    cmd = [FF, "-y", "-hide_banner", "-v", "info",
           "-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
           "-i", a, "-i", b, "-filter_complex", graph,
           "-map", ra_map, "-frames:v", str(TRAN), "-f", "null", os.devnull]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", timeout=90, creationflags=CNW)
        log = p.stderr or ""
        rc = p.returncode
    except subprocess.TimeoutExpired:
        print(f"  {nhan:<38} ** QUÁ 90s -> TREO (đúng bệnh phình RAM) **")
        return
    ts = [m.group(1) for m in re.finditer(r"pts_time:([-\d.]+)", log)]
    loi = [x for x in log.splitlines()
           if "rror" in x or "Impossible" in x or "not in the" in x]
    print(f"  {nhan:<38} rc={rc:<3} khung={len(ts):<4} "
          f"pts đầu={ts[:4]} … cuối={ts[-2:]}")
    if len(ts) >= TRAN:
        print("      ** CHẠM TRẦN {} KHUNG cho vùng chồng {}s (kỳ vọng {}) -> "
              "SINH KHUNG VÔ TẬN **".format(TRAN, D, int(round(D * FPS))))
    if loi:
        print("      lỗi:", loi[-1][:110])


a, b = seg(100.0, "a"), seg(300.0, "b")
print(f"[nguồn] {os.path.basename(src)}  ·  2 đoạn {D}s @{FPS}fps "
      f"(kỳ vọng ra {int(round(D * FPS))} khung)")
print(f"[GPU] OpenCL={GPU.co_opencl()}")
N = GPU.CHUAN_HOA
KER = GPU.duong_filter(GPU.duong_kernel())

print("\n--- A. `xfade` CPU thường (ĐỐI CHỨNG: đây là cái ĐÚNG) ---")
pts("xfade=fade CPU",
    f"[0:v][1:v]xfade=transition=fade:duration={D:.3f}:offset=0[v]")

print("\n--- B. `xfade_opencl` với kiểu DỰNG SẴN (không phải kernel tôi viết) ---")
for k in ("fade", "wipeleft"):
    pts(f"xfade_opencl={k}",
        f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
        f"[x][y]xfade_opencl=transition={k}:duration={D:.3f}:offset=0[o];"
        f"[o]hwdownload,format=yuv420p[v]")

print("\n--- C. `xfade_opencl` custom kernel (gl-transitions) ---")
pts("custom gl_gio, KHÔNG fps",
    f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
    f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gio:"
    f"duration={D:.3f}:offset=0[o];[o]hwdownload,format=yuv420p[v]")
pts("custom gl_gio + fps=30 (ca PHÌNH RAM)",
    f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
    f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gio:"
    f"duration={D:.3f}:offset=0[o];[o]hwdownload,format=yuv420p,fps={FPS}[v]")
pts("custom gl_gio + setpts=N/FR/TB",
    f"[0:v]{N},hwupload[x];[1:v]{N},hwupload[y];"
    f"[x][y]xfade_opencl=transition=custom:source='{KER}':kernel=gl_gio:"
    f"duration={D:.3f}:offset=0[o];"
    f"[o]hwdownload,format=yuv420p,setpts=N/{FPS}/TB[v]")

print(f"\nthư mục: {td}")
