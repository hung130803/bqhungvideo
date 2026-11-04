# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 106 (nhạc nền tự chọn): gỡ ĐÚNG MỘT chốt mỗi lượt, cổng PHẢI đỏ.

Luật: neo DUY NHẤT trong file, bản phá phải `compile()` được (không thì là lỗi
của phép thử, không phải "BẮT"); file gốc LUÔN được trả lại (finally + atexit).
CỐ Ý KHÔNG có phép "bỏ atrim": video câm + nhạc lặp vô hạn thì ffmpeg chạy
mãi — phép thử đó treo máy chứ không chứng minh gì.
"""
import atexit
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
PY = sys.executable
NT = REPO / "app" / "core" / "nhac_tu_dong.py"
FU = REPO / "app" / "core" / "ffmpeg_utils.py"

PHA = [
    ("nhạc vui được xét TRƯỚC dấu hiệu nặng", NT,
     '    for nhom, manh, yeu, ten in (',
     '    k = _dem(t, _VUI)\n    if k:\n        return "playful", "x"\n'
     '    for nhom, manh, yeu, ten in ('),
    ("nhạc chỉ dưới lời 4 dB (to quá)", NT,
     "DUOI_LOI_DB = 12.0", "DUOI_LOI_DB = 4.0"),
    ("nhạc dưới lời 20 dB (bé quá — đúng lỗi anh Hùng nghe ra)", NT,
     "DUOI_LOI_DB = 12.0", "DUOI_LOI_DB = 20.0"),
    ("bỏ né lời", NT, "    if not kh:\n        return \"\"",
     "    if True:\n        return \"\""),
    ("mẫu cũ 'off' lại thành KHÔNG nhạc", NT,
     '        return m\n    return "auto"',
     '        return m\n    return "none"'),
    ("bỏ qua lại video nền to (không còn 'mọi video có nhạc')", NT,
     'caller không bỏ qua."""\n    return ""',
     'caller không bỏ qua."""\n    return "x" if (nen_khong_noi_db or -99)'
     ' > (loi_db or 0) - 6 else ""'),
    ("bài cố định mất file thì im (không lùi tự chọn)", REPO / "app" / "ui"
     / "studio_page.py",
     "            return f if f and os.path.exists(f) else MA_TU_DONG",
     '            return f if f and os.path.exists(f) else ""'),
    ("lùi sang nhạc VUI khi thiếu bài", NT,
     '    for m in (mood, "calm"):', '    for m in (mood, "bright"):'),
    ("đường bao bỏ cửa sổ im (lỗi cũ)", FU,
     "                bao_vt.append(_SAN_IM)", "                pass"),
    ("nền dùng bpv20 cửa sổ có tiếng (lỗi cũ)", FU,
     "                _nen_kn = _bpv(list(_bao_goc), 0.20)",
     "                _nen_kn = _nen_db"),
    ("không tăng trần +6 dB", NT, "TANG_TOI_DA = 6.0", "TANG_TOI_DA = 30.0"),
    ("mức user chọn bị bỏ qua", NT, "    duoi = DUOI_LOI_DB if duoi_db is None else max(",
     "    duoi = DUOI_LOI_DB if True else max("),
    ("mức mặc định đổi khoá chống trùng", NT,
     "    if abs(d - DUOI_LOI_DB) < 0.05:\n        return MA_TU_DONG\n",
     ""),
]

_goc = {p: p.read_text("utf-8") for p in (NT, FU, REPO / "app" / "ui" / "studio_page.py")}


def _tra():
    for p, s in _goc.items():
        if p.read_text("utf-8") != s:
            p.write_text(s, "utf-8")


atexit.register(_tra)


def cong() -> int:
    try:
        return subprocess.run([PY, str(REPO / "_test_nhac_tu_dong.py")],
                              capture_output=True, cwd=str(REPO),
                              timeout=900).returncode
    except subprocess.TimeoutExpired:
        return 99


def main() -> int:
    if cong() != 0:
        print("CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ -> dừng")
        return 2
    bat = lot = khong = 0
    for ten, p, a, b in PHA:
        s = _goc[p]
        if s.count(a) != 1:
            print(f"  KHÔNG PHÁ ĐƯỢC  {ten} (neo xuất hiện {s.count(a)} lần)")
            khong += 1
            continue
        moi = s.replace(a, b)
        try:
            compile(moi, str(p), "exec")
        except SyntaxError as e:
            print(f"  KHÔNG PHÁ ĐƯỢC  {ten} (bản phá lỗi cú pháp: {e})")
            khong += 1
            continue
        try:
            p.write_text(moi, "utf-8")
            rc = cong()
        finally:
            _tra()
        if rc != 0:
            bat += 1
            print(f"  BẮT  {ten}", flush=True)
        else:
            lot += 1
            print(f"  LỌT  {ten}", flush=True)
    print(f"\nTHỬ PHÁ: BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong}")
    return 0 if lot == 0 and khong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
