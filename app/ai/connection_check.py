"""Explicit connection check: chat success is not proof of speech access."""
from __future__ import annotations

import io
import wave
import base64
import struct
import zlib

from config import settings
from app.ai import key_health, llm


def _speech(key: str):
    from openai import OpenAI
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * 16000)
    with OpenAI(api_key=key, base_url='https://api.groq.com/openai/v1',
                timeout=25, max_retries=0) as client:
        client.audio.transcriptions.create(
            file=('connection-check.wav', audio.getvalue(), 'audio/wav'),
            model=settings.GROQ_WHISPER_MODEL, response_format='json')


def _vision(key: str):
    """Explicit access recheck using a generated swatch, never user images."""
    from openai import OpenAI
    # Small fixed RGB PNG made with the standard library. No optional imaging
    # dependency and no access to user files is needed for an access probe.
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    image=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))+
           chunk(b'IDAT',zlib.compress((b'\0'+bytes((220,30,30))*64)*64))+chunk(b'IEND',b''))
    url='data:image/png;base64,'+base64.b64encode(image).decode('ascii')
    with OpenAI(api_key=key,base_url='https://api.groq.com/openai/v1',timeout=25,max_retries=0) as client:
        request=dict(model=llm.groq_vision_model(),max_tokens=200,
            messages=[{'role':'user','content':[{'type':'text','text':'Name the main color of this image in one word.'},
                       {'type':'image_url','image_url':{'url':url}}]}])
        try:response=client.chat.completions.create(reasoning_effort='none',**request)
        except Exception as error:
            if 'reasoning_effort' not in str(error):raise
            request['max_tokens']=900
            response=client.chat.completions.create(**request)
    if not (response.choices[0].message.content or '').strip():
        raise RuntimeError('Model hình ảnh trả về nội dung rỗng.')


def check(provider: str, whisper_provider: str, *, groq_key=None, include_vision=False) -> list[dict]:
    """Check exactly one configured key for each service; no failover on denial.

    This is an explicit recheck. Only success of that same key/service clears
    its restriction; checking chat never clears a failed transcription.
    """
    rows = []
    scopes = [(provider, 'chat', 'AI chat')]
    if whisper_provider == 'groq':
        scopes.append(('groq', 'transcription', 'Whisper chép lời'))
    if include_vision and provider == 'groq':
        scopes.append(('groq','vision','Hình ảnh'))
    for service_provider, scope, label in scopes:
        keys = settings.llm_keys_for(service_provider)
        if not keys:
            rows.append({'ok': False, 'message': label + ': chưa có key.'})
            continue
        key = groq_key if service_provider=='groq' and groq_key is not None else keys[0]
        if key not in keys:
            rows.append({'ok':False,'message':label+': key được chọn không còn trong cấu hình. Chọn lại key.'})
            continue
        masked = llm.che_key(key)
        try:
            llm.mark_used(service_provider, key)
            if scope == 'transcription':
                _speech(key)
            elif scope == 'vision':
                _vision(key)
            else:
                answer = llm._call_once(service_provider, key, 'Trả lời đúng một từ: OK', '', 0.0,
                                        request_timeout=25, retries=0)
                if not answer.strip():
                    raise RuntimeError('Model trả về nội dung rỗng.')
            llm.mark_ok(service_provider, key, scope=scope)
            rows.append({'ok': True, 'message': f'{label}: ĐẠT ({masked}).'})
        except Exception as error:
            text = str(error)
            for secret in keys:
                text = text.replace(secret, '[key]')
            if llm.is_rate_limit_error(text):
                headers=getattr(getattr(error,'response',None),'headers',{}) or {}
                seconds=llm.mark_limited(service_provider,key,text,retry_after=headers.get('retry-after'),scope=scope)
                state='error'
                text=f'429: tạm hết lượt, chờ khoảng {seconds:.0f}s; chưa xác nhận dịch vụ dùng được. Không coi là sai key.'
            elif llm.is_org_restricted(text):
                state = 'restricted'
                text = 'organization_restricted: Groq hạn chế tổ chức của key này; cần kiểm tra tài khoản với Groq.'
            elif llm.is_auth_error(text):
                state = 'invalid'
            else:
                state = 'error'
            key_health.record(service_provider, key, scope, state, text)
            rows.append({'ok': False, 'message': f'{label}: LỖI ({masked}) — {text[:260]}'})
    if whisper_provider != 'groq':
        rows.append({'ok': True, 'message': 'Chép lời local: chưa chạy thử model trên máy.'})
    return rows
