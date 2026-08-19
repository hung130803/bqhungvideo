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

**ĐỌC SAI CHỮ (Groq chép ngược, 192 từ):** tiếng Anh **4,2-4,7%**.

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
        ·  **Chatterbox 76,2 ms = 1,75x edge-tts**
      -> Chatterbox nằm **DƯỚI cả Piper**, mà Piper đã phải ghi cảnh báo
         trong app vì mốc lệch. Và mốc đó còn phải **moi cửa sau** ra khỏi
         thuộc tính riêng tư ``t3.patched_model.alignment_stream_analyzer``
         — API công khai **không trả một mốc nào** (``generate()`` trả đúng
         một khối sóng âm). Bản sau đổi là **gãy im lặng**.

    ĐỌC SAI CHỮ / BỊA CHỮ (Groq chép ngược):
        Anh 4,0% (0,99x số chữ)  ·  Nhật 15,9% (**1,32x**)
        ·  Trung 28,8% (**1,66x**)
      -> tiếng Trung nó **đọc thêm cả một câu không hề có trong bản gửi
         vào**. Với người BÁN video thì đó là hỏng hàng, không phải lỗi nhỏ.

    TIẾNG VIỆT: **KHÔNG CÓ.** 23 thứ tiếng, không có ``vi``
        (``SUPPORTED_LANGUAGES`` đọc thẳng từ gói đã cài, không đọc quảng cáo).

    TỐC ĐỘ: GPU RTX 3060 **1,53x** thời gian thật · **CPU 0,25x**
        (1 phút tiếng tốn 4 phút máy). edge-tts 5,55x và **không tốn GPU**.
      -> **MÁY NHÂN VIÊN KHÔNG CÓ GPU thì bộ này không dùng được.**

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

#: Cảnh báo CHẤT LƯỢNG — cùng luật Piper/OmniVoice: tệ hơn edge-tts thì phải
#: ghi ra ngay trên DÒNG, đừng để người dùng tự phát hiện sau 300 video.
CANH_BAO_CL = ("mốc chữ phải MOI CỬA SAU của thư viện nên rung 76 ms so với "
               "44 ms của giọng thường (chữ bám lời kém hơn); KHÔNG có tiếng "
               "Việt; đọc sai chữ tiếng Trung 28,8% và có bịa thêm câu; mọi "
               "file đều bị ĐÓNG DẤU CHÌM không tắt được")

#: Cảnh báo MÁY — số đo, không phải lời doạ.
CANH_BAO_MAY = ("cần GPU NVIDIA: RTX 3060 đọc nhanh 1,53 lần thời gian thật, "
                "còn CPU chỉ 0,25 lần (1 phút tiếng tốn 4 phút máy)")

#: Trọng số tải từ Hugging Face lúc chạy lần đầu.
REPO_CB = "ResembleAI/chatterbox"

#: Nhãn nút tải. **PHẢI KHỚP ĐƯỜNG SẼ ĐI** (cổng 71 CA 4): con số này là
#: lượng tải THẬT của môi trường Python (torch CUDA ~2,5 GB + thư viện) cộng
#: trọng số ~3,0 GB. Ghi 155 MB rồi tải 2,5 GB là lặp đúng lỗi cũ.
NHAN_TAI = "Tải bộ nhân bản giọng Chatterbox (khoảng 5,5 GB, cần GPU NVIDIA)"


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
    """Nhãn đầy đủ cho hộp chọn giọng. TIẾNG VIỆT, KHÔNG EMOJI.

    Nhãn PHẢI mang cả ba cảnh báo (giấy phép · chất lượng · máy). Đây không
    phải chỗ bán hàng: anh Hùng chạy 200-300 kênh, chọn nhầm một lần là hàng
    trăm video.
    """
    lang, duong = tach_ma(ma)
    ten = (ten_hien or "").strip() or (Path(duong).stem if duong else ma)
    tieng = TIENG.get(lang, "?")
    return (f"{ten} (nhân bản, Chatterbox, tiếng {tieng}) - {GIAY_PHEP}; "
            f"{CANH_BAO_CL}; {CANH_BAO_MAY}")


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
    # DONG SEED: khong dong thi cung cau cung tham so lech do dai 33,7% giua
    # cac luot (do that, 8 luot). Dong seed -> 0,0%. Day khong phai lam dep
    # so: `khop_thoi_gian` o tien trinh cha can do dai TIEN DINH thi vong ep
    # khung moi hoi tu.
    seed = int(J.get("seed", 1234))
    ra = []
    t1 = time.time()
    for i, it in enumerate(items):
        torch.manual_seed(seed)
        kw = {}
        if ref:
            kw["audio_prompt_path"] = ref
        wav = m.generate(it["text"], language_id=lang, **kw)
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
        for r in ket.get("ra", []):
            i = int(r.get("i", -1))
            if not (0 <= i < n):
                continue
            raw = Path(r.get("p") or "")
            if not (raw.exists() and raw.stat().st_size > 1000):
                continue
            # Ép vừa khung bằng `rubberband` — KHÔNG dùng núm của model
            # (Chatterbox không có núm nào), và `_ep_khung` tự lùi `atempo`
            # khi ffmpeg máy đó thiếu rubberband.
            xau[i] = bool(_gn._ep_khung(raw, Path(paths[i]), tempo))
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
