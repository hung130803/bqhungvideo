# -*- coding: utf-8 -*-
"""ĐỐI CHỨNG NGÔN NGỮ: cùng máy · cùng engine · v2.44.0 — nhưng TIẾNG VIỆT.

Anh Hùng đang chạy MỘT LƯỢT NỮA ngay lúc này (`_job_12084_59739`, bắt đầu
27/08 11:50:59, runner CÓ `add_voice` = **đúng đường v2.44.0**), và lượt này
đọc **TIẾNG VIỆT** với mẫu KHÁC (`test.wav`).

Ghép với lượt 26/08 (đường CŨ, TIẾNG ANH, mẫu `adam_clone.wav`) thì có một
phép so mà không lượt đo dựng lại nào bằng được — **dữ liệu thật, máy thật**:

    26/08  đường CŨ   · TIẾNG ANH  -> đã đo: 1,07 ngắt/câu (trần en 0,53)
    27/08  v2.44.0    · TIẾNG VIỆT -> lượt này

Nó KHÔNG phải phép so ghép cặp (khác tiếng, khác mẫu, khác đường) nên **không
dùng để chấm v2.44.0** — chỗ đó đã có `_do_v244_danhvan.py`. Nó trả lời một
câu KHÁC và cũng quan trọng không kém: *triệu chứng "ngắt vụn" có phải là
chuyện của TIẾNG ANH không?* Mỗi arm so với TRẦN edge bản ngữ CỦA CHÍNH TIẾNG
ĐÓ, nên hai tỉ số đọc được cạnh nhau.

**CHỈ ĐỌC** máy anh Hùng. Bỏ file cuối cùng (có thể đang ghi dở).
"""
from __future__ import annotations

import json
import statistics as st
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / "_kq_danhvan" / "hung_viet"
HOP.mkdir(parents=True, exist_ok=True)
RA = REPO / "_kq_hung_viet.json"

import config  # noqa: E402
from app.core import piper_tts  # noqa: E402

FF = str(getattr(config.settings, "FFMPEG_PATH", "ffmpeg"))
NO_WIN = 0x08000000
JOB = Path(r"C:\Users\Admin\AppData\Local\BQHungVideo\_giong_vieneu"
           r"\_job_12084_59739\job.json")
GIONG_VI = "vi-VN-NamMinhNeural"
SO_TRAN = 40


def dodac(w: Path) -> dict | None:
    khoang, tong = piper_tts.khoang_co_tieng(w)
    if tong <= 0:
        return None
    if not khoang:
        return {"so": 0, "im": 0.0, "dai_nhat": 0.0, "ty": 0.0, "dai": tong}
    ngat = [khoang[i + 1][0] - khoang[i][1] for i in range(len(khoang) - 1)]
    co = sum(b - a for a, b in khoang)
    return {"so": len(ngat), "im": round(sum(ngat), 3),
            "dai_nhat": round(max(ngat), 3) if ngat else 0.0,
            "ty": round(co / tong, 4), "dai": round(tong, 3)}


def _gom(ten: str, ds: list[dict], kt: list[int]) -> dict:
    so = [d["so"] for d in ds]
    t100 = [100.0 * s / max(1, n) for s, n in zip(so, kt)]
    r = {"n": len(ds), "ngat_cau": round(st.mean(so), 2),
         "ngat_tv": st.median(so),
         "im_giua_s": round(st.mean(d["im"] for d in ds), 3)
         if False else round(st.mean([d["im"] for d in ds]), 3),
         "ngat_100kt": round(st.mean(t100), 2),
         "ty_co_tieng": round(st.mean([d["ty"] for d in ds]), 4),
         "giay_cau": round(st.mean([d["dai"] for d in ds]), 2),
         "cau_0_ngat": round(100.0 * sum(1 for s in so if s == 0) / len(so), 1),
         "cau_2_ngat_tro_len": round(
             100.0 * sum(1 for s in so if s >= 2) / len(so), 1)}
    print(f"{ten:<28}{r['n']:>5}{r['ngat_cau']:>10.2f}{r['ngat_tv']:>6.1f}"
          f"{r['im_giua_s']:>10.3f}{r['ngat_100kt']:>12.2f}"
          f"{r['cau_0_ngat']:>10.1f}%{r['cau_2_ngat_tro_len']:>10.1f}%"
          f"{r['giay_cau']:>10.2f}")
    return r


def main() -> int:
    d = json.loads(JOB.read_text("utf-8"))
    print(f"JOB v2.44.0 ĐANG CHẠY: {len(d['items'])} câu · "
          f"voice={d.get('voice')!r} · mẫu={Path(d['ref_audio']).name}")
    muc = [(it["text"], Path(it["raw"])) for it in d["items"]
           if Path(it["raw"]).exists()]
    if len(muc) > 1:
        muc = muc[:-1]              # bỏ file cuối: có thể đang ghi dở
    print(f"   WAV đã xong (bỏ file cuối): {len(muc)}")
    if len(muc) < 10:
        print("   chưa đủ file để đo — chạy lại sau.")
        return 1

    do, kt = [], []
    for t, w in muc:
        r = dodac(w)
        if r:
            r["text"] = t
            do.append(r)
            kt.append(len(t))

    cau_tran = [x["text"] for x in do][:SO_TRAN]
    print(f"\nTRẦN: edge-tts {GIONG_VI} (BẢN NGỮ TIẾNG VIỆT) đọc "
          f"{len(cau_tran)} câu đầu của chính bộ này...")
    import asyncio
    import edge_tts

    async def _go():
        for i, t in enumerate(cau_tran):
            mp3 = HOP / f"t{i:03d}.mp3"
            if not mp3.exists():
                await edge_tts.Communicate(t, GIONG_VI).save(str(mp3))
    asyncio.run(_go())
    tran, kt_t = [], []
    for i, t in enumerate(cau_tran):
        w = HOP / f"t{i:03d}.wav"
        subprocess.run([FF, "-y", "-v", "error", "-i",
                        str(HOP / f"t{i:03d}.mp3"), "-ar", "24000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(w)],
                       capture_output=True, creationflags=NO_WIN)
        r = dodac(w)
        if r:
            tran.append(r)
            kt_t.append(len(t))

    print("\n" + "=" * 100)
    print("BẢNG — NGẮT GIỮA CÂU, TIẾNG VIỆT, đường v2.44.0 (dữ liệu THẬT "
          "đang chạy)")
    print("=" * 100)
    print(f"{'arm':<28}{'n':>5}{'ngắt/câu':>10}{'tvị':>6}{'im giữa':>10}"
          f"{'ngắt/100kt':>12}{'0 ngắt':>11}{'≥2 ngắt':>11}{'giây/câu':>10}")
    b_vn = _gom("vnb: v2.44.0 · TIẾNG VIỆT", do, kt)
    b_vn40 = _gom("  ↳ 40 câu đầu", do[:len(tran)], kt[:len(tran)])
    b_tr = _gom(f"TRẦN edge {GIONG_VI[:14]}", tran, kt_t)

    ty = b_vn40["ngat_100kt"] / max(0.01, b_tr["ngat_100kt"])
    print(f"\n  TỈ SỐ so TRẦN BẢN NGỮ (ngắt/100 ký tự): "
          f"**{ty:.2f} lần**")
    print("  (đối chiếu — lượt TIẾNG ANH 26/08 đo được: "
          "2,65 / 1,08 = **2,45 lần**)")

    RA.write_text(json.dumps({
        "job": JOB.name, "n_file": len(do), "giong_tran": GIONG_VI,
        "viet": b_vn, "viet_40": b_vn40, "tran": b_tr,
        "ty_so_tran": round(ty, 3),
    }, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nĐÃ GHI {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
