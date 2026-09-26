"""Reviewed report layouts, sourced stills and bounded keyframe motion."""
from pathlib import Path
import math

LAYOUTS={'template':'Theo mẫu xuất hiện tại','report':'Phóng sự · vàng / đỏ','explain':'Giải thích · xanh'}

def keeps_full_source(plan):
    """Report coordinates and preview refer to the uncropped source image."""
    return bool(plan and plan.get('enabled',True) and plan.get('layout','template') in ('report','explain'))

def geometry(iw,ih,ow,oh):
    # Source always fits between cards. No crop, including portrait footage.
    scale=min(ow*.98/iw,oh*.34/ih)
    return (.5,.46,iw*scale/ow)

def pages(text,limit=150):
    result=[];line=''
    for char in str(text):
        if len(line)>=limit and (char.isspace() or len(line)>=limit+25):
            result.append(line.strip());line=''
        line+=char
    if line.strip():result.append(line.strip())
    return result

def panel(path,text,width,height,color,title=False):
    from PyQt6.QtCore import Qt,QRectF
    from PyQt6.QtGui import QImage,QPainter,QFont,QFontMetrics,QColor,QPen
    image=QImage(width,height,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(13,18,27,240));painter.setPen(QPen(QColor('#FF5757' if title and color=='#FFDE39' else color),max(1,width/220)))
    painter.drawRoundedRect(QRectF(2,2,width-4,height-4),width*.025,width*.025)
    pad=max(8,int(width*.025));rect=QRectF(pad,pad,width-2*pad,height-2*pad)
    flags=Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap
    font=QFont('Be Vietnam Pro');font.setBold(True)
    for size in range(max(12,int(width*(.047 if title else .041))),8,-1):
        font.setPixelSize(size);bounds=QFontMetrics(font).boundingRect(rect.toRect(),int(flags),text)
        if bounds.height()<=rect.height() and bounds.width()<=rect.width():break
    if bounds.height()>rect.height() or bounds.width()>rect.width():
        painter.end();raise ValueError('Chữ quá dài cho khung phóng sự; rút gọn tiêu đề/lời kể trước khi xuất.')
    painter.setFont(font);painter.setPen(QColor(color if title else '#FFFFFF'));painter.drawText(rect,int(flags),text);painter.end()
    if not image.save(str(path)):raise RuntimeError('Không tạo được khung phóng sự.')

def spoken_cards(events,total):
    """Use measured cue times; never stretch text to fill the source shot."""
    cards=[]
    for event in events:
        cues=event.get('words') or []
        if not cues and str(event.get('text','')).strip():
            a,b=event.get('speech') or [event['start'],event['end']]
            lines=pages(event['text'],70)
            size=sum(len(line) for line in lines)
            cursor=float(a)
            for line in lines:
                end=cursor+(float(b)-float(a))*len(line)/max(1,size)
                cues.append([cursor,end,line]);cursor=end
        for a,b,text in cues:
            a,b=float(a),float(b)
            if not math.isfinite(a+b):continue
            lo,hi=event.get('speech') or [event.get('start',0),event.get('end',total)]
            a=max(0.,float(lo),a);b=min(float(total),float(hi),b)
            text=str(text).strip()
            if b>a and text:cards.append((text,a,b-a,.65,.16,False))
    return sorted(cards,key=lambda c:c[1])


def append_spoken_track(cmd,filters,label,index,cards,folder,width,height,color,total):
    """One timed image stream, not one FFmpeg decoder per spoken phrase."""
    from PyQt6.QtGui import QImage
    from PyQt6.QtCore import Qt
    cw=int(width*.94)//2*2;ch=int(height*.16)//2*2
    blank=Path(folder)/'report_blank.png'
    image=QImage(cw,ch,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
    if not image.save(str(blank)):raise RuntimeError('Không tạo được nền phụ đề trong suốt.')
    entries=[];cursor=0.
    for n,(text,start,duration,_,__,___) in enumerate(sorted(cards,key=lambda c:c[1])):
        end=min(total,start+duration);start=max(cursor,start)
        if end<=start:continue
        if start>cursor:entries.append((blank,start-cursor))
        path=Path(folder)/f'spoken_{n}.png';panel(path,text,cw,ch,color)
        entries.append((path,end-start));cursor=end
    if cursor<total:entries.append((blank,total-cursor))
    if not entries:return label,index
    manifest=Path(folder)/'report_spoken.ffconcat'
    lines=['ffconcat version 1.0']
    for path,duration in entries+[(blank,.1)]:
        escaped=path.resolve().as_posix().replace("'", "'\\''")
        lines.extend([f"file '{escaped}'",f'duration {duration:.9f}'])
    lines.append("file 'report_blank.png'")
    manifest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    cmd+=['-f','concat','-safe','0','-i',str(manifest)]
    filters.append(f'[{index}:v]format=rgba,setpts=PTS-STARTPTS[reportspoken]')
    filters.append(f"{label}[reportspoken]overlay=x=(W-w)/2:y=H*.65:eof_action=pass[reportspokenout]")
    return '[reportspokenout]',index+1


def append(cmd,filters,label,index,plan,parts,segments,folder,width,height,narration_events=None):
    if plan.get('layout','template')=='template':return label,index
    color='#FFDE39' if plan['layout']=='report' else '#64D9FF'
    total=sum(b-a for a,b in segments);cards=[]
    title=plan.get('report_title','').strip()
    if title:cards.append((title,0,total,.14,.13,True))
    if narration_events is not None:cards.extend(spoken_cards(narration_events,total))
    elapsed=0.
    for a,b in segments:
        for p in parts:
            lo=max(a,p['start']);hi=min(b,p['end'])
            if hi<=lo:continue
            if p.get('mode')=='narrate' and narration_events is not None:continue
            lines=pages(p.get('text','')) if p.get('mode')=='narrate' else ['ÂM THANH GỐC']
            for j,text in enumerate(lines):
                duration=(hi-lo)/len(lines)
                cards.append((text,elapsed+lo-a+j*duration,duration,.65,.16,False))
        elapsed+=b-a
    if narration_events is not None:
        label,index=append_spoken_track(cmd,filters,label,index,[c for c in cards if not c[-1]],folder,width,height,color,total)
        cards=[c for c in cards if c[-1]]
    for n,(text,start,duration,y,h,title) in enumerate(cards):
        path=Path(folder)/f'report_{n}.png';cw=int(width*.94)//2*2;ch=int(height*h)//2*2
        panel(path,text,cw,ch,color,title)
        cmd+=['-loop','1','-framerate','30','-t',f'{duration:.6f}','-i',str(path)]
        filters.append(f'[{index}:v]format=rgba,setpts=PTS-STARTPTS+{start:.6f}/TB[reportcard{n}]')
        filters.append(f"{label}[reportcard{n}]overlay=x=(W-w)/2:y=H*{y:.4f}:eof_action=repeat:enable='gte(t,{start:.6f})*lt(t,{start+duration:.6f})'[reportout{n}]")
        label=f'[reportout{n}]';index+=1
    return label,index
