# -*- coding: utf-8 -*-
"""THAY GIỌNG NÓI — thay LỜI THOẠI sang tiếng khác, GIỮ NGUYÊN nhạc + tiếng động.

HAI CÁCH TRỘN, cùng đi 6 bước dưới, KHÁC NHAU ĐÚNG Ở BƯỚC 1 VÀ BƯỚC 6 —
xem `CACH_TRON` và `thay_giong_video(de_giong=...)`:

  · **`"tach"` (MẶC ĐỊNH, hành vi cũ)** — Demucs tách lớp nhạc khỏi lớp giọng,
    **BỎ HẲN** giọng gốc rồi đặt giọng đã dịch vào chỗ trống. Tiếng gốc mất
    hoàn toàn; giá phải trả là cần torch/Demucs (~4,3 GB, nên có GPU) và mọi
    câu bộ chép lời bỏ qua đều thành khoảng TRỐNG (xem `bu_giong_goc`).
  · **`"de"` (đè giọng, KHÔNG tách)** — giữ NGUYÊN tiếng gốc làm nền, chỉ HẠ
    nó xuống rồi ĐÈ giọng lồng lên (voice-over). **Mất tiếng = 0 THEO CẤU
    TẠO**: không bỏ đi gì thì không có gì để mất. Không cần Demucs, không cần
    GPU, không có bước tách nên nhanh hơn hẳn. Đánh đổi: tiếng gốc VẪN NGHE
    ĐƯỢC ở dưới.

**CÙNG MỘT HÀM TRỘN CHO CẢ HAI CÁCH** (`tron_thay_giong`) — chỗ khác nhau chỉ
là *cái gì được truyền vào làm lớp nền*: lớp nhạc Demucs, hay CHÍNH audio gốc.
Đừng viết đường trộn thứ hai: mọi thứ đã đo được ở đó (ducking theo cửa sổ
giọng · cân bằng giọng-nhạc · chuẩn hoá −14 LUFS · trần đỉnh trừ hai lần ·
chốt độ dài) đều dùng lại y nguyên cho cách mới.

SÁU BƯỚC (mỗi bước có hàm riêng, đo được riêng):
  1. `tach_giong`      — tách lớp NHẠC (giữ) khỏi lớp GIỌNG (bỏ). **Cách "de"
                         BỎ HẲN bước này** (không tách thì không cần).
  2. `chep_loi`        — chép lời gốc, có mốc từng từ (dùng `transcribe.py`).
  3. `dich_hau_kiem`   — dịch + DỊCH NGƯỢC tự chấm, câu lệch thì dịch lại.
  4. `doc_ban_dich`    — TTS bản dịch (dùng `dubbing.py`).
  5. `khop_thoi_gian`  — co giãn atempo từng câu về đúng mốc gốc.
  6. `tron_thay_giong` — trộn giọng mới lên lớp NỀN (nhạc đã tách, hoặc chính
                         audio gốc nếu chọn cách "de").

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

#: HAI CÁCH TRỘN TIẾNG — xem docstring đầu file. `"tach"` là hành vi CŨ và là
#: MẶC ĐỊNH; đổi mặc định là đổi tiếng của MỌI video từ nay trên 200-300 kênh
#: đang chạy sản xuất, nên nó phải là một QUYẾT ĐỊNH của anh Hùng sau khi nghe,
#: không phải một dòng mã.
CACH_TRON = ("tach", "de")

#: Nhãn tiếng Việt cho hộp chọn — đặt Ở ĐÂY (cạnh mã) chứ không ở UI: cổng test
#: và nhật ký phải nói cùng một thứ tiếng với cái người dùng thấy, và hai chỗ
#: viết tay hai lần là hai chỗ lệch nhau.
NHAN_CACH_TRON = {
    "tach": "Thay hẳn giọng (tách nhạc) — tiếng gốc MẤT HẲN",
    "de": "Đè giọng (không tách) — giữ nguyên tiếng gốc bên dưới",
}


def chuan_cach_tron(cach: str | None) -> str:
    """CỬA DUY NHẤT chuẩn hoá tên cách trộn. Không nhận ra -> `"tach"`.

    Phải có một cửa: giá trị này tới từ QSettings (người dùng đổi bản), từ
    payload job cũ trong DB, và từ tham số hàm — ba nguồn, và nguồn nào cũng có
    thể mang chuỗi lạ. Không nhận ra thì lùi về **hành vi CŨ**, không phải về
    cách mới: lùi về cái mới là âm thầm đổi tiếng của video người ta.
    """
    c = str(cach or "").strip().lower()
    return c if c in CACH_TRON else "tach"


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


def do_fps(path: str | Path) -> float:
    """Nhịp hình THẬT của nguồn (fps). 0.0 nếu không đọc được.

    Đọc `r_frame_rate` (phân số, vd `2997/125` = 23,976) chứ KHÔNG `avg_frame_
    rate`: nguồn VFR thì avg là số trung bình vô nghĩa, còn trần làm chậm hình
    phải bám nhịp danh định.
    """
    try:
        r = subprocess.run(
            [settings.FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
             str(path)], capture_output=True, text=True,
            creationflags=_CREATE_NO_WINDOW, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return 0.0
    s = (r.stdout or "").strip().split(",")[0]
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            return float(a) / float(b) if float(b) else 0.0
        return float(s)
    except (ValueError, ZeroDivisionError):
        return 0.0


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


#: Chỉ mục wheel của PyTorch. Bản `+cpu` 121,9 MB · bản `+cu126` **2.474,4 MB**
#: (đo bằng HTTP HEAD trên chính wheel, không ước bừa).
CHI_MUC_TORCH_CPU = "https://download.pytorch.org/whl/cpu"
CHI_MUC_TORCH_CUDA = "https://download.pytorch.org/whl/cu126"


def co_gpu_nvidia() -> bool:
    """Máy có GPU NVIDIA DÙNG ĐƯỢC không — hỏi `nvidia-smi`, **KHÔNG import
    torch**.

    Vì sao không hỏi torch: đây là hàm chạy TRONG tiến trình app (đã nạp Qt),
    mà `import torch` ở đó gây ACCESS VIOLATION chứ không phải ném lỗi bắt
    được — xem `thiet_bi_tach`. Và dù có bắt được thì cũng vô nghĩa: torch
    đang cài LÀ BẢN CPU, hỏi nó "có CUDA không" thì đời nào cũng trả False,
    tức đúng vòng luẩn quẩn khiến máy có RTX 3060 mãi mãi tải bản CPU.

    `nvidia-smi` đi kèm driver NVIDIA nên "gọi được + trả về tên GPU" là bằng
    chứng đủ mạnh cho việc CHỌN GÓI TẢI. Nếu đoán nhầm thì hậu quả cũng chỉ
    là tải gói to hơn/nhỏ hơn — `_MA_TACH` vẫn tự quyết định thiết bị bằng
    `torch.cuda.is_available()` lúc chạy, nên KHÔNG BAO GIỜ nổ vì hàm này.

    KHÔNG BAO GIỜ NÉM.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25,
            creationflags=_CREATE_NO_WINDOW)
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except Exception:  # noqa: BLE001
        return False


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

#: Nhãn khi máy CÓ GPU NVIDIA: đường tải là bản CUDA, **2,5 GB** chứ không phải
#: 155 MB (đo bằng HTTP HEAD trên chính wheel: 2.474,4 MB vs 121,9 MB). Ghi
#: 155 MB rồi tải 2,5 GB là đúng lỗi đã mắc một lần theo chiều ngược lại (nhãn
#: nút 155 MB nhưng hộp xác nhận doạ 2 GB). Nói kèm CÁI ĐƯỢC để người dùng tự
#: quyết: đo được tách nhanh 3,15 lần cả lượt (9,28 lần riêng phần tính).
NHAN_TAI_DEMUCS_GPU = ("Tải bộ tách giọng bản GPU (khoảng 2,5 GB — "
                       "tách nhanh hơn ~3 lần)")

#: Nhãn khi `_lib` đã có MỘT PHẦN (vd có demucs, thiếu torch). Ghi "Tải bộ tách
#: giọng" lúc này là nói sai: người dùng tưởng chưa có gì và tưởng phải tải lại
#: từ đầu.
NHAN_CAI_TIEP = "Cài tiếp phần còn thiếu"


def nhan_nut_tai(tt: Optional[dict] = None) -> str:
    """Nhãn ĐÚNG cho nút tải, theo tình trạng `_lib` hiện tại.

    Nhãn phải nói dung lượng của ĐƯỜNG SẼ ĐI, không phải một con số cố định:
    máy có GPU NVIDIA thì `cai_demucs` lấy chỉ mục CUDA (2,5 GB), máy không có
    thì lấy bản CPU (155 MB).
    """
    tt = tt if tt is not None else tinh_trang_demucs()
    thieu = list(tt.get("thieu") or [])
    if thieu and len(thieu) < len(GOI_TACH_GIONG):
        return NHAN_CAI_TIEP + " (" + ", ".join(thieu) + ")"
    return NHAN_TAI_DEMUCS_GPU if co_gpu_nvidia() else NHAN_TAI_DEMUCS

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
        # MÁY CÓ GPU NVIDIA -> LẤY BẢN CUDA (sửa 18/08/2026).
        # Ghi chú cũ ở đây nói "bản CUDA không có gì để đánh đổi" — câu đó
        # đúng với chỗ nó nhìn (wheel PyPI 122,1 MB vs `+cpu` 121,9 MB, cả hai
        # đều KHÔNG kèm gói `nvidia-*`) nhưng nó dẫn tới kết luận SAI, vì trên
        # Windows phần CUDA nằm THẲNG trong wheel của chỉ mục `cu###` chứ
        # không đi qua gói `nvidia-*`. Trỏ vào `cu126` thì có bản CUDA thật.
        #
        # ĐO ĐƯỢC (`_do_demucs_gpu.py`, 3 vòng ĐAN XEN, 60 giây tiếng THẬT,
        # chạy CHÍNH runner của app, khác biệt duy nhất là torch nào được nạp):
        #     apply_model  CPU 25,06s -> GPU  2,70s = NHANH 9,28 lần
        #     cả lượt wall CPU 29,27s -> GPU  9,28s = NHANH 3,15 lần
        #     VRAM đỉnh 1.536/12.288 MiB (Demucs chiếm thêm 893 MiB)
        # CHẤT LƯỢNG KHÔNG ĐỔI, và phải đọc kèm SÀN NHIỄU mới thấy:
        #     GPU vs CPU  lớp nhạc −19,02/−21,54/−21,11 dB
        #     CPU vs CPU  lớp nhạc −19,24/−22,05 dB  <- sàn nhiễu
        # Hai cột TRÙNG DẢI nhau -> lệch đó là NHIỄU của chính Demucs (không
        # tiền định), KHÔNG phải "GPU làm đổi tiếng". Đọc mỗi số −19 dB rồi
        # kết luận là đúng bẫy "số thô là SỐ LỪA".
        #
        # GIÁ: wheel CUDA **2.474,4 MB** so với 121,9 MB (đo bằng HTTP HEAD).
        # Vì vậy CHỈ tải bản CUDA khi máy THẬT SỰ có GPU NVIDIA — máy nhân
        # viên không GPU vẫn lấy đúng gói nhỏ như trước, không đổi một byte.
        #
        # `--extra-index-url` (KHÔNG phải `--index-url`): chỉ mục của pytorch
        # không có `demucs`/`soundfile` nên ép cả lượt vào đó là hỏng phép
        # giải. ĐÃ KIỂM bằng `pip install --dry-run --report`: với chỉ mục
        # cu126 pip chọn đúng `torch==2.13.0+cu126`, với chỉ mục cpu pip chọn
        # `torch==2.13.0+cpu`.
        gpu = co_gpu_nvidia()
        chi_muc = CHI_MUC_TORCH_CUDA if gpu else CHI_MUC_TORCH_CPU
        args = [*pip, "install", "--no-input", "--disable-pip-version-check",
                "--upgrade", "--ignore-installed", "--target", lib,
                "--extra-index-url", chi_muc,
                *GOI_TACH_GIONG]
        # Số ĐO, không phải ước bừa: bản CPU 154,0 MB tải về (cổng 58) · bản
        # CUDA ~2,5 GB. Nói ĐÚNG con số của đường đang đi — nhãn sai là user
        # bấm xong ngồi đợi một lượt tải gấp 16 lần cái mình vừa đọc.
        prog(0.02, ("Máy có GPU NVIDIA — đang tải bộ tách giọng bản CUDA "
                    "(khoảng 2,5 GB, chạy 1 lần, tách nhanh hơn ~3 lần)..."
                    if gpu else
                    "Đang tải bộ tách giọng (khoảng 155 MB, chạy 1 lần)..."))
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
        prog(1.0, "Đã cài xong bộ tách giọng"
                  + (" (bản CUDA — sẽ tách bằng GPU)" if gpu else ""))
        return {"ok": True, "lib": lib, "ma_thoat": 0, "kiem": kiem,
                "goi": goi, "thieu": [], "gpu": gpu, "chi_muc": chi_muc,
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

#: Số vòng dịch LẠI câu còn sót chữ gốc. Vòng nào LLM không đổi được câu nào
#: thì dừng sớm — đốt thêm lượt Groq cho một model đang lặp lại chính nó là vô
#: ích (và 300 kênh thì lượt nào cũng đáng tiền).
CJK_VONG_TOI_DA = 2

#: Dùng `app.ai.dich.dich_va_soat` (dịch theo NGÂN SÁCH THỜI GIAN + thước chấm)
#: thay cho `_dich_loat` ở bước dịch ĐẦU của `dich_hau_kiem`.
#: **MẶC ĐỊNH TẮT — có lý do bằng SỐ, đừng bật nếu chưa đo lại.** Xem khối
#: "THƯỚC CHẤM DỊCH: ĐO XONG, KHÔNG NỐI" trong CLAUDE.md.
#: `BQ_DICH_SOAT=1` bật để đo A/B.
DUNG_DICH_SOAT = os.environ.get("BQ_DICH_SOAT", "") == "1"

#: Dùng `app.ai.dich.dich_theo_gio` — chỉ lấy phần NGÂN SÁCH THỜI GIAN của
#: `dich_va_soat`, **BỎ HẲN hội đồng 3 model chấm điểm** (phần đắt nhất).
#: Đây là hướng còn lại sau khi `DUNG_DICH_SOAT` đã đo và bị bác.
#: `BQ_DICH_GIO=1` bật để đo A/B.
DUNG_DICH_GIO = os.environ.get("BQ_DICH_GIO", "") == "1"


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


#: Ngôn ngữ đích mà chữ CJK/Thái/Lào/Miến/Khmer trong bản dịch là ĐÚNG — với
#: các tiếng này `_has_cjk` kêu là kêu ĐÚNG NGƯỜI, không phải sót.
#: (`recap._CJK_CHARS` gom cả Thái/Lào/Miến/Khmer, xem chú thích ở đó.)
NN_DUNG_CHU_CJK = frozenset({"zh", "ja", "ko", "th", "lo", "my", "km"})

#: Luật ĐI KÈM MỌI prompt dịch. Tách hằng số để 3 chỗ (dịch loạt · dịch lại
#: câu lệch nghĩa · dịch lại câu còn chữ gốc) không bao giờ lệch nhau.
_LUAT_KHONG_SOT = (
    "- TUYỆT ĐỐI KHÔNG để sót chữ của tiếng gốc trong bản dịch: không chữ "
    "Hán, không kana, không hangul. Tên riêng cũng phải chuyển sang chữ của "
    "ngôn ngữ đích.")


def con_chu_goc(text: str, dich_sang: str) -> bool:
    """Bản dịch CÒN SÓT chữ của tiếng gốc (Hán/kana/hangul) không?

    Dùng lại `recap._has_cjk` (đừng viết bộ dò mới — cổng 52 đã hiệu chuẩn nó
    trên corpus thật). Chỉ thêm CỬA NGÔN NGỮ ĐÍCH: dịch SANG tiếng Trung/Nhật/
    Hàn/Thái… thì chữ đó là kết quả ĐÚNG, kêu lên là báo động giả 100%.

    Hàm THUẦN — cổng gọi thẳng được, không cần mạng.
    """
    if ma_ngon_ngu(dich_sang) in NN_DUNG_CHU_CJK:
        return False
    from app.ai import recap
    return recap._has_cjk(str(text or ""))


def _dich_lai_sot(goc: list[str], dich: list[str], dich_sang: str,
                  goc_ma: str) -> list[str]:
    """Dịch LẠI riêng những câu còn sót chữ gốc, prompt siết chặt hơn.

    Khác `_dich_loat`: gửi kèm CHÍNH BẢN DỊCH HỎNG để model thấy nó vừa làm
    sai gì. Trả list cùng độ dài `goc`; câu nào không đòi được thì trả lại
    đúng bản cũ (KHÔNG bịa, không xoá — caller còn đếm để báo cáo).
    """
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = [f'#{i} GỐC ({_ten_nn(goc_ma)}): "{g[:300]}"\n'
             f'   BẢN DỊCH HỎNG (còn chữ gốc): "{d[:300]}"'
             for i, (g, d) in enumerate(zip(goc, dich))]
    system = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. CHỈ trả JSON "
              "thuần.")
    prompt = (
        f"Những bản dịch dưới đây BỊ LỖI: vẫn còn nguyên chữ của tiếng gốc "
        f"nên người xem {ten_dich} không đọc/nghe được. Hãy dịch LẠI cho "
        "đúng.\n"
        f"{chr(10).join(items)}\n\n"
        "QUY TẮC:\n"
        f"- Dịch TOÀN BỘ sang {ten_dich}, văn NÓI tự nhiên.\n"
        + _LUAT_KHONG_SOT + "\n"
        "- Bản dịch phải dài xấp xỉ câu gốc, không thêm chú thích.\n"
        f"- Trả MẢNG JSON {len(goc)} đối tượng "
        '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
        "BẮT BUỘC đủ MỌI số #."
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001
        return list(dich)
    bang = _theo_nhan(data, list(range(len(goc))), "t")
    ra = list(dich)
    for i in range(len(goc)):
        t = bang.get(i)
        if isinstance(t, str) and t.strip():
            ra[i] = t.strip()
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
            f"- Dịch sang {ten_dich}, văn NÓI tự nhiên — viết như người thật "
            "đang NÓI trong video, KHÔNG dịch máy móc từng chữ.\n"
            "- Giữ giọng điệu của câu gốc (kể chuyện, giới thiệu, cảm thán).\n"
            "- ĐỌC LÊN phải lọt khung [số giây] của câu đó — dài quá thì lược "
            "từ đệm, GIỮ Ý CHÍNH.\n"
            "- KHÔNG thêm chú thích, không phiên âm.\n"
            + _LUAT_KHONG_SOT + "\n"
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
    if DUNG_DICH_SOAT:
        from app.ai import dich as _D
        ban_dich = list(_D.dich_va_soat(cau, dich_sang, goc_ma)["ban_dich"])
    elif DUNG_DICH_GIO:
        # NGÂN SÁCH THỜI GIAN, KHÔNG kèm thước chấm (bỏ hội đồng 3 model).
        from app.ai import dich as _D
        ban_dich = list(_D.dich_theo_gio(cau, dich_sang, goc_ma)["ban_dich"])
    else:
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

    # --- HẬU KIỂM CHỮ GỐC CÒN SÓT (lỗi anh Hùng: "còn có cả tiếng Trung
    # không hiểu"). Phải làm SAU vòng dịch-lại-theo-nghĩa: vòng đó có thể tự
    # đẻ ra câu sót mới, và cũng có thể chữa hộ vài câu.
    sot_dau = [i for i, t in enumerate(ban_dich)
               if con_chu_goc(t, dich_sang)]
    sot = list(sot_dau)
    for _ in range(CJK_VONG_TOI_DA):
        if not sot:
            break
        if on_progress:
            on_progress(0.9, f"Dịch lại {len(sot)} câu còn sót chữ gốc...")
        lai = _dich_lai_sot([goc_txt[i] for i in sot],
                            [ban_dich[i] for i in sot], dich_sang, goc_ma)
        doi = 0
        for j, i in enumerate(sot):
            # CHỈ NHẬN khi bản mới thật sự SẠCH — nhận bừa là đổi một câu sót
            # lấy một câu sót khác rồi tự khen đã chữa (cùng luật "chỉ nhận
            # bản rút gọn khi nó NGẮN HƠN thật" của bước 4b).
            if lai[j] != ban_dich[i] and not con_chu_goc(lai[j], dich_sang):
                ban_dich[i] = lai[j]
                doi += 1
        sot = [i for i in sot if con_chu_goc(ban_dich[i], dich_sang)]
        if not doi:
            break                    # LLM không nhúc nhích -> đừng đốt lượt
    # CÒN SÓT THÌ NÓI RA, KHÔNG GIẤU: câu này sẽ được giọng đích đọc nguyên
    # chữ Hán = đúng cái anh Hùng nghe thấy. Không tự ý xoá (xoá là mất câu,
    # thành "chỗ có chỗ không").
    con_sot = [i for i in range(len(ban_dich))
               if con_chu_goc(ban_dich[i], dich_sang)]

    con_xau = sum(1 for d in diem if d < nguong)
    if on_progress:
        on_progress(1.0, "Dịch xong")
    return {
        "ban_dich": ban_dich,
        "sot_chu_goc_truoc": len(sot_dau),
        "sot_chu_goc_sau": len(con_sot),
        "sot_chu_goc_cau": con_sot[:20],
        "ty_le_sot_truoc": round(100.0 * len(sot_dau) / max(1, len(cau)), 1),
        "ty_le_sot_sau": round(100.0 * len(con_sot) / max(1, len(cau)), 1),
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


# ==================================================================
# BIẾN THỂ GIỌNG — edge-tts chỉ có 2 giọng Việt, `pitch` sinh thêm
# ==================================================================
# edge-tts cho tiếng Việt có ĐÚNG 2 giọng: `vi-VN-NamMinhNeural` (nam) và
# `vi-VN-HoaiMyNeural` (nữ). 200-300 kênh dùng chung 2 giọng thì kênh nào cũng
# kêu giống nhau. `pitch` sinh thêm biến thể mà **KHÔNG tốn thêm một lượt mạng
# nào** — cùng một lời gọi `Communicate`, chỉ thêm tham số.
#
# CÁCH MÃ HOÁ: `"<voice>|<pitch>"`, ví dụ `"vi-VN-NamMinhNeural|-20Hz"`.
# Chọn dấu `|` vì id giọng edge-tts KHÔNG BAO GIỜ chứa nó, nên chuỗi cũ
# (không có `|`) đi qua `tach_giong_pitch` ra Y NGUYÊN + `"+0Hz"`, mà
# `_synth_all_words` coi `"+0Hz"` là KHÔNG truyền `pitch` -> mẫu đã lưu, job
# đã nằm trong DB và mọi lối gọi chưa nối đều chạy y hệt trước, không đổi một
# ký tự nào.
_SEP_PITCH = "|"
_RE_PITCH = re.compile(r"[+-]\d{1,3}Hz")


def tach_giong_pitch(voice: str) -> tuple[str, str]:
    """`"vi-VN-NamMinhNeural|-20Hz"` -> `("vi-VN-NamMinhNeural", "-20Hz")`.

    Chuỗi KHÔNG có `|` -> trả nguyên vẹn kèm `"+0Hz"` (đường cũ, không đổi).
    Mã pitch LẠ (user sửa tay mẫu / file mẫu hỏng) -> BỎ phần pitch chứ
    KHÔNG ném: mất một biến thể còn hơn chết cả lượt thay giọng.

    **CHATTERBOX DÙNG `|` CHO VIỆC KHÁC — PHẢI CHỪA RA (lỗi thật, v2.38.0).**
    Mã của nó là `cb:<lang>|<đường dẫn mẫu>`. Luật "pitch lạ thì BỎ" ở trên
    biến `cb:en|D:\\mau.wav` thành `("cb:en", "+0Hz")` -> **đường dẫn mẫu bị
    vứt IM LẶNG** -> `giong_chatter.tach_ma("cb:en")` trả `("","")` -> lùi
    edge-tts. Tức anh Hùng chọn giọng nhân bản của kênh mình, nghe ra Hoài My,
    và **không một dòng báo** — đúng họ lỗi "chọn X ra Y" mà `ov:nu_am` đã
    sập. Chừa Ở ĐÂY chứ không nới `_RE_PITCH`: luật "pitch lạ thì bỏ" vẫn
    đúng và cổng 63 CA 1e vẫn chấm nó y nguyên.
    """
    s = str(voice or "")
    if _SEP_PITCH not in s:
        return s, "+0Hz"
    from app.core import giong_chatter as _gc
    if _gc.la_giong_chatter(s):
        return s, "+0Hz"
    v, _, p = s.partition(_SEP_PITCH)
    p = p.strip()
    return v.strip(), (p if _RE_PITCH.fullmatch(p) else "+0Hz")


def ma_bien_the(voice: str, pitch: str) -> str:
    """Ghép ngược: `("vi-VN-NamMinhNeural", "-20Hz")` -> mã lưu vào mẫu.

    `"+0Hz"` KHÔNG ghép hậu tố — giọng gốc phải giữ ĐÚNG chuỗi cũ để mẫu đã
    lưu và mã sinh mới trùng nhau từng ký tự.
    """
    p = str(pitch or "+0Hz").strip()
    if p == "+0Hz" or not _RE_PITCH.fullmatch(p):
        return str(voice or "")
    return f"{voice}{_SEP_PITCH}{p}"


# ================== BẢNG BIẾN THỂ — LẤY TỪ SỐ ĐO ==================
# `_do_bien_the_giong.py` (16/08/2026): 2 giọng × 9 mức pitch × 10 câu THẬT
# (lấy từ corpus bản dịch của anh Hùng), mỗi file cho **Groq CHÉP NGƯỢC rồi
# ĐẾM TỪ SAI**, cộng **F0 trung vị** đo bằng tự tương quan trên sóng.
# Mốc so sánh là `+0Hz` CỦA CHÍNH GIỌNG ĐÓ (edge-tts + Groq vốn đã có sai số
# nền ~5-7%, so với 0 tuyệt đối là kết luận sai).
#
#   Nam Minh (mốc F0 146,0 Hz · sai từ nền 7,08%)
#     -40Hz 107,2 Hz  6,19% (−0,88)      +10Hz 155,8 Hz  6,19% (−0,88)
#     -30Hz 116,2 Hz  7,96% (+0,88)      +20Hz 166,3 Hz  7,96% (+0,88)
#     -20Hz 127,0 Hz  7,08% (+0,00)      +30Hz 175,1 Hz  7,08% (+0,00)
#     -10Hz 135,6 Hz  7,08% (+0,00)      +40Hz 184,5 Hz  6,19% (−0,88)
#   Hoài My (mốc F0 225,1 Hz · sai từ nền 5,31%)
#     -40Hz 165,7 Hz  8,85% (+3,54) LOẠI +10Hz 240,1 Hz  7,08% (+1,77)
#     -30Hz 180,2 Hz  7,96% (+2,65)      +20Hz 254,6 Hz  7,96% (+2,65)
#     -20Hz 195,4 Hz  7,96% (+2,65)      +30Hz 269,4 Hz  7,96% (+2,65)
#     -10Hz 210,1 Hz  5,31% (+0,00)      +40Hz 281,9 Hz  9,73% (+4,42) LOẠI
#
# ĐỌC BẢNG NÀY CHO ĐÚNG:
# · **KHÔNG có biến thể GIẢ**: bước F0 ~10 Hz (nam) / ~15 Hz (nữ), trên
#   ngưỡng phân biệt cao độ của tai người (~3-5%) -> mức nào cũng khác thật.
# · Cửa "sai từ" **LOẠI đúng 2/18**: Hoài My ±40Hz. Tức nó không phải con
#   dấu, nhưng cũng **THÔ**: 113 từ nên 1 từ sai = 0,88 điểm %, dải nhiễu
#   ±1 điểm. Đừng đọc chênh lệch dưới 1 điểm thành ý nghĩa gì.
#
# ==== VÌ SAO BẢNG DƯỚI CHỈ ±20Hz TRONG KHI SỐ ĐO CHO TỚI ±30/±40 ====
# **KHÔNG phải vì con số** — mà vì con số đó ĐO SAI THỨ. "Groq chép đúng
# chữ" là ĐỌC RÕ, KHÔNG PHẢI NGHE TỰ NHIÊN. Một giọng đẩy xuống 107 Hz hay
# lên 282 Hz vẫn có thể chép đúng 100% mà tai người nghe ra "giọng máy /
# giọng chuột". **Tôi không có tai, nên tôi không được phép nói mức nào nghe
# được.** Đây đúng họ bẫy repo đã dính: *số đo bảo dải chữ đã sạch mà mắt
# vẫn đọc ra chữ* (cổng 56b).
# Nên bảng ship ±20Hz — vùng còn cách xa cửa loại ở CẢ HAI giọng (Δ sai từ
# lớn nhất +2,65 so với mức loại +3,54). Muốn mở tới ±30Hz thì **phải NGHE
# trước**: `_do_bien_the_giong.py` để sẵn file ở `_do_bt_giong/`.
#: `{voice edge-tts: ((pitch, nhãn tiếng Việt), ...)}` — nhãn KHÔNG EMOJI.
BIEN_THE_PITCH: dict[str, tuple[tuple[str, str], ...]] = {
    "vi-VN-NamMinhNeural": (
        ("-20Hz", "Nam Minh — trầm"),
        ("-10Hz", "Nam Minh — hơi trầm"),
        ("+0Hz", "Nam Minh — giọng gốc"),
        ("+10Hz", "Nam Minh — hơi cao"),
        ("+20Hz", "Nam Minh — cao"),
    ),
    "vi-VN-HoaiMyNeural": (
        ("-20Hz", "Hoài My — trầm"),
        ("-10Hz", "Hoài My — hơi trầm"),
        ("+0Hz", "Hoài My — giọng gốc"),
        ("+10Hz", "Hoài My — hơi cao"),
        ("+20Hz", "Hoài My — cao"),
    ),
}


def bien_the_giong(voice: str = "") -> list[tuple[str, str]]:
    """Danh sách `[(mã lưu vào mẫu, nhãn tiếng Việt)]` cho combo giao diện.

    `voice` rỗng -> trả biến thể của MỌI giọng có bảng. Giọng không có bảng
    (mọi giọng không phải tiếng Việt) -> trả `[]`, combo giữ nguyên như cũ.
    """
    ten = tach_giong_pitch(voice)[0] if voice else ""
    ra: list[tuple[str, str]] = []
    for v, bang in BIEN_THE_PITCH.items():
        if ten and v != ten:
            continue
        for p, nhan in bang:
            ra.append((ma_bien_the(v, p), nhan))
    return ra


#: Câu mẫu NGHE THỬ **TIẾNG VIỆT**. Có dấu thanh đủ 6 kiểu, để nghe ra ngay
#: giọng nào nuốt dấu (Piper `vais1000` từng bị chê thiếu dấu ở giọng khác).
CAU_NGHE_THU = "Xin chào anh Hùng, đây là giọng đọc thử của kênh mình nhé."


def cau_nghe_thu(nn: str = "") -> str:
    """Câu mẫu nghe thử **ĐÚNG NGÔN NGỮ** `nn`. Không có câu -> chuỗi RỖNG.

    ═══ VÌ SAO HÀM NÀY PHẢI CÓ (lỗi anh Hùng gặp 19/08/2026) ═══
    Anh Hùng: *"cái phần nghe thử chọn tiếng Anh ngôn ngữ đó cứ ra tiếng Việt
    lung ta lung tung"*. `doc_thu` bản trước dùng **một câu tiếng Việt CỐ
    ĐỊNH** cho mọi giọng, nên chọn giọng tiếng Anh là nghe giọng Anh cố đọc
    chữ Việt — ra tiếng lạ, mà người nghe lại đọc thành "giọng này hỏng".
    Trong khi cửa nghe thử CŨ (`dubbing.synth_demo`, hộp Lồng tiếng) đã chọn
    câu theo ngôn ngữ của giọng từ lâu; **chỉ đường Thay giọng bị sót**.

    ═══ NGUỒN CÂU: `dubbing._DEMO_TEXTS`, KHÔNG ĐẺ BẢNG THỨ HAI ═══
    Hai bảng câu mẫu là hai chỗ để lệch nhau: sửa một chỗ thì nghe thử ở hộp
    này và hộp kia đọc hai câu khác nhau mà không ai biết vì sao. Tiếng Việt
    cố ý dùng `CAU_NGHE_THU` (câu quen của anh Hùng, đủ 6 dấu thanh).

    **KHÔNG lùi về câu tiếng Anh ở đây** — trả RỖNG để nơi gọi tự quyết và
    NÓI RA là nó đang lùi (`_cau_doc_thu.py` đã ghi đúng cái bẫy này: lùi câu
    tiếng Anh cho tiếng khác thì phép nghe/đo vẫn "chạy" nhưng chứng nhận sai
    thứ — nó chứng nhận "giọng đọc được chữ Latin").
    """
    from app.core import dubbing
    ma = dubbing.norm_lang(str(nn or "").strip()) if str(nn or "").strip() else ""
    if not ma:
        return ""
    if ma == "vi":
        return CAU_NGHE_THU
    return str(dubbing._DEMO_TEXTS.get(ma) or "")    # noqa: SLF001


def nn_cua_giong(voice: str) -> str:
    """Ngôn ngữ mà GIỌNG NÀY đọc được. `""` = đa ngữ / không biết.

    Dùng để chọn câu mẫu khi nơi gọi KHÔNG truyền ngôn ngữ đích, và để biết
    khi nào phải BÁO "giọng này không đọc được tiếng đó".

    Trả `""` thay vì đoán bừa là cố ý: đoán sai thì câu mẫu sai ngôn ngữ, mà
    đó chính là lỗi đang đi chữa. `""` -> nơi gọi lùi về hành vi cũ (câu Việt)
    chứ không phát chứng nhận nào.
    """
    v = str(voice or "").strip()
    if not v:
        return ""
    if v.startswith(("el:", "gemini:", "ov:", "ix:", "cb:")):
        return ""                   # đa ngữ (hoặc chưa đo) -> không kết luận
    if v.startswith("vbee:"):
        return "vi"
    if v.startswith("piper:"):
        # `piper:vi_VN-vais1000-medium` -> `vi`. Piper đặt tên model theo
        # `<lang>_<REGION>-...` nên phần trước `_` là mã ngôn ngữ.
        ten = v.split(":", 1)[1]
        return ten.split("_", 1)[0].strip().lower() or ""
    from app.core import giong_vieneu as _vn
    if _vn.la_giong_vieneu(v):
        # `vn:Adam` là giọng TIẾNG ANH duy nhất của bộ VieNeu (19 giọng còn
        # lại là giọng Việt) — bảng `GIONG_TIENG_ANH` là NGUỒN DUY NHẤT, đừng
        # ghi tên giọng ra đây lần thứ hai.
        if _vn.ten_giong(v) in _vn.GIONG_TIENG_ANH:
            return "en"
        return "vi"                 # kể cả giọng NHÂN BẢN: model là model Việt
    from app.core import dubbing
    # edge-tts: `vi-VN-HoaiMyNeural` -> `vi`. Có thể mang hậu tố `|<pitch>`
    # nhưng nơi gọi đã tách; cứ chặn thêm cho chắc.
    dau = v.split(_SEP_PITCH, 1)[0].split("-", 1)[0].strip().lower()
    return dubbing.norm_lang(dau) if len(dau) in (2, 3) else ""


def doc_thu(voice: str, out_wav: str | Path, text: str = "",
            dung_cache: bool = True, nn: str = "") -> dict:
    """Đọc MỘT câu mẫu bằng **đúng giọng + đúng biến thể cao độ** đang chọn.

    **ĐI ĐÚNG CỬA MÀ LƯỢT XUẤT THẬT ĐI** (`dubbing._synth_all_words`, y hệt
    `doc_ban_dich`) — không dựng đường riêng cho nút nghe thử. Nghe thử mà đi
    cửa khác thì nó hết là *nghe thử*: anh Hùng nghe một đằng, video ra một
    nẻo. Nhờ đi cửa chung, nút này tự hưởng luôn nhánh rẽ Piper
    (`_piper_hay_khong`) và phần tách `|<pitch>` mà không phải chép lại luật.

    Trả `{"ra", "nguon", "cache", "loi", "canh_bao", "nn", "cau"}` — `nguon` là
    NGUỒN GIỌNG THẬT SỰ đã đọc (`edge-tts` / `piper` / `elevenlabs`), **KHÔNG
    phải cái người dùng chọn**: Piper chưa tải thì app LÙI ÊM về edge-tts, mà
    lùi êm không nói ra thì người nghe tưởng đang nghe Piper rồi chọn nhầm cho
    cả 300 kênh.

    ═══ `nn` = NGÔN NGỮ ĐÍCH, và vì sao nó phải là THAM SỐ ═══
    Câu mẫu đi theo `nn` (xem `cau_nghe_thu`). `nn` rỗng -> suy từ CHÍNH GIỌNG
    (`nn_cua_giong`), nên lối gọi cũ **không phải sửa** mà vẫn hết bệnh "giọng
    tiếng Anh đọc câu tiếng Việt".
    **KHÔNG đọc ngôn ngữ đích từ QSettings** dù làm vậy thì khỏi sửa nơi gọi:
    hộp thoại chỉ ghi cài đặt lúc Chạy/đóng, nên đọc setting là đọc lựa chọn
    CŨ — đúng lỗi "chạy dây chuyền lấy nhóm từ setting nên chạy sai nhóm" đã
    sập một lần. Trạng thái đang hiện nằm ở WIDGET, phải truyền vào.

    ═══ GIỌNG KHÔNG ĐỌC ĐƯỢC TIẾNG ĐÓ THÌ **BÁO**, KHÔNG ĐỌC BỪA ═══
    `vn:` (trừ `Adam`) · `piper:vais1000` · `vbee:` chỉ đọc được tiếng Việt;
    `vn:Adam` và giọng `en-*` là giọng tiếng Anh. Bắt chúng đọc tiếng khác thì
    ra tiếng lạ **và người nghe sẽ kết luận là giọng hỏng** — nên `canh_bao`
    nói thẳng ra. Vẫn ĐỌC (không chặn): đó đúng là thứ lượt xuất thật sẽ ra
    nếu anh Hùng giữ lựa chọn này, nghe được thì mới quyết được.

    `dung_cache=True`: cùng (giọng · pitch · câu) thì dùng lại file cũ. Bấm
    liên tiếp KHÔNG gọi lại mạng — với ElevenLabs mỗi lượt gọi là tốn credit
    thật, còn edge-tts thì đỡ 1-2 giây chờ. Câu mẫu nằm TRONG khoá cache nên
    đổi ngôn ngữ là tự sinh file mới, không trả file tiếng cũ.
    """
    import hashlib

    import config
    from app.core import dubbing

    out_wav = Path(out_wav)
    v, pitch = tach_giong_pitch(voice or "")
    if not v:
        return {"ra": "", "nguon": "", "cache": False, "canh_bao": "",
                "nn": "", "cau": "", "loi": "Chưa chọn giọng"}

    # ---- CHỌN CÂU MẪU THEO NGÔN NGỮ (ngôn ngữ đích > ngôn ngữ của giọng) ----
    nn_dich = dubbing.norm_lang(str(nn).strip()) if str(nn or "").strip() else ""
    nn_giong = nn_cua_giong(v)
    nn_cau = nn_dich or nn_giong or "vi"
    canh_bao = ""
    txt = (text or "").strip()
    if not txt:
        txt = cau_nghe_thu(nn_cau)
        if not txt:
            # Ngôn ngữ chưa có câu mẫu -> LÙI câu tiếng Anh nhưng NÓI RA.
            txt = cau_nghe_thu("en") or CAU_NGHE_THU
            canh_bao = (f"chưa có câu mẫu tiếng «{nn_cau}» nên đang đọc câu "
                        f"TIẾNG ANH")
            nn_cau = "en"
    if nn_giong and nn_cau != nn_giong:
        # Giọng đọc tiếng A mà câu là tiếng B. Nói CẢ HAI vế + nói phải làm gì.
        canh_bao = (
            f"giọng này đọc tiếng «{nn_giong}», còn câu mẫu là tiếng "
            f"«{nn_cau}» (ngôn ngữ đích) — nghe lạ là ĐÚNG theo cấu tạo, "
            f"KHÔNG phải giọng hỏng. Muốn nghe đúng thì chọn giọng của tiếng "
            f"«{nn_cau}»" + (f"; {canh_bao}" if canh_bao else ""))

    # Đọc `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số: cổng test trỏ
    # `BQ_DATA_DIR` sang thư mục tạm, cất sẵn là ghi vào DATA_DIR THẬT.
    kho = Path(config.DATA_DIR) / "_nghe_thu"
    kho.mkdir(parents=True, exist_ok=True)
    khoa = hashlib.sha1(f"{v}|{pitch}|{txt}".encode("utf-8")).hexdigest()[:16]
    cache = kho / f"{khoa}.wav"

    # NGUỒN THẬT: hỏi trước khi đọc, vì `_piper_hay_khong` có thể lùi về edge.
    nguon = "edge-tts"
    if v.startswith("el:"):
        nguon = "elevenlabs"
    elif v.startswith("gemini:"):
        nguon = "gemini"
    else:
        try:
            from app.core import piper_tts
            if piper_tts.la_giong_piper(v):
                nguon = "piper" if piper_tts.co_piper() else (
                    "edge-tts (Piper chưa tải nên lùi về giọng thường)")
        except Exception:  # noqa: BLE001
            pass

    ra_chung = {"nguon": nguon, "canh_bao": canh_bao, "nn": nn_cau, "cau": txt}

    if dung_cache and cache.exists() and cache.stat().st_size > 1024:
        shutil.copyfile(cache, out_wav)
        return {"ra": str(out_wav), "cache": True, "loi": "", **ra_chung}

    tam = out_wav.with_suffix(".tho.mp3")
    thu_muc = out_wav.parent / f"_thu_{khoa}"
    try:
        if v.startswith(("el:", "gemini:")):
            # Hai nguồn này KHÔNG đi qua đường thay tiếng — `giong_dung_duoc`
            # lọc chúng khỏi combo vì `doc_ban_dich` không đọc được. Giữ nhánh
            # cho lối gọi khác (hộp Lồng tiếng đã dùng `synth_demo` sẵn).
            from app.core.dubbing import synth_demo
            if not synth_demo(v, tam, text=txt, pitch=pitch):
                raise RuntimeError("nguồn giọng không trả về tiếng")
            nguon_file = tam
        else:
            # ĐI THẲNG QUA `doc_ban_dich` — ĐÚNG BƯỚC 4 của lượt xuất thật,
            # KHÔNG tự gọi `_synth_all_words`. Ba cái lợi, cái thứ ba là lý do
            # quyết định:
            #  (1) nó tự `tach_giong_pitch` -> biến thể cao độ chắc chắn đúng;
            #  (2) nó tự CẮT LỀ IM (edge-tts chèn ~1,07 s im mỗi câu) -> bấm
            #      là kêu ngay, không phải ngồi đợi khoảng lặng;
            #  (3) **KHÔNG đẻ ra chỗ gọi `_synth_all_words` thứ 4.** Cổng 63
            #      đếm đúng 3 chỗ và cố ý ĐỎ khi có chỗ thứ 4, để bắt người
            #      thêm phải nối `pitch`. Đi qua cửa CẤP TRÊN vừa khỏi đụng
            #      chốt đó, vừa đúng tinh thần của nó — và không phải sửa một
            #      con số nào trong cổng.
            # `dich_sang=nn_cau`: cửa chung dùng nó để chọn giọng LÙI khi giọng
            # đang chọn hỏng (`default_voice`) và để gióng hàng đúng ngôn ngữ.
            # Bản trước để mặc định `"en"` -> nghe thử câu TIẾNG VIỆT mà giọng
            # hỏng thì lùi sang giọng TIẾNG ANH đọc chữ Việt = đúng cái bệnh
            # đang chữa, chỉ khác đường vào.
            kq_d = doc_ban_dich([txt], thu_muc, voice=voice, dich_sang=nn_cau)
            if not kq_d.get("ok") or not kq_d["ok"][0]:
                raise RuntimeError("nguồn giọng không trả về tiếng")
            ds = [p for p in (kq_d.get("files") or []) if p]
            if not ds:
                raise RuntimeError("không có file tiếng nào ra")
            nguon_file = Path(ds[0])
        # -> WAV: `winsound` của giao diện CHỈ phát được WAV.
        _ffmpeg(["-i", str(nguon_file), "-ac", "1", "-ar", "24000",
                 "-c:a", "pcm_s16le", str(out_wav)], "đổi tiếng thử ra wav")
        _kiem_wav(out_wav)          # bẫy "rc=0 mà file 0 KiB / RMS 0"
        if dung_cache:
            shutil.copyfile(out_wav, cache)
        return {"ra": str(out_wav), "cache": False, "loi": "", **ra_chung}
    except Exception as e:  # noqa: BLE001
        return {"ra": "", "cache": False, "loi": str(e), **ra_chung}
    finally:
        Path(tam).unlink(missing_ok=True)
        # Qua cửa chung (cổng 80): `thu_muc` = `out_wav.parent / f"_thu_{khoa}"`
        # nên hôm nay KHÔNG thể ra `.` — nhưng đó là tính chất của NƠI GỌI,
        # không phải chốt của chỗ xoá, và `out_wav` đến từ tham số. Đòi thêm
        # tiền tố `_thu_` (tên do chính hàm này đặt) cho khỏi phải tin vào may.
        from app.core.xoa_an_toan import don_thu_muc
        don_thu_muc(thu_muc, ten_bat_dau="_thu_")


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
    # THU LUÔN MỐC TỪNG-TỪ (WordBoundary). Cùng một lượt gọi edge-tts, KHÔNG
    # tốn thêm giây mạng nào — `_synth_all_words` chỉ đọc thêm loại chunk mà
    # server vẫn gửi. Đây là hạ tầng app đã có sẵn cho phụ đề recap; đường
    # THAY TIẾNG trước nay vứt nó đi rồi đổ cả cụm 3 dòng ra một lúc.
    # BIẾN THỂ GIỌNG: `voice` có thể mang hậu tố `|<pitch>`. Phải tách ở CẢ 3
    # chỗ gọi TTS của file này (đây · `rut_gon_vua_khung` · `doc_nhanh_vua_
    # khung`) — sót một chỗ thì câu đi qua chỗ đó đọc bằng cao độ GỐC, ra
    # video lẫn hai giọng mà rc vẫn 0, không một dòng báo.
    _v, _pitch = tach_giong_pitch(voice)
    # `lang` để cửa chung biết lùi về giọng edge-tts NÀO nếu giọng trả phí
    # (ElevenLabs) hỏng/hết credit. Lượt đọc ĐẦU nên `el_lui` giữ mặc định
    # True: chưa có gì trong tay, lùi cả track sang edge vẫn ra video ĐÚNG.
    ok, moc_tu = asyncio.run(
        dubbing._synth_all_words(texts, _v, paths, on_done=_done,
                                 pitch=_pitch, lang=dich_sang))
    # CẮT LỀ IM NGAY TẠI ĐÂY, trước khi bất kỳ ai đo độ dài câu: mọi bước sau
    # (rút gọn, khớp thời gian) phải nhìn thấy ĐỘ DÀI TIẾNG THẬT, không phải
    # độ dài file có kèm ~1,07 s im lặng của edge-tts.
    if on_progress:
        on_progress(0.95, "Cắt lề im lặng đầu/cuối câu...")
    sach, le = cat_le_loat(paths, list(ok), out_dir / "sach", moc_tu=moc_tu)
    return {
        "files": sach, "files_tho": paths, "ok": list(ok), "voice": voice,
        "giay": round(time.time() - t0, 2),
        "so_hong": sum(1 for x in ok if not x),
        "cat_le": le,
        "moc_tu": moc_tu,
        "so_cau_co_moc": sum(1 for m in moc_tu if m),
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
    """Cắt lề im lặng hai đầu file TTS -> wav. Trả độ dài THẬT sau khi cắt."""
    return cat_le_im_moc(src, dst, nguong_db)[0]


def cat_le_im_moc(src: str | Path, dst: str | Path,
                  nguong_db: float = NGUONG_IM_DB) -> tuple[float, float]:
    """Như `cat_le_im` nhưng trả THÊM số giây đã cắt Ở ĐẦU.

    Trả `(độ dài sau cắt, giây cắt đầu)`.

    **VÌ SAO CẦN SỐ THỨ HAI:** mốc WordBoundary của edge-tts đo trên file mp3
    GỐC. Cắt mất `a` giây đầu rồi mà không trừ lại thì MỌI mốc từ lệch đúng
    `a` giây (đo được 0,16-0,20 s — đủ để chữ chạy trước tiếng thấy rõ). Đây
    là chỗ duy nhất biết `a`, nên nó phải nói ra chứ không nuốt.

    KHÔNG BAO GIỜ trả file rỗng: đo hỏng, hoặc cắt xong còn dưới 0,08 giây
    (câu chỉ có tiếng thở / TTS hỏng) -> giữ NGUYÊN bản gốc, và khi đó giây
    cắt đầu là **0,0** (phải trả đúng 0, không phải `a` dự kiến — trả số dự
    kiến là dời mốc của một phép cắt KHÔNG XẢY RA).
    """
    src, dst = Path(src), Path(dst)
    dau, cuoi, tong = do_le_im(src, nguong_db)
    a = max(0.0, dau - GIU_DAU)
    b = max(a + 0.01, tong - max(0.0, cuoi - GIU_CUOI))
    af = ["aresample=44100"]
    da_cat = 0.0
    if tong > 0 and (a > 0.005 or b < tong - 0.005) and (b - a) >= 0.08:
        af.append(f"atrim=start={a:.3f}:end={b:.3f}")
        af.append("asetpts=N/SR/TB")
        da_cat = a
    _ffmpeg(["-i", str(src), "-af", ",".join(af), "-ac", "1", "-ar", "44100",
             "-c:a", "pcm_s16le", str(dst)], f"cắt lề im {src.name}")
    d = probe_duration(dst)
    if d < 0.05:                       # cắt hụt -> quay về bản chưa cắt
        _ffmpeg(["-i", str(src), "-af", "aresample=44100", "-ac", "1",
                 "-ar", "44100", "-c:a", "pcm_s16le", str(dst)],
                f"giữ nguyên {src.name}")
        d = probe_duration(dst)
        da_cat = 0.0
    return d, da_cat


def doi_moc_tu(moc: list, tru: float, dai: float = 0.0) -> list:
    """Dời mốc từng-từ về sau khi CẮT `tru` giây ở đầu file. Hàm THUẦN.

    Mốc âm (từ nằm trọn trong phần vừa cắt — không xảy ra với lề IM nhưng cứ
    chặn) bị kẹp về 0; kẹp trần theo `dai` nếu có.
    """
    ra = []
    for m in moc or ():
        try:
            a, b, w = float(m[0]) - tru, float(m[1]) - tru, m[2]
        except (TypeError, ValueError, IndexError):
            continue
        a = max(0.0, a)
        b = max(a, b)
        if dai > 0:
            a, b = min(a, dai), min(b, dai)
        ra.append([round(a, 3), round(b, 3), w])
    return ra


def cat_le_loat(files: list[str], ok: list[bool], out_dir: str | Path,
                tien_to: str = "sach",
                moc_tu: Optional[list] = None) -> tuple[list[str], dict]:
    """Cắt lề cho cả loạt câu. Trả (files_mới, số đo).

    Câu TTS hỏng (`ok[i]` False) giữ nguyên đường dẫn cũ — caller vẫn bỏ nó
    theo `ok`, không được để lệch chỉ số.

    `moc_tu` (nếu truyền) là list mốc từng-từ theo CÂU, **sửa TẠI CHỖ**: mỗi
    câu bị dời đúng số giây vừa cắt ở đầu. Sửa tại chỗ chứ không trả bản mới
    vì hàm này đã có 2 giá trị trả về và 3 nơi gọi — thêm cái thứ ba là chỗ
    nào quên nhận cái đó thì mốc lệch IM LẶNG.
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
        d1, cat_dau = cat_le_im_moc(f, dst)
        ra[i] = str(dst)
        if moc_tu is not None and i < len(moc_tu):
            moc_tu[i] = doi_moc_tu(moc_tu[i], cat_dau, d1)
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
    # Mốc từng-từ đi KÈM file: câu nào bị thay file thì mốc cũ VÔ GIÁ TRỊ,
    # phải thay theo. Quên chỗ này là chữ chạy theo lời của bản CHƯA rút gọn.
    moc_tu = [list(m) for m in (tts.get("moc_tu") or [[] for _ in texts])]
    while len(moc_tu) < len(texts):
        moc_tu.append([])

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
        v, _pitch = tach_giong_pitch(voice or giong_theo_ngon_ngu(dich_sang))
        # `el_lui=False`: đây là lượt ĐỌC LẠI, câu nào cũng đã có sẵn bản
        # ElevenLabs. Hết credit mà lùi edge thì mấy câu này ra giọng khác
        # phần còn lại = video LẪN HAI GIỌNG; trả False để GIỮ BẢN CŨ.
        ok2, mt2 = asyncio.run(
            dubbing._synth_all_words(thu, v, paths, pitch=_pitch,
                                     lang=dich_sang, el_lui=False))
        # CẮT LỀ như đường chính — không cắt thì bản rút gọn bị đo DÀI HƠN
        # thực tế và bị loại oan ở phép so "có ngắn hơn không" bên dưới.
        paths, _le = cat_le_loat(paths, list(ok2), out_dir / f"sach{vong}",
                                 moc_tu=mt2)

        for j, m in enumerate(muc):
            i = m["i"]
            if not ok2[j] or not Path(paths[j]).exists():
                continue
            d_moi = probe_duration(paths[j])
            if d_moi <= 0 or d_moi >= m["d_nat"] - 0.05:
                continue                       # không ngắn hơn -> GIỮ bản cũ
            texts[i] = thu[j]
            files[i] = paths[j]
            moc_tu[i] = mt2[j]
            ok[i] = True
            so_sua += 1

    sau = _can_tempo()

    def _mx(xs: list[float]) -> float:
        return round(max(xs or [1.0]), 3)

    return {
        "texts": texts, "files": files, "ok": ok, "so_sua": so_sua,
        "moc_tu": moc_tu,
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
# cuối cùng mới ép co giãn.
#
# **CẬP NHẬT (việc 1, 15/08/2026): bước ép cuối nay đi `rubberband` chứ không
# còn `atempo`** — xem khối số đo ở `_co_gian_chuoi`. THỨ TỰ TRÊN GIỮ NGUYÊN:
# `rubberband` chỉ làm bước cuối bớt đau, nó KHÔNG chữa cái gốc (ép nén khoảng
# im), nên đừng lấy nó làm cớ hạ `NGUONG_DOC_NHANH` hay bỏ bước rút gọn.

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
                        moc_tu: Optional[list] = None,
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
    moc_tu = [list(m) for m in (moc_tu or [[] for _ in files])]
    while len(moc_tu) < len(files):
        moc_tu.append([])

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
        return {"files": files, "ok": ok, "so_doc_lai": 0, "moc_tu": moc_tu,
                "can_truoc": [round(t, 3) for t in truoc],
                "can_sau": [round(t, 3) for t in truoc], "rate_max": 0}

    if on_progress:
        on_progress(0.2, f"Đọc nhanh lại {len(xau)} câu cho vừa khung...")
    v, _pitch = tach_giong_pitch(voice or giong_theo_ngon_ngu(dich_sang))
    thu = [texts[i] if i < len(texts) else "" for i in xau]
    rates, paths = [], []
    for j, i in enumerate(xau):
        r = min(RATE_TOI_DA,
                max(1, int(round((truoc[i] - 1.0) * 100)) + RATE_BU))
        rates.append(f"+{r}%")
        paths.append(str(out_dir / f"nhanh_{i:04d}.mp3"))
    # `rate` chỉ đổi TỐC ĐỌC của model; WordBoundary server trả theo audio
    # THẬT (đã áp rate) nên mốc từng-từ vẫn đúng, KHÔNG phải bù lại.
    # `el_lui=False` — cùng lý do ở `rut_gon_vua_khung`: giữ bản cũ chứ không
    # trộn giọng. LƯU Ý ĐÁNH ĐỔI THẬT: ElevenLabs KHÔNG có tham số `rate` nên
    # bước ĐỌC NHANH này không rút ngắn được gì, câu tràn khung sẽ phải nhờ
    # `atempo` như trước v2.27.0 (xem mục "chưa được" của ghi chú phát hành).
    ok2, mt2 = asyncio.run(
        dubbing._synth_all_words(thu, v, paths, rate=rates, pitch=_pitch,
                                 lang=dich_sang, el_lui=False))
    sach, _le = cat_le_loat(paths, list(ok2), out_dir / "sach", moc_tu=mt2)

    so = 0
    for j, i in enumerate(xau):
        if not ok2[j] or not Path(sach[j]).exists():
            continue
        d_cu = probe_duration(files[i])
        d_moi = probe_duration(sach[j])
        if d_moi <= 0.05 or d_moi >= d_cu - 0.02:
            continue                       # không ngắn hơn -> GIỮ bản cũ
        files[i] = sach[j]
        moc_tu[i] = mt2[j]
        ok[i] = True
        so += 1

    sau = _can()
    return {
        "files": files, "ok": ok, "so_doc_lai": so, "moc_tu": moc_tu,
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
    """Chuỗi filter atempo, chia tầng nếu > 2.0 (atempo chỉ nhận 0.5-2.0).

    **ĐƯỜNG LÙI** — chỉ dùng khi ffmpeg của máy KHÔNG có `rubberband`. Đường
    chính là `_co_gian_chuoi`; xem khối ghi chú ở đó cho số đo hai bên.
    """
    parts = []
    while tempo > 2.0:
        parts.append("atempo=2.0")
        tempo /= 2.0
    parts.append(f"atempo={tempo:.4f}")
    return ",".join(parts)


# ─────────────── CO GIÃN: `rubberband` THAY `atempo` ────────────────────────
#
# **ĐỌC HẾT KHỐI NÀY TRƯỚC KHI ĐỔI LẠI.** v2.27.0 đã CỐ Ý bỏ đường ép nhanh
# (`29a0fb2`), và lý do lúc đó gồm HAI phần — chỉ MỘT phần được chữa bằng việc
# đổi bộ lọc:
#   (1) `atempo` là WSOLA (cắt sóng thành cửa sổ rồi dán chồng) -> méo.
#       -> ĐỔI BỘ LỌC CHỮA ĐƯỢC.
#   (2) GỐC RỄ: app đang ép nén KHOẢNG IM của edge-tts chứ không phải tiếng
#       nói (câu 12 ký tự thì 58% file là im lặng). Chữa bằng cắt lề im +
#       rút ngắn chữ + `rate`.
#       -> ĐỔI BỘ LỌC **KHÔNG** CHỮA. Lý do này VẪN ĐÚNG NGUYÊN.
# Vì vậy **THỨ TỰ ƯU TIÊN Ở `khop_thoi_gian` GIỮ NGUYÊN** (lọt sẵn -> mượn ->
# mới ép). Đổi bộ lọc chỉ làm cho BƯỚC CUỐI — cái vẫn còn đó và vẫn bắn trên
# câu quá dài — rẻ hơn về chất lượng. Đây KHÔNG phải lời mời hạ `NGUONG_
# DOC_NHANH` hay bỏ bước rút gọn.
#
# SỐ ĐO (`_do_rubberband.py` + `_do_rb_soi.py`, 6 câu edge-tts thật, thước
# log-mel quy về dB; ĐỐI CHỨNG chép nguyên file = **0,000 dB** nên thước sạch):
#
#   hệ số | atempo | rubberband      (vòng tròn: ép k rồi ép ngược 1/k)
#    1,10 |  5,120 |  2,663
#    1,20 |  5,837 |  3,643
#    1,30 |  5,622 |  4,141
#    1,50 |  6,353 |  4,834
#    1,80 |  7,703 |  5,695
#
# **CHỖ CHÊNH LỆCH LỚN NHẤT LÀ Ở HỆ SỐ 1,0** — tức lúc KHÔNG ĐƯỢC PHÉP đổi gì:
#   · `rubberband=tempo=1.0` trả lại **ĐÚNG TỪNG MẪU** (lệch mẫu lớn nhất
#     `0.000000`, lệch phổ **0,000 dB**) — nó là đường ống trong suốt.
#   · `atempo=1.0` **phá tiếng**: lệch phổ thô 3,617 dB, và **căn thẳng hàng
#     rồi VẪN còn 1,982 dB** (tức méo THẬT, không phải chỉ trễ), kèm trễ
#     **2,8-15,0 ms THAY ĐỔI theo từng câu** = rung mốc tiếng so với hình.
#   Hôm nay `khop_thoi_gian` không gọi bộ lọc ở đúng 1,0 (`abs(tempo-1.0) >
#   1e-3`) nên cái hại đó chưa chạm đường thật — nhưng nó nói lên bản chất:
#   với `atempo` thì mọi hệ số đều mất phí, còn `rubberband` thì không.
#
# GIÁ PHẢI TRẢ, GHI THẲNG:
#   · **ĐẮT HƠN**: atempo ~0,000 CPU-giây/câu (dưới ngưỡng đo được),
#     rubberband **0,016** CPU-giây/câu. Với ~40 câu/video là **+0,6
#     CPU-giây/video** — không đáng kể so với Demucs (~25 giây/phút phim).
#   · **NGẮN HƠN ~1,3%**: `rubberband` bỏ bớt đuôi. Đã soi: mất **112 ms ở
#     ĐUÔI** trên 3/6 câu (3 câu còn lại mất 0 ms), **trễ đầu = 0 mẫu** (mốc
#     đầu câu giữ nguyên tuyệt đối), và phần bị bỏ đo được **−180 dBFS = im
#     lặng số tuyệt đối**, KHÔNG phải phụ âm cuối. Với `khop_thoi_gian` thì
#     ngắn hơn là phía AN TOÀN (bất biến "0 ms chồng lấn"), và hàm vẫn đo lại
#     `d_fin` bằng ffprobe chứ không tin số dự kiến.
#   · Bảng "ép đúng khung" vì thế đọc ra `atempo −0,69%` vs `rubberband
#     −1,38%` — nhìn thì atempo sát hơn, nhưng toàn bộ phần chênh của
#     rubberband là ĐUÔI IM bị bỏ, không phải sai hệ số.

#: Đã dò được `rubberband` trong ffmpeg đang dùng chưa (None = chưa dò).
_CO_RUBBERBAND: Optional[bool] = None


def co_rubberband() -> bool:
    """ffmpeg ĐANG DÙNG có bộ lọc `rubberband` không (nhớ kết quả).

    Máy nhân viên có thể chạy ffmpeg riêng trên PATH không build kèm
    `--enable-librubberband`. **Thiếu bộ lọc thì LÙI về `atempo`, KHÔNG
    được nổ** — ép nhanh hơi méo vẫn tốt hơn cả lượt xuất chết.
    """
    global _CO_RUBBERBAND
    if _CO_RUBBERBAND is None:
        try:
            r = subprocess.run(
                [settings.FFMPEG_PATH, "-hide_banner", "-filters"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            _CO_RUBBERBAND = bool(re.search(r"^\s*\S*\s+rubberband\s",
                                            r.stdout or "", re.MULTILINE))
        except Exception:                                      # noqa: BLE001
            _CO_RUBBERBAND = False
    return _CO_RUBBERBAND


def _co_gian_chuoi(tempo: float) -> str:
    """Chuỗi filter CO GIÃN THỜI GIAN cho hệ số `tempo` (>1 = nhanh lên).

    `rubberband` nếu ffmpeg có (mặc định), LÙI về `atempo` nếu không. Đặt
    `BQ_TG_RUBBERBAND=0` để ép đi đường `atempo` (đo A/B / gỡ rối máy user).

    `rubberband` nhận tempo 0,01..100 nên KHÔNG phải chia tầng như `atempo`
    (bị kẹp 0,5..2,0).
    """
    if os.environ.get("BQ_TG_RUBBERBAND", "1").strip() in ("0", "false", "no"):
        return _atempo_chuoi(tempo)
    if not co_rubberband():
        return _atempo_chuoi(tempo)
    #: `transients=crisp` (mặc định) giữ phụ âm bật sắc nét — đúng chỗ WSOLA
    #: làm hỏng trước tiên. Không đặt `pitch` (giữ nguyên cao độ giọng).
    return f"rubberband=tempo={tempo:.4f}"


#: TRẦN LÀM CHẬM HÌNH ở chế độ "Chỉnh video theo giọng".
#:
#: **ĐẶT THEO NHỊP HÌNH CÒN LẠI, KHÔNG PHẢI THEO SỞ THÍCH.** Làm chậm hình bằng
#: `-itsscale` KHÔNG sinh khung mới — nó chỉ giãn mốc thời gian, nên nhịp hình
#: hiệu dụng tụt đúng theo hệ số: `fps_còn_lại = fps_nguồn / k`.
#: Nguồn anh Hùng đang làm đo được **23,976 fps** (`2997/125`), tức đã sát mức
#: chiếu phim — chỗ trống rất hẹp:
#:
#: | k | nhịp hình còn lại (nguồn 23,976) |
#: |---|---|
#: | 1,10 | 21,80 fps |
#: | **1,20** | **19,98 fps** |
#: | 1,35 | 17,76 fps |
#: | 1,50 | 15,98 fps |
#:
#: Chốt `SAN_NHIP_HINH_FPS = 20` -> nguồn 23,976 cho trần **k = 1,199**; nguồn
#: 30 fps cho **k = 1,50** (chặn lại bởi trần cứng dưới đây).
#: **TÔI KHÔNG CÓ MẮT để nói 20 fps có giật hay không** — vì vậy có sẵn file
#: mẫu ở 5 mức cho anh Hùng TỰ XEM (`_do_hinh_theo_giong.py`), và trần này là
#: chỗ để sửa sau khi anh ấy xem, KHÔNG phải con số cuối cùng.
SAN_NHIP_HINH_FPS = 20.0

#: Trần CỨNG, chặn trên cả phép tính theo fps. Nguồn 60 fps thì công thức cho
#: k = 3,0 — chậm 3 lần là phim khác, không phải "khớp giọng".
TRAN_CHINH_HINH = 1.25


def he_so_hinh_can(cau: list[dict], files: list[str], ok: list[bool],
                   tong: float) -> dict:
    """Tính hệ số LÀM CHẬM HÌNH cần thiết để MỌI câu đọc ở tốc độ TỰ NHIÊN.

    **ĐÂY LÀ "LÀM ĐÚNG CHIỀU" mà anh Hùng nói 18/08/2026:** *"đáng nhẽ chỉ
    chỉnh video sao cho khớp giọng nói chứ"*. Chiều CŨ là ép tiếng vừa khung
    câu gốc (`atempo`/`rubberband`) -> mỗi câu một hệ số ép -> tốc độ đọc nhấp
    nhô = đúng chữ *"giọng cứ lúc nhanh lúc chậm không đều"*.

    Điều kiện KHÔNG CHỒNG LẤN với hệ số `k` (câu i đặt ở `k*s_i`):
        `k*s_i + d_i <= k*s_{i+1}`  ->  `k >= d_i / (s_{i+1} - s_i)`
    nên `k = max` của các tỉ số đó (và của câu cuối so với hết phim). Lấy MỘT
    hệ số cho cả clip chứ không phải mỗi câu một hệ số: hình đổi tốc độ giữa
    phim thì mắt đọc ra ngay, còn tiếng thì giữ tempo **1,0 tuyệt đối**.

    Trả `{k_can, k_dung, cham_tran, ty_so_max, cau_chat_nhat}`.
    """
    ty: list[tuple[float, int]] = []
    for i, c in enumerate(cau):
        if i >= len(files) or not ok[i] or not Path(files[i]).exists():
            continue
        d_nat = probe_duration(files[i])
        if d_nat <= 0:
            continue
        a = float(c["start"])
        ke = float(cau[i + 1]["start"]) if i + 1 < len(cau) else tong
        cho = max(0.05, ke - a - CHUA_TRUOC_CAU_KE)
        ty.append((d_nat / cho, i))
    if not ty:
        return {"k_can": 1.0, "k_dung": 1.0, "cham_tran": False,
                "ty_so_max": 1.0, "cau_chat_nhat": -1}
    ty.sort(reverse=True)
    k_can = max(1.0, ty[0][0])
    return {"k_can": round(k_can, 4), "ty_so_max": round(ty[0][0], 4),
            "cau_chat_nhat": ty[0][1]}


def tran_hinh_theo_fps(fps: float) -> float:
    """Trần `k` cho nguồn `fps` — xem `SAN_NHIP_HINH_FPS`. Hàm THUẦN."""
    if fps <= 0:
        return TRAN_CHINH_HINH
    return max(1.0, min(TRAN_CHINH_HINH, fps / SAN_NHIP_HINH_FPS))


def khop_thoi_gian(cau: list[dict], files: list[str], ok: list[bool],
                   tong: float, out_dir: str | Path,
                   tempo_canh_bao: float = TEMPO_CANH_BAO,
                   tempo_toi_da: float = TEMPO_TOI_DA,
                   moc_tu: Optional[list] = None,
                   he_so_hinh: float = 1.0,
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
    #: [(chỉ số câu, [[giây_bắt_đầu, giây_hết, từ], ...])] — TIMELINE ĐẦU RA.
    moc_tu_ra: list[tuple[int, list]] = []
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

    # HỆ SỐ LÀM CHẬM HÌNH: mọi mốc câu nhân `k`, còn TIẾNG giữ nguyên độ dài
    # tự nhiên. `k = 1.0` -> chạy y hệt bản cũ (không một phép nhân nào đổi số).
    k = max(1.0, float(he_so_hinh or 1.0))
    tong_ra = tong * k

    for i, c in enumerate(cau):
        if i >= len(files) or not ok[i] or not Path(files[i]).exists():
            bo_qua += 1
            continue
        a = float(c["start"]) * k
        b = float(c["end"]) * k
        khung = max(0.05, b - a)

        # khoảng lặng tới câu kế (có thể MƯỢN)
        ke = (float(cau[i + 1]["start"]) * k if i + 1 < len(cau) else tong_ra)
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
                # `rubberband` (lùi về `atempo` nếu ffmpeg máy không có) —
                # xem khối số đo ở `_co_gian_chuoi`.
                af.append(_co_gian_chuoi(tempo))
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

        # MỐC TỪNG-TỪ -> TIMELINE ĐẦU RA. Hai đường tỉ lệ KHÁC NHAU, đừng gộp:
        #  · không cắt đuôi -> lấy `d_fin/d_nat` ĐO THẬT (atempo/aresample làm
        #    tròn khác `1/tempo`, dùng số đo thì hết phải tin lời hứa);
        #  · CÓ cắt đuôi -> `d_fin` là chiều dài SAU KHI CẮT nên `d_fin/d_nat`
        #    sẽ nén cả câu lại (chữ chạy nhanh hơn tiếng); phải dùng `1/tempo`
        #    rồi VỨT những từ rơi ra ngoài phần đã cắt.
        mt = (moc_tu[i] if moc_tu is not None and i < len(moc_tu) else None)
        if mt:
            if cat_lan:
                ty_le = 1.0 / max(1e-6, tempo)
            else:
                ty_le = (d_fin / d_nat) if d_nat > 0 \
                    else 1.0 / max(1e-6, tempo)
            ds = []
            for w in mt:
                wa, wb = float(w[0]) * ty_le, float(w[1]) * ty_le
                if wa >= d_fin - 1e-3:
                    break                     # từ này nằm trong phần bị cắt
                ds.append([round(a + wa, 3), round(a + min(wb, d_fin), 3),
                           w[2]])
            if ds:
                moc_tu_ra.append((i, ds))

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
        "moc_tu": moc_tu_ra,
        "so_cau_co_moc_tu": len(moc_tu_ra),
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
        # TRẢI hệ số ép = max − min. `tempo_max` một mình KHÔNG nói được
        # "giọng lúc nhanh lúc chậm": trải mới là con số của cái nhấp nhô đó.
        "tempo_trai": round(max(temps or [1.0]) - min(temps or [1.0]), 3),
        "he_so_hinh": round(k, 4),
        "do_dai_ra": round(tong_ra, 3),
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


#: Khoảng trống ngắn hơn mức này thì KHÔNG bù giọng gốc — đó là nhịp nghỉ giữa
#: hai câu, nhét tiếng gốc vào chỉ làm bẩn. 0,35 s là dưới độ dài một từ nói rõ
#: (~0,15 s) cộng hai mép chuyển tiếp.
BU_GOC_DAI_MIN = 0.35

#: Mép chuyển tiếp vào/ra khi bù (giây). Bật/tắt phát một là nghe thấy "cụp" —
#: cùng bài học `enable=` của nhóm hiệu ứng (cổng 43).
BU_GOC_MEP = 0.06

#: Lùi mép khoảng trống lại bấy nhiêu giây ở MỖI ĐẦU trước khi bù. Mốc câu mới
#: và mốc câu gốc lệch nhau vài chục ms (cổng 60 đo 43 ms), nên bù sát mép là
#: chồng lên đuôi/đầu giọng MỚI = hai giọng cùng nói.
BU_GOC_LUI = 0.10

#: BƯỚC ĐO đường bao khi dò "gốc có tiếng".
#:
#: **PHẢI LÀ 0,05 s, VÀ ĐÂY LÀ SỐ ĐO CHỨ KHÔNG PHẢI SỞ THÍCH.** Bản đầu dùng
#: `BUOC_DO_MUC` (0,20 s) và bản vá **KHÔNG CHẠY MỘT LẦN NÀO** trên video thật
#: (phép A/B end-to-end ra `so_bu = 0 · bo_qua = 44`). Lý do: cửa sổ 0,20 s
#: TRUNG BÌNH mất các khoảng lặng giữa từ nên sàn bị kéo lên sát mức lời. Đo
#: trên lớp giọng Demucs THẬT (`_do_nguong_bu.py`, 150 s video của anh Hùng):
#:
#: | bước | p20 (sàn) | p90 (lời) | cách nhau | `sàn+10` nhận ra |
#: |---|---|---|---|---|
#: | **0,05 s** | −26,39 | −11,95 | **14,4 dB** | **51,3%** |
#: | 0,20 s | −19,87 | −12,85 | **7,0 dB** | **0,0%** (ngưỡng −9,87 > max −10,18) |
BU_GOC_BUOC = 0.05

#: Khoảng trống chỉ được bù khi lớp giọng GỐC thật sự CÓ TIẾNG ở đó, nổi hơn
#: sàn nhiễu của chính nó bấy nhiêu dB. Không có cửa này thì mọi nhịp nghỉ đều
#: được "bù" bằng nhiễu nền của Demucs.
#:
#: **12 dB LÀ ĐỂ KHỚP VỚI THƯỚC ĐO** (`_do_mat_giong.khoang_mat` dùng
#: `sàn + 12` ở bước 0,05 s). Bộ dò của bản vá và bộ dò của phép đo phải là MỘT:
#: lệch nhau thì có cửa sổ cổng đếm là "mất" mà bản vá không bù, rồi chốt "tổng
#: giây mất = 0" không bao giờ đạt được vì một lý do không ai lần ra.
BU_GOC_NOI_DB = 12.0

#: LƯỚI AN TOÀN: ngưỡng KHÔNG BAO GIỜ được cao quá `p90 − mức này`.
#:
#: Sàn ước bằng bách phân vị 20 có thể sai HẲN khi lớp giọng bị nén / rỉ nhạc
#: nhiều (đúng ca 0,20 s ở trên: sàn ước −19,87 trong khi lời chỉ −12,85). Thiếu
#: lưới này thì ngưỡng leo lên TRÊN mức lời và bản vá **im lặng không bù gì** —
#: hỏng đúng kiểu nguy hiểm nhất: mọi cổng vẫn xanh, chỉ `so_bu = 0` tố giác.
#: Với dữ liệu thật lưới gần như không đụng tới: min(−14,39; −14,95) = −14,95.
BU_GOC_DUOI_DINH_DB = 3.0


def khoang_khong_giong(manh: list[tuple[float, str]], tong: float,
                       dai_min: float = BU_GOC_DAI_MIN,
                       lui: float = BU_GOC_LUI) -> list[tuple[float, float]]:
    """Khoảng KHÔNG có giọng MỚI trên trục [0, `tong`].

    **VÌ SAO HÀM NÀY TỒN TẠI (lỗi anh Hùng báo 18/08/2026):** *"mấy cái đoạn âm
    thanh gốc nói tiếng Anh nó không đọc phần đó thì lại bị **tắt tiếng**"* ·
    *"cái nghe được cái không"*. Dây chuyền BỎ HẲN giọng gốc rồi đặt giọng mới
    vào; đoạn nào bộ chép lời không lấy (câu tiếng Anh giữa phim Trung) hoặc
    TTS lỗi thì **không có giọng nào cả** — còn lại chỉ nhạc.
    ĐO ĐƯỢC trên 4 bản anh Hùng đã xuất (`_do_mat_giong.py`, so LỚP GIỌNG với
    LỚP GIỌNG): mất **82,3 s / 1.209,3 s = 6,8%**, dồn vào 2/4 video
    (**31,1 s** và **50,4 s**) — đúng chữ "cái nghe được cái không".

    Mỗi mép khoảng trống bị LÙI vào `lui` giây để không chồng lên giọng mới.
    Trả [] khi không có khoảng nào đáng bù.
    """
    if tong <= 0:
        return []
    # [đầu, cuối] của từng câu MỚI. `probe_duration` trên file đã ghi — KHÔNG
    # suy từ độ dài dự kiến (`atempo`/cắt lề làm lệch, bài học `nen_lop_giong`).
    che: list[tuple[float, float]] = []
    for off, p in manh or []:
        d = probe_duration(p)
        if d > 0:
            che.append((float(off), float(off) + d))
    che.sort()
    # gộp các đoạn chồng nhau lại thành phủ liên tục
    gop: list[list[float]] = []
    for a, b in che:
        if gop and a <= gop[-1][1] + 1e-6:
            gop[-1][1] = max(gop[-1][1], b)
        else:
            gop.append([a, b])
    ra: list[tuple[float, float]] = []
    moc = 0.0
    for a, b in gop:
        if a - moc >= dai_min:
            ra.append((moc, a))
        moc = max(moc, b)
    if tong - moc >= dai_min:
        ra.append((moc, tong))
    # lùi hai mép rồi bỏ khoảng còn quá ngắn
    hep: list[tuple[float, float]] = []
    for a, b in ra:
        a2, b2 = a + lui, b - lui
        if b2 - a2 >= dai_min:
            hep.append((round(max(0.0, a2), 3), round(min(tong, b2), 3)))
    return hep


#: Số mảnh giọng mới được LẤY MẪU để đo mức. Đo hết 175 mảnh là 175 lượt ffmpeg
#: cho một con số duy nhất; lấy mẫu rải đều cho ra cùng câu trả lời.
BU_GOC_MAU_DO = 8


def _muc_noi_manh(manh: list[tuple[float, str]]) -> Optional[float]:
    """Mức LỜI (dBFS) của track giọng MỚI, đo qua vài mảnh lấy mẫu.

    Lấy trung vị của bách phân vị 90 từng mảnh: p90 trong một mảnh là chỗ ĐANG
    NÓI (mảnh nào cũng gần như toàn tiếng nói), còn trung vị giữa các mảnh loại
    được mảnh cá biệt. Trả None khi không đo được — nơi gọi phải coi None là
    "đừng bù mức", KHÔNG được coi là 0 dB.
    """
    if not manh:
        return None
    buoc = max(1, len(manh) // BU_GOC_MAU_DO)
    ds: list[float] = []
    for _off, p in manh[::buoc][:BU_GOC_MAU_DO]:
        b = duong_bao_muc(p, buoc=BUOC_DO_MUC)
        hu = [v for v in b if v > -119.0]
        if hu:
            ds.append(_bpv(hu, 0.90))
    return _bpv(ds, 0.5) if ds else None


def bu_giong_goc(giong_goc: str | Path, manh: list[tuple[float, str]],
                 tong: float, out_dir: str | Path,
                 he_so_hinh: float = 1.0) -> dict:
    """Cắt lớp giọng GỐC ở những khoảng KHÔNG có giọng mới -> mảnh để trộn vào.

    Trả `{manh: [(offset, wav)], khoang: [...], giay_bu, giay_trong, bo_qua}`.
    `manh` CỘNG THẲNG vào danh sách mảnh giọng mới rồi đưa cho
    `tron_thay_giong` — **cố ý đi cửa đó chứ không trộn vào file cuối**: nhờ
    vậy phần bù được tính vào cả phép cân bằng giọng-nhạc, cả ducking, cả bước
    chuẩn hoá độ to. Trộn sau khi đã chuẩn hoá là làm sai chính con số vừa đo.

    **CHỈ BÙ CHỖ GỐC CÓ TIẾNG THẬT.** Ngưỡng lấy theo SÀN NHIỄU CỦA CHÍNH lớp
    giọng đó (`BU_GOC_NOI_DB`), không phải hằng số dBFS: Demucs để lại mức
    nhiễu khác nhau mỗi lượt, đặt hằng số là bù cả những chỗ chỉ có nhiễu.

    `he_so_hinh > 1` (chế độ "Chỉnh video theo giọng"): trục thời gian ĐẦU RA
    đã giãn `k` lần nên mốc gốc phải chia `k` khi đi cắt, và mảnh cắt ra phải
    được giãn đúng `k` — nếu không thì phần bù trôi mỗi lúc một xa.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    k = max(1.0, float(he_so_hinh or 1.0))
    trong = khoang_khong_giong(manh, tong)
    ket: dict = {"manh": [], "khoang": [], "giay_bu": 0.0,
                 "giay_trong": round(sum(b - a for a, b in trong), 2),
                 "so_trong": len(trong), "bo_qua": 0}
    if not trong or not giong_goc or not Path(str(giong_goc)).exists():
        ket["ly_do"] = "không có khoảng trống" if not trong else "thiếu lớp giọng gốc"
        return ket

    bao = duong_bao_muc(giong_goc, buoc=BU_GOC_BUOC)
    if not bao:
        ket["ly_do"] = "không đo được đường bao lớp giọng gốc"
        return ket
    # SÀN NHIỄU = bách phân vị 20 trên **MỌI** cửa sổ, KỂ CẢ cửa sổ im tuyệt
    # đối (`duong_bao_muc` trả -120 cho `-inf`).
    #
    # **BỎ CỬA SỔ IM RA LÀ BUG, cổng 78 bắt được:** lớp giọng do Demucs tách
    # LUÔN có sàn rỉ nhạc (đo thật trên 4 video: **-24,0 .. -29,2 dBFS**) nên
    # bỏ hay không bỏ đều ra cùng số. Nhưng nguồn tách kiểu KHÁC (`cach="nhe"`
    # của ffmpeg, hoặc video vốn im hẳn ngoài lời) cho ra "hoặc tiếng hoặc IM
    # TUYỆT ĐỐI"; lọc `> -119` khi đó vứt sạch phần im, nên p20 của phần CÒN
    # LẠI chính là MỨC LỜI -> ngưỡng nhảy lên trên cả lời -> **bù 0 mảnh, im
    # lặng, không một dòng báo**. Tính trên mọi cửa sổ thì ca đó ra sàn -120 và
    # ngưỡng -110, đúng như phải vậy.
    sx = sorted(bao)
    san = sx[int(len(sx) * 0.20)]
    dinh = sx[int(len(sx) * 0.90)]
    # LƯỚI AN TOÀN — xem `BU_GOC_DUOI_DINH_DB`: ngưỡng không bao giờ được leo
    # lên trên mức lời, dù phép ước sàn có sai thế nào.
    nguong = min(san + BU_GOC_NOI_DB, dinh - BU_GOC_DUOI_DINH_DB)
    ket["san_db"] = round(san, 2)
    ket["dinh_db"] = round(dinh, 2)
    ket["nguong_db"] = round(nguong, 2)
    ket["luoi_an_toan"] = bool(dinh - BU_GOC_DUOI_DINH_DB
                               < san + BU_GOC_NOI_DB)

    # --- KHỚP MỨC: giọng gốc phải to NGANG giọng mới, không to hơn ---
    # Lớp giọng gốc mang mức của bản master gốc (đo trên video anh Hùng:
    # cả bản trộn **-13,0 LUFS**) còn track TTS đo được **-19,7 LUFS** — chênh
    # ~6-7 dB. Nhét thẳng vào thì hai chuyện xảy ra, cả hai đều nghe ra:
    #   (1) chỗ bù NHẢY TO hơn phần còn lại = đúng kiểu "chỗ to chỗ nhỏ";
    #   (2) `can_bang_giong_nhac` đo track giọng SAU khi đã cộng phần bù, thấy
    #       nó to sẵn nên bớt nâng -> GIỌNG TTS bị nhỏ đi ở cả video.
    # Nên đo mức LỜI của cả hai bên rồi bù cho ngang. Trần ±12 dB để một phép đo
    # lệch không đẩy phần bù thành tiếng rít hay mất hút.
    muc_moi = _muc_noi_manh(manh)
    muc_goc = _bpv([v for v in bao if v > nguong], 0.5) if any(
        v > nguong for v in bao) else None
    gain_db = 0.0
    if muc_moi is not None and muc_goc is not None:
        gain_db = max(-12.0, min(12.0, muc_moi - muc_goc))
    ket["muc_giong_moi_db"] = (None if muc_moi is None
                               else round(muc_moi, 2))
    ket["muc_giong_goc_db"] = (None if muc_goc is None
                               else round(muc_goc, 2))
    ket["gain_khop_db"] = round(gain_db, 2)

    for i, (a, b) in enumerate(trong):
        # Mốc trên lớp giọng GỐC (trục CHƯA giãn).
        ag, bg = a / k, b / k
        i0 = int(ag / BU_GOC_BUOC)
        i1 = min(len(bao), max(i0 + 1, int(bg / BU_GOC_BUOC)))
        if not any(bao[j] > nguong for j in range(i0, i1)):
            ket["bo_qua"] += 1              # chỗ này gốc cũng im -> đừng bù
            continue
        p = out_dir / f"bu_{i:04d}.wav"
        af = [f"atrim=start={ag:.3f}:end={bg:.3f}", "asetpts=N/SR/TB"]
        if k > 1.0 + 1e-6:
            af.append(_co_gian_chuoi(1.0 / k))
        if abs(gain_db) > 0.1:
            af.append(f"volume={gain_db:.2f}dB")
        af.append(f"aresample={SR_TACH}")
        # Mép vào/ra: bật/tắt phát một thì nghe thấy "cụp".
        d = max(0.05, (bg - ag) * k)
        m = min(BU_GOC_MEP, d / 3.0)
        af.append(f"afade=t=in:st=0:d={m:.3f}")
        af.append(f"afade=t=out:st={max(0.0, d - m):.3f}:d={m:.3f}")
        try:
            _ffmpeg(["-i", str(giong_goc), "-af", ",".join(af),
                     "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
                     str(p)], f"cắt giọng gốc bù khoảng {a:.2f}-{b:.2f}s",
                    timeout=300)
        except Exception:                                   # noqa: BLE001
            ket["bo_qua"] += 1
            continue
        # ffmpeg mã 0 mà file 0 KiB là ca đã sập nhiều lần -> kiểm KÍCH THƯỚC.
        if not p.exists() or p.stat().st_size < 1024:
            ket["bo_qua"] += 1
            continue
        ket["manh"].append((round(a, 3), str(p)))
        ket["khoang"].append([round(a, 2), round(b, 2)])
        ket["giay_bu"] += probe_duration(p)
    ket["giay_bu"] = round(ket["giay_bu"], 2)
    ket["so_bu"] = len(ket["manh"])
    return ket


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


#: BƯỚC ĐO đường bao mức (giây). 0,20 s đủ mịn để thấy từng câu, đủ thô để
#: không biến khoảng nghỉ giữa hai từ thành "hết nói".
BUOC_DO_MUC = 0.20

#: Cửa sổ được coi là ĐANG NÓI: mức giọng nằm trong bấy nhiêu dB dưới bách
#: phân vị 95 của CHÍNH lớp giọng. Lấy TƯƠNG ĐỐI vì mức edge-tts trả về đổi
#: theo giọng/ngôn ngữ — hằng số tuyệt đối là đúng hôm nay, sai khi đổi giọng.
DANG_NOI_DUOI_DB = 18.0

#: ĐÍCH: giọng mới phải cao hơn nhạc nền bấy nhiêu dB Ở LÚC ĐANG NÓI.
#: **CON SỐ NÀY LẤY TỪ CHÍNH BẢN GỐC**, không bịa: đo lớp giọng/lớp nhạc của
#: video Trung anh Hùng gửi ra **+3,35 dB**. Đặt +6 vì giọng TTS phẳng hơn
#: giọng người (dải động 8 dB so với 34 dB) nên cần dư ra mới nghe rõ bằng.
DICH_GIONG_TREN_NHAC_DB = 6.0

#: Trần NÂNG giọng. Trên mức này là kéo cả nền nhiễu của edge-tts lên theo.
TANG_GIONG_TOI_DA_DB = 12.0

#: Trần HẠ nhạc. Cả tính năng này tên là "GIỮ NGUYÊN nhạc nền" — hạ quá tay
#: là tự phá mục tiêu. Phần còn thiếu để nhạc NÉ chỗ nào cần thì `ducking` lo.
HA_NHAC_TOI_DA_DB = 8.0

#: Đỉnh lớp giọng sau khi nâng không được vượt mức này (dBFS) — chừa chỗ cho
#: nhạc cộng vào rồi mới tới `alimiter`.
#:
#: **PHẢI SO VỚI ĐỈNH THẬT, KHÔNG PHẢI ĐỈNH ĐƯỜNG BAO RMS** — bản đầu của
#: hàm này lấy `max(đường bao RMS)` làm đỉnh và đã sai HẲN: đường bao ra
#: **-15,9 dBFS** trong khi đỉnh thật (`astats Peak level`) là **-5,33**, tức
#: hụt **10,6 dB**. Nâng +12 dB theo con số hụt đó đẩy lớp giọng lên
#: **+6,67 dBFS**, và `alimiter` phải gọt tới 7,7 dB ngay trên tiếng nói —
#: đúng loại "sửa cái này hỏng cái kia" mà tai nghe ra là giọng bị bóp.
DINH_GIONG_TOI_DA_DB = -3.0

#: NÉN LỚP GIỌNG TRƯỚC KHI NÂNG. Giọng edge-tts có hệ số đỉnh/RMS **15,3 dB**
#: (đỉnh -5,33 · RMS lúc nói -20,64) — vài phụ âm bật chiếm hết chỗ trống, còn
#: phần nghe được thì thấp. Nén hạ hệ số đó xuống rồi mới nâng: to hơn mà
#: KHÔNG đụng trần, và tiếng nói đều hơn (dễ nghe trên nền nhạc).
#: Ngưỡng đặt CAO HƠN mức lời đo được `NEN_TREN_LOI_DB` dB nên chỉ phần đỉnh
#: bị đụng, thân câu giữ nguyên động.
#:
#: **QUÉT 12 TỔ HỢP RỒI MỚI CHỌN** (`_do_nen_giong.py`, ngưỡng +3/+6/+9/+12 dB
#: trên mức lời × tỉ lệ 3/4/6). Kết quả đáng nhớ: **cả 12 tổ hợp ra giọng/nhạc
#: +5,55 .. +5,99 dB** — tham số nén gần như KHÔNG đổi kết quả cuối, vì nén
#: sâu hơn thì vừa hạ đỉnh (được nâng nhiều hơn) vừa hạ luôn mức lời (phải
#: nâng nhiều hơn), hai cái triệt tiêu nhau. Cái CHẶN thật sự là trần đỉnh
#: `DINH_GIONG_TOI_DA_DB` và trần hạ nhạc `HA_NHAC_TOI_DA_DB`.
#: Vì vậy chọn +6/3.0 = mức ĐỤNG VÀO THÂN CÂU ÍT NHẤT trong nhóm cùng kết quả
#: (mức lời chỉ tụt 1,71 dB, so với 2,93 dB ở ngưỡng +3).
#: **ĐỪNG "tối ưu" hai số này** — bảng đã cho thấy không có gì để tối ưu; muốn
#: khá hơn phải đụng vào hai cái trần kia, và đó là đánh đổi với NHẠC NỀN.
NEN_TREN_LOI_DB = 6.0
NEN_TI_LE = 3.0

#: NHẠC NÉ GIỌNG (ducking) — nhạc tụt ở ĐÚNG chỗ đang nói, chỗ không nói giữ
#: NGUYÊN mức. Khác hẳn "hạ nhạc cả bài", và đó là lý do phải có nó: cả tính
#: năng này tên là *giữ nguyên nhạc nền*.
#:
#: **HAI HẰNG SỐ NÀY LÀ SỐ ĐO, KHÔNG PHẢI CÔNG THỨC** (`_do_hieu_chuan_duck.py`
#: trên chính lượt chạy thật). Bản đầu tính `ratio` từ công thức nén
#: `R = 1/(1 - duck/(vào-T))` rồi tin luôn — SAI HẲN: đặt đích tụt 4 dB mà đo
#: ra nhạc mất **10,42 dB** và giọng vọt **+15,48 dB** (đích 10,0). Lý do:
#: mức nhạc ta đo là TRUNG VỊ cửa sổ RMS 0,2 s, còn bộ nén nhìn mức TỨC THỜI,
#: mà đỉnh nhạc cao hơn trung vị nhiều nên nó nén sâu hơn hẳn.
#: Bảng quét THẬT (ngưỡng đặt dưới mức nhạc 8 dB), cột giữa là nhạc tụt TB:
#:     ratio 1,3 -> **-3,28 dB** · 1,6 -> -4,79 · 2,0 -> -5,75 · 3,0 -> -6,64
#: Chọn **1,3**: đủ dọn chỗ cho lời mà nhạc vẫn còn nghe rõ. Muốn đổi thì
#: CHẠY LẠI bảng đó, đừng suy từ công thức.
DUCK_RATIO = 1.3

#: Ngưỡng nén đặt THẤP HƠN MỨC NHẠC ĐO ĐƯỢC bấy nhiêu dB (bám mức thật, không
#: phải hằng số tuyệt đối: cùng `threshold=0.03` thì phim nhạc to tụt 10 dB
#: còn phim nhạc nhỏ không tụt tí nào — tức tính năng chạy hay không tuỳ may).
DUCK_TREN_NGUONG_DB = 8.0

#: Độ tụt ĐO ĐƯỢC ứng với `DUCK_RATIO` ở trên — chỉ để ghi nhật ký/báo cáo,
#: KHÔNG dùng để tính gì (tính ngược lại từ nó là quay về đúng cái sai cũ).
DUCK_DB_DO_DUOC = 3.28


# ==================================================================
# NGƯỜI DÙNG TỰ CHỈNH ÂM LƯỢNG — hai ô dB trong hộp Thay giọng nói
# ==================================================================
# Anh Hùng 20/08/2026: *"cái phần âm thanh gốc nó nói bé k tuỳ chỉnh âm thanh
# đc à chứ to quá"*. Tới v2.41.1 mọi hằng số ở trên TỰ QUYẾT thay anh ấy:
# `grep -c "muc_giong_db\|muc_nhac_db\|slider" app/ui/thay_giong_dialog.py` = 0.
# App ĐO rồi tính là đúng cho ca trung bình, nhưng nó KHÔNG biết tai anh Hùng
# muốn nghe tiếng gốc nhiều hay ít — đó là lựa chọn, không phải phép đo.
#
# **HAI Ô NÀY CHỈ ĐỔI TỈ LỆ, KHÔNG ĐỔI ĐỘ TO CUỐI.** `chuan_do_to` (bước cuối
# của `tron_thay_giong`) vẫn kéo cả bản trộn về `DICH_LUFS` bằng MỘT hệ số
# TĨNH, nên I/TP của file thành phẩm giữ nguyên đích ở MỌI cấu hình — cái đổi
# là hiệu (giọng − nền). Đó cũng là lý do không cần (và không được) nới trần
# đỉnh: trần đỉnh trừ HAI LẦN nằm nguyên chỗ cũ.

#: TRẦN hai ô, tính theo dB. Đặt ±6 vì đó là mức ĐỔI HẲN cảm nhận mà vẫn nằm
#: trong chỗ trống của hệ:
#:   · nền: phần tự động hạ nền tối đa `HA_NHAC_TOI_DA_DB` = 8 dB, nên +6 chỉ
#:     đưa nền về gần mức GỐC của nó, không đẩy vượt bản gốc.
#:   · giọng: −6 là hạ, luôn an toàn; +6 thì còn bị `DINH_GIONG_TAY_TOI_DA_DB`
#:     bên dưới chặn lại theo ĐỈNH ĐO ĐƯỢC, nên trần này là trần MỀM của ô.
#: Cho rộng hơn ±6 là mở cửa cho cấu hình tự dìm lời (bệnh 15/08: giọng dưới
#: nhạc 9,27 dB -> 93,5% cửa sổ chìm = *"chỗ có chỗ không nghe không được"*).
TRAN_MUC_TAY_DB = 6.0

#: Bước làm tròn khi băm/so-với-mặc-định. 0,1 dB là dưới ngưỡng nghe ra được,
#: nên **PHẢI làm tròn TRƯỚC khi băm** — y bài học `chuan_muc_mo` (cổng 56e):
#: băm giá trị THÔ là đẻ job chạy lại cho một thay đổi KHÔNG TỒN TẠI.
BUOC_MUC_TAY_DB = 0.1

#: TRẦN ĐỈNH cho phần NGƯỜI DÙNG TỰ TĂNG giọng (dBFS), đo trên CHÍNH lớp giọng
#: đã nén. Nới hơn trần tự động `DINH_GIONG_TOI_DA_DB` = −3,0 là CÓ CHỦ Ý:
#: trần −3 để chừa chỗ cho nhạc cộng vào, còn ô này là anh Hùng CỐ Ý đòi giọng
#: nổi hơn, nên phải cho nó tiêu vào chỗ trống đó.
#:
#: **VÌ SAO ĐÚNG BẰNG `TRAN_DINH_DB` (−1,0) CHỨ KHÔNG HƠN:** trên mức đó thì
#: lớp giọng MỘT MÌNH đã vượt trần `alimiter` của bản trộn, tức bộ hạn đỉnh
#: phải gọt NGAY TRÊN TIẾNG NÓI trước khi nền kịp cộng vào — đúng cái đã đo
#: được một lần: nâng +12 dB theo số hụt sai làm đỉnh lớp giọng lên +6,67 dBFS,
#: `alimiter` gọt 7,7 dB và số mẫu chạm trần nhảy **36 -> 1.577**.
#: `Abs_Peak_count` là thước bắt được chuyện này; I và TP thì KHÔNG (chúng vẫn
#: đúng đích vì `chuan_do_to` chạy sau).
DINH_GIONG_TAY_TOI_DA_DB = TRAN_DINH_DB


def chuan_muc_db(v) -> float:
    """CHUẨN HOÁ một ô dB: kẹp trong trần, làm tròn `BUOC_MUC_TAY_DB`.

    Đây là **CỬA DUY NHẤT** quyết định "ô này có khác mặc định hay không". Mọi
    chỗ (UI · payload job · khoá chống trùng · bước trộn) phải đi qua đây, không
    thì ba nơi tự chuẩn hoá theo ba kiểu rồi lệch nhau — lỗi "chọn X ra Y".

    Rác (None · "" · chữ · NaN · inf) -> **0,0** = MẶC ĐỊNH. Thà bỏ qua một ô
    hỏng còn hơn nhân một hệ số bịa vào tiếng của anh Hùng.

    `-0.0` phải ra `0.0`: `-0.0 != 0.0` là False trong Python nên so sánh vẫn
    đúng, nhưng `f"{-0.0:+.1f}"` ra `"-0.0"` -> khoá chống trùng khác chuỗi
    trong khi giá trị y nhau.
    """
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    if x != x or x in (float("inf"), float("-inf")):   # NaN / vô cực
        return 0.0
    x = max(-TRAN_MUC_TAY_DB, min(TRAN_MUC_TAY_DB, x))
    x = round(x / BUOC_MUC_TAY_DB) * BUOC_MUC_TAY_DB
    return round(x, 1) + 0.0        # `+ 0.0` biến -0.0 thành 0.0


def _tham_so_duck(muc_nhac_db: float, ratio: float = DUCK_RATIO,
                  ) -> tuple[float, float]:
    """(ngưỡng tuyến tính, ratio) cho `sidechaincompress`. Hàm THUẦN.

    Ngưỡng bám theo MỨC NHẠC ĐO ĐƯỢC nên độ tụt không đổi khi đổi phim.
    """
    nguong = 10.0 ** ((muc_nhac_db - DUCK_TREN_NGUONG_DB) / 20.0)
    return (max(1e-4, min(1.0, nguong)), max(1.0, min(20.0, ratio)))


def duong_bao_muc(path: str | Path, buoc: float = BUOC_DO_MUC,
                  sr: int = SR_TACH) -> list[float]:
    """[dBFS] mỗi `buoc` giây — MỘT lượt ffmpeg, tính trong C.

    `-inf` (cửa sổ im tuyệt đối) -> **-120.0**: phải trả số hữu hạn, không thì
    mọi phép trung bình/bách phân vị phía sau ra `nan` rồi lặng lẽ hỏng.
    BẪY (cổng 44/53): mỗi dòng `astats` mở đầu bằng `[Parsed_astats_0 @ ...]`
    nên phải dùng `in`, KHÔNG `startswith`.
    """
    n = max(1, int(round(sr * buoc)))
    cmd = [settings.FFMPEG_PATH, "-v", "error", "-nostdin", "-i", str(path),
           "-map", "0:a:0", "-af",
           f"aresample={sr},asetnsamples=n={n}:p=0,"
           "astats=metadata=1:reset=1:measure_overall=none:"
           "measure_perchannel=RMS_level,"
           "ametadata=print:key=lavfi.astats.1.RMS_level:file=-",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=1800)
    except (OSError, subprocess.TimeoutExpired):
        return []
    ra: list[float] = []
    for dong in (r.stdout or "").splitlines():
        if "lavfi.astats.1.RMS_level=" not in dong:
            continue
        try:
            v = float(dong.split("=", 1)[1].strip())
        except ValueError:
            v = -120.0
        # **`float("-inf")` PARSE ĐƯỢC — nên nhánh `except` KHÔNG BAO GIỜ bắt
        # được cửa sổ im tuyệt đối.** Docstring hàm này hứa trả -120,0 từ đầu
        # nhưng thực tế trả `-inf`, và cổng 78 bắt được: `-inf` làm mọi phép
        # TRUNG BÌNH ra `-inf` và mọi ngưỡng kiểu `sàn + 10` ra `-inf`, nên phép
        # so `x < ngưỡng` LUÔN False -> bộ đo im lặng không thấy gì.
        # Kẹp ở ĐÂY (cửa chung) chứ không ở từng nơi gọi: sót một nơi là một
        # phép đo phát chứng nhận khống.
        # KHÔNG đổi hành vi của `can_bang_giong_nhac`: nó lọc `> -70.0` nên -120
        # và -inf đều bị loại y như nhau.
        ra.append(-120.0 if v == float("-inf") else v)
    return ra


def _bpv(xs: list[float], p: float) -> float:
    if not xs:
        return -120.0
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def nen_lop_giong(giong_wav: str | Path, out_wav: str | Path,
                  muc_loi_db: float) -> str:
    """NÉN lớp giọng (chưa nâng mức) -> file mới. Trả đường dẫn.

    Tách hẳn thành MỘT LƯỢT RIÊNG để bước sau ĐO được kết quả thật thay vì
    suy ra. Đã thử suy ra và SAI: công thức nén cho đỉnh sau nén **-13,54
    dBFS**, đo thật lại ra **-2,99** — lệch 10,6 dB, vì `attack=5ms` CHO LỌT
    phụ âm bật (chính những mẫu tạo ra đỉnh). Đây đúng họ bẫy `astats` cổng
    53: phép đo suy diễn phát chứng nhận cho thứ không đúng.
    """
    nguong = 10.0 ** ((muc_loi_db + NEN_TREN_LOI_DB) / 20.0)
    _ffmpeg(["-i", str(giong_wav), "-af",
             f"acompressor=level_in=1:threshold={nguong:.6f}:"
             f"ratio={NEN_TI_LE:.1f}:attack=5:release=150:makeup=1:knee=6",
             "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
             str(out_wav)], "nén lớp giọng mới")
    _kiem_wav(out_wav)
    return str(out_wav)


def can_bang_giong_nhac(giong_wav: str | Path, nhac_wav: str | Path,
                        dich_db: float = DICH_GIONG_TREN_NHAC_DB) -> dict:
    """ĐO hai lớp rồi TÍNH hệ số — không chỉnh mò, không hằng số bịa.

    **VÌ SAO HÀM NÀY RA ĐỜI (lỗi anh Hùng 15/08: *"âm thanh sau khi tách lỗi
    hết, chỗ có chỗ không nghe không được"*).** Bản cũ trộn bằng HAI HẰNG SỐ
    `muc_giong_db=0` / `muc_nhac_db=-2`, tức giả định lớp nhạc và giọng TTS
    vốn đã ngang nhau. Đo trên chính video anh Hùng gửi thì KHÔNG:
    nhạc nền Douyin master rất to, còn edge-tts trả về mức vừa phải ->
    `giong_tren_nhac_db = **-10,61 dB**` (bản gốc tiếng Trung là **+3,35 dB**).
    Giọng mới nằm dưới nhạc hơn 10 dB thì chỗ nhạc lặng mới nghe ra tiếng =
    đúng chữ "chỗ có chỗ không".

    Cách đo phải là **LÚC ĐANG NÓI**, không phải RMS cả track: track giọng có
    tới ~30% là im lặng giữa các câu nên RMS toàn bài luôn thấp giả tạo — đọc
    số đó rồi kéo bù là kéo quá tay. (Cùng bài học "nền đo bằng `mean_volume`"
    của nhóm tiếng động.)

    Trả {gain_giong_db, gain_nhac_db, ...số đo}. Đo hỏng -> trả hệ số 0 và
    khoá `do_duoc=False`: thà giữ y bản cũ còn hơn nhân một hệ số bịa.
    """
    bg = duong_bao_muc(giong_wav)
    bn = duong_bao_muc(nhac_wav)
    n = min(len(bg), len(bn))
    if n < 5:
        return {"do_duoc": False, "gain_giong_db": 0.0, "gain_nhac_db": 0.0,
                "ly_do": "không dựng được đường bao mức"}
    dinh_g = _bpv(bg[:n], 0.95)
    nguong = dinh_g - DANG_NOI_DUOI_DB
    noi = [i for i in range(n) if bg[i] >= nguong and bg[i] > -70.0]
    if len(noi) < 3:
        return {"do_duoc": False, "gain_giong_db": 0.0, "gain_nhac_db": 0.0,
                "ly_do": "không tìm được cửa sổ đang nói"}
    muc_g = _bpv([bg[i] for i in noi], 0.5)
    muc_n = _bpv([bn[i] for i in noi], 0.5)
    hien_tai = muc_g - muc_n
    can = dich_db - hien_tai

    # ĐỈNH THẬT (không phải đỉnh đường bao RMS — xem chú thích
    # `DINH_GIONG_TOI_DA_DB`), ĐO trên chính file được đưa vào.
    dinh_tho = float(do_meo(giong_wav).get("dinh") or 0.0)
    nguong_nen_db = muc_g + NEN_TREN_LOI_DB
    tran_theo_dinh = max(0.0, DINH_GIONG_TOI_DA_DB - dinh_tho)
    # NÂNG GIỌNG TRƯỚC (không đụng tới nhạc là không mất gì của bản gốc),
    # chặn bởi 2 trần: trần nâng và ĐỈNH lớp giọng.
    g_giong = max(0.0, min(can, TANG_GIONG_TOI_DA_DB, tran_theo_dinh))
    # Còn thiếu bao nhiêu thì hạ nhạc — nhưng chỉ tới trần, phần dư để
    # `ducking` lo (né đúng chỗ, không hạ cả bài).
    g_nhac = -max(0.0, min(can - g_giong, HA_NHAC_TOI_DA_DB))
    return {
        "do_duoc": True,
        "gain_giong_db": round(g_giong, 2),
        "gain_nhac_db": round(g_nhac, 2),
        "nen_nguong_db": round(nguong_nen_db, 2),
        "nen_ti_le": NEN_TI_LE,
        "muc_giong_luc_noi_db": round(muc_g, 2),
        "muc_nhac_luc_noi_db": round(muc_n, 2),
        "giong_tren_nhac_truoc_db": round(hien_tai, 2),
        "can_bu_db": round(can, 2),
        "dinh_giong_db": round(dinh_tho, 2),
        "he_so_dinh_db": round(dinh_tho - muc_g, 2),
        "so_cua_so_noi": len(noi),
        "giay_noi": round(len(noi) * BUOC_DO_MUC, 2),
        "dich_db": dich_db,
    }


def do_giong_tren_nhac(giong_wav: str | Path, nhac_wav: str | Path) -> dict:
    """Thước NGHIỆM THU: giọng cao hơn nhạc bao nhiêu dB LÚC ĐANG NÓI.

    Tách riêng khỏi `can_bang_giong_nhac` để đo được cả TRƯỚC lẫn SAU bằng
    CÙNG một phép — dùng chính hàm tính hệ số để tự chấm là tự cấp chứng chỉ.
    """
    bg = duong_bao_muc(giong_wav)
    bn = duong_bao_muc(nhac_wav)
    n = min(len(bg), len(bn))
    if n < 5:
        return {"do_duoc": False}
    nguong = _bpv(bg[:n], 0.95) - DANG_NOI_DUOI_DB
    noi = [i for i in range(n) if bg[i] >= nguong and bg[i] > -70.0]
    if len(noi) < 3:
        return {"do_duoc": False}
    d = sorted(bg[i] - bn[i] for i in noi)
    return {
        "do_duoc": True,
        "giong_tren_nhac_tb": round(sum(d) / len(d), 2),
        "giong_tren_nhac_trung_vi": round(d[len(d) // 2], 2),
        "giong_tren_nhac_min": round(d[0], 2),
        "so_cua_so_chim": sum(1 for x in d if x < 0),
        "ty_le_chim": round(100.0 * sum(1 for x in d if x < 0) / len(d), 1),
        "so_cua_so_noi": len(noi),
    }


#: ĐÍCH ĐỘ TO TÍCH HỢP (LUFS) của bản trộn cuối — mức mạng xã hội chuẩn hoá về.
#:
#: **VÌ SAO PHẢI CÓ BƯỚC NÀY (anh Hùng 16/08/2026: *"phần giọng nói ít tiếng
#: quá nghe không hay"*):** đường thay tiếng TRƯỚC ĐÂY KHÔNG HỀ chuẩn hoá độ
#: to — chỉ có `alimiter` chặn đỉnh, mà chặn đỉnh KHÔNG nói gì về độ to nghe
#: được. Đo trên chính file anh Hùng xuất 16/08: **−16,00 LUFS**, trong khi
#: video GỐC là **−5,07 LUFS** — thấp hơn **10,9 LU**.
#:
#: YouTube/TikTok chỉ chuẩn hoá XUỐNG, KHÔNG nâng lên: clip −16 LUFS phát ra
#: nhỏ hơn hẳn mọi clip khác trong cùng luồng (chúng đều bị kéo về ~−14).
#: Đó đúng là chữ *"ít tiếng quá"*.
#:
#: **Lượt chữa "giọng chìm dưới nhạc" (15/08) LÀM NẶNG THÊM chứ không gây ra:**
#: trộn cách CŨ −12,76 -> cách MỚI −14,26 = nhỏ đi **1,50 LU**. Gỡ nguyên phần
#: đó ra vẫn còn thiếu ~3 LU nữa. Bệnh có TRƯỚC, lượt chữa chỉ cộng thêm.
DICH_LUFS = -14.0

#: Trần ĐỈNH THẬT (dBTP) của bản đã chuẩn hoá. Đỉnh thật (đo giữa các mẫu) mới
#: là cái quyết định có vỡ tiếng sau khi nén AAC hay không — đỉnh MẪU không đủ.
TRAN_DINH_THAT_DBTP = -1.0

#: Biên trừ hao đặt cho `alimiter` (nó chặn đỉnh MẪU, không chặn đỉnh THẬT).
#:
#: **PHẢI TRỪ HAI LẦN, KHÔNG PHẢI MỘT** — cả hai đều là SỐ ĐO trên chính file
#: anh Hùng, quét 5 mức trần:
#:
#: | trần `alimiter` | đỉnh thật của WAV | sau khi nén **AAC 192k** |
#: |---|---|---|
#: | −1,0 | −0,94 (**vượt**) | **−0,95 (VẪN VƯỢT)** |
#: | −1,2 | −1,14 | −1,15 |
#: | **−1,5** | **−1,44** | **−1,27** |
#: | −1,8 | −1,74 | −1,64 |
#: | −2,0 | −1,94 | −1,75 |
#:
#: (1) `alimiter` chặn đỉnh MẪU nên đỉnh THẬT (đo giữa các mẫu) vượt thêm
#:     **+0,06 dB**; (2) **nén AAC còn đẩy lên tiếp, đo được tới +0,19 dB** —
#:     bước này TRƯỚC ĐÂY KHÔNG AI TÍNH, và nó là lý do bản e2e v2.30.0 ra
#:     **+0,04 dBTP** (vỡ tiếng) dù lớp wav của nó mới −0,57.
#:
#: Chọn **0,5 dB**: bản AAC cuối ra −1,27 dBTP, còn dư 0,27 dB cho lượt nén
#: LẠI của TikTok (nó re-encode 128–192 kbps, mà AES TD1004 ghi rõ *coder bit
#: rate thấp vọt đỉnh nhiều hơn*). Giá phải trả: **0,01 LU** (−14,01 ->
#: −14,02) — tức gần như cho không.
BIEN_DINH_THAT_DB = 0.5

#: SÀN: bản trộn đo dưới mức này thì **BỎ QUA** bước chuẩn hoá.
#: Bản trộn gần câm (Demucs trả lớp rỗng · cả loạt câu TTS hỏng) đo ra
#: −60..−70 LUFS; nâng nó về −14 là +46..+56 dB, và thứ được nâng lúc đó là
#: NỀN NHIỄU chứ không phải tiếng nói. Thà giao file nhỏ tiếng còn hơn giao
#: file rít. `_kiem_wav` không bắt được ca này vì nó đo RMS, không đo LUFS.
SAN_LUFS_CHUAN_HOA = -45.0

#: Trần chỉnh độ to MỘT LƯỢT (dB, cả hai chiều). Bình thường chỉ cần 1-3 dB;
#: cần quá 24 dB nghĩa là bản trộn đã bất thường, và nâng tiếp cũng không cứu
#: được. Chặn ở đây để một lượt đo lỗi không đẻ ra file vỡ tiếng.
TRAN_CHINH_DO_TO_DB = 24.0


def do_do_to(path: str | Path) -> dict:
    """ĐỘ TO TÍCH HỢP + ĐỈNH THẬT + DẢI ĐỘNG, bằng pha ĐO của `loudnorm`.

    Trả `{"I": LUFS, "TP": dBTP, "LRA": LU, "thresh": LUFS}`.

    `print_format=json` in ra **stderr** (không phải stdout) — đọc nhầm cửa là
    ra rỗng rồi tưởng file câm. ffmpeg lỗi thì **NÉM**, tuyệt đối không trả
    `None` âm thầm: đó đúng là bẫy `astats` cổng 53 (*phép đo hỏng nguy hiểm
    hơn không đo, vì nó phát chứng nhận*).
    """
    import json as _json
    import re as _re

    # KHÔNG dùng `_ffmpeg`: nó ép `-loglevel error`, mà JSON của loudnorm in ở
    # mức `info` -> sẽ ra RỖNG rồi bị đọc nhầm thành "file câm".
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-nostdin",
           "-i", str(path), "-af",
           f"loudnorm=I={DICH_LUFS}:TP={TRAN_DINH_THAT_DBTP}"
           ":LRA=11:print_format=json", "-f", "null", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace",
                         stdin=subprocess.DEVNULL,
                         creationflags=_CREATE_NO_WINDOW)
    _gan_job(p)
    try:
        _out, err = p.communicate(timeout=900)   # BẮT BUỘC có hạn chờ
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        raise
    finally:
        _bo_gan_job(p)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi khi đo độ to (mã thoát {p.returncode}"
                           f"): {(err or '')[-500:]}")
    m = _re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err or "", _re.S)
    if not m:
        raise RuntimeError(f"loudnorm KHÔNG trả JSON khi đo {Path(path).name}")
    d = _json.loads(m.group(0))
    return {"I": float(d["input_i"]), "TP": float(d["input_tp"]),
            "LRA": float(d["input_lra"]), "thresh": float(d["input_thresh"])}


def chuan_do_to(wav_in: str | Path, wav_out: str | Path,
                dich: float = DICH_LUFS,
                tran_tp: float = TRAN_DINH_THAT_DBTP) -> dict:
    """Nâng bản trộn về `dich` LUFS bằng **MỘT HỆ SỐ TĨNH**, chặn đỉnh thật.

    **VÌ SAO KHÔNG DÙNG `loudnorm` ĐỂ ÁP (đã đo cả 3 cách, đây là số):**

    | cách | I | TP | LRA (vào 2,10) | độ lệch chuẩn hệ số |
    |---|---|---|---|---|
    | `loudnorm` MỘT lượt (động) | −13,81 | −1,00 | **2,00** | **0,277 dB** |
    | `loudnorm` HAI lượt `linear=true` | −14,11 | −0,99 | **1,90** | — |
    | **nâng thuần + hạn đỉnh (đang dùng)** | **−14,00** | −0,94* | **2,10** | **0,017 dB** |

    (*) trước khi trừ hao `BIEN_DINH_THAT_DB`; sau khi trừ ra **−1,14 dBTP**.

    **`linear=true` KHÔNG Ở LẠI TUYẾN TÍNH — nó TỰ TỤT VỀ ĐỘNG mà rc vẫn 0.**
    Trên chính file anh Hùng: cần nâng **+2,00 dB** nhưng chỗ trống tới trần
    đỉnh chỉ **1,26 dB**, nên ffmpeg in *"Normalization Type: Dynamic"* rồi
    làm động — LRA **2,10 -> 1,90**, tức **NÉN DẬP** đúng cái phải tránh. Chỉ
    đọc `rc` thì không bao giờ biết. Đây là họ bẫy "ffmpeg trả mã 0 mà kết quả
    sai" của cả repo này.

    **HỆ SỐ TĨNH GIỮ NGUYÊN CÂN BẰNG GIỌNG-NHẠC THEO TOÁN HỌC, không phải theo
    hy vọng:** nhân cả bản trộn với cùng một số thì hiệu (giọng − nhạc) ở MỌI
    cửa sổ không đổi một ly. Đo lại để chắc: giọng trên nhạc **+5,99 -> +5,99
    dB**, cửa sổ chìm **7,9% -> 7,9%**, y hệt từng chữ số.

    Phần vượt trần do `alimiter` gọt — nó chỉ đụng vài đỉnh nhọn, khác hẳn bộ
    nén động kéo lên dìm xuống suốt cả bài (0,017 so với 0,277 dB).
    """
    wav_in, wav_out = Path(wav_in), Path(wav_out)
    truoc = do_do_to(wav_in)
    can = dich - truoc["I"]
    tran_lim = tran_tp - BIEN_DINH_THAT_DB

    # CHẶN NÂNG ĐIÊN. Bản trộn gần như câm (Demucs trả lớp rỗng, TTS hỏng cả
    # loạt) đo ra -60..-70 LUFS -> `can` thành +46..+56 dB, và lúc đó thứ được
    # nâng KHÔNG phải tiếng nói mà là NỀN NHIỄU. Thà để nhỏ tiếng còn hơn đưa
    # cho anh Hùng một file rít. `_kiem_wav` đã chặn ca câm tuyệt đối, nhưng nó
    # đo RMS chứ không đo LUFS nên không bắt được ca "có tiếng mà bé xíu".
    if truoc["I"] < SAN_LUFS_CHUAN_HOA:
        return {"nang_db": 0.0, "bo_qua": True,
                "vi_sao": (f"bản trộn chỉ {truoc['I']:.2f} LUFS, dưới sàn "
                           f"{SAN_LUFS_CHUAN_HOA} — nâng lên là nâng nền "
                           f"nhiễu chứ không phải tiếng nói"),
                "truoc": {k: round(v, 2) for k, v in truoc.items()},
                "sau": {k: round(v, 2) for k, v in truoc.items()},
                "dat_dich": False, "qua_tran_dinh": False, "lra_doi": 0.0}
    can = max(-TRAN_CHINH_DO_TO_DB, min(TRAN_CHINH_DO_TO_DB, can))

    # `alimiter` BẮT BUỘC `level=0` (mặc định `level=true` TỰ NÂNG +3,1 dB —
    # tức tự phá đúng cái trần vừa đặt) và `latency=1` (không có thì trễ
    # 0,98 ms, đủ làm lệch hình-tiếng). Bẫy đã ghi ở đầu file.
    _ffmpeg(["-i", str(wav_in), "-af",
             f"volume={can:.3f}dB,alimiter=level_in=1:level_out=1:"
             f"limit={10.0 ** (tran_lim / 20.0):.6f}:level=0:latency=1",
             "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
             str(wav_out)], "chuẩn hoá độ to")
    _kiem_wav(wav_out)
    sau = do_do_to(wav_out)
    kq = {"nang_db": round(can, 2), "tran_alimiter_db": round(tran_lim, 2),
          "truoc": {k: round(v, 2) for k, v in truoc.items()},
          "sau": {k: round(v, 2) for k, v in sau.items()},
          "dat_dich": abs(sau["I"] - dich) <= 0.5,
          "qua_tran_dinh": sau["TP"] > tran_tp,
          "lra_doi": round(sau["LRA"] - truoc["LRA"], 2)}
    return kq


#: BÙ DẢI CAO ("bù sáng") — CHỮA ĐÚNG CÂU anh Hùng kêu 18/08/2026: *"lỗi quan
#: trọng: âm thanh video bị lỗi hay sao cứ bị bé"*.
#:
#: **ĐỘ TO TÍCH HỢP KHÔNG PHẢI THỦ PHẠM — ĐÃ ĐO, ĐỪNG ĐI SỬA LẠI CHỖ ĐÓ.**
#: Bản anh Hùng xuất 18/08 đo ra **−14,00 LUFS**, tức `chuan_do_to` (v2.31.0)
#: ĐÃ LÀM ĐÚNG VIỆC: video GỐC là −13,03, chỉ hơn **0,97 LU**. Hai thước độc
#: lập (`loudnorm` pha đo · `ebur128`) lệch nhau **0,00 LU**.
#: Chỗ hỏng nằm ở **CÂN BẰNG DẢI TẦN**. Quét 9 dải octave, GỐC so với bản
#: thay giọng (ebur128, LUFS):
#:
#: | dải Hz | GỐC | THAY GIỌNG | lệch |
#: |---|---|---|---|
#: | 250-500 | −21,90 | −21,10 | +0,80 |
#: | 500-1000 | −24,20 | −23,30 | +0,90 |
#: | 1000-2000 | −25,40 | −29,30 | **−3,90** |
#: | 2000-4000 | −25,00 | −32,20 | **−7,20** |
#: | 4000-8000 | −28,30 | −40,90 | **−12,60** |
#: | 8000-16000 | −28,20 | −51,20 | **−23,00** |
#:
#: Dải giọng nói (250-1000 Hz) khớp gốc trong **1 dB**, còn từ 2 kHz trở lên
#: mất 7-23 dB. Tai người nhạy nhất ở **2-5 kHz**, nên mất 7-12 dB ở đó nghe
#: ra ĐÚNG LÀ "bé" và đục — dù máy đo báo cùng một con số LUFS.
#:
#: **VÌ SAO MẤT (truy được, không đoán):** dải cao của bản gốc phần lớn là
#: **phụ âm gió của chính người dẫn gốc** — mà đó đúng là thứ Demucs bóc đi.
#: Đo lớp nhạc Demucs trả về: 8-16 kHz chỉ **−62,40 LUFS** (nguồn −27,60) =
#: coi như câm. Giọng thay vào thì cả edge-tts LẪN OmniVoice đều trả **24 kHz
#: mono** -> KHÔNG có gì trên 12 kHz, và đo được 8-16 kHz mới **−50,00**.
#: Tức không phải "app hạ nhạc quá tay" (đo `gain_nhac_db` = **0,00 dB** trên
#: chính nguồn này) mà là **chỗ trống do bóc giọng gốc không ai lấp lại**.
#:
#: **TRẦN +6 dB LÀ SỐ ĐO, KHÔNG PHẢI SỐ CHỌN.** Quét 5 mức trên chính bản
#: xuất (thiếu 9,70 dB):
#:
#: | bù | còn thiếu | I | TP |
#: |---|---|---|---|
#: | 0 | 9,70 | −14,02 | −1,45 |
#: | +4 | 6,20 | −13,94 | −1,46 |
#: | **+6** | **4,40** | **−13,87** | **−1,46** |
#: | +8 | 2,60 | −13,77 | −1,13 |
#: | +10 | 0,90 | −13,63 | **−0,95 (VƯỢT trần −1,0 dBTP)** |
#:
#: +6 đóng được **55%** khoảng thiếu mà đỉnh thật KHÔNG nhúc nhích (−1,45 ->
#: −1,46) và độ to chỉ đổi **0,15 LU**. +10 thì vỡ trần đỉnh. **ĐỪNG NỚI** —
#: nới là đổi tiếng lấy con số, đúng cái đã cấm ở `chuan_do_to`.
BU_SANG_TOI_DA_DB = 6.0

#: Thiếu ÍT HƠN mức này thì BỎ QUA hẳn (khỏi tốn 1 lượt ffmpeg cho thứ không
#: ai nghe ra). Nguồn nào bản trộn vốn đã sáng bằng gốc thì bước này KHÔNG
#: CHẠY — an toàn DO XÂY DỰNG, không phải do hy vọng.
BU_SANG_TOI_THIEU_DB = 1.0

#: Tần số gối của bộ lọc kệ cao. Đặt ở 3,5 kHz (không phải 4 kHz) để phần
#: 2-4 kHz — dải tai nhạy nhất, đang thiếu 7,20 dB — cũng được nâng một phần.
BU_SANG_TAN_SO = 3500.0

#: Dải THAM CHIẾU và dải CAO của phép đo "độ sáng". Lấy 300-3000 Hz làm mốc vì
#: đo được bản trộn ĐÃ khớp gốc ở đó (lệch < 1 dB) — mốc phải là chỗ không
#: hỏng, không thì phép trừ đo lẫn cả hai lỗi.
_AF_SANG_MID = ("highpass=f=300:poles=2,highpass=f=300:poles=2,"
                "lowpass=f=3000:poles=2,lowpass=f=3000:poles=2")
_AF_SANG_HI = "highpass=f=4000:poles=2,highpass=f=4000:poles=2"


def do_do_sang(path: str | Path) -> float:
    """ĐỘ SÁNG = mức dải >4 kHz TRỪ mức dải 300-3000 Hz (dB). Càng lớn càng sáng.

    **MỘT lượt ffmpeg cho CẢ HAI dải** (`asplit` + 2 `astats`) — đo hai lượt
    riêng thì đắt gấp đôi mà không chính xác hơn, vì đây là phép TRỪ hai dải
    của CÙNG một file.

    Số này là TƯƠNG ĐỐI nên không phụ thuộc thước: dùng `astats` (RMS) hay
    `ebur128` (K-weighted) đều ra cùng một kết luận, đã đối chiếu.

    Đo hỏng -> trả `nan`; nơi gọi phải coi `nan` là "không bù" chứ đừng nhân
    một hệ số bịa (bài học `astats` cổng 53: phép đo hỏng phát chứng nhận).

    BẪY: mỗi dòng `astats` mở đầu bằng `[Parsed_astats_N @ ...]` nên phải dùng
    `in`, KHÔNG `startswith` (cổng 44).
    """
    import math

    fc = (f"[0:a]asplit=2[m][h];"
          f"[m]{_AF_SANG_MID},astats@bqmid=measure_perchannel=none"
          f":measure_overall=RMS_level[mo];"
          f"[h]{_AF_SANG_HI},astats@bqhi=measure_perchannel=none"
          f":measure_overall=RMS_level[ho]")
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-nostdin",
           "-i", str(path), "-filter_complex", fc,
           "-map", "[mo]", "-f", "null", "-",
           "-map", "[ho]", "-f", "null", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=1800)
    except (OSError, subprocess.TimeoutExpired):
        return float("nan")
    if p.returncode != 0:
        return float("nan")
    # ĐỌC THEO **TÊN FILTER** (`astats@bqmid` / `astats@bqhi`), KHÔNG theo thứ
    # tự dòng in ra.
    #
    # **BẪY ĐÃ SẬP THẬT KHI VIẾT HÀM NÀY (18/08/2026), và nó IM LẶNG:** bản
    # đầu lấy `muc[1] - muc[0]` với lý lẽ "astats in theo thứ tự khai báo".
    # SAI — ffmpeg giải phóng filter theo thứ tự NGƯỢC, nên dòng đầu là dải
    # CAO. Độ lớn vẫn ra **9,65 dB** (khớp ebur128 9,70 tới 0,05 dB) nên nhìn
    # số là thấy "đúng", chỉ có **DẤU BỊ LẬT** -> app sẽ đi CẮT dải cao đúng
    # lúc cần NÂNG. Bắt được là nhờ đối chiếu với thước thứ hai; đọc một thước
    # thôi thì bản vá này đã làm tiếng đục THÊM mà vẫn khoe đã chữa.
    muc: dict[str, float] = {}
    for dong in (p.stderr or "").splitlines():
        if "RMS level dB:" not in dong:
            continue
        khoa = ("mid" if "astats@bqmid" in dong else
                ("hi" if "astats@bqhi" in dong else ""))
        if not khoa:
            continue
        try:
            muc[khoa] = float(dong.split("RMS level dB:")[1].strip())
        except (ValueError, IndexError):
            pass
    if len(muc) < 2 or any(math.isinf(x) or math.isnan(x)
                           for x in muc.values()):
        return float("nan")
    return muc["hi"] - muc["mid"]


def bu_sang(wav_in: str | Path, wav_out: str | Path, g_db: float,
            tran_dinh_db: float = TRAN_DINH_DB) -> None:
    """Nâng dải cao thêm `g_db` bằng BỘ LỌC KỆ (high shelf) + hạn đỉnh.

    Dùng `treble` (kệ cao) chứ KHÔNG dùng bộ nén đa dải: kệ là phép NHÂN HẰNG
    theo tần số nên KHÔNG đụng tới dải động (đo LRA 1,90 -> 1,90) và KHÔNG đổi
    cân bằng giọng-nhạc trong dải lời nói.

    `alimiter` bắt buộc `level=0` + `latency=1` — bẫy đã ghi ở đầu file.
    """
    _ffmpeg(["-i", str(wav_in), "-af",
             f"treble=g={g_db:.2f}:f={BU_SANG_TAN_SO:.0f}"
             f":width_type=q:w=0.6,"
             f"alimiter=level_in=1:level_out=1:limit="
             f"{10.0 ** (tran_dinh_db / 20.0):.6f}:level=0:latency=1",
             "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
             str(wav_out)], "bù dải cao cho bản trộn")
    _kiem_wav(wav_out)


def tron_thay_giong(nhac_wav: str | Path, manh: list[tuple[float, str]],
                    tong: float, out_wav: str | Path,
                    muc_giong_db: float = 0.0, muc_nhac_db: float = 0.0,
                    tran_dinh_db: float = TRAN_DINH_DB,
                    tu_can_bang: bool = True, duck: bool = True,
                    chuan_do_to_bat: bool = True,
                    goc_wav: str | Path = "",
                    on_progress: Optional[Callable[[float, str], None]] = None,
                    ) -> dict:
    """Trộn GIỌNG MỚI lên LỚP NỀN, hạn đỉnh chống méo, rồi ĐO cân bằng.

    **HÀM NÀY PHỤC VỤ CẢ HAI CÁCH TRỘN** (xem `CACH_TRON` ở đầu file) và không
    hề biết mình đang chạy cách nào — chỗ khác nhau duy nhất là `nhac_wav`:
      · cách `"tach"`: `nhac_wav` = lớp NHẠC do Demucs tách ra.
      · cách `"de"`:   `nhac_wav` = **CHÍNH audio GỐC** (còn cả giọng gốc).
    Đó là lý do không có đường trộn thứ hai: `can_bang_giong_nhac` ĐO lớp nền
    rồi mới tính hệ số, nên nền to hơn (có thêm giọng gốc) thì nó tự hạ nền
    nhiều hơn — trong trần `HA_NHAC_TOI_DA_DB` — còn `sidechaincompress` thì
    vốn đã né theo CỬA SỔ giọng lồng, không hạ đều cả bài. Cả hai cơ chế đúng
    cho cách mới mà không phải sửa một dòng nào.

    `tu_can_bang=True` (mặc định): hệ số lấy từ `can_bang_giong_nhac` — ĐO hai
    lớp rồi tính, thay cho hai hằng số cũ. `muc_giong_db`/`muc_nhac_db` vẫn
    được cộng vào (người dùng còn chỉnh tay được), chỉ khác là nay chúng là
    phần BÙ THÊM chứ không phải toàn bộ câu trả lời.

    **HAI THAM SỐ ĐÓ NAY LÀ HAI Ô THẬT TRONG HỘP THAY GIỌNG** (v2.42.0, anh
    Hùng 20/08/2026: *"phần âm thanh gốc nó nói bé k tuỳ chỉnh âm thanh đc à"*).
    Cả hai đi qua `chuan_muc_db` (kẹp ±`TRAN_MUC_TAY_DB`, làm tròn 0,1 dB, rác
    -> 0,0) NGAY TRONG hàm này, nên payload cũ/lối gọi khác không lọt được một
    hệ số bịa nào. `0,0` = MẶC ĐỊNH và khối trần an toàn bên dưới **không chạy
    một dòng nào** -> tiếng ra giống HỆT bản trước, không phải "gần giống".

    **`muc_nhac_db` MẶC ĐỊNH ĐỔI -2,0 -> 0,0 CÓ CHỦ Ý:** -2 dB cũ là một hằng
    số đặt mò cho việc "nhường chỗ cho lời". Nay phần nhường chỗ đã do phép đo
    quyết định (`gain_nhac_db`) nên giữ -2 nữa là TRỪ HAI LẦN — mà mỗi dB nhạc
    mất đi là một dB đi ngược mục tiêu "giữ nguyên nhạc nền". Truyền tay giá
    trị khác thì vẫn được cộng như cũ.

    `duck=True`: nhạc NÉ giọng bằng `sidechaincompress` — tụt ~`DUCK_DB` dB ở
    đúng chỗ đang nói, chỗ không nói giữ NGUYÊN. Đây là lý do không phải hạ
    nhạc cả bài để nghe rõ lời.

    `chuan_do_to_bat=True` (mặc định): bước CUỐI nâng cả bản trộn về
    `DICH_LUFS`. **Bước này chữa đúng câu anh Hùng kêu 16/08 (*"ít tiếng
    quá"*)** — xem `chuan_do_to`. Nó dùng MỘT HỆ SỐ TĨNH nên KHÔNG đụng tới
    cân bằng giọng-nhạc mà mấy trăm dòng ở trên vừa đo ra; đo lại sau khi nâng
    vẫn đúng **+5,99 dB / 7,9%**, không lệch một chữ số.
    Hỏng ở bước này thì GIỮ bản trộn chưa nâng (nhỏ tiếng còn hơn mất video).

    `alimiter` bắt buộc `level=0` (mặc định `level=true` TỰ NÂNG +3,1 dB) và
    `latency=1` (không có thì trễ 0,98 ms) — bẫy đã ghi ở đầu file.
    """
    import math

    out_wav = Path(out_wav)
    tam = out_wav.with_suffix(".giong.wav")
    if on_progress:
        on_progress(0.2, "Ghép track giọng mới...")
    _ghep_track_giong(manh, tong, tam)
    _kiem_wav(tam)

    # HAI VÒNG ĐO, KHÔNG PHẢI MỘT. Vòng 1 đo track giọng THÔ để biết ngưỡng
    # nén; nén ra file riêng; vòng 2 đo lại CHÍNH FILE ĐÃ NÉN để tính mức
    # nâng. Suy ra đỉnh-sau-nén bằng công thức đã sai 10,6 dB (xem
    # `nen_lop_giong`), nên bước ĐO LẠI này là bắt buộc chứ không phải cho
    # chắc. Giá: 1 lượt ffmpeg trên audio (~1-2 s cho video 107 s).
    cb: dict = {"do_duoc": False}
    giong_vao = tam
    if tu_can_bang:
        if on_progress:
            on_progress(0.4, "Đo mức giọng so với nhạc nền...")
        cb0 = can_bang_giong_nhac(tam, nhac_wav)
        if cb0.get("do_duoc"):
            if on_progress:
                on_progress(0.5, "Nén lớp giọng cho đều...")
            giong_vao = out_wav.with_suffix(".giong_nen.wav")
            nen_lop_giong(tam, giong_vao, float(cb0["muc_giong_luc_noi_db"]))
            cb = can_bang_giong_nhac(giong_vao, nhac_wav)
            cb["truoc_nen"] = {k: cb0.get(k) for k in
                               ("muc_giong_luc_noi_db", "dinh_giong_db",
                                "he_so_dinh_db", "giong_tren_nhac_truoc_db")}
        else:
            cb = cb0
    # HAI Ô NGƯỜI DÙNG đi qua `chuan_muc_db` — CỬA DUY NHẤT chuẩn hoá (kẹp
    # trần + làm tròn 0,1 dB + rác thành 0,0). Gọi ở ĐÂY nữa, không chỉ ở UI:
    # payload job cũ / lối gọi khác / cổng test đều vào cửa này, và một hệ số
    # bịa nhân vào tiếng là thứ không có đường lùi.
    muc_giong_db = chuan_muc_db(muc_giong_db)
    muc_nhac_db = chuan_muc_db(muc_nhac_db)
    g_giong = muc_giong_db + (cb.get("gain_giong_db") or 0.0)
    g_nhac = muc_nhac_db + (cb.get("gain_nhac_db") or 0.0)

    # ---- TRẦN AN TOÀN: người dùng TĂNG giọng thì vẫn không được vỡ tiếng ----
    # **CHỈ CHẠY KHI `muc_giong_db > 0`** — nghĩa là để MẶC ĐỊNH (0,0) hay HẠ
    # giọng thì khối này không đụng tới một biến nào, và đó chính là bằng chứng
    # "mặc định ra tiếng GIỐNG HỆT hôm nay" ở mức mã chứ không phải mức lời.
    #
    # Phần TỰ ĐỘNG đã tự kẹp bằng `tran_theo_dinh` (xem `can_bang_giong_nhac`)
    # nên nó không bao giờ vượt trần −3; chỗ có thể vượt là phần CỘNG TAY. Kẹp
    # theo ĐỈNH ĐO ĐƯỢC của chính lớp giọng đã nén, không theo hằng số bịa.
    tay: dict = {}
    if muc_giong_db > 0.0 and cb.get("do_duoc"):
        tran_tay = max(0.0, DINH_GIONG_TAY_TOI_DA_DB
                       - float(cb.get("dinh_giong_db") or 0.0))
        if g_giong > tran_tay:
            tay = {
                "giong_xin_db": muc_giong_db,
                "giong_cho_db": round(
                    tran_tay - (cb.get("gain_giong_db") or 0.0), 2),
                "bi_kep": True,
                "vi_sao": (f"đỉnh lớp giọng {cb.get('dinh_giong_db')} dBFS + "
                           f"nâng {g_giong:.2f} dB sẽ vượt trần "
                           f"{DINH_GIONG_TAY_TOI_DA_DB} dBFS — hạn đỉnh phải "
                           f"gọt ngay trên tiếng nói"),
            }
            g_giong = tran_tay

    if on_progress:
        on_progress(0.6, "Trộn giọng mới với nhạc nền gốc...")
    # NHÁNH NHẠC: chỉnh mức -> (nếu bật) NÉ GIỌNG. Ngưỡng nén bám theo MỨC
    # NHẠC ĐO ĐƯỢC (sau khi đã chỉnh `g_nhac`), không phải hằng số: cùng một
    # `threshold=0.03` thì phim nhạc to tụt 10 dB còn phim nhạc nhỏ không tụt
    # tí nào — tức tính năng chạy hay không tuỳ may.
    nhac_sau = (cb.get("muc_nhac_luc_noi_db") or -14.0) + g_nhac
    nguong_duck, ratio_duck = _tham_so_duck(nhac_sau)
    # **KHÔNG DÙNG `asplit` ĐỂ LẤY TÍN HIỆU KHOÁ CHO `sidechaincompress`.**
    # ĐO ĐƯỢC 15/08/2026: `[gi]asplit=2[gi1][gikey]` rồi cho một nhánh vào
    # `sidechaincompress` còn nhánh kia vào `amix=duration=first` làm **ĐỘ DÀI
    # ĐẦU RA KHÔNG TIỀN ĐỊNH** — chạy 3 lượt CÙNG một lệnh, cùng file, ra
    # **107,183 · 107,254 · 107,183 giây**, và trong lượt dây chuyền thật ra
    # **106,162** (hụt 1,09 s). Hai nhánh asplit bị tiêu thụ ở nhịp khác nhau
    # nên EOF lan tới `amix` sớm muộn tuỳ lượt. rc=0, không một dòng báo —
    # đúng họ bẫy "ffmpeg trả mã 0 mà file sai" của cả repo này.
    # CHỮA: mở CHÍNH FILE ĐÓ THÊM MỘT ĐẦU VÀO (`-i` thứ ba, giải mã wav là
    # rẻ) -> không còn nhánh dùng chung. VÀ ép độ dài bằng `apad`+`atrim` —
    # hai lớp, vì đây là chỗ `kiem_video_ra` đã bắt được lỗi thật.
    fc = [f"[0:a]volume={g_nhac:.2f}dB[nh0]",
          f"[1:a]volume={g_giong:.2f}dB[gi]"]
    vao = ["-i", str(nhac_wav), "-i", str(giong_vao)]
    if duck:
        vao += ["-i", str(giong_vao)]
        fc.append(f"[2:a]volume={g_giong:.2f}dB[gikey]")
        fc.append(
            f"[nh0][gikey]sidechaincompress=threshold={nguong_duck:.5f}"
            f":ratio={ratio_duck:.3f}:attack=20:release=300:makeup=1"
            ":level_sc=1[nh]")
    else:
        fc.append("[nh0]anull[nh]")
    fc.append("[nh][gi]amix=inputs=2:duration=first:normalize=0[mx]")
    fc.append(f"[mx]alimiter=level_in=1:level_out=1:limit="
              f"{10.0 ** (tran_dinh_db / 20.0):.6f}:level=0:latency=1[lim]")
    # ÉP ĐÚNG ĐỘ DÀI: thiếu thì đệm im lặng, thừa thì cắt. Không có bước này
    # thì mỗi lượt xuất ra một độ dài khác nhau -> `kiem_video_ra` đỏ ngẫu
    # nhiên, và tệ hơn là hình-tiếng lệch dần về cuối phim.
    fc.append(f"[lim]apad,atrim=0:{tong:.3f},asetpts=N/SR/TB[out]")
    _ffmpeg([*vao, "-filter_complex", ";".join(fc),
             "-map", "[out]", "-ac", "2", "-ar", str(SR_TACH),
             "-c:a", "pcm_s16le", str(out_wav)], "trộn giọng mới + nhạc")
    _kiem_wav(out_wav)
    _d = probe_duration(out_wav)
    if abs(_d - tong) > 0.05:
        raise RuntimeError(
            f"Bản trộn dài {_d:.3f}s, phải là {tong:.3f}s "
            f"(lệch {_d - tong:+.3f}s) — KHÔNG ghép vào video")

    # ---- BÙ DẢI CAO — ĐẶT TRƯỚC chuẩn hoá độ to, CÓ LÝ DO ----
    # Bù sáng làm đổi độ to (đo: +6 dB -> I nhích 0,15 LU), nên phải bù XONG
    # rồi mới đo-và-nâng; làm ngược lại là chuẩn hoá cho một bản không còn tồn
    # tại. Hệ số lấy từ CHÍNH VIDEO GỐC của lượt này, không phải hằng số:
    # nguồn nào vốn đã đục thì `thieu` ra nhỏ và bước này TỰ KHÔNG CHẠY.
    bu: dict = {}
    if goc_wav and Path(goc_wav).exists():
        import math as _mt
        if on_progress:
            on_progress(0.86, "Đo cân bằng dải tần so với bản gốc...")
        s_goc = do_do_sang(goc_wav)
        s_ra = do_do_sang(out_wav)
        thieu = (s_goc - s_ra) if not (_mt.isnan(s_goc) or _mt.isnan(s_ra)) \
            else float("nan")
        bu = {"sang_goc_db": None if _mt.isnan(s_goc) else round(s_goc, 2),
              "sang_tron_db": None if _mt.isnan(s_ra) else round(s_ra, 2),
              "thieu_db": None if _mt.isnan(thieu) else round(thieu, 2)}
        if _mt.isnan(thieu):
            bu["bu_db"] = 0.0
            bu["bo_qua"] = "đo độ sáng hỏng — KHÔNG bù (thà giữ nguyên còn hơn "
            bu["bo_qua"] += "nhân một hệ số bịa)"
        elif thieu < BU_SANG_TOI_THIEU_DB:
            bu["bu_db"] = 0.0
            bu["bo_qua"] = (f"chỉ thiếu {thieu:.2f} dB, dưới "
                            f"{BU_SANG_TOI_THIEU_DB} — không ai nghe ra")
        else:
            g = min(thieu, BU_SANG_TOI_DA_DB)
            _tam_bu = out_wav.with_suffix(".busang.wav")
            try:
                bu_sang(out_wav, _tam_bu, g, tran_dinh_db)
                _db = probe_duration(_tam_bu)
                if abs(_db - tong) > 0.05:
                    raise RuntimeError(
                        f"Bản bù sáng dài {_db:.3f}s, phải là {tong:.3f}s")
                os.replace(_tam_bu, out_wav)
                bu["bu_db"] = round(g, 2)
                bu["cham_tran_bu"] = round(g, 2) == BU_SANG_TOI_DA_DB
                bu["sang_sau_db"] = round(do_do_sang(out_wav), 2)
            except Exception as e:  # noqa: BLE001
                # Bù sáng là bước LÀM ĐẸP — hỏng thì giữ bản trộn cũ, tuyệt
                # đối không để cả video chết vì nó (y như `chuan_do_to`).
                bu["bu_db"] = 0.0
                bu["loi"] = str(e)
                Path(_tam_bu).unlink(missing_ok=True)

    # ---- CHUẨN HOÁ ĐỘ TO — bước CUỐI, sau khi độ dài đã chốt ----
    # Đặt ở đây chứ không nhét vào chuỗi filter trên: muốn nâng bao nhiêu thì
    # phải ĐO bản trộn đã xong, mà đo được thì nó phải tồn tại rồi. Giá: thêm
    # 2 lượt ffmpeg CHỈ TRÊN AUDIO (~2 s cho video 107 s).
    # `volume` + `alimiter` KHÔNG đổi độ dài, nhưng vẫn kiểm lại bên dưới —
    # đây đúng chỗ `asplit` từng làm độ dài không tiền định mà rc vẫn 0.
    do_to: dict = {}
    if chuan_do_to_bat:
        if on_progress:
            on_progress(0.9, "Chuẩn hoá độ to...")
        _tam_ch = out_wav.with_suffix(".chuan.wav")
        try:
            do_to = chuan_do_to(out_wav, _tam_ch)
            _dc = probe_duration(_tam_ch)
            if abs(_dc - tong) > 0.05:
                raise RuntimeError(
                    f"Bản chuẩn hoá dài {_dc:.3f}s, phải là {tong:.3f}s "
                    f"(lệch {_dc - tong:+.3f}s)")
            os.replace(_tam_ch, out_wav)
        except Exception as e:  # noqa: BLE001
            # Chuẩn hoá hỏng thì GIỮ BẢN TRỘN CŨ (vẫn nghe được, chỉ nhỏ tiếng)
            # — KHÔNG để cả video chết vì bước làm-đẹp này.
            do_to = {"loi": str(e)}
            Path(_tam_ch).unlink(missing_ok=True)

    meo = do_meo(out_wav)
    kq = {
        "ra": str(out_wav),
        "do_to": do_to,
        "bu_sang": bu,
        "rms_giong": round(do_rms(tam), 6),
        "rms_nhac": round(do_rms(nhac_wav), 6),
        "rms_tron": round(do_rms(out_wav), 6),
        "dinh_dbfs": meo.get("dinh"),
        "cham_tran": meo.get("cham_tran"),
        "do_dai": round(probe_duration(out_wav), 3),
        "can_bang": cb,
        "gain_giong_db": round(g_giong, 2),
        "gain_nhac_db": round(g_nhac, 2),
        # HAI Ô NGƯỜI DÙNG phải nằm trong nhật ký: đọc lại một lượt cũ mà không
        # biết anh Hùng đã kéo mấy dB thì không đối chiếu được gì (bài học
        # `cach_tron` phải vào `result`, cổng 86). 0,0 = để mặc định.
        "muc_tay_giong_db": muc_giong_db,
        "muc_tay_nen_db": muc_nhac_db,
        "muc_tay_kep": tay,
        "duck_db_du_kien": DUCK_DB_DO_DUOC if duck else 0.0,
        "duck_nguong": round(nguong_duck, 5) if duck else 0.0,
        "duck_ratio": round(ratio_duck, 3) if duck else 0.0,
        "giong_track": str(tam),
        "giong_da_nen": str(giong_vao),
    }
    g, n = kq["rms_giong"], kq["rms_nhac"]
    if g > 0 and n > 0:
        # RMS CẢ TRACK của lớp giọng THÔ — giữ lại để so với các lượt cũ, NHƯNG
        # nó KHÔNG phải con số nói lên "có nghe được lời không": track giọng
        # ~30% là im lặng nên nó thấp giả tạo, và nó đo bản CHƯA nâng.
        kq["giong_tren_nhac_db_tho"] = round(20.0 * math.log10(g / n), 2)
    if cb.get("do_duoc"):
        # CON SỐ ĐÁNG ĐỌC: giọng cao hơn nhạc bao nhiêu dB LÚC ĐANG NÓI, sau
        # khi đã áp hệ số. Cộng thêm phần nhạc NÉ đi (đo được, xem DUCK_RATIO).
        tinh = float(cb["giong_tren_nhac_truoc_db"]) + g_giong - g_nhac
        kq["giong_tren_nhac_tinh_db"] = round(tinh, 2)
        kq["giong_tren_nhac_ke_ne_db"] = round(
            tinh + (DUCK_DB_DO_DUOC if duck else 0.0), 2)
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
                     dong_chu: Optional[list] = None,
                     kieu_chu: Optional[dict] = None,
                     he_so_hinh: float = 1.0) -> None:
    """Thay TIẾNG của video. `che_chu=False` -> GIỮ NGUYÊN hình (`-c:v copy`).

    `he_so_hinh > 1` = chế độ **"Chỉnh video theo giọng"**: làm CHẬM hình đúng
    hệ số đó để giọng được đọc ở tốc độ TỰ NHIÊN (xem `he_so_hinh_can`).

    **LÀM CHẬM HÌNH MÀ VẪN `-c:v copy` — đây là chỗ đáng nói nhất:** dùng
    `-itsscale` (nhân mốc thời gian của ĐẦU VÀO) chứ không `setpts`. `setpts`
    là filter nên bắt buộc encode lại cả luồng hình — với video 10 phút × 200-
    300 kênh thì đó là hàng giờ máy và một đời nén nữa. `-itsscale` chỉ ghi lại
    mốc lúc remux: **0 khung nào bị mã hoá lại, 0 điểm ảnh nào đổi**.
    Giá phải trả (nói thẳng): nó KHÔNG sinh khung mới, nên nhịp hình hiệu dụng
    tụt đúng theo hệ số — xem trần `SAN_NHIP_HINH_FPS`.

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
    # `-itsscale` chỉ được thêm khi THẬT SỰ làm chậm hình. `he_so_hinh = 1.0`
    # -> danh sách RỖNG -> lệnh ffmpeg giống **TỪNG KÝ TỰ** bản cũ (bất biến
    # cổng 59 đo, và cổng 76 canh lại).
    k = max(1.0, float(he_so_hinh or 1.0))
    its = ["-itsscale", f"{k:.6f}"] if k > 1.0 + 1e-6 else []

    if not che_chu:
        _ffmpeg([*its, "-i", str(video_goc), "-i", str(audio_moi),
                 "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                 "-c:a", "aac", "-b:a", "192k", "-shortest", str(video_ra)],
                "thay tiếng vào video", timeout=1800)
        if che_chu_log is not None:
            che_chu_log.append({"bat": False, "che": False, "ly_do": "",
                               "he_so_hinh": round(k, 4)})
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
        thay_audio_video(video_goc, audio_moi, video_ra, che_chu=False,
                         he_so_hinh=k)
        return

    # --- CHỮ MỚI THEO MỐC GIỌNG (chỉ khi ĐÃ che — cấm 2 lớp chữ) ---
    chuoi = [loc]
    so_dong = 0
    if dong_chu:
        try:
            d_viet = dai if (dai is not None and getattr(dai, "co_chu", False)
                             and dai.cao_dai > 0) else None
            ass = Path(video_ra).with_suffix(".chu_theo_giong.ass")
            # `kieu_chu` = ĐƠN THUỐC KIỂU CHỮ user đặt trong hộp Thay giọng
            # (cỡ · phông · đậm · nghiêng · màu chữ · màu viền · độ dày viền ·
            # vị trí · kiểu có sẵn của Chỉnh mẫu). None/rỗng -> .ass giống
            # TỪNG BYTE bản cũ, xem `che_chu.ghi_ass`.
            if d_viet is not None and _CC.ghi_ass(dong_chu, ass, d_viet,
                                                  kieu=kieu_chu):
                # nối bằng DẤU PHẨY: `loc` là GRAPH kết bằng `overlay=`, nối
                # `;subtitles=` là đẻ chuỗi RỜI không đầu vào (bẫy đã ghi ở
                # `che_chu.che_va_viet`). Phẩy = viết chữ SAU khi che xong.
                # `chuoi_subtitles` LUÔN kèm `fontsdir` — thiếu nó thì phông
                # đóng gói (Anton/Be Vietnam Pro…) KHÔNG được libass tìm ra,
                # nó lùi im lặng về phông mặc định mà ffmpeg vẫn trả mã 0, tức
                # ô chọn phông chỉ là cái nhãn (đo 17/08/2026).
                chuoi.append(_CC.chuoi_subtitles(ass))
                so_dong = len(dong_chu)
        except Exception as e:      # noqa: BLE001 — chữ mới KHÔNG được giết lượt
            so_dong = 0
            if che_chu_log:
                che_chu_log[-1]["chu_loi"] = str(e)[:200]
    if che_chu_log:
        che_chu_log[-1]["so_dong_chu"] = so_dong

    from app.core.ffmpeg_utils import detect_encoder
    enc = detect_encoder()
    # `-profile:v high` + `-movflags +faststart`: xem `ffmpeg_utils._enc_args`.
    # Trình phát Windows từ chối High 10 / High 4:4:4 (0x80004005 + khung
    # trắng); thiếu `moov` ở đầu file thì phát qua mạng/ứng dụng nào đọc dần
    # cũng báo hỏng. Ép ở CẢ HAI nhánh, không chỉ nhánh nvenc.
    if enc == "h264_nvenc":
        ve = ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr",
              "-cq", "21", "-pix_fmt", "yuv420p", "-profile:v", "high"]
    else:
        ve = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-pix_fmt", "yuv420p", "-profile:v", "high"]
    # NHÁNH CHE CHỮ: `-itsscale` vẫn dùng được (nó đụng mốc ĐẦU VÀO, trước cả
    # filter) nên KHÔNG cần `setpts` — chuỗi filter che chữ giữ nguyên. Mốc
    # hộp che lấy từ `segs=[(0, dur)]` của video GỐC, mà `-itsscale` giãn đều
    # nên hộp vẫn bám đúng chỗ chữ cũ.
    _ffmpeg([*its, "-i", str(video_goc), "-i", str(audio_moi),
             "-filter_complex", f"[0:v]{','.join(chuoi)}[vout]",
             "-map", "[vout]", "-map", "1:a:0", *ve,
             "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", str(video_ra)],
            "thay tiếng + che chữ vào video", timeout=3600)


#: Chữ mới phải nằm ít nhất bấy nhiêu giây trên màn hình — câu đọc 0,2 giây mà
#: chữ chớp 0,2 giây thì không ai đọc kịp. Nới về SAU (chưa tới câu kế) nên
#: không bao giờ che mất chữ của câu sau.
CHU_TOI_THIEU_S = 0.90

#: Chừa lại trước mốc nói của câu KẾ — chữ hai câu dính nhau nhìn như nhảy.
CHU_CHUA_TRUOC_S = 0.06

#: TRẦN KÝ TỰ MỖI LẦN HIỆN CHỮ — con số anh Hùng nhìn thấy trực tiếp.
#: Ảnh anh ấy gửi 15/08 là **MỘT KHỐI 3 DÒNG / 131 ký tự** đổ ra cùng lúc.
#: Chọn bằng SỐ ĐO (`_do_cum_chu.py`, 39 câu bản dịch THẬT của chính video
#: đó), không đoán: xem bảng ở `chia_cum_theo_tu`.
TRAN_KY_TU_CUM = 30

#: Cụm ngắn hơn mức này thì GỘP với cụm kế — 2 chữ chớp 0,2 giây còn khó đọc
#: hơn cả câu dài. Gộp chứ không giãn: giãn là lấn sang cụm sau.
CUM_TOI_THIEU_S = 0.45

#: Dấu ngắt câu (cả dạng nửa-độ-rộng lẫn CJK) — cắt cụm ở đây thì câu không
#: bị đứt giữa mệnh đề.
_DAU_NGAT = ",.!?;:…，。！？；：、"


def _khop_tu_vao_chu(text: str, moc: list) -> list:
    """Gắn từng mốc-từ vào ĐÚNG vị trí ký tự của nó trong `text`. Hàm THUẦN.

    Trả `[(char_dau, char_cuoi, giây_a, giây_b)]`. Từ nào không tìm thấy trong
    text (edge-tts đôi khi trả từ đã chuẩn hoá) thì BỎ QUA chứ không đoán —
    các từ còn lại vẫn đủ để chia cụm, còn đoán bừa là chữ nhảy lung tung.

    Đi TIẾN theo con trỏ nên từ lặp lại (`the ... the`) vẫn khớp đúng lần
    xuất hiện của nó, không dính về lần đầu.
    """
    ra: list = []
    cur = 0
    thap = text.lower()
    for m in moc or ():
        try:
            w = str(m[2] or "").strip()
            a, b = float(m[0]), float(m[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not w:
            continue
        j = text.find(w, cur)
        if j < 0:
            j = thap.find(w.lower(), cur)
        if j < 0:
            continue
        ra.append((j, j + len(w), a, b))
        cur = j + len(w)
    return ra


def chia_cum_theo_tu(text: str, moc: list, tran: int = TRAN_KY_TU_CUM,
                     ) -> list:
    """Cắt `text` thành CỤM <= `tran` ký tự, mốc lấy từ WordBoundary. THUẦN.

    Trả `[(giây_bắt_đầu, giây_hết_TỪ CUỐI của cụm, chữ)]` — mốc còn THÔ (chưa
    nối liền cụm), `dong_chu_theo_giong` mới là chỗ chốt khung hiển thị.

    `moc` rỗng / không khớp được từ nào -> trả `[]`, caller tự lùi về cách
    chia theo TỈ LỆ KÝ TỰ (vẫn cắt ngắn được, chỉ kém chính xác hơn).

    **CẮT Ở DẤU NGẮT KHI CÓ THỂ:** đủ 60% ngân sách mà gặp dấu phẩy/chấm thì
    cắt luôn — cụm trùng với mệnh đề thì đọc lướt một cái là hiểu, còn cắt
    giữa mệnh đề thì mắt phải chờ cụm sau.
    """
    text = str(text or "")
    tu = _khop_tu_vao_chu(text, moc)
    if not tu:
        return []
    cum: list[list] = []          # [char_dau, char_cuoi, a, b]
    for c0, c1, a, b in tu:
        if not cum:
            cum.append([c0, c1, a, b])
            continue
        cuoi = cum[-1]
        dai = c1 - cuoi[0]
        # ký tự ngay sau từ vừa xong (bỏ qua khoảng trắng) là dấu ngắt?
        sau = text[cuoi[1]:c0].strip()
        ngat = bool(sau) and sau[-1] in _DAU_NGAT
        if dai > tran or (ngat and (cuoi[1] - cuoi[0]) >= tran * 0.6):
            cum.append([c0, c1, a, b])
        else:
            cuoi[1], cuoi[3] = c1, b
    ra: list = []
    for k, (c0, c1, a, b) in enumerate(cum):
        # LẤY CẢ PHẦN GIỮA HAI CỤM (dấu câu, khoảng trắng) vào cụm TRƯỚC —
        # không thì dấu phẩy/chấm biến mất khỏi chữ hiện lên.
        het = cum[k + 1][0] if k + 1 < len(cum) else len(text)
        # cụm ĐẦU lấy luôn phần mở đầu bị edge-tts bỏ (dấu ngoặc kép...)
        bd = 0 if k == 0 else c0
        s = text[bd:het].strip()
        if s:
            ra.append((round(a, 3), round(b, 3), s))
    return ra


def chia_cum_theo_ty_le(text: str, a: float, b: float,
                        tran: int = TRAN_KY_TU_CUM) -> list:
    """ĐƯỜNG LÙI khi không có mốc từ: cắt theo ký tự, chia đều theo TỈ LỆ.

    Kém chính xác hơn WordBoundary (giả định đọc đều), nhưng vẫn giải đúng
    việc anh Hùng kêu — không đổ cả khối 3 dòng ra một lúc. Hàm THUẦN.
    """
    from app.core import dubbing

    text = str(text or "").strip()
    if not text:
        return []
    tu = dubbing._tach_tu(text) or [text]
    cum: list[str] = []
    for w in tu:
        if cum and len(cum[-1]) + 1 + len(w) <= tran:
            cum[-1] = dubbing._noi_tu([cum[-1], w])
        else:
            cum.append(w)
    tong_kt = sum(len(c) for c in cum) or 1
    ra: list = []
    t = float(a)
    dai = max(0.05, float(b) - float(a))
    for c in cum:
        d = dai * len(c) / tong_kt
        ra.append((round(t, 3), round(t + d, 3), c))
        t += d
    return ra


def dong_chu_theo_giong(moc_tieng: list, texts: list,
                        moc_tu: Optional[list] = None,
                        tran: int = TRAN_KY_TU_CUM) -> list:
    """[(bắt_đầu, kết_thúc, chữ)] cho `che_chu.ghi_ass` — CHỮ CHẠY THEO LỜI.

    `moc_tieng` = `khop_thoi_gian()["moc_tieng"]` = [(i, giây_nói, giây_hết)]
    ĐO bằng `silencedetect` trên chính file wav đã khớp. `texts` = lời CUỐI
    CÙNG app đọc lên (`rut_gon_vua_khung()["texts"]`).
    `moc_tu` = `khop_thoi_gian()["moc_tu"]` = [(i, [[a, b, từ], ...])] đã ở
    TIMELINE ĐẦU RA.

    **VÌ SAO ĐỔI (anh Hùng 15/08):** *"nó che nhưng mà không khớp, kiểu nói
    đến đâu chữ hiện đến đó chứ không hiện hàng loạt ra chữ như thế kia"*.
    Bản cũ trả ĐÚNG MỘT dòng cho cả câu -> khung câu 9,6 giây thì 131 ký tự
    (3 dòng) đứng im 9,6 giây. Nay mỗi câu bị cắt thành nhiều CỤM <= `tran`
    ký tự, mốc lấy từ WordBoundary của chính giọng vừa đọc.

    **KHÔNG DÙNG THẺ KARAOKE `\\k`** — đã cân nhắc và LOẠI, lý do đo được ghi
    ở `_do_cum_chu.py`: `\\k` vẫn để NGUYÊN cả khối 3 dòng trên màn hình (chỉ
    đổi màu dần), tức KHÔNG giải được đúng câu anh Hùng kêu; và libass phải
    có style 2 màu, nền/trình phát nào nuốt thẻ là ra một khối chữ đứng im —
    hỏng ÂM THẦM. Cụm nối tiếp thì mọi trình phát đều hiểu.

    Hàm THUẦN, không đụng đĩa — để cổng thử phá gọi thẳng được: đưa mốc GỐC
    (`cau[i]["start"]`) vào đây là bảng lệch phải ĐỎ.
    """
    bang_tu = {int(i): ds for i, ds in (moc_tu or ())}
    ra: list = []
    n = len(moc_tieng)
    for k, (i, a, b) in enumerate(moc_tieng):
        t = str(texts[i]).strip() if 0 <= i < len(texts) else ""
        if not t:
            continue
        a, b = float(a), float(b)
        # TRẦN CỨNG của câu này: không bao giờ lấn sang mốc nói của câu kế.
        tran_cuoi = (float(moc_tieng[k + 1][1]) - CHU_CHUA_TRUOC_S
                     if k + 1 < n else None)
        het_cau = max(b, a + CHU_TOI_THIEU_S)
        if tran_cuoi is not None:
            het_cau = min(het_cau, tran_cuoi)
        if het_cau <= a:
            het_cau = a + 0.20

        cum = chia_cum_theo_tu(t, bang_tu.get(int(i)) or [], tran)
        if not cum:
            cum = chia_cum_theo_ty_le(t, a, b, tran)
        if not cum:
            continue
        # GỘP cụm quá ngắn vào cụm sau — chữ chớp 0,2 giây khó đọc hơn cả câu
        # dài, mà GIÃN thì lấn sang cụm sau (2 dòng chữ cùng lúc).
        gop: list[list] = []
        for ca, cb, cs in cum:
            if gop and (ca - gop[-1][0]) < CUM_TOI_THIEU_S:
                gop[-1][1] = cb
                gop[-1][2] = f"{gop[-1][2]} {cs}".strip()
            else:
                gop.append([ca, cb, cs])
        # CỤM CUỐI CÂU bị câu KẾ bóp ngắn thì gộp NGƯỢC vào cụm trước. Vòng
        # gộp ở trên chỉ nhìn khoảng cách giữa hai cụm, không biết cụm cuối
        # sắp bị `tran_cuoi` cắt — đo ra 4-10 cụm chớp dưới 0,4 s đúng từ chỗ
        # này, và chúng nằm ở CUỐI câu nên là chỗ mắt vừa kịp nhìn tới.
        while len(gop) > 1 and (het_cau - gop[-1][0]) < CUM_TOI_THIEU_S:
            cuoi_bo = gop.pop()
            gop[-1][1] = cuoi_bo[1]
            gop[-1][2] = f"{gop[-1][2]} {cuoi_bo[2]}".strip()
        # KHUNG HIỂN THỊ: cụm này hiện tới lúc cụm SAU bắt đầu (không hở,
        # không chồng). Cụm cuối chạy tới hết tiếng của câu.
        for j, (ca, _cb, cs) in enumerate(gop):
            ket = gop[j + 1][0] if j + 1 < len(gop) else het_cau
            if tran_cuoi is not None:
                ket = min(ket, tran_cuoi)
            ca = max(a, min(ca, het_cau))
            if ket <= ca:
                continue
            ra.append((round(ca, 3), round(ket, 3), cs))
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
                     kieu_chu: Optional[dict] = None,
                     hinh_theo_giong: bool = False,
                     bu_giong_goc_bat: bool = True,
                     de_giong: bool = False,
                     on_progress: Optional[Callable[[float, str], None]] = None,
                     ) -> dict:
    """CHẠY ĐỦ 6 BƯỚC cho 1 video, trả file video MỚI (chưa đụng file gốc).

    `de_giong=True` -> **ĐÈ GIỌNG, KHÔNG TÁCH** (anh Hùng đề xuất 19/08/2026:
    *"thêm tính năng KHÔNG tách nhạc nền, chỉ GIẢM tiếng video gốc rồi ĐÈ giọng
    lồng tiếng vào, để không bị mất mấy tiếng của video"*). Ba thứ đổi, và chỉ
    ba thứ đó:
      1. **BỎ bước tách** (`tach_giong`) — không cần Demucs/torch/GPU.
      2. **Lớp nền = CHÍNH audio gốc** thay cho lớp nhạc đã tách. `chep_loi`
         chép trên audio gốc (nó tự lùi khi không có lớp giọng, ghi rõ
         `_nguon="audio_goc"` — không im lặng coi như cùng chất lượng).
      3. **BỎ bước bù giọng gốc** — `bu_giong_goc` tồn tại để lấp chỗ giọng gốc
         *đã bị bỏ*; ở đây nó chưa bao giờ bị bỏ nên bù là **CỘNG GIỌNG GỐC
         HAI LẦN** (một lần trong nền, một lần trong mảnh bù) = vang đôi.
    Mọi bước còn lại (chép lời · dịch · đọc · rút gọn · khớp · trộn · ducking ·
    chuẩn hoá độ to · che chữ · viết chữ mới) đi Y NGUYÊN đường cũ.

    `bu_giong_goc_bat=True` (mặc định BẬT): đoạn nào KHÔNG được đọc lại thì giữ
    lại GIỌNG GỐC thay vì để trống. Xem `khoang_khong_giong` — đây là bản chữa
    lỗi anh Hùng báo 18/08/2026 (*"đoạn nói tiếng Anh nó không đọc thì bị tắt
    tiếng"*), và mặc định BẬT vì để trống là MẤT NỘI DUNG.

    `hinh_theo_giong=True` -> **CHỈNH VIDEO THEO GIỌNG** thay vì ép giọng vừa
    khung câu gốc. Anh Hùng 18/08/2026: *"giọng cứ lúc nhanh lúc chậm không
    đều — đáng nhẽ chỉ chỉnh video sao cho khớp giọng nói chứ"*. Xem
    `he_so_hinh_can` (cách tính hệ số) và `SAN_NHIP_HINH_FPS` (trần + giá).

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

    de_giong = bool(de_giong)
    kq: dict = {"vao": str(video_in), "thu_muc_lam": str(tam_goc),
                "cach_tron": "de" if de_giong else "tach"}
    t0 = time.time()
    try:
        # --- bước 0: rút audio
        prog(0.02, "Rút tiếng khỏi video...")
        goc_wav = tam_goc / "goc.wav"
        tong = tach_wav(video_in, goc_wav)
        kq["do_dai"] = round(tong, 3)

        # --- bước 1: tách giọng / nhạc
        # CHẾ ĐỘ ĐÈ GIỌNG BỎ HẲN BƯỚC NÀY. Không phải "tối ưu cho nhanh" mà là
        # điều kiện của chính tính năng: giữ nguyên tiếng gốc thì không có gì
        # phải tách ra để bỏ đi. Nhờ vậy nó KHÔNG cần torch/Demucs/GPU và mất
        # tiếng về 0 THEO CẤU TẠO (Demucs mới là chỗ sinh ra khoảng trống).
        t: dict = {"nhac": str(goc_wav), "giong": "", "cach": "de_giong",
                   "ghi_chu": "KHÔNG tách — giữ nguyên tiếng gốc làm lớp nền"}
        if not de_giong:
            prog(0.06, "Tách giọng khỏi nhạc nền...")
            t = tach_giong(goc_wav, tam_goc / "tach", cach=cach_tach,
                           on_progress=lambda p, m: prog(0.06 + 0.24 * p, m))
        kq["tach"] = {k: v for k, v in t.items() if k != "stems"}

        # --- bước 2: chép lời
        prog(0.32, "Chép lời gốc...")
        # `t["giong"]` RỖNG ở chế độ đè giọng -> `chep_loi` tự chép trên audio
        # GỐC và đóng dấu `_nguon="audio_goc"`. Nói thẳng cái giá: nền nhạc còn
        # nguyên nên whisper dễ nhầm hơn so với chép trên lớp giọng đã tách.
        d = chep_loi(goc_wav, t.get("giong") or "",
                     on_progress=lambda p, m: prog(0.32 + 0.10 * p, m))
        cau = cau_tu_transcript(d)
        kq["chep"] = {"ngon_ngu": d.get("language"),
                      "so_tu": len(d.get("words") or []),
                      "so_cau": len(cau),
                      "nguon": d.get("_nguon"),
                      "giay": d.get("_giay_chep")}
        # MỐC người GỐC nói từng câu. Đi cặp với `loi_cuoi` (cùng số phần tử,
        # cùng thứ tự) để đối chiếu được "câu này ĐÁNG LẼ nói lúc mấy giây" với
        # "trong file thành phẩm nó nói lúc mấy giây". Thiếu mốc thì phép đo
        # lệch phải mượn bản chép lời của lượt KHÁC — số ra sai mà trông vẫn
        # hợp lý (đã suýt báo nhầm 3,2 giây lệch vì đúng chuyện này).
        kq["cau_moc"] = [(round(float(c["start"]), 3),
                          round(float(c["end"]), 3)) for c in cau]
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
                                 moc_tu=rg.get("moc_tu"),
                                 on_progress=lambda p, m: prog(0.79 + 0.01 * p, m))
        kq["doc_nhanh"] = {k: v for k, v in dn.items()
                           if k not in ("files", "ok", "can_truoc", "can_sau")}

        # --- bước 5: khớp thời gian
        prog(0.80, "Khớp thời gian...")
        # --- HỆ SỐ LÀM CHẬM HÌNH (chế độ "Chỉnh video theo giọng") ---
        # Tính TRƯỚC khi khớp, vì `khop_thoi_gian` cần nó để đặt mốc. Trần lấy
        # theo fps THẬT của nguồn (nguồn 23,976 fps chừa rất ít chỗ).
        hs = 1.0
        kq["hinh"] = {"bat": bool(hinh_theo_giong)}
        if hinh_theo_giong:
            _c = he_so_hinh_can(cau, dn["files"], dn["ok"], tong)
            _fps = do_fps(video_in)
            _tran = tran_hinh_theo_fps(_fps)
            hs = max(1.0, min(float(_c["k_can"]), _tran))
            kq["hinh"].update({
                **_c, "fps_nguon": round(_fps, 3),
                "tran_theo_fps": round(_tran, 4),
                "k_dung": round(hs, 4),
                "cham_tran": float(_c["k_can"]) > _tran + 1e-6,
                "nhip_hinh_con_lai_fps": round(_fps / hs, 2) if hs > 0 else 0,
            })
        kh = khop_thoi_gian(cau, dn["files"], dn["ok"], tong,
                            tam_goc / "khop", moc_tu=dn.get("moc_tu"),
                            he_so_hinh=hs,
                            on_progress=lambda p, m: prog(0.80 + 0.10 * p, m))
        kq["khop"] = {k: v for k, v in kh.items() if k != "manh"}
        if not kh["manh"]:
            raise RuntimeError("Không câu nào khớp được thời gian")
        # ĐỘ DÀI ĐẦU RA đổi theo hệ số hình — mọi bước sau (trộn · ghép · kiểm)
        # phải dùng con số MỚI này, dùng `tong` cũ là lệch hẳn `(k-1)*tong`.
        tong_ra = tong * hs

        # --- LỚP NỀN PHẢI GIÃN THEO HÌNH ---
        # Làm chậm hình mà để nhạc/tiếng động chạy tốc độ cũ thì nhạc HẾT SỚM
        # và mọi cú va không còn rơi đúng khung hình của nó — tức đổi một lỗi
        # đồng bộ lấy một lỗi đồng bộ khác. Giãn bằng `rubberband` (đo được méo
        # 0,061 dB so với `atempo` 5,982 dB) và ĐO LẠI độ dài trên file đã ghi.
        # ĐỌC `t["nhac"]` CHỨ KHÔNG `goc_wav`: ở chế độ đè giọng hai cái là MỘT
        # (xem chỗ dựng `t` ở bước 1), nên một dòng này phục vụ cả hai cách và
        # không có đường nào bị bỏ sót phép giãn.
        nhac_dung = t["nhac"]
        if hs > 1.0 + 1e-6:
            prog(0.90, "Giãn nhạc nền cho khớp hình...")
            _nh = tam_goc / "nhac_gian.wav"
            _ffmpeg(["-i", str(t["nhac"]), "-af",
                     f"{_co_gian_chuoi(1.0 / hs)},aresample={SR_TACH},"
                     f"apad,atrim=0:{tong_ra:.3f},asetpts=N/SR/TB",
                     "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
                     str(_nh)], "giãn lớp nhạc theo hệ số hình")
            _kiem_wav(_nh, cho_phep_im=True)
            _dn = probe_duration(_nh)
            if abs(_dn - tong_ra) > 0.05:
                raise RuntimeError(
                    f"Lớp nhạc giãn ra {_dn:.3f}s, phải là {tong_ra:.3f}s")
            nhac_dung = str(_nh)
            kq["hinh"]["nhac_gian_giay"] = round(_dn, 3)

        # --- BÙ GIỌNG GỐC Ở ĐOẠN KHÔNG ĐƯỢC ĐỌC LẠI ---
        # Anh Hùng 18/08/2026: *"mấy cái đoạn âm thanh gốc nói tiếng Anh nó
        # không đọc phần đó thì lại bị TẮT TIẾNG"* · *"cái nghe được cái
        # không"*. Đoạn nào không có giọng MỚI thì giọng GỐC đã bị bỏ -> chỉ còn
        # nhạc -> MẤT NỘI DUNG (nặng hơn chuyện âm lượng). Đo trên 4 bản anh
        # Hùng đã xuất: mất 82,3s/1.209,3s = 6,8%, dồn vào 2/4 video (31,1s và
        # 50,4s) — xem `khoang_khong_giong`.
        #
        # Mảnh bù CỘNG THẲNG vào danh sách mảnh giọng trước khi trộn, nên nó
        # được tính vào CẢ cân bằng giọng-nhạc, CẢ ducking, CẢ chuẩn hoá độ to.
        #
        # **CHẾ ĐỘ ĐÈ GIỌNG KHÔNG ĐƯỢC BÙ** — và đây là chỗ dễ sai nhất của cả
        # bản vá: hai tính năng nghe như cùng hướng ("giữ tiếng gốc") nhưng cộng
        # lại là SAI. Ở chế độ đè, giọng gốc nằm SẴN trong lớp nền; bù thêm mảnh
        # giọng gốc nữa là cộng CÙNG MỘT tín hiệu hai lần -> vang đôi/dội, và
        # tệ hơn là mảnh bù đó còn bị tính vào cân bằng giọng-nhạc rồi kéo lệch
        # cả phép đo. Chốt bằng `and not de_giong`, KHÔNG bắt người gọi tự nhớ.
        manh_tron = list(kh["manh"])
        if de_giong:
            kq["bu_goc"] = {
                "bat": False,
                "vi_sao": "chế độ đè giọng — tiếng gốc còn NGUYÊN trong lớp "
                          "nền, bù thêm là cộng giọng gốc hai lần"}
        elif bu_giong_goc_bat:
            # LỜI NHẮN NÀY CỐ Ý KHÔNG CHỨA CHỮ "ĐỌC" (hay "dịch"/"rút gọn"/
            # "khớp thời gian"…). `tg_so.buoc_tu_tien_trinh` tra bước bằng CHUỖI
            # CON, và khoá `("đọc", 5)` sẽ khớp *"không được đọc lại"* -> bảng
            # tiến độ tụt từ 8/9 về 5/9 = **THANH TIẾN ĐỘ CHẠY NGƯỢC**, đúng cái
            # anh Hùng từng kêu "chạy lùi/treo" (xem chú thích ở `TEN_BUOC` và
            # khối `khoa`). Không khớp khoá nào thì nó suy theo KHOẢNG tiến
            # trình: 0,905 < 0,91 -> bước 8, đúng và không lùi.
            prog(0.905, "Bù giọng gốc cho đoạn bị bỏ trống...")
            try:
                bu = bu_giong_goc(t.get("giong") or "", kh["manh"], tong_ra,
                                  tam_goc / "bu_goc", he_so_hinh=hs)
                manh_tron += bu["manh"]
                kq["bu_goc"] = {x: y for x, y in bu.items() if x != "manh"}
            except Exception as e:                          # noqa: BLE001
                # Bù được thì tốt, KHÔNG bù được thì vẫn ra video (chỉ thiếu
                # tiếng ở mấy đoạn đó, y như bản trước) — đừng để bước phụ này
                # giết cả lượt xuất.
                kq["bu_goc"] = {"ok": False,
                                "loi": f"{type(e).__name__}: {e}"[:200]}
        else:
            kq["bu_goc"] = {"bat": False}

        # --- bước 6: trộn + thay vào video
        # LỜI NHẮN CỦA CẢ HAI CÁCH PHẢI CHỨA ĐÚNG CỤM **"Trộn tiếng"**.
        # `tg_so.buoc_tu_tien_trinh` tra bước bằng CHUỖI CON với khoá
        # `("trộn tiếng", 9)`; không khớp khoá nào thì nó lùi về suy theo KHOẢNG
        # tiến trình. Bản đầu của dòng này viết *"Trộn giọng lồng lên tiếng
        # gốc…"* — KHÔNG chứa "trộn tiếng" nên nó rơi vào đường LÙI, và chỉ ra
        # đúng bước 9 NHỜ MAY (0,91 lọt khoảng cuối). Đo được bằng cách gọi với
        # `p=0.0`: câu đó ra **bước 1** còn câu có "trộn tiếng" ra **bước 9** —
        # tức ai đổi mốc `prog` sau này là thanh tiến độ chạy ngược ÂM THẦM.
        # Và KHÔNG được chứa cụm "tách giọng" (khoá bước 2) — "không tách nhạc"
        # thì an toàn, "không tách giọng" thì thanh tiến độ tụt về bước 2.
        prog(0.91, "Trộn tiếng mới ĐÈ lên tiếng gốc (không tách nhạc)..."
             if de_giong else "Trộn tiếng mới với nhạc nền gốc...")
        # `goc_wav` truyền vào để bước BÙ DẢI CAO lấy được cân bằng dải tần
        # của CHÍNH video này làm đích (xem `BU_SANG_TOI_DA_DB`). Thiếu nó thì
        # bước bù tự tắt — nên đây là chỗ DUY NHẤT phải nhớ nối.
        au = tron_thay_giong(nhac_dung, manh_tron, tong_ra,
                             tam_goc / "tieng_moi.wav", goc_wav=goc_wav)
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
        dong_chu = dong_chu_theo_giong(
            kh.get("moc_tieng") or [], rg["texts"],
            moc_tu=kh.get("moc_tu")) if viet_chu else []
        kq["chu_theo_giong"] = {
            "bat": bool(viet_chu), "so_dong": len(dong_chu),
            "so_cau": len(kh.get("moc_tieng") or []),
            "so_cau_co_moc_tu": kh.get("so_cau_co_moc_tu", 0),
            "tran_ky_tu": TRAN_KY_TU_CUM,
            "ky_tu_tb": round(sum(len(d[2]) for d in dong_chu)
                              / max(1, len(dong_chu)), 1),
            "ky_tu_max": max([len(d[2]) for d in dong_chu] or [0])}
        thay_audio_video(video_in, au["ra"], ra, che_chu=che_chu,
                         che_chu_cach=che_chu_cach, che_chu_muc=che_chu_muc,
                         che_chu_log=_cc_log, dong_chu=dong_chu,
                         kieu_chu=kieu_chu, he_so_hinh=hs)
        kq["che_chu"] = _cc_log[0] if _cc_log else {"bat": False}
        # KIỂM theo `tong_ra` (độ dài ĐÍCH), KHÔNG theo `tong`: chế độ chỉnh
        # hình làm video dài ra `(k-1)*tong` một cách CỐ Ý. Dùng `tong` ở đây
        # là `kiem_video_ra` ném đúng lúc mọi thứ đang đúng.
        kq["kiem"] = kiem_video_ra(ra, tong_ra)
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


def chot_co_bo_tach_giong(cach_tach: str = "auto",
                          de_giong: bool = False) -> None:
    """CHẶN TRƯỚC: máy chưa có bộ tách giọng thì ném NGAY, đừng chạy dở.

    Vì sao phải chặn ở đây nữa dù `tach_giong` đã ném: không có chốt này thì
    mỗi video vẫn rút audio xong (chục giây/video) rồi mới chết ở bước 1 — 20
    video là 20 lần vô ích, và nhật ký đầy lỗi giống nhau.

    `de_giong=True` -> **KHÔNG CHẶN**: chế độ đè giọng không đi qua `tach_giong`
    một lần nào (xem `thay_giong_video`), nên đòi Demucs ở đây là chặn oan đúng
    cái đường được làm ra để chạy trên máy KHÔNG có Demucs. Đây là chốt duy
    nhất trong file phải biết tới `de_giong` — mọi chốt khác nằm trong
    `thay_giong_video`.
    """
    if de_giong:
        return
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
                         che_chu_muc: float = 1.0, viet_chu: bool = True,
                         kieu_chu: Optional[dict] = None,
                         hinh_theo_giong: bool = False,
                         bu_giong_goc_bat: bool = True,
                         de_giong: bool = False,
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
                         che_chu_muc=che_chu_muc, viet_chu=viet_chu,
                         kieu_chu=kieu_chu,
                         # HAI CỜ NÀY PHẢI CHUYỀN QUA — thiếu là job handler
                         # (`jobs._thay_giong` gọi CỬA NÀY, không gọi thẳng
                         # `thay_giong_video`) nổ `unexpected keyword argument`
                         # và **MỌI job thay giọng đều LỖI**. Cổng 55 bắt được
                         # đúng thế: 2/2 job `failed`.
                         hinh_theo_giong=hinh_theo_giong,
                         bu_giong_goc_bat=bu_giong_goc_bat,
                         # CỜ THỨ BA CŨNG PHẢI CHUYỀN QUA — cùng lý do hai cờ
                         # trên: `jobs._thay_giong` gọi CỬA NÀY chứ không gọi
                         # thẳng `thay_giong_video`, thiếu một cờ là job nổ
                         # `unexpected keyword argument` và MỌI job đều LỖI.
                         de_giong=de_giong,
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
                       de_giong: bool = False,
                       on_video: Optional[Callable[[str, dict], None]] = None,
                       ) -> dict:
    """Thay giọng CẢ THƯ MỤC video, chạy ĐA LUỒNG, xong thì thay video gốc.

    `thay_goc=False` -> chỉ tạo file mới bên cạnh, KHÔNG đụng gốc (dùng để thử).
    `de_giong=True` -> chế độ ĐÈ GIỌNG (xem `thay_giong_video`).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    thu_muc = Path(thu_muc)
    # CHẶN TRƯỚC khi đụng video nào: thiếu bộ tách giọng thì ném NGAY. Chế độ
    # đè giọng không dùng bộ tách nên chốt tự cho qua (xem hàm đó).
    chot_co_bo_tach_giong(cach_tach, de_giong=de_giong)
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
            de_giong=de_giong,
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
