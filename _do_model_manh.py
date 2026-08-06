# -*- coding: utf-8 -*-
"""ĐO: khâu CHỌN ĐOẠN có dùng được MODEL MẠNH không, hay chỉ là cái cớ 413.

Anh Hùng 06/08/2026: "k dùng model mạnh thông minh phân tích đc à rẻ quá sợ
phân tích ẩu mà đoạn k hay vẫn cho vào".
Trước đây tôi chỉ ghi "gpt-oss-120b -> 413" rồi bỏ. Lần này đo tử tế:
  1. prompt chọn đoạn THẬT dài bao nhiêu (video 1.000s của anh)
  2. từng model MẠNH còn sống trên Groq: có nhận nổi không, bao lâu, hạn mức
  3. nếu 413 thì THIẾU bao nhiêu -> cần thu prompt bao nhiêu %
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="momanh_")
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
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from config import settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.modules import m1_highlight as M  # noqa: E402

CACHE = Path(REPO, "_do_chon_cache")
VIDEO = [
    (r"C:\Users\Admin\Downloads\Video\16 year old girl defiant to her mom & says she doesn’t love her #prisondr #viral.mp4", 1062.0),
    (r"C:\Users\Admin\Downloads\Video\Big Body OG Pred Gets Busted!.mp4", 1117.0),
]
CFG = {"min_len": 60.0, "max_len": 90.0, "count": 3}


def _cac_ban_chep_loi():
    """Mọi bản chép lời có trong cache (bỏ file kết quả moc/moi)."""
    ra = []
    for f in sorted(CACHE.glob("*.json")):
        if f.stem in ("moc", "moi"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and (d.get("segments") or d.get("words")):
            segs = d.get("segments") or []
            dur = max([float(s.get("end", 0)) for s in segs] or [0]) + 30
            ra.append((f.name, d, dur))
    return ra


print(f"model đang dùng cho CHỌN ĐOẠN: {settings.GROQ_LLM_MODEL}")
print(f"số key: {len(settings.groq_keys())}\n")

# ── 1. prompt chọn đoạn THẬT dài bao nhiêu ──
print("=== 1. Prompt chọn đoạn THẬT ===")
prompts = []
for nhan, tr, dur in _cac_ban_chep_loi():
    # DỰNG ĐÚNG như đường thật: transcript được CHIA KHÚC rồi mỗi khúc 1 prompt
    khuc = M._chunk_transcript(tr.get("segments") or [])
    prs = [M._select_prompt(k, M._lang_name(tr.get("language", "")), "", "",
                            CFG["min_len"], CFG["max_len"], CFG["count"])
           for k in khuc]
    dai_nhat = max(prs, key=len)
    prompts.append((nhan, dai_nhat))
    print(f"  {nhan}: video ~{dur:.0f}s · {len(tr.get('segments') or [])} câu "
          f"-> {len(khuc)} khúc · prompt DÀI NHẤT {len(dai_nhat):,} ký tự "
          f"≈ {len(dai_nhat)//4:,} token")
prompts.sort(key=lambda x: -len(x[1]))      # lấy prompt DÀI NHẤT làm ca xấu
if not prompts:
    print("  ✗ không có cache -> chạy `python _do_chon_doan.py --moc` trước")
    sys.exit(1)

# ── 2. thử từng model MẠNH ──
print("\n=== 2. Model MẠNH có nhận nổi prompt đó không ===")
MODEL = [
    ("llama-3.3-70b-versatile", "đang dùng (nhanh, rẻ)"),
    ("openai/gpt-oss-120b", "MẠNH NHẤT trên Groq"),
    ("openai/gpt-oss-20b", "trung bình"),
    ("qwen/qwen3.6-27b", "suy luận + nhìn hình"),
]
nhan, pr = prompts[0]
print(f"  (dùng prompt của: {nhan} — {len(pr):,} ký tự)\n")
for md, ghi in MODEL:
    t0 = time.time()
    try:
        raw = llm.complete_text(pr, model=md)
        dt = time.time() - t0
        try:
            data = llm._extract_json(raw or "")
        except Exception:  # noqa: BLE001
            data = None
        n = len(data) if isinstance(data, list) else (
            len(data.get("clips", [])) if isinstance(data, dict) else 0)
        print(f"  ✅ {md:26s} {dt:5.1f}s · trả {len(raw or ''):,} ký tự · "
              f"đọc ra {n} clip   [{ghi}]")
    except Exception as ex:
        dt = time.time() - t0
        s = str(ex)
        rq = ""
        if "Requested" in s:
            import re
            m = re.search(r"Requested (\d+)", s)
            lim = re.search(r"Limit (\d+)", s)
            if m and lim:
                rq = (f" -> cần {int(m.group(1)):,} token nhưng hạn mức "
                      f"{int(lim.group(1)):,}/phút "
                      f"(phải thu nhỏ {100-int(lim.group(1))/int(m.group(1))*100:.0f}%)")
        print(f"  ❌ {md:26s} {dt:5.1f}s · {type(ex).__name__}: "
              f"{s[:100]}{rq}   [{ghi}]")
    time.sleep(3)

print(f"\n(sandbox {T})")
