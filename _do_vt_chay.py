# -*- coding: utf-8 -*-
"""NGHI PHẠM SỐ MỘT: `doc_viet_tat` có CHẠY trên đường anh Hùng đi không?

Đường anh Hùng đi (đọc từ `_job_*/job.json` THẬT của app anh ấy):
  * giọng NHÂN BẢN `vnb:` (job.json: `voice=""` + `ref_audio=<mẫu>`)
  * đích dịch **TIẾNG ANH** (`dich_sang="en"`)

Hai câu hỏi, hai phép đo TÁCH BẠCH:
  A. **CÓ GỌI KHÔNG** — bọc `doi_chu`/`sua_loat`/`sua_cho_may_doc`/
     `bat_cho_giong` bằng hàm ĐẾM rồi gọi THẬT `thay_giong.doc_ban_dich`.
     Không đọc mã rồi suy: cửa `sua_loat` nằm TRONG `if dung_vn` của
     `dubbing._synth_all_words`, nên phải đi hết đường mới biết.
  B. **NẾU CHẠY THÌ ĐỔI GÌ** — chạy HÀM THUẦN `doi_chu` trên **CẢ 236 câu
     tiếng Anh THẬT** của anh Hùng, in danh sách trước-sau. Câu hỏi này độc
     lập với A: A trả lời "hôm nay có bắn không", B trả lời "bắn thì hỏng cỡ
     nào" (tức cái giá nếu ai đó bật `BQ_VIET_TAT_VN=1`).

Máy đọc được VÁ thành hàm sinh WAV bằng ffmpeg: phép đo này hỏi về ĐƯỜNG CHỮ,
mà chữ bị đổi (hoặc không) TRƯỚC khi model nhìn thấy nó. Vá máy đọc làm phép
đo TIỀN ĐỊNH + chạy trong vài giây thay vì ~20 phút, và **không đổi câu trả
lời** — mục 0 chốt lại điều đó bằng cách đòi cửa VieNeu phải THẬT SỰ được đi
qua (`_chay_vieneu` bị gọi), nếu không thì mọi số 0 ở dưới là số 0 vì lý do
NGƯỢC HẲN (lùi sang edge-tts).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / "_kq_danhvan" / "vt_chay"
HOP.mkdir(parents=True, exist_ok=True)
RA = REPO / "_kq_vt_chay.json"

import config  # noqa: E402
from app.core import doc_viet_tat  # noqa: E402

FF = str(getattr(config.settings, "FFMPEG_PATH", "ffmpeg"))

# ── SỔ THEO DÕI ──────────────────────────────────────────────────────────
SO = {
    "bat_cho_giong": [],      # [(voice, kết quả)]
    "sua_loat": [],           # [(voice, số câu, số câu bị đổi)]
    "sua_cho_may_doc": [],    # [(voice, có đổi không)]
    "doi_chu": [],            # [(vào, ra, thay)]
    "chay_vieneu": 0,         # cửa VieNeu có được đi qua không
    "doc_loat": 0,
}

_bat_goc = doc_viet_tat.bat_cho_giong
_doi_goc = doc_viet_tat.doi_chu
_loat_goc = doc_viet_tat.sua_loat
_mot_goc = doc_viet_tat.sua_cho_may_doc


def _bat(voice):
    r = _bat_goc(voice)
    SO["bat_cho_giong"].append((str(voice), bool(r)))
    return r


def _doi(text):
    g, thay = _doi_goc(text)
    SO["doi_chu"].append((str(text), g, list(thay)))
    return g, thay


def _loat(texts, voice):
    ra, thay_ds = _loat_goc(texts, voice)
    SO["sua_loat"].append((str(voice), len(list(texts or [])),
                           sum(1 for t in thay_ds if t)))
    return ra, thay_ds


def _mot(text, voice):
    g, thay = _mot_goc(text, voice)
    SO["sua_cho_may_doc"].append((str(voice), bool(thay)))
    return g, thay


doc_viet_tat.bat_cho_giong = _bat
doc_viet_tat.doi_chu = _doi
doc_viet_tat.sua_loat = _loat
doc_viet_tat.sua_cho_may_doc = _mot


def _wav_gia(path: str, giay: float = 1.4) -> bool:
    """Sinh WAV có tiếng bằng ffmpeg. `duration=` nằm TRONG biểu thức lavfi —
    **cố ý không dùng `-t`** (`-t` là tuỳ chọn ĐẦU VÀO; đặt sai đã từng làm
    anullsrc ghi vô hạn và đầy ổ C 420 GB)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency=180:duration={giay:.3f}",
         "-ar", "24000", "-ac", "1", path],
        capture_output=True)
    return r.returncode == 0 and Path(path).exists()


def _va_may_doc():
    """Vá `giong_vieneu.doc_loat` thành hàm sinh WAV + ĐẾM lượt đi qua."""
    from app.core import giong_vieneu as vn

    def _gia(texts, paths, voice="", on_done=None, rate=0, on_msg=None,
             lay_moc=False, **kw):
        SO["doc_loat"] += 1
        ok = []
        for i, (t, p) in enumerate(zip(texts, paths)):
            g = max(0.5, min(9.0, len(str(t)) * 0.055))
            ok.append(_wav_gia(p, g))
            if on_done:
                on_done(i)
        return ok, [[] for _ in texts]

    vn.doc_loat = _gia
    vn.co_vieneu = lambda: True

    from app.core import dubbing as _dub
    _cv_goc = _dub._chay_vieneu

    async def _cv(*a, **k):
        SO["chay_vieneu"] += 1
        return await _cv_goc(*a, **k)

    _dub._chay_vieneu = _cv


def main() -> int:
    cau = json.loads((REPO / "_kq_corpus_hung.json").read_text("utf-8"))
    print(f"Corpus THẬT của anh Hùng: {len(cau)} câu tiếng Anh "
          f"(2 job trong %LOCALAPPDATA%\\BQHungVideo)")

    # ── B. HÀM THUẦN trên CẢ corpus (độc lập chuyện có bật hay không) ────
    doi_ds = []
    for t in cau:
        g, thay = _doi_goc(t)
        if thay:
            doi_ds.append({"truoc": t, "sau": g,
                           "tu": [x[2] for x in thay]})
    tu_dem: dict[str, int] = {}
    for d in doi_ds:
        for tk in d["tu"]:
            tu_dem[tk] = tu_dem.get(tk, 0) + 1
    print(f"\n[B] HÀM THUẦN `doi_chu` trên 236 câu tiếng Anh THẬT:")
    print(f"    câu bị đổi : {len(doi_ds)}/{len(cau)} "
          f"({100.0*len(doi_ds)/max(1,len(cau)):.1f}%)")
    print(f"    token bị đổi: {sum(tu_dem.values())} lượt, "
          f"{len(tu_dem)} từ khác nhau")
    for tk, n in sorted(tu_dem.items(), key=lambda x: -x[1]):
        moi = " ".join(doc_viet_tat.CHU_ANH[c] for c in tk)
        print(f"      {tk!r:8s} x{n:<3d} -> {moi!r}")
    for d in doi_ds[:12]:
        print(f"      TRƯỚC: {d['truoc']}")
        print(f"      SAU  : {d['sau']}")

    # ── A. GỌI THẬT `doc_ban_dich` trên đường `vnb:` + en ────────────────
    SO["doi_chu"].clear()
    _va_may_doc()
    from app.core import thay_giong

    mau = str(HOP / "mau.wav")
    _wav_gia(mau, 7.0)
    voice = "vnb:" + mau
    thu = cau[:12]
    print(f"\n[A] GỌI THẬT `doc_ban_dich(voice={voice[:14]}..., "
          f"dich_sang='en')` trên {len(thu)} câu...")
    kq = thay_giong.doc_ban_dich(thu, HOP / "ra", voice=voice,
                                 dich_sang="en")
    print(f"    ok = {sum(1 for x in kq['ok'] if x)}/{len(thu)} câu")
    print(f"    cửa VieNeu đi qua : _chay_vieneu {SO['chay_vieneu']} lượt · "
          f"doc_loat {SO['doc_loat']} lượt")
    print(f"    bat_cho_giong     : {SO['bat_cho_giong']}")
    print(f"    sua_loat          : {SO['sua_loat']}")
    print(f"    sua_cho_may_doc   : {len(SO['sua_cho_may_doc'])} lượt, "
          f"đổi {sum(1 for _v, c in SO['sua_cho_may_doc'] if c)}")
    print(f"    doi_chu GỌI       : {len(SO['doi_chu'])} lượt")
    n_doi = sum(1 for _t, _g, th in SO["doi_chu"] if th)
    print(f"    doi_chu ĐỔI THẬT  : {n_doi} câu")

    # ── A'. cùng đường, BẬT cờ `BQ_VIET_TAT_VN=1` (đối chứng CÓ RĂNG) ────
    import os
    SO["doi_chu"].clear()
    SO["sua_loat"].clear()
    SO["bat_cho_giong"].clear()
    os.environ["BQ_VIET_TAT_VN"] = "1"
    kq2 = thay_giong.doc_ban_dich(thu, HOP / "ra2", voice=voice,
                                  dich_sang="en")
    n_doi2 = sum(1 for _t, _g, th in SO["doi_chu"] if th)
    print(f"\n[A'] ĐỐI CHỨNG cùng đường, BQ_VIET_TAT_VN=1:")
    print(f"    bat_cho_giong  : {SO['bat_cho_giong'][:3]}")
    print(f"    sua_loat       : {SO['sua_loat']}")
    print(f"    doi_chu ĐỔI    : {n_doi2}/{len(thu)} câu")
    for t, g, th in SO["doi_chu"]:
        if th:
            print(f"      TRƯỚC: {t}")
            print(f"      SAU  : {g}")
    os.environ.pop("BQ_VIET_TAT_VN", None)

    ket = {
        "corpus_cau": len(cau),
        "B_ham_thuan": {
            "cau_bi_doi": len(doi_ds),
            "token_luot": sum(tu_dem.values()),
            "token_ds": tu_dem,
            "vi_du": doi_ds[:20],
        },
        "A_goi_that": {
            "voice": "vnb:", "dich_sang": "en", "so_cau": len(thu),
            "chay_vieneu": SO["chay_vieneu"], "doc_loat": SO["doc_loat"],
            "doi_chu_doi_that": n_doi,
            "ok": sum(1 for x in kq["ok"] if x),
        },
        "A_doi_chung_bat_co": {
            "doi_chu_doi_that": n_doi2,
            "ok": sum(1 for x in kq2["ok"] if x),
        },
    }
    RA.write_text(json.dumps(ket, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nĐÃ GHI {RA.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        import shutil
        from app.core import xoa_an_toan
        try:
            # `an_toan_de_xoa` trả **bool**, KHÔNG phải tuple — bản đầu viết
            # `[0]` và ra `TypeError: 'bool' object is not subscriptable`
            # đúng trong `finally`, tức hộp cát nằm lại mà lời lỗi thì nói về
            # chuyện khác.
            if xoa_an_toan.an_toan_de_xoa(HOP, trong=REPO / "_kq_danhvan"):
                shutil.rmtree(HOP, ignore_errors=True)
        except Exception as e:  # noqa: BLE001
            print("dọn hộp cát lỗi:", e)
