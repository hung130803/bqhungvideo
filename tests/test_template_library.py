import os,sys,tempfile,unittest,subprocess,json
from pathlib import Path
from unittest.mock import patch
AREA=Path(tempfile.mkdtemp(prefix='templates36_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import _test_guard
import app.queue.jobs
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage,QFontDatabase
from PyQt6.QtCore import Qt
from app.ui.theme import apply_theme
from app.ui.fonts import load_fonts
APP=QApplication.instance() or QApplication([])
for f in ('segoeui.ttf','segoeuib.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)
load_fonts();apply_theme(APP)
from app.core.template_library import catalog,ensure_templates
from app.core.template_backgrounds import decode,fit_rect,image
from app.ui.template_gallery import TemplateGallery
from app.ui.editor import EditorDialog,render_overlay_png
from app import services
from app.core import ffmpeg_utils as F
from app.core.captions import build_ass
from config import settings
OUT=Path(os.environ.get('BQ_TEST_TEMPLATE_OUTPUT',str(AREA/'preview')));OUT.mkdir(parents=True,exist_ok=True)

class Templates(unittest.TestCase):
    def test_effect_gallery_and_saved_pool(self):
        from app.ui.effects_gallery import EffectsGallery
        from app.core.effects_config import parse,encode,PACKS,NEW_KEYS,allowed
        from app.core.hieu_ung import KHO,chon_hieu_ung
        gallery=EffectsGallery(value='nhe');gallery.show();APP.processEvents()
        self.assertEqual(gallery.items.count(),97)
        self.assertTrue(set(gallery.selected()).isdisjoint(NEW_KEYS))
        gallery.pack.setCurrentText('Phim — màu / ánh sáng')
        self.assertEqual(set(gallery.selected()),set(PACKS['Phim — màu / ánh sáng']))
        gallery.group.setCurrentText('Tông màu')
        self.assertEqual(sum(not gallery.items.item(i).isHidden() for i in range(97)),6)
        gallery.grab().save(str(OUT/'effects-gallery.png'));gallery._use()
        level,keys=parse(gallery.value);self.assertEqual(level,'nhe');self.assertEqual(set(keys),set(gallery.selected()))
        frame=OUT/'fx-source.png';image('navy',640,360).save(str(frame))
        lay=catalog()[0]['layout'];lay['hieu_ung']=gallery.value
        with patch.object(EditorDialog,'_dub_lang_ui'),patch.object(EditorDialog,'_load_tmpl'):
            dlg=EditorDialog(str(frame),lay)
            self.assertEqual(dlg._collect_layout()['hieu_ung'],gallery.value);dlg.close()
        self.assertEqual(parse(encode('vua',[])),('vua',()))
        self.assertTrue(set(allowed(KHO,None)).isdisjoint(NEW_KEYS))
        samples=dict(nl=[.1]*5+[1.4]+[.1]*8+[1.2]+[.1]*15,cd=[1]*30,moc_noi=[10,20],co_the_dung=list(keys))
        chosen=chon_hieu_ung(30,'vua',**samples)
        self.assertEqual(chosen,chon_hieu_ung(30,'vua',**samples))
        self.assertTrue(set(c['khoa'] for c in chosen)<=set(keys))
        self.assertLessEqual(len(chosen),3);self.assertLessEqual(sum(c['het']-c['bat'] for c in chosen),3.001)

    def test_new_effects_render_and_respect_time_window(self):
        import numpy as np
        from app.core.hieu_ung import KHO
        from app.core.effects_config import NEW_KEYS
        base=[settings.FFMPEG_PATH,'-v','error','-f','lavfi','-i','testsrc2=s=160x90:r=10:d=2']
        def raw(vf):
            result=subprocess.run(base+['-vf',vf,'-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            return np.frombuffer(result.stdout,np.uint8).reshape(-1,90,160,3).astype('int16')
        for key in sorted(NEW_KEYS):
            h=KHO[key];inactive=raw(h.chuoi(.25,5,6,160,90,10))
            active=raw(h.chuoi(.25,.5,1.2,160,90,10))
            self.assertEqual(active.shape,(20,90,160,3),key)
            self.assertEqual(int(np.abs(active[2]-inactive[2]).max()),0,key)
            self.assertEqual(int(np.abs(active[15]-inactive[15]).max()),0,key)
            self.assertGreater(float(np.abs(active[8]-inactive[8]).mean()),.2,key)

    def test_curve_antialias_at_full_resolution(self):
        import numpy as np
        from app.core.template_backgrounds import encode,foreground_filter,warp_preview
        from PyQt6.QtGui import QPixmap,QColor
        mode=encode('paper',False,True)
        result=subprocess.run([settings.FFMPEG_PATH,'-v','error','-f','lavfi','-i','color=red:s=1080x608:r=1:d=1',
            '-vf',foreground_filter(mode),'-frames:v','1','-pix_fmt','rgba','-f','rawvideo','-'],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        alpha=np.frombuffer(result.stdout,np.uint8).reshape(608,1080,4)[:,:,3]
        self.assertGreater(int(((alpha>0)&(alpha<255)).sum()),1500)
        self.assertGreaterEqual(int(alpha[300,540]),254)
        frame=QPixmap(1080,608);frame.fill(QColor('red'));preview=warp_preview(frame,1080,608,mode).toImage()
        from app.core.template_backgrounds import _curve_maps
        mask=QImage(_curve_maps(OUT,1080,608)[2])
        for x in range(50,1030,31):
            for y in range(32):self.assertLessEqual(abs(mask.pixelColor(x,y).red()-int(alpha[y,x])),2)
        for x in range(50,1030,31):
            for y in range(32):self.assertLessEqual(abs(preview.pixelColor(x,y).alpha()-int(alpha[y,x])),2)

    def test_custom_effect_pool_reaches_actual_export(self):
        from app.core.effects_config import encode
        src=OUT/'fx-real-source.mp4';dst=OUT/'fx-custom.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-f','lavfi','-i','testsrc2=s=160x90:r=30:d=8','-c:v','libx264',str(src)],check=True,timeout=30)
        log=[]
        with patch('app.core.hieu_ung.do_nhip',return_value=([],[])),patch('app.core.hieu_ung.dung_duoc',return_value=['mau_am_diu']):
            self.assertTrue(F.export_canvas_clip(src,dst,[(0,8)],(.5,.5,1),out_w=180,out_h=320,bg='design:paper:curve:echo',fit_src=True,
                encoder='libx264',hieu_ung=encode('vua',['mau_am_diu']),hieu_ung_log=log,fx_fade=False,fx_whoosh=False,chuyen_canh='tat'))
        self.assertTrue(log);self.assertEqual({c['khoa'] for c in log},{'mau_am_diu'})
        self.assertAlmostEqual(F.probe(dst).duration,8,delta=.15)

    def test_curved_edges_preserve_center_and_controls(self):
        from app.core.template_backgrounds import encode,options,warp_preview,layer_settings,draw_foreground
        from PyQt6.QtGui import QPixmap,QColor
        frame=QPixmap(320,180);frame.fill(QColor('#abcdef'))
        mode=encode('paper',True,True,True)
        warped=warp_preview(frame,320,180,mode).toImage()
        self.assertEqual(warped.pixelColor(160,0).alpha(),0)
        self.assertEqual(warped.pixelColor(160,179).alpha(),0)
        self.assertEqual(warped.pixelColor(160,90).name(),'#abcdef')
        self.assertEqual(warped.pixelColor(2,90).alpha(),255)
        self.assertEqual(options('design:paper:unknown')[0],None)
        path=OUT/'curve-source.png';frame.save(str(path))
        with patch.object(EditorDialog,'_dub_lang_ui'),patch.object(EditorDialog,'_load_tmpl'):
            dlg=EditorDialog(str(path),catalog()[0]['layout'])
            self.assertTrue(dlg.design_curve.isChecked());self.assertTrue(dlg.design_echo.isChecked())
            dlg.design_curve.setChecked(False)
            self.assertNotIn('curve',options(dlg._collect_layout()['bg'])[1])
            self.assertIn('echo',options(dlg._collect_layout()['bg'])[1])
            dlg._set_plain_background('blur')
            self.assertEqual(dlg._collect_layout()['bg'],'blur')
            self.assertFalse(dlg.design_echo.isChecked())
            dlg._apply_layout(catalog()[0]['layout'])
            self.assertEqual(dlg._collect_layout()['bg'],mode)
            for key,value in [('opacity',85),('shift',-8),('scale',115)]:dlg.design_layer_controls[key].setValue(value)
            custom=dlg._collect_layout()
            self.assertEqual(layer_settings(custom['bg']),dict(opacity=85,shift=-8,scale=115))
            dlg._apply_layout(custom)
            for key,value in [('opacity',85),('shift',-8),('scale',115)]:self.assertEqual(dlg.design_layer_controls[key].value(),value)
            self.assertEqual(dlg._collect_layout()['bg'],custom['bg'])
            self.assertGreaterEqual(abs(custom['cap_ny']-custom['narr_ny']),.06)
            dlg.close()

    def test_sharp_duplicate_is_visible_and_alpha_is_adjustable(self):
        from PyQt6.QtGui import QPixmap,QColor,QPainter
        from PyQt6.QtCore import QRectF
        from app.core.template_backgrounds import encode,draw_foreground
        src=QPixmap(320,180);src.fill(QColor('#e03020'))
        def render(opacity):
            out=QPixmap(360,400);out.fill(QColor('#102040'))
            p=QPainter(out);draw_foreground(p,QRectF(20,100,320,180),src,encode('paper',False,True,True,opacity=opacity,scale=120));p.end()
            return out.toImage()
        full=render(100);faint=render(20)
        # y=95 is outside the foreground but inside the larger curved back layer.
        self.assertEqual(full.pixelColor(180,95).name(),'#e03020')
        self.assertNotEqual(faint.pixelColor(180,95).name(),full.pixelColor(180,95).name())
        self.assertEqual(full.pixelColor(180,190).name(),'#e03020')

    def test_seed_idempotent_preserves_user_edit(self):
        ensure_templates();name=catalog()[0]['name'];edited=services.get_template(name)
        edited['speed']=1.05;services.save_template(name,edited)
        self.assertEqual(ensure_templates(),[]);self.assertEqual(services.get_template(name)['speed'],1.05)
        services.save_template(name,catalog()[0]['layout'])

    def test_geometry_contains_portrait_square_landscape(self):
        for w,h in [(1920,1080),(1080,1920),(1080,1080),(2560,720)]:
            cx,cy,sw=fit_rect([.5,.49,.98],w,h,1080,1920)
            vh=sw*1080*h/w
            self.assertLessEqual(vh,1920*.44+.01)
            self.assertGreaterEqual(cy*1920-vh/2,1920*.26-.01)
            self.assertLessEqual(cy*1920+vh/2,1920*.72+.01)

    def test_gallery_and_editor_roundtrip_all_presets(self):
        ensure_templates();gallery=TemplateGallery();gallery.show();APP.processEvents()
        self.assertEqual(gallery.grid.count(),8)
        gallery.grab().save(str(OUT/'gallery.png'))
        gallery.category.setCurrentText('Công việc / kỹ năng')
        self.assertEqual(sum(not gallery.grid.item(i).isHidden() for i in range(8)),1)
        gallery._choose();self.assertEqual(gallery.selected_name,catalog()[6]['name']);gallery.close()
        frame=OUT/'frame.png';image('navy',640,360).save(str(frame))
        for entry in catalog():
            layout=entry['layout']
            with patch.object(EditorDialog,'_dub_lang_ui'),patch.object(EditorDialog,'_load_tmpl'):
                dlg=EditorDialog(str(frame),layout,current_name=entry['name'])
                actual=dlg._collect_layout()
                for key in ('bg','fit_src','cap_preset','cap_font','hieu_ung','chuyen_canh'):
                    self.assertEqual(actual[key],layout[key],(entry['name'],key,actual[key]))
                self.assertEqual(len(actual['layers']),2)
                if entry['id']=='paper':
                    dlg.show();APP.processEvents();dlg.grab().save(str(OUT/'editor.png'))
                dlg.close()

    def test_real_video_exports_every_theme_and_motion(self):
        src=OUT/'source.mp4'
        subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-f','lavfi','-i','testsrc2=s=640x360:r=30:d=3',
                        '-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',str(src)],check=True,timeout=60)
        for entry in catalog():
            lay=entry['layout'];w,h=360,640;stem=entry['id'];overlay=OUT/(stem+'.png');ass=OUT/(stem+'.ass')
            rect=fit_rect(lay['video_rect'],640,360,w,h);cx,cy,sw=rect;vw=sw*w;vh=vw*360/640
            render_overlay_png(lay['layers'],1,w,h,overlay,'Một phát hiện thú vị',video_px=(cx*w-vw/2,cy*h-vh/2,vw,vh))
            words=[{'start':i*.4,'end':(i+1)*.4,'word':text} for i,text in enumerate(['Một','phát','hiện','thú','vị'])]
            build_ass(words,[(0,3)],ass,out_w=w,out_h=h,font=lay['cap_font'],size=int(h*.043),ny=lay['cap_ny'],preset=lay['cap_preset'])
            dst=OUT/(stem+'.mp4')
            self.assertTrue(F.export_canvas_clip(src,dst,[(0,3)],tuple(lay['video_rect']),bg=lay['bg'],out_w=w,out_h=h,
                encoder='libx264',overlay_png=str(overlay),ass_path=str(ass),fonts_dir=str(ROOT/'app/assets/fonts'),fit_src=True,
                fx_fade=False,fx_whoosh=False,hieu_ung='tat',chuyen_canh='tat'))
            info=F.probe(dst);self.assertEqual((info.width,info.height),(w,h));self.assertAlmostEqual(info.duration,3,delta=.12)
            for t in (.1,2.3):
                subprocess.run([settings.FFMPEG_PATH,'-v','error','-y','-ss',str(t),'-i',str(dst),'-frames:v','1',str(OUT/f'{stem}-{t}.png')],check=True,timeout=30)
            a,b=[QImage(str(OUT/f'{stem}-{t}.png')) for t in (.1,2.3)]
            difference=sum(abs(a.pixelColor(x,y).red()-b.pixelColor(x,y).red()) for x in range(20,340,8) for y in range(15,65,4))
            if decode(lay['bg'])[1]:self.assertGreater(difference,100,stem)
        print('PREVIEWS',OUT,flush=True)

if __name__=='__main__':unittest.main(verbosity=2)
