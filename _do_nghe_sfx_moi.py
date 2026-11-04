# -*- coding: utf-8 -*-
"""FILE NGHE THỬ tiếng động TRƯỚC / SAU (02/11/2026).

Cùng video, cùng đoạn cắt, cùng hiệu ứng hình (chọn theo số đo -> tiền định),
chỉ khác cách chọn + kho tiếng:
  A_TRUOC = luật cũ + kho cũ (bỏ file k2_/s2_)   — `BQ_SFX_CU=1`
  B_SAU   = `sfx_chon` + kho mới
Cả hai chuẩn về -14 LUFS bằng chính `thay_giong.chuan_do_to` rồi đo lại bằng
`loudnorm` chạy RIÊNG. Ghi kèm danh sách tiếng đã chèn vào SO_DO.txt.
Nguồn chỉ ĐỌC; file ra ở `_NGHE_THU_ANH_HUNG/sfx_moi/`.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import thay_giong as TG  # noqa: E402

RA = REPO / "_NGHE_THU_ANH_HUNG" / "sfx_moi"
RA.mkdir(parents=True, exist_ok=True)
GOC = Path(r"D:\video ssmatool\video mỹ\kênh 112")
NGUON = [
    ("biker_tai_nan", GOC / "Shocking Crash Leaves Biker With No Memory!.mp4",
     [(30.0, 33.0), (3.0, 10.0), (10.5, 18.0), (20.0, 29.0), (33.5, 39.0)]),
    ("vui_nhon", GOC / "That was enough fun… 😂.mp4",
     [(15.0, 18.0), (1.0, 7.0), (7.4, 14.0), (18.5, 23.0)]),
    ("canh_sat", GOC / "The Cops Jumped Him 😨🫠.mp4",
     [(18.0, 21.0), (1.0, 8.0), (8.3, 14.0), (14.6, 18.0), (21.0, 24.5)]),
]
FF = str(REPO / "bin" / "ffmpeg.exe")
NW = 0x08000000 if os.name == "nt" else 0


def lufs(p: str) -> tuple:
    r = subprocess.run([FF, "-hide_banner", "-i", p, "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, creationflags=NW)
    t = r.stderr.decode("utf-8", "replace")
    j = json.loads(t[t.rindex("{"):t.rindex("}") + 1])
    return float(j["input_i"]), float(j["input_tp"])


def _cats(segs):
    """Loại chỗ nối ĐÚNG như dây chuyền thật (m1, theo nội dung chỗ nối)."""
    from app.modules import m1_highlight as M1
    return M1._context_join_categories(segs, {}, seed=1)


def xuat(src, segs, dst, cu: bool):
    lib = F._sfx_library()
    if cu:
        os.environ["BQ_SFX_CU"] = "1"
        F._SFX_LIB_CACHE = {k: [f for f in v if not os.path.basename(f)
                                .startswith(("k2_", "s2_"))]
                            for k, v in lib.items()}
    else:
        os.environ.pop("BQ_SFX_CU", None)
    log: list = []
    try:
        dur = sum(e - s for s, e in segs)
        F.export_canvas_clip(str(src), dst, segs, (0.5, 0.5, 1.0), bg="blur",
                             out_w=720, out_h=1280, encoder="libx264",
                             fx_whoosh=True, hieu_ung="nhe",
                             join_categories=_cats(segs),
                             tieng_dong_log=log,
                             chuyen_canh="nhe")
    finally:
        F._SFX_LIB_CACHE = lib
        os.environ.pop("BQ_SFX_CU", None)
    return log, dur


def main():
    dong = []
    for ten, src, segs in NGUON:
        if not src.is_file():
            print("thiếu nguồn", src)
            continue
        for nhan, cu in (("A_TRUOC", True), ("B_SAU", False)):
            tho = str(RA / f"_{ten}_{nhan}_tho.mp4")
            log, dur = xuat(src, segs, tho, cu)
            wav = str(RA / f"_{ten}_{nhan}.wav")
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", tho, "-vn",
                            "-ac", "2", "-ar", "48000", wav], check=True,
                           creationflags=NW)
            ra_wav = str(RA / f"{ten}_{nhan}_{len(log)}tieng.wav")
            TG.chuan_do_to(wav, ra_wav)
            # ghép hình gốc + tiếng đã chuẩn hoá -> file mp4 xem được
            mp4 = ra_wav[:-4] + ".mp4"
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", tho, "-i",
                            ra_wav, "-map", "0:v", "-map", "1:a", "-c:v",
                            "copy", "-c:a", "aac", "-b:a", "192k", mp4],
                           check=True, creationflags=NW)
            for x in (tho, wav, ra_wav):
                try:
                    os.remove(x)
                except OSError:
                    pass
            i, tp = lufs(mp4)
            s = (f"{ten} {nhan}: {len(log)} tiếng / {dur:.0f}s · I {i:.2f} "
                 f"LUFS · TP {tp:.2f} dBTP\n    " +
                 "\n    ".join(f"{x['giay']:6.2f}s {x['vai']:<9} "
                                f"{x['loai']:<10} {x['ten']}" for x in log))
            print(s)
            dong.append(s)
    (RA / "NGHE_THU.txt").write_text("\n".join(dong) + "\n", "utf-8")


if __name__ == "__main__":
    main()
