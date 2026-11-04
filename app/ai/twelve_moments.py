"""Optional, resumable TwelveLabs candidate retrieval. Never factual evidence."""
import hashlib
import json
import math
from pathlib import Path
import threading
import time

BASE = 'https://api.twelvelabs.io/v1.3'
QUERIES = (
    ('conflict', 'A disagreement or confrontation with a clear response from another person.'),
    ('change', 'An unexpected change or surprising discovery followed by a reaction.'),
    ('payoff', 'An important action followed by its immediate result or consequence.'),
    ('explanation', 'Someone explains or demonstrates something useful with a concrete result.'),
)
_LOCK = threading.Lock()

class Rejected(RuntimeError):
    """Server explicitly rejected work; safe to retry after fixing the cause."""
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8'); temp.replace(p)


def validate_hits(data, duration, video_id):
    if not isinstance(data,dict) or not isinstance(data.get('data'),list):
        raise RuntimeError('TwelveLabs trả kết quả tìm cảnh sai cấu trúc; giữ các bước đã xong.')
    rows = []
    for r in data['data']:
        if not isinstance(r,dict):continue
        if str(r.get('video_id')) != str(video_id):
            continue
        try:
            a, b = float(r['start']), float(r['end'])
        except (ValueError, TypeError, KeyError):
            continue
        if math.isfinite(a) and math.isfinite(b) and 0 <= a < b <= duration + .1:
            rows.append({'start': a, 'end': min(b, duration), 'rank': len(rows)+1})
        if len(rows) == 5: break
    return rows


def candidate_ids(units, result):
    """Bounded ranking hints only; no made-up confidence or changed source facts."""
    scores = {}
    for hits in result.get('queries', {}).values():
        for hit in hits:
            for u in units:
                if u['start'] < hit['end'] and u['end'] > hit['start']:
                    scores[u['id']] = scores.get(u['id'], 0) + 1 / hit['rank']
    return sorted(scores, key=lambda i: (-scores[i], i))[:20]


class Client:
    def __init__(self, keys, ctx):
        import requests
        self.session = requests.Session()
        self.keys = keys; self.ctx = ctx; self.key = keys[0]

    def request(self, method, endpoint, **kwargs):
        self.ctx.check_canceled()
        try:
            response = self.session.request(method, BASE+endpoint,
                headers={'x-api-key': self.key}, timeout=(15, 120 if method=='POST' and endpoint=='/assets' else 45), **kwargs)
        except Exception:
            raise RuntimeError('TwelveLabs mất kết nối. Tiến độ đã lưu; yêu cầu chưa rõ kết quả sẽ không tự gửi trùng.') from None
        if not response.ok:
            code = ''
            try: code = str(response.json().get('code', ''))[:100]
            except ValueError: pass
            if response.status_code == 429:
                raise Rejected('TwelveLabs đang giới hạn lượt. Đã giữ kết quả; thử lại khi hạn mức hồi. Không đổi tài khoản để tải lại video.')
            if response.status_code in (402, 422):
                raise Rejected('TwelveLabs không nhận yêu cầu: kiểm tra dung lượng/hạn mức trong Billing. Đã giữ tiến độ. '+code)
            if response.status_code in (401,403):
                raise Rejected('Key TwelveLabs hết hạn hoặc không có quyền. Có thể chọn key khác cùng kho rồi thử lại.')
            raise RuntimeError(f'TwelveLabs HTTP {response.status_code}; đã giữ tiến độ. '+code)
        try:
            value=response.json() if response.content else {}
        except ValueError:
            raise RuntimeError('TwelveLabs trả nội dung chưa đọc được; giữ tiến độ, không tự gửi trùng.') from None
        if not isinstance(value,dict):raise RuntimeError('TwelveLabs trả dữ liệu không hợp lệ; giữ tiến độ.')
        return value

    def wait(self, endpoint, label):
        deadline = time.monotonic()+1200
        while time.monotonic() < deadline:
            data = self.request('GET', endpoint)
            if data.get('status')=='ready': return data
            if data.get('status')=='failed':
                raise RuntimeError('TwelveLabs xử lý video thất bại; đã giữ ID để kiểm tra, không tải lại tự động.')
            self.ctx.progress(.02, 'TwelveLabs · '+label+' · '+str(data.get('status','đang chờ')))
            for _ in range(25): self.ctx.check_canceled(); time.sleep(.2)
        raise RuntimeError('TwelveLabs chưa xử lý xong sau 20 phút; thử lại để kiểm tra cùng công việc.')


def retrieve(src, duration, preset, ctx):
    if not preset.get('story_twelve'): return {}
    from app.ai.twelve_keys import load
    from config import DATA_DIR, settings
    keys = load()
    slot = int(preset.get('story_twelve_key', 0))
    if not 0 <= slot < len(keys): raise RuntimeError('Chưa có key TwelveLabs đã chọn. Mở Cài đặt dựng chuyện → TwelveLabs.')
    if duration > 60*int(preset.get('story_twelve_max_minutes', 60)):
        raise RuntimeError('Video vượt giới hạn phút/lần gửi TwelveLabs bạn đặt. Tăng giới hạn hoặc tắt TwelveLabs cho lượt này.')
    while not _LOCK.acquire(timeout=.2):
        ctx.check_canceled(); ctx.progress(.01,'Đợi lượt TwelveLabs để tránh tải trùng và đầy kho.')
    client = Client([keys[slot]], ctx)
    try:
        index = str(preset.get('story_twelve_index','')).strip()
        indexes = client.request('GET','/indexes',params={'page_limit':50}).get('data',[])
        if index:
            info = client.request('GET','/indexes/'+index)
        else:
            candidates = [x for x in indexes if any(m.get('model_name','').startswith('marengo') for m in x.get('models',[]))]
            if not candidates: raise RuntimeError('TwelveLabs chưa có kho Marengo. Tạo kho trên tài khoản rồi thử lại.')
            info = candidates[0]; index=info['_id']
        p = Path(src); stat=p.stat()
        stamp=[str(p.resolve()),stat.st_size,stat.st_mtime_ns]
        folder=Path(DATA_DIR)/'_cache'/'twelvelabs'/digest([index,stamp])
        state_path=folder/'state.json'; state=read(state_path)
        if state.get('complete'): return state
        state.update(index=index,source=stamp,model=info.get('models',[]))
        if state.get('uncertain'):
            raise RuntimeError('TwelveLabs: lần trước gửi yêu cầu nhưng chưa nhận ID. Cần kiểm tra kho trước khi thử lại để tránh tải/lập chỉ mục trùng.')
        folder.mkdir(parents=True,exist_ok=True)
        if not state.get('asset_id'):
            proxy=folder/'upload.mp4'
            if not proxy.exists():
                from app.core.ffmpeg_utils import _run
                target=folder/'upload.partial.mp4'
                bitrate=min(900,max(80,int(175_000_000*8/max(duration,1)/1000)-96))
                cmd=[settings.FFMPEG_PATH,'-hide_banner','-loglevel','error','-y','-i',src,
                     '-map','0:v:0','-map','0:a:0?','-vf','scale=-2:480','-c:v','libx264','-preset','veryfast',
                     '-threads','2','-b:v',str(bitrate)+'k','-maxrate',str(bitrate)+'k','-bufsize',str(bitrate*2)+'k',
                     '-c:a','aac','-b:a','96k','-movflags','+faststart',str(target)]
                ctx.progress(.01,'Chuẩn bị bản gửi TwelveLabs · giữ nguyên video gốc')
                code = _run(cmd)
                ctx.check_canceled()
                if code or not target.exists(): raise RuntimeError('Không tạo được bản gửi TwelveLabs; video gốc còn nguyên.')
                target.replace(proxy)
            if proxy.stat().st_size>=200_000_000: raise RuntimeError('Bản gửi vượt 200 MB; chưa tải lên TwelveLabs.')
            state['uncertain']='upload'; write(state_path,state)
            ctx.progress(.02,'Đang gửi video lên TwelveLabs')
            with proxy.open('rb') as stream:
                data=client.request('POST','/assets',data={'method':'direct','enable_hls':'false'},files={'file':(proxy.name,stream,'video/mp4')})
            state['asset_id']=data['_id']; state.pop('uncertain'); write(state_path,state)
        client.wait('/assets/'+state['asset_id'],'kiểm tra video')
        if not state.get('video_id'):
            state['uncertain']='index'; write(state_path,state)
            data=client.request('POST','/indexes/'+index+'/indexed-assets',json={'asset_id':state['asset_id']})
            state['video_id']=data['_id']; state.pop('uncertain'); write(state_path,state)
        endpoint='/indexes/'+index+'/indexed-assets/'+state['video_id']
        client.wait(endpoint,'đọc nội dung video')
        for name, query in QUERIES:
            if name in state.get('queries',{}): continue
            ctx.progress(.025,'TwelveLabs · tìm tình tiết '+str(len(state.get('queries',{}))+1)+'/4')
            fields=[('index_id',index),('query_text',query),('search_options','visual'),('search_options','audio'),
                    ('search_options','transcription'),('operator','or'),('page_limit','5'),
                    ('filter',json.dumps({'id':[state['video_id']]}))]
            data=client.request('POST','/search',files=[(k,(None,v)) for k,v in fields])
            state.setdefault('queries',{})[name]=validate_hits(data,duration,state['video_id']); write(state_path,state)
        state['complete']=True; write(state_path,state)
        return state
    except Rejected:
        if 'state' in locals() and 'state_path' in locals():
            state.pop('uncertain',None); write(state_path,state)
        raise
    finally:
        client.session.close(); _LOCK.release()
