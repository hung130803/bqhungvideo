"""Provider budgets, bounded SDK calls, and resumable director stages, offline."""
import os,sys,tempfile,json,unittest
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq-resume-'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
sys.path.insert(0,str(ROOT))
import _test_guard
from app.ai import story_quality as q,story_director as d,llm
from app.core import analysis,pipeline
from app.queue.worker import CanceledError


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.ctx=Mock();self.saved={}
        self.units=[dict(u,transcript='The speaker describes the setup.',safe_orig=True,
            observations=[{'at':(u['start']+u['end'])/2,'visible':'A card','uncertain':'Unknown identity'}])
            for u in q.coverage(144)]
        self.plans=[{'title':'Story '+str(i),'angle':'A real event','parts':[
            {'source_id':i,'start':i*12,'end':i*12+12,'text':'','evidence':json.dumps(self.units[i])}]} for i in range(2)]
        self.cards=[{'id':u['id'],'event':'A specific event','interest':3} for u in self.units]

    def write(self,vid,kind,status,data,**kw):self.saved[kind]=deepcopy(data)
    def read(self,vid,kind):return deepcopy(self.saved.get(kind))
    def run_direct(self,script,**kw):
        with patch.object(analysis,'get_analysis',side_effect=self.read),patch.object(analysis,'_set',side_effect=self.write),\
             patch.object(d,'catalogue',return_value=self.cards) as cat,\
             patch.object(d,'choose_edits',return_value=deepcopy(self.plans)) as choose,\
             patch.object(d,'refine') as refine,patch.object(d,'script',side_effect=script) as write:
            result=d.direct(deepcopy(self.units),'source.mp4',set(),kw.get('preset',{}),2,'English',self.ctx,cache=(5,kw.get('key','source-key')))
            return result,cat.call_count,choose.call_count,refine.call_count,write.call_count

    def good(self,plan,*args,**kw):
        plan=deepcopy(plan);plan['parts'][0]['text']='The speaker explains the setup.'
        plan['review']={'approved':False,'issues':'Human review required'}
        return plan

    def test_gemini_does_not_inherit_groq_budget(self):
        prompt='映'*8000
        with patch.object(llm,'active_provider',return_value='gemini'),patch.object(llm,'complete_json',return_value={'ok':True}) as api:
            self.assertEqual(q.ask(prompt),{'ok':True});api.assert_called_once()
        with patch.object(llm,'active_provider',return_value='groq'),patch.object(llm,'complete_json') as api:
            with self.assertRaisesRegex(RuntimeError,'story_input_too_large'):q.ask(prompt)
            api.assert_not_called()

    def test_larger_gemini_batches_retain_every_scene(self):
        units=[{'id':i,'transcript':'Actual attributed speech. '*40,
            'observations':[{'visible':'Visible object. '*60,'uncertain':'Unknown identity.'}]} for i in range(109)]
        small=q.evidence_batches(units,limit=6500)
        large=q.evidence_batches(units,limit=18000,token_limit=7500)
        self.assertLess(len(large),len(small))
        self.assertEqual([u for block in large for u in block],units)
        self.assertTrue(all(q.token_size(block)<=7500 and len(block)<=24 for block in large))

    def test_gemini_keeps_long_source_candidates_without_shortlist_calls(self):
        units=[dict(u,observations=[{'at':(u['start']+u['end'])/2,'visible':'Visible factual context. '*12}])
            for u in q.coverage(1306.4)]
        cards=[{'id':u['id'],'event':'A specific attributed event with uncertainty. '*5,'interest':3} for u in units]
        with patch.object(llm,'active_provider',return_value='gemini'),patch.object(d,'planning_cards',side_effect=AssertionError('Unnecessary API shortlist')):
            retained,notes=d.planning_notes(cards,{u['id']:u for u in units},self.ctx)
        self.assertEqual(retained,cards)
        self.assertEqual([n[0] for n in notes],[u['id'] for u in units])
        self.assertLessEqual(q.token_size(notes),10000)

    def test_oversized_error_stops_automatic_whole_job_retry(self):
        with patch.object(llm,'active_provider',return_value='gemini'),patch.object(llm,'complete_json') as api:
            with self.assertRaises(RuntimeError) as raised:q.ask('映'*25000)
            self.assertTrue(pipeline.is_configuration_error(str(raised.exception)))
            self.assertFalse(pipeline.is_source_error(str(raised.exception)));api.assert_not_called()

    def test_selection_does_not_retry_for_trimmed_original_dialogue(self):
        units=deepcopy(self.units)
        units[2]['end']-=.0014
        raw={'title':'A connected event','angle':'Setup and consequence',
            'shots':[{'source_id':i,'in':0,'out':round(units[i]['end']-units[i]['start'],2),
                      'mode':'orig','reason':'Supported setup and consequence'} for i in (0,2,4,6,8,10)]}
        raw['shots'][2].update({'in':1,'out':11})
        with patch.object(q,'ask',side_effect=[raw,{'approved':True}]) as api:
            plans=d.choose_edits(units,self.cards,set(),{},1,self.ctx)
        self.assertEqual(api.call_count,2)
        parts=plans[0]['parts']
        self.assertEqual(parts[0]['mode'],'narrate')
        self.assertEqual(parts[1]['mode'],'orig')
        self.assertEqual(parts[1]['end'],units[2]['end'])
        self.assertEqual(parts[2]['mode'],'narrate')
        self.assertEqual((parts[2]['start'],parts[2]['end']),(49,59))

    def test_stage_identified_without_logging_prompt(self):
        secret='PRIVATE_SOURCE_SENTENCE'
        with patch.object(llm,'complete_json',return_value={}),q.request_stage(self.ctx,'Viết Part 1',.7):q.ask(secret)
        self.assertIn('Viết Part 1',self.ctx.progress.call_args.args[1])
        logs=list((AREA/'logs').glob('story_timing*'));self.assertTrue(logs)
        self.assertNotIn(secret,logs[0].read_text(encoding='utf-8'))

    def test_resume_after_second_part_failure_skips_completed_stages(self):
        def fail_second(plan,*args,**kw):
            if plan['title']=='Story 1':raise RuntimeError('transient')
            return self.good(plan,*args,**kw)
        with self.assertRaisesRegex(RuntimeError,'transient'):self.run_direct(fail_second)
        result,cat,choose,refine,write=self.run_direct(self.good)
        self.assertEqual((cat,choose,refine,write),(0,0,0,1))
        self.assertEqual(len(result[0]),2)
        self.assertFalse(result[0][0]['review']['approved'])
        again=self.run_direct(self.good)
        self.assertEqual(again[1:],(0,0,0,0))

    def test_settings_and_source_changes_invalidate_cache(self):
        self.run_direct(self.good)
        changed=self.run_direct(self.good,preset={'story_lang':'vi'})
        self.assertEqual(changed[1:4],(1,1,1))
        changed=self.run_direct(self.good,preset={'story_lang':'vi'},key='changed-file')
        self.assertEqual(changed[1:4],(1,1,1))

    def test_corrupt_checkpoint_is_not_reused(self):
        self.run_direct(self.good)
        self.saved['story_director']['state']['plans'][0]['title']='Corrupt'
        changed=self.run_direct(self.good)
        self.assertEqual(changed[1:4],(1,1,1))

    def test_cancel_does_not_cache_incomplete_script(self):
        with self.assertRaises(CanceledError):self.run_direct(lambda *a,**k:(_ for _ in ()).throw(CanceledError()))
        self.assertFalse(self.saved['story_director']['state'].get('scripts'))

    def test_refine_saves_completed_evidence(self):
        plans=deepcopy(self.plans);checkpoint=Mock()
        with patch.object(d,'enrich_scene',side_effect=lambda src,u,ctx,f:u):
            d.refine(plans,deepcopy(self.units),'source.mp4',self.ctx,on_checkpoint=checkpoint)
        self.assertEqual(checkpoint.call_count,2)

    def test_chat_sdk_uses_deadline_and_no_hidden_retry(self):
        import google.generativeai as genai
        from types import SimpleNamespace
        model=Mock();model.generate_content.return_value=SimpleNamespace(text='{}',usage_metadata=None)
        with patch.object(llm.settings.__class__,'GEMINI_MODEL','gemini-legacy-test'),patch.object(genai,'configure'),patch.object(genai,'GenerativeModel',return_value=model),llm.bounded_call(3):
            llm._call_once('gemini','fixture','prompt','',.3,json_mode=True,request_timeout=20)
        options=model.generate_content.call_args.kwargs
        self.assertLessEqual(options['request_options']['timeout'],3)
        self.assertIsNone(options['request_options']['retry'])
        self.assertEqual(options['generation_config']['response_mime_type'],'application/json')

    def test_strict_story_json_never_returns_inner_array_from_truncated_object(self):
        broken='{"hooks":["one","two","three"],"shots":'
        with patch.object(llm,'complete_text',side_effect=[broken,'{"shots":[]}']),patch.object(llm,'ly_do_ket_thuc',return_value='stop') as finish:
            self.assertEqual(llm.complete_json('prompt',strict_object=True),{'shots':[]})
            self.assertEqual(finish.call_count,2)
        with patch.object(llm,'complete_text',return_value=broken),patch.object(llm,'ly_do_ket_thuc',return_value='length'):
            with self.assertRaises(llm.LLMCatCut):llm.complete_json('prompt',strict_object=True)

    def test_bounded_gemini_reserves_reasoning_and_output_separately(self):
        response=Mock(ok=True)
        response.json.return_value={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}'}]}}]}
        with patch.object(llm.settings.__class__,'GEMINI_MODEL','gemini-2.5-flash'),patch('requests.post',return_value=response) as post,llm.bounded_call(3):
            self.assertEqual(llm._call_once('gemini','fixture','prompt','system',.3,json_mode=True),'{}')
        sent=post.call_args.kwargs
        self.assertEqual(sent['json']['generationConfig']['thinkingConfig']['thinkingBudget'],4096)
        self.assertEqual(sent['json']['generationConfig']['maxOutputTokens'],12288)
        self.assertLessEqual(sent['timeout'],3)
        self.assertNotIn('fixture',post.call_args.args[0])
        self.assertEqual(llm.ly_do_ket_thuc(),'stop')

    def test_gemini_http_quota_and_cut_are_not_silently_salvaged(self):
        response=Mock(ok=False,status_code=429)
        response.json.return_value={'error':{'message':'quota exceeded'}}
        with patch.object(llm.settings.__class__,'GEMINI_MODEL','gemini-2.5-flash'),patch('requests.post',return_value=response),llm.bounded_call(3):
            with self.assertRaisesRegex(RuntimeError,'429') as raised:llm._call_once('gemini','fixture','prompt','',.3,json_mode=True)
            self.assertTrue(llm.is_rate_limit_error(str(raised.exception)))
            response.ok=True
            response.json.return_value={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{"hooks":[],'}]}}]}
            llm._call_once('gemini','fixture','prompt','',.3,json_mode=True)
            self.assertEqual(llm.ly_do_ket_thuc(),'length')

if __name__=='__main__':unittest.main(verbosity=2)
