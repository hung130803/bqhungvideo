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


#: MÔ HÌNH LOA ĐIỆN THOẠI — bậc 4 (24 dB/quãng tám) cắt dưới 300 Hz. Khán giả
#: Shorts/TikTok nghe bằng loa điện thoại hoặc loa laptop, thứ gần như KHÔNG
#: phát được dưới 300 Hz. Đo 13 mốc trên 3 video thật (`_do_che_loi.py`): tiếng
#: động bốc trúng file TRẦM thì dải <300 Hz vọt lên **+22..+38 dB** mà mọi dải
#: từ 300 Hz trở lên KHÔNG đổi (còn tụt vì ducking) — trên máy đo là "rất to",
#: trên điện thoại là **KHÔNG NGHE THẤY GÌ**. Đúng câu anh Hùng nói: *"nó dùng
#: mà không nghe thấy luôn"*.
LOA = "highpass=f=300:poles=2,highpass=f=300:poles=2,"
#: DẢI SÁNG (trên 4 kHz) — chỗ GIỌNG NÓI gần như KHÔNG có năng lượng. Giọng
#: người dồn 300-3400 Hz; tiếng động có nhiều năng lượng trên 4 kHz thì nó
#: KHÔNG phải đấu với lời, nghe rõ mà chẳng cần to thêm dB nào (đúng hướng "chọn
#: tiếng động LỆCH DẢI TẦN với giọng nói"). Đây là cách rẻ nhất: không thêm độ
#: to -> không chói, không đẩy việc cho lớp hạn đỉnh, không phải hạ giọng sâu.
SANG = "highpass=f=4000:poles=2,highpass=f=4000:poles=2,"


def do_ngan_han(p: Path, truoc: str = "",
                sr: int = 8000) -> tuple[float, float] | None:
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
         # `truoc` đặt TRƯỚC `aresample`: lọc phải chạy ở tần số lấy mẫu GỐC.
         # BẪY ĐÃ SẬP: để sau `aresample=8000` thì `highpass=f=4000` nằm đúng
         # tần số Nyquist -> cắt sạch, MỌI file ra -99 dB (cột "độ sáng" tự
         # PASS thành vô nghĩa). Dải nào cần đo trên 4 kHz thì phải `sr` >= 16k.
         "-af", f"{truoc}aresample={sr},aformat=channel_layouts=mono,"
                f"asetnsamples=n={int(sr * 0.05)},"
                "astats=metadata=1:reset=1,"
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
        lo = do_ngan_han(p, LOA)
        # ĐỘ SÁNG đo ở 16 kHz (Nyquist 8 kHz) và so với mức TOÀN DẢI ĐO CÙNG
        # 16 kHz — so với cột 3 (đo ở 8 kHz, đã mất hết phần trên 4 kHz) là tự
        # thổi phồng đúng cái đang muốn đo.
        sg = do_ngan_han(p, SANG, sr=16000)
        full16 = do_ngan_han(p, "", sr=16000)
        key = p.relative_to(KHO).as_posix()
        # [mean, max, đỉnh RMS 50 ms, GIÂY xảy ra đỉnh, HỤT QUA LOA, ĐỘ SÁNG]
        # — mục 5-6 THÊM 09/08/2026 (đều <= 0 dB). File cũ thiếu mục nào cũng
        # vẫn đọc được (app tự suy ra).
        _st = st[0] if st is not None else kq[0] + 6.0
        bang[key] = [round(kq[0], 1), round(kq[1], 1), round(_st, 1),
                     round(st[1] if st is not None else 0.0, 2),
                     round((lo[0] - _st) if lo is not None else 0.0, 1),
                     round((sg[0] - full16[0])
                           if (sg is not None and full16 is not None)
                           else -99.0, 1)]
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
    lo_ = sorted(v[4] for v in bang.values())
    print(f"HỤT QUA LOA ĐIỆN THOẠI (cắt <300 Hz): trung vị "
          f"{lo_[len(lo_)//2]:.1f} dB · bpv10 {lo_[int(len(lo_)*0.1)]:.1f} dB "
          f"· tệ nhất {lo_[0]:.1f} dB · "
          f"{sum(1 for x in lo_ if x < -6.0)} file hụt quá 6 dB")
    xau = sorted((v[4], k) for k, v in bang.items())[:8]
    print("  TRẦM NHẤT (nghe trên máy đo thì to, trên điện thoại thì câm):")
    for d_, k in xau:
        print(f"    {d_:6.1f} dB  {k}")
    sg_ = sorted(v[5] for v in bang.values())
    print(f"ĐỘ SÁNG (năng lượng trên 4 kHz, chỗ giọng nói KHÔNG có): trung vị "
          f"{sg_[len(sg_)//2]:.1f} dB · bpv75 {sg_[int(len(sg_)*0.75)]:.1f} dB "
          f"· cao nhất {sg_[-1]:.1f} dB · "
          f"{sum(1 for x in sg_ if x >= -12.0)} file >= -12 dB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
