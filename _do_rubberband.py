# -*- coding: utf-8 -*-
"""ĐO `atempo` (WSOLA) so với `rubberband` (phase-vocoder) TRÊN CÙNG MỘT THƯỚC.

VÌ SAO CÓ PHÉP ĐO NÀY — ĐỌC TRƯỚC KHI SỬA `thay_giong.py`:
v2.27.0 đã CỐ Ý bỏ đường ép nhanh `atempo` (commit `29a0fb2`). Lý do ghi trong
commit đó gồm HAI phần, và chỉ MỘT phần liên quan tới việc đổi bộ lọc:
  (1) `atempo` là WSOLA (cắt sóng thành cửa sổ rồi dán chồng) -> méo phổ đo
      được 5,357 dB ở 1,20 · 6,765 ở 1,50 · 8,071 ở 1,80.  <-- ĐỔI BỘ LỌC CHỮA
  (2) GỐC RỄ là app đang ép nén KHOẢNG IM của edge-tts chứ không phải tiếng
      nói (câu 12 ký tự: 58% file là im lặng). Chữa bằng cắt lề im + rút ngắn
      chữ + `rate` của edge-tts.                            <-- ĐỔI BỘ LỌC KHÔNG CHỮA

Tức lý do (2) VẪN CÒN NGUYÊN GIÁ TRỊ và `rubberband` KHÔNG thay thế nó. Thứ tự
ưu tiên của `khop_thoi_gian` (lọt sẵn -> mượn -> ép) PHẢI GIỮ. Việc đổi bộ lọc
chỉ làm cho BƯỚC CUỐI CÙNG — cái vẫn còn đó và vẫn bắn trên câu quá dài — rẻ
hơn về chất lượng. Đo để biết rẻ hơn bao nhiêu, và có mất gì không.

THƯỚC (giống thước đã dùng ở `_do_nguong_tempo.py`, cộng một thước MỚI):
  · ĐỐI CHỨNG "chép nguyên file"  — chỉ `aresample`, không bộ lọc nào.
    Số này PHẢI ~0,000 dB; khác 0 là thước hỏng, đừng đọc tiếp bảng.
  · MỘT LƯỢT ở k=1,00 (MỚI)      — bộ lọc KHÔNG ĐƯỢC LÀM GÌ ở hệ số 1,0.
    Đây là câu hỏi "bộ lọc có phá tiếng ngay cả khi không ép gì không".
  · VÒNG TRÒN k rồi 1/k          — méo do CHÍNH thuật toán sinh ra.
  · ĐỘ DÀI ĐẦU RA                — ép đúng khung hay lệch (`d/k` so với đo thật).
  · CHÉP NGƯỢC BẰNG GROQ         — đếm từ sai, thước duy nhất "còn nghe ra chữ".
  · CPU-GIÂY                     — rubberband là phase vocoder, đắt hơn WSOLA.

  .venv\\Scripts\\python -u _do_rubberband.py [nhanh|du]
"""
from __future__ import annotations

import asyncio
import json
import os
import re
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

from config import settings  # noqa: E402
from app.core import dubbing  # noqa: E402

LAM = REPO / "_do_rb_tam"
CACHE = REPO / "_do_rb_cache.json"
KQ = REPO / "_do_rb_ketqua.json"

#: Hệ số ĐO. 1,00 là mục quan trọng nhất (bộ lọc có tự phá tiếng không).
MUC = [1.00, 1.10, 1.20, 1.30, 1.50, 1.80]

#: Câu THẬT kiểu lời dẫn video reup — có phụ âm bật (t, k, p, s, ch) vì đó
#: đúng chỗ WSOLA cắt-dán làm hỏng trước tiên.
CAU = [
    "He never expected the door to open by itself in the middle of the night.",
    "She looked at the photograph one more time and finally understood everything.",
    "Nobody in the village had seen anything like it before.",
    "The doctor came up with a clever trick and saved the boy's life in seconds.",
    "They walked away without saying a single word to each other.",
    "What happened next changed the way the whole family lived for ten years.",
]
GIONG = "en-US-JennyNeural"

_C: dict = {}


# ══════════════════════ hạ tầng đo ══════════════════════
def ff(args: list[str], timeout: float = 180.0) -> None:
    """ffmpeg BẮT BUỘC có timeout (bẫy `-t` sai chỗ ghi vô hạn 115 MB/giây)."""
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {r.stderr[:400]}")


def ff_cpu(args: list[str], timeout: float = 180.0) -> float:
    """Chạy ffmpeg, trả CPU-GIÂY thật (GetProcessTimes qua psutil)."""
    import psutil
    t0 = time.perf_counter()
    p = psutil.Popen([settings.FFMPEG_PATH, "-y", "-hide_banner",
                      "-loglevel", "error", *args],
                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    cpu = 0.0
    try:
        while p.poll() is None:
            try:
                ct = p.cpu_times()
                cpu = max(cpu, ct.user + ct.system)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.02)
            if time.perf_counter() - t0 > timeout:
                p.kill()
                raise RuntimeError("ffmpeg quá giờ")
    finally:
        try:
            p.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass
    return cpu


def pcm(path: Path, sr: int = 16000) -> np.ndarray:
    r = subprocess.run([settings.FFMPEG_PATH, "-v", "error", "-i", str(path),
                        "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True, timeout=180)
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768.0


def do_dai(path: Path) -> float:
    r = subprocess.run([settings.FFPROBE_PATH, "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, timeout=60)
    try:
        return float((r.stdout or "0").strip())
    except Exception:  # noqa: BLE001
        return 0.0


def _mel_bank(n_fft: int, sr: int, n_mel: int = 40) -> np.ndarray:
    def hz2mel(f):
        return 2595.0 * np.log10(1.0 + f / 700.0)

    def mel2hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    lo, hi = hz2mel(50.0), hz2mel(sr / 2.0)
    pts = mel2hz(np.linspace(lo, hi, n_mel + 2))
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb = np.zeros((n_mel, n_fft // 2 + 1), dtype=np.float32)
    for i in range(n_mel):
        a, b, c = bins[i], bins[i + 1], bins[i + 2]
        if b == a:
            b = a + 1
        if c == b:
            c = b + 1
        c = min(c, n_fft // 2)
        b = min(b, c)
        for j in range(a, b):
            fb[i, j] = (j - a) / max(1, b - a)
        for j in range(b, c):
            fb[i, j] = (c - j) / max(1, c - b)
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


def lech_db(a: Path, b: Path) -> float:
    """Lệch log-mel giữa 2 file, quy về thang dB (×10) — THƯỚC CHÍNH."""
    x, y = pcm(a), pcm(b)
    n = min(len(x), len(y))
    if n < 4096:
        return -1.0
    mx, my = logmel(x[:n]), logmel(y[:n])
    m = min(len(mx), len(my))
    return float(np.mean(np.abs(mx[:m] - my[:m]))) * 10.0


# ══════════════════════ chuỗi filter ══════════════════════
def chuoi_atempo(k: float) -> str:
    parts = []
    while k > 2.0:
        parts.append("atempo=2.0")
        k /= 2.0
    parts.append(f"atempo={k:.4f}")
    return ",".join(parts)


def chuoi_rb(k: float) -> str:
    #: `rubberband` nhận tempo bất kỳ (0,01..100) nên KHÔNG phải chia tầng.
    return f"rubberband=tempo={k:.4f}"


# ══════════════════════ chép lời ══════════════════════
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


_BO = re.compile(r"[^\w\s']", re.UNICODE)


def tu(s: str) -> list[str]:
    s = unicodedata.normalize("NFKC", (s or "").lower())
    return [w for w in _BO.sub(" ", s).split() if w]


def wer(ref: str, hyp: str) -> float:
    a, b = tu(ref), tu(hyp)
    if not a:
        return 0.0
    d = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1,
                       prev + (a[i - 1] != b[j - 1]))
            prev = cur
    return d[len(b)] / len(a) * 100.0


# ══════════════════════ dò bộ lọc ══════════════════════
def co_rubberband() -> bool:
    try:
        r = subprocess.run([settings.FFMPEG_PATH, "-hide_banner", "-filters"],
                           capture_output=True, text=True, timeout=60)
        return bool(re.search(r"^\s*\S*\s+rubberband\s", r.stdout or "",
                              re.MULTILINE))
    except Exception:  # noqa: BLE001
        return False


# ══════════════════════ phần đo ══════════════════════
def synth() -> list[Path]:
    ps = [LAM / f"tho_{i}.mp3" for i in range(len(CAU))]
    if all(p.exists() and p.stat().st_size > 1000 for p in ps):
        return ps
    ok = asyncio.run(dubbing._synth_all(CAU, GIONG, [str(p) for p in ps]))
    if not all(ok):
        raise RuntimeError("TTS hỏng — chạy lại")
    return ps


def main() -> int:
    che_do = (sys.argv[1] if len(sys.argv) > 1 else "nhanh").lower()
    LAM.mkdir(parents=True, exist_ok=True)
    _nap()

    print("=" * 74)
    print("ĐO `atempo` (WSOLA) so với `rubberband` (phase vocoder)")
    print("=" * 74)
    print(f"ffmpeg  : {settings.FFMPEG_PATH}")
    import shutil as _sh
    print(f"          -> {_sh.which(settings.FFMPEG_PATH) or '(tuyệt đối)'}")
    print(f"rubberband có trong ffmpeg này: "
          f"{'CÓ' if co_rubberband() else 'KHÔNG'}")
    if not co_rubberband():
        print("!! ffmpeg này KHÔNG có rubberband — bảng dưới chỉ đo atempo.")

    print("\n--- sinh giọng bằng edge-tts ---")
    tho = synth()
    for i, p in enumerate(tho):
        print(f"  câu {i}: {do_dai(p):6.3f}s  {len(CAU[i]):3d} ký tự")

    # ── chuẩn hoá về wav gốc (mọi phép so đều đi từ ĐÂY, không từ mp3) ──
    goc = []
    for i, p in enumerate(tho):
        g = LAM / f"goc_{i}.wav"
        ff(["-i", str(p), "-af", "aresample=16000", "-ac", "1", "-ar",
            "16000", "-c:a", "pcm_s16le", str(g)])
        goc.append(g)

    kq: dict = {"ffmpeg": settings.FFMPEG_PATH,
                "co_rubberband": co_rubberband(), "bang": {}}

    # ══════════════ (0) ĐỐI CHỨNG: chép nguyên file ══════════════
    print("\n" + "=" * 74)
    print("(0) ĐỐI CHỨNG — chỉ `aresample`, KHÔNG bộ lọc nào")
    print("    Số này phải ~0,000 dB. Khác 0 = THƯỚC HỎNG, đừng đọc bảng dưới.")
    print("=" * 74)
    dc = []
    for i, g in enumerate(goc):
        d = LAM / f"dc_{i}.wav"
        ff(["-i", str(g), "-af", "aresample=16000", "-ac", "1", "-ar",
            "16000", "-c:a", "pcm_s16le", str(d)])
        dc.append(lech_db(g, d))
    print(f"  lệch TB = {np.mean(dc):.3f} dB   (từng câu: "
          f"{' · '.join(f'{v:.3f}' for v in dc)})")
    kq["doi_chung_db"] = float(np.mean(dc))

    # ══════════════ (1) MỘT LƯỢT — bộ lọc có tự phá tiếng không ══════════════
    print("\n" + "=" * 74)
    print("(1) MỘT LƯỢT qua bộ lọc — so với ĐỐI CHỨNG chép nguyên file")
    print("    Cột k=1,00 trả lời: *bộ lọc có phá tiếng NGAY CẢ KHI không ép*")
    print("=" * 74)
    print(f"{'k':>6} | {'atempo dB':>10} | {'rubberband dB':>14} | "
          f"{'dài atempo':>11} | {'dài rb':>9} | {'đích s':>8}")
    print("-" * 74)
    rb_ok = co_rubberband()
    for k in MUC:
        at_db, rb_db, at_dd, rb_dd, dich = [], [], [], [], []
        for i, g in enumerate(goc):
            d0 = do_dai(g)
            dich.append(d0 / k)
            a = LAM / f"a1_{i}_{int(k*100)}.wav"
            ff(["-i", str(g), "-af", f"aresample=16000,{chuoi_atempo(k)}",
                "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(a)])
            at_dd.append(do_dai(a))
            # so với ĐỐI CHỨNG: ở k=1,0 độ dài bằng nhau nên so thẳng được;
            # ở k>1 thì so là vô nghĩa -> chỉ đọc cột k=1,00.
            at_db.append(lech_db(LAM / f"dc_{i}.wav", a) if abs(k - 1.0) < 1e-9
                         else float("nan"))
            if rb_ok:
                b = LAM / f"r1_{i}_{int(k*100)}.wav"
                ff(["-i", str(g), "-af", f"aresample=16000,{chuoi_rb(k)}",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(b)])
                rb_dd.append(do_dai(b))
                rb_db.append(lech_db(LAM / f"dc_{i}.wav", b)
                             if abs(k - 1.0) < 1e-9 else float("nan"))
        s_at = (f"{np.mean(at_db):10.3f}" if abs(k - 1.0) < 1e-9 else
                f"{'—':>10}")
        s_rb = (f"{np.mean(rb_db):14.3f}" if (rb_ok and abs(k - 1.0) < 1e-9)
                else f"{'—':>14}")
        print(f"{k:6.2f} | {s_at} | {s_rb} | {np.mean(at_dd):11.3f} | "
              f"{np.mean(rb_dd) if rb_ok else 0:9.3f} | {np.mean(dich):8.3f}")
        kq["bang"][f"{k:.2f}"] = {
            "atempo_1luot_db": (float(np.mean(at_db))
                                if abs(k - 1.0) < 1e-9 else None),
            "rb_1luot_db": (float(np.mean(rb_db))
                            if (rb_ok and abs(k - 1.0) < 1e-9) else None),
            "atempo_dai": float(np.mean(at_dd)),
            "rb_dai": float(np.mean(rb_dd)) if rb_ok else None,
            "dai_dich": float(np.mean(dich)),
        }

    # ══════════════ (2) ÉP ĐÚNG KHUNG KHÔNG ══════════════
    print("\n" + "=" * 74)
    print("(2) ÉP ĐÚNG KHUNG — sai lệch độ dài so với đích `d/k` (%)")
    print("=" * 74)
    print(f"{'k':>6} | {'atempo %':>9} | {'rubberband %':>13}")
    print("-" * 74)
    for k in MUC:
        b = kq["bang"][f"{k:.2f}"]
        e_at = (b["atempo_dai"] - b["dai_dich"]) / max(1e-6, b["dai_dich"]) * 100
        s_rb = (f"{(b['rb_dai'] - b['dai_dich']) / max(1e-6, b['dai_dich']) * 100:13.2f}"
                if b["rb_dai"] else f"{'—':>13}")
        print(f"{k:6.2f} | {e_at:9.2f} | {s_rb}")
        b["sai_khung_atempo_pc"] = float(e_at)
        b["sai_khung_rb_pc"] = (
            float((b["rb_dai"] - b["dai_dich"]) / max(1e-6, b["dai_dich"]) * 100)
            if b["rb_dai"] else None)

    # ══════════════ (3) VÒNG TRÒN k rồi 1/k ══════════════
    print("\n" + "=" * 74)
    print("(3) VÒNG TRÒN: ép k rồi ép ngược 1/k, so với GỐC")
    print("    Méo do CHÍNH thuật toán sinh ra (thước cũ của `_do_nguong_tempo`)")
    print("=" * 74)
    print(f"{'k':>6} | {'atempo dB':>10} | {'rubberband dB':>14}")
    print("-" * 74)
    for k in MUC:
        at_v, rb_v = [], []
        for i, g in enumerate(goc):
            a1 = LAM / f"v_a1_{i}_{int(k*100)}.wav"
            a2 = LAM / f"v_a2_{i}_{int(k*100)}.wav"
            ff(["-i", str(g), "-af", f"aresample=16000,{chuoi_atempo(k)}",
                "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(a1)])
            ff(["-i", str(a1), "-af", f"atempo={1.0/k:.6f}", "-ac", "1",
                "-ar", "16000", "-c:a", "pcm_s16le", str(a2)])
            at_v.append(lech_db(g, a2))
            if rb_ok:
                b1 = LAM / f"v_r1_{i}_{int(k*100)}.wav"
                b2 = LAM / f"v_r2_{i}_{int(k*100)}.wav"
                ff(["-i", str(g), "-af", f"aresample=16000,{chuoi_rb(k)}",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(b1)])
                ff(["-i", str(b1), "-af", f"rubberband=tempo={1.0/k:.6f}",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(b2)])
                rb_v.append(lech_db(g, b2))
        s_rb = f"{np.mean(rb_v):14.3f}" if rb_ok else f"{'—':>14}"
        print(f"{k:6.2f} | {np.mean(at_v):10.3f} | {s_rb}")
        kq["bang"][f"{k:.2f}"]["atempo_vongtron_db"] = float(np.mean(at_v))
        kq["bang"][f"{k:.2f}"]["rb_vongtron_db"] = (float(np.mean(rb_v))
                                                   if rb_ok else None)

    # ══════════════ (4) CPU-GIÂY ══════════════
    print("\n" + "=" * 74)
    print("(4) CPU-GIÂY (ĐAN XEN a,r,a,r — máy này luôn có việc nền)")
    print("=" * 74)
    if rb_ok:
        c_at, c_rb = [], []
        for _v in range(3):
            for i, g in enumerate(goc[:3]):
                c_at.append(ff_cpu(["-i", str(g), "-af",
                                    f"aresample=16000,{chuoi_atempo(1.5)}",
                                    "-ac", "1", "-ar", "16000", "-c:a",
                                    "pcm_s16le",
                                    str(LAM / f"cpu_a_{i}.wav")]))
                c_rb.append(ff_cpu(["-i", str(g), "-af",
                                    f"aresample=16000,{chuoi_rb(1.5)}",
                                    "-ac", "1", "-ar", "16000", "-c:a",
                                    "pcm_s16le",
                                    str(LAM / f"cpu_r_{i}.wav")]))
        print(f"  atempo     trung vị {np.median(c_at):.3f} CPU-giây/câu")
        print(f"  rubberband trung vị {np.median(c_rb):.3f} CPU-giây/câu")
        print(f"  -> rubberband đắt hơn {np.median(c_rb)/max(1e-6,np.median(c_at)):.2f} lần")
        kq["cpu_atempo"] = float(np.median(c_at))
        kq["cpu_rb"] = float(np.median(c_rb))

    # ══════════════ (5) CHÉP NGƯỢC BẰNG GROQ ══════════════
    if che_do == "du":
        print("\n" + "=" * 74)
        print("(5) CHÉP NGƯỢC BẰNG GROQ — đếm từ sai (WER %)")
        print("=" * 74)
        print(f"{'k':>6} | {'atempo WER':>11} | {'rubberband WER':>15}")
        print("-" * 74)
        for k in [1.00, 1.30, 1.50, 1.80]:
            w_at, w_rb = [], []
            for i, g in enumerate(goc):
                a = LAM / f"a1_{i}_{int(k*100)}.wav"
                if a.exists():
                    w_at.append(wer(CAU[i], chep(a, f"at_{i}_{int(k*100)}")))
                if rb_ok:
                    b = LAM / f"r1_{i}_{int(k*100)}.wav"
                    if b.exists():
                        w_rb.append(wer(CAU[i], chep(b, f"rb_{i}_{int(k*100)}")))
            s_rb = f"{np.mean(w_rb):15.2f}" if w_rb else f"{'—':>15}"
            print(f"{k:6.2f} | {np.mean(w_at):11.2f} | {s_rb}")
            kq["bang"][f"{k:.2f}"]["wer_atempo"] = float(np.mean(w_at))
            kq["bang"][f"{k:.2f}"]["wer_rb"] = (float(np.mean(w_rb))
                                               if w_rb else None)

    KQ.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nĐã ghi {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
