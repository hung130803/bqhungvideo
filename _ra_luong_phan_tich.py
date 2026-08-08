# -*- coding: utf-8 -*-
r"""VÌ SAO LƯỢNG ffmpeg VỌT LÊN 203 (8,46x nhân) TRONG LƯỢT e2e?

    .venv\Scripts\python _ra_luong_phan_tich.py [--video <path>]

Mốc của anh Hùng "tổng luồng ffmpeg <= 2x số nhân" đã ĐO ĐẠT ở đường **XUẤT**
(44 luồng / 1,83x). Nhưng lượt e2e đo CẢ DÂY CHUYỀN — gồm cả pha **PHÂN TÍCH**
(chép lời, NGHE `astats`, XEM `scdet`, đo nhịp) — và ra **203**.

File này chỉ ra ĐÍCH DANH lệnh nào: lấy mẫu 20 lần/giây MỌI ffmpeg con, ghi
`num_threads` **kèm CHỮ KÝ dòng lệnh** (lấy các filter chính), rồi xếp hạng.

BẪY: **KHÔNG lọc tiến trình theo `cmdline`** (mã nguồn có chữ 'ffmpeg' -> đếm
cả chính lệnh kiểm). Lọc theo `p.name()`; cmdline CHỈ dùng để DÁN NHÃN.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_lpt_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))

import psutil  # noqa: E402

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import tim_video_nhat  # noqa: E402


def nhan(cmd: list) -> str:
    """Rút CHỮ KÝ ngắn của 1 lệnh ffmpeg để xếp nhóm."""
    s = " ".join(cmd)
    for k, v in (("astats", "NGHE astats"), ("scdet", "XEM scdet"),
                 ("showinfo", "showinfo"), ("silencedetect", "silencedetect"),
                 ("ebur128", "ebur128"),
                 ("xfade", "XUẤT xfade"), ("subtitles", "XUẤT đốt .ass"),
                 ("frei0r", "hiệu ứng frei0r"), ("boxblur", "XUẤT nền mờ"),
                 ("gblur", "XUẤT nền mờ"),
                 ("-vn", "TÁCH TIẾNG (chép lời)"),
                 ("select=", "trích khung"), ("-c copy", "copy")):
        if k in s:
            return v
    if "-f null" in s:
        return "đo (-f null)"
    return "khác"


class Soi:
    """Lấy mẫu num_threads của MỌI ffmpeg con + nhãn theo dòng lệnh."""

    def __init__(self) -> None:
        self.goc = os.getpid()
        self._stop = threading.Event()
        self.theo_nhan: dict[str, list[int]] = {}
        self.tong: list[int] = []
        self.dinh = 0
        self.dinh_nhan = ""
        self.th = threading.Thread(target=self._vong, daemon=True)

    def _vong(self) -> None:
        me = psutil.Process(self.goc)
        while not self._stop.is_set():
            tong = 0
            hien: list[tuple[str, int]] = []
            try:
                for c in me.children(recursive=True):
                    try:
                        if "ffmpeg" not in (c.name() or "").lower():
                            continue      # LỌC THEO TÊN, không theo cmdline
                        n = c.num_threads()
                        tong += n
                        hien.append((nhan(c.cmdline()), n))
                    except psutil.Error:
                        continue
            except psutil.Error:
                pass
            if hien:
                self.tong.append(tong)
                for k, n in hien:
                    self.theo_nhan.setdefault(k, []).append(n)
                if tong > self.dinh:
                    self.dinh = tong
                    self.dinh_nhan = " + ".join(f"{k}:{n}" for k, n in hien)
            time.sleep(0.05)

    def __enter__(self):
        self.th.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self.th.join(timeout=3)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="")
    a = ap.parse_args()
    src = Path(a.video) if a.video else (tim_video_nhat(1) or [None])[0]
    if not src or not Path(src).exists():
        print("DỪNG: không có video Nhật.")
        return 2
    cores = os.cpu_count() or 1
    print(f"nguồn: {Path(src).name}")
    print(f"nhân: {cores} · ngân sách 2× = {2*cores} luồng\n")

    from app.ai import chon_doan as CD
    from app.core import ffmpeg_utils as fu
    from app.core import hieu_ung as HU
    from config import settings

    print(f"decode_threads()={fu.decode_threads()} · "
          f"so_ffmpeg_song_song()={fu.so_ffmpeg_song_song()}\n")

    buoc = []
    with Soi() as s:
        t = time.time()
        CD.nang_luong(str(src), settings.FFMPEG_PATH)
        buoc.append(("NGHE nang_luong (astats)", time.time() - t, s.dinh))
        d0 = s.dinh
        t = time.time()
        CD.chuyen_dong(str(src), settings.FFMPEG_PATH)
        buoc.append(("XEM chuyen_dong (scdet)", time.time() - t, s.dinh))
        d1 = s.dinh
        t = time.time()
        try:
            HU.do_nhip(str(src), settings.FFMPEG_PATH)
            buoc.append(("do_nhip (hiệu ứng)", time.time() - t, s.dinh))
        except Exception as e:      # noqa: BLE001
            buoc.append((f"do_nhip LỖI {type(e).__name__}", time.time() - t, s.dinh))

    print(f"{'bước':<34} {'giây':>7} {'đỉnh luồng cộng dồn':>20}")
    for ten, gi, dn in buoc:
        print(f"{ten:<34} {gi:7.1f} {dn:20d}")

    print(f"\n── luồng theo TỪNG LỆNH (mẫu 20 lần/giây) ──")
    print(f"{'lệnh':<26} {'mẫu':>6} {'TB':>7} {'ĐỈNH':>6}  so 2× nhân")
    for k, v in sorted(s.theo_nhan.items(), key=lambda x: -max(x[1])):
        print(f"{k:<26} {len(v):6d} {statistics.mean(v):7.1f} {max(v):6d}  "
              f"{max(v)/(2*cores):.2f}×  {'VƯỢT' if max(v) > 2*cores else 'trong ngân sách'}")
    print(f"\nĐỈNH TỔNG: {s.dinh} luồng ({s.dinh/cores:.2f}× nhân) — "
          f"lúc đó: {s.dinh_nhan}")
    print(f"TB TỔNG  : {statistics.mean(s.tong):.1f} luồng "
          f"({statistics.mean(s.tong)/cores:.2f}× nhân)" if s.tong else "")

    ket = {"nhan": cores, "dinh": s.dinh, "dinh_x": round(s.dinh/cores, 2),
           "dinh_luc": s.dinh_nhan,
           "theo_lenh": {k: {"tb": round(statistics.mean(v), 1),
                             "dinh": max(v)} for k, v in s.theo_nhan.items()},
           "buoc": [{"ten": t, "giay": round(g, 1)} for t, g, _ in buoc]}
    (REPO / "_ket__ra_luong_phan_tich.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n[đã ghi] _ket__ra_luong_phan_tich.json")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
