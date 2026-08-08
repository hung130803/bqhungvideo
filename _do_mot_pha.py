# -*- coding: utf-8 -*-
"""THỬ BỎ PHA TÁCH FILE TẠM — dùng inpoint/outpoint của concat demuxer.

    python _do_mot_pha.py

Ý TƯỞNG: hiện app ghép nhiều đoạn bằng 2 PHA — pha 1 tách MỖI đoạn ra 1 file
`.mkv` cq16 ở NGUYÊN độ phân giải nguồn, pha 2 nối lại rồi dựng khung. Cái giá:
mã hoá thừa 1 lần + giải mã thừa 1 lần + rác đĩa (CLAUDE.md mục 18: `_seg_*.mkv`
để lại 1,71 GB trong %TEMP%).

concat demuxer có `inpoint`/`outpoint`: liệt kê CÙNG 1 file nhiều lần với mốc
vào/ra -> ffmpeg tự seek và phát nối tiếp THEO THỨ TỰ DANH SÁCH. Nếu đúng thì
bỏ được hẳn pha 1.

PHẢI KIỂM 3 BẤT BIẾN (bài học đã ghi trong CLAUDE.md, đừng làm hỏng):
  1. THỨ TỰ hook-first: đoạn sau có thể NẰM TRƯỚC đoạn đầu trên trục thời gian
     gốc (v1.87 từng lệch tiếng-hình vì cái này).
  2. Nguồn VFR (video YouTube) không được trôi lệch tiếng-hình.
  3. Mốc cắt phải ĐÚNG KHUNG (so ảnh với bản 2 pha).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_SBOX = Path(tempfile.gettempdir()) / "_do_luong_sbox"
_SBOX.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SBOX))
os.environ.setdefault("BQ_DB_PATH", str(_SBOX / "do.db"))
os.environ.setdefault("ECO_MODE", "0")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FF = str(REPO / "bin" / "ffmpeg.exe")
FP = str(REPO / "bin" / "ffprobe.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0
from _do_luong_xuat import chon_video, probe                   # noqa: E402
from _do_uu_tien import _chay_prio                             # noqa: E402

DUOI_TB = 0x00004000
OK, XAU = 0, 0


def kiem(dieu: bool, mo_ta: str, them: str = "") -> None:
    global OK, XAU
    if dieu:
        OK += 1
        print(f"    ✓ {mo_ta}" + (f"  ({them})" if them else ""))
    else:
        XAU += 1
        print(f"    ✗ {mo_ta}" + (f"  ({them})" if them else ""))


def viet_list(p: Path, src: str, segs: list) -> str:
    """ffconcat có inpoint/outpoint — CÙNG 1 file, nhiều mốc, ĐÚNG thứ tự."""
    s = "ffconcat version 1.0\n"
    for a, b in segs:
        s += f"file '{str(src).replace(chr(92), '/')}'\n"
        s += f"inpoint {a:.3f}\noutpoint {b:.3f}\n"
    p.write_text(s, encoding="utf-8")
    return str(p)


def khung_rgb(vid: str, t: float, w: int = 160) -> bytes:
    """Trích 1 khung ở giây t, thu nhỏ -> so ảnh giữa 2 bản."""
    ra = Path(tempfile.gettempdir()) / f"_k{os.getpid()}_{int(t*1000)}.rgb"
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", vid, "-vf",
         f"scale={w}:-2", "-frames:v", "1", "-f", "rawvideo",
         "-pix_fmt", "rgb24", str(ra)],
        capture_output=True, creationflags=_NO_WIN)
    d = ra.read_bytes() if ra.exists() else b""
    ra.unlink(missing_ok=True)
    return d if r.returncode == 0 else b""


def lech(a: bytes, b: bytes) -> float:
    """Sai khác trung bình mỗi kênh màu (0..255). <8 = coi như CÙNG khung."""
    if not a or not b or len(a) != len(b):
        return 999.0
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def do_dai(vid: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", vid],
                       capture_output=True, text=True, creationflags=_NO_WIN)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main() -> int:
    print("═" * 74)
    print("THỬ BỎ PHA TÁCH FILE TẠM (concat demuxer inpoint/outpoint)")
    print("═" * 74)
    src = chon_video(1)[0]
    inf = probe(src)
    out = Path(tempfile.mkdtemp(prefix="_do_1pha_"))
    print(f"  nguồn: {Path(src).name[:52]} · {inf['w']}x{inf['h']} "
          f"{inf['fps']:.2f}fps {inf['codec']} {inf['dur']:.0f}s")

    # HOOK-FIRST: đoạn 2 nằm TRƯỚC đoạn 1 trên trục thời gian gốc (ngược thời
    # gian) — đúng cảnh app hay gặp nhất và cũng là chỗ v1.87 từng sai.
    g = max(60.0, inf["dur"] * 0.3)
    segs = [(g + 120.0, g + 140.0), (g, g + 20.0)]
    print(f"  đoạn (HOOK-FIRST, ngược thời gian): "
          f"{segs[0][0]:.0f}-{segs[0][1]:.0f}s rồi {segs[1][0]:.0f}-{segs[1][1]:.0f}s")

    print("\n  ── 1. CÁCH HIỆN TẠI: 2 pha (tách file tạm rồi nối) ──")
    from app.core import ffmpeg_utils as fu
    t0 = time.time()
    lst2, temps = fu._extract_segments_to_temp(src, segs, "h264_nvenc")
    t_tach = time.time() - t0
    tong_kb = sum((Path(p).stat().st_size // 1024) for p in temps
                  if Path(p).exists())
    print(f"    tách xong {len(temps)} file tạm trong {t_tach:.1f}s · "
          f"{tong_kb/1024:.0f} MB rác đĩa")

    ra2 = str(out / "hai_pha.mp4")
    cmd2 = [FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
            "-i", lst2, "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", ra2]
    r2 = _chay_prio(cmd2, DUOI_TB)
    cpu2 = r2["cpu_giay"]
    # CPU pha tách phải cộng vào
    print(f"    nối: {r2['giay']:.1f}s · {cpu2:.1f} CPU-giây")

    print("\n  ── 2. CÁCH MỚI: 1 pha (inpoint/outpoint) ──")
    lst1 = viet_list(out / "mot.txt", src, segs)
    ra1 = str(out / "mot_pha.mp4")
    cmd1 = [FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
            "-segment_time_metadata", "1", "-i", lst1,
            "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", ra1]
    r1 = _chay_prio(cmd1, DUOI_TB)
    print(f"    1 lệnh: {r1['giay']:.1f}s · {r1['cpu_giay']:.1f} CPU-giây · "
          f"0 MB rác đĩa")

    print("\n  ── 3. NGHIỆM THU ──")
    kiem(r1["ma"] == 0, "lệnh 1 pha chạy được", f"mã {r1['ma']}")
    if r1["ma"] != 0:
        return 1
    d1, d2 = do_dai(ra1), do_dai(ra2)
    mong = sum(b - a for a, b in segs)
    kiem(abs(d1 - mong) < 0.5, "độ dài đúng tổng các đoạn",
         f"{d1:.2f}s / mong {mong:.1f}s")
    kiem(abs(d1 - d2) < 0.5, "độ dài KHỚP bản 2 pha",
         f"1pha {d1:.2f}s · 2pha {d2:.2f}s")

    # THỨ TỰ + MỐC: so khung ở nhiều điểm trong clip ra
    print("    so khung hình 2 bản (0 = giống hệt):")
    xau_khung = 0
    for t in (1.0, 5.0, 10.0, 15.0, 19.0, 21.0, 25.0, 30.0, 35.0):
        if t > min(d1, d2) - 0.5:
            continue
        l = lech(khung_rgb(ra1, t), khung_rgb(ra2, t))
        moc = "đoạn 1" if t < 20 else "đoạn 2"
        print(f"      giây {t:>4.0f} ({moc}): lệch {l:6.2f}")
        if l >= 8.0:
            xau_khung += 1
    kiem(xau_khung == 0, "MỌI khung khớp bản 2 pha (thứ tự hook-first đúng)",
         f"{xau_khung} khung lệch")

    # so với NGUỒN để chắc mốc cắt đúng (không lệch keyframe)
    print("    so với VIDEO GỐC (mốc cắt có đúng khung không):")
    for i, (a, b) in enumerate(segs):
        t_ra = 1.0 if i == 0 else (segs[0][1] - segs[0][0]) + 1.0
        l1 = lech(khung_rgb(ra1, t_ra), khung_rgb(src, a + 1.0))
        l2 = lech(khung_rgb(ra2, t_ra), khung_rgb(src, a + 1.0))
        print(f"      đoạn {i+1}: 1pha lệch {l1:6.2f} · 2pha lệch {l2:6.2f}")
        kiem(l1 <= max(8.0, l2 + 3.0),
             f"đoạn {i+1} cắt đúng chỗ (không tệ hơn bản 2 pha)",
             f"{l1:.2f} vs {l2:.2f}")

    tong2 = cpu2 + 0.0
    print(f"\n  ── 4. GIÁ PHẢI TRẢ ──")
    print(f"    2 pha : {r2['giay'] + t_tach:>6.1f}s tường · "
          f"{cpu2:>5.1f} CPU-giây (chưa tính CPU pha tách) · "
          f"{tong_kb/1024:.0f} MB rác")
    print(f"    1 pha : {r1['giay']:>6.1f}s tường · "
          f"{r1['cpu_giay']:>5.1f} CPU-giây · 0 MB rác")
    fu._cleanup_paths(temps + [lst2])
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    print(f"\n  ✓ {OK} đạt · ✗ {XAU} hỏng")
    return 1 if XAU else 0


if __name__ == "__main__":
    sys.exit(main())
