# -*- coding: utf-8 -*-
"""FILE NGHE THỬ NHẠC NỀN TỰ CHỌN (02/11/2026) — 3 video THẬT, chép lời THẬT.

Mỗi video 2 bản CÙNG đoạn cắt, CÙNG tiếng động mới:
  A_KHONG_NHAC = như hiện tại (không nhạc nền)
  B_NHAC_TU_CHON = bật "Tự chọn theo nội dung" — tâm trạng + bài chọn bằng ĐÚNG
                  hàm app dùng (`nhac_tu_dong.tam_trang` / `chon_bai`) từ lời
                  chép Groq + tiêu đề; nhạc né đúng các câu nói.
Cả hai chuẩn về -14 LUFS (`thay_giong.chuan_do_to`), đo lại bằng `loudnorm`.
Nguồn chỉ ĐỌC. Ra `_NGHE_THU_ANH_HUNG/nhac_nen/`.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import music_library as ML  # noqa: E402
from app.core import nhac_tu_dong as NT  # noqa: E402
from app.core import thay_giong as TG  # noqa: E402
from app.core.transcribe import transcribe  # noqa: E402

RA = REPO / "_NGHE_THU_ANH_HUNG" / "nhac_nen"
RA.mkdir(parents=True, exist_ok=True)
GOC = Path(r"D:\video ssmatool\video mỹ\kênh 112")
NGUON = [
    ("biker_tai_nan", GOC / "Shocking Crash Leaves Biker With No Memory!.mp4",
     [(30.0, 33.0), (3.0, 10.0), (10.5, 18.0), (20.0, 29.0), (33.5, 39.0)]),
    ("vui_nhon", GOC / "That was enough fun… 😂.mp4",
     [(15.0, 18.0), (1.0, 7.0), (7.4, 14.0), (18.5, 23.0)]),
    ("canh_sat", GOC / "The Cops Jumped Him 😨🫠.mp4",
     [(18.0, 21.0), (1.0, 8.0), (8.3, 14.0), (14.6, 18.0), (21.0, 24.5)]),
    ("tu_te", GOC / "Stranger Stops to Help Female Deputy With Flat Tire "
                    "#biker #kindness.mp4", None),
]
FF = str(REPO / "bin" / "ffmpeg.exe")
NW = 0x08000000 if os.name == "nt" else 0


def lufs(p: str) -> tuple:
    r = subprocess.run([FF, "-nostdin", "-hide_banner", "-i", p, "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, creationflags=NW, timeout=300)
    t = r.stderr.decode("utf-8", "replace")
    j = json.loads(t[t.rindex("{"):t.rindex("}") + 1])
    return float(j["input_i"]), float(j["input_tp"])


def main():
    tam = Path(tempfile.mkdtemp(prefix="nghe_nhac_"))
    dong = []
    for ten, src, segs in NGUON:
        if not src.is_file():
            print("thiếu nguồn", src)
            continue
        dur = float(F.probe(str(src)).duration)
        if segs is None:
            segs = [(0.0, min(dur, 40.0))]
        wav = tam / f"{ten}.wav"
        subprocess.run([FF, "-nostdin", "-y", "-loglevel", "error", "-i",
                        str(src), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       check=True, creationflags=NW, timeout=300)
        tr = transcribe(str(wav))
        loi = " ".join(c["text"] for c in tr.get("segments") or []
                       if any(c["end"] > s and c["start"] < e for s, e in segs))
        mood, ly = NT.tam_trang(loi, src.stem)
        bai = NT.chon_bai(list(ML.catalog()), mood, f"{ten}|{segs[0][0]}")
        path = ML.resolve(ML.PREFIX + bai["id"])
        for nhan, nhac in (("A_KHONG_NHAC", False), ("B_NHAC_TU_CHON", True)):
            tho = str(tam / f"{ten}_{nhan}.mp4")
            lg: dict = {}
            F.export_canvas_clip(
                str(src), tho, segs, (0.5, 0.5, 1.0), bg="blur", out_w=720,
                out_h=1280, encoder="libx264", fx_whoosh=True, hieu_ung="nhe",
                chuyen_canh="nhe", noi_dung={"transcript": tr},
                bgm_path=path if nhac else None,
                bgm_tu_dong=({"lufs": bai["lufs"], "transcript": tr, "log": lg}
                             if nhac else None))
            w1, w2 = str(tam / "a.wav"), str(tam / "b.wav")
            subprocess.run([FF, "-nostdin", "-y", "-loglevel", "error", "-i",
                            tho, "-vn", "-ac", "2", "-ar", "48000", w1],
                           check=True, creationflags=NW, timeout=300)
            TG.chuan_do_to(w1, w2)
            mp4 = str(RA / f"{ten}_{nhan}.mp4")
            subprocess.run([FF, "-nostdin", "-y", "-loglevel", "error", "-i",
                            tho, "-i", w2, "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                            mp4], check=True, creationflags=NW, timeout=300)
            i, tp = lufs(mp4)
            s = (f"{ten} {nhan}: I {i:.2f} LUFS · TP {tp:.2f} dBTP"
                 + (f"\n    tâm trạng: {mood} ({ly})\n    bài: {bai['title']}"
                    f" — {bai['author']} (CC0)\n    {lg}" if nhac else ""))
            print(s, flush=True)
            dong.append(s)
    (RA / "NGHE_THU.txt").write_text("\n".join(dong) + "\n", "utf-8")


if __name__ == "__main__":
    main()
