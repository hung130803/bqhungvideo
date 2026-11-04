"""Offline boundary/context, actual-interval dedupe, and multi-process quota checks."""
import os
import sys
import tempfile
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, Mock
import unittest

ROOT=Path(r'D:\claude\ai-content-studio')
AREA=Path(tempfile.mkdtemp(prefix='editorial38-'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
sys.path.insert(0,str(ROOT))
import _test_guard
from app.ai import groq_dispatch as G, llm
from app.ai.editorial_context import contextual_chunks
from app.modules import m1_highlight as M


class EditorialTests(unittest.TestCase):
    def test_chunk_boundary_keeps_question_answer(self):
        chunks=['0 20 | A woman shows a vase.\n20 30 | How much is it?',
                '30 40 | Five dollars.\n40 50 | She buys it.']
        result=contextual_chunks(chunks)
        self.assertEqual(len(result),len(chunks))
        for text in result:
            self.assertIn('How much is it?',text);self.assertIn('Five dollars.',text)
        self.assertIn(chunks[0],result[0]);self.assertIn(chunks[1],result[1])

    def test_context_bounded_and_never_truncates(self):
        chunks=['\n'.join(f'{i*100+j} {i*100+j+1} | '+('x'*90) for j in range(50)) for i in range(50)]
        for source,result in zip(chunks,contextual_chunks(chunks)):
            self.assertIn(source,result)
            self.assertLessEqual(len(result)-len(source),700)
            self.assertTrue(all(line.endswith('x'*90) for line in result.splitlines()))
        self.assertEqual(contextual_chunks([]),[])
        self.assertEqual(contextual_chunks(['abc']),['abc'])

    def test_selector_keeps_distinct_parts_inside_montage_gaps(self):
        transcript={'language':'en','segments':[{'start':i,'end':i+10,'text':'An item is inspected and priced.'} for i in range(0,180,10)]}
        proposed=[{'title':'One','score':90,'segments':[[0,30],[120,150]]},
                  {'title':'Two','score':18,'segments':[[40,100]]},
                  {'title':'Three','score':12,'segments':[[150,180]]}]
        with patch.object(llm,'is_configured',return_value=True),patch.object(llm,'complete_json',return_value=proposed), \
             patch.object(M,'_normalize_clip',side_effect=lambda r,*args:dict(r)), \
             patch.object(M,'_trim_junk_edges',side_effect=lambda s,*args:s), \
             patch.object(M,'_junk_ratio',return_value=0), \
             patch.object(M,'_refine_clip',side_effect=lambda c,*args:c):
            clips,warnings=M._llm_select_clips(transcript,180,cfg={'count':3,'min_len':0})
        self.assertEqual(len(clips),3)
        self.assertEqual([c['score'] for c in clips],[90,18,12])

    def test_cooldown_cross_process_and_scope(self):
        key='test-only-not-a-real-key';G.defer(key,'chat',12)
        code="from app.ai.groq_dispatch import remaining;print(remaining('test-only-not-a-real-key','chat'))"
        proc=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=os.environ,check=True,capture_output=True,text=True)
        self.assertGreater(float(proc.stdout.strip()),0)
        self.assertEqual(G.remaining(key,'vision'),0)
        self.assertNotIn(key,(AREA/'_cache/groq_dispatch.sqlite3').read_bytes().decode('latin1'))

    def test_shared_lanes_exclude_competing_processes(self):
        self.assertTrue(G._claim('test-lane','parent'))
        code="from app.ai.groq_dispatch import _claim;print(_claim('test-lane','child'))"
        proc=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env=os.environ,check=True,capture_output=True,text=True)
        self.assertEqual(proc.stdout.strip(),'False')
        G._release('test-lane','wrong-owner')
        self.assertFalse(G._claim('test-lane','other'))
        G._release('test-lane','parent');time.sleep(.4)
        self.assertTrue(G._claim('test-lane','other'))
        G._release('test-lane','other')

    def test_crashed_lease_expires(self):
        self.assertTrue(G._claim('dead','old'))
        con=G._connect()
        with con:con.execute('UPDATE lane SET until=0 WHERE scope=?',('dead',))
        con.close()
        self.assertTrue(G._claim('dead','new'));G._release('dead','new')

    def test_older_success_preserves_newer_limit(self):
        started=time.time()-5
        G.defer('racing-key','chat',60)
        G.clear('racing-key','chat',started)
        self.assertGreater(G.remaining('racing-key','chat'),0)
        G.clear('racing-key','chat',time.time())
        self.assertEqual(G.remaining('racing-key','chat'),0)

    def test_actual_overlap_removed_but_score_not_a_gate(self):
        from app.ai.chon_doan import bo_trung_nhau
        clips=[{'score':20,'segments':[[0,60]]}, {'score':15,'segments':[[10,65]]},
               {'score':5,'segments':[[100,160]]}]
        kept,_=bo_trung_nhau(clips,ty_le=.25)
        self.assertEqual([c['score'] for c in kept],[20,5])

    def test_audio_cooldown_does_not_block_chat(self):
        llm.mark_limited('groq','audio-only-limit','429 retry in 60s',scope='transcription')
        self.assertGreater(llm.soonest_ready_wait('groq',['audio-only-limit'],scope='transcription'),0)
        self.assertEqual(llm.soonest_ready_wait('groq',['audio-only-limit'],scope='chat'),0)
        self.assertEqual(llm.soonest_ready_wait('groq',['audio-only-limit'],scope='vision'),0)

    def test_wait_cancels_without_request(self):
        self.assertTrue(G._claim('cancel','busy'))
        def cancel():raise InterruptedError('cancelled')
        with self.assertRaises(InterruptedError):
            with G.slot('cancel',cancel):self.fail('must not call')
        G._release('cancel','busy')

    def test_http_429_published_before_next_request(self):
        key='unit-rate-key';client=Mock()
        error=RuntimeError('429 rate limit exceeded, try again in 9s')
        client.chat.completions.create.side_effect=error
        with self.assertRaises(RuntimeError):llm._groq_create(client,key,model='unit')
        self.assertGreater(G.remaining(key,'chat'),0)
        self.assertGreater(llm.soonest_ready_wait('groq',[key]),0)
        with self.assertRaises(RuntimeError):llm._groq_create(client,key,model='unit')
        self.assertEqual(client.chat.completions.create.call_count,1)

    def test_payload_error_does_not_cool_key(self):
        client=Mock();client.chat.completions.create.side_effect=RuntimeError('413 request too large')
        with self.assertRaises(RuntimeError):llm._groq_create(client,'unit-large',model='unit')
        self.assertEqual(G.remaining('unit-large','chat'),0)


if __name__=='__main__':unittest.main()
