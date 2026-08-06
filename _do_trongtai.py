# -*- coding: utf-8 -*-
"""ĐO KHÂU CHẤM ĐIỂM: model thường vs model SUY LUẬN (mức 2 của lộ trình).

Cách đo phải công bằng và phải BẮT ĐƯỢC LỖI, nên dùng bộ clip có THỨ TỰ HAY/DỞ
BIẾT TRƯỚC (do người dựng), rồi xem trọng tài có xếp đúng thứ tự đó không:
  A = cao trào thật (xung đột, câu chốt)   -> phải điểm CAO nhất
  B = nói bình thường                       -> giữa
  C = intro chào kênh + kêu đăng ký         -> phải điểm THẤP nhất
Chấm 3 lượt mỗi model để xem có ỔN ĐỊNH (lệch ít) — trọng tài lúc cao lúc thấp
thì sàn lọc rác thành xổ số.
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="tt_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
from pathlib import Path  # noqa: E402

_e = Path(os.environ.get("LOCALAPPDATA") or "") / "BQHungVideo" / ".env"
if _e.exists():
    for _ln in _e.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        if _k.strip() in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v.strip():
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _test_guard  # noqa: E402,F401

from config import settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.ai import chon_doan as CD  # noqa: E402

CAU = [
    # C — intro rác (0-40s)
    (0.0, 8.0, "Hey guys welcome back to my channel, hope you are doing well."),
    (8.0, 18.0, "Before we start please hit that subscribe button and the bell."),
    (18.0, 30.0, "Also check the link in my bio for the merch, alright?"),
    (30.0, 40.0, "So today we are going to do something a little different."),
    # B — nói bình thường (100-140s)
    (100.0, 112.0, "So I pulled up to the address around four in the afternoon."),
    (112.0, 126.0, "The building was pretty quiet, nothing looked out of place."),
    (126.0, 140.0, "I waited in the car for a few minutes and then went inside."),
    # A — cao trào (300-340s)
    (300.0, 310.0, "You lied to my face! I heard the whole thing on the phone!"),
    (310.0, 322.0, "Don't you dare walk away from me right now, we are not done!"),
    (322.0, 334.0, "Fine. Then I'm telling everyone exactly what you did."),
    (334.0, 340.0, "And that was the moment everything fell apart."),
]
TR = {"language": "en",
      "segments": [{"start": a, "end": b, "text": t} for a, b, t in CAU],
      "words": []}
CLIP = [
    {"title": "Cao trào: bị bóc mẽ, cãi nhau",
     "segments": [[300.0, 340.0]], "score": 90},
    {"title": "Kể lại chuyện đi tới địa chỉ",
     "segments": [[100.0, 140.0]], "score": 90},
    {"title": "Chào kênh + kêu đăng ký",
     "segments": [[0.0, 40.0]], "score": 90},
]
TEN = ["A cao trào", "B bình thường", "C intro rác"]
MODEL = [("(mặc định) " + settings.GROQ_LLM_MODEL, ""),
         ("qwen/qwen3.6-27b (SUY LUẬN)", "qwen/qwen3.6-27b")]
N_LUOT = 3

print(f"=== ĐO TRỌNG TÀI · {len(CLIP)} clip biết trước thứ tự · "
      f"{N_LUOT} lượt/model · {len(settings.groq_keys())} key")
for ten_m, md in MODEL:
    print(f"\n▶ {ten_m}")
    diem = {i: [] for i in range(len(CLIP))}
    dung = 0
    tong_t = 0.0
    for lan in range(N_LUOT):
        t0 = time.time()
        try:
            ra = CD.cham_mu(CLIP, TR, llm.complete_text, model=md)
        except Exception as e:  # noqa: BLE001
            print(f"   lượt {lan+1}: LỖI {type(e).__name__}: {str(e)[:150]}")
            continue
        dt = time.time() - t0
        tong_t += dt
        if not ra:
            print(f"   lượt {lan+1}: {dt:.1f}s — KHÔNG chấm được (parse hỏng?)")
            continue
        ds = [float(ra.get(i, {}).get("score", -1)) for i in range(len(CLIP))]
        for i, s in enumerate(ds):
            if s >= 0:
                diem[i].append(s)
        thu_tu_dung = ds[0] > ds[1] > ds[2]
        dung += 1 if thu_tu_dung else 0
        print(f"   lượt {lan+1}: {dt:.1f}s · điểm "
              f"{[f'{x:.0f}' for x in ds]} · xếp đúng thứ tự: "
              f"{'CÓ' if thu_tu_dung else 'KHÔNG'}")
    print(f"   ── xếp đúng {dung}/{N_LUOT} lượt · trung bình {tong_t/max(1,N_LUOT):.1f}s/lượt")
    for i in range(len(CLIP)):
        v = diem[i]
        if len(v) >= 2:
            print(f"      {TEN[i]:16s} điểm {v} · lệch "
                  f"{statistics.pstdev(v):.1f}")
        elif v:
            print(f"      {TEN[i]:16s} điểm {v}")
print(f"\n(sandbox {T})")
