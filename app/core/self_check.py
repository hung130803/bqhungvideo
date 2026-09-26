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
        from app.ui.fonts import load_fonts
        load_fonts()
        from app.core.editorial import validate
        from app.ui.editorial_dialog import EditorialDialog
        from app.core.ffmpeg_utils import export_canvas_clip, _assets_sfx_dir
        parts = [dict(start=0., end=1., role='hook', mode='narrate', text='Kiểm tra')]
        plan = validate(dict(version=1, style='clean', events=[
            dict(part=0, offset=.1, duration=.5, kind='label', text='Kiểm tra chữ')]), parts)
        editor = EditorialDialog(None, str(video), parts, plan)
        assert editor.checked()['events'][0]['text'] == 'Kiểm tra chữ'
        editor.reject()
        assert len(list(_assets_sfx_dir().glob('*/ed_*.opus'))) == 20
        from app.core.music_library import catalog,resolve
        from app.ui.music_picker import MusicPicker
        tracks=catalog();assert len(tracks)==14
        for track in tracks:assert Path(resolve('bqmusic:'+track['id'])).is_file()
        picker=MusicPicker(current='bqmusic:sector',allow_auto=False)
        assert picker.items.count()==14
        picker.reject()
        assert len(list(_assets_sfx_dir().glob('*/casino_*.opus')))==55
        results['checks'].append('compiled music browser, 14 verified CC0 tracks and 55 new sound files')
        edited = DATA_DIR / 'editorial.mp4'
        export_canvas_clip(video, edited, [(0, 1)], (.5, .5, .9), bg='black',
                           out_w=180, out_h=320, encoder='libx264', fx_fade=False,
                           fx_whoosh=False, hieu_ung='tat', edit_plan=plan, edit_parts=parts,bgm_path=resolve('bqmusic:sector'))
        assert abs(probe(edited).duration - 1.) < .15
        results['checks'].append('compiled editorial dialog, Unicode render and 20 new sound assets')
        from app.core.story_craft import word_budget,delivery_rate
        assert word_budget(12,'vi')==38 and delivery_rate('+0%','reflective')=='-6%'
        report_plan=validate(dict(version=1,style='explain',layout='report',report_title='Chi tiết đã kiểm tra',events=[
            dict(part=0,offset=0,duration=.9,kind='kenburns',x=.4,y=.5,end_x=.6,end_y=.5,zoom_end=1.12)]),parts)
        export_canvas_clip(video,DATA_DIR/'report.mp4',[(0,1)],(.5,.5,1),out_w=180,out_h=320,encoder='libx264',
                           fx_fade=False,fx_whoosh=False,hieu_ung='tat',edit_plan=report_plan,edit_parts=parts)
        assert abs(probe(DATA_DIR/'report.mp4').duration-1)<.15
        results['checks'].append('compiled story delivery, report cards and keyframe render')
        from app.ui.recap_settings import RecapSettingsDialog
        from app.ui.appsettings import app_settings
        from app.core.dubbing import default_voice
        prefs=app_settings()
        saved={key:prefs.value(key) for key in ('story_lang','recap_voice')}
        prefs.setValue('story_lang','vi');prefs.setValue('recap_voice','en-US-GuyNeural')
        loader=RecapSettingsDialog._fill_voices_bg
        RecapSettingsDialog._fill_voices_bg=lambda self:None
        try:
            language_dialog=RecapSettingsDialog(story_start=True)
            assert language_dialog.story_lang.currentData()=='vi'
            assert language_dialog.voice.currentData()==''
            assert default_voice('vi') in language_dialog.language_note.text()
            assert language_dialog.story_lang.isEnabled()
            language_dialog.reject()
        finally:
            RecapSettingsDialog._fill_voices_bg=loader
            for key,value in saved.items():
                if value is None:prefs.remove(key)
                else:prefs.setValue(key,value)
        results['checks'].append('compiled target-language dialog repairs English voice for Vietnamese output')
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
