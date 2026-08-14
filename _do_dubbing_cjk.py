# -*- coding: utf-8 -*-
r"""ĐO 3 chỗ `.split()` của `app/core/dubbing.py` trên DỮ LIỆU THẬT.

    .venv\Scripts\python _do_dubbing_cjk.py

Chạy được trên CẢ bản TRƯỚC và SAU khi vá (không import gì mới) — dùng để in
số đo trước/sau. Nguồn số liệu THẬT, không bịa:
  · `_tq_work/trung_transcript.json` — Groq whisper THẬT trên video tiếng Trung
    của anh Hùng: nhãn ngôn ngữ **"Chinese"** (chữ, KHÔNG phải mã `zh`),
    99 câu · 1.230 ký tự · **1.074 mốc TỪNG TỪ** (1.020 từ dài đúng 1 ký tự).
  · `_do_hook_cache.json` — 16 video THẬT 4 nhóm tiếng (Nhật/Hàn/Anh/Việt).

Ba chỗ đo:
  A `_phrase_groups_by_speech` — chia cụm phụ đề rải vào các đoạn CÓ TIẾNG.
  B `_phrase_groups_even`      — chia đều theo SỐ TỪ.
  C `_align_stt_words`         — ghép mốc STT với chữ kịch bản; lệch số từ quá
    40% thì trả None = **âm thầm lùi về silencedetect** (nguy hiểm nhất).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_T = tempfile.mkdtemp(prefix="bq_dobg_")
os.environ.setdefault("BQ_DATA_DIR", os.path.join(_T, "data"))
os.environ.setdefault("BQ_DB_PATH", os.path.join(_T, "data", "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", os.path.join(_T, "settings.ini"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import dubbing as D  # noqa: E402

WORK = REPO / "_tq_work"
_tq = json.loads((WORK / "trung_transcript.json").read_text(encoding="utf-8"))
ZH_SEGS = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
           for s in _tq["segments"] if str(s.get("text") or "").strip()]
ZH_WORDS = [[float(w["start"]), float(w["end"]), str(w.get("word") or "")]
            for w in _tq["words"] if str(w.get("word") or "").strip()]
KHO4 = json.loads((REPO / "_do_hook_cache.json").read_text(encoding="utf-8"))


def parts(segs: list, dai: float = 10.0) -> list:
    """Gộp câu liền kề thành 'part' ~`dai` giây — đúng cỡ part narrate thật."""
    ra, cur = [], []
    for a, b, t in segs:
        if cur and b - cur[0][0] > dai:
            ra.append(cur)
            cur = []
        cur.append((a, b, t))
    if cur:
        ra.append(cur)
    return ra


def noi(cum: list) -> str:
    """Nối câu trong 1 part: CJK không dấu cách, còn lại 1 dấu cách."""
    from app.ai.recap import _has_cjk
    return ("" if _has_cjk(cum[0][2]) else " ").join(t for _a, _b, t in cum)


print("=" * 74)
print("ĐO 3 CHỖ `.split()` TRONG dubbing.py — dữ liệu THẬT")
print(f"nhãn ngôn ngữ Groq trả: {_tq.get('language')!r}  (chữ, không phải mã)")
print(f"lời Trung: {len(ZH_SEGS)} câu · {len(_tq['text'])} ký tự · "
      f"{len(ZH_WORDS)} mốc từng-từ")
print("=" * 74)

ZH_PARTS = parts(ZH_SEGS)
print(f"\ngộp thành {len(ZH_PARTS)} part ~10 giây (cỡ part narrate thật)")

# ─────────────────────────────────────────── A. _phrase_groups_by_speech
print("\n=== A. _phrase_groups_by_speech (rải cụm vào đoạn CÓ TIẾNG) ===")
_a_n, _a_min, _a_max = [], 99, 0
for p in ZH_PARTS:
    txt = noi(p)
    dur = p[-1][1] - p[0][0]
    # giả lập 3 đoạn có tiếng đều nhau trên file part (gốc 0)
    sp = [(0.0, dur / 3 - 0.05), (dur / 3, 2 * dur / 3 - 0.05),
          (2 * dur / 3, dur)]
    g = D._phrase_groups_by_speech(txt, 0.0, sp)
    _a_n.append(len(g))
    if g:
        _a_min = min(_a_min, min(len(str(x[2])) for x in g))
        _a_max = max(_a_max, max(len(str(x[2])) for x in g))
print(f"  số cụm/part (Trung): min {min(_a_n)} · max {max(_a_n)} · "
      f"tổng {sum(_a_n)} trên {len(ZH_PARTS)} part")
print(f"  ký tự/cụm: min {_a_min} · max {_a_max}")
print(f"  part ra ĐÚNG 1 CỤM: {sum(1 for n in _a_n if n == 1)}/{len(_a_n)}")
_dc = sum(1 for p in ZH_PARTS
          for x in D._phrase_groups_by_speech(noi(p), 0.0,
                                              [(0.0, 3.0), (3.1, 6.0)])
          if " " in str(x[2]))
print(f"  cụm bị CHÈN DẤU CÁCH giữa chữ Hán: {_dc}")

# ─────────────────────────────────────────── B. _phrase_groups_even
print("\n=== B. _phrase_groups_even (chia đều theo SỐ TỪ) ===")
_b_n = []
for p in ZH_PARTS:
    dur = p[-1][1] - p[0][0]
    g = D._phrase_groups_even(noi(p), 0.0, dur)
    _b_n.append(len(g))
print(f"  số cụm/part (Trung): min {min(_b_n)} · max {max(_b_n)} · "
      f"tổng {sum(_b_n)}")
print(f"  part ra ĐÚNG 1 CỤM: {sum(1 for n in _b_n if n == 1)}/{len(_b_n)}")
_p0 = ZH_PARTS[0]
_g0 = D._phrase_groups_even(noi(_p0), 0.0, _p0[-1][1] - _p0[0][0])
print(f"  part 1 ({_p0[-1][1] - _p0[0][0]:.2f}s): {len(_g0)} cụm · "
      f"cụm đầu dài {_g0[0][1] - _g0[0][0]:.2f}s")
_dcb = sum(1 for p in ZH_PARTS
           for x in D._phrase_groups_even(noi(p), 0.0, 9.0)
           if " " in str(x[2]))
print(f"  cụm bị CHÈN DẤU CÁCH giữa chữ Hán: {_dcb}")

# ─────────────────────────────────────────── C. _align_stt_words
print("\n=== C. _align_stt_words (mốc STT + chữ kịch bản) ===")
_c_ok, _c_none, _ty = 0, 0, []
for p in ZH_PARTS:
    a0, b0 = p[0][0], p[-1][1]
    w = [[x[0] - a0, x[1] - a0, x[2]] for x in ZH_WORDS if a0 <= x[0] < b0]
    if not w:
        continue
    r = D._align_stt_words(noi(p), w)
    if r:
        _c_ok += 1
    else:
        _c_none += 1
    # tỉ lệ lệch mà hàm dùng để quyết định
    m = len(str(noi(p)).split())
    _ty.append(abs(m - len(w)) / max(m, len(w)))
print(f"  ghép ĐƯỢC: {_c_ok}/{_c_ok + _c_none} part · "
      f"trả None (lùi silencedetect): {_c_none}")
print(f"  tỉ lệ lệch số từ theo .split(): min {min(_ty):.3f} · "
      f"max {max(_ty):.3f} (ngưỡng {D._STT_MISS_MAX})")
_full = D._align_stt_words(_tq["text"], ZH_WORDS)
print(f"  CẢ BÀI (1.230 ký tự vs {len(ZH_WORDS)} mốc STT): "
      f"{'ghép được ' + str(len(_full)) + ' từ' if _full else 'None'}")

# ─────────────────────────────────────────── D. BẤT BIẾN 4 thứ tiếng
print("\n=== D. BẤT BIẾN — 16 video thật 4 nhóm tiếng (chuỗi kết quả) ===")
print("  (băm THEO TỪNG NHÓM: nhóm chữ latin phải Y HỆT; nhóm `nhat` CỐ Ý đổi")
print("   vì tiếng Nhật cũng KHÔNG có dấu cách — trước đây cũng ra 1 cụm)")
import hashlib  # noqa: E402
from collections import defaultdict  # noqa: E402

_hh: dict = defaultdict(hashlib.sha256)
_nn: dict = defaultdict(int)
_cum: dict = defaultdict(int)
for v in KHO4:
    g = str(v.get("nhom") or "?")
    ss = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
          for s in v.get("segments") or [] if str(s.get("text") or "").strip()]
    if not ss:
        continue
    for p in parts(ss):
        txt = noi(p)
        dur = max(0.2, p[-1][1] - p[0][0])
        sp = [(0.0, dur / 3 - 0.05), (dur / 3, 2 * dur / 3 - 0.05),
              (2 * dur / 3, dur)]
        for r in (D._phrase_groups_by_speech(txt, 1.5, sp),
                  D._phrase_groups_even(txt, 1.5, dur)):
            _hh[g].update(repr(r).encode("utf-8"))
            _nn[g] += 1
            _cum[g] += len(r)
        w = [[i * 0.3, i * 0.3 + 0.28, t]
             for i, t in enumerate(str(txt).split())]
        _hh[g].update(repr(D._align_stt_words(txt, w)).encode("utf-8"))
        _nn[g] += 1
for g in sorted(_hh):
    print(f"  {g:5} {_nn[g]:4} phép gọi · {_cum[g]:5} cụm -> "
          f"sha256 {_hh[g].hexdigest()[:32]}")

# ─────────────────────────────────────────── E. TIẾNG HÀN (tự dựng)
print("\n=== E. TIẾNG HÀN — hangul CÓ dấu cách, phải đi đường .split() ===")
_KO = ("그런데 갑자기 눈보라가 몰아치기 시작했습니다",
       "결국 그는 아무 말도 하지 못하고 돌아섰어요",
       "이 사진 속에 숨겨진 비밀을 아무도 몰랐습니다")
_tach = getattr(D, "_tach_tu", None)      # bản MỐC chưa có -> đo bằng .split()
_noi = getattr(D, "_noi_tu", None)
for s in _KO:
    t = _tach(s) if _tach else s.split()
    r = _noi(t) if _noi else " ".join(t)
    print(f"  split {len(s.split())} · tách {len(t)} · nối lại đúng nguyên "
          f"văn: {r == s} · cỡ cụm "
          f"{D._co_cum(s, 4) if hasattr(D, '_co_cum') else 4}")
print("\nXONG.")
