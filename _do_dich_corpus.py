# -*- coding: utf-8 -*-
"""DỰNG CORPUS THẬT cho việc đo CHẤT LƯỢNG DỊCH (Trung -> Việt).

Chép lời video THẬT của anh Hùng bằng Groq rồi cất ra `_do_dich_cache.json`
để mọi phép đo sau chạy trên CÙNG một corpus (bài học cổng 47: corpus không
đóng băng thì con số là của KHO ĐĨA chứ không phải của MÃ).

AN TOÀN: video gốc trong `Downloads\\longtieng` **CHỈ ĐỌC** — chép ra hộp cát
trước khi đụng tới, không xoá/đổi tên/ghi đè gì trong thư mục nguồn.

Chạy: `.venv\\Scripts\\python -u _do_dich_corpus.py`
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
CACHE = REPO / "_do_dich_cache.json"
FFMPEG = REPO / "bin" / "ffmpeg.exe"


def _don(san: Path) -> None:
    shutil.rmtree(san, ignore_errors=True)


def _quet_san_cu() -> None:
    """Dọn hộp cát của những lần chạy trước (luật: hộp cát tự dọn)."""
    for p in REPO.glob("bq_dichcorpus_*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def rut_tieng(vid: Path, ra: Path) -> None:
    cmd = [str(FFMPEG), "-y", "-i", str(vid), "-vn", "-ac", "1",
           "-ar", "16000", "-c:a", "pcm_s16le", str(ra)]
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    if r.returncode != 0 or not ra.exists():
        raise RuntimeError(f"ffmpeg rút tiếng lỗi: {r.stderr[-400:]!r}")


def main() -> int:
    _quet_san_cu()
    if CACHE.exists():
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"ĐÃ CÓ cache: {len(d['cau'])} câu · {d['video']}")
        return 0

    vids = sorted(NGUON.glob("*.mp4"))
    if not vids:
        print(f"KHÔNG thấy video trong {NGUON}")
        return 2
    vid = vids[0]
    print(f"video: {vid.name} ({vid.stat().st_size/1e6:.1f} MB)")

    san = REPO / f"bq_dichcorpus_{os.getpid()}"
    san.mkdir(parents=True, exist_ok=True)
    atexit.register(_don, san)

    # CHÉP RA hộp cát — tuyệt đối không đụng file gốc
    ban_sao = san / vid.name
    shutil.copy2(vid, ban_sao)
    wav = san / "tieng.wav"
    t0 = time.time()
    rut_tieng(ban_sao, wav)
    print(f"rút tiếng: {time.time()-t0:.1f}s · {wav.stat().st_size/1e6:.1f} MB")

    from app.core.transcribe import transcribe
    from app.core.thay_giong import cau_tu_transcript

    t0 = time.time()
    d = transcribe(str(wav))
    print(f"chép lời: {time.time()-t0:.1f}s · nhãn ngôn ngữ = {d.get('language')!r}")

    cau = cau_tu_transcript(d)
    print(f"số câu: {len(cau)} · thời lượng {d.get('duration', 0):.2f}s")
    for c in cau[:5]:
        print(f"  [{c['start']:6.2f}-{c['end']:6.2f}] {c['text']}")

    CACHE.write_text(json.dumps({
        "video": vid.name,
        "duration": d.get("duration", 0),
        "language": d.get("language", ""),
        "cau": cau,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"đã ghi {CACHE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
