# -*- coding: utf-8 -*-
r"""ĐO RÒ MẢNH `_seg_*` KHI XUẤT LỖI / BỊ HUỶ (việc 1).

Chạy: .venv\Scripts\python _do_ro_seg.py
Env BẮT BUỘC: BQ_FFMPEG_SLOTS=1 (máy anh Hùng đang làm việc thật — 1 ffmpeg).

Dựng đúng 2 ca đã thấy trên máy user rồi ĐẾM file + MB còn lại trong %TEMP%:
  A. HUỶ giữa lúc xuất, kill ffmpeg kiểu ứng dụng thật (`kill()` KHÔNG chờ).
  B. LỖI ở pha "2n-1 mảnh" -> app lùi đường "nối cả clip"; mảnh của lượt hỏng
     bị `del temps[:]` gỡ khỏi sổ nên caller không còn đường nào dọn.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"do_roseg_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu  # noqa: E402
from app.queue import worker as W  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x08000000
TMP = Path(tempfile.gettempdir())


def rac() -> set:
    return {p.name for p in TMP.glob("_seg_*")}


def mb(names) -> float:
    t = 0
    for n in names:
        try:
            t += (TMP / n).stat().st_size
        except OSError:
            pass
    return t / 1e6


def nguon(ten: str, giay: float) -> Path:
    p = _SB / ten
    if p.exists():
        return p
    subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=30:d={giay:g}",
         "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={giay:g}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest",
         str(p)], capture_output=True, timeout=300, creationflags=_NOWIN)
    return p


def ca_huy() -> None:
    print("\n[A] HUỶ giữa lúc xuất (kill ffmpeg như app thật, KHÔNG chờ)")
    src = nguon("a.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    out = _SB / "a_out.mp4"
    truoc = rac()
    goc = W.current_job_canceled
    co_huy = threading.Event()
    W.current_job_canceled = lambda: co_huy.is_set()   # type: ignore[assignment]
    ket: dict = {}

    def chay() -> None:
        try:
            fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                                  out_w=540, out_h=960, encoder="libx264",
                                  chuyen_canh="vua")
            ket["e"] = None
        except Exception as ex:                          # noqa: BLE001
            ket["e"] = ex

    t = threading.Thread(target=chay, daemon=True)
    t.start()
    time.sleep(1.6)
    # KILL đúng kiểu app: cancel() gọi kill_job_procs -> p.kill() KHÔNG chờ
    with fu._PROC_LOCK:
        procs = list(fu._ACTIVE_PROCS)
    co_huy.set()
    for p in procs:
        try:
            if p.poll() is None:
                p.kill()
        except OSError:
            pass
    t.join(timeout=120)
    W.current_job_canceled = goc                        # type: ignore[assignment]
    sot = sorted(rac() - truoc)
    print(f"    ném: {type(ket.get('e')).__name__} · "
          f"SÓT {len(sot)} file / {mb(sot):.1f} MB")
    for s in sot[:8]:
        print(f"      · {s}")
    return


def ca_loi_pha_2n1() -> None:
    print("\n[B] LỖI ở pha '2n-1 mảnh' -> lùi 'nối cả clip'")
    src = nguon("b.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    out = _SB / "b_out.mp4"
    truoc = rac()
    goc = fu._tach_va_noi_manh
    dem = {"n": 0}

    def hong(*a, **k):
        """Tạo mảnh THẬT rồi mới ném (đúng cảnh mảnh chuyển cảnh ra 0 khung)."""
        temps = a[9] if len(a) > 9 else k.get("temps")
        goc_run = fu._run_with_fallback
        try:
            goc(*a, **k)
        except Exception:
            pass
        finally:
            fu._run_with_fallback = goc_run
        dem["n"] += 1
        raise RuntimeError("mảnh chuyển cảnh ra 0 khung (mô phỏng)")

    fu._tach_va_noi_manh = hong                          # type: ignore[assignment]
    try:
        fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="vua")
        e = None
    except Exception as ex:                              # noqa: BLE001
        e = ex
    finally:
        fu._tach_va_noi_manh = goc                       # type: ignore[assignment]
    sot = sorted(rac() - truoc)
    print(f"    lùi {dem['n']} lần · ném: {type(e).__name__ if e else 'không'} · "
          f"SÓT {len(sot)} file / {mb(sot):.1f} MB")
    for s in sot[:8]:
        print(f"      · {s}")


def ca_khoa_file() -> None:
    """Mảnh còn BỊ KHOÁ đúng lúc dọn -> `_cleanup_dst` nuốt PermissionError."""
    print("\n[C] File tạm ĐANG BỊ KHOÁ lúc dọn")
    p = TMP / f"_seg_khoa{os.getpid()}_0.mkv"
    p.write_bytes(b"x" * 4096)
    fh = open(p, "rb")
    try:
        fu._cleanup_paths([str(p)])
        print(f"    sau _cleanup_paths: còn tồn tại = {p.exists()}")
    finally:
        fh.close()
        try:
            p.unlink()
        except OSError:
            pass


def _cua_so_khoa(giay: float):
    """Mô phỏng ĐÚNG hành vi Windows: file `_seg_*` vừa bị kill thì KHÔNG xoá
    được trong `giay` giây đầu (PermissionError), sau đó xoá được.

    Không mock ffmpeg — chỉ dựng lại cửa sổ khoá của HỆ ĐIỀU HÀNH, đúng thứ
    `_cleanup_dst` đang nuốt im lặng."""
    goc = Path.unlink
    het = time.time() + giay

    def vaunlink(self, missing_ok=False):
        if "_seg_" in self.name and time.time() < het:
            raise PermissionError(32, "The process cannot access the file")
        return goc(self, missing_ok=missing_ok)

    Path.unlink = vaunlink                              # type: ignore[assignment]
    return goc


def ca_khoa_2giay() -> None:
    """CA THẬT: xuất LỖI trong lúc mảnh còn bị khoá 2 giây (như vừa kill ffmpeg)."""
    print("\n[D] XUẤT LỖI + mảnh còn bị KHOÁ 2 giây (cửa sổ Windows thật)")
    src = nguon("d.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    truoc = rac()
    xau = _SB / "la_thu_muc_d.mp4"
    xau.mkdir(exist_ok=True)
    goc_unlink = _cua_so_khoa(2.0)
    try:
        fu.export_canvas_clip(src, xau, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="vua")
        e = None
    except Exception as ex:                              # noqa: BLE001
        e = ex
    finally:
        Path.unlink = goc_unlink                         # type: ignore[assignment]
    time.sleep(2.5)                                      # hết cửa sổ khoá
    sot = sorted(rac() - truoc)
    print(f"    ném: {type(e).__name__ if e else 'không'} · "
          f"SÓT {len(sot)} file / {mb(sot):.1f} MB")
    for s in sot[:8]:
        try:
            kb = (TMP / s).stat().st_size // 1024
        except OSError:
            kb = -1
        print(f"      · {s}  ({kb} KB)")
    for s in sot:                       # dọn tay để lần đo sau sạch
        try:
            (TMP / s).unlink()
        except OSError:
            pass


if __name__ == "__main__":
    print(f"ffmpeg: {settings.FFMPEG_PATH} · cửa chờ = "
          f"{fu.so_ffmpeg_song_song()} chỗ")
    ca_huy()
    ca_loi_pha_2n1()
    ca_khoa_file()
    ca_khoa_2giay()
    con = sorted(rac())
    print(f"\nTỔNG `_seg_*` còn trong %TEMP%: {len(con)} file / "
          f"{mb(con):.1f} MB")
