"""Offline English-source/Vietnamese-output contract and settings regressions."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(os.environ.get('BQ_SOURCE_ROOT') or Path(__file__).resolve().parents[1])
AREA=Path(tempfile.mkdtemp(prefix='bq_language_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard
import app.queue.jobs
from PyQt6.QtWidgets import QApplication,QMessageBox
from app.ui.recap_settings import RecapSettingsDialog
from app.ui.appsettings import app_settings
from app.ai import story_quality as q
from app.core.dubbing import default_voice
from app.database import db
from app import services

app=QApplication([])
ERRORS=[]
sys.excepthook=lambda kind,error,tb:ERRORS.append(str(error))

class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.settings=app_settings();self.settings.clear();self.dialogs=[]
        self.network=patch.object(RecapSettingsDialog,'_fill_voices_bg');self.network.start()
        self.popup=patch.object(QMessageBox,'information');self.popup.start()

    def tearDown(self):
        for dlg in self.dialogs:dlg.close();dlg.deleteLater()
        app.processEvents();self.network.stop();self.popup.stop()
        self.assertFalse(ERRORS,ERRORS)

    def dialog(self,**kwargs):
        dlg=RecapSettingsDialog(**kwargs);self.dialogs.append(dlg);return dlg

    def test_saved_vietnamese_target_english_voice_repaired_before_start(self):
        self.settings.setValue('story_lang','vi');self.settings.setValue('recap_voice','en-US-GuyNeural')
        dlg=self.dialog(story_start=True)
        self.assertEqual(dlg.story_lang.currentData(),'vi')
        self.assertEqual(dlg.voice.currentData(),'')
        self.assertIn('Giọng cũ',dlg.language_note.text())
        self.assertIn('vi-VN-',dlg.language_note.text())
        # Merely opening the dialog must not mutate saved settings.
        self.assertEqual(self.settings.value('recap_voice'),'en-US-GuyNeural')
        dlg._set_voices([('Guy','en-US-GuyNeural'),('Hoài My','vi-VN-HoaiMyNeural')])
        self.assertEqual(dlg.voice.currentData(),'')
        with patch('config.update_env'):
            dlg._save()
        self.assertEqual(self.settings.value('story_lang'),'vi')
        self.assertEqual(self.settings.value('recap_voice'),'')

    def test_language_change_keeps_compatible_voice_and_resets_incompatible(self):
        dlg=self.dialog(story_start=True)
        dlg._set_voices([('Guy','en-US-GuyNeural'),('Nam Minh','vi-VN-NamMinhNeural')])
        dlg.voice.setCurrentIndex(dlg.voice.findData('en-US-GuyNeural'))
        dlg.story_lang.setCurrentIndex(dlg.story_lang.findData('vi'))
        self.assertEqual(dlg.voice.currentData(),'')
        dlg.voice.setCurrentIndex(dlg.voice.findData('vi-VN-NamMinhNeural'))
        dlg._output_language_changed()
        self.assertEqual(dlg.voice.currentData(),'vi-VN-NamMinhNeural')

    def test_invalid_explicit_voice_cannot_save_or_start(self):
        dlg=self.dialog(story_start=True)
        dlg.story_lang.setCurrentIndex(dlg.story_lang.findData('vi'))
        dlg.voice.addItem('Guy','en-US-GuyNeural');dlg.voice.setCurrentIndex(dlg.voice.count()-1)
        with patch.object(QMessageBox,'warning') as warning,patch('config.update_env') as write:
            dlg._save()
        warning.assert_called_once();write.assert_not_called()
        self.assertEqual(dlg.result(),0)
        self.assertIsNone(self.settings.value('story_lang'))

    def test_multilingual_voice_is_retained(self):
        self.settings.setValue('recap_voice','en-US-AndrewMultilingualNeural')
        dlg=self.dialog(story_start=True)
        dlg.story_lang.setCurrentIndex(dlg.story_lang.findData('vi'))
        self.assertEqual(dlg.voice.currentData(),'en-US-AndrewMultilingualNeural')

    def test_explicit_auto_choice_survives_voice_list_reload(self):
        self.settings.setValue('recap_voice','vi-VN-NamMinhNeural')
        self.settings.setValue('story_lang','vi')
        dlg=self.dialog(story_start=True)
        dlg.voice.setCurrentIndex(0)
        dlg._set_voices([('Nam Minh','vi-VN-NamMinhNeural')])
        dlg.search.setText('Nam Minh')
        self.assertEqual(dlg.voice.currentData(),'')

    def test_legacy_selector_explains_scope_and_voice_only_still_works(self):
        dlg=self.dialog()
        self.assertFalse(dlg.story_lang.isEnabled())
        self.assertIn('Bật AI dựng chuyện',dlg.language_note.text())
        voice=self.dialog(voice_only=True,initial_voice='vi-VN-NamMinhNeural')
        voice._set_voices([('Nam Minh','vi-VN-NamMinhNeural')])
        self.assertEqual(voice.voice.currentData(),'vi-VN-NamMinhNeural')

    def test_language_control_is_above_voice_and_visible(self):
        dlg=self.dialog(story_start=True);dlg.show();app.processEvents()
        self.assertLess(dlg.story_lang.y(),dlg.voice.y())
        self.assertTrue(dlg.story_lang.visibleRegion().isEmpty() is False)

    def test_preview_uses_target_language_with_auto_and_multilingual_voice(self):
        dlg=self.dialog(story_start=True)
        dlg.story_lang.setCurrentIndex(dlg.story_lang.findData('vi'))
        for voice in ('','en-US-AndrewMultilingualNeural'):
            if voice:dlg.voice.addItem(voice,voice);dlg.voice.setCurrentIndex(dlg.voice.count()-1)
            with patch('app.ui.recap_settings.threading.Thread') as thread,patch('app.core.dubbing.synth_demo',return_value=False) as synth:
                dlg._preview();thread.call_args.kwargs['target']()
            self.assertEqual(synth.call_args.args[0],voice or default_voice('vi'))
            self.assertIn('Không ai ngờ',synth.call_args.kwargs['text'])

    def test_english_evidence_vietnamese_script_voice_and_persisted_contract(self):
        db.execute('DELETE FROM projects')
        pid=services.create_project('language test','Test')
        src=AREA/'source.mp4';src.write_bytes(b'fixture')
        vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,72)',(pid,str(src)))
        transcript={'language':'en','text':'A woman shows a blue card.',
                    'segments':[{'start':0,'end':72,'text':'A woman shows a blue card.'}]}
        evidence=[{'id':0,'start':0,'end':72,'transcript':transcript['text']}]
        parts=[{'start':0,'end':72,'mode':'narrate','text':'Người phụ nữ đưa ra một tấm thẻ màu xanh.'}]
        plan={'title':'Tấm thẻ màu xanh','parts':parts,'windows':[[0,72]],'duration':72,'review':{}}
        def analysis(_vid,kind):return transcript if kind=='transcript' else {}
        with patch.object(q.llm,'is_configured',return_value=True),patch.object(q.llm,'vision_available',return_value=True),\
             patch('app.core.analysis.get_analysis',side_effect=analysis),\
             patch.object(q,'build_evidence',return_value=(evidence,q.source_signature(src),'key')) as build,\
             patch('app.ai.story_director.direct',return_value=([plan],{})) as direct:
            result=q.generate({'video_id':vid,'preset':{'story_lang':'vi','recap_voice':'','recap_count':1}},Mock())
        self.assertEqual(direct.call_args.args[5],'Vietnamese')
        self.assertEqual(build.call_args.args[3],transcript['segments'])
        meta=db.loads(db.query_one('SELECT signals FROM clips WHERE id=?',(result['clip_ids'][0],))['signals'],{})['recap']
        self.assertEqual(meta['lang'],'vi');self.assertEqual(meta['voice'],default_voice('vi'))
        self.assertEqual(meta['parts'][0]['text'],parts[0]['text'])
        self.assertEqual(transcript['language'],'en');self.assertFalse(q.is_approved(meta))

    def test_vietnamese_narration_export_keeps_target_voice_and_source(self):
        import subprocess
        from config import settings
        from app.core import dubbing as d
        db.execute('DELETE FROM projects')
        self.pid=services.create_project('Vietnamese export','Test')
        from app.queue.worker import WorkerPool
        from app.queue.resource_manager import PROFILE,profile_dict
        from app.core.ffmpeg_utils import probe
        source=AREA/'export_source.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i',
            'testsrc=size=320x240:rate=15:duration=72','-f','lavfi','-i','sine=frequency=220:duration=72',
            '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True,timeout=30)
        vid=services.import_video(self.pid,str(source))
        evidence=[dict(id=0,start=0,end=32,observations=[],transcript='A blue card.'),
                  dict(id=1,start=40,end=72,observations=[],transcript='A blue card.')]
        text='Một tấm thẻ màu xanh xuất hiện.'
        draft={'title':'Tấm thẻ màu xanh','shots':[{'source_id':i,'mode':'narrate','text':text} for i in (0,1)]}
        plan=q.validate_plan(draft,evidence,set(),64,64)
        meta=dict(quality_story=q.VERSION,parts=plan['parts'],windows=plan['windows'],voice='vi-VN-NamMinhNeural',
                  lang='vi',source_signature=q.source_signature(source),contract=q.contract(plan['parts'],plan['windows']))
        cid=db.insert("INSERT INTO clips(video_id,start_sec,end_sec,title,signals,status) VALUES(?,0,72,'Story export',?,'suggested')",
                      (vid,db.dumps({'recap':meta,'segments':plan['windows'],'dur':64})))
        async def synth(texts,voice,paths,**kwargs):
            self.assertEqual(voice,'vi-VN-NamMinhNeural')
            self.assertTrue(all(t==text for t in texts))
            for path in paths:
                subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','sine=frequency=600:duration=1.5',
                                '-f','wav',str(path)],check=True,timeout=15)
            return [True]*len(texts),[[[0,1.4,text]] for _ in texts]
        pool=WorkerPool(profile_dict(PROFILE))
        try:
            blocked=services.enqueue_export(pool,cid,vid,self.pid,out_w=320,out_h=240,out_dir=str(AREA/'blocked'),flat_export=True)
            db.execute('UPDATE jobs SET max_attempts=1 WHERE id=?',(blocked,))
            blocked_job=db.query_one('SELECT type,payload FROM jobs WHERE id=?',(blocked,))
            with patch.object(d,'_synth_all_words') as tts:
                pool._run_job(blocked,blocked_job['type'],blocked_job['payload'])
                tts.assert_not_called()
            blocked_result=db.query_one('SELECT status,error FROM jobs WHERE id=?',(blocked,))
            self.assertEqual(blocked_result['status'],'failed');self.assertIn('Chờ duyệt',blocked_result['error'])
            self.assertTrue(source.exists())
            q.approve_script(cid,q.digest(meta),[p['text'] for p in plan['parts']])
            jid=services.enqueue_export(pool,cid,vid,self.pid,out_w=320,out_h=240,mode='center',captions=True,
                out_dir=str(AREA/'output'),part_no=1,flat_export=True,fx_fade=False,fx_whoosh=False,
                hieu_ung='tat',chuyen_canh='tat')
            job=db.query_one('SELECT type,payload FROM jobs WHERE id=?',(jid,))
            with patch.object(d,'_synth_all_words',side_effect=synth):pool._run_job(jid,job['type'],job['payload'])
            result=db.query_one('SELECT status,error,result FROM jobs WHERE id=?',(jid,))
            self.assertEqual(result['status'],'done',result['error'])
            info=probe(db.loads(result['result'])['export_path'])
            self.assertAlmostEqual(info.duration,64,delta=.3);self.assertTrue(info.has_audio)
            saved=db.loads(db.query_one('SELECT signals FROM clips WHERE id=?',(cid,))['signals'])
            self.assertEqual(len(saved['recap']['rendered_parts']),2)
            self.assertIn('da_ap',saved)
            self.assertTrue(source.exists())
        finally:pool.stop(wait=True)

if __name__=='__main__':unittest.main(verbosity=2)
