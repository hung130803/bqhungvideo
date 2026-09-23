"""Chạy các cổng offline trong thư mục tạm riêng, không chạm cấu hình thật."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
AREA = Path(os.environ.get('BQ_VALIDATION_DIR') or ROOT.parent / 'validation').resolve()
AREA.mkdir(parents=True, exist_ok=True)
TMP = AREA / 'temp'
TMP.mkdir(exist_ok=True)
environment = dict(os.environ)
environment.update(TEMP=str(TMP), TMP=str(TMP), PYTHONUTF8='1', BQ_BO_MANG='1',
                   BQ_DATA_DIR=str(AREA / 'data'),
                   BQ_DB_PATH=str(AREA / 'data' / 'test.db'),
                   BQ_QSETTINGS_INI=str(AREA / 'settings.ini'),
                   QT_QPA_PLATFORM='offscreen',
                   FFMPEG_PATH=str(ROOT / 'bin' / 'ffmpeg.exe'),
                   FFPROBE_PATH=str(ROOT / 'bin' / 'ffprobe.exe'))
for executable in ('FFMPEG_PATH', 'FFPROBE_PATH'):
    if not Path(environment[executable]).is_file():
        raise SystemExit(f'Missing test dependency: {environment[executable]}')
tests = sys.argv[1:] or [
    'tests/test_pipeline_safety.py', 'tests/test_queue_progress.py', 'tests/test_workspace_ui.py',
    'tests/test_folder_shortcuts.py',
    'tests/test_key_health.py', 'tools/check_startup.py',
    'tests/test_repair_regressions.py', '_test_app_smoke.py',
    '_test_pipe_dialogs.py', '_test_pipe_overlap.py', '_test_cancel_persist.py',
    '_test_lane_starve.py', '_test_shutdown_safety.py', '_test_db_corrupt_guard.py',
    '_test_db_maint.py', '_test_tpl_per_channel.py', '_test_tpl_export_path.py',
    '_test_ui_smooth.py', '_test_reanalyze_clean.py', '_test_clip_count_len.py',
    '_test_chan_search.py', '_test_ai_gate.py', '_test_quota_wait.py',
    '_test_don_rac.py', '_test_so_lieu.py', '_test_json_bao_dung.py',
    '_test_dong_goi.py', '_test_reanalyze_basic.py', '_test_repair_export.py',
    '_test_no_popup.py', '_test_chatter_noi.py',
]
results = []
for name in tests:
    start = time.monotonic()
    logfile = AREA / (Path(name).stem + '.log')
    print('RUN', name, flush=True)
    with logfile.open('w', encoding='utf-8') as stream:
        try:
            result = subprocess.run([sys.executable, '-B', str(ROOT / name)],
                                    cwd=ROOT, env=environment, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=180)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    item = {'test': name, 'exit': code, 'seconds': round(time.monotonic()-start, 2), 'log': str(logfile)}
    results.append(item)
    print(json.dumps(item), flush=True)
    if code != 0:
        print(f'::group::Failure details: {name}', flush=True)
        print('\n'.join(logfile.read_text(encoding='utf-8', errors='replace').splitlines()[-100:]), flush=True)
        print('::endgroup::', flush=True)
    (AREA / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    (AREA / (Path(name).stem + '.result.json')).write_text(json.dumps(item, indent=2), encoding='utf-8')
sys.exit(1 if any(r['exit'] != 0 for r in results) else 0)
