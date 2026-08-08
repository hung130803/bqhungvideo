# -*- coding: utf-8 -*-
r"""ĐO 5 LỖI của kho hiệu ứng điểm nhấn — TRƯỚC khi sửa (và sau, để đối chiếu).

Chạy: .venv\Scripts\python.exe _do_5loi.py

Đo qua ĐƯỜNG XUẤT THẬT (`export_canvas_clip`), nguồn Nhật thật. Mỗi lỗi in ra
SỐ, không in "đạt/không đạt" — kết luận để người đọc.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"do5loi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401
import numpy as np  # noqa: E402

import _nguon_nhat  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402
from app.core import hieu_ung as HU  # noqa: E402
from config import settings  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NOWIN = 0x08000000


def dai(p: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True,
                       text=True, creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def khung(p: str, t: float, W: int, H: int):
    """1 khung ở mốc t -> mảng (3,H,W) YUV int16."""
    raw = str(_SB / f"k_{abs(hash((p, t))) % 10**8}.raw")
    subprocess.run([FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", p,
                    "-frames:v", "1", "-pix_fmt", "yuv444p", "-f", "rawvideo",
                    raw], capture_output=True, creationflags=_NOWIN)
    d = np.fromfile(raw, dtype=np.uint8)
    if d.size < W * H * 3:
        return None
    return d[:W * H * 3].reshape(3, H, W).astype(np.int16)


def nguon_fps(fps: int, giay: float, W: int = 480, H: int = 854) -> str:
    """Nguồn tự sinh, fps ép cứng, CÓ tiếng — để đo lỗi zoompan-fps."""
    p = str(_SB / f"src{fps}.mp4")
    if os.path.exists(p):
        return p
    subprocess.run(
        [FF, "-y", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=size={W}x{H}:rate={fps}:d={giay}",
         "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:d={giay}",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(fps), "-fps_mode:v", "cfr",
         "-c:a", "aac", "-shortest", p],
        capture_output=True, creationflags=_NOWIN)
    return p


def xuat(out: str, src: str, segs: list, **kw) -> bool:
    return fu.export_canvas_clip(
        src, out, segs, (0.5, 0.5, 1.0), out_w=540, out_h=960,
        encoder=kw.pop("encoder", fu.detect_encoder()), fx_fade=False,
        fx_whoosh=False, **kw)


def loi1_fps() -> None:
    print("\n=== LỖI 1: zoompan nhận fps SAI khi nền Đen/Trắng ===")
    src = nguon_fps(25, 6.0)
    hu = [{"bat": 1.0, "het": 1.4, "khoa": "zoom_nhoi", "dam": 0.18}]
    for bg in ("black", "blur"):
        for ten, h in (("TẮT", ""), ("zoom_nhoi", hu)):
            o = str(_SB / f"l1_{bg}_{ten}.mp4")
            xuat(o, src, [(0.0, 2.0)], bg=bg, hieu_ung=h)
            print(f"  nền {bg:<6} {ten:<10} độ dài {dai(o):6.3f}s "
                  f"(mong đợi 2.000)")


def loi2_vien_net() -> None:
    print("\n=== LỖI 2: vien_net đổi màu TOÀN CLIP ===")
    src = _nguon_nhat.mot("JP")
    segs = [(100.0, 103.0)]
    base = str(_SB / "l2_tat.mp4")
    xuat(base, src, segs, bg="blur", hieu_ung="")
    g_ng = khung(base, 0.30, 540, 960)
    for k in ("vien_net", "quang_sang", "zoom_nhoi"):
        o = str(_SB / f"l2_{k}.mp4")
        xuat(o, src, segs, bg="blur",
             hieu_ung=[{"bat": 1.2, "het": 1.55, "khoa": k, "dam": 0.18}])
        a = khung(o, 0.30, 540, 960)     # NGOÀI cửa sổ
        if a is None or g_ng is None:
            print(f"  {k:<12} KHÔNG trích được khung"); continue
        du = abs(float(a[1].mean()) - float(g_ng[1].mean()))
        dv = abs(float(a[2].mean()) - float(g_ng[2].mean()))
        dy = float((np.abs(a[0] - g_ng[0]) > 12).mean()) * 100
        print(f"  {k:<12} NGOÀI cửa sổ: |dU| {du:5.2f}  |dV| {dv:5.2f}  "
              f"%pixel Y đổi {dy:5.2f}%")


def loi3_vspeed() -> None:
    print("\n=== LỖI 3: nhân vspeed sai chiều (hiệu ứng không chạy) ===")
    src = _nguon_nhat.mot("JP")
    segs = [(100.0, 110.0)]     # nội bộ 10s; speed 1.25 -> ra 8s
    log: list = []
    o = str(_SB / "l3_speed.mp4")
    xuat(o, src, segs, bg="blur", speed=1.25, hieu_ung="manh",
         hieu_ung_log=log)
    print(f"  độ dài ra {dai(o):.3f}s (mong đợi 8.000)")
    for c in log:
        print(f"    chọn: {c['khoa']:<12} {c['bat']:.2f}-{c['het']:.2f}s "
              f"({c['loai']})")
    # có hiệu ứng nào thấy được trên khung ra không?
    base = str(_SB / "l3_tat.mp4")
    xuat(base, src, segs, bg="blur", speed=1.25, hieu_ung="")
    for c in log:
        t = (float(c["bat"]) + float(c["het"])) / 2.0
        a, b = khung(o, t, 540, 960), khung(base, t, 540, 960)
        if a is None or b is None:
            print(f"    mốc {t:.2f}s: KHÔNG trích được"); continue
        pct = float((np.abs(a[0] - b[0]) > 12).mean()) * 100
        print(f"    mốc {t:5.2f}s ({c['khoa']}): %pixel đổi {pct:6.2f}%")


def loi4_dem_nguoc() -> None:
    print("\n=== LỖI 4: dem_nguoc mốc cứng 0,30/0,60 ===")
    h = HU.KHO["dem_nguoc"]
    for vs in (1.0, 0.7, 1.5):
        dai_cs = 0.80 * vs
        s = h.chuoi(0.18, 0.0, dai_cs, 540, 960, 30, "x.ttf")
        so1 = [x for x in s.split("drawtext") if "text='1'" in x]
        print(f"  vspeed {vs:.1f} cửa sổ {dai_cs:.2f}s -> "
              f"số 1 enable: {so1[0].split(':enable=')[1][:34] if so1 else '?'}")


def loi5_font() -> None:
    print("\n=== LỖI 5: log khoe hiệu ứng mà chuoi_filter sẽ VỨT ===")
    dd = HU.dung_duoc(co_font=True)
    chon = HU.chon_hieu_ung(30.0, "manh", nl=[], cd=[], moc_noi=[5.0, 12.0],
                            co_the_dung=dd)
    ten = [c["khoa"] for c in chon]
    ch = HU.chuoi_filter(chon, 540, 960, 30, font="")     # KHÔNG có font
    n_ff = len([x for x in ch.split(",") if x.strip()]) if ch else 0
    print(f"  chọn (log) {len(chon)}: {ten}")
    print(f"  có 'dem_nguoc' trong log: {'dem_nguoc' in ten} · "
          f"chuỗi filter khi THIẾU font có drawtext: {'drawtext' in ch}")
    print(f"  số filter trong chuỗi: {n_ff}")


if __name__ == "__main__":
    print("[nguồn]", os.path.basename(_nguon_nhat.mot("JP")))
    print("[encoder]", fu.detect_encoder())
    for f in (loi1_fps, loi2_vien_net, loi3_vspeed, loi4_dem_nguoc, loi5_font):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"  !! {f.__name__} nổ: {e}")
            traceback.print_exc()
