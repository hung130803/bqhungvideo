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
# Khi phải chạy CPU (máy không GPU / CUDA lỗi) thì hạ về model nhỏ: chậm hơn
# chút nhưng máy user không "chết" 10GB RAM. GPU vẫn dùng model lớn như cũ.
_CPU_MODEL_CAP = {"large-v3": "small", "large-v2": "small", "large-v1": "small",
                  "large": "small", "distil-large-v3": "small",
                  "large-v3-turbo": "small", "turbo": "small",
                  "medium": "medium", "medium.en": "medium.en"}


def _cap_cpu_model(model_name: str) -> str:
    return _CPU_MODEL_CAP.get(model_name, model_name)


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
        "text": " ".join(full).strip(),
    }


def _g(o, k, d=0):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _groq_one(audio_path: str, language, keys: list) -> tuple:
    """Gửi 1 FILE cho Groq, xoay vòng key khi hết lượt. Trả (segs, words, lang, text).

    Dùng CHUNG sổ trạng thái key với app.ai.llm: key nào vừa 429 (kể cả do
    LLM chọn clip) thì bị xếp cuối, key ready lên trước; mọi lời gọi đều
    mark_used/mark_ok/mark_limited để UI 'Cài đặt AI' hiện trạng thái sống."""
    from openai import OpenAI
    from app.ai import llm
    last = ""
    # ready trước, limited-sắp-hết-cooldown sau (không bao giờ rỗng nếu có key)
    for key in llm.pick_keys("groq", keys):
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
            segs = [{"start": float(_g(s, "start", 0)), "end": float(_g(s, "end", 0)),
                     "text": (_g(s, "text", "") or "").strip()}
                    for s in (_g(r, "segments", None) or [])]
            words = [{"start": float(_g(w, "start", 0)), "end": float(_g(w, "end", 0)),
                      "word": (_g(w, "word", "") or "").strip()}
                     for w in (_g(r, "words", None) or [])]
            llm.mark_ok("groq", key)
            return segs, words, (_g(r, "language", None) or language or ""), \
                (_g(r, "text", "") or "")
        except Exception as e:  # noqa: BLE001
            last = str(e)
            if llm.is_rate_limit_error(last):
                llm.mark_limited("groq", key, last)
                continue                       # key hết lượt -> xoay key kế
            if llm.is_auth_error(last):
                llm.mark_invalid("groq", key)
                continue                       # KEY SAI -> bỏ qua, thử key khác
            raise                              # lỗi khác (mạng...): KHÔNG giết oan key
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
            if on_progress:
                on_progress(0.1, f"Đang chép lời (Groq) 0/{n} phần...")
            with ThreadPoolExecutor(max_workers=min(3, len(parts))) as ex:
                futs = {ex.submit(_groq_one, parts[i], language, keys): i
                        for i in sorted(parts)}
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
        if on_progress:
            on_progress(1.0, "Chép lời xong (Groq)")
        return {"language": lang,
                "duration": all_segs[-1]["end"] if all_segs else 0.0,
                "segments": all_segs, "words": all_words,
                "text": " ".join(t for t in full if t).strip()}
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
    language = language or settings.WHISPER_LANGUAGE
    provider = settings.WHISPER_PROVIDER
    # MÁY KHÁCH (bản .exe nhẹ): không có faster-whisper nhưng CÓ key Groq ->
    # tự dùng Groq, không bắt user phải biết đổi thêm 'Nguồn nghe-chép'.
    if provider != "groq" and not is_available() and settings.groq_keys():
        provider = "groq"
    # GROQ (mây) TRƯỚC — KHÔNG cần lib local. Máy yếu/không cài gì vẫn chép được.
    if provider == "groq" and settings.groq_keys():
        try:
            return _transcribe_groq(audio_path, language, on_progress)
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
            return _transcribe_stable(audio_path, model_name, device,
                                      compute_type, language, on_progress)
        except Exception:  # noqa: BLE001 - stable-ts lỗi -> dùng faster-whisper thường
            # GIẢI PHÓNG model stable trước khi nạp model thường: không thì
            # 2 bản model cùng nằm trong RAM (x2 GB với model lớn).
            release_models()
    model = _get_model(model_name, device, compute_type)

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
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

    return {
        "language": getattr(info, "language", language) or "",
        "duration": total,
        "segments": segments,
        "words": words,
        "text": " ".join(full_text).strip(),
    }
