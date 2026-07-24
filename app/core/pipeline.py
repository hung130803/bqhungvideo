"""🤖 DÂY CHUYỀN — bộ QUÉT thư mục trung chuyển (xem INTEGRATION.md).

Nửa "nhận hàng" của dây chuyền 2 tool: tool tải (bqhungdown) thả video mới
vào `<TRUNG_CHUYỂN>\\<Tên kênh>\\`; module này quét, lọc file ĐỨNG YÊN, chống
trùng 2 lớp (hash nội dung + sổ pipeline_files), áp hạn mức video/ngày theo
kênh, rồi trả KẾ HOẠCH (PlanItem) cho tầng chạy (B2) + BÁO CÁO chi tiết lý do
từng file bị bỏ qua (B3). Mọi hàm quét ở đây KHÔNG side-effect lên file —
chỉ đọc; ghi sổ do tầng chạy gọi (take_file/mark_done/mark_error).
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.database.db import db

# Đuôi video hoàn chỉnh chấp nhận (khớp INTEGRATION.md mục 2)
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
# Clip do tool XUẤT ra tên "Part 1 …", "Part 2 …" — scan bỏ qua để không
# cắt lại (xuất Part thẳng vào thư mục kênh, chung với video gốc).
_PART_RE = re.compile(r"(?i)^part\s*\d")
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
        # BỎ QUA clip DO CHÍNH TOOL XUẤT (tên "Part N …") — xuất Part thẳng
        # vào thư mục kênh, nếu quét lại sẽ cắt vòng vô hạn. yt-dlp/nguồn
        # gần như không đặt tên video gốc bắt đầu bằng "Part <số>".
        if _PART_RE.match(p.name):
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


def mark_bad(project_id: int, file_name: str, note: str) -> None:
    """File HỎNG từ đầu (ffprobe không đọc được) — ghi sổ 'bad', KHÔNG tốn
    suất ngày (taken_today không đếm 'bad'; file đã quarantine khỏi thư mục
    nên không lặp lại được)."""
    db.execute(
        "INSERT INTO pipeline_files(project_id, file_name, status, note, "
        "done_at) VALUES(?,?, 'bad', ?, datetime('now'))",
        (project_id, file_name, note[:500]))


def expire_stale_taken(hours: int = 12) -> int:
    """Entry 'taken' treo quá `hours` giờ (app tắt giữa chừng/kẹt) -> chuyển
    'error' để file (nếu còn trong thư mục) được NHẬN LẠI ở lần chạy sau.
    Trả số entry đã chuyển."""
    cur = db.execute(
        "UPDATE pipeline_files SET status='error', "
        "note=COALESCE(note,'') || ' [gián đoạn - app tắt giữa chừng?]', "
        "done_at=datetime('now') "
        "WHERE status='taken' AND taken_at < datetime('now', ?)",
        (f"-{int(hours)} hours",))
    try:
        return cur.rowcount or 0
    except Exception:  # noqa: BLE001
        return 0


def reset_channel(project_id: int) -> int:
    """CHO PHÉP LÀM LẠI kênh: xoá sổ đã-xử-lý (pipeline_files) của kênh →
    mọi video (kể cả video đã làm mà user bỏ lại vào folder) được NHẬN LẠI ở
    lần chạy sau. KHÔNG đụng file trên đĩa. Trả số dòng sổ đã xoá."""
    cur = db.execute("DELETE FROM pipeline_files WHERE project_id=?",
                     (project_id,))
    try:
        return cur.rowcount or 0
    except Exception:  # noqa: BLE001
        return 0


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
    files: list = field(default_factory=list)      # [Path] ỨNG VIÊN theo thứ tự
                                                   # (cũ trước) — CHƯA cắt theo
                                                   # hạn mức; runner đếm số nhận
                                                   # THÀNH CÔNG so với `quota`
                                                   # (file hỏng không nuốt suất)
    quota: int = 0                                 # còn được nhận mấy video hôm nay
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
                 hash_fn=None, export_dir: str | None = None) -> PlanItem:
    """QUÉT 1 kênh -> PlanItem. Thư mục LẤY video (ưu tiên):
    pipe_src (chọn riêng) > export_dir ("Thư mục lưu" của kênh — 1 thư mục
    dùng chung input+output theo yêu cầu) > <root>\\<Tên kênh>. Clip cắt xong
    xuất vào thư mục con 'Clip' bên trong nên KHÔNG bị quét lại (scan_dir chỉ
    đọc tầng trên). KHÔNG side-effect file; chỉ đọc sổ."""
    from app.services import _file_hash
    hash_fn = hash_fn or _file_hash
    # export_dir đóng vai NGUỒN nếu không đặt pipe_src riêng (mô hình 1 thư mục).
    src_override = (pipe_src or "").strip() or (export_dir or "").strip()
    it = PlanItem(project_id=project_id, name=name, src_dir="")
    if not src_override and not (root or "").strip():
        it.note = "CHƯA đặt Thư mục lưu cho kênh (đặt ở phần Kênh)"
        return it
    d = resolve_src_dir(root, name, src_override)
    it.src_dir = str(d)
    if not d.is_dir():
        it.note = "thư mục lấy video chưa tồn tại"
        return it
    ready, busy = scan_dir(d, now)
    it.busy = len(busy)
    # KHÔNG có video sẵn sàng + KHÔNG có file đang tải dở -> báo RÕ lý do
    # (nếu không, _pipe_run im lặng, user tưởng "chạy không lên gì"). Case hay
    # gặp nhất: video gốc đã cắt xong & bị xoá, thư mục chỉ còn file Part.
    if not ready and not busy:
        it.note = ("không có video mới để cắt — thư mục trống, hoặc video gốc "
                   "đã cắt xong & bị xoá (chỉ còn file Part đã xuất)")
        return it
    # CẮT HẾT: có bao nhiêu video sẵn sàng trong thư mục thì xử lý HẾT bấy
    # nhiêu — khớp 100% cột "Chờ cắt" trên UI (kênh 2 video cắt 2, 3 cắt 3).
    # UI đã BỎ cột "video/ngày" nên KHÔNG áp hạn mức nữa. (pipe_daily cũ trong
    # DB mặc định 1 từng khiến chỉ cắt 1 video/ngày — đó là lý do trước đây
    # thấy thiếu; nay bỏ hẳn giới hạn.) Chỉ cap khi ai đó CỐ đặt >=2 (không có
    # UI nên gần như không xảy ra).
    daily = int(pipe_daily or 0)
    if daily >= 2:
        it.quota = max(0, daily - taken_today(project_id))
        if it.quota <= 0 and ready:
            it.note = "hôm nay đã đủ hạn mức — file chờ ngày mai"
            return it
    else:
        it.quota = len(ready)  # 0/1 (mặc định) = KHÔNG giới hạn — làm hết folder
    for p in ready:
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
        it.files.append(p)          # ứng viên — runner áp quota khi nhận
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
        # export_dir có thể vắng trong hàng query cũ → lấy an toàn.
        try:
            ed = c["export_dir"]
        except (KeyError, IndexError):
            ed = None
        out.append(plan_channel(int(c["id"]), c["name"], root,
                                c["pipe_src"], int(c["pipe_daily"] or 1),
                                now=now, hash_fn=hash_fn, export_dir=ed))
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


# ------------------------------------------------------ THÙNG RÁC theo ngày --
# Thay vì XOÁ THẲNG video gốc sau khi cắt xong, chuyển vào thùng rác của user
# (tự chọn thư mục) theo cấu trúc <thùng rác>/<YYYY-MM-DD>/<Tên kênh>/<file>
# để có thể KHÔI PHỤC về đúng thư mục kênh nếu phân tích lỗi. Không cần DB —
# đường dẫn tự mã hoá ngày + kênh; khôi phục = chuyển về resolve_src_dir(kênh).
RECYCLE_DIRNAME = "_DaXoa"


def _today_str() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def _unique_in(dst_dir: Path, name: str) -> Path:
    """Đường dẫn KHÔNG đè file cũ: thêm _1, _2… nếu trùng tên."""
    stem, suffix = Path(name).stem, Path(name).suffix
    dst = dst_dir / name
    i = 1
    while dst.exists():
        dst = dst_dir / f"{stem}_{i}{suffix}"
        i += 1
    return dst


def _move_with_retry(src: Path, dst: Path, tries: int = 5) -> bool:
    """Chuyển file, THỬ LẠI vài lần: trên Windows ffmpeg/handle vừa xong còn
    giữ khoá file chốc lát → rename ngay bị 'file đang dùng'. Chờ tăng dần."""
    for k in range(tries):
        try:
            src.rename(dst)
            return True
        except OSError:
            # khác ổ đĩa → rename thất bại vĩnh viễn: thử copy+xoá
            try:
                import shutil
                shutil.move(str(src), str(dst))
                return True
            except OSError:
                pass
            time.sleep(0.4 * (k + 1))
    return False


def _delete_with_retry(path: Path, tries: int = 5) -> bool:
    """Xoá file, THỬ LẠI vài lần (chống file kẹt do handle chưa nhả)."""
    for k in range(tries):
        try:
            path.unlink(missing_ok=True)
            return True
        except OSError:
            time.sleep(0.4 * (k + 1))
    return not path.exists()


def recycle_source(path: Path, channel: str, recycle_root: str,
                   day: str | None = None) -> Path | None:
    """Chuyển video gốc (đã cắt xong) vào THÙNG RÁC theo ngày. Trả đường dẫn
    mới, hoặc None nếu thất bại (caller sẽ báo 'file kẹt')."""
    root = (recycle_root or "").strip()
    if not root:
        return None
    try:
        dst_dir = Path(root) / (day or _today_str()) / (channel or "_")
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = _unique_in(dst_dir, path.name)
        return dst if _move_with_retry(path, dst) else None
    except OSError:
        return None


def delete_or_recycle(path: Path, channel: str,
                      recycle_root: str) -> tuple[str, Path | None]:
    """Sau khi cắt xong: có THÙNG RÁC (recycle_root) -> CHUYỂN VÀO đó theo
    ngày (khôi phục được); không thì XOÁ HẲN (đều thử-lại chống file kẹt).
    Trả ('recycled'|'deleted'|'stuck', đường_dẫn_mới_hoặc_None)."""
    if (recycle_root or "").strip():
        dst = recycle_source(path, channel, recycle_root)
        if dst:
            return ("recycled", dst)
        # thùng rác lỗi (khác ổ/kẹt) -> KHÔNG xoá hẳn để khỏi mất video; báo kẹt
        return ("stuck", None)
    return ("deleted", None) if _delete_with_retry(path) else ("stuck", None)


def list_recycled_days(recycle_root: str) -> list[str]:
    """Danh sách NGÀY (YYYY-MM-DD) có video trong thùng rác, mới nhất trước."""
    root = (recycle_root or "").strip()
    if not root or not Path(root).is_dir():
        return []
    days = [p.name for p in Path(root).iterdir()
            if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name)]
    return sorted(days, reverse=True)


def list_recycled(recycle_root: str, day: str) -> list[dict]:
    """Video trong thùng rác của 1 ngày: [{channel, name, path, size}]."""
    root = (recycle_root or "").strip()
    out: list[dict] = []
    base = Path(root) / day if root else None
    if not base or not base.is_dir():
        return out
    for chdir in sorted(base.iterdir()):
        if not chdir.is_dir():
            continue
        for f in sorted(chdir.iterdir()):
            if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
                try:
                    sz = f.stat().st_size
                except OSError:
                    sz = 0
                out.append({"channel": chdir.name, "name": f.name,
                            "path": str(f), "size": sz})
    return out


def restore_recycled(recycled_path: str, dest_dir: str) -> Path | None:
    """KHÔI PHỤC 1 video từ thùng rác về thư mục kênh (dest_dir). Trả đường
    dẫn mới, hoặc None nếu lỗi. mtime đặt về HIỆN TẠI để scan_dir coi là mới
    (ổn định) và cắt lại được ngay."""
    try:
        src = Path(recycled_path)
        dd = Path(dest_dir)
        dd.mkdir(parents=True, exist_ok=True)
        dst = _unique_in(dd, src.name)
        if not _move_with_retry(src, dst):
            return None
        now = time.time()
        try:
            os.utime(dst, (now, now))
        except OSError:
            pass
        return dst
    except OSError:
        return None
