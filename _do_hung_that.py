# -*- coding: utf-8 -*-
"""ĐO THẲNG 184 FILE TIẾNG THẬT MÁY ANH HÙNG VỪA ĐỌC RA.

`%LOCALAPPDATA%\\BQHungVideo\\_giong_vieneu\\_tam_*/raw/*.wav` là **đúng thứ
anh Hùng nghe rồi kêu "như trẻ con mới đánh vần"** — không phải câu tôi bịa,
không phải lượt tôi chạy lại. Ghép với `_job_*/job.json` (có `text` của từng
file) thì đo được cả hai vế: chữ vào và tiếng ra.

**CHỈ ĐỌC.** Không sửa, không xoá, không copy đi đâu.

THƯỚC (dùng lại `piper_tts.khoang_co_tieng` — đọc thẳng mẫu PCM16, KHÔNG gọi
ffmpeg nên không đụng gì tới máy đang chạy):
  * NGẮT GIỮA CÂU: khoảng lặng nằm GIỮA các khoảng có tiếng (bỏ lề đầu/cuối)
  * tỉ lệ thời gian CÓ TIẾNG / tổng
  * **giây/ký tự** — chỗ tố giác BÙNG NỔ: câu ngắn mà ra file dài là model
    lảm nhảm/lặp, đúng hình dạng "đánh vần".

**TRẦN ĐỐI CHỨNG**: edge-tts `en-US` bản ngữ đọc CÙNG bộ câu. Không có trần
thì "0,9 ngắt mỗi câu" là con số vô nghĩa.
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

HOP = REPO / "_kq_danhvan" / "hung_that"
HOP.mkdir(parents=True, exist_ok=True)
RA = REPO / "_kq_hung_that.json"

import config  # noqa: E402
from app.core import piper_tts  # noqa: E402

FF = str(getattr(config.settings, "FFMPEG_PATH", "ffmpeg"))
NO_WIN = 0x08000000
GOC = Path(r"C:\Users\Admin\AppData\Local\BQHungVideo\_giong_vieneu")

#: Trần trên số câu lấy làm TRẦN edge (mỗi câu là một lượt mạng).
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
    im = [d["im"] for d in ds]
    ty = [d["ty"] for d in ds]
    dai = [d["dai"] for d in ds]
    gky = [d["dai"] / max(1, n) for d, n in zip(ds, kt)]
    t100 = [100.0 * s / max(1, n) for s, n in zip(so, kt)]
    r = {"n": len(ds), "ngat_cau": round(st.mean(so), 2),
         "ngat_tv": st.median(so),
         "im_giua_s": round(st.mean(im), 3),
         "im_tong_s": round(sum(im), 2),
         "dai_nhat": round(max(d["dai_nhat"] for d in ds), 3),
         "ngat_100kt": round(st.mean(t100), 2),
         "ty_co_tieng": round(st.mean(ty), 4),
         "giay_cau": round(st.mean(dai), 2),
         "giay_ky_tu": round(st.mean(gky), 4),
         "giay_ky_tu_tv": round(st.median(gky), 4),
         "cau_tren_3_ngat": sum(1 for s in so if s >= 3)}
    print(f"{ten:<26}{r['n']:>5}{r['ngat_cau']:>9.2f}{r['ngat_tv']:>7.1f}"
          f"{r['im_giua_s']:>10.3f}{r['dai_nhat']:>9.2f}"
          f"{r['ngat_100kt']:>11.2f}{r['ty_co_tieng']*100:>10.1f}%"
          f"{r['giay_ky_tu']:>10.4f}{r['cau_tren_3_ngat']:>9}")
    return r


def main() -> int:
    # ── nạp job THẬT: chữ + đường dẫn WAV ────────────────────────────────
    muc = []
    for jd in sorted(GOC.glob("_job_*")):
        j = jd / "job.json"
        if not j.exists():
            continue
        d = json.loads(j.read_text("utf-8"))
        for it in d.get("items") or []:
            w = Path(it["raw"])
            if w.exists():
                muc.append({"text": it["text"], "wav": w, "job": jd.name})
    print(f"FILE TIẾNG THẬT còn trên đĩa: {len(muc)} "
          f"(máy anh Hùng, CHỈ ĐỌC)")
    if not muc:
        print("Không còn file nào — không đo được.")
        return 1
    for jn in sorted({m["job"] for m in muc}):
        print(f"   {jn}: {sum(1 for m in muc if m['job'] == jn)} file")

    do, kt, bo = [], [], 0
    for m in muc:
        r = dodac(m["wav"])
        if r is None:
            bo += 1
            continue
        r["text"] = m["text"]
        do.append(r)
        kt.append(len(m["text"]))
    print(f"   đọc được {len(do)} file (bỏ {bo} file không đọc nổi header)\n")

    # ── TRẦN edge-tts en-US, CÙNG bộ câu ─────────────────────────────────
    cau_tran = [d["text"] for d in do][:SO_TRAN]
    print(f"TRẦN: edge-tts en-US-Andrew đọc {len(cau_tran)} câu ĐẦU "
          f"của chính bộ này...")
    import asyncio
    import edge_tts

    async def _go():
        for i, t in enumerate(cau_tran):
            mp3 = HOP / f"t{i:03d}.mp3"
            if not mp3.exists():
                await edge_tts.Communicate(t, "en-US-AndrewNeural").save(
                    str(mp3))
    asyncio.run(_go())
    tran, kt_t = [], []
    for i, t in enumerate(cau_tran):
        w = HOP / f"t{i:03d}.wav"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(HOP / f"t{i:03d}.mp3"),
                        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                        str(w)], capture_output=True, creationflags=NO_WIN)
        r = dodac(w)
        if r:
            r["text"] = t
            tran.append(r)
            kt_t.append(len(t))
    print(f"   trần đo được {len(tran)} câu\n")

    # ── BẢNG ─────────────────────────────────────────────────────────────
    print("=" * 100)
    print("BẢNG — NGẮT GIỮA CÂU trên TIẾNG THẬT anh Hùng vừa nghe")
    print("=" * 100)
    print(f"{'arm':<26}{'n':>5}{'ngắt/câu':>9}{'tvị':>7}{'im giữa':>10}"
          f"{'ngắt dài':>9}{'ngắt/100kt':>11}{'%có tiếng':>11}{'s/ký tự':>10}"
          f"{'≥3 ngắt':>9}")
    b_hung = _gom("vnb: ANH HÙNG (thật)", do, kt)
    # cùng tập câu với trần, để so TÁO với TÁO
    b_hung40 = _gom("  ↳ 40 câu đầu", do[:len(tran)], kt[:len(tran)])
    b_tran = _gom("TRẦN edge en-US", tran, kt_t)

    # ── BÙNG NỔ: câu ngắn ra file dài ────────────────────────────────────
    gky = [d["dai"] / max(1, len(d["text"])) for d in do]
    tv = st.median(gky)
    bung = [(d, g) for d, g in zip(do, gky) if g > 2.5 * tv]
    print(f"\nBÙNG NỔ (giây/ký tự > 2,5x trung vị {tv:.4f}): "
          f"{len(bung)}/{len(do)} câu ({100.0*len(bung)/len(do):.1f}%)")
    for d, g in sorted(bung, key=lambda x: -x[1])[:12]:
        print(f"   {g/tv:5.1f}x · {d['dai']:6.2f}s · {d['so']:2d} ngắt · "
              f"[{len(d['text']):3d} kt] {d['text'][:62]}")
    gky_t = [d["dai"] / max(1, len(d["text"])) for d in tran]
    tvt = st.median(gky_t)
    bung_t = sum(1 for g in gky_t if g > 2.5 * tvt)
    print(f"   TRẦN cùng phép: {bung_t}/{len(tran)} câu "
          f"({100.0*bung_t/max(1,len(tran)):.1f}%)  <- ĐỐI CHỨNG")

    # ── phân bố số ngắt ──────────────────────────────────────────────────
    print("\nPHÂN BỐ SỐ NGẮT GIỮA CÂU:")
    print(f"{'số ngắt':>9}{'anh Hùng':>12}{'TRẦN edge':>12}")
    mx = max([d["so"] for d in do] + [d["so"] for d in tran])
    for k in range(0, min(mx, 8) + 1):
        a = sum(1 for d in do if d["so"] == k)
        b = sum(1 for d in tran if d["so"] == k)
        print(f"{k:>9}{a:>7} ({100.0*a/len(do):4.1f}%)"
              f"{b:>7} ({100.0*b/max(1,len(tran)):4.1f}%)")
    a = sum(1 for d in do if d["so"] > 8)
    b = sum(1 for d in tran if d["so"] > 8)
    print(f"{'>8':>9}{a:>7} ({100.0*a/len(do):4.1f}%)"
          f"{b:>7} ({100.0*b/max(1,len(tran)):4.1f}%)")

    RA.write_text(json.dumps({
        "n_file": len(do), "anh_hung": b_hung, "anh_hung_40": b_hung40,
        "tran_edge": b_tran, "so_tran": len(tran),
        "bung_no": {"nguong_x": 2.5, "tv_giay_ky_tu": round(tv, 5),
                    "so_ca": len(bung), "ty_le": round(len(bung)/len(do), 4),
                    "tran_so_ca": bung_t,
                    "tran_ty_le": round(bung_t/max(1, len(tran)), 4),
                    "vi_du": [{"x": round(g/tv, 2), "dai": d["dai"],
                               "ngat": d["so"], "kt": len(d["text"]),
                               "text": d["text"]}
                              for d, g in sorted(bung, key=lambda x: -x[1])[:20]]},
    }, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nĐÃ GHI {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
