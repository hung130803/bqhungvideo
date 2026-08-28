# -*- coding: utf-8 -*-
"""VIỆC 2 — "ASR CẮT ĐÔI THÀNH NGỮ, DỊCH RIÊNG RA VÔ NGHĨA".

Ca đích danh (`_kq_dich_anh_hung.json`, video `八位好莱坞导演…`):
    #78 `眼看尸体前脚下葬`   -> "Nhìn xác người đã được chôn một chân,"
    #79 `后脚他就已经开挖了` -> "chân còn lại anh đã bắt đầu đào."
`前脚…后脚` là thành ngữ *"vừa mới… thì đã…"*; tách ra thì mỗi nửa vô nghĩa.

**CÂU HỎI PHẢI TRẢ LỜI TRƯỚC KHI VIẾT MỘT DÒNG VÁ NÀO:** hai câu đó có nằm
CÙNG một lượt gọi LLM không? `_dich_loat` **đã** chia mẻ và gửi cả mẻ trong MỘT
prompt, **đã** kèm `ME_NGU_CANH_BEN = 3` câu trước/sau, và **đã** có luật
*"Câu ngắn/cụt là MỘT MẨU của câu dài đang nói dở"*. Nếu chúng cùng mẻ thì
model ĐÃ CÓ đủ ngữ cảnh mà vẫn dịch sai -> *"gộp cho có ngữ cảnh"* là vá vào
chỗ KHÔNG có bệnh, và phải tìm cách khác.

Chỉ ĐO, không sửa. Bản chép lời cache lại để lượt sau khỏi tốn lượt Groq.

    .venv\\Scripts\\python -u _do_gop_dich.py
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

from app.core import thay_giong as tg                 # noqa: E402

VIDEO = Path(r"C:\Users\Admin\Downloads\longtieng"
             r"\八位好莱坞导演联手拍的电影有多厉害#电影解说.mp4")
LAM = REPO / "_do_gd_tam"
CACHE = REPO / "_do_gd_chep.json"
KQ = REPO / "_kq_gop_dich.json"

#: Thành ngữ/cặp liên từ hay bị ASR chặt đôi. Dò để ĐẾM, không để sửa.
CAP_TU = [("前脚", "后脚"), ("不但", "而且"), ("虽然", "但是"),
          ("因为", "所以"), ("一边", "一边"), ("不是", "就是"),
          ("刚", "就"), ("既然", "那么"), ("除了", "还")]
_HAN = re.compile(r"[㐀-䶿一-鿿]")


def chep() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    LAM.mkdir(parents=True, exist_ok=True)
    wav = LAM / "goc.wav"
    if not wav.exists():
        tg.tach_wav(VIDEO, wav)
    print("  chép lời bằng Groq (lần đầu, sẽ cache)...")
    d = tg.chep_loi(wav)
    CACHE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def main() -> int:
    if not VIDEO.exists():
        print(f"KHÔNG thấy video: {VIDEO}")
        return 2
    d = chep()
    cau = tg.cau_tu_transcript(d)
    n = len(cau)
    L = [len(c["text"]) for c in cau]
    D = [c["end"] - c["start"] for c in cau]
    print(f"\n{VIDEO.name[:50]}")
    print(f"  segment thô {len(d.get('segments') or [])} -> câu {n}")
    print(f"  ký tự/câu: TB {statistics.fmean(L):.1f} · trung vị "
          f"{statistics.median(L):.0f} · min {min(L)} · max {max(L)}")
    print(f"  câu <= 8 ký tự: {sum(1 for x in L if x <= 8)}/{n} = "
          f"{100 * sum(1 for x in L if x <= 8) / n:.1f}%")
    print(f"  giây/câu:  TB {statistics.fmean(D):.2f} · trung vị "
          f"{statistics.median(D):.2f} · max {max(D):.2f}")
    print(f"  câu dài quá 12s (bị cau_tu_transcript CẮT): "
          f"{sum(1 for x in D if x > 12.0)}")

    mes = tg.chia_me_dich(cau, list(range(n)))
    o_me = {}
    for k, m in enumerate(mes):
        for i in m:
            o_me[i] = k
    print(f"\n  MẺ DỊCH: {len(mes)} mẻ · cỡ {[len(m) for m in mes]}")

    # ---- CẶP TỪ BỊ CHẶT ĐÔI: nằm cùng mẻ hay khác mẻ? ----
    print(f"\n  {'cặp bị chặt đôi':<14} | {'câu':>9} | mẻ | CÙNG MẺ? | "
          f"cách nhau")
    tim, cung, khac = 0, 0, 0
    vd = []
    for i in range(n - 1):
        t1, t2 = cau[i]["text"], cau[i + 1]["text"]
        for a, b in CAP_TU:
            if a in t1 and b in t2 and b not in t1 and a not in t2:
                tim += 1
                same = o_me.get(i) == o_me.get(i + 1)
                cung += int(same)
                khac += int(not same)
                vd.append({"i": i, "cap": f"{a}…{b}", "cung_me": same,
                           "t1": t1, "t2": t2})
                print(f"  {a + '…' + b:<14} | #{i:>3}-#{i + 1:<4} | "
                      f"{o_me.get(i)}/{o_me.get(i + 1)} | "
                      f"{'CÙNG' if same else 'KHÁC':>8} | "
                      f"{cau[i + 1]['start'] - cau[i]['end']:.2f}s")
                break
    print(f"\n  -> tìm được {tim} cặp bị chặt đôi · CÙNG mẻ {cung} · "
          f"KHÁC mẻ {khac}")

    # ---- mọi câu: bao nhiêu % có câu KỀ nằm khác mẻ (mất ngữ cảnh liền kề) --
    khac_ke = sum(1 for i in range(n - 1) if o_me.get(i) != o_me.get(i + 1))
    print(f"  ranh giới mẻ cắt ngang {khac_ke}/{n - 1} chỗ nối câu = "
          f"{100 * khac_ke / max(1, n - 1):.1f}%  (mỗi ranh giới vẫn còn "
          f"ME_NGU_CANH_BEN={tg.ME_NGU_CANH_BEN} câu trước/sau trong prompt)")

    ket = {"video": VIDEO.name, "so_segment": len(d.get("segments") or []),
           "so_cau": n, "ky_tu_tb": round(statistics.fmean(L), 1),
           "ky_tu_trung_vi": statistics.median(L),
           "ty_le_cau_duoi_8_ky_tu_%": round(100 * sum(1 for x in L if x <= 8) / n, 1),
           "giay_tb": round(statistics.fmean(D), 2),
           "so_cau_qua_12s": sum(1 for x in D if x > 12.0),
           "so_me": len(mes), "co_me": [len(m) for m in mes],
           "cap_bi_chat_doi": tim, "cung_me": cung, "khac_me": khac,
           "ranh_gioi_me_cat_ngang_%": round(100 * khac_ke / max(1, n - 1), 1),
           "ME_NGU_CANH_BEN": tg.ME_NGU_CANH_BEN, "vi_du": vd}
    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
