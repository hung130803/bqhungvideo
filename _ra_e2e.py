# -*- coding: utf-8 -*-
"""TỔNG RÀ SOÁT — câu 1 (tích hợp), 2 (mượt), 4 (AI), 5 (nghẽn) của anh Hùng.

    .venv\\Scripts\\python _ra_e2e.py [--so-video 6] [--phut 45]

CHẠY CÁI GÌ: e2e THẬT qua app — quét nguồn -> nhận -> chép lời -> phân tích AI
-> cắt -> xuất Part -> xoá gốc — trên **video Nhật THẬT** trong
`C:\\Users\\Admin\\Downloads\\thùng rác`, đủ ca **có lời / KHÔNG lời / VFR /
CFR 30 & 60 fps**, chia thành **nhiều KÊNH** (đúng cảnh sản xuất 200-300 kênh).

ĐO GÌ TRONG LÚC CHẠY (mốc của anh Hùng):
  · trễ vòng lặp UI  — trung vị < 30ms, đỉnh < 150ms  (đo LIÊN TỤC, ≥120s)
  · tổng luồng ffmpeg — ≤ 2× số nhân
  · CPU% + RAM đỉnh của cả cây tiến trình
  · job nào đợi > 10 phút (nghẽn) · làn nào đói · %TEMP% phình · ffmpeg mồ côi
  · bao nhiêu video ra clip AI vs "Cắt cơ bản" **và VÌ SAO**

AN TOÀN (quy tắc sắt của repo):
  · sandbox `BQ_DB_PATH` + `BQ_DATA_DIR` + `BQ_QSETTINGS_INI` -> KHÔNG đụng DB
    thật, KHÔNG ghi QSettings thật của anh Hùng.
  · nguồn được **CHÉP** vào sandbox — dây chuyền XOÁ GỐC sau khi xuất, không
    bao giờ được xoá video thật trong Downloads.
  · key Groq đọc từ `%LOCALAPPDATA%\\BQHungVideo\\.env` rồi truyền qua **ENV**,
    KHÔNG ghi ra file nào.
  · `import _test_guard` -> cấm mở Explorer/trình phát trên máy user.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="ra_e2e_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "settings.ini")   # KHÔNG chạm registry
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WHISPER_PROVIDER"] = "groq"

# key Groq: đọc từ .env THẬT, chuyền qua ENV (không ghi file) — bài học cổng 22
_env_that = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo" / ".env"
if _env_that.exists():
    for _ln in _env_that.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import psutil  # noqa: E402

import _test_guard  # noqa: E402,F401 - CẤM test đụng máy user

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import DoLuong, _may_ranh  # noqa: E402

THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")
FFMPEG = REPO / "bin" / "ffmpeg.exe"

# Nguồn Nhật THẬT đã soi bằng `_ra_probe.py` (08/08/2026) — chọn phủ đủ ca,
# độ dài 2-14 phút (đúng cỡ video sản xuất, chạy hết trong 1 lượt đo được).
NGUON = [
    # (tên kênh, đuôi file để tìm, ca)
    ("Nhật · thể thao 25fps", "初めて両想いだと気づいた瞬間.mp4", "có lời · CFR 25fps · 119s"),
    ("Nhật · điều tra 30fps", "女探偵［岡田真弓］のMR浮気調査チャンネル.mp4", "có lời · CFR 29,97 · 333s"),
    ("Nhật · phóng sự VFR", "2週間後に自殺をしてしまいました。.mp4", "có lời · **VFR** · 607s"),
    ("Nhật · bất động sản 60fps", "デザイナーズ秘密基地を内見！.mp4", "có lời · CFR 59,94 · 653s"),
    ("Nhật · khám phá VFR", "GPSの犯人が訴えると脅して来たので晒します.mp4", "có lời · **VFR** · 718s"),
    ("Nhật · kinh dị 30fps", "｟心霊｠Japanese horror.mp4", "có lời · CFR 29,97 · 849s"),
]
# ca KHÔNG LỜI: hình là video Nhật THẬT, tiếng thay bằng im lặng -> chắc chắn
# rơi vào nhánh `co_loi_noi_that()==False` -> phải đi đường XEM HÌNH (v2.15.0).
KHONG_LOI_TU = "初めて両想いだと気づいた瞬間.mp4"


def tim(duoi: str) -> Path | None:
    for p in THUNG.rglob("*.mp4"):
        if p.name.endswith(duoi):
            return p
    return None


def dung_nguon(sb: Path, so_video: int) -> list[tuple[str, Path, str]]:
    """Chép nguồn THẬT vào sandbox (mỗi kênh 1 thư mục). Trả [(kênh, file, ca)]."""
    root = sb / "daychuyen"
    ra: list[tuple[str, Path, str]] = []
    for ten_kenh, duoi, ca in NGUON[:so_video]:
        src = tim(duoi)
        if not src:
            print(f"  !! KHÔNG thấy nguồn {duoi}")
            continue
        d = root / ten_kenh
        d.mkdir(parents=True, exist_ok=True)
        dst = d / src.name
        shutil.copy2(src, dst)
        old = time.time() - 3600           # mtime cũ -> coi như tải xong
        os.utime(dst, (old, old))
        ra.append((ten_kenh, dst, ca))
        print(f"  + {ten_kenh:28s} {ca:34s} {src.stat().st_size/1024/1024:6.0f} MB")

    # ---- ca KHÔNG LỜI ----
    src = tim(KHONG_LOI_TU)
    if src:
        d = root / "Nhật · KHÔNG LỜI"
        d.mkdir(parents=True, exist_ok=True)
        dst = d / ("khong_loi_" + src.name)
        r = subprocess.run(
            [str(FFMPEG), "-y", "-v", "error", "-i", str(src),
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-map", "0:v:0", "-map", "1:a:0", "-shortest",
             "-c:v", "copy", "-c:a", "aac", str(dst)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and dst.exists():
            old = time.time() - 3600
            os.utime(dst, (old, old))
            ra.append(("Nhật · KHÔNG LỜI", dst,
                       "KHÔNG LỜI (hình Nhật thật, tiếng im lặng)"))
            print(f"  + {'Nhật · KHÔNG LỜI':28s} "
                  f"{'KHÔNG LỜI -> phải đi đường XEM HÌNH':34s} "
                  f"{dst.stat().st_size/1024/1024:6.0f} MB")
        else:
            print(f"  !! dựng ca KHÔNG LỜI hỏng: {r.stderr[:200]}")
    return ra


def kich_thuoc(d: Path) -> tuple[int, int]:
    """(số file, tổng byte) — bỏ qua file bị khoá."""
    n = t = 0
    try:
        for p in d.rglob("*"):
            try:
                if p.is_file():
                    n += 1
                    t += p.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return n, t


def rac_temp() -> dict[str, int]:
    tmp = Path(tempfile.gettempdir())
    ra = {"_seg_": 0, "_MEI": 0, "_nhip_": 0}
    try:
        for p in tmp.iterdir():
            for k in ra:
                if p.name.startswith(k):
                    ra[k] += 1
    except OSError:
        pass
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-video", type=int, default=6)
    ap.add_argument("--phut", type=float, default=45.0, help="trần thời gian")
    ap.add_argument("--du-may-ban", action="store_true")
    a = ap.parse_args()

    ok_ranh, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok_ranh and not a.du_may_ban:
        print("DỪNG: máy đang bận -> số đo sẽ sai. Dùng --du-may-ban nếu buộc phải đo.")
        return 2
    n_key = len([x for x in os.environ.get("GROQ_API_KEYS", "").replace(",", "\n")
                 .splitlines() if x.strip()])
    print(f"[key Groq] {n_key} key (0 = sẽ tụt về whisper MÁY, rất chậm)")
    print(f"[sandbox] {_SB}")

    rac0 = rac_temp()
    tmp_n0, tmp_b0 = kich_thuoc(Path(tempfile.gettempdir()))
    print(f"[%TEMP% trước] {tmp_n0} file · {tmp_b0/1024/1024/1024:.2f} GB · "
          f"rác {rac0}")

    print("\n── Chép nguồn THẬT vào sandbox (gốc trong Downloads KHÔNG bị đụng) ──")
    ds = dung_nguon(_SB, a.so_video)
    if len(ds) < 5:
        print(f"DỪNG: chỉ dựng được {len(ds)} video, cần ≥5.")
        return 2
    root = _SB / "daychuyen"

    # ---------- dựng app ----------
    import app.queue.jobs  # noqa: F401  (cv2 nạp trước Qt — đúng thứ tự main.py)
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from app.core import ffmpeg_utils as fu
    from app.database.db import db
    from app.ui.appsettings import app_settings
    from app.ui.state import AppState
    from app.ui.studio_page import StudioPage

    qapp = QApplication(sys.argv)          # PHẢI giữ biến (bẫy 0xC0000409)
    st = app_settings()
    st.setValue("pipe_root", str(root))
    st.setValue("chan_group", "Nhật")
    st.setValue("chan_groups_extra", "[]")
    st.setValue("pipe_grp_sel", "Nhật")
    st.sync()

    for ten_kenh, f, _ca in ds:
        d = f.parent
        db.execute(
            "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_src, "
            "pipe_on, pipe_mode, pipe_daily) "
            "VALUES(?, ?, 'Nhật', ?, ?, 1, 'auto', 0)",
            (ten_kenh, str(_SB / "assets"), str(d), str(d)))

    print(f"\n[encoder] {fu.detect_encoder()} · trần ffmpeg song song "
          f"{fu.so_ffmpeg_song_song()} · giải mã {fu.decode_threads()} luồng "
          f"· nhân {os.cpu_count()}")
    db_b0 = Path(os.environ["BQ_DB_PATH"]).stat().st_size if \
        Path(os.environ["BQ_DB_PATH"]).exists() else 0

    state = AppState()
    state.start()
    pg = StudioPage(state)

    t0 = time.time()
    n_nhan = pg._pipe_run()
    print(f"\n>> dây chuyền NHẬN {n_nhan} video / {len(ds)} kênh\n")

    # ---------- đo trong lúc chạy ----------
    tre: list[float] = []
    moc = {"t": 0.0}
    NHIP = 50
    may: list[tuple[float, float, float]] = []   # (t, cpu%, rss_GB cây)
    xong = {"het": False}
    han = t0 + a.phut * 60

    me = psutil.Process()

    def _lay_may() -> None:
        me.cpu_percent(None)
        while not xong["het"]:
            try:
                rss = me.memory_info().rss
                for c in me.children(recursive=True):
                    try:
                        rss += c.memory_info().rss
                    except psutil.Error:
                        pass
                may.append((time.time() - t0,
                            psutil.cpu_percent(None), rss / 1024 ** 3))
            except psutil.Error:
                pass
            time.sleep(1.0)

    th_may = threading.Thread(target=_lay_may, daemon=True)

    def _tick() -> None:
        now = time.perf_counter()
        if moc["t"]:
            tre.append(max(0.0, (now - moc["t"]) * 1000.0 - NHIP))
        moc["t"] = now
        # ĐÚNG việc app thật làm mỗi nhịp (xem `_poll_tick`)
        try:
            pg._check_auto_export()
            pg._pipe_poll()
        except Exception as e:      # noqa: BLE001
            print(f"  !! poll nổ: {type(e).__name__}: {e}")
        moc["t"] = time.perf_counter()   # trừ phần việc poll ra khỏi nhịp sau
        con = db.query_one(
            "SELECT COUNT(*) c FROM pipeline_files "
            "WHERE status NOT IN ('done','error','dup','bad')")
        if (con and int(con["c"]) == 0) or time.time() > han:
            xong["het"] = True
            qapp.quit()

    tm = QTimer()
    tm.setInterval(NHIP)
    tm.timeout.connect(_tick)

    with DoLuong() as d:
        th_may.start()
        tm.start()
        qapp.exec()
    xong["het"] = True
    wall = time.time() - t0
    state.stop()
    time.sleep(1.5)

    # ---------- kết quả ----------
    cores = os.cpu_count() or 1
    print("=" * 78)
    print(f"XONG sau {wall:.0f}s ({wall/60:.1f} phút)")
    print("=" * 78)

    print("\n══ CÂU 1 — TÍCH HỢP CÓ CHẠY KHÔNG ══")
    so = db.query("SELECT p.name kenh, f.file_name, f.status, f.note "
                  "FROM pipeline_files f JOIN projects p ON p.id=f.project_id "
                  "ORDER BY f.id")
    n_done = n_err = 0
    for r in so:
        n_done += r["status"] == "done"
        n_err += r["status"] in ("error", "bad")
        print(f"  {r['status']:7s} {r['kenh'][:26]:26s} "
              f"{(r['note'] or '')[:44]}")
    parts = sorted(root.rglob("Part *.mp4"))
    goc_con = [f for _k, f, _c in ds if f.exists()]
    n0 = [p for p in parts if p.stat().st_size == 0]
    print(f"  -> done {n_done} · lỗi {n_err} · Part xuất ra {len(parts)} "
          f"· Part 0-byte {len(n0)} · gốc CHƯA xoá {len(goc_con)}")

    print("\n══ CÂU 2 — CHẠY MƯỢT CHƯA ══")
    tv = round(statistics.median(tre), 1) if tre else -1
    p95 = round(sorted(tre)[int(len(tre) * 0.95)], 1) if tre else -1
    dinh = round(max(tre), 1) if tre else -1
    cpu_dinh = round(max((x[1] for x in may), default=0), 1)
    cpu_tb = round(statistics.mean([x[1] for x in may]), 1) if may else -1
    ram_dinh = round(max((x[2] for x in may), default=0), 2)
    print(f"  trễ vòng lặp UI  trung vị {tv}ms · p95 {p95}ms · đỉnh {dinh}ms "
          f"({len(tre)} nhịp / {len(tre)*NHIP/1000:.0f}s)")
    print(f"  CPU cả máy       TB {cpu_tb}% · đỉnh {cpu_dinh}%")
    print(f"  RAM cây tiến trình đỉnh {ram_dinh} GB")
    print(f"  luồng ffmpeg     đỉnh {d.dinh_luong} "
          f"({d.dinh_luong/cores:.2f}× nhân) · TB {d.tb_luong} "
          f"· đỉnh {d.dinh_tt} tiến trình")

    print("\n══ CÂU 4 — XỬ LÝ AI ══")
    vids = db.query("SELECT v.id, v.src_path, p.name kenh FROM videos v "
                    "JOIN projects p ON p.id=v.project_id ORDER BY v.id")
    n_ai = n_cb = 0
    for v in vids:
        cl = db.query("SELECT signals, title FROM clips WHERE video_id=? "
                      "AND status!='archived'", (v["id"],))
        ai = xh = False
        for c in cl:
            s = db.loads(c["signals"], {}) or {}
            ai = ai or bool(s.get("llm_used"))
            xh = xh or bool(s.get("xem_hinh"))
        nhan = ("AI" + (" + XEM HÌNH" if xh else "")) if ai else "CẮT CƠ BẢN"
        n_ai += ai
        n_cb += (not ai) and bool(cl)
        print(f"  {nhan:14s} {len(cl)} clip  {v['kenh'][:28]:28s}")
    print(f"  -> {n_ai} video ra clip AI · {n_cb} rơi Cắt cơ bản")

    print("\n══ CÂU 5 — CÓ NGHẼN KHÔNG ══")
    js = db.query("SELECT type,status,started_at,finished_at,created_at,error "
                  "FROM jobs ORDER BY id")
    dem: dict[str, int] = {}
    loi = []
    for j in js:
        k = f"{j['type']}/{j['status']}"
        dem[k] = dem.get(k, 0) + 1
        if j["status"] == "failed":
            loi.append(f"{j['type']}: {(j['error'] or '')[:120]}")
    print(f"  job: {dem}")
    doi = db.query(
        "SELECT type, (julianday(COALESCE(started_at,'now'))-"
        "julianday(created_at))*86400 gio FROM jobs ORDER BY gio DESC LIMIT 3")
    for r in doi:
        print(f"  đợi lâu nhất: {r['type']} {r['gio']:.0f}s")
    if loi:
        print(f"  JOB THẤT BẠI ({len(loi)}):")
        for x in loi[:6]:
            print("   -", x)
    mo_coi = [p.pid for p in psutil.process_iter(["name"])
              if (p.info["name"] or "").lower().startswith("ffmpeg")]
    rac1 = rac_temp()
    tmp_n1, tmp_b1 = kich_thuoc(Path(tempfile.gettempdir()))
    db_b1 = Path(os.environ["BQ_DB_PATH"]).stat().st_size
    print(f"  ffmpeg mồ côi (toàn máy): {len(mo_coi)}")
    print(f"  rác %TEMP%: trước {rac0} -> sau {rac1}")
    print(f"  %TEMP% tổng: {tmp_b0/1024**3:.2f} GB -> {tmp_b1/1024**3:.2f} GB "
          f"({tmp_n1-tmp_n0:+d} file)")
    print(f"  DB: {db_b0/1024:.0f} KB -> {db_b1/1024:.0f} KB "
          f"(+{(db_b1-db_b0)/1024:.0f} KB cho {len(vids)} video)")

    # nhật ký AI để đọc LÝ DO
    lg = _SB / "logs"
    if lg.is_dir():
        print(f"\n  nhật ký: {[p.name for p in lg.glob('*.log')]}")

    ket = {
        "wall_s": round(wall, 1), "nhan": n_nhan, "done": n_done, "loi": n_err,
        "part": len(parts), "part_0byte": len(n0), "goc_con": len(goc_con),
        "ui_tv": tv, "ui_p95": p95, "ui_dinh": dinh,
        "cpu_tb": cpu_tb, "cpu_dinh": cpu_dinh, "ram_dinh_gb": ram_dinh,
        "luong_dinh": d.dinh_luong, "luong_tb": d.tb_luong,
        "tien_trinh_dinh": d.dinh_tt, "nhan_x": round(d.dinh_luong/cores, 2),
        "video_ai": n_ai, "video_co_ban": n_cb,
        "job": dem, "ffmpeg_mo_coi": len(mo_coi),
        "db_kb_truoc": round(db_b0/1024), "db_kb_sau": round(db_b1/1024),
        "sandbox": str(_SB),
    }
    (REPO / "_ket__ra_e2e.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[đã ghi] _ket__ra_e2e.json")
    print(f"[sandbox giữ lại để soi] {_SB}")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
