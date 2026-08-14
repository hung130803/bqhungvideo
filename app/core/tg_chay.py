# -*- coding: utf-8 -*-
"""XẾP JOB THAY GIỌNG — luật "chạy video nào" nằm ở ĐÂY, không nằm trong UI.

Vì sao tách khỏi UI: cổng test phải gọi thẳng được luật này (bảng tiến độ chỉ
là cái hiện ra), và hai đường vào (bấm Chạy · chuột phải Làm lại) phải đi CHUNG
một cửa — hai bên tự quyết là lệch nhau, đúng bài học cổng 19 (mẫu-theo-kênh
chỉ áp ở dây chuyền, bấm tay vẫn ăn cấu hình cũ).

Job đi qua LÀN RIÊNG `worker.LAN_TG` (mỗi video một job) — xem
`app/queue/jobs.py:_thay_giong` cho phần chạy thật.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.core import tg_so
from app.core.thay_giong import TEN_THU_MUC_TAM


def khoa_chong_trung(video: str | Path, dich_sang: str, voice: str,
                     thu_muc_ra: str | Path) -> str:
    """`dedup_key` của job.

    Gồm CẢ THƯ MỤC ĐÍCH: đổi thư mục đích rồi bấm Chạy lại là một việc KHÁC,
    không được nuốt vào job cũ (bài học cổng 56e — cờ không vào hash chống
    trùng thì bấm lại chẳng job nào chạy mà không một dòng báo).
    """
    d = os.path.abspath(str(video)).lower()
    r = os.path.abspath(str(thu_muc_ra)).lower()
    return f"thaygiong:{d}:{dich_sang}:{voice}:{r}"


def thu_muc_lam_cho(video: str | Path, thu_muc_ra: str | Path) -> str:
    """Thư mục làm việc tạm — ĐẶT TRONG THƯ MỤC ĐÍCH, không đặt cạnh video gốc.

    Anh Hùng đòi "thư mục nguồn không được đụng tới": file wav/mp3 của một
    video 10 phút lên hàng trăm MB, đổ vào thư mục nguồn là bẩn đúng chỗ anh
    ấy dặn đừng đụng. (Vẫn KHÔNG dùng %TEMP% — bị dọn định kỳ giữa chừng.)
    """
    return str(Path(thu_muc_ra) / TEN_THU_MUC_TAM / Path(str(video)).stem)


def can_chay(video: str | Path, lam_lai: bool = False) -> bool:
    """Video này có phải chạy trong lượt bấm Chạy không.

    `lam_lai=True` (chuột phải -> Làm lại video này) thì LUÔN chạy.
    """
    return True if lam_lai else tg_so.can_chay(video)


def xep_mot(pool, video: str | Path, dich_sang: str, voice: str = "",
            thu_muc_ra: str | Path = "", kenh: str = "",
            lam_lai: bool = False) -> Optional[int]:
    """Xếp job cho MỘT video. Trả job id, hoặc None nếu BỎ QUA/không có pool.

    `lam_lai=True` xoá mục trong sổ TRƯỚC khi xếp — nếu không thì job chạy
    xong ghi lại "xong" trong khi mục cũ vẫn ở đó, và lượt sau vẫn thấy dòng
    "đã xong" của lần trước.
    """
    v = os.path.abspath(str(video))
    ra = str(thu_muc_ra or "").strip() or tg_so.thu_muc_dich_mac_dinh(
        os.path.dirname(v))
    if tg_so.trung_thu_muc(os.path.dirname(v), ra):
        raise ValueError("Thư mục đích TRÙNG thư mục nguồn")
    if lam_lai:
        tg_so.xoa(v)
    elif not tg_so.can_chay(v):
        return None
    if pool is None:
        return None
    os.makedirs(ra, exist_ok=True)
    return pool.enqueue(
        "thay_giong",
        {"video": v, "dich_sang": dich_sang, "voice": voice,
         "cach_tach": "auto", "thay_goc": False, "kenh": kenh,
         "thung_rac": "", "thu_muc_ra": ra,
         "thu_muc_lam": thu_muc_lam_cho(v, ra)},
        needs_gpu=False, priority=5,
        dedup_key=khoa_chong_trung(v, dich_sang, voice, ra),
        skip_if_done=False, max_attempts=1,
    )
