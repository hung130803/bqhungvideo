"""Reviewed report layouts, sourced stills and bounded keyframe motion."""
from pathlib import Path

LAYOUTS={'template':'Theo mẫu xuất hiện tại','report':'Phóng sự · vàng / đỏ','explain':'Giải thích · xanh'}

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

def append(cmd,filters,label,index,plan,parts,segments,folder,width,height):
    if plan.get('layout','template')=='template':return label,index
    color='#FFDE39' if plan['layout']=='report' else '#64D9FF'
    total=sum(b-a for a,b in segments);cards=[]
    title=plan.get('report_title','').strip()
    if title:cards.append((title,0,total,.14,.13,True))
    elapsed=0.
    for a,b in segments:
        for p in parts:
            lo=max(a,p['start']);hi=min(b,p['end'])
            if hi<=lo:continue
            lines=pages(p.get('text','')) if p.get('mode')=='narrate' else ['ÂM THANH GỐC']
            for j,text in enumerate(lines):
                duration=(hi-lo)/len(lines)
                cards.append((text,elapsed+lo-a+j*duration,duration,.65,.16,False))
        elapsed+=b-a
    for n,(text,start,duration,y,h,title) in enumerate(cards):
        path=Path(folder)/f'report_{n}.png';cw=int(width*.94)//2*2;ch=int(height*h)//2*2
        panel(path,text,cw,ch,color,title)
        cmd+=['-loop','1','-framerate','30','-t',f'{duration:.6f}','-i',str(path)]
        filters.append(f'[{index}:v]format=rgba,setpts=PTS-STARTPTS+{start:.6f}/TB[reportcard{n}]')
        filters.append(f"{label}[reportcard{n}]overlay=x=(W-w)/2:y=H*{y:.4f}:eof_action=repeat:enable='gte(t,{start:.6f})*lt(t,{start+duration:.6f})'[reportout{n}]")
        label=f'[reportout{n}]';index+=1
    return label,index
