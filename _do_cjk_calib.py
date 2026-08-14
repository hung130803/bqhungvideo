# -*- coding: utf-8 -*-
r"""HIỆU CHUẨN LƯỚI CHỐNG CHÉP LỜI CHO TIẾNG TRUNG (token = 1 KÝ TỰ).

    .venv\Scripts\python _do_cjk_calib.py

VÌ SAO PHẢI HIỆU CHUẨN CHỨ KHÔNG DÙNG LẠI HẰNG SỐ CŨ: `_RETELL_NGRAM=3` và
`_CONTENT_OVERLAP_MAX=0.55` được đo cho ngôn ngữ CÓ DẤU CÁCH, ở đó 1 token =
1 TỪ. Với tiếng Trung `_word_tokens` cho 1 token = 1 KÝ TỰ, nên "3 token liên
tiếp trùng" chỉ là 3 chữ Hán liền nhau — chuyện xảy ra suốt. Ghi chú trong
`recap.py` đã nói đúng điều đó và vì thế TẮT HẲN lưới cho CJK. Script này đo để
biết có ngưỡng nào TÁCH SẠCH hai nhóm không, thay vì đoán.

CORPUS **THẬT** (Groq thật, không bịa tay — quy tắc sắt "thành phần THẬT"):
  · nguồn: `_tq_work/trung_transcript.json` (video anh Hùng, 99 câu)
  · nhóm CHÉP/KỂ LẠI  -> LLM được YÊU CẦU kể lại chính lời nhân vật
  · nhóm SÁNG TÁC     -> LLM được YÊU CẦU bình luận từ góc NGOÀI, cấm chép
  · cộng 12 câu CHÉP NGUYÊN VĂN lấy thẳng từ transcript (ca chắc chắn phải bắt)
Kết quả cache ở `_tq_work/zh_narrate.json` để cổng chạy lại KHÔNG tốn lượt LLM.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"

_env = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
        / "BQHungVideo" / ".env")
if _env.exists():
    for _ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

CACHE = WORK / "zh_narrate.json"


def _cau() -> list:
    d = json.loads((WORK / "trung_transcript.json").read_text(encoding="utf-8"))
    return [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
            for s in d["segments"] if str(s.get("text") or "").strip()]


def sinh_corpus(ss: list) -> dict:
    """Gọi Groq THẬT sinh 2 nhóm câu dẫn tiếng Trung. Cache ra đĩa."""
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    from app.ai import llm
    doan = "\n".join(f"{a:.1f}-{b:.1f} {t}" for a, b, t in ss[:34])
    ra = {}
    for nhom, yeu_cau in (
        ("ke_lai",
         "Hãy KỂ LẠI bằng tiếng Trung nội dung từng câu thoại (diễn giải sát "
         "nghĩa, được đổi vài chữ và đảo trật tự, nhưng phải nói ĐÚNG chuyện "
         "trong lời thoại)."),
        ("sang_tac",
         "Hãy viết lời BÌNH LUẬN tiếng Trung từ góc NGOÀI (cảm xúc, phán "
         "đoán, đặt câu hỏi cho người xem). TUYỆT ĐỐI KHÔNG được kể lại nội "
         "dung câu thoại, KHÔNG dùng lại các từ trong lời thoại."),
    ):
        out = llm.complete_text(
            f"Đây là lời thoại (tiếng Trung) của một đoạn phim:\n{doan}\n\n"
            f"{yeu_cau}\n"
            "Trả về ĐÚNG 14 câu, mỗi câu 1 dòng, không đánh số, không giải "
            "thích gì thêm. Mỗi câu 15-40 chữ Hán.",
            system="Bạn là biên tập viên video. Trả lời gọn, đúng định dạng.",
            temperature=0.6)
        from app.ai.llm import bo_khoi_suy_nghi
        dong = [x.strip(" -·*0123456789.、") for x in
                bo_khoi_suy_nghi(out).splitlines()]
        ra[nhom] = [x for x in dong if len(x) >= 12][:14]
        print(f"  Groq -> {nhom}: {len(ra[nhom])} câu")
    CACHE.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return ra


def main() -> int:
    from app.ai import recap as R
    ss = _cau()
    corpus = sinh_corpus(ss)
    nguyen_van = [t for _a, _b, t in ss[8:20] if len(t) >= 12]

    # POSITIVE = phải BỊ BẮT · NEGATIVE = KHÔNG được bắt
    POS = [("nguyên văn", t) for t in nguyen_van] \
        + [("kể lại (Groq)", t) for t in corpus.get("ke_lai") or []]
    NEG = [("sáng tác (Groq)", t) for t in corpus.get("sang_tac") or []]
    print(f"\nCORPUS: {len(POS)} câu PHẢI BẮT · {len(NEG)} câu KHÔNG ĐƯỢC BẮT")

    tn = " ".join(R._norm_for_copy(t) for _a, _b, t in ss)
    wtext = R._window_text(ss, 0.0, 60.0)
    wwords = R._window_words(ss, 0.0, 60.0)

    print("\n== (1) LƯỚI CHÉP NGUYÊN VĂN `_is_transcript_copy` ==")
    b1 = sum(1 for _n, t in POS[:len(nguyen_van)]
             if R._is_transcript_copy(t, tn))
    print(f"   nguyên văn bị bắt: {b1}/{len(nguyen_van)}")
    print("   ghép 4 câu liền (LLM lười chép cả cụm): "
          f"{R._is_transcript_copy(''.join(nguyen_van[:4]), tn)}")

    print("\n== (2) QUÉT NGƯỠNG: tỉ lệ TẬP TỪ-NỘI-DUNG (order-independent) ==")
    def _ov(t):
        return R._content_overlap_ratio(t, wtext)
    _bang(POS, NEG, _ov, "overlap", (0.30, 0.45, 0.55, 0.65, 0.75, 0.85))

    print("\n== (3) QUÉT NGƯỠNG: n-gram TỪ-NỘI-DUNG LIÊN TIẾP dài nhất ==")
    def _ng(t):
        return _ngram_dai_nhat(R, t, wtext)
    _bang(POS, NEG, _ng, "n-gram", (3, 4, 5, 6, 7, 8, 9, 10), nguoc=True)

    print("\n== (4) QUÉT NGƯỠNG: `_fuzzy_copy_ratio` (token THÔ) ==")
    def _fz(t):
        return R._fuzzy_copy_ratio(t, wwords)
    _bang(POS, NEG, _fz, "fuzzy", (0.45, 0.60, 0.70, 0.80, 0.88, 0.94))
    return 0


def _ngram_dai_nhat(R, text: str, window_text: str) -> int:
    seq, win = R._content_seq(text), R._content_seq(window_text)
    if not seq or not win:
        return 0
    best = 0
    for n in range(1, min(len(seq), len(win)) + 1):
        g = {" ".join(win[i:i + n]) for i in range(len(win) - n + 1)}
        if any(" ".join(seq[i:i + n]) in g for i in range(len(seq) - n + 1)):
            best = n
        else:
            break
    return best


def _bang(POS, NEG, f, ten, nguongs, nguoc=False) -> None:
    vp = sorted(f(t) for _n, t in POS)
    vn = sorted(f(t) for _n, t in NEG)
    print(f"   PHẢI BẮT   : min {vp[0]} · trung vị {vp[len(vp)//2]} · "
          f"max {vp[-1]}")
    print(f"   KHÔNG BẮT  : min {vn[0]} · trung vị {vn[len(vn)//2]} · "
          f"max {vn[-1]}")
    for g in nguongs:
        bat_p = sum(1 for v in vp if v >= g)
        bat_n = sum(1 for v in vn if v >= g)
        cot = "TÁCH SẠCH" if bat_n == 0 and bat_p > 0 else ""
        print(f"     {ten} >= {g:<5} -> bắt {bat_p}/{len(vp)} ĐÚNG · "
              f"{bat_n}/{len(vn)} OAN   {cot}")


if __name__ == "__main__":
    sys.exit(main())
