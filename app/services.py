"""
Lớp service: API mức cao cho UI. Giấu chi tiết DB/queue.

Pipeline điển hình:
  create_project -> import_video -> enqueue_analysis ->
  enqueue_highlights -> (duyệt clip) -> enqueue_export
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
    return pool.enqueue(
        "auto", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
    )


def enqueue_highlights(pool: WorkerPool, video_id: int, project_id: int,
                       preset: Optional[dict] = None) -> Optional[int]:
    return pool.enqueue(
        "m1_highlights", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, priority=5,
    )


def enqueue_mixed_cut(pool: WorkerPool, video_id: int, project_id: int,
                      preset: Optional[dict] = None) -> Optional[int]:
    return pool.enqueue(
        "m1_mixed_cut", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, priority=5,
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
                   pitch: float = 1.0, out_dir: str = "") -> Optional[int]:
    sig = (f"{mode}:{zoom}:{crop_rect}:{video_rect}:{bg}:{trim_black}:"
           f"{overlay_png}:cap{int(captions)}:{cap_style}:{blur_amt}:{speed}:{pitch}")
    return pool.enqueue(
        "m1_export_clip",
        {"clip_id": clip_id, "out_w": out_w, "out_h": out_h,
         "mode": mode, "zoom": zoom, "crop_rect": crop_rect,
         "text_overlays": text_overlays or [], "overlay_png": overlay_png,
         "video_rect": video_rect, "bg": bg, "trim_black": trim_black,
         "part_no": part_no, "out_name": out_name, "captions": captions,
         "cap_style": cap_style or {}, "blur_amt": blur_amt,
         "speed": speed, "pitch": pitch, "out_dir": out_dir},
        project_id=project_id, video_id=video_id,
        needs_gpu=False, priority=3,   # cắt/xuất libx264 -> lane CPU (luồng cắt riêng)
        dedup_key=f"export:{clip_id}:{out_w}x{out_h}:p{part_no}:{sig}",
    )


# ---- Truy vấn cho UI ----
def list_clips(video_id: int) -> list:
    # Theo thứ tự THỜI GIAN (đoạn đầu -> cuối) để Part 1,2,3 đúng thứ tự.
    return db.query(
        "SELECT * FROM clips WHERE video_id=? ORDER BY start_sec, id",
        (video_id,),
    )


def update_clip_range(clip_id: int, start: float, end: float) -> None:
    db.execute("UPDATE clips SET start_sec=?, end_sec=? WHERE id=?",
               (start, end, clip_id))


def set_clip_status(clip_id: int, status: str) -> None:
    db.execute("UPDATE clips SET status=? WHERE id=?", (status, clip_id))


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


def clips_dir(project_id: int) -> Optional[str]:
    """Thư mục chứa clip đã xuất của project (tạo nếu chưa có)."""
    pdir = _project_dir(project_id)
    if not pdir:
        return None
    out = pdir / "clips"
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


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


def set_export_dir(project_id: int, path: str) -> None:
    db.execute("UPDATE projects SET export_dir=? WHERE id=?", (path or None, project_id))


def get_export_dir(project_id: int) -> Optional[str]:
    row = db.query_one("SELECT export_dir FROM projects WHERE id=?", (project_id,))
    return (row["export_dir"] if row and "export_dir" in row.keys() else None) or None


def export_base(project_id: int) -> Optional[str]:
    """Thư mục LƯU clip của kênh: user chọn -> dùng; chưa chọn -> mặc định clips/."""
    d = get_export_dir(project_id)
    if d:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            return d
        except OSError:
            pass
    return clips_dir(project_id)


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


def delete_video(video_id: int) -> None:
    """
    Xóa 1 video khỏi project: xóa file clip đã xuất + file audio tạm, rồi xóa
    dòng DB (cascade xóa analysis/clips/jobs liên quan).
    """
    proj = db.query_one("SELECT project_id FROM videos WHERE id=?", (video_id,))
    # xóa file clip trên đĩa
    for c in db.query("SELECT export_path FROM clips WHERE video_id=?", (video_id,)):
        if c["export_path"]:
            try:
                Path(c["export_path"]).unlink(missing_ok=True)
            except OSError:
                pass
    # xóa audio tạm nếu còn
    if proj:
        pdir = _project_dir(proj["project_id"])
        if pdir:
            try:
                (pdir / f"audio_{video_id}.wav").unlink(missing_ok=True)
            except OSError:
                pass
    db.execute("DELETE FROM videos WHERE id=?", (video_id,))  # cascade


def delete_project(project_id: int) -> None:
    """Xóa cả project: xóa thư mục assets + dòng DB (cascade toàn bộ)."""
    pdir = _project_dir(project_id)
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))  # cascade
    if pdir and pdir.exists():
        try:
            shutil.rmtree(pdir, ignore_errors=True)
        except OSError:
            pass
