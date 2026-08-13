# -*- coding: utf-8 -*-
"""CỔNG 52 — MẢNH TIẾNG CUỐI QUÁ NGẮN KHÔNG ĐƯỢC GỬI GROQ.

Chạy: .venv\\Scripts\\python _test_manh_cuoi.py

VÌ SAO CÓ CỔNG NÀY — lỗi THẬT anh Hùng gặp 09/08/2026:

    Chép lời qua Groq lỗi: Error code: 400 -
    'Audio file is too short. Minimum audio length is 0.01 seconds.'

Lời lỗi đó làm **CẢ bước chép lời thất bại** -> video không có phụ đề -> không
chọn được đoạn -> dây chuyền báo "không có Part nào được xuất".

GỐC: `_transcribe_groq` chia audio thành mảnh 600 giây bằng
`n = ceil(total / chunk)`. Audio dài 600,005 giây ra **mảnh cuối 0,005 giây**.
Chốt an toàn `os.path.getsize(part) >= 400` KHÔNG bắt được vì **riêng header
mp3 đã đủ 400 byte** -> mảnh rỗng vượt cửa rồi đi thẳng lên Groq.

CÁCH ĐO Ở ĐÂY: dựng audio THẬT ngắn (ffmpeg thật), rồi vá `_audio_duration`
để nó BÁO 600,005 giây — ép đúng ca biên mà không phải chờ cắt file 10 phút.
Vá `_groq_one` để GHI LẠI từng file được gửi, rồi `ffprobe` đo độ dài THẬT của
chính những file đó. Bất biến: **không file nào dưới 0,25 giây được gửi.**

Cùng lúc canh CHIỀU NGƯỢC (chống sửa quá tay): audio 5 giây bình thường thì
vẫn phải gửi ĐÚNG 1 mảnh — vá mà làm mất lời thì tệ hơn lỗi ban đầu.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_manh_cuoi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("GROQ_API_KEYS", "gsk_test_khong_goi_mang")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import transcribe as tr  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x0800_0000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH or "ffmpeg"
FP = settings.FFPROBE_PATH or "ffprobe"

_OK: list[str] = []
_LOI: list[str] = []


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def _dai(p: str) -> float:
    """Độ dài THẬT của file, đọc bằng ffprobe (không tin tên/kích thước)."""
    r = subprocess.run(
        [FP, "-v", "error", "-show_entries", "format=duration", "-of",
         "csv=p=0", p],
        capture_output=True, text=True, creationflags=_NOWIN, timeout=60)
    try:
        return float((r.stdout or "").strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


def _dung_audio(giay: float, dst: Path) -> bool:
    """Sinh audio THẬT bằng ffmpeg (không mock)."""
    r = subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={giay}", "-ac", "1", "-ar",
         "16000", str(dst)],
        capture_output=True, creationflags=_NOWIN, timeout=120)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 0


def _chay(bao_dai: float, src: Path) -> list:
    """Gọi `_transcribe_groq` với `_audio_duration` bị vá để BÁO `bao_dai`.

    Trả danh sách đường dẫn file mà `_groq_one` NHẬN được. `_groq_one` bị vá
    nên KHÔNG hề gọi mạng — thứ đang đo là ĐƯỜNG CHẠY (gửi gì), không phải
    Groq trả gì.
    """
    da_gui: list = []
    goc_dai, goc_one = tr._audio_duration, tr._groq_one

    def _dai_gia(*_a, **_k):
        return bao_dai

    def _one_gia(audio_path, *_a, **_k):
        da_gui.append(audio_path)
        return ([], [], "vi", "")

    tr._audio_duration = _dai_gia          # type: ignore[assignment]
    tr._groq_one = _one_gia                # type: ignore[assignment]
    try:
        tr._transcribe_groq(str(src), "vi", None)
    except Exception as e:  # noqa: BLE001
        print(f"      (ghi nhận: _transcribe_groq ném {type(e).__name__}: "
              f"{str(e)[:70]})")
    finally:
        tr._audio_duration = goc_dai       # type: ignore[assignment]
        tr._groq_one = goc_one             # type: ignore[assignment]
    return da_gui


def main() -> int:
    print("=" * 62)
    print("CỔNG 52 — MẢNH TIẾNG CUỐI QUÁ NGẮN KHÔNG ĐƯỢC GỬI GROQ")
    print("=" * 62)

    print(f"\nSÀN đang dùng trong mã: {tr._CAT_TOI_THIEU} giây")
    bao("có hằng số sàn `_CAT_TOI_THIEU`", tr._CAT_TOI_THIEU >= 0.01,
        f"{tr._CAT_TOI_THIEU} giây (Groq đòi >= 0,01)")

    src = _SB / "nguon.mp3"
    if not _dung_audio(6.0, src):
        bao("dựng được audio thật bằng ffmpeg", False, "ffmpeg lỗi")
        return 1
    bao("dựng được audio thật bằng ffmpeg", True,
        f"{_dai(str(src)):.3f} giây, {src.stat().st_size} byte")

    # ---- CA 1: ĐÚNG CA CỦA ANH HÙNG — 600,005 giây -> mảnh cuối 0,005 s ----
    print("\n[CA 1] audio BÁO 600,005 giây (mảnh cuối lẽ ra 0,005 s)")
    gui = _chay(600.005, src)
    dais = [_dai(p) for p in gui]
    print(f"      gửi {len(gui)} mảnh, độ dài THẬT: "
          f"{[f'{d:.3f}' for d in dais]}")
    qua_ngan = [d for d in dais if 0 <= d < tr._CAT_TOI_THIEU]
    bao("KHÔNG gửi mảnh nào dưới sàn", not qua_ngan,
        f"{len(qua_ngan)} mảnh dưới {tr._CAT_TOI_THIEU}s"
        + (f" (ngắn nhất {min(qua_ngan):.4f}s)" if qua_ngan else ""))
    bao("vẫn gửi mảnh ĐẦU (không bỏ sạch)", len(gui) >= 1,
        f"{len(gui)} mảnh")

    # ---- CA 2: CHIỀU NGƯỢC — audio thường KHÔNG được mất lời ----
    print("\n[CA 2] CHỐNG SỬA QUÁ TAY — audio 5 giây bình thường")
    gui2 = _chay(5.0, src)
    bao("audio ngắn bình thường vẫn gửi đúng 1 mảnh", len(gui2) == 1,
        f"{len(gui2)} mảnh")

    # ---- CA 3: TỰ KIỂM BỘ DÒ — bỏ sàn thì cổng PHẢI kêu ----
    # Không có ca này thì cổng chỉ là con dấu (bài học cổng 43 + 47).
    print("\n[CA 3] TỰ KIỂM: hạ sàn về 0 thì cổng PHẢI bắt được mảnh rỗng")
    cu = tr._CAT_TOI_THIEU
    tr._CAT_TOI_THIEU = 0.0                # type: ignore[assignment]
    try:
        gui3 = _chay(600.005, src)
        dais3 = [_dai(p) for p in gui3]
        rong = [d for d in dais3 if 0 <= d < 0.25]
        print(f"      gửi {len(gui3)} mảnh: {[f'{d:.3f}' for d in dais3]}")
        bao("bỏ sàn -> XUẤT HIỆN mảnh rỗng (bộ dò có tác dụng)", bool(rong),
            f"{len(rong)} mảnh < 0,25s"
            + (f", ngắn nhất {min(rong):.4f}s" if rong else " -> BỘ DÒ MÙ"))
    finally:
        tr._CAT_TOI_THIEU = cu             # type: ignore[assignment]

    print("\n" + "=" * 62)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for d in _LOI:
        print(f"  HỎNG: {d}")
    print("=" * 62)
    return 1 if _LOI else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(code)
