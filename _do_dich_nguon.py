# -*- coding: utf-8 -*-
"""BƯỚC 1 — LẤY CHỮ THẬT: rút tiếng từ video THẬT của anh Hùng rồi CHÉP LỜI
bằng Groq (đúng đường app đi), cất vào cache để mọi arm sau dùng CHUNG BỘ CÂU.

CHỈ ĐỌC video gốc (`Downloads\longtieng`) — mọi thứ ghi ra đều nằm trong
`_kq_dich/`. Không đụng `studio.db`.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
HOP = REPO / "_kq_dich"
HOP.mkdir(exist_ok=True)

NGUON = Path(os.environ["USERPROFILE"]) / "Downloads" / "longtieng"
VIDEO = {
    "v396": "八位好莱坞导演联手拍的电影有多厉害#电影解说.mp4",
    "v148": "#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐.mp4",
}


def rut_tieng(mp4: Path, wav: Path) -> None:
    if wav.exists() and wav.stat().st_size > 1000:
        return
    from config import settings
    cmd = [settings.FFMPEG_PATH, "-v", "error", "-y", "-i", str(mp4),
           "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not wav.exists():
        raise RuntimeError(f"ffmpeg hỏng: {r.stderr[:400]}")


def main() -> None:
    from app.core import thay_giong as TG
    for ma, ten in VIDEO.items():
        mp4 = NGUON / ten
        if not mp4.exists():
            print(f"[{ma}] KHÔNG CÓ FILE: {mp4}"); continue
        wav = HOP / f"{ma}.wav"
        kq = HOP / f"chep_{ma}.json"
        rut_tieng(mp4, wav)
        if kq.exists():
            d = json.loads(kq.read_text(encoding="utf-8"))
            print(f"[{ma}] dùng CACHE: {len(d.get('segments') or [])} segment")
        else:
            t0 = time.time()
            d = TG.chep_loi(wav)
            d["_video"] = ten
            kq.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            print(f"[{ma}] chép lời {time.time()-t0:.1f}s")
        cau = TG.cau_tu_transcript(d)
        (HOP / f"cau_{ma}.json").write_text(
            json.dumps({"video": ten, "language": d.get("language"),
                        "duration": d.get("duration"), "cau": cau},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        ky = [len(c["text"]) for c in cau]
        khung = [c["end"] - c["start"] for c in cau]
        print(f"[{ma}] nhãn tiếng = {d.get('language')!r} · {len(cau)} câu · "
              f"ký tự/câu TB {sum(ky)/max(1,len(ky)):.1f} "
              f"(min {min(ky)} max {max(ky)}) · "
              f"khung TB {sum(khung)/max(1,len(khung)):.2f}s "
              f"(min {min(khung):.2f} max {max(khung):.2f})")
        print(f"[{ma}] 5 câu đầu: " +
              " | ".join(c["text"][:30] for c in cau[:5]))


if __name__ == "__main__":
    main()
