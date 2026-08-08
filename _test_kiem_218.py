# -*- coding: utf-8 -*-
r"""CỔNG 45 — 3 LỖI ÂM THẦM LƯỢT KIỂM ĐỘC LẬP v2.18.0 TÌM RA (08/08/2026).

Cả 3 đều thuộc loại "app vẫn chạy, mọi cổng vẫn xanh, chỉ SỐ ĐO tố giác".

(A) **ĐO NHỊP BỊ CỤT -> MẤT SẠCH ĐIỂM NHẤN, IM LẶNG.**
    `hieu_ung.do_nhip` trả 1 giá trị/giây và KHÔNG bao giờ báo lỗi khi nó chỉ
    đo được mấy giây đầu (file `metadata=print` bị ffmpeg GHI ĐÈ mỗi lần dựng
    lại filter graph). `chon_hieu_ung` nhận danh sách ngắn ấy như số đo THẬT
    của cả clip. ĐO TRÊN CHÍNH HÀM (clip 16 s, cao trào ở giây 7/11/14, mức
    "vua"):
        đo ĐỦ 16/16 giây  -> 3 điểm nhấn (7,0 · 11,0 · 14,0)
        đo cụt  8/16 giây -> 3 điểm nhưng DỒN vào 0,0 · 3,0 · 7,0
        đo cụt  4/16 giây -> **0 điểm nhấn**
        KHÔNG đo được []  -> 3 điểm (đường CẤU TRÚC)  <- thà thế còn hơn
    Đúng triệu chứng đã xảy ra thật hôm 08/08 (mảnh mezzanine lệch `pix_fmt`
    -> chỉ đo được 4/16 giây -> 0 điểm nhấn trên MỌI máy không NVENC). Bản vá
    hôm đó bịt ĐÚNG MỘT nguyên nhân; cái DÒ thì chưa có. Nay có `do_du`.

(B) **NHẬT KÝ DÂY CHUYỀN ĐỌC TIẾNG ĐỘNG CỦA CLIP KHÁC.**
    `m1_highlight._ghi_cong_thuc` đọc biến TOÀN CỤC
    `ffmpeg_utils._SFX_LAST_PICK`, trong khi chính file đó đã ghi chú "đừng đọc
    biến toàn cục: 3 làn xuất song song thì nó là của clip nào xong sau cùng".
    Máy anh Hùng chạy 3 chỗ ffmpeg song song -> dòng nhật ký của Part A có thể
    là tiếng của Part B. Nay `_ghi_cong_thuc` nhận `td_log` của chính lượt.

(C) **BẤT BIẾN `.ass`: cỡ chữ là PIXEL.** `captions.build_ass(size=…)` nhận
    PIXEL; truyền tỉ lệ (0,055) thì file .ass ghi `Fontsize: 0.055` -> chữ nhỏ
    dưới 1 điểm ảnh = KHÔNG THẤY GÌ, mà `build_ass` vẫn trả True và ffmpeg vẫn
    rc=0 + đủ khung. Ca này chốt lại quy ước để lối gọi mới không sập.

Chạy: .venv\Scripts\python.exe _test_kiem_218.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"kiem218_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_TEST", "1")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import captions as CAP          # noqa: E402
from app.core import hieu_ung as HU           # noqa: E402

_OK: list[str] = []
_LOI: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK  ' if ok else 'FAIL'}] {ten}: {so}")


def _nhip(n: int = 16, cao=(7, 11, 14)):
    nl = [0.05] * n
    cd = [0.10] * n
    for i in cao:
        if i < n:
            nl[i], cd[i] = 0.90, 0.85
    return nl, cd


# ══════════════════ A. ĐO CỤT PHẢI BỊ BẮT ══════════════════
def ca_do_cut() -> None:
    print("\n[A] ĐO NHỊP BỊ CỤT — phải bị bắt, không được coi là số đo thật")
    nl, cd = _nhip()
    dung = HU.dung_duoc(co_font=True)
    kq = {}
    for n in (16, 12, 8, 4, 2):
        kq[n] = HU.chon_hieu_ung(16.0, "vua", nl=nl[:n], cd=cd[:n],
                                 moc_noi=[6.0, 11.0], co_the_dung=dung)
    khong = HU.chon_hieu_ung(16.0, "vua", nl=[], cd=[], moc_noi=[6.0, 11.0],
                             co_the_dung=dung)
    for n, r in kq.items():
        print(f"      đo {n:2d}/16 giây -> {len(r)} điểm "
              f"{[(c['khoa'], c['bat']) for c in r]}")
    print(f"      KHÔNG đo được -> {len(khong)} điểm "
          f"{[(c['khoa'], c['bat']) for c in khong]}")

    # 1. Bộ dò phải KÊU đúng chỗ (đây là cái cổng canh, không phải con dấu).
    bao("`do_du` nói ĐỦ khi đo đủ 16/16 giây",
        HU.do_du(nl, cd, 16.0), f"{len(nl)} mẫu / 16 giây")
    bao("`do_du` nói CỤT khi chỉ đo được 8/16 giây",
        not HU.do_du(nl[:8], cd[:8], 16.0), "8 mẫu / 16 giây")
    bao("`do_du` nói CỤT khi chỉ đo được 4/16 giây (đúng ca lỗi thật)",
        not HU.do_du(nl[:4], cd[:4], 16.0), "4 mẫu / 16 giây")
    bao("`do_du` KHÔNG kêu oan khi thiếu 1 giây cuối (làm tròn)",
        HU.do_du(nl[:15], cd[:15], 16.0), "15 mẫu / 16 giây")
    bao("`do_du` với clip ngắn 2 giây vẫn đúng",
        HU.do_du([0.1, 0.2], [0.1, 0.2], 2.0)
        and not HU.do_du([0.1], [], 4.0), "2/2 đủ · 1/4 cụt")

    # 2. SỐ ĐO chứng minh vì sao phải bắt: cụt TỆ HƠN không đo.
    bao("đo CỤT 4/16 giây làm MẤT SẠCH điểm nhấn (0 điểm)",
        len(kq[4]) == 0, f"{len(kq[4])} điểm")
    bao("KHÔNG đo được thì vẫn ra đủ điểm nhấn (đường CẤU TRÚC)",
        len(khong) >= 2, f"{len(khong)} điểm "
        f"{[c['bat'] for c in khong]}")
    bao("đo CỤT 8/16 giây DỒN mọi điểm vào nửa đầu clip (sai chỗ)",
        bool(kq[8]) and max(c["bat"] for c in kq[8]) < 8.0,
        f"điểm xa nhất {max((c['bat'] for c in kq[8]), default=-1)}s "
        f"trong khi cao trào thật ở 7/11/14s")

    # 3. Đường xuất PHẢI gọi bộ dò — quét tĩnh (bịt lại là cổng biết).
    src = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    bao("`export_canvas_clip` CÓ gọi `do_du` ngay sau `do_nhip`",
        "do_nhip(" in src and "do_du(" in src
        and src.index("do_du(") - src.index("_HU.do_nhip(") < 1200,
        "quét tĩnh: có cả 2, đứng cạnh nhau")


# ══════════════════ B. NHẬT KÝ PHẢI LÀ CỦA CHÍNH LƯỢT ══════════════════
def ca_nhat_ky_dung_clip() -> None:
    print("\n[B] NHẬT KÝ DÂY CHUYỀN — tiếng động phải là của CHÍNH Part này")
    from app.core import ffmpeg_utils as FU
    from app.modules import m1_highlight as M1
    from config import DATA_DIR

    # dựng bẫy: biến TOÀN CỤC mang tiếng của CLIP KHÁC (lượt xong sau cùng)
    FU._SFX_LAST_PICK = [("impact", "CUA_CLIP_KHAC.opus")]
    td_log = [{"giay": 1.2, "loai": "scratch", "ten": "CUA_CHINH_TOI.opus",
               "vai": "điểm nhấn", "db": -3.0, "nguon": "kho tiếng động"}]
    log_dir = Path(DATA_DIR) / "logs"
    truoc = set(p.name for p in log_dir.glob("pipeline_*.log")) \
        if log_dir.exists() else set()
    M1._ghi_cong_thuc({"cap_style": {"preset": "X", "_mau": "mẫu A"},
                       "captions": True, "hieu_ung": "vua"},
                      "co.ass", ["transition"], False, "blur", "[Part 1] ",
                      [], duong="canvas", td_log=td_log)
    files = sorted(log_dir.glob("pipeline_*.log")) if log_dir.exists() else []
    noi_dung = "".join(f.read_text(encoding="utf-8", errors="replace")
                       for f in files)
    bao("nhật ký ghi tiếng của CHÍNH lượt này",
        "CUA_CHINH_TOI.opus" in noi_dung,
        "thấy tên file của lượt này" if "CUA_CHINH_TOI.opus" in noi_dung
        else f"KHÔNG thấy · {len(files)} file log · {len(truoc)} file cũ")
    bao("nhật ký KHÔNG lấy tiếng của clip khác từ biến toàn cục",
        "CUA_CLIP_KHAC.opus" not in noi_dung,
        "sạch" if "CUA_CLIP_KHAC.opus" not in noi_dung
        else "ĐANG ĐỌC BIẾN TOÀN CỤC = lỗi")
    src = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8", errors="replace")
    bao("chỗ gọi `_ghi_cong_thuc` CÓ truyền `td_log`",
        "td_log=locals().get(\"_td_log\")" in src
        or "td_log=locals().get('_td_log')" in src, "quét tĩnh")
    FU._SFX_LAST_PICK = []


# ══════════════════ C. CỠ CHỮ .ass LÀ PIXEL ══════════════════
def ca_co_chu_ass() -> None:
    print("\n[C] `build_ass(size=…)` là PIXEL — truyền tỉ lệ ra chữ VÔ HÌNH")
    ws = [{"start": 0.2 + i * 0.4, "end": 0.5 + i * 0.4, "word": w}
          for i, w in enumerate("MOT HAI BA BON NAM SAU".split())]
    a = _SB / "px.ass"
    b = _SB / "ti_le.ass"
    CAP.build_ass(ws, [(0.0, 4.0)], str(a), out_w=1080, out_h=1920,
                  size=int(0.055 * 1920), preset="Vàng nhảy (TikTok)")
    CAP.build_ass(ws, [(0.0, 4.0)], str(b), out_w=1080, out_h=1920,
                  size=0.055, preset="Vàng nhảy (TikTok)")

    def _cot(p) -> float:
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.startswith("Style: Default"):
                try:
                    return float(ln.split(",")[2])
                except (ValueError, IndexError):
                    return -1.0
        return -1.0

    bao("truyền PIXEL -> Fontsize hợp lệ (>= 20 px)", _cot(a) >= 20,
        f"Fontsize={_cot(a)}")
    bao("truyền TỈ LỆ -> Fontsize < 1 px (chữ VÔ HÌNH mà hàm vẫn trả True)",
        0 < _cot(b) < 1.0,
        f"Fontsize={_cot(b)} — quy ước: nhân out_h TRƯỚC khi gọi "
        f"(m1_highlight làm `int(csize*out_h)`)")
    src = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8", errors="replace")
    bao("m1_highlight vẫn quy đổi tỉ lệ -> pixel trước khi gọi build_ass",
        "int(csize * out_h) if csize < 1 else int(csize)" in src, "quét tĩnh")


def main() -> int:
    print("=" * 74)
    print("CỔNG 45 — lượt kiểm độc lập v2.18.0")
    print("=" * 74)
    try:
        ca_do_cut()
        ca_nhat_ky_dung_clip()
        ca_co_chu_ass()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    print("\n" + "=" * 74)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("   ✗ " + x)
    print("=" * 74)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
