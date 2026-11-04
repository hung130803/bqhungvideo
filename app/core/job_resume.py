"""Durable completed-call checkpoints, isolated by job and source revision.

Never serializes credentials, prompts or executable Python objects. A response
is replayed at most once per matching occurrence in a new run. Calls which have
not returned cannot be resumed inside a remote provider.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import hashlib
import inspect
import json
import threading
from pathlib import Path

_scope = ContextVar('job_resume_scope', default=None)
_nested = ContextVar('job_resume_nested', default=False)


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def file_stamp(path):
    p = Path(path)
    try:
        s = p.stat()
        return [str(p.resolve()), s.st_size, s.st_mtime_ns]
    except OSError:
        return [str(p), 'missing']


@contextmanager
def scope(job_id, payload, check=None):
    from app.database import db
    row = db.query_one('SELECT id, type, video_id, created_at FROM jobs WHERE id=?', (job_id,))
    if not row:
        yield
        return
    vid = payload.get('video_id') or row['video_id']
    source = db.query_one('SELECT src_path FROM videos WHERE id=?', (vid,)) if vid else None
    stamp = file_stamp(source['src_path']) if source else None
    state = {'job': int(job_id), 'identity': digest([1, dict(row), payload, stamp]),
             'counts': {}, 'lock': threading.Lock(), 'check': check}
    token = _scope.set(state)
    try:
        yield
    finally:
        _scope.reset(token)


def _read(state, key):
    from app.database import db
    row = db.query_one('SELECT data, checksum FROM job_checkpoints WHERE job_id=? AND scope=? AND step=?',
                       (state['job'], state['identity'], key))
    if not row:
        return None
    try:
        value = json.loads(row['data'])
        return value if digest(value) == row['checksum'] else None
    except (ValueError, TypeError):
        return None


def _save(state, key, value):
    from app.database import db
    data = json.dumps(value, ensure_ascii=False, allow_nan=False)
    db.execute('INSERT INTO job_checkpoints(job_id,scope,step,data,checksum) VALUES(?,?,?,?,?) '
               'ON CONFLICT(job_id,scope,step) DO UPDATE SET data=excluded.data,checksum=excluded.checksum',
               (state['job'], state['identity'], key, data, digest(value)))


def local_step(name, inputs, run):
    """Pure JSON-valued work; no checkpoint for a failed or empty measurement."""
    state = _scope.get()
    if state is None:
        return run()
    if state['check']:
        state['check']()
    key = 'local:' + digest([name, inputs])
    old = _read(state, key)
    if old is not None:
        return old['value']
    value = run()
    if value:
        _save(state, key, {'value': value})
    return value


def random_for(name, inputs):
    import random
    state = _scope.get()
    if state is None:
        return random
    key = 'random:' + digest([name, inputs])
    with state['lock']:
        index = state['counts'].get(key, 0)
        state['counts'][key] = index + 1
    return random.Random(digest([state['identity'], key, index]))


def remember_generation(con, name, inputs, result):
    state = _scope.get()
    if state is None:
        return
    value = {'value': result}
    con.execute('INSERT INTO job_checkpoints(job_id,scope,step,data,checksum) VALUES(?,?,?,?,?) '
                'ON CONFLICT(job_id,scope,step) DO UPDATE SET data=excluded.data,checksum=excluded.checksum',
                (state['job'], state['identity'], 'generation:' + digest([name, inputs]),
                 json.dumps(value, ensure_ascii=False), digest(value)))


def bind_context(fn):
    """One copied context per submitted task; never share a Context concurrently."""
    from contextvars import copy_context
    context = copy_context()
    return lambda *a, **kw: context.run(fn, *a, **kw)


def content_stamp(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def generation_result(name, inputs):
    state = _scope.get()
    if state is None:
        return None
    key = 'generation:' + digest([name, inputs])
    old = _read(state, key)
    if old is None:
        return None
    from app.database import db
    ids = old['value'].get('clip_ids', [])
    if all(db.query_one("SELECT id FROM clips WHERE id=? AND status<>'archived'", (cid,)) for cid in ids):
        return old['value']
    return None


def publish_highlights(video_id, rows, result, inputs):
    """Publish an entire selection and its resume receipt in ONE transaction."""
    from app.database import db
    state = _scope.get()
    con = db.conn()
    con.execute('BEGIN IMMEDIATE')
    try:
        keep = set()
        for j in con.execute("SELECT payload FROM jobs WHERE type='m1_export_clip' AND status IN ('pending','running') AND video_id=?", (video_id,)):
            try:
                keep.add(int(json.loads(j['payload']).get('clip_id')))
            except (ValueError, TypeError, AttributeError):
                pass
        existing = con.execute("SELECT id,status FROM clips WHERE video_id=?", (video_id,)).fetchall()
        for c in existing:
            if c['id'] in keep:
                continue
            if c['status'] == 'suggested':
                con.execute('DELETE FROM clips WHERE id=?', (c['id'],))
            elif c['status'] in ('exported', 'done'):
                con.execute("UPDATE clips SET status='archived' WHERE id=?", (c['id'],))
        ids = []
        for params in rows:
            cur = con.execute("INSERT INTO clips(video_id,start_sec,end_sec,score,reason,title,transcript,signals,status) VALUES(?,?,?,?,?,?,?,?, 'suggested')", params)
            ids.append(cur.lastrowid)
        result = dict(result, clip_ids=ids, count=len(ids))
        if state is not None:
            value = {'value': result}
            con.execute('INSERT INTO job_checkpoints(job_id,scope,step,data,checksum) VALUES(?,?,?,?,?) '
                        'ON CONFLICT(job_id,scope,step) DO UPDATE SET data=excluded.data,checksum=excluded.checksum',
                        (state['job'], state['identity'], 'generation:' + digest(['highlights', inputs]),
                         json.dumps(value, ensure_ascii=False), digest(value)))
        con.commit()
        return result
    except BaseException:
        con.rollback()
        raise


def completed_ai_call(fn):
    """Replay completed top-level calls only; parsing/validation still runs."""
    signature = inspect.signature(fn)

    @wraps(fn)
    def wrapped(*args, **kwargs):
        state = _scope.get()
        if state is None or _nested.get():
            return fn(*args, **kwargs)
        if state['check']:
            state['check']()
        from app.ai import llm
        from config import settings
        values = dict(signature.bind(*args, **kwargs).arguments)
        # Image filenames are temporary; hash image bytes, not their location.
        if 'image_paths' in values:
            values['image_paths'] = [hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                     for p in values['image_paths']]
        models = {k: getattr(settings, k) for k in dir(settings)
                  if 'MODEL' in k and 'KEY' not in k and isinstance(getattr(settings, k), (str, int, float, bool))}
        provider = values.get('provider') or llm.active_provider()
        key = digest([fn.__name__, values, provider, models])
        with state['lock']:
            index = state['counts'].get(key, 0)
            state['counts'][key] = index + 1
        key = f'ai:{key}:{index}'
        old = _read(state, key)
        if old is not None:
            llm._LAN.ket_thuc = old.get('finish', '')
            llm._LAN.chan_doan = old.get('diagnostic', {})
            return old['value']
        token = _nested.set(True)
        try:
            value = fn(*args, **kwargs)
        finally:
            _nested.reset(token)
        _save(state, key, {'value': value, 'finish': llm.ly_do_ket_thuc(),
                           'diagnostic': llm.chan_doan_lan()})
        return value
    return wrapped
