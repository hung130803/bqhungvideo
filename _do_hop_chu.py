# -*- coding: utf-8 -*-
"""ĐO: che theo DẢI NGANG vs che theo HỘP CHỮ — giảm bao nhiêu %, SÓT bao nhiêu?

Anh Hùng 14/08/2026: *"sao phần text hiện trong video nó không xác định rồi
che mờ ĐÚNG VỊ TRÍ chữ xuất hiện thôi không được à"*.

Script CHỈ ĐO, không sửa gì. Bốn con số cần lấy:
  1. diện tích che của DẢI hiện tại (`do_dai_chu`) / diện tích khung
  2. diện tích che của HỘP CỐ ĐỊNH khít và HỘP THEO ĐOẠN THỜI GIAN
  3. **SÓT** — khung nào chữ nhô RA NGOÀI hộp (ca nguy hiểm nhất). Đo trên tập
     **GIỮ RIÊNG**: đọc dày 2 khung/giây rồi chia CHẴN (dựng hộp) / LẺ (chấm).
     Dựng và chấm trên cùng một tập là tự cấp chứng nhận.
  4. giá lấy mẫu (xem `_do_gia_lay_mau.py`: 1 lượt giải mã `fps=1` = 0,62-0,83
     s/phút phim, RẺ HƠN 48 lượt `-ss` mà dày gấp 7)

Chạy: .venv\\Scripts\\python _do_hop_chu.py
"""
from __future__ import annotations

import os

import sys
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
_SB = Path(r"D:\claude\_do_che_chu\_sandbox")
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                              # noqa: BLE001
    pass

import numpy as np                            # noqa: E402
from app.core import che_chu as C             # noqa: E402

KHO = Path(r"D:\claude\_do_che_chu\nguon")


def doc_day(src: Path, fps: float, y0: int, y1: int, rong: int = C.RONG_DO):
    """MỘT lượt giải mã: `fps=k` + `crop` đúng dải hàng -> (ảnh, w, h, t[]).

    `crop` SAU `scale` để toạ độ khớp hệ 640px của `che_chu`. Cắt sớm giúp
    giảm hẳn lượng byte phải chuyển qua ống (dải chỉ ~7% chiều cao khung).
    """
    tt = C.thong_tin(src)
    if not tt["rong"]:
        return None, 0, 0, []
    w = rong if rong % 2 == 0 else rong + 1
    h = int(round(tt["cao"] * w / tt["rong"]))
    h += h % 2
    ty = h / float(tt["cao"])
    a = max(0, int(y0 * ty) - 12)
    b = min(h, int(y1 * ty) + 12)
    b = max(a + 2, b)
    ch = b - a
    cmd = [C._bin("ffmpeg"), "-v", "error", "-i", str(src), "-vf",
           f"fps={fps},scale={w}:{h},crop={w}:{ch}:0:{a}", "-f", "rawvideo",
           "-pix_fmt", "gray", "-"]
    r = C._chay(cmd, timeout=1800)
    n = len(r.stdout) // (w * ch)
    if n < 4:
        return None, 0, 0, []
    arr = np.frombuffer(r.stdout[:n * w * ch], np.uint8).reshape(n, ch, w)
    return arr, w, a, [(i + 0.5) / fps for i in range(n)]


def mat_na_lo(arr: np.ndarray) -> np.ndarray:
    """Mặt nạ nét chữ cho CẢ CHỒNG khung (top-hat từng khung)."""
    return np.stack([C._mat_na(g) for g in arr])


def _moc_ra(prof: np.ndarray, i0: int, ng: float, khe: int,
            lo: int, hi: int) -> tuple:
    a = b = i0
    i, hut = i0, 0
    while i + 1 < hi:
        i += 1
        if prof[i] >= ng:
            b, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    i, hut = i0, 0
    while i - 1 >= lo:
        i -= 1
        if prof[i] >= ng:
            a, hut = i, 0
        else:
            hut += 1
            if hut > khe:
                break
    return a, b + 1


def be_ngang(m: np.ndarray, r0: int, r1: int, w: int, ty_cot: float = 0.25,
             khe: int = 0, md_min: float = C.NGUONG_HANG) -> tuple | None:
    """[x0,x1) của chữ trong MỘT khung. None = khung này KHÔNG có chữ.

    Cửa `md_min` là thứ tách "khung không có phụ đề" khỏi "khung có" — thiếu nó
    thì khung trống vẫn đẻ ra một hộp bám vào vân nền (đo: hộp rộng 24 px ở
    chỗ hoàn toàn không có chữ), rồi hộp đó kéo HỢP cả video rộng ra.
    """
    sub = m[r0:r1]
    if sub.size == 0 or float(sub.mean()) < md_min:
        return None
    cot = sub.sum(axis=0).astype(np.float32)
    if cot.max() <= 0:
        return None
    cs = np.convolve(cot, np.ones(3, np.float32) / 3.0, mode="same")
    dinh = int(np.argmax(cs))
    return _moc_ra(cs, dinh, max(1.0, ty_cot * float(cs[dinh])),
                   khe or max(2, (r1 - r0)), 0, w)


def _hop(bs) -> tuple:
    return min(b[0] for b in bs), max(b[1] for b in bs)


def do_mot(ten: str, fps: float = 2.0, dem: int = 4) -> dict | None:
    p = KHO / ten
    if not p.exists():
        return None
    t0 = time.perf_counter()
    d = C.do_dai_chu(p, so_khung=16)
    t_dai = time.perf_counter() - t0
    tt = C.thong_tin(p)
    W, H, DUR = tt["rong"], tt["cao"], tt["do_dai"]
    print(f"\n=== {ten}  {W}x{H} · {DUR:.0f}s")
    if not d.co_chu:
        print(f"    KHÔNG chữ ({d.ly_do})")
        return {"ten": ten, "co_chu": False}
    print(f"    DẢI hiện tại: y={d.y0}..{d.y1} x={d.x0}..{d.x1} "
          f"· dò {t_dai:.2f}s")

    t0 = time.perf_counter()
    arr, w, off, moc = doc_day(p, fps, d.y0, d.y1)
    t_day = time.perf_counter() - t0
    if arr is None:
        print("    không đọc dày được")
        return None
    n = arr.shape[0]
    print(f"    đọc dày {n} khung ({fps} khung/giây) trong {t_day:.2f}s "
          f"= {t_day/(DUR/60):.2f} s/phút phim")

    mns = mat_na_lo(arr)
    const = (mns.sum(axis=0) >= C.TY_LE_HANG * n).astype(np.uint8)
    doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)
    tyv = w / float(W)
    r0 = int(d.y0 * tyv) - off
    r1 = int(d.y1 * tyv) - off
    r0, r1 = max(0, r0), min(arr.shape[1], max(r0 + 2, r1))

    hs = [be_ngang(doi[i], r0, r1, w) for i in range(n)]
    co_chu_i = [i for i, x in enumerate(hs) if x]
    if len(co_chu_i) < 8:
        print(f"    chỉ {len(co_chu_i)} khung có chữ — bỏ")
        return None
    ty_co = len(co_chu_i) / n

    chan = [i for i in co_chu_i if i % 2 == 0]      # DỰNG hộp
    le = [i for i in co_chu_i if i % 2 == 1]        # CHẤM (giữ riêng)

    cao = (d.y1 - d.y0)
    dt_dai = cao * (d.x1 - d.x0) / float(W * H)
    ra = {"ten": ten, "co_chu": True, "dt_dai": dt_dai, "n": n,
          "ty_co": ty_co, "t_dai": t_dai, "t_day": t_day, "DUR": DUR,
          "W": W, "H": H}

    print(f"    diện tích che / khung hình (che CẢ CLIP)   "
          f"[DẢI {dt_dai*100:.3f}% · x rộng {(d.x1-d.x0)/W*100:.1f}%]")
    print("      chiến lược       đệm    diện tích  giảm   sót/lẻ   "
          "nhô ra tối đa")

    def _cham(ten_cl, khoang, dem_px):
        """khoang = [(i, j, (x0,x1)|None)] -> in một dòng. dem_px: đệm (px 640)."""
        tong = sot = 0.0
        nho = 0
        for (i, j, hp) in khoang:
            if hp is None:
                continue
            a, b = max(0, hp[0] - dem_px), min(w, hp[1] + dem_px)
            tong += cao * ((b - a) / tyv) / float(W * H) * (j - i) / n
            for k in le:
                if i <= k < j and (hs[k][0] < a or hs[k][1] > b):
                    sot += 1
                    nho = max(nho, a - hs[k][0], hs[k][1] - b)
        print(f"      {ten_cl:15s} {dem_px:3d}px {tong*100:8.3f}%  "
              f"{(1-tong/dt_dai)*100:5.1f}%  {int(sot):3d}/{len(le):3d}   "
              f"{nho/tyv:5.1f}px nguồn")
        return tong, int(sot), nho / tyv

    # ---- HỘP CỐ ĐỊNH (hợp cả video, dựng từ tập CHẴN) ----
    fx0, fx1 = _hop([hs[i] for i in chan])
    for dem in (0, dem_px_mac := 8):
        t_, s_, nh_ = _cham("HỘP cố định", [(0, n, (fx0, fx1))], dem)
        if dem == dem_px_mac:
            ra["dt_hop"], ra["sot_hop"], ra["nho_hop"] = t_, s_, nh_

    # ---- HỘP THEO ĐOẠN THỜI GIAN ----
    for D in (4.0, 8.0, 16.0):
        b_dai = max(1, int(round(D * fps)))
        khoang = []
        i = 0
        while i < n:
            j = min(n, i + b_dai)
            # HỢP các khung CHẴN trong [i,j) + ĐỆM 1 bậc mỗi phía (dòng phụ đề
            # nằm vắt qua mép đoạn thì mẫu của nó rơi vào đoạn BÊN CẠNH)
            cc = [hs[k] for k in chan if i - 1 <= k < j + 1 and hs[k]]
            khoang.append((i, j, _hop(cc) if cc else None))
            i = j
        for dem in (0, 8, 24):
            t_, s_, nh_ = _cham(f"HỘP {D:.0f}s/đoạn", khoang, dem)
            if dem == 8:
                ra[f"dt_D{int(D)}"] = t_
                ra[f"sot_D{int(D)}"] = s_
                ra[f"nho_D{int(D)}"] = nh_

    # ---- trần lý thuyết: che TỪNG khung ----
    tr = float(np.mean([cao * ((x[1] - x[0]) / tyv) / float(W * H)
                        for x in hs if x])) * ty_co
    ra["dt_tran"] = tr
    print(f"      (trần: che từng khung {tr*100:7.3f}%  giảm "
          f"{(1-tr/dt_dai)*100:5.1f}%)")
    print(f"      khung CÓ chữ: {ty_co*100:.1f}%  "
          f"(che cả clip là che thừa {100-ty_co*100:.1f}% thời lượng)")
    return ra


def main():
    bo = ["zh_ep12.mp4", "zh_dongho.mp4", "en_d5.mp4", "en_bus.mp4"]
    bo += sorted(x.name for x in KHO.glob("dy*.mp4"))
    kq = [do_mot(t) for t in bo]
    kq = [k for k in kq if k and k.get("co_chu")]
    if not kq:
        return
    print("\n──────── TỔNG ────────")
    for cot in ("dt_hop", "dt_D4", "dt_D8", "dt_D16", "dt_tran"):
        g = [(1 - k[cot] / k["dt_dai"]) * 100 for k in kq]
        s = sum(k.get("sot_" + cot.split("_")[1], 0) for k in kq)
        print(f"  {cot:8s} giảm TB {sum(g)/len(g):5.1f}% "
              f"(thấp nhất {min(g):5.1f}%) · tổng SÓT {s}")


if __name__ == "__main__":
    main()
