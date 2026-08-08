# -*- coding: utf-8 -*-
r"""ĐO: `xfade` và `acrossfade` xử lý "đoạn B NGẮN HƠN d" KHÁC NHAU hay không.

Nghi vấn: `_bu_xfade` chỉ kẹp `d` theo PHIM CÒN LẠI sau `segs[i][1]`, KHÔNG kẹp
theo ĐỘ DÀI ĐOẠN KẾ. `_graph_xfade` rồi dùng CÙNG một `d` cho `xfade` (hình) và
`acrossfade` (tiếng). Nếu 2 filter cắt khác nhau khi B ngắn hơn `d` thì tiếng và
hình lệch nhau — đúng loại lỗi v1.87 "hình một đằng tiếng một đằng".

Đo bằng ffmpeg THẬT, in độ dài LUỒNG HÌNH và LUỒNG TIẾNG riêng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
_SB = tempfile.mkdtemp(prefix="dobu_")
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

from config import settings                                    # noqa: E402

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
td = tempfile.mkdtemp(prefix="dobu_")
A_DAI, FPS = 2.0, 30


def seg(dai: float, mau: str, ten: str) -> str:
    p = os.path.join(td, ten + ".mkv")
    subprocess.run(
        [FF, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", f"color=c={mau}:s=320x240:r={FPS}:d={dai:g}",
         "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={dai:g}",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000",
         "-ac", "2", "-shortest", "-r", str(FPS), "-fps_mode:v", "cfr", p],
        capture_output=True, timeout=180, creationflags=CNW)
    return p


def dai_luong(p: str, loai: str) -> float:
    """Độ dài LUỒNG (giây). ĐẾM THẬT chứ không đọc tag `duration`.

    LỖI ĐO đã sập 1 lần: Matroska KHÔNG ghi `stream=duration` cho từng luồng ->
    ffprobe trả rỗng -> hàm trả -1.000 ở MỌI ca và bảng ra "lệch 0ms" cho tất cả,
    trông y như không có lỗi. Nay đếm KHUNG (hình) và ĐẾM MẪU (tiếng).
    """
    if loai.startswith("v"):
        r = subprocess.run([FP, "-v", "error", "-select_streams", loai,
                            "-count_frames", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", p],
                           capture_output=True, text=True, creationflags=CNW)
        s = (r.stdout or "").strip().splitlines()
        return (int(s[0]) / FPS) if s and s[0].strip().isdigit() else -1.0
    r = subprocess.run([FP, "-v", "error", "-select_streams", loai,
                        "-count_packets", "-show_entries",
                        "stream=nb_read_packets,sample_rate,codec_name",
                        "-of", "csv=p=0", p],
                       capture_output=True, text=True, creationflags=CNW)
    # PCM: 1 gói không cố định số mẫu -> dùng ffmpeg đọc hết rồi lấy time cuối
    r2 = subprocess.run([FF, "-v", "error", "-i", p, "-map", loai,
                         "-af", "astats=metadata=1:reset=0", "-f", "null",
                         os.devnull], capture_output=True, text=True,
                        creationflags=CNW)
    del r, r2
    r3 = subprocess.run([FP, "-v", "error", "-select_streams", loai,
                         "-show_entries", "packet=pts_time,duration_time",
                         "-of", "csv=p=0", p], capture_output=True, text=True,
                        creationflags=CNW)
    dong = [x for x in (r3.stdout or "").strip().splitlines() if "," in x]
    if not dong:
        return -1.0
    a, b = dong[-1].split(",")[:2]
    try:
        return float(a) + float(b)
    except ValueError:
        return -1.0


# DỰNG ĐÚNG NHƯ `_extract_segments_to_temp` + `_graph_xfade` làm:
#   file A dài (A_DAI + d)  — đã LẤY THÊM `d` giây phim ở cuối (phần bù)
#   offset = A_DAI (độ dài GỐC) -> tổng phải = A_DAI + B, timeline bất biến.
# LỖI ĐO đã sập 1 lần: để file A dài đúng A_DAI rồi vẫn đặt offset = A_DAI thì
# xfade không còn khung nào của A để hoà -> mọi ca đều sai, kết luận hớ.
print(f"A gốc {A_DAI}s, file A dài {A_DAI}+d (đã bù) · offset = {A_DAI}s")
print("kỳ vọng CẢ HÌNH LẪN TIẾNG ra = A_gốc + B")
print(f"{'B dài':>7}{'d':>7}{'kỳ vọng':>9}{'hình ra':>10}{'tiếng ra':>10}"
      f"{'LỆCH':>9}   kết luận")
print("-" * 82)
for b_dai in (0.20, 0.30, 0.35, 0.40, 0.50, 0.80, 2.00):
    for d in (0.40, 0.30):
        a = seg(A_DAI + d, "red", f"a{d}")
        b = seg(b_dai, "blue", f"b{b_dai}")
        ky = A_DAI + b_dai
        out = os.path.join(td, f"o_{b_dai}_{d}.mkv")
        g = (f"[0:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[v0];"
             f"[1:v]settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[v1];"
             f"[0:a]asetpts=N/SR/TB[a0];[1:a]asetpts=N/SR/TB[a1];"
             f"[v0][v1]xfade=transition=fade:duration={d:.3f}:"
             f"offset={A_DAI:.3f}[vo];"
             f"[a0][a1]acrossfade=d={d:.3f}:c1=tri:c2=tri[ao]")
        r = subprocess.run(
            [FF, "-y", "-hide_banner", "-v", "error", "-i", a, "-i", b,
             "-filter_complex", g, "-map", "[vo]", "-map", "[ao]",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", out],
            capture_output=True, text=True, errors="replace", timeout=180,
            creationflags=CNW)
        if r.returncode:
            print(f"{b_dai:7.2f}{d:7.2f}   rc={r.returncode} "
                  f"{(r.stderr or '')[-70:]}")
            continue
        dv, da_ = dai_luong(out, "v:0"), dai_luong(out, "a:0")
        lech = abs(dv - da_) * 1000
        sai_ky = max(abs(dv - ky), abs(da_ - ky)) * 1000
        kq = ("OK" if (lech < 80 and sai_ky < 80)
              else f"** lệch tiếng-hình {lech:.0f}ms · sai kỳ vọng "
                   f"{sai_ky:.0f}ms **")
        print(f"{b_dai:7.2f}{d:7.2f}{ky:9.2f}{dv:10.3f}{da_:10.3f}"
              f"{lech:8.0f}ms   {kq}")
# TỰ DỌN: quy tắc sắt của repo — script đo KHÔNG được để rác %TEMP% trên máy
# anh Hùng (ổ C đã từng đầy 100% vì đúng loại rác này).
import shutil                                                  # noqa: E402
shutil.rmtree(td, ignore_errors=True)
shutil.rmtree(_SB, ignore_errors=True)
print("\n(đã tự dọn thư mục tạm)")
