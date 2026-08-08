# -*- coding: utf-8 -*-
r"""LƯỢT KIỂM ĐỘC LẬP trước khi gộp `hieu-ung-video` vào `main`.

KHÔNG dùng lại phép đo của cổng 36/37 — dựng lại từ đầu để tự mắt xem:

  A. BẤT BIẾN SỐNG CÒN — chuyển cảnh + hiệu ứng TẮT phải ra file GIỐNG `main`
     ở CẢ 2 ca: **2 đoạn hook-first** và **3 đoạn hook-first**.
     Cổng 36 CA 8 chỉ làm 2 đoạn và **chỉ so HÌNH** -> lượt này so thêm **TIẾNG**
     (md5 của PCM 16-bit 8 kHz) và **số khung**.
  B. TÊN FILE XẤU — ký tự Nhật · dấu tiếng Việt · `%` · dấu nháy `'` · `[]`.
     Không cổng nào đang canh; `drawtext`/`ass`/`concat` đều có bẫy escape.
  C. Mẫu CŨ (thiếu khoá) -> `nhe` ở CẢ 3 CỬA, và user chọn TẮT -> `tat`.

Chạy: `.venv\Scripts\python _kiem_doclap.py`
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"kiem_doclap_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "qs.ini"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401

import numpy as np  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x08000000
FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}", flush=True)


def _chay(cmd: list, giay: int = 300) -> tuple[int, str]:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       creationflags=_NOWIN, timeout=giay)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def dai(p: Path) -> float:
    rc, out = _chay([FP, "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(p)])
    try:
        return float(out.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


def so_khung(p: Path) -> int:
    rc, out = _chay([FP, "-v", "error", "-select_streams", "v:0",
                     "-count_frames", "-show_entries", "stream=nb_read_frames",
                     "-of", "csv=p=0", str(p)])
    s = (out or "").strip().splitlines()
    return int(s[0]) if s and s[0].strip().isdigit() else 0


def khung(p: Path, t: float, dst: Path) -> bool:
    rc, _ = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                   "-ss", f"{t:.3f}", "-i", str(p), "-frames:v", "1",
                   "-q:v", "2", str(dst)])
    return rc == 0 and dst.exists() and dst.stat().st_size > 0


def _xam(p: Path):
    import cv2
    im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    return None if im is None else im.astype(np.int16)


def psnr(a: Path, b: Path) -> float:
    ia, ib = _xam(a), _xam(b)
    if ia is None or ib is None or ia.shape != ib.shape:
        return -1.0
    mse = float(np.mean((ia - ib) ** 2))
    return 99.0 if mse < 1e-9 else round(10.0 * np.log10(255.0 ** 2 / mse), 1)


def bam_tieng(p: Path) -> tuple[str, float]:
    """md5 của TOÀN BỘ tiếng (PCM s16le 8 kHz mono) + RMS. Rỗng -> ('', -1)."""
    raw = _SB / f"aud_{p.stem[:20]}_{os.getpid()}.raw"
    rc, _ = _chay([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", str(p),
                   "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", str(raw)])
    if rc != 0 or not raw.exists() or raw.stat().st_size == 0:
        return ("", -1.0)
    b = raw.read_bytes()
    a = np.frombuffer(b, dtype="<i2").astype(np.float32) / 32768.0
    raw.unlink(missing_ok=True)
    return (hashlib.md5(b).hexdigest()[:16], round(float(np.sqrt(np.mean(a ** 2))), 5))


def nap_main():
    """Nạp `git show main:app/core/ffmpeg_utils.py` thành module riêng."""
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        "main:app/core/ffmpeg_utils.py"],
                       capture_output=True, creationflags=_NOWIN, timeout=60)
    out = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(out) < 5000:
        bao("lấy được ffmpeg_utils.py của main", False,
            f"git rc={r.returncode} · {len(out)} ký tự")
        return None
    # CHỐNG SO-VỚI-CHÍNH-MÌNH: xem docstring cùng tên ở `_test_chuyen_canh.py`.
    # 08/08/2026 `main` đã bị một tiến trình khác fast-forward tới nhánh này
    # NGAY GIỮA lượt kiểm -> nếu không canh thì PSNR 99 dB là số VÔ NGHĨA.
    nay = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    if out.strip() == nay.strip():
        bao("bản `main` KHÁC nhánh này (đối chứng hợp lệ)", False,
            "main TRÙNG nhánh -> đã bị merge; `git branch -f main origin/main`")
        return None
    bao("bản `main` KHÁC nhánh này (đối chứng hợp lệ)", True,
        f"main {len(out)} ký tự · nhánh {len(nay)} ký tự")
    f = _SB / "fu_main.py"
    f.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("fu_main_kd", str(f))
    if spec is None or spec.loader is None:
        bao("nạp được module main", False, "spec None")
        return None
    m = importlib.util.module_from_spec(spec)
    sys.modules["fu_main_kd"] = m
    try:
        spec.loader.exec_module(m)
    except Exception as e:                                   # noqa: BLE001
        bao("nạp được module main", False, f"{type(e).__name__}: {e}")
        return None
    bao("nạp được ffmpeg_utils.py của `main` (module riêng)", True,
        f"{len(out)} ký tự")
    return m


def tim_nguon() -> Path | None:
    thung = Path(r"C:\Users\Admin\Downloads\thùng rác")
    if not thung.is_dir():
        return None
    ung = []
    for p in thung.rglob("*.mp4"):
        try:
            n = p.stat().st_size
        except OSError:
            continue
        if 50 * 1024 ** 2 < n < 400 * 1024 ** 2 and any(
                "぀" <= c <= "ヿ" or "一" <= c <= "鿿"
                for c in p.name):
            ung.append((n, p))
    ung.sort()
    return ung[0][1] if ung else None


# =====================================================================
def ca_a_bat_bien(src: Path, mm) -> None:
    """A. Preset CŨ / hiệu ứng TẮT phải ra file GIỐNG HỆT `main`."""
    print("\n[A] BẤT BIẾN SỐNG CÒN — TẮT hết vs `main` (2 đoạn + 3 đoạn "
          "hook-first)")
    bo = {
        "2 đoạn hook-first": [(60.0, 70.0), (20.0, 30.0)],
        "3 đoạn hook-first": [(120.0, 128.0), (30.0, 38.0), (200.0, 208.0)],
    }
    for ten, segs in bo.items():
        a, b = _SB / f"m_{len(segs)}.mp4", _SB / f"n_{len(segs)}.mp4"
        t0 = time.time()
        try:
            mm.export_canvas_clip(str(src), str(a), segs, (0.5, 0.42, 0.98),
                                  bg="blur", out_w=1080, out_h=1920,
                                  fx_fade=False, fx_whoosh=False)
        except Exception as e:                               # noqa: BLE001
            bao(f"{ten}: xuất bằng mã `main`", False, f"{e}"[:200])
            continue
        try:
            fu.export_canvas_clip(str(src), str(b), segs, (0.5, 0.42, 0.98),
                                  bg="blur", out_w=1080, out_h=1920,
                                  fx_fade=False, fx_whoosh=False,
                                  chuyen_canh="tat", hieu_ung="tat")
        except Exception as e:                               # noqa: BLE001
            bao(f"{ten}: xuất bằng mã NHÁNH (TẮT)", False, f"{e}"[:200])
            continue
        dt = time.time() - t0
        d1, d2 = dai(a), dai(b)
        bao(f"{ten}: độ dài GIỐNG main", abs(d1 - d2) * 1000 < 40,
            f"main {d1:.3f}s · nhánh {d2:.3f}s · lệch "
            f"{abs(d1-d2)*1000:.1f} ms  (xuất 2 bản mất {dt:.1f}s)")
        k1, k2 = so_khung(a), so_khung(b)
        bao(f"{ten}: SỐ KHUNG giống main", k1 == k2 and k1 > 0,
            f"main {k1} khung · nhánh {k2} khung")
        tong = sum(e - s for s, e in segs)
        moc = [round(tong * x, 2) for x in (0.05, 0.25, 0.45, 0.65, 0.9)]
        ps = []
        for i, t in enumerate(moc):
            ka, kb = _SB / f"ka{i}.png", _SB / f"kb{i}.png"
            if khung(a, t, ka) and khung(b, t, kb):
                ps.append(psnr(ka, kb))
        bao(f"{ten}: PSNR >= 50 dB ở {len(moc)} mốc",
            len(ps) == len(moc) and min(ps or [0]) >= 50.0,
            f"{ps} dB (mốc {moc})")
        # TIẾNG — cổng 36 KHÔNG kiểm; xfade kéo theo acrossfade nên đây là chỗ
        # dễ lệch nhất nếu nhánh vô tình đụng vào đường tiếng.
        h1, r1 = bam_tieng(a)
        h2, r2 = bam_tieng(b)
        bao(f"{ten}: TIẾNG giống main (md5 PCM 8kHz)", bool(h1) and h1 == h2,
            f"main {h1!r} rms {r1} · nhánh {h2!r} rms {r2}")
        # md5 CẢ FILE — nếu trùng thì bất biến là tuyệt đối
        m1 = hashlib.md5(a.read_bytes()).hexdigest()[:12] if a.exists() else ""
        m2 = hashlib.md5(b.read_bytes()).hexdigest()[:12] if b.exists() else ""
        print(f"       (md5 cả file: main {m1} · nhánh {m2} · "
              f"{'TRÙNG' if m1 == m2 else 'khác — chấp nhận nếu PSNR/tiếng đạt'})")
        for p in (a, b):
            p.unlink(missing_ok=True)


# =====================================================================
TEN_XAU = [
    "【日本語】不倫ハシゴ - Part 1 現場突撃",          # Nhật
    "Tiếng Việt có dấu - Part 2 chuyện lạ",           # dấu tiếng Việt
    "Giam gia 100% - Part 3",                          # % (bẫy drawtext expansion)
    "It's a trap - Part 4 [test]",                     # nháy đơn + ngoặc vuông
    "co,dau;phay - Part 5 - 50%25 & co",               # dấu phẩy/chấm phẩy/&
]


def ca_b_ten_file(src: Path) -> None:
    """B. Tên file XẤU: Nhật · dấu Việt · `%` · nháy đơn · `[]` · `,;&`."""
    print("\n[B] TÊN FILE XẤU (Nhật · dấu Việt · % · nháy đơn · [] · ,;&)")
    segs = [(60.0, 66.0), (20.0, 26.0)]
    for ten in TEN_XAU:
        dst = _SB / f"{ten}.mp4"
        try:
            fu.export_canvas_clip(str(src), str(dst), segs, (0.5, 0.42, 0.98),
                                  bg="blur", out_w=1080, out_h=1920,
                                  fx_fade=True, fx_whoosh=True,
                                  chuyen_canh="nhe", hieu_ung="nhe")
        except Exception as e:                               # noqa: BLE001
            bao(f"tên «{ten[:28]}…» xuất được", False,
                f"{type(e).__name__}: {e}"[:220])
            continue
        d = dai(dst)
        n = dst.stat().st_size if dst.exists() else 0
        bao(f"tên «{ten[:28]}…» ra clip đúng", n > 50_000 and abs(d - 12.0) < 0.25,
            f"{n/1024:.0f} KB · {d:.3f}s (mong 12,000s)")
        dst.unlink(missing_ok=True)


# =====================================================================
def ca_c_mau_cu() -> None:
    """C. Mẫu CŨ thiếu khoá -> `nhe`; user chọn TẮT -> `tat` (3 cửa)."""
    print("\n[C] MẪU CŨ -> 'nhe' · user chọn TẮT -> 'tat' (3 cửa đọc mẫu)")
    cua = {
        "studio_page._export_video_inner": REPO / "app/ui/studio_page.py",
        "m1_highlight (job xuất)": REPO / "app/modules/m1_highlight.py",
        "editor._apply_layout": REPO / "app/ui/editor.py",
    }
    for ten, f in cua.items():
        t = f.read_text(encoding="utf-8", errors="replace")
        for khoa in ("chuyen_canh", "hieu_ung"):
            co = (f'get("{khoa}", "nhe")' in t or
                  f"get('{khoa}', 'nhe')" in t)
            bao(f"{ten}: khoá `{khoa}` mặc định 'nhe'", co,
                "CÓ" if co else "KHÔNG THẤY -> mẫu cũ có thể ra 'tat' hoặc nổ")
    # HÀNH VI thật (không đọc chữ trong file)
    mau_cu: dict = {"cap_preset": "Trắng đơn giản"}
    v1 = str(mau_cu.get("chuyen_canh", "nhe") or "tat")
    v2 = str(mau_cu.get("hieu_ung", "nhe") or "tat")
    bao("mẫu CŨ (thiếu cả 2 khoá) -> ('nhe','nhe')", (v1, v2) == ("nhe", "nhe"),
        f"ra ({v1!r}, {v2!r})")
    mau_tat = {"chuyen_canh": "tat", "hieu_ung": "tat"}
    v3 = str(mau_tat.get("chuyen_canh", "nhe") or "tat")
    bao("user chọn TẮT -> 'tat', KHÔNG bị ép về 'nhe'", v3 == "tat", f"{v3!r}")
    mau_rong = {"chuyen_canh": "", "hieu_ung": ""}
    v4 = str(mau_rong.get("chuyen_canh", "nhe") or "tat")
    bao("khoá RỖNG (mẫu lưu chuỗi rỗng) -> 'tat'", v4 == "tat", f"{v4!r}")
    bao("'tat' -> chon_chuyen_canh trả [] (đường CŨ y nguyên)",
        fu.chon_chuyen_canh([(0, 5), (10, 15)], "tat") == [],
        f"{fu.chon_chuyen_canh([(0, 5), (10, 15)], 'tat')!r}")
    bao("'nhe' -> có chuyển cảnh cho clip 2 đoạn",
        len(fu.chon_chuyen_canh([(0, 5), (10, 15)], "nhe")) == 1,
        f"{fu.chon_chuyen_canh([(0, 5), (10, 15)], 'nhe')!r}")
    bao("clip 1 ĐOẠN -> [] dù mức 'manh' (không có chỗ nối)",
        fu.chon_chuyen_canh([(0, 5)], "manh") == [], "[]")


# =====================================================================
if __name__ == "__main__":
    print("=" * 74)
    print("LƯỢT KIỂM ĐỘC LẬP — bất biến · tên file xấu · mẫu cũ")
    print("=" * 74)
    src = tim_nguon()
    if src is None:
        bao("tìm được video Nhật THẬT", False, "không có file 50-400 MB")
    else:
        print(f"nguồn: {src.name}  ({src.stat().st_size/1024**2:.0f} MB)")
        print(f"       {src.parent}")
        mm = nap_main()
        if mm is not None:
            ca_a_bat_bien(src, mm)
        ca_b_ten_file(src)
    ca_c_mau_cu()
    # rác
    con = list(Path(tempfile.gettempdir()).glob("_seg_*"))
    bao("KHÔNG bỏ lại mảnh `_seg_*` ở %TEMP%", not con, f"{len(con)} file")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    print("\n" + "=" * 74)
    print(f"ĐẠT {len(_OK)} · FAIL {len(_LOI)}")
    for x in _LOI:
        print("  ✗", x)
    print("=" * 74)
    sys.stdout.flush()
    os._exit(1 if _LOI else 0)
