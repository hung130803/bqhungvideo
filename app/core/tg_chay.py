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

import hashlib
import os
from pathlib import Path
from typing import Optional

from app.core import tg_so
from app.core.thay_giong import TEN_THU_MUC_TAM


def khoa_chong_trung(video: str | Path, dich_sang: str, voice: str,
                     thu_muc_ra: str | Path, che_chu: bool = False,
                     che_chu_cach: str = "mo", che_chu_muc: float = 1.0) -> str:
    """`dedup_key` của job.

    Gồm CẢ THƯ MỤC ĐÍCH: đổi thư mục đích rồi bấm Chạy lại là một việc KHÁC,
    không được nuốt vào job cũ (bài học cổng 56e — cờ không vào hash chống
    trùng thì bấm lại chẳng job nào chạy mà không một dòng báo).

    **CỜ CHE CHỮ NỐI VÀO ĐUÔI, CHỈ KHI THẬT SỰ BẬT** — y hệt cách
    `services.enqueue_export` làm (cổng 56e): nối vô điều kiện là đổi khoá của
    MỌI job cũ đang nằm trong DB. Mức mờ đi qua `chuan_muc_mo` TRƯỚC khi băm
    vì 0,30 và 0,50 đều bị SÀN 0,60 kéo về cùng một chỗ — băm giá trị THÔ là
    đẻ job chạy lại cho một thay đổi KHÔNG TỒN TẠI.
    """
    d = os.path.abspath(str(video)).lower()
    r = os.path.abspath(str(thu_muc_ra)).lower()
    sig = f"thaygiong:{d}:{dich_sang}:{voice}:{r}"
    if che_chu:
        from app.core.che_chu import chuan_cach, chuan_muc_mo
        sig += f":cc={chuan_cach(che_chu_cach)}:{chuan_muc_mo(che_chu_muc):.2f}"
    return sig


#: Số ký tự tên video giữ lại làm TIỀN TỐ thư mục tạm — chỉ để người mở thư
#: mục ra còn đoán được nó của video nào. Phần bảo đảm KHÔNG TRÙNG là mã băm.
TEN_TAM_TOI_DA = 16


def ten_tam_cho(video: str | Path) -> str:
    """Tên thư mục tạm NGẮN nhưng KHÔNG BAO GIỜ TRÙNG: `<16 ký tự đầu>_<băm8>`.

    **VÌ SAO KHÔNG DÙNG THẲNG TÊN VIDEO** (bản cũ làm thế): video reup tiếng
    Trung tên tới 60 ký tự, mà mọi file trung gian đều nằm dưới thư mục này và
    ĐI VÀO DÒNG LỆNH ffmpeg — đo được 127 ký tự cho MỖI đường dẫn wav, nhân
    278 câu là 47.794 ký tự dòng lệnh (`WinError 206`). Cắt tên ở đây rút mỗi
    đường dẫn xuống ~92 ký tự, và kéo đường dài nhất của cả lượt từ **183 về
    ~120 ký tự** — chỗ dư tới trần `MAX_PATH` 260 tăng gấp đôi, nên anh Hùng
    đặt thư mục đích sâu vài cấp (`D:\\Kênh\\<tên kênh>\\xuất`) vẫn không vỡ.

    **BẮT BUỘC LÀ BĂM, KHÔNG ĐƯỢC CẮT CỤT KHÔNG.** Hai video reup thường trùng
    nhau rất dài ở đầu tên (`（完整）…`, `上集，…`) — cắt 16 ký tự đầu là hai
    video khác nhau ra CÙNG một thư mục tạm, hai lượt chạy song song ghi đè
    `goc.wav`/`khop_0000.wav` của nhau và cả hai ra video hỏng mà không một
    dòng báo. Băm theo ĐƯỜNG DẪN ĐẦY ĐỦ (không phải riêng tên) để hai video
    trùng tên ở hai thư mục nguồn khác nhau cũng tách được.
    """
    duong = os.path.normcase(os.path.abspath(str(video)))
    ma = hashlib.sha1(duong.encode("utf-8", "surrogatepass")).hexdigest()[:8]
    # bỏ ký tự Windows cấm + khoảng trắng/dấu chấm ở đuôi (Windows tự cắt đuôi
    # đó rồi báo "không thấy thư mục" ở lượt sau)
    tho = Path(str(video)).stem[:TEN_TAM_TOI_DA]
    sach = "".join("_" if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in tho)
    return f"{sach.rstrip(' .')}_{ma}" if sach.rstrip(' .') else ma


def thu_muc_lam_cho(video: str | Path, thu_muc_ra: str | Path) -> str:
    """Thư mục làm việc tạm — ĐẶT TRONG THƯ MỤC ĐÍCH, không đặt cạnh video gốc.

    Anh Hùng đòi "thư mục nguồn không được đụng tới": file wav/mp3 của một
    video 10 phút lên hàng trăm MB, đổ vào thư mục nguồn là bẩn đúng chỗ anh
    ấy dặn đừng đụng. (Vẫn KHÔNG dùng %TEMP% — bị dọn định kỳ giữa chừng.)

    Tên thư mục do `ten_tam_cho` đặt: NGẮN + băm, xem lý do ở đó.
    """
    return str(Path(thu_muc_ra) / TEN_THU_MUC_TAM / ten_tam_cho(video))


def can_chay(video: str | Path, lam_lai: bool = False) -> bool:
    """Video này có phải chạy trong lượt bấm Chạy không.

    `lam_lai=True` (chuột phải -> Làm lại video này) thì LUÔN chạy.
    """
    return True if lam_lai else tg_so.can_chay(video)


def xep_mot(pool, video: str | Path, dich_sang: str, voice: str = "",
            thu_muc_ra: str | Path = "", kenh: str = "",
            lam_lai: bool = False, che_chu: bool = False,
            che_chu_cach: str = "mo", che_chu_muc: float = 1.0,
            ) -> Optional[int]:
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
    tt = {"video": v, "dich_sang": dich_sang, "voice": voice,
          "cach_tach": "auto", "thay_goc": False, "kenh": kenh,
          "thung_rac": "", "thu_muc_ra": ra,
          "thu_muc_lam": thu_muc_lam_cho(v, ra)}
    if che_chu:
        # CHỈ ghi khoá khi BẬT: payload không mang khoá = job cũ/lối gọi chưa
        # nối vẫn chạy y như trước (`jobs._thay_giong` đọc bằng `.get`).
        tt["che_chu"] = True
        tt["che_chu_cach"] = che_chu_cach
        tt["che_chu_muc"] = che_chu_muc
    return pool.enqueue(
        "thay_giong", tt,
        needs_gpu=False, priority=5,
        dedup_key=khoa_chong_trung(v, dich_sang, voice, ra, che_chu,
                                   che_chu_cach, che_chu_muc),
        skip_if_done=False, max_attempts=1,
    )
