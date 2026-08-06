# -*- coding: utf-8 -*-
"""SO CHẤT LƯỢNG CHỌN ĐOẠN: model rẻ (llama-3.3-70b) vs model MẠNH (gpt-oss-120b).

Anh Hùng 06/08/2026: "rẻ quá sợ phân tích ẩu mà đoạn k hay vẫn cho vào".
Đo CÔNG BẰNG: CÙNG video, CÙNG bản chép lời (cache), CÙNG cấu hình, chỉ đổi
MODEL CHỌN ĐOẠN. Rồi cho HỘI ĐỒNG TRỌNG TÀI (cùng 1 model chấm cho cả 2 bên,
chấm MÙ — không biết clip của model nào) cho điểm.

Kiểm cả 2 nỗi lo đã ghi trong config.py về gpt-oss:
  - 413 "Request too large"  -> đếm số lượt lỗi
  - "content trả RỖNG"       -> đếm số khúc AI không trả nổi clip nào
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="somodel_")
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
from app.ai import chon_doan as CD  # noqa: E402
from app.ai import llm  # noqa: E402
from app.modules import m1_highlight as M  # noqa: E402

CACHE = Path(REPO, "_do_chon_cache")
CFG = {"min_len": 60.0, "max_len": 90.0, "count": 3}
MODEL = [("", "llama-3.3-70b (RẺ, đang dùng)"),
         ("openai/gpt-oss-120b", "gpt-oss-120b (MẠNH)")]


def _ban_chep_loi():
    ra = []
    for f in sorted(CACHE.glob("*.json")):
        if f.stem in ("moc", "moi"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        segs = d.get("segments") or []
        if len(segs) > 40:
            ra.append((f.stem[:10], d,
                       max(float(s.get("end", 0)) for s in segs) + 30))
    return ra


def _cau(tr, a, b, n=76):
    for s in tr.get("segments") or []:
        if float(s.get("end", 0)) >= a and float(s.get("start", 0)) <= b:
            t = " ".join(str(s.get("text", "")).split())
            if len(t) > 8:
                return t[:n]
    return "(không thoại)"


VIDEO = _ban_chep_loi()
print(f"=== SO 2 MODEL trên {len(VIDEO)} video thật · cấu hình {CFG} ===")
print(f"    trọng tài chấm mù dùng CHUNG model {settings.GROQ_LLM_MODEL} "
      f"cho cả 2 bên (công bằng)\n")
KQ = {}
for md, ten in MODEL:
    os.environ["SELECT_MODEL"] = md
    settings.SELECT_MODEL = md               # đè trực tiếp (đã nạp settings)
    print(f"▶ {ten}")
    diem_tat, n_clip, t_tong, n_rong, n_413 = [], 0, 0.0, 0, 0
    for nhan, tr, dur in VIDEO:
        t0 = time.time()
        try:
            out = M._llm_select_clips(tr, dur, None, None, CFG)
            clips = out[0] if isinstance(out, tuple) else out
            warns = out[1] if isinstance(out, tuple) and len(out) > 1 else []
        except Exception as ex:                # noqa: BLE001
            print(f"    {nhan}: ✗ {type(ex).__name__}: {str(ex)[:90]}")
            continue
        dt = time.time() - t0
        t_tong += dt
        for w in warns or []:
            s = str(w).lower()
            n_413 += 1 if "413" in s or "too large" in s else 0
            n_rong += 1 if "rỗng" in s or "empty" in s else 0
        if not clips:
            n_rong += 1
        # HỘI ĐỒNG chấm MÙ (chỉ thấy đoạn thoại, không biết model nào chọn)
        cham = CD.cham_hoi_dong(clips, tr, llm.complete_text) if clips else {}
        ds = []
        for i, c in enumerate(clips or []):
            segs = c.get("segments") or []
            a = float(segs[0][0]) if segs else 0.0
            b = float(segs[-1][1]) if segs else 0.0
            d = float(cham.get(i, {}).get("score", 0))
            diem_tat.append(d)
            ds.append((a, b, d, len(segs)))
        n_clip += len(ds)
        print(f"    {nhan}: {len(ds)} clip · {dt:4.0f}s · điểm "
              f"{[f'{x[2]:.0f}' for x in ds]}")
        for a, b, d, ns in ds:
            print(f"        {a:7.1f}-{b:7.1f}s ({ns} đoạn) đ{d:3.0f} · "
                  f"{_cau(tr, a, b)}")
    tb = statistics.mean(diem_tat) if diem_tat else 0
    KQ[ten] = (tb, n_clip, t_tong, n_rong, n_413, diem_tat)
    print(f"    ── điểm TRUNG BÌNH {tb:.1f} · {n_clip} clip · "
          f"{t_tong:.0f}s · khúc trả rỗng {n_rong} · lỗi 413 {n_413}\n")

print("═══ KẾT LUẬN ═══")
for ten, (tb, n, t, r, e, ds) in KQ.items():
    print(f"  {ten:34s} điểm TB {tb:5.1f} · {n} clip · {t:4.0f}s · "
          f"rỗng {r} · 413 {e}")
if len(KQ) == 2:
    a, b = list(KQ.values())
    hieu = b[0] - a[0]
    print(f"\n  Model MẠNH hơn {hieu:+.1f} điểm "
          f"({'ĐÁNG đổi' if hieu >= 3 else 'KHÔNG đáng đổi'}), "
          f"chậm hơn {b[2]-a[2]:+.0f}s cho {len(VIDEO)} video")
print(f"\n(sandbox {T})")
