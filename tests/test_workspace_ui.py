"""Offline UI regression: selected-video actions, progress truth, and small screens."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_workspace_'))
os.environ.update(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'), QT_QPA_PLATFORM='offscreen', BQ_BO_MANG='1')
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: E402,F401
import app.queue.jobs  # noqa: E402,F401
from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtGui import QFontDatabase  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton, QPlainTextEdit, QWidget  # noqa: E402
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.services_batch import snapshot  # noqa: E402
from app.ui.batch_page import BatchPage  # noqa: E402
from app.ui.layout_tools import button_menu, SectionJump  # noqa: E402
from app.ui.theme import apply_theme  # noqa: E402

qapp = QApplication([])
for font in ('segoeui.ttf', 'segoeuib.ttf', 'seguisb.ttf'):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/font))
apply_theme(qapp)
QT_ERRORS = []
sys.excepthook = lambda kind,error,tb: QT_ERRORS.append(f'{kind.__name__}: {error}')


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM projects')
        self.pid = services.create_project('Kênh thử nghiệm', grp='Nhóm một')
        self.vid = self.video(self.pid, 'Đường phố.mp4')
        self.pool = Mock()
        self.page = BatchPage(types.SimpleNamespace(pool=self.pool))
        self.page.resize(1120, 690)
        self.page.show(); qapp.processEvents(); self.page.timer.stop()
        self.dialogs = []

    def tearDown(self):
        for widget in self.dialogs+[self.page]:
            for timer in widget.findChildren(QTimer):timer.stop()
            widget.hide();widget.deleteLater()
        qapp.processEvents()
        self.assertFalse(QT_ERRORS, '\n'.join(QT_ERRORS))

    def video(self,pid,name):
        return db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)',
            (pid,str(AREA/name)))

    def clip(self,status='suggested'):
        return db.insert('INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,2,?,?)',
            (self.vid,status,str(AREA/'part.mp4') if status=='exported' else ''))

    def job(self,status='failed',kind='auto',vid=None,cid=None):
        return db.insert('INSERT INTO jobs(type,project_id,video_id,status,payload,error) VALUES(?,?,?,?,?,?)',
            (kind,self.pid,vid or self.vid,status,json.dumps({'clip_id':cid}) if cid else '{}',
             'Lỗi mẫu' if status=='failed' else ''))

    def record(self):
        return next(r for r in snapshot()[0] if r['id']==self.vid)

    def select(self,vid):
        self.page.refresh()
        self.page.table.selectRow(self.page._visible_ids.index(vid))

    def test_failed_export_with_old_output_is_not_done(self):
        cid=self.clip('exported')
        self.job(kind='m1_export_clip',cid=cid)
        r=self.record()
        self.assertEqual(r['state'],'failed')
        self.assertEqual(r['parts'],'1/1')
        self.assertIn('Lỗi mẫu',r['detail'])

    def test_retry_supersedes_old_cancel_and_ignores_archived_parts(self):
        cid=self.clip('exported')
        self.job('canceled','m1_export_clip',cid=cid)
        self.assertEqual(self.record()['state'],'canceled')
        self.job('done','m1_export_clip',cid=cid)
        old=self.clip('archived')
        self.job('failed','m1_export_clip',cid=old)
        self.assertEqual(self.record()['state'],'done')
        self.assertEqual(self.record()['retry_ids'],[])

    def test_analysis_retry_does_not_requeue_obsolete_exports(self):
        cid=self.clip()
        self.job('failed','m1_export_clip',cid=cid)
        jid=self.job('failed')
        self.assertEqual(self.record()['retry_ids'],[jid])
        self.job('running')
        self.assertEqual(self.record()['retry_ids'],[])

    def test_source_cleanup_is_separate_from_export_state(self):
        self.clip('exported')
        pf=db.insert("INSERT INTO pipeline_files(project_id,video_id,file_name,status,note) VALUES(?,?,?,'done',?)",
            (self.pid,self.vid,'source.mp4','[GỐC KẸT]'))
        self.assertEqual(self.record()['state'],'done')
        self.assertEqual(self.record()['source'],'Gốc chưa dọn')
        db.execute('UPDATE pipeline_files SET note=? WHERE id=?',('[GỐC ĐÃ CHUYỂN THÙNG RÁC]',pf))
        self.assertEqual(self.record()['source'],'Đã vào Thùng rác')

    def test_filtering_is_read_only_and_supports_vietnamese(self):
        self.clip();self.job('pending')
        before=[tuple(r) for r in db.query('SELECT * FROM jobs')]
        self.page.refresh();self.page.search.setText('duong pho')
        self.assertEqual(self.page._visible_ids,[self.vid])
        self.page.filter.setCurrentIndex(self.page.filter.findData('done'))
        self.assertEqual(self.page.table.rowCount(),0)
        self.assertFalse(self.page.cancel_btn.isEnabled())
        self.assertEqual(before,[tuple(r) for r in db.query('SELECT * FROM jobs')])

    def test_selection_tracks_id_when_rows_reorder(self):
        other=self.video(self.pid,'Khác.mp4')
        self.select(self.vid)
        self.job('running',vid=other)
        self.page.refresh()
        self.assertEqual(self.page.selected()['id'],self.vid)
        self.page.search.setText('Khác')
        self.assertIsNone(self.page.selected())
        self.assertFalse(self.page.retry_btn.isEnabled())

    def test_cancel_scoped_and_refreshes_after_confirmation(self):
        wanted=self.job('pending')
        other=self.video(self.pid,'Khác.mp4');self.job('pending',vid=other)
        self.select(self.vid)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            self.page.cancel_selected()
        self.pool.cancel.assert_called_once_with(wanted)
        self.pool.cancel_all.assert_not_called()

    def test_retry_scoped_and_new_running_job_blocks_stale_click(self):
        wanted=self.job('failed')
        other=self.video(self.pid,'Khác.mp4');self.job('failed',vid=other)
        self.select(self.vid);self.page.retry_selected()
        self.pool.retry.assert_called_once_with(wanted)
        self.job('running')
        self.page.retry_selected()
        self.pool.retry.assert_called_once_with(wanted)

    def test_many_videos_bounded_rows_and_fast_refresh(self):
        for n in range(220):self.video(self.pid,f'Sample {n}.mp4')
        start=time.perf_counter();self.page.refresh()
        self.assertLess(time.perf_counter()-start,1.0)
        self.assertEqual(self.page.table.rowCount(),100)
        self.page.change_page(1)
        self.assertEqual(self.page.table.rowCount(),100)
        self.page.change_page(1)
        self.assertEqual(self.page.table.rowCount(),21)
        self.assertFalse(self.page.next.isEnabled())

    def test_menu_keeps_original_handler_and_enabled_state(self):
        widget=QWidget();self.dialogs.append(widget)
        original=QPushButton('Xuất',widget);handler=Mock();original.clicked.connect(handler)
        menu=button_menu(widget,'Thêm',[original]).menu()
        original.setEnabled(False);menu.aboutToShow.emit()
        self.assertFalse(menu.actions()[0].isEnabled())
        original.setEnabled(True);menu.aboutToShow.emit();menu.actions()[0].trigger()
        handler.assert_called_once()

    def test_workspace_navigation_keeps_pipeline_timer_and_correct_video(self):
        from app.ui.state import AppState
        from app.ui.main_window import MainWindow
        from app.ui.studio_page import StudioPage
        state=AppState()
        with patch.object(MainWindow,'_start_update_check'),patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            win=MainWindow(state);self.dialogs.append(win)
            win.resize(1280,720);win.show();qapp.processEvents()
            self.assertEqual((win.width(),win.height()),(1280,720))
            self.assertTrue(win.studio.timer.isActive())
            win._show_workspace(1);qapp.processEvents()
            self.assertTrue(win.studio.timer.isActive())
            self.assertFalse(win.queue_panel.timer.isActive())
            pid=services.create_project('Kênh khác',grp='Nhóm hai')
            vid=self.video(pid,'Nhóm khác.mp4')
            win._open_batch_video(pid,vid);qapp.processEvents()
            self.assertEqual(win.studio.proj.currentData(),pid)
            self.assertEqual(win.studio.vid.currentData(),vid)
            self.assertTrue(win.queue_panel.timer.isActive())
            self.assertTrue(win.nav_video.isChecked())
        state.pool.stop(wait=True)

    def test_editor_jump_resize_does_not_change_export_template(self):
        from app.ui.editor import EditorDialog
        from app.ui.state import AppState
        from app.ui.studio_page import StudioPage
        state=AppState()
        with patch.object(StudioPage,'_bg_thumbs'),patch.object(StudioPage,'_pipe_resume_auto'):
            studio=StudioPage(state);self.dialogs.append(studio)
            editor=EditorDialog(None,dict(studio.layout_tpl));self.dialogs.append(editor)
            editor.resize(1100,690);editor.show();qapp.processEvents()
            before=editor._collect_layout()
            jump=editor.findChild(SectionJump)
            self.assertGreaterEqual(jump.count(),7)
            jump.jump(jump.count()-1);editor.resize(1000,640);qapp.processEvents()
            self.assertEqual(before,editor._collect_layout())
            self.assertLessEqual(editor.height(),640)
        state.pool.stop(wait=True)

    def test_voice_and_recap_pinned_controls_and_settings_roundtrip(self):
        from app.ui.thay_giong_dialog import ThayGiongDialog
        from app.ui.recap_settings import RecapSettingsDialog
        from app.ui.appsettings import app_settings
        from app.ui.state import AppState
        state=AppState()
        with patch.object(ThayGiongDialog,'_nap_giong_nen'),patch.object(ThayGiongDialog,'_do_demucs'):
            voice=ThayGiongDialog(state.pool);self.dialogs.append(voice)
            voice.resize(1160,690);voice.show();qapp.processEvents()
            self.assertLessEqual(voice.settings_scroll.widget().minimumSizeHint().width(),1120)
            self.assertLessEqual(voice.settings_scroll.horizontalScrollBar().maximum(),0)
            value=voice.cb_khop.currentData()
            voice.settings_scroll.verticalScrollBar().setValue(100000);qapp.processEvents()
            self.assertEqual(value,voice.cb_khop.currentData())
            for button in (voice.b_chay,voice.b_dung):
                self.assertTrue(button.isVisibleTo(voice))
                self.assertLess(button.mapTo(voice,button.rect().bottomRight()).y(),voice.height())
            self.assertGreaterEqual(voice.bang.height(),150)
        s=app_settings();s.setValue('recap_ratio',42);s.setValue('recap_min_sec',40);s.setValue('recap_max_sec',120)
        s.setValue('story_quality',False)
        with patch.object(RecapSettingsDialog,'_fill_voices_bg'):
            recap=RecapSettingsDialog();self.dialogs.append(recap)
            recap.resize(690,640);recap.show();qapp.processEvents()
            self.assertFalse(recap.story_quality.isChecked())
            recap.story_quality.setChecked(True)
            self.assertEqual(recap.min_sec.value(),61)
            recap.min_sec.setValue(30)
            self.assertEqual(recap.min_sec.value(),61)
            recap.settings_scroll.verticalScrollBar().setValue(100000)
            with patch('config.update_env'):recap._save()
            self.assertEqual(int(s.value('recap_ratio')),42)
            self.assertEqual(int(s.value('recap_min_sec')),40)
            self.assertEqual(int(s.value('recap_max_sec')),120)
            self.assertEqual(int(s.value('story_min_sec')),61)
            self.assertEqual(int(s.value('story_max_sec')),119)
            self.assertTrue(s.value('story_quality',type=bool))
        state.pool.stop(wait=True)

    def test_story_review_displays_rendered_words_and_source_evidence(self):
        from app.ui.story_review import show_story
        from PyQt6.QtWidgets import QTableWidget
        original={'start':0,'end':12,'mode':'narrate','text':'A longer initial script.',
                  'evidence':json.dumps({'transcript':'Source words.','observations':[{'visible':'Blue card','uncertain':'Identity unknown'}]})}
        meta={'parts':[original],'rendered_parts':[dict(original,text='A blue card.')],'source_signature':[str(AREA/'absent.mp4')]}
        observed={}
        def inspect():
            dlg=qapp.activeModalWidget()
            if not dlg:return
            table=dlg.findChild(QTableWidget)
            observed['text']=table.item(0,2).text()
            observed['evidence']=dlg.findChild(QPlainTextEdit).toPlainText()
            observed['source_enabled']=next(b for b in dlg.findChildren(QPushButton) if b.text()=='Mở video nguồn').isEnabled()
            observed['width']=dlg.width()
            dlg.grab().save(str(AREA/'story-review.png'))
            dlg.accept()
        QTimer.singleShot(80,inspect)
        show_story(None,meta)
        self.assertEqual(observed['text'],'A blue card.')
        self.assertIn('Blue card',observed['evidence'])
        self.assertFalse(observed['source_enabled'])
        self.assertLessEqual(observed['width'],1100)

    def test_story_review_close_does_not_approve_and_save_uses_edited_words(self):
        from app.ui.story_review import show_story
        from PyQt6.QtWidgets import QTableWidget
        from PyQt6.QtCore import Qt
        meta={'parts':[{'start':0,'end':12,'mode':'narrate','text':'Two cards.','evidence':'Source'},
                       {'start':12,'end':24,'mode':'orig','text':'','evidence':'Original audio'}]}
        def close():qapp.activeModalWidget().reject()
        with patch('app.ai.story_quality.approve_script') as approve:
            QTimer.singleShot(30,close);self.assertFalse(show_story(None,meta,123));approve.assert_not_called()
            def edit():
                dlg=qapp.activeModalWidget();table=dlg.findChild(QTableWidget)
                self.assertTrue(table.item(0,2).flags() & Qt.ItemFlag.ItemIsEditable)
                self.assertFalse(table.item(1,2).flags() & Qt.ItemFlag.ItemIsEditable)
                table.item(0,2).setText('One card.')
                next(b for b in dlg.findChildren(QPushButton) if b.text()=='Lưu & duyệt').click()
            QTimer.singleShot(30,edit);self.assertTrue(show_story(None,meta,123))
            self.assertEqual(approve.call_args.args[2],['One card.',''])

    def test_update_notes_not_truncated_or_interpreted_as_html(self):
        from app.ui.update_dialog import UpdateDialog
        notes='<b>Ghi chú</b>\n'+('Dòng giải thích.\n'*200)+'KẾT THÚC'
        dlg=UpdateDialog({'tag':'vTEST','asset_url':'','notes':notes});self.dialogs.append(dlg)
        dlg.show();qapp.processEvents()
        self.assertEqual(dlg.findChild(QPlainTextEdit).toPlainText(),notes)
        self.assertLess(dlg.height(),650)

    def test_narrow_voice_label_keeps_cost_and_download_requirements(self):
        from PyQt6.QtGui import QFontMetrics
        from app.ui.thay_giong_dialog import nhan_gon
        metrics=QFontMetrics(qapp.font())
        for cost in ('miễn phí','TỐN TIỀN, cần key','cần tải bộ 250 MB'):
            label=('Andrew — Nam trầm ấm, kể chuyện đa ngôn ngữ '*3+
                ' - nhấn nhá 3,8 truyền cảm - đọc được Anh·Nhật·Trung - '+cost)
            shortened=nhan_gon(label,metrics,500)
            self.assertIn(cost,shortened)
            self.assertLessEqual(metrics.horizontalAdvance(shortened),500)


if __name__=='__main__':
    unittest.main(verbosity=2)
