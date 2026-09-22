"""Regression checks for visible batch progress using the real Qt panel and DB."""
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_progress_'))
os.environ.update(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA/'test.db'),
                  BQ_QSETTINGS_INI=str(AREA/'settings.ini'), QT_QPA_PLATFORM='offscreen', BQ_BO_MANG='1')
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: F401,E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.queue_panel import QueuePanel  # noqa: E402
from app.ui.theme import apply_theme  # noqa: E402

app = QApplication([])
from PyQt6.QtGui import QFontDatabase  # noqa: E402
# Qt offscreen does not enumerate Windows system fonts itself.
for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
    path = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/font
    if path.is_file():
        QFontDatabase.addApplicationFont(str(path))
apply_theme(app)


class QueueProgress(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM projects')
        self.pid = services.create_project('COURT NERDS | Mỹ mới 1')
        self.vid = db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',
                             (self.pid, str(AREA/'Court Watch Judge Erupts During Testimony.mp4')))
        self.panel = QueuePanel(types.SimpleNamespace(pool=Mock()))
        self.panel.timer.stop()
        self.panel.resize(1220, 470)
        self.panel.show()
        app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        app.processEvents()

    def job(self, kind='auto', status='running', progress=.92, message='AI đang chọn các đoạn nổi bật…', payload='{}'):
        return db.insert('INSERT INTO jobs(type,project_id,video_id,status,progress,message,payload) VALUES(?,?,?,?,?,?,?)',
                         (kind,self.pid,self.vid,status,progress,message,payload))

    def test_visible_stage_estimate_and_widget_reuse(self):
        jid=self.job()
        self.panel.refresh()
        row=self.panel._rows[jid]
        self.assertIn('AI đang chọn',row['detail'].text())
        self.assertIn('~92%',row['st'].text())
        db.execute("UPDATE jobs SET progress=1,message='Hoàn thiện hashtag cho các Part…' WHERE id=?",(jid,))
        self.panel.refresh()
        self.assertIs(row['bar'],self.panel._rows[jid]['bar'])
        self.assertEqual(row['bar'].value(),99)
        self.assertIn('Hoàn thiện hashtag',row['detail'].text())
        db.execute("UPDATE jobs SET status='done' WHERE id=?",(jid,))
        self.panel.refresh()
        self.assertEqual(row['bar'].value(),100)
        self.assertIn('xem riêng',row['detail'].full_text())

    def test_retry_clears_error_click_and_pending_stale_progress(self):
        jid=self.job(status='failed')
        db.execute("UPDATE jobs SET error='Lỗi mạng thử nghiệm' WHERE id=?",(jid,))
        self.panel.refresh()
        self.panel._show_error=Mock()
        row=self.panel._rows[jid]
        row['st'].mousePressEvent(None)
        self.panel._show_error.assert_called_once()
        db.execute("UPDATE jobs SET status='pending',error=NULL WHERE id=?",(jid,))
        self.panel.refresh()
        row['st'].mousePressEvent(None)
        self.panel._show_error.assert_called_once()
        self.assertEqual(row['bar'].value(),0)
        self.assertNotIn('AI đang chọn',row['detail'].full_text())
        self.assertNotIn('LỖI:',row['name'].toolTip())

    def test_part_progress_counts_active_clips_only_and_midnight_completion(self):
        for status in ('exported','suggested','archived'):
            db.insert('INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,2,?,?)',
                       (self.vid,status,str(AREA/'Part.mp4') if status!='suggested' else ''))
        jid=self.job(kind='m1_export_clip',message='Mã hóa video: 45%',progress=.45,payload='{"part_no":2}')
        done=self.job(status='done')
        db.execute("UPDATE jobs SET created_at=datetime('now','-2 days'),finished_at=datetime('now') WHERE id=?",(done,))
        self.panel.refresh()
        row=self.panel._rows[jid]
        self.assertIn('Part 2',row['name'].full_text())
        self.assertIn('1/2 Part',row['detail'].full_text())
        self.assertNotIn('~',row['st'].text())
        self.assertEqual(services.queue_counts()['done_analyze'],1)
        self.assertIn('1 việc AI/xử lý',self.panel.summary.text())
        db.insert("INSERT INTO pipeline_files(project_id,video_id,file_name,status,note) VALUES(?,?,?,'done',?)",
                  (self.pid,self.vid,'source.mp4','2 part [GỐC ĐÃ CHUYỂN THÙNG RÁC]'))
        db.execute("UPDATE jobs SET status='done' WHERE id=?",(jid,))
        self.panel.refresh()
        self.assertIn('Gốc đã chuyển vào Thùng rác',row['detail'].full_text())

    def test_many_jobs_bounded_rows_and_narrow_layout(self):
        for i in range(600):
            self.job(status='pending' if i>4 else 'running')
        self.panel.refresh()
        self.assertLessEqual(len(self.panel._rows),36)
        begin=time.perf_counter()
        for _ in range(5):
            self.panel.refresh()
        self.assertLess((time.perf_counter()-begin)/5,.4)
        self.panel.resize(510,470)
        app.processEvents()
        self.assertTrue(self.panel._narrow)
        for row in self.panel._rows.values():
            self.assertTrue(row['bar'].isHidden())
            self.assertGreater(row['detail'].width(),60)
        self.panel.grab().save(str(AREA/'queue-narrow.png'))

    def test_preview_batch(self):
        self.job()
        self.job(kind='m1_export_clip',progress=.45,message='FFmpeg đang mã hóa khung hình và âm thanh…',payload='{"part_no":2}')
        self.job(status='pending',message='')
        self.job(status='done',message='Xong')
        self.job(status='failed',message='Groq: dịch vụ tạm thời không phản hồi')
        self.panel.refresh()
        app.processEvents()
        self.assertTrue(self.panel.grab().save(str(AREA/'queue-wide.png')))
        print('PREVIEW',AREA,flush=True)


if __name__=='__main__':
    unittest.main(verbosity=2)
