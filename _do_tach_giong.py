# -*- coding: utf-8 -*-
"""ĐO BƯỚC 1 — TÁCH GIỌNG khỏi NHẠC. So Demucs với cách nhẹ (ffmpeg).

Chạy trên VIDEO THẬT (bản sao 60 giây trong `_tg/asset`), THÀNH PHẦN THẬT
(ffmpeg thật, Groq thật). Đo cho MỖI cách:
  · giây xử lý / 1 phút video   (ty_le = giây / độ dài audio)
  · RAM ĐỈNH (RSS) đo bằng psutil, lấy mẫu 100 ms trong lúc chạy
  · giam_giong_db  — giọng giảm bao nhiêu dB ở đoạn ĐANG NÓI
  · giu_nhac_db    — nhạc mất bao nhiêu dB ở đoạn KHÔNG nói
  · TỪ CÒN SÓT     — chép lời chính track "nhạc" bằng Groq: còn đọc ra bao nhiêu
                     từ so với bản gốc. Đây là thước đo THẬT: người xem nghe
                     thấy giọng cũ hay không.

CÁCH DÙNG:  .venv\\Scripts\\python.exe _do_tach_giong.py [zh60|en60] [cach...]
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import psutil  # noqa: E402

from app.core import thay_giong as tg  # noqa: E402


class DoRam:
    """Lấy mẫu RSS của tiến trình này 100 ms/lần -> RAM ĐỈNH thật."""

    def __init__(self) -> None:
        self.dinh = 0
        self._stop = threading.Event()
        self._p = psutil.Process()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.dinh = max(self.dinh, self._p.memory_info().rss)
            except psutil.Error:
                return
            self._stop.wait(0.1)

    def __enter__(self):
        self._nen = self._p.memory_info().rss
        self.dinh = self._nen
        self._t.start()
        return self

    def __exit__(self, *a) -> None:
        self._stop.set()
        self._t.join(timeout=2)

    @property
    def dinh_mb(self) -> float:
        return round(self.dinh / 2 ** 20, 1)

    @property
    def them_mb(self) -> float:
        return round((self.dinh - self._nen) / 2 ** 20, 1)


def chep_loi(wav: str, nhan: str) -> dict:
    """Chép lời bằng Groq THẬT, có cache ra `_tg/<nhan>.json` để đo lại nhanh."""
    cache = ROOT / "_tg" / f"chep_{nhan}.json"
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        print(f"  (dùng lại bản chép lời đã lưu: {cache.name})")
        return d
    from app.core import transcribe
    t0 = time.time()
    d = transcribe.transcribe(wav)
    d["_giay_chep"] = round(time.time() - t0, 2)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _tu(text: str) -> list[str]:
    import re
    t = re.sub(r"[^\w\s]", " ", (text or ""), flags=re.UNICODE)
    return [x for x in t.split() if x.strip()]


def main() -> int:
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh60"
    cachs = sys.argv[2:] or ["demucs", "nhe"]
    mp4 = ROOT / "_tg" / "asset" / f"{ten}.mp4"
    if not mp4.exists():
        print(f"THIEU video mau: {mp4}")
        return 2

    work = ROOT / "_tg" / f"do_{ten}"
    work.mkdir(parents=True, exist_ok=True)
    goc = work / "goc.wav"
    if not goc.exists():
        d = tg.tach_wav(mp4, goc)
        print(f"Audio goc: {d:.2f} giay, 44.1kHz stereo")

    tong = tg.probe_duration(goc)
    print(f"\n=== CHEP LOI GOC (Groq that) — de biet doan NAO dang noi ===")
    tr = chep_loi(str(goc), ten)
    words = tr.get("words") or []
    segs = tr.get("segments") or []
    print(f"  ngon ngu={tr.get('language')} so tu={len(words)} so cau={len(segs)}")
    if not words:
        print("  !! KHONG co moc tung tu -> khong do duoc chat luong tach")
        return 3
    noi, im = tg.khoang_noi_im(words, tong)
    print(f"  doan DANG NOI: {len(noi)}  |  doan KHONG noi: {len(im)}")
    if not im:
        print("  !! Video khong co doan im -> khong do duoc 'giu duoc nhac'")

    tu_goc = _tu(tr.get("text") or "")
    ket: dict = {"video": ten, "do_dai": round(tong, 2),
                 "so_tu_goc": len(tu_goc), "ngon_ngu": tr.get("language"),
                 "cachs": {}}

    for cach in cachs:
        print(f"\n=== CACH: {cach} ===")
        out = work / cach
        out.mkdir(parents=True, exist_ok=True)
        try:
            with DoRam() as ram:
                r = tg.tach_giong(goc, out, cach=cach,
                                  on_progress=lambda p, m: None)
            r["ram_dinh_mb"] = ram.dinh_mb
            r["ram_them_mb"] = ram.them_mb
        except Exception as e:  # noqa: BLE001
            print(f"  KHONG LAM DUOC: {e}")
            ket["cachs"][cach] = {"loi": str(e)[:400]}
            continue

        print(f"  giay={r['giay']}  ty_le={r['ty_le']}x thoi-gian-thuc  "
              f"thiet_bi={r['thiet_bi']}  RAM dinh={r['ram_dinh_mb']} MB "
              f"(+{r['ram_them_mb']} MB)")
        if r.get("lui_vi"):
            print(f"  !! DA TU LUI sang cach nhe, ly do: {r['lui_vi']}")

        q = tg.do_chat_luong_tach(goc, r["nhac"], noi, im)
        r.update(q)
        print(f"  giam_giong={q['giam_giong_db']} dB (cang LON cang sach)")
        print(f"  giu_nhac  ={q['giu_nhac_db']} dB (cang GAN 0 cang tot)")
        print(f"  loi_the   ={q['loi_the_db']} dB")
        print(f"  nhac_rms  ={q['nhac_rms']} (0.0 = TRACK IM LANG = tach hong)")

        # THUOC DO THAT: chep lai chinh track NHAC -> con doc ra bao nhieu tu?
        try:
            mp3 = out / "nhac_de_chep.mp3"
            tg._ffmpeg(["-i", r["nhac"], "-ac", "1", "-ar", "16000",
                        "-b:a", "64k", str(mp3)], "nen track nhac de chep loi")
            tr2 = chep_loi(str(mp3), f"{ten}_{cach}_nhac")
            tu2 = _tu(tr2.get("text") or "")
            r["so_tu_con_sot"] = len(tu2)
            r["ty_le_tu_con_sot"] = (round(len(tu2) / len(tu_goc), 3)
                                     if tu_goc else None)
            r["mau_tu_con_sot"] = (tr2.get("text") or "")[:160]
            print(f"  TU CON SOT trong track nhac: {len(tu2)}/{len(tu_goc)} "
                  f"= {r['ty_le_tu_con_sot']}")
            print(f"  mau: {r['mau_tu_con_sot'][:120]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"  (khong chep lai duoc track nhac: {e})")

        ket["cachs"][cach] = r

    p = ROOT / f"_ket__do_tach_{ten}.json"
    p.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    print(f"\nDa ghi so do: {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
