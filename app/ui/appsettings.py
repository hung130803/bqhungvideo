"""Một CỬA DUY NHẤT để lấy QSettings của app.

Vì sao có file này: QSettings("AIContentStudio","studio") ghi vào REGISTRY
Windows dùng chung với bản app THẬT đang chạy trên máy. Test nào set giá trị
vào đó là làm bẩn cài đặt của user — và nếu test chết giữa đường (timeout,
crash) thì KHÔNG kịp trả lại.

CHUYỆN ĐÃ XẢY RA (2026-07-26): test smoke toàn app bị timeout ở nút mở hộp
chọn file, nên `pipe_root` và `pipe_recycle_dir` của anh Hùng bị bỏ lại trỏ vào
`%TEMP%\\app_smoke_xxx\\...`. May là chốt `_is_safe_recycle_root` từ chối mọi
đường dẫn trong Temp nên KHÔNG mất video nào, nhưng cột "Chờ cắt" hiện lệch và
hộp Thùng rác chỉ sai đường.

Cách chặn tận gốc: đặt env `BQ_QSETTINGS_INI` trỏ tới 1 file .ini thì TOÀN BỘ
app đọc/ghi vào file đó, KHÔNG chạm registry. Test chỉ cần set env này ở đầu
file là vĩnh viễn không thể làm bẩn cài đặt thật — dù có chết giữa đường.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import QSettings

ORG = "AIContentStudio"
APP = "studio"

#: env để chuyển hướng cài đặt sang 1 file .ini (dùng cho TEST).
ENV_INI = "BQ_QSETTINGS_INI"


def app_settings() -> QSettings:
    """QSettings của app. Mặc định = registry thật; có BQ_QSETTINGS_INI thì
    đọc/ghi vào file .ini đó (test dùng, không đụng cài đặt user)."""
    ini = (os.environ.get(ENV_INI) or "").strip()
    if ini:
        return QSettings(ini, QSettings.Format.IniFormat)
    return QSettings(ORG, APP)


def dung_file_ini() -> bool:
    """True nếu đang chạy với cài đặt trong file .ini (tức đang trong test)."""
    return bool((os.environ.get(ENV_INI) or "").strip())
