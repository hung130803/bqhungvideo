from pathlib import Path
import os,sys,json,subprocess,unittest
from unittest.mock import patch
import tempfile
root=Path(__file__).resolve().parents[1];area=Path(tempfile.mkdtemp(prefix='bq_delivery_layout_'))
os.environ.update(BQ_DATA_DIR=str(area/'test-data'),BQ_DB_PATH=str(area/'test-data/test.db'),BQ_QSETTINGS_INI=str(area/'test-data/settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
sys.path.insert(0,str(root))
import _test_guard
from app.core import dubbing as d,story_craft as c,editorial as e,report_layout as r,ffmpeg_utils as f
from PyQt6.QtWidgets import QApplication
APP=QApplication.instance() or QApplication([])
from app.ui.fonts import load_fonts
load_fonts()
from app.ui.theme import apply_theme
apply_theme(APP)
from config import settings

class Changes(unittest.TestCase):
 def test_voice_directions_follow_settings(self):
  slow=c.gemini_delivery_prefix('vi','slow','curious',True,8)
  fast=c.gemini_delivery_prefix('vi','fast','brisk',True,8)
  self.assertGreater(c.gemini_pace_tempo('fast'),c.gemini_pace_tempo('normal'));self.assertIn('Vietnamese',fast);self.assertIn('maximum, not a target',fast)
  self.assertNotIn('Delivery:',c.gemini_delivery_prefix('vi',emotion=False))
  with self.assertRaises(ValueError):c.gemini_delivery_prefix('vi',window=float('nan'))

 def test_prefix_maps_correctly_even_when_shortest_is_not_first(self):
  calls=[];texts=['Một câu dài hơn','Tên James.'];prefix=['ONE:','TWO:']
  with patch.object(d,'_gemini_tts',side_effect=lambda text,voice,path:calls.append((text,path)) or True),patch.object(d.time,'sleep'):
   self.assertEqual(d._synth_all_gemini(texts,'gemini:Kore',['a','b'],'vi',gemini_prefix=prefix,allow_fallback=False),[True,True])
  self.assertEqual(dict((path,text) for text,path in calls),{'a':prefix[0]+texts[0],'b':prefix[1]+texts[1]})
  self.assertEqual(texts,['Một câu dài hơn','Tên James.'])
  with patch.object(d,'_gemini_tts') as synth:
   with self.assertRaises(ValueError):d._synth_all_gemini(texts,'gemini:Kore',['a','b'],'vi',gemini_prefix=['one'])
   synth.assert_not_called()

 def test_real_audio_tempo_is_faster_without_changing_window_or_pitch(self):
  src=area/'tone.wav'
  subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=3','-c:a','pcm_s16le',str(src)],check=True)
  durations=[]
  for pace in ('normal','fast'):
   out=area/(pace+'.wav')
   final,natural,tempo=d._fit_recap_chunk(str(src),str(out),5,tempo_max=1.15,allow_trim=False,requested_tempo=c.gemini_pace_tempo(pace))
   durations.append(final);self.assertAlmostEqual(natural,3,delta=.02)
   self.assertAlmostEqual(final,3/c.gemini_pace_tempo(pace),delta=.06)
   import numpy as np
   data=subprocess.check_output([settings.FFMPEG_PATH,'-v','error','-i',str(out),'-f','f32le','-ac','1','-ar','48000','-'])
   samples=np.frombuffer(data,dtype=np.float32);peak=np.argmax(abs(np.fft.rfft(samples)))*48000/len(samples)
   self.assertAlmostEqual(peak,440,delta=2)
  self.assertLess(durations[1],durations[0])

 def test_plan_validation_and_geometry(self):
  parts=[dict(start=0,end=2,mode='narrate',text='Xin chào')]
  for layout in ('report','explain','paper','navy','mint'):
   p=e.validate(dict(version=1,style='clean',layout=layout,events=[],background='paper',video_height=.44,footer='Part 4'),parts)
   self.assertTrue(r.keeps_full_source(p));self.assertEqual(p['footer'],'Part 4')
   for iw,ih in ((1920,1080),(1080,1920)):
    x,y,w=r.geometry(iw,ih,360,640,p);h=w*360*ih/iw/640
    self.assertLessEqual(h,.440001);self.assertGreaterEqual(y-h/2,.2399);self.assertLessEqual(y+h/2,.6801)
  for field,value in (('background','invalid'),('video_height',float('nan')),('footer','line\nbreak')):
   p=dict(version=1,style='clean',events=[]);p[field]=value
   with self.assertRaises(ValueError):e.validate(p,parts)

 def test_ui_controls_roundtrip(self):
  from app.ui.editorial_dialog import EditorialDialog
  parts=[dict(start=0,end=2,mode='narrate',text='Xin chào')]
  p=dict(version=1,style='clean',layout='paper',events=[],background='mint',video_height=.42,footer='Part 4')
  ui=EditorialDialog(None,'',parts,p);self.assertEqual(ui.checked()['footer'],'Part 4')
  self.assertEqual(ui.checked()['background'],'mint');self.assertEqual(ui.checked()['video_height'],.42)
  ui.resize(1050,760);ui.show();APP.processEvents();ui.grab().save(str(area/'editorial-ui.png'));ui.close()

 def test_real_render_background_and_timed_captions(self):
  src=area/'source.mp4'
  subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-t','2','-c:v','libx264','-preset','ultrafast',str(src)],check=True,timeout=30)
  parts=[dict(start=0,end=2,mode='narrate',text='Một câu thử')]
  for layout in ('paper','navy','mint'):
   p=e.validate(dict(version=1,style='clean',layout=layout,report_title='Tiêu đề đúng nội dung',events=[],video_height=.44,footer='Part 4'),parts)
   out=area/(layout+'.mp4')
   f.export_canvas_clip(src,out,[(0,2)],(.5,.5,1),out_w=360,out_h=640,encoder='libx264',fx_fade=False,fx_whoosh=False,hieu_ung='tat',edit_plan=p,edit_parts=parts,narration_events=[dict(start=0,end=2,speech=[.2,.9],text='Một câu thử',words=[[.2,.9,'Một câu thử']])])
   self.assertAlmostEqual(f.probe(out).duration,2,delta=.15)
   f.extract_frame(out,.5,area/(layout+'.png'))
   f.extract_frame(out,1.5,area/(layout+'-quiet.png'))
  print('Preview MP4s:',area,flush=True)

if __name__=='__main__':unittest.main(verbosity=2)
