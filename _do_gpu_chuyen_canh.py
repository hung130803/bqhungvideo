# -*- coding: utf-8 -*-
r"""CỔNG RENDER THẬT cho 2 NGUỒN GPU: `xfade_opencl` + `libplacebo`.

Không tin tên hiệu ứng, không tin "ffmpeg có filter": **render bằng GPU thật,
trích khung, ĐẾM PIXEL, đo U/V, đo CPU-giây**. Đúng bẫy đã sập 2 lần của việc
này (hiệu ứng báo `0,03 CPU-giây` thực ra là LỖI FILTER; `tim.mp4` lệch V=142).

## 3 điều script này phải chứng minh
1. **CHUYỂN CẢNH CÓ XẢY RA**: khung GIỮA vùng chồng phải KHÁC cả khung đầu (A)
   lẫn khung cuối (B). Chỉ khác A thôi là chưa đủ — cắt thẳng cũng khác A.
2. **KHÔNG LOÈ MÀU**: U/V trung bình lệch < 3 so với bản đối chứng (bài học
   `tim.mp4` tím cả khung).
3. **ĐÚNG SỐ KHUNG**: `d` giây × fps. Thiếu khung = bẫy "ngữ cảnh hwframe" làm
   clip CỤT trong im lặng (đo được 53/90 khung ở bản dựng sai).

## Đo CPU-GIÂY, không đo wall
Mục đích cả việc này là **chuyển tải từ CPU sang GPU** (máy anh Hùng CPU 96,7% /
GPU 11,3%). Vì vậy cột quyết định là CPU-giây của tiến trình ffmpeg, đối chứng
với `xfade` CPU làm CÙNG việc.

Chạy: .venv\Scripts\python _do_gpu_chuyen_canh.py [--lap 3] [--json ...]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

_SB = os.path.join(tempfile.gettempdir(), f"gpu_do_{os.getpid()}")
os.makedirs(_SB, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

import _nguon_nhat                                            # noqa: E402
from app.core import hieu_ung_gpu as GPU                       # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
W, H, FPS = 720, 1280, 30
D = 0.5                    # độ dài vùng chồng (giây) — đúng cỡ app dùng
#: 2 mốc phim SÁNG (bài học cổng 36: mốc tối làm ca đếm pixel FAIL OAN —
#: giây 20 của nguồn Nhật sáng TB chỉ 3,3/255)
MOC_A, MOC_B = 100.0, 300.0
UV_MAX = 3.0


def _ff() -> str:
    from config import settings
    return settings.FFMPEG_PATH


def _probe(p: str, khoa: str) -> str:
    from config import settings
    r = subprocess.run([settings.FFPROBE_PATH, "-v", "error", "-select_streams",
                        "v:0", "-count_frames", "-show_entries",
                        f"stream={khoa}", "-of", "csv=p=0", p],
                       capture_output=True, text=True, creationflags=CNW)
    return (r.stdout or "").strip().splitlines()[0] if r.stdout.strip() else ""


def chay_do(args: list, lap: int) -> tuple[int, str, float, float]:
    """Chạy ffmpeg `lap` lần, trả (rc, log, wall trung vị, CPU-giây trung vị)."""
    walls, cpus, rc, log = [], [], -1, ""
    for _ in range(max(1, lap)):
        cmd = [_ff(), "-y", "-hide_banner", "-nostats", "-v", "error",
               *[str(x) for x in args]]
        t0 = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             errors="replace", creationflags=CNW)
        cpu = 0.0
        try:
            pr = psutil.Process(p.pid)
            while p.poll() is None:
                try:
                    c = pr.cpu_times()
                    cpu = c.user + c.system
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                time.sleep(0.02)
        except psutil.NoSuchProcess:
            pass
        out = p.stdout.read() if p.stdout else ""
        p.wait()
        rc, log = p.returncode, out[-400:]
        walls.append(time.time() - t0)
        cpus.append(cpu)
    return rc, log, float(np.median(walls)), float(np.median(cpus))


def khung_yuv(path: str, t: float):
    """Khung ở giây `t` — ĐỌC TUẦN TỰ, không seek theo mili-giây.

    **LỖI ĐO đã sập 1 lần (08/08/2026):** clip vùng chồng chỉ 0,5 s (15 khung);
    `cap.set(CAP_PROP_POS_MSEC, 250)` trả `ok=False` -> hàm trả None -> cả 24
    kernel bị báo "không đọc được khung ra" và bảng kết quả TRẮNG TRƠN, trông y
    như 24 kernel đều hỏng. Kernel không sai một dòng nào — PHÉP ĐO sai. Đọc
    tuần tự thì clip ngắn cỡ nào cũng lấy được khung.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    can = max(0, int(round(t * (fps if fps > 1 else FPS))))
    fr = last = None
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        last = f
        if i == can:
            fr = f
            break
        i += 1
    cap.release()
    fr = fr if fr is not None else last
    return cv2.cvtColor(fr, cv2.COLOR_BGR2YUV) if fr is not None else None


def pct_khac(a, b) -> float:
    """% pixel lệch SÁNG > 12 giữa 2 khung YUV."""
    dy = np.abs(a[:, :, 0].astype(np.int16) - b[:, :, 0].astype(np.int16))
    return float((dy > 12).mean() * 100.0)


def uv_tb(a) -> tuple[float, float]:
    return float(a[:, :, 1].mean()), float(a[:, :, 2].mean())


def may_ranh() -> tuple[bool, str]:
    c = psutil.cpu_percent(interval=3.0)
    la = [p.info["name"] for p in psutil.process_iter(["name"])
          if (p.info["name"] or "").lower() in ("ffmpeg.exe", "bqhungvideo.exe")]
    return (c < 25 and not la), f"cpu {c:.1f}% · tiến trình lạ {la or 'không'}"


def dung_doan(src: str, td: str) -> tuple[str, str]:
    """2 đoạn dài ĐÚNG D giây, cùng thông số — 2 đầu vào của vùng chồng."""
    ra = []
    for i, moc in enumerate((MOC_A, MOC_B)):
        p = os.path.join(td, f"seg{i}.mp4")
        subprocess.run([_ff(), "-y", "-hide_banner", "-v", "error",
                        "-ss", f"{moc:.3f}", "-t", f"{D:.3f}", "-i", src,
                        "-an", "-vf",
                        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                        f"crop={W}:{H},setsar=1,fps={FPS}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                        "-pix_fmt", "yuv420p", p],
                       capture_output=True, timeout=300, creationflags=CNW)
        ra.append(p)
    return ra[0], ra[1]


# =====================================================================
def do_chuyen_canh(src: str, td: str, lap: int) -> tuple[list, dict]:
    a, b = dung_doan(src, td)
    ka, kb = khung_yuv(a, D * 0.5), khung_yuv(b, D * 0.5)
    if ka is None or kb is None:
        print("không đọc được khung 2 đoạn nguồn")
        return [], {}
    print(f"\n2 đoạn thử: {W}x{H} {FPS}fps, mỗi đoạn {D}s "
          f"(giây {MOC_A:.0f} và {MOC_B:.0f}) · khác nhau "
          f"{pct_khac(ka, kb):.1f}% pixel")

    # ---- ĐỐI CHỨNG CPU: `xfade` thường làm ĐÚNG việc đó ----
    out_cpu = os.path.join(td, "cpu.mp4")
    rc, log, w_cpu, c_cpu = chay_do(
        ["-i", a, "-i", b, "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={D:.3f}:offset=0[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", out_cpu], lap)
    print(f"ĐỐI CHỨNG CPU (`xfade=fade`): rc={rc} · wall {w_cpu:.3f}s · "
          f"CPU {c_cpu:.3f} giây")
    doi_chung = {"wall": w_cpu, "cpu": c_cpu, "rc": rc}

    # ---- CHI PHÍ KHỞI TẠO GPU (đo RIÊNG, nếu không sẽ kết luận hớ) ----
    # Mở thiết bị OpenCL/Vulkan tốn CPU CỐ ĐỊNH mỗi lệnh ffmpeg. Với chuyển cảnh
    # chỉ 0,3-0,5 s thì phí này có thể LỚN HƠN toàn bộ phần tiết kiệm được ->
    # phải tách ra mới nói được GPU lãi hay lỗ.
    _rc, _lg, w_kt, c_kt = chay_do(
        ["-init_hw_device", "opencl=ocl", "-filter_hw_device", "ocl",
         "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.05",
         "-f", "null", os.devnull], lap)
    _rc2, _lg2, w_k2, c_k2 = chay_do(
        ["-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.05",
         "-f", "null", os.devnull], lap)
    doi_chung["cpu_mo_opencl"] = c_kt - c_k2
    print(f"CHI PHÍ MỞ THIẾT BỊ OpenCL (đo riêng): {c_kt:.3f} - {c_k2:.3f} = "
          f"**{c_kt - c_k2:.3f} CPU-giây/lệnh** (phí CỐ ĐỊNH, không phụ thuộc "
          f"độ dài chuyển cảnh)")

    if not GPU.co_opencl():
        print("\n** MÁY NÀY KHÔNG CHẠY ĐƯỢC OpenCL -> nhóm GPU tự TẮT (đúng "
              "thiết kế fallback êm, app vẫn xuất bình thường) **")
        return [], doi_chung

    print(f"\n{'kiểu':<22}{'tên tiếng Việt':<26}{'khung':>7}{'vsA':>7}"
          f"{'vsB':>7}{'dU':>7}{'dV':>7}{'CPU-giây':>10}{'so CPU':>8}  kết luận")
    print("-" * 118)
    ket = []
    for khoa, h in GPU.KHO_GPU.items():
        out = os.path.join(td, f"g_{khoa}.mp4")
        rc, log, wall, cpu = chay_do(
            GPU.lenh_vung_chong(a, b, out, khoa, D, fps=FPS,
                                enc=["-c:v", "libx264", "-preset", "veryfast",
                                     "-crf", "18", "-pix_fmt", "yuv420p"]), lap)
        r = {"khoa": khoa, "ten": h.ten, "capcut": h.capcut, "goc": h.goc,
             "rc": rc, "wall": wall, "cpu": cpu}
        if rc != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            r["kq"] = "LỖI: " + (log.splitlines()[-1][:60] if log.strip() else "rc≠0")
            ket.append(r)
            print(f"{khoa:<22}{h.ten:<26}{'-':>7}{'-':>7}{'-':>7}{'-':>7}"
                  f"{'-':>7}{'-':>10}{'-':>8}  {r['kq']}")
            continue
        nf = _probe(out, "nb_read_frames")
        r["khung"] = int(nf) if nf.isdigit() else -1
        ky_vong = int(round(D * FPS))
        km = khung_yuv(out, D * 0.5)         # khung GIỮA vùng chồng
        if km is None:
            # KHÔNG im lặng: bảng trắng trơn từng làm tưởng 24 kernel đều hỏng
            r["kq"] = "PHÉP ĐO lỗi: không đọc được khung ra"
            ket.append(r)
            print(f"{khoa:<22}{h.ten:<26}{r['khung']:>7}{'?':>7}{'?':>7}"
                  f"{'?':>7}{'?':>7}{cpu:>10.3f}{'-':>8}  {r['kq']}")
            continue
        r["vsA"], r["vsB"] = pct_khac(km, ka), pct_khac(km, kb)
        u, v = uv_tb(km)
        ua, va = uv_tb(ka)
        ub, vb = uv_tb(kb)
        # đối chứng U/V = TRUNG BÌNH 2 đoạn (giữa chuyển cảnh là pha trộn)
        r["dU"], r["dV"] = u - (ua + ub) / 2.0, v - (va + vb) / 2.0
        # ---- chấm ----
        ly = []
        if r["khung"] != ky_vong:
            ly.append(f"CỤT KHUNG {r['khung']}/{ky_vong}")
        if r["vsA"] < 8.0:
            ly.append(f"không khác A ({r['vsA']:.1f}%)")
        if r["vsB"] < 8.0:
            ly.append(f"không khác B ({r['vsB']:.1f}%)")
        if abs(r["dU"]) >= UV_MAX or abs(r["dV"]) >= UV_MAX:
            ly.append(f"LOÈ MÀU (U{r['dU']:+.1f} V{r['dV']:+.1f})")
        r["kq"] = "OK" if not ly else " · ".join(ly)
        r["so_cpu"] = (cpu / c_cpu) if c_cpu > 0 else 0.0
        ket.append(r)
        print(f"{khoa:<22}{h.ten:<26}{r['khung']:>7}{r['vsA']:>6.1f}%"
              f"{r['vsB']:>6.1f}%{r['dU']:>7.2f}{r['dV']:>7.2f}{cpu:>10.3f}"
              f"{r['so_cpu']:>7.2f}x  {r['kq']}")
    return ket, doi_chung


def do_shader(src: str, td: str, lap: int) -> list:
    if not GPU.co_libplacebo():
        print("\n** MÁY NÀY KHÔNG CHẠY ĐƯỢC libplacebo/Vulkan -> nhóm shader tự"
              " TẮT (fallback êm) **")
        return []
    seg = os.path.join(td, "sh_src.mp4")
    subprocess.run([_ff(), "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{MOC_A:.3f}", "-t", "1.0", "-i", src, "-an",
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                           f"crop={W}:{H},setsar=1,fps={FPS}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                    "-pix_fmt", "yuv420p", seg],
                   capture_output=True, timeout=300, creationflags=CNW)
    # ĐỐI CHỨNG: libplacebo KHÔNG shader. Bắt buộc — libplacebo tự đổi màu/tone
    # nên so với NGUỒN sẽ ra "có đổi" dù shader không chạy (bẫy 0,03 CPU-giây).
    gd = os.path.join(td, "lp_khong_shader.mp4")
    rc0, log0, w0, c0 = chay_do(
        ["-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk", "-i", seg,
         "-filter_complex",
         "[0:v]format=yuv420p,hwupload[x];[x]libplacebo[o];"
         "[o]hwdownload,format=yuv420p[v]", "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", gd], lap)
    k0 = khung_yuv(gd, 0.5) if rc0 == 0 else None
    print(f"\nĐỐI CHỨNG libplacebo KHÔNG shader: rc={rc0} · CPU {c0:.3f} giây")
    if k0 is None:
        print("  -> không dựng được đối chứng, BỎ nhóm shader (không kết luận hớ)")
        return []
    print(f"\n{'shader':<20}{'khung':>7}{'đổi vs đối chứng':>19}{'dU':>7}{'dV':>7}"
          f"{'CPU-giây':>10}  kết luận")
    print("-" * 90)
    ra = []
    for ten in sorted(f for f in os.listdir(GPU.thu_muc_shader())
                      if f.endswith(".hook")):
        out = os.path.join(td, "sh_" + ten + ".mp4")
        rc, log, wall, cpu = chay_do(
            GPU.lenh_shader(seg, out, ten,
                            enc=["-c:v", "libx264", "-preset", "veryfast",
                                 "-crf", "18", "-pix_fmt", "yuv420p"]), lap)
        r = {"shader": ten, "rc": rc, "wall": wall, "cpu": cpu}
        if rc != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            r["kq"] = "LỖI: " + (log.splitlines()[-1][:55] if log.strip() else "rc≠0")
            ra.append(r)
            print(f"{ten:<20}{'-':>7}{'-':>19}{'-':>7}{'-':>7}{'-':>10}  {r['kq']}")
            continue
        nf = _probe(out, "nb_read_frames")
        r["khung"] = int(nf) if nf.isdigit() else -1
        km = khung_yuv(out, 0.5)
        if km is None:
            r["kq"] = "không đọc được khung"
            ra.append(r)
            continue
        r["pct"] = pct_khac(km, k0)
        u, v = uv_tb(km)
        u0, v0 = uv_tb(k0)
        r["dU"], r["dV"] = u - u0, v - v0
        ly = []
        if r["khung"] != int(round(1.0 * FPS)):
            ly.append(f"CỤT KHUNG {r['khung']}/{FPS}")
        if r["pct"] < 3.0:
            ly.append(f"KHÔNG THẤY ĐƯỢC ({r['pct']:.1f}% — shader có chạy không?)")
        if abs(r["dU"]) >= UV_MAX or abs(r["dV"]) >= UV_MAX:
            ly.append(f"LOÈ MÀU (U{r['dU']:+.1f} V{r['dV']:+.1f})")
        r["kq"] = "OK" if not ly else " · ".join(ly)
        ra.append(r)
        print(f"{ten:<20}{r['khung']:>7}{r['pct']:>18.1f}%{r['dU']:>7.2f}"
              f"{r['dV']:>7.2f}{cpu:>10.3f}  {r['kq']}")
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lap", type=int, default=3)
    ap.add_argument("--json", default="_ket_gpu.json")
    a = ap.parse_args()

    ok, mo = may_ranh()
    print(f"[máy] {mo}")
    if not ok:
        print("MÁY ĐANG BẬN -> DỪNG (số đo sẽ phồng, xem bài học 'đo A/B phải "
              "đan xen'). Chạy lại khi máy rảnh.")
        return 3
    print(f"[GPU] OpenCL={GPU.co_opencl()} · libplacebo/Vulkan="
          f"{GPU.co_libplacebo()}")
    src = _nguon_nhat.mot("JP")
    if not src:
        print("KHÔNG CÓ nguồn Nhật")
        return 2
    print(f"[nguồn] {os.path.basename(src)} · lặp {a.lap} lấy trung vị")

    td = tempfile.mkdtemp(prefix="_dogpu_")
    try:
        cc, dc = do_chuyen_canh(src, td, a.lap)
        sh = do_shader(src, td, a.lap)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)

    n_ok = sum(1 for r in cc if r.get("kq") == "OK")
    s_ok = sum(1 for r in sh if r.get("kq") == "OK")
    print("\n" + "=" * 74)
    print("SỐ THẬT DÙNG ĐƯỢC (đã render + đếm pixel + đo U/V, không phải đếm tên)")
    print("=" * 74)
    print(f"  nguồn 3 — xfade_opencl + kernel gl-transitions : "
          f"{n_ok}/{len(cc)} kiểu ĐẠT")
    print(f"  nguồn 4 — libplacebo + shader GLSL tự viết     : "
          f"{s_ok}/{len(sh)} shader ĐẠT")
    if dc.get("cpu"):
        gpu_cpu = [r["cpu"] for r in cc if r.get("kq") == "OK"]
        if gpu_cpu:
            print(f"\n  CPU-giây: xfade CPU {dc['cpu']:.3f} · GPU trung vị "
                  f"{float(np.median(gpu_cpu)):.3f} -> "
                  f"{float(np.median(gpu_cpu)) / dc['cpu']:.2f}x")
    xau = [r for r in cc + sh if r.get("kq") not in ("OK", None)]
    if xau:
        print(f"\n  KHÔNG ĐẠT ({len(xau)}):")
        for r in xau:
            print(f"    {r.get('khoa') or r.get('shader'):<24} {r['kq']}")
    with open(os.path.join(ROOT, a.json), "w", encoding="utf-8") as f:
        json.dump({"chuyen_canh": cc, "shader": sh, "doi_chung": dc},
                  f, ensure_ascii=False, indent=1)
    print(f"\nJSON: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
