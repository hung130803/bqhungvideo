"""Cấu hình máy chủ tài khoản (Supabase). anon key là loại CÔNG KHAI, an toàn
để kèm trong app (mọi bảo vệ nằm ở RLS + hàm SECURITY DEFINER phía Supabase).

Thứ tự ưu tiên đọc: QSettings (admin nhập trong app) > biến môi trường > giá trị
"nướng sẵn" bên dưới (điền sau khi tạo project để máy team khỏi phải nhập)."""
from __future__ import annotations

import os

# Điền sau khi tạo project Supabase (để team khỏi nhập tay). VD:
_BAKED_URL = ""   # https://xxxxxxxx.supabase.co
_BAKED_KEY = ""   # anon public key (eyJ...)

_ORG, _APP = "AIContentStudio", "studio"


def _qs():
    from PyQt6.QtCore import QSettings
    return QSettings(_ORG, _APP)


def supabase_url() -> str:
    v = (_qs().value("sb_url", "") or os.getenv("SUPABASE_URL", "") or _BAKED_URL)
    return str(v).strip().rstrip("/")


def supabase_key() -> str:
    v = (_qs().value("sb_key", "") or os.getenv("SUPABASE_ANON_KEY", "") or _BAKED_KEY)
    return str(v).strip()


def set_config(url: str, key: str) -> None:
    s = _qs()
    s.setValue("sb_url", (url or "").strip().rstrip("/"))
    s.setValue("sb_key", (key or "").strip())


def is_configured() -> bool:
    return bool(supabase_url() and supabase_key())
