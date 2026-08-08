# -*- coding: utf-8 -*-
r"""TỔNG RÀ SOÁT — MỤC "MÁY NHÂN VIÊN" (anh Hùng nhấn mạnh 08/08/2026).

    .venv-build\Scripts\python.exe _ra_may_nhanvien.py

CHẠY BẰNG **VENV KHÁCH** (`requirements-build.txt`) — đúng bộ thư viện mà bản
`.exe` gói cho máy nhân viên: **KHÔNG có opencv / torch / whisper / mediapipe**.

3 câu hỏi phải trả lời bằng SỐ:
  1. App **nạp được** trên venv khách không (thiếu cv2 có nổ ImportError không)?
  2. Thiếu **NVENC** / thiếu **frei0r** / thiếu **OpenCL+Vulkan** thì kho hiệu
     ứng có **tự co** và **vẫn xuất đúng** không, hay **nổ lỗi**?
  3. Xuất THẬT ở cấu hình máy yếu nhất (libx264, không frei0r, không GPU) ra
     clip **đúng độ dài, đúng số khung, không 0-byte** không?

BẪY ĐÃ SẬP (cổng 37, đừng lặp):
  · `thu_muc_frei0r()` trả **Path**, stub trả `str` -> `AttributeError` giả.
  · phải xoá **CẢ 2** chỗ nhớ `_F0R_OK` **và** `_MOD_CACHE`, không thì đọc kết
    quả lần đo trước rồi **PASS OAN**.
  · đếm ffmpeg theo `p.name()`, **KHÔNG theo cmdline**.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="ra_mnv_"))
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "settings.ini"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_NOWIN = 0x08000000
_LOI: list[str] = []
_OK: list[str] = []
_SO: dict = {}


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def main() -> int:
    print("=" * 76)
    print("MÁY NHÂN VIÊN — venv khách (requirements-build.txt)")
    print("=" * 76)
    print(f"python  : {sys.version.split()[0]}  ({sys.executable})")

    # ---- 1. thư viện: đúng bộ khách chứ không phải venv dev ----
    thieu = []
    for m in ("cv2", "torch", "mediapipe", "faster_whisper"):
        try:
            __import__(m)
        except Exception:      # noqa: BLE001
            thieu.append(m)
    bao("venv khách ĐÚNG là bộ rút gọn (không cv2/torch/mediapipe/whisper)",
        len(thieu) == 4, f"thiếu {thieu}")
    _SO["thu_vien_thieu"] = thieu

    # ---- 2. app nạp được không ----
    try:
        import app.queue.jobs  # noqa: F401
        from app.core import ffmpeg_utils as fu
        from app.core import hieu_ung as HU
        from app.core import hieu_ung_gpu as GPU
        import app.ui.studio_page  # noqa: F401
        import main  # noqa: F401
        bao("app NẠP ĐƯỢC trên venv khách (thiếu cv2 vẫn không nổ)", True,
            "app.queue.jobs + ffmpeg_utils + hieu_ung + studio_page + main")
    except Exception as e:      # noqa: BLE001
        bao("app NẠP ĐƯỢC trên venv khách", False, f"{type(e).__name__}: {e}")
        return 1

    from config import settings
    FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH

    print(f"\n  encoder máy này    : {fu.detect_encoder()}")
    print(f"  ffmpeg song song   : {fu.so_ffmpeg_song_song()}")
    print(f"  luồng giải mã      : {fu.decode_threads()}")
    print(f"  frei0r có sẵn      : {HU.co_frei0r()}")
    kho_day = HU.dung_duoc()
    print(f"  kho hiệu ứng ĐẦY ĐỦ: {len(kho_day)} / {len(HU.KHO)} trong kho")
    print(f"  chuyển cảnh GPU    : {len(GPU.dung_duoc())} kiểu "
          f"(OpenCL {GPU.co_opencl()})")
    _SO["kho_day"] = len(kho_day)
    _SO["gpu_day"] = len(GPU.dung_duoc())

    # ================= 3. GIẢ LẬP MÁY NHÂN VIÊN =================
    print("\n── (a) THIẾU frei0r ──")
    goc_tm, goc_ok = HU.thu_muc_frei0r, HU._F0R_OK
    goc_mod = dict(HU._MOD_CACHE)
    try:
        # BẪY: phải trả **Path**, và phải xoá CẢ `_F0R_OK` lẫn `_MOD_CACHE`
        HU.thu_muc_frei0r = lambda: _SB / "khong_co_frei0r"   # type: ignore
        HU._F0R_OK = None
        HU._MOD_CACHE.clear()
        kho_co = HU.dung_duoc()
        bao("thiếu frei0r -> kho hiệu ứng TỰ CO mà KHÔNG rỗng, KHÔNG nổ",
            0 < len(kho_co) < len(kho_day),
            f"{len(kho_day)} -> {len(kho_co)} hiệu ứng")
        bao("thiếu frei0r -> co_frei0r()=False và NÊU ĐƯỢC lý do",
            HU.co_frei0r() is False and bool(HU.ly_do_khong_co_frei0r()),
            HU.ly_do_khong_co_frei0r()[:90])
        _SO["kho_thieu_frei0r"] = len(kho_co)
    finally:
        HU.thu_muc_frei0r = goc_tm       # type: ignore[assignment]
        HU._F0R_OK = goc_ok
        HU._MOD_CACHE.clear()
        HU._MOD_CACHE.update(goc_mod)

    print("\n── (b) THIẾU OpenCL + Vulkan ──")
    goc_co = dict(GPU._CO)
    try:
        GPU._CO["opencl"] = False
        GPU._CO["vulkan"] = False
        ds = GPU.dung_duoc()
        bao("thiếu OpenCL+Vulkan -> nhóm chuyển cảnh GPU TẮT HẲN (trả rỗng)",
            ds == [], f"{len(ds)} kiểu GPU")
        # và phải LÙI ÊM sang kiểu CPU, không ném lỗi: mọi khoá GPU trong kho
        # phải tra ra được 1 kiểu xfade CPU tương ứng
        thieu_lui = [k for k in GPU.KHO_GPU if k not in fu.GPU_LUI_VE]
        bao("mọi kiểu GPU đều có ĐƯỜNG LÙI về xfade CPU (không kẹt)",
            not thieu_lui,
            f"{len(fu.GPU_LUI_VE)} kiểu có đường lùi · thiếu {thieu_lui[:5]}")
        _SO["gpu_khi_thieu_opencl"] = len(ds)
        _SO["gpu_lui_ve"] = len(fu.GPU_LUI_VE)
    finally:
        GPU._CO.clear()
        GPU._CO.update(goc_co)

    print("\n── (c) THIẾU NVENC: xuất THẬT bằng libx264 + chuyển cảnh + hiệu ứng ──")
    src = _SB / "nguon.mp4"
    subprocess.run(
        [FF, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=20",
         "-f", "lavfi", "-i", "sine=f=440:r=48000:d=20",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest",
         str(src)], capture_output=True, timeout=300, creationflags=_NOWIN)

    goc_enc = fu.detect_encoder
    goc_f0r = HU.thu_muc_frei0r
    goc_ok2, goc_mod2 = HU._F0R_OK, dict(HU._MOD_CACHE)
    goc_co2 = dict(GPU._CO)
    out = _SB / "may_yeu.mp4"
    try:
        # máy yếu nhất: không NVENC + không frei0r + không GPU, cùng lúc
        fu.detect_encoder = lambda *a, **k: "libx264"     # type: ignore
        HU.thu_muc_frei0r = lambda: _SB / "khong_co_frei0r"  # type: ignore
        HU._F0R_OK = None
        HU._MOD_CACHE.clear()
        GPU._CO["opencl"] = False
        GPU._CO["vulkan"] = False
        fu.export_canvas_clip(
            str(src), str(out), [(2.0, 8.0), (12.0, 18.0)],
            (0.5, 0.42, 0.98), bg="blur", out_w=1080, out_h=1920,
            fx_fade=True, fx_whoosh=True,
            chuyen_canh="manh", hieu_ung="manh")   # mức NẶNG NHẤT
    except Exception as e:      # noqa: BLE001
        bao("máy yếu nhất (libx264 + 0 frei0r + 0 GPU) xuất được", False,
            f"{type(e).__name__}: {e}")
    finally:
        fu.detect_encoder = goc_enc       # type: ignore[assignment]
        HU.thu_muc_frei0r = goc_f0r       # type: ignore[assignment]
        HU._F0R_OK = goc_ok2
        HU._MOD_CACHE.clear()
        HU._MOD_CACHE.update(goc_mod2)
        GPU._CO.clear()
        GPU._CO.update(goc_co2)

    if out.exists():
        r = subprocess.run(
            [FP, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], capture_output=True, text=True,
            creationflags=_NOWIN, timeout=60)
        try:
            dai = float((r.stdout or "0").strip().splitlines()[0])
        except (ValueError, IndexError):
            dai = -1.0
        rk = subprocess.run(
            [FP, "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0",
             str(out)], capture_output=True, text=True,
            creationflags=_NOWIN, timeout=300)
        try:
            khung = int((rk.stdout or "0").strip().splitlines()[0])
        except (ValueError, IndexError):
            khung = -1
        rt = subprocess.run(
            [FP, "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", str(out)],
            capture_output=True, text=True, creationflags=_NOWIN, timeout=60)
        kb = out.stat().st_size
        bao("máy yếu nhất -> clip ĐÚNG ĐỘ DÀI 12,000s (lệch < 80ms)",
            abs(dai - 12.0) < 0.08, f"{dai:.3f}s")
        bao("máy yếu nhất -> clip CÓ KHUNG THẬT (không phải file rỗng)",
            khung > 300, f"{khung} khung")
        bao("máy yếu nhất -> clip KHÔNG 0-byte và CÒN TIẾNG",
            kb > 10000 and "audio" in (rt.stdout or ""),
            f"{kb/1024:.0f} KB · tiếng {'CÓ' if 'audio' in (rt.stdout or '') else 'MẤT'}")
        _SO["may_yeu"] = {"dai_s": round(dai, 3), "khung": khung, "kb": kb // 1024}
    else:
        bao("máy yếu nhất -> có ra file", False, "KHÔNG có file đích")

    # ---- 4. rác + ffmpeg mồ côi ----
    import psutil
    tmp = Path(tempfile.gettempdir())
    rac = [p.name for p in tmp.glob("_seg_*")] + [p.name for p in tmp.glob("_nhip_*")]
    mo_coi = sum(1 for p in psutil.process_iter(["name"])
                 if (p.info["name"] or "").lower() in ("ffmpeg.exe", "ffmpeg"))
    bao("không để lại rác _seg_* / _nhip_* ở %TEMP%", not rac, f"{len(rac)} file")
    bao("không bỏ lại ffmpeg mồ côi", mo_coi == 0, f"{mo_coi} tiến trình")

    print("\n" + "=" * 76)
    print(f"ĐẠT {len(_OK)} · FAIL {len(_LOI)}")
    for x in _LOI:
        print("  ✗", x)
    print("=" * 76)
    _SO["ok"] = len(_OK)
    _SO["fail"] = len(_LOI)
    _SO["python"] = sys.version.split()[0]
    (REPO / "_ket__ra_may_nhanvien.json").write_text(
        json.dumps(_SO, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    sys.stdout.flush()
    os._exit(1 if _LOI else 0)


if __name__ == "__main__":
    sys.exit(main())
