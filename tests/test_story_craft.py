"""Script delivery contracts and actual report/keyframe FFmpeg output, offline."""
import os,sys,tempfile,unittest,subprocess,json,hashlib
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_craft_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: F401,E402
from app.core import story_craft as craft,editorial as ed,report_layout as report,music_library as music
from app.ai import story_director as director
from app.core import dubbing as d,ffmpeg_utils as ff
from config import settings
from PyQt6.QtWidgets import QApplication
APP=QApplication.instance() or QApplication([])
from app.ui.fonts import load_fonts
load_fonts()

class Craft(unittest.TestCase):
    def test_report_inherited_crop_matches_full_source_and_legacy_crop_still_works(self):
        src=AREA/'crop-source.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30',
            '-t','1','-c:v','libx264','-preset','ultrafast',str(src)],check=True,timeout=20)
        parts=[dict(start=0,end=1,mode='orig',text='')]
        original_hash=hashlib.sha256(src.read_bytes()).hexdigest()
        def render(name,plan,crop):
            out=AREA/(name+'.mp4')
            ff.export_canvas_clip(src,out,[(0,1)],(.5,.5,.8),bg='blur',out_w=180,out_h=320,encoder='libx264',
                fx_fade=False,fx_whoosh=False,hieu_ung='tat',edit_plan=plan,edit_parts=parts,pre_crop=crop,fit_src=True)
            self.assertAlmostEqual(ff.probe(out).duration,1,delta=.1)
            return subprocess.check_output([settings.FFMPEG_PATH,'-v','error','-i',str(out),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
        for layout in ('report','explain'):
            plan=ed.validate(dict(version=1,style='explain',layout=layout,events=[]),parts)
            self.assertTrue(report.keeps_full_source(plan))
            self.assertEqual(render(layout+'-full',plan,None),render(layout+'-crop',plan,'160:180:160:0'))
        for plan in (None,dict(version=1,style='explain',layout='template',events=[]),dict(enabled=False,layout='report')):
            self.assertFalse(report.keeps_full_source(plan))
            self.assertNotEqual(render('legacy-full',plan,None),render('legacy-crop',plan,'160:180:160:0'))
        self.assertEqual(original_hash,hashlib.sha256(src.read_bytes()).hexdigest())

    def test_vietnamese_budget_is_syllabic_and_rates_are_bounded(self):
        self.assertEqual(craft.word_budget(12,'Vietnamese'),38)
        self.assertEqual(craft.word_budget(12,'en'),22)
        self.assertEqual(craft.delivery_rate('+0%','reflective'),'-6%')
        self.assertEqual(craft.delivery_rate('+29%','brisk'),'+30%')
        self.assertEqual(craft.delivery_rate('-29%','measured'),'-30%')

    def test_writer_keeps_context_evidence_and_delivery_without_extra_ai_call(self):
        text=' '.join(['Đây là lời kể thử nghiệm rõ ràng.']*3)
        parts=[dict(source_id=1,start=0,end=12,mode='narrate',role='hook',text='',evidence=json.dumps({'transcript':'A person shows a card.','observations':[]}))]
        plan=dict(title='Tấm thẻ',angle='Tấm thẻ',parts=parts)
        raw=dict(hooks=[text,'Một tấm thẻ.','Chi tiết này.'],selected_hook=0,music_mood='mystery',shots=[dict(source_id=1,text=text,delivery='curious',music_energy='low',support_quote='shows a card')])
        with patch.object(director.q,'ask',return_value=raw) as ask,patch.object(director,'audit',return_value={'approved':True}):
            result=director.script(plan,{},'Vietnamese',Mock(),0,1)
        self.assertEqual(ask.call_count,1);self.assertEqual(result['parts'][0]['delivery'],'curious')
        self.assertEqual(result['music_mood'],'mystery');self.assertIn('one spoken paragraph',ask.call_args.args[0])
        self.assertEqual(result['parts'][0]['evidence'],parts[0]['evidence'])

    def test_semantic_music_is_pinned_and_explicit_choice_wins(self):
        ref=music.choose('bqmusic:auto:story','funny','seed',0,story_mood='tension')
        self.assertEqual(music.track(ref.split(':')[1])['mood'],'tension')
        self.assertEqual(music.choose(ref,'clean','different',4,story_mood='bright'),ref)

    def test_cards_preserve_all_text_and_geometry_fits_portrait_landscape(self):
        text='Một cảnh rất rõ. '*35
        self.assertEqual(''.join(report.pages(text)).replace(' ',''),text.replace(' ',''))
        for iw,ih in ((1920,1080),(1080,1920),(600,600)):
            cx,cy,sw=report.geometry(iw,ih,360,640)
            self.assertLessEqual(sw,1);self.assertLessEqual(sw*360*ih/iw,640*.34+.01)
            self.assertEqual((cx,cy),(.5,.46))

    def test_report_settings_and_keyframes_survive_editor_round_trip(self):
        from app.ui.editorial_dialog import EditorialDialog
        parts=[dict(start=0,end=12,mode='narrate',text='Một cảnh rõ ràng.')]
        p=ed.validate(dict(version=1,style='explain',layout='report',report_title='Một chi tiết',events=[dict(part=0,kind='kenburns',offset=1,duration=2,x=.4,y=.5,end_x=.65,end_y=.55,zoom_end=1.22)]),parts)
        dlg=EditorialDialog(None,'missing.mp4',parts,p)
        try:self.assertEqual(dlg.checked(),p)
        finally:dlg.reject()
        with self.assertRaises(ValueError):ed.validate(dict(p,report_title='x'*141),parts)
        with self.assertRaises(ValueError):ed.validate(dict(p,layout='unknown'),parts)

    def test_tts_receives_individual_pace_language_and_same_approved_words(self):
        parts=[dict(start=0,end=4,mode='narrate',text='Chi tiết này là gì?',delivery='curious'),
               dict(start=4,end=8,mode='narrate',text='Câu trả lời đã rõ.',delivery='reflective')]
        async def synth(texts,voice,paths,**kwargs):
            self.assertEqual(texts,[p['text'] for p in parts]);self.assertEqual(kwargs['lang'],'vi')
            self.assertEqual(kwargs['rate'],['-2%','-6%']);self.assertFalse(kwargs['el_lui'])
            for path in paths:
                subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','sine=frequency=650:duration=1','-f','wav',path],check=True,timeout=10)
            return [True,True],[[[0,.9,t]] for t in texts]
        with patch.object(d,'_synth_all_words',side_effect=synth):
            path,events=d.build_recap_track(parts,[(0,8)],'vi-VN-NamMinhNeural','vi',AREA/'voice.wav',strict=True,allow_rewrite=False)
        self.assertAlmostEqual(ff.probe(path).duration,8,delta=.1)
        self.assertEqual([e['text'] for e in events],[p['text'] for p in parts])

    def test_report_zoom_still_disjoint_source_and_music_render(self):
        src=AREA/'source.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30',
            '-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','12','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(src)],check=True,timeout=20)
        before=hashlib.sha256(src.read_bytes()).hexdigest()
        parts=[dict(start=0,end=4,mode='narrate',text='Một chi tiết nhỏ giúp giải thích toàn bộ câu chuyện.',role='hook',music_energy='low'),
               dict(start=8,end=12,mode='orig',text='',role='payoff',music_energy='hush')]
        p=ed.validate(dict(version=1,style='explain',layout='report',report_title='CHI TIẾT THAY ĐỔI CÂU CHUYỆN',music_arc=True,transitions=False,
            events=[dict(part=0,kind='kenburns',offset=0,duration=3,x=.4,y=.5,end_x=.6,end_y=.5,zoom_end=1.15),
                    dict(part=1,kind='freeze',offset=1,duration=2,x=.75,y=.46,size=.25)]),parts)
        out=AREA/'report.mp4'
        ff.export_canvas_clip(src,out,[(0,4),(8,12)],(.5,.5,1),bg='fill',out_w=360,out_h=640,encoder='libx264',
            fx_fade=False,fx_whoosh=False,hieu_ung='tat',edit_plan=p,edit_parts=parts,
            bgm_path=music.resolve('bqmusic:sector'),story_mix=True,speed=1.25)
        info=ff.probe(out);self.assertAlmostEqual(info.duration,6.4,delta=.2);self.assertTrue(info.has_audio)
        self.assertEqual(before,hashlib.sha256(src.read_bytes()).hexdigest())
        ff.extract_frame(out,1,AREA/'report.png')
        from app.ui.editorial_dialog import Preview
        preview=Preview(str(src),parts,dict(p,events=[]),None,str(AREA),None);received=[]
        preview.result.connect(lambda path,note:received.append(path));preview.run()
        self.assertTrue(received and Path(received[0]).is_file())
        print('CRAFT_RENDER='+str(out),flush=True)

if __name__=='__main__':unittest.main(verbosity=2)
