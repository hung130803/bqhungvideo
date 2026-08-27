# -*- coding: utf-8 -*-
"""TẬT "ĐỌC LAN MAN" CỦA `vnb:` CÓ Ở NHỮNG TIẾNG NÀO — và NGƯỠNG 1,5 có đúng?

`app/core/doc_lan.py` phát hành ở v2.43.0 với ngưỡng **1,5**, hiệu chuẩn trên
**MỘT** thứ tiếng: tiếng ANH (`_do_vnb_lan.py`). Nhưng bản vá ấy đang chạy trên
**MỌI** ngôn ngữ của 200-300 kênh. Hai câu chưa ai trả lời:

  1. Tật ấy có ở **tiếng VIỆT** (tiếng gốc của model) và các tiếng khác không?
  2. **Ngưỡng 1,5 có đúng cho tiếng khác không**, hay nó kêu oan / bỏ sót?

Câu 2 nặng hơn, vì nó nói về thứ ĐANG CHẠY.

═══════════════════════════════════════════════════════════════════════════
DÙNG LẠI NGUYÊN BỘ CHẤM — KHÔNG VIẾT BỘ THỨ HAI
═══════════════════════════════════════════════════════════════════════════
corpus `_bo_cau_thu_doc` · đọc + chép ngược + WER + chấm token
`_do_vieneu_en.chay_arm/cham` · bịa chữ `_do_adam_en.dem_op` · sự thật đối
chứng + `lan` `_do_vnb_lan._hang` · canh động cơ `_do_vnb_en.CanhDongCo` ·
**cùng một file mẫu** `_do_vnb_en.lam_mau()`. Bộ chấm thứ hai = hai bảng số
không so được với nhau.

Nhờ dùng chung `_do_vn_en/cache.json`, arm tiếng Anh của lượt 26/08 vẫn nằm
nguyên đó và **được in lại làm cột so** mà không tốn một lượt nào.

═══════════════════════════════════════════════════════════════════════════
BỐN ĐIỀU KIỆN, THIẾU CÁI NÀO THÌ BẢNG SỐ VÔ NGHĨA
═══════════════════════════════════════════════════════════════════════════
 1. **TRẦN ĐỐI CHỨNG cho TỪNG TIẾNG** — giọng edge-tts **bản ngữ đúng tiếng
    đó**, chạy CÙNG LƯỢT. "5% sai chữ" là tốt hay tệ chỉ trả lời được khi
    biết máy đọc bản ngữ đạt bao nhiêu TRÊN CHÍNH bộ câu này. Và ngưỡng `lan`
    được chọn theo ĐÚNG cột đó (chỗ thấp nhất mà TRẦN không kêu lần nào).
 2. **VieNeu KHÔNG TIỀN ĐỊNH -> >= 2 LƯỢT, ghi DẢI.** Chính vì chạy 2 lượt
    mới lòi ra tật này (WER 3,1% rồi 12,7% trên cùng bản mã, cùng mẫu).
 3. **ĐẾM TỪ PHẢI CJK-AWARE.** Bộ chuẩn hoá cũ vứt sạch chữ Hán/kana/hangul
    nên câu Trung/Nhật/**Hàn** ra **0 token** -> mọi tỉ lệ ra 0 và bảng **TỰ
    ĐẠT OAN** (đúng lỗi đã sập ở cổng 52/54). Đã vá ở `_do_vieneu_en.chuan_tu`
    và MỤC TỰ KIỂM dưới đây DỪNG cả lượt đo nếu bản vá không ăn.
 4. **CANH ĐỘNG CƠ.** `dubbing._synth_all` cố ý lùi êm về edge-tts khi máy
    nhân bản hỏng cả loạt — đúng cho người dùng, **thảm hoạ cho phép đo**:
    bảng sẽ ghi "vnb: 0% sai chữ" trong khi thứ vừa đọc là edge-tts.

═══════════════════════════════════════════════════════════════════════════
HAI THỨ CỐ Ý GIỮ NGUYÊN GIỮA CÁC TIẾNG (để chỉ có NGÔN NGỮ là biến)
═══════════════════════════════════════════════════════════════════════════
  · **CÙNG MỘT FILE MẪU** (`mau_en_andrew.wav`, từng byte). `giong_chatter`
    đã đo *"MẪU kéo nhịp đọc"* — cùng 12 câu, mẫu này 1,03x mẫu kia 1,32x.
    Đổi mẫu theo tiếng là trộn hai nguyên nhân vào một cột số. Đây cũng đúng
    đường anh Hùng đi: anh ấy có MỘT giọng nhân bản và dùng nó cho mọi đích.
  · **CÙNG bộ câu 34 câu + token rời** của `_bo_cau_thu_doc`.

Chạy:  .venv\\Scripts\\python -u _do_lan_nn.py
Env:   BQ_LN_VONG=2 · BQ_LN_LAI=1 (bỏ cache) · BQ_LN_NN=vi,ko
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

import _do_adam_en as DA                                        # noqa: E402
import _do_vieneu_en as DV                                      # noqa: E402
import _do_vnb_en as DB                                         # noqa: E402
import _do_vnb_lan as DL                                        # noqa: E402
from _bo_cau_thu_doc import NHAN_NN                             # noqa: E402
from app.core import doc_lan                                    # noqa: E402

KQ = REPO / "_kq_lan_nn.json"

#: BẢN GỌN **CÓ THEO DÕI GIT** — cổng 92 đọc file này, đúng lý do
#: `_moc_doc_lan.json` tồn tại: `_kq*.json` bị `.gitignore` nên cổng đọc thẳng
#: nó sẽ ĐỎ OAN vì KHO trên máy vừa clone (bệnh cổng 47 CA2 / cổng 68).
MOC = REPO / "_moc_doc_lan_nn.json"

#: ngôn ngữ -> giọng edge-tts **BẢN NGỮ** làm TRẦN ĐỐI CHỨNG.
TRAN_NN: dict[str, str] = {
    "vi": "vi-VN-HoaiMyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}

#: Thứ tự đo. Tiếng Anh KHÔNG đo lại — lấy thẳng arm cũ trong cache.
NN_DO = ("vi", "zh", "ja", "ko")

#: Quét ngưỡng ở đây. Bước 0,1 quanh 1,5 để trả lời được câu "hạ/nâng một bậc
#: thì TRẦN có kêu không" — đúng cách 1,5 được chọn cho tiếng Anh.
LUOI_NGUONG = (1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.5, 3.0, 4.0)


# ═══════════════════════════════════════════════════ TỰ KIỂM BỘ ĐẾM TỪ
def tu_kiem_dem_tu() -> bool:
    """Bộ đếm từ có CJK-aware thật không — và có GIỮ NGUYÊN chữ latin không.

    Không có mục này thì cả bảng zh/ja/ko có thể ra **0,0% ở mọi cột** rồi
    được đọc thành "giọng nhân bản đọc tiếng Trung hoàn hảo". Đó đúng là họ
    bẫy *"phép đo hỏng phát chứng nhận"* (`astats` cổng 53 · `startswith`
    cổng 44 · mức mờ 0,40 cổng 56b).
    """
    def cu(s: str) -> list[str]:
        s = re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\s]", " ", (s or "").lower())
        return re.sub(r"\s+", " ", s).strip().split()

    ok = True
    # (a) CJK phải ra > 1 token
    for nn, s, toi_thieu in (
            ("zh", "今天天气很好，我们一起出去走走吧。", 10),
            ("ja", "今日はとてもいい天気なので、一緒に散歩しましょう。", 10),
            ("ko", "오늘은 날씨가 아주 좋으니까 같이 산책하러 가요.", 5)):
        n = len(DV.chuan_tu(s))
        dat = n >= toi_thieu
        ok = ok and dat
        print(f"  {'ĐẠT ' if dat else 'HỎNG'} {nn}: {n} token "
              f"(bản cũ {len(cu(s))})")
    # (b) tiếng HÀN tách theo TỪ, KHÔNG theo âm tiết (nó CÓ dấu cách)
    ko = DV.chuan_tu("오늘은 날씨가 아주 좋으니까 같이 산책하러 가요.")
    dat = len(ko) == 7 and ko[0] == "오늘은"
    ok = ok and dat
    print(f"  {'ĐẠT ' if dat else 'HỎNG'} Hàn tách theo TỪ ({len(ko)} token), "
          f"KHÔNG theo âm tiết (recap._word_tokens ra 20)")
    # (c) BẤT BIẾN: chữ latin ra Y HỆT bản cũ
    from _bo_cau_thu_doc import CORPUS
    n = lech = 0
    for l_nn in ("en", "vi"):
        for _l, c, toks in CORPUS[l_nn]:
            for s in [c] + list(toks):
                n += 1
                lech += int(cu(s) != DV.chuan_tu(s))
    ok = ok and lech == 0
    print(f"  {'ĐẠT ' if lech == 0 else 'HỎNG'} BẤT BIẾN latin: "
          f"{n - lech}/{n} chuỗi giống HỆT bản cũ")
    return ok


# ═══════════════════════════════════════════════════════════ chạy một arm
def chay(ten: str, voice: str, nn: str, vong: int, cache: dict,
         lam_lai: bool, can_may: str) -> dict:
    """Một arm-lượt: đọc + chép ngược + chấm, KÈM canh động cơ."""
    khoa = f"{ten}|{voice}|{nn}|v{vong}"
    da_co = bool(cache.get(khoa)) and not lam_lai
    with DB.CanhDongCo() as canh:
        t0 = time.time()
        kq = DV.chay_arm(ten, voice, nn, vong, cache, lam_lai)
        giay = time.time() - t0
    n_can = len(DV.CORPUS[nn]) + len(DV.token_theo_nn(nn))
    if da_co:
        hop_le = None                       # cache: không có gì để đếm
    elif can_may:
        hop_le = canh.dem.get(can_may, 0) >= n_can
        print(f"  [{ten} v{vong}] CANH ĐỘNG CƠ: {can_may} trả "
              f"{canh.dem.get(can_may, 0)}/{n_can} -> "
              f"{'HỢP LỆ' if hop_le else 'KHÔNG HỢP LỆ (lùi edge?)'}")
    else:
        hop_le = True
    c = DV.cham(kq)
    thay = chen = thieu = tong = 0
    for h in kq["cau"]:
        if not h["doc_duoc"]:
            continue
        t_, c_, k_, n_ = DA.dem_op(h["cau"], h["chep"])
        thay, chen, thieu, tong = thay + t_, chen + c_, thieu + k_, tong + n_
    c |= {"thay": thay, "chen": chen, "thieu": thieu, "tu": tong,
          "hop_le": hop_le, "vong": vong, "nn": nn, "arm": ten,
          "doc_duoc": sum(1 for h in kq["cau"] if h["doc_duoc"]),
          "so_cau": len(kq["cau"]),
          "giay_moi_cau": giay / max(1, n_can) if not da_co else None}
    print(f"  [{ten} v{vong}] đọc {c['doc_duoc']}/{c['so_cau']} câu · "
          f"token trong câu {c['tc_sai']}/{c['tc_n']} · rời "
          f"{c['tr_sai']}/{c['tr_n']} · bịa {chen}/{tong} · "
          f"WER {c['wer']:.1f}% · nhãn {c['nn_dung']}/{c['nn_n']}")
    return {"cham": c, "kq": kq}


def hang(kq: dict, nn: str, chen_min: int) -> list[dict]:
    """Danh sách câu + token rời có đủ `lan` + `bia`, mốc khớp TỪ CHÍNH LOẠT."""
    hs = (DL._hang(kq, "c", "cau", nn, chen_min)
          + DL._hang(kq, "t", "token", nn, chen_min))
    if not hs:
        return []
    a, b = doc_lan.moc_nhip([h["chu"] for h in hs], [h["giay"] for h in hs])
    for h in hs:
        h["lan"] = doc_lan.lan_vuot(h["chu"], h["giay"], a, b)
    return hs


def dai(xs: list[float], d: int = 1) -> str:
    if not xs:
        return "—"
    if len(xs) == 1:
        return f"{xs[0]:.{d}f}"
    return f"{min(xs):.{d}f}–{max(xs):.{d}f}"


# ═══════════════════════════════════════════════════════════════════ chạy
def main() -> int:
    DV.HOP.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    if DV.CACHE.exists():
        try:
            cache = json.loads(DV.CACHE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_LN_LAI") == "1"
    so_vong = int(os.environ.get("BQ_LN_VONG", "2"))
    chi = [x.strip() for x in (os.environ.get("BQ_LN_NN") or "").split(",")
           if x.strip()]
    nns = [n for n in NN_DO if not chi or n in chi]

    print("=" * 78)
    print("TẬT ĐỌC LAN MAN CỦA `vnb:` THEO NGÔN NGỮ — và ngưỡng có phải đổi?")
    print("=" * 78)

    # ĐO **BỆNH THÔ**, KHÔNG ĐO BẢN ĐÃ CHỮA. `BAT_DOC_LAI` mặc định BẬT, mà
    # lượt đọc lại THAY FILE bằng bản đỡ hơn -> đo sau đó là hiệu chuẩn ngưỡng
    # trên chính đầu ra của bộ dò, tức bộ dò tự chấm điểm mình. Bộ dò VẪN CHẠY
    # và VẪN GHI LOG khi tắt (cột đối chứng) — xem `_doc_lai_lan_man`.
    os.environ["BQ_VN_DOC_LAI"] = "0"
    print("BQ_VN_DOC_LAI=0 — đo BỆNH THÔ (bộ dò vẫn dò + ghi log, chỉ không "
          "đọc lại)")

    # NGÂN SÁCH GIỜ CỦA MỘT LOẠT. Mặc định `doc_loat` là 1800 s; đo thử tiếng
    # HÀN ra **22,7 s/câu**, tức 58 mục ≈ 1.230 s — sát trần tới mức một lượt
    # chậm hơn bình thường là **quá giờ, mất trắng cả arm**, và triệu chứng
    # ("đọc 0/34") trông y hệt "giọng không đọc được tiếng đó" = kết luận NGƯỢC.
    from app.core import giong_vieneu as _GV
    _that = _GV.doc_loat

    def _rong_han(*a, **k):
        k.setdefault("han_giay", 5400)
        return _that(*a, **k)

    _GV.doc_loat = _rong_han                                # type: ignore

    print("\nTỰ KIỂM BỘ ĐẾM TỪ (CJK-aware + bất biến latin)")
    if not tu_kiem_dem_tu():
        print("  DỪNG: bộ đếm từ hỏng -> mọi số dưới đây VÔ NGHĨA "
              "(bảng sẽ tự ĐẠT OAN).")
        return 2

    mau = DB.lam_mau()
    print(f"\nmẫu CHUNG cho MỌI tiếng: {mau.name} · {mau.stat().st_size} byte")
    for n in nns:
        print(f"  {NHAN_NN[n]:<6} corpus {len(DV.CORPUS[n])} câu + "
              f"{len(DV.token_theo_nn(n))} token rời · TRẦN {TRAN_NN[n]}")

    # arm mới phải khai ĐỌC RỜI, nếu không `chay_arm` bỏ hẳn cột đó
    them = tuple(f"{p}_{n}" for n in nns for p in ("VNB", "EDG"))
    DV.ARM_ROI = tuple(DV.ARM_ROI) + them

    tat: dict[str, list[dict]] = {}
    kqs: dict[str, list[dict]] = {}
    for vong in range(1, so_vong + 1):
        # ĐAN XEN + XOAY: chạy liền mạch một tiếng rồi mới tiếng kia thì tiếng
        # sau gánh phần máy/mạng đã nóng (đã sai 3 lần trên đúng máy này).
        thu = nns[(vong - 1) % max(1, len(nns)):] + \
            nns[:(vong - 1) % max(1, len(nns))]
        print(f"\n--- VÒNG {vong}/{so_vong} · thứ tự: {', '.join(thu)} ---")
        for nn in thu:
            r = chay(f"VNB_{nn}", f"vnb:{mau}", nn, vong, cache, lam_lai,
                     "vieneu")
            tat.setdefault(f"VNB_{nn}", []).append(r["cham"])
            kqs.setdefault(f"VNB_{nn}", []).append(r["kq"])
            if vong == 1:
                # TRẦN chạy CÙNG LƯỢT. edge-tts tiền định nên 1 lượt là đủ —
                # ghi thẳng ra, không giả vờ đã chạy 2.
                r2 = chay(f"EDG_{nn}", TRAN_NN[nn], nn, vong, cache, lam_lai,
                          "")
                tat.setdefault(f"EDG_{nn}", []).append(r2["cham"])
                kqs.setdefault(f"EDG_{nn}", []).append(r2["kq"])

    # ═════════════════════════════════════════════════════════════ BẢNG 1
    print("\n" + "=" * 78)
    print("BẢNG 1 — ĐỌC ĐƯỢC KHÔNG · SAI CHỮ · BỊA CHỮ  (DẢI qua các lượt)")
    print("=" * 78)
    print(f"{'arm':<34}{'đọc được':>10}{'TRONG CÂU %':>14}{'RỜI %':>12}"
          f"{'bịa %':>12}{'WER %':>13}{'nhãn':>9}")
    thu_tu = [a for n in nns for a in (f"VNB_{n}", f"EDG_{n}")]
    for ten in thu_tu:
        rs = tat.get(ten) or []
        if not rs:
            continue
        nn = rs[0]["nn"]
        nhan = (f"vnb: x {NHAN_NN[nn]}" if ten.startswith("VNB")
                else f"edge {TRAN_NN[nn].split('-')[-1]} x {NHAN_NN[nn]} TRẦN")
        dd = dai([100 * r["doc_duoc"] / max(1, r["so_cau"]) for r in rs], 0)
        tc = dai([100 * r["tc_sai"] / max(1, r["tc_n"]) for r in rs])
        tr = (dai([100 * r["tr_sai"] / max(1, r["tr_n"]) for r in rs])
              if rs[0]["tr_n"] else "—")
        bi = dai([100 * r["chen"] / max(1, r["tu"]) for r in rs])
        w = dai([r["wer"] for r in rs])
        la = "/".join(f"{r['nn_dung']}/{r['nn_n']}" for r in rs)
        co = "" if all(r["hop_le"] is not False for r in rs) else " [KHÔNG HỢP LỆ]"
        print(f"{nhan + co:<34}{dd + '%':>10}{tc:>14}{tr:>12}{bi:>12}"
              f"{w:>13}{la:>9}")
    print("  (DẢI = nhỏ nhất–lớn nhất qua các lượt. arm TRẦN edge-tts chạy 1 "
          "lượt: đã đo được là tiền định.)")

    # ═══════════════════════════════════════════════ NGƯỠNG `chen` cho bịa
    print("\n" + "=" * 78)
    print("BẢNG 2 — HIỆU CHUẨN 'BAO NHIÊU TỪ TỰ THÊM MỚI GỌI LÀ BỊA'")
    print("=" * 78)
    print("  Luật tiếng Anh là `chen >= 2` TỪ. Với Trung/Nhật một token là MỘT")
    print("  KÝ TỰ, nên 2 token là mức nhiễu của chính máy nghe. Chọn như đã")
    print("  chọn cho tiếng Anh: **k nhỏ nhất mà arm TRẦN không dính lần nào**")
    print("  (tiếng Anh: edge_en dính 0/58 ngay ở k=2).")
    print(f"\n{'tiếng':<8}" + "".join(f"{'k=' + str(k):>10}"
                                      for k in range(1, 9)) + f"{'CHỌN':>8}")
    chen_min: dict[str, int] = {}
    for nn in nns:
        rs = kqs.get(f"EDG_{nn}") or []
        if not rs:
            chen_min[nn] = 2
            continue
        d = ""
        chon = None
        for k in range(1, 9):
            hs = hang(rs[0], nn, k)
            n = sum(1 for h in hs if h["bia"])
            d += f"{f'{n}/{len(hs)}':>10}"
            if n == 0 and chon is None:
                chon = k
        chen_min[nn] = chon or 8
        print(f"{NHAN_NN[nn]:<8}{d}{chen_min[nn]:>8}")
    print("  (ô = số mục arm TRẦN bị GÁN OAN là bịa / tổng mục)")

    # ═══════════════════════════════════════════════ phân bố hai nhóm
    print("\n" + "=" * 78)
    print("BẢNG 3 — PHÂN BỐ `lan` HAI NHÓM (câu LÀNH vs câu BỊA) + arm TRẦN")
    print("=" * 78)
    print(f"{'tiếng · nhóm':<30}{'n':>5}{'nhỏ nhất':>11}{'trung vị':>11}"
          f"{'bpv90':>9}{'lớn nhất':>11}")
    dong: dict[str, dict[str, list[dict]]] = {}
    for nn in nns:
        dong[nn] = {
            "vnb": [h for kq in (kqs.get(f"VNB_{nn}") or [])
                    for h in hang(kq, nn, chen_min[nn])],
            "tran": [h for kq in (kqs.get(f"EDG_{nn}") or [])
                     for h in hang(kq, nn, chen_min[nn])],
        }
        for nhan, xs in (
                ("vnb LÀNH", [h["lan"] for h in dong[nn]["vnb"] if not h["bia"]]),
                ("vnb BỊA ", [h["lan"] for h in dong[nn]["vnb"] if h["bia"]]),
                ("TRẦN edge", [h["lan"] for h in dong[nn]["tran"]])):
            xs = sorted(xs)
            if not xs:
                print(f"  {NHAN_NN[nn]} · {nhan:<18}{0:>5}"
                      + f"{'—':>11}" * 2 + f"{'—':>9}{'—':>11}")
                continue
            p90 = xs[min(len(xs) - 1, int(0.90 * len(xs)))]
            print(f"  {NHAN_NN[nn]} · {nhan:<18}{len(xs):>5}{xs[0]:>11.2f}"
                  f"{st.median(xs):>11.2f}{p90:>9.2f}{xs[-1]:>11.2f}")

    # ═══════════════════════════════════════════════ quét ngưỡng
    print("\n" + "=" * 78)
    print("BẢNG 4 — QUÉT NGƯỠNG THEO TỪNG TIẾNG")
    print("=" * 78)
    chon_ng: dict[str, float] = {}
    for nn in nns:
        vnb, tran = dong[nn]["vnb"], dong[nn]["tran"]
        bia = [h for h in vnb if h["bia"]]
        lanh = [h for h in vnb if not h["bia"]]
        print(f"\n  ### {NHAN_NN[nn]} — vnb {len(vnb)} mục "
              f"({len(bia)} bịa / {len(lanh)} lành) · TRẦN {len(tran)} mục")
        if not tran:
            print("     KHÔNG có arm TRẦN -> KHÔNG đặt được ngưỡng.")
            continue
        print(f"{'ngưỡng':>10}{'BẮT/bịa':>12}{'kêu oan/lành':>16}{'oan %':>8}"
              f"{'TRẦN kêu oan':>15}")
        thap = None
        for ng in LUOI_NGUONG:
            bat = sum(1 for h in bia if h["lan"] >= ng)
            oan = sum(1 for h in lanh if h["lan"] >= ng)
            t = sum(1 for h in tran if h["lan"] >= ng)
            if t == 0 and thap is None:
                thap = ng
            sao = "  <= THẤP NHẤT MÀ TRẦN IM" if (t == 0 and thap == ng) else ""
            print(f"{ng:>10.1f}{f'{bat}/{len(bia)}':>12}"
                  f"{f'{oan}/{len(lanh)}':>16}"
                  f"{100 * oan / max(1, len(lanh)):>7.1f}%"
                  f"{f'{t}/{len(tran)}':>15}{sao}")
        chon_ng[nn] = thap or 0.0
        # HAI NHÓM CÓ TÁCH KHÔNG — nói thẳng, không giả vờ có đường kẻ sạch
        if bia and lanh:
            tl, db = max(h["lan"] for h in lanh), min(h["lan"] for h in bia)
            print(f"     hai nhóm: lành cao nhất {tl:.2f} · bịa thấp nhất "
                  f"{db:.2f} -> "
                  + (f"TÁCH RỜI (trống {db - tl:.2f})" if db > tl
                     else "**CHỒNG NHAU** (không có đường kẻ sạch)"))
        else:
            print("     thiếu một nhóm -> **CHƯA ĐẶT ĐƯỢC NGƯỠNG** cho tiếng "
                  "này (bài học `ty_giu`: đừng đặt mò).")

    # ═══════════════════════════════════════════════ kết luận
    print("\n" + "=" * 78)
    print("BẢNG 5 — NGƯỠNG ĐANG DÙNG CÓ ĐÚNG CHO TỪNG TIẾNG KHÔNG")
    print("=" * 78)
    ng0 = doc_lan.NGUONG_LAN
    print(f"{'tiếng':<8}{'TRẦN kêu oan @' + str(ng0):>18}"
          f"{'thấp nhất mà TRẦN im':>24}{'kết luận':>26}")
    for nn in nns:
        tran = dong[nn]["tran"]
        if not tran:
            print(f"{NHAN_NN[nn]:<8}{'—':>18}{'—':>24}{'không có trần':>26}")
            continue
        t = sum(1 for h in tran if h["lan"] >= ng0)
        thap = chon_ng.get(nn) or 0.0
        kl = ("GIỮ 1,5" if t == 0 and thap <= ng0 else
              (f"PHẢI NÂNG lên {thap:.1f}" if t else "xem lại"))
        print(f"{NHAN_NN[nn]:<8}{f'{t}/{len(tran)}':>18}{thap:>24.1f}{kl:>26}")

    # 10 mục `lan` cao nhất mỗi tiếng — để NGƯỜI đọc ra kiểu hỏng
    for nn in nns:
        vnb = dong[nn]["vnb"]
        if not vnb:
            continue
        print(f"\n  6 mục `lan` cao nhất — {NHAN_NN[nn]}:")
        for h in sorted(vnb, key=lambda x: -x["lan"])[:6]:
            print(f"    lan {h['lan']:>5.2f} · {h['giay']:>5.1f}s / "
                  f"{h['n_chu']:>3} ký tự · bịa="
                  f"{'CÓ ' if h['bia'] else 'không'} · «{h['chu'][:26]}» -> "
                  f"«{h['chep'][:38]}»")

    KQ.write_text(json.dumps(
        {"cham": tat, "chen_min": chen_min, "chon_nguong": chon_ng,
         "nguong_dang_dung": ng0, "mau": str(mau),
         "luc": time.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    MOC.write_text(json.dumps(
        {"nguon": "_do_lan_nn.py", "chen_min": chen_min,
         "chon_nguong": chon_ng,
         "arm": {f"{k}_{nn}": [{"loai": h["loai"], "lan": h["lan"],
                                "bia": h["bia"], "nn": nn}
                               for h in dong[nn][v]]
                 for nn in nns for k, v in (("VNB", "vnb"), ("EDG", "tran"))}},
        ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\nSố thô: {KQ}\nBản gọn (cổng 92 đọc, CÓ theo dõi git): {MOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
