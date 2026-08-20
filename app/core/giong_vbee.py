# -*- coding: utf-8 -*-
"""GIỌNG VBEE AIVOICE — API CHÍNH HÃNG, CẦN KEY. LỰA CHỌN THÊM, KHÔNG THAY THẾ.

═══════════════════════════════════════════════════════════════════════════
CÂU QUAN TRỌNG NHẤT: **VBEE KHÔNG TRẢ MỐC TỪNG CHỮ**
═══════════════════════════════════════════════════════════════════════════
Đã đọc TOÀN BỘ tài liệu API chính thức (`api-docs.vbee.vn`, bản `llms-full.txt`
+ từng trang `realtime-api` · `batch-api` · `callback-api` · `get-request` ·
`get-list-voices`) ngày 18/08/2026. **KHÔNG có một trường nào** mang mốc thời
gian: không `timestamps`, không `alignment`, không `marks`, không `word`,
không `subtitle`/`srt`.

Đây là toàn bộ những gì API trả về, chép nguyên văn:

  · sync  -> **luồng nhị phân MP3/WAV/PCM**, hết. Không JSON, không mốc.
  · async -> `{"requestId": "...", "status": "PROCESSING"}`
  · poll  -> `{"status": "COMPLETED|PROCESSING|FAILED", "audioLink": "..."}`
  · callback -> `{app_id, request_id, characters, voice_code, audio_type,
                  speed_rate, sample_rate, bitrate, created_at, status,
                  audio_link}`

Trường gần nhất với "mốc" là `characters` — **SỐ LƯỢNG ký tự để tính tiền**,
không phải vị trí thời gian của ký tự. Đừng ai đọc nhầm rồi đi viết bộ parse.

**HỆ QUẢ BẮT BUỘC: mốc phải lấy bằng GIÓNG HÀNG CƯỠNG BỨC**
(`app/core/giong_hang.py`, đã có sẵn, phủ **98,6%**). Đây là đường TỐT NHẤT
còn lại và nó đã được đo:

  | đường lấy mốc            | PHỦ       | RUNG mốc chữ đầu |
  |--------------------------|-----------|------------------|
  | edge-tts `WordBoundary`  | 99,4-100% | **15,7 ms**      |
  | **gióng hàng cưỡng bức** | **98,6%** | **90-119 ms**    |
  | Groq chép ngược          | 38-99%    | 250-712 ms       |

Tức **Vbee tụt một bậc so với edge-tts ở khoản chữ bám lời** — không phải vì
giọng dở mà vì API không trả mốc. Nhãn hộp chọn giọng PHẢI nói ra điều này
(`CANH_BAO_MOC`), đúng tiền lệ Piper (cổng 64) và OmniVoice (cổng 72): anh
Hùng chạy 200-300 kênh, chọn nhầm một lần là hàng trăm video.

Máy CHƯA tải bộ gióng hàng -> `doc_loat` trả mốc RỖNG. Không tự bịa mốc, không
nội suy: **mốc gán nhầm chữ tệ hơn hẳn không có mốc** (bài học
`piper_tts._lay_moc`).

═══════════════════════════════════════════════════════════════════════════
KHÔNG CÓ TIẾN TRÌNH RIÊNG — CỐ Ý, ĐỪNG CHÉP KHUÔN OmniVoice
═══════════════════════════════════════════════════════════════════════════
`giong_ngoai.py` phải chạy tiến trình con vì `import torch` SAU khi Qt nạp là
`OSError [WinError 1114]` (cổng 55). File này **chỉ gọi HTTP** — không torch,
không transformers, không model trên máy. Đẻ thêm tiến trình ở đây là thêm chỗ
hỏng mà không mua được gì.

(Riêng bước GIÓNG HÀNG có nạp torch, nhưng `giong_hang.giong_hang_loat` đã tự
chạy tiến trình riêng của nó — file này không import torch một dòng nào.)

═══════════════════════════════════════════════════════════════════════════
GIẤY PHÉP / ĐIỀU KHOẢN — ĐÂY LÀ ĐƯỜNG MUA CHÍNH HÃNG
═══════════════════════════════════════════════════════════════════════════
Ba giọng anh Hùng muốn là hàng Vbee **BÁN**. Đường duy nhất được phép đi là
API có key hợp lệ. **ĐÃ TỪ CHỐI và KHÔNG BAO GIỜ nối vào đây:** mọi model
"giọng Vbee" tải rời trên HuggingFace, Kokoro-Vietnamese (giấu nguồn dữ liệu),
mọi cửa hậu trang demo, mọi key lậu.

**RÚT LẠI MỘT KHẲNG ĐỊNH (20/08/2026) — ĐỌC TRƯỚC KHI DỰNG LẠI NÓ.** Dòng trên
trước đây ghi model *"Ngọc Huyền"* trên HuggingFace *"tác giả TỰ KHAI huấn luyện
từ giọng Vbee rồi tự dán cc-by-nc"*. Anh Hùng hỏi thẳng **"model nào khai linh
tinh"** và **tôi không đưa ra được**: không tên repo, không URL, không một câu
nguyên văn nào của model card. Quét lại chính file này thì lời khai đó **chỉ là
văn xuôi ở đây**, và file **không có danh sách chặn nào** (`_NGO_NGUON` /
blacklist đều không tồn tại) — tức tài liệu còn mô tả một chốt chặn *không có
trong mã*.

Trạng thái đúng: **KHÔNG tích hợp model tải-rời nào cho Vbee** — đó là một
**QUYẾT ĐỊNH** (đi API chính hãng, không dùng trọng số nguồn không rõ), KHÔNG
phải một phát hiện về tác giả một model cụ thể. Muốn nói lại chuyện "ai tự khai
gì" thì phải kèm **tên repo + URL + nguyên văn model card**, đúng tiêu chuẩn
file này áp cho `vivos` và `25hours_single` ở `piper_tts`.

Ghi thẳng vì đây là lỗi của tôi chứ không của mã: tôi bắt mọi lượt kiểm phải
trích nguyên văn giấy phép, rồi lại dùng một lời khai không giữ được bằng chứng
để từ chối anh Hùng nhiều lượt.

**GÓI MIỄN PHÍ — CHƯA XÁC NHẬN ĐƯỢC LÀ CÓ CHO KIẾM TIỀN HAY KHÔNG.** FAQ của
Vbee chỉ nói chung *"Khách hàng hoàn toàn có thể sử dụng các file âm thanh sau
khi chuyển đổi để ứng dụng vào các lĩnh vực, công việc khác nhau (sản xuất
sách nói, báo nói, sản xuất clip up lên các trang mạng xã hội như Facebook,
Youtube...)"* nhưng **KHÔNG tách bạch gói free với gói trả phí**, và không có
một câu nào nói riêng về gói free. Vbee cũng ghi *"Vbee sẽ không chịu trách
nhiệm về vấn đề bản quyền"*.
-> Nhãn phải ghi ĐÚNG mức chắc chắn đó: **"chưa xác nhận"**, không được ghi
"được phép" cũng không được ghi "bị cấm". Đúng cách đã làm với ElevenLabs
(§1(c) cấm gói free dùng thương mại — chỗ đó có văn bản rõ nên ghi rõ).
Anh Hùng muốn chắc thì hỏi thẳng contact@vbee.ai TRƯỚC khi chạy sản xuất.

═══════════════════════════════════════════════════════════════════════════
KHÔNG ĐỌC ĐƯỢC SỐ DƯ — CHỖ HỔNG THẬT, GHI THẲNG
═══════════════════════════════════════════════════════════════════════════
Tài liệu API **KHÔNG có endpoint nào trả số điểm còn lại** (chỉ có tts · stt ·
voices · legacy). Khác hẳn ElevenLabs (`GET /v1/user/subscription` -> đếm được
ký tự còn lại trước khi chạy, `dubbing.eleven_quota`).

Hệ quả PHẢI chấp nhận, đừng hứa hão:
  · `uoc_ky_tu()` ước được SẼ TIÊU bao nhiêu (ước THỪA, không ước hụt).
  · **KHÔNG biết trước còn bao nhiêu** -> không thể chặn "hết điểm giữa mẻ"
    bằng cách đếm trước như ElevenLabs.
  · Hết điểm chỉ lộ ra bằng LỖI `TTS_SPEND_CREDITS_FAILED` -> lúc đó
    `doc_loat` trả toàn `False` (cả video một giọng edge-tts, KHÔNG lẫn hai
    giọng) và ghi tên video vào `logs/giong_vbee_<ngày>.log` + sổ
    `_da_lui()` để nơi gọi báo ĐÍCH DANH video nào bị lùi.

═══════════════════════════════════════════════════════════════════════════
GIÁ (đọc 18/08/2026) — SỐ NÀO LÀ SỐ ĐO, SỐ NÀO LÀ SUY RA
═══════════════════════════════════════════════════════════════════════════
  · `credit_factor` = **1 điểm / 1 ký tự** cho mọi giọng HN trong danh sách
    (đọc thẳng từ `get-list-voices`) -> **1 ký tự = 1 điểm**.
  · Gói tháng có 4 bậc (Tiêu chuẩn · Đặc biệt · VIP · VIP+). **Bậc "Đặc biệt"
    799.000 đ/tháng** (9.590.000 đ/năm) — con số này lấy từ trang bán hàng,
    CHƯA đối chiếu được số điểm kèm theo vì bảng giá của Vbee nằm trong ẢNH.
  · **BẪY PHẢI BIẾT:** gói Tiêu chuẩn/Đặc biệt/VIP chỉ cho dùng **MỘT NỬA**
    số điểm qua API; chỉ **VIP+** mới được dùng trọn gói cho API. App này gọi
    API nên phần dùng được chỉ bằng nửa con số quảng cáo, trừ khi mua VIP+.
  · Gói free: FAQ ghi **3.000 ký tự/lượt chuyển đổi**. Phần "~3.000 điểm/ngày
    qua nhiệm vụ" là chính sách khuyến mãi, **không nằm trong tài liệu API**
    nên file này KHÔNG dựa vào nó để tính gì.

═══════════════════════════════════════════════════════════════════════════
BA GIỌNG ANH HÙNG NÊU — ĐƯỢC 2, THIẾU 1
═══════════════════════════════════════════════════════════════════════════
  · **HN - Ngọc Huyền** -> `hn_female_ngochuyen_full_48k-fhg`  (CÓ, và là
    giọng HN DUY NHẤT tài liệu ghi rõ chạy được ở chế độ `sync`)
  · **HN - Anh Khôi**   -> `hn_male_phuthang_news65dt_44k-fhg` (bản tin) và
    `hn_male_phuthang_stor80dt_48k-fhg` (kể chuyện). CÓ.
  · **HN - Minh Quân**  -> **KHÔNG CÓ trong danh sách giọng của tài liệu API.**
    Không bịa mã. `tai_danh_sach_giong()` hỏi thẳng API lúc chạy, nên nếu Vbee
    đã thêm giọng đó cho tài khoản của anh Hùng thì nó TỰ hiện ra; còn không
    thì combo không có, và nhãn nói thẳng là chưa thấy.

═══════════════════════════════════════════════════════════════════════════
CHƯA LÀM / CHƯA KIỂM ĐƯỢC — VÌ CHƯA CÓ KEY. ĐỌC KỸ, ĐỪNG TƯỞNG ĐÃ CHẠY THẬT
═══════════════════════════════════════════════════════════════════════════
Toàn bộ file này viết theo TÀI LIỆU, **chưa gọi API thật một lần nào** (anh
Hùng chưa mua key). Những chỗ chỉ có tài liệu chống lưng, chưa có số đo:
  · đường `async` + poll: tài liệu ghi `webhookUrl` là **BẮT BUỘC** cho chế độ
    async, nhưng lại có sẵn `GET /v1/tts/requests/{id}` để hỏi trạng thái.
    App trên máy để bàn KHÔNG có URL công khai để nhận webhook, nên ở đây thử
    async KHÔNG kèm `webhookUrl` rồi poll. **Nếu Vbee từ chối** (400 kêu thiếu
    `webhookUrl`) thì `_bao_thieu_webhook()` ghi log rõ và cả loạt lùi edge-tts
    — KHÔNG treo, KHÔNG nổ. Có key rồi phải đo lại chỗ này ĐẦU TIÊN.
  · `speed` gốc của Vbee (0,25-1,9) dùng THAY cho `atempo`: theo đúng kết luận
    đã đo của edge-tts (`rate` của chính máy đọc thì méo = 0 theo cấu tạo, còn
    `atempo` là cắt-dán WSOLA, đo được 5,357 dB méo phổ ở 1,20). **Nhưng chưa
    đo trên Vbee** — nói cơ chế, không bịa số.
  · Giọng nào chạy được ở chế độ `sync`: tài liệu chỉ liệt kê 5 giọng và trong
    đó chỉ Ngọc Huyền là giọng HN. Vì vậy Anh Khôi mặc định đi đường async.
    `_SYNC_DUOC` là chỗ sửa khi đo được thật.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Callable, Optional

_NO_WIN = 0x08000000 if os.name == "nt" else 0

# ---------------------------------------------------------------------------
# Nhận dạng giọng
# ---------------------------------------------------------------------------
#: Tiền tố mã giọng. Mã edge-tts không bao giờ chứa dấu hai chấm nên các họ
#: giọng (`piper:` · `el:` · `gemini:` · `ov:` · `ix:` · `vbee:`) không lẫn.
TIEN_TO_VBEE = "vbee:"

#: Điểm cuối. `api.vbee.vn` là bản đang dùng; `vbee.vn/api/v1/tts` là bản
#: LEGACY, để nguyên đây làm ghi chú chứ KHÔNG gọi (tài liệu tự đánh dấu cũ).
API_TTS = "https://api.vbee.vn/v1/tts"
API_REQ = "https://api.vbee.vn/v1/tts/requests/"
API_VOICES = "https://vbee.vn/api/public/v1/voices"

#: Trần ký tự của từng chế độ — LẤY TỪ TÀI LIỆU, đừng đoán.
TRAN_SYNC = 300
TRAN_ASYNC = 100_000

#: 1 ký tự = 1 điểm (`credit_factor` = 1 cho mọi giọng HN đã liệt kê).
DIEM_MOI_KY_TU = 1.0

#: Giọng tài liệu ghi rõ chạy được ở chế độ `sync` (trả thẳng nhị phân, 1 lượt
#: gọi, không phải poll). Giọng NGOÀI danh sách này đi đường async cho chắc —
#: đoán bừa rồi ăn 400 giữa mẻ 300 kênh thì đắt hơn nhiều so với chậm vài giây.
_SYNC_DUOC = frozenset({"hn_female_ngochuyen_full_48k-fhg"})

#: Kho giọng CHỐT CỨNG — chỉ những mã đọc được ĐÍCH DANH trong tài liệu API.
#: (mã app, voiceCode của Vbee, nhãn tiếng Việt)
#: **KHÔNG bịa mã cho "Minh Quân"** — xem khối đầu file.
GIONG_VBEE: tuple[tuple[str, str, str], ...] = (
    ("vbee:ngochuyen", "hn_female_ngochuyen_full_48k-fhg",
     "HN - Ngọc Huyền (nữ)"),
    ("vbee:anhkhoi_tin", "hn_male_phuthang_news65dt_44k-fhg",
     "HN - Anh Khôi (nam, giọng bản tin)"),
    ("vbee:anhkhoi_ke", "hn_male_phuthang_stor80dt_48k-fhg",
     "HN - Anh Khôi (nam, giọng kể chuyện)"),
)

#: Giọng anh Hùng nêu mà tài liệu KHÔNG có. Giữ tên ở đây để `nhan_giong` và
#: nhãn hộp chọn nói được "chưa thấy giọng này", thay vì im lặng thiếu.
GIONG_CHUA_THAY: tuple[str, ...] = ("HN - Minh Quân",)

_BANG_MA = {ma: vc for ma, vc, _ in GIONG_VBEE}

# ---------------------------------------------------------------------------
# Nhãn — TIẾNG VIỆT, KHÔNG EMOJI
# ---------------------------------------------------------------------------
#: Chưa có key thì nói rõ phải làm gì. Đây là câu anh Hùng sẽ đọc trước khi
#: biết mình cần mua gì, nên phải có ĐỦ: cần key, mua ở đâu.
CAN_KEY = "cần key Vbee, xem vbee.vn"

#: Cảnh báo MỐC — bắt buộc hiện trong hộp chọn giọng. Xem khối đầu file.
CANH_BAO_MOC = ("Vbee không trả mốc từng chữ nên mốc phải dựng lại bằng bộ "
                "gióng hàng: phủ 98,6% và rung 90-119 ms, so với 16 ms của "
                "giọng thường - chữ bám lời kém hơn edge-tts")

#: Máy CHƯA có bộ gióng hàng thì còn tệ hơn nữa: không có mốc nào.
CANH_BAO_MOC_KHONG_GH = ("Vbee không trả mốc từng chữ, mà máy này chưa tải bộ "
                         "gióng hàng nên chữ sẽ KHÔNG chạy theo lời. Tải bộ "
                         "gióng hàng để hết bệnh này")

#: Cảnh báo TIỀN — Vbee tính theo điểm, 1 ký tự 1 điểm.
CANH_BAO_TIEN = ("tính tiền theo ký tự (1 ký tự = 1 điểm); gói thường chỉ cho "
                 "dùng MỘT NỬA số điểm qua API, phải gói VIP+ mới dùng trọn")

#: Cảnh báo GÓI FREE — nói ĐÚNG mức chắc chắn: chưa xác nhận, không phán bừa.
CANH_BAO_FREE = ("gói miễn phí 3.000 ký tự mỗi lượt: Vbee KHÔNG nói rõ gói "
                 "này có được dùng cho video kiếm tiền hay không - hỏi "
                 "contact@vbee.ai trước khi chạy sản xuất")


def la_giong_vbee(voice: str) -> bool:
    """Mã giọng này có thuộc file này không."""
    return str(voice or "").startswith(TIEN_TO_VBEE)


def canh_bao_moc() -> str:
    """Câu cảnh báo mốc ĐÚNG VỚI MÁY NÀY.

    KHÔNG cất kết quả vào hằng số: anh Hùng bấm nút tải bộ gióng hàng giữa
    phiên thì nhãn phải đổi theo, không đợi khởi động lại app (bài học
    `tg_so.duong_so` và `giong_ngoai.canh_bao_chat_luong`).
    """
    return CANH_BAO_MOC if _co_giong_hang() else CANH_BAO_MOC_KHONG_GH


def _co_giong_hang() -> bool:
    try:
        from app.core import giong_hang as _gh
        return bool(_gh.co_giong_hang())
    except Exception:  # noqa: BLE001 - thiếu module -> coi như chưa có
        return False


def nhan_giong(ma: str) -> str:
    """Nhãn đầy đủ cho hộp chọn giọng. TIẾNG VIỆT, KHÔNG EMOJI.

    Nhãn PHẢI mang cả ba cảnh báo (mốc + tiền + gói free). Đây không phải chỗ
    bán hàng: Piper/OmniVoice đã có tiền lệ ghi thẳng đánh đổi ngay trong
    nhãn, lý do là anh Hùng chạy 200-300 kênh.
    """
    for m, _vc, ten in GIONG_VBEE:
        if m == ma:
            if not co_key():
                return f"{ten} (Vbee) - {CAN_KEY}"
            return (f"{ten} (Vbee) - {canh_bao_moc()}; {CANH_BAO_TIEN}; "
                    f"{CANH_BAO_FREE}")
    return ma


def danh_sach_giong() -> list[tuple[str, str]]:
    """[(mã, nhãn)] để đổ vào combo.

    KHÁC `giong_ngoai.danh_sach_giong` MỘT ĐIỂM CÓ CHỦ Ý: ở đó, giọng không
    chạy được thì GIẤU đi (thiếu model 6 GB là chuyện người dùng không tự sửa
    nhanh được). Ở đây thứ còn thiếu chỉ là **một dòng key dán vào Cài đặt** —
    giấu giọng đi thì anh Hùng không bao giờ biết là có đường này để mua. Nên
    vẫn hiện, nhưng nhãn ghi thẳng `cần key Vbee, xem vbee.vn`, và `doc_loat`
    lùi edge-tts êm nếu bấm vào lúc chưa có key.
    """
    return [(m, nhan_giong(m)) for m, _vc, _t in GIONG_VBEE]


# ---------------------------------------------------------------------------
# KEY — LẤY TỪ ENV HOẶC Ô CÀI ĐẶT. KHÔNG GHI CỨNG, KHÔNG IN RA LOG
# ---------------------------------------------------------------------------
def _doc_cai_dat(ten: str) -> str:
    """Đọc một khoá cấu hình: ưu tiên biến MÔI TRƯỜNG, rồi tới `settings`.

    ĐỌC MỖI LẦN GỌI, không cất hằng số ở tầm module: anh Hùng dán key rồi bấm
    Lưu là phải ăn ngay, không phải khởi động lại app (bài học
    `tg_so.duong_so`). Cùng lý do, test đổi ENV giữa chừng vẫn đúng.
    """
    v = (os.environ.get(ten) or "").strip()
    if v:
        return v
    try:
        from config import settings
        return str(getattr(settings, ten, "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def thong_tin_key() -> tuple[str, str]:
    """(app_id, token). Thiếu một trong hai = coi như CHƯA CÓ KEY.

    Vbee cần ĐỦ CẢ HAI (`App-Id` + `Authorization: Bearer <token>`), khác
    Groq/ElevenLabs chỉ cần một chuỗi. Thiếu một nửa mà vẫn gọi là ăn 401 rồi
    tưởng key sai.
    """
    return _doc_cai_dat("VBEE_APP_ID"), _doc_cai_dat("VBEE_TOKEN")


def co_key() -> bool:
    """Có đủ key để gọi Vbee không. KHÔNG BAO GIỜ NÉM."""
    try:
        app_id, token = thong_tin_key()
        return bool(app_id and token)
    except Exception:  # noqa: BLE001
        return False


def che_key(s: str) -> str:
    """Che chuỗi bí mật trước khi đưa vào log/nhãn.

    **CỬA DUY NHẤT** để một chuỗi key được phép xuất hiện ở bất cứ đâu người
    đọc được. Giữ 4 ký tự cuối cho anh Hùng phân biệt được hai key, phần còn
    lại thay bằng dấu sao. Chuỗi ngắn -> che HẾT (4 ký tự cuối của một chuỗi
    6 ký tự gần như là cả chuỗi).
    """
    s = str(s or "")
    if not s:
        return "(chưa có)"
    if len(s) <= 8:
        return "*" * len(s)
    return "*" * 6 + s[-4:]


def tinh_trang_vbee() -> dict:
    """{co, thieu, app_id_che, gióng hàng...}. KHÔNG chứa key nguyên văn.

    `thieu` là danh sách để đặt NHÃN — nói đích danh còn thiếu gì, đừng chỉ
    nói "chưa có" (bài học cổng 58: hộp Demucs phải nêu tên từng gói).
    """
    app_id, token = thong_tin_key()
    thieu: list[str] = []
    if not app_id:
        thieu.append("App ID của Vbee (VBEE_APP_ID)")
    if not token:
        thieu.append("Access token của Vbee (VBEE_TOKEN)")
    return {
        "co": not thieu,
        "thieu": thieu,
        # CHE — không bao giờ trả nguyên văn ra ngoài, kể cả cho UI.
        "app_id_che": che_key(app_id),
        "token_che": che_key(token),
        "co_giong_hang": _co_giong_hang(),
        "ghi_chu": ("Vbee không trả mốc từng chữ; mốc lấy bằng bộ gióng hàng"
                    if _co_giong_hang() else
                    "Vbee không trả mốc từng chữ và máy chưa có bộ gióng hàng"
                    " -> chữ sẽ không chạy theo lời"),
    }


# ---------------------------------------------------------------------------
# LOG — LÙI ÊM MÀ IM LẶNG THÌ ĐÚNG BẰNG HỎNG ÂM THẦM
# ---------------------------------------------------------------------------
def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI / lỗi vào log ngày.

    Cùng luật với `piper_tts._ghi_log`, `giong_ngoai._ghi_log`,
    `dubbing._ghi_log_el`. **KHÔNG BAO GIỜ NÉM.**

    Chuỗi đưa vào đây phải ĐÃ che key (`che_key`) — hàm này không tự đoán được
    đâu là key. Có một lớp chắn cuối ở dưới: nếu lỡ lọt key vào chuỗi thì
    `_loc_bi_mat` thay nó bằng dấu sao.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"giong_vbee_{ts:%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {_loc_bi_mat(dong)}\n")
    except Exception:  # noqa: BLE001
        pass


def _loc_bi_mat(s: str) -> str:
    """LỚP CHẮN CUỐI: thay mọi lần xuất hiện của key thật bằng dấu sao.

    Vì sao cần dù mọi chỗ gọi đã tự che: lời lỗi của server ĐÔI KHI dội lại
    chính chuỗi mình gửi lên (`Bearer eyJ...`), mà chuỗi đó đi thẳng vào log
    qua `detail`. Một cửa quên là key nằm trong file log rồi đi theo lượt gửi
    log gỡ rối. Đây đúng bài học `prodown-cookie-temp-copy-every-spawn`: sót
    một cửa là hỏng cả.
    """
    out = str(s or "")
    try:
        for bi_mat in thong_tin_key():
            if bi_mat and len(bi_mat) >= 6:
                out = out.replace(bi_mat, che_key(bi_mat))
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------------------
# LỖI — PHÂN LOẠI CHO ĐÚNG. ĐÂY LÀ CHỖ ĐÃ ĐỐT SẠCH 38 KEY MỘT LẦN
# ---------------------------------------------------------------------------
class VbeeError(Exception):
    """Lỗi Vbee ĐÃ PHÂN LOẠI. `kind` quyết định app xử ra sao.

    BẢNG PHÂN LOẠI — chép đúng luật đã chốt trong repo, đừng sửa theo cảm tính:

      | kind        | HTTP | nghĩa                  | phạt key? | app làm gì   |
      |-------------|------|------------------------|-----------|--------------|
      | `key_sai`   | 401/403 | token/App-Id sai    | **CÓ**    | báo đúng key |
      | `het_diem`  | 500 TTS_SPEND_CREDITS_FAILED | hết điểm | **KHÔNG** | lùi edge |
      | `qua_tai`   | 429  | quá số lượt cùng lúc   | **KHÔNG** | đợi, thử lại |
      | `qua_to`    | 413  | yêu cầu quá to         | **KHÔNG** | THU NHỎ      |
      | `loi_app`   | 400  | mình gửi sai tham số   | **KHÔNG** | sửa app      |
      | `mang`      | -    | mạng đứt/timeout       | **KHÔNG** | lùi edge     |
      | `khac`      | 5xx  | server Vbee lỗi        | **KHÔNG** | lùi edge     |

    **429 KHÁC 413 — bug cũ hiểu sai 413 đã KHOÁ CẢ 38 KEY.** 413 là lỗi CỦA
    YÊU CẦU (mọi key đều dính, vì trần giống nhau), phạt key là tự bắn vào
    chân. 404 model chết cũng vậy: lỗi APP, không phải lỗi key.
    """

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind

    #: Có được phép phạt (khoá) đúng key này không. CHỈ `key_sai`.
    @property
    def phat_key(self) -> bool:
        return self.kind == "key_sai"


def _phan_loai(code: int, detail: str) -> VbeeError:
    """HTTP code + thân lỗi -> `VbeeError` đúng loại.

    Dò theo MÃ TRƯỚC, rồi mới tới chữ trong thân lỗi. Lý do: `detail` của Vbee
    có mã chữ (`TTS_SPEND_CREDITS_FAILED`...) nằm chung một chỗ với lời văn,
    mà lời văn thì đổi theo bản; mã số HTTP ổn định hơn.
    """
    d = (detail or "")[:600]
    dl = d.lower()
    if code in (401, 403):
        return VbeeError("key_sai",
                         f"Vbee từ chối key (HTTP {code}): {d}")
    if code == 413:
        # KHÔNG phạt key. Caller phải THU NHỎ yêu cầu.
        return VbeeError("qua_to", f"Yêu cầu quá to (HTTP 413): {d}")
    if code == 429:
        return VbeeError("qua_tai",
                         f"Vbee quá số lượt cùng lúc (HTTP 429): {d}")
    if "spend_credits" in dl or "credit" in dl or "insufficient" in dl:
        # Hết điểm. Đây KHÔNG phải lỗi key -> đừng khoá key, key vẫn đúng.
        return VbeeError("het_diem", f"Tài khoản Vbee hết điểm: {d}")
    if code == 400:
        return VbeeError("loi_app", f"App gửi sai tham số (HTTP 400): {d}")
    return VbeeError("khac", f"Vbee lỗi (HTTP {code}): {d}")


# ---------------------------------------------------------------------------
# GỌI HTTP — MỌI LƯỢT ĐỀU CÓ timeout=
# ---------------------------------------------------------------------------
def _headers() -> dict:
    app_id, token = thong_tin_key()
    return {
        "Authorization": f"Bearer {token}",
        "App-Id": app_id,
        "Content-Type": "application/json",
        # User-Agent tường minh: repo đã dính một lần Cloudflare trả 403
        # error 1010 vì UA mặc định của urllib.
        "User-Agent": "BQHungVideo/1.0 (+https://vbee.vn)",
    }


def _goi(url: str, body: Optional[dict] = None, method: str = "POST",
         timeout: float = 120.0) -> tuple[bytes, str]:
    """Gọi một lượt -> (thân nhị phân, content-type). Ném `VbeeError`.

    KHÔNG bao giờ đưa header (chứa token) vào lời lỗi.
    """
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(),
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), (r.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")
        except OSError:
            detail = ""
        raise _phan_loai(e.code, detail) from None
    except urllib.error.URLError as e:
        raise VbeeError("mang", f"Vbee lỗi mạng: {e.reason}") from None
    except (TimeoutError, OSError) as e:
        raise VbeeError("mang", f"Vbee lỗi mạng: {e}") from None


def tai_danh_sach_giong(timeout: float = 30.0) -> list[dict]:
    """Hỏi API danh sách giọng THẬT của tài khoản này.

    Vì sao có hàm này dù đã chốt cứng 3 mã: **"HN - Minh Quân" không có trong
    tài liệu**. Nếu Vbee đã thêm giọng đó (hoặc tài khoản anh Hùng có giọng
    riêng), hàm này thấy được mà không phải sửa mã. Trả `[]` nếu chưa có key /
    lỗi — KHÔNG BAO GIỜ NÉM.
    """
    if not co_key():
        return []
    try:
        raw, _ct = _goi(API_VOICES, None, "GET", timeout)
        d = json.loads(raw.decode("utf-8", "replace"))
    except (VbeeError, ValueError, UnicodeDecodeError) as e:
        _ghi_log(f"Hỏi danh sách giọng hỏng: {e}")
        return []
    kq = d.get("result") if isinstance(d, dict) else None
    ds = (kq or {}).get("voices") if isinstance(kq, dict) else None
    return [v for v in (ds or []) if isinstance(v, dict)]


# ---------------------------------------------------------------------------
# ĐẾM ĐIỂM TRƯỚC KHI CHẠY CẢ THƯ MỤC
# ---------------------------------------------------------------------------
def uoc_ky_tu(texts: list[str]) -> int:
    """Ước số KÝ TỰ sẽ tiêu cho cả loạt câu.

    Đếm đúng cái Vbee đếm: độ dài chuỗi `text` gửi lên (trường `characters`
    trong callback). Ước phải luôn **>= số thật** — ước hụt là anh Hùng tưởng
    đủ điểm rồi chết giữa mẻ 300 kênh (cùng luật `_uoc_token` của cổng 74).
    Nên đếm trên chuỗi ĐÃ chuẩn hoá y hệt lúc gửi.
    """
    return sum(len(_chuan_text(t)) for t in (texts or []))


def uoc_diem(texts: list[str], he_so: float = DIEM_MOI_KY_TU) -> int:
    """Ước số ĐIỂM sẽ tiêu. `credit_factor` = 1 cho mọi giọng HN đã liệt kê,
    nhưng vẫn để tham số vì API có trả `credit_factor` theo từng giọng."""
    import math
    return int(math.ceil(uoc_ky_tu(texts) * max(0.0, float(he_so))))


def canh_bao_truoc_me(texts: list[str], so_video: int = 1) -> str:
    """Câu cảnh báo TRƯỚC khi chạy cả thư mục. "" = không có gì phải báo.

    ĐỌC KỸ VÌ SAO CÂU NÀY KHÔNG GIỐNG ElevenLabs: ở ElevenLabs app đếm được
    số ký tự CÒN LẠI (`eleven_credit_remain`) nên so được "cần X / còn Y" rồi
    chặn trước. **Vbee KHÔNG có endpoint số dư** (xem đầu file), nên câu này
    chỉ nói được vế CẦN, không nói được vế CÒN. Nói thẳng như vậy còn hơn bịa
    ra một con số "còn lại" mà mình không biết.
    """
    ky_tu = uoc_ky_tu(texts)
    if ky_tu <= 0:
        return ""
    diem = uoc_diem(texts)
    s_kt = f"{ky_tu:,}".replace(",", ".")
    s_d = f"{diem:,}".replace(",", ".")
    phan = (f"Mẻ này ước tiêu khoảng {s_kt} ký tự Vbee (~{s_d} điểm)"
            + (f" cho {so_video} video" if so_video > 1 else "") + ". ")
    return phan + ("Vbee KHÔNG có cửa hỏi số điểm còn lại, nên app không biết "
                   "trước là có đủ hay không. Hết điểm giữa chừng thì video "
                   "còn lại tự đọc bằng giọng thường (edge-tts) và app ghi rõ "
                   "video nào bị lùi.")


# ---------------------------------------------------------------------------
# SỔ VIDEO BỊ LÙI — "GHI RÕ VIDEO NÀO BỊ LÙI", KHÔNG ĐỂ NỬA MẺ HAI GIỌNG
# ---------------------------------------------------------------------------
#: Sổ RAM: [(nhãn video, lý do)]. Nơi gọi đọc rồi in vào nhật ký dây chuyền.
#: CỐ Ý chỉ ở RAM và CỐ Ý không tự xoá: lượt chạy nào cũng phải tự
#: `xoa_so_lui()` trước khi bắt đầu, để sổ luôn là của ĐÚNG lượt đang chạy
#: (bài học `_SFX_LAST_PICK` — biến toàn cục đọc nhầm của lượt khác).
_SO_LUI: list[tuple[str, str]] = []


def xoa_so_lui() -> None:
    """Bắt đầu một lượt mới -> xoá sổ. Gọi ở đầu mỗi mẻ."""
    _SO_LUI.clear()


def _da_lui(nhan: str, ly_do: str) -> None:
    _SO_LUI.append((str(nhan or "?"), str(ly_do or "")))


def so_lui() -> list[tuple[str, str]]:
    """Bản SAO danh sách video đã phải lùi edge-tts trong lượt này."""
    return list(_SO_LUI)


def bao_cao_lui() -> str:
    """Câu tổng kết cho nhật ký. "" = không video nào bị lùi."""
    if not _SO_LUI:
        return ""
    dong = "; ".join(f"{n} ({l})" for n, l in _SO_LUI)
    return (f"{len(_SO_LUI)} video phải đọc bằng giọng thường (edge-tts) thay "
            f"vì Vbee: {dong}")


# ---------------------------------------------------------------------------
# ĐỌC MỘT CÂU
# ---------------------------------------------------------------------------
def _chuan_text(t: str) -> str:
    """Chuẩn hoá chuỗi gửi lên: bỏ xuống dòng, gộp khoảng trắng.

    Phải là CỬA DUY NHẤT, vì `uoc_ky_tu` đếm trên chính hàm này — đếm một
    đằng gửi một nẻo là ước sai tiền.
    """
    return " ".join(str(t or "").split())


def _speed_tu_rate(rate: str) -> float:
    """`"+25%"` -> 1,25. Kẹp vào dải Vbee cho phép (0,25 - 1,9).

    DÙNG NÚM `speed` CỦA CHÍNH MÁY ĐỌC, KHÔNG dùng `atempo`: repo đã đo trên
    edge-tts rằng đọc nhanh bằng `rate` thì méo = 0 theo cấu tạo, còn `atempo`
    là cắt-dán WSOLA (5,357 dB méo phổ ở 1,20). **Chưa đo trên Vbee** — đây là
    lập luận theo cơ chế, không phải số đo.
    """
    try:
        s = str(rate or "").strip().rstrip("%")
        v = 1.0 + float(s) / 100.0
    except (TypeError, ValueError):
        v = 1.0
    return max(0.25, min(1.9, v))


def _than_yeu_cau(text: str, voice_code: str, speed: float,
                  che_do: str) -> dict:
    body = {
        "text": text,
        "voiceCode": voice_code,
        "mode": che_do,
        "outputFormat": "wav",   # xin thẳng WAV, đỡ một đời giải mã mp3
        "speed": round(float(speed), 2),
    }
    return body


def _doc_sync(text: str, voice_code: str, speed: float,
              timeout: float) -> bytes:
    """Chế độ sync: trả THẲNG nhị phân. 1 lượt gọi, không poll."""
    raw, ct = _goi(API_TTS, _than_yeu_cau(text, voice_code, speed, "sync"),
                   "POST", timeout)
    if "json" in ct:
        # Server trả JSON ở chỗ đáng lẽ là audio = có lỗi mà mã vẫn 200.
        raise VbeeError("khac",
                        f"sync trả JSON thay vì audio: "
                        f"{raw.decode('utf-8', 'replace')[:300]}")
    if not raw or len(raw) < 500:
        raise VbeeError("khac", f"Vbee trả audio rỗng/quá ngắn "
                                f"({len(raw or b'')} byte)")
    return raw


def _doc_async(text: str, voice_code: str, speed: float, timeout: float,
               nhip: float = 1.5) -> bytes:
    """Chế độ async + POLL (không webhook — app để bàn không có URL công khai).

    CHƯA KIỂM ĐƯỢC VỚI KEY THẬT. Tài liệu ghi `webhookUrl` là bắt buộc cho
    async nhưng lại có sẵn cửa hỏi trạng thái; nếu Vbee từ chối thì ta ăn 400
    `loi_app` và cả loạt lùi edge-tts êm (không treo, không nổ).
    """
    raw, _ct = _goi(API_TTS, _than_yeu_cau(text, voice_code, speed, "async"),
                    "POST", timeout)
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except (ValueError, UnicodeDecodeError):
        raise VbeeError("khac", "async trả JSON hỏng") from None
    rid = str((d or {}).get("requestId") or (d or {}).get("request_id") or "")
    if not rid:
        raise VbeeError("khac", f"async không trả requestId: {str(d)[:300]}")

    han = time.time() + max(10.0, timeout)
    link = ""
    while time.time() < han:
        time.sleep(nhip)
        try:
            r2, _c2 = _goi(API_REQ + urllib.parse.quote(rid), None, "GET", 60.0)
            d2 = json.loads(r2.decode("utf-8", "replace"))
        except (VbeeError, ValueError, UnicodeDecodeError):
            continue
        kq = d2.get("result") if isinstance(d2.get("result"), dict) else d2
        tt = str((kq or {}).get("status") or "").upper()
        if tt in ("COMPLETED", "SUCCESS"):
            link = str((kq or {}).get("audioLink")
                       or (kq or {}).get("audio_link") or "")
            break
        if tt in ("FAILED", "FAILURE"):
            raise VbeeError("khac", f"Vbee báo đọc hỏng (request {rid[:8]}…)")
    if not link:
        raise VbeeError("khac", f"Quá giờ chờ Vbee (request {rid[:8]}…)")

    # Link audio KHÔNG cần header xác thực và HẾT HẠN SAU 3 PHÚT -> tải NGAY.
    try:
        req = urllib.request.Request(
            link, headers={"User-Agent": "BQHungVideo/1.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            au = r.read()
    except (urllib.error.URLError, OSError) as e:
        raise VbeeError("mang", f"Tải audio Vbee hỏng: {e}") from None
    if not au or len(au) < 500:
        raise VbeeError("khac", "Audio tải về rỗng/quá ngắn")
    return au


def _doc_mot(text: str, voice_code: str, speed: float,
             timeout: float) -> bytes:
    """Chọn đường sync/async rồi đọc một câu. Ném `VbeeError`."""
    if len(text) <= TRAN_SYNC and voice_code in _SYNC_DUOC:
        return _doc_sync(text, voice_code, speed, timeout)
    if len(text) > TRAN_ASYNC:
        # KHÔNG tự cắt câu: cắt là đổi ngữ điệu và làm hỏng gióng hàng. Câu
        # dài thế này là app gọi sai chỗ -> nói ra.
        raise VbeeError("qua_to",
                        f"Câu {len(text)} ký tự vượt trần {TRAN_ASYNC} của "
                        f"Vbee -> phải chia nhỏ ở nơi gọi")
    return _doc_async(text, voice_code, speed, timeout)


# ---------------------------------------------------------------------------
# GHI RA FILE — KHÔNG TIN "MÃ THOÁT 0", LUÔN ĐO LẠI
# ---------------------------------------------------------------------------
def dai_wav(p: str | Path) -> float:
    """Độ dài WAV theo giây (0.0 nếu đọc không được). Không gọi ffprobe."""
    try:
        with wave.open(str(p), "rb") as w:
            fr = w.getframerate() or 0
            return (w.getnframes() / float(fr)) if fr else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _ghi_wav(au: bytes, dich: Path) -> bool:
    """Ghi byte Vbee trả về thành WAV chuẩn ở `dich`. True = xong.

    Đi qua ffmpeg dù đã xin `outputFormat=wav`: Vbee có thể trả WAV lạ tần số
    /số kênh, mà bước gióng hàng và bước trộn sau đó đều muốn PCM đều đặn.
    **ffmpeg TRẢ MÃ 0 MÀ FILE RỖNG là chuyện đã xảy ra nhiều lần trong repo
    này** -> luôn kiểm KÍCH THƯỚC + ĐỘ DÀI, đừng tin mã thoát.
    """
    try:
        from config import settings
        dich.parent.mkdir(parents=True, exist_ok=True)
        tam = dich.with_suffix(dich.suffix + ".tai")
        tam.write_bytes(au)
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(tam), "-c:a", "pcm_s16le", str(dich)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300, creationflags=_NO_WIN)
        try:
            tam.unlink()
        except OSError:
            pass
        if r.returncode != 0 or not dich.exists() or dich.stat().st_size < 1024:
            _ghi_log(f"Ghi WAV hỏng ({dich.name}): rc={r.returncode} "
                     f"{(r.stderr or '')[-200:]}")
            return False
        if dai_wav(dich) <= 0.02:
            _ghi_log(f"Ghi WAV ra file 0 giây ({dich.name}) -> bỏ")
            return False
        return True
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Ghi WAV hỏng ({dich.name}): {type(e).__name__}: {e}")
        return False


# ---------------------------------------------------------------------------
# MỐC TỪNG CHỮ — GIÓNG HÀNG CƯỠNG BỨC (Vbee KHÔNG trả mốc)
# ---------------------------------------------------------------------------
def _lay_moc(wavs: list[str], texts: list[str], lang: str) -> list[list]:
    """Mốc `[[đầu, cuối, từ], ...]` cho từng câu, bằng gióng hàng cưỡng bức.

    Gióng hàng **không đoán chữ, nó ĐÃ BIẾT chữ** -> phủ 98,6% do cấu tạo,
    không tốn một lượt Groq nào, và rẻ hơn 5,2 lần đường Groq chép ngược.

    Máy chưa có bộ gióng hàng -> trả rỗng và NÓI RA. Không nội suy, không bịa.
    """
    n = len(wavs)
    rong: list[list] = [[] for _ in range(n)]
    if not _co_giong_hang():
        _ghi_log("Máy chưa có bộ gióng hàng -> giọng Vbee KHÔNG có mốc từng "
                 "chữ (Vbee không trả mốc). Chữ sẽ không chạy theo lời.")
        return rong
    try:
        from app.core import giong_hang as _gh
        moc = _gh.giong_hang_loat(wavs, texts, lang)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Gióng hàng hỏng ({type(e).__name__}: {e}) -> câu này "
                 f"KHÔNG có mốc (tiếng vẫn dùng được)")
        return rong
    if not isinstance(moc, list) or len(moc) != n:
        _ghi_log(f"Gióng hàng trả {len(moc) if isinstance(moc, list) else '?'}"
                 f" mục cho {n} câu -> bỏ mốc cả nhóm cho chắc")
        return rong
    return [m if isinstance(m, list) else [] for m in moc]


# ---------------------------------------------------------------------------
# CỬA CHÍNH — cùng hợp đồng `giong_ngoai.doc_loat` / `piper_tts.doc_loat`
# ---------------------------------------------------------------------------
#: Đọc được bao nhiêu câu thì mới coi cả loạt là dùng được. Xem `doc_loat`.
TY_LE_TOI_THIEU = 1.0


def doc_loat(texts: list[str], paths: list[str], voice: str,
             on_done: Optional[Callable[[int], None]] = None,
             rate: str | list = "+0%",
             lang: str = "",
             lay_moc: bool = True,
             han_giay: int = 1800,
             on_msg: Optional[Callable[[str], None]] = None,
             nhan_video: str = "",
             ) -> tuple[list[bool], list[list]]:
    """Đọc cả LOẠT câu bằng giọng Vbee. Cùng hợp đồng `_synth_all_words`.

    Trả `(ok, words)`: `ok[i]` = câu i đọc được chưa · `words[i]` =
    `[[đầu, cuối, từ], ...]`, rỗng nếu không lấy được mốc chắc chắn.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả `ok` toàn `False` để nơi gọi lùi về
    edge-tts (`dubbing._synth_all_words`).

    ═══ CHƯA CÓ KEY -> LÙI ÊM, KHÔNG NỔ ═══
    Đây là đường đi thường gặp nhất lúc này (anh Hùng chưa mua key): trả `ok`
    toàn `False` + ghi một dòng log nói rõ thiếu gì. Cùng luật với Piper và
    OmniVoice, khác luật Demucs (thiếu Demucs mà lùi là ra video HỎNG nên phải
    CHẶN; ở đây lùi ra video ĐÚNG, chỉ khác giọng).

    ═══ ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE — VÌ SAO ALL-OR-NOTHING ═══
    Đọc được 18/20 câu rồi để 2 câu kia lùi edge-tts thì video ra **LẪN HAI
    GIỌNG** giữa chừng — đúng mệnh đề cổng 63 canh, và mã thoát vẫn 0 nên
    không ai biết. Vì vậy chỉ cần MỘT câu không đọc được là trả `ok` toàn
    `False`: cả video một giọng edge-tts, xấu hơn nhưng ĐỀU. Và tên video được
    ghi vào sổ `so_lui()` để nhật ký nói ĐÍCH DANH video nào bị lùi — "đừng để
    nửa mẻ hai giọng" là yêu cầu, sổ này là cách chứng minh đã làm đúng.
    (`BQ_VBEE_TY_LE` hạ ngưỡng để đo/gỡ rối; đừng hạ trong sản xuất.)
    """
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]
    nhan = nhan_video or "(không rõ tên video)"

    def _xong_het() -> None:
        # Báo XONG cho MỌI câu kể cả câu rỗng/hỏng: nơi gọi ĐẾM số lần
        # `on_done` để chạy thanh tiến trình, thiếu một nhịp là thanh đứng mãi
        # không đủ (đúng cách `piper_tts.doc_loat` làm).
        for i in range(n):
            if on_done:
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass

    def _bo_ca_loat(ly_do: str) -> tuple[list[bool], list[list]]:
        _ghi_log(f"{nhan}: {ly_do} -> LÙI về edge-tts cho CẢ video")
        _da_lui(nhan, ly_do)
        _xong_het()
        return [False] * n, [[] for _ in range(n)]

    if n == 0:
        return ok, words

    if not la_giong_vbee(voice):
        return _bo_ca_loat(f"mã giọng lạ {voice!r}")

    voice_code = _BANG_MA.get(voice, "")
    if not voice_code:
        return _bo_ca_loat(f"chưa biết voiceCode cho {voice!r}")

    if not co_key():
        tt = tinh_trang_vbee()
        return _bo_ca_loat("chưa có key Vbee (thiếu: "
                           + ", ".join(tt["thieu"]) + f"; {CAN_KEY})")

    can = [i for i in range(n) if _chuan_text(texts[i])]
    if not can:
        _xong_het()
        return ok, words

    if on_msg:
        try:
            on_msg(f"Đang đọc {len(can)} câu bằng giọng Vbee...")
        except Exception:  # noqa: BLE001
            pass

    han = time.time() + max(30, int(han_giay))
    for k, i in enumerate(can):
        if time.time() > han:
            return _bo_ca_loat(f"quá giờ sau {k}/{len(can)} câu")
        txt = _chuan_text(texts[i])
        r_i = (rate[i] if isinstance(rate, list) and i < len(rate)
               else (rate if isinstance(rate, str) else "+0%"))
        try:
            au = _doc_mot(txt, voice_code, _speed_tu_rate(r_i), 120.0)
        except VbeeError as e:
            # PHÂN LOẠI ĐÚNG BỆNH — xem bảng ở `VbeeError`.
            if e.kind == "qua_tai":
                # 429 = quá số lượt CÙNG LÚC, không phải hết hạn mức. Nghỉ một
                # nhịp rồi thử LẠI ĐÚNG câu đó một lần. KHÔNG phạt key.
                time.sleep(3.0)
                try:
                    au = _doc_mot(txt, voice_code, _speed_tu_rate(r_i), 120.0)
                except VbeeError as e2:
                    return _bo_ca_loat(f"câu {i}: {e2}")
            elif e.kind == "het_diem":
                return _bo_ca_loat(
                    f"HẾT ĐIỂM Vbee ở câu {k + 1}/{len(can)} (nạp thêm điểm "
                    f"tại vbee.vn); key vẫn đúng, KHÔNG bị khoá")
            elif e.kind == "key_sai":
                tt = tinh_trang_vbee()
                return _bo_ca_loat(
                    f"KEY SAI hoặc hết hạn (App ID {tt['app_id_che']}, token "
                    f"{tt['token_che']}) - kiểm lại ở Cài đặt")
            else:
                return _bo_ca_loat(f"câu {i}: {e}")
        except Exception as e:  # noqa: BLE001
            return _bo_ca_loat(f"câu {i} lỗi lạ: {type(e).__name__}: {e}")

        if not _ghi_wav(au, Path(paths[i])):
            return _bo_ca_loat(f"câu {i}: ghi file tiếng hỏng")
        ok[i] = True
        if on_msg and (k + 1) % 5 == 0:
            try:
                on_msg(f"Vbee đã đọc {k + 1}/{len(can)} câu...")
            except Exception:  # noqa: BLE001
                pass

    # ---- chốt ALL-OR-NOTHING (chống video lẫn hai giọng) ----
    duoc = [i for i in can if ok[i]]
    try:
        nguong = float(os.environ.get("BQ_VBEE_TY_LE", TY_LE_TOI_THIEU))
    except ValueError:
        nguong = TY_LE_TOI_THIEU
    if len(duoc) < nguong * len(can):
        return _bo_ca_loat(f"chỉ đọc được {len(duoc)}/{len(can)} câu")

    # ---- MỐC: Vbee không trả, phải gióng hàng ----
    if lay_moc and duoc:
        moc = _lay_moc([paths[i] for i in duoc],
                       [_chuan_text(texts[i]) for i in duoc], lang)
        for vt, i in enumerate(duoc):
            if vt < len(moc):
                words[i] = moc[vt]

    co_moc = sum(1 for i in duoc if words[i])
    _ghi_log(f"{nhan}: Vbee đọc {len(duoc)}/{len(can)} câu bằng {voice} · "
             f"mốc {co_moc}/{len(duoc)} câu · ước tiêu "
             f"{uoc_ky_tu([texts[i] for i in can])} ký tự")
    _xong_het()
    return ok, words
