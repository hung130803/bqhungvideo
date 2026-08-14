# -*- coding: utf-8 -*-
r"""CỔNG 54 — **3 CHỖ `.split()` CỦA `dubbing.py` LÀM HỎNG CJK** (14/08/2026).

    .venv\Scripts\python _test_dubbing_cjk.py

Cổng 52 (`_test_cjk_va.py`) chốt 3 lỗ tiếng Trung ở `lop_phu`/`recap`/
`hook_to_mo` và **ghi thẳng phần nó KHÔNG được phép đụng**: `dubbing.py` dòng
1977 · 2199 · 2312 có ĐÚNG cùng bệnh. Cổng này chốt 3 chỗ đó.

  1977 `_phrase_groups_by_speech` — chia cụm phụ đề rồi rải vào đoạn CÓ TIẾNG.
  2199 `_phrase_groups_even`      — chia đều theo SỐ TỪ.
  2312 `_align_stt_words`         — ghép mốc STT với chữ kịch bản. **NGUY HIỂM
       NHẤT**: lệch số từ > 40% thì trả None và app **âm thầm lùi về
       silencedetect** — tính năng khớp-từng-từ (đã tốn lượt Groq chép lời!)
       không bao giờ chạy với tiếng Trung, không một dòng báo.
  Kèm `_phrase_groups_from_words` — NỐI CHUỖI của chính kết quả 2312; không
  chữa thì phụ đề tiếng Trung ra '他 们 发 现'.

=== NGUỒN SỐ LIỆU: THẬT HẾT, KHÔNG BỊA ===
  · `_tq_work/trung_transcript.json` — Groq whisper THẬT trên video tiếng
    Trung của anh Hùng: nhãn `"Chinese"` (CHỮ, không phải mã `zh`), 99 câu ·
    1.230 ký tự · **1.074 mốc TỪNG TỪ** (1.020 mốc dài đúng 1 ký tự — whisper
    chấm tiếng Trung theo KÝ TỰ). Đây là cặp (kịch bản, mốc STT) THẬT, đúng
    thứ `_align_stt_words` nhận ở đời thật.
  · `_do_hook_cache.json` — 16 video THẬT 4 nhóm tiếng. Corpus BẤT BIẾN.
  · Câu tiếng HÀN/THÁI tự dựng — CHỈ dùng cho phép so BẤT BIẾN (mốc vs nay),
    không rút kết luận chất lượng (máy anh Hùng không còn video tiếng Hàn).

=== CHỐNG PASS OAN (bài học cổng 36/41/47/51/52) ===
  · so với **BẢN MỐC** `git show 841c773:...` (bản anh Hùng ĐANG CHẠY), kèm
    chốt "mốc phải KHÁC bản đang test" + phân biệt 2 nguyên nhân khi TRÙNG.
  · mỗi việc có ca **TỰ KIỂM BỘ DÒ**: bắt bản MỐC phải TRƯỢT đúng phép đo mà
    bản mới ĐẠT.
  · quét tĩnh `.split()` bằng `ast` (KHÔNG dùng `in` chuỗi — chính dòng ghi
    chú "CẤM .split()" sẽ bị kể là vi phạm, đỏ oan y hệt cổng 47/51/53).
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
T = tempfile.mkdtemp(prefix="bq_dbcjk_")
os.environ["BQ_DATA_DIR"] = os.path.join(T, "data")
os.environ["BQ_DB_PATH"] = os.path.join(T, "data", "studio.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"
import _test_guard  # noqa: E402,F401 - CẤM cổng đụng máy anh Hùng

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

#: Mốc đối chứng = bản anh Hùng ĐANG CHẠY (v2.24.0). `dubbing.py` không đổi
#: một byte nào từ mốc đó tới ngay trước bản vá này.
MOC = os.environ.get("BQ_MOC_DUB", "841c773")

_OK: list = []
_FAIL: list = []


def ok(dieu_kien, ten: str, chi_tiet: str = "") -> bool:
    (_OK if dieu_kien else _FAIL).append(ten)
    print(f"  [{'OK  ' if dieu_kien else 'FAIL'}] {ten}"
          + (f"   — {chi_tiet}" if chi_tiet else ""))
    return bool(dieu_kien)


def _git(*a) -> str:
    return subprocess.run(("git",) + a, cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8",
                          errors="replace").stdout


def _la_to_tien(sha: str) -> bool:
    """HEAD có phải TỔ TIÊN của `sha` không (bài học cổng 36)."""
    return subprocess.run(("git", "merge-base", "--is-ancestor", "HEAD", sha),
                          cwd=str(REPO), capture_output=True).returncode == 0


def _nap_moc(duong: str, ten: str):
    """Nạp bản MỐC của một file mã nguồn thành module RIÊNG."""
    src = _git("show", f"{MOC}:{duong}")
    if len(src) < 500:
        return None, False
    cur = (REPO / duong).read_text(encoding="utf-8")
    khac = src.replace("\r\n", "\n") != cur.replace("\r\n", "\n")
    p = os.path.join(T, ten + ".py")
    Path(p).write_text(src, encoding="utf-8")
    sp = importlib.util.spec_from_file_location(ten, p)
    m = importlib.util.module_from_spec(sp)
    sys.modules[ten] = m          # @dataclass tra sys.modules -> phải có TRƯỚC
    sp.loader.exec_module(m)
    return m, khac


def _chot_moc(khac: bool, nhan: str) -> bool:
    """Chốt chống 'so nó với chính nó'. Trả True = ĐƯỢC đo bất biến."""
    if khac:
        ok(True, f"{nhan} bản mốc {MOC} KHÁC bản đang test (đo được bất biến)")
        return True
    if _la_to_tien(MOC):
        ok(False, f"{nhan} bản mốc TRÙNG bản đang test VÀ HEAD là tổ tiên của "
                  f"{MOC} -> mốc đã chứa chính bản vá, phép đo VÔ NGHĨA")
        return False
    ok(True, f"{nhan} bản mốc TRÙNG nhưng HEAD KHÔNG phải tổ tiên -> nhánh này "
             "không đụng file đó, bất biến ĐÚNG DO XÂY DỰNG")
    return False


# ====================================================================== CORPUS
_tq = json.loads((WORK / "trung_transcript.json").read_text(encoding="utf-8"))
ZH_SEGS = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
           for s in _tq["segments"] if str(s.get("text") or "").strip()]
ZH_WORDS = [[float(w["start"]), float(w["end"]), str(w.get("word") or "")]
            for w in _tq["words"] if str(w.get("word") or "").strip()]
KHO4 = json.loads((REPO / "_do_hook_cache.json").read_text(encoding="utf-8"))
#: Hàn/Thái TỰ DỰNG — chỉ dùng cho phép so BẤT BIẾN (xem docstring).
KO = ("그런데 갑자기 눈보라가 몰아치기 시작했습니다",
      "결국 그는 아무 말도 하지 못하고 돌아섰어요",
      "이 사진 속에 숨겨진 비밀을 아무도 몰랐습니다")
JA = ("ところがその瞬間、誰も予想しなかったことが起きました",
      "実は彼はずっと前から気づいていたのです")


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


def noi_cau(cum: list) -> str:
    """Nối câu trong 1 part: CJK không dấu cách, còn lại 1 dấu cách."""
    from app.ai.recap import _has_cjk
    return ("" if _has_cjk(cum[0][2]) else " ").join(t for _a, _b, t in cum)


print("=" * 74)
print(f"CỔNG 54 — 3 chỗ `.split()` của dubbing.py · mốc đối chứng {MOC}")
print(f"corpus: lời Trung {len(ZH_SEGS)} câu / {len(ZH_WORDS)} mốc từng-từ · "
      f"bất biến {len(KHO4)} video {sorted({v.get('nhom') for v in KHO4})}")
print("=" * 74)

from app.core import dubbing as D          # noqa: E402
from app.core import lop_phu as LP         # noqa: E402

D_MOC, _d_khac = _nap_moc("app/core/dubbing.py", "dub_moc")
ZH_PARTS = parts(ZH_SEGS)


def _sp3(dur: float) -> list:
    """3 đoạn CÓ TIẾNG đều nhau trên file part (gốc 0) — đầu vào của 1977."""
    return [(0.0, dur / 3 - 0.05), (dur / 3, 2 * dur / 3 - 0.05),
            (2 * dur / 3, dur)]


# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 0. CHỐT MỐC ===")
_do_duoc = False
if D_MOC is None:
    ok(False, f"0a nạp được bản mốc {MOC}:app/core/dubbing.py")
else:
    ok(True, f"0a nạp được bản mốc {MOC}:app/core/dubbing.py")
    _do_duoc = _chot_moc(_d_khac, "0b")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 1. HIỆU QUẢ — lời Trung THẬT, 3 chỗ ===")
_n1_moc = [len(D_MOC._phrase_groups_by_speech(
    noi_cau(p), 0.0, _sp3(p[-1][1] - p[0][0]))) for p in ZH_PARTS] \
    if D_MOC else []
_n1 = [len(D._phrase_groups_by_speech(
    noi_cau(p), 0.0, _sp3(p[-1][1] - p[0][0]))) for p in ZH_PARTS]
ok(all(n >= 2 for n in _n1),
   f"1a `_phrase_groups_by_speech`: KHÔNG part nào còn ra 1 CỤM DUY NHẤT "
   f"({sum(1 for n in _n1 if n == 1)}/{len(_n1)} part)",
   f"mốc {sum(1 for n in _n1_moc if n == 1)}/{len(_n1_moc)} part ra 1 cụm · "
   f"tổng cụm {sum(_n1_moc)} -> {sum(_n1)}")
ok(_n1_moc and all(n == 1 for n in _n1_moc),
   "1b TỰ KIỂM BỘ DÒ: bản MỐC ra ĐÚNG 1 cụm ở MỌI part (nếu mốc cũng chia "
   "được thì 1a chỉ là con dấu)",
   f"{sum(1 for n in _n1_moc if n == 1)}/{len(_n1_moc)}")

_n2_moc = [len(D_MOC._phrase_groups_even(noi_cau(p), 0.0,
                                         p[-1][1] - p[0][0]))
           for p in ZH_PARTS] if D_MOC else []
_n2 = [len(D._phrase_groups_even(noi_cau(p), 0.0, p[-1][1] - p[0][0]))
       for p in ZH_PARTS]
ok(all(n >= 2 for n in _n2),
   "1c `_phrase_groups_even`: KHÔNG part nào còn ra 1 CỤM DUY NHẤT",
   f"tổng cụm {sum(_n2_moc)} -> {sum(_n2)}")
ok(_n2_moc and all(n == 1 for n in _n2_moc),
   "1d TỰ KIỂM BỘ DÒ: bản MỐC ra ĐÚNG 1 cụm ở MỌI part")

#: dài nhất của MỘT cụm — trước đây cả part thành 1 dòng phụ đề
_max_ky = max(len(str(x[2]))
              for p in ZH_PARTS
              for x in D._phrase_groups_even(noi_cau(p), 0.0,
                                             p[-1][1] - p[0][0]))
_max_ky_moc = max(len(str(x[2]))
                  for p in ZH_PARTS
                  for x in D_MOC._phrase_groups_even(
                      noi_cau(p), 0.0, p[-1][1] - p[0][0])) if D_MOC else -1
ok(_max_ky <= D._RECAP_PHRASE_MAX_CJK,
   f"1e cụm dài nhất {_max_ky} ký tự (trần {D._RECAP_PHRASE_MAX_CJK} = "
   f"`captions._CJK_MAX['word']`, đo ở 1080x1920 vừa MỘT dòng)",
   f"mốc {_max_ky_moc} ký tự/cụm")

# ---- 2312: chỗ NGUY HIỂM NHẤT (fallback im lặng) ----
_c_ok, _c_none, _c_ok_moc = 0, 0, 0
for p in ZH_PARTS:
    a0, b0 = p[0][0], p[-1][1]
    w = [[x[0] - a0, x[1] - a0, x[2]] for x in ZH_WORDS if a0 <= x[0] < b0]
    if not w:
        continue
    if D._align_stt_words(noi_cau(p), w):
        _c_ok += 1
    else:
        _c_none += 1
    if D_MOC and D_MOC._align_stt_words(noi_cau(p), w):
        _c_ok_moc += 1
ok(_c_none == 0,
   f"1f `_align_stt_words` ghép được {_c_ok}/{_c_ok + _c_none} part — KHÔNG "
   f"còn part nào trả None (= không còn âm thầm lùi silencedetect)",
   f"mốc ghép được {_c_ok_moc}/{_c_ok + _c_none}")
ok(_c_ok_moc == 0,
   "1g TỰ KIỂM BỘ DÒ: bản MỐC trả None ở MỌI part (nếu mốc cũng ghép được "
   "thì 1f chỉ là con dấu)", f"mốc ghép được {_c_ok_moc}")
_full = D._align_stt_words(_tq["text"], ZH_WORDS)
_full_moc = D_MOC._align_stt_words(_tq["text"], ZH_WORDS) if D_MOC else None
ok(bool(_full) and abs(len(_full) - len(ZH_WORDS)) / len(_full) <= 0.40,
   f"1h CẢ BÀI: {len(_tq['text'])} ký tự kịch bản vs {len(ZH_WORDS)} mốc STT "
   f"-> ghép được {len(_full) if _full else 0} từ",
   f"mốc: {'None' if not _full_moc else len(_full_moc)}")
ok(all(_full[i][0] <= _full[i + 1][0] for i in range(len(_full) - 1)),
   "1i mốc trả về KHÔNG GIẢM (bất biến của hàm, không được vỡ khi đổi tách từ)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 2. BẤT BIẾN — chữ LATIN (Anh · Việt · nhóm `han`) ===")
if not _do_duoc:
    ok(False, "2a không đo được bất biến (thiếu mốc)")
else:
    _lech: list = []
    _n, _cum_moc, _cum_nay = 0, 0, 0
    _nhom_do: set = set()
    for v in KHO4:
        g = str(v.get("nhom") or "?")
        if g == "nhat":
            continue                       # CỐ Ý đổi — đo riêng ở CA 4
        ss = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
              for s in v.get("segments") or []
              if str(s.get("text") or "").strip()]
        if not ss:
            continue
        _nhom_do.add(g)
        for p in parts(ss):
            txt = noi_cau(p)
            dur = max(0.2, p[-1][1] - p[0][0])
            a = D_MOC._phrase_groups_by_speech(txt, 1.5, _sp3(dur))
            b = D._phrase_groups_by_speech(txt, 1.5, _sp3(dur))
            _n += 1
            _cum_moc += len(a)
            _cum_nay += len(b)
            if a != b:
                _lech.append((g, "_phrase_groups_by_speech", txt[:26]))
            a = D_MOC._phrase_groups_even(txt, 1.5, dur)
            b = D._phrase_groups_even(txt, 1.5, dur)
            _n += 1
            _cum_moc += len(a)
            _cum_nay += len(b)
            if a != b:
                _lech.append((g, "_phrase_groups_even", txt[:26]))
            w = [[i * 0.3, i * 0.3 + 0.28, t]
                 for i, t in enumerate(str(txt).split())]
            _n += 1
            if D_MOC._align_stt_words(txt, w) != D._align_stt_words(txt, w):
                _lech.append((g, "_align_stt_words", txt[:26]))
            _n += 1
            if D_MOC._phrase_groups_from_words(w, 1.5) \
                    != D._phrase_groups_from_words(w, 1.5):
                _lech.append((g, "_phrase_groups_from_words", txt[:26]))
    ok(not _lech,
       f"2a {_n} phép gọi trên {len(KHO4) - 4} video chữ latin "
       f"{sorted(_nhom_do)}: CHUỖI KẾT QUẢ giống mốc {MOC} 100%",
       f"lệch {len(_lech)}: {_lech[:3]}")
    ok(_cum_moc == _cum_nay,
       f"2b tổng số cụm KHÔNG đổi một cái nào ({_cum_moc} -> {_cum_nay})")
    # TỰ KIỂM: đúng bộ so đó PHẢI bắt được khác biệt khi đưa lời TRUNG vào
    _txt_zh = noi_cau(ZH_PARTS[0])
    ok(D_MOC._phrase_groups_even(_txt_zh, 1.5, 8.0)
       != D._phrase_groups_even(_txt_zh, 1.5, 8.0),
       "2c TỰ KIỂM BỘ DÒ: đúng phép so đó, lời TRUNG cho kết quả KHÁC mốc "
       "(bằng nhau thì 2a chỉ là con dấu)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 3. TIẾNG HÀN — hangul CÓ dấu cách, KHÔNG được hồi quy ===")
# `recap._CJK_CHARS` GỒM hangul (ở recap chỉ ĐẾM token nên vô hại). Ở đây còn
# NỐI LẠI ĐỂ HIỂN THỊ + SO SỐ TỪ với mốc STT -> lấy nguyên bộ đó là làm HỎNG
# tiếng Hàn đang chạy tốt. Đây là ca canh cho lần sau đừng "dọn dẹp" gộp lại.
from app.ai.recap import _word_tokens as _RW    # noqa: E402

ok(all(len(D._tach_tu(s)) == len(s.split()) for s in KO),
   "3a `_tach_tu` câu Hàn ra ĐÚNG số từ của `.split()` (không tách âm tiết)",
   " · ".join(f"{len(s.split())}/{len(D._tach_tu(s))}" for s in KO))
ok(all(len(_RW(s)) > len(s.split()) * 2 for s in KO),
   "3b TỰ KIỂM BỘ DÒ: `recap._word_tokens` (bộ CÓ hangul) tách câu đó ra GẤP "
   "BỘI số từ — tức nếu dùng thẳng nó thì 3a đã hỏng",
   " · ".join(f"{len(s.split())}->{len(_RW(s))}" for s in KO))
ok(all(D._noi_tu(D._tach_tu(s)) == s for s in KO),
   "3c nối lại ra ĐÚNG NGUYÊN VĂN câu Hàn (còn đủ dấu cách)")
from app.core.captions import _noi_cum as _NC   # noqa: E402

ok(all(_NC(s.split()) != s for s in KO),
   "3d TỰ KIỂM BỘ DÒ: `captions._noi_cum` (coi hangul là CJK) NUỐT dấu cách "
   "kể cả khi đưa vào đúng `.split()` — nên `_noi_tu` phải viết riêng",
   repr(_NC(KO[0].split()))[:52])
if _do_duoc:
    _l3 = []
    for s in KO:
        w = [[i * 0.3, i * 0.3 + 0.28, t] for i, t in enumerate(s.split())]
        for f, a in (("_phrase_groups_even", (s, 1.0, 6.0)),
                     ("_phrase_groups_by_speech", (s, 1.0, _sp3(6.0))),
                     ("_phrase_groups_from_words", (w, 1.0)),
                     ("_align_stt_words", (s, w))):
            if getattr(D_MOC, f)(*a) != getattr(D, f)(*a):
                _l3.append((f, s[:18]))
    ok(not _l3, "3e cả 4 hàm trên câu Hàn ra Y HỆT bản mốc", f"lệch {_l3}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 4. TIẾNG NHẬT — CỐ Ý đổi, và phải đổi cho ĐÚNG ===")
_ja_moc, _ja_nay = 0, 0
for v in KHO4:
    if str(v.get("nhom")) != "nhat":
        continue
    ss = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
          for s in v.get("segments") or [] if str(s.get("text") or "").strip()]
    for p in parts(ss):
        dur = max(0.2, p[-1][1] - p[0][0])
        _ja_nay += len(D._phrase_groups_even(noi_cau(p), 1.5, dur))
        if D_MOC:
            _ja_moc += len(D_MOC._phrase_groups_even(noi_cau(p), 1.5, dur))
ok(_ja_nay > _ja_moc * 3,
   f"4a 4 video NHẬT thật: số cụm {_ja_moc} -> {_ja_nay} (tiếng Nhật cũng "
   "KHÔNG có dấu cách nên trước đây cũng ra ~1 cụm/part — sửa luôn, có chủ ý)")
ok(all(D._noi_tu(D._tach_tu(s)) == s for s in JA),
   "4b câu Nhật nối lại ĐÚNG NGUYÊN VĂN — kể cả dấu câu CJK `、`(U+3001) "
   "không bị chèn dấu cách hai bên")
_ja_cum = [x[2] for s in JA for x in D._phrase_groups_even(s, 0.0, 8.0)]
ok(all(" " not in c for c in _ja_cum),
   f"4c KHÔNG cụm Nhật nào bị chèn dấu cách ({len(_ja_cum)} cụm)",
   " | ".join(_ja_cum[:4]))

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 5. QUÉT TĨNH `.split()` (ast, bỏ hằng chuỗi) ===")
_src = (REPO / "app" / "core" / "dubbing.py").read_text(encoding="utf-8")
_bien, _hang = [], []
for _nd in ast.walk(ast.parse(_src)):
    if (isinstance(_nd, ast.Call) and isinstance(_nd.func, ast.Attribute)
            and _nd.func.attr == "split" and not _nd.args):
        (_hang if isinstance(_nd.func.value, ast.Constant) else _bien) \
            .append(_nd.lineno)
ok(len(_bien) == 1,
   "5a chỉ còn ĐÚNG 1 chỗ `.split()` KHÔNG THAM SỐ trên BIẾN — nằm trong "
   "chính `_tach_tu` (đường tách cụm-trắng, bất biến non-CJK)",
   f"dòng {_bien}")
if _bien:
    _fn = [n.name for n in ast.walk(ast.parse(_src))
           if isinstance(n, ast.FunctionDef)
           and n.lineno <= _bien[0] <= (n.end_lineno or n.lineno)]
    ok(_fn == ["_tach_tu"],
       "5b chỗ đó đúng là `_tach_tu`, không phải chỗ khác lọt lưới", str(_fn))
_moc_bien = [n.lineno for n in ast.walk(ast.parse(_git(
    "show", f"{MOC}:app/core/dubbing.py")))
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    and n.func.attr == "split" and not n.args]
ok(len(_moc_bien) == 3,
   "5c TỰ KIỂM BỘ DÒ: bản MỐC có ĐÚNG 3 chỗ (1977 · 2199 · 2312) — đúng 3 "
   "chỗ cổng 52 bàn giao lại", f"dòng {_moc_bien}")
# `.split(" ")` cũng ĐẾM TỪ y hệt `.split()` — rà cả dạng CÓ tham số, đừng chỉ
# rà dạng không tham số (chỗ còn lại đều tách mã locale/voice id: '-' ':' ',').
_tach_trang, _tach_khac = [], []
for _nd in ast.walk(ast.parse(_src)):
    if (isinstance(_nd, ast.Call) and isinstance(_nd.func, ast.Attribute)
            and _nd.func.attr in ("split", "rsplit") and _nd.args
            and isinstance(_nd.args[0], ast.Constant)):
        (_tach_trang if not str(_nd.args[0].value or "x").strip()
         else _tach_khac).append((_nd.lineno, _nd.args[0].value))
ok(not _tach_trang,
   f"5d KHÔNG chỗ nào tách bằng DẤU CÁCH (`.split(' ')` đếm từ y hệt "
   f"`.split()`); {len(_tach_khac)} chỗ tách bằng dấu KHÁC là tách mã "
   f"locale/voice id, không đếm từ",
   f"{sorted({d for _l, d in _tach_khac})}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 6. BẪY NHÃN NGÔN NGỮ (`Chinese` vs `zh`) ===")
ok(str(_tq.get("language")) == "Chinese",
   "6a corpus THẬT xác nhận Groq trả nhãn CHỮ `Chinese`, không phải mã `zh`",
   repr(_tq.get("language")))
ok(LP.chuan_ngon_ngu("Chinese") == "zh" and LP.chuan_ngon_ngu("zh") == "zh",
   "6b `lop_phu.chuan_ngon_ngu` (cổng 52 đã làm) vẫn nhận CẢ HAI dạng — "
   "DÙNG LẠI hàm đó, không viết lại")
_zh_src = ast.parse(_src)
_doc_nhan = [n.lineno for n in ast.walk(_zh_src)
             if isinstance(n, ast.Call) and (
                 (isinstance(n.func, ast.Name)
                  and n.func.id == "chuan_ngon_ngu")
                 or (isinstance(n.func, ast.Attribute)
                     and n.func.attr == "chuan_ngon_ngu"))]
ok(not _doc_nhan,
   "6c bản vá KHÔNG đọc nhãn ngôn ngữ MỘT LẦN NÀO — nó dò trên CHÍNH CHỮ "
   "(regex ký tự), nên cái bẫy `Chinese`/`zh` không với tới được đường này. "
   "Đây là chỗ TỐT HƠN: nhãn Groq trả sai (corpus có video Hàn bị gán "
   "`Norwegian Nynorsk`) cũng không làm bản vá tịt")
# chốt THẬT: đổi nhãn ngôn ngữ KHÔNG được đổi kết quả
_p = ZH_PARTS[0]
_a0, _b0 = _p[0][0], _p[-1][1]
_w = [[x[0] - _a0, x[1] - _a0, x[2]] for x in ZH_WORDS if _a0 <= x[0] < _b0]
_ra = {lang: (D._phrase_groups_even(noi_cau(_p), 0.0, _b0 - _a0),
              D._align_stt_words(noi_cau(_p), _w))
       for lang in ("Chinese", "zh", "zh-CN", "", "Norwegian Nynorsk")}
ok(len({repr(v) for v in _ra.values()}) == 1,
   "6d đổi nhãn ngôn ngữ qua 5 dạng (`Chinese`/`zh`/`zh-CN`/rỗng/nhãn SAI) "
   "-> kết quả Y HỆT nhau", f"{len(_ra['Chinese'][0])} cụm ở mọi nhãn")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 7. NỐI CHUỖI — không mất chữ, không thêm dấu cách ===")
_CA = [("Hàn", KO[0]), ("Trung", ZH_SEGS[0][2]),
       ("Trung+dấu", "这不是在夸张，不信你往下看。"), ("Nhật", JA[0]),
       ("Anh", "the man simply dropped his watch while diving"),
       ("Anh+dấu", "hello , world . ok"),
       ("Việt", "anh ta chỉ vô tình làm rơi chiếc đồng hồ"),
       ("Trộn", "他说 OK 了"), ("Thái", "สวัสดีครับทุกคน")]
_rt = [(n, D._noi_tu(D._tach_tu(s)) == s) for n, s in _CA]
ok(all(r for _n, r in _rt),
   f"7a tách rồi nối lại ra ĐÚNG NGUYÊN VĂN {sum(r for _n, r in _rt)}/"
   f"{len(_rt)} ca (9 hệ chữ)",
   " · ".join(n for n, r in _rt if not r) or "không ca nào lệch")
ok(all(D._noi_tu(s.split()) == " ".join(s.split())
       for n, s in _CA if not D._KHONG_DAU_CACH.search(s)),
   "7b BẤT BIẾN: text không thuộc hệ chữ không-dấu-cách -> `_noi_tu` == "
   "`\" \".join` từng byte")
# không MẤT CHỮ: ghép mọi cụm lại phải ra đủ chữ của kịch bản
_mat = []
for n, s in _CA:
    g = D._phrase_groups_even(s, 0.0, 8.0)
    if "".join(str(x[2]) for x in g).replace(" ", "") != s.replace(" ", ""):
        _mat.append(n)
ok(not _mat, "7c ghép MỌI cụm lại = đủ chữ kịch bản, không nuốt chữ nào",
   f"mất ở: {_mat}")
ok(D._KHONG_DAU_CACH.search("그") is None
   and D._KHONG_DAU_CACH.search("一") is not None
   and D._KHONG_DAU_CACH.search("、") is not None
   and D._KHONG_DAU_CACH.search("ア") is not None,
   "7d `_KHONG_DAU_CACH` đúng biên: hangul NGOÀI · chữ Hán TRONG · dấu câu "
   "CJK TRONG · kana TRONG (dán ký tự thật vào dải regex đọc không ra sai "
   "lệch — `豈` là U+8C48 chứ không phải U+F900, nuốt trọn hangul)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 8. ĐẦU-CUỐI — cue phụ đề thật sự nhiều lên ===")
try:
    from app.modules.m1_highlight import _recap_caption_cues as _cues
except Exception as e:      # noqa: BLE001 - máy thiếu cv2/torch -> ghi thẳng
    _cues = None
    print(f"  (bỏ qua: không nạp được m1_highlight — {type(e).__name__})")
if _cues is not None:
    def _ev(mod, p):
        dur = p[-1][1] - p[0][0]
        t = noi_cau(p)
        return {"start": round(p[0][0], 3), "end": round(p[-1][1], 3),
                "text": t, "clamped": True,
                "words": mod._phrase_groups_even(t, p[0][0], dur)}
    _c_nay = _cues([_ev(D, p) for p in ZH_PARTS])
    _c_moc = _cues([_ev(D_MOC, p) for p in ZH_PARTS]) if D_MOC else []
    ok(len(_c_nay) > len(_c_moc) * 5,
       f"8a cue phụ đề tiếng Trung: {len(_c_moc)} -> {len(_c_nay)}",
       f"{len(ZH_PARTS)} part")
    _dai = [b - a for a, b, _t, _k in _c_nay]
    ok(min(_dai) >= 0.12,
       f"8b cue ngắn nhất {min(_dai):.3f}s >= 0,12s — KHÔNG rơi vào bệnh "
       "'1 chữ Hán nhấp nháy 6 lần/giây' của cổng 21",
       f"trung vị {sorted(_dai)[len(_dai) // 2]:.3f}s")
    ok(all(" " not in str(t) for _a, _b, t, _k in _c_nay),
       "8c không cue nào bị chèn dấu cách giữa chữ Hán")
    _dai_moc = [b - a for a, b, _t, _k in _c_moc]
    ok(_dai_moc and max(_dai_moc) > 5.0,
       f"8d TỰ KIỂM BỘ DÒ: cue của bản MỐC dài tới {max(_dai_moc):.2f}s "
       "(một dòng chữ đứng im gần hết part)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 9. BẤT BIẾN CẢ FILE — băm chuỗi kết quả theo nhóm tiếng ===")
if _do_duoc:
    _bam: dict = {}
    for mod, ten in ((D_MOC, "moc"), (D, "nay")):
        for v in KHO4:
            g = str(v.get("nhom") or "?")
            ss = [(float(s["start"]), float(s["end"]),
                   str(s.get("text") or ""))
                  for s in v.get("segments") or []
                  if str(s.get("text") or "").strip()]
            h = _bam.setdefault((ten, g), hashlib.sha256())
            for p in parts(ss):
                txt = noi_cau(p)
                dur = max(0.2, p[-1][1] - p[0][0])
                h.update(repr(mod._phrase_groups_by_speech(
                    txt, 1.5, _sp3(dur))).encode("utf-8"))
                h.update(repr(mod._phrase_groups_even(
                    txt, 1.5, dur)).encode("utf-8"))
    for g in sorted({k[1] for k in _bam}):
        a = _bam[("moc", g)].hexdigest()[:16]
        b = _bam[("nay", g)].hexdigest()[:16]
        if g == "nhat":
            ok(a != b, f"9-{g} CỐ Ý khác mốc (chữ Nhật không có dấu cách)",
               f"{a} -> {b}")
        else:
            ok(a == b, f"9-{g} băm chuỗi kết quả Y HỆT mốc {MOC}",
               f"{a} == {b}")

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 74)
print(f"KẾT: ĐẠT {len(_OK)} · HỎNG {len(_FAIL)}")
for x in _FAIL:
    print("   HỎNG:", x)
sys.exit(1 if _FAIL else 0)
