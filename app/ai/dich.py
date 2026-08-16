# -*- coding: utf-8 -*-
"""DỊCH BIẾT ĐẾM THỜI GIAN — đường dịch cho THAY GIỌNG, viết lại từ 3 lỗi ĐO ĐƯỢC.

VÌ SAO CÓ FILE NÀY (không sửa thẳng `thay_giong._dich_loat`): đường dịch cũ
dịch xong RỒI MỚI ép tiếng vừa khung câu gốc. Đo trên video thật của anh Hùng:
câu gốc khung **9,62 s** mà bản dịch đọc hết **0,99 s** -> thừa 8,6 s trống.
Đó là gốc của **26% thời lượng "chữ chạy mà không nói"** (CLAUDE.md đã đo lại
3 lượt: 25,1-26,7%, và ghi thẳng là bản vá mốc KHÔNG chữa được). Nghề lồng
tiếng làm ngược lại: **bắt bản dịch vừa thời gian NGAY TỪ LÚC DỊCH**.

BA LỖI CHẤT LƯỢNG ĐÃ ĐO TRÊN VIDEO THẬT, mỗi lỗi một chốt trong prompt:
  · **sai thuật ngữ** — `新片` (phim mới) -> *"phim về chip"*. Chốt: gửi BỐI
    CẢNH cả bài + cấm đoán theo ÂM, kèm đúng ví dụ đó.
  · **ngược tai** — *"một võ sĩ **xuống cấp**"*, *"quyền quyền đến thịt"*.
    Chốt: cấm dịch Hán-Việt mặt chữ, đòi văn NÓI.
  · **cụt / gộp** — câu dưới 20 ký tự 8% và 15%; câu trên 60 ký tự 6/38 và
    6/40. Chốt: NGÂN SÁCH CHỮ hai đầu (sàn chống cụt · trần chống gộp) + hậu
    kiểm đếm lại, lệch thì bắt viết lại.

NGÂN SÁCH LẤY TỪ SỐ ĐO, KHÔNG ĐOÁN (`_do_toc_doc.py`, edge-tts giọng Việt,
**đã cắt lề im** — đo trên file TTS thô là sai ~1,07 s/câu vì edge-tts chèn
~0,20 s im đầu + ~0,87 s cuối MỖI câu).

BẤT BIẾN: hàm ở đây CHỈ SINH CHỮ. Không đụng file, không ép tốc độ, không
trộn tiếng — phần ÉP tiếng nằm ở `dubbing.py`/`thay_giong.py`.
"""
from __future__ import annotations

from typing import Callable, Optional

from app.ai.cham_dich import am_tiet_viet

# --------------------------------------------------------------------------
# TỐC ĐỘ ĐỌC — ĐO THẬT, đừng chỉnh mò (`_do_toc_doc.py`)
# --------------------------------------------------------------------------
#: `giây = GIAY_MOI_AM_TIET * âm_tiết + GIAY_CO_DINH`
#: Đo trên 20 câu tiếng Việt thật (4..25 âm tiết, 1,12..6,06 s), R² = 0,941.
#: **Phải có hằng số cộng**: tỉ lệ thô ở câu 5-7 âm tiết là 0,282 s/âm tiết
#: còn ở câu 11-14 chỉ 0,239 — lấy một tỉ lệ trung bình rồi áp cho mọi câu là
#: ước lượng sai HỆ THỐNG ở hai đầu, đúng chỗ đau nhất (video toàn câu ngắn).
GIAY_MOI_AM_TIET = 0.2388
GIAY_CO_DINH = 0.1503

#: Nhắm bao nhiêu phần khung câu gốc. KHÔNG nhắm 1,00: bản dịch còn phải đi
#: qua bước ĐỌC NHANH (`rate` của edge-tts) và bước mượn khoảng lặng; nhắm
#: sát trần là mọi sai số đều đẩy sang phía TRÀN, tức ép `atempo` — thứ đã đo
#: được là làm méo tiếng (5,357 dB ở 1,20 · 6,765 ở 1,50).
NHAM = 0.92
#: Trần: dài hơn ngần này lần khung thì bắt viết lại. 1,30 vì bước đọc nhanh
#: của app nuốt được tới ~1,45 lần mà không méo (đo `rate`: +50% -> 1,455×).
TRAN = 1.30
#: Sàn: ngắn hơn ngần này lần khung là CỤT — đây là chốt chống đúng cái
#: "0,99 s tiếng trong khung 9,62 s".
SAN = 0.62
#: Câu gốc ngắn hơn ngần này giây thì KHÔNG ép sàn: khung 1 giây chỉ chứa 3
#: âm tiết, ép thêm là bắt model nhồi chữ vô nghĩa.
KHUNG_TOI_THIEU = 1.2

# --------------------------------------------------------------------------
# TRẦN THEO CÂU GỐC — CHỐT CHỐNG BỊA, ĐO ĐƯỢC, ĐỪNG BỎ
# --------------------------------------------------------------------------
# **LỖI THẬT CỦA CHÍNH BẢN ĐẦU FILE NÀY**, bắt được ngay lượt thử 8 câu: khung
# 4,12 s cho câu gốc `第一部地下决斗室` (8 chữ Hán = "Phần một: Sàn Đấu Ngầm")
# đẻ ra ngân sách **15 chữ**, và model ngoan ngoãn nhồi cho đủ:
#   *"Bộ phim đầu tiên về phòng đấu ngầm, **nơi diễn ra các trận đấu đầy kịch
#   tính và hấp dẫn**"* (20 chữ) — vế sau KHÔNG CÓ trong câu gốc.
# Tức ngân sách thời gian nếu chỉ nhìn ĐỒNG HỒ thì nó mua thời lượng bằng
# NỘI DUNG BỊA. Đó là đổi một lỗi đo được (trống tiếng) lấy một lỗi tệ hơn
# (sai nội dung), đúng bài học "chặt chữ làm xấu NỘI DUNG — cái sau tệ hơn".
#
# Nên ngân sách phải kẹp bởi ĐỘ DÀI TỰ NHIÊN của chính câu gốc. Tỉ lệ đo trên
# 20 bản dịch Trung -> Việt viết tay (`_do_bo_hong.TOT`):
#   min 0,50 · 10% 0,67 · **trung vị 0,89** · 90% 1,13 · max 1,25 âm tiết/chữ Hán
#: Trần "còn tự nhiên" — trên mức này là đang thêm chữ không có trong câu gốc.
TY_LE_TRAN = 1.25
#: Trần CỨNG cho cửa viết-lại (nới hơn trần nhắm để đừng bắt viết lại một câu
#: chỉ hơi dài hơn bản người dịch).
TY_LE_TRAN_CUNG = 1.50
#: Sàn "còn tự nhiên" — dưới mức này thì câu gốc vốn đã ngắn, ép dài là bịa.
TY_LE_SAN = 0.70
#: Nguồn KHÔNG phải chữ Hán (mỗi âm tiết đã là một "chữ") thì tỉ lệ khác hẳn.
#: **CHƯA ĐO** cho nhóm này — để 1,0/1,8/0,7 là số THẬN TRỌNG, không phải số
#: đo được. Ai dùng cho nguồn Anh/Nhật/Hàn phải đo lại rồi sửa ở đây.
TY_LE_TRAN_LATIN = 1.60
TY_LE_TRAN_CUNG_LATIN = 2.00
TY_LE_SAN_LATIN = 0.60
#: Số câu mỗi lượt gọi. Groq trả 413 khi gói to — 413 là lỗi CỦA YÊU CẦU,
#: phải THU NHỎ, KHÔNG phạt key.
CO_MOI_LUOT = 14
#: Số vòng đòi lại câu LLM bỏ sót.
VONG_DOI_LAI = 3
#: Số vòng viết lại câu lệch ngân sách.
VONG_VIET_LAI = 2
#: Bối cảnh gửi kèm: bao nhiêu ký tự đầu bài. Đủ để model biết video nói về
#: cái gì (đây là chốt bắt `新片` = "phim mới" chứ không phải "con chip"),
#: chưa đủ to để chạm 413.
BOI_CANH_KY_TU = 900


def _ten_nn(ma: str) -> str:
    from app.core.thay_giong import _ten_nn as t
    return t(ma)


def _theo_nhan(data, chi_so: list[int], khoa: str) -> dict:
    from app.core.thay_giong import _theo_nhan as f
    return f(data, chi_so, khoa)


def _con_chu_goc(text: str, dich_sang: str) -> bool:
    from app.core.thay_giong import con_chu_goc
    return bool(con_chu_goc(text, dich_sang))


# --------------------------------------------------------------------------
# NGÂN SÁCH
# --------------------------------------------------------------------------
def giay_doc(am_tiet: int) -> float:
    """Ước lượng số giây đọc `am_tiet` âm tiết tiếng Việt (đã cắt lề im)."""
    return GIAY_MOI_AM_TIET * max(0, am_tiet) + GIAY_CO_DINH


def am_tiet_vua(giay: float, phan: float = NHAM) -> int:
    """Đảo mô hình: `phan` phần của khung `giay` chứa được mấy âm tiết."""
    n = (max(0.0, giay) * phan - GIAY_CO_DINH) / GIAY_MOI_AM_TIET
    return max(1, int(round(n)))


def co_goc(goc: str) -> int:
    """"Cỡ" câu gốc tính bằng đơn vị đếm được: chữ Hán, hoặc âm tiết nếu
    nguồn không phải CJK (cùng quy ước `cham_dich.loi_may`)."""
    from app.ai.cham_dich import _so_chu_han
    return _so_chu_han(goc) or am_tiet_viet(goc)


def ngan_sach(giay: float, goc: str = "") -> dict:
    """Ngân sách CHỮ cho khung `giay`, KẸP theo độ dài tự nhiên của `goc`.

    Trả {giay, dich, min, max, do_goc, tran_goc}.
    `min` = 0 nghĩa là không đặt sàn (khung quá ngắn, hoặc câu gốc vốn ngắn).

    HAI RÀNG BUỘC, LẤY CÁI CHẶT HƠN:
      · ĐỒNG HỒ  — bao nhiêu chữ đọc lọt khung (mô hình tốc độ đọc đo được)
      · CÂU GỐC  — bao nhiêu chữ là còn dịch, quá thì là BỊA (tỉ lệ đo được)
    Bỏ ràng buộc thứ hai thì khung dài + câu gốc ngắn = model nhồi chữ (xem
    khối ghi chú `TY_LE_TRAN` — lỗi thật của bản đầu file này).
    """
    giay = max(0.0, float(giay))
    n = co_goc(goc)
    from app.ai.cham_dich import _so_chu_han
    han = _so_chu_han(goc) > 0
    r_tran = TY_LE_TRAN if han else TY_LE_TRAN_LATIN
    r_cung = TY_LE_TRAN_CUNG if han else TY_LE_TRAN_CUNG_LATIN
    r_san = TY_LE_SAN if han else TY_LE_SAN_LATIN

    dong_ho = am_tiet_vua(giay, NHAM)
    dh_max = max(2, int((giay * TRAN - GIAY_CO_DINH) / GIAY_MOI_AM_TIET))
    dh_min = 0 if giay < KHUNG_TOI_THIEU else \
        max(1, int((giay * SAN - GIAY_CO_DINH) / GIAY_MOI_AM_TIET))

    if n <= 0:                                   # không đo được cỡ gốc
        return {"giay": round(giay, 2), "dich": dong_ho, "min": dh_min,
                "max": dh_max, "do_goc": 0, "tran_goc": 0}

    tran_goc = max(2, int(round(r_tran * n)))
    cung_goc = max(2, int(round(r_cung * n)))
    san_goc = max(1, int(round(r_san * n)))
    return {
        "giay": round(giay, 2),
        "dich": max(1, min(dong_ho, tran_goc)),
        "min": min(dh_min, san_goc),             # KHÔNG BAO GIỜ ép bịa
        "max": max(2, min(dh_max, cung_goc)),
        "do_goc": n,
        "tran_goc": tran_goc,
    }


def _chia_co(n: int, co: int = CO_MOI_LUOT):
    for i in range(0, n, co):
        yield list(range(i, min(i + co, n)))


def _boi_canh(cau: list[dict]) -> str:
    """Vài câu đầu của CHÍNH bài — để model biết video đang nói về cái gì.

    Đây là chốt rẻ nhất chống lỗi thuật ngữ: `新片` một mình thì đoán được là
    "phim mới" hay "chip mới"; nằm cạnh `电影`/`推荐`/`第一部` thì không.
    """
    ra, n = [], 0
    for c in cau:
        t = str(c.get("text") or "").strip()
        if not t:
            continue
        if n + len(t) > BOI_CANH_KY_TU:
            break
        ra.append(t)
        n += len(t)
    return " ".join(ra)


# --------------------------------------------------------------------------
# PROMPT
# --------------------------------------------------------------------------
_SYSTEM = ("Bạn là biên dịch viên LỒNG TIẾNG chuyên nghiệp. Bản dịch của bạn "
           "sẽ được máy đọc thành tiếng và ghép vào đúng khung thời gian của "
           "câu gốc, nên nó phải vừa ĐÚNG NGHĨA vừa VỪA ĐỘ DÀI. "
           "CHỈ trả JSON thuần.")


#: Ví dụ CHỐNG LỖI lấy từ CHÍNH video đang đo (`新片`, `落魄拳手`). Bật cái này
#: lên là **dạy đúng bài thi**: con số đo trên video đó không còn nói được là
#: prompt tốt hay là prompt đã học thuộc. Mặc định TẮT. `_do_dich_ab.py` chạy
#: RIÊNG một arm bật nó lên để tách hai phần đó ra bằng SỐ.
VI_DU_RIENG = (
    " Ví dụ lỗi thật của kênh này phải tránh: "
    '`新片` nghĩa là "phim mới" — dịch thành "chip" là SAI HẲN; '
    '`落魄拳手` là "võ sĩ sa cơ lỡ vận" — không phải "đầu bếp", không phải '
    '"võ sĩ xuống cấp".'
)


def _luat_chung(ten_dich: str, vi_du_rieng: bool = False) -> str:
    return (
        "QUY TẮC BẮT BUỘC:\n"
        "1. ĐÚNG NGHĨA TRƯỚC ĐÃ. Dịch đúng nghĩa MẶT CHỮ của từ khoá "
        "(tên riêng, con số, sự vật chính). TUYỆT ĐỐI KHÔNG đoán nghĩa theo "
        "ÂM ĐỌC hay theo từ trông na ná — một từ khoá dịch sai là người xem "
        "hiểu sai cả câu. Từ nào nhiều nghĩa thì chọn nghĩa hợp BỐI CẢNH cả "
        "video ở trên."
        + (VI_DU_RIENG if vi_du_rieng else "") + "\n"
        f"2. VĂN NÓI {ten_dich.upper()}, KHÔNG DỊCH MẶT CHỮ. Viết như người "
        "thật đang nói trong video. CẤM bê nguyên âm Hán-Việt (hoặc từ mượn "
        "của tiếng gốc) khi tiếng Việt đã có cách nói thường: "
        '"hắc ám" -> "tối tăm"; "tiểu tâm" -> "cẩn thận"; '
        '"khai thuỷ" -> "bắt đầu". Đọc lại câu mình vừa viết: người Việt có '
        "nói như thế không? Nghe gượng là viết lại.\n"
        "3. MỘT CÂU GỐC RA ĐÚNG MỘT CÂU DỊCH. Không gộp hai câu làm một, "
        "không tách một câu làm hai, không thêm câu mới, không bỏ câu nào.\n"
        "4. ĐỦ Ý — không cắt cụt thành mẩu ghi chú. Nhưng cũng KHÔNG thêm "
        "thông tin không có trong câu gốc để cho dài ra.\n"
        "5. KHÔNG chú thích, KHÔNG phiên âm, KHÔNG để sót chữ của tiếng gốc.\n"
    )


def _luat_do_dai() -> str:
    return (
        "ĐỘ DÀI — ĐÂY LÀ ĐIỂM KHÁC BIỆT, ĐỌC KỸ:\n"
        "Mỗi câu ghi `[<giây> giây · ~<N> chữ (<min>-<max>)]`. Máy sẽ đọc bản "
        "dịch của bạn trong ĐÚNG ngần ấy giây.\n"
        "- Viết khoảng **N chữ**, và BẮT BUỘC nằm trong khoảng min-max.\n"
        "- 'Chữ' = tiếng tách bởi dấu cách, ví dụ 'Bảy bộ phim mới đang hot' "
        "= 6 chữ.\n"
        "- NGẮN QUÁ thì hình chạy mà không có tiếng — hãy nói TRỌN Ý, thêm "
        "chủ ngữ / từ nối / cách nói tự nhiên cho đủ nhịp.\n"
        "- DÀI QUÁ thì máy phải đọc nhanh, méo tiếng — hãy bỏ từ đệm, chọn từ "
        "ngắn hơn, GIỮ NGUYÊN ý chính.\n"
        "- **TUYỆT ĐỐI KHÔNG BỊA THÊM Ý cho đủ số chữ.** Câu gốc ngắn thì bản "
        "dịch được phép ngắn — thà thiếu vài chữ còn hơn thêm một chi tiết "
        "không có trong câu gốc. Số chữ ghi ở trên đã tính sẵn theo độ dài "
        "câu gốc rồi.\n"
        "- ĐẾM LẠI số chữ trước khi trả.\n"
    )


def _mo_ta_cau(i: int, c: dict, ns: dict) -> str:
    t = str(c.get("text") or "")[:400]
    khoang = (f"{ns['min']}-{ns['max']}" if ns["min"]
              else f"tối đa {ns['max']}")
    return f'#{i} [{ns["giay"]:.1f} giây · ~{ns["dich"]} chữ ({khoang})]: "{t}"'


# --------------------------------------------------------------------------
# DỊCH
# --------------------------------------------------------------------------
def _dich_goi(cau: list[dict], chi_so: list[int], ns: list[dict],
              dich_sang: str, goc_ma: str, boi_canh: str,
              model: Optional[str] = None,
              vi_du_rieng: bool = False) -> dict[int, str]:
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = [_mo_ta_cau(i, cau[i], ns[i]) for i in chi_so]
    prompt = (
        f"Dịch lời thoại video từ {_ten_nn(goc_ma)} sang {ten_dich}.\n\n"
        f"BỐI CẢNH CẢ VIDEO (để hiểu đúng thuật ngữ, KHÔNG dịch phần này):\n"
        f"\"{boi_canh}\"\n\n"
        f"CÁC CÂU CẦN DỊCH:\n{chr(10).join(items)}\n\n"
        + _luat_chung(ten_dich, vi_du_rieng)
        + _luat_do_dai()
        + f"\nTrả MẢNG JSON {len(chi_so)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
        "BẮT BUỘC đủ MỌI số #."
    )
    try:
        data = llm.complete_json(prompt, system=_SYSTEM, model=model)
    except Exception:                                    # noqa: BLE001
        return {}
    ra: dict[int, str] = {}
    for i, t in _theo_nhan(data, chi_so, "t").items():
        if isinstance(t, str) and t.strip():
            ra[i] = t.strip()
    return ra


def _viet_lai(cau: list[dict], chi_so: list[int], hien: list[str],
              ns: list[dict], dich_sang: str, goc_ma: str,
              model: Optional[str] = None) -> dict[int, str]:
    """Viết lại RIÊNG những câu lệch ngân sách, có nói rõ đang lệch bao nhiêu.

    Gửi kèm CHÍNH BẢN DỊCH ĐANG LỆCH + số chữ hiện tại: model sửa một bản có
    sẵn thì giữ được nghĩa tốt hơn hẳn dịch lại từ đầu (cùng cách
    `_dich_lai_sot` đang dùng cho câu sót chữ gốc).
    """
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = []
    for i in chi_so:
        n = am_tiet_viet(hien[i])
        huong = "DÀI QUÁ, phải rút ngắn" if n > ns[i]["max"] else \
                "NGẮN QUÁ, phải nói đủ ý cho dài ra"
        items.append(
            f'#{i} GỐC: "{str(cau[i].get("text") or "")[:300]}"\n'
            f'   BẢN DỊCH HIỆN TẠI ({n} chữ): "{hien[i][:300]}"\n'
            f'   -> {huong}: cần ~{ns[i]["dich"]} chữ '
            f'({ns[i]["min"] or 1}-{ns[i]["max"]}), khung {ns[i]["giay"]:.1f} giây')
    prompt = (
        f"Những bản dịch {ten_dich} dưới đây ĐÚNG NGHĨA nhưng SAI ĐỘ DÀI so "
        "với khung thời gian của câu gốc. Hãy viết lại cho vừa.\n"
        f"{chr(10).join(items)}\n\n"
        "QUY TẮC:\n"
        "- GIỮ NGUYÊN Ý của câu gốc. Rút ngắn thì bỏ từ đệm, KHÔNG bỏ ý "
        "chính. Kéo dài thì nói trọn ý bằng cách nói tự nhiên hơn — "
        "**TUYỆT ĐỐI KHÔNG bịa thêm chi tiết không có trong câu gốc**; "
        "không đủ chữ mà vẫn trọn ý thì cứ để ngắn.\n"
        f"- Vẫn phải là văn NÓI {ten_dich}, không dịch mặt chữ.\n"
        "- ĐẾM LẠI số chữ trước khi trả.\n"
        f"- Trả MẢNG JSON {len(chi_so)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<bản dịch mới>"}. '
        "BẮT BUỘC đủ MỌI số #."
    )
    try:
        data = llm.complete_json(prompt, system=_SYSTEM, model=model)
    except Exception:                                    # noqa: BLE001
        return {}
    ra: dict[int, str] = {}
    for i, t in _theo_nhan(data, chi_so, "t").items():
        if isinstance(t, str) and t.strip():
            ra[i] = t.strip()
    return ra


def _lech(n: int, ns: dict) -> bool:
    """Câu `n` chữ có lệch ngân sách `ns` không."""
    if n > ns["max"]:
        return True
    return bool(ns["min"]) and n < ns["min"]


def dich_theo_gio(cau: list[dict], dich_sang: str = "vi", goc_ma: str = "",
                  model: Optional[str] = None,
                  vong_viet_lai: int = VONG_VIET_LAI,
                  vi_du_rieng: bool = False,
                  on_progress: Optional[Callable[[float, str], None]] = None,
                  ) -> dict:
    """Dịch `cau` (list {text,start,end}) sang `dich_sang` THEO NGÂN SÁCH THỜI GIAN.

    Trả {ban_dich, ngan_sach, so_lech_truoc, so_lech_sau, so_viet_lai,
         sot_chu_goc, thieu_cau}.

    KHÔNG hứa "chuẩn 100%": trả về SỐ CÂU CÒN LỆCH sau khi viết lại để caller
    biết bản dịch vừa khung tới đâu. Câu LLM không trả được thì giữ nguyên câu
    GỐC (đúng cách `_dich_loat` đang làm) và đếm vào `thieu_cau` — không im
    lặng bịa.
    """
    n = len(cau)
    if not n:
        return {"ban_dich": [], "ngan_sach": [], "so_lech_truoc": 0,
                "so_lech_sau": 0, "so_viet_lai": 0, "sot_chu_goc": 0,
                "thieu_cau": 0}

    ns = [ngan_sach(float(c.get("end", 0)) - float(c.get("start", 0)),
                    str(c.get("text") or "")) for c in cau]
    bc = _boi_canh(cau)

    if on_progress:
        on_progress(0.10, f"Đang dịch {n} câu theo ngân sách thời gian...")

    ra: dict[int, str] = {}
    con = list(range(n))
    for _vong in range(VONG_DOI_LAI):
        if not con:
            break
        moi: dict[int, str] = {}
        for nhom in _chia_co(len(con)):
            phan = [con[j] for j in nhom]
            moi.update(_dich_goi(cau, phan, ns, dich_sang, goc_ma, bc, model,
                                 vi_du_rieng))
        if not moi:
            break
        ra.update(moi)
        con = [i for i in range(n) if i not in ra]

    thieu = len(con)
    ban_dich = [ra.get(i) or str(cau[i].get("text") or "") for i in range(n)]

    # ---- HẬU KIỂM NGÂN SÁCH ----
    lech0 = [i for i in range(n) if _lech(am_tiet_viet(ban_dich[i]), ns[i])]
    da_sua = 0
    lech = list(lech0)
    for _vong in range(max(0, vong_viet_lai)):
        if not lech:
            break
        if on_progress:
            on_progress(0.75, f"Viết lại {len(lech)} câu lệch khung...")
        moi: dict[int, str] = {}
        for nhom in _chia_co(len(lech)):
            phan = [lech[j] for j in nhom]
            moi.update(_viet_lai(cau, phan, ban_dich, ns, dich_sang, goc_ma,
                                 model))
        doi = 0
        for i, t in moi.items():
            # CHỈ NHẬN khi bản mới THẬT SỰ gần ngân sách hơn và không đẻ ra
            # lỗi mới (rỗng · còn chữ gốc). Nhận bừa là đổi câu lệch này lấy
            # câu lệch khác rồi tự khen đã chữa — đúng bẫy `_dich_lai_sot`.
            if not t.strip() or _con_chu_goc(t, dich_sang):
                continue
            cu = abs(am_tiet_viet(ban_dich[i]) - ns[i]["dich"])
            mo = abs(am_tiet_viet(t) - ns[i]["dich"])
            if mo < cu:
                ban_dich[i] = t
                doi += 1
        da_sua += doi
        lech = [i for i in lech if _lech(am_tiet_viet(ban_dich[i]), ns[i])]
        if not doi:
            break                        # LLM không nhúc nhích -> đừng đốt lượt

    return {
        "ban_dich": ban_dich,
        "ngan_sach": ns,
        "so_lech_truoc": len(lech0),
        "so_lech_sau": len(lech),
        "so_viet_lai": da_sua,
        "sot_chu_goc": sum(1 for t in ban_dich if _con_chu_goc(t, dich_sang)),
        "thieu_cau": thieu,
    }


# --------------------------------------------------------------------------
# NỐI THƯỚC VÀO ĐƯỜNG DỊCH
# --------------------------------------------------------------------------
def dich_va_soat(cau: list[dict], dich_sang: str = "vi", goc_ma: str = "",
                 model: Optional[str] = None,
                 vong_soat: int = 1,
                 vi_du_rieng: bool = False,
                 on_progress: Optional[Callable[[float, str], None]] = None,
                 ) -> dict:
    """`dich_theo_gio` + CHẤM bằng `cham_dich` + dịch lại RIÊNG câu trượt.

    **CHỈ ĐƯỢC BẬT KHI THƯỚC ĐÃ ĐỦ YÊN.** Ở v1 (kêu oan 34,2% ngoài mẫu) hàm
    này là cỗ máy phá bản dịch tốt: cứ 3 câu đã tốt thì 1 câu bị đem đi dịch
    lại, mà bước dịch lại đã đo được là CÓ CƠ LÀM XẤU ĐI (−0,58 .. −1,24
    điểm). v2 hạ kêu oan về **8,3%** nên đường này mới có nghĩa.

    HAI CHỐT CHỐNG TỰ PHÁ, đừng gỡ:
      · **CHỈ NHẬN bản mới khi nó ĐẠT** (bản cũ trượt, bản mới đạt). Bản mới
        cũng trượt -> GIỮ BẢN CŨ; đổi một câu trượt lấy một câu trượt khác
        rồi tự khen đã chữa là đúng bẫy `_dich_lai_sot` đã ghi.
      · Thước hỏng / hết lượt / mạng chết -> GIỮ NGUYÊN toàn bộ bản dịch đầu,
        KHÔNG bao giờ ném (fail-safe, cùng luật `mach_lac`).

    Trả kết quả của `dich_theo_gio` + {dat_truoc, dat_sau, so_dich_lai,
    so_nhan, cau_cham}.
    """
    from app.ai import cham_dich as CD

    kq = dich_theo_gio(cau, dich_sang, goc_ma, model,
                       vi_du_rieng=vi_du_rieng, on_progress=on_progress)
    goc = [str(c.get("text") or "") for c in cau]
    bd = list(kq["ban_dich"])
    ns = kq["ngan_sach"]
    kq.update({"dat_truoc": None, "dat_sau": None, "so_dich_lai": 0,
               "so_nhan": 0, "cau_cham": []})
    if not bd:
        return kq

    try:
        if on_progress:
            on_progress(0.80, f"Soát lại {len(bd)} câu bằng thước chấm...")
        cham = CD.cham_ban_dich(goc, bd, goc_ma=goc_ma or "zh",
                                dich_ma=dich_sang)
    except Exception:                                    # noqa: BLE001
        return kq                                        # KHÔNG có thước -> thôi
    kq["cau_cham"] = cham["cau"]
    kq["dat_truoc"] = cham["ty_le_dat"]
    kq["dat_sau"] = cham["ty_le_dat"]

    for _vong in range(max(0, vong_soat)):
        xau = [i for i, c in enumerate(cham["cau"]) if not c["dat"]]
        if not xau:
            break
        kq["so_dich_lai"] += len(xau)
        if on_progress:
            on_progress(0.88, f"Dịch lại {len(xau)} câu thước chấm trượt...")
        moi: dict[int, str] = {}
        for nhom in _chia_co(len(xau)):
            phan = [xau[j] for j in nhom]
            moi.update(_dich_lai_xau(cau, phan, bd, ns, cham["cau"],
                                     dich_sang, goc_ma, model, vi_du_rieng))
        thu = list(bd)
        doi = [i for i, t in moi.items()
               if t.strip() and t.strip() != bd[i]
               and not _con_chu_goc(t, dich_sang)]
        for i in doi:
            thu[i] = moi[i].strip()
        if not doi:
            break
        try:
            lai = CD.cham_ban_dich([goc[i] for i in doi],
                                   [thu[i] for i in doi],
                                   goc_ma=goc_ma or "zh", dich_ma=dich_sang)
        except Exception:                                # noqa: BLE001
            break
        nhan = 0
        for j, i in enumerate(doi):
            if lai["cau"][j]["dat"]:                     # CHỈ NHẬN khi ĐẠT
                bd[i] = thu[i]
                cham["cau"][i] = lai["cau"][j]
                nhan += 1
        kq["so_nhan"] += nhan
        if not nhan:
            break
    kq["ban_dich"] = bd
    kq["dat_sau"] = round(100.0 * sum(1 for c in cham["cau"] if c["dat"])
                          / max(1, len(cham["cau"])), 1)
    kq["sot_chu_goc"] = sum(1 for t in bd if _con_chu_goc(t, dich_sang))
    return kq


def _ly_do(c: dict) -> str:
    """Nói cho model biết câu của nó bị chê ĐÚNG chỗ nào — chê chung chung
    thì nó viết lại một câu khác cùng bệnh."""
    from app.ai import cham_dich as CD
    ra = []
    ma = {"cut": "bị CỤT, thiếu ý", "gop": "GỘP hai câu làm một",
          "con_chu_goc": "còn sót chữ của tiếng gốc",
          "chep_goc": "chép nguyên câu gốc", "rong": "rỗng"}
    for m in c.get("loi") or []:
        ra.append(ma.get(m, m))
    if c.get("thuat_ngu"):
        ra.append("dịch sai từ khoá: " + "; ".join(c["thuat_ngu"][:3]))
    ten = {"nghia": "SAI NGHĨA", "xuoi": "KHÔNG XUÔI tiếng Việt",
           "noi": "KHÔNG PHẢI VĂN NÓI", "tron": "THIẾU/THỪA ý"}
    for k, v in CD.NGUONG_TRUC.items():
        x = c.get(k)
        if x is not None and x < v:
            ra.append(f"{ten[k]} (chấm {x:.0f}/10)")
    return " · ".join(ra) or "chưa đạt"


def _dich_lai_xau(cau: list[dict], chi_so: list[int], hien: list[str],
                  ns: list[dict], cham: list[dict], dich_sang: str,
                  goc_ma: str, model: Optional[str] = None,
                  vi_du_rieng: bool = False) -> dict[int, str]:
    """Dịch lại câu thước chấm TRƯỢT, gửi kèm LÝ DO TRƯỢT."""
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = []
    for i in chi_so:
        items.append(
            f'#{i} GỐC: "{str(cau[i].get("text") or "")[:300]}"\n'
            f'   BẢN DỊCH BỊ CHÊ: "{hien[i][:300]}"\n'
            f'   LÝ DO: {_ly_do(cham[i])}\n'
            f'   cần ~{ns[i]["dich"]} chữ, khung {ns[i]["giay"]:.1f} giây')
    prompt = (
        f"Những bản dịch {ten_dich} dưới đây đã bị người soát ĐÁNH TRƯỢT. "
        "Hãy dịch LẠI cho đúng, sửa ĐÚNG cái bị chê.\n"
        f"{chr(10).join(items)}\n\n"
        + _luat_chung(ten_dich, vi_du_rieng)
        + "- Đừng viết lại y như cũ: nó đã bị trượt vì lý do ghi ở trên.\n"
        + f"- Trả MẢNG JSON {len(chi_so)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<bản dịch mới>"}. '
        "BẮT BUỘC đủ MỌI số #."
    )
    try:
        data = llm.complete_json(prompt, system=_SYSTEM, model=model)
    except Exception:                                    # noqa: BLE001
        return {}
    ra: dict[int, str] = {}
    for i, t in _theo_nhan(data, chi_so, "t").items():
        if isinstance(t, str) and t.strip():
            ra[i] = t.strip()
    return ra
