"""Ảnh chụp trạng thái từng video cho bảng hàng loạt, không sửa job hay file."""
from collections import defaultdict
import json
from pathlib import Path

from app.database.db import db

LIMIT = 2000
ANALYSIS = {'auto', 'auto_mixed', 'auto_recap', 'analyze', 'm1_highlights', 'm1_mixed_cut'}


_JSON_SQL = None   # None = chưa thử; True/False = SQLite có/không có hàm JSON


def _jobs_rows(marks, batch):
    """Job của một lô video. 26/10/2026: KHÔNG kéo cả cột payload (~1 KB/job,
    bảng này làm mới mỗi 2,5 s) rồi json.loads từng job ở luồng giao diện —
    SQLite tự rút clip_id (json_extract, chỉ cho job xuất có JSON hợp lệ).
    SQLite thiếu hàm JSON -> lùi về cách cũ."""
    global _JSON_SQL
    if _JSON_SQL is not False:
        try:
            rows = db.query(
                "SELECT id,video_id,type,status,message,error,progress,"
                "CASE WHEN type='m1_export_clip' AND json_valid(payload) "
                "THEN json_extract(payload,'$.clip_id') END AS clip_id "
                f"FROM jobs WHERE video_id IN ({marks}) ORDER BY id DESC", batch)
            _JSON_SQL = True
            return rows
        except Exception:  # noqa: BLE001 - SQLite cũ không có JSON1
            if _JSON_SQL:
                raise
            _JSON_SQL = False
    return db.query(f"SELECT id,video_id,type,status,message,error,payload,progress FROM jobs "
                    f"WHERE video_id IN ({marks}) ORDER BY id DESC", batch)


def signature(project_id):
    """CHỮ KÝ RẺ của mọi thứ snapshot(project_id) hiển thị — nhịp 2,5 s của
    bảng so chữ ký trước, giống nhau thì khỏi dựng lại cả ảnh chụp
    (26/10/2026). Chỉ đọc chỉ mục; đổi trạng thái/tiến độ/tin nhắn job, clip
    xuất xong, sổ dây chuyền... đều làm đổi chữ ký."""
    pid = int(project_id)
    r = db.query_one(
        "SELECT "
        "(SELECT COUNT(*)||':'||IFNULL(MAX(id),0) FROM videos WHERE project_id=?) AS v,"
        "(SELECT COUNT(*)||':'||IFNULL(MAX(id),0)||':'||TOTAL(id*(CASE status "
        "  WHEN 'running' THEN 1 WHEN 'pending' THEN 2 WHEN 'done' THEN 3 "
        "  WHEN 'failed' THEN 5 WHEN 'canceled' THEN 7 ELSE 11 END)) "
        "  FROM jobs WHERE project_id=?) AS j,"
        "(SELECT group_concat(id||'|'||IFNULL(message,'')||'|'||IFNULL(progress,0),'~') "
        "  FROM jobs WHERE project_id=? AND status='running') AS jr,"
        "(SELECT COUNT(*)||':'||TOTAL(c.id*(c.status='exported'))||':'||"
        "  TOTAL(c.id*(c.export_path IS NOT NULL)) FROM clips c "
        "  JOIN videos v ON v.id=c.video_id "
        "  WHERE v.project_id=? AND c.status<>'archived') AS c,"
        "(SELECT COUNT(*)||':'||IFNULL(MAX(id),0)||':'||TOTAL(id*length(status||IFNULL(note,''))) "
        "  FROM pipeline_files WHERE project_id=?) AS p",
        (pid, pid, pid, pid, pid))
    return tuple(r) if r else None


def snapshot(project_id=None):
    # The channel view must include older videos too. Keep the legacy bound
    # only for callers explicitly requesting the global overview.
    where = 'WHERE v.project_id=? ' if project_id is not None else ''
    params = (int(project_id),) if project_id is not None else ()
    total = int(db.query_one('SELECT COUNT(*) AS n FROM videos v '+where, params)['n'])
    videos = db.query(
        "SELECT v.id,v.project_id,v.src_path,v.imported_at,p.name AS channel,p.grp,"
        "MAX(CASE WHEN j.status IN ('running','pending') THEN 1 ELSE 0 END) AS active,"
        "MAX(j.id) AS last_job FROM videos v JOIN projects p ON p.id=v.project_id "
        "LEFT JOIN jobs j ON j.video_id=v.id "+where+"GROUP BY v.id "
        "ORDER BY active DESC,COALESCE(last_job,0) DESC,v.id DESC"+
        (" LIMIT ?" if project_id is None else ''), params if project_id is not None else (LIMIT,))
    ids = [v['id'] for v in videos]
    jobs, clips, pipeline = defaultdict(list), defaultdict(list), {}
    for start in range(0,len(ids),400):
        batch = ids[start:start+400]
        marks = ','.join('?' for _ in batch)
        for r in _jobs_rows(marks, batch):
            jobs[r['video_id']].append(dict(r))
        for r in db.query(f"SELECT id,video_id,status,export_path FROM clips WHERE video_id IN ({marks}) "
                          "AND status<>'archived'", batch):
            clips[r['video_id']].append(dict(r))
        for r in db.query(f"SELECT id,video_id,status,note FROM pipeline_files WHERE video_id IN ({marks}) "
                          "ORDER BY id DESC", batch):
            pipeline.setdefault(r['video_id'],dict(r))
    output = []
    for video in videos:
        vid = video['id']
        current = clips[vid]
        clip_ids = {c['id'] for c in current}
        exported = sum(c['status']=='exported' and bool(c['export_path']) for c in current)
        latest = {}
        active = [j for j in jobs[vid] if j['status'] in ('running','pending')]
        for j in jobs[vid]:
            if j['type']=='m1_export_clip':
                try:
                    if 'clip_id' in j:
                        cid = int(j['clip_id'] or 0)
                    else:
                        cid = int((json.loads(j.pop('payload', None) or '{}') or {}).get('clip_id') or 0)
                except (ValueError,TypeError,AttributeError):
                    cid = 0
                if cid and cid not in clip_ids:
                    continue
                key = ('export',cid or -j['id'])
            elif j['type'] in ANALYSIS:
                key = ('analysis',0)
            else:
                key = (j['type'],0)
            latest.setdefault(key,j)
        failures = [j for j in latest.values() if j['status']=='failed']
        canceled = [j for j in latest.values() if j['status'] in ('canceled','skipped')]
        running = [j for j in active if j['status']=='running']
        export_running = [j for j in running if j['type']=='m1_export_clip']
        if running:
            state='running'
            stage='Đang xuất Part' if export_running else 'Đang phân tích/xử lý'
            item=(export_running or running)[0]
            detail=item['message'] or stage
        elif active:
            state,stage='pending','Đang chờ'
            detail=f"{len(active)} việc chờ đến lượt; chưa hoàn tất video"
        elif failures:
            state,stage='failed','Có lỗi cần xử lý'
            detail=failures[0]['error'] or failures[0]['message'] or 'Mở chi tiết công việc để xem lỗi'
        elif canceled:
            state,stage='canceled','Đã hủy/bỏ qua'
            detail='Có công việc đã hủy; không tự coi là video hoàn tất'
        elif current and exported==len(current):
            state,stage='done','Đã xuất đủ Part'
            detail='Các Part được ghi nhận đã xuất thành công'
        elif current:
            state,stage='ready','Có clip chưa xuất'
            detail='Có thể đang chờ tự xuất hoặc cần duyệt và bấm Xuất'
        else:
            state,stage='idle','Chưa có clip'
            detail='Chọn video để xem hoặc tạo clip'
        p = pipeline.get(vid)
        source='Ngoài Dây chuyền'
        if p:
            note=p['note'] or ''
            if '[GỐC KẸT]' in note:
                source='Gốc chưa dọn'
            elif '[GỐC ĐÃ CHUYỂN THÙNG RÁC]' in note:
                source='Đã vào Thùng rác'
            elif p['status']=='taken':
                source='Đang được Dây chuyền theo dõi'
            elif p['status']=='error':
                source='Cần kiểm tra gốc'
            else:
                source='Xem báo cáo Dây chuyền'
        retry = [j for j in failures+canceled if j['status']!='skipped']
        # Re-analysis can archive/replace the clips. Never requeue exports
        # from the old analysis concurrently with that operation.
        analysis_retry = [j for j in retry if j['type'] in ANALYSIS]
        retry = [] if active else (analysis_retry or retry)
        output.append(dict(id=vid,pid=video['project_id'],channel=video['channel'],
            group=video['grp'] or 'Chưa phân nhóm',video=Path(video['src_path']).name,
            path=video['src_path'],state=state,stage=stage,detail=detail,
            parts=f'{exported}/{len(current)}',source=source,
            imported_at=video['imported_at'] or '',last_job=video['last_job'] or 0,
            export_paths=[c['export_path'] for c in current if c['status']=='exported' and c['export_path']],
            job_ids=[j['id'] for j in active],
            retry_ids=[j['id'] for j in retry],
            jobs=jobs[vid],note=(p['note'] or '') if p else ''))
    return output,total
