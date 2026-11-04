"""Offline regression: real selection/storage/UI gates, synthetic AI responses."""
import contextlib, copy, os, sys, tempfile, types, unittest, wave
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
AREA=Path(tempfile.mkdtemp(prefix='part_policy_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard
from app.modules import m1_highlight as M
from app.ai import chon_doan as CD
from app.database.db import db
from app import services
from app.core import ffmpeg_utils as F, pipeline as P
from app.ui.studio_page import StudioPage
from app.queue import jobs, worker
from config import settings
from PyQt6.QtWidgets import QApplication
app=QApplication.instance() or QApplication([])

def clip(i,score):
    return dict(title=f'Story {i}',title_en=f'Story {i}',score=score,segments=[[100+i*180,170+i*180]],reason='fixture')

class PartPolicy(unittest.TestCase):
    def setUp(self):
        self.folder=AREA/self._testMethodName;self.folder.mkdir()
        self.pid=services.create_project(self._testMethodName)
        self.source=self.folder/'source.mp4';self.source.write_bytes(b'keep original')
        self.vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)',(self.pid,str(self.source),1200))
        self.tr=dict(language='en',text='A meaningful story with a turning point.',segments=[dict(start=i,end=i+5,text='The situation changed suddenly and the answer surprised everyone.') for i in range(0,1200,5)])
        self.ctx=types.SimpleNamespace(profile={},progress=Mock(),check_canceled=lambda:None)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        # No network can escape through text/vision/hashtag calls in these tests.
        for obj,name in [(M.llm,'complete_json'),(M.llm,'complete_text')]:
            self.stack.enter_context(patch.object(obj,name,side_effect=AssertionError('unexpected API call')))

    def generate(self,scores,critic=None,partial=False,judge=None):
        def select(*args,audit=None,**kwargs):
            audit.update(analysis_complete=not partial,chunks_total=2,chunks_failed=int(partial))
            return [clip(i,s) for i,s in enumerate(scores)],(['1/2 phần transcript gọi AI lỗi'] if partial else [])
        with contextlib.ExitStack() as st:
            for obj,name,value in [(M,'get_analysis',lambda v,k:self.tr if k=='transcript' else {}),(M,'load_used_ranges',lambda v:[]),(M,'_llm_select_clips',select),(M,'_polish_titles',lambda *a:0),(M._vd,'nen_xem_hinh',lambda v:False),(M._vd,'xem_hinh_kenh',lambda v:False),(CD,'co_loi_noi_that',lambda *a:(True,'',0)),(M.llm,'is_configured',lambda:True),(M.llm,'active_provider',lambda:'groq')]:
                st.enter_context(patch.object(obj,name,value))
            st.enter_context(patch('config.settings',types.SimpleNamespace(DEEP_SENSE=False,BLIND_JUDGE=judge is not None,JUDGE_PANEL=False,AI_MULTIPASS=critic is not None,HAU_KIEM_GHEP=False,QUALITY_FLOOR=55,FFMPEG_PATH=settings.FFMPEG_PATH)))
            if judge is not None:st.enter_context(patch.object(CD,'cham_mu',return_value=judge))
            if critic is not None:st.enter_context(patch.object(M.llm,'complete_json',return_value=critic))
            return M.generate_highlights({'video_id':self.vid,'preset':dict(count=3,min_len=60,max_len=180)},self.ctx)

    def test_three_good_candidates_store_three_parts(self):
        r=self.generate([90,85,80]);self.assertEqual(r['count'],3);self.assertTrue(r['auto_export_allowed'])
        self.assertEqual(len(services.list_clips(self.vid)),3)

    def test_low_scores_do_not_reduce_requested_count(self):
        r=self.generate([90,18,8]);self.assertEqual(r['count'],3)
        self.assertEqual(r['selection']['rejected_quality'],0)
        self.assertTrue(r['auto_export_allowed'])

    def test_single_weak_candidate_can_export_without_fabricating_parts(self):
        r=self.generate([18]);self.assertEqual(r['count'],1)
        self.assertTrue(r['auto_export_allowed'])
        row=db.query_one('SELECT signals FROM clips WHERE id=?',(r['clip_ids'][0],))
        self.assertFalse(db.loads(row['signals']).get('quality_review_required',False))

    def test_screenshot_three_low_judged_candidates_can_export(self):
        r=self.generate([90,85,80],dict(keep=[0,2],drop=[1]),judge={i:{'score':s,'vi_sao':'fixture'} for i,s in enumerate([12,18,15])})
        self.assertEqual(r['count'],3);self.assertTrue(r['auto_export_allowed'])
        rows=[db.query_one('SELECT score,signals FROM clips WHERE id=?',(cid,)) for cid in r['clip_ids']]
        self.assertEqual(sorted(row['score'] for row in rows),[12,15,18])
        self.assertTrue(all(not db.loads(row['signals']).get('quality_review_required',False) for row in rows))

    def test_auto_export_enqueues_low_score_and_legacy_review_result(self):
        r=self.generate([18,12,8])
        legacy=copy.deepcopy(r)
        legacy['selection']['quality_review_required']=True
        legacy['auto_export_allowed']=False
        for result in (r,legacy):
            jid=db.insert('INSERT INTO jobs(type,video_id,status,payload,result) VALUES(?,?,?,?,?)',('auto',self.vid,'done','{}',db.dumps(result)))
            page=types.SimpleNamespace(_pending_export={jid:self.vid},_auto_tpl={jid:1},_pipe_cut={},_pipe_by_vid={},_pipe_log=Mock(),status=Mock(),_video_cut_basic=Mock(return_value=False),_export_video=Mock(return_value=3),_pipe_on_exported=Mock(),_pipe_on_export_failed=Mock())
            StudioPage._check_auto_export_inner(page)
            page._export_video.assert_called_once_with(self.vid,tpl=1)
            page._pipe_on_export_failed.assert_not_called()
            self.assertEqual(page._pending_export,{})

    def test_critic_weak_ranking_does_not_discard_real_candidates(self):
        r=self.generate([18,12,8],dict(keep=[],drop=[0,1,2]))
        self.assertEqual(r['count'],3);self.assertTrue(r['auto_export_allowed'])

    def test_critic_rejections_never_restored(self):
        r=self.generate([90,85,80],dict(keep=[0],drop=[1,2],usable={'1':False,'2':False}))
        self.assertEqual(r['count'],1);self.assertEqual(r['selection']['rejected_critic'],2)

    def test_explicit_empty_critic_does_not_fall_back_to_heuristics(self):
        r=self.generate([90,85,80],dict(keep=[],drop=[0,1,2],usable={'0':False,'1':False,'2':False}));self.assertEqual(r['count'],0)
        self.assertEqual(services.list_clips(self.vid),[])

    def test_all_unusable_are_removed(self):
        r=self.generate([90,85],dict(keep=[0,1],usable={'0':False,'1':False}));self.assertEqual(r['count'],0)

    def test_partial_analysis_retains_candidates_but_holds_auto_export(self):
        r=self.generate([90],partial=True);self.assertEqual(r['count'],1)
        self.assertFalse(r['auto_export_allowed']);self.assertIn('chưa đầy đủ',r['selection_note'])

    def test_malformed_critic_is_not_called_no_good_segments(self):
        r=self.generate([90,85],dict(keep='bad'));self.assertEqual(r['count'],2)
        self.assertTrue(r['selection']['critic_incomplete']);self.assertFalse(r['auto_export_allowed'])

    def test_relative_score_gap_does_not_remove_distinct_parts(self):
        r=self.generate([85,40,35]);self.assertEqual(r['count'],3)
        self.assertTrue(r['auto_export_allowed'])

    def test_valid_empty_ai_response_is_not_invalid_clip(self):
        audit={}
        with patch.object(M.llm,'is_configured',return_value=True),patch.object(M.llm,'complete_json',return_value={'clips':[]}):
            clips,warnings=M._llm_select_clips(self.tr,1200,cfg={'count':3},audit=audit)
        self.assertEqual(clips,[]);self.assertTrue(audit['analysis_complete']);self.assertEqual(audit['proposed'],0)

    def test_chunk_error_persisted_in_audit(self):
        audit={}
        with patch.object(M.llm,'is_configured',return_value=True),patch.object(M,'_chunk_transcript',return_value=['[100-170] Story','[200-270] Story']),patch.object(M.llm,'complete_json',side_effect=[{'clips':[clip(0,90)]},M.llm.LLMError('fixture timeout')]),patch.object(M,'_refine_clip',side_effect=lambda c,*a:c):
            clips,warnings=M._llm_select_clips(self.tr,1200,cfg={'count':3,'min_len':60,'max_len':180},audit=audit)
        self.assertEqual(len(clips),1);self.assertFalse(audit['analysis_complete']);self.assertEqual(audit['chunks_failed'],1)
        self.assertIn('1/2',warnings[0])

    def test_auto_export_gate_never_exports_old_parts_or_retries_zero(self):
        old=db.insert('INSERT INTO clips(video_id,start_sec,end_sec,title,status,signals) VALUES(?,0,70,?,\'suggested\',?)',(self.vid,'old',db.dumps({'llm_used':False})))
        r=self.generate([],critic=None)
        entry=P.take_file(self.pid,self.source.name,'fixture',self.vid)
        jid=db.insert('INSERT INTO jobs(type,video_id,status,payload,result) VALUES(?, ?, ?, ?, ?)',('auto',self.vid,'done','{}',db.dumps(r)))
        page=types.SimpleNamespace(_pending_export={jid:self.vid},_auto_tpl={jid:1},_pipe_cut={jid:{}},_pipe_by_vid={self.vid:dict(entry=entry)},_pipe_log=Mock(),status=Mock(),_export_video=Mock(side_effect=AssertionError('must not export')), _video_cut_basic=Mock(side_effect=AssertionError('must not retry')))
        StudioPage._check_auto_export_inner(page)
        self.assertEqual(page._pending_export,{});page._export_video.assert_not_called()
        self.assertTrue(self.source.exists());self.assertIsNotNone(db.query_one('SELECT id FROM clips WHERE id=?',(old,)))

    def test_worker_persists_selection_summary(self):
        result=M._selection_result([123],{'count':3},'groq',{'analysis_complete':True},['fixture reason'])
        jid=db.insert('INSERT INTO jobs(type,video_id,status,payload) VALUES(?,?,?,?)',('part_test',self.vid,'pending','{}'))
        pool=worker.WorkerPool({},max_cpu=1,max_gpu=1)
        with patch.dict(worker._HANDLERS,{'part_test':lambda p,c:result}):pool._run_job(jid,'part_test','{}')
        row=db.query_one('SELECT status,message,result FROM jobs WHERE id=?',(jid,))
        self.assertEqual(row['status'],'done');self.assertEqual(row['message'],result['selection_note'])

    def test_zero_parts_skip_hashtag_api(self):
        with patch.object(jobs,'analysis_status',return_value={k:'done' for k in ('transcript','scenes','audio','faces')}),patch.object(M,'generate_highlights',return_value={'count':0}),patch.object(jobs,'_precompute_hashtags') as tags:
            jobs._auto({'video_id':self.vid},self.ctx)
        tags.assert_not_called()

class AudioFailure(unittest.TestCase):
    def setUp(self):
        self.folder=Path(tempfile.mkdtemp(prefix='audio_atomic_'));self.src=self.folder/'src.mp4';self.src.write_bytes(b'original')
        self.dst=self.folder/'audio.wav'

    def test_error_cause_survives_progress_tail_and_no_partial_published(self):
        def run(cmd,callback,**kwargs):
            Path(cmd[-1]).write_bytes(b'incomplete audio')
            callback('Error submitting packet to decoder: Invalid data found')
            for i in range(30):callback('size=100 time=00:29:47 speed=1x')
            callback('Conversion failed!');return -22
        with patch.object(F,'_run',side_effect=run):ok,why=F.extract_audio_wav_why(self.src,self.dst)
        self.assertFalse(ok);self.assertIn('Error submitting packet',why);self.assertIn('âm thanh',why)
        self.assertFalse(self.dst.exists());self.assertEqual(list(self.folder.glob('*.partial.wav')),[])
        self.assertEqual(self.src.read_bytes(),b'original')

    def test_cancellation_cleans_staging_and_keeps_existing_destination(self):
        self.dst.write_bytes(b'prior good file')
        def run(cmd,*a,**k):Path(cmd[-1]).write_bytes(b'partial');raise RuntimeError('canceled')
        with patch.object(F,'_run',side_effect=run),self.assertRaisesRegex(RuntimeError,'canceled'):F.extract_audio_wav_why(self.src,self.dst)
        self.assertEqual(self.dst.read_bytes(),b'prior good file');self.assertEqual(list(self.folder.glob('*.partial.wav')),[])

    def test_success_publishes_only_valid_wav(self):
        def run(cmd,*a,**k):
            with wave.open(cmd[-1],'wb') as wav:wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*16000)
            return 0
        with patch.object(F,'_run',side_effect=run):self.assertEqual(F.extract_audio_wav_why(self.src,self.dst),(True,''))
        with wave.open(str(self.dst)) as wav:self.assertEqual(wav.getnframes(),16000)

    def test_exit_zero_with_empty_file_does_not_publish(self):
        def run(cmd,*a,**k):Path(cmd[-1]).write_bytes(b'');return 0
        with patch.object(F,'_run',side_effect=run):ok,why=F.extract_audio_wav_why(self.src,self.dst)
        self.assertFalse(ok);self.assertFalse(self.dst.exists())

if __name__=='__main__':unittest.main(verbosity=2)
