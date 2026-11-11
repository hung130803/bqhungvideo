"""NHƯỜNG NHÂN MẠNH CHO NGƯỜI DÙNG khi họ đang ngồi máy (11/11/2026).

Anh Hùng chạy 5 luồng thì "thao tác gì cũng đơ giật", dù mọi lệnh nặng đã ở
BELOW_NORMAL. Máy là i7-13700F (8 nhân MẠNH = 16 luồng logic + 8 nhân PHỤ) chạy
Windows 10 — bản Windows này không xếp việc khéo trên CPU hai loại nhân, nên ưu
tiên thấp thôi là chưa đủ.

ĐO TRÊN MÁY ANH HÙNG trước khi viết:
  · dừng hẳn ffmpeg 45 s -> CPU 40-75% xuống 18-25% (đương nhiên, không chạy).
  · app VẪN CHẠY nhưng mọi tiến trình con chỉ được dùng 8 nhân PHỤ trong 60 s
    -> nhân mạnh chỉ bận 14-16%, nhân phụ 99-100%, anh Hùng: "k đơ giật".

Nên: anh đang dùng chuột/bàn phím -> mọi tiến trình CON của app (ffmpeg, tiến
trình phân tích, yt-dlp...) bị giới hạn vào nhân PHỤ; rời máy >= `_RANH_GIAY`
giây (cùng ngưỡng với `ffmpeg_utils`) -> trả lại toàn bộ nhân. Lệnh ffmpeg
KHÔNG đổi một tham số nào nên CHẤT LƯỢNG GIỮ NGUYÊN, chỉ chậm hơn lúc anh ngồi
máy. Tiến trình giao diện (chính app) không bị giới hạn -> cửa sổ vẫn nhanh.

Máy KHÔNG có hai loại nhân (máy nhân viên, CPU đời cũ) -> KHÔNG làm gì cả.
Tắt hẳn: BQ_NHUONG_MAY=0. Nhật ký: logs/nhuong_may_<ngày>.log (chỉ khi ĐỔI).
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional

_NHIP = 2.0                 # giây giữa 2 lần xét
_LUONG: Optional[threading.Thread] = None
_CHE_DO_TRUOC: Optional[str] = None


def nhan_phu_va_tat_ca() -> tuple[list[int], list[int]]:
    """(nhân PHỤ, mọi nhân) theo chỉ số logic. CPU chỉ một loại nhân -> ([], tất cả).

    Đọc `EfficiencyClass` qua GetSystemCpuSetInformation: nhân PHỤ có lớp THẤP
    hơn nhân mạnh. Lỗi gì cũng trả ([], ...) = không nhường gì (an toàn)."""
    tat_ca = list(range(os.cpu_count() or 1))
    if os.name != "nt":
        return [], tat_ca
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        can = wintypes.ULONG(0)
        k.GetSystemCpuSetInformation(None, 0, ctypes.byref(can), None, 0)
        if not can.value:
            return [], tat_ca
        buf = (ctypes.c_ubyte * can.value)()
        if not k.GetSystemCpuSetInformation(buf, can, ctypes.byref(can), None, 0):
            return [], tat_ca
        raw = bytes(buf)
        lop: dict[int, int] = {}
        i = 0
        while i + 20 <= len(raw):
            size = int.from_bytes(raw[i:i + 4], "little")
            if size <= 0:
                break
            group = int.from_bytes(raw[i + 12:i + 14], "little")
            if group == 0:  # máy 1 nhóm (<= 64 luồng) — đủ cho máy này
                lop[raw[i + 14]] = raw[i + 18]   # LogicalProcessorIndex -> EfficiencyClass
            i += size
        if not lop or len(set(lop.values())) < 2:
            return [], tat_ca
        thap = min(lop.values())
        phu = sorted(lp for lp, c in lop.items() if c == thap)
        return phu, sorted(lop)
    except Exception:  # noqa: BLE001
        return [], tat_ca


def bat() -> bool:
    return os.environ.get("BQ_NHUONG_MAY", "1").strip() != "0"


def che_do_bay_gio() -> str:
    """'nhuong' (anh đang dùng máy) | 'het_suc' (rời máy / không đọc được ... )."""
    from app.core import ffmpeg_utils as fu
    roi = fu.giay_roi_may()
    # không đọc được giờ rời máy -> NHƯỜNG (máy mượt là mặc định an toàn)
    if roi is None or roi < fu._RANH_GIAY:
        return "nhuong"
    return "het_suc"


def _ghi(che_do: str, so: int, phu: list[int]) -> None:
    try:
        from config import DATA_DIR
        d = Path(DATA_DIR) / "logs"
        d.mkdir(parents=True, exist_ok=True)
        ly_do = (f"anh đang dùng máy -> app chỉ dùng {len(phu)} nhân phụ"
                 if che_do == "nhuong" else "anh rời máy -> app dùng hết nhân")
        with open(d / f"nhuong_may_{time.strftime('%Y%m%d')}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {ly_do} · {so} tiến trình con" + chr(10))
    except Exception:  # noqa: BLE001
        pass


def ap_mot_luot(goc=None, phu=None, tat_ca=None, che_do=None) -> int:
    """Áp mặt nạ nhân cho mọi tiến trình CON của `goc` (mặc định: chính app).
    Trả số tiến trình đã đặt được. Không bao giờ ném lỗi."""
    global _CHE_DO_TRUOC
    try:
        import psutil
        if phu is None or tat_ca is None:
            phu, tat_ca = nhan_phu_va_tat_ca()
        if not phu:
            return 0
        che_do = che_do or che_do_bay_gio()
        mat_na = phu if che_do == "nhuong" else tat_ca
        goc = goc or psutil.Process(os.getpid())
        n = 0
        for ch in goc.children(recursive=True):
            try:
                if sorted(ch.cpu_affinity()) != mat_na:
                    ch.cpu_affinity(mat_na)
                n += 1
            except Exception:  # noqa: BLE001 - tiến trình vừa thoát / không có quyền
                pass
        if che_do != _CHE_DO_TRUOC:
            _CHE_DO_TRUOC = che_do
            _ghi(che_do, n, phu)
        return n
    except Exception:  # noqa: BLE001
        return 0


def _vong() -> None:
    phu, tat_ca = nhan_phu_va_tat_ca()
    if not phu:
        return  # máy một loại nhân -> không có gì để nhường
    while True:
        ap_mot_luot(phu=phu, tat_ca=tat_ca)
        time.sleep(_NHIP)


def khoi_dong() -> bool:
    """Gọi MỘT lần từ tiến trình giao diện. Trả True nếu đã chạy luồng canh."""
    global _LUONG
    if not bat() or _LUONG is not None:
        return False
    _LUONG = threading.Thread(target=_vong, daemon=True, name="nhuong-may")
    _LUONG.start()
    return True
