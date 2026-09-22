"""Groq diagnostic regressions: no network, real shared state on disk."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AREA = tempfile.TemporaryDirectory(prefix='bq-key-tests-')
os.environ.update(BQ_DATA_DIR=AREA.name, BQ_DB_PATH=str(Path(AREA.name)/'test.db'),
                  BQ_QSETTINGS_INI=str(Path(AREA.name)/'settings.ini'))
import config
from app.ai import connection_check, key_health, llm


class KeyHealthTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=AREA.name)
        self.data = Path(self.folder.name)
        self.keys = ['gsk_fixture_first_private_key', 'gsk_fixture_second_private_key']
        self.patches = [patch.object(config, 'DATA_DIR', self.data),
                        patch.dict(llm._KEY_STATE, {}, clear=True),
                        patch.object(llm.settings, 'llm_keys_for', return_value=self.keys)]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def test_unobserved_keys_are_not_shown_as_healthy_or_in_use(self):
        rows = llm.key_status('groq')
        self.assertTrue(all(row['state'] == 'unknown' for row in rows))
        self.assertFalse(any(row['in_use'] for row in rows))

    def test_restriction_is_key_and_service_specific(self):
        first, second = self.keys
        llm.mark_provider_restricted('groq', first, 'transcription')
        self.assertEqual(llm.pick_keys('groq', self.keys, scope='transcription'), [second])
        self.assertEqual(llm.pick_keys('groq', self.keys), self.keys)
        llm.mark_ok('groq', first, 'chat')
        self.assertTrue(key_health.blocked('groq', first, 'transcription'))
        llm.ensure_provider_available('groq', self.keys, 'transcription')
        llm.mark_ok('groq', first, 'transcription')
        self.assertEqual(llm.pick_keys('groq', self.keys, scope='transcription'), self.keys)

    def test_failed_recheck_does_not_clear_denial(self):
        first = self.keys[0]
        llm.mark_provider_restricted('groq', first, 'transcription')
        with patch.object(llm, '_call_once', return_value='OK'), patch.object(
                connection_check, '_speech', side_effect=TimeoutError('connection timed out')):
            rows = connection_check.check('groq', 'groq')
        self.assertEqual([row['ok'] for row in rows], [True, False])
        self.assertTrue(key_health.blocked('groq', first, 'transcription'))

    def test_chat_ok_cannot_mask_failed_speech_or_test_other_keys(self):
        with patch.object(llm, '_call_once', return_value='OK') as chat, patch.object(
                connection_check, '_speech', side_effect=RuntimeError('organization_restricted')) as speech:
            rows = connection_check.check('groq', 'groq')
        self.assertEqual([row['ok'] for row in rows], [True, False])
        self.assertIn('Whisper', rows[1]['message'])
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(chat.call_args.args[1], self.keys[0])
        speech.assert_called_once_with(self.keys[0])
        self.assertEqual(llm.key_status('groq')[0]['state'], 'restricted')
        self.assertEqual(llm.key_status('groq')[1]['state'], 'unknown')

    def test_successful_explicit_speech_recheck_restores_only_checked_key(self):
        for key in self.keys:
            llm.mark_provider_restricted('groq', key, 'transcription')
        with patch.object(llm, '_call_once', return_value='OK'), patch.object(connection_check, '_speech'):
            self.assertTrue(all(row['ok'] for row in connection_check.check('groq', 'groq')))
        self.assertFalse(key_health.blocked('groq', self.keys[0], 'transcription'))
        self.assertTrue(key_health.blocked('groq', self.keys[1], 'transcription'))

    def test_empty_chat_answer_is_not_success(self):
        with patch.object(llm, '_call_once', return_value='  '):
            self.assertFalse(connection_check.check('groq', 'local')[0]['ok'])

    def test_worker_state_is_visible_in_ui_without_raw_keys_on_disk(self):
        key = self.keys[0]
        script = "from app.ai import key_health; key_health.record('groq', %r, 'transcription', 'restricted', %r)" % (key, key)
        subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                       env=dict(os.environ, BQ_DATA_DIR=str(self.data)), check=True, timeout=15)
        row = llm.key_status('groq')[0]
        self.assertEqual(row['state'], 'restricted')
        self.assertEqual(row['calls'], 0)
        contents = ''.join(p.name + p.read_text(encoding='utf-8') for p in (self.data/'key_health').iterdir())
        self.assertNotIn(key, contents)
        self.assertIn('[key]', contents)

    def test_legacy_whole_pool_block_cannot_disable_unchecked_keys(self):
        import hashlib
        pool_hash = hashlib.sha256('\n'.join(sorted(self.keys)).encode()).hexdigest()
        (self.data/'ai_provider_blocks.json').write_text(json.dumps({'groq': pool_hash}))
        llm.ensure_provider_available('groq', self.keys)
        self.assertEqual(llm.pick_keys('groq', self.keys), self.keys)

    def test_wait_ignores_blocked_key_in_same_scope(self):
        llm.mark_provider_restricted('groq', self.keys[0], 'transcription')
        llm.mark_limited('groq', self.keys[1], 'try again in 30s')
        self.assertGreater(llm.soonest_ready_wait('groq', self.keys, 'transcription'), 0)
        self.assertEqual(llm.soonest_ready_wait('groq', self.keys, 'chat'), 0)

    def test_restricted_key_never_offered_for_auto_removal(self):
        for status in (400, 403):
            error = urllib.error.HTTPError('https://api.groq.com/test', status, 'Denied', {},
                                           io.BytesIO(b'{"code":"organization_restricted"}'))
            with patch('urllib.request.urlopen', side_effect=error):
                result = llm.check_groq_keys([self.keys[0]], max_workers=1)
            self.assertEqual(result['counts']['restricted'], 1)
            self.assertEqual(result['invalid'], [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
