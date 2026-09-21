"""Cắt/xuất thật bằng handler + ffmpeg; xác minh Part rồi recycle/restore gốc."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
T = Path(tempfile.mkdtemp(prefix='repair_export_'))
os.environ.update(BQ_DATA_DIR=str(T), BQ_DB_PATH=str(T / 'studio.db'),
                  BQ_QSETTINGS_INI=str(T / 'settings.ini'), QT_QPA_PLATFORM='offscreen',
                  FFMPEG_PATH=str(ROOT / 'bin/ffmpeg.exe'),
                  FFPROBE_PATH=str(ROOT / 'bin/ffprobe.exe'))
import _test_guard
import app.queue.jobs
from app import services
from app.database.db import db
from app.queue.worker import WorkerPool
from app.core import pipeline
from app.core.ffmpeg_utils import probe

source = T / 'source.mp4'
subprocess.run([str(ROOT / 'bin/ffmpeg.exe'), '-y', '-v', 'error', '-f', 'lavfi',
                '-i', 'testsrc=size=320x240:rate=15:duration=4', '-f', 'lavfi',
                '-i', 'sine=frequency=440:duration=4', '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(source)],
               check=True, timeout=30)
pid = services.create_project('Kênh | kiểm tra xuất thật')
vid = services.import_video(pid, str(source))
clip = db.insert("INSERT INTO clips(video_id, start_sec, end_sec, title, status) "
                 "VALUES(?, 0, 2, 'Fixture export', 'suggested')", (vid,))
from app.queue.resource_manager import PROFILE, profile_dict
pool = WorkerPool(profile_dict(PROFILE))
jid = services.enqueue_export(pool, clip, vid, pid, out_w=320, out_h=240, mode='center',
                              captions=False, out_dir=str(T / 'output'), part_no=1,
                              flat_export=True, fx_fade=False, fx_whoosh=False,
                              hieu_ung='tat', chuyen_canh='tat')
row = db.query_one('SELECT type,payload FROM jobs WHERE id=?', (jid,))
pool._run_job(jid, row['type'], row['payload'])
row = db.query_one('SELECT status,error,result FROM jobs WHERE id=?', (jid,))
assert row['status'] == 'done', row['error']
result = db.loads(row['result'], {})
assert result['verified_output']['size'] > 0
part = Path(result['export_path'])
info = probe(part)
assert 1.8 <= info.duration <= 2.3 and info.width == 320 and info.has_audio, info
moved = pipeline.recycle_source(source, 'Kênh | kiểm tra xuất thật', str(T / 'recycle'))
assert moved and not source.exists() and part.exists()
restored = pipeline.restore_recycled(str(moved), str(T))
assert restored and probe(restored).duration >= 3.9
pool.stop(wait=True)
print('PASS: real export handler + verified video/audio + recycle/restore source')
