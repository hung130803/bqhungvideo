"""Kiểm tra bản cập nhật từ GitHub Releases (nhẹ, best-effort, không chặn app).

Cách hoạt động: gọi API releases/latest của kho, so tag (vd v1.0.2) với
__version__ hiện tại. Mới hơn -> trả thông tin để UI hiện hộp thoại cập nhật
(kèm URL file .zip để TỰ TẢI + TỰ CÀI — xem app/core/self_update.py).
Lỗi mạng / chưa có release -> trả None (im lặng, không phiền người dùng).
"""
from __future__ import annotations

import json
import urllib.request

from app.version import __version__, GITHUB_OWNER, GITHUB_REPO


def _parse(v: str) -> tuple:
    out = []
    for x in (v or "").lstrip("vV").split("."):
        try:
            out.append(int(x))
        except ValueError:
            break
    return tuple(out)


def check_latest(timeout: int = 6):
    """Trả dict thông tin bản mới nếu CÓ, ngược lại None.

    dict: {tag, page, asset_url, asset_size, notes}
      - asset_url/asset_size: file .zip của Release (để tự tải); có thể rỗng
        nếu Release không đính kèm zip -> UI fallback mở trang tải.
    """
    if GITHUB_OWNER.startswith("PLACEHOLDER"):
        return None                       # chưa cấu hình kho -> bỏ qua
    url = (f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
           "/releases/latest")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-content-studio-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    tag = data.get("tag_name") or ""
    page = (data.get("html_url")
            or f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases")
    if not tag or _parse(tag) <= _parse(__version__):
        return None
    asset_url, asset_size = "", 0
    for a in data.get("assets") or []:
        name = (a.get("name") or "").lower()
        if name.endswith(".zip") and a.get("browser_download_url"):
            asset_url = a["browser_download_url"]
            asset_size = int(a.get("size") or 0)
            break
    return {"tag": tag, "page": page, "asset_url": asset_url,
            "asset_size": asset_size, "notes": (data.get("body") or "").strip()}
