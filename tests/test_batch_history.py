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
from PyQt6.QtWidgets import QApplication, QDialog, QPushButton, QMessageBox
from app import services
from app.database.db import db
from app.ui.appsettings import app_settings
from app.ui.batch_files import presence, inspect_record, file_labels, file_warning
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
        self.assertEqual(self.page.table.rowCount(),1)
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

    def test_manual_refresh_rechecks_moved_source_and_part_without_mutations(self):
        vid=self.video('manual-source.mp4',True);self.done(vid,'manual-part.mp4',True)
        self.page.refresh();self.settle()
        before=[tuple(row) for row in db.query('SELECT * FROM clips')]
        (AREA/'manual-source.mp4').rename(AREA/'manual-source-moved.mp4')
        (AREA/'manual-part.mp4').rename(AREA/'manual-part-moved.mp4')
        self.page.refresh_btn.click();self.settle()
        self.assertEqual(self.page._files[vid]['source'],'missing')
        self.assertEqual(self.page._files[vid]['parts'][0][1],'missing')
        self.assertEqual(self.page._visible_ids,[vid])
        self.assertIn('kiểm tra',self.page.table.item(0,2).text())
        self.assertIn('Kiểm tra lúc',self.page.file_status.text())
        self.assertEqual(before,[tuple(row) for row in db.query('SELECT * FROM clips')])
        self.assertEqual(db.query('SELECT * FROM jobs'),[])

    def test_recycled_source_with_present_parts_is_normal_history(self):
        vid=self.video('recycled-source.mp4');self.done(vid,'recycled-part.mp4',True)
        self.page.refresh();self.settle()
        self.assertEqual(file_warning(self.page.records[0],self.page._files[vid]),'')
        self.assertEqual(self.page.table.rowCount(),0)
        self.page.scope.setCurrentIndex(self.page.scope.findData('history'))
        self.assertEqual(self.page._visible_ids,[vid])

    def test_attention_scope_clears_after_part_restored(self):
        vid=self.video('attention-source.mp4');self.done(vid,'attention-part.mp4')
        self.page.refresh();self.settle()
        self.page.scope.setCurrentIndex(self.page.scope.findData('attention'))
        self.assertEqual(self.page._visible_ids,[vid])
        (AREA/'attention-part.mp4').write_bytes(b'restored')
        self.page.refresh_btn.click();self.settle()
        self.assertEqual(self.page.table.rowCount(),0)
        self.page.scope.setCurrentIndex(self.page.scope.findData('history'))
        self.assertEqual(self.page.table.item(0,2).text(),'Đã ghi xuất đủ')

    def test_changed_channel_clears_secondary_filters_and_clear_button_shows_all(self):
        self.video('filter-source.mp4')
        other=services.create_project('Other','Mỹ')
        vid=self.video('filter-other.mp4',True,other)
        self.page.refresh();self.settle()
        self.page.file_filter.setCurrentIndex(self.page.file_filter.findData('missing'))
        self.page.filter.setCurrentIndex(self.page.filter.findData('failed'))
        self.page.channels.select_project(other);self.settle()
        self.assertEqual(self.page.file_filter.currentData(),'')
        self.assertEqual(self.page.filter.currentData(),'')
        self.assertEqual(self.page._visible_ids,[vid])
        self.page.search.setText('does not match')
        self.assertEqual(self.page.table.rowCount(),0)
        self.assertIn('does not match',self.page.empty.text())
        self.page.clear_btn.click()
        self.assertEqual(self.page._visible_ids,[vid])
        self.assertEqual(self.page.scope.currentData(),'all')

    def test_parts_button_opens_recorded_video_location(self):
        vid=self.video('recorded-source.mp4');self.done(vid,'recorded-part.mp4',True)
        self.page.refresh();self.settle();self.page.clear_btn.click()
        self.page.table.selectRow(0)
        action=Mock();self.page.open_folder.connect(action)
        self.page.folder_btn.click()
        action.assert_called_once_with(self.pid,vid,'video')

    def test_source_preview_distinguishes_empty_missing_permission_and_unset(self):
        from app.ui.pipeline_preview import source_preview
        folder=AREA/'preview-empty';folder.mkdir(exist_ok=True)
        scan=Mock(return_value=([],[]))
        self.assertEqual(source_preview(str(folder),scan)['label'],'0')
        self.assertEqual(source_preview('',scan)['label'],'Chưa đặt')
        self.assertEqual(source_preview(str(AREA/'not-a-directory'),scan)['label'],'Không thấy')
        with patch('app.ui.pipeline_preview.os.scandir',side_effect=PermissionError()):
            self.assertEqual(source_preview(str(folder),scan)['label'],'Không đọc được')
        self.assertEqual(scan.call_count,1)

    def test_run_scope_not_narrowed_by_search_and_redo_is_menu_only(self):
        from app.ui.studio_page import StudioPage
        from app.ui.state import AppState
        state=AppState()
        existing=AREA/'preview-existing';existing.mkdir(exist_ok=True)
        db.execute('UPDATE projects SET pipe_on=1,pipe_src=? WHERE id=?',(str(existing),self.pid))
        other=services.create_project('Other preview','Mỹ')
        db.execute('UPDATE projects SET pipe_on=1,pipe_src=? WHERE id=?',(str(AREA/'preview-missing'),other))
        ignored=services.create_project('Another group','Nhật')
        db.execute('UPDATE projects SET pipe_on=1 WHERE id=?',(ignored,))
        app_settings().setValue('pipe_grp_sel','Mỹ')
        with patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            studio=StudioPage(state);self.widgets.append(studio)
            def inspect(dlg):
                self.assertIn('(2 kênh)',studio._pipe_run_button.text())
                self.assertIn('1 kênh cần kiểm tra thư mục',studio._pipe_scope_hint.text())
                labels=[studio._pipe_tbl.item(i,6).text() for i in range(studio._pipe_tbl.rowCount())]
                self.assertIn('Không thấy',labels);self.assertIn('0',labels)
                self.assertFalse(any(b.text()=='Cắt lại' for b in dlg.findChildren(QPushButton)))
                menus=[b.menu() for b in dlg.findChildren(QPushButton) if b.text()=='Thêm']
                self.assertEqual(len(menus),2)
                self.assertTrue(all('Phân tích / xuất lại' in menu.actions()[0].text() for menu in menus))
                studio._pipe_search.setText('Other preview');studio._pipe_fill()
                self.assertEqual(studio._pipe_tbl.rowCount(),1)
                self.assertIn('(2 kênh)',studio._pipe_run_button.text())
                self.assertIn('không thu hẹp',studio._pipe_scope_hint.text())
                return QDialog.DialogCode.Rejected
            with patch.object(QDialog,'exec',inspect),patch.object(studio,'_scan_cached',return_value=([],[])):
                studio._pipeline_dialog()
        state.pool.stop(wait=True)

    def test_hide_restore_preserves_media_database_and_active_work(self):
        from app.ui.batch_visibility import hidden
        vid=self.video('hide-source.mp4',True);self.done(vid,'hide-part.mp4',True)
        self.page.refresh();self.settle();self.page.clear_filters()
        before=[tuple(r) for r in db.query('SELECT * FROM clips')]
        self.page.table.selectRow(self.page._visible_ids.index(vid))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            self.page.change_visibility(True)
        self.assertNotIn(vid,self.page._visible_ids)
        self.page.scope.setCurrentIndex(self.page.scope.findData('hidden'))
        self.assertIn(vid,self.page._visible_ids)
        record=next(r for r in self.page.records if r['id']==vid)
        self.assertTrue(hidden(record))
        self.assertFalse(hidden(dict(record,job_ids=[123])))
        self.page.table.selectRow(0);self.page.change_visibility(False);self.page.clear_filters()
        self.assertIn(vid,self.page._visible_ids)
        self.assertEqual(before,[tuple(r) for r in db.query('SELECT * FROM clips')])
        self.assertTrue((AREA/'hide-source.mp4').exists());self.assertTrue((AREA/'hide-part.mp4').exists())
        self.assertEqual(db.query('SELECT * FROM jobs'),[])

    def test_inventory_button_targets_current_channel(self):
        self.video('inventory-route.mp4');self.page.refresh()
        calls=[];self.page.open_folder.connect(lambda *args:calls.append(args))
        self.page.inventory_btn.click()
        self.assertEqual(calls,[(self.pid,0,'inventory')])


if __name__=='__main__':unittest.main(verbosity=2)
