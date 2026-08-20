# -*- coding: utf-8 -*-
"""KOKORO-82M — 54 giọng, Apache 2.0, chạy HẲN trên máy.

**TRẠNG THÁI: mới là MODULE, CHƯA NỐI VÀO `dubbing`/`giong_bang`.**
Đọc mục "CÒN PHẢI LÀM" ở cuối docstring trước khi tin nó chạy.

═══════════════════════════════════════════════════════════════════════════
GIẤY PHÉP — ĐÃ XÁC MINH TẠI KHO GỐC 19/08/2026, ĐỪNG TRA LẠI
═══════════════════════════════════════════════════════════════════════════
Kho `hexgrad/Kokoro-82M`, model card ghi **`apache-2.0`** → dùng thương mại
được, KHÁC hẳn `F5-TTS` (CC-BY-NC = cấm thương mại, đã LOẠI).
Dữ liệu huấn luyện **có KHAI RÕ**: public domain + audio giấy phép Apache/MIT
+ **audio tổng hợp từ TTS đóng của nhà cung cấp lớn**; kèm Koniwa (CC BY 3.0,
<1h) và SIWIS (CC BY 4.0, <11h) → phải ghi công ở `LICENSES.txt`.
Dòng "audio tổng hợp từ TTS đóng" ghi ra để không ai tưởng tôi giấu — tác giả
tự khai, giấy phép vẫn Apache 2.0, rất nhiều nơi dùng thương mại.

**KHÁC HẲN `Kokoro-Vietnamese` (đã LOẠI)** — bản đó GIẤU nguồn dữ liệu và có
3 tên trùng dàn giọng Vbee. Cùng chữ "Kokoro" nhưng hai thứ khác nhau; đừng
lấy nhầm.

`espeak-ng` là **GPL** → gọi như **CHƯƠNG TRÌNH RỜI** qua `subprocess`, đúng
khuôn `piper_tts.py`. **`import espeakng` MỘT DÒNG là mất quyền giữ kín mã.**
Máy này ĐÃ CÓ SẴN ở `_piper/piper/espeak-ng-data` — không phải tải.

═══════════════════════════════════════════════════════════════════════════
ĐIỂM CHẤT LƯỢNG DO CHÍNH TÁC GIẢ CHẤM (`VOICES.md`) — dùng làm nhãn, ĐỪNG BỊA
═══════════════════════════════════════════════════════════════════════════
    af_bella                      A-   <- CAO NHẤT CẢ BỘ
    am_fenrir · am_michael · am_puck   C+
    bm_fable · bm_george               C
    am_echo · am_eric · am_liam · am_onyx · bm_daniel   D
    bm_lewis                           D+
    am_santa                           D-
    **am_adam                          F+  <- THẤP NHẤT nam Mỹ**

**ANH HÙNG MUỐN KOKORO VÌ TƯỞNG NÓ CÓ ADAM HAY.** Nhãn PHẢI nói thẳng F+,
nếu không anh ấy lại thất vọng đúng như lần `vn:Adam` của VieNeu (*"nghe lạ
lạ, khác lắm"*). Cả bộ **không có giọng nam nào khá** — cao nhất chỉ C+.
Thứ đáng dùng ở đây là **`af_bella` (A-)**, không phải Adam.

Mốc so đã đo trong repo: `en-GB-Ryan` nhấn nhá **5,38** · edge-tts khớp chữ
**15,7 ms** · sai chữ **6,2%**. Kokoro **KHÔNG trả mốc từng chữ** → chữ chạy
theo tiếng phải nhờ `giong_hang` (phủ 98,6%) hoặc Groq chép ngược (tốn lượt,
phủ 38-99% tuỳ lượt). **Nhãn phải nói ra điều đó** — đây là chỗ Kokoro KÉM
HƠN cái anh Hùng đang có, ở đúng thứ anh ấy kêu nhiều nhất.

═══════════════════════════════════════════════════════════════════════════
CÒN PHẢI LÀM — 4 VIỆC, THIẾU BẤT KỲ CÁI NÀO LÀ "CHỌN X RA Y" IM LẶNG
═══════════════════════════════════════════════════════════════════════════
1. **`giong_bang`**: thêm hằng `KOKORO`, `("kk:", KOKORO)` vào `_TIEN_TO`,
   tên vào `TEN_NGUON`, xếp vào nhóm "Trên máy".
2. **`dubbing._synth_all` VÀ `_synth_all_words`** — cửa CHUNG, cạnh cửa
   Piper/VieNeu/Chatterbox. **KHÔNG sửa từng chỗ gọi**: cổng 63 phải vẫn đếm
   đúng 3 chỗ gọi của `thay_giong.py`; sót một chỗ là video ra **HAI GIỌNG
   TRỘN** mà mã thoát vẫn 0.
3. **Cổng mới**: GỌI THẬT `_synth_all_words` với `kk:...` rồi xem nó rẽ vào
   đâu — **đừng quét chuỗi** (quét chuỗi thì `x=False` vẫn khớp `x=`). Kèm
   tự-kiểm: gỡ chốt PHẢI đỏ. Nối `_chay_hoi_quy.py`.
4. **Đo 54 giọng**: mỗi giọng đọc thật ra WAV CÓ TIẾNG (độ dài + RMS, không
   phải 0 byte). **Câm thì KHÔNG cho vào combo**, ghi tên + lý do. Đếm giọng
   THẬT bằng **ECAPA** (Kani quảng cáo 18, đo ra 2; MFCC/cao độ là thước HỎNG:
   tự-ồn 97,7 > khoảng cách thật 48,4).

Ba lần đã sập vì thiếu bước 1-2: `ov:nu_am` chọn X ra Y · `vn:` module xong mà
`dubbing` không biết nên chọn "Minh Đức" ra giọng khác · `cb:` đăng ký thiếu
nên rơi nhóm `edge`. **Cả ba đều `rc=0`, không một dòng báo.**

═══════════════════════════════════════════════════════════════════════════
BA BẪY MÔI TRƯỜNG — mỗi cái đã cắn thật một lần
═══════════════════════════════════════════════════════════════════════════
· **`import torch` SAU khi Qt nạp = ACCESS VIOLATION** (`WinError 1114`),
  `try/except` KHÔNG chặn được → buộc chạy TIẾN TRÌNH RIÊNG. Dò "đã cài chưa"
  bằng **file có tồn tại không**, đừng `find_spec` (nó NẠP gói cha).
· **KHÔNG cài vào `.venv`** — anh Hùng đang chạy sản xuất 300 kênh; một lượt
  `pip install` kéo torch có thể phá app đang chạy.
· **KHÔNG để môi trường ở `%TEMP%`** (một lượt dọn ổ C là mất sạch, mà triệu
  chứng chỉ là *"giọng biến khỏi combo"* — không ai lần ra) và **KHÔNG cạnh
  `.exe`** (lượt tự cập nhật `rmdir /S /Q _internal.old` xoá mất). Bản đóng
  gói → `DATA_DIR`.
· Hậu kiểm sau khi cài phải **so `spec.origin` với thư mục đích**, đừng hỏi
  "import được không": máy dev mượn `.venv` rồi báo "cài xong" trong khi bản
  `.exe` rỗng. Bộ gióng hàng vừa dính đúng lỗi này hôm nay
  (`libtorchaudio.pyd` không nạp được vì thiếu torch trong `_giong_hang`).

Anh Hùng **KHÔNG chạy được lệnh cài** → mọi thứ phải qua **NÚT trong app**.
Nhãn ghi ĐÚNG số GB thật (`pip install --dry-run --report`, đừng ước) — đã có
2 lỗi nhãn: `250 MB` lặp 20 dòng và `6,1 GB` lặp 5 dòng làm anh Hùng đọc
thành 30,5 GB.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

#: Mã giọng trong combo: ``kk:af_bella``. Cùng quy ước ``vn:`` / ``cb:``.
TIEN_TO = "kk:"

#: 54 giọng + ĐIỂM DO TÁC GIẢ CHẤM. Điểm là chuỗi để in thẳng ra nhãn — đừng
#: quy sang số rồi so với `nhan_nha` (hai thang khác nhau, so là số lừa).
GIONG_KK: tuple[tuple[str, str, str], ...] = (
    # (mã, "giới tính · tiếng · mô tả", điểm tác giả chấm)
    ("af_bella",    "Nữ · Mỹ · giọng tốt nhất cả bộ",     "A-"),
    ("af_heart",    "Nữ · Mỹ · ấm",                       "A"),
    ("af_nicole",   "Nữ · Mỹ · thì thầm",                 "B-"),
    ("af_aoede",    "Nữ · Mỹ",                            "C+"),
    ("af_kore",     "Nữ · Mỹ",                            "C+"),
    ("af_sarah",    "Nữ · Mỹ",                            "C+"),
    ("af_alloy",    "Nữ · Mỹ",                            "C"),
    ("af_jessica",  "Nữ · Mỹ",                            "D"),
    ("af_nova",     "Nữ · Mỹ",                            "C"),
    ("af_river",    "Nữ · Mỹ",                            "D"),
    ("af_sky",      "Nữ · Mỹ",                            "C-"),
    ("am_fenrir",   "Nam · Mỹ",                           "C+"),
    ("am_michael",  "Nam · Mỹ",                           "C+"),
    ("am_puck",     "Nam · Mỹ",                           "C+"),
    ("am_echo",     "Nam · Mỹ",                           "D"),
    ("am_eric",     "Nam · Mỹ",                           "D"),
    ("am_liam",     "Nam · Mỹ",                           "D"),
    ("am_onyx",     "Nam · Mỹ",                           "D"),
    ("am_santa",    "Nam · Mỹ",                           "D-"),
    ("am_adam",     "Nam · Mỹ",                           "F+"),
    ("bf_emma",     "Nữ · Anh",                           "B-"),
    ("bf_isabella", "Nữ · Anh",                           "C"),
    ("bf_alice",    "Nữ · Anh",                           "D"),
    ("bf_lily",     "Nữ · Anh",                           "D"),
    ("bm_fable",    "Nam · Anh",                          "C"),
    ("bm_george",   "Nam · Anh",                          "C"),
    ("bm_daniel",   "Nam · Anh",                          "D"),
    ("bm_lewis",    "Nam · Anh",                          "D+"),
)

#: Giọng bị tác giả chấm dưới mức này thì nhãn phải KÊU. Không CHẶN — anh Hùng
#: đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*; chỉ nói thật.
DIEM_KEU = {"D", "D-", "D+", "F", "F+", "F-"}

#: Nhãn nút tải khai ở DƯỚI (`NHAN_TAI` / `NHAN_TAI_CUDA` + `nhan_tai()`),
#: cạnh `mb_se_tai()` đã ĐO thật bằng `--dry-run --report`. Trước đây có một
#: `NHAN_TAI = "…(chưa đo dung lượng)"` khai TRÙNG ở đúng chỗ này: Python lấy
#: bản sau nên nhãn hiện ra vẫn đúng, **nhưng ai đọc file từ trên xuống thì
#: thấy bản CŨ và tưởng app chưa đo** — đúng họ bẫy "phép đo phát chứng nhận
#: cho thứ đã lạc hậu". Một hằng số = MỘT chỗ khai, đặt cạnh phép đo của nó.

CANH_BAO = (
    "Kokoro KHÔNG trả mốc từng chữ — chữ chạy theo tiếng phải nhờ bộ gióng "
    "chữ (phủ 98,6%) hoặc máy nghe (tốn lượt mạng). Kém hơn edge-tts "
    "(15,7 ms, tự trả mốc) ở đúng chỗ đó."
)


def la_giong_kokoro(voice: str) -> bool:
    """Giọng này có thuộc file này không. KHÔNG BAO GIỜ NÉM."""
    return str(voice or "").startswith(TIEN_TO)


def tach_ma(voice: str) -> str:
    """``kk:af_bella`` -> ``af_bella``. Trả "" nếu không phải giọng Kokoro."""
    v = str(voice or "")
    return v[len(TIEN_TO):] if v.startswith(TIEN_TO) else ""


def thu_muc() -> Path:
    """Môi trường Kokoro. **KHÔNG `%TEMP%`, KHÔNG cạnh `.exe`** — xem docstring.

    Bản đóng gói dùng ``DATA_DIR`` vì lượt tự cập nhật xoá cả ``_internal``
    (bài học `_lib` cổng 58 CA5). Đọc `config.DATA_DIR` MỖI LẦN GỌI, đừng cất
    hằng số (bài học `tg_so.duong_so`).
    """
    if getattr(sys, "frozen", False):
        from config import DATA_DIR
        return Path(DATA_DIR) / "_giong_kokoro"
    return Path(__file__).resolve().parents[2] / "_giong_kokoro"


def python_rieng() -> Path:
    """Python của môi trường riêng. Chưa cài thì đường dẫn không tồn tại."""
    return thu_muc() / "venv" / "Scripts" / "python.exe"


def espeak_data() -> Path | None:
    """`espeak-ng-data` mượn từ bộ Piper đã có. None = chưa có.

    Gọi espeak như CHƯƠNG TRÌNH RỜI (GPL) — xem docstring.

    **BẢN `.exe` KHÔNG TÌM Ở `parents[2]` ĐƯỢC — ĐÃ SỬA 20/08/2026.** Trong bản
    đóng gói, `parents[2]` là `_internal`, mà bộ Piper tải về nằm ở
    `DATA_DIR/_piper` (`piper_tts.thu_muc_piper` cố ý đặt ngoài thư mục cài vì
    lượt tự cập nhật `rmdir /S /Q _internal.old` xoá sạch — cổng 58 CA 5). Bản
    cũ hỏi đúng một chỗ KHÔNG BAO GIỜ có gì, nên trên máy nhân viên
    `tinh_trang()["co"]` mãi mãi False -> **chọn giọng Kokoro là lùi êm về
    edge-tts vĩnh viễn**, kể cả sau khi đã tải đủ. Máy dev thì đúng, vì ở đây
    `parents[2]` CHÍNH LÀ repo. Đúng lớp bệnh "máy dev xanh, máy thật đỏ".
    """
    ds: list[Path] = []
    try:
        from app.core import piper_tts as _pt
        ds.append(Path(_pt.thu_muc_piper()) / "piper" / "espeak-ng-data")
    except Exception:  # noqa: BLE001 - thiếu module thì vẫn còn đường dưới
        pass
    ds.append(Path(__file__).resolve().parents[2] / "_piper" / "piper"
              / "espeak-ng-data")
    for p in ds:
        try:
            if p.is_dir():
                return p
        except OSError:
            pass
    return None


def espeak_trong_venv() -> Path | None:
    """`espeak-ng-data` do CHÍNH gói `espeakng_loader` mang theo. None = chưa có.

    **ĐÂY LÀ ĐƯỜNG CHÍNH, KHÔNG PHẢI ĐƯỜNG LÙI — đọc trước khi "dọn gọn".**
    `misaki/espeak.py` gọi `EspeakWrapper.set_data_path(espeakng_loader.
    get_data_path())` NGAY LÚC IMPORT, tức bộ dữ liệu này là thứ Kokoro dùng khi
    không ai đặt gì khác. `pip install kokoro` kéo theo `espeakng_loader` (đo
    thật: `espeakng-loader==0.2.4` nằm trong 92 gói pip giải ra) nên máy nào cài
    được Kokoro là máy đó CÓ bộ dữ liệu — không cần bộ Piper.
    Bản cũ đếm "thiếu espeak-ng-data (lấy từ bộ Piper)" vào `thieu` nên máy chưa
    tải Piper bị **CHẶN OAN** dù Kokoro chạy được.
    """
    sp = _thu_muc_goi(thu_muc() / "venv")
    if not sp:
        return None
    p = Path(sp) / "espeakng_loader" / "espeak-ng-data"
    try:
        return p if p.is_dir() else None
    except OSError:
        return None


def espeak_dung_duoc() -> tuple[str, str]:
    """(đường dẫn, nguồn) của bộ phiên âm. nguồn: 'piper' | 'kokoro' | ''.

    Ưu tiên bộ của Piper vì nó DÙNG CHUNG (một bộ cho cả hai máy đọc, đỡ 100 MB
    trùng lặp), nhưng thiếu nó KHÔNG phải là thiếu — xem `espeak_trong_venv`.
    """
    p = espeak_data()
    if p is not None:
        return str(p), "piper"
    v = espeak_trong_venv()
    if v is not None:
        return str(v), "kokoro"
    return "", ""


# ---------------------------------------------------------------------------
# DÒ ĐÃ CÀI CHƯA — HỎI "GÓI CÓ NẰM THẬT TRONG MÔI TRƯỜNG RIÊNG KHÔNG"
# ---------------------------------------------------------------------------
#: Gói PHẢI nằm THẬT trong site-packages của môi trường riêng. Chỉ tên TẦNG
#: TRÊN CÙNG: `PathFinder.find_spec("kokoro.pipeline", ...)` sẽ IMPORT gói cha
#: thật, mà nạp torch vào tiến trình app đã có Qt là ACCESS VIOLATION.
GOI_KK: tuple[str, ...] = ("kokoro", "misaki", "torch", "soundfile", "numpy")

#: Gói đưa cho pip. `kokoro` tự kéo `misaki`/`torch`/`numpy`/`transformers`/
#: `espeakng_loader` (đo: 92 gói); `soundfile` thì `_MA_DOC` cần để ghi WAV mà
#: `kokoro` KHÔNG khai phụ thuộc nó -> phải nêu tên tường minh.
GOI_PIP: tuple[str, ...] = ("kokoro", "soundfile")

#: Chỉ mục wheel của PyTorch — cùng hai địa chỉ `thay_giong` đang dùng.
CHI_MUC_TORCH_CPU = "https://download.pytorch.org/whl/cpu"
CHI_MUC_TORCH_CUDA = "https://download.pytorch.org/whl/cu126"

#: **SỐ ĐO 20/08/2026, KHÔNG ƯỚC** (`_do_kokoro_tai.py`): `pip install --dry-run
#: --report` để pip tự giải phép phụ thuộc, rồi **HTTP HEAD** trên chính 92
#: wheel nó chọn. Python 3.12, chỉ mục `cpu`:
#:     92 gói = **211,5 MB**  (riêng torch 2.13.0+cpu = 116,3 MB)
#: Trọng số tải riêng lúc chạy (qua Hugging Face, KHÔNG qua pip):
#:     `kokoro-v1_0.pth` **312,1 MB** + 28 gói giọng **14,0 MB** (0,50 MB/giọng)
#: -> TỔNG **537,6 MB ~ 538 MB**, khớp đúng `giong_bang._CAN_TAI[KOKORO]`.
#: Bung ra đĩa thì lớn hơn hẳn: venv **1.120 MB** + trọng số 313 MB. Nhãn nói
#: LƯỢNG TẢI vì đó là thứ người dùng ngồi chờ (đúng cách `_lib` của Demucs đã
#: sửa: nhãn cũ "2 GB" gấp 13 lần lượng tải thật).
MB_TAI_PIP = 211.5
MB_TRONG_SO = 312.1
MB_GIONG_28 = 14.0
MB_TAI = MB_TAI_PIP + MB_TRONG_SO + MB_GIONG_28          # 537,6

#: Bản CUDA: **2.569,7 MB** pip (torch 2.13.0+cu126 một mình **2.474,4 MB**) =
#: **+2.358,2 MB** so với bản cpu, tức tổng ~2,9 GB.
MB_TAI_PIP_CUDA = 2569.7

#: **MẶC ĐỊNH LẤY BẢN CPU, VÀ ĐÂY LÀ LÝ DO BẰNG SỐ — đừng đổi mà không đo.**
#: (a) `giong_bang._CAN_TAI[KOKORO]` ĐÃ PHÁT HÀNH con số **538 MB** ra đuôi dòng
#:     combo. Nút này đi đường CUDA là tải 2,9 GB cho một nhãn ghi 538 MB —
#:     đúng lỗi "nhãn không khớp đường sẽ đi" mà cổng 71 CA 4 sinh ra để chặn,
#:     chỉ đổi chiều (trước: nút ghi 155 MB, hộp doạ 2 GB).
#: (b) Kokoro là model **82 triệu tham số** — nhỏ hơn Demucs hàng chục lần. Đo
#:     được của Demucs (nhanh 9,28x nhờ GPU, cổng 71) **KHÔNG suy sang đây
#:     được**, và **chưa ai đo Kokoro trên GPU**. Trả 2.358 MB cho một cái lợi
#:     chưa đo là đúng thứ repo này cấm.
#: (c) Môi trường 1,4 GB trên máy dev đang chạy torch CPU và ĐÃ đọc ra WAV
#:     158.444 byte / 3,30 giây — tức đường CPU là đường ĐÃ CHỨNG MINH.
#: `BQ_KK_CUDA=1` chỉ để ĐO lại sau này; bật thì `nhan_tai()` tự đổi số theo
#: (nhãn luôn khớp đường sẽ đi, kể cả ở lối đo).
def xin_ban_cuda() -> bool:
    """Có ai cố ý đòi bản CUDA không (chỉ để ĐO). KHÔNG BAO GIỜ NÉM."""
    return str(os.environ.get("BQ_KK_CUDA", "")).strip() in ("1", "true", "True")


def mb_se_tai() -> float:
    """Số MB nút này SẼ tải, theo đúng đường nó sẽ đi."""
    if xin_ban_cuda():
        return MB_TAI_PIP_CUDA + MB_TRONG_SO + MB_GIONG_28
    return MB_TAI


#: Nhãn nút tải. **PHẢI KHỚP ĐƯỜNG SẼ ĐI** — đo bằng `--dry-run --report`
#: trước khi điền số, đừng ước (cổng 71 CA 4).
NHAN_TAI = "Tải giọng Kokoro (khoảng 538 MB)"
NHAN_TAI_CUDA = "Tải giọng Kokoro bản CUDA (khoảng 2,9 GB — CHƯA ĐO có nhanh hơn)"


def nhan_tai() -> str:
    """Nhãn nút ĐÚNG với đường sẽ đi. Đọc lại mỗi lần gọi (bài học
    `tg_so.duong_so`) — bật/tắt cờ đo giữa phiên thì nhãn phải đổi theo."""
    return NHAN_TAI_CUDA if xin_ban_cuda() else NHAN_TAI


def _thu_muc_goi(venv: Path) -> str:
    """site-packages của môi trường riêng. '' = chưa dựng."""
    for ten in ("Lib", "lib"):
        d = Path(venv) / ten / "site-packages"
        try:
            if d.is_dir():
                return str(d)
        except OSError:
            pass
    return ""


def do_goi_kokoro(venv: Optional[Path] = None) -> dict:
    """TỪNG gói đang nằm ở ĐÂU — **KHÔNG import một dòng nào**.

    Trả `{tên: {"venv": <đường trong môi trường riêng|"">, "he": <đường NGOÀI>,
    "nguon": "venv" | "hệ thống" | ""}}`.

    **HỎI ĐÚNG CÂU — bài học cổng 58, đã cắn hai lần.** Câu hỏi KHÔNG phải
    *"import được không"*: máy dev có `.venv` đầy đủ nên câu trả lời luôn là CÓ
    kể cả khi thư mục đích rỗng -> app báo "cài xong", còn bản `.exe` (không có
    gì để mượn) báo thiếu. Câu đúng là *"`spec.origin` có nằm THẬT dưới thư mục
    đích không"*, và nó cho ra CÙNG một câu trả lời ở cả hai máy **do xây
    dựng**, vì `PathFinder.find_spec(ten, [site_packages])` không hề nhìn
    `sys.path`.

    Dùng `PathFinder` chứ KHÔNG `importlib.util.find_spec`: `find_spec` phải NẠP
    gói cha (nạp torch sau Qt = ACCESS VIOLATION, `try/except` không chặn) và nó
    luôn tìm trên `sys.path` nên không trả lời được câu trên.
    """
    from importlib.machinery import PathFinder
    if venv is None:
        venv = thu_muc() / "venv"
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
        if g in ("", "namespace", "built-in", "frozen"):
            locs = list(getattr(s, "submodule_search_locations", None) or [])
            g = locs[0] if locs else ""
        return str(g or "")

    ra: dict = {}
    for ten in GOI_KK:
        o_venv = _tim(ten, duong) if duong else ""
        he = "" if o_venv else _tim(ten, None)
        ra[ten] = {"venv": o_venv, "he": he,
                   "nguon": "venv" if o_venv else ("hệ thống" if he else "")}
    return ra


# ---------------------------------------------------------------------------
# PYTHON DÙNG ĐỂ DỰNG MÔI TRƯỜNG — CÓ HẠN TRÊN, ĐO ĐƯỢC
# ---------------------------------------------------------------------------
#: Bản Python **ĐÃ ĐO CHẠY ĐƯỢC** (môi trường 1,4 GB trên máy này là 3.12.10).
BAN_PY_DO = (3, 12)

#: Sàn của chính `kokoro` (`requires_python >= 3.10`).
BAN_PY_TOI_THIEU = (3, 10)

#: **TRẦN TRÊN — ĐO ĐƯỢC 20/08/2026, KHÔNG PHÒNG XA.** `_do_kokoro_tai.py` chạy
#: `pip install --dry-run` cho `kokoro soundfile` bằng **Python 3.14.0** (đúng
#: bản mà bản `.exe` sẽ gọi: `which python` trên máy này ra `C:\Python314`):
#: cả hai chỉ mục đều **`metadata-generation-failed`**. Cơ chế: một gói trong
#: cây phụ thuộc (đám C/Rust của `spacy`/`thinc`/`tokenizers`) chưa có wheel
#: `cp314`, pip lùi dần về bản `kokoro` CŨ, bản cũ đó ghim **`numpy==1.26.4`**
#: (wheel chỉ tới cp312) nên pip đi biên dịch numpy từ mã nguồn rồi chết:
#: *"Unknown compiler(s): [['icl'], ['cl'], ['cc'], ['gcc'], ...]"* — máy nhân
#: viên KHÔNG BAO GIỜ có MSVC.
#: Cùng lệnh, Python **3.12.10** giải ra 92 gói / 211,5 MB, `numpy==2.5.2`, sạch.
#: Vì vậy phải CHỌN bản Python, không phải lấy cái đầu tiên `which` trả về:
#: lấy bừa là nút tải chết bằng một lời lỗi trình biên dịch mà không ai đọc nổi.
#: 3.13 KHÔNG có trên máy này nên **chưa đo** — cho đi qua (đúng khoảng
#: `requires_python`) nhưng xếp SAU 3.12 và 3.11.
BAN_PY_TOI_DA = (3, 13)

#: Thứ tự thử qua `py` launcher: bản ĐÃ ĐO trước, rồi tới bản chưa đo.
_UU_TIEN_PY = ((3, 12), (3, 11), (3, 13), (3, 10))

#: Cache lượt dò (mỗi lượt là một `subprocess`, mà `tinh_trang()` bị gọi cho
#: MỖI mẻ đọc). None = chưa dò. Kết quả không đổi trong một phiên chạy.
_PY_CAI: Optional[list[str]] = None
_PY_CAI_THAY: str = ""


def _ban_python(cmd: list[str]) -> tuple[int, int]:
    """(major, minor) của một lệnh python. (0, 0) = không gọi được."""
    try:
        r = subprocess.run(
            [*cmd, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, creationflags=_NO_WIN)
        if r.returncode != 0:
            return 0, 0
        a, _, b = (r.stdout or "").strip().partition(".")
        return int(a), int(b)
    except Exception:  # noqa: BLE001
        return 0, 0


def _ung_vien_python() -> list[list[str]]:
    """Các lệnh python đáng thử, theo thứ tự ưu tiên."""
    ds: list[list[str]] = []
    if not getattr(sys, "frozen", False):
        # Chạy từ nguồn: python của `.venv` (3.12 trên máy này) — đúng bản đã
        # dựng nên môi trường 1,4 GB đang chạy được.
        ds.append([sys.executable])
    pyl = shutil.which("py")
    if pyl:
        for a, b in _UU_TIEN_PY:
            ds.append([pyl, f"-{a}.{b}"])
    for ten in ("python.exe", "python3.exe", "python", "python3"):
        p = shutil.which(ten)
        if p and [p] not in ds:
            ds.append([p])
    return ds


def python_cai(lam_lai: bool = False) -> list[str]:
    """Lệnh python dùng để DỰNG môi trường Kokoro. `[]` = máy này không cài được.

    **KHÔNG lấy `sys.executable` ở bản `.exe`** — chỗ đó là `BQHungVideo.exe`,
    gọi `-m venv` vào nó là vô nghĩa (đúng cách `piper_tts._python_chay` và
    `giong_ngoai._python_he_thong` đã làm).

    **VÀ KHÔNG LẤY BẢN ĐẦU TIÊN `which` TRẢ VỀ** — xem `BAN_PY_TOI_DA`: trên
    chính máy này `which python` ra **3.14.0**, mà 3.14 làm pip đi biên dịch
    numpy từ mã nguồn rồi chết vì thiếu MSVC.
    """
    global _PY_CAI, _PY_CAI_THAY
    if _PY_CAI is not None and not lam_lai:
        return list(_PY_CAI)
    thay: list[str] = []
    chon: list[str] = []
    for cmd in _ung_vien_python():
        v = _ban_python(cmd)
        if v == (0, 0):
            continue
        thay.append(f"{v[0]}.{v[1]}")
        if BAN_PY_TOI_THIEU <= v <= BAN_PY_TOI_DA and not chon:
            chon = list(cmd)
    _PY_CAI = chon
    _PY_CAI_THAY = ", ".join(dict.fromkeys(thay))
    return list(chon)


def vi_sao_khong_cai_duoc() -> str:
    """Câu nói THẲNG vì sao nút tải bị khoá. '' = cài được.

    Nút xám mà không nói vì sao chỉ là câu đố (bài học cổng 58/16/51).
    """
    if python_cai():
        return ""
    thay = _PY_CAI_THAY
    if not thay:
        return ("Máy này không có Python nên app không tự tải được: cài "
                "Python 3 (bản 3.12, python.org) rồi bấm lại, hoặc copy thư "
                "mục _giong_kokoro từ máy đã cài sang.")
    return ("Máy này chỉ có Python " + thay + " mà bộ Kokoro chưa có bản dựng "
            "sẵn cho bản đó (pip phải tự biên dịch numpy và chết vì máy không "
            "có trình biên dịch C). Cài thêm Python "
            f"{BAN_PY_DO[0]}.{BAN_PY_DO[1]} (python.org) rồi bấm lại, hoặc "
            "copy thư mục _giong_kokoro từ máy đã cài sang.")


# ---------------------------------------------------------------------------
# CHỖ TRỐNG TRÊN ĐĨA — HỎI TRƯỚC KHI TẢI
# ---------------------------------------------------------------------------
#: Cần bấy nhiêu MB TRỐNG mới dám tải: venv bung ra **1.120 MB** + trọng số
#: **313 MB** (đo trên chính máy này) + 15% chỗ thở cho lượt giải nén của pip.
MB_CAN_TRONG = 1650.0


def dia_trong_mb(cho: Optional[Path] = None) -> float:
    """Số MB còn trống ở ổ chứa `cho`. -1.0 = không đo được. KHÔNG BAO GIỜ NÉM.

    Đi LÊN dần tới thư mục CHA có thật: `thu_muc()` thường chưa tồn tại lúc hỏi,
    mà `disk_usage` trên đường dẫn không tồn tại thì ném.
    """
    try:
        p = Path(cho or thu_muc()).resolve()
    except Exception:  # noqa: BLE001
        return -1.0
    for _ in range(8):
        try:
            if p.exists():
                return shutil.disk_usage(str(p)).free / 1024 / 1024
        except OSError:
            pass
        if p.parent == p:
            break
        p = p.parent
    return -1.0


def tinh_trang() -> dict:
    """Máy này đã dùng được Kokoro chưa? KHÔNG tải gì, KHÔNG gọi mạng.

    Trả {co, du_venv, thieu, ngoai_venv, nguon, duong, thu_muc, venv, so_giong,
    espeak, espeak_nguon, co_trong_so, cai_duoc, vi_sao, mb_tai}.
    **KHÔNG BAO GIỜ NÉM.**

    Đọc cho đúng — ba khoá này trả lời BA CÂU KHÁC NHAU (bài học cổng 58):

    · **`thieu`** = gói KHÔNG nằm trong môi trường riêng. **Đây đúng là cái bản
      `.exe` sẽ thấy.** Nhãn/nút phải bám khoá này, ĐỪNG bám `co`.
    · **`du_venv`** = `not thieu` — môi trường tự đứng được một mình chưa.
    · **`co`** = đọc được không. Ở đây `co == du_venv` **do xây dựng**, vì bước
      đọc chạy bằng `python_rieng()` (python CỦA môi trường riêng) nên không có
      gì để mượn của `.venv` — khác hẳn Demucs, chỗ `co` và `du_lib` lệch nhau
      trên máy dev. `ngoai_venv` vẫn được trả về để nói ra chuyện *"gói này máy
      có nhưng nằm ngoài môi trường riêng"*, tức KHÔNG dùng được.

    Dò bằng `PathFinder` trên ĐÚNG site-packages của môi trường riêng, **không**
    `find_spec` — `find_spec` phải NẠP gói cha, mà nạp torch trong tiến trình đã
    có Qt là ACCESS VIOLATION.
    """
    d = thu_muc()
    venv = d / "venv"
    thieu: list[str] = []
    goi: dict = {}
    try:
        if not python_rieng().is_file():
            thieu.append("môi trường Python riêng")
        goi = do_goi_kokoro(venv)
        thieu += [t for t in GOI_KK if not goi[t]["venv"]]
        dat, ngn = espeak_dung_duoc()
        if not dat:
            thieu.append("espeak-ng-data")
    except Exception as e:  # noqa: BLE001 - hàm này KHÔNG BAO GIỜ NÉM
        _ghi_log(f"tinh_trang hỏng: {type(e).__name__}: {e}")
        dat, ngn = "", ""
        if not thieu:
            thieu.append("không dò được môi trường")
    ngoai = [t for t in GOI_KK if goi.get(t, {}).get("he")]
    return {
        "co": not thieu,
        "du_venv": not thieu,
        "thieu": thieu,
        "ngoai_venv": ngoai,
        "goi": goi,
        "nguon": {t: goi.get(t, {}).get("nguon", "") for t in GOI_KK},
        "duong": {t: (goi.get(t, {}).get("venv")
                      or goi.get(t, {}).get("he", "")) for t in GOI_KK},
        "thu_muc": str(d),
        "venv": str(venv),
        "so_giong": len(GIONG_KK),
        "espeak": dat,
        "espeak_nguon": ngn,
        "co_trong_so": co_trong_so(),
        "cai_duoc": bool(python_cai()),
        "vi_sao": vi_sao_khong_cai_duoc(),
        "mb_tai": mb_se_tai(),
    }


def duong_trong_so() -> Path:
    """Chỗ Hugging Face cất trọng số (`HF_HOME` mà `_chay_kokoro` đặt)."""
    return thu_muc() / "hf"


def co_trong_so() -> bool:
    """Trọng số 312 MB đã nằm trên đĩa chưa. KHÔNG BAO GIỜ NÉM.

    Dò bằng FILE, không hỏi thư viện: `kokoro-v1_0.pth` là tên do chính kho
    `hexgrad/Kokoro-82M` đặt. Thiếu nó thì lượt đọc ĐẦU TIÊN phải tải 312 MB
    giữa lúc anh Hùng đang chờ một video — nói ra trước thì đỡ tưởng app treo.
    """
    try:
        return any(duong_trong_so().rglob("kokoro-v1_0.pth"))
    except Exception:  # noqa: BLE001
        return False


# ==========================================================================
# TẢI BỘ KOKORO — **CHỈ khi NGƯỜI DÙNG BẤM**
# ==========================================================================
#: Một lượt tải là 538 MB — hai lượt chồng nhau vào cùng thư mục là hỏng cả hai
#: (user bấm hai lần vẫn phải ra MỘT lượt).
_KHOA_CAI = threading.Lock()

#: Mã kéo TRỌNG SỐ về, chạy ở **TIẾN TRÌNH RIÊNG bằng python CỦA môi trường
#: riêng**. Cùng ràng buộc `_MA_DOC`: `import torch` trong tiến trình đã nạp Qt
#: là ACCESS VIOLATION mà `try/except` KHÔNG chặn được.
#:
#: Nó đọc THẬT một câu ngắn, không chỉ tải file. Lý do: "thư mục đầy" chưa bao
#: giờ là bằng chứng chạy được (bài học `--target` của `giong_ngoai`), và bước
#: này là lần DUY NHẤT app có cớ chạy Kokoro mà không ai đang đợi một video.
_MA_TAI_TS = r'''
import json, os, sys, time

hf, giong, ra_wav, dat = sys.argv[1:5]
os.environ["HF_HOME"] = hf
if dat and os.path.isdir(dat):
    os.environ["PHONEMIZER_ESPEAK_DATA_PATH"] = dat
    os.environ["ESPEAK_DATA_PATH"] = dat


def bao(p, m):
    sys.stdout.write("BQP\t%.4f\t%s\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap thu vien Kokoro...")
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    if dat and os.path.isdir(dat):
        try:
            from phonemizer.backend.espeak.wrapper import EspeakWrapper
            EspeakWrapper.set_data_path(dat)
        except Exception:
            pass
    bao(0.20, "Tai trong so Kokoro (khoang 312 MB)...")
    t0 = time.time()
    pipe = KPipeline(lang_code=("b" if giong[:1].lower() == "b" else "a"),
                     repo_id="hexgrad/Kokoro-82M")
    t_nap = time.time() - t0
    bao(0.80, "Doc thu mot cau de kiem...")
    manh = []
    for r in pipe("Kokoro voice is ready.", voice=giong, speed=1.0):
        a = getattr(r, "audio", None)
        if a is None:
            continue
        manh.append(np.asarray(a, dtype="float32").reshape(-1))
    if not manh:
        raise RuntimeError("khong sinh duoc am nao")
    a = np.concatenate(manh) if len(manh) > 1 else manh[0]
    sf.write(ra_wav, a, 24000)
    ket = {"ok": True, "nap": round(t_nap, 2), "wav": ra_wav,
           "giay": round(len(a) / 24000.0, 3),
           "torch": ""}
    try:
        import torch
        ket["torch"] = getattr(torch, "__version__", "?")
        ket["thiet_bi"] = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        pass
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\t" + json.dumps(ket) + "\n")
sys.stdout.flush()
'''


def _chay_ghi_log(args: list[str], han: int,
                  prog: Optional[Callable[[float, str], None]] = None,
                  p0: float = 0.0, p1: float = 0.9,
                  nhip: float = 900.0) -> tuple[int, list[str], dict]:
    """Chạy một lệnh, gom log, báo tiến độ, trả (mã thoát, log, BQJSON).

    Mã thoát `-1` = quá giờ (đã giết). Đăng ký tiến trình con để bấm Huỷ giết
    được nó. KHÔNG BAO GIỜ NÉM — hỏng thì trả mã thoát khác 0.
    """
    log: list[str] = []
    ket: dict = {}
    p = None
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", bufsize=1,
                             creationflags=_NO_WIN)
        _gan_job(p)
        han_luc = time.time() + han
        n = 0
        for dong in p.stdout or ():
            dong = dong.rstrip()
            if not dong:
                continue
            if dong.startswith("BQJSON\t"):
                try:
                    ket = json.loads(dong.split("\t", 1)[1])
                except ValueError:
                    ket = {}
                continue
            if dong.startswith("BQP\t"):
                phan = dong.split("\t", 2)
                if prog and len(phan) > 2:
                    try:
                        prog(p0 + (p1 - p0) * float(phan[1]), phan[2])
                    except (ValueError, TypeError):
                        pass
                continue
            log.append(dong)
            n += 1
            # KHÔNG biết trước tổng byte -> % chỉ là dấu hiệu "đang chạy", và
            # trần `p1` để không khoe xong trước khi xong.
            if prog:
                prog(min(p1, p0 + (p1 - p0) * n / nhip), dong[-110:])
            if time.time() > han_luc:
                p.kill()
                return -1, log, ket
        return p.wait(timeout=180), log, ket
    except Exception as e:  # noqa: BLE001
        log.append(f"{type(e).__name__}: {e}")
        return 1, log, ket
    finally:
        if p is not None:
            _bo_gan_job(p)


def cai_kokoro(on_progress: Optional[Callable[[float, str], None]] = None,
               han_giay: int = 7200, tai_trong_so: bool = True) -> dict:
    """TẢI + CÀI bộ giọng Kokoro. **CHỈ chạy khi NGƯỜI DÙNG BẤM.**

    Trả `{ok, loi, giay, venv, thieu, goi, tinh_trang, trong_so, canh_bao,
    nhat_ky}`. **KHÔNG BAO GIỜ NÉM** — hỏng thì `ok=False` + `loi` (đúng ý
    *"trả (False, lý do)"*, chỉ đóng trong dict cho khớp `cai_demucs`/
    `cai_piper`/`cai_omnivoice` mà UI đang gọi) và ghi
    `logs/kokoro_<ngày>.log`.

    ═══ KHÔNG BAO GIỜ CÀI VÀO `.venv` ═══
    `.venv` là môi trường anh Hùng đang chạy sản xuất 300 kênh. Một lượt
    `pip install` kéo theo torch/transformers khác bản có thể phá app ĐANG
    chạy — đúng lý do Demucs phải ở `_lib` (cổng 55), VieNeu ở
    `_giong_vieneu` (cổng 79), OmniVoice ở `_giong_ngoai` (cổng 72).

    ═══ VÌ SAO **VENV** CHỨ KHÔNG `--target` NHƯ `_lib`/`_piper` ═══
    Module này đã chọn venv từ đầu (`python_rieng()` = `<thu_muc>/venv/Scripts/
    python.exe`, và `_chay_kokoro` spawn ĐÚNG file đó) — đổi sang `--target` là
    vứt bỏ môi trường 1,4 GB đang chạy được trên máy này. Nó cũng là lựa chọn
    ĐÚNG cho đúng bộ gói này, theo phép đo đã ghi ở `giong_ngoai.cai_omnivoice`:
    `--target` chỉ CHÉP file rồi nhét vào `sys.path` của MỘT python KHÁC, nên
    gói biên dịch cho `cp312` nằm đủ 4 GB trong thư mục mà python `cp314` nạp
    vào là `ImportError` phần mở rộng C. Cả 5 gói ở đây (torch · numpy ·
    soundfile · tokenizers · thinc) đều có phần mở rộng nhị phân.
    Venv thì có **python CỦA NÓ**: pip cài cho đúng bản đang đứng đó, không
    mượn gì của ai, không thể lệch ABI **do xây dựng** — và đó cũng là lý do
    `tinh_trang()['co']` ở đây nói thật trên CẢ máy dev lẫn bản `.exe`.

    ═══ `--ignore-installed` — CỜ QUYẾT ĐỊNH, ĐỪNG GỠ ═══
    pip coi gói đã có trong môi trường ĐANG CHẠY là "đã thoả mãn" rồi BỎ QUA,
    không chép vào đích. Đó đúng là cách `_lib` của Demucs thiếu torch mà máy
    dev vẫn báo "cài xong" (cổng 58: mọi gói CÓ trong `_lib` đều là gói `.venv`
    KHÔNG có, mọi gói THIẾU đều là gói `.venv` ĐÃ CÓ — một phép chia đôi hoàn
    hảo). Ở venv trắng thì gần như không có gì để bỏ qua, nhưng cờ này khiến
    kết quả **không phụ thuộc bản pip** — và `_lib` đã chứng minh hành vi cũ có
    thật.

    ═══ HẬU KIỂM SO `spec.origin` VỚI THƯ MỤC ĐÍCH ═══
    **ĐỪNG hỏi "import được không"** — máy dev mượn `.venv` rồi báo cài xong
    trong khi bản `.exe` rỗng. Lỗi này đã cắn hai lần (cổng 58 và bộ gióng
    hàng). Xem `do_goi_kokoro`.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(max(0.0, min(1.0, p)), m)
            except Exception:  # noqa: BLE001
                pass

    t0 = time.time()
    d = thu_muc()
    venv = d / "venv"
    ra: dict = {"ok": False, "loi": "", "venv": str(venv), "giay": 0.0,
                "nhat_ky": [], "canh_bao": ""}

    def xong(loi: str = "", **kw) -> dict:
        ra.update(kw)
        ra["loi"] = loi
        ra["ok"] = not loi
        ra["giay"] = round(time.time() - t0, 2)
        _ghi_log(("Cài Kokoro XONG vào " + str(venv)) if not loi
                 else ("Cài Kokoro HỎNG: " + loi[:300]))
        return ra

    try:
        py = python_cai()
        if not py:
            return xong(vi_sao_khong_cai_duoc())

        # ═══ `df` TRƯỚC KHI TẢI ═══
        # Ổ C của máy anh Hùng đã đầy 100% một lần (30/07) và hậu quả là
        # **studio.db vỡ** — tải 538 MB vào ổ gần đầy là mở lại đúng cửa đó.
        # Hỏi ổ chứa thư mục đích (bản `.exe` -> DATA_DIR, có thể khác ổ repo).
        trong = dia_trong_mb(d)
        if 0 <= trong < MB_CAN_TRONG:
            return xong(
                f"Ổ đĩa chứa {d} chỉ còn {trong:,.0f} MB trống, cần khoảng "
                f"{MB_CAN_TRONG:,.0f} MB (tải {mb_se_tai():,.0f} MB rồi bung "
                "ra đĩa còn to hơn). Dọn bớt đĩa rồi bấm lại."
                .replace(",", "."))

        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return xong(f"Không tạo được thư mục {d}: {e}")

        if not _KHOA_CAI.acquire(blocking=False):
            return xong("Đang tải rồi — đợi lượt này xong.")
        try:
            nhat_ky: list[str] = []
            # ---- 1. dựng môi trường Python riêng ----
            vpy = str(python_rieng())
            if not Path(vpy).is_file():
                prog(0.02, "Đang dựng môi trường Python riêng...")
                ma, log, _ = _chay_ghi_log([*py, "-m", "venv", str(venv)], 900)
                nhat_ky += log[-10:]
                if ma != 0 or not Path(vpy).is_file():
                    return xong(f"Dựng môi trường Python hỏng (mã {ma}): "
                                + " | ".join(log[-3:]), nhat_ky=nhat_ky)

            # ---- 2. pip install vào ĐÚNG môi trường đó ----
            cuda = xin_ban_cuda()
            chi_muc = CHI_MUC_TORCH_CUDA if cuda else CHI_MUC_TORCH_CPU
            # `--extra-index-url` (KHÔNG `--index-url`): chỉ mục của pytorch
            # không có `kokoro`/`misaki`/`soundfile` nên ép cả lượt vào đó là
            # hỏng phép giải (bài học `cai_demucs`).
            args = [vpy, "-m", "pip", "install", "--no-input",
                    "--disable-pip-version-check", "--upgrade",
                    "--ignore-installed",
                    "--extra-index-url", chi_muc, *GOI_PIP]
            prog(0.05, ("Đang tải bộ giọng Kokoro (khoảng "
                        f"{mb_se_tai():,.0f} MB, chạy 1 lần)..."
                        .replace(",", ".")))
            ma, log, _ = _chay_ghi_log(args, han_giay, prog, 0.05, 0.60,
                                       nhip=1200.0)
            nhat_ky += log[-40:]
            if ma == -1:
                return xong(f"Tải quá {han_giay}s, đã dừng.", nhat_ky=nhat_ky)
            if ma != 0:
                return xong(f"pip trả mã {ma}: " + " | ".join(log[-4:]),
                            nhat_ky=nhat_ky)

            # ---- 3. HẬU KIỂM: gói có nằm THẬT trong môi trường riêng không ----
            # `PathFinder` nhớ nội dung thư mục theo mtime, mà pip vừa ghi vào,
            # nên phải xoá bộ nhớ đó — không thì lượt kiểm ngay sau khi cài vẫn
            # thấy thư mục như lúc chưa cài rồi báo THIẾU oan.
            prog(0.62, "Đang kiểm lại từng gói...")
            import importlib
            importlib.invalidate_caches()
            goi = do_goi_kokoro(venv)
            thieu = [g for g in GOI_KK if not goi[g]["venv"]]
            if thieu:
                return xong(
                    "pip trả mã 0 nhưng những gói này KHÔNG nằm trong "
                    + str(venv) + ": " + ", ".join(thieu)
                    + ". Đừng coi là đã cài — bản .exe sẽ không chạy được.",
                    goi=goi, thieu=thieu, nhat_ky=nhat_ky)
            ra.update({"goi": goi, "thieu": []})

            # ---- 4. trọng số + ĐỌC THỬ MỘT CÂU ----
            # Không tính vào `ok`: gói đã đủ thì lượt đọc đầu tiên tự tải trọng
            # số được (thư viện tự lo). Nhưng nếu bỏ bước này thì 312 MB đó bị
            # tải GIỮA LÚC anh Hùng đang chờ một video, và triệu chứng là "app
            # treo". Hỏng ở đây -> `canh_bao`, KHÔNG phải `loi`.
            if tai_trong_so:
                prog(0.65, "Đang tải trọng số Kokoro (khoảng 312 MB)...")
                kq = _thu_doc(vpy, han_giay, prog)
                ra["trong_so"] = kq
                if not kq.get("ok"):
                    ra["canh_bao"] = (
                        "Đã cài xong thư viện, nhưng chưa tải được trọng số / "
                        "chưa đọc thử được: " + str(kq.get("loi") or "")[:300]
                        + " — lượt đọc đầu tiên sẽ tự tải (chậm hơn).")
                    _ghi_log("Cài Kokoro: " + ra["canh_bao"])

            prog(1.0, "Đã cài xong bộ giọng Kokoro.")
            return xong("", tinh_trang=tinh_trang(), nhat_ky=nhat_ky,
                        cuda=cuda, chi_muc=chi_muc)
        finally:
            try:
                _KHOA_CAI.release()
            except RuntimeError:
                pass
    except Exception as e:  # noqa: BLE001 - hàm này KHÔNG BAO GIỜ NÉM
        return xong(f"{type(e).__name__}: {e}"[:400])


def _thu_doc(vpy: str, han_giay: int,
             prog: Optional[Callable[[float, str], None]] = None) -> dict:
    """Kéo trọng số về rồi ĐỌC THỬ một câu. Trả dict, KHÔNG NÉM.

    Đọc thử bằng **`af_bella`** vì đó là giọng tác giả tự chấm cao nhất (A-);
    trọng số model dùng chung nên chọn giọng nào cũng tải đúng 312 MB đó.
    """
    ma_lot = _ma_lot()
    sb = thu_muc() / f"_cai_{ma_lot}"
    runner = thu_muc() / f"_bq_kokoro_tai_{ma_lot}.py"
    try:
        sb.mkdir(parents=True, exist_ok=True)
        runner.write_text(_MA_TAI_TS, encoding="utf-8")
        wav = sb / "thu.wav"
        dat, _ngn = espeak_dung_duoc()
        ma, log, ket = _chay_ghi_log(
            [vpy, "-u", str(runner), str(duong_trong_so()), "af_bella",
             str(wav), dat], han_giay, prog, 0.65, 0.97, nhip=200.0)
        if ma == -1:
            return {"ok": False, "loi": f"quá {han_giay}s (bỏ cuộc)"}
        if not ket:
            return {"ok": False,
                    "loi": f"mã thoát {ma}: " + (" | ".join(log[-3:]) or "?")}
        if not ket.get("ok"):
            return ket
        # **ĐỪNG TIN TIẾN TRÌNH CON BÁO OK** — đo lại chính file nó ghi ra
        # (cùng lý lẽ `_kiem_wav` ở đường đọc thật: `sf.write` một mảng toàn 0
        # cho ra file hợp lệ hoàn hảo mà CÂM).
        dung, vi_sao = _kiem_wav(wav)
        if not dung:
            return {"ok": False, "loi": "đọc thử ra file không dùng được: "
                                        + vi_sao}
        try:
            ket["byte"] = wav.stat().st_size
        except OSError:
            pass
        ket["co_trong_so"] = co_trong_so()
        return ket
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "loi": f"{type(e).__name__}: {e}"}
    finally:
        _don(sb)
        try:
            runner.unlink(missing_ok=True)
        except OSError:
            pass


def co_kokoro() -> bool:
    """Có chạy được không. KHÔNG BAO GIỜ NÉM."""
    try:
        return bool(tinh_trang()["co"])
    except Exception:
        return False


#: Dấu dán vào nhãn giọng khi máy CHƯA có bộ Kokoro. **PHẢI CÓ CHỮ "CHƯA
#: TẢI"** — Piper đã làm đúng từ cổng 64 và đó là thứ duy nhất cho anh Hùng biết
#: TRƯỚC khi bấm; không có nó thì anh ấy chọn `kk:af_bella`, app lùi êm về
#: edge-tts (có ghi `logs/kokoro_*.log`, nhưng anh ấy không đọc log) rồi ngồi
#: nghe một giọng khác hẳn cái mình chọn — đúng bẫy "chọn X ra Y" mà `ov:nu_am`,
#: `vn:` và `cb:` đã sập ba lần.
#:
#: **CỐ Ý MANG CẢ CỤM "cần tải"** dù câu đọc hơi lặp: `giong_bang._DO_TRUNG[
#: KOKORO]` dò đúng cụm đó để THÔI dán đuôi *"· miễn phí (Apache 2.0), cần tải
#: bộ 538 MB, KHÔNG có tiếng Việt, KHÔNG có mốc từng chữ"* vào cuối dòng. Không
#: có cụm này thì một dòng combo nói HAI LẦN cùng một chuyện và dài gấp đôi. (Ở
#: Piper, `_DO_TRUNG[PIPER]` có sẵn cả "chưa tải" nên nhãn nó không cần —
#: `giong_bang.py` đang do luồng khác giữ, không sửa được, nên chỗ nhường là
#: đây.)
DAU_CHUA_TAI = (" · CHƯA TẢI (cần tải bộ {mb} MB một lần, dùng chung cho cả "
                "{n} giọng) — chọn giọng này thì app vẫn chạy nhưng sẽ đọc "
                "bằng giọng thường (edge-tts)")


def dau_chua_tai(tt: Optional[dict] = None) -> str:
    """Dấu "CHƯA TẢI" cho nhãn giọng. "" khi máy đã có đủ. KHÔNG BAO GIỜ NÉM."""
    try:
        tt = tt if tt is not None else tinh_trang()
        if tt.get("co"):
            return ""
        mb = float(tt.get("mb_tai") or MB_TAI)
    except Exception:  # noqa: BLE001
        mb = MB_TAI
    # Dấu nghìn kiểu Việt: đổi RIÊNG con số rồi mới ghép. `.replace(",", ".")`
    # trên CẢ câu thì nó ăn luôn dấu phẩy của câu tiếng Việt ("một lần, dùng
    # chung" -> "một lần. dùng chung") — đã sập ngay lượt thử đầu.
    return DAU_CHUA_TAI.format(mb=f"{mb:,.0f}".replace(",", "."),
                               n=len(GIONG_KK))


def nhan_giong(ma: str, tt: Optional[dict] = None) -> str:
    """Nhãn một dòng cho combo — **nói thật điểm tác giả chấm VÀ nói thật là
    máy chưa tải**.

    Giọng bị chấm dưới `DIEM_KEU` thì nhãn KÊU. Không chặn, không giấu: anh
    Hùng đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*.

    `tt` = kết quả `tinh_trang()` đã dò sẵn. **NƠI GỌI VÒNG LẶP PHẢI TRUYỀN
    VÀO**: `tinh_trang()` đi `PathFinder` + `rglob` trọng số, gọi 28 lần cho
    28 dòng combo là 28 lượt quét đĩa cho một câu trả lời duy nhất.
    """
    for m, mo_ta, diem in GIONG_KK:
        if m != ma:
            continue
        # Cụm này CỐ Ý NGẮN. Bản đầu ghi thêm ", nên chọn giọng khác" (21 ký tự)
        # và cổng 84 đo được: **12 dòng** — đúng 12 giọng bị chấm thấp — dài quá
        # nên bị cắt **đúng chỗ chữ "cần tải"** của đuôi `giong_bang.duoi_dong`.
        # Tức lời khuyên "nên chọn giọng khác" đã ĐẨY MẤT thông tin quan trọng
        # hơn nó (máy chưa tải bộ 538 MB thì chọn giọng này ra giọng KHÁC).
        # Giữ đúng cụm "TÁC GIẢ CHẤM THẤP" — cổng 87 CA 10b dò chính chữ đó, và
        # phần lời khuyên đã nằm trong tooltip của combo.
        canh = " — TÁC GIẢ CHẤM THẤP" if diem in DIEM_KEU else ""
        # **KHÔNG tự dán "· miễn phí" ở đây.** `giong_bang.duoi_dong` đã dán một
        # bản GIÀU HƠN ("miễn phí (Apache 2.0), cần tải bộ 538 MB, KHÔNG có
        # tiếng Việt, KHÔNG có mốc từng chữ"), mà `_DO_TRUNG[KOKORO]` chỉ dò chữ
        # *"cần tải"* nên nó KHÔNG thấy chữ "miễn phí" của tôi -> dòng combo nói
        # **"miễn phí" HAI LẦN** rồi dài quá và **bị cắt đúng chỗ chữ "cần
        # tải"** — tức mất đúng cảnh báo mà anh Hùng cần thấy nhất.
        # Cổng 84 đo được: 13 dòng thiếu thông tin "phải tải", ví dụ
        # «… · điểm A- · miễn phí - chưa đo tiếng · miễn phí (Apache 2.0), cần…»
        # Bỏ nó đi thì vừa hết nói hai lần vừa còn chỗ cho phần bị cắt.
        return f"{m} — {mo_ta} (Kokoro) · điểm {diem}{canh}" + dau_chua_tai(tt)
    return ma


def danh_sach_giong() -> list[tuple[str, str]]:
    """[(mã, nhãn)] để đổ vào combo. Giọng điểm cao lên trên.

    **TRẢ ĐỦ 28 GIỌNG KỂ CẢ KHI MÁY CHƯA TẢI** — chỉ đổi NHÃN, không ẩn dòng.
    Anh Hùng đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*, và đây đúng tiền lệ
    Piper/VieNeu (app TỰ TẢI được nên còn hiện dòng "chưa tải"); chỉ OmniVoice
    6,1 GB mới phải giấu vì app không tự tải được nó.
    """
    thang = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-",
             "D+", "D", "D-", "F+", "F", "F-"]
    def khoa(r: tuple[str, str, str]) -> tuple[int, str]:
        try:
            return (thang.index(r[2]), r[0])
        except ValueError:
            return (len(thang), r[0])
    tt = tinh_trang()                    # DÒ MỘT LẦN cho cả 28 dòng
    return [(TIEN_TO + m, nhan_giong(m, tt))
            for m, _mo_ta, _d in sorted(GIONG_KK, key=khoa)]


#: Kho trọng số trên Hugging Face. GHIM tường minh — thư viện tự mặc định về
#: đúng kho này nhưng in ra một dòng ``WARNING`` mỗi lượt, mà dòng đó lẫn vào
#: stdout của tiến trình con (nơi `_chay_kokoro` đang dò `BQP`/`BQJSON`).
KHO_HF = "hexgrad/Kokoro-82M"

#: Tần số mẫu Kokoro sinh ra. HẰNG SỐ CỦA MODEL (`KModel` 24 kHz) — đừng đọc
#: từ đâu khác rồi ghi vào WAV sai nhịp: sai `sr` là tiếng nhanh/chậm mà file
#: vẫn hợp lệ, `_kiem_wav` KHÔNG bắt được (nó chỉ hỏi có tiếng không).
SR = 24000

#: Câm thì phải KÊU: RMS dưới mức này coi như không có tiếng. `thay_giong.
#: _kiem_wav` đã chặn ca RMS == 0; ngưỡng này bắt thêm ca "có tiếng nhưng nhỏ
#: đến mức không nghe ra" (giọng hỏng thường ra nhiễu nền chứ không im hẳn).
RMS_TOI_THIEU = 0.002


def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI vào `logs/kokoro_<ngày>.log`. KHÔNG BAO GIỜ NÉM.

    **Lùi êm mà im lặng thì đúng bằng hỏng âm thầm** — cùng luật với
    `piper_tts._ghi_log` / `giong_vieneu._ghi_log` / `giong_ngoai._ghi_log`.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"kokoro_{ts:%Y%m%d}.log", "a", encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


def ma_tieng(ma: str) -> str:
    """Mã giọng -> `lang_code` của `KPipeline`. `af_/am_` -> `a`, `bf_/bm_` -> `b`.

    **KHÔNG ĐOÁN, ĐỌC TỪ CHÍNH MÃ GIỌNG.** `KPipeline` `assert lang_code in
    LANG_CODES` nên đưa sai là NÉM ngay; nhưng nguy hơn là đưa `a` cho giọng
    Anh-Anh: lúc đó thư viện in *"Language mismatch, loading b voice into a
    pipeline"* rồi **VẪN ĐỌC** bằng bộ phiên âm Mỹ — tiếng ra được, chỉ là sai
    trọng âm, và không một dòng nào tố giác.
    """
    return "b" if str(ma or "")[:1].lower() == "b" else "a"


# ---------------------------------------------------------------------------
# Tiến trình con — SCRIPT ĐỘC LẬP, KHÔNG `-m <module>`
# ---------------------------------------------------------------------------
#: **BẮT BUỘC CHẠY Ở TIẾN TRÌNH RIÊNG, KHÔNG PHẢI ĐỂ CHO GỌN.** `import torch`
#: trong tiến trình đã nạp Qt ném `OSError [WinError 1114] ... c10.dll` và
#: `try/except` KHÔNG chặn được (cổng 55 tái hiện 100%). App này LÀ app Qt.
#:
#: Không `-m app.core...`: bản `.exe` không có cây mã nguồn để `-m` bám vào
#: (bài học cổng 55). Việc và kết quả đi qua FILE JSON chứ không qua dòng lệnh.
#:
#: **espeak-ng LÀ GPL — nó chỉ được phép sống TRONG script này.** App không
#: `import` một dòng nào của nó; dữ liệu phiên âm truyền vào bằng BIẾN MÔI
#: TRƯỜNG (`BQ_ESPEAK_DATA`). Lưu ý đã đo: `misaki/espeak.py` gọi
#: `EspeakWrapper.set_data_path(espeakng_loader.get_data_path())` NGAY LÚC
#: IMPORT, và `_ESPEAK_DATA_PATH` của lớp ĐÈ LÊN mọi biến môi trường
#: (`wrapper.py:214` xét nó TRƯỚC `PHONEMIZER_ESPEAK_DATA_PATH`) -> muốn dùng
#: bộ dữ liệu dùng chung của Piper thì phải đặt LẠI SAU khi import, đúng như
#: dưới đây. Đặt env mà không đặt lại là bản vá không bao giờ chạy.
_MA_DOC = r'''
import json, os, sys, time

with open(sys.argv[1], "r", encoding="utf-8") as f:
    J = json.load(f)


def bao(p, m):
    sys.stdout.write("BQP\t%.4f\t%s\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model Kokoro...")
    _dat = (J.get("espeak_data") or "").strip()
    if _dat and os.path.isdir(_dat):
        os.environ["PHONEMIZER_ESPEAK_DATA_PATH"] = _dat
        os.environ["ESPEAK_DATA_PATH"] = _dat

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    # SAU khi kokoro/misaki da import (misaki ghi cung data_path luc import).
    if _dat and os.path.isdir(_dat):
        try:
            from phonemizer.backend.espeak.wrapper import EspeakWrapper
            EspeakWrapper.set_data_path(_dat)
        except Exception:
            pass

    t0 = time.time()
    pipe = KPipeline(lang_code=J["lang_code"], repo_id=J["repo_id"])
    t_nap = time.time() - t0
    sr = int(J.get("sr", 24000))

    items = J["items"]
    ra = []
    t1 = time.time()
    for k, it in enumerate(items):
        manh = []
        moc = []
        loi = ""
        try:
            for r in pipe(it["text"], voice=J["voice"],
                          speed=float(J.get("speed", 1.0))):
                a = getattr(r, "audio", None)
                if a is None:
                    continue
                a = np.asarray(a, dtype="float32").reshape(-1)
                # Mot cau co the ra NHIEU manh -> moc cua manh sau phai
                # CONG DON offset, khong thi moi manh lai bat dau tu 0.
                off = sum(len(x) for x in manh) / float(sr)
                for t in (getattr(r, "tokens", None) or []):
                    a0 = getattr(t, "start_ts", None)
                    a1 = getattr(t, "end_ts", None)
                    w = str(getattr(t, "text", "") or "").strip()
                    if a0 is None or a1 is None or not w:
                        continue
                    moc.append([round(off + float(a0), 3),
                                round(off + float(a1), 3), w])
                manh.append(a)
        except Exception as e:
            loi = "%s: %s" % (type(e).__name__, e)
        if not manh:
            ra.append({"i": it["i"], "p": "", "giay": 0.0,
                       "loi": loi or "khong sinh duoc am nao"})
            continue
        a = np.concatenate(manh) if len(manh) > 1 else manh[0]
        sf.write(it["raw"], a, sr)
        ra.append({"i": it["i"], "p": it["raw"],
                   "giay": round(len(a) / float(sr), 4),
                   "manh": len(manh), "moc": moc})
        bao(0.10 + 0.85 * (k + 1) / max(1, len(items)),
            "Doc cau %d/%d" % (k + 1, len(items)))
    t_gen = time.time() - t1

    ket = {"ok": True, "nap": round(t_nap, 2), "gen": round(t_gen, 2),
           "sr": sr, "ra": ra}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\t" + json.dumps(ket) + "\n")
sys.stdout.flush()
'''

_NO_WIN = 0x08000000 if os.name == "nt" else 0


def _viet_runner(ma_lot: str) -> Path:
    """Ghi script chạy ra `<thu_muc>/_bq_kokoro_runner_<mã lượt>.py`.

    **MỘT FILE MỘT LƯỢT GỌI — đã hỏng thật ở `giong_hang`, đừng "dọn gọn".**
    Dùng chung một đường dẫn thì `write_text` mở chế độ `w` = **CẮT CỤT ngay**
    file mà tiến trình con của luồng kia đang đọc; còn ghi tên tạm rồi
    `os.replace` (nguyên tử trên POSIX) thì **Windows từ chối thay file ĐANG
    MỞ** (`PermissionError [WinError 5]`, đo được ngay lượt song song đầu). Làn
    thay giọng mặc định **2 luồng**, nên đây là ca chắc chắn gặp.
    """
    d = thu_muc()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"_bq_kokoro_runner_{ma_lot}.py"
    p.write_text(_MA_DOC, encoding="utf-8")
    return p


def _ma_lot() -> str:
    """Mã DUY NHẤT cho MỘT lượt gọi. Dùng lại `giong_hang._ma_lot`.

    KHÔNG viết bộ sinh mã thứ hai: `giong_hang._ma_lot` đã mang đúng bài học
    (`p<pid>t<luồng>n<đếm>` — `pid` một mình là giống hệt nhau cho mọi luồng
    trong app). Module đó không kéo theo torch nên import ở đây an toàn.
    Hỏng thì tự lo bằng pid+luồng+đồng hồ, không được ném.
    """
    try:
        from app.core import giong_hang as _gh
        return _gh._ma_lot()
    except Exception:  # noqa: BLE001
        import threading
        return (f"p{os.getpid()}t{threading.get_ident()}"
                f"n{int(time.time() * 1000) % 1000000}")


def _don(d: Path | None) -> None:
    """Dọn hộp cát. KHÔNG BAO GIỜ NÉM, và KHÔNG BAO GIỜ ra ngoài `thu_muc()`.

    **`Path("")` KHÔNG RỖNG — nó là `WindowsPath('.')`**, tức THƯ MỤC ĐANG LÀM
    VIỆC: `str()` ra `'.'` (truthy), `is_dir()` ra True, rồi `rmtree('.')`
    **xoá sạch cây mã** với mã thoát 0. Đã xảy ra thật 19/08/2026
    (`giong_ngoai._don`). Đi qua cửa chung `xoa_an_toan` + còn tự kẹp trong
    `thu_muc()` (hai lớp, cố ý thừa — lớp trong là lớp chịu lực).

    ═══ KHÔNG CÓ ĐƯỜNG LÙI `shutil.rmtree` TRẦN — CỐ Ý, ĐỪNG THÊM LẠI ═══
    Bản đầu (v2.41.0) có một nhánh lùi `shutil.rmtree(p, ignore_errors=True)`
    cho ca "import `xoa_an_toan` hỏng". **Cổng 87 xanh nhưng CỔNG 80 bắt được**
    (CA 6 quét tĩnh bằng AST: mọi file `app/` gọi `shutil.rmtree` phải nằm trong
    sổ 9 file đã rà). Hai lý do bỏ hẳn thay vì ghi tên file vào sổ:

    1. Nhánh lùi ấy nằm dưới `except Exception` bọc **CẢ lượt gọi**, nên một lỗi
       **BÊN TRONG** `don_thu_muc` cũng rơi xuống rmtree trần — tức chốt chung bị
       vô hiệu hoá đúng lúc nó đang hỏng. Đó là *đường lùi âm thầm*, họ bẫy mà cả
       repo này chống.
    2. `xoa_an_toan` là module CÙNG GÓI. Nó không import được thì app đã hỏng
       nặng, và lúc đó thứ đúng đắn là **bỏ lại thư mục tạm** (nằm gọn trong
       `thu_muc()`, `tempsweep` dọn sau) chứ không phải tự tay gọi rmtree.
    `piper_tts.py` đã đi đúng đường này từ trước (cổng 80 đo: `rmtree=False` ·
    `gọi don_thu_muc=True`) nên đây là làm cho khớp, không phải phát minh.
    """
    try:
        if d is None or not str(d).strip():
            return
        p = Path(d).resolve()
        goc = thu_muc().resolve()
        if p == goc or goc not in p.parents:
            _ghi_log(f"TỪ CHỐI dọn {p} — nằm ngoài {goc}")
            return
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(p, trong=goc, ghi_log=_ghi_log)
    except Exception as e:  # noqa: BLE001 - dọn rác KHÔNG BAO GIỜ được ném
        # GHI LOG chứ không im lặng: "không dọn được" phải đọc ra được, nếu
        # không thì thư mục tạm phình lên mà không ai biết vì sao.
        _ghi_log(f"không dọn được {d}: {type(e).__name__}: {e}")


def _gan_job(p) -> None:
    """Đăng ký tiến trình con để bấm Huỷ GIẾT ĐƯỢC nó. KHÔNG BAO GIỜ NÉM."""
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


def _chay_kokoro(items: list[dict], ma: str, han_giay: int,
                 on_msg: Optional[Callable[[str], None]] = None,
                 speed: float = 1.0) -> dict:
    """Gọi tiến trình con đọc CẢ LOẠT một lượt. Trả dict (KHÔNG ném)."""
    ma_lot = _ma_lot()
    runner = _viet_runner(ma_lot)
    sb = thu_muc() / f"_job_{ma_lot}"
    (sb / "raw").mkdir(parents=True, exist_ok=True)
    # Đường ghi ra do ĐÂY đặt (nơi biết hộp cát), nơi gọi chỉ đưa chữ. Để nơi
    # gọi tự đặt là mở đường cho hai lượt ghi chung một tên file.
    items = [dict(it, raw=str(sb / "raw" / f"c{int(it['i']):04d}.wav"))
             for it in items]
    job = sb / "job.json"
    job.write_text(json.dumps(
        {"items": items, "voice": ma, "lang_code": ma_tieng(ma),
         "repo_id": KHO_HF, "sr": SR, "speed": float(speed),
         "espeak_data": str(espeak_data() or "")},
        ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Trọng số để CẠNH môi trường, KHÔNG trong `%TEMP%`: một lượt dọn ổ C là
    # "giọng tự nhiên biến khỏi combo" và không ai lần ra (bài học `_lib` cổng
    # 58 CA5, và môi trường OmniVoice 7,74 GB từng nằm ở đó).
    env.setdefault("HF_HOME", str(thu_muc() / "hf"))
    dat = espeak_data()
    if dat:
        # Truyền qua BIẾN MÔI TRƯỜNG — app KHÔNG import gì của espeak (GPL).
        env["BQ_ESPEAK_DATA"] = str(dat)
        env["PHONEMIZER_ESPEAK_DATA_PATH"] = str(dat)
        env["ESPEAK_DATA_PATH"] = str(dat)

    ket: dict = {}
    duoi: list[str] = []
    ma_thoat: Optional[int] = None
    p = None
    try:
        p = subprocess.Popen(
            [str(python_rieng()), "-u", str(runner), str(job)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, env=env,
            creationflags=_NO_WIN)
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
                # `_sandbox` PHẢI có ở MỌI đường ra — thiếu nó thì nơi gọi
                # nhận `Path("")` = `rmtree('.')`. Đúng chỗ đã xoá cây mã.
                return {"ok": False, "loi": f"quá {han_giay}s (bỏ cuộc)",
                        "_sandbox": str(sb), "_runner": str(runner)}
        ma_thoat = p.wait(timeout=120)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "loi": f"{type(e).__name__}: {e}",
                "_sandbox": str(sb), "_runner": str(runner)}
    finally:
        if p is not None:
            _bo_gan_job(p)
    if not ket:
        ket = {"ok": False,
               "loi": (f"mã thoát {ma_thoat}: "
                       + (" | ".join(duoi[-4:]) or "không rõ"))}
    ket["_sandbox"] = str(sb)
    ket["_runner"] = str(runner)
    return ket


def _do_wav(p: Path) -> tuple[float, float]:
    """(độ dài giây, RMS) của WAV. `(0.0, 0.0)` nếu đọc không được.

    Đọc THẲNG mẫu bằng `wave` + `audioop` thay vì gọi ffmpeg: hàm này chạy cho
    TỪNG câu (hàng chục lượt/video) và chỉ cần trả lời "có tiếng không".
    """
    try:
        import audioop
        import wave
        with wave.open(str(p), "rb") as w:
            fr = w.getframerate() or 0
            n = w.getnframes()
            if not fr or not n:
                return 0.0, 0.0
            raw = w.readframes(n)
            rms = audioop.rms(raw, w.getsampwidth()) / 32768.0
            return n / float(fr), rms
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def _kiem_wav(p: Path) -> tuple[bool, str]:
    """(dùng được không, lý do nếu không). **ĐỪNG TIN TIẾN TRÌNH CON BÁO OK.**

    Ba lớp, mỗi lớp bắt một ca đã xảy ra thật trong repo: file KHÔNG CÓ · file
    RỖNG (mã thoát 0 mà 0 byte) · file CÓ mà **CÂM** (đúng bẫy *thành công
    giả*: `sf.write` ghi ra một mảng toàn 0 thì file hợp lệ hoàn hảo).
    """
    if not p.exists():
        return False, "không có file"
    try:
        cỡ = p.stat().st_size
    except OSError as e:
        return False, f"không đọc được ({e})"
    if cỡ < 1024:
        return False, f"file rỗng ({cỡ} byte)"
    d, rms = _do_wav(p)
    if d < 0.05:
        return False, f"chỉ {d:.3f} giây"
    if rms < RMS_TOI_THIEU:
        return False, f"CÂM (RMS {rms:.5f} < {RMS_TOI_THIEU})"
    return True, ""


def _speed_tu_rate(rate) -> float:
    """`"+25%"` -> 1,25. Không đọc được -> 1,0.

    Kokoro có núm `speed` THẬT trong `KPipeline.__call__` (nhân vào `pred_dur`
    của bộ dự đoán độ dài) nên đọc nhanh bằng núm model, KHÔNG phải `atempo`
    cắt-dán (đo được 5,4-8,1 dB méo phổ, cổng 53).

    `rate` là LIST (mỗi câu một tốc độ) thì lấy **1,0 cho cả loạt**: một lượt
    gọi chỉ nạp model một lần và núm `speed` áp cho cả lượt, nên ép từng câu
    phải làm ở tầng khác. Trả 1,0 là "không đụng gì" — an toàn, không bịa.
    """
    if isinstance(rate, (list, tuple)):
        return 1.0
    try:
        s = str(rate or "").strip().rstrip("%")
        return max(0.5, min(2.0, 1.0 + float(s) / 100.0))
    except (TypeError, ValueError):
        return 1.0


#: Đọc được dưới tỉ lệ này thì BỎ CẢ LOẠT. Xem "ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE" ở
#: `doc_loat`. `BQ_KK_TY_LE` chỉ để đo/gỡ rối, đừng hạ trong sản xuất.
TY_LE_TOI_THIEU = 1.0


def doc_loat(texts: list[str], paths: list[str], voice: str,
             on_done: Optional[Callable[[int], None]] = None,
             rate: str | list = "+0%",
             lang: str = "en",
             han_giay: int = 1800,
             on_msg: Optional[Callable[[str], None]] = None,
             **_kw) -> list[bool]:
    """Đọc cả loạt trong MỘT lượt gọi tiến trình con. Trả `ok[i]` từng câu.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả toàn `False` để nơi gọi
    (`dubbing._synth_all` / `_synth_all_words`) lùi êm về edge-tts, và **ghi
    lý do** vào `logs/kokoro_<ngày>.log` — lùi êm mà im lặng thì đúng bằng
    hỏng âm thầm.

    **MỐC TỪNG CHỮ KHÔNG ĐI QUA ĐÂY.** Hàm trả `list[bool]` chứ không
    `(ok, words)`: mốc lấy ở cửa chung `dubbing._moc_giong_hang` (gióng hàng
    cưỡng bức, cổng 73) — cùng đường Chatterbox đang đi. Xem `moc_thu` nếu cần
    đọc mốc do CHÍNH Kokoro dự đoán (đã đo, chưa dùng — xem docstring hàm đó).

    ═══ ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE ═══
    Đọc được 18/20 câu rồi để 2 câu kia lùi edge-tts thì video ra **LẪN HAI
    GIỌNG** giữa chừng, mà `rc` vẫn 0 nên không ai biết — đúng mệnh đề cổng 63
    canh. Nên một câu hỏng là trả `False` cả loạt: cả video một giọng, xấu hơn
    nhưng ĐỀU.

    ═══ GOM CẢ LOẠT VÀO MỘT LƯỢT ═══
    Mỗi lượt gọi nạp lại model (~2,2 s đo ở `piper_tts`), nên gọi từng câu là
    trả cái giá đó nhân số câu. Ở đây còn đắt hơn vì tiến trình con phải nạp
    cả torch.
    """
    n = len(texts)
    ok = [False] * n

    def _xong_het() -> None:
        # Báo XONG cho MỌI câu kể cả câu rỗng/hỏng: nơi gọi ĐẾM số lần
        # `on_done` để chạy thanh tiến trình, thiếu một nhịp là thanh đứng mãi.
        for i in range(n):
            if on_done:
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass

    if n == 0 or len(paths) < n:
        if n:
            _ghi_log(f"số câu ({n}) khác số file ({len(paths)}) -> bỏ qua")
        _xong_het()
        return ok

    ma = tach_ma(voice)
    if not ma:
        _ghi_log(f"Mã giọng lạ {voice!r} -> LÙI về edge-tts")
        _xong_het()
        return ok

    tt = tinh_trang()
    if not tt["co"]:
        _ghi_log(f"Chưa dùng được Kokoro (thiếu: {tt['thieu']}) -> LÙI về "
                 f"edge-tts")
        _xong_het()
        return ok

    can = [i for i in range(n) if str(texts[i] or "").strip()]
    if not can:
        _xong_het()
        return ok

    ket: dict = {}
    try:
        items = [{"i": i,
                  "text": str(texts[i]).strip().replace("\n", " ")}
                 for i in can]
        ket = _doc(items, ma, paths, rate, han_giay, on_msg)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Kokoro hỏng ({type(e).__name__}: {e}) -> LÙI về edge-tts")
        ket = {}

    for i in ket.get("ok_i") or ():
        if 0 <= i < n:
            ok[i] = True

    duoc = [i for i in can if ok[i]]
    try:
        nguong = float(os.environ.get("BQ_KK_TY_LE", TY_LE_TOI_THIEU))
    except ValueError:
        nguong = TY_LE_TOI_THIEU
    if len(duoc) < nguong * len(can):
        _ghi_log(f"Chỉ đọc được {len(duoc)}/{len(can)} câu bằng {voice} -> BỎ "
                 f"CẢ LOẠT, lùi edge-tts (không để video lẫn hai giọng)")
        ok = [False] * n

    _xong_het()
    return ok


def _doc(items: list[dict], ma: str, paths: list[str], rate,
         han_giay: int, on_msg: Optional[Callable[[str], None]]) -> dict:
    """Thân thật: chạy tiến trình con, KIỂM từng file, chép về `paths`.

    Có thể ném — `doc_loat` bắt. Trả `{"ok_i": [...], "moc": {...}}`.
    """
    ket = _chay_kokoro(items, ma, han_giay, on_msg, _speed_tu_rate(rate))
    sb = Path(ket.get("_sandbox") or "")
    runner = ket.get("_runner") or ""
    try:
        if not ket.get("ok"):
            _ghi_log(f"Kokoro đọc hỏng ({ma}): {ket.get('loi')}")
            return {"ok_i": [], "moc": {}}

        ok_i: list[int] = []
        moc: dict[int, list] = {}
        for r in ket.get("ra") or []:
            i = int(r.get("i", -1))
            raw = Path(r.get("p") or "")
            if not r.get("p"):
                _ghi_log(f"Kokoro không sinh được câu {i} ({ma}): "
                         f"{r.get('loi')}")
                continue
            # **KHÔNG TIN TIẾN TRÌNH CON BÁO OK** — đo lại file nó ghi ra.
            dung, vi_sao = _kiem_wav(raw)
            if not dung:
                _ghi_log(f"Kokoro ghi ra file không dùng được cho câu {i} "
                         f"({ma}): {vi_sao}")
                continue
            dich = Path(paths[i])
            try:
                dich.parent.mkdir(parents=True, exist_ok=True)
                if dich.exists():
                    dich.unlink()
                shutil.copyfile(raw, dich)
            except OSError as e:
                _ghi_log(f"Không chép được câu {i} về {dich}: {e}")
                continue
            # KIỂM LẠI BẢN ĐÍCH: chép trên Windows có thể ra file cụt khi hết
            # đĩa mà `copyfile` không ném (đúng bẫy "ffmpeg mã 0 file rỗng").
            dung2, vi_sao2 = _kiem_wav(dich)
            if not dung2:
                _ghi_log(f"Bản chép của câu {i} không dùng được: {vi_sao2}")
                continue
            ok_i.append(i)
            if r.get("moc"):
                moc[i] = r["moc"]

        _ghi_log(f"Kokoro đọc {len(ok_i)}/{len(items)} câu bằng {ma} · "
                 f"nạp {ket.get('nap')}s · sinh {ket.get('gen')}s")
        return {"ok_i": ok_i, "moc": moc}
    finally:
        _don(sb)
        try:
            if runner:
                Path(runner).unlink(missing_ok=True)
        except OSError:
            pass


def moc_thu(texts: list[str], paths: list[str], voice: str,
            han_giay: int = 1800) -> dict:
    """Đọc cả loạt VÀ trả kèm mốc do CHÍNH Kokoro dự đoán. **CHỈ ĐỂ ĐO.**

    ═══ VÌ SAO CÓ HÀM NÀY, VÀ VÌ SAO ĐƯỜNG SẢN XUẤT KHÔNG DÙNG NÓ ═══
    Mục "CÒN PHẢI LÀM" ở đầu file (và cả nhãn) chốt rằng *"Kokoro KHÔNG trả
    mốc từng chữ"*. **ĐỌC MÃ THÌ CÂU ĐÓ SAI**: `KPipeline.join_timestamps`
    điền `MToken.start_ts/end_ts` cho MỌI giọng tiếng Anh (`lang_code in
    'ab'`), tức toàn bộ 28 giọng của bảng này. Đây đúng họ *"đọc mã tới
    `lang="vi"` rồi kết luận là DỪNG QUÁ SỚM"* — nên hàm này tồn tại để phép
    đo có đường vào, thay vì tôi khẳng định suông theo cả hai chiều.

    **NHƯNG ĐÓ LÀ MỐC *SUY RA*, KHÔNG PHẢI MỐC ĐO** — cùng loại với Piper,
    KHÁC hẳn `WordBoundary` của edge-tts và `/with-timestamps` của ElevenLabs.
    Nó cộng dồn `pred_dur` (bộ dự đoán độ dài phát ra, chính nó cũng ước
    lượng), và ngay trong mã thư viện còn một dòng `# TODO: Is -3 an
    appropriate offset?` ở phép bù mốc đầu. Vì vậy đường sản xuất đi
    `giong_hang` (gióng hàng cưỡng bức trên CHÍNH file tiếng, cổng 73), còn
    con số của đường này phải **ĐO rồi mới được tin** — và phải đo bằng thước
    thứ ba, không bằng Groq chép ngược (cổng 67 đã chứng minh thước Groq phụ
    thuộc giọng).
    """
    n = len(texts)
    ra = {"ok": [False] * n, "moc": [[] for _ in range(n)]}
    ma = tach_ma(voice)
    if not ma or not tinh_trang()["co"]:
        return ra
    can = [i for i in range(n) if str(texts[i] or "").strip()]
    items = [{"i": i, "text": str(texts[i]).strip().replace("\n", " "),
              "raw": ""} for i in can]
    try:
        kq = _doc(items, ma, paths, "+0%", han_giay, None)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"moc_thu hỏng: {type(e).__name__}: {e}")
        return ra
    for i in kq.get("ok_i") or ():
        if 0 <= i < n:
            ra["ok"][i] = True
    for i, m in (kq.get("moc") or {}).items():
        if 0 <= int(i) < n:
            ra["moc"][int(i)] = m
    return ra
