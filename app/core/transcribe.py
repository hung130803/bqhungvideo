"""
Transcribe word-level bằng faster-whisper (local, free).
Trả về danh sách segment + danh sách từ kèm timestamp.

Lib nặng được import lười (lazy) để app khởi động được dù chưa cài.
"""
from __future__ import annotations

from typing import Callable, Optional

from config import settings

_model_cache: dict = {}  # (model_name, device, compute) -> WhisperModel
_cuda_libs_done = False

# Model lớn chạy CPU ngốn RAM khủng (large-v3 int8 ~3-4GB) + CPU cả giờ.
# Khi phải chạy CPU (máy không GPU / CUDA lỗi) thì hạ model theo RAM máy:
# >=16GB -> medium (int8 ~1.5GB, chính xác gần large), <16GB -> small.
# GPU vẫn dùng model lớn như cũ — không đổi gì.
_BIG_MODELS = ("large", "distil-large", "turbo")


def _ram_gb() -> float:
    """Tổng RAM máy (GB) — ctypes thuần, không cần psutil (bản .exe nhẹ)."""
    try:
        import ctypes

        class _MemStat(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint32),
                        ("dwMemoryLoad", ctypes.c_uint32),
                        ("ullTotalPhys", ctypes.c_uint64),
                        ("ullAvailPhys", ctypes.c_uint64),
                        ("ullTotalPageFile", ctypes.c_uint64),
                        ("ullAvailPageFile", ctypes.c_uint64),
                        ("ullTotalVirtual", ctypes.c_uint64),
                        ("ullAvailVirtual", ctypes.c_uint64),
                        ("ullAvailExtendedVirtual", ctypes.c_uint64)]

        st = _MemStat()
        st.dwLength = ctypes.sizeof(_MemStat)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            return st.ullTotalPhys / (1024 ** 3)
    except Exception:  # noqa: BLE001 - không phải Windows / lỗi API
        pass
    return 0.0


def _cap_cpu_model(model_name: str) -> str:
    if not model_name.startswith(_BIG_MODELS):
        return model_name          # small/base/medium giữ nguyên
    return "medium" if _ram_gb() >= 15.5 else "small"


def cpu_threads() -> int:
    """Ngân sách luồng CPU cho whisper/ctranslate2: ECO (mặc định) 2-4 luồng,
    tắt eco thì tối đa nửa số nhân — phân tích KHÔNG được chiếm cả máy."""
    import os
    cores = os.cpu_count() or 4
    if getattr(settings, "ECO_MODE", True):
        return max(2, min(4, cores // 4))
    return max(2, min(8, cores // 2))


def release_models() -> None:
    """GIẢI PHÓNG model whisper khỏi RAM (gọi ngay khi chép lời xong, trước
    các pha face/scene — không để model 1-3GB nằm chờ suốt job phân tích)."""
    import gc
    _model_cache.clear()
    gc.collect()


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def provider_ready() -> bool:
    """Có cách chép lời không: Groq (mây, có key) HOẶC faster-whisper (máy).

    Có key Groq thì luôn tính là sẵn sàng kể cả WHISPER_PROVIDER=local mà máy
    thiếu faster-whisper (bản .exe nhẹ) — transcribe() sẽ tự lùi sang Groq.
    """
    if settings.groq_keys() and (settings.WHISPER_PROVIDER == "groq"
                                 or not is_available()):
        return True
    return is_available()


def _ensure_cuda_libs() -> bool:
    """Đưa cuDNN/cuBLAS (cài qua pip nvidia-*) vào đường tìm DLL để whisper chạy
    GPU. Trả True nếu thấy thư viện. Gọi trước khi nạp model cuda."""
    global _cuda_libs_done
    if _cuda_libs_done:
        return True
    import os
    try:
        import nvidia
        import pathlib
        nv = pathlib.Path(list(nvidia.__path__)[0])
        dirs = [str(nv / s) for s in ("cublas/bin", "cudnn/bin", "cuda_nvrtc/bin")
                if (nv / s).is_dir()]
        if not dirs:
            return False
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ["PATH"]
        for d in dirs:
            try:
                os.add_dll_directory(d)
            except OSError:
                pass
        _cuda_libs_done = True
        return True
    except Exception:  # noqa: BLE001
        return False


def _get_model(model_name: str, device: str, compute_type: str):
    if device != "cuda":
        model_name = _cap_cpu_model(model_name)
    key = (model_name, device, compute_type)
    if key not in _model_cache:
        from faster_whisper import WhisperModel
        from config import MODELS_DIR
        if device == "cuda":
            _ensure_cuda_libs()
        try:
            _model_cache[key] = WhisperModel(
                model_name, device=device, compute_type=compute_type,
                download_root=str(MODELS_DIR), cpu_threads=cpu_threads(),
            )
        except Exception:  # noqa: BLE001 - GPU lỗi/thiếu cuDNN -> lùi CPU cho chạy được
            if device == "cuda":
                # CPU không kham nổi model GPU cỡ lớn (large-v3 int8 ~3-4GB RAM,
                # chậm x10) -> hạ model khi rơi về CPU.
                _model_cache[key] = WhisperModel(
                    _cap_cpu_model(model_name), device="cpu", compute_type="int8",
                    download_root=str(MODELS_DIR), cpu_threads=cpu_threads(),
                )
            else:
                raise
    return _model_cache[key]


def _stable_available() -> bool:
    try:
        import stable_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _get_stable_model(model_name: str, device: str, compute_type: str):
    if device != "cuda":
        model_name = _cap_cpu_model(model_name)
    key = ("stable", model_name, device, compute_type)
    if key not in _model_cache:
        import stable_whisper
        from config import MODELS_DIR
        if device == "cuda":
            _ensure_cuda_libs()
        try:
            _model_cache[key] = stable_whisper.load_faster_whisper(
                model_name, device=device, compute_type=compute_type,
                download_root=str(MODELS_DIR), cpu_threads=cpu_threads())
        except Exception:  # noqa: BLE001 - GPU lỗi -> lùi CPU (model nhỏ, xem _get_model)
            if device == "cuda":
                _model_cache[key] = stable_whisper.load_faster_whisper(
                    _cap_cpu_model(model_name), device="cpu", compute_type="int8",
                    download_root=str(MODELS_DIR), cpu_threads=cpu_threads())
            else:
                raise
    return _model_cache[key]


def _transcribe_stable(audio_path, model_name, device, compute_type, language,
                       on_progress) -> dict:
    """Dùng stable-ts: căn mốc TỪNG TỪ chính xác hơn (snap theo khoảng lặng)."""
    if on_progress:
        on_progress(0.1, "Đang chép lời (căn chuẩn)...")
    model = _get_stable_model(model_name, device, compute_type)
    # transcribe() không có callback tiến độ -> NHỊP TIM nền: video dài đứng im
    # ở 10% hàng chục phút làm user tưởng treo. Tiến dần (không tới 100%) + số
    # giây đã chạy để biết app vẫn sống.
    import threading as _th
    import time as _time
    _stop = _th.Event()
    if on_progress:
        def _beat():
            t0 = _time.time()
            while not _stop.wait(5):
                el = _time.time() - t0
                p = min(0.85, 0.1 + 0.75 * el / (el + 240))
                on_progress(p, f"Đang chép lời (căn chuẩn)... {int(el)}s")
        _th.Thread(target=_beat, daemon=True).start()
    try:
        # (Đã GỠ vad=True: torch CPU + tải model silero làm TREO bước chép lời.)
        r = model.transcribe(audio_path, language=language, word_timestamps=True,
                             verbose=False)
    finally:
        _stop.set()
    segments, words, full = [], [], []
    for seg in r.segments:
        segments.append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                         "text": (seg.text or "").strip()})
        full.append((seg.text or "").strip())
        for w in (seg.words or []):
            words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                          "word": (w.word or "").strip()})
    if on_progress:
        on_progress(1.0, "Chép lời xong")
    total = segments[-1]["end"] if segments else 0.0
    return {
        "language": getattr(r, "language", None) or language or "",
        "duration": total, "segments": segments, "words": words,
        "engine": f"stable-ts:{model_name}",   # xem chú thích ở nhánh Groq
        "text": " ".join(full).strip(),
    }


def _g(o, k, d=0):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


#: Lỗi TẠM THỜI phía Groq — máy chủ họ chớp nhoáng, KHÔNG phải key sai cũng
#: không phải hết lượt. Phải thử lại ngay, đừng bỏ cả video.
#:
#: LỖI THẬT (anh Hùng 2026-07-25): "Error code: 500 - Internal Server Error"
#: rơi vào nhánh `raise` nên chết ngay lần đầu → video bị coi là cắt lỗi và
#: chuyển vào `_Loi`, dù chỉ cần thử lại sau 1 giây là được.
_GROQ_TRANSIENT = (
    "error code: 500", "error code: 502", "error code: 503", "error code: 504",
    "internal server error", "bad gateway", "service unavailable",
    "gateway timeout", "overloaded", "timed out", "timeout",
    "connection reset", "connection aborted", "connection error",
    "remote end closed", "temporarily",
)


def _groq_transient(msg: str) -> bool:
    """True nếu lỗi Groq thuộc loại nên THỬ LẠI NGAY (hàm thuần, để test)."""
    m = (msg or "").lower()
    return any(k in m for k in _GROQ_TRANSIENT)


def _groq_one(audio_path: str, language, keys: list, start_at: int = 0,
              on_wait=None) -> tuple:
    """Gửi 1 FILE cho Groq, xoay vòng key khi hết lượt. Trả (segs, words, lang, text).

    Dùng CHUNG sổ trạng thái key với app.ai.llm: key nào vừa 429 (kể cả do
    LLM chọn clip) thì bị xếp cuối, key ready lên trước; mọi lời gọi đều
    mark_used/mark_ok/mark_limited để UI 'Cài đặt AI' hiện trạng thái sống.

    start_at: XOAY ĐIỂM BẮT ĐẦU danh sách key (chia tải khi chép lời SONG SONG
    — mỗi cửa sổ bắt đầu ở 1 key khác nhau thay vì cả 3 đập vào key đầu, gây
    429 chùm trong cùng phút). on_wait(sec): callback báo "đang đợi Groq hồi
    X giây" khi TẤT CẢ key đều limited với reset NGẮN (TPM cùng nick) — đợi
    rồi thử lại thay vì fail (video dài chép lời rất dễ chạm TPM).
    """
    import time as _time
    from openai import OpenAI
    from app.ai import llm
    last = ""

    def _order():
        """Danh sách key ưu tiên, xoay start_at vòng (chỉ xoay phần READY để
        chia tải song song; limited/invalid vẫn giữ cuối)."""
        ordered = llm.pick_keys("groq", keys)
        if start_at and ordered:
            k = start_at % len(ordered)
            ordered = ordered[k:] + ordered[:k]
        return ordered

    # tối đa 2 vòng: vòng 1 thử mọi key; nếu TẤT CẢ đều 429 với reset ngắn
    # (TPM cùng nick), đợi hết cooldown ngắn nhất rồi thử lại vòng 2.
    groq_tries: dict = {}      # key -> số lần đã thử lại vì lỗi tạm thời
    for _round in (1, 2):
        pending = list(_order())
        while pending:
            key = pending.pop(0)
            llm.mark_used("groq", key)
            try:
                client = OpenAI(api_key=key,
                                base_url="https://api.groq.com/openai/v1",
                                timeout=180, max_retries=1)
                with open(audio_path, "rb") as f:
                    r = client.audio.transcriptions.create(
                        file=f, model=settings.GROQ_WHISPER_MODEL,
                        response_format="verbose_json",
                        timestamp_granularities=["segment", "word"],
                        language=language or None)
                segs = [{"start": float(_g(s, "start", 0)),
                         "end": float(_g(s, "end", 0)),
                         "text": (_g(s, "text", "") or "").strip()}
                        for s in (_g(r, "segments", None) or [])]
                words = [{"start": float(_g(w, "start", 0)),
                          "end": float(_g(w, "end", 0)),
                          "word": (_g(w, "word", "") or "").strip()}
                         for w in (_g(r, "words", None) or [])]
                llm.mark_ok("groq", key)
                return segs, words, (_g(r, "language", None) or language or ""), \
                    (_g(r, "text", "") or "")
            except Exception as e:  # noqa: BLE001
                last = str(e)
                if llm.is_too_large_error(last):
                    # 413 "Request too large" (đoạn tiếng gửi lên quá dài cho
                    # hạn mức token/phút). Groq gắn kèm `rate_limit_exceeded`
                    # nên nhánh dưới sẽ coi là HẾT LƯỢT và khoá key 120s —
                    # lần lượt CẢ 38 key, dù key nào cũng cùng hạn mức. Đây là
                    # lỗi CỦA YÊU CẦU: nổi lên để caller chia nhỏ đoạn tiếng.
                    # (xem llm.is_too_large_error — đo 06/08/2026)
                    raise llm.LLMTooLarge(f"Chép lời: đoạn tiếng quá lớn cho "
                                          f"hạn mức token/phút: {last}")
                if llm.is_rate_limit_error(last):
                    llm.mark_limited("groq", key, last)
                    continue                   # key hết lượt -> xoay key kế
                if llm.is_auth_error(last):
                    llm.mark_invalid("groq", key)
                    continue                   # KEY SAI -> bỏ qua, thử key khác
                if _groq_transient(last):
                    # LỖI PHÍA GROQ (500/502/503, timeout, mạng chớp): thử lại
                    # NGAY trên CHÍNH key này — nghỉ 1s rồi 3s. Trước đây rơi
                    # thẳng vào `raise` nên cả video bị coi là cắt lỗi và đẩy
                    # vào `_Loi`, dù chỉ cần thử lại 1 giây sau là xong.
                    tried = groq_tries.get(key, 0)
                    if tried < 2:
                        groq_tries[key] = tried + 1
                        if on_wait:
                            on_wait(1.0 + 2.0 * tried)
                        _time.sleep(1.0 + 2.0 * tried)
                        pending.insert(0, key)   # thử lại NGAY chính key này
                        continue
                    continue                   # hết lượt thử -> sang key khác
                raise                          # lỗi khác: KHÔNG giết oan key
        # hết vòng: mọi key vừa thử đều limited. Nếu reset NGẮN (TPM/phút,
        # <= 90s) -> ĐỢI hết cooldown ngắn nhất rồi thử lại (vòng 2). Reset
        # dài (hết lượt ngày) thì đợi vô ích -> thoát báo lỗi.
        if _round == 1 and not llm.is_auth_error(last):
            wait = llm.soonest_ready_wait("groq", keys)
            if wait is not None and 0 < wait <= 90.0:
                if on_wait:
                    on_wait(wait)
                _time.sleep(wait + 0.5)
                continue
        break
    if llm.is_auth_error(last):
        raise RuntimeError(
            "Tất cả key Groq đều SAI/không hợp lệ — vào 'Cài đặt AI' kiểm tra "
            f"lại key (xóa dấu cách thừa, dán key đúng). Chi tiết: {last}")
    raise RuntimeError(f"Groq whisper lỗi (hết key/quota): {last}")


def _audio_duration(path: str, ff_probe: str, flags: int) -> float:
    import subprocess
    try:
        r = subprocess.run(
            [ff_probe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=60, creationflags=flags)
        return float((r.stdout or "0").strip() or 0)
    except Exception:  # noqa: BLE001
        return 0.0


VA_LO_MIN = 2.0          # khoảng trống >= 2s mới xét (dưới mức này là nghỉ hơi)
VA_LO_TOI_DA = 8         # trần số lỗ vá / video — không đội thời gian + hạn mức
VA_LO_DEM = 0.30         # đệm mỗi đầu để không cắt cụt từ


def _co_giong_nguoi(audio_path: str, a: float, b: float) -> bool:
    """Khoảng [a,b] có TIẾNG NGƯỜI NÓI không? (không phải nhạc/tiếng động).

    BÀI HỌC 07/08/2026: bản đầu tôi dùng `silencedetect` làm thước đo rồi kết
    luận "phụ đề chỉ phủ 83%". SAI — video máy xúc thì tiếng động cơ cũng là
    "không im lặng". Nay lọc DẢI TẦN GIỌNG NGƯỜI (300-3400Hz) trước rồi mới đo
    to/nhỏ: tiếng động cơ/nhạc nền nằm phần lớn ngoài dải này nên bị hạ xuống.
    """
    import re
    import subprocess
    _NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0
    # KHÔNG dùng `-v error`: astats in kết quả ở mức INFO, hạ mức log là NUỐT
    # luôn số đo -> hàm này trả False MỌI LÚC -> vá lỗ không bao giờ chạy mà
    # cũng không báo lỗi. Đúng bẫy `volumedetect` đã sập một lần trước đây.
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-ss", f"{a:.3f}",
         "-t", f"{b - a:.3f}", "-i", audio_path,
         # 3 TẦNG (đo 07/08/2026): 1 tầng quá thoải, tiếng ù máy 80Hz chỉ tụt
         # còn -44 dB nên vẫn bị coi là giọng người. 3 tầng -> -67 dB.
         "-af", "highpass=f=300:poles=2,highpass=f=300:poles=2,"
                "lowpass=f=3400:poles=2,astats=metadata=1:reset=0",
         "-f", "null", "-"],
        capture_output=True, text=True, creationflags=_NO_WINDOW)
    m = re.findall(r"RMS level dB:\s*(-?[\d.]+|-?inf)", r.stderr or "")
    if not m:
        return False
    try:
        rms = max(float(x) for x in m if x not in ("-inf", "inf"))
    except ValueError:
        return False
    # NGƯỠNG -55 dB — chọn theo SỐ ĐO, không phỏng đoán (sau 3 tầng lọc):
    #   giọng người -27 · giọng NHỎ (-25dB) -51 · ù máy -67 · nhạc 9kHz -73
    # -55 nằm giữa giọng-nhỏ và ù-máy: giữ được giọng nhỏ, loại tiếng động.
    return rms > -55.0


def va_lo_chep_loi(audio_path: str, segs: list, words: list, lang: str,
                   on_progress=None) -> tuple:
    """VÁ LỖ: chép lại RIÊNG những khoảng bị bỏ sót rồi ghép vào transcript.

    VÌ SAO (anh Hùng 07/08/2026: "nhiều đoạn nó nói mà k có sub luôn, bên
    capcut gần như hoàn hảo"): ĐO THẬT trên video 600s — chép cả file thì
    khoảng 300,4-311,9s KHÔNG có câu nào, nhưng CẮT RIÊNG đúng đoạn đó gửi lại
    Groq thì ra "I got that in pretty well.". Cùng tiếng, cùng model: gửi cả
    khối 10 phút thì whisper nuốt mất chỗ giọng nhỏ/lẫn nhạc. CapCut hơn ở chỗ
    nó nhận dạng theo TỪNG CHỖ CÓ GIỌNG, nên mình làm thêm lượt vá này.

    FAIL-SAFE tuyệt đối: mọi lỗi ở đây đều nuốt và trả lại transcript GỐC —
    thà thiếu vài dòng còn hơn hỏng cả bản chép lời.
    Trả (segments, words, số_lỗ_vá_được).
    """
    import os
    import re
    import shutil
    import subprocess
    import tempfile
    _NO_WINDOW = 0x08000000 if hasattr(subprocess, "STARTUPINFO") else 0
    if not segs:
        return segs, words, 0
    try:
        lo = []
        for i in range(len(segs) - 1):
            a, b = float(segs[i]["end"]), float(segs[i + 1]["start"])
            if b - a >= VA_LO_MIN:
                lo.append((a, b))
        lo.sort(key=lambda x: x[1] - x[0], reverse=True)
        lo = lo[:VA_LO_TOI_DA]
        if not lo:
            return segs, words, 0
        keys = settings.groq_keys()
        if not keys:
            return segs, words, 0
        them_s: list = []
        them_w: list = []
        n_va = 0
        work = tempfile.mkdtemp(prefix="valo_")
        try:
            for k, (a, b) in enumerate(lo):
                if not _co_giong_nguoi(audio_path, a, b):
                    continue
                if on_progress:
                    on_progress(0.97, f"Chép lại chỗ bị sót {k + 1}/{len(lo)}…")
                a2, b2 = max(0.0, a - VA_LO_DEM), b + VA_LO_DEM
                p = os.path.join(work, f"lo{k}.m4a")
                subprocess.run(
                    [settings.FFMPEG_PATH, "-v", "error", "-y",
                     "-ss", f"{a2:.3f}", "-t", f"{b2 - a2:.3f}", "-i", audio_path,
                     "-vn", "-ac", "1", "-ar", "16000", "-c:a", "aac",
                     "-b:a", "48k", p],
                    creationflags=_NO_WINDOW)
                if not os.path.exists(p) or os.path.getsize(p) < 800:
                    continue
                s2, w2, _lg2, _tx2 = _groq_one(p, _ma_iso(lang), keys)
                # chỉ nhận câu CÓ CHỮ THẬT và NẰM TRONG lỗ (đệm có thể lấn sang
                # câu kề -> nhận vào là ra phụ đề TRÙNG, tệ hơn thiếu)
                got = False
                for s in s2 or []:
                    t = re.sub(r"[\s.,!?…、。]+", "", str(s.get("text", "")))
                    if len(t) < 2:
                        continue
                    ss, se = a2 + float(s["start"]), a2 + float(s["end"])
                    if se <= a + 0.05 or ss >= b - 0.05:
                        continue
                    them_s.append({**s, "start": max(ss, a), "end": min(se, b),
                                   "text": s.get("text", "")})
                    got = True
                if got:
                    n_va += 1
                    for w in w2 or []:
                        ws, we = a2 + float(w["start"]), a2 + float(w["end"])
                        if a <= ws < b:
                            them_w.append({**w, "start": ws, "end": min(we, b)})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if not them_s:
            return segs, words, 0
        segs = sorted(segs + them_s, key=lambda s: float(s["start"]))
        words = sorted((words or []) + them_w, key=lambda w: float(w["start"]))
        return segs, words, n_va
    except Exception:  # noqa: BLE001 — vá lỗ HỎNG thì giữ nguyên bản gốc
        return segs, words, 0


def _transcribe_groq(audio_path: str, language, on_progress) -> dict:
    """Nghe-chép qua GROQ (mây, FREE). Cắt audio thành CỬA SỔ CHÍNH XÁC 10 phút
    (-ss i*600 -t 600) rồi nén mp3 nhẹ -> dưới giới hạn 25MB + mốc giờ KHÔNG lệch
    (offset = i*600 ĐÚNG vì cắt đúng từ mốc đó). Ghép lại đúng timeline."""
    import math
    import os
    import shutil
    import subprocess
    import tempfile
    keys = settings.groq_keys()
    if not keys:
        raise RuntimeError("Chưa có GROQ key.")
    ff = shutil.which("ffmpeg") or settings.FFMPEG_PATH or "ffmpeg"
    fp = shutil.which("ffprobe") or settings.FFPROBE_PATH or "ffprobe"
    flags = 0x0800_0000 if os.name == "nt" else 0
    chunk = 600
    total = _audio_duration(audio_path, fp, flags)
    n = max(1, math.ceil(total / chunk)) if total > 0 else 1
    work = tempfile.mkdtemp(prefix="gq_")
    try:
        all_segs, all_words, full, lang = [], [], [], (language or "")
        failed_windows: list = []
        # ---- BƯỚC 1: cắt tất cả cửa sổ (ffmpeg, nhanh) ----
        parts: dict = {}                         # i -> đường dẫn mp3 đã cắt
        for i in range(n):
            start = i * chunk                    # mốc CHÍNH XÁC của phần này
            part = os.path.join(work, f"p{i}.mp3")
            cmd = [ff, "-y", "-ss", str(start)]
            if total > 0:
                cmd += ["-t", str(chunk)]        # 1 cửa sổ 10 phút (chính xác)
            cmd += ["-i", audio_path, "-ac", "1", "-ar", "16000", "-b:a", "48k",
                    part]
            # cắt hỏng KHÔNG được bỏ qua im lặng (mất nguyên 10 phút transcript
            # mà không ai biết) -> thử lại 1 lần; ghi nhận phần hỏng để xử lý
            # sau vòng lặp.
            ok_cut = False
            for _attempt in (1, 2):
                try:
                    subprocess.run(cmd, capture_output=True, creationflags=flags,
                                   timeout=900)
                except Exception:  # noqa: BLE001
                    pass
                if os.path.exists(part) and os.path.getsize(part) >= 400:
                    ok_cut = True
                    break
            if ok_cut:
                parts[i] = part
            else:
                failed_windows.append(i + 1)
        # ---- BƯỚC 2: gửi Groq SONG SONG tối đa 3 cửa sổ (video dài nhanh hẳn).
        # _groq_one an toàn thread: client OpenAI tạo mới mỗi lần gọi, keys chỉ
        # đọc. Kết quả ghép theo index -> thứ tự + offset không đổi so với tuần tự.
        results: dict = {}                       # i -> (segs, words, lg, text)
        if parts:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            done = 0
            waiting = {"sec": 0.0}                # reset dài nhất đang đợi (log)
            if on_progress:
                on_progress(0.1, f"Đang chép lời (Groq) 0/{n} phần...")

            def _on_wait(sec):                    # 1 cửa sổ đang đợi TPM hồi
                waiting["sec"] = max(waiting["sec"], sec)
                if on_progress:
                    on_progress(0.1 + 0.85 * done / n,
                                f"Đang đợi Groq hồi hạn mức ~{int(sec)}s rồi "
                                f"thử lại (đã xong {done}/{n} phần)...")
            # CHIA TẢI: mỗi cửa sổ BẮT ĐẦU ở 1 key khác nhau (start_at=idx) —
            # 3 cửa sổ song song không cùng đập vào key đầu gây 429 chùm trong
            # cùng phút (Groq giới hạn theo phút). Kết quả ghép theo index nên
            # thứ tự/offset không đổi.
            idx_list = sorted(parts)
            # ── KHOÁ NGÔN NGỮ THEO KHÚC ĐẦU ───────────────────────────────
            # LỖI THẬT (anh Hùng 07/08/2026, kênh Nhật): "video nhật sub nhật nó
            # trộn lẫn lộn cả tiếng anh". Vì `language` truyền vào là None (để
            # Groq tự nhận diện), mà video dài bị chia THÀNH TỪNG KHÚC 10 PHÚT
            # và MỖI KHÚC TỰ ĐOÁN NGÔN NGỮ RIÊNG. Khúc nào tiếng nhỏ/khó nghe là
            # Groq đoán 'en' rồi DỊCH luôn khúc đó sang tiếng Anh -> phụ đề nửa
            # Nhật nửa Anh, không cách nào dùng được.
            # Nay: chép khúc ĐẦU trước (1 lượt), lấy ngôn ngữ của nó (có
            # resolve_lang soi chữ để không tin nhãn sai), rồi ÉP ngôn ngữ đó
            # cho MỌI khúc còn lại -> cả video 1 ngôn ngữ duy nhất.
            _lang_ep = _ma_iso(language)
            if not _lang_ep and len(idx_list) > 1:
                _i0 = idx_list[0]
                results[_i0] = _groq_one(parts[_i0], None, keys, start_at=0,
                                         on_wait=_on_wait)
                done += 1
                _lg0, _txt0 = results[_i0][2], results[_i0][3]
                try:
                    from app.ai import recap as _rc
                    _lang_ep = _rc.resolve_lang(_lg0 or "", _txt0 or "") or _lg0
                except Exception:  # noqa: BLE001
                    _lang_ep = _lg0
                # ⚠ PHẢI ĐỔI VỀ MÃ ISO. LỖI THẬT tôi gây ra ở v2.11.1 (anh Hùng
                # 07/08/2026 "kênh nào phân tích cũng bị… k có AI phân tích"):
                # Groq TRẢ VỀ tên đầy đủ ("English"/"Japanese") nhưng tham số
                # GỬI LÊN chỉ nhận mã ISO ("en"/"ja") -> ném nguyên tên vào là
                # 400 "unsupported language: English" -> CHẾT cả bước chép lời
                # -> tụt về whisper máy -> mọi video >10 phút ra "Cắt cơ bản".
                # Không nhận ra được thì THÀ tự nhận diện như cũ còn hơn chết.
                _lang_ep = _ma_iso(_lang_ep)
                idx_list = idx_list[1:]
                if on_progress:
                    on_progress(0.1 + 0.85 * done / n,
                                f"Chép lời (Groq) 1/{n} phần — đã khoá ngôn ngữ "
                                f"«{_lang_ep or 'tự nhận diện'}» cho cả video")
            with ThreadPoolExecutor(max_workers=min(3, max(1, len(idx_list)))) as ex:
                futs = {ex.submit(_groq_one, parts[i], _lang_ep, keys,
                                  start_at=pos, on_wait=_on_wait): i
                        for pos, i in enumerate(idx_list)}
                for fut in as_completed(futs):
                    results[futs[fut]] = fut.result()   # lỗi -> nổi lên như cũ
                    done += 1
                    if on_progress:
                        on_progress(0.1 + 0.85 * done / n,
                                    f"Đang chép lời (Groq) {done}/{n} phần...")
        for i in sorted(results):                # ghép ĐÚNG THỨ TỰ thời gian
            segs, words, lg, _ = results[i]
            start = i * chunk
            lang = lang or lg
            for s in segs:
                all_segs.append({"start": round(s["start"] + start, 3),
                                 "end": round(s["end"] + start, 3),
                                 "text": s["text"]})
                full.append(s["text"])
            for w in words:
                all_words.append({"start": round(w["start"] + start, 3),
                                  "end": round(w["end"] + start, 3),
                                  "word": w["word"]})
        if not all_words and not all_segs:       # nén/cắt hỏng -> gửi nguyên file
            segs, words, lang, _ = _groq_one(audio_path, language, keys)
            all_segs, all_words = segs, words
            full = [s["text"] for s in segs]
        elif failed_windows:
            # có kết quả MỘT PHẦN nhưng vài cửa sổ hỏng -> transcript thiếu
            # nội dung; FAIL rõ ràng còn hơn cắt clip trên transcript khuyết.
            raise RuntimeError(
                f"Nén/cắt audio thất bại ở phần {failed_windows} (tổng {n} "
                "phần) — transcript sẽ thiếu nội dung nên đã dừng. Thử lại sau.")
        all_segs, all_words, _va = va_lo_chep_loi(
            audio_path, all_segs, all_words, lang, on_progress)
        if _va:
            full = [s["text"] for s in all_segs]
        if on_progress:
            on_progress(1.0, "Chép lời xong (Groq)"
                        + (f" · vá thêm {_va} chỗ bị sót" if _va else ""))
        return {"language": lang,
                "duration": all_segs[-1]["end"] if all_segs else 0.0,
                "segments": all_segs, "words": all_words,
                # AI ĐÃ CHÉP BẰNG GÌ — xem `analysis._run_one`: cột
                # `analysis.engine` từng đóng cứng "faster-whisper:<model>" nên
                # KHÔNG BAO GIỜ biết được lượt đó đi Groq hay tụt về máy.
                "engine": "groq:whisper-large-v3",
                "text": " ".join(t for t in full if t).strip()}
    finally:
        shutil.rmtree(work, ignore_errors=True)


#: MÃ ISO Groq/Whisper NHẬN cho tham số `language` (lấy từ chính lời báo lỗi
#: 400 "Language must be one of: [...]"). Ném tên đầy đủ vào là 400 -> chết cả
#: bước chép lời (lỗi thật v2.11.1, xem _ma_iso).
_ISO_OK = frozenset("""mg de tr vi uk th lv be nn ca he et sd tl da km zh te kn
br gl yo tg tk no oc gu mt haw ba jv ro mi cy sw es ru ja ar bg ml pl it ms ta
mn af ur lt bn is ne bs si sn fr id hi hr am yi uz ln ko fi el sl en pt nl sv
cs hu fa ka az kk hy sq mk my lo sa ps bo tt so su nb la eu pa as fo ht ha sk
ka""".split())
#: tên đầy đủ Groq HAY TRẢ VỀ -> mã ISO
_TEN_ISO = {
    "english": "en", "japanese": "ja", "vietnamese": "vi", "korean": "ko",
    "chinese": "zh", "mandarin": "zh", "thai": "th", "spanish": "es",
    "portuguese": "pt", "french": "fr", "german": "de", "russian": "ru",
    "indonesian": "id", "hindi": "hi", "arabic": "ar", "italian": "it",
    "dutch": "nl", "turkish": "tr", "polish": "pl", "filipino": "tl",
    "tagalog": "tl", "malay": "ms", "swedish": "sv", "ukrainian": "uk",
}


def _ma_iso(lg):
    """Đổi nhãn ngôn ngữ về MÃ ISO mà Groq nhận; không nhận ra -> None.

    LỖI THẬT (v2.11.1, anh Hùng 07/08/2026 "kênh nào phân tích cũng bị"): bản vá
    khoá-ngôn-ngữ lấy nhãn Groq TRẢ VỀ ("English") ném lại làm tham số
    `language`, mà tham số đó chỉ nhận MÃ ("en") -> 400 "unsupported language:
    English" -> cả bước chép lời chết -> tụt whisper máy -> MỌI video trên 10
    phút ra "Cắt cơ bản (chưa qua AI)".
    Trả None khi không chắc: tự nhận diện lại còn hơn làm chết cả lượt."""
    s = str(lg or "").strip().lower()
    if not s:
        return None
    if s in _ISO_OK:
        return s
    s2 = _TEN_ISO.get(s)
    if s2:
        return s2
    if len(s) > 2 and s[:2] in _ISO_OK and ("-" in s or "_" in s):
        return s[:2]                      # "en-US" -> "en"
    return None


def _fix_lang(result: dict) -> dict:
    """SỬA NHÃN NGÔN NGỮ theo CHỮ trong transcript: whisper đôi khi trả nhãn
    sai (vd bị ép/hiểu nhầm là 'en' nhưng chữ ra là tiếng Nhật). recap.resolve_lang
    nhìn script phi-Latin (kana/hangul/Thái/Cyrillic/Ả Rập/Devanagari) mà ép
    đúng -> recap/lồng tiếng/phụ đề dùng đúng ngôn ngữ. Chữ Latin thì giữ nhãn
    whisper. Lỗi -> trả nguyên result (không chặn chép lời)."""
    try:
        from app.ai import recap
        result["language"] = recap.resolve_lang(
            result.get("language", ""), result.get("text", ""))
    except Exception:  # noqa: BLE001
        pass
    return result


def transcribe(
    audio_path: str,
    model_name: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: Optional[str] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> dict:
    """
    Trả về:
      {
        "language": "vi",
        "duration": 123.4,
        "segments": [{"start","end","text"}],
        "words": [{"start","end","word"}],
        "text": "toàn bộ"
      }
    Ưu tiên stable-ts (căn từ chuẩn hơn); lỗi -> lùi faster-whisper.
    """
    # NGÔN NGỮ: LUÔN TỰ NHẬN DIỆN (cả Groq lẫn whisper local) — KHÔNG ép theo
    # WHISPER_LANGUAGE nữa. Trước đây stale "en" trong .env/cài đặt khiến MỌI
    # video (kể cả tiếng Nhật) bị chép/dán nhãn tiếng Anh -> recap/lồng tiếng/
    # phụ đề ra tiếng Anh. Whisper (Groq large-v3 + faster-whisper) tự nhận diện
    # rất tốt; _fix_lang còn sửa nhãn theo CHỮ nếu whisper trả nhãn sai.
    provider = settings.WHISPER_PROVIDER
    # MÁY KHÁCH (bản .exe nhẹ): không có faster-whisper nhưng CÓ key Groq ->
    # tự dùng Groq, không bắt user phải biết đổi thêm 'Nguồn nghe-chép'.
    if provider != "groq" and not is_available() and settings.groq_keys():
        provider = "groq"
    # KHỎE NHẤT mà KHÔNG tốn máy: phải chạy CPU (không GPU) mà có key Groq
    # -> mây TRƯỚC (whisper-large-v3, chính xác hơn model local đã cap, RAM ~0,
    # CPU rảnh). Groq lỗi/hết hạn mức -> tự lùi về whisper máy ở dưới.
    # GPU tốt -> giữ local như cũ (nhanh, không phụ thuộc hạn mức).
    if provider != "groq" and device != "cuda" and settings.groq_keys():
        provider = "groq"
    # (User có KEY GROQ VÔ HẠN -> KHÔNG né Groq theo độ dài nữa: dùng Groq
    # thẳng cho chính xác + đồng nhất. Việc chia tải nhiều key + tự đợi/thử lại
    # ở _transcribe_groq đủ để chạy mượt kể cả video dài.)

    # GROQ (mây) TRƯỚC — KHÔNG cần lib local. Máy yếu/không cài gì vẫn chép được.
    if provider == "groq" and settings.groq_keys():
        try:
            # language=None -> Groq TỰ NHẬN DIỆN (không để stale "en" phá video Nhật)
            return _fix_lang(_transcribe_groq(audio_path, None, on_progress))
        except Exception as e:  # noqa: BLE001
            if not (is_available() or _stable_available()):
                raise RuntimeError(f"Chép lời qua Groq lỗi: {e}")
            # còn whisper máy -> thử tiếp ở dưới
    # ---- Chép lời bằng MÁY (faster-whisper / stable-ts) ----
    if not is_available():
        raise RuntimeError(
            "Chưa bật chép lời. Vào 'Cài đặt AI' dán key Groq (miễn phí), "
            "hoặc cài faster-whisper (pip install -r requirements.txt)."
        )
    if _stable_available():
        try:
            return _fix_lang(_transcribe_stable(audio_path, model_name, device,
                                                compute_type, None, on_progress))
        except Exception:  # noqa: BLE001 - stable-ts lỗi -> dùng faster-whisper thường
            # GIẢI PHÓNG model stable trước khi nạp model thường: không thì
            # 2 bản model cùng nằm trong RAM (x2 GB với model lớn).
            release_models()
    model = _get_model(model_name, device, compute_type)

    segments_iter, info = model.transcribe(
        audio_path,
        language=None,          # TỰ NHẬN DIỆN (bỏ stale "en" phá video khác tiếng)
        word_timestamps=True,
        vad_filter=True,  # bỏ qua khoảng lặng -> nhanh + chính xác hơn
    )

    total = float(getattr(info, "duration", 0) or 0)
    segments: list[dict] = []
    words: list[dict] = []
    full_text: list[str] = []

    for seg in segments_iter:
        segments.append(
            {"start": round(seg.start, 3), "end": round(seg.end, 3),
             "text": seg.text.strip()}
        )
        full_text.append(seg.text.strip())
        for w in (seg.words or []):
            words.append(
                {"start": round(w.start, 3), "end": round(w.end, 3),
                 "word": w.word.strip()}
            )
        if on_progress and total:
            on_progress(min(1.0, seg.end / total), "Đang chép lời...")

    return _fix_lang({
        "language": getattr(info, "language", None) or "",
        "duration": total,
        "segments": segments,
        "words": words,
        "engine": f"faster-whisper:{model_name}",   # xem chú thích ở nhánh Groq
        "text": " ".join(full_text).strip(),
    })
