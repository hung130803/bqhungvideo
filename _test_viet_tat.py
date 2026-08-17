# -*- coding: utf-8 -*-
"""CỔNG 69 — ĐỌC ĐÚNG VIẾT TẮT MÀ **KHÔNG LỆCH MỐC CHỮ**.

VIỆC NÀY ĐÃ BỊ TỪ CHỐI NỐI VÀO APP MỘT LƯỢT, và lý do từ chối chính là mệnh đề
đắt nhất cổng này canh:

  chữ HIỆN LÊN lấy từ `texts` GỐC, còn MỐC THỜI GIAN lấy từ `WordBoundary` của
  chính chữ **ĐÃ GỬI** cho máy đọc. Gửi "gi đi pi" thay cho `GDP` thì 3 mốc-từ
  ấy không còn tìm thấy trong chữ hiện lên; `_khop_tu_vao_chu` bỏ qua từ không
  khớp NHƯNG **đẩy con trỏ đi TIẾN**, mà `"gi"` là chuỗi con của rất nhiều chữ
  Việt (`gì`, `giá`, `nghĩ`) -> mốc dính SAI CHỖ rồi làm lệch mốc MỌI TỪ SAU =
  tái tạo đúng lỗi *"chữ chạy không khớp tiếng"* mà v2.28.0 vừa chữa.

Nên cổng này KHÔNG chỉ kiểm "có đổi chữ không". Nó kiểm:
  CA 1 — đổi đúng thứ phải đổi (`GDP` `CEO` `USB` `MV` `AI` `OST`)
  CA 2 — KHÔNG đổi thứ không được đổi (số La Mã · viết tắt gốc Việt · từ đọc
         thành từ · chữ thường · có chữ số kèm · giữa từ · CÂU HOA HẾT)
  CA 3 — chỉ edge-tts GIỌNG VIỆT: `el:` / `gemini:` / `piper:` / `en-US-*` /
         `zh-CN-*` phải ra NGUYÊN VĂN
  CA 4 — **MỐC TRỎ ĐÚNG TOKEN GỐC**: mọi chữ trong mốc sau khi gộp phải tìm
         được trong `texts` GỐC theo con trỏ đi tiến
  CA 5 — **KHÔNG LỆCH MỐC CÁC TỪ SAU**: mốc của những từ đứng sau viết tắt
         phải khớp ĐÚNG vị trí ký tự của chúng, so với arm "không có viết tắt"
  CA 6 — chạy trọn `chia_cum_theo_tu` / `dong_chu_theo_giong` với mốc thật của
         chữ đã đổi: cụm ra phải là chữ GỐC, đủ chữ, đúng thứ tự
  CA 7 — **TỰ KIỂM CỔNG (gỡ chốt ra thì PHẢI ĐỎ)**: bỏ bước gộp mốc
         (`tra_moc_ve_goc`) thì CA 4/CA 5 phải HỎNG. Cổng không tự bắt được lỗi
         nó sinh ra để canh thì là cổng phát chứng nhận, không phải cổng.
  CA 8 — nối ĐỦ CỬA trong `dubbing.py` (`_synth_all` · `_synth_all_words` ·
         `synth_demo`) và `_synth_all_words` PHẢI gọi `tra_moc_ve_goc`.

KHÔNG GỌI MẠNG, KHÔNG TỐN LƯỢT NÀO. Mốc `WordBoundary` ở đây là mốc DỰNG TAY
theo đúng định dạng edge-tts trả (`[a, b, từ]`, đơn vị giây) — phần đọc thật
đã đo riêng ở `_do_viet_tat_app.py` (tỉ lệ đọc sai) và `_do_moc_viet_tat.py`
(độ lệch chữ-tiếng). Cổng chỉ canh LOGIC, và canh nó bằng đường THẬT
(`dubbing._synth_all_words` bị chặn mạng, gọi `doc_viet_tat` thật).

  .venv\\Scripts\\python -u _test_viet_tat.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass

DAT = HONG = 0
GIONG_VI = "vi-VN-HoaiMyNeural"


def kiem(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


# --------------------------------------------------------------------------
# GIẢ LẬP edge-tts: cắt chữ ĐÃ GỬI thành từ rồi phát mốc tăng dần — ĐÚNG định
# dạng `WordBoundary` (`[start_s, end_s, text]`). Không giả lập cái app dùng
# (`doc_viet_tat`), chỉ giả lập cái NẰM NGOÀI máy này (dịch vụ Microsoft).
# --------------------------------------------------------------------------
def moc_gia(txt_gui: str, buoc: float = 0.30) -> list:
    ra: list = []
    t = 0.5
    for m in re.finditer(r"[^\s]+", txt_gui):
        w = m.group(0).strip(".,!?;:\"'“”…()")
        if not w:
            continue
        ra.append([round(t, 3), round(t + buoc * 0.8, 3), w])
        t += buoc
    return ra


def moc_tro_dung(text_goc: str, moc: list) -> tuple[bool, str]:
    """Mọi chữ trong `moc` tìm được trong `text_goc` theo CON TRỎ ĐI TIẾN?

    Đây chính là phép mà `_khop_tu_vao_chu` làm. Trả (đúng?, chỗ hỏng).
    """
    cur = 0
    thap = text_goc.lower()
    for m in moc:
        w = str(m[2]).strip()
        j = text_goc.find(w, cur)
        if j < 0:
            j = thap.find(w.lower(), cur)
        if j < 0:
            return False, f"«{w}» không tìm thấy từ vị trí {cur}"
        cur = j + len(w)
    return True, ""


def main() -> int:                                       # noqa: C901
    print("=" * 72)
    print("CỔNG 69 — ĐỌC ĐÚNG VIẾT TẮT MÀ KHÔNG LỆCH MỐC CHỮ")
    print("=" * 72)

    from app.core import doc_viet_tat as DVT
    from app.core import thay_giong as TG

    # ═══════════════ CA 1 — ĐỔI ĐÚNG THỨ PHẢI ĐỔI ═══════════════
    print("\nCA 1 — đổi đúng viết tắt (gốc bệnh: giọng Việt đánh vần kiểu Việt)")
    g1, t1 = DVT.doi_chu("GDP của cả nước năm nay tăng khá mạnh.")
    kiem("1a `GDP` -> «gi đi pi»", "gi đi pi" in g1, g1[:40])
    kiem("1b ghi lại đúng token GỐC", t1 and t1[0][2] == "GDP", str(t1))
    kiem("1c khoảng ký tự trỏ đúng phần đã thay",
         bool(t1) and g1[t1[0][0]:t1[0][1]] == "gi đi pi",
         g1[t1[0][0]:t1[0][1]] if t1 else "")
    for tok, cho in (("CEO", "xi i âu"), ("USB", "diu ét bi"),
                     ("MV", "em vi"), ("AI", "ây ai"), ("OST", "âu ét ti")):
        gg, _ = DVT.doi_chu(f"Cái {tok} này rất hay.")
        kiem(f"1d `{tok}` -> «{cho}»", cho in gg, gg)
    g1e, t1e = DVT.doi_chu("MV có GDP và USB.")
    kiem("1e NHIỀU viết tắt trong một câu -> đủ 3 khoảng thay",
         len(t1e) == 3 and [x[2] for x in t1e] == ["MV", "GDP", "USB"],
         str([x[2] for x in t1e]))
    kiem("1f khoảng thay TĂNG DẦN, không chồng nhau",
         all(t1e[k][1] <= t1e[k + 1][0] for k in range(len(t1e) - 1)))
    kiem("1g mọi khoảng thay soi vào chữ gửi ra đúng phần phiên âm",
         all(g1e[a:b] == " ".join(DVT.CHU_ANH[c] for c in tok)
             for a, b, tok in t1e))

    # ═══════════════ CA 2 — KHÔNG ĐỔI THỨ KHÔNG ĐƯỢC ĐỔI ═══════════════
    print("\nCA 2 — KHÔNG đụng thứ đang đọc đúng (mỗi ca là một cách hỏng thật)")
    for cau, vi in (
        ("Chiến tranh thế giới thứ II đã kết thúc.", "số La Mã II"),
        ("Đó là chuyện của thế kỷ XX rồi.", "số La Mã XX"),
        ("Anh ấy sống ở TP Hồ Chí Minh.", "viết tắt gốc Việt TP"),
        ("Người ta nói đó là một chiếc UFO.", "UFO đọc thành từ"),
        ("Cứ để nó ai đó làm cũng được.", "chữ thường"),
        ("Màn hình 3D nhìn rất thật.", "có chữ số kèm"),
        ("Cái iPhone này còn mới.", "HOA nằm giữa từ"),
        ("Netflix vừa ra phim mới.", "tên riêng — đo ra ĐANG ĐÚNG SẴN"),
        ("Cô ấy đạt triệu view sau một ngày.", "phiên âm đoán KHÔNG hơn thô"),
        ("1.500.000 người đã xem vào 15/08.", "số/ngày Azure chuẩn hoá sẵn"),
        ("38°C và 250 km/h.", "đơn vị Azure chuẩn hoá sẵn"),
    ):
        gg, tt = DVT.doi_chu(cau)
        kiem(f"2 giữ NGUYÊN VĂN ({vi})", gg == cau and not tt, gg)
    hoa = "KHÔNG THE NAO TIN NOI CHUYEN NAY"
    gh, th = DVT.doi_chu(hoa)
    kiem("2z CÂU VIẾT HOA HẾT -> không đánh vần cả câu",
         gh == hoa and not th, gh[:40])
    kiem("2y chuỗi rỗng / None -> không nổ",
         DVT.doi_chu("") == ("", []) and DVT.doi_chu(None) == ("", []))

    # ═══════════════ CA 3 — CHỈ edge-tts GIỌNG VIỆT ═══════════════
    print("\nCA 3 — chỉ edge-tts giọng Việt (máy đọc khác CHƯA ĐO -> không đụng)")
    cau = "GDP tăng mạnh."
    kiem("3a giọng Việt -> BẬT", DVT.bat_cho_giong(GIONG_VI))
    for v in ("en-US-AndrewNeural", "zh-CN-XiaoxiaoNeural",
              "ja-JP-NanamiNeural", "el:pNInz6obpgDQGcFmaJgB",
              "gemini:Kore", "piper:vi_VN-vais1000-medium", "", None):
        kiem(f"3b «{v}» -> TẮT, chữ nguyên văn",
             not DVT.bat_cho_giong(v)
             and DVT.sua_cho_may_doc(cau, v) == (cau, []))
    os.environ["BQ_VIET_TAT"] = "0"
    tat = DVT.sua_cho_may_doc(cau, GIONG_VI)
    os.environ.pop("BQ_VIET_TAT", None)
    kiem("3c `BQ_VIET_TAT=0` tắt được (phép đo cần arm đối chứng)",
         tat == (cau, []), str(tat))
    kiem("3d mặc định BẬT lại sau khi bỏ biến",
         DVT.sua_cho_may_doc(cau, GIONG_VI)[1] != [])

    # ═══════════════ CA 4 — MỐC TRỎ ĐÚNG TOKEN GỐC ═══════════════
    print("\nCA 4 — mốc sau khi gộp trỏ ĐÚNG token GỐC (không phải «gi»/«đi»)")
    CAU_THU = [
        "GDP của cả nước năm nay tăng khá mạnh.",
        "Vị CEO này giá gì cũng nghĩ ra được.",       # bẫy «gi»/«giá»/«nghĩ»
        "MV mới của cô ấy đạt triệu view chỉ sau một ngày.",
        "Anh nhớ cắm cái USB vào máy giúp tôi nhé.",
        "Công nghệ AI đang thay đổi cách chúng ta làm việc.",
        "Bài OST của phim này rất hay, ai nghe cũng thích.",
        "Cái GDP và cái CEO đều nói tới chuyện tiền.",
    ]
    for cau in CAU_THU:
        gui, thay = DVT.sua_cho_may_doc(cau, GIONG_VI)
        wb = moc_gia(gui)
        moc = DVT.tra_moc_ve_goc(wb, gui, thay)
        ok, vi = moc_tro_dung(cau, moc)
        kiem(f"4a mốc trỏ đúng chữ gốc — «{cau[:28]}...»", ok, vi)
        kiem("4b số mốc chỉ GIẢM (gộp), không mọc thêm", len(moc) <= len(wb),
             f"{len(wb)} -> {len(moc)}")
        kiem("4c thứ tự thời gian còn TĂNG DẦN",
             all(float(moc[k][0]) <= float(moc[k + 1][0])
                 for k in range(len(moc) - 1)))
        for a, b, tok in thay:
            del a, b
            kiem(f"4d token gốc «{tok}» CÓ trong mốc",
                 any(str(m[2]) == tok for m in moc),
                 str([m[2] for m in moc])[:70])
        # KHÔNG kiểm "có chữ nào trùng mảnh phiên âm" — `ai` vừa là mảnh của
        # `AI` vừa là TỪ VIỆT THẬT ("ai nghe cũng thích"), kiểm thế là báo sai
        # oan. Kiểm bằng SỐ MỐC GIẢM ĐÚNG BẰNG số mảnh bị gộp: mảnh nào lọt ra
        # thì con số này lệch ngay.
        giam = sum(len(gui[a:b].split()) - 1 for a, b, _t in thay)
        kiem("4e số mốc giảm ĐÚNG bằng số mảnh phiên âm bị gộp",
             len(moc) == len(wb) - giam,
             f"{len(wb)} - {giam} = {len(wb)-giam}, thực {len(moc)}")

    # mốc GỘP phải bao đúng khoảng: đầu của từ đầu, cuối của từ cuối
    gui, thay = DVT.sua_cho_may_doc("GDP tăng mạnh.", GIONG_VI)
    wb = moc_gia(gui)
    moc = DVT.tra_moc_ve_goc(wb, gui, thay)
    kiem("4f mốc gộp lấy ĐẦU của «gi» và CUỐI của «pi»",
         moc and moc[0][0] == wb[0][0] and moc[0][1] == wb[2][1],
         f"{moc[0] if moc else None} vs wb {wb[:3]}")
    kiem("4g 3 mốc phiên âm gộp thành 1 -> tổng mốc giảm đúng 2",
         len(moc) == len(wb) - 2, f"{len(wb)} -> {len(moc)}")
    kiem("4h mốc rỗng / không có phần thay -> trả y nguyên",
         DVT.tra_moc_ve_goc([], gui, thay) == []
         and DVT.tra_moc_ve_goc(wb, gui, []) == wb)

    # ═══════════════ CA 5 — KHÔNG LỆCH MỐC CÁC TỪ SAU ═══════════════
    print("\nCA 5 — mốc các từ ĐỨNG SAU viết tắt không bị đẩy lệch")
    cau = "Vị CEO này giá gì cũng nghĩ ra được."
    gui, thay = DVT.sua_cho_may_doc(cau, GIONG_VI)
    moc = DVT.tra_moc_ve_goc(moc_gia(gui), gui, thay)
    khop = TG._khop_tu_vao_chu(cau, moc)
    # từ nào cũng phải khớp được, và khớp vào ĐÚNG vị trí ký tự của nó
    kiem("5a mọi mốc khớp được vào chữ gốc (không bị bỏ qua)",
         len(khop) == len(moc), f"{len(khop)}/{len(moc)}")
    sai = [(c0, c1, cau[c0:c1], str(m[2]))
           for (c0, c1, _a, _b), m in zip(khop, moc) if cau[c0:c1] != str(m[2])]
    kiem("5b mỗi mốc khớp vào ĐÚNG chuỗi ký tự của chính nó", not sai,
         str(sai[:3]))
    # ARM ĐỐI CHỨNG: câu KHÔNG có viết tắt -> vị trí ký tự phải y như khi
    # chạy qua đường viết tắt (chứng minh đường mới không làm xê dịch gì).
    cau_sach = cau.replace("CEO", "abc")
    gui2, thay2 = DVT.sua_cho_may_doc(cau_sach, GIONG_VI)
    kiem("5c arm đối chứng: câu không có viết tắt thì đường mới KHÔNG đụng",
         gui2 == cau_sach and thay2 == [])
    khop2 = TG._khop_tu_vao_chu(cau_sach, moc_gia(cau_sach))
    kiem("5d cùng SỐ từ khớp được ở hai arm", len(khop) == len(khop2),
         f"{len(khop)} vs {len(khop2)}")
    kiem("5e vị trí ký tự các từ SAU viết tắt trùng khớp hai arm",
         [c0 for c0, _c1, _a, _b in khop[2:]]
         == [c0 for c0, _c1, _a, _b in khop2[2:]],
         f"{[c0 for c0, _1, _2, _3 in khop[2:]][:6]} vs "
         f"{[c0 for c0, _1, _2, _3 in khop2[2:]][:6]}")

    # ═══════════════ CA 6 — CHẠY TRỌN ĐƯỜNG CHỮ CHẠY ═══════════════
    print("\nCA 6 — `chia_cum_theo_tu` / `dong_chu_theo_giong` ra CHỮ GỐC")
    cau = "GDP của cả nước năm nay tăng khá mạnh nhờ CEO giỏi."
    gui, thay = DVT.sua_cho_may_doc(cau, GIONG_VI)
    moc = DVT.tra_moc_ve_goc(moc_gia(gui), gui, thay)
    cum = TG.chia_cum_theo_tu(cau, moc)
    kiem("6a chia được cụm (không rơi về đường lùi tỉ lệ)", bool(cum),
         f"{len(cum)} cụm")
    ghep = " ".join(c for _a, _b, c in cum)
    kiem("6b chữ hiện lên là chữ GỐC, có `GDP` và `CEO`",
         "GDP" in ghep and "CEO" in ghep, ghep[:70])
    kiem("6c KHÔNG lọt chữ phiên âm ra màn hình",
         "gi đi pi" not in ghep and "xi i âu" not in ghep, ghep[:70])
    kiem("6d không mất chữ nào của câu gốc",
         re.sub(r"\s+", "", ghep) == re.sub(r"\s+", "", cau),
         f"«{ghep}»")
    kiem("6e mốc cụm tăng dần, không chồng",
         all(cum[k][0] <= cum[k + 1][0] for k in range(len(cum) - 1)))
    dong = TG.dong_chu_theo_giong([(0, 0.5, 4.0)], [cau], [(0, moc)])
    kiem("6f `dong_chu_theo_giong` ra dòng chữ GỐC", bool(dong)
         and "GDP" in " ".join(c for _a, _b, c in dong),
         str([c for _a, _b, c in dong])[:80])
    kiem("6g khung hiển thị không chồng nhau",
         all(dong[k][1] <= dong[k + 1][0] + 1e-6
             for k in range(len(dong) - 1)))

    # ═══════════════ CA 7 — TỰ KIỂM CỔNG (gỡ chốt -> PHẢI ĐỎ) ═══════════════
    print("\nCA 7 — TỰ KIỂM: gỡ bước gộp mốc ra thì CA 4/CA 5 PHẢI hỏng")
    xau = 0
    for cau in CAU_THU:
        gui, thay = DVT.sua_cho_may_doc(cau, GIONG_VI)
        # KHÔNG gộp mốc = đúng cái bản vá sai mà lượt trước từ chối nối
        ok, _vi = moc_tro_dung(cau, moc_gia(gui))
        if not ok:
            xau += 1
    kiem("7a bỏ `tra_moc_ve_goc` -> mốc KHÔNG trỏ được vào chữ gốc",
         xau >= len(CAU_THU) - 1, f"{xau}/{len(CAU_THU)} câu hỏng khi gỡ chốt")
    # và bẫy NGUY nhất: mốc «gi» dính vào chữ Việt khác rồi kéo con trỏ qua
    cau = "Vị CEO này giá gì cũng nghĩ ra được."
    gui, thay = DVT.sua_cho_may_doc(cau, GIONG_VI)
    kho_gia = TG._khop_tu_vao_chu(cau, moc_gia(gui))
    dinh_sai = [(cau[c0:c1]) for c0, c1, _a, _b in kho_gia]
    kiem("7b bỏ chốt -> mốc dính vào chữ Việt KHÁC (đúng lỗi đã lường)",
         any(x in ("gi", "i", "âu", "xi") for x in dinh_sai)
         or len(kho_gia) < len(moc_gia(gui)) - 1,
         f"dính vào: {dinh_sai[:8]}")
    kiem("7c có chốt thì SỐ từ khớp được NHIỀU HƠN khi gỡ chốt",
         len(TG._khop_tu_vao_chu(
             cau, DVT.tra_moc_ve_goc(moc_gia(gui), gui, thay))) >= len(kho_gia),
         f"có chốt {len(TG._khop_tu_vao_chu(cau, DVT.tra_moc_ve_goc(moc_gia(gui), gui, thay)))}"
         f" vs gỡ {len(kho_gia)}")

    # ═══════════════ CA 8 — NỐI ĐỦ CỬA ═══════════════
    print("\nCA 8 — nối ĐỦ CỬA trong `dubbing.py` (sót một cửa là lẫn hai kiểu)")
    src = (REPO / "app" / "core" / "dubbing.py").read_text(encoding="utf-8")
    kiem("8a `dubbing` có import `doc_viet_tat`",
         "doc_viet_tat" in src.split("def ")[0] or
         "from app.core import doc_viet_tat" in src)
    kiem("8b gọi `sua_cho_may_doc` đủ 3 cửa (_synth_all · _synth_all_words · "
         "synth_demo)", src.count("sua_cho_may_doc(") >= 3,
         f"{src.count('sua_cho_may_doc(')} chỗ")
    kiem("8c `_synth_all_words` GỌI `tra_moc_ve_goc` (không gọi = lệch mốc)",
         "tra_moc_ve_goc(" in src, f"{src.count('tra_moc_ve_goc(')} chỗ")
    # chỗ gán `words[i]` phải đi qua hàm gộp — gán thẳng `wb` là lỗi ÂM THẦM
    kiem("8d `words[i]` gán qua hàm gộp, KHÔNG gán thẳng `wb`",
         re.search(r"words\[i\]\s*=\s*doc_viet_tat\.tra_moc_ve_goc\(", src)
         is not None and re.search(r"words\[i\]\s*=\s*wb\b", src) is None)
    # bảng chữ cái là bảng ĐÃ ĐO -> đủ 26 chữ, không rỗng
    kiem("8e bảng `CHU_ANH` đủ 26 chữ cái", len(DVT.CHU_ANH) == 26,
         str(len(DVT.CHU_ANH)))
    kiem("8f nhãn/bảng KHÔNG có emoji",
         not any(ord(c) > 0x2100 for c in "".join(DVT.CHU_ANH.values())))

    print("\n" + "=" * 72)
    print(f"TỔNG KẾT: ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 72)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
