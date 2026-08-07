# -*- coding: utf-8 -*-
"""MỐC 1 (anh Hùng): MÁY KHÔNG ĐƠ/GIẬT khi 10 làn đang xuất.

    .venv\\Scripts\\python _do_ui_tai_nang.py [--luot 10] [--giay 60]

ĐO CÁI GÌ: **độ trễ vòng lặp UI** = QTimer hẹn 50ms nhưng nổ MUỘN bao nhiêu.
Đây đúng cái anh Hùng cảm nhận là "đơ giật lag": vòng lặp sự kiện Qt bị tranh
CPU nên nút bấm/thanh tiến trình đứng. Mốc: **trung vị < 30ms VÀ đỉnh < 150ms**.

VÌ SAO ĐO ĐỘ TRỄ CHỨ KHÔNG ĐO CPU%: máy 100% CPU mà UI vẫn nổ đúng nhịp thì
user KHÔNG thấy đơ (ffmpeg chạy ưu tiên IDLE). Ngược lại 60% CPU mà vòng lặp bị
chặn 400ms là user thấy giật. Chỉ số trễ mới nói đúng cảm nhận.

Chạy song song: luồng nền xuất `--luot` clip THẬT qua `export_canvas_clip`;
luồng chính chạy vòng lặp Qt + đếm trễ. Kèm tổng luồng ffmpeg để đối chiếu.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"do_ui_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import psutil                                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import DoLuong, _ass_mau, _may_ranh, tim_video_nhat  # noqa: E402,E501


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luot", type=int, default=10)
    ap.add_argument("--giay", type=float, default=60.0)
    ap.add_argument("--nhip", type=int, default=50, help="nhịp QTimer (ms)")
    a = ap.parse_args()

    ok, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok:
        print("DỪNG: máy đang bận -> số trễ sẽ sai.")
        return 2
    vids = tim_video_nhat(1)
    if not vids:
        print("DỪNG: không có video Nhật.")
        return 2
    src = vids[0]

    from PyQt6.QtCore import QCoreApplication, QTimer
    from app.core import ffmpeg_utils as fu

    print(f"[encoder] {fu.detect_encoder()} · trần ffmpeg song song "
          f"{fu.so_ffmpeg_song_song()} · giải mã {fu.decode_threads()} luồng "
          f"· nhân {os.cpu_count()}")
    ass = _ass_mau(_SB / "sub.ass", 20.0)
    out = _SB / "out"
    out.mkdir(exist_ok=True)

    xong = {"n": 0, "loi": []}
    dung = threading.Event()

    def _work(i: int) -> None:
        # xuất LẶP LẠI tới khi hết thời gian đo -> tải giữ đều suốt 60 giây
        k = 0
        while not dung.is_set():
            f = out / f"u{i}_{k}.mp4"
            try:
                fu.export_canvas_clip(
                    str(src), str(f),
                    [(60.0, 70.0), (20.0, 30.0)],     # NGƯỢC = hook-first
                    (0.5, 0.42, 0.98), bg="blur", out_w=1080, out_h=1920,
                    ass_path=str(ass), fx_fade=True, fx_whoosh=True)
                xong["n"] += 1
            except Exception as e:                        # noqa: BLE001
                xong["loi"].append(f"{i}.{k}: {type(e).__name__}: {e}"[:120])
            f.unlink(missing_ok=True)
            k += 1

    app = QCoreApplication(sys.argv)
    tre: list[float] = []
    moc = {"t": 0.0}
    t_bd = time.perf_counter()

    def _tick() -> None:
        now = time.perf_counter()
        if moc["t"]:
            tre.append((now - moc["t"]) * 1000.0 - a.nhip)
        moc["t"] = now
        if now - t_bd >= a.giay:
            dung.set()
            app.quit()

    tm = QTimer()
    tm.setInterval(a.nhip)
    tm.timeout.connect(_tick)

    with DoLuong() as d:
        ths = [threading.Thread(target=_work, args=(i,), daemon=True)
               for i in range(a.luot)]
        for t in ths:
            t.start()
        tm.start()
        app.exec()
        for t in ths:
            t.join(timeout=180)

    tre = [max(0.0, x) for x in tre]
    cores = os.cpu_count() or 1
    tv = round(statistics.median(tre), 1) if tre else -1
    p95 = round(sorted(tre)[int(len(tre) * 0.95)], 1) if tre else -1
    dinh = round(max(tre), 1) if tre else -1
    print(f"\n=== {a.luot} làn xuất liên tục {a.giay:.0f}s "
          f"(xong {xong['n']} clip) ===")
    print(f"  trễ vòng lặp UI  trung vị {tv}ms · p95 {p95}ms · đỉnh {dinh}ms "
          f"({len(tre)} nhịp)")
    print(f"  luồng ffmpeg     đỉnh {d.dinh_luong} ({d.dinh_luong / cores:.2f}x "
          f"nhân) · TB {d.tb_luong} · đỉnh {d.dinh_tt} tiến trình")
    print(f"  CPU-giây ffmpeg  {d.cpu_giay}")
    print(f"  ĐẠT MỐC 1 (trung vị < 30ms và đỉnh < 150ms): "
          f"{'CÓ' if (0 <= tv < 30 and 0 <= dinh < 150) else 'KHÔNG'}")
    print(f"  ĐẠT MỐC 2 (luồng <= 2x nhân = {2 * cores}): "
          f"{'CÓ' if d.dinh_luong <= 2 * cores else 'KHÔNG'}")
    if xong["loi"]:
        print(f"  LỖI XUẤT ({len(xong['loi'])}): {xong['loi'][:3]}")
    else:
        print("  LỖI XUẤT: 0")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
