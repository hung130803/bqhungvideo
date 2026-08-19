# -*- coding: utf-8 -*-
"""GIỌNG NÀO ĐỌC ĐƯỢC TIẾNG NÀO — **SỐ ĐO, KHÔNG PHẢI NHÃN CỦA NHÀ CUNG CẤP**.

Anh Hùng 19/08/2026: *"Giọng nào đọc chỉ 1 ngôn ngữ thì ghi rõ; cái nào 1
giọng đọc được cả tiếng Anh tiếng Việt cũng được"* · *"giọng nào đa ngôn ngữ
cứ báo tôi nhé, nhiều giọng đọc hết oke cả Hàn Nhật Mỹ Trung mà rất hay ấy"*.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CẦN FILE NÀY: NHÃN CŨ LẤY TỪ **TÊN GIỌNG**
═══════════════════════════════════════════════════════════════════════════
``giong_bang.da_ngu(vid)`` trả True khi **tên giọng có chữ "Multilingual"** —
tức app đang tin lời Microsoft, chưa ai bắt đọc thử. Ca đối chiếu nằm ngay
trong repo và nó đắt: **Chatterbox** cũng tự nhận đa ngôn ngữ, ép đọc *"Một
cơn bão chưa từng có"* thì ra ***"Mokonbel, Chutanko, Tronglaichsatanglaich"***
— sai 100%, **không ném lỗi, mã thoát 0**.

═══════════════════════════════════════════════════════════════════════════
KẾT QUẢ ĐO — VÀ NÓ **LẬT LẠI** GIẢ THIẾT BAN ĐẦU, PHẢI NÓI THẲNG
═══════════════════════════════════════════════════════════════════════════
Việc này được giao với mệnh đề *"nhãn Multilingual KHÔNG phải bằng chứng"*.
Đo xong 103 arm (``_do_5_tieng.py``) thì **nhãn đó phần lớn ĐÚNG**:

* **0/12** giọng ``*Multilingual*`` đo ra KHÔNG đọc được tiếng Việt.
* **10/12** đọc được **cả 5 tiếng** (Việt · Anh · Hàn · Nhật · Trung).
* **1 ca hỏng thật**: ``en-US-AndrewMultilingual`` × **tiếng HÀN** (token đọc
  rời sai **75%**, trần 0%) — nhãn nhà cung cấp nói "mọi thứ tiếng" mà nó
  trượt đúng một tiếng.
* **2 ô hai thước đá nhau** (``AndrewMultilingual`` và ``AvaMultilingual`` ×
  tiếng Việt) -> ghi ``None`` = CHƯA KẾT LUẬN, không gọi là hỏng.

Thước PHỤ ĐỘC LẬP đồng ý: hỏi máy nghe *"tiếng phát ra là tiếng gì"*
(``language=None``, không liên quan việc chấm chữ) thì **cả 12 giọng đều 3/3
đúng tiếng ở mọi tiếng**. Hai thước khác nhau cùng chỉ một hướng.

Ngược lại, **SÀN đúng như dự đoán**: ``en-US-Andrew`` (giọng MỘT tiếng) trượt
**cả 4** tiếng ngoài; ``vi-VN-HoaiMy`` trượt tiếng Anh và **KHÔNG RA NỔI MỘT
FILE TIẾNG NÀO** với chữ Hàn/Nhật/Trung (11/11 mẫu hỏng, mỗi arm ~300 giây
thử lại). Ca đó là hỏng CỨNG — chọn nhầm thì lượt xuất KHÔNG CÓ TIẾNG chứ
không ra chữ vô nghĩa, tức app FAIL TO chứ không im lặng.

═══════════════════════════════════════════════════════════════════════════
NGƯỠNG ĐẶT BẰNG SỐ, VÀ CHỈ KẾT LUẬN KHI HAI THƯỚC ĐỒNG Ý
═══════════════════════════════════════════════════════════════════════════
Mỗi tiếng có TRẦN (giọng bản ngữ đọc tiếng của nó) và SÀN (giọng một-tiếng bị
ép đọc tiếng khác) đo trong CÙNG lượt; ngưỡng nằm GIỮA khoảng trống. Cột kết
luận là **token ĐỌC RỜI** (máy nghe không còn ngữ cảnh để chữa hộ máy đọc —
chênh đo được **+12,2 điểm** toàn bộ, riêng tiếng Việt **+47,9**).

Ngưỡng đọc rời: Việt **87,5%** · Anh **37,5%** · Hàn **37,5%** ·
Nhật **50,0%** · Trung **25,0%**.

**CẤM SO CHÉO TIẾNG**: vi/en chấm theo TỪ, ko/ja/zh chấm theo KÝ TỰ — hai đơn
vị khác nhau. Mọi kết luận so với TRẦN của CHÍNH tiếng đó.

**HAI THƯỚC PHẢI ĐỒNG Ý.** Cột đọc rời một mình không đủ, và đây là số:
``AvaMultilingual`` đọc câu Việt TRƠN sai **0,0%** (bằng trần) mà **4/4 tên
riêng đọc rời đều sai**; mà chính TRẦN tiếng Việt cũng sai **50-75%** ở cột
đó (``HoaiMy`` 2/4 · ``NamMinh`` 3/4) — phần lớn cái "sai" ấy là **máy NGHE
không chép nổi một tên riêng Việt đứng một mình**, không phải máy ĐỌC sai.
Chọn một cột làm quan toà là tự chọn kết luận; đòi hai cột đồng ý thì ca Ava
ra "CHƯA KẾT LUẬN" — câu trả lời đúng.

═══════════════════════════════════════════════════════════════════════════
BA NHÃN, KHÔNG MẬP MỜ
═══════════════════════════════════════════════════════════════════════════
Mỗi dòng combo rơi vào ĐÚNG MỘT:

1. **"đọc được: Việt · Anh · ..."** — có trong ``BANG``, >= 2 tiếng ``True``.
2. **"chỉ đọc tiếng X"** — có trong ``BANG`` và chỉ 1 tiếng ``True``; hoặc
   giọng edge-tts CHƯA đo nhưng mã mang locale (``en-GB-RyanNeural``).
3. **"chưa đo"** — không suy ra được gì.

**VÌ SAO ĐƯỢC PHÉP SUY TỪ LOCALE Ở NHÃN 2** (mà KHÔNG được phép suy từ chữ
"Multilingual" ở nhãn 1): vì có bằng chứng ở mức LỚP. Hai giọng locale được
đem thử ép đọc tiếng khác (``en-US-Andrew`` · ``vi-VN-HoaiMy``) thì **trượt
8/8 ô** — không một ngoại lệ. Còn chữ "Multilingual" thì hứa **5 tiếng cùng
lúc**, tức hứa nhiều hơn hẳn, nên phải đo. Nhãn 2 vẫn ghi rõ là suy từ mã
giọng (``_SUY_TU_MA``) để không ai đọc nhầm thành số đo.

**KHÔNG BỊA MỘT TIẾNG NÀO CẠNH TÊN GIỌNG.** Bịa là người dùng TIN mà chọn —
đúng luật ``nhan_nha.nhan`` đã chốt. Tiếng chưa đo thì không có mặt trong
danh sách, chứ không đoán.

**SINH RA TỪ PHÉP ĐO, ĐỪNG SỬA TAY** — chạy ``_ra_bang_da_ngu.py --ghi``.
"""
from __future__ import annotations

#: Năm tiếng anh Hùng cần phủ, theo thứ tự hiện ra trên nhãn.
NN5: tuple[str, ...] = ("vi", "en", "ko", "ja", "zh")

#: Tên tiếng Việt của mã ngôn ngữ. Chỉ 5 tiếng đã đo + vài tiếng hay gặp để
#: nhãn "chỉ đọc tiếng X" đọc được bằng tiếng Việt.
TEN_TIENG: dict[str, str] = {
    "vi": "Việt", "en": "Anh", "ko": "Hàn", "ja": "Nhật", "zh": "Trung",
    "th": "Thái", "id": "Indonesia", "hi": "Hindi", "ar": "Ả Rập",
    "fr": "Pháp", "de": "Đức", "es": "Tây Ban Nha", "pt": "Bồ Đào Nha",
    "ru": "Nga", "it": "Ý", "ms": "Mã Lai", "nl": "Hà Lan", "pl": "Ba Lan",
    "tr": "Thổ Nhĩ Kỳ", "sv": "Thuỵ Điển", "he": "Do Thái", "km": "Khmer",
    "lo": "Lào", "my": "Miến", "fil": "Philippines",
}

#: Đuôi nhãn cho giọng CHƯA ĐO. **KHÔNG EMOJI** (máy anh Hùng thiếu glyph ->
#: ô đen, bài học v2.6.22).
CHUA_DO = " - chưa đo đọc được tiếng gì"

#: Đuôi ghi rõ nhãn này SUY TỪ MÃ GIỌNG, không phải số đo. Có nó thì người
#: đọc phân biệt được "đã bắt đọc thử" với "tin theo mã".
_SUY_TU_MA = " (theo mã giọng, chưa đo)"

#: (giọng, tiếng) mà máy đọc **KHÔNG RA NỔI MỘT FILE TIẾNG NÀO** — khác hẳn
#: "ra tiếng nhưng sai chữ". Đo được: ``vi-VN-HoaiMy`` + chữ Hàn/Nhật/Trung
#: hỏng **11/11 mẫu**, mỗi arm ~300 giây thử lại, trong khi arm tiếng Anh của
#: CÙNG giọng chạy ngon trong 46 giây -> không phải mạng chập chờn mà là dịch
#: vụ TỪ CHỐI.
#:
#: Phải tách vì **lời cảnh báo khác nhau**: ca này lượt xuất **KHÔNG CÓ
#: TIẾNG** (app FAIL TO, người dùng thấy ngay) còn ca "sai chữ" thì app im
#: lặng ra 300 video hỏng. Nói ca hỏng-cứng thành ca im-lặng là báo sai bệnh,
#: đúng lỗi đã ghi ở cổng 74 (*"lời lỗi phải đúng bệnh"*).
KHONG_RA_TIENG: frozenset[tuple[str, str]] = frozenset({
    ("vi-VN-HoaiMyNeural", "ko"),
    ("vi-VN-HoaiMyNeural", "ja"),
    ("vi-VN-HoaiMyNeural", "zh"),
})

#: voice_id -> {mã tiếng: True (đọc được) · False (KHÔNG) · None (chưa kết
#: luận được — hai thước đá nhau)}. Tiếng KHÔNG có mặt = CHƯA ĐO tiếng đó.
#:
#: **SINH TỪ `_ra_bang_da_ngu.py`, ĐỪNG GÕ TAY.** Sắp theo số tiếng đọc được
#: giảm dần.
BANG: dict[str, dict[str, bool | None]] = {
    "de-DE-FlorianMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "de-DE-SeraphinaMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "en-AU-WilliamMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "en-US-BrianMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "en-US-EmmaMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "fr-FR-RemyMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "fr-FR-VivienneMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "it-IT-GiuseppeMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "ko-KR-HyunsuMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "pt-BR-ThalitaMultilingualNeural": {"vi": True, "en": True, "ko": True, "ja": True, "zh": True},
    "en-US-AvaMultilingualNeural": {"vi": None, "en": True, "ko": True, "ja": True, "zh": True},
    "en-US-AndrewMultilingualNeural": {"vi": None, "en": True, "ko": False, "ja": True, "zh": True},
    "en-US-AndrewNeural": {"vi": False, "en": True, "ko": False, "ja": False, "zh": False},
    "en-US-AriaNeural": {"en": True},
    "ja-JP-KeitaNeural": {"ja": True},
    "ja-JP-NanamiNeural": {"ja": True},
    "ko-KR-InJoonNeural": {"ko": True},
    "ko-KR-SunHiNeural": {"ko": True},
    "vi-VN-HoaiMyNeural": {"vi": True, "en": False, "ko": False, "ja": False, "zh": False},
    "vi-VN-NamMinhNeural": {"vi": True},
    "zh-CN-XiaoxiaoNeural": {"zh": True},
    "zh-CN-YunxiNeural": {"zh": True},
}


def _bo_pitch(vid: str) -> str:
    """`vi-VN-HoaiMyNeural|+10Hz` -> `vi-VN-HoaiMyNeural`.

    Biến thể cao độ là CÙNG một người đọc nên nó thừa hưởng kết quả đo của
    giọng gốc. Mã Chatterbox (`cb:en|D:/mau.wav`) cũng chứa `|` nhưng nó
    KHÔNG phải biến thể cao độ -> chừa ra, nếu không thì cắt mất đường dẫn
    mẫu rồi tra sai bảng.
    """
    s = str(vid or "")
    if ":" in s.split("|")[0]:
        return s
    return s.split("|", 1)[0]


def ten_tieng(nn: str, vid: str = "") -> str:
    """Tên tiếng Việt của mã ngôn ngữ; mã lạ -> nói thẳng là mã, đừng in trần.

    `TEN_TIENG` chỉ có 25 tiếng, còn edge-tts có **75**. In trần mã ra thành
    *"chỉ đọc tiếng af"* là một dòng combo đọc không hiểu — mà người dùng vẫn
    tưởng đó là tên tiếng. Nói *"theo mã «af-ZA»"* thì họ biết đó là mã và
    tra được.
    """
    nn = str(nn or "").split("-")[0].lower()
    if nn in TEN_TIENG:
        return TEN_TIENG[nn]
    v = _bo_pitch(vid)
    goc = "-".join(v.split("-")[:2]) if v.count("-") >= 2 else nn
    return f"theo mã «{goc}»"


def _locale(vid: str) -> str:
    """Mã tiếng suy từ MÃ GIỌNG edge-tts ("" = không suy được).

    `en-GB-RyanNeural` -> `en`. Giọng `*Multilingual*` trả "" (mã của chúng
    mang locale của giọng gốc chứ không nói gì về tiếng chúng đọc được — đó
    đúng là chỗ nhãn cũ sai). Mã không phải edge-tts trả "".
    """
    v = _bo_pitch(vid)
    if ":" in v or "multilingual" in v.lower():
        return ""
    phan = v.split("-")
    return phan[0].lower() if len(phan) >= 3 else ""


def _tieng_theo_bo_doc(vid: str) -> str:
    """Tiếng mà BỘ ĐỌC này sinh ra được, suy từ chính module nguồn ("" = ?).

    Khác ``_locale`` (suy từ mã edge-tts) ở chỗ đây là thuộc tính của **MODEL**:
    ``vn:`` là VieNeu — một bộ đọc TIẾNG VIỆT (19/20 giọng Việt, riêng
    ``Adam`` tiếng Anh) · ``piper:`` chỉ có model ``vais1000`` tiếng Việt ·
    ``cb:<tiếng>|<mẫu>`` mang tiếng THẲNG TRONG MÃ (Chatterbox bắt buộc
    ``language_id``).

    **LẤY TỪ MODULE NGUỒN, KHÔNG GÕ TAY.** Gõ tay tên "Adam" vào đây là tự đẻ
    một bản sao của ``giong_vieneu.GIONG_TIENG_ANH`` rồi hai bên trôi khác
    nhau — đúng cái bẫy ``_TIEN_TO`` của ``giong_bang`` đã sập hai lần với
    ``vn:`` và ``cb:``. Import HOÃN (trong hàm) để không tạo vòng import.
    """
    v = _bo_pitch(vid)
    if v.startswith("cb:"):
        try:
            from app.core import giong_chatter as gc
            lang, duong = gc.tach_ma(v)
            return lang if (lang and duong) else ""
        except Exception:                                      # noqa: BLE001
            return ""
    if v.startswith(("vn:", "vnb:")):
        try:
            from app.core import giong_vieneu as gv
            if v.startswith(gv.TIEN_TO_NB):
                return ""              # giọng nhân bản: tiếng theo file mẫu
            return "en" if gv.ten_giong(v) in gv.GIONG_TIENG_ANH else "vi"
        except Exception:                                      # noqa: BLE001
            return ""
    if v.startswith("piper:"):
        try:
            from app.core import piper_tts as pt
            return "vi" if pt.TEN_MODEL in v else ""
        except Exception:                                      # noqa: BLE001
            return ""
    return ""


def da_do(vid: str) -> bool:
    """Giọng này đã bị bắt đọc thử chưa."""
    return _bo_pitch(vid) in BANG


def doc_duoc(vid: str, nn: str) -> bool | None:
    """Giọng `vid` có đọc được tiếng `nn`? True / False / None (chưa biết).

    **None KHÔNG PHẢI "KHÔNG"** — nó là "chưa đo / chưa kết luận được". Nơi
    gọi phải phân biệt: cảnh báo cho `False` là nói ra một điều ĐÃ ĐO; cảnh
    báo cho `None` là dọa người dùng bằng chỗ mình chưa biết.
    """
    nn = str(nn or "").split("-")[0].lower()
    d = BANG.get(_bo_pitch(vid))
    if d is not None and nn in d:
        return d[nn]
    lo = _locale(vid) or _tieng_theo_bo_doc(vid)
    if lo:
        # Suy từ mã giọng / bộ đọc: giọng một-tiếng đọc ĐÚNG tiếng của nó (đo
        # 8/8 arm TRẦN đều đạt) và TRƯỢT tiếng khác (đo 8/8 arm SÀN đều
        # trượt). Với `vn:`/`piper:` còn có bằng chứng RIÊNG: VieNeu đọc chữ
        # Nhật/Trung ra **11/11 mẫu hỏng hết**, tức từ chối hẳn.
        return lo == nn
    return None


def cac_tieng(vid: str) -> tuple[list[str], list[str], list[str]]:
    """(đọc được, KHÔNG đọc được, chưa kết luận) — chỉ tiếng ĐÃ ĐO."""
    d = BANG.get(_bo_pitch(vid)) or {}
    co = [n for n in NN5 if d.get(n) is True]
    khong = [n for n in NN5 if n in d and d[n] is False]
    chua = [n for n in NN5 if n in d and d[n] is None]
    return co, khong, chua


def nhan(vid: str) -> str:
    """Đuôi nhãn cho một dòng combo — RƠI VÀO ĐÚNG MỘT trong ba trạng thái.

    Trả chuỗi bắt đầu bằng ``" - "`` để dán thẳng vào cuối dòng, hoặc ``""``
    khi không biết gì (nơi gọi tự quyết định có ghi "chưa đo" hay không).
    """
    co, khong, chua = cac_tieng(vid)
    if co and len(co) >= 2:
        s = " - đọc được: " + " · ".join(TEN_TIENG.get(n, n) for n in co)
        if khong:
            s += (" · KHÔNG đọc được "
                  + " · ".join(TEN_TIENG.get(n, n) for n in khong))
        if chua:
            s += (" · chưa rõ "
                  + " · ".join(TEN_TIENG.get(n, n) for n in chua))
        return s
    if co:
        return f" - chỉ đọc tiếng {ten_tieng(co[0], vid)}"
    lo = _locale(vid)
    if lo:
        return f" - chỉ đọc tiếng {ten_tieng(lo, vid)}{_SUY_TU_MA}"
    return CHUA_DO


def nhan_gon(vid: str) -> str:
    """Bản NGẮN của `nhan()` — dùng cho DÒNG COMBO.

    Combo lúc ĐÓNG chỉ rộng bằng hộp nên **quá ~60 ký tự là phần sau không ai
    đọc được** (`giong_vieneu.nhan_giong` đã đo và chốt điều đó). Bản dài của
    `nhan()` đi vào TOOLTIP; dòng chỉ mang phần SẼ HỎNG NGAY nếu chọn sai.

    Ba trạng thái vẫn phân biệt được TỪ CHÍNH DÒNG, không cần mở tooltip:
    ``(đã đo)`` · ``(theo mã, chưa đo)`` · ``chưa đo``. Thiếu dấu phân biệt đó
    thì "chỉ đọc tiếng Anh" của một giọng ĐÃ THỬ trông y hệt của một giọng chỉ
    được ĐOÁN theo mã — đúng cái mập mờ việc này đi chữa.
    """
    co, khong, chua = cac_tieng(vid)
    if co and len(co) >= 2:
        s = " - đọc được " + "·".join(ten_tieng(n, vid) for n in co) + " (đo)"
        if khong:
            s += " · KHÔNG đọc được " + "·".join(
                ten_tieng(n, vid) for n in khong)
        return s
    # MỘT TIẾNG -> KHÔNG dán dấu (đo)/(chưa đo) vào DÒNG, để nó ở tooltip
    # (`nhan()`). Hai lý do, cả hai đo được:
    # (a) NGÂN SÁCH CHỮ: thêm 10 ký tự đẩy dòng VieNeu lên **138**, vượt trần
    #     132 của cổng 79 — mà trần đó tồn tại vì combo lúc ĐÓNG chỉ đọc được
    #     ~60 ký tự đầu, tức 10 ký tự cuối này gần như không ai thấy.
    # (b) GIÁ TRỊ THẤP: với giọng MỘT tiếng, hai đường (đã đo / suy từ mã)
    #     dẫn tới CÙNG một lời khuyên, và đường suy có bằng chứng 8/8 arm SÀN.
    #     Câu "chỉ tiếng Việt" KHÔNG nhận vơ là số đo nên nó không sai.
    # Chỗ PHẢI giữ dấu là nhánh NHIỀU TIẾNG ở trên — đúng chỗ nhãn của nhà
    # cung cấp từng nói quá, nên câu "đã ĐO" ở đó mới là thông tin.
    if co:
        return f" - chỉ tiếng {ten_tieng(co[0], vid)}"
    lo = _locale(vid) or _tieng_theo_bo_doc(vid)
    if lo:
        return f" - chỉ tiếng {ten_tieng(lo, vid)}"
    return " - chưa đo tiếng"


def canh_bao(vid: str, nn: str) -> str:
    """Lời cảnh báo khi người dùng chọn giọng này cho tiếng `nn` ("" = ổn).

    **CẤM IM LẶNG RA CHỮ VÔ NGHĨA** — đó đúng là ca ``ov:nu_am`` và
    Chatterbox đã sập: chọn giọng, xuất 300 video, không một dòng báo.
    Nhưng cũng cấm dọa bừa: ``None`` (chưa đo) có lời khác hẳn ``False``.
    """
    nn = str(nn or "").split("-")[0].lower()
    if not nn:
        return ""
    kq = doc_duoc(vid, nn)
    ten = TEN_TIENG.get(nn, nn)
    if kq is True:
        return ""
    if kq is False:
        co, _k, _c = cac_tieng(vid)
        them = ("; giọng này đo ra chỉ đọc được: "
                + " · ".join(TEN_TIENG.get(n, n) for n in co)) if co else ""
        if (_bo_pitch(vid), nn) in KHONG_RA_TIENG:
            return (f"Giọng này ĐO RA KHÔNG ĐỌC NỔI chữ {ten} — máy đọc trả "
                    f"về file RỖNG (11/11 mẫu), tức lượt xuất sẽ KHÔNG CÓ "
                    f"TIẾNG{them}.")
        # **"ĐO RA" CHỈ ĐƯỢC NÓI KHI THẬT SỰ CÓ ĐO Ô ĐÓ.** `doc_duoc` trả
        # False theo HAI đường: ô có trong `BANG` (đã bắt đọc thử), hoặc suy
        # từ mã giọng / bộ đọc. Bản đầu dùng chung một lời cho cả hai, nên
        # `vn:Adam` × tiếng Việt hiện ra *"Giọng này ĐO RA KHÔNG đọc được"*
        # trong khi **chưa ai bắt Adam đọc một câu tiếng Việt nào**. Nhận vơ
        # một phép đo không tồn tại là đúng thứ file này đi chữa, chỉ đổi
        # chiều — lần này chính app nói quá.
        d = BANG.get(_bo_pitch(vid)) or {}
        if d.get(nn) is False:
            return (f"Giọng này ĐO RA KHÔNG đọc được tiếng {ten} — chọn nó "
                    f"cho kênh tiếng {ten} là ra tiếng sai chữ mà app không "
                    f"báo{them}.")
        return (f"Giọng này là giọng tiếng "
                f"{ten_tieng(_locale(vid) or _tieng_theo_bo_doc(vid), vid)} — "
                f"chọn nó cho kênh tiếng {ten} thì nó đọc chữ {ten} bằng cách "
                f"phát âm của tiếng nó, ra tiếng sai chữ. (Suy từ mã giọng, "
                f"CHƯA đo riêng cặp này; hai giọng cùng loại đem thử đều "
                f"trượt 8/8.)")
    return (f"CHƯA ĐO giọng này với tiếng {ten} — chưa có số để nói nó đọc "
            f"được hay không. Nghe thử một clip trước khi chạy cả kênh.")
