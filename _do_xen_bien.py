# -*- coding: utf-8 -*-
"""VIỆC 2 — XÉN IM Ở BIÊN MỖI MẢNH TRƯỚC KHI DÁN: ĐO 3 MỨC XÉN.

**BỆNH ĐO ĐƯỢC (bảng 0):** file nghe thử `_NGHE_THU_ANH_HUNG/nhan_nha_them/`
được `_nghe_thu_nhan_nha.noi()` nối **RAW**, KHÔNG qua `cat_le_loat`. Mỗi
lượt gọi edge-tts kèm ~0,19 s im ĐẦU + ~0,84 s im ĐUÔI, nên **mỗi mối nối =
~1,03 giây chết**. Đo được `vi_VN_NamMinhNeural__1_TRUOC` có **38,2% là im**.
Đó chính là *"NGẮT QUÃNG QUÁ NHIỀU"* anh Hùng nghe thấy.

**PHẢI NÓI RÕ MỘT ĐIỀU KẺO KẾT LUẬN SAI:** đường XUẤT THẬT của app **ĐÃ** xén
lề từ v2.27.0 (`doc_ban_dich` -> `cat_le_loat`, `GIU_DAU=0,04` ·
`GIU_CUOI=0,08`). Nên bệnh này là bệnh của **FILE NGHE THỬ**, không phải của
video anh Hùng xuất ra. Lẫn hai cái là đi vá nhầm chỗ.

**GIỚI HẠN CỦA PHÉP ĐO NÀY, GHI THẲNG:** xén lề KHÔNG đụng một mẫu âm nào của
TIẾNG NÓI, nên `nhan_nha` và `đọc sai` gần như KHÔNG THỂ đổi — hai cột đó ở
đây là **chốt CHỐNG LÀM HỎNG**, không phải chốt chứng minh cái hay. Thứ duy
nhất phán được *"xén sạch quá thì nghe như máy"* là **TAI**; vì vậy script
sinh file nghe thử. Cột đọc sai vẫn có răng ở một chỗ THẬT: xén sạch 0/0 gọt
mất phụ âm đầu/đuôi -> ASR chép sai.

Chạy:  .venv\\Scripts\\python -u _do_xen_bien.py
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from config import settings                                    # noqa: E402
from app.core import thay_giong as tg                          # noqa: E402
import _do_nhan_nha as NN                                      # noqa: E402
from _do_lien_mach import (khoang_im, _dur, _noi_thang,        # noqa: E402
                           lay_corpus, MAY, NOWIN)

SAN = REPO / "bq_do_xen_bien"
KQ = REPO / "_kq_lienmach"

#: (tên, giữ ĐẦU, giữ CUỐI) — `None` = KHÔNG xén (hiện trạng file nghe thử).
MUC = (
    ("M0_KHONG_XEN", None, None),
    ("M1_XEN_NHE",   0.15, 0.30),
    ("M2_APP",       tg.GIU_DAU, tg.GIU_CUOI),   # ĐANG DÙNG trong app
    ("M3_XEN_SACH",  0.00, 0.00),
)


def xen(src: Path, dst: Path, giu_dau, giu_cuoi) -> tuple[float, float, float]:
    """Xén lề im. Trả (dài sau, im đầu TRƯỚC, im cuối TRƯỚC)."""
    dau, cuoi, tong = tg.do_le_im(src)
    if giu_dau is None:
        subprocess.run(
            [settings.FFMPEG_PATH, "-y", "-v", "error", "-i", str(src),
             "-af", "aresample=44100", "-ac", "1", "-ar", "44100",
             "-c:a", "pcm_s16le", str(dst)],
            capture_output=True, creationflags=NOWIN)
        return (_dur(dst), dau, cuoi)
    a = max(0.0, dau - giu_dau)
    b = max(a + 0.01, tong - max(0.0, cuoi - giu_cuoi))
    subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-v", "error", "-i", str(src), "-af",
         f"aresample=44100,atrim=start={a:.3f}:end={b:.3f},asetpts=N/SR/TB",
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, creationflags=NOWIN)
    return (_dur(dst), dau, cuoi)


def chep_nguoc(wav: Path, nn: str) -> str:
    """Groq chép ngược — bộ đếm ĐỌC SAI. Hỏng thì trả '' (KHÔNG bịa)."""
    try:
        from app.core.transcribe import transcribe
        d = transcribe(str(wav), language=nn)
        return " ".join(str(s.get("text", "")) for s in (d.get("segments") or []))
    except Exception as e:                                   # noqa: BLE001
        print(f"    (chép ngược hỏng: {type(e).__name__}: {e})")
        return ""


def _tu(s: str) -> list[str]:
    from app.ai.recap import _word_tokens
    return [w.lower() for w in _word_tokens(s or "")]


def wer(goc: str, nghe: str) -> float:
    import difflib
    a, b = _tu(goc), _tu(nghe)
    if not a:
        return -1.0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return 100.0 * (1.0 - sum(bl.size for bl in sm.get_matching_blocks()) / len(a))


def main():
    cau, vi, en = lay_corpus()
    voice, lang = MAY["edge"]
    texts = vi
    SAN.mkdir(parents=True, exist_ok=True)
    KQ.mkdir(parents=True, exist_ok=True)

    # ── đọc TỪNG CÂU một lượt (đúng hành vi hiện tại) — CHỈ MỘT LẦN, mọi
    #    mức xén dùng CHUNG bộ file thô => GHÉP CẶP tuyệt đối, 0 nhiễu TTS.
    import asyncio
    from app.core import dubbing
    tho = SAN / "tho"
    tho.mkdir(exist_ok=True)
    paths = [str(tho / f"c{i:03d}.mp3") for i in range(len(texts))]
    if not all(Path(p).exists() for p in paths):
        print(f"đọc {len(texts)} câu bằng {voice} ...")
        asyncio.run(dubbing._synth_all_words(texts, voice, paths, lang=lang))

    print("=" * 100)
    print("BẢNG G — XÉN IM Ở BIÊN: 3 MỨC (cùng MỘT bộ file thô -> ghép cặp)")
    print("=" * 100)
    le = [tg.do_le_im(p) for p in paths]
    print(f"lề im TRƯỚC khi xén, {len(paths)} câu: "
          f"ĐẦU TB {1000*statistics.mean(x[0] for x in le):.0f} ms "
          f"(min {1000*min(x[0] for x in le):.0f} · "
          f"max {1000*max(x[0] for x in le):.0f}) · "
          f"ĐUÔI TB {1000*statistics.mean(x[1] for x in le):.0f} ms "
          f"(min {1000*min(x[1] for x in le):.0f} · "
          f"max {1000*max(x[1] for x in le):.0f})")
    print(f"=> MỘT MỐI NỐI (đuôi câu trước + đầu câu sau) = "
          f"{1000*(statistics.mean(x[1] for x in le) + statistics.mean(x[0] for x in le)):.0f} ms\n")

    goc_txt = " ".join(texts)
    ra = {}
    print(f"{'mức':<14} {'giữ đ/c':>10} {'dài':>7} {'im':>7} {'%im':>7} "
          f"{'#im':>4} {'dài nhất':>9} {'nhấn nhá':>9} {'WER':>7}")
    print("-" * 100)
    for ten, gd, gc in MUC:
        tm = SAN / ten
        tm.mkdir(exist_ok=True)
        outs = []
        for i, p in enumerate(paths):
            d = tm / f"x{i:03d}.wav"
            xen(Path(p), d, gd, gc)
            outs.append(str(d))
        noi = SAN / f"{ten}.wav"
        _noi_thang(outs, noi)
        tong, kh = khoang_im(noi)
        im = sum(b - a for a, b in kh)
        nn_v = statistics.pstdev(NN.f0_nua_cung(noi)) if tong else 0.0
        nghe = chep_nguoc(noi, lang)
        w = wer(goc_txt, nghe) if nghe else -1.0
        ra[ten] = dict(dai=round(tong, 2), im=round(im, 2),
                       pc=round(100 * im / tong, 2) if tong else 0,
                       so_im=len(kh),
                       dai_nhat=round(max((b - a for a, b in kh), default=0), 2),
                       nhan_nha=round(nn_v, 2), wer=round(w, 2),
                       wav=str(noi))
        r = ra[ten]
        gg = "—" if gd is None else f"{gd:.2f}/{gc:.2f}"
        print(f"{ten:<14} {gg:>10} {r['dai']:>7.2f} {r['im']:>7.2f} "
              f"{r['pc']:>6.2f}% {r['so_im']:>4} {r['dai_nhat']:>9.2f} "
              f"{r['nhan_nha']:>9.2f} {r['wer']:>6.2f}%")
        (KQ / "G_xen_bien.json").write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nCHỐT CHỐNG-ĐẠT-OAN: M0 phải có %im CAO (nếu M0 đã thấp thì bộ file "
          "này không có lề để xén -> mọi dòng dưới vô nghĩa).")
    return ra


if __name__ == "__main__":
    main()
