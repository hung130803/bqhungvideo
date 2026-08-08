# -*- coding: utf-8 -*-
"""TỔNG RÀ SOÁT — câu 3 của anh Hùng: **NHIỀU KÊNH, NHIỀU LUỒNG được chưa?**

    .venv\\Scripts\\python _ra_50kenh.py [--kenh 50] [--lan 10]

DỰNG ĐÚNG CẢNH SẢN XUẤT: `--kenh` kênh, mỗi kênh 1 video + 1 clip, **xếp HẾT
vào hàng chờ một lượt** rồi bật WorkerPool THẬT với `--lan` làn cắt. Song song
đó nhồi 60 job PHÂN TÍCH (priority 10) vào làn GPU để tái hiện đúng bẫy
"làn cắt chết đói vì LIMIT 50" (cổng 5).

ĐO (mốc anh Hùng):
  · tổng luồng ffmpeg **≤ 2× số nhân**            (24 nhân -> ≤ 48)
  · RAM đỉnh của cả cây tiến trình
  · trễ vòng lặp UI trung vị < 30ms, đỉnh < 150ms
  · **có làn nào bị bỏ đói không** — job xuất có được chạy khi 60 job phân
    tích đang ngập hàng chờ không
  · **job nào đợi > 10 phút** (nghẽn)
  · 0 clip lỗi · 0 clip 0-byte · 0 ffmpeg mồ côi

Xuất THẬT bằng `export_canvas_clip` trên video Nhật THẬT (2 đoạn hook-first,
nền mờ, đốt .ass, 1080x1920) — đúng đường mà 200-300 kênh đang đi.
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

_SB = Path(tempfile.mkdtemp(prefix="ra_50k_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import psutil  # noqa: E402

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import DoLuong, _ass_mau, _may_ranh, tim_video_nhat  # noqa: E402,E501


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kenh", type=int, default=50)
    ap.add_argument("--lan", type=int, default=10, help="số LÀN cắt (max_cpu)")
    ap.add_argument("--phan-tich", type=int, default=60,
                    help="job phân tích nhồi vào làn GPU (bẫy LIMIT 50)")
    ap.add_argument("--phut", type=float, default=25.0)
    ap.add_argument("--du-may-ban", action="store_true")
    a = ap.parse_args()

    ok, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok and not a.du_may_ban:
        print("DỪNG: máy bận.")
        return 2
    vids = tim_video_nhat(1)
    if not vids:
        print("DỪNG: không có video Nhật.")
        return 2
    src = vids[0]

    from config import settings
    settings.ECO_MODE = False          # đúng cấu hình máy anh Hùng (ô không tích)

    from PyQt6.QtCore import QCoreApplication, QTimer

    from app.core import ffmpeg_utils as fu
    from app.database.db import db
    from app.queue.worker import WorkerPool

    cores = os.cpu_count() or 1
    print(f"[encoder] {fu.detect_encoder()} · trần ffmpeg song song "
          f"{fu.so_ffmpeg_song_song()} · giải mã {fu.decode_threads()} luồng "
          f"· nhân {cores}")
    print(f"[cấu hình] {a.kenh} kênh · {a.lan} làn cắt · "
          f"{a.phan_tich} job phân tích nhồi vào làn GPU\n")

    ass = _ass_mau(_SB / "sub.ass", 20.0)
    out = _SB / "out"
    out.mkdir(exist_ok=True)

    # ---- dựng `--kenh` kênh, mỗi kênh 1 video + 1 clip ----
    pids, cids = [], []
    for i in range(a.kenh):
        pid = db.execute(
            "INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,'Nhật')",
            (f"Kênh {i+1:03d}", str(_SB / "assets"))).lastrowid
        vid = db.execute(
            "INSERT INTO videos(project_id, title, src_path, duration) "
            "VALUES(?,?,?,?)", (pid, f"video {i+1}", str(src), 300.0)).lastrowid
        cid = db.execute(
            "INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
            "status, signals) VALUES(?,?,?,?,?,'suggested','{}')",
            (vid, 60.0, 70.0, 0.9, f"Part {i+1}")).lastrowid
        pids.append(pid)
        cids.append(cid)
    print(f"dựng xong {len(pids)} kênh / {len(cids)} clip")

    # ---- pool THẬT, nhưng handler xuất gọi thẳng export_canvas_clip ----
    xong = {"n": 0, "loi": [], "byte0": 0}
    lock = threading.Lock()

    from app.queue.worker import register_handler

    def _xuat(payload, ctx):
        i = int(payload["clip_id"])
        f = out / f"k{i}.mp4"
        fu.export_canvas_clip(
            str(src), str(f),
            [(60.0, 70.0), (20.0, 30.0)],        # NGƯỢC = hook-first
            (0.5, 0.42, 0.98), bg="blur", out_w=1080, out_h=1920,
            ass_path=str(ass), fx_fade=True, fx_whoosh=True,
            chuyen_canh="nhe", hieu_ung="nhe")   # MẶC ĐỊNH MỚI
        with lock:
            if not f.exists() or f.stat().st_size == 0:
                xong["byte0"] += 1
            xong["n"] += 1
        f.unlink(missing_ok=True)
        return {"ok": True}

    def _phan_tich(payload, ctx):
        # job làn GPU: chỉ giữ chỗ để tái hiện hàng chờ ngập, KHÔNG đốt CPU
        # (mục tiêu của ca này là ĐIỀU PHỐI, không phải đo AI).
        time.sleep(2.0)
        return {"ok": True}

    register_handler("ra_xuat", _xuat)
    register_handler("ra_phantich", _phan_tich)

    pool = WorkerPool({}, max_cpu=a.lan, max_gpu=1)

    # NHỒI làn GPU TRƯỚC -> đúng thứ tự gây bẫy (job phân tích created_at sớm hơn)
    for _ in range(a.phan_tich):
        db.insert("INSERT INTO jobs(type,payload,needs_gpu,priority,status) "
                  "VALUES('ra_phantich','{}',1,10,'pending')")
    for cid in cids:
        db.insert("INSERT INTO jobs(type,payload,needs_gpu,priority,status) "
                  "VALUES('ra_xuat',?,0,3,'pending')",
                  (json.dumps({"clip_id": cid}),))
    n_job = a.phan_tich + len(cids)
    print(f"xếp {n_job} job vào hàng chờ "
          f"({a.phan_tich} phân tích priority 10 + {len(cids)} xuất priority 3)\n")

    # ---- đo ----
    tre: list[float] = []
    moc = {"t": 0.0}
    NHIP = 50
    may: list[tuple[float, float]] = []
    dung = {"het": False}
    t0 = time.time()
    han = t0 + a.phut * 60
    me = psutil.Process()
    # LÀN ĐÓI: theo dõi lúc nào job XUẤT đầu tiên được chạy
    dau = {"xuat": None, "n_xuat_khi_pt_con": 0}

    def _lay_may() -> None:
        psutil.cpu_percent(None)
        while not dung["het"]:
            try:
                rss = me.memory_info().rss
                for c in me.children(recursive=True):
                    try:
                        rss += c.memory_info().rss
                    except psutil.Error:
                        pass
                may.append((psutil.cpu_percent(None), rss / 1024 ** 3))
            except psutil.Error:
                pass
            time.sleep(1.0)

    qapp = QCoreApplication(sys.argv)

    def _tick() -> None:
        now = time.perf_counter()
        if moc["t"]:
            tre.append(max(0.0, (now - moc["t"]) * 1000.0 - NHIP))
        moc["t"] = now
        r = db.query_one(
            "SELECT SUM(type='ra_xuat' AND status IN ('done','failed')) x, "
            "SUM(type='ra_phantich' AND status='pending') ptc, "
            "SUM(type='ra_xuat' AND status='running') xr FROM jobs")
        if r and r["xr"] and dau["xuat"] is None:
            dau["xuat"] = time.time() - t0
            dau["n_xuat_khi_pt_con"] = int(r["ptc"] or 0)
        if (r and int(r["x"] or 0) >= len(cids)) or time.time() > han:
            dung["het"] = True
            qapp.quit()

    tm = QTimer()
    tm.setInterval(NHIP)
    tm.timeout.connect(_tick)

    th = threading.Thread(target=_lay_may, daemon=True)
    with DoLuong() as d:
        th.start()
        pool.start()
        tm.start()
        qapp.exec()
    dung["het"] = True
    wall = time.time() - t0
    pool.stop()
    time.sleep(1.0)

    # ---- kết quả ----
    tv = round(statistics.median(tre), 1) if tre else -1
    p95 = round(sorted(tre)[int(len(tre) * 0.95)], 1) if tre else -1
    dinh = round(max(tre), 1) if tre else -1
    ram = round(max((x[1] for x in may), default=0), 2)
    cpu_tb = round(statistics.mean([x[0] for x in may]), 1) if may else -1
    cpu_d = round(max((x[0] for x in may), default=0), 1)

    doi = db.query(
        "SELECT type, MAX((julianday(COALESCE(started_at,'now'))-"
        "julianday(created_at))*86400) gio FROM jobs GROUP BY type")
    that_bai = db.query(
        "SELECT type, COUNT(*) n FROM jobs WHERE status='failed' GROUP BY type")
    mo_coi = sum(1 for p in psutil.process_iter(["name"])
                 if (p.info["name"] or "").lower().startswith("ffmpeg"))

    print("=" * 76)
    print(f"XONG {xong['n']}/{len(cids)} clip trong {wall:.0f}s "
          f"({wall/60:.1f} phút)")
    print("=" * 76)
    print(f"  luồng ffmpeg      đỉnh {d.dinh_luong} "
          f"({d.dinh_luong/cores:.2f}× nhân) · TB {d.tb_luong} "
          f"· đỉnh {d.dinh_tt} tiến trình")
    print(f"  trễ vòng lặp UI   trung vị {tv}ms · p95 {p95}ms · đỉnh {dinh}ms "
          f"({len(tre)} nhịp)")
    print(f"  RAM cây đỉnh      {ram} GB")
    print(f"  CPU cả máy        TB {cpu_tb}% · đỉnh {cpu_d}%")
    print(f"  CPU-giây ffmpeg   {d.cpu_giay}")
    print(f"  clip 0-byte       {xong['byte0']}")
    print(f"  ffmpeg mồ côi     {mo_coi}")
    for r in doi:
        print(f"  đợi lâu nhất '{r['type']}': {r['gio']:.0f}s "
              f"{'<< NGHẼN (>10 phút)' if (r['gio'] or 0) > 600 else ''}")
    print(f"  job THẤT BẠI: {[(r['type'], r['n']) for r in that_bai] or 0}")
    print(f"\n  LÀN ĐÓI? job XUẤT đầu tiên chạy sau {dau['xuat']}s, "
          f"lúc đó còn {dau['n_xuat_khi_pt_con']} job phân tích ĐANG CHỜ")
    print(f"     -> {'KHÔNG đói (làn cắt chạy dù làn phân tích ngập)' if (dau['xuat'] is not None and dau['xuat'] < 30) else 'NGHI ĐÓI — xem lại'}")

    ket = {
        "kenh": a.kenh, "lan": a.lan, "job_phan_tich": a.phan_tich,
        "wall_s": round(wall, 1), "clip_xong": xong["n"],
        "clip_0byte": xong["byte0"],
        "luong_dinh": d.dinh_luong, "luong_tb": d.tb_luong,
        "nhan_x": round(d.dinh_luong / cores, 2), "tien_trinh_dinh": d.dinh_tt,
        "ui_tv": tv, "ui_p95": p95, "ui_dinh": dinh,
        "ram_dinh_gb": ram, "cpu_tb": cpu_tb, "cpu_dinh": cpu_d,
        "cpu_giay_ffmpeg": d.cpu_giay,
        "doi_lau_nhat": {r["type"]: round(r["gio"] or 0) for r in doi},
        "that_bai": {r["type"]: r["n"] for r in that_bai},
        "ffmpeg_mo_coi": mo_coi,
        "lan_xuat_chay_sau_s": dau["xuat"],
        "phan_tich_con_cho_luc_do": dau["n_xuat_khi_pt_con"],
    }
    (REPO / "_ket__ra_50kenh.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n[đã ghi] _ket__ra_50kenh.json")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
