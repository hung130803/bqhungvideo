# -*- coding: utf-8 -*-
"""GIÓNG HÀNG CƯỠNG BỨC vs GROQ CHÉP NGƯỢC vs WordBoundary — 4 THỨ TIẾNG.

═══════════════════════════════════════════════════════════════════════════
CÂU HỎI
═══════════════════════════════════════════════════════════════════════════
Với máy đọc **KHÔNG tự trả mốc** (Piper · OmniVoice · mọi bộ trên GitHub),
app đang lấy mốc bằng **Groq chép ngược** — đo được rung **59,1 ms** và
**42% chữ hiện muộn** (Piper). Câu hỏi: **gióng hàng cưỡng bức** (đã biết
chữ, chỉ đi tìm chỗ) có tốt hơn không, và tốt hơn ở CẢ 4 thứ tiếng không?

═══════════════════════════════════════════════════════════════════════════
BA KHUNG ĐO — CỐ Ý KHÔNG DÙNG MỘT THƯỚC DUY NHẤT
═══════════════════════════════════════════════════════════════════════════
Mọi arm chạy trên **CÙNG file tiếng** (edge-tts sinh ra), nên khác biệt là
của PHÉP LẤY MỐC chứ không của máy đọc.

  KHUNG 1 — thước = **Groq chép ngược**. Đây là khung của mọi con số đã công
    bố (`_do_piper_moc_that.py`), giữ lại để **so được với số cũ**.
  KHUNG 2 — thước = **WordBoundary** (mốc THẬT của chính máy đọc). Đây là
    khung TRẢ LỜI CÂU HỎI: cả Groq lẫn gióng hàng đều là cách SUY RA, đem
    cả hai so với sự thật của máy đọc thì mới biết cách nào gần hơn.
    **KHÔNG dùng Groq làm thước cho gióng hàng** — Groq whisper là một mô
    hình NGÔN NGỮ, nó chữa hộ máy đọc; lấy nó chấm chính đối thủ của nó là
    tự phát chứng nhận.
  KHUNG 3 — thước = **`silencedetect`**, ĐỘC LẬP HOÀN TOÀN (không Groq,
    không model, chỉ đo năng lượng). Chỉ trả lời được MỘT câu — "chữ đầu
    tiên có rơi đúng lúc bắt đầu có tiếng không" — nhưng đó đúng là câu mà
    hai khung trên không tự trả lời được, vì cả hai đều có thể lệch HỆ THỐNG
    cùng chiều mà không ai biết. Cổng 67 đã chốt luật này: *lệch HỆ THỐNG đo
    bằng Groq KHÔNG được coi là thuộc tính của máy đọc cho tới khi có thước
    thứ ba*.

**TÁCH LỆCH HỆ THỐNG KHỎI RUNG — BẮT BUỘC.** Số thô là SỐ LỪA khi hai arm
lệch hệ thống ngược dấu (đã sập 3 lần: Piper 65,1 vs edge 60,4 nhìn ngang
nhau, tách ra là 59,1 vs 38,6). Lệch HỆ THỐNG trừ được bằng MỘT hằng số;
RUNG thì không — rung mới là chất lượng thật.

═══════════════════════════════════════════════════════════════════════════
SO THEO **VỊ TRÍ KÝ TỰ**, KHÔNG SO THEO TOKEN — ĐO RA MỚI BIẾT
═══════════════════════════════════════════════════════════════════════════
edge-tts trả `WordBoundary` theo **TỪ NGÔN NGỮ** còn `dubbing._tach_tu` trả
**TỪNG KÝ TỰ** với tiếng Trung/Nhật. Đo thật:
  · zh `主要讲述落魄拳手…` -> WB **14 mốc** (`主要`·`讲述`·`落魄`…) ·
    `_tach_tu` **28 token** (`主`·`要`·`讲`·`述`…)
  · ja `その瞬間、誰も…`   -> WB **14 mốc** (`その`·`瞬間`·`誰`…) ·
    `_tach_tu` **24 token**
Ghép hai danh sách đó theo THỨ TỰ TOKEN là lệch ngay từ token thứ hai và mọi
con số sau đó vô nghĩa. Nên mỗi mốc được quy về **vị trí ký tự** của chữ đầu
tiên trong nó, rồi chỉ so ở vị trí mà **CẢ HAI arm cùng bắt đầu một mốc**.
Với arm Groq (chép ra chữ KHÁC) thì ánh xạ vị trí bằng `SequenceMatcher`
trên CHUỖI KÝ TỰ. Cách này đúng cho cả 4 thứ tiếng, không cần luật riêng.

DẤU: **DƯƠNG = mốc MUỘN hơn thước** (chữ hiện sau khi đã nói).

  .venv\\Scripts\\python -u _do_giong_hang.py
  BQ_SO_CAU=6 BQ_NN=vi,en .venv\\Scripts\\python -u _do_giong_hang.py
  BQ_TOC_DO=1 .venv\\Scripts\\python -u _do_giong_hang.py   (chỉ đo tốc độ)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

SO_CAU = int(os.environ.get("BQ_SO_CAU", "12"))
NN_LIST = [x for x in os.environ.get("BQ_NN", "vi,en,zh,ja").split(",") if x]
RA = REPO / os.environ.get("BQ_RA", "_do_giong_hang.json")
CHI_TOC_DO = os.environ.get("BQ_TOC_DO") == "1"
SAN = Path(os.environ.get("TEMP", "/tmp")) / f"bq_gh_do_{os.getpid()}"

GIONG = {
    "vi": "vi-VN-NamMinhNeural",
    "en": "en-US-AndrewNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
}
TEN_NN = {"vi": "Việt", "en": "Anh", "zh": "Trung", "ja": "Nhật"}


# ==========================================================================
# CORPUS — LỜI THẬT TRÊN MÁY, KHÔNG BỊA CÂU MẪU
# ==========================================================================
def nap_cau(nn: str) -> list[str]:
    """Câu THẬT lấy từ chính các bản chép lời đang có trong repo.

    Câu mẫu ngắn/sạch làm phép đo đẹp giả tạo — dùng lời thật của video anh
    Hùng đang chạy.
    """
    if nn == "zh":
        d = json.loads((REPO / "_do_dich_cache.json").read_text(encoding="utf-8"))
        cau = [str(c.get("text") or "").strip() for c in (d.get("cau") or [])]
        cau = [c for c in cau if len(c) >= 8]
        return sorted(set(cau), key=lambda t: -len(t))[:SO_CAU]

    ten = {"en": "English", "ja": "Japanese", "vi": "Vietnamese"}[nn]
    d = json.loads((REPO / "_do_hook_cache.json").read_text(encoding="utf-8"))
    got: set[str] = set()
    for v in d:
        if not isinstance(v, dict) or v.get("lang") != ten:
            continue
        for s in (v.get("segments") or []):
            t = str((s or {}).get("text") or "").strip()
            if t:
                got.add(t)
    if nn == "ja":                       # Nhật không có dấu cách -> đếm ký tự
        ds = [t for t in got if len(t) >= 10]
    else:
        ds = [t for t in got if len(t.split()) >= 6]
    return sorted(ds, key=lambda t: -len(t))[:SO_CAU]


# ==========================================================================
# QUY MỐC VỀ VỊ TRÍ KÝ TỰ
# ==========================================================================
_DAU = re.compile(r"[\s.,!?;:\"'“”‘’…()\-–—\[\]{}、。，！？；：「」『』（）]+")


def _chuan(w: str) -> str:
    return _DAU.sub("", str(w or "")).lower()


def theo_vi_tri(moc: list) -> tuple[str, dict]:
    """[[start,end,từ],…] -> (chuỗi ký tự đã chuẩn hoá, {vị_trí_đầu: start}).

    Quy mọi mốc về vị trí KÝ TỰ vì WordBoundary và `_tach_tu` chia từ khác
    nhau ở tiếng Trung/Nhật (xem docstring đầu file).
    """
    s: list[str] = []
    d: dict[int, float] = {}
    n = 0
    for m in moc or []:
        try:
            a, w = float(m[0]), _chuan(m[2])
        except Exception:                                # noqa: BLE001
            continue
        if not w:
            continue
        d.setdefault(n, a)
        s.append(w)
        n += len(w)
    return "".join(s), d


def so_hai_arm(thuoc: list, arm: list) -> list[float]:
    """Lệch (ms) của `arm` so với `thuoc`, DƯƠNG = arm MUỘN hơn.

    Chỉ so ở vị trí ký tự mà CẢ HAI cùng bắt đầu một mốc.
    """
    s_t, d_t = theo_vi_tri(thuoc)
    s_a, d_a = theo_vi_tri(arm)
    if not s_t or not s_a:
        return []
    anh_xa: dict[int, int] = {}
    for i, j, n in SequenceMatcher(None, s_t, s_a,
                                   autojunk=False).get_matching_blocks():
        for k in range(n):
            anh_xa[i + k] = j + k
    ra = []
    for off, t in d_t.items():
        oa = anh_xa.get(off)
        if oa is None:
            continue
        ta = d_a.get(oa)
        if ta is not None:
            ra.append((ta - t) * 1000.0)
    return ra


def thong_ke(lech: list[float]) -> dict:
    """TÁCH LỆCH HỆ THỐNG KHỎI RUNG — xem docstring đầu file."""
    if not lech:
        return {"n": 0}
    ab = sorted(abs(x) for x in lech)
    goc = statistics.median(lech)
    rung = sorted(abs(x - goc) for x in lech)
    return {
        "n": len(lech),
        "tho_tb": round(sum(ab) / len(ab), 1),
        "tho_p90": round(ab[min(len(ab) - 1, int(len(ab) * 0.9))], 1),
        "he_thong": round(goc, 1),
        "rung_tb": round(sum(rung) / len(rung), 1),
        "rung_trung_vi": round(statistics.median(rung), 1),
        "rung_p90": round(rung[min(len(rung) - 1, int(len(rung) * 0.9))], 1),
        # muộn THÔ = cái người xem thấy nếu không chỉnh gì
        "muon_tho": round(100.0 * sum(1 for x in lech if x > 50) / len(lech), 1),
        # muộn SAU KHI trừ lệch hệ thống = phần KHÔNG chữa được bằng hằng số
        "muon_sau": round(100.0 * sum(1 for x in lech if x - goc > 50)
                          / len(lech), 1),
        "trong_50_sau": round(100.0 * sum(1 for x in lech
                                          if abs(x - goc) <= 50) / len(lech), 1),
    }


# ==========================================================================
# THƯỚC THỨ BA — ĐỘC LẬP, KHÔNG GROQ KHÔNG MODEL
# ==========================================================================
def am_bat_dau(wav: str) -> float | None:
    """Giây file THẬT SỰ bắt đầu có tiếng (`silencedetect`).

    Chỉ đo năng lượng nên nó không biết gì về chữ nghĩa -> không thể thiên vị
    arm nào. Đây là thứ duy nhất trong cả phép đo không phụ thuộc mô hình.
    """
    from config import settings
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-v", "info", "-i", wav, "-af",
         "silencedetect=noise=-45dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180)
    if r.returncode != 0:
        return None
    dau_im, ket = None, None
    for d in (r.stderr or "").splitlines():
        if "silence_start:" in d:
            try:
                v = float(d.split("silence_start:")[1].split("|")[0])
            except Exception:                            # noqa: BLE001
                continue
            if dau_im is None:
                dau_im = v
        elif "silence_end:" in d and ket is None:
            try:
                ket = float(d.split("silence_end:")[1].split("|")[0])
            except Exception:                            # noqa: BLE001
                pass
    if dau_im is not None and dau_im <= 0.02 and ket is not None:
        return ket                       # file mở đầu bằng im lặng
    return 0.0                           # có tiếng ngay từ giây 0


# ==========================================================================
# CHẠY MỘT NGÔN NGỮ
# ==========================================================================
def chay_mot(nn: str) -> dict:
    from app.core import dubbing, giong_hang as gh, thay_giong as tg

    texts = nap_cau(nn)
    if not texts:
        return {"loi": "không lấy được câu"}
    san = SAN / nn
    san.mkdir(parents=True, exist_ok=True)
    wavs = [str(san / f"c{i:03d}.mp3") for i in range(len(texts))]

    # 1) edge-tts sinh tiếng + mốc THẬT (WordBoundary) — đi ĐÚNG cửa app
    ok, wb = asyncio.run(dubbing._synth_all_words(
        texts, GIONG[nn], wavs, lang=nn))
    dung = [i for i in range(len(texts)) if ok[i] and wb[i]
            and Path(wavs[i]).is_file()]
    if not dung:
        return {"loi": "edge-tts không đọc được câu nào"}

    # 2) GIÓNG HÀNG (cửa mới)
    t0 = time.time()
    ghm = gh.giong_hang_loat([wavs[i] for i in dung],
                             [texts[i] for i in dung], lang=nn)
    giay_gh = round(time.time() - t0, 2)

    # 3) GROQ chép ngược (đường app ĐANG dùng cho Piper/ElevenLabs)
    grq: list[list] = []
    t0 = time.time()
    for i in dung:
        try:
            d = tg.chep_loi(wavs[i])
            ws = d.get("words") or []
            m = []
            for x in ws:
                if isinstance(x, dict):
                    m.append([float(x.get("start", 0)), float(x.get("end", 0)),
                              str(x.get("word") or x.get("text") or "")])
                else:
                    m.append([float(x[0]), float(x[1]), str(x[2])])
            grq.append(m)
        except Exception as e:                           # noqa: BLE001
            print(f"    Groq lỗi câu {i}: {type(e).__name__}: {e}")
            grq.append([])
    giay_groq = round(time.time() - t0, 2)

    # 4) ba khung
    k1_wb, k1_gh = [], []            # thước = Groq
    k2_grq, k2_gh = [], []           # thước = WordBoundary
    dau = {"WB": [], "GROQ": [], "GH": []}
    tong_giay = 0.0
    for k, i in enumerate(dung):
        w, g, q = wb[i], (ghm[k] if k < len(ghm) else []), grq[k]
        if q:
            k1_wb += so_hai_arm(q, w)
            if g:
                k1_gh += so_hai_arm(q, g)
        if g:
            k2_gh += so_hai_arm(w, g)
        if q:
            k2_grq += so_hai_arm(w, q)
        # khung 3 — chữ ĐẦU so với lúc thật sự có tiếng
        t_am = am_bat_dau(wavs[i])
        if t_am is not None:
            for ten, m in (("WB", w), ("GROQ", q), ("GH", g)):
                if m:
                    dau[ten].append((float(m[0][0]) - t_am) * 1000.0)
        try:
            tong_giay += float(subprocess.run(
                [__import__("config").settings.FFPROBE_PATH, "-v", "error",
                 "-show_entries", "format=duration", "-of",
                 "default=nw=1:nk=1", wavs[i]],
                capture_output=True, text=True, timeout=60).stdout.strip() or 0)
        except Exception:                                # noqa: BLE001
            pass

    return {
        "so_cau": len(dung), "so_cau_gui": len(texts),
        "gh_co_moc": sum(1 for m in ghm if m),
        "groq_co_moc": sum(1 for m in grq if m),
        "giay_tieng": round(tong_giay, 1),
        "giay_gh": giay_gh, "giay_groq": giay_groq,
        "K1_WB": thong_ke(k1_wb), "K1_GH": thong_ke(k1_gh),
        "K2_GROQ": thong_ke(k2_grq), "K2_GH": thong_ke(k2_gh),
        "K3": {k: (round(statistics.median(v), 1) if v else None)
               for k, v in dau.items()},
        "K3_n": {k: len(v) for k, v in dau.items()},
    }


def in_bang(kq: dict) -> None:
    print()
    print("=" * 78)
    print("KHUNG 2 (thước = WordBoundary, mốc THẬT của máy đọc) — KHUNG TRẢ LỜI")
    print("=" * 78)
    print(f"  {'tiếng':<7} {'đường':<12} {'n':>5} {'RUNG tb':>9} {'rung 90%':>9}"
          f" {'hệ thống':>10} {'muộn thô':>9} {'muộn sau':>9}")
    for nn in NN_LIST:
        d = kq.get(nn) or {}
        if d.get("loi"):
            print(f"  {TEN_NN.get(nn, nn):<7} LỖI: {d['loi']}")
            continue
        for ten, khoa in (("Groq ngược", "K2_GROQ"), ("GIÓNG HÀNG", "K2_GH")):
            t = d.get(khoa) or {}
            if not t.get("n"):
                print(f"  {TEN_NN.get(nn, nn):<7} {ten:<12} — không đo được")
                continue
            print(f"  {TEN_NN.get(nn, nn):<7} {ten:<12} {t['n']:>5} "
                  f"{t['rung_tb']:>9.1f} {t['rung_p90']:>9.1f} "
                  f"{t['he_thong']:>+10.1f} {t['muon_tho']:>8.1f}% "
                  f"{t['muon_sau']:>8.1f}%")
        print()

    print("=" * 78)
    print("KHUNG 1 (thước = Groq chép ngược) — để SO ĐƯỢC VỚI SỐ CŨ đã công bố")
    print("=" * 78)
    print(f"  {'tiếng':<7} {'đường':<12} {'n':>5} {'RUNG tb':>9} {'rung 90%':>9}"
          f" {'hệ thống':>10} {'muộn thô':>9}")
    for nn in NN_LIST:
        d = kq.get(nn) or {}
        if d.get("loi"):
            continue
        for ten, khoa in (("edge WB", "K1_WB"), ("GIÓNG HÀNG", "K1_GH")):
            t = d.get(khoa) or {}
            if not t.get("n"):
                continue
            print(f"  {TEN_NN.get(nn, nn):<7} {ten:<12} {t['n']:>5} "
                  f"{t['rung_tb']:>9.1f} {t['rung_p90']:>9.1f} "
                  f"{t['he_thong']:>+10.1f} {t['muon_tho']:>8.1f}%")
        print()

    print("=" * 78)
    print("KHUNG 3 — THƯỚC ĐỘC LẬP `silencedetect`: chữ ĐẦU lệch lúc bắt đầu có")
    print("tiếng bao nhiêu (trung vị ms · DƯƠNG = mốc MUỘN hơn tiếng thật)")
    print("=" * 78)
    print(f"  {'tiếng':<7} {'WordBoundary':>14} {'Groq ngược':>14} "
          f"{'GIÓNG HÀNG':>14}")
    for nn in NN_LIST:
        d = (kq.get(nn) or {}).get("K3")
        if not d:
            continue
        f = lambda v: (f"{v:+.1f}" if v is not None else "—")   # noqa: E731
        print(f"  {TEN_NN.get(nn, nn):<7} {f(d['WB']):>14} "
              f"{f(d['GROQ']):>14} {f(d['GH']):>14}")


def main() -> int:
    print("=" * 78)
    print("GIÓNG HÀNG CƯỠNG BỨC vs GROQ CHÉP NGƯỢC vs WordBoundary")
    print(f"{SO_CAU} câu/tiếng · {', '.join(TEN_NN.get(x, x) for x in NN_LIST)}")
    print("Mọi arm chạy trên CÙNG file tiếng (edge-tts) -> khác biệt là của")
    print("PHÉP LẤY MỐC, không phải của máy đọc.")
    print("=" * 78)
    from app.core import giong_hang as gh
    tt = gh.tinh_trang_giong_hang()
    print(f"bộ gióng hàng: {'ĐỦ' if tt['co'] else 'THIẾU ' + str(tt['thieu'])}"
          f"  · torch ở {tt['lib_torch']}")
    if not tt["co"]:
        return 2

    kq = {}
    for nn in NN_LIST:
        print()
        print("-" * 78)
        print(f"### {TEN_NN.get(nn, nn)} ({nn}) · giọng {GIONG[nn]}")
        print("-" * 78)
        try:
            kq[nn] = chay_mot(nn)
        except Exception as e:                           # noqa: BLE001
            import traceback
            traceback.print_exc()
            kq[nn] = {"loi": f"{type(e).__name__}: {e}"}
        d = kq[nn]
        if d.get("loi"):
            print(f"  LỖI: {d['loi']}")
        else:
            print(f"  {d['so_cau']}/{d['so_cau_gui']} câu · "
                  f"{d['giay_tieng']}s tiếng · gióng hàng {d['gh_co_moc']} câu "
                  f"có mốc ({d['giay_gh']}s) · Groq {d['groq_co_moc']} câu "
                  f"({d['giay_groq']}s)")
        RA.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    in_bang(kq)
    RA.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(SAN, ignore_errors=True)
