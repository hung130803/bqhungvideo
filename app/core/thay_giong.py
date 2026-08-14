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
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from typing import Callable, Optional

from config import settings

_CREATE_NO_WINDOW = 0x0800_0000 if os.name == "nt" else 0

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

def _ffmpeg(args: list[str], what: str, timeout: int = 900) -> None:
    """Chạy ffmpeg. In mã thoát THẬT khi lỗi (không nối `| tail` để khỏi mất mã)."""
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
           *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_CREATE_NO_WINDOW,
                       timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lỗi khi {what} (mã thoát {r.returncode}): "
            f"{(r.stderr or '')[-500:]}")


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
    """Đỉnh (dBFS) + số mẫu chạm trần, đọc bằng `astats` (dùng `in`)."""
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-i", str(path),
           "-map", "0:a:0", "-af", "astats=measure_overall=Peak_level+"
           "Number_of_clipped_samples:measure_perchannel=none",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return {"dinh": None, "cham_tran": None}
    dinh, cham = None, None
    for line in (r.stderr or "").splitlines():
        if "Peak level dB:" in line:
            raw = line.split(":")[-1].strip()
            if raw.lower().lstrip("-") not in ("inf", "nan"):
                try:
                    dinh = float(raw)
                except ValueError:
                    pass
        if "Number of clipped samples:" in line:
            try:
                cham = int(float(line.split(":")[-1].strip()))
            except ValueError:
                pass
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
    mặc định `<repo>/_lib`.
    """
    p = (os.environ.get("BQ_DEMUCS_LIB") or "").strip()
    return p or str(Path(__file__).resolve().parents[2] / "_lib")


def co_demucs() -> bool:
    """Demucs + torch có nạp được không (KHÔNG tải model, chỉ thử import).

    Máy nhân viên KHÔNG cài torch -> hàm trả False -> tự lui `tach_nhe`.
    """
    lib = lib_demucs()
    if lib and lib not in sys.path and Path(lib).is_dir():
        sys.path.insert(0, lib)
    try:
        import torch  # noqa: F401
        import demucs.apply  # noqa: F401
        import demucs.pretrained  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def thiet_bi_tach() -> str:
    """'cuda' nếu torch build CÓ CUDA và thấy GPU, ngược lại 'cpu'.

    ĐÃ ĐO: `.venv` app cài torch **2.13.0+cpu** nên trả 'cpu' KỂ CẢ khi máy có
    RTX 3060. Đây là con số quyết định tốc độ — xem báo cáo.
    """
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


def _tach_demucs(wav_44k: str | Path, out_dir: Path, model_name: str,
                 threads: int,
                 on_progress: Optional[Callable[[float, str], None]],
                 ) -> dict:
    """Tách bằng Demucs (`htdemucs`, Meta, MIT). Ném RuntimeError nếu thiếu lib."""
    lib = lib_demucs()
    if lib and lib not in sys.path and Path(lib).is_dir():
        sys.path.insert(0, lib)
    os.environ.setdefault("TORCH_HOME", str(Path(lib) / "_models"))
    try:
        import soundfile as sf
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Chưa cài được Demucs (thư mục {lib}): {e}") from e

    def prog(p: float, m: str) -> None:
        if on_progress:
            on_progress(max(0.0, min(1.0, p)), m)

    if threads > 0:
        torch.set_num_threads(int(threads))

    prog(0.02, "Nạp model tách giọng...")
    model = get_model(model_name)
    model.eval()

    data, sr = sf.read(str(wav_44k), dtype="float32", always_2d=True)
    if sr != model.samplerate:
        raise RuntimeError(
            f"Audio phải ở {model.samplerate} Hz (đang {sr} Hz) — resample "
            "bằng ffmpeg trước khi gọi (dùng tach_wav).")
    wav = torch.from_numpy(data.T).contiguous()
    if wav.shape[0] == 1:                       # mono -> nhân đôi kênh
        wav = wav.repeat(2, 1)
    dur = wav.shape[1] / float(sr)

    # Chuẩn hoá theo trung bình/độ lệch như bản gốc Demucs rồi trả lại sau.
    ref = wav.mean(0)
    std = float(ref.std()) or 1.0
    mean = float(ref.mean())
    w = (wav - mean) / std

    dev = thiet_bi_tach()
    prog(0.10, f"Đang tách nhạc/giọng ({dur:.0f} giây, {dev})...")
    t0 = time.time()
    with torch.no_grad():
        src = apply_model(model, w[None], device=dev, progress=False,
                          split=True, overlap=0.25)[0]
    giay = time.time() - t0
    src = src * std + mean

    stems: dict[str, str] = {}
    for i, name in enumerate(model.sources):
        p = out_dir / f"stem_{name}.wav"
        sf.write(str(p), src[i].numpy().T, sr)
        stems[name] = str(p)

    # Lớp GIỮ = cộng drums+bass+other ở MIỀN MẪU (không qua `amix` để tránh bẫy
    # chia biên độ, và giữ đúng từng mẫu).
    idx = {n: i for i, n in enumerate(model.sources)}
    keep = sum(src[idx[n]] for n in LOP_GIU if n in idx)
    p_nhac = out_dir / "lop_nhac.wav"
    sf.write(str(p_nhac), keep.numpy().T, sr)

    _kiem_wav(p_nhac)
    prog(1.0, "Xong tách nhạc/giọng")
    return {
        "cach": f"demucs:{model_name}",
        "nhac": str(p_nhac),
        "giong": stems.get(LOP_BO, ""),
        "stems": stems,
        "giay": round(giay, 2),
        "ty_le": round(giay / dur, 3) if dur > 0 else 0.0,
        "thiet_bi": dev,
        "do_dai": round(dur, 3),
        "sr": sr,
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


def tach_giong(wav_44k: str | Path, out_dir: str | Path,
               cach: str = "auto", model_name: str = "htdemucs",
               threads: int = 0,
               on_progress: Optional[Callable[[float, str], None]] = None,
               ) -> dict:
    """Tách `wav_44k` (stereo 44,1 kHz) thành lớp NHẠC (giữ) + lớp GIỌNG (bỏ).

    `cach`: "demucs" (ép Demucs, thiếu lib -> lỗi) | "nhe" (ép ffmpeg) |
            "auto" (có Demucs thì Demucs, KHÔNG có thì tự lui `nhe`).

    Trả dict: nhac / giong / stems / giay / ty_le / thiet_bi / do_dai / sr / cach
    (`giong` = "" nghĩa là cách này KHÔNG cho lớp giọng sạch).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cach = (cach or "auto").lower().strip()

    if cach == "nhe":
        return _tach_nhe(wav_44k, out_dir, on_progress)
    if cach == "demucs":
        return _tach_demucs(wav_44k, out_dir, model_name, threads, on_progress)

    # auto
    if co_demucs():
        try:
            return _tach_demucs(wav_44k, out_dir, model_name, threads,
                                on_progress)
        except Exception as e:  # noqa: BLE001
            # Demucs hỏng giữa đường (model tải lỗi, hết RAM...) -> vẫn còn
            # đường lui, nhưng GHI RÕ lý do vào kết quả để không im lặng tụt
            # chất lượng.
            ket = _tach_nhe(wav_44k, out_dir, on_progress)
            ket["lui_vi"] = str(e)[:300]
            return ket
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
