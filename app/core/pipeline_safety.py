"""Kiểm tra lại dữ liệu bền vững trước khi hồi phục hoặc dọn video gốc."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from app.database.db import db

PARTS_MARK = ' [PART_IDS:'


def parts_note(ids) -> str:
    return PARTS_MARK + ','.join(str(i) for i in sorted(ids)) + ']'


def note_parts(note: str) -> set[int] | None:
    match = re.search(r'\[PART_IDS:([0-9,]+)\]', note or '')
    return {int(i) for i in match[1].split(',')} if match else None


def latest_export_states(video_id: int) -> dict:
    """Trạng thái lần xuất mới nhất của từng clip ĐANG dùng.

    Clip của lần phân tích cũ đã archived không chặn lần mới. Retry trên
    cùng job hoặc job mới cho cùng clip thay thế trạng thái hủy trước đó.
    Job đời cũ thiếu clip_id được giữ riêng để không tự bỏ qua lệnh hủy.
    """
    active = {r['id'] for r in db.query(
        "SELECT id FROM clips WHERE video_id=? AND status<>'archived'", (video_id,))}
    result = {}
    for row in db.query(
            "SELECT id, payload, status FROM jobs WHERE video_id=? "
            "AND type='m1_export_clip' ORDER BY id DESC", (video_id,)):
        try:
            cid = int((json.loads(row['payload'] or '{}') or {}).get('clip_id') or 0)
        except (ValueError, TypeError, AttributeError):
            cid = 0
        if cid and cid not in active:
            continue
        key = cid or -row['id']
        result.setdefault(key, row['status'])
    return result


def source_problem(entry_id: int, video_id: int, path: Path) -> str:
    """Đối chiếu đường dẫn và fingerprint lúc nhận; lỗi đọc cũng phải giữ gốc."""
    from app.services import _file_hash

    row = db.query_one(
        "SELECT f.file_hash, v.file_hash AS video_hash, v.src_path "
        "FROM pipeline_files f JOIN videos v ON v.id=? WHERE f.id=?",
        (video_id, entry_id))
    if not row or not row['file_hash'] or row['file_hash'] != row['video_hash']:
        return 'Thiếu hoặc lệch dấu nhận dạng video gốc; giữ nguyên để kiểm tra'
    try:
        if os.path.normcase(str(path.resolve())) != os.path.normcase(str(Path(row['src_path']).resolve())):
            return 'Đường dẫn nguồn đã đổi; không dọn file ở thư mục mới'
        before = path.stat()
        actual = _file_hash(str(path))
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            return 'Video gốc đang thay đổi; chưa được dọn'
        if actual != row['file_hash']:
            return 'Video gốc đã được thay bằng file khác cùng tên; giữ file mới'
    except OSError:
        return 'Không đọc được video gốc để xác minh; chưa được dọn'
    return ''


def parts_problem(video_id: int, expected_ids=None, old_note='') -> str:
    clips = db.query("SELECT id, export_path FROM clips WHERE video_id=? AND status<>'archived'",
                     (video_id,))
    ids = {r['id'] for r in clips}
    if expected_ids is not None and ids != set(expected_ids):
        return 'Danh sách Part đã đổi; giữ video gốc'
    old_count = re.match(r'(\d+) part', old_note or '')
    if not clips or (old_count and len(clips) != int(old_count[1])):
        return 'Chưa đủ danh sách Part; giữ video gốc'
    if any(st != 'done' for st in latest_export_states(video_id).values()):
        return 'Còn Part chưa xuất thành công hoặc đã hủy; giữ video gốc'
    try:
        if any(not r['export_path'] or not Path(r['export_path']).is_file()
               or Path(r['export_path']).stat().st_size <= 0 for r in clips):
            return 'Part bị thiếu hoặc rỗng; giữ video gốc'
    except OSError:
        return 'Không kiểm tra được file Part; giữ video gốc'
    return ''
