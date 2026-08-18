# -*- coding: utf-8 -*-
"""PIPER TRƯỚC/SAU GIÓNG HÀNG — chấm bằng THƯỚC ĐỘC LẬP `silencedetect`.

VÌ SAO PHẢI CÓ FILE NÀY. Đo Piper bằng Groq chép ngược (`_do_piper_moc_that`)
ra một cặp số MÂU THUẪN sau khi bật gióng hàng:
    RUNG      51,8 -> 29,5 ms   (TỐT HƠN, và tốt hơn cả edge-tts 38,6)
    % muộn    38,6% -> 47,6%    (XẤU ĐI)
Cả hai đến từ một chỗ: lệch HỆ THỐNG so với Groq nở ra +32,0 -> +46,5 ms.
Câu hỏi sống còn: **+46,5 ms đó là của PIPER hay của THƯỚC?**

Cổng 67 đã chốt luật cho đúng tình huống này: *lệch HỆ THỐNG đo bằng Groq
KHÔNG được coi là thuộc tính của máy đọc cho tới khi có thước THỨ BA* — và
đã có tiền lệ suýt trừ nhầm 94 ms cho ElevenLabs vì bỏ qua luật ấy.

THƯỚC THỨ BA: `silencedetect` — chỉ đo NĂNG LƯỢNG, không biết chữ nghĩa,
không phải mô hình, nên không thể thiên vị arm nào. Nó chỉ trả lời được MỘT
câu (chữ ĐẦU có rơi đúng lúc bắt đầu có tiếng không) nhưng đó đúng là câu mà
thước Groq không tự trả lời được.

Hai arm dùng CHÍNH `dubbing._synth_all_words` (cửa app thật), khác nhau đúng
một biến môi trường `BQ_GIONG_HANG`.

  .venv\\Scripts\\python -u _do_piper_thuoc_doc_lap.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

SO_CAU = int(os.environ.get("BQ_SO_CAU", "14"))
SAN = Path(os.environ.get("TEMP", "/tmp")) / f"bq_pipertd_{os.getpid()}"
GIONG_PIPER = "piper:vi_VN-vais1000-medium"
GIONG_EDGE = "vi-VN-NamMinhNeural"
RA = REPO / "_do_piper_thuoc_doc_lap.json"


def am_bat_dau(wav: str) -> float | None:
    import _do_giong_hang as D
    return D.am_bat_dau(wav)


def mot_arm(ten: str, giong: str, texts: list[str], bat_gh: bool) -> dict:
    """Đọc bằng CHÍNH cửa app rồi chấm chữ ĐẦU bằng `silencedetect`."""
    from app.core import dubbing
    cu = os.environ.get("BQ_GIONG_HANG")
    os.environ["BQ_GIONG_HANG"] = "1" if bat_gh else "0"
    san = SAN / ten
    san.mkdir(parents=True, exist_ok=True)
    try:
        paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
        ok, words = asyncio.run(dubbing._synth_all_words(
            texts, giong, paths, lang="vi"))
        lech = []
        for i in range(len(texts)):
            if not ok[i] or not words[i] or not Path(paths[i]).is_file():
                continue
            t = am_bat_dau(paths[i])
            if t is None:
                continue
            lech.append((float(words[i][0][0]) - t) * 1000.0)
        return {
            "n": len(lech), "co_moc": sum(1 for w in words if w),
            "trung_vi": round(statistics.median(lech), 1) if lech else None,
            "tb": round(sum(lech) / len(lech), 1) if lech else None,
            "muon_qua_50": sum(1 for x in lech if x > 50),
            "som_qua_50": sum(1 for x in lech if x < -50),
            "tho": [round(x, 1) for x in lech],
        }
    finally:
        if cu is None:
            os.environ.pop("BQ_GIONG_HANG", None)
        else:
            os.environ["BQ_GIONG_HANG"] = cu
        shutil.rmtree(san, ignore_errors=True)


def main() -> int:
    import _do_piper_moc_that as P
    texts = P.nap_cau()[:SO_CAU]
    print("=" * 76)
    print(f"PIPER — THƯỚC ĐỘC LẬP `silencedetect` · {len(texts)} câu tiếng Việt")
    print("Chữ ĐẦU lệch bao nhiêu so với lúc file THẬT SỰ bắt đầu có tiếng.")
    print("DƯƠNG = mốc MUỘN hơn tiếng (chữ hiện sau khi đã nói).")
    print("=" * 76)

    arms = [
        ("piper_truoc", "PIPER — mốc SUY RA (cách cũ)", GIONG_PIPER, False),
        ("piper_sau", "PIPER — GIÓNG HÀNG", GIONG_PIPER, True),
        ("edge", "edge-tts — WordBoundary (mốc 'THẬT')", GIONG_EDGE, False),
    ]
    kq = {}
    for khoa, nhan, giong, bat in arms:
        kq[khoa] = mot_arm(khoa, giong, texts, bat)
        d = kq[khoa]
        print(f"\n  {nhan}")
        print(f"     {d['co_moc']}/{len(texts)} câu có mốc · chấm được {d['n']} câu")
        print(f"     lệch chữ đầu: trung vị {d['trung_vi']:+.1f} ms · "
              f"TB {d['tb']:+.1f} ms")
        print(f"     muộn quá 50 ms: {d['muon_qua_50']}/{d['n']}  ·  "
              f"sớm quá 50 ms: {d['som_qua_50']}/{d['n']}")
    RA.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print()
    print("=" * 76)
    print("KẾT LUẬN")
    print("=" * 76)
    t, s, e = kq["piper_truoc"], kq["piper_sau"], kq["edge"]
    print(f"  Piper CŨ    {t['trung_vi']:+7.1f} ms")
    print(f"  Piper GIÓNG {s['trung_vi']:+7.1f} ms   <- thước ĐỘC LẬP nói gì")
    print(f"  edge-tts    {e['trung_vi']:+7.1f} ms")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(SAN, ignore_errors=True)
