"""Opt-in motion editing: real FFmpeg, unchanged legacy graph and isolated Qt."""
import os,sys,tempfile,unittest,subprocess,json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_editor_test_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: F401,E402
from app.core import editorial as ed,editorial_render as render,ffmpeg_utils as ff
from app.ai import story_quality as q
from config import settings
from PyQt6.QtWidgets import QApplication,QDialog
APP=QApplication.instance() or QApplication([])
from app.ui.fonts import load_fonts
load_fonts()
PARTS=[dict(start=0.,end=24.,mode='narrate',text='A supported statement.',role='hook')]


def event(kind='arrow',**kw):return dict(part=0,offset=1.,duration=1.,kind=kind,text='',**kw)
def plan(events=None):return dict(version=1,style='clean',music_arc=True,events=events or [])


class Editorial(unittest.TestCase):
    def test_unknown_nonfinite_overlap_and_bounds_rejected(self):
        for key,val in [('part',True),('offset',float('nan')),('duration',float('inf')),('x',5),('kind','bad'),('sound','bad'),('sound_file','../x.wav')]:
            e=event();e[key]=val
            with self.subTest(key=key),self.assertRaises(ValueError):ed.validate(plan([e]),PARTS)
        with self.assertRaises(ValueError):ed.validate(plan([event(),event()]),PARTS)
        bad=event('replay');bad['offset']=.5
        with self.assertRaises(ValueError):ed.validate(plan([bad]),PARTS)
        with self.assertRaises(ValueError):ed.validate(plan([event('label')]),PARTS)

    def test_map_disjoint_merged_and_excluded_frames(self):
        parts=[dict(start=10,end=16),dict(start=30,end=38)]
        e=event();e.update(part=1,offset=2)
        result=ed.timeline(plan([e]),parts,[(10,16),(30,38)])[0]
        self.assertEqual((result['start'],result['source_start']),(8,32))
        with self.assertRaises(ValueError):ed.timeline(plan([e]),parts,[(10,16),(30,32)])

    def test_draft_uses_exact_words_and_does_not_invent_emotion(self):
        p=ed.propose(PARTS,'funny');self.assertEqual(p['events'][0]['text'],PARTS[0]['text'])
        self.assertFalse(p['events'][0]['track'])

    def test_legacy_signature_unchanged_new_edit_requires_approval(self):
        meta=dict(parts=PARTS,windows=[[0,24]],source_signature=['x',1,1],voice='voice',lang='en',contract='c')
        old=q.digest({k:meta[k] for k in ('parts','windows','source_signature','voice','lang','contract')})
        self.assertEqual(old,q.approval_signature(meta));meta['human_approval']={'signature':old}
        meta['edit_plan']=plan([event()]);self.assertFalse(q.is_approved(meta))

    def test_tracking_known_motion_and_occlusion(self):
        rng=np.random.default_rng(5);pattern=rng.integers(0,255,(31,31),dtype=np.uint8)
        frames=np.zeros((6,144,192),dtype=np.uint8)
        for i in range(4):frames[i,57:88,81+i*2:112+i*2]=pattern
        points=render.track_frames(frames,.5,.5)
        self.assertGreaterEqual(len(points),3);self.assertLessEqual(len(points),4)
        self.assertGreater(points[-1][1],points[0][1])
        self.assertEqual(render.track_frames(np.zeros((4,144,192),dtype=np.uint8),.5,.5),[])

    def test_layout_mapping_mirror_and_fill(self):
        a=render.map_point(.25,.5,(1920,1080),(360,640),(.5,.5,1),'black',False)
        b=render.map_point(.25,.5,(1920,1080),(360,640),(.5,.5,1),'black',True)
        self.assertAlmostEqual(a[0]+b[0],1)
        self.assertEqual(render.map_point(.5,.5,(1920,1080),(360,640),(.5,.5,1),'fill',False),(.5,.5))

    def test_ui_stores_edits_does_not_approve_and_cancel_discards(self):
        from app.ui.editorial_dialog import EditorialDialog
        original=ed.validate(plan([event()]),PARTS)
        dlg=EditorialDialog(None,'missing.mp4',PARTS,original);dlg.x.setValue(27)
        result=dlg.checked();self.assertEqual(result['events'][0]['x'],.27)
        self.assertEqual(original['events'][0]['x'],.5);self.assertNotIn('human_approval',result)
        dlg.reject();self.assertEqual(dlg.result(),QDialog.DialogCode.Rejected)

    def test_music_ramps_preserve_optout(self):
        self.assertIn('volume=',ed.music_envelope(plan(),PARTS,[(0,24)],1))
        self.assertEqual(ed.music_envelope(dict(plan(),music_arc=False),PARTS,[(0,24)],1),'')

    def test_transitions_respect_style_disable_and_contiguous_source(self):
        segs=[(0,4),(10,14),(14,18)]
        self.assertEqual(ed.transitions(dict(plan(),transitions=False),PARTS,segs),[])
        result=ed.transitions(dict(plan(),style='funny'),PARTS,segs)
        self.assertEqual(result[0][0],'wipeleft');self.assertEqual(result[1][1],0)

    def test_long_unicode_label_fits_canvas_and_assets_are_original(self):
        from PyQt6.QtGui import QImage
        path=AREA/'label.png';render.text_sprite(path,'日本語説明文 ' * 8,320,22)
        image=QImage(str(path));self.assertLessEqual(image.width(),304);self.assertGreater(image.height(),44)
        self.assertEqual(len(list((ROOT/'app/assets/sfx').glob('*/ed_*.opus'))),20)

    def test_target_click_coordinates_ignore_letterbox(self):
        from app.ui.editorial_dialog import TargetImage
        from PyQt6.QtGui import QPixmap,QMouseEvent
        from PyQt6.QtCore import Qt,QEvent,QPointF
        pixmap=QPixmap(320,180);pic=TargetImage(pixmap);pic.resize(400,400)
        rect=pic.image_rect();self.assertGreater(rect.top(),0)
        event=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(100,200),QPointF(100,200),Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        pic.mousePressEvent(event);self.assertAlmostEqual(pic.point[0],.25);self.assertAlmostEqual(pic.point[1],.5)

    def test_no_network_is_needed_for_effect_proposals(self):
        with patch.object(q.llm,'complete_json',side_effect=AssertionError('Unexpected AI call')):
            for style in ed.STYLES:ed.propose(PARTS,style)

    def test_missing_selected_sound_survives_reopening_editor(self):
        from app.ui.editorial_dialog import EditorialDialog
        original=ed.validate(plan([event(sound='pop',sound_file='removed_sound.opus')]),PARTS)
        dlg=EditorialDialog(None,'missing.mp4',PARTS,original)
        try:
            self.assertEqual(dlg.checked()['events'][0]['sound_file'],'removed_sound.opus')
            self.assertIn('thiếu',dlg.variant.currentText().lower())
        finally:dlg.reject()

    def test_reviewed_opening_label_replaces_template_title_only_when_enabled(self):
        p=plan([dict(event('label'),text='Opening')])
        self.assertTrue(ed.replaces_opening_title(p,PARTS,[(0,24)],6))
        self.assertFalse(ed.replaces_opening_title(dict(p,enabled=False),PARTS,[(0,24)],6))
        self.assertFalse(ed.replaces_opening_title(None,PARTS,[(0,24)],6))
        p['events'][0]['offset']=10
        self.assertFalse(ed.replaces_opening_title(p,PARTS,[(0,24)],6))

    def test_source_picker_discards_result_when_selection_changes(self):
        from app.ui.editorial_dialog import EditorialDialog
        dlg=EditorialDialog(None,'missing.mp4',PARTS,ed.validate(plan([event()]),PARTS))
        dlg.target_context=(dlg.row,0,1.,'arrow');dlg.offset.setValue(2.)
        with patch.object(dlg,'error',side_effect=AssertionError('Stale result must be discarded')):
            dlg.target_ready('','old extraction error')
        self.assertFalse(dlg.track.isChecked());dlg.reject()


class RealRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=AREA/'source.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=30',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','24','-c:v','libx264','-preset','ultrafast',
            '-c:a','aac',str(cls.src)],check=True,timeout=35)

    def test_all_visuals_unicode_explicit_audio_duration(self):
        import hashlib
        before=hashlib.sha256(self.src.read_bytes()).hexdigest()
        kinds=list(ed.KINDS);total=0
        for batch in range(0,len(kinds),11):
            events=[]
            for i,kind in enumerate(kinds[batch:batch+11]):
                e=event(kind);e.update(offset=i*2+.1,text="Chi tiết: 50% 'đúng'" if kind=='label' else '',sound='pop' if i==0 else 'none')
                if kind=='replay':e['offset']=22
                events.append(e)
            output=AREA/f'all{batch}.mp4';logs=[];audio=[]
            ff.export_canvas_clip(self.src,output,[(0,24)],(.5,.5,.95),bg='black',out_w=320,out_h=568,
                encoder='libx264',fx_fade=False,hieu_ung='tat',edit_plan=ed.validate(plan(events),PARTS),edit_parts=PARTS,
                edit_log=logs,tieng_dong_log=audio)
            info=ff.probe(output);self.assertAlmostEqual(info.duration,24,delta=.15);self.assertTrue(info.has_audio)
            self.assertEqual(len(logs),len(events));self.assertEqual(len(audio),1);total+=len(logs)
            self.assertAlmostEqual(audio[0]['giay'],events[0]['offset'],delta=.03)
        self.assertEqual(total,len(ed.KINDS))
        self.assertEqual(before,hashlib.sha256(self.src.read_bytes()).hexdigest())

    def test_optout_and_empty_plan_same_pixels_and_audio(self):
        paths=[AREA/'old.mp4',AREA/'empty.mp4']
        for i,path in enumerate(paths):
            ff.export_canvas_clip(self.src,path,[(0,3)],(.5,.5,.9),bg='black',out_w=180,out_h=320,
                encoder='libx264',fx_fade=False,fx_whoosh=False,hieu_ung='tat',
                **({'edit_plan':plan(),'edit_parts':PARTS} if i else {}))
        def digest(path):
            return subprocess.check_output([settings.FFMPEG_PATH,'-v','error','-i',str(path),'-map','0','-f','framemd5','-'])
        self.assertEqual(digest(paths[0]),digest(paths[1]))

    def test_speed_and_tracking_failure_are_bounded(self):
        e=event('circle',track=True);output=AREA/'tracked.mp4';logs=[]
        ff.export_canvas_clip(self.src,output,[(0,6)],(.5,.5,1),bg='fill',out_w=180,out_h=320,
            encoder='libx264',speed=1.5,fx_fade=False,fx_whoosh=False,hieu_ung='tat',
            edit_plan=ed.validate(plan([e]),PARTS),edit_parts=PARTS,edit_log=logs)
        self.assertAlmostEqual(ff.probe(output).duration,4,delta=.2);self.assertIn('tracking_note',logs[0])

    def test_preview_replay_uses_prior_footage_and_returns_file(self):
        from app.ui.editorial_dialog import Preview
        e=event('replay');e['offset']=4
        worker=Preview(str(self.src),PARTS,ed.validate(plan([e]),PARTS),0,str(AREA),None)
        received=[];worker.result.connect(lambda path,note:received.append((path,note)));worker.run()
        self.assertTrue(received and Path(received[0][0]).is_file(),received)
        self.assertAlmostEqual(ff.probe(received[0][0]).duration,3,delta=.15)

    def test_selected_sound_file_and_multicut_duration_with_music(self):
        e=event('sparkle');e.update(part=1,offset=.2,sound='reveal',sound_file='ed_glass_chime.opus',sound_gain=.35)
        parts=[dict(PARTS[0],start=0,end=3,role='setup'),dict(PARTS[0],start=10,end=14,role='payoff')]
        audio=[];out=AREA/'multi.mp4';chosen=ed.validate(dict(plan([e]),style='explain'),parts)
        ff.export_canvas_clip(self.src,out,[(0,3),(10,14)],(.5,.5,.9),bg='blur',out_w=180,out_h=320,
            encoder='libx264',fx_fade=False,hieu_ung='tat',edit_plan=chosen,edit_parts=parts,
            story_mix=True,bgm_path=str(ROOT/'app/assets/sfx/sad/ed_low_bell.opus'),duck_ranges=[(0,2)],tieng_dong_log=audio)
        self.assertAlmostEqual(ff.probe(out).duration,7,delta=.18);self.assertTrue(ff.probe(out).has_audio)
        self.assertEqual(audio[0]['ten'],'ed_glass_chime.opus');self.assertAlmostEqual(audio[0]['giay'],3.2,delta=.02)

    def test_missing_pinned_audio_fails_instead_of_silent_substitution(self):
        e=event(sound='pop',sound_file='not_present.opus');out=AREA/'missing.mp4'
        with self.assertRaises(ValueError):
            ff.export_canvas_clip(self.src,out,[(0,3)],(.5,.5,.9),bg='black',out_w=180,out_h=320,
                encoder='libx264',hieu_ung='tat',edit_plan=ed.validate(plan([e]),PARTS),edit_parts=PARTS)
        self.assertFalse(out.exists())

    def test_mixed_contiguous_and_transition_boundaries_do_not_fallback(self):
        temps=[]
        pieces=ff._tach_va_noi_manh(self.src,[(0,2),(2,4),(10,12)],
            [('fade',0),('fade',.2)],[0,.2],'libx264',30,True,str(AREA),'mixed',temps,dung_gpu=False)
        self.assertEqual(len(pieces),4)
        self.assertFalse(any('_g0' in p for p in pieces))
        self.assertAlmostEqual(sum(ff.probe(p).duration for p in pieces),6,delta=.1)

    def test_rotated_source_cannot_silently_misplace_tracking(self):
        path=AREA/'rotated.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-display_rotation','90','-i',str(self.src),
            '-c','copy',str(path)],check=True,timeout=20)
        with self.assertRaises(ValueError):render.check_tracking_geometry(path)
        render.check_tracking_geometry(self.src)

    def test_reviewed_sound_category_is_not_overridden_by_template_folder(self):
        folder=AREA/'custom_sfx';folder.mkdir(exist_ok=True)
        subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-i',
            str(ROOT/'app/assets/sfx/comedy/ed_rubber.opus'),str(folder/'wrong_group.wav')],check=True,timeout=15)
        logs=[];out=AREA/'category.mp4';p=ed.validate(plan([event(sound='reveal')]),PARTS)
        ff.export_canvas_clip(self.src,out,[(0,3)],(.5,.5,.9),bg='black',out_w=180,out_h=320,
            encoder='libx264',fx_fade=False,hieu_ung='tat',fx_sfx_dir=str(folder),
            edit_plan=p,edit_parts=PARTS,tieng_dong_log=logs)
        self.assertEqual(len(logs),1)
        self.assertNotEqual(logs[0]['ten'],'wrong_group.wav')
        self.assertEqual(logs[0]['nguon'],'kho tiếng động của app')
        legacy=[]
        ff.export_canvas_clip(self.src,AREA/'legacy_folder.mp4',[(0,2),(8,10)],(.5,.5,.9),bg='black',out_w=180,out_h=320,
            encoder='libx264',fx_fade=False,hieu_ung='tat',fx_sfx_dir=str(folder),tieng_dong_log=legacy)
        self.assertEqual(legacy[0]['ten'],'wrong_group.wav')

    def test_tracked_circle_near_edge_keeps_target_anchor(self):
        # A fixed measured target at 90% width. Render a circle and inspect its
        # top rim: keeping the sprite entirely in-frame would shift its center.
        e=ed.timeline(plan([event('circle',track=True,size=.45)]),PARTS,[(0,3)])[0]
        e['track_points']=[(0.,.9,.5),(.2,.9,.5),(.4,.9,.5)]
        cmd=[settings.FFMPEG_PATH,'-v','error','-y','-f','lavfi','-i','color=black:s=200x200:r=30:d=3']
        filters=[]
        label,_=render.append_graph(cmd,filters,'[0:v]',1,[e],str(AREA),200,200,'','explain',(200,200),(.5,.5,1),'fill',False)
        out=AREA/'edge.mp4';cmd+=['-filter_complex',';'.join(filters),'-map',label,'-t','3','-c:v','libx264',str(out)]
        subprocess.run(cmd,check=True,timeout=30)
        pixels=subprocess.check_output([settings.FFMPEG_PATH,'-v','error','-ss','1.2','-i',str(out),
            '-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
        image=np.frombuffer(pixels,dtype=np.uint8).reshape(200,200,3)
        rim=image[62:67,177:183]
        self.assertGreater(int(rim[:,:,1].max()),100,'circle must stay centered on target near edge')


if __name__=='__main__':
    print('Isolated render artifacts:',AREA,flush=True);unittest.main(verbosity=2)
