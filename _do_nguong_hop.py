# -*- coding: utf-8 -*-
"""ĐO: vì sao dò bề NGANG theo TỪNG KHUNG lại bám vào vân nền — và cách chữa.

Bằng chứng (`_do_hop_chu.py`, zh_dongho): hộp theo đoạn 8s SÓT 20/186 khung
LẺ, chỗ nhô ra tới **188 px nguồn** — không phải "thiếu vài px", mà là hộp
nằm HẲN chỗ khác. Xem profile cột ở t=7,75s: chữ nằm x≈240..400 nhưng nền
(mạn thuyền trắng + nước loé) cũng cho mực từ x=512 tới 640.

Script này thử 2 cách chữa, đo trên CÙNG dữ liệu:
  (1) NGƯỠNG NÉT cao hơn (chữ phụ đề là trắng tinh có viền đen -> top-hat rất
      mạnh; loé nền yếu hơn)
  (2) GỘP CẢ ĐOẠN rồi mới dò (nền đổi giữa các khung nên trung bình xuống,
      chữ đứng yên trong dải nên trung bình giữ nguyên)
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


def mat_na_nguong(g: np.ndarray, ng: int) -> np.ndarray:
    return (C._top_hat(g) > ng).astype(np.uint8)


def thu(ten: str, fps: float = 2.0):
    p = M.KHO / ten
    d = C.do_dai_chu(p, so_khung=16)
    tt = C.thong_tin(p)
    W, H = tt["rong"], tt["cao"]
    arr, w, off, moc = M.doc_day(p, fps, d.y0, d.y1)
    n = arr.shape[0]
    tyv = w / float(W)
    r0 = max(0, int(d.y0 * tyv) - off)
    r1 = min(arr.shape[1], max(r0 + 2, int(d.y1 * tyv) - off))
    print(f"\n=== {ten}  {n} khung · dải hàng {r0}..{r1}")

    for ng in (55, 80, 110, 140):
        mns = np.stack([mat_na_nguong(g, ng) for g in arr])
        const = (mns.sum(axis=0) >= C.TY_LE_HANG * n).astype(np.uint8)
        doi = np.clip(mns.astype(np.int16) - const[None], 0, 1).astype(np.uint8)
        hs = [M.be_ngang(doi[i], r0, r1, w, md_min=0.02) for i in range(n)]
        co = [i for i, x in enumerate(hs) if x]
        chan = [i for i in co if i % 2 == 0]
        le = [i for i in co if i % 2 == 1]
        if not chan or not le:
            print(f"  ngưỡng {ng:3d}: không đủ khung có chữ")
            continue
        # ---- (1) TỪNG KHUNG rồi hợp theo đoạn 8s
        b = int(8 * fps)
        tong = sot = 0.0
        nho = 0
        i = 0
        while i < n:
            j = min(n, i + b)
            cc = [hs[k] for k in range(max(0, i - 1), min(n, j + 1))
                  if k % 2 == 0 and hs[k]]
            if cc:
                a0 = min(x[0] for x in cc)
                a1 = max(x[1] for x in cc)
                tong += (a1 - a0) / float(w) * (j - i) / n
                for k in range(i, j):
                    if k % 2 == 1 and hs[k]:
                        ov = max(a0 - hs[k][0], hs[k][1] - a1)
                        if ov > 0:
                            sot += 1
                            nho = max(nho, ov)
            i = j
        # ---- (2) GỘP CẢ ĐOẠN rồi mới dò
        tong2 = sot2 = 0.0
        nho2 = 0
        i = 0
        while i < n:
            j = min(n, i + b)
            idx = [k for k in range(max(0, i - 1), min(n, j + 1)) if k % 2 == 0]
            if idx:
                gop = doi[idx].mean(axis=0)
                sub = gop[r0:r1]
                cot = sub.sum(axis=0).astype(np.float32)
                cs = np.convolve(cot, np.ones(3, np.float32) / 3.0, mode="same")
                if cs.max() > 0:
                    dinh = int(np.argmax(cs))
                    a0, a1 = M._moc_ra(cs, dinh, 0.15 * float(cs[dinh]),
                                       max(2, r1 - r0), 0, w)
                    tong2 += (a1 - a0) / float(w) * (j - i) / n
                    for k in range(i, j):
                        if k % 2 == 1 and hs[k]:
                            ov = max(a0 - hs[k][0], hs[k][1] - a1)
                            if ov > 0:
                                sot2 += 1
                                nho2 = max(nho2, ov)
            i = j
        print(f"  ngưỡng {ng:3d}: khung có chữ {len(co):3d}/{n} · "
              f"[từng khung] rộng TB {tong*100:5.1f}% W · sót {int(sot):3d} "
              f"nhô {nho/tyv:5.1f}px  ||  [gộp đoạn] rộng TB {tong2*100:5.1f}% W"
              f" · sót {int(sot2):3d} nhô {nho2/tyv:5.1f}px")


for t in ("zh_dongho.mp4", "zh_ep12.mp4"):
    thu(t)
