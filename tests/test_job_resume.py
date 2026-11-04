"""Offline restart, cancellation, multi-channel and atomic-publication checks."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
if not (ROOT/'app').exists():ROOT=Path(r'D:\claude\ai-content-studio')
AREA=Path(tempfile.mkdtemp(prefix='bq-resume37-'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),
 BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
sys.path.insert(0,str(ROOT))
import _test_guard
from app.database import db
from app.core import job_resume as R
from app.ai import llm
from app.queue.worker import WorkerPool, CanceledError
from app import services

class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.pid=services.create_project(self._testMethodName)
  self.src=AREA/(self._testMethodName+'.mp4');self.src.write_bytes(b'source')
  self.vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)',(self.pid,str(self.src),300))
  self.payload={'video_id':self.vid,'preset':{'count':3}}
  self.jid=self.job()

 def job(self):
  return db.insert('INSERT INTO jobs(type,project_id,video_id,payload,status) VALUES(?,?,?,?,?)',
   ('auto',self.pid,self.vid,db.dumps(self.payload),'pending'))

 def test_completed_calls_replay_once_per_occurrence(self):
  calls=[]
  @R.completed_ai_call
  def api(prompt,provider=None):calls.append(prompt);return {'number':len(calls)}
  with R.scope(self.jid,self.payload):
   self.assertEqual(api('same')['number'],1);self.assertEqual(api('same')['number'],2)
  with R.scope(self.jid,self.payload):
   self.assertEqual(api('same')['number'],1);self.assertEqual(api('same')['number'],2)
   self.assertEqual(api('same')['number'],3)
  self.assertEqual(len(calls),3)

 def test_failed_call_not_saved_and_source_change_invalidates(self):
  run=Mock(side_effect=[ValueError('interrupted'),{'ok':True},{'new':True}])
  @R.completed_ai_call
  def api(prompt):return run()
  with R.scope(self.jid,self.payload):
   with self.assertRaises(ValueError):api('test')
  with R.scope(self.jid,self.payload):self.assertEqual(api('test'),{'ok':True})
  with R.scope(self.jid,self.payload):self.assertEqual(api('test'),{'ok':True})
  self.src.write_bytes(b'changed source')
  with R.scope(self.jid,self.payload):self.assertEqual(api('test'),{'new':True})
  self.assertEqual(run.call_count,3)

 def test_local_audio_done_motion_interrupted(self):
  audio=Mock(return_value=[.1,.2]);motion=Mock(side_effect=[RuntimeError('close'),[.3,.4]])
  for attempt in range(2):
   with R.scope(self.jid,self.payload):
    self.assertEqual(R.local_step('audio',[],audio),[.1,.2])
    if attempt==0:
     with self.assertRaises(RuntimeError):R.local_step('motion',[],motion)
    else:self.assertEqual(R.local_step('motion',[],motion),[.3,.4])
  self.assertEqual(audio.call_count,1);self.assertEqual(motion.call_count,2)

 def test_images_replay_across_temporary_directories(self):
  a=AREA/'a.jpg';b=AREA/'b.jpg';a.write_bytes(b'image');b.write_bytes(b'image')
  calls=Mock(return_value={'visible':'fixture'})
  @R.completed_ai_call
  def api(prompt,image_paths):return calls()
  with R.scope(self.jid,self.payload):api('view',[str(a)])
  with R.scope(self.jid,self.payload):api('view',[str(b)])
  self.assertEqual(calls.call_count,1)

 def test_corrupt_checkpoint_recomputed_not_trusted(self):
  run=Mock(return_value=[1])
  with R.scope(self.jid,self.payload):R.local_step('a',[],run)
  db.execute("UPDATE job_checkpoints SET data='{}' WHERE job_id=?",(self.jid,))
  with R.scope(self.jid,self.payload):self.assertEqual(R.local_step('a',[],run),[1])
  self.assertEqual(run.call_count,2)

 def test_canceled_job_does_not_replay_or_call(self):
  run=Mock(return_value=[1])
  with R.scope(self.jid,self.payload):R.local_step('a',[],run)
  with R.scope(self.jid,self.payload,Mock(side_effect=CanceledError)):
   with self.assertRaises(CanceledError):R.local_step('a',[],run)
  self.assertEqual(run.call_count,1)

 def test_three_hundred_jobs_remain_isolated(self):
  jobs=[self.job() for _ in range(300)]
  def work(jid):
   with R.scope(jid,self.payload):return R.local_step('part',[],lambda:[jid])
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   first=list(pool.map(work,jobs));second=list(pool.map(work,jobs))
  self.assertEqual(first,[[j] for j in jobs]);self.assertEqual(first,second)

 def test_child_threads_keep_their_scope(self):
  calls=Mock(side_effect=lambda p: {'p':p})
  @R.completed_ai_call
  def api(prompt):return calls(prompt)
  for _ in range(2):
   with R.scope(self.jid,self.payload),concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    fs=[pool.submit(R.bind_context(api),str(i)) for i in range(8)]
    self.assertEqual([f.result() for f in fs],[{'p':str(i)} for i in range(8)])
  self.assertEqual(calls.call_count,8)

 def test_normal_shutdown_does_not_exhaust_retry_budget(self):
  pool=WorkerPool({},max_cpu=1,max_gpu=1)
  db.execute("UPDATE jobs SET status='running',attempts=1,progress=.84 WHERE id=?",(self.jid,))
  pool.stop()
  row=db.query_one('SELECT status,attempts,progress FROM jobs WHERE id=?',(self.jid,))
  self.assertEqual(tuple(row),('pending',0,.84))
  pool._recover_crashed()
  self.assertEqual(db.query_one('SELECT status FROM jobs WHERE id=?',(self.jid,))['status'],'pending')

 def test_atomic_publication_rolls_back_and_replays_without_generation(self):
  old=db.insert('INSERT INTO clips(video_id,start_sec,end_sec,title,status) VALUES(?,?,?,?,?)',(self.vid,0,60,'old','suggested'))
  rows=[(self.vid,60,130,50,'reason','first','','{}'),(self.vid,140,210,40,'reason','second','','{}')]
  db.execute("CREATE TEMP TRIGGER fail_second BEFORE INSERT ON clips WHEN NEW.title='second' BEGIN SELECT RAISE(ABORT,'simulate disk interruption'); END")
  with R.scope(self.jid,self.payload):
   with self.assertRaises(Exception):R.publish_highlights(self.vid,rows,{},self.payload['preset'])
   self.assertIsNone(R.generation_result('highlights',self.payload['preset']))
  self.assertIsNotNone(db.query_one('SELECT id FROM clips WHERE id=?',(old,)))
  db.execute('DROP TRIGGER fail_second')
  with R.scope(self.jid,self.payload):
   done=R.publish_highlights(self.vid,rows,{'llm_used':True},self.payload['preset'])
  with R.scope(self.jid,self.payload):
   self.assertEqual(R.generation_result('highlights',self.payload['preset']),done)
  self.assertEqual(len(db.query('SELECT id FROM clips WHERE video_id=?',(self.vid,))),2)

 def test_random_choices_stable_only_within_same_job(self):
  def sample(jid):
   with R.scope(jid,self.payload):return [R.random_for('length',[60,120]).random() for _ in range(10)]
  self.assertEqual(sample(self.jid),sample(self.jid));self.assertNotEqual(sample(self.jid),sample(self.job()))

 def test_process_exit_preserves_finished_step(self):
  code='''import os,sys
sys.path.insert(0,sys.argv[1])
from app.core import job_resume as r
import json
with r.scope(int(sys.argv[2]),json.loads(sys.argv[3])):
 r.local_step('before-exit',[],lambda:[42])
os._exit(17)
'''
  proc=subprocess.run([sys.executable,'-B','-c',code,str(ROOT),str(self.jid),json.dumps(self.payload)],env=dict(os.environ),capture_output=True)
  self.assertEqual(proc.returncode,17,proc.stderr.decode(errors='replace'))
  with R.scope(self.jid,self.payload):
   self.assertEqual(R.local_step('before-exit',[],Mock(side_effect=AssertionError('repeated'))),[42])

if __name__=='__main__':unittest.main(verbosity=2)
