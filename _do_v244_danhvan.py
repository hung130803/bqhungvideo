# -*- coding: utf-8 -*-
"""v2.44.0 CÓ LÀM ĐỔI TIẾNG KHÔNG + BẢNG NGẮT GIỮA CÂU (thước "đánh vần").

Anh Hùng báo *"đọc như trẻ con mới đánh vần"* NGAY SAU khi phát hành v2.44.0
(`infer(ref_audio=)` -> `add_voice()` + `infer(voice=)`). Báo cáo v2.44.0
KHẲNG ĐỊNH *"không đổi một tham số nào đưa vào model"* — câu đó suy từ ĐỌC MÃ,
chưa ai kiểm bằng TIẾNG. Đây là phép kiểm đó.

━━ THIẾT KẾ, VÀ VÌ SAO PHẢI THẾ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**VieNeu KHÔNG TIỀN ĐỊNH** (`temperature=0.8 · top_k=25 · top_p=0.95`). Cùng
bản mã, cùng mẫu, cùng câu đã đo được WER **3,1% vs 12,7%**. Nên so MỘT lượt
CŨ với MỘT lượt MỚI thì không phân biệt được "bản vá đổi tiếng" với "model tự
lấy mẫu khác". Bắt buộc phải có **SÀN NHIỄU = CŨ vs CŨ** — đúng khuôn đã cứu
phép đo Demucs GPU (*"hai hàng TRÙNG DẢI nhau -> lệch là NHIỄU"*).

Vậy 4 arm, **ĐAN XEN TỪNG CÂU** trong **CÙNG MỘT tiến trình** (cùng model đã
nạp, cùng mẫu, cùng bộ chữ), có **XOAY THỨ TỰ** chẵn/lẻ để không arm nào luôn
đi trước:
    CU1 · MOI1 · CU2 · MOI2
  đọc bảng:  |CU1−MOI1|  so với  |CU1−CU2|  (sàn nhiễu)
  hai cột trùng dải  ->  v2.44.0 KHÔNG đổi tiếng.

━━ THƯỚC ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **F0 trung vị · độ trải F0** — dùng LẠI `_do_nhan_nha.f0_nua_cung`, thước
   duy nhất của repo. KHÔNG viết bộ đo thứ hai (hai bảng số không so được).
2. **thời lượng** từng câu.
3. **NGẮT GIỮA CÂU** — đây là thước của triệu chứng MỚI. "Đánh vần" = đọc rời
   rạc, ngắt quãng **BÊN TRONG** câu. Nên đếm khoảng lặng NẰM GIỮA các khoảng
   có tiếng, **bỏ lề đầu/cuối** (`piper_tts.khoang_co_tieng` — cố ý dùng hàm
   này chứ không `thay_giong.do_le_im`: `do_le_im` chỉ nhìn im DÍNH MÉP, đúng
   thứ KHÔNG cần ở đây).
4. **TRẦN ĐỐI CHỨNG**: edge-tts `en-US` bản ngữ đọc **CÙNG bộ câu**, **CÙNG
   LƯỢT**. Không có trần thì "3 khoảng lặng mỗi câu" là con số vô nghĩa.

━━ RANH GIỚI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mẫu nhân bản là **GIỌNG MÁY** (edge-tts sinh ra), **KHÔNG dùng
`adam_clone.wav`** — không nhân bản giọng người thật nào ngoài anh Hùng.
Câu đọc là **bản dịch tiếng Anh THẬT** của anh Hùng (`_job_*/job.json`).
"""
from __future__ import annotations

import json
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: Câu bản dịch tiếng Anh THẬT của anh Hùng, chọn trải độ dài + có dấu câu
#: giữa câu (dấu phẩy là chỗ máy đọc hay chèn nghỉ — đúng chỗ cần soi).
SO_CAU = int(__import__("os").environ.get("BQ_SO_CAU") or 6)
#: 2 vòng mỗi arm. VieNeu không tiền định nên 1 vòng KHÔNG đọc được gì.
VONG = int(__import__("os").environ.get("BQ_VONG") or 2)
_HOP_TEN = __import__("os").environ.get("BQ_HOP") or "v244"

HOP = REPO / "_kq_danhvan" / _HOP_TEN
HOP.mkdir(parents=True, exist_ok=True)
RA = REPO / f"_kq_v244_{_HOP_TEN}.json"

import config  # noqa: E402
from app.core import giong_vieneu as vn  # noqa: E402
from app.core import piper_tts  # noqa: E402

FF = str(getattr(config.settings, "FFMPEG_PATH", "ffmpeg"))
NO_WIN = 0x08000000

# Chạy tiến trình con: đọc CÙNG bộ câu bằng 2 cách, ĐAN XEN, xoay thứ tự.
_MA = r'''
import json, os, sys, time
job = json.load(open(sys.argv[1], "r", encoding="utf-8"))
def bao(m):
    sys.stdout.write("BQP\t%s\n" % m); sys.stdout.flush()
try:
    import numpy as np, soundfile as sf
    from vieneu import Vieneu
    bao("nap model...")
    t0 = time.time(); tts = Vieneu(); t_nap = time.time() - t0
    sr = int(getattr(tts, "sample_rate", 48000))
    mau = job["mau"]
    # ARM MOI: enrol MOT LAN, y het v2.44.0 (`add_voice` + `infer(voice=)`).
    t0 = time.time(); tts.add_voice("_bq_clone", mau); t_enrol = time.time()-t0
    bao("enrol %.1fs" % t_enrol)
    ra = []
    for viec in job["viec"]:
        # `arm`: "cu" -> infer(ref_audio=) (duong TRUOC v2.44.0)
        #        "moi" -> infer(voice="_bq_clone") (duong v2.44.0)
        kw = {"apply_watermark": True}
        if viec["arm"] == "cu":
            kw["ref_audio"] = mau
        else:
            kw["voice"] = "_bq_clone"
        t0 = time.time()
        a = tts.infer(text=viec["text"], **kw)
        gy = time.time() - t0
        a = np.asarray(a, dtype="float32").reshape(-1)
        sf.write(viec["out"], a, sr)
        ra.append({"k": viec["k"], "giay_chay": round(gy, 3),
                   "giay": round(len(a) / float(sr), 4)})
        bao("%s %d/%d" % (viec["arm"], len(ra), len(job["viec"])))
    ket = {"ok": True, "nap": round(t_nap,2), "enrol": round(t_enrol,2),
           "sr": sr, "ra": ra}
except Exception as e:
    import traceback; traceback.print_exc()
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\t" + json.dumps(ket) + "\n"); sys.stdout.flush()
'''


def _ff(args: list[str]) -> int:
    return subprocess.run([FF, "-y", "-v", "error"] + args,
                          capture_output=True,
                          creationflags=NO_WIN).returncode


def _pcm16(src: str | Path, dst: str | Path, sr: int = 24000) -> bool:
    """Về PCM16 mono cùng nhịp lấy mẫu — MỘT thước cho MỌI arm."""
    ok = _ff(["-i", str(src), "-ar", str(sr), "-ac", "1",
              "-c:a", "pcm_s16le", str(dst)]) == 0
    return ok and Path(dst).exists()


def ngat_giua(wav: Path) -> dict:
    """Khoảng lặng NẰM GIỮA câu (bỏ lề đầu/cuối) + tỉ lệ có tiếng."""
    khoang, tong = piper_tts.khoang_co_tieng(wav)
    if not khoang or tong <= 0:
        return {"so": 0, "tong_im": 0.0, "dai_nhat": 0.0,
                "ty_le_co_tieng": 0.0, "dai": tong}
    ngat = [round(khoang[i + 1][0] - khoang[i][1], 4)
            for i in range(len(khoang) - 1)]
    co = sum(b - a for a, b in khoang)
    return {"so": len(ngat), "tong_im": round(sum(ngat), 3),
            "dai_nhat": round(max(ngat), 3) if ngat else 0.0,
            "ty_le_co_tieng": round(co / tong, 4), "dai": round(tong, 3),
            "ngat": ngat}


def f0(wav: Path) -> dict:
    import _do_nhan_nha as nn
    v = nn.f0_nua_cung(wav)
    if len(v) < 5:
        return {"n": len(v), "tv": None, "trai": None}
    return {"n": len(v), "tv": round(st.median(v), 3),
            "trai": round(st.pstdev(v), 3)}


def _sinh_mau() -> str:
    """Mẫu nhân bản = GIỌNG MÁY edge-tts (luật cấm giọng người thật)."""
    import asyncio
    import edge_tts
    mp3 = HOP / "mau.mp3"
    wav = HOP / "mau.wav"
    txt = ("This is a neutral reference recording used only as a machine "
           "voice sample. It contains ordinary spoken sentences, read at a "
           "steady and natural pace, for measurement purposes.")

    async def _go():
        c = edge_tts.Communicate(txt, "en-US-AndrewNeural")
        await c.save(str(mp3))
    asyncio.run(_go())
    assert _pcm16(mp3, wav), "khong chuyen duoc mau ve PCM16"
    return str(wav)


def _edge_tran(cau: list[str]) -> list[Path]:
    """TRẦN: edge-tts en-US bản ngữ đọc CÙNG bộ câu, CÙNG LƯỢT."""
    import asyncio
    import edge_tts
    ra = []

    async def _go():
        for i, t in enumerate(cau):
            mp3 = HOP / f"tran_{i:02d}.mp3"
            c = edge_tts.Communicate(t, "en-US-AndrewNeural")
            await c.save(str(mp3))
            w = HOP / f"tran_{i:02d}.wav"
            _pcm16(mp3, w)
            ra.append(w)
    asyncio.run(_go())
    return ra


def main() -> int:
    corpus = json.loads((REPO / "_kq_corpus_hung.json").read_text("utf-8"))
    # chọn câu có dấu phẩy/độ dài trung bình — chỗ máy đọc hay chèn nghỉ
    cau = [t for t in corpus if 40 <= len(t) <= 95][:SO_CAU]
    print(f"BỘ CÂU (bản dịch tiếng Anh THẬT của anh Hùng, {len(cau)} câu):")
    for t in cau:
        print(f"   [{len(t):3d}] {t}")

    print("\nSinh MẪU nhân bản bằng edge-tts (GIỌNG MÁY — "
          "KHÔNG dùng adam_clone.wav)...")
    mau = _sinh_mau()
    print(f"   mẫu = {mau}")

    # ── dựng danh sách việc: ĐAN XEN + XOAY THỨ TỰ ───────────────────────
    viec = []
    for v in range(VONG):
        for i, t in enumerate(cau):
            # câu CHẴN: cũ trước · câu LẺ: mới trước -> không arm nào luôn đi
            # đầu (arm đi sau gánh phần model đã "nóng").
            thu_tu = ("cu", "moi") if (i % 2 == 0) else ("moi", "cu")
            for arm in thu_tu:
                k = f"{arm}{v+1}_c{i:02d}"
                viec.append({"k": k, "arm": arm, "text": t,
                             "out": str(HOP / f"{k}.wav")})
    print(f"\n{len(viec)} lượt đọc "
          f"({VONG} vòng x {len(cau)} câu x 2 arm), đan xen từng câu.")

    job = HOP / "job.json"
    job.write_text(json.dumps({"mau": mau, "viec": viec}, ensure_ascii=False),
                   "utf-8")
    runner = HOP / "runner_v244.py"
    runner.write_text(_MA, "utf-8")
    py, extra, _pb = vn._python_vieneu()
    print(f"python VieNeu = {py}")

    t0 = time.time()
    p = subprocess.Popen([py] + list(extra) + [str(runner), str(job)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace",
                         creationflags=NO_WIN)
    ket = None
    for dong in p.stdout:
        dong = dong.rstrip("\n")
        if dong.startswith("BQJSON\t"):
            ket = json.loads(dong.split("\t", 1)[1])
        elif dong.startswith("BQP\t"):
            print("   ", dong.split("\t", 1)[1], flush=True)
        else:
            print("   |", dong[:160], flush=True)
    p.wait()
    wall = time.time() - t0
    if not ket or not ket.get("ok"):
        print("LƯỢT ĐỌC HỎNG:", ket)
        return 1
    print(f"\nxong {wall:.1f}s · nạp {ket['nap']}s · enrol {ket['enrol']}s")

    print("\nTRẦN edge-tts en-US đọc CÙNG bộ câu, CÙNG LƯỢT...")
    tran_w = _edge_tran(cau)

    # ── ĐO ───────────────────────────────────────────────────────────────
    giay = {r["k"]: r["giay"] for r in ket["ra"]}
    chay = {r["k"]: r["giay_chay"] for r in ket["ra"]}
    do: dict[str, dict] = {}
    for v in viec:
        w = Path(v["out"])
        if not w.exists():
            continue
        do[v["k"]] = {"f0": f0(w), "ngat": ngat_giua(w),
                      "giay": giay.get(v["k"], 0.0),
                      "chay": chay.get(v["k"], 0.0)}
    tran = [{"f0": f0(w), "ngat": ngat_giua(w)} for w in tran_w]

    def _lay(arm: str, v: int, i: int, *ks):
        d = do.get(f"{arm}{v}_c{i:02d}")
        for k in ks:
            if d is None:
                return None
            d = d.get(k)
        return d

    # ── BẢNG 1: v2.44.0 CÓ ĐỔI TIẾNG KHÔNG (ghép cặp + SÀN NHIỄU) ────────
    print("\n" + "=" * 74)
    print("BẢNG 1 — v2.44.0 CÓ LÀM ĐỔI TIẾNG KHÔNG")
    print("  |CU1-MOI1| = thứ đang hỏi   ·   |CU1-CU2| = SÀN NHIỄU (cùng arm)")
    print("=" * 74)
    print(f"{'câu':<4}{'F0tv CU1':>9}{'F0tv MOI1':>10}{'|Δ|hỏi':>8}"
          f"{'|Δ|SÀN':>8} | {'dài CU1':>8}{'dài MOI1':>9}{'|Δ|hỏi':>8}"
          f"{'|Δ|SÀN':>8}")
    hoi_f0, san_f0, hoi_d, san_d, hoi_tr, san_tr = [], [], [], [], [], []
    for i in range(len(cau)):
        a = _lay("cu", 1, i, "f0", "tv")
        b = _lay("moi", 1, i, "f0", "tv")
        c = _lay("cu", 2, i, "f0", "tv")
        da = _lay("cu", 1, i, "giay")
        db = _lay("moi", 1, i, "giay")
        dc = _lay("cu", 2, i, "giay")
        ta = _lay("cu", 1, i, "f0", "trai")
        tb = _lay("moi", 1, i, "f0", "trai")
        tc = _lay("cu", 2, i, "f0", "trai")
        if None in (a, b, c, da, db, dc):
            continue
        hoi_f0.append(abs(a - b)); san_f0.append(abs(a - c))
        hoi_d.append(abs(da - db)); san_d.append(abs(da - dc))
        if None not in (ta, tb, tc):
            hoi_tr.append(abs(ta - tb)); san_tr.append(abs(ta - tc))
        print(f"{i:<4}{a:>9.2f}{b:>10.2f}{abs(a-b):>8.2f}{abs(a-c):>8.2f}"
              f" | {da:>8.2f}{db:>9.2f}{abs(da-db):>8.2f}{abs(da-dc):>8.2f}")

    def _dai(x):
        return (f"{min(x):.2f}-{max(x):.2f} (TB {st.mean(x):.2f})"
                if x else "—")
    print("-" * 74)
    print(f"  F0 trung vị (nửa cung)  HỎI {_dai(hoi_f0)}")
    print(f"                          SÀN {_dai(san_f0)}")
    print(f"  ĐỘ TRẢI F0 (nửa cung)   HỎI {_dai(hoi_tr)}")
    print(f"                          SÀN {_dai(san_tr)}")
    print(f"  THỜI LƯỢNG (giây)       HỎI {_dai(hoi_d)}")
    print(f"                          SÀN {_dai(san_d)}")

    # ── BẢNG 2: NGẮT GIỮA CÂU + TRẦN edge bản ngữ ────────────────────────
    print("\n" + "=" * 74)
    print("BẢNG 2 — NGẮT GIỮA CÂU (thước của triệu chứng \"đánh vần\")")
    print("=" * 74)
    print(f"{'arm':<10}{'ngắt/câu':>10}{'im giữa(s)':>12}{'dài nhất':>10}"
          f"{'ngắt/100kt':>12}{'%có tiếng':>11}{'giây/câu':>10}")

    def _gom(ten: str, ds: list[dict], kt: list[int]):
        if not ds:
            return None
        so = [d["ngat"]["so"] for d in ds]
        im = [d["ngat"]["tong_im"] for d in ds]
        dn = [d["ngat"]["dai_nhat"] for d in ds]
        ty = [d["ngat"]["ty_le_co_tieng"] for d in ds]
        dai = [d["ngat"]["dai"] for d in ds]
        tren100 = [100.0 * s / max(1, n) for s, n in zip(so, kt)]
        r = {"ngat_cau": round(st.mean(so), 2),
             "im_giua_s": round(st.mean(im), 3),
             "dai_nhat": round(max(dn), 3),
             "ngat_100kt": round(st.mean(tren100), 2),
             "ty_co_tieng": round(st.mean(ty), 4),
             "giay_cau": round(st.mean(dai), 2),
             "ngat_dai": so}
        print(f"{ten:<10}{r['ngat_cau']:>10.2f}{r['im_giua_s']:>12.3f}"
              f"{r['dai_nhat']:>10.3f}{r['ngat_100kt']:>12.2f}"
              f"{r['ty_co_tieng']*100:>10.1f}%{r['giay_cau']:>10.2f}")
        return r

    kt = [len(t) for t in cau]
    bang2 = {}
    for arm in ("cu", "moi"):
        for v in (1, 2):
            ds = [do[f"{arm}{v}_c{i:02d}"] for i in range(len(cau))
                  if f"{arm}{v}_c{i:02d}" in do]
            nhan = ("vnb: CŨ" if arm == "cu" else "vnb: MỚI") + f" l{v}"
            bang2[f"{arm}{v}"] = _gom(nhan, ds, kt)
    bang2["tran"] = _gom("TRẦN edge", tran, kt)
    print("  (TRẦN = edge-tts en-US-Andrew bản ngữ, CÙNG bộ câu, CÙNG lượt)")

    print("\n  DẢI SỐ NGẮT TỪNG CÂU:")
    for k, r in bang2.items():
        if r:
            print(f"    {k:<6} {r['ngat_dai']}")

    ket_ra = {
        "cau": cau, "vong": VONG,
        "wall_s": round(wall, 1), "nap_s": ket["nap"], "enrol_s": ket["enrol"],
        "bang1_v244": {
            "f0_tv_hoi": hoi_f0, "f0_tv_san": san_f0,
            "f0_trai_hoi": hoi_tr, "f0_trai_san": san_tr,
            "dai_hoi": hoi_d, "dai_san": san_d,
        },
        "bang2_ngat": bang2,
        "chi_tiet": do,
        "tran_chi_tiet": tran,
    }
    RA.write_text(json.dumps(ket_ra, ensure_ascii=False, indent=1), "utf-8")
    print(f"\nĐÃ GHI {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
