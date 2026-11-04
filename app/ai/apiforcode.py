"""Explicit APIforcode connection. No automatic provider/model fallback."""
from __future__ import annotations
import base64
from pathlib import Path
import re
import json
import time
import queue
import threading
from contextlib import contextmanager
import requests

BASE_URL = 'https://api.apiforcode.com/v1'


TEXT_REQUEST_TIMEOUT = 300.
_PROGRESS = threading.local()
_HTTP_SLOTS = threading.BoundedSemaphore(3)

@contextmanager
def request_progress(callback=None):
    previous=getattr(_PROGRESS,'callback',None)
    _PROGRESS.callback=callback
    try:yield
    finally:_PROGRESS.callback=previous

def _transport(payload,key,streaming,seconds):
    """One POST, bounded across headers AND body; cancellation never resends it."""
    from app.ai import llm
    started=time.monotonic();deadline=started+seconds
    llm._check_call_budget(seconds)
    slots=_HTTP_SLOTS
    if not slots.acquire(blocking=False):
        raise llm.LLMError('apiforcode_request_uncertain: Còn yêu cầu APIforcode đang đóng kết nối; chưa gửi yêu cầu mới. Chờ kết nối cũ kết thúc.')
    stop=threading.Event();done=threading.Event();state={'phase':'waiting_headers'};result={}
    def worker():
        response=None
        try:
            # Always stream transport so JSON fallback cannot block the caller.
            response=requests.post(BASE_URL+'/chat/completions',headers={'Authorization':'Bearer '+key},
                json=payload,timeout=(15,seconds),allow_redirects=False,stream=True)
            if stop.is_set():return
            if streaming and response.ok and 'text/event-stream' in str(response.headers.get('Content-Type','')).lower():
                state['phase']='receiving_stream'
                body=_stream_body(response,deadline,stop)
            else:
                state['phase']='reading_json'
                body=response.json()
            if not stop.is_set():result['value']=(response,body)
        except Exception as exc:
            result['error']=exc
        finally:
            # iter_lines owns an SSE socket until it exits; don't block cancel on close.
            try:
                if response is not None and state['phase']!='receiving_stream':response.close()
            finally:
                slots.release();done.set()
    threading.Thread(target=worker,daemon=True,name='apiforcode-http').start()
    outcome='interrupted';last=None;next_update=0.
    try:
        while True:
            llm._check_call_budget(seconds)
            elapsed=time.monotonic()-started
            if elapsed>=seconds:
                outcome='deadline'
                raise llm.LLMError(f'apiforcode_request_uncertain: Hết {seconds:.0f} giây chờ APIforcode tại bước {state["phase"]}. Đã giữ phần hoàn tất; chưa rõ đã trừ lượt, không tự gửi lại.')
            phase=state['phase']
            if phase!=last or elapsed>=next_update:
                callback=getattr(_PROGRESS,'callback',None)
                if callback:callback(phase,elapsed,seconds)
                last=phase;next_update=elapsed+5
            if done.wait(min(.2,seconds-elapsed)):break
        if 'error' in result:
            error=result['error'];outcome=type(error).__name__
            if isinstance(error,requests.ConnectTimeout):
                raise llm.LLMError('apiforcode_request_uncertain: Hết thời gian kết nối APIforcode (15 giây); không tự gửi lại.') from None
            if isinstance(error,requests.ReadTimeout):
                raise llm.LLMError(f'apiforcode_request_uncertain: APIforcode chưa trả lời sau {seconds:.0f} giây tại bước {state["phase"]}; đã giữ tiến độ, không tự gửi lại.') from None
            if isinstance(error,requests.RequestException):
                raise llm.LLMError(f'apiforcode_request_uncertain: Kết nối APIforcode bị ngắt tại bước {state["phase"]}; chưa rõ đã trừ lượt, không tự gửi lại.') from None
            if isinstance(error,ValueError):
                raise llm.LLMError('apiforcode_request_uncertain: APIforcode trả dữ liệu không đọc được; không tự gửi lại.') from None
            raise error
        llm._check_call_budget(seconds)
        if time.monotonic()>=deadline:
            outcome='deadline'
            raise llm.LLMError('apiforcode_request_uncertain: APIforcode trả lời sau hạn chờ; không tự gửi lại.')
        outcome='received'
        return result['value']
    finally:
        stop.set()
        # Diagnostic counters only. No key, prompt, source path or response text.
        try:
            from config import LOGS_DIR
            LOGS_DIR.mkdir(parents=True,exist_ok=True)
            with (LOGS_DIR/('apiforcode_transport_'+time.strftime('%Y%m%d')+'.log')).open('a',encoding='utf-8') as log:
                log.write(json.dumps(dict(phase=state['phase'],outcome=outcome,seconds=round(time.monotonic()-started,2),limit=seconds))+'\n')
        except OSError:pass

def _stream_body(response, deadline, abort=None):
    """Only return complete SSE choices; no retry or partial JSON acceptance.

    A daemon owns the socket reader. The caller remains cancelable even if
    the remote stream stops sending bytes. Queue size bounds buffered data.
    """
    from app.ai import llm
    messages=queue.Queue(maxsize=32);stop=threading.Event();reader_done=threading.Event()
    def put(value):
        while not stop.is_set():
            try:messages.put(value,timeout=.1);return
            except queue.Full:pass
    def reader():
        try:
            for line in response.iter_lines(chunk_size=1):
                if stop.is_set():break
                put(('line',line))
                if line.strip()==b'data: [DONE]':break
            put(('eof',None))
        except Exception:put(('error',None))
        finally:
            try:response.close()
            finally:reader_done.set()
    threading.Thread(target=reader,daemon=True,name='apiforcode-stream').start()
    pieces=[];finish=None;usage={};done=False;size=0;count=0;refusal=False
    try:
        while True:
            if abort is not None and abort.is_set():raise llm.LLMError('apiforcode_request_uncertain: Đã ngừng nhận phản hồi; không tự gửi lại.')
            llm._check_call_budget(TEXT_REQUEST_TIMEOUT)
            remaining=deadline-time.monotonic()
            if remaining<=0:raise llm.LLMError('apiforcode_request_uncertain: Hết thời gian nhận phản hồi APIforcode; đã giữ tiến độ, không tự gửi lại.')
            try:kind,line=messages.get(timeout=min(.2,remaining))
            except queue.Empty:continue
            if kind=='error':raise llm.LLMError('apiforcode_request_uncertain: Kết nối APIforcode bị ngắt khi đang nhận; không dùng kết quả thiếu hoặc tự gửi lại.')
            if kind=='eof':break
            count+=1
            if count>100000:raise llm.LLMError('apiforcode_request_uncertain: Phản hồi APIforcode quá lớn; không tự gửi lại.')
            if not line or not line.startswith(b'data:'):continue
            data=line[5:].strip()
            if data==b'[DONE]':done=True;break
            try:value=json.loads(data)
            except (ValueError,UnicodeError):raise llm.LLMError('apiforcode_request_uncertain: Dữ liệu streaming APIforcode không hợp lệ; không tự gửi lại.') from None
            if not isinstance(value,dict) or value.get('error'):
                raise llm.LLMError('apiforcode_request_uncertain: APIforcode báo lỗi giữa phản hồi; không tự gửi lại.')
            if isinstance(value.get('usage'),dict):usage=value['usage']
            choices=value.get('choices') or []
            if not isinstance(choices,list):raise llm.LLMError('apiforcode_request_uncertain: Streaming sai cấu trúc.')
            for choice in choices:
                if not isinstance(choice,dict) or choice.get('index',0)!=0:continue
                delta=choice.get('delta') or {}
                if not isinstance(delta,dict):raise llm.LLMError('apiforcode_request_uncertain: Streaming sai nội dung.')
                refusal=refusal or bool(delta.get('refusal'))
                text=delta.get('content')
                if isinstance(text,str):
                    size+=len(text)
                    if size>1000000:raise llm.LLMError('apiforcode_request_uncertain: Nội dung APIforcode quá lớn.')
                    pieces.append(text)
                if choice.get('finish_reason'):finish=choice['finish_reason']
        if not done or not finish:
            raise llm.LLMError('apiforcode_request_uncertain: APIforcode chưa kết thúc phản hồi; không dùng phần thiếu hoặc tự gửi lại.')
        return {'choices':[{'finish_reason':finish,'message':{'content':''.join(pieces),'refusal':refusal}}],'usage':usage}
    finally:
        stop.set()
        if abort is not None:reader_done.wait()


def chat(key, model, prompt, system='', image_paths=(), timeout=None):
    from app.ai import llm
    content = prompt
    if image_paths:
        if len(image_paths)>8:
            raise llm.LLMTooLarge('APIforcode: app giới hạn 8 ảnh mỗi yêu cầu; chia nhóm để giữ chi tiết.')
        content=[{'type':'text','text':prompt}]
        for path in image_paths:
            data=Path(path).read_bytes()
            mime='image/png' if data.startswith(b'\x89PNG') else 'image/jpeg'
            content.append({'type':'image_url','image_url':{'url':f'data:{mime};base64,'+base64.b64encode(data).decode('ascii')}})
    messages=([{'role':'system','content':system}] if system else [])+[{'role':'user','content':content}]
    streaming=not image_paths
    payload={'model':model,'messages':messages,'stream':streaming,'max_tokens':min(6000,max(1800,len(image_paths)*600)) if image_paths else 6000}
    maximum=120. if image_paths else TEXT_REQUEST_TIMEOUT
    seconds=max(.1,min(float(timeout) if timeout is not None else maximum,maximum))
    response,body=_transport(payload,key,streaming,seconds)
    if not isinstance(body,dict):
        raise llm.LLMError('apiforcode_request_uncertain: APIforcode trả dữ liệu sai cấu trúc; không tự gửi lại.')
    if response.status_code>=500:
        raise llm.LLMError('apiforcode_request_uncertain: Máy chủ APIforcode lỗi; chưa rõ đã trừ lượt, không tự gửi lại.')
    if not response.ok:
        detail=re.sub(r'sk-[A-Za-z0-9_-]+','[key]',str(body.get('error',''))).replace(key,'[key]')[:350]
        if response.status_code==402 or any(t in detail.lower() for t in ('insufficient_quota','quota_exhausted','余额不足','额度不足')):
            raise llm.LLMError('api_request_exhausted: APIforcode báo hết lượt/số dư. Kiểm tra gói tại api.apiforcode.com/check; không tự đổi dịch vụ.')
        if 300<=response.status_code<400:
            raise llm.LLMError('apiforcode_request_uncertain: APIforcode yêu cầu chuyển địa chỉ; app không gửi key sang địa chỉ khác.')
        raise RuntimeError(f'APIforcode Error code: {response.status_code} - {detail}')
    choices=body.get('choices') or []
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):
        raise llm.LLMError('apiforcode_request_uncertain: APIforcode không trả kết quả lựa chọn; không tự gửi lại.')
    choice=choices[0];message=choice.get('message') or {};finish=choice.get('finish_reason','')
    if not isinstance(message,dict):
        raise llm.LLMError('apiforcode_request_uncertain: APIforcode trả lời sai cấu trúc; không tự gửi lại.')
    if finish=='content_filter' or message.get('refusal'):
        raise llm.LLMContentBlocked('finish_reason=content_filter',provider='APIforcode')
    text=message.get('content')
    if not isinstance(text,str) or not text.strip():
        raise llm.LLMError('apiforcode_request_uncertain: APIforcode trả nội dung rỗng; chưa chấp nhận kết quả hoặc tự gửi lại.')
    if finish not in ('stop','length'):
        raise llm.LLMError('apiforcode_request_uncertain: APIforcode chưa kết thúc câu trả lời hợp lệ.')
    return text,finish,body.get('usage') or {}
