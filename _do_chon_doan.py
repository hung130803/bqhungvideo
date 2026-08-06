# -*- coding: utf-8 -*-
"""ĐO CHẤT LƯỢNG CHỌN ĐOẠN của AI — chạy trên VIDEO THẬT, so trước/sau.

    python _do_chon_doan.py --moc      # chạy bản HIỆN TẠI, lưu làm MỐC
    python _do_chon_doan.py --so       # chạy bản MỚI rồi in bảng so với mốc

Vì sao cần: "hay/nhạt" là cảm nhận. Muốn biết sửa có khá lên thật thì phải có
mốc: CÙNG video, CÙNG bản chép lời (cache lại, không chép lại để khỏi lệch),
chỉ đổi cách CHỌN. In ra đoạn được chọn + câu thoại + điểm + lý do để anh Hùng
đọc 10 dòng là biết.

Chép lời cache ở `_do_chon_cache/` (dùng lại giữa các lượt -> so công bằng).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CACHE = REPO / "_do_chon_cache"
CACHE.mkdir(exist_ok=True)
FF = str(REPO / "bin" / "ffmpeg.exe")
FP = str(REPO / "bin" / "ffprobe.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0

#: video THẬT đúng thể loại kênh anh Hùng (drama/xung đột/bodycam/wrestling)
VIDEO = [
    r"C:\Users\Admin\Downloads\Video\16 year old girl defiant to her mom & says she doesn’t love her #prisondr #viral.mp4",
    r"C:\Users\Admin\Downloads\Video\Big Body OG Pred Gets Busted!.mp4",
    r"C:\Users\Admin\Downloads\Video\Bad Way to Start off Monday!! Ram 3500 Winch Out!.mp4",
]
CFG = {"min_len": 60.0, "max_len": 90.0, "count": 3}


def _dur(p: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True,
                       creationflags=_NO_WIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def chep_loi(p: str) -> dict:
    """Chép lời qua Groq, CACHE theo tên file (lượt sau dùng lại -> so công bằng)."""
    key = CACHE / (str(abs(hash(p)))[:12] + ".json")
    if key.exists():
        return json.loads(key.read_text(encoding="utf-8"))
    wav = CACHE / "tmp.wav"
    subprocess.run([FF, "-y", "-v", "error", "-i", p, "-vn", "-ac", "1",
                    "-ar", "16000", str(wav)], capture_output=True,
                   creationflags=_NO_WIN)
    from app.core import transcribe as TR
    t0 = time.time()
    tr = TR._transcribe_groq(str(wav), None, None)
    print(f"    chép lời {time.time()-t0:.0f}s · {len(tr.get('words') or [])} từ")
    key.write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    wav.unlink(missing_ok=True)
    return tr


def cau_thoai(tr: dict, a: float, b: float, n: int = 90) -> str:
    """Câu thoại đầu tiên trong khoảng [a,b] — để anh Hùng đọc biết đoạn gì."""
    for s in tr.get("segments") or []:
        if float(s.get("end", 0)) >= a and float(s.get("start", 0)) <= b:
            t = " ".join(str(s.get("text", "")).split())
            if len(t) > 8:
                return t[:n]
    return "(không có thoại)"


def chay(ten_ban: str) -> dict:
    from app.modules import m1_highlight as M
    ra = {}
    for p in VIDEO:
        if not os.path.exists(p):
            print(f"  ✗ thiếu video: {os.path.basename(p)}")
            continue
        nhan = os.path.basename(p)[:44]
        print(f"\n  ▶ {nhan}")
        tr = chep_loi(p)
        dur = _dur(p)
        t0 = time.time()
        khoi = ""
        nl = []
        if os.environ.get("BQ_MOI"):
            from app.ai import chon_doan as CD
            FFM = str(REPO / "bin" / "ffmpeg.exe")
            nl = CD.nang_luong(p, FFM)
            cd = CD.chuyen_dong(p, FFM)
            khoi = (CD.khoi_prompt_nghe(CD.cua_so_cang(nl), dur)
                    + CD.khoi_prompt_hanh_dong(
                        CD.cua_so_dong_khong_loi(cd, tr, dur)))
            print(f"    nghe {len(nl)}s · xem {len(cd)}s · khối prompt {len(khoi)} ký tự")
        out = M._llm_select_clips(tr, dur, None, None, CFG, None, nghe_xem=khoi)
        clips = out[0] if isinstance(out, tuple) else out
        if os.environ.get("BQ_MOI") and clips:
            from app.ai import chon_doan as CD
            from app.ai import llm as _L
            cham = CD.cham_mu(clips, tr, _L.complete_text)
            for i, c in enumerate(clips):
                if i in cham:
                    c["score_tu_cham"] = c.get("score", 0)
                    c["score"] = cham[i]["score"]
                    c["reason"] = cham[i]["vi_sao"]
            clips, bo = CD.loc_intro_outro(clips, dur)
            for _c, ly in bo:
                print(f"    BỎ 1 clip vì {ly}")
            clips, bo2 = CD.san_thich_ung(clips)
            for _c, ly in bo2:
                print(f"    BỎ 1 clip: {ly}")
            if nl:
                for c in clips:
                    hs = CD.hook_theo_tieng(c, nl)
                    if hs:
                        c["hook_seg"] = hs
        dt = time.time() - t0
        ds = []
        for c in clips or []:
            segs = c.get("segments") or []
            a = float(segs[0][0]) if segs else 0.0
            b = float(segs[-1][1]) if segs else 0.0
            ds.append({"a": round(a, 1), "b": round(b, 1),
                       "score": float(c.get("score", 0)),
                       "title": (c.get("title") or "")[:60],
                       "reason": (c.get("reason") or "")[:80],
                       "thoai": cau_thoai(tr, a, b),
                       "n_seg": len(segs)})
        print(f"    {len(ds)} clip · {dt:.0f}s · điểm "
              f"{[d['score'] for d in ds]}")
        for d in ds:
            print(f"      {d['a']:7.1f}-{d['b']:7.1f}s ({d['n_seg']} đoạn) "
                  f"điểm {d['score']:.0f} · {d['thoai'][:70]}")
        ra[nhan] = ds
    return ra


ap = argparse.ArgumentParser()
ap.add_argument("--moc", action="store_true", help="lưu làm MỐC (bản hiện tại)")
ap.add_argument("--so", action="store_true", help="so với mốc đã lưu")
a = ap.parse_args()
print(f"=== ĐO CHỌN ĐOẠN — {len(VIDEO)} video thật, cấu hình {CFG}")
kq = chay("moc" if a.moc else "moi")
f = CACHE / ("moc.json" if a.moc else "moi.json")
f.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\nĐã lưu: {f}")
if a.so and (CACHE / "moc.json").exists():
    moc = json.loads((CACHE / "moc.json").read_text(encoding="utf-8"))
    print("\n═══ BẢNG SO SÁNH ═══")
    for k in kq:
        print(f"\n▶ {k}")
        print("  CŨ :", " | ".join(f"{d['a']:.0f}-{d['b']:.0f}s đ{d['score']:.0f}"
                                   for d in moc.get(k, [])) or "—")
        print("  MỚI:", " | ".join(f"{d['a']:.0f}-{d['b']:.0f}s đ{d['score']:.0f}"
                                   for d in kq[k]) or "—")
