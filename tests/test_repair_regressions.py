"""Hồi quy lỗi rà soát 2026-09; hoàn toàn cách ly dữ liệu và không gọi API."""
import ast
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SANDBOX = tempfile.TemporaryDirectory(prefix='bqhung_regression_', dir=ROOT.parent,
                                      ignore_cleanup_errors=True)
os.environ.update(BQ_DATA_DIR=SANDBOX.name,
                  BQ_DB_PATH=str(Path(SANDBOX.name) / 'studio.db'),
                  BQ_QSETTINGS_INI=str(Path(SANDBOX.name) / 'settings.ini'),
                  QT_QPA_PLATFORM='offscreen')
from app.database.db import Database, db
from app.core import pipeline, dbmaint
from app.ai import llm


def actual_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    code = compile(ast.Module(body=[node], type_ignores=[]), path, 'exec')
    exec(code, namespace)
    return namespace[name]


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SANDBOX.name)
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_windows_channel_roundtrip(self):
        source = self.folder / 'channel' / 'source.mp4'
        source.parent.mkdir()
        source.write_bytes(b'original')
        channel = 'COURT NERDS | Your Court Watch Source'
        target = pipeline.recycle_source(source, channel, str(self.folder / 'recycle'), '2026-09-21')
        self.assertIsNotNone(target)
        self.assertEqual(target.read_bytes(), b'original')
        self.assertFalse(source.exists())
        rows = pipeline.list_recycled(str(self.folder / 'recycle'), '2026-09-21')
        self.assertEqual(rows[0]['channel'], channel)
        restored = pipeline.restore_recycled(str(target), str(source.parent))
        self.assertEqual(restored.read_bytes(), b'original')

    def test_channel_names_no_path_escape_or_collision(self):
        values = ['a/b', 'a:b', 'a|b', '..', 'CON', 'NUL.txt', 'name.', 'normal']
        names = [pipeline.channel_dir_name(s) for s in values]
        self.assertEqual(len(set(names)), len(names))
        for n in names:
            self.assertNotRegex(n, r'[<>:"/\\|?*]')
            self.assertNotIn(n, ['.', '..'])

    def test_cross_volume_copy_moves_only_complete_file(self):
        source, target = self.folder / 'a.mp4', self.folder / 'b.mp4'
        source.write_bytes(b'x' * 1024)
        rename = Path.rename
        def cross(path, dst):
            if path == source:
                raise OSError(errno.EXDEV, 'cross volume')
            return rename(path, dst)
        with patch.object(Path, 'rename', cross):
            self.assertTrue(pipeline._move_with_retry(source, target, tries=1))
        self.assertFalse(source.exists())
        self.assertEqual(target.stat().st_size, 1024)

    def test_partial_copy_preserves_source(self):
        source, target = self.folder / 'a.mp4', self.folder / 'b.mp4'
        source.write_bytes(b'original')
        with (patch.object(Path, 'rename', side_effect=OSError(errno.EXDEV, 'cross volume')),
              patch('shutil.copy2', side_effect=OSError('disk full'))):
            self.assertFalse(pipeline._move_with_retry(source, target, tries=1))
        self.assertEqual(source.read_bytes(), b'original')
        self.assertFalse(target.exists())

    def test_snapshot_includes_uncheckpointed_wal(self):
        database = Database(self.folder / 'data.db')
        database.conn().execute('PRAGMA wal_autocheckpoint=0')
        self.addCleanup(database._reset_conn)
        database.execute("INSERT INTO projects(name, assets_dir) VALUES('WAL-only', '')")
        target = self.folder / 'backup.db'
        database.backup_to(target)
        c = sqlite3.connect(target)
        try:
            self.assertEqual(c.execute('SELECT name FROM projects').fetchone()[0], 'WAL-only')
        finally:
            c.close()
        database._reset_conn()

    def test_corrupt_db_backup_failure_never_wipes(self):
        path = self.folder / 'broken.db'
        path.write_bytes(b'not sqlite original data')
        with (patch.object(Database, '_backup_db_file', return_value=None),
              patch.object(Database, '_wipe_db_files') as wipe):
            with self.assertRaises(RuntimeError):
                Database(path)
        wipe.assert_not_called()
        self.assertEqual(path.read_bytes(), b'not sqlite original data')

    def test_backup_failure_aborts_transcript_deletion(self):
        with (patch.object(dbmaint, '_co_the_don', return_value=[(42, 200)]),
             patch.object(dbmaint, 'sao_luu_db', return_value=''),
             patch.object(dbmaint.db, 'execute') as execute):
            self.assertEqual(dbmaint.don_chep_loi_cu(), (0, 0.0))
        execute.assert_not_called()

    def test_json_repair_never_changes_quoted_content(self):
        s = '{"text":"hello, ] and , } and \\\"quote\\\"", "items":[1,2,],}'
        parsed = json.loads(llm._bo_phay_thua(s))
        self.assertEqual(parsed['text'], 'hello, ] and , } and "quote"')
        self.assertEqual(parsed['items'], [1, 2])

    def test_key_rotation_preserves_priority(self):
        with patch.dict(llm._KEY_STATE, {}, clear=True):
            llm.mark_invalid('groq', 'bad')
            llm.mark_limited('groq', 'wait', 'rate limit')
            self.assertEqual(llm.pick_keys('groq', ['a', 'b', 'wait', 'bad'], 1), ['b', 'a', 'wait'])

    def test_org_restriction_never_retries_denied_key(self):
        from app.core.transcribe import _groq_one
        audio = self.folder / 'audio.wav'
        audio.write_bytes(b'fixture')
        call = Mock(side_effect=RuntimeError('organization_restricted'))
        client = types.SimpleNamespace(audio=types.SimpleNamespace(transcriptions=types.SimpleNamespace(create=call)))
        with patch('openai.OpenAI', return_value=client), patch.dict(llm._KEY_STATE, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'organization_restricted'):
                _groq_one(str(audio), 'en', ['first'])
        self.assertEqual(call.call_count, 1)
        self.assertTrue(pipeline.is_configuration_error('organization_restricted'))
        with self.assertRaisesRegex(llm.LLMError, 'organization_restricted'):
            llm.ensure_provider_available('groq', ['first'], scope='transcription')
        llm.ensure_provider_available('groq', ['first', 'second'], scope='transcription')
        llm.ensure_provider_available('groq', ['first', 'second'])
        self.assertEqual(llm.pick_keys('groq', ['first', 'second'], scope='transcription'), ['second'])
        llm.mark_ok('groq', 'first', scope='transcription')
        self.assertEqual(llm.pick_keys('groq', ['first', 'second'], scope='transcription'), ['first', 'second'])

    def test_silent_process_deadline(self):
        from app.core.process_guard import ProcessDeadline
        p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], stdout=subprocess.PIPE)
        start = time.monotonic()
        deadline = ProcessDeadline(p, 0.3)
        try:
            self.assertEqual(p.stdout.read(), b'')
            p.wait(timeout=5)
        finally:
            deadline.cancel()
            p.stdout.close()
            if p.poll() is None:
                p.kill()
        self.assertLess(time.monotonic() - start, 6)
        self.assertTrue(deadline.expired.is_set())

    def test_temp_sweep_does_not_touch_foreign_mei(self):
        from app.core.tempsweep import quet_temp
        foreign = self.folder / '_MEIforeign'
        foreign.mkdir()
        (foreign / 'data').write_bytes(b'keep')
        os.utime(foreign, (1, 1))
        with patch.dict(os.environ, {'TEMP': str(self.folder)}):
            self.assertEqual(quet_temp(), (0, 0))
        self.assertTrue(foreign.exists())

    def test_enqueue_concurrent_preserves_snapshot(self):
        from app.queue.worker import WorkerPool
        pool = object.__new__(WorkerPool)
        pool._notify = lambda: None
        key = 'regression-' + str(time.time_ns())
        def enqueue(i):
            try:
                return pool.enqueue('fixture', {'template': i}, dedup_key=key)
            finally:
                db.conn().close()
                db._local.conn = None
        with ThreadPoolExecutor(max_workers=8) as executor:
            ids = list(executor.map(enqueue, range(20)))
        self.assertEqual(len(set(ids)), 1)
        original = db.query_one('SELECT payload FROM jobs WHERE id=?', (ids[0],))['payload']
        pool.enqueue('fixture', {'template': 'changed'}, dedup_key=key)
        self.assertEqual(db.query_one('SELECT payload FROM jobs WHERE id=?', (ids[0],))['payload'], original)

    def test_stop_late_handler_keeps_pending_and_cancel_stays_canceled(self):
        from app.queue import worker
        for user_cancel in (False, True):
            pool = object.__new__(worker.WorkerPool)
            pool._stop = threading.Event()
            pool._lock = threading.Lock()
            pool._inflight = set()
            pool._inflight_gpu = {}
            pool._inflight_tg = set()
            pool._canceled = set()
            pool._notify = lambda: None
            pool.profile = types.SimpleNamespace()
            jid = pool.enqueue('regression_stop', {})
            def handler(payload, ctx):
                pool._stop.set()
                db.execute("UPDATE jobs SET status=?, cancel_req=? WHERE id=?",
                           ('canceled' if user_cancel else 'pending', int(user_cancel), jid))
                raise worker.CanceledError()
            with patch.dict(worker._HANDLERS, {'regression_stop': handler}):
                pool._run_job(jid, 'regression_stop', '{}')
            self.assertEqual(db.query_one('SELECT status FROM jobs WHERE id=?', (jid,))['status'],
                             'canceled' if user_cancel else 'pending')

    def test_export_poll_keeps_tracking_when_db_read_fails(self):
        ent = {'jobs': {12}, 'ctx': {'entry': 1, 'path': 'unused', 'name': 'channel', 'file': 'source'}}
        page = types.SimpleNamespace(_pipe_exports={9: ent})
        fake_db = Mock()
        fake_db.query.side_effect = sqlite3.OperationalError('locked')
        fn = actual_function('app/ui/studio_page.py', '_pipe_poll_exports', {
            'db': fake_db, 'services': types.SimpleNamespace(job_states=lambda j: {12: 'done'}),
            'Path': Path, 'os': os, 'MARK_STUCK': '[GỐC KẸT]'})
        with self.assertRaises(sqlite3.OperationalError):
            fn(page)
        self.assertIs(page._pipe_exports[9], ent)

    def test_export_missing_one_part_keeps_original(self):
        original = self.folder / 'original.mp4'
        original.write_bytes(b'original')
        part = self.folder / 'Part 1.mp4'
        part.write_bytes(b'part')
        page = types.SimpleNamespace(_pipe_exports={9: {'jobs': {12}, 'ctx': {
            'entry': 1, 'path': str(original), 'name': 'channel', 'file': 'original'}}},
            _pipe_log=lambda m: None)
        fn = actual_function('app/ui/studio_page.py', '_pipe_poll_exports', {
            'db': types.SimpleNamespace(query=lambda *a: [
                {'id': 1, 'export_path': str(part)}, {'id': 2, 'export_path': None}]),
            'services': types.SimpleNamespace(job_states=lambda j: {12: 'done'}),
            'Path': Path, 'os': os, 'MARK_STUCK': '[GỐC KẸT]'})
        with patch.object(pipeline, 'mark_error') as error, patch.object(pipeline, 'delete_or_recycle') as recycle:
            fn(page)
        error.assert_called_once()
        recycle.assert_not_called()
        self.assertTrue(original.exists())

    def test_resume_button_retries_stuck_even_without_taken(self):
        from PyQt6.QtWidgets import QMessageBox
        fn = actual_function('app/ui/studio_page.py', '_pipe_resume_dialog', {})
        page = types.SimpleNamespace(_pipe_retry_stuck=Mock(return_value=1))
        with patch.object(pipeline, 'list_taken', return_value=[]), patch.object(QMessageBox, 'information'):
            fn(page)
        page._pipe_retry_stuck.assert_called_once()

    def test_overlay_mode_does_not_require_demucs(self):
        from PyQt6.QtWidgets import QMessageBox
        fn = actual_function('app/ui/thay_giong_dialog.py', '_chay', {'QMessageBox': QMessageBox})
        page = types.SimpleNamespace(_do_demucs=lambda: {'co': False}, _de_giong=lambda: True,
                                    _video_trong_thu_muc=Mock(return_value=[]))
        with patch.object(QMessageBox, 'warning') as warning, patch.object(QMessageBox, 'information'):
            self.assertEqual(fn(page), 0)
        warning.assert_not_called()
        page._video_trong_thu_muc.assert_called_once()

    def test_password_encryption_failure_never_stores_plain_base64(self):
        fn = actual_function('app/ui/login.py', '_enc', {'_dpapi': lambda *a, **k: None})
        self.assertEqual(fn('dummy password fixture'), '')

    def test_hash_covers_tail_of_one_to_two_mb_file(self):
        from app.services import _file_hash
        a, b = self.folder / 'a.mp4', self.folder / 'b.mp4'
        a.write_bytes(b'x' * (1 << 20) + b'a' * (1 << 19))
        b.write_bytes(b'x' * (1 << 20) + b'b' * (1 << 19))
        self.assertNotEqual(_file_hash(str(a)), _file_hash(str(b)))

    def test_source_requires_two_stable_observations(self):
        source = self.folder / 'downloading.mp4'
        source.write_bytes(b'a')
        self.assertFalse(pipeline.observe_source(source, now=0))
        self.assertFalse(pipeline.observe_source(source, now=9))
        self.assertTrue(pipeline.observe_source(source, now=10))
        source.write_bytes(b'changed content')
        self.assertFalse(pipeline.observe_source(source, now=12))
        self.assertFalse(pipeline.observe_source(source, now=21))
        self.assertTrue(pipeline.observe_source(source, now=22))

    def test_metrics_do_not_mix_missing_retention_with_raw_views(self):
        from app.ai.so_lieu import so_lieu_cua_kenh
        rows = [{'ten_file': f'{i}', 'dai': 100, 'xem_tb': i * 10, 'view': 5} for i in range(1, 7)]
        rows.append({'ten_file': 'unknown', 'dai': 0, 'xem_tb': 0, 'view': 9999999})
        fake = types.SimpleNamespace(query=lambda *args: rows)
        result = so_lieu_cua_kenh(1, fake, vi_du=2, toi_thieu=4)
        self.assertEqual(result['tot'][0]['ten_file'], '6')
        self.assertNotIn('unknown', [r['ten_file'] for r in result['tot'] + result['te']])

    def test_restore_snapshot_preserves_old_db_bundle(self):
        from app.core.db_restore import restore_snapshot
        backup = self.folder / 'backup.db'
        target = self.folder / 'studio.db'
        database = Database(backup)
        database.execute("INSERT INTO projects(name,assets_dir) VALUES('restored','')")
        database._reset_conn()
        target.write_bytes(b'old database')
        Path(str(target) + '-wal').write_bytes(b'old wal')
        Path(str(target) + '-shm').write_bytes(b'old shm')
        saved = restore_snapshot(backup, target)
        self.assertEqual((saved / 'studio.db').read_bytes(), b'old database')
        self.assertEqual((saved / 'studio.db-wal').read_bytes(), b'old wal')
        self.assertFalse(Path(str(target) + '-wal').exists())
        c = sqlite3.connect(target)
        try:
            self.assertEqual(c.execute('SELECT name FROM projects').fetchone()[0], 'restored')
        finally:
            c.close()

    def test_update_rejects_traversal(self):
        from app.core import self_update as su
        archive = self.folder / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escape.txt', 'bad')
        with patch.object(su, 'UPDATES_DIR', self.folder / 'updates'):
            with self.assertRaises(RuntimeError):
                su.extract(archive)
        self.assertFalse((self.folder / 'escape.txt').exists())

    def test_update_checksum_mismatch_never_finalizes_download(self):
        from app.core import self_update as su
        response = io.BytesIO(b'x' * (1 << 20))
        response.headers = {'Content-Length': str(1 << 20)}
        with patch.object(su, 'UPDATES_DIR', self.folder), patch('urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'SHA256'):
                su.download('https://fixture.invalid/update.zip', 'v0', expected_digest='sha256:' + '0' * 64)
        self.assertFalse(list(self.folder.glob('*.zip')))
        self.assertFalse(list(self.folder.glob('*.partial')))

    @unittest.skipUnless(os.name == 'nt', 'PowerShell updater is Windows-only')
    def test_update_transaction_restores_exe_and_internal_on_failure(self):
        from app.core.update_swap import SWAP_SCRIPT
        source, destination = self.folder / 'source', self.folder / 'app'
        for root, value in [(source, b'new'), (destination, b'old')]:
            (root / '_internal').mkdir(parents=True)
            (root / '_internal' / 'lib.txt').write_bytes(value)
            (root / 'BQHungVideo.exe').write_bytes(value)
        plan = {'source': str(source), 'destination': str(destination), 'exe': 'BQHungVideo.exe',
                'processId': 0, 'token': uuid.uuid4().hex, 'relaunch': False,
                'files': {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in source.rglob('*') if p.is_file()}}
        plan_path = self.folder / 'plan.json'
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        script_path = self.folder / 'apply.ps1'
        # Inject failure after BOTH replacements, before successful completion.
        script_path.write_text(SWAP_SCRIPT.replace("    Log 'Update complete;", "    throw 'fixture forced failure'\n    Log 'Update complete;"), encoding='utf-8-sig')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(script_path), '-PlanFile', str(plan_path)], capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 1, result.stderr)
        log = Path(str(plan_path) + '.log')
        self.assertTrue((Path(str(plan_path) + '.journal')).exists(),
                        (log.read_text(encoding='utf-8-sig') if log.exists() else '') + str(result.stderr))
        self.assertEqual((destination / 'BQHungVideo.exe').read_bytes(), b'old')
        self.assertEqual((destination / '_internal' / 'lib.txt').read_bytes(), b'old')
        # Chính helper không tiêm lỗi phải cài được trọn bộ và giữ bản cũ.
        plan['token'] = uuid.uuid4().hex
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        script_path.write_text(SWAP_SCRIPT, encoding='utf-8-sig')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(script_path), '-PlanFile', str(plan_path)], capture_output=True,
                                timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((destination / 'BQHungVideo.exe').read_bytes(), b'new')
        self.assertEqual((destination / '_internal' / 'lib.txt').read_bytes(), b'new')
        backup = destination / ('.update-backup-' + plan['token'])
        self.assertEqual((backup / 'BQHungVideo.exe').read_bytes(), b'old')


if __name__ == '__main__':
    unittest.main(verbosity=2)
