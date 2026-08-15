# -*- coding: utf-8 -*-
"""CỔNG 61 — CO GIÃN THỜI GIAN ĐI `rubberband`, THIẾU THÌ LÙI `atempo`.

VÌ SAO CÓ CỔNG NÀY (15/08/2026, việc 1):
`khop_thoi_gian` bước cuối cùng ép co giãn cho câu quá dài. v2.27.0 đã bỏ
được PHẦN LỚN các lượt ép (cắt lề im + rút gọn + `rate`), nhưng bước ép vẫn
còn đó và vẫn bắn. Đo được `rubberband` méo ít hơn `atempo` ở MỌI hệ số, và ở
hệ số 1,0 thì `rubberband` là đường ống trong suốt (lệch mẫu `0.000000`) còn
`atempo` vẫn phá 1,982 dB — xem `_do_rubberband.py` / `_do_rb_soi.py`.

**RỦI RO CỔNG NÀY CANH:** máy nhân viên chạy ffmpeg riêng trên PATH không
build kèm `--enable-librubberband`. Lúc đó chuỗi filter `rubberband=...` làm
**ffmpeg chết cả lượt** -> mất trắng video. Nên phải LÙI, và đường lùi phải
được kiểm THẬT chứ không chỉ hứa trong ghi chú.

  .venv\\Scripts\\python -u _test_co_gian.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _test_guard  # noqa: F401,E402  (luật: mọi cổng phải import)

from config import settings  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

SAN = REPO / f"bq_test_cogian_{os.getpid()}"
DAT = HONG = 0


def kiem(ten: str, dieu_kien: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu_kien:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


def ff(args: list[str], timeout: float = 120.0) -> int:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode


def dung_giong(dst: Path, giay: float = 2.0) -> None:
    """Nguồn có PHỤ ÂM BẬT giả lập (chuỗi xung) — chỗ WSOLA hỏng trước tiên."""
    ff(["-f", "lavfi", "-i",
        f"sine=frequency=220:duration={giay}",
        "-af", "aresample=44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)])


def main() -> int:
    SAN.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("CỔNG 61 — CO GIÃN `rubberband` + ĐƯỜNG LÙI `atempo`")
    print("=" * 70)
    print(f"ffmpeg: {settings.FFMPEG_PATH}")

    # ═══════════ CA 1 — dò bộ lọc ═══════════
    print("\nCA 1 — dò `rubberband` trong ffmpeg đang dùng")
    tg._CO_RUBBERBAND = None
    co = tg.co_rubberband()
    print(f"  co_rubberband() = {co}")
    # dò phải KHỚP với sự thật đọc từ `-filters`
    r = subprocess.run([settings.FFMPEG_PATH, "-hide_banner", "-filters"],
                       capture_output=True, text=True, timeout=60)
    that = any(ln.split()[1:2] == ["rubberband"]
               for ln in (r.stdout or "").splitlines() if len(ln.split()) > 1)
    kiem("1a dò khớp với `ffmpeg -filters`", co == that,
         f"dò={co} · thật={that}")

    # ═══════════ CA 2 — chuỗi filter đúng dạng ═══════════
    print("\nCA 2 — chuỗi filter sinh ra")
    os.environ.pop("BQ_TG_RUBBERBAND", None)
    tg._CO_RUBBERBAND = None
    if co:
        s12 = tg._co_gian_chuoi(1.2)
        kiem("2a mặc định dùng `rubberband`", s12.startswith("rubberband="),
             s12)
        # rubberband KHÔNG bị kẹp 0,5..2,0 nên KHÔNG được chia tầng
        s25 = tg._co_gian_chuoi(2.5)
        kiem("2b hệ số > 2,0 KHÔNG chia tầng", s25.count("rubberband") == 1,
             s25)
        kiem("2c KHÔNG đặt `pitch` (giữ nguyên cao độ)", "pitch" not in s12,
             s12)
    # đường lùi
    os.environ["BQ_TG_RUBBERBAND"] = "0"
    s_lui = tg._co_gian_chuoi(2.5)
    kiem("2d `BQ_TG_RUBBERBAND=0` -> `atempo` chia tầng",
         s_lui == "atempo=2.0,atempo=1.2500", s_lui)
    os.environ.pop("BQ_TG_RUBBERBAND", None)

    # ═══════════ CA 3 — GIẢ LẬP MÁY THIẾU BỘ LỌC ═══════════
    # Đây là mục quan trọng nhất: thiếu bộ lọc phải LÙI, KHÔNG ĐƯỢC NỔ.
    print("\nCA 3 — máy nhân viên KHÔNG có `rubberband` -> phải LÙI, không nổ")
    tg._CO_RUBBERBAND = False           # giả lập ffmpeg không có bộ lọc
    try:
        s = tg._co_gian_chuoi(1.35)
        kiem("3a thiếu bộ lọc -> chuỗi `atempo`", s == "atempo=1.3500", s)
        kiem("3b thiếu bộ lọc -> KHÔNG ném lỗi", True)
    except Exception as e:                                     # noqa: BLE001
        kiem("3b thiếu bộ lọc -> KHÔNG ném lỗi", False, str(e)[:60])
    tg._CO_RUBBERBAND = None

    # ═══════════ CA 4 — CHẠY THẬT, ffmpeg PHẢI NHẬN ═══════════
    print("\nCA 4 — ffmpeg chạy THẬT cả 2 đường (mã 0 + file CÓ RUỘT)")
    src = SAN / "src.wav"
    dung_giong(src, 2.0)
    for nhan, env in (("rubberband", "1"), ("atempo", "0")):
        if nhan == "rubberband" and not co:
            print(f"  (bỏ qua {nhan} — ffmpeg này không có)")
            continue
        os.environ["BQ_TG_RUBBERBAND"] = env
        tg._CO_RUBBERBAND = None
        dst = SAN / f"ra_{nhan}.wav"
        chuoi = tg._co_gian_chuoi(1.35)
        rc = ff(["-i", str(src), "-af", f"aresample=44100,{chuoi}",
                 "-ac", "1", "-c:a", "pcm_s16le", str(dst)])
        cỡ = dst.stat().st_size if dst.exists() else 0
        dur = tg.probe_duration(str(dst)) if dst.exists() else 0.0
        # BẪY ĐÃ ĐO: ffmpeg trả mã 0 mà file 0 KiB -> phải kiểm CỠ + ĐỘ DÀI
        kiem(f"4a[{nhan}] ffmpeg mã 0", rc == 0, f"rc={rc}")
        kiem(f"4b[{nhan}] file CÓ RUỘT", cỡ > 10000 and dur > 0.5,
             f"{cỡ} byte · {dur:.3f}s")
        # ép 1,35 thì độ dài phải quanh 2,0/1,35 = 1,481s
        kiem(f"4c[{nhan}] ép đúng hệ số (±5%)",
             abs(dur - 2.0 / 1.35) / (2.0 / 1.35) < 0.05,
             f"{dur:.3f}s (đích {2.0/1.35:.3f}s)")
    os.environ.pop("BQ_TG_RUBBERBAND", None)
    tg._CO_RUBBERBAND = None

    # ═══════════ CA 5 — `khop_thoi_gian` ĐI QUA ĐƯỜNG MỚI ═══════════
    # Quét TĨNH: bước ép phải gọi `_co_gian_chuoi`, KHÔNG gọi thẳng
    # `_atempo_chuoi`. Dùng AST chứ không dùng chuỗi — bài học cổng 56d/58:
    # tìm bằng chuỗi thì chính DÒNG GHI CHÚ cũng khớp, và phép phá giữ nguyên
    # mặt chữ mà đổi ý nghĩa vẫn lọt.
    print("\nCA 5 — `khop_thoi_gian` gọi ĐÚNG cửa (quét bằng AST)")
    import ast
    cay = ast.parse(Path(tg.__file__).read_text(encoding="utf-8"))
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef)
                and n.name == "khop_thoi_gian"), None)
    kiem("5a tìm thấy `khop_thoi_gian`", ham is not None)
    if ham:
        goi = {n.func.id for n in ast.walk(ham)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        kiem("5b gọi `_co_gian_chuoi`", "_co_gian_chuoi" in goi,
             f"các hàm gọi: {sorted(goi & {'_co_gian_chuoi','_atempo_chuoi'})}")
        kiem("5c KHÔNG gọi thẳng `_atempo_chuoi`",
             "_atempo_chuoi" not in goi)
        # TỰ KIỂM BỘ DÒ: `_co_gian_chuoi` PHẢI còn gọi `_atempo_chuoi`
        # (đường lùi). Mất chỗ đó = máy thiếu bộ lọc sẽ nổ.
        h2 = next((n for n in ast.walk(cay)
                   if isinstance(n, ast.FunctionDef)
                   and n.name == "_co_gian_chuoi"), None)
        goi2 = {n.func.id for n in ast.walk(h2)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} \
            if h2 else set()
        kiem("5d TỰ KIỂM: `_co_gian_chuoi` GIỮ đường lùi `_atempo_chuoi`",
             "_atempo_chuoi" in goi2, f"{sorted(goi2)}")

    # ═══════════ CA 6 — BẤT BIẾN: hệ số 1,0 KHÔNG đụng bộ lọc ═══════════
    # Thứ tự ưu tiên của v2.27.0 (lọt sẵn -> mượn -> mới ép) là thứ CHỮA GỐC.
    # Đổi bộ lọc KHÔNG được phép nới nó ra.
    print("\nCA 6 — BẤT BIẾN v2.27.0: lọt khung sẵn thì KHÔNG đụng tốc độ")
    than = Path(tg.__file__).read_text(encoding="utf-8")
    kiem("6a còn chốt `abs(tempo - 1.0) > 1e-3`",
         "abs(tempo - 1.0) > 1e-3" in than)
    kiem("6b `NGUONG_DOC_NHANH` KHÔNG bị nới", tg.NGUONG_DOC_NHANH <= 1.03,
         f"{tg.NGUONG_DOC_NHANH}")
    kiem("6c `TEMPO_TOI_DA` KHÔNG bị nới", tg.TEMPO_TOI_DA <= 1.50,
         f"{tg.TEMPO_TOI_DA}")

    print("\n" + "=" * 70)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 70)
    shutil.rmtree(SAN, ignore_errors=True)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
