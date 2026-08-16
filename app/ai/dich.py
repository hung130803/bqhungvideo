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


def ngan_sach(giay: float) -> dict:
    """Ngân sách CHỮ cho một khung `giay`: {dich, min, max, giay}.

    `min` = 0 nghĩa là khung quá ngắn để đặt sàn (xem `KHUNG_TOI_THIEU`).
    """
    giay = max(0.0, float(giay))
    nho = giay < KHUNG_TOI_THIEU
    return {
        "giay": round(giay, 2),
        "dich": am_tiet_vua(giay, NHAM),
        "min": 0 if nho else max(1, int((giay * SAN - GIAY_CO_DINH)
                                        / GIAY_MOI_AM_TIET)),
        "max": max(2, int((giay * TRAN - GIAY_CO_DINH) / GIAY_MOI_AM_TIET)),
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


def _luat_chung(ten_dich: str) -> str:
    return (
        "QUY TẮC BẮT BUỘC:\n"
        f"1. ĐÚNG NGHĨA TRƯỚC ĐÃ. Dịch đúng nghĩa MẶT CHỮ của từ khoá "
        "(tên riêng, con số, sự vật chính). TUYỆT ĐỐI KHÔNG đoán nghĩa theo "
        "ÂM ĐỌC hay theo từ trông giống. Ví dụ lỗi thật phải tránh: "
        '`新片` nghĩa là "phim mới" — dịch thành "chip" là SAI HẲN; '
        '`落魄拳手` là "võ sĩ sa cơ lỡ vận" — không phải "đầu bếp", không '
        'phải "võ sĩ xuống cấp".\n'
        f"2. VĂN NÓI {ten_dich.upper()}, KHÔNG DỊCH MẶT CHỮ. Viết như người "
        "thật đang nói trong video. CẤM bê nguyên từ Hán-Việt/từ gốc khi "
        'tiếng Việt có cách nói thường: "trường diện" -> "cảnh phim"; '
        '"tuyệt cảnh cầu sinh" -> "tìm đường sống giữa đường cùng"; '
        '"quyền quyền đến thịt" -> "đấm phát nào ra phát nấy". Đọc lại câu '
        "mình vừa viết: người Việt có nói như thế không?\n"
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
        "- NGẮN QUÁ thì hình chạy mà không có tiếng — hãy nói trọn ý, thêm "
        "chủ ngữ / từ nối / cách nói tự nhiên cho đủ nhịp.\n"
        "- DÀI QUÁ thì máy phải đọc nhanh, méo tiếng — hãy bỏ từ đệm, chọn từ "
        "ngắn hơn, GIỮ NGUYÊN ý chính.\n"
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
              model: Optional[str] = None) -> dict[int, str]:
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = [_mo_ta_cau(i, cau[i], ns[i]) for i in chi_so]
    prompt = (
        f"Dịch lời thoại video từ {_ten_nn(goc_ma)} sang {ten_dich}.\n\n"
        f"BỐI CẢNH CẢ VIDEO (để hiểu đúng thuật ngữ, KHÔNG dịch phần này):\n"
        f"\"{boi_canh}\"\n\n"
        f"CÁC CÂU CẦN DỊCH:\n{chr(10).join(items)}\n\n"
        + _luat_chung(ten_dich)
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
        "chính. Kéo dài thì nói trọn ý bằng cách nói tự nhiên hơn, KHÔNG bịa "
        "thêm thông tin không có trong câu gốc.\n"
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

    ns = [ngan_sach(float(c.get("end", 0)) - float(c.get("start", 0)))
          for c in cau]
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
            moi.update(_dich_goi(cau, phan, ns, dich_sang, goc_ma, bc, model))
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
