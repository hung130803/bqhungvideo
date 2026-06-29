"""Đăng nhập + quản lý tài khoản qua Supabase (RPC).

Mật khẩu KHÔNG bao giờ gửi/lưu dạng thường ở client: app gọi hàm RPC trên
Supabase, hàm tự băm/so khớp (bcrypt qua pgcrypto). App chỉ giữ anon key
(công khai). Mọi thao tác admin đều phải kèm tài khoản admin để máy chủ kiểm.
"""
from __future__ import annotations

from app.auth_config import is_configured, supabase_key, supabase_url


class AuthError(Exception):
    pass


def _rpc(fn: str, payload: dict, timeout: int = 20):
    if not is_configured():
        raise AuthError("Chưa cấu hình máy chủ tài khoản (Supabase). "
                        "Bấm 'Cấu hình máy chủ' để nhập.")
    import requests
    url, key = supabase_url(), supabase_key()
    try:
        r = requests.post(
            f"{url}/rest/v1/rpc/{fn}",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise AuthError(f"Không kết nối được máy chủ (mạng?). {str(e)[:120]}")
    if r.status_code >= 400:
        raise AuthError(f"Máy chủ báo lỗi ({r.status_code}). "
                        "Kiểm tra lại cấu hình/SQL.")
    try:
        return r.json()
    except ValueError:
        return None


def login(username: str, password: str):
    """Trả {'username','role'} nếu đúng + tài khoản đang mở; None nếu sai."""
    rows = _rpc("app_login", {"p_username": username, "p_password": password})
    if isinstance(rows, list) and rows:
        return {"username": rows[0]["username"], "role": rows[0]["role"]}
    return None


def admin_list_users(admin: str, admin_pass: str) -> list:
    rows = _rpc("app_admin_list_users",
                {"p_admin": admin, "p_admin_pass": admin_pass})
    return rows if isinstance(rows, list) else []


def admin_upsert_user(admin: str, admin_pass: str, username: str,
                      password: str, role: str = "user") -> str:
    """Tạo mới HOẶC đặt lại mật khẩu/quyền cho 1 user. Trả 'OK' hoặc 'NOT_ADMIN'."""
    return _rpc("app_admin_upsert_user", {
        "p_admin": admin, "p_admin_pass": admin_pass,
        "p_username": username, "p_password": password, "p_role": role})


def admin_set_active(admin: str, admin_pass: str, username: str,
                     active: bool) -> str:
    return _rpc("app_admin_set_active", {
        "p_admin": admin, "p_admin_pass": admin_pass,
        "p_username": username, "p_active": active})


def admin_delete_user(admin: str, admin_pass: str, username: str) -> str:
    return _rpc("app_admin_delete_user", {
        "p_admin": admin, "p_admin_pass": admin_pass, "p_username": username})
