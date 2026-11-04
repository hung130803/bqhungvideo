"""Resume saved export jobs without regenerating music, overlays or recipes."""
from app.database import db

def saved_job(clip_id):
    rows=db.query("SELECT id,status,result FROM jobs WHERE type='m1_export_clip' AND json_extract(payload,'$.clip_id')=? ORDER BY CASE WHEN status='running' THEN 0 WHEN status='pending' THEN 1 ELSE 2 END,id DESC",(int(clip_id),))
    for row in rows:
        result=db.loads(row['result'],{}) or {}
        if isinstance(result,dict) and result.get('superseded_by'):continue
        return int(row['id'])
    return None

def same_destination(a,b):
    import os
    norm=lambda x:os.path.normcase(os.path.abspath(str(x or '.')))
    return (a.get('clip_id')==b.get('clip_id') and
            norm(a.get('out_dir'))==norm(b.get('out_dir')) and
            a.get('out_name')==b.get('out_name') and
            a.get('part_no')==b.get('part_no') and
            bool(a.get('flat'))==bool(b.get('flat')))


def _ban_da_xong(pending_row, connection=None):
    """Job xuất ĐANG CHỜ này có phải bản TRÙNG của một job đã xuất XONG sau khi
    nó được xếp không? -> id job đã xong, hoặc None.

    LỖI THẬT (sổ của anh Hùng 25-26/10/2026): app mở lại sau khi tắt xếp LẠI
    lệnh xuất cho video dở trong lúc lệnh cũ còn chờ (bản cũ chưa có chốt
    `same_destination` ở `enqueue`). Lệnh cũ chạy xong đủ Part, lệnh mới vẫn
    nằm 'pending' hàng giờ sau đuôi hàng đợi -> dây chuyền thấy Part "chưa
    xong" nên KHÔNG dọn video gốc (7 video còn nguyên trong thư mục), và tới
    lượt thì xuất LẠI đúng Part đó lần nữa (phí ~1 giờ máy / video).
    Điều kiện bỏ: cùng clip, cùng nơi lưu/tên/Part, job kia 'done' và xong
    SAU lúc job này được xếp, và file Part còn trên đĩa. Bấm "Xuất lại" có chủ
    ý KHÔNG dính: lúc bấm, lệnh cũ (nếu đang chờ) được dùng lại, còn lệnh cũ
    đã xong thì xong TRƯỚC lúc bấm."""
    import os
    q = (connection.execute if connection is not None else db.query)
    try:
        payload = db.loads(pending_row['payload'], {}) or {}
        cid = int(payload.get('clip_id') or 0)
    except (TypeError, ValueError, AttributeError):
        return None
    if not cid or not pending_row['created_at']:
        return None
    rows = q("SELECT id,payload,finished_at,result FROM jobs WHERE type='m1_export_clip' "
             "AND status='done' AND json_extract(payload,'$.clip_id')=? AND id<>? "
             "AND finished_at>=? ORDER BY finished_at DESC",
             (cid, int(pending_row['id']), str(pending_row['created_at'])))
    for row in (rows.fetchall() if hasattr(rows, 'fetchall') else rows):
        other = db.loads(row['payload'], {}) or {}
        if not same_destination(other, payload):
            continue
        res = db.loads(row['result'], {}) or {}
        path = (res.get('export_path') if isinstance(res, dict) else None) or ''
        if not path:
            path = os.path.join(str(payload.get('out_dir') or ''),
                                str(payload.get('out_name') or ''))
        try:
            if path and os.path.isfile(path) and os.path.getsize(path) > 0:
                return int(row['id']), path
        except OSError:
            continue
    return None


def bo_xuat_trung_da_xong() -> int:
    """Quét MỌI job xuất đang chờ, bỏ bản trùng của job đã xuất xong (xem
    `_ban_da_xong`). Trả số job đã bỏ. An toàn chạy nhiều lần."""
    import json
    n = 0
    try:
        rows = db.query("SELECT id,payload,created_at FROM jobs WHERE "
                        "type='m1_export_clip' AND status='pending'")
    except Exception:  # noqa: BLE001
        return 0
    for row in rows:
        hit = _ban_da_xong(row)
        if not hit:
            continue
        done_id, path = hit
        cur = db.execute(
            "UPDATE jobs SET status='skipped', finished_at=datetime('now'), "
            "message=?, result=? WHERE id=? AND status='pending'",
            (f"Bỏ lượt xuất trùng: Part đã xuất xong ở việc #{done_id}",
             json.dumps({"superseded_by": done_id, "export_path": path,
                         "reason": "duplicate_after_done"}), int(row['id'])))
        try:
            n += int(cur.rowcount or 0)
        except Exception:  # noqa: BLE001
            n += 1
    return n
