"""ĐO: che chữ có PHỦ TỚI ĐOẠN CUỐI clip không?

Anh Hùng 20/08/2026: *"sao cứ đến gần cuối video nó k che mờ chữ gì cả"*.

CHẠY:
    .venv\\Scripts\\python _do_che_cuoi.py phu     # phủ hộp theo thời gian
    .venv\\Scripts\\python _do_che_cuoi.py xuat    # XUẤT THẬT + đo mật độ nét

`phu` là phép đo RẺ (chỉ dò, không encode) và nó trả lời ĐÍCH DANH nghi phạm 1
và 2: in ra DANH SÁCH MỐC HỘP của `do_hop_chu` cùng khoảng THIẾU PHỦ ở đuôi,
rồi quy qua `hop_theo_doan` cho nhiều độ dài clip — cố ý gồm cả độ dài CHIA HẾT
cho 8 và KHÔNG chia hết cho 8 (`HOP_DOAN` = 8 s).

`xuat` mới là thước thật: xuất clip qua `export_canvas_clip` rồi đo mật độ nét
TRONG DẢI trên FILE ĐÃ XUẤT ở nhiều mốc %, kèm trích PNG để NGƯỜI TỰ NHÌN
(cổng 56 bẫy (b): mức mờ 0,40 làm MỌI thước máy bảo "sạch" mà mắt vẫn đọc
được chữ).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

KHO = Path(r"C:\Users\Admin\Downloads\longtieng")   # CHỈ ĐỌC
RA = Path(__file__).resolve().parent / "_kq_che_cuoi"
#: Mốc % độ dài clip để soi. Dày ở ĐUÔI vì đó là chỗ anh Hùng chỉ.
MOC_TY = (0.10, 0.30, 0.50, 0.70, 0.85, 0.92, 0.97)


def _nguon() -> list:
    if not KHO.is_dir():
        return []
    return sorted([p for p in KHO.glob("*.mp4") if p.is_file()],
                  key=lambda p: p.name)


# ═══════════════════════════ 1. PHỦ HỘP THEO THỜI GIAN ══════════════════════
def _phu(hop, dai_clip: float) -> tuple:
    """(giây được phủ, khoảng THIẾU ở ĐUÔI, danh sách lỗ)."""
    ks = sorted((float(a), float(b)) for a, b, *_ in hop)
    gop, phu = [], 0.0
    for a, b in ks:
        a, b = max(0.0, a), min(dai_clip, b)
        if b <= a:
            continue
        if gop and a <= gop[-1][1] + 1e-6:
            gop[-1][1] = max(gop[-1][1], b)
        else:
            gop.append([a, b])
    lo, t = [], 0.0
    for a, b in gop:
        if a > t + 0.02:
            lo.append((round(t, 3), round(a, 3)))
        t = max(t, b)
        phu += b - a
    duoi = max(0.0, dai_clip - t)
    if duoi > 0.02:
        lo.append((round(t, 3), round(dai_clip, 3)))
    return phu, duoi, lo


def do_phu() -> int:
    from app.core import che_chu as CC
    print("=" * 78)
    print("ĐO 1 — PHỦ HỘP THEO THỜI GIAN (rẻ: chỉ dò, không encode)")
    print("=" * 78)
    kq = {}
    for src in _nguon():
        tt = CC.thong_tin(src)
        dur = float(tt["do_dai"] or 0)
        t0 = time.time()
        d = CC.dai_theo_video(src)
        giay = time.time() - t0
        print(f"\n── {src.name[:52]}")
        print(f"   dài {dur:.3f}s · {tt['rong']}x{tt['cao']} · dò {giay:.1f}s")
        print(f"   co_chu={d.co_chu} · {d.ly_do}")
        if not d.co_chu:
            continue
        hop = list(d.hop or [])
        print(f"   SỐ MỐC HỘP = {len(hop)}")
        if hop:
            print(f"   mốc ĐẦU  = {hop[0][0]:.3f} .. {hop[0][1]:.3f}")
            print(f"   mốc CUỐI = {hop[-1][0]:.3f} .. {hop[-1][1]:.3f}")
            phu, duoi, lo = _phu(hop, dur)
            print(f"   PHỦ {phu:.2f}/{dur:.2f}s = {phu/max(1e-9,dur)*100:.1f}%"
                  f" · THIẾU Ở ĐUÔI = {duoi:.3f}s")
            if lo:
                print(f"   LỖ: {lo[:8]}")
            kq[src.name] = {"dur": dur, "so_moc": len(hop),
                            "cuoi": hop[-1][1], "duoi": duoi, "lo": lo}
        # NGHI PHẠM 2 — quy về timeline ĐẦU RA cho nhiều độ dài clip.
        print("   ── hop_theo_doan (1 đoạn, bắt đầu ở 20% video) ──")
        s0 = round(dur * 0.20, 3)
        for L in (24.0, 32.0, 40.0, 45.0, 60.0, 61.0, 67.0):
            if s0 + L > dur - 0.5:
                continue
            hr = CC.hop_theo_doan(d, [(s0, s0 + L)])
            phu, duoi, lo = _phu(hr, L)
            cd = "CHIA HẾT 8" if abs(L % 8) < 1e-6 else "KHÔNG chia hết 8"
            print(f"      clip {L:5.1f}s ({cd:16s}) mốc={len(hr)} "
                  f"phủ={phu/L*100:5.1f}% thiếu-đuôi={duoi:.3f}s "
                  f"cuối={hr[-1][1] if hr else 0:.3f}")
            kq.setdefault(src.name, {}).setdefault("clip", {})[str(L)] = {
                "moc": len(hr), "phu_ty": phu / L, "duoi": duoi,
                "cuoi": (hr[-1][1] if hr else 0.0)}
        # hook-first: 2 đoạn NGƯỢC thời gian (đúng đường xuất thật)
        print("   ── hop_theo_doan (2 đoạn hook-first, NGƯỢC thời gian) ──")
        for L in (60.0, 61.0):
            a2 = round(dur * 0.62, 3)
            b2 = round(dur * 0.18, 3)
            segs = [(a2, a2 + 3.0), (b2, b2 + L - 3.0)]
            hr = CC.hop_theo_doan(d, segs)
            phu, duoi, lo = _phu(hr, L)
            print(f"      clip {L:5.1f}s mốc={len(hr)} phủ={phu/L*100:5.1f}% "
                  f"thiếu-đuôi={duoi:.3f}s cuối={hr[-1][1] if hr else 0:.3f}")
    RA.mkdir(exist_ok=True)
    (RA / "phu.json").write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    print(f"\n-> {RA / 'phu.json'}")
    return 0


# ═════════════════════════════ 2. XUẤT THẬT + ĐO ════════════════════════════
def _mat_do(src: Path, y0: int, y1: int, moc: list, x0: int = 0,
            x1: int = 0) -> float:
    from app.core import che_chu as CC
    return CC.mat_do_vung(src, y0, y1, moc, x0=x0, x1=x1)


def do_xuat() -> int:
    from app.core import che_chu as CC
    from app.core import ffmpeg_utils as FU
    RA.mkdir(exist_ok=True)
    srcs = _nguon()
    if not srcs:
        print("KHÔNG có nguồn"); return 2
    bang = []
    for src in srcs[:2]:
        tt = CC.thong_tin(src)
        dur = float(tt["do_dai"] or 0)
        d = CC.dai_theo_video(src)
        if not d.co_chu:
            print(f"BỎ QUA (không chữ): {src.name}"); continue
        for L in (40.0, 45.0):
            s0 = round(dur * 0.20, 3)
            if s0 + L > dur - 0.5:
                continue
            segs = [(s0, s0 + L)]
            dst = RA / f"{'A' if src is srcs[0] else 'B'}_{int(L)}.mp4"
            log: list = []
            t0 = time.time()
            FU.export_canvas_clip(
                str(src), str(dst), segs, out_w=1080, out_h=1920,
                bg="fill", che_chu=True, che_chu_cach="mo", che_chu_muc=1.0,
                che_chu_log=log, hieu_ung="tat", chuyen_canh="tat")
            gi = time.time() - t0
            print(f"\n── {dst.name} ({gi:.1f}s) {log[0].get('ly_do','')}")
            ra_tt = CC.thong_tin(dst)
            L2 = float(ra_tt["do_dai"] or L)
            # DẢI trong toạ độ FILE XUẤT: nguồn 1080 rộng -> ra 1080 nên
            # `bg=fill` giữ tỉ lệ; quy y theo tỉ lệ chiều cao.
            ty = (ra_tt["cao"] or 1920) / max(1, tt["cao"])
            y0, y1 = int(d.y0 * ty), int(d.y1 * ty)
            x0d = int((d.x0_dai or d.x0) * ty)
            x1d = int((d.x1_dai or d.x1) * ty)
            dong = {"file": dst.name, "dai": L2, "moc": {}}
            for r in MOC_TY:
                t = round(L2 * r, 3)
                md_g = _mat_do(src, d.y0, d.y1, [s0 + t],
                               x0=(d.x0_dai or d.x0), x1=(d.x1_dai or d.x1))
                md_r = _mat_do(dst, y0, y1, [t], x0=x0d, x1=x1d)
                dong["moc"][f"{int(r*100)}%"] = {"t": t, "goc": round(md_g, 4),
                                                 "xuat": round(md_r, 4)}
                print(f"   {int(r*100):3d}%  t={t:7.3f}s  gốc={md_g:.4f}  "
                      f"XUẤT={md_r:.4f}")
                CC.trich_khung(dst, t, RA / f"{dst.stem}_{int(r*100)}.png")
            bang.append(dong)
    (RA / "xuat.json").write_text(
        json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {RA / 'xuat.json'}  · ảnh PNG trong {RA}")
    return 0


if __name__ == "__main__":
    viec = (sys.argv[1] if len(sys.argv) > 1 else "phu").lower()
    sys.exit(do_phu() if viec == "phu" else do_xuat())
