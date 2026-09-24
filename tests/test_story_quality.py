"""Evidence contracts, atomic multi-Part creation and non-truncating audio, offline."""
import os
from pathlib import Path
import tempfile
import sys
import json
import subprocess
import unittest
import wave
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_story_test_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),
                  QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: F401,E402
import app.queue.jobs  # noqa: F401,E402
from app.ai import story_quality as q
from app.core import dubbing as d
from app.core.story_audio import fit_narration_text
from app.database import db
from app import services
from config import settings


def wav(path,seconds):
    with wave.open(str(path),'wb') as f:
        f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(b'\0\0'*int(seconds*16000))


def units(duration=72):
    return [dict(u,transcript='A blue card is shown.',observations=[{'visible':'Blue card','uncertain':'No identity known'}]) for u in q.coverage(duration)]


def draft(ids):
    return {'title':'The blue card','shots':[{'source_id':i,'mode':'narrate','text':'A blue card appears.','sfx':'transition'} for i in ids]}


class StoryQuality(unittest.TestCase):
    def setUp(self):
        db.execute('DELETE FROM projects');self.ctx=Mock();self.src=AREA/'source.mp4';self.src.write_bytes(b'fixture')
        self.pid=services.create_project('Story test','Test')
        self.vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,72)',(self.pid,str(self.src)))

    def review_fixture(self):
        evidence=[dict(units()[0],start=0,end=36),dict(units()[1],start=36,end=72)]
        p=q.validate_plan(draft([0,1]),evidence,set(),72,72)
        meta=dict(quality_story=q.VERSION,parts=p['parts'],windows=p['windows'],voice='en-US-GuyNeural',lang='en',
                  source_signature=q.source_signature(self.src),contract=q.contract(p['parts'],p['windows']))
        cid=db.insert("INSERT INTO clips(video_id,start_sec,end_sec,signals) VALUES(?,0,72,?)",(self.vid,db.dumps({'recap':meta,'segments':p['windows']})))
        return cid,meta

    def test_human_approval_required_and_bound_to_words_voice_and_windows(self):
        cid,meta=self.review_fixture()
        self.assertEqual(q.pending_review(self.vid),[cid])
        with self.assertRaisesRegex(RuntimeError,'Chờ duyệt'):q.verify_export(meta,meta['windows'],self.src)
        approved=q.approve_script(cid,q.digest(meta),['One blue card.','It is on screen.'])
        q.verify_export(approved,approved['windows'],self.src)
        self.assertEqual(q.pending_review(self.vid),[])
        approved['voice']='another voice'
        with self.assertRaisesRegex(RuntimeError,'Chờ duyệt'):q.verify_export(approved,approved['windows'],self.src)

    def test_default_duration_and_speed_cannot_produce_short_part(self):
        self.assertEqual(q.length_limits({}),(61,120))
        self.assertEqual(q.length_limits({'min_len':30,'max_len':90}),(61,90))
        cid,meta=self.review_fixture()
        approved=q.approve_script(cid,q.digest(meta),[p['text'] for p in meta['parts']])
        q.verify_export(approved,approved['windows'],self.src,1)
        with self.assertRaisesRegex(RuntimeError,'trên 60 giây'):q.verify_export(approved,approved['windows'],self.src,1.2)

    def test_short_source_or_too_many_parts_stops_before_vision_calls(self):
        with patch.object(q.llm,'is_configured',return_value=True),patch.object(q.llm,'vision_available',return_value=True),patch.object(q,'build_evidence') as vision:
            with self.assertRaisesRegex(RuntimeError,'không đủ thời lượng'):
                q.generate({'video_id':self.vid,'preset':{'recap_count':2}},self.ctx)
            vision.assert_not_called()

    def test_stale_dialog_and_active_jobs_cannot_overwrite_review(self):
        cid,meta=self.review_fixture();texts=[p['text'] for p in meta['parts']]
        jid=db.insert("INSERT INTO jobs(type,video_id,status) VALUES('m1_export_clip',?,'pending')",(self.vid,))
        with self.assertRaisesRegex(RuntimeError,'đang có việc'):q.approve_script(cid,q.digest(meta),texts)
        db.execute("UPDATE jobs SET status='canceled' WHERE id=?",(jid,))
        q.approve_script(cid,q.digest(meta),texts)
        with self.assertRaisesRegex(RuntimeError,'đã thay đổi'):q.approve_script(cid,q.digest(meta),texts)

    def test_editing_review_invalidates_old_export_without_deleting_file(self):
        from app.core.pipeline_safety import parts_problem
        cid,meta=self.review_fixture();approved=q.approve_script(cid,q.digest(meta),[p['text'] for p in meta['parts']])
        output=AREA/'previous.mp4';output.write_bytes(b'previous file')
        approved['exported_approval']=q.approval_signature(approved)
        db.execute("UPDATE clips SET status='exported',export_path=?,signals=? WHERE id=?",(str(output),db.dumps({'recap':approved,'segments':approved['windows']}),cid))
        self.assertEqual(parts_problem(self.vid),'')
        edited=q.approve_script(cid,q.digest(approved),['A single blue card.','No other object.'])
        self.assertNotIn('exported_approval',edited)
        self.assertIn('giữ video gốc',parts_problem(self.vid))
        self.assertIsNone(db.query_one('SELECT export_path FROM clips WHERE id=?',(cid,))['export_path'])
        self.assertTrue(output.exists());self.assertTrue(self.src.exists())

    def test_approved_overlong_speech_never_rewrites_or_trims(self):
        path=AREA/'approved-long.wav';wav(path,6)
        with patch.object(q,'shorten') as shorter:
            with self.assertRaisesRegex(RuntimeError,'lời đã duyệt'):
                fit_narration_text('Keep these words.','evidence',2,str(path),'en-US-GuyNeural','en','+0%','+0Hz',allow_rewrite=False)
            shorter.assert_not_called()

    def test_strict_voice_language_mismatch_is_explicit_not_silent_switch(self):
        with patch.object(d,'_synth_all_words') as tts:
            with self.assertRaisesRegex(RuntimeError,'khác ngôn ngữ'):
                d.build_recap_track([dict(start=0,end=4,mode='narrate',text='Keep This Text.')],[[0,4]],
                    'vi-VN-NamMinhNeural','en',str(AREA/'mismatch.wav'),strict=True,allow_rewrite=False)
            tts.assert_not_called()

    def test_auto_pipeline_waits_after_restart_then_resumes_after_all_approvals(self):
        from types import SimpleNamespace
        from app.ui.studio_page import StudioPage
        cid,meta=self.review_fixture()
        jid=db.insert("INSERT INTO jobs(type,video_id,status) VALUES('auto_recap',?,'done')",(self.vid,))
        def page():
            return SimpleNamespace(_pending_export={jid:self.vid},_auto_tpl={jid:{}},_pipe_by_vid={self.vid:{}},
                status=Mock(),_pipe_log=Mock(),_video_cut_basic=Mock(return_value=False),_export_video=Mock(return_value=1),
                _pipe_on_exported=Mock(),_pipe_on_export_failed=Mock())
        first=page();StudioPage._check_auto_export_inner(first)
        first._export_video.assert_not_called();first._pipe_on_exported.assert_not_called()
        restarted=page();StudioPage._check_auto_export_inner(restarted)
        restarted._export_video.assert_not_called();self.assertIn(jid,restarted._pending_export)
        q.approve_script(cid,q.digest(meta),[p['text'] for p in meta['parts']])
        StudioPage._check_auto_export_inner(restarted)
        restarted._export_video.assert_called_once();restarted._pipe_on_exported.assert_called_once()
        self.assertFalse(restarted._pending_export);self.assertTrue(self.src.exists())

    def test_full_coverage_no_twelve_frame_cap_and_finite_bounds(self):
        rows=q.coverage(1201,[5,19,400,float('nan')])
        self.assertGreater(len(rows),100);self.assertEqual(rows[0]['start'],0);self.assertEqual(rows[-1]['end'],1201)
        for a,b in zip(rows,rows[1:]):self.assertEqual(a['end'],b['start'])
        self.assertTrue(all(0<r['end']-r['start']<=12 for r in rows))
        for bad in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):q.coverage(bad)

    def test_reject_unknown_duplicate_reorder_used_or_wrong_duration(self):
        for ids in ([0,99],[0,0],[2,1],[0,1]):
            with self.assertRaises(ValueError):q.validate_plan(draft(ids),units(),{0},24,40)
        with self.assertRaises(ValueError):q.validate_plan(draft([1]),units(),set(),25,40)
        p=q.validate_plan(draft([0,1]),units(),set(),24,40)
        self.assertEqual(p['windows'],[[0.,12.],[12.,24.]])

    def test_malformed_modes_empty_text_and_missing_hook_fail(self):
        for mode,text in [('unknown','x'),('narrate',''),('orig','')]:
            raw=draft([0,1]);raw['shots'][0].update(mode=mode,text=text)
            with self.assertRaises(ValueError):q.validate_plan(raw,units(),set(),24,40)

    def test_every_claim_must_pass_local_evidence_check(self):
        p=q.validate_plan(draft([0,1]),units(),set(),24,40)
        with patch.object(q.llm,'complete_json',return_value={'supported':True,'matches_scene':False}):
            with self.assertRaisesRegex(ValueError,'khớp cảnh'):q.review_plan(p,units(),self.ctx)

    def test_global_hook_review_rejects_string_true(self):
        p=q.validate_plan(draft([0,1]),units(),set(),24,40)
        def call(prompt,**_):
            return {'supported':True,'matches_scene':True} if prompt.startswith('Verify each') else {'approved':'true'}
        with patch.object(q.llm,'complete_json',side_effect=call):
            with self.assertRaisesRegex(ValueError,'đối chiếu'):q.review_plan(p,units(),self.ctx)

    def test_three_failed_reviews_return_flagged_draft_for_human_not_auto_approval(self):
        with patch.object(q.llm,'complete_json',return_value=draft([0,1])),patch.object(q,'review_plan',side_effect=ValueError('unsupported')) as review:
            result=q.write_part(units(),[],set(),{'min_len':24,'max_len':40},0,1,'English',self.ctx)
            self.assertFalse(result['review']['approved']);self.assertIn('unsupported',result['review']['issues'])
            self.assertNotIn('human_approval',result)
            self.assertEqual(review.call_count,3)

    def test_structurally_invalid_drafts_never_become_reviewable_parts(self):
        with patch.object(q.llm,'complete_json',return_value=draft([999])):
            with self.assertRaisesRegex(RuntimeError,'mốc cảnh hợp lệ'):
                q.write_part(units(),[],set(),{'min_len':24,'max_len':40},0,1,'English',self.ctx)

    def test_partial_evidence_cache_resumes_and_source_change_invalidates(self):
        def make(src,u,transcript,ctx):return dict(u,transcript=transcript,observations=[])
        with patch.object(q,'visual_evidence',side_effect=make) as vision:
            first=q.build_evidence(self.vid,str(self.src),24,[],{},self.ctx)
            q.build_evidence(self.vid,str(self.src),24,[],{},self.ctx)
            self.assertEqual(vision.call_count,2)
            self.src.write_bytes(b'changed source')
            second=q.build_evidence(self.vid,str(self.src),24,[],{},self.ctx)
            self.assertEqual(vision.call_count,4);self.assertNotEqual(first[2],second[2])

    def test_failed_visual_call_never_commits_complete_cache(self):
        with patch.object(q,'visual_evidence',side_effect=RuntimeError('provider unavailable')):
            with self.assertRaises(RuntimeError):q.build_evidence(self.vid,str(self.src),24,[],{},self.ctx)
        self.assertEqual(db.query('SELECT * FROM clips'),[])

    def test_export_detects_source_or_script_changes(self):
        p=q.validate_plan(draft([0,1]),units(),set(),24,40)
        meta=dict(parts=p['parts'],source_signature=q.source_signature(self.src),contract=q.contract(p['parts'],p['windows']))
        q.verify_export(meta,p['windows'],str(self.src))
        meta['parts'][0]['text']='An invented event.'
        with self.assertRaises(RuntimeError):q.verify_export(meta,p['windows'],str(self.src))
        meta['contract']=q.contract(meta['parts'],p['windows']);self.src.write_bytes(b'new')
        with self.assertRaises(RuntimeError):q.verify_export(meta,p['windows'],str(self.src))

    def test_multi_part_commits_together_without_duplicate_ranges(self):
        all_units=units(144);signature=q.source_signature(self.src)
        db.execute('UPDATE videos SET duration=144 WHERE id=?',(self.vid,))
        def write(pool,context,used,preset,index,count,lang,ctx):
            p=q.validate_plan(draft([u['id'] for u in pool]),pool,used,61,80);p['review']={'approved':True};return p
        with patch.object(q.llm,'is_configured',return_value=True),patch.object(q.llm,'vision_available',return_value=True),\
             patch.object(q,'build_evidence',return_value=(all_units,signature,'key')),patch.object(q,'overview',return_value=[]),patch.object(q,'write_part',side_effect=write):
            result=q.generate({'video_id':self.vid,'preset':{'recap_count':2,'min_len':61,'max_len':80}},self.ctx)
        self.assertEqual(result['count'],2)
        rows=db.query('SELECT signals FROM clips ORDER BY id')
        a,b=[json.loads(r['signals']) for r in rows]
        self.assertLessEqual(a['segments'][-1][1],b['segments'][0][0])
        self.assertEqual(a['recap']['voice'],b['recap']['voice'])

    def test_second_part_failure_leaves_no_partial_clips(self):
        db.execute('UPDATE videos SET duration=144 WHERE id=?',(self.vid,))
        p=q.validate_plan(draft([0,1]),units(),set(),24,40);p['review']={}
        with patch.object(q.llm,'is_configured',return_value=True),patch.object(q.llm,'vision_available',return_value=True),\
             patch.object(q,'build_evidence',return_value=(units(144),q.source_signature(self.src),'key')),\
             patch.object(q,'overview',return_value=[]),patch.object(q,'write_part',side_effect=[p,RuntimeError('bad second part')]):
            with self.assertRaises(RuntimeError):q.generate({'video_id':self.vid,'preset':{'recap_count':2}},self.ctx)
        self.assertEqual(db.query('SELECT * FROM clips'),[])

    def test_real_ffmpeg_strict_fit_keeps_sentence_or_refuses(self):
        source=AREA/'voice.wav';out=AREA/'fitted.wav';wav(source,3)
        with self.assertRaisesRegex(RuntimeError,'cắt cụt'):
            d._fit_recap_chunk(str(source),str(out),1,tempo_max=1.15,allow_trim=False)
        final,natural,tempo=d._fit_recap_chunk(str(source),str(out),4,tempo_max=1.15,allow_trim=False)
        self.assertAlmostEqual(final,3,delta=.1);self.assertEqual(tempo,1)

    def test_overflow_rewrites_and_revoices_with_new_word_timing(self):
        path=AREA/'overflow.wav';wav(path,6)
        async def synth(texts,voice,paths,**kwargs):
            wav(paths[0],1.5);return [True],[[{'text':'Short.','start':0,'end':1}]]
        with patch.object(q,'shorten',return_value='Short.') as shorter,patch.object(d,'_synth_all_words',side_effect=synth):
            text,words=fit_narration_text('A long complete sentence.','evidence',2,str(path),'en-US-GuyNeural','en','+0%','+0Hz')
        self.assertEqual(text,'Short.');self.assertTrue(words);shorter.assert_called_once()

    def test_shortening_is_rejected_without_verification(self):
        with patch.object(q.llm,'complete_json',side_effect=[{'text':'Short.'},{'approved':False}]):
            with self.assertRaises(RuntimeError):q.shorten('A long original sentence.','evidence',2)

    def test_visual_sampling_runs_real_frame_extraction(self):
        source=AREA/'real.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:d=2',str(source)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        def vision(prompt,paths,**kwargs):
            self.assertEqual(len(paths),1)
            self.assertTrue(all(Path(p).stat().st_size>0 for p in paths));return {'visible':'Blue image','uncertain':'No visible action'}
        with patch.object(q.llm,'complete_vision_json',side_effect=vision) as model:
            result=q.visual_evidence(str(source),{'id':0,'start':0,'end':2},'',self.ctx)
            self.assertEqual(model.call_count,3);self.assertEqual(len(result['observations']),3)

    def test_legacy_recap_dispatch_is_explicit(self):
        from app.modules.m2_recap import generate_recap
        with patch.object(q,'generate',return_value={'quality':True}) as generate:
            self.assertEqual(generate_recap({'video_id':self.vid,'preset':{'story_quality':True}},self.ctx),{'quality':True})
            generate.assert_called_once()

    def test_long_cjk_inputs_are_batched_and_oversized_call_is_not_sent(self):
        items=[{'id':i,'note':'映像の説明。'*100} for i in range(70)]
        blocks=q.evidence_batches(items)
        self.assertEqual(sum(len(b) for b in blocks),len(items))
        self.assertTrue(all(q.token_size(b)<=3000 for b in blocks))
        with patch.object(q.llm,'complete_json') as api:
            with self.assertRaises(RuntimeError):q.ask('映'*7000)
            api.assert_not_called()

    def test_block_selection_has_enough_duration_and_excludes_used(self):
        source=units(240)
        def choose(prompt,**kwargs):
            choices=json.loads(prompt.split('\n',1)[1]);return {'id':choices[0]['id']}
        with patch.object(q.llm,'complete_json',side_effect=choose):
            pool,notes=q.choose_pool(source,25,60,{0,1},self.ctx)
        self.assertGreaterEqual(sum(u['end']-u['start'] for u in pool),25)
        self.assertLessEqual(sum(u['end']-u['start'] for u in pool),60)
        self.assertTrue(all(u['id'] not in (0,1) for u in pool))

    def test_gemini_strict_failure_never_changes_voice(self):
        with patch.object(d,'_gemini_tts',return_value=False),patch.object(d,'_synth_all') as fallback:
            self.assertEqual(d._synth_all_gemini(['Sentence.'],'gemini:Puck',['unused.wav'],'en',allow_fallback=False),[False])
            fallback.assert_not_called()

    def test_transient_provider_retries_without_masking_account_errors(self):
        with patch.object(q.time,'sleep'):
            request=Mock(side_effect=[q.llm.LLMError('Error code: 503 over capacity'),{'ok':True}])
            self.assertEqual(q.provider_call(request),{'ok':True});self.assertEqual(request.call_count,2)
            restricted=Mock(side_effect=q.llm.LLMError('organization_restricted'))
            with self.assertRaises(q.llm.LLMError):q.provider_call(restricted)
            self.assertEqual(restricted.call_count,1)

    def test_retired_vision_default_migrates_but_custom_model_is_kept(self):
        with patch.object(type(settings),'GROQ_VISION_MODEL','qwen/qwen3.6-27b'):
            self.assertEqual(q.llm.groq_vision_model(),'qwen/qwen3.8-27b')
        with patch.object(type(settings),'GROQ_VISION_MODEL','custom-model'):
            self.assertEqual(q.llm.groq_vision_model(),'custom-model')

    def test_strict_edge_failure_never_switches_backup_voice(self):
        async def fail(*args,**kwargs):return [False],[[]]
        parts=[{'start':0,'end':4,'mode':'narrate','text':'A blue card.'}]
        with patch.object(d,'_synth_all_words',side_effect=fail),patch.object(d.time,'sleep'),\
             patch.object(d,'_recap_backup_voice') as fallback:
            with self.assertRaisesRegex(RuntimeError,'Thiếu giọng'):
                d.build_recap_track(parts,[[0,4]],'en-US-GuyNeural','en',str(AREA/'failed.wav'),strict=True)
            fallback.assert_not_called()

    def test_real_export_with_strict_narration_two_source_windows_and_captions(self):
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
        plan=q.validate_plan(draft([0,1]),evidence,set(),64,64)
        meta=dict(quality_story=q.VERSION,parts=plan['parts'],windows=plan['windows'],voice='en-US-GuyNeural',
                  lang='en',source_signature=q.source_signature(source),contract=q.contract(plan['parts'],plan['windows']))
        cid=db.insert("INSERT INTO clips(video_id,start_sec,end_sec,title,signals,status) VALUES(?,0,72,'Story export',?,'suggested')",
                      (vid,db.dumps({'recap':meta,'segments':plan['windows'],'dur':64})))
        async def synth(texts,voice,paths,**kwargs):
            for path in paths:
                subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','sine=frequency=600:duration=1.5',
                                '-f','wav',str(path)],check=True,timeout=15)
            return [True]*len(texts),[[[0,1.4,'A blue card appears.']] for _ in texts]
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
            self.assertTrue(source.exists())
        finally:pool.stop(wait=True)


if __name__=='__main__':unittest.main(verbosity=2)
