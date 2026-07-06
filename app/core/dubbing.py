"""
LỒNG TIẾNG AI (dubbing) bằng edge-tts (giọng Microsoft Neural — hay, tự nhiên, free).

Quy trình build_dub_track:
  1. Lấy các câu transcript nằm trong clip_segments, ÁNH XẠ mốc về timeline đầu ra
     (giống captions._remap_words — clip ghép nhiều khúc, bỏ khúc thừa).
  2. GOM các segment liền kề (gap < 0.4s) thành CÂU/cụm -> giọng đọc tự nhiên.
  3. DỊCH 1 lần tất cả cụm bằng LLM (JSON mảng cùng số phần tử, văn nói NGẮN GỌN
     lọt khung thời gian). target == ngôn ngữ gốc -> bỏ qua dịch.
  4. TTS từng cụm (edge-tts, song song tối đa 4 cụm/lượt).
  5. KHỚP THỜI GIAN: cụm đọc dài hơn khung -> tăng tốc atempo (≤1.35, chia tầng);
     ngắn hơn -> giữ nguyên (im lặng tự đệm). Ghép: anullsrc đúng tổng độ dài
     + adelay từng cụm theo start + amix -> 1 file WAV 48kHz dài ĐÚNG bằng clip.

Chỉ dùng subprocess ffmpeg (settings.FFMPEG_PATH) — không thêm dependency audio.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from config import DATA_DIR, settings

_CREATE_NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0

# Gom 2 câu transcript liền kề thành 1 cụm nếu hở dưới ngưỡng này (giây)
_JOIN_GAP = 0.4
# Tăng tốc tối đa cho phép để nhét lời đọc vào khung thời gian (nghe vẫn tự nhiên)
_MAX_TEMPO = 1.35
# Số cụm TTS chạy song song (edge-tts qua mạng)
_TTS_PARALLEL = 4

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
    "en-US-BrianNeural", "en-US-SteffanNeural",
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
    """TOÀN BỘ giọng edge-tts của ngôn ngữ `lang` -> [(nhãn, ShortName)].
    Giọng cùng quốc gia chính lên đầu (vi -> vi-VN trước), kèm các giọng
    Multilingual (đọc được mọi ngôn ngữ) ở cuối. Offline/lỗi mạng ->
    fallback danh sách tĩnh VOICES."""
    lang = norm_lang(lang)
    static = list(VOICES.get(lang, []))
    allv = _fetch_all_voices()
    if not allv:
        return static
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
    out = [(_voice_label(v), v["ShortName"]) for v in native + multi]
    return out or static


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


def synth_demo(voice: str, out_mp3: str | Path, text: str | None = None) -> bool:
    """Đọc thử 1 câu ngắn bằng giọng `voice` -> file mp3. Câu mẫu tự chọn
    theo ngôn ngữ của giọng (vi-VN-... -> câu tiếng Việt). True nếu ra file
    hợp lệ; False nếu lỗi (mạng, giọng sai...)."""
    voice = (voice or "").strip()
    if not voice:
        return False
    lang = norm_lang(voice.split("-")[0])
    txt = (text or "").strip() or _DEMO_TEXTS.get(lang) or _DEMO_TEXTS["en"]
    out_mp3 = str(out_mp3)

    async def _run() -> None:
        import edge_tts
        await edge_tts.Communicate(txt, voice, rate="+0%").save(out_mp3)

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
                     on_done: Optional[Callable[[int], None]] = None) -> None:
    import edge_tts
    sem = asyncio.Semaphore(_TTS_PARALLEL)

    async def one(i: int) -> None:
        async with sem:
            last = None
            for attempt in range(3):        # mạng chập chờn -> thử lại
                try:
                    comm = edge_tts.Communicate(texts[i], voice, rate="+0%")
                    await comm.save(paths[i])
                    if os.path.getsize(paths[i]) > 200:
                        if on_done:
                            on_done(i)
                        return
                    last = RuntimeError("edge-tts trả file rỗng")
                except Exception as e:  # noqa: BLE001
                    last = e
                await asyncio.sleep(1.5 * (attempt + 1))
            raise RuntimeError(
                f"Lồng tiếng thất bại ở câu #{i} (giọng {voice}): {last}")

    await asyncio.gather(*(one(i) for i in range(len(texts))))


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


def _tempo_filters(tempo: float) -> str:
    """Chuỗi atempo (chia tầng nếu >2.0 — phòng xa, hiện _MAX_TEMPO=1.35)."""
    parts = []
    while tempo > 2.0:
        parts.append("atempo=2.0")
        tempo /= 2.0
    parts.append(f"atempo={tempo:.4f}")
    return ",".join(parts)


def _fit_chunk(src_mp3: str, dst_wav: str, window: float, hard_max: float) -> None:
    """Chuyển 1 cụm TTS (mp3) -> wav 48k mono, NÉN thời gian cho lọt khung:
    dài hơn khung -> atempo (≤ _MAX_TEMPO); vẫn dư -> cắt cứng tại hard_max
    (fade 120ms cuối cho khỏi bụp). Ngắn hơn khung -> giữ nguyên."""
    dur = probe_duration(src_mp3)
    af = ["aresample=48000"]
    if dur > window + 0.05 and window > 0.2:
        tempo = min(_MAX_TEMPO, dur / window)
        af.append(_tempo_filters(tempo))
        dur = dur / tempo
    if dur > hard_max + 0.05:           # atempo kịch trần vẫn dư -> cắt + fade
        af.append(f"atrim=0:{hard_max:.3f}")
        af.append(f"afade=t=out:st={max(0.0, hard_max - 0.12):.3f}:d=0.12")
    _ffmpeg(["-i", src_mp3, "-af", ",".join(af), "-ac", "1", "-ar", "48000",
             "-c:a", "pcm_s16le", dst_wav], "khớp thời gian lồng tiếng")


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


# ------------------------------------------------------------------
# API chính
# ------------------------------------------------------------------
def build_dub_track(transcript: dict, clip_segments: list, target_lang: str,
                    voice: str, out_wav: str | Path,
                    llm_translate: bool = True,
                    on_progress: Optional[Callable[[float, str], None]] = None,
                    ) -> tuple[str, list[dict]]:
    """
    Tạo track lồng tiếng cho clip. Trả (đường_dẫn_wav, dub_segments) với
    dub_segments = [{"start","end","text"}] trên timeline ĐẦU RA (text đã dịch)
    — dùng cho phụ đề khớp bản dịch. WAV 48kHz mono, dài ĐÚNG tổng độ dài clip.
    """
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

    dub_segments = [{"start": c["start"], "end": c["end"], "text": t}
                    for c, t in zip(chunks, texts)]

    with tempfile.TemporaryDirectory(prefix="dub_") as td:
        # --- TTS song song ---
        mp3s = [os.path.join(td, f"c{i}.mp3") for i in range(len(chunks))]
        done = {"n": 0}

        def _tts_done(_i: int) -> None:
            done["n"] += 1
            prog(0.15 + 0.55 * done["n"] / max(1, len(chunks)),
                 f"Đang đọc lời thoại ({done['n']}/{len(chunks)})...")

        prog(0.15, f"Đang đọc {len(chunks)} câu (edge-tts)...")
        asyncio.run(_synth_all(texts, voice, mp3s, on_done=_tts_done))

        # --- Khớp thời gian từng cụm ---
        fitted: list[tuple[float, str]] = []
        for i, c in enumerate(chunks):
            window = c["end"] - c["start"]
            # cho phép tràn nhẹ sang khoảng LẶNG sau cụm (tới cụm kế/hết clip)
            nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else total
            hard_max = max(window, min(nxt, total) - c["start"] - 0.05)
            wav = os.path.join(td, f"f{i}.wav")
            _fit_chunk(mp3s[i], wav, window, hard_max)
            fitted.append((c["start"], wav))
            prog(0.70 + 0.15 * (i + 1) / len(chunks), "Khớp thời gian...")

        # --- Ghép về 1 track dài đúng bằng clip ---
        prog(0.88, "Ghép track lồng tiếng...")
        Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
        _mix_track(fitted, total, str(out_wav))

    prog(1.0, "Xong lồng tiếng")
    return str(out_wav), dub_segments
