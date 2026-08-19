# -*- coding: utf-8 -*-
"""GIỌNG NGOÀI — OmniVoice (+ khung IndexTTS). LỰA CHỌN THÊM, KHÔNG THAY THẾ.

═══════════════════════════════════════════════════════════════════════════
ĐỌC TRƯỚC — ANH HÙNG ĐÃ BIẾT VÀ ĐÃ QUYẾT
═══════════════════════════════════════════════════════════════════════════
Hai điều đã trình bày rõ trước khi làm file này, anh Hùng vẫn bảo *"không
được OmniVoice vẫn oke mà, thêm hết vào cho tôi, với Index vào"*:

  1. **KHÔNG bộ nào có mốc từng chữ.** `generate()` của OmniVoice trả về
     **danh sách sóng âm, hết** (soi 45 file mã nguồn: không có
     `timestamp`/`alignment`/`word_time`/`boundary` nào lọt ra ngoài).
     Mốc phải **SUY RA bằng Groq chép ngược** — xem `_lay_moc_groq`. Sai số
     của máy dò CỘNG THÊM vào, không thay thế. Đây là lý do kỹ thuật khiến
     bộ này lùi một bậc so với edge-tts, bất kể giọng hay tới đâu.
  2. **Trọng số OmniVoice là CC-BY-NC = CẤM KIẾM TIỀN.** Nguyên văn model
     card gốc: *"Our code is released under the Apache 2.0 License. The
     pre-trained model is licensed under the CC-BY-NC due to constraints
     from its training data (e.g., Emilia)."* Kèm lớp thứ ba:
     `audio_tokenizer` = Boson Higgs Audio 2 (dẫn xuất Meta Llama 3), ngưỡng
     100.000 người dùng/năm + bắt buộc ghi công.
     -> Nhãn trong hộp chọn giọng **PHẢI ghi ra** (`nhan_giong`). Anh Hùng
     biết mình đang dùng gì, không phải nhớ.

VÌ THẾ: mặc định vẫn là **edge-tts**. Thiếu model/thiếu Python thì **LÙI ÊM**
về edge-tts và GHI LÝ DO vào log — KHÔNG được nổ. (Cùng luật với Piper, khác
luật Demucs: thiếu Demucs mà lùi là ra video HỎNG nên phải CHẶN; ở đây lùi ra
video ĐÚNG, chỉ khác giọng.)

═══════════════════════════════════════════════════════════════════════════
SỐ ĐO CỦA LƯỢT 7 (docs/GIONG_LUOT_7.md) — DÙNG LẠI, ĐỪNG ĐO LẠI
═══════════════════════════════════════════════════════════════════════════
  · **KHÔNG BỊA CHỮ**: thừa **0,0%** ở mọi thứ tiếng, mọi mức ép. Qua được
    án tử đã dùng để loại viXTTS (tiếng Trung 1,38× số chữ) và Chatterbox.
  · Một giọng đọc được **4 thứ tiếng** (Anh · Trung · Nhật · Việt).
  · Đọc đúng chữ (8 câu/thứ tiếng, arm edge CÙNG lượt Groq):
        EN  OV **2,0%** | edge 4,0%        JA  OV **11,8%** | edge 13,7%
        VI  OV  16,9%   | edge **6,8%**    ZH  OV  34,1%   | edge **12,6%**
    -> **Tiếng Việt nó sai gấp 2,5 lần edge-tts.** Nhãn phải nói ra.
  · Nhấn nhá 11 giọng thiết kế trải **2,16** nửa cung (edge-tts 17 giọng Mỹ:
    **3,31**) — hẹp hơn, cùng kết luận cũ về Chatterbox.
  · RTX 3060: VRAM **2,03 GiB** · nạp 5-31 s · EN 2,44× thời gian thật.

═══════════════════════════════════════════════════════════════════════════
ĐỘ KHỚP MỐC — ĐÃ ĐO 18/08/2026, VÀ PHÉP ĐO HIỂN NHIÊN NHẤT LÀ PHÉP ĐO SAI
═══════════════════════════════════════════════════════════════════════════
`_do_gn_moc.py` — 2 lượt ĐAN XEN có xoay thứ tự, 12 câu THẬT mỗi thứ tiếng,
4 thứ tiếng, arm đối chứng edge-tts chạy lại trên CÙNG corpus.

**BẪY SỐ 1 — ĐO BẰNG GROQ LÀ SO NÓ VỚI CHÍNH NÓ.** Piper suy mốc từ ĐỘ DÀI
WAV nên Groq là thước độc lập với nó (59,1 ms có nghĩa). OmniVoice thì mốc
**lấy thẳng từ Groq**, mà Groq lại **TIỀN ĐỊNH** (chép cùng file hai lần ra
mốc giống TỪNG CHỮ SỐ). Đo được đúng **0,0 ms trên cả 1.587 mốc / 4 thứ
tiếng** — một bảng điểm hoàn hảo cho một thứ chưa hề được kiểm. Ai nhìn con
số đó rồi kết luận "khớp hơn edge-tts 43,6 ms" là đã sập bẫy.

**BẪY SỐ 2 — MỌI THƯỚC LÀ MÁY NGHE ĐỀU THIÊN VỊ.** Thước thứ hai
(faster-whisper `medium`, trọng số KHÁC, chạy local) ra rung **50,6 ms** cho
OmniVoice so với **56,5 ms** của edge-tts, tức "OmniVoice tốt hơn". ĐỪNG TIN:
mốc OmniVoice do MÁY NGHE sinh ra nên nó mang sẵn cách cắt từ của máy nghe,
khớp với một máy nghe khác dễ hơn hẳn mốc lấy từ CHỮ GỐC của edge-tts. Dấu
hiệu lộ ra ngay ở cột `n`: cùng một corpus mà OmniVoice khớp **1.466** mốc
còn edge-tts chỉ **1.043**.

**THƯỚC DUY NHẤT KHÔNG THIÊN VỊ: `silencedetect`** (không máy nghe nào) — so
mốc chữ ĐẦU với lúc THẬT SỰ phát ra tiếng, đúng thước thứ ba cổng 67 đã dùng
để chặn một phép trừ sai 94 ms:

    RUNG mốc chữ đầu   edge-tts **15,9 ms**  ·  OmniVoice **236,0 ms**
    (Việt 2,6 / 42,8 · Anh 3,4 / 189,5 · Trung 5,1 / 148,5 · Nhật 17,6 / 506,2)
    chữ hiện MUỘN hơn tiếng >50 ms:  edge-tts **0,0%**  ·  OmniVoice **32,3%**

**VÀ CHỖ HỎNG NẶNG NHẤT KHÔNG PHẢI ĐỘ LỆCH — LÀ MỐC KHÔNG CÓ.** `_do_gn_phu.py`
đếm tỉ lệ chữ CÓ mốc (Groq nghe sai thì từ đó bị bỏ, không nội suy):

    PHỦ    Việt **34,6 – 56,3%**  ·  Anh 75,3 – 94,6%
           Trung 46,9 – 73,8%     ·  Nhật 29,3 – 35,2%      (3 lượt đo)

edge-tts phủ **100% do cấu tạo** (WordBoundary trả mọi từ). Tức với tiếng
Việt, **một phần ba tới hai phần ba số chữ không có mốc nào** — chỗ đó chữ
không chạy theo tiếng được.

**VÀ CON SỐ ĐÓ KHÔNG ỔN ĐỊNH: đo lại trên ĐÚNG cùng bộ file WAV ra 56,3% rồi
34,6%.** Groq tiền định trong hai cú gọi liền nhau (đã kiểm) nhưng qua các
lượt cách xa thì KHÔNG — nên đây là dải, không phải một con số, và **không vá
được bằng hằng số**. Ai lấy một lượt rồi báo một số là tự lừa mình.

**KẾT LUẬN PHẢI NÓI THẲNG: kém hơn edge-tts, kém hơn cả Piper** (Piper rung
59,1 ms / 42% muộn nhưng phủ đủ chữ). Vì vậy `CANH_BAO_CL_OV` ghi thẳng vào
nhãn hộp chọn giọng — đúng tiền lệ Piper, cổng 72 CA 7 canh.

═══════════════════════════════════════════════════════════════════════════
GIÓNG HÀNG CHỮA ĐƯỢC BỆNH PHỦ — ĐO 18/08/2026, VÀ ĐÂY LÀ SỐ
═══════════════════════════════════════════════════════════════════════════
`dubbing._synth_all_words` nay lấy mốc cho giọng ngoài bằng **gióng hàng
cưỡng bức** (`giong_hang.py`) khi máy có bộ đó. Gióng hàng **không đoán chữ,
nó ĐÃ BIẾT chữ** -> phủ gần đủ do cấu tạo, không phụ thuộc máy nghe.

**PHÉP ĐO PHẢI TÁCH ĐƯỢC "GIÓNG HÀNG TỐT" KHỎI "LƯỢT NÀY MODEL ĐỌC RÕ HƠN".**
Đây là chỗ suýt kết luận sai: `_do_gn_gh.py` (WAV sinh mới hôm nay) đo đường
Groq ra PHỦ tiếng Việt **99,4%** — trong khi nhãn đang ghi 30-56%. Chạy lại
`_do_gn_phu.py` trên bộ WAV CŨ thì vẫn ra **41,8% · 61,4%**. Cùng một hàm,
cùng một corpus, khác nhau đúng ở **mẻ tiếng**: OmniVoice KHÔNG TIỀN ĐỊNH,
lượt này đọc rõ lượt kia đọc ngọng, và Groq chép ngược ăn theo chuyện đó.
Tức **34-56% không phải hằng số của đường Groq, nó là hằng số của một mẻ đọc
kém** — ai đo một lượt rồi báo một số là tự lừa mình (mục trên đã cảnh báo,
nhưng lần này truy được NGUYÊN NHÂN chứ không chỉ ghi nhận dao động).

Vì vậy `_do_gn_cu.py` cho **hai đường lấy mốc chạy trên ĐÚNG MỘT BỘ FILE
TIẾNG** — bỏ hẳn nhiễu đó. Thước DUY NHẤT là `silencedetect`.

  bộ WAV CŨ (mẻ đọc kém, chính mẻ sinh ra con số 34-56%):

    PHỦ        Groq **52,5%**  ->  gióng hàng **98,6%**
       Việt      37,6 -> **98,9**   ·  Anh    79,0 -> **100,0**
       Trung     67,5 -> **96,8**   ·  Nhật   25,7 -> **98,7**
    RUNG chữ đầu  711,9 -> **90,4 ms**   ·  mốc[0] đúng từ đầu 45/96 -> 88/96
    GIÂY/mẻ 12 câu  32,49 -> **6,30**   (và KHÔNG tốn lượt Groq nào)

  bộ WAV MỚI (mẻ đọc tốt) — arm edge-tts chạy lại trên CÙNG corpus:

    PHỦ       edge 78,2*  ·  Groq 82,1  ->  gióng hàng **98,5%**
    RUNG      edge **15,7**  ·  Groq 250,4  ->  gióng hàng **119,2 ms**

  (*) edge 78,2% KHÔNG phải lỗi của edge-tts mà là **giới hạn của mẫu số**:
  PHỦ đếm theo `recap._word_tokens` (CJK tách TỪNG KÝ TỰ) còn `WordBoundary`
  của edge trả theo CỤM, nên Trung 56,3% / Nhật 57,1% là hai cách đếm khác
  nhau chứ không phải chữ mất mốc. Ở tiếng Việt/Anh (có dấu cách) edge ra
  **99,4% / 100%** đúng như cấu tạo. Đọc cột PHỦ của CJK thì phải nhớ điều
  này; cột dùng để kết luận là Việt/Anh và là phép so Groq-vs-gióng-hàng
  (hai bên cùng một mẫu số).

**PHỦ LÊN GẦN 100% Ở CẢ HAI MẺ (98,5 · 98,6) — tức nó là tính chất do CẤU
TẠO, không phải may.** Đó là câu trả lời cho "gióng hàng có chữa được bệnh
không": CÓ, đúng cái bệnh nặng nhất.

**NHƯNG CHƯA BẰNG edge-tts, PHẢI NÓI THẲNG:** rung mốc chữ đầu còn
**90-119 ms** so với **15,7 ms**. Nặng nhất là tiếng Anh (lệch hệ thống
**+104..+121 ms**, rung 128 ms) — mốc rơi SAU lúc `silencedetect` báo có
tiếng. Chưa truy ra vì sao, và **đừng trừ nó đi bằng một hằng số**: cổng 67
đã chặn đúng phép trừ kiểu đó (94 ms), lệch hệ thống chỉ được coi là thuộc
tính của bộ mốc khi có thước thứ ba xác nhận.
Cột "% chữ hiện muộn >50 ms" (Groq 36,5% -> gióng hàng 42,7%) **KHÔNG đọc
thẳng được**: nó tính trên lệch THÔ nên trừng phạt bên có lệch hệ thống
DƯƠNG và thưởng bên marks SỚM — edge ra 0,0% chính vì nó sớm sẵn
(−88,9 ms). Muốn so chất lượng thuần thì đọc cột RUNG.

**KHÔNG BỊA CHỮ — xác nhận lại**: thừa TB **+0,8%** (Việt) · **−1,7%**
(Trung) trên arm OmniVoice, cùng dải với edge-tts. Khớp kết luận lượt 7
(0,0%). Số Nhật (−30%) là do cách đếm token CJK, KHÔNG phải bịa chữ — hai arm
lệch như nhau (−30,1% vs −29,9%) nên nó là của THƯỚC.

═══════════════════════════════════════════════════════════════════════════
ÉP VỪA KHUNG: DÙNG `rubberband`, **KHÔNG** DÙNG NÚM `duration` CỦA MODEL
═══════════════════════════════════════════════════════════════════════════
Đây là phát hiện đáng giá nhất lượt 7, và nó ngược với trực giác. OmniVoice
có núm ép thời lượng THẬT (ghi thẳng bằng giây, không phải hệ số mơ hồ như
Piper). Ép cùng một câu về cùng độ dài bằng hai đường rồi chấm bằng thước
Groq chép ngược (tiếng Anh, 3 câu):

    nén     1,0   1,2   1,4   1,5    1,6    1,8    2,0
    núm     1,8   3,5   3,5   6,7   13,0   28,5   37,0  % đọc sai
    rubber  1,8   1,8   1,8   1,8    1,8    1,8    3,5  % đọc sai

  **Nén an toàn: núm model 1,50× — `rubberband` 2,00×** (tiếng Việt: 1,40×
  so với 1,60×). Núm model còn **TRƯỢT ĐÍCH +2,5% .. +12,3%** (luôn đọc dài
  hơn số giây mình xin), còn `rubberband` trúng đích tuyệt đối vì nó cắt
  theo đồng hồ.

-> `doc_loat` **sinh xong ở tốc độ tự nhiên rồi mới ép bằng `rubberband`**
   (`_ep_khung`, dùng lại `thay_giong._co_gian_chuoi` nên tự lùi `atempo`
   khi ffmpeg máy đó không có `rubberband`). Tham số `duration`/`speed` của
   model **KHÔNG BAO GIỜ được truyền** — cổng canh bằng quét tĩnh.

═══════════════════════════════════════════════════════════════════════════
TIẾN TRÌNH RIÊNG — BẮT BUỘC, KHÔNG PHẢI CHO GỌN
═══════════════════════════════════════════════════════════════════════════
Trong tiến trình đã nạp PyQt6 + `QApplication` thì `import torch` chết với
`OSError [WinError 1114] ... torch\\lib\\c10.dll`. Tái hiện 100%: torch TRƯỚC
Qt -> OK · torch SAU Qt -> 1114. **App này LÀ app Qt.** Demucs đã phải làm
đúng vậy (cổng 55) sau khi tính năng v2.24.0 hoá ra KHÔNG BAO GIỜ chạy được
khi bấm từ giao diện — mà lỗi lại đội lốt *"máy chưa cài Demucs"*.

Vì vậy trong CẢ FILE NÀY:
  - KHÔNG `import torch`, KHÔNG `import omnivoice`, KHÔNG `import
    transformers` (kể cả trong `try/except` — `try/except` KHÔNG chặn được
    ACCESS VIOLATION).
  - KHÔNG chèn thư mục gói vào `sys.path` của app.
  - Dò "đã cài chưa" bằng **FILE CÓ TỒN TẠI KHÔNG**, không bằng `find_spec`
    (`find_spec` phải NẠP gói cha; và nó luôn tìm trên `sys.path` nên không
    trả lời được câu "gói có nằm ĐÚNG CHỖ KIA không" — bài học cổng 58: máy
    dev mượn torch của `.venv` rồi báo "đã cài" trong khi `_lib` thiếu).

═══════════════════════════════════════════════════════════════════════════
CHƯA LÀM — GHI THẲNG, ĐỪNG ĐỌC NHẦM LÀ ĐÃ XONG
═══════════════════════════════════════════════════════════════════════════
  · **IndexTTS: MỚI CÓ KHUNG, CHƯA CHẠY ĐƯỢC CÂU NÀO.** Bản 2 **KHÔNG có**
    núm thời lượng (`infer_v2.py:661` là số cứng `code_lens * 1.72`), chỉ
    bản **2.5** mới có (`infer_v2_5.py:832 duration_factor`). Nó **KHÔNG có
    tiếng Việt** (zh/en/ja/es/ar). Không có bản cài `pip`: phải tải mã nguồn
    GitHub + trọng số **5,24 GB** rồi tự dựng trên Windows. Đã chủ động
    DỪNG ở phần khung thay vì sa lầy — `tinh_trang_indextts()` nói thẳng
    còn thiếu gì, `doc_loat` với mã `ix:` lùi êm về edge-tts.
    (Giấy phép của nó thì DỄ CHỊU NHẤT trong 4 bộ: bilibili Model Use
    License **CHO** thương mại. Đó là lý do đáng để làm nốt sau này.)
  · App **KHÔNG tự tải** trọng số OmniVoice (6,1 GB trong kho HF của máy).
    Máy nào chưa có thì `co_omnivoice()` = False -> lùi edge-tts.
  · Bản `.exe` KHÔNG gói torch/omnivoice (cùng ràng buộc Demucs/Piper): máy
    nhân viên phải có Python 3 + môi trường riêng thì mới dùng được.
"""
from __future__ import annotations

import json
import os
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
#: Tiền tố mã giọng. Mã edge-tts không bao giờ chứa dấu hai chấm nên các họ
#: giọng (`piper:` · `el:` · `gemini:` · `ov:` · `ix:`) không lẫn nhau được.
TIEN_TO_OV = "ov:"
TIEN_TO_IX = "ix:"

#: Cảnh báo giấy phép — **BẮT BUỘC hiện trong hộp chọn giọng**. Xem đầu file.
CANH_BAO_GP_OV = ("trọng số CC-BY-NC: nhà phát hành CẤM dùng cho mục đích "
                  "thương mại; có kèm Boson Higgs Audio 2 / Meta Llama 3")

#: Cảnh báo CHẤT LƯỢNG — cùng luật với Piper (cổng 64): tệ hơn edge-tts thì
#: phải ghi ra, đừng để người dùng tự phát hiện sau 300 video.
#:
#: **HAI CÂU, VÌ MÁY CÓ HAI TRẠNG THÁI** (đúng tiền lệ nhãn Piper ở
#: `thay_giong_dialog._do_piper`): bệnh nặng nhất của giọng ngoài là **mốc
#: KHÔNG CÓ**, mà bệnh đó do đường LẤY MỐC gây ra chứ không phải do giọng —
#: nên máy đã tải bộ gióng hàng thì câu cũ thành lời doạ sai. In câu cũ cho
#: máy đã có gióng hàng là đuổi người dùng khỏi một lựa chọn vừa được chữa;
#: in câu mới cho máy chưa có là hứa hão. `canh_bao_chat_luong()` chọn câu.
#:
#: Số lấy từ `_do_gn_gh.py` + `_do_gn_cu.py` (4 thứ tiếng × 12 câu × 2 lượt
#: ĐAN XEN có xoay thứ tự, **2 bộ tiếng độc lập**, 2.186 chữ mỗi bộ), thước
#: DUY NHẤT là `silencedetect` — xem khối "ĐỘ KHỚP MỐC" ở đầu file.
#: Phần "đọc sai chữ" GIỮ NGUYÊN: nó đo cách model ĐỌC, không liên quan
#: đường lấy mốc, nên gióng hàng không đụng tới.
_CL_DOC_SAI = "đọc sai chữ tiếng Việt 16,9% so với edge-tts 6,8%"

CANH_BAO_CL_OV = (_CL_DOC_SAI + "; mốc chữ phải dò lại bằng máy nghe nên "
                  "CHỈ CÓ cho 38-99% số chữ tuỳ lượt (không đoán trước "
                  "được) và rung 250-712 ms (edge-tts 16 ms) — chữ sẽ chạy "
                  "không khớp tiếng. Tải bộ gióng hàng để hết bệnh này")

#: Máy ĐÃ có bộ gióng hàng: mốc lấy từ chữ ĐÃ BIẾT nên phủ gần đủ do cấu tạo.
#: Vẫn phải nói phần CHƯA bằng edge-tts — rung 90-119 ms so với 16 ms.
CANH_BAO_CL_OV_GH = (_CL_DOC_SAI + "; máy này có bộ gióng hàng nên mốc chữ "
                     "phủ 98,5% (trước 52-82%), nhưng vẫn rung 90-119 ms so "
                     "với 16 ms của giọng thường — chữ bám lời kém hơn "
                     "edge-tts")


def canh_bao_chat_luong() -> str:
    """Câu cảnh báo chất lượng ĐÚNG VỚI MÁY NÀY.

    KHÔNG cất kết quả vào hằng số: người dùng bấm nút tải bộ gióng hàng giữa
    phiên thì nhãn phải đổi theo, không đợi khởi động lại app (bài học
    `tg_so.duong_so` — đọc lại mỗi lần gọi).
    """
    try:
        from app.core import giong_hang as _gh
        if _gh.co_giong_hang():
            return CANH_BAO_CL_OV_GH
    except Exception:  # noqa: BLE001 - thiếu module -> giữ cảnh báo cũ
        pass
    return CANH_BAO_CL_OV

#: Kho giọng THIẾT KẾ BẰNG CHỮ (voice design). OmniVoice không có giọng đặt
#: tên sẵn: gõ một câu tả là ra giọng, nên số giọng coi như không giới hạn.
#: Chỉ đưa vào combo vài giọng ĐÃ CHẠY THẬT ở lượt 7 — thêm giọng bịa là
#: thêm chỗ hỏng mà không ai đo.
#:   (mã, câu tả gửi cho model, nhãn tiếng Việt)
#:
#: **CÂU TẢ PHẢI GHÉP TỪ ĐÚNG BẢNG TỪ CỦA MODEL, KHÔNG ĐƯỢC VIẾT VĂN.**
#: OmniVoice nhận một DANH SÁCH ĐÓNG (`male` · `female` · `young adult` ·
#: `middle-aged` · `elderly` · `teenager` · `child` · `very low pitch` ·
#: `low pitch` · `moderate pitch` · `high pitch` · `very high pitch` ·
#: `whisper` · các giọng vùng). Viết thêm chữ cho hay là nó NÉM
#: `ValueError: Unsupported instruct items`.
#:
#: **ĐÃ SẬP THẬT — `ov:nu_am` là giọng CHẾT từ lúc ra đời tới 18/08/2026:**
#: nó khai `warm low pitch` (chữ `warm` không có trong bảng) nên **0/4 câu đọc
#: được, 2/2 lượt đo**, rồi `doc_loat` lùi êm về edge-tts. Anh Hùng chọn nó
#: trong combo thì được một giọng KHÁC HẲN mà **không một dòng báo trên giao
#: diện** (lý do chỉ nằm trong `logs/giong_ngoai_<ngày>.log`) — đúng họ lỗi
#: "chọn X ra Y". Thêm giọng mới vào bảng này thì **phải đọc thử 1 câu**,
#: đừng tin là câu tả nghe hợp lý thì model hiểu.
GIONG_OV: tuple[tuple[str, str, str], ...] = (
    ("ov:nu_tre",   "female, young adult, moderate pitch",
     "Nữ trẻ"),
    ("ov:nam_tre",  "male, young adult, moderate pitch",
     "Nam trẻ"),
    ("ov:nam_tram", "male, middle-aged, low pitch",
     "Nam trung niên trầm"),
    ("ov:nu_am",    "female, middle-aged, low pitch",
     "Nữ trung niên ấm"),
    ("ov:ong_gia",  "male, elderly, very low pitch",
     "Nam cao tuổi rất trầm"),
)

#: Khung IndexTTS. CHƯA CHẠY ĐƯỢC — xem `tinh_trang_indextts`. Để sẵn mã ở
#: đây để đường rẽ, log và cổng test có thứ để bám; `danh_sach_giong()` chỉ
#: trả nó ra khi máy thật sự chạy được.
GIONG_IX: tuple[tuple[str, str, str], ...] = (
    ("ix:mac_dinh", "", "Giọng mặc định (IndexTTS)"),
)

_BANG_INSTRUCT = {ma: tt for ma, tt, _ in GIONG_OV}


def la_giong_omnivoice(voice: str) -> bool:
    return str(voice or "").startswith(TIEN_TO_OV)


def la_giong_indextts(voice: str) -> bool:
    return str(voice or "").startswith(TIEN_TO_IX)


def la_giong_ngoai(voice: str) -> bool:
    """Giọng này có thuộc file này không (OmniVoice hoặc IndexTTS)."""
    return la_giong_omnivoice(voice) or la_giong_indextts(voice)


def nhan_giong(ma: str) -> str:
    """Nhãn đầy đủ cho hộp chọn giọng. TIẾNG VIỆT, KHÔNG EMOJI.

    **Nhãn PHẢI mang cả hai cảnh báo** (giấy phép + chất lượng). Đây không
    phải chỗ để bán hàng: Piper đã có tiền lệ ghi thẳng đánh đổi ngay trong
    nhãn, và lý do là anh Hùng chạy 200-300 kênh — chọn nhầm một lần là hàng
    trăm video.

    **KÈM MỨC NHẤN NHÁ** (``app/core/nhan_nha.py``) để giọng OmniVoice đứng
    CÙNG THANG với giọng edge-tts — chúng đọc cùng bộ câu tiếng Việt nên so
    trực tiếp được. Và số đó **cãi lại một mệnh đề đang được truyền tay**:
    ``ov:nam_tre`` đo **4,24**, CAO HƠN cả NamMinh (4,04) lẫn HoaiMy (3,18),
    chứ không phải "đáy thang 2,16" (2,16 là TRẢI của 11 giọng, không phải
    giá trị một giọng). Lý do nên cân nhắc bỏ OmniVoice nằm ở **giấy phép và
    độ chính xác chữ**, không nằm ở nhấn nhá.
    """
    from app.core import nhan_nha
    for m, _tt, ten in GIONG_OV:
        if m == ma:
            return (f"{ten} (OmniVoice, 4 thứ tiếng){nhan_nha.nhan(ma)} - "
                    f"{CANH_BAO_GP_OV}; {canh_bao_chat_luong()}")
    for m, _tt, ten in GIONG_IX:
        if m == ma:
            return (f"{ten} - không có tiếng Việt; mốc chữ phải dò lại bằng "
                    f"Groq nên kém khớp hơn edge-tts")
    return ma


def danh_sach_giong() -> list[tuple[str, str]]:
    """[(mã, nhãn)] để đổ vào combo. CHỈ trả giọng máy này CHẠY ĐƯỢC.

    Đưa giọng không chạy được vào combo là đẩy người dùng chọn một thứ sẽ
    âm thầm lùi về edge-tts — đúng loại "chọn X ra Y" mà repo này đã sửa
    nhiều lần (việc #110, cổng 55).
    """
    ds: list[tuple[str, str]] = []
    if co_omnivoice():
        ds += [(m, nhan_giong(m)) for m, _t, _n in GIONG_OV]
    if co_indextts():
        ds += [(m, nhan_giong(m)) for m, _t, _n in GIONG_IX]
    return ds


# ---------------------------------------------------------------------------
# Chỗ để đồ — NGOÀI thư mục cài
# ---------------------------------------------------------------------------
def thu_muc_ngoai() -> Path:
    """Thư mục làm việc của nhóm giọng ngoài (runner, log, hộp cát).

    ĐỌC `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số ở tầm module — test
    đổi `BQ_DATA_DIR` sau khi module đã nạp thì hằng số cũ trỏ sai chỗ (bài
    học `tg_so.duong_so`, `piper_tts.thu_muc_piper`, `lib_demucs`).

    BẢN ĐÓNG GÓI PHẢI RA `DATA_DIR`, KHÔNG ĐƯỢC RA CẠNH `.exe`: lượt tự cập
    nhật đổi tên `_internal` -> `_internal.old` rồi `rmdir /S /Q`, tức mọi
    thứ nằm trong đó bị XOÁ SẠCH (cổng 58 CA 5, đã xảy ra thật với `_lib`).
    """
    try:
        import config
        goc = Path(getattr(config, "DATA_DIR", "") or "")
    except Exception:  # noqa: BLE001
        goc = Path("")
    if getattr(sys, "frozen", False):
        return (goc or Path.home()) / "_giong_ngoai"
    return Path(__file__).resolve().parents[2] / "_giong_ngoai"


#: Python có sẵn `omnivoice` + torch + transformers. Dò theo THỨ TỰ:
#:   1. `BQ_OV_PYTHON` — ép cứng (đo A/B, gỡ rối máy user, cổng test)
#:   2. môi trường riêng của app: `<thu_muc_ngoai>/venv`
#:   3. `%TEMP%\bq_tts_rr\venv_ov` — **CHỖ CŨ, ĐÃ DỜI ĐI 18/08/2026.**
#:      Lượt 7 dựng môi trường 7,74 GB ngay trong `%TEMP%`, tức một lượt
#:      `tempsweep` / Disk Cleanup / anh Hùng dọn ổ C là **mất sạch**, và
#:      triệu chứng lại là "giọng tự nhiên biến khỏi combo" — không ai lần ra
#:      nguyên nhân. Đã chép sang `<thu_muc_ngoai>/venv` (47.520 file, 0
#:      FAILED, chạy lại thật ra WAV 3,11 s + gióng hàng 11/11 mốc) rồi xoá
#:      bản cũ (ổ C: 370 -> 377 GB trống).
#:      **VẪN GIỮ ứng viên này ở CUỐI danh sách**, cố ý: máy nào còn bản cũ
#:      thì vẫn chạy được thay vì gãy: nhưng `tinh_trang_omnivoice()['o_tam']`
#:      sẽ báo và `doc_loat` ghi log MỖI LƯỢT (xem `o_thu_muc_tam`).
def _ung_vien_python() -> list[Path]:
    ds: list[Path] = []
    ep = os.environ.get("BQ_OV_PYTHON", "").strip()
    if ep:
        ds.append(Path(ep))
    ds.append(thu_muc_ngoai() / "venv" / "Scripts" / "python.exe")
    ds.append(thu_muc_ngoai() / "venv" / "bin" / "python")
    tam = Path(tempfile.gettempdir())
    ds.append(tam / "bq_tts_rr" / "venv_ov" / "Scripts" / "python.exe")
    ds.append(tam / "bq_tts_rr" / "venv_ov" / "bin" / "python")
    return ds


#: File PHẢI có mặt cạnh python thì mới coi là "có omnivoice". Dò bằng ĐƯỜNG
#: DẪN nên bản `.exe` (không có `.venv` để mượn) thấy ĐÚNG cái máy dev thấy.
_CAN_CO_OV = ("omnivoice/models/omnivoice.py", "torch/__init__.py",
              "transformers/__init__.py", "soundfile.py")


def _site_packages(py: Path) -> list[Path]:
    """Các thư mục gói đi kèm một python — KHÔNG chạy python để hỏi."""
    goc = py.parent.parent
    return [goc / "Lib" / "site-packages", goc / "lib" / "site-packages"]


def _python_omnivoice() -> tuple[str, list[str]]:
    """(python chạy được OmniVoice, danh sách thứ còn thiếu của ứng viên tốt
    nhất). `("", [...])` = không có ứng viên nào chạy được."""
    thieu_tot_nhat: Optional[list[str]] = None
    for py in _ung_vien_python():
        if not py.exists():
            continue
        for sp in _site_packages(py):
            if not sp.is_dir():
                continue
            thieu = [t for t in _CAN_CO_OV if not (sp / t).exists()]
            if not thieu:
                return str(py), []
            if thieu_tot_nhat is None or len(thieu) < len(thieu_tot_nhat):
                thieu_tot_nhat = thieu
    return "", (thieu_tot_nhat if thieu_tot_nhat is not None
                else ["môi trường Python có omnivoice"])


#: Trọng số. `BQ_OV_MODEL` trỏ thẳng vào thư mục snapshot; không đặt thì tra
#: trong kho Hugging Face của máy. **KHÔNG BAO GIỜ để nó tự tải**: 6,1 GB
#: giữa lúc anh Hùng đang chạy sản xuất là không chấp nhận được, và một lượt
#: tải hỏng thì lỗi đội lốt "giọng đọc hỏng".
REPO_OV = "k2-fsa/OmniVoice"


def _kho_hf() -> Path:
    for k in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        v = os.environ.get(k, "").strip()
        if v:
            return Path(v)
    v = os.environ.get("HF_HOME", "").strip()
    if v:
        return Path(v) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def duong_model_ov() -> str:
    """Thư mục snapshot của trọng số OmniVoice. "" = không tìm thấy.

    Trả thẳng ĐƯỜNG DẪN chứ không trả tên kho: `from_pretrained` mà nhận tên
    kho thì có đường đi hỏi mạng, và một lượt đọc giọng KHÔNG được phép phụ
    thuộc mạng khi trọng số đã nằm sẵn trên đĩa.
    """
    ep = os.environ.get("BQ_OV_MODEL", "").strip()
    if ep:
        return ep if _du_trong_so(Path(ep)) else ""
    goc = _kho_hf() / ("models--" + REPO_OV.replace("/", "--"))
    ref = goc / "refs" / "main"
    ung: list[Path] = []
    try:
        if ref.exists():
            ung.append(goc / "snapshots" / ref.read_text(
                encoding="utf-8").strip())
    except OSError:
        pass
    try:
        ung += sorted((goc / "snapshots").iterdir())
    except OSError:
        pass
    for d in ung:
        if _du_trong_so(d):
            return str(d)
    return ""


#: Đủ trọng số = có CẢ model chính LẪN bộ mã hoá tiếng. Thiếu `audio_tokenizer`
#: thì `from_pretrained` quay ra HỎI MẠNG (xem `omnivoice.py:352`) — tức một
#: lượt đọc tưởng chạy offline lại treo vì mạng.
_CAN_CO_TRONG_SO = ("config.json", "model.safetensors",
                    "audio_tokenizer/model.safetensors")


def _du_trong_so(d: Path) -> bool:
    try:
        return d.is_dir() and all((d / t).exists() for t in _CAN_CO_TRONG_SO)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Dò đã dùng được chưa — bằng FILE, không bằng import
# ---------------------------------------------------------------------------
def tinh_trang_omnivoice() -> dict:
    """{co, thieu, python, model, thu_muc}. KHÔNG import gì của model.

    `thieu` là danh sách để đặt NHÃN — nói đích danh còn thiếu gì, đừng chỉ
    nói "chưa có" (bài học cổng 58: hộp Demucs phải nêu tên từng gói).
    """
    py, thieu = _python_omnivoice()
    model = duong_model_ov()
    if not model:
        thieu = list(thieu) + [f"trọng số {REPO_OV} (6,1 GB, chưa có trên máy)"]
    return {
        "co": bool(py) and bool(model),
        "thieu": thieu,
        "python": py,
        "model": model,
        "thu_muc": str(thu_muc_ngoai()),
        # NGUỒN TỪNG GÓI — trả lời câu *"gói nằm THẬT ở đâu"*, đúng cái bản
        # `.exe` thấy. `goi[x]['nguon'] == 'hệ thống'` nghĩa là *"máy này chạy
        # được, máy anh Hùng thì không"* (cổng 58). Để RIÊNG khoá, không gộp
        # vào `thieu`.
        "goi": do_goi_ov(),
        "venv": str(thu_muc_ngoai() / "venv"),
        # Nút tải bấm được không (máy nhân viên có thể không có Python 3).
        "cai_duoc": bool(_python_he_thong()),
        "nhan_tai": nhan_tai(),
        # CẢNH BÁO CHỖ ĐỂ ĐỒ — xem `o_thu_muc_tam`. Đây KHÔNG phải "thiếu"
        # (máy vẫn chạy được), nên để riêng khoá: gộp vào `thieu` là nút tải
        # và nhãn báo sai trạng thái.
        "o_tam": o_thu_muc_tam(py),
    }


def o_thu_muc_tam(py: str = "") -> str:
    """Môi trường đang nằm trong thư mục TẠM thì trả đường dẫn đó, "" nếu không.

    VÌ SAO PHẢI BÁO RA. Môi trường OmniVoice ~7,7 GB được dựng ở
    `%TEMP%\\bq_tts_rr\\venv_ov` (lượt 7). `%TEMP%` là chỗ TẠM: một lượt
    `tempsweep`, một lượt Disk Cleanup của Windows, hoặc chính anh Hùng dọn ổ
    C khi đầy là **mất sạch** — và lúc đó `co_omnivoice()` trả False nên
    **giọng lặng lẽ biến khỏi combo**, đúng loại hỏng âm thầm repo này chống.
    Đã có tiền lệ y hệt: `_lib` của Demucs bị chính lượt tự cập nhật xoá
    (cổng 58 CA5) và anh Hùng kêu *"trước tôi nhớ báo cài rồi mà nay nó ghi
    chưa có bộ tách giọng"*.

    Chỗ ĐÚNG là `thu_muc_ngoai()` (cạnh repo khi chạy nguồn · `DATA_DIR` ở
    bản `.exe`) — y như `_piper`. Hàm này KHÔNG tự dời: dời 7,7 GB sau lưng
    người đang chạy sản xuất là việc phải hỏi. Nó chỉ NÓI RA.
    """
    try:
        p = str(py or _python_omnivoice()[0] or "")
        if not p:
            return ""
        tam = Path(tempfile.gettempdir()).resolve()
        return str(Path(p).resolve()) if tam in Path(p).resolve().parents \
            else ""
    except Exception:  # noqa: BLE001
        return ""


def co_omnivoice() -> bool:
    """Có chạy được OmniVoice không. KHÔNG BAO GIỜ NÉM."""
    try:
        return bool(tinh_trang_omnivoice()["co"])
    except Exception:  # noqa: BLE001
        return False


def tinh_trang_indextts() -> dict:
    """IndexTTS — **MỚI CÓ KHUNG**. Nói thẳng còn thiếu gì.

    Không có bản `pip`; muốn chạy phải: tải mã nguồn `index-tts` từ GitHub,
    tải trọng số **5,24 GB**, dựng trên Windows, rồi trỏ `BQ_IX_PYTHON` +
    `BQ_IX_MODEL` vào. Chừng nào chưa có đủ hai thứ đó thì `co` = False và
    `doc_loat` lùi êm về edge-tts.

    NHẮC LẠI ĐỂ KHỎI AI KỲ VỌNG NHẦM: bản **2 KHÔNG có** núm thời lượng
    (`infer_v2.py:661` là số cứng), chỉ **2.5** mới có; và **cả hai đều
    KHÔNG có tiếng Việt**.
    """
    py = os.environ.get("BQ_IX_PYTHON", "").strip()
    model = os.environ.get("BQ_IX_MODEL", "").strip()
    thieu: list[str] = []
    if not py or not Path(py).exists():
        thieu.append("môi trường Python có index-tts (BQ_IX_PYTHON)")
    if not model or not Path(model).is_dir():
        thieu.append("trọng số IndexTTS 5,24 GB (BQ_IX_MODEL)")
    return {
        "co": not thieu,
        "thieu": thieu,
        "python": py,
        "model": model,
        "ghi_chu": ("chưa dựng được trên máy này: không có bản pip, phải "
                    "dựng mã GitHub + tải 5,24 GB; bản 2 không có núm thời "
                    "lượng, cả 2 bản đều không có tiếng Việt"),
    }


def co_indextts() -> bool:
    try:
        return bool(tinh_trang_indextts()["co"])
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# NÚT CÀI — chỉ chạy khi NGƯỜI DÙNG BẤM
# ---------------------------------------------------------------------------
#: **VÌ SAO HÀM NÀY PHẢI TỒN TẠI — 19/08/2026, MẤT MÔI TRƯỜNG 7,74 GB.**
#: Repo có `cai_demucs` · `cai_giong_hang` · `cai_piper` · `cai_vieneu` nhưng
#: KHÔNG có `cai_omnivoice`: môi trường lượt 7 dựng bằng tay ngoài app. Nên khi
#: `_don(Path(""))` xoá sạch cây làm việc, mọi thứ khác dựng lại được từ nút
#: bấm còn `_giong_ngoai/` thì **không có nút nào để bấm** — phải suy ra tên
#: gói rồi cài tay. Một tính năng không có đường dựng lại là một tính năng chỉ
#: sống được tới lần mất đầu tiên.
#:
#: Tên gói PyPI là **`omnivoice`** (0.2.1, `requires_python >= 3.10`) — đã kiểm
#: bằng metadata chỉ mục, không đoán.

#: Gói PHẢI nằm THẬT trong site-packages của môi trường riêng. Chỉ tên TẦNG
#: TRÊN CÙNG: `PathFinder.find_spec("omnivoice.models.omnivoice", ...)` sẽ
#: IMPORT gói cha thật, mà nạp torch vào tiến trình app đã có Qt là ACCESS
#: VIOLATION (xem khối "TIẾN TRÌNH RIÊNG" ở đầu file).
GOI_OV: tuple[str, ...] = ("omnivoice", "torch", "torchaudio",
                           "transformers", "soundfile")

#: Chỉ mục wheel của PyTorch. `--extra-index-url` chứ KHÔNG `--index-url`:
#: chỉ mục này không có `omnivoice`/`gradio`/`librosa` nên ép cả lượt vào đó
#: là hỏng phép giải (bài học `cai_demucs`).
CHI_MUC_TORCH_CUDA = "https://download.pytorch.org/whl/cu126"
CHI_MUC_TORCH_CPU = "https://download.pytorch.org/whl/cpu"

#: **SỐ ĐO, KHÔNG PHẢI ƯỚC BỪA** — `pip install --dry-run --report` (87 gói)
#: rồi HTTP HEAD từng wheel, 19/08/2026:
#:     cu126  torch 2.13.0+cu126 **2.474,4 MB** + 184,4 MB còn lại = **2.658,8 MB**
#:     cpu    torch 2.13.0+cpu     116,3 MB     + 183,2 MB còn lại =   **299,5 MB**
#: Nhãn PHẢI khớp ĐƯỜNG SẼ ĐI (cổng 71 CA 4): repo này đã có lỗi nút ghi
#: 155 MB mà hộp xác nhận doạ 2 GB — bấm xong ngồi đợi một lượt tải gấp 16 lần
#: cái vừa đọc. Con số ở đây là **phần pip tải**; trọng số 6,1 GB là việc
#: KHÁC và `tinh_trang_omnivoice()['thieu']` nói riêng.
MB_TAI_GPU = 2658.8
MB_TAI_CPU = 299.5
NHAN_TAI_GPU = ("Tải môi trường OmniVoice bản CUDA (khoảng 2,6 GB) — "
                "chạy 1 lần")
NHAN_TAI_CPU = "Tải môi trường OmniVoice (khoảng 300 MB) — chạy 1 lần"


def nhan_tai() -> str:
    """Nhãn nút tải ĐÚNG với máy này. Đọc lại mỗi lần gọi (bài học
    `tg_so.duong_so`): cắm/rút GPU giữa phiên thì nhãn phải đổi theo."""
    return NHAN_TAI_GPU if co_gpu_nvidia() else NHAN_TAI_CPU


def co_gpu_nvidia() -> bool:
    """Máy có GPU NVIDIA dùng được không — hỏi `nvidia-smi`, **KHÔNG hỏi
    torch**.

    Dùng lại `thay_giong.co_gpu_nvidia` để hai nút tải không bao giờ chọn
    khác chỉ mục nhau. Thiếu module thì tự hỏi lấy — hàm này KHÔNG BAO GIỜ NÉM,
    và đoán nhầm cũng chỉ dẫn tới tải gói to/nhỏ hơn: `_MA_DOC` vẫn tự quyết
    thiết bị bằng `torch.cuda.is_available()` lúc chạy.
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


def _thu_muc_goi(venv: Path) -> str:
    """site-packages của môi trường riêng. '' = chưa dựng."""
    for ten in ("Lib", "lib"):
        d = venv / ten / "site-packages"
        try:
            if d.is_dir():
                return str(d)
        except OSError:
            pass
    return ""


def do_goi_ov(venv: Optional[Path] = None) -> dict:
    """TỪNG gói đang nằm ở ĐÂU — **KHÔNG import một dòng nào**.

    Trả `{tên: {"venv": <đường trong môi trường riêng|"">, "he": <đường NGOÀI>,
    "nguon": "venv" | "hệ thống" | ""}}`.

    **HỎI ĐÚNG CÂU — bài học cổng 58.** Câu hỏi KHÔNG phải *"import được
    không"* (máy dev mượn gói của `.venv` rồi báo "đã cài" trong khi thư mục
    đích rỗng, bản `.exe` thì báo thiếu — máy dev XANH, máy thật ĐỎ) mà là
    *"`spec.origin` có nằm THẬT trong thư mục đích không"*.

    Dùng `PathFinder` chứ KHÔNG `importlib.util.find_spec`: `find_spec` phải
    NẠP gói cha, và nó luôn tìm trên `sys.path` nên không trả lời được câu
    trên.
    """
    from importlib.machinery import PathFinder
    if venv is None:
        venv = thu_muc_ngoai() / "venv"
    sp = _thu_muc_goi(Path(venv))
    duong = [sp] if sp else []

    def _tim(ten: str, o_dau: Optional[list]) -> str:
        try:
            s = PathFinder.find_spec(ten, o_dau)
        except Exception:  # noqa: BLE001 - thư mục hỏng / gói cụt
            return ""
        if s is None:
            return ""
        g = getattr(s, "origin", "") or ""
        if (not g or g == "namespace") and getattr(s, "submodule_search_locations", None):
            try:
                g = list(s.submodule_search_locations)[0]
            except (TypeError, IndexError):
                g = ""
        return str(g or "")

    ra: dict = {}
    for ten in GOI_OV:
        o_venv = _tim(ten, duong) if duong else ""
        he = "" if o_venv else _tim(ten, None)
        ra[ten] = {"venv": o_venv, "he": he,
                   "nguon": "venv" if o_venv else ("hệ thống" if he else "")}
    return ra


def _python_he_thong() -> str:
    """Python 3 trên máy để DỰNG môi trường riêng. "" = không có.

    KHÔNG dùng `sys.executable` ở bản `.exe`: chỗ đó là chính
    `BQHungVideo.exe`, gọi `-m venv` vào nó là vô nghĩa (đúng cách
    `giong_vieneu._python_he_thong` / `piper_tts._python_chay` đã làm).
    """
    if not getattr(sys, "frozen", False):
        ex = Path(sys.executable)
        try:
            if ex.exists() and ex.name.lower().startswith("python"):
                return str(ex)
        except OSError:
            pass
    for ten in ("py", "python", "python3"):
        p = shutil.which(ten)
        if p:
            return p
    return ""


#: Một lượt cài là 2,6 GB — hai lượt chồng nhau vào cùng thư mục là hỏng cả hai.
_KHOA_CAI = threading.Lock()


def cai_omnivoice(on_progress: Optional[Callable[[float, str], None]] = None,
                  han_giay: int = 7200) -> dict:
    """Dựng môi trường OmniVoice ở `thu_muc_ngoai()/venv`. **CHỈ khi NGƯỜI
    DÙNG BẤM** — không bao giờ tự chạy nền.

    ═══ VÌ SAO **VENV** CHỨ KHÔNG `--target` NHƯ `_lib`/`_piper` ═══
    Đây là chỗ đã sập một lần và nó là bẫy KÍCH THƯỚC-KHÔNG-CHỨNG-MINH-GÌ:
    `--target` chỉ chép file vào một thư mục rồi nhét vào `sys.path` của MỘT
    python KHÁC, nên gói biên dịch cho **cp314** nằm đủ 4 GB trong thư mục mà
    python **cp312** nạp vào là `ImportError` phần mở rộng C. Thư mục đầy
    không có nghĩa là chạy được.
    Venv thì có **python CỦA NÓ**: pip cài cho đúng bản đang đứng đó, không
    mượn gì của ai, không thể lệch ABI do xây dựng. Đó cũng đúng lý do
    `giong_vieneu` chọn venv (librosa/numba/soundfile đều có phần mở rộng), và
    là điều làm phép dò `_python_omnivoice` nói THẬT.

    ═══ KHÔNG BAO GIỜ CÀI VÀO `.venv` ═══
    `.venv` là môi trường anh Hùng đang chạy sản xuất 300 kênh. Một lượt
    `pip install` kéo theo torch/transformers khác bản có thể phá app đang
    chạy — đúng lý do Demucs phải ở `_lib` (cổng 55) và VieNeu ở
    `_giong_vieneu` (cổng 79).

    ═══ `--ignore-installed` ═══
    Giữ đúng luật cổng 58: pip cũ coi gói đã có trong môi trường ĐANG CHẠY là
    "đã thoả mãn" rồi BỎ QUA, không chép vào đích. Ở venv trắng thì gần như
    không có gì để bỏ qua, nhưng cờ này khiến kết quả **không phụ thuộc bản
    pip** — và `_lib` đã chứng minh hành vi cũ có thật.

    Trả `{ok, loi, giay, venv, tinh_trang, goi, gpu, chi_muc, nhat_ky}`.
    KHÔNG BAO GIỜ NÉM.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(max(0.0, min(1.0, p)), m)
            except Exception:  # noqa: BLE001
                pass

    d = thu_muc_ngoai()
    venv = d / "venv"
    py = _python_he_thong()
    if not py:
        return {"ok": False, "venv": str(venv), "giay": 0.0,
                "loi": ("Máy này không có Python 3 nên app không tự tải được: "
                        "cài Python 3 (python.org) rồi bấm lại, hoặc copy thư "
                        "mục _giong_ngoai từ máy đã cài sang.")}
    if not _KHOA_CAI.acquire(blocking=False):
        return {"ok": False, "venv": str(venv), "giay": 0.0,
                "loi": "Đang tải rồi — đợi lượt này xong."}
    t0 = time.time()
    nhat_ky: list[str] = []
    try:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"ok": False, "venv": str(venv), "giay": 0.0,
                    "loi": f"Không tạo được thư mục {d}: {e}"}

        vpy = _python_trong_venv(venv)
        if not vpy:
            prog(0.03, "Đang dựng môi trường Python riêng...")
            r = _chay_lenh([py, "-m", "venv", str(venv)], 900)
            nhat_ky.append(f"venv rc={r[0]} {r[1][-200:]}")
            if r[0] != 0:
                return {"ok": False, "venv": str(venv), "nhat_ky": nhat_ky,
                        "giay": round(time.time() - t0, 2),
                        "loi": f"Dựng môi trường hỏng: {r[1][-500:]}"}
            vpy = _python_trong_venv(venv)
        if not vpy:
            return {"ok": False, "venv": str(venv), "nhat_ky": nhat_ky,
                    "giay": round(time.time() - t0, 2),
                    "loi": f"Dựng xong mà không thấy python ở {venv}"}

        gpu = co_gpu_nvidia()
        chi_muc = CHI_MUC_TORCH_CUDA if gpu else CHI_MUC_TORCH_CPU
        args = [vpy, "-m", "pip", "install", "--no-input",
                "--disable-pip-version-check", "--upgrade",
                "--ignore-installed", "--extra-index-url", chi_muc,
                "omnivoice"]
        prog(0.06, (NHAN_TAI_GPU if gpu else NHAN_TAI_CPU) + "...")
        p = None
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace",
                                 bufsize=1, creationflags=_NO_WIN)
            _gan_job(p)
            han = time.time() + han_giay
            n = 0
            for dong in p.stdout or ():
                dong = dong.rstrip()
                if not dong:
                    continue
                nhat_ky.append(dong)
                n += 1
                # KHÔNG biết trước tổng byte -> % chỉ là dấu hiệu "đang chạy",
                # trần 0,93 để không khoe xong trước khi xong.
                prog(min(0.93, 0.06 + n / 1200.0), dong[-110:])
                if time.time() > han:
                    p.kill()
                    return {"ok": False, "venv": str(venv), "gpu": gpu,
                            "giay": round(time.time() - t0, 2),
                            "nhat_ky": nhat_ky[-40:],
                            "loi": f"Tải quá {han_giay}s, đã dừng."}
            ma = p.wait(timeout=180)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "venv": str(venv), "gpu": gpu,
                    "giay": round(time.time() - t0, 2),
                    "nhat_ky": nhat_ky[-40:],
                    "loi": f"{type(e).__name__}: {e}"}
        finally:
            if p is not None:
                _bo_gan_job(p)
        if ma != 0:
            return {"ok": False, "venv": str(venv), "gpu": gpu, "ma_thoat": ma,
                    "giay": round(time.time() - t0, 2),
                    "nhat_ky": nhat_ky[-40:],
                    "loi": f"pip trả mã {ma}: " + " | ".join(nhat_ky[-4:])}

        # ═══ HẬU KIỂM: SO `spec.origin` VỚI THƯ MỤC ĐÍCH ═══
        # KHÔNG hỏi "import được không" — bài học cổng 58. `PathFinder` nhớ
        # nội dung thư mục theo mtime, mà pip vừa ghi vào, nên phải xoá bộ nhớ
        # đó; không thì lượt kiểm ngay sau khi cài vẫn thấy thư mục như lúc
        # chưa cài rồi báo THIẾU oan.
        prog(0.95, "Đang kiểm lại...")
        import importlib
        importlib.invalidate_caches()
        goi = do_goi_ov(venv)
        thieu = [g for g in GOI_OV if not goi[g]["venv"]]
        if thieu:
            return {"ok": False, "venv": str(venv), "gpu": gpu, "goi": goi,
                    "giay": round(time.time() - t0, 2),
                    "nhat_ky": nhat_ky[-40:], "thieu": thieu,
                    "loi": ("pip trả mã 0 nhưng những gói này KHÔNG nằm trong "
                            + str(venv) + ": " + ", ".join(thieu))}
        tt = tinh_trang_omnivoice()
        prog(1.0, "Đã cài xong môi trường OmniVoice.")
        _ghi_log(f"Đã cài môi trường OmniVoice vào {venv} "
                 f"({'CUDA' if gpu else 'CPU'}, {round(time.time() - t0)}s)")
        return {"ok": True, "loi": "", "venv": str(venv), "gpu": gpu,
                "chi_muc": chi_muc, "goi": goi, "tinh_trang": tt,
                "giay": round(time.time() - t0, 2), "nhat_ky": nhat_ky[-40:]}
    finally:
        try:
            _KHOA_CAI.release()
        except RuntimeError:
            pass


def _python_trong_venv(venv: Path) -> str:
    """python.exe của môi trường riêng. '' = chưa dựng."""
    for phan in (("Scripts", "python.exe"), ("bin", "python")):
        p = Path(venv).joinpath(*phan)
        try:
            if p.exists():
                return str(p)
        except OSError:
            pass
    return ""


def _chay_lenh(cmd: list, han: int) -> tuple:
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


def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI vào log ngày.

    **Lùi êm mà im lặng thì đúng bằng hỏng âm thầm** — cùng luật với
    `piper_tts._ghi_log` và `dubbing._ghi_log_el`.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"giong_ngoai_{ts:%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Tiến trình con — SCRIPT ĐỘC LẬP, không `-m <module>`
# ---------------------------------------------------------------------------
#: Không dùng `-m app.core...`: bản `.exe` không chạy được và không có cây mã
#: nguồn để `-m` bám vào (bài học cổng 55). Việc và kết quả đi qua FILE JSON
#: chứ không qua dòng lệnh — chữ Việt/Trung/Nhật trên dòng lệnh Windows là
#: một đường vỡ bảng mã không cần thiết.
_MA_DOC = '''
import json, os, sys, time

job_path = sys.argv[1]
with open(job_path, "r", encoding="utf-8") as f:
    J = json.load(f)


def bao(p, m):
    sys.stdout.write("BQP\\t%.4f\\t%s\\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model doc...")
    import numpy as np
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    t0 = time.time()
    dung_gpu = torch.cuda.is_available()
    dev = "cuda" if dung_gpu else "cpu"
    m = OmniVoice.from_pretrained(
        J["model"], dtype=torch.bfloat16 if dung_gpu else torch.float32)
    m = m.to(dev)
    t_nap = time.time() - t0

    items = J["items"]
    texts = [it["text"] for it in items]
    langs = J.get("langs") or None
    ins = J.get("instruct") or ""
    kw = {}
    if langs:
        kw["language"] = langs
    if ins:
        kw["instruct"] = [ins] * len(texts)
    # KHONG truyen `duration`/`speed`: nut cua model thua `rubberband`
    # (do o luot 7). Ep khung lam o tien trinh cha bang ffmpeg.
    bao(0.25, "Dang doc %d cau (%s)..." % (len(texts), dev))
    t1 = time.time()
    with torch.no_grad():
        au = m.generate(text=texts, **kw)
    t_gen = time.time() - t1

    sr = int(m.sampling_rate)
    ra = []
    for i, a in enumerate(au):
        a = np.asarray(a, dtype="float32").reshape(-1)
        p = items[i]["raw"]
        sf.write(p, a, sr)
        ra.append({"i": items[i]["i"], "p": p,
                   "giay": round(len(a) / float(sr), 4)})
        bao(0.25 + 0.70 * (i + 1) / max(1, len(au)),
            "Ghi tieng %d/%d" % (i + 1, len(au)))

    ket = {"ok": True, "nap": round(t_nap, 2), "gen": round(t_gen, 2),
           "dev": dev, "sr": sr, "ra": ra,
           "vram": (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                    if dung_gpu else 0.0),
           "torch": getattr(torch, "__version__", "?")}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\\t" + json.dumps(ket) + "\\n")
sys.stdout.flush()
'''


def _viet_runner() -> Path:
    """Ghi script chạy ra `<thu_muc_ngoai>/_bq_giong_runner.py` (đè mỗi lượt)."""
    p = thu_muc_ngoai() / "_bq_giong_runner.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_MA_DOC, encoding="utf-8")
    return p


def _chay_ov(items: list[dict], model: str, py: str, instruct: str,
             langs: Optional[list[str]], han_giay: int,
             on_msg: Optional[Callable[[str], None]]) -> dict:
    """Gọi tiến trình con đọc cả loạt. Trả dict kết quả (không ném)."""
    runner = _viet_runner()
    sb = thu_muc_ngoai() / f"_job_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sb.mkdir(parents=True, exist_ok=True)
    job = sb / "job.json"
    job.write_text(json.dumps(
        {"model": model, "items": items, "instruct": instruct,
         "langs": langs}, ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Trọng số đã nằm trên đĩa -> CẤM đi hỏi mạng. Một lượt đọc giọng treo vì
    # mạng thì lỗi đội lốt "giọng đọc hỏng" và rất khó truy.
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"

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
                # `_sandbox` PHẢI có ở MỌI đường ra: nơi gọi làm
                # `_don(Path(ket.get("_sandbox") or ""))`, thiếu khoá là
                # `Path("")` = thư mục ĐANG LÀM VIỆC. Xem `_don`.
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
    """`"+25%"` -> 1,25. Trả 1.0 nếu không đọc được.

    KHÁC edge-tts MỘT ĐIỂM PHẢI BIẾT: với edge-tts, `rate=+50%` đo ra
    **1,455×** chứ không phải 1,50× (model tự đọc nhanh, không tuyến tính).
    `rubberband` cắt theo ĐỒNG HỒ nên ở đây `+50%` ra **đúng 1,500×**. Tức
    cùng một chuỗi `rate`, giọng ngoài ép MẠNH HƠN edge-tts một chút — đúng
    hướng an toàn (câu lọt khung), và `khop_thoi_gian` vẫn là người nói cuối.
    """
    try:
        s = str(rate or "").strip().rstrip("%")
        return max(0.25, min(4.0, 1.0 + float(s) / 100.0))
    except (TypeError, ValueError):
        return 1.0


def _ep_khung(nguon: Path, dich: Path, tempo: float) -> bool:
    """Ép `nguon` nhanh lên `tempo` lần rồi ghi ra `dich`. True = xong.

    DÙNG LẠI `thay_giong._co_gian_chuoi` chứ không viết chuỗi filter thứ hai:
    hàm đó đã canh sẵn chuyện ffmpeg máy nhân viên không có `rubberband`
    (lùi `atempo`, chia tầng khi > 2,0) và có công tắc `BQ_TG_RUBBERBAND=0`
    để đo A/B. Đẻ đường thứ hai là đẻ chỗ để hai đường lệch nhau.
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
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            creationflags=_NO_WIN)
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
# MỐC TỪNG CHỮ — GROQ CHÉP NGƯỢC (bộ này không trả mốc)
# ---------------------------------------------------------------------------
#: Dấu câu cần bóc khi so hai chuỗi từ. Groq và mình chấm câu khác nhau.
_DAU = ".,!?;:\"'“”…()-–—[]{}「」『』、。，！？；：《》"


def _chuan(w: str) -> str:
    return str(w or "").strip().strip(_DAU).lower()


def _lay_moc_groq(text: str, wav: str | Path) -> list:
    """Mốc `[[đầu, cuối, từ], ...]` cho `text`, dò trên CHÍNH file đã đọc.

    **Đây là chỗ yếu nhất của nhóm giọng ngoài, và phải nói thẳng:** hai bộ
    này KHÔNG trả mốc, nên mốc là do **máy nghe** (Groq whisper-large-v3)
    đọc ngược ra. Sai số của máy nghe **CỘNG THÊM** vào chứ không thay thế —
    khác hẳn `WordBoundary` của edge-tts (sự thật của chính máy đọc) và
    `/with-timestamps` của ElevenLabs.

    CÁCH LÀM (đúng đường `_do_piper_moc_that.py` đã dùng để đo, và đường
    `thay_giong.chep_loi` app vẫn chạy hằng ngày):
      1. Groq chép ngược file WAV -> danh sách từ CÓ MỐC.
      2. Căn chuỗi từ Groq với chuỗi từ mình GỬI ĐI bằng `SequenceMatcher`.
      3. Chữ hiện lên phải là **CHỮ GỐC**, mốc lấy của chữ Groq khớp được.

    **CHỮ HIỆN LÊN LẤY TỪ `text` GỐC, KHÔNG lấy chữ Groq chép ra.** Groq
    chép sai chính tả là chuyện thường (lượt 7 đo tiếng Việt sai 16,9%);
    lấy chữ của nó là vừa sai chữ vừa sai mốc.

    Từ nào không khớp thì **BỎ QUA, không nội suy** — mốc bịa còn tệ hơn
    thiếu mốc (bài học `piper_tts._lay_moc`: "thà không có mốc còn hơn mốc
    gán nhầm chữ").
    """
    from difflib import SequenceMatcher
    from app.ai import recap

    goc = [t for t in recap._word_tokens(text or "") if _chuan(t)]
    if not goc:
        return []
    try:
        from app.core import thay_giong as _tg
        d = _tg.chep_loi(str(wav))
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Groq chép ngược hỏng ({Path(wav).name}): "
                 f"{type(e).__name__}: {e} -> câu này KHÔNG có mốc")
        return []
    ws = d.get("words") or []
    if not ws:
        _ghi_log(f"Groq không trả mốc từ cho {Path(wav).name} -> câu này "
                 f"KHÔNG có mốc")
        return []
    that = [(_chuan(w.get("word") or ""), float(w.get("start") or 0.0),
             float(w.get("end") or 0.0)) for w in ws]
    that = [x for x in that if x[0]]
    if not that:
        return []

    sm = SequenceMatcher(None, [_chuan(t) for t in goc],
                         [x[0] for x in that], autojunk=False)
    moc: list = []
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            _t, s, e = that[b + k]
            moc.append([s, max(s, e), goc[a + k]])
    moc.sort(key=lambda m: m[0])
    return moc


# ---------------------------------------------------------------------------
# CỬA CHÍNH — cùng hợp đồng với `piper_tts.doc_loat`
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
             ) -> tuple[list[bool], list[list]]:
    """Đọc cả LOẠT câu bằng giọng ngoài. Cùng hợp đồng `_synth_all_words`.

    Trả `(ok, words)`: `ok[i]` = câu i đọc được chưa · `words[i]` =
    `[[đầu, cuối, từ], ...]`, rỗng nếu không lấy được mốc chắc chắn.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả `ok` toàn `False` để nơi gọi lùi về
    edge-tts (`dubbing._synth_all_words`).

    ═══ ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE — VÌ SAO ALL-OR-NOTHING ═══
    Đọc được 18/20 câu rồi để 2 câu kia lùi edge-tts thì video ra **LẪN HAI
    GIỌNG** giữa chừng — đúng cái mệnh đề cổng 63 canh, và mã thoát vẫn 0
    nên không ai biết. Vì vậy chỉ cần MỘT câu không đọc được là trả `ok`
    toàn `False`: cả video một giọng edge-tts, xấu hơn nhưng ĐỀU.
    (`BQ_GN_TY_LE` hạ ngưỡng xuống để đo/gỡ rối; đừng hạ trong sản xuất.)

    ═══ GOM CẢ LOẠT VÀO MỘT LƯỢT ═══
    Nạp model tốn 5-31 giây, nên gọi từng câu là mỗi câu trả lại từng ấy.
    Đọc ở tốc độ TỰ NHIÊN một lượt, rồi ép từng câu bằng `rubberband` —
    nhóm theo `rate` như Piper là vô ích ở đây vì `rate` không đi vào model.
    """
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]
    if n == 0:
        return ok, words

    def _xong_het() -> None:
        # Báo XONG cho MỌI câu kể cả câu rỗng/hỏng: nơi gọi ĐẾM số lần
        # `on_done` để chạy thanh tiến trình, thiếu một nhịp là thanh đứng
        # mãi không đủ (đúng cách `piper_tts.doc_loat` làm).
        for i in range(n):
            if on_done:
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass

    if la_giong_indextts(voice):
        tt = tinh_trang_indextts()
        _ghi_log(f"Giọng {voice}: IndexTTS chưa dựng được trên máy này "
                 f"(thiếu: {tt['thieu']}) -> LÙI về edge-tts")
        _xong_het()
        return ok, words

    if not la_giong_omnivoice(voice):
        _ghi_log(f"Mã giọng lạ {voice!r} -> LÙI về edge-tts")
        _xong_het()
        return ok, words

    tt = tinh_trang_omnivoice()
    if not tt["co"]:
        _ghi_log(f"Chưa dùng được OmniVoice (thiếu: {tt['thieu']}) -> LÙI "
                 f"về edge-tts")
        _xong_het()
        return ok, words
    if tt.get("o_tam"):
        # Chạy được, nhưng đang đứng trên đất mượn. Nói ra MỖI LƯỢT: im lặng
        # thì tới hôm mất mới biết, mà lúc đó triệu chứng lại là "giọng tự
        # nhiên biến khỏi combo" — không ai lần ra nguyên nhân.
        _ghi_log(f"CẢNH BÁO: môi trường OmniVoice đang nằm trong thư mục TẠM "
                 f"({tt['o_tam']}). Một lượt dọn đĩa là mất. Chỗ đúng: "
                 f"{tt['thu_muc']}\\venv")

    try:
        ok, words = _doc_omnivoice(texts, paths, voice, tt, rate, lang,
                                   lay_moc, han_giay, on_msg)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"OmniVoice hỏng ({type(e).__name__}: {e}) -> LÙI về "
                 f"edge-tts")
        ok, words = [False] * n, [[] for _ in range(n)]

    can = [i for i in range(n) if (texts[i] or "").strip()]
    duoc = [i for i in can if ok[i]]
    try:
        nguong = float(os.environ.get("BQ_GN_TY_LE", TY_LE_TOI_THIEU))
    except ValueError:
        nguong = TY_LE_TOI_THIEU
    if can and len(duoc) < nguong * len(can):
        _ghi_log(f"Chỉ đọc được {len(duoc)}/{len(can)} câu bằng {voice} -> "
                 f"BỎ CẢ LOẠT, lùi edge-tts (không để video lẫn hai giọng)")
        ok, words = [False] * n, [[] for _ in range(n)]

    _xong_het()
    return ok, words


def _doc_omnivoice(texts: list[str], paths: list[str], voice: str, tt: dict,
                   rate: str | list, lang: str, lay_moc: bool, han_giay: int,
                   on_msg: Optional[Callable[[str], None]],
                   ) -> tuple[list[bool], list[list]]:
    """Thân của `doc_loat` cho OmniVoice. Có thể ném — `doc_loat` bắt."""
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]

    can = [i for i in range(n) if (texts[i] or "").strip()]
    if not can:
        return ok, words

    sb = thu_muc_ngoai() / f"_tam_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    (sb / "raw").mkdir(parents=True, exist_ok=True)
    items = [{"i": i, "text": (texts[i] or "").strip().replace("\n", " "),
              "raw": str(sb / "raw" / f"c{i:04d}.wav")} for i in can]
    ten_ngon_ngu = _ten_ngon_ngu(lang)
    ket = _chay_ov(items, tt["model"], tt["python"],
                   _BANG_INSTRUCT.get(voice, ""),
                   [ten_ngon_ngu] * len(items) if ten_ngon_ngu else None,
                   han_giay, on_msg)
    if not ket.get("ok"):
        _ghi_log(f"OmniVoice đọc hỏng: {ket.get('loi')}")
        _don(sb)
        _don(Path(ket.get("_sandbox") or ""))
        return ok, words

    for r in ket.get("ra") or []:
        i = int(r.get("i", -1))
        if not (0 <= i < n):
            continue
        raw = Path(r.get("p") or "")
        # KHÔNG tin tiến trình con báo "ok" — ĐO lại file nó ghi ra. Cùng
        # một luật với "ffmpeg trả mã 0 mà file rỗng".
        if dai_wav(raw) <= 0.02:
            _ghi_log(f"OmniVoice ghi ra file 0 giây cho câu {i} -> bỏ")
            continue
        r_i = (rate[i] if isinstance(rate, list) and i < len(rate)
               else (rate if isinstance(rate, str) else "+0%"))
        dich = Path(paths[i])
        dich.parent.mkdir(parents=True, exist_ok=True)
        if not _ep_khung(raw, dich, _tempo_tu_rate(r_i)):
            continue
        ok[i] = True

    if lay_moc:
        for i in can:
            if not ok[i]:
                continue
            try:
                words[i] = _lay_moc_groq(texts[i], paths[i])
            except Exception as e:  # noqa: BLE001
                _ghi_log(f"Lấy mốc câu {i} hỏng (tiếng vẫn dùng được): "
                         f"{type(e).__name__}: {e}")

    _ghi_log(f"OmniVoice đọc {sum(1 for i in can if ok[i])}/{len(can)} câu · "
             f"nạp {ket.get('nap')}s · sinh {ket.get('gen')}s · "
             f"{ket.get('dev')} · VRAM {ket.get('vram')} GiB")
    _don(sb)
    _don(Path(ket.get("_sandbox") or ""))
    return ok, words


#: Tên ngôn ngữ OmniVoice hiểu. Khai báo tên giúp đọc chuẩn hơn (tài liệu gốc:
#: *"Performance is slightly better if you specify the language"*), nhưng
#: **nhãn LẠ thì để None** chứ không đoán — đoán sai ngôn ngữ tệ hơn không
#: khai (Groq từng gán `Norwegian Nynorsk` cho video tiếng Hàn, cổng 54).
_TEN_NGON_NGU = {
    "vi": "Vietnamese", "en": "English", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "th": "Thai", "fr": "French", "de": "German",
    "es": "Spanish", "ru": "Russian",
}


def _ten_ngon_ngu(lang: str) -> str:
    ma = str(lang or "").strip().lower().replace("_", "-").split("-")[0]
    return _TEN_NGON_NGU.get(ma, "")


def _don(d: Path) -> None:
    """Dọn thư mục tạm. KHÔNG BAO GIỜ NÉM (bài học rò `_seg_*`, cổng 42).

    ═══ ĐÃ XOÁ NHẦM CẢ REPO MỘT LẦN — 19/08/2026, ĐỪNG NỚI CHỐT NÀY ═══
    Bản cũ là ``if d and str(d) and d.is_dir(): shutil.rmtree(d)``. Trông vô
    hại, nhưng **``Path("")`` KHÔNG rỗng — nó là ``WindowsPath('.')``**, tức
    THƯ MỤC ĐANG LÀM VIỆC: ``str(d)`` ra ``'.'`` (truthy), ``d.is_dir()`` ra
    True, rồi ``rmtree('.')`` **xoá sạch cây mã**. Đã xảy ra THẬT: mất
    ``.git`` (chỉ còn ``objects``), ``.venv``, ``bin``, ``_lib``,
    ``_giong_hang``, ``_piper``, ``_giong_ngoai`` — phải dựng lại repo từ
    ``.git/objects``.

    Đường đi tới đó có sẵn trong chính file này: ``_doc_omnivoice`` gọi
    ``_don(Path(ket.get("_sandbox") or ""))`` ở nhánh LỖI, mà ``_chay_ov``
    **không đặt ``_sandbox`` ở nhánh quá-giờ và nhánh ném** -> ``.get`` trả
    None -> ``or ""`` -> ``Path("")``. Nghĩa là **một lượt OmniVoice quá giờ
    là xoá thư mục làm việc của anh Hùng**, im lặng, mã thoát vẫn 0.

    Nay hai lớp chắn: ``_chay_ov`` luôn đặt ``_sandbox`` (đường 1), và hàm này
    **CHỈ xoá thư mục nằm THẬT SỰ BÊN TRONG** ``thu_muc_ngoai()`` (đường 2).
    Hai lớp vì đường 1 dễ bị một bản vá sau làm hỏng lại mà không ai thấy.
    """
    try:
        if d is None or not str(d).strip():
            return
        p = Path(d).resolve()
        goc = thu_muc_ngoai().resolve()
        # `p == goc` cũng CẤM: hộp cát là thư mục CON, xoá cả gốc là xoá luôn
        # môi trường 7,7 GB.
        if p == goc or goc not in p.parents:
            _ghi_log(f"TỪ CHỐI dọn {p} — nằm ngoài {goc}")
            return
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
