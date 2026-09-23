"""Exercise real folder buttons without launching Explorer or touching user data."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
AREA=Path(tempfile.mkdtemp(prefix='bq_folders_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: E402,F401
import app.queue.jobs  # noqa: E402,F401
from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtGui import QFontDatabase  # noqa: E402
from PyQt6.QtWidgets import QApplication,QPushButton  # noqa: E402
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui import folder_access as folders  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402
from app.ui.theme import apply_theme  # noqa: E402

qapp=QApplication([])
for name in ('segoeui.ttf','segoeuib.ttf','seguisb.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name))
apply_theme(qapp)
QT_ERRORS=[]
sys.excepthook=lambda kind,error,tb:QT_ERRORS.append(f'{kind.__name__}: {error}')


class FolderShortcuts(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM projects')
        self.area=Path(tempfile.mkdtemp(dir=AREA))
        self.root=self.area/'Kho riêng'
        self.pid=services.create_project('Kênh | Một. ',grp='Nhóm một')
        self.src=self.area/'Nguồn'/'Tình huống 01.mp4'
        self.vid=db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',(self.pid,str(self.src)))
        self.expected=self.root/'Đã xuất'/'Kênh _ Một'
        self.launch=patch.object(folders.os,'startfile');self.startfile=self.launch.start()
        self.windows=[]

    def tearDown(self):
        self.launch.stop()
        for win in self.windows:
            for timer in win.findChildren(QTimer):timer.stop()
            win.hide();win.deleteLater()
        qapp.processEvents()
        self.assertFalse(QT_ERRORS,'\n'.join(QT_ERRORS))

    def perform(self,kind):
        return folders.perform(None,kind,self.pid,self.vid,self.root)

    def test_unexported_channel_opens_exact_channel_not_common_root(self):
        self.assertFalse(self.expected.exists())
        self.assertIn('Đã mở',self.perform('channel'))
        self.assertTrue(self.expected.is_dir())
        self.startfile.assert_called_once_with(str(self.expected))
        self.assertFalse((self.expected/self.src.stem).exists())

    def test_custom_flat_folder_does_not_create_default_library(self):
        custom=self.area/'Thư mục chung của kênh'
        services.set_project_export_dir(self.pid,str(custom))
        self.perform('channel')
        self.startfile.assert_called_once_with(str(custom))
        self.assertFalse(self.root.exists())
        self.assertEqual(folders.locations(self.pid,self.vid,self.root)['video'],custom)

    def test_copy_path_does_not_create_directories_or_change_settings(self):
        before=[tuple(r) for r in db.query('SELECT * FROM projects')]
        self.perform('copy')
        self.assertEqual(qapp.clipboard().text(),str(self.expected))
        self.assertFalse(self.root.exists());self.startfile.assert_not_called()
        self.assertEqual(before,[tuple(r) for r in db.query('SELECT * FROM projects')])

    def test_missing_source_directory_is_not_recreated(self):
        message=self.perform('source')
        self.assertIn('không tồn tại',message)
        self.assertFalse(self.src.parent.exists());self.startfile.assert_not_called()

    def test_deleted_source_can_still_open_its_existing_parent(self):
        self.src.parent.mkdir()
        self.perform('source')
        self.startfile.assert_called_once_with(str(self.src.parent))
        self.assertFalse(self.src.exists())

    def test_video_part_folder_follows_recorded_export_after_rename(self):
        old=self.area/'Kênh cũ'/'Video cũ';old.mkdir(parents=True)
        db.insert("INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,2,'exported',?)",
            (self.vid,str(old/'Part 1.mp4')))
        self.perform('video')
        self.startfile.assert_called_once_with(str(old))
        self.assertFalse(self.expected.exists())

    def test_multiple_recorded_folders_let_user_choose(self):
        for name in ('Lần xuất cũ','Lần xuất mới'):
            old=self.area/name;old.mkdir()
            db.insert("INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,2,'exported',?)",
                (self.vid,str(old/'Part 1.mp4')))
        with patch.object(folders,'show_locations') as show:
            self.assertIn('nhiều thư mục',self.perform('video'))
        show.assert_called_once();self.startfile.assert_not_called()

    def test_wrong_channel_or_missing_selection_never_opens(self):
        other=services.create_project('Khác',grp='Nhóm hai')
        self.assertIn('không thuộc',folders.perform(None,'channel',other,self.vid,self.root))
        self.assertIn('Chọn kênh',folders.perform(None,'channel',None,None,self.root))
        self.startfile.assert_not_called()

    def test_failed_explorer_and_file_instead_of_folder_are_reported(self):
        self.startfile.side_effect=OSError('Windows từ chối mở')
        self.assertIn('Windows từ chối mở',self.perform('channel'))
        self.startfile.reset_mock();self.startfile.side_effect=None
        fake=self.area/'not-a-folder.exe';fake.write_bytes(b'not executable')
        services.set_project_export_dir(self.pid,str(fake))
        self.assertIn('Không thực hiện được',self.perform('channel'))
        self.startfile.assert_not_called()

    def test_relative_path_is_not_opened_as_current_working_directory(self):
        services.set_project_export_dir(self.pid,'relative-output')
        self.assertIn('chưa đầy đủ',self.perform('channel'))
        self.startfile.assert_not_called()

    def test_pipeline_source_priority_matches_current_configuration(self):
        shared=self.area/'Chung';explicit=self.area/'Riêng'
        services.set_project_export_dir(self.pid,str(shared))
        self.assertEqual(folders.locations(self.pid,self.vid,self.root,'D:/Stage')['pipeline'],shared)
        db.execute('UPDATE projects SET pipe_src=? WHERE id=?',(str(explicit),self.pid))
        self.assertEqual(folders.locations(self.pid,self.vid,self.root,'D:/Stage')['pipeline'],explicit)

    def test_buttons_menu_routing_and_batch_target_remain_correct(self):
        state=AppState()
        with patch.object(MainWindow,'_start_update_check'),patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            win=MainWindow(state);self.windows.append(win)
            win.studio._settings.setValue('lib_root',str(self.root))
            win.studio._select_project(self.pid);win.studio._reload_videos(select_id=self.vid)
            win.resize(1280,720);win.show();qapp.processEvents()
            self.assertEqual((win.width(),win.height()),(1280,720))
            win.studio.channel_folder_btn.click()
            self.startfile.assert_called_once_with(str(self.expected));self.startfile.reset_mock()
            button=next(b for b in win.studio.findChildren(QPushButton) if b.text()=='Thư mục khác')
            with patch.object(folders,'perform',return_value='TEST') as perform:
                for action,kind in zip(button.menu().actions(),('video','source','pipeline','copy','details')):
                    action.trigger();self.assertEqual(perform.call_args.args[1],kind)
            other=services.create_project('Kênh khác',grp='Nhóm hai')
            othervid=db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',(other,str(self.area/'other.mp4')))
            selected=(win.studio.proj.currentData(),win.studio.vid.currentData())
            win._show_workspace(1);win.batch.refresh()
            win.batch.table.selectRow(win.batch._visible_ids.index(othervid))
            win.batch.folder_btn.click()
            self.startfile.assert_called_once_with(str(self.root/'Đã xuất'/'Kênh khác'))
            self.assertEqual(selected,(win.studio.proj.currentData(),win.studio.vid.currentData()))
            self.assertEqual(win.workspace.currentIndex(),1)
            self.assertLessEqual(win.width(),1280)
            with patch.object(win.studio,'_lib_root',side_effect=OSError('Cấu hình hỏng')):
                win.studio.channel_folder_btn.click()
                self.assertIn('Cấu hình hỏng',win.studio.status.text())
                win.batch.folder_btn.click()
                self.assertIn('Cấu hình hỏng',win.batch.feedback.text())
            win.batch.search.setText('zzzzKhôngKếtQuả')
            self.assertFalse(win.batch.folder_btn.isEnabled())
        state.pool.stop(wait=True)


if __name__=='__main__':unittest.main(verbosity=2)
