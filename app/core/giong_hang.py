# -*- coding: utf-8 -*-
"""GIÓNG HÀNG CƯỠNG BỨC (forced alignment) — lấy MỐC TỪNG CHỮ cho MỌI máy đọc.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ FILE NÀY — CÂU HỎI CŨ ĐẶT SAI
═══════════════════════════════════════════════════════════════════════════
Đường thay tiếng dựng chữ chạy theo mốc TỪNG CHỮ (cổng 60). Trước file này,
app chỉ có HAI cách lấy mốc, và cả hai đều buộc phải hỏi *"máy đọc có tự trả
mốc không"*:

  · edge-tts  -> `WordBoundary`, mốc THẬT do dịch vụ trả
  · ElevenLabs -> `/with-timestamps`, cũng mốc thật
  · Piper / mọi bộ khác -> **KHÔNG có mốc** -> app cho **Groq CHÉP NGƯỢC**
    chính file tiếng vừa đọc rồi đoán xem nó nói gì.

Ràng buộc "phải có mốc thật" đã loại gần 30 bộ giọng khỏi danh sách dùng
được. **Nhưng nó là ràng buộc TỰ ĐẶT RA, không phải ràng buộc của bài toán.**
Gióng hàng cưỡng bức nhận vào (TIẾNG + CHỮ ĐÃ BIẾT) rồi đi tìm mỗi chữ nằm ở
giây nào. So với chép ngược:

  · **chép ngược** phải ĐOÁN xem người ta nói gì (bài toán mở, 1 trong vô số
    câu) — và Groq whisper là một MÔ HÌNH NGÔN NGỮ nên nó còn **CHỮA HỘ** máy
    đọc: nghe "nét phờ lích" nó vẫn viết ra `Netflix`. Mốc nó trả về là mốc
    của câu NÓ NGHĨ ra, không phải câu mình gửi đi.
  · **gióng hàng** ĐÃ BIẾT chữ, chỉ còn đi tìm chỗ (bài toán ràng buộc chặt).

Hệ quả: chất lượng giọng thành tiêu chí DUY NHẤT khi chọn máy đọc.

═══════════════════════════════════════════════════════════════════════════
BA BẤT BIẾN — ĐỪNG "DỌN GỌN" MẤT
═══════════════════════════════════════════════════════════════════════════
(1) **TIẾN TRÌNH RIÊNG, BẮT BUỘC.** Trong tiến trình đã nạp PyQt6 +
    `QApplication` thì `import torch` chết với `OSError [WinError 1114] ...
    torch\\lib\\c10.dll`, và **`try/except` KHÔNG chặn được** (nó là access
    violation ở tầng nạp DLL). Tái hiện 100%: torch TRƯỚC Qt -> OK · torch SAU
    Qt -> 1114. App này LÀ app Qt. Đây đúng bài học `_tach_demucs` (cổng 55) —
    ở đó lỗi còn đội lốt *"máy chưa cài Demucs"* và dẫn người ta đi cài lại
    2 GB lần nữa. Vì vậy **KHÔNG file nào trong `app/` được `import torch`**;
    mã torch nằm trong `_MA_GIONG` dạng CHUỖI, chỉ tiến trình con mới chạy.
(2) **DÒ BẰNG FILE CÓ TỒN TẠI KHÔNG, KHÔNG `find_spec`/`import`.**
    `find_spec("torchaudio.pipelines")` phải NẠP gói cha = chạm torch trong
    tiến trình app = đúng cái (1) cấm. Và `find_spec` luôn tìm trên `sys.path`
    nên không trả lời được câu *"có nằm trong thư mục CỦA MÌNH không"* — đúng
    lỗ hổng cổng 58: máy dev mượn `.venv` rồi báo "đã cài", bản `.exe` cùng
    thư mục đó lại báo "chưa có".
(3) **THIẾU ĐỒ THÌ LÙI ÊM, KHÔNG NỔ.** `giong_hang_loat` trả list RỖNG; nơi
    gọi tự quay về đường cũ (Groq chép ngược). Khác ca Demucs (cổng 55 "thiếu
    là CHẶN"): ở đó lùi ra video HỎNG (giọng cũ chồng giọng mới), ở đây lùi ra
    video ĐÚNG, chỉ kém chính xác mốc — nên lùi là lựa chọn đúng. Nhưng phải
    GHI LẠI lý do: lùi êm mà im lặng thì đúng bằng hỏng âm thầm.

═══════════════════════════════════════════════════════════════════════════
MODEL: MMS_FA (torchaudio) — ĐA NGÔN NGỮ 1.130 THỨ TIẾNG
═══════════════════════════════════════════════════════════════════════════
`torchaudio.pipelines.MMS_FA` là wav2vec2 CTC do Meta huấn luyện RIÊNG cho
việc gióng hàng. Bảng token của nó chỉ có **a-z + dấu nháy** (29 token) nên
**mọi thứ tiếng đều phải ROMANIZE trước** — kể cả tiếng Việt (bỏ dấu), chứ
không riêng Trung/Nhật. Đó là thiết kế của model, không phải chỗ có thể bỏ.

**ROMANIZE TỪNG TỪ MỘT, KHÔNG ROMANIZE CẢ CÂU** — đây là chỗ dễ hỏng nhất:
`uroman("你好世界")` ra `nihaoshijie` **DÍNH LIỀN, mất sạch ranh giới từ**, mà
ranh giới từ chính là thứ ta cần. Romanize từng token rồi ghép mới giữ được
"token thứ k gồm mấy ký tự", tức mới chia mốc về đúng từ được.

Ranh giới TỪ lấy bằng `dubbing._tach_tu` (CJK-aware) — cùng cửa mà phụ đề
dùng, nên mốc trả về khớp đúng đơn vị chữ sẽ hiện lên màn hình. Dùng
`.split()` ở đây là câu Trung/Nhật ra **1 token** (bài học cổng 52/54).

**GIẢI MÃ TIẾNG BẰNG ffmpeg, KHÔNG `torchaudio.load`:** torchaudio >= 2.9 đẩy
việc đọc file sang `torchcodec` (gói RIÊNG, chưa cài) nên `torchaudio.load`
ném `ImportError`. ffmpeg thì repo này đã có sẵn và đã dùng ở mọi đường khác.
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

#: Mốc chữ đầu tra ra ngoài file thì bỏ — mốc âm là dấu hiệu tính sai tỉ lệ
#: khung, không phải chuyện "chữ nói trước khi file bắt đầu".
_NGUONG_AM = -0.001

#: Rác `_viec/` cũ hơn ngần này thì dọn — cùng luật `tempsweep`: file mới hơn
#: có thể là của lượt ĐANG chạy (app thoát bằng `os._exit`, `finally` không
#: chạy) nên tuyệt đối không đụng.
_RAC_QUA_GIAY = 2 * 3600

_DEM_LOT = itertools.count()
_KHOA_LOT = threading.Lock()


def _ma_lot() -> str:
    """Mã DUY NHẤT cho MỘT lượt gọi — `p<pid>t<thread>n<đếm>`.

    **ĐÂY LÀ CHỖ ĐÃ HỎNG, đừng rút gọn về `os.getpid()`.** Tên file việc/kết
    quả trước đây là `viec_<pid>.json` / `ket_<pid>.json`, mà `pid` là của
    tiến trình GỌI — giống hệt nhau cho MỌI luồng trong app. Hai video thay
    giọng chạy song song (làn `LAN_TG` mặc định 2 luồng) là hai luồng cùng
    một tiến trình, nên chúng:
      · ghi ĐÈ file việc của nhau -> tiến trình con gióng mẻ tiếng của luồng
        KIA rồi trả về đủ số mục, **mốc gán sai chữ mà không một dòng báo**;
      · ghi ĐÈ file kết quả của nhau;
      · và `finally` của luồng xong trước **XOÁ** file kết quả của luồng kia
        -> luồng kia đọc hụt -> *"tiến trình gióng hàng không ghi kết quả
        (mã 0)"* -> trả rỗng -> **mất sạch mốc của cả mẻ**.
    Đo thật (`_do_gh_luong.py`, 2 mẻ 6 câu): chạy lần lượt ra **12/12 câu có
    mốc**, chạy 2 luồng ra **6/12** — đúng một mẻ mất trắng, cả 2/2 lượt.
    Giữ `pid` ở ĐẦU mã để lượt dọn rác còn phân biệt được "của tiến trình
    đang sống" với "của lần chạy trước đã chết".
    """
    with _KHOA_LOT:
        return f"p{os.getpid()}t{threading.get_ident()}n{next(_DEM_LOT)}"


def _don_rac_viec(tmp: Path) -> None:
    """Dọn file việc/kết quả MỒ CÔI của lần chạy trước.

    Tên file nay là DUY NHẤT mỗi lượt nên `finally` không còn dọn hộ lượt
    khác được nữa — app bị giết giữa chừng (`os._exit`) là để lại rác vĩnh
    viễn. Chỉ đụng đúng mẫu tên app đặt và chỉ khi đã quá `_RAC_QUA_GIAY`;
    file của user, tên gần giống, file mới -> KHÔNG ĐỘNG. Không bao giờ ném.
    """
    try:
        gio = time.time()
        for p in (list(tmp.glob("viec_*.json")) + list(tmp.glob("ket_*.json"))
                  + list(tmp.glob("_bq_giong_runner_*.py"))):
            try:
                if gio - p.stat().st_mtime > _RAC_QUA_GIAY:
                    p.unlink()
            except OSError:
                pass
    except Exception:                                # noqa: BLE001
        pass


# ==========================================================================
# CHỖ CẤT ĐỒ
# ==========================================================================
def lib_torch() -> str:
    """Thư mục CHỨA TORCH — **DÙNG CHUNG `_lib` CỦA DEMUCS, CHỈ ĐỌC**.

    Dùng chung là quyết định theo SỐ, không phải cho gọn: `_lib` đã có sẵn
    **torch 4,3 GB** (bản CUDA, tải về cho Demucs ở cổng 71) và gióng hàng cần
    ĐÚNG torch đó. Dựng thư mục riêng cho torch là bắt anh Hùng tải lại 4,3 GB
    cho thứ máy đã có.

    **FILE NÀY KHÔNG BAO GIỜ GHI VÀO ĐÂY.** Một lượt `pip install --target
    _lib` có thể thay numpy/torch mà Demucs đang chạy sản xuất phụ thuộc —
    phần RIÊNG của gióng hàng vì thế nằm ở `thu_muc_gh()`.
    """
    from app.core.thay_giong import lib_demucs
    return lib_demucs()


def thu_muc_gh() -> str:
    """Thư mục RIÊNG của gióng hàng: `torchaudio` + `uroman` + model MMS_FA.

    Tách khỏi `_lib` vì hai lý do, cả hai đều đã thành sự thật một lần:
      · `_lib` là đồ của Demucs đang chạy sản xuất — thêm gói vào đó là rủi ro
        thay nhầm gói dùng chung (numpy/torch).
      · gỡ gióng hàng ra chỉ cần xoá MỘT thư mục, không đụng Demucs.

    **BẢN `.exe` PHẢI ĐẶT NGOÀI `_internal`** (bài học cổng 58 CA 5):
    `self_update.py` cập nhật bằng `ren _internal -> _internal.old` rồi
    `rmdir /S /Q _internal.old`, tức mỗi lượt tự cập nhật là xoá sạch và người
    dùng phải tải lại 1,18 GB. Đọc `config.DATA_DIR` MỖI LẦN GỌI, không cất
    hằng số (bài học `tg_so.duong_so`).
    """
    p = (os.environ.get("BQ_GIONG_HANG_LIB") or "").strip()
    if p:
        return p
    if getattr(sys, "frozen", False):
        import config
        return str(Path(config.DATA_DIR) / "_giong_hang")
    return str(Path(__file__).resolve().parents[2] / "_giong_hang")


def duong_model() -> Path:
    """File model MMS_FA (~1,18 GB). torch tải về `<TORCH_HOME>/hub/checkpoints`."""
    return Path(thu_muc_gh()) / "_models" / "hub" / "checkpoints" / "model.pt"


# ==========================================================================
# DÒ — KHÔNG IMPORT TORCH, KHÔNG `find_spec`
# ==========================================================================
def _co_goi(thu_muc: str, ten: str) -> bool:
    """Gói `ten` có nằm THẬT trong `thu_muc` không.

    Hỏi bằng ĐƯỜNG DẪN chứ không `find_spec`: `find_spec` phải nạp gói cha
    (= chạm torch trong tiến trình Qt, xem bất biến 1) và nó luôn tìm trên
    `sys.path` nên máy dev sẽ mượn `.venv` rồi báo "đã cài" trong khi bản
    `.exe` cùng thư mục ấy báo "chưa có" — đúng lỗ hổng cổng 58.
    """
    d = Path(thu_muc)
    return (d / ten).is_dir() or (d / f"{ten}.py").is_file()


def tinh_trang_giong_hang() -> dict:
    """Máy có đủ đồ gióng hàng chưa — và THIẾU ĐÍCH DANH cái gì.

    Trả `thieu` = sự thật của thư mục CỦA MÌNH (đúng cái bản `.exe` nhìn
    thấy), `ngoai_lib` = gói đang mượn của môi trường khác. Hai câu hỏi KHÁC
    NHAU; gộp lại là tự lừa mình đúng kiểu cổng 58.
    """
    thieu: list[str] = []
    ngoai: list[str] = []
    for thu_muc, ten in ((lib_torch(), "torch"),
                         (thu_muc_gh(), "torchaudio"),
                         (thu_muc_gh(), "uroman")):
        if _co_goi(thu_muc, ten):
            continue
        thieu.append(ten)
        # Mượn được của môi trường đang chạy không? (chỉ để BÁO, KHÔNG tính là
        # đã cài — máy anh Hùng không có `.venv` để mượn.)
        try:
            import importlib.util as _iu
            if _iu.find_spec(ten) is not None:       # noqa: S001
                ngoai.append(ten)
        except Exception:                            # noqa: BLE001
            pass
    if not duong_model().is_file():
        thieu.append("model MMS_FA (1,18 GB)")
    py = _python_chay()
    if not py:
        thieu.append("python3 (máy chưa cài Python)")
    return {
        "co": not thieu,
        "thieu": thieu,
        "ngoai_lib": ngoai,
        "lib_torch": lib_torch(),
        "thu_muc": thu_muc_gh(),
        "model": str(duong_model()),
        # `cai_duoc` = BẤM NÚT TẢI CÓ ĂN THUA GÌ KHÔNG — câu hỏi KHÁC hẳn
        # `co`. Không có python thì pip không chạy được; chưa có torch trong
        # `_lib` thì gióng hàng vẫn thiếu chân dù tải xong phần của mình, nên
        # phải bấm nút *Tải bộ tách giọng* trước. Nút xám mà không nói vì sao
        # chỉ là câu đố (bài học cổng 58/16/51) -> `vi_sao_khong_cai` nói ra.
        "cai_duoc": bool(py) and _co_goi(lib_torch(), "torch"),
        "vi_sao_khong_cai": ("Máy chưa cài Python 3 (python.org)." if not py
                             else ("Chưa có torch — bấm 'Tải bộ tách giọng' "
                                   "ở hàng trên trước."
                                   if not _co_goi(lib_torch(), "torch")
                                   else "")),
    }


def co_giong_hang() -> bool:
    """Có chạy gióng hàng được không. KHÔNG import torch (xem bất biến 1+2).

    `BQ_GIONG_HANG=0` tắt hẳn -> mọi máy đọc quay về đúng cách lấy mốc cũ.
    Cần cái công tắc này vì hai lý do: đo A/B (bật/tắt trên CÙNG corpus mới
    so được), và gỡ rối trên máy user mà không phải xoá 1,18 GB model.
    """
    if (os.environ.get("BQ_GIONG_HANG") or "").strip() == "0":
        return False
    return bool(tinh_trang_giong_hang()["co"])


def _python_chay() -> list[str]:
    """Python dùng cho tiến trình con. [] = máy không có python nào."""
    if not getattr(sys, "frozen", False):
        return [sys.executable]
    for ten in ("python.exe", "python3.exe"):
        p = shutil.which(ten)
        if p:
            return [p]
    p = shutil.which("py")
    return [p, "-3"] if p else []


def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI vào log ngày — lùi êm mà im lặng thì đúng bằng hỏng âm
    thầm (cùng luật với `piper_tts._ghi_log` / `dubbing._ghi_log_el`)."""
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"giong_hang_{ts:%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:                                # noqa: BLE001
        pass


# ==========================================================================
# TẢI BỘ GIÓNG HÀNG — **CHỈ khi NGƯỜI DÙNG BẤM**
# ==========================================================================
#: Nhãn nút. Số là SỐ ĐO trên máy này (`model.pt` 1.203,6 MB + torchaudio/
#: uroman/regex vài MB), KHÔNG phải ước bừa. Nhãn sai là user bấm xong ngồi
#: đợi một lượt tải khác hẳn cái vừa đọc — đúng lỗi `NHAN_TAI_DEMUCS` ghi
#: 155 MB rồi hộp doạ 2 GB.
NHAN_TAI_GH = "Tải bộ gióng hàng (khoảng 1,2 GB)"

#: `torchaudio` phải `--no-deps`: nó khai phụ thuộc `torch`, mà torch đã nằm
#: sẵn trong `_lib` (4,3 GB bản CUDA). Không có cờ này thì pip tải THÊM một
#: bản torch nữa vào `thu_muc_gh()` — 2,5 GB trùng lặp cho thứ máy đã có.
#: `uroman` thì lấy CẢ phụ thuộc (`regex`, ~0,3 MB).
GOI_KHONG_DEPS = ("torchaudio",)
GOI_CO_DEPS = ("uroman",)

_KHOA_CAI = threading.Lock()

#: Tải model bằng CHÍNH `torch.hub` của torchaudio thay vì tự gõ URL: nó biết
#: đúng đường, tự kiểm hash, tự đặt tên file — và nếu bản torchaudio sau đổi
#: URL thì ta đi theo, không phải sửa hằng số. Chạy Ở TIẾN TRÌNH RIÊNG vì nó
#: `import torch` (bất biến 1).
_MA_TAI_MODEL = r'''
import os, sys
thu_muc, lib_torch = sys.argv[1:3]
sys.path.insert(0, lib_torch)
sys.path.insert(0, thu_muc)
os.environ.setdefault("TORCH_HOME", os.path.join(thu_muc, "_models"))
try:
    import torch
    from torchaudio.pipelines import MMS_FA
    MMS_FA.get_model()      # torch.hub tai ve <TORCH_HOME>/hub/checkpoints
    sys.stdout.write("BQOK\ttorch %s\n" % getattr(torch, "__version__", "?"))
except Exception as e:
    sys.stdout.write("BQLOI\t%s: %s\n" % (type(e).__name__, e))
sys.stdout.flush()
'''


def cai_giong_hang(on_progress: Optional[Callable[[float, str], None]] = None,
                   timeout: int = 5400) -> dict:
    """Tải `torchaudio` + `uroman` + model MMS_FA về `thu_muc_gh()`.

    **CHỈ chạy khi NGƯỜI DÙNG BẤM** — app không bao giờ tự tải 1,2 GB sau
    lưng người đang chạy sản xuất 300 kênh (cùng luật `cai_demucs`/
    `cai_piper`).

    **KHÔNG tự cài torch.** torch dùng CHUNG `_lib` với Demucs; hàm này chỉ
    ĐỌC chỗ đó (xem `lib_torch`). Thiếu torch thì báo thẳng là phải bấm nút
    *Tải bộ tách giọng* trước, chứ không âm thầm kéo về bản torch thứ hai —
    hai bản torch trong hai thư mục là đúng cách phá Demucs đang chạy.

    Trả `{ok, giay, thu_muc, loi, nhat_ky, tinh_trang}`. KHÔNG BAO GIỜ NÉM.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            try:
                on_progress(max(0.0, min(1.0, p)), m)
            except Exception:                            # noqa: BLE001
                pass

    d = thu_muc_gh()
    t0 = time.time()

    def _xong(ok: bool, loi: str = "", nk: Optional[list] = None) -> dict:
        return {"ok": ok, "loi": loi, "thu_muc": d,
                "giay": round(time.time() - t0, 2),
                "nhat_ky": (nk or [])[-40:],
                "tinh_trang": tinh_trang_giong_hang()}

    from app.core.thay_giong import _lenh_pip          # dùng lại, không viết mới
    pip = _lenh_pip()
    if not pip:
        return _xong(False, "Máy này không có python/pip nên app không tự tải "
                            "được. Cài Python 3 (python.org) rồi bấm lại, "
                            "hoặc copy thư mục _giong_hang từ máy đã cài sang.")
    if not _co_goi(lib_torch(), "torch"):
        return _xong(False, "Chưa có torch trong " + lib_torch() + ". Bấm nút "
                            "'Tải bộ tách giọng' ở hàng trên trước — gióng "
                            "hàng dùng CHUNG torch với bộ tách giọng, tải "
                            "riêng một bản nữa là thừa 2,5 GB.")
    if not _KHOA_CAI.acquire(blocking=False):
        return _xong(False, "Đang tải rồi — đợi lượt này xong.")

    nhat_ky: list[str] = []
    try:
        Path(d).mkdir(parents=True, exist_ok=True)
        # Cùng chỉ mục với torch đang có: bản `+cu126` và bản PyPI thường là
        # hai cây khác nhau, lấy lệch cây là torchaudio nạp lên báo thiếu DLL.
        from app.core.thay_giong import (CHI_MUC_TORCH_CPU,
                                         CHI_MUC_TORCH_CUDA, co_gpu_nvidia)
        chi_muc = CHI_MUC_TORCH_CUDA if co_gpu_nvidia() else CHI_MUC_TORCH_CPU
        for goi, khong_deps in ((GOI_KHONG_DEPS, True), (GOI_CO_DEPS, False)):
            args = [*pip, "install", "--no-input",
                    "--disable-pip-version-check", "--upgrade",
                    # `--ignore-installed`: thiếu cờ này thì pip coi gói máy
                    # đã có là "đã thoả mãn" rồi BỎ QUA, `--target` nhận thư
                    # mục rỗng -> máy dev vẫn chạy (mượn `.venv`) còn máy anh
                    # Hùng thì không. Đúng lỗi `_lib` của Demucs (cổng 58).
                    "--ignore-installed", "--target", d,
                    "--extra-index-url", chi_muc, *goi]
            if khong_deps:
                args.insert(-len(goi), "--no-deps")
            prog(0.02, "Đang tải " + ", ".join(goi) + "...")
            try:
                r = subprocess.run(args, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace",
                                   creationflags=_CREATE_NO_WINDOW,
                                   timeout=timeout)
            except subprocess.TimeoutExpired:
                return _xong(False, "Tải " + ", ".join(goi) + " quá lâu, đã "
                                    "dừng.", nhat_ky)
            nhat_ky += [x for x in (r.stdout or "").splitlines() if x.strip()]
            if r.returncode != 0:
                return _xong(False, "pip trả mã " + str(r.returncode) + ": "
                             + (r.stderr or r.stdout or "")[-500:], nhat_ky)

        # MODEL — phần nặng. torch.hub tự bỏ qua nếu file đã có.
        if duong_model().is_file():
            prog(0.98, "Model MMS_FA đã có sẵn, không tải lại.")
        else:
            prog(0.10, "Đang tải model gióng hàng MMS_FA (khoảng 1,18 GB, "
                       "chạy 1 lần)...")
            runner = Path(d) / "_bq_tai_model.py"
            runner.write_text(_MA_TAI_MODEL, encoding="utf-8")
            py = _python_chay()
            try:
                r2 = subprocess.run([*py, str(runner), d, lib_torch()],
                                    capture_output=True, text=True,
                                    encoding="utf-8", errors="replace",
                                    creationflags=_CREATE_NO_WINDOW,
                                    timeout=timeout)
            except subprocess.TimeoutExpired:
                return _xong(False, "Tải model gióng hàng quá lâu, đã dừng.",
                             nhat_ky)
            finally:
                try:
                    runner.unlink()
                except OSError:
                    pass
            ra = (r2.stdout or "") + "\n" + (r2.stderr or "")
            nhat_ky += [x for x in ra.splitlines() if x.strip()][-20:]
            if "BQOK\t" not in ra:
                return _xong(False, "Tải model gióng hàng hỏng: "
                             + ra.strip()[-500:], nhat_ky)

        # HẬU KIỂM BẰNG ĐƯỜNG DẪN, KHÔNG BẰNG "pip báo mã 0".
        # pip trả 0 mà thư mục vẫn thiếu là chuyện ĐÃ XẢY RA (cổng 58) — và
        # đó đúng là ca máy dev xanh / máy anh Hùng đỏ.
        prog(0.99, "Đang kiểm lại bộ gióng hàng...")
        tt = tinh_trang_giong_hang()
        if not tt["co"]:
            return _xong(False, "Chạy xong nhưng VẪN THIẾU: "
                         + ", ".join(tt["thieu"]) + " (trong " + d + "). "
                         "Đừng coi là đã cài — bản .exe sẽ không chạy được.",
                         nhat_ky)
        prog(1.0, "Đã tải xong bộ gióng hàng")
        _ghi_log(f"Đã cài bộ gióng hàng vào {d}")
        return _xong(True, "", nhat_ky)
    except Exception as e:                               # noqa: BLE001
        return _xong(False, f"{type(e).__name__}: {e}", nhat_ky)
    finally:
        _KHOA_CAI.release()


# ==========================================================================
# MÃ CHẠY Ở TIẾN TRÌNH RIÊNG
# ==========================================================================
#: Cố ý là script ĐỘC LẬP (chỉ cần lib + torch + torchaudio + uroman) chứ
#: không `-m app.core.giong_hang`: bản `.exe` KHÔNG chạy được `-m <module>` và
#: cũng không có cây mã nguồn, nên chung một đường thế này thì máy dev và máy
#: nhân viên chạy y hệt. Nhận việc qua FILE JSON (không qua argv): một mẻ có
#: thể hàng trăm câu, argv Windows chỉ chịu được 32.768 ký tự.
_MA_GIONG = r'''
import json, os, subprocess, sys, time

# `lib_torch` CHI DOC (torch dung chung voi Demucs) · `thu_muc` la phan rieng
# cua giong hang (torchaudio + uroman + model). Dat `thu_muc` TRUOC de goi
# rieng thang the neu co ngay trung ten.
thu_muc, lib_torch, viec_json, ket_json = sys.argv[1:5]
sys.path.insert(0, lib_torch)
sys.path.insert(0, thu_muc)
os.environ.setdefault("TORCH_HOME", os.path.join(thu_muc, "_models"))

with open(viec_json, "r", encoding="utf-8") as f:
    viec = json.load(f)
FFMPEG = viec["ffmpeg"]
SR = 16000


def bao(p, m):
    sys.stdout.write("BQP\t%.4f\t%s\n" % (p, m))
    sys.stdout.flush()


def doc_tieng(path):
    """Giai ma bang ffmpeg -> mono 16 kHz float32.

    KHONG dung torchaudio.load: tu 2.9 no doi hoi goi RIENG `torchcodec`.
    """
    r = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path, "-f", "s16le", "-ac", "1",
         "-ar", str(SR), "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("ffmpeg khong giai ma duoc %s: %s"
                           % (os.path.basename(path),
                              r.stderr.decode("utf-8", "replace")[-200:]))
    import numpy as np
    pcm = np.frombuffer(r.stdout, dtype="<i2").astype("float32") / 32768.0
    return pcm.copy()


try:
    bao(0.02, "Nap bo giong hang...")
    import numpy as np
    import torch
    import uroman as _ur
    from torchaudio.functional import forced_align, merge_tokens
    from torchaudio.pipelines import MMS_FA

    if int(viec.get("threads") or 0) > 0:
        torch.set_num_threads(int(viec["threads"]))
    dev = "cuda" if (viec.get("gpu", True) and torch.cuda.is_available()) \
        else "cpu"
    model = MMS_FA.get_model().to(dev).eval()
    BANG = MMS_FA.get_dict()
    uro = _ur.Uroman()
    bao(0.10, "Da nap (%s)" % dev)

    # DAU GACH NOI LA TOKEN BLANK — BO NO, KHONG THI HONG MOC CA CAU.
    # `BANG` cua MMS_FA anh xa '-' -> **0**, ma 0 chinh la blank truyen cho
    # `forced_align(blank=0)`. uroman GIU NGUYEN dau gach noi ("COVID-19" ->
    # "COVID-19"), nen mot chu co gach noi lam torchaudio nem
    # `ValueError: targets Tensor shouldn't contain blank index` -> khoi
    # `except` ben duoi tra `[]` cho CA CAU. Do that trong log ngay 18/08:
    # cau 11 tieng Viet chet vi chuoi "covid-chi con la bai...".
    # Loc theo ID (khong loc theo mat chu) de ban torchaudio sau co doi ky
    # tu blank thi van dung.
    BLANK = 0
    BO = {c for c, v in BANG.items() if v == BLANK} | {"*"}

    def ma_hoa(tu, lcode):
        """1 tu -> danh sach id token. Romanize TUNG TU (xem docstring)."""
        try:
            r = uro.romanize_string(tu, lcode=lcode)
        except Exception:
            r = uro.romanize_string(tu)
        r = (r or "").lower()
        return [BANG[c] for c in r if c in BANG and c not in BO]

    ket = []
    tong = max(1, len(viec["cap"]))
    t_all = time.time()
    giay_align = 0.0
    for i, cap in enumerate(viec["cap"]):
        try:
            toks = cap["tu"]
            lcode = cap.get("lcode") or "eng"
            ids, so_tok = [], []
            for t in toks:
                v = ma_hoa(t, lcode)
                so_tok.append(len(v))
                ids.extend(v)
            if not ids:
                ket.append([])
                continue
            pcm = doc_tieng(cap["wav"])
            wav = torch.from_numpy(pcm).unsqueeze(0).to(dev)
            t0 = time.time()
            with torch.inference_mode():
                em, _ = model(wav)
                # `torchaudio::forced_align` CHI CO BAN CPU (da do: goi tren
                # tensor CUDA nem NotImplementedError "only available for
                # these backends: [CPU, Meta, ...]"). Phan NANG la luot
                # wav2vec2 o tren, van chay GPU; buoc Viterbi nay re nen dua
                # ve CPU khong mat gi.
                lp = torch.log_softmax(em, dim=-1).cpu()
                al, sc = forced_align(
                    lp, torch.tensor([ids], dtype=torch.int32), blank=BLANK)
            spans = merge_tokens(al[0], sc[0].exp(), blank=BLANK)
            giay_align += time.time() - t0
            if len(spans) != len(ids):
                ket.append([])
                continue
            # KHUNG -> GIAY: ti le do THAT tu so mau / so khung, khong ghi
            # cung 0,02 s. Model doi stride la moi mo hinh im lang lech het.
            ti_le = len(pcm) / float(lp.shape[1]) / float(SR)
            moc, k = [], 0
            for j, t in enumerate(toks):
                n = so_tok[j]
                if n == 0:                    # token toan dau cau -> khong moc
                    continue
                a = spans[k].start * ti_le
                b = spans[k + n - 1].end * ti_le
                k += n
                moc.append([round(max(0.0, a), 3), round(b, 3), t])
            ket.append(moc)
        except Exception as e:
            ket.append([])
            sys.stdout.write("BQERR\t%d\t%s: %s\n" % (i, type(e).__name__, e))
            sys.stdout.flush()
        if (i + 1) % 5 == 0 or i + 1 == tong:
            bao(0.10 + 0.88 * (i + 1) / tong, "Giong hang %d/%d" % (i + 1, tong))
    out = {"ok": True, "moc": ket, "thiet_bi": dev,
           "giay": round(time.time() - t_all, 2),
           "giay_align": round(giay_align, 2),
           "torch": getattr(torch, "__version__", "?")}
except Exception as e:
    out = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}

with open(ket_json, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
sys.stdout.write("BQJSON\tOK\n")
sys.stdout.flush()
'''


def _viet_runner(tmp: Path, ma_lot: str) -> Path:
    """Ghi script chạy ra `<_viec>/_bq_giong_runner_<mã lượt>.py`.

    Ghi vào thư mục RIÊNG, KHÔNG vào `_lib` của Demucs — file này không có
    việc gì phải đụng vào đồ đang chạy sản xuất.

    **MỖI LƯỢT MỘT FILE RIÊNG. Đã thử hai cách rẻ hơn, CẢ HAI HỎNG TRÊN
    WINDOWS — đừng "dọn gọn" về lại:**
      · `write_text` đè lên MỘT đường dẫn dùng chung: mở chế độ `w` là CẮT
        CỤT ngay rồi mới ghi dần, nên luồng thứ hai cắt cụt đúng file mà
        tiến trình con của luồng thứ nhất đang đọc -> `SyntaxError` giữa
        dòng hoặc file rỗng, `rc` vẫn có thể là 0.
      · ghi tên tạm rồi `os.replace` (nguyên tử trên POSIX): Windows từ chối
        thay file ĐANG BỊ MỞ — đo thật ra
        `PermissionError [WinError 5] Access is denied` ngay lượt chạy song
        song đầu tiên, vì python con đang giữ handle chính file script đó.
    File riêng thì không có gì để tranh; `finally` của `giong_hang_loat` dọn,
    và `_don_rac_viec` quét mồ côi của lần chạy bị giết giữa chừng.
    """
    tmp.mkdir(parents=True, exist_ok=True)
    p = tmp / f"_bq_giong_runner_{ma_lot}.py"
    p.write_text(_MA_GIONG, encoding="utf-8")
    return p


# ==========================================================================
# MÃ NGÔN NGỮ CHO uroman
# ==========================================================================
#: uroman dùng mã ISO 639-3. Đưa sai mã thì nó vẫn chạy nhưng chép âm theo
#: luật ngôn ngữ KHÁC — chữ Hán mà đọc luật tiếng Nhật ra `konnichiha` thay vì
#: `nihao`, tức gióng hàng đi tìm một chuỗi âm KHÔNG có trong file tiếng.
_LCODE = {
    "vi": "vie", "en": "eng", "zh": "cmn", "ja": "jpn", "ko": "kor",
    "th": "tha", "fr": "fra", "de": "deu", "es": "spa", "ru": "rus",
    "id": "ind", "pt": "por", "it": "ita", "hi": "hin", "ar": "ara",
}


def _ma_ngon_ngu(lang: str) -> str:
    l = str(lang or "").strip().lower().replace("_", "-")
    if not l:
        return "eng"
    if l in _LCODE:
        return _LCODE[l]
    return _LCODE.get(l.split("-")[0], "eng")


# ==========================================================================
# CỬA CHÍNH
# ==========================================================================
def giong_hang_loat(wavs: list[str], texts: list[str], lang: str = "",
                    threads: int = 0, gpu: bool = True,
                    timeout: int = 3600,
                    on_progress: Optional[Callable[[float, str], None]] = None,
                    thong_tin: Optional[dict] = None,
                    ) -> list[list]:
    """Lấy mốc TỪNG CHỮ cho cả LOẠT (tiếng, chữ đã biết) — TIẾN TRÌNH RIÊNG.

    Trả `moc[i] = [[start_s, end_s, từ], ...]` — CÙNG hợp đồng với
    `dubbing._synth_all_words`, nên nơi gọi đặt thẳng vào chỗ cũ được.
    Câu nào gióng không nổi -> `[]` (KHÔNG bịa mốc); thiếu đồ / lỗi cả mẻ ->
    trả `[[] ...]` đủ độ dài để caller lùi êm về đường cũ.

    `thong_tin` (nếu truyền) được ĐIỀN THÊM `thiet_bi` · `giay` (cả lượt, kể
    cả nạp model) · `giay_align` (riêng phần gióng) · `torch`. Tách hai cột
    thời gian là bắt buộc: phí nạp model 1,18 GB là HẰNG SỐ mỗi lượt gọi, gộp
    nó vào thời gian gióng thì đo ra "gióng hàng chậm" trong khi thứ chậm là
    việc mở tiến trình.

    **GOM CẢ LOẠT VÀO MỘT LƯỢT GỌI.** Model 1,18 GB nạp mất ~3,5 giây; gọi
    từng câu là trả cái giá đó nhân số câu (đúng bài học `piper_tts.doc_loat`).
    """
    n = len(wavs)
    ra: list[list] = [[] for _ in range(n)]
    if n == 0:
        return ra
    if len(texts) != n:
        _ghi_log(f"số wav ({n}) khác số câu ({len(texts)}) -> bỏ qua gióng hàng")
        return ra

    tt = tinh_trang_giong_hang()
    if not tt["co"]:
        _ghi_log(f"Chưa đủ bộ gióng hàng (thiếu: {', '.join(tt['thieu'])}) "
                 f"-> LÙI về cách cũ")
        return ra

    from app.core import dubbing
    from config import settings

    lcode = _ma_ngon_ngu(lang)
    cap = []
    for i in range(n):
        # `_tach_tu` = CJK-aware. `.split()` cho câu Trung/Nhật ra 1 token
        # (bài học cổng 52/54) -> cả câu thành MỘT mốc = vô dụng.
        cap.append({"wav": str(wavs[i]),
                    "tu": dubbing._tach_tu(str(texts[i] or "")),
                    "lcode": lcode})

    thu_muc = thu_muc_gh()
    py = _python_chay()
    tmp = Path(thu_muc) / "_viec"
    tmp.mkdir(parents=True, exist_ok=True)
    _don_rac_viec(tmp)
    # TÊN DUY NHẤT MỖI LƯỢT GỌI — xem `_ma_lot`. Đặt theo `os.getpid()` là
    # hai luồng thay giọng song song ghi đè và XOÁ file của nhau.
    _lot = _ma_lot()
    runner = _viet_runner(tmp, _lot)
    p_viec = tmp / f"viec_{_lot}.json"
    p_ket = tmp / f"ket_{_lot}.json"
    p_viec.write_text(json.dumps(
        {"cap": cap, "ffmpeg": settings.FFMPEG_PATH, "threads": int(threads),
         "gpu": bool(gpu)}, ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if threads > 0:
        for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            env.setdefault(v, str(int(threads)))

    try:
        pr = subprocess.Popen(
            [*py, str(runner), thu_muc, lib_torch(), str(p_viec), str(p_ket)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=env,
            creationflags=_CREATE_NO_WINDOW)
        try:
            for dong in pr.stdout:                   # type: ignore[union-attr]
                if dong.startswith("BQP\t") and on_progress:
                    try:
                        _, p, m = dong.rstrip("\n").split("\t", 2)
                        on_progress(max(0.0, min(1.0, float(p))), m)
                    except Exception:                # noqa: BLE001
                        pass
                elif dong.startswith("BQERR\t"):
                    _ghi_log("câu " + dong.split("\t", 1)[1].strip())
            pr.wait(timeout=timeout)
        finally:
            if pr.poll() is None:
                pr.kill()
        if not p_ket.is_file():
            _ghi_log(f"tiến trình gióng hàng không ghi kết quả (mã "
                     f"{pr.returncode}): "
                     f"{(pr.stderr.read() if pr.stderr else '')[-300:]}")
            return ra
        d = json.loads(p_ket.read_text(encoding="utf-8"))
        if not d.get("ok"):
            _ghi_log(f"gióng hàng lỗi: {d.get('loi')}")
            return ra
        moc = d.get("moc") or []
        for i in range(min(n, len(moc))):
            ra[i] = _don_moc(moc[i])
        if thong_tin is not None:
            for k in ("thiet_bi", "giay", "giay_align", "torch"):
                thong_tin[k] = d.get(k)
        _ghi_log(f"gióng hàng {sum(1 for x in ra if x)}/{n} câu · "
                 f"{d.get('thiet_bi')} · {d.get('giay')}s "
                 f"(riêng gióng {d.get('giay_align')}s) · torch {d.get('torch')}")
        return ra
    except Exception as e:                           # noqa: BLE001
        _ghi_log(f"gióng hàng hỏng: {type(e).__name__}: {e} -> LÙI về cách cũ")
        return ra
    finally:
        # Dọn ĐÚNG file của lượt này (tên mang `_lot`) — không còn chuyện
        # xoá nhầm file kết quả của luồng đang chạy song song.
        for p in (p_viec, p_ket, runner):
            try:
                p.unlink()
            except OSError:
                pass


def _don_moc(moc: list) -> list:
    """Bỏ mốc vô lý thay vì để nó chạy tiếp xuống phụ đề.

    Mốc phải TĂNG DẦN và không âm. Mốc lùi về sau là dấu hiệu tính sai tỉ lệ
    khung — để lọt thì chữ nhảy ngược, mà `rc` vẫn 0 và không một dòng báo.
    """
    ra = []
    truoc = _NGUONG_AM
    for m in moc or []:
        try:
            a, b, w = float(m[0]), float(m[1]), str(m[2])
        except Exception:                            # noqa: BLE001
            continue
        if a < _NGUONG_AM or b < a or a < truoc - 0.001:
            return []                                # cả câu đáng ngờ -> bỏ
        truoc = a
        ra.append([round(a, 3), round(b, 3), w])
    return ra
