# -*- coding: utf-8 -*-
"""ĐO HỘP CHE CHỮ CÓ TRÔI KHÔNG khi bật "Chỉnh video theo giọng" (20/08/2026).

**VÌ SAO CÓ PHÉP ĐO NÀY.** `thay_audio_video` làm chậm hình bằng `-itsscale`
(rẻ, không mã hoá lại). Nhưng ở nhánh CHE CHỮ thì có filter, và chú thích
trong mã đang khẳng định:

    "`-itsscale` vẫn dùng được (nó đụng mốc ĐẦU VÀO, trước cả filter) nên
     KHÔNG cần `setpts` — chuỗi filter che chữ giữ nguyên. Mốc hộp che lấy từ
     `segs=[(0, dur)]` của video GỐC, mà `-itsscale` giãn đều nên hộp vẫn bám
     đúng chỗ chữ cũ."

Câu đó nghe hợp lý nên **chưa ai đo**. Nó SAI: `-itsscale` giãn mốc TRƯỚC khi
frame vào filter, nên biến `t` mà `enable='between(t,a,b)'` đọc CHÍNH LÀ mốc
ĐÃ GIÃN. Còn `a,b` thì `che_chu.loc_cho_xuat` dò trên video GỐC nên là mốc
CHƯA GIÃN. Hai bên lệch nhau đúng hệ số `k` và **lệch càng xa về cuối phim**:
chữ ở giây 80 với k=1,2 thì hộp che rơi ở giây 80 trong khi chữ đã trôi tới
giây 96 -> **16 giây lệch**, hộp che một chỗ trống rồi chữ cũ hiện nguyên.

**THƯỚC:** nguồn tự sinh bằng `lavfi` — dải TRẮNG ở đáy khung chỉ hiện trong
một cửa sổ thời gian BIẾT TRƯỚC. Xuất rồi đo ĐỘ SÁNG dải đáy theo từng mốc.
Hộp che đúng chỗ -> dải đáy KHÔNG BAO GIỜ trắng. Hộp trôi -> có mốc trắng
nguyên. Không đọc `rc` của ffmpeg, đọc ĐIỂM ẢNH.

Ba cấu hình:
  1. `k=1,0`         — ĐỐI CHỨNG: không giãn thì phải che đúng (nếu mục này
                       hỏng thì bộ đo hỏng, đừng đọc tiếp bảng).
  2. `-itsscale k`   — cách CŨ đang có trong mã.
  3. `setpts` SAU khối che — cách VÁ (giống thứ tự `ffmpeg_utils` đang dùng:
                       che/overlay trên mốc NGUỒN rồi mới giãn).

    .venv\\Scripts\\python -u _do_hop_che_troi.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_DATA_DIR", tempfile.mkdtemp(prefix="bq_hopche_"))

from config import settings  # noqa: E402

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NW = 0x0800_0000 if os.name == "nt" else 0

W, H, FPS = 320, 240, 24.0
DAI = 10.0            # độ dài nguồn (giây)
CHU_A, CHU_B = 6.0, 8.0   # dải TRẮNG ở đáy chỉ hiện trong khoảng này
DAY = 40              # bề cao dải đáy (điểm ảnh) — "vùng chữ"
K = 1.25              # hệ số làm chậm hình đem đo


def ff(args: list[str]) -> None:
    r = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True, timeout=300,
                       creationflags=_NW)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {(r.stderr or '')[:400]}")


def sang_day(vid: Path, t: float) -> float:
    """Độ sáng TRUNG BÌNH của dải đáy tại mốc `t` giây (0..255)."""
    r = subprocess.run(
        [FF, "-v", "error", "-ss", f"{t:.3f}", "-i", str(vid),
         "-frames:v", "1", "-vf", f"crop={W}:{DAY}:0:{H - DAY}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, timeout=120, creationflags=_NW)
    b = r.stdout
    return (sum(b) / len(b)) if b else -1.0


def do_dai(vid: Path) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1",
                        str(vid)], capture_output=True, text=True, timeout=60,
                       creationflags=_NW)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def so_khung(vid: Path) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "default=nw=1:nk=1", str(vid)],
                       capture_output=True, text=True, timeout=300,
                       creationflags=_NW)
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return -1


def main() -> int:
    hop = Path(tempfile.mkdtemp(prefix="bq_hopche_"))
    try:
        # --- NGUỒN: nền xám, dải TRẮNG ở đáy chỉ trong [CHU_A, CHU_B] ---
        # Nền XÁM (không đen) để phân biệt được "bị hộp che phủ đen" với
        # "vốn không có chữ".
        src = hop / "goc.mp4"
        ff(["-f", "lavfi", "-i",
            f"color=c=gray:s={W}x{H}:r={FPS:g}:d={DAI:g}",
            "-vf", (f"drawbox=x=0:y={H - DAY}:w={W}:h={DAY}:color=white:"
                    f"t=fill:enable='between(t,{CHU_A},{CHU_B})'"),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-pix_fmt", "yuv420p", str(src)])

        # Chuỗi filter "che chữ" GIẢ — đúng khuôn `che_chu` sinh ra: một
        # `drawbox` phủ khối kèm `enable='between(t,a,b)'` với a,b là mốc dò
        # được trên video GỐC.
        che = (f"drawbox=x=0:y={H - DAY}:w={W}:h={DAY}:color=black:"
               f"t=fill:enable='between(t,{CHU_A},{CHU_B})'")

        ra: dict[str, Path] = {}

        # 1. ĐỐI CHỨNG k=1,0
        p = hop / "k1.mp4"
        ff(["-i", str(src), "-filter_complex", f"[0:v]{che}[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "18", "-pix_fmt", "yuv420p", str(p)])
        ra["1. ĐỐI CHỨNG k=1,0"] = p

        # 2. CÁCH CŨ: -itsscale K, chuỗi che giữ nguyên mốc NGUỒN
        p = hop / "cu.mp4"
        ff(["-itsscale", f"{K:.6f}", "-i", str(src),
            "-filter_complex", f"[0:v]{che}[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "18", "-pix_fmt", "yuv420p", str(p)])
        ra[f"2. CŨ  -itsscale {K}"] = p

        # 3. CÁCH VÁ: che trên mốc NGUỒN rồi mới `setpts` giãn
        p = hop / "va.mp4"
        ff(["-i", str(src), "-filter_complex",
            f"[0:v]{che},setpts=PTS*{K:.6f}[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "18", "-pix_fmt", "yuv420p", str(p)])
        ra[f"3. VÁ  setpts SAU khối che ({K})"] = p

        print(f"NGUỒN: {DAI:g}s · {FPS:g} fps · dải trắng ở đáy "
              f"[{CHU_A:g}, {CHU_B:g}]s · hệ số đem đo k={K}")
        print(f"  gốc: {do_dai(src):.3f}s · {so_khung(src)} khung\n")

        print(f"{'cấu hình':<34} {'giây':>7} {'khung':>6} "
              f"{'sáng nhất dải đáy':>18} {'mốc':>7}  KẾT LUẬN")
        print("-" * 96)
        for ten, vid in ra.items():
            d = do_dai(vid)
            n = so_khung(vid)
            # quét dày 0,2 giây suốt cả file, tìm mốc dải đáy SÁNG NHẤT
            xs = []
            t = 0.05
            while t < d - 0.05:
                xs.append((sang_day(vid, t), t))
                t += 0.2
            top, moc = max(xs) if xs else (-1.0, -1.0)
            # dải trắng = ~235; nền xám = ~125; bị phủ đen = ~16
            lot = top > 200.0
            print(f"{ten:<34} {d:7.3f} {n:6d} {top:18.1f} {moc:7.2f}  "
                  + ("LỌT CHỮ (hộp che TRÔI)" if lot
                     else "che KÍN (không lọt)"))
        print("\nĐọc bảng: 'sáng nhất dải đáy' ~235 = dải TRẮNG hiện nguyên "
              "-> hộp che rơi sai chỗ.\n~125 = nền xám (không có chữ, không "
              "bị che oan). ~16 = bị phủ đen.")
        return 0
    finally:
        shutil.rmtree(hop, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
