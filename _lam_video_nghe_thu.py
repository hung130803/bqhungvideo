# -*- coding: utf-8 -*-
r"""DỰNG 2 VIDEO ĐỂ ANH HÙNG **TỰ XEM BẰNG MẮT** — cùng tiếng, khác cách lấy mốc.

Mọi con số trong báo cáo đều là SỐ ĐO; tôi không có tai và không có mắt. Thứ
duy nhất trả lời được câu *"chữ có chạy theo lời không"* là nhìn tận mắt.

Hai file ra CHỈ khác nhau ở **cách lấy mốc từng chữ**:
  · `1_CACH_CU_groq.mp4`      mốc do máy nghe (Groq) chép ngược rồi đoán
  · `2_CACH_MOI_giong_hang.mp4` mốc do gióng hàng cưỡng bức
Tiếng, câu chữ, phông, cỡ chữ — **giống hệt nhau**. Chữ nào KHÔNG có mốc thì
KHÔNG hiện lên: đó chính là chỗ cần nhìn.

Dùng bộ WAV `_do_gn_san` (mẻ OmniVoice đọc kém — chính mẻ làm đường Groq ra
PHỦ 37,6% tiếng Việt). Cố ý chọn mẻ xấu: mẻ đẹp thì hai bên gần như nhau, xem
không ra gì.

    .venv\Scripts\python -u _lam_video_nghe_thu.py
"""
from __future__ import annotations

import importlib.util as _u
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

_s = _u.spec_from_file_location("_m_gn_moc", REPO / "_do_gn_moc.py")
M = _u.module_from_spec(_s)
_s.loader.exec_module(M)

NN = os.environ.get("BQ_NN", "vi")
SAN = REPO / os.environ.get("BQ_SAN", "_do_gn_san") / f"l0_{NN}_OV"
RA = REPO / "_NGHE_THU_ANH_HUNG" / "giong_hang"
SO_CAU = int(os.environ.get("BQ_SO_CAU", "6"))
W, H = 720, 1280


def _ass(duong: Path, cum: list, tieu_de: str) -> None:
    """.ass tối giản: mỗi CHỮ một dòng, hiện đúng lúc nó được đọc."""
    def t(x: float) -> str:
        x = max(0.0, x)
        return f"{int(x // 3600)}:{int(x // 60) % 60:02d}:{x % 60:05.2f}"

    d = [
        "[Script Info]", "ScriptType: v4.00+",
        f"PlayResX: {W}", f"PlayResY: {H}", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        f"Style: C,Arial,{int(H * 0.045)},&H00FFFFFF,&H00000000,&H00000000,"
        "-1,0,1,3,0,2,40,40,180,1",
        f"Style: T,Arial,{int(H * 0.028)},&H0000E5FF,&H00000000,&H00000000,"
        "-1,0,1,3,0,8,40,40,60,1", "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,9:59:59.00,T,,0,0,0,,{tieu_de}",
    ]
    for a, b, w in cum:
        w = str(w).replace("{", "(").replace("}", ")").replace("\n", " ")
        d.append(f"Dialogue: 0,{t(a)},{t(max(b, a + 0.12))},C,,0,0,0,,{w}")
    duong.write_text("\n".join(d) + "\n", encoding="utf-8")


def main() -> int:
    from config import settings
    from app.core import dubbing, giong_hang as gh, giong_ngoai as gn
    if not SAN.is_dir():
        print(f"Chưa có {SAN} — chạy `_do_gn_moc.py` trước.")
        return 2
    if not gh.co_giong_hang():
        print("Máy chưa có bộ gióng hàng.")
        return 2
    RA.mkdir(parents=True, exist_ok=True)
    FF = settings.FFMPEG_PATH

    texts = M.nap_cau(NN)[:SO_CAU]
    wavs = [str(SAN / f"c{i:03d}.wav") for i in range(len(texts))]
    co = [i for i in range(len(texts)) if Path(wavs[i]).exists()]
    texts = [texts[i] for i in co]
    wavs = [wavs[i] for i in co]
    if not wavs:
        print("Không có WAV nào.")
        return 2
    print(f"{len(wavs)} câu tiếng {NN}")

    # 1. NỐI TIẾNG — nhớ mốc bắt đầu từng câu để dời mốc chữ theo
    ds = RA / "_noi.txt"
    ds.write_text("\n".join(f"file '{Path(w).as_posix()}'" for w in wavs),
                  encoding="utf-8")
    audio = RA / f"tieng_{NN}.wav"
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f",
                    "concat", "-safe", "0", "-i", str(ds), "-c", "copy",
                    str(audio)], check=True, timeout=300)
    moc_dau, t = [], 0.0
    for w in wavs:
        moc_dau.append(t)
        t += dubbing.probe_duration(w)
    tong = t
    print(f"tiếng nối: {tong:.2f}s -> {audio.name}")

    # 2. HAI BỘ MỐC trên CÙNG bộ WAV đó
    bo: dict = {}
    bo["groq"] = [gn._lay_moc_groq(texts[i], wavs[i]) for i in range(len(wavs))]
    bo["giong_hang"] = gh.giong_hang_loat(wavs, texts, NN)

    n_tu = sum(len(dubbing._tach_tu(x)) for x in texts)
    for ten, moc in bo.items():
        n = sum(len(m) for m in moc)
        print(f"  {ten:<11} {n}/{n_tu} chữ có mốc = {100.0 * n / n_tu:.1f}%")

    # 3. DỰNG VIDEO
    nhan = {"groq": ("1_CACH_CU_groq",
                     "CACH CU - moc do may nghe chep nguoc"),
            "giong_hang": ("2_CACH_MOI_giong_hang",
                           "CACH MOI - moc do giong hang")}
    for ten, moc in bo.items():
        cum = []
        for i, m in enumerate(moc):
            for a, b, w in m:
                cum.append((a + moc_dau[i], b + moc_dau[i], w))
        cum.sort(key=lambda x: x[0])
        ten_file, tieu_de = nhan[ten]
        n = sum(len(m) for m in moc)
        ass = RA / f"{ten_file}.ass"
        _ass(ass, cum, f"{tieu_de} ({n}/{n_tu} chu co moc)")
        out = RA / f"{ten_file}.mp4"
        subprocess.run(
            [FF, "-y", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", f"color=c=0x101418:s={W}x{H}:d={tong:.3f}",
             "-i", str(audio),
             "-vf", "subtitles=" + ass.name.replace("\\", "/"),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
             "-shortest", str(out)],
            check=True, timeout=900, cwd=str(RA))
        kb = out.stat().st_size / 1024
        dai = dubbing.probe_duration(out)
        # ffmpeg trả mã 0 mà file rỗng là chuyện đã xảy ra -> ĐO đầu ra
        assert kb > 20 and dai > 1.0, f"{out} ra hỏng ({kb:.0f} KB / {dai}s)"
        print(f"  {out.name}: {kb:.0f} KB · {dai:.2f}s")

    try:
        ds.unlink()
    except OSError:
        pass
    print(f"\nMỞ HAI FILE NÀY XEM: {RA}")
    print("  1_CACH_CU_groq.mp4        <- chữ hiện thưa, nhiều chữ KHÔNG hiện")
    print("  2_CACH_MOI_giong_hang.mp4 <- chữ hiện gần đủ, chạy theo lời")
    print("Tiếng của hai file GIỐNG HỆT nhau — chỉ khác cách lấy mốc.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
