"""Offline provider refusal through real job queue; never contact an API."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
AREA=Path(tempfile.mkdtemp(prefix='bq_content_block_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
    BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
import _test_guard
from app.ai import llm
from app.database.db import db
from app.queue import worker
from app.core.pipeline import is_content_block_error
from app.ui.queue_panel import QueuePanel

class ContentBlockTests(unittest.TestCase):
    def run_job(self,error,max_attempts=3,cancel=False):
        pool=worker.WorkerPool({})
        jid=db.insert("INSERT INTO jobs(type,payload,status,attempts,max_attempts) VALUES('block_test','{}','pending',0,?)",(max_attempts,))
        def handler(payload,ctx):
            ctx.progress(.89,'Đối chiếu tình tiết · nhóm 2/4')
            if cancel:db.execute('UPDATE jobs SET cancel_req=1 WHERE id=?',(jid,))
            raise error
        try:
            with patch.dict(worker._HANDLERS,{'block_test':handler}):
                pool._run_job(jid,'block_test','{}')
            return dict(db.query_one('SELECT * FROM jobs WHERE id=?',(jid,)))
        finally:pool.stop(wait=True)

    def test_block_stops_first_attempt_and_preserves_stage(self):
        row=self.run_job(llm.LLMContentBlocked('block_reason=PROHIBITED_CONTENT'))
        self.assertEqual((row['status'],row['attempts']),('failed',1))
        self.assertEqual(row['message'],'Đối chiếu tình tiết · nhóm 2/4')
        self.assertIn('nhóm 2/4',QueuePanel._fail_text(row))
        self.assertIn('không tự thử lại',row['error'])

    def test_legacy_wrapped_block_also_stops(self):
        row=self.run_job(RuntimeError('Viết kịch bản: Gemini không trả nội dung: finish_reason=, block_reason=PROHIBITED_CONTENT. Không đánh dấu key hỏng.'))
        self.assertEqual(row['status'],'failed')
        self.assertTrue(is_content_block_error('Gemini không cung cấp nội dung hình ảnh (block_reason=1, finish_reason=0)'))

    def test_transient_error_still_retries(self):
        self.assertEqual(self.run_job(RuntimeError('Connection timed out'))['status'],'pending')
        self.assertFalse(is_content_block_error('429 rate limit'))

    def test_final_transient_failure_retains_stage(self):
        row=self.run_job(RuntimeError('Connection timed out'),max_attempts=1)
        self.assertEqual(row['status'],'failed')
        self.assertIn('nhóm 2/4',row['message'])

    def test_cancel_wins_over_content_block(self):
        row=self.run_job(llm.LLMContentBlocked('block_reason=PROHIBITED_CONTENT'),cancel=True)
        self.assertEqual(row['status'],'canceled')

    def test_legacy_popup_does_not_claim_failure_is_stage(self):
        self.assertEqual(QueuePanel._fail_text({'error':'lỗi thử','message':'Thất bại'}),'lỗi thử')

    def test_provider_block_calls_once_without_key_rotation(self):
        response=Mock(ok=True)
        response.json.return_value={'promptFeedback':{'blockReason':'PROHIBITED_CONTENT'}}
        with patch.object(llm.settings,'llm_keys_for',return_value=['fixture-key-1','fixture-key-2']), \
             patch.object(llm.settings,'GEMINI_MODEL','gemini-2.5-flash'), \
             patch.object(llm,'ensure_provider_available'), \
             patch.object(llm,'pick_keys',return_value=['fixture-key-1','fixture-key-2']), \
             patch('app.ai.key_health.blocked',return_value=False), \
             patch.object(llm,'mark_used'),patch.object(llm,'mark_limited') as limited, \
             patch.object(llm,'mark_ok') as ok, \
             patch('requests.post',return_value=response) as post, llm.bounded_call(15):
            with self.assertRaises(llm.LLMContentBlocked):
                llm.complete_text('fixture prompt',provider='gemini',json_mode=True)
        self.assertEqual(post.call_count,1)
        limited.assert_not_called();ok.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
