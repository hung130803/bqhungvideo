"""Đợt 2 hệ thiết kế: studio/thay giọng/dây chuyền/cài đặt dùng vai QSS, không
setStyleSheet trong đường nóng (thẻ clip, khối tiến trình)."""
import ast
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_design2_'))
for k, v in dict(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA/'test.db'),
                 BQ_QSETTINGS_INI=str(AREA/'settings.ini'),
                 QT_QPA_PLATFORM='offscreen').items():
    os.environ.setdefault(k, v)
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: F401,E402
from PyQt6.QtWidgets import QApplication, QLabel, QProgressBar  # noqa: E402

APP = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402


def _calls_in(func_name, path, attr):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return [n for n in ast.walk(node) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == attr]
    raise AssertionError(f'không thấy hàm {func_name}')


class HotPathsHaveNoStylesheets(unittest.TestCase):
    STUDIO = ROOT/'app'/'ui'/'studio_page.py'

    def test_clip_card_and_progress_use_properties(self):
        for fn in ('_clip_row', '_update_job_progress', '_job_progress_widget'):
            self.assertEqual(_calls_in(fn, self.STUDIO, 'setStyleSheet'), [], fn)
        self.assertNotIn('"_bq_ss"', self.STUDIO.read_text(encoding='utf-8'))
        self.assertTrue(_calls_in('_update_job_progress', self.STUDIO, 'set_phase') or
                        'set_phase(' in self.STUDIO.read_text(encoding='utf-8'))

    def test_inline_stylesheets_shrunk(self):
        n = {f: (ROOT/'app'/'ui'/f).read_text(encoding='utf-8').count('.setStyleSheet(')
             for f in ('studio_page.py', 'thay_giong_dialog.py', 'batch_page.py',
                       'batch_channels.py', 'recap_settings.py')}
        # trước đợt 2: 92 / 47 / 4 / 1 / 7
        self.assertLessEqual(n['studio_page.py'], 10, n)
        self.assertLessEqual(n['thay_giong_dialog.py'], 3, n)
        self.assertEqual(n['batch_page.py'] + n['batch_channels.py'], 0, n)
        self.assertLessEqual(n['recap_settings.py'], 1, n)


class Phase2Helpers(unittest.TestCase):
    def setUp(self):
        theme.apply_theme(APP)

    def test_set_style_clears_inline_and_sets_role_tone(self):
        lb = QLabel('x'); lb.setStyleSheet('color:#FFB86C; font-size:11px;')
        theme.set_style(lb, 'hint', 'warn')
        self.assertEqual(lb.styleSheet(), '')
        self.assertEqual((lb.property('role'), lb.property('tone')), ('hint', 'warn'))
        lb.show(); APP.processEvents()
        self.assertEqual(lb.font().pixelSize(), theme.FS_XS)
        self.assertEqual(lb.palette().color(lb.foregroundRole()).name().upper(), theme.WARN.upper())
        lb.close()

    def test_color_mappers(self):
        self.assertEqual(theme.phase_for_color('#a78bfa'), 'analyze')
        self.assertEqual(theme.phase_for_color(theme.TEAL), 'export')
        self.assertEqual(theme.phase_for_color('#123456'), 'accent')
        self.assertEqual(theme.tone_for_color('#a6e3a1'), 'success')
        self.assertEqual(theme.tone_for_color(theme.DANGER), 'danger')
        self.assertEqual(theme.tone_for_color('#123456'), 'text')

    def test_new_selectors_present(self):
        for sel in ('QWidget#clipCard', 'QWidget#ctlPanel', 'QLabel#stepDot', 'QLabel#score[tone=',
                    'QWidget#jobProgBox', 'QTableView[table', 'QLabel[banner=', 'QPushButton[variant="chip"]',
                    'QFrame#aiCard', 'QLabel[role="heading"]', 'QLabel[role="tag"]'):
            self.assertIn(sel, theme.QSS, sel)

    def test_job_bar_phase_property_drives_colour(self):
        bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(50)
        theme.set_phase(bar, 'export'); bar.resize(200, 20); bar.show(); APP.processEvents()
        img = bar.grab().toImage()
        c = img.pixelColor(5, 10).name().upper()
        bar.close()
        self.assertEqual(c, theme.TEAL.upper())


class RecapQualityLabels(unittest.TestCase):
    def test_max_is_recommended_values_unchanged(self):
        src = (ROOT/'app'/'ui'/'recap_settings.py').read_text(encoding='utf-8')
        self.assertIn('"Tối đa (khuyên dùng)', src)
        self.assertNotIn('Cân bằng (khuyên dùng)', src)
        for key in ('"balance"),', '"max"),', '"save")):'):
            self.assertIn(key, src)


if __name__ == '__main__':
    unittest.main()
