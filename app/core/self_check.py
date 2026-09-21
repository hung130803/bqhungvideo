"""Kiểm tra bản đóng gói offline, chỉ chạy với dữ liệu và QSettings cách ly."""
import json
import os
from pathlib import Path
import subprocess
import traceback


def run(output: str) -> int:
    if not os.environ.get('BQ_DATA_DIR') or not os.environ.get('BQ_QSETTINGS_INI'):
        raise RuntimeError('Self-check cần BQ_DATA_DIR và BQ_QSETTINGS_INI cách ly.')
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    results = {'ok': False, 'checks': []}
    try:
        from config import DATA_DIR, settings
        from app.version import __version__
        results['version'] = __version__
        from app.database.db import db
        db.execute("INSERT INTO projects(name,assets_dir) VALUES('SELF-CHECK', '')")
        db.backup_to(DATA_DIR / 'check_backup.db')
        results['checks'].append('database WAL snapshot')
        video = DATA_DIR / 'sample.mp4'
        subprocess.run([settings.FFMPEG_PATH, '-y', '-v', 'error', '-f', 'lavfi',
                        '-i', 'color=c=blue:s=160x120:d=1', '-c:v', 'libx264', str(video)],
                       check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        from app.core.ffmpeg_utils import probe
        metadata = probe(video)
        assert metadata.width == 160 and metadata.duration > 0
        results['checks'].append('bundled ffmpeg/ffprobe actual encode')
        from app.core.pipeline import recycle_source, restore_recycled
        moved = recycle_source(video, 'Kênh | kiểm tra', str(DATA_DIR / 'recycle'))
        assert moved and restore_recycled(str(moved), str(DATA_DIR))
        results['checks'].append('recycle/restore invalid Windows channel name')
        import app.queue.jobs  # cv2 trước Qt theo hợp đồng của app
        from PyQt6.QtWidgets import QApplication
        from app.ui.theme import QSS
        from app.ui.state import AppState
        from app.ui.studio_page import StudioPage
        qapp = QApplication.instance() or QApplication([])
        qapp.setStyleSheet(QSS)
        state = AppState()
        page = StudioPage(state)
        results['checks'].append('compiled StudioPage and real QSS')
        from app.ui.shutdown import set_closing
        set_closing()
        page.close()
        state.pool.stop(wait=False)
        db.gap_wal()
        results['ok'] = True
    except Exception:
        results['error'] = traceback.format_exc()
    Path(output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if results['ok'] else 1
