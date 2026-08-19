# -*- coding: utf-8 -*-
"""RA BẢNG cho phép đo 5 tiếng — và **ĐẶT NGƯỠNG BẰNG SỐ**.

Đọc ``bq_do_5_tieng/ket_qua.json`` (do ``_do_5_tieng.py`` sinh) rồi trả lời
đúng ba câu anh Hùng hỏi:

1. **Giọng nào đọc được mấy trong 5 tiếng**, kèm % đọc sai từng tiếng và TRẦN.
2. **Bao nhiêu giọng mang nhãn "Multilingual" mà đo ra KHÔNG đọc được tiếng
   Việt.**
3. **Trong câu và đọc rời chênh nhau bao nhiêu.**

═══════════════════════════════════════════════════════════════════════════
NGƯỠNG PHẢI TÁCH ĐƯỢC HAI NHÓM, KHÔNG THÌ NÓI THẲNG LÀ CHƯA KẾT LUẬN ĐƯỢC
═══════════════════════════════════════════════════════════════════════════
Ngưỡng KHÔNG phải con số tròn nghĩ ra. Nó được suy ra từ hai nhóm đối chứng
đo trong CÙNG lượt, CÙNG tiếng, CÙNG bộ câu:

* **TRẦN** = giọng bản ngữ đọc tiếng của chính nó -> đây là mức sai mà máy
  nghe gây ra, không thể tốt hơn.
* **SÀN**  = giọng một-tiếng bị ép đọc tiếng khác -> hình dạng của một ca
  HỎNG THẬT.

Ngưỡng đặt ở **GIỮA KHOẢNG TRỐNG** giữa TRẦN cao nhất và SÀN thấp nhất. Nếu
hai nhóm **CHỒNG LẤN** thì bảng ghi thẳng *"CHƯA KẾT LUẬN ĐƯỢC"* cho tiếng
đó chứ không nặn ra một con số — ngưỡng không tách được hai nhóm thì nó
không phải ngưỡng, nó là lời phỏng đoán đội lốt số liệu.

**CẤM SO CHÉO TIẾNG:** mỗi tiếng có TRẦN/SÀN/ngưỡng RIÊNG. vi/en chấm theo
TỪ, ko/ja/zh chấm theo KÝ TỰ — hai đơn vị khác nhau.

Chạy: .venv\\Scripts\\python -u _ra_bang_5_tieng.py [--md]
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

from _bo_cau_thu_doc import NHAN_NN                            # noqa: E402

HOP = REPO / "bq_do_5_tieng"
KQ = HOP / "ket_qua.json"
CACHE = HOP / "cache.json"
NN5 = ("vi", "en", "ko", "ja", "zh")

#: Cột dùng để KẾT LUẬN. `tr` = ĐỌC RỜI (token một mình) — máy nghe không còn
#: ngữ cảnh để chữa hộ máy đọc. Xem docstring `_do_5_tieng`.
#:
#: **NHƯNG CỘT NÀY KHÔNG TÁCH ĐƯỢC Ở MỌI TIẾNG, VÀ ĐÓ LÀ SỐ ĐO:** tên riêng
#: bản địa tiếng Việt (`Nguyễn Huệ`, `Đắk Lắk`) đọc RỜI thì **chính giọng bản
#: ngữ cũng sai 50-75%** (HoaiMy 2/4 · NamMinh 3/4) — tức TRẦN đã sát SÀN.
#: Vì vậy bảng đặt ngưỡng cho **CẢ HAI** cột và nói rõ cột nào tách được ở
#: tiếng nào. Cột `cau` (sai chữ trên câu bản ngữ TRƠN) tách rất sạch:
#: TRẦN 0-3,9% so với SÀN 45-117%.
COT_KET_LUAN = "tr"

#: Cột phụ trợ — sai chữ trên câu thường. Dùng khi cột `tr` chồng lấn.
COT_LUI = "cau"


def nap() -> dict[str, list[dict]]:
    """Đọc **`cache.json`** rồi CHẤM LẠI — một nguồn sự thật duy nhất.

    **LỖI ĐÃ SẬP, ĐỪNG QUAY LẠI ĐỌC `ket_qua.json`:** `_do_5_tieng.py` chạy
    theo NHÓM (`tran,san` rồi `dich` rồi `ngoai`) và mỗi lượt **GHI ĐÈ**
    `ket_qua.json` bằng đúng những arm của lượt đó. Nên đọc file ấy sau lượt
    `dich` là mất sạch TRẦN và SÀN -> `nguong()` không đặt được ngưỡng nào ->
    **cả bảng ra dấu `?`**, trông y hệt "phép đo không kết luận được gì" trong
    khi số liệu vẫn còn nguyên trên đĩa.

    `cache.json` giữ bản ghi THÔ của MỌI arm đã chạy (chép lời, token, cờ đọc
    được) nên chấm lại từ đó vừa đủ mọi arm, vừa cho phép đổi cách chấm mà
    KHÔNG phải đọc lại 103 arm bằng edge-tts + Groq.
    """
    if not CACHE.exists():
        print(f"CHƯA CÓ {CACHE} — chạy `_do_5_tieng.py` trước.")
        raise SystemExit(2)
    from _do_5_tieng import cham
    tho = json.loads(CACHE.read_text(encoding="utf-8"))
    ra: dict[str, list[dict]] = {}
    for _khoa, kq in tho.items():
        if not isinstance(kq, dict) or "arm" not in kq:
            continue
        ra.setdefault(kq["arm"], []).append(cham(kq))
    if not ra:
        print(f"{CACHE} không có arm nào đọc được.")
        raise SystemExit(2)
    KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    return ra


def _ty(rs: list[dict], cot: str) -> float:
    """% sai của cột token (`tc` trong câu / `tr` đọc rời), gộp mọi vòng.

    **MẪU SỐ CHỈ GỒM TOKEN ĐỌC ĐƯỢC.** Token hỏng vì mạng/edge-tts chặn tốc
    độ nằm ở cột `*_hong` riêng — gộp vào đây là biến một sự cố dịch vụ thành
    kết luận *"giọng này không đọc được tiếng đó"*.
    """
    sai = sum(r[f"{cot}_sai"] for r in rs)
    n = sum(r[f"{cot}_n"] for r in rs)
    return 100.0 * sai / n if n else float("nan")


def _hong(rs: list[dict]) -> int:
    return sum(r.get("hong_cau", 0) + r.get("tc_hong", 0) + r.get("tr_hong", 0)
               for r in rs)


def _cau(rs: list[dict]) -> float:
    xs = [r["sai_cau"] for r in rs if r["sai_cau"] == r["sai_cau"]]
    return st.mean(xs) if xs else float("nan")


def gom(tat: dict) -> dict:
    """arm -> {voice, nn, nhom, sai_cau, tc%, tr%, nhãn nn, nguồn}."""
    ra = {}
    for ten, rs in tat.items():
        if not rs:
            continue
        ra[ten] = {
            "voice": rs[0]["voice"], "nn": rs[0]["nn"],
            "nguon": rs[0].get("nguon_that", "?"),
            "nhom": ten.split("_")[0],
            "cau": _cau(rs), "tc": _ty(rs, "tc"), "tr": _ty(rs, "tr"),
            "hong": _hong(rs),
            "tr_n": sum(r["tr_n"] for r in rs),
            "n_cau": sum(r["n_cau"] for r in rs),
            "nn_dung": sum(r["nn_dung"] for r in rs),
            "nn_n": sum(r["nn_n"] for r in rs),
            "nn_khac": sorted({x for r in rs for x in r["nn_khac"]}),
            "vong": len(rs),
        }
    return ra


# ---------------------------------------------------------------------------
# NGƯỠNG
# ---------------------------------------------------------------------------
def nguong(g: dict, cot: str) -> dict[str, dict]:
    """Ngưỡng từng tiếng, suy từ TRẦN và SÀN đo trong CÙNG lượt."""
    ra = {}
    for nn in NN5:
        tran = [v[cot] for v in g.values()
                if v["nhom"] == "TRAN" and v["nn"] == nn and v[cot] == v[cot]]
        san = [v[cot] for v in g.values()
               if v["nhom"] == "SAN" and v["nn"] == nn and v[cot] == v[cot]]
        if not tran or not san:
            ra[nn] = {"tran": tran, "san": san, "nguong": None,
                      "vi_sao": "thiếu TRẦN hoặc SÀN -> không đặt được ngưỡng"}
            continue
        t_max, s_min = max(tran), min(san)
        if t_max < s_min:
            ra[nn] = {
                "tran": tran, "san": san,
                "nguong": (t_max + s_min) / 2.0,
                "vi_sao": (f"TRẦN cao nhất {t_max:.1f}% < SÀN thấp nhất "
                           f"{s_min:.1f}% -> hai nhóm TÁCH RỜI, ngưỡng đặt "
                           f"giữa khoảng trống {s_min - t_max:.1f} điểm"),
            }
        else:
            ra[nn] = {
                "tran": tran, "san": san, "nguong": None,
                "vi_sao": (f"CHỒNG LẤN: TRẦN cao nhất {t_max:.1f}% >= SÀN "
                           f"thấp nhất {s_min:.1f}% -> CHƯA KẾT LUẬN ĐƯỢC "
                           f"cho tiếng này"),
            }
    return ra


def chon_cot(ngt: dict, ngc: dict) -> dict[str, str]:
    """Tiếng nào có ngưỡng ở cột nào: ``"tr"`` · ``"cau"`` · ``"tr+cau"`` ·
    ``""`` (không cột nào tách được -> không chấm tiếng đó)."""
    ra = {}
    for nn in NN5:
        co_tr = ngt[nn].get("nguong") is not None
        co_cau = ngc[nn].get("nguong") is not None
        ra[nn] = ("tr+cau" if (co_tr and co_cau) else
                  "tr" if co_tr else "cau" if co_cau else "")
    return ra


def doc_duoc(v: float, ng: dict) -> str | None:
    """'CÓ' / 'KHÔNG' / None (chưa kết luận được)."""
    if ng.get("nguong") is None or v != v:
        return None
    return "CÓ" if v < ng["nguong"] else "KHÔNG"


def phan_xu(v: dict, nn: str, NG: dict) -> tuple[str | None, str]:
    """Kết luận cho MỘT (giọng × tiếng): ('CÓ'/'KHÔNG'/None, lý do).

    **HAI THƯỚC PHẢI ĐỒNG Ý, KHÔNG THÌ KHÔNG KẾT LUẬN.** Đây là chỗ lượt đo
    này đổi ý và nó đổi vì SỐ, không vì sở thích:

    Bản đầu chấm bằng cột ĐỌC RỜI (đúng lời đề bài) và lấy cột câu thường làm
    đường lùi. Nhưng dữ liệu tiếng Việt bác cách đó:

    * ``en-US-AvaMultilingual`` đọc câu Việt TRƠN sai **0,0%** (bằng TRẦN) mà
      **4/4 tên riêng đọc RỜI đều sai** -> cột đọc rời gọi nó là "KHÔNG đọc
      được tiếng Việt", cột câu gọi nó là "đọc tốt như giọng bản ngữ".
    * mà chính TRẦN tiếng Việt (``vi-VN-HoaiMy`` 2/4 · ``NamMinh`` 3/4) cũng
      sai 50-75% ở cột đọc rời. Tức phần lớn cái "sai" đó là **máy NGHE không
      chép nổi một tên riêng Việt đứng một mình**, không phải máy ĐỌC sai.

    Chọn một trong hai cột làm quan toà là tự chọn một kết luận. Đòi hai cột
    ĐỒNG Ý thì: khớp -> kết luận có căn cứ kép; đá nhau -> **nói thẳng là chưa
    kết luận được**, và đó là câu trả lời ĐÚNG cho ca Ava.

    Cột nào KHÔNG có ngưỡng (TRẦN chồng SÀN) thì không được bỏ phiếu.
    """
    # MÁY ĐỌC TỪ CHỐI HẲN — KHÁC "chưa kết luận", và nó là ca AN TOÀN NHẤT.
    # `vi-VN-HoaiMy` + chữ Hàn/Nhật/Trung: edge-tts thử 4 lần rồi trả file
    # 0 byte, **11/11 mẫu đều hỏng** ở cả 3 tiếng (mỗi arm ~300 giây backoff).
    # Đó không phải mạng chập chờn (arm tiếng Anh của CÙNG giọng chạy ngon
    # trong 46 giây) mà là dịch vụ TỪ CHỐI. Với người dùng, hậu quả là **lượt
    # xuất không ra tiếng** chứ không phải ra chữ vô nghĩa — tức app FAIL TO
    # thay vì im lặng, đúng thứ repo này luôn muốn. Gọi nó là "chưa kết luận"
    # là bỏ mất một kết luận CHẮC CHẮN.
    if v.get("hong", 0) > 0 and v.get("tr_n", 0) == 0 and v.get("n_cau", 0) == 0:
        return "KHÔNG", (f"MÁY ĐỌC KHÔNG RA TIẾNG NÀO ({v['hong']} mẫu hỏng "
                         f"hết) -> chọn giọng này cho tiếng đó là lượt xuất "
                         f"KHÔNG CÓ TIẾNG")
    kq_tr = doc_duoc(v["tr"], NG["tr"][nn])
    kq_cau = doc_duoc(v["cau"], NG["cau"][nn])
    co = [x for x in (kq_tr, kq_cau) if x is not None]
    if not co:
        return None, "không cột nào chấm được"
    if kq_tr is not None and kq_cau is not None:
        if kq_tr == kq_cau:
            return kq_tr, "hai thước đồng ý"
        return None, (f"HAI THƯỚC ĐÁ NHAU: đọc rời -> {kq_tr} "
                      f"({v['tr']:.0f}%) · câu thường -> {kq_cau} "
                      f"({v['cau']:.0f}%)")
    return co[0], ("chỉ cột đọc rời chấm được" if kq_tr is not None
                   else "chỉ cột câu thường chấm được")


# ---------------------------------------------------------------------------
def main() -> int:
    tat = nap()
    g = gom(tat)
    ng_tr = nguong(g, "tr")
    ng_cau = nguong(g, "cau")
    cot_cua = chon_cot(ng_tr, ng_cau)
    NG = {"tr": ng_tr, "cau": ng_cau}

    print("=" * 78)
    print("BẢNG 0 — TRẦN · SÀN · NGƯỠNG cho TỪNG TIẾNG")
    print("=" * 78)
    print("TRẦN = giọng bản ngữ đọc tiếng của nó (mức sai do MÁY NGHE gây ra)")
    print("SÀN  = giọng một-tiếng bị ép đọc tiếng khác (hình dạng ca HỎNG "
          "THẬT)")
    print("Ngưỡng đặt GIỮA khoảng trống TRẦN-SÀN. Chồng lấn -> KHÔNG ĐẶT.")
    for nn in NN5:
        print(f"\n  ── {NHAN_NN[nn]} ──")
        for cot, ten in (("tr", "ĐỌC RỜI  "), ("cau", "câu thường")):
            d = NG[cot][nn]
            tr = " · ".join(f"{x:.0f}" for x in sorted(d["tran"])) or "-"
            sa = " · ".join(f"{x:.0f}" for x in sorted(d["san"])) or "-"
            nv = (f"ngưỡng {d['nguong']:.1f}%" if d["nguong"] is not None
                  else "KHÔNG ĐẶT")
            dung = "  <== DÙNG CỘT NÀY" if cot_cua[nn] == cot else ""
            print(f"     {ten}  TRẦN [{tr}]  SÀN [{sa}]  -> {nv}{dung}")
            print(f"        {d['vi_sao']}")
        if not cot_cua[nn]:
            print("     *** CẢ HAI CỘT CHỒNG LẤN -> CHƯA KẾT LUẬN ĐƯỢC cho "
                  "tiếng này ***")
        # ĐỘ PHÂN GIẢI: cột ĐỌC RỜI chỉ có 4 token/arm nên nó chỉ nhận được
        # các giá trị 0/25/50/75/100%. Ngưỡng nằm cách TRẦN dưới một bước
        # (25 điểm) thì phép chấm thực chất chỉ phân biệt được "sai HẾT" với
        # "sai gần hết" — vẫn dùng được, nhưng phải nói ra chứ đừng để người
        # đọc tưởng con số 87,5% là một ranh giới tinh tế.
        d = NG["tr"][nn]
        if cot_cua[nn] == "tr" and d.get("nguong") is not None:
            n_tok = max((v["tr_n"] for v in g.values() if v["nn"] == nn),
                        default=0)
            buoc = 100.0 / n_tok if n_tok else 0.0
            cach = d["nguong"] - max(d["tran"])
            if buoc and cach <= buoc * 1.01:
                print(f"     ! ĐỘ PHÂN GIẢI THÔ: mỗi arm chỉ {n_tok} token "
                      f"-> bước {buoc:.0f} điểm; ngưỡng chỉ cách TRẦN "
                      f"{cach:.0f} điểm = ĐÚNG MỘT BƯỚC.")
                print(f"       Nghĩa thực: chỉ arm sai HẾT token mới bị gọi "
                      f"là KHÔNG đọc được. Cột `câu thường` "
                      f"(khoảng trống {NG['cau'][nn]['nguong'] is not None and (min(NG['cau'][nn]['san']) - max(NG['cau'][nn]['tran'])) or 0:.0f} điểm) "
                      f"mịn hơn — đọc kèm.")

    # ---------------------------------------------------------- bảng chính
    print("\n" + "=" * 78)
    print("BẢNG 1 — GIỌNG NÀO ĐỌC ĐƯỢC MẤY TRONG 5 TIẾNG")
    print("=" * 78)
    print("mỗi ô = «% ĐỌC RỜI sai / % sai chữ trên câu thường»")
    print("dấu sau ô: (trống) = ĐỌC ĐƯỢC · x = KHÔNG đọc được · ? = chưa kết "
          "luận được (hai thước đá nhau)")
    print("kết luận chỉ khi HAI thước ĐỒNG Ý — xem `phan_xu.__doc__`")
    da_nhau: list[tuple[str, str, str]] = []
    voices: dict[str, dict] = {}
    for v in g.values():
        voices.setdefault(v["voice"], {})[v["nn"]] = v
    h = f"{'giọng':40s}{'nguồn':11s}" + "".join(f"{NHAN_NN[n]:>10s}"
                                               for n in NN5) + "  đọc được"
    print(h)
    print("-" * len(h))
    thong_ke: dict[str, list[str]] = {}
    for voice in sorted(voices, key=lambda x: (
            0 if "multilingual" in x.lower() else 1, x)):
        hang = voices[voice]
        if not any(n in hang for n in NN5):
            continue
        o, dem, nguon = [], 0, "?"
        for nn in NN5:
            v = hang.get(nn)
            if not v:
                o.append(f"{'-':>10s}")
                continue
            nguon = v["nguon"]
            kq, ly = phan_xu(v, nn, NG)
            dau = {"CÓ": " ", "KHÔNG": "x", None: "?"}[kq]
            if kq == "CÓ":
                dem += 1
            thong_ke.setdefault(voice, []).append(f"{nn}:{kq}")
            if "ĐÁ NHAU" in ly:
                da_nhau.append((voice, nn, ly))
            # in CẢ HAI cột: rời/câu — người đọc tự thấy hai thước có khớp
            tr = "NA" if v["tr"] != v["tr"] else f"{v['tr']:.0f}"
            ca = "NA" if v["cau"] != v["cau"] else f"{v['cau']:.0f}"
            o.append(f"{tr:>3s}/{ca:>3s}{dau} ")
        ten = voice if len(voice) <= 39 else voice[:36] + "..."
        print(f"{ten:40s}{nguon:11s}" + "".join(o) + f"  {dem}/5")

    # --------------------------------------- câu hỏi 2: nhãn Multilingual
    print("\n" + "=" * 78)
    print("BẢNG 2 — NHÃN \"Multilingual\" CÓ PHẢI BẰNG CHỨNG KHÔNG")
    print("=" * 78)
    ml = [v for v in voices if "multilingual" in v.lower()]

    if da_nhau:
        print(f"\n  HAI THƯỚC ĐÁ NHAU ở {len(da_nhau)} ô -> KHÔNG kết luận "
              f"những ô đó (đây là câu trả lời ĐÚNG, không phải lỗi):")
        for voice, nn, ly in da_nhau[:12]:
            print(f"    {voice:42s} {NHAN_NN[nn]:6s} {ly}")
        if len(da_nhau) > 12:
            print(f"    ... còn {len(da_nhau)-12} ô nữa")

    def _kq(voice: str, nn: str) -> str | None:
        v = voices.get(voice, {}).get(nn)
        return phan_xu(v, nn, NG)[0] if v else None

    for nn in NN5:
        co = khong = chua = 0
        for voice in ml:
            if nn not in voices[voice]:
                continue
            kq = _kq(voice, nn)
            co += kq == "CÓ"
            khong += kq == "KHÔNG"
            chua += kq is None
        _c = {"tr+cau": "cả hai thước", "tr": "chỉ ĐỌC RỜI",
              "cau": "chỉ câu thường", "": "KHÔNG cột nào"}[cot_cua[nn]]
        print(f"  {NHAN_NN[nn]:6s}: đọc được {co:2d} · KHÔNG đọc được "
              f"{khong:2d} · chưa kết luận {chua:2d}   (trên {len(ml)} giọng "
              f"mang nhãn · có ngưỡng ở: {_c})")
    xau_vi = [v for v in ml if _kq(v, "vi") == "KHÔNG"]
    print(f"\n  *** {len(xau_vi)}/{len(ml)} giọng mang nhãn \"Multilingual\" "
          f"ĐO RA KHÔNG ĐỌC ĐƯỢC TIẾNG VIỆT ***")
    for v in sorted(xau_vi):
        d = voices[v]["vi"]
        print(f"      {v:44s} đọc rời {d['tr']:5.0f}%  trong câu "
              f"{d['tc']:5.0f}%  sai câu {d['cau']:5.1f}%")
    du5 = [v for v in ml if all(_kq(v, n) == "CÓ" for n in NN5)]
    print(f"\n  Giọng mang nhãn mà đo ra ĐỌC ĐƯỢC CẢ 5 TIẾNG: {len(du5)}"
          f"/{len(ml)}" + (f" — {', '.join(sorted(du5))}" if du5 else ""))

    # --------------------------------- câu hỏi 3: trong câu vs đọc rời
    print("\n" + "=" * 78)
    print("BẢNG 3 — MÁY NGHE CHỮA HỘ MÁY ĐỌC BAO NHIÊU (trong câu vs đọc rời)")
    print("=" * 78)
    print(f"{'nhóm':10s}{'tiếng':8s}{'TRONG CÂU':>11s}{'ĐỌC RỜI':>10s}"
          f"{'chênh':>8s}")
    print("-" * 47)
    for nhom in ("TRAN", "SAN", "ML", "NGOAI"):
        for nn in NN5:
            xs = [v for v in g.values() if v["nn"] == nn
                  and (v["nhom"] == nhom
                       or (nhom == "NGOAI" and v["nhom"] in
                           ("VN", "PIPER", "OV", "CB")))]
            if not xs:
                continue
            tc = [x["tc"] for x in xs if x["tc"] == x["tc"]]
            tr = [x["tr"] for x in xs if x["tr"] == x["tr"]]
            if not (tc and tr):
                continue
            print(f"{nhom:10s}{NHAN_NN[nn]:8s}{st.mean(tc):10.1f}%"
                  f"{st.mean(tr):9.1f}%{st.mean(tr)-st.mean(tc):+8.1f}")
    tc_a = [v["tc"] for v in g.values() if v["tc"] == v["tc"]]
    tr_a = [v["tr"] for v in g.values() if v["tr"] == v["tr"]]
    if tc_a and tr_a:
        print("-" * 47)
        print(f"{'TẤT CẢ':10s}{'':8s}{st.mean(tc_a):10.1f}%"
              f"{st.mean(tr_a):9.1f}%{st.mean(tr_a)-st.mean(tc_a):+8.1f}")
        print("\n  Đây là lý do KHÔNG được kết luận bằng cột TRONG CÂU: Groq "
              "whisper là mô hình\n  ngôn ngữ, có ngữ cảnh thì nó ĐOÁN RA chữ "
              "đúng dù máy đọc phát âm sai.")

    # ------------------------------------------------- nhãn ngôn ngữ (phụ)
    print("\n" + "=" * 78)
    print("BẢNG 4 — THƯỚC PHỤ ĐỘC LẬP: máy nghe TỰ ĐOÁN ra tiếng gì")
    print("=" * 78)
    print("(hỏi `language=None`; trả lời câu \"tiếng phát ra NGHE có giống "
          "tiếng này không\",\n khác hẳn câu \"chữ có đúng không\" — hai "
          "thước sai khác nhau thì phải xem lại)")
    xau = []
    for voice in sorted(voices):
        for nn in NN5:
            v = voices[voice].get(nn)
            if v and v["nn_n"] and v["nn_dung"] < v["nn_n"]:
                xau.append((voice, nn, v))
    if not xau:
        print("  mọi arm đều được máy nghe gán ĐÚNG tiếng.")
    for voice, nn, v in xau[:40]:
        print(f"  {voice:42s} {NHAN_NN[nn]:6s} {v['nn_dung']}/{v['nn_n']} "
              f"đúng · nghe ra: {', '.join(v['nn_khac'][:4])}")
    if len(xau) > 40:
        print(f"  ... còn {len(xau)-40} dòng nữa")

    # ------------------------------------------------------------- xuất
    ra = {"nguong_doc_roi": ng_tr, "nguong_cau": ng_cau,
          "cot_dung_cho_tung_tieng": cot_cua,
          "giong": {v: thong_ke.get(v, []) for v in voices}}
    (KQ.parent / "ket_luan.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {KQ.parent / 'ket_luan.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
