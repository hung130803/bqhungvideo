"""Explicit connection check: chat success is not proof of speech access."""
from __future__ import annotations

import io
import wave

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


def check(provider: str, whisper_provider: str) -> list[dict]:
    """Check exactly one configured key for each service; no failover on denial.

    This is an explicit recheck. Only success of that same key/service clears
    its restriction; checking chat never clears a failed transcription.
    """
    rows = []
    scopes = [(provider, 'chat', 'AI chat')]
    if whisper_provider == 'groq':
        scopes.append(('groq', 'transcription', 'Whisper chép lời'))
    for service_provider, scope, label in scopes:
        keys = settings.llm_keys_for(service_provider)
        if not keys:
            rows.append({'ok': False, 'message': label + ': chưa có key.'})
            continue
        key = keys[0]
        masked = llm.che_key(key)
        try:
            llm.mark_used(service_provider, key)
            if scope == 'transcription':
                _speech(key)
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
            if llm.is_org_restricted(text):
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
