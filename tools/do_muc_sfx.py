# -*- coding: utf-8 -*-
"""SINH BẢNG MỨC ÂM CHO KHO TIẾNG ĐỘNG -> `app/assets/sfx/muc_do.json`.

VÌ SAO PHẢI CÓ BẢNG NÀY (đo thật 08/08/2026): kho 185 file có ĐỈNH đều nhau
(0,0 .. -3,7 dBFS) nhưng mức NGHE ĐƯỢC (mean/RMS) trải **15 dB**:
    riser/riser_fast_05   mean **-3,9** dB      <- to nhất
    pop/click_02          mean **-19,1** dB     <- nhỏ nhất
Bản cũ nhân CÙNG một hệ số `volume` theo NHÓM (0,24-0,42) nên cùng một nhóm
cũng ra tiếng lúc nghe rõ lúc mất hút, và so với tiếng gốc của clip (đo -23,6
dB) thì tiếng động chỉ nhô lên **+0,7 dB** = KHÔNG NGHE THẤY. Có bảng này thì
lúc xuất tính được hệ số để tiếng động luôn cao hơn nền ĐÚNG số dB mong muốn.

Chạy 1 lần khi kho đổi:  .venv\\Scripts\\python.exe tools\\do_muc_sfx.py
Chạy TUẦN TỰ (1 ffmpeg tại một thời điểm — luật máy anh Hùng).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FF = str(ROOT / "bin" / "ffmpeg.exe")
KHO = ROOT / "app" / "assets" / "sfx"
RA = KHO / "muc_do.json"
NOWIN = 0x08000000 if os.name == "nt" else 0
DUOI = (".wav", ".opus", ".ogg", ".mp3", ".m4a")


def do(p: Path) -> tuple[float, float] | None:
    r = subprocess.run([FF, "-hide_banner", "-v", "info", "-i", str(p),
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, creationflags=NOWIN, timeout=60)
    txt = (r.stderr or b"").decode("utf-8", "replace")
    mean = mx = None
    for ln in txt.splitlines():
        if "mean_volume:" in ln:
            mean = float(ln.split("mean_volume:")[1].split("dB")[0])
        elif "max_volume:" in ln:
            mx = float(ln.split("max_volume:")[1].split("dB")[0])
    if mean is None or mx is None:
        return None
    return (mean, mx)


def do_ngan_han(p: Path) -> tuple[float, float] | None:
    """ĐỈNH RMS NGẮN HẠN (cửa sổ 50 ms) — dBFS. Đây mới là thước dự đoán được
    "nghe to hay nhỏ" của một cú va NGẮN:
      * `mean_volume` là trung bình CẢ FILE, kể cả đuôi ngân và khoảng lặng ->
        file có đuôi dài bị đánh giá nhỏ oan.
      * `max_volume` là 1 mẫu đơn lẻ; kho đã chuẩn hoá ĐỈNH nên gần như file
        nào cũng ~0 dBFS -> không phân biệt được gì.
    Chuẩn hoá theo số này thì MỌI file kêu to bằng nhau ở tai người, tức hết
    "3 Part cùng mức mà Part này nghe rõ Part kia mất hút" (nhấp nháy).
    Đo bằng chính khuôn cổng test dùng: 8 kHz mono, cửa sổ 400 mẫu = 50 ms.

    Trả (mức dBFS, **GIÂY xảy ra đỉnh**). Số thứ hai để app DÓNG cú va vào
    đúng mốc: kho có tiếng VÀO CHẬM (ding/sparkle/riser) mà đỉnh rơi 0,6 s SAU
    lúc bắt đầu -> nó không hề "đánh dấu" điểm nhấn nào cả. Đo thật
    (`ding_soft_04_v2.opus`): trong cửa sổ +-0,175 s quanh mốc chỉ còn
    **-28,3 dBFS** thay vì -20,1 = hụt **8,2 dB**, và đó chính là 1 trong 2
    nguồn làm cổng 44 nhấp nháy (5 lượt hỏng 2)."""
    r = subprocess.run(
        [FF, "-hide_banner", "-v", "error", "-nostdin", "-i", str(p), "-vn",
         "-af", "aresample=8000,aformat=channel_layouts=mono,"
                "asetnsamples=n=400,astats=metadata=1:reset=1,"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
         "-f", "null", "-"],
        capture_output=True, creationflags=NOWIN, timeout=60)
    vals = []
    for ln in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if "RMS_level=" in ln:
            try:
                v = float(ln.split("=")[1])
            except (ValueError, IndexError):
                continue
            if v > -200.0:
                vals.append(v)
    if not vals:
        return None
    i = max(range(len(vals)), key=lambda k: vals[k])
    return (vals[i], i * 0.05)


def main() -> int:
    bang: dict = {}
    files = sorted(p for p in KHO.rglob("*") if p.is_file()
                   and p.suffix.lower() in DUOI)
    for i, p in enumerate(files, 1):
        kq = do(p)
        if kq is None:
            print(f"  !! bỏ qua (không đo được): {p.name}")
            continue
        st = do_ngan_han(p)
        key = p.relative_to(KHO).as_posix()
        # [mean, max, đỉnh RMS 50 ms, GIÂY xảy ra đỉnh] — 2 mục cuối THÊM
        # 08-09/08/2026. File cũ chỉ có 2 mục vẫn đọc được (`_muc_sfx3` tự suy
        # ra), nhưng nên chạy lại tool.
        bang[key] = [round(kq[0], 1), round(kq[1], 1),
                     round(st[0] if st is not None else kq[0] + 6.0, 1),
                     round(st[1] if st is not None else 0.0, 2)]
        if i % 25 == 0:
            print(f"  ... {i}/{len(files)}")
    RA.write_text(json.dumps(bang, ensure_ascii=False, indent=0,
                             sort_keys=True), encoding="utf-8")
    ms = [v[0] for v in bang.values()]
    ss = [v[2] for v in bang.values()]
    cr = sorted(v[1] - v[2] for v in bang.values())
    print(f"\nĐã ghi {RA} — {len(bang)} file")
    print(f"mean_volume: thấp nhất {min(ms):.1f} dB · cao nhất {max(ms):.1f} dB"
          f" · trải {max(ms)-min(ms):.1f} dB")
    print(f"đỉnh RMS 50 ms: {min(ss):.1f} .. {max(ss):.1f} dB "
          f"· trải {max(ss)-min(ss):.1f} dB")
    print(f"hệ số đỉnh NGẮN HẠN (max − rms50): min {cr[0]:.1f} · trung vị "
          f"{cr[len(cr)//2]:.1f} · max {cr[-1]:.1f} dB")
    tp = sorted(v[3] for v in bang.values())
    print(f"GIÂY xảy ra đỉnh: trung vị {tp[len(tp)//2]:.2f}s · "
          f"bpv90 {tp[int(len(tp)*0.9)]:.2f}s · max {tp[-1]:.2f}s · "
          f"{sum(1 for x in tp if x > 0.35)} file vào CHẬM (> 0,35 s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
