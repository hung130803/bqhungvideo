# -*- coding: utf-8 -*-
r"""ĐO GIÁ PHẢI TRẢ của hiệu ứng điểm nhấn — wall + CPU-giây, lặp 3 lấy trung vị.

Chạy: .venv\Scripts\python _do_gia_hieu_ung.py

Anh Hùng chạy 200-300 kênh nên "chậm hơn bao nhiêu" là con số PHẢI biết trước
khi bật mặc định. Đo bằng CPU-GIÂY (`psutil`), kiểm máy rảnh trước.
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"gia_hu_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401
import psutil  # noqa: E402

import _nguon_nhat  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


class DoCPU:
    """CPU-giây của MỌI tiến trình ffmpeg sinh ra trong khoảng đo.

    Lọc theo `p.name()`, KHÔNG theo cmdline — lọc cmdline sẽ đếm chính lệnh
    kiểm (mã nguồn có chữ 'ffmpeg') và báo sai, đã sai 4 lần.
    """

    def __init__(self) -> None:
        self.cpu = 0.0
        self.dinh_luong = 0
        self._seen: dict = {}
        self._stop = False

    def _quet(self) -> None:
        import threading
        del threading
        while not self._stop:
            lg = 0
            for p in psutil.process_iter(["name", "pid"]):
                try:
                    if (p.info["name"] or "").lower() not in ("ffmpeg.exe",
                                                              "ffmpeg"):
                        continue
                    t = p.cpu_times()
                    self._seen[p.info["pid"]] = t.user + t.system
                    lg += p.num_threads()
                except psutil.Error:
                    pass
            self.dinh_luong = max(self.dinh_luong, lg)
            time.sleep(0.15)

    def __enter__(self):
        import threading
        self._t = threading.Thread(target=self._quet, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop = True
        self._t.join(timeout=2)
        self.cpu = sum(self._seen.values())
        return False


def may_ranh() -> bool:
    psutil.cpu_percent()
    time.sleep(4)
    c = psutil.cpu_percent()
    n = sum(1 for p in psutil.process_iter(["name"])
            if (p.info["name"] or "").lower() in ("ffmpeg.exe", "ffmpeg"))
    print(f"[máy] CPU {c:.1f}% · ffmpeg đang chạy {n} · nhân "
          f"{psutil.cpu_count()}")
    return c < 20 and n == 0


def main() -> None:
    if not may_ranh():
        print("MÁY ĐANG BẬN -> DỪNG (quy tắc sắt: đo trên máy rảnh)")
        return
    src = _nguon_nhat.liet_ke()[1]
    segs = [(100.0, 110.0), (60.0, 68.0), (200.0, 206.0)]
    enc = fu.detect_encoder()
    print(f"[nguồn] {os.path.basename(src)}")
    print(f"[đoạn]  3 đoạn = {sum(e - s for s, e in segs):.0f}s · 1080x1920 · "
          f"{enc} · trần ffmpeg {fu.so_ffmpeg_song_song()}")
    print()
    print(f"{'ca':<34}{'wall (tv)':>11}{'CPU-giây':>11}{'đỉnh luồng':>12}"
          f"{'so với TẮT':>12}")
    print("-" * 80)
    goc_w = goc_c = 0.0
    for ten, hu, xf in (("TẮT hết (đường cũ)", "tat", "tat"),
                        ("chỉ chuyển cảnh 'nhe'", "tat", "nhe"),
                        ("chỉ điểm nhấn 'nhe'", "nhe", "tat"),
                        ("chỉ điểm nhấn 'vua'", "vua", "tat"),
                        ("chỉ điểm nhấn 'manh'", "manh", "tat"),
                        ("MẶC ĐỊNH MỚI (nhe + nhe)", "nhe", "nhe"),
                        ("manh + manh (GPU)", "manh", "manh")):
        ws, cs, lg = [], [], 0
        for lap in range(3):
            out = str(_SB / f"{hu}_{xf}_{lap}.mp4")
            with DoCPU() as d:
                t0 = time.time()
                fu.export_canvas_clip(
                    src, out, segs, (0.5, 0.5, 1.0), out_w=1080, out_h=1920,
                    bg="blur", encoder=enc, fx_fade=True, fx_whoosh=True,
                    chuyen_canh=xf, hieu_ung=hu)
                ws.append(time.time() - t0)
            cs.append(d.cpu)
            lg = max(lg, d.dinh_luong)
            os.unlink(out)
        w, c = statistics.median(ws), statistics.median(cs)
        if goc_w == 0.0:
            goc_w, goc_c = w, c
            so = "—"
        else:
            so = f"{w / goc_w:.2f}x wall"
        print(f"{ten:<34}{w:>10.2f}s{c:>11.2f}{lg:>12}{so:>12}")


if __name__ == "__main__":
    try:
        main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
        sys.stdout.flush()
    os._exit(0)
