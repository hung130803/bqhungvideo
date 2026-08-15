# -*- coding: utf-8 -*-
"""ĐO BIẾN THỂ GIỌNG edge-tts (đổi `pitch`) — LOẠI biến thể nào MÉO.

VÌ SAO: edge-tts chỉ có **2 giọng tiếng Việt** (`vi-VN-NamMinhNeural` nam,
`vi-VN-HoaiMyNeural` nữ). 200-300 kênh mà chung 2 giọng thì kênh nào cũng
kêu giống nhau. `pitch` sinh thêm biến thể **không tốn thêm một lượt mạng
nào** (cùng một lời gọi `Communicate`).

**TÔI KHÔNG CÓ TAI — nên ở đây KHÔNG có một chữ nào về "nghe hay/nghe dở".**
Chỉ hai số ĐO ĐƯỢC:

  1. **SAI TỪ (WER)** — cho **Groq chép ngược** chính file vừa đọc rồi đếm từ
     sai so với chữ đưa vào. Đây là cửa LOẠI: pitch đẩy quá tay thì phụ âm
     vỡ và máy nghe sai chữ. So với mốc `+0Hz` của CHÍNH giọng đó, không so
     với 0 tuyệt đối (edge-tts + Groq vốn đã có sai số nền).
  2. **F0 TRUNG VỊ (Hz)** — cao độ THẬT đo bằng tự tương quan trên sóng.
     Cửa này bắt **BIẾN THỂ GIẢ**: nếu F0 gần như không đổi thì "biến thể"
     ấy chỉ là cùng một giọng, thêm vào chỉ tổ rối danh sách.

CÁI HAI SỐ NÀY **KHÔNG** ĐO ĐƯỢC, ghi thẳng: nghe có tự nhiên không, có bị
"giọng chipmunk" không. Máy chép đúng chữ mà tai người thấy chối thì hai số
trên vẫn đẹp. Ai duyệt lần cuối phải NGHE — file để sẵn ở `_do_bt_giong/`.

  .venv\\Scripts\\python -u _do_bien_the_giong.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SAN = REPO / "_do_bt_giong"

#: Câu THẬT — lấy nguyên bản dịch tốt của corpus anh Hùng (`_do_bo_hong.TOT`)
#: nên đúng loại chữ đường thay giọng sẽ phải đọc.
from _do_bo_hong import TOT                              # noqa: E402

CAU = [d for _g, d in TOT][:10]

GIONG = ("vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural")

#: Quét ĐỀU hai phía quanh mốc, đủ rộng để thấy chỗ VỠ chứ không chỉ chỗ đẹp.
#: Không quét thì không biết trần nằm ở đâu, và "chọn ±20Hz" chỉ là con số bịa.
PITCH = ("-40Hz", "-30Hz", "-20Hz", "-10Hz", "+0Hz",
         "+10Hz", "+20Hz", "+30Hz", "+40Hz")


# --------------------------------------------------------------------------
def ffmpeg() -> str:
    p = REPO / "bin" / "ffmpeg.exe"
    return str(p) if p.exists() else "ffmpeg"


def sang_wav(mp3: Path, wav: Path) -> bool:
    r = subprocess.run(
        [ffmpeg(), "-y", "-v", "error", "-i", str(mp3), "-ac", "1",
         "-ar", "16000", "-f", "wav", str(wav)],
        capture_output=True, timeout=120)      # LUẬT: mọi subprocess có timeout
    return r.returncode == 0 and wav.exists() and wav.stat().st_size > 1000


def f0_trung_vi(wav: Path) -> float:
    """Cao độ trung vị (Hz) bằng TỰ TƯƠNG QUAN, chỉ tính khung CÓ TIẾNG.

    Đơn giản mà đủ dùng cho việc ở đây: cần biết hai biến thể có KHÁC NHAU
    thật không, không cần độ chính xác của máy phân tích giọng.
    """
    import numpy as np

    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    x = x.astype(np.float64) / 32768.0
    if x.size < sr // 4:
        return 0.0
    n = int(0.040 * sr)                     # khung 40 ms
    hop = int(0.020 * sr)
    lo, hi = int(sr / 400.0), int(sr / 70.0)   # 70-400 Hz: dải giọng người
    nguong = float(np.sqrt((x ** 2).mean())) * 0.5
    ra = []
    for i in range(0, max(0, x.size - n), hop):
        k = x[i:i + n]
        if float(np.sqrt((k ** 2).mean())) < nguong:
            continue                        # khung im -> không có cao độ
        k = k - k.mean()
        r = np.correlate(k, k, mode="full")[n - 1:]
        if r[0] <= 0:
            continue
        seg = r[lo:hi]
        if seg.size == 0:
            continue
        j = int(np.argmax(seg)) + lo
        if r[j] / r[0] < 0.30:              # tương quan yếu -> không phải tiếng
            continue
        ra.append(sr / float(j))
    return round(float(np.median(ra)), 1) if ra else 0.0


def chuan(s: str) -> list[str]:
    from app.ai.recap import _word_tokens
    import re
    s = re.sub(r"[^0-9A-Za-zÀ-ỹ\s]", " ", (s or "").lower())
    return _word_tokens(re.sub(r"\s+", " ", s).strip())


def wer(goc: str, nghe: str) -> tuple[float, int, int]:
    """Tỉ lệ sai từ (Levenshtein trên TỪ). Trả (tỉ lệ, số lỗi, số từ gốc)."""
    a, b = chuan(goc), chuan(nghe)
    if not a:
        return 0.0, 0, 0
    tr = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        moi = [i]
        for j in range(1, len(b) + 1):
            moi.append(min(tr[j] + 1, moi[-1] + 1,
                           tr[j - 1] + (a[i - 1] != b[j - 1])))
        tr = moi
    return tr[len(b)] / len(a), tr[len(b)], len(a)


def doc(voice: str, pitch: str, thu_muc: Path) -> list[Path]:
    from app.core import dubbing
    thu_muc.mkdir(parents=True, exist_ok=True)
    paths = [str(thu_muc / f"c{i:02d}.mp3") for i in range(len(CAU))]
    ok, _w = asyncio.run(
        dubbing._synth_all_words(CAU, voice, paths, pitch=pitch))
    return [Path(p) for p, o in zip(paths, ok) if o]


def chep_lai(files: list[Path]) -> list[str]:
    """Groq chép ngược. Nối các câu thành 1 file cho rẻ lượt gọi -> nhưng
    như vậy không biết câu nào ra câu nào; nên chép TỪNG file (câu ngắn,
    Groq nhanh, và key của anh Hùng gần vô hạn — ưu tiên CHẤT LƯỢNG SỐ ĐO)."""
    from app.core import transcribe
    ra = []
    for p in files:
        try:
            kq = transcribe.transcribe(str(p), language="vi")
            ra.append(str(kq.get("text") or ""))
        except Exception as e:               # noqa: BLE001
            ra.append(f"<<LỖI {e}>>")
    return ra


def main() -> int:
    shutil.rmtree(SAN, ignore_errors=True)
    SAN.mkdir(parents=True, exist_ok=True)
    print("=" * 76)
    print("ĐO BIẾN THỂ GIỌNG edge-tts — 2 giọng Việt × "
          f"{len(PITCH)} mức pitch × {len(CAU)} câu")
    print("SỐ ĐO: sai từ (Groq chép ngược) + F0 trung vị. KHÔNG có nhận xét "
          "'nghe hay' — tôi không có tai.")
    print("=" * 76)

    bang: dict[tuple[str, str], dict] = {}
    for voice in GIONG:
        for pitch in PITCH:
            tag = f"{voice.split('-')[2]}_{pitch.replace('+', 'p').replace('-', 'm')}"
            tm = SAN / tag
            files = doc(voice, pitch, tm)
            if len(files) < len(CAU):
                print(f"\n{voice} {pitch}: edge-tts CHỈ ĐỌC ĐƯỢC "
                      f"{len(files)}/{len(CAU)} câu")
            # F0
            f0s = []
            for p in files:
                w = p.with_suffix(".wav")
                if sang_wav(p, w):
                    v = f0_trung_vi(w)
                    if v:
                        f0s.append(v)
            f0 = round(sum(f0s) / len(f0s), 1) if f0s else 0.0
            # WER
            nghe = chep_lai(files)
            loi = tu = 0
            for i, t in enumerate(nghe):
                _r, l, n = wer(CAU[i], t)
                loi += l
                tu += n
            ty = 100.0 * loi / max(1, tu)
            bang[(voice, pitch)] = {"f0": f0, "wer": ty, "loi": loi, "tu": tu,
                                    "so_cau": len(files), "nghe": nghe}
            print(f"  {voice:<22} {pitch:>6}  F0 {f0:>6.1f} Hz  "
                  f"sai từ {loi:>3}/{tu:<3} = {ty:5.2f}%  "
                  f"({len(files)}/{len(CAU)} câu)")

    # ---- KẾT LUẬN THEO SỐ ----
    print("\n" + "=" * 76)
    print("KẾT LUẬN — mốc là `+0Hz` CỦA CHÍNH GIỌNG ĐÓ")
    print("=" * 76)
    for voice in GIONG:
        moc = bang[(voice, "+0Hz")]
        print(f"\n{voice}: mốc F0 {moc['f0']} Hz · sai từ nền {moc['wer']:.2f}%")
        print("   pitch |    F0 | ΔF0 |  sai từ | Δ sai từ | kết luận")
        for pitch in PITCH:
            b = bang[(voice, pitch)]
            d_f0 = b["f0"] - moc["f0"]
            d_wer = b["wer"] - moc["wer"]
            if b["so_cau"] < len(CAU):
                kl = "LOẠI — edge-tts không đọc đủ câu"
            elif abs(d_f0) < 4.0 and pitch != "+0Hz":
                kl = "LOẠI — biến thể GIẢ (F0 gần như không đổi)"
            elif d_wer > 3.0:
                kl = f"LOẠI — sai từ tăng {d_wer:+.2f} điểm %"
            else:
                kl = "GIỮ"
            print(f"   {pitch:>6} | {b['f0']:5.1f} | {d_f0:+5.1f} | "
                  f"{b['wer']:6.2f}% | {d_wer:+7.2f} | {kl}")
    print(f"\nFile để NGHE bằng tai: {SAN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
