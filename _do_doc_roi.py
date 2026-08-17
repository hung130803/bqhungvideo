# -*- coding: utf-8 -*-
"""PHÉP ĐO 2 — ĐỌC TOKEN RỜI, có ARM ĐỐI CHỨNG giọng bản ngữ.

**VÌ SAO PHẢI CÓ PHÉP ĐO NÀY.** `_do_doc_sai.py` chép ngược CẢ CÂU bằng Groq
(whisper-large-v3) — mà whisper là một MÔ HÌNH NGÔN NGỮ: nghe *"nét phờ lích"*
trong câu *"đứng đầu bảng xếp hạng ___"* thì nó vẫn viết ra `Netflix` vì đó là
từ hợp lý nhất ở chỗ đó. Tức **máy nghe CHỮA HỘ máy đọc**, và bảng số của phép
đo 1 có thể đang **phát chứng nhận cho thứ vẫn hỏng** — đúng họ bẫy `astats`
(cổng 53) và mức mờ 0,40 "sạch theo máy mà mắt vẫn đọc được chữ" (cổng 56b).

**CÁCH GỠ:** đọc token **MỘT MÌNH, không câu, không ngữ cảnh**. Không còn gì
cho mô hình ngôn ngữ bám vào, nên bản chép phản ánh ÂM THẬT sát hơn hẳn.

**VÀ PHẢI CÓ ĐỐI CHỨNG, nếu không con số vô nghĩa:** token rời thì máy nghe
nào cũng khó, kể cả khi phát âm chuẩn. Nên mỗi token đọc bằng **HAI giọng**:

  * arm ĐÍCH   — giọng của ngôn ngữ đang lồng (vd giọng Việt đọc "Netflix")
  * arm BẢN NGỮ — giọng en-US đọc chính token đó = **TRẦN đạt được**

Hiệu giữa hai arm mới là *"giọng Việt đọc chữ Anh tệ hơn bao nhiêu"*. Đo một
arm rồi kết luận là lặp lại bẫy "đo A/B phải đan xen / phải có mẫu số đúng" đã
sập nhiều lần trên máy này.

Chạy:  .venv\\Scripts\\python -u _do_doc_roi.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _bo_cau_thu_doc import CORPUS, NHAN_LOAI, NHAN_NN  # noqa: E402
from _do_doc_sai import cham_llm, chep_nguoc, khop_chuoi  # noqa: E402

HOP = REPO / "_do_doc_roi"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "doc_roi"
CACHE = HOP / "cache.json"

#: Giọng BẢN NGỮ của token gốc Latin — trần đạt được của phép đo.
GIONG_BAN_NGU = "en-US-AndrewNeural"

#: Chỉ đo loại có token "lạ với ngôn ngữ đích". `cau_thuong` là câu chứ không
#: phải token nên không đọc rời được; `ban_dia` thì giọng đích CHÍNH LÀ bản ngữ
#: nên không có gì để so.
LOAI_DO = ("ten_rieng", "viet_tat", "so_ngay", "don_vi")


def token_theo_nn(nn: str) -> list[tuple[str, str]]:
    """[(loại, token)] — bỏ trùng, giữ thứ tự."""
    ra, da = [], set()
    for loai, _c, toks in CORPUS[nn]:
        if loai not in LOAI_DO:
            continue
        for t in toks:
            if t not in da:
                da.add(t)
                ra.append((loai, t))
    return ra


def doc_loat(texts: list[str], voice: str, thu: Path) -> list[bool]:
    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    paths = [str(thu / f"t{i:03d}.mp3") for i in range(len(texts))]
    return asyncio.run(dubbing._synth_all(texts, voice, paths))


def mot_arm(ten_arm: str, toks: list[tuple[str, str]], voice: str,
            thu: Path, cache: dict) -> list[dict]:
    khoa = f"{ten_arm}|{voice}|{len(toks)}"
    if cache.get(khoa) and os.environ.get("BQ_DR_LAI") != "1":
        chep_ds = cache[khoa]
        print(f"  [{ten_arm}] dùng lại cache ({voice})")
    else:
        t0 = time.time()
        ok = doc_loat([t for _l, t in toks], voice, thu)
        chep_ds = []
        for i in range(len(toks)):
            mp3 = thu / f"t{i:03d}.mp3"
            chep_ds.append(chep_nguoc(mp3) if ok[i] and mp3.exists()
                           else "[không đọc được]")
        cache[khoa] = chep_ds
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"  [{ten_arm}] {voice} · đọc {sum(ok)}/{len(ok)} · "
              f"{time.time()-t0:.0f}s")
    ra = []
    for (loai, tok), chep in zip(toks, chep_ds):
        if khop_chuoi(tok, chep):
            dung, nghe = True, tok
        else:
            dung, nghe = cham_llm(tok, chep)
        ra.append({"arm": ten_arm, "loai": loai, "token": tok,
                   "chep": chep, "dung": dung, "nghe_ra": nghe})
    return ra


def main() -> int:
    from app.core.thay_giong import giong_theo_ngon_ngu
    HOP.mkdir(exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            cache = {}

    nns = [x.strip() for x in
           (os.environ.get("BQ_DR_NN") or "vi,zh,ja").split(",") if x.strip()]
    tat: dict[str, list[dict]] = {}
    # ARM ĐỐI CHỨNG chạy MỘT LẦN trên hợp token của mọi ngôn ngữ (token Latin
    # giống nhau ở cả 3 bộ) — đọc lại 3 lần là tốn công mà không thêm thông tin.
    toks_vi = token_theo_nn("vi")
    print(f"ARM ĐỐI CHỨNG (trần đạt được) · {len(toks_vi)} token")
    tat["__tran__"] = mot_arm("bản ngữ en-US", toks_vi, GIONG_BAN_NGU,
                              HOP / "tran", cache)
    for nn in nns:
        toks = token_theo_nn(nn)
        v = giong_theo_ngon_ngu(nn)
        print(f"\n=== {NHAN_NN[nn]} ({nn}) · {len(toks)} token ===")
        tat[nn] = mot_arm(NHAN_NN[nn], toks, v, HOP / nn, cache)
        dich = NGHE / nn
        dich.mkdir(parents=True, exist_ok=True)
        for i, (loai, t) in enumerate(toks):
            src = HOP / nn / f"t{i:03d}.mp3"
            if src.exists():
                ten = re.sub(r"[^0-9A-Za-z]+", "_", t)[:30] or f"tok{i}"
                shutil.copy2(src, dich / f"{i:02d}_{loai}_{ten}.mp3")

    print("\n" + "=" * 78)
    print("ĐỌC TOKEN RỜI (không ngữ cảnh) — tỉ lệ máy nghe KHÔNG nhận ra")
    print("=" * 78)
    cot = ["__tran__"] + nns
    ten_cot = {"__tran__": "TRẦN en-US", **{n: NHAN_NN[n] for n in nns}}
    head = f"{'Loại':<26}" + "".join(f"{ten_cot[c]:>13}" for c in cot)
    print(head)
    print("-" * len(head))
    for loai in LOAI_DO:
        d = f"{NHAN_LOAI[loai]:<26}"
        for c in cot:
            r = [x for x in tat[c] if x["loai"] == loai]
            sai = sum(1 for x in r if not x["dung"])
            d += f"{f'{sai}/{len(r)} ({100*sai/max(1,len(r)):.0f}%)':>13}"
        print(d)
    print("-" * len(head))
    d = f"{'TỔNG':<26}"
    for c in cot:
        r = tat[c]
        sai = sum(1 for x in r if not x["dung"])
        d += f"{f'{sai}/{len(r)} ({100*sai/max(1,len(r)):.0f}%)':>13}"
    print(d)

    print("\nTOKEN HỎNG Ở ARM ĐÍCH MÀ TRẦN ĐỌC ĐƯỢC (= lỗi CỦA GIỌNG, không "
          "phải của phép đo):")
    tran_ok = {x["token"] for x in tat["__tran__"] if x["dung"]}
    for n in nns:
        xau = [x for x in tat[n] if not x["dung"] and x["token"] in tran_ok]
        print(f"  [{NHAN_NN[n]}] {len(xau)} token")
        for x in xau:
            print(f"     «{x['token']}» -> nghe ra «{x['chep'][:60]}»")

    (HOP / "ket_qua.json").write_text(
        json.dumps(tat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSỐ LIỆU: {HOP/'ket_qua.json'}\nNGHE THỬ: {NGHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
