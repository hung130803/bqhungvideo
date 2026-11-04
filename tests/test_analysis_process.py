"""Offline process lifecycle and forty-item queue regression; never call AI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import threading
import time
import unittest
from unittest.mock import patch

# SQLite thread-local connections can still be held at interpreter shutdown.
TEMP = tempfile.TemporaryDirectory(prefix='bqhung-queue-tests-', ignore_cleanup_errors=True)
os.environ.update(BQ_DATA_DIR=TEMP.name, BQ_DB_PATH=str(Path(TEMP.name)/'test.db'),
                  BQ_QSETTINGS_INI=str(Path(TEMP.name)/'settings.ini'), BQ_BO_MANG='1',
                  HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core import analysis_process as ap
from app.queue.worker import CanceledError, WorkerPool, register_handler
from app.database import db
from config import settings

CHILD = '''
import os,sys,time
from app.core.analysis_process import publish
mode=sys.argv[1]
if mode=='startup':
    time.sleep(60)
elif mode=='exit':
    sys.exit(0)
elif mode=='error':
    publish('error',0,'Lỗi thử có dấu tiếng Việt')
    sys.exit(1)
elif mode=='terminal':
    publish('done',1,'xong')
    time.sleep(60)
elif mode=='terminal_error':
    publish('error',0,'Lỗi thật rồi treo')
    time.sleep(60)
else:
    publish('progress',.25,'Đang chép lời thử')
    time.sleep(.15)
    if mode=='idle':
        time.sleep(60)
    if mode=='profile':
        import json
        p=json.loads(os.environ['BQ_ANALYSIS_PROFILE'])
        assert p=={'device':'cpu','whisper_model':'small','compute_type':'int8'}
    publish('done',1,'Đã kiểm tra xong')
'''

class Context:
    profile = dict(device='cpu', whisper_model='small', compute_type='int8', api_key='NEVER-PASS')
    def __init__(self, cancel_after=None):
        self.updates=[]
        self.start=time.monotonic()
        self.cancel_after=cancel_after
    def progress(self,p,m=''):
        self.check_canceled()
        self.updates.append((p,m))
    def check_canceled(self):
        if self.cancel_after is not None and time.monotonic()-self.start > self.cancel_after:
            raise CanceledError()

def run(mode, ctx=None, **kw):
    ctx=ctx or Context()
    ap.supervise([sys.executable,'-B','-c',CHILD,mode], str(ROOT), dict(os.environ),ctx,
                  startup_timeout=5, idle_timeout=5, heartbeat=.1, poll_interval=.02,
                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0), **kw)
    return ctx

class ProcessTests(unittest.TestCase):
    def test_success_and_unicode(self):
        ctx=run('ok',base=.1,span=.7)
        self.assertTrue(any('chép lời' in m for p,m in ctx.updates))
        self.assertAlmostEqual(ctx.updates[-1][0],.8)
    def test_profile_excludes_secrets(self):
        run('profile')
    def test_exit_without_done_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError,'analysis_worker_failed'):
            run('exit')
    def test_crash_keeps_stderr_tail(self):
        # 27/10/2026: chết "mã 1" mà stderr bị vứt -> không còn dấu vết.
        with self.assertRaisesRegex(RuntimeError,'Lỗi cuối: .*MemoryError: het RAM'):
            ap.supervise([sys.executable,'-c','import sys; sys.stderr.write("MemoryError: het RAM"); sys.exit(1)'],
                         str(ROOT),dict(os.environ),Context(),startup_timeout=5,poll_interval=.02)
    def test_error_message_survives_windowless_child(self):
        with self.assertRaisesRegex(RuntimeError,'Lỗi thử có dấu tiếng Việt'):
            run('error')
    def test_startup_timeout_frees_child(self):
        ctx=Context()
        with self.assertRaisesRegex(RuntimeError,'analysis_worker_timeout'):
            ap.supervise([sys.executable,'-c','import time; time.sleep(60)'],str(ROOT),dict(os.environ),ctx,
                          startup_timeout=.4,heartbeat=.1,poll_interval=.02)
        self.assertTrue(any('có thể bấm Hủy' in m for p,m in ctx.updates))
    def test_idle_timeout_after_ready(self):
        with self.assertRaisesRegex(RuntimeError,'Không có tiến độ mới'):
            ap.supervise([sys.executable,'-B','-c',CHILD,'idle'],str(ROOT),dict(os.environ),Context(),
                          startup_timeout=5,idle_timeout=.4,poll_interval=.02)
    def test_terminal_does_not_wait_forever(self):
        # 27/10/2026: đã 'done' (kết quả đã lưu) mà kẹt lúc thoát -> tắt tiến
        # trình, tính là XONG; không chờ mãi, không báo lỗi oan.
        started=time.monotonic()
        ctx=run('terminal',exit_timeout=.3)
        self.assertLess(time.monotonic()-started,15)
        self.assertTrue(any(m=='xong' for p,m in ctx.updates))
    def test_terminal_error_hang_still_fails(self):
        with self.assertRaisesRegex(RuntimeError,'không đóng.*Lỗi thật rồi treo'):
            run('terminal_error',exit_timeout=.3)
    def test_cancel_while_silent(self):
        started=time.monotonic()
        with self.assertRaises(CanceledError):
            run('startup',Context(cancel_after=.35))
        self.assertLess(time.monotonic()-started,3)
    def test_partial_snapshot_is_ignored(self):
        path=Path(TEMP.name)/'partial.json'
        path.write_text('{',encoding='utf-8')
        self.assertEqual(ap.read_status(path),{})
    def test_publish_does_not_need_stdout(self):
        path=Path(TEMP.name)/'published.json'
        with patch.dict(os.environ,{ap.STATUS_ENV:str(path)}), patch('sys.stdout',None):
            ap.publish('progress',.2,'Chép lời tiếng Việt')
        self.assertEqual(ap.read_status(path)['message'],'Chép lời tiếng Việt')
    def test_concurrent_progress_writers(self):
        from concurrent.futures import ThreadPoolExecutor
        path=Path(TEMP.name)/'parallel.json'
        with patch.dict(os.environ,{ap.STATUS_ENV:str(path)}):
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda n: ap.publish('progress',n/60.,f'Phần {n}'),range(60)))
            ap.publish('done',1.,'Hoàn tất')
        self.assertEqual(ap.read_status(path)['kind'],'done')

    def test_actual_runner_fails_missing_video_without_hardware_probe(self):
        env=dict(os.environ,BQ_ANALYSIS_PROFILE='{}')
        path=Path(TEMP.name)/'runner.json'
        env[ap.STATUS_ENV]=str(path)
        proc=subprocess.run([sys.executable,'-B','-m','app.core.analysis_runner','-999'],cwd=ROOT,
                            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        self.assertEqual(proc.returncode,1,proc.stderr.decode('utf-8','replace'))
        self.assertIn('Không tìm thấy video',ap.read_status(path)['message'])
    def test_forty_jobs_three_workers_do_not_starve_after_timeout(self):
        settings.ECO_MODE=False
        seen=[]
        lock=threading.Lock()
        def handler(payload,ctx):
            with lock:
                seen.append(ctx.job_id)
            if payload['n']==0:
                ap.supervise([sys.executable,'-c','import time; time.sleep(60)'],str(ROOT),dict(os.environ),ctx,
                              startup_timeout=.3,poll_interval=.02)
            else:
                run('ok',ctx)
            return {}
        register_handler('queue_protocol_test',handler)
        ids=[db.insert("INSERT INTO jobs(type,payload,status,needs_gpu,max_attempts) VALUES(?,?,'pending',1,3)",
                       ('queue_protocol_test',json.dumps({'n':n}))) for n in range(40)]
        pool=WorkerPool({},max_cpu=1,max_gpu=3,poll_interval=.02)
        try:
            pool.start()
            deadline=time.monotonic()+90
            peak=0
            while time.monotonic()<deadline:
                states=db.query("SELECT status,count(*) AS n FROM jobs WHERE type='queue_protocol_test' GROUP BY status")
                counts={r['status']:r['n'] for r in states}
                peak=max(peak,counts.get('running',0))
                if counts.get('done',0)+counts.get('failed',0)==40:
                    break
                time.sleep(.02)
            self.assertEqual(counts.get('done'),39,counts)
            self.assertEqual(counts.get('failed'),1,counts)
            self.assertEqual(peak,3)
            self.assertEqual(len(seen),40,'timeout must not automatically retry')
            row=db.query_one('SELECT attempts,error FROM jobs WHERE id=?',(ids[0],))
            self.assertEqual(row['attempts'],1)
            self.assertIn('analysis_worker_timeout',row['error'])
        finally:
            pool.stop(wait=True)

if __name__=='__main__':
    unittest.main(verbosity=2)
