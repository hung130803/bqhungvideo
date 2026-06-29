"""
Cấu hình trung tâm + đường dẫn của AI Content Studio.
Mọi module import từ đây để biết file nằm ở đâu và đọc .env.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# ---- Đường dẫn gốc ----
# ROOT_DIR = nơi chứa MÃ/tài nguyên đọc (plugin...). DATA_DIR = nơi chứa DỮ LIỆU
# người dùng (project, db, .env, cookie). Tách 2 cái để khi cập nhật bản .exe
# (thay _internal) KHÔNG làm mất dữ liệu người dùng.
if getattr(sys, "frozen", False):                 # đang chạy bản .exe (PyInstaller)
    ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # cho subprocess tìm thấy ffmpeg/ffprobe/yt-dlp đã đóng gói KÈM trong app
    os.environ["PATH"] = str(ROOT_DIR) + os.pathsep + os.environ.get("PATH", "")
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo"
else:                                             # chạy từ mã nguồn (dev)
    ROOT_DIR = Path(__file__).resolve().parent
    DATA_DIR = ROOT_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(DATA_DIR / ".env")  # nạp .env nếu có

# Nơi lưu dữ liệu chạy (mỗi project 1 thư mục con)
PROJECTS_DIR = DATA_DIR / "projects"
LOGS_DIR = DATA_DIR / "logs"
MODELS_DIR = DATA_DIR / "models"  # cache model whisper...

# Database dùng chung cho toàn app (projects, jobs, kết quả phân tích, clip...)
DB_PATH = DATA_DIR / "studio.db"

for _d in (PROJECTS_DIR, LOGS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


class Settings:
    """Đọc cấu hình từ .env. Giá trị rỗng = để resource manager tự quyết."""

    # LLM (mặc định Groq: free, khôn, nhẹ — khỏi cần Ollama tốn ổ)
    LLM_PROVIDER = _env("LLM_PROVIDER", "groq").lower()

    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY = _env("GEMINI_API_KEY")
    GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash")

    DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
    DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")

    # Ollama (LLM chạy LOCAL, FREE, không giới hạn — dùng GPU của bạn)
    OLLAMA_BASE_URL = _env("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    # DÙNG 1 MODEL cho cả đọc chữ + nhìn hình (VL) -> card 12GB không phải
    # nạp đi nạp lại 2 model (tránh chậm 100s+). VL vẫn đọc text tốt.
    OLLAMA_MODEL = _env("OLLAMA_MODEL", "qwen2.5vl:7b")
    # Model NHÌN ĐƯỢC HÌNH (vision) để chấm viral theo khung hình. Rỗng = tắt.
    OLLAMA_VL_MODEL = _env("OLLAMA_VL_MODEL", "qwen2.5vl:7b")
    # Bật chấm điểm bằng hình ảnh (1) hay tắt (0)
    USE_VISION = _env("USE_VISION", "1") == "1"

    # CHẾ ĐỘ MÁY YẾU (mặc định BẬT): KHÔNG dùng sức máy/GPU — dồn việc lên mây
    # (Groq chép lời + AI cắt). Bỏ dò cảnh / phân tích âm thanh / bám khuôn mặt /
    # chấm điểm bằng hình -> máy yếu vẫn chạy nhanh. Đặt LIGHT_MODE=0 để bật full.
    LIGHT_MODE = _env("LIGHT_MODE", "1") == "1"

    # Whisper
    WHISPER_PROVIDER = _env("WHISPER_PROVIDER", "local").lower()  # local | groq
    GROQ_API_KEYS = _env("GROQ_API_KEYS")      # nhiều key, mỗi dòng/dấu phẩy 1 key
    GROQ_WHISPER_MODEL = _env("GROQ_WHISPER_MODEL", "whisper-large-v3")
    # Groq còn chạy LLM (llama) FREE -> dùng làm AI CẮT, khỏi cần Ollama (đỡ ổ)
    GROQ_LLM_MODEL = _env("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    WHISPER_MODEL = _env("WHISPER_MODEL")      # rỗng = auto theo phần cứng
    WHISPER_LANGUAGE = _env("WHISPER_LANGUAGE") or None
    # Thiết bị chạy whisper: cpu | cuda. Rỗng = cpu (ổn định nhất).
    # Đặt =cuda để dùng GPU (NHANH hơn nhưng cần cài cuDNN, nếu thiếu sẽ sập).
    WHISPER_DEVICE = _env("WHISPER_DEVICE").lower()

    # Diarization
    HUGGINGFACE_TOKEN = _env("HUGGINGFACE_TOKEN")

    # ffmpeg
    FFMPEG_PATH = _env("FFMPEG_PATH", "ffmpeg")
    FFPROBE_PATH = _env("FFPROBE_PATH", "ffprobe")

    # Hiệu năng (rỗng = auto)
    MAX_CPU_WORKERS = _env("MAX_CPU_WORKERS")
    # Số luồng chạy SONG SONG (rỗng = mặc định). Tách 2 khâu cho dễ điều chỉnh:
    AI_WORKERS = _env("AI_WORKERS")          # phân tích + AI chọn cảnh (mỗi video)
    EXPORT_WORKERS = _env("EXPORT_WORKERS")  # cắt/xuất video theo mẫu
    VIDEO_ENCODER = _env("VIDEO_ENCODER", "auto").lower()

    @classmethod
    def llm_key_for(cls, provider: str) -> str:
        # nhiều key (mỗi dòng/dấu phẩy) -> lấy key ĐẦU làm mặc định
        keys = cls.llm_keys_for(provider)
        return keys[0] if keys else ("ollama" if provider == "ollama" else "")

    @classmethod
    def llm_keys_for(cls, provider: str) -> list:
        """DANH SÁCH key (để XOAY VÒNG khi hết quota). Tách theo dòng hoặc dấu phẩy."""
        raw = {
            "openai": cls.OPENAI_API_KEY,
            "gemini": cls.GEMINI_API_KEY,
            "deepseek": cls.DEEPSEEK_API_KEY,
            "groq": cls.GROQ_API_KEYS,
            "ollama": "ollama",
        }.get(provider, "")
        return [k.strip() for k in raw.replace(",", "\n").splitlines() if k.strip()]

    @classmethod
    def groq_keys(cls) -> list:
        return [k.strip() for k in (cls.GROQ_API_KEYS or "").replace(",", "\n")
                .splitlines() if k.strip()]


settings = Settings()


def update_env(values: dict) -> None:
    """Ghi/cập nhật các khóa vào file .env (giữ nguyên dòng khác) + áp NGAY vào
    settings đang chạy (không cần khởi động lại)."""
    path = DATA_DIR / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = {k: ("" if v is None else str(v)) for k, v in values.items()}
    out = []
    for ln in lines:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
        if m and m.group(1) in pending:
            out.append(f"{m.group(1)}={pending.pop(m.group(1))}")
        else:
            out.append(ln)
    for k, v in pending.items():
        out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    # áp ngay vào bộ nhớ
    for k, v in values.items():
        val = v
        if k == "LLM_PROVIDER":
            val = (str(v) or "gemini").strip().lower()
        elif k == "USE_VISION":
            val = str(v) == "1"
        if hasattr(Settings, k):
            setattr(Settings, k, val)
