"""Portable licensed soundtrack choices, pinned per Part before human approval."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

MOODS={'bright':'Vui / tích cực','playful':'Tinh nghịch / hài','calm':'Êm / giải thích',
       'mystery':'Bí ẩn','tension':'Căng thẳng','emotional':'Cảm xúc / trầm'}
PREFIX='bqmusic:'

def folder():
    from config import ROOT_DIR
    return ROOT_DIR/'app/assets/music'

@lru_cache(maxsize=1)
def catalog():
    data=json.loads((folder()/'catalog.json').read_text(encoding='utf-8'))
    if data.get('version')!=1:raise ValueError('Kho nhạc cần phiên bản ứng dụng mới hơn.')
    tracks=data['tracks'];seen=set()
    for t in tracks:
        name=t['file']
        if (t['id'] in seen or t['mood'] not in MOODS or t['license']!='CC0-1.0'
                or Path(name).name!=name or '/' in name or '\\' in name or ':' in name):
            raise ValueError('Thông tin kho nhạc không hợp lệ.')
        seen.add(t['id'])
    return tuple(tracks)

def track(ident):
    value=next((t for t in catalog() if t['id']==ident),None)
    if value is None:raise ValueError('Không tìm thấy bài nhạc đã chọn: '+str(ident))
    return dict(value)

def resolve(ref,*,verify=True):
    if not ref.startswith(PREFIX):return ref
    if ref==PREFIX+'off':return ''
    t=track(ref[len(PREFIX):]);p=folder()/t['file']
    if not p.is_file():raise ValueError('Thiếu bài nhạc đã duyệt: '+t['title']+'. Cập nhật lại ứng dụng.')
    if verify and hashlib.sha256(p.read_bytes()).hexdigest()!=t['sha256']:
        raise ValueError('File nhạc đã thay đổi so với thư viện: '+t['title'])
    return str(p)

def choose(ref,style,seed,index,used=(),story_mood='calm'):
    """Stable within an analysis; avoid repeats within the selected mood until exhausted."""
    if not ref.startswith(PREFIX+'auto:'):return ref
    mood=ref.split(':',2)[2]
    if mood=='story':mood=story_mood if story_mood in MOODS else 'calm'
    if mood=='style':mood={'funny':'playful','tension':'tension','explain':'calm','clean':'calm'}.get(style,'calm')
    if mood not in MOODS:raise ValueError('Nhóm nhạc không hợp lệ.')
    candidates=sorted((t for t in catalog() if t['mood']==mood),
        key=lambda t:hashlib.sha256((str(seed)+'|'+t['id']).encode()).hexdigest())
    if not candidates:raise ValueError('Kho nhạc chưa có bài thuộc nhóm '+MOODS[mood])
    unused=[t for t in candidates if PREFIX+t['id'] not in used]
    chosen=unused[0] if unused else candidates[index%len(candidates)]
    return PREFIX+chosen['id']

def describe(ref):
    if not ref:return 'Theo nhạc của mẫu xuất'
    if ref==PREFIX+'off':return 'Tắt nhạc nền'
    if ref.startswith(PREFIX+'auto:'):
        mood=ref.split(':',2)[2]
        return 'Tự chọn · '+('theo nội dung Part (AI đề xuất, cần nghe duyệt)' if mood=='story' else 'theo phong cách dựng' if mood=='style' else MOODS.get(mood,mood))
    if ref.startswith(PREFIX):
        t=track(ref[len(PREFIX):]);return f"{t['title']} · {MOODS[t['mood']]} · {t['author']} · CC0"
    return Path(ref).name

def export_path(meta,template_path):
    ref=meta.get('music_path','')
    if ref==PREFIX+'off':return None
    path=resolve(ref) if ref else template_path
    if ref and not Path(path).is_file():raise ValueError('Không tìm thấy nhạc nền đã chọn; giữ nguyên video nguồn.')
    return path or None
