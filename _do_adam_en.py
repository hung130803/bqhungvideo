# -*- coding: utf-8 -*-
"""`vn:Adam` HỎNG THẬT hay CHỈ KÉM HƠN — phép đo cho anh Hùng (19/08/2026).

Anh Hùng nghe rồi nói: *"cái adam bị lỗi hay sao nghe cứ lạ lạ khác lắm, không
như tôi nghĩ"*, và trỏ vào `_NGHE_THU_ANH_HUNG\\adam\\EL_Adam_A.wav` nói *"ít
nhất phải như này mới oke"*. File đó là **giọng Adam THẬT của ElevenLabs**
(sinh ra hôm nay chỉ để chứng minh hai giọng KHÁC NGƯỜI — ECAPA 0,223).

═══════════════════════════════════════════════════════════════════════════
CÂU HỎI PHẢI TÁCH LÀM HAI — GỘP LÀ KẾT LUẬN SAI
═══════════════════════════════════════════════════════════════════════════
  (1) **HỎNG** = lỗi mã/cấu hình của app hoặc của giọng đó -> SỬA được.
  (2) **KÉM** = giới hạn của model -> KHÔNG sửa được bằng mã, chỉ nói thẳng
      trên nhãn và chỉ đường sang giọng tốt hơn.
Dấu hiệu tách hai: nếu `vn:Adam` sai chữ **ngang** 19 giọng VieNeu khác thì
đó là giới hạn CỦA BỘ (kém); nếu nó sai **hơn hẳn** thì mới nghi mã/cấu hình.

═══════════════════════════════════════════════════════════════════════════
KHÔNG NHÂN BẢN TỪ MẪU ElevenLabs — RANH GIỚI CỨNG, KHÔNG PHẢI LỰA CHỌN
═══════════════════════════════════════════════════════════════════════════
File này KHÔNG đọc `EL_Adam_*.wav` làm `ref_audio`, KHÔNG tinh chỉnh, KHÔNG
đề xuất đường đó. Nhân bản một giọng thương mại đang được bán vào app anh Hùng
BÁN RA là chuyện khác hẳn "đo xem giọng có hỏng không". Mẫu ElevenLabs ở đây
chỉ dùng đúng một việc: **để anh Hùng nghe so bằng tai** (việc 4).

═══════════════════════════════════════════════════════════════════════════
ĐI QUA CỬA THẬT, DÙNG LẠI BỘ CHẤM CŨ
═══════════════════════════════════════════════════════════════════════════
Cửa: `dubbing._synth_all` (nó tự rẽ `giong_vieneu.doc_loat`). Corpus, WER, bộ
chấm token, cache TTS đều **dùng lại `_do_vieneu_en.py`** — viết bộ chấm thứ
hai là đẻ ra hai bảng số không so được với nhau. Nhờ dùng chung cache, các arm
`edge_en` (TRẦN) · `NH_en` · `MD_en` · `TL_en` · `NH_vi` đo hôm nay lấy lại
**đúng file tiếng đã đo sáng nay**, không tốn lượt nào.

═══════════════════════════════════════════════════════════════════════════
BỐN THƯỚC, MỖI THƯỚC TRẢ LỜI MỘT CÂU KHÁC NHAU
═══════════════════════════════════════════════════════════════════════════
  1. **Token sai TRONG CÂU** — máy nghe có ngữ cảnh nên nó CHỮA HỘ máy đọc
     (đã đo: trong câu 5% vs đọc rời 24% trên cùng bộ). Đây là cột DỄ DÃI.
  2. **Token sai ĐỌC RỜI** — token một mình, mô hình ngôn ngữ không còn gì
     bám vào. Đây là cột THẬT.
  3. **BỊA CHỮ** — số từ máy nghe chép ra mà bản gốc KHÔNG CÓ (phép CHÈN
     trong gióng hàng Levenshtein), chia cho số từ gốc. WER gộp cả sai/thiếu/
     thêm nên không phân biệt được "đọc sai chữ" với "đọc thêm chữ không có";
     mà hai cái đó khác nhau về bản chất (một là phát âm, một là model tự
     sinh thêm tiếng).
  4. **LỀ IM đầu/cuối** — `thay_giong.do_le_im` (ffmpeg `silencedetect`),
     đúng hàm đường xuất thật dùng. VieNeu đo được ~350 ms; lề dài là bấm
     nghe thử phải ngồi đợi, và là dấu hiệu model sinh thừa.
  Kèm thước PHỤ: **NHÃN NGÔN NGỮ** máy nghe tự nhận (lượt chép KHÔNG ép ngôn
  ngữ) — giọng đọc tiếng Anh mà whisper dán nhãn "Vietnamese" là dấu hiệu
  nặng, đọc được mà không cần chấm từng chữ.

═══════════════════════════════════════════════════════════════════════════
VieNeu KHÔNG TIỀN ĐỊNH -> CHẠY NHIỀU LƯỢT, BÁO DẢI
═══════════════════════════════════════════════════════════════════════════
OmniVoice từng ra 41,8% và 99,4% trên CÙNG một hàm; VieNeu cũng vậy (bảng
giọng dựng sẵn đo 5 lượt mới ra dải 0,115-0,346 ở phép ECAPA). Một lượt rồi
báo số là tự lừa mình. edge-tts tiền định nên 1 lượt là đủ, ghi thẳng ra.

Chạy:  .venv\\Scripts\\python -u _do_adam_en.py
Env:   BQ_AD_VONG=2 · BQ_AD_LAI=1 (bỏ cache) · BQ_AD_ARM=AD_en,AD_vi
"""
from __future__ import annotations

import json
import os
import re
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_vieneu_en as DV                                      # noqa: E402
from _do_doc_sai import tu_kiem_bo_cham                         # noqa: E402

#: Arm MỚI của lượt này. Arm cũ lấy lại từ cache của `_do_vieneu_en.py`.
ARM_MOI: list[tuple[str, str, str]] = [
    ("AD_en", "vn:Adam", "en"),      # CÂU HỎI CHÍNH
    ("AD_vi", "vn:Adam", "vi"),      # ĐỐI CHỨNG: chính nó đọc tiếng Việt
]

#: Arm ĐỐI CHỨNG (đã có trong cache — không đọc lại, không tốn lượt).
ARM_CU: list[tuple[str, str, str]] = [
    ("edge_en", "en-US-AriaNeural",   "en"),    # TRẦN tiếng Anh
    ("NH_en",   "vn:Ngọc Huyền",      "en"),
    ("MD_en",   "vn:Minh Đức",        "en"),
    ("TL_en",   "vn:Trúc Ly",         "en"),
    ("NH_vi",   "vn:Ngọc Huyền",      "vi"),
    ("edge_vi", "vi-VN-HoaiMyNeural", "vi"),    # TRẦN tiếng Việt
]

NHAN = {
    "AD_en":   "vn:Adam x ANH  <= CÂU HỎI",
    "AD_vi":   "vn:Adam x VIỆT (đối chứng)",
    "edge_en": "edge Aria x ANH (TRẦN Anh)",
    "NH_en":   "vn:Ngọc Huyền x ANH",
    "MD_en":   "vn:Minh Đức x ANH",
    "TL_en":   "vn:Trúc Ly x ANH",
    "NH_vi":   "vn:Ngọc Huyền x VIỆT",
    "edge_vi": "edge HoaiMy x VIỆT (TRẦN Việt)",
}

HOP = DV.HOP
KQ_JSON = REPO / "_kq_adam_en.json"


# ------------------------------------------------------------ BỊA CHỮ / SAI
def dem_op(goc: str, nghe: str) -> tuple[int, int, int, int]:
    """(THAY, CHÈN, THIẾU, số từ gốc) — gióng hàng Levenshtein CÓ TRUY VẾT.

    `_do_vieneu_en.wer` chỉ trả TỔNG lỗi nên không tách được "đọc sai chữ"
    với "bịa thêm chữ". Hai cột PHẢI đọc trên **cùng một cách tách từ**.

    Bản đầu **CHÉP LẠI** biểu thức chuẩn hoá của `wer` — hai bản sao là hai
    chỗ để lệch nhau, và đã lệch thật: lượt vá CJK ngày 26/08 sửa `wer` thì
    `dem_op` vẫn cắt sạch chữ Hán. Nay GỌI THẲNG `DV.chuan_tu` (một bộ tách,
    CJK-aware, giữ nguyên hành vi với chữ latin).
    """
    a, b = DV.chuan_tu(goc), DV.chuan_tu(nghe)
    if not a:
        return (0, 0, 0, 0)
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    i, j, thay, chen, thieu = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            thay += int(a[i - 1] != b[j - 1])
            i, j = i - 1, j - 1
        elif j > 0 and d[i][j] == d[i][j - 1] + 1:
            chen += 1
            j -= 1
        else:
            thieu += 1
            i -= 1
    return (thay, chen, thieu, n)


def do_le(ten: str, vong: int, so_cau: int = 8) -> tuple[float, float, int]:
    """(lề im ĐẦU, lề im CUỐI) TRUNG BÌNH giây trên `so_cau` file ĐẦU của arm.

    Đo bằng `thay_giong.do_le_im` — ĐÚNG hàm đường xuất thật dùng để cắt lề,
    không dựng thước riêng. Chỉ lấy vài câu đầu: mỗi lượt gọi là một lệnh
    ffmpeg, mà câu hỏi ở đây là "lề có dài bất thường không", không phải
    "lề của câu thứ 31 là bao nhiêu".
    """
    from app.core import thay_giong as TG
    thu = HOP / f"{ten}_v{vong}"
    dau, cuoi = [], []
    for i in range(so_cau):
        p = thu / f"c{i:03d}.mp3"
        if not p.exists():
            continue
        try:
            d, c, _t = TG.do_le_im(p)
        except Exception:                                       # noqa: BLE001
            continue
        dau.append(d)
        cuoi.append(c)
    if not dau:
        return (0.0, 0.0, 0)
    return (st.mean(dau), st.mean(cuoi), len(dau))


def dai(xs: list[float], don_vi: str = "") -> str:
    if not xs:
        return "—"
    if len(xs) == 1:
        return f"{xs[0]:.1f}{don_vi}"
    return (f"{min(xs):.1f}–{max(xs):.1f}{don_vi} "
            f"(TB {st.mean(xs):.1f}{don_vi})")


# ------------------------------------------------- GIẢ THUYẾT "bộ âm tiếng Việt"
def kiem_gia_thuyet() -> dict:
    """Adam có đọc tiếng Anh bằng BỘ ÂM TIẾNG VIỆT không — đọc MÃ, không đoán.

    Ba câu hỏi tách rời, mỗi câu một bằng chứng:
      (a) bảng giọng có trường NGÔN NGỮ riêng cho Adam không, hay chỉ có
          `speaker_emb`/`codes` (tức chỉ là CHẤT GIỌNG)?
      (b) `infer()` có tham số ngôn ngữ không?
      (c) bộ phiên âm chữ->âm có đổi theo giọng không, và nó ra âm gì với chữ
          tiếng Anh?
    """
    ra: dict = {}
    vn_dir = REPO / "_giong_vieneu" / "venv" / "Lib" / "site-packages"
    js = vn_dir / "vieneu" / "assets" / "voices_v3_turbo.json"
    if js.exists():
        d = json.loads(js.read_text(encoding="utf-8"))
        ps = d.get("presets") or {}
        ad = ps.get("Adam") or {}
        khac = ps.get("Minh Đức") or {}
        ra["so_giong"] = len(ps)
        ra["khoa_adam"] = sorted(ad.keys())
        ra["khoa_giong_viet"] = sorted(khac.keys())
        ra["cung_bo_khoa"] = sorted(ad.keys()) == sorted(khac.keys())
        ra["region_adam"] = ad.get("region")
        ra["meta"] = d.get("meta")
    src = vn_dir / "vieneu" / "v3turbo.py"
    if src.exists():
        t = src.read_text(encoding="utf-8", errors="replace")
        ra["infer_co_lang"] = bool(re.search(r"def infer\([^)]*lang", t, re.S))
        ra["goi_phonemize"] = t.count("phonemize_text_with_emotions(")
    ph = vn_dir / "vieneu_utils" / "phonemize_text.py"
    if ph.exists():
        t = ph.read_text(encoding="utf-8", errors="replace")
        ra["lang_ghi_cung"] = sorted(set(re.findall(r"lang\s*=\s*\"(\w+)\"", t)))
    # (c) CHẠY THẬT bộ phiên âm trong môi trường VieNeu -> âm ra là gì
    py = REPO / "_giong_vieneu" / "venv" / "Scripts" / "python.exe"
    if py.exists():
        ma = (
            "import json,sys\n"
            "sys.stdout.reconfigure(encoding='utf-8')\n"
            "from vieneu_utils.phonemize_text import phonemize_text\n"
            "from sea_g2p import SEAPipeline\n"
            "r={}\n"
            "r['en']=phonemize_text('A storm unlike anything in recorded "
            "history is closing in on the city.')\n"
            "r['vi']=phonemize_text('Một cơn bão chưa từng có trong lịch sử "
            "đang ập tới thành phố này.')\n"
            "ok=[]\n"
            "for lg in ('vi','en','th','id'):\n"
            "    try:\n"
            "        SEAPipeline(lang=lg); ok.append(lg)\n"
            "    except Exception: pass\n"
            "r['lang_ho_tro']=ok\n"
            "print('##JSON##'+json.dumps(r,ensure_ascii=False))\n")
        import subprocess
        tam = HOP / "_ph.py"
        HOP.mkdir(parents=True, exist_ok=True)
        tam.write_text(ma, encoding="utf-8")
        try:
            r = subprocess.run([str(py), "-u", str(tam)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=300)
            for d in (r.stdout or "").splitlines():
                if d.startswith("##JSON##"):
                    ra.update(json.loads(d[8:]))
        except Exception as e:                                  # noqa: BLE001
            ra["loi_phonemize"] = f"{type(e).__name__}: {e}"
        finally:
            tam.unlink(missing_ok=True)
    return ra


# -------------------------------------------------------------------- chạy
def main() -> int:
    HOP.mkdir(exist_ok=True)
    cache = {}
    if DV.CACHE.exists():
        try:
            cache = json.loads(DV.CACHE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_AD_LAI") == "1"
    so_vong = int(os.environ.get("BQ_AD_VONG", "2"))
    chi = [x.strip() for x in (os.environ.get("BQ_AD_ARM") or "").split(",")
           if x.strip()]

    # Adam phải được đo ĐỌC RỜI (cột THẬT) — arm cũ giữ nguyên danh sách của
    # `_do_vieneu_en.py` để cache còn dùng lại được.
    DV.ARM_ROI = tuple(DV.ARM_ROI) + ("AD_en", "AD_vi")
    DV.NHAN_ARM.update(NHAN)

    print("=" * 78)
    print("`vn:Adam` HỎNG THẬT hay CHỈ KÉM — cửa thật `dubbing._synth_all`")
    print("=" * 78)
    print(f"corpus: `_bo_cau_thu_doc.py` · en {len(DV.CORPUS['en'])} câu / "
          f"{len(DV.token_theo_nn('en'))} token rời · vi "
          f"{len(DV.CORPUS['vi'])} câu / {len(DV.token_theo_nn('vi'))} token rời")

    print("\nTỰ KIỂM BỘ CHẤM (6 cặp đã biết đáp án)")
    # `tu_kiem_bo_cham()` TỰ IN bảng 6 cặp và trả về **bool** (True = khớp
    # hết). In lại nó dưới dạng "lệch N/6" là ra `lệch True/6` — số vô nghĩa
    # mà trông như số đo.
    dat = bool(tu_kiem_bo_cham())
    print(f"  -> bộ chấm {'KHỚP HẾT' if dat else 'CÓ LỆCH'}")
    if not dat:
        print("  DỪNG: bộ chấm lệch -> mọi số dưới đây vô nghĩa")
        return 2

    tat: dict[str, list[dict]] = {}
    for vong in range(1, so_vong + 1):
        # ĐAN XEN + XOAY thứ tự: đo liền mạch một arm rồi mới arm kia là để
        # máy/mạng nóng-nguội đi vào cột số (đã sập 3 lần trên máy này).
        arms = list(ARM_MOI)
        arms = arms[(vong - 1) % len(arms):] + arms[:(vong - 1) % len(arms)]
        if vong == 1:
            arms = arms + ARM_CU
        arms = [a for a in arms if not chi or a[0] in chi]
        print(f"\n--- VÒNG {vong}/{so_vong} · thứ tự: "
              f"{', '.join(a[0] for a in arms)} ---")
        for ten, voice, nn in arms:
            if ten in dict((a[0], a) for a in ARM_CU) and vong > 1:
                continue                    # edge/arm cũ: 1 lượt là đủ
            kq = DV.chay_arm(ten, voice, nn, vong, cache, lam_lai)
            c = DV.cham(kq)
            # BỊA CHỮ + LỀ IM: tính TỪ CHÍNH bản chép đã cache
            thay = chen = thieu = tong = 0
            for h in kq["cau"]:
                if not h["doc_duoc"]:
                    continue
                t_, c_, k_, n_ = dem_op(h["cau"], h["chep"])
                thay += t_
                chen += c_
                thieu += k_
                tong += n_
            c["thay"], c["chen"], c["thieu"], c["tu"] = thay, chen, thieu, tong
            le_d, le_c, le_n = do_le(ten, vong)
            c["le_dau"], c["le_cuoi"], c["le_n"] = le_d, le_c, le_n
            c["giay_cau"] = kq.get("giay_cau")
            tat.setdefault(ten, []).append(c)
            print(f"  [{ten} v{vong}] token trong câu "
                  f"{c['tc_sai']}/{c['tc_n']} · đọc rời {c['tr_sai']}/"
                  f"{c['tr_n']} · bịa {chen}/{tong} từ · lề {le_d*1000:.0f}/"
                  f"{le_c*1000:.0f} ms · nhãn nn {c['nn_dung']}/{c['nn_n']}")

    # ------------------------------------------------------------- BẢNG 1
    thu_tu = ["AD_en", "edge_en", "NH_en", "MD_en", "TL_en",
              "AD_vi", "NH_vi", "edge_vi"]
    print("\n" + "=" * 78)
    print("BẢNG 1 — SAI CHỮ / BỊA CHỮ / LỀ IM  (dải qua các lượt)")
    print("=" * 78)
    print(f"{'arm':<30}{'token TRONG CÂU %':>19}{'ĐỌC RỜI %':>13}"
          f"{'bịa chữ %':>12}")
    for ten in thu_tu:
        rs = tat.get(ten) or []
        if not rs:
            continue
        tc = dai([100 * r["tc_sai"] / max(1, r["tc_n"]) for r in rs])
        tr = (dai([100 * r["tr_sai"] / max(1, r["tr_n"]) for r in rs])
              if rs[0]["tr_n"] else "—")
        bi = dai([100 * r["chen"] / max(1, r["tu"]) for r in rs])
        print(f"{NHAN.get(ten, ten):<30}{tc:>19}{tr:>13}{bi:>12}")

    print("\n" + "=" * 78)
    print("BẢNG 2 — WER · THAY/THIẾU CHỮ · LỀ IM · NHÃN NGÔN NGỮ MÁY NGHE")
    print("=" * 78)
    print(f"{'arm':<30}{'WER %':>14}{'thay %':>9}{'thiếu %':>9}"
          f"{'lề đầu/cuối ms':>18}{'nhãn đúng':>11}")
    for ten in thu_tu:
        rs = tat.get(ten) or []
        if not rs:
            continue
        w = dai([r["wer"] for r in rs])
        th = dai([100 * r["thay"] / max(1, r["tu"]) for r in rs])
        ti = dai([100 * r["thieu"] / max(1, r["tu"]) for r in rs])
        le = (f"{st.mean([r['le_dau'] for r in rs])*1000:.0f}/"
              f"{st.mean([r['le_cuoi'] for r in rs])*1000:.0f}")
        nn = "/".join(f"{r['nn_dung']}/{r['nn_n']}" for r in rs)
        print(f"{NHAN.get(ten, ten):<30}{w:>14}{th:>9}{ti:>9}{le:>18}{nn:>11}")
    for ten in thu_tu:
        rs = tat.get(ten) or []
        if rs and rs[0].get("nn_khac"):
            print(f"  nhãn LẠ ở {NHAN.get(ten, ten)}: "
                  f"{', '.join(rs[0]['nn_khac'])}")

    # ------------------------------------------------------------- BẢNG 3
    print("\n" + "=" * 78)
    print("BẢNG 3 — TOKEN HỎNG Ở `vn:Adam x ANH` MÀ TRẦN edge ĐỌC ĐƯỢC")
    print("=" * 78)
    if tat.get("AD_en") and tat.get("edge_en"):
        for nhan_cot, khoa in (("TRONG CÂU", "tc"), ("ĐỌC RỜI", "tr")):
            tran_ok = {x["token"] for x in tat["edge_en"][0][khoa] if x["dung"]}
            hong: dict[str, str] = {}
            for r in tat["AD_en"]:
                for x in r[khoa]:
                    if not x["dung"] and x["token"] in tran_ok:
                        hong.setdefault(x["token"], x["chep"][:70])
            print(f"  {nhan_cot}: {len(hong)} token")
            for tk, ch in sorted(hong.items()):
                print(f"    «{tk}» -> máy nghe chép «{ch}»")

    # --------------------------------------------------------- GIẢ THUYẾT
    print("\n" + "=" * 78)
    print("GIẢ THUYẾT: Adam đọc tiếng Anh bằng BỘ ÂM TIẾNG VIỆT?")
    print("=" * 78)
    gt = kiem_gia_thuyet()
    print(f"  bảng giọng: {gt.get('so_giong')} giọng · meta {gt.get('meta')}")
    print(f"  khoá của `Adam`      : {gt.get('khoa_adam')}")
    print(f"  khoá của giọng Việt  : {gt.get('khoa_giong_viet')}")
    print(f"  -> CÙNG bộ khoá: {gt.get('cung_bo_khoa')} · "
          f"region ghi: {gt.get('region_adam')!r}")
    print(f"  `infer()` có tham số ngôn ngữ: {gt.get('infer_co_lang')}")
    print(f"  ngôn ngữ GHI CỨNG trong bộ phiên âm: {gt.get('lang_ghi_cung')}")
    print(f"  sea-g2p nhận lang: {gt.get('lang_ho_tro')}")
    print(f"  âm ra cho chữ ANH: {str(gt.get('en'))[:150]}")
    print(f"  âm ra cho chữ VIỆT: {str(gt.get('vi'))[:150]}")

    KQ_JSON.write_text(json.dumps(
        {"arm": {k: [{kk: vv for kk, vv in r.items() if kk not in ("tc", "tr")}
                     for r in v] for k, v in tat.items()},
         "gia_thuyet": gt, "luc": time.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSố thô: {KQ_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
