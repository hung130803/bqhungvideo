"""Per-key, per-service observations shared by UI and analysis processes.

Each record has its own atomic file, so independent workers cannot overwrite
another key's state. Raw keys are never written. A legacy whole-pool block
does not identify a failing key and is deliberately not used here.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid

SCOPES = ('chat', 'transcription', 'vision')


def _path(provider: str, key: str, scope: str):
    from config import DATA_DIR
    if scope not in SCOPES:
        raise ValueError('Unknown API service')
    identity = hashlib.sha256((provider + '\0' + key).encode()).hexdigest()
    return DATA_DIR / 'key_health' / (identity + '.' + scope + '.json')


def read(provider: str, key: str, scope: str) -> dict:
    try:
        result = json.loads(_path(provider, key, scope).read_text(encoding='utf-8'))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def record(provider: str, key: str, scope: str, state: str, note: str = '') -> None:
    path = _path(provider, key, scope)
    clean = str(note).replace(key, '[key]') if key else str(note)
    clean = re.sub(r'gsk_[A-Za-z0-9_-]+', '[key]', clean)[:350]
    value = {'state': state, 'checked_at': time.time(), 'note': clean}
    previous = read(provider, key, scope)
    if previous.get('state') in ('restricted', 'invalid') and state not in ('ok', 'restricted', 'invalid'):
        # A timeout during an explicit recheck is not evidence that access
        # has been restored. Only success of this key/service clears denial.
        value['state'] = previous['state']
    temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        temporary.replace(path)
    except OSError:
        # Read-only disk must not turn a completed API request into a failure.
        pass
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def blocked(provider: str, key: str, scope: str) -> bool:
    return read(provider, key, scope).get('state') in ('restricted', 'invalid')
