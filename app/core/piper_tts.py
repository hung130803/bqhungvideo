# -*- coding: utf-8 -*-
"""PIPER — LỰA CHỌN GIỌNG ĐỌC THỨ HAI (không thay edge-tts).

═══════════════════════════════════════════════════════════════════════════
RANH GIỚI GIẤY PHÉP — ĐỌC TRƯỚC KHI SỬA FILE NÀY
═══════════════════════════════════════════════════════════════════════════
`piper-tts` là **GPL-3.0-or-later** (kho `OHF-Voice/piper1-gpl`; bản MIT cũ
dừng ở 1.2.0). App này là phần mềm ĐÓNG, bán cho người dùng.

  · Gọi Piper như **CHƯƠNG TRÌNH RỜI** qua `subprocess`, chỉ trao đổi
    **dòng lệnh + file WAV**  ->  app KHÔNG phải mở mã nguồn.
  · `import piper` **MỘT DÒNG THÔI LÀ MẤT QUYỀN GIỮ KÍN MÃ**.
  · Đóng `piper` vào `.exe` PyInstaller cũng vậy.

App ĐÃ chạy đúng mô hình an toàn này với `ffmpeg` (cũng GPL) nhiều năm. Làm y
hệt. Vì vậy trong CẢ FILE NÀY:
  - KHÔNG `import piper`, KHÔNG `from piper import ...`
  - KHÔNG thêm `_piper` vào `sys.path` (chèn vào là mở đường cho người sau
    lỡ import, và làm bẩn phép dò của mọi lượt sau — bài học cổng 58)
  - Dò "đã cài chưa" bằng **FILE CÓ TỒN TẠI KHÔNG**, không bằng `find_spec`
    (`find_spec` phải nạp gói cha = chạm vào mã GPL trong tiến trình app)
Cổng 64 quét tĩnh bằng `tokenize` để canh đúng mấy điều trên.

KHÔNG đóng gói vào `.exe`: app TỰ TẢI khi người dùng chọn dùng, tải THẲNG từ
kho GitHub của tác giả, lưu NGOÀI thư mục cài. Người tải là NGƯỜI DÙNG, app
chỉ chỉ đường -> nhẹ nhất về nghĩa vụ GPL. Xem `LICENSES.txt` mục 3 và 4.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO THÊM PIPER — ĐÚNG MỘT LÝ DO: MỐC TỪNG CHỮ
═══════════════════════════════════════════════════════════════════════════
Piper KHÔNG hay hơn edge-tts. Đo trên cùng đoạn chữ (docs/GIONG_DOC_MIEN_PHI):
nhấn nhá edge-tts NamMinh **3,96** · HoaiMy **3,40** · Piper vais1000
**3,24** — tức Piper ĐỀU HƠN, đi lùi ở đúng cái anh Hùng đang chê. Nó cũng
chỉ có **1 giọng Việt** dùng được (edge-tts có 2).

Cái nó hơn: chạy HẲN TRÊN MÁY (không gọi dịch vụ của ai — xem ghi chú
edge-tts ở `LICENSES.txt` mục 5), và có mốc từng chữ mà không tốn lượt mạng.

VÌ THẾ: đây là LỰA CHỌN THÊM. Mặc định vẫn là edge-tts. Thiếu Piper thì LÙI
ÊM về edge-tts, KHÔNG được nổ.

═══════════════════════════════════════════════════════════════════════════
MỐC TỪNG CHỮ: LẤY THẾ NÀO — 3 BẪY ĐÃ ĐO ĐƯỢC, ĐỪNG LÀM LẠI
═══════════════════════════════════════════════════════════════════════════
CLI của Piper **KHÔNG có cờ xuất mốc**. Mốc chỉ có trong API Python
(`PiperVoice.load(include_alignments=True)`) — mà API Python là thứ CẤM dùng
ở đây vì nó buộc `import piper`. Nên mốc phải suy ra từ ĐỘ DÀI WAV của từng
chữ: `--output-dir` ghi MỘT WAV cho MỖI DÒNG đầu vào -> mỗi từ một dòng.

Đo bằng `_do_piper/_do_moc_cach2.py` trên máy này (Python 3.12.10):

BẪY 1 — **`--output-dir-naming timestamp` LÀM MẤT FILE, và MẤT KHÔNG ĐỀU.**
  `piper/__main__.py` đặt tên file bằng `time.monotonic_ns()`. Trên Windows
  `time.monotonic` nhảy **15,625 ms** (đo được), nên hai chữ NGẮN đọc liền
  nhau nhận CÙNG một tên -> file sau **GHI ĐÈ** file trước. Đo 48 từ:
  lượt 1 ra **44 WAV**, lượt 2 ra **46**, lượt 3 ra **46** — nhấp nháy.
  Nguy hiểm thật không nằm ở chỗ thiếu file mà ở chỗ `zip(wav, tu)` sau đó
  **gán mốc cho SAI CHỮ từ chỗ mất trở đi**, rc=0, không một dòng báo.
  => KHÔNG DÙNG kiểu đặt tên này.

BẪY 2 — **tên file KHÔNG PHẢI là chữ mình gửi.** Dùng `--output-dir-naming
  text` thì Piper đặt tên bằng `pathvalidate.sanitize_filename`, và nó ĐỔI:
    `con`   -> `con_.wav`   (CON là tên THIẾT BỊ của Windows)
    `giờ.`  -> `giờ.wav`    (Windows nuốt dấu chấm cuối)
  Đoán tên rồi tra hụt là mốc lại lệch. => làm sạch dấu câu TRƯỚC khi gửi,
  rồi tra bằng bộ khớp nhiều dạng, VÀ đối soát "mọi chữ tra được + mọi file
  đều có chủ". Không khớp trọn -> **TRẢ MỐC RỖNG**, tuyệt đối không đoán.

BẪY 3 — **chữ đọc RỜI không dài bằng chữ đọc TRONG CÂU.** Tổng độ dài 46 chữ
  đọc rời = **9,427 s** trong khi đọc liền cả câu = **9,764 s** (**−3,4%**).
  Nên phải CO GIÃN mốc về đúng độ dài WAV thật của câu (`_co_gian`). Không
  co giãn thì mốc cuối hụt gần 1/3 giây so với tiếng.

Hệ quả phải chấp nhận: mốc Piper là **suy ra**, không phải mốc máy đọc trả
về như `WordBoundary` của edge-tts. Nó đúng THỨ TỰ và đúng TỔNG, còn ranh
giới từng chữ là ước lượng theo tỉ lệ. Cột số đo thật nằm ở cổng 64.

═══════════════════════════════════════════════════════════════════════════
`length_scale` BÃO HOÀ — ĐO LẠI 16/08/2026, SỐ CŨ LÀ SỐ RÁC
═══════════════════════════════════════════════════════════════════════════
Bảng `length_scale` trong `_do_piper/work/ket_qua.json` ra **TOÀN 0,000
giây**: lượt đo đó KHÔNG HỀ CHẠY ĐƯỢC (vòng lặp không kiểm `rc`) nhưng vẫn
ghi ra file kết quả trông như thật. Đo lại có kiểm `rc`, cùng câu 200 ký tự:

    length_scale | 1.0   0.9   0.8   0.74  0.7   0.6   0.5   0.45  0.3   0.2
    so tự nhiên  | .981  .977  .937  .860  .836  .767  .751  .744  .697  .692

**HAI ĐIỀU PHẢI NHỚ:**
 1. **BÃO HOÀ ở ~0,69×.** Ép dưới `length_scale` 0,5 gần như không ngắn thêm
    (0,751 -> 0,692 trong khi tham số đi từ 0,5 xuống 0,2).
 2. **`length_scale` KHÔNG TỈ LỆ THUẬN với độ dài.** Đặt 0,45 KHÔNG ra 0,45×
    mà ra **0,744×**. Ai tính `length_scale = khung / độ_dài_tự_nhiên` sẽ ép
    hụt rất xa rồi tưởng Piper hỏng. `_ls_tu_rate` vì thế dò theo BẢNG ĐO
    chứ không theo công thức.

Để so cho công bằng: edge-tts `rate=+50%` đo được 1,455× nhanh hơn, tức
**0,687×** độ dài — hai bên **xấp xỉ nhau**. Nghĩa là kiến trúc 4 bước hiện
tại của app (cắt lề im -> rút gọn chữ -> đọc nhanh -> mượn lặng -> co giãn)
dùng được nguyên xi với Piper, KHÔNG phải viết lại.

═══════════════════════════════════════════════════════════════════════════
CHI PHÍ — GỌI TIẾN TRÌNH RỜI THÌ LƯỢT NÀO CŨNG PHẢI NẠP LẠI MODEL
═══════════════════════════════════════════════════════════════════════════
Con số "25,8× nhanh hơn thời gian thật" trong tài liệu là tốc độ **SAU KHI
model đã nạp**, đo trong tiến trình. Gọi rời thì mỗi lượt phải nạp lại
(~2,2 s). Đo thật cả lượt: câu 9,7 giây tiếng ra trong **2,70 s wall =
3,62× thời gian thật**. Lấy mốc tốn thêm **1,12×** lượt đọc câu nữa.
Vì vậy: GOM CẢ LOẠT VÀO MỘT LƯỢT GỌI (`doc_loat`), đừng gọi từng câu.

DUNG LƯỢNG LÀ SỐ ĐO, KHÔNG PHẢI ƯỚC BỪA (bài học cổng 58: nhãn Demucs từng
ghi *"khoảng 2 GB"* trong khi lượng tải thật là 154 MB — **gấp 13 lần**).
Chạy thật `cai_piper()` vào hộp cát rỗng: **ok=True · 36,8 giây · 212,4 MB
trên đĩa** (bộ đọc + onnxruntime + numpy + giọng 63 MB), rồi đọc thử một câu
ra **8 mốc / 1,788 s**. Nhãn trong UI ghi đúng số đó.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import unicodedata
import wave
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Nhận dạng giọng
# ---------------------------------------------------------------------------
#: Tiền tố mã giọng Piper trong combo. Mã giọng edge-tts không bao giờ chứa
#: dấu hai chấm nên hai họ không lẫn nhau được.
TIEN_TO = "piper:"

#: Tên model. CHỈ MỘT giọng được phép có mặt.
#:   `vais1000`  trọng số MIT + dữ liệu CC BY 4.0  -> BÁN ĐƯỢC (ghi công
#:               trong `LICENSES.txt` mục 4)
#: HAI GIỌNG VIỆT CÒN LẠI BỊ CẤM ĐƯA VÀO — đã tra tận model card:
#:   `vivos`             dữ liệu CC BY-NC-SA 4.0 = CẤM THƯƠNG MẠI, và bảng âm
#:                       THIẾU DẤU THANH tiếng Việt (in "Missing phoneme from
#:                       id map: 2/4/5/6"), đọc ngọng 10,6% sai từ.
#:   `25hours_single`    model card ghi "License: Unknown". Im lặng KHÔNG
#:                       phải là cho phép. Đo ra 0 mốc + 8,5% sai từ.
#: Cổng 64 có ca quét: hai tên trên không được xuất hiện ở bất kỳ đâu trong
#: bảng giọng.
TEN_MODEL = "vi_VN-vais1000-medium"

#: Mã giọng đầy đủ dùng trong combo / trong DB.
MA_GIONG = f"{TIEN_TO}{TEN_MODEL}"

#: Nhãn hiện cho anh Hùng. Tiếng Việt, KHÔNG EMOJI, không phơi mã máy.
NHAN_GIONG = "Giọng Việt chạy trên máy (Piper)"

#: Kho tải. PHẢI là kho của CHÍNH TÁC GIẢ — tự dựng máy chủ chứa bản sao
#: Piper là app trở thành NGƯỜI PHÁT HÀNH và nghĩa vụ GPL quay lại đủ.
KHO_PIPER = "https://github.com/OHF-Voice/piper1-gpl"
BAN_PIPER = "1.7.0"
URL_WHEEL = (f"{KHO_PIPER}/releases/download/v{BAN_PIPER}/"
             f"piper_tts-{BAN_PIPER}-cp39-abi3-win_amd64.whl")
#: Giọng lấy từ kho giọng chính thức của Piper (model card + giấy phép nằm
#: cùng chỗ). Đây cũng là nơi `piper.download_voices` của chính họ tải về.
URL_GIONG = ("https://huggingface.co/rhasspy/piper-voices/resolve/main/"
             f"vi/vi_VN/vais1000/medium/{TEN_MODEL}")

_NO_WIN = 0x08000000 if os.name == "nt" else 0


def la_giong_piper(voice: str) -> bool:
    """`voice` có phải mã giọng Piper không (chịu được hậu tố `|<pitch>`)."""
    return str(voice or "").strip().lower().startswith(TIEN_TO)


# ---------------------------------------------------------------------------
# Chỗ để Piper trên đĩa
# ---------------------------------------------------------------------------
def thu_muc_piper() -> Path:
    """Thư mục chứa Piper + giọng. NGOÀI thư mục cài.

    ĐỌC `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số ở tầm module — test
    đổi `BQ_DATA_DIR` sau khi module đã nạp thì hằng số cũ trỏ sai chỗ (bài
    học `tg_so.duong_so` và `lib_demucs`).

    BẢN ĐÓNG GÓI PHẢI RA `DATA_DIR`, KHÔNG ĐƯỢC RA CẠNH `.exe`: lượt tự cập
    nhật đổi tên `_internal` -> `_internal.old` rồi `rmdir /S /Q`, tức mọi
    thứ tải về nằm trong đó bị XOÁ SẠCH — đúng lỗi đã xảy ra với `_lib` của
    Demucs (cổng 58 CA 5). Chạy từ nguồn thì để trong repo cho tiện gỡ rối.
    """
    try:
        import config
        goc = Path(getattr(config, "DATA_DIR", "") or "")
    except Exception:  # noqa: BLE001
        goc = Path("")
    if getattr(sys, "frozen", False):
        return (goc or Path.home()) / "_piper"
    # chạy từ nguồn: <repo>/_piper (đã có trong .gitignore)
    return Path(__file__).resolve().parents[2] / "_piper"


def duong_model() -> Path:
    return thu_muc_piper() / "voices" / f"{TEN_MODEL}.onnx"


def _python_chay() -> str:
    """Python dùng để CHẠY tiến trình Piper.

    Bản chạy từ nguồn: chính python đang chạy app. Bản `.exe`: `sys.executable`
    là BQHungVideo.exe (không chạy được `-m piper`) nên phải tìm Python hệ
    thống — cùng ràng buộc đã ghi cho Demucs ở cổng 55/58: máy nhân viên phải
    có Python 3 thì mới dùng được, không có thì app nói thẳng chứ không im
    lặng.
    """
    if not getattr(sys, "frozen", False):
        return sys.executable
    for ten in ("python.exe", "python3.exe", "python"):
        from shutil import which
        p = which(ten)
        if p:
            return p
    return ""


def _env() -> dict:
    """Môi trường cho tiến trình con.

    `PYTHONPATH` chỉ được đặt cho TIẾN TRÌNH CON. KHÔNG bao giờ đụng
    `sys.path` của app — đó là ranh giới giữ cho mã GPL không bao giờ nạp vào
    tiến trình app.
    """
    e = dict(os.environ)
    e["PYTHONPATH"] = str(thu_muc_piper())
    e["PYTHONIOENCODING"] = "utf-8"
    return e


# ---------------------------------------------------------------------------
# Dò đã cài chưa — bằng FILE, không bằng import
# ---------------------------------------------------------------------------
#: Những thứ bắt buộc phải có mặt. Dò bằng đường dẫn nên bản `.exe` (không có
#: `.venv` để mượn) thấy ĐÚNG cái mà máy dev thấy — đây chính là lỗi cổng 58
#: đã lôi ra với Demucs: dò bằng "import được không" thì máy dev mượn thư viện
#: của `.venv` rồi báo "đã cài" trong khi `_lib` thiếu.
_CAN_CO = ("piper/__main__.py", "piper/voice.py", "onnxruntime", "numpy")


def tinh_trang_piper() -> dict:
    """Trả {co, thieu, co_model, thu_muc, model, python}.

    `co` = chạy được không · `thieu` = phần còn thiếu (để đặt nhãn nút).
    """
    d = thu_muc_piper()
    thieu = [t for t in _CAN_CO if not (d / t).exists()]
    co_model = duong_model().exists()
    py = _python_chay()
    if not py:
        thieu.append("python3 (máy chưa cài Python)")
    return {
        "co": (not thieu) and co_model,
        "thieu": thieu,
        "co_model": co_model,
        "thu_muc": str(d),
        "model": str(duong_model()),
        "python": py,
    }


def co_piper() -> bool:
    """Có chạy được Piper không. KHÔNG BAO GIỜ NÉM."""
    try:
        return bool(tinh_trang_piper()["co"])
    except Exception:  # noqa: BLE001
        return False


def cai_piper(bao: Optional[Callable[[str], None]] = None,
              han_giay: int = 1800) -> dict:
    """Tải Piper + giọng về `thu_muc_piper()`. CHỈ chạy khi NGƯỜI DÙNG BẤM.

    Wheel lấy THẲNG từ kho GitHub của tác giả (`URL_WHEEL`); phần phụ thuộc
    (onnxruntime, numpy) lấy từ PyPI như mọi gói Python khác.

    `--target` + `--ignore-installed`: thiếu cờ sau thì pip có thể BỎ QUA gói
    máy đã có -> thư mục đích thiếu gói -> máy dev vẫn chạy (mượn của
    `.venv`) còn máy anh Hùng thì không. Đó đúng là lỗi `_lib` của Demucs
    (cổng 58) — đừng lặp lại.
    """
    def _noi(s: str) -> None:
        if bao:
            try:
                bao(s)
            except Exception:  # noqa: BLE001
                pass

    d = thu_muc_piper()
    d.mkdir(parents=True, exist_ok=True)
    py = _python_chay()
    if not py:
        return {"ok": False, "loi": "Máy chưa cài Python 3 nên không tải "
                                    "được bộ đọc Piper."}
    _noi("Đang tải bộ đọc Piper (khoảng 60 MB)...")
    cmd = [py, "-m", "pip", "install", "--no-input", "--disable-pip-version-check",
           "--target", str(d), "--ignore-installed", URL_WHEEL]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_NO_WIN, timeout=han_giay)
    except subprocess.TimeoutExpired:
        return {"ok": False, "loi": "Tải bộ đọc Piper quá lâu, đã dừng."}
    if r.returncode != 0:
        return {"ok": False, "loi": (r.stderr or r.stdout or "")[-600:]}

    # giọng: 2 file (.onnx + .onnx.json), tải thẳng, không qua pip
    _noi("Đang tải giọng tiếng Việt (khoảng 63 MB)...")
    voi = d / "voices"
    voi.mkdir(parents=True, exist_ok=True)
    import urllib.request
    for duoi in (".onnx", ".onnx.json"):
        dich = voi / f"{TEN_MODEL}{duoi}"
        if dich.exists() and dich.stat().st_size > 1000:
            continue
        tam = dich.with_suffix(dich.suffix + ".tai")
        try:
            with urllib.request.urlopen(URL_GIONG + duoi + "?download=true",
                                        timeout=600) as r2, \
                    open(tam, "wb") as f:
                while True:
                    khoi = r2.read(1 << 20)
                    if not khoi:
                        break
                    f.write(khoi)
            tam.replace(dich)
        except Exception as e:  # noqa: BLE001
            try:
                tam.unlink()
            except OSError:
                pass
            return {"ok": False, "loi": f"Tải giọng hỏng: {e}"}

    # HẬU KIỂM bằng chính phép dò của bản `.exe` — không tin lời pip báo
    tt = tinh_trang_piper()
    return {"ok": bool(tt["co"]), "loi": "" if tt["co"] else
            f"Cài xong nhưng vẫn thiếu: {tt['thieu']}", "tinh_trang": tt}


# ---------------------------------------------------------------------------
# Gọi Piper
# ---------------------------------------------------------------------------
def _chay(args: list[str], vao: str, han: int) -> tuple[int, str]:
    """Chạy Piper như CHƯƠNG TRÌNH RỜI. Mọi `subprocess` đều có `timeout`."""
    py = _python_chay()
    if not py:
        return 1, "không có Python để chạy Piper"
    cmd = [py, "-m", "piper", "-m", str(duong_model()), *args]
    try:
        r = subprocess.run(cmd, input=vao.encode("utf-8"),
                           capture_output=True, env=_env(),
                           creationflags=_NO_WIN, timeout=han)
    except subprocess.TimeoutExpired:
        return 1, f"Piper chạy quá {han}s"
    except OSError as e:
        return 1, str(e)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")[-400:]


def dai_wav(p: str | Path) -> float:
    """Độ dài WAV (giây). 0.0 nếu không đọc được.

    KHÔNG dùng cỡ file: header WAV vẫn ghi ra được khi thân rỗng, đúng họ bẫy
    "ffmpeg trả mã 0 mà file 0 KiB".
    """
    try:
        with wave.open(str(p), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:  # noqa: BLE001
        return 0.0


#: Dấu câu phải BỎ trước khi lấy mốc. Lý do KHÔNG phải thẩm mỹ: `giờ.` ra file
#: `giờ.wav` (Windows nuốt dấu chấm cuối) nên tra theo tên sẽ hụt.
_DAU_CAU = " \t\r\n.,!?;:\"'()[]{}…–—-«»“”‘’"


def _lam_sach(tu: str) -> str:
    """Chữ đem đi lấy mốc: bỏ dấu câu hai đầu, bỏ ký tự CẤM của tên file."""
    s = unicodedata.normalize("NFC", str(tu or "")).strip(_DAU_CAU)
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", s)
    return s.strip(_DAU_CAU)


def _tra_file(thu_muc: Path, chu: str) -> Optional[Path]:
    """Tìm WAV của `chu`. KHÔNG ĐOÁN MỘT DẠNG TÊN DUY NHẤT.

    `pathvalidate` của Piper đổi tên theo luật riêng — đo được `con` ->
    `con_.wav` (CON là tên thiết bị Windows). Tra theo nhiều dạng, so KHÔNG
    phân biệt hoa/thường (Windows vốn không phân biệt).
    """
    co = {p.name.lower(): p for p in thu_muc.glob("*.wav")}
    for ten in (f"{chu}.wav", f"{chu}_.wav"):
        p = co.get(ten.lower())
        if p is not None:
            return p
    return None


def _co_gian(moc: list[list], dai_that: float) -> list[list]:
    """Co giãn mốc về ĐÚNG độ dài WAV thật của câu.

    Chữ đọc RỜI ngắn hơn chữ đọc TRONG CÂU — đo được **−3,4%** trên câu 48 từ
    (9,427 s so với 9,764 s). Không co giãn thì mốc cuối hụt gần 1/3 giây,
    tức chữ chạy nhanh hơn tiếng suốt cả câu.
    """
    if not moc or dai_that <= 0:
        return moc
    tong = moc[-1][1]
    if tong <= 0:
        return moc
    he = dai_that / tong
    return [[round(a * he, 3), round(b * he, 3), w] for a, b, w in moc]


#: Bảng ĐO THẬT (xem đầu file). Tra bảng, KHÔNG dùng công thức: `length_scale`
#: không tỉ lệ thuận với độ dài, đặt 0,45 ra 0,744× chứ không phải 0,45×.
_BANG_LS = ((1.00, 0.981), (0.90, 0.977), (0.80, 0.937), (0.74, 0.860),
            (0.70, 0.836), (0.60, 0.767), (0.50, 0.751), (0.45, 0.744),
            (0.30, 0.697), (0.20, 0.692))

#: Nén sâu nhất Piper làm được (đo). Xin ngắn hơn mức này là xin điều không
#: tồn tại — `khop_thoi_gian` phải lo phần còn lại như với edge-tts.
NEN_SAU_NHAT = 0.692


def _ls_tu_rate(rate: str) -> Optional[float]:
    """Đổi `rate` kiểu edge-tts ('+20%') sang `length_scale` của Piper.

    Trả None khi không cần đổi (rate ~ 0) để lệnh gọi giống hệt đường thường.
    """
    try:
        r = float(str(rate or "+0%").strip().rstrip("%")) / 100.0
    except ValueError:
        return None
    if abs(r) < 0.005:
        return None
    dich = 1.0 / (1.0 + r)                     # tỉ lệ độ dài MONG MUỐN
    dich = max(NEN_SAU_NHAT, min(1.35, dich))
    # lấy `length_scale` có tỉ lệ đo được GẦN đích nhất
    return min(_BANG_LS, key=lambda x: abs(x[1] - dich))[0]


def doc_loat(texts: list[str], paths: list[str],
             on_done: Optional[Callable[[int], None]] = None,
             rate: str | list = "+0%",
             lay_moc: bool = True,
             han_giay: int = 900,
             ) -> tuple[list[bool], list[list]]:
    """Đọc cả LOẠT câu bằng Piper. Cùng hợp đồng với `_synth_all_words`.

    Trả `(ok, words)`: `ok[i]` = câu i đọc được chưa · `words[i]` =
    `[[đầu, cuối, từ], ...]` theo thời gian THẬT của giọng, rỗng nếu không
    lấy được mốc chắc chắn.

    GOM CẢ LOẠT VÀO MỘT LƯỢT GỌI cho mỗi nhóm tốc độ — gọi từng câu là mỗi
    câu phải nạp lại model ~2,2 giây.

    KHÔNG BAO GIỜ NÉM: hỏng thì trả `ok` toàn False để nơi gọi lùi về
    edge-tts.
    """
    n = len(texts)
    ok = [False] * n
    words: list[list] = [[] for _ in range(n)]
    if n == 0:
        return ok, words

    try:
        # nhóm theo tốc độ: mỗi `length_scale` là một lượt gọi Piper
        nhom: dict[Optional[float], list[int]] = {}
        for i in range(n):
            r_i = rate[i] if isinstance(rate, list) and i < len(rate) else (
                rate if isinstance(rate, str) else "+0%")
            nhom.setdefault(_ls_tu_rate(r_i), []).append(i)

        for ls, chi_so in nhom.items():
            chi_so = [i for i in chi_so if (texts[i] or "").strip()]
            if not chi_so:
                continue
            _doc_nhom(texts, paths, chi_so, ls, ok, words, lay_moc, han_giay)
    except Exception:  # noqa: BLE001
        return [False] * n, [[] for _ in range(n)]
    # Báo XONG cho MỌI câu, kể cả câu rỗng/hỏng: nơi gọi đếm số lần `on_done`
    # để chạy thanh tiến trình, thiếu một nhịp là thanh đứng mãi không đủ.
    for i in range(n):
        if on_done:
            try:
                on_done(i)
            except Exception:  # noqa: BLE001
                pass
    return ok, words


def _doc_nhom(texts: list[str], paths: list[str], chi_so: list[int],
              ls: Optional[float], ok: list[bool], words: list[list],
              lay_moc: bool, han_giay: int) -> None:
    """Đọc một nhóm câu CÙNG tốc độ trong MỘT lượt gọi Piper."""
    thu_muc = Path(paths[chi_so[0]]).parent
    tam = thu_muc / f"_piper_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    cau_dir = tam / "cau"
    cau_dir.mkdir(parents=True, exist_ok=True)
    them = ["--length-scale", str(ls)] if ls else []

    # ---- 1. đọc CÂU: mỗi câu một WAV ----
    # Câu dài hàng trăm ms nên va chạm tên theo thời gian gần như không xảy
    # ra, NHƯNG vẫn phải ĐẾM LẠI: đúng bao nhiêu file mới dám ghép theo thứ
    # tự. Thiếu một file là mọi câu từ đó trở đi lệch sang tiếng của câu khác.
    rc, err = _chay(["-d", str(cau_dir), "--output-dir-naming", "timestamp",
                     *them],
                    vao="\n".join(texts[i].strip().replace("\n", " ")
                                  for i in chi_so),
                    han=han_giay)
    ra = sorted(cau_dir.glob("*.wav"), key=lambda p: int(p.stem)
                if p.stem.isdigit() else 0)
    if rc != 0 or len(ra) != len(chi_so):
        _ghi_log(f"Piper đọc câu hỏng: rc={rc} · ra {len(ra)}/{len(chi_so)} "
                 f"WAV · {err}")
        _don(tam)
        return

    for vt, i in enumerate(chi_so):
        d = dai_wav(ra[vt])
        if d <= 0:                      # WAV rỗng: header vẫn ghi được
            continue
        try:
            dich = Path(paths[i])
            dich.parent.mkdir(parents=True, exist_ok=True)
            if dich.exists():
                dich.unlink()
            ra[vt].replace(dich)
            ok[i] = True
        except OSError:
            continue

    # ---- 2. mốc từng chữ ----
    if lay_moc:
        try:
            _lay_moc(texts, paths, chi_so, ls, ok, words, tam, han_giay)
        except Exception as e:  # noqa: BLE001
            _ghi_log(f"Piper lấy mốc hỏng (tiếng vẫn dùng được): {e}")
    _don(tam)


def _lay_moc(texts: list[str], paths: list[str], chi_so: list[int],
             ls: Optional[float], ok: list[bool], words: list[list],
             tam: Path, han_giay: int) -> None:
    """Lấy mốc từng chữ cho các câu trong nhóm — MỘT lượt gọi Piper cho cả nhóm.

    Gửi mỗi chữ KHÁC NHAU đúng một lần (khử trùng KHÔNG phân biệt hoa/thường
    vì Windows không phân biệt), rồi ĐỐI SOÁT hai chiều: mọi chữ phải tra ra
    file, và mọi file phải có chủ. Lệch một cái là **BỎ MỐC CẢ NHÓM** —
    mốc gán nhầm chữ tệ hơn hẳn không có mốc.
    """
    tu_theo_cau: dict[int, list[str]] = {}
    rieng: list[str] = []
    da = set()
    for i in chi_so:
        if not ok[i]:
            continue
        sach = [_lam_sach(t) for t in (texts[i] or "").split()]
        sach = [t for t in sach if t]
        tu_theo_cau[i] = sach
        for t in sach:
            k = t.lower()
            if k not in da:
                da.add(k)
                rieng.append(k)
    if not rieng:
        return

    d_tu = tam / "tu"
    d_tu.mkdir(parents=True, exist_ok=True)
    them = ["--length-scale", str(ls)] if ls else []
    rc, err = _chay(["-d", str(d_tu), "--output-dir-naming", "text", *them],
                    vao="\n".join(rieng), han=han_giay)
    if rc != 0:
        _ghi_log(f"Piper đọc chữ rời hỏng: rc={rc} · {err}")
        return

    bang: dict[str, float] = {}
    dung = set()
    for t in rieng:
        p = _tra_file(d_tu, t)
        if p is None:
            _ghi_log(f"Piper: không tra ra WAV của chữ {t!r} -> BỎ MỐC cả "
                     f"nhóm (thà không có mốc còn hơn mốc gán nhầm chữ)")
            return
        bang[t] = dai_wav(p)
        dung.add(p.name.lower())
    thua = [p.name for p in d_tu.glob("*.wav") if p.name.lower() not in dung]
    if thua:
        _ghi_log(f"Piper: còn {len(thua)} WAV không chữ nào nhận ({thua[:3]}) "
                 f"-> BỎ MỐC cả nhóm")
        return

    for i, ds in tu_theo_cau.items():
        tho = [bang.get(t.lower(), 0.0) for t in ds]
        if not tho or sum(tho) <= 0:
            continue
        moc, t0 = [], 0.0
        for chu, d in zip(ds, tho):
            moc.append([t0, t0 + d, chu])
            t0 += d
        words[i] = _co_gian(moc, dai_wav(paths[i]))


def _don(d: Path) -> None:
    """Dọn thư mục tạm. KHÔNG BAO GIỜ NÉM (bài học rò `_seg_*`)."""
    try:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def _ghi_log(s: str) -> None:
    """Ghi lý do vào `logs/piper_<ngày>.log`.

    Mọi đường lùi ÊM đều phải để lại dấu vết — lùi êm mà im lặng thì đúng
    bằng hỏng âm thầm.
    """
    try:
        import config
        d = Path(getattr(config, "DATA_DIR", ".")) / "logs"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"piper_{time.strftime('%Y%m%d')}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {s}\n")
    except Exception:  # noqa: BLE001
        pass
