# -*- coding: utf-8 -*-
"""MỔ XẺ khâu xuất clip: 61 luồng đẻ TỪ ĐÂU + 70,6 CPU-giây tiêu vào KHÂU NÀO.

    python _do_pha_xuat.py

Cách làm: chặn `ffmpeg_utils._run` để LẤY ĐÚNG 2 lệnh ffmpeg app sinh ra (pha
tách đoạn + pha dựng khung), rồi chạy LẠI từng biến thể của chính lệnh đó và
đo luồng/CPU-giây/thời gian. Không mock, không đoán.

Biến thể (mỗi cái bóc 1 lớp để biết lớp đó tốn bao nhiêu):
  goc         : y nguyên lệnh app
  khong_ass   : bỏ đốt phụ đề (libass)      -> giá của PHỤ ĐỀ
  khong_blur  : nền đen thay nền mờ         -> giá của LÀM MỜ NỀN
  chi_giai_ma : -f null, bỏ hết filter      -> giá của GIẢI MÃ
  nvdec       : -hwaccel cuda (giải mã GPU) -> giải mã đổ sang GPU được không
  luong_*     : giới hạn luồng giải mã/filter ở các mức
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_SBOX = Path(tempfile.gettempdir()) / "_do_luong_sbox"
_SBOX.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SBOX))
os.environ.setdefault("BQ_DB_PATH", str(_SBOX / "do.db"))
os.environ.setdefault("ECO_MODE", "0")

import psutil  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FF = str(REPO / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0
from _do_luong_xuat import chon_video, lam_ass, probe  # noqa: E402


# ---- CPU-giây CHÍNH XÁC: giữ HANDLE tiến trình rồi hỏi GetProcessTimes SAU
# KHI nó thoát. Lấy bằng cách lấy mẫu (psutil) là ĐẾM THIẾU: nhịp cuối cách
# lúc chết tới 50ms × 24 nhân = hụt cả CPU-giây. Handle mở sẵn giữ đối tượng
# tiến trình sống nên số liệu cuối cùng vẫn đọc được.
import ctypes                                                    # noqa: E402
from ctypes import wintypes                                      # noqa: E402

_K32 = ctypes.WinDLL("kernel32", use_last_error=True)
_PROCESS_QUERY_INFORMATION = 0x0400


def _mo_handle(pid: int):
    h = _K32.OpenProcess(_PROCESS_QUERY_INFORMATION, False, pid)
    return h or None


def _cpu_giay(h) -> float:
    """(user+kernel) giây của tiến trình — đọc được cả khi nó đã thoát."""
    ft = (wintypes.FILETIME * 4)()
    if not _K32.GetProcessTimes(h, ctypes.byref(ft[0]), ctypes.byref(ft[1]),
                                ctypes.byref(ft[2]), ctypes.byref(ft[3])):
        return -1.0
    def v(f):
        return (f.dwHighDateTime << 32 | f.dwLowDateTime) / 1e7
    return v(ft[2]) + v(ft[3])              # kernel + user


# ---- ĐỌC ENCODER THỰC (đừng sửa regex, đừng dùng IGNORECASE) ----
# LỖI THẬT 07/08/2026: file này đổ stderr vào `subprocess.DEVNULL` -> KHÔNG BAO
# GIỜ có log để đọc -> cột "enc" của mọi báo cáo do cửa này nuôi luôn ra `?`.
# Sửa regex bao nhiêu cũng vô ích: nguyên nhân là CẤU TRÚC (không có log).
#
# BẪY ĐÃ ĐO: file .mkv mezzanine mang tag `ENCODER : Lavc62.15.100 h264_nvenc`
# **CHỮ HOA** ở phần INPUT (Matroska hoa, MP4 thường). Thêm `re.IGNORECASE` là
# đọc tag của INPUT -> LUÔN báo h264_nvenc -> PASS oan, che đúng cái
# "nvenc tụt về CPU" đang đi tìm. Vì vậy 2 khuôn dưới đây CHỮ THƯỜNG, cố ý.
#   - pha 1 (không filter): `... -> h264 (h264_nvenc))`
#   - pha 2 (-filter_complex): `setsar:default -> Stream #0:0 (h264_nvenc)`
#     -> chỉ khuôn `encoder:\s*Lavc` (chữ thường) khớp.
_RE_ENC = (r"->\s*h264\s*\(([\w_]+)\)",
           r"encoder\s*:\s*Lavc[\d.]*\s+([\w_]+)",
           r"\[(h264_nvenc|libx264)\s*@")


def doc_encoder(log: str) -> str:
    """Encoder THỰC SỰ chạy, đọc từ log ffmpeg. Không có log -> '?'."""
    import re
    for pat in _RE_ENC:
        m = re.search(pat, log or "")
        if m:
            return m.group(1)
    return "?"


def chay_do(cmd: list[str], ten: str) -> dict:
    """Chạy 1 lệnh ffmpeg, đo luồng đỉnh + CPU-giây + thời gian + ENCODER THỰC.

    stderr đi vào FILE TẠM (không phải PIPE): vòng lặp lấy mẫu luồng ở đây
    không đọc pipe, ffmpeg in vài chục KB là pipe đầy -> ffmpeg TREO. File tạm
    không bao giờ đầy nên số đo wall/CPU không bị nhiễu bởi cách lấy log.
    """
    t0 = time.time()
    flog = Path(tempfile.gettempdir()) / f"_do_log_{os.getpid()}_{id(cmd)}.txt"
    with open(flog, "wb") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,
                             creationflags=_NO_WIN)
        h = _mo_handle(p.pid)
        ps = psutil.Process(p.pid)
        dinh, mau = 0, []
        while p.poll() is None:
            try:
                n = ps.num_threads()
                dinh = max(dinh, n)
                mau.append(n)
            except psutil.Error:
                break
            time.sleep(0.05)
        p.wait()
    cpu = _cpu_giay(h) if h else -1.0
    if h:
        _K32.CloseHandle(h)
    log = flog.read_text("utf-8", errors="replace")
    flog.unlink(missing_ok=True)
    return {"ten": ten, "ma": p.returncode, "giay": round(time.time() - t0, 1),
            "luong_dinh": dinh, "luong_tb": round(sum(mau) / max(1, len(mau))),
            "cpu_giay": round(cpu, 1), "enc": doc_encoder(log),
            "log_cuoi": " | ".join(log.strip().splitlines()[-2:])[:200]}


def bat_lenh(src: str, segs: list, ass: str, out: Path) -> list[list[str]]:
    """Lấy ĐÚNG các lệnh ffmpeg mà app sinh ra (không chạy thật)."""
    from app.core import ffmpeg_utils as fu
    giu: list[list[str]] = []
    that = fu._run

    def gia(cmd, on_line=None):
        giu.append(list(cmd))
        # pha 1 phải tạo ra file tạm thật thì pha 2 mới dựng được lệnh
        if "_seg_" in " ".join(cmd) and "-filter_complex" not in " ".join(cmd):
            return that(cmd, on_line)
        return 0

    fu._run = gia
    don = fu._cleanup_paths
    fu._cleanup_paths = lambda *_a, **_k: None   # GIỮ file _seg_* để chạy lại
    try:
        fu.export_canvas_clip(
            src, str(out / "bo.mp4"), segs, (0.5, 0.42, 1.0), bg="blur",
            out_w=1080, out_h=1920, ass_path=ass,
            fonts_dir=str(REPO / "app" / "assets" / "fonts"),
            blur_amt=22, fx_fade=True, fx_whoosh=True,
            join_categories=["impact"] * max(0, len(segs) - 1))
    finally:
        fu._run = that
        fu._cleanup_paths = don
    return giu


def main() -> int:
    print("═" * 70)
    print("MỔ XẺ KHÂU XUẤT CLIP — luồng đẻ từ đâu, CPU tiêu vào đâu")
    print("═" * 70)
    vid = chon_video(1)
    if not vid:
        print("không có video thật")
        return 2
    src = vid[0]
    inf = probe(src)
    print(f"  nguồn: {Path(src).name[:58]}")
    print(f"         {inf['w']}x{inf['h']} {inf['fps']:.0f}fps {inf['codec']} "
          f"{inf['dur']:.0f}s")
    out = Path(tempfile.mkdtemp(prefix="_do_pha_"))
    goc_t = max(30.0, inf["dur"] * 0.3)
    segs = [(goc_t, goc_t + 30.0), (goc_t + 70.0, goc_t + 100.0)]
    ass = lam_ass(out, segs, 1080, 1920)

    lenh = bat_lenh(src, segs, ass, out)
    print(f"\n  app sinh {len(lenh)} lệnh ffmpeg:")
    for i, c in enumerate(lenh):
        s = " ".join(c)
        pha = ("TÁCH ĐOẠN" if "_seg_" in s and "-filter_complex" not in s
               else "DỰNG KHUNG")
        print(f"    [{i}] {pha}  ({len(s)} ký tự)")
    tach = [c for c in lenh
            if "_seg_" in " ".join(c) and "-filter_complex" not in " ".join(c)]
    dung = [c for c in lenh if "-filter_complex" in " ".join(c)]
    if not dung:
        print("  KHÔNG bắt được lệnh dựng khung")
        return 2
    D = dung[0]
    print("\n  ── LỆNH DỰNG KHUNG (rút gọn) ──")
    s = " ".join(D)
    print("   ", s[:300].replace(str(out), "<tmp>"), "...")

    ra = str(out / "thu.mp4")

    def thay_out(cmd: list[str], moi: str) -> list[str]:
        c = list(cmd)
        c[-1] = moi
        return c

    def bo_filter(cmd: list[str], bo: str) -> list[str]:
        """Gỡ 1 mắt xích khỏi filter_complex (nối lại nhãn vào/ra)."""
        c = list(cmd)
        i = c.index("-filter_complex")
        parts = c[i + 1].split(";")
        giu = [p for p in parts if bo not in p]
        c[i + 1] = ";".join(giu)
        return c

    ket: list[dict] = []
    print("\n  ── CHẠY BIẾN THỂ (mỗi cái bóc 1 lớp) ──")

    # 1. gốc
    ket.append(chay_do(thay_out(D, ra), "goc"))
    print(f"    goc          : {ket[-1]}")

    # 2. bỏ phụ đề (libass) — nối [vdim/vv] thẳng sang khâu sau
    c = list(D)
    i = c.index("-filter_complex")
    g = c[i + 1]
    if "subtitles=" in g:
        parts = g.split(";")
        idx = next(k for k, p in enumerate(parts) if "subtitles=" in p)
        vao = parts[idx].split("]")[0] + "]"          # nhãn vào, vd [vv]
        rap = parts[idx].split("[")[-1]               # vsub]
        rap = "[" + rap
        parts.pop(idx)
        # nhãn ra của khâu bị bỏ -> thay bằng nhãn vào ở các khâu sau
        parts = [p.replace(rap, vao) for p in parts]
        c[i + 1] = ";".join(parts)
        ket.append(chay_do(thay_out(c, ra), "khong_ass"))
        print(f"    khong_ass    : {ket[-1]}")

    # 3. bỏ làm mờ nền (boxblur) — vẫn scale nhưng không blur
    c = list(D)
    c[i + 1] = c[i + 1].replace("boxblur=5:1,", "")
    ket.append(chay_do(thay_out(c, ra), "khong_blur"))
    print(f"    khong_blur   : {ket[-1]}")

    # 4. CHỈ GIẢI MÃ (bỏ hết filter + encode)
    j = D.index("-filter_complex")
    dec = D[:j] + ["-f", "null", "-"]
    ket.append(chay_do(dec, "chi_giai_ma"))
    print(f"    chi_giai_ma  : {ket[-1]}")

    # 5. giải mã bằng GPU (NVDEC) rồi lọc trên CPU như cũ
    c = list(D)
    c.insert(2, "cuda")
    c.insert(2, "-hwaccel")
    ket.append(chay_do(thay_out(c, ra), "nvdec"))
    print(f"    nvdec        : {ket[-1]}")

    # 6. giới hạn LUỒNG GIẢI MÃ (-threads đặt TRƯỚC -i = luồng decode)
    for n in (2, 4, 8):
        c = list(D)
        k = c.index("-i")
        c.insert(k, str(n))
        c.insert(k, "-threads")
        ket.append(chay_do(thay_out(c, ra), f"decode_threads_{n}"))
        print(f"    decode_thr {n:<2}: {ket[-1]}")

    # 7. giới hạn luồng FILTER
    for n in (2, 4):
        c = list(D)
        k = c.index("-filter_complex_threads")
        c[k + 1] = str(n)
        ket.append(chay_do(thay_out(c, ra), f"filter_threads_{n}"))
        print(f"    filter_thr {n:<2}: {ket[-1]}")

    # ---- pha TÁCH ĐOẠN
    if tach:
        T = tach[0]
        print("\n  ── PHA TÁCH ĐOẠN ──")
        seg_ra = str(out / "seg.mkv")
        ket.append(chay_do(thay_out(T, seg_ra), "tach_goc"))
        print(f"    tach_goc     : {ket[-1]}")
        c = list(T)
        k = c.index("-i")
        c.insert(k, "4")
        c.insert(k, "-threads")
        ket.append(chay_do(thay_out(c, seg_ra), "tach_decode_4"))
        print(f"    tach_dec_4   : {ket[-1]}")
        c = list(T)
        c.insert(1, "cuda")
        c.insert(1, "-hwaccel")
        ket.append(chay_do(thay_out(c, seg_ra), "tach_nvdec"))
        print(f"    tach_nvdec   : {ket[-1]}")

    print("\n" + "═" * 70)
    print(f"{'biến thể':<22}{'luồng đỉnh':>12}{'CPU-giây':>11}{'giây':>8}"
          f"{'mã':>5}{'enc THỰC':>12}")
    print("-" * 70)
    for k in ket:
        print(f"{k['ten']:<22}{k['luong_dinh']:>12}{k['cpu_giay']:>11.1f}"
              f"{k['giay']:>8.1f}{k['ma']:>5}{k.get('enc', '?'):>12}"
              + ("" if k["ma"] == 0 else f"  {k.get('log_cuoi', '')}"))
    (REPO / "_do_luong_cache" / "pha.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), "utf-8")
    import shutil
    shutil.rmtree(out, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
