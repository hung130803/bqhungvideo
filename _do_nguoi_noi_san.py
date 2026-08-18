"""SÂN ĐO cho bộ nhận biết NGƯỜI KỂ CHUYỆN vs NGƯỜI THẬT TRONG KHUNG.

Bước 1: COPY 4 video anh Hùng đang làm ra sân riêng (KHÔNG đụng bản gốc ở
Downloads\\longtieng), tách wav, chép lời qua ĐÚNG CỬA `thay_giong.chep_loi`
(Groq whisper-large-v3), cắt thành CÂU rồi ghi JSON.

Chạy: python -u _do_nguoi_noi_san.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
SAN = GOC / "_kq_nn"
VID = SAN / "video"
WAV = SAN / "wav"
FF = str(GOC / "bin" / "ffmpeg.exe")
FP = str(GOC / "bin" / "ffprobe.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: Tên ngắn không dấu / không ký tự Trung cho từng video (đặt tay, ổn định).
TEN = {
    "一款可以预测死亡时间的软件有多炸裂#倒忌时": "v1_dutu",
    "从来没有一部电影能让我从头尿到尾#精选 #抖音精选 #悬疑推理": "v2_nieu",
    "八位好莱坞导演联手拍的电影有多厉害#电影解说": "v3_8daodien",
    "#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐": "v4_khuyendung",
}


def _dai(p: Path) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       text=True, creationflags=_NO_WIN, timeout=120)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def chuan_bi() -> list[dict]:
    VID.mkdir(parents=True, exist_ok=True)
    WAV.mkdir(parents=True, exist_ok=True)
    ds = []
    for han, ten in TEN.items():
        src = NGUON / f"{han}.mp4"
        if not src.exists():
            print(f"  THIEU: {src}")
            continue
        dst = VID / f"{ten}.mp4"
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)          # COPY, gốc giữ nguyên
        w44 = WAV / f"{ten}_44k.wav"
        w16 = WAV / f"{ten}_16k.wav"
        if not w44.exists():
            subprocess.run([FF, "-y", "-v", "error", "-i", str(dst), "-vn",
                            "-ac", "2", "-ar", "44100", str(w44)],
                           check=True, creationflags=_NO_WIN, timeout=900)
        if not w16.exists():
            subprocess.run([FF, "-y", "-v", "error", "-i", str(dst), "-vn",
                            "-ac", "1", "-ar", "16000", str(w16)],
                           check=True, creationflags=_NO_WIN, timeout=900)
        # BẪY: ffmpeg mã 0 + file 0 KiB -> kiểm KÍCH THƯỚC + ĐỘ DÀI
        for w in (w44, w16):
            kb = w.stat().st_size / 1024
            dai = _dai(w)
            if kb < 8 or dai < 1.0:
                raise RuntimeError(f"wav rong: {w.name} {kb:.0f}KiB {dai:.2f}s")
        ds.append({"ten": ten, "video": str(dst), "wav44": str(w44),
                   "wav16": str(w16), "dai": round(_dai(dst), 3)})
        print(f"  {ten}: {ds[-1]['dai']:.1f}s  wav16 "
              f"{w16.stat().st_size / 2**20:.1f}MiB")
    return ds


def chep(ds: list[dict]) -> None:
    from app.core import thay_giong as tg
    for m in ds:
        out = SAN / f"chep_{m['ten']}.json"
        if out.exists():
            print(f"  {m['ten']}: da co ban chep, bo qua")
            continue
        t0 = time.time()
        d = tg.chep_loi(m["wav16"])
        cau = tg.cau_tu_transcript(d, gop_toi_da=12.0)
        out.write_text(json.dumps(
            {"ten": m["ten"], "dai": m["dai"], "lang": d.get("language"),
             "so_tu": len(d.get("words") or []),
             "segments": d.get("segments") or [],
             "words": d.get("words") or [],
             "cau": cau}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {m['ten']}: {len(cau)} cau, lang={d.get('language')}, "
              f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    print("== CHUAN BI (copy + tach wav) ==")
    ds = chuan_bi()
    (SAN / "nguon.json").write_text(json.dumps(ds, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print("== CHEP LOI (Groq whisper-large-v3) ==")
    chep(ds)
    print("XONG")
