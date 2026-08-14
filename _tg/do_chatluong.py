# -*- coding: utf-8 -*-
"""ĐO CHẤT LƯỢNG TÁCH bằng SỐ (bước 1) — trên video THẬT.

Hai thước, phải đọc CẢ HAI (một mình thước nào cũng lừa được):

 1. RMS — `giam_giong_db` (giọng bị giảm bao nhiêu ở đoạn ĐANG NÓI, càng lớn
    càng sạch) và `giu_nhac_db` (nhạc mất bao nhiêu ở đoạn KHÔNG nói, càng gần
    0 càng tốt). Tách sạch mà mất luôn nhạc thì VÔ NGHĨA -> `loi_the_db`.

 2. CHÉP LẠI CHÍNH LỚP NHẠC bằng Groq. Đây là thước THẲNG THẮN nhất: nếu
    whisper vẫn chép ra đúng lời gốc từ lớp "nhạc" thì giọng CÒN NGUYÊN, bất
    kể RMS đẹp đến đâu. (Đã bắt được cách nhẹ bằng đúng thước này.)

    python _tg/do_chatluong.py --ten zh60
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _chep(path: Path, cache: Path) -> dict:
    """Chép lời bằng Groq THẬT (có cache ra file để khỏi đốt lượt)."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from app.core import transcribe as tr
    t0 = time.time()
    d = tr.transcribe(str(path))
    d["_giay_chep"] = round(time.time() - t0, 2)
    cache.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _mp3(src: Path, dst: Path) -> Path:
    """Nén sang mp3 cho nhẹ đường mạng (Groq nhận thoải mái)."""
    from app.core import thay_giong as tg
    if not dst.exists():
        tg._ffmpeg(["-i", str(src), "-ac", "1", "-ar", "16000", "-b:a", "64k",
                    str(dst)], "nén mp3 để chép lời")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ten", default="zh60")
    a = ap.parse_args()

    from app.core import thay_giong as tg

    ten = a.ten
    d_do = REPO / f"_tg/do_{ten}"
    goc = d_do / "goc.wav"
    if not goc.exists():
        d_do.mkdir(parents=True, exist_ok=True)
        src = REPO / f"_tg/asset/{ten}.wav"
        goc.write_bytes(src.read_bytes())

    # --- mốc từng từ của BẢN GỐC -> khoảng nói / khoảng im
    chep_goc = _chep(_mp3(goc, d_do / "goc.mp3"), REPO / f"_tg/chep_{ten}.json")
    tong = tg.probe_duration(goc)
    noi, im = tg.khoang_noi_im(chep_goc.get("words") or [], tong)
    print(f"[{ten}] {tong:.1f}s · {len(chep_goc.get('words') or [])} từ gốc "
          f"· {len(noi)} đoạn NÓI · {len(im)} đoạn IM")

    bang = []
    for cach in ("demucs", "nhe"):
        nhac = d_do / cach / "lop_nhac.wav"
        if not nhac.exists():
            print(f"  (chưa có {nhac} — chạy do_buoc1.py trước)")
            continue
        q = tg.do_chat_luong_tach(goc, nhac, noi, im)

        # thước 2: chép lại chính lớp nhạc
        mp3 = _mp3(nhac, d_do / cach / "nhac_de_chep.mp3")
        ch = _chep(mp3, REPO / f"_tg/chep_{ten}_{cach}_nhac.json")
        q["cach"] = cach
        q["chep_nhac_so_tu"] = len(ch.get("words") or [])
        q["chep_nhac_ngon_ngu"] = ch.get("language")
        q["chep_nhac_text"] = (ch.get("text") or "")[:120]
        q["goc_so_tu"] = len(chep_goc.get("words") or [])
        q["ro_ri_tu"] = (round(100.0 * q["chep_nhac_so_tu"]
                               / max(1, q["goc_so_tu"]), 1))
        bang.append(q)
        print(json.dumps(q, ensure_ascii=False, indent=1))

    out = REPO / f"_tg/ket_chatluong_{ten}.json"
    out.write_text(json.dumps(bang, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nĐã ghi {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
