# -*- coding: utf-8 -*-
"""CHATTERBOX (Resemble AI) — MÁY **NHÂN BẢN GIỌNG**, không phải kho giọng.

═══════════════════════════════════════════════════════════════════════════
ANH HÙNG HỎI ĐÍCH DANH — VÀ CÂU TRẢ LỜI KHÔNG PHẢI CÁI ANH ẤY MONG
═══════════════════════════════════════════════════════════════════════════
Nguyên văn: *"chatter oke hơn à bạn test ky đi hay lỗi thôi **nếu có nhiều
giọng hay**"*.

**Chatterbox có ĐÚNG 0 giọng đặt tên sẵn.** Vế *"nếu có nhiều giọng hay"* —
điều kiện anh ấy đặt ra — **không thoả theo nghĩa đen**. Nhưng nó không phải
là "không có giọng nào": nó là **máy nhân bản**, đưa vào một mẫu tiếng thì đọc
bằng giọng của mẫu đó. Số giọng vì thế **bằng số mẫu anh Hùng đưa vào**, và đó
mới là cái đáng đo — nên file này đi cùng ``nhan_ban_giong.py``.

**GIẤY PHÉP: MIT — cả mã lẫn trọng số.** Rộng nhất trong mọi bộ đã xét, rộng
hơn hẳn OmniVoice (CC-BY-NC = **cấm** thương mại). Anh Hùng BÁN app nên đây là
điểm cộng thật, và là lý do bộ này đáng có mặt dù các số đo khác đều kém.

═══════════════════════════════════════════════════════════════════════════
CÓ MẤY GIỌNG THẬT — ĐO BẰNG ECAPA, 19/08/2026 (``_do_chatter.py``)
═══════════════════════════════════════════════════════════════════════════
Đưa **8 mẫu tiếng khác nhau** (sinh bằng 8 giọng edge-tts, nên biết CHẮC là 8
người khác nhau) rồi đếm bằng ECAPA-TDNN — thước đã hiệu chuẩn ở
``_do_nguoi_noi_ecapa``: **cùng giọng ~0,78 · khác giọng <= 0,31**.
(MFCC/cao độ là thước HỎNG cho việc này: tự-ồn 97,7 > khoảng cách thật 48,4.)

    cos(bản sao, MẪU của nó)        TB **0,812**   -> nhân bản CHẠY THẬT
    cos(bản sao, giọng MẶC ĐỊNH)    TB **0,193**   -> **ĐỐI CHỨNG ÂM ĐẠT**
    cos giữa hai bản sao khác nhau  TB 0,159 · max **0,759**
    ==> **8 mẫu vào -> 7 GIỌNG THẬT ra**

Cặp duy nhất DÍNH NHAU là ``en-GB-Ryan`` và ``en-CA-Liam`` (**0,759**, hai
giọng nam gần nhau); mọi cặp còn lại <= 0,404. Tức con số đúng là **7/8**,
không phải 8/8 — và cũng không phải "vô hạn giọng" như cách nói thường thấy.

**BẪY ĐO ĐÃ SẬP NGAY LƯỢT ĐẦU, VÀ NÓ LÀ LỖI CỦA *CHÍNH THƯ VIỆN* — PHẢI ĐỌC
TRƯỚC KHI VIẾT THÊM CHỖ GỌI:** ``ChatterboxMultilingualTTS`` **CẤT mẫu tham
chiếu lên chính đối tượng model** (``self.conds``). Gọi ``generate()`` mà
KHÔNG kèm ``audio_prompt_path`` thì nó **dùng lại mẫu của lượt TRƯỚC**, chứ
không quay về giọng mặc định. Lượt đo đầu xếp arm đối chứng ở CUỐI nên nó thừa
hưởng mẫu m7 -> đo ra ``cos(m7, mặc định) = 1,000``, tức **đối chứng âm không
hề là đối chứng**, mà bảng số vẫn đẹp và không một dòng báo.
**HỆ QUẢ CHO APP:** đọc cho kênh A rồi kênh B trong CÙNG một tiến trình mà
quên truyền mẫu là **kênh B ra giọng kênh A**. Vì vậy ``_chay`` ở dưới nhận
**ĐÚNG MỘT ``ref`` cho cả loạt** và **luôn sinh tiến trình mới** — đừng "tối
ưu" bằng cách giữ model sống qua nhiều kênh.

**LỀ IM ĐẦU FILE — số chưa ai đo, và nó to:** ``silencedetect`` trên chính file
Chatterbox trả về: TB **337 ms**, cá biệt **2.680 ms**. edge-tts chèn ~200 ms.
Đường thay tiếng đã có ``cat_le_loat`` cắt lề trước khi đo khung (v2.27.0) nên
không vỡ, **nhưng lối gọi mới nào quên cắt là câu đó trễ gần 3 giây.**

**NHẤN NHÁ 8 GIỌNG NHÂN BẢN** (thước cổng 76, cùng bộ 4 câu tiếng Anh):
**2,55 – 5,87, TRẢI 3,32**. So cho đúng: 17 giọng ``en-US`` của edge-tts trải
**3,31**, còn núm ``exaggeration`` của chính Chatterbox chỉ trải **1,84**.
Tức **nhân bản mới là chỗ Chatterbox cho thêm lựa chọn thật; vặn núm cảm xúc
thì cho ÍT lựa chọn hơn là đổi giọng edge-tts.** Nhưng nhớ: độ trải đó **đi
theo MẪU** (mẫu là 8 giọng edge-tts vốn đã trải 3,31) — Chatterbox giữ được
nhấn nhá của mẫu, chứ không tự sinh ra nó.

**TỐC ĐỘ ĐO LẠI TRÊN RTX 3060:** **1,30x** thời gian thật (bỏ lượt hâm máy:
**1,45x**) · VRAM **3,16-3,62 GiB** · nạp model **10-48 giây**.
Lượt đo mới nhất (bộ 48 câu): **cuda · 1,14x** thời gian thật · VRAM đỉnh
**4.898 MiB** · RAM đỉnh **5.143 MB**. Máy trắng phải tải **5,59 GB**.

**ĐỌC SAI CHỮ (Groq chép ngược, 192 từ):** tiếng Anh **4,2-4,7%**.
Lượt mới, bộ 48 câu: **48/48 câu đọc được**, WER **1,5-4,4%** so với trần bản
ngữ 0,0-1,5% (để so: VieNeu Adam đọc tiếng Anh **7,7-12,8%**).

**NHÂN BẢN CHẠY XUYÊN NGÔN NGỮ THẬT — thước ECAPA, không phải cảm nhận:**
cos(bản sao, mẫu CỦA NÓ) **0,727** vs cos(bản sao, mẫu KIA) **0,151**; độ trải
F0 giữa hai bản sao **7,83-8,33** nửa cung, bám đúng mẫu (mẫu trải 7,76).
Hai mẫu cách nhau xa là điều kiện bắt buộc của phép đo này — một mẫu thôi thì
không phân biệt được nhân bản với giọng mặc định (bài học cổng 88).

**MỐC TỪNG CHỮ: NÓ *KHÔNG TỰ TRẢ*, PHẢI NHỜ ``giong_hang``.**
``generate()`` trả đúng một khối sóng âm. App **KHÔNG** moi thuộc tính riêng
tư nào — ``dubbing._synth_all_words`` nhánh ``dung_cb`` gọi thẳng
``_moc_giong_hang`` (đúng cửa Piper/OmniVoice/Kokoro). Phủ mốc đo được:
**en 100,0% · ja 92,7% · zh 88,9%**. Máy chưa có bộ gióng hàng -> mốc RỖNG,
tiếng vẫn đúng.
(Nhãn ``CANH_BAO_CL`` bản cũ ghi *"mốc chữ phải MOI CỬA SAU ... rung 76 ms"* —
**tả một đường KHÔNG CÓ trong mã**, đã vá 21/08/2026.)

**ĐỌC LOẠN NHỊP — RỦI RO LỚN NHẤT CỦA BỘ NÀY, xem khối ``LANG_GIUA_*``.**
Lượt bàn giao ghi *"một bộ câu đọc 54,9s / trần 30,4s = 1,81 lần, câu tệ nhất
3,5 lần"*. **ĐO LẠI 21/08/2026 (`_do_chatter_nhip.py`, 26 câu, 3 bộ, GHÉP CẶP
trên CÙNG bộ WAV) KHÔNG TÁI HIỆN được 1,81 lần cho cả bộ — và cái tìm ra
NẶNG HƠN, chỉ khác chỗ.** Bảng (trần = edge-tts đọc CHÍNH những chữ ấy, đã
cắt lề im hai đầu ở cả hai bên):

    bộ            | trần   | THÔ            | CẮT LẶNG GIỮA  | câu tệ nhất
    en_ngan (12)  | 37,81s | 38,96s (1,03x) | 37,41s (0,99x) | 1,52x -> 1,34x
    en_dai   (8)  | 39,37s | 44,68s (1,14x) | 42,38s (1,08x) | **10,80x** -> 10,00x
    ja       (6)  | 24,43s | 24,79s (1,01x) | 22,72s (0,93x) | 1,65x -> 1,15x

**⚠ KẾT LUẬN *"KHÔNG TÁI HIỆN"* Ở TRÊN CHỈ ĐÚNG VỚI `en` VÀ `ja` — ĐỌC TIẾP.**
Bảng ấy **thiếu đúng bộ câu `zh`**, mà arm sinh ra con số 1,81x lại là
`A_nu × zh`; nó còn dùng một **MẪU KHÁC HẲN** (`en-US-AndrewMultilingual` thay
vì `A_nu` = `vi-VN-HoaiMy`). Tức nó bác một arm bằng cách đo ba arm KHÁC — xem
khối `NHIP_THEO_TIENG` và mục dưới đây.

**Tật KHÔNG rải đều — nó dồn vào CÂU NGẮN.** Câu 55-180 ký tự đọc gần đúng
nhịp (0,80-1,18x). Câu **5 ký tự** (*"Okay."*, trần 0,66s) ra **7,15 giây**
= **10,8 lần**: đó không phải khoảng lặng, đó là máy **đọc lan man** — cắt
lặng chỉ đưa về 6,62s. `nghi_doc_lan()` ghi log ca này chứ không chữa được;
chữa thật phải là đừng gửi câu quá ngắn cho nó.

**Khoảng lặng GIỮA CÂU thì có thật và cắt được:** 16 khoảng / 26 câu, dài
nhất **1,29 giây** (câu Nhật), tổng **9,12 giây** chết. Cắt xong: số câu chạm
trần `atempo` 1,50 tụt **5/26 -> 1/26** (câu còn lại đúng là ca "Okay.").
Chỗ ``cat_le_loat`` không với tới (nó chỉ cắt lề HAI ĐẦU) và
``doc_nhanh_vua_khung`` không chữa được (bộ này **không có** ``rate``).

**TIẾNG VIỆT: KHÔNG ĐỌC ĐƯỢC — sai 100%, đo thật chứ không đọc tài liệu.**
Gửi *"Một cơn bão chưa từng có trong lịch sử đang ập tới thành phố này."*
đọc ra *"Mokonbel, Chutanko, Tronglaichsatanglaichsatanichtanfo nai'e."*
Nó **không ném lỗi** — nó đọc ra một chuỗi vô nghĩa và trả mã 0. Đó là lý do
``ma_nhan_ban`` bắt buộc mang ``lang`` và ``tach_ma`` **từ chối mã thiếu ngôn
ngữ** thay vì đoán ``en``.

═══════════════════════════════════════════════════════════════════════════
SỐ ĐO CŨ — lượt 6 (``docs/GIONG_DOC_MIEN_PHI.md``), VẪN ĐÚNG
═══════════════════════════════════════════════════════════════════════════
**Đo tệ hơn edge-tts thì nói thẳng là tệ hơn.** Bảng dưới không uốn:

    ĐỘ KHỚP CHỮ (rung, thước Groq chép ngược, 403 mốc / 12 câu Anh):
        edge-tts **43,6 ms**  ·  Kokoro 46,1  ·  Piper 59,1
        ·  Chatterbox **76,2 ms** — **NHƯNG SỐ NÀY ĐO TRÊN MỘT ĐƯỜNG APP
        KHÔNG ĐI**, đừng chép nó vào nhãn lần nữa. Lượt đo đó tự moi thuộc
        tính riêng tư ``t3.patched_model.alignment_stream_analyzer`` để lấy
        mốc; **app không có một dòng nào làm việc đó** (và đúng ra là không
        nên: bản thư viện sau đổi tên là gãy im lặng). Đường THẬT của app là
        bộ gióng hàng — phủ mốc **en 100,0% · ja 92,7% · zh 88,9%**, xem khối
        trên. Hai con số ấy đo HAI THỨ KHÁC NHAU (rung của mốc vs tỉ lệ chữ
        CÓ mốc), không so thẳng được.

    ĐỌC SAI CHỮ / BỊA CHỮ (Groq chép ngược):
        Anh 4,0% (0,99x số chữ)  ·  Nhật 15,9% (**1,32x**)
        ·  Trung 28,8% (**1,66x**)
      -> tiếng Trung nó **đọc thêm cả một câu không hề có trong bản gửi
         vào**. Với người BÁN video thì đó là hỏng hàng, không phải lỗi nhỏ.

    TIẾNG VIỆT: **KHÔNG CÓ.** 23 thứ tiếng, không có ``vi``
        (``SUPPORTED_LANGUAGES`` đọc thẳng từ gói đã cài, không đọc quảng cáo).

    TỐC ĐỘ: GPU RTX 3060 **1,53x** thời gian thật · **CPU 0,25x**
        (1 phút tiếng tốn 4 phút máy). edge-tts 5,55x và **không tốn GPU**.
      -> **MÁY NHÂN VIÊN KHÔNG CÓ GPU thì tính năng này KHÔNG TỒN TẠI.** Đó là
         mệnh đề mạnh hơn "chậm": 0,25x nghĩa là mẻ 300 video không chạy nổi.
         Nhãn phải nói thẳng (``CANH_BAO_MAY``), và đường đọc **không được lùi
         im lặng** sang giọng khác giữa mẻ — lùi im lặng là video LẪN HAI
         GIỌNG với ``rc`` vẫn 0. ``_chatter_hay_khong`` vì thế ghi log MỖI lần
         lùi, và ``doc_loat`` là **all-or-nothing** (18/20 câu cũng bỏ cả loạt).

    ĐỘ DÀI KHÔNG ĐIỀU KHIỂN ĐƯỢC: không có tham số ``speed``/``duration``;
        cùng câu cùng tham số 8 lượt chênh **33,7%**. **Đóng seed thì chênh
        0,0%** (``torch.manual_seed``) — nên phải đóng seed, xem ``_MA_DOC``.
        Ép vừa khung bằng ``rubberband``: 1,337x méo **0,901 dB**, **0,0%** từ
        sai. Tức "không có núm thời lượng" **KHÔNG** phải án tử; án tử là mốc
        chữ và chuyện không có tiếng Việt.

    ĐÓNG DẤU CHÌM (Resemble Perth): **BẮT BUỘC, không tắt được.** Mọi file ra
        đều mang dấu để máy nhận ra là AI. Phải nói cho anh Hùng biết.

**VÌ SAO VẪN THÊM:** giấy phép MIT + nhân bản giọng chạy thật (số đo ở
``nhan_ban_giong``). Với kênh **tiếng Anh** và máy **có GPU**, nó cho anh Hùng
thứ edge-tts không có: **giọng riêng, không ai khác trên YouTube có**. Ngoài
hai điều kiện đó thì **edge-tts hơn ở mọi cột** — nhãn trong hộp chọn giọng
ghi thẳng như vậy.

═══════════════════════════════════════════════════════════════════════════
TIẾN TRÌNH RIÊNG — BẮT BUỘC, KHÔNG PHẢI CHO GỌN
═══════════════════════════════════════════════════════════════════════════
Trong tiến trình đã nạp PyQt6 thì ``import torch`` chết với
``OSError [WinError 1114] ... torch\\lib\\c10.dll`` (tái hiện 100%: torch
TRƯỚC Qt -> OK · torch SAU Qt -> 1114), và ``try/except`` **không chặn được
ACCESS VIOLATION**. App này LÀ app Qt. Demucs đã phải làm đúng vậy sau khi
tính năng v2.24.0 hoá ra KHÔNG BAO GIỜ chạy được khi bấm từ giao diện — mà
lỗi lại đội lốt *"máy chưa cài Demucs"*.

Vì vậy trong CẢ FILE NÀY: **KHÔNG ``import torch``, KHÔNG ``import
chatterbox``**, kể cả trong ``try/except``; **KHÔNG** chèn thư mục gói vào
``sys.path`` của app; dò "đã cài chưa" bằng **FILE CÓ TỒN TẠI KHÔNG**, không
bằng ``find_spec`` (``find_spec`` phải NẠP gói cha, và nó luôn tìm trên
``sys.path`` nên không trả lời được câu *"gói có nằm ĐÚNG CHỖ KIA không"* —
bài học cổng 58: máy dev mượn torch của ``.venv`` rồi báo "đã cài" trong khi
``_lib`` thiếu).

**MỌI ĐƯỜNG RA ĐỀU ĐẶT ``_sandbox``.** Nơi gọi dọn bằng
``xoa_an_toan.don_thu_muc(ket.get("_sandbox"))``; thiếu khoá là ``Path("")``
= **thư mục đang làm việc**, và chuyện đó đã xoá sạch cây mã một lần
(``b5bd003``).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from app.core import doc_lan

_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: Tiền tố mã giọng. Mã edge-tts KHÔNG BAO GIỜ chứa `:` nên các họ giọng
#: không lẫn nhau — quy ước đã chốt ở `giong_bang._TIEN_TO`.
#:
#: **LUỒNG LẮP GIAO DIỆN PHẢI THÊM `("cb:", CHATTER)` VÀO
#: `giong_bang._TIEN_TO`.** Thiếu dòng đó thì `nguon()` trả về `edge` và giọng
#: Chatterbox rơi vào nhóm sai, mất nhãn "cần tải", **không một dòng báo** —
#: đúng lỗi `vieneu:`/`vn:` đã sập một lần (`24a3bcf`).
TIEN_TO = "cb:"

#: 23 thứ tiếng — đọc từ chính gói đã cài (`chatterbox.SUPPORTED_LANGUAGES`),
#: KHÔNG chép từ trang giới thiệu. **KHÔNG CÓ `vi`.**
TIENG: dict[str, str] = {
    "ar": "Ả Rập", "da": "Đan Mạch", "de": "Đức", "el": "Hy Lạp",
    "en": "Anh", "es": "Tây Ban Nha", "fi": "Phần Lan", "fr": "Pháp",
    "he": "Do Thái", "hi": "Hindi", "it": "Ý", "ja": "Nhật",
    "ko": "Hàn", "ms": "Mã Lai", "nl": "Hà Lan", "no": "Na Uy",
    "pl": "Ba Lan", "pt": "Bồ Đào Nha", "ru": "Nga", "sv": "Thuỵ Điển",
    "sw": "Swahili", "tr": "Thổ Nhĩ Kỳ", "zh": "Trung",
}

GIAY_PHEP = "giấy phép MIT (cả mã lẫn trọng số) - bán được"

# ---------------------------------------------------------------------------
# NHỊP ĐỌC THEO **TIẾNG** — số đo, và nó KHÔNG rải đều
# ---------------------------------------------------------------------------
#: ═══ MỘT TẬT CÓ THẬT SUÝT BỊ ĐÓNG SỔ VÌ ĐO THIẾU MỘT ARM (26/08/2026) ═══
#: Con số báo động đầu tiên của bộ này là arm **`A_nu × zh`**: đọc **54,9 s**
#: cho bộ câu mà trần bản ngữ chỉ **30,4 s** = **1,81x** (`_kq_chatter_dangn.
#: json`). Lượt đo lại kết luận *"không tái hiện được"* rồi **hạ con số đó
#: khỏi nhãn** — nhưng bộ đo lúc ấy chỉ có `en_ngan`/`en_dai`/`ja`, **THIẾU
#: ĐÚNG `zh`**, và còn dùng một MẪU khác hẳn. Nó bác một arm bằng cách đo ba
#: arm KHÁC.
#:
#: Dựng lại ĐÚNG arm (cùng 8 câu, cùng mẫu `A_nu`) thì tật **CÓ tái hiện**.
#: Thước THÔ = độ dài file CHƯA cắt lề (đúng thước bảng 25/08 dùng):
#:
#:     arm                        | trần(thô) | THÔ     | tỉ lệ | câu tệ nhất
#:     zh_goc@A_nu (mẫu 25/08)    |  30,53 s  | 54,88 s | 1,80x |   3,44x
#:     zh_goc@A_nu (mẫu sinh lại) |  30,53 s  | 50,84 s | 1,67x |   3,26x
#:     zh_goc@B_nam (ĐỐI CHỨNG)   |  30,53 s  | 24,08 s | 0,79x |   0,92x
#:
#: Hàng ĐẦU là phép so thẳng với bảng 25/08 và nó khớp **tới từng câu**:
#: 3,98/12,06/5,02/7,86/3,94/4,38/8,10/9,54 giây so với 4,0/12,1/5,0/7,9/3,9/
#: 4,4/8,1/9,5 — tổng **54,88 s vs 54,90 s**, tỉ lệ **1,798x vs 1,806x**.
#: Tức **1,81x TÁI HIỆN, không phải số rút thăm.**
#:
#: ...và trên thước ĐÚNG CHO APP (đã cắt lề hai đầu như `cat_le_loat` làm, rồi
#: chạy `cat_lang_giua` — tức đúng thứ `khop_thoi_gian` nhìn thấy) thì nó
#: **TỆ HƠN**, vì trần edge-tts chèn lề đuôi tới 860 ms còn Chatterbox ít hơn:
#:
#:     arm            | trần  | THÔ            | SAU CẮT LẶNG   | tệ nhất
#:     zh_goc@A_nu    | 25,52 | 50,14 (1,97x)  | 47,16 (1,85x)  | 3,79 -> 3,56
#:     zh_goc@B_nam   | 25,52 | 20,88 (0,82x)  | 20,70 (0,81x)  | 1,00 -> 1,00
#:     zh@A_nu (trộn) | 62,50 | 78,85 (1,26x)  | 75,07 (1,20x)  | 3,33 -> 2,80
#:     en_ngan@A_nu   | 37,75 | 49,91 (1,32x)  | 46,88 (1,24x)  | 1,79 -> 1,68
#:
#: **CỘT `en_ngan@A_nu` LÀ CHỖ PHẢI ĐỌC KỸ.** Cùng 12 câu tiếng Anh ấy, bảng
#: 21/08 (mẫu `en-US-AndrewMultilingual`) ra **1,03x**; hôm nay với mẫu `A_nu`
#: ra **1,32x**. Tức **MẪU kéo nhịp đọc, không riêng gì TIẾNG** — `A_nu` là
#: một mẫu "đọc chậm" ở mọi tiếng. Nhưng nó chỉ đẩy tiếng Anh từ 1,03 lên 1,32
#: còn tiếng Trung thì từ 0,81 (mẫu `B_nam`) lên **1,85**: cùng một mẫu, tiếng
#: Trung đắt hơn tiếng Anh **1,5 lần nữa**, và ĐỘ TRẢI của tiếng Trung
#: (0,81-1,85) rộng gấp bốn tiếng Anh (0,99-1,24).
#: Trần đối chứng khớp bảng cũ trong **0,06 s / 0,2%** (37,75 vs 37,81) nên máy
#: hôm nay không khác máy hôm đó — chênh lệch là của MẪU, không của môi trường.
#:
#: **`cat_lang_giua` ĂN ĐƯỢC BAO NHIÊU TRÊN `zh` — ÍT, VÀ PHẢI NÓI THẲNG:**
#: 7 khoảng lặng giữa câu / 8 câu, tổng **4,39 s** (dài nhất **1,44 s**), cắt
#: được 5/8 câu và bỏ **2,98 s** chết -> **1,97x xuống 1,85x** (bớt 0,12x,
#: tức **6%** của phần dôi). Và cột đáng đọc hơn cả: **số câu chạm trần
#: `atempo` 1,50 KHÔNG đổi — 4/8 trước và 4/8 sau.** Nghĩa là với tiếng Trung,
#: chỗ dôi ra **KHÔNG phải khoảng lặng** mà là chính tiếng nói bị kéo dài, nên
#: cắt lặng chữa được rất ít. (Trên `en_dai` nó từng đưa chạm trần 5/26 xuống
#: 1/26 — khác hẳn.)
#:
#: ═══ VÌ SAO CÓ HAI HÀNG `A_nu`, VÀ ĐÂY LÀ BÀI HỌC ĐÁNG NHỚ NHẤT ═══
#: Hai hàng đó **cùng mẫu câu, cùng giọng mẫu `vi-VN-HoaiMy`, cùng `CAU_MAU`,
#: cùng seed** — khác nhau đúng một thứ: **BYTE của file mẫu**. edge-tts
#: KHÔNG trả về audio giống từng byte cho cùng chữ + cùng giọng qua các ngày
#: (mp3 25/08 và mp3 26/08 **cùng cỡ 49.824 byte, khác MD5**). Chatterbox thì
#: **TIỀN ĐỊNH tuyệt đối** theo bộ `(chữ, mẫu, tiếng, seed)` — đo được: 6 câu
#: dùng chung giữa bộ `zh_goc` và bộ `zh` cho ra tỉ lệ GIỐNG NHAU tới 2 chữ
#: số thập phân, ở HAI tiến trình và HAI vị trí khác nhau trong mẻ.
#: **QUY TẮC RÚT RA: với máy nhân bản, "cùng giọng, cùng câu" KHÔNG phải là
#: "cùng mẫu".** Muốn dựng lại một phép đo nhân bản thì phải giữ lại chính
#: FILE mẫu; sinh lại mẫu là đo một arm khác. Đó cũng là lý do lượt đo lại
#: 21/08 kết luận nhầm "không tái hiện được".
#: **HỆ QUẢ CHO ANH HÙNG:** con số này đi theo MẪU anh ấy đưa vào, nên nhãn
#: ghi DẢI chứ không ghi một số — mẫu khác có thể tệ hơn 1,80x.
#:
#: **WER của chính arm đó chỉ 1,5%** -> nó **đọc ĐÚNG CHỮ, SAI NHỊP**. Đó là
#: lý do mọi thước "đọc sai chữ" đều nói bộ này ổn trong khi tiếng ra dài gấp
#: rưỡi: hai thước đo hai chuyện khác nhau, và cột WER **không** thay được cột
#: nhịp.
#:
#: **BẢNG NÀY LÀ NGUỒN DUY NHẤT** — nhãn, tooltip và dòng cảnh báo lúc chọn
#: tiếng đều đọc từ đây (một phép đo, nhiều chỗ đọc; bài học cổng 58 *"nút ghi
#: 155 MB, hộp doạ 2 GB"*). Đo thêm tiếng nào thì thêm dòng, đừng gõ tay số
#: vào nhãn.
#: Khoá = mã ngôn ngữ · giá trị = `(XẤU NHẤT, TỐT NHẤT, CÂU TỆ NHẤT)` đo trên
#: các MẪU đã thử, **thước SAU `cat_lang_giua`** (= đúng thứ người dùng nhận).
#: Ghi cả hai đầu là cố ý: một số lẻ ở đây là lời hứa không giữ được, vì con
#: số đi theo MẪU chứ không theo tiếng.
NHIP_THEO_TIENG: dict[str, tuple[float, float, float]] = {
    # zh: A_nu 1,85x · B_nam 0,81x   (câu tệ nhất 3,56x)
    "zh": (1.85, 0.81, 3.56),
    # en: A_nu 1,24x · Andrew 0,99x  (câu tệ nhất 1,67x)
    "en": (1.24, 0.99, 1.67),
    # ja: mới đo ĐÚNG MỘT mẫu (Andrew) -> hai đầu bằng nhau, và đó là điểm
    # YẾU của dòng này chứ không phải điểm mạnh: xem "CHƯA ĐO ĐỦ" ở dưới.
    "ja": (0.93, 0.93, 1.15),
}

#: Dưới mức này thì **KHÔNG KÊU**. Kêu cho cả `en`/`ja` là cảnh báo rác, mà
#: cảnh báo rác thì người ta thôi đọc cảnh báo.
#: **1,25 KHÔNG phải số tròn cho đẹp — nó nằm giữa hai nhóm ĐÃ ĐO:** cao nhất
#: của nhóm ổn là `en@A_nu` **1,24**, thấp nhất của nhóm hỏng là `zh@A_nu`
#: **1,85**. Nhưng biên trên chỉ còn **0,01** nên đây là chỗ MỎNG: đo thêm một
#: mẫu tiếng Anh chậm hơn nữa là `en` sẽ vượt ngưỡng, và lúc đó phải ĐỔI BẢNG
#: (thêm dòng, nói ra số) chứ **không được nới ngưỡng cho hết kêu**.
NHIP_KEU_TU = 1.25

#: Tiếng **CHƯA ĐO** thì nói thẳng là chưa đo, đừng im (im = người dùng hiểu
#: nhầm thành "đã đo và không sao"). 23 thứ tiếng mà mới đo được 3.
#: **SUY TỪ BẢNG, KHÔNG GÕ TAY** — hai danh sách là hai chỗ để lệch nhau.
NHIP_DA_DO = tuple(NHIP_THEO_TIENG)


def so_thap(x: float) -> str:
    """``1.67`` -> ``"1,67"``. Dấu phẩy tiếng Việt, **chỉ đổi CON SỐ**.

    Cùng lý do ``so_gb`` tồn tại: ``str(...).replace(",", ".")`` trên CẢ CÂU
    đã biến *"một lần, dùng chung"* thành *"một lần. dùng chung"* hai lần
    trong repo này. Để RIÊNG khỏi ``so_gb`` vì hai bên khác đơn vị và khác
    số chữ số — gộp làm một là lần sau đổi định dạng GB thì nhãn nhịp đổi theo.
    """
    try:
        return f"{float(x):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "?"


def canh_bao_nhip(lang: str) -> str:
    """Lời cảnh báo NHỊP ĐỌC cho một tiếng. ``""`` = tiếng này đọc đúng nhịp.

    Ba đường ra, và **ba đường đều phải khác nhau**:
      · tiếng đo được là HỎNG   -> nêu SỐ ĐO + nói rõ là sai NHỊP chứ không
        phải sai CHỮ (WER 1,5%), vì người đọc rất dễ đi soi bản dịch;
      · tiếng đo được là ỔN     -> ``""``, không kêu oan;
      · tiếng CHƯA ĐO           -> nói thẳng *"chưa đo"*.
    """
    ma = str(lang or "").strip()
    ty = NHIP_THEO_TIENG.get(ma)
    if ty and ty[0] >= NHIP_KEU_TU:
        return (f"ĐỌC LOẠN NHỊP ở tiếng {TIENG.get(ma, ma)}: đo trên hai MẪU "
                f"giọng khác nhau ra {so_thap(ty[1])} và {so_thap(ty[0])} lần "
                f"thời gian một giọng thường đọc cùng chữ ấy, câu tệ nhất "
                f"{so_thap(ty[2])} lần - nó đọc ĐÚNG CHỮ (sai chữ chỉ 1,5%) "
                f"nhưng SAI NHỊP, mà bộ này KHÔNG có núm chỉnh tốc độ nên chỉ "
                f"gỡ được bằng cách ép nhanh (méo tiếng); con số đi theo MẪU "
                f"anh đưa vào nên mẫu khác có thể tệ hơn")
    if ma and ma not in NHIP_DA_DO:
        return (f"nhịp đọc tiếng {TIENG.get(ma, ma)} CHƯA AI ĐO - mới đo Anh, "
                f"Nhật, Trung; tiếng Trung đo ra loạn nhịp tới "
                f"{so_thap(NHIP_THEO_TIENG['zh'][0])} lần nên tiếng chưa đo "
                f"cũng có thể như vậy")
    return ""

#: Cảnh báo CHẤT LƯỢNG — cùng luật Piper/OmniVoice: tệ hơn edge-tts thì phải
#: ghi ra ngay trên DÒNG, đừng để người dùng tự phát hiện sau 300 video.
#:
#: ═══ NHÃN NÀY TỪNG MÔ TẢ MỘT ĐƯỜNG **KHÔNG CÓ TRONG MÃ** — VÁ 21/08/2026 ═══
#: Bản cũ mở đầu bằng *"mốc chữ phải MOI CỬA SAU của thư viện nên rung 76 ms"*.
#: Câu đó tả đúng cái mà lượt ĐO lượt 6 đã làm (moi
#: ``t3.patched_model.alignment_stream_analyzer``), nhưng **app KHÔNG đi đường
#: đó một dòng nào**: ``dubbing._synth_all_words`` lấy mốc bằng **BỘ GIÓNG
#: HÀNG** (``_moc_giong_hang``, đúng cửa Piper/OmniVoice/Kokoro đang đi) — đọc
#: thẳng ở ``dubbing.py`` nhánh ``dung_cb`` là thấy. Nhãn nói một đường, mã
#: chạy một nẻo; ai đọc nhãn rồi đi tìm "cửa sau" đó trong mã sẽ không thấy,
#: còn ai tin con số 76 ms sẽ so nhầm với một phép đo KHÁC hẳn.
#: Số ĐÚNG của đường app đi là **PHỦ MỐC của bộ gióng hàng**: en **100,0%** ·
#: ja 92,7% · zh 88,9% (máy chưa có bộ gióng hàng -> mốc RỖNG, tiếng vẫn đúng).
#:
#: **Vế tiếng Việt phải nói rõ nó hỏng KIỂU GÌ, không chỉ nói "không có".**
#: Ép đọc tiếng Việt thì nó KHÔNG ném lỗi và KHÔNG câm — nó đọc ra một chuỗi
#: vô nghĩa (*"Một cơn bão chưa từng có"* -> *"Mokonbel, Chutanko..."*) rồi
#: trả mã 0. Người dùng nhận được file nghe được, tưởng đã xong.
#:
#: ═══ VÁ LẦN HAI 26/08/2026 — NHÃN ĐANG GIẤU MỘT TẬT CÓ THẬT ═══
#: Bản trước chỉ nói tật CÂU NGẮN (*"5 ký tự -> 7,15 giây"*), vì lượt đo lại
#: **thiếu đúng bộ câu `zh`** rồi kết luận 1,81x "không tái hiện được". Đo lại
#: đúng arm thì tiếng Trung **CÓ loạn nhịp cả bộ** — xem `NHIP_THEO_TIENG`.
#: Vế đó nay lấy THẲNG từ bảng số (`canh_bao_nhip`), không gõ tay.
CANH_BAO_CL = ("mốc từng chữ do BỘ GIÓNG HÀNG dựng chứ máy đọc KHÔNG tự trả "
               "(phủ mốc: Anh 100,0% · Nhật 92,7% · Trung 88,9%; máy chưa có "
               "bộ gióng hàng thì chữ không chạy theo lời); "
               + canh_bao_nhip("zh") + "; CÂU NGẮN THÌ ĐỌC "
               "LAN MAN - đo thật một câu 5 ký tự ra 7,15 giây, gấp 10,8 lần "
               "giọng thường; KHÔNG có tiếng Việt (ép "
               "đọc thì ra chuỗi vô nghĩa mà vẫn báo thành công); mọi file "
               "đều bị ĐÓNG DẤU CHÌM không tắt được")

#: Cảnh báo MÁY — số đo, không phải lời doạ. **BẮT BUỘC**, không phải "nên có":
#: CPU đo **0,25x thời gian thật** = 1 phút tiếng tốn 4 phút máy, tức mẻ 300
#: video là không thể. Máy nhân viên không GPU thì tính năng này **không tồn
#: tại** — nhãn phải nói thẳng, và đường đọc KHÔNG được lùi im lặng sang giọng
#: khác giữa mẻ (lùi im lặng = video LẪN HAI GIỌNG, ``rc`` vẫn 0).
CANH_BAO_MAY = ("BẮT BUỘC GPU NVIDIA: card rời đọc nhanh 1,14 lần thời gian "
                "thật (VRAM đỉnh 4,9 GB), còn CPU chỉ 0,25 lần - 1 phút tiếng "
                "tốn 4 phút máy, không dùng cho sản xuất được")

#: ĐÓNG DẤU CHÌM — **anh Hùng BÁN video ra, phải cho anh ấy biết, đừng giấu.**
#: ``chatterbox/mtl_tts.py:317`` trả thẳng ``watermarked_wav``: không có tham
#: số nào tắt được, không có nhánh nào bỏ qua. Mọi file tiếng ra khỏi bộ này
#: đều mang dấu Resemble Perth để máy nhận ra là AI.
DONG_DAU_CHIM = ("mọi file tiếng đều bị ĐÓNG DẤU CHÌM (Resemble Perth) để máy "
                 "nhận ra là AI - KHÔNG TẮT ĐƯỢC, không có tham số nào bỏ qua")

#: Trọng số tải từ Hugging Face lúc chạy lần đầu.
REPO_CB = "ResembleAI/chatterbox"

#: Lượng tải trên MÁY TRẮNG — **đo thật, đơn vị GB đúng như lúc đo**.
#: Cất thẳng con số đo được, KHÔNG cất MB rồi chia 1024 lúc hiển thị: phép
#: quy đổi đó biến 5,59 thành **5,46** (GB thập phân vs GiB nhị phân) và nhãn
#: sẽ nói một số KHÔNG AI TỪNG ĐO. Đúng lớp lỗi cổng 58 "nút ghi 155 MB, hộp
#: doạ 2 GB", chỉ nhỏ hơn.
GB_TAI = 5.59


def so_gb(gb: Optional[float] = None) -> str:
    """``5.59`` -> ``"5,59"``. Dấu phẩy tiếng Việt, **chỉ đổi CON SỐ**.

    ``str(x).replace(",", ".")`` trên CẢ CÂU đã biến *"một lần, dùng chung"*
    thành *"một lần. dùng chung"* hai lần trong repo này (``giong_kokoro``
    dòng 817/850 vẫn còn lỗi đó). Một phép đo, nhiều chỗ đọc — **đừng gõ tay
    con số vào nhãn / tooltip / hộp xác nhận** (cổng 58: nút ghi 155 MB, hộp
    doạ 2 GB).
    """
    try:
        return f"{float(GB_TAI if gb is None else gb):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "?"


#: Nhãn nút tải. **PHẢI KHỚP ĐƯỜNG SẼ ĐI** (cổng 71 CA 4): con số này là
#: lượng tải THẬT của môi trường Python (torch CUDA + thư viện) cộng trọng số.
#: Ghi 155 MB rồi tải 2,5 GB là lặp đúng lỗi cũ.
NHAN_TAI = (f"Tải bộ nhân bản giọng Chatterbox (khoảng {so_gb()} GB, "
            f"BẮT BUỘC GPU NVIDIA)")


def la_giong_chatter(voice: str) -> bool:
    return str(voice or "").startswith(TIEN_TO)


def ma_nhan_ban(duong_mau: str, lang: str = "en") -> str:
    """Mã giọng cho MỘT file mẫu: ``cb:<lang>|<đường dẫn>``.

    Ngôn ngữ nằm TRONG mã chứ không đoán lúc đọc: ``generate()`` bắt buộc có
    ``language_id``, đoán sai là model đọc chữ Anh bằng luật phát âm tiếng
    Ba Lan mà **vẫn ra tiếng, vẫn mã thoát 0**.
    """
    return f"{TIEN_TO}{(lang or 'en').strip()}|{str(duong_mau or '').strip()}"


def tach_ma(ma: str) -> tuple[str, str]:
    """``cb:en|D:\\mau.wav`` -> ``("en", "D:\\mau.wav")``. Sai dạng -> ``("","")``."""
    s = str(ma or "")
    if not s.startswith(TIEN_TO):
        return "", ""
    than = s[len(TIEN_TO):]
    if "|" not in than:
        # Mã cũ/thiếu ngôn ngữ: KHÔNG đoán là 'en' rồi chạy tiếp — trả rỗng để
        # nơi gọi lùi êm về edge-tts và GHI LOG. Đoán bừa là "chọn X ra Y".
        return "", ""
    lang, duong = than.split("|", 1)
    lang = lang.strip()
    if lang not in TIENG:
        # Ngôn ngữ lạ -> trả RỖNG CẢ HAI, đúng như docstring hứa. Bản đầu trả
        # `("", duong)`: nơi gọi vẫn an toàn (nó kiểm cả hai) nhưng hàm nói
        # một đằng làm một nẻo, và lối gọi MỚI nào chỉ kiểm `lang` sẽ đi tiếp
        # với một đường dẫn hợp lệ. Cổng 81 CA 6f bắt được chỗ này.
        return "", ""
    return lang, duong.strip()


def nhan_giong(ma: str, ten_hien: str = "") -> str:
    """Nhãn đầy đủ cho hộp thoại / tooltip. TIẾNG VIỆT, KHÔNG EMOJI.

    Nhãn PHẢI mang đủ BỐN vế (giấy phép · chất lượng · máy · đóng dấu chìm).
    Đây không phải chỗ bán hàng: anh Hùng chạy 200-300 kênh, chọn nhầm một lần
    là hàng trăm video.

    **KHÔNG DÙNG CHO DÒNG COMBO** — nó dài gấp 5 lần trần ``TRAN_NHAN`` (130).
    Dòng combo dùng ``canh_bao_gon()``; xem lý do ở đó.
    """
    lang, duong = tach_ma(ma)
    ten = (ten_hien or "").strip() or (Path(duong).stem if duong else ma)
    tieng = TIENG.get(lang, "?")
    return (f"{ten} (nhân bản, Chatterbox, tiếng {tieng}) - {GIAY_PHEP}; "
            f"{CANH_BAO_CL}; {CANH_BAO_MAY}; {DONG_DAU_CHIM}")


def canh_bao_gon() -> str:
    """Cảnh báo BẢN GỌN, vừa MỘT DÒNG COMBO. Nguồn duy nhất, đừng chép tay.

    ═══ VÌ SAO PHẢI CÓ BẢN GỌN, VÀ VÌ SAO NÓ MANG ĐÚNG BỐN CHỮ NÀY ═══
    ``nhan_giong()`` mang đủ bốn vế nhưng dài ~470 ký tự — quá trần
    ``nhan_ban_giong.TRAN_NHAN`` (130) gấp mấy lần. Mà trần đó không phải số
    cho đẹp: nhãn Kokoro 139-178 ký tự đã bị cắt **đúng chỗ cụm "cần tải"**
    trên máy anh Hùng, tức phần bị mất là phần quan trọng nhất.

    Bốn chữ trong câu này được chọn theo ĐÚNG thứ tự người dùng cần biết TRƯỚC
    khi bấm, và **ba trong bốn còn gánh việc thứ hai**: ``giong_bang._DO_TRUNG
    [CHATTER] = ("cần tải", "gpu", "mit")`` so với ``nhan.lower()``, nên nhãn
    tự nói ba điều đó thì ``duoi_dong`` **thôi dán** đuôi 60 ký tự
    *" · miễn phí (MIT), cần tải bộ 5,5 GB, cần GPU NVIDIA, KHÔNG có tiếng
    Việt"* — vừa hết nói hai lần, vừa trả lại chỗ cho vế **ĐÓNG DẤU CHÌM**,
    thứ mà đuôi kia KHÔNG hề nhắc tới. Đó là cách vế thứ tư lên được dòng
    combo mà không đụng một dòng nào của ``giong_bang.py``.

    Bỏ bất kỳ chữ nào trong ``mit`` / ``cần tải`` / ``GPU`` là đuôi cũ quay
    lại, dòng phồng lên **143 ký tự** và vế đóng dấu chìm bị đẩy ra. Cổng canh
    đúng ba chữ đó.
    """
    return (f"miễn phí (MIT), cần tải {so_gb()} GB, BẮT BUỘC GPU NVIDIA, "
            f"có ĐÓNG DẤU CHÌM")


# ---------------------------------------------------------------------------
# Chỗ để đồ — NGOÀI thư mục cài
# ---------------------------------------------------------------------------
def thu_muc_chatter() -> Path:
    """Thư mục làm việc của Chatterbox (môi trường Python, runner, hộp cát).

    ĐỌC ``config.DATA_DIR`` MỖI LẦN GỌI, không cất hằng số ở tầm module — test
    đổi ``BQ_DATA_DIR`` sau khi module đã nạp thì hằng số cũ trỏ sai chỗ (bài
    học ``tg_so.duong_so`` · ``piper_tts.thu_muc_piper`` · ``lib_demucs``).

    BẢN ĐÓNG GÓI PHẢI RA ``DATA_DIR``, KHÔNG ĐƯỢC RA CẠNH ``.exe``: lượt tự
    cập nhật đổi tên ``_internal`` -> ``_internal.old`` rồi ``rmdir /S /Q``,
    tức mọi thứ nằm trong đó bị **XOÁ SẠCH** (cổng 58 CA 5, đã xảy ra thật với
    ``_lib`` của Demucs, và triệu chứng lại là *"trước tôi nhớ báo cài rồi mà
    nay nó ghi chưa có"*).
    """
    try:
        import config
        goc = Path(getattr(config, "DATA_DIR", "") or "")
    except Exception:                                          # noqa: BLE001
        goc = Path("")
    if getattr(sys, "frozen", False):
        return (goc or Path.home()) / "_giong_chatter"
    return Path(__file__).resolve().parents[2] / "_giong_chatter"


def _ung_vien_python() -> list[Path]:
    """Python có sẵn ``chatterbox`` + torch. ``BQ_CB_PYTHON`` ép cứng."""
    ds: list[Path] = []
    ep = os.environ.get("BQ_CB_PYTHON", "").strip()
    if ep:
        ds.append(Path(ep))
    ds.append(thu_muc_chatter() / "venv" / "Scripts" / "python.exe")
    ds.append(thu_muc_chatter() / "venv" / "bin" / "python")
    return ds


#: File PHẢI có mặt cạnh python thì mới coi là "có Chatterbox". Dò bằng ĐƯỜNG
#: DẪN nên bản `.exe` (không có `.venv` để mượn) thấy ĐÚNG cái máy dev thấy.
#: `perth` nằm trong danh sách vì thiếu nó thì model chết lúc NẠP với lời báo
#: `TypeError: 'NoneType' object is not callable` — lời báo **không liên quan
#: gì tới nguyên nhân thật** (gói đóng dấu chìm cần `pkg_resources`, mà
#: `setuptools>=81` đã bỏ `pkg_resources`). Đó là lý do có cả `pkg_resources`.
_CAN_CO = (
    "chatterbox/mtl_tts.py",
    "torch/__init__.py",
    "torchaudio/__init__.py",
    "transformers/__init__.py",
    "librosa/__init__.py",
    "perth/__init__.py",
    "pkg_resources/__init__.py",
)


def _site_packages(py: Path) -> list[Path]:
    """Thư mục gói đi kèm một python — KHÔNG chạy python để hỏi."""
    goc = py.parent.parent
    return [goc / "Lib" / "site-packages", goc / "lib" / "site-packages"]


def _python_chatter() -> tuple[str, list[str]]:
    """``(python chạy được, thứ còn thiếu của ứng viên tốt nhất)``."""
    thieu_tot: Optional[list[str]] = None
    for py in _ung_vien_python():
        if not py.exists():
            continue
        for sp in _site_packages(py):
            if not sp.is_dir():
                continue
            thieu = [t.split("/")[0] for t in _CAN_CO if not (sp / t).exists()]
            if not thieu:
                return str(py), []
            if thieu_tot is None or len(thieu) < len(thieu_tot):
                thieu_tot = thieu
    return "", (thieu_tot if thieu_tot is not None
                else ["môi trường Python có chatterbox"])


def co_gpu_nvidia() -> bool:
    """Máy có GPU NVIDIA không — hỏi ``nvidia-smi``, **KHÔNG import torch**.

    Dùng lại đúng cách ``thay_giong.co_gpu_nvidia`` đã chốt ở cổng 71: import
    torch trong tiến trình đã nạp Qt là ACCESS VIOLATION, và hỏi torch cũng vô
    nghĩa (torch trong ``.venv`` có thể là bản CPU, đời nào cũng trả False).
    """
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True,
                           text=True, timeout=20, creationflags=_NO_WIN)
        return r.returncode == 0 and "GPU 0" in (r.stdout or "")
    except Exception:                                          # noqa: BLE001
        return False


def tinh_trang() -> dict:
    """``{co, thieu, python, gpu, thu_muc}``. KHÔNG import gì của model.

    ``thieu`` nói **đích danh** còn thiếu gói nào — bài học cổng 58: hộp Demucs
    phải nêu tên từng gói, ghi "chưa có" trơn là người dùng không biết bấm gì.

    ``gpu`` để RIÊNG, **không gộp vào ``thieu``**: máy không GPU vẫn CHẠY
    ĐƯỢC (0,25x), chỉ là chậm tới mức không dùng cho sản xuất. Gộp vào là nhãn
    và nút báo sai trạng thái (đúng lý do ``giong_ngoai`` tách khoá ``o_tam``).
    """
    py, thieu = _python_chatter()
    return {
        "co": bool(py),
        "thieu": thieu,
        "python": py,
        "gpu": co_gpu_nvidia(),
        "thu_muc": str(thu_muc_chatter()),
    }


def co_chatter() -> bool:
    """Có chạy được Chatterbox không. **KHÔNG BAO GIỜ NÉM.**"""
    try:
        return bool(tinh_trang()["co"])
    except Exception:                                          # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# NÚT TẢI — chỉ chạy khi NGƯỜI DÙNG BẤM
# ---------------------------------------------------------------------------
#: Bản ĐANG CHẠY ĐƯỢC trên máy này, đọc thẳng từ `_giong_chatter/venv` chứ
#: không chép từ trang giới thiệu. Ghim cả ba là **cố ý**:
#:   · `chatterbox-tts` — không ghim thì tháng sau tác giả đổi bảng ngôn ngữ
#:     là `TIENG` ở trên lệch với gói mà không một dòng báo (cùng lý do
#:     `giong_vieneu` ghim `vieneu==3.2.8`).
#:   · `torch`/`torchaudio` **2.6.0** — KHÔNG nâng bừa. Từ torchaudio 2.9 trở
#:     đi việc nạp/ghi audio đi qua `torchcodec`, mà `torchcodec` đòi FFmpeg
#:     **dạng DLL chia sẻ** còn app chỉ đóng gói `ffmpeg.exe` TĨNH — đúng chuỗi
#:     lỗi 4 bước `giong_vieneu.ban_cuda_se_tai()` đã truy ra trên máy anh Hùng.
#:     2.6.0 nằm TRƯỚC mốc đó và là bản đang chạy được, đo tại chỗ.
GOI_CB = ("chatterbox-tts==0.1.7", "resemble-perth==1.0.1")
GOI_TORCH = ("torch==2.6.0+cu124", "torchaudio==2.6.0+cu124")

#: `perth` (gói đóng dấu chìm) nạp qua `pkg_resources`, mà **setuptools >= 81
#: đã BỎ `pkg_resources`**. Thiếu nó thì model chết lúc NẠP với lời báo
#: `TypeError: 'NoneType' object is not callable` — **không liên quan gì tới
#: nguyên nhân thật**. Ghim dưới 81 để lời lỗi đó không bao giờ xuất hiện.
GOI_SETUPTOOLS = "setuptools<81"

#: Chỉ mục wheel CUDA. **ĐƯỜNG NÀY CỐ Ý NGƯỢC VỚI `giong_vieneu`** (bên đó
#: LUÔN lấy bản CPU): ở đây GPU là **điều kiện tồn tại** của tính năng chứ
#: không phải "cho nhanh" — CPU đo **0,25x** thời gian thật. Tải bản CPU cho
#: bộ này là tải 2 GB về để dùng một thứ không dùng được.
CHI_MUC_TORCH_CU124 = "https://download.pytorch.org/whl/cu124"


def _python_he_thong() -> str:
    """Python 3 trên máy để DỰNG môi trường. "" = không có.

    KHÔNG dùng ``sys.executable``: ở bản ``.exe`` đó là chính
    ``BQHungVideo.exe``, gọi ``-m venv`` vào nó là vô nghĩa (đúng cách
    ``giong_vieneu._python_he_thong`` và ``piper_tts._python_chay`` đã làm).
    """
    if not getattr(sys, "frozen", False):
        ex = Path(sys.executable)
        if ex.exists() and ex.name.lower().startswith("python"):
            return str(ex)
    import shutil as _sh
    for ten in ("py", "python", "python3"):
        p = _sh.which(ten)
        if p:
            return p
    return ""


def vi_sao_khong_cai() -> str:
    """"" = tải được. Khác rỗng = **LÝ DO**, để nút xám còn nói được vì sao.

    Nút xám KHÔNG MỘT LỜI là câu đố (bài học cổng 58/16/51). Ở đây có tới HAI
    lý do có thật, và chúng **khác hẳn nhau**:
      · không có Python 3 -> chưa dựng nổi môi trường (sửa được: cài Python);
      · **không có GPU NVIDIA** -> dựng xong cũng vô nghĩa, vì CPU đo 0,25x =
        1 phút tiếng tốn 4 phút máy. Đây là chốt 2: tải 5,59 GB cho một thứ
        chắc chắn không dùng được là lừa người dùng một cách lịch sự.
    """
    if not _python_he_thong():
        return ("Máy này không có Python 3 nên app không tự tải được bộ "
                "Chatterbox: cài Python 3 (python.org) rồi bấm lại, hoặc copy "
                "thư mục _giong_chatter từ máy đã cài sang.")
    if not co_gpu_nvidia():
        return ("Máy này KHÔNG có GPU NVIDIA. Chatterbox chạy trên CPU đo được "
                "0,25 lần thời gian thật (1 phút tiếng tốn 4 phút máy) nên "
                "không dùng cho sản xuất được - app không mời anh tải "
                f"{so_gb()} GB cho một thứ chắc chắn không dùng được. Giọng "
                "nhân bản TIẾNG VIỆT (VieNeu) không cần GPU, vẫn dùng bình "
                "thường.")
    return ""


def nhan_tai(thieu: Optional[list] = None) -> str:
    """Nhãn nút tải. Đang cài dở -> nói *"cài tiếp"* thay vì *"tải"*.

    **NÚT BÁM ``thieu``, KHÔNG BÁM ``co``** — bám ``co`` thì trên máy dev (đã
    có ``_giong_chatter/venv``) nút **BIẾN MẤT**, không ai bấm thử, rồi bản
    ``.exe`` trên máy nhân viên trắng **mãi mãi không có đường tải**. Đã sập
    hai lần (cổng 58 ``_lib``, rồi hàng Kokoro).

    Con số đi qua ``so_gb()`` — một phép đo, ba chỗ đọc.
    """
    t = list(thieu or [])
    if t and len(t) < len(_CAN_CO):
        return f"Cài tiếp phần còn thiếu ({', '.join(t[:3])})"
    return NHAN_TAI


def _chay_lenh(cmd: list, han: int) -> tuple[int, str]:
    """Chạy một lệnh, trả ``(mã thoát, đuôi log)``. KHÔNG BAO GIỜ NÉM."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=han,
                           creationflags=_NO_WIN)
        return r.returncode, ((r.stdout or "") + (r.stderr or ""))[-2000:]
    except Exception as e:                                     # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def cai_chatter(on_progress: Optional[Callable[[float, str], None]] = None,
                han_giay: int = 7200, da_dong_y: bool = False) -> dict:
    """Dựng môi trường Chatterbox ở ``thu_muc_chatter()/venv``. CHỈ khi BẤM.

    Trả ``{"ok", "loi", "tinh_trang"}``. **KHÔNG BAO GIỜ NÉM.**

    ═══ MÔI TRƯỜNG RIÊNG, KHÔNG `pip install` VÀO `.venv` ĐANG CHẠY ═══
    Một lượt cài kéo theo torch/numpy khác bản có thể phá app đang chạy 300
    kênh — đúng lý do Demucs phải ở ``_lib`` (cổng 55) và VieNeu phải có venv
    riêng (cổng 58). Venv riêng còn làm phép dò ``_python_chatter`` nói THẬT:
    nó dò bằng **FILE CÓ TỒN TẠI KHÔNG**, không mượn được gói của ai.

    ``--ignore-installed``: ép mọi gói nằm THẬT trong venv đích. pip đời cũ bỏ
    qua gói "đã có" rồi báo xong, và đó chính là cách ``_lib`` của Demucs nằm
    thiếu torch suốt một tháng mà máy dev vẫn xanh (cổng 58).

    ``da_dong_y`` để nơi gọi nói *"người dùng đã đồng ý ở hộp trước rồi"* khi
    đây là bước 2 của một chuỗi — cùng khuôn ``giong_vieneu.cai_nhan_ban``.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(p, m)
            except Exception:                                  # noqa: BLE001
                pass

    vi_sao = vi_sao_khong_cai()
    if vi_sao and not (da_dong_y and _python_he_thong()):
        return {"ok": False, "loi": vi_sao}
    py = _python_he_thong()
    if not py:
        return {"ok": False, "loi": vi_sao or "Máy này không có Python 3."}

    d = thu_muc_chatter()
    venv = d / "venv"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "loi": f"Không tạo được thư mục {d}: {e}"}

    vpy = venv / "Scripts" / "python.exe"
    if not vpy.exists():
        vpy = venv / "bin" / "python"
    if not vpy.exists():
        prog(0.03, "Đang dựng môi trường Python riêng...")
        ma, log = _chay_lenh([py, "-m", "venv", str(venv)], 900)
        if ma != 0:
            return {"ok": False, "loi": f"Dựng môi trường hỏng: {log[-500:]}"}
        vpy = venv / "Scripts" / "python.exe"
        if not vpy.exists():
            vpy = venv / "bin" / "python"
    if not vpy.exists():
        return {"ok": False, "loi": f"Dựng xong mà không thấy python ở {venv}"}

    nen = [str(vpy), "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--ignore-installed"]

    # TORCH TRƯỚC, và từ chỉ mục CUDA. Cài sau `chatterbox-tts` thì gói đó đã
    # kéo về bản torch mặc định (KHÔNG CUDA) từ PyPI, rồi lượt sau phải gỡ ra
    # cài lại — tải hai lần cùng một thứ 2,5 GB.
    prog(0.05, f"Đang tải torch bản CUDA (phần nặng nhất của {so_gb()} GB)...")
    ma, log = _chay_lenh(
        nen + ["--extra-index-url", CHI_MUC_TORCH_CU124] + list(GOI_TORCH),
        han_giay)
    if ma != 0:
        _ghi_log(f"cài torch CUDA hỏng: {log[-300:]}")
        return {"ok": False, "loi": log[-800:]}

    prog(0.70, "Đang tải Chatterbox...")
    ma, log = _chay_lenh(nen + list(GOI_CB) + [GOI_SETUPTOOLS], han_giay)
    if ma != 0:
        _ghi_log(f"cài Chatterbox hỏng: {log[-300:]}")
        return {"ok": False, "loi": log[-800:]}

    # HẬU KIỂM bằng CHÍNH phép dò của bản `.exe` — **không tin lời pip báo**.
    # pip từng báo xong trong khi thư mục đích vẫn thiếu gói, và máy dev không
    # thấy vì nó mượn được của `.venv` (cổng 58).
    prog(0.95, "Đang kiểm lại...")
    tt = tinh_trang()
    if tt["thieu"]:
        return {"ok": False, "tinh_trang": tt,
                "loi": f"Cài xong nhưng vẫn thiếu: {', '.join(tt['thieu'])}"}
    _ghi_log(f"Cài Chatterbox XONG vào {venv}")
    prog(1.0, "Đã cài xong bộ nhân bản giọng Chatterbox.")
    return {"ok": True, "loi": "", "tinh_trang": tt}


def _ghi_log(dong: str) -> None:
    """Ghi ``logs/giong_chatter_<ngày>.log``. KHÔNG BAO GIỜ NÉM.

    Lùi êm mà không ghi lý do thì người dùng chọn giọng X nghe ra giọng Y và
    **không có đường nào truy** — đúng ca ``ov:nu_am`` chết âm thầm.
    """
    try:
        import config
        d = Path(config.DATA_DIR) / "logs"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"giong_chatter_{time.strftime('%Y%m%d')}.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {dong}\n")
    except Exception:                                          # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# CHỐT 1 — ĐỌC LOẠN NHỊP: CẮT KHOẢNG LẶNG **GIỮA CÂU**
# ---------------------------------------------------------------------------
# ĐO ĐƯỢC, KHÔNG PHẢI PHÒNG XA: một bộ câu Chatterbox đọc hết **54,9 giây**
# trong khi trần bản ngữ (cùng chữ, edge-tts) chỉ **30,4 giây** = **1,81 lần**;
# câu tệ nhất **3,5 lần**. Mà WER chỉ 1,5-4,4% -> nó **đọc ĐÚNG CHỮ, SAI
# NHỊP**: chỗ dôi ra là những khoảng lặng **1,12-1,22 giây nằm GIỮA CÂU**.
#
# VÌ SAO KHÔNG CÓ SẴN ĐƯỜNG NÀO CHỮA (đọc trước khi định "dùng lại hàm cũ"):
#   · `thay_giong.cat_le_loat` chỉ cắt lề **HAI ĐẦU** — lặng giữa câu nó không
#     với tới. Đo trên chính bộ file này: cắt lề xong vẫn còn nguyên phần dôi.
#   · bước 4c `thay_giong.doc_nhanh_vua_khung` đọc LẠI câu bằng tham số `rate`
#     của máy đọc. **Chatterbox KHÔNG CÓ tham số `rate`** (không `speed`, không
#     `duration`) nên bước đó **không chạy được** — y hệt ca ElevenLabs Adam đã
#     ghi ở cổng 67. Toàn bộ phần dôi vì thế dồn hết sang `atempo` ở bước 5 và
#     **chạm trần `TEMPO_TOI_DA` = 1,50**, tức nghe méo.
#
# NÊN CHỖ CHỮA PHẢI NẰM Ở ĐÂY, TRONG CỬA ĐỌC CỦA CHÍNH NÓ, và đó cũng là chỗ
# ĐÚNG theo hai lẽ:
#   1. đây là tật của RIÊNG Chatterbox — vá ở `thay_giong` là bắt mọi máy đọc
#      khác trả giá cho một bệnh không phải của chúng;
#   2. **thứ tự đúng theo cấu tạo**: `doc_loat` ghi ra `paths[i]`, rồi
#      `dubbing._synth_all_words` mới gọi `_moc_giong_hang(texts, paths, ...)`.
#      Tức mốc từng chữ được dựng **SAU** khi đã cắt, trên chính file đã cắt ->
#      **không có đường nào cho mốc lệch**. Cắt ở tầng trên (sau khi đã có mốc)
#      thì phải tự dời từng mốc, và đó đúng là chỗ v2.28.0 đã lệch một lần.
#
# **KHÔNG BAO GIỜ LÀM TỆ ĐI**: mọi nhánh hỏng đều GIỮ NGUYÊN file gốc. Cắt
# hỏng một câu còn tệ hơn để nó dài — dài thì `atempo` còn gỡ được, còn cắt
# nhầm vào tiếng nói là mất chữ, mà mất chữ thì không ai gỡ lại được.

#: Ngưỡng coi là "im" khi dò. Cùng con số `thay_giong.NGUONG_IM_DB` dùng cho
#: lề hai đầu — hai ngưỡng khác nhau trên cùng một file là hai kết luận khác
#: nhau về cùng một khoảng lặng.
NGUONG_LANG_DB = -40.0

#: Khoảng lặng GIỮA CÂU dài hơn mức này mới bị cắt. Đặt **0,35** chứ không
#: thấp hơn là có lý do: nghỉ ở dấu phẩy của chính Chatterbox đo được
#: **0,10-0,14 giây** (cùng bậc với Piper), nên 0,35 nằm hẳn ngoài vùng nhịp
#: TỰ NHIÊN và chỉ chạm vào phần chết. Hạ xuống 0,20 là đi cắt dấu phẩy —
#: nghe dồn chữ, và đó là đổi một tật lấy một tật.
LANG_GIUA_CAT_TU = 0.35

#: ...và cắt xuống còn ĐÚNG mức này (giây), chừa đều hai bên. Không cắt sạch
#: về 0: hai câu dính liền nghe như nói hụt hơi (cùng lý do
#: `thay_giong.CHUA_TRUOC_CAU_KE` chừa 0,12 giây khi mượn khoảng lặng).
LANG_GIUA_GIU = 0.20

#: **LƯỚI AN TOÀN — cắt xong mà file còn dưới tỉ lệ này của bản gốc thì VỨT
#: BẢN CẮT, giữ nguyên file cũ.** Bộ dò lặng có thể hiểu nhầm cả một đoạn nói
#: nhỏ là "im" (giọng thều thào, mẫu thu xa micro); lúc đó bản "đã chữa" là
#: một file mất chữ mà `rc` vẫn 0 và độ dài vẫn hợp lý — đúng họ bẫy *"phép đo
#: hỏng phát chứng nhận"*. Ngưỡng 0,45 chừa chỗ cho ca 3,5 lần (cắt hợp lệ
#: nhiều nhất đo được là còn 0,52 bản gốc) mà vẫn chặn được ca hiểu nhầm.
LANG_GIUA_CON_TOI_THIEU = 0.45


def _ffmpeg() -> str:
    """Đường ffmpeg app THẬT SỰ chạy.

    Đọc `config.settings.FFMPEG_PATH` MỖI LẦN GỌI, **KHÔNG ghi cứng
    `bin/ffmpeg.exe`**: bản trong `bin/` đã từng là build 2023 trong khi app
    chạy bản trên PATH, và 21 file `_test_*.py` ghi cứng nó đang đo một ffmpeg
    KHÁC ffmpeg sản xuất (bài học cổng 86).
    """
    try:
        from config import settings
        return str(getattr(settings, "FFMPEG_PATH", "") or "ffmpeg")
    except Exception:                                          # noqa: BLE001
        return "ffmpeg"


def _do_lang(p: Path) -> tuple[float, list[tuple[float, float]]]:
    """``(độ dài, [(bắt đầu, kết thúc)] mọi khoảng im)`` — MỘT lượt ffmpeg.

    Độ dài lấy từ mốc ``time=`` LỚN NHẤT chứ không phải dòng cuối: ffmpeg in
    nhiều dòng tiến trình và dòng cuối không bảo đảm là dòng lớn nhất.

    Khoảng im còn HỞ ĐUÔI là chuyện bình thường (``silence_start`` có mà
    ``silence_end`` không, khi file kết thúc trong lúc đang im) -> đóng nó
    bằng chính độ dài file. Bỏ qua ca đó là bỏ sót khoảng im CUỐI, tuy ở đây
    không dùng tới nhưng để hàm nói đúng cái nó hứa.
    """
    r = subprocess.run(
        [_ffmpeg(), "-v", "info", "-i", str(p), "-af",
         f"silencedetect=noise={NGUONG_LANG_DB}dB:d={LANG_GIUA_CAT_TU:.3f}",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=300)
    txt = (r.stderr or "") + (r.stdout or "")
    if r.returncode != 0:
        return 0.0, []
    import re as _re
    dai = 0.0
    for m in _re.finditer(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", txt):
        dai = max(dai, int(m.group(1)) * 3600 + int(m.group(2)) * 60
                  + float(m.group(3)))
    ra: list[tuple[float, float]] = []
    dang: Optional[float] = None
    for m in _re.finditer(r"silence_(start|end):\s*(-?\d+(?:\.\d+)?)", txt):
        if m.group(1) == "start":
            dang = float(m.group(2))
        elif dang is not None:
            ra.append((dang, float(m.group(2))))
            dang = None
    if dang is not None and dai > dang:
        ra.append((dang, dai))
    return dai, ra


def khoang_lang_giua(p: Path) -> tuple[float, list[tuple[float, float]]]:
    """``(độ dài, khoảng lặng NẰM GIỮA đáng cắt)``. KHÔNG BAO GIỜ NÉM.

    **Cố ý CHỪA lề hai đầu ra**: đó là việc của ``thay_giong.cat_le_loat``, và
    hàm đó còn phải DỜI MỐC TỪNG CHỮ theo đúng số giây nó cắt ở đầu. Cắt lề ở
    đây nữa là làm hai lần một việc, mà lần này thì không ai dời mốc.
    """
    try:
        dai, ds = _do_lang(p)
        if dai <= 0:
            return 0.0, []
        me = 0.02
        return dai, [(a, b) for a, b in ds
                     if a > me and b < dai - me
                     and (b - a) > LANG_GIUA_CAT_TU]
    except Exception:                                          # noqa: BLE001
        return 0.0, []


#: Dưới ngần này ký tự thì coi là "câu ngắn" — vùng Chatterbox đọc lan man.
#: Đo được: câu 5 và 16 ký tự đều vượt nhịp (10,80x · 1,75x · 1,55x · 1,25x),
#: còn câu 55-180 ký tự thì 0,80-1,18x. 24 nằm giữa hai nhóm.
LAN_MAN_CHU_TOI_DA = 24

#: Ước tốc độ đọc bình thường (ký tự/giây) để biết "bao lâu là hợp lý".
#: Lấy từ chính bảng trần của lượt đo: 26 câu, tổng 613 ký tự / 101,6 giây
#: edge-tts -> ~6,0 ký tự/giây, làm tròn XUỐNG cho rộng tay.
LAN_MAN_CHU_MOI_GIAY = 6.0

#: Vượt ngần này lần so với ước lượng thì KÊU. 3,0 nằm dưới ca thật (10,8x)
#: rất xa mà vẫn trên mọi câu đọc bình thường đo được (cao nhất 1,18x).
LAN_MAN_LAN = 3.0


def nghi_doc_lan(text: str, giay: float) -> float:
    """Câu này có bị đọc LAN MAN không -> trả **số lần** vượt (0 = không).

    Hàm THUẦN, KHÔNG chữa được gì — và đó là chủ ý. Nó tồn tại để tật này
    **không hỏng âm thầm**: `doc_loat` ghi log mỗi ca, nên khi anh Hùng thấy
    một câu bị ép nhanh tới méo thì có đường truy ra *"câu 5 ký tự mà máy đọc
    7,15 giây"* thay vì đoán mò.

    **VÌ SAO KHÔNG TỰ VỨT CÂU ĐÓ ĐI:** `doc_loat` là all-or-nothing, đánh
    trượt một câu là **cả loạt** lùi về edge-tts — tức một chữ *"Okay."* trong
    kịch bản làm cả video mất giọng nhân bản. Đổi một tật nhỏ lấy một tật to.

    **PHÉP TÍNH NẰM Ở `doc_lan.lan_vuot`, KHÔNG CHÉP LẠI Ở ĐÂY.** `giong_vieneu`
    cần đúng phép tính này (chỉ khác MỐC so sánh: nó khớp mốc từ chính loạt
    đang đọc thay vì dùng hằng số), nên hai bên đi chung một hàm — hai bản sao
    là hai chỗ để lệch nhau. Ở đây mốc là hằng số `a=0 · b=1/6,0` giây/ký tự,
    và **CHÍNH SÁCH** riêng của bộ này là chỉ soi câu NGẮN (xem
    `LAN_MAN_CHU_TOI_DA`) — đó là chỗ đo được tật, câu 55-180 ký tự thì
    0,80-1,18x nên soi vào là kêu oan.
    """
    try:
        n = len(str(text or "").strip())
        if n <= 0 or n > LAN_MAN_CHU_TOI_DA or giay <= 0:
            return 0.0
        lan = doc_lan.lan_vuot(text, giay, 0.0, 1.0 / LAN_MAN_CHU_MOI_GIAY)
        return lan if lan > LAN_MAN_LAN else 0.0
    except (TypeError, ValueError):
        return 0.0


def cat_lang_giua(nguon: Path, dich: Path) -> dict:
    """Cắt bớt khoảng lặng GIỮA CÂU của một file. **KHÔNG BAO GIỜ NÉM.**

    Trả ``{"ok", "giay_truoc", "giay_sau", "so_khoang", "giay_cat", "ly_do"}``.
    ``ok=False`` nghĩa là **giữ nguyên ``nguon``** — nơi gọi phải đọc cờ đó,
    đừng cứ thế dùng ``dich``.
    """
    ra = {"ok": False, "giay_truoc": 0.0, "giay_sau": 0.0, "so_khoang": 0,
          "giay_cat": 0.0, "ly_do": ""}
    try:
        dai, ds = khoang_lang_giua(nguon)
        ra["giay_truoc"] = round(dai, 3)
        ra["so_khoang"] = len(ds)
        if dai <= 0:
            ra["ly_do"] = "không đo được độ dài"
            return ra
        if not ds:
            ra["ly_do"] = "không có khoảng lặng giữa câu nào đáng cắt"
            return ra
        giu = LANG_GIUA_GIU / 2.0
        doan: list[tuple[float, float]] = []
        truoc = 0.0
        for a, b in ds:
            x, y = a + giu, b - giu
            if y <= x:
                continue
            doan.append((truoc, x))
            truoc = y
        doan.append((truoc, dai))
        doan = [(a, b) for a, b in doan if b - a > 0.01]
        if len(doan) < 2:
            ra["ly_do"] = "không còn đoạn nào để nối"
            return ra
        loc = []
        for i, (a, b) in enumerate(doan):
            loc.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},"
                       f"asetpts=N/SR/TB[c{i}]")
        loc.append("".join(f"[c{i}]" for i in range(len(doan)))
                   + f"concat=n={len(doan)}:v=0:a=1[o]")
        r = subprocess.run(
            [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(nguon), "-filter_complex", ";".join(loc),
             "-map", "[o]", "-c:a", "pcm_s16le", str(dich)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            creationflags=_NO_WIN, timeout=600)
        # ffmpeg TRẢ MÃ 0 MÀ FILE RỖNG là chuyện đã xảy ra nhiều lần trong repo
        # này -> kiểm KÍCH THƯỚC rồi ĐỘ DÀI, đừng tin mã thoát.
        if r.returncode != 0 or not dich.exists() or dich.stat().st_size < 1024:
            ra["ly_do"] = f"ffmpeg hỏng (mã {r.returncode})"
            return ra
        sau, _ = _do_lang(dich)
        ra["giay_sau"] = round(sau, 3)
        if sau <= 0.02:
            ra["ly_do"] = "file cắt ra rỗng"
            return ra
        # LƯỚI AN TOÀN — xem `LANG_GIUA_CON_TOI_THIEU`.
        if sau < dai * LANG_GIUA_CON_TOI_THIEU:
            ra["ly_do"] = (f"cắt quá tay ({sau:.2f}/{dai:.2f} giây) -> GIỮ bản "
                           f"gốc")
            return ra
        ra["ok"] = True
        ra["giay_cat"] = round(max(0.0, dai - sau), 3)
        return ra
    except Exception as e:                                     # noqa: BLE001
        ra["ly_do"] = f"{type(e).__name__}: {e}"
        return ra


# ---------------------------------------------------------------------------
# Tiến trình con — SCRIPT ĐỘC LẬP, không `-m <module>`
# ---------------------------------------------------------------------------
#: Không dùng `-m app.core...`: bản `.exe` không chạy được và không có cây mã
#: nguồn để `-m` bám vào (bài học cổng 55). Việc và kết quả đi qua FILE JSON
#: chứ không qua dòng lệnh — chữ Việt/Trung/Nhật trên dòng lệnh Windows là một
#: đường vỡ bảng mã không cần thiết.
_MA_DOC = '''
import json, os, sys, time

with open(sys.argv[1], "r", encoding="utf-8") as f:
    J = json.load(f)


def bao(p, m):
    sys.stdout.write("BQP\\t%.4f\\t%s\\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model Chatterbox...")
    import torch, torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    t0 = time.time()
    dung_gpu = torch.cuda.is_available()
    dev = "cuda" if dung_gpu else "cpu"
    m = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    t_nap = time.time() - t0

    items = J["items"]
    ref = J.get("ref") or ""
    lang = J.get("lang") or "en"
    # ‼ MAU THAM CHIEU LA BAT BUOC — DAY LA CHOT CHONG "KENH B RA GIONG KENH A".
    # `ChatterboxMultilingualTTS` CAT mau len chinh doi tuong model (`self.
    # conds`). Goi `generate()` KHONG kem `audio_prompt_path` thi no **dung lai
    # mau cua luot TRUOC**, chu KHONG quay ve giong mac dinh — va no khong nem
    # loi, khong bao mot dong nao. Doc kenh A roi kenh B ma quen truyen mau la
    # kenh B ra GIONG KENH A. Voi 300 kenh day la loi chet nguoi.
    # Vi vay: thieu `ref` thi **NEM NGAY**, khong doc mot cau nao. Doc bang mot
    # giong khong xac dinh con te hon khong doc: nguoi dung nhan duoc file
    # nghe duoc, tuong da xong.
    if not ref:
        raise ValueError(
            "thieu audio_prompt_path (mau tham chieu): Chatterbox se dung lai "
            "mau cua luot truoc -> kenh nay ra giong kenh khac")
    # DONG SEED: khong dong thi cung cau cung tham so lech do dai 33,7% giua
    # cac luot (do that, 8 luot). Dong seed -> 0,0%. Day khong phai lam dep
    # so: `khop_thoi_gian` o tien trinh cha can do dai TIEN DINH thi vong ep
    # khung moi hoi tu.
    seed = int(J.get("seed", 1234))
    ra = []
    t1 = time.time()
    for i, it in enumerate(items):
        torch.manual_seed(seed)
        # `audio_prompt_path` truyen VO DIEU KIEN o MOI cau — khong `if`,
        # khong `**kw`. Mot cau lot la cau do mang giong cua lan goi truoc.
        wav = m.generate(it["text"], language_id=lang,
                         audio_prompt_path=ref)
        x = wav.detach().cpu()
        if x.dim() == 1:
            x = x[None]
        ta.save(it["raw"], x, m.sr)
        ra.append({"i": it["i"], "p": it["raw"],
                   "giay": round(x.shape[-1] / float(m.sr), 4)})
        bao(0.20 + 0.75 * (i + 1) / max(1, len(items)),
            "Doc cau %d/%d (%s)" % (i + 1, len(items), dev))
    ket = {"ok": True, "nap": round(t_nap, 2),
           "gen": round(time.time() - t1, 2), "dev": dev, "sr": int(m.sr),
           "ra": ra, "torch": getattr(torch, "__version__", "?"),
           "vram": (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                    if dung_gpu else 0.0)}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\\t" + json.dumps(ket) + "\\n")
sys.stdout.flush()
'''


def _viet_runner() -> Path:
    """Ghi script chạy ra ``<thu_muc_chatter>/_bq_cb_runner.py`` (đè mỗi lượt)."""
    p = thu_muc_chatter() / "_bq_cb_runner.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_MA_DOC, encoding="utf-8")
    return p


def _chay(items: list[dict], ref: str, lang: str, py: str, han_giay: int,
          on_msg: Optional[Callable[[str], None]]) -> dict:
    """Gọi tiến trình con đọc cả loạt. Trả dict (KHÔNG NÉM).

    **``_sandbox`` có ở MỌI đường ra** — kể cả nhánh quá giờ và nhánh ném.
    Thiếu nó là nơi gọi làm ``don_thu_muc("")`` -> ``Path("")`` -> thư mục
    đang làm việc. Đây đúng chỗ ``_chay_ov`` từng hở và đã xoá sạch cây mã.
    """
    runner = _viet_runner()
    sb = (thu_muc_chatter()
          / f"_job_{os.getpid()}_{int(time.time() * 1000) % 100000}")
    sb.mkdir(parents=True, exist_ok=True)
    job = sb / "job.json"
    job.write_text(json.dumps({"items": items, "ref": ref, "lang": lang},
                              ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    def _ra(d: dict) -> dict:
        """Đóng dấu ``_sandbox`` rồi mới trả. **MỌI đường ra đi qua đây.**

        Bản đầu đặt ``_sandbox`` ở từng nhánh, và nhánh THÀNH CÔNG thì gán ở
        dòng trước ``return ket`` — an toàn, nhưng **không kiểm bằng máy
        được**, nên bản vá sau xoá đi cũng không ai thấy. Cổng 81 CA 6d đòi
        mọi ``return`` phải gọi ``_ra``: một hàm, một chỗ để hỏng, một chỗ để
        canh.
        """
        d["_sandbox"] = str(sb)
        return d

    ket: dict = {}
    duoi: list[str] = []
    ma: Optional[int] = None
    p = None
    try:
        p = subprocess.Popen(
            [py, "-u", str(runner), str(job)], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1, env=env, creationflags=_NO_WIN)
        _gan_job(p)
        han = time.time() + han_giay
        for dong in p.stdout or ():
            dong = dong.rstrip("\n")
            if dong.startswith("BQP\t"):
                phan = dong.split("\t", 2)
                if on_msg and len(phan) > 2:
                    try:
                        on_msg(phan[2])
                    except Exception:                          # noqa: BLE001
                        pass
                continue
            if dong.startswith("BQJSON\t"):
                try:
                    ket = json.loads(dong.split("\t", 1)[1])
                except ValueError:
                    ket = {}
                continue
            if dong.strip():
                duoi.append(dong[-300:])
            if time.time() > han:
                p.kill()
                return _ra({"ok": False, "loi": "quá giờ (bỏ cuộc)"})
        ma = p.wait(timeout=120)
    except Exception as e:                                     # noqa: BLE001
        return _ra({"ok": False, "loi": f"{type(e).__name__}: {e}"})
    finally:
        if p is not None:
            _bo_gan_job(p)
    if not ket:
        ket = {"ok": False,
               "loi": f"mã thoát {ma}: " + (" | ".join(duoi[-4:]) or "không rõ")}
    return _ra(ket)


def _gan_job(p) -> None:
    """Đăng ký tiến trình con để bấm Huỷ GIẾT ĐƯỢC nó (như Demucs).

    KHÔNG BAO GIỜ NÉM: module điều phối có thể chưa nạp (cổng test, đo đạc).
    """
    try:
        from app.queue.worker import register_job_proc
        register_job_proc(p)
    except Exception:                                          # noqa: BLE001
        pass


def _bo_gan_job(p) -> None:
    try:
        from app.queue.worker import unregister_job_proc
        unregister_job_proc(p)
    except Exception:                                          # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Cửa đọc — cùng hợp đồng `dubbing._synth_all`
# ---------------------------------------------------------------------------
def doc_loat(texts: list[str], paths: list[str], voice: str,
             rate: str | list = "+0%", han_giay: int = 3600,
             on_msg: Optional[Callable[[str], None]] = None) -> list[bool]:
    """Đọc cả LOẠT câu bằng giọng nhân bản Chatterbox.

    Trả ``ok[i]`` — cùng hợp đồng ``dubbing._synth_all``.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả toàn ``False`` để nơi gọi lùi êm về
    edge-tts (cùng luật Piper/OmniVoice: ở đây lùi ra video ĐÚNG, chỉ khác
    giọng — khác Demucs, thiếu Demucs mà lùi là ra video HỎNG nên phải CHẶN).

    **ĐƯỢC ĂN CẢ NGÃ VỀ EDGE — all-or-nothing.** Đọc được 18/20 câu rồi để 2
    câu kia lùi edge-tts thì video ra **LẪN HAI GIỌNG** giữa chừng, mà mã
    thoát vẫn 0 nên không ai biết (mệnh đề cổng 63).
    """
    n = len(texts or [])
    xau = [False] * n
    if n == 0 or len(paths or []) != n:
        return xau
    lang, ref = tach_ma(voice)
    if not lang or not ref:
        _ghi_log(f"mã giọng sai dạng «{voice}» -> lùi edge-tts")
        return xau
    if not Path(ref).exists():
        _ghi_log(f"MẤT FILE MẪU «{ref}» -> lùi edge-tts")
        return xau
    tt = tinh_trang()
    if not tt["co"]:
        _ghi_log(f"chưa cài Chatterbox (thiếu: {', '.join(tt['thieu'])})"
                 f" -> lùi edge-tts")
        return xau

    sb = ""
    try:
        items = [{"i": i, "text": str(texts[i] or ""),
                  "raw": str(Path(paths[i]).with_suffix(".cb.wav"))}
                 for i in range(n)]
        ket = _chay(items, ref, lang, tt["python"], han_giay, on_msg)
        sb = str(ket.get("_sandbox") or "")
        if not ket.get("ok"):
            _ghi_log(f"đọc hỏng: {ket.get('loi')} -> lùi edge-tts")
            return xau
        from app.core import giong_ngoai as _gn
        tempo = _gn._tempo_tu_rate(rate if isinstance(rate, str) else "+0%")
        # CHỐT 1 — cắt lặng GIỮA CÂU **TRƯỚC** khi ép khung. Thứ tự là cả bản
        # vá: cắt trước thì `_ep_khung` (và `khop_thoi_gian` ở tầng trên) nhìn
        # thấy một độ dài đã gọn, nên phần phải nhờ `atempo` ít đi đúng bằng
        # phần vừa cắt. Cắt SAU là ép méo rồi mới bỏ đi chỗ trống — trả tiền
        # cho một quãng im.
        # `BQ_CB_CAT_LANG=0` tắt hẳn để đo A/B, KHÔNG phải để dùng.
        bat_cat = os.environ.get("BQ_CB_CAT_LANG", "1").strip() != "0"
        cat_tong, cat_so, cat_cau = 0.0, 0, 0
        for r in ket.get("ra", []):
            i = int(r.get("i", -1))
            if not (0 <= i < n):
                continue
            raw = Path(r.get("p") or "")
            if not (raw.exists() and raw.stat().st_size > 1000):
                continue
            gon = raw.with_suffix(".gon.wav")
            if bat_cat:
                kq = cat_lang_giua(raw, gon)
                if kq.get("ok"):
                    raw = gon
                    cat_tong += float(kq.get("giay_cat") or 0.0)
                    cat_so += int(kq.get("so_khoang") or 0)
                    cat_cau += 1
                # ĐỌC LAN MAN: cắt lặng KHÔNG chữa được (phần dôi là tiếng
                # nói thật, máy tự bịa thêm). Chỉ ghi log — xem `nghi_doc_lan`.
                lan = nghi_doc_lan(
                    texts[i], float(kq.get("giay_sau") or kq.get("giay_truoc")
                                    or 0.0))
                if lan:
                    _ghi_log(f"câu {i} chỉ {len(str(texts[i] or '').strip())} "
                             f"ký tự mà đọc {lan:.1f} lần lâu hơn mức thường "
                             f"-> câu này sẽ bị ép nhanh (méo tiếng). Câu quá "
                             f"ngắn là chỗ Chatterbox đọc lan man.")
            # Ép vừa khung bằng `rubberband` — KHÔNG dùng núm của model
            # (Chatterbox **không có** `rate`/`speed`/`duration`, nên bước 4c
            # `doc_nhanh_vua_khung` không chạy được với bộ này), và `_ep_khung`
            # tự lùi `atempo` khi ffmpeg máy đó thiếu rubberband.
            xau[i] = bool(_gn._ep_khung(raw, Path(paths[i]), tempo))
            try:
                if gon.exists():
                    gon.unlink()
            except OSError:
                pass
        if cat_cau:
            _ghi_log(f"cắt lặng GIỮA CÂU: {cat_cau}/{n} câu · {cat_so} khoảng "
                     f"· bỏ {cat_tong:.2f} giây chết")
        if not all(xau):
            _ghi_log(f"chỉ đọc được {sum(xau)}/{n} câu -> BỎ CẢ LOẠT "
                     f"(all-or-nothing) -> lùi edge-tts")
            return [False] * n
        return xau
    except Exception as e:                                     # noqa: BLE001
        _ghi_log(f"lỗi lạ: {type(e).__name__}: {e} -> lùi edge-tts")
        return [False] * n
    finally:
        # CỬA CHUNG, không tự viết `rmtree`: `xoa_an_toan` chặn `Path("")`,
        # thư mục cha, gốc ổ đĩa. Và `trong=` là lớp chắn THỨ HAI.
        try:
            from app.core import xoa_an_toan
            xoa_an_toan.don_thu_muc(sb, trong=thu_muc_chatter())
        except Exception:                                      # noqa: BLE001
            pass
