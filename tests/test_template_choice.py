import os,sys,tempfile,unittest,copy
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
AREA=Path(tempfile.mkdtemp(prefix='bq-template-choice-'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
import _test_guard
from PyQt6.QtWidgets import QApplication
from app import services
from app.ui.studio_page import StudioPage
from app.ui.state import AppState
from app.core.template_library import ensure_templates,catalog
app=QApplication.instance() or QApplication([])

class TemplateChoice(unittest.TestCase):
 def test_pick_updates_only_current_channel_and_export_snapshot(self):
  ensure_templates();names=[x['name'] for x in catalog()]
  a=services.create_project('chosen');b=services.create_project('other')
  services.set_project_template(a,names[1]);services.set_project_template(b,names[2])
  page=StudioPage(AppState());page.state.set_project(a)
  page._populate_templates(names[0]);page._on_template_pick()
  self.assertEqual(services.project_template_name(a),names[0])
  self.assertEqual(services.project_template_name(b),names[2])
  self.assertTrue(page._tpl_for_project(a)['bg'].startswith('design:paper'))
  snap=copy.deepcopy(page._tpl_for_project(a))
  page._populate_templates(names[3]);page._on_template_pick()
  self.assertNotEqual(page._tpl_for_project(a)['bg'],snap['bg'])
  self.assertTrue(snap['bg'].startswith('design:paper'))
  with patch.object(page,'_export_video_inner',side_effect=lambda *x:copy.deepcopy(page.layout_tpl)):
   self.assertEqual(page._export_video(-1,tpl=snap)['bg'],snap['bg'])
  page.close()

if __name__=='__main__':unittest.main(verbosity=2)
