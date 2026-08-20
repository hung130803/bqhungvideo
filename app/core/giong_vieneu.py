# -*- coding: utf-8 -*-
"""VieNeu-TTS — giọng Việt BẢN ĐỊA chạy trên máy. LỰA CHỌN THÊM, KHÔNG THAY THẾ.

═══════════════════════════════════════════════════════════════════════════
NÓ LÀ GÌ, VÀ VÌ SAO NÓ KHÁC 3 BỘ TRƯỚC
═══════════════════════════════════════════════════════════════════════════
`github.com/pnnbao97/VieNeu-TTS` · pip `vieneu` · **Apache-2.0** (kiểm ở
`_kq_vieneu_whl/x/vieneu-3.2.8.dist-info/METADATA`, không đọc bài giới thiệu).

Khác ba bộ đã làm trước:
  · **OmniVoice** (`giong_ngoai.py`) — trọng số **CC-BY-NC = CẤM kiếm tiền**.
    Anh Hùng bán app, nên bộ đó vĩnh viễn là đồ thử.
  · **Piper** (`piper_tts.py`) — GPL-3, phải gọi như chương trình RỜI, và chỉ
    có **1 giọng Việt**.
  · **ElevenLabs** — tính tiền theo ký tự.
  VieNeu: **Apache-2.0 sạch** (dùng thương mại được, không phải mở mã),
  **20 giọng Việt dựng sẵn**, chạy trên máy, và **nhân bản giọng** từ mẫu 3-5
  giây.

═══════════════════════════════════════════════════════════════════════════
BA CON SỐ ĐÍNH CHÍNH SO VỚI MÔ TẢ VIỆC — ĐỌC TRƯỚC KHI TIN TÀI LIỆU
═══════════════════════════════════════════════════════════════════════════
  1. **48 kHz, KHÔNG phải 24 kHz.** `v3turbo.py:109` ghi thẳng
     `self.sample_rate = 48_000`. 24 kHz là bản **v2** (`voices.json`, 6
     giọng). Bản này dùng **v3 Turbo**.
  2. **20 giọng chỉ có từ 3.2.8.** Đếm THẲNG trong gói pip
     (`vieneu/assets/voices_v3_turbo.json`): **3.2.5 = 14 giọng · 3.2.8 = 20
     giọng**. Máy nào còn 3.2.5 thì 6 giọng cuối (kể cả `Adam`) **KHÔNG TỒN
     TẠI** và `infer` sẽ NÉM `ValueError`. Vì vậy `tinh_trang_vieneu()` đọc
     phiên bản và `PHIEN_BAN_TOI_THIEU` chặn — xem `_du_giong`.
  3. **KHÔNG có mốc từng chữ.** `infer()` trả về **một mảng sóng âm, hết**
     (đọc `v3turbo.py:397-446`: không `timestamp`/`alignment`/`boundary` nào
     lọt ra ngoài). Mốc phải lấy bằng **gióng hàng cưỡng bức**
     (`giong_hang.py`) — xem `_lay_moc`.

═══════════════════════════════════════════════════════════════════════════
BẪY SỐ 1 — `use_ref_codes` LÀ CỜ BOOL, KHÔNG PHẢI CHỖ ĐỂ ĐƯỜNG DẪN
═══════════════════════════════════════════════════════════════════════════
**Lượt 4 đã sập đúng cái bẫy này** (`docs/GIONG_NHAN_BAN.md` B0): truyền
đường dẫn file mẫu vào tham số `use_ref_codes`. Nhìn thì có vẻ chạy — không
nổ, ra tiếng bình thường — nhưng chữ ký thật là::

    def infer(self, text, ref_audio=None, voice=None, style=None,
              denoise=True, use_ref_codes=True, ...)

`use_ref_codes` là **bool**. Đưa chuỗi đường dẫn vào chỉ làm nó thành `True`
(chuỗi khác rỗng là truthy), nên **giọng ra vẫn là giọng mặc định** =
**DƯƠNG TÍNH GIẢ**. Tham số ĐÚNG để nhân bản là **`ref_audio=`**.

Thứ tự ưu tiên trong `_resolve_ref` (`v3turbo.py:304`), chép nguyên văn
docstring của nó: *"Precedence: cloned ``ref_audio`` → preset ``voice`` (name
or dict) → default preset."* Tức đưa CẢ HAI thì `ref_audio` thắng và `voice`
bị bỏ im lặng. **File này luôn truyền ĐÚNG MỘT trong hai** (`_viec_doc`), và
cổng có ca **quét tĩnh bằng AST** bắt: không được có `use_ref_codes=<chuỗi>`,
và không được truyền đồng thời `ref_audio` với `voice`.

**ĐỐI CHỨNG ÂM LÀ BẮT BUỘC KHI ĐO NHÂN BẢN.** Muốn biết nhân bản có CHẠY
không thì phải chạy thêm một lượt **không đưa mẫu nào** để biết giọng mặc
định cao độ bao nhiêu; 8 bản sao mà xúm quanh giá trị đó là nhân bản KHÔNG
chạy. Lượt 9 đã làm đúng vậy: mặc định **160,9 Hz**, 8 bản sao trải
**98,2 → 273,5 Hz**, tản mát **60,9 Hz**, Spearman mẫu-vs-bản-sao **1,0000**.

═══════════════════════════════════════════════════════════════════════════
BẪY SỐ 2 — CÓ WATERMARK NHÚNG TRONG TIẾNG, VÀ NÓ BẬT SẴN
═══════════════════════════════════════════════════════════════════════════
`base.py:118 _init_watermarker` dựng `perth.PerthImplicitWatermarker()`, và
`infer(..., apply_watermark=True)` là **mặc định**. Gói `perth` **đã có** trong
môi trường (kiểm: `site-packages/perth`), nên tiếng ra **CÓ dấu chìm**.

Đây không phải lỗi, nhưng anh Hùng bán app nên **phải biết mình đang phát
hành cái gì** — cùng luật với nhãn giấy phép của OmniVoice/Piper. File này
**GIỮ NGUYÊN watermark theo mặc định của tác giả** (gỡ dấu nguồn gốc của
người khác là việc phải hỏi, không phải việc tự quyết), và nói ra trong nhãn.
`BQ_VN_WATERMARK=0` tắt được — để đo A/B, đừng bật bừa trong sản xuất.

═══════════════════════════════════════════════════════════════════════════
GIỌNG "Adam" — NGHI VẤN ĐÃ ĐO XONG, KHÔNG CÒN CHẶN (19/08/2026)
═══════════════════════════════════════════════════════════════════════════
Giọng thứ 20 tên **`Adam`**, mô tả *"Nam · Tiếng Anh · Giọng đọc tự nhiên"* —
và `Adam` cũng đúng là tên một giọng dựng sẵn nổi tiếng của ElevenLabs.

**BẢN TRƯỚC CHẶN NÓ, VÀ CHẶN SAI — TỰ MÂU THUẪN NGAY TRONG FILE NÀY.** Bằng
chứng để chặn vỏn vẹn là **CÁI TÊN**; mà cách đó 10 dòng, cùng file, kết luận
về `Ngọc Huyền` (trùng tên một giọng Vbee anh Hùng từng muốn mua) là *"trùng
tên KHÔNG phải bằng chứng"* nên KHÔNG chặn. **Cùng một lập luận, áp hai
kiểu.** Anh Hùng bắt đúng: *"Adam là giọng của 1 người nào đó chứ không phải
giọng mà Adam bán"* — "Adam" là tên người rất phổ biến, y như "Ngọc Huyền".

**ĐO THAY VÌ TRANH LUẬN.** Máy có 5 key ElevenLabs -> lấy được giọng Adam
THẬT -> so bằng **ECAPA-TDNN** (`_do_adam.py`, thước là HỆ THỨ BA:
`speechbrain/spkrec-ecapa-voxceleb`, không phải ElevenLabs cũng không phải
VieNeu). 6 câu tiếng Anh giống hệt nhau, VieNeu chạy **5 lượt** vì bộ này
không tiền định::

    CÂU HỎI  VieNeu Adam  x  ElevenLabs Adam    0,115 – 0,346  (TV 0,223)

    ĐỐI CHỨNG DƯƠNG  ElevenLabs Adam x chính nó 0,814 – 0,889
    ĐỐI CHỨNG DƯƠNG  VieNeu Adam     x chính nó 0,756 – 0,931
    ĐỐI CHỨNG ÂM     VN Adam x EL Brian (nam)   0,006 – 0,135
    ĐỐI CHỨNG ÂM     VN Adam x EL Sarah (nữ)    0,082 – 0,204
    ĐỐI CHỨNG ÂM     VN Adam x VN "Minh Đức"    0,255 – 0,362

Cao nhất của câu hỏi (**0,346**) so với thấp nhất của cùng-một-người
(**0,756**) là **vực sâu 0,41**. Nặng hơn nữa: **hai giọng VieNeu KHÁC NHAU
giống nhau (0,292) HƠN là `vn:Adam` giống Adam ElevenLabs (0,223)**.
=> **KHÁC NGƯỜI.** Giọng này KHÔNG phải giọng ElevenLabs bán.

**ĐIỀU VẪN CHƯA BIẾT — GHI THẲNG, ĐỪNG ĐỌC PHÉP ĐO QUÁ TAY:** phép đo trên
chỉ loại được ĐÚNG MỘT nghi vấn. Nó **KHÔNG** trả lời được "vậy giọng này của
ai", vì bảng giọng chỉ lưu `speaker_emb` (192 số) + `codes`, **`text` = None**
— KHÔNG file mẫu gốc, KHÔNG dòng ghi công, `meta` vỏn vẹn
`{"note": "v3 turbo curated preset voices (named)", "count": 20}`. Đó đúng
bằng mức "chưa biết" của **cả 19 giọng còn lại**, nên nó không phải lý do để
đối xử riêng với giọng này. Nhãn nói ra điều chưa biết đó (`GHI_CHU_ADAM`),
KHÔNG chặn.

**LUẬT CHUNG RÚT RA, ÁP CHO MỌI BỘ GIỌNG:** *trùng tên = CHƯA BIẾT, không
phải bằng chứng.* Muốn chặn thì phải có lý do CỤ THỂ HƠN CÁI TÊN — tác giả tự
khai nguồn dữ liệu (`giong_vbee`: model "Ngọc Huyền" trên HuggingFace tự khai
huấn luyện từ giọng Vbee), hoặc giấy phép ghi rõ cấm thương mại
(`piper_tts`: `vivos` CC BY-NC-SA · `25hours_single` "License: Unknown").

═══════════════════════════════════════════════════════════════════════════
"Adam NGHE LẠ": HỎNG THẬT hay CHỈ KÉM — ĐO XONG 19/08/2026, LÀ **CHỈ KÉM**
═══════════════════════════════════════════════════════════════════════════
Anh Hùng nghe rồi: *"cái adam bị lỗi hay sao nghe cứ lạ lạ khác lắm, không như
tôi nghĩ"*, và trỏ vào giọng Adam THẬT của ElevenLabs: *"ít nhất phải như này
mới oke"*. `_do_adam_en.py` (cửa thật `dubbing._synth_all`, corpus + bộ chấm
dùng lại `_do_vieneu_en.py`, Groq chép ngược, VieNeu chạy 2 lượt vì **không
tiền định**) trả lời bằng số — xem `_kq_adam_en.txt`.

**KHÔNG TÌM RA MỘT LỖI MÃ/CẤU HÌNH NÀO Ở ĐƯỜNG ADAM** (nên không có gì để
sửa, và đó là kết luận chứ không phải "chưa tìm"):
  · `_MA_DOC` gọi `tts.infer(text=..., voice="Adam")` — ĐÚNG tham số, KHÔNG
    truyền kèm `ref_audio` (bẫy số 1 ở trên), KHÔNG truyền `style` (bản v3
    Turbo ghi thẳng `style` là **DEPRECATED và BỊ BỎ QUA**: phong cách nằm
    trong `codes` của chính giọng);
  · `Adam` có **CÙNG BỘ KHOÁ** với 19 giọng Việt (`description · gender ·
    region · style · speaker_emb 192 số · codes`) — tức nó chỉ là một CHẤT
    GIỌNG khác, không phải một chế độ khác;
  · đọc **34/34 câu** và **24/24 token rời**, không câu nào hỏng, không lần
    nào lùi edge-tts.

**GIẢ THUYẾT "Adam dùng BỘ ÂM TIẾNG VIỆT để đọc tiếng Anh" — ĐO RA LÀ SAI Ở
CHỖ NGƯỜI TA HAY NGHĨ, VÀ ĐÚNG Ở MỘT CHỖ KHÁC.** Đây là phần đáng đọc nhất:
  · `infer()` **không có tham số ngôn ngữ**, và bộ phiên âm ghi cứng
    `SEAPipeline(lang="vi")` + `G2P(lang="vi")` (`vieneu_utils/
    phonemize_text.py`); `sea_g2p` còn **từ chối `lang="en"`**
    (*"lang must be one of ('vi','th','id')"*). Đọc tới đây thì giả thuyết
    trông như đã được chứng minh.
  · **NHƯNG CHẠY THẬT BỘ PHIÊN ÂM ĐÓ THÌ NGƯỢC LẠI**: chữ tiếng Anh ra **âm
    tiếng Anh đúng** (`A storm unlike anything` -> `ɐ stˈɔːɹm ʌnlˈaɪk
    ˈɛnɪθˌɪŋ`), chữ tiếng Việt ra âm Việt kèm số thanh điệu (`Một cơn bão` ->
    `mˈo6t̪ kˈəːn bˈaː5w`). Docstring của nó ghi *"Vietnamese/**bilingual**
    text"* — tức nó CÓ đường cho chữ Latin nước ngoài.
  · Bộ token của model là **byte-level BPE 419 token**: cả hai chuỗi âm đều
    ra **0 `<|unk|>`** (Anh 76 token / 80 ký tự âm · Việt 80/92). Không có
    chuyện "âm tiếng Anh bị bỏ".
  · Vậy chỗ ĐÚNG của giả thuyết là **MODEL ÂM**, không phải bộ âm/token:
    checkpoint là `VieNeu-TTS-v3-Turbo` huấn luyện trên
    `VieNeu-TTS-1000h-in-the-wild-**coded**` (tiếng Việt), nên nó phát ra âm
    tiếng Anh bằng thứ nó học được từ tiếng Việt. Bằng chứng thực nghiệm sạch
    nhất cho điều đó nằm ngay trong bảng số: **`vn:Adam` đọc TIẾNG VIỆT tốt
    hơn hẳn chính nó đọc TIẾNG ANH, và tốt NGANG một giọng Việt** (xem
    `GHI_CHU_ADAM`). Một giọng "tiếng Anh" mà giỏi tiếng Việt hơn tiếng Anh
    thì "nghe lạ" là **đúng theo cấu tạo**, không phải lỗi.
  · Thước PHỤ độc lập cũng nói vậy theo chiều khác: Groq (KHÔNG ép ngôn ngữ)
    dán nhãn **34/34 câu Adam đọc tiếng Anh là "English"** — tiếng ra vẫn là
    tiếng Anh nhận ra được, chứ không phải "tiếng lạ" theo nghĩa máy nghe
    không hiểu.

**HỆ QUẢ, VÀ NÓ LÀ VIỆC CỦA NHÃN CHỨ KHÔNG PHẢI CỦA MÃ:** kém là giới hạn của
model, không sửa được bằng mã. Nên `GHI_CHU_ADAM` (a) nói thẳng số đo, (b) chỉ
đường sang **ElevenLabs Adam đã có sẵn trong app** cho ai cần đúng chất giọng
ấy, kèm cái giá (tốn hạn mức). **KHÔNG chặn, KHÔNG giấu khỏi combo** — anh
Hùng đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*, và số đo không đủ xấu để
tự quyết thay anh ấy (Adam **không** phải giọng tệ nhất bộ ở tiếng Anh).

**TUYỆT ĐỐI KHÔNG nhân bản/tinh chỉnh giọng từ mẫu ElevenLabs** để "cho giống
Adam". App này BÁN RA; đó là làm bản sao một giọng thương mại đang được bán.
Đường đó không đi, và cũng không đề xuất.

═══════════════════════════════════════════════════════════════════════════
SỐ ĐO ĐÃ CÓ (docs/GIONG_NHAN_BAN.md, lượt 9 — 18/08/2026)
═══════════════════════════════════════════════════════════════════════════
Thước mốc DUY NHẤT là `silencedetect` (không máy nghe nào), ngưỡng −30 dB
(−40 dB quá nhạy, nó tưởng tiếng HÍT VÀO là bắt đầu nói -> chấm trễ oan;
đã sửa thước rồi đo lại TOÀN BỘ các arm, arm edge-tts vẫn tái lập ~15 ms nên
thước tin được).

    RUNG mốc chữ đầu   VieNeu mặc định **8,5 ms** · edge-tts **13,5 ms**
                       nhân bản **14,6 ms** (Common Voice) / **15,4** (FLEURS)
                       Piper 29,5 ms · OmniVoice + gióng hàng 90-119 ms
    ĐỌC SAI CHỮ        edge-tts **6,2%** · VieNeu mặc định **7,7%**
                       nhân bản **21,2%** (Common Voice) / **15,9%** (FLEURS)
    BỊA CHỮ            **+0,8%** — sạch, qua được án tử đã loại viXTTS

**PHẦN PHẢI NÓI THẲNG:** 21,2% của nhân bản **KHÔNG phải lỗi của cơ chế nhân
bản**. Lượt 9 chạy arm quyết định: nhân bản từ **mẫu sạch tuyệt đối** (lấy
chính đầu ra của giọng mặc định làm mẫu) ra **7,7%** — **đúng bằng** giọng
mặc định, tức **giá của việc nhân bản = 0,0 điểm**. Toàn bộ phần sai thêm là
**CHẤT LƯỢNG MẪU**, và **lọc nhiễu KHÔNG chữa được** (đã thử: 28,2% -> 29,2%,
tệ đi). Hệ quả thực dụng: **mẫu tốt thì được giọng tốt; lấy mẫu bừa thì ~2/3
khả năng ra giọng hỏng** — nên `nhan_giong` nói thẳng câu đó ra.

═══════════════════════════════════════════════════════════════════════════
TIẾN TRÌNH RIÊNG — BẮT BUỘC, KHÔNG PHẢI CHO GỌN
═══════════════════════════════════════════════════════════════════════════
Trong tiến trình đã nạp PyQt6 + `QApplication` thì `import torch` chết với
`OSError [WinError 1114] ... torch\\lib\\c10.dll`, và **`try/except` KHÔNG
chặn được ACCESS VIOLATION**. App này LÀ app Qt (bài học cổng 55: tính năng
v2.24.0 hoá ra KHÔNG BAO GIỜ chạy được khi bấm từ giao diện, mà lỗi lại đội
lốt *"máy chưa cài Demucs"*).

VieNeu bản CPU chạy bằng **onnxruntime, không cần torch** — nhưng
`_v3_turbo_engine` vẫn `import torch` ở đường GPU, và `perth` cũng kéo theo
đồ nặng. **Không đánh cược**: cả file này
  - KHÔNG `import torch`, KHÔNG `import vieneu`, KHÔNG `import onnxruntime`
    (kể cả trong `try/except`);
  - KHÔNG chèn thư mục gói vào `sys.path` của app;
  - dò "đã cài chưa" bằng **FILE CÓ TỒN TẠI KHÔNG**, không bằng `find_spec`
    (`find_spec` phải NẠP gói cha; và nó luôn tìm trên `sys.path` nên không
    trả lời được câu "gói có nằm ĐÚNG CHỖ KIA không" — bài học cổng 58: máy
    dev mượn gói của `.venv` rồi báo "đã cài" trong khi thư mục đích rỗng).

═══════════════════════════════════════════════════════════════════════════
CHỖ ĐỂ ĐỒ: `DATA_DIR`, **KHÔNG** `%TEMP%` — VÀ ĐÂY LÀ BẰNG CHỨNG
═══════════════════════════════════════════════════════════════════════════
Lượt 9 dựng môi trường ở `%TEMP%\\bq_giong8\\venv`. Kiểm lại hôm nay:
**venv (768 MB) còn, nhưng thư mục trọng số `hf` ĐÃ BIẾN MẤT** — tức chuyện
"`%TEMP%` bị dọn" **không phải nguy cơ lý thuyết, nó ĐÃ XẢY RA** ngay trên
chính bộ đo này. Và triệu chứng không phải một dòng lỗi mà là **"giọng tự
nhiên biến khỏi combo"**, đúng loại hỏng âm thầm không ai lần ra.

Cùng bệnh: `_lib` của Demucs bị chính lượt tự cập nhật xoá (cổng 58 CA5),
môi trường OmniVoice 7,74 GB nằm trong `%TEMP%` (đã dời 18/08/2026).

Nên: `thu_muc_vieneu()` = `<repo>/_giong_vieneu` khi chạy nguồn ·
`DATA_DIR/_giong_vieneu` ở bản `.exe` (**không** cạnh `.exe`: lượt tự cập
nhật `ren _internal -> _internal.old` rồi `rmdir /S /Q` là xoá sạch).
Ứng viên `%TEMP%` vẫn GIỮ ở **CUỐI** danh sách — máy nào còn bản cũ thì chạy
được thay vì gãy — nhưng `o_thu_muc_tam()` sẽ **kêu mỗi lượt**.

═══════════════════════════════════════════════════════════════════════════
CHƯA LÀM — GHI THẲNG, ĐỪNG ĐỌC NHẦM LÀ ĐÃ XONG
═══════════════════════════════════════════════════════════════════════════
  · Bản `.exe` **KHÔNG gói** vieneu (cùng ràng buộc Demucs/Piper/gióng hàng):
    máy nhân viên phải có Python 3 rồi bấm nút tải.
  · `nhan_nha.BANG` **chưa có giọng `vn:`** cho tới khi đo xong -> `nhan()`
    trả chuỗi RỖNG. Cố ý: bịa một con số cho giọng chưa đo là đúng loại "phép
    đo phát chứng nhận" mà cả repo này đang chống.
"""
from __future__ import annotations

import array
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Optional

_NO_WIN = 0x08000000 if os.name == "nt" else 0

# ---------------------------------------------------------------------------
# Nhận dạng giọng
# ---------------------------------------------------------------------------
#: Giọng DỰNG SẴN: `vn:<tên giọng>` (tên có dấu, đúng khoá trong gói).
#: Mã edge-tts không bao giờ chứa dấu hai chấm nên các họ giọng không lẫn nhau.
TIEN_TO = "vn:"

#: Giọng NHÂN BẢN: `vnb:<đường dẫn file mẫu>`. Đường dẫn đi THẲNG trong mã
#: giọng vì `doc_loat` chỉ nhận một chuỗi `voice` — cùng cách `piper:` nhét
#: tên model vào mã. Nhờ vậy mọi đường gọi cũ không phải đổi chữ ký.
TIEN_TO_NB = "vnb:"

#: Từ bản này trở lên mới đủ 20 giọng. 3.2.5 chỉ có 14 và **thiếu cả `Adam`**;
#: chọn giọng không tồn tại thì `infer` NÉM `ValueError`, tức người dùng chọn
#: một giọng có trong combo mà lượt đọc chết -> `doc_loat` lùi edge-tts.
PHIEN_BAN_TOI_THIEU = (3, 2, 8)

#: Kho HuggingFace của trọng số (tải tự động lần đầu qua `huggingface_hub`).
REPO_VN = "pnnbao-ump/VieNeu-TTS-v3-Turbo"

#: Tần số lấy mẫu đầu ra — ĐỌC TỪ MÃ GÓI (`v3turbo.py:109`), không phải từ
#: trang giới thiệu.
TAN_SO = 48000


def la_giong_dung_san(voice: str) -> bool:
    return str(voice or "").startswith(TIEN_TO)


def la_giong_nhan_ban(voice: str) -> bool:
    return str(voice or "").startswith(TIEN_TO_NB)


def la_giong_vieneu(voice: str) -> bool:
    """Giọng này có thuộc file này không."""
    return la_giong_dung_san(voice) or la_giong_nhan_ban(voice)


def ten_giong(voice: str) -> str:
    """`vn:Minh Đức` -> `Minh Đức`. Giọng nhân bản -> đường dẫn file mẫu."""
    s = str(voice or "")
    if s.startswith(TIEN_TO_NB):
        return s[len(TIEN_TO_NB):]
    if s.startswith(TIEN_TO):
        return s[len(TIEN_TO):]
    return s


# ---------------------------------------------------------------------------
# 20 GIỌNG DỰNG SẴN
# ---------------------------------------------------------------------------
#: (khoá trong gói, nhãn tiếng Việt). **ĐẾM THẲNG TRONG GÓI pip**
#: `vieneu/assets/voices_v3_turbo.json` của bản **3.2.8** (`meta.count = 20`),
#: không chép từ README — README của repo liệt kê tên khác và thiếu vài giọng.
#:
#: Nhãn giữ NGUYÊN VĂN mô tả của tác giả (`Nam · Bắc · Phong cách tin tức`)
#: chứ không tự dịch lại: đó là thông tin của người làm ra giọng, mình đoán
#: lại là thêm một chỗ sai.
#:
#: **THỨ TỰ Ở ĐÂY KHÔNG PHẢI THỨ TỰ TRONG COMBO** — `danh_sach_giong()` sắp
#: theo nhấn nhá (cổng 76), giọng truyền cảm lên trên.
GIONG_VN: tuple[tuple[str, str], ...] = (
    ("Minh Đức",    "Nam · Bắc · Phong cách tin tức"),
    ("Phạm Tuyên",  "Nam · Bắc · Phong cách tự nhiên"),
    ("Thái Sơn",    "Nam · Nam · Phong cách kể chuyện"),
    ("Xuân Vĩnh",   "Nam · Nam · Phong cách tự nhiên"),
    ("Thanh Bình",  "Nam · Bắc · Phong cách kể chuyện"),
    ("Trúc Ly",     "Nữ · Bắc · Phong cách tự nhiên"),
    ("Ngọc Linh",   "Nữ · Bắc · Phong cách kể chuyện"),
    ("Đoan Trang",  "Nữ · Bắc · Phong cách tự nhiên"),
    ("Mai Anh",     "Nữ · Bắc · Phong cách tin tức"),
    ("Thục Đoan",   "Nữ · Nam · Phong cách kể chuyện"),
    ("Minh Triết",  "Nam · Nam · Phong cách tin tức"),
    ("Thùy Dung",   "Nữ · Nam · Phong cách tin tức"),
    ("Quang Sơn",   "Nam · Trung · Phong cách tự nhiên"),
    ("Ngọc Trân",   "Nữ · Trung · Phong cách tự nhiên"),
    ("Mỹ Duyên",    "Nữ · Nam · Phong cách đọc truyện"),
    ("Quỳnh Anh",   "Nữ · Bắc · Phong cách đọc truyện"),
    ("Đức Trí",     "Nam · Nam · Phong cách đọc truyện"),
    ("Kim Thanh",   "Nữ · Nam · Phong cách đọc truyện"),
    ("Ngọc Huyền",  "Nữ · Bắc · Giọng đọc tự nhiên"),
    ("Adam",        "Nam · Tiếng Anh · Giọng đọc tự nhiên"),
)

#: Giọng bị CHẶN khỏi combo vì nguồn.
#:
#: **RỖNG — 19/08/2026.** `Adam` từng nằm đây với bằng chứng DUY NHẤT là cái
#: tên; đã đo bằng ECAPA và loại được nghi vấn đó (xem khối đầu file).
#:
#: **ĐIỀU KIỆN ĐỂ THÊM MỘT TÊN VÀO ĐÂY** — cố ý viết ra để lần sau đừng ai
#: chặn theo linh cảm: phải có lý do **CỤ THỂ HƠN CÁI TÊN**, tức tác giả TỰ
#: KHAI nguồn dữ liệu, hoặc giấy phép GHI RÕ cấm thương mại. Trùng tên một
#: mình thì **KHÔNG** — đó là "chưa biết", không phải bằng chứng, và cả 20
#: giọng của bộ này đều ở mức "chưa biết" như nhau.
_NGO_NGUON: frozenset[str] = frozenset()

#: Giọng đọc TIẾNG ANH. **`Adam` là giọng tiếng Anh DUY NHẤT trong 20 giọng**
#: — 19 giọng còn lại đều là giọng Việt (Bắc/Trung/Nam), xem `GIONG_VN`.
#:
#: Phải nói ra **NGAY TRÊN DÒNG combo lúc ĐÓNG**, không đẩy vào tooltip: anh
#: Hùng chạy 200-300 kênh Việt, chọn nhầm một lần là hàng trăm video đọc bằng
#: giọng tiếng Anh. Đây là chuyện SẼ HỎNG NGAY, khác hẳn ghi chú nguồn.
GIONG_TIENG_ANH: frozenset[str] = frozenset({"Adam"})

#: GHI CHÚ (không phải cảnh báo, không phải chốt chặn) cho `Adam` — đi vào
#: TOOLTIP. Giữ lại thông tin của bản cũ vì **thông tin không sai, chỉ có kết
#: luận rút ra từ nó là sai**; nay nói cả hai vế: cái ĐÃ ĐO và cái CHƯA BIẾT.
#:
#: **19/08/2026 — THÊM SỐ ĐO "HỎNG hay KÉM" VÀ CHỈ ĐƯỜNG SANG ElevenLabs.**
#: Anh Hùng nghe rồi nói *"nghe cứ lạ lạ khác lắm, không như tôi nghĩ"* và trỏ
#: vào giọng Adam THẬT của ElevenLabs. Đo ra là **KÉM, KHÔNG HỎNG** (chi tiết ở
#: khối docstring đầu file + `_do_adam_en.py`), tức **không có gì sửa được bằng
#: mã** — nên việc phải làm là nhãn NÓI THẲNG số đo và chỉ đúng chỗ có chất
#: giọng đó. Nhãn không chỉ đường thì anh Hùng còn nghe thử 19 giọng nữa để
#: tìm thứ bộ này không có.
#:
#: Số trong nhãn LẤY TỪ CÙNG MỘT LƯỢT ĐO (`_kq_adam_en.txt`, 34 câu, Groq chép
#: ngược, cửa thật) nên so được với nhau. **Đừng trộn với 7,7%/6,2% của
#: `_CL_DUNG_SAN`** — số đó đo trên bộ câu KHÁC, ghép hai bảng là kết luận sai.
GHI_CHU_ADAM = (
    "giọng TIẾNG ANH duy nhất của bộ — chọn cho video tiếng Việt là đọc sai "
    "cả loạt. ĐO 19/08 trên BỘ CÂU TIẾNG ANH RIÊNG (34 câu × 2 lượt, máy nghe "
    "chép ngược — mấy số dưới đây KHÔNG so được với «7,7% so với edge-tts "
    "6,2%» nói ở trên vì khác bộ câu): đọc tiếng Anh "
    "sai chữ 7,7-12,8% còn giọng thường en-US-AriaNeural chỉ 0,0%; đọc rời "
    "từng chữ 16,7-29,2% so với 4,2% — tức KÉM HƠN, KHÔNG HỎNG: nó đọc trôi "
    "cả 34/34 câu, bịa chữ 0,6% (THẤP NHẤT bảng), sai cả bài chỉ 5,2-7,0% so "
    "với 3,7% của giọng thường, và máy nghe nhận đúng tiếng Anh 34/34 (ba "
    "giọng VieNeu khác đọc tiếng Anh còn bị nhận thành tiếng Việt / tiếng "
    "Mã Lai). Ba giọng đó cũng sai nhiều hơn hẳn (15,4-17,9%), nên đây là "
    "giới hạn CỦA CẢ BỘ giọng Việt, không phải lỗi riêng giọng này — nghe lạ "
    "là ĐÚNG THEO CẤU TẠO (chính nó đọc TIẾNG VIỆT chỉ sai 2,5-5,0%, giỏi "
    "tiếng Việt hơn tiếng Anh). Chỗ nó thật sự hụt là TÊN RIÊNG và VIẾT TẮT "
    "(đo được: Albuquerque, Siobhan, CEO, AI, OST, 250 km/h). "
    "MUỐN ĐÚNG CHẤT GIỌNG ẤY thì chọn Adam của "
    "ElevenLabs đã có sẵn trong app (nhóm giọng trả phí) — hay hơn nhưng TỐN "
    "HẠN MỨC tính theo số ký tự, đó là giá của chất lượng đó. "
    "Tên trùng một giọng dựng sẵn của ElevenLabs nhưng ĐÃ ĐO bằng ECAPA-TDNN "
    "và ra KHÁC NGƯỜI (0,115-0,346 so với cùng-một-người 0,756-0,931; hai "
    "giọng VieNeu khác nhau còn giống nhau hơn thế); vẫn CHƯA BIẾT giọng gốc "
    "của ai vì gói không kèm mẫu gốc lẫn dòng ghi công — đúng bằng mức chưa "
    "biết của 19 giọng còn lại")

#: Tên cũ, GIỮ để lối gọi/tài liệu cũ không gãy. Trỏ vào `GHI_CHU_ADAM`.
CANH_BAO_ADAM = GHI_CHU_ADAM

#: Giấy phép — nói ĐƯỢC cái gì, đừng chỉ nói tên giấy phép.
GIAY_PHEP = ("Apache-2.0: dùng thương mại được, không phải mở mã app")

#: Cảnh báo chất lượng cho giọng DỰNG SẴN. Số lấy từ `docs/GIONG_NHAN_BAN.md`.
#: Cùng luật với Piper/OmniVoice (cổng 64/72): tệ hơn edge-tts ở chỗ nào thì
#: phải ghi ra, đừng để người dùng tự phát hiện sau 300 video.
_CL_DUNG_SAN = ("đọc sai chữ 7,7% so với edge-tts 6,2%; tiếng có dấu chìm "
                "(watermark Perth) của nhà phát hành")

#: Giọng NHÂN BẢN: điểm yếu nằm ở MẪU, không ở máy — nói đúng chỗ đó.
_CL_NHAN_BAN = ("đọc sai chữ tuỳ CHẤT LƯỢNG MẪU: mẫu sạch 7,7% (bằng giọng "
                "dựng sẵn) nhưng mẫu thu bằng điện thoại lên tới 21-31%; lọc "
                "nhiễu KHÔNG chữa được — phải nghe thử rồi mới dùng")


def canh_bao_chat_luong(ma: str = "") -> str:
    """Câu cảnh báo ĐÚNG VỚI MÁY NÀY và đúng loại giọng.

    KHÔNG cất kết quả vào hằng số: người dùng bấm nút tải bộ gióng hàng giữa
    phiên thì nhãn phải đổi theo, không đợi khởi động lại app (bài học
    `tg_so.duong_so` và `giong_ngoai.canh_bao_chat_luong`).
    """
    goc = _CL_NHAN_BAN if la_giong_nhan_ban(ma) else _CL_DUNG_SAN
    if not _co_giong_hang():
        return (goc + "; máy CHƯA có bộ gióng hàng nên chữ KHÔNG chạy theo "
                      "tiếng được (VieNeu không tự trả mốc từng chữ) — tải bộ "
                      "gióng hàng để hết bệnh này")
    return goc + "; mốc chữ lấy bằng gióng hàng, rung 8,5 ms (edge-tts 13,5)"


def _co_giong_hang() -> bool:
    try:
        from app.core import giong_hang as _gh
        return bool(_gh.co_giong_hang())
    except Exception:  # noqa: BLE001
        return False


def nhan_giong(ma: str, ngan: bool = False) -> str:
    """Nhãn cho hộp chọn giọng. TIẾNG VIỆT, KHÔNG EMOJI.

    Nhãn PHẢI mang cả giấy phép lẫn điểm yếu — Piper/OmniVoice đã có tiền lệ
    ghi thẳng đánh đổi ngay trong nhãn, lý do là anh Hùng chạy 200-300 kênh:
    chọn nhầm một lần là hàng trăm video.

    KÈM MỨC NHẤN NHÁ (`app/core/nhan_nha.py`) để giọng VieNeu đứng CÙNG THANG
    với edge-tts — chúng đọc cùng bộ câu tiếng Việt nên so trực tiếp được.
    Giọng chưa đo thì `nhan_nha.nhan()` trả chuỗi RỖNG (không bịa số).

    ═══ ``ngan=True`` — VÌ SAO PHẢI CÓ, ĐO ĐƯỢC ═══
    Nhãn đầy đủ dài **364-521 ký tự** (đo thẳng trên `gom_nhom`, giọng `Adam`
    là 521). Combo lúc ĐÓNG chỉ rộng bằng hộp, nên **quá 60 ký tự là phần sau
    không ai đọc được** — tức nhãn dài KHÔNG hề "nói ra cảnh báo", nó chỉ làm
    danh sách không đọc nổi trong khi cảnh báo vẫn vô hình. Đúng cái anh Hùng
    kêu: *"rất lung tung, không biết chọn sao"*.
    Nên: **combo dùng bản NGẮN, phần cảnh báo đầy đủ đi vào TOOLTIP** (hộp
    chọn giọng gắn bằng `ToolTipRole`). Không mất chữ nào, mà nhìn là đọc
    được. Thứ **SẼ HỎNG NGAY** thì vẫn phải nằm ở bản NGẮN: giọng bị chặn
    nguồn mang dấu **NGỜ NGUỒN**, giọng đọc tiếng Anh mang dấu **TIẾNG ANH**
    (chọn nó cho video Việt là hỏng cả loạt — không được đẩy vào tooltip).
    """
    from app.core import nhan_nha
    if la_giong_nhan_ban(ma):
        mau = Path(ten_giong(ma)).name or "(chưa chọn)"
        dau = f"Nhân bản từ mẫu «{mau}» (VieNeu){nhan_nha.nhan(ma)}"
        if ngan:
            return dau
        return f"{dau} - {GIAY_PHEP}; {canh_bao_chat_luong(ma)}"
    ten = ten_giong(ma)
    for k, mo_ta in GIONG_VN:
        if k == ten:
            ngo = k in _NGO_NGUON
            anh = k in GIONG_TIENG_ANH
            dau = f"{k} — {mo_ta} (VieNeu){nhan_nha.nhan(ma)}"
            if ngan:
                # Chỉ MỘT dấu ở bản ngắn (combo đóng rất hẹp). NGỜ NGUỒN nặng
                # hơn nên thắng — nhưng hiện `_NGO_NGUON` rỗng nên thực tế
                # nhánh chạy là TIẾNG ANH.
                return dau + (" - NGỜ NGUỒN" if ngo
                              else " - TIẾNG ANH" if anh else "")
            them = f"; {CANH_BAO_ADAM}" if ngo else ""
            if anh and not ngo:
                them = f"; {GHI_CHU_ADAM}"
            return f"{dau} - {GIAY_PHEP}; {canh_bao_chat_luong(ma)}{them}"
    return ma


def ma_nhan_ban(duong_mau: str) -> str:
    """Mã giọng cho một file mẫu. Dùng ở hộp chọn file của giao diện."""
    return TIEN_TO_NB + str(duong_mau or "").strip()


#: Ghi vào ĐẦU nhãn khi máy CHƯA tải model. Phải nói ra ở CHÍNH DÒNG đó, vì
#: combo lúc ĐÓNG chỉ hiện một dòng — nhãn nhóm không cứu được.
#:
#: **CHỮ "BỘ CHUNG" LÀ BẮT BUỘC, KHÔNG PHẢI CHO ĐẸP.** Tiền tố này dán lên
#: **CẢ 20 DÒNG** VieNeu, nên bản cũ `"CHƯA TẢI (250 MB) — "` cho anh Hùng đọc
#: ra 20 × 250 MB = **5 GB** (*"sao có cái giọng 1 giọng tận 250mb á tốn
#: thế"*). Sự thật là MỘT bộ 250 MB dùng chung cho cả 20 giọng, tải một lần.
#: Số giọng chính xác nói ở nút `NHAN_TAI` và ở tooltip
#: (`giong_bang.ghi_chu_bo_chung`) — hai chỗ đọc MỘT LẦN, không nhân lên được.
#: Giữ NGẮN vì nó ăn vào bề rộng của chính dòng giọng (cổng 84: 0 nhãn bị cắt).
CHUA_TAI = "CHƯA TẢI (bộ chung 250 MB) — "


def danh_sach_giong(du_chua_tai: bool = False,
                    ngan: bool = False) -> list[tuple[str, str]]:
    """[(mã, nhãn)] để đổ vào combo. Sắp theo **nhấn nhá giảm dần** (cổng 76).

    ``du_chua_tai=False`` (mặc định, giữ cho mọi lối gọi cũ): CHỈ trả giọng
    máy này CHẠY ĐƯỢC.

    ``du_chua_tai=True``: trả ĐỦ 20 giọng kể cả khi chưa tải model, nhãn mang
    tiền tố ``CHUA_TAI``. **ĐÂY LÀ ĐƯỜNG HỘP CHỌN GIỌNG ĐI**, và nó theo đúng
    tiền lệ Piper (cổng 64) chứ không phải một ngoại lệ mới: app **tự tải
    được** VieNeu (nút ``NHAN_TAI``, 250 MB) nên giấu đi thì người dùng không
    bao giờ biết là có, còn hiện ra kèm chữ "CHƯA TẢI" thì họ biết phải bấm
    gì. Khác hẳn OmniVoice 6,1 GB — cái đó app KHÔNG tự tải được nên giấu là
    đúng.

    Điều kiện để việc hiện-khi-chưa-tải KHÔNG thành bẫy "chọn X ra Y": lượt
    đọc phải **nói ra** là nó đã lùi. `dubbing._vieneu_hay_khong` ghi log rồi
    lùi edge-tts, đúng luật Piper.

    ═══ GIỌNG TIẾNG ANH XUỐNG CUỐI — SỐ ĐO, KHÔNG PHẢI SỞ THÍCH ═══
    `nhan_nha.BANG` **chưa có giọng `vn:` nào** (cố ý — chưa đo thì không bịa
    số), nên `khoa_sap` trả **Y HỆT `(1, 0.0)` cho cả 20 giọng** và thứ tự
    thật rơi hết về tiêu chí phụ là **THỨ TỰ CHỮ CÁI của mã giọng**. Hệ quả
    đo được: `vn:Adam` đứng **ĐẦU DANH SÁCH** chỉ vì chữ "A" — tức giọng
    TIẾNG ANH DUY NHẤT nằm trên cùng một danh sách 19 giọng Việt, ngay chỗ
    người ta bấm nhanh nhất. Anh Hùng chạy 200-300 kênh Việt: chọn nhầm một
    lần là hàng trăm video đọc bằng giọng Anh.
    Nên thêm bậc **NGÔN NGỮ** vào ĐẦU khoá sắp: giọng Việt trước, giọng tiếng
    Anh sau. Không đụng bậc nhấn nhá của cổng 76 — nó vẫn là bậc kế tiếp và
    sẽ tự có tác dụng ngay khi bảng nhấn nhá có số cho `vn:`.
    """
    from app.core import nhan_nha
    co = co_vieneu()
    if not co and not du_chua_tai:
        return []
    ma_ds = [TIEN_TO + k for k, _m in GIONG_VN if _cho_hien(k)]
    ma_ds.sort(key=lambda m: (1 if ten_giong(m) in GIONG_TIENG_ANH else 0,
                              nhan_nha.khoa_sap(m), m))
    dau = "" if co else CHUA_TAI
    return [(m, dau + nhan_giong(m, ngan=ngan)) for m in ma_ds]


def _cho_hien(khoa: str) -> bool:
    """Giọng này có được vào combo không. Xem `_NGO_NGUON`.

    **HIỆN ĐỦ 20/20 — `_NGO_NGUON` RỖNG (19/08/2026).**

    Đường đi của quyết định này, ghi lại để đừng ai đảo ngược bằng linh cảm:
      · bản đầu **GIẤU** `Adam` sau `BQ_VN_ADAM=1`, bằng chứng là CÁI TÊN;
      · v2.38.0 đổi thành **HIỆN kèm dấu NGỜ NGUỒN** — đúng hướng, vì cùng
        repo này đang hiện OmniVoice, thứ có rào pháp lý **CỨNG HƠN HẲN**
        (trọng số CC-BY-NC = cấm thương mại, đen trắng trong model card).
        Giấu một giọng chỉ MỜ NGHI trong khi hiện một giọng CHẮC CHẮN cấm
        thương mại là hai cân nặng nhẹ cho cùng một câu hỏi;
      · nay **BỎ HẲN dấu NGỜ NGUỒN**: nghi vấn đó đã ĐO và đã LOẠI bằng
        ECAPA (khối đầu file). Để dấu lại là dán một cảnh báo mà chính mình
        vừa chứng minh là không có cơ sở — người dùng đọc riết rồi bỏ qua mọi
        cảnh báo, kể cả cảnh báo thật.

    Giữ nguyên **CƠ CHẾ** `_NGO_NGUON` chứ không xoá: mai có giọng nào lộ ra
    lý do CỤ THỂ (tác giả tự khai nguồn / giấy phép cấm thương mại) thì thêm
    một dòng là chặn được. Cái bỏ đi là **cái tên trong danh sách**, không
    phải cái khoá.

    (`BQ_VN_ADAM` đã gỡ — nó khoá đúng một giọng theo tên, mà nay không giọng
    nào bị chặn theo tên nữa.)
    """
    return khoa not in _NGO_NGUON


# ---------------------------------------------------------------------------
# Chỗ để đồ — NGOÀI thư mục cài, NGOÀI %TEMP%
# ---------------------------------------------------------------------------
def thu_muc_vieneu() -> Path:
    """Thư mục làm việc của VieNeu (môi trường Python, runner, log, hộp cát).

    ĐỌC `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số ở tầm module — test
    đổi `BQ_DATA_DIR` sau khi module đã nạp thì hằng số cũ trỏ sai chỗ (bài
    học `tg_so.duong_so`, `piper_tts.thu_muc_piper`, `giong_hang.thu_muc_gh`).
    """
    ep = (os.environ.get("BQ_VN_DIR") or "").strip()
    if ep:
        return Path(ep)
    if getattr(sys, "frozen", False):
        try:
            import config
            goc = Path(getattr(config, "DATA_DIR", "") or "")
        except Exception:  # noqa: BLE001
            goc = Path("")
        return (goc or Path.home()) / "_giong_vieneu"
    return Path(__file__).resolve().parents[2] / "_giong_vieneu"


def _venv_that(py) -> Path:
    """Venv mà pip THẬT SỰ cài vào, suy từ chính python được chạy.

    LỖI THẬT 20/08/2026 — log NÓI SAI làm CHÍNH TÔI chẩn đoán sai. `cai_nhan_ban`
    lấy `venv = thu_muc_vieneu()/"venv"` cho lời log, nhưng pip lại chạy bằng
    `_python_vieneu()[0]` = python **ĐANG DÙNG** (trên máy anh Hùng là
    `%TEMP%\\bq_giong8\\venv`). Nên log ghi:

        [19:00:39] Cài phần nhân bản XONG vào ...\\BQHungVideo\\_giong_vieneu\\venv

    trong khi thư mục đó **KHÔNG HỀ TỒN TẠI**. Đọc dòng đó tôi kết luận ngay
    *"cài một chỗ, chạy một chỗ khác"* và suýt đi sửa một bug không có. Kiểm chỗ
    torch thật sự nằm mới thấy pip cài **ĐÚNG** venv đang chạy — chỉ lời log là
    sai.

    Bài học: **lời log phải suy từ CÁI ĐÃ LÀM, không phải từ cái ĐỊNH LÀM.** Log
    nói sai còn tệ hơn không log, vì nó phát chứng nhận cho một chẩn đoán sai —
    cùng họ bẫy "phép đo hỏng phát chứng nhận" của cả repo này.
    """
    p = Path(str(py))
    # <venv>/Scripts/python.exe  hoặc  <venv>/bin/python
    return p.parent.parent if p.parent.name in ("Scripts", "bin") else p.parent


def _ung_vien_python() -> list[Path]:
    """Python có sẵn `vieneu`. Dò theo THỨ TỰ, chỗ ĐÚNG trước chỗ TẠM sau."""
    ds: list[Path] = []
    ep = (os.environ.get("BQ_VN_PYTHON") or "").strip()
    if ep:
        ds.append(Path(ep))
    d = thu_muc_vieneu()
    ds.append(d / "venv" / "Scripts" / "python.exe")
    ds.append(d / "venv" / "bin" / "python")
    # CHỖ CŨ của lượt 9 — giữ ở CUỐI, cố ý: máy nào còn bản cũ thì vẫn chạy
    # được thay vì gãy. Nhưng `o_thu_muc_tam()` sẽ kêu mỗi lượt.
    tam = Path(tempfile.gettempdir())
    ds.append(tam / "bq_giong8" / "venv" / "Scripts" / "python.exe")
    ds.append(tam / "bq_giong8" / "venv" / "bin" / "python")
    return ds


#: File PHẢI có mặt cạnh python thì mới coi là "có vieneu". Dò bằng ĐƯỜNG DẪN
#: nên bản `.exe` (không có `.venv` để mượn) thấy ĐÚNG cái máy dev thấy.
#: `voices_v3_turbo.json` nằm trong danh sách vì **bảng giọng đi kèm GÓI pip**,
#: không đi kèm trọng số — thiếu nó là 20 giọng biến mất mà model vẫn nạp được.
_CAN_CO = ("vieneu/v3turbo.py",
           "vieneu/assets/voices_v3_turbo.json",
           "onnxruntime/__init__.py",
           "soundfile.py",
           "librosa/__init__.py")


def _site_packages(py: Path) -> list[Path]:
    """Các thư mục gói đi kèm một python — KHÔNG chạy python để hỏi."""
    goc = py.parent.parent
    return [goc / "Lib" / "site-packages", goc / "lib" / "site-packages"]


def _phien_ban(sp: Path) -> tuple[int, ...]:
    """Phiên bản `vieneu` đọc từ tên thư mục `.dist-info`. () = không rõ.

    KHÔNG chạy `pip show` (tốn một tiến trình mỗi lượt dò nhãn) và KHÔNG
    import gói.
    """
    try:
        for d in sp.iterdir():
            n = d.name
            if n.startswith("vieneu-") and n.endswith(".dist-info"):
                so = n[len("vieneu-"):-len(".dist-info")].split(".")
                return tuple(int(x) for x in so[:3] if x.isdigit())
    except OSError:
        pass
    return ()


def _python_vieneu() -> tuple[str, list[str], tuple[int, ...]]:
    """(python chạy được, thứ còn thiếu của ứng viên tốt nhất, phiên bản)."""
    thieu_tot_nhat: Optional[list[str]] = None
    pb_tot_nhat: tuple[int, ...] = ()
    for py in _ung_vien_python():
        if not py.exists():
            continue
        for sp in _site_packages(py):
            if not sp.is_dir():
                continue
            thieu = [t for t in _CAN_CO if not (sp / t).exists()]
            pb = _phien_ban(sp)
            if not thieu:
                return str(py), [], pb
            if thieu_tot_nhat is None or len(thieu) < len(thieu_tot_nhat):
                thieu_tot_nhat, pb_tot_nhat = thieu, pb
    return "", (thieu_tot_nhat if thieu_tot_nhat is not None
                else ["môi trường Python có vieneu"]), pb_tot_nhat


def _du_giong(pb: tuple[int, ...]) -> bool:
    """Bản này có đủ 20 giọng không. Không rõ phiên bản -> coi là KHÔNG đủ.

    Không rõ mà cho qua là đúng bệnh "chọn X ra Y": combo hiện 20 giọng, người
    dùng chọn `Adam`, `infer` ném `ValueError`, cả loạt lùi edge-tts.
    """
    return bool(pb) and pb >= PHIEN_BAN_TOI_THIEU


# ---------------------------------------------------------------------------
# Dò đã dùng được chưa — bằng FILE, không bằng import
# ---------------------------------------------------------------------------
def tinh_trang_vieneu() -> dict:
    """{co, thieu, python, thu_muc, phien_ban, so_giong, o_tam, cai_duoc}.

    `thieu` là danh sách để đặt NHÃN — nói đích danh còn thiếu gì, đừng chỉ
    nói "chưa có" (bài học cổng 58: hộp Demucs phải nêu tên từng gói).
    """
    py, thieu, pb = _python_vieneu()
    thieu = list(thieu)
    if py and not _du_giong(pb):
        thieu.append(
            "vieneu >= %s (đang có %s — bản này thiếu 6 giọng)"
            % (".".join(str(x) for x in PHIEN_BAN_TOI_THIEU),
               ".".join(str(x) for x in pb) if pb else "không rõ bản"))
    return {
        "co": bool(py) and not thieu,
        "thieu": thieu,
        "python": py,
        "phien_ban": ".".join(str(x) for x in pb) if pb else "",
        "so_giong": len(GIONG_VN),
        "thu_muc": str(thu_muc_vieneu()),
        # CẢNH BÁO CHỖ ĐỂ ĐỒ. Đây KHÔNG phải "thiếu" (máy vẫn chạy được), nên
        # để RIÊNG khoá: gộp vào `thieu` là nút tải và nhãn báo sai trạng thái.
        "o_tam": o_thu_muc_tam(py),
        "cai_duoc": bool(_python_he_thong()),
    }


def o_thu_muc_tam(py: str = "") -> str:
    """Môi trường nằm trong thư mục TẠM thì trả đường dẫn đó, "" nếu không.

    VÌ SAO PHẢI BÁO RA — và lần này KHÔNG phải nguy cơ lý thuyết: lượt 9 dựng
    môi trường ở `%TEMP%\\bq_giong8`, và tới hôm nay **thư mục trọng số `hf`
    trong đó ĐÃ BIẾN MẤT** trong khi venv vẫn còn. Một lượt `tempsweep` /
    Disk Cleanup / anh Hùng dọn ổ C là mất nốt, và lúc đó `co_vieneu()` trả
    False nên **giọng lặng lẽ biến khỏi combo** — đúng loại hỏng âm thầm repo
    này chống.

    Hàm này KHÔNG tự dời: dời cả một môi trường sau lưng người đang chạy sản
    xuất là việc phải hỏi. Nó chỉ NÓI RA.
    """
    try:
        p = str(py or _python_vieneu()[0] or "")
        if not p:
            return ""
        tam = Path(tempfile.gettempdir()).resolve()
        return str(Path(p).resolve()) if tam in Path(p).resolve().parents \
            else ""
    except Exception:  # noqa: BLE001
        return ""


def co_vieneu() -> bool:
    """Có chạy được VieNeu không. KHÔNG BAO GIỜ NÉM."""
    try:
        return bool(tinh_trang_vieneu()["co"])
    except Exception:  # noqa: BLE001
        return False


def _python_he_thong() -> str:
    """Python 3 trên máy để DỰNG môi trường. "" = không có.

    KHÔNG dùng `sys.executable`: ở bản `.exe` đó là chính `BQHungVideo.exe`,
    gọi `-m venv` vào nó là vô nghĩa (đúng cách `piper_tts._python_chay` và
    `thay_giong` đã làm).
    """
    if not getattr(sys, "frozen", False):
        ex = Path(sys.executable)
        if ex.exists() and ex.name.lower().startswith("python"):
            return str(ex)
    for ten in ("py", "python", "python3"):
        p = shutil.which(ten)
        if p:
            return p
    return ""


def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI vào log ngày.

    **Lùi êm mà im lặng thì đúng bằng hỏng âm thầm** — cùng luật với
    `piper_tts._ghi_log` và `giong_ngoai._ghi_log`.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"giong_vieneu_{ts:%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# NÚT TẢI — chỉ chạy khi NGƯỜI DÙNG BẤM
# ---------------------------------------------------------------------------
#: Nhãn nút. **PHẢI KHỚP ĐƯỜNG SẼ ĐI** (cổng 71 CA 4): ghi 155 MB rồi tải
#: 2,5 GB là lặp đúng lỗi cũ chỉ đổi chiều. Bản CPU (onnxruntime, KHÔNG cần
#: torch) — đo bằng `pip download --no-deps` + metadata chỉ mục, xem
#: `co_bao_nhieu_mb()`.
#:
#: **NÚT LÀ CHỖ ĐÚNG ĐỂ NÓI CON SỐ GIỌNG** (nó chỉ có MỘT cái, đọc một lần,
#: không nhân lên được) — khác hẳn `CHUA_TAI` dán lên cả 20 dòng. Số giọng lấy
#: bằng `len(GIONG_VN)` chứ KHÔNG ghi cứng "20": ghi cứng thì lần thêm/bớt
#: giọng kế tiếp biến nhãn thành lời khai sai mà không một cổng nào kêu.
NHAN_TAI = (f"Tải bộ giọng Việt VieNeu (250 MB, tải MỘT LẦN — dùng chung cho "
            f"cả {len(GIONG_VN)} giọng)")


def cai_vieneu(on_progress: Optional[Callable[[float, str], None]] = None,
               han_giay: int = 3600) -> dict:
    """Dựng môi trường VieNeu ở `thu_muc_vieneu()/venv`. CHỈ khi NGƯỜI DÙNG BẤM.

    **MÔI TRƯỜNG RIÊNG, KHÔNG `pip install` vào `.venv` đang chạy sản xuất**
    — một lượt cài kéo theo numpy/onnxruntime khác bản có thể phá app đang
    chạy 300 kênh (đúng lý do Demucs phải ở `_lib`, cổng 55).

    **KHÔNG dùng `--target`** như Piper/Demucs mà dựng hẳn **venv**: `vieneu`
    kéo theo `librosa`/`numba`/`soundfile` có phần mở rộng biên dịch, cài kiểu
    `--target` rồi nhét vào `sys.path` của một python khác là đường vỡ ABI.
    Venv riêng thì tiến trình con có python CỦA NÓ, không mượn gì của ai —
    và đó cũng là điều làm phép dò `_python_vieneu` nói thật (cổng 58).

    **GHIM ĐÚNG BẢN**: `vieneu==3.2.8`. Không ghim thì hôm nay được 20 giọng,
    tháng sau tác giả đổi bảng giọng là combo lệch với `GIONG_VN` mà không một
    dòng báo.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(p, m)
            except Exception:  # noqa: BLE001
                pass

    py = _python_he_thong()
    if not py:
        return {"ok": False,
                "loi": ("Máy này không có Python 3 nên app không tự tải được: "
                        "cài Python 3 rồi bấm lại, hoặc copy thư mục "
                        "_giong_vieneu từ máy đã cài sang.")}

    d = thu_muc_vieneu()
    venv = d / "venv"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "loi": f"Không tạo được thư mục {d}: {e}"}

    vpy = venv / "Scripts" / "python.exe"
    if not vpy.exists():
        vpy = venv / "bin" / "python"
    if not vpy.exists():
        prog(0.05, "Đang dựng môi trường Python riêng...")
        r = _chay_lenh([py, "-m", "venv", str(venv)], 600)
        if r[0] != 0:
            return {"ok": False, "loi": f"Dựng môi trường hỏng: {r[1][-500:]}"}
        vpy = venv / "Scripts" / "python.exe"
        if not vpy.exists():
            vpy = venv / "bin" / "python"
    if not vpy.exists():
        return {"ok": False, "loi": f"Dựng xong mà không thấy python ở {venv}"}

    prog(0.15, "Đang tải bộ đọc VieNeu (khoảng 250 MB)...")
    r = _chay_lenh([str(vpy), "-m", "pip", "install", "--no-input",
                    "--disable-pip-version-check",
                    "vieneu==%s" % ".".join(
                        str(x) for x in PHIEN_BAN_TOI_THIEU)], han_giay)
    if r[0] != 0:
        return {"ok": False, "loi": (r[1] or "")[-800:]}

    # HẬU KIỂM bằng CHÍNH phép dò của bản `.exe` — không tin lời pip báo.
    # (Bài học cổng 58: pip báo xong trong khi thư mục đích vẫn thiếu gói, và
    # máy dev không thấy vì nó mượn được của `.venv`.)
    prog(0.92, "Đang kiểm lại...")
    tt = tinh_trang_vieneu()
    if not tt["co"]:
        return {"ok": False, "tinh_trang": tt,
                "loi": f"Cài xong nhưng vẫn thiếu: {tt['thieu']}"}
    prog(1.0, "Đã cài xong bộ đọc VieNeu.")
    return {"ok": True, "loi": "", "tinh_trang": tt}


# ---------------------------------------------------------------------------
# NÚT TẢI PHẦN NHÂN BẢN — `torch` + `torchaudio` vào ĐÚNG venv của VieNeu
# ---------------------------------------------------------------------------
#
# ═══ LỖI THẬT ĐẺ RA CẢ KHỐI NÀY (ảnh chụp màn hình của anh Hùng) ═══
# Anh Hùng thêm giọng nhân bản của mình ("MQ Idol", mẫu 7 giây), **lưu thành
# công**, rồi dòng giọng trong hộp "Giọng của tôi" hiện:
#     CHƯA CHẠY ĐƯỢC (thiếu torch, torchaudio) - MQ Idol (giọng nhân bản...)
# Nhãn đó **NÓI THẬT** — `nhan_ban_giong.thieu_de_nhan_ban()` dò bằng FILE CÓ
# TỒN TẠI KHÔNG trong site-packages của python VieNeu (cố ý KHÔNG `find_spec`,
# bài học cổng 58). Đo được: chạy từ MÃ NGUỒN thì `_giong_vieneu/venv/Lib/
# site-packages/torch` CÓ + `torchaudio` CÓ -> trả `[]` = đủ; bản `.exe` thì
# venv nằm ở `%LOCALAPPDATA%\BQHungVideo\_giong_vieneu\venv` và KHÔNG có torch.
# Tức 20 giọng DỰNG SẴN vẫn chạy (chúng đi bằng `onnxruntime`, không cần
# torch) — **chỉ đường NHÂN BẢN mới đụng torch** — và trước lượt này **KHÔNG
# CÓ NÚT NÀO để cài nó**. Tính năng thật thà báo "chưa chạy được" mà không cho
# anh ấy một đường sửa: đó là cái được vá ở đây.
#
# ═══ VÌ SAO HÀM NÀY NẰM Ở `giong_vieneu` CHỨ KHÔNG Ở `nhan_ban_giong` ═══
# Cả 4 hàm cài đã có đều nằm trong module SỞ HỮU môi trường đích:
# `thay_giong.cai_demucs` -> `_lib` · `piper_tts.cai_piper` -> `_piper` ·
# `giong_kokoro.cai_kokoro` -> `_giong_kokoro/venv` · `giong_ngoai.
# cai_omnivoice` -> `_giong_ngoai/venv`. Môi trường đích ở đây là
# `_giong_vieneu/venv`, do CHÍNH file này sở hữu — `thu_muc_vieneu()`,
# `_python_vieneu()`, `_python_he_thong()`, `_ghi_log()` đều đã ở đây. Còn
# `nhan_ban_giong` là bộ ĐIỀU PHỐI (VieNeu vs Chatterbox); nhét một lệnh pip
# riêng của VieNeu vào đó là làm rò nội tạng VieNeu ra tầng điều phối.
# Danh sách gói thì KHÔNG chép lại: đọc `nhan_ban_giong._CAN_CHO_NHAN_BAN` —
# hai bản sao là hai chỗ để quên.

#: Chỉ mục wheel của PyTorch — CÙNG hai địa chỉ `thay_giong`/`giong_kokoro`/
#: `giong_ngoai` đang dùng, để bốn nút tải không bao giờ chọn khác nhau.
CHI_MUC_TORCH_CPU = "https://download.pytorch.org/whl/cpu"
CHI_MUC_TORCH_CUDA = "https://download.pytorch.org/whl/cu126"

#: **SỐ ĐO 20/08/2026, KHÔNG ƯỚC** (`_do_nhan_ban_tai.py` -> `_kq_nhan_ban_
#: tai.json`): `pip install --dry-run --report` bằng CHÍNH python của venv
#: VieNeu (3.12.10) rồi **HTTP HEAD** trên đúng wheel pip chọn. Lệnh dry-run
#: dựng giống hệt lệnh `cai_nhan_ban()` chạy — đo một lệnh rồi cài lệnh KHÁC
#: thì con số vô nghĩa.
#:     cpu    11 gói = **126,3 MB**   (torch 2.13.0+cpu   116,3 · torchaudio 0,3)
#:     cu126  11 gói = **2.485,6 MB** (torch 2.13.0+cu126 2.474,4 · torchaudio 1,4)
#: Chênh **19,7 lần**. Vì vậy nhãn PHẢI nói đúng bản SẼ tải (cổng 71 CA 4:
#: repo này đã có lỗi nút ghi 155 MB mà hộp xác nhận doạ 2 GB).
MB_NB_CPU = 126.3
MB_NB_CUDA = 2485.6

#: Cần trống bao nhiêu mới cho tải. Ổ C của anh Hùng đã đầy 100% một lần
#: (30/07) và hậu quả là **studio.db VỠ** — tải 2,5 GB vào ổ gần đầy là mở lại
#: đúng cửa đó. Bung ra đĩa lớn hơn lượng tải (torch bản cpu tải 116 MB nhưng
#: nằm trên đĩa **527 MB** — đo trên chính venv này), nên đòi ~2,2 lần.
_HE_SO_BUNG = 2.2


def xin_ban_cpu() -> bool:
    """Có ai cố ý đòi bản CPU (nhỏ hơn 19,7 lần) không. KHÔNG BAO GIỜ NÉM.

    Để dành cho hai ca thật: mạng tính theo dung lượng, và lối ĐO (hộp cát của
    cổng/`_do_*` không nên kéo 2,5 GB). Bật thì `nhan_tai_nhan_ban()` tự đổi
    số theo — **nhãn luôn khớp đường sẽ đi**, kể cả ở lối đo.
    """
    return str(os.environ.get("BQ_NB_CPU", "")).strip() in ("1", "true", "True")


def co_gpu_nvidia() -> bool:
    """Máy có GPU NVIDIA dùng được không — hỏi `nvidia-smi`, **KHÔNG import
    torch**.

    Dùng lại `thay_giong.co_gpu_nvidia` để bốn nút tải không bao giờ chọn khác
    chỉ mục nhau. Vì sao không hỏi torch: hàm này chạy TRONG tiến trình app (đã
    nạp Qt), mà `import torch` ở đó là **ACCESS VIOLATION** chứ không phải lỗi
    bắt được — `try/except` không chặn nổi. Và dù bắt được cũng vô nghĩa: torch
    đang cài LÀ BẢN CPU nên hỏi nó "có CUDA không" thì đời nào cũng False, tức
    đúng vòng luẩn quẩn khiến máy có RTX 3060 mãi mãi tải bản CPU (cổng 71).

    KHÔNG BAO GIỜ NÉM. Đoán nhầm thì hậu quả cũng chỉ là tải gói to/nhỏ hơn —
    `_MA_DOC` vẫn tự quyết thiết bị lúc chạy.
    """
    try:
        from app.core import thay_giong as _tg
        return bool(_tg.co_gpu_nvidia())
    except Exception:  # noqa: BLE001
        pass
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=25, creationflags=_NO_WIN)
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except Exception:  # noqa: BLE001
        return False


def ban_cuda_se_tai() -> bool:
    """Lượt tải SẼ lấy bản CUDA hay không. MỘT chỗ quyết định duy nhất.

    Nhãn nút, tooltip, hộp xác nhận VÀ lệnh pip đều phải hỏi hàm này — ba chỗ
    tự đoán lấy là đúng lỗi cổng 58 (nút ghi 155 MB, hộp doạ 2 GB).
    """
    return (not xin_ban_cpu()) and co_gpu_nvidia()


def mb_nhan_ban() -> float:
    """Số MB nút này SẼ tải, theo đúng đường nó sẽ đi. Đọc lại MỖI LẦN GỌI
    (bài học `tg_so.duong_so`): cắm/rút GPU giữa phiên thì số phải đổi theo."""
    return MB_NB_CUDA if ban_cuda_se_tai() else MB_NB_CPU


def so_mb(mb: float) -> str:
    """`2485.6` -> `"2.486"`. Dấu nghìn kiểu Việt, ĐỔI RIÊNG CON SỐ.

    **ĐỪNG `.replace(",", ".")` trên CẢ CÂU** — nó ăn luôn dấu phẩy của câu
    tiếng Việt. Đo được ở chính lượt CHẠY THẬT đầu tiên của `cai_nhan_ban`
    (`_do_cai_nhan_ban.py`): dòng tiến độ ra *"(khoảng 126 MB. tải 1 lần)"*.
    `giong_kokoro.dau_chua_tai` đã ghi đúng bài học này ("một lần, dùng chung"
    -> "một lần. dùng chung") mà HAI chỗ khác trong cùng file đó vẫn còn lỗi —
    nên ở đây làm MỘT hàm, và mọi nơi đọc số đều gọi nó.
    """
    return f"{mb:,.0f}".replace(",", ".")


def _goi_nhan_ban() -> tuple[str, ...]:
    """Gói mà đường nhân bản cần — NGUỒN DUY NHẤT là `nhan_ban_giong`.

    Chép lại danh sách sang đây là dựng bản sao thứ hai: lần thêm gói kế tiếp
    (`torch` -> lộ `torchaudio` là chuyện ĐÃ xảy ra) sẽ sửa một bản và bỏ bản
    kia, rồi nút cài thiếu gói mà nhãn vẫn khoe đủ.
    """
    try:
        from app.core.nhan_ban_giong import _CAN_CHO_NHAN_BAN
        return tuple(_CAN_CHO_NHAN_BAN)
    except Exception:  # noqa: BLE001
        return ("torch", "torchaudio")


def thieu_nhan_ban() -> list[str]:
    """Còn thiếu gì thì đường NHÂN BẢN mới chạy. **Đây là khoá nút phải bám.**

    Chỉ gọi lại `nhan_ban_giong.thieu_de_nhan_ban(MAY_VIENEU)` — CỐ Ý không tự
    dò lần thứ hai: hai bộ dò là hai câu trả lời, và cái nút bám sẽ là cái
    KHÔNG khớp nhãn mà người dùng đang đọc. KHÔNG BAO GIỜ NÉM.
    """
    try:
        from app.core.nhan_ban_giong import MAY_VIENEU, thieu_de_nhan_ban
        return list(thieu_de_nhan_ban(MAY_VIENEU))
    except Exception:  # noqa: BLE001
        return ["không dò được"]


def nhan_tai_nhan_ban(thieu: Optional[list[str]] = None) -> str:
    """Nhãn nút tải ĐÚNG với đường sẽ đi VÀ đúng với tình trạng hiện tại.

    Ba trạng thái phải trông KHÁC NHAU, nếu không người dùng đọc sai việc mình
    đang làm:
      · **chưa có gì** -> "Tải phần nhân bản giọng (torch, torchaudio — ...)"
      · **CÀI DỞ** (lượt trước đứt mạng, còn 1 trong 2) -> "Cài tiếp phần còn
        thiếu (torchaudio ...)". Ghi "Tải phần nhân bản" lúc này là nói sai:
        người dùng tưởng chưa có gì và tưởng phải tải lại từ đầu (đúng lý do
        `thay_giong.NHAN_CAI_TIEP` tồn tại).
      · **chưa có cả bộ VieNeu** -> nút này KHÔNG giải được, phải nói ra chứ
        đừng để bấm rồi báo lỗi.
    Số MB lấy từ `mb_nhan_ban()` — CÙNG một phép đo với tooltip và hộp xác nhận.

    **CA CÀI DỞ VẪN GHI ĐỦ SỐ MB, và đó là ĐÚNG chứ không phải quên:** lệnh cài
    có `--ignore-installed` nên pip giải lại và tải lại **TOÀN BỘ** danh sách,
    không phải chỉ cái còn thiếu (cổng 58 đo đúng vậy: cờ này khiến pip giải
    lại cả 33 gói vào `_lib`). Ghi "1,4 MB" cho ca thiếu `torchaudio` là hứa
    một lượt tải không tồn tại.
    """
    goi = _goi_nhan_ban()
    thieu = list(thieu if thieu is not None else thieu_nhan_ban())
    la_goi = [t for t in thieu if t in goi]
    # Thiếu thứ KHÔNG phải torch/torchaudio = thiếu chính bộ VieNeu (hoặc bộ dò
    # hỏng). Nút này chỉ cài được torch nên phải nói thẳng, đừng hứa.
    if thieu and not la_goi:
        return "Chưa có bộ giọng VieNeu — tải bộ đó trước"
    mb = so_mb(mb_nhan_ban())
    cuda = ban_cuda_se_tai()
    # Nói kèm "CHƯA ĐO có nhanh hơn" khi đi đường CUDA: Demucs có số đo 9,28x
    # để hứa, đường nhân bản của VieNeu thì **chưa ai đo GPU** — hứa nhanh mà
    # không có số là đúng thứ repo này cấm (khuôn `giong_kokoro.NHAN_TAI_CUDA`).
    duoi = (f"bản GPU khoảng {mb} MB — CHƯA ĐO có nhanh hơn" if cuda
            else f"khoảng {mb} MB")
    if la_goi and len(la_goi) < len(goi):
        return f"Cài tiếp phần còn thiếu ({', '.join(la_goi)} — {duoi})"
    return f"Tải phần nhân bản giọng ({', '.join(goi)} — {duoi})"


def vi_sao_khong_cai_nhan_ban() -> str:
    """"" = cài được. Khác rỗng = LÝ DO, để nút xám còn nói được vì sao.

    Nút xám không một lời là câu đố (bài học cổng 58/16/51) — mà đây là ca RẤT
    dễ gặp: bản `.exe` không mang Python, máy nhân viên có thể chưa cài.
    """
    if not _python_vieneu()[0]:
        return ("Máy này chưa có bộ giọng VieNeu nên chưa có môi trường để cài "
                "phần nhân bản vào. Tải bộ giọng Việt VieNeu trước.")
    if not _python_he_thong():
        return ("Máy này không có Python 3 nên app không tự tải được: cài "
                "Python 3 (python.org) rồi bấm lại, hoặc copy thư mục "
                "_giong_vieneu từ máy đã cài sang.")
    return ""


def _dia_trong_mb(d: Path) -> float:
    """MB trống của ổ chứa `d`. -1 = không hỏi được (thì ĐỪNG chặn)."""
    p = Path(d)
    for _ in range(6):
        try:
            return shutil.disk_usage(str(p)).free / 1024 / 1024
        except OSError:
            if p.parent == p:
                return -1.0
            p = p.parent
    return -1.0


def tinh_trang_nhan_ban() -> dict:
    """{thieu, co, cai_duoc, vi_sao, nhan, mb_tai, cuda, python, thu_muc}.

    Một cửa cho UI đọc, để nhãn/nút/hộp xác nhận không ai tự dò lấy.
    """
    thieu = thieu_nhan_ban()
    vi_sao = vi_sao_khong_cai_nhan_ban()
    return {
        # `thieu` là khoá NÚT PHẢI BÁM. Bám "chạy được" thì trên máy dev (đã có
        # torch) nút BIẾN MẤT, không ai bấm, bản `.exe` mãi mãi thiếu — đúng
        # cái bẫy đã làm ra việc này (cổng 58 + hàng Kokoro).
        "thieu": thieu,
        "co": not thieu,
        "cai_duoc": not vi_sao,
        "vi_sao": vi_sao,
        "nhan": nhan_tai_nhan_ban(thieu),
        "mb_tai": mb_nhan_ban(),
        "cuda": ban_cuda_se_tai(),
        "python": _python_vieneu()[0],
        "thu_muc": str(thu_muc_vieneu()),
    }


#: Một lượt tải/cài duy nhất tại một thời điểm (user bấm 2 lần vẫn 1 lượt).
_KHOA_NB = threading.Lock()

# ---------------------------------------------------------------------------
# VÒNG TỰ DÒ — chấm dứt chuyện ĐOÁN danh sách gói
# ---------------------------------------------------------------------------
#: Trần số vòng. Hết trần thì trả `ok=False` nêu rõ còn thiếu gì, **KHÔNG lặp
#: vô tận**: mỗi vòng là một lượt pip có thể tải hàng trăm MB, và một vòng lặp
#: không trần trên đường mạng là cách treo máy anh Hùng cả đêm.
TRAN_VONG_DO = 6

#: Gói **KHÔNG BAO GIỜ** tự cài, dù lời lỗi có đòi đích danh. Lý do ghi ngay
#: cạnh vì người sau sẽ hỏi "sao không cài nốt cho xong":
_CHAN_TU_DO: dict[str, str] = {
    "gradio": "giao diện web, không dính gì tới một lượt ĐỌC TIẾNG",
    "lmdeploy": "máy chủ suy luận, kéo về là gãy lượt cài",
    "llama_cpp": "llama-cpp-python KHÔNG build được trên Windows",
    "triton": "triton KHÔNG build được trên Windows",
    "triton_windows": "triton-windows KHÔNG build được trên Windows",
    "fitz": "PyMuPDF là bộ đọc PDF",
    "pymupdf": "bộ đọc PDF",
}

#: tên-IMPORT khác tên-PIP. Bảng NHỎ và chỉ chứa ca ĐÃ GẶP hoặc chắc chắn —
#: không biết thì cứ thử ĐÚNG TÊN rồi báo thẳng khi pip trả mã khác 0 (đoán bừa
#: một tên pip là cài về một gói LẠ mang đúng tên đó, tệ hơn hẳn báo lỗi).
_TEN_PIP: dict[str, str] = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python-headless",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "soxr": "soxr",
    "regex": "regex",
    "hf_hub": "huggingface-hub",
    "huggingface_hub": "huggingface-hub",
}

#: Bóc tên gói khỏi lời lỗi. Chỉ nhận tên HỢP LỆ — lời lỗi là chuỗi từ tiến
#: trình con, đưa thẳng vào dòng lệnh pip là một cửa tiêm lệnh.
_RE_THIEU = re.compile(r"No module named ['\"]([A-Za-z0-9_.\-]+)['\"]")


def _ten_thieu(loi: str) -> str:
    """Tên gói còn thiếu, bóc từ ``ModuleNotFoundError``. "" nếu không thấy.

    Lấy **gói GỐC** (``a.b.c`` -> ``a``): pip cài theo gói phát hành, không cài
    theo module con. Và chỉ nhận ``[A-Za-z0-9_.\\-]+`` — xem ``_RE_THIEU``.
    """
    m = _RE_THIEU.search(str(loi or ""))
    if not m:
        return ""
    goc = m.group(1).split(".")[0].strip()
    return goc if re.fullmatch(r"[A-Za-z0-9_\-]+", goc) else ""


def _ten_pip(ten: str) -> str:
    """Tên để đưa cho pip. Không biết thì trả ĐÚNG TÊN đã bóc được."""
    return _TEN_PIP.get(ten, _TEN_PIP.get(ten.lower(), ten))


def _bi_chan(ten: str) -> str:
    """Lý do KHÔNG tự cài gói này ("" = cứ cài)."""
    t = ten.lower().replace("-", "_")
    for k, v in _CHAN_TU_DO.items():
        if t == k or t.startswith(k):
            return v
    return ""


def _mau_thu(d: Path) -> str:
    """Sinh WAV mẫu vài giây bằng ffmpeg để CÓ CÁI mà nhân bản. "" nếu hỏng.

    **KHÔNG đòi mẫu của người dùng**: lượt cài phải tự chứng minh được là nó
    chạy, ngay lúc bấm, không chờ ai đưa file.

    ``duration=`` nằm TRONG biểu thức lavfi, **cố ý không dùng `-t`**:
    ``-t`` là tuỳ chọn ĐẦU VÀO và đặt sai chỗ thì nguồn lavfi ghi VÔ HẠN —
    lỗi đó đã làm đầy ổ C 420 GB một lần (115 MB/s). Dạng này có biên cứng.
    """
    ra = d / "mau_thu.wav"
    try:
        p = subprocess.run(
            [_ffmpeg_vn(), "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "sine=frequency=210:duration=4",
             "-ac", "1", "-ar", "24000", str(ra)],
            capture_output=True, text=True, timeout=120,
            creationflags=_NO_WIN)
    except Exception:  # noqa: BLE001
        return ""
    # ffmpeg TRẢ MÃ 0 MÀ FILE RỖNG là chuyện đã xảy ra nhiều lần trong repo
    # này -> kiểm FILE, không tin mã thoát.
    if p.returncode != 0 or not ra.is_file() or ra.stat().st_size < 2048:
        return ""
    return str(ra)


def _ffmpeg_vn() -> str:
    """ffmpeg đóng kèm app, lùi về tên trần nếu không có."""
    p = Path(__file__).resolve().parents[2] / "bin" / "ffmpeg.exe"
    return str(p) if p.exists() else "ffmpeg"


def do_wav(p: str | Path) -> dict:
    """ĐỘ DÀI + RMS của một WAV, đọc mẫu THẲNG. ``{giay, rms, co_tieng}``.

    ═══ VÌ SAO KHÔNG TIN ``doc_loat`` TRẢ True ═══
    ``doc_loat`` trả True nghĩa là *"tiến trình chạy xong, file có tồn tại"*.
    Nó **không** trả lời *"file có TIẾNG không"*. Cả repo này đã bị đúng cái
    khoảng cách đó cắn: ``ffmpeg`` trả mã 0 mà file 0 KiB (app tưởng xuất xong
    rồi xoá gốc), và bộ 28 giọng Kokoro phải đọc mẫu THẲNG mới biết giọng nào
    câm. Nên bằng chứng cuối cùng của lượt cài là **hai con số ở đây**.

    RMS tính trên mẫu 16-bit; định dạng khác -> trả rms 0 và ``co_tieng`` theo
    độ dài, ĐỪNG bịa số (bịa một lời khai TỐT cũng là bịa).
    """
    ra = {"giay": 0.0, "rms": 0.0, "co_tieng": False}
    try:
        with wave.open(str(p), "rb") as w:
            fr = w.getframerate() or 0
            n = w.getnframes()
            ra["giay"] = round((n / float(fr)) if fr else 0.0, 3)
            if w.getsampwidth() == 2 and n:
                a = array.array("h")
                a.frombytes(w.readframes(n)[: (n * w.getnchannels()) * 2])
                if len(a):
                    ra["rms"] = round(
                        (sum(float(x) * x for x in a) / len(a)) ** 0.5
                        / 32768.0, 5)
    except Exception:  # noqa: BLE001
        return ra
    # Sàn 0,001: bộ 28 giọng Kokoro đo được thấp nhất 0,02967 nên 0,001 là
    # "có tín hiệu" chứ không phải "đọc hay", đúng việc cần ở đây.
    ra["co_tieng"] = bool(ra["giay"] >= 0.3 and ra["rms"] >= 0.001)
    return ra


def _doc_thu_nhan_ban(vpy: Path, mau: str, dich: Path,
                      han_giay: int = 900) -> dict:
    """ĐỌC THẬT một câu qua đường NHÂN BẢN. ``{ok, loi, giay, rms}``.

    ═══ VÌ SAO PHẢI ĐỌC THẬT, KHÔNG PHÉP DÒ NÀO THAY ĐƯỢC ═══
    Đo trên máy anh Hùng 20/08/2026: trên chính venv đang thiếu
    ``transformers``, cả ``import vieneu`` LẪN ``import vieneu.v3turbo`` đều
    **THÀNH CÔNG**. Gói nạp ``transformers`` **LƯỜI** — chỉ khi đường nhân bản
    (``ref_audio=``) chạy. Nên mọi phép dò tĩnh đều nói "đủ" trong khi lượt đọc
    thật sẽ gãy, và đó đúng là cách danh sách gói đoán tay cứ thiếu: vá 2 tên
    thì lộ tên thứ 3.
    """
    t0 = time.time()
    # Khuôn item ĐÚNG BẰNG khuôn `_doc` dựng: `{"i", "text", "raw"}`. Sai khoá
    # ở đây là tiến trình con ném `KeyError` rồi vòng tự dò đọc lời lỗi đó
    # thành "thiếu gói" — cổng phải bắt được chuyện này (mục 13).
    items = [{"i": 0, "text": "Xin chào, đây là câu thử.", "raw": str(dich)}]
    # ĐÚNG MỘT trong hai đường: đường NHÂN BẢN là `voice=""` +
    # `ref_audio=<file mẫu>`. Truyền mã `vnb:...` vào ô `voice` là đi đường
    # giọng DỰNG SẴN — đường đó KHÔNG đụng torch nên lượt tự dò sẽ xanh oan
    # (xem "BẪY SỐ 1" ở đầu file).
    ket = _chay_vieneu(items, str(vpy), "", mau, han_giay, None)
    # `or ""` -> `Path("")` = `WindowsPath('.')` = THƯ MỤC ĐANG LÀM VIỆC; đúng
    # cái đã xoá sạch cây mã một lần (xem `_don`). Kiểm chuỗi TRƯỚC khi dựng
    # Path, đừng dựa vào chốt bên trong `_don` — nó là lớp chắn thứ hai.
    _sb = str(ket.get("_sandbox") or "").strip()
    if _sb:
        _don(Path(_sb))
    d = do_wav(dich)
    loi = str(ket.get("loi") or "")
    if ket.get("ok") and not d["co_tieng"]:
        loi = (f"chạy xong mà WAV KHÔNG CÓ TIẾNG (dài {d['giay']}s, "
               f"RMS {d['rms']}) — đừng coi là đã cài")
    return {"ok": bool(ket.get("ok")) and d["co_tieng"], "loi": loi,
            "giay": d["giay"], "rms": d["rms"],
            "phut": round(time.time() - t0, 1)}


def cai_nhan_ban(on_progress: Optional[Callable[[float, str], None]] = None,
                 han_giay: int = 7200,
                 ban_cuda: Optional[bool] = None) -> dict:
    """TẢI + CÀI `torch` + `torchaudio` vào venv VieNeu. **CHỈ khi NGƯỜI DÙNG
    BẤM.**

    Trả `{ok, loi, giay, thieu, venv, cuda, chi_muc, mb_tai, nhat_ky}`.
    **KHÔNG BAO GIỜ NÉM** — hỏng thì `ok=False` + `loi` + ghi
    `logs/giong_vieneu_<ngày>.log`, đúng như 4 hàm cài kia.

    ═══ CÀI VÀO VENV CỦA VIENEU, KHÔNG BAO GIỜ VÀO `.venv` CỦA APP ═══
    `.venv` là môi trường anh Hùng đang chạy sản xuất 300 kênh. Một lượt
    `pip install torch` khác bản có thể phá app ĐANG chạy — đúng lý do Demucs
    phải ở `_lib` (cổng 55), Kokoro ở venv riêng, OmniVoice ở `_giong_ngoai`.
    Thêm một lý do riêng ở đây: tiến trình đọc là `_python_vieneu()`, nên gói
    nằm ở chỗ khác thì **cài xong vẫn không chạy được**.

    ═══ `--ignore-installed` — CỜ QUYẾT ĐỊNH, ĐỪNG GỠ ═══
    pip coi gói đã có trong môi trường ĐANG CHẠY là "đã thoả mãn" rồi BỎ QUA,
    không chép vào đích. Đó đúng là cách `_lib` của Demucs thiếu torch mà máy
    dev vẫn báo "cài xong" (cổng 58: mọi gói CÓ trong `_lib` đều là gói `.venv`
    KHÔNG có, mọi gói THIẾU đều là gói `.venv` ĐÃ CÓ — một phép chia đôi hoàn
    hảo). Ở venv riêng thì ít thứ để bỏ qua, nhưng cờ này khiến kết quả **không
    phụ thuộc bản pip**, và `_lib` đã chứng minh hành vi cũ CÓ THẬT.

    ═══ HẬU KIỂM SO ĐƯỜNG DẪN, ĐỪNG HỎI "IMPORT ĐƯỢC KHÔNG" ═══
    Máy dev mượn `.venv` rồi báo cài xong trong khi đích rỗng — lỗi này đã cắn
    HAI lần (cổng 58 và bộ gióng hàng). Hậu kiểm ở đây dùng lại CHÍNH
    `thieu_de_nhan_ban()`, thứ dò bằng FILE CÓ TỒN TẠI KHÔNG trong
    site-packages của đúng python đó: cài xong nó phải trả `[]`.
    **Mừng theo nó, KHÔNG theo mã thoát của pip.**

    `ban_cuda=None` -> hỏi `ban_cuda_se_tai()`. Truyền tường minh chỉ để ĐO
    (hộp cát không nên kéo 2,5 GB) — và khi đó nhãn vẫn khớp vì hộp xác nhận
    của UI đọc `mb_nhan_ban()` chứ không đọc tham số này.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(max(0.0, min(1.0, p)), m)
            except Exception:  # noqa: BLE001
                pass

    t0 = time.time()
    venv = thu_muc_vieneu() / "venv"
    cuda = ban_cuda_se_tai() if ban_cuda is None else bool(ban_cuda)
    mb = MB_NB_CUDA if cuda else MB_NB_CPU
    ra: dict = {"ok": False, "loi": "", "giay": 0.0, "venv": str(venv),
                "cuda": cuda, "mb_tai": mb, "thieu": [], "nhat_ky": []}

    def xong(loi: str = "", **kw) -> dict:
        ra.update(kw)
        ra["loi"] = loi
        ra["ok"] = not loi
        ra["giay"] = round(time.time() - t0, 2)
        # Đọc `ra["venv"]` chứ KHÔNG đọc biến `venv`: biến đó là chỗ ĐỊNH cài,
        # còn `ra["venv"]` được đặt lại thành chỗ pip THẬT SỰ cài vào ngay sau
        # khi biết `vpy`. Xem `_venv_that` để biết vì sao chuyện này quan trọng.
        _ghi_log(("Cài phần nhân bản XONG vào " + str(ra.get("venv") or venv))
                 if not loi else ("Cài phần nhân bản HỎNG: " + loi[:300]))
        return ra

    try:
        # ---- 0. có môi trường để cài vào chưa ----
        # KHÔNG tự dựng venv ở đây: dựng xong mà không có `vieneu` thì
        # `thieu_de_nhan_ban` vẫn trả danh sách của VieNeu -> hậu kiểm HỎNG và
        # lời lỗi nói về torch trong khi thứ thiếu là cả bộ đọc. Nói thẳng.
        py = _python_vieneu()[0]
        if not py:
            return xong(vi_sao_khong_cai_nhan_ban()
                        or "Chưa có môi trường VieNeu để cài vào.")
        vpy = Path(py)
        if not vpy.is_file():
            return xong(f"Không thấy python của VieNeu ở {vpy}")
        # CHỖ THẬT SỰ ĐƯỢC CÀI VÀO — đặt NGAY khi biết `vpy`, để mọi lời log và
        # mọi lời lỗi từ đây trở đi nêu đúng thư mục pip ghi vào. Máy anh Hùng
        # chạy VieNeu từ `%TEMP%\bq_giong8\venv` nên chỗ chuẩn KHÔNG tồn tại;
        # log cũ nêu chỗ chuẩn và làm chẩn đoán đi sai hướng.
        venv = _venv_that(vpy)
        ra["venv"] = str(venv)

        # ---- 1. đĩa TRƯỚC KHI TẢI ----
        can = mb * _HE_SO_BUNG
        trong = _dia_trong_mb(venv)
        if 0 <= trong < can:
            return xong(
                f"Ổ đĩa chứa {venv} chỉ còn {so_mb(trong)} MB trống, cần "
                f"khoảng {so_mb(can)} MB (tải {so_mb(mb)} MB rồi bung ra đĩa "
                "còn to hơn: bản cpu tải 126 MB mà venv phình 11,5 -> 603,7 MB "
                "= +592 MB, ĐO THẬT). Dọn bớt đĩa rồi bấm lại.")

        if not _KHOA_NB.acquire(blocking=False):
            return xong("Đang tải rồi — đợi lượt này xong.")
        try:
            goi = _goi_nhan_ban()
            chi_muc = CHI_MUC_TORCH_CUDA if cuda else CHI_MUC_TORCH_CPU
            ra["chi_muc"] = chi_muc
            # `--extra-index-url` (KHÔNG `--index-url`): ép cả lượt vào chỉ mục
            # của pytorch là hỏng phép giải khi gói phụ thuộc không có ở đó
            # (bài học `cai_demucs`). Vẫn ra bản đúng vì `2.13.0+cu126` >
            # `2.13.0` theo PEP 440 — ĐÃ KIỂM bằng `--dry-run --report`: chỉ
            # mục cpu ra `torch==2.13.0+cpu`, cu126 ra `torch==2.13.0+cu126`.
            args = [str(vpy), "-m", "pip", "install", "--no-input",
                    "--disable-pip-version-check", "--upgrade",
                    "--ignore-installed",
                    "--extra-index-url", chi_muc, *goi]
            # `so_mb()` đổi dấu nghìn RIÊNG CON SỐ. Bản đầu `.replace(",",
            # ".")` cả câu và lượt CHẠY THẬT đầu tiên in ra
            # *"(khoảng 126 MB. tải 1 lần)"* — dấu phẩy thành dấu chấm.
            prog(0.02, ("Máy có GPU NVIDIA — đang tải phần nhân bản bản CUDA "
                        f"(khoảng {so_mb(mb)} MB, tải 1 lần)..." if cuda else
                        f"Đang tải phần nhân bản (khoảng {so_mb(mb)} MB, tải "
                        "1 lần)..."))
            ma, log = _chay_theo_dong(args, han_giay, prog, 0.02, 0.90)
            ra["nhat_ky"] = log[-40:]
            if ma == -1:
                return xong(f"Tải quá {han_giay}s, đã dừng.")
            if ma != 0:
                return xong(f"pip trả mã {ma}: " + " | ".join(log[-4:]))

            # ---- 2. HẬU KIỂM bằng CHÍNH phép dò của bản `.exe` ----
            # `PathFinder`/`os.scandir` nhớ nội dung thư mục theo mtime mà pip
            # vừa ghi vào -> phải xoá bộ nhớ đó, không thì lượt kiểm ngay sau
            # khi cài vẫn thấy thư mục như lúc chưa cài rồi báo THIẾU oan.
            prog(0.93, "Đang kiểm lại từng gói...")
            import importlib
            importlib.invalidate_caches()
            thieu = thieu_nhan_ban()
            ra["thieu"] = thieu
            if thieu:
                return xong(
                    "pip trả mã 0 nhưng những gói này KHÔNG nằm trong "
                    + str(_venv_that(vpy)) + ": " + ", ".join(thieu)
                    + ". Đừng coi là đã cài — giọng nhân bản vẫn sẽ lùi về "
                      "giọng thường.")

            # ---- 3. VÒNG TỰ DÒ: ĐỌC THẬT, ĐỪNG ĐOÁN DANH SÁCH GÓI ----
            # Hậu kiểm tĩnh ở bước 2 chỉ nói *"5 gói tôi BIẾT đều có mặt"*. Nó
            # KHÔNG nói được *"đọc có ra tiếng không"* — và đo trên máy anh Hùng
            # thì `import vieneu` lẫn `import vieneu.v3turbo` **đều thành công**
            # trong khi `transformers` đang thiếu, vì gói nạp nó LƯỜI (chỉ khi
            # `ref_audio=` chạy). Nên chỉ có ĐỌC THẬT nói thật, và đó là lý do
            # danh sách đoán tay cứ thiếu: vá 2 tên thì lộ tên thứ 3.
            them: list[str] = []
            vong = 0
            with tempfile.TemporaryDirectory(prefix="bq_docthu_") as _td:
                tmp = Path(_td)
                mau = _mau_thu(tmp)
                if not mau:
                    # KHÔNG coi là hỏng cả lượt cài: gói đã nằm đúng chỗ, chỉ là
                    # lượt tự kiểm không dựng nổi file mẫu (thiếu ffmpeg). Nói
                    # thẳng ra thay vì im lặng mừng.
                    _ghi_log("Vòng tự dò BỎ QUA: ffmpeg không dựng được WAV mẫu")
                    prog(1.0, "Đã cài xong (chưa tự đọc thử được — thiếu "
                              "ffmpeg).")
                    return xong("", tu_do=them, vong=0, doc_thu="")
                while vong < TRAN_VONG_DO:
                    vong += 1
                    prog(0.94, f"Đang đọc thử để kiểm tra thật (vòng {vong})...")
                    kq = _doc_thu_nhan_ban(vpy, mau, tmp / f"thu{vong}.wav")
                    ra["doc_thu"] = kq
                    if kq["ok"]:
                        _ghi_log(f"Vòng tự dò: ĐỌC THẬT ĐƯỢC ở vòng {vong} "
                                 f"(WAV {kq['giay']}s · RMS {kq['rms']}), "
                                 f"đã cài thêm: {them or 'không gói nào'}")
                        break
                    ten = _ten_thieu(kq["loi"])
                    if not ten:
                        # Hỏng vì lý do KHÁC (hết RAM, model chưa tải, ...) ->
                        # đừng cài bừa thêm gói, nói đúng cái lỗi đọc được.
                        _ghi_log(f"Vòng tự dò vòng {vong}: hỏng KHÔNG phải do "
                                 f"thiếu gói -> {kq['loi'][:200]}")
                        return xong(
                            "Đã cài đủ danh sách gói nhưng ĐỌC THẬT vẫn hỏng: "
                            + kq["loi"][:400], tu_do=them, vong=vong)
                    vi = _bi_chan(ten)
                    if vi:
                        _ghi_log(f"Vòng tự dò vòng {vong}: CHẶN `{ten}` ({vi})")
                        return xong(
                            f"Đường nhân bản đòi `{ten}` mà gói đó nằm trong "
                            f"danh sách CHẶN ({vi}). Không tự cài.",
                            tu_do=them, vong=vong)
                    goi_moi = _ten_pip(ten)
                    _ghi_log(f"Vòng tự dò vòng {vong}: thiếu `{ten}` -> "
                             f"cài `{goi_moi}` vào {venv}")
                    prog(0.95, f"Còn thiếu {goi_moi} — đang cài (vòng {vong})...")
                    ma2, log2 = _chay_theo_dong(
                        [str(vpy), "-m", "pip", "install", "--no-input",
                         "--disable-pip-version-check", "--ignore-installed",
                         "--extra-index-url", chi_muc, goi_moi],
                        han_giay, prog, 0.95, 0.99)
                    if ma2 != 0:
                        return xong(
                            f"Đường nhân bản còn thiếu `{ten}` mà pip trả mã "
                            f"{ma2} khi cài `{goi_moi}`: "
                            + " | ".join(log2[-3:]),
                            tu_do=them, vong=vong)
                    them.append(goi_moi)
                    importlib.invalidate_caches()
                else:
                    # Hết trần -> KHÔNG mừng. Nêu rõ còn thiếu gì.
                    con = _ten_thieu(str(ra.get("doc_thu", {}).get("loi", "")))
                    _ghi_log(f"Vòng tự dò HẾT TRẦN {TRAN_VONG_DO} vòng, "
                             f"đã cài {them}, còn thiếu {con or '(không rõ)'}")
                    return xong(
                        f"Đã thử {TRAN_VONG_DO} vòng mà đường nhân bản vẫn "
                        f"chưa đọc được — còn thiếu `{con or 'không rõ'}`. "
                        f"Đã tự cài: {', '.join(them) or 'không gói nào'}.",
                        tu_do=them, vong=vong)

            ra["tu_do"] = them
            ra["vong"] = vong
            prog(1.0, "Đã cài xong phần nhân bản giọng — đã đọc thử ra tiếng.")
            return xong("")
        finally:
            _KHOA_NB.release()
    except Exception as e:  # noqa: BLE001 - nút bấm KHÔNG được phép ném
        return xong(f"{type(e).__name__}: {e}")


def _chay_theo_dong(cmd: list[str], han: int,
                    prog: Optional[Callable[[float, str], None]] = None,
                    lo: float = 0.0, hi: float = 0.9,
                    nhip: float = 900.0) -> tuple[int, list[str]]:
    """Chạy lệnh, ĐỌC TỪNG DÒNG để còn báo tiến độ. (mã thoát, nhật ký).

    `-1` = quá hạn (đã giết). Không biết trước tổng dung lượng nên % chỉ là
    dấu hiệu "đang chạy" — nhưng KHÔNG có nó thì thanh tiến độ đứng im ở 1%
    suốt vài phút, đúng cái anh Hùng đã kêu ("ấn chạy thì chỉ hiện thanh tiến
    trình, không hiện gì cả").
    """
    log: list[str] = []
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", bufsize=1,
                             creationflags=_NO_WIN)
    except OSError as e:
        return 1, [str(e)]
    han_lo = time.time() + han
    n = 0
    try:
        for dong in p.stdout or ():
            dong = dong.rstrip()
            if dong:
                log.append(dong)
                n += 1
                if prog:
                    prog(min(hi, lo + n / nhip), dong[-110:])
            if time.time() > han_lo:
                p.kill()
                return -1, log
    finally:
        try:
            p.wait(timeout=60)
        except Exception:  # noqa: BLE001
            p.kill()
    return int(p.returncode or 0), log


def _chay_lenh(cmd: list[str], han: int) -> tuple[int, str]:
    """Mọi `subprocess` đều có `timeout` — luật của repo."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_NO_WIN, timeout=han)
    except subprocess.TimeoutExpired:
        return 1, f"chạy quá {han}s, đã dừng"
    except OSError as e:
        return 1, str(e)
    return r.returncode, (r.stderr or "") + (r.stdout or "")


# ---------------------------------------------------------------------------
# Tiến trình con — SCRIPT ĐỘC LẬP, không `-m <module>`
# ---------------------------------------------------------------------------
#: Không dùng `-m app.core...`: bản `.exe` không chạy được và không có cây mã
#: nguồn để `-m` bám vào (bài học cổng 55). Việc và kết quả đi qua FILE JSON
#: chứ không qua dòng lệnh — chữ Việt trên dòng lệnh Windows là một đường vỡ
#: bảng mã không cần thiết.
#:
#: **HAI DÒNG QUAN TRỌNG NHẤT CỦA CẢ FILE NÀY** nằm trong `kw` bên dưới:
#: nhân bản đi bằng **`ref_audio=`**, giọng dựng sẵn đi bằng **`voice=`**, và
#: **KHÔNG BAO GIỜ truyền cả hai** — xem khối "BẪY SỐ 1" ở đầu file.
_MA_DOC = r'''
import json, os, sys, time

job_path = sys.argv[1]
with open(job_path, "r", encoding="utf-8") as f:
    J = json.load(f)


def bao(p, m):
    sys.stdout.write("BQP\t%.4f\t%s\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model doc...")
    import numpy as np
    import soundfile as sf
    from vieneu import Vieneu

    t0 = time.time()
    tts = Vieneu()
    t_nap = time.time() - t0
    sr = int(getattr(tts, "sample_rate", 48000))

    # KIEM LAI GIONG CO THAT KHONG truoc khi doc ca loat. `infer` nem
    # ValueError neu ten giong khong co trong ban nay -> bat som de bao dung
    # benh, thay vi chet giua me.
    co_giong = []
    try:
        co_giong = [k for _d, k in tts.list_preset_voices()]
    except Exception:
        co_giong = []
    if J.get("voice") and co_giong and J["voice"] not in co_giong:
        raise ValueError("Ban vieneu nay khong co giong %r (co: %d giong)"
                         % (J["voice"], len(co_giong)))

    kw = {}
    if J.get("ref_audio"):
        # NHAN BAN. Tham so DUNG la `ref_audio` — `use_ref_codes` la co BOOL,
        # nhet duong dan vao do chi lam no True (bay luot 4 = duong tinh gia).
        kw["ref_audio"] = J["ref_audio"]
    elif J.get("voice"):
        kw["voice"] = J["voice"]
    kw["apply_watermark"] = bool(J.get("watermark", True))

    items = J["items"]
    ra = []
    t1 = time.time()
    for i, it in enumerate(items):
        a = tts.infer(text=it["text"], **kw)
        a = np.asarray(a, dtype="float32").reshape(-1)
        sf.write(it["raw"], a, sr)
        ra.append({"i": it["i"], "p": it["raw"],
                   "giay": round(len(a) / float(sr), 4)})
        bao(0.10 + 0.85 * (i + 1) / max(1, len(items)),
            "Doc cau %d/%d" % (i + 1, len(items)))
    t_gen = time.time() - t1

    ket = {"ok": True, "nap": round(t_nap, 2), "gen": round(t_gen, 2),
           "sr": sr, "ra": ra, "so_giong": len(co_giong),
           "watermark": bool(getattr(tts, "watermarker", None)) and kw["apply_watermark"]}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\t" + json.dumps(ket) + "\n")
sys.stdout.flush()
'''


def _viet_runner() -> Path:
    """Ghi script chạy ra `<thu_muc>/_bq_vieneu_runner.py` (đè mỗi lượt)."""
    p = thu_muc_vieneu() / "_bq_vieneu_runner.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_MA_DOC, encoding="utf-8")
    return p


def _chay_vieneu(items: list[dict], py: str, voice: str, ref_audio: str,
                 han_giay: int,
                 on_msg: Optional[Callable[[str], None]]) -> dict:
    """Gọi tiến trình con đọc cả loạt. Trả dict kết quả (KHÔNG ném)."""
    runner = _viet_runner()
    sb = thu_muc_vieneu() / f"_job_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sb.mkdir(parents=True, exist_ok=True)
    job = sb / "job.json"
    job.write_text(json.dumps(
        {"items": items, "voice": voice, "ref_audio": ref_audio,
         "watermark": os.environ.get("BQ_VN_WATERMARK", "1").strip() != "0"},
        ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Trọng số nằm trong kho HF của MÁY, để riêng ra khỏi %TEMP% cùng lý do
    # với môi trường. Không ép offline: lần đầu phải tải thật.
    env.setdefault("HF_HOME", str(thu_muc_vieneu() / "hf"))

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
                    except Exception:  # noqa: BLE001
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
                return {"ok": False, "loi": "quá giờ (bỏ cuộc)",
                        "_sandbox": str(sb)}
        ma = p.wait(timeout=120)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "loi": f"{type(e).__name__}: {e}",
                "_sandbox": str(sb)}
    finally:
        if p is not None:
            _bo_gan_job(p)
    if not ket:
        ket = {"ok": False,
               "loi": f"mã thoát {ma}: " + (" | ".join(duoi[-4:]) or "không rõ")}
    ket["_sandbox"] = str(sb)
    return ket


def _gan_job(p) -> None:
    """Đăng ký tiến trình con để bấm Huỷ GIẾT ĐƯỢC nó (như Demucs).

    KHÔNG BAO GIỜ NÉM: module điều phối có thể chưa nạp (cổng test, đo đạc).
    """
    try:
        from app.queue.worker import register_job_proc
        register_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


def _bo_gan_job(p) -> None:
    try:
        from app.queue.worker import unregister_job_proc
        unregister_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Ép vừa khung — `rubberband`, KHÔNG dùng núm của model
# ---------------------------------------------------------------------------
def _tempo_tu_rate(rate: str) -> float:
    """`"+25%"` -> 1,25. Trả 1.0 nếu không đọc được."""
    try:
        s = str(rate or "").strip().rstrip("%")
        return max(0.25, min(4.0, 1.0 + float(s) / 100.0))
    except (TypeError, ValueError):
        return 1.0


def _ep_khung(nguon: Path, dich: Path, tempo: float) -> bool:
    """Ép `nguon` nhanh lên `tempo` lần rồi ghi ra `dich`. True = xong.

    DÙNG LẠI `thay_giong._co_gian_chuoi` chứ không viết chuỗi filter thứ hai:
    hàm đó đã canh sẵn chuyện ffmpeg máy nhân viên không có `rubberband` (lùi
    `atempo`, chia tầng khi > 2,0) và có công tắc `BQ_TG_RUBBERBAND=0` để đo
    A/B. Đẻ đường thứ hai là đẻ chỗ để hai đường lệch nhau.

    **KHÔNG dùng núm `temperature`/`max_new_frames` của model để ép nhanh** —
    lượt 7 đã đo trên OmniVoice: núm model trượt đích +2,5..+12,3% và làm đọc
    sai tăng vọt, còn `rubberband` cắt theo ĐỒNG HỒ nên trúng đích tuyệt đối.
    """
    from config import settings
    from app.core import thay_giong as _tg

    if abs(tempo - 1.0) < 1e-3:
        try:
            if dich.exists():
                dich.unlink()
            shutil.copyfile(nguon, dich)
            return True
        except OSError:
            return False
    try:
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(nguon), "-filter:a", _tg._co_gian_chuoi(tempo),
             "-c:a", "pcm_s16le", str(dich)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300, creationflags=_NO_WIN)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Ép khung hỏng ({nguon.name}): {type(e).__name__}: {e}")
        return False
    # **ffmpeg TRẢ MÃ 0 MÀ FILE RỖNG là chuyện đã xảy ra nhiều lần** trong
    # repo này -> luôn kiểm KÍCH THƯỚC + ĐỘ DÀI, đừng tin mã thoát.
    if r.returncode != 0 or not dich.exists() or dich.stat().st_size < 1024:
        _ghi_log(f"Ép khung hỏng ({nguon.name}): rc={r.returncode} "
                 f"{(r.stderr or '')[-200:]}")
        return False
    if dai_wav(dich) <= 0.02:
        _ghi_log(f"Ép khung ra file 0 giây ({dich.name}) -> bỏ")
        return False
    return True


def dai_wav(p: str | Path) -> float:
    """Độ dài WAV theo giây (0.0 nếu đọc không được). Không gọi ffprobe."""
    try:
        with wave.open(str(p), "rb") as w:
            fr = w.getframerate() or 0
            return (w.getnframes() / float(fr)) if fr else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------------------
# MỐC TỪNG CHỮ — GIÓNG HÀNG (bộ này KHÔNG trả mốc)
# ---------------------------------------------------------------------------
def _lay_moc(paths: list[str], texts: list[str], lang: str) -> list[list]:
    """Mốc `[[đầu, cuối, từ], ...]` cho từng câu, bằng GIÓNG HÀNG CƯỠNG BỨC.

    **VieNeu KHÔNG trả mốc — đây là sự thật ĐỌC ĐƯỢC TRONG MÃ GÓI, không phải
    phỏng đoán:** `v3turbo.infer()` trả về đúng `np.ndarray` sóng âm, và cả
    file `v3turbo.py` không có một khoá `timestamp`/`alignment`/`boundary`
    nào lọt ra ngoài.

    Nhưng khác OmniVoice ở chỗ **KHÔNG phải dò lại bằng máy nghe**: gióng hàng
    **không đoán chữ, nó ĐÃ BIẾT chữ** -> phủ gần đủ do cấu tạo, không tốn
    một lượt Groq nào, và lượt 9 đo được rung **8,5 ms** (edge-tts 13,5 ms).

    Thiếu bộ gióng hàng -> trả rỗng, KHÔNG bịa mốc và KHÔNG nổ: tiếng vẫn
    dùng được, chỉ là chữ không chạy theo lời (nhãn đã nói trước điều đó).
    """
    n = len(paths)
    if not _co_giong_hang():
        _ghi_log("Máy chưa có bộ gióng hàng -> KHÔNG có mốc từng chữ "
                 "(tiếng vẫn dùng được, chữ sẽ không chạy theo lời)")
        return [[] for _ in range(n)]
    try:
        from app.core import giong_hang as _gh
        return _gh.giong_hang_loat(paths, texts, lang=lang)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Gióng hàng hỏng ({type(e).__name__}: {e}) -> câu này "
                 f"KHÔNG có mốc")
        return [[] for _ in range(n)]


# ---------------------------------------------------------------------------
# CỬA CHÍNH — cùng hợp đồng với `piper_tts.doc_loat` / `giong_ngoai.doc_loat`
# ---------------------------------------------------------------------------
#: Đọc được bao nhiêu câu thì mới coi cả loạt là dùng được. Xem `doc_loat`.
TY_LE_TOI_THIEU = 1.0


def doc_loat(texts: list[str], paths: list[str], voice: str,
             on_done: Optional[Callable[[int], None]] = None,
             rate: str | list = "+0%",
             lang: str = "vi",
             lay_moc: bool = True,
             han_giay: int = 1800,
             on_msg: Optional[Callable[[str], None]] = None,
             ) -> tuple[list[bool], list[list]]:
    """Đọc cả LOẠT câu bằng VieNeu. Cùng hợp đồng `_synth_all_words`.

    Trả `(ok, words)`: `ok[i]` = câu i đọc được chưa · `words[i]` =
    `[[đầu, cuối, từ], ...]`, rỗng nếu không lấy được mốc chắc chắn.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả `ok` toàn `False` để nơi gọi lùi về
    edge-tts (`dubbing._synth_all_words`).

    ═══ ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE — VÌ SAO ALL-OR-NOTHING ═══
    Đọc được 18/20 câu rồi để 2 câu kia lùi edge-tts thì video ra **LẪN HAI
    GIỌNG** giữa chừng — đúng mệnh đề cổng 63 canh, và **mã thoát vẫn 0** nên
    không ai biết. Vì vậy chỉ cần MỘT câu không đọc được là trả `ok` toàn
    `False`: cả video một giọng edge-tts, xấu hơn nhưng ĐỀU.
    (`BQ_VN_TY_LE` hạ ngưỡng để đo/gỡ rối; đừng hạ trong sản xuất.)

    ═══ GOM CẢ LOẠT VÀO MỘT LƯỢT ═══
    Nạp model tốn hàng giây, nên gọi từng câu là mỗi câu trả lại từng ấy
    (đúng bài học `piper_tts.doc_loat` và `giong_hang_loat`). Đọc ở tốc độ TỰ
    NHIÊN một lượt, rồi ép từng câu bằng `rubberband`.
    """
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]
    if n == 0:
        return ok, words

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

    if not la_giong_vieneu(voice):
        _ghi_log(f"Mã giọng lạ {voice!r} -> LÙI về edge-tts")
        _xong_het()
        return ok, words

    tt = tinh_trang_vieneu()
    if not tt["co"]:
        _ghi_log(f"Chưa dùng được VieNeu (thiếu: {tt['thieu']}) -> LÙI về "
                 f"edge-tts")
        _xong_het()
        return ok, words
    if tt.get("o_tam"):
        # Chạy được, nhưng đang đứng trên đất mượn. Nói ra MỖI LƯỢT: im lặng
        # thì tới hôm mất mới biết, mà lúc đó triệu chứng lại là "giọng tự
        # nhiên biến khỏi combo" — không ai lần ra nguyên nhân.
        _ghi_log(f"CẢNH BÁO: môi trường VieNeu đang nằm trong thư mục TẠM "
                 f"({tt['o_tam']}). Một lượt dọn đĩa là mất. Chỗ đúng: "
                 f"{tt['thu_muc']}\\venv")

    if la_giong_nhan_ban(voice):
        mau = ten_giong(voice)
        if not mau or not Path(mau).is_file():
            _ghi_log(f"File mẫu nhân bản không có thật ({mau!r}) -> LÙI về "
                     f"edge-tts")
            _xong_het()
            return ok, words

    try:
        ok, words = _doc(texts, paths, voice, tt, rate, lang, lay_moc,
                         han_giay, on_msg)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"VieNeu hỏng ({type(e).__name__}: {e}) -> LÙI về edge-tts")
        ok, words = [False] * n, [[] for _ in range(n)]

    can = [i for i in range(n) if (texts[i] or "").strip()]
    duoc = [i for i in can if ok[i]]
    try:
        nguong = float(os.environ.get("BQ_VN_TY_LE", TY_LE_TOI_THIEU))
    except ValueError:
        nguong = TY_LE_TOI_THIEU
    if can and len(duoc) < nguong * len(can):
        _ghi_log(f"Chỉ đọc được {len(duoc)}/{len(can)} câu bằng {voice} -> "
                 f"BỎ CẢ LOẠT, lùi edge-tts (không để video lẫn hai giọng)")
        ok, words = [False] * n, [[] for _ in range(n)]

    _xong_het()
    return ok, words


def _doc(texts: list[str], paths: list[str], voice: str, tt: dict,
         rate: str | list, lang: str, lay_moc: bool, han_giay: int,
         on_msg: Optional[Callable[[str], None]],
         ) -> tuple[list[bool], list[list]]:
    """Thân của `doc_loat`. Có thể ném — `doc_loat` bắt."""
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]

    can = [i for i in range(n) if (texts[i] or "").strip()]
    if not can:
        return ok, words

    sb = thu_muc_vieneu() / f"_tam_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    (sb / "raw").mkdir(parents=True, exist_ok=True)
    items = [{"i": i, "text": (texts[i] or "").strip().replace("\n", " "),
              "raw": str(sb / "raw" / f"c{i:04d}.wav")} for i in can]

    # ĐÚNG MỘT trong hai đường — xem "BẪY SỐ 1" ở đầu file.
    nb = la_giong_nhan_ban(voice)
    ket = _chay_vieneu(items, tt["python"],
                       "" if nb else ten_giong(voice),
                       ten_giong(voice) if nb else "",
                       han_giay, on_msg)
    if not ket.get("ok"):
        _ghi_log(f"VieNeu đọc hỏng: {ket.get('loi')}")
        _don(sb)
        _don(Path(ket.get("_sandbox") or ""))
        return ok, words

    for r in ket.get("ra") or []:
        i = int(r.get("i", -1))
        if not (0 <= i < n):
            continue
        raw = Path(r.get("p") or "")
        # KHÔNG tin tiến trình con báo "ok" — ĐO lại file nó ghi ra. Cùng một
        # luật với "ffmpeg trả mã 0 mà file rỗng".
        if dai_wav(raw) <= 0.02:
            _ghi_log(f"VieNeu ghi ra file 0 giây cho câu {i} -> bỏ")
            continue
        r_i = (rate[i] if isinstance(rate, list) and i < len(rate)
               else (rate if isinstance(rate, str) else "+0%"))
        dich = Path(paths[i])
        dich.parent.mkdir(parents=True, exist_ok=True)
        if not _ep_khung(raw, dich, _tempo_tu_rate(r_i)):
            continue
        ok[i] = True

    if lay_moc:
        xong = [i for i in can if ok[i]]
        if xong:
            m = _lay_moc([paths[i] for i in xong],
                         [texts[i] for i in xong], lang)
            for k, i in enumerate(xong):
                if k < len(m):
                    words[i] = m[k]

    _ghi_log(f"VieNeu đọc {sum(1 for i in can if ok[i])}/{len(can)} câu bằng "
             f"{voice} · nạp {ket.get('nap')}s · sinh {ket.get('gen')}s · "
             f"{ket.get('sr')} Hz · watermark {ket.get('watermark')}")
    _don(sb)
    _don(Path(ket.get("_sandbox") or ""))
    return ok, words


def _don(d: Path) -> None:
    """Dọn thư mục tạm. KHÔNG BAO GIỜ NÉM (bài học rò `_seg_*`, cổng 42).

    ═══ CHỐT NÀY SINH RA TỪ MỘT TAI NẠN THẬT — 19/08/2026 ═══
    Bản đầu chép nguyên `giong_ngoai._don`:
    ``if d and str(d) and d.is_dir(): shutil.rmtree(d)``. **`Path("")` KHÔNG
    rỗng — nó là `WindowsPath('.')`**, tức THƯ MỤC ĐANG LÀM VIỆC: `str(d)` ra
    `'.'` (truthy), `is_dir()` ra True, rồi `rmtree('.')` **xoá sạch cây mã**.

    Đã xảy ra THẬT khi chạy cổng 79: cổng vá `_chay_vieneu` bằng một hàm trả
    dict KHÔNG có khoá `_sandbox` -> `ket.get("_sandbox") or ""` ->
    `Path("")`. Mất `.git` (chỉ còn `objects`), `.venv`, `bin`, `_lib`,
    `_giong_hang`, `_piper`, `_giong_ngoai`; repo phải dựng lại từ
    `.git/objects`.

    Và đây KHÔNG phải lỗi riêng của cổng — `giong_ngoai.py` **đang chạy sản
    xuất** có đúng lỗ đó ở nhánh QUÁ GIỜ (`_chay_ov` không đặt `_sandbox`),
    tức một lượt OmniVoice quá giờ là xoá thư mục làm việc. Đã vá cùng ngày.

    HAI LỚP CHẮN, cố ý thừa: mọi đường ra của `_chay_vieneu` đều đặt
    `_sandbox` (đường 1), và hàm này **CHỈ xoá thư mục nằm THẬT SỰ BÊN TRONG**
    `thu_muc_vieneu()` (đường 2). Đường 1 dễ bị một bản vá sau làm hỏng lại mà
    không ai thấy, nên đường 2 mới là chốt chịu lực.
    """
    try:
        if d is None or not str(d).strip():
            return
        p = Path(d).resolve()
        goc = thu_muc_vieneu().resolve()
        # `p == goc` cũng CẤM: hộp cát là thư mục CON; xoá cả gốc là xoá luôn
        # môi trường Python vừa tải về.
        if p == goc or goc not in p.parents:
            _ghi_log(f"TỪ CHỐI dọn {p} — nằm ngoài {goc}")
            return
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
