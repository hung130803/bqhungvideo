"""SMOKE: đường `vnb:` chạy được không + giá NẠP MODEL so với giá ĐỌC.

Chạy trước lượt e2e dài để không đốt 30 phút vào một đường đang hỏng. Cũng
trả lời luôn nghi phạm số 2: **nạp model mỗi lượt gọi tốn bao nhiêu**.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_cham_tg import HOP, lam_mau  # noqa: E402

CAU = [
    "A sudden storm changed everything for the small fishing town.",
    "Nobody expected the old man to walk back through that door.",
    "By the end of the week, the whole country knew his name.",
]


def main() -> int:
    HOP.mkdir(parents=True, exist_ok=True)
    mau = lam_mau(HOP / "mau_may.wav")
    from app.core import giong_vieneu as VN
    voice = VN.ma_nhan_ban(str(mau))
    ra = HOP / "smoke"
    if ra.exists():
        shutil.rmtree(ra, ignore_errors=True)
    ra.mkdir(parents=True, exist_ok=True)

    spawn = []
    goc = VN._chay_vieneu

    def _chay(items, py, v, ref, han, on_msg):
        t0 = time.time()
        k = goc(items, py, v, ref, han, on_msg)
        spawn.append({"so_cau": len(items), "wall": round(time.time() - t0, 2),
                      "nap": k.get("nap"), "gen": k.get("gen"),
                      "ok": bool(k.get("ok")), "loi": k.get("loi", "")[:200]})
        return k

    VN._chay_vieneu = _chay
    paths = [str(ra / f"c{i}.wav") for i in range(len(CAU))]
    t0 = time.time()
    ok, words = VN.doc_loat(CAU, paths, voice, lang="en", han_giay=1200)
    wall = time.time() - t0
    VN._chay_vieneu = goc

    d = {"voice": voice, "wall_s": round(wall, 2),
         "ok": ok, "so_mot": sum(1 for x in ok if x),
         "co_moc": [len(w) for w in words], "spawn": spawn}
    if spawn and spawn[0].get("gen") is not None:
        g = float(spawn[0]["gen"] or 0)
        n = float(spawn[0]["nap"] or 0)
        d["giay_moi_cau_khong_ke_nap"] = round(g / max(1, len(CAU)), 2)
        d["nap_model_s"] = n
        d["ty_le_nap_tren_ca_luot"] = round(n / max(1e-9, n + g), 3)
    print(json.dumps(d, ensure_ascii=False, indent=1))
    (REPO / "_kq_cham_smoke.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(ra, ignore_errors=True)
    return 0 if d["so_mot"] == len(CAU) else 1


if __name__ == "__main__":
    raise SystemExit(main())
