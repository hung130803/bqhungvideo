# -*- coding: utf-8 -*-
"""TRUY LỖI 'AI XEM HÌNH ra 0 mốc' — chạy TỪNG BƯỚC, in LỖI THẬT.

build_vision_digest nuốt mọi lỗi (`except: return []`) nên không biết chết ở
đâu. Script này gọi tay từng bước: bật cờ -> có key -> trích ảnh -> gọi vision.
"""
import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="vsbuoc_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
os.environ["VISION_CUT"] = "1"
from pathlib import Path as _P  # noqa: E402

_e = _P(os.environ.get("LOCALAPPDATA") or "") / "BQHungVideo" / ".env"
if _e.exists():
    for _ln in _e.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        if _k.strip() in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v.strip():
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from config import settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.core import vision_digest as VD  # noqa: E402
from app.core.ffmpeg_utils import extract_frame  # noqa: E402

SRC = r"C:\Users\Admin\Downloads\Video\Big Body OG Pred Gets Busted!.mp4"

print("── B1. cờ + key ──")
print(f"  USE_VISION={settings.USE_VISION} VISION_CUT={settings.VISION_CUT} "
      f"LIGHT_MODE={settings.LIGHT_MODE}")
print(f"  provider={llm.active_provider()} model={settings.GROQ_VISION_MODEL}")
print(f"  số key groq={len(settings.groq_keys())}")
print(f"  vision_digest_enabled={VD.vision_digest_enabled()} "
      f"vision_available={llm.vision_available()}")

print("\n── B2. trích ảnh bằng ffmpeg thật ──")
if not os.path.exists(SRC):
    print(f"  ✗ thiếu video {SRC}")
    sys.exit(1)
anh = []
t0 = time.time()
for k, t in enumerate((60.0, 300.0, 600.0)):
    fp = os.path.join(T, f"f{k}.jpg")
    ok = extract_frame(SRC, t, fp, width=480)
    sz = os.path.getsize(fp) if os.path.exists(fp) else 0
    print(f"  t={t:.0f}s -> extract_frame={ok} · {sz} byte")
    if ok and sz:
        anh.append(fp)
print(f"  trích {len(anh)}/3 ảnh trong {time.time()-t0:.1f}s")
if not anh:
    print("  ✗ CHẾT Ở BƯỚC TRÍCH ẢNH")
    sys.exit(1)

print("\n── B3. gọi vision THẬT (in nguyên lỗi) ──")
t0 = time.time()
try:
    data = llm.complete_vision_json(VD._VISION_PROMPT, anh)
    print(f"  ✓ {time.time()-t0:.1f}s · kiểu={type(data).__name__}")
    print(f"  nội dung: {str(data)[:600]}")
except Exception as e:  # noqa: BLE001
    print(f"  ✗ {time.time()-t0:.1f}s · {type(e).__name__}: {str(e)[:500]}")
    sys.exit(1)

print("\n── B4. _describe_batch (bóc dict/list) ──")
try:
    rows = VD._describe_batch(anh)
    print(f"  ra {len(rows)} dòng: {str(rows)[:400]}")
except Exception as e:  # noqa: BLE001
    print(f"  ✗ {type(e).__name__}: {str(e)[:400]}")

print(f"\n(sandbox {T})")
