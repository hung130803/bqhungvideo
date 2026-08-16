# -*- coding: utf-8 -*-
r"""CỔNG 39 — BẢN ĐÓNG GÓI PHẢI ĐỦ TÀI NGUYÊN (máy nhân viên).

    .venv\Scripts\python _test_dong_goi.py

VÌ SAO CÓ CỔNG NÀY — LỖI THẬT tìm ra 08/08/2026 khi tổng rà soát:
`BQHungVideo.spec` khai `app/assets/fonts` + `app/assets/sfx` nhưng **QUÊN
`app/assets/hieu_ung`**. Hậu quả trên máy nhân viên (chỉ có bản `.exe`):

  · `hieu_ung/frei0r/` mất  -> `co_frei0r()` False -> kho hiệu ứng **25 -> 14**
  · `hieu_ung/gl_transitions.cl` mất -> `duong_kernel()` rỗng -> **21 chuyển
    cảnh GPU biến mất** (mức 'manh' lặng lẽ lùi về CPU)
  · `hieu_ung/shaders/` mất -> 6 shader libplacebo không dùng được
  · `hieu_ung/NGUON_GIAY_PHEP.md` mất -> **KHÔNG kèm ghi nguồn + giấy phép
    GPL/LGPL của frei0r** khi phát hành

Và app **KHÔNG BÁO MỘT DÒNG LỖI NÀO** — mọi đường đều "lùi êm". Đây đúng loại
lỗi "app vẫn chạy, test vẫn xanh, chỉ SỐ ĐO tố giác": máy anh Hùng chạy từ
NGUỒN nên đủ hiệu ứng, máy nhân viên chạy `.exe` thì thiếu, mà không ai biết.

CỔNG NÀY LÀM 2 VIỆC:
  A. QUÉT TĨNH — mọi thư mục `app/assets/*` mà MÃ NGUỒN có đọc thì spec phải
     khai. Thêm thư mục tài nguyên mới mà quên spec là FAIL ngay.
  B. KIỂM BẢN ĐÃ BUILD (nếu có `dist/BQHungVideo`) — đếm file thật trong
     `_internal/app/assets/...` và so với nguồn; kiểm ngày sửa `.exe` để không
     sập lại bẫy 06/08/2026 ("dist/ còn bản cũ mà tưởng đã build").
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


SPEC = REPO / "BQHungVideo.spec"
CI = REPO / ".github" / "workflows" / "release.yml"
ASSETS = REPO / "app" / "assets"


def spec_datas() -> str:
    """Gộp CẢ HAI cửa đóng gói.

    QUAN TRỌNG: `BQHungVideo.spec` bị `.gitignore` (dòng 40 `*.spec`) nên nó
    CHỈ dùng để build TAY trên máy anh Hùng. Bản mà **máy nhân viên tự cập
    nhật** do `.github/workflows/release.yml` build bằng `--add-data` rời.
    Sửa spec mà quên release.yml = máy nhân viên vẫn thiếu. Cổng phải soi CẢ HAI.
    """
    t = ""
    for p in (SPEC, CI):
        try:
            t += p.read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            pass
    return t


# =====================================================================
def ca_a_quet_tinh() -> None:
    """Mọi thư mục app/assets/* MÃ CÓ ĐỌC đều phải nằm trong spec."""
    print("\n[CA A] 2 cửa đóng gói có khai đủ tài nguyên app/assets/* không?")
    print(f"  cửa 1 (build tay)   : {SPEC.name} "
          f"{'CÓ' if SPEC.exists() else 'KHÔNG CÓ'}")
    print(f"  cửa 2 (PHÁT HÀNH)   : .github/workflows/{CI.name} "
          f"{'CÓ' if CI.exists() else 'KHÔNG CÓ'}  << máy nhân viên lấy bản này")
    txt = spec_datas()
    # mỗi cửa phải khai RIÊNG — sửa 1 cửa không cứu được cửa kia
    for nhan, p in (("build tay (.spec)", SPEC), ("PHÁT HÀNH (release.yml)", CI)):
        if not p.exists():
            continue
        t1 = p.read_text(encoding="utf-8", errors="replace")
        bao(f"{nhan} khai app/assets/hieu_ung",
            "app/assets/hieu_ung" in t1,
            "CÓ" if "app/assets/hieu_ung" in t1 else
            "THIẾU -> mất 25 hiệu ứng + 21 chuyển cảnh GPU + giấy phép GPL")
    thu_muc = sorted(p.name for p in ASSETS.iterdir() if p.is_dir())
    print(f"  thư mục tài nguyên trong nguồn: {thu_muc}")
    thieu = []
    for ten in thu_muc:
        # mã nguồn có nhắc tới thư mục này không (tức app ĐỌC nó lúc chạy)?
        co_doc = False
        for py in (REPO / "app").rglob("*.py"):
            try:
                if f'"{ten}"' in py.read_text(encoding="utf-8", errors="replace") \
                        or f"'{ten}'" in py.read_text(encoding="utf-8", errors="replace"):
                    co_doc = True
                    break
            except OSError:
                pass
        if not co_doc:
            continue
        if f"app/assets/{ten}" not in txt and f"app\\\\assets\\\\{ten}" not in txt:
            thieu.append(ten)
    bao("spec khai ĐỦ mọi thư mục app/assets mã có đọc",
        not thieu, f"thiếu {thieu}" if thieu else f"đủ {len(thu_muc)} thư mục")

    # 4 tài nguyên SỐNG CÒN của hiệu ứng — nêu đích danh, đừng để lùi êm
    from app.core import hieu_ung as HU
    from app.core import hieu_ung_gpu as GPU
    can = {
        "frei0r (25 hiệu ứng)": HU.thu_muc_frei0r(),
        "kernel gl-transitions (21 chuyển cảnh GPU)": Path(GPU.duong_kernel() or "x"),
        "shader libplacebo": Path(GPU.thu_muc_shader() or "x"),
        "NGUON_GIAY_PHEP.md (giấy phép GPL frei0r)":
            ASSETS / "hieu_ung" / "NGUON_GIAY_PHEP.md",
    }
    for ten, p in can.items():
        bao(f"NGUỒN có {ten}", Path(p).exists(), str(p).replace(str(REPO), "."))
    bao("spec khai app/assets/hieu_ung (frei0r + kernel GPU + shader + giấy phép)",
        "app/assets/hieu_ung" in txt,
        "CÓ" if "app/assets/hieu_ung" in txt else
        "THIẾU -> máy nhân viên mất 25 hiệu ứng + 21 chuyển cảnh GPU")

    # ---- LICENSES.txt: NGHĨA VỤ PHÁP LÝ, không phải tài liệu cho đẹp ----
    # `bin/ffmpeg.exe` kèm bộ cài là bản `--enable-gpl --enable-version3`
    # (GPL-3.0-or-later, có librubberband GPL-2.0). GPL BUỘC người phát hành
    # kèm văn bản giấy phép + chỉ chỗ lấy mã nguồn. Bộ cài trước 16/08/2026
    # THIẾU hẳn — app vẫn chạy, không một dòng báo, chỉ có rủi ro pháp lý.
    lic = REPO / "LICENSES.txt"
    bao("NGUỒN có LICENSES.txt", lic.exists(), str(lic).replace(str(REPO), "."))
    for nhan, p in (("build tay (.spec)", SPEC),
                    ("PHÁT HÀNH (release.yml)", CI)):
        if not p.exists():
            continue
        t1 = p.read_text(encoding="utf-8", errors="replace")
        bao(f"{nhan} khai LICENSES.txt", "LICENSES.txt" in t1,
            "CÓ" if "LICENSES.txt" in t1 else
            "THIẾU -> phát hành ffmpeg GPL mà không kèm giấy phép")
    if lic.exists():
        t_lic = lic.read_text(encoding="utf-8", errors="replace")
        # Nêu ĐÍCH DANH từng thành phần bắt buộc. Chỉ hỏi "file có tồn tại
        # không" thì ai đó để lại file rỗng là cổng vẫn xanh.
        can_co = {
            "ffmpeg (GPL-3.0)": ("ffmpeg", "GPL-3.0"),
            "rubberband": ("rubberband",),
            "Piper + kho mã nguồn": ("piper1-gpl",),
            "espeak-ng": ("espeak-ng",),
            "giọng vais1000 + CC BY 4.0": ("vais1000", "CC BY 4.0"),
            "edge-tts (LGPL)": ("edge-tts", "LGPL"),
        }
        thieu_m = [ten for ten, khoa in can_co.items()
                   if not all(k.lower() in t_lic.lower() for k in khoa)]
        bao("LICENSES.txt nêu ĐỦ thành phần bắt buộc", not thieu_m,
            f"thiếu {thieu_m}" if thieu_m
            else f"đủ {len(can_co)} mục · {len(t_lic)} ký tự")


# =====================================================================
def ca_b_ban_da_build() -> None:
    """Nếu có dist/ thì kiểm bản build THẬT (đếm file + ngày sửa .exe)."""
    print("\n[CA B] bản đã build trong dist/ (bỏ qua nếu chưa build)")
    d = REPO / "dist" / "BQHungVideo"
    exe = d / "BQHungVideo.exe"
    if not exe.exists():
        print("  (chưa có dist/BQHungVideo/BQHungVideo.exe — bỏ qua)")
        return
    tuoi = (time.time() - exe.stat().st_mtime) / 86400.0
    print(f"  .exe sửa lần cuối: "
          f"{time.strftime('%d/%m/%Y %H:%M', time.localtime(exe.stat().st_mtime))} "
          f"({tuoi:.1f} ngày trước)")
    noi = d / "_internal" / "app" / "assets"
    for ten in ("fonts", "sfx", "hieu_ung"):
        goc = ASSETS / ten
        if not goc.is_dir():
            continue
        n_goc = sum(1 for p in goc.rglob("*") if p.is_file())
        n_dist = sum(1 for p in (noi / ten).rglob("*") if p.is_file()) \
            if (noi / ten).is_dir() else 0
        bao(f"dist có ĐỦ app/assets/{ten}", n_dist >= n_goc,
            f"nguồn {n_goc} file · dist {n_dist} file")
    # bẫy 06/08/2026: build hỏng mà dist/ còn bản cũ -> .exe già hơn mã nguồn
    moi_nhat = max((p.stat().st_mtime for p in (REPO / "app").rglob("*.py")),
                   default=0)
    bao(".exe MỚI HƠN mã nguồn (không phải bản build cũ còn sót)",
        exe.stat().st_mtime >= moi_nhat,
        f".exe {time.strftime('%d/%m %H:%M', time.localtime(exe.stat().st_mtime))} "
        f"vs mã {time.strftime('%d/%m %H:%M', time.localtime(moi_nhat))}")


# =====================================================================
if __name__ == "__main__":
    print("=" * 74)
    print("CỔNG 39 — BẢN ĐÓNG GÓI PHẢI ĐỦ TÀI NGUYÊN")
    print("=" * 74)
    ca_a_quet_tinh()
    ca_b_ban_da_build()
    print("\n" + "=" * 74)
    print(f"ĐẠT {len(_OK)} · FAIL {len(_LOI)}")
    for x in _LOI:
        print("  ✗", x)
    print("=" * 74)
    sys.stdout.flush()
    os._exit(1 if _LOI else 0)
