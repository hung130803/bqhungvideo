"""
Kiểm tra môi trường trước khi chạy app.  Chạy:  python check_env.py
Báo cáo: phiên bản Python, ffmpeg, các thư viện, GPU, LLM key.
"""
from __future__ import annotations

import sys

# Console Windows mặc định cp1252 -> ép UTF-8 để in được tiếng Việt/emoji
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def _ok(b: bool) -> str:
    return "✅" if b else "❌"


def _check_ollama(settings):
    """Trả (đang_chạy, [tên model])."""
    try:
        import requests
        base = settings.OLLAMA_BASE_URL.replace("/v1", "")
        r = requests.get(f"{base}/api/tags", timeout=3)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return True, [m for m in models if m]
    except Exception:  # noqa: BLE001
        return False, []


def main() -> None:
    print("=" * 56)
    print(" AI Content Studio — kiểm tra môi trường")
    print("=" * 56)

    # Python
    v = sys.version_info
    py_ok = (v.major, v.minor) in ((3, 10), (3, 11), (3, 12))  # khớp README
    print(f"{_ok(py_ok)} Python {v.major}.{v.minor}.{v.micro}"
          + ("" if py_ok else "  ⚠ NÊN dùng 3.11/3.12 (xem README)"))

    # Thư viện
    libs = {
        "PyQt6": "PyQt6",
        "faster-whisper": "faster_whisper",
        "PySceneDetect": "scenedetect",
        "librosa": "librosa",
        "mediapipe": "mediapipe",
        "opencv": "cv2",
        "openai (OpenAI/DeepSeek)": "openai",
        "google-generativeai (Gemini)": "google.generativeai",
        "python-dotenv": "dotenv",
        "psutil": "psutil",
    }
    print("\n-- Thư viện --")
    for name, mod in libs.items():
        try:
            __import__(mod)
            print(f"{_ok(True)} {name}")
        except Exception:  # noqa: BLE001
            print(f"{_ok(False)} {name}  (pip install -r requirements.txt)")

    # ffmpeg + phần cứng (dùng chính code của app)
    print("\n-- ffmpeg + phần cứng --")
    try:
        from app.queue.resource_manager import HARDWARE, PROFILE
        print(f"{_ok(HARDWARE.has_ffmpeg)} ffmpeg")
        print(f"   CPU: {HARDWARE.cpu_cores} luồng · RAM: {HARDWARE.ram_gb} GB")
        gpu = HARDWARE.gpu_name if HARDWARE.has_cuda else "Không có GPU NVIDIA"
        print(f"   GPU: {gpu}"
              + (f" ({HARDWARE.vram_gb} GB)" if HARDWARE.has_cuda else ""))
        print("\n-- Cấu hình tự đề xuất --")
        for note in (PROFILE.notes or []):
            print(f"   • {note}")
    except Exception as e:  # noqa: BLE001
        print(f"{_ok(False)} Không chạy được resource manager: {e}")

    # LLM keys
    print("\n-- LLM --")
    try:
        from app.ai import llm
        from config import settings
        print(f"   Provider đang chọn: {settings.LLM_PROVIDER}")
        for p in ("openai", "gemini", "deepseek"):
            print(f"   {_ok(bool(settings.llm_key_for(p)))} key {p}")

        # Ollama: kiểm tra server local + model
        ok_ollama, models = _check_ollama(settings)
        print(f"   {_ok(ok_ollama)} Ollama (local) "
              + (f"- model có sẵn: {', '.join(models) or '(chưa tải model nào)'}"
                 if ok_ollama else "- chưa chạy (cài tại https://ollama.com/download)"))
        if settings.LLM_PROVIDER == "ollama":
            if not ok_ollama:
                print("   ⚠ Đang chọn ollama nhưng chưa chạy -> M1 sẽ dùng heuristic. "
                      "Cài Ollama rồi chạy: ollama pull " + settings.OLLAMA_MODEL)
            elif settings.OLLAMA_MODEL.split(":")[0] not in \
                    [m.split(":")[0] for m in models]:
                print(f"   ⚠ Chưa tải model '{settings.OLLAMA_MODEL}'. "
                      f"Chạy: ollama pull {settings.OLLAMA_MODEL}")
        elif not llm.is_configured():
            print("   ⚠ Chưa có key cho provider đang chọn — M1 sẽ dùng heuristic.")
    except Exception as e:  # noqa: BLE001
        print(f"   ❌ {e}")

    print("\nXong. Nếu mọi mục đều ✅ (trừ diarization/GPU tùy chọn) -> chạy: python main.py")


if __name__ == "__main__":
    main()
