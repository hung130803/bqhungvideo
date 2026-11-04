"""CỬA CHỜ ĐỌC ĐĨA — CHUNG CHO MỌI TIẾN TRÌNH của app.

VÌ SAO CÓ (đo trên máy anh Hùng 31/10/2026): ổ D: là ổ cứng CƠ (WD10EZEX), mọi
video gốc nằm trên đó. Pha phân tích đọc TRỌN mỗi video gốc 3 lần (tách tiếng,
đo mức âm, đo chuyển động), mà:
  * tách tiếng chạy trong tiến trình con `--analyze` — mỗi tiến trình có CỬA
    CHỜ ffmpeg RIÊNG (`ffmpeg_utils._GATE_COND` là biến trong bộ nhớ), nên 7 làn
    AI = 7 cửa, tổng số lệnh không ai chặn;
  * đo mức âm + chuyển động gọi `subprocess.run` THẲNG, không qua cửa nào.
Đo được lúc anh kêu đơ: 8 lệnh ffmpeg của app + 4 lệnh ghép của BQHungDown cùng
đọc file GB trên ổ D:, hàng đợi đĩa 14-19, mỗi lần đọc chờ ~138 ms; một video
1,6 GB tách tiếng 17 phút mới dùng 5,9 giây CPU (toàn bộ thời gian là chờ đĩa).
Ổ quay mà bị nhiều luồng đọc tuần tự song song thì đầu đọc nhảy qua lại liên
tục -> TỔNG tốc độ tụt, ai cũng chậm.

CÁCH LÀM: N "chỗ" là N file khoá trong DATA_DIR, giữ bằng `msvcrt.locking`.
Khoá file do HỆ ĐIỀU HÀNH giữ theo tiến trình -> tiến trình chết (kể cả bị Huỷ,
bị giết, app thoát bằng os._exit) thì chỗ TỰ NHẢ, không bao giờ kẹt chết.
Chỉ áp cho ổ QUAY (hỏi Windows "có seek penalty không"); ổ SSD/không xác định
được -> KHÔNG chặn gì, hành vi y hệt trước.
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from typing import Callable, Optional

_CACHE_QUAY: dict = {}


def _so_cho() -> int:
    ep = os.environ.get("BQ_DOC_DIA_SLOTS", "").strip()
    if ep:
        try:
            return max(1, min(16, int(ep)))
        except ValueError:
            pass
    return SO_CHO_MAC_DINH


#: Số lệnh được đọc TRỌN video gốc cùng lúc trên MỘT ổ quay (mọi tiến trình
#: cộng lại). Số chọn theo phép đo `do_doc_song_song.py` — xem CLAUDE.md.
SO_CHO_MAC_DINH = 2


def _o_dia(path: str) -> str:
    d = os.path.splitdrive(os.path.abspath(path))[0]
    return d.upper().rstrip("\\") if d else ""


def o_quay(path: str) -> Optional[bool]:
    """True = ổ chứa `path` là ổ CƠ (có seek penalty) · False = SSD ·
    None = không biết (ổ mạng, lỗi, không phải Windows)."""
    o = _o_dia(path)
    if not o or len(o) != 2 or o[1] != ":":
        return None
    if o in _CACHE_QUAY:
        return _CACHE_QUAY[o]
    kq = _hoi_windows(o)
    _CACHE_QUAY[o] = kq
    return kq


def _hoi_windows(o: str) -> Optional[bool]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateFileW.restype = wintypes.HANDLE
        k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.HANDLE]
        k32.DeviceIoControl.restype = wintypes.BOOL
        k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        h = k32.CreateFileW(f"\\\\.\\{o}", 0, 3, None, 3, 0, None)  # truy cập 0: không cần admin
        if not h or h == wintypes.HANDLE(-1).value:
            return None
        try:
            # STORAGE_PROPERTY_QUERY{PropertyId=7 (SeekPenalty), QueryType=0}
            q = (ctypes.c_ulong * 3)(7, 0, 0)
            out = (ctypes.c_ulong * 3)()   # DEVICE_SEEK_PENALTY_DESCRIPTOR
            n = wintypes.DWORD(0)
            ok = k32.DeviceIoControl(h, 0x002D1400, ctypes.byref(q), ctypes.sizeof(q),
                                     ctypes.byref(out), ctypes.sizeof(out),
                                     ctypes.byref(n), None)
            if not ok or n.value < 9:
                return None
            return bool(ctypes.cast(ctypes.byref(out), ctypes.POINTER(ctypes.c_ubyte))[8])
        finally:
            k32.CloseHandle(h)
    except Exception:  # noqa: BLE001 - không biết thì KHÔNG chặn
        return None


def _thu_muc_khoa() -> str:
    try:
        from config import DATA_DIR
        base = str(DATA_DIR)
    except Exception:  # noqa: BLE001
        base = os.environ.get("BQ_DATA_DIR") or os.path.join(
            os.environ.get("LOCALAPPDATA", "."), "BQHungVideo")
    d = os.path.join(base, "_cua_doc_dia")
    os.makedirs(d, exist_ok=True)
    return d


def _thu_giu(f: str):
    """Thử giữ chỗ `f` NGAY (không chờ). Trả fd đang giữ, hoặc None."""
    import msvcrt
    try:
        fd = os.open(f, os.O_RDWR | os.O_CREAT, 0o666)
    except OSError:
        return None
    try:
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return fd
    except OSError:
        os.close(fd)
        return None


def _nha(fd) -> None:
    import msvcrt
    try:
        os.lseek(fd, 0, 0)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


def _kiem_huy_mac_dinh() -> None:
    try:
        from app.core.ffmpeg_utils import _raise_if_job_canceled
        _raise_if_job_canceled()
    except ImportError:
        pass


@contextmanager
def giu_cho(path: str, bao: Optional[Callable[[str], None]] = None,
            kiem_huy: Optional[Callable[[], None]] = None, nhip: float = 0.25):
    """Giữ 1 chỗ đọc trên ổ chứa `path` trong suốt khối `with`.

    Ổ không quay / không xác định được / không phải Windows -> vào thẳng.
    `bao(msg)` được gọi ~1 lần/giây khi đang đợi (để thanh tiến trình nói
    "đang đợi lượt đọc ổ D:" thay vì đứng im). `kiem_huy()` ném lỗi khi user
    bấm Huỷ -> rời hàng ngay."""
    if sys.platform != "win32" or o_quay(path) is not True:
        yield
        return
    try:
        d = _thu_muc_khoa()
    except OSError:
        yield
        return
    o = _o_dia(path)[0]
    n = _so_cho()
    files = [os.path.join(d, f"{o}_{i}.lock") for i in range(n)]
    huy = kiem_huy or _kiem_huy_mac_dinh
    fd = None
    bat_dau = time.monotonic()
    lan_bao = 0.0
    while fd is None:
        for f in files:
            fd = _thu_giu(f)
            if fd is not None:
                break
        if fd is not None:
            break
        huy()
        now = time.monotonic()
        if bao and now - lan_bao >= 1.0:
            lan_bao = now
            try:
                bao(f"đang đợi lượt đọc ổ {o}: (ổ cứng cơ, {n} việc đang đọc) · "
                    f"{int(now - bat_dau)} giây")
            except Exception as e:  # noqa: BLE001 - Huỷ phải nổi lên
                if type(e).__name__ == "CanceledError":
                    raise
        time.sleep(nhip)
    try:
        yield
    finally:
        _nha(fd)
