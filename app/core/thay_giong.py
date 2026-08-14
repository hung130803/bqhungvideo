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
            cum.append(w)
            dai = float(cum[-1]["end"]) - float(cum[0]["start"])
            if dai >= gop_toi_da:
                out.append({
                    "start": round(float(cum[0]["start"]), 3),
                    "end": round(float(cum[-1]["end"]), 3),
                    "text": "".join(str(x.get("word", "")) for x in cum).strip(),
                })
                cum = []
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
}


def _ten_nn(ma: str) -> str:
    return _TEN_NN.get((ma or "").lower()[:2], ma or "tiếng Anh")


def _dich_loat(cau: list[dict], dich_sang: str, goc_ma: str) -> list[str]:
    """Dịch cả loạt câu trong 1 lượt LLM. Trả list cùng số phần tử."""
    from app.ai import llm

    ten_dich = _ten_nn(dich_sang)
    items = []
    for i, c in enumerate(cau):
        dur = max(0.1, float(c["end"]) - float(c["start"]))
        items.append(f'#{i} [{dur:.1f} giây]: "{c["text"][:400]}"')
    system = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. Dịch tự nhiên như "
              "VĂN NÓI, đúng ý, đúng cảm xúc. CHỈ trả JSON thuần.")
    prompt = (
        f"Dịch các câu thoại sau từ {_ten_nn(goc_ma)} sang {ten_dich}.\n"
        f"{chr(10).join(items)}\n\n"
        "QUY TẮC:\n"
        f"- Dịch sang {ten_dich}, văn NÓI tự nhiên.\n"
        "- ĐỌC LÊN phải lọt khung [số giây] của câu đó — dài quá thì lược từ "
        "đệm, GIỮ Ý CHÍNH.\n"
        "- KHÔNG thêm chú thích, không phiên âm.\n"
        f"- Trả MẢNG JSON đúng {len(cau)} chuỗi, cùng thứ tự."
    )
    data = llm.complete_json(prompt, system=system)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list):
        raise llm.LLMError("LLM không trả mảng bản dịch.")
    out = []
    for i, c in enumerate(cau):
        t = data[i] if i < len(data) else None
        out.append(str(t).strip() if isinstance(t, str) and str(t).strip()
                   else c["text"])
    return out


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
        f"Trả MẢNG JSON đúng {len(goc)} SỐ, cùng thứ tự: [10, 7, ...]"
    )
    try:
        data = llm.complete_json(prompt, system=system)
    except Exception:  # noqa: BLE001
        return [10.0] * len(goc)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list):
        return [10.0] * len(goc)
    out = []
    for i in range(len(goc)):
        try:
            out.append(float(data[i]))
        except (IndexError, TypeError, ValueError):
            out.append(10.0)
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
    return {
        "files": paths, "ok": list(ok), "voice": voice,
        "giay": round(time.time() - t0, 2),
        "so_hong": sum(1 for x in ok if not x),
    }


# ==================================================================
# BƯỚC 5 — KHỚP THỜI GIAN (co giãn + MƯỢN thời gian đoạn kế)
# ==================================================================

#: Trên mức này nghe đã MÉO -> phải mượn thời gian đoạn kế thay vì ép nhanh.
TEMPO_CANH_BAO = 1.30

#: Trần tuyệt đối: mượn hết rồi vẫn tràn thì đành ép tới đây.
TEMPO_TOI_DA = 1.50

#: Chừa lại chút im lặng trước câu kế khi mượn (giây) — mượn sát quá thì hai
#: câu dính liền, nghe như nói hụt hơi.
CHUA_TRUOC_CAU_KE = 0.12


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

    Trả {manh, lech_dau_ms, lech_cuoi_ms, tempo_max, so_cau_ep, so_cau_muon}.
    `manh` = [(mốc_giây, đường_dẫn_wav)] để bước 6 trộn.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manh: list[tuple[float, str]] = []
    lech_dau: list[float] = []
    lech_cuoi: list[float] = []
    temps: list[float] = []
    so_ep = so_muon = 0
    bo_qua = 0

    for i, c in enumerate(cau):
        if i >= len(files) or not ok[i] or not Path(files[i]).exists():
            bo_qua += 1
            continue
        a = float(c["start"])
        b = float(c["end"])
        khung = max(0.05, b - a)

        # khoảng lặng tới câu kế (có thể MƯỢN)
        ke = float(cau[i + 1]["start"]) if i + 1 < len(cau) else tong
        cho_phep = max(khung, ke - a - CHUA_TRUOC_CAU_KE)

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
        af = ["aresample=44100"]
        if abs(tempo - 1.0) > 1e-3:
            af.append(_atempo_chuoi(tempo))
        _ffmpeg(["-i", files[i], "-af", ",".join(af), "-ac", "2",
                 "-ar", str(SR_TACH), "-c:a", "pcm_s16le", str(dst)],
                f"khớp thời gian câu #{i}")
        d_fin = _kiem_wav(dst)

        manh.append((a, str(dst)))
        temps.append(tempo)
        lech_dau.append(0.0)                  # đặt ĐÚNG mốc gốc
        lech_cuoi.append((a + d_fin - b) * 1000.0)
        if on_progress:
            on_progress((i + 1) / max(1, len(cau)),
                        f"Khớp thời gian {i + 1}/{len(cau)}...")

    def _tb(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 1) if xs else 0.0

    return {
        "manh": manh,
        "so_cau": len(manh), "bo_qua": bo_qua,
        "lech_dau_ms_tb": _tb([abs(x) for x in lech_dau]),
        "lech_dau_ms_max": round(max([abs(x) for x in lech_dau] or [0]), 1),
        "lech_cuoi_ms_tb": _tb([abs(x) for x in lech_cuoi]),
        "lech_cuoi_ms_max": round(max([abs(x) for x in lech_cuoi] or [0]), 1),
        "tempo_max": round(max(temps or [1.0]), 3),
        "tempo_tb": round(sum(temps) / len(temps), 3) if temps else 1.0,
        "so_cau_ep": so_ep, "so_cau_muon": so_muon,
        "so_cau_vuot_canh_bao": sum(1 for t in temps if t > tempo_canh_bao),
    }


# ==================================================================
# BƯỚC 6 — TRỘN GIỌNG MỚI + LỚP NHẠC GỐC
# ==================================================================

def _ghep_track_giong(manh: list[tuple[float, str]], tong: float,
                      out_wav: str | Path) -> None:
    """Rải các câu đã khớp lên 1 track im lặng dài ĐÚNG `tong` giây.

    `normalize=0` BẮT BUỘC — không thì amix chia biên độ theo số đầu vào và
    giọng nhỏ dần theo số câu (bẫy đã ghi ở đầu file).
    """
    args: list[str] = ["-f", "lavfi", "-t", f"{tong:.3f}",
                       "-i", f"anullsrc=r={SR_TACH}:cl=stereo"]
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
             "-ac", "2", "-ar", str(SR_TACH), "-c:a", "pcm_s16le",
             str(out_wav)]
    _ffmpeg(args, "ghép track giọng mới", timeout=900)


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
                     video_ra: str | Path) -> None:
    """Thay TIẾNG của video, GIỮ NGUYÊN hình (`-c:v copy`, không encode lại)."""
    _ffmpeg(["-i", str(video_goc), "-i", str(audio_moi),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-shortest", str(video_ra)],
            "thay tiếng vào video", timeout=1800)


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
                     on_progress: Optional[Callable[[float, str], None]] = None,
                     ) -> dict:
    """CHẠY ĐỦ 6 BƯỚC cho 1 video, trả file video MỚI (chưa đụng file gốc).

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
                           on_progress=lambda p, m: prog(0.62 + 0.16 * p, m))
        kq["doc"] = {"voice": tts["voice"], "giay": tts["giay"],
                     "so_hong": tts["so_hong"]}

        # --- bước 5: khớp thời gian
        prog(0.80, "Khớp thời gian...")
        kh = khop_thoi_gian(cau, tts["files"], tts["ok"], tong,
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

        prog(0.96, "Ghép tiếng mới vào video...")
        ra = tam_goc / f"{video_in.stem}__thaygiong{video_in.suffix}"
        thay_audio_video(video_in, au["ra"], ra)
        kq["kiem"] = kiem_video_ra(ra, tong)
        kq["ra"] = str(ra)
        kq["ok"] = True
    except Exception as e:  # noqa: BLE001
        kq["ok"] = False
        kq["loi"] = f"{type(e).__name__}: {e}"
    kq["giay_tong"] = round(time.time() - t0, 2)
    prog(1.0, "Xong" if kq.get("ok") else f"LỖI: {kq.get('loi', '')[:120]}")
    return kq
