# -*- coding: utf-8 -*-
"""HIỆU CHUẨN HỘP CHỮ — cách LỌC nhiễu · đệm · cố định hay theo đoạn.

VÌ SAO PHẢI CÓ BƯỚC LỌC RIÊNG (đừng chép ngưỡng của bộ dò DẢI): bộ dò DẢI làm
việc trên profile TRUNG BÌNH nhiều khung nên vân nền tự triệt tiêu. Dò BỀ NGANG
thì phải làm trên TỪNG khung — và ở đó **nền cho mực ngang ngửa chữ**. Đã NHÌN
TẬN MẮT trên `zh_dongho` t=7,75s (`_nhin/band_7.75.png`): chữ ở x≈495..790,
nhưng mạn thuyền trắng bên trái và **lan can + thang kim loại bên phải**
(x≈900..1280) cũng là NÉT SÁNG MẢNH — đúng thứ top-hat sinh ra để bắt. Đây là
NỀN THẬT, không phải lỗi bộ dò; nâng ngưỡng nét không cứu được (đo: ngưỡng 150
vẫn nhô sai 256 px).

CÁCH CHỮA ĐO ĐƯỢC — GIAO NHAU THEO THỜI GIAN: một dòng phụ đề đứng YÊN TỪNG
ĐIỂM ẢNH suốt 1,5-3 giây, còn nền thì trôi. Giữ lại điểm ảnh nào CÒN BẬT ở
khung liền trước HOẶC liền sau (cùng tập mẫu, cách 1 giây) thì nền chết, chữ
sống. Đo trên 3 khung hỏng nặng nhất của `zh_dongho`: mực nhiễu bên phải
**186 -> 0**, mực chữ giữ nguyên vị trí.

TẬP DỰNG / TẬP CHẤM TÁCH HẲN: khung CHẴN (t=0,25s · 1,25s · …) dựng hộp; khung
LẺ (t=0,75s · 1,75s · …) chấm. Phép lọc giao-nhau của mỗi tập chỉ dùng hàng xóm
TRONG TẬP ĐÓ — dựng và chấm trên cùng dữ liệu là tự cấp chứng nhận.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
_SB = Path(r"D:\claude\_do_che_chu\_sandbox")
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                              # noqa: BLE001
    pass

import numpy as np                                             # noqa: E402
from app.core import che_chu as C                              # noqa: E402
import _do_hop_chu as M                                        # noqa: E402


def loc_thoi_gian(m: np.ndarray) -> np.ndarray:
    """Giữ điểm ảnh CÒN BẬT ở khung liền trước HOẶC liền sau (cùng tập)."""
    tr = np.zeros_like(m)
    sa = np.zeros_like(m)
    tr[1:] = m[:-1]
    tr[0] = m[1] if len(m) > 1 else m[0]
    sa[:-1] = m[1:]
    sa[-1] = m[-2] if len(m) > 1 else m[-1]
    return (m & (tr | sa)).astype(np.uint8)


def hop_tu(mm: np.ndarray, r0: int, r1: int, w: int, ty: float = 0.20,
           md_min: float = 0.012):
    """[x0,x1) từ MỘT khung đã lọc. None = khung này không có chữ."""
    sub = mm[r0:r1]
    if sub.size == 0 or float(sub.mean()) < md_min:
        return None
    cot = sub.sum(axis=0).astype(np.float32)
    if cot.max() <= 0:
        return None
    cs = np.convolve(cot, np.ones(3, np.float32) / 3.0, mode="same")
    dinh = int(np.argmax(cs))
    return M._moc_ra(cs, dinh, max(1.0, ty * float(cs[dinh])),
                     max(2, r1 - r0), 0, w)


def thu(ten: str, fps: float = 2.0):
    p = M.KHO / ten
    d = C.do_dai_chu(p, so_khung=16)
    if not d.co_chu:
        print(f"\n=== {ten}: KHÔNG chữ — bỏ")
        return None
    tt = C.thong_tin(p)
    W, H = tt["rong"], tt["cao"]
    arr, w, off, moc = M.doc_day(p, fps, d.y0, d.y1)
    n = arr.shape[0]
    tyv = w / float(W)
    r0 = max(0, int(d.y0 * tyv) - off)
    r1 = min(arr.shape[1], max(r0 + 2, int(d.y1 * tyv) - off))
    mns = np.stack([C._mat_na(g) for g in arr])
    const = (mns.sum(axis=0) >= C.TY_LE_HANG * n).astype(np.uint8)
    doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)

    ic = list(range(0, n, 2))
    il = list(range(1, n, 2))
    gc = loc_thoi_gian(doi[ic])         # tập DỰNG, lọc trong tập
    gl = loc_thoi_gian(doi[il])         # tập CHẤM, lọc trong tập
    hc = {ic[k]: hop_tu(gc[k], r0, r1, w) for k in range(len(ic))}
    hl = {il[k]: hop_tu(gl[k], r0, r1, w) for k in range(len(il))}
    co_l = [i for i in il if hl[i]]
    rong_dai = (d.x1 - d.x0) / float(W)
    print(f"\n=== {ten}  {W}x{H} · {n} khung · DẢI rộng {rong_dai*100:.1f}% W "
          f"· khung chấm có chữ {len(co_l)}/{len(il)}")
    print("   chiến lược   đệm   rộng TB   giảm    sót/chấm   nhô tối đa")
    ra = {"ten": ten, "rong_dai": rong_dai}
    for ten_cl, b in (("cố định", n), ("16s/đoạn", int(16 * fps)),
                      ("8s/đoạn", int(8 * fps)), ("4s/đoạn", int(4 * fps))):
        for dem in (0, 10, 20):
            tong = 0.0
            sot = 0
            nho = 0.0
            i = 0
            while i < n:
                j = min(n, i + b)
                cc = [hc[k] for k in range(max(0, i - 2), min(n, j + 2))
                      if k in hc and hc[k]]
                if cc:
                    a0 = max(0.0, min(x[0] for x in cc) - dem * tyv)
                    a1 = min(float(w), max(x[1] for x in cc) + dem * tyv)
                    tong += (a1 - a0) / float(w) * (j - i) / n
                    for k in range(i, j):
                        if k in hl and hl[k]:
                            ov = max(a0 - hl[k][0], hl[k][1] - a1)
                            if ov > 0:
                                sot += 1
                                nho = max(nho, ov)
                i = j
            print(f"   {ten_cl:11s} {dem:3d}px {tong*100:7.1f}% "
                  f"{(1-tong/rong_dai)*100:6.1f}%   {sot:4d}/{len(co_l):3d}  "
                  f"{nho/tyv:6.1f}px nguồn")
            ra[f"{ten_cl}|{dem}"] = (tong, sot, nho / tyv)
    return ra


if __name__ == "__main__":
    ra = [thu(t.name) for t in sorted(M.KHO.glob("*.mp4"))]
    ra = [x for x in ra if x]
    if ra:
        print("\n──────── TỔNG (giảm % bề rộng che so với DẢI) ────────")
        for k in ("cố định|10", "16s/đoạn|10", "8s/đoạn|10", "4s/đoạn|10"):
            g = [(1 - x[k][0] / x["rong_dai"]) * 100 for x in ra if k in x]
            s = sum(x[k][1] for x in ra if k in x)
            nh = max(x[k][2] for x in ra if k in x)
            print(f"  {k:12s} giảm TB {sum(g)/len(g):6.1f}% "
                  f"(thấp nhất {min(g):6.1f}%) · sót {s} · nhô tối đa "
                  f"{nh:.0f}px")
