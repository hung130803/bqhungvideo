# -*- coding: utf-8 -*-
"""ĐO BƯỚC 1 — tách giọng: Demucs vs cách nhẹ, trên VIDEO THẬT.

Chạy 1 cách trong TIẾN TRÌNH CON rồi bố mẹ lấy mẫu RSS (kể cả tiến trình con
của nó) -> RAM đỉnh đo được thật, không đoán.

    python _tg/do_buoc1.py --cach demucs --wav _tg/asset/zh60.wav
    python _tg/do_buoc1.py --tat-ca            # chạy cả 2 rồi in bảng

BẪY ĐÃ PHÒNG:
· ffmpeg trả mã 0 mà file rỗng -> `_kiem_wav` trong thay_giong.py.
· đo RAM bằng RSS của CHÍNH mình thì demucs chạy in-process nên đúng, còn
  cách nhẹ chạy ffmpeg CON -> phải cộng cả con, nếu không ra ~0 và kết luận
  sai "cách nhẹ không tốn RAM".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


# ------------------------------------------------------------------
# TIẾN TRÌNH CON: chạy đúng 1 cách rồi in JSON ra stdout
# ------------------------------------------------------------------
def chay_mot_cach(cach: str, wav: str, out_dir: str) -> dict:
    from app.core import thay_giong as tg

    t0 = time.time()
    ket = tg.tach_giong(wav, out_dir, cach=cach)
    ket["wall"] = round(time.time() - t0, 2)
    return ket


# ------------------------------------------------------------------
# BỐ MẸ: spawn + lấy mẫu RAM
# ------------------------------------------------------------------
def do_ram(cach: str, wav: str, out_dir: str) -> dict:
    import psutil

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["BQ_FFMPEG_SLOTS"] = "1"
    p = subprocess.Popen(
        [sys.executable, str(Path(__file__)), "--con", "--cach", cach,
         "--wav", wav, "--out", out_dir],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        cwd=str(REPO), text=True, encoding="utf-8", errors="replace")

    dinh = {"rss": 0}

    def lay_mau() -> None:
        try:
            pr = psutil.Process(p.pid)
        except psutil.Error:
            return
        while p.poll() is None:
            try:
                tong = pr.memory_info().rss
                for c in pr.children(recursive=True):
                    try:
                        tong += c.memory_info().rss
                    except psutil.Error:
                        pass
                dinh["rss"] = max(dinh["rss"], tong)
            except psutil.Error:
                return
            time.sleep(0.05)

    th = threading.Thread(target=lay_mau, daemon=True)
    th.start()
    out, err = p.communicate()
    th.join(timeout=2)

    ket: dict = {}
    for line in (out or "").splitlines():
        if line.startswith("__KET__"):
            ket = json.loads(line[len("__KET__"):])
    if not ket:
        return {"cach": cach, "loi": (err or out or "")[-800:]}
    ket["ram_dinh_mb"] = round(dinh["rss"] / 1024 / 1024, 1)
    return ket


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--con", action="store_true")
    ap.add_argument("--cach", default="demucs")
    ap.add_argument("--wav", default=str(REPO / "_tg/asset/zh60.wav"))
    ap.add_argument("--out", default="")
    ap.add_argument("--tat-ca", action="store_true")
    a = ap.parse_args()

    if a.con:
        out = a.out or str(REPO / "_tg/do_zh60" / a.cach)
        Path(out).mkdir(parents=True, exist_ok=True)
        try:
            ket = chay_mot_cach(a.cach, a.wav, out)
        except Exception as e:  # noqa: BLE001
            ket = {"cach": a.cach, "loi": f"{type(e).__name__}: {e}"}
        print("__KET__" + json.dumps(ket, ensure_ascii=False))
        return 0

    ten = Path(a.wav).stem
    cachs = ["demucs", "nhe"] if a.tat_ca else [a.cach]
    bang = []
    for c in cachs:
        out = str(REPO / f"_tg/do_{ten}" / c)
        Path(out).mkdir(parents=True, exist_ok=True)
        print(f"--- đang chạy {c} trên {a.wav} ...", flush=True)
        k = do_ram(c, a.wav, out)
        bang.append(k)
        print(json.dumps(k, ensure_ascii=False, indent=1), flush=True)

    kq = REPO / f"_tg/ket_buoc1_{ten}.json"
    kq.write_text(json.dumps(bang, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nĐã ghi {kq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
