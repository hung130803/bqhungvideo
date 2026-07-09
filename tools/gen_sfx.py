#!/usr/bin/env python
"""
SINH THƯ VIỆN TIẾNG ĐỘNG (SFX) đóng gói sẵn — thuần ffmpeg lavfi.

Chạy 1 LẦN để tạo ra ~26 file WAV trong app/assets/sfx/<category>/*.wav rồi
COMMIT các file .wav đó vào repo (đóng gói sẵn -> máy khách chỉ cập nhật là có,
KHÔNG cài gì, KHÔNG tải mạng, KHÔNG bản quyền). Script này CHỈ để TÁI TẠO được
thư viện; artifact CHÍNH THỨC là các file .wav.

Đặc tả mỗi file:
  - 48kHz mono, độ dài 0.2-0.8s, âm lượng chuẩn hoá nhẹ (không lố).
  - Phân loại theo NGỮ CẢNH / CẢM XÚC điểm nối:
      transition/  (9):    whoosh lên/xuống, swoosh gió, air, tick chuyển
      impact/      (5):    boom trầm, hit, thud, punch (khoảnh khắc mạnh/twist)
      riser/       (5):    build-up căng dần trước cao trào (sweep tần số lên)
      reveal/      (4):    ding, bell, sparkle (lúc "lộ diện"/kết)
      pop/         (4):    pop, click, blip nhẹ
      suspense/    (4):    drone trầm ngân căng thẳng (đoạn gây cấn/hồi hộp)
      comedy/      (4):    boing, spring, blip vui (đoạn hài)
      scratch/     (3):    record-scratch (noise sweep nhanh) — bất ngờ/"khựng"
      sad/         (3):    nốt trầm buồn / piano trầm ngắn (đoạn buồn)
      drumroll/    (2):    trống dồn ngắn trước cao trào
  - Mỗi file 1 biến thể khác nhau (đổi tần số/bandpass/độ dài/đường cong fade).

Cách chạy:
    .venv/Scripts/python.exe tools/gen_sfx.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Console Windows mặc định cp1252 -> in tiếng Việt sẽ crash. Ép UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# ROOT = thư mục dự án (tools/ nằm ngay dưới ROOT)
ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "app" / "assets" / "sfx"

FFMPEG = "ffmpeg"

_CREATE_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0


# ------------------------------------------------------------------
# ĐỊNH NGHĨA CÁC FILE: (category, ten_file, thoi_luong, nguon_lavfi, chuoi_filter)
# Chuỗi filter KHÔNG gồm âm lượng cuối + fade cuối (thêm chung ở dưới): chỉ tạo
# nguồn + lọc đặc trưng loại. loudnorm nhẹ + volume theo loại áp ở _build().
# ------------------------------------------------------------------
def _defs() -> list[tuple[str, str, float, str, str, float]]:
    """Trả list (category, name, dur, lavfi_src, filter, peak_vol).

    peak_vol = biên độ đỉnh mong muốn (0..1) — impact to hơn transition chút,
    ding/reveal nhẹ. fade in/out được ghép tự động theo dur (đường cong đa dạng).
    """
    d: list[tuple[str, str, float, str, str, float]] = []

    # ---- transition/ (9 biến thể: whoosh/swoosh/air/tick) ----
    d.append(("transition", "whoosh_up_01", 0.30,
              "anoisesrc=color=white:r=48000",
              "highpass=f=500,bandpass=f=1500:width_type=h:w=1300,"
              "afade=t=in:st=0:d=0.20:curve=ipar,"
              "afade=t=out:st=0.24:d=0.06:curve=tri", 0.55))
    d.append(("transition", "whoosh_down_02", 0.32,
              "anoisesrc=color=white:r=48000",
              "bandpass=f=1200:width_type=h:w=1000,lowpass=f=2200,"
              "afade=t=in:st=0:d=0.05:curve=exp,"
              "afade=t=out:st=0.11:d=0.21:curve=qsin", 0.55))
    d.append(("transition", "swoosh_air_03", 0.34,
              "anoisesrc=color=pink:r=48000",
              "bandpass=f=1100:width_type=h:w=2000,"
              "afade=t=in:st=0:d=0.14:curve=tri,"
              "afade=t=out:st=0.17:d=0.17:curve=tri", 0.50))
    d.append(("transition", "whoosh_mid_04", 0.26,
              "anoisesrc=color=white:r=48000",
              "bandpass=f=1400:width_type=h:w=900,"
              "afade=t=in:st=0:d=0.08:curve=exp,"
              "afade=t=out:st=0.10:d=0.16:curve=tri", 0.55))
    d.append(("transition", "air_soft_05", 0.36,
              "anoisesrc=color=brown:r=48000",
              "bandpass=f=800:width_type=h:w=1400,lowpass=f=3000,"
              "afade=t=in:st=0:d=0.18:curve=qsin,"
              "afade=t=out:st=0.22:d=0.14:curve=qsin", 0.48))
    d.append(("transition", "tick_soft_06", 0.22,
              "sine=frequency=2200:r=48000",
              "highpass=f=1500,afade=t=out:st=0.012:d=0.05:curve=exp", 0.45))
    d.append(("transition", "swoosh_hi_07", 0.28,
              "anoisesrc=color=white:r=48000",
              "highpass=f=900,bandpass=f=2000:width_type=h:w=1600,"
              "afade=t=in:st=0:d=0.16:curve=ipar,"
              "afade=t=out:st=0.20:d=0.08:curve=tri", 0.52))
    d.append(("transition", "whoosh_low_08", 0.30,
              "anoisesrc=color=pink:r=48000",
              "bandpass=f=700:width_type=h:w=800,lowpass=f=1600,"
              "afade=t=in:st=0:d=0.06:curve=exp,"
              "afade=t=out:st=0.12:d=0.18:curve=qsin", 0.52))
    d.append(("transition", "tick_click_09", 0.20,
              "sine=frequency=1600:r=48000",
              "highpass=f=1200,afade=t=out:st=0.006:d=0.05:curve=exp", 0.42))

    # ---- impact/ (5: boom/hit/thud/punch — to hơn chút) ----
    d.append(("impact", "boom_low_01", 0.34,
              "sine=frequency=70:r=48000",
              "lowpass=f=160,afade=t=in:st=0:d=0.008:curve=exp,"
              "afade=t=out:st=0.05:d=0.29:curve=qsin", 0.80))
    d.append(("impact", "hit_mid_02", 0.24,
              "anoisesrc=color=brown:r=48000",
              "lowpass=f=500,bandpass=f=180:width_type=h:w=300,"
              "afade=t=in:st=0:d=0.005:curve=exp,"
              "afade=t=out:st=0.03:d=0.21:curve=exp", 0.72))
    d.append(("impact", "thud_03", 0.28,
              "sine=frequency=95:r=48000",
              "lowpass=f=220,afade=t=in:st=0:d=0.006:curve=exp,"
              "afade=t=out:st=0.04:d=0.24:curve=tri", 0.76))
    d.append(("impact", "punch_04", 0.20,
              "anoisesrc=color=brown:r=48000",
              "lowpass=f=350,afade=t=in:st=0:d=0.004:curve=exp,"
              "afade=t=out:st=0.02:d=0.18:curve=exp", 0.72))
    d.append(("impact", "boom_deep_05", 0.40,
              "sine=frequency=55:r=48000",
              "lowpass=f=130,afade=t=in:st=0:d=0.01:curve=exp,"
              "afade=t=out:st=0.07:d=0.33:curve=qsin", 0.82))

    # ---- riser/ (5: build-up căng dần, sweep tần số lên) ----
    # aevalsrc: tần số tăng tuyến tính f0 -> f1 trong dur giây (chirp).
    for i, (name, dur, f0, f1, pk) in enumerate((
            ("riser_soft_01", 0.45, 300.0, 1400.0, 0.55),
            ("riser_tense_02", 0.55, 250.0, 1800.0, 0.58),
            ("riser_hi_03", 0.40, 500.0, 2200.0, 0.55),
            ("riser_wide_04", 0.60, 200.0, 1600.0, 0.56),
            ("riser_fast_05", 0.35, 400.0, 2000.0, 0.55))):
        k = (f1 - f0) / dur
        expr = f"sin(2*PI*t*({f0:.1f}+{k / 2:.2f}*t))"
        # fade vào dài (căng dần), tắt nhanh ở đỉnh
        fin = dur * 0.7
        fout_st = dur * 0.88
        fout_d = dur - fout_st
        d.append(("riser", name, dur, f"aevalsrc={expr}:s=48000",
                  f"afade=t=in:st=0:d={fin:.3f}:curve=ipar,"
                  f"afade=t=out:st={fout_st:.3f}:d={fout_d:.3f}:curve=tri", pk))

    # ---- reveal/ (4: ding/bell/sparkle — lúc lộ diện/kết, nhẹ) ----
    d.append(("reveal", "ding_hi_01", 0.40,
              "sine=frequency=1760:r=48000",
              "afade=t=in:st=0:d=0.006:curve=exp,"
              "afade=t=out:st=0.05:d=0.35:curve=qsin", 0.50))
    d.append(("reveal", "bell_02", 0.50,
              "sine=frequency=1318:r=48000",
              "afade=t=in:st=0:d=0.006:curve=exp,"
              "afade=t=out:st=0.06:d=0.44:curve=qsin", 0.50))
    d.append(("reveal", "sparkle_03", 0.38,
              "sine=frequency=2637:r=48000",
              "highpass=f=1500,afade=t=in:st=0:d=0.006:curve=exp,"
              "afade=t=out:st=0.04:d=0.34:curve=exp", 0.44))
    d.append(("reveal", "ding_soft_04", 0.44,
              "sine=frequency=1046:r=48000",
              "afade=t=in:st=0:d=0.008:curve=exp,"
              "afade=t=out:st=0.05:d=0.39:curve=qsin", 0.48))

    # ---- pop/ (4: pop/click/blip nhẹ) ----
    d.append(("pop", "pop_01", 0.22,
              "sine=frequency=440:r=48000",
              "afade=t=in:st=0:d=0.005:curve=exp,"
              "afade=t=out:st=0.02:d=0.10:curve=exp", 0.55))
    d.append(("pop", "click_02", 0.20,
              "sine=frequency=880:r=48000",
              "highpass=f=600,afade=t=out:st=0.008:d=0.062:curve=exp", 0.50))
    d.append(("pop", "blip_03", 0.21,
              "sine=frequency=660:r=48000",
              "afade=t=in:st=0:d=0.004:curve=exp,"
              "afade=t=out:st=0.015:d=0.085:curve=exp", 0.52))
    d.append(("pop", "pop_hi_04", 0.23,
              "sine=frequency=1100:r=48000",
              "afade=t=in:st=0:d=0.004:curve=exp,"
              "afade=t=out:st=0.02:d=0.09:curve=exp", 0.50))

    # ---- suspense/ (4: drone trầm ngân căng thẳng — đoạn gây cấn/hồi hộp) ----
    # sine trầm (55-110Hz) + tremolo nhẹ (rung biên) tạo cảm giác căng, ngân
    # dài, fade vào/ra mượt để làm NỀN dưới giọng (không giật).
    d.append(("suspense", "drone_low_01", 0.70,
              "sine=frequency=60:r=48000",
              "tremolo=f=6:d=0.4,lowpass=f=200,"
              "afade=t=in:st=0:d=0.30:curve=qsin,"
              "afade=t=out:st=0.45:d=0.25:curve=qsin", 0.50))
    d.append(("suspense", "drone_tense_02", 0.80,
              "sine=frequency=82:r=48000",
              "tremolo=f=8:d=0.5,lowpass=f=260,"
              "afade=t=in:st=0:d=0.35:curve=qsin,"
              "afade=t=out:st=0.55:d=0.25:curve=qsin", 0.50))
    d.append(("suspense", "drone_deep_03", 0.75,
              "sine=frequency=48:r=48000",
              "tremolo=f=5:d=0.35,lowpass=f=170,"
              "afade=t=in:st=0:d=0.32:curve=qsin,"
              "afade=t=out:st=0.50:d=0.25:curve=qsin", 0.52))
    d.append(("suspense", "drone_hum_04", 0.65,
              "sine=frequency=98:r=48000",
              "tremolo=f=7:d=0.45,bandpass=f=110:width_type=h:w=140,"
              "afade=t=in:st=0:d=0.28:curve=qsin,"
              "afade=t=out:st=0.42:d=0.23:curve=qsin", 0.48))

    # ---- comedy/ (4: boing/spring/blip vui — đoạn hài) ----
    # boing = sine QUÉT tần số nhanh (aevalsrc chirp lên rồi xuống) -> "boing".
    d.append(("comedy", "boing_01", 0.34,
              # 700 -> 300Hz giảm nhanh: cảm giác "boing" nảy
              "aevalsrc=sin(2*PI*t*(700-600*t)):s=48000",
              "afade=t=in:st=0:d=0.01:curve=exp,"
              "afade=t=out:st=0.10:d=0.24:curve=qsin", 0.55))
    d.append(("comedy", "spring_02", 0.40,
              # quét lên-xuống dạng nảy lò xo (dùng |sin| của tần số dao động)
              "aevalsrc=sin(2*PI*t*(400+300*sin(2*PI*4*t))):s=48000",
              "afade=t=in:st=0:d=0.01:curve=exp,"
              "afade=t=out:st=0.14:d=0.26:curve=tri", 0.52))
    d.append(("comedy", "blip_happy_03", 0.24,
              # blip vui: sine cao nảy lên nhanh 500->1200Hz
              "aevalsrc=sin(2*PI*t*(500+700*t)):s=48000",
              "afade=t=in:st=0:d=0.006:curve=exp,"
              "afade=t=out:st=0.10:d=0.14:curve=exp", 0.52))
    d.append(("comedy", "boing_hi_04", 0.30,
              "aevalsrc=sin(2*PI*t*(900-700*t)):s=48000",
              "highpass=f=300,afade=t=in:st=0:d=0.008:curve=exp,"
              "afade=t=out:st=0.09:d=0.21:curve=qsin", 0.50))

    # ---- scratch/ (3: record-scratch giả lập — bất ngờ/"khựng") ----
    # noise sweep NHANH: nhiễu qua bandpass quét + tremolo nhanh (giật) mô phỏng
    # tiếng kim đĩa bị kéo ngược. Ngắn, RÕ (âm lượng cao hơn transition).
    d.append(("scratch", "scratch_01", 0.28,
              "anoisesrc=color=pink:r=48000",
              "bandpass=f=1200:width_type=h:w=1600,tremolo=f=30:d=0.8,"
              "afade=t=in:st=0:d=0.01:curve=exp,"
              "afade=t=out:st=0.14:d=0.14:curve=tri", 0.62))
    d.append(("scratch", "scratch_fast_02", 0.22,
              "anoisesrc=color=white:r=48000",
              "bandpass=f=1600:width_type=h:w=2000,tremolo=f=40:d=0.9,"
              "afade=t=in:st=0:d=0.008:curve=exp,"
              "afade=t=out:st=0.10:d=0.12:curve=tri", 0.60))
    d.append(("scratch", "scratch_low_03", 0.30,
              "anoisesrc=color=brown:r=48000",
              "bandpass=f=800:width_type=h:w=1200,tremolo=f=24:d=0.75,"
              "afade=t=in:st=0:d=0.01:curve=exp,"
              "afade=t=out:st=0.16:d=0.14:curve=tri", 0.62))

    # ---- sad/ (3: nốt trầm buồn / piano trầm ngắn — đoạn buồn) ----
    # sine MỀM trầm ngân, fade dài như 1 nốt piano buồn buông. Âm lượng nhỏ.
    d.append(("sad", "note_low_01", 0.60,
              "sine=frequency=220:r=48000",   # A3
              "lowpass=f=900,afade=t=in:st=0:d=0.02:curve=exp,"
              "afade=t=out:st=0.10:d=0.50:curve=qsin", 0.46))
    d.append(("sad", "note_soft_02", 0.66,
              "sine=frequency=196:r=48000",   # G3
              "lowpass=f=800,afade=t=in:st=0:d=0.02:curve=exp,"
              "afade=t=out:st=0.12:d=0.54:curve=qsin", 0.44))
    d.append(("sad", "note_deep_03", 0.70,
              "sine=frequency=165:r=48000",   # E3
              "lowpass=f=700,afade=t=in:st=0:d=0.02:curve=exp,"
              "afade=t=out:st=0.14:d=0.56:curve=qsin", 0.46))

    # ---- drumroll/ (2: trống dồn ngắn TĂNG DẦN trước cao trào) ----
    # nhiễu nâu qua lowpass (giống mặt trống) + tremolo NHANH (dồn) + fade IN
    # dài (to dần tới đỉnh) rồi cắt nhanh -> hiệu ứng trống dồn build-up.
    d.append(("drumroll", "roll_01", 0.60,
              "anoisesrc=color=brown:r=48000",
              "lowpass=f=350,tremolo=f=22:d=0.95,"
              "afade=t=in:st=0:d=0.50:curve=ipar,"
              "afade=t=out:st=0.55:d=0.05:curve=tri", 0.58))
    d.append(("drumroll", "roll_fast_02", 0.50,
              "anoisesrc=color=brown:r=48000",
              "lowpass=f=420,tremolo=f=30:d=0.95,"
              "afade=t=in:st=0:d=0.42:curve=ipar,"
              "afade=t=out:st=0.46:d=0.04:curve=tri", 0.58))

    return d


def _build(category: str, name: str, dur: float, src: str, filt: str,
           peak: float) -> Path:
    """Sinh 1 file WAV (48kHz mono, pcm_s16le) từ định nghĩa. Trả path."""
    out_dir = SFX_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.wav"
    # chuẩn hoá nhẹ về đỉnh mong muốn: alimiter đỉnh + volume — không dùng
    # loudnorm 2-pass (chậm, và với xung rất ngắn dễ đội nền). Dùng
    # dynaudnorm nhẹ để san đều rồi ép đỉnh bằng alimiter.
    chain = (f"{filt},aresample=48000,"
             f"alimiter=limit={peak:.3f},"
             f"volume={peak:.3f}")
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-t", f"{dur:.3f}", "-i", src,
        "-ac", "1", "-ar", "48000",
        "-af", chain,
        "-c:a", "pcm_s16le", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       creationflags=_CREATE_NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi khi sinh {category}/{name}:\n{r.stderr}")
    return out


def main() -> int:
    defs = _defs()
    print(f"Sinh {len(defs)} file SFX vào {SFX_DIR} ...")
    by_cat: dict[str, int] = {}
    total_bytes = 0
    for category, name, dur, src, filt, peak in defs:
        out = _build(category, name, dur, src, filt, peak)
        sz = out.stat().st_size
        total_bytes += sz
        by_cat[category] = by_cat.get(category, 0) + 1
        print(f"  {category}/{out.name}  ({dur:.2f}s, {sz / 1024:.1f} KB)")
    print("---")
    for c in ("transition", "impact", "riser", "reveal", "pop",
              "suspense", "comedy", "scratch", "sad", "drumroll"):
        print(f"  {c}: {by_cat.get(c, 0)} file")
    print(f"TỔNG: {len(defs)} file, {total_bytes / 1024:.1f} KB "
          f"({total_bytes / 1048576:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
