"""Local, deterministic design backgrounds. No downloads or AI requests."""
from functools import lru_cache
from pathlib import Path
import math

THEMES = {
    'paper': ('Giấy nhăn ấm', '#d9bc99', '#b69978'),
    'linen': ('Vải linen sáng', '#eee8dc', '#cec5b5'),
    'navy': ('Bản tin xanh đêm', '#152b45', '#071323'),
    'mint': ('Ngọc xanh dịu', '#daece4', '#92bdae'),
    'sunset': ('Cam đào', '#f7c9ac', '#cc817f'),
    'aurora': ('Cực quang tím xanh', '#172849', '#462b66'),
    'graphite': ('Than chì', '#333c45', '#151c25'),
    'sand': ('Cát & đường cong', '#eee2c6', '#c6ac7e'),
}

#: CHIỀU CAO khung video trên nền thiết kế, % chiều cao khung xuất (cờ `cao<N>`).
#: 30/10/2026 anh Hùng: "chiều ngang luôn luôn hết, chiều cao thì tôi chỉnh".
#: Bản cũ GIỚI HẠN cao 44% rồi THU NHỎ CẢ BỀ NGANG theo -> video dọc 720x966
#: chỉ còn rộng ~58% khung. Nay bề ngang LUÔN 100%, video cao hơn mức này thì
#: CẮT BỚT trên/dưới (giữa) chứ không thu nhỏ. Mặc định 44 = đúng dải cũ, và
#: mặc định KHÔNG ghi vào chuỗi nền -> mẫu cũ giữ nguyên chuỗi (không xuất lại).
CAO_MAC_DINH = 44
CAO_KHOANG = (25, 90)


def options(mode):
    import re
    fields=str(mode or '').split(':')
    def valid(flag):
        if flag in {'drift','curve','echo'}:return True
        match=re.fullmatch(r'(opacity|shift|scale|ngang|cao)(-?\d{1,3})',flag)
        if not match:return False
        low,high={'opacity':(20,100),'shift':(-20,20),'scale':(100,140),'ngang':(100,140),'cao':CAO_KHOANG}[match[1]]
        return low<=int(match[2])<=high
    if len(fields)>=2 and ((fields[0]=='design' and fields[1] in THEMES) or (fields[0]=='layer' and fields[1] in {'blur','black','white','fill'})) and all(valid(flag) for flag in fields[2:]):
        return fields[1],set(fields[2:])
    return None,set()

def decode(mode):
    theme,flags=options(mode)
    return (theme if str(mode).startswith('design:') else None),'drift' in flags

def layer_settings(mode):
    _,flags=options(mode);values={'opacity':100,'shift':0,'scale':108,'ngang':0,'cao':CAO_MAC_DINH}
    for field in str(mode or '').split(':')[2:]:
        if field not in flags:continue
        for key in values:
            if field.startswith(key):values[key]=int(field[len(key):])
    return values

def encode(theme, motion=False, curve=False, echo=False, opacity=100, shift=0, scale=108, cao=CAO_MAC_DINH, ngang=0):
    if theme not in THEMES: raise ValueError('Nền mẫu không hợp lệ.')
    text='design:'+theme+''.join(':'+key for key,on in [('drift',motion),('curve',curve),('echo',echo)] if on)
    if echo:
        for key,value,default,lo,hi in [('opacity',opacity,100,20,100),('shift',shift,0,-20,20),('scale',scale,108,100,140)]:
            value=max(lo,min(hi,int(value)))
            if value!=default:text+=':'+key+str(value)
        # BỀ NGANG lớp sau RIÊNG (anh Hùng 31/10/2026: "2 bên mép nhỏ hơn, trên
        # dưới to hơn 1 tí"). 0 = theo `scale` (y như cũ) -> KHÔNG ghi cờ, nên
        # chuỗi nền của mọi mẫu cũ giữ nguyên từng ký tự (không xuất lại).
        ngang=int(ngang or 0)
        if ngang:
            ngang=max(100,min(140,ngang))
            if ngang!=max(100,min(140,int(scale))):text+=':ngang'+str(ngang)
    cao=max(CAO_KHOANG[0],min(CAO_KHOANG[1],int(cao)))
    if cao!=CAO_MAC_DINH:text+=':cao'+str(cao)
    return text

def plain_base(mode):
    theme,_=options(mode)
    return theme if str(mode).startswith('layer:') and theme else mode

def encode_plain(base,curve=False,echo=False,**values):
    base=plain_base(base)
    if base not in {'blur','black','white','fill'}:base='blur'
    if not curve and not echo:return base
    return encode('paper',False,curve,echo,**values).replace('design:paper','layer:'+base,1)

def foreground_filter(mode):
    """Inverse mapping compresses every source row into inward-curved edges."""
    _,flags=options(mode)
    if 'curve' not in flags:return 'null'
    bend="(H*0.045*sin(PI*X/(W-1))*(1+0.13*sin(T*1.1)))"
    sy=f"(Y-{bend})/(1-2*{bend}/(H-1))"
    rgb=':'.join(f"{c}='{c}(X,{sy})'" for c in ('r','g','b'))
    return f"format=rgba,geq={rgb}:a='255*clip(min(Y-{bend}+0.5,H-0.5-{bend}-Y),0,1)'"

def _curve_maps(folder,width,height):
    """Precompute maps once. Double vertical sampling smooths the bend; horizontal coordinates stay integral."""
    import numpy as np
    from PyQt6.QtGui import QImage
    prefix=Path(folder)/f'curve_v59_{width}_{height}'
    files=[str(prefix)+tail for tail in ('_x.pgm','_y.pgm','_alpha.png')]
    if all(Path(p).exists() for p in files):return files
    y,x=np.mgrid[:height,:width]
    bend=height*.045*np.sin(np.pi*x/(width-1))
    sy=np.clip((y-bend)/(1-2*bend/(height-1)),0,height-1)
    for path,arr in zip(files[:2],(x,np.rint(sy*2))):
        with open(path,'wb') as stream:
            stream.write(f'P5\n{width} {height}\n65535\n'.encode('ascii'))
            stream.write(arr.astype('>u2').tobytes())
    alpha=np.ascontiguousarray((255*np.clip(np.minimum(y-bend+.5,height-.5-bend-y),0,1)).astype('uint8'))
    im=QImage(alpha.data,width,height,width,QImage.Format.Format_Grayscale8).copy()
    if not im.save(files[2]):raise RuntimeError('Không tạo được mép khung cong.')
    return files

def dung_yuv():
    """Dựng khung cong + lớp sau ở hệ màu VIDEO (YUV) thay vì RGB.

    31/10/2026: lớp sau RGBA + `overlay format=auto` kéo CẢ khung 1080x1920
    qua lại RGB ở mọi bước sau -> phần lọc của nền cong nhiều lớp đo 10,6 s/30 s
    phim, giữ YUV còn 5,4 s. KHÔNG trùng từng điểm ảnh (lệch TB ~1,4 mức ở
    nền, ~4 mức trong khung do làm tròn vị trí chồng ảnh về số chẵn) nên để
    CÔNG TẮC `BQ_NEN_CONG_YUV`: mặc định BẬT (anh Hùng duyệt 31/10/2026 sau khi
    xem cùng 1 Part 2 cách: nhanh ~28%, đủ khung, chỉ lệch vị trí 1 điểm ảnh);
    "0" = trả về cách cũ."""
    import os
    return os.environ.get('BQ_NEN_CONG_YUV', '1') != '0'


def compose_foreground(parts,source,mode,width,cx,cy,cmd,nextidx,folder,total,aspect):
    _,flags=options(mode);cfg=layer_settings(mode);base='base'
    yuv=dung_yuv() and 'curve' in flags
    fmt_ov='yuv420' if yuv else 'auto'
    def warped(src,w,label):
        nonlocal nextidx
        h=max(2,int(w*aspect/2+.5)*2)
        if 'curve' not in flags:
            parts.append(f'{src}scale={w}:{h}:flags=lanczos,setsar=1[{label}]');return
        maps=_curve_maps(folder,w,h);ids=[]
        for path in maps:
            ids.append(nextidx);nextidx+=1
            # Static remap/alpha inputs repeat their last frame in framesync.
            # Decode once; geometry and antialiased edge pixels are unchanged.
            cmd.extend(['-framerate','30','-i',path])
        parts.append(f'{src}scale={w}:{h*2}:flags=bilinear,format=gbrp[{label}src]')
        parts.append(f'[{label}src][{ids[0]}:v][{ids[1]}:v]remap=fill=black[{label}mapped]')
        parts.append(f'[{label}mapped][{ids[2]}:v]alphamerge,setsar=1'
                     + (',format=yuva420p' if yuv else '') + f'[{label}]')
    if 'echo' in flags:
        # TĂNG TỐC 26/10/2026 — đo trên đúng lệnh lọc của Part thật (nền
        # layer:blur:curve:echo, khung 1270 px): phần lọc hình mất ~5,5 lần nền
        # thường. Hai chỗ tốn, sửa cả hai:
        #  1) `colorchannelmixer=aa=1.00` khi độ mờ để 100% là phép KHÔNG LÀM GÌ
        #     nhưng tính từng điểm ảnh bằng số thực: bỏ đi ra khung Y HỆT từng bit
        #     (đã so md5 từng khung), nhanh hơn ~18%. Độ mờ <100% dùng bảng tra
        #     `lutrgb` thay vì phép nhân số thực.
        #  2) Bản cũ UỐN CONG HAI LẦN mỗi khung (bản trước + bản bóng to hơn 8%).
        #     Độ cong H*0.045*sin(pi*X/W) TỈ LỆ THUẬN với khung nên uốn MỘT lần
        #     rồi phóng bản đã uốn lên cỡ bóng cho cùng hình học; bóng là lớp nằm
        #     sau, chỉ lộ viền ~4% quanh khung trước.
        bw=max(2,int(width*cfg['scale']/100)//2*2)
        bh=max(2,int(bw*aspect/2+.5)*2)
        if cfg.get('ngang'):
            # Chiều DỌC vẫn theo `scale`, chiều NGANG theo `ngang` (viền hai
            # bên mỏng hơn viền trên/dưới). Không có cờ -> y nguyên lệnh cũ.
            bw=max(2,int(width*cfg['ngang']/100)//2*2)
        warped(source,width,'designfgw')
        parts.append('[designfgw]split=2[designfg][designfgcopy]')
        op=cfg['opacity']
        if yuv:
            mo='' if op>=100 else f",lut=a='val*{op/100:.2f}'"
            parts.append(f"[designfgcopy]scale={bw}:{bh}:flags=bilinear{mo}[designback]")
        else:
            mo='' if op>=100 else f",lutrgb=a='val*{op/100:.2f}'"
            parts.append(f"[designfgcopy]scale={bw}:{bh}:flags=bilinear,format=rgba{mo}[designback]")
        parts.append(f"[base][designback]overlay=x='{cx:.4f}*W-w/2':y='{cy:.4f}*H-h/2+h*{cfg['shift']/cfg['scale']:.4f}':format={fmt_ov}[designbase]")
        base='designbase'
    else:
        warped(source,width,'designfg')
    parts.append(f"[{base}][designfg]overlay=x='{cx:.4f}*W-w/2':y='{cy:.4f}*H-h/2':format={fmt_ov}[vv]")
    return nextidx

def warp_preview(pm,width,height,mode):
    from PyQt6.QtGui import QImage,QPixmap
    from PyQt6.QtCore import Qt
    import numpy as np
    _,flags=options(mode)
    im=pm.toImage().scaled(max(2,int(width)),max(2,int(height)),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_RGBA8888)
    if 'curve' not in flags:return QPixmap.fromImage(im)
    w,h=im.width(),im.height();ptr=im.bits();ptr.setsize(im.sizeInBytes())
    src=np.frombuffer(ptr,dtype=np.uint8).reshape(h,im.bytesPerLine())[:,:w*4].reshape(h,w,4)
    y,x=np.mgrid[:h,:w];bend=h*.045*np.sin(np.pi*x/(w-1));sy=(y-bend)/(1-2*bend/(h-1))
    sy=np.clip(sy,0,h-1);lo=sy.astype(int);hi=np.minimum(lo+1,h-1);weight=(sy-lo)[...,None]
    arr=np.ascontiguousarray((src[lo,x]*(1-weight)+src[hi,x]*weight).astype('uint8'))
    arr[:,:,3]=(255*np.clip(np.minimum(y-bend+.5,h-.5-bend-y),0,1)).astype('uint8')
    return QPixmap.fromImage(QImage(arr.data,w,h,w*4,QImage.Format.Format_RGBA8888).copy())

def draw_foreground(p,rect,pm,mode,cache=None):
    from PyQt6.QtCore import QRectF
    _,flags=options(mode);cfg=layer_settings(mode)
    key=(pm.cacheKey(),int(rect.width()),int(rect.height()),mode)
    if cache is not None and cache.get('key')==key:
        warped=cache['pixmap'];back=cache.get('back')
    else:
        warped=warp_preview(pm,rect.width(),rect.height(),mode)
        _ng=(cfg.get('ngang') or cfg['scale'])/100
        back=warp_preview(pm,rect.width()*_ng,rect.height()*cfg['scale']/100,mode) if 'echo' in flags else None
        if cache is not None:cache.update(key=key,pixmap=warped,back=back)
    if back is not None:
        rw=rect.width()*(cfg.get('ngang') or cfg['scale'])/100;rh=rect.height()*cfg['scale']/100
        target=QRectF(rect.center().x()-rw/2,rect.center().y()-rh/2+rect.height()*cfg['shift']/100,rw,rh)
        p.save();p.setOpacity(cfg['opacity']/100);p.drawPixmap(target,back,QRectF(back.rect()));p.restore()
    p.drawPixmap(rect,warped,QRectF(warped.rect()))

def khung(rect, iw, ih, ow, oh, cao=CAO_MAC_DINH):
    """Khung video trên nền thiết kế: BỀ NGANG LUÔN KÍN 100% khung, cao tối đa
    `cao`% khung. Trả (cx, cy, sw, giu) — `giu` = phần chiều cao NGUỒN được
    giữ (1.0 = không cắt; <1 = cắt bớt đều trên/dưới). Xem trước và lúc xuất
    gọi CHUNG hàm này nên hình học khớp nhau."""
    cx,cy,sw=map(float,rect)
    if not all(math.isfinite(v) for v in (cx,cy,sw,iw,ih,ow,oh)) or min(iw,ih,ow,oh,sw)<=0:
        raise ValueError('Khung video không hợp lệ.')
    cao=max(CAO_KHOANG[0],min(CAO_KHOANG[1],float(cao)))/100
    width=float(ow)
    tu_nhien=width*ih/iw
    height=min(tu_nhien,oh*cao)
    giu=height/tu_nhien
    hf=height/oh
    if hf<=.46:     # vừa dải giữa -> chừa chỗ tiêu đề (trên) + Part (dưới) như cũ
        cy=min(max(cy,.26+hf/2),.72-hf/2)
    else:           # user chỉnh cao hơn dải giữa -> chỉ giữ trọn trong khung
        cy=min(max(cy,hf/2),1-hf/2)
    return .5,cy,1.0,giu


def fit_rect(rect, iw, ih, ow, oh, cao=CAO_MAC_DINH):
    """(cx, cy, sw) của `khung` — giữ chữ ký cũ cho các chỗ gọi sẵn có."""
    return khung(rect,iw,ih,ow,oh,cao)[:3]

def image(theme, width, height):
    """Generate at bounded working size, then upscale softly; foreground stays sharp."""
    from PyQt6.QtCore import Qt
    return _texture(theme, min(540,width), min(960,height)).scaled(
        width,height,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)

@lru_cache(maxsize=16)
def _texture(theme,width,height):
    import numpy as np
    from PyQt6.QtGui import QImage
    if theme not in THEMES: raise ValueError('Nền chưa được hỗ trợ.')
    rng=np.random.default_rng(713)
    y,x=np.mgrid[0:height,0:width].astype(float);x/=width;y/=height
    def rgb(s):return np.array([int(s[i:i+2],16) for i in (1,3,5)],dtype=float)
    _,a,b=THEMES[theme]
    mix=np.clip(.25*x+.65*y,0,1)[...,None]
    arr=rgb(a)*(1-mix)+rgb(b)*mix
    if theme=='paper':
        # Broad folds with narrow highlights, irregular orientation and fine grain.
        fold=np.zeros_like(x)
        for _ in range(28):
            angle=rng.uniform(0,6.28);freq=rng.uniform(6,45);phase=rng.uniform(0,6.28)
            wave=np.sin((x*np.cos(angle)+y*np.sin(angle))*freq+phase)
            fold+=(wave+np.sign(wave)*np.abs(wave)**12)*rng.uniform(.6,1.4)
        # Short intersecting creases, rather than only a cloudy broad texture.
        for _ in range(95):
            px,py=rng.uniform(0,1,2);angle=rng.uniform(0,6.28)
            along=(x-px)*np.cos(angle)+(y-py)*np.sin(angle)
            across=-(x-px)*np.sin(angle)+(y-py)*np.cos(angle)
            length=rng.uniform(.035,.18);spread=rng.uniform(.0015,.005)
            crease=np.exp(-(along/length)**4)*np.exp(-(across/spread)**2)
            fold+=crease*np.sign(across)*rng.uniform(3,7)
        arr+=fold[...,None]*1.8+rng.normal(0,2.5,(height,width,1))
    elif theme=='linen':
        weave=np.sin(x*width*2.1)*1.2+np.sin(y*height*2.3)*1.4
        arr+=weave[...,None]+rng.normal(0,.7,(height,width,1))
    elif theme in ('aurora','sunset','mint'):
        colors={'aurora':(19,95,99),'sunset':(34,19,7),'mint':(15,25,17)}
        glow=np.exp(-((x-.24-.12*np.sin(y*5))**2/.14+(y-.3)**2/.34))
        arr+=glow[...,None]*np.array(colors[theme])
        arr+=rng.normal(0,.5,(height,width,1))
    elif theme=='sand':
        waves=np.cos(y*18+x*8+3*np.sin(x*3))
        arr+=waves[...,None]*3.5+rng.normal(0,.8,(height,width,1))
    else:
        diagonal=np.maximum(0,np.cos(x*18+y*12))**36
        arr+=diagonal[...,None]*3
        arr+=rng.normal(0,.45,(height,width,1))
    arr=np.ascontiguousarray(np.clip(arr,0,255).astype('uint8'))
    return QImage(arr.data,width,height,width*3,QImage.Format.Format_RGB888).copy()

def write_background(mode, folder, width, height):
    theme,motion=decode(mode)
    if not theme:raise ValueError('Nền mẫu không hợp lệ.')
    # Extra border permits a slow pan with no black edges or frame distortion.
    w=(int(width*1.08)//2*2) if motion else width
    h=(int(height*1.08)//2*2) if motion else height
    path=Path(folder)/f'{theme}_{w}_{h}.png'
    if not path.exists() and not image(theme,w,h).save(str(path)):
        raise RuntimeError('Không tạo được nền mẫu.')
    return str(path)

def video_filter(mode,width,height):
    _,motion=decode(mode)
    if not motion:return 'setsar=1'
    return (f"crop={width}:{height}:x='(iw-ow)/2*(1+0.65*sin(t*0.23))':"
            "y='(ih-oh)/2*(1+0.65*cos(t*0.19))',setsar=1")
