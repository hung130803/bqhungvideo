"""Local motion graphics in the existing FFmpeg encode, before captions.

Original procedural artwork: no downloaded stock, fonts or model weights.
Tracking is short-window template matching, not object recognition.
"""
from pathlib import Path
import math
import unicodedata
import numpy as np


def check_tracking_geometry(src):
    """Do not place a confident-looking marker using incompatible geometry."""
    import json
    import subprocess
    from config import settings
    result=subprocess.run([settings.FFPROBE_PATH,'-v','error','-select_streams','v:0',
        '-show_streams','-of','json',str(src)],capture_output=True,text=True,
        encoding='utf-8',timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
    stream=json.loads(result.stdout)['streams'][0]
    rotation=float(stream.get('tags',{}).get('rotate',0) or 0)
    for data in stream.get('side_data_list',[]):
        rotation=float(data.get('rotation',rotation) or 0)
    sar=stream.get('sample_aspect_ratio','1:1')
    if rotation%360 or sar not in ('1:1','0:1','N/A',None):
        raise ValueError('Bám vật chưa hỗ trợ nguồn có metadata xoay/tỉ lệ điểm ảnh đặc biệt. Tắt bám vật hoặc chuẩn hóa video trước khi duyệt lại.')


def sprite(path,kind,color):
    from PyQt6.QtCore import Qt,QPointF,QRectF
    from PyQt6.QtGui import QImage,QPainter,QPen,QColor,QPainterPath
    image=QImage(256,256,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#141824'),20,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    def draw():
        if kind=='circle':p.drawEllipse(QRectF(25,25,206,206))
        elif kind=='arrow':
            p.drawLine(36,218,206,48);p.drawLine(114,48,206,48);p.drawLine(206,48,206,140)
        elif kind=='question':
            curve=QPainterPath(QPointF(65,82));curve.cubicTo(65,4,208,4,193,97)
            curve.cubicTo(188,125,128,126,128,161);p.drawPath(curve);p.drawPoint(128,208)
        elif kind=='alert':p.drawLine(128,40,128,160);p.drawPoint(128,208)
        elif kind=='check':p.drawLine(45,128,104,191);p.drawLine(104,191,213,58)
        elif kind=='cross':p.drawLine(55,55,201,201);p.drawLine(201,55,55,201)
        elif kind=='star':
            curve=QPainterPath()
            for j in range(10):
                angle=-math.pi/2+j*math.pi/5;r=101 if j%2==0 else 43
                point=QPointF(128+r*math.cos(angle),128+r*math.sin(angle))
                if j==0:curve.moveTo(point)
                else:curve.lineTo(point)
            curve.closeSubpath();p.drawPath(curve)
        elif kind=='bolt':
            curve=QPainterPath(QPointF(145,24))
            for x,y in ((65,139),(120,139),(107,231),(200,104),(142,104)):curve.lineTo(x,y)
            curve.closeSubpath();p.drawPath(curve)
        elif kind=='target':
            p.drawEllipse(QRectF(40,40,176,176));p.drawEllipse(QRectF(87,87,82,82))
            p.drawLine(128,17,128,68);p.drawLine(128,188,128,239);p.drawLine(17,128,68,128);p.drawLine(188,128,239,128)
        elif kind=='clock':
            p.drawEllipse(QRectF(30,30,196,196));p.drawLine(128,65,128,128);p.drawLine(128,128,180,155)
        elif kind=='eye':
            curve=QPainterPath(QPointF(24,128));curve.cubicTo(83,30,173,30,232,128);curve.cubicTo(173,226,83,226,24,128)
            p.drawPath(curve);p.drawEllipse(QRectF(94,94,68,68))
        elif kind=='bubble':
            p.drawRoundedRect(QRectF(25,35,206,150),32,32);p.drawLine(60,185,55,225);p.drawLine(55,225,105,185)
            for x in (80,128,176):p.drawPoint(x,110)
        elif kind=='quote':
            for x in (56,153):
                p.drawRoundedRect(QRectF(x,55,47,68),12,12);p.drawLine(x+47,123,x+22,192)
        elif kind=='bracket':
            for x,y,dx,dy in ((33,33,1,1),(223,33,-1,1),(33,223,1,-1),(223,223,-1,-1)):
                p.drawLine(x,y,x+dx*57,y);p.drawLine(x,y,x,y+dy*57)
        elif kind=='chevrons':
            for x in (55,130):p.drawLine(x,55,x+65,128);p.drawLine(x+65,128,x,201)
        elif kind=='confetti':
            for x,y,dx,dy in ((42,40,15,18),(116,28,-3,24),(196,50,-14,19),(50,141,22,-9),(135,114,13,20),(207,154,-17,18),(86,215,20,-8),(169,224,6,-22)):
                p.drawLine(x,y,x+dx,y+dy)
        elif kind=='heart':
            curve=QPainterPath(QPointF(128,215));curve.cubicTo(-42,120,55,-15,128,80)
            curve.cubicTo(201,-15,298,120,128,215);p.drawPath(curve)
        else:
            for i in range(8):
                a=i*math.pi/4;r=43 if kind=='burst' else 12
                p.drawLine(QPointF(128+r*math.cos(a),128+r*math.sin(a)),QPointF(128+100*math.cos(a),128+100*math.sin(a)))
    draw();p.setPen(QPen(QColor(color),11,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));draw();p.end()
    if not image.save(str(path)):raise RuntimeError('Không tạo được hình sticker tạm.')


def track_frames(frames,x,y):
    """Conservative NCC, 6 fps. Hide immediately on ambiguity/large jumps."""
    if len(frames)==0:return []
    h,w=frames[0].shape;r=max(5,int(min(w,h)*.065));px=int(x*w);py=int(y*h)
    if px<r or py<r or px+r>=w or py+r>=h:return []
    template=frames[0,py-r:py+r+1,px-r:px+r+1].astype(np.float32)
    template-=template.mean();norm=np.linalg.norm(template)
    if norm<35:return []
    positions=[(0.,x,y)];template/=norm
    for i,frame in enumerate(frames[1:],1):
        from app.core.ffmpeg_utils import _raise_if_job_canceled
        _raise_if_job_canceled()
        radius=12
        x0=max(r,px-radius);x1=min(w-r-1,px+radius)
        y0=max(r,py-radius);y1=min(h-r-1,py+radius)
        area=frame[y0-r:y1+r+1,x0-r:x1+r+1].astype(np.float32)
        windows=np.lib.stride_tricks.sliding_window_view(area,template.shape)
        windows=windows-windows.mean(axis=(-2,-1),keepdims=True)
        den=np.linalg.norm(windows,axis=(-2,-1))
        scores=(windows*template).sum(axis=(-2,-1))/np.maximum(den,.001)
        best=np.unravel_index(np.argmax(scores),scores.shape);score=float(scores[best])
        yy,xx=best;other=scores.copy();other[max(0,yy-3):yy+4,max(0,xx-3):xx+4]=-1
        if score<.80 or score-float(other.max())<.025:break
        nx,ny=x0+xx,y0+yy
        if abs(nx-px)>=radius-1 or abs(ny-py)>=radius-1:break
        px,py=nx,ny;positions.append((i/6.,px/w,py/h))
    return positions


def prepare(events,src,folder,ffmpeg):
    from app.core.ffmpeg_utils import _run,_raise_if_job_canceled
    output=[]
    for i,e in enumerate(events):
        _raise_if_job_canceled();event=dict(e);prefix=Path(folder)/f'event{i}'
        if e['kind'] in ('freeze','replay'):
            ext='.png' if e['kind']=='freeze' else '.mp4';path=prefix.with_suffix(ext)
            source_at=e['source_start']-(e['duration'] if e['kind']=='replay' else 0)
            args=[ffmpeg,'-y','-v','error','-ss',f"{source_at:.6f}",'-i',str(src),'-an','-vf','scale=480:-2,setsar=1']
            args+=['-frames:v','1'] if ext=='.png' else ['-t',f"{e['duration']:.6f}",'-r','30','-c:v','libx264','-preset','ultrafast','-crf','18']
            log=[];code=_run(args+[str(path)],on_line=lambda s:log.append(s))
            if code or not path.is_file():raise RuntimeError('Không tạo được ô ảnh dừng/phát lại: '+'\n'.join(log[-5:]))
            event['asset']=str(path)
        if e.get('track'):
            raw=prefix.with_suffix('.gray')
            args=[ffmpeg,'-y','-v','error','-ss',f"{e['source_start']:.6f}",'-i',str(src),
                  '-t',f"{e['duration']:.6f}",'-vf','scale=192:144,fps=6,format=gray','-f','rawvideo',str(raw)]
            log=[];code=_run(args,on_line=lambda s:log.append(s))
            if code:raise RuntimeError('Không đọc được khung hình để bám vật: '+'\n'.join(log[-5:]))
            data=np.fromfile(raw,dtype=np.uint8);frames=data[:len(data)//(192*144)*(192*144)].reshape(-1,144,192)
            event['track_points']=track_frames(frames,e['target_x'],e['target_y'])
            event['tracking_note']='Bám được %.2fs / %.2fs; tự ẩn khi mất dấu.' % (len(event['track_points'])/6,e['duration'])
        output.append(event)
    return output


def escape_path(path):
    return str(path).replace('\\:',':').replace('\\','/').replace(':','\\:').replace("'", "'\\''")


def wrap_label(text,width,font_size):
    limit=max(6,(width-40)/font_size);lines=[];line='';used=0.
    for char in text:
        weight=1. if unicodedata.east_asian_width(char) in ('W','F') else .62
        if used+weight>limit and line:lines.append(line.rstrip());line='';used=0.
        line+=char;used+=weight
    if line:lines.append(line.rstrip())
    return '\n'.join(lines)


def text_sprite(path,text,width,size):
    """Qt shapes Unicode with installed fallback fonts; no filter-string text."""
    from PyQt6.QtCore import Qt,QRect
    from PyQt6.QtGui import QImage,QPainter,QFont,QFontMetrics,QColor,QGuiApplication
    if QGuiApplication.instance() is None:raise RuntimeError('Chữ nhấn cần khởi tạo giao diện ứng dụng trước khi xuất.')
    font=QFont('Be Vietnam Pro');font.setPixelSize(size);font.setBold(True)
    metrics=QFontMetrics(font);padding=max(8,int(size*.5));limit=max(24,width-2*padding-24)
    # WordWrap does not break a long CJK/URL token consistently; wrap at glyph boundaries.
    lines=[];line=''
    for char in text:
        if line and metrics.horizontalAdvance(line+char)>limit:lines.append(line.rstrip());line=''
        line+=char
    if line:lines.append(line.rstrip())
    height=metrics.lineSpacing()*max(1,len(lines))+padding*2
    w=min(width-16,max(metrics.horizontalAdvance(s) for s in lines)+padding*2)
    image=QImage(w,height,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor(20,24,36,225))
    painter.drawRoundedRect(QRect(0,0,w,height),padding,padding);painter.setFont(font);painter.setPen(QColor('white'))
    for i,line in enumerate(lines):painter.drawText(padding,padding+metrics.ascent()+i*metrics.lineSpacing(),line)
    painter.end()
    if not image.save(str(path)):raise RuntimeError('Không tạo được chữ nhấn.')


def map_point(x,y,source_size,out_size,rect,bg,flip):
    iw,ih=source_size;ow,oh=out_size
    if flip:x=1-x
    if bg=='fill':
        scale=max(ow/iw,oh/ih);return (.5+(x-.5)*iw*scale/ow,.5+(y-.5)*ih*scale/oh)
    cx,cy,sw=rect
    return cx+(x-.5)*sw,cy+(y-.5)*sw*ow*ih/iw/oh


def append_graph(cmd,filters,label,index,events,folder,width,height,font,style,source_size,rect,bg,flip):
    """All timestamps pre-speed, identical to the input of subtitles."""
    color={'clean':'#4C91FF','funny':'#FFD34E','tension':'#FF6A57','explain':'#49DEC3'}[style]
    for i,e in enumerate(events):
        a=e['start'];b=e['end'];kind=e['kind'];out=f'[ed{i}]';enable=f'gte(t,{a:.5f})*lt(t,{b:.5f})'
        if kind=='kenburns':
            # One output frame per input frame at an explicit frame rate.
            # Smoothstep returns to the unzoomed frame at the end, no hard jump.
            u=f'min(1,max(0,(on/30-{a:.6f})/{b-a:.6f}))'
            ease=f'(sin(PI*({u}))*sin(PI*({u})))'
            z=f'1+{e["zoom_end"]-1:.6f}*({ease})'
            xx=f'max(0,min(iw-iw/zoom,iw*({e["x"]:.6f}+({e["end_x"]-e["x"]:.6f})*({u}))-iw/zoom/2))'
            yy=f'max(0,min(ih-ih/zoom,ih*({e["y"]:.6f}+({e["end_y"]-e["y"]:.6f})*({u}))-ih/zoom/2))'
            filters.append(f"{label}fps=30,zoompan=z='{z}':x='{xx}':y='{yy}':d=1:s={width}x{height}:fps=30{out}")
        elif kind=='zoom':
            # Short punch-in behind captions, bounded at 1.12x; no duration change.
            cw=int(width/1.12)//2*2;ch=int(height/1.12)//2*2
            xx=int((width-cw)*e['x']);yy=int((height-ch)*e['y'])
            filters += [f'{label}split[ezb{i}][ezf{i}]',
                f'[ezf{i}]crop={cw}:{ch}:{xx}:{yy},scale={width}:{height}[ezz{i}]',
                f"[ezb{i}][ezz{i}]overlay=enable='{enable}'{out}"]
        else:
            media=kind in ('freeze','replay')
            path=e.get('asset') if media else str(Path(folder)/f'sticker{i}.png')
            if kind=='label':text_sprite(path,e['text'],width,max(16,int(width*e['size']*.3)))
            elif not media:sprite(path,kind,color)
            if kind=='replay':cmd+=['-i',path]
            else:cmd+=['-loop','1','-framerate','30','-t',f"{e['duration']:.6f}",'-i',path]
            size=max(16,int(width*e['size']))//2*2
            chain=f'[{index}:v]'+('' if kind=='label' else f'scale={size}:-2,')+'format=rgba'
            if media:
                text='XEM LAI' if kind=='replay' else 'ANH DUNG'
                chain+=f",drawtext=fontfile='{escape_path(font)}':text='{text}':fontsize={max(12,int(width*.035))}:fontcolor=white:box=1:boxcolor=black@0.8:x=6:y=6"
            chain+=f',setpts=PTS-STARTPTS+{a:.6f}/TB[es{i}]';filters.append(chain);index+=1
            x=f"{e['x']:.6f}";y=f"{e['y']:.6f}"
            if e.get('track'):
                points=e.get('track_points',[])
                if not points:
                    # Consume the declared input without producing a false annotation.
                    filters.append(f'[es{i}]nullsink');continue
                enable+=f'*lt(t,{a+len(points)/6:.6f})'
                coords=[(a+t,*map_point(xx,yy,source_size,(width,height),rect,bg,flip)) for t,xx,yy in points]
                def expr(axis):
                    result=f'{coords[-1][axis]:.6f}'
                    for p,n in reversed(list(zip(coords,coords[1:]))):
                        result=f'if(lt(t,{n[0]:.6f}),{p[axis]:.6f}+(t-{p[0]:.6f})*{(n[axis]-p[axis])/(n[0]-p[0]):.6f},{result})'
                    return result
                x,y=expr(1),expr(2)
                enable+=f'*between(({x}),0,1)*between(({y}),0,1)'
            anchor_x='w*.8' if kind=='arrow' and e.get('track') else 'w/2'
            anchor_y='h*.2' if kind=='arrow' and e.get('track') else 'h/2'
            motion='0' if e.get('track') else f'4*sin((t-{a})*9)'
            xpos=f'W*({x})-{anchor_x}';ypos=f'H*({y})-{anchor_y}-{motion}'
            if not e.get('track'):
                xpos=f'max(0,min(W-w,{xpos}))';ypos=f'max(0,min(H-h,{ypos}))'
            # Tracked art may be clipped by the frame; clamping its rectangle
            # would move the pointer away from the measured target near edges.
            filters.append(f"{label}[es{i}]overlay=x='{xpos}':"
                f"y='{ypos}':eof_action=repeat:enable='{enable}'{out}")
        label=out
    return label,index
