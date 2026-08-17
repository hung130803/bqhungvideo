# -*- coding: utf-8 -*-
"""ĐỌC ĐÚNG TỪ VIẾT TẮT khi giọng đọc là GIỌNG VIỆT — và TRẢ MỐC VỀ TOKEN GỐC.

Anh Hùng 17/08/2026: *"chọn tiếng Việt, mấy chữ tiếng Anh hay tên riêng nó đọc
toàn bị lỗi ở cái đó ... lỗi to đó"*.

GỐC BỆNH — ĐO ĐƯỢC, KHÔNG PHẢI ĐOÁN (`_do_doc_roi.py` + `_do_phien_am.py`):
giọng Việt của Azure đánh vần bằng **TÊN CHỮ CÁI VIỆT** (G = "dê", D = "đê",
P = "pê") nên `GDP` phát ra "dê-dê-pê" -> máy nghe chép lại thành `DDP`. Người
Việt thì đọc viết tắt bằng **tên chữ cái ANH** ("gi-đi-pi"). Đổi sang tên chữ
cái Anh VIẾT BẰNG ÂM VIỆT thì `CEO` và `GDP` đọc đúng, và `AI`/`MV`/`USB`
KHÔNG hỏng thêm (đo ghép cặp 25 token, 2 arm đan xen: thô 6/25 sai -> phiên âm
4/25 sai, **TỐT LÊN 2 · TỆ ĐI 0 · y nguyên 23**).

BA ĐƯỜNG ĐÃ THỬ VÀ BỊ BÁC BẰNG SỐ — đừng đi lại:
  1. **SSML** (`<say-as interpret-as="characters">`): `edge_tts.Communicate`
     escape chữ người dùng TRƯỚC khi dựng SSML nên thẻ bị **ĐỌC THÀNH TIẾNG**
     (`_do_ssml.py`: ra *"CS Interps Charaster GDP CS"*). Thử cả cửa app lẫn
     API trần, giống hệt. **ĐƯỜNG NÀY ĐÓNG.**
  2. **BẢNG TÊN RIÊNG** (`Netflix`/`iPhone`/`YouTube`/`Elon Musk`): đo ra
     ĐANG ĐÚNG SẴN ở bản thô -> chép âm cho chúng là rủi ro thuần, 0 lợi ích.
     Còn `Marvel`/`TikTok`/`view` thì **vẫn hỏng SAU khi chép âm**. Tức phiên
     âm ĐOÁN không hơn bản thô. **KHÔNG làm bảng tên riêng.**
  3. **SỐ / NGÀY / ĐƠN VỊ**: 0% sai ở CẢ 4 ngôn ngữ, CẢ 2 phép đo — Azure
     chuẩn hoá sẵn (`1.500.000` -> "1 triệu 500 nghìn", `38°C` -> "38 độ C").
     Làm gì ở đây là **sửa thứ đang đúng**.

VÌ SAO PHẢI CÓ `tra_moc_ve_goc` — ĐÂY LÀ NỬA KHÓ CỦA VIỆC:
chữ HIỆN LÊN lấy từ `texts` GỐC, còn MỐC THỜI GIAN lấy từ `WordBoundary` của
chính chữ **ĐÃ GỬI** cho máy đọc (`dong_chu_theo_giong` -> `chia_cum_theo_tu`
-> `_khop_tu_vao_chu`). Gửi "gi đi pi" thay cho `GDP` thì 3 mốc-từ ấy KHÔNG
còn tìm thấy trong chữ hiện lên. `_khop_tu_vao_chu` bỏ qua từ không khớp nên
không vỡ — **nhưng nó ĐẨY CON TRỎ ĐI TIẾN**, mà `"gi"` là chuỗi con của rất
nhiều chữ Việt (`gì`, `giá`, `nghĩ`), nên mốc dính vào SAI CHỖ rồi kéo con trỏ
qua, làm lệch mốc MỌI TỪ SAU = tái tạo đúng lỗi *"chữ chạy không khớp tiếng"*
mà v2.28.0 vừa chữa.
Nên cửa chung phải **GỘP dãy mốc của phần thay thế thành MỘT mốc mang chữ
GỐC** (giữ mốc đầu của "gi", mốc cuối của "pi", chữ trả về là `GDP`) — caller
không bao giờ nhìn thấy chữ đã đổi.

PHẠM VI CỐ Ý HẸP — hẹp là AN TOÀN, và mọi giới hạn đều đúng chiều "để nguyên
= hành vi hôm nay, không thể tệ hơn":
  * chỉ **GIỌNG VIỆT** (`vi-*`): Trung/Nhật đo ra ĐÚNG BẰNG TRẦN en-US, không
    có bệnh để chữa; giọng Anh vốn đánh vần đúng.
  * chỉ **edge-tts**: đó là máy đọc đã ĐO. ElevenLabs/Gemini/Piper đi đường
    riêng, KHÔNG đo -> KHÔNG đụng.
  * chỉ **2-3 chữ cái HOA**: đúng cỡ đã đo (`AI` `MV` `CEO` `GDP` `OST` `USB`).
    4-5 chữ cái hay bị đọc thành TỪ (`NASA` -> "na-sa" là ĐÚNG rồi), đánh vần
    ra là làm hỏng thứ đang chạy tốt.
  * có **DANH SÁCH BỎ QUA**: số La Mã (`thế kỷ XX` KHÔNG phải "ích ích"), viết
    tắt gốc VIỆT (`TP`, `HCM` — người Việt đọc bằng tên chữ cái VIỆT), và mấy
    cái đọc thành từ (`UFO` -> "u-phô", `OK` -> "ô-kê").

Tắt bằng `BQ_VIET_TAT=0` — CHỈ để phép đo chạy được arm đối chứng trong cùng
một tiến trình (và để cứu hộ nếu có ca lạ). Mặc định BẬT.
"""
from __future__ import annotations

import os
import re

#: TÊN CHỮ CÁI kiểu ANH, viết bằng âm Việt. **BẢNG NÀY LÀ BẢNG ĐÃ ĐO** ở
#: `_do_phien_am.py` — đổi một dòng ở đây là con số đo được không còn nói về
#: thứ đang chạy nữa. Muốn đổi thì đo lại.
CHU_ANH = {
    "A": "ây", "B": "bi", "C": "xi", "D": "đi", "E": "i", "F": "ép",
    "G": "gi", "H": "ếch", "I": "ai", "J": "giay", "K": "kây", "L": "eo",
    "M": "em", "N": "en", "O": "âu", "P": "pi", "Q": "kiu", "R": "a",
    "S": "ét", "T": "ti", "U": "diu", "V": "vi", "W": "đắp liu", "X": "ích",
    "Y": "quai", "Z": "dét",
}

#: SỐ LA MÃ hay gặp trong lời thuyết minh ("thế kỷ XX", "chiến tranh thứ II").
#: Chỉ liệt kê tường minh, KHÔNG dò theo bộ ký tự `[IVXLCDM]`: dò thế thì
#: `DVD` (D-V-D) cũng bị coi là số La Mã và mất luôn phần chữa đúng.
LA_MA = {"II", "III", "IV", "VI", "VII", "IX", "XI", "XII", "XX", "XV",
         "XVI", "XIX", "XXI"}

#: VIẾT TẮT KHÔNG ĐƯỢC ĐÁNH VẦN KIỂU ANH. Hai nhóm:
#:   * gốc VIỆT — người Việt đọc bằng tên chữ cái VIỆT hoặc đọc bung ra
#:     (`TP` = "thành phố", `HCM` = "hát-cê-em"), áp tên chữ cái Anh vào là
#:     làm SAI thêm.
#:   * đọc thành TỪ chứ không đánh vần (`UFO` = "u-phô", `OK` = "ô-kê").
#: Để nguyên = ĐÚNG hành vi hôm nay, nên thêm vào đây không bao giờ làm tệ
#: hơn bản đang chạy — đó là lý do danh sách này được phép "phòng xa".
BO_QUA = {
    # gốc Việt
    "TP", "HCM", "VN", "HN", "SG", "BV", "TS", "GS", "BS", "KS", "SV", "HS",
    "GV", "CA", "CS", "TT", "UB", "BT", "CT",
    # đọc thành từ
    "UFO", "OK", "SEA", "GAY", "PIN", "SIM",
}

#: 2-3 chữ cái HOA liền nhau. Ranh giới kiểm bằng `isalnum()` ở
#: `doi_chu` (nhận biết chữ Việt có dấu) chứ không nhồi vào regex.
_RE_HOA = re.compile(r"[A-Z]{2,3}")


def bat_cho_giong(voice: str) -> bool:
    """Có sửa viết tắt cho `voice` không? CHỈ edge-tts giọng Việt (`vi-*`).

    `el:` / `gemini:` / `piper:` -> False (máy đọc khác, chưa đo).
    """
    if os.environ.get("BQ_VIET_TAT") == "0":
        return False
    v = str(voice or "").strip().lower()
    if not v or ":" in v:               # el: / gemini: / piper:
        return False
    return v.startswith("vi-")


def doi_chu(text: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Đổi viết tắt trong `text` sang tên chữ cái Anh. HÀM THUẦN.

    Trả `(chữ_gửi_máy_đọc, [(đầu, cuối, token_GỐC)])` — chỉ số ký tự tính
    trên chữ **ĐÃ ĐỔI** (tức chuỗi thật sự gửi đi), vì đó là chuỗi mà
    `tra_moc_ve_goc` phải soi `WordBoundary` vào.
    Không có gì phải đổi -> trả `(text, [])` NGUYÊN VẸN (không đụng gì).
    """
    s = str(text or "")
    if not s:
        return s, []
    # CÂU VIẾT HOA HẾT (tiêu đề hô hào) -> mọi từ đều khớp `[A-Z]{2,3}`, đánh
    # vần cả câu là thảm hoạ. Không có CHỮ THƯỜNG nào mà câu lại dài thì bỏ.
    if len(s) > 12 and not any(c.islower() for c in s):
        return s, []
    ra: list[str] = []
    thay: list[tuple[int, int, str]] = []
    cur = 0
    for m in _RE_HOA.finditer(s):
        i, j = m.span()
        tok = m.group(0)
        if tok in BO_QUA or tok in LA_MA:
            continue
        # RANH GIỚI TỪ — `isalnum()` hiểu chữ Việt có dấu, nên "GDPhải" hay
        # "aGDP" không bị cắn vào. Chữ số hai bên cũng loại (`A4`, `3D`).
        if i > 0 and (s[i - 1].isalnum() or s[i - 1] == "_"):
            continue
        if j < len(s) and (s[j].isalnum() or s[j] == "_"):
            continue
        moi = " ".join(CHU_ANH[c] for c in tok)
        ra.append(s[cur:i])
        d = sum(len(x) for x in ra)
        ra.append(moi)
        thay.append((d, d + len(moi), tok))
        cur = j
    if not thay:
        return s, []
    ra.append(s[cur:])
    return "".join(ra), thay


def _vi_tri_tu(txt: str, moc: list) -> list:
    """[(chỉ_số_mốc, đầu, cuối)] — vị trí ký tự của từng mốc-từ trong `txt`.

    Cùng thuật toán con-trỏ-đi-tiến với `thay_giong._khop_tu_vao_chu` (từ lặp
    lại vẫn dính đúng lần xuất hiện của nó). Từ không tìm thấy -> KHÔNG có
    dòng nào, caller giữ mốc đó y nguyên.
    """
    ra: list = []
    cur = 0
    thap = txt.lower()
    for k, m in enumerate(moc or ()):
        try:
            w = str(m[2] or "").strip()
        except (TypeError, IndexError):
            continue
        if not w:
            continue
        j = txt.find(w, cur)
        if j < 0:
            j = thap.find(w.lower(), cur)
        if j < 0:
            continue
        ra.append((k, j, j + len(w)))
        cur = j + len(w)
    return ra


def tra_moc_ve_goc(moc: list, txt_gui: str,
                   thay: list[tuple[int, int, str]]) -> list:
    """GỘP dãy mốc của phần thay thế thành MỘT mốc mang chữ GỐC. HÀM THUẦN.

    `moc` = `[[a, b, từ], ...]` do `WordBoundary` trả về **cho chữ đã đổi**.
    `txt_gui` / `thay` = đúng hai thứ `doi_chu` trả ra.

    Ra: cùng định dạng, nhưng mọi từ nằm trong khoảng thay thế bị thu thành
    một mốc `[mốc_đầu_của_dãy, mốc_cuối_của_dãy, token_GỐC]`. Nhờ vậy chữ
    trong mốc LUÔN tìm được trong `texts` gốc và `_khop_tu_vao_chu` không bị
    kéo con trỏ đi sai chỗ.

    Bất biến giữ nguyên: THỨ TỰ tăng dần, và số mốc chỉ GIẢM (gộp), không bao
    giờ mọc thêm. Mốc không định vị được trong `txt_gui` -> giữ Y NGUYÊN.
    """
    if not moc:
        return list(moc or [])
    if not thay:
        return list(moc)
    # mốc thứ k thuộc khoảng thay thế nào (-1 = không thuộc)
    thuoc: dict[int, int] = {}
    for k, a, b in _vi_tri_tu(str(txt_gui or ""), moc):
        for idx, (d, h, _tok) in enumerate(thay):
            # CHỒNG LẤN là đủ, không đòi nằm trọn: máy đọc có thể trả từ đã
            # chuẩn hoá dài/ngắn hơn một vài ký tự.
            if a < h and b > d:
                thuoc[k] = idx
                break
    ra: list = []
    k = 0
    n = len(moc)
    while k < n:
        idx = thuoc.get(k, -1)
        if idx < 0:
            ra.append(list(moc[k]))
            k += 1
            continue
        j = k
        while j + 1 < n and thuoc.get(j + 1, -1) == idx:
            j += 1
        try:
            a = float(moc[k][0])
            b = float(moc[j][1])
        except (TypeError, ValueError, IndexError):
            ra.extend(list(x) for x in moc[k:j + 1])
            k = j + 1
            continue
        ra.append([round(a, 3), round(b, 3), thay[idx][2]])
        k = j + 1
    return ra


def sua_cho_may_doc(text: str, voice: str,
                    ) -> tuple[str, list[tuple[int, int, str]]]:
    """CỬA DUY NHẤT cho `dubbing._synth_all` / `_synth_all_words` gọi.

    Giọng không phải edge-tts Việt (hoặc `BQ_VIET_TAT=0`) -> trả `(text, [])`,
    tức KHÔNG đổi một ký tự nào.
    """
    if not bat_cho_giong(voice):
        return str(text or ""), []
    return doi_chu(text)
