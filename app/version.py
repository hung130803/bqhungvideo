"""Phiên bản app + thông tin kho GitHub (dùng cho tính năng tự cập nhật).

Mỗi lần phát hành bản mới: tăng __version__ ở đây rồi tạo 1 GitHub Release có
tag trùng (vd v1.0.1). Máy người dùng sẽ thấy thông báo "có bản mới".
"""
from __future__ import annotations

__version__ = "1.7.1"

# Sẽ được điền đúng khi tạo kho trên GitHub (chủ kho / tên kho).
GITHUB_OWNER = "hung130803"
GITHUB_REPO = "bqhungvideo"
