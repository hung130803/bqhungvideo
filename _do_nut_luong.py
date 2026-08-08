# -*- coding: utf-8 -*-
"""SOI TỪNG NÚM luồng của ffmpeg: núm nào giảm luồng mà KHÔNG làm chậm?

VÌ SAO (lần thử 07/08/2026 thất bại): thêm `-threads`+`-filter_threads` vào cả
2 encoder -> luồng 62->45 nhưng chậm 3,4 lần rồi phải revert, và **không biết
núm nào gây chậm** vì bật hết một lượt. File này bật/tắt TỪNG NÚM trên ĐÚNG
lệnh pha 2 (nặng nhất: concat + blur + overlay + đốt .ass + nvenc), đo:
  - đỉnh luồng + trung bình luồng (lấy mẫu 20 lần/giây)
  - CPU-giây (user+system) — số duy nhất không bị nhiễu bởi máy đang bận
  - **ENCODER THỰC SỰ CHẠY** (đọc log ffmpeg) — bắt buộc, vì nghi `-threads`
    trên nhánh nvenc làm rớt về CPU mà lần trước KHÔNG ai log lại để biết.

Chạy: .venv\\Scripts\\python _do_nut_luong.py
"""
from __future__ import annotations

import os
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_SB = Path(tempfile.gettempdir()) / f"do_nut_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))

import psutil  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

from _do_luong_ffmpeg import _ass_mau, _may_ranh, tim_video_nhat  # noqa: E402

_NOWIN = 0x08000000


def chay_dem(cmd: list[str]) -> dict:
    """Chạy 1 lệnh ffmpeg, lấy mẫu luồng + CPU-giây, đọc log ra encoder THỰC."""
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         universal_newlines=True, encoding="utf-8",
                         errors="replace", creationflags=_NOWIN)
    ps = psutil.Process(p.pid)
    mau: list[int] = []
    cpu = {"v": 0.0}
    stop = threading.Event()

    def _sample() -> None:
        while not stop.is_set():
            try:
                mau.append(ps.num_threads())
                ct = ps.cpu_times()
                cpu["v"] = float(ct.user) + float(ct.system)
            except psutil.Error:
                break
            time.sleep(0.05)

    th = threading.Thread(target=_sample, daemon=True)
    th.start()
    log = p.stdout.read() if p.stdout else ""      # type: ignore[union-attr]
    p.wait()
    stop.set()
    th.join(timeout=2)
    wall = round(time.perf_counter() - t0, 2)
    # ENCODER THỰC (BẮT BUỘC log — nghi `-threads` làm nvenc rớt về CPU mà lần
    # thử trước không ai ghi lại). ffmpeg in "Video: h264 (Main), ... encoder :
    # Lavc h264_nvenc" hoặc dòng map "-> h264 (h264_nvenc)".
    enc_that = "?"
    for pat in (r"->\s*h264\s*\(([\w_]+)\)",
                r"encoder\s*:\s*Lavc[\d.]*\s+([\w_]+)",
                r"\[(h264_nvenc|libx264)\s*@"):
        m = re.search(pat, log)
        if m:
            enc_that = m.group(1)
            break
    return {"wall": wall, "cpu": round(cpu["v"], 2),
            "dinh": max(mau) if mau else 0,
            "tb": round(statistics.mean(mau), 1) if mau else 0.0,
            "rc": p.returncode, "enc": enc_that,
            "log_cuoi": " | ".join(log.strip().splitlines()[-2:])[:200]}


def main() -> int:
    ok, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok:
        print("DỪNG: máy bận.")
        return 2
    vids = tim_video_nhat(1)
    if not vids:
        print("DỪNG: không có video Nhật.")
        return 2
    src = vids[0]
    from app.core import ffmpeg_utils as fu
    from config import settings

    ff = settings.FFMPEG_PATH
    print(f"[ffmpeg] {ff}")
    ass = _ass_mau(_SB / "sub.ass", 20.0)
    ap = str(ass).replace("\\", "/").replace(":", "\\:")
    out = _SB / "o.mp4"

    # ---- LỆNH PHA 2 y như app dựng: concat 2 đoạn -> blur nền + overlay khối
    # video + đốt .ass + fade -> nvenc. Ở đây dùng THẲNG 1 input (đoạn đã tách)
    # để cô lập núm; số luồng/CPU của graph không khác.
    seg = _SB / "seg.mkv"
    if not seg.exists():
        subprocess.run([ff, "-y", "-ss", "60", "-t", "20", "-i", str(src),
                        "-c:v", "h264_nvenc", "-preset", "p1", "-cq", "16",
                        "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode:v", "cfr",
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                        str(seg)], capture_output=True, creationflags=_NOWIN)
    print(f"[đoạn tạm] {seg.stat().st_size // 1024} KB")

    W, H = 1080, 1920
    bw, bh, br = W // 4, H // 4, 22 // 4
    vw = 1058
    graph = (
        f"[0:v]split=2[bv][fv];"
        f"[bv]scale={bw}:{bh}:force_original_aspect_ratio=increase,"
        f"crop={bw}:{bh},boxblur={br}:1,scale={W}:{H},setsar=1[base];"
        f"[fv]scale={vw}:-2:flags=lanczos,setsar=1[fg];"
        f"[base][fg]overlay=x='0.5*W-w/2':y='0.42*H-h/2'[vv];"
        f"[vv]subtitles='{ap}'[vsub];"
        f"[vsub]fade=t=in:st=0:d=0.35,fade=t=out:st=19.65:d=0.35[vfx]"
    )

    def lenh(gl: list[str], inop: list[str], encop: list[str]) -> list[str]:
        return ([ff, "-y", *gl, *inop, "-i", str(seg),
                 "-filter_complex", graph, "-map", "[vfx]", "-map", "0:a",
                 *encop, "-c:a", "aac", "-b:a", "160k",
                 "-movflags", "+faststart", str(out)])

    NV = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19",
          "-pix_fmt", "yuv420p"]
    ca = [
        ("0. HIỆN TẠI (fct=7, nvenc không -threads)",
         ["-filter_complex_threads", "7"], [], NV),
        ("1. bỏ hết giới hạn (đối chứng)", [], [], NV),
        ("2. fct=7 + THREADS GIẢI MÃ 4 (trước -i)",
         ["-filter_complex_threads", "7"], ["-threads", "4"], NV),
        ("3. fct=7 + giải mã 2", ["-filter_complex_threads", "7"],
         ["-threads", "2"], NV),
        ("4. fct=4 + giải mã 4", ["-filter_complex_threads", "4"],
         ["-threads", "4"], NV),
        ("5. fct=2 + giải mã 2", ["-filter_complex_threads", "2"],
         ["-threads", "2"], NV),
        ("6. fct=7 + giải mã 4 + nvenc CÓ -threads 4",
         ["-filter_complex_threads", "7"], ["-threads", "4"],
         NV + ["-threads", "4"]),
        ("7. fct=7 + giải mã 4 + filter_threads 4",
         ["-filter_complex_threads", "7", "-filter_threads", "4"],
         ["-threads", "4"], NV),
        ("8. SÀN: fct=1 + ft=1 + giải mã 1",
         ["-filter_complex_threads", "1", "-filter_threads", "1"],
         ["-threads", "1"], NV),
        ("9. SÀN vừa: fct=2 + ft=2 + giải mã 2",
         ["-filter_complex_threads", "2", "-filter_threads", "2"],
         ["-threads", "2"], NV),
        ("10. libx264 HIỆN TẠI (fct=7, -threads 7 encode)",
         ["-filter_complex_threads", "7"], [],
         ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
          "-threads", "7"]),
        ("11. libx264 + giải mã 2 + fct/ft=2",
         ["-filter_complex_threads", "2", "-filter_threads", "2"],
         ["-threads", "2"],
         ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
          "-threads", "2"]),
    ]
    print(f"\n{'ca':52s} {'wall':>6s} {'CPU-s':>7s} {'đỉnh':>5s} {'TB':>6s} "
          f"{'enc THỰC':>10s}")
    ket = []
    for ten, gl, inop, encop in ca:
        r = chay_dem(lenh(gl, inop, encop))
        ket.append((ten, r))
        print(f"{ten:52s} {r['wall']:6.2f} {r['cpu']:7.2f} {r['dinh']:5d} "
              f"{r['tb']:6.1f} {r['enc']:>10s}"
              + ("" if r["rc"] == 0 else f"  RC={r['rc']} {r['log_cuoi']}"))
        out.unlink(missing_ok=True)
    base = ket[0][1]
    print("\n=== SO VỚI CA 0 (hiện tại) ===")
    for ten, r in ket[1:]:
        print(f"{ten:52s} luồng {r['dinh'] / max(1, base['dinh']):.2f}x · "
              f"CPU {r['cpu'] / max(0.01, base['cpu']):.2f}x · "
              f"wall {r['wall'] / max(0.01, base['wall']):.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
