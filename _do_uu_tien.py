# -*- coding: utf-8 -*-
"""ĐO ĐỘ ƯU TIÊN tiến trình ffmpeg — nghi can số 1 của "xuất chậm + máy đơ".

    python _do_uu_tien.py

PHÁT HIỆN 07/08/2026: `ffmpeg_utils._run` spawn ffmpeg với
`_IDLE_PRIORITY = 0x40` = IDLE_PRIORITY_CLASS — mức THẤP NHẤT Windows có.
Tiến trình idle chỉ được chạy khi KHÔNG CÒN AI muốn CPU. Máy anh Hùng lúc nào
cũng có prodown (yt-dlp) tải video + Defender quét => ffmpeg bị BỎ ĐÓI.

Số đo đối chứng: CÙNG 1 lệnh dựng khung, chạy qua app mất ~51s; chạy tay
(ưu tiên thường) hết 7,8s.

Bộ đo này chạy CÙNG 1 lệnh ở 3 mức ưu tiên × 2 mức tải máy, đo giây tường +
CPU-giây (GetProcessTimes, chính xác cả khi tiến trình đã thoát).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
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

from _do_luong_xuat import chon_video, lam_ass, probe          # noqa: E402
from _do_pha_xuat import bat_lenh, chay_do                     # noqa: E402

# creationflags Windows
UU_TIEN = {
    "idle (app đang dùng)": 0x00000040,      # IDLE_PRIORITY_CLASS
    "duoi trung binh": 0x00004000,           # BELOW_NORMAL_PRIORITY_CLASS
    "trung binh": 0x00000020,                # NORMAL_PRIORITY_CLASS
}


class TaiGia:
    """Giả lập máy BẬN: n luồng quay vòng ở ưu tiên THƯỜNG (như yt-dlp)."""

    def __init__(self, n: int):
        self.n = n
        self._chay = False
        self._ths: list[threading.Thread] = []

    def bat(self) -> None:
        if self.n <= 0:
            return
        self._chay = True
        for _ in range(self.n):
            t = threading.Thread(target=self._quay, daemon=True)
            t.start()
            self._ths.append(t)

    def _quay(self) -> None:
        x = 0.0
        while self._chay:
            for _ in range(200000):
                x = x * 1.000001 + 1.0
        self._x = x

    def tat(self) -> None:
        self._chay = False
        for t in self._ths:
            t.join(timeout=2)
        self._ths = []


def main() -> int:
    print("═" * 72)
    print("ĐO ĐỘ ƯU TIÊN ffmpeg — vì sao cùng 1 lệnh mà app chậm gấp 6,5 lần")
    print("═" * 72)
    vid = chon_video(1)
    src = vid[0]
    inf = probe(src)
    print(f"  nguồn: {Path(src).name[:56]} · {inf['w']}x{inf['h']} "
          f"{inf['fps']:.0f}fps")
    out = Path(tempfile.mkdtemp(prefix="_do_uu_"))
    g = max(30.0, inf["dur"] * 0.3)
    segs = [(g, g + 30.0), (g + 70.0, g + 100.0)]
    ass = lam_ass(out, segs, 1080, 1920)
    lenh = bat_lenh(src, segs, ass, out)
    D = next(c for c in lenh if "-filter_complex" in " ".join(c))
    D = list(D)
    D[-1] = str(out / "thu.mp4")
    print(f"  lệnh dựng khung 60s ra 1080x1920, nền mờ + phụ đề .ass\n")

    ket = []
    for n_tai in (0, 8):
        tai = TaiGia(n_tai)
        tai.bat()
        if n_tai:
            time.sleep(1.0)
        nhan_tai = "máy RẢNH" if n_tai == 0 else f"máy BẬN ({n_tai} nhân)"
        print(f"  ── {nhan_tai} ──")
        for ten, co in UU_TIEN.items():
            r = _chay_prio(D, co)
            r.update({"uu_tien": ten, "tai": n_tai})
            ket.append(r)
            print(f"    {ten:<22} {r['giay']:>6.1f}s tường · "
                  f"{r['cpu_giay']:>6.1f} CPU-giây · {r['luong_dinh']} luồng")
        tai.tat()
        print()

    print("═" * 72)
    print(f"{'ưu tiên':<24}{'máy rảnh':>14}{'máy bận':>14}{'chậm thêm':>14}")
    print("-" * 72)
    for ten in UU_TIEN:
        a = next(k for k in ket if k["uu_tien"] == ten and k["tai"] == 0)
        b = next(k for k in ket if k["uu_tien"] == ten and k["tai"] == 8)
        d = b["giay"] / max(0.1, a["giay"])
        print(f"{ten:<24}{a['giay']:>13.1f}s{b['giay']:>13.1f}s{d:>13.2f}x")
    (REPO / "_do_luong_cache" / "uu_tien.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), "utf-8")
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    return 0


def _chay_prio(cmd: list[str], co: int) -> dict:
    """Như chay_do nhưng đặt ĐÚNG cờ ưu tiên (creationflags)."""
    import ctypes
    import psutil
    from _do_pha_xuat import (_cpu_giay, _mo_handle, _K32, _NO_WIN,
                              doc_encoder)
    import tempfile
    from pathlib import Path as _P
    t0 = time.time()
    # stderr vào FILE TẠM, KHÔNG DEVNULL: xem ghi chú `chay_do` trong
    # _do_pha_xuat.py — DEVNULL là lý do CẤU TRÚC làm cột "enc" luôn ra `?`.
    flog = _P(tempfile.gettempdir()) / f"_do_uu_{os.getpid()}_{co}.txt"
    with open(flog, "wb") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,
                             creationflags=_NO_WIN | co)
        h = _mo_handle(p.pid)
        ps = psutil.Process(p.pid)
        dinh = 0
        while p.poll() is None:
            try:
                dinh = max(dinh, ps.num_threads())
            except psutil.Error:
                break
            time.sleep(0.05)
        p.wait()
    cpu = _cpu_giay(h) if h else -1.0
    if h:
        _K32.CloseHandle(h)
    enc = doc_encoder(flog.read_text("utf-8", errors="replace"))
    flog.unlink(missing_ok=True)
    return {"ma": p.returncode, "giay": round(time.time() - t0, 1),
            "luong_dinh": dinh, "cpu_giay": round(cpu, 1), "enc": enc}


if __name__ == "__main__":
    sys.exit(main())
