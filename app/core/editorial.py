"""Versioned, reviewed edit decisions. Source-time coordinates; no AI/network calls."""
from copy import deepcopy
import math
from pathlib import Path

STYLES = {'clean':'Gọn, rõ nội dung', 'funny':'Hài / prank', 'tension':'Căng thẳng', 'explain':'Giải thích'}
KINDS = {'arrow':'Mũi tên động','circle':'Khoanh chi tiết','question':'Dấu hỏi động',
         'alert':'Dấu chấm than','sparkle':'Lấp lánh','heart':'Trái tim',
         'burst':'Tia nhấn','label':'Chữ nhấn','zoom':'Zoom chi tiết',
         'freeze':'Ảnh dừng trong ô','replay':'Phát lại trong ô'}
SOUNDS = ('none','transition','impact','riser','reveal','pop','suspense','comedy','scratch','sad','drumroll')


def number(value, lo, hi, name):
    if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
        raise ValueError(f'{name} phải trong khoảng {lo:g}–{hi:g}.')
    return float(value)


def validate(plan, parts):
    if not isinstance(plan,dict) or plan.get('version')!=1 or plan.get('style') not in STYLES:
        raise ValueError('Bộ dựng không hợp lệ hoặc cần phiên bản ứng dụng mới hơn.')
    events=plan.get('events')
    if not isinstance(events,list) or len(events)>12:raise ValueError('Tối đa 12 điểm nhấn mỗi Part.')
    clean=[]
    for raw in events:
        if not isinstance(raw,dict):raise ValueError('Điểm nhấn không hợp lệ.')
        i=raw.get('part')
        if type(i) is not int or not 0<=i<len(parts):raise ValueError('Điểm nhấn không thuộc cảnh nào.')
        length=float(parts[i]['end'])-float(parts[i]['start'])
        start=number(raw.get('offset'),0,max(0,length-.2),'Mốc trong cảnh')
        duration=number(raw.get('duration'),.2,min(4.,length-start),'Độ dài điểm nhấn')
        kind=raw.get('kind')
        if kind not in KINDS:raise ValueError('Hiệu ứng chưa hỗ trợ.')
        if kind=='replay' and start<duration:
            raise ValueError('Phát lại cần đủ thời gian trước mốc chèn trong cùng cảnh; tăng mốc hoặc giảm độ dài.')
        text=raw.get('text','')
        if not isinstance(text,str) or len(text)>72 or any(ord(c)<32 for c in text):
            raise ValueError('Chữ nhấn cần một dòng, tối đa 72 ký tự.')
        if kind=='label' and not text.strip():raise ValueError('Chưa nhập chữ nhấn.')
        sound=raw.get('sound','none')
        if sound not in SOUNDS:raise ValueError('Nhóm tiếng động không hợp lệ.')
        sound_file=str(raw.get('sound_file',''))
        if sound_file and (Path(sound_file).name!=sound_file or '/' in sound_file or '\\' in sound_file or ':' in sound_file):
            raise ValueError('Tên tiếng động không hợp lệ.')
        tracked=bool(raw.get('track',False))
        if tracked and kind not in ('arrow','circle'):raise ValueError('Chỉ mũi tên/khoanh chi tiết hỗ trợ bám vật.')
        clean.append(dict(part=i,offset=start,duration=duration,kind=kind,text=text.strip(),
            x=number(raw.get('x',.5),.05,.95,'Vị trí ngang'),
            y=number(raw.get('y',.22),.05,.95,'Vị trí dọc'),
            size=number(raw.get('size',.18),.08,.45,'Kích thước'),
            track=tracked, target_x=number(raw.get('target_x',.5),.1,.9,'Tâm vật ngang'),
            target_y=number(raw.get('target_y',.5),.1,.9,'Tâm vật dọc'),
            sound=sound, sound_file=sound_file, sound_gain=number(raw.get('sound_gain',.7),0,1,'Âm lượng tiếng nhấn'),
            reason=str(raw.get('reason','Người dùng chọn'))[:240]))
    # No simultaneous overlays; do not silently throw away user edits.
    clean.sort(key=lambda e:(e['part'],e['offset']))
    for a,b in zip(clean,clean[1:]):
        if a['part']==b['part'] and a['offset']+a['duration']>b['offset']+.001:
            raise ValueError('Hai điểm nhấn chồng nhau trong cùng cảnh; hãy dời mốc hoặc rút ngắn.')
    return dict(version=1,style=plan['style'],events=clean,enabled=bool(plan.get('enabled',True)),transitions=bool(plan.get('transitions',True)),
                music_arc=bool(plan.get('music_arc',True)))


def propose(parts,style='clean'):
    """Evidence-derived draft, never infer emotion/identity from keywords."""
    style=style if style in STYLES else 'clean'
    events=[]
    for i,p in enumerate(parts):
        if len(events)>=4:break
        length=p['end']-p['start']
        if length<1:continue
        # Only the first narrative sentence / explicit AI accent is a candidate.
        if p.get('role')=='hook' and p.get('mode')=='narrate' and p.get('text'):
            # Exact excerpt, not a second invented hook.
            words=p['text'].split();text=' '.join(words[:7])
            if len(text)>65:continue
            events.append(dict(part=i,offset=.1,duration=min(2.5,length-.1),kind='label',text=text,
                reason='Trích nguyên phần đầu lời kể; cần duyệt cùng kịch bản.',sound='pop' if style=='funny' else 'none'))
        elif p.get('sfx','none')!='none' and p.get('sfx_reason'):
            at=min(max(0.,float(p.get('sfx_offset',0))),length-.5)
            events.append(dict(part=i,offset=at,duration=min(1.2,length-at),
                kind='burst' if style=='funny' else 'sparkle' if style=='explain' else 'alert',
                reason=p['sfx_reason'],sound=p['sfx']))
    return validate(dict(version=1,style=style,events=events,music_arc=True),parts)


def timeline(plan,parts,segments):
    """Map through merged/disjoint source cuts; reject crossing excluded footage."""
    result=[]
    for event in validate(plan,parts)['events']:
        a=float(parts[event['part']]['start'])+event['offset'];b=a+event['duration'];acc=0.
        for s,e in segments:
            if a>=s-.001 and b<=e+.001:
                result.append(dict(event,start=acc+a-s,end=acc+b-s,source_start=a,source_end=b));break
            acc+=e-s
        else:raise ValueError('Điểm nhấn nằm ngoài các đoạn xuất; cần duyệt lại.')
    return result


def sound_parts(plan,parts):
    """Explicit editor events replace automatic audio accents, no duplicate hits."""
    out=[]
    for e in validate(plan,parts)['events']:
        if e['sound']=='none' or e['sound_gain']==0:continue
        p=deepcopy(parts[e['part']]);p.update(sfx=e['sound'],sfx_offset=e['offset'],
            sfx_reason=e['reason'],sfx_gain=e['sound_gain'])
        out.append(p)
    return out


def replaces_opening_title(plan,parts,segments,hook_duration):
    """One opening text layer: a reviewed label takes priority over template hook."""
    if not plan or not plan.get('enabled',True):return False
    return any(e['kind']=='label' and e['start']<hook_duration
               for e in timeline(plan,parts,segments))


def music_envelope(plan,parts,segments,speed):
    """Role-based music levels, smooth ramps; existing speech ducking remains."""
    if not plan.get('music_arc'):return ''
    levels={'hook':.55,'setup':.65,'build':.8,'payoff':1.,'ending':.65}
    expr='.65'
    for p in parts:
        elapsed=0.
        for a,b in segments:
            lo=max(a,p['start']);hi=min(b,p['end'])
            if hi>lo:
                start=(elapsed+lo-a)/speed;end=(elapsed+hi-a)/speed
                delta=levels.get(p.get('role'),.75)-.65
                if delta:expr+=f"+({delta:.3f})*min(1,max(0,(t-{start:.4f})/.3))*min(1,max(0,({end:.4f}-t)/.3))"
            elapsed+=b-a
    return f",volume='{expr}':eval=frame"


def transitions(plan,parts,segments):
    if not plan.get('transitions',True):return []
    result=[]
    for i,(_a,b) in enumerate(segments[:-1]):
        a,_b=segments[i+1]
        role=next((p.get('role','build') for p in parts if p['start']<=a<p['end']),'build')
        if abs(a-b)<.15:result.append(('fade',0.));continue
        if plan['style']=='funny':kind='smoothleft' if role=='payoff' else 'wipeleft'
        elif plan['style']=='tension':kind='fadeblack' if role=='payoff' else 'fade'
        elif plan['style']=='explain':kind='dissolve'
        else:kind='fade'
        result.append((kind,.18 if plan['style']=='funny' else .25))
    return result
