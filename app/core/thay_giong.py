# -*- coding: utf-8 -*-
"""THAY GIỌNG NÓI — thay LỜI THOẠI sang tiếng khác, GIỮ NGUYÊN nhạc + tiếng động.

KHÁC HẲN `dubbing.py`: `dubbing` CHỒNG giọng mới lên trên tiếng gốc (voice-over,
tiếng gốc vẫn nghe thấy bên dưới). Ở đây tiếng gốc bị **TÁCH BỎ HẲN**, chỉ giữ
lại lớp nhạc nền + tiếng động hiện trường, rồi đặt giọng đã dịch vào chỗ trống.

SÁU BƯỚC (mỗi bước có hàm riêng, đo được riêng):
  1. `tach_giong`      — tách lớp NHẠC (giữ) khỏi lớp GIỌNG (bỏ).
  2. `chep_loi`        — chép lời gốc, có mốc từng từ (dùng `transcribe.py`).
  3. `dich_hau_kiem`   — dịch + DỊCH NGƯỢC tự chấm, câu lệch thì dịch lại.
  4. `doc_ban_dich`    — TTS bản dịch (dùng `dubbing.py`).
  5. `khop_thoi_gian`  — co giãn atempo từng câu về đúng mốc gốc.
  6. `tron_thay_giong` — trộn giọng mới lên lớp nhạc đã giữ.

======================================================================
BẪY ĐÃ ĐO ĐƯỢC TRÊN VIDEO THẬT — ĐỌC TRƯỚC KHI SỬA
======================================================================
· CÁCH NHẸ (trừ kênh giữa) CHỈ LÀ ĐƯỜNG LUI, KHÔNG PHẢI LỰA CHỌN.
  Video thật của anh Hùng gần như DUAL-MONO: tương quan L/R đo được 0,963
  (video Trung) và 0,950 (video Anh). Tín hiệu cạnh (L-R)/2 chỉ còn -17,4 dB
  so với bản gốc -> trừ kênh giữa VỨT LUÔN ~98% năng lượng, gồm cả nhạc.
  Vì vậy `tach_nhe` PHẢI cộng lại dải trầm (`_TRAM_HZ`) nếu không track "nhạc"
  ra gần như im lặng và anh Hùng mất hết nhạc nền.
· L == R TUYỆT ĐỐI (mono nhân đôi) thì trừ kênh giữa ra ĐÚNG SỐ 0. Phải chặn
  bằng `_co_the_tru_kenh_giua` -> ra 0 thì trả lỗi, KHÔNG ghi file im lặng rồi
  báo thành công.
· ffmpeg trả mã 0 mà file rỗng / RMS = 0 là chuyện ĐÃ XẢY RA. Mọi hàm ghi file
  ở đây phải `_kiem_wav` (tồn tại + độ dài + RMS > 0) chứ KHÔNG tin mã thoát.
· đọc `astats` phải dùng `in`, KHÔNG `startswith` — mỗi dòng có tiền tố
  `[Parsed_astats_0 @ ...]` nên `startswith` không bao giờ khớp và mọi file ra
  -99 dBFS (ca "không méo" tự PASS vĩnh viễn).
· `alimiter` PHẢI `level=0` (mặc định `level=true` tự nâng +3,1 dB) và
  `latency=1` (không có thì trễ 0,98 ms).
· mono -> stereo phải dùng `pan` với toán tử `<` (không chuẩn hoá lại), nếu để
  ffmpeg tự đổi bố cục là MẤT ĐÚNG 3,0 dB ÂM THẦM.
· `amix` phải `normalize=0`, không thì biên độ bị chia theo số đầu vào.
· torch trong `.venv` của app là bản **CPU** (`2.13.0+cpu`) — `cuda.is_available()`
  trả False KỂ CẢ khi máy có RTX 3060. Muốn GPU phải cài lại torch bản CUDA.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from importlib.machinery import PathFinder
from pathlib import Path
from typing import Callable, Optional

from config import settings

_CREATE_NO_WINDOW = 0x0800_0000 if os.name == "nt" else 0


class HuyBo(Exception):
    """NGƯỜI DÙNG BẤM HUỶ — không phải "video lỗi".

    `thay_giong_video` bọc cả 6 bước trong `except Exception` để một video
    hỏng không làm chết cả lượt. Nhưng `CanceledError` của bộ điều phối cũng
    là `Exception` -> nếu không có lớp RIÊNG thì bấm Huỷ bị ghi thành LỖI
    VIDEO, và job kết thúc 'failed' rồi TỰ THỬ LẠI (bài học "huỷ ≠ lỗi").
    """

#: Lớp GIỮ LẠI (nhạc nền + tiếng động hiện trường) và lớp VỨT ĐI.
LOP_GIU = ("drums", "bass", "other")
LOP_BO = "vocals"

#: Demucs làm việc ở đúng tần số này (htdemucs). Sai tần số là sai kết quả.
SR_TACH = 44100

#: Trần đỉnh sau khi trộn (dBFS) — theo luật "không méo" của CLAUDE.md.
TRAN_DINH_DB = -1.0

#: Dải TRẦM cộng lại sau khi trừ kênh giữa. Nhạc nền/trống nằm phần lớn ở đây
#: và gần như luôn ở giữa -> không cộng lại là mất bass sạch.
_TRAM_HZ = 220

#: Dải CAO cộng lại (chũm chọe, tiếng động sắc). Giọng người gần như hết ở
#: 8 kHz nên cộng lại phần trên đó không kéo giọng về.
_CAO_HZ = 7000


# ==================================================================
# HẠ TẦNG — gọi ffmpeg và ĐO, tuyệt đối không tin mã thoát
# ==================================================================

def _gan_job(p) -> None:
    """Gắn tiến trình ffmpeg vào JOB đang chạy trên thread này (nếu có).

    Không gắn thì bấm Huỷ chỉ đặt cờ, còn lệnh ffmpeg đang chạy vẫn chạy tới
    hết (1-2 phút) — đúng bệnh đã chữa cho đường xuất clip.
    """
    try:
        from app.queue.worker import register_job_proc
        register_job_proc(p)
    except Exception:  # noqa: BLE001 - chạy ngoài app (script đo) thì bỏ qua
        pass


def _bo_gan_job(p) -> None:
    try:
        from app.queue.worker import unregister_job_proc
        unregister_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


def _ffmpeg(args: list[str], what: str, timeout: int = 900) -> None:
    """Chạy ffmpeg. In mã thoát THẬT khi lỗi (không nối `| tail` để khỏi mất mã).

    Dùng `Popen` chứ không `subprocess.run` để GẮN được tiến trình vào job —
    bấm Huỷ là ffmpeg bị giết ngay, không phải đợi lệnh chạy hết.
    """
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
           *args]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8",
                         errors="replace", creationflags=_CREATE_NO_WINDOW)
    _gan_job(p)
    try:
        _out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        raise
    finally:
        _bo_gan_job(p)
    if p.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lỗi khi {what} (mã thoát {p.returncode}): "
            f"{(err or '')[-500:]}")


def probe_duration(path: str | Path) -> float:
    """Độ dài (giây) bằng ffprobe; 0.0 nếu lỗi."""
    cmd = [settings.FFPROBE_PATH, "-v", "error", "-print_format", "json",
           "-show_format", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace",
                             creationflags=_CREATE_NO_WINDOW, timeout=120)
        return float(json.loads(out.stdout or "{}")
                     .get("format", {}).get("duration", 0) or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


def do_khung_hinh(path: str | Path) -> int:
    """SỐ KHUNG HÌNH thật (đếm gói) — để bắt ca "mã 0 mà video 0 khung"."""
    cmd = [settings.FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
           "-count_packets", "-show_entries", "stream=nb_read_packets",
           "-of", "csv=p=0", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace",
                             creationflags=_CREATE_NO_WINDOW, timeout=600)
        return int((out.stdout or "0").strip().rstrip(",") or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def do_rms(path: str | Path, start: float = 0.0, dur: float = 0.0) -> float:
    """RMS (biên độ 0..1) của audio, đọc qua `astats`. 0.0 = IM LẶNG HẲN.

    BẪY: `astats` in `RMS level dB: -inf` cho track im lặng -> float('-inf'),
    phải bắt để không nổ ValueError.
    """
    args = ["-hide_banner", "-nostats"]
    if start > 0:
        args += ["-ss", f"{start:.3f}"]
    args += ["-i", str(path)]
    if dur > 0:
        args += ["-t", f"{dur:.3f}"]
    args += ["-map", "0:a:0", "-af",
             "astats=measure_overall=RMS_level:measure_perchannel=none",
             "-f", "null", "-"]
    try:
        r = subprocess.run([settings.FFMPEG_PATH, *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return -1.0
    for line in (r.stderr or "").splitlines():
        if "RMS level dB:" in line:                 # `in`, KHÔNG startswith
            raw = line.split(":")[-1].strip()
            if raw.lower().lstrip("-") in ("inf", "nan"):
                return 0.0
            try:
                return 10.0 ** (float(raw) / 20.0)
            except ValueError:
                return -1.0
    return -1.0


def do_meo(path: str | Path) -> dict:
    """Đỉnh (dBFS) + số mẫu CHẠM TRẦN, đọc bằng `astats` (dùng `in`).

    BẪY ĐÃ SẬP THẬT (14/08, bản đầu của hàm này): tên chỉ số
    `Number_of_clipped_samples` KHÔNG TỒN TẠI trong ffmpeg N-121186 -> cả lệnh
    ffmpeg CHẾT ("Unable to parse measure_overall") -> hàm trả
    `{dinh: None, cham_tran: None}` IM LẶNG -> mọi phép kiểm "có méo không"
    đọc None rồi cho qua = TỰ PASS OAN VĨNH VIỄN. Tên đúng là `Abs_Peak_count`
    (in ra dòng "Abs Peak count:").
    Nay ffmpeg lỗi thì NÉM, không trả None âm thầm.
    """
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-i", str(path),
           "-map", "0:a:0", "-af", "astats=measure_overall=Peak_level+"
           "Abs_Peak_count:measure_perchannel=none",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"Không chạy được astats để đo méo: {e}") from e
    if r.returncode != 0:
        raise RuntimeError(
            f"astats lỗi khi đo méo (mã {r.returncode}): "
            f"{(r.stderr or '')[-300:]}")
    dinh, cham = None, None
    for line in (r.stderr or "").splitlines():
        if "Peak level dB:" in line:
            raw = line.split(":")[-1].strip()
            if raw.lower().lstrip("-") not in ("inf", "nan"):
                try:
                    dinh = float(raw)
                except ValueError:
                    pass
        if "Abs Peak count:" in line:
            try:
                cham = int(float(line.split(":")[-1].strip()))
            except ValueError:
                pass
    if dinh is None:
        raise RuntimeError(
            "astats chạy xong mà KHÔNG có dòng 'Peak level dB' — đừng coi là "
            "'không méo', hãy sửa phép đo.")
    return {"dinh": dinh, "cham_tran": cham}


def _kiem_wav(path: str | Path, cho_phep_im: bool = False,
              toi_thieu_giay: float = 0.05) -> float:
    """KIỂM file audio vừa ghi: có thật + đủ dài + CÓ TIẾNG. Trả độ dài.

    Đây là lá chắn cho bẫy "ffmpeg trả mã 0 mà file 0 KiB / RMS 0".
    """
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"Không có file {p.name} (ffmpeg im lặng không ghi)")
    if p.stat().st_size < 1024:
        raise RuntimeError(f"File {p.name} rỗng ({p.stat().st_size} byte)")
    d = probe_duration(p)
    if d < toi_thieu_giay:
        raise RuntimeError(f"File {p.name} chỉ {d:.3f} giây (coi như hỏng)")
    if not cho_phep_im:
        r = do_rms(p)
        if r <= 0.0:
            raise RuntimeError(
                f"File {p.name} IM LẶNG HẲN (RMS {r}) — ffmpeg trả mã 0 nhưng "
                "không có tiếng")
    return d


def tach_wav(video: str | Path, out_wav: str | Path,
             sr: int = SR_TACH, ac: int = 2) -> float:
    """Rút audio từ video ra WAV `sr` Hz / `ac` kênh. Trả độ dài."""
    _ffmpeg(["-i", str(video), "-vn", "-ac", str(ac), "-ar", str(sr),
             "-c:a", "pcm_s16le", str(out_wav)], "rút audio khỏi video")
    return _kiem_wav(out_wav)


# ==================================================================
# BƯỚC 1 — TÁCH GIỌNG / NHẠC + TIẾNG ĐỘNG
# ==================================================================

def lib_demucs() -> str:
    """Thư mục cài Demucs RIÊNG — cố ý KHÔNG cài vào `.venv` của app.

    Một lượt `pip install demucs` kéo theo torch/torchaudio có thể phá app đang
    chạy sản xuất 300 kênh của anh Hùng. Đường dẫn từ env `BQ_DEMUCS_LIB`,
    mặc định `<repo>/_lib` khi chạy nguồn.

    **BẢN `.exe` PHẢI ĐẶT NGOÀI `_internal` — ĐO ĐƯỢC, KHÔNG PHÒNG XA:**
    `Path(__file__).parents[2]` trong bản đóng gói trỏ vào **`_internal`**, mà
    `self_update.py` cập nhật bằng cách `ren _internal -> _internal.old` rồi
    `rmdir /S /Q _internal.old` — tức **mỗi lượt tự cập nhật là xoá sạch `_lib`**
    và anh Hùng phải tải lại 155 MB. App này tự cập nhật liên tục, nên đó không
    phải rủi ro lý thuyết mà là chuyện chắc chắn xảy ra.
    `config.py` đã tách sẵn `DATA_DIR` đúng vì lý do này (*"Tách 2 cái để khi
    cập nhật bản .exe (thay _internal) KHÔNG làm mất dữ liệu người dùng"*) — đi
    theo nó. CHỈ đổi ở nhánh `frozen`: chạy nguồn vẫn `<repo>/_lib` y như cũ nên
    `_lib` đã tải sẵn của máy dev không bị bỏ rơi.
    """
    p = (os.environ.get("BQ_DEMUCS_LIB") or "").strip()
    if p:
        return p
    if getattr(sys, "frozen", False):
        # Đọc `config.DATA_DIR` MỖI LẦN GỌI, không cất sẵn vào hằng số — cổng
        # test đổi `BQ_DATA_DIR` rồi nạp lại config (bài học `tg_so.duong_so`).
        import config
        return str(Path(config.DATA_DIR) / "_lib")
    return str(Path(__file__).resolve().parents[2] / "_lib")


def _duoi_thu_muc(duong: str, thu_muc: str) -> bool:
    """`duong` có nằm TRONG `thu_muc` không (so đường dẫn THẬT, đã resolve)."""
    if not duong or not thu_muc:
        return False
    try:
        a = Path(duong).resolve()
        b = Path(thu_muc).resolve()
    except (OSError, ValueError):        # đường dẫn rác / ổ đĩa đã rút
        return False
    return a == b or b in a.parents


def _duong_cua_spec(sp) -> str:
    """Đường dẫn file THẬT của một `ModuleSpec` ('' = không xác định được)."""
    if sp is None:
        return ""
    o = sp.origin or ""
    if o in ("", "namespace", "built-in", "frozen"):
        locs = list(getattr(sp, "submodule_search_locations", None) or [])
        o = locs[0] if locs else ""
    return o


def _tim_goi(ten: str, duong: Optional[list[str]]) -> str:
    """Gói `ten` nằm ở đâu khi tìm trong `duong` (None = `sys.path`). '' = không có.

    **DÙNG `PathFinder` CHỨ KHÔNG `importlib.util.find_spec` — 2 lý do:**
    (a) `find_spec("demucs.pretrained")` **IMPORT gói cha** `demucs` thật; ở đây
        chỉ cần biết FILE nằm đâu nên không có cớ gì phải nạp mã người khác vào
        tiến trình app (và đó là đường dẫn tới bẫy `import torch` sau Qt).
    (b) `find_spec` luôn tìm trên `sys.path` nên KHÔNG trả lời được câu hỏi
        *"gói này có nằm THẬT trong `_lib` không"* — nó vui vẻ trả về gói của
        `.venv` máy dev. `PathFinder.find_spec(ten, [lib])` tìm ĐÚNG trong `lib`.
    """
    try:
        return _duong_cua_spec(PathFinder.find_spec(ten, duong))
    except Exception:  # noqa: BLE001 - gói cha hỏng / thư mục không đọc được
        return ""


def _demucs_du_bo(duong: str) -> bool:
    """`demucs` tìm thấy ở `duong` có kèm `pretrained.py` không (cài dở thì không)."""
    try:
        return (Path(duong).parent / "pretrained.py").is_file()
    except (OSError, ValueError):
        return False


def do_goi_tach_giong(lib: str = "") -> dict:
    """TỪNG gói tách giọng đang nằm ở ĐÂU — KHÔNG import một dòng nào.

    Trả `{tên: {"lib": <đường trong _lib|"">, "he": <đường NGOÀI _lib|"">,
    "nguon": "_lib" | "hệ thống" | ""}}`.

    **VÌ SAO PHẢI PHÂN BIỆT `_lib` VỚI "hệ thống" — LỖI THẬT ANH HÙNG GẶP
    (14/08/2026, *"trước tôi nhớ báo cài rồi mà nay nó ghi chưa có bộ tách
    giọng"*):** bản cũ chèn `_lib` vào `sys.path` rồi hỏi `find_spec` "import
    được không". Trên máy dev, `.venv` đã có `torch` + `soundfile` nên câu trả
    lời luôn là CÓ **kể cả khi `_lib` không hề có torch** -> app báo "đã cài",
    `thieu = []`. Bản `.exe` không có `.venv` -> cùng một `_lib` đó lại báo
    "chưa có bộ tách giọng". Máy dev XANH, máy thật ĐỎ, không ai phát hiện.
    ĐO ĐƯỢC trên chính `_lib` của anh Hùng: `demucs` -> `_lib\\demucs`, còn
    `torch` -> `.venv\\Lib\\site-packages\\torch` và `soundfile` ->
    `.venv\\...\\soundfile.py`. Tức **2/3 gói chưa bao giờ nằm trong `_lib`.**
    Vì vậy câu hỏi đúng là *"`spec.origin` có nằm dưới `_lib` không"*, không
    phải *"import được không"*.
    """
    lib = lib or lib_demucs()
    try:
        co_thu_muc = Path(lib).is_dir()
    except (OSError, ValueError):
        co_thu_muc = False
    duong_lib = [lib] if co_thu_muc else []
    ra: dict = {}
    for ten in GOI_TACH_GIONG:
        o_lib = _tim_goi(ten, duong_lib) if duong_lib else ""
        if o_lib and ten == "demucs" and not _demucs_du_bo(o_lib):
            o_lib = ""                  # có thư mục nhưng cụt -> coi như chưa có
        he = ""
        if not o_lib:
            he = _tim_goi(ten, None)
            # `sys.path` có thể ĐÃ chứa `_lib` (lượt dò trước chèn vào) — tìm
            # thấy ở đó thì vẫn là `_lib`, đừng đếm nhầm thành "hệ thống".
            if he and _duoi_thu_muc(he, lib):
                o_lib, he = he, ""
                if ten == "demucs" and not _demucs_du_bo(o_lib):
                    o_lib = ""
            elif he and ten == "demucs" and not _demucs_du_bo(he):
                he = ""
        ra[ten] = {"lib": o_lib, "he": he,
                   "nguon": "_lib" if o_lib else ("hệ thống" if he else "")}
    return ra


def co_demucs() -> bool:
    """Máy này CÓ Demucs + torch không — dò bằng đường dẫn, KHÔNG import.

    **VÌ SAO KHÔNG ĐƯỢC IMPORT THẬT (đo được 14/08, không phải phòng xa):**
    trong tiến trình đã nạp PyQt6 + `QApplication` thì `import torch` CHẾT với
    `OSError [WinError 1114] ... Error loading torch\\lib\\c10.dll`. App này
    LÀ app Qt, nên hàm bản cũ (import thật) trả **False trên chính máy ĐANG
    CÓ Demucs** -> UI báo "máy chưa cài" và người ta đi cài lại lần nữa.
    Đo: torch TRƯỚC Qt -> OK · torch SAU Qt -> WinError 1114 (tái hiện 100%).

    Dò bằng `PathFinder` (chỉ TÌM file, không nạp DLL) -> chạy đúng ở cả hai
    thứ tự. Việc "chạy được thật không" do `_tach_demucs` (tiến trình riêng)
    trả lời, và nó báo lỗi THẬT chứ không im lặng.

    **TRẢ LỜI CÂU "MÁY NÀY CHẠY ĐƯỢC KHÔNG", KHÔNG PHẢI "`_lib` ĐÃ ĐỦ CHƯA".**
    Hai câu đó KHÁC NHAU trên máy dev: bước tách chạy bằng `_python_chay_tach()`
    = `sys.executable` (python của `.venv`), nên gói nằm trong `.venv` vẫn dùng
    được thật. Muốn biết bản `.exe` sẽ thấy gì thì đọc `tinh_trang_demucs()`
    khoá **`du_lib`** / **`thieu`** — đó mới là sự thật của `_lib`.
    Chốt quan trọng: hàm này KHÔNG còn chèn `_lib` vào `sys.path` nữa. Chèn vào
    là tự tay làm bẩn phép đo của mọi lượt dò sau (và của tiến trình giả lập
    `.exe` ở cổng 58).
    """
    goi = do_goi_tach_giong()
    return all(goi[t]["nguon"] for t in GOI_TACH_GIONG)


def qt_da_nap() -> bool:
    """Tiến trình NÀY đã nạp Qt chưa (chỉ NGÓ `sys.modules`, không import gì).

    Dùng để CHẶN `import torch` — xem `thiet_bi_tach`.
    """
    return any(m == "PyQt6" or m.startswith("PyQt6.") for m in sys.modules)


def thiet_bi_tach() -> str:
    """'cuda' nếu torch build CÓ CUDA và thấy GPU · 'cpu' · **'' = chưa biết**.

    ĐÃ ĐO: `.venv` app cài torch **2.13.0+cpu** nên trả 'cpu' KỂ CẢ khi máy có
    RTX 3060. Đây là con số quyết định tốc độ — xem báo cáo.

    **TRẢ '' NGAY KHI TIẾN TRÌNH ĐÃ NẠP Qt — ĐỪNG GỠ CHỐT NÀY.** `try/except`
    quanh `import torch` KHÔNG đủ: trước khi ném `OSError [WinError 1114]`,
    `torch/__init__.py:_load_dll_libraries` gây **ACCESS VIOLATION** ở tầng
    native. Cái đó KHÔNG bắt được bằng `except`; `faulthandler` của app (bật
    từ cổng 6) chộp được và ghi `logs/crash_native.txt` — tức mỗi lần anh Hùng
    mở hộp "Thay giọng nói" là một dòng crash native, và app đứng trước rủi ro
    chết thật. Đo được 14/08/2026 bằng chính `_test_app_smoke.py`:
    *"Windows fatal exception: access violation"* với ngăn xếp
    `_thay_giong_dialog -> tinh_trang_demucs -> thiet_bi_tach -> import torch`.
    Đây là ĐÚNG cái bẫy cổng 55 đã ghi, chỉ là còn SÓT một cửa: `co_demucs` và
    `tinh_trang_demucs` đã đổi sang `find_spec` rồi, riêng hàm này thì chưa.

    '' KHÔNG PHẢI 'cpu': trả 'cpu' cho ca chưa-biết là NÓI DỐI người dùng (máy
    có CUDA vẫn hiện "chạy trên CPU"). Thiết bị THẬT do `_tach_demucs` đọc ở
    TIẾN TRÌNH RIÊNG và ghi vào khoá `thiet_bi` của kết quả — đọc số đó.
    """
    if qt_da_nap():
        return ""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


# ==================================================================
# DÒ BỘ TÁCH GIỌNG + CHO NGƯỜI DÙNG BẤM TẢI
# ==================================================================
#
# HƯỚNG ĐÃ CHỐT: app TỰ DÒ, THIẾU thì HIỆN NÚT để NGƯỜI DÙNG BẤM TẢI.
# TUYỆT ĐỐI KHÔNG tự tải sau lưng (2 GB trên đường mạng của anh Hùng) và
# TUYỆT ĐỐI KHÔNG tự lui sang "cách nhẹ" — đo được rò rỉ lời 100% (tiếng
# Trung) / 86,3% (tiếng Anh), tức giọng cũ CÒN NGUYÊN chồng lên giọng mới mà
# ffmpeg vẫn trả mã 0, không một dòng báo. Trên 200-300 kênh là hỏng hàng loạt.

#: Các gói phải có mới tách được giọng. `soundfile` để đọc/ghi wav cho Demucs.
GOI_TACH_GIONG = ("torch", "demucs", "soundfile")

#: Nhãn nút TẢI (tiếng Việt, KHÔNG EMOJI — máy anh Hùng thiếu font).
#: SỐ ĐO 14/08/2026 (hỏi metadata chỉ mục, KHÔNG tải thật): 33 gói = **154,0 MB
#: tải về** (torch 121,9 MB + 32,1 MB còn lại), bung ra đĩa ~700 MB (riêng
#: torch 513,6 MB, đo trên `.venv`). "Khoảng 2 GB" của bản cũ là ƯỚC BỪA — nó
#: doạ người dùng bằng con số gấp 13 lần lượng tải thật.
NHAN_TAI_DEMUCS = "Tải bộ tách giọng (tải khoảng 155 MB)"

#: Nhãn khi `_lib` đã có MỘT PHẦN (vd có demucs, thiếu torch). Ghi "Tải bộ tách
#: giọng" lúc này là nói sai: người dùng tưởng chưa có gì và tưởng phải tải lại
#: từ đầu.
NHAN_CAI_TIEP = "Cài tiếp phần còn thiếu"


def nhan_nut_tai(tt: Optional[dict] = None) -> str:
    """Nhãn ĐÚNG cho nút tải, theo tình trạng `_lib` hiện tại."""
    tt = tt if tt is not None else tinh_trang_demucs()
    thieu = list(tt.get("thieu") or [])
    if thieu and len(thieu) < len(GOI_TACH_GIONG):
        return NHAN_CAI_TIEP + " (" + ", ".join(thieu) + ")"
    return NHAN_TAI_DEMUCS

#: Một lượt tải/cài duy nhất tại một thời điểm (user bấm 2 lần vẫn 1 lượt).
_KHOA_CAI = threading.Lock()

# ĐÃ GỠ `_MA_KIEM_LIB` + `kiem_lib_bang_tien_trinh_rieng` (14/08/2026).
# Chúng chạy python riêng rồi `sys.path.insert(0, lib)` và hỏi "`__import__` có
# chạy không". Nhưng python riêng ấy CHÍNH LÀ python của `.venv`, nên nó mượn
# torch của `.venv` rồi báo "cài xong" trong khi `_lib` vẫn rỗng torch — đúng
# cái bẫy nó sinh ra để chặn. Giữ lại một hàm kiểm biết nói dối thì nguy hiểm
# hơn không có hàm nào (phép đo hỏng phát chứng nhận cho thứ vẫn hỏng).
# Thay bằng `do_goi_tach_giong()`: so `spec.origin` với `_lib`, không import gì.


def _lenh_pip() -> list[str]:
    """Lệnh pip dùng để TẢI bộ tách giọng. [] = máy này không cài được.

    Bản `.exe` (PyInstaller) KHÔNG có pip nên `sys.executable` vô dụng — phải
    tìm python của máy. Không có thì BÁO RÕ chứ không im lặng thất bại.
    """
    if not getattr(sys, "frozen", False):
        return [sys.executable, "-m", "pip"]
    for ten in ("python.exe", "python3.exe"):
        p = shutil.which(ten)
        if p:
            return [p, "-m", "pip"]
    p = shutil.which("py")
    if p:
        return [p, "-3", "-m", "pip"]
    return []


def tinh_trang_demucs() -> dict:
    """Máy này đã có bộ tách giọng chưa? KHÔNG tải gì, KHÔNG gọi mạng.

    Trả {co, du_lib, thieu, ngoai_lib, nguon, goi, lib, thiet_bi, cai_duoc,
    loi_nhan}. Đọc cho đúng — 3 khoá này trả lời 3 câu HỎI KHÁC NHAU:

    · **`thieu`** = gói KHÔNG nằm trong `_lib`. **Đây đúng là cái bản `.exe` sẽ
      thấy** (máy nhân viên không có `.venv` nào để mượn). Nhãn/nút phải bám
      khoá này, đừng bám `co`.
    · **`du_lib`** = `not thieu`. `_lib` tự đứng được một mình chưa.
    · **`co`** = máy NÀY chạy được không (tính cả gói mượn của môi trường hệ
      thống). Chỉ dùng để khoá/mở nút Chạy — trên máy dev nó True trong khi
      `_lib` vẫn thiếu torch, và đó là ĐÚNG chứ không phải mâu thuẫn.
    · **`ngoai_lib`** = gói đang được MƯỢN của môi trường hệ thống. Danh sách
      này KHÔNG RỖNG nghĩa là *"máy này chạy được, máy anh Hùng thì không"* —
      phải nói thẳng ra màn hình, vì đây chính là chỗ đã lừa một lần rồi.
    """
    lib = lib_demucs()
    goi = do_goi_tach_giong(lib)
    thieu = [t for t in GOI_TACH_GIONG if not goi[t]["lib"]]
    ngoai_lib = [t for t in thieu if goi[t]["he"]]
    khong_dau = [t for t in GOI_TACH_GIONG if not goi[t]["nguon"]]
    co = not khong_dau
    return {
        "co": co,
        "du_lib": not thieu,
        "thieu": thieu,
        "ngoai_lib": ngoai_lib,
        "goi": goi,
        "nguon": {t: goi[t]["nguon"] for t in GOI_TACH_GIONG},
        "duong": {t: (goi[t]["lib"] or goi[t]["he"]) for t in GOI_TACH_GIONG},
        "lib": lib,
        # '' = CHƯA BIẾT. Hàm này là cửa UI gọi (hộp "Thay giọng nói" dựng
        # trong tiến trình app ĐÃ NẠP Qt), nên `thiet_bi_tach` ở đây LUÔN trả
        # '' — đúng như thiết kế, không phải thiếu sót. Thiết bị THẬT nằm ở
        # kết quả của `_tach_demucs` (tiến trình riêng).
        "thiet_bi": thiet_bi_tach() if co else "",
        "cai_duoc": bool(_lenh_pip()),
        "loi_nhan": "" if co else THIEU_DEMUCS,
    }


def cai_demucs(on_progress: Optional[Callable[[float, str], None]] = None,
               timeout: int = 5400) -> dict:
    """TẢI + CÀI bộ tách giọng vào `_lib`. **CHỈ gọi khi NGƯỜI DÙNG BẤM.**

    Cài vào thư mục RIÊNG `_lib` (env `BQ_DEMUCS_LIB`), CỐ Ý KHÔNG cài vào
    `.venv` của app: một lượt `pip install demucs` kéo theo torch/torchaudio
    có thể phá app đang chạy sản xuất 300 kênh của anh Hùng.

    Trả {ok, giay, lib, ma_thoat, loi, nhat_ky}. Không bao giờ tự chạy nền.
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            on_progress(max(0.0, min(1.0, p)), m)

    lib = lib_demucs()
    pip = _lenh_pip()
    if not pip:
        return {"ok": False, "lib": lib, "giay": 0.0,
                "loi": "Máy này không có python/pip nên app không tự tải "
                       "được. Cài Python 3 (python.org) rồi bấm lại, hoặc "
                       "copy thư mục _lib từ máy đã cài sang."}
    if not _KHOA_CAI.acquire(blocking=False):
        return {"ok": False, "lib": lib, "giay": 0.0,
                "loi": "Đang tải rồi — đợi lượt này xong."}
    t0 = time.time()
    nhat_ky: list[str] = []
    try:
        Path(lib).mkdir(parents=True, exist_ok=True)
        # `--ignore-installed` LÀ CỜ QUYẾT ĐỊNH, ĐỪNG GỠ.
        # Không có nó, pip coi gói đã có trong MÔI TRƯỜNG ĐANG CHẠY là "đã thoả
        # mãn" rồi BỎ QUA, không chép vào `--target`. Trên máy dev `.venv` sẵn
        # có torch + soundfile -> `_lib` chỉ nhận được `demucs` và mấy gói lạ.
        # ĐO ĐƯỢC trên chính `_lib` của anh Hùng (14/08/2026): mọi gói CÓ trong
        # `_lib` (antlr4 · demucs · einops · julius · lameenc · omegaconf) đều là
        # gói KHÔNG có trong `.venv`, còn mọi gói THIẾU (torch · soundfile ·
        # numpy · tqdm...) đều là gói `.venv` ĐÃ CÓ. Một phép chia đôi hoàn hảo
        # — không thể là trùng hợp, và cũng không phải "tải dở giữa chừng" (cả
        # thư mục cùng dấu thời gian 00:55).
        # Cờ này khiến pip giải lại TOÀN BỘ 33 gói vào `_lib` (154 MB) -> `_lib`
        # tự đứng được một mình, đúng cái bản `.exe` cần.
        #
        # `--extra-index-url` (KHÔNG phải `--index-url`): chỉ mục cpu của pytorch
        # không có `demucs`/`soundfile` nên ép cả lượt vào đó là hỏng phép giải.
        # Vẫn ra bản CPU vì `2.13.0+cpu` > `2.13.0` theo PEP 440 (local version)
        # — ĐÃ KIỂM bằng `pip install --dry-run --report`: pip chọn
        # `torch==2.13.0+cpu` lấy từ download.pytorch.org.
        # Bản CUDA có đáng không: ĐO RA LÀ KHÔNG CÓ GÌ ĐỂ ĐÁNH ĐỔI — wheel
        # Windows trên PyPI (122,1 MB) và bản `+cpu` (121,9 MB) LỆCH NHAU 0,2 MB
        # và cả hai đều KHÔNG kéo theo gói `nvidia-*` nào. Muốn dùng RTX 3060
        # phải trỏ hẳn sang chỉ mục `cu###`, đó là việc RIÊNG chứ không phải
        # tự nhiên có bằng cách bỏ cờ này.
        args = [*pip, "install", "--no-input", "--disable-pip-version-check",
                "--upgrade", "--ignore-installed", "--target", lib,
                "--extra-index-url", "https://download.pytorch.org/whl/cpu",
                *GOI_TACH_GIONG]
        prog(0.02, "Đang tải bộ tách giọng (khoảng 2 GB, chạy 1 lần)...")
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", bufsize=1,
                             creationflags=_CREATE_NO_WINDOW)
        _gan_job(p)
        han = time.time() + timeout
        n = 0
        try:
            for dong in p.stdout or ():
                dong = dong.rstrip()
                if not dong:
                    continue
                nhat_ky.append(dong)
                n += 1
                # KHÔNG biết trước tổng dung lượng -> % chỉ là dấu hiệu "đang
                # chạy", trần 0,95 để không khoe xong trước khi xong.
                prog(min(0.95, 0.02 + n / 900.0), dong[-110:])
                if time.time() > han:
                    p.kill()
                    raise subprocess.TimeoutExpired(args[0], timeout)
            ma = p.wait(timeout=120)
        finally:
            _bo_gan_job(p)
        if ma != 0:
            return {"ok": False, "lib": lib, "ma_thoat": ma,
                    "giay": round(time.time() - t0, 2),
                    "loi": "pip trả mã " + str(ma) + ": "
                           + " | ".join(nhat_ky[-4:]),
                    "nhat_ky": nhat_ky[-40:]}
        prog(0.97, "Đang kiểm lại bộ tách giọng...")
        # KIỂM BẰNG ĐƯỜNG DẪN TRONG `_lib`, KHÔNG BẰNG "import được không".
        # Bản cũ hỏi tiến trình riêng "`__import__` có chạy không" — mà tiến
        # trình riêng đó là python của `.venv`, nên nó mượn torch của `.venv`
        # rồi báo CÀI XONG trong khi `_lib` vẫn rỗng torch. Đúng cái bẫy hàm
        # này sinh ra để chặn, nhưng lại tự sập vào.
        # `PathFinder` nhớ nội dung thư mục theo mtime; `_lib` vừa bị pip ghi
        # thêm nên phải xoá bộ nhớ đó, không thì lượt kiểm ngay sau khi cài có
        # thể vẫn thấy `_lib` như lúc chưa cài (báo THIẾU oan).
        import importlib
        importlib.invalidate_caches()
        goi = do_goi_tach_giong(lib)
        thieu = [g for g in GOI_TACH_GIONG if not goi[g]["lib"]]
        kiem = {g: goi[g]["lib"] for g in GOI_TACH_GIONG if goi[g]["lib"]}
        if thieu:
            return {"ok": False, "lib": lib, "ma_thoat": 0, "goi": goi,
                    "giay": round(time.time() - t0, 2), "thieu": thieu,
                    "loi": "pip trả mã 0 nhưng " + ", ".join(thieu)
                           + " VẪN KHÔNG nằm trong _lib (" + lib + "). "
                             "Đừng coi là đã cài — bản .exe sẽ không chạy được.",
                    "kiem": kiem, "nhat_ky": nhat_ky[-40:]}
        prog(1.0, "Đã cài xong bộ tách giọng")
        return {"ok": True, "lib": lib, "ma_thoat": 0, "kiem": kiem,
                "goi": goi, "thieu": [],
                "giay": round(time.time() - t0, 2),
                "nhat_ky": nhat_ky[-40:]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "lib": lib, "giay": round(time.time() - t0, 2),
                "loi": f"{type(e).__name__}: {e}"[:400],
                "nhat_ky": nhat_ky[-40:]}
    finally:
        _KHOA_CAI.release()


#: Mã CHẠY DEMUCS Ở TIẾN TRÌNH RIÊNG. Cố ý là script ĐỘC LẬP (chỉ cần
#: lib + torch + demucs + soundfile) chứ không `-m app.core.thay_giong`:
#: bản `.exe` KHÔNG chạy được `-m <module>` và cũng không có cây mã nguồn,
#: nên chung một đường thế này thì máy dev và máy nhân viên chạy y hệt.
_MA_TACH = '''
import json, os, sys, time
lib, wav_in, out_dir, model_name, threads = sys.argv[1:6]
sys.path.insert(0, lib)
os.environ.setdefault("TORCH_HOME", os.path.join(lib, "_models"))


def bao(p, m):
    sys.stdout.write("BQP\\t%.4f\\t%s\\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model tach giong...")
    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    if int(threads) > 0:
        torch.set_num_threads(int(threads))
    model = get_model(model_name)
    model.eval()
    data, sr = sf.read(wav_in, dtype="float32", always_2d=True)
    if sr != model.samplerate:
        raise RuntimeError("Audio phai o %d Hz (dang %d Hz)"
                           % (model.samplerate, sr))
    wav = torch.from_numpy(data.T).contiguous()
    if wav.shape[0] == 1:
        wav = wav.repeat(2, 1)
    dur = wav.shape[1] / float(sr)
    ref = wav.mean(0)
    std = float(ref.std()) or 1.0
    mean = float(ref.mean())
    w = (wav - mean) / std
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    bao(0.10, "Dang tach nhac/giong (%.0f giay, %s)..." % (dur, dev))
    t0 = time.time()
    with torch.no_grad():
        src = apply_model(model, w[None], device=dev, progress=False,
                          split=True, overlap=0.25)[0]
    giay = time.time() - t0
    src = src * std + mean
    stems = {}
    for i, name in enumerate(model.sources):
        p = os.path.join(out_dir, "stem_%s.wav" % name)
        sf.write(p, src[i].numpy().T, sr)
        stems[name] = p
    idx = {n: i for i, n in enumerate(model.sources)}
    keep = None
    for n in ("drums", "bass", "other"):
        if n in idx:
            keep = src[idx[n]] if keep is None else keep + src[idx[n]]
    p_nhac = os.path.join(out_dir, "lop_nhac.wav")
    sf.write(p_nhac, keep.numpy().T, sr)
    ket = {"ok": True, "nhac": p_nhac, "stems": stems,
           "giay": round(giay, 2), "thiet_bi": dev,
           "do_dai": round(dur, 3), "sr": sr,
           "torch": getattr(torch, "__version__", "?")}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\\t" + json.dumps(ket) + "\\n")
sys.stdout.flush()
'''


def _python_chay_tach() -> list[str]:
    """Python dùng để chạy bước tách. [] = máy không có python nào."""
    if not getattr(sys, "frozen", False):
        return [sys.executable]
    for ten in ("python.exe", "python3.exe"):
        p = shutil.which(ten)
        if p:
            return [p]
    p = shutil.which("py")
    return [p, "-3"] if p else []


def _viet_runner(lib: str) -> Path:
    """Ghi script chạy Demucs ra `<lib>/_bq_tach_runner.py` (ghi đè mỗi lượt)."""
    p = Path(lib) / "_bq_tach_runner.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_MA_TACH, encoding="utf-8")
    return p


def _tach_demucs(wav_44k: str | Path, out_dir: Path, model_name: str,
                 threads: int,
                 on_progress: Optional[Callable[[float, str], None]],
                 timeout: int = 5400,
                 ) -> dict:
    """Tách bằng Demucs (`htdemucs`, Meta, MIT) — chạy ở **TIẾN TRÌNH RIÊNG**.

    **VÌ SAO TIẾN TRÌNH RIÊNG — ĐO ĐƯỢC 14/08, ĐỪNG GỘP LẠI VÀO APP:**
    trong tiến trình đã nạp PyQt6 + `QApplication` thì `import torch` chết với
    `OSError [WinError 1114] Error loading ...torch\\lib\\c10.dll`. Tái hiện
    100%: torch TRƯỚC Qt -> OK · torch SAU Qt -> 1114. App này LÀ app Qt, nên
    bản cũ (nhúng thẳng Demucs vào tiến trình app) là tính năng **KHÔNG BAO
    GIỜ chạy được khi bấm từ giao diện** — mà lỗi lại đội lốt "máy chưa cài
    Demucs", đúng loại bẫy dẫn người ta đi chữa nhầm chỗ.
    Hai cái lợi kèm theo: RAM ~1,3 GB được trả SẠCH khi tiến trình thoát, và
    bấm Huỷ giết được tiến trình (đã `register_job_proc`).
    """
    lib = lib_demucs()
    py = _python_chay_tach()
    if not py:
        raise RuntimeError(
            "Không tìm thấy Python để chạy bộ tách giọng. Cài Python 3 "
            "(python.org) rồi thử lại.")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runner = _viet_runner(lib)

    def prog(p: float, m: str) -> None:
        if on_progress:
            on_progress(max(0.0, min(1.0, p)), m)

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Ngân sách luồng cho torch/OpenMP: không đặt là 1 video ăn hết CPU cả máy
    # và các luồng thay giọng khác đứng im.
    if threads > 0:
        for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                  "OPENBLAS_NUM_THREADS"):
            env.setdefault(v, str(int(threads)))
    args = [*py, str(runner), lib, str(wav_44k), str(out_dir), model_name,
            str(int(threads))]
    t0 = time.time()
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace", bufsize=1,
                         env=env, creationflags=_CREATE_NO_WINDOW)
    _gan_job(p)
    ket: dict = {}
    duoi: list[str] = []
    ma: Optional[int] = None
    han = time.time() + timeout
    try:
        for dong in p.stdout or ():
            dong = dong.rstrip("\n")
            if dong.startswith("BQP\t"):
                phan = dong.split("\t", 2)
                try:
                    prog(float(phan[1]), phan[2] if len(phan) > 2 else "")
                except (ValueError, IndexError):
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
                raise RuntimeError("Tách giọng quá giờ (bỏ cuộc)")
        ma = p.wait(timeout=120)
    finally:
        _bo_gan_job(p)
    if not ket.get("ok"):
        raise RuntimeError(
            "Tách giọng lỗi (mã thoát {}): {}".format(
                "?" if ma is None else ma,
                ket.get("loi") or " | ".join(duoi[-4:]) or "không rõ"))
    p_nhac = ket.get("nhac") or ""
    # KHÔNG tin tiến trình con báo "ok" — ĐO lại file nó ghi ra. Đây là cùng
    # một luật với "ffmpeg trả mã 0 mà file rỗng".
    _kiem_wav(p_nhac)
    dur = float(ket.get("do_dai") or 0)
    giay = float(ket.get("giay") or (time.time() - t0))
    prog(1.0, "Xong tách nhạc/giọng")
    stems = ket.get("stems") or {}
    return {
        "cach": f"demucs:{model_name}",
        "nhac": p_nhac,
        "giong": stems.get(LOP_BO, ""),
        "stems": stems,
        "giay": round(giay, 2),
        "ty_le": round(giay / dur, 3) if dur > 0 else 0.0,
        "thiet_bi": ket.get("thiet_bi") or "cpu",
        "do_dai": round(dur, 3),
        "sr": ket.get("sr") or SR_TACH,
        "giay_ca_tien_trinh": round(time.time() - t0, 2),
        "torch": ket.get("torch", ""),
    }


def _co_the_tru_kenh_giua(wav: str | Path) -> tuple[bool, float]:
    """L và R có KHÁC nhau đủ để trừ kênh giữa không? Trả (được, tương_quan).

    BẪY SỐNG CÒN: file mono-nhân-đôi (L == R) thì (L-R) ra ĐÚNG SỐ 0 -> track
    "nhạc" im lặng tuyệt đối mà ffmpeg vẫn trả mã 0. Phải chặn Ở ĐÂY.
    """
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-i", str(wav),
           "-map", "0:a:0", "-af",
           "pan=mono|c0=0.5*c0-0.5*c1,"
           "astats=measure_overall=RMS_level:measure_perchannel=none",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return (False, 1.0)
    for line in (r.stderr or "").splitlines():
        if "RMS level dB:" in line:
            raw = line.split(":")[-1].strip()
            if raw.lower().lstrip("-") in ("inf", "nan"):
                return (False, 1.0)
            try:
                # -70 dBFS trở xuống coi như im lặng (mono nhân đôi có sai số
                # lượng tử hoá nhỏ, không phải 0 tuyệt đối).
                return (float(raw) > -70.0, 0.0)
            except ValueError:
                return (False, 1.0)
    return (False, 1.0)


def _tach_nhe(wav_44k: str | Path, out_dir: Path,
              on_progress: Optional[Callable[[float, str], None]],
              ) -> dict:
    """ĐƯỜNG LUI cho máy KHÔNG có torch: trừ kênh giữa + cộng lại trầm/cao.

    Nguyên lý: lời thoại gần như luôn nằm CHÍNH GIỮA (L ≈ R) nên (L-R) triệt
    giọng. Nhưng trầm (bass/trống) và phần lớn nhạc cũng ở giữa -> trừ trơn là
    mất nhạc luôn (ĐÃ ĐO: tín hiệu cạnh chỉ còn -17,4 dB). Nên:
      lớp nhạc = (L-R) [toàn dải]  +  giữa[< 220 Hz]  +  giữa[> 7 kHz]
    Giọng người tập trung 220 Hz - 7 kHz nên hai phần cộng lại kéo về rất ít
    giọng, mà cứu được bass và chũm chọe.

    KHÔNG có lớp "giọng" sạch -> chép lời phải dùng audio GỐC (kém hơn Demucs).
    """
    def prog(p: float, m: str) -> None:
        if on_progress:
            on_progress(max(0.0, min(1.0, p)), m)

    prog(0.05, "Kiểm tra kênh trái/phải...")
    duoc, _ = _co_the_tru_kenh_giua(wav_44k)
    if not duoc:
        raise RuntimeError(
            "Audio là MONO nhân đôi (kênh trái = kênh phải) nên không thể trừ "
            "kênh giữa — trừ ra sẽ IM LẶNG HẲN. Video này bắt buộc phải dùng "
            "Demucs.")

    dur = probe_duration(wav_44k)
    p_nhac = out_dir / "lop_nhac.wav"
    prog(0.25, f"Đang tách nhẹ bằng ffmpeg ({dur:.0f} giây)...")
    t0 = time.time()
    fc = (
        # 3 nhánh từ cùng nguồn
        "[0:a]asplit=3[a][b][c];"
        # (1) tín hiệu CẠNH: giọng ở giữa bị triệt
        "[a]pan=stereo|c0=c0-c1|c1=c1-c0[side];"
        # (2) GIỮA phần TRẦM: cứu bass/trống
        f"[b]pan=mono|c0=0.5*c0+0.5*c1,lowpass=f={_TRAM_HZ},"
        "pan=stereo|FL<c0|FR<c0[low];"
        # (3) GIỮA phần CAO: cứu chũm chọe / tiếng động sắc
        f"[c]pan=mono|c0=0.5*c0+0.5*c1,highpass=f={_CAO_HZ},"
        "pan=stereo|FL<c0|FR<c0[high];"
        # cộng lại, normalize=0 để KHÔNG bị chia biên độ
        "[side][low][high]amix=inputs=3:duration=longest:normalize=0[out]"
    )
    _ffmpeg(["-i", str(wav_44k), "-filter_complex", fc, "-map", "[out]",
             "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
             str(p_nhac)], "tách nhẹ nhạc/giọng bằng ffmpeg")
    giay = time.time() - t0
    _kiem_wav(p_nhac)
    prog(1.0, "Xong tách nhẹ")
    return {
        "cach": "nhe:tru-kenh-giua",
        "nhac": str(p_nhac),
        # KHÔNG có lớp giọng sạch — cố ý để rỗng để bước chép lời biết mà dùng
        # audio gốc, thay vì âm thầm chép lời trên file không tồn tại.
        "giong": "",
        "stems": {},
        "giay": round(giay, 2),
        "ty_le": round(giay / dur, 3) if dur > 0 else 0.0,
        "thiet_bi": "cpu",
        "do_dai": round(dur, 3),
        "sr": SR_TACH,
    }


#: Lời báo khi máy KHÔNG có Demucs. ĐO ĐƯỢC: đường lui `nhe` để lọt 86-100%
#: số từ của lời gốc sang track "nhạc" -> video ra vẫn nghe rõ giọng cũ chồng
#: lên giọng mới. Đó là VIDEO HỎNG, không phải "chất lượng thấp hơn một chút".
THIEU_DEMUCS = (
    "Máy này CHƯA cài Demucs/torch nên KHÔNG tách được giọng khỏi nhạc nền.\n"
    "Đã đo trên video thật: cách nhẹ (trừ kênh giữa) để sót 86-100% lời gốc "
    "trong track nhạc — video ra sẽ nghe thấy CẢ giọng cũ lẫn giọng mới.\n"
    "Hãy cài Demucs (xem `lib_demucs()`) rồi chạy lại, hoặc gọi với "
    "cach='nhe' nếu CỐ Ý chấp nhận chất lượng đó."
)


def tach_giong(wav_44k: str | Path, out_dir: str | Path,
               cach: str = "auto", model_name: str = "htdemucs",
               threads: int = 0, cho_phep_nhe: bool = False,
               on_progress: Optional[Callable[[float, str], None]] = None,
               ) -> dict:
    """Tách `wav_44k` (stereo 44,1 kHz) thành lớp NHẠC (giữ) + lớp GIỌNG (bỏ).

    `cach`: "demucs" (ép Demucs, thiếu lib -> lỗi) | "nhe" (ép ffmpeg) |
            "auto" (có Demucs thì Demucs, KHÔNG có thì **BÁO LỖI**).

    VÌ SAO "auto" KHÔNG TỰ LUI NỮA: đường lui `nhe` KHÔNG xoá được giọng (đo:
    rò 86-100% số từ). Tự lui = âm thầm xuất ra video hỏng HÀNG LOẠT, đúng loại
    bẫy "ffmpeg trả mã 0 mà file sai" mà cả repo này đang chống. Muốn lui thì
    phải NÓI RA: `cho_phep_nhe=True` hoặc `cach="nhe"`.

    Trả dict: nhac / giong / stems / giay / ty_le / thiet_bi / do_dai / sr / cach
    (`giong` = "" nghĩa là cách này KHÔNG cho lớp giọng sạch).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cach = (cach or "auto").lower().strip()

    if cach == "nhe":
        ket = _tach_nhe(wav_44k, out_dir, on_progress)
        ket["canh_bao"] = "cách nhẹ: giọng gốc CÒN SÓT nhiều, chỉ dùng để thử"
        return ket
    if cach == "demucs":
        return _tach_demucs(wav_44k, out_dir, model_name, threads, on_progress)

    # auto
    if co_demucs():
        try:
            return _tach_demucs(wav_44k, out_dir, model_name, threads,
                                on_progress)
        except Exception as e:  # noqa: BLE001
            # Demucs hỏng giữa đường (model tải lỗi, hết RAM...).
            if not cho_phep_nhe:
                raise RuntimeError(f"{THIEU_DEMUCS}\n(lý do: {e})") from e
            ket = _tach_nhe(wav_44k, out_dir, on_progress)
            ket["lui_vi"] = str(e)[:300]
            return ket
    if not cho_phep_nhe:
        raise RuntimeError(THIEU_DEMUCS)
    ket = _tach_nhe(wav_44k, out_dir, on_progress)
    ket["lui_vi"] = "máy không có Demucs/torch"
    return ket


# ==================================================================
# ĐO CHẤT LƯỢNG TÁCH — số, không phải cảm nhận
# ==================================================================

def do_chat_luong_tach(goc_wav: str | Path, nhac_wav: str | Path,
                       khoang_noi: list[tuple[float, float]],
                       khoang_im: list[tuple[float, float]]) -> dict:
    """Chấm chất lượng tách bằng SỐ, trên chính video thật.

    `khoang_noi` / `khoang_im`: các đoạn ĐANG NÓI / KHÔNG nói (lấy từ mốc từ của
    bước chép lời). Trả:
      giam_giong_db  — mức giọng bị giảm bao nhiêu dB ở đoạn ĐANG NÓI (càng
                       lớn càng sạch). Đo RMS đoạn nói của bản gốc so bản nhạc.
      giu_nhac_db    — mức nhạc bị mất bao nhiêu dB ở đoạn KHÔNG nói (càng gần
                       0 càng tốt; âm nhiều = mất nhạc).
      loi_the_db     — giam_giong_db - |giu_nhac_db|. Đây là con số DUY NHẤT
                       đáng tin: tách sạch mà mất luôn nhạc thì vô nghĩa.
      nhac_rms       — RMS lớp nhạc toàn bài. 0.0 = TRACK IM LẶNG (tách hỏng).
    """
    import math

    def rms_tap(path, khoang) -> float:
        vals = [do_rms(path, a, max(0.05, b - a)) for a, b in khoang]
        vals = [v for v in vals if v > 0]
        if not vals:
            return 0.0
        # cộng năng lượng rồi lấy căn (RMS gộp), KHÔNG lấy trung bình dB
        return math.sqrt(sum(v * v for v in vals) / len(vals))

    def db(a: float, b: float) -> Optional[float]:
        if a <= 0 or b <= 0:
            return None
        return round(20.0 * math.log10(b / a), 2)

    g_noi = rms_tap(goc_wav, khoang_noi)
    n_noi = rms_tap(nhac_wav, khoang_noi)
    g_im = rms_tap(goc_wav, khoang_im)
    n_im = rms_tap(nhac_wav, khoang_im)

    giam = db(n_noi, g_noi)         # gốc / nhạc  -> dương = giọng bị giảm
    giu = db(g_im, n_im)            # nhạc / gốc  -> 0 = giữ nguyên nhạc
    loi_the = None
    if giam is not None and giu is not None:
        loi_the = round(giam - abs(giu), 2)
    return {
        "giam_giong_db": giam,
        "giu_nhac_db": giu,
        "loi_the_db": loi_the,
        "nhac_rms": round(do_rms(nhac_wav), 6),
        "goc_rms": round(do_rms(goc_wav), 6),
        "rms_noi_goc": round(g_noi, 6), "rms_noi_nhac": round(n_noi, 6),
        "rms_im_goc": round(g_im, 6), "rms_im_nhac": round(n_im, 6),
        "so_khoang_noi": len(khoang_noi), "so_khoang_im": len(khoang_im),
    }


def khoang_noi_im(words: list, tong: float,
                  dem: float = 0.10, im_toi_thieu: float = 0.60,
                  toi_da: int = 25) -> tuple[list, list]:
    """Từ mốc TỪNG TỪ -> (các đoạn ĐANG NÓI, các đoạn KHÔNG nói).

    Dùng cho `do_chat_luong_tach`. Gộp các từ liền nhau thành đoạn nói; khoảng
    trống >= `im_toi_thieu` giây là đoạn im. Cắt bớt `dem` giây hai đầu đoạn im
    để không liếm sang tiếng nói.
    """
    ws = sorted([(float(w["start"]), float(w["end"])) for w in (words or [])
                 if float(w.get("end", 0)) > float(w.get("start", 0))])
    if not ws:
        return ([], [])
    noi: list[list[float]] = []
    for a, b in ws:
        if noi and a - noi[-1][1] < 0.25:
            noi[-1][1] = max(noi[-1][1], b)
        else:
            noi.append([a, b])
    im: list[tuple[float, float]] = []
    truoc = 0.0
    for a, b in noi:
        if a - truoc >= im_toi_thieu:
            im.append((truoc + dem, a - dem))
        truoc = b
    if tong - truoc >= im_toi_thieu:
        im.append((truoc + dem, tong - dem))
    noi_t = [(a, b) for a, b in noi if b - a >= 0.30][:toi_da]
    im_t = [(a, b) for a, b in im if b - a >= 0.30][:toi_da]
    return (noi_t, im_t)


# ==================================================================
# BƯỚC 2 — CHÉP LỜI GỐC (mốc từng từ)
# ==================================================================

def chep_loi(audio: str | Path, lop_giong: str = "",
             on_progress: Optional[Callable[[float, str], None]] = None,
             ) -> dict:
    """Chép lời + mốc TỪNG TỪ bằng `transcribe.py` (Groq whisper-large-v3).

    `lop_giong` = lớp GIỌNG đã tách (stem vocals). Có thì chép trên đó vì nền
    nhạc đã bị bỏ -> whisper ít nhầm hơn; KHÔNG có (cách nhẹ) thì chép trên
    audio gốc và ghi rõ trong kết quả để không tưởng là cùng chất lượng.
    """
    from app.core import transcribe as tr

    nguon = str(lop_giong) if lop_giong and Path(lop_giong).exists() else str(audio)
    if on_progress:
        on_progress(0.05, "Đang chép lời gốc...")
    t0 = time.time()
    d = tr.transcribe(nguon)
    d["_giay_chep"] = round(time.time() - t0, 2)
    d["_nguon"] = "lop_giong" if nguon != str(audio) else "audio_goc"
    if on_progress:
        on_progress(1.0, f"Chép xong {len(d.get('words') or [])} từ")
    return d


def cau_tu_transcript(d: dict, gop_toi_da: float = 12.0) -> list[dict]:
    """Đổi transcript -> danh sách CÂU {start, end, text} để dịch và đọc.

    Ưu tiên `segments` của whisper; segment quá dài (> `gop_toi_da` giây) thì
    cắt theo mốc TỪ để mỗi câu còn khớp thời gian được.
    """
    segs = d.get("segments") or []
    words = d.get("words") or []
    out: list[dict] = []
    for s in segs:
        a = float(s.get("start", 0) or 0)
        b = float(s.get("end", 0) or 0)
        t = (s.get("text") or "").strip()
        if b <= a or not t:
            continue
        if b - a <= gop_toi_da or not words:
            out.append({"start": round(a, 3), "end": round(b, 3), "text": t})
            continue
        # cắt segment dài theo mốc TỪ
        ws = [w for w in words
              if float(w.get("start", 0)) >= a - 0.01
              and float(w.get("end", 0)) <= b + 0.01]
        if not ws:
            out.append({"start": round(a, 3), "end": round(b, 3), "text": t})
            continue
        cum: list = []
        for w in ws:
            # CẮT TRƯỚC KHI VƯỢT, không phải sau: gộp rồi mới kiểm thì câu luôn
            # dài quá `gop_toi_da` đúng một từ (đo: đặt 12s ra câu 14,5s).
            if cum and float(w["end"]) - float(cum[0]["start"]) > gop_toi_da:
                out.append({
                    "start": round(float(cum[0]["start"]), 3),
                    "end": round(float(cum[-1]["end"]), 3),
                    "text": "".join(str(x.get("word", "")) for x in cum).strip(),
                })
                cum = []
            cum.append(w)
        if cum:
            out.append({
                "start": round(float(cum[0]["start"]), 3),
                "end": round(float(cum[-1]["end"]), 3),
                "text": "".join(str(x.get("word", "")) for x in cum).strip(),
            })
    return [c for c in out if c["text"].strip()]


# ==================================================================
# BƯỚC 3 — DỊCH + HẬU KIỂM BẰNG DỊCH NGƯỢC
# ==================================================================

#: Câu có điểm giống nghĩa DƯỚI mức này thì dịch lại. Thang 0-10, CÀNG CAO
#: CÀNG GIỐNG (bài học cổng 49: phải nói rõ CHIỀU của thang cho LLM).
NGUONG_GIONG_NGHIA = 7.0

_TEN_NN = {
    "en": "tiếng Anh", "vi": "tiếng Việt", "zh": "tiếng Trung",
    "ja": "tiếng Nhật", "ko": "tiếng Hàn", "de": "tiếng Đức",
    "fr": "tiếng Pháp", "es": "tiếng Tây Ban Nha", "th": "tiếng Thái",
    "pt": "tiếng Bồ Đào Nha", "id": "tiếng Indonesia", "ru": "tiếng Nga",
    "it": "tiếng Ý", "ar": "tiếng Ả Rập", "hi": "tiếng Hindi",
}

#: Groq trả NHÃN CHỮ ("Chinese"), KHÔNG phải mã ISO — bẫy đã ghi ở CLAUDE.md
#: (cổng 52). `thay_giong_video` còn cắt `[:2]` nữa nên nhãn tới đây là "ch",
#: tra bảng trượt, và prompt dịch ra câu *"Dịch các câu thoại sau từ ch sang
#: tiếng Anh"* — model phải TỰ ĐOÁN tiếng nguồn. Bảng này bắt CẢ HAI dạng.
_NHAN_NN = {
    "chinese": "zh", "ch": "zh", "mandarin": "zh", "cmn": "zh",
    "english": "en", "vietnamese": "vi", "japanese": "ja", "korean": "ko",
    "german": "de", "french": "fr", "spanish": "es", "thai": "th",
    "portuguese": "pt", "indonesian": "id", "russian": "ru",
    "italian": "it", "arabic": "ar", "hindi": "hi",
}


def ma_ngon_ngu(ma: str) -> str:
    """Chuẩn hoá nhãn ngôn ngữ -> mã ISO 2 ký tự. Không nhận ra -> trả nguyên."""
    s = (ma or "").strip().lower().replace("_", "-")
    if s in _NHAN_NN:
        return _NHAN_NN[s]
    goc = s.split("-")[0]
    if goc in _TEN_NN:
        return goc
    return _NHAN_NN.get(goc, goc)


def _ten_nn(ma: str) -> str:
    return _TEN_NN.get(ma_ngon_ngu(ma), ma or "tiếng Anh")


#: Số vòng ĐÒI LẠI phần LLM trả thiếu. Đo `_do_nhan_dich.py`: mảng CÓ NHÃN trả
#: đủ 37/37 ngay VÒNG 1 ở cả 3 lượt — vòng 2-3 chỉ là lưới an toàn.
VONG_DOI_LAI = 3


def _mang_llm(data) -> list:
    """Bóc mảng ra khỏi kiểu LLM hay trả ({"ket_qua": [...]} hoặc [...])."""
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return data if isinstance(data, list) else []


def _theo_nhan(data, chi_so: list[int], khoa: str) -> dict[int, object]:
    """Map kết quả LLM về ĐÚNG câu bằng NHÃN `#i`, không bằng VỊ TRÍ.

    **VÌ SAO TỒN TẠI — LỖI ANH HÙNG BÁO 14/08/2026** (*"vẫn không khớp"* +
    *"giọng nói không chuẩn"*): mọi hàm LLM ở đây từng đọc kết quả bằng
    `data[i]`, trong khi prompt đã đánh số `#0 #1 #2 …` rồi VỨT NHÃN ĐI. Đo
    thật (`_do_lech_dich.py`, Groq thật, 37 câu tiếng Trung, 3 lượt): LLM trả
    về **29 · 33 · 34** phần tử — LUÔN THIẾU. Hậu quả kép:
      · câu rơi ra ngoài mảng -> nhánh lùi `c["text"]` = **giữ nguyên tiếng
        Trung** rồi đưa cho giọng en-US đọc (= "nói không chuẩn");
      · LLM gộp 2 câu ở giữa -> **mọi câu phía sau lệch bậc**, giọng đọc lời
        của đoạn khác (= "không khớp").
    Cả hai VÔ HÌNH với thước v2.27.0 vì thước đó chỉ đo ĐỘ DÀI (tempo, chồng
    lấn, lệch mốc), không ai hỏi "câu này có đúng LỜI của đoạn này không".

    `chi_so` = danh sách nhãn THẬT đã gửi đi (bản gọi lại chỉ gửi phần thiếu,
    nhãn vẫn là nhãn GỐC). Trả {nhãn: giá trị} — thiếu thì KHÔNG có khoá, để
    caller tự biết mà đòi lại chứ không im lặng lấp bằng câu gốc.

    CHẤP NHẬN CẢ HAI KIỂU TRẢ VỀ: model ngoan thì ra `{"i":…, "<khoa>":…}`;
    model trả mảng thuần thì lùi về đọc theo VỊ TRÍ **trong đúng `chi_so`**
    (không phải theo 0..n-1) — bản lùi này vẫn đúng khi mảng đủ.
    """
    xs = _mang_llm(data)
    ra: dict[int, object] = {}
    co_nhan = False
    for o in xs:
        if not isinstance(o, dict):
            continue
        gt = o.get(khoa, o.get("t", o.get("text")))
        try:
            i = int(o.get("i"))
        except (TypeError, ValueError):
            continue
        if i in chi_so and gt is not None and i not in ra:
            ra[i] = gt
            co_nhan = True
    if co_nhan:
        return ra
    # lùi: mảng thuần -> ghép theo thứ tự đã gửi
    for j, i in enumerate(chi_so):
        if j < len(xs) and not isinstance(xs[j], dict):
            ra[i] = xs[j]
    return ra


def _dich_loat(cau: list[dict], dich_sang: str, goc_ma: str) -> list[str]:
    """Dịch cả loạt câu trong 1 lượt LLM. Trả list cùng số phần tử."""
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    system = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. Dịch tự nhiên như "
              "VĂN NÓI, đúng ý, đúng cảm xúc. CHỈ trả JSON thuần.")

    ra: dict[int, str] = {}
    con: list[int] = list(range(len(cau)))
    loi_dau: Optional[Exception] = None
    for vong in range(VONG_DOI_LAI):
        if not con:
            break
        items = []
        for i in con:
            c = cau[i]
            dur = max(0.1, float(c["end"]) - float(c["start"]))
            items.append(f'#{i} [{dur:.1f} giây]: "{c["text"][:400]}"')
        prompt = (
            f"Dịch các câu thoại sau từ {_ten_nn(goc_ma)} sang {ten_dich}.\n"
            f"{chr(10).join(items)}\n\n"
            "QUY TẮC:\n"
            f"- Dịch sang {ten_dich}, văn NÓI tự nhiên.\n"
            "- ĐỌC LÊN phải lọt khung [số giây] của câu đó — dài quá thì lược "
            "từ đệm, GIỮ Ý CHÍNH.\n"
            "- KHÔNG thêm chú thích, không phiên âm.\n"
            f"- Trả MẢNG JSON {len(con)} đối tượng "
            '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
            "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào, KHÔNG gộp hai câu."
        )
        try:
            data = llm.complete_json(prompt, system=system)
        except Exception as e:      # noqa: BLE001
            # Hết lượt / mạng chết ở vòng ĐÒI LẠI không được xoá phần đã dịch
            # được ở vòng trước — thà thiếu vài câu còn hơn mất cả loạt.
            loi_dau = loi_dau or e
            break
        for i, t in _theo_nhan(data, con, "t").items():
            if isinstance(t, str) and t.strip():
                ra[i] = t.strip()
        con = [i for i in range(len(cau)) if i not in ra]
    if not ra and loi_dau is not None:
        raise loi_dau
    if not ra:
        raise llm.LLMError("LLM không trả mảng bản dịch.")
    # Câu vẫn không đòi được -> đành giữ câu GỐC (nhánh này là chỗ tiếng Trung
    # lọt sang giọng tiếng Anh; nay nó chỉ còn là lưới cuối, không phải đường
    # đi thường xuyên như trước — đo: 4,0 câu/lượt -> 0,0).
    return [ra.get(i) or c["text"] for i, c in enumerate(cau)]


def _dich_nguoc_cham(goc: list[str], dich: list[str], goc_ma: str,
                     dich_ma: str) -> list[float]:
    """DỊCH NGƯỢC bản dịch về tiếng gốc rồi CHẤM độ giống nghĩa.

    Trả list điểm 0-10 (CÀNG CAO CÀNG GIỐNG). Lỗi -> trả 10.0 hết (fail-safe:
    không có căn cứ thì ĐỪNG dịch lại bừa, giữ nguyên bản dịch đầu).
    """
    from app.ai import llm

    items = []
    for i, (g, d) in enumerate(zip(goc, dich)):
        items.append(f'#{i}\n  GỐC ({_ten_nn(goc_ma)}): "{g[:300]}"\n'
                     f'  BẢN DỊCH ({_ten_nn(dich_ma)}): "{d[:300]}"')
    system = ("Bạn là người soát bản dịch. Hãy DỊCH NGƯỢC bản dịch về tiếng "
              "gốc trong đầu, rồi so nghĩa với câu gốc. CHỈ trả JSON thuần.")
    prompt = (
        "Với mỗi cặp dưới đây, chấm ĐỘ GIỐNG NGHĨA giữa BẢN DỊCH và câu GỐC.\n"
        f"{chr(10).join(items)}\n\n"
        "THANG ĐIỂM 0-10, CÀNG CAO CÀNG GIỐNG NGHĨA:\n"
        "- 10 = giống hệt nghĩa, không sót ý, không thêm ý.\n"
        "- 7  = sát nghĩa, chỉ khác cách diễn đạt.\n"
        "- 4  = lệch một phần ý, hoặc sót ý quan trọng.\n"
        "- 0  = SAI nghĩa hẳn, hoặc dịch thiếu gần hết.\n"
        f"Trả MẢNG JSON {len(goc)} đối tượng "
        '{"i": <đúng số sau dấu #>, "d": <điểm 0-10>}. '
        "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào."
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001
        return [10.0] * len(goc)
    # Lấy theo NHÃN: điểm rơi nhầm câu thì vòng "dịch lại câu lệch nghĩa" đi
    # dịch lại ĐÚNG NHỮNG CÂU KHÔNG CẦN, còn câu hỏng thật thì bỏ sót.
    bang = _theo_nhan(data, list(range(len(goc))), "d")
    if not bang:
        return [10.0] * len(goc)
    out = []
    for i in range(len(goc)):
        try:
            out.append(float(bang[i]))          # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError):
            out.append(10.0)                    # không chấm được -> ĐỪNG nghi oan
    return out


def dich_hau_kiem(cau: list[dict], dich_sang: str, goc_ma: str = "",
                  nguong: float = NGUONG_GIONG_NGHIA, vong_toi_da: int = 1,
                  on_progress: Optional[Callable[[float, str], None]] = None,
                  ) -> dict:
    """Dịch `cau` sang `dich_sang`, HẬU KIỂM bằng dịch ngược, câu lệch dịch lại.

    KHÔNG hứa "chuẩn 100%" — trả về TỈ LỆ câu phải dịch lại và điểm từng câu
    để biết bản dịch đáng tin tới đâu.

    Trả {ban_dich, diem, phai_dich_lai, ty_le_dich_lai, diem_tb, diem_min}.
    """
    if not cau:
        return {"ban_dich": [], "diem": [], "phai_dich_lai": 0,
                "ty_le_dich_lai": 0.0, "diem_tb": 0.0, "diem_min": 0.0}

    if on_progress:
        on_progress(0.10, f"Đang dịch {len(cau)} câu...")
    goc_txt = [c["text"] for c in cau]
    ban_dich = _dich_loat(cau, dich_sang, goc_ma)

    if on_progress:
        on_progress(0.50, "Đang dịch ngược để hậu kiểm...")
    diem = _dich_nguoc_cham(goc_txt, ban_dich, goc_ma, dich_sang)

    tong_lam_lai = 0
    for _ in range(max(0, vong_toi_da)):
        xau = [i for i, d in enumerate(diem) if d < nguong]
        if not xau:
            break
        if on_progress:
            on_progress(0.75, f"Dịch lại {len(xau)} câu lệch nghĩa...")
        con = [cau[i] for i in xau]
        try:
            lai = _dich_loat(con, dich_sang, goc_ma)
        except Exception:  # noqa: BLE001
            break
        diem_lai = _dich_nguoc_cham([goc_txt[i] for i in xau], lai,
                                    goc_ma, dich_sang)
        for j, i in enumerate(xau):
            # chỉ NHẬN bản mới khi nó thật sự khá hơn (không tụt lùi)
            if diem_lai[j] > diem[i]:
                ban_dich[i] = lai[j]
                diem[i] = diem_lai[j]
        tong_lam_lai += len(xau)

    con_xau = sum(1 for d in diem if d < nguong)
    if on_progress:
        on_progress(1.0, "Dịch xong")
    return {
        "ban_dich": ban_dich,
        "diem": [round(float(d), 2) for d in diem],
        "phai_dich_lai": tong_lam_lai,
        "ty_le_dich_lai": round(100.0 * tong_lam_lai / max(1, len(cau)), 1),
        "con_duoi_nguong": con_xau,
        "ty_le_con_xau": round(100.0 * con_xau / max(1, len(cau)), 1),
        "diem_tb": round(sum(diem) / max(1, len(diem)), 2),
        "diem_min": round(min(diem), 2) if diem else 0.0,
        "nguong": nguong,
    }


# ==================================================================
# BƯỚC 4 — ĐỌC BẢN DỊCH (TTS)
# ==================================================================

def giong_theo_ngon_ngu(ma: str) -> str:
    """Giọng edge-tts mặc định khớp ngôn ngữ đích (tái dùng `dubbing.py`)."""
    from app.core import dubbing
    return dubbing.default_voice(dubbing.norm_lang(ma))


def doc_ban_dich(texts: list[str], out_dir: str | Path, voice: str = "",
                 dich_sang: str = "en",
                 on_progress: Optional[Callable[[float, str], None]] = None,
                 ) -> dict:
    """Đọc từng câu bản dịch ra mp3 bằng edge-tts (tái dùng `dubbing._synth_all`).

    Trả {files, ok, voice, giay}. `ok[i]=False` = câu đó TTS hỏng -> caller BỎ
    RIÊNG câu đó, các câu khác giữ đúng mốc (không dồn/lệch cả track).
    """
    import asyncio
    from app.core import dubbing

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice = voice or giong_theo_ngon_ngu(dich_sang)
    paths = [str(out_dir / f"cau_{i:04d}.mp3") for i in range(len(texts))]

    xong = {"n": 0}

    def _done(_i: int) -> None:
        xong["n"] += 1
        if on_progress:
            on_progress(xong["n"] / max(1, len(texts)),
                        f"Đang đọc câu {xong['n']}/{len(texts)}...")

    t0 = time.time()
    ok = asyncio.run(dubbing._synth_all(texts, voice, paths, on_done=_done))
    # CẮT LỀ IM NGAY TẠI ĐÂY, trước khi bất kỳ ai đo độ dài câu: mọi bước sau
    # (rút gọn, khớp thời gian) phải nhìn thấy ĐỘ DÀI TIẾNG THẬT, không phải
    # độ dài file có kèm ~1,07 s im lặng của edge-tts.
    if on_progress:
        on_progress(0.95, "Cắt lề im lặng đầu/cuối câu...")
    sach, le = cat_le_loat(paths, list(ok), out_dir / "sach")
    return {
        "files": sach, "files_tho": paths, "ok": list(ok), "voice": voice,
        "giay": round(time.time() - t0, 2),
        "so_hong": sum(1 for x in ok if not x),
        "cat_le": le,
    }


# ==================================================================
# BƯỚC 4a — CẮT LỀ IM LẶNG edge-tts CHÈN VÀO MỖI CÂU
# ==================================================================
#
# ĐÂY LÀ GỐC RỄ CỦA "NÓI KHÔNG MƯỢT" — đo được, không phải phòng xa.
# `_do_le_im.py` đo bằng `silencedetect` trên chính file edge-tts trả về:
# mỗi câu bị chèn **~0,20 giây im ở ĐẦU và ~0,87 giây im ở CUỐI**, bất kể câu
# dài hay ngắn. Câu dịch 12 ký tự: file 1,848 s nhưng TIẾNG THẬT chỉ 0,762 s
# — **58% file là im lặng**.
#
# App cũ đo độ dài câu bằng `probe_duration` (tức TÍNH CẢ LỀ IM) rồi ép
# `atempo` cho lọt khung -> **ép méo tiếng nói thật chỉ để nén khoảng im**.
# Đo trên video Douyin 90 giây: 23-32% số câu chạm TRẦN 1,5 ở cả 3 lượt.
#
# Cắt lề rồi thì phần lớn câu lọt khung ở tempo 1,0 — không méo gì cả.
# GIỮ LẠI một chút hai đầu (`GIU_DAU`/`GIU_CUOI`) để câu không nghe như bị
# chặt cụt; khoảng nghỉ giữa các câu đã có sẵn trên TIMELINE GỐC (mỗi câu đặt
# đúng mốc `start` của người nói gốc), không cần edge-tts nghỉ hộ.

#: Ngưỡng coi là im lặng. -45 dBFS: dưới mức này edge-tts không phát gì (đo
#: được lề im ổn định 0,18-0,21 s đầu · 0,82-1,31 s cuối trên 12 câu thử).
NGUONG_IM_DB = -45.0

#: Chừa lại hai đầu (giây) — cắt sát 0 thì phụ âm đầu/đuôi bị gọt, nghe cụt.
GIU_DAU = 0.04
GIU_CUOI = 0.08


def do_le_im(path: str | Path, nguong_db: float = NGUONG_IM_DB,
             ) -> tuple[float, float, float]:
    """(im ĐẦU, im CUỐI, tổng) giây — đo bằng `silencedetect` THẬT.

    Chỉ tính khoảng im DÍNH MÉP file; khoảng nghỉ giữa câu thì KHÔNG đụng.
    Lỗi/không đo được -> (0, 0, tổng) = coi như không có lề (fail-safe: thà
    không cắt còn hơn cắt nhầm vào tiếng nói).
    """
    tong = probe_duration(path)
    if tong <= 0:
        return (0.0, 0.0, 0.0)
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-i", str(path),
           "-af", f"silencedetect=n={nguong_db}dB:d=0.03", "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return (0.0, 0.0, tong)
    khoang: list[tuple[float, float]] = []
    st: Optional[float] = None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", r.stderr or ""):
        if m.group(1) == "start":
            st = float(m.group(2))
        elif st is not None:
            khoang.append((st, float(m.group(2))))
            st = None
    if st is not None:
        khoang.append((st, tong))
    dau = khoang[0][1] if khoang and khoang[0][0] <= 0.02 else 0.0
    cuoi = (tong - khoang[-1][0]) if khoang and khoang[-1][1] >= tong - 0.02 \
        else 0.0
    return (max(0.0, dau), max(0.0, cuoi), tong)


def cat_le_im(src: str | Path, dst: str | Path,
              nguong_db: float = NGUONG_IM_DB) -> float:
    """Cắt lề im lặng hai đầu file TTS -> wav. Trả độ dài THẬT sau khi cắt.

    KHÔNG BAO GIỜ trả file rỗng: đo hỏng, hoặc cắt xong còn dưới 0,08 giây
    (câu chỉ có tiếng thở / TTS hỏng) -> giữ NGUYÊN bản gốc. Độ dài trả về
    luôn là số ĐO LẠI trên file đã ghi, không phải số dự kiến (bẫy "ffmpeg mã
    0 nhưng file rỗng").
    """
    src, dst = Path(src), Path(dst)
    dau, cuoi, tong = do_le_im(src, nguong_db)
    a = max(0.0, dau - GIU_DAU)
    b = max(a + 0.01, tong - max(0.0, cuoi - GIU_CUOI))
    af = ["aresample=44100"]
    if tong > 0 and (a > 0.005 or b < tong - 0.005) and (b - a) >= 0.08:
        af.append(f"atrim=start={a:.3f}:end={b:.3f}")
        af.append("asetpts=N/SR/TB")
    _ffmpeg(["-i", str(src), "-af", ",".join(af), "-ac", "1", "-ar", "44100",
             "-c:a", "pcm_s16le", str(dst)], f"cắt lề im {src.name}")
    d = probe_duration(dst)
    if d < 0.05:                       # cắt hụt -> quay về bản chưa cắt
        _ffmpeg(["-i", str(src), "-af", "aresample=44100", "-ac", "1",
                 "-ar", "44100", "-c:a", "pcm_s16le", str(dst)],
                f"giữ nguyên {src.name}")
        d = probe_duration(dst)
    return d


def cat_le_loat(files: list[str], ok: list[bool], out_dir: str | Path,
                tien_to: str = "sach") -> tuple[list[str], dict]:
    """Cắt lề cho cả loạt câu. Trả (files_mới, số đo).

    Câu TTS hỏng (`ok[i]` False) giữ nguyên đường dẫn cũ — caller vẫn bỏ nó
    theo `ok`, không được để lệch chỉ số.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ra = list(files)
    cat_tong = 0.0
    truoc_tong = 0.0
    sau_tong = 0.0
    n = 0
    for i, f in enumerate(files):
        if i >= len(ok) or not ok[i] or not f or not Path(f).exists():
            continue
        d0 = probe_duration(f)
        dst = out_dir / f"{tien_to}_{i:04d}.wav"
        d1 = cat_le_im(f, dst)
        ra[i] = str(dst)
        truoc_tong += d0
        sau_tong += d1
        cat_tong += max(0.0, d0 - d1)
        n += 1
    return ra, {
        "so_cau": n,
        "giay_cat_tong": round(cat_tong, 2),
        "giay_cat_tb": round(cat_tong / max(1, n), 3),
        "giay_truoc": round(truoc_tong, 2),
        "giay_sau": round(sau_tong, 2),
    }


# ==================================================================
# HẰNG SỐ KHỚP THỜI GIAN (bước 4b và bước 5 dùng chung)
# ==================================================================

#: Trên mức này nghe đã MÉO -> chữa bằng cách rút NGẮN câu dịch / mượn thời
#: gian đoạn kế, chứ đừng ép nhanh.
TEMPO_CANH_BAO = 1.30

#: Trần tuyệt đối: rút gọn + mượn hết rồi vẫn tràn thì đành ép tới đây.
TEMPO_TOI_DA = 1.50

#: NGƯỠNG GỌI TỚI BƯỚC RÚT GỌN — **KHÔNG phải `TEMPO_CANH_BAO`**.
#: Từ khi có bước 4c (`doc_nhanh_vua_khung`), phần dôi ra tới ~1,45 lần khung
#: đã được giọng ĐỌC NHANH nuốt gọn mà KHÔNG méo tiếng, KHÔNG mất chữ. Nên
#: rút gọn chỉ phải lo phần vượt QUÁ tầm với của `rate`.
#:
#: ĐO ĐƯỢC VÌ SAO KHÔNG ĐƯỢC ĐỂ THẤP: đặt ngưỡng 1,30 + ngân sách ký tự nhắm
#: thẳng khung (hệ số 0,92) thì bản dịch bị chặt tới mức MẤT NGHĨA — chấm lại
#: bằng chính phép dịch-ngược, câu bị đổi chữ tụt **7,19 -> 2,38 · 7,00 ->
#: 4,89 · 7,00 -> 2,00** (3 lượt). Ép nhanh làm xấu TIẾNG, chặt chữ làm xấu
#: NỘI DUNG — cái sau tệ hơn, và trước đó không ai đo.
NGUONG_RUT_GON = 1.38

#: Ngân sách ký tự cho bước rút gọn = `khung × ký-tự/giây × hệ số này`. Lớn
#: hơn 1 CÓ CHỦ Ý: câu chỉ cần ngắn tới mức `rate` với tới được, không cần
#: ngắn tới mức đọc vừa khung ở tốc độ thường.
RUT_GON_HE_SO = 1.30

#: Chừa lại chút im lặng trước câu kế khi mượn (giây) — mượn sát quá thì hai
#: câu dính liền, nghe như nói hụt hơi.
CHUA_TRUOC_CAU_KE = 0.12


# ==================================================================
# BƯỚC 4b — RÚT GỌN CÂU DỊCH DÀI QUÁ KHUNG (làm TRƯỚC khi ép atempo)
# ==================================================================
#
# VÌ SAO PHẢI CÓ (đo được, không phải phòng xa): dịch Trung -> Anh đọc lên
# DÀI HƠN HẲN câu gốc. Lượt e2e đầu tiên trên zh60: 15/21 câu phải ép quá
# 1,30, `tempo_max` CHẠM TRẦN 1,50 và lệch mốc cuối tới 4.632 ms.
# Ép nhanh thì méo tiếng; câu ngắn lại thì KHÔNG méo gì cả. Nên chữa ở CHỮ
# trước, chỉ còn dư mới đụng tới tốc độ.

def khung_cho_phep(cau: list[dict], i: int, tong: float) -> float:
    """Khung thời gian câu #i được phép chiếm (đã tính phần MƯỢN đoạn kế)."""
    a = float(cau[i]["start"])
    b = float(cau[i]["end"])
    ke = float(cau[i + 1]["start"]) if i + 1 < len(cau) else tong
    return max(max(0.05, b - a), ke - a - CHUA_TRUOC_CAU_KE)


def toc_do_doc(texts: list[str], files: list[str], ok: list[bool]) -> float:
    """KÝ TỰ/GIÂY của CHÍNH giọng đang dùng, đo trên chính lượt đọc vừa xong.

    Vì sao không dùng hằng số: mỗi giọng/ngôn ngữ một tốc độ (đo `_do_le_im.py`:
    en-US-JennyNeural 20,45 · vi-VN-HoaiMyNeural 18,85 ký tự/giây trên phần
    TIẾNG THẬT). Tự đo thì đổi giọng/đổi ngôn ngữ vẫn đúng, không phải chỉnh
    tay. Chỉ tính câu đã CẮT LỀ (files ở đây là bản sạch) — tính cả lề im thì
    ra tốc độ thấp giả tạo và ngân sách ký tự bị siết oan.
    """
    kt = gy = 0.0
    for i, f in enumerate(files):
        if i >= len(ok) or not ok[i] or not f or not Path(f).exists():
            continue
        d = probe_duration(f)
        t = texts[i] if i < len(texts) else ""
        if d > 0.15 and len(t) > 3:
            kt += len(t)
            gy += d
    return (kt / gy) if gy > 0.5 else 16.0


def _rut_gon_loat(muc: list[dict], dich_sang: str) -> list[str]:
    """Nhờ LLM rút NGẮN các câu dịch quá dài, GIỮ Ý CHÍNH.

    Mỗi câu kèm **NGÂN SÁCH KÝ TỰ** tính từ tốc độ đọc ĐO ĐƯỢC của chính
    giọng đang dùng — nói "ngắn bớt 40%" thì model đoán mò, đưa con số ký tự
    thì nó có đích rõ ràng.
    """
    from app.ai import llm

    items = []
    for j, m in enumerate(muc):
        nga = m.get("toi_da_kytu") or 0
        items.append(
            f'#{j} [khung {m["khung"]:.1f} giây, bản hiện tại đọc mất '
            f'{m["d_nat"]:.1f} giây, TỐI ĐA {nga} ký tự]: "{m["text"][:400]}"')
    system = ("Bạn là biên tập lời thoại lồng tiếng. Rút NGẮN câu mà GIỮ "
              "nguyên ý chính. CHỈ trả JSON thuần.")
    prompt = (
        f"Các câu {_ten_nn(dich_sang)} sau đọc lên DÀI HƠN khung thời gian cho "
        "phép. Hãy viết lại NGẮN HƠN.\n"
        f"{chr(10).join(items)}\n\n"
        "QUY TẮC:\n"
        "- GIỮ Ý CHÍNH và giữ đúng ngôn ngữ đang có.\n"
        "- KHÔNG được vượt số ký tự TỐI ĐA ghi trong ngoặc của câu đó.\n"
        "- Bỏ từ đệm, bỏ chi tiết phụ, dùng từ ngắn hơn.\n"
        "- Vẫn phải là câu nói TỰ NHIÊN, không cụt lủn khó hiểu.\n"
        f"- Trả MẢNG JSON {len(muc)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<câu đã rút gọn>"}. '
        "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào."
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001
        return [m["text"] for m in muc]
    # Lấy theo NHÃN. Ở đây lệch bậc còn độc hơn: câu A bị thay bằng bản rút gọn
    # của câu B -> lời ĐÚNG NGHĨA của đoạn khác, mà độ dài vẫn "vừa khung" nên
    # không thước nào kêu.
    bang = _theo_nhan(data, list(range(len(muc))), "t")
    out = []
    for j, m in enumerate(muc):
        t = bang.get(j)
        out.append(str(t).strip() if isinstance(t, str) and str(t).strip()
                   else m["text"])
    return out


def rut_gon_vua_khung(cau: list[dict], texts: list[str], tts: dict,
                      tong: float, out_dir: str | Path, dich_sang: str,
                      voice: str = "", nguong_tempo: float = NGUONG_RUT_GON,
                      vong_toi_da: int = 2,
                      on_progress: Optional[Callable[[float, str], None]] = None,
                      ) -> dict:
    """Rút ngắn câu dịch nào đọc lên vượt khung, ĐỌC LẠI, giữ bản TỐT HƠN.

    Chỉ NHẬN bản rút gọn khi nó thật sự đọc NGẮN HƠN bản cũ — LLM đôi khi trả
    câu dài hơn, nhận bừa là tự làm hỏng.

    Trả {texts, files, ok, so_sua, tempo_can_truoc, tempo_can_sau}.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = list(texts)
    files = list(tts["files"])
    ok = list(tts["ok"])

    def _can_tempo() -> list[float]:
        """Hệ số atempo CẦN cho từng câu (1.0 = lọt khung sẵn)."""
        ra = []
        for i in range(len(cau)):
            if i >= len(files) or not ok[i] or not Path(files[i]).exists():
                ra.append(1.0)
                continue
            d = probe_duration(files[i])
            kh = khung_cho_phep(cau, i, tong)
            ra.append(max(1.0, d / kh) if kh > 0 and d > 0 else 1.0)
        return ra

    truoc = _can_tempo()
    so_sua = 0
    for vong in range(max(0, vong_toi_da)):
        can = _can_tempo()
        xau = [i for i, t in enumerate(can) if t > nguong_tempo]
        if not xau:
            break
        if on_progress:
            on_progress(vong / max(1, vong_toi_da),
                        f"Rút gọn {len(xau)} câu dài quá khung...")
        kts = toc_do_doc(texts, files, ok)      # ký tự/giây ĐO của giọng này
        muc = []
        for i in xau:
            kh = khung_cho_phep(cau, i, tong)
            d = probe_duration(files[i])
            muc.append({"i": i, "text": texts[i], "khung": kh, "d_nat": d,
                        "bot": max(0.05, 1.0 - kh / d) if d > 0 else 0.2,
                        # Ngân sách NỚI theo `RUT_GON_HE_SO`: phần dôi ra đã
                        # có bước ĐỌC NHANH lo, không cần chặt chữ tới mức
                        # mất nghĩa (số đo ở chú thích NGUONG_RUT_GON).
                        "toi_da_kytu": max(8, int(kh * kts * RUT_GON_HE_SO))})
        moi = _rut_gon_loat(muc, dich_sang)

        # đọc lại CHỈ các câu vừa rút gọn, vào file RIÊNG để còn so
        thu = [m for m in moi]
        paths = [str(out_dir / f"rg{vong}_{muc[j]['i']:04d}.mp3")
                 for j in range(len(muc))]
        import asyncio
        from app.core import dubbing
        v = voice or giong_theo_ngon_ngu(dich_sang)
        ok2 = asyncio.run(dubbing._synth_all(thu, v, paths))
        # CẮT LỀ như đường chính — không cắt thì bản rút gọn bị đo DÀI HƠN
        # thực tế và bị loại oan ở phép so "có ngắn hơn không" bên dưới.
        paths, _le = cat_le_loat(paths, list(ok2), out_dir / f"sach{vong}")

        for j, m in enumerate(muc):
            i = m["i"]
            if not ok2[j] or not Path(paths[j]).exists():
                continue
            d_moi = probe_duration(paths[j])
            if d_moi <= 0 or d_moi >= m["d_nat"] - 0.05:
                continue                       # không ngắn hơn -> GIỮ bản cũ
            texts[i] = thu[j]
            files[i] = paths[j]
            ok[i] = True
            so_sua += 1

    sau = _can_tempo()

    def _mx(xs: list[float]) -> float:
        return round(max(xs or [1.0]), 3)

    return {
        "texts": texts, "files": files, "ok": ok, "so_sua": so_sua,
        "tempo_can_max_truoc": _mx(truoc), "tempo_can_max_sau": _mx(sau),
        "so_cau_vuot_truoc": sum(1 for t in truoc if t > nguong_tempo),
        "so_cau_vuot_sau": sum(1 for t in sau if t > nguong_tempo),
        # TỪNG CÂU (không chỉ max) — phân bố mới nói được "còn bao nhiêu câu
        # bị ép", max chỉ nói được câu tệ nhất.
        "can_truoc": [round(t, 3) for t in truoc],
        "can_sau": [round(t, 3) for t in sau],
    }


# ==================================================================
# BƯỚC 4c — ĐỌC NHANH LẠI (thay cho ép `atempo`)
# ==================================================================
#
# `atempo` là WSOLA: cắt sóng thành cửa sổ rồi dán chồng — ĐO ĐƯỢC
# **5,357 dB méo phổ ở 1,20 · 6,765 ở 1,50 · 8,071 ở 1,80** (vòng tròn ép
# nhanh k rồi ép chậm 1/k, `_do_nguong_tempo.py`). Đó chính là cái tai nghe ra
# là "nói không mượt, nhiều lỗi".
#
# edge-tts có tham số `rate`: mô hình TỰ ĐỌC NHANH HƠN — không có phép cắt-dán
# nào, méo do co giãn = 0 theo cấu tạo. Đo `_do_rate_tts.py` (8 câu thật):
#   rate +5% -> nhanh THẬT 1,046x · +10% -> 1,093 · +20% -> 1,190 ·
#   +30% -> 1,279 · +40% -> 1,370 · +50% -> 1,455
# sai lệch so với yêu cầu chỉ −0,4% .. −3,0%, và WER KHÔNG xấu đi
# (0,83-2,92% — đúng dải nhiễu của chính phép đo).
#
# Nên thứ tự chữa bây giờ là: rút NGẮN CHỮ -> ĐỌC NHANH -> mượn thời gian ->
# cuối cùng mới `atempo`.

#: Trên mức này thì đọc lại còn hơn ép. 1,03 = dưới cả sai số của `rate`.
NGUONG_DOC_NHANH = 1.03

#: Trần `rate` edge-tts. +50% đã đo ra 1,455x; trên nữa CHƯA ĐO nên không dùng.
RATE_TOI_DA = 50

#: Bù phần edge-tts đọc HỤT so với yêu cầu (đo −0,4% .. −3,0%) + chút dư để
#: `khop_thoi_gian` không phải đụng tới `atempo` nữa.
RATE_BU = 4


def doc_nhanh_vua_khung(cau: list[dict], texts: list[str], files: list[str],
                        ok: list[bool], tong: float, out_dir: str | Path,
                        dich_sang: str = "en", voice: str = "",
                        nguong: float = NGUONG_DOC_NHANH,
                        on_progress: Optional[Callable[[float, str], None]] = None,
                        ) -> dict:
    """Câu nào vẫn dài quá khung -> ĐỌC LẠI bằng chính giọng đó, NHANH HƠN.

    Chỉ NHẬN bản đọc nhanh khi nó thật sự NGẮN HƠN bản cũ (edge-tts có lúc trả
    file dài hơn — nhận bừa là tự làm hỏng, cùng luật với bước rút gọn).

    Trả {files, ok, so_doc_lai, can_truoc, can_sau, rate_max}.
    """
    import asyncio
    from app.core import dubbing

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = list(files)
    ok = list(ok)

    def _can() -> list[float]:
        ra = []
        for i in range(len(cau)):
            if i >= len(files) or not ok[i] or not Path(files[i]).exists():
                ra.append(1.0)
                continue
            d = probe_duration(files[i])
            kh = khung_cho_phep(cau, i, tong)
            ra.append(max(1.0, d / kh) if kh > 0 and d > 0 else 1.0)
        return ra

    truoc = _can()
    xau = [i for i, t in enumerate(truoc) if t > nguong]
    if not xau:
        return {"files": files, "ok": ok, "so_doc_lai": 0,
                "can_truoc": [round(t, 3) for t in truoc],
                "can_sau": [round(t, 3) for t in truoc], "rate_max": 0}

    if on_progress:
        on_progress(0.2, f"Đọc nhanh lại {len(xau)} câu cho vừa khung...")
    v = voice or giong_theo_ngon_ngu(dich_sang)
    thu = [texts[i] if i < len(texts) else "" for i in xau]
    rates, paths = [], []
    for j, i in enumerate(xau):
        r = min(RATE_TOI_DA,
                max(1, int(round((truoc[i] - 1.0) * 100)) + RATE_BU))
        rates.append(f"+{r}%")
        paths.append(str(out_dir / f"nhanh_{i:04d}.mp3"))
    ok2 = asyncio.run(dubbing._synth_all(thu, v, paths, rate=rates))
    sach, _le = cat_le_loat(paths, list(ok2), out_dir / "sach")

    so = 0
    for j, i in enumerate(xau):
        if not ok2[j] or not Path(sach[j]).exists():
            continue
        d_cu = probe_duration(files[i])
        d_moi = probe_duration(sach[j])
        if d_moi <= 0.05 or d_moi >= d_cu - 0.02:
            continue                       # không ngắn hơn -> GIỮ bản cũ
        files[i] = sach[j]
        ok[i] = True
        so += 1

    sau = _can()
    return {
        "files": files, "ok": ok, "so_doc_lai": so,
        "can_truoc": [round(t, 3) for t in truoc],
        "can_sau": [round(t, 3) for t in sau],
        "can_max_truoc": round(max(truoc or [1.0]), 3),
        "can_max_sau": round(max(sau or [1.0]), 3),
        "rate_max": max(int(r.strip("+%")) for r in rates) if rates else 0,
    }


# ==================================================================
# BƯỚC 5 — KHỚP THỜI GIAN (co giãn + MƯỢN thời gian đoạn kế)
# ==================================================================

#: Ngưỡng im khi ĐO MỐC TIẾNG THẬT trên file đã khớp. Nhạy hơn `NGUONG_IM_DB`
#: (-45) vì ở đây câu đã qua `aresample`/`atempo`, nền số hoá nhích lên; -40 dB
#: là chỗ `_do_chu_tieng.py` đo được tách sạch giọng khỏi nền trên cả 2 lớp.
NGUONG_IM_MOC_DB = -40.0


def _atempo_chuoi(tempo: float) -> str:
    """Chuỗi filter atempo, chia tầng nếu > 2.0 (atempo chỉ nhận 0.5-2.0)."""
    parts = []
    while tempo > 2.0:
        parts.append("atempo=2.0")
        tempo /= 2.0
    parts.append(f"atempo={tempo:.4f}")
    return ",".join(parts)


def khop_thoi_gian(cau: list[dict], files: list[str], ok: list[bool],
                   tong: float, out_dir: str | Path,
                   tempo_canh_bao: float = TEMPO_CANH_BAO,
                   tempo_toi_da: float = TEMPO_TOI_DA,
                   on_progress: Optional[Callable[[float, str], None]] = None,
                   ) -> dict:
    """Đặt từng câu đã đọc vào ĐÚNG mốc gốc, co giãn khi cần.

    THỨ TỰ ƯU TIÊN (quan trọng — đừng đổi):
      1. Lọt khung sẵn -> KHÔNG đụng tốc độ (tempo 1.0, không méo).
      2. Tràn -> MƯỢN khoảng lặng ngay sau câu (tới trước câu kế
         `CHUA_TRUOC_CAU_KE` giây). Mượn được thì vẫn tempo 1.0.
      3. Mượn hết vẫn tràn -> mới ép atempo, trần `tempo_toi_da`.
      4. Ép trần vẫn tràn -> CẮT + fade ra. **0 ms CHỒNG LẤN LÀ BẤT BIẾN**,
         không phải may: thà mất đuôi một câu còn hơn hai câu chồng tiếng
         (anh Hùng nghe ra ngay, và nó làm hỏng CẢ câu sau chứ không chỉ câu
         này). Số câu phải cắt được ĐẾM và trả về — cấm giấu.

    Bất biến được KIỂM LẠI trên file đã ghi (`d_fin` đo bằng ffprobe), không
    tin số dự kiến: `atempo`/`atrim`/`aresample` làm tròn khác `d/k`.

    Trả {manh, lech_dau_ms, lech_cuoi_ms, tempo_max, so_cau_ep, so_cau_muon,
    moc_tieng, im_duoi_chu_ms_*}.
    `manh` = [(mốc_giây, đường_dẫn_wav)] để bước 6 trộn.
    `moc_tieng` = [(i, giây_BẮT_ĐẦU_NÓI, giây_HẾT_NÓI)] trên timeline đầu ra,
    ĐO bằng `silencedetect` trên chính file vừa ghi. **Đây là NGUỒN MỐC DUY
    NHẤT cho chữ mới** — xem `thay_audio_video`.

    **`lech_dau_ms` TRƯỚC ĐÂY LÀ SỐ BỊA.** Bản cũ ghi thẳng
    `lech_dau.append(0.0)` kèm chú thích "đặt ĐÚNG mốc gốc": đó là mốc ĐẶT
    FILE, không phải mốc PHÁT RA TIẾNG. File sau `cat_le_im` vẫn còn `GIU_DAU`
    (0,04 s) lề im, `atempo`/`aresample` còn làm nó lệch thêm. Đo thật trên
    video Douyin 132 s: **42,7 ms trung bình, 70,2 ms lớn nhất** — nhỏ, nhưng
    một con số ĐO ĐƯỢC thì lần sau nó to lên mới có ai thấy. Đây đúng họ bẫy
    `astats`/`startswith` của cổng 44/53: **phép đo hỏng nguy hiểm hơn không
    đo, vì nó phát chứng nhận.**

    **`im_duoi_chu_ms` LÀ SỐ MỚI, VÀ NÓ MỚI LÀ CHỖ HỎNG THẬT.** = phần khung
    câu còn chạy SAU KHI đã hết tiếng. Phụ đề cháy sẵn trong hình chạy theo
    người nói GỐC, nên chỗ đó là "chữ chạy mà không ai nói". Đo trên chính
    video anh Hùng chê: **tổng 22,52 s / 132,3 s**, câu tệ nhất **6.599 ms**
    (khung 11,89 s mà tiếng chỉ 5,29 s).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manh: list[tuple[float, str]] = []
    moc_tieng: list[tuple[int, float, float]] = []
    lech_dau: list[float] = []
    lech_cuoi: list[float] = []
    im_duoi: list[float] = []
    chong: list[float] = []
    temps: list[float] = []
    so_ep = so_muon = so_cat = 0
    bo_qua = 0
    #: mép an toàn khi cắt: ffmpeg làm tròn theo mẫu, cắt đúng bằng trần thì
    #: file ra có thể dài hơn vài chục micro-giây -> vẫn tính là chồng lấn.
    _MEP = 0.005

    for i, c in enumerate(cau):
        if i >= len(files) or not ok[i] or not Path(files[i]).exists():
            bo_qua += 1
            continue
        a = float(c["start"])
        b = float(c["end"])
        khung = max(0.05, b - a)

        # khoảng lặng tới câu kế (có thể MƯỢN)
        ke = float(cau[i + 1]["start"]) if i + 1 < len(cau) else tong
        # TRẦN CỨNG: câu này TUYỆT ĐỐI không được kéo tới mốc câu kế.
        tran = max(0.10, ke - a)
        cho_phep = min(tran, max(khung, ke - a - CHUA_TRUOC_CAU_KE))

        d_nat = probe_duration(files[i])
        if d_nat <= 0:
            bo_qua += 1
            continue

        if d_nat <= khung + 1e-3:
            tempo = 1.0                       # (1) lọt sẵn
        elif d_nat <= cho_phep + 1e-3:
            tempo = 1.0                       # (2) mượn đoạn kế, không méo
            so_muon += 1
        else:                                 # (3) đành ép
            tempo = min(tempo_toi_da, d_nat / max(0.05, cho_phep))
            so_ep += 1
            if d_nat > khung + 1e-3:
                so_muon += 1

        dst = out_dir / f"khop_{i:04d}.wav"
        d_fin = 0.0
        cat_lan = 0
        # (4) BẤT BIẾN 0 ms: dựng, ĐO LẠI, còn tràn thì cắt — tối đa 2 vòng.
        while True:
            af = ["aresample=44100"]
            if abs(tempo - 1.0) > 1e-3:
                af.append(_atempo_chuoi(tempo))
            gioi = tran - _MEP
            if cat_lan or (d_nat / tempo) > gioi:
                af.append(f"atrim=0:{gioi:.3f}")
                af.append("asetpts=N/SR/TB")
                af.append(f"afade=t=out:st={max(0.0, gioi - 0.10):.3f}:d=0.10")
            _ffmpeg(["-i", files[i], "-af", ",".join(af), "-ac", "2",
                     "-ar", str(SR_TACH), "-c:a", "pcm_s16le", str(dst)],
                    f"khớp thời gian câu #{i}")
            d_fin = _kiem_wav(dst)
            if a + d_fin <= ke + 1e-4 or cat_lan >= 2:
                if cat_lan:
                    so_cat += 1
                break
            cat_lan += 1
            tran = min(tran, ke - a)          # siết lại rồi cắt thật

        # MỐC TIẾNG THẬT — ĐO, không suy ra từ chỗ đặt file.
        le_d, le_c, _tg = do_le_im(dst, nguong_db=NGUONG_IM_MOC_DB)
        t_noi_a = a + le_d
        t_noi_b = a + max(le_d + 0.05, d_fin - le_c)
        moc_tieng.append((i, round(t_noi_a, 3), round(t_noi_b, 3)))

        manh.append((a, str(dst)))
        temps.append(tempo)
        lech_dau.append(le_d * 1000.0)        # LỆCH ĐẦU THẬT (bản cũ bịa 0,0)
        lech_cuoi.append((a + d_fin - b) * 1000.0)
        # CHỮ CÒN CHẠY MÀ ĐÃ HẾT TIẾNG — con số anh Hùng nghe ra
        im_duoi.append(max(0.0, b - t_noi_b) * 1000.0)
        # CHỒNG LẤN = phần LIẾM SANG câu kế. Đây mới là con số nói lên
        # "timeline sai": kéo dài vào KHOẢNG LẶNG là cố ý (mượn thời gian),
        # còn đè lên câu sau mới là hỏng.
        chong.append(max(0.0, (a + d_fin - ke) * 1000.0))
        if on_progress:
            on_progress((i + 1) / max(1, len(cau)),
                        f"Khớp thời gian {i + 1}/{len(cau)}...")

    def _tb(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 1) if xs else 0.0

    return {
        "manh": manh,
        "moc_tieng": moc_tieng,
        "so_cau": len(manh), "bo_qua": bo_qua,
        "lech_dau_ms_tb": _tb([abs(x) for x in lech_dau]),
        "lech_dau_ms_max": round(max([abs(x) for x in lech_dau] or [0]), 1),
        # CHỮ CHẠY MÀ KHÔNG CÓ TIẾNG — cấm giấu, đây là lỗi anh Hùng nghe ra
        "im_duoi_chu_ms_tb": _tb(im_duoi),
        "im_duoi_chu_ms_max": round(max(im_duoi or [0]), 1),
        "im_duoi_chu_giay_tong": round(sum(im_duoi) / 1000.0, 2),
        "so_cau_im_duoi_1s": sum(1 for x in im_duoi if x > 1000.0),
        # lệch cuối GỒM CẢ phần mượn khoảng lặng hợp lệ -> đọc kèm chồng lấn
        "lech_cuoi_ms_tb": _tb([abs(x) for x in lech_cuoi]),
        "lech_cuoi_ms_max": round(max([abs(x) for x in lech_cuoi] or [0]), 1),
        "chong_lan_ms_max": round(max(chong or [0]), 1),
        "so_cau_chong_lan": sum(1 for x in chong if x > 1.0),
        "tempo_max": round(max(temps or [1.0]), 3),
        "tempo_tb": round(sum(temps) / len(temps), 3) if temps else 1.0,
        "so_cau_ep": so_ep, "so_cau_muon": so_muon,
        # Câu phải CẮT ĐUÔI để giữ bất biến 0 ms — số này KHÔNG được giấu:
        # nó là chỗ duy nhất còn mất chữ.
        "so_cau_cat": so_cat,
        "so_cau_vuot_canh_bao": sum(1 for t in temps if t > tempo_canh_bao),
        # PHÂN BỐ từng câu — `tempo_max` một mình che mất "bao nhiêu % câu bị
        # ép quá 1,2 / 1,3 / 1,4" (số đo anh Hùng cần để biết nghe dở tới đâu).
        "tempo_cau": [round(t, 3) for t in temps],
        "chong_cau_ms": [round(x, 1) for x in chong],
    }


# ==================================================================
# BƯỚC 6 — TRỘN GIỌNG MỚI + LỚP NHẠC GỐC
# ==================================================================

#: Trần DÒNG LỆNH của Windows `CreateProcess` (ký tự, kể cả NUL) — **KHÔNG
#: liên quan gì tới `MAX_PATH` 260** dù lời lỗi nghe y hệt. ĐO ĐƯỢC 14/08/2026
#: (`_do_cmdline.py`, gọi ffmpeg thật với tham số dài dần): 32.763 ký tự CHẠY
#: ĐƯỢC · 32.863 ký tự ném `FileNotFoundError [WinError 206] The filename or
#: extension is too long`. Đúng chuỗi lỗi anh Hùng thấy trên màn hình, và tên
#: lỗi ấy đã dẫn thẳng tới chẩn đoán sai "đường dẫn quá 260".
TRAN_CMD_WINDOWS = 32767

#: Ngân sách tự đặt cho MỘT lệnh ffmpeg. Chừa ~2.700 ký tự so với trần thật:
#: `list2cmdline` thêm dấu ngoặc/gạch chéo mà ta không đoán trước được, và
#: `settings.FFMPEG_PATH` trên máy nhân viên có thể dài hơn máy này.
NGAN_SACH_CMD = 30000


def _dai_dong_lenh(args: list[str]) -> int:
    """Độ dài dòng lệnh Windows sẽ dựng ra — KỂ CẢ phần `_ffmpeg` tự thêm.

    Đo bằng chính `subprocess.list2cmdline` (thứ `Popen` dùng để nối argv
    thành `lpCommandLine`), không ước lượng bằng `sum(len(...))`: dấu ngoặc
    kép quanh đường dẫn có dấu cách là phần đếm được, đừng bỏ.
    """
    return len(subprocess.list2cmdline(
        [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
         *args]))


def _args_ghep(manh: list[tuple[float, str]], tong: float,
               out_wav: str | Path, pcm: str = "pcm_s16le",
               sr: int = SR_TACH, ac: int = 2, cl: str = "stereo") -> list[str]:
    """Tham số ffmpeg rải `manh` lên 1 track im lặng dài `tong` giây.

    `normalize=0` BẮT BUỘC — không thì amix chia biên độ theo số đầu vào và
    giọng nhỏ dần theo số câu (bẫy đã ghi ở đầu file).

    `sr`/`ac`/`cl` có tham số vì `dubbing._mix_track` (đường LỒNG TIẾNG) dùng
    48k MONO và mắc ĐÚNG cùng bệnh — xem `ghep_track_am`.
    """
    args: list[str] = ["-f", "lavfi", "-t", f"{tong:.3f}",
                       "-i", f"anullsrc=r={sr}:cl={cl}"]
    parts, labels = [], []
    for i, (start, wav) in enumerate(manh):
        args += ["-i", str(wav)]
        ms = max(0, int(round(start * 1000)))
        parts.append(f"[{i + 1}:a]adelay={ms}:all=1[d{i}]")
        labels.append(f"[d{i}]")
    n = len(manh) + 1
    parts.append(f"[0:a]{''.join(labels)}amix=inputs={n}:duration=first:"
                 f"normalize=0[out]")
    args += ["-filter_complex", ";".join(parts), "-map", "[out]",
             "-ac", str(ac), "-ar", str(sr), "-c:a", pcm,
             str(out_wav)]
    return args


def _chia_me(manh: list[tuple[float, str]], tong: float,
             out_wav: str | Path, **kw) -> list[list[tuple[float, str]]]:
    """Chia `manh` thành các MẺ, mỗi mẻ dựng được bằng MỘT lệnh vừa ngân sách.

    Cắt theo ĐỘ DÀI DÒNG LỆNH THẬT (dựng thử rồi đo), không theo "N câu mỗi
    mẻ": chi phí mỗi câu là ĐỘ DÀI ĐƯỜNG DẪN wav, mà đường dẫn đó dài ngắn tuỳ
    tên video + chỗ anh Hùng đặt thư mục đích. Chốt cứng con số câu là hôm nay
    đúng, mai anh ấy đổi thư mục là sai lại.
    """
    me: list[list[tuple[float, str]]] = []
    cur: list[tuple[float, str]] = []
    for m in manh:
        thu = cur + [m]
        if cur and _dai_dong_lenh(
                _args_ghep(thu, tong, out_wav, "pcm_f32le",
                           **kw)) > NGAN_SACH_CMD:
            me.append(cur)
            cur = [m]
        else:
            cur = thu
    if cur:
        me.append(cur)
    return me


def _cong_track(files: list[str], tong: float, out_wav: str | Path,
                pcm: str = "pcm_s16le", sr: int = SR_TACH, ac: int = 2,
                chay: Optional[Callable] = None) -> None:
    """CỘNG nhiều track cùng độ dài lại làm một (amix `normalize=0` = phép cộng).

    Tự chia mẻ nốt nếu danh sách file dài quá ngân sách — track mẻ mang tên
    NGẮN (`_me00.wav`) nên trên thực tế không bao giờ tới đó, nhưng để vòng lặp
    này ở đây thì hàm đúng với MỌI độ dài video, không phải "đủ dùng cho tới
    khi anh Hùng đưa video 3 tiếng".
    """
    chay = chay or _ffmpeg
    lop = [str(f) for f in files]
    vong = 0
    tam_da_tao: list[Path] = []
    try:
        while True:
            args: list[str] = []
            for f in lop:
                args += ["-i", str(f)]
            fc = ("".join(f"[{i}:a]" for i in range(len(lop)))
                  + f"amix=inputs={len(lop)}:duration=first:normalize=0[out]")
            args += ["-filter_complex", fc, "-map", "[out]",
                     "-ac", str(ac), "-ar", str(sr), "-c:a", pcm,
                     str(out_wav)]
            if len(lop) <= 2 or _dai_dong_lenh(args) <= NGAN_SACH_CMD:
                chay(args, "cộng các mẻ track giọng", timeout=900)
                return
            # còn dài -> cộng từng nhóm 32 rồi lặp lại
            goc = Path(out_wav).parent
            moi: list[str] = []
            for k in range(0, len(lop), 32):
                nhom = lop[k:k + 32]
                if len(nhom) == 1:
                    moi.append(nhom[0])
                    continue
                dst = goc / f"_cg{vong}_{k // 32:02d}.wav"
                _cong_track(nhom, tong, dst, "pcm_f32le", sr, ac, chay)
                tam_da_tao.append(dst)
                moi.append(str(dst))
            lop, vong = moi, vong + 1
    finally:
        for f in tam_da_tao:
            try:
                f.unlink()
            except OSError:
                pass


def _ghep_track_giong(manh: list[tuple[float, str]], tong: float,
                      out_wav: str | Path) -> None:
    """Rải các câu đã khớp lên 1 track im lặng dài ĐÚNG `tong` giây.

    **LỖI THẬT 14/08/2026 — `WinError 206` trên video DÀI.** Hàm này đưa MỘT
    `-i <đường dẫn wav>` vào dòng lệnh cho MỖI CÂU, cộng một `adelay` trong
    `-filter_complex`. Chi phí ~170 ký tự/câu (đường dẫn ~127 + nhãn), nên dòng
    lệnh phình theo `số câu × độ dài đường dẫn`. Đo trên 6 video thật của anh
    Hùng (`_do_206.py`): 107 câu -> 17.097 ký tự (chạy được) · **278 câu ->
    47.794** · **241 câu -> 42.153** — hai video cuối chính là hai dòng "Lỗi"
    trên màn hình. `CreateProcess` từ chối từ ~32.767 ký tự.

    **CHỮA: chia MẺ.** `amix` với `normalize=0` là PHÉP CỘNG thuần, mà mỗi mẻ
    đã là một track dài đủ `tong` giây (chỗ chưa có câu nào là im lặng = 0),
    nên cộng các mẻ lại cho ra ĐÚNG track như dựng một lượt. Mẻ trung gian ghi
    `pcm_f32le` để không lượng tử hoá hai lần.

    **VỪA NGÂN SÁCH THÌ CHẠY Y HỆT BẢN CŨ** — không phải "cho chắc" mà là cách
    duy nhất giữ được bất biến: video ngắn đi đúng dòng lệnh cũ TỪNG KÝ TỰ, nên
    không cần tin lời hứa "kết quả giống nhau". Đường chia mẻ chỉ chạy ở đúng
    chỗ bản cũ ĐÃ CHẾT.
    """
    ghep_track_am(manh, tong, out_wav, ten_viec="ghép track giọng mới")


def ghep_track_am(manh: list[tuple[float, str]], tong: float,
                  out_wav: str | Path, sr: int = SR_TACH, ac: int = 2,
                  cl: str = "stereo", chay: Optional[Callable] = None,
                  ten_viec: str = "ghép track") -> None:
    """Rải `manh` lên track im lặng `tong` giây, TỰ CHIA MẺ khi lệnh quá dài.

    Dùng chung cho HAI đường mắc ĐÚNG cùng bệnh (rà ra 14/08/2026):
      · `thay_giong._ghep_track_giong` — 44,1k STEREO (thay giọng nói)
      · `dubbing._mix_track`           — 48k MONO (lồng tiếng / thuyết minh)

    `chay` = hàm chạy ffmpeg CỦA MODULE GỌI. Mỗi module có `_ffmpeg` riêng
    (khác lời báo lỗi, khác cách gắn tiến trình vào job để bấm Huỷ giết được
    nó) — đừng ép cả hai dùng chung một hàm chạy chỉ để bớt một tham số.
    """
    chay = chay or _ffmpeg
    kw = {"sr": sr, "ac": ac, "cl": cl}
    args = _args_ghep(manh, tong, out_wav, **kw)
    if _dai_dong_lenh(args) <= NGAN_SACH_CMD:
        chay(args, ten_viec, timeout=900)
        return

    goc = Path(out_wav).parent
    me = _chia_me(manh, tong, out_wav, **kw)
    tam: list[Path] = []
    try:
        for k, nhom in enumerate(me):
            dst = goc / f"_me{k:02d}.wav"
            chay(_args_ghep(nhom, tong, dst, "pcm_f32le", **kw),
                 f"{ten_viec} mẻ {k + 1}/{len(me)}", timeout=900)
            tam.append(dst)
        _cong_track([str(t) for t in tam], tong, out_wav, "pcm_s16le",
                    sr, ac, chay)
    finally:
        # DỌN KỂ CẢ KHI LỖI GIỮA CHỪNG: mỗi mẻ là một wav dài bằng cả video
        # (video 8 phút ~ 85 MB), bỏ lại vài mẻ là đúng đường tới "ổ C đầy".
        for f in tam:
            try:
                f.unlink()
            except OSError:
                pass


def tron_thay_giong(nhac_wav: str | Path, manh: list[tuple[float, str]],
                    tong: float, out_wav: str | Path,
                    muc_giong_db: float = 0.0, muc_nhac_db: float = -2.0,
                    tran_dinh_db: float = TRAN_DINH_DB,
                    on_progress: Optional[Callable[[float, str], None]] = None,
                    ) -> dict:
    """Trộn GIỌNG MỚI lên LỚP NHẠC gốc, hạn đỉnh chống méo, rồi ĐO cân bằng.

    `alimiter` bắt buộc `level=0` (mặc định `level=true` TỰ NÂNG +3,1 dB) và
    `latency=1` (không có thì trễ 0,98 ms) — bẫy đã ghi ở đầu file.
    """
    out_wav = Path(out_wav)
    tam = out_wav.with_suffix(".giong.wav")
    if on_progress:
        on_progress(0.2, "Ghép track giọng mới...")
    _ghep_track_giong(manh, tong, tam)
    _kiem_wav(tam)

    if on_progress:
        on_progress(0.6, "Trộn giọng mới với nhạc nền gốc...")
    fc = (
        f"[0:a]volume={muc_nhac_db:.2f}dB[nh];"
        f"[1:a]volume={muc_giong_db:.2f}dB[gi];"
        "[nh][gi]amix=inputs=2:duration=first:normalize=0[mx];"
        f"[mx]alimiter=level_in=1:level_out=1:limit="
        f"{10.0 ** (tran_dinh_db / 20.0):.6f}:level=0:latency=1[out]"
    )
    _ffmpeg(["-i", str(nhac_wav), "-i", str(tam), "-filter_complex", fc,
             "-map", "[out]", "-ac", "2", "-ar", str(SR_TACH),
             "-c:a", "pcm_s16le", str(out_wav)], "trộn giọng mới + nhạc")
    _kiem_wav(out_wav)

    meo = do_meo(out_wav)
    kq = {
        "ra": str(out_wav),
        "rms_giong": round(do_rms(tam), 6),
        "rms_nhac": round(do_rms(nhac_wav), 6),
        "rms_tron": round(do_rms(out_wav), 6),
        "dinh_dbfs": meo.get("dinh"),
        "cham_tran": meo.get("cham_tran"),
        "do_dai": round(probe_duration(out_wav), 3),
    }
    g, n = kq["rms_giong"], kq["rms_nhac"]
    if g > 0 and n > 0:
        import math
        kq["giong_tren_nhac_db"] = round(20.0 * math.log10(g / n), 2)
    if on_progress:
        on_progress(1.0, "Trộn xong")
    return kq


# ==================================================================
# NỐI VÀO VIDEO — thay audio, KIỂM rồi mới đụng tới file gốc
# ==================================================================

def thay_audio_video(video_goc: str | Path, audio_moi: str | Path,
                     video_ra: str | Path,
                     che_chu: bool = False,
                     che_chu_cach: str = "mo",
                     che_chu_muc: float = 1.0,
                     che_chu_log: Optional[list] = None,
                     dong_chu: Optional[list] = None) -> None:
    """Thay TIẾNG của video. `che_chu=False` -> GIỮ NGUYÊN hình (`-c:v copy`).

    `dong_chu` = [(giây_bắt_đầu, giây_kết_thúc, chữ), ...] — **MỐC LẤY TỪ
    CHÍNH FILE GIỌNG ĐÃ SINH RA** (`khop_thoi_gian` trả `moc_tieng`, đo bằng
    `silencedetect`), KHÔNG lấy từ bản chép lời gốc. Giọng nói ở đâu thì chữ
    hiện ở đó — MỘT NGUỒN DUY NHẤT.

    **VÌ SAO PHẢI VIẾT LẠI CHỮ, KHÔNG PHẢI CHỈ CHE** (lỗi anh Hùng nghe+xem
    14/08/2026: *"chữ dịch ở dưới vẫn chạy mà trên đáng lý ra phải nói mà k có
    nói, 1 lúc sau nó lại tự nói"*): phụ đề của video Douyin **cháy sẵn trong
    ĐIỂM ẢNH** và đường này `-c:v copy` nên nó giữ NGUYÊN mốc GỐC, trong khi
    giọng thì đặt lại theo câu chép lời. Hai bên lệch nhau ở đúng 2 chỗ ĐO
    ĐƯỢC: câu dài (khung 11,89 s, tiếng 5,29 s -> **6,6 giây chữ chạy không
    tiếng**) và LỖ bản chép lời (Groq bỏ sót 9,56 s liền). Che-mà-không-viết
    thì hết lệch nhưng người xem **mất trắng** phần chữ; che-rồi-viết-theo-
    giọng thì chữ và tiếng không thể lệch nhau NỮA theo cấu tạo.

    Chữ mới CHỈ được viết khi CÓ CHE (`loc` khác rỗng): viết đè lên chữ cũ mà
    không che là **HAI LỚP CHỮ** chồng nhau, tệ hơn hẳn.

    **VÌ SAO CHE CHỮ PHẢI Ở ĐÂY, KHÔNG PHẢI Ở `ffmpeg_utils`** (lỗi anh Hùng
    báo 14/08/2026: *"chữ trong video vẫn k bị mờ"*): `che_chu` tới v2.27.1
    CHỈ được nối vào đường XUẤT CLIP (`export_canvas_clip`). Đường THAY TIẾNG
    là đường KHÁC — nó không cắt clip, không vẽ lớp chữ, và tới đây thì
    `grep che_chu app/core/thay_giong.py` ra **0 kết quả**. Nên bật ô trong
    "Chỉnh mẫu" rồi bấm "Thay giọng nói" thì chữ cháy sẵn KHÔNG BAO GIỜ bị
    che, mà cũng KHÔNG một dòng báo — đúng họ bẫy "app vẫn chạy, cổng vẫn
    xanh" cả repo này đang chống.

    **GIÁ PHẢI TRẢ, NÓI THẲNG:** che chữ thì BẮT BUỘC encode lại luồng hình
    (không có cách nào bôi mờ điểm ảnh mà vẫn `-c:v copy`). Vì vậy cờ TẮT
    phải giữ lệnh ffmpeg **giống từng ký tự** bản cũ — đó là bất biến cổng 59
    đo, không phải lời hứa.

    `segs=[(0, độ_dài)]`: đường này giữ NGUYÊN video nên thời gian ĐẦU RA
    trùng thời gian NGUỒN, `hop_theo_doan` quy đổi với `off=0` là đúng. Nhờ
    vậy hộp che vẫn BÁM THEO MỐC (chữ chạy tới đâu che tới đó) chứ không phải
    một dải ngang suốt phim.
    """
    if not che_chu:
        _ffmpeg(["-i", str(video_goc), "-i", str(audio_moi),
                 "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "192k", "-shortest", str(video_ra)],
                "thay tiếng vào video", timeout=1800)
        if che_chu_log is not None:
            che_chu_log.append({"bat": False, "che": False, "ly_do": ""})
        return

    loc, dai, ly_do = "", None, ""
    try:
        from app.core import che_chu as _CC
        dur = probe_duration(video_goc)
        segs = [(0.0, dur)] if dur > 0 else None
        loc, dai, ly_do = _CC.loc_cho_xuat(
            video_goc, cach=che_chu_cach, muc=che_chu_muc, segs=segs)
    except Exception as e:      # noqa: BLE001 — che chữ KHÔNG được giết lượt
        loc, dai = "", None
        ly_do = f"dò/che chữ lỗi ({e}) -> KHÔNG che"
    if che_chu_log is not None:
        che_chu_log.append({
            "bat": True, "che": bool(loc),
            "cach": _CC_TEN.get((che_chu_cach or "mo").lower(), "làm mờ"),
            "muc": float(che_chu_muc or 0), "ly_do": ly_do,
            "dai": (dai.dict() if dai is not None
                    and hasattr(dai, "dict") else None)})

    if not loc:
        # KHÔNG dò ra chữ -> đừng encode lại vô ích (che oan video sạch là ca
        # sai đắt nhất của tính năng này: 0/76 ở cổng 56).
        thay_audio_video(video_goc, audio_moi, video_ra, che_chu=False)
        return

    # --- CHỮ MỚI THEO MỐC GIỌNG (chỉ khi ĐÃ che — cấm 2 lớp chữ) ---
    chuoi = [loc]
    so_dong = 0
    if dong_chu:
        try:
            d_viet = dai if (dai is not None and getattr(dai, "co_chu", False)
                             and dai.cao_dai > 0) else None
            ass = Path(video_ra).with_suffix(".chu_theo_giong.ass")
            if d_viet is not None and _CC.ghi_ass(dong_chu, ass, d_viet):
                # nối bằng DẤU PHẨY: `loc` là GRAPH kết bằng `overlay=`, nối
                # `;subtitles=` là đẻ chuỗi RỜI không đầu vào (bẫy đã ghi ở
                # `che_chu.che_va_viet`). Phẩy = viết chữ SAU khi che xong.
                chuoi.append(f"subtitles='{_CC._esc_loc(ass)}'")
                so_dong = len(dong_chu)
        except Exception as e:      # noqa: BLE001 — chữ mới KHÔNG được giết lượt
            so_dong = 0
            if che_chu_log:
                che_chu_log[-1]["chu_loi"] = str(e)[:200]
    if che_chu_log:
        che_chu_log[-1]["so_dong_chu"] = so_dong

    from app.core.ffmpeg_utils import detect_encoder
    enc = detect_encoder()
    if enc == "h264_nvenc":
        ve = ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr",
              "-cq", "21", "-pix_fmt", "yuv420p"]
    else:
        ve = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-pix_fmt", "yuv420p"]
    _ffmpeg(["-i", str(video_goc), "-i", str(audio_moi),
             "-filter_complex", f"[0:v]{','.join(chuoi)}[vout]",
             "-map", "[vout]", "-map", "1:a:0", *ve,
             "-c:a", "aac", "-b:a", "192k", "-shortest", str(video_ra)],
            "thay tiếng + che chữ vào video", timeout=3600)


#: Chữ mới phải nằm ít nhất bấy nhiêu giây trên màn hình — câu đọc 0,2 giây mà
#: chữ chớp 0,2 giây thì không ai đọc kịp. Nới về SAU (chưa tới câu kế) nên
#: không bao giờ che mất chữ của câu sau.
CHU_TOI_THIEU_S = 0.90

#: Chừa lại trước mốc nói của câu KẾ — chữ hai câu dính nhau nhìn như nhảy.
CHU_CHUA_TRUOC_S = 0.06


def dong_chu_theo_giong(moc_tieng: list, texts: list) -> list:
    """[(bắt_đầu, kết_thúc, chữ)] cho `che_chu.ghi_ass` — MỐC TỪ GIỌNG.

    `moc_tieng` = `khop_thoi_gian()["moc_tieng"]` = [(i, giây_nói, giây_hết)]
    ĐO bằng `silencedetect` trên chính file wav đã khớp. `texts` = lời CUỐI
    CÙNG app đọc lên (`rut_gon_vua_khung()["texts"]`).

    Hàm THUẦN, không đụng đĩa — để cổng thử phá gọi thẳng được: đưa mốc GỐC
    (`cau[i]["start"]`) vào đây là bảng lệch phải ĐỎ.
    """
    ra: list = []
    n = len(moc_tieng)
    for k, (i, a, b) in enumerate(moc_tieng):
        t = str(texts[i]).strip() if 0 <= i < len(texts) else ""
        if not t:
            continue
        b = max(float(b), float(a) + CHU_TOI_THIEU_S)
        if k + 1 < n:                      # KHÔNG được lấn sang câu kế
            b = min(b, float(moc_tieng[k + 1][1]) - CHU_CHUA_TRUOC_S)
        if b <= a:
            b = float(a) + 0.20
        ra.append((round(float(a), 3), round(b, 3), t))
    return ra


#: Tên tiếng Việt của cách che — cho nhật ký, KHÔNG EMOJI.
_CC_TEN = {"mo": "làm mờ", "khoi": "phủ khối", "hat": "làm hạt"}


def kiem_video_ra(video_ra: str | Path, do_dai_goc: float,
                  lech_toi_da: float = 1.0) -> dict:
    """KIỂM file mới TRƯỚC KHI đụng tới video gốc — có hình, có tiếng, đúng dài.

    Đây là lá chắn cho bẫy ĐÃ XẢY RA THẬT: ffmpeg trả mã 0 mà file 0 KiB /
    0 khung / im lặng. Ném RuntimeError nếu bất kỳ mục nào hỏng.
    """
    p = Path(video_ra)
    if not p.exists():
        raise RuntimeError(f"Không có file ra {p.name}")
    cỡ = p.stat().st_size
    if cỡ < 10240:
        raise RuntimeError(f"File ra {p.name} rỗng ({cỡ} byte)")
    khung = do_khung_hinh(p)
    if khung <= 0:
        raise RuntimeError(f"File ra {p.name} KHÔNG CÓ KHUNG HÌNH nào "
                           "(ffmpeg trả mã 0 nhưng video rỗng)")
    dai = probe_duration(p)
    if dai <= 0:
        raise RuntimeError(f"File ra {p.name} độ dài 0 giây")
    lech = abs(dai - do_dai_goc)
    if do_dai_goc > 0 and lech > lech_toi_da:
        raise RuntimeError(
            f"File ra {p.name} dài {dai:.3f}s, gốc {do_dai_goc:.3f}s — "
            f"lệch {lech:.3f}s (quá {lech_toi_da}s)")
    rms = do_rms(p)
    if rms <= 0:
        raise RuntimeError(f"File ra {p.name} IM LẶNG HẲN (RMS {rms})")
    return {"co": cỡ, "khung": khung, "do_dai": round(dai, 3),
            "lech_do_dai": round(lech, 3), "rms": round(rms, 6)}


def thay_giong_video(video_in: str | Path, dich_sang: str = "en",
                     thu_muc_lam: str | Path = "", voice: str = "",
                     cach_tach: str = "auto", giu_file_tam: bool = False,
                     che_chu: bool = False, che_chu_cach: str = "mo",
                     che_chu_muc: float = 1.0, viet_chu: bool = True,
                     on_progress: Optional[Callable[[float, str], None]] = None,
                     ) -> dict:
    """CHẠY ĐỦ 6 BƯỚC cho 1 video, trả file video MỚI (chưa đụng file gốc).

    `viet_chu=True` (mặc định) + `che_chu=True` -> sau khi che dòng chữ cháy
    sẵn thì VIẾT LẠI bản dịch vào đúng dải đó, mốc lấy từ CHÍNH GIỌNG vừa
    sinh. Không bật che chữ thì cờ này vô hiệu (viết đè lên chữ cũ = 2 lớp).

    KHÔNG tự xoá/đổi tên gì cả — việc đó do `thay_giong_thu_muc` làm SAU KHI
    `kiem_video_ra` đã xác nhận file mới hợp lệ.
    """
    import tempfile as _tf

    video_in = Path(video_in)
    tam_goc = Path(thu_muc_lam) if thu_muc_lam else Path(
        _tf.mkdtemp(prefix="tg_", dir=str(video_in.parent)))
    tam_goc.mkdir(parents=True, exist_ok=True)

    def prog(p: float, m: str) -> None:
        if on_progress:
            on_progress(max(0.0, min(1.0, p)), m)

    kq: dict = {"vao": str(video_in), "thu_muc_lam": str(tam_goc)}
    t0 = time.time()
    try:
        # --- bước 0: rút audio
        prog(0.02, "Rút tiếng khỏi video...")
        goc_wav = tam_goc / "goc.wav"
        tong = tach_wav(video_in, goc_wav)
        kq["do_dai"] = round(tong, 3)

        # --- bước 1: tách giọng / nhạc
        prog(0.06, "Tách giọng khỏi nhạc nền...")
        t = tach_giong(goc_wav, tam_goc / "tach", cach=cach_tach,
                       on_progress=lambda p, m: prog(0.06 + 0.24 * p, m))
        kq["tach"] = {k: v for k, v in t.items() if k != "stems"}

        # --- bước 2: chép lời
        prog(0.32, "Chép lời gốc...")
        d = chep_loi(goc_wav, t.get("giong") or "",
                     on_progress=lambda p, m: prog(0.32 + 0.10 * p, m))
        cau = cau_tu_transcript(d)
        kq["chep"] = {"ngon_ngu": d.get("language"),
                      "so_tu": len(d.get("words") or []),
                      "so_cau": len(cau),
                      "nguon": d.get("_nguon"),
                      "giay": d.get("_giay_chep")}
        if not cau:
            raise RuntimeError("Không chép được câu nào — video không có lời?")

        # --- bước 3: dịch + hậu kiểm
        prog(0.44, f"Dịch {len(cau)} câu...")
        goc_ma = (d.get("language") or "")[:2].lower()
        dd = dich_hau_kiem(cau, dich_sang, goc_ma,
                           on_progress=lambda p, m: prog(0.44 + 0.16 * p, m))
        kq["dich"] = {k: v for k, v in dd.items() if k != "ban_dich"}

        # --- bước 4: đọc bản dịch
        prog(0.62, "Đọc bản dịch...")
        tts = doc_ban_dich(dd["ban_dich"], tam_goc / "tts", voice, dich_sang,
                           on_progress=lambda p, m: prog(0.62 + 0.12 * p, m))
        kq["doc"] = {"voice": tts["voice"], "giay": tts["giay"],
                     "so_hong": tts["so_hong"]}

        # --- bước 4b: rút gọn câu dài quá khung (chữa ở CHỮ trước khi ép tốc độ)
        prog(0.74, "Rút gọn câu dài quá khung...")
        rg = rut_gon_vua_khung(cau, dd["ban_dich"], tts, tong,
                               tam_goc / "rutgon", dich_sang, tts["voice"],
                               on_progress=lambda p, m: prog(0.74 + 0.06 * p, m))
        kq["rut_gon"] = {k: v for k, v in rg.items()
                         if k not in ("texts", "files", "ok")}
        # LỜI CUỐI CÙNG app THẬT SỰ đọc lên (sau dịch + rút gọn). Không có mục
        # này thì không cách nào đối chiếu "app ĐỊNH nói gì" với "file phát ra
        # cái gì" — đúng chỗ mù đã để lỗi dịch lệch bậc đi tới tận tai anh Hùng
        # mà mọi cổng vẫn xanh. `doc_nhanh_vua_khung` chỉ đọc lại NHANH HƠN,
        # không đổi một chữ nào, nên đây là lời cuối.
        kq["loi_cuoi"] = list(rg["texts"])

        # --- bước 4c: đọc NHANH lại câu còn dài (thay cho ép atempo méo tiếng)
        prog(0.79, "Đọc nhanh lại câu còn dài quá khung...")
        dn = doc_nhanh_vua_khung(cau, rg["texts"], rg["files"], rg["ok"], tong,
                                 tam_goc / "docnhanh", dich_sang, tts["voice"],
                                 on_progress=lambda p, m: prog(0.79 + 0.01 * p, m))
        kq["doc_nhanh"] = {k: v for k, v in dn.items()
                           if k not in ("files", "ok", "can_truoc", "can_sau")}

        # --- bước 5: khớp thời gian
        prog(0.80, "Khớp thời gian...")
        kh = khop_thoi_gian(cau, dn["files"], dn["ok"], tong,
                            tam_goc / "khop",
                            on_progress=lambda p, m: prog(0.80 + 0.10 * p, m))
        kq["khop"] = {k: v for k, v in kh.items() if k != "manh"}
        if not kh["manh"]:
            raise RuntimeError("Không câu nào khớp được thời gian")

        # --- bước 6: trộn + thay vào video
        prog(0.91, "Trộn tiếng mới với nhạc nền gốc...")
        au = tron_thay_giong(t["nhac"], kh["manh"], tong,
                             tam_goc / "tieng_moi.wav")
        kq["tron"] = au

        prog(0.96, "Ghép tiếng mới vào video..." if not che_chu
             else "Che chữ cháy sẵn rồi ghép tiếng mới vào video...")
        # TÊN NGẮN, KHÔNG nhắc lại tên video: `tam_goc` ĐÃ mang tên video rồi
        # nên ghép thêm stem vào đây là đếm tên hai lần (đo: 183 ký tự cho
        # video tên 60 ký tự, trong khi cả đường chỉ còn 76 ký tự dư tới trần
        # MAX_PATH 260 — anh Hùng đặt thư mục đích sâu hơn một cấp là vỡ).
        # File này chỉ sống trong thư mục tạm; `jobs._thay_giong` chuyển nó
        # sang `<thư mục đích>/<TÊN GỐC>` nên tên ở đây user không bao giờ
        # thấy. Giữ đuôi `__thaygiong` để mọi lượt quét bỏ-qua-bản-đã-làm
        # (`DAU_DA_LAM`) vẫn nhận ra.
        ra = tam_goc / f"ban{DAU_DA_LAM}{video_in.suffix}"
        _cc_log: list = []
        # CHỮ MỚI LẤY MỐC TỪ CHÍNH FILE GIỌNG (`kh["moc_tieng"]` đo bằng
        # silencedetect), KHÔNG lấy `cau[i]["start"]` của bản chép lời gốc.
        # Đây là cả điểm mấu chốt của bản vá: một nguồn mốc duy nhất.
        dong_chu = dong_chu_theo_giong(kh.get("moc_tieng") or [],
                                       rg["texts"]) if viet_chu else []
        kq["chu_theo_giong"] = {"bat": bool(viet_chu),
                                "so_dong": len(dong_chu)}
        thay_audio_video(video_in, au["ra"], ra, che_chu=che_chu,
                         che_chu_cach=che_chu_cach, che_chu_muc=che_chu_muc,
                         che_chu_log=_cc_log, dong_chu=dong_chu)
        kq["che_chu"] = _cc_log[0] if _cc_log else {"bat": False}
        kq["kiem"] = kiem_video_ra(ra, tong)
        kq["ra"] = str(ra)
        kq["ok"] = True
    except HuyBo:
        # HUỶ ≠ LỖI. Nuốt nó thành `ok=False` là job kết thúc 'failed' rồi
        # TỰ THỬ LẠI dù người dùng đã bấm Huỷ (bài học cổng 7).
        raise
    except Exception as e:  # noqa: BLE001
        kq["ok"] = False
        kq["loi"] = f"{type(e).__name__}: {e}"
    kq["giay_tong"] = round(time.time() - t0, 2)
    prog(1.0, "Xong" if kq.get("ok") else f"LỖI: {kq.get('loi', '')[:120]}")
    return kq


# ==================================================================
# NỐI VÀO APP — thư mục video, ĐA LUỒNG, thay gốc AN TOÀN
# ==================================================================

DUOI_VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts", ".flv")

#: Đuôi tên file app tự đặt cho bản ĐÃ thay giọng — quét thư mục phải BỎ QUA
#: nó, không thì lượt sau đi thay giọng của chính bản vừa làm.
DAU_DA_LAM = "__thaygiong"

#: Thư mục làm việc tạm ĐẶT CẠNH video (KHÔNG dùng %TEMP%: file wav/mp3 của
#: một video 10 phút lên hàng trăm MB, và %TEMP% bị dọn định kỳ).
TEN_THU_MUC_TAM = "_thaygiong_tam"

#: Ngôn ngữ đích cho combo UI — nhãn TIẾNG VIỆT, KHÔNG EMOJI. Thứ tự theo
#: thị trường anh Hùng nhắm: Mỹ · Hàn · Nhật · Anh · Đức · Pháp.
NGON_NGU_DICH = (
    ("Tiếng Anh", "en"),
    ("Tiếng Hàn", "ko"),
    ("Tiếng Nhật", "ja"),
    ("Tiếng Đức", "de"),
    ("Tiếng Pháp", "fr"),
    ("Tiếng Trung", "zh"),
    ("Tiếng Tây Ban Nha", "es"),
    ("Tiếng Bồ Đào Nha", "pt"),
    ("Tiếng Thái", "th"),
    ("Tiếng Indonesia", "id"),
    ("Tiếng Việt", "vi"),
)


def liet_ke_video(thu_muc: str | Path) -> list[Path]:
    """Video trong thư mục (bỏ bản đã thay giọng + thư mục tạm/thùng rác).

    MỘT NGUỒN SỰ THẬT cho cả UI (đếm để hiện bảng) và lượt chạy — hai bên đếm
    khác nhau là bảng tiến độ lệch với việc thật.
    """
    p = Path(thu_muc)
    if not p.is_dir():
        return []
    return sorted(f for f in p.iterdir()
                  if f.is_file() and f.suffix.lower() in DUOI_VIDEO
                  and not f.stem.endswith(DAU_DA_LAM))


def chot_co_bo_tach_giong(cach_tach: str = "auto") -> None:
    """CHẶN TRƯỚC: máy chưa có bộ tách giọng thì ném NGAY, đừng chạy dở.

    Vì sao phải chặn ở đây nữa dù `tach_giong` đã ném: không có chốt này thì
    mỗi video vẫn rút audio xong (chục giây/video) rồi mới chết ở bước 1 — 20
    video là 20 lần vô ích, và nhật ký đầy lỗi giống nhau.
    """
    if (cach_tach or "auto").lower().strip() == "nhe":
        return                                  # user CỐ Ý chọn cách nhẹ
    tt = tinh_trang_demucs()
    if not tt["co"]:
        raise RuntimeError(THIEU_DEMUCS)


def thay_giong_mot_video(video_in: str | Path, dich_sang: str = "en",
                         voice: str = "", cach_tach: str = "auto",
                         thay_goc: bool = True, kenh: str = "",
                         thung_rac: str = "", thu_muc_lam: str | Path = "",
                         che_chu: bool = False, che_chu_cach: str = "mo",
                         che_chu_muc: float = 1.0,
                         on_progress: Optional[
                             Callable[[float, str], None]] = None,
                         ) -> dict:
    """MỘT video: 6 bước -> KIỂM file mới -> gốc vào thùng rác -> đặt bản mới.

    Đây là cửa DUY NHẤT của "làm 1 video" — job handler và
    `thay_giong_thu_muc` đều đi qua đây, nên thứ tự an toàn không thể lệch
    giữa hai đường (bài học cổng 19: mẫu-theo-kênh chỉ áp ở dây chuyền, bấm
    tay vẫn ăn cấu hình cũ).

    THỨ TỰ BẮT BUỘC, ĐỪNG ĐỔI: `kiem_video_ra` ĐẠT -> `delete_or_recycle`
    -> mới `shutil.move` bản mới vào chỗ gốc.
    """
    v = Path(video_in)
    r = thay_giong_video(v, dich_sang=dich_sang, voice=voice,
                         cach_tach=cach_tach, thu_muc_lam=thu_muc_lam,
                         che_chu=che_chu, che_chu_cach=che_chu_cach,
                         che_chu_muc=che_chu_muc,
                         on_progress=on_progress)
    if not r.get("ok"):
        return r
    if not thay_goc:
        r["thay_the"] = {"thay": False, "vi_sao": "user chọn GIỮ video gốc"}
        return r
    try:
        r["thay_the"] = thay_the_video_goc(v, r["ra"], kenh, thung_rac)
    except Exception as e:  # noqa: BLE001
        r["thay_the"] = {"thay": False, "vi_sao": str(e)[:300]}
    return r


def _so_luong_mac_dinh() -> int:
    """Số video chạy song song. Demucs ăn ~1,3 GB RAM + nhiều nhân, nên KHÔNG
    chạy nhiều: mặc định 2, ép bằng env `BQ_TG_LUONG`."""
    try:
        n = int((os.environ.get("BQ_TG_LUONG") or "").strip() or 0)
        if n > 0:
            return n
    except ValueError:
        pass
    return 2


def thay_the_video_goc(video_goc: str | Path, video_moi: str | Path,
                       kenh: str = "", thung_rac: str = "") -> dict:
    """ĐƯA GỐC VÀO THÙNG RÁC rồi đặt video mới vào đúng chỗ/tên của nó.

    TUYỆT ĐỐI KHÔNG xoá hẳn (anh Hùng nói "tự xoá" nhưng xoá hẳn là mất video
    vĩnh viễn) và KHÔNG chuyển vào %TEMP% (bị dọn định kỳ = mất). Dùng
    `pipeline.delete_or_recycle`: thùng rác user chọn, không có thì `_DaXoa`
    cạnh thư mục kênh — luôn khôi phục được.

    CHỈ ĐƯỢC GỌI SAU KHI `kiem_video_ra` đã xác nhận file mới hợp lệ.
    """
    from app.core import pipeline as P

    goc = Path(video_goc)
    moi = Path(video_moi)
    if not moi.exists() or moi.stat().st_size < 10240:
        raise RuntimeError("File mới không hợp lệ — KHÔNG đụng tới video gốc")

    action, dst = P.delete_or_recycle(goc, kenh or goc.parent.name,
                                      thung_rac or "")
    if action != "recycled":
        # gốc đang kẹt (Windows còn giữ handle) -> GIỮ NGUYÊN mọi thứ, để lượt
        # sau làm lại. Không được ghi đè lên gốc lúc này.
        return {"thay": False, "vi_sao": "gốc đang kẹt, chưa dọn được",
                "goc_o": str(goc)}
    try:
        shutil.move(str(moi), str(goc))
    except OSError as e:
        # gốc đã vào thùng rác an toàn, chỉ là chưa đặt được file mới vào chỗ.
        return {"thay": False, "vi_sao": f"không đặt được file mới: {e}",
                "goc_da_vao_thung_rac": str(dst), "file_moi_con_o": str(moi)}
    return {"thay": True, "goc_da_vao_thung_rac": str(dst),
            "video_moi": str(goc)}


def thay_giong_thu_muc(thu_muc: str | Path, dich_sang: str = "en",
                       voice: str = "", cach_tach: str = "auto",
                       so_luong: int = 0, thung_rac: str = "",
                       kenh: str = "", thay_goc: bool = True,
                       on_video: Optional[Callable[[str, dict], None]] = None,
                       ) -> dict:
    """Thay giọng CẢ THƯ MỤC video, chạy ĐA LUỒNG, xong thì thay video gốc.

    `thay_goc=False` -> chỉ tạo file mới bên cạnh, KHÔNG đụng gốc (dùng để thử).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    thu_muc = Path(thu_muc)
    # CHẶN TRƯỚC khi đụng video nào: thiếu bộ tách giọng thì ném NGAY.
    chot_co_bo_tach_giong(cach_tach)
    vids = liet_ke_video(thu_muc)
    n = so_luong if so_luong > 0 else _so_luong_mac_dinh()
    lam_goc = thu_muc / TEN_THU_MUC_TAM
    lam_goc.mkdir(parents=True, exist_ok=True)

    ket: list[dict] = []
    t0 = time.time()

    def _mot(v: Path) -> dict:
        return thay_giong_mot_video(
            v, dich_sang=dich_sang, voice=voice, cach_tach=cach_tach,
            thay_goc=thay_goc, kenh=kenh, thung_rac=thung_rac,
            thu_muc_lam=lam_goc / v.stem)

    with ThreadPoolExecutor(max_workers=max(1, n)) as ex:
        fut = {ex.submit(_mot, v): v for v in vids}
        for f in as_completed(fut):
            v = fut[f]
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                r = {"vao": str(v), "ok": False, "loi": str(e)}
            ket.append(r)
            if on_video:
                on_video(str(v), r)

    xong = sum(1 for r in ket if r.get("ok"))
    return {
        "thu_muc": str(thu_muc), "so_video": len(vids),
        "xong": xong, "hong": len(vids) - xong,
        "da_thay_goc": sum(1 for r in ket
                           if (r.get("thay_the") or {}).get("thay")),
        "so_luong": n,
        "giay": round(time.time() - t0, 2),
        "chi_tiet": ket,
    }
