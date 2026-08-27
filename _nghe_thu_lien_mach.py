# -*- coding: utf-8 -*-
"""FILE NGHE THỬ CHO ANH HÙNG — **TAI LÀ PHÁN QUYẾT CUỐI**.

Cả lượt đo này đứng trên hai thước KHÔNG phán được điều anh Hùng hỏi:
`f0_nua_cung` chỉ nói ĐỘ TRẢI CAO ĐỘ (không nói HAY), và `%im` không nói
*"nghe có liền mạch không"*. Nên phải có file để nghe.

**NĂM THỨ BẮT BUỘC (mỗi cái đã sập một lần):**
  1. **CẶP TRƯỚC/SAU trên CÙNG đoạn CÙNG giọng** — nghe hai giọng khác nhau
     rồi bảo "cái này hay hơn" là so GIỌNG, không so bản vá.
  2. **ĐOẠN NHIỀU CÂU LIỀN NHAU (>= 6-8 câu)** — đoạn 1 câu KHÔNG nghe ra được
     ngắt quãng, mà ngắt quãng đúng là thứ anh Hùng đang kêu. Ở đây 12 câu.
  3. **CÙNG −14 LUFS** qua chính `thay_giong.chuan_do_to`, rồi **KIỂM LẠI
     BẰNG `loudnorm` CHẠY RIÊNG** — lượt trước cột LUFS của hàm in ra 0,00 vì
     đọc sai khoá, tức bảng khoe một phép chuẩn hoá KHÔNG ai kiểm.
  4. **MD5 KHÁC NHAU** — bẫy cache đã cho ra 2 file y hệt mang 2 tên.
  5. **TÊN KÈM SỐ ĐO** để nghe xong đối chiếu được ngay.

Chạy:  .venv\\Scripts\\python -u _nghe_thu_lien_mach.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from config import settings                                    # noqa: E402

RA = REPO / "_NGHE_THU_ANH_HUNG" / "lien_mach_2"
KQ = REPO / "_kq_lienmach"
NOWIN = 0x08000000


def md5(p) -> str:
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:10]


def do_lufs(p) -> tuple[float, float]:
    """(I, TP) đo bằng `loudnorm` CHẠY RIÊNG — thước ĐỘC LẬP với hàm áp."""
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-i", str(p), "-af",
         "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NOWIN, timeout=300)
    s = r.stderr or ""
    i = s.rfind("{")
    if i < 0:
        return (0.0, 0.0)
    try:
        d = json.loads(s[i:s.rfind("}") + 1])
        return (float(d.get("input_i", 0)), float(d.get("input_tp", 0)))
    except (ValueError, TypeError):
        return (0.0, 0.0)


def main():
    from app.core import thay_giong as tg

    shutil.rmtree(RA, ignore_errors=True)
    RA.mkdir(parents=True, exist_ok=True)
    kq_h = json.loads((KQ / "H_nhan_nha_noi.json").read_text(encoding="utf-8"))
    kq_g = json.loads((KQ / "G_xen_bien.json").read_text(encoding="utf-8"))

    #: (tên đích, file nguồn, ghi chú) — mọi cặp đều CÙNG đoạn CÙNG giọng.
    ds: list[tuple[str, Path]] = []

    # ── CẶP 1: NHẤN NHÁ (giọng anh Hùng đang dùng: vi_VN_NamMinhNeural) ──
    for may, gi in (("edge", "vi_VN_NamMinhNeural"), ("vn", "vn_ThanhBinh")):
        d = kq_h.get(may) or {}
        for arm, nhan in (("TAT", "1_TRUOC"), ("BAT", "2_NHAN_NHA")):
            a = d.get(arm)
            if not a or not Path(a["wav"]).exists():
                continue
            ds.append((f"NHANNHA__{gi}__{nhan}__nn{a['nhan_nha']:.2f}"
                       f"_wer{a['wer']:.1f}.wav", Path(a["wav"])))

    # ── CẶP 2: XÉN LỀ IM (đúng bệnh của file nghe thử lượt trước) ──
    for ten, nhan in (("M0_KHONG_XEN", "1_TRUOC_nhu_file_cu"),
                      ("M1_XEN_NHE", "2_XEN_NHE"),
                      ("M2_APP", "3_XEN_NHU_APP"),
                      ("M3_XEN_SACH", "4_XEN_SACH")):
        a = kq_g.get(ten)
        if not a or not Path(a["wav"]).exists():
            continue
        ds.append((f"NGATQUANG__vi_VN_NamMinhNeural__{nhan}"
                   f"__im{a['pc']:.1f}pc_dainhat{a['dai_nhat']:.2f}s.wav",
                   Path(a["wav"])))

    print("=" * 96)
    print("FILE NGHE THỬ — mọi file chuẩn hoá CÙNG -14 LUFS, kiểm lại bằng "
          "`loudnorm` CHẠY RIÊNG")
    print("=" * 96)
    print(f"{'file':<62} {'I (LUFS)':>9} {'TP':>7} {'MD5':>12}")
    print("-" * 96)
    seen: dict[str, str] = {}
    for ten, src in ds:
        dst = RA / ten
        try:
            tg.chuan_do_to(src, dst)
        except Exception as e:                                # noqa: BLE001
            print(f"{ten:<62} CHUẨN HOÁ HỎNG: {type(e).__name__}: {e}")
            continue
        if not dst.exists():
            continue
        i_, tp = do_lufs(dst)
        h = md5(dst)
        canh = "  <-- TRÙNG MD5!" if h in seen else ""
        seen[h] = ten
        print(f"{ten:<62} {i_:>9.2f} {tp:>7.2f} {h:>12}{canh}")
    print("-" * 96)
    print(f"tổng {len(seen)} file MD5 KHÁC NHAU / {len(ds)} file sinh ra")
    print(f"\nthư mục: {RA}")


if __name__ == "__main__":
    main()
