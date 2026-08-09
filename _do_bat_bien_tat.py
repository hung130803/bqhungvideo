# -*- coding: utf-8 -*-
"""BẤT BIẾN SỐNG CÒN: mức "tat" phải ra file GIỐNG HỆT bản cũ (PSNR >= 50 dB).

=== VÌ SAO PHẢI CÓ FILE NÀY, KHÔNG DÙNG THẲNG CỔNG `_test_chuyen_canh.py` ===
CA 8 của cổng đó so `app/core/ffmpeg_utils.py` giữa mốc cũ và nhánh này, kèm
chốt chặn "so-với-chính-mình": hai bản TRÙNG NHAU thì nó FAIL (đúng — sinh ra
để bắt ca `main` bị fast-forward, xem `CLAUDE.md`).

Lượt "mở rộng kho" 09/08/2026 KHÔNG đụng `ffmpeg_utils.py` một dòng nào; nó đụng
`app/core/hieu_ung.py` + `app/core/hieu_ung_gpu.py`. Nên với mốc `7b1da35`:
  · CA 8 thấy `ffmpeg_utils.py` TRÙNG -> FAIL "so-với-chính-mình" (đúng luật
    của nó, nhưng KHÔNG đo được cái đang thay đổi);
  · còn thứ THẬT SỰ cần chứng minh — "kho phình từ 27 lên 43 kiểu mà mức Tắt
    vẫn ra file y hệt" — thì không ai kiểm.
File này bịt đúng khoảng trống đó: nạp `hieu_ung.py`/`hieu_ung_gpu.py` CỦA MỐC
CŨ thành module, THAY vào `sys.modules`, xuất; rồi trả module thật về, xuất lại;
so PSNR 2 file. Cùng cách CA 8 làm, chỉ khác chỗ nó soi.

CHẠY:
    .venv\\Scripts\\python _do_bat_bien_tat.py [--moc 7b1da35]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"bat_bien_tat_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore
    except (AttributeError, ValueError):
        pass

from config import settings                      # noqa: E402

FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH
_NOWIN = 0x08000000 if os.name == "nt" else 0
W, H, FPS = 1080, 1920, 30
_LOI: list = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    if not ok:
        _LOI.append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def _nap_moc(moc: str, ten_mod: str, duong: str):
    """Nạp 1 file .py CỦA MỐC CŨ thành module rời và cắm vào `sys.modules`.

    Phải cắm vào `sys.modules` với ĐÚNG tên gói (`app.core.hieu_ung`), vì
    `ffmpeg_utils` import TRỄ bằng `from app.core import hieu_ung` — cắm tên
    khác thì nó vẫn lấy bản MỚI và phép so tự PASS OAN.
    """
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{moc}:{duong}"],
                       capture_output=True, creationflags=_NOWIN, timeout=60)
    src = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(src) < 2000:
        raise RuntimeError(f"không lấy được {duong} của {moc}: "
                           f"rc={r.returncode} · {len(src)} ký tự")
    f = _SB / f"{ten_mod.replace('.', '_')}_cu.py"
    f.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(ten_mod, str(f))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"spec None cho {ten_mod}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[ten_mod] = m
    spec.loader.exec_module(m)
    # === CHỈ THAY `sys.modules` LÀ CHƯA ĐỦ — bản đầu file này đã PASS OAN ===
    # `ffmpeg_utils` lấy module bằng `from app.core import hieu_ung`, mà cú pháp
    # đó tra THUỘC TÍNH trên gói `app.core` TRƯỚC khi ngó `sys.modules`. Gói đã
    # nạp một lần rồi nên thuộc tính vẫn trỏ bản MỚI -> "bản cũ" chưa bao giờ
    # được dùng, PSNR ra inf vì so bản mới với chính nó.
    # Ca tự kiểm "kho cũ phải < 40 kiểu" chính là thứ tố giác việc này (nó in
    # ra `kho cũ 43 kiểu`). Giữ ca đó lại — không có nó thì cổng là con dấu.
    goi, _, ten_con = ten_mod.rpartition(".")
    if goi and goi in sys.modules:
        setattr(sys.modules[goi], ten_con, m)
    return m, src


def nguon() -> str:
    """8 giây phim THẬT, đúng khung dọc 1080x1920."""
    dst = str(_SB / "goc.mp4")
    cand = []
    for thu in (Path("D:/video test/Đã tải"),
                Path(r"C:\Users\Admin\Downloads\thùng rác")):
        if thu.is_dir():
            cand += sorted((p for p in thu.iterdir()
                            if p.suffix.lower() in (".mp4", ".mkv", ".webm")),
                           key=lambda p: p.stat().st_size)[:4]
    for p in cand:
        r = subprocess.run(
            [FF, "-y", "-v", "error", "-ss", "120", "-t", "8", "-i", str(p),
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", "-b:a", "96k", dst],
            capture_output=True, creationflags=_NOWIN, timeout=600)
        if r.returncode == 0 and os.path.exists(dst):
            print(f"  [nguồn] {p.name[:50]} @120s")
            return dst
    raise RuntimeError("không có video thật để đo (quy tắc sắt: cấm mock)")


def psnr(a: str, b: str) -> float:
    r = subprocess.run(
        [FF, "-v", "info", "-i", a, "-i", b, "-lavfi",
         "[0:v][1:v]psnr", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace",
        creationflags=_NOWIN, timeout=900)
    m = re.search(r"average:(inf|[\d.]+)", (r.stderr or "") + (r.stdout or ""))
    if not m:
        return -1.0
    return 999.0 if m.group(1) == "inf" else float(m.group(1))


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", p], capture_output=True,
                       creationflags=_NOWIN, timeout=600)
    try:
        return int((r.stdout or b"").decode().strip().split(",")[0])
    except (ValueError, IndexError):
        return -1


def xuat(src: str, dst: str) -> None:
    from app.core.ffmpeg_utils import export_canvas_clip
    export_canvas_clip(src, dst, [(0.30, 3.60), (4.20, 7.60)],
                       (0.5, 0.42, 0.98), bg="blur", out_w=W, out_h=H,
                       encoder="libx264", hieu_ung="tat", chuyen_canh="tat",
                       fx_whoosh=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--moc", default="7b1da35")
    a = ap.parse_args()
    print(f"BẤT BIẾN mức 'tat' — nhánh này vs mốc {a.moc} (v2.19.0)")

    # --- CHỐNG PASS OAN: 2 file ĐANG SỬA phải THẬT SỰ KHÁC bản mốc ---------
    # Không có bước này thì nếu mốc trỏ nhầm vào chính nhánh, PSNR sẽ 999 dB
    # vĩnh viễn và cổng thành con dấu (đúng lỗi "so với chính mình" đã ghi).
    khac = {}
    for duong in ("app/core/hieu_ung.py", "app/core/hieu_ung_gpu.py"):
        r = subprocess.run(["git", "-C", str(REPO), "show", f"{a.moc}:{duong}"],
                           capture_output=True, creationflags=_NOWIN,
                           timeout=60)
        cu = (r.stdout or b"").decode("utf-8", errors="replace")
        nay = (REPO / duong).read_text(encoding="utf-8", errors="replace")
        khac[duong] = cu.strip() != nay.strip()
        bao(f"{duong} của nhánh KHÁC bản mốc (đối chứng hợp lệ)",
            khac[duong], f"mốc {len(cu)} ký tự · nhánh {len(nay)} ký tự")
    if not any(khac.values()):
        print("\nDỪNG: không file nào khác mốc -> phép so vô nghĩa.")
        return 1

    src = nguon()
    b = str(_SB / "tat_moi.mp4")
    xuat(src, b)
    n_moi = dem_khung(b)

    # nạp hieu_ung + hieu_ung_gpu CỦA MỐC CŨ, ĐẨY bản mới ra khỏi sys.modules
    giu = {k: sys.modules.get(k) for k in
           ("app.core.hieu_ung", "app.core.hieu_ung_gpu",
            "app.core.ffmpeg_utils")}
    try:
        _nap_moc(a.moc, "app.core.hieu_ung", "app/core/hieu_ung.py")
        _nap_moc(a.moc, "app.core.hieu_ung_gpu", "app/core/hieu_ung_gpu.py")
        # ffmpeg_utils phải nạp LẠI để nó bắt đúng 2 module cũ vừa cắm
        sys.modules.pop("app.core.ffmpeg_utils", None)
        from app.core import hieu_ung as _hu_cu
        bao(f"đã cắm được kho CŨ của mốc {a.moc}",
            len(_hu_cu.KHO) < 40, f"kho cũ {len(_hu_cu.KHO)} kiểu")
        aa = str(_SB / "tat_cu.mp4")
        xuat(src, aa)
        n_cu = dem_khung(aa)
    finally:
        for k, v in giu.items():
            if v is not None:
                sys.modules[k] = v
                goi, _, con = k.rpartition(".")
                if goi and goi in sys.modules:
                    setattr(sys.modules[goi], con, v)
            else:
                sys.modules.pop(k, None)

    p = psnr(aa, b)
    bao("mức 'tat': số khung GIỐNG HỆT bản mốc",
        n_cu == n_moi and n_cu > 0, f"{n_cu} vs {n_moi} khung")
    bao("mức 'tat': PSNR >= 50 dB so với bản mốc (BẤT BIẾN SỐNG CÒN)",
        p >= 50.0, f"PSNR {p if p < 999 else 'inf (giống HỆT từng bit)'} dB")
    sa, sb = os.path.getsize(aa), os.path.getsize(b)
    bao("mức 'tat': cỡ file lệch < 0,5%",
        abs(sa - sb) <= max(1, sa) * 0.005,
        f"{sa} vs {sb} byte (lệch {abs(sa-sb)})")

    print("\n" + "=" * 70)
    if _LOI:
        print(f"HỎNG {len(_LOI)}:")
        for x in _LOI:
            print("  · " + x)
        return 1
    print("BẤT BIẾN GIỮ: kho 27 -> 43 kiểu mà mức Tắt ra file y hệt v2.19.0")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
