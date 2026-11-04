"""Giao diện không đơ khi Dây chuyền chạy (26/10/2026).

Kiểm: phần nặng (dựng lệnh xuất Part, soi ffprobe/băm lúc nhận, băm + dọn
gốc) chạy ở LUỒNG NỀN; sổ RAM chỉ đổi khi kết quả về luồng giao diện; không
bao giờ 2 lượt dựng cho cùng 1 video; truy vấn rẻ cho bảng/nhãn cho kết quả y
hệt bản cũ. Không gọi mạng, không đụng file thật của người dùng.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_ui_responsive_'))
os.environ.update(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA / 'test.db'),
                  BQ_QSETTINGS_INI=str(AREA / 'settings.ini'),
                  QT_QPA_PLATFORM='offscreen', BQ_BO_MANG='1')
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: E402,F401
import app.queue.jobs  # noqa: E402,F401
from PyQt6.QtWidgets import QApplication  # noqa: E402
from app import services  # noqa: E402
from app.core import pipeline as P  # noqa: E402
from app.database.db import db  # noqa: E402

qapp = QApplication.instance() or QApplication([])
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402


def cho(dk, giay=30.0):
    """Bơm vòng sự kiện tới khi dk() đúng (kết quả nền về qua tín hiệu)."""
    het = time.monotonic() + giay
    while time.monotonic() < het:
        qapp.processEvents()
        if dk():
            return True
        time.sleep(0.01)
    qapp.processEvents()
    return bool(dk())


class ResponsivePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = StudioPage(AppState())
        cls.page.timer.stop()
        cls.logs = []
        cls.page._pipe_log = cls.logs.append

    def _video(self, n_clip=3, name='nguon.mp4'):
        pid = services.create_project(f'Kênh nhanh {time.monotonic_ns()}', 'NhomNhanh')
        d = AREA / f'p{pid}'
        d.mkdir()
        src = d / name
        src.write_bytes(b'video goc ' * 200)
        fh = services._file_hash(str(src))
        vid = db.insert('INSERT INTO videos(project_id,src_path,file_hash,duration,width,height) '
                        'VALUES(?,?,?,?,?,?)', (pid, str(src), fh, 60, 1920, 1080))
        clips = [db.insert('INSERT INTO clips(video_id,start_sec,end_sec,title,signals,status) '
                           'VALUES(?,?,?,?,?,?)',
                           (vid, i * 10, i * 10 + 5, f'Đoạn {i}',
                            db.dumps({'llm_used': True, 'title_en': f'Moment {i}'}), 'suggested'))
                 for i in range(n_clip)]
        entry = P.take_file(pid, src.name, fh, video_id=vid)
        ctx = {'entry': entry, 'vid': vid, 'path': str(src), 'pid': pid,
               'name': 'Kênh nhanh', 'file': src.name, 'mode': 'auto'}
        return pid, vid, src, clips, entry, ctx

    def test_auto_export_prepares_in_background_once_per_video(self):
        pg = self.page
        pid, vid, src, clips, entry, ctx = self._video()
        jid = db.insert("INSERT INTO jobs(type,status,project_id,video_id,payload) "
                        "VALUES('auto','done',?,?,'{}')", (pid, vid))
        pg._pipe_by_vid[vid] = ctx
        pg._pending_export[jid] = vid
        pg._auto_tpl[jid] = pg._tpl_for_project(pid)
        goc = pg._export_prepare
        cua = threading.Event()
        luong = []

        def cham(*a, **k):
            luong.append(threading.current_thread().name)
            cua.wait(10)
            return goc(*a, **k)
        pg._export_prepare = cham
        try:
            t0 = time.perf_counter()
            pg._check_auto_export_nhip()
            self.assertLess(time.perf_counter() - t0, 0.5, 'nhịp poll phải trả về ngay')
            pg._check_auto_export_nhip()          # nhịp kế tiếp lúc còn đang dựng
            cho(lambda: bool(luong), 5)
            self.assertIn(jid, pg._pending_export, 'sổ chỉ gỡ khi kết quả về')
            self.assertIn(vid, pg._xuat_dang)
            self.assertFalse(pg._xuat_nen(vid), 'không dựng 2 lượt cho cùng 1 video')
            cua.set()
            self.assertTrue(cho(lambda: vid in pg._pipe_exports))
        finally:
            pg._export_prepare = goc
            cua.set()
        self.assertEqual(luong, ['bq-dung-part'])
        self.assertEqual(len(pg._pipe_exports[vid]['jobs']), 3)
        self.assertNotIn(jid, pg._pending_export)
        self.assertNotIn(vid, pg._xuat_dang)
        names = [db.loads(r['payload'], {}).get('out_name', '') for r in db.query(
            "SELECT payload FROM jobs WHERE video_id=? AND type='m1_export_clip' ORDER BY id", (vid,))]
        self.assertEqual([n.split(' ')[1] for n in names], ['1', '2', '3'])
        pg._pipe_exports.pop(vid, None)

    def test_sync_export_path_unchanged_for_direct_calls(self):
        pg = self.page
        pid, vid, src, clips, entry, ctx = self._video(2)
        n = pg._export_video(vid)
        self.assertEqual(n, 2)
        self.assertEqual(len(pg._last_export_jids), 2)
        self.assertEqual(pg._export_results[vid]['clips'], clips)

    def test_source_cleanup_runs_in_background_and_keeps_tracking(self):
        pg = self.page
        pid, vid, src, clips, entry, ctx = self._video(2)
        jobs = []
        for i, cid in enumerate(clips):
            part = AREA / f'p{pid}' / f'Part {i + 1}.mp4'
            part.write_bytes(b'part ' * 10)
            db.execute("UPDATE clips SET export_path=?, status='exported' WHERE id=?", (str(part), cid))
            jobs.append(db.insert("INSERT INTO jobs(type,project_id,video_id,status,payload) "
                                  "VALUES('m1_export_clip',?,?,'done',?)",
                                  (pid, vid, db.dumps({'clip_id': cid, 'part_no': i + 1}))))
        ent = {'jobs': set(jobs), 'ctx': ctx, 'clips': clips}
        pg._pipe_exports[vid] = ent
        cua = threading.Event()
        luong = []
        goc = P.delete_or_recycle

        def cham(*a, **k):
            luong.append(threading.current_thread().name)
            cua.wait(10)
            return goc(*a, **k)
        with patch.object(P, 'delete_or_recycle', side_effect=cham), \
                patch.object(pg, '_pipe_recycle_dir', return_value=str(AREA / 'rac')):
            pg._pipe_poll_exports(nen=True)
            cho(lambda: bool(luong), 5)
            self.assertIs(pg._pipe_exports.get(vid), ent, 'đang dọn vẫn phải còn trong sổ')
            pg._pipe_poll_exports(nen=True)       # nhịp sau: không dọn lần 2
            cua.set()
            self.assertTrue(cho(lambda: vid not in pg._pipe_exports))
        self.assertEqual(luong, ['bq-don-goc'])
        self.assertFalse(src.exists())
        self.assertEqual(db.query_one('SELECT status FROM pipeline_files WHERE id=?', (entry,))['status'], 'done')

    def test_intake_probe_and_hash_happen_off_ui_thread(self):
        pg = self.page
        grp = f'NhomNhan{time.monotonic_ns()}'
        pid = services.create_project('Kênh nhận nền', grp)
        d = AREA / f'nhan{pid}'
        d.mkdir()
        tiny = AREA / 'tiny.mp4'
        if not tiny.exists():
            from config import settings as _st
            subprocess.run([_st.FFMPEG_PATH, '-y', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=160x90:rate=10', '-f', 'lavfi', '-i', 'sine',
                            '-t', '2', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac',
                            str(tiny)], check=True, timeout=60)
        old = time.time() - 300
        for i in range(3):
            p = d / f'v{i}.mp4'
            p.write_bytes(tiny.read_bytes() + bytes([i]) * 32)
            os.utime(p, (old, old))
            P.observe_source(p, now=time.monotonic() - 30)
        db.execute('UPDATE projects SET pipe_on=1, pipe_src=? WHERE id=?', (str(d), pid))
        pg._settings.setValue('pipe_grp_sel', grp)
        import app.core.ffmpeg_utils as FU
        goc = FU.probe
        luong = []

        def ghi(*a, **k):
            luong.append(threading.current_thread().name)
            return goc(*a, **k)
        mark = len(self.logs)
        with patch.object(FU, 'probe', side_effect=ghi):
            t0 = time.perf_counter()
            self.assertEqual(pg._pipe_run(nen=True), 0)
            self.assertLess(time.perf_counter() - t0, 0.5)
            self.assertTrue(cho(lambda: any('tổng nhận' in x for x in self.logs[mark:]), 60),
                            self.logs[mark:])
        self.assertTrue(any('tổng nhận 3/3' in x for x in self.logs[mark:]), self.logs[mark:])
        self.assertTrue(luong and all(n == 'bq-soi-file' for n in luong), luong)
        taken = [c for c in pg._pipe_cut.values() if c['pid'] == pid]
        self.assertEqual(len(taken), 3)
        for c in taken:
            row = db.query_one('SELECT f.file_hash, v.file_hash AS vh, v.duration FROM pipeline_files f '
                               'JOIN videos v ON v.id=f.video_id WHERE f.id=?', (c['entry'],))
            self.assertEqual(row['file_hash'], services._file_hash(c['path']))
            self.assertEqual(row['file_hash'], row['vh'])
            self.assertGreater(row['duration'], 1.0)

    def test_resume_after_restart_hashes_sources_off_ui_thread(self):
        pg = self.page
        pid, vid, src, clips, entry, ctx = self._video(1)
        db.execute('UPDATE projects SET pipe_src=? WHERE id=?', (str(src.parent), pid))
        jid = db.insert("INSERT INTO jobs(type,status,project_id,video_id,payload) "
                        "VALUES('auto','pending',?,?,'{}')", (pid, vid))
        import app.core.pipeline_safety as PS
        goc = PS.source_problem
        luong = []

        def ghi(*a, **k):
            luong.append(threading.current_thread().name)
            return goc(*a, **k)
        with patch.object(PS, 'source_problem', side_effect=ghi):
            t0 = time.perf_counter()
            pg._pipe_resume_auto()
            self.assertLess(time.perf_counter() - t0, 0.5)
            self.assertTrue(cho(lambda: vid in pg._pipe_by_vid))
        self.assertIn('bq-hoi-phuc', luong)
        self.assertNotIn('MainThread', luong)
        self.assertEqual(pg._pipe_cut[jid]['entry'], entry)
        self.assertEqual(pg._pending_export[jid], vid)
        pg._pipe_cut.pop(jid, None); pg._pipe_by_vid.pop(vid, None); pg._pending_export.pop(jid, None)
        db.execute("UPDATE jobs SET status='canceled' WHERE id=?", (jid,))
        P.unmark_taken(entry)

    def test_channel_activity_one_matches_full(self):
        pid, vid, *_ = self._video(1)
        db.insert("INSERT INTO jobs(type,status,project_id,video_id) VALUES('auto','running',?,?)", (pid, vid))
        db.insert("INSERT INTO jobs(type,status,project_id,video_id) VALUES('auto','pending',?,?)", (pid, vid))
        db.insert("INSERT INTO jobs(type,status,project_id,video_id,finished_at) "
                  "VALUES('auto','failed',?,?,datetime('now'))", (pid, vid))
        full = services.channel_activity()[pid]
        one = services.channel_activity_one(pid)
        for k in ('running', 'pending', 'failed_recent', 'last_done', 'last_done_type'):
            self.assertEqual(one[k], full[k], k)

    def test_batch_signature_and_light_snapshot(self):
        import app.services_batch as SB
        pid, vid, src, clips, *_ = self._video(2)
        jid = db.insert("INSERT INTO jobs(type,status,project_id,video_id,payload) "
                        "VALUES('m1_export_clip','pending',?,?,?)",
                        (pid, vid, db.dumps({'clip_id': clips[0]})))
        db.insert("INSERT INTO jobs(type,status,project_id,video_id,payload) "
                  "VALUES('m1_export_clip','failed',?,?,'không phải json')", (pid, vid))
        s1 = SB.signature(pid)
        self.assertEqual(s1, SB.signature(pid))
        moi = SB.snapshot(pid)
        with patch.object(SB, '_JSON_SQL', False):
            cu = SB.snapshot(pid)
        bo = lambda rows: [{k: v for k, v in r.items() if k != 'jobs'} for r in rows[0]]  # noqa: E731
        self.assertEqual(bo(moi), bo(cu))
        db.execute("UPDATE jobs SET status='running', message='đang xuất 10%' WHERE id=?", (jid,))
        s2 = SB.signature(pid)
        self.assertNotEqual(s1, s2)
        db.execute("UPDATE jobs SET message='đang xuất 50%' WHERE id=?", (jid,))
        self.assertNotEqual(s2, SB.signature(pid))
        db.execute("UPDATE clips SET export_path='x.mp4', status='exported' WHERE id=?", (clips[1],))
        self.assertNotEqual(s2, SB.signature(pid))


if __name__ == '__main__':
    unittest.main()
