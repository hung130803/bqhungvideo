"""History/file truth, stale asynchronous checks and unified pipeline navigation."""
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
AREA=Path(tempfile.mkdtemp(prefix='bq_history_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard
import app.queue.jobs
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from app import services
from app.database.db import db
from app.ui.appsettings import app_settings
from app.ui.batch_files import presence, inspect_record, file_labels
from app.ui.batch_page import BatchPage
from app.ui.theme import apply_theme

app=QApplication([]);apply_theme(app)
ERRORS=[]
sys.excepthook=lambda kind,error,tb:ERRORS.append(f'{kind.__name__}: {error}')


class HistoryTests(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM projects');app_settings().clear()
        self.pid=services.create_project('Kênh thử','Mỹ')
        self.page=BatchPage(types.SimpleNamespace(pool=Mock()))
        self.widgets=[self.page]

    def tearDown(self):
        for w in self.widgets:
            for timer in w.findChildren(QTimer):timer.stop()
            w.hide();w.deleteLater()
        app.processEvents()
        self.assertFalse(ERRORS,str(ERRORS))

    def video(self,name,exists=False,pid=None):
        path=AREA/name
        if exists:path.write_bytes(b'test source')
        return db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',(pid or self.pid,str(path)))

    def done(self,vid,name,exists=False):
        path=AREA/name
        if exists:path.write_bytes(b'test part')
        db.insert("INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,10,'exported',?)",(vid,str(path)))

    def settle(self):
        deadline=time.monotonic()+4
        while self.page.inspector._working and time.monotonic()<deadline:
            app.processEvents();time.sleep(.005)
        app.processEvents();self.page.render()

    def test_history_is_not_file_inventory_and_does_not_requeue_missing_parts(self):
        vid=self.video('old-source.mp4');self.done(vid,'old-part.mp4')
        self.page.refresh();self.settle()
        self.assertEqual(self.page.table.rowCount(),0)
        self.assertTrue(self.page.empty.text())
        self.page.scope.setCurrentIndex(self.page.scope.findData('history'))
        self.assertEqual(self.page._visible_ids,[vid])
        self.assertEqual(self.page.table.item(0,4).text(),'Không thấy ở đường dẫn cũ')
        self.assertIn('0/1 còn file',self.page.table.item(0,3).text())
        self.assertEqual(self.page.records[0]['state'],'done')
        self.page.table.selectRow(0)
        self.assertFalse(self.page.retry_btn.isEnabled())
        self.assertEqual(db.query('SELECT * FROM jobs'),[])

    def test_presence_permission_empty_folder_and_relative_are_not_missing(self):
        src=AREA/'real.mp4';src.write_bytes(b'x')
        empty=AREA/'empty.mp4';empty.write_bytes(b'')
        self.assertEqual(presence(str(src)),'present')
        self.assertEqual(presence(str(empty)),'empty')
        self.assertEqual(presence(str(AREA)),'invalid')
        self.assertEqual(presence('relative.mp4'),'unknown')
        with patch('app.ui.batch_files.os.stat',side_effect=PermissionError()):
            self.assertEqual(presence(str(src)),'unknown')

    def test_refresh_after_moved_file_keeps_history_and_new_path_invalidates_cache(self):
        vid=self.video('exists.mp4',True);self.done(vid,'exists-part.mp4',True)
        self.page.refresh();self.settle()
        row=self.page.records[0]
        self.assertEqual(self.page._files[vid]['source'],'present')
        (AREA/'exists.mp4').rename(AREA/'moved.mp4')
        self.page.check_files(force=True);self.settle()
        self.assertEqual(self.page._files[vid]['source'],'missing')
        db.execute('UPDATE videos SET src_path=? WHERE id=?',(str(AREA/'moved.mp4'),vid))
        self.page.refresh();self.settle()
        self.assertEqual(self.page._files[vid]['source'],'present')
        self.assertEqual((AREA/'moved.mp4').read_bytes(),b'test source')

    def test_stale_result_from_other_channel_or_changed_path_is_ignored(self):
        vid=self.video('first.mp4')
        self.page.refresh();self.settle()
        old=self.page.records[0];value=inspect_record(old)
        old_generation=self.page._scan_generation
        other=services.create_project('Khác','Mỹ')
        self.video('second.mp4',True,other)
        self.page.channels.select_project(other);self.settle()
        self.page._file_result(old_generation,vid,value)
        self.assertNotIn(vid,self.page._files)
        self.page._file_result(self.page._scan_generation,vid,value)
        self.assertNotIn(vid,self.page._files)

    def test_explicit_order_natural_names_and_source_filter(self):
        two=self.video('Video 2.mp4',True);ten=self.video('Video 10.mp4')
        self.page.refresh();self.settle()
        self.page.order.setCurrentIndex(self.page.order.findData('name'))
        self.assertEqual(self.page._visible_ids,[two,ten])
        self.page.order.setCurrentIndex(self.page.order.findData('new'))
        self.assertEqual(self.page._visible_ids,[ten,two])
        self.page.order.setCurrentIndex(self.page.order.findData('old'))
        self.assertEqual(self.page._visible_ids,[two,ten])
        self.page.file_filter.setCurrentIndex(self.page.file_filter.findData('present'))
        self.assertEqual(self.page._visible_ids,[two])
        self.page.file_filter.setCurrentIndex(self.page.file_filter.findData('missing'))
        self.assertEqual(self.page._visible_ids,[ten])

    def test_channel_folder_order_and_open_source_are_explicit(self):
        other=services.create_project('AAA','Mỹ')
        db.execute('UPDATE projects SET pipe_src=? WHERE id=?',(str(AREA/'Kênh 2'),self.pid))
        db.execute('UPDATE projects SET pipe_src=? WHERE id=?',(str(AREA/'Kênh 10'),other))
        self.page.refresh()
        panel=self.page.channels
        panel.order.setCurrentIndex(panel.order.findData('path'))
        self.assertEqual(panel.table.item(0,1).text(),'Kênh thử')
        panel.table.selectRow(0)
        action=Mock();self.page.open_folder.connect(action);panel.source_btn.click()
        action.assert_called_once_with(self.pid,0,'pipeline')

    def test_scan_is_off_gui_thread_and_refresh_does_not_rescan(self):
        self.video('slow.mp4')
        import threading
        started=threading.Event();release=threading.Event()
        def slow(r):
            started.set();release.wait(3);return inspect_record(r)
        with patch('app.ui.batch_files.inspect_record',side_effect=slow) as check:
            start=time.monotonic();self.page.refresh()
            self.assertLess(time.monotonic()-start,.7)
            self.assertTrue(started.wait(1))
            self.page.refresh();release.set();self.settle()
            self.assertEqual(check.call_count,1)

    def test_unified_navigation_preserves_channel_and_worker_timer_and_small_screen(self):
        from app.ui.main_window import MainWindow
        from app.ui.studio_page import StudioPage
        from app.ui.state import AppState
        state=AppState()
        with patch.object(MainWindow,'_start_update_check'),patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            win=MainWindow(state);self.widgets.append(win)
            win.resize(1280,720);win.show();app.processEvents()
            win.studio._select_project(self.pid)
            win.studio.open_pipeline_center.emit();app.processEvents()
            self.assertEqual(win.workspace.currentIndex(),1)
            self.assertEqual(win.batch.channels.pid,self.pid)
            self.assertTrue(win.studio.timer.isActive())
            self.assertEqual(win.nav_batch.text(),'Dây chuyền')
            self.assertEqual((win.width(),win.height()),(1280,720))
            for button in (win.batch.check_btn,win.batch.channels.paths_btn,win.batch.next,win.batch.config_btn):
                point=button.mapTo(win,button.rect().bottomRight())
                self.assertLess(point.x(),win.width());self.assertLess(point.y(),win.height())
            win.grab().save(str(AREA/'workflow.png'))
        state.pool.stop(wait=True)


if __name__=='__main__':unittest.main(verbosity=2)
