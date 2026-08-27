# -*- coding: utf-8 -*-
"""NGHI PHẠM SỐ 4: gói `vieneu` TỰ CHIA CHUNK rồi CHÈN IM LẶNG giữa các chunk.

`v3turbo.infer` -> `normalize_to_chunks_v3_with_gaps(text, max_chars=256)` ->
`join_audio_chunks(..., silence_ps=gaps_to_silence(gaps))`. Bảng im lặng:
    V3_GAP_SILENCE = {"para": 0.35, "sentence": 0.18, "minor": 0.04}
Tức MỖI ranh giới chunk là một khoảng IM CHÈN THÊM **nằm GIỮA câu** — đúng
hình dạng triệu chứng "đánh vần".

HÀM THUẦN, chạy trên **CẢ 236 câu tiếng Anh THẬT** của anh Hùng. Không model,
không GPU, TIỀN ĐỊNH.

CHẠY BẰNG PYTHON CỦA VENV VieNeu (gói `vieneu_utils` chỉ có ở đó).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CORPUS = Path(r"D:\claude\ai-content-studio\_kq_corpus_hung.json")
RA = Path(r"D:\claude\ai-content-studio\_kq_chunk_vn.json")

from vieneu_utils.core_utils import V3_GAP_SILENCE, gaps_to_silence  # noqa
from vieneu_utils.phonemize_text import (  # noqa
    normalize_to_chunks_v3_with_gaps)


def main() -> int:
    cau = json.loads(CORPUS.read_text("utf-8"))
    print(f"BẢNG IM LẶNG CHÈN GIỮA CHUNK: {V3_GAP_SILENCE}")
    print(f"Corpus: {len(cau)} câu tiếng Anh THẬT của anh Hùng "
          f"(_job_*/job.json)\n")

    nhieu = []
    dem_chunk: dict[int, int] = {}
    dem_gap: dict[str, int] = {}
    tong_im = 0.0
    for t in cau:
        ch, gaps = normalize_to_chunks_v3_with_gaps(t, max_chars=256)
        n = len(ch)
        dem_chunk[n] = dem_chunk.get(n, 0) + 1
        im = sum(gaps_to_silence(gaps)) if gaps else 0.0
        tong_im += im
        for g in gaps:
            dem_gap[g] = dem_gap.get(g, 0) + 1
        if n > 1:
            nhieu.append({"cau": t, "n": n, "chunks": ch, "gaps": gaps,
                          "im_s": round(im, 3)})

    print("SỐ CHUNK MỖI CÂU:")
    for n in sorted(dem_chunk):
        print(f"   {n} chunk : {dem_chunk[n]:3d} câu "
              f"({100.0*dem_chunk[n]/len(cau):5.1f}%)")
    n_nhieu = sum(v for k, v in dem_chunk.items() if k > 1)
    print(f"\n   >1 chunk (= CÓ chèn im giữa câu): {n_nhieu}/{len(cau)} "
          f"({100.0*n_nhieu/len(cau):.1f}%)")
    print(f"   loại ranh giới: {dem_gap}")
    print(f"   TỔNG im chèn thêm cả corpus: {tong_im:.2f}s "
          f"({tong_im/len(cau)*1000:.0f} ms/câu TB)")

    if nhieu:
        print("\nCÂU BỊ CHIA (tối đa 15 ca đầu):")
        for d in nhieu[:15]:
            print(f"   [{d['n']} chunk · im {d['im_s']}s] {d['cau']}")
            for c, g in zip(d["chunks"], list(d["gaps"]) + ["—"]):
                print(f"        {c!r}  --{g}-->")

    # ĐỐI CHỨNG CÓ RĂNG: bộ dò có thật sự chia được không? Ép max_chars nhỏ.
    ep = normalize_to_chunks_v3_with_gaps(cau[0], max_chars=16)
    print(f"\nĐỐI CHỨNG (bộ dò CÓ RĂNG) — cùng câu, max_chars=16:")
    print(f"   {cau[0]!r}")
    print(f"   -> {len(ep[0])} chunk, gaps={ep[1]}")

    RA.write_text(json.dumps({
        "bang_im": V3_GAP_SILENCE, "so_cau": len(cau),
        "dem_chunk": {str(k): v for k, v in dem_chunk.items()},
        "cau_nhieu_chunk": n_nhieu, "dem_gap": dem_gap,
        "tong_im_s": round(tong_im, 3),
        "vi_du": nhieu[:30],
        "doi_chung_max16": {"n": len(ep[0]), "gaps": ep[1]},
    }, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nĐÃ GHI {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
