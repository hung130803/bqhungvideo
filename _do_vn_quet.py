# -*- coding: utf-8 -*-
"""QUÉT CẢ 20 GIỌNG VieNeu — CÒN GIỌNG NÀO ĐỌC SAI VƯỢT TRẦN KHÔNG (19/08/2026).

Anh Hùng chỉ nêu đích danh `vn:Adam`, nhưng câu hỏi thật là *"còn mấy kiểu khác
nữa"*: giọng nào trong combo mà đo ra **sai chữ / bịa chữ** vượt trần thì phải
liệt kê hết, không chỉ nhìn một giọng.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO BỘ CÂU NGẮN (8 câu) CHỨ KHÔNG 34 CÂU NHƯ `_do_adam_en.py`
═══════════════════════════════════════════════════════════════════════════
21 arm × 34 câu là ~40 phút TTS + ~1.400 lượt Groq. Câu hỏi ở đây KHÁC câu hỏi
của `_do_adam_en.py`: nó không hỏi "giọng X sai bao nhiêu phần trăm" (cần mẫu
lớn) mà hỏi **"có giọng nào LỆCH HẲN khỏi đám còn lại không"** — dạng sàng lọc.
8 câu là đủ để một giọng hỏng NẶNG lộ ra, và cái giá là **không kết luận được
chênh lệch nhỏ**: ghi thẳng ra đây để đừng ai đọc bảng này như bảng chính xác.
Giọng nào lệch thì đo lại bằng bộ 34 câu.

═══════════════════════════════════════════════════════════════════════════
TRẦN LÀ `vi-VN-HoaiMyNeural` — SO VỚI CHÍNH THỨ ANH HÙNG ĐANG DÙNG
═══════════════════════════════════════════════════════════════════════════
Không có trần thì mọi con số là số trơ: máy nghe (Groq) tự nó cũng sai, và bộ
câu này có tên riêng / viết tắt nên sai vài % là bình thường. Arm edge chạy
CÙNG bộ câu, CÙNG bộ chấm.

`vn:Adam` cố ý ĐỨNG TRONG bảng này với bộ câu TIẾNG VIỆT: nó là giọng tiếng
Anh, nên số của nó ở đây trả lời câu *"chọn Adam cho video Việt thì tệ thế
nào"* — đúng ca anh Hùng dễ bấm nhầm nhất (200-300 kênh Việt).

Chạy:  .venv\\Scripts\\python -u _do_vn_quet.py
Env:   BQ_QUET_CAU=8 · BQ_QUET_LAI=1 (bỏ cache) · BQ_QUET_GIONG=Adam,Trúc Ly
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_vieneu_en as DV                                      # noqa: E402
from _do_adam_en import dem_op                                  # noqa: E402
from _do_doc_sai import cham_llm, khop_chuoi                    # noqa: E402
from app.core import giong_vieneu as VN                         # noqa: E402

HOP = REPO / "_do_vn_quet"
CACHE = HOP / "cache.json"
KQ_JSON = REPO / "_kq_vn_quet.json"
TRAN = "vi-VN-HoaiMyNeural"


def bo_cau(n: int) -> list[tuple[str, str, list[str]]]:
    """`n` câu tiếng Việt, LẤY ĐỦ MỌI LOẠI (không lấy n câu đầu).

    `CORPUS['vi']` xếp theo loại, nên `[:8]` là 8 câu `cau_thuong` -> bảng
    không có token tên riêng/viết tắt nào để chấm. Lấy vòng tròn theo loại.
    """
    theo_loai: dict[str, list] = {}
    for loai, c, toks in DV.CORPUS["vi"]:
        theo_loai.setdefault(loai, []).append((loai, c, toks))
    ra: list = []
    i = 0
    while len(ra) < n:
        them = False
        for loai in sorted(theo_loai):
            if i < len(theo_loai[loai]) and len(ra) < n:
                ra.append(theo_loai[loai][i])
                them = True
        if not them:
            break
        i += 1
    return ra


def chay_mot(ten: str, voice: str, ds: list, cache: dict,
             lam_lai: bool) -> dict:
    khoa = f"{voice}|{len(ds)}"
    if cache.get(khoa) and not lam_lai:
        print(f"  [{ten}] dùng lại cache")
        return cache[khoa]
    thu = HOP / ten.replace(":", "_").replace(" ", "_")
    t0 = time.time()
    ok = DV.doc_loat([c for _l, c, _t in ds], voice, thu, "c")
    giay = time.time() - t0
    hang = []
    for i, (loai, c, tks) in enumerate(ds):
        mp3 = thu / f"c{i:03d}.mp3"
        if not (ok[i] and mp3.exists()):
            hang.append({"loai": loai, "cau": c, "tok": tks,
                         "chep": "[không đọc được]", "doc_duoc": False})
            continue
        txt, _nn = DV.chep(mp3, "vi")
        hang.append({"loai": loai, "cau": c, "tok": tks, "chep": txt,
                     "doc_duoc": True})
    kq = {"voice": voice, "giay": round(giay, 1), "cau": hang}
    cache[khoa] = kq
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"  [{ten}] đọc {sum(ok)}/{len(ok)} · {giay:.0f}s")
    return kq


def cham(kq: dict) -> dict:
    """Sai token · bịa chữ · WER. Cùng bộ chấm `_do_vieneu_en` dùng."""
    sai = n_tok = 0
    thay = chen = thieu = tu = 0
    wers = []
    hong_cau = 0
    for h in kq["cau"]:
        if not h["doc_duoc"]:
            hong_cau += 1
            wers.append(1.0)
            n_tok += len(h["tok"])
            sai += len(h["tok"])
            continue
        r, _n = DV.wer(h["cau"], h["chep"])
        wers.append(r)
        t_, c_, k_, n_ = dem_op(h["cau"], h["chep"])
        thay += t_
        chen += c_
        thieu += k_
        tu += n_
        for tk in h["tok"]:
            n_tok += 1
            if khop_chuoi(tk, h["chep"]):
                continue
            d, _ = cham_llm(tk, h["chep"])
            sai += 0 if d else 1
    return {"wer": 100 * sum(wers) / max(1, len(wers)),
            "tok_sai": sai, "tok_n": n_tok,
            "thay": thay, "chen": chen, "thieu": thieu, "tu": tu,
            "hong_cau": hong_cau, "giay": kq.get("giay")}


def main() -> int:
    HOP.mkdir(exist_ok=True)
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_QUET_LAI") == "1"
    so_cau = int(os.environ.get("BQ_QUET_CAU", "8"))
    chi = [x.strip() for x in (os.environ.get("BQ_QUET_GIONG") or "").split(",")
           if x.strip()]
    ds = bo_cau(so_cau)

    print("=" * 78)
    print("QUÉT 20 GIỌNG VieNeu + TRẦN edge-tts — CÂU TIẾNG VIỆT, cửa thật")
    print("=" * 78)
    print(f"bộ câu: {len(ds)} câu · loại: "
          f"{', '.join(sorted({l for l, _c, _t in ds}))}")
    print("SÀNG LỌC, KHÔNG PHẢI BẢNG CHÍNH XÁC: 8 câu chỉ đủ bắt giọng lệch "
          "HẲN; chênh vài % là nhiễu.")

    arms: list[tuple[str, str]] = [("edge HoaiMy (TRẦN)", TRAN)]
    for k, _mo in VN.GIONG_VN:
        if chi and k not in chi:
            continue
        arms.append((f"vn:{k}", VN.TIEN_TO + k))
    if chi:
        arms = [a for a in arms if a[0] == "edge HoaiMy (TRẦN)"
                or a[0][3:] in chi]

    kq_tat: dict[str, dict] = {}
    for ten, voice in arms:
        kq_tat[ten] = cham(chay_mot(ten, voice, ds, cache, lam_lai))

    tran = kq_tat.get("edge HoaiMy (TRẦN)") or {}
    tran_tok = 100 * tran.get("tok_sai", 0) / max(1, tran.get("tok_n", 1))
    tran_bia = 100 * tran.get("chen", 0) / max(1, tran.get("tu", 1))

    print("\n" + "=" * 78)
    print("BẢNG — SẮP THEO SAI TOKEN GIẢM DẦN")
    print("=" * 78)
    print(f"{'giọng':<26}{'token sai %':>12}{'bịa chữ %':>11}{'thiếu %':>9}"
          f"{'WER %':>8}{'câu hỏng':>10}{'giây':>7}")
    hang = sorted(kq_tat.items(),
                  key=lambda kv: -100 * kv[1]["tok_sai"] / max(1, kv[1]["tok_n"]))
    for ten, c in hang:
        t = 100 * c["tok_sai"] / max(1, c["tok_n"])
        b = 100 * c["chen"] / max(1, c["tu"])
        k = 100 * c["thieu"] / max(1, c["tu"])
        print(f"{ten:<26}{t:>12.1f}{b:>11.1f}{k:>9.1f}{c['wer']:>8.1f}"
              f"{c['hong_cau']:>10}{c['giay'] or 0:>7.0f}")

    print(f"\nTRẦN edge-tts: token sai {tran_tok:.1f}% · bịa chữ "
          f"{tran_bia:.1f}%")
    # VƯỢT TRẦN = quá TRẦN + 10 điểm %. Biên 10 điểm là vì mẫu chỉ 8 câu: với
    # ~20 token thì 1 token = 5 điểm %, nên chênh dưới ~10 điểm là nhiễu của
    # phép sàng lọc, không phải kết luận. (Ai muốn ngưỡng chặt hơn thì phải
    # chạy bộ 34 câu, đừng siết ngưỡng trên bộ 8 câu.)
    BIEN = 10.0
    vuot = []
    for ten, c in hang:
        t = 100 * c["tok_sai"] / max(1, c["tok_n"])
        b = 100 * c["chen"] / max(1, c["tu"])
        if t > tran_tok + BIEN or b > tran_bia + BIEN or c["hong_cau"]:
            vuot.append((ten, t, b, c["hong_cau"]))
    print("\n" + "=" * 78)
    print(f"GIỌNG VƯỢT TRẦN (> trần + {BIEN:.0f} điểm %, hoặc có câu KHÔNG "
          f"đọc được)")
    print("=" * 78)
    if not vuot:
        print("  KHÔNG có giọng nào vượt trần.")
    for ten, t, b, h in vuot:
        print(f"  {ten:<26} token sai {t:.1f}% · bịa {b:.1f}% · câu hỏng {h}")

    tt = [100 * c["tok_sai"] / max(1, c["tok_n"]) for k, c in kq_tat.items()
          if k != "edge HoaiMy (TRẦN)"]
    if tt:
        print(f"\n20 giọng VieNeu: token sai {min(tt):.1f}–{max(tt):.1f}% "
              f"(trung vị {st.median(tt):.1f}%)")

    KQ_JSON.write_text(json.dumps(
        {"tran": {"tok": tran_tok, "bia": tran_bia}, "arm": kq_tat,
         "so_cau": len(ds), "luc": time.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSố thô: {KQ_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
