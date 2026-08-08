# -*- coding: utf-8 -*-
r"""VÌ SAO lượt e2e chép lời bằng `faster-whisper` (MÁY) chứ không phải GROQ (mây)?

    .venv\Scripts\python _ra_chep_loi.py

Đây là chỗ nguy hiểm đã ghi trong CLAUDE.md (cổng 22): Groq lỗi -> app **tụt về
whisper MÁY, chậm hàng chục lần, KHÔNG báo lỗi**. Lượt e2e 08/08/2026 ghi
`engine = faster-whisper:large-v3` cho CẢ 7 video trong khi 38/38 key Groq đo ra
còn SỐNG -> phải biết vì sao.

Cách đo: tách 60 giây tiếng từ nguồn Nhật thật rồi gọi THẲNG `_transcribe_groq`
để xem nó ném lỗi gì (nếu có), rồi gọi `transcribe()` xem nó chọn đường nào.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="ra_cl_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "t.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "s.ini")
os.environ["WHISPER_PROVIDER"] = "groq"

_env = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo" / ".env"
if _env.exists():
    for ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        k, _, v = ln.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and v:
            os.environ.setdefault(k, v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")
DUOI = "初めて両想いだと気づいた瞬間.mp4"


def main() -> int:
    src = next((p for p in THUNG.rglob("*.mp4") if p.name.endswith(DUOI)), None)
    if not src:
        print("DỪNG: không thấy nguồn.")
        return 2
    from config import settings
    from app.core import transcribe as TR

    print(f"WHISPER_PROVIDER = {settings.WHISPER_PROVIDER!r}")
    print(f"WHISPER_DEVICE   = {settings.WHISPER_DEVICE!r}")
    print(f"số key Groq      = {len(settings.groq_keys())}")
    print(f"faster-whisper có trên máy? {TR.is_available()}")
    print(f"provider_ready() = {TR.provider_ready()}")

    wav = _SB / "a.mp3"
    subprocess.run([settings.FFMPEG_PATH, "-y", "-v", "error", "-t", "60",
                    "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                    "-b:a", "64k", str(wav)], check=True,
                   creationflags=0x08000000)
    print(f"\naudio thử: {wav.stat().st_size/1024:.0f} KB (60 giây)")

    print("\n── gọi THẲNG _transcribe_groq ──")
    try:
        d = TR._transcribe_groq(str(wav), None, None)
        segs = d.get("segments") or []
        print(f"  OK · {len(segs)} đoạn · {len(d.get('words') or [])} từ · "
              f"ngôn ngữ {d.get('language')!r} · engine {d.get('engine')!r}")
        print(f"  «{' '.join(s.get('text','') for s in segs)[:100]}»")
    except Exception as e:      # noqa: BLE001
        print(f"  NÉM LỖI -> {type(e).__name__}: {e}")

    print("\n── gọi transcribe() như app ──")
    try:
        d = TR.transcribe(str(wav))
        print(f"  engine THỰC = {d.get('engine')!r} · "
              f"{len(d.get('segments') or [])} đoạn")
    except Exception as e:      # noqa: BLE001
        print(f"  NÉM LỖI -> {type(e).__name__}: {e}")
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
