import os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
AREA=Path(tempfile.mkdtemp(prefix='auto-resume-'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1')
import _test_guard
from app.database import db
from app.core.auto_export_resume import JobMap

class AutoExportResume(unittest.TestCase):
 def test_snapshot_and_intent_survive_restart_but_canceled_jobs_do_not(self):
  a=db.insert("INSERT INTO jobs(type,payload,status) VALUES('auto','{}','running')")
  b=db.insert("INSERT INTO jobs(type,payload,status) VALUES('auto','{}','canceled')")
  videos=JobMap('video');templates=JobMap('template')
  template={'bg':'design:paper','layers':[{'text':'saved'}]}
  videos[a]=12;templates[a]=template;videos[b]=13;templates[b]=template
  template['layers'][0]['text']='changed'
  self.assertEqual(JobMap('video'),{a:12})
  fresh=JobMap('template');self.assertEqual(fresh[a]['layers'][0]['text'],'saved')
  fresh.setdefault(a,{'bg':'blur'});self.assertEqual(fresh[a]['bg'],'design:paper')
  videos.pop(a);fresh.pop(a)
  self.assertEqual(JobMap('video'),{});self.assertEqual(JobMap('template'),{})

if __name__=='__main__':unittest.main(verbosity=2)
