# -*- coding: utf-8 -*-
"""GOM NHÓM DANH SÁCH GIỌNG — combo "Giọng đọc" phải ĐỌC ĐƯỢC, không phải dò.

**VÌ SAO CÓ FILE NÀY.** Anh Hùng gửi ảnh chụp combo Giọng đọc của v2.37.0:

    "phần chọn giọng nó không phân gì cả, rất lung tung, không biết chọn sao,
     sắp xếp lại cho tôi"

Ảnh cho thấy đúng bốn bệnh, và cả bốn đều là bệnh của CÁCH BÀY chứ không phải
của bản thân giọng — nên file này **KHÔNG BỎ MỘT GIỌNG NÀO**, chỉ xếp lại:

1. **Andrew hiện HAI LẦN, Brian hiện HAI LẦN.** Đây KHÔNG phải lỗi trùng lặp
   thật: ``en-US-AndrewNeural`` và ``en-US-AndrewMultilingualNeural`` là **hai
   giọng khác nhau**, đo nhấn nhá ra **4,49** và **3,79** (lệch 0,70 — ngoài
   mọi mức nhiễu của phép đo, xem ``nhan_nha`` mục "SỐ NÀY TIỀN ĐỊNH").
   **Gộp chúng lại là mất một giọng thật.** Cách chữa đúng là ghi rõ chúng
   khác nhau ở đâu ngay trên DÒNG (``ten_ro_rang``), vì combo lúc ĐÓNG chỉ
   hiện một dòng — nhãn nhóm không cứu được.
2. **Giọng đa ngôn ngữ trộn lẫn giọng tiếng Anh.** Hai thứ này trả lời hai câu
   hỏi khác nhau ("đọc được mọi tiếng" và "đọc tiếng Anh hay") nên phải nằm
   hai nhóm.
3. **Không biết cái nào miễn phí / tốn tiền / phải tải model.** Đây là câu hỏi
   TIỀN, hỏi sau khi đã chạy 300 kênh thì muộn -> ``duoi_dong()`` gắn thẳng
   vào dòng.
4. **Chọn tiếng Việt thì giọng Việt bị chôn dưới 47 giọng Anh** (con số 47 lấy
   từ ``dubbing.GIONG_MO_HET``, không phải ước). -> ``gom_nhom(ds, nn)`` xếp
   theo NGÔN NGỮ ĐÍCH đang chọn.

**BẤT BIẾN SỐNG CÒN — MỖI MÃ GIỌNG XUẤT HIỆN ĐÚNG MỘT LẦN.** Nhóm "Khuyên
dùng" **LẤY HẲN** giọng ra khỏi nhóm gốc chứ không chép thêm một bản. Chép
thêm là tự tay đẻ lại đúng cái bệnh số 1 mà anh Hùng vừa kêu — và lần này là
trùng THẬT (cùng một mã), tệ hơn hẳn ca Andrew.

**KHÔNG VIẾT LẠI THƯỚC NHẤN NHÁ.** Thứ tự trong mọi nhóm dùng
``nhan_nha.khoa_sap`` (cổng 76 đã dựng, đã có mốc). File này chỉ GOM NHÓM;
mọi con số nhấn nhá vẫn có một nguồn duy nhất là ``nhan_nha.BANG``.

**KHÔNG NẠP Qt, KHÔNG GỌI MẠNG, KHÔNG ĐỌC ĐĨA.** Hàm thuần nhận vào danh sách
``[(nhãn, mã)]`` và trả ra danh sách cùng dạng, nên cổng test chấm được ở mức
đơn vị mà không phải dựng giao diện.

**SỐ TRONG FILE NÀY LÀ SỐ ĐÃ ĐO, KHÔNG ĐO LẠI** — nguồn ghi ngay cạnh từng
hằng số. Chỗ nào chưa đo thì để rỗng chứ **không bịa**: bịa một con số cạnh
tên giọng là người dùng sẽ tin mà chọn (đúng luật ``nhan_nha.nhan``).
"""
from __future__ import annotations

from app.core import nhan_nha

# ---------------------------------------------------------------------------
# NGUỒN GIỌNG — nhận theo TIỀN TỐ mã
# ---------------------------------------------------------------------------
# Mã edge-tts (`vi-VN-HoaiMyNeural`) không bao giờ chứa dấu hai chấm, nên mọi
# họ giọng khác đều mang tiền tố có `:` và không thể lẫn nhau. Quy ước này đã
# được ghi ở `giong_vbee.py` — giữ đúng, đừng đặt tiền tố mới không có `:`.
EDGE = "edge"
PIPER = "piper"
OMNIVOICE = "ov"
INDEXTTS = "ix"
VIENEU = "vieneu"
ELEVEN = "el"
VBEE = "vbee"
GEMINI = "gemini"

#: tiền tố -> tên nguồn. `vieneu:` là CHỖ CHỪA SẴN cho luồng đang thêm
#: `app/core/giong_vieneu.py` (VieNeu-TTS v3 Turbo, Apache 2.0). Chừa trước để
#: khi module đó vào thì giọng rơi ĐÚNG nhóm "Trên máy" ngay, không phải sửa
#: lại file này giữa lúc luồng khác đang giữ nó.
_TIEN_TO: tuple[tuple[str, str], ...] = (
    ("piper:", PIPER),
    ("ov:", OMNIVOICE),
    ("ix:", INDEXTTS),
    ("vieneu:", VIENEU),
    ("el:", ELEVEN),
    ("vbee:", VBEE),
    ("gemini:", GEMINI),
)

#: Tên nguồn hiện cho người đọc.
TEN_NGUON: dict[str, str] = {
    EDGE: "edge-tts",
    PIPER: "Piper",
    OMNIVOICE: "OmniVoice",
    INDEXTTS: "IndexTTS",
    VIENEU: "VieNeu",
    ELEVEN: "ElevenLabs",
    VBEE: "Vbee",
    GEMINI: "Gemini",
}

#: Nguồn nào KHÔNG tốn tiền/hạn mức. edge-tts miễn phí (rủi ro nằm ở điều
#: khoản dịch vụ Microsoft, đã khai `LICENSES.txt` mục 5 — đó là chuyện GIẤY
#: PHÉP, không phải chuyện tiền, nên không trộn vào cột này).
_MIEN_PHI: frozenset[str] = frozenset(
    {EDGE, PIPER, OMNIVOICE, INDEXTTS, VIENEU})

#: Nguồn -> cần tải bao nhiêu thì mới chạy được. **SỐ ĐO, không ước:**
#: Piper 212,4 MB (`piper_tts`, chạy thật `cai_piper()` vào hộp cát rỗng) ·
#: OmniVoice 6,1 GB (`giong_ngoai`, trọng số trong kho Hugging Face) ·
#: VieNeu 286 MB (`docs/GIONG_DOC_MIEN_PHI.md` bảng đối chiếu).
#: Nguồn không có trong bảng = chạy được ngay, không tải gì.
_CAN_TAI: dict[str, str] = {
    PIPER: "212 MB",
    OMNIVOICE: "6,1 GB",
    INDEXTTS: "bộ IndexTTS",
    VIENEU: "286 MB",
}

#: Nguồn -> RUNG mốc chữ (chữ hiện lệch tiếng bao nhiêu). **CHỈ điền nguồn đã
#: đo bằng CÙNG MỘT THƯỚC** (`silencedetect`, xem khối "GIÓNG HÀNG" của
#: CLAUDE.md và `docs/GIONG_NHAN_BAN.md` mục C5) — trộn hai thước vào một cột
#: là đúng cái bẫy `nhan_nha` đã dặn ("so CHÉO chỉ là tham khảo").
#:
#: ElevenLabs CỐ Ý ĐỂ RỖNG: nó có mốc THẬT (`/with-timestamps`) và đo ra ngang
#: edge-tts (1,03 lần), nhưng con số đó đo bằng thước KHÁC (Groq chép ngược)
#: nên **không đặt cạnh 15,7 ms được**. Cổng 67 đã chứng minh thước Groq phụ
#: thuộc giọng; điền bừa vào đây là dựng lại đúng cái sai đó.
_KHOP_MS: dict[str, str] = {
    EDGE: "15,7 ms",
    PIPER: "29,5 ms",
    OMNIVOICE: "90-119 ms",
    VIENEU: "14,6-15,4 ms",
    VBEE: "90-119 ms",
}


def nguon(vid: str) -> str:
    """Mã giọng này thuộc nguồn nào. Không nhận ra -> coi là edge-tts.

    Lùi về edge-tts chứ không ném: mã lạ (mẫu cũ, user gõ tay) vẫn phải xếp
    được vào một chỗ, mất một nhãn còn hơn combo trống một dòng.
    """
    s = str(vid or "")
    for tt, ng in _TIEN_TO:
        if s.startswith(tt):
            return ng
    return EDGE


def mien_phi(vid: str) -> bool:
    """Chọn giọng này có tốn tiền/hạn mức không."""
    return nguon(vid) in _MIEN_PHI


def can_tai(vid: str) -> str:
    """Phải tải bao nhiêu thì giọng này mới chạy được ("" = không cần)."""
    return _CAN_TAI.get(nguon(vid), "")


def tren_may(vid: str) -> bool:
    """Giọng chạy HẲN trên máy (không gọi mạng lúc đọc)."""
    return bool(can_tai(vid))


def khop_ms(vid: str) -> str:
    """Chữ chạy theo lời lệch bao nhiêu ("" = chưa đo bằng thước chung)."""
    return _KHOP_MS.get(nguon(vid), "")


def _bo_pitch(vid: str) -> str:
    """Bỏ hậu tố biến thể cao độ (`vi-VN-NamMinhNeural|-20Hz`).

    KHÔNG import `thay_giong` để dùng `tach_giong_pitch`: file đó kéo theo cả
    ffmpeg/Groq/Demucs, mà đây là hàm thuần dùng trong lúc dựng giao diện.
    Dấu phân cách `|` là quy ước đã chốt ở `thay_giong._SEP_PITCH`.
    """
    return str(vid or "").split("|", 1)[0]


def ma_ngon_ngu(vid: str) -> str:
    """Mã ngôn ngữ 2 chữ của giọng ("" = đa ngôn ngữ / không biết).

    Chỉ đọc được với giọng edge-tts (`vi-VN-...`). Giọng máy/giọng trả tiền có
    ngôn ngữ riêng của nó -> trả "" và được xếp theo NGUỒN, không theo tiếng.
    """
    v = _bo_pitch(vid)
    if nguon(v) != EDGE:
        return ""
    if da_ngu(v):
        return ""
    phan = v.split("-")
    return phan[0].lower() if len(phan) >= 3 else ""


def da_ngu(vid: str) -> bool:
    """Giọng đọc được MỌI thứ tiếng (edge-tts `*Multilingual*`)."""
    return "multilingual" in _bo_pitch(vid).lower()


def ten_goc(vid: str) -> str:
    """Tên người đọc rút từ mã: `en-US-AndrewMultilingualNeural` -> `Andrew`.

    Dùng để BẮT hai dòng cùng tên (Andrew/Brian/Ava/Emma) — chính cái anh Hùng
    nhìn thấy là "hiện hai lần". Mã không phải edge-tts thì trả "" (tên của
    chúng nằm trong nhãn do chính module nguồn dựng, không đoán lại).
    """
    v = _bo_pitch(vid)
    if nguon(v) != EDGE:
        return ""
    phan = v.split("-", 2)
    if len(phan) != 3:
        return ""
    ten = phan[2]
    for duoi in ("Neural", "Multilingual"):
        ten = ten.replace(duoi, "")
    return ten.strip()


# ---------------------------------------------------------------------------
# ĐUÔI DÒNG — tiền / phải tải gì
# ---------------------------------------------------------------------------
#: Đuôi gắn vào cuối nhãn, theo nguồn. Ngắn cố ý: combo lúc ĐÓNG chỉ rộng bằng
#: hộp, dòng dài quá là bị cắt đúng chỗ quan trọng.
_DUOI: dict[str, str] = {
    EDGE: "miễn phí",
    PIPER: "miễn phí, cần tải 212 MB",
    OMNIVOICE: "miễn phí, cần tải 6,1 GB",
    INDEXTTS: "miễn phí, cần tải bộ IndexTTS",
    VIENEU: "miễn phí, cần tải 286 MB",
    ELEVEN: "TỐN HẠN MỨC ElevenLabs",
    VBEE: "TỐN TIỀN theo ký tự",
    GEMINI: "TỐN HẠN MỨC Gemini",
}

#: Chữ để dò xem nhãn ĐÃ nói điều đó chưa (nhãn của `giong_ngoai`/`giong_vbee`
#: vốn đã dài và đã mang cảnh báo riêng). Nói hai lần một chuyện trên cùng một
#: dòng thì dòng dài gấp đôi mà không thêm thông tin nào.
_DO_TRUNG: dict[str, tuple[str, ...]] = {
    ELEVEN: ("tốn", "hạn mức", "trả tiền"),
    VBEE: ("tính tiền", "tốn", "cần key"),
    GEMINI: ("tốn", "hạn mức", "cần key"),
    PIPER: ("cần tải", "chưa tải"),
    OMNIVOICE: ("cần tải",),
    VIENEU: ("cần tải",),
    INDEXTTS: ("cần tải",),
}


def duoi_dong(vid: str, nhan: str = "") -> str:
    """Đuôi ' · miễn phí' / ' · TỐN TIỀN theo ký tự' ... cho một dòng combo.

    Trả chuỗi RỖNG khi nhãn đã tự nói điều đó rồi.
    """
    ng = nguon(vid)
    duoi = _DUOI.get(ng, "")
    if not duoi:
        return ""
    thap = str(nhan or "").lower()
    if any(t in thap for t in _DO_TRUNG.get(ng, ())):
        return ""
    return " · " + duoi


def ten_ro_rang(vid: str, nhan: str, trung_ten: bool) -> str:
    """Thêm chỗ KHÁC NHAU vào dòng khi hai giọng cùng tên người đọc.

    ``trung_ten`` = tên này có **cả bản đa ngôn ngữ lẫn bản thường** (Andrew ·
    Brian · Ava · Emma). Lúc đó nhãn phải tự phân biệt được **khi combo ĐANG
    ĐÓNG** — nhãn nhóm nằm ở trên, người dùng không nhìn thấy.

    Chữ dùng là "bản đa ngôn ngữ" / "bản tiếng Anh" chứ không phải "(đa ngữ)":
    "đa ngữ" là chữ của bản cũ và nó đã KHÔNG đủ để anh Hùng phân biệt.

    **ĐIỀU KIỆN PHẢI LÀ CẶP ĐA-NGỮ/THƯỜNG, KHÔNG PHẢI "TÊN LẶP LẠI"** — bản
    đầu chỉ đếm tên và dán "[bản tiếng Anh]" vào **Nam Minh**, vì biến thể cao
    độ ``vi-VN-NamMinhNeural|-20Hz`` cũng rút ra tên "NamMinh". Dán một chữ SAI
    cạnh tên giọng còn tệ hơn không dán gì.
    """
    if not trung_ten:
        return nhan
    ro = "bản đa ngôn ngữ" if da_ngu(vid) else "bản tiếng Anh"
    if ro in nhan:
        return nhan
    return f"{nhan} [{ro}]"


def la_bien_the(vid: str) -> bool:
    """Mã này là BIẾN THỂ CAO ĐỘ của một giọng khác (`...|-20Hz`)?

    Biến thể **không phải giọng mới** — cùng người đọc, chỉ khác cao độ, và
    số nhấn nhá trong bảng là số của giọng GỐC chứ chưa ai đo riêng từng mức.
    Vì vậy chúng không được lên nhóm "Khuyên dùng" (khuyên bằng một con số
    mượn của mã khác thì đúng bằng bịa), mà nằm trong nhóm ngôn ngữ của chính
    giọng gốc, nơi nhãn "Nam Minh - trầm" tự nói ra nó là gì.
    """
    return "|" in str(vid or "")


# ---------------------------------------------------------------------------
# NHÓM
# ---------------------------------------------------------------------------
N_KHUYEN = "khuyen"
N_DICH = "mp_dich"
N_DANGU = "mp_dangu"
N_MAY = "tren_may"
N_TIEN = "tra_tien"
N_KHAC = "mp_khac"

#: Thứ tự nhóm trong combo. "Tiếng khác" xuống ĐÁY: khi anh Hùng chọn Tiếng
#: Việt thì 47 giọng Anh là thứ anh ấy không cần, mà chúng đang chiếm chỗ ngay
#: đầu danh sách — đó đúng là câu "giọng Việt bị chôn".
THU_TU_NHOM: tuple[str, ...] = (
    N_KHUYEN, N_DICH, N_DANGU, N_MAY, N_TIEN, N_KHAC)

#: Nhãn nhóm. KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ra ô đen, bài học
#: v2.6.22). Nhãn nói THẲNG tiền và việc phải tải, vì đó là hai câu anh Hùng
#: hỏi đích danh.
_NHAN_NHOM: dict[str, str] = {
    N_KHUYEN: "KHUYÊN DÙNG cho {nn} - miễn phí, chạy được ngay",
    N_DICH: "MIỄN PHÍ (edge-tts) - giọng {nn}",
    N_DANGU: "MIỄN PHÍ (edge-tts) - đọc được MỌI thứ tiếng",
    N_MAY: "TRÊN MÁY - miễn phí nhưng phải tải model về trước",
    N_TIEN: "TRẢ TIỀN - tốn hạn mức hoặc tốn tiền",
    N_KHAC: "MIỄN PHÍ (edge-tts) - các tiếng khác",
}

#: Tên tiếng Việt của ngôn ngữ đích, để nhãn nhóm đọc được. Lấy đúng bộ mã
#: `thay_giong.NGON_NGU_DICH` đang dùng; mã lạ -> in nguyên mã (không bịa tên).
TEN_NN: dict[str, str] = {
    "vi": "Tiếng Việt", "en": "Tiếng Anh", "zh": "Tiếng Trung",
    "ja": "Tiếng Nhật", "ko": "Tiếng Hàn", "th": "Tiếng Thái",
    "id": "Tiếng Indonesia", "es": "Tiếng Tây Ban Nha",
    "pt": "Tiếng Bồ Đào Nha", "fr": "Tiếng Pháp", "de": "Tiếng Đức",
    "ru": "Tiếng Nga", "it": "Tiếng Ý", "ar": "Tiếng Ả Rập",
    "hi": "Tiếng Hindi",
}


def ten_ngon_ngu(nn: str) -> str:
    """`vi` / `vi-VN` -> `Tiếng Việt`. Mã lạ -> trả nguyên mã."""
    g = str(nn or "").split("-")[0].lower()
    return TEN_NN.get(g, g or "?")


def nhom_cua(vid: str, nn: str) -> str:
    """Giọng này thuộc nhóm nào (CHƯA xét "khuyên dùng").

    Tách riêng khỏi ``gom_nhom`` để cổng test chấm được từng mã một, không
    phải dựng cả danh sách rồi suy ngược.
    """
    ng = nguon(vid)
    if ng in (ELEVEN, VBEE, GEMINI):
        return N_TIEN
    if ng != EDGE:
        return N_MAY
    if da_ngu(vid):
        return N_DANGU
    goc = str(nn or "").split("-")[0].lower()
    return N_DICH if ma_ngon_ngu(vid) == goc else N_KHAC


#: Bao nhiêu giọng trong nhóm "Khuyên dùng". 5 là số đọc hết được bằng một
#: liếc mắt mà vẫn có chỗ cho cả nam lẫn nữ; nhiều hơn thì nó thành một danh
#: sách nữa để dò, tức lặp lại đúng bệnh đang chữa.
SO_KHUYEN = 5


def _dung_duoc_ngay(vid: str) -> bool:
    """Chọn phát là chạy được: miễn phí VÀ không phải tải gì."""
    return mien_phi(vid) and not can_tai(vid)


def chon_khuyen(ds: list[tuple[str, str]], nn: str,
                so: int = SO_KHUYEN) -> list[str]:
    """Mã của các giọng đưa lên nhóm "Khuyên dùng", tốt nhất trước.

    Ba điều kiện, theo thứ tự quan trọng:

    1. **ĐỌC ĐƯỢC tiếng đích** — đúng ngôn ngữ, hoặc đa ngôn ngữ.
    2. **CHỌN PHÁT LÀ CHẠY** — miễn phí và không phải tải gì. Khuyên một giọng
       phải tải 6,1 GB thì lời khuyên đó vô dụng ở lần bấm đầu tiên.
    3. **ĐÃ ĐO nhấn nhá** — chưa đo thì không lên nhóm này. Đây là chỗ nhóm
       "khuyên dùng" khác nhóm thường: nó là LỜI KHUYÊN, mà khuyên bằng cảm
       tính thì đúng bằng bảng `_HOT_VOICES` viết tay mà cổng 76 vừa bỏ.

    Không giọng nào đủ 3 điều -> trả rỗng. **Nhóm rỗng thì `gom_nhom` bỏ hẳn
    nhãn nhóm**, thà không khuyên còn hơn khuyên bừa.
    """
    goc = str(nn or "").split("-")[0].lower()
    ung: list[str] = []
    for _nhan, vid in ds:
        if not vid or la_bien_the(vid) or not _dung_duoc_ngay(vid):
            continue
        if nhan_nha.muc(_bo_pitch(vid)) is None:
            continue
        if ma_ngon_ngu(vid) == goc or da_ngu(vid):
            ung.append(vid)
    ung.sort(key=lambda v: nhan_nha.khoa_sap(_bo_pitch(v)))
    return ung[:max(0, int(so))]


def gom_nhom(ds: list[tuple[str, str]], nn: str = "en",
             ) -> list[tuple[str, str]]:
    """Xếp lại danh sách giọng thành các nhóm có tiêu đề.

    Vào: ``[(nhãn, mã)]`` đúng dạng ``giong_dung_duoc`` trả ra — dòng có mã
    RỖNG là nhãn nhóm CŨ và bị **vứt hết** (nhóm mới dựng lại từ đầu, giữ lại
    là hai hệ thống nhóm chồng nhau).

    Ra: cùng dạng ``[(nhãn, mã)]``, mã rỗng = nhãn nhóm (UI phải disable).

    **BA BẤT BIẾN, cổng test chấm đúng ba cái này:**

    * **không mất giọng**: tập mã ra == tập mã vào (bỏ mã rỗng);
    * **không trùng**: mỗi mã xuất hiện ĐÚNG một lần;
    * **trong mỗi nhóm, nhấn nhá cao đứng trên** (``nhan_nha.khoa_sap``),
      giọng chưa đo xuống cuối nhóm chứ không bị vứt.
    """
    # 1) bỏ nhãn nhóm cũ + bỏ mã trùng (giữ nhãn gặp ĐẦU TIÊN)
    da: set[str] = set()
    sach: list[tuple[str, str]] = []
    for nhan, vid in ds or []:
        v = str(vid or "")
        if not v or v in da:
            continue
        da.add(v)
        sach.append((str(nhan or v), v))

    # 2) tên nào có CẢ bản đa ngôn ngữ LẪN bản thường -> dòng phải tự phân
    #    biệt. Đếm theo mã GỐC (bỏ hậu tố cao độ): biến thể của cùng một giọng
    #    không phải hai giọng cùng tên.
    co_da: dict[str, bool] = {}
    co_thuong: dict[str, bool] = {}
    for _n, v in sach:
        t = ten_goc(v)
        if not t:
            continue
        if da_ngu(v):
            co_da[t] = True
        else:
            co_thuong[t] = True
    can_ro = {t for t in co_da if co_thuong.get(t)}

    # 3) chia nhóm. "Khuyên dùng" LẤY HẲN giọng khỏi nhóm gốc.
    khuyen = chon_khuyen(sach, nn)
    o_khuyen = set(khuyen)
    thung: dict[str, list[tuple[str, str]]] = {k: [] for k in THU_TU_NHOM}
    for nhan, vid in sach:
        k = N_KHUYEN if vid in o_khuyen else nhom_cua(vid, nn)
        thung[k].append((nhan, vid))

    # 4) sắp trong nhóm + dựng nhãn
    ra: list[tuple[str, str]] = []
    for k in THU_TU_NHOM:
        muc = thung[k]
        if not muc:
            continue                    # nhóm rỗng -> KHÔNG để nhãn trơ
        if k == N_KHUYEN:               # giữ đúng thứ tự `chon_khuyen`
            muc = sorted(muc, key=lambda it: khuyen.index(it[1]))
        else:
            muc = sorted(muc, key=lambda it: (
                nhan_nha.khoa_sap(_bo_pitch(it[1])), it[1]))
        ra.append((_NHAN_NHOM[k].format(nn=ten_ngon_ngu(nn)), ""))
        for nhan, vid in muc:
            n2 = ten_ro_rang(vid, nhan, ten_goc(vid) in can_ro)
            ra.append((n2 + duoi_dong(vid, n2), vid))
    return ra
