# -*- coding: utf-8 -*-
"""ĐO NGƯỠNG TEMPO NGHE ĐƯỢC — trần 1,5 hiện tại là con số AI ĐÓ CHỌN, chưa đo.

CÂU HỎI: ép giọng nhanh tới đâu thì bắt đầu MÉO tới mức nghe không ra chữ?

CÁCH ĐO (2 thước độc lập, thành phần THẬT):
  1. **CHÉP LỜI LẠI BẰNG GROQ RỒI ĐẾM TỪ SAI** (thước chính). Giọng méo thì
     whisper chép sai — đây là thước duy nhất nói được "tai/máy có nghe ra
     chữ không". Đo WER (word error rate) của bản ĐÃ ép so với CHÍNH văn bản
     đưa cho edge-tts đọc.
  2. **MÉO PHỔ VÒNG TRÒN**: ép nhanh k rồi ép chậm 1/k để về đúng độ dài, so
     phổ log-mel với bản gốc. atempo là WSOLA (cắt-dán cửa sổ) nên vòng tròn
     KHÔNG triệt tiêu — số này là méo do CHÍNH thuật toán sinh ra.

Cả hai phải cùng chỉ về một chỗ thì mới lấy làm ngưỡng.

    .venv\\Scripts\\python _do_nguong_tempo.py
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401

import numpy as np  # noqa: E402

from config import settings  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

LAM = Path(REPO) / "_do_nguong_tam"
CACHE = Path(REPO) / "_do_nguong_cache.json"

# Mức tempo cần quét. Trần app hiện tại = 1,50.
MUC = [1.00, 1.10, 1.20, 1.25, 1.30, 1.35, 1.40, 1.50, 1.60, 1.80, 2.00]

# Câu THẬT lấy từ lời dẫn video reup tiếng Anh (dài ngắn khác nhau: 6-24 từ).
CAU = [
    "He never expected the door to open by itself in the middle of the night.",
    "She looked at the photograph one more time and finally understood everything.",
    "Nobody in the village had seen anything like it before.",
    "The doctor came up with a clever idea and saved the boy's life in seconds.",
    "They walked away without saying a single word to each other.",
    "What happened next changed the way the whole family lived for the next ten years.",
]


def ff(args: list[str]) -> None:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {r.stderr[:400]}")


def pcm(path: Path, sr: int = 16000) -> np.ndarray:
    """Đọc file audio ra mảng float mono."""
    r = subprocess.run([settings.FFMPEG_PATH, "-v", "error", "-i", str(path),
                        "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("không đọc được PCM")
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768.0


def _mel_bank(n_fft: int, sr: int, n_mel: int = 40) -> np.ndarray:
    def hz2mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel2hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

    lo, hi = hz2mel(80.0), hz2mel(sr / 2.0)
    pts = mel2hz(np.linspace(lo, hi, n_mel + 2))
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb = np.zeros((n_mel, n_fft // 2 + 1), dtype=np.float32)
    for i in range(n_mel):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        if b == a:
            b = a + 1
        if c == b:
            c = b + 1
        c = min(c, fb.shape[1] - 1)
        b = min(b, c)
        for j in range(a, b):
            fb[i, j] = (j - a) / max(1, (b - a))
        for j in range(b, c):
            fb[i, j] = (c - j) / max(1, (c - b))
    return fb


def logmel(x: np.ndarray, sr: int = 16000, n_fft: int = 512,
           hop: int = 160) -> np.ndarray:
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    w = np.hanning(n_fft).astype(np.float32)
    n = 1 + (len(x) - n_fft) // hop
    fr = np.lib.stride_tricks.as_strided(
        x, shape=(n, n_fft), strides=(x.strides[0] * hop, x.strides[0])).copy()
    sp = np.abs(np.fft.rfft(fr * w, axis=1)) ** 2
    fb = _mel_bank(n_fft, sr)
    return np.log10(sp @ fb.T + 1e-10)


def meo_pho(goc: Path, k: float, tam: Path) -> float:
    """Ép nhanh k RỒI ép chậm 1/k -> so phổ với gốc. dB trung bình/ô mel."""
    a = tam / f"rt_{int(k * 100)}_a.wav"
    b = tam / f"rt_{int(k * 100)}_b.wav"
    ff(["-i", str(goc), "-af", f"aresample=16000,{tg._atempo_chuoi(k)}",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(a)])
    ff(["-i", str(a), "-af", f"atempo={1.0 / k:.6f}",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(b)])
    x, y = pcm(goc), pcm(b)
    n = min(len(x), len(y))
    if n < 4096:
        return 0.0
    mx, my = logmel(x[:n]), logmel(y[:n])
    m = min(len(mx), len(my))
    return float(np.mean(np.abs(mx[:m] - my[:m]))) * 10.0   # -> dB


_BO = re.compile(r"[^\w\s']", re.UNICODE)


def tu(s: str) -> list[str]:
    s = unicodedata.normalize("NFKC", (s or "").lower())
    return [w for w in _BO.sub(" ", s).split() if w]


def wer(ref: str, hyp: str) -> float:
    r, h = tu(ref), tu(hyp)
    if not r:
        return 0.0
    d = np.arange(len(h) + 1, dtype=np.int32)
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1,
                       prev + (0 if r[i - 1] == h[j - 1] else 1))
            prev = cur
    return float(d[len(h)]) / len(r)


def chep(path: Path) -> str:
    from app.core import transcribe as tr
    for _ in range(3):
        try:
            return (tr.transcribe(str(path)).get("text") or "").strip()
        except Exception as e:  # noqa: BLE001
            print(f"      (chép lỗi: {str(e)[:80]} — thử lại)")
            time.sleep(2.0)
    return ""


def main() -> int:
    if LAM.exists():
        shutil.rmtree(LAM, ignore_errors=True)
    LAM.mkdir(parents=True, exist_ok=True)
    voice = tg.giong_theo_ngon_ngu("en")
    print(f"Giọng: {voice} · {len(CAU)} câu × {len(MUC)} mức tempo")

    import asyncio
    from app.core import dubbing
    goc = [LAM / f"c{i}.mp3" for i in range(len(CAU))]
    ok = asyncio.run(dubbing._synth_all(CAU, voice, [str(p) for p in goc]))
    for i, o in enumerate(ok):
        if not o:
            print(f"  ! TTS hỏng câu #{i}")

    cache: dict = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}

    bang: dict[float, dict] = {}
    for k in MUC:
        wers, meos, tocdo = [], [], []
        for i, txt in enumerate(CAU):
            if not ok[i]:
                continue
            src = goc[i]
            d0 = tg.probe_duration(src)
            dst = LAM / f"c{i}_k{int(k * 100)}.wav"
            af = ["aresample=16000"]
            if abs(k - 1.0) > 1e-3:
                af.append(tg._atempo_chuoi(k))
            ff(["-i", str(src), "-af", ",".join(af), "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(dst)])
            d1 = tg.probe_duration(dst)
            tocdo.append(len(tu(txt)) / max(0.05, d1))
            key = f"{i}|{k:.2f}"
            if key not in cache:
                cache[key] = chep(dst)
                CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
            wers.append(wer(txt, cache[key]))
            meos.append(meo_pho(src, k, LAM) if abs(k - 1.0) > 1e-3 else 0.0)
            if i == 0:
                print(f"  tempo {k:.2f}: {d0:.2f}s -> {d1:.2f}s")
        bang[k] = {
            "wer": 100.0 * sum(wers) / max(1, len(wers)),
            "wer_max": 100.0 * max(wers or [0]),
            "meo": sum(meos) / max(1, len(meos)),
            "tu_giay": sum(tocdo) / max(1, len(tocdo)),
            "so_cau_sai": sum(1 for w in wers if w > 0.001),
        }
        b = bang[k]
        print(f"  == k={k:.2f} · WER TB {b['wer']:.2f}% (max {b['wer_max']:.1f}%) "
              f"· câu sai {b['so_cau_sai']}/{len(wers)} "
              f"· méo phổ {b['meo']:.3f} dB · {b['tu_giay']:.2f} từ/giây")

    print("\n=== BẢNG ===")
    print(f"{'tempo':>6} {'WER TB %':>9} {'WER max %':>10} {'câu sai':>8} "
          f"{'méo phổ dB':>11} {'từ/giây':>8}")
    for k in MUC:
        b = bang[k]
        print(f"{k:>6.2f} {b['wer']:>9.2f} {b['wer_max']:>10.1f} "
              f"{b['so_cau_sai']:>8} {b['meo']:>11.3f} {b['tu_giay']:>8.2f}")

    (Path(REPO) / "_do_nguong_ketqua.json").write_text(
        json.dumps({str(k): v for k, v in bang.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(LAM, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
