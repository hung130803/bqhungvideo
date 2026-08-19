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

from app.core import da_ngu as da_ngu_do
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
CHATTER = "chatter"

#: tiền tố -> tên nguồn.
#:
#: **`vn:` và `vnb:` LÀ CỦA VieNeu — ĐỌC TỪ `giong_vieneu.py`, KHÔNG ĐOÁN.**
#: Bản đầu của file này chừa sẵn `vieneu:` theo suy đoán; module thật vào
#: (`a95e0e6`) thì tiền tố hoá ra là `vn:` (giọng dựng sẵn) và `vnb:` (giọng
#: nhân bản từ mẫu). Đoán sai tiền tố thì `nguon()` trả về `edge` -> 20 giọng
#: VieNeu rơi vào nhóm "các tiếng khác", mất nhãn "cần tải", và **không một
#: dòng báo nào**. Thêm nguồn mới thì lấy hằng số từ chính module nguồn.
#:
#: **`cb:` LÀ CỦA CHATTERBOX — bài học đó lặp lại nguyên xi ở v2.38.0.**
#: `giong_chatter.py` viết xong 471 dòng, có sẵn hằng `TIEN_TO = "cb:"` và một
#: dòng ghi chú dặn đích danh *"luồng lắp giao diện phải thêm `("cb:", CHATTER)`
#: vào `giong_bang._TIEN_TO`"* — mà **không ai thêm**. Hậu quả đo được trước khi
#: vá: `nguon("cb:en|D:/mau.wav")` trả `edge` -> giọng nhân bản rơi vào nhóm
#: *"MIỄN PHÍ (edge-tts) - các tiếng khác"*, mất nhãn "cần tải 5,5 GB" và mất
#: cả cảnh báo "cần GPU". Đúng lỗi `ov:nu_am` và `vn:` đã sập hai lần.
_TIEN_TO: tuple[tuple[str, str], ...] = (
    ("piper:", PIPER),
    ("ov:", OMNIVOICE),
    ("ix:", INDEXTTS),
    ("vnb:", VIENEU),               # phải đứng TRƯỚC `vn:` — nó dài hơn
    ("vn:", VIENEU),
    ("el:", ELEVEN),
    ("vbee:", VBEE),
    ("gemini:", GEMINI),
    ("cb:", CHATTER),
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
    CHATTER: "Chatterbox",
}

#: Nguồn nào KHÔNG tốn tiền/hạn mức. edge-tts miễn phí (rủi ro nằm ở điều
#: khoản dịch vụ Microsoft, đã khai `LICENSES.txt` mục 5 — đó là chuyện GIẤY
#: PHÉP, không phải chuyện tiền, nên không trộn vào cột này).
#:
#: Chatterbox **MIỄN PHÍ THẬT**: giấy phép MIT cho CẢ mã LẪN trọng số, chạy
#: hẳn trên máy, không một lượt mạng nào. Đây là cột DUY NHẤT nó hơn edge-tts
#: (edge-tts miễn phí về tiền nhưng điều khoản dịch vụ Microsoft ghi thẳng
#: *"It shouldn't be used for commercial reasons"* — `LICENSES.txt` mục 5).
_MIEN_PHI: frozenset[str] = frozenset(
    {EDGE, PIPER, OMNIVOICE, INDEXTTS, VIENEU, CHATTER})

#: Nguồn -> cần tải bao nhiêu thì mới chạy được. **SỐ ĐO, không ước:**
#: Piper 212,4 MB (`piper_tts`, chạy thật `cai_piper()` vào hộp cát rỗng) ·
#: OmniVoice 6,1 GB (`giong_ngoai`, trọng số trong kho Hugging Face) ·
#: VieNeu 250 MB — lấy ĐÚNG con số trên nhãn nút `giong_vieneu.NHAN_TAI`,
#: không lấy 286 MB của `docs/GIONG_DOC_MIEN_PHI.md` (đó là cỡ trọng số,
#: không phải lượng tải thật). Nhãn phải KHỚP ĐƯỜNG SẼ ĐI — cổng 71 CA 4.
#: Nguồn không có trong bảng = chạy được ngay, không tải gì.
#: Chatterbox 5,5 GB — lấy ĐÚNG con số trên nhãn nút `giong_chatter.NHAN_TAI`
#: (torch CUDA ~2,5 GB + thư viện + trọng số ~3,0 GB), KHÔNG ước bừa. Nhãn phải
#: KHỚP ĐƯỜNG SẼ ĐI: ghi 155 MB rồi tải 2,5 GB là đúng lỗi cổng 71 CA 4.
_CAN_TAI: dict[str, str] = {
    PIPER: "212 MB",
    OMNIVOICE: "6,1 GB",
    INDEXTTS: "bộ IndexTTS",
    VIENEU: "250 MB",
    CHATTER: "5,5 GB",
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
#:
#: **Chatterbox CŨNG CỐ Ý ĐỂ RỖNG, cùng lý do — đừng ai "bổ sung cho đủ".**
#: Con số của nó là **76,2 ms** (`giong_chatter` docstring), đo bằng ĐÚNG thước
#: Groq chép ngược, và trong CÙNG lượt đo đó edge-tts ra **43,6 ms**. Cặp
#: 76,2/43,6 so được với nhau vì cùng thước; nhưng đặt 76,2 cạnh **15,7** (số
#: của `silencedetect`) là trộn hai thước — đúng cái bẫy mục này sinh ra để
#: chặn. Cặp số đó đi vào NHÃN (`giong_chatter.CANH_BAO_CL` ghi "76 ms so với
#: 44 ms của giọng thường"), nơi cả hai vế cùng một thước.
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


#: Nguồn dùng `|` cho việc KHÁC (không phải cao độ). Hiện chỉ Chatterbox:
#: `cb:<lang>|<đường dẫn mẫu>`. Cắt ở `|` cho mã của nó là **vứt mất đường dẫn
#: mẫu** — mà đường dẫn mẫu CHÍNH LÀ giọng; mất nó thì `tach_ma` trả rỗng và
#: giọng nhân bản của kênh A ra giọng edge-tts. Cùng lỗi này còn nằm ở
#: `thay_giong.tach_giong_pitch` (đã vá kèm).
_CO_ONG_RIENG: tuple[str, ...] = (CHATTER,)


def _bo_pitch(vid: str) -> str:
    """Bỏ hậu tố biến thể cao độ (`vi-VN-NamMinhNeural|-20Hz`).

    KHÔNG import `thay_giong` để dùng `tach_giong_pitch`: file đó kéo theo cả
    ffmpeg/Groq/Demucs, mà đây là hàm thuần dùng trong lúc dựng giao diện.
    Dấu phân cách `|` là quy ước đã chốt ở `thay_giong._SEP_PITCH`.

    **Mã của nguồn dùng `|` cho việc khác thì trả NGUYÊN VẸN** — xem
    `_CO_ONG_RIENG`.
    """
    s = str(vid or "")
    if nguon(s) in _CO_ONG_RIENG:
        return s
    return s.split("|", 1)[0]


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
#: **CON SỐ ĐÚNG MÀ ĐẶT CHỖ SAI THÌ NGƯỜI ĐỌC NHÂN LÊN — anh Hùng 19/08/2026:**
#: *"sao có cái giọng 1 giọng tận 250mb á tốn thế"*. Đuôi cũ ghi
#: `"miễn phí, cần tải 250 MB"` và nó lặp trên **TỪNG DÒNG**, đo được:
#:
#:   · `250 MB` trên **20 dòng** VieNeu   -> đọc thành 20 × 250 MB = **5 GB**
#:   · `6,1 GB` trên **5 dòng** OmniVoice -> đọc thành 5 × 6,1 GB = **30,5 GB**
#:   · `212 MB` trên **1 dòng** Piper     -> 1 dòng thì không có ảo giác nhân
#:
#: Sự thật: mỗi nguồn chỉ có **MỘT bộ DÙNG CHUNG** cho mọi giọng của nó, tải
#: một lần. Đuôi vì thế đổi `cần tải 250 MB` -> **`cần tải bộ 250 MB`**: chữ
#: "bộ" biến câu từ *mỗi dòng một lần tải* thành *một bộ đã xác định*, và nó
#: KHÔNG cần biết số dòng nên một chữ chữa được cả 5 nguồn.
#:
#: **VÌ SAO DÒNG KHÔNG MANG CẢ CÂU "dùng chung cho cả 20 giọng" — SỐ ĐO, KHÔNG
#: PHẢI TIẾT KIỆM CHỮ CHO ĐẸP:** cổng 79 có trần **132 ký tự** cho dòng VieNeu
#: (trần đó tồn tại để bắt "ai đó nhét bản ĐẦY ĐỦ 364-682 ký tự vào combo").
#: Đo thật độ dài dòng dài nhất (`Thanh Bình`) với từng cách viết:
#:
#:   `cần tải 250 MB`                -> 128  (bản cũ, ĐỌC THÀNH NHÂN LÊN)
#:   `cần tải bộ 250 MB`             -> **131  ĐANG DÙNG**
#:   `cần tải 1 bộ 250 MB`           -> 133  TRÀN
#:   `cần tải bộ chung 250 MB`       -> 137  TRÀN
#:   `cần tải bộ dùng chung 250 MB`  -> 142  TRÀN
#:
#: Nới trần 132 cho vừa câu dài là vừa đúng chỗ cổng 79 mất khả năng bắt lỗi nó
#: sinh ra để bắt — nên câu ĐẦY ĐỦ (kèm SỐ GIỌNG) đặt ở ba chỗ đọc MỘT LẦN,
#: không nhân lên được: tooltip (`ghi_chu_bo_chung`) · nút `giong_vieneu.
#: NHAN_TAI` · tiền tố `giong_vieneu.CHUA_TAI`.
#: **ĐỪNG ghi cứng "cả 20 giọng" vào đây** — thêm/bớt giọng là nhãn thành lời
#: khai sai mà không một cổng nào kêu.
_DUOI: dict[str, str] = {
    EDGE: "miễn phí",
    PIPER: "miễn phí, cần tải bộ 212 MB",
    OMNIVOICE: "miễn phí, cần tải bộ 6,1 GB",
    INDEXTTS: "miễn phí, cần tải bộ IndexTTS",
    VIENEU: "miễn phí, cần tải bộ 250 MB",
    ELEVEN: "TỐN HẠN MỨC ElevenLabs",
    VBEE: "TỐN TIỀN theo ký tự",
    GEMINI: "TỐN HẠN MỨC Gemini",
    # Ba cảnh báo trong một dòng ngắn, theo đúng thứ tự người dùng cần biết
    # TRƯỚC khi bấm: phải tải · phải có GPU · KHÔNG đọc được tiếng Việt. Phần
    # đầy đủ (mốc chữ 76 ms so 44 ms · đóng dấu chìm · đọc sai tiếng Trung
    # 28,8%) nằm ở `giong_chatter.nhan_giong`, dòng combo không chứa nổi.
    CHATTER: ("miễn phí (MIT), cần tải bộ 5,5 GB, cần GPU NVIDIA, "
              "KHÔNG có tiếng Việt"),
}


def ghi_chu_bo_chung(vid: str, so_giong: int = 0) -> str:
    """Câu nói RÕ *"một bộ, tải một lần"* — dành cho TOOLTIP, không cho dòng.

    Anh Hùng đọc 20 dòng cùng ghi *"cần tải 250 MB"* thành **20 × 250 MB =
    5 GB** rồi hỏi *"sao có cái giọng 1 giọng tận 250mb á tốn thế"*. Đuôi dòng
    (`_DUOI`) đã mang chữ "bộ dùng chung" để chặn phép nhân, nhưng nó cố ý
    KHÔNG mang con số giọng: dòng combo không còn chỗ, và số ghi cứng trong
    hằng số là thứ sẽ nói sai ngay lần thêm giọng kế tiếp.

    Chỗ nói con số là ĐÂY, vì tooltip đọc **từng dòng một** nên không dựng lại
    được ảo giác nhân. `so_giong` phải do NƠI GỌI ĐẾM TRÊN DANH SÁCH ĐANG BÀY
    (`thay_giong_dialog._dung_combo_giong`) — đếm ở đó thì thêm/bớt giọng là số
    tự đúng theo. `so_giong <= 1` -> KHÔNG nói số (một giọng thì "dùng chung"
    là câu vô nghĩa, và cũng chẳng có ảo giác nào để chữa).

    Trả "" cho nguồn không phải tải gì — gọi ở đâu cũng an toàn.
    """
    can = can_tai(vid)
    if not can:
        return ""
    ten = TEN_NGUON.get(nguon(vid), "bộ này")
    if int(so_giong or 0) > 1:
        return (f"TẢI MỘT LẦN: bộ {ten} {can} dùng chung cho CẢ "
                f"{int(so_giong)} giọng {ten} — KHÔNG phải "
                f"{int(so_giong)} × {can}.")
    return f"TẢI MỘT LẦN: bộ {ten} {can}."

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
    # `giong_chatter.nhan_giong` đã mang đủ ba cảnh báo -> dán thêm là dòng
    # dài gấp đôi mà không thêm một thông tin nào.
    # **CHỮ PHẢI VIẾT THƯỜNG**: `duoi_dong` so với `nhan.lower()`, nên để
    # "GPU"/"MIT" ở đây là chuỗi KHÔNG BAO GIỜ khớp -> dán thừa mà cổng nào
    # chỉ hỏi "có đuôi không" vẫn xanh (đã sập ngay lượt thử đầu).
    CHATTER: ("cần tải", "gpu", "mit"),
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


#: Chữ đánh dấu dòng LỐI TẮT ở nhóm "Khuyên dùng" — xem `gom_nhom(loi_tat=)`.
#: Đặt ở CUỐI dòng và nói thẳng "cùng giọng", vì cái anh Hùng kêu ở v2.37.0
#: không phải "có hai dòng" mà là "hai dòng mà không biết nó là một".
DAU_LOI_TAT = " [lối tắt — cùng giọng ở nhóm dưới]"


def duoi_nhan_nha(vid: str, nhan: str = "") -> str:
    """Đuôi ' - nhấn nhá 4,0 rất truyền cảm' cho một dòng combo.

    Trả RỖNG khi giọng CHƯA ĐO (``nhan_nha.nhan`` đã lo: cấm bịa số cạnh tên
    giọng) **hoặc khi nhãn đã tự mang số rồi** — `giong_vieneu.nhan_giong` và
    `dubbing.list_recap_voices` nhóm "ĐỀ XUẤT" đều tự gọi `nhan_nha.nhan()`,
    dán thêm lần nữa là dòng ra *"... nhấn nhá 4,0 ... nhấn nhá 4,0 ..."*.
    Cùng khuôn chống-nói-hai-lần của `duoi_dong`/`_DO_TRUNG`.
    """
    if "nhấn nhá" in str(nhan or "").lower():
        return ""
    return nhan_nha.nhan(vid)


def duoi_da_ngu(vid: str, nhan: str = "") -> str:
    """Đuôi ' - đọc được Việt·Anh·Hàn·Nhật·Trung (đã đo)' cho một dòng combo.

    **ĐÂY LÀ CHỖ THAY "NHÃN CỦA MICROSOFT" BẰNG "SỐ ĐO".** ``da_ngu()`` phía
    trên chỉ hỏi *"tên giọng có chữ Multilingual không"* — nó vẫn dùng để GOM
    NHÓM (nhóm là chuyện BÀY, xếp sai thì chỉ khó tìm) nhưng **không được dùng
    làm LỜI HỨA với người dùng** (hứa sai thì 300 video ra tiếng vô nghĩa mà
    không một dòng báo). Lời hứa lấy từ ``app/core/da_ngu.py`` = bảng ĐO ĐƯỢC:
    103 arm, hai thước phải đồng ý, ngưỡng suy từ TRẦN/SÀN cùng lượt.

    Trả RỖNG khi nhãn đã tự nói điều đó rồi — cùng khuôn chống-nói-hai-lần
    của ``duoi_dong``/``duoi_nhan_nha``. Phải có: ``giong_vieneu.nhan_giong``
    và ``giong_ngoai`` tự ghi "4 thứ tiếng" / "TIẾNG ANH" vào nhãn của chúng.
    """
    # **DANH SÁCH NÀY PHẢI HẸP.** Bản đầu để cả chuỗi ``"tiếng anh"`` và nó
    # khớp trúng ``[bản tiếng Anh]`` do `ten_ro_rang` vừa dán vào — mà chuỗi
    # đó nói về *BẢN NÀO của Andrew*, không nói gì về *đọc được tiếng gì*.
    # Hậu quả: đúng giọng ĐÃ ĐO (`en-US-AndrewNeural`, đo ra trượt cả 4 tiếng
    # ngoài) lại là giọng DUY NHẤT mất nhãn ngôn ngữ. Dấu của `giong_vieneu`
    # là `" - TIẾNG ANH"` nên phải so kèm dấu gạch, đừng so chuỗi trần.
    thap = str(nhan or "").lower()
    if any(t in thap for t in ("đọc được", "chỉ đọc tiếng", "chưa đo đọc",
                              "thứ tiếng", " - tiếng anh")):
        return ""
    return da_ngu_do.nhan_gon(vid)


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
    thap = str(nhan or "").lower()
    if da_ngu(vid):
        # nhãn nhóm ĐỀ XUẤT đã ghi sẵn "(đa ngôn ngữ)", nhãn thường ghi
        # "(Nam, đa ngữ)" -> nói lần nữa là dòng dài thêm mà không rõ thêm.
        if "đa ngôn ngữ" in thap or "đa ngữ" in thap:
            return nhan
        return f"{nhan} [bản đa ngôn ngữ]"
    if "tiếng anh" in thap:
        return nhan
    return f"{nhan} [bản tiếng Anh]"


def la_bien_the(vid: str) -> bool:
    """Mã này là BIẾN THỂ CAO ĐỘ của một giọng khác (`...|-20Hz`)?

    Biến thể **không phải giọng mới** — cùng người đọc, chỉ khác cao độ, và
    số nhấn nhá trong bảng là số của giọng GỐC chứ chưa ai đo riêng từng mức.
    Vì vậy chúng không được lên nhóm "Khuyên dùng" (khuyên bằng một con số
    mượn của mã khác thì đúng bằng bịa), mà nằm trong nhóm ngôn ngữ của chính
    giọng gốc, nơi nhãn "Nam Minh - trầm" tự nói ra nó là gì.

    **`cb:en|D:/mau.wav` KHÔNG phải biến thể cao độ** dù có dấu `|` — xem
    `_CO_ONG_RIENG`. Trả True cho nó là loại giọng nhân bản khỏi mọi phép lọc
    đi theo hàm này, mà lý do loại lại là một chuyện không có thật.
    """
    s = str(vid or "")
    if nguon(s) in _CO_ONG_RIENG:
        return False
    return "|" in s


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
    # "MỌI thứ tiếng" là LỜI CỦA MICROSOFT, và app từng in nguyên nó ra.
    # Đo 19/08/2026 (`_do_5_tieng.py`): **10/12** giọng nhóm này đọc được cả 5
    # tiếng Việt/Anh/Hàn/Nhật/Trung, nhưng `en-US-AndrewMultilingual` **trượt
    # tiếng HÀN** (đọc rời sai 75%, trần 0%) và 2 ô tiếng Việt chưa kết luận
    # được. Mà 5 tiếng cũng chỉ là 5 trong **75** thứ tiếng của edge-tts.
    # Nên nhãn nhóm nói ĐÚNG PHẠM VI ĐÃ ĐO và trỏ người đọc xuống ĐUÔI DÒNG
    # (`duoi_da_ngu`) — chỗ ghi từng tiếng cho từng giọng.
    N_DANGU: "MIỄN PHÍ (edge-tts) - ĐA NGÔN NGỮ (đã đo 5 tiếng, xem cuối dòng)",
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

    **BẤT BIẾN: CHỈ giọng edge-tts mới vào được nhóm NGÔN NGỮ ĐÍCH** (nhánh
    ``ng != EDGE`` chặn trước). Nhờ đó giọng Chatterbox **không bao giờ** hiện
    ở nhóm "giọng Tiếng Việt" — mà nó đọc tiếng Việt ra **chuỗi vô nghĩa và
    KHÔNG ném lỗi** (đo thật: *"Một cơn bão chưa từng có"* -> *"Mokonbel,
    Chutanko..."*, mã thoát 0). Xếp nó vào nhóm tiếng Việt là mời người dùng
    hỏng 300 video mà không một dòng báo. Cổng 82 CA 2 chấm đúng mệnh đề này.
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

    **GIỌNG ĐÚNG TIẾNG ĐÍCH LUÔN ĐỨNG TRÊN GIỌNG ĐA NGÔN NGỮ — và đây KHÔNG
    phải sở thích, nó là điều kiện để con số nhấn nhá còn có nghĩa.**
    ``nhan_nha`` đo mỗi giọng trên **4 câu ĐÚNG TIẾNG CỦA NÓ** và dặn thẳng ở
    đầu bảng: *"so trong CÙNG một tiếng thì chắc; so CHÉO tiếng chỉ là tham
    khảo"*. Xếp một hàng chung thì ``en-AU-WilliamMultilingual`` **4,73** (đo
    trên câu tiếng Anh) đứng trên ``vi-VN-NamMinh`` **4,04** (đo trên câu
    tiếng Việt) — bản đầu của hàm này ĐÃ làm đúng như vậy, tức là đem khuyên
    anh Hùng một giọng đọc tiếng Việt giọng Tây bằng một phép so sai luật.
    Nay chia **hai rổ**: đúng tiếng trước, đa ngôn ngữ sau; **trong mỗi rổ**
    mới xếp theo số đo, vì lúc đó mọi giọng cùng một bộ câu.
    """
    goc = str(nn or "").split("-")[0].lower()
    ung: list[str] = []
    # **PHẢI TỰ BỎ MÃ TRÙNG — lỗi thật, cổng 79 CA 8 bắt được 19/08/2026.**
    # Danh sách vào của app CÓ SẴN 20 dòng trùng mã (nhóm "ĐỀ XUẤT" của
    # `list_recap_voices` liệt kê lại giọng đã có ở nhóm ngôn ngữ). Không lọc
    # thì `ung` ra `[NamMinh, NamMinh, HoaiMy, HoaiMy, William]` -> nhóm
    # "Khuyên dùng" **hiện Nam Minh HAI LẦN** và mất 2 suất khuyên. Đó đúng
    # bằng cái anh Hùng kêu ("Andrew hiện hai lần"), chỉ đổi chỗ.
    # `gom_nhom` vô tình che được vì nó dedupe TRƯỚC khi gọi — nhưng hàm này
    # là hàm CÔNG KHAI, gọi thẳng từ ngoài (cổng 79 CA 5 làm đúng thế) thì
    # bệnh lộ ra. Chốt phải nằm TRONG hàm, đừng nhờ nơi gọi.
    da: set[str] = set()
    for _nhan, vid in ds:
        if not vid or vid in da or la_bien_the(vid):
            continue
        if not _dung_duoc_ngay(vid):
            da.add(vid)
            continue
        if nhan_nha.muc(_bo_pitch(vid)) is None:
            da.add(vid)
            continue
        if ma_ngon_ngu(vid) == goc or da_ngu(vid):
            da.add(vid)
            ung.append(vid)
    ung.sort(key=lambda v: (1 if da_ngu(v) else 0,
                            nhan_nha.khoa_sap(_bo_pitch(v))))
    return ung[:max(0, int(so))]


def gom_nhom(ds: list[tuple[str, str]], nn: str = "en",
             loi_tat: bool = False) -> list[tuple[str, str]]:
    """Xếp lại danh sách giọng thành các nhóm có tiêu đề.

    Vào: ``[(nhãn, mã)]`` đúng dạng ``giong_dung_duoc`` trả ra — dòng có mã
    RỖNG là nhãn nhóm CŨ và bị **vứt hết** (nhóm mới dựng lại từ đầu, giữ lại
    là hai hệ thống nhóm chồng nhau).

    Ra: cùng dạng ``[(nhãn, mã)]``, mã rỗng = nhãn nhóm (UI phải disable).

    **BẤT BIẾN, cổng 79 chấm:**

    * **không mất giọng**: tập mã ra == tập mã vào (bỏ mã rỗng) — đúng ở CẢ
      HAI chế độ, đây là mệnh đề không bao giờ được nhân nhượng;
    * **trong mỗi nhóm, nhấn nhá cao đứng trên** (``nhan_nha.khoa_sap``),
      giọng chưa đo xuống cuối nhóm chứ không bị vứt;
    * ``loi_tat=False`` (mặc định): **mỗi mã xuất hiện ĐÚNG một lần**, nhóm
      "Khuyên dùng" LẤY HẲN giọng ra khỏi nhóm gốc.

    ═══ ``loi_tat=True`` — LUẬT ANH HÙNG CHỐT 19/08/2026, ĐÈ LÊN BẢN ĐẦU ═══
    Nguyên văn: *"nhiều bên sẽ có nhiều giọng giống nhau nhưng kệ nó cứ thêm
    vào trùng lặp hay sao cũng được cho tôi, tại chỗ free chỗ mất tiền ấy, cứ
    thêm"*. Với nhóm "Khuyên dùng" thì nghĩa là: **giữ nó như một LỐI TẮT**,
    tức giọng nằm CẢ ở đầu danh sách LẪN trong nhóm gốc của nó.

    Đây KHÔNG mâu thuẫn với cái anh Hùng kêu ở v2.37.0 (*"Andrew hiện hai
    lần"*), và chỗ khác nhau là chỗ đáng giá nhất của mục này: **hồi đó hai
    dòng giống hệt nhau nên không đọc ra được đó là MỘT giọng hay HAI giọng
    khác nhau** — mà ngay cạnh nó lại có một ca HAI GIỌNG THẬT cùng tên
    (`AndrewNeural` 4,49 vs `AndrewMultilingualNeural` 3,79). Nay dòng lối tắt
    mang ``DAU_LOI_TAT`` nói thẳng *"cùng giọng ở nhóm dưới"*, nên hai loại
    trùng đó không thể lẫn vào nhau nữa.

    **Vì sao vẫn để mặc định ``False``:** bất biến "mỗi mã đúng một lần" là
    thứ chống được lỗi trùng THẬT (một mã lọt vào hai nhóm do chia nhóm sai).
    Bỏ hẳn nó đi thì không còn ai canh chuyện đó. Nên nó vẫn được chấm ở chế
    độ mặc định, còn chế độ lối tắt có bất biến RIÊNG, chặt hơn: mã lặp thì
    phải lặp ĐÚNG HAI LẦN, đúng một lần ở "Khuyên dùng" và một lần ở nhóm
    gốc, và dòng ở "Khuyên dùng" phải mang dấu lối tắt.
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

    # 3) chia nhóm. `loi_tat=False` -> "Khuyên dùng" LẤY HẲN giọng khỏi nhóm
    #    gốc; `loi_tat=True` -> CHÉP THÊM một dòng, giọng vẫn còn ở nhóm gốc.
    khuyen = chon_khuyen(sach, nn)
    o_khuyen = set(khuyen)
    thung: dict[str, list[tuple[str, str]]] = {k: [] for k in THU_TU_NHOM}
    for nhan, vid in sach:
        if vid in o_khuyen:
            thung[N_KHUYEN].append((nhan, vid))
            if not loi_tat:
                continue                # LẤY HẲN -> không vào nhóm gốc nữa
        thung[nhom_cua(vid, nn)].append((nhan, vid))

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
            # SỐ NHẤN NHÁ nằm TRONG dòng, không phải việc của UI: cổng 79 chấm
            # được nội dung dòng, mà combo lúc ĐÓNG cũng chỉ hiện một dòng.
            n2 += duoi_nhan_nha(vid, n2)
            # ĐỌC ĐƯỢC TIẾNG GÌ đứng TRƯỚC phần tiền: "chọn nó có ra tiếng
            # đúng không" là câu hỏi phải trả lời trước "nó tốn bao nhiêu".
            n2 += duoi_da_ngu(vid, n2)
            n2 += duoi_dong(vid, n2)
            if loi_tat and k == N_KHUYEN:
                n2 += DAU_LOI_TAT
            ra.append((n2, vid))
    return ra
