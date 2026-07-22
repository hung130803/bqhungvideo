"""🤖 DÂY CHUYỀN — bộ QUÉT thư mục trung chuyển (xem INTEGRATION.md).

Nửa "nhận hàng" của dây chuyền 2 tool: tool tải (bqhungdown) thả video mới
vào `<TRUNG_CHUYỂN>\\<Tên kênh>\\`; module này quét, lọc file ĐỨNG YÊN, chống
trùng 2 lớp (hash nội dung + sổ pipeline_files), áp hạn mức video/ngày theo
kênh, rồi trả KẾ HOẠCH (PlanItem) cho tầng chạy (B2) + BÁO CÁO chi tiết lý do
từng file bị bỏ qua (B3). Mọi hàm quét ở đây KHÔNG side-effect lên file —
chỉ đọc; ghi sổ do tầng chạy gọi (take_file/mark_done/mark_error).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from app.database.db import db

# Đuôi video hoàn chỉnh chấp nhận (khớp INTEGRATION.md mục 2)
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
# Đuôi file TẠM của trình tải (đang tải dở) — tuyệt đối không đụng
TMP_SUFFIXES = (".part", ".ytdl", ".tmp", ".crdownload", ".aria2", ".frag")
# File phải "đứng yên" ít nhất chừng này giây (mtime) mới được coi là tải xong
STABLE_AGE_SEC = 30
# Thư mục chứa file lỗi (INTEGRATION.md mục 4)
ERR_DIRNAME = "_Loi"


# ---------------------------------------------------------------- quét file --
def is_tmp_file(name: str) -> bool:
    """File tạm/đang tải dở của trình tải (kể cả mảnh .f140.mp4 của yt-dlp)?
    Hàm thuần."""
    low = name.lower()
    if low.endswith(TMP_SUFFIXES):
        return True
    # mảnh định dạng yt-dlp: name.f140.m4a / name.f313.webm
    parts = low.rsplit(".", 2)
    return len(parts) == 3 and parts[1].startswith("f") and parts[1][1:].isdigit()


def is_stable(path: Path, now: float | None = None,
              min_age: float = STABLE_AGE_SEC) -> bool:
    """File đã "ĐỨNG YÊN" chưa: không phải file tạm + có dung lượng + mtime
    cách hiện tại >= min_age giây (Windows cập nhật mtime khi đang ghi ->
    mtime cũ = không ai ghi nữa = tải xong)."""
    if is_tmp_file(path.name):
        return False
    try:
        st = path.stat()
    except OSError:
        return False
    if st.st_size <= 0:
        return False
    now = time.time() if now is None else now
    return (now - st.st_mtime) >= min_age


def scan_dir(d: Path, now: float | None = None) -> tuple[list[Path], list[Path]]:
    """Liệt kê video trong 1 thư mục kênh -> (sẵn_sàng, đang_dở).

    sẵn_sàng: file video hoàn chỉnh + đứng yên, sort mtime TĂNG (đến trước
    làm trước — INTEGRATION.md mục 5). đang_dở: video chưa ổn định (đang
    tải) để báo cáo "còn N file đang tải"."""
    ready: list[Path] = []
    busy: list[Path] = []
    now = time.time() if now is None else now
    try:
        entries = list(d.iterdir())
    except OSError:
        return [], []
    for p in entries:
        if not p.is_file() or p.suffix.lower() not in VIDEO_EXTS:
            continue
        if is_tmp_file(p.name):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        old = (now - st.st_mtime) >= STABLE_AGE_SEC
        if st.st_size > 0 and old:
            ready.append(p)                 # hoàn chỉnh + đứng yên
        elif st.st_size == 0 and old:
            continue                        # RÁC 0-byte cũ (tải đứt) — bỏ qua,
                                            # không phải "đang tải"
        else:
            busy.append(p)                  # đang tải dở (mtime/size còn động)
    ready.sort(key=lambda p: p.stat().st_mtime)
    return ready, busy


# ------------------------------------------------------------------- sổ DB --
def taken_today(project_id: int) -> int:
    """Số video kênh này ĐÃ NHẬN hôm nay (giờ máy) — áp hạn mức pipe_daily.
    Tính cả taken/done/error (video lỗi vẫn tốn suất — tránh vòng lặp lỗi
    ngốn cả thư mục trong 1 ngày); 'dup' KHÔNG tính (bỏ qua không tốn suất)."""
    r = db.query_one(
        "SELECT COUNT(*) AS n FROM pipeline_files WHERE project_id=? "
        "AND status IN ('taken','done','error') "
        "AND date(taken_at, 'localtime') = date('now', 'localtime')",
        (project_id,))
    return int(r["n"] if r else 0)


def seen_before(project_id: int, file_hash: str) -> dict | None:
    """File hash này kênh này từng xử lý chưa? -> dòng sổ cũ hoặc None."""
    r = db.query_one(
        "SELECT id, status, file_name, date(taken_at) AS d FROM pipeline_files "
        "WHERE project_id=? AND file_hash=? AND status IN ('taken','done') "
        "ORDER BY id DESC LIMIT 1", (project_id, file_hash))
    return dict(r) if r else None


def take_file(project_id: int, file_name: str, file_hash: str) -> int:
    """Ghi sổ NHẬN file (status='taken') -> id dòng sổ."""
    return db.insert(
        "INSERT INTO pipeline_files(project_id, file_name, file_hash, status) "
        "VALUES(?,?,?, 'taken')", (project_id, file_name, file_hash))


def mark_dup(project_id: int, file_name: str, file_hash: str, note: str) -> None:
    db.execute(
        "INSERT INTO pipeline_files(project_id, file_name, file_hash, status, "
        "note, done_at) VALUES(?,?,?, 'dup', ?, datetime('now'))",
        (project_id, file_name, file_hash, note))


def mark_done(entry_id: int, video_id: int | None = None,
              note: str = "") -> None:
    db.execute(
        "UPDATE pipeline_files SET status='done', video_id=?, note=?, "
        "done_at=datetime('now') WHERE id=?", (video_id, note, entry_id))


def mark_error(entry_id: int, note: str) -> None:
    db.execute(
        "UPDATE pipeline_files SET status='error', note=?, "
        "done_at=datetime('now') WHERE id=?", (note[:500], entry_id))


def last_intake_at(project_id: int) -> str | None:
    """Lần cuối kênh NHẬN được file (cảnh báo nguồn cạn — mục 7)."""
    r = db.query_one(
        "SELECT MAX(taken_at) AS t FROM pipeline_files "
        "WHERE project_id=? AND status IN ('taken','done')", (project_id,))
    return r["t"] if r and r["t"] else None


# ------------------------------------------------------------------ kế hoạch --
@dataclass
class PlanItem:
    """1 dòng kế hoạch/báo cáo cho 1 kênh sau khi quét."""
    project_id: int
    name: str
    src_dir: str
    files: list = field(default_factory=list)      # [Path] sẽ xử lý lần này
    skips: list = field(default_factory=list)      # [(tên_file, lý_do)]
    busy: int = 0                                  # file đang tải dở
    note: str = ""                                 # lý do kênh bị bỏ qua hẳn


def resolve_src_dir(root: str, name: str, pipe_src: str | None) -> Path:
    """Thư mục trung chuyển của kênh: pipe_src riêng nếu đặt, không thì
    <gốc>\\<Tên kênh> (INTEGRATION.md mục 1)."""
    s = (pipe_src or "").strip()
    return Path(s) if s else Path(root) / name


def plan_channel(project_id: int, name: str, root: str,
                 pipe_src: str | None, pipe_daily: int,
                 now: float | None = None,
                 hash_fn=None) -> PlanItem:
    """QUÉT 1 kênh -> PlanItem: chọn tối đa (pipe_daily - đã_nhận_hôm_nay)
    file sẵn sàng, cũ nhất trước; phần còn lại ghi lý do vào skips.
    KHÔNG side-effect file; chỉ đọc sổ. hash_fn để test cắm hash giả."""
    from app.services import _file_hash
    hash_fn = hash_fn or _file_hash
    d = resolve_src_dir(root, name, pipe_src)
    it = PlanItem(project_id=project_id, name=name, src_dir=str(d))
    if not d.is_dir():
        it.note = "thư mục trung chuyển chưa tồn tại"
        return it
    ready, busy = scan_dir(d, now)
    it.busy = len(busy)
    quota = max(0, int(pipe_daily or 1) - taken_today(project_id))
    if quota <= 0 and ready:
        it.note = "hôm nay đã đủ hạn mức — file chờ ngày mai"
    for p in ready:
        if len(it.files) >= quota:
            if quota > 0:
                it.skips.append((p.name, "quá hạn mức hôm nay — chờ ngày mai"))
            continue
        try:
            fh = hash_fn(str(p))
        except OSError as e:
            it.skips.append((p.name, f"không đọc được file: {e}"))
            continue
        old = seen_before(project_id, fh)
        if old:
            mark_dup(project_id, p.name, fh,
                     f"trùng với '{old['file_name']}' đã làm ngày {old['d']}")
            it.skips.append(
                (p.name, f"TRÙNG video đã làm ngày {old['d']} — bỏ qua"))
            continue
        it.files.append(p)
    return it


def plan_run(root: str, channels: list, now: float | None = None,
             hash_fn=None) -> list[PlanItem]:
    """Quét TẤT CẢ kênh bật dây chuyền -> danh sách PlanItem (cả kênh bị bỏ
    qua, để báo cáo đầy đủ). `channels`: dòng projects (id, name, pipe_on,
    pipe_src, pipe_daily)."""
    out: list[PlanItem] = []
    for c in channels:
        if not c["pipe_on"]:
            continue
        out.append(plan_channel(int(c["id"]), c["name"], root,
                                c["pipe_src"], int(c["pipe_daily"] or 1),
                                now=now, hash_fn=hash_fn))
    return out


def err_dir_for(src_dir: Path) -> Path:
    """Thư mục _Loi/<Kênh> cạnh gốc trung chuyển (INTEGRATION.md mục 4):
    <gốc>\\_Loi\\<Tên kênh> — gốc = cha của thư mục kênh."""
    return src_dir.parent / ERR_DIRNAME / src_dir.name


def quarantine(path: Path) -> Path | None:
    """Chuyển file hỏng/lỗi sang thư mục _Loi (không xóa oan). Trả đường dẫn
    mới hoặc None nếu chuyển thất bại (file kẹt) — caller ghi báo cáo."""
    try:
        dst_dir = err_dir_for(path.parent)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / path.name
        i = 1
        while dst.exists():
            dst = dst_dir / f"{path.stem}_{i}{path.suffix}"
            i += 1
        path.rename(dst)
        return dst
    except OSError:
        return None
