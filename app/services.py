"""
Lớp service: API mức cao cho UI. Giấu chi tiết DB/queue.

Pipeline điển hình:
  create_project -> import_video -> enqueue_auto (phân tích + tìm highlight)
  -> (duyệt clip) -> enqueue_export
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Optional

from app.core.analysis import STEPS, analysis_status
from app.core.ffmpeg_utils import probe
from app.database import db
from app.queue.worker import WorkerPool
from config import PROJECTS_DIR


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return s.strip("_") or "project"


def _file_hash(path: str, chunk: int = 1 << 20) -> str:
    """Hash nhanh: kích thước + đầu/cuối file (đủ cho smart-skip)."""
    p = Path(path)
    h = hashlib.sha1()
    h.update(str(p.stat().st_size).encode())
    with open(p, "rb") as f:
        h.update(f.read(chunk))
        if p.stat().st_size > chunk * 2:
            f.seek(-chunk, 2)
            h.update(f.read(chunk))
    return h.hexdigest()[:16]


# ---- Project ----
def create_project(name: str) -> int:
    assets = PROJECTS_DIR / f"{_slug(name)}"
    i = 1
    base = assets
    while assets.exists():
        assets = Path(f"{base}_{i}")
        i += 1
    assets.mkdir(parents=True, exist_ok=True)
    return db.insert(
        "INSERT INTO projects (name, assets_dir) VALUES (?,?)",
        (name, str(assets)),
    )


def list_projects() -> list:
    return db.query("SELECT * FROM projects ORDER BY created_at DESC")


# ---- Video ----
def import_video(project_id: int, src_path: str) -> int:
    info = probe(src_path)
    fh = _file_hash(src_path)
    # smart-skip: cùng project + cùng file đã import -> trả lại id cũ
    existing = db.query_one(
        "SELECT id FROM videos WHERE project_id=? AND file_hash=?",
        (project_id, fh),
    )
    if existing:
        return int(existing["id"])
    return db.insert(
        """INSERT INTO videos (project_id, src_path, file_hash, duration,
                               width, height, fps, has_audio)
           VALUES (?,?,?,?,?,?,?,?)""",
        (project_id, src_path, fh, info.duration, info.width, info.height,
         info.fps, 1 if info.has_audio else 0),
    )


def list_videos(project_id: int) -> list:
    return db.query("SELECT * FROM videos WHERE project_id=? ORDER BY id",
                    (project_id,))


# ---- Enqueue (qua worker pool) ----
def enqueue_analysis(pool: WorkerPool, video_id: int, project_id: int,
                     force: bool = False) -> Optional[int]:
    return pool.enqueue(
        "analyze", {"video_id": video_id, "force": force},
        project_id=project_id, video_id=video_id,
        needs_gpu=True,  # transcribe/face nặng -> ưu tiên hàng đợi GPU nếu có
        priority=10,
        dedup_key=None if force else f"analyze:{video_id}",
    )


def enqueue_auto(pool: WorkerPool, video_id: int, project_id: int,
                 preset: Optional[dict] = None) -> Optional[int]:
    """Nút 'Tạo clip tự động': phân tích (nếu chưa) + tìm highlight trong 1 job."""
    # dedup: bấm 2 lần khi job đang chờ/chạy -> KHÔNG tạo job trùng (2 job auto
    # song song sẽ gọi LLM 2 lần + ghi đè lẫn nhau bảng clips). skip_if_done=False
    # để sau khi xong vẫn bấm "Tạo clip" lại được (tạo lại gợi ý mới).
    return pool.enqueue(
        "auto", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"auto:{video_id}", skip_if_done=False,
    )


def enqueue_auto_mixed(pool: WorkerPool, video_id: int, project_id: int,
                       preset: Optional[dict] = None) -> Optional[int]:
    """Nút 'Mixed-Cut': phân tích (nếu chưa) + ghép khoảnh khắc hay nhất."""
    return pool.enqueue(
        "auto_mixed", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"automix:{video_id}", skip_if_done=False,
    )


def enqueue_auto_recap(pool: WorkerPool, video_id: int, project_id: int,
                       preset: Optional[dict] = None) -> Optional[int]:
    """Nút '🎙 Reup thuyết minh': phân tích (nếu chưa) + AI viết kịch bản
    thuyết minh (preset kèm recap_style/recap_ratio/recap_count). Dedup như
    auto — recap_count vào dedup key để đổi 'Số clip' rồi bấm lại vẫn chạy
    (job cũ khác count đang chờ không nuốt mất lần bấm mới)."""
    try:                                # 0 = "Tự động theo độ dài" (hợp lệ,
        cnt = int((preset or {}).get("recap_count", 0) or 0)   # đừng ép về 2)
    except (TypeError, ValueError):
        cnt = 0
    return pool.enqueue(
        "auto_recap", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"autorecap:{video_id}:c{cnt}", skip_if_done=False,
    )


def enqueue_export(pool: WorkerPool, clip_id: int, video_id: int,
                   project_id: int, out_w: int = 1080, out_h: int = 1920,
                   mode: str = "face", zoom: float = 1.0,
                   crop_rect=None, text_overlays=None, overlay_png=None,
                   video_rect=None, bg: str = "blur",
                   trim_black: bool = False, part_no: int = 0,
                   out_name: str = "", captions: bool = False,
                   cap_style: Optional[dict] = None,
                   blur_amt: int = 22, speed: float = 1.0,
                   pitch: float = 1.0, out_dir: str = "",
                   hook_first: bool = False, bgm_path: str = "",
                   bgm_vol: float = 0.15, orig_vol: float = 1.0,
                   dub_lang: str = "",
                   dub_voice: str = "", dub_mute: bool = False,
                   dub_mode: str = "natural",
                   recap_voice: str = "", recap_pace: str = "",
                   recap_pitch: str = "", recap_volume: float = 1.15,
                   recap_emotion: bool = True, recap_dim: float = 0.14,
                   fx_fade: bool = True, fx_whoosh: bool = True,
                   fx_sfx_dir: str = "", flip_h: bool = False,
                   fit_src: bool = False,
                   force: bool = False) -> Optional[int]:
    """force=True: xuất lại kể cả khi từng xuất xong y hệt (nút 'Xuất lại' /
    'Xuất clip này' — user chủ động muốn file mới, vd đã lỡ xóa file cũ)."""
    # sig phải phủ MỌI thứ ảnh hưởng kết quả: cả mốc cắt start/end của clip
    # (user kéo sửa trim rồi xuất lại) + NỘI DUNG chữ (overlay_png là đường dẫn
    # cố định _ovl_{clip_id}.png nên phải hash nội dung file) + nơi lưu.
    row = db.query_one("SELECT start_sec, end_sec FROM clips WHERE id=?",
                       (clip_id,))
    se = f"{row['start_sec']:.3f}-{row['end_sec']:.3f}" if row else "?"
    ovl = ""
    if overlay_png:
        try:
            st = Path(overlay_png).stat()
            ovl = f"{st.st_size}:{st.st_mtime_ns}"
        except OSError:
            pass
    extra = hashlib.sha1(
        repr((text_overlays, cap_style, out_name, out_dir, ovl,
              hook_first, bgm_path, bgm_vol, orig_vol,
              dub_lang, dub_voice, dub_mute, dub_mode,
              recap_voice, recap_pace, recap_pitch,
              round(float(recap_volume or 0), 3), bool(recap_emotion),
              round(float(recap_dim or 0), 3),
              fx_fade, fx_whoosh, fx_sfx_dir, flip_h, fit_src)).encode()
    ).hexdigest()[:12]
    sig = (f"{se}:{mode}:{zoom}:{crop_rect}:{video_rect}:{bg}:{trim_black}:"
           f"cap{int(captions)}:{blur_amt}:{speed}:{pitch}:{extra}")
    return pool.enqueue(
        "m1_export_clip",
        {"clip_id": clip_id, "out_w": out_w, "out_h": out_h,
         "mode": mode, "zoom": zoom, "crop_rect": crop_rect,
         "text_overlays": text_overlays or [], "overlay_png": overlay_png,
         "video_rect": video_rect, "bg": bg, "trim_black": trim_black,
         "part_no": part_no, "out_name": out_name, "captions": captions,
         "cap_style": cap_style or {}, "blur_amt": blur_amt,
         "speed": speed, "pitch": pitch, "out_dir": out_dir,
         "hook_first": hook_first, "bgm_path": bgm_path, "bgm_vol": bgm_vol,
         "orig_vol": orig_vol,
         "dub_lang": dub_lang, "dub_voice": dub_voice, "dub_mute": dub_mute,
         "dub_mode": dub_mode,
         "recap_voice": recap_voice, "recap_pace": recap_pace,
         "recap_pitch": recap_pitch, "recap_volume": recap_volume,
         "recap_emotion": recap_emotion, "recap_dim": recap_dim,
         "fx_fade": fx_fade, "fx_whoosh": fx_whoosh,
         "fx_sfx_dir": fx_sfx_dir, "flip_h": flip_h, "fit_src": fit_src},
        project_id=project_id, video_id=video_id,
        needs_gpu=False, priority=3,   # cắt/xuất libx264 -> lane CPU (luồng cắt riêng)
        dedup_key=f"export:{clip_id}:{out_w}x{out_h}:p{part_no}:{sig}",
        skip_if_done=not force,
    )


# ---- Truy vấn cho UI ----
def list_clips(video_id: int) -> list:
    # Theo thứ tự THỜI GIAN (đoạn đầu -> cuối) để Part 1,2,3 đúng thứ tự.
    return db.query(
        "SELECT * FROM clips WHERE video_id=? ORDER BY start_sec, id",
        (video_id,),
    )


# ---- Mẫu (template/preset) cho Module 1 ----
def save_template(name: str, data: dict) -> None:
    """Lưu/ghi đè mẫu theo tên (khung + các lớp chữ)."""
    db.execute(
        "INSERT INTO presets (name, module, data) VALUES (?, 'm1', ?) "
        "ON CONFLICT(name) DO UPDATE SET data=excluded.data",
        (name, db.dumps(data)),
    )


def list_templates() -> list:
    return db.query("SELECT name FROM presets WHERE module='m1' ORDER BY name")


def get_template(name: str) -> Optional[dict]:
    row = db.query_one("SELECT data FROM presets WHERE name=? AND module='m1'", (name,))
    return db.loads(row["data"]) if row else None


def delete_template(name: str) -> None:
    db.execute("DELETE FROM presets WHERE name=? AND module='m1'", (name,))


def clear_finished_jobs() -> int:
    """Xóa lịch sử job ĐÃ XONG/lỗi/hủy khỏi danh sách tiến trình. GIỮ việc đang
    chạy/chờ. Trả số dòng đã xóa."""
    cur = db.execute(
        "DELETE FROM jobs WHERE status IN ('done','failed','canceled','skipped')")
    try:
        return cur.rowcount if cur else 0
    except Exception:  # noqa: BLE001
        return 0


def job_state(job_id: int) -> str:
    """Trạng thái 1 job ('done'/'failed'/'running'/'pending'/...); '' nếu không có.
    Dùng cho TỰ ĐỘNG XUẤT: theo dõi job phân tích, xong thì kích hoạt xuất."""
    if not job_id:
        return ""
    row = db.query_one("SELECT status FROM jobs WHERE id=?", (job_id,))
    return row["status"] if row else ""


def list_jobs(limit: int = 100) -> list:
    # kèm tên KÊNH + đường dẫn video để thanh tiến trình hiện rõ việc nào của ai
    return db.query(
        "SELECT j.*, p.name AS chan_name, v.src_path AS vid_path "
        "FROM jobs j "
        "LEFT JOIN projects p ON p.id = j.project_id "
        "LEFT JOIN videos v ON v.id = j.video_id "
        "ORDER BY "
        "CASE j.status WHEN 'running' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, "
        "j.id DESC LIMIT ?", (limit,),
    )


def queue_counts() -> dict:
    """Đếm job cho BẢNG ĐẾM TRẠNG THÁI khu Tiến trình (1 query GROUP BY nhẹ,
    có idx_jobs_status).

    - analyzing / exporting: đang chạy (running) — xuất = m1_export_clip,
      còn lại là giai đoạn phân tích (khớp màu giai đoạn ở queue_panel).
    - waiting: mọi việc pending (kèm tách wait_analyze / wait_export).
    - done / failed: CHỈ đếm việc tạo HÔM NAY (created_at của SQLite là
      datetime('now') = UTC -> quy đổi 0h local sang UTC để so sánh).
    - canceled / skipped: KHÔNG tính vào bất kỳ ô nào.
    """
    from datetime import datetime, timezone
    day0 = (datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    rows = db.query(
        "SELECT status, type, COUNT(*) AS n FROM jobs "
        "WHERE status IN ('running','pending') "
        "   OR (status IN ('done','failed') AND created_at >= ?) "
        "GROUP BY status, type", (day0,))
    c = {"analyzing": 0, "exporting": 0, "waiting": 0,
         "wait_analyze": 0, "wait_export": 0, "done": 0, "failed": 0}
    for r in rows:
        st, jt, n = r["status"], r["type"], int(r["n"])
        if st == "running":
            c["exporting" if jt == "m1_export_clip" else "analyzing"] += n
        elif st == "pending":
            c["waiting"] += n
            c["wait_export" if jt == "m1_export_clip" else "wait_analyze"] += n
        elif st == "done":
            c["done"] += n
        elif st == "failed":
            c["failed"] += n
    return c


# ---- Hoạt động theo KÊNH (nhãn cạnh combo Kênh + bảng "Tình hình các kênh") ----
def channel_activity() -> dict:
    """Tình hình job của TOÀN BỘ kênh trong 2 query GROUP BY (dùng
    idx_jobs_project, KHÔNG query từng kênh — user chạy nhiều kênh cùng lúc).

    Trả dict[project_id] = {
        "running": n, "pending": n,
        "failed_recent": n,        # job failed trong 24h qua
        "exported": n,             # tổng clip đã xuất xong (m1_export_clip done)
        "last_done": "YYYY-MM-DD HH:MM:SS" (UTC, như SQLite ghi) | None,
        "last_done_type": type của job done gần nhất ("auto"/"m1_export_clip"...),
    } — mọi project đều có mặt (kênh chưa có job = toàn 0/None).
    """
    from datetime import datetime, timedelta, timezone
    # SQLite datetime('now') ghi UTC -> mốc 24h cũng phải tính bằng UTC
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)
              ).strftime("%Y-%m-%d %H:%M:%S")
    act = {int(p["id"]): {"running": 0, "pending": 0, "failed_recent": 0,
                          "exported": 0, "last_done": None,
                          "last_done_type": ""}
           for p in db.query("SELECT id FROM projects")}
    for r in db.query(
            "SELECT project_id AS pid, "
            "SUM(status='running') AS running, "
            "SUM(status='pending') AS pending, "
            "SUM(status='failed' AND COALESCE(finished_at, created_at) >= ?) "
            "  AS failed_recent, "
            "SUM(status='done' AND type='m1_export_clip') AS exported "
            "FROM jobs WHERE project_id IS NOT NULL GROUP BY project_id",
            (cutoff,)):
        a = act.get(int(r["pid"]))
        if a is None:          # job của project vừa bị xóa (race) -> bỏ qua
            continue
        a["running"] = int(r["running"] or 0)
        a["pending"] = int(r["pending"] or 0)
        a["failed_recent"] = int(r["failed_recent"] or 0)
        a["exported"] = int(r["exported"] or 0)
    # MAX(finished_at) + bare column: SQLite ĐẢM BẢO cột trần (type) lấy từ
    # đúng dòng đạt MAX -> biết luôn job done gần nhất là loại gì, khỏi query 2.
    for r in db.query(
            "SELECT project_id AS pid, MAX(finished_at) AS last_done, "
            "type AS last_type FROM jobs "
            "WHERE status='done' AND finished_at IS NOT NULL "
            "AND project_id IS NOT NULL GROUP BY project_id"):
        a = act.get(int(r["pid"]))
        if a is not None:
            a["last_done"] = r["last_done"]
            a["last_done_type"] = r["last_type"] or ""
    return act


def rel_time_vi(iso_str, short: bool = False) -> str:
    """'2026-07-12 08:00:00' (UTC — như SQLite datetime('now') ghi) -> chuỗi
    tương đối tiếng Việt: 'vừa xong' (<90s), 'X phút trước' (<60ph),
    'X giờ trước' (<24h), 'hôm qua', 'N ngày trước'. None/hỏng -> ''.
    short=True: dạng gọn cho đuôi combo ('12ph', '3h', 'hôm qua')."""
    from datetime import datetime, timezone
    if not iso_str:
        return ""
    s = str(iso_str).strip().replace("T", " ")
    s = s.split(".")[0].split("+")[0].strip()      # bỏ .ms / +tz nếu có
    try:
        t = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return ""
    sec = (datetime.now(timezone.utc) - t).total_seconds()
    if sec < 0:                 # lệch đồng hồ nhẹ -> coi như vừa xong
        sec = 0
    if sec < 90:
        return "vừa xong"
    if sec < 3600:
        m = int(sec // 60)
        return f"{m}ph" if short else f"{m} phút trước"
    if sec < 86400:
        h = int(sec // 3600)
        return f"{h}h" if short else f"{h} giờ trước"
    d = int(sec // 86400)
    if d == 1:
        return "hôm qua"
    return f"{d} ngày" if short else f"{d} ngày trước"


# ---- Trạng thái phân tích ----
def video_analyzed(video_id: int) -> bool:
    """True nếu video đã chạy xong lõi phân tích (mọi bước done/skipped)."""
    st = analysis_status(video_id)
    if not st:
        return False
    return all(st.get(kind) in ("done", "skipped") for kind, _ in STEPS)


def video_analysis_label(video_id: int) -> str:
    """Nhãn ngắn cho UI: chưa / đang / xong / lỗi."""
    st = analysis_status(video_id)
    if not st:
        return "○ chưa phân tích"
    if any(v == "running" for v in st.values()):
        return "⏳ đang phân tích"
    if any(v == "failed" for v in st.values()):
        return "⚠ phân tích lỗi"
    if video_analyzed(video_id):
        return "✓ đã phân tích"
    return "○ chưa xong"


# ---- Xóa (dọn dữ liệu) ----
def _project_dir(project_id: int) -> Optional[Path]:
    row = db.query_one("SELECT assets_dir FROM projects WHERE id=?", (project_id,))
    return Path(row["assets_dir"]) if row else None


def cache_dir(assets_dir) -> str:
    """Thư mục con _cache chứa ảnh tạm (thumbnail/preview/lớp chữ) — KHÔNG để lẫn
    vào thư mục người dùng nhìn. Tạo nếu chưa có."""
    d = Path(assets_dir) / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def project_cache_dir(project_id: int) -> Optional[str]:
    pdir = _project_dir(project_id)
    return cache_dir(pdir) if pdir else None


def project_dir(project_id: int) -> Optional[str]:
    """Thư mục gốc của Kênh (chứa các folder con theo từng video)."""
    pdir = _project_dir(project_id)
    return str(pdir) if pdir else None


def delete_clip(clip_id: int) -> None:
    """Xóa 1 clip: file đã xuất + thumbnail + dòng DB."""
    row = db.query_one(
        """SELECT cl.export_path, p.assets_dir FROM clips cl
           JOIN videos v ON v.id=cl.video_id JOIN projects p ON p.id=v.project_id
           WHERE cl.id=?""", (clip_id,))
    if row:
        for f in (row["export_path"],
                  str(Path(cache_dir(row["assets_dir"])) / f"_thumb_{clip_id}.jpg")):
            if f:
                try:
                    Path(f).unlink(missing_ok=True)
                except OSError:
                    pass
    db.execute("DELETE FROM clips WHERE id=?", (clip_id,))


def _cancel_jobs(pool: Optional[WorkerPool], where: str, params: tuple) -> None:
    """Hủy job đang chờ/chạy trước khi xóa video/kênh — nếu không, dòng job bị
    cascade-xóa khỏi panel nhưng tiến trình phân tích/ffmpeg VẪN chạy ngầm và
    có thể tạo lại thư mục 'ma' sau khi xóa."""
    if not pool:
        return
    for j in db.query(
            f"SELECT id FROM jobs WHERE status IN ('pending','running') "
            f"AND {where}", params):
        pool.cancel(int(j["id"]))


def delete_video(video_id: int, pool: Optional[WorkerPool] = None) -> None:
    """
    Xóa 1 video khỏi project: hủy job liên quan, xóa file clip đã xuất +
    thumbnail + file audio tạm, rồi xóa dòng DB (cascade analysis/clips/jobs).
    """
    _cancel_jobs(pool, "video_id=?", (video_id,))
    proj = db.query_one("SELECT project_id FROM videos WHERE id=?", (video_id,))
    pdir = _project_dir(proj["project_id"]) if proj else None
    # xóa file clip + thumbnail trên đĩa
    for c in db.query("SELECT id, export_path FROM clips WHERE video_id=?",
                      (video_id,)):
        if c["export_path"]:
            try:
                Path(c["export_path"]).unlink(missing_ok=True)
            except OSError:
                pass
        if pdir:
            try:
                (Path(cache_dir(pdir)) / f"_thumb_{c['id']}.jpg").unlink(
                    missing_ok=True)
            except OSError:
                pass
    # xóa audio tạm nếu còn (nằm trong _cache/; dọn thêm chỗ cũ cho bản trước)
    if pdir:
        for wav in (pdir / "_cache" / f"audio_{video_id}.wav",
                    pdir / f"audio_{video_id}.wav"):
            try:
                wav.unlink(missing_ok=True)
            except OSError:
                pass
    db.execute("DELETE FROM videos WHERE id=?", (video_id,))  # cascade


def cleanup_stale_temp(days: float = 3.0) -> int:
    """Dọn FILE TẠM MỒ CÔI trong projects/*/_cache lúc khởi động (chạy nền).

    Đo thật cho thấy file tạm tích tụ khi job bị hủy/app bị tắt giữa chừng:
    audio_*.wav (29-38MB/video), _dub_*.wav (~30-50MB/clip), _ovl_*.png,
    _cap_*.ass, _vlf_*.jpg. Job đang chạy luôn tạo file MỚI (mtime hiện tại)
    nên chỉ xóa file cũ hơn `days` ngày — an toàn tuyệt đối với job đang chạy
    lẫn job sẽ retry. Kèm: giữ tối đa 3 bản studio_backup_*.db mới nhất.
    Trả về số file đã xóa (để log/test)."""
    import time
    from config import DATA_DIR, PROJECTS_DIR
    cutoff = time.time() - days * 86400
    n = 0
    pats = ("_ovl_*.png", "_cap_*.ass", "_dub_*.wav", "_vlf_*.jpg",
            "audio_*.wav")
    try:
        cache_dirs = list(PROJECTS_DIR.glob("*/_cache"))
    except OSError:
        cache_dirs = []
    for cd in cache_dirs:
        for pat in pats:
            try:
                for f in cd.glob(pat):
                    try:
                        if f.stat().st_mtime < cutoff:
                            f.unlink()
                            n += 1
                    except OSError:
                        pass
            except OSError:
                pass
    # backup DB (tạo khi cứu DB hỏng): giữ 3 bản mới nhất, xóa phần còn lại
    try:
        baks = sorted(DATA_DIR.glob("studio_backup_*.db"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        for f in baks[3:]:
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
    except OSError:
        pass
    return n


def delete_project(project_id: int, pool: Optional[WorkerPool] = None) -> None:
    """Xóa cả project: hủy job, xóa thư mục assets + dòng DB (cascade toàn bộ)."""
    _cancel_jobs(pool, "project_id=?", (project_id,))
    pdir = _project_dir(project_id)
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))  # cascade
    if pdir and pdir.exists():
        try:
            shutil.rmtree(pdir, ignore_errors=True)
        except OSError:
            pass
