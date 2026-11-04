# -*- coding: utf-8 -*-
"""MỞ RỘNG KHO TIẾNG ĐỘNG LẦN 2 (02/11/2026) — ĐA DẠNG HỌ TIẾNG, KHÔNG CHỈ SỐ FILE.

VÌ SAO (đo trên nhật ký dây chuyền THẬT 22/10-02/11, 1.317 Part / 5.160 lượt chèn):
  * 3 HỌ tiếng (`impactGlass_light`, `impactBell_heavy`, `impactGlass_medium`)
    chiếm **51%** mọi lượt chèn; riêng `impactGlass_light` **28%**.
  * kho có 262 file nhưng chỉ ~59 HỌ thật (file `_v2/_v3` là cùng một tiếng đổi
    cao độ) -> nghe "đơn điệu" là đúng.
Lượt này THÊM HỌ MỚI (tiếng đấm, gỗ, vải phẩy, lật trang, rút dao, xu, cửa kẽo
kẹt, ly thuỷ tinh...) chứ không đẻ thêm biến thể của họ cũ.

NGUỒN — chỉ 2 loại, đều dùng THƯƠNG MẠI được, không cần ghi công:
  1. Kenney.nl (CC0 1.0) — các gói `impact-sounds`, `rpg-audio`,
     `interface-sounds`; tải bằng chính đường của trang (`/download-link/<hex>`).
     Chỉ lấy các HỌ chưa có trong kho. Kèm `License.txt` gốc đã kiểm (CC0).
  2. Tự sinh bằng ffmpeg `lavfi` (0 mẫu của bên thứ ba) — tiếng cartoon trượt
     còi / bloop cho nhóm `comedy` (trước đây 0 lượt dùng vì kho quá nghèo) và
     (bản "reverse swell" cho `riser` đã THỬ RỒI BỎ: đỉnh ở cuối là bản chất
     nên app luôn loại vì vào chậm).

Chuẩn hoá Y HỆT `tools/fetch_sfx.py`: mono 48 kHz, dynaudnorm + alimiter, Opus
32k. Sau khi chạy phải chạy lại `tools/do_muc_sfx.py` (bảng mức) — các bộ lọc
loa điện thoại / vào chậm / độ sáng của app tự loại file không dùng được.

    python tools/them_sfx_v2.py <thư_mục_đã_giải_nén>          # xem trước
    python tools/them_sfx_v2.py <thư_mục_đã_giải_nén> --ghi    # ghi thật
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "app" / "assets" / "sfx"
FF = str(ROOT / "bin" / "ffmpeg.exe")
NOWIN = 0x08000000 if sys.platform == "win32" else 0
LOC = "dynaudnorm=f=100:g=5,alimiter=limit=0.9,volume=0.9"
#: Cắt khoảng lặng ĐẦU file: đo lần 1 `creak`/`bookFlip` có đỉnh rơi 0,40-0,55 s
#: sau lúc bắt đầu -> app loại (vào chậm không đánh dấu được điểm nhấn).
CAT_DAU = "silenceremove=start_periods=1:start_threshold=-38dB"
#: BẢN HỢP LOA ĐIỆN THOẠI cho tiếng đấm/gỗ: đo lần 1 hụt 7-28 dB dưới 300 Hz
#: (app loại mọi file hụt quá 6 dB). Cắt trầm + nhấn dải 2-4 kHz = tiếng "chát"
#: kiểu dựng phim ngắn, vẫn đọc ra là cú đấm/gõ gỗ trên loa nhỏ.
#: Lần đo 2 (highpass 260 Hz 2 cực) còn 14 file hụt 6-13 dB -> 2 tầng 320 Hz.
HOP_LOA = ("highpass=f=320,highpass=f=320,"
           "equalizer=f=2600:t=q:w=1.2:g=6")

#: `doorClose` ĐÃ THỬ RỒI BỎ: tiếng ĐÓNG CỬA quá nghĩa đen, và vì rất sáng
#: nó chiếm 15% mọi cú impact trong phép phát lại.
#: `impactWood_heavy` / `impactSoft_heavy` ĐÃ THỬ RỒI BỎ: thân tiếng nằm dưới
#: 300 Hz, cắt trầm xong còn hụt 9-13 dB = câm trên loa điện thoại.
#: (gói, tiền tố tên file trong gói, nhóm app, số file tối đa)
CHON = [
    ("impact-sounds", "impactPunch_heavy", "impact", 5),
    ("impact-sounds", "impactPunch_medium", "impact", 5),
    ("impact-sounds", "impactWood_medium", "impact", 3),
    ("impact-sounds", "impactPlate_medium", "impact", 3),
    ("impact-sounds", "impactPlank_medium", "impact", 3),
    ("impact-sounds", "impactTin_medium", "impact", 2),
    ("impact-sounds", "impactMetal_light", "impact", 3),
    ("rpg-audio", "cloth", "transition", 4),
    ("rpg-audio", "bookFlip", "transition", 3),
    ("rpg-audio", "drawKnife", "transition", 3),
    ("rpg-audio", "knifeSlice", "transition", 2),
    ("rpg-audio", "clothBelt", "transition", 2),
    ("rpg-audio", "bookPlace", "pop", 3),
    ("rpg-audio", "metalClick", "pop", 1),
    ("rpg-audio", "metalLatch", "pop", 1),
    ("rpg-audio", "beltHandle", "pop", 2),
    ("rpg-audio", "handleSmallLeather", "pop", 2),
    ("rpg-audio", "handleCoins", "reveal", 2),
    ("rpg-audio", "creak", "suspense", 3),
    ("interface-sounds", "glass_", "pop", 6),
    ("interface-sounds", "drop_", "pop", 4),
    ("interface-sounds", "pluck_", "pop", 2),
    ("interface-sounds", "glitch_", "scratch", 4),
    ("interface-sounds", "bong", "reveal", 1),
]

#: Tiếng TỰ SINH: (nhóm, tên, nguồn lavfi, chuỗi filter). Không mẫu bên thứ ba.
#: Trượt còi: sin quét tần số theo thời gian (biểu thức pha tích phân) — cùng
#: cách `gen_sfx.py` sinh riser, chỉ khác dải và độ dài.
TU_SINH = [
    ("comedy", "s2_truot_coi_len",
     "aevalsrc='0.6*sin(2*PI*(600*t+1400*t*t))*exp(-1.2*t)':s=48000:d=0.55",
     "afade=t=in:d=0.02,afade=t=out:st=0.4:d=0.15"),
    ("comedy", "s2_truot_coi_xuong",
     "aevalsrc='0.6*sin(2*PI*(1900*t-1300*t*t))*exp(-1.0*t)':s=48000:d=0.6",
     "afade=t=in:d=0.02,afade=t=out:st=0.45:d=0.15"),
    ("comedy", "s2_bloop",
     "aevalsrc='0.7*sin(2*PI*(300*t+900*t*t))*exp(-9*t)':s=48000:d=0.3",
     "afade=t=in:d=0.005"),
    ("comedy", "s2_bloop_doi",
     "aevalsrc='0.6*(sin(2*PI*(350*t+1500*t*t))*exp(-12*t)"
     "+sin(2*PI*(500*(t-0.14)+1800*(t-0.14)*(t-0.14)))*exp(-12*(t-0.14))"
     "*gte(t,0.14))':s=48000:d=0.42",
     "afade=t=in:d=0.005"),
    ("comedy", "s2_lo_xo",
     "aevalsrc='0.5*sin(2*PI*(440+180*sin(2*PI*14*t))*t)*exp(-3.5*t)'"
     ":s=48000:d=0.7",
     "afade=t=in:d=0.005,afade=t=out:st=0.55:d=0.15"),
    ("transition", "s2_vut_gio",
     "anoisesrc=d=0.45:c=pink:s=23:a=0.9",
     "bandpass=f=1800:w=1400,volume='sin(PI*t/0.45)':eval=frame"),
]


def _chay(cmd: list) -> bool:
    r = subprocess.run(cmd, capture_output=True, creationflags=NOWIN)
    return r.returncode == 0


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("goc", help="thư mục chứa các gói Kenney đã giải nén")
    ap.add_argument("--ghi", action="store_true")
    a = ap.parse_args()
    goc = Path(a.goc)
    ghi_nhan = {"nguon_kenney": "https://kenney.nl/assets/<goi> — CC0 1.0",
                "tu_sinh": "ffmpeg lavfi (tools/them_sfx_v2.py) — CC0 1.0",
                "files": []}
    so = 0
    for goi, tien_to, nhom, toi_da in CHON:
        lic = goc / goi / "License.txt"
        if not lic.is_file() or "CC0" not in lic.read_text("utf-8", "replace"):
            print(f"!! {goi}: không thấy License.txt CC0 -> BỎ cả gói")
            continue
        ung = sorted(p for p in (goc / goi).rglob("*")
                     if p.suffix.lower() in (".ogg", ".wav")
                     and p.name.startswith(tien_to))
        for src in ung[:toi_da]:
            ten = f"k2_{goi.split('-')[0]}_{src.stem}.opus"
            dst = SFX / nhom / ten
            print(f"  {nhom:<10} {ten}")
            so += 1
            loc = CAT_DAU + ","
            if any(x in tien_to for x in ("Punch", "Wood", "Plank", "Soft",
                                           "glitch", "bong", "cloth")):
                loc += HOP_LOA + ","
            if a.ghi and not dst.exists():
                ok = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                            "-i", str(src), "-ac", "1", "-ar", "48000",
                            "-af", loc + LOC, "-c:a", "libopus", "-b:a", "32k",
                            "-vbr", "on", "-application", "audio", str(dst)])
                if not ok:
                    print("    LỖI ffmpeg")
                    continue
            if a.ghi and dst.exists():
                ghi_nhan["files"].append({"file": f"{nhom}/{ten}",
                                          "nguon": f"kenney {goi}/{src.name}",
                                          "license": "CC0-1.0",
                                          "sha256": _sha(dst)})
    for nhom, ten, nguon, loc in TU_SINH:
        dst = SFX / nhom / f"{ten}.opus"
        print(f"  {nhom:<10} {dst.name} (tự sinh)")
        so += 1
        if a.ghi and not dst.exists():
            ok = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", nguon, "-af", f"{loc},{LOC}",
                        "-ac", "1", "-ar", "48000", "-c:a", "libopus",
                        "-b:a", "32k", "-vbr", "on", "-application", "audio",
                        str(dst)])
            if not ok:
                print("    LỖI ffmpeg")
                continue
        if a.ghi and dst.exists():
            ghi_nhan["files"].append({"file": f"{nhom}/{dst.name}",
                                      "nguon": "tự sinh ffmpeg lavfi",
                                      "license": "CC0-1.0",
                                      "sha256": _sha(dst)})
    print(f"Tổng: {so} file")
    if a.ghi:
        (SFX / "v2-provenance.json").write_text(
            json.dumps(ghi_nhan, ensure_ascii=False, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
