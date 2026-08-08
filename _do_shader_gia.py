# -*- coding: utf-8 -*-
r"""GIÁ PHẢI TRẢ của nhánh shader `libplacebo` — đo ĐAN XEN trên clip 24 giây.

VÌ SAO ĐAN XEN (bài học đã sai 2 lần): máy anh Hùng LUÔN có app tải video chạy
nền, chạy liền mạch A rồi B là đo cả cơn tải chứ không đo bản vá. Ở đây chạy
A,B,C,A,B,C… rồi lấy TRUNG VỊ.

3 cách dựng, cùng 1 clip, cùng cửa sổ 0,45 giây:
  A = KHÔNG hiệu ứng                       (mốc gốc)
  B = hiệu ứng CPU đang dùng (`eq=contrast`, có `enable`)
  C = shader GPU (`split` + libplacebo + `overlay` có `enable`)

Đo WALL + CPU-GIÂY (GetProcessTimes qua psutil) — CPU-giây mới là cái đắt khi
10 làn chạy cùng lúc.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _test_guard          # noqa: E402,F401

REPO = os.path.dirname(os.path.abspath(__file__))
FF = os.path.join(REPO, "bin", "ffmpeg.exe")
FP = os.path.join(REPO, "bin", "ffprobe.exe")
SHD = os.path.join(REPO, "app", "assets", "hieu_ung", "shaders")
#: Thư mục đo TỰ DỌN (nguồn 24s 1080x1920 nặng 65 MB) — ổ C từng đầy 100%.
TD = os.path.join(tempfile.gettempdir(), f"do_shader_gia_{os.getpid()}")
CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
A, B = 8.0, 8.45          # cửa sổ hiệu ứng (0,45s — đúng `dai` mặc định)


def esc(p):
    return str(p).replace("\\", "/").replace(":", "\\:")


def chay_do(args: list) -> tuple[int, float, float]:
    """(rc, wall, CPU-giây của CHÍNH tiến trình ffmpeg + con)."""
    import psutil
    t0 = time.perf_counter()
    p = subprocess.Popen([FF, "-y", "-hide_banner", "-v", "error", *args],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         creationflags=CNW)
    cpu = 0.0
    try:
        ps = psutil.Process(p.pid)
        while p.poll() is None:
            try:
                c = ps.cpu_times()
                cpu = c.user + c.system
            except psutil.Error:
                break
            time.sleep(0.05)
        try:
            c = ps.cpu_times()
            cpu = max(cpu, c.user + c.system)
        except psutil.Error:
            pass
    except psutil.Error:
        pass
    p.wait()
    return p.returncode, time.perf_counter() - t0, cpu


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", p],
                       capture_output=True, text=True, creationflags=CNW)
    s = (r.stdout or "").strip().splitlines()
    return int(s[0]) if s and s[0].strip().isdigit() else 0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(TD, exist_ok=True)
    import _nguon_nhat
    ds = _nguon_nhat.liet_ke()
    if not ds:
        print("KHÔNG có video thật -> dừng")
        sys.exit(2)
    src24 = os.path.join(TD, "goc24.mkv")
    if not os.path.exists(src24):
        subprocess.run([FF, "-y", "-hide_banner", "-v", "error",
                        "-ss", "100", "-t", "24", "-i", ds[9],
                        "-vf", "crop=ih*9/16:ih,scale=1080:1920,setsar=1",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode:v", "cfr",
                        "-an", src24], creationflags=CNW)
    n0 = dem_khung(src24)
    print(f"NGUỒN 24s 1080x1920: {n0} khung · "
          f"{os.path.getsize(src24) / 1e6:.1f} MB")

    sh = os.path.join(SHD, "hat_phim.hook")
    ca = {
        "A KHÔNG hiệu ứng": ([], "[0:v]null[v]"),
        "B CPU eq=contrast": ([], f"[0:v]eq=contrast=1.35:"
                                  f"enable='between(t,{A},{B})'[v]"),
        "C GPU cả clip    ": (["-init_hw_device", "vulkan=vk",
                               "-filter_hw_device", "vk"],
                              f"[0:v]split[b][f];[f]hwupload,"
                              f"libplacebo=custom_shader_path='{esc(sh)}',"
                              f"hwdownload,format=yuv420p,format=yuva420p,"
                              f"colorchannelmixer=aa=0.6[f2];"
                              f"[b][f2]overlay=x=0:y=0:eof_action=pass:"
                              f"enable='between(t,{A},{B})',format=yuv420p[v]"),
        "D GPU CHỈ cửa sổ ": (["-init_hw_device", "vulkan=vk",
                               "-filter_hw_device", "vk"],
                              f"[0:v]split=3[p0][p1][p2];"
                              f"[p0]trim=end={A},setpts=PTS-STARTPTS[b0];"
                              f"[p1]trim=start={A}:end={B},setpts=PTS-STARTPTS,"
                              f"hwupload,libplacebo="
                              f"custom_shader_path='{esc(sh)}',"
                              f"hwdownload,format=yuv420p,format=yuva420p,"
                              f"colorchannelmixer=aa=0.6,format=yuv420p[b1];"
                              f"[p2]trim=start={B},setpts=PTS-STARTPTS[b2];"
                              f"[b0][b1][b2]concat=n=3:v=1:a=0[v]"),
    }
    kq = {k: {"w": [], "c": [], "n": []} for k in ca}
    LAP = 4
    print(f"\nchạy ĐAN XEN {LAP} vòng (A,B,C,A,B,C…)")
    for v in range(LAP):
        for ten, (pre, g) in ca.items():
            out = os.path.join(TD, f"gia_{ten[0]}.mp4")
            rc, w, c = chay_do([*pre, "-i", src24, "-filter_complex", g,
                                "-map", "[v]", "-c:v", "libx264",
                                "-preset", "veryfast", "-crf", "20",
                                "-pix_fmt", "yuv420p", out])
            n = dem_khung(out)
            kq[ten]["w"].append(w)
            kq[ten]["c"].append(c)
            kq[ten]["n"].append(n)
            print(f"  vòng {v + 1} · {ten}: rc={rc} · {n} khung · "
                  f"wall {w:.2f}s · CPU {c:.2f}s")

    def tv(xs):
        ys = sorted(xs)
        n = len(ys)
        return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2

    print(f"\n{'cách dựng':<20} {'khung':>6} {'wall (trung vị)':>16} "
          f"{'CPU-giây':>10} {'so với A':>10}")
    print("-" * 70)
    wa = tv(kq["A KHÔNG hiệu ứng"]["w"])
    ca_ = tv(kq["A KHÔNG hiệu ứng"]["c"])
    for ten in ca:
        w, c = tv(kq[ten]["w"]), tv(kq[ten]["c"])
        print(f"{ten:<20} {min(kq[ten]['n']):>6} {w:>14.2f}s "
              f"{c:>9.2f}s {w / wa:>9.2f}x")
    print(f"\nCPU-giây so A: B {tv(kq['B CPU eq=contrast']['c']) / ca_:.2f}x · "
          f"C {tv(kq['C GPU cả clip    ']['c']) / ca_:.2f}x")
    print(f"SỐ KHUNG phải BẰNG NHAU cả 3: "
          f"{[min(kq[t]['n']) for t in ca]}")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(TD, ignore_errors=True)
