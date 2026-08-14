# -*- coding: utf-8 -*-
"""KHO DÙNG CHUNG cho các phép đo THAY GIỌNG — cắt video thật, chép lời, tách nhạc.

Vì sao tách ra file riêng: mọi phép đo dưới đây phải chạy **NHIỀU LƯỢT** (LLM
không tiền định — bài học cổng 53: tỉ lệ dịch lại 0% · 21,7% · 39,1% giữa 3
lượt cùng video cùng mã). Chép lời Groq và tách Demucs thì TIỀN ĐỊNH và đắt
(Demucs ~25 giây/phút phim), nên đóng băng vào cache; phần LLM/TTS mới chạy
lại mỗi lượt.

**KHÔNG BAO GIỜ đụng file trong `Downloads\\Video`** — chỉ đọc và cắt ra bản
sao trong thư mục làm việc của repo.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _f in (sys.stdout, sys.stderr):     # console cp1252 -> hỏng ngay dòng print
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

from config import settings  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

KHO = Path(r"C:\Users\Admin\Downloads\Video")
LAM = REPO / "_do_tg_kho"
CACHE = REPO / "_do_tg_cache.json"

#: Video THẬT của anh Hùng. Trung = nguồn Douyin (đọc lời phim, nói DÀY — đúng
#: ca xấu nhất cho khớp thời gian); Anh = video reup Mỹ.
NGUON = [
    ("zh", KHO / "Kênh Douyin — 20 video" /
     "一群人均不满十二岁的，非洲童子军，残暴至极 #我的观影报告 #电影解说 #影视解说.mp4"),
    ("zh2", KHO / "Kênh Douyin — 20 video" /
     "上集，一帮非洲孩子，被军阀洗脑残暴至极 #我的观影报告 #电影解说 #悬疑电影 #人性.mp4"),
    ("en", KHO / "GOING BACK TO OUR OLD HOUSE.mp4"),
    # BẢN SAO ĐÓNG BĂNG — xem `DU_PHONG` bên dưới.
    ("zh_ep12", Path(r"D:\claude\_do_che_chu\nguon\zh_ep12.mp4")),
    ("zh_dongho", Path(r"D:\claude\_do_che_chu\nguon\zh_dongho.mp4")),
]

#: **KHO TRÊN ĐĨA ĐỔI THEO THỜI GIAN — ĐÃ LÀM HỎNG PHÉP ĐO MỘT LẦN.** Cổng 47
#: CA2 từng báo `2/8` thay vì `4/8` và phải bisect mới biết không phải hồi quy
#: mã, mà là `Downloads\Video\video hàn` bị xoá. Tới 14/08/2026 thì cả thư mục
#: `Kênh Douyin — 20 video` cũng RỖNG: hai nguồn `zh`/`zh2` ở trên trỏ vào chỗ
#: KHÔNG CÒN GÌ -> mọi phép đo thay giọng chết ngay dòng đầu.
#:
#: Bản sao Douyin đóng băng ở `_do_che_chu\nguon` (đã dùng cho cổng 56) không
#: đi đâu cả. Thiếu nguồn gốc thì lấy bản sao đó — ghi RA MÀN HÌNH là đang
#: dùng bản thay thế, không im lặng đổi mẫu số rồi báo số như thường.
DU_PHONG = {
    "zh": Path(r"D:\claude\_do_che_chu\nguon\zh_ep12.mp4"),
    "zh2": Path(r"D:\claude\_do_che_chu\nguon\zh_dongho.mp4"),
}

GIAY = 90.0     # cắt 90 giây đầu mỗi video


def _ff(args: list[str]) -> None:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {r.stderr[:400]}")


def _cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def _luu(c: dict) -> None:
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def chuan_bi(ten: str, can_nhac: bool = False) -> dict:
    """Trả {video, wav, tong, chep, cau, nhac} cho 1 nguồn — có cache."""
    src = dict(NGUON)[ten]
    thay = False
    if not src.exists() and ten in DU_PHONG:
        src, thay = DU_PHONG[ten], True
        print(f"  [{ten}] NGUỒN GỐC KHÔNG CÒN -> dùng bản sao đóng băng "
              f"{src.name} (mẫu số ĐÃ ĐỔI, đừng so thẳng với số cũ)")
    if not src.exists():
        raise FileNotFoundError(f"không thấy video: {src}")
    # Nguồn thay thế phải có THƯ MỤC và KHOÁ CACHE RIÊNG — dùng lại khoá cũ là
    # lấy bản chép lời của video KHÁC mà không một dòng báo.
    d = LAM / (f"{ten}__dp" if thay else ten)
    d.mkdir(parents=True, exist_ok=True)
    vid = d / "cat.mp4"
    if not vid.exists():
        _ff(["-i", str(src), "-t", f"{GIAY}", "-c", "copy", str(vid)])
    wav = d / "goc.wav"
    tong = tg.probe_duration(wav) if wav.exists() else 0.0
    if tong <= 0:
        tong = tg.tach_wav(vid, wav)

    c = _cache()
    khoa = f"chep|{ten}|{GIAY}" + (f"|dp:{src.name}" if thay else "")
    if khoa not in c:
        print(f"  [{ten}] chép lời bằng Groq (lần đầu, sẽ cache)...")
        c[khoa] = tg.chep_loi(wav)
        _luu(c)
    chep = c[khoa]
    cau = tg.cau_tu_transcript(chep)

    nhac = d / "nhac.wav"
    if can_nhac and not nhac.exists():
        print(f"  [{ten}] tách nhạc bằng Demucs (lần đầu, ~{GIAY / 2.4:.0f}s)...")
        t = tg.tach_giong(wav, d / "tach", cach="demucs")
        import shutil
        shutil.copy2(t["nhac"], nhac)

    return {"ten": ten, "video": vid, "wav": wav, "tong": tong,
            "chep": chep, "cau": cau,
            "nhac": nhac if nhac.exists() else None,
            "ngon_ngu": (chep.get("language") or "")[:2].lower()}


def tom_tat() -> None:
    for ten, _ in NGUON:
        k = chuan_bi(ten)
        tho = sum(len(c["text"]) for c in k["cau"])
        print(f"{ten:>4} · {k['tong']:6.2f}s · {len(k['cau']):3d} câu · "
              f"{tho:5d} ký tự · nhãn {k['chep'].get('language')}")


if __name__ == "__main__":
    tom_tat()
