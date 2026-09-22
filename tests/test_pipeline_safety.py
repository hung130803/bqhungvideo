"""Exercise released source against isolated DB/files; never touch user media."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(os.environ.get('TEMP', str(ROOT.parent)))/'pipeline-audit'/uuid.uuid4().hex
AREA.mkdir(parents=True)
os.environ.update(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA/'test.db'),
                  BQ_QSETTINGS_INI=str(AREA/'settings.ini'), QT_QPA_PLATFORM='offscreen',
                  BQ_BO_MANG='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  FFMPEG_PATH=str(ROOT/'bin/ffmpeg.exe'), FFPROBE_PATH=str(ROOT/'bin/ffprobe.exe'))
sys.path.insert(0, str(ROOT))
import _test_guard
import app.queue.jobs
from app import services
from app.core import pipeline as P
from app.core.ffmpeg_utils import probe
from app.database.db import db
from app.ui.studio_page import StudioPage, MARK_STUCK
from app.ui.state import AppState
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

app = QApplication([])


class PipelineAudit(unittest.TestCase):
    def setUp(self):
        self.folder = AREA/hashlib.sha1(self._testMethodName.encode()).hexdigest()[:8]
        (self.folder/'input').mkdir(parents=True)
        self.source = self.folder/'input/source.mp4'
        self.source.write_bytes(b'original source content')
        self.name = 'Audit ' + self.folder.name
        self.pid = services.create_project(self.name)
        db.execute('UPDATE projects SET pipe_src=?,export_dir=?,pipe_on=1 WHERE id=?',
                   (str(self.source.parent), str(self.folder/'output'), self.pid))
        self.vid = db.insert('INSERT INTO videos(project_id,src_path,file_hash,duration,width,height) VALUES(?,?,?,?,?,?)',
                             (self.pid, str(self.source), services._file_hash(str(self.source)), 4, 320, 240))
        self.entry = P.take_file(self.pid, self.source.name, services._file_hash(str(self.source)), self.vid)
        self.clips, self.parts, self.jobs = [], [], []
        for i in range(2):
            part = self.folder/f'Part {i+1}.mp4'
            part.write_bytes(b'nonempty part '+bytes([i]))
            cid = db.insert('INSERT INTO clips(video_id,start_sec,end_sec,title,status,export_path,signals) VALUES(?,?,?,?,?,?,?)',
                            (self.vid, i*2, i*2+2, f'clip {i}', 'exported', str(part), db.dumps({'llm_used':True})))
            jid = db.insert('INSERT INTO jobs(type,project_id,video_id,status,payload) VALUES(?,?,?,?,?)',
                            ('m1_export_clip',self.pid,self.vid,'done',db.dumps({'clip_id':cid,'part_no':i+1})))
            self.clips.append(cid); self.parts.append(part); self.jobs.append(jid)
        self.ctx = {'entry':self.entry,'vid':self.vid,'pid':self.pid,'path':str(self.source),
                    'name':self.name,'file':self.source.name,'mode':'auto'}
        self.logs = []
        self.page = types.SimpleNamespace(
            _pipe_exports={self.vid:{'jobs':set(self.jobs),'ctx':self.ctx,'clips':self.clips}},
            _pipe_recycle_dir=lambda:str(self.folder/'recycle'), _pipe_root=lambda:str(self.folder),
            _pipe_log=self.logs.append)

    def poll(self):
        StudioPage._pipe_poll_exports(self.page)

    def test_complete_parts_move_source_and_can_restore_identically(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.poll()
        self.assertFalse(self.source.exists())
        moved = list(self.folder.rglob('source.mp4'))
        self.assertEqual(len(moved),1)
        self.assertTrue(all(part.exists() for part in self.parts))
        restored = P.restore_recycled(str(moved[0]),str(self.source.parent))
        self.assertEqual(hashlib.sha256(restored.read_bytes()).hexdigest(),before)

    def test_waits_for_all_export_jobs(self):
        db.execute("UPDATE jobs SET status='running' WHERE id=?",(self.jobs[1],))
        self.poll()
        self.assertTrue(self.source.exists())
        self.assertIn(self.vid,self.page._pipe_exports)

    def test_missing_part_keeps_source(self):
        self.parts[1].unlink()
        self.poll()
        self.assertTrue(self.source.exists())

    def test_empty_part_keeps_source(self):
        self.parts[1].write_bytes(b'')
        self.poll()
        self.assertTrue(self.source.exists())

    def test_failed_export_keeps_source_even_if_old_part_exists(self):
        db.execute("UPDATE jobs SET status='failed' WHERE id=?",(self.jobs[0],))
        self.poll()
        self.assertTrue(self.source.exists())

    def test_canceled_export_keeps_source(self):
        db.execute("UPDATE jobs SET status='canceled' WHERE id=?",(self.jobs[0],))
        self.poll()
        self.assertTrue(self.source.exists())
        self.assertNotIn(self.vid,self.page._pipe_exports)

    def test_changed_clip_list_keeps_source(self):
        db.execute("UPDATE clips SET status='archived' WHERE id=?",(self.clips[0],))
        self.poll()
        self.assertTrue(self.source.exists())

    def test_locked_source_retries_after_handle_released(self):
        with self.source.open('rb'):
            self.poll()
            self.assertTrue(self.source.exists())
            self.assertIn(MARK_STUCK,db.query_one('SELECT note FROM pipeline_files WHERE id=?',(self.entry,))['note'])
        self.assertEqual(StudioPage._pipe_retry_stuck(self.page),1)
        self.assertFalse(self.source.exists())

    def test_replaced_source_is_not_moved_as_old_video(self):
        self.source.write_bytes(b'NEW UNPROCESSED VIDEO WITH SAME NAME')
        self.poll()
        self.assertTrue(self.source.exists(),'New source was moved using export results of old source')

    def test_stuck_retry_does_not_move_new_file_with_same_name(self):
        P.mark_done(self.entry,self.vid,'2 part'+MARK_STUCK)
        self.source.write_bytes(b'NEW UNPROCESSED VIDEO AFTER RESTART')
        StudioPage._pipe_retry_stuck(self.page)
        self.assertTrue(self.source.exists(),'Stuck retry moved new video without checking its hash')

    def test_stuck_retry_checks_parts_still_present(self):
        P.mark_done(self.entry,self.vid,'2 part'+MARK_STUCK)
        self.parts[1].unlink()
        StudioPage._pipe_retry_stuck(self.page)
        self.assertTrue(self.source.exists(),'Stuck retry moved original despite a missing output Part')

    def test_resume_honors_cancel_on_any_part_not_only_last(self):
        db.insert('INSERT INTO jobs(type,project_id,video_id,status,payload) VALUES(?,?,?,?,?)',
                  ('auto',self.pid,self.vid,'done','{}'))
        db.execute("UPDATE jobs SET status='canceled' WHERE id=?",(self.jobs[0],))
        page = types.SimpleNamespace(_pipe_root=lambda:str(self.folder),_pipe_paths_in_flight=lambda:set(),
             _pipe_log=self.logs.append,_pipe_cut={},_pipe_by_vid={},_pending_export={},
             _tpl_for_project=lambda pid:{},_auto_tpl={})
        with patch.object(P,'list_taken',return_value=[r for r in P.list_taken() if r['id']==self.entry]):
            StudioPage._pipe_resume_taken(page)
        self.assertNotIn(self.vid,page._pending_export.values(),'Restart resumed exports although an earlier Part was canceled')

    def test_retry_new_attempt_overrides_old_canceled_clip(self):
        from app.core.pipeline_safety import latest_export_states
        db.execute("UPDATE jobs SET status='canceled' WHERE id=?", (self.jobs[0],))
        db.insert('INSERT INTO jobs(type,project_id,video_id,status,payload) VALUES(?,?,?,?,?)',
                  ('m1_export_clip',self.pid,self.vid,'done',db.dumps({'clip_id':self.clips[0]})))
        self.assertNotIn('canceled', latest_export_states(self.vid).values())
        self.page._pipe_exports[self.vid]['jobs'].remove(self.jobs[0])
        self.poll()
        self.assertFalse(self.source.exists())

    def test_old_archived_clip_cancellation_does_not_block_current_attempt(self):
        from app.core.pipeline_safety import latest_export_states
        old = db.insert('INSERT INTO clips(video_id,start_sec,end_sec,status) VALUES(?,0,1,?)',
                        (self.vid,'archived'))
        db.insert('INSERT INTO jobs(type,project_id,video_id,status,payload) VALUES(?,?,?,?,?)',
                  ('m1_export_clip',self.pid,self.vid,'canceled',db.dumps({'clip_id':old})))
        self.assertNotIn('canceled',latest_export_states(self.vid).values())

    def test_stuck_retry_rejects_different_clip_set_with_same_count(self):
        from app.core.pipeline_safety import parts_note
        P.mark_done(self.entry,self.vid,'2 part'+MARK_STUCK+parts_note(self.clips))
        db.execute("UPDATE clips SET status='archived' WHERE id=?",(self.clips[0],))
        db.insert('INSERT INTO clips(video_id,start_sec,end_sec,status,export_path) VALUES(?,0,1,?,?)',
                  (self.vid,'exported',str(self.parts[0])))
        StudioPage._pipe_retry_stuck(self.page)
        self.assertTrue(self.source.exists())

    def test_changed_source_directory_does_not_clean_unrelated_file(self):
        new_dir=self.folder/'new-input'
        new_dir.mkdir()
        replacement=new_dir/self.source.name
        replacement.write_bytes(self.source.read_bytes())
        db.execute('UPDATE projects SET pipe_src=? WHERE id=?',(str(new_dir),self.pid))
        P.mark_done(self.entry,self.vid,'2 part'+MARK_STUCK)
        StudioPage._pipe_retry_stuck(self.page)
        self.assertTrue(replacement.exists())
        self.assertTrue(self.source.exists())

    def test_real_ui_auto_export_two_channels_and_recycle_after_last_part(self):
        state = AppState()
        page = StudioPage(state)
        for timer in page.findChildren(QTimer):
            timer.stop()
        page._pipe_report=[]
        page._settings.setValue('pipe_recycle_dir',str(self.folder/'recycle'))
        page.auto_export_chk.setChecked(False)  # pipeline must still force export
        page.layout_tpl={'captions':False,'layers':[],'hieu_ung':'tat','chuyen_canh':'tat',
                         'fx_fade':False,'fx_whoosh':False,'_ten_mau':'audit'}
        samples=[]
        for index in range(2):
            source=self.folder/f'channel{index}'/'source.mp4'
            source.parent.mkdir()
            subprocess.run([str(ROOT/'bin/ffmpeg.exe'),'-y','-v','error','-f','lavfi','-i',
                 'testsrc=size=320x240:rate=15:duration=4','-f','lavfi','-i',
                 f'sine=frequency={440+index*100}:duration=4','-c:v','libx264','-pix_fmt','yuv420p',
                 '-c:a','aac','-shortest',str(source)],check=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
            pid=services.create_project(f'audit batch {index} | channel')
            db.execute('UPDATE projects SET pipe_src=?,export_dir=? WHERE id=?',
                       (str(source.parent),str(self.folder/f'output{index}'),pid))
            self.assertTrue(page._pipe_take(pid,f'audit batch {index} | channel','auto',source))
            jid=next(j for j,c in page._pipe_cut.items() if c['pid']==pid)
            ctx=page._pipe_cut[jid]; vid=ctx['vid']
            for number in range(2):
                db.insert('INSERT INTO clips(video_id,start_sec,end_sec,title,signals,status) VALUES(?,?,?,?,?,?)',
                    (vid,number*2,number*2+2,f'Fixture {index} {number}',
                     db.dumps({'llm_used':True,'title_en':f'Fixture {index} {number}'}),'suggested'))
            db.execute("UPDATE jobs SET status='done' WHERE id=?",(jid,))  # controlled AI output; no API
            samples.append((source,vid,ctx['entry']))
        original=services.enqueue_export
        def compact(*args,**kwargs):
            kwargs.update(out_w=320,out_h=240,mode='center',captions=False,overlay_png=None,
                          ovl_spec=None,text_overlays=None,video_rect=None,fx_fade=False,fx_whoosh=False,
                          hieu_ung='tat',chuyen_canh='tat',bgm_path='')
            return original(*args,**kwargs)
        try:
            with patch.object(services,'enqueue_export',side_effect=compact):
                page._check_auto_export()
            for source,vid,entry in samples:
                self.assertIn(vid,page._pipe_exports)
                jobs=sorted(page._pipe_exports[vid]['jobs'])
                self.assertEqual(len(jobs),2)
                for number,jid in enumerate(jobs):
                    row=db.query_one('SELECT type,payload FROM jobs WHERE id=?',(jid,))
                    state.pool._run_job(jid,row['type'],row['payload'])
                    status=db.query_one('SELECT status,error FROM jobs WHERE id=?',(jid,))
                    self.assertEqual(status['status'],'done',status['error'])
                    page._pipe_poll_exports()
                    self.assertEqual(source.exists(),number==0)
                parts=db.query('SELECT export_path FROM clips WHERE video_id=? ORDER BY start_sec',(vid,))
                for row in parts:
                    info=probe(row['export_path'])
                    self.assertTrue(info.has_audio)
                    self.assertTrue(1.8 <= info.duration <= 2.4,info)
                self.assertEqual(db.query_one('SELECT status FROM pipeline_files WHERE id=?',(entry,))['status'],'done')
        finally:
            state.pool.stop(wait=True)
            page.close()


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PipelineAudit))
    summary={'area':str(AREA),'tests':result.testsRun,'failures':[(str(t),msg) for t,msg in result.failures],
             'errors':[(str(t),msg) for t,msg in result.errors],'ok':result.wasSuccessful()}
    (AREA/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (AREA.parent/'latest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REPORT',AREA/'result.json',flush=True)
    os._exit(0 if result.wasSuccessful() else 1)
