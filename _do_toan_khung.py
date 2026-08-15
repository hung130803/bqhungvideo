# -*- coding: utf-8 -*-
"""ĐO bộ dò chữ cháy khi QUÉT CẢ KHUNG (không chỉ dải đáy).

Anh Hùng 15/08/2026: *"làm mờ chữ nó tự nhận diện trên khung hình không được
à, phải khớp 100%, không lệch không nhanh"*.

GỐC RỄ ĐÃ XÁC ĐỊNH: `do_dai_chu` có `y_min = int(h * vung_day)` với
VUNG_DAY=0,55 -> bộ dò CHỈ NHÌN phần dưới khung. Chữ ở TRÊN/GÓC thì nó không
NHÌN THẤY (khác hẳn "nhìn nhầm").

CÁC LỆNH (`python -u _do_toan_khung.py <lệnh>`):
  quet   — quét kho video, tìm nguồn CÓ chữ ngoài dải đáy (để làm bộ đối chứng)
  vung   — in bản đồ mật độ nét theo HÀNG của một video (xem chữ nằm đâu)
  do     — bỏ sót / che oan: bản DẢI ĐÁY (cũ) vs bản TOÀN KHUNG (mới)
  moc    — ĐỘ LỆCH THỜI GIAN: chữ hiện/tắt thật vs mặt che bật/tắt (mili-giây)
  gia    — GIÁ: giây/phút phim với 1 vùng vs nhiều vùng

LUẬT (VIỆC 0 — chống lặp lại sự cố đầy ổ 15/08):
  · MỌI subprocess ffmpeg có `timeout=` và `-t`/`-frames:v` chặn độ dài ĐẦU RA.
  · `-t` là tuỳ chọn ĐẦU VÀO, áp cho đầu vào khai SAU nó — script này không
    dùng `lavfi` sinh vô hạn, mọi nguồn đều là FILE có độ dài hữu hạn.
  · Hộp cát mang PID, tự dọn bằng `atexit` + quét hộp cũ lúc khởi động
    (chép khuôn `_test_thay_giong.py`).
  · KHÔNG đụng video gốc trong `Downloads\\longtieng` và `Downloads\\Video`.
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import numpy as np                                             # noqa: E402

from app.core import che_chu as C                              # noqa: E402

_TIEN_TO = "cc_toankhung_"
FF_HAN = 900          # trần cho mọi lượt ffmpeg (giây)


def _con_song(pid: int) -> bool:
    try:
        import psutil
    except ImportError:
        return True
    try:
        return psutil.pid_exists(pid)
    except Exception:                                          # noqa: BLE001
        return True


def _don_hop_cu() -> tuple:
    goc = Path(tempfile.gettempdir())
    n, byte = 0, 0
    try:
        ds = list(goc.glob(_TIEN_TO + "*"))
    except OSError:
        return (0, 0.0)
    for d in ds:
        try:
            if not d.is_dir():
                continue
            phan = d.name[len(_TIEN_TO):].split("_")[0]
            if phan.isdigit() and (int(phan) == os.getpid()
                                   or _con_song(int(phan))):
                continue
            byte += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d, ignore_errors=True)
            n += 1
        except OSError:
            continue
    return (n, byte / 1073741824.0)


_cu_n, _cu_gb = _don_hop_cu()
if _cu_n:
    print(f"  dọn {_cu_n} hộp cát {_TIEN_TO}* của lượt TRƯỚC ({_cu_gb:.2f} GB)")

T = Path(tempfile.mkdtemp(prefix=f"{_TIEN_TO}{os.getpid()}_"))


def _don(*_a) -> None:
    shutil.rmtree(T, ignore_errors=True)


def _bi_giet(_s=None, _f=None) -> None:
    _don()
    try:
        sys.stdout.flush()
    except Exception:                                          # noqa: BLE001
        pass
    os._exit(2)


atexit.register(_don)
for _ten in ("SIGTERM", "SIGBREAK", "SIGINT"):
    _s = getattr(signal, _ten, None)
    if _s is not None:
        try:
            signal.signal(_s, _bi_giet)
        except (ValueError, OSError):
            pass

#: Chỗ giữ ảnh/clip để NGƯỜI TỰ NHÌN — KHÔNG nằm trong %TEMP% (phải xem được
#: sau khi script thoát). Tự dọn ở đầu mỗi lượt.
NHIN = Path(os.environ.get("BQ_CC_NHIN", r"D:\claude\_che_toan_khung"))
V = Path(r"C:\Users\Admin\Downloads\Video")
LT = Path(r"C:\Users\Admin\Downloads\longtieng")
NGUON = Path(r"D:\claude\_do_che_chu\nguon")


def _ff(args: list, han: int = FF_HAN) -> subprocess.CompletedProcess:
    """ffmpeg/ffprobe với TRẦN THỜI GIAN bắt buộc."""
    return subprocess.run(args, capture_output=True, timeout=han,
                          stdin=subprocess.DEVNULL,
                          creationflags=C._CREATE_NO_WINDOW)


# ══════════════════════ đọc khung DÀY, CẢ KHUNG ═════════════════════════════
def doc_ca_khung(src, fps: float = 2.0, rong: int = 320,
                 bat_dau: float = 0.0, dai: float = 0.0) -> tuple:
    """MỘT lượt giải mã -> (mảng khung xám (N,h,w), w, h).

    `rong` nhỏ hơn RONG_DO=640 vì nay phải giữ CẢ KHUNG trong RAM chứ không
    chỉ dải đáy: 640x1138x N khung ở fps=2 cho video 10 phút = 875 MB.
    320 px vẫn đủ cho top-hat 9x9 bắt nét chữ (đo ở `quet`).
    """
    tt = C.thong_tin(src)
    if not tt["rong"] or not tt["cao"]:
        return None, 0, 0
    w = rong + (rong % 2)
    h = int(round(tt["cao"] * w / tt["rong"]))
    h += h % 2
    cmd = [C._bin("ffmpeg"), "-v", "error"]
    if bat_dau > 0:
        cmd += ["-ss", f"{bat_dau:.3f}"]
    cmd += ["-i", str(src)]
    if dai > 0:
        cmd += ["-t", f"{dai:.3f}"]
    cmd += ["-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo",
            "-pix_fmt", "gray", "-"]
    try:
        r = _ff(cmd)
    except subprocess.TimeoutExpired:
        return None, 0, 0
    n = len(r.stdout) // (w * h)
    if n < 3:
        return None, 0, 0
    return (np.frombuffer(r.stdout[:n * w * h], np.uint8).reshape(n, h, w),
            w, h)


def muc_na(arr: np.ndarray) -> np.ndarray:
    """(N,h,w) xám -> (N,h,w) mặt nạ nét, ĐÃ trừ phần HẰNG + GIAO THỜI GIAN."""
    mns = np.stack([C._mat_na(g) for g in arr])
    n = mns.shape[0]
    const = (mns.sum(axis=0) >= C.TY_LE_HANG * n).astype(np.uint8)
    doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)
    return C._loc_thoi_gian(doi)


# ══════════════════════════ LỆNH: quet ══════════════════════════════════════
def _kho() -> list:
    ds = []
    for p in sorted(LT.glob("*.mp4")):
        ds.append(("longtieng", p))
    for p in sorted(NGUON.glob("*.mp4")):
        ds.append(("nguon", p))
    for d in sorted([x for x in V.iterdir() if x.is_dir()]) if V.is_dir() else []:
        fs = sorted(d.glob("*.mp4"))[:3]
        for p in fs:
            ds.append((d.name, p))
    return ds


def lenh_quet(gioi_han: int = 60) -> None:
    """Tìm video CÓ chữ NGOÀI dải đáy (nguyên liệu cho bộ đối chứng)."""
    print("\n=== QUÉT KHO: chữ nằm ĐÂU trong khung? ===")
    print("  cột = mật độ nét (đã trừ HẰNG + giao thời gian) theo 5 tầng khung")
    print(f"  {'nhóm':14s} {'video':38s} {'trên':>7s} {'t-giữa':>7s} "
          f"{'giữa':>7s} {'d-giữa':>7s} {'đáy':>7s}")
    ds = _kho()[:gioi_han]
    ket = []
    for nhom, p in ds:
        try:
            arr, w, h = doc_ca_khung(p, fps=1.0, rong=256, bat_dau=3.0,
                                     dai=40.0)
        except Exception as e:                                 # noqa: BLE001
            print(f"  {nhom:14s} {p.name[:38]:38s} LỖI {e}")
            continue
        if arr is None:
            continue
        gia = muc_na(arr)
        prof = gia.mean(axis=(0, 2))                # (h,) mật độ theo hàng
        tang = [float(prof[int(h * a):int(h * b)].max())
                for a, b in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.))]
        ngoai_day = max(tang[:3])                   # trên VUNG_DAY=0,55
        ket.append((ngoai_day, nhom, p, tang))
        print(f"  {nhom[:14]:14s} {p.name[:38]:38s} " +
              " ".join(f"{x:7.4f}" for x in tang))
    ket.sort(reverse=True)
    print("\n  --- 8 video ĐẬM NHẤT ở phần TRÊN (ứng viên chữ ngoài đáy) ---")
    for v, nhom, p, tang in ket[:8]:
        print(f"  {v:.4f}  {nhom}/{p.name[:60]}")


# ══════════════════════════ LỆNH: vung ══════════════════════════════════════
def lenh_vung(duong: str, fps: float = 2.0) -> None:
    """In bản đồ mật độ nét theo HÀNG + trích khung ra PNG để tự nhìn."""
    p = Path(duong)
    print(f"\n=== BẢN ĐỒ HÀNG: {p.name} ===")
    arr, w, h = doc_ca_khung(p, fps=fps, rong=320)
    if arr is None:
        print("  không đọc được")
        return
    gia = muc_na(arr)
    prof = gia.mean(axis=(0, 2))
    print(f"  {arr.shape[0]} khung, {w}x{h}, mốc VUNG_DAY={C.VUNG_DAY} "
          f"= hàng {int(h*C.VUNG_DAY)}")
    for i in range(0, h, max(1, h // 48)):
        v = float(prof[i])
        cot = "#" * int(v * 400)
        cua = "  <-- MỐC VUNG_DAY" if abs(i - int(h * C.VUNG_DAY)) < h // 96 \
            else ""
        print(f"  hàng {i:4d} ({i/h*100:5.1f}%) {v:.4f} {cot}{cua}")


def _main() -> int:
    lenh = sys.argv[1] if len(sys.argv) > 1 else "quet"
    if lenh == "quet":
        lenh_quet(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    elif lenh == "vung":
        lenh_vung(sys.argv[2])
    else:
        print(f"lệnh lạ: {lenh}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_main())
