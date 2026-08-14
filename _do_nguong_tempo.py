# -*- coding: utf-8 -*-
"""ĐO 2 THỨ: (A) cắt lề im có NUỐT CHỮ không · (B) NGƯỠNG TEMPO nghe được.

(A) CẮT LỀ CÓ AN TOÀN KHÔNG — bản vá "cắt lề im lặng edge-tts" là bản vá
    ĐỘNG VÀO TIẾNG NÓI, nên phải chứng minh nó không gọt mất phụ âm đầu/cuối.
    Đo: chép lời lại bằng Groq CẢ bản thô LẪN bản đã cắt, so số từ sai (WER)
    với chính văn bản đưa cho edge-tts đọc.

(B) NGƯỠNG TEMPO — trần 1,5 hiện tại là con số AI ĐÓ CHỌN, chưa ai đo.
    **BẢN ĐẦU CỦA PHÉP ĐO NÀY LÀ PHÉP ĐO VÔ DỤNG, GHI LẠI ĐỂ ĐỪNG LẶP:** chép
    lời bản TTS SẠCH (không nhạc) ra WER **1,11% Y HỆT NHAU ở CẢ 11 mức tempo
    từ 1,00 tới 2,00** — whisper khoẻ quá, nó đọc ra chữ kể cả khi tiếng đã
    méo. Phép đo phẳng tuyệt đối = phát chứng nhận cho mọi mức = vô dụng
    (anh em của bẫy `astats` cổng 53).
    NAY đo trong ĐIỀU KIỆN THẬT: trộn giọng lên **LỚP NHẠC NỀN THẬT** (stem
    Demucs của chính video anh Hùng) đúng mức app trộn (nhạc −2 dB, giọng
    0 dB) rồi mới chép lời. Đó mới là thứ tai nghe.
    Thước thứ hai không cần ASR: **méo phổ vòng tròn** (ép nhanh k rồi ép
    chậm 1/k, so log-mel với gốc) — méo do CHÍNH thuật toán WSOLA sinh ra.

    .venv\\Scripts\\python _do_nguong_tempo.py [A|B|AB]
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import numpy as np  # noqa: E402

import _do_kho_tg as kho  # noqa: E402
from config import settings  # noqa: E402
from app.core import dubbing, thay_giong as tg  # noqa: E402

LAM = REPO / "_do_nguong_tam"
CACHE = REPO / "_do_nguong_cache.json"

MUC = [1.00, 1.10, 1.20, 1.25, 1.30, 1.35, 1.40, 1.50, 1.60, 1.80]

#: Câu THẬT kiểu lời dẫn video reup (dài 4-24 từ, có phụ âm đầu/cuối khó:
#: "s", "t", "k", "ch" — đúng chỗ phép cắt lề dễ gọt mất nhất).
CAU = [
    "Stop.",
    "He never expected the door to open by itself in the middle of the night.",
    "She looked at the photograph one more time and finally understood everything.",
    "Nobody in the village had seen anything like it before.",
    "The doctor came up with a clever trick and saved the boy's life in seconds.",
    "They walked away without saying a single word to each other.",
    "What happened next changed the way the whole family lived for the next ten years.",
    "Six strict experts checked the facts.",
]


def ff(args: list[str]) -> None:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {r.stderr[:400]}")


def pcm(path: Path, sr: int = 16000) -> np.ndarray:
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

    pts = mel2hz(np.linspace(hz2mel(80.0), hz2mel(sr / 2.0), n_mel + 2))
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb = np.zeros((n_mel, n_fft // 2 + 1), dtype=np.float32)
    for i in range(n_mel):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        b = max(b, a + 1)
        c = min(max(c, b + 1), fb.shape[1] - 1)
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
    return np.log10(sp @ _mel_bank(n_fft, sr).T + 1e-10)


def meo_pho(goc: Path, k: float, tam: Path) -> float:
    a = tam / f"rt_a_{int(k * 100)}.wav"
    b = tam / f"rt_b_{int(k * 100)}.wav"
    ff(["-i", str(goc), "-af", f"aresample=16000,{tg._atempo_chuoi(k)}",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(a)])
    ff(["-i", str(a), "-af", f"atempo={1.0 / k:.6f}", "-ac", "1",
        "-ar", "16000", "-c:a", "pcm_s16le", str(b)])
    x, y = pcm(goc), pcm(b)
    n = min(len(x), len(y))
    if n < 4096:
        return 0.0
    mx, my = logmel(x[:n]), logmel(y[:n])
    m = min(len(mx), len(my))
    return float(np.mean(np.abs(mx[:m] - my[:m]))) * 10.0


_BO = re.compile(r"[^\w\s']", re.UNICODE)


def tu(s: str) -> list[str]:
    return [w for w in _BO.sub(" ", unicodedata.normalize(
        "NFKC", (s or "").lower())).split() if w]


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


_C: dict = {}


def _nap() -> None:
    global _C
    if CACHE.exists():
        try:
            _C = json.loads(CACHE.read_text(encoding="utf-8"))
            return
        except Exception:  # noqa: BLE001
            pass
    _C = {}


def chep(path: Path, khoa: str) -> str:
    if khoa in _C:
        return _C[khoa]
    from app.core import transcribe as tr
    txt = ""
    for _ in range(3):
        try:
            txt = (tr.transcribe(str(path)).get("text") or "").strip()
            break
        except Exception as e:  # noqa: BLE001
            print(f"      (chép lỗi: {str(e)[:70]} — thử lại)")
            time.sleep(2.0)
    _C[khoa] = txt
    CACHE.write_text(json.dumps(_C, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return txt


def synth(voice: str) -> list[Path]:
    ps = [LAM / f"tho_{i}.mp3" for i in range(len(CAU))]
    ok = asyncio.run(dubbing._synth_all(CAU, voice, [str(p) for p in ps]))
    if not all(ok):
        raise RuntimeError("TTS hỏng — chạy lại")
    return ps


# ==================================================================
def phan_A(tho: list[Path]) -> None:
    print("\n########## (A) CẮT LỀ IM CÓ NUỐT CHỮ KHÔNG ##########")
    print(f"{'ký tự':>6} {'thô s':>7} {'sạch s':>7} {'bỏ s':>6} "
          f"{'WER thô':>8} {'WER sạch':>9}")
    w_tho, w_sach, bo = [], [], 0.0
    for i, txt in enumerate(CAU):
        sach = LAM / f"sach_{i}.wav"
        d0 = tg.probe_duration(tho[i])
        d1 = tg.cat_le_im(tho[i], sach)
        a = wer(txt, chep(tho[i], f"A|tho|{i}"))
        b = wer(txt, chep(sach, f"A|sach|{i}"))
        w_tho.append(a)
        w_sach.append(b)
        bo += d0 - d1
        print(f"{len(txt):>6} {d0:>7.3f} {d1:>7.3f} {d0 - d1:>6.3f} "
              f"{100 * a:>7.1f}% {100 * b:>8.1f}%")
    n = len(CAU)
    print(f"  => WER thô {100 * sum(w_tho) / n:.2f}% · "
          f"WER sạch {100 * sum(w_sach) / n:.2f}% · bỏ tổng {bo:.2f}s")
    xau = [i for i in range(n) if w_sach[i] > w_tho[i] + 1e-9]
    print(f"  => câu bị CẮT LÀM SAI THÊM: {len(xau)}/{n} "
          f"{'(' + ', '.join(map(str, xau)) + ')' if xau else ''}")


# ==================================================================
def phan_B(tho: list[Path]) -> None:
    print("\n########## (B) NGƯỠNG TEMPO — CÓ NHẠC NỀN THẬT ##########")
    k = kho.chuan_bi("zh", can_nhac=True)
    nhac = k["nhac"]
    print(f"  nền: stem Demucs của {k['ten']} ({tg.probe_duration(nhac):.1f}s)")

    bang = {}
    for km in MUC:
        w_sach, w_nhac, meos, tocdo = [], [], [], []
        for i, txt in enumerate(CAU):
            src = LAM / f"sach_{i}.wav"
            if not src.exists():
                tg.cat_le_im(tho[i], src)
            ep = LAM / f"ep_{i}_{int(km * 100)}.wav"
            af = ["aresample=44100"]
            if abs(km - 1.0) > 1e-3:
                af.append(tg._atempo_chuoi(km))
            ff(["-i", str(src), "-af", ",".join(af), "-ac", "1", "-ar",
                "44100", "-c:a", "pcm_s16le", str(ep)])
            d = tg.probe_duration(ep)
            tocdo.append(len(tu(txt)) / max(0.05, d))
            # TRỘN lên nhạc nền THẬT, đúng mức app trộn (nhạc -2 dB, giọng 0)
            tron = LAM / f"tron_{i}_{int(km * 100)}.wav"
            ff(["-ss", f"{2.0 + i * 5.0:.1f}", "-t", f"{d + 0.4:.3f}",
                "-i", str(nhac), "-i", str(ep), "-filter_complex",
                "[0:a]volume=-2dB,aformat=channel_layouts=mono[nh];"
                "[1:a]volume=0dB[gi];"
                "[nh][gi]amix=inputs=2:duration=first:normalize=0[o]",
                "-map", "[o]", "-ac", "1", "-ar", "44100",
                "-c:a", "pcm_s16le", str(tron)])
            w_sach.append(wer(txt, chep(ep, f"B|sach|{i}|{km:.2f}")))
            w_nhac.append(wer(txt, chep(tron, f"B|nhac|{i}|{km:.2f}")))
            meos.append(meo_pho(src, km, LAM) if abs(km - 1.0) > 1e-3 else 0.0)
        n = len(CAU)
        bang[km] = {
            "wer_sach": 100 * sum(w_sach) / n,
            "wer_nhac": 100 * sum(w_nhac) / n,
            "sai_nhac": sum(1 for x in w_nhac if x > 1e-9),
            "meo": sum(meos) / n,
            "tu_giay": sum(tocdo) / n,
        }
        b = bang[km]
        print(f"  k={km:.2f} · WER sạch {b['wer_sach']:5.2f}% · "
              f"WER CÓ NHẠC {b['wer_nhac']:5.2f}% ({b['sai_nhac']}/{n} câu) · "
              f"méo phổ {b['meo']:.3f} dB · {b['tu_giay']:.2f} từ/giây")

    print("\n=== BẢNG NGƯỠNG ===")
    print(f"{'tempo':>6} {'WER sạch %':>11} {'WER +nhạc %':>12} "
          f"{'câu sai':>8} {'méo phổ dB':>11} {'từ/giây':>8}")
    for km in MUC:
        b = bang[km]
        print(f"{km:>6.2f} {b['wer_sach']:>11.2f} {b['wer_nhac']:>12.2f} "
              f"{b['sai_nhac']:>8} {b['meo']:>11.3f} {b['tu_giay']:>8.2f}")
    (REPO / "_do_nguong_ketqua.json").write_text(
        json.dumps({f"{k2:.2f}": v for k2, v in bang.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    phan = (sys.argv[1] if len(sys.argv) > 1 else "AB").upper()
    _nap()
    if LAM.exists():
        shutil.rmtree(LAM, ignore_errors=True)
    LAM.mkdir(parents=True, exist_ok=True)
    voice = tg.giong_theo_ngon_ngu("en")
    print(f"Giọng: {voice} · {len(CAU)} câu")
    tho = synth(voice)
    if "A" in phan:
        phan_A(tho)
    if "B" in phan:
        phan_B(tho)
    shutil.rmtree(LAM, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
