# -*- coding: utf-8 -*-
"""GIỌNG VIỆT VieNeU ĐỌC TIẾNG ANH ĐƯỢC KHÔNG — phép đo cho anh Hùng.

CÂU HỎI: *"dùng Ngọc Huyền cho nói tiếng Anh được không?"*

═══════════════════════════════════════════════════════════════════════════
ĐI QUA CỬA THẬT
═══════════════════════════════════════════════════════════════════════════
`dubbing._synth_all(texts, "vn:Ngọc Huyền", paths)` -> `_vieneu_hay_khong`
-> `_chay_vieneu` -> `giong_vieneu.doc_loat`. **Không dựng đường riêng** —
đo đường không ai đi là đo cái không tồn tại.

═══════════════════════════════════════════════════════════════════════════
4 ARM, ĐAN XEN (đừng chạy liền mạch một arm rồi mới arm kia)
═══════════════════════════════════════════════════════════════════════════
  1. `vn:Ngọc Huyền` × câu **tiếng ANH**      — câu hỏi chính
  2. `vn:Ngọc Huyền` × câu **tiếng VIỆT**     — ĐỐI CHỨNG: mức nền của
     CHÍNH giọng đó. Không có nó thì không biết 10% là "hỏng vì tiếng Anh"
     hay "giọng này vốn 10%".
  3. `en-US-AriaNeural` × cùng câu tiếng Anh  — TRẦN đạt được
  4. `vi-VN-HoaiMyNeural` × câu tiếng Việt    — TRẦN tiếng Việt (để đọc
     được arm 2)
  5-6. 2 giọng VieNeu KHÁC × tiếng Anh        — chuyện riêng của Ngọc Huyền
     hay cả 20 giọng đều vậy

═══════════════════════════════════════════════════════════════════════════
BẪY: MÁY NGHE CHỮA HỘ MÁY ĐỌC -> PHẢI ĐO **CẢ HAI**
═══════════════════════════════════════════════════════════════════════════
Groq whisper là MỘT MÔ HÌNH NGÔN NGỮ: nghe *"nét phờ lích"* trong câu có ngữ
cảnh nó vẫn viết ra `Netflix`. Nên đo:
  · **TRONG CÂU** — token nằm giữa câu, máy nghe có ngữ cảnh để chữa;
  · **ĐỌC RỜI** — token một mình, không còn gì cho mô hình ngôn ngữ bám vào.
(`_do_doc_roi.py` đã đo được chênh lệch thật: trong câu 5% vs đọc rời 24%.)

═══════════════════════════════════════════════════════════════════════════
VieNeu KHÔNG TIỀN ĐỊNH -> CHẠY NHIỀU LƯỢT, BÁO DẢI
═══════════════════════════════════════════════════════════════════════════
OmniVoice từng đo ra 41,8% và 99,4% trên CÙNG một hàm. Arm VieNeu chạy
`BQ_VE_VONG` lượt (mặc định 2), bảng in **dải** chứ không in một số.
edge-tts tiền định nên 1 lượt là đủ (ghi thẳng ra, không giả vờ).

═══════════════════════════════════════════════════════════════════════════
THƯỚC
═══════════════════════════════════════════════════════════════════════════
  · **WER** (Levenshtein trên TỪ) của cả câu — dùng lại đúng hàm của
    `_do_chatter.wer`, so được giữa các arm TRONG CÙNG bộ câu này.
    **KHÔNG so thẳng với mốc 7,7%/6,2% của lượt 9** — mốc đó đo trên bộ câu
    KHÁC. Cột so được là arm ĐỐI CHỨNG ở ngay dưới.
  · **Token sai** — chấm theo TOKEN (`_do_doc_sai.khop_chuoi` + `cham_llm`),
    cùng bộ chấm đã tự kiểm 6 cặp biết đáp án.
  · **NHÃN NGÔN NGỮ máy nghe tự nhận** (lượt chép KHÔNG ép ngôn ngữ) — thước
    PHỤ, độc lập với việc chấm chữ: giọng Việt đọc tiếng Anh mà whisper dán
    nhãn "Vietnamese" là dấu hiệu nặng, thấy được mà không cần chấm từ.

Chạy:  .venv\\Scripts\\python -u _do_vieneu_en.py
Env:   BQ_VE_VONG=2   BQ_VE_LAI=1 (bỏ cache)   BQ_VE_ARM=NH_en,edge_en
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _bo_cau_thu_doc import CORPUS, NHAN_LOAI  # noqa: E402
from _do_doc_sai import cham_llm, khop_chuoi, tu_kiem_bo_cham  # noqa: E402

HOP = REPO / "_do_vn_en"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "vieneu_en"
CACHE = HOP / "cache.json"

#: (tên arm, mã giọng, ngôn ngữ corpus, có tiền định không)
ARMS: list[tuple[str, str, str, bool]] = [
    ("NH_en",   "vn:Ngọc Huyền",      "en", False),
    ("NH_vi",   "vn:Ngọc Huyền",      "vi", False),
    ("edge_en", "en-US-AriaNeural",   "en", True),
    ("edge_vi", "vi-VN-HoaiMyNeural", "vi", True),
    ("MD_en",   "vn:Minh Đức",        "en", False),
    ("TL_en",   "vn:Trúc Ly",         "en", False),
]

NHAN_ARM = {
    "NH_en":   "Ngọc Huyền x ANH",
    "NH_vi":   "Ngọc Huyền x VIỆT (đối chứng)",
    "edge_en": "edge Aria x ANH (TRẦN)",
    "edge_vi": "edge HoaiMy x VIỆT (trần Việt)",
    "MD_en":   "Minh Đức x ANH",
    "TL_en":   "Trúc Ly x ANH",
}

#: Nhãn ngôn ngữ Groq whisper trả về, theo mã ISO của corpus. Thước PHỤ
#: `nn_dung/nn_n` so với đúng bảng này; thiếu một tiếng là tiếng đó ra 0/34 và
#: bảng đọc thành "giọng hỏng" trong khi chỉ là bảng tra thiếu dòng.
TEN_NN = {"en": "English", "vi": "Vietnamese", "zh": "Chinese",
          "ja": "Japanese", "ko": "Korean"}

#: Loại có token "lạ với ngôn ngữ đích" -> đọc rời được. `cau_thuong` là CÂU
#: nên không đọc rời; `ban_dia` thì giọng đích chính là bản ngữ.
LOAI_TOKEN = ("ten_rieng", "viet_tat", "so_ngay", "don_vi")

#: Arm nào có đo ĐỌC RỜI (arm nào cũng đo thì tốn mà không thêm thông tin —
#: câu hỏi "đọc rời tệ hơn bao nhiêu" chỉ cần đích + trần + đối chứng).
ARM_ROI = ("NH_en", "edge_en", "NH_vi", "MD_en")


# --------------------------------------------------------------------- WER
#: Ký tự ĐƯỢC GIỮ khi chuẩn hoá. Bản cũ chỉ giữ `0-9a-zà-ỹA-ZÀ-Ỹ` + trắng, tức
#: **mọi chữ Hán · kana · hangul đều bị biến thành DẤU CÁCH** -> câu Trung /
#: Nhật / Hàn ra **0 token** -> `wer` trả 0,0 và `dem_op` trả (0,0,0,0), tức
#: bảng số **TỰ ĐẠT OAN** cho ba thứ tiếng. Đã đo trước khi vá:
#:
#:     zh  wer=(0.0, 0)  dem_op=(0,0,0,0)    <- mọi tỉ lệ ra 0
#:     ja  wer=(0.0, 0)  dem_op=(0,0,0,0)
#:     ko  wer=(0.0, 0)  dem_op=(0,0,0,0)    <- Hàn CÓ dấu cách vẫn hỏng, vì
#:                                              chính KÝ TỰ hangul bị vứt
#:     en  wer=(0.67, 9) dem_op=(0,6,0,9)    <- chỉ tiếng Anh là đúng
#:
#: Đây đúng lỗi đã sập ở cổng 52/54; nay dùng LẠI bộ giữ ký tự của
#: `recap._CJK_CHARS` (gồm cả hangul, để hangul không bị vứt) rồi giao việc
#: TÁCH cho `dubbing._tach_tu`.
from app.ai.recap import _CJK_CHARS as _GIU_CJK              # noqa: E402
_RAC_RE = re.compile("[^0-9a-zà-ỹA-ZÀ-Ỹ\\s" + _GIU_CJK + "]")


def chuan_tu(s: str) -> list[str]:
    """Chuẩn hoá + tách TỪ, **CJK-aware**. MỘT bộ tách cho MỌI cột số.

    Tách bằng `dubbing._tach_tu` chứ KHÔNG gọi thẳng `recap._word_tokens`:
    `recap` coi hangul là CJK nên nó cắt tiếng **Hàn** thành TỪNG ÂM TIẾT
    (câu 5 từ ra 20 token) — mà **tiếng Hàn CÓ dấu cách**, cắt kiểu đó là
    đổi mẫu số rồi mọi tỉ lệ của tiếng Hàn thành số khác hẳn. `_tach_tu` có
    bộ ký tự RIÊNG `_KHONG_DAU_CACH` (Hán · kana · Thái · Lào · Miến · Khmer,
    **KHÔNG hangul**) — đúng bài học cổng 54.

    **BẤT BIẾN:** chuỗi KHÔNG có ký tự CJK -> trả Y HỆT bản cũ
    (`re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\\s]", " ", s.lower()).split()`), nên mọi con
    số tiếng Anh/Việt đã công bố **không đổi một chữ số nào**.
    """
    from app.core.dubbing import _tach_tu
    return _tach_tu(_RAC_RE.sub(" ", (s or "").lower()))


def wer(goc: str, nghe: str) -> tuple[float, int]:
    """Tỉ lệ sai TỪ (Levenshtein trên TỪ). Trả (tỉ lệ, số từ gốc).

    Chép nguyên xi `_do_chatter.wer` — hai bản khác nhau là hai bảng số không
    so được với nhau. Chỉ khác đúng một chỗ: bộ tách nay là `chuan_tu`
    (CJK-aware), xem khối ghi chú ngay trên.
    """
    a, b = chuan_tu(goc), chuan_tu(nghe)
    if not a:
        return 0.0, 0
    tr = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        moi = [i]
        for j in range(1, len(b) + 1):
            moi.append(min(tr[j] + 1, moi[-1] + 1,
                           tr[j - 1] + (a[i - 1] != b[j - 1])))
        tr = moi
    return tr[len(b)] / len(a), len(a)


# ------------------------------------------------------------------- corpus
def cau_theo_nn(nn: str) -> list[tuple[str, str, list[str]]]:
    return list(CORPUS[nn])


def token_theo_nn(nn: str) -> list[tuple[str, str]]:
    ra, da = [], set()
    for loai, _c, toks in CORPUS[nn]:
        if loai not in LOAI_TOKEN:
            continue
        for t in toks:
            if t not in da:
                da.add(t)
                ra.append((loai, t))
    return ra


# ---------------------------------------------------------------- đọc + chép
def doc_loat(texts: list[str], voice: str, thu: Path, tien_to: str) -> list[bool]:
    """CỬA THẬT: `dubbing._synth_all` (nó tự rẽ sang `giong_vieneu.doc_loat`)."""
    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    paths = [str(thu / f"{tien_to}{i:03d}.mp3") for i in range(len(texts))]
    return asyncio.run(dubbing._synth_all(texts, voice, paths))


def chep(mp3: Path, lang: str | None) -> tuple[str, str]:
    """(chữ chép ngược, nhãn ngôn ngữ máy nghe trả về)."""
    from app.core import transcribe as TR
    try:
        r = TR.transcribe(str(mp3), language=lang)
        return str(r.get("text") or ""), str(r.get("language") or "")
    except Exception as e:                                     # noqa: BLE001
        return f"[lỗi chép: {type(e).__name__}: {str(e)[:60]}]", ""


# ------------------------------------------------------------------ một arm
def chay_arm(ten: str, voice: str, nn: str, vong: int, cache: dict,
             lam_lai: bool) -> dict:
    """Một arm, một lượt. Trả dict kết quả (đã cache theo (arm, vòng))."""
    khoa = f"{ten}|{voice}|{nn}|v{vong}"
    if cache.get(khoa) and not lam_lai:
        print(f"  [{ten} v{vong}] dùng lại cache")
        return cache[khoa]

    ds = cau_theo_nn(nn)
    cau = [c for _l, c, _t in ds]
    thu = HOP / f"{ten}_v{vong}"
    t0 = time.time()
    ok = doc_loat(cau, voice, thu, "c")
    t_cau = time.time() - t0
    print(f"  [{ten} v{vong}] câu: đọc {sum(ok)}/{len(ok)} · {t_cau:.0f}s")

    # ---- token ĐỌC RỜI (chỉ vài arm)
    toks: list[tuple[str, str]] = []
    ok_t: list[bool] = []
    t_tok = 0.0
    if ten in ARM_ROI:
        toks = token_theo_nn(nn)
        t1 = time.time()
        ok_t = doc_loat([t for _l, t in toks], voice, thu, "t")
        t_tok = time.time() - t1
        print(f"  [{ten} v{vong}] token rời: đọc {sum(ok_t)}/{len(ok_t)} · "
              f"{t_tok:.0f}s")

    # ---- chép ngược
    # ÉP ĐÚNG NGÔN NGỮ CỦA CORPUS. Bản cũ viết `"en" if nn == "en" else "vi"`
    # (lúc đó chỉ có hai tiếng) — để nguyên là **ép whisper chép tiếng Trung/
    # Nhật/Hàn bằng tiếng VIỆT**, tức đo một thứ khác hẳn rồi báo như thật.
    # `nn` chính là mã ISO-639-1 mà Groq nhận, nên với en/vi kết quả **không
    # đổi một ký tự**.
    ep = nn
    hang_cau = []
    for i, (loai, c, tks) in enumerate(ds):
        mp3 = thu / f"c{i:03d}.mp3"
        if not (ok[i] and mp3.exists()):
            hang_cau.append({"loai": loai, "cau": c, "tok": tks,
                             "chep": "[không đọc được]", "nn_tu_nhan": "",
                             "doc_duoc": False})
            continue
        txt, _ = chep(mp3, ep)
        # lượt THỨ HAI không ép ngôn ngữ -> thước PHỤ độc lập
        _t2, nn_tn = chep(mp3, None)
        hang_cau.append({"loai": loai, "cau": c, "tok": tks, "chep": txt,
                         "nn_tu_nhan": nn_tn, "doc_duoc": True})
    hang_tok = []
    for i, (loai, tk) in enumerate(toks):
        mp3 = thu / f"t{i:03d}.mp3"
        if not (ok_t[i] and mp3.exists()):
            hang_tok.append({"loai": loai, "token": tk,
                             "chep": "[không đọc được]", "doc_duoc": False})
            continue
        txt, _ = chep(mp3, ep)
        hang_tok.append({"loai": loai, "token": tk, "chep": txt,
                         "doc_duoc": True})

    kq = {"arm": ten, "voice": voice, "nn": nn, "vong": vong,
          "giay_cau": round(t_cau, 1), "giay_tok": round(t_tok, 1),
          "cau": hang_cau, "tok": hang_tok}
    cache[khoa] = kq
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return kq


# ------------------------------------------------------------------- chấm
def cham(kq: dict) -> dict:
    """Chấm một arm-lượt: WER + token trong câu + token đọc rời."""
    # WER
    wers, tong_tu = [], 0
    for h in kq["cau"]:
        if not h["doc_duoc"]:
            wers.append(1.0)
            tong_tu += len(h["cau"].split())
            continue
        r, nw = wer(h["cau"], h["chep"])
        wers.append(r)
        tong_tu += nw
    # token TRONG CÂU
    tc = []
    for h in kq["cau"]:
        for tk in h["tok"]:
            if not h["doc_duoc"]:
                tc.append({"loai": h["loai"], "token": tk, "dung": False,
                           "chep": h["chep"]})
                continue
            if khop_chuoi(tk, h["chep"]):
                tc.append({"loai": h["loai"], "token": tk, "dung": True,
                           "chep": h["chep"]})
            else:
                d, _n = cham_llm(tk, h["chep"])
                tc.append({"loai": h["loai"], "token": tk, "dung": d,
                           "chep": h["chep"]})
    # token ĐỌC RỜI
    tr = []
    for h in kq["tok"]:
        if not h["doc_duoc"]:
            tr.append({"loai": h["loai"], "token": h["token"], "dung": False,
                       "chep": h["chep"]})
            continue
        if khop_chuoi(h["token"], h["chep"]):
            tr.append({"loai": h["loai"], "token": h["token"], "dung": True,
                       "chep": h["chep"]})
        else:
            d, _n = cham_llm(h["token"], h["chep"])
            tr.append({"loai": h["loai"], "token": h["token"], "dung": d,
                       "chep": h["chep"]})
    nn_la = [h["nn_tu_nhan"] for h in kq["cau"] if h["doc_duoc"]]
    dung_nn = TEN_NN.get(kq["nn"], "Vietnamese")
    return {
        "wer": 100 * sum(wers) / max(1, len(wers)),
        "tong_tu": tong_tu,
        "tc_sai": sum(1 for x in tc if not x["dung"]), "tc_n": len(tc),
        "tr_sai": sum(1 for x in tr if not x["dung"]), "tr_n": len(tr),
        "tc": tc, "tr": tr,
        "nn_dung": sum(1 for x in nn_la if x == dung_nn), "nn_n": len(nn_la),
        "nn_khac": sorted({x for x in nn_la if x != dung_nn}),
    }


def dai(xs: list[float]) -> str:
    if not xs:
        return "—"
    if len(xs) == 1:
        return f"{xs[0]:.1f}"
    return f"{min(xs):.1f}–{max(xs):.1f} (TB {st.mean(xs):.1f})"


# -------------------------------------------------------------------- chạy
def main() -> int:
    HOP.mkdir(exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_VE_LAI") == "1"
    so_vong = int(os.environ.get("BQ_VE_VONG", "2"))
    chi = [x.strip() for x in (os.environ.get("BQ_VE_ARM") or "").split(",")
           if x.strip()]
    arms = [a for a in ARMS if not chi or a[0] in chi]

    print("=" * 78)
    print("VieNeu ĐỌC TIẾNG ANH — cửa thật `dubbing._synth_all` -> "
          "`giong_vieneu.doc_loat`")
    print("=" * 78)
    print(f"bộ câu: `_bo_cau_thu_doc.py` · en {len(CORPUS['en'])} câu / "
          f"{len(token_theo_nn('en'))} token rời · vi {len(CORPUS['vi'])} câu / "
          f"{len(token_theo_nn('vi'))} token rời")
    if not tu_kiem_bo_cham():
        print("BỘ CHẤM KHÔNG TIN ĐƯỢC -> DỪNG")
        return 2

    tat: dict[str, list[dict]] = {}
    for v in range(1, so_vong + 1):
        # ĐAN XEN + XOAY THỨ TỰ: chạy liền mạch một arm rồi mới arm kia là
        # arm chạy sau gánh phần máy đã nóng / mạng đã khác (bài học đo A/B).
        thu_tu = arms[v % len(arms):] + arms[:v % len(arms)]
        print(f"\n--- VÒNG {v}/{so_vong} · thứ tự: "
              f"{', '.join(a[0] for a in thu_tu)} ---")
        for ten, voice, nn, tien_dinh in thu_tu:
            if tien_dinh and v > 1:
                print(f"  [{ten} v{v}] BỎ QUA — edge-tts tiền định, 1 lượt đủ")
                continue
            kq = chay_arm(ten, voice, nn, v, cache, lam_lai)
            tat.setdefault(ten, []).append(cham(kq) | {"vong": v})

    # ---- giữ file cho anh Hùng tự nghe (vòng 1)
    for ten, voice, nn, _td in arms:
        src = HOP / f"{ten}_v1"
        if not src.is_dir():
            continue
        dich = NGHE / ten
        dich.mkdir(parents=True, exist_ok=True)
        ds = cau_theo_nn(nn)
        for i, (loai, c, _t) in enumerate(ds):
            f = src / f"c{i:03d}.mp3"
            if f.exists():
                nm = re.sub(r"[^0-9A-Za-zÀ-ỹ]+", "_", c)[:44]
                shutil.copy2(f, dich / f"cau{i:02d}_{loai}_{nm}.mp3")
        if ten in ARM_ROI:
            for i, (loai, tk) in enumerate(token_theo_nn(nn)):
                f = src / f"t{i:03d}.mp3"
                if f.exists():
                    nm = re.sub(r"[^0-9A-Za-zÀ-ỹ]+", "_", tk)[:30] or f"tok{i}"
                    shutil.copy2(f, dich / f"roi{i:02d}_{loai}_{nm}.mp3")

    # ---------------------------------------------------------------- bảng
    print("\n" + "=" * 78)
    print("BẢNG 1 — SAI TỪ (WER cả câu) · TOKEN TRONG CÂU · TOKEN ĐỌC RỜI")
    print("=" * 78)
    h = (f"{'arm':<32}{'WER %':>18}{'token TRONG CÂU':>20}"
         f"{'token ĐỌC RỜI':>20}")
    print(h)
    print("-" * len(h))
    for ten, _v, _nn, _td in arms:
        rs = tat.get(ten) or []
        if not rs:
            continue
        w = dai([r["wer"] for r in rs])
        tc = dai([100 * r["tc_sai"] / max(1, r["tc_n"]) for r in rs])
        tr = (dai([100 * r["tr_sai"] / max(1, r["tr_n"]) for r in rs])
              if rs[0]["tr_n"] else "—")
        print(f"{NHAN_ARM[ten]:<32}{w:>18}{tc:>20}{tr:>20}")

    print("\n" + "=" * 78)
    print("BẢNG 2 — TOKEN SAI THEO LOẠI (trong câu / đọc rời), vòng 1")
    print("=" * 78)
    cot = [a[0] for a in arms if tat.get(a[0])]
    h = f"{'loại':<26}" + "".join(f"{c:>22}" for c in cot)
    print(h)
    print("-" * len(h))
    for loai in ("cau_thuong",) + LOAI_TOKEN:
        d = f"{NHAN_LOAI[loai]:<26}"
        for c in cot:
            r = tat[c][0]
            a = [x for x in r["tc"] if x["loai"] == loai]
            b = [x for x in r["tr"] if x["loai"] == loai]
            sa = sum(1 for x in a if not x["dung"])
            sb = sum(1 for x in b if not x["dung"])
            o = f"{sa}/{len(a)}" if a else "—"
            o += f" | {sb}/{len(b)}" if b else " | —"
            d += f"{o:>22}"
        print(d)

    print("\n" + "=" * 78)
    print("BẢNG 3 — THƯỚC PHỤ: máy nghe TỰ NHẬN ngôn ngữ đúng bao nhiêu câu")
    print("=" * 78)
    for ten, _v, _nn, _td in arms:
        rs = tat.get(ten) or []
        if not rs:
            continue
        r = rs[0]
        khac = (", nhãn lạ: " + ", ".join(r["nn_khac"])) if r["nn_khac"] else ""
        print(f"  {NHAN_ARM[ten]:<32} {r['nn_dung']}/{r['nn_n']}{khac}")

    print("\n" + "=" * 78)
    print("TOKEN HỎNG Ở ARM `Ngọc Huyền x ANH` MÀ TRẦN edge ĐỌC ĐƯỢC")
    print("=" * 78)
    if tat.get("NH_en") and tat.get("edge_en"):
        for cot_ten, khoa in (("TRONG CÂU", "tc"), ("ĐỌC RỜI", "tr")):
            tran_ok = {x["token"] for x in tat["edge_en"][0][khoa] if x["dung"]}
            xau = [x for x in tat["NH_en"][0][khoa]
                   if not x["dung"] and x["token"] in tran_ok]
            print(f"  [{cot_ten}] {len(xau)} token")
            for x in xau:
                print(f"     «{x['token']}» -> nghe ra «{x['chep'][:70]}»")

    (HOP / "ket_qua.json").write_text(
        json.dumps({k: [{kk: vv for kk, vv in r.items()
                         if kk not in ("tc", "tr")} for r in v]
                    for k, v in tat.items()}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nSỐ LIỆU: {HOP / 'ket_qua.json'}")
    print(f"NGHE THỬ: {NGHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
