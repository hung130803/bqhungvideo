"""Isolated batch navigation, completeness, path integrity and screen tests."""
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
AREA=Path(tempfile.mkdtemp(prefix='bq_batch_channels_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: E402,F401
import app.queue.jobs  # noqa: E402,F401
from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.services_batch import snapshot  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402
from app.ui.batch_channels import ChannelPathsDialog, save_paths  # noqa: E402
from app.ui.batch_page import BatchPage  # noqa: E402
from app.ui.theme import apply_theme  # noqa: E402

qapp=QApplication([]);apply_theme(qapp)
ERRORS=[]
sys.excepthook=lambda kind,error,tb:ERRORS.append(f'{kind.__name__}: {error}')


class BatchChannelTests(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM pipeline_files');db.execute('DELETE FROM projects')
        app_settings().clear()
        self.pid=services.create_project('Kênh 2','Mỹ')
        self.other=services.create_project('Kênh 10','Mỹ')
        self.jp=services.create_project('Kênh Nhật','Nhật')
        self.vid=db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',(self.pid,str(AREA/'Cũ.mp4')))
        self.page=BatchPage(types.SimpleNamespace(pool=Mock()))
        self.page.resize(1040,640);self.page.show();qapp.processEvents();self.page.timer.stop()
        self.widgets=[self.page]

    def tearDown(self):
        for widget in self.widgets:
            for timer in widget.findChildren(QTimer):timer.stop()
            widget.hide();widget.deleteLater()
        qapp.processEvents()
        self.assertFalse(ERRORS,str(ERRORS))

    def test_groups_include_saved_empty_but_never_all(self):
        app_settings().setValue('chan_groups_extra',json.dumps(['Trống']))
        self.page.refresh()
        self.assertEqual([self.page.group.itemData(i) for i in range(self.page.group.count())],['Mỹ','Nhật','Trống'])
        self.page.group.setCurrentIndex(self.page.group.findData('Trống'))
        self.assertEqual(self.page.channels.table.rowCount(),0)
        self.assertEqual(self.page.table.rowCount(),0)
        self.assertTrue(self.page.channels.add_btn.isEnabled())
        self.assertFalse(self.page.channels.paths_btn.isEnabled())

    def test_ungrouped_only_when_present_and_no_cross_group_videos(self):
        pid=services.create_project('Chưa gán')
        self.page.refresh();self.assertGreaterEqual(self.page.group.findData(''),0)
        self.page.channels.select_project(pid)
        self.assertEqual(self.page.records,[])
        services.set_project_group(pid,'Nhật');self.page.refresh()
        self.assertEqual(self.page.group.findData(''),-1)

    def test_channel_numbering_empty_channels_search_and_remember(self):
        panel=self.page.channels
        self.assertEqual([panel.table.item(i,1).text() for i in range(2)],['Kênh 2','Kênh 10'])
        panel.search.setText('kenh 10')
        self.assertEqual(panel.table.item(0,0).text(),'2')
        self.assertEqual(panel.pid,self.other)
        self.assertEqual(self.page.records,[])
        self.assertTrue(panel.open_btn.isEnabled())
        newer=BatchPage(types.SimpleNamespace(pool=Mock()));self.widgets.append(newer)
        newer.refresh();self.assertEqual(newer.channels.pid,self.other)
        panel.search.clear();panel.select_project(self.jp)
        self.assertEqual(self.page.group.currentData(),'Nhật')

    def test_all_old_videos_accessible_above_2000_and_scoped_counts(self):
        con=db.conn()
        con.executemany('INSERT INTO videos(project_id,src_path) VALUES(?,?)',
            [(self.pid,str(AREA/f'Sample {i}.mp4')) for i in range(2050)]+[(self.jp,str(AREA/'Elsewhere.mp4'))])
        con.commit();self.page.refresh()
        self.assertEqual(self.page.total,2051)
        self.assertEqual(len(snapshot(self.pid)[0]),2051)
        self.assertEqual(self.page.table.rowCount(),100)
        self.page.search.setText('cu.mp4')
        self.assertEqual(self.page._visible_ids,[self.vid])
        self.assertIn('/2051',self.page.page_label.text())
        self.page.channels.select_project(self.jp)
        self.assertEqual(self.page.total,1)
        self.assertEqual(self.page.search.text(),'')

    def test_path_change_is_atomic_correct_channel_and_preserves_files(self):
        out=AREA/'Output';out.mkdir(exist_ok=True)
        src=AREA/'Source';src.mkdir(exist_ok=True)
        original=src/'Original.mp4';original.write_bytes(b'original')
        save_paths(self.pid,str(out),str(src),('',''))
        self.assertEqual(services.project_export_dir(self.pid),str(out))
        self.assertEqual(services.project_export_dir(self.other),'')
        self.page.refresh()
        self.assertEqual(self.page.channels.output.text(),str(out))
        self.assertEqual(self.page.channels.source.text(),str(src))
        self.assertEqual(original.read_bytes(),b'original')
        save_paths(self.pid,'','',(str(out),str(src)))
        self.assertEqual(services.project_export_dir(self.pid),'')

    def test_busy_or_pipeline_unfinished_blocks_both_paths(self):
        for kind in ('pending','running','taken'):
            if kind=='taken':
                db.insert("INSERT INTO pipeline_files(project_id,file_name,status) VALUES(?,'a.mp4','taken')",(self.pid,))
            else:
                db.insert('INSERT INTO jobs(type,project_id,status,payload) VALUES(?,?,?,?)',('auto',self.pid,kind,'{}'))
            with self.assertRaisesRegex(ValueError,'chưa hoàn tất'):
                save_paths(self.pid,str(AREA),str(AREA),('',''))
            self.assertEqual(services.project_export_dir(self.pid),'')
            db.execute('DELETE FROM jobs');db.execute('DELETE FROM pipeline_files')

    def test_stale_deleted_and_invalid_paths_do_not_overwrite(self):
        services.set_project_export_dir(self.pid,str(AREA))
        with self.assertRaisesRegex(ValueError,'nơi khác'):save_paths(self.pid,'','',('',''))
        with self.assertRaisesRegex(ValueError,'tồn tại'):save_paths(self.pid,'relative','',(str(AREA),''))
        self.assertEqual(services.project_export_dir(self.pid),str(AREA))
        db.execute('DELETE FROM projects WHERE id=?',(self.pid,))
        with self.assertRaisesRegex(ValueError,'không còn'):save_paths(self.pid,'','',('',''))

    def test_dialog_cancel_browse_cancel_and_invalid_save(self):
        dlg=ChannelPathsDialog(self.pid);self.widgets.append(dlg)
        dlg.output.setText(str(AREA))
        with patch('app.ui.batch_channels.QFileDialog.getExistingDirectory',return_value=''):
            dlg.browse(dlg.output)
        self.assertEqual(dlg.output.text(),str(AREA))
        dlg.reject();self.assertEqual(services.project_export_dir(self.pid),'')
        dlg.output.setText('relative');dlg.save()
        self.assertNotEqual(dlg.result(),QDialog.DialogCode.Accepted)
        self.assertTrue(dlg.error.text())

    def test_channel_open_without_video_and_no_selection_after_search(self):
        callback=Mock();self.page.open_folder.connect(callback)
        self.page.channels.select_project(self.other);self.page.channels.open_btn.click()
        callback.assert_called_once_with(self.other,0,'channel')
        self.page.channels.search.setText('DoesNotExist')
        self.assertEqual(self.page.records,[])
        self.assertFalse(self.page.channels.open_btn.isEnabled())
        self.assertFalse(self.page.open_btn.isEnabled())

    def test_small_window_controls_fit_and_modal_restores_timers(self):
        from app.ui.main_window import MainWindow
        from app.ui.state import AppState
        from app.ui.studio_page import StudioPage
        state=AppState()
        with patch.object(MainWindow,'_start_update_check'),patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            win=MainWindow(state);self.widgets.append(win)
            win.resize(1280,720);win.show();win._show_workspace(1);qapp.processEvents()
            self.assertEqual((win.width(),win.height()),(1280,720))
            self.assertTrue(win.studio.timer.isActive())
            def dialog(_dlg):
                self.assertFalse(win.studio.timer.isActive());self.assertFalse(win.batch.timer.isActive())
                return QDialog.DialogCode.Rejected
            with patch.object(ChannelPathsDialog,'exec',dialog):win._batch_manage('paths',self.pid)
            self.assertTrue(win.studio.timer.isActive());self.assertTrue(win.batch.timer.isActive())
            # Add from a different group than Studio's current selection.
            win.batch.channels.select_project(self.jp)
            with patch('PyQt6.QtWidgets.QInputDialog.getText',return_value=('Kênh mới',True)):
                win._batch_manage('add','Nhật')
            created=next(p for p in win.batch.channels.projects if p['name']=='Kênh mới')
            self.assertEqual(created['grp'],'Nhật')
            self.assertEqual(win.batch.channels.pid,created['id'])
            with patch.object(win.studio,'_pipeline_dialog') as configure:
                win._batch_pipeline()
            configure.assert_called_once()
            self.assertEqual(win.studio._settings.value('pipe_grp_sel'),'Nhật')
            for button in (win.batch.channels.paths_btn,win.batch.cancel_btn,win.batch.next):
                self.assertLess(button.mapTo(win,button.rect().bottomRight()).y(),win.height())
            win.batch.grab().save(str(AREA/'batch.png'))
        state.pool.stop(wait=True)


if __name__=='__main__':unittest.main(verbosity=2)
