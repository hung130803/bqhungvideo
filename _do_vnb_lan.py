# -*- coding: utf-8 -*-
"""HIỆU CHUẨN BỘ DÒ "CÂU LAN MAN" CỦA GIỌNG NHÂN BẢN VieNeu (`vnb:`).

Lượt đo 26/08 kết luận: bệnh của `vnb:` đọc tiếng Anh **KHÔNG phải "đọc sai
tiếng Anh"** mà là **KHÔNG ĐỀU** — cùng chữ, cùng file mẫu, hai lượt ra
`WER 3,1% · bịa 0,3%` và `WER 12,7% · bịa 9,7%`. Vì cái hỏng NGẪU NHIÊN theo
lượt nên **đọc lại** có cơ sở ăn thật; nhưng đọc lại chỉ có nghĩa khi có một
bộ dò chỉ ĐÚNG câu hỏng.

File này KHÔNG đọc lại gì cả — nó chỉ trả lời một câu: **ngưỡng nào tách được
câu lành với câu bịa, và tách có SẠCH không.**

═══════════════════════════════════════════════════════════════════════════
SỰ THẬT ĐỐI CHỨNG LẤY TỪ ĐÂU (và vì sao nó KHÔNG phải là bộ dò)
═══════════════════════════════════════════════════════════════════════════
"Câu này có bị bịa không" chấm bằng **BẢN CHÉP NGƯỢC** đã có sẵn trong
`_do_vn_en/cache.json` (Groq nghe lại chính file tiếng mà arm đó vừa đọc):

  · `chen` — số từ máy TỰ THÊM, gióng hàng Levenshtein CÓ TRUY VẾT
    (`_do_adam_en.dem_op`).
  · `_has_cjk` — câu tiếng Anh mà chép ngược ra **chữ Hán** = bịa chắc chắn
    («2026» -> `在英雄城的美索`). Dùng lại `recap._has_cjk`, không viết bộ thứ hai.
  · `lap` — cụm lặp nhiều lần trong một câu («OST» ra một câu Trung lặp 3 lần).

**BA THỨ ĐÓ ĐỀU CẦN ASR — TỐN LƯỢT GROQ, KHÔNG DÙNG ĐƯỢC LÚC SẢN XUẤT.** Nên
chúng chỉ đóng vai **SỰ THẬT ĐỐI CHỨNG**. Cái đem đi dò lúc chạy thật phải là
tín hiệu MIỄN PHÍ: **giây/ký tự của câu so với TRUNG VỊ của chính loạt ấy**
(độ dài WAV thì máy đọc đã trả về sẵn).

So hằng số là SAI ở đây: `giong_chatter` đã đo được *"MẪU kéo nhịp đọc"* —
cùng 12 câu, mẫu này 1,03x mẫu kia 1,32x. Nhịp là của LOẠT, không phải của
tiếng.

═══════════════════════════════════════════════════════════════════════════
ĐỌC BẢNG: PHÂN BỐ HAI NHÓM, KHÔNG PHẢI MỘT CON SỐ
═══════════════════════════════════════════════════════════════════════════
Bảng in ra phân bố `lan` (bội số so trung vị) của **nhóm LÀNH** và **nhóm
BỊA** RIÊNG. Hai nhóm CHỒNG NHAU thì nói thẳng là **chưa đặt được ngưỡng** —
bài học `ty_giu` (cổng "camera cố định"): 1 điểm dữ liệu thì KHÔNG đặt ngưỡng,
và biên 2,3% thì không phải là ngưỡng, đó là sự trùng hợp.

Chạy:  .venv\\Scripts\\python -u _do_vnb_lan.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_adam_en as DA                                        # noqa: E402
from app.ai.recap import _has_cjk                               # noqa: E402
from app.core.doc_lan import lan_vuot, moc_nhip                 # noqa: E402
from app.core.thay_giong import probe_duration                  # noqa: E402

HOP = REPO / "_do_vn_en"
CACHE = HOP / "cache.json"
KQ = REPO / "_kq_vnb_lan.json"

#: BẢN GỌN, **CÓ THEO DÕI GIT** — cổng 92 CA 3 đọc file này.
#:
#: `_kq*.json` nằm trong `.gitignore`, nên nếu cổng đọc thẳng `KQ` thì trên máy
#: vừa clone (và trên máy dựng bản phát hành) nó **ĐỎ OAN vì KHO chứ không vì
#: MÃ** — đúng bệnh cổng 47 CA2 (*"chép lời lại mỗi lần chạy, kho video đổi thì
#: cổng nhấp nháy"*) và cổng 68 (*"`NGUON` ghi cứng tên file không còn trên
#: đĩa"*). Ngưỡng `doc_lan.NGUONG_LAN` được hiệu chuẩn trên MỘT lượt đo cụ thể,
#: nên bằng chứng của lượt đo ấy phải đi kèm mã, không nằm trong file rác.
#: Chỉ giữ 3 cột cổng thật sự chấm (`loai` · `lan` · `bia`) -> vài chục KB.
MOC = REPO / "_moc_doc_lan.json"

#: Arm đem hiệu chuẩn. `VNB_en` = đúng đường anh Hùng đi (`vnb:` × tiếng Anh).
#: `edge_en` là TRẦN — bộ dò mà kêu trên arm này là kêu OAN, vì đó là giọng
#: bản ngữ đọc đúng. KHÔNG có cột đó thì "bắt được 9/9" không nói lên gì.
ARM = {
    "VNB_en": "vnb: NHÂN BẢN qua VieNeu x ANH  <= ANH HÙNG ĐANG ĐI",
    "CB_en": "cb: NHÂN BẢN qua Chatterbox x ANH",
    "edge_en": "edge Aria x ANH (TRẦN — kêu ở đây là kêu OAN)",
}


def _lap_toi_da(chep: str) -> int:
    """Cụm dài nhất lặp lại bao nhiêu LẦN trong một bản chép. 1 = không lặp.

    Dò trên CHUỖI KÝ TỰ chứ không trên từ: câu bịa ra là tiếng Trung, mà tiếng
    Trung KHÔNG có dấu cách nên tách theo từ ra một token (đúng bệnh
    `.split()` cổng 52/54). Cụm tối thiểu 4 ký tự cho khỏi đếm nhầm dấu câu.
    """
    s = re.sub(r"\s+", "", str(chep or ""))
    if len(s) < 8:
        return 1
    tot = 1
    for w in range(4, len(s) // 2 + 1):
        for i in range(0, len(s) - w + 1):
            cum = s[i:i + w]
            n = 1
            j = i + w
            while s[j:j + w] == cum:
                n += 1
                j += w
            tot = max(tot, n)
    return tot


#: Hệ chữ mà bản chép ngược **KHÔNG ĐƯỢC PHÉP** có, theo ngôn ngữ đích.
#:
#: Luật tiếng Anh (*"chép ngược ra chữ Hán = bịa chắc chắn"*) **KHÔNG bê thẳng
#: sang tiếng Trung/Nhật được**: ở đó chữ Hán là chữ ĐÚNG, bê sang là gán oan
#: 100% số câu. Đây đúng họ bẫy `料理` của cổng 52 (chữ Hán dùng chung mặt chữ,
#: khác nghĩa) — chỉ khác chiều. Tiếng **Hàn** vẫn gặp hanja trong văn bản thật
#: nên chữ Hán KHÔNG kể là bịa; chỉ kana mới là dấu hiệu.
LA_HE_CHU: dict[str, tuple[str, ...]] = {
    "en": ("han", "kana", "hangul"),
    "vi": ("han", "kana", "hangul"),
    "zh": ("kana", "hangul"),
    "ja": ("hangul",),
    "ko": ("kana",),
}


def _la_he_chu(chep: str, nn: str) -> bool:
    """Bản chép có hệ chữ LẠ với ngôn ngữ đích không. Hàm thuần."""
    from app.ai.recap import _HAN_RE, _HANGUL_RE, _KANA_RE
    s = str(chep or "")
    bo = {"han": _HAN_RE, "kana": _KANA_RE, "hangul": _HANGUL_RE}
    return any(bo[k].search(s) for k in LA_HE_CHU.get(nn, ("han",)))


def _hang(kq: dict, tien_to: str, khoa_chu: str, nn: str = "en",
          chen_min: int = 2) -> list[dict]:
    """Trải một arm-lượt thành danh sách câu/token có đủ số đo.

    `nn` = ngôn ngữ ĐÍCH của arm (quyết định hệ chữ nào là LẠ) · `chen_min` =
    số từ máy TỰ THÊM để coi là bịa. Mặc định `("en", 2)` giữ NGUYÊN hành vi
    của lượt hiệu chuẩn tiếng Anh — `_moc_doc_lan.json` không đổi một dòng.
    """
    ra = []
    goc = HOP / f"{kq['arm']}_v{kq['vong']}"
    ds = kq["cau"] if tien_to == "c" else kq["tok"]
    for i, h in enumerate(ds):
        if not h.get("doc_duoc"):
            continue
        f = goc / f"{tien_to}{i:03d}.mp3"
        if not f.exists():
            continue
        giay = probe_duration(f)
        chu = str(h[khoa_chu] or "")
        chep = str(h.get("chep") or "")
        if giay <= 0 or not chu.strip():
            continue
        thay, chen, thieu, tong = DA.dem_op(chu, chep)
        lap = _lap_toi_da(chep)
        # `_has_cjk` chỉ đúng khi ĐÍCH không dùng CJK — xem `LA_HE_CHU`.
        cjk = bool(_has_cjk(chep)) if nn in ("en", "vi") \
            else _la_he_chu(chep, nn)
        ra.append({
            "loai": tien_to, "i": i, "chu": chu, "chep": chep, "nn": nn,
            "giay": round(giay, 3), "n_chu": len(chu.strip()),
            "chen": chen, "thay": thay, "tu": tong, "lap": lap, "cjk": cjk,
            # SỰ THẬT ĐỐI CHỨNG. Ba dấu hiệu, OR lại: chỉ cần một cái đúng là
            # câu đó đã hỏng theo cách anh Hùng nghe ra ("máy tự thêm chữ").
            # Ngưỡng `chen >= 2` chứ không phải `>= 1`: chép ngược tự nó có
            # nhiễu (edge-tts TRẦN cũng ra bịa 0,9%), 1 từ thêm nằm trong dải
            # nhiễu đó -> lấy 1 làm mốc là gán oan cho cả nhóm lành.
            "bia": bool(cjk or lap >= 3 or chen >= chen_min),
        })
    return ra


def main() -> int:
    if not CACHE.exists():
        print(f"KHÔNG có {CACHE} — chạy `_do_vnb_en.py` trước.")
        return 2
    cache = json.loads(CACHE.read_text(encoding="utf-8"))

    print("=" * 78)
    print("HIỆU CHUẨN BỘ DÒ CÂU LAN MAN — `vnb:` VieNeu đọc tiếng Anh")
    print("=" * 78)

    tat: dict[str, list[dict]] = {}
    for khoa, kq in cache.items():
        ten = kq.get("arm") or khoa.split("|")[0]
        if ten not in ARM:
            continue
        hs = _hang(kq, "c", "cau") + _hang(kq, "t", "token")
        if not hs:
            continue
        # MỐC KHỚP TỪ CHÍNH LOẠT ẤY — không so hằng số.
        a, b = moc_nhip([h["chu"] for h in hs], [h["giay"] for h in hs])
        for h in hs:
            h["gc"] = round(h["giay"] / max(1, h["n_chu"]), 4)
            h["lan"] = lan_vuot(h["chu"], h["giay"], a, b)
        tat.setdefault(ten, []).extend(hs)
        print(f"\n[{ten} v{kq['vong']}] {len(hs)} mục · mốc nhịp = "
              f"{a:.3f} + {b:.4f}*ký_tự")

    # ---------------------------------------------------------- PHÂN BỐ
    print("\n" + "=" * 78)
    print("BẢNG 1 — PHÂN BỐ `lan` (bội số so TRUNG VỊ của chính loạt)")
    print("=" * 78)
    print(f"{'arm / nhóm':<44}{'n':>5}{'nhỏ nhất':>11}{'trung vị':>11}"
          f"{'bpv90':>9}{'lớn nhất':>11}")
    moc: dict[str, dict] = {}
    for ten in ARM:
        hs = tat.get(ten) or []
        if not hs:
            continue
        for nhan, loc in (("LÀNH", lambda h: not h["bia"]),
                          ("BỊA ", lambda h: h["bia"])):
            xs = sorted(h["lan"] for h in hs if loc(h))
            if not xs:
                print(f"  {ten} · {nhan:<36}{0:>5}{'—':>11}{'—':>11}"
                      f"{'—':>9}{'—':>11}")
                continue
            bpv90 = xs[min(len(xs) - 1, int(0.90 * len(xs)))]
            print(f"  {ten} · {nhan:<36}{len(xs):>5}{xs[0]:>11.2f}"
                  f"{st.median(xs):>11.2f}{bpv90:>9.2f}{xs[-1]:>11.2f}")
            moc.setdefault(ten, {})[nhan.strip()] = {
                "n": len(xs), "min": xs[0], "med": st.median(xs),
                "p90": bpv90, "max": xs[-1]}

    # -------------------------------------------------- HAI NHÓM CÓ TÁCH KHÔNG
    print("\n" + "=" * 78)
    print("BẢNG 2 — HAI NHÓM CÓ **TÁCH RỜI** KHÔNG (khoảng trống ở giữa)")
    print("=" * 78)
    for ten in ARM:
        m = moc.get(ten) or {}
        if "LÀNH" not in m or "BỊA" not in m:
            print(f"  {ten}: thiếu một nhóm -> KHÔNG kết luận được")
            continue
        tren_lanh, duoi_bia = m["LÀNH"]["max"], m["BỊA"]["min"]
        if duoi_bia > tren_lanh:
            print(f"  {ten}: TÁCH RỜI — lành cao nhất {tren_lanh:.2f} < "
                  f"bịa thấp nhất {duoi_bia:.2f} (trống {duoi_bia - tren_lanh:.2f})")
        else:
            print(f"  {ten}: **CHỒNG NHAU** — lành cao nhất {tren_lanh:.2f} "
                  f">= bịa thấp nhất {duoi_bia:.2f}. Không có ngưỡng nào tách "
                  f"sạch; phải chấm bằng BẮT/BỎ SÓT ở bảng 3.")

    # ----------------------------------------------------- QUÉT NGƯỠNG
    print("\n" + "=" * 78)
    print("BẢNG 3 — QUÉT NGƯỠNG: bắt được bao nhiêu / KÊU OAN bao nhiêu")
    print("=" * 78)
    hs = tat.get("VNB_en") or []
    tran = tat.get("edge_en") or []
    print(f"{'ngưỡng':>8}{'BẮT / tổng bịa':>18}{'bỏ sót':>9}"
          f"{'kêu oan / lành':>18}{'oan %':>8}{'TRẦN kêu oan':>15}")
    quet = []
    for ng in (1.2, 1.3, 1.4, 1.5, 1.8, 2.0, 2.5, 3.0, 4.0):
        bia = [h for h in hs if h["bia"]]
        lanh = [h for h in hs if not h["bia"]]
        bat = sum(1 for h in bia if h["lan"] >= ng)
        oan = sum(1 for h in lanh if h["lan"] >= ng)
        t_oan = sum(1 for h in tran if h["lan"] >= ng)
        quet.append({"nguong": ng, "bat": bat, "bia": len(bia), "oan": oan,
                     "lanh": len(lanh), "tran_oan": t_oan, "tran": len(tran)})
        print(f"{ng:>8.1f}{f'{bat}/{len(bia)}':>18}{len(bia) - bat:>9}"
              f"{f'{oan}/{len(lanh)}':>18}"
              f"{100 * oan / max(1, len(lanh)):>7.1f}%"
              f"{f'{t_oan}/{len(tran)}':>15}")

    # -------------------------------- CHỈ CÂU (thứ lượt sản xuất thật sự đọc)
    print("\n" + "=" * 78)
    print("BẢNG 3b — CHỈ CÂU (loại `c`). Lượt xuất thật đọc CÂU, không đọc")
    print("token trần; bảng 3 gộp cả token rời nên nó là ca KHÓ HƠN thực tế.")
    print("=" * 78)
    hc = [h for h in hs if h["loai"] == "c"]
    tc = [h for h in tran if h["loai"] == "c"]
    bia_c = [h for h in hc if h["bia"]]
    lanh_c = [h for h in hc if not h["bia"]]
    for ng in (1.3, 1.4, 1.5, 1.8, 2.0):
        print(f"  ngưỡng {ng:.1f}: bắt "
              f"{sum(1 for h in bia_c if h['lan'] >= ng)}/{len(bia_c)} · "
              f"kêu oan {sum(1 for h in lanh_c if h['lan'] >= ng)}/"
              f"{len(lanh_c)} · TRẦN kêu oan "
              f"{sum(1 for h in tc if h['lan'] >= ng)}/{len(tc)}")
    if bia_c and lanh_c:
        print(f"  câu LÀNH cao nhất {max(h['lan'] for h in lanh_c):.2f} · "
              f"câu BỊA {sorted(h['lan'] for h in bia_c)}")
        print("  -> CHỈ 2 câu bịa trên 68. Hai nhóm chỉ hở 0,04 — đó là TRÙNG "
              "HỢP,\n     không phải ngưỡng (bài học `ty_giu`). Ngưỡng chọn "
              "theo cột TRẦN.")

    # ------------------------------------------------- ba dấu hiệu, ai gánh
    print("\n" + "=" * 78)
    print("BẢNG 4 — SỰ THẬT ĐỐI CHỨNG ĐẾN TỪ DẤU HIỆU NÀO (arm VNB_en)")
    print("=" * 78)
    for nhan, loc in (("chữ Hán (`_has_cjk`)", lambda h: h["cjk"]),
                      ("lặp cụm >= 3 lần", lambda h: h["lap"] >= 3),
                      ("máy TỰ THÊM >= 2 từ", lambda h: h["chen"] >= 2)):
        n = sum(1 for h in hs if loc(h))
        print(f"  {nhan:<28}{n:>4} mục")
    print(f"  {'TỔNG (OR ba cái)':<28}{sum(1 for h in hs if h['bia']):>4}/"
          f"{len(hs)} mục")

    print("\n  10 mục `lan` cao nhất của arm VNB_en:")
    for h in sorted(hs, key=lambda x: -x["lan"])[:10]:
        print(f"    lan {h['lan']:>5.2f} · {h['giay']:>5.1f}s / "
              f"{h['n_chu']:>3} ký tự · bịa={'CÓ ' if h['bia'] else 'không'}"
              f" · «{h['chu'][:34]}» -> «{h['chep'][:40]}»")

    KQ.write_text(json.dumps(
        {"arm": {k: v for k, v in tat.items()}, "moc": moc, "quet": quet},
        ensure_ascii=False, indent=1), encoding="utf-8")
    MOC.write_text(json.dumps(
        {"nguon": "_do_vnb_lan.py", "arm": {
            k: [{"loai": h["loai"], "lan": h["lan"], "bia": h["bia"]}
                for h in v] for k, v in tat.items()}},
        ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"\nSố thô: {KQ}\nBản gọn (cổng 92 đọc, CÓ theo dõi git): {MOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
