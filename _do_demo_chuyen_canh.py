# -*- coding: utf-8 -*-
"""XUẤT DEMO CHUYỂN CẢNH ra `D:\\hieu-ung-demo-v2\\` để anh Hùng XEM trước.

Chạy: .venv\\Scripts\\python _do_demo_chuyen_canh.py

Mỗi ca xuất 2 file cạnh nhau — `_TAT` (cắt thẳng như bản đang chạy) và bản có
chuyển cảnh — để so bằng MẮT ngay trong 1 thư mục. Kèm file `_ghi_chu.txt` ghi
đúng kiểu xfade nào đã dùng ở chỗ nối nào và vì sao chọn kiểu đó.

Có ĐỐT PHỤ ĐỀ chạy chữ vào demo: mắt người phát hiện lệch phụ đề nhanh hơn mọi
số đo, mà lệch phụ đề đúng là rủi ro lớn nhất của việc này.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.gettempdir()) / f"demo_xf_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu          # noqa: E402
from config import settings                      # noqa: E402

RA = Path(r"D:\hieu-ung-demo-v2")
THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")
_NOWIN = 0x08000000
_LOAI_VN = {"nguoc": "nhảy NGƯỢC thời gian (hook-first) -> chuyển dứt khoát",
            "lien": "gần liền mạch (<=1,2s) -> hoà mềm",
            "chot": "đoạn kế rất ngắn (câu chốt) -> nhấn",
            "xa": "nhảy xa, đổi bối cảnh -> mờ dần trung tính"}


def ass_chay_chu(dst: Path, dai: float) -> Path:
    """Phụ đề chạy chữ đếm giây — LỆCH là thấy ngay bằng mắt."""
    def hms(v: float) -> str:
        return f"{int(v // 3600)}:{int(v // 60) % 60:02d}:{v % 60:05.2f}"
    dong, t, i = [], 0.0, 0
    while t < dai:
        dong.append(f"Dialogue: 0,{hms(t)},{hms(min(dai, t + 0.5))},D,,0,0,0,,"
                    "{\\an2}" + f"giay {t:.1f}")
        t += 0.5
        i += 1
    dst.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,"
        "SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
        "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: D,Arial,96,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,6,0,2,60,60,200,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,"
        "MarginV,Effect,Text\n" + "\n".join(dong) + "\n", encoding="utf-8")
    return dst


def dai_video(p: Path) -> float:
    r = subprocess.run([settings.FFPROBE_PATH, "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


CA = [
    ("2doan_hookfirst", [(60.0, 70.0), (20.0, 30.0)], "vua",
     "2 ĐOẠN kiểu hook-first: đoạn 60-70s đứng TRƯỚC đoạn 20-30s (NGƯỢC "
     "thời gian) — đây là cảnh app hay dùng nhất."),
    ("3doan_manh", [(60.0, 68.0), (20.0, 28.0), (120.0, 126.0)], "manh",
     "3 ĐOẠN, mức MẠNH (trượt/khép rõ) — xem hiệu ứng đậm nhất trông thế nào."),
    ("3doan_nhe", [(60.0, 68.0), (20.0, 28.0), (120.0, 126.0)], "nhe",
     "3 ĐOẠN, mức NHẸ = MẶC ĐỊNH của app. So với file _manh cùng mốc cắt."),
    ("4doan_lienmach", [(300.0, 308.0), (309.0, 316.0), (316.5, 318.0),
                        (500.0, 512.0)], "vua",
     "4 ĐOẠN có chỗ nối gần LIỀN MẠCH (309 ngay sau 308) và 1 câu CHỐT rất "
     "ngắn (1,5s) — kiểm luật chọn kiểu theo nội dung."),
]


def main() -> int:
    vids = [p for p in (THUNG.rglob("*.mp4") if THUNG.exists() else [])
            if p.stat().st_size > 5_000_000
            and any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" for c in str(p))]
    if not vids:
        print(f"DỪNG: không thấy video Nhật trong {THUNG}")
        return 2
    src = vids[0]
    RA.mkdir(parents=True, exist_ok=True)
    print(f"[nguồn] {src.name}")
    print(f"[ra]    {RA}")
    print(f"[encoder] {fu.detect_encoder()} · trần ffmpeg song song "
          f"{fu.so_ffmpeg_song_song()}")
    ghi: list[str] = [
        "DEMO CHUYỂN CẢNH Ở CHỖ GHÉP ĐOẠN (xfade) — nhánh hieu-ung-video",
        f"nguồn: {src.name}",
        "",
        "Mỗi ca có 2 file: *_TAT.mp4 (cắt thẳng như bản đang chạy) và "
        "*_<mức>.mp4 (có chuyển cảnh). Mở cạnh nhau mà so.",
        "Phụ đề 'giay X.X' được đốt vào hình: nếu chuyển cảnh làm LỆCH thì số "
        "giây trên chữ sẽ không còn khớp giữa 2 file.",
        "",
    ]
    for ten, segs, muc, mota in CA:
        tong = sum(e - s for s, e in segs)
        ass = str(ass_chay_chu(_SB / f"{ten}.ass", tong))
        xf = fu.chon_chuyen_canh(segs, muc)
        loai = [fu._loai_cho_noi(segs, i) for i in range(len(segs) - 1)]
        print(f"\n=== {ten} ({len(segs)} đoạn, mức {muc}) ===")
        ghi += [f"--- {ten} ---", mota,
                f"mốc cắt: {segs}  (tổng {tong:.1f}s)"]
        for i, (k, d) in enumerate(xf):
            moc = sum(e - s for s, e in segs[:i + 1])
            ghi.append(f"  chỗ nối {i + 1} ở giây {moc:.1f}: "
                       f"{k} {d:.2f}s — {_LOAI_VN.get(loai[i], loai[i])}")
        for nhan, m in (("TAT", "tat"), (muc, muc)):
            out = RA / f"{ten}_{nhan}.mp4"
            t0 = time.perf_counter()
            try:
                fu.export_canvas_clip(
                    str(src), str(out), segs, (0.5, 0.42, 0.98), bg="blur",
                    out_w=1080, out_h=1920, ass_path=ass,
                    fx_fade=False, fx_whoosh=False, chuyen_canh=m)
            except Exception as e:                       # noqa: BLE001
                print(f"  LỖI {nhan}: {type(e).__name__}: {e}")
                ghi.append(f"  LỖI {nhan}: {e}")
                continue
            w = round(time.perf_counter() - t0, 2)
            d = dai_video(out)
            kb = out.stat().st_size // 1024
            print(f"  {out.name:34s} {d:7.3f}s  {kb:7d} KB  wall {w}s")
            ghi.append(f"  {out.name}: dài {d:.3f}s · {kb} KB · xuất {w}s")
        ghi.append("")
    (RA / "_ghi_chu.txt").write_text("\n".join(ghi), encoding="utf-8")
    print(f"\nXong. Ghi chú: {RA / '_ghi_chu.txt'}")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
