"""Dây chuyền không bỏ sót / không kẹt gốc (27/10/2026, từ sổ thật của anh Hùng):
  1. Lệnh xuất TRÙNG còn chờ sau khi Part đã xuất xong -> chặn dọn gốc.
  2. AI lỗi tạm thời (key Groq bị hạn chế) -> video nằm im "chờ xem lại".
  3. Video gốc tên "Part N…" bị bỏ qua im lặng.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_day_chuyen_sot_'))
os.environ.setdefault('BQ_DATA_DIR', str(AREA))
os.environ.setdefault('BQ_DB_PATH', str(AREA / 'test.db'))
os.environ.setdefault('BQ_QSETTINGS_INI', str(AREA / 'settings.ini'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: E402,F401
from app import services  # noqa: E402
from app.core import pipeline as P  # noqa: E402
from app.core.export_recovery import bo_xuat_trung_da_xong  # noqa: E402
from app.core.pipeline_safety import latest_export_states  # noqa: E402
from app.database.db import db  # noqa: E402


def _job(vid, cid, status, created, finished=None, out_dir='', name='Part 1 a.mp4', result=None):
    return db.insert(
        "INSERT INTO jobs(type,video_id,payload,status,created_at,finished_at,result) "
        "VALUES('m1_export_clip',?,?,?,?,?,?)",
        (vid, json.dumps({'clip_id': cid, 'out_dir': out_dir, 'out_name': name,
                          'part_no': 1, 'flat': True}), status, created, finished,
         json.dumps(result or {})))


class XuatTrungTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=AREA))
        self.pid = services.create_project(f'K{self.d.name}', 'Mỹ')
        self.vid = db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',
                             (self.pid, str(self.d / 'goc.mp4')))
        self.cid = db.insert("INSERT INTO clips(video_id,start_sec,end_sec,status) "
                             "VALUES(?,0,10,'exported')", (self.vid,))
        part = self.d / 'Part 1 a.mp4'
        part.write_bytes(b'x' * 100)
        db.execute('UPDATE clips SET export_path=? WHERE id=?', (str(part), self.cid))

    def test_lenh_trung_cho_sau_khi_da_xuat_xong_bi_bo(self):
        # đúng ca 561PC: lệnh cũ chờ -> app mở lại xếp lệnh mới -> lệnh cũ xong
        old = _job(self.vid, self.cid, 'done', '2026-10-25 14:35:08', '2026-10-25 17:55:35',
                   str(self.d), result={'export_path': str(self.d / 'Part 1 a.mp4')})
        dup = _job(self.vid, self.cid, 'pending', '2026-10-25 17:20:34', None, str(self.d))
        self.assertEqual(latest_export_states(self.vid)[self.cid], 'pending')
        self.assertGreaterEqual(bo_xuat_trung_da_xong(), 1)
        row = db.query_one('SELECT status,result FROM jobs WHERE id=?', (dup,))
        self.assertEqual(row['status'], 'skipped')
        self.assertEqual(json.loads(row['result'])['superseded_by'], old)
        self.assertEqual(latest_export_states(self.vid)[self.cid], 'done')

    def test_xuat_lai_co_chu_y_khong_bi_bo(self):
        # bấm Xuất lại SAU khi lần trước đã xong -> giữ nguyên lệnh mới
        _job(self.vid, self.cid, 'done', '2026-10-25 10:00:00', '2026-10-25 10:20:00', str(self.d))
        moi = _job(self.vid, self.cid, 'pending', '2026-10-25 11:00:00', None, str(self.d))
        bo_xuat_trung_da_xong()
        self.assertEqual(db.query_one('SELECT status FROM jobs WHERE id=?', (moi,))['status'], 'pending')

    def test_khac_noi_luu_hoac_mat_file_khong_bi_bo(self):
        _job(self.vid, self.cid, 'done', '2026-10-25 10:00:00', '2026-10-25 12:00:00',
             str(self.d), name='Part 1 khac.mp4')
        k1 = _job(self.vid, self.cid, 'pending', '2026-10-25 11:00:00', None, str(self.d))
        bo_xuat_trung_da_xong()
        self.assertEqual(db.query_one('SELECT status FROM jobs WHERE id=?', (k1,))['status'], 'pending')


class _GiaTrang:
    """Gọi thẳng 2 hàm hẹn-thử-lại của StudioPage, không dựng giao diện."""
    from app.ui.studio_page import StudioPage as _S
    _AI_THU_LAI_TOI_DA = _S._AI_THU_LAI_TOI_DA
    _AI_THU_LAI_PHUT = _S._AI_THU_LAI_PHUT
    _pipe_khoa = staticmethod(_S._pipe_khoa)
    _pipe_ai_hen_thu_lai = _S._pipe_ai_hen_thu_lai

    def __init__(self):
        self.log = []

    def _pipe_log(self, s):
        self.log.append(s)


class AiThuLaiTests(unittest.TestCase):
    def setUp(self):
        self.pid = services.create_project(f'AI{id(self)}', 'Mỹ')
        self.path = str(AREA / f'goc_{id(self)}.mp4')
        self.entry = P.take_file(self.pid, Path(self.path).name, 'h' + str(id(self)))
        self.ctx = {'entry': self.entry, 'path': self.path, 'pid': self.pid,
                    'name': 'Kênh', 'file': Path(self.path).name, 'mode': 'auto'}

    def test_ai_loi_tam_thoi_hen_thu_lai_va_go_so(self):
        page = _GiaTrang()
        out = {'count': 2, 'selection': {'analysis_complete': False}}
        self.assertTrue(page._pipe_ai_hen_thu_lai(self.ctx, out, 'x'))
        self.assertIsNone(db.query_one('SELECT id FROM pipeline_files WHERE id=?', (self.entry,)))
        self.assertEqual(len(page._ai_thu_lai_q), 1)
        self.assertIn('tự thử lại', page.log[-1])

    def test_toi_da_3_lan_roi_moi_cho_xem_lai(self):
        page = _GiaTrang()
        out = {'count': 0, 'selection': {'analysis_complete': True, 'critic_incomplete': True}}
        for _ in range(3):
            e = P.take_file(self.pid, 'x.mp4', 'hh')
            self.assertTrue(page._pipe_ai_hen_thu_lai(dict(self.ctx, entry=e), out, 'x'))
        self.assertFalse(page._pipe_ai_hen_thu_lai(self.ctx, out, 'x'))

    def test_ai_cham_xong_va_loai_het_thi_khong_thu_lai(self):
        page = _GiaTrang()
        out = {'count': 0, 'selection': {'analysis_complete': True}}
        self.assertFalse(page._pipe_ai_hen_thu_lai(self.ctx, out, 'x'))
        self.assertIsNotNone(db.query_one('SELECT id FROM pipeline_files WHERE id=?', (self.entry,)))


class PartTenTests(unittest.TestCase):
    def test_bao_video_goc_ten_part_nhung_khong_bao_part_da_xuat(self):
        d = Path(tempfile.mkdtemp(dir=AREA))
        pid = services.create_project(f'PT{d.name}', 'Mỹ')
        vid = db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)', (pid, str(d / 'g.mp4')))
        that = d / 'Part 1 Da xuat.mp4'
        that.write_bytes(b'x')
        db.insert("INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) "
                  "VALUES(?,0,1,'exported',?)", (vid, str(that)))
        (d / 'Part 2 - my road trip.mp4').write_bytes(b'x')
        self.assertEqual(P.part_ten_la(d, pid), ['Part 2 - my road trip.mp4'])


if __name__ == '__main__':
    unittest.main()
