"""Windows user-bound encrypted credentials; never store in presets/jobs."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def crypt(raw, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Kho key cần Windows trên tài khoản đã lưu key.')
    buf = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    fn = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise RuntimeError('Không mở được kho key trên tài khoản Windows này.')
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(result.data)


def path():
    from config import DATA_DIR
    return Path(DATA_DIR) / '_credentials' / 'twelvelabs.keys.dpapi.json'


def load():
    p = path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding='utf-8-sig'))
        return [crypt(bytes.fromhex(x), True).decode('utf-16-le') for x in data['keys']]
    except (ValueError, KeyError, UnicodeError) as exc:
        raise RuntimeError('Kho key TwelveLabs chưa đọc được; nhập lại trong cài đặt.') from exc


def save(keys):
    values = list(dict.fromkeys(k.strip() for k in keys if k.strip()))
    if any(not k.startswith('tlk_') or any(c.isspace() for c in k) for k in values):
        raise ValueError('Key TwelveLabs cần bắt đầu bằng tlk_ và không có khoảng trắng.')
    p = path(); p.parent.mkdir(parents=True, exist_ok=True)
    data = {'version': 1, 'protection': 'Windows DPAPI CurrentUser',
            'keys': [crypt(k.encode('utf-16-le')).hex() for k in values]}
    temp = p.with_suffix('.tmp')
    temp.write_text(json.dumps(data), encoding='utf-8')
    temp.replace(p)
