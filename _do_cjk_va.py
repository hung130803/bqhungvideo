# -*- coding: utf-8 -*-
r"""ĐO 3 LỖ HỔNG CJK **TRƯỚC / SAU** BẢN VÁ (chạy được ở cả hai bản).

    .venv\Scripts\python _do_cjk_va.py

Luồng trước đã CHỨNG MINH 3 lỗ hổng bằng số đo (chỉ được phép chạm
`captions.py` nên không vá). Script này đo LẠI đúng 3 chỗ đó để có cặp
số TRƯỚC/SAU, và nó **không phụ thuộc bản vá**: chỗ nào chưa có API mới thì
in "(bản cũ)" chứ không nổ.

  VIỆC 1  `app/core/lop_phu.py` — khối `_CJK` có Nhật/Hàn, KHÔNG có tiếng Trung
          + BẪY CHÉO NGÔN NGỮ (`料理` Nhật=nấu ăn / Trung=xử lý).
  VIỆC 2  `app/ai/recap.py` — `.split()` trên chữ chép lời -> câu CJK ra 1 token.
  VIỆC 3  `app/ai/hook_to_mo.py` — `_HUA_HEN` 26 từ, 0 chữ Hán.

Nguồn lời tiếng Trung: `_tq_work/trung_transcript.json` (Groq THẬT, video
`我的观影报告…mp4` của anh Hùng, 187,27 s, 99 câu / 1.132 ký tự).
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
import _test_guard  # noqa: E402,F401 - CẤM đụng máy anh Hùng

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def _tr() -> dict:
    p = WORK / "trung_transcript.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ====================================================================== VIỆC 1
def viec1() -> None:
    from app.core import lop_phu as LP
    print("\n" + "=" * 72)
    print("VIỆC 1 — lop_phu.py: bảng từ khoá cảnh gặp tiếng TRUNG")
    print("=" * 72)

    co_zh = hasattr(LP, "_ZH")
    print(f"  bảng _ZH (từ khoá tiếng Trung riêng): "
          f"{'CÓ — ' + str(len(LP._ZH)) + ' cảnh' if co_zh else 'CHƯA CÓ'}")

    print("\n-- (a) BẪY CHÉO NGÔN NGỮ: cùng chữ Hán, KHÁC nghĩa Trung/Nhật --")
    BAY = (("料理", "Nhật=nấu ăn · TRUNG=XỬ LÝ/giải quyết", "cam"),
           ("手紙", "Nhật=lá thư · TRUNG=GIẤY VỆ SINH", "phu"))
    for tu, y, _o in BAY:
        for lang, nhan in (("", "bản MẶC ĐỊNH (Nhật/Hàn)"), ("zh", "tiếng TRUNG")):
            cam, khop = [], []
            for k, l in LP.LUAT.items():
                rm, rp, rc = _mau(LP, l, lang)
                if LP._co(tu, rc):
                    cam.append(k)
                if LP._co(tu, rm) or LP._co(tu, rp):
                    khop.append(k)
            print(f"  '{tu}' [{nhan:<24}] CẤM oan: {cam or '—'} · "
                  f"khớp: {khop or '—'}")
        print(f"      ({y})")

    tr = _tr()
    if not tr:
        print("  BỎ QUA (b)(c): chưa có _tq_work/trung_transcript.json")
        return
    loi = "".join(str(s.get("text") or "") for s in tr.get("segments") or [])
    print(f"\n-- (b) LỜI TRUNG THẬT ({len(loi)} ký tự · "
          f"language={tr.get('language')!r}) --")
    for lang, nhan in (("", "bản MẶC ĐỊNH"), ("zh", "bảng TIẾNG TRUNG")):
        n = 0
        chi_tiet = []
        for k, l in LP.LUAT.items():
            rm, rp, rc = _mau(LP, l, lang)
            for ten, bo, tu_goc in (("MẠNH", rm, _tu(LP, l, lang, "manh")),
                                    ("PHỤ", rp, _tu(LP, l, lang, "phu")),
                                    ("CẤM", rc, _tu(LP, l, lang, "cam"))):
                for i, r in enumerate(bo):
                    if LP._co(loi, [r]):
                        n += 1
                        if len(chi_tiet) < 24:
                            chi_tiet.append(f"{k}/{ten}/{tu_goc[i]}")
        tong = sum(len(x) for l in LP.LUAT.values()
                   for x in _mau(LP, l, lang))
        print(f"  [{nhan:<18}] {n}/{tong} từ khoá khớp — {', '.join(chi_tiet)}")

    print("\n-- (c) ĐIỂM TỰ TIN trên lời Trung thật (ngưỡng "
          f"{LP.NGUONG_TIN}) --")
    segs = [[0.0, float(tr.get("duration") or 187.27)]]
    dg = LP.digest_tu_loi(tr, segs)
    print(f"  digest_tu_loi -> {len(dg)} mốc · "
          f"mốc mang nhãn lang: {sum(1 for d in dg if d.get('lang'))}")
    for lang, nhan in (("", "bản MẶC ĐỊNH"), ("zh", "bảng TIẾNG TRUNG")):
        bang = []
        for k, l in LP.LUAT.items():
            d = _diem(LP, l, dg, "", lang)
            if d:
                bang.append((d["tin"], k, d))
        bang.sort(reverse=True)
        top = " · ".join(f"{k} {t:.2f}" for t, k, _d in bang[:4])
        qua = [k for t, k, _d in bang if t >= LP.NGUONG_TIN]
        print(f"  [{nhan:<18}] {top}  -> vượt ngưỡng: {qua or 'KHÔNG CÁI NÀO'}")

    print("\n-- (d) chon_lop_phu trên 3 đoạn cắt THẬT của video --")
    for ten, ss in (("cả video", [[0.0, 187.27]]),
                    ("đoạn LẶN (0-60s)", [[0.0, 60.0]]),
                    ("đoạn KHO BÁU (55-90s)", [[55.0, 90.0]])):
        d2 = LP.digest_tu_loi(tr, ss)
        ra, ly = _chon(LP, d2, "", sum(e - s for s, e in ss), tr)
        print(f"  {ten:<22} -> {len(ra)} lớp phủ · "
              f"{(ra[0]['khoa'] + ' / ' + ra[0]['canh']) if ra else '—'}")
        print(f"      {ly[:150]}")


def _mau(LP, l, lang: str) -> tuple:
    f = getattr(LP, "_mau_loi", None)
    if f is None:
        return l._rd_manh, l._rd_phu, l._rd_cam
    return f(l, lang)


def _tu(LP, l, lang: str, o: str) -> list:
    f = getattr(LP, "_tu_loi", None)
    if f is None:
        return list(getattr(l, o))
    return f(l, lang, o)


def _diem(LP, l, dg, loi, lang):
    try:
        return LP._diem(l, dg, loi, lang)
    except TypeError:
        return LP._diem(l, dg, loi)


def _chon(LP, dg, loi, giay, tr):
    try:
        return LP.chon_lop_phu(dg, loi, giay,
                               ngon_ngu=str(tr.get("language") or ""))
    except TypeError:
        return LP.chon_lop_phu(dg, loi, giay)


# ====================================================================== VIỆC 2
def viec2() -> None:
    from app.ai import recap as R
    print("\n" + "=" * 72)
    print("VIỆC 2 — recap.py: `.split()` trên chữ chép lời (câu CJK = 1 token)")
    print("=" * 72)
    tr = _tr()
    ss = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
          for s in (tr.get("segments") or []) if s.get("text")]
    if not ss:
        print("  BỎ QUA: chưa có bản chép lời tiếng Trung.")
        return

    cau = ss[12][2] if len(ss) > 12 else ss[0][2]
    cau_dai = "".join(x[2] for x in ss[10:14])
    print(f"\n-- (a) SỐ TOKEN của câu Trung (câu: «{cau_dai[:40]}…») --")
    print(f"  .split()        -> {len(cau_dai.split())} token")
    print(f"  _word_tokens()  -> {len(R._word_tokens(R._norm_for_copy(cau_dai)))}"
          " token")

    print("\n-- (b) 5 HÀM ĐẾM TỪ: câu Trung ra bao nhiêu? --")
    for ten, f in (("_content_pron_set", R._content_pron_set),
                   ("_content_seq", R._content_seq),
                   ("_content_words", R._content_words)):
        print(f"  {ten:<20}(câu Trung 4 câu) -> {len(f(cau_dai))} phần tử")
    tn = " ".join(R._norm_for_copy(t) for _a, _b, t in ss)
    win = R._window_words(ss, 10.0, 17.0)
    print(f"  _window_words    (10-17s)      -> {len(win)} phần tử")
    print(f"  _fuzzy_copy_ratio(CHÉP NGUYÊN VĂN vs cửa sổ) -> "
          f"{R._fuzzy_copy_ratio(cau_dai, win):.3f} (0.0 = lưới TẮT)")

    print("\n-- (c) 3 LƯỚI CHỐNG CHÉP LỜI có CHẠY cho tiếng Trung không --")
    ca = (("CHÉP NGUYÊN VĂN 4 câu", cau_dai, True),
          ("CHÉP NGUYÊN VĂN 1 câu dài", ss[13][2], True),
          ("KỂ LẠI (đảo/đổi vài chữ)",
           "他立刻认出这是古代船只使用的压舱石头", True),
          ("SÁNG TÁC thật (không chép)",
           "这个男人的运气实在太好了让人羡慕不已真是天上掉馅饼", False))
    for ten, t, mong in ca:
        a = R._is_transcript_copy(t, tn)
        b = R._is_copy_narrate(t, ss, 10.0, 17.0)
        print(f"  {ten:<28} nguyên văn={a!s:<5} kể lại={b!s:<5} "
              f"(mong đợi BỊ BẮT={mong})")
    print("  _is_relevant(câu Trung, tập từ khung) -> "
          f"{R._is_relevant(cau_dai, R._window_words(ss, 10.0, 17.0))}")

    print("\n-- (d) BẤT BIẾN EN/VI: _word_tokens == .split() --")
    for t in ("The moment I touched the valve I heard a loud hiss",
              "Gã này vừa mất cả gia tài chỉ vì một cú click chuột"):
        n = R._norm_for_copy(t)
        print(f"  {'ĐẠT' if R._word_tokens(n) == n.split() else 'HỎNG'} "
              f"— «{t[:44]}…»")

    print("\n-- (e) QUÉT `.split()` CÒN LẠI (AST, bỏ comment/chuỗi) --")
    import ast
    src = (REPO / "app" / "ai" / "recap.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "split" and not node.args):
            v = node.func.value
            kind = ("HẰNG CHUỖI (chỉ tách bảng stopword) -> ĐỂ YÊN"
                    if isinstance(v, ast.Constant) else "TRÊN BIẾN -> phải soi")
            print(f"  dòng {node.lineno:<5} {kind}")


# ====================================================================== VIỆC 3
def viec3() -> None:
    from app.ai import hook_to_mo as H
    print("\n" + "=" * 72)
    print("VIỆC 3 — hook_to_mo.py: `_HUA_HEN` không có chữ Hán")
    print("=" * 72)
    for ten, tap in (("_DO_DANG", H._DO_DANG), ("_PHAT_HIEN", H._PHAT_HIEN),
                     ("_CAU_HOI", H._CAU_HOI), ("_BAT_NGO", H._BAT_NGO),
                     ("_HUA_HEN", H._HUA_HEN), ("_XAU", H._XAU)):
        han = [t for t in tap
               if any(0x4E00 <= ord(c) <= 0x9FFF for c in t)
               and not any(0x3040 <= ord(c) <= 0x30FF for c in t)]
        print(f"  {ten:<12} {len(tap):>3} từ · chỉ-chữ-Hán {len(han):>2}: "
              f"{', '.join(han[:10])}")
    print("\n-- câu Trung «hứa hẹn có cấu trúc» được chấm bao nhiêu --")
    CAU = ("首先我们来看第一步该怎么做",
           "接下来我教你一个最简单的办法",
           "别急看到最后你就明白了",
           "大家好今天我们来聊聊这个话题")
    for c in CAU:
        d, ly = H.cham_cau(c, 2.5)
        print(f"  {d:.3f} (ngưỡng {H.NGUONG}) «{c}» — {ly}")


def main() -> int:
    viec1()
    viec2()
    viec3()
    return 0


if __name__ == "__main__":
    sys.exit(main())
