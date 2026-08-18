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
CANH_BAO_CL_OV = ("đọc sai chữ tiếng Việt 16,9% so với edge-tts 6,8%; "
                  "mốc chữ phải dò lại bằng Groq nên kém khớp hơn edge-tts")

#: Kho giọng THIẾT KẾ BẰNG CHỮ (voice design). OmniVoice không có giọng đặt
#: tên sẵn: gõ một câu tả là ra giọng, nên số giọng coi như không giới hạn.
#: Chỉ đưa vào combo vài giọng ĐÃ CHẠY THẬT ở lượt 7 — thêm giọng bịa là
#: thêm chỗ hỏng mà không ai đo.
#:   (mã, câu tả gửi cho model, nhãn tiếng Việt)
GIONG_OV: tuple[tuple[str, str, str], ...] = (
    ("ov:nu_tre",   "female, young adult, moderate pitch",
     "Nữ trẻ"),
    ("ov:nam_tre",  "male, young adult, moderate pitch",
     "Nam trẻ"),
    ("ov:nam_tram", "male, middle-aged, low pitch",
     "Nam trung niên trầm"),
    ("ov:nu_am",    "female, middle-aged, warm low pitch",
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
    """
    for m, _tt, ten in GIONG_OV:
        if m == ma:
            return (f"{ten} (OmniVoice, 4 thứ tiếng) - {CANH_BAO_GP_OV}; "
                    f"{CANH_BAO_CL_OV}")
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
#:   3. môi trường đã dựng sẵn trên MÁY DEV NÀY ở `%TEMP%` (lượt 7 dựng ra,
#:      xem `docs/GIONG_LUOT_7.md`). Ghi ra đây thay vì giấu, vì `%TEMP%` là
#:      chỗ TẠM: `tempsweep` hoặc một lượt dọn đĩa là mất, và lúc đó
#:      `co_omnivoice()` phải trả False cho ĐÚNG chứ không được đoán bừa.
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
    }


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
                return {"ok": False, "loi": "quá giờ (bỏ cuộc)"}
        ma = p.wait(timeout=120)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "loi": f"{type(e).__name__}: {e}"}
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
            capture_output=True, text=True, timeout=300,
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
    """Dọn thư mục tạm. KHÔNG BAO GIỜ NÉM (bài học rò `_seg_*`, cổng 42)."""
    try:
        if d and str(d) and d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
