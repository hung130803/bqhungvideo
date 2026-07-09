"""
LỒNG TIẾNG AI (dubbing) bằng edge-tts (giọng Microsoft Neural — hay, tự nhiên, free).
Tùy chọn CAO CẤP: Gemini TTS (giọng "gemini:Kore"...) — nét hơn, cần key Gemini,
hạn mức free thấp; hết hạn mức thì tự CHUYỂN CẢ TRACK về edge-tts (giọng dự phòng).

Quy trình build_dub_track:
  1. Lấy các câu transcript nằm trong clip_segments, ÁNH XẠ mốc về timeline đầu ra
     (giống captions._remap_words — clip ghép nhiều khúc, bỏ khúc thừa).
  2. GOM các segment liền kề (gap < 0.4s) thành CÂU/cụm -> giọng đọc tự nhiên.
  3. DỊCH 1 lần tất cả cụm bằng LLM (JSON mảng cùng số phần tử, văn nói NGẮN GỌN
     lọt khung thời gian). target == ngôn ngữ gốc -> bỏ qua dịch.
  4. TTS từng cụm (edge-tts, song song tối đa 4 cụm/lượt).
  5. KHỚP THỜI GIAN (mặc định "Tự nhiên"): mỗi cụm NEO đúng start gốc; đọc tốc
     độ thường, CHỈ tăng tốc (atempo ≤1.5, chia tầng) khi lời đọc sắp ĐÈ sang
     start cụm kế; đọc ngắn hơn khung -> giữ nguyên (im lặng tự đệm, KHÔNG kéo
     dài). Chế độ "Khớp chặt" -> ép mỗi cụm lọt khung riêng như cũ. Chế độ
     "Khớp video (mượt)" -> KHÔNG tăng tốc giọng (đọc hoàn toàn tự nhiên) và
     TÍNH hệ số kéo dài tổng (stretch): khi lời đọc dài hơn khung gốc, trả về
     ratio > 1 để export CO GIÃN NHẸ cả clip video cho khớp giọng (như
     pyVideoTrans) thay vì tăng tốc gắt. Cụm TTS lỗi
     -> BỎ RIÊNG cụm đó, cụm khác GIỮ ĐÚNG mốc. Ghép: anullsrc đúng tổng độ dài
     + adelay từng cụm theo start + amix -> 1 file WAV 48kHz dài ĐÚNG bằng clip.

Chỉ dùng subprocess ffmpeg (settings.FFMPEG_PATH) — không thêm dependency audio.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Callable, Optional

from config import DATA_DIR, settings

_CREATE_NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0

# Gom 2 câu transcript liền kề thành 1 cụm nếu hở dưới ngưỡng này (giây)
_JOIN_GAP = 0.4
# Tăng tốc tối đa cho phép để nhét lời đọc vào khung thời gian (nghe vẫn tự nhiên).
# 1.5 = trần khi lời đọc SẼ ĐÈ sang cụm kế (chỉ tăng tốc vừa đủ để không đè).
_MAX_TEMPO = 1.5
# Chế độ "Khớp video (mượt)": trần hệ số kéo dài (làm chậm) clip video. Vượt
# quá thì phần dư vẫn tăng tốc giọng nhẹ (để clip không bị chậm đến mức lố).
# 1.5 = cho phép clip dài ra tối đa 50% — đủ nuốt hầu hết câu dịch dài mà nhìn
# vẫn tự nhiên (pyVideoTrans thường 1.05–1.3x).
_MAX_STRETCH = 1.5
# Số cụm TTS chạy song song (edge-tts qua mạng)
_TTS_PARALLEL = 4

# 🎙 Reup thuyết minh — NHỊP KỂ user chọn (Cài đặt Reup) -> rate edge-tts.
# Giá trị NHỎ có chủ đích: fit window (atempo) tự bù phần lệch, rate chỉ đổi
# "đà" giọng đọc gốc (thong thả vs dồn dập) trước khi khớp khung.
RECAP_PACES = {"slow": "-3%", "normal": "+0%", "fast": "+4%"}


def recap_pace_rate(pace: str) -> str:
    """Đổi key nhịp kể ('slow'/'normal'/'fast') -> rate edge-tts."""
    return RECAP_PACES.get(str(pace or "").strip().lower(), "+0%")


# 🎙 Reup thuyết minh — TÔNG GIỌNG user chọn (Cài đặt Reup) -> pitch edge-tts.
# ±18Hz nghe khác RÕ (trầm ấm hơn / sáng cao hơn) mà giọng không méo.
# Giọng Gemini KHÔNG hỗ trợ pitch -> bỏ qua (giữ tông gốc).
RECAP_PITCHES = {"low": "-18Hz", "normal": "+0Hz", "high": "+18Hz"}


def recap_pitch_hz(pitch: str) -> str:
    """Đổi key tông giọng ('low'/'normal'/'high') -> pitch edge-tts ('-18Hz'
    /'+0Hz'/'+18Hz'). Key lạ/rỗng -> '+0Hz' (giữ tông gốc)."""
    return RECAP_PITCHES.get(str(pitch or "").strip().lower(), "+0Hz")


def _bump_rate(rate: str, delta: int) -> str:
    """Cộng thêm delta điểm % vào rate edge-tts ('+0%' + 2 -> '+2%').
    Dùng cho câu HOOK mở đầu recap (đọc nhanh hơn nhịp nền ~2% cho có
    năng lượng). Rate lạ/parse hỏng -> coi như 0."""
    try:
        v = int(str(rate or "").strip().rstrip("%") or 0)
    except ValueError:
        v = 0
    return f"{v + delta:+d}%"


# Giọng Gemini KHÔNG có tham số rate -> truyền vibe kể chuyện bằng CHỈ DẪN
# prepend vào text TTS (chỉ dẫn KHÔNG lọt vào phụ đề/words — caller giữ text
# gốc cho narrate_events).
_GEMINI_NARRATE_PREFIX = {
    "vi": "Kể như người kể chuyện lôi cuốn, ngắt nghỉ kịch tính: ",
    "en": "Narrate like a gripping storyteller, with dramatic pauses: ",
}


def gemini_narrate_prefix(lang: str) -> str:
    """Chỉ dẫn kể chuyện prepend vào text Gemini TTS, theo ngôn ngữ video."""
    return _GEMINI_NARRATE_PREFIX.get(norm_lang(lang),
                                      _GEMINI_NARRATE_PREFIX["en"])

# Ngôn ngữ hỗ trợ -> [(nhãn hiển thị, voice_id NỮ), (nhãn, voice_id NAM)]
VOICES: dict[str, list[tuple[str, str]]] = {
    "vi": [("Nữ — Hoài My", "vi-VN-HoaiMyNeural"),
           ("Nam — Nam Minh", "vi-VN-NamMinhNeural")],
    "en": [("Nữ — Jenny", "en-US-JennyNeural"),
           ("Nam — Guy", "en-US-GuyNeural")],
    "id": [("Nữ — Gadis", "id-ID-GadisNeural"),
           ("Nam — Ardi", "id-ID-ArdiNeural")],
    "th": [("Nữ — Premwadee", "th-TH-PremwadeeNeural"),
           ("Nam — Niwat", "th-TH-NiwatNeural")],
    "ko": [("Nữ — SunHi", "ko-KR-SunHiNeural"),
           ("Nam — InJoon", "ko-KR-InJoonNeural")],
    "ja": [("Nữ — Nanami", "ja-JP-NanamiNeural"),
           ("Nam — Keita", "ja-JP-KeitaNeural")],
    "zh": [("Nữ — Xiaoxiao", "zh-CN-XiaoxiaoNeural"),
           ("Nam — Yunxi", "zh-CN-YunxiNeural")],
    "es": [("Nữ — Elvira", "es-ES-ElviraNeural"),
           ("Nam — Alvaro", "es-ES-AlvaroNeural")],
    "pt": [("Nữ — Francisca", "pt-BR-FranciscaNeural"),
           ("Nam — Antonio", "pt-BR-AntonioNeural")],
    "fr": [("Nữ — Denise", "fr-FR-DeniseNeural"),
           ("Nam — Henri", "fr-FR-HenriNeural")],
}

# ---- GIỌNG HOT (được ưa dùng nhất, tự nhiên nhất) — ghim lên ĐẦU danh sách,
# gắn ⭐. Gồm các giọng Multilingual đời mới (đọc được MỌI ngôn ngữ, tự nhiên
# gần bằng ElevenLabs) + giọng bản địa hay nhất mỗi tiếng. ----
_HOT_VOICES = {
    # Đa ngữ (đọc được mọi thứ tiếng — hot nhất, giọng kể chuyện tự nhiên)
    "en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural",
    "en-US-AvaMultilingualNeural", "en-US-EmmaMultilingualNeural",
    # Tiếng Anh Mỹ nam trầm (kiểu "Adam" kể chuyện)
    "en-US-GuyNeural", "en-US-DavisNeural", "en-US-JasonNeural",
    "en-US-TonyNeural", "en-US-EricNeural", "en-US-AndrewNeural",
    "en-US-BrianNeural", "en-US-SteffanNeural", "en-US-ChristopherNeural",
    # Tiếng Anh Mỹ nữ hot
    "en-US-JennyNeural", "en-US-AriaNeural", "en-US-MichelleNeural",
    "en-US-SaraNeural", "en-US-NancyNeural",
    # Anh-Anh (giọng Anh Quốc)
    "en-GB-RyanNeural", "en-GB-SoniaNeural",
    # Tiếng Việt
    "vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural",
    # Các tiếng khác — giọng hay nhất
    "id-ID-ArdiNeural", "id-ID-GadisNeural",
    "th-TH-NiwatNeural", "th-TH-PremwadeeNeural",
    "ko-KR-InJoonNeural", "ko-KR-SunHiNeural",
    "ja-JP-KeitaNeural", "ja-JP-NanamiNeural",
    "zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural", "zh-CN-YunjianNeural",
    "es-ES-AlvaroNeural", "pt-BR-AntonioNeural", "fr-FR-HenriNeural",
}

# ---- NHÓM "🔥 ĐỀ XUẤT — mượt & hot nhất" (curate TAY, có MÔ TẢ từng giọng)
# — sửa lỗi user "không biết giọng nào mượt/hot": danh sách ngắn đã nghe
# kiểm chứng, ghim NGAY dưới nhóm Gemini. [(voice_id, "Tên — mô tả")].
# Giọng "đa ngôn ngữ" đọc được MỌI thứ tiếng — hợp kênh reup đa nguồn. ----
_RECOMMENDED_VOICES: list[tuple[str, str]] = [
    # Đa ngôn ngữ (đọc mọi thứ tiếng)
    ("en-US-AndrewMultilingualNeural",
     "Andrew — Nam trầm ấm, kể chuyện hay nhất (đa ngôn ngữ)"),
    ("en-US-BrianMultilingualNeural",
     "Brian — Nam trẻ, tự nhiên (đa ngôn ngữ)"),
    ("en-US-AvaMultilingualNeural",
     "Ava — Nữ mượt, sáng (đa ngôn ngữ)"),
    ("en-US-EmmaMultilingualNeural",
     "Emma — Nữ ấm áp (đa ngôn ngữ)"),
    # Tiếng Anh (Mỹ)
    ("en-US-AndrewNeural", "Andrew — Nam trầm ấm (tiếng Anh)"),
    ("en-US-BrianNeural", "Brian — Nam trẻ, tự nhiên (tiếng Anh)"),
    ("en-US-ChristopherNeural",
     "Christopher — Nam trầm uy tín (tiếng Anh)"),
    ("en-US-GuyNeural", "Guy — Nam kiểu tin tức, dứt khoát (tiếng Anh)"),
    ("en-US-AriaNeural", "Aria — Nữ rõ ràng, biểu cảm (tiếng Anh)"),
    ("en-US-JennyNeural", "Jenny — Nữ thân thiện, đều giọng (tiếng Anh)"),
    # Tiếng Việt
    ("vi-VN-NamMinhNeural", "Nam Minh — Nam chuẩn (tiếng Việt)"),
    ("vi-VN-HoaiMyNeural", "Hoài My — Nữ nhẹ nhàng (tiếng Việt)"),
]

# ---- GEMINI TTS (tùy chọn CAO CẤP — giọng nét nhất, cần key Gemini) ----
# Voice id dạng "gemini:Kore" (khác hẳn ShortName edge -> không đụng nhau).
# Giọng prebuilt đa ngôn ngữ (đọc tiếng Việt tự nhiên). Hạn mức free THẤP
# (vài request/phút) -> synth TUẦN TỰ + retry 429 + fallback edge-tts.
_GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
_GEMINI_PREBUILT = [
    "Kore", "Zephyr", "Puck", "Charon", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]


def _gemini_available() -> bool:
    """Có key Gemini trong settings không (đọc y hệt llm.py — .env)."""
    try:
        return bool(settings.llm_keys_for("gemini"))
    except Exception:  # noqa: BLE001 — settings hỏng thì coi như không có
        return False


def _gemini_voice_items() -> list[tuple[str, str]]:
    """Nhóm giọng Gemini cho combo: [("🌟 Kore (Gemini)", "gemini:Kore"), ...]."""
    return [(f"🌟 {n} (Gemini)", f"gemini:{n}") for n in _GEMINI_PREBUILT]


# ---- ELEVENLABS TTS (tùy chọn CHẤT LƯỢNG CAO NHẤT — cần key, user tự cắm) ----
# Voice id dạng "el:{voice_id}" (khác hẳn ShortName edge & "gemini:" -> không
# đụng nhau). Trả BYTES mp3 trực tiếp (không base64) -> ghi thẳng .mp3, pipeline
# hiện có xử lý như edge. KHÔNG có rate/pitch param -> bỏ qua (fit window vẫn
# qua atempo). KHÔNG trả word timestamps -> phụ đề recap dùng câu-cụm (như
# Gemini). Hạn mức free 10k ký tự/tháng -> 401/429 -> mark key + fallback edge.
_ELEVEN_MODEL_DEFAULT = "eleven_multilingual_v2"
# Model hỗ trợ AUDIO TAG cảm xúc ([excited]/[whispers]/[dramatic pause]...) —
# dùng khi user BẬT "Giọng cảm xúc" + chọn giọng ElevenLabs. Chưa mở/lỗi model
# -> _eleven_tts tự LÙI về _ELEVEN_MODEL_DEFAULT (v2 không hiểu tag -> caller
# đã _strip_audio_tags trước khi gửi cho v2/edge/gemini).
_ELEVEN_MODEL_V3 = "eleven_v3"
# Bảng GIỌNG NỔI TIẾNG (voice_id premade CÔNG KHAI của ElevenLabs) — luôn có
# kể cả khi GET /voices lỗi/chưa gọi. Adam ĐẦU danh sách (nam trầm Mỹ, hay kể
# chuyện). [(voice_id, "Tên — mô tả")].
_ELEVEN_PREMADE: list[tuple[str, str]] = [
    ("pNInz6obpgDQGcFmaJgB", "Adam — Nam trầm Mỹ, kể chuyện hay"),
    ("ErXwobaYiN019PkySvjV", "Antoni — Nam ấm, cuốn hút"),
    ("VR6AewLTigWG4xSOukaG", "Arnold — Nam khỏe, dứt khoát"),
    ("TxGEqnHWrfWFTfGW9XjX", "Josh — Nam trẻ, sâu"),
    ("21m00Tcm4TlvDq8ikWAM", "Rachel — Nữ điềm tĩnh, rõ ràng"),
    ("EXAVITQu4vr4xnSDxMaL", "Bella — Nữ nhẹ nhàng"),
    ("AZnzlk1XvdvUeBnXmlld", "Domi — Nữ mạnh mẽ, tự tin"),
    ("MF3mGyEYCl7XYWbV9V6O", "Elli — Nữ trẻ, tươi sáng"),
    ("yoZ06aMxZJJ28mfd3POQ", "Sam — Nam trung tính, kể tin"),
]
# CACHE danh sách giọng account (GET /voices) 7 ngày như voice edge.
_ELEVEN_VOICES_CACHE_FILE = DATA_DIR / "_eleven_voices.json"
_ELEVEN_VOICES_TTL = 7 * 24 * 3600
_eleven_voices_ram: list[tuple[str, str]] | None = None   # cache RAM


def _eleven_keys() -> list:
    """DANH SÁCH key ElevenLabs (đọc y hệt pattern key hiện có — .env)."""
    try:
        return settings.elevenlabs_keys()
    except Exception:  # noqa: BLE001 — settings hỏng thì coi như không có
        return []


def _eleven_available() -> bool:
    """Có key ElevenLabs trong settings không (đọc y hệt _gemini_available)."""
    return bool(_eleven_keys())


def _eleven_model() -> str:
    """Model TTS ElevenLabs (settings.ELEVENLABS_MODEL) — mặc định
    multilingual_v2 (đa ngôn ngữ, ổn định)."""
    return (getattr(settings, "ELEVENLABS_MODEL", "") or "").strip() \
        or _ELEVEN_MODEL_DEFAULT


def _eleven_voices() -> list[tuple[str, str]]:
    """Danh sách giọng ElevenLabs cho combo: [("🎧 Adam (ElevenLabs — Nam
    trầm Mỹ)", "el:pNInz..."), ...]. Ưu tiên giọng ACCOUNT (GET /voices, cache
    7 ngày) — có thì merge lên đầu (bỏ trùng premade); luôn KÈM bảng premade
    công khai. Không key/lỗi mạng -> chỉ premade (vẫn dùng được)."""
    premade = [(f"🎧 {desc.split(' — ')[0]} (ElevenLabs — "
                f"{desc.split(' — ', 1)[1]})", f"el:{vid}")
               for vid, desc in _ELEVEN_PREMADE]
    if not _eleven_available():
        return premade
    account = _fetch_eleven_voices()      # [(name, voice_id)] từ account
    if not account:
        return premade
    premade_ids = {vid for vid, _ in _ELEVEN_PREMADE}
    acc_items = [(f"🎧 {name} (ElevenLabs)", f"el:{vid}")
                 for name, vid in account if vid not in premade_ids]
    # Adam (premade đầu) vẫn để trước, rồi giọng account, rồi premade còn lại
    return premade[:1] + acc_items + premade[1:]


def _read_eleven_cache(max_age: float) -> list | None:
    """Đọc cache giọng account nếu còn hạn; None nếu hỏng/quá hạn."""
    try:
        data = json.loads(
            _ELEVEN_VOICES_CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts", 0)) < max_age:
            v = data.get("voices")
            if isinstance(v, list):
                return [(x[0], x[1]) for x in v if isinstance(x, list)
                        and len(x) == 2]
    except (OSError, ValueError, TypeError):
        pass
    return None


def _fetch_eleven_voices() -> list[tuple[str, str]]:
    """Giọng account [(name, voice_id)] qua GET /v1/voices (header key).
    Cache RAM -> cache file còn hạn (7 ngày) -> gọi mạng -> offline: cache cũ
    -> [] (caller dùng premade)."""
    global _eleven_voices_ram
    if _eleven_voices_ram is not None:
        return _eleven_voices_ram
    v = _read_eleven_cache(_ELEVEN_VOICES_TTL)
    if v is None:
        keys = _eleven_keys()
        if not keys:
            _eleven_voices_ram = []
            return []
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": keys[0]}, method="GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            v = [(str(x.get("name") or ""), str(x.get("voice_id") or ""))
                 for x in (data.get("voices") or [])
                 if x.get("voice_id")]
            if v:
                try:
                    _ELEVEN_VOICES_CACHE_FILE.write_text(
                        json.dumps({"ts": time.time(),
                                    "voices": [list(t) for t in v]},
                                   ensure_ascii=False),
                        encoding="utf-8")
                except OSError:
                    pass
        except Exception:  # noqa: BLE001 — offline/lỗi mạng/key sai
            v = _read_eleven_cache(float("inf"))   # cache cũ còn hơn không
    _eleven_voices_ram = v or []
    return _eleven_voices_ram


# Nhãn tiếng Việt cho combo UI
LANG_LABELS = {
    "vi": "Tiếng Việt", "en": "Tiếng Anh", "id": "Tiếng Indonesia",
    "th": "Tiếng Thái", "ko": "Tiếng Hàn", "ja": "Tiếng Nhật",
    "zh": "Tiếng Trung", "es": "Tiếng Tây Ban Nha",
    "pt": "Tiếng Bồ Đào Nha", "fr": "Tiếng Pháp",
}

# Chuẩn hoá tên ngôn ngữ whisper trả về ("english"/"vietnamese"...) -> mã 2 chữ
_LANG_ALIASES = {
    "vietnamese": "vi", "english": "en", "indonesian": "id", "thai": "th",
    "korean": "ko", "japanese": "ja", "chinese": "zh", "mandarin": "zh",
    "spanish": "es", "portuguese": "pt", "french": "fr",
}


def norm_lang(code: str) -> str:
    c = (code or "").strip().lower()
    return _LANG_ALIASES.get(c, c[:2])


def default_voice(lang: str) -> str:
    """Giọng mặc định (nữ) của ngôn ngữ; '' nếu không hỗ trợ."""
    vs = VOICES.get(norm_lang(lang))
    return vs[0][1] if vs else ""


# ------------------------------------------------------------------
# Danh sách TOÀN BỘ giọng edge-tts (cache RAM + file, TTL 7 ngày)
# ------------------------------------------------------------------
_VOICES_CACHE_FILE = DATA_DIR / "_tts_voices.json"
_VOICES_TTL = 7 * 24 * 3600            # 7 ngày
_all_voices: list[dict] | None = None  # cache module-level (RAM)

_GENDER_VI = {"female": "nữ", "male": "nam"}


def _read_voices_cache(max_age: float) -> list[dict] | None:
    """Đọc cache file nếu còn hạn (max_age giây); None nếu hỏng/quá hạn."""
    try:
        data = json.loads(_VOICES_CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts", 0)) < max_age:
            v = data.get("voices")
            if isinstance(v, list) and v:
                return v
    except (OSError, ValueError, TypeError):
        pass
    return None


def _fetch_all_voices() -> list[dict]:
    """Toàn bộ giọng edge-tts [{ShortName,Gender,Locale}]. Thứ tự thử:
    cache RAM -> cache file còn hạn (7 ngày) -> gọi mạng (rồi ghi cache)
    -> offline: dùng cache file CŨ quá hạn -> [] (caller fallback VOICES)."""
    global _all_voices
    if _all_voices:
        return _all_voices
    v = _read_voices_cache(_VOICES_TTL)
    if v is None:
        try:
            import edge_tts
            raw = asyncio.run(edge_tts.list_voices())
            v = [{"ShortName": x.get("ShortName", ""),
                  "Gender": x.get("Gender", ""),
                  "Locale": x.get("Locale", "")}
                 for x in raw if x.get("ShortName")]
            if v:
                try:
                    _VOICES_CACHE_FILE.write_text(
                        json.dumps({"ts": time.time(), "voices": v},
                                   ensure_ascii=False),
                        encoding="utf-8")
                except OSError:
                    pass
        except Exception:  # noqa: BLE001 — offline/mạng lỗi
            v = _read_voices_cache(float("inf"))   # cache cũ còn hơn không
    _all_voices = v or []
    return _all_voices


def _voice_label(v: dict) -> str:
    """Nhãn thân thiện: 'HoaiMy — nữ (VN)' / 'Andrew — nam (US, đa ngữ)'."""
    short = v.get("ShortName", "")
    parts = short.split("-", 2)
    name = parts[2] if len(parts) == 3 else short
    if name.endswith("Neural"):
        name = name[:-len("Neural")]
    multi = "Multilingual" in name
    if multi:
        name = name.replace("Multilingual", "")
    g = _GENDER_VI.get((v.get("Gender") or "").lower(), "?")
    region = (v.get("Locale") or "").split("-")[-1]
    star = "⭐ " if short in _HOT_VOICES else ""      # giọng HOT -> gắn sao
    return f"{star}{name} — {g} ({region}, đa ngữ)" if multi \
        else f"{star}{name} — {g} ({region})"


def list_voices_for(lang: str) -> list[tuple[str, str]]:
    """TOÀN BỘ giọng của ngôn ngữ `lang` -> [(nhãn, voice_id)].
    Nhóm 🌟 Gemini (id "gemini:Kore"...) lên TRÊN CÙNG — CHỈ khi có key Gemini
    (không key -> ẩn nhóm). Tiếp theo là giọng edge-tts: cùng quốc gia chính
    trước (vi -> vi-VN), kèm giọng Multilingual ở cuối. Offline/lỗi mạng ->
    fallback danh sách tĩnh VOICES."""
    lang = norm_lang(lang)
    el = _eleven_voices() if _eleven_available() else []
    gem = _gemini_voice_items() if _gemini_available() else []
    static = list(VOICES.get(lang, []))
    allv = _fetch_all_voices()
    if not allv:
        return el + gem + static
    pref = "-".join(static[0][1].split("-")[:2]) if static else ""  # "vi-VN"
    native = [v for v in allv
              if (v.get("Locale") or "").lower().startswith(lang + "-")]
    seen = {v["ShortName"] for v in native}
    multi = [v for v in allv
             if "multilingual" in v.get("ShortName", "").lower()
             and v["ShortName"] not in seen]
    fav = {vid for _, vid in static}    # giọng mặc định cũ (đã kiểm chứng hay)
    # Ưu tiên: giọng HOT (⭐) trước > cùng vùng chính > mặc định cũ > còn lại
    native.sort(key=lambda v: (0 if v["ShortName"] in _HOT_VOICES else 1,
                               0 if v.get("Locale") == pref else 1,
                               0 if v["ShortName"] in fav else 1,
                               v.get("Locale", ""), v.get("ShortName", "")))
    # giọng đa ngữ HOT lên đầu nhóm đa ngữ
    multi.sort(key=lambda v: (0 if v["ShortName"] in _HOT_VOICES else 1,
                              v.get("ShortName", "")))
    edge = [(_voice_label(v), v["ShortName"]) for v in native + multi]
    return el + gem + (edge or static)


# Bảng locale/mã ngôn ngữ -> (cờ, tên tiếng Việt) cho danh sách giọng KỂ
# recap (user không biết "en-US-Andrew" là tiếng gì -> nhóm + nhãn Việt).
# Ưu tiên khớp FULL locale ("en-US") rồi mới tới mã ngôn ngữ ("en");
# không có trong bảng -> hiện mã locale thô.
_LOCALE_VI: dict[str, tuple[str, str]] = {
    "vi": ("🇻🇳", "Tiếng Việt"),
    "en-US": ("🇺🇸", "Tiếng Anh (Mỹ)"),
    "en-GB": ("🇬🇧", "Tiếng Anh (Anh)"),
    "en-AU": ("🇦🇺", "Tiếng Anh (Úc)"),
    "en-IN": ("🇮🇳", "Tiếng Anh (Ấn Độ)"),
    "en": ("🌍", "Tiếng Anh (vùng khác)"),
    "ja": ("🇯🇵", "Tiếng Nhật"),
    "ko": ("🇰🇷", "Tiếng Hàn"),
    "zh-CN": ("🇨🇳", "Tiếng Trung"),
    "zh-TW": ("🇹🇼", "Tiếng Trung (Đài Loan)"),
    "zh-HK": ("🇭🇰", "Tiếng Quảng Đông (Hồng Kông)"),
    "zh": ("🇨🇳", "Tiếng Trung"),
    "th": ("🇹🇭", "Tiếng Thái"),
    "id": ("🇮🇩", "Tiếng Indonesia"),
    "ms": ("🇲🇾", "Tiếng Mã Lai"),
    "fil": ("🇵🇭", "Tiếng Philippines"),
    "fr": ("🇫🇷", "Tiếng Pháp"),
    "de": ("🇩🇪", "Tiếng Đức"),
    "es": ("🇪🇸", "Tiếng Tây Ban Nha"),
    "es-MX": ("🇲🇽", "Tiếng Tây Ban Nha (Mexico)"),
    "pt-BR": ("🇧🇷", "Tiếng Bồ Đào Nha (Brazil)"),
    "pt": ("🇵🇹", "Tiếng Bồ Đào Nha"),
    "ru": ("🇷🇺", "Tiếng Nga"),
    "it": ("🇮🇹", "Tiếng Ý"),
    "hi": ("🇮🇳", "Tiếng Hindi"),
    "ar": ("🇸🇦", "Tiếng Ả Rập"),
    "tr": ("🇹🇷", "Tiếng Thổ Nhĩ Kỳ"),
    "nl": ("🇳🇱", "Tiếng Hà Lan"),
    "pl": ("🇵🇱", "Tiếng Ba Lan"),
}
# Thứ tự nhóm ngôn ngữ trong combo (Việt trước, rồi các tiếng phổ biến)
_GROUP_ORDER = ["vi", "en-US", "en-GB", "ja", "ko", "zh-CN", "zh", "th",
                "id", "fr", "es", "pt-BR", "pt"]

# Dòng thông báo khi CHƯA có key Gemini (voice_id rỗng -> UI disable) —
# user vẫn biết nhóm giọng Gemini TỒN TẠI và cần gì để mở.
GEMINI_LOCKED_LABEL = ("🌟 Giọng Gemini: dán key Gemini trong 'Cài đặt AI' "
                       "để mở khóa")

# Dòng thông báo khi CHƯA có key ElevenLabs (voice_id rỗng -> UI disable) —
# user vẫn biết nhóm giọng cao cấp TỒN TẠI và cần gì để mở.
ELEVEN_LOCKED_LABEL = ("🎧 ElevenLabs: dán key trong Cài đặt AI để mở khóa "
                       "(giọng Adam...)")


def _lang_group_label(key: str) -> str:
    flag, name = _LOCALE_VI.get(key) or _LOCALE_VI.get(key.split("-")[0]) \
        or ("🌍", key)
    return f"{flag} {name}"


def _recap_voice_label(v: dict) -> str:
    """Nhãn giọng cho danh sách recap: '   ⭐ Andrew (Nam)' /
    '   ⭐ Ava (Nữ, đa ngữ)' — user thấy ngay tên + giới tính. Giọng
    KHÔNG hot (chỉ hiện khi 'Hiện tất cả giọng') -> không gắn ⭐."""
    short = v.get("ShortName", "")
    parts = short.split("-", 2)
    name = parts[2] if len(parts) == 3 else short
    if name.endswith("Neural"):
        name = name[:-len("Neural")]
    multi = "Multilingual" in name
    if multi:
        name = name.replace("Multilingual", "")
    g = {"female": "Nữ", "male": "Nam"}.get((v.get("Gender") or "").lower(),
                                            "?")
    star = "⭐ " if short in _HOT_VOICES else ""
    return (f"   {star}{name} ({g}, đa ngữ)" if multi
            else f"   {star}{name} ({g})")


def list_recap_voices(all: bool = False) -> list[tuple[str, str]]:  # noqa: A002
    """Giọng cho GIỌNG KỂ Reup thuyết minh, NHÓM THEO NGÔN NGỮ với nhãn
    tiếng Việt + cờ (sửa lỗi user 'danh sách mù mờ không biết tiếng gì').
    Trả [(nhãn, voice_id)]; dòng có voice_id RỖNG là NHÃN NHÓM / thông báo
    — UI phải disable (không cho chọn).

    all=False (mặc định): chỉ giọng ĐỀ XUẤT + ⭐ hot (danh sách gọn).
    all=True: TOÀN BỘ kho ~500 giọng edge-tts (_fetch_all_voices, cache 7
    ngày) — nhóm ngôn ngữ như cũ, giọng hot vẫn gắn ⭐; offline/mạng lỗi
    -> tự rơi về danh sách gọn (không vỡ).

    Cấu trúc: nhóm 🌟 Gemini (có key -> giọng chọn được; KHÔNG key -> 1
    dòng disabled chỉ cách mở khóa) -> nhóm 🔥 ĐỀ XUẤT (curate tay, có MÔ
    TẢ từng giọng — mượt & hot nhất, luôn có kể cả offline) -> nhóm 🌐 đa
    ngôn ngữ (Multilingual, đọc mọi thứ tiếng) -> từng ngôn ngữ (🇻🇳 Tiếng
    Việt, 🇺🇸 Tiếng Anh (Mỹ)...), mỗi giọng ghi 'Tên (Nam/Nữ)'. Offline/
    lỗi mạng -> dựng từ danh sách tĩnh VOICES (gender lấy từ nhãn cũ
    'Nữ —/Nam —')."""
    out: list[tuple[str, str]] = []
    if _gemini_available():
        out.append(("🌟 Gemini — đa ngôn ngữ (CẦN key Gemini)", ""))
        out += [(f"   🌟 {n} (Gemini)", f"gemini:{n}")
                for n in _GEMINI_PREBUILT]
    else:
        out.append((GEMINI_LOCKED_LABEL, ""))
    # 0) nhóm 🔥 ĐỀ XUẤT — curate tay kèm mô tả, KHÔNG cần mạng
    out.append(("🔥 ĐỀ XUẤT — mượt & hot nhất", ""))
    out += [(f"   🔥 {desc}", vid) for vid, desc in _RECOMMENDED_VOICES]
    # 0b) nhóm 🎧 ElevenLabs — chất lượng cao nhất (CẦN key). Có key -> liệt kê
    # giọng (Adam đầu + premade + account voices); KHÔNG key -> 1 dòng disabled
    # chỉ cách mở khóa. ElevenLabs KHÔNG có rate/pitch (tooltip UI đã ghi).
    if _eleven_available():
        out.append(("🎧 ElevenLabs — chất lượng cao nhất (CẦN key)", ""))
        out += [(f"   {lbl}", vid) for lbl, vid in _eleven_voices()]
    else:
        out.append((ELEVEN_LOCKED_LABEL, ""))
    allv = _fetch_all_voices()
    if all and allv:                    # kho ĐẦY ĐỦ (~500 giọng)
        pool = list(allv)
    else:                               # danh sách gọn: chỉ giọng ⭐ hot
        pool = [v for v in (allv or []) if v.get("ShortName") in _HOT_VOICES]
    if not pool:                        # offline -> giọng tĩnh đã kiểm chứng
        seen: set = set()
        for _lang, vs in VOICES.items():
            for lbl, vid in vs:
                if vid not in seen:
                    seen.add(vid)
                    pool.append({
                        "ShortName": vid,
                        "Gender": "Female" if lbl.startswith("Nữ") else "Male",
                        "Locale": "-".join(vid.split("-")[:2])})
    # 1) nhóm ĐA NGÔN NGỮ (đọc được mọi thứ tiếng — gợi ý mạnh nhất)
    multi_ids = {v["ShortName"] for v in pool
                 if "multilingual" in v["ShortName"].lower()}
    multi = sorted((v for v in pool if v["ShortName"] in multi_ids),
                   key=lambda v: (v["ShortName"] not in _HOT_VOICES,
                                  v["ShortName"]))
    if multi:
        out.append(("🌐 Đa ngôn ngữ — đọc được MỌI thứ tiếng", ""))
        out += [(_recap_voice_label(v), v["ShortName"]) for v in multi]
    # 2) nhóm theo NGÔN NGỮ với nhãn Việt + cờ (giọng ⭐ hot lên đầu nhóm)
    groups: dict[str, list[dict]] = {}
    for v in pool:
        if v["ShortName"] in multi_ids:
            continue
        loc = v.get("Locale") or "-".join(v["ShortName"].split("-")[:2])
        key = loc if loc in _LOCALE_VI else loc.split("-")[0]
        groups.setdefault(key, []).append(v)
    ordered = ([k for k in _GROUP_ORDER if k in groups]
               + sorted(k for k in groups if k not in _GROUP_ORDER))
    for k in ordered:
        out.append((_lang_group_label(k), ""))
        out += [(_recap_voice_label(v), v["ShortName"])
                for v in sorted(groups[k],
                                key=lambda v: (v["ShortName"] not in
                                               _HOT_VOICES,
                                               v["ShortName"]))]
    return out


# ------------------------------------------------------------------
# Gemini TTS (REST thuần — urllib stdlib, không thêm dependency)
# ------------------------------------------------------------------
# Bóc "retryDelay": "30s" trong body lỗi 429 của Gemini (llm.parse_retry_wait
# không bắt dạng này — nó bắt "in 30s"/"retry-after").
_GEMINI_RETRY_DELAY = re.compile(r'retryDelay"?\s*[:=]\s*"?(\d+(?:\.\d+)?)')


def _gemini_tts_once(text: str, voice_name: str, key: str,
                     out_path: str) -> None:
    """1 lần gọi Gemini TTS -> ghi WAV (PCM 16-bit mono, rate parse từ
    mimeType, thường 24000). Ném RuntimeError kèm mã HTTP/body nếu lỗi."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{_GEMINI_TTS_MODEL}:generateContent")
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {
                "prebuiltVoiceConfig": {"voiceName": voice_name}}},
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:800]
        except OSError:
            detail = ""
        # mã HTTP nằm trong message -> is_rate_limit_error/is_auth_error bắt được
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Gemini TTS lỗi mạng: {e}") from None
    try:
        part = (data.get("candidates") or [{}])[0].get("content", {}) \
            .get("parts", [{}])[0]
    except (AttributeError, IndexError, TypeError):
        part = {}
    inline = (part.get("inlineData") or part.get("inline_data") or {}) \
        if isinstance(part, dict) else {}
    b64 = inline.get("data", "")
    if not b64:
        raise RuntimeError(f"Gemini TTS không trả audio: {str(data)[:300]}")
    pcm = base64.b64decode(b64)
    if len(pcm) < 2000:                 # < ~0.04s @24k -> coi như hỏng
        raise RuntimeError("Gemini TTS trả audio quá ngắn")
    mime = inline.get("mimeType") or inline.get("mime_type") or ""
    m = re.search(r"rate=(\d+)", mime)
    rate = int(m.group(1)) if m else 24000
    with wave.open(out_path, "wb") as w:   # header WAV chuẩn -> winsound/ffmpeg OK
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def _gemini_tts(text: str, voice: str, out_path: str | Path,
                retries: int = 2, max_wait: float = 30.0) -> bool:
    """Synth 1 đoạn text bằng Gemini TTS -> file WAV. Trả True nếu OK.

    Key đọc y hệt llm.py (settings.llm_keys_for("gemini")) + XOAY VÒNG nhiều
    key qua sổ trạng thái của llm (mark_limited/mark_invalid dùng chung với
    phần dịch). 429 -> thử key kế; hết key thì đợi theo retryDelay của server
    (trần `max_wait`) rồi thử lại, tối đa `retries` vòng. Không key/lỗi hết
    -> False (caller tự fallback edge-tts)."""
    from app.ai import llm
    name = voice.split(":", 1)[1] if voice.startswith("gemini:") else voice
    text = (text or "").strip()
    if not text or not name:
        return False
    out_path = str(out_path)
    # TTS CACHE (tiết kiệm hạn mức): cùng giọng+text đã synth trước đó ->
    # dùng lại, không gọi API (cache dùng chung với ElevenLabs, xem tts_cache_*)
    cached = tts_cache_get(f"gemini:{name}", _GEMINI_TTS_MODEL, text)
    if cached:
        try:
            shutil.copyfile(cached, out_path)
            return True
        except OSError:
            pass
    wait = 5.0                          # chờ mặc định khi 429 không kèm delay
    for attempt in range(retries + 1):
        keys = llm.pick_keys("gemini")
        if not keys:
            return False
        rate_limited = False
        for key in keys:
            llm.mark_used("gemini", key)
            try:
                _gemini_tts_once(text, name, key, out_path)
                llm.mark_ok("gemini", key)
                tts_cache_put(f"gemini:{name}", _GEMINI_TTS_MODEL, text,
                              out_path)
                return True
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if llm.is_rate_limit_error(msg):
                    rate_limited = True
                    llm.mark_limited("gemini", key, msg)
                    md = _GEMINI_RETRY_DELAY.search(msg)
                    w = (float(md.group(1)) if md
                         else llm.parse_retry_wait(msg))
                    if w:
                        wait = min(float(w), max_wait)
                    continue            # 429 -> thử key kế tiếp ngay
                if llm.is_auth_error(msg):
                    llm.mark_invalid("gemini", key)
                    continue            # key sai -> bỏ, thử key khác
                # lỗi khác (mạng/parse) -> nghỉ ngắn rồi thử vòng sau
        if attempt < retries:
            time.sleep(min(wait if rate_limited else 2.0, max_wait))
    return False


def _edge_fallback_voice(lang: str) -> str:
    """Giọng edge-tts DỰ PHÒNG khi Gemini hết hạn mức: giọng ⭐ hot đầu tiên
    của ngôn ngữ (list_voices_for đã xếp hot lên đầu), bỏ qua nhóm gemini."""
    for _lbl, vid in list_voices_for(lang):
        if vid and not vid.startswith("gemini:") and not vid.startswith("el:"):
            return vid
    return default_voice(lang) or "en-US-JennyNeural"


def _recap_backup_voice(lang: str, primary: str) -> str:
    """Giọng edge-tts DỰ PHÒNG cho recap khi giọng CHÍNH fail hết retry:
    giọng ⭐ hot kế tiếp CÙNG ngôn ngữ, khác giọng chính (server MS hay lỗi
    NoAudioReceived theo GIỌNG — đổi giọng thường cứu được part).
    '' nếu không còn giọng nào khác."""
    for _lbl, vid in list_voices_for(lang):
        if (vid and not vid.startswith("gemini:")
                and not vid.startswith("el:") and vid != primary):
            return vid
    return ""


def _shortest_nonempty_index(texts: list[str]) -> int:
    """Chỉ số cụm KHÔNG rỗng NGẮN NHẤT (ít ký tự nhất) — dùng cho PRE-FLIGHT
    giọng cao cấp: thử cụm ngắn nhất trước để tốn ít quota/token nhất mà vẫn
    biết key còn sống hay đã hết hạn mức. -1 nếu mọi cụm rỗng."""
    best, best_len = -1, None
    for i, t in enumerate(texts):
        s = (t or "").strip()
        if not s:
            continue
        if best_len is None or len(s) < best_len:
            best, best_len = i, len(s)
    return best


def _synth_all_gemini(texts: list[str], voice: str, paths: list[str],
                      lang: str,
                      on_done: Optional[Callable[[int], None]] = None,
                      on_msg: Optional[Callable[[str], None]] = None,
                      edge_rate: str = "+0%",
                      gemini_prefix: str = "",
                      ) -> list[bool]:
    """Synth TUẦN TỰ từng cụm qua Gemini TTS (hạn mức free thấp — KHÔNG chạy
    song song; _gemini_tts tự retry 429 theo retryDelay).

    GIỌNG NHẤT QUÁN TOÀN CLIP (all-or-nothing) — sửa lỗi 'mỗi part một giọng':
    - PRE-FLIGHT: thử cụm NGẮN NHẤT trước. Lỗi (hết hạn mức/key hỏng) -> CHUYỂN
      CẢ TRACK sang edge-tts NGAY TỪ ĐẦU (đỡ phí quota + đảm bảo mọi part CÙNG
      1 giọng). Không thì cụm đó đã có audio, tái dùng.
    - Nếu BẤT KỲ cụm nào (kể cả part thứ 3-4 khi quota cạn GIỮA CHỪNG) synth
      lỗi -> HỦY TOÀN BỘ track Gemini, re-synth TẤT CẢ bằng edge-tts giọng dự
      phòng. KHÔNG BAO GIỜ trộn 2 nguồn trong 1 clip (trước đây chỉ bắt lỗi ở
      2 cụm ĐẦU -> quota cạn ở part sau vẫn lọt -> clip nhiều giọng).
    Ghi WAV vào paths[i] (tên .mp3 cũng được — ffmpeg/ffprobe sniff nội dung).
    gemini_prefix: CHỈ DẪN giọng điệu prepend vào text khi gọi Gemini (recap
    kể chuyện) — KHÔNG áp cho đường fallback edge-tts (edge sẽ ĐỌC to chỉ
    dẫn thành lời); edge_rate: rate cho đường fallback edge-tts."""
    def _fallback_edge(reason: str) -> list[bool]:
        # Hết hạn mức/lỗi -> đổi CẢ track sang edge-tts (text GỐC không prefix
        # — edge đọc to mọi chữ trong text). Re-synth TẤT CẢ part -> đồng nhất.
        fb = _edge_fallback_voice(lang)
        if on_msg:
            on_msg(f"Gemini {reason} -> synth LẠI toàn bộ bằng giọng dự "
                   f"phòng ({fb}) cho đồng nhất...")
        return asyncio.run(_synth_all(texts, fb, paths, on_done=on_done,
                                      rate=edge_rate))

    ok = [False] * len(texts)
    # ---- PRE-FLIGHT: thử cụm NGẮN NHẤT trước; lỗi -> edge ngay từ đầu ----
    pf = _shortest_nonempty_index(texts)
    if pf < 0:                              # mọi cụm rỗng -> không có gì để đọc
        for i in range(len(texts)):
            if on_done:
                on_done(i)
        return ok
    if not _gemini_tts(gemini_prefix + texts[pf].strip(), voice, paths[pf]):
        return _fallback_edge("hết hạn mức (pre-flight)")
    ok[pf] = True
    time.sleep(0.3)
    # ---- Synth các cụm còn lại; BẤT KỲ cụm nào lỗi -> hủy cả track ----
    for i, t in enumerate(texts):
        txt = (t or "").strip()
        if not txt or i == pf:              # cụm rỗng / đã làm ở pre-flight
            if on_done:
                on_done(i)
            continue
        if not _gemini_tts(gemini_prefix + txt, voice, paths[i]):
            # Quota cạn GIỮA CHỪNG -> re-synth TẤT CẢ bằng edge (đồng nhất)
            return _fallback_edge("hết hạn mức giữa chừng")
        ok[i] = True
        if on_done:
            on_done(i)
        time.sleep(0.3)                     # nghỉ nhẹ — tôn trọng hạn mức
    return ok


# ------------------------------------------------------------------
# ElevenLabs TTS (REST thuần — urllib stdlib, không thêm dependency)
# ------------------------------------------------------------------
_ELEVEN_API = "https://api.elevenlabs.io/v1"


class ElevenError(RuntimeError):
    """Lỗi ElevenLabs ĐÃ PHÂN LOẠI theo detail.status trong body JSON của
    API ({"detail": {"status": "...", "message": "..."}}). str(e) = NGUYÊN
    VĂN detail.message (user thấy đúng lý do thật, không đoán mò).

    kind:
      quota           — hết credit THẬT (quota_exceeded) -> mark_limited
      invalid_key     — key sai/bị chặn (invalid_api_key/401/
                        detected_unusual_activity) -> mark_invalid
      model_denied    — GÓI không có quyền model (model_access_denied /
                        model_not_found — free/starter chưa chắc có
                        eleven_v3!) -> KHÔNG phải hết credit, lùi v2
      voice_not_found — voice id sai/không có trên account -> báo rõ
      rate_limit      — 429 tạm thời (too_many_concurrent_requests) ->
                        đợi ngắn retry, KHÔNG mark_limited vĩnh viễn
      network / other — lỗi mạng / lỗi khác
    """

    def __init__(self, kind: str, message: str, http: int = 0):
        super().__init__(message)
        self.kind = kind
        self.http = int(http or 0)


def _classify_eleven_http(code: int, body: str) -> ElevenError:
    """Phân loại HTTPError của ElevenLabs từ (mã HTTP, body JSON) ->
    ElevenError đúng kind. QUAN TRỌNG: quota_exceeded của ElevenLabs trả về
    HTTP 401 — phải đọc detail.status TRƯỚC, mã HTTP chỉ là fallback
    (trước đây gộp mọi lỗi làm 'hết hạn mức' -> user 'còn credit mà báo
    hết'). Hàm thuần — unit test được."""
    status, message = "", ""
    try:
        det = json.loads(body or "{}").get("detail")
        if isinstance(det, dict):
            status = str(det.get("status") or "").strip().lower()
            message = str(det.get("message") or "").strip()
        elif isinstance(det, str):
            message = det.strip()
    except (ValueError, AttributeError, TypeError):
        pass
    if not message:
        message = (body or "").strip()[:300] or f"HTTP {code}"
    low = f"{status} {message}".lower()
    if status == "quota_exceeded" or "quota_exceeded" in low:
        kind = "quota"
    elif (status in ("model_access_denied", "model_not_found")
          or "model_access_denied" in low or "model_not_found" in low
          or (code in (400, 422) and "model" in low)):
        kind = "model_denied"
    elif status == "voice_not_found" or "voice_not_found" in low:
        kind = "voice_not_found"
    elif (code == 429 or status in ("too_many_concurrent_requests",
                                    "system_busy")
          or "too many" in low or "too_many" in low):
        kind = "rate_limit"
    elif (status in ("invalid_api_key", "needs_authorization",
                     "detected_unusual_activity")
          or code in (401, 403) or "invalid api key" in low
          or "unauthorized" in low):
        kind = "invalid_key"
    else:
        kind = "other"
    return ElevenError(kind, message, http=code)


def _eleven_tts_once(text: str, voice_id: str, model: str, key: str,
                     out_path: str) -> None:
    """1 lần gọi ElevenLabs TTS -> ghi BYTES mp3 thẳng ra out_path. Ném
    ElevenError ĐÃ PHÂN LOẠI (kind + detail.message nguyên văn) nếu lỗi.
    API trả mp3 nhị phân trực tiếp (KHÔNG JSON base64)."""
    url = (f"{_ELEVEN_API}/text-to-speech/{voice_id}"
           "?output_format=mp3_44100_128")
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75,
                           "style": 0.0, "use_speaker_boost": True},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            audio = r.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:800]
        except OSError:
            detail = ""
        raise _classify_eleven_http(e.code, detail) from None
    except urllib.error.URLError as e:
        raise ElevenError("network", f"ElevenLabs lỗi mạng: {e}") from None
    if not audio or len(audio) < 500:      # mp3 rỗng/hỏng
        raise ElevenError("other", "ElevenLabs trả audio rỗng/quá ngắn")
    with open(out_path, "wb") as f:
        f.write(audio)


# ---- KIỂM TRA CREDIT (GET /v1/user/subscription) + cache 5 phút ----
_ELEVEN_QUOTA_CACHE: dict[str, tuple[float, dict]] = {}   # key -> (ts, quota)
_ELEVEN_QUOTA_TTL = 300.0                                 # 5 phút


def _eleven_quota_fetch(key: str, timeout: float = 20.0) -> dict:
    """Gọi TƯƠI GET /user/subscription -> dict quota. Ném ElevenError
    (kind invalid_key/network/...) nếu lỗi — caller UI hiện đúng lý do."""
    req = urllib.request.Request(f"{_ELEVEN_API}/user/subscription",
                                 headers={"xi-api-key": key}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:800]
        except OSError:
            detail = ""
        raise _classify_eleven_http(e.code, detail) from None
    except Exception as e:  # noqa: BLE001 — mạng/parse
        raise ElevenError("network", f"lỗi mạng: {e}") from None
    try:
        used = int(data.get("character_count") or 0)
        limit = int(data.get("character_limit") or 0)
    except (TypeError, ValueError):
        raise ElevenError("other", "subscription trả dữ liệu lạ") from None
    q = {"used": used, "limit": limit, "remain": max(0, limit - used),
         "tier": str(data.get("tier") or ""),
         "reset_ts": float(data.get("next_character_count_reset_unix")
                           or 0)}
    _ELEVEN_QUOTA_CACHE[key] = (time.time(), q)
    return q


def eleven_quota(key: str, use_cache: bool = True) -> Optional[dict]:
    """Credit ElevenLabs của 1 key -> {"used","limit","remain","tier",
    "reset_ts"}; LỖI (key sai/mạng) -> None. use_cache: dùng cache RAM 5
    phút (dialog ⚙/pre-flight gọi lặp không tốn request)."""
    if use_cache:
        hit = _ELEVEN_QUOTA_CACHE.get(key)
        if hit and time.time() - hit[0] < _ELEVEN_QUOTA_TTL:
            return dict(hit[1])
    try:
        return dict(_eleven_quota_fetch(key))
    except ElevenError:
        return None


def eleven_credit_remain(keys: Optional[list] = None,
                         use_cache: bool = True) -> Optional[int]:
    """TỔNG ký tự CÒN LẠI trên tất cả key (bỏ key lỗi). None nếu KHÔNG key
    nào trả được quota (mạng đứt/mọi key sai) — caller tự quyết pre-flight
    kiểu cũ."""
    keys = _eleven_keys() if keys is None else keys
    total, got = 0, False
    for k in keys:
        q = eleven_quota(k, use_cache=use_cache)
        if q is not None:
            got = True
            total += max(0, int(q.get("remain") or 0))
    return total if got else None


def eleven_key_status_line(key: str) -> str:
    """Dòng trạng thái tiếng Việt cho nút 'Kiểm tra' (Cài đặt AI) — gọi
    quota TƯƠI. Ví dụ: '🟢 Key …abc123: còn 8.230/10.000 ký tự (free,
    reset 15/07)'; key lỗi -> 'SAI KEY'/lý do nguyên văn."""
    masked = f"…{key[-6:]}" if len(key) > 6 else key
    try:
        q = _eleven_quota_fetch(key)
    except ElevenError as e:
        if e.kind == "invalid_key":
            return f"🔴 Key {masked}: SAI KEY / bị chặn — {e}"
        if e.kind == "network":
            return f"⚠️ Key {masked}: lỗi mạng — {e}"
        return f"⚠️ Key {masked}: {e.kind} — {e}"
    reset = ""
    if q.get("reset_ts"):
        import datetime
        try:
            reset = ", reset " + datetime.datetime.fromtimestamp(
                q["reset_ts"]).strftime("%d/%m")
        except (OverflowError, OSError, ValueError):
            reset = ""
    tier = q.get("tier") or "?"
    remain = f"{q['remain']:,}".replace(",", ".")
    limit = f"{q['limit']:,}".replace(",", ".")
    icon = "🟢" if q["remain"] > 0 else "⛔"
    return f"{icon} Key {masked}: còn {remain}/{limit} ký tự ({tier}{reset})"


# ---- TTS CACHE (tiết kiệm credit): sha1(voice|model|text) -> mp3 ----
# Xuất lại cùng clip / chỉnh mẫu / bấm nghe thử nhiều lần -> KHÔNG tốn
# credit lần 2. Chỉ giọng trả phí (el:/gemini:) đi qua cache — edge free.
_TTS_CACHE_DIR = DATA_DIR / "_cache" / "tts"
_TTS_CACHE_MAX_BYTES = 300 * 1024 * 1024      # 300MB — vượt thì xóa cũ nhất


def _tts_cache_path(voice_id: str, model: str, text: str) -> Path:
    h = hashlib.sha1(
        f"{voice_id}|{model}|{text}".encode("utf-8")).hexdigest()
    return _TTS_CACHE_DIR / f"{h}.mp3"


def tts_cache_get(voice_id: str, model: str, text: str,
                  touch: bool = True) -> Optional[str]:
    """Đường dẫn file cache nếu CÓ (và hợp lệ >500B); None nếu chưa.
    touch=True: cập nhật mtime (LRU — file hay dùng không bị dọn)."""
    p = _tts_cache_path(voice_id, model, text)
    try:
        if p.is_file() and p.stat().st_size > 500:
            if touch:
                os.utime(p, None)
            return str(p)
    except OSError:
        pass
    return None


def _tts_cache_evict(max_bytes: int = _TTS_CACHE_MAX_BYTES) -> None:
    """Tổng cache vượt max_bytes -> xóa file CŨ NHẤT (mtime) tới khi lọt."""
    try:
        files = []
        for f in _TTS_CACHE_DIR.iterdir():
            try:
                st = f.stat()
                if f.is_file():
                    files.append((st.st_mtime, st.st_size, f))
            except OSError:
                continue
    except OSError:
        return
    total = sum(s for _, s, _ in files)
    if total <= max_bytes:
        return
    for _, size, f in sorted(files):          # cũ nhất trước
        try:
            f.unlink()
            total -= size
        except OSError:
            pass
        if total <= max_bytes:
            break


def tts_cache_put(voice_id: str, model: str, text: str,
                  src_path: str) -> None:
    """Lưu audio vừa synth vào cache (best-effort — lỗi đĩa thì bỏ qua),
    rồi dọn bớt nếu vượt 300MB."""
    p = _tts_cache_path(voice_id, model, text)
    try:
        _TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(p) + ".tmp"
        shutil.copyfile(src_path, tmp)
        os.replace(tmp, p)
    except OSError:
        return
    _tts_cache_evict()


# Model bị API TỪ CHỐI trong phiên chạy (model_access_denied — gói không có
# quyền, vd free tier chưa mở eleven_v3) -> các request sau dùng thẳng v2,
# khỏi tốn 1 lượt lỗi mỗi part. KHÔNG lưu đĩa: user nâng gói thì restart là
# thử lại v3.
_ELEVEN_DENIED_MODELS: set = set()


def _eleven_effective_model(model: str = "") -> str:
    """Model sẽ THẬT SỰ gửi đi: model yêu cầu, trừ khi đã biết bị gói từ
    chối trong phiên -> lùi _ELEVEN_MODEL_DEFAULT."""
    m = (model or _eleven_model()).strip()
    if m in _ELEVEN_DENIED_MODELS and m != _ELEVEN_MODEL_DEFAULT:
        return _ELEVEN_MODEL_DEFAULT
    return m


def _eleven_tts(text: str, voice: str, out_path: str | Path,
                model: str = "", retries: int = 1,
                on_msg: Optional[Callable[[str], None]] = None) -> bool:
    """Synth 1 đoạn text bằng ElevenLabs TTS -> file mp3. Trả True nếu OK.

    voice: "el:{voice_id}" (hoặc voice_id trần). Key XOAY VÒNG qua sổ trạng
    thái của llm (provider="elevenlabs") — mỗi REQUEST thử lần lượt key sống
    (pick_keys); voice premade GIỐNG NHAU giữa các account nên đổi key giữa
    track vẫn CÙNG GIỌNG. Phân loại lỗi theo ElevenError.kind:
      quota           -> mark_limited (kèm reset time nếu biết) + key kế NGAY
      invalid_key     -> mark_invalid + key kế
      model_denied    -> LÙI multilingual_v2 thử lại CÙNG key (gói không có
                         quyền model — KHÔNG phải hết credit, KHÔNG rơi edge)
      voice_not_found -> báo rõ, thử key kế (voice account khác nhau)
      rate_limit      -> đợi ngắn (retry-after, trần 15s) retry CÙNG key,
                         KHÔNG mark_limited vĩnh viễn
    on_msg: nhận message lỗi NGUYÊN VĂN (detail.message) cho progress/log.
    CACHE: sha1(voice|model|text) có sẵn -> dùng lại, KHÔNG gọi API (xuất
    lại clip/nghe thử lặp không tốn credit). Hết key/lỗi hết -> False
    (caller tự fallback edge-tts)."""
    from app.ai import llm

    def note(m: str) -> None:
        if on_msg:
            on_msg(m)

    vid = voice.split(":", 1)[1] if voice.startswith("el:") else voice
    text = (text or "").strip()
    if not text or not vid:
        return False
    out_path = str(out_path)
    model = _eleven_effective_model(model)
    cached = tts_cache_get(vid, model, text)
    if cached:
        try:
            shutil.copyfile(cached, out_path)
            return True
        except OSError:
            pass                          # cache hỏng -> synth bình thường
    for _attempt in range(retries + 1):
        keys = llm.pick_keys("elevenlabs", _eleven_keys())
        if not keys:
            return False
        for key in keys:
            cur_model = _eleven_effective_model(model)
            tries = 3                     # mỗi key: lùi model / retry 429
            while tries > 0:
                tries -= 1
                llm.mark_used("elevenlabs", key)
                try:
                    _eleven_tts_once(text, vid, cur_model, key, out_path)
                    llm.mark_ok("elevenlabs", key)
                    tts_cache_put(vid, cur_model, text, out_path)
                    return True
                except ElevenError as e:
                    if (e.kind == "model_denied"
                            and cur_model != _ELEVEN_MODEL_DEFAULT):
                        # GÓI không có quyền model (vd free chưa mở v3) —
                        # KHÔNG phải hết credit -> lùi v2, TIẾP TỤC ElevenLabs
                        _ELEVEN_DENIED_MODELS.add(cur_model)
                        note(f"ElevenLabs: gói chưa có quyền model "
                             f"{cur_model} (KHÔNG phải hết credit) -> dùng "
                             f"{_ELEVEN_MODEL_DEFAULT}. Chi tiết: {e}")
                        cur_model = _ELEVEN_MODEL_DEFAULT
                        c2 = tts_cache_get(vid, cur_model, text)
                        if c2:
                            try:
                                shutil.copyfile(c2, out_path)
                                return True
                            except OSError:
                                pass
                        continue          # thử lại CÙNG key với v2
                    if e.kind == "quota":
                        # HẾT CREDIT THẬT key này -> nghỉ tới kỳ reset (nếu
                        # biết từ quota cache) rồi chuyển key kế NGAY —
                        # track đang chạy TIẾP TỤC, không rơi edge.
                        msg = str(e)
                        hit = _ELEVEN_QUOTA_CACHE.get(key)
                        if hit and hit[1].get("reset_ts"):
                            w = hit[1]["reset_ts"] - time.time()
                            if w > 0:
                                msg += f" retry-after: {int(w)}"
                        llm.mark_limited("elevenlabs", key, msg)
                        note(f"ElevenLabs key …{key[-4:]} HẾT CREDIT: {e} "
                             "-> chuyển key kế")
                        break             # key kế
                    if e.kind == "invalid_key":
                        llm.mark_invalid("elevenlabs", key)
                        note(f"ElevenLabs key …{key[-4:]} SAI/bị chặn: {e} "
                             "-> thử key kế")
                        break             # key kế
                    if e.kind == "voice_not_found":
                        note(f"ElevenLabs: KHÔNG có giọng '{vid}' trên "
                             f"account key …{key[-4:]}: {e} — kiểm tra lại "
                             "voice id / chọn giọng khác")
                        break             # account khác có thể có -> key kế
                    if e.kind == "rate_limit":
                        w = llm.parse_retry_wait(str(e)) or 2.0
                        note(f"ElevenLabs bận (429 tạm thời) — đợi "
                             f"{w:.0f}s rồi thử lại: {e}")
                        time.sleep(min(float(w), 15.0))
                        continue          # retry CÙNG key, KHÔNG mark
                    note(f"ElevenLabs lỗi ({e.kind}): {e}")
                    break                 # network/other -> key kế
                except Exception as e:  # noqa: BLE001 — lỗi lạ (đĩa/parse)
                    note(f"ElevenLabs lỗi không phân loại: {e}")
                    break
        if _attempt < retries:
            time.sleep(1.5)
    return False


def _synth_all_eleven(texts: list[str], voice: str, paths: list[str],
                      lang: str,
                      on_done: Optional[Callable[[int], None]] = None,
                      on_msg: Optional[Callable[[str], None]] = None,
                      edge_rate: str = "",
                      model: str = "",
                      edge_texts: Optional[list[str]] = None,
                      ) -> list[bool]:
    """Synth TUẦN TỰ từng cụm qua ElevenLabs TTS (KHUÔN _synth_all_gemini).
    _eleven_tts tự XOAY KEY từng request (key hết credit -> key kế NGAY,
    voice premade giống nhau giữa account nên CÙNG GIỌNG, track chạy tiếp
    không gián đoạn) + tự lùi v2 khi gói không có quyền model. CHỈ khi
    TẤT CẢ key đều hết/chết (part nào đó False) -> all-or-nothing fallback
    edge, kèm LÝ DO THẬT (message cuối từ _eleven_tts) trong progress.
    ElevenLabs KHÔNG có rate/pitch -> edge_rate CHỈ áp cho đường fallback.
    model: model_id ElevenLabs (eleven_v3 khi bật audio tag cảm xúc; gói
    không có quyền -> _eleven_tts tự lùi v2, KHÔNG rơi edge). edge_texts:
    bản text ĐÃ STRIP audio tag dùng cho đường FALLBACK edge-tts (edge
    KHÔNG hiểu tag -> đọc to "[excited]" nếu dùng texts có tag). None ->
    dùng chính `texts`.

    PRE-FLIGHT bằng CREDIT CHECK (đỡ phí credit nửa chừng):
    - TÍNH TỔNG KÝ TỰ track sắp gửi (bỏ cụm đã có CACHE) -> so tổng remain
      của các key (eleven_quota, cache 5 phút). Không đủ -> quyết fallback
      edge NGAY TỪ ĐẦU (đồng nhất giọng + không phí credit).
    - API quota lỗi (mạng/không đọc được) -> giữ pre-flight SYNTH cụm ngắn
      nhất như cũ.
    GIỌNG NHẤT QUÁN TOÀN CLIP (all-or-nothing): BẤT KỲ cụm nào lỗi (mọi key
    chết giữa chừng) -> HỦY cả track ElevenLabs, re-synth TẤT CẢ bằng edge
    (KHÔNG trộn 2 nguồn)."""
    fb_texts = edge_texts if edge_texts is not None else texts
    last_err = {"msg": ""}                 # lý do lỗi CUỐI (hiện nguyên văn)

    def _note(m: str) -> None:
        last_err["msg"] = m
        if on_msg:
            on_msg(m)

    def _fallback_edge(reason: str) -> list[bool]:
        fb = _edge_fallback_voice(lang)
        if on_msg:
            on_msg(f"ElevenLabs {reason} -> synth LẠI toàn bộ bằng giọng dự "
                   f"phòng ({fb}) cho đồng nhất...")
        # edge-tts KHÔNG hiểu audio tag v3 -> dùng bản ĐÃ STRIP (fb_texts)
        return asyncio.run(_synth_all(fb_texts, fb, paths, on_done=on_done,
                                      rate=edge_rate or "+0%"))

    ok = [False] * len(texts)
    pf = _shortest_nonempty_index(texts)
    if pf < 0:
        for i in range(len(texts)):
            if on_done:
                on_done(i)
        return ok
    # ---- PRE-FLIGHT: so TỔNG KÝ TỰ cần gửi với credit còn lại ----
    vid = voice.split(":", 1)[1] if voice.startswith("el:") else voice
    model_eff = _eleven_effective_model(model)
    need = sum(len(t.strip()) for t in texts
               if (t or "").strip()
               and not tts_cache_get(vid, model_eff, t.strip(), touch=False))
    if need > 0:
        remain = eleven_credit_remain()
        if remain is not None:
            if need > remain:
                return _fallback_edge(
                    f"KHÔNG đủ credit cho cả track (cần ~{need} ký tự, các "
                    f"key còn tổng ~{remain})")
            if on_msg:
                on_msg(f"🎧 ElevenLabs: còn ~{remain} ký tự, track cần "
                       f"~{need} -> đủ, bắt đầu thu giọng...")
        else:
            # quota API lỗi -> pre-flight SYNTH cụm ngắn nhất như cũ
            if not _eleven_tts(texts[pf].strip(), voice, paths[pf],
                               model=model, on_msg=_note):
                why = last_err["msg"] or "lỗi pre-flight (mọi key đều lỗi)"
                return _fallback_edge(f"lỗi ngay từ đầu — {why}")
            ok[pf] = True
    # ---- synth từng cụm; BẤT KỲ cụm nào lỗi (mọi key chết) -> hủy track ----
    for i, t in enumerate(texts):
        txt = (t or "").strip()
        if not txt or ok[i]:               # cụm rỗng / đã làm ở pre-flight
            if on_done:
                on_done(i)
            continue
        if not _eleven_tts(txt, voice, paths[i], model=model, on_msg=_note):
            why = last_err["msg"] or "mọi key đều hết credit/chết"
            return _fallback_edge(f"lỗi giữa chừng — {why}")
        ok[i] = True
        if on_done:
            on_done(i)
    return ok


# ------------------------------------------------------------------
# Đọc thử 1 câu ngắn (nghe demo giọng trong UI)
# ------------------------------------------------------------------
_DEMO_TEXTS = {
    "vi": "Xin chào, đây là giọng đọc thử của kênh.",
    "en": "Hello, this is a voice preview.",
    "id": "Halo, ini adalah contoh suara.",
    "th": "สวัสดีค่ะ นี่คือเสียงตัวอย่าง",
    "ko": "안녕하세요, 이것은 음성 미리 듣기입니다.",
    "ja": "こんにちは、これは音声のサンプルです。",
    "zh": "你好，这是语音试听。",
    "es": "Hola, esta es una prueba de voz.",
    "pt": "Olá, esta é uma amostra de voz.",
    "fr": "Bonjour, ceci est un aperçu de la voix.",
}


def synth_demo(voice: str, out_mp3: str | Path, text: str | None = None,
               rate: str = "+0%", pitch: str = "+0Hz",
               emotion: bool = False) -> bool:
    """Đọc thử 1 câu ngắn bằng giọng `voice` -> file mp3. Câu mẫu tự chọn
    theo ngôn ngữ của giọng (vi-VN-... -> câu tiếng Việt). True nếu ra file
    hợp lệ; False nếu lỗi (mạng, giọng sai...).
    rate: tốc độ edge-tts (nghe thử nhịp kể recap); pitch: tông giọng
    edge-tts ('-18Hz'/'+0Hz'/'+18Hz' — Tông giọng recap). Gemini bỏ qua
    cả rate lẫn pitch (không hỗ trợ).
    emotion: BẬT + giọng ElevenLabs -> chèn 1-2 audio tag DEMO ([excited]/
    [whispers]) + model eleven_v3 để nghe KHÁC BIỆT cảm xúc; giọng khác bỏ
    qua (tag chỉ v3 hiểu)."""
    voice = (voice or "").strip()
    if not voice:
        return False
    if voice.startswith("el:"):         # ElevenLabs: đa ngữ -> câu mẫu Việt
        txt = (text or "").strip() or _DEMO_TEXTS["vi"]
        model = ""
        if emotion:                     # chèn 1-2 tag DEMO + model v3
            from app.ai.recap import _strip_audio_tags
            base = _strip_audio_tags(txt)   # bỏ tag cũ nếu có, tránh lồng
            txt = f"[whispers]{base} [excited]KHÔNG thể tin nổi!"
            model = _ELEVEN_MODEL_V3
        try:
            if _eleven_tts(txt, voice, str(out_mp3), model=model):
                return True
        except Exception:  # noqa: BLE001
            pass
        # lỗi/hết hạn mức -> fallback edge giọng đa ngữ (STRIP tag: edge
        # không hiểu; nghe thử vẫn ra, chỉ mất cảm xúc v3)
        from app.ai.recap import _strip_audio_tags
        return synth_demo("en-US-AndrewMultilingualNeural", out_mp3,
                          text=_strip_audio_tags(txt), rate=rate, pitch=pitch)
    if voice.startswith("gemini:"):     # giọng Gemini: đa ngữ -> câu mẫu Việt
        txt = (text or "").strip() or _DEMO_TEXTS["vi"]
        try:
            return _gemini_tts(txt, voice, str(out_mp3))
        except Exception:  # noqa: BLE001
            return False
    lang = norm_lang(voice.split("-")[0])
    txt = (text or "").strip() or _DEMO_TEXTS.get(lang) or _DEMO_TEXTS["en"]
    out_mp3 = str(out_mp3)

    async def _run() -> None:
        import edge_tts
        kw = {"rate": rate}
        if pitch and pitch != "+0Hz":
            kw["pitch"] = pitch
        try:
            comm = edge_tts.Communicate(txt, voice, **kw)
        except TypeError:               # bản edge-tts cổ không có pitch
            comm = edge_tts.Communicate(txt, voice, rate=rate)
        await comm.save(out_mp3)

    for _ in range(2):                  # mạng chập chờn -> thử lại 1 lần
        try:
            asyncio.run(_run())
            if os.path.getsize(out_mp3) > 1000:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.8)
    return False


# ------------------------------------------------------------------
# Bước 1+2: ánh xạ segment về timeline đầu ra + gom thành cụm câu
# ------------------------------------------------------------------
def _remap_segments(transcript: dict, clip_segments: list) -> list:
    """Trả list cụm [{start,end,text}] trên TIMELINE ĐẦU RA (sau ghép khúc).
    Gom các câu transcript liền nhau (gap < _JOIN_GAP) thành 1 cụm; KHÔNG gom
    vắt qua chỗ cắt ghép (khúc khác nhau -> cụm mới)."""
    segs = (transcript or {}).get("segments", []) or []
    raw = []                       # [start_out, end_out, text, seg_idx]
    offset = 0.0
    for si, (s, e) in enumerate(clip_segments or []):
        s, e = float(s), float(e)
        for t in segs:
            try:
                ts, te = float(t["start"]), float(t["end"])
            except (KeyError, ValueError, TypeError):
                continue
            txt = (t.get("text") or "").strip()
            if not txt:
                continue
            # lấy câu có phần GIAO với khúc này; kẹp mốc vào trong khúc
            if te > s and ts < e:
                a = offset + (max(ts, s) - s)
                b = offset + (min(te, e) - s)
                if b - a >= 0.25:            # mẩu quá ngắn (lẹm biên) -> bỏ
                    raw.append([a, b, txt, si])
        offset += (e - s)
    raw.sort(key=lambda x: x[0])

    # Gom cụm liền kề thành CÂU (giọng đọc tự nhiên hơn đọc từng mẩu)
    out: list[dict] = []
    for a, b, txt, si in raw:
        if out and si == out[-1]["_si"] and a - out[-1]["end"] < _JOIN_GAP:
            out[-1]["end"] = max(out[-1]["end"], b)
            out[-1]["text"] += " " + txt
        else:
            out.append({"start": a, "end": b, "text": txt, "_si": si})
    for o in out:
        o.pop("_si", None)
        o["start"] = round(o["start"], 3)
        o["end"] = round(o["end"], 3)
    return out


# ------------------------------------------------------------------
# Bước 3: dịch 1 LẦN tất cả cụm bằng LLM
# ------------------------------------------------------------------
_LANG_VI = {
    "vi": "tiếng Việt", "en": "tiếng Anh", "id": "tiếng Indonesia",
    "th": "tiếng Thái", "ko": "tiếng Hàn", "ja": "tiếng Nhật",
    "zh": "tiếng Trung", "es": "tiếng Tây Ban Nha",
    "pt": "tiếng Bồ Đào Nha", "fr": "tiếng Pháp",
}


def _translate_chunks(chunks: list[dict], target_lang: str) -> list[str]:
    """Dịch tất cả cụm sang target_lang trong 1 lần gọi LLM. Trả list text dịch
    (cùng số phần tử; phần tử lỗi/thiếu -> giữ text gốc). Ném LLMError nếu LLM
    chưa cấu hình hoặc gọi thất bại hoàn toàn."""
    from app.ai import llm
    if not llm.is_configured():
        raise llm.LLMError(
            "Lồng tiếng cần AI để dịch lời thoại — hãy dán key Groq/Gemini "
            "trong Cài đặt AI (hoặc chọn ngôn ngữ trùng với video).")
    lang_name = _LANG_VI.get(target_lang, target_lang)
    items = []
    for i, c in enumerate(chunks):
        dur = c["end"] - c["start"]
        txt = c["text"].replace("\n", " ")[:500]
        items.append(f'#{i} [{dur:.1f} giây]: "{txt}"')
    listing = "\n".join(items)
    system = (
        "Bạn là chuyên gia dịch lồng tiếng video (dubbing). Dịch tự nhiên như "
        "VĂN NÓI, ngắn gọn, giữ đúng ý và cảm xúc. CHỈ trả JSON thuần.")
    prompt = (
        f"Dịch các câu thoại sau sang {lang_name} để LỒNG TIẾNG video.\n"
        "Mỗi dòng: #số_thứ_tự [số giây cho phép]: \"lời thoại gốc\".\n"
        f"{listing}\n\n"
        "QUY TẮC:\n"
        f"- Dịch sang {lang_name}, văn NÓI tự nhiên (không văn viết cứng).\n"
        "- NGẮN GỌN: độ dài ĐỌC LÊN phải lọt khung [số giây] của từng câu — "
        "câu gốc dài thì lược bớt từ đệm, giữ ý chính.\n"
        "- KHÔNG thêm chú thích, không phiên âm, chỉ lời thoại.\n"
        f"- Trả về MẢNG JSON đúng {len(chunks)} chuỗi, cùng thứ tự:\n"
        '["câu dịch 1", "câu dịch 2", ...]')
    data = llm.complete_json(prompt, system=system)
    if isinstance(data, dict):          # model bọc {"translations": [...]}
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list):
        raise llm.LLMError("LLM không trả về mảng bản dịch cho lồng tiếng.")
    out = []
    for i, c in enumerate(chunks):
        t = data[i] if i < len(data) else None
        out.append(str(t).strip() if isinstance(t, str) and str(t).strip()
                   else c["text"])
    return out


# ------------------------------------------------------------------
# Bước 4: TTS edge-tts (async, song song tối đa 4)
# ------------------------------------------------------------------
async def _synth_all(texts: list[str], voice: str, paths: list[str],
                     on_done: Optional[Callable[[int], None]] = None,
                     rate: str = "+0%",
                     ) -> list[bool]:
    """Đọc từng câu song song. Trả list[bool] ok[i] = câu #i ra file hợp lệ.
    Câu lỗi (retry 4 lần vẫn hỏng) -> ok[i]=False (KHÔNG ném lỗi cả track):
    caller sẽ BỎ RIÊNG cụm đó, các cụm khác giữ ĐÚNG mốc (không dồn/lệch).
    rate: tốc độ edge-tts ("-3%"/"+0%"/"+4%"...) — nhịp kể recap."""
    import edge_tts
    sem = asyncio.Semaphore(_TTS_PARALLEL)
    ok = [False] * len(texts)

    async def one(i: int) -> None:
        async with sem:
            txt = (texts[i] or "").strip()
            if not txt:                     # cụm rỗng -> coi như không có tiếng
                if on_done:
                    on_done(i)
                return
            for attempt in range(4):        # server MS chập chờn THEO ĐỢT
                                            # (NoAudioReceived) -> thử lại lâu hơn
                try:
                    comm = edge_tts.Communicate(txt, voice, rate=rate)
                    await comm.save(paths[i])
                    if os.path.getsize(paths[i]) > 200:
                        ok[i] = True
                        break
                except Exception:  # noqa: BLE001
                    pass
                await asyncio.sleep(1.5 * (attempt + 1))
            if on_done:
                on_done(i)

    await asyncio.gather(*(one(i) for i in range(len(texts))))
    return ok


# WordBoundary của edge-tts trả offset/duration theo tick 100 nano-giây
_WB_TICKS = 10_000_000.0


async def _synth_all_words(texts: list[str], voice: str, paths: list[str],
                           on_done: Optional[Callable[[int], None]] = None,
                           rate: str | list = "+0%",
                           pitch: str = "+0Hz",
                           ) -> tuple[list[bool], list[list]]:
    """Như _synth_all nhưng THU thêm WORD BOUNDARY của edge-tts (stream API:
    chunk type "WordBoundary" có offset/duration 100-ns) -> mốc TỪNG TỪ theo
    thời gian THẬT của giọng đọc (TRƯỚC atempo).

    Trả (ok, words): ok[i] như _synth_all; words[i] = [[start_s, end_s, từ],
    ...] tăng dần theo thời gian (rỗng nếu cụm rỗng/lỗi/không có event).
    CHỈ edge-tts có event này — giọng Gemini dùng đường khác (không words).
    rate: nhịp kể recap ("-3%"/"+0%"/"+4%") — WordBoundary do server trả theo
    audio THẬT (đã áp rate) nên mốc từng từ vẫn đúng, không cần bù.
    rate có thể là LIST cùng độ dài texts (rate RIÊNG từng cụm — câu hook
    recap đọc nhanh hơn +2%); chuỗi đơn = chung cho mọi cụm.
    pitch: TÔNG GIỌNG edge-tts ('-18Hz'/'+0Hz'/'+18Hz' — Tông giọng recap),
    chung cho mọi cụm; '+0Hz' -> không truyền (giữ hành vi cũ y nguyên).
    """
    import edge_tts
    sem = asyncio.Semaphore(_TTS_PARALLEL)
    ok = [False] * len(texts)
    words: list[list] = [[] for _ in texts]

    async def one(i: int) -> None:
        async with sem:
            txt = (texts[i] or "").strip()
            if not txt:                     # cụm rỗng -> coi như không có tiếng
                if on_done:
                    on_done(i)
                return
            r_i = rate[i] if isinstance(rate, list) else rate
            kw = {"rate": r_i}
            if pitch and pitch != "+0Hz":   # tông giọng (edge-tts >=6 có)
                kw["pitch"] = pitch
            for attempt in range(4):        # server MS chập chờn THEO ĐỢT
                                            # (NoAudioReceived) -> thử lại lâu hơn
                wb: list = []
                try:
                    try:
                        # edge-tts >=7 mặc định SentenceBoundary -> phải xin
                        # WordBoundary tường minh
                        comm = edge_tts.Communicate(txt, voice,
                                                    boundary="WordBoundary",
                                                    **kw)
                    except TypeError:       # edge-tts <7: luôn WordBoundary
                        try:
                            comm = edge_tts.Communicate(txt, voice, **kw)
                        except TypeError:   # bản cổ không có pitch
                            comm = edge_tts.Communicate(txt, voice, rate=r_i)
                    with open(paths[i], "wb") as f:
                        async for ch in comm.stream():
                            if ch["type"] == "audio" and ch.get("data"):
                                f.write(ch["data"])
                            elif ch["type"] == "WordBoundary":
                                a = float(ch.get("offset", 0)) / _WB_TICKS
                                d = float(ch.get("duration", 0)) / _WB_TICKS
                                w = str(ch.get("text") or "").strip()
                                if w and d >= 0:
                                    wb.append([round(a, 3),
                                               round(a + d, 3), w])
                    if os.path.getsize(paths[i]) > 200:
                        ok[i] = True
                        words[i] = wb
                        break
                except Exception:  # noqa: BLE001
                    pass
                await asyncio.sleep(1.5 * (attempt + 1))
            if on_done:
                on_done(i)

    await asyncio.gather(*(one(i) for i in range(len(texts))))
    return ok, words


# ------------------------------------------------------------------
# ffmpeg helpers
# ------------------------------------------------------------------
def _ffmpeg(args: list[str], what: str, timeout: int = 300) -> None:
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
           *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_CREATE_NO_WINDOW,
                       timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi khi {what}: {(r.stderr or '')[-400:]}")


def probe_duration(path: str | Path) -> float:
    """Độ dài (giây) của file audio bằng ffprobe; 0.0 nếu lỗi."""
    cmd = [settings.FFPROBE_PATH, "-v", "error", "-print_format", "json",
           "-show_format", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace",
                             creationflags=_CREATE_NO_WINDOW, timeout=60)
        return float(json.loads(out.stdout or "{}")
                     .get("format", {}).get("duration", 0) or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0.0


# silencedetect: khoảng IM ≥ ngưỡng này (giây) mới coi là "ngắt" (nối 2 đoạn
# nói). Giọng cảm xúc v3 chèn [dramatic pause] tạo khoảng lặng 0.3-1s giữa câu
# -> tách thành các đoạn CÓ TIẾNG riêng để phụ đề chỉ chạy khi đang nói.
_SILENCE_NOISE_DB = -30.0
_SILENCE_MIN_DUR = 0.25
_SIL_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END_RE = re.compile(r"silence_end:\s*(-?[\d.]+)")

# Phụ đề narrate MẶC ĐỊNH chia theo CÂU-CỤM (2-4 từ/nhóm) phân bố theo audio
# THẬT thay vì karaoke từng-từ: WordBoundary của Microsoft không phải lúc nào
# cũng chuẩn (nhất là ngôn ngữ ngoài en) -> chia cụm ít trôi hơn. Word-level
# giữ làm tuỳ chọn (RECAP_WORD_LEVEL_CAPTION=1). (Định nghĩa SỚM ở đây vì
# _phrase_groups_by_speech ngay dưới dùng làm default arg.)
_RECAP_PHRASE_MIN = 2
_RECAP_PHRASE_MAX = 4


def _detect_speech_segments(wav_path: str, total: float,
                            noise_db: float = _SILENCE_NOISE_DB,
                            min_sil: float = _SILENCE_MIN_DUR,
                            ) -> list[tuple[float, float]]:
    """DÒ các ĐOẠN CÓ TIẾNG trong file audio bằng ffmpeg silencedetect
    (n=noise_db dB : d=min_sil giây). Trả [(a, b), ...] các khoảng NÓI (đã bỏ
    khoảng im), theo thời gian file (0..total). Dùng để căn phụ đề giọng
    KHÔNG có word timestamp (ElevenLabs/Gemini) khi bật cảm xúc: chữ chỉ chạy
    lúc đang nói, ngắt [dramatic pause] thì chữ ĐỨNG.

    Cách làm: silencedetect log các khoảng IM (silence_start/silence_end) ra
    stderr; NGHỊCH ĐẢO thành các khoảng có tiếng. Không dò được đoạn im nào
    (nói liền một mạch) -> trả [] để caller FALLBACK chia đều như cũ (không
    ép tách vô cớ). total <= 0 -> []."""
    if total <= 0.05:
        return []
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-i",
           str(wav_path), "-af",
           f"silencedetect=noise={noise_db:.1f}dB:d={min_sil:.3f}",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    log = r.stderr or ""
    # Ghép cặp start/end theo thứ tự xuất hiện (ffmpeg log tuần tự).
    sils: list[list[float]] = []
    for line in log.splitlines():
        ms = _SIL_START_RE.search(line)
        if ms:
            sils.append([float(ms.group(1)), total])   # end tạm = total
            continue
        me = _SIL_END_RE.search(line)
        if me and sils:
            sils[-1][1] = float(me.group(1))
    if not sils:                        # không có khoảng im -> caller chia đều
        return []
    # NGHỊCH ĐẢO khoảng im -> khoảng có tiếng, kẹp trong [0, total]
    speech: list[tuple[float, float]] = []
    cur = 0.0
    for a, b in sils:
        a = max(0.0, min(a, total))
        b = max(0.0, min(b, total))
        if a - cur > 0.05:              # có tiếng trước khoảng im này
            speech.append((round(cur, 3), round(a, 3)))
        cur = max(cur, b)
    if total - cur > 0.05:              # có tiếng sau khoảng im cuối
        speech.append((round(cur, 3), round(total, 3)))
    # Bỏ đoạn nói quá ngắn (<0.12s — nhiễu/bụp), tránh cụm chữ rơi vào rác
    speech = [(a, b) for a, b in speech if b - a >= 0.12]
    return speech


def _phrase_groups_by_speech(text: str, start: float,
                             speech_segs: list[tuple[float, float]],
                             group: int = _RECAP_PHRASE_MAX) -> list:
    """Chia `text` thành cụm ~`group` từ rồi RẢI vào các ĐOẠN CÓ TIẾNG
    `speech_segs` (mốc THEO FILE audio, gốc 0). Mỗi đoạn nhận số cụm/thời
    gian TỈ LỆ ĐỘ DÀI đoạn đó, trong đoạn chia tiếp theo TỈ LỆ SỐ KÝ TỰ ->
    đoạn nói dài mang nhiều chữ hơn; KHÔNG có chữ trong khoảng im giữa các
    đoạn. Neo về timeline clip bằng cộng `start`. Trả [[a, b, cụm], ...].

    Dùng cho giọng el/Gemini khi BẬT cảm xúc (có [dramatic pause]) — sửa lỗi
    'phụ đề delay lệch' do chia đều mù quáng qua khoảng lặng. speech_segs
    rỗng -> [] (caller dùng _phrase_groups_even chia đều)."""
    toks = str(text or "").split()
    if not toks or not speech_segs:
        return []
    groups = [toks[i:i + group] for i in range(0, len(toks), group)]
    ng = len(groups)
    seg_dur = [max(0.01, b - a) for a, b in speech_segs]
    total_dur = sum(seg_dur) or 1.0
    # PHÂN BỔ số cụm cho từng đoạn theo TỈ LỆ độ dài đoạn (mỗi đoạn >=1 cụm
    # nếu còn cụm; đoạn dài -> nhiều cụm hơn). Largest-remainder cho khỏi lệch.
    want = [d / total_dur * ng for d in seg_dur]
    cnt = [int(w) for w in want]
    rem = ng - sum(cnt)
    order = sorted(range(len(speech_segs)), key=lambda k: want[k] - cnt[k],
                   reverse=True)
    for k in order:
        if rem <= 0:
            break
        cnt[k] += 1
        rem -= 1
    # đảm bảo không đoạn nào 0 cụm khi vẫn dư cụm ở đoạn khác >1 (dồn chữ lệch)
    out: list = []
    gi = 0
    for si, (sa, sb) in enumerate(speech_segs):
        take = cnt[si]
        if take <= 0 or gi >= ng:
            continue
        segs_here = groups[gi:gi + take]
        gi += take
        chars = [max(1, len(" ".join(g))) for g in segs_here]
        tot_c = sum(chars) or 1
        t = float(start) + sa
        seg_len = sb - sa
        for g, c in zip(segs_here, chars):
            d = seg_len * c / tot_c
            out.append([round(t, 3), round(t + d, 3), " ".join(g)])
            t += d
        if out:                         # kẹp cụm cuối đoạn đúng mép có tiếng
            out[-1][1] = round(float(start) + sb, 3)
    # cụm còn sót (do làm tròn) -> nối vào đoạn cuối cùng
    if gi < ng and out:
        leftover = " ".join(" ".join(g) for g in groups[gi:])
        if leftover.strip():
            out[-1][2] = (out[-1][2] + " " + leftover).strip()
    return out


def _tempo_filters(tempo: float) -> str:
    """Chuỗi atempo (chia tầng nếu >2.0 — phòng xa, hiện _MAX_TEMPO=1.35)."""
    parts = []
    while tempo > 2.0:
        parts.append("atempo=2.0")
        tempo /= 2.0
    parts.append(f"atempo={tempo:.4f}")
    return ",".join(parts)


def _fit_chunk(src_mp3: str, dst_wav: str, budget: float, hard_max: float,
               tight: bool = False, window: float = 0.0) -> float:
    """Chuyển 1 cụm TTS (mp3) -> wav 48k mono. Trả về ĐỘ DÀI (giây) sau khi xử lý.

    Chế độ "Tự nhiên" (tight=False, mặc định): đọc TỐC ĐỘ THƯỜNG, neo vào đúng
    start. CHỈ tăng tốc khi lời đọc dài hơn `budget` (khoảng cách tới start cụm
    kế) — tức sắp ĐÈ sang cụm sau; tăng vừa đủ, trần _MAX_TEMPO. Đọc ngắn hơn
    khung -> để tự nhiên (im lặng phần dư, KHÔNG kéo dài).

    Chế độ "Khớp chặt" (tight=True): ép lời đọc lọt khung riêng của cụm
    (`window` = end-start) như cũ -> khớp sát nhưng có thể nhanh/giật.

    hard_max: chặn cứng tuyệt đối (không cho tràn quá điểm này) -> cắt + fade
    120ms cuối cho khỏi bụp. Đảm bảo cụm KHÔNG bao giờ đè lên start cụm kế."""
    dur = probe_duration(src_mp3)
    if dur <= 0:
        raise RuntimeError("TTS trả file audio hỏng (0 giây)")
    af = ["aresample=48000"]
    limit = window if (tight and window > 0.2) else budget
    if limit > 0.2 and dur > limit + 0.05:
        tempo = min(_MAX_TEMPO, dur / limit)
        af.append(_tempo_filters(tempo))
        dur = dur / tempo
    if hard_max > 0.05 and dur > hard_max + 0.05:   # trần vẫn dư -> cắt + fade
        af.append(f"atrim=0:{hard_max:.3f}")
        af.append(f"afade=t=out:st={max(0.0, hard_max - 0.12):.3f}:d=0.12")
        dur = hard_max
    _ffmpeg(["-i", src_mp3, "-af", ",".join(af), "-ac", "1", "-ar", "48000",
             "-c:a", "pcm_s16le", dst_wav], "khớp thời gian lồng tiếng")
    return dur


def _mix_track(chunk_wavs: list[tuple[float, str]], total: float,
               out_wav: str) -> None:
    """Ghép các cụm vào 1 track: nền im lặng anullsrc dài ĐÚNG total, mỗi cụm
    adelay theo mốc start rồi amix (normalize=0 giữ nguyên âm lượng)."""
    args: list[str] = ["-f", "lavfi", "-t", f"{total:.3f}",
                       "-i", "anullsrc=r=48000:cl=mono"]
    parts, labels = [], []
    for i, (start, wav) in enumerate(chunk_wavs):
        args += ["-i", wav]
        ms = max(0, int(round(start * 1000)))
        parts.append(f"[{i + 1}:a]adelay={ms}:all=1[d{i}]")
        labels.append(f"[d{i}]")
    n = len(chunk_wavs) + 1
    parts.append(f"[0:a]{''.join(labels)}amix=inputs={n}:duration=first:"
                 f"normalize=0[out]")
    args += ["-filter_complex", ";".join(parts), "-map", "[out]",
             "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out_wav)]
    _ffmpeg(args, "ghép track lồng tiếng", timeout=600)


def _loudnorm_wav(wav_path: str, i_lufs: float = -16.0) -> None:
    """Chuẩn hoá loudness track thuyết minh về `i_lufs` (EBU R128 1-pass,
    TP=-1.5 chống clip; gating của R128 tự BỎ khoảng lặng giữa các part nên
    chỉ đo phần có giọng). Ghi đè file gốc (giữ 48k mono pcm_s16le).
    Ném RuntimeError nếu ffmpeg lỗi (caller best-effort)."""
    tmp = wav_path + ".ln.wav"
    _ffmpeg(["-i", wav_path,
             "-af", f"loudnorm=I={i_lufs:.1f}:TP=-1.5:LRA=11,aresample=48000",
             "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", tmp],
            "chuẩn hoá âm lượng thuyết minh", timeout=600)
    os.replace(tmp, wav_path)


def measure_loudness(path: str | Path, start: float = 0.0,
                     dur: float = 0.0) -> Optional[float]:
    """Đo integrated loudness (LUFS, EBU R128) của audio trong file/đoạn
    [start, start+dur] bằng loudnorm print_format=json (chỉ decode, không ghi
    file). Trả None nếu ffmpeg lỗi / không có audio / gần câm (<= -70 LUFS).

    Dùng để ĐO ĐỘ TO THẬT của video nguồn: video nhạc/gaming thường rất to
    (-6..-10 LUFS) — chuẩn hoá narration cứng về -16 LUFS vẫn CHÌM nghỉm
    (lỗi 'giọng AI bé' user gặp thật). Đo gốc rồi match mới đúng."""
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-nostats"]
    if start > 0.01:
        cmd += ["-ss", f"{start:.3f}"]
    if dur > 0.01:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(path), "-vn", "-sn", "-map", "0:a:0",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           creationflags=_CREATE_NO_WINDOW, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r'"input_i"\s*:\s*"?(-?[\d.]+|-inf)"?', r.stderr or "")
    if not m or "inf" in m.group(1):
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return v if v > -70.0 else None


def _gain_wav(wav_path: str, gain_db: float = 0.0,
              factor: float = 1.0) -> None:
    """Nhân âm lượng track WAV (gain dB và/hoặc hệ số), kèm limiter chống
    clip (alimiter trần ~-0.45dBFS, level=false để không tự khuếch đại lại).
    Ghi đè file gốc (giữ 48k mono pcm_s16le). Không có gì để chỉnh -> no-op.
    Ném RuntimeError nếu ffmpeg lỗi (caller quyết best-effort)."""
    af = []
    if abs(gain_db) > 0.05:
        af.append(f"volume={gain_db:.2f}dB")
    if abs(factor - 1.0) > 0.02:
        af.append(f"volume={max(0.1, min(4.0, factor)):.3f}")
    if not af:
        return
    af.append("alimiter=limit=0.95:level=false")
    tmp = wav_path + ".g.wav"
    _ffmpeg(["-i", wav_path, "-af", ",".join(af) + ",aresample=48000",
             "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", tmp],
            "chỉnh âm lượng thuyết minh", timeout=600)
    os.replace(tmp, wav_path)


# Auto-match âm lượng narration với TIẾNG GỐC video: to hơn gốc nhẹ
# (+1.5dB) cho lời kể nổi lên; kẹp target trong [-27, -9] LUFS (trần -9 để
# loudnorm TP=-1.5 còn chỗ thở, sàn -27 khi video gốc gần câm).
_RECAP_HEADROOM_DB = 1.5
_RECAP_TARGET_MIN = -27.0
_RECAP_TARGET_MAX = -9.0


# ------------------------------------------------------------------
# 🎙 REUP THUYẾT MINH (recap) — track giọng AI đọc KỊCH BẢN theo part
# ------------------------------------------------------------------
# atempo cho lời thuyết minh: KHÔNG BAO GIỜ kéo chậm (<1.0) — kênh recap
# thật đọc TỐC ĐỘ TỰ NHIÊN; lời ngắn hơn part là bình thường (phần dư trả
# tiếng gốc về, KHÔNG lấp bằng cách đọc lề mề — lỗi 'AI đọc quá chậm' user
# gặp thật). Chỉ NÉN nhẹ (tối đa 1.28) khi lời dài hơn khung — phần tràn xử
# bằng MƯỢN THỜI GIAN từ part orig kế, xem build_recap_track.
_RECAP_TEMPO_MIN = 1.0
_RECAP_TEMPO_MAX = 1.28
# Part narrate CUỐI clip (không còn chỗ mượn): cho nói nhanh tới 1.4 trước
# khi đành trim + fade — thà nhanh một chút còn hơn CỤT CHỮ giữa câu.
_RECAP_TEMPO_MAX_TAIL = 1.4
# MƯỢN THỜI GIAN: lời narrate tràn khung (dù đã atempo 1.28) -> kéo dài window
# sang đầu part orig kế, tối đa min(_BORROW_MAX_S, _BORROW_MAX_FRAC * độ dài
# quãng orig kế). Phần orig bị mượn sẽ bị duck thêm (narr_events giãn theo)
# — chấp nhận, còn hơn mất chữ.
_BORROW_MAX_S = 3.0
_BORROW_MAX_FRAC = 0.40


def _recap_word_level() -> bool:
    """Có bật phụ đề narrate WORD-LEVEL (karaoke từng từ) không. Mặc định
    TẮT -> dùng câu-cụm (ít trôi). Bật qua biến môi trường / settings
    RECAP_WORD_LEVEL_CAPTION khi muốn karaoke từng từ."""
    v = os.environ.get("RECAP_WORD_LEVEL_CAPTION")
    if v is None:
        v = str(getattr(settings, "RECAP_WORD_LEVEL_CAPTION", "") or "")
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _phrase_groups_even(text: str, start: float, speech_dur: float,
                        group: int = _RECAP_PHRASE_MAX) -> list:
    """Chia `text` thành cụm ~`group` từ, PHÂN BỐ ĐỀU theo PHẦN CÓ TIẾNG THẬT:
    mỗi cụm chiếm thời gian TỈ LỆ số từ của nó trên `speech_dur`, neo từ
    `start`. speech_dur = độ dài phần LỜI NÓI thật (mép từ cuối), KHÔNG tính
    khoảng lặng/hơi thở đuôi mà edge-tts hay thêm -> cụm cuối tắt đúng lúc hết
    tiếng (không trôi +1s). Trả [[a, b, cụm], ...] trên timeline clip. Ít trôi
    hơn karaoke từng-từ vì chỉ cần TỔNG speech_dur đúng (đo thật)."""
    toks = str(text or "").split()
    if not toks or speech_dur <= 0.05:
        return []
    groups = [toks[i:i + group] for i in range(0, len(toks), group)]
    total_w = sum(len(g) for g in groups) or 1
    out, t = [], float(start)
    for g in groups:
        d = speech_dur * len(g) / total_w
        out.append([round(t, 3), round(t + d, 3), " ".join(g)])
        t += d
    # kẹp cụm cuối đúng mép tiếng (làm tròn tích luỹ)
    if out:
        out[-1][1] = round(float(start) + speech_dur, 3)
    return out


# ------------------------------------------------------------------
# 🔁 STT WORD-SYNC (sửa lỗi 'phụ đề lệch ở giọng cảm xúc'): giọng el/Gemini
# (và đường fallback edge của chúng) KHÔNG có WordBoundary — silencedetect +
# chia theo ký tự vẫn TRÔI vì tốc độ đọc KHÔNG ĐỀU trong 1 đoạn có tiếng
# (chỗ nhanh chỗ chậm -> chữ nhảy trước khi nói). Giải quyết TRIỆT ĐỂ:
# CHÉP LỜI word-level CHÍNH audio part ĐÃ RENDER (Groq whisper — đường
# transcribe._groq_one sẵn có; part 5-25s nên nhanh + rẻ) -> dùng MỐC THỜI
# GIAN của STT nhưng CHỮ của kịch bản. STT lỗi/không key/timeout/lệch từ
# quá 40% -> fallback silencedetect + chia ký tự như cũ (không tệ hơn).
# ------------------------------------------------------------------
_STT_TIMEOUT_S = 20.0        # quá 20s -> bỏ STT, fallback silencedetect
_STT_MISS_MAX = 0.40         # số từ STT lệch quá 40% so kịch bản -> coi fail


def _stt_part_words(wav_path: str, lang: str,
                    timeout: float = _STT_TIMEOUT_S) -> Optional[list]:
    """Word-level STT cho 1 file audio part (Groq whisper — đường transcribe
    SẴN CÓ của app). Trả [[start, end, từ], ...] theo thời gian FILE (gốc 0,
    tăng dần) hoặc None (không key / lỗi / timeout / không nghe ra từ nào —
    caller fallback silencedetect, không tệ hơn hiện tại).

    CACHE theo SHA1 NỘI DUNG audio (nằm cùng thư mục TTS cache, LRU dọn
    chung): part tái render y hệt (TTS cache hit -> audio byte-identical)
    -> đọc cache, KHÔNG gọi STT lại — xuất lại clip không tốn lượt Groq."""
    try:
        h = hashlib.sha1(Path(wav_path).read_bytes()).hexdigest()
    except OSError:
        return None
    cache = _TTS_CACHE_DIR / f"{h}.stt.json"
    try:
        if cache.is_file():
            data = json.loads(cache.read_text(encoding="utf-8"))
            os.utime(cache, None)      # LRU — file hay dùng không bị dọn
            w = data.get("words") if isinstance(data, dict) else None
            if isinstance(w, list) and w:
                return [[float(a), float(b), str(t)] for a, b, t in w]
    except (OSError, ValueError, TypeError):
        pass
    try:
        keys = settings.groq_keys()
    except Exception:  # noqa: BLE001 — settings hỏng thì coi như không key
        keys = []
    if not keys:
        return None
    import threading
    from app.core import transcribe as _tr

    box: dict = {}

    def _run() -> None:
        try:
            _segs, w, _lg, _txt = _tr._groq_one(
                wav_path, norm_lang(lang) or None, keys)
            box["words"] = w
        except Exception:  # noqa: BLE001 — 401/429/mạng -> fallback êm
            pass

    # Thread DAEMON + join có timeout (KHÔNG dùng ThreadPoolExecutor: worker
    # của nó bị join ở exit — request treo sẽ giữ app không thoát được).
    th = threading.Thread(target=_run, daemon=True)
    th.start()
    th.join(timeout)
    words = box.get("words")           # quá timeout -> None (thread tự chết)
    if not words:
        return None
    out = []
    for w in words or []:
        try:
            a, b = float(w["start"]), float(w["end"])
            t = str(w.get("word") or "").strip()
        except (KeyError, TypeError, ValueError):
            continue
        if t and b >= a >= 0:
            out.append([round(a, 3), round(max(a, b), 3), t])
    if not out:
        return None
    try:                               # cache best-effort (đĩa lỗi -> bỏ qua)
        _TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(cache) + ".tmp"
        Path(tmp).write_text(json.dumps({"words": out}, ensure_ascii=False),
                             encoding="utf-8")
        os.replace(tmp, cache)
        _tts_cache_evict()
    except OSError:
        pass
    return out


def _align_stt_words(script_text: str, stt_words: list,
                     miss_max: float = _STT_MISS_MAX) -> Optional[list]:
    """Ghép MỐC THỜI GIAN của words STT với CHỮ của KỊCH BẢN (STT nghe nhầm
    chính tả/dấu là thường — chữ hiển thị phải là bản kịch bản sạch). Align
    ĐƠN GIẢN theo thứ tự từ: số từ bằng nhau -> map 1-1; lệch nhỏ -> map TỈ
    LỆ chỉ số (từ kịch bản i nhận khoảng thời gian của cụm từ STT tương
    ứng); lệch quá `miss_max` (40%) -> None (STT nghe sai quá nhiều — caller
    fallback silencedetect). Trả [[start, end, từ_kịch_bản], ...] theo thời
    gian FILE, mốc không giảm. Hàm thuần — unit test được."""
    toks = str(script_text or "").split()
    k = len(stt_words or [])
    m = len(toks)
    if not m or not k:
        return None
    if abs(m - k) / max(m, k) > miss_max:
        return None
    out = []
    for i in range(m):
        j0 = min(k - 1, (i * k) // m)
        j1 = min(k - 1, max(j0, ((i + 1) * k) // m - 1))
        a = float(stt_words[j0][0])
        b = max(a, float(stt_words[j1][1]))
        if out and a < out[-1][0]:     # phòng STT trả mốc lộn xộn
            a = out[-1][0]
            b = max(a, b)
        out.append([round(a, 3), round(b, 3), toks[i]])
    return out


def _phrase_groups_from_words(words: list, start: float,
                              group: int = _RECAP_PHRASE_MAX) -> list:
    """Gom words [[a, b, từ], ...] (thời gian FILE, mốc TỪNG TỪ THẬT từ
    STT/WordBoundary) thành CỤM ~`group` từ, neo timeline clip bằng cộng
    `start` -> [[a, b, cụm], ...]. Mốc cụm = mép từ ĐẦU/CUỐI ĐO THẬT —
    không chia đều ước lượng nên không trôi khi giọng đọc nhanh chậm thất
    thường (giọng cảm xúc). Hàm thuần — unit test được."""
    out = []
    for i in range(0, len(words or []), group):
        g = words[i:i + group]
        txt = " ".join(str(w[2]).strip() for w in g if str(w[2]).strip())
        if not txt:
            continue
        out.append([round(start + float(g[0][0]), 3),
                    round(start + float(g[-1][1]), 3), txt])
    return out


# ------------------------------------------------------------------
# 🔒 KHÓA CỨNG ĐỘ CHÍNH XÁC PHỤ ĐỀ (hậu kiểm BẮT BUỘC sau khi build cue)
# Yêu cầu TUYỆT ĐỐI: chữ hiện ĐÚNG LÚC nói — không bao giờ hiện TRƯỚC khi
# nói hoặc SAU khi hết nói. Bất kể nguồn mốc (WordBoundary/STT/silencedetect/
# chia đều), MỌI cue narrate đều phải qua 2 lớp:
#   LỚP 1 (_clamp_cues_to_speech): clamp cứng vào các khoảng CÓ TIẾNG đo
#     THẬT trên wav part CUỐI CÙNG (silencedetect -32dB/0.18 — nhạy hơn tham
#     số cũ); cue hoàn toàn ngoài tiếng -> XÓA (thà không chữ còn hơn sai lúc).
#   LỚP 2 (_cue_speech_bias): cue đầu part lệch speech onset thật > 0.12s
#     (cả part trượt đều — offset/adelay/STT lệch hệ thống) -> DỊCH cả cụm
#     đúng hiệu lệch rồi chạy lại lớp 1.
# CHỈ áp cho cue NARRATE (orig cues lấy từ transcript video — vốn khớp).
# ------------------------------------------------------------------
_CLAMP_NOISE_DB = -32.0      # ngưỡng silencedetect cho hậu kiểm (nhạy hơn -30)
_CLAMP_MIN_SIL = 0.18        # khoảng im >= 0.18s mới coi là ngắt
_CUE_PAD_BEFORE = 0.05       # cue được phép SỚM hơn tiếng tối đa 50ms
_CUE_PAD_AFTER = 0.12        # cue được phép MUỘN hơn hết tiếng tối đa 120ms
_CUE_BIAS_MAX = 0.12         # lệch hệ thống > 0.12s -> shift cả part


def _cue_speech_bias(cues: list, speech: list,
                     thresh: float = _CUE_BIAS_MAX) -> float:
    """LỚP 2 — TỰ CĂN LỆCH HỆ THỐNG: so mốc cue ĐẦU TIÊN với mốc BẮT ĐẦU
    có tiếng THẬT (speech[0][0], đo silencedetect trên wav part cuối).
    Lệch quá `thresh` giây (toàn bộ part trượt đều) -> trả HIỆU LỆCH để
    caller DỊCH TẤT CẢ cue của part (shift cả cụm); lệch nhỏ -> 0.0.
    `cues` [[a, b, text], ...] và `speech` [(a, b), ...] CÙNG gốc thời gian
    (file part, gốc 0). Hàm thuần — unit test được."""
    if not cues or not speech:
        return 0.0
    d = float(speech[0][0]) - float(cues[0][0])
    return d if abs(d) > thresh else 0.0


def _clamp_cues_to_speech(cues: list, speech: list,
                          pad_before: float = _CUE_PAD_BEFORE,
                          pad_after: float = _CUE_PAD_AFTER) -> list:
    """LỚP 1 — CLAMP CỨNG: KHÔNG cue nào được nằm ngoài khoảng CÓ TIẾNG.
    Với mỗi cue [a, b, text]:
      - start = max(start, onset đoạn tiếng GẦN NHẤT - pad_before);
      - end   = min(end,  mép HẾT tiếng gần nhất + pad_after);
      - cue HOÀN TOÀN ngoài mọi khoảng tiếng -> XÓA. "Ngoài" tính theo mép
        tiếng THẬT (KHÔNG cộng pad): cue chỉ lọt vùng pad (vd nằm trọn trong
        120ms sau khi hết tiếng) vẫn là chữ hiện lúc KHÔNG nói -> xóa;
      - sau clamp bị đảo/quá ngắn (end - start < 0.05) -> XÓA.
    Cue trải qua NHIỀU đoạn tiếng (cụm chữ vắt qua ngắt ngắn) -> giữ, chỉ
    kẹp 2 mép theo đoạn đầu/cuối giao được. `cues`/`speech` CÙNG gốc thời
    gian. speech rỗng -> [] (không tiếng thì không chữ). Hàm thuần."""
    if not speech:
        return []
    out: list = []
    for a, b, txt in cues:
        a, b = float(a), float(b)
        touch = [(float(sa), float(sb)) for sa, sb in speech
                 if min(b, float(sb)) - max(a, float(sa)) > 0.0]
        if not touch:                    # không GIAO khoảng tiếng nào -> xóa
            continue
        na = max(a, touch[0][0] - pad_before)
        nb = min(b, touch[-1][1] + pad_after)
        if nb - na < 0.05:               # đảo/quá ngắn sau clamp -> xóa
            continue
        out.append([round(na, 3), round(nb, 3), txt])
    return out


def _fit_recap_chunk(src: str, dst_wav: str, window: float,
                     tempo_max: float = _RECAP_TEMPO_MAX,
                     ) -> tuple[float, float, float]:
    """Khớp 1 cụm thuyết minh vào khung `window` giây: atempo 1.0-`tempo_max`
    (KHÔNG BAO GIỜ kéo chậm <1.0 — lời ngắn hơn khung thì giữ tốc độ tự
    nhiên, phần dư của part caller trả tiếng gốc về); vẫn dư -> cắt + fade
    120ms cuối (không tràn sang part kế).

    Trả (D_final, D_nat, tempo):
      - D_final = ĐỘ DÀI THẬT của file wav sau MỌI filter (đo lại bằng ffprobe,
        KHÔNG tin tham số dự kiến — atempo/aresample/atrim làm tròn khác dur/k).
      - D_nat   = độ dài TỰ NHIÊN (trước atempo, sau khi có thể bị atrim ở
        window*tempo_max) = phần audio gốc thực sự được nén vào D_final.
      - tempo   = hệ số atempo đã áp (log/tham khảo).
    Caller SCALE mốc word boundary theo D_final/D_nat (đo THẬT) thay vì 1/tempo
    -> phụ đề khớp audio ~100% dù ffmpeg làm tròn/đổi mẫu (sửa lỗi 'chữ trôi')."""
    dur = probe_duration(src)
    if dur <= 0:
        raise RuntimeError("TTS trả file audio hỏng (0 giây)")
    d_nat = dur                       # phần audio gốc ánh xạ vào D_final
    af = ["aresample=48000"]
    tempo = 1.0
    if window > 0.2 and abs(dur - window) > 0.05:
        t = max(_RECAP_TEMPO_MIN, min(max(tempo_max, _RECAP_TEMPO_MIN),
                                      dur / window))
        if abs(t - 1.0) > 0.02:
            tempo = t
            af.append(_tempo_filters(tempo))
            dur = dur / tempo
    if window > 0.05 and dur > window + 0.05:       # tempo trần vẫn dư -> cắt
        af.append(f"atrim=0:{window:.3f}")
        af.append(f"afade=t=out:st={max(0.0, window - 0.12):.3f}:d=0.12")
        # atrim cắt ở D_final=window -> phần gốc bị mất tương ứng: D_nat co lại
        d_nat = window * tempo
        dur = window
    _ffmpeg(["-i", src, "-af", ",".join(af), "-ac", "1", "-ar", "48000",
             "-c:a", "pcm_s16le", dst_wav], "khớp thời gian thuyết minh")
    d_final = probe_duration(dst_wav) or dur       # ĐO THẬT (không tin dur/k)
    return d_final, d_nat, tempo


def _map_to_output(t: float, clip_segments: list) -> Optional[float]:
    """Đổi mốc t (timeline VIDEO GỐC) -> timeline ĐẦU RA sau ghép khúc.
    t nằm ngoài mọi khúc -> None."""
    offset = 0.0
    for s, e in clip_segments:
        s, e = float(s), float(e)
        if s - 0.05 <= t <= e + 0.05:
            return offset + min(max(t, s), e) - s
        offset += e - s
    return None


def build_recap_track(parts: list, clip_segments: list, voice: str,
                      lang: str, out_wav: str | Path,
                      on_progress: Optional[Callable[[float, str], None]] = None,
                      pace: str = "normal", pitch: str = "normal",
                      src_path: str = "", volume: float = 1.0,
                      emotion: bool = False,
                      ) -> tuple[str, list[dict]]:
    """Dựng track THUYẾT MINH cho clip recap. Trả (wav_path, narrate_events).

    src_path: đường dẫn VIDEO GỐC (tùy chọn) — dùng ĐO loudness thật của
    tiếng gốc trong clip để auto-match âm lượng narration (gốc +1.5dB).
    volume: hệ số "Âm lượng giọng kể" user chọn (0.8-2.0, mặc định 1.15) —
    nhân THÊM sau bước auto-match (có limiter chống clip).

    parts: kịch bản [{"start","end","mode","text"}] — mốc theo TIMELINE VIDEO
    GỐC (app/ai/recap.py đã validate). Chỉ part mode="narrate" được đọc.
    clip_segments: các khúc của clip -> mốc part được ÁNH XẠ về timeline đầu ra.
    voice: giọng edge-tts hoặc "gemini:...". lang: để chọn giọng dự phòng.
    pace: nhịp kể "slow"/"normal"/"fast" (Cài đặt Reup) -> rate edge-tts
    (-3%/0%/+4%); giọng Gemini không có rate -> prepend CHỈ DẪN kể chuyện vào
    text TTS (chỉ dẫn không lọt narrate_events/phụ đề). Fit window (atempo)
    tự bù nên mốc part vẫn khít; WordBoundary thu theo audio thật (đã áp
    rate) nên mốc từng từ vẫn đúng.
    pitch: TÔNG GIỌNG "low"/"normal"/"high" (Cài đặt Reup) -> pitch edge-tts
    -18Hz/+0Hz/+18Hz (trầm ấm hơn / giữ nguyên / sáng cao hơn). Giọng Gemini
    KHÔNG hỗ trợ pitch -> bỏ qua (cả đường fallback edge của Gemini).

    narrate_events = [{"start","end","text","duck"[,"words"]}] trên timeline
    ĐẦU RA (chưa speed) — dùng cho phụ đề thuyết minh + duck_ranges.
    "end" = mép HẾT TIẾNG THẬT của giọng AI (đo audio, KHÔNG phải hết part)
    -> phụ đề chỉ phủ đúng khoảng nói. "duck" = [a, b] khoảng HẠ tiếng gốc
    (speech-0.3s .. speech+0.35s, kẹp trong part) — phần còn lại của part
    narrate tiếng gốc TRỞ LẠI bình thường (hết 'khoảng chết' câm lặng).
    "words" = [[start, end, cụm], ...] mốc phụ đề narrate trên timeline clip.
    MẶC ĐỊNH = CÂU-CỤM (2-4 từ/nhóm) phân bố ĐỀU theo ĐỘ DÀI AUDIO THẬT
    (D_final đo bằng ffprobe sau MỌI filter) — ít trôi hơn karaoke từng từ vì
    KHÔNG phụ thuộc WordBoundary. Bật RECAP_WORD_LEVEL_CAPTION -> mốc TỪNG TỪ
    thật (WordBoundary edge-tts, scale theo D_final/D_nat đo thật). Giọng
    el/Gemini (và edge-fallback của chúng) KHÔNG có word boundary -> 🔁 STT
    WORD-SYNC: chép lời word-level CHÍNH audio đã render bằng Groq whisper
    (_stt_part_words, cache theo hash audio, timeout 20s) rồi dùng MỐC STT +
    CHỮ kịch bản (_align_stt_words) — khớp cả giọng cảm xúc đọc nhanh chậm
    thất thường; STT fail -> silencedetect/chia đều như cũ (progress cảnh
    báo '⚠ Part N: phụ đề căn ước lượng').
    🔒 HẬU KIỂM BẮT BUỘC (mọi nguồn mốc): mỗi event mang "clamped"=True —
    cue "words" đã qua LỚP 2 (_cue_speech_bias: cả part trượt đều >0.12s so
    speech onset thật -> dịch cả cụm) rồi LỚP 1 (_clamp_cues_to_speech:
    clamp cứng vào khoảng CÓ TIẾNG đo silencedetect -32dB/0.18 trên wav part
    cuối; cue ngoài tiếng bị XÓA). "clamped" + "words" rỗng -> caller KHÔNG
    fallback chia ký tự (thà không chữ còn hơn chữ sai lúc).
    WAV 48kHz mono dài ĐÚNG tổng độ dài clip.

    ĐỘ BỀN + CÂN ÂM LƯỢNG (sửa lỗi user):
    - Part TTS lỗi (edge-tts chập chờn THEO ĐỢT) -> thử lại thêm 1 LƯỢT VÉT
      riêng các part hỏng; vẫn hỏng -> BỎ part khỏi narrate_events LUÔN
      (caller sẽ KHÔNG duck/không phụ đề part đó -> tiếng gốc giữ nguyên,
      KHÔNG còn 'khoảng chết' câm lặng giữa clip như trước).
    - MỌI part lỗi -> raise (không xuất clip thuyết minh câm).
    - CÂN ÂM LƯỢNG THEO NGUỒN: đo loudness THẬT của tiếng gốc video (đoạn
      dài nhất của clip) -> loudnorm narration về mức gốc +1.5dB (kẹp
      [-27,-9] LUFS). Chuẩn cứng -16 LUFS cũ vẫn CHÌM khi video nguồn to
      (-6..-10 LUFS, nhạc/gaming) — lỗi 'giọng bé' user gặp thật. loudnorm
      lỗi -> KHÔNG bỏ qua: fallback gain thô theo chênh loudness đo được.
    - Lời narrate TRÀN khung: atempo trần 1.28, vẫn tràn -> MƯỢN THỜI GIAN
      từ quãng orig kế (max min(3s, 40% quãng) — narr_events giãn theo nên
      duck/phụ đề tự khớp); part cuối không mượn được -> atempo tới 1.4
      rồi mới trim + fade (hết cảnh CỤT CHỮ giữa câu).
    - Giọng chính fail hết retry -> thử GIỌNG DỰ PHÒNG cùng ngôn ngữ trước
      khi bỏ part (server MS chập chờn theo GIỌNG là có thật).
    - Part narrate ĐẦU TIÊN (hook) đọc nhanh hơn nhịp nền +2% (năng lượng
      mở đầu) — chỉ đường edge-tts (Gemini không có rate).
    """
    def prog(p: float, msg: str = "") -> None:
        if on_progress:
            on_progress(min(1.0, max(0.0, p)), msg)

    total = sum(float(e) - float(s) for s, e in (clip_segments or []))
    if total <= 0.2:
        raise ValueError("Clip không có đoạn nào để thuyết minh.")
    voice = (voice or "").strip() or default_voice(lang) or "en-US-JennyNeural"

    # Part narrate -> mốc đầu ra; part rơi ngoài clip/khung quá hẹp -> bỏ
    narr: list[dict] = []
    for p in parts or []:
        if (p.get("mode") != "narrate"
                or not str(p.get("text") or "").strip()):
            continue
        a = _map_to_output(float(p["start"]), clip_segments)
        b = _map_to_output(float(p["end"]), clip_segments)
        if a is None or b is None or b - a < 0.8:
            continue
        # RAW = lời narrate GỐC (có thể chứa audio tag [excited]/CAPS khi AI
        # đạo diễn chèn cảm xúc). _raw để gửi TTS ElevenLabs v3; "text" = bản
        # SẠCH (bỏ tag + hạ CAPS) dùng cho PHỤ ĐỀ + word timing.
        from app.ai.recap import _strip_audio_tags
        raw = str(p["text"]).strip()
        narr.append({"start": round(a, 3), "end": round(b, 3),
                     "text": _strip_audio_tags(raw), "_raw": raw})
    if not narr:
        raise RuntimeError("Kịch bản không có part thuyết minh hợp lệ.")

    # AUDIO TAG CẢM XÚC (ElevenLabs v3): CHỈ khi user BẬT emotion + giọng el:
    # thì gửi bản CÓ tag cho v3 đọc; mọi đường khác (v2/edge/Gemini/tắt
    # emotion) nhận bản ĐÃ STRIP (edge/gemini không hiểu tag -> đọc to
    # "[excited]" nếu không strip). Phụ đề LUÔN dùng n["text"] đã strip.
    _use_v3 = bool(emotion and voice.startswith("el:"))
    # texts = ĐẦU VÀO TTS: có tag nếu el v3 + emotion, ngược lại sạch.
    texts = [(n["_raw"] if _use_v3 else n["text"]) for n in narr]
    rate = recap_pace_rate(pace)
    pitch_hz = recap_pitch_hz(pitch)    # tông giọng (chỉ đường edge-tts)
    with tempfile.TemporaryDirectory(prefix="recap_") as td:
        mp3s = [os.path.join(td, f"n{i}.mp3") for i in range(len(narr))]
        done = {"n": 0}

        def _tts_done(_i: int) -> None:
            done["n"] += 1
            prog(0.05 + 0.60 * done["n"] / max(1, len(narr)),
                 f"Thu giọng đoạn {done['n']}/{len(narr)}...")

        word_lists: list[list] = [[] for _ in narr]
        if voice.startswith("el:"):
            # ElevenLabs TTS KHÔNG trả word boundary -> word_lists rỗng, phụ
            # đề narrate dùng CÂU-CỤM chia theo D_final (tái dùng đường Gemini).
            # ElevenLabs không có rate/pitch -> bỏ qua (fit window atempo tự
            # bù). _synth_all_eleven tự đổi cả track sang edge-tts khi hết hạn
            # mức (đường đó cũng không thu words -> phụ đề vẫn câu-cụm).
            # emotion BẬT -> model eleven_v3 (đọc audio tag [excited]/CAPS);
            # tắt -> multilingual_v2 mặc định (texts đã STRIP). v3 lỗi/chưa mở
            # -> _eleven_tts tự lùi v2 (khi đó tag còn trong text nhưng v2 chỉ
            # đọc phần lời, tag lọt ít — chấp nhận vì hiếm; sub vẫn sạch).
            el_model = _ELEVEN_MODEL_V3 if _use_v3 else ""
            _emo = " + cảm xúc v3" if _use_v3 else ""
            prog(0.05, f"Thu giọng {len(narr)} đoạn (ElevenLabs TTS{_emo})...")
            ok = _synth_all_eleven(texts, voice, mp3s, norm_lang(lang),
                                   on_done=_tts_done,
                                   on_msg=lambda m: prog(0.06, m),
                                   edge_rate=rate, model=el_model,
                                   # đường fallback edge nhận bản ĐÃ strip tag
                                   edge_texts=[n["text"] for n in narr])
        elif voice.startswith("gemini:"):
            # Gemini TTS KHÔNG trả word boundary -> word_lists rỗng, phụ đề
            # narrate fallback chia theo ký tự (m1._recap_caption_cues).
            # (_synth_all_gemini có thể tự đổi cả track sang edge-tts khi hết
            # hạn mức — đường đó cũng không thu words, chấp nhận fallback.)
            # Gemini không có rate -> prepend chỉ dẫn kể chuyện vào text TTS
            # (chỉ khi gọi Gemini — narr events GIỮ text gốc nên chỉ dẫn
            # không lọt phụ đề/words; fallback edge cũng dùng text gốc).
            prog(0.05, f"Thu giọng {len(narr)} đoạn (Gemini TTS)...")
            ok = _synth_all_gemini(texts, voice, mp3s, norm_lang(lang),
                                   on_done=_tts_done,
                                   on_msg=lambda m: prog(0.06, m),
                                   edge_rate=rate,
                                   gemini_prefix=gemini_narrate_prefix(lang))
        else:
            prog(0.05, f"Thu giọng {len(narr)} đoạn (edge-tts)...")
            # Câu HOOK (part narrate đầu) đọc nhanh hơn +2% cho có năng lượng
            rates = [rate] * len(narr)
            if rates:
                rates[0] = _bump_rate(rate, 2)
            ok, word_lists = asyncio.run(_synth_all_words(
                texts, voice, mp3s, on_done=_tts_done, rate=rates,
                pitch=pitch_hz))
            # LƯỢT VÉT: server MS hay lỗi NoAudioReceived THEO ĐỢT — nghỉ
            # ngắn rồi thử lại RIÊNG các part hỏng 1 lần nữa (đo thật cho
            # thấy đợt lỗi qua nhanh; trước đây part hỏng bị bỏ luôn ->
            # khoảng thuyết minh bị câm).
            fails = [i for i, k in enumerate(ok) if not k and texts[i].strip()]
            if fails:
                prog(0.62, f"Thu lại {len(fails)} đoạn giọng bị lỗi mạng...")
                time.sleep(2.5)
                ok2, wl2 = asyncio.run(_synth_all_words(
                    [texts[i] for i in fails], voice,
                    [mp3s[i] for i in fails],
                    rate=[rates[i] for i in fails], pitch=pitch_hz))
                for j, i in enumerate(fails):
                    if ok2[j]:
                        ok[i] = True
                        word_lists[i] = wl2[j]
            # GIỌNG DỰ PHÒNG: giọng chính fail hết retry (dịch vụ chập chờn
            # THEO GIỌNG) -> thử giọng hot khác CÙNG ngôn ngữ trước khi bỏ
            # part (bỏ part = mất đoạn thuyết minh — lỗi user gặp thật).
            fails = [i for i, k in enumerate(ok)
                     if not k and texts[i].strip()]
            if fails:
                fb = _recap_backup_voice(lang, voice)
                if fb:
                    prog(0.63, f"Giọng chính lỗi {len(fails)} đoạn -> thử "
                               f"giọng dự phòng ({fb})...")
                    ok3, wl3 = asyncio.run(_synth_all_words(
                        [texts[i] for i in fails], fb,
                        [mp3s[i] for i in fails],
                        rate=[rates[i] for i in fails], pitch=pitch_hz))
                    for j, i in enumerate(fails):
                        if ok3[j]:
                            ok[i] = True
                            word_lists[i] = wl3[j]
        if not any(ok):
            raise RuntimeError(
                "TTS thuyết minh thất bại toàn bộ (mạng/giọng lỗi) — "
                "thử lại hoặc đổi giọng đọc trong mẫu.")

        fitted: list[tuple[float, str]] = []
        kept: list[dict] = []          # CHỈ part có audio thật -> narrate_events
        for i, n in enumerate(narr):
            if not ok[i]:
                continue
            wav = os.path.join(td, f"f{i}.wav")
            window = n["end"] - n["start"]
            # ---- MƯỢN THỜI GIAN: lời đọc dài hơn khung (dù atempo trần
            # 1.28) -> KÉO DÀI window sang đầu quãng orig kế (tối đa
            # min(3s, 40% quãng)) thay vì TRIM CỤT CHỮ giữa câu (lỗi user
            # gặp thật). n["end"] giãn theo -> duck_ranges + phụ đề (caller
            # dùng narr_events) tự khớp; quãng orig bị mượn sẽ duck thêm —
            # chấp nhận. Part cuối/không còn chỗ mượn -> nới atempo 1.4
            # rồi mới đành trim + fade.
            dur0 = probe_duration(mp3s[i])
            nxt_start = narr[i + 1]["start"] if i + 1 < len(narr) else total
            room = max(0.0, min(nxt_start, total) - n["end"])
            tempo_max = _RECAP_TEMPO_MAX
            if dur0 > 0 and dur0 / _RECAP_TEMPO_MAX > window + 0.05:
                need = dur0 / _RECAP_TEMPO_MAX - window
                borrow = min(_BORROW_MAX_S, _BORROW_MAX_FRAC * room,
                             need + 0.1)
                if borrow > 0.05:
                    n["end"] = round(min(n["end"] + borrow, total), 3)
                    window = n["end"] - n["start"]
                if dur0 / _RECAP_TEMPO_MAX > window + 0.05:
                    tempo_max = _RECAP_TEMPO_MAX_TAIL
            try:
                d_final, d_nat, tempo = _fit_recap_chunk(
                    mp3s[i], wav, window, tempo_max=tempo_max)
            except RuntimeError:
                continue                    # part hỏng -> bỏ riêng part đó
            fitted.append((n["start"], wav))
            kept.append(n)                  # có audio thật -> mới được duck/sub
            # ---- MỐC PHỤ ĐỀ khớp AUDIO THẬT (sửa lỗi 'chữ trôi') ----
            # ĐO D_final (độ dài file wav THẬT sau atempo+atrim) rồi ánh xạ mốc
            # theo tỉ lệ THẬT D_final/D_nat — KHÔNG chia theo tempo dự kiến
            # (ffmpeg làm tròn/đổi mẫu nên dur/k lệch dần). offset = n["start"]
            # = ĐÚNG mốc adelay của part trong _mix_track (1 biến, không tính 2
            # nơi). loudnorm/gain sau vòng này KHÔNG đổi độ dài nên D_final vẫn
            # đúng cho track cuối.
            scale = (d_final / d_nat) if d_nat > 0.01 else (1.0 / tempo)
            wl = word_lists[i] if i < len(word_lists) else []
            # ---- 🔁 STT WORD-SYNC: part KHÔNG có WordBoundary (el/Gemini/
            # edge-fallback của chúng) -> CHÉP LỜI word-level CHÍNH file wav
            # ĐÃ RENDER (đã atempo -> mốc STT ở đúng thang D_final, KHÔNG
            # cần scale) rồi lấy MỐC của STT + CHỮ của kịch bản. STT lỗi/
            # không key/timeout/lệch từ >40% -> stt_wl=None, đi tiếp đường
            # silencedetect + chia ký tự như cũ (không tệ hơn hiện tại).
            stt_wl = None
            if not wl and str(n["text"] or "").strip():
                raw_stt = _stt_part_words(wav, lang)
                if raw_stt:
                    stt_wl = _align_stt_words(n["text"], raw_stt)
                    if stt_wl:
                        prog(0.65 + 0.25 * (i + 1) / len(narr),
                             "Căn phụ đề theo giọng thật (STT)...")
                if not stt_wl:
                    # LỚP 3 — MINH BẠCH: không WordBoundary + STT fail/không
                    # key -> mốc phụ đề part này là ƯỚC LƯỢNG (silencedetect/
                    # chia đều); lớp clamp vẫn khóa 'không chữ ngoài lúc nói'
                    # nhưng muốn khớp TỪNG TỪ thì cần key Groq.
                    prog(0.65 + 0.25 * (i + 1) / len(narr),
                         f"⚠ Part {i + 1}: phụ đề căn ước lượng — dán key "
                         "Groq để khớp từng từ")
            # KHOẢNG CÓ TIẾNG THẬT [speech_a, speech_b]: mép từ ĐẦU/CUỐI
            # (WordBoundary) scale theo D_final/D_nat, kẹp trong D_final. Neo
            # phụ đề vào ĐÚNG lúc bắt đầu/kết thúc có tiếng (bỏ khoảng lặng/hơi
            # thở đầu-đuôi edge-tts hay thêm). Không words (Gemini) -> mốc STT
            # nếu có; không nốt -> cả part.
            speech_a, speech_b = 0.0, d_final
            if wl:
                fa = wl[0][0] * scale
                lb = wl[-1][1] * scale
                if 0.0 <= fa < d_final:
                    speech_a = fa
                if speech_a + 0.1 < lb < d_final:
                    speech_b = lb
            elif stt_wl:
                fa = float(stt_wl[0][0])
                lb = float(stt_wl[-1][1])
                if 0.0 <= fa < d_final:
                    speech_a = fa
                if speech_a + 0.1 < lb:
                    speech_b = min(lb, d_final)
            # ---- DUCK CHỈ ĐÚNG LÚC AI NÓI (sửa 'khoảng chết' câm lặng) ----
            # Trước đây caller duck CẢ PART narrate — lời LLM thường ngắn hơn
            # part -> giọng AI hết mà tiếng gốc vẫn tắt = im lặng chết cả
            # quãng. Giờ mỗi event mang "duck" = [speech_start-0.3,
            # speech_end+0.35] KẸP TRONG PART (speech đo THẬT từ audio);
            # phần còn lại của part tiếng gốc TRỞ LẠI bình thường. n["end"]
            # cũng co về mép HẾT TIẾNG -> phụ đề narrate (kể cả fallback
            # câu/ký tự của caller) chỉ phủ đúng khoảng nói, không phủ đuôi.
            part_end = n["end"]
            sp_a = n["start"] + speech_a
            sp_b = min(part_end, n["start"] + speech_b)
            n["duck"] = [round(max(n["start"], sp_a - 0.3), 3),
                         round(min(part_end, sp_b + 0.35), 3)]
            n["end"] = round(sp_b, 3)
            if not _recap_word_level():
                # MẶC ĐỊNH: câu-cụm 2-4 từ. CĂN theo GIỌNG THẬT:
                #  - edge-tts (CÓ WordBoundary trong `wl`): tags đã strip nên
                #    giọng đọc đều -> chia ĐỀU theo phần có tiếng (như cũ).
                #  - el/Gemini (KHÔNG word timestamp -> `wl` rỗng): ƯU TIÊN
                #    mốc TỪNG TỪ THẬT từ STT (`stt_wl` — chữ kịch bản, giờ
                #    STT) gom thành cụm 2-4 từ -> khớp cả khi giọng cảm xúc
                #    đọc nhanh chậm thất thường. STT fail -> DÒ đoạn nói
                #    bằng silencedetect trên audio ĐÃ RENDER (wav) rồi rải
                #    cụm chữ vào các đoạn có tiếng; không dò được -> chia đều
                #    (đúng hành vi cũ).
                grp = None
                if stt_wl:
                    grp = _phrase_groups_from_words(stt_wl, n["start"])
                if not grp and not wl:
                    segs_sp = _detect_speech_segments(wav, d_final)
                    if len(segs_sp) >= 2:   # ≥2 đoạn -> có ngắt đáng kể
                        grp = _phrase_groups_by_speech(
                            n["text"], n["start"], segs_sp)
                if not grp:                 # edge / nói liền / dò hỏng -> đều
                    grp = _phrase_groups_even(n["text"],
                                              n["start"] + speech_a,
                                              speech_b - speech_a)
                if grp:
                    n["words"] = grp
            elif wl:
                # WORD-LEVEL (tuỳ chọn): mốc từng từ scale theo D_final/D_nat.
                out_w = []
                for a, b, wtxt in wl:
                    a2, b2 = a * scale, b * scale
                    if a2 >= d_final - 0.01:  # từ rơi vào phần bị cắt -> bỏ
                        break
                    out_w.append([round(n["start"] + a2, 3),
                                  round(n["start"] + min(b2, d_final), 3),
                                  wtxt])
                if out_w:
                    n["words"] = out_w
            elif stt_wl:
                # WORD-LEVEL từ STT: mốc đã ở thang D_final -> cộng offset.
                out_w = []
                for a, b, wtxt in stt_wl:
                    if a >= d_final - 0.01:   # từ rơi vào phần bị cắt -> bỏ
                        break
                    out_w.append([round(n["start"] + a, 3),
                                  round(n["start"] + min(b, d_final), 3),
                                  wtxt])
                if out_w:
                    n["words"] = out_w
            # ==== 🔒 KHÓA CỨNG ĐỘ CHÍNH XÁC PHỤ ĐỀ (hậu kiểm BẮT BUỘC) ====
            # LỚP 2 (bias) + LỚP 1 (clamp) trên wav part CUỐI CÙNG — chính là
            # audio được adelay vào track (loudnorm/gain sau đó KHÔNG đổi
            # thời gian). MỌI đường mốc (WordBoundary/STT/silencedetect/chia
            # đều — kể cả word-level không dựng được cue) đều qua đây;
            # orig cues KHÔNG (lời gốc theo transcript video — vốn khớp).
            base = n.get("words") or []
            if not base and str(n["text"] or "").strip():
                # đường word-level không ra cue (hiếm) -> vẫn dựng cụm ước
                # lượng để clamp — đảm bảo part có chữ nếu có tiếng khớp
                base = _phrase_groups_even(n["text"], n["start"] + speech_a,
                                           speech_b - speech_a)
            speech_real = _detect_speech_segments(
                wav, d_final, noise_db=_CLAMP_NOISE_DB,
                min_sil=_CLAMP_MIN_SIL)
            if not speech_real:
                # không dò được khoảng im (nói liền mạch / ffmpeg lỗi) ->
                # khoảng tiếng = [speech_a, speech_b] đã đo ở trên
                speech_real = [(max(0.0, speech_a),
                                min(d_final, max(speech_a + 0.1, speech_b)))]
            off = n["start"]
            fcues = [[float(a) - off, float(b) - off, t] for a, b, t in base]
            bias = _cue_speech_bias(fcues, speech_real)
            if bias:                       # LỚP 2: shift cả cụm đúng hiệu lệch
                fcues = [[a + bias, b + bias, t] for a, b, t in fcues]
            fcues = _clamp_cues_to_speech(fcues, speech_real)   # LỚP 1
            n["words"] = [[round(a + off, 3), round(b + off, 3), t]
                          for a, b, t in fcues]
            # cờ cho caller (m1._recap_caption_cues): cue ĐÃ hậu kiểm —
            # words rỗng nghĩa là XÓA HẾT (không fallback chia ký tự nữa).
            n["clamped"] = True
            prog(0.65 + 0.25 * (i + 1) / len(narr), "Khớp thời gian...")

        # Part TTS/fit hỏng KHÔNG được nằm trong narrate_events: caller dùng
        # events để TẮT tiếng gốc (duck) + vẽ phụ đề — part không có giọng mà
        # vẫn duck sẽ thành KHOẢNG CHẾT câm lặng (lỗi user gặp thật). Bỏ part
        # -> đoạn đó giữ nguyên tiếng gốc, người xem không thấy hụt.
        if not kept:
            raise RuntimeError(
                "TTS thuyết minh thất bại toàn bộ (mạng/giọng lỗi) — "
                "thử lại hoặc đổi giọng đọc trong mẫu.")

        prog(0.92, "Ghép track thuyết minh...")
        Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
        _mix_track(fitted, round(total, 3), str(out_wav))
        # ---- CÂN ÂM LƯỢNG THEO NGUỒN (sửa lỗi 'giọng AI cực bé') ----
        # 1) ĐO loudness THẬT của tiếng gốc trong clip (đoạn dài nhất, mẫu
        #    tối đa 60s): video nhạc/gaming thường -6..-10 LUFS -> chuẩn cứng
        #    -16 LUFS cũ vẫn chìm nghỉm dưới tiếng gốc.
        # 2) loudnorm narration về mức GỐC + 1.5dB (kẹp [-27,-9] LUFS;
        #    TP=-1.5 chống clip). Không đo được nguồn -> giữ mặc định -16.
        # 3) loudnorm LỖI -> KHÔNG lặng lẽ bỏ qua như trước (track giữ nguyên
        #    bé tí): fallback GAIN THÔ theo chênh loudness đo được + limiter.
        target = -16.0
        src_i = None
        if src_path and os.path.exists(str(src_path)) and clip_segments:
            s0, e0 = max(((float(s), float(e)) for s, e in clip_segments),
                         key=lambda p: p[1] - p[0])
            src_i = measure_loudness(src_path, start=s0,
                                     dur=min(e0 - s0, 60.0))
        if src_i is not None:
            target = max(_RECAP_TARGET_MIN,
                         min(_RECAP_TARGET_MAX, src_i + _RECAP_HEADROOM_DB))
        prog(0.94, f"Cân âm lượng giọng kể (gốc "
                   f"{src_i:.1f} LUFS -> {target:.1f})..." if src_i is not None
             else "Cân âm lượng giọng kể...")
        try:
            _loudnorm_wav(str(out_wav), i_lufs=target)
        except (RuntimeError, OSError):
            prog(0.95, "loudnorm lỗi -> bù âm lượng thô theo chênh đo được...")
            try:
                cur = measure_loudness(str(out_wav))
                gain = (target - cur) if cur is not None else 6.0
                _gain_wav(str(out_wav),
                          gain_db=max(-12.0, min(20.0, gain)))
            except (RuntimeError, OSError):
                prog(0.95, "CẢNH BÁO: không cân được âm lượng giọng kể "
                           "(ffmpeg lỗi) — giọng có thể bé.")
        # Slider "Âm lượng giọng kể" (80-200%, mặc định 115%) nhân THÊM sau
        # auto-match — user chê bé/to thì tự nêm; limiter chống clip.
        vol = max(0.5, min(2.5, float(volume or 1.0)))
        if abs(vol - 1.0) > 0.02:
            try:
                _gain_wav(str(out_wav), factor=vol)
            except (RuntimeError, OSError):
                pass                      # best-effort — track đã auto-match

    prog(1.0, "Xong thuyết minh")
    for _n in kept:                     # _raw chỉ dùng nội bộ (TTS v3) -> bỏ
        _n.pop("_raw", None)
    return str(out_wav), kept


# ------------------------------------------------------------------
# API chính
# ------------------------------------------------------------------
def build_dub_track(transcript: dict, clip_segments: list, target_lang: str,
                    voice: str, out_wav: str | Path,
                    llm_translate: bool = True,
                    dub_mode: str = "natural",
                    on_progress: Optional[Callable[[float, str], None]] = None,
                    ) -> tuple[str, list[dict], float]:
    """
    Tạo track lồng tiếng cho clip. Trả (đường_dẫn_wav, dub_segments, stretch):
      dub_segments = [{"start","end","text"}] trên timeline ĐẦU RA (text đã dịch)
        — dùng cho phụ đề khớp bản dịch. WAV 48kHz mono, dài ĐÚNG tổng độ dài clip.
      stretch = hệ số KÉO DÀI clip (>= 1.0). Chỉ khác 1.0 ở chế độ "video":
        nếu tổng lời đọc tự nhiên dài hơn khung, trả ratio để export làm CHẬM
        ĐỀU cả clip video (+ dub) cho khớp. Các chế độ khác luôn trả 1.0.

    dub_mode:
      "natural" (mặc định) — đọc tốc độ THƯỜNG, mỗi câu neo ĐÚNG start gốc;
                 chỉ tăng tốc khi lời đọc sắp ĐÈ sang câu kế (trần 1.5). Nghe
                 đều giọng, khớp mốc, không giật.
      "tight"  — ép mỗi câu lọt khung riêng của nó (khớp sát, có thể nhanh/giật).
      "video"  — KHÔNG tăng tốc giọng (đọc hoàn toàn tự nhiên). Tính hệ số kéo
                 dài tổng: nếu lời đọc dài hơn khung, trả stretch > 1 để export
                 CO GIÃN NHẸ đoạn video cho khớp giọng (như pyVideoTrans) —
                 mượt nhất, giọng tự nhiên nhất. Dub track vẫn dựng trên timeline
                 gốc (dài = total); export nhân đều cả video lẫn dub theo stretch.
    """
    mode = str(dub_mode or "natural").lower()
    tight = mode.startswith("t")
    video_fit = mode.startswith("v")
    def prog(p: float, msg: str = "") -> None:
        if on_progress:
            on_progress(min(1.0, max(0.0, p)), msg)

    target_lang = norm_lang(target_lang)
    voice = voice or default_voice(target_lang)
    if not voice:
        raise ValueError(f"Ngôn ngữ lồng tiếng không hỗ trợ: {target_lang}")
    total = sum(float(e) - float(s) for s, e in (clip_segments or []))
    if total <= 0.2:
        raise ValueError("Clip không có đoạn nào để lồng tiếng.")

    prog(0.02, "Gom câu thoại...")
    chunks = _remap_segments(transcript, clip_segments)
    if not chunks:
        raise RuntimeError("Không có lời thoại trong đoạn clip để lồng tiếng.")

    # --- Dịch (bỏ qua nếu cùng ngôn ngữ) ---
    src_lang = norm_lang((transcript or {}).get("language", ""))
    if llm_translate and src_lang != target_lang:
        prog(0.08, "AI đang dịch lời thoại...")
        texts = _translate_chunks(chunks, target_lang)
    else:
        texts = [c["text"] for c in chunks]

    # AN TOÀN: số bản dịch phải KHỚP số cụm (LLM có thể trả thiếu/thừa phần tử).
    # Map theo index, cụm thiếu -> dùng nguyên văn gốc; thừa -> cắt bỏ. Nhờ vậy
    # KHÔNG cụm nào bị lệch mốc dù bản dịch lỗi.
    if len(texts) != len(chunks):
        texts = [(texts[i] if i < len(texts) and str(texts[i]).strip()
                  else chunks[i]["text"]) for i in range(len(chunks))]

    with tempfile.TemporaryDirectory(prefix="dub_") as td:
        # --- TTS song song ---
        mp3s = [os.path.join(td, f"c{i}.mp3") for i in range(len(chunks))]
        done = {"n": 0}

        def _tts_done(_i: int) -> None:
            done["n"] += 1
            prog(0.15 + 0.55 * done["n"] / max(1, len(chunks)),
                 f"Đang đọc lời thoại ({done['n']}/{len(chunks)})...")

        if voice.startswith("el:"):
            # ElevenLabs TTS: tuần tự; 2 cụm đầu lỗi -> tự chuyển CẢ track
            # sang edge-tts giọng dự phòng (on_msg báo lên progress).
            prog(0.15, f"Đang đọc {len(chunks)} câu (ElevenLabs TTS)...")
            ok = _synth_all_eleven(texts, voice, mp3s, target_lang,
                                   on_done=_tts_done,
                                   on_msg=lambda m: prog(0.16, m))
        elif voice.startswith("gemini:"):
            # Gemini TTS: tuần tự (hạn mức thấp); 2 cụm đầu lỗi -> tự chuyển
            # CẢ track sang edge-tts giọng dự phòng (on_msg báo lên progress).
            prog(0.15, f"Đang đọc {len(chunks)} câu (Gemini TTS)...")
            ok = _synth_all_gemini(texts, voice, mp3s, target_lang,
                                   on_done=_tts_done,
                                   on_msg=lambda m: prog(0.16, m))
        else:
            prog(0.15, f"Đang đọc {len(chunks)} câu (edge-tts)...")
            ok = asyncio.run(_synth_all(texts, voice, mp3s,
                                        on_done=_tts_done))

        # --- Khớp thời gian từng cụm ---
        # gap[i] = khoảng cách từ start cụm i tới start cụm kế (hoặc hết clip)
        # trên TIMELINE GỐC.
        gaps = []
        for i, c in enumerate(chunks):
            nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else total
            gaps.append(max(0.2, min(nxt, total) - c["start"] - 0.03))

        # CHẾ ĐỘ "video": tính hệ số kéo dài tổng. Đo độ dài ĐỌC TỰ NHIÊN từng
        # cụm (chỉ probe mp3, không encode). stretch = max(dur/gap) — giãn ĐỀU
        # cả timeline (mốc + khung) theo stretch thì MỌI cụm lọt khung tự nhiên.
        # KHÁC 2 chế độ kia: dub track dựng trên timeline ĐÃ GIÃN (dài total*
        # stretch), export chỉ việc làm chậm video theo stretch, KHÔNG atempo dub.
        stretch = 1.0
        if video_fit:
            for i in range(len(chunks)):
                if not ok[i]:
                    continue
                d = probe_duration(mp3s[i])
                if d > gaps[i] + 0.02:
                    stretch = max(stretch, d / gaps[i])
            stretch = min(_MAX_STRETCH, round(stretch, 4))

        # Mốc cụm trên timeline ĐÃ GIÃN — CHỈ dùng để NEO track lồng tiếng
        # (WAV dài total*stretch, khớp với video sau khi export setpts giãn).
        out_start = [round(c["start"] * stretch, 3) for c in chunks]
        out_total = round(total * stretch, 3)
        # dub_segments cho PHỤ ĐỀ giữ mốc GỐC (chưa giãn): phụ đề .ass đốt vào
        # video TRƯỚC bước setpts nên phải khớp timeline gốc; setpts sẽ giãn chữ
        # cùng video (y như cơ chế `speed`). Nếu giãn sẵn ở đây sẽ lệch gấp đôi.
        dub_segments = [{"start": c["start"], "end": c["end"], "text": texts[i]}
                        for i, c in enumerate(chunks)]

        # --- Khớp/encode từng cụm ---
        # Neo mỗi cụm vào start (đã giãn nếu video). Cụm TTS lỗi -> BỎ RIÊNG cụm
        # đó, các cụm khác GIỮ ĐÚNG mốc (không dồn/lệch).
        fitted: list[tuple[float, str]] = []
        for i, c in enumerate(chunks):
            if not ok[i]:                   # cụm này TTS hỏng/rỗng -> bỏ, giữ mốc
                prog(0.70 + 0.15 * (i + 1) / len(chunks), "Khớp thời gian...")
                continue
            window = c["end"] - c["start"]
            gap = gaps[i]
            wav = os.path.join(td, f"f{i}.wav")
            if video_fit:
                # Khung ĐÃ GIÃN = gap*stretch. stretch chọn theo cụm chật nhất
                # nên gap*stretch >= dur mọi cụm -> đọc y nguyên, KHÔNG tăng tốc.
                # Chỉ khi stretch bị TRẦN (_MAX_STRETCH) mà cụm vẫn quá dài thì
                # _fit_chunk mới tăng tốc NHẸ phần dư để không đè cụm kế.
                lim = gap * stretch
                fit_budget, fit_hard = lim, lim
            else:
                # budget (Tự nhiên): tới sát start cụm kế -> chỉ tăng tốc khi lời
                # đọc sẽ ĐÈ sang cụm sau. Chặn cứng hard_max để KHÔNG bao giờ đè.
                fit_budget, fit_hard = gap, max(window, gap)
            try:
                _fit_chunk(mp3s[i], wav, fit_budget, fit_hard,
                           tight=tight, window=window)
            except RuntimeError:            # file TTS hỏng lúc xử lý -> bỏ cụm
                prog(0.70 + 0.15 * (i + 1) / len(chunks), "Khớp thời gian...")
                continue
            fitted.append((out_start[i], wav))
            prog(0.70 + 0.15 * (i + 1) / len(chunks), "Khớp thời gian...")

        # --- Ghép về 1 track dài đúng bằng clip (đã giãn nếu chế độ video) ---
        # (fitted rỗng = mọi cụm TTS lỗi -> track im lặng đúng độ dài, KHÔNG vỡ)
        prog(0.88, "Ghép track lồng tiếng...")
        Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
        _mix_track(fitted, out_total, str(out_wav))

    prog(1.0, "Xong lồng tiếng")
    return str(out_wav), dub_segments, stretch
