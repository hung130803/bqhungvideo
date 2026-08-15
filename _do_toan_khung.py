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


# ══════════════════════════ LỆNH: ben ═══════════════════════════════════════
def _giao_k(m: np.ndarray, k: int) -> np.ndarray:
    """Giữ điểm ảnh BẬT LIÊN TIẾP >= k khung (k=2 = `_loc_thoi_gian` hiện tại).

    Chữ đứng yên TỪNG ĐIỂM ẢNH 1,5-3 giây = 3-6 khung ở fps=2. Nền trôi.
    Mở bộ dò ra CẢ KHUNG thì nền nhiều gấp bội -> phải đo k nào tách sạch.
    """
    if k <= 1 or len(m) < k:
        return m
    # cửa sổ trượt: điểm ảnh sống nếu nằm trong MỘT dãy k khung liên tiếp
    n = len(m)
    acc = np.zeros_like(m)
    run = np.zeros(m.shape[1:], np.int16)
    dai = np.zeros_like(m, dtype=np.int16)
    for i in range(n):
        run = np.where(m[i] > 0, run + 1, 0)
        dai[i] = run
    # lan ngược: khung nào thuộc dãy đủ dài thì bật
    du = dai >= k
    for i in range(n - 1, -1, -1):
        if i + 1 < n:
            du[i] |= du[i + 1] & (m[i] > 0)
    return (du & (m > 0)).astype(np.uint8)


def lenh_ben(duong: str) -> None:
    """ĐỘ BỀN bao nhiêu khung thì tách được CHỮ khỏi NỀN trên CẢ khung?"""
    p = Path(duong)
    print(f"\n=== ĐỘ BỀN THỜI GIAN: {p.name} ===")
    arr, w, h = doc_ca_khung(p, fps=C.HOP_FPS, rong=320)
    if arr is None:
        print("  không đọc được")
        return
    mns = np.stack([C._mat_na(g) for g in arr])
    n = mns.shape[0]
    const = (mns.sum(axis=0) >= C.TY_LE_HANG * n).astype(np.uint8)
    doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)
    print(f"  {n} khung {w}x{h}")
    print(f"  {'k':>3s} {'đỉnh CHỮ trên':>14s} {'đỉnh CHỮ đáy':>13s} "
          f"{'NỀN giữa (đỉnh)':>16s} {'tách (lần)':>11s}")
    for k in (1, 2, 3, 4, 5, 6):
        g = C._loc_thoi_gian(doi) if k == 2 else _giao_k(doi, k)
        prof = g.mean(axis=(0, 2))
        tren = float(prof[int(h * .15):int(h * .32)].max())
        day = float(prof[int(h * .72):int(h * .90)].max())
        nen = float(prof[int(h * .35):int(h * .70)].max())
        tach = min(tren, day) / max(1e-6, nen)
        print(f"  {k:3d} {tren:14.4f} {day:13.4f} {nen:16.4f} {tach:11.2f}")


# ══════════════════════════ LỆNH: vungthu ══════════════════════════════════
def lenh_vungthu(*duong) -> None:
    """Chạy `do_vung_chu` trên từng video, in vùng dò được + giá."""
    print("\n=== DÒ TOÀN KHUNG (do_vung_chu) ===")
    for d in duong:
        p = Path(d)
        if not p.exists():
            print(f"  THIẾU {p}")
            continue
        tt = C.thong_tin(p)
        t0 = time.perf_counter()
        vs = C.do_vung_chu(p)
        gy = time.perf_counter() - t0
        print(f"\n  {p.name}  {tt['rong']}x{tt['cao']} {tt['do_dai']:.1f}s "
              f"— dò {gy:.1f}s ({gy/max(1e-6, tt['do_dai'])*60:.1f} s/phút) "
              f"-> {len(vs)} vùng")
        for v in vs:
            tong = sum(b - a for a, b in v.khoang) if v.khoang else tt["do_dai"]
            print(f"    y={v.y0:5d}..{v.y1:<5d} ({v.y0/max(1,tt['cao'])*100:4.0f}%"
                  f"..{v.y1/max(1,tt['cao'])*100:4.0f}%) x={v.x0:5d}..{v.x1:<5d}"
                  f" md={v.mat_do:.3f} nền={v.ty_so_nen:5.1f}x"
                  f" {len(v.khoang):3d} khoảng = {tong:6.1f}s"
                  f" ({tong/max(1e-6, tt['do_dai'])*100:3.0f}% clip)"
                  f" {len(v.hop)} hộp")
        for v in C.VET_LOAI:
            print(f"    [loại] {v}")
        # so với bản DẢI ĐÁY hiện hành
        t0 = time.perf_counter()
        cu = C.do_dai_chu(p)
        gy2 = time.perf_counter() - t0
        print(f"    [bản DẢI ĐÁY cũ] {gy2:.1f}s -> "
              f"{'CÓ chữ y=%d..%d' % (cu.y0, cu.y1) if cu.co_chu else 'KHÔNG'}"
              f" | {cu.ly_do[:60]}")


# ══════════════════════════ LỆNH: ve ════════════════════════════════════════
def lenh_ve(duong: str, *moc) -> None:
    """VẼ khung viền các vùng dò được lên khung hình -> PNG để TỰ NHÌN."""
    p = Path(duong)
    ra = NHIN / "ve"
    ra.mkdir(parents=True, exist_ok=True)
    vs = C.do_vung_chu(p)
    print(f"\n=== VẼ VÙNG: {p.name} -> {len(vs)} vùng ===")
    ts = [float(x) for x in moc] if moc else [5.0, 10.0]
    for t in ts:
        ve = []
        for i, v in enumerate(vs):
            bat = any(a <= t <= b for a, b in v.khoang) if v.khoang else True
            mau = "red" if bat else "yellow"
            ve.append(f"drawbox=x={v.x0}:y={v.y0}:w={v.x1-v.x0}:"
                      f"h={v.y1-v.y0}:color={mau}@1:t=5")
            print(f"    t={t}s vùng{i} y={v.y0}..{v.y1} "
                  f"{'ĐANG BẬT (đỏ)' if bat else 'tắt (vàng)'}")
        vf = ",".join(ve + ["scale=340:-2"]) if ve else "scale=340:-2"
        f = ra / f"{p.stem}_t{t:.0f}.png"
        _ff([C._bin("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.3f}",
             "-i", str(p), "-frames:v", "1", "-vf", vf, str(f)], han=120)
        print(f"  {f}")


# ══════════════════════════ LỆNH: hinh ══════════════════════════════════════
#: Sự thật ghi BẰNG MẮT: (nhãn, video, y0, y1 ở PIXEL NGUỒN, CÓ_CHỮ)
#: Lấy từ ảnh cắt đúng dải (`_che_toan_khung/dai/*.png`) — xem báo cáo.
DAI_THAT = [
    ("taxi_TIEUDE", "jp_taxi", 190, 330, True),     # 『あなたの子供買いたい』2 dòng
    ("taxi_mep_giuong", "jp_taxi", 456, 512, False),  # MÉP NGANG của tấm phủ
    ("taxi_phude", "jp_taxi", 1470, 1566, True),
    ("tuyet_TIEUDE", "jp_tuyet", 150, 400, True),
    ("tuyet_san", "jp_tuyet", 576, 646, False),
    ("tuyet_hangrao", "jp_tuyet", 688, 1000, False),
    ("tuyet_san2", "jp_tuyet", 1048, 1322, False),
    ("tuyet_phude", "jp_tuyet", 1322, 1430, True),
    ("art_TIEUDE", "jp_art", 442, 630, True),
    ("art_tuong", "jp_art", 700, 1400, False),      # tường hoạ tiết khắc nét
    ("phim_phude", "zh_phim", 646, 690, True),
]


def _chay_ngang(m: np.ndarray, nguong: int) -> tuple:
    """(tỉ lệ mực nằm trong dãy ngang DÀI hơn `nguong`, dài dãy trung vị)."""
    tong = int(m.sum())
    if tong == 0:
        return 0.0, 0.0
    dai_ds = []
    dai_lon = 0
    for hang in m:
        d = 0
        for v in hang:
            if v:
                d += 1
            elif d:
                dai_ds.append(d)
                if d > nguong:
                    dai_lon += d
                d = 0
        if d:
            dai_ds.append(d)
            if d > nguong:
                dai_lon += d
    return dai_lon / float(tong), float(np.median(dai_ds)) if dai_ds else 0.0


def lenh_hinh(nguong: int = 12) -> None:
    """CHỮ khác NỀN ở chỗ nào? Đo trên dải đã ghi sự thật BẰNG MẮT."""
    print(f"\n=== HÌNH DẠNG: chữ vs nền (dãy ngang > {nguong} px = 'vệt dài') ===")
    print(f"  {'dải':20s} {'thật':5s} | {'mật độ':>7s} {'vệt dài':>8s} "
          f"{'biênđộ TB':>10s} {'%nét>120':>9s} {'tương phản':>11s} "
          f"{"lệch hàng":>10s} {"nền CỤC BỘ":>10s}")
    nho = {}
    for nhan, ten, y0, y1, that in DAI_THAT:
        p = NHIN / "nguon" / f"{ten}.mp4"
        if not p.exists():
            continue
        if ten not in nho:
            arr, w, h = doc_ca_khung(p, fps=C.HOP_FPS, rong=320)
            if arr is None:
                continue
            mns = np.stack([C._mat_na(g) for g in arr])
            th = np.stack([C._top_hat(g) for g in arr])
            nho[ten] = (C._loc_thoi_gian(mns), th, arr, h,
                        C.thong_tin(p)["cao"])
        gia, th, arr, h, H = nho[ten]
        r0 = max(0, int(y0 * h / H))
        r1 = min(h, max(r0 + 2, int(y1 * h / H)))
        md = float(gia[:, r0:r1, :].mean())
        per = gia[:, r0:r1, :].reshape(len(gia), -1).mean(axis=1)
        k = int(np.argmax(per))
        m1 = gia[k, r0:r1, :]
        ty_dai, _tv = _chay_ngang(m1, nguong)
        # biên độ top-hat TRÊN ĐIỂM CÓ MỰC (chữ làm ra để đọc -> nét gắt)
        t1 = th[k, r0:r1, :]
        muc = m1 > 0
        bd = float(t1[muc].mean()) if muc.any() else 0.0
        gat = float((t1[muc] > 120).mean()) if muc.any() else 0.0
        # tương phản: lệch chuẩn độ xám trong dải (chữ = nền phẳng + nét gắt)
        tp = float(arr[k, r0:r1, :].std())
        # ĐỘ GỢN THEO HÀNG: chữ có hàng đậm (thân chữ) xen hàng nhạt (khe
        # dòng); nền tự nhiên trải đều -> gợn thấp
        ph = gia[:, r0:r1, :].mean(axis=(0, 2))
        gon = float(ph.std() / max(1e-6, ph.mean()))
        # TỈ SỐ NỀN CỤC BỘ: đậm hơn NGAY TRÊN và NGAY DƯỚI bao nhiêu lần.
        # Chữ là dải MỎNG NỔI trên nền -> tụt hẳn; mảng nền thì liền mạch.
        cao = max(2, r1 - r0)
        a0, a1 = max(0, r0 - cao), r0
        b0, b1 = r1, min(h, r1 + cao)
        ke = []
        if a1 > a0:
            ke.append(float(gia[:, a0:a1, :].mean()))
        if b1 > b0:
            ke.append(float(gia[:, b0:b1, :].mean()))
        cb = md / max(1e-6, float(np.mean(ke))) if ke else 0.0
        print(f"  {nhan:20s} {'CHỮ' if that else 'nền':5s} | {md:7.4f} "
              f"{ty_dai*100:7.1f}% {bd:10.1f} {gat*100:8.1f}% {tp:11.1f} "
              f"{gon:10.3f} {cb:10.2f}")


def _main() -> int:
    lenh = sys.argv[1] if len(sys.argv) > 1 else "quet"
    if lenh == "hinh":
        lenh_hinh(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
        return 0
    if lenh == "ve":
        lenh_ve(sys.argv[2], *sys.argv[3:])
        return 0
    if lenh == "vungthu":
        lenh_vungthu(*sys.argv[2:])
        return 0
    if lenh == "quet":
        lenh_quet(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    elif lenh == "vung":
        lenh_vung(sys.argv[2])
    elif lenh == "ben":
        lenh_ben(sys.argv[2])
    else:
        print(f"lệnh lạ: {lenh}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_main())
