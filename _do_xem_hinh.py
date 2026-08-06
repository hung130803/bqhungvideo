# -*- coding: utf-8 -*-
"""ĐO CHI PHÍ 'AI XEM HÌNH' (vision digest) trên VIDEO THẬT — trước khi bật."""
import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="xemhinh_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
os.environ["VISION_CUT"] = "1"          # bật xem hình bằng công tắc riêng
# key Groq nằm ở <DATA_DIR>/.env mà sandbox trỏ sang temp -> 0 key -> vision
# tưởng "không nhìn được" (đúng bẫy đã gặp ở cổng e2e). Chuyền key qua ENV.
from pathlib import Path as _P
_e = _P(os.environ.get("LOCALAPPDATA") or "") / "BQHungVideo" / ".env"
if _e.exists():
    for _ln in _e.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        if _k.strip() in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v.strip():
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
REPO = r"D:\claude\ai-content-studio"
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from config import settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.core import vision_digest as VD  # noqa: E402
from app.database.db import db  # noqa: E402

VIDEO = [
    (r"C:\Users\Admin\Downloads\Video\Big Body OG Pred Gets Busted!.mp4", 1117.0),
    (r"C:\Users\Admin\Downloads\Video\5 Ways to Cook a Cactus.mp4", 466.0),
]
print(f"VISION_CUT={settings.VISION_CUT} · model={settings.GROQ_VISION_MODEL}")
print(f"bật xem hình? {VD.vision_digest_enabled()} · AI nhìn được? "
      f"{llm.vision_available()}\n")
for p, dur in VIDEO:
    if not os.path.exists(p):
        print(f"  ✗ thiếu {os.path.basename(p)}")
        continue
    pid = db.execute("INSERT INTO projects(name,assets_dir,grp) VALUES(?,?,'M')",
                     (os.path.basename(p)[:20], T)).lastrowid
    vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                     "VALUES(?,?,?)", (pid, p, dur)).lastrowid
    moc = VD.pick_frame_times(dur, None)
    print(f"▶ {os.path.basename(p)[:44]} ({dur:.0f}s)")
    print(f"    sẽ trích {len(moc)} khung hình")
    t0 = time.time()
    try:
        dg = VD.build_vision_digest(vid, p, dur, ctx=None)
    except Exception as e:  # noqa: BLE001
        print(f"    ✗ LỖI: {type(e).__name__} {str(e)[:140]}")
        continue
    dt = time.time() - t0
    print(f"    xong {dt:.0f}s · digest {len(dg or [])} mốc")
    for d in (dg or [])[:4]:
        print(f"      {float(d.get('t', 0)):6.0f}s  act={d.get('act')}  "
              f"{str(d.get('desc'))[:76]}")
print(f"\n(sandbox: {T})")
