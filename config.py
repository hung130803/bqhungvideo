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
if FROZEN:
    # Mọi file tạm do app/tiến trình con tạo được gom vào vùng có chủ sở hữu.
    import tempfile
    _owned_temp = DATA_DIR / '_temp'
    _owned_temp.mkdir(parents=True, exist_ok=True)
    (_owned_temp / '.bqhung-owned').touch(exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(_owned_temp)
    tempfile.tempdir = str(_owned_temp)
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

    APIFORCODE_API_KEY = _env("APIFORCODE_API_KEY")
    APIFORCODE_KEYS_FILE = _env("APIFORCODE_KEYS_FILE")
    APIFORCODE_MODEL = _env("APIFORCODE_MODEL", "claude-opus-5-on")
    APIFORCODE_VISION_MODEL = _env("APIFORCODE_VISION_MODEL", "claude-opus-5-on")

    OPENAI_API_KEY = _env("OPENAI_API_KEY")
    OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY = _env("GEMINI_API_KEY")
    GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash")
    # Groq hết key/lỗi thì tự chuyển sang Gemini (cổng 114). Model riêng vì tài
    # khoản mới bị 404 với 2.5, còn 3.5-flash free chỉ 20 lượt/ngày (đo 06/11/2026).
    GEMINI_DU_PHONG = _env("GEMINI_DU_PHONG", "1") == "1"
    GEMINI_DU_PHONG_MODEL = _env("GEMINI_DU_PHONG_MODEL", "gemini-3.5-flash-lite")

    # CHỌN ĐOẠN BẰNG AGENT MUSE (Meta) qua CLI `muse-ai` RỜI — cổng 117,
    # app/ai/muse_agent.py, HUONG_DAN_MUSE.md. "1" bật · "0" tắt (đường Groq y
    # nguyên) · RỖNG = TỰ ĐỘNG: bật khi máy có `muse-ai` + đã đăng nhập Muse
    # (`muse_agent.bat`). Máy nhân viên không cài MuseAI-API -> tắt như cũ.
    # 13/11/2026: anh Hùng chạy cả buổi mà Muse không lần nào được gọi — dòng
    # MUSE_CHON_DOAN=1 Claude ghi bị Windows chuyển sang .env RIÊNG của Claude
    # (MSIX), .env thật không có -> mặc định "0" -> TẮT im lặng.
    MUSE_CHON_DOAN = _env("MUSE_CHON_DOAN", "")
    # Muse hỏng/quá giờ/0 clip -> 1 = tự chọn bằng Groq (rồi Gemini dự phòng) như
    # cũ; 0 = ĐỢI rồi thử Muse lại (DoiLuotAI, trần vòng đợi chung 12/video, hết
    # trần vẫn rơi Groq để video không kẹt mãi).
    MUSE_LUI_GROQ = _env("MUSE_LUI_GROQ", "1") == "1"
    # Muse chọn đoạn xong thì DÙNG LUÔN tiêu đề/điểm/mốc hook của Muse, bỏ 4 bước
    # Groq phía sau (cắt gọn · chấm · đánh bóng tiêu đề · hậu kiểm mạch). Groq chỉ
    # còn chép lời + dự phòng khi Muse hỏng. 0 = Groq làm các bước sau như cũ.
    MUSE_LAM_HET = _env("MUSE_LAM_HET", "1") == "1"
    MUSE_DOI_GIAY = float(_env("MUSE_DOI_GIAY", "60") or 60)   # đợi trước khi thử Muse lại
    MUSE_AI_CLI = _env("MUSE_AI_CLI")            # rỗng = tìm `muse-ai` trên PATH
    MUSE_STATE_DIR = _env("MUSE_STATE_DIR")      # thư mục .muse-state (cookies)
    # NHIỀU tài khoản: các thư mục .muse-state cách nhau bởi dấu phẩy; mỗi video
    # đi tài khoản đang ít việc nhất (muse_agent.chon_phien).
    MUSE_STATE_DIRS = _env("MUSE_STATE_DIRS")
    MUSE_SESSION_ID = _env("MUSE_SESSION_ID")    # rỗng = mỗi việc một phiên mới
    # Đo 13/11/2026 (1 tài khoản): 6 video cùng lúc 6/6 · 15 cùng lúc 12/15 (3 lỗi
    # HTTP 429 lúc mở kết nối -> nay có giãn nhịp + thử lại).
    MUSE_SONG_SONG = _env_int("MUSE_SONG_SONG", 100)   # trần CỨNG cả máy
    MUSE_MOI_TK = _env_int("MUSE_MOI_TK", 16)   # mỗi tài khoản tối đa N video cùng lúc (đo 13/11: 1 tài khoản 30 việc cùng lúc ra 30/30)
    # Đo 14/11/2026 (19 lượt thật): Muse TRẢ LỜI thì luôn trong 55-109 s (kể cả video 21 phút); 7/19
    # lượt KHÔNG BAO GIỜ trả lời và app đợi 22-25 phút (2x độ dài + 600 s). Gửi lại thì trả trong 55 s.
    # Nay đợi 0,1x độ dài + 300 s (19 phút -> ~7 phút, 56 phút -> ~10,5 phút) rồi bỏ để gửi lại.
    MUSE_TIMEOUT_HE_SO = float(_env("MUSE_TIMEOUT_HE_SO", "0.1") or 0.1)
    MUSE_TIMEOUT_THEM = float(_env("MUSE_TIMEOUT_THEM", "300") or 300)
    MUSE_TIMEOUT_MAX = float(_env("MUSE_TIMEOUT_MAX", "3600") or 3600)
    MUSE_POLL_GIAY = float(_env("MUSE_POLL_GIAY", "20") or 20)
    MUSE_PROXY_CAO = _env_int("MUSE_PROXY_CAO", 480)
    MUSE_PROXY_FPS = float(_env("MUSE_PROXY_FPS", "2") or 2)
    # Ảnh tổng hợp gửi kèm Muse: 1 khung mỗi N giây (0 = tắt). Đo 13/11/2026: Muse tự trích
    # khung thưa 30-38 s nên lỡ cảnh hình ngắn (bắt 0-1/4 thẻ 6 s); kèm ảnh 5 s -> 4/4.
    MUSE_BANG_GIAY = float(_env("MUSE_BANG_GIAY", "5") or 0)

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

    # Vbee AIVoice (giọng Việt MUA CHÍNH HÃNG — tùy chọn, user tự cắm key).
    # Cần ĐỦ CẢ HAI: App ID + access token (khác Groq/ElevenLabs chỉ 1 chuỗi);
    # thiếu một nửa mà vẫn gọi là ăn 401 rồi tưởng key sai. Thiếu key ->
    # app LÙI ÊM về edge-tts, không nổ (app/core/giong_vbee.py).
    # LƯU Ý TIỀN: Vbee tính 1 điểm / 1 ký tự, và gói thường chỉ cho dùng MỘT
    # NỬA số điểm qua API (phải VIP+ mới dùng trọn). Vbee KHÔNG có cửa hỏi số
    # điểm còn lại nên app không chặn trước được — xem đầu giong_vbee.py.
    VBEE_APP_ID = _env("VBEE_APP_ID")
    VBEE_TOKEN = _env("VBEE_TOKEN")

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
    # TRẦN BITRATE file Part xuất (Mbps). 0 = không trần (như bản cũ).
    # 26/10/2026 anh Hùng: Part 2 phút ra 585 MB (~34 Mbps) -> up TikTok rất
    # lâu. Mẫu nền mờ + lớp vọng + video bodycam nhiễu làm CQ 19 "đòi" bitrate
    # rất cao; TikTok nén lại còn vài Mbps nên phần vượt 12 Mbps không thấy
    # được trên điện thoại. Trần chỉ chạm vào cảnh nặng, cảnh thường giữ nguyên.
    EXPORT_MAX_MBPS = _env_int("EXPORT_MAX_MBPS", 12)
    # Núm nén hiệu quả của NVENC (lookahead, AQ, khung B) — tự thử máy có hỗ
    # trợ không. 0 = tắt, dùng đúng lệnh NVENC cũ.
    EXPORT_NVENC_HQ = _env("EXPORT_NVENC_HQ", "1") == "1"
    # BÌA TIKTOK: khung đầu không fade từ đen + lưu ảnh bìa đẹp nhất vào _Bia.
    EXPORT_COVER = _env("EXPORT_COVER", "1") == "1"

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
    # ── PHÉP ĐO 06/08/2026 GIỮ LẠI LÀM CĂN CỨ, nhưng KẾT LUẬN của nó ("giữ
    #    llama làm mặc định") đã HẾT HIỆU LỰC: 17/08/2026 Groq GỠ HẲN llama,
    #    không còn lựa chọn nào để giữ. Xem khối ══ bên dưới. ──
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
    # => (kết luận CŨ 06/08: giữ llama cho khâu cắt — nay KHÔNG áp dụng được
    #    nữa vì llama đã bị gỡ). Muốn thử model khác cho riêng khâu cắt: đặt
    #    SELECT_MODEL trong .env (không phải đổi GROQ_LLM_MODEL, tránh ảnh
    #    hưởng khâu reup vốn thật sự bị 413).
    #    LƯU Ý HÀNH VI ĐỔI THEO: gpt-oss thiên về lấy 1 KHỐI LIỀN thay vì ghép
    #    2-7 đoạn như llama. Đó là thay đổi CÁCH CẮT, không phải tụt điểm —
    #    nhưng anh Hùng xem clip sẽ thấy khác, nên phải nói ra.
    # GROQ_LLM_MODEL_CREATIVE: model RIÊNG cho các pass VIẾT kịch bản reup —
    # mặc định RỖNG = dùng chung model chính.
    # Model lỗi "không tồn tại"/413/content rỗng -> app TỰ RƠI VỀ
    # GROQ_LLM_FALLBACK ngay trong lệnh gọi, không bao giờ chết ở máy khách.
    # ══ 17/08/2026 — GROQ KHAI TỬ `llama-3.3-70b-versatile`. ĐỌC TRƯỚC KHI SỬA ══
    # Hỏi thẳng GET /models bằng key thật: model đó KHÔNG còn trong danh sách,
    # gọi vào ra 404 `model_not_found`. TOÀN BỘ họ Llama đã biến mất khỏi Groq
    # (chỉ còn 2 model `llama-prompt-guard` 512 token, không phải model chat).
    # Hậu quả trên máy anh Hùng: cắt/thay giọng/reup chết cả dây chuyền, 6 lỗi
    # liên tiếp — và lời lỗi làm anh ấy tưởng HẾT HẠN MỨC 41 key.
    #
    # LỖI KIẾN TRÚC LÀM BẢN CŨ KHÔNG TỰ CỨU ĐƯỢC: `GROQ_LLM_MODEL` và
    # `GROQ_LLM_FALLBACK` để **CÙNG MỘT TÊN**, mà lưới rơi-về-fallback trong
    # `llm._call_once` có điều kiện `model != fb` -> lưới KHÔNG BAO GIỜ chạy.
    # BẤT BIẾN TỪ NAY: model chính và model dự phòng phải KHÁC HỌ NHAU.
    #
    # Đo thật 17/08/2026 (gọi chat thật từng model, cùng câu hỏi, temperature=0):
    #   openai/gpt-oss-120b  0,95s  trả lời ĐÚNG      <-- CHỌN LÀM MODEL CHÍNH
    #   groq/compound        1,54s  trả lời ĐÚNG      <-- dự phòng 1 (KHÁC HỌ)
    #   openai/gpt-oss-20b   0,60s  trả lời SAI       <-- dự phòng 2 (phao cuối)
    # gpt-oss-120b đã được đo ở khâu CHỌN ĐOẠN từ 06/08: 53,3 điểm so với llama
    # 52,2 (trọng tài chấm mù) -> đổi sang nó KHÔNG tụt chất lượng.
    # LƯU Ý ĐO ĐƯỢC: gpt-oss là model SUY LUẬN — đặt `max_tokens` thấp thì phần
    # "nghĩ" ăn hết chỗ và content trả về RỖNG. App KHÔNG đặt max_tokens cho
    # chat nên không dính; chỗ gọi mới thì phải nhớ. Và `reasoning_effort` nay
    # CHỈ nhận low/medium/high — `"none"` trả 400 (llm.py đã có lưới gọi lại).
    GROQ_LLM_MODEL = _env("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
    GROQ_LLM_MODEL_CREATIVE = _env("GROQ_LLM_MODEL_CREATIVE", "")
    # 31/10/2026: `groq/compound` ĐÃ BỊ GROQ GỠ (không còn trong /models) -> dây
    # chuyền thực chất chỉ còn 2 model CÙNG HỌ gpt-oss, mà cả hai cùng trả RỖNG
    # theo một kiểu (nghĩ hết ~5.800 token ở mức "low", finish=length; đo 20
    # lượt trong logs/llm_rong_20261031.log). Dự phòng nay là qwen3.8-27b: còn
    # sống, KHÁC HỌ, tắt được phần nghĩ (`reasoning_effort="none"`, đo 0,7s).
    GROQ_LLM_FALLBACK = _env("GROQ_LLM_FALLBACK", "qwen/qwen3.8-27b")
    #: DÂY CHUYỀN DỰ PHÒNG THÊM (phân cách bằng dấu phẩy) — thử sau model chính
    #: và model dự phòng. Groq sẽ còn khai tử model nữa; có dây chuyền thì lần
    #: sau app chỉ chậm đi một nhịp chứ không chết. Xem `llm.chuoi_model_groq`.
    GROQ_LLM_CHAIN = _env("GROQ_LLM_CHAIN", "openai/gpt-oss-20b")
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
    GROQ_VISION_MODEL = _env("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
    # MỨC SUY NGHĨ của model suy luận Groq (gpt-oss) cho khâu QUAN TRỌNG: chọn
    # đoạn, chấm, tiêu đề, hậu kiểm mạch, viết kịch bản recap (low|medium|high).
    # Mặc định "high" (26/10/2026 — anh Hùng: chất lượng trước, chậm cũng được).
    # Dịch/thay giọng (hàng loạt) LUÔN "low" — đo 18/08: low đủ cho dịch.
    # Nghĩ kỹ mà hết chỗ trả lời -> llm.py TỰ hạ high->medium->low + gọi lại
    # bằng key khác (log `llm_rong_*.log`). Nút ⚙ "Chất lượng AI tối đa".
    GROQ_REASONING_EFFORT = _env("GROQ_REASONING_EFFORT", "high")
    # (tùy chọn) ghi đè từng việc: "select=high,judge=medium,translate=low".
    # Việc: select · judge · title · coherence · recap (khác -> low).
    GROQ_REASONING_EFFORT_TASKS = _env("GROQ_REASONING_EFFORT_TASKS", "")
    # Trần thời gian NGHỈ của 1 key Groq sau lỗi hết lượt (giây). Lỗi hạn mức
    # NGÀY (TPD) Groq hay báo "thử lại sau 20-30 phút" nhưng key thường dùng
    # lại được sớm hơn nhiều (đo 01/11/2026) -> nghỉ tối đa 5 phút rồi thử lại.
    GROQ_NGHI_TOI_DA = _env("GROQ_NGHI_TOI_DA", "300")
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
    #: KHÂU TRỌNG TÀI CHẤM MÙ — MẶC ĐỊNH TẮT (anh Hùng chốt 13/11/2026).
    #: Đo `_do_cham_diem.py` (5 video thật, Groq thật): Part xuất ra GIỐNG HỆT
    #: 5/5 khi bỏ khâu này, vì điểm chỉ dùng để XẾP HẠNG (rank_only) và lúc đó
    #: số clip đã <= số Part. Giá của nó ~12K token (~23%) + 20-30 s/video.
    #: `BLIND_JUDGE=1` bật lại (điểm trên thẻ clip lúc đó là điểm trọng tài).
    BLIND_JUDGE = _env("BLIND_JUDGE", "0") == "1"
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
    # Mặc định "max" từ 26/10/2026 (anh Hùng có hàng trăm key xoay vòng). An
    # toàn: critic/refine lỗi (413/hết lượt) -> recap._refine_script GIỮ bản nháp.
    RECAP_QUALITY = _env("RECAP_QUALITY", "max")
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
    #: GIẢI MÃ BẰNG GPU (NVDEC) khi xuất. 27/10/2026: mặc định "auto" — máy
    #: xuất bằng NVENC thì THỬ THẬT giải mã GPU 1 lần, chạy được mới dùng.
    #: Giải mã H.264/HEVC/VP9/AV1 theo chuẩn cho ĐÚNG từng điểm ảnh như CPU, nên
    #: hình không đổi; chỉ bớt việc cho CPU. "1" = luôn bật, "0" = tắt hẳn.
    #: Lỗi giữa chừng -> tự chạy lại bằng CPU và tắt cho cả phiên.
    HWACCEL_DECODE = {"1": True, "true": True, "yes": True, "on": True,
                      "0": False, "false": False, "no": False, "off": False
                      }.get(_env("HWACCEL_DECODE", "auto").lower(), "auto")

    @classmethod
    def llm_key_for(cls, provider: str) -> str:
        # nhiều key (mỗi dòng/dấu phẩy) -> lấy key ĐẦU làm mặc định
        keys = cls.llm_keys_for(provider)
        return keys[0] if keys else ("ollama" if provider == "ollama" else "")

    @classmethod
    def llm_keys_for(cls, provider: str) -> list:
        """DANH SÁCH key (để XOAY VÒNG khi hết quota). Tách theo dòng hoặc dấu phẩy.
        Groq gộp thêm key từ GROQ_KEYS_FILE (hàng trăm key) qua groq_keys()."""
        if provider == "apiforcode":
            pasted=(cls.APIFORCODE_API_KEY or '').replace(',', '\n').splitlines()
            path=cls.APIFORCODE_KEYS_FILE
            try:
                raw=Path(path).read_bytes() if path else b''
                text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
                pasted.extend(text.splitlines())
            except (OSError,UnicodeError):
                pass
            # Purchased key files may contain a label/account on the same line.
            return list(dict.fromkeys(re.findall(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])', '\n'.join(pasted))))
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
    # GHI NGUYÊN TỬ (rà soát 01/11/2026): file này chứa MỌI key Groq; ghi đè
    # tại chỗ mà mất điện / tắt app giữa chừng là .env cụt -> mất sạch key ->
    # app lặng lẽ chép lời bằng whisper máy (chậm hàng chục lần). Ghi file tạm,
    # flush + fsync rồi os.replace; giữ 1 bản .env.bak trước khi thay.
    tam = path.with_name(path.name + ".tmp")
    with open(tam, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    try:
        if path.exists():
            import shutil as _sh
            _sh.copy2(path, path.with_name(path.name + ".bak"))
    except OSError:
        pass
    os.replace(tam, path)
    _ap_vao_bo_nho(values)
    _ghi_nhat_ky_luu(path, pending)


def _ghi_nhat_ky_luu(path, pending: dict) -> None:
    """07/11/2026: anh Hùng bấm Lưu (app hiện "Đã lưu cài đặt AI") mà file
    .env trên đĩa vẫn bản 03/11, 1 key Gemini. Ghi lại MỖI lượt lưu: đường dẫn
    thật, giờ sửa file, SỐ key ghi vs số key đọc lại được (KHÔNG ghi key) để
    lần sau nhìn là biết lưu đi đâu / có lọt không. Không bao giờ ném lỗi."""
    try:
        import datetime
        from dotenv import dotenv_values
        doc = dotenv_values(path)
        dem = lambda v: len([x for x in re.split(r"[,\s]+", str(v or "")) if x])
        phan = []
        for k in ("GEMINI_API_KEY", "GROQ_API_KEYS", "ELEVENLABS_API_KEYS"):
            if k in pending:
                ghi, doc_lai = dem(pending[k]), dem(doc.get(k))
                phan.append(f"{k}: ghi {ghi} · đọc lại {doc_lai}"
                            + ("" if ghi == doc_lai else " · LỆCH!"))
        ts = datetime.datetime.now()
        d = DATA_DIR / "logs"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"luu_cai_dat_{ts:%Y%m%d}.log", "a", encoding="utf-8") as f:
            f.write(f"{ts:%H:%M:%S} pid={os.getpid()} {path} "
                    f"(sửa {datetime.datetime.fromtimestamp(path.stat().st_mtime):%d/%m %H:%M:%S}) "
                    + " | ".join(phan) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _ap_vao_bo_nho(values: dict) -> None:
    """Áp giá trị .env vào `Settings` đang chạy (đúng kiểu từng khoá)."""
    for k, v in values.items():
        val = v
        if k == "LLM_PROVIDER":
            val = (str(v) or "groq").strip().lower()  # khớp mặc định ở trên
        elif k in ("USE_VISION", "LIGHT_MODE", "ECO_MODE", "EXPORT_COVER",
                   "MUSE_CHON_DOAN", "MUSE_LUI_GROQ", "MUSE_LAM_HET", "GEMINI_DU_PHONG"):
            val = str(v) == "1"    # setting bool: giữ đúng kiểu khi áp live
        elif k == "EXPORT_MAX_MBPS":
            try:
                val = max(0, int(str(v).strip() or 0))
            except ValueError:
                val = 12
        if hasattr(Settings, k):
            setattr(Settings, k, val)


def nap_lai_tu_dia(keys) -> list:
    """Đọc lại các khoá `keys` từ file .env TRÊN ĐĨA rồi áp vào app đang chạy.

    03/11/2026: anh Hùng thêm 2 key Groq mà không vào được file. Hộp Cài đặt
    AI dựng ô key từ BỘ NHỚ của app, nên (a) key ghi vào .env từ ngoài (bot,
    lượt sửa tay, bản app khác) không hiện ra và app không dùng tới cho tới khi
    mở lại, (b) bấm Lưu lúc đó còn GHI ĐÈ mất các key đó. Gọi hàm này lúc mở
    hộp thì file trên đĩa là sự thật duy nhất. Khoá không có trong file -> giữ
    nguyên bộ nhớ. Trả danh sách khoá đã đổi. Không bao giờ ném lỗi."""
    try:
        from dotenv import dotenv_values
        tren_dia = dotenv_values(DATA_DIR / ".env")
    except Exception:  # noqa: BLE001
        return []
    doi = {}
    for k in keys:
        if k in tren_dia and tren_dia[k] is not None:
            v = tren_dia[k]
            if str(getattr(Settings, k, "") or "") != v:
                doi[k] = v
    if doi:
        _ap_vao_bo_nho(doi)
    return sorted(doi)
