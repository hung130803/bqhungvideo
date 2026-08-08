# -*- coding: utf-8 -*-
r"""DEMO v4 cho anh Hùng — `D:\hieu-ung-demo-v4\`.

Chạy: .venv\Scripts\python _do_demo_v4.py

5 clip THẬT từ video Nhật trong `C:\Users\Admin\Downloads\thùng rác`, **mỗi clip
2 bản BẬT/TẮT** để mở cạnh nhau mà so. Kèm `_ghi_chu.txt`: bảng "giây thứ mấy ->
hiệu ứng gì -> VÌ SAO (số đo)" + **tỉ lệ % thời lượng có hiệu ứng** từng clip.

Xuất qua ĐÚNG hàm sản xuất `export_canvas_clip` (không dựng lệnh riêng) nên cái
anh Hùng xem ĐÚNG BẰNG cái app sẽ ra.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"demo_v4_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401

import _nguon_nhat  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402
from app.core import hieu_ung as HU  # noqa: E402
from app.core import hieu_ung_gpu as HG  # noqa: E402
from config import settings  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

RA = Path(r"D:\hieu-ung-demo-v4")
FP = settings.FFPROBE_PATH
_NOWIN = 0x08000000


def dai(p: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True,
                       text=True, creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


#: 5 CLIP — mỗi cái nhắm một CA THẬT khác nhau của dây chuyền.
#  (tên, chỉ số nguồn, các đoạn, mức hiệu ứng, mức chuyển cảnh, giải thích)
CA = [
    ("A_2doan_hookfirst", 0, [(300.0, 312.0), (100.0, 108.0)], "nhe", "nhe",
     "2 đoạn HOOK-FIRST (đoạn sau đưa lên trước) — ca hay gặp nhất"),
    ("B_3doan_vua", 1, [(100.0, 110.0), (60.0, 68.0), (200.0, 206.0)],
     "vua", "vua", "3 đoạn, mức Vừa"),
    ("C_3doan_manh_GPU", 1, [(200.0, 210.0), (100.0, 107.0), (300.0, 305.0)],
     "manh", "manh", "3 đoạn, mức Mạnh — chuyển cảnh chạy trên GPU (OpenCL)"),
    ("D_1doan_dai", 2, [(60.0, 95.0)], "vua", "nhe",
     "1 đoạn dài 35s — không có chỗ nối, hiệu ứng phải tự tìm điểm nhấn"),
    ("E_4doan_lienmach", 0, [(100.0, 108.0), (108.5, 114.0), (114.2, 119.0),
                             (200.0, 203.0)], "nhe", "nhe",
     "4 đoạn GẦN LIỀN MẠCH (chỉ bỏ vài giây thừa)"),
]


def main() -> None:
    ds = _nguon_nhat.liet_ke()
    if len(ds) < 3:
        print("KHÔNG đủ video Nhật thật -> DỪNG")
        return
    RA.mkdir(parents=True, exist_ok=True)
    enc = fu.detect_encoder()
    print(f"[ra]      {RA}")
    print(f"[encoder] {enc} · trần ffmpeg song song "
          f"{fu.so_ffmpeg_song_song()}")
    print(f"[kho]     hiệu ứng điểm nhấn {len(HU.dung_duoc())}/{len(HU.KHO)} · "
          f"chuyển cảnh CPU 58 · GPU {len(fu.co_chuyen_canh_gpu())} · "
          f"shader {len(HG.shader_co())}")
    for i, p in enumerate(ds[:3]):
        print(f"[nguồn {i}] {os.path.basename(p)}")

    gc: list[str] = []
    gc.append("GHI CHÚ DEMO v4 — HIỆU ỨNG ĐIỂM NHẤN DO AI TỰ CHỌN")
    gc.append("=" * 100)
    gc.append("")
    gc.append("Mỗi clip có 2 bản: `_TAT` (không hiệu ứng) và `_BAT` (có).")
    gc.append("MỞ CẠNH NHAU MÀ SO — bản TẮT ra file GIỐNG HỆT bản app cũ.")
    gc.append("")
    gc.append("AI chọn theo SỐ ĐO CỦA CHÍNH CLIP, không bốc thăm:")
    gc.append("  · RMS từng giây  -> giây nào tiếng VỌT LÊN so với trung vị")
    gc.append("  · mức chuyển động từng giây -> cảnh ĐỘNG hay cảnh TĨNH")
    gc.append("  · mốc ghép đoạn  -> chỗ đổi mạch")
    gc.append("4 luật chống loè: tối đa 3 điểm/clip · mỗi điểm 0,30-0,80s ·")
    gc.append("TỔNG giây có hiệu ứng <= 10% thời lượng · cảnh TĨNH không nhận")
    gc.append("hiệu ứng động · đoạn không cao trào thì KHÔNG thêm gì.")
    gc.append("")

    tong_ty_le: list[float] = []
    for ten, idx, segs, muc, xf, mo_ta in CA:
        src = ds[min(idx, len(ds) - 1)]
        tong = sum(e - s for s, e in segs)
        print(f"\n=== {ten} ({mo_ta}) ===")
        gc.append("=" * 100)
        gc.append(f"{ten}   —   {mo_ta}")
        gc.append(f"  nguồn: {os.path.basename(src)}")
        gc.append(f"  đoạn : " + " + ".join(f"[{s:.1f}s..{e:.1f}s]"
                                            for s, e in segs)
                  + f"  = {tong:.2f}s")
        gc.append(f"  mức  : hiệu ứng điểm nhấn «{muc}» · "
                  f"chuyển cảnh «{xf}»")
        ket = {}
        for nhan, m_hu, m_xf in (("TAT", "tat", "tat"), ("BAT", muc, xf)):
            out = str(RA / f"{ten}_{nhan}.mp4")
            log: list = []
            t0 = time.time()
            fu.export_canvas_clip(
                src, out, segs, (0.5, 0.5, 1.0), out_w=1080, out_h=1920,
                bg="blur", encoder=enc, fx_fade=True, fx_whoosh=True,
                chuyen_canh=m_xf, hieu_ung=m_hu, hieu_ung_log=log)
            w = time.time() - t0
            kb = os.path.getsize(out) // 1024
            d = dai(out)
            ket[nhan] = (d, log, w)
            print(f"  {nhan:<3} {d:7.3f}s {kb:7d} KB  wall {w:5.2f}s  "
                  f"· {len(log)} điểm nhấn")
        d_tat, d_bat = ket["TAT"][0], ket["BAT"][0]
        log = ket["BAT"][1]
        ty = HU.ty_le_co_hieu_ung(log, d_bat) if log else 0.0
        tong_ty_le.append(ty)
        gc.append(f"  độ dài: TẮT {d_tat:.3f}s · BẬT {d_bat:.3f}s  "
                  f"(lệch {abs(d_bat - d_tat) * 1000:.0f} ms — phải ~0, nếu"
                  f" lệch thì phụ đề sẽ trôi)")
        gc.append("")
        if not log:
            gc.append("  ĐIỂM NHẤN: KHÔNG có điểm nào — clip này PHẲNG (không")
            gc.append("  có giây nào tiếng/hình vọt lên đủ so với trung vị).")
            gc.append("  Đây là hành vi ĐÚNG: 'cái nào cần thì hiện thôi'.")
        else:
            gc.append("  giây (bật-tắt) | hiệu ứng             | CapCut       "
                      "     | VÌ SAO — số đo của chính clip này")
            gc.append("  " + "-" * 122)
            for c in log:
                h = HU.KHO.get(c["khoa"])
                gc.append(f"  {c['bat']:6.2f}-{c['het']:6.2f} | "
                          f"{(h.ten if h else c['khoa']):<21} | "
                          f"{(h.capcut if h else ''):<18} | "
                          f"{c.get('vi_sao', '')}")
            gc.append("  " + "-" * 122)
            gc.append(f"  TỔNG: clip {d_bat:.2f}s · "
                      f"{sum(c['het'] - c['bat'] for c in log):.2f}s có hiệu "
                      f"ứng = **{ty:.1f}%** (trần 10%)")
        # chuyển cảnh
        if len(segs) > 1 and xf != "tat":
            kieu = fu.chon_chuyen_canh(segs, xf)
            gc.append("")
            gc.append("  CHUYỂN CẢNH ở chỗ ghép đoạn (kiểu do app suy theo "
                      "NỘI DUNG chỗ nối):")
            for i, (k, dd) in enumerate(kieu):
                loai = fu._loai_cho_noi(segs, i)
                nn = {"nguoc": "nhảy NGƯỢC thời gian (hook-first)",
                      "lien": "gần liền mạch (chỉ bỏ vài giây thừa)",
                      "chot": "đoạn kế rất ngắn = câu chốt",
                      "xa": "nhảy xa = đổi bối cảnh"}.get(loai, loai)
                gpu = " [chạy trên GPU]" if str(k).startswith("gl_") else ""
                ten_k = HG.KHO_GPU[k].ten if str(k).startswith("gl_") else k
                gc.append(f"    chỗ nối {i + 1}: {ten_k} {dd:.2f}s{gpu} "
                          f"— vì {nn}")
        gc.append("")

    gc.append("=" * 100)
    gc.append(f"TỈ LỆ % THỜI LƯỢNG CÓ HIỆU ỨNG — 5 clip: "
              + " · ".join(f"{t:.1f}%" for t in tong_ty_le))
    gc.append(f"cao nhất {max(tong_ty_le):.1f}% (trần thiết kế 10%). "
              f"Vượt 10% là SAI thiết kế, app tự cắt bớt điểm.")
    gc.append("")
    gc.append("BẢN TẮT RA FILE GIỐNG HỆT BẢN APP CŨ — đã đo PSNR ở cổng 38.")
    (RA / "_ghi_chu.txt").write_text("\n".join(gc), encoding="utf-8")
    print(f"\nXong. Ghi chú: {RA / '_ghi_chu.txt'}")
    print("tỉ lệ % có hiệu ứng: "
          + " · ".join(f"{t:.1f}%" for t in tong_ty_le))


if __name__ == "__main__":
    try:
        main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
        for _s in (sys.stdout, sys.stderr):
            try:
                _s.flush()
            except (ValueError, OSError):
                pass
    os._exit(0)
