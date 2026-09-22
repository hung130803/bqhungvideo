"""Groq diagnostic regressions: no network, real shared state on disk."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
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

    def _speech_client(self, on_call):
        def factory(api_key, **kwargs):
            def create(**request):
                return on_call(api_key, request)
            return types.SimpleNamespace(audio=types.SimpleNamespace(
                transcriptions=types.SimpleNamespace(create=create)))
        return factory

    def _speech_result(self):
        return {'segments': [{'start': 0, 'end': 1, 'text': 'kept audio'}],
                'words': [{'start': 0, 'end': 1, 'word': 'kept'}],
                'language': 'en', 'text': 'kept audio'}

    def test_transcription_denied_key_continues_same_chunk_on_next_key(self):
        from app.core.transcribe import _groq_one
        audio = self.data/'chunk.wav'
        audio.write_bytes(b'original audio bytes')
        calls = []
        def respond(key, request):
            calls.append(key)
            self.assertEqual(request['file'].read(), b'original audio bytes')
            if key == self.keys[0]:
                raise RuntimeError('organization_restricted')
            return self._speech_result()
        with patch('openai.OpenAI', side_effect=self._speech_client(respond)):
            result = _groq_one(str(audio), 'en', self.keys)
        self.assertEqual(calls, self.keys)
        self.assertEqual(result[3], 'kept audio')
        self.assertEqual(audio.read_bytes(), b'original audio bytes')
        self.assertTrue(key_health.blocked('groq', self.keys[0], 'transcription'))

    def test_ninth_key_denied_wraps_back_to_working_first_key(self):
        from app.core.transcribe import _groq_one
        audio = self.data/'chunk.wav'
        audio.write_bytes(b'chunk')
        keys = ['fixture-key-'+str(i) for i in range(1, 10)]
        calls = []
        def respond(key, request):
            calls.append(key)
            if key == keys[8]:
                raise RuntimeError('organization_restricted')
            return self._speech_result()
        with patch('openai.OpenAI', side_effect=self._speech_client(respond)):
            result = _groq_one(str(audio), 'en', keys, start_at=8)
        self.assertEqual(calls, [keys[8], keys[0]])
        self.assertEqual(result[3], 'kept audio')

    def test_all_denied_keys_attempted_once_and_reported_accurately(self):
        from app.core.transcribe import _groq_one
        audio = self.data/'chunk.wav'
        audio.write_bytes(b'chunk')
        calls = []
        def respond(key, request):
            calls.append(key)
            raise RuntimeError('organization_restricted')
        with patch('openai.OpenAI', side_effect=self._speech_client(respond)):
            with self.assertRaisesRegex(RuntimeError, 'Tổng 2 key: 2 bị hạn chế'):
                _groq_one(str(audio), 'en', self.keys)
            with self.assertRaisesRegex(llm.LLMError, 'Tổng 2 key: 2 bị hạn chế'):
                _groq_one(str(audio), 'en', self.keys)
        self.assertEqual(calls, self.keys)
        self.assertEqual(audio.read_bytes(), b'chunk')

    def test_pending_key_denied_by_another_worker_is_skipped(self):
        from app.core.transcribe import _groq_one
        audio = self.data/'chunk.wav'
        audio.write_bytes(b'chunk')
        keys = [*self.keys, 'third-fixture-key']
        calls = []
        def respond(key, request):
            calls.append(key)
            if key == keys[0]:
                llm.mark_provider_restricted('groq', keys[1], 'transcription')
                raise RuntimeError('organization_restricted')
            return self._speech_result()
        with patch('openai.OpenAI', side_effect=self._speech_client(respond)):
            _groq_one(str(audio), 'en', keys)
        self.assertEqual(calls, [keys[0], keys[2]])

    def test_chat_rotation_succeeds_after_denial_without_repeating_bad_key(self):
        calls = []
        def respond(provider, key, *args, **kwargs):
            calls.append(key)
            if key == self.keys[0]:
                raise RuntimeError('organization_restricted')
            return 'OK'
        with patch.object(llm, '_call_once', side_effect=respond):
            self.assertEqual(llm.complete_text('test', provider='groq'), 'OK')
            self.assertEqual(llm.complete_text('test again', provider='groq'), 'OK')
        self.assertEqual(calls, [self.keys[0], self.keys[1], self.keys[1]])

    def test_vision_rotation_succeeds_after_denial(self):
        calls = []
        def factory(api_key, **kwargs):
            def create(**request):
                calls.append(api_key)
                if api_key == self.keys[0]:
                    raise RuntimeError('organization_restricted')
                return types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(content='{"ok": true}'))])
            return types.SimpleNamespace(chat=types.SimpleNamespace(
                completions=types.SimpleNamespace(create=create)))
        with patch('openai.OpenAI', side_effect=factory), patch.object(llm.settings, 'groq_keys', return_value=self.keys):
            self.assertEqual(llm.complete_vision_json('test', [], provider='groq'), {'ok': True})
        self.assertEqual(calls, self.keys)

    def test_mixed_key_failures_report_counts_and_no_raw_secret(self):
        llm.mark_provider_restricted('groq', self.keys[0], 'chat')
        llm.mark_invalid('groq', self.keys[1])
        message = llm.key_failure_message('groq', self.keys, 'chat', self.keys[0])
        self.assertIn('Tổng 2 key: 1 bị hạn chế, 1 sai key', message)
        self.assertNotIn(self.keys[0], message)

    def test_chat_quota_reason_survives_last_key_restriction(self):
        def respond(provider, key, *args, **kwargs):
            raise RuntimeError('429 rate limit, try again in 500s' if key == self.keys[0]
                               else 'organization_restricted')
        with patch.object(llm, '_call_once', side_effect=respond):
            with self.assertRaises(llm.LLMError) as error:
                llm.complete_text('test', provider='groq')
        self.assertTrue(llm.is_rate_limit_error(str(error.exception)))
        self.assertFalse(llm.is_org_restricted(str(error.exception)))
        self.assertIn('1 bị hạn chế', str(error.exception))

    def test_parallel_transcription_keeps_all_nine_chunks_in_order(self):
        from app.core import transcribe
        audio = self.data/'source.wav'
        audio.write_bytes(b'source must survive')
        keys = ['fixture-parallel-'+str(i) for i in range(9)]
        def cut(command, **kwargs):
            Path(command[-1]).write_bytes(b'x'*500)
        def respond(key, request):
            if key == keys[8]:
                raise RuntimeError('organization_restricted')
            index = int(Path(request['file'].name).stem[1:])
            return {'segments': [{'start': 0, 'end': 1, 'text': f'part {index}'}],
                    'words': [{'start': 0, 'end': 1, 'word': f'part{index}'}],
                    'language': 'en', 'text': f'part {index}'}
        with patch.object(transcribe.settings, 'groq_keys', return_value=keys), \
                patch.object(transcribe, '_audio_duration', return_value=5400), \
                patch('subprocess.run', side_effect=cut), \
                patch('openai.OpenAI', side_effect=self._speech_client(respond)), \
                patch.object(transcribe, 'va_lo_chep_loi', side_effect=lambda a,s,w,l,p: (s,w,0)):
            result = transcribe._transcribe_groq(str(audio), 'en', None)
        self.assertEqual([s['text'] for s in result['segments']], [f'part {i}' for i in range(9)])
        self.assertEqual([s['start'] for s in result['segments']], [i*600 for i in range(9)])
        self.assertEqual(len(result['words']), 9)
        self.assertEqual(audio.read_bytes(), b'source must survive')
        self.assertTrue(key_health.blocked('groq', keys[8], 'transcription'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
