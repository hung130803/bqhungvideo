"""Offline music choice/approval, license packaging, real decode and Qt picker."""
import os,sys,tempfile,unittest,json,subprocess,hashlib
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_media_test_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard
import app.queue.jobs
from app.core import music_library as music,editorial,editorial_render
from app.ai import story_quality as q
from app.database import db
from app import services
from config import settings
from PyQt6.QtWidgets import QApplication,QDialog
from PyQt6.QtCore import Qt
APP=QApplication.instance() or QApplication([])

class MusicTests(unittest.TestCase):
    def test_all_music_decode_provenance_hash_and_mood_coverage(self):
        tracks=music.catalog();self.assertEqual(len(tracks),14)
        self.assertEqual(set(t['mood'] for t in tracks),set(music.MOODS))
        self.assertEqual(len({t['sha256'] for t in tracks}),14)
        for t in tracks:
            with self.subTest(track=t['id']):
                self.assertEqual(t['license'],'CC0-1.0');self.assertTrue(t['author']);self.assertTrue(t['source'].startswith('https://'))
                p=music.resolve(music.PREFIX+t['id'])
                subprocess.run([settings.FFMPEG_PATH,'-v','error','-i',p,'-f','null','-'],check=True,capture_output=True,timeout=30)

    def test_rotation_pins_distinct_tracks_until_mood_exhausted(self):
        for mood in music.MOODS:
            count=sum(t['mood']==mood for t in music.catalog());used=[]
            for i in range(count):used.append(music.choose('bqmusic:auto:'+mood,'clean','source',i,used))
            self.assertEqual(len(set(used)),count)
            self.assertEqual(music.choose('bqmusic:auto:'+mood,'clean','source',0),used[0])
        ref=music.choose('bqmusic:auto:style','funny','video',0)
        self.assertEqual(music.track(ref.split(':')[1])['mood'],'playful')

    def test_pinned_music_does_not_depend_on_export_order(self):
        ref=music.choose('bqmusic:auto:calm','clean','source',0)
        meta={'music_path':ref}
        self.assertEqual(music.export_path(meta,'missing-template.mp3'),music.resolve(ref))
        self.assertEqual(music.export_path(meta,None),music.resolve(ref))
        self.assertIsNone(music.export_path({'music_path':'bqmusic:off'},'template.mp3'))
        self.assertEqual(music.export_path({},'template.mp3'),'template.mp3')

    def test_invalid_reference_missing_or_changed_files_never_silently_substitute(self):
        for ref in ('bqmusic:../source','bqmusic:auto:calm','bqmusic:missing'):
            with self.assertRaises(ValueError):music.resolve(ref)
        t=music.catalog()[0]
        with patch.object(music,'folder',return_value=AREA):
            with self.assertRaises(ValueError):music.resolve('bqmusic:'+t['id'])
            (AREA/t['file']).write_bytes(b'changed')
            with self.assertRaises(ValueError):music.resolve('bqmusic:'+t['id'])

    def test_picker_filter_preview_and_selection_no_settings_writes(self):
        from app.ui.music_picker import MusicPicker
        from app.ui.appsettings import app_settings
        s=app_settings();s.setValue('story_music_path','existing.wav')
        dlg=MusicPicker(current='bqmusic:sector',allow_auto=False)
        try:
            self.assertEqual(dlg.items.currentItem().data(Qt.ItemDataRole.UserRole),'bqmusic:sector')
            self.assertNotIn('auto:',','.join(str(dlg.items.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(dlg.items.count())))
            dlg.mood.setCurrentIndex(dlg.mood.findData('calm'))
            self.assertEqual(dlg.items.count(),sum(t['mood']=='calm' for t in music.catalog()))
            dlg.items.setCurrentRow(0)
            with patch.object(dlg.player,'setSource') as source,patch.object(dlg.player,'play'):
                dlg.preview();source.assert_called_once()
            dlg.apply();self.assertEqual(dlg.result(),QDialog.DialogCode.Accepted)
            self.assertTrue(dlg.selection.startswith('bqmusic:'));self.assertEqual(s.value('story_music_path'),'existing.wav')
        finally:dlg.close()

    def test_picker_auto_and_off_do_not_get_replaced_by_last_previewed_track(self):
        from app.ui.music_picker import MusicPicker
        for ref in ('bqmusic:auto:style','bqmusic:auto:calm','bqmusic:off',''):
            dlg=MusicPicker(current=ref)
            try:
                self.assertEqual(dlg.mode.currentData(),ref)
                dlg.items.setCurrentRow(0)
                dlg.mode.setCurrentIndex(dlg.mode.findData(ref));dlg.apply()
                self.assertEqual(dlg.selection,ref)
            finally:dlg.close()

    def fixture(self):
        db.execute('DELETE FROM projects');pid=services.create_project('Media','Test')
        src=AREA/'source.mp4';src.write_bytes(b'fixture')
        vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,72)',(pid,str(src)))
        parts=[dict(start=0,end=72,mode='narrate',text='A blue card appears.')];windows=[[0,72]]
        meta=dict(quality_story=q.VERSION,parts=parts,windows=windows,lang='en',voice='en-US-GuyNeural',source_signature=q.source_signature(src),contract=q.contract(parts,windows))
        cid=db.insert("INSERT INTO clips(video_id,start_sec,end_sec,signals,status) VALUES(?,0,72,?,'suggested')",(vid,db.dumps({'recap':meta,'segments':windows})))
        return vid,cid,meta,src

    def test_changing_music_requires_new_approval_and_clears_export(self):
        vid,cid,meta,src=self.fixture();texts=[p['text'] for p in meta['parts']]
        approved=q.approve_script(cid,q.digest(meta),texts,music='bqmusic:sector')
        self.assertTrue(q.is_approved(approved))
        db.execute("UPDATE clips SET status='exported',export_path='old.mp4' WHERE id=?",(cid,))
        new=q.approve_script(cid,q.digest(approved),texts,music='bqmusic:airy')
        self.assertTrue(q.is_approved(new));self.assertIsNone(db.query_one('SELECT export_path FROM clips WHERE id=?',(cid,))['export_path'])
        new['music_path']='bqmusic:sector';self.assertFalse(q.is_approved(new))

    def test_invalid_music_rolls_back_approval(self):
        vid,cid,meta,src=self.fixture()
        with self.assertRaises(ValueError):q.approve_script(cid,q.digest(meta),[p['text'] for p in meta['parts']],music='bqmusic:auto:style')
        stored=db.loads(db.query_one('SELECT signals FROM clips WHERE id=?',(cid,))['signals'])['recap']
        self.assertEqual(q.digest(stored),q.digest(meta))

    def test_delivery_music_energy_are_reviewed_and_invalid_choices_roll_back(self):
        vid,cid,meta,src=self.fixture();texts=[p['text'] for p in meta['parts']]
        for options in ({'deliveries':['unknown']},{'deliveries':[{}]},{'energies':['loud']},{'energies':[]}):
            with self.assertRaises(ValueError):q.approve_script(cid,q.digest(meta),texts,**options)
            stored=db.loads(db.query_one('SELECT signals FROM clips WHERE id=?',(cid,))['signals'])['recap']
            self.assertEqual(q.digest(stored),q.digest(meta))
        approved=q.approve_script(cid,q.digest(meta),texts,deliveries=['measured'],energies=['hush'])
        self.assertTrue(q.is_approved(approved));self.assertEqual(approved['parts'][0]['delivery'],'measured')
        approved['parts'][0]['music_energy']='lift';self.assertFalse(q.is_approved(approved))

    def test_generation_pins_different_music_per_part_and_keeps_review_required(self):
        vid,cid,meta,src=self.fixture();db.execute('DELETE FROM clips');db.execute('UPDATE videos SET duration=144 WHERE id=?',(vid,))
        plans=[]
        for a,b in ((0,72),(72,144)):
            plans.append(dict(title='Story',parts=[dict(start=a,end=b,mode='narrate',text='A blue card appears.')],windows=[[a,b]],duration=72,review={}))
        with patch.object(q.llm,'is_configured',return_value=True),patch.object(q.llm,'vision_available',return_value=True),\
             patch.object(q,'build_evidence',return_value=([],q.source_signature(src),'key')),\
             patch('app.ai.story_director.direct',return_value=(plans,{})):
            q.generate({'video_id':vid,'preset':{'recap_count':2,'story_music_path':'bqmusic:auto:story','story_layout':'report'}},Mock())
        metas=[db.loads(r['signals'])['recap'] for r in db.query('SELECT signals FROM clips')]
        self.assertEqual(len({m['music_path'] for m in metas}),2)
        for m in metas:self.assertFalse(q.is_approved(m));self.assertTrue(Path(music.resolve(m['music_path'])).is_file())
        for m in metas:self.assertEqual(m['edit_plan']['layout'],'report')

    def test_new_sfx_files_decode_and_have_measurement_cache(self):
        base=ROOT/'app/assets/sfx';files=list(base.glob('*/casino_*.opus'))
        self.assertEqual(len(files),55)
        stats=json.loads((base/'muc_do.json').read_text())
        hashes=set()
        for p in files:
            self.assertIn(p.relative_to(base).as_posix(),stats)
            subprocess.run([settings.FFMPEG_PATH,'-v','error','-i',str(p),'-f','null','-'],check=True,capture_output=True,timeout=10)
            hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(len(hashes),55)

    def test_new_sticker_shapes_are_distinct_and_nonempty(self):
        from PyQt6.QtGui import QImage
        kinds=('check','cross','star','bolt','target','clock','eye','bubble','quote','bracket','chevrons','confetti');hashes=set()
        for kind in kinds:
            self.assertIn(kind,editorial.KINDS);p=AREA/(kind+'.png');editorial_render.sprite(p,kind,'#FFD34E')
            img=QImage(str(p));self.assertFalse(img.isNull());hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(len(hashes),12)

if __name__=='__main__':unittest.main(verbosity=2)
