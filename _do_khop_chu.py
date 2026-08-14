# -*- coding: utf-8 -*-
"""BẢNG TỪNG CÂU — mốc CHỮ (phụ đề cháy sẵn) so mốc TIẾNG THẬT của giọng mới.

Chạy ĐÚNG các hàm của đường thay tiếng, ĐÚNG thứ tự `thay_giong_video`, nhưng
GIỮ LẠI mọi thứ ở giữa để dựng được bảng từng câu — thứ `thay_giong_video`
không trả ra (`kq` chỉ có số tóm tắt).

CÁI MỚI SO VỚI MỌI THƯỚC CŨ: `khop_thoi_gian` ghi `lech_dau_ms = 0` bằng hằng
số (`lech_dau.append(0.0)` — "đặt ĐÚNG mốc gốc"). Đó là mốc ĐẶT FILE. File
`khop_*.wav` vẫn còn lề im đầu, và quan trọng hơn: câu 12 giây mà tiếng chỉ
4 giây thì 8 giây còn lại KHÔNG CÓ TIẾNG trong khi chữ cháy sẵn vẫn chạy.
Ở đây đo mốc PHÁT RA TIẾNG THẬT bằng `silencedetect` trên chính file đã khớp.

CHẠY:
    python _do_khop_chu.py --video "<video nguồn>" --lam D:\\work\\tg1 \\
        --sang en --ten v1 [--stem <vocals đã tách sẵn>]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import thay_giong as TG      # noqa: E402


def _le_dau(w: str) -> float:
    """Lề im ở ĐẦU file (giây) — `silencedetect` thật trên chính file đã ghi."""
    try:
        dau, _cuoi, _tong = TG.do_le_im(w, nguong_db=-40.0)
        return float(dau)
    except Exception:                                           # noqa: BLE001
        return 0.0


def chay(video: str, lam: Path, sang: str, voice: str, stem: str = "") -> dict:
    lam.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    goc_wav = lam / "goc.wav"
    if not goc_wav.exists():
        TG.tach_wav(video, goc_wav)
    tong = TG.probe_duration(goc_wav)

    # --- bước 1: tách giọng (dùng lại stem đã tách nếu có -> Demucs rất đắt)
    if stem and Path(stem).exists():
        giong, nhac = stem, str(Path(stem).parent / "lop_nhac.wav")
        t = {"giong": giong, "nhac": nhac, "cach": "demucs (dùng lại)"}
    else:
        t = TG.tach_giong(goc_wav, lam / "tach", cach="demucs")

    # --- bước 2: chép lời
    d = TG.chep_loi(goc_wav, t.get("giong") or "")
    cau = TG.cau_tu_transcript(d)
    (lam / "chep.json").write_text(json.dumps(d, ensure_ascii=False),
                                   encoding="utf-8")

    # --- bước 3: dịch
    goc_ma = (d.get("language") or "")[:2].lower()
    dd = TG.dich_hau_kiem(cau, sang, goc_ma)

    # --- bước 4/4b/4c: đọc + rút gọn + đọc nhanh
    tts = TG.doc_ban_dich(dd["ban_dich"], lam / "tts", voice, sang)
    rg = TG.rut_gon_vua_khung(cau, dd["ban_dich"], tts, tong, lam / "rutgon",
                              sang, tts["voice"])
    dn = TG.doc_nhanh_vua_khung(cau, rg["texts"], rg["files"], rg["ok"], tong,
                                lam / "docnhanh", sang, tts["voice"])

    # --- bước 5: khớp thời gian
    kh = TG.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop")

    # ---------------- BẢNG TỪNG CÂU ----------------
    dat = {round(a, 3): w for a, w in kh["manh"]}
    bang = []
    for i, c in enumerate(cau):
        a, b = float(c["start"]), float(c["end"])
        w = dat.get(round(a, 3))
        if w is None:
            bang.append({"i": i, "chu_bat_dau": round(a, 3),
                         "chu_ket_thuc": round(b, 3), "khung_s": round(b - a, 3),
                         "co_tieng": False, "lech_dau_ms": None,
                         "tieng_s": 0.0, "im_duoi_ms": round((b - a) * 1000, 1),
                         "text": (c.get("text") or "")[:60]})
            continue
        d_fin = TG.probe_duration(w)
        le = _le_dau(w)
        bang.append({
            "i": i, "chu_bat_dau": round(a, 3), "chu_ket_thuc": round(b, 3),
            "khung_s": round(b - a, 3), "co_tieng": True,
            # LỆCH ĐẦU THẬT = lề im còn lại trong file đã khớp
            "lech_dau_ms": round(le * 1000.0, 1),
            "tieng_bat_dau": round(a + le, 3),
            "tieng_s": round(d_fin, 3),
            "tieng_ket_thuc": round(a + d_fin, 3),
            # IM CUỐI KHUNG = khoảng chữ còn chạy mà đã hết tiếng
            "im_duoi_ms": round(max(0.0, b - (a + d_fin)) * 1000.0, 1),
            "text": (c.get("text") or "")[:60],
        })

    co = [r for r in bang if r["co_tieng"]]
    ld = np.array([r["lech_dau_ms"] for r in co], float) if co else np.zeros(0)
    im = np.array([r["im_duoi_ms"] for r in bang], float) if bang else np.zeros(0)
    # LỖ TRONG BẢN CHÉP LỜI — chữ chạy mà KHÔNG có câu nào (nguồn "nói muộn")
    lo = []
    for i in range(len(cau) - 1):
        g = float(cau[i + 1]["start"]) - float(cau[i]["end"])
        if g >= 1.0:
            lo.append({"tu": round(float(cau[i]["end"]), 2),
                       "den": round(float(cau[i + 1]["start"]), 2),
                       "dai_s": round(g, 2)})

    kq = {
        "video": video, "ten": lam.name, "sang": sang,
        "voice": tts["voice"], "do_dai_s": round(tong, 2),
        "so_cau": len(cau), "so_cau_co_tieng": len(co),
        "chep": {"ngon_ngu": d.get("language"),
                 "so_seg": len(d.get("segments") or []),
                 "so_tu": len(d.get("words") or [])},
        "lech_dau_ms": {
            "tb": round(float(ld.mean()), 1) if len(ld) else 0.0,
            "max": round(float(ld.max()), 1) if len(ld) else 0.0,
            "vuot_150": int((ld > 150).sum()) if len(ld) else 0},
        "im_duoi_khung_ms": {
            "tb": round(float(im.mean()), 1) if len(im) else 0.0,
            "max": round(float(im.max()), 1) if len(im) else 0.0,
            "tong_giay": round(float(im.sum()) / 1000.0, 2),
            "so_cau_vuot_1s": int((im > 1000).sum()) if len(im) else 0},
        "lo_chep_loi": lo,
        "lo_tong_giay": round(sum(x["dai_s"] for x in lo), 2),
        "khop": {k: v for k, v in kh.items()
                 if k not in ("manh", "tempo_cau", "chong_cau_ms")},
        "bang": bang,
        "giay_tong": round(time.time() - t0, 1),
    }
    return kq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--lam", required=True)
    ap.add_argument("--sang", default="en")
    ap.add_argument("--voice", default="")
    ap.add_argument("--stem", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    kq = chay(a.video, Path(a.lam), a.sang, a.voice, a.stem)
    out = a.json or str(Path(a.lam) / "_bang.json")
    Path(out).write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(json.dumps({k: v for k, v in kq.items() if k != "bang"},
                     ensure_ascii=False, indent=1), flush=True)
    print("\n  i |  chữ từ |  khung |  tiếng | lệch đầu | im dưới chữ", flush=True)
    for r in kq["bang"]:
        print(f"{r['i']:3d} | {r['chu_bat_dau']:7.2f} | {r['khung_s']:6.2f} | "
              f"{r['tieng_s']:6.2f} | "
              f"{(str(r['lech_dau_ms']) + ' ms') if r['lech_dau_ms'] is not None else '  KHÔNG NÓI':>9} | "
              f"{r['im_duoi_ms']:8.0f} ms", flush=True)
    print(f"\n-> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
