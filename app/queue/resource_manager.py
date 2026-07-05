"""
Resource manager: dò phần cứng lúc khởi động và TỰ ĐỀ XUẤT cấu hình
(whisper model, device, encoder, số worker, số job đồng thời) để không treo máy.

Người dùng có thể override qua .env (xem config.Settings).
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict

from config import settings


@dataclass
class HardwareInfo:
    cpu_cores: int = 1
    ram_gb: float = 0.0
    has_cuda: bool = False
    gpu_name: str = ""
    vram_gb: float = 0.0
    has_ffmpeg: bool = False
    has_nvenc: bool = False


@dataclass
class ResourceProfile:
    # phân tích
    whisper_model: str = "small"
    device: str = "cpu"          # cpu | cuda
    compute_type: str = "int8"   # int8 (cpu) | float16 (gpu)
    # encode
    encoder: str = "libx264"     # libx264 | h264_nvenc
    # song song
    max_cpu_workers: int = 2
    max_gpu_workers: int = 1     # hàng đợi GPU riêng để 2 job không tranh GPU
    notes: list[str] = None      # giải thích cho UI


def detect_hardware() -> HardwareInfo:
    hw = HardwareInfo()

    # CPU + RAM
    try:
        import psutil
        hw.cpu_cores = psutil.cpu_count(logical=True) or os.cpu_count() or 1
        hw.ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        hw.cpu_cores = os.cpu_count() or 1

    # GPU NVIDIA qua nvidia-smi (không cần torch)
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            import subprocess
            out = subprocess.run(
                [smi, "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=8,
                # bản .exe windowed: thiếu cờ này sẽ NHÁY cửa sổ console đen
                # mỗi lần mở app (trông như virus với khách)
                creationflags=(0x08000000 if os.name == "nt" else 0),
                stdin=subprocess.DEVNULL,
            )
            line = (out.stdout or "").strip().splitlines()
            if line:
                name, mem = line[0].split(",")
                hw.has_cuda = True
                hw.gpu_name = name.strip()
                hw.vram_gb = round(float(mem) / 1024, 1)
        except Exception:  # noqa: BLE001
            pass

    # ffmpeg + nvenc
    from app.core.ffmpeg_utils import ffmpeg_available, detect_encoder
    hw.has_ffmpeg = ffmpeg_available()
    if hw.has_ffmpeg:
        hw.has_nvenc = detect_encoder() == "h264_nvenc" if hw.has_cuda else False

    return hw


def suggest_profile(hw: HardwareInfo) -> ResourceProfile:
    """Đề xuất cấu hình theo phần cứng. Tôn trọng override trong .env."""
    notes: list[str] = []
    p = ResourceProfile(notes=notes)

    # ---- Whisper model + device ----
    # MẶC ĐỊNH chạy GPU nếu có card + đã cài cuDNN (pip nvidia-cudnn-cu12) -> nhanh
    # ~20 lần. Thiếu cuDNN hoặc ép WHISPER_DEVICE=cpu -> chạy CPU (vẫn ổn).
    import importlib.util as _ilu
    try:
        cudnn_ok = _ilu.find_spec("nvidia.cudnn") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        cudnn_ok = False        # bản .exe không kèm nvidia -> coi như không có cuDNN

    force_cpu = settings.WHISPER_DEVICE == "cpu"
    want_cuda = hw.has_cuda and cudnn_ok and not force_cpu and hw.vram_gb >= 6
    if want_cuda:
        # large-v3: model whisper CHÍNH XÁC NHẤT (phụ đề chuẩn ~ CapCut). Trên GPU
        # 12GB vẫn nhanh (~12x realtime). Card yếu hơn (<8GB VRAM) tự lùi medium.
        p.whisper_model = "large-v3" if hw.vram_gb >= 8 else "medium"
        p.device = "cuda"
        p.compute_type = "float16"
        notes.append(f"GPU {hw.gpu_name} -> whisper {p.whisper_model} (chính xác cao). "
                     "Muốn nhanh hơn: WHISPER_MODEL=medium hoặc small.")
    else:
        # chọn theo RAM để tránh OOM
        if hw.ram_gb >= 16 or hw.ram_gb == 0:
            p.whisper_model = "small"
        elif hw.ram_gb >= 8:
            p.whisper_model = "base"
        else:
            p.whisper_model = "tiny"
        p.device = "cpu"
        p.compute_type = "int8"
        if hw.has_cuda and not cudnn_ok:
            notes.append("Có GPU nhưng THIẾU cuDNN -> whisper chạy CPU (chậm). Tăng "
                         "tốc ~20x: chạy `pip install nvidia-cudnn-cu12 "
                         "nvidia-cublas-cu12` rồi mở lại app.")
        elif hw.has_cuda and force_cpu:
            notes.append(f"WHISPER_DEVICE=cpu -> chạy CPU (whisper {p.whisper_model}).")
        else:
            notes.append(f"Whisper {p.whisper_model} chạy CPU (int8).")

    # ---- Encoder ----
    if hw.has_nvenc:
        p.encoder = "h264_nvenc"
        notes.append("Encode bằng NVENC (GPU) — nhanh.")
    else:
        p.encoder = "libx264"
        notes.append("Encode bằng libx264 (CPU).")

    # ---- Số luồng SONG SONG (tách 2 khâu) ----
    # GPU lane = luồng AI/phân tích; CPU lane = luồng cắt/xuất video (libx264).
    p.max_cpu_workers = 3
    if p.encoder == "libx264":
        # Encode CPU: mỗi ffmpeg đã bị giới hạn ~1/3 luồng (xem _enc_args) nhưng
        # vẫn nặng -> TRẦN đề xuất = cpu_cores//8 để máy không đơ 100% CPU.
        # Chỉ là MẶC ĐỊNH đề xuất — user vẫn override được (spin UI / .env).
        p.max_cpu_workers = min(p.max_cpu_workers, max(1, hw.cpu_cores // 8))
    if hw.ram_gb:                                    # máy ít RAM -> giảm cho an toàn
        p.max_cpu_workers = max(1, min(p.max_cpu_workers, int(hw.ram_gb // 4)))
    # Số luồng pipeline (auto/xuất) chạy song song. Lời gọi AI (Ollama) được KHÓA
    # tuần tự trong llm.py nên KHÔNG tràn VRAM dù nhiều luồng: phần nghe-chép lời
    # (whisper) của nhiều video chạy song song, AI vẫn xử lý lần lượt -> an toàn.
    # luồng AI (Ollama khóa tuần tự nên nhiều luồng vẫn không tràn VRAM)
    p.max_gpu_workers = 3 if hw.has_cuda else 2
    if hw.ram_gb:
        p.max_gpu_workers = max(1, min(p.max_gpu_workers, int(hw.ram_gb // 4)))

    # ---- Override từ .env ----
    if settings.WHISPER_MODEL:
        p.whisper_model = settings.WHISPER_MODEL
        notes.append(f"(.env override) whisper={p.whisper_model}")
    if settings.AI_WORKERS.isdigit():
        p.max_gpu_workers = max(1, int(settings.AI_WORKERS))
    if settings.EXPORT_WORKERS.isdigit():
        p.max_cpu_workers = max(1, int(settings.EXPORT_WORKERS))
    elif settings.MAX_CPU_WORKERS.isdigit():
        p.max_cpu_workers = max(1, int(settings.MAX_CPU_WORKERS))
    notes.append(f"{p.max_gpu_workers} luồng AI + {p.max_cpu_workers} luồng cắt video.")
    if settings.VIDEO_ENCODER in ("nvenc", "libx264"):
        p.encoder = "h264_nvenc" if settings.VIDEO_ENCODER == "nvenc" else "libx264"

    if not hw.has_ffmpeg:
        notes.append("⚠ CHƯA tìm thấy ffmpeg — cài ffmpeg hoặc đặt FFMPEG_PATH trong .env.")

    return p


def profile_dict(p: ResourceProfile) -> dict:
    return asdict(p)


# Dò 1 lần lúc import, cache lại
HARDWARE = detect_hardware()
PROFILE = suggest_profile(HARDWARE)
