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
FROZEN = getattr(sys, "frozen", False)
if FROZEN:                                        # đang chạy bản .exe (PyInstaller)
    ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # cho subprocess tìm thấy ffmpeg/ffprobe/yt-dlp đã đóng gói KÈM trong app
    os.environ["PATH"] = str(ROOT_DIR) + os.pathsep + os.environ.get("PATH", "")
    # TRỎ THẲNG vào binary đóng gói (chắc chắn, khỏi phụ thuộc PATH)
    for _b in ("ffmpeg", "ffprobe"):
        _p = ROOT_DIR / f"{_b}.exe"
        if _p.exists():
            os.environ[_b.upper() + "_PATH"] = str(_p)
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo"
else:                                             # chạy từ mã nguồn (dev)
    ROOT_DIR = Path(__file__).resolve().parent
    DATA_DIR = ROOT_DIR
# BQ_DATA_DIR: override nơi chứa DỮ LIỆU (projects/db/cache) — dùng cho test
# cách ly (không đụng dữ liệu thật) hoặc user muốn chuyển kho sang ổ khác.
if os.environ.get("BQ_DATA_DIR"):
    DATA_DIR = Path(os.environ["BQ_DATA_DIR"])


def bundled_exe(name: str) -> str:
    """Đường dẫn binary đóng gói kèm (.exe) khi chạy bản đóng gói; '' nếu không có."""
    if FROZEN:
        p = ROOT_DIR / f"{name}.exe"
        if p.exists():
            return str(p)
    return ""
DATA_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(DATA_DIR / ".env")  # nạp .env nếu có

# Nơi lưu dữ liệu chạy (mỗi project 1 thư mục con)
PROJECTS_DIR = DATA_DIR / "projects"
LOGS_DIR = DATA_DIR / "logs"
MODELS_DIR = DATA_DIR / "models"  # cache model whisper...

# Database dùng chung cho toàn app (projects, jobs, kết quả phân tích, clip...)
# Ưu tiên biến môi trường BQ_DB_PATH: khi app CHÍNH phải cứu DB hỏng và ĐỔI sang
# file khác (studio_<ts>.db) hoặc RAM, nó set BQ_DB_PATH để mọi TIẾN TRÌNH CON
# (phân tích) mở ĐÚNG file app chính đang dùng — nếu không subprocess mở studio.db
# rỗng và báo "không tìm thấy video".
DB_PATH = Path(os.environ.get("BQ_DB_PATH") or (DATA_DIR / "studio.db"))

for _d in (PROJECTS_DIR, LOGS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _env_bool(key: str, default: bool = False) -> bool:
    """Đọc cờ bật/tắt từ .env: '1'/'true'/'yes'/'on' -> True (không phân
    biệt hoa thường). Rỗng -> `default`."""
    v = _env(key, "").lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _env_int(key: str, default: int = 0) -> int:
    """Đọc số nguyên từ .env. Rỗng/không phải số -> `default` (không sập app
    vì user gõ nhầm chữ vào .env)."""
    v = _env(key, "")
    try:
        return int(float(v)) if v else default
    except ValueError:
        return default


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

    # ElevenLabs TTS (giọng lồng tiếng/thuyết minh CAO CẤP — tùy chọn, user tự
    # cắm key). Nhiều key mỗi dòng/dấu phẩy (tự xoay vòng khi hết hạn mức free
    # 10k ký tự/tháng) — đọc y hệt GROQ_API_KEYS. ELEVENLABS_API_KEY giữ để
    # tương thích/1 key; gộp cả 2 khi liệt kê key.
    ELEVENLABS_API_KEY = _env("ELEVENLABS_API_KEY")
    ELEVENLABS_API_KEYS = _env("ELEVENLABS_API_KEYS")
    # Model TTS ElevenLabs mặc định (đa ngôn ngữ, ổn định). Đặt "eleven_v3"
    # để dùng v3 alpha (biểu cảm hơn); dubbing tự lùi về v2 nếu API báo lỗi.
    ELEVENLABS_MODEL = _env("ELEVENLABS_MODEL", "eleven_multilingual_v2")

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

    # TIẾT KIỆM MÁY (mặc định BẬT): khi app đang xuất/phân tích, máy vẫn dùng
    # bình thường (lướt web, mở app khác không giật). Bật -> chỉ 1 job xuất +
    # 1 job phân tích chạy cùng lúc, ffmpeg dùng ~1/2 ngân sách luồng CPU,
    # yt-dlp tải 4 mảnh song song (thay vì 8). Tắt = "Hiệu năng tối đa" (nhiều
    # job song song, chia đều ngân sách luồng — vẫn ưu tiên thấp + chừa 2 nhân).
    ECO_MODE = _env("ECO_MODE", "1") == "1"

    # Whisper
    WHISPER_PROVIDER = _env("WHISPER_PROVIDER", "local").lower()  # local | groq
    GROQ_API_KEYS = _env("GROQ_API_KEYS")      # nhiều key, mỗi dòng/dấu phẩy 1 key
    # File .txt chứa HÀNG TRĂM key Groq (mỗi dòng 1 key). App GỘP key ở ô dán
    # (GROQ_API_KEYS) + key trong file này (dedup, giữ thứ tự). Tách file riêng
    # vì .env 1 dòng = 1 khóa, không nhét được hàng trăm dòng.
    GROQ_KEYS_FILE = _env("GROQ_KEYS_FILE")
    # (tùy chọn) file key ElevenLabs — cùng cơ chế
    ELEVENLABS_KEYS_FILE = _env("ELEVENLABS_KEYS_FILE")
    GROQ_WHISPER_MODEL = _env("GROQ_WHISPER_MODEL", "whisper-large-v3")
    # Groq còn chạy LLM FREE -> dùng làm AI CẮT, khỏi cần Ollama (đỡ ổ).
    # MODEL CHÍNH mặc định = llama-3.3-70b-versatile.
    # ĐO LẠI 06/08/2026 (`_do_model_manh.py` + `_do_so_model.py`, 3 video THẬT,
    # trọng tài chấm MÙ) — ghi chú cũ "gpt-oss-120b bị 413 / trả rỗng" CHỈ ĐÚNG
    # với prompt REUP (dài). Với khâu CHỌN ĐOẠN thì SAI:
    #   prompt chọn đoạn thật chỉ ~8.400 ký tự (~2.100 token) vì transcript đã
    #   được CHIA KHÚC -> gpt-oss-120b chạy TỐT: 0 lỗi 413, 0 khúc trả rỗng.
    #   CHẤT LƯỢNG: llama 52,2 điểm vs gpt-oss 53,3 điểm (+1,1 = trong sai số),
    #   gpt-oss chậm hơn 23s/3 video.
    #   ĐIỀU QUAN TRỌNG HƠN ĐIỂM: llama ghép 2-7 ĐOẠN mỗi clip (bỏ phần nhạt ở
    #   giữa rồi nối phần hay) còn gpt-oss gần như chỉ lấy 1 KHỐI LIỀN (8/9
    #   clip = 1 đoạn) và còn ăn cả intro (11,7s) lẫn outro (998-1062s).
    # => GIỮ llama làm mặc định cho khâu cắt. Muốn thử model khác: đặt
    #    SELECT_MODEL trong .env (không phải đổi GROQ_LLM_MODEL, tránh ảnh
    #    hưởng khâu reup vốn thật sự bị 413).
    # GROQ_LLM_MODEL_CREATIVE: model RIÊNG cho các pass VIẾT kịch bản reup —
    # mặc định RỖNG = dùng chung model chính.
    # Model lỗi "không tồn tại"/413/content rỗng -> app TỰ RƠI VỀ
    # GROQ_LLM_FALLBACK ngay trong lệnh gọi, không bao giờ chết ở máy khách.
    GROQ_LLM_MODEL = _env("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    GROQ_LLM_MODEL_CREATIVE = _env("GROQ_LLM_MODEL_CREATIVE", "")
    GROQ_LLM_FALLBACK = _env("GROQ_LLM_FALLBACK", "llama-3.3-70b-versatile")
    # Model THÔNG MINH NHẤT cho các lệnh NGẮN, chất lượng quyết định bộ mặt
    # kênh: ĐÁNH BÓNG TIÊU ĐỀ (đúng ngôn ngữ video, giật tít) + hashtag.
    # gpt-oss-120b trên tier free CHẠY TỐT với prompt ngắn (đã test thật —
    # chỉ prompt đạo diễn dài mới bị 413); lỗi gì đã có lưới rơi về
    # GROQ_LLM_FALLBACK trong llm._call_once. Đặt rỗng để tắt (dùng model chính).
    GROQ_LLM_MODEL_SMART = _env("GROQ_LLM_MODEL_SMART", "openai/gpt-oss-120b")
    # (tùy chọn) model Groq MẠNH HƠN cho các pass CHẤM/VIẾT LẠI chất lượng cao.
    # Mặc định = GROQ_LLM_MODEL (không đổi hành vi); user tự trỏ model xịn hơn.
    GROQ_LLM_MODEL_HQ = _env("GROQ_LLM_MODEL_HQ", "") or _env(
        "GROQ_LLM_MODEL", "openai/gpt-oss-120b")
    # Model Groq NHÌN ĐƯỢC HÌNH (vision) — AI xem khung hình khi chọn đoạn.
    # ĐO 06/08/2026 (hỏi thẳng /models của Groq rồi thử ảnh thật từng model):
    # `meta-llama/llama-4-scout…` và `…maverick…` ĐÃ BỊ GỠ -> 404; compound và
    # llama-3.3-70b KHÔNG nhận ảnh (400 "content must be a string"); model duy
    # nhất còn nhìn được là `qwen/qwen3.6-27b` (mô tả đúng cảnh bodycam thật).
    # Nó là model SUY LUẬN nên trả kèm khối <think> — llm._extract_json đã bóc.
    # Giới hạn cứng: 3 ảnh/lượt (xem llm.vision_max_images).
    # Đặt rỗng để tắt vision Groq.
    GROQ_VISION_MODEL = _env("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
    # NHIỀU-PASS (mặc định BẬT): AI tự chấm bản nháp rồi viết lại tốt hơn cho
    # CẮT GHÉP clip + THOẠI recap. Mọi pass mới nếu lỗi/không hợp lệ/tệ hơn ->
    # TỰ QUAY VỀ bản cũ (fail-safe, không bao giờ làm xấu đi). Đặt =0 để tắt.
    AI_MULTIPASS = _env_bool("AI_MULTIPASS", True)
    # SÀN CHẤT LƯỢNG clip AI cắt (0-100): sau khi AI chọn + chấm điểm, clip
    # có score DƯỚI sàn bị BỎ — "chỉ giữ đoạn đáng dùng". Luôn giữ ít nhất
    # 1 clip điểm cao nhất (không bao giờ trắng tay). Đặt 0 để tắt.
    #: HỘI ĐỒNG 3 TRỌNG TÀI chấm clip (3 góc nhìn, lấy trung vị) — 1 trọng tài
    #: duy nhất từng chấm lệch/parse hỏng (đo 06/08/2026). 0 = 1 trọng tài.
    #: BẬT AI XEM HÌNH cho khâu chọn đoạn mà KHÔNG phải tắt LIGHT_MODE (tắt
    #: LIGHT_MODE sẽ bật luôn faces/mediapipe rất nặng và vô dụng với luồng
    #: dùng mẫu khung). Mặc định TẮT — phải ĐO chi phí (số ảnh + lượt Groq +
    #: giây/video) trước khi bật cho 300 kênh.
    VISION_CUT = _env("VISION_CUT", "0") == "1"
    #: HẬU KIỂM BẢN GHÉP (`app/ai/mach_lac.py`): sau khi đã chọn xong các đoạn,
    #: đọc LỜI THOẠI của chính chúng rồi hỏi AI "ghép theo thứ tự này có mạch
    #: lạc không" -> đổi thứ tự / bỏ 1 đoạn. Thêm ~1 lượt LLM NGẮN mỗi Part.
    #: Fail-safe tuyệt đối: lỗi / hết lượt / JSON rác -> GIỮ NGUYÊN lựa chọn
    #: ban đầu. Đặt `HAU_KIEM_GHEP=0` để tắt hẳn (chạy y như v2.20.0).
    HAU_KIEM_GHEP = _env("HAU_KIEM_GHEP", "1") == "1"
    #: SỐ LƯỢT AI XEM HÌNH CHẠY SONG SONG (mỗi lượt một key Groq khác nhau).
    #: **MẶC ĐỊNH 1 = TUẦN TỰ, Y HỆT v2.20.0 — vì ĐO RA SONG SONG KHÔNG CHẮC
    #: NHANH HƠN.** Ghi thẳng số, không tô hồng:
    #:
    #: 1) `_do_vision_219.py` (video thật, 38 key) tách 219 giây ra:
    #:      trích khung (ffmpeg)  1,45 giây = **1,3%**
    #:      đợi API (tuần tự)   107,80 giây = **98,7%**
    #:    -> nút thắt đúng là ĐỢI MẠNG, không phải CPU máy. Lượt đo ĐẦU TIÊN
    #:    cho song song 39,20 giây (**2,75x**) và trông rất hứa hẹn.
    #: 2) NHƯNG đo lại bằng `_do_vision_ss.py` trên ĐÚNG `build_vision_digest`,
    #:    **6 lượt mỗi mức, ĐAN XEN** (máy anh Hùng luôn có prodown chạy nền):
    #:      tuần tự  : trung vị **45,23** giây (min 5,54 · max 100,53)
    #:      song song: trung vị **40,05** giây (min 19,48 · max 75,34)
    #:      = 1,13x, mà **hai khoảng min-max CHỒNG NHAU** -> KHÔNG kết luận được.
    #:    Lý do: chính Groq trả về rất thất thường — CÙNG một lượt tuần tự đo
    #:    được 5,54 giây rồi 100,53 giây. Song song chỉ bỏ được phép CỘNG, không
    #:    bỏ được cái ĐUÔI: `max(4 lượt)` gần bằng `tổng(4 lượt)` khi một lượt
    #:    chiếm hết. Số 2,75x của lần đo đầu là MAY, không lặp lại được.
    #: KẾT LUẬN THẲNG: **bật AI xem hình cho MỌI clip vẫn KHÔNG khả thi** —
    #: ~40 giây/video ở cả hai mức, đuôi tới 100 giây, nhân 300 kênh là quá đắt.
    #: Mã song song vẫn giữ (đã đo: KHÔNG mất mốc nào, 7/7 cả 6 lượt) để bật
    #: bằng `VISION_SONG_SONG=6` khi Groq đổi hành vi — nhưng KHÔNG bật sẵn.
    VISION_SONG_SONG = int(_env("VISION_SONG_SONG", "1") or 1)
    JUDGE_PANEL = _env("JUDGE_PANEL", "1") == "1"
    #: model cho khâu CHẤM. **ĐỂ RỖNG — đã ĐO, model suy luận KHÔNG hơn.**
    #: Đo 06/08/2026 (bộ đo `_do_trongtai.py`: 3 clip biết trước thứ tự hay/dở
    #: A cao trào > B thường > C intro rác, 3 lượt mỗi model):
    #:   llama-3.3-70b (mặc định) -> xếp ĐÚNG 3/3 lượt, 80-85 / 20-40 / 0-10,
    #:                               1,2 giây/lượt
    #:   qwen/qwen3.6-27b (SUY LUẬN) -> 0/3 lượt (không ra nổi đáp án), 19,5
    #:                               giây/lượt = chậm 16 LẦN
    #: Vì sao hỏng: nó tiêu gần hết max_tokens cho khối <think> nên câu trả lời
    #: bị cắt giữa lúc đang nghĩ. Muốn dùng thì phải nới max_tokens rất rộng ->
    #: càng chậm + càng cạn hạn mức, mà độ chính xác thì đã đầy điểm sẵn.
    #: Muốn chấm CHẮC TAY hơn thì dùng HỘI ĐỒNG 3 TRỌNG TÀI (JUDGE_PANEL=1,
    #: đang bật) — lấy trung vị 3 góc nhìn, rẻ và ổn định hơn.
    #: (prompt CHỌN ĐOẠN cũng KHÔNG đổi model được: gpt-oss-120b -> lỗi 413.)
    JUDGE_MODEL = _env("JUDGE_MODEL", "")
    #: model cho khâu CHỌN ĐOẠN (quyết định quan trọng nhất của cả tool).
    #: ĐO 06/08/2026 — ghi chú cũ "prompt chọn đoạn 413 nên không đổi được
    #: model" là SAI: transcript đã được CHIA KHÚC (_chunk_transcript) nên
    #: prompt thật chỉ ~8.400 ký tự (~2.100 token), model nào cũng nhận:
    #:   llama-3.3-70b (cũ)  -> 6,7s, ra 3 clip
    #:   openai/gpt-oss-120b -> 7,3s, ra 3 clip   <-- MẠNH NHẤT trên Groq
    #: Rỗng = dùng GROQ_LLM_MODEL như cũ.
    SELECT_MODEL = _env("SELECT_MODEL", "")
    QUALITY_FLOOR = _env_int("QUALITY_FLOOR", 55)
    # CHẤT LƯỢNG kịch bản AI reup (đánh đổi CHẤT LƯỢNG vs TOKEN/ngày Groq):
    #   "save"    = luôn 1-pass (ít token nhất, nhanh nhất)
    #   "balance" = nhiều-pass cho video NGẮN, 1-pass cho video DÀI (mặc định)
    #   "max"     = nhiều-pass MỌI video (chất lượng cao nhất, tốn token nhất —
    #               video dài dễ chạm HẠN MỨC TOKEN/NGÀY của Groq)
    RECAP_QUALITY = _env("RECAP_QUALITY", "balance")
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
        """DANH SÁCH key (để XOAY VÒNG khi hết quota). Tách theo dòng hoặc dấu phẩy.
        Groq gộp thêm key từ GROQ_KEYS_FILE (hàng trăm key) qua groq_keys()."""
        if provider == "groq":
            return cls.groq_keys()
        raw = {
            "openai": cls.OPENAI_API_KEY,
            "gemini": cls.GEMINI_API_KEY,
            "deepseek": cls.DEEPSEEK_API_KEY,
            "ollama": "ollama",
        }.get(provider, "")
        return [k.strip() for k in raw.replace(",", "\n").splitlines() if k.strip()]

    @staticmethod
    def _read_keys_file(path: str) -> list:
        """Đọc file .txt mỗi dòng 1 key: bỏ dòng trống + dòng comment (#).
        File lỗi/không tồn tại -> trả [] (KHÔNG ném lỗi, app vẫn chạy bằng ô dán)."""
        if not path:
            return []
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        out = []
        for ln in text.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.append(ln)
        return out

    @classmethod
    def groq_keys(cls) -> list:
        """DANH SÁCH key Groq (xoay vòng khi hết quota). GỘP key ở ô dán
        (GROQ_API_KEYS, mỗi dòng/dấu phẩy 1 key) + key trong file GROQ_KEYS_FILE
        (mỗi dòng 1 key, bỏ trống/comment). DEDUP giữ thứ tự xuất hiện. File
        lỗi/không có -> chỉ dùng ô dán (không crash)."""
        pasted = [k.strip() for k in (cls.GROQ_API_KEYS or "").replace(",", "\n")
                  .splitlines() if k.strip()]
        from_file = cls._read_keys_file(cls.GROQ_KEYS_FILE)
        out, seen = [], set()
        for k in pasted + from_file:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    @classmethod
    def elevenlabs_keys(cls) -> list:
        """DANH SÁCH key ElevenLabs (để XOAY VÒNG khi hết hạn mức). Gộp cả
        ELEVENLABS_API_KEY (1 key) lẫn ELEVENLABS_API_KEYS (nhiều key), tách
        theo dòng hoặc dấu phẩy, bỏ trùng — giữ thứ tự xuất hiện."""
        raw = ((cls.ELEVENLABS_API_KEYS or "") + "\n" +
               (cls.ELEVENLABS_API_KEY or ""))
        pasted = [k.strip() for k in raw.replace(",", "\n").splitlines() if k.strip()]
        from_file = cls._read_keys_file(cls.ELEVENLABS_KEYS_FILE)
        out, seen = [], set()
        for k in pasted + from_file:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out


settings = Settings()


def update_env(values: dict) -> None:
    """Ghi/cập nhật các khóa vào file .env (giữ nguyên dòng khác) + áp NGAY vào
    settings đang chạy (không cần khởi động lại)."""
    path = DATA_DIR / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    # .env là định dạng 1 dòng = 1 khóa. Giá trị NHIỀU DÒNG (vd dán nhiều key
    # Groq mỗi dòng 1 key) sẽ vỡ file -> đọc lại chỉ được key ĐẦU. Chuyển
    # newline -> dấu phẩy khi ghi (llm_keys_for/groq_keys tách cả 2 kiểu).
    pending = {k: ("" if v is None else
                   re.sub(r"[\r\n]+", ",", str(v)).strip(","))
               for k, v in values.items()}
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
            val = (str(v) or "groq").strip().lower()  # khớp mặc định ở trên
        elif k in ("USE_VISION", "LIGHT_MODE", "ECO_MODE"):
            val = str(v) == "1"    # setting bool: giữ đúng kiểu khi áp live
        if hasattr(Settings, k):
            setattr(Settings, k, val)
