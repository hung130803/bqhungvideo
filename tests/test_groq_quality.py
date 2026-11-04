"""Mức suy nghĩ Groq theo từng việc + lưới hạ mức. Không mạng: OpenAI giả."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AREA = tempfile.TemporaryDirectory(prefix='bq-groq-quality-')
os.environ.setdefault('BQ_DATA_DIR', AREA.name)
os.environ.setdefault('BQ_QSETTINGS_INI', str(Path(AREA.name) / 's.ini'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import openai  # noqa: E402
import config  # noqa: E402
from app.ai import llm  # noqa: E402


class _FakeGroq:
    """Ghi mọi lượt create(); trả lần lượt các (content, finish_reason)."""
    calls: list = []
    replies: list = []

    def __init__(self, api_key=None, **_kw):
        self.api_key = api_key
        self.chat = self
        self.completions = self

    def create(self, **kw):
        _FakeGroq.calls.append(dict(kw, _key=self.api_key))
        content, finish = (_FakeGroq.replies.pop(0) if _FakeGroq.replies
                           else ('{"ok": 1}', 'stop'))

        class _M:
            pass
        m = _M()
        m.content = content
        c = _M()
        c.message, c.finish_reason = m, finish
        u = _M()
        u.completion_tokens, u.prompt_tokens = 4000, 900
        r = _M()
        r.choices, r.usage = [c], u
        return r


class GroqQualityTests(unittest.TestCase):
    def setUp(self):
        self.data = Path(tempfile.mkdtemp(dir=AREA.name))
        self.keys = ['gsk_fixture_quality_one', 'gsk_fixture_quality_two',
                     'gsk_fixture_quality_three']
        _FakeGroq.calls, _FakeGroq.replies = [], []
        self.patches = [
            patch.object(config, 'DATA_DIR', self.data),
            patch.dict(llm._KEY_STATE, {}, clear=True),
            patch.object(llm.settings, 'llm_keys_for', return_value=self.keys),
            patch.object(llm.settings.__class__, 'GROQ_REASONING_EFFORT', 'high'),
            patch.object(llm.settings.__class__, 'GROQ_REASONING_EFFORT_TASKS', ''),
            patch.object(openai, 'OpenAI', _FakeGroq),
            patch.object(llm, 'chuoi_model_groq',
                         lambda m=None: ['openai/gpt-oss-120b', 'groq/compound']),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def efforts(self):
        return [c.get('reasoning_effort') for c in _FakeGroq.calls]

    def test_selection_prompt_sends_high(self):
        from app.modules import m1_highlight as m1
        out = llm.complete_json('chọn đoạn', system=m1._SEL_SYSTEM, provider='groq')
        self.assertEqual(out, {'ok': 1})
        self.assertEqual(self.efforts(), ['high'])

    def test_title_and_judge_send_high(self):
        llm.complete_json('tiêu đề', provider='groq',
                          system='Bạn là chuyên gia đặt tiêu đề video viral.')
        from app.ai import chon_doan
        clips = [{'segments': [[0, 5]]}, {'segments': [[5, 10]]}]
        tr = {'segments': [{'start': 0, 'end': 5, 'text': 'một'},
                           {'start': 5, 'end': 10, 'text': 'hai'}]}
        _FakeGroq.replies = [('[{"index":0,"score":80},{"index":1,"score":20}]', 'stop')]
        r = chon_doan.cham_mu(clips, tr, lambda p, **k: llm.complete_text(p, provider='groq', **k))
        self.assertEqual(r[0]['score'], 80.0)
        self.assertEqual(self.efforts(), ['high', 'high'])

    def test_recap_context_sends_high_but_translation_stays_low(self):
        from app.ai import dich
        llm.complete_json('dịch', system=dich._SYSTEM, provider='groq')
        with llm.tac_vu('recap'):
            llm.complete_json('viết kịch bản', provider='groq')
            with llm.tac_vu('translate'):   # cham_dich bọc kiểu này
                llm.complete_json('chấm dịch', provider='groq')
        self.assertEqual(self.efforts(), ['low', 'high', 'low'])

    def test_toggle_off_restores_low_everywhere(self):
        with patch.object(llm.settings.__class__, 'GROQ_REASONING_EFFORT', 'low'):
            with llm.tac_vu('select'):
                llm.complete_json('x', provider='groq')
        self.assertEqual(self.efforts(), ['low'])

    def test_per_task_override(self):
        with patch.object(llm.settings.__class__, 'GROQ_REASONING_EFFORT_TASKS',
                          'judge=medium, translate=high'):
            self.assertEqual(llm.muc_suy_nghi_cho('judge'), 'medium')
            self.assertEqual(llm.muc_suy_nghi_cho('translate'), 'high')
            self.assertEqual(llm.muc_suy_nghi_cho('select'), 'high')
            self.assertEqual(llm.muc_suy_nghi_cho(None), 'low')

    def test_narrow_output_space_downgrades_before_sending(self):
        with llm.tac_vu('select'):
            self.assertEqual(llm.muc_cho_loi_goi('', '', 6000), 'high')
            self.assertEqual(llm.muc_cho_loi_goi('', '', 3000), 'medium')
            self.assertEqual(llm.muc_cho_loi_goi('', '', 1024), 'low')

    def test_empty_or_cut_high_answer_retries_lower_on_other_key(self):
        _FakeGroq.replies = [('', 'length'), ('{"ok": 2}', 'stop')]
        with llm.tac_vu('select'):
            out = llm.complete_json('chọn', provider='groq')
        self.assertEqual(out, {'ok': 2})
        self.assertEqual(self.efforts(), ['high', 'medium'])
        models = [c['model'] for c in _FakeGroq.calls]
        self.assertEqual(models, ['openai/gpt-oss-120b'] * 2)   # không rơi model yếu
        k1, k2 = (c['_key'] for c in _FakeGroq.calls)
        self.assertNotEqual(k1, k2)
        for k in (k1, k2):                                       # key KHÔNG bị đốt
            st = llm._KEY_STATE.get(('groq', k), {})
            self.assertNotIn(st.get('state'), ('invalid', 'limited'))
        log = list((self.data / 'logs').glob('llm_rong_*.log'))
        self.assertTrue(log and 'hạ suy nghĩ xuống medium' in log[0].read_text('utf-8'))
        self.assertIsNone(getattr(llm._LAN, 'muc_tran', None))   # phạm vi đã xoá

    def test_downgrade_chain_reaches_low_then_stops(self):
        _FakeGroq.replies = [('', 'stop'), ('{"cut', 'length'), ('{"ok": 3}', 'stop')]
        with llm.tac_vu('recap'):
            out = llm.complete_json('viết', provider='groq')
        self.assertEqual(out, {'ok': 3})
        self.assertEqual(self.efforts(), ['high', 'medium', 'low'])

    def test_low_effort_empty_keeps_old_model_chain(self):
        _FakeGroq.replies = [('', 'stop'), ('{"ok": 4}', 'stop')]
        out = llm.complete_json('dịch', provider='groq')
        self.assertEqual(out, {'ok': 4})
        self.assertEqual([c['model'] for c in _FakeGroq.calls],
                         ['openai/gpt-oss-120b', 'groq/compound'])

    def test_non_reasoning_model_gets_no_reasoning_effort(self):
        with patch.object(llm, 'chuoi_model_groq', lambda m=None: ['groq/compound']):
            with llm.tac_vu('select'):
                llm.complete_json('x', provider='groq')
        self.assertNotIn('reasoning_effort', _FakeGroq.calls[0])


class QualityToggleTests(unittest.TestCase):
    def test_toggle_round_trip(self):
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])  # noqa: F841
        data = Path(tempfile.mkdtemp(dir=AREA.name))
        cls = config.Settings
        with patch.object(config, 'DATA_DIR', data), \
                patch.object(cls, 'GROQ_REASONING_EFFORT', 'high'), \
                patch.object(cls, 'RECAP_QUALITY', 'max'):
            from app.ui.recap_settings import RecapSettingsDialog
            d = RecapSettingsDialog()
            self.assertTrue(d.ai_max.isChecked())
            self.assertEqual(d.quality.currentData(), 'max')
            self.assertIn('Chất lượng AI tối đa', d.ai_max.text())
            d.ai_max.setChecked(False)
            self.assertEqual(d.quality.currentData(), 'balance')
            d._save()
            self.assertEqual(cls.GROQ_REASONING_EFFORT, 'low')
            self.assertEqual(cls.RECAP_QUALITY, 'balance')
            env = (data / '.env').read_text('utf-8')
            self.assertIn('GROQ_REASONING_EFFORT=low', env)
            d2 = RecapSettingsDialog()
            self.assertFalse(d2.ai_max.isChecked())
            d2.ai_max.setChecked(True)
            d2._save()
            self.assertEqual(cls.GROQ_REASONING_EFFORT, 'high')
            self.assertEqual(cls.RECAP_QUALITY, 'max')

    def test_defaults(self):
        import importlib
        src = (ROOT / 'config.py').read_text('utf-8')
        self.assertIn('_env("GROQ_REASONING_EFFORT", "high")', src)
        self.assertIn('_env("RECAP_QUALITY", "max")', src)
        importlib.import_module('config')


if __name__ == '__main__':
    unittest.main()
