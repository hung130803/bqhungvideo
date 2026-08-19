# -*- coding: utf-8 -*-
"""ĐO NHẤN NHÁ 20 GIỌNG VieNeu — cột đang TRỐNG trong `nhan_nha.BANG`.

**VÌ SAO CỘT NÀY TRỐNG LẠI LÀ MỘT LỖI THẬT, KHÔNG PHẢI "CHƯA LÀM TỚI".**
`giong_vieneu.danh_sach_giong` sắp giọng bằng `nhan_nha.khoa_sap(m)`, mà bảng
không có một giọng `vn:` nào -> hàm trả **Y HỆT `(1, 0.0)` cho cả 20 giọng**
-> thứ tự thật rơi hết về tiêu chí phụ là **THỨ TỰ CHỮ CÁI**. Hệ quả đo được:
`vn:Adam` — giọng TIẾNG ANH duy nhất — từng đứng **ĐẦU** danh sách 20 giọng
Việt chỉ vì chữ "A". Anh Hùng chạy 200-300 kênh Việt; bấm nhầm một lần là hàng
trăm video đọc bằng giọng Anh. (`giong_vieneu` đã vá tạm bằng cách đẩy nhóm
tiếng Anh xuống cuối, nhưng 19 giọng Việt còn lại vẫn xếp theo bảng chữ cái.)

═══════════════════════════════════════════════════════════════════════════
PHẦN 1 — CHỨNG MINH BẪY "BỘ CÂU SAI TIẾNG" LÀ CÓ THẬT
═══════════════════════════════════════════════════════════════════════════
`_do_nhan_nha_bang.cau_cho` tra bộ câu theo tiền tố mã giọng. Danh sách tiền
tố đó ra đời TRƯỚC `giong_vieneu.py`, nên `vn:Minh Đức` không khớp gì rồi rơi
vào **nhánh lùi tiếng Anh** — bắt một bộ đọc CHỈ BIẾT TIẾNG VIỆT đọc
*"A storm unlike anything in recorded history…"* rồi ghi số vào cùng cột với
`vi-VN-*`. Đây đúng là bẫy đã làm `piper:vais1000` ra **1,88** (thấp nhất
toàn bảng) ở lượt trước.

Phần 1 KHÔNG lập luận, nó **ĐO**: cùng một giọng, cùng một thước, chỉ khác bộ
câu, chạy **ĐAN XEN** (vi, en, en, vi) để nhiễu máy không dồn về một arm.

═══════════════════════════════════════════════════════════════════════════
PHẦN 2 — ĐO 20 GIỌNG BẰNG BỘ CÂU TIẾNG VIỆT
═══════════════════════════════════════════════════════════════════════════
Đúng thước cổng 76 (`_do_nhan_nha.f0_nua_cung`), đúng cửa thật
(`dubbing._synth_all`), đúng bộ câu `CAU["vi"]` mà `vi-VN-*` đã dùng — nên số
ra so được với NamMinh 4,04 · HoaiMy 3,18 trong cùng một cột.

**CẤM SO CHÉO TIẾNG** (`nhan_nha` giới hạn số 1): `vn:Adam` đọc tiếng Anh nên
số của nó **KHÔNG** đứng chung thang với 19 giọng Việt. Nó vẫn được đo (để
biết), nhưng phải đo bằng bộ câu tiếng Anh và bảng ghi rõ cột riêng.

Chạy:  .venv\\Scripts\\python -u _do_nhan_nha_vn.py
       .venv\\Scripts\\python -u _do_nhan_nha_vn.py --bay-only
       .venv\\Scripts\\python -u _do_nhan_nha_vn.py --in-bang
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics as st
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "bq_do_nhan_nha_vn"
KQ = SAN / "ket_qua.json"

#: Giọng dùng cho phép thử bẫy. Chọn `Ngọc Huyền` vì nó là giọng mặc định
#: `giong_vieneu` dùng ở mọi ví dụ, tức giọng nhiều người chạm nhất.
GIONG_BAY = "vn:Ngọc Huyền"


def _do_voi_cau(voice: str, texts: list[str], nhan: str) -> dict:
    """Đọc `texts` bằng CỬA THẬT rồi đo F0 — không dùng `cau_cho`.

    Tách khỏi `_do_nhan_nha_bang.do_mot` đúng một chỗ: bộ câu truyền vào tay.
    Mọi thứ còn lại (cửa, thước, cách quy WAV) **import chứ không chép** —
    hai bản thước là hai bảng số không so được với nhau.
    """
    from _do_nhan_nha import f0_nua_cung
    from _do_nhan_nha_bang import ra_wav
    from app.core import dubbing

    tm = SAN / f"{voice.replace(':', '_').replace(' ', '_')}__{nhan}"
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    paths = [str(tm / f"c{i}.mp3") for i in range(len(texts))]
    t0 = time.monotonic()
    try:
        ok = asyncio.run(dubbing._synth_all(texts, voice, paths))
    except Exception as e:                                    # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    files = [p for p, o in zip(paths, ok) if o and Path(p).exists()]
    if not files:
        return {"loi": "không đọc được câu nào"}
    tat: list[float] = []
    for i, p in enumerate(files):
        w = tm / f"w{i}.wav"
        if not ra_wav(Path(p), w):
            continue
        d = f0_nua_cung(w)
        if len(d) >= 20:
            tat.extend(d)
    if len(tat) < 50:
        return {"loi": f"quá ít khung có tiếng ({len(tat)})"}
    return {"nhan_nha": round(st.pstdev(tat), 2),
            "so_khung": len(tat), "so_cau": len(files),
            "f0_giua_hz": round(100.0 * 2 ** (st.median(tat) / 12.0), 1),
            "giay": round(time.monotonic() - t0, 1)}


# ---------------------------------------------------------------------------
# PHẦN 1 — bẫy bộ câu sai tiếng
# ---------------------------------------------------------------------------
def phan_1() -> dict:
    """Cùng giọng, cùng thước, khác bộ câu. ĐAN XEN vi/en/en/vi."""
    from _do_nhan_nha_bang import CAU

    print("=" * 74)
    print("PHẦN 1 — BỘ CÂU SAI TIẾNG LÀM LỆCH BAO NHIÊU")
    print(f"giọng {GIONG_BAY} (VieNeu, bộ đọc CHỈ tiếng Việt) · thước "
          f"f0_nua_cung · cửa dubbing._synth_all")
    print("=" * 74)
    vi_s, en_s = [], []
    for i, nn in enumerate(("vi", "en", "en", "vi")):      # ĐAN XEN + XOAY
        d = _do_voi_cau(GIONG_BAY, CAU[nn], f"bay_{nn}_{i}")
        if d.get("loi"):
            print(f"  lượt {i+1} bộ câu {nn}: LỖI {d['loi']}")
            continue
        (vi_s if nn == "vi" else en_s).append(d["nhan_nha"])
        print(f"  lượt {i+1} bộ câu {nn.upper():2s} -> nhấn nhá "
              f"{d['nhan_nha']:5.2f} · {d['so_khung']:4d} khung · "
              f"{d['giay']:.0f}s", flush=True)
    if not (vi_s and en_s):
        print("  KHÔNG đủ số liệu -> không kết luận.")
        return {}
    tv, te = st.mean(vi_s), st.mean(en_s)
    print(f"\n  bộ câu VIỆT (đúng tiếng) : {tv:.2f}   {vi_s}")
    print(f"  bộ câu ANH  (nhánh lùi)  : {te:.2f}   {en_s}")
    print(f"  LỆCH: {abs(tv-te):.2f} nửa cung "
          f"(nhiễu của phép đo: 0,12 — xem `nhan_nha`)")
    return {"vi": tv, "en": te, "lech": abs(tv - te),
            "vi_ds": vi_s, "en_ds": en_s}


# ---------------------------------------------------------------------------
# PHẦN 2 — 20 giọng
# ---------------------------------------------------------------------------
#: Số lượt đo MỖI giọng. **KHÔNG PHẢI 1 — VieNeu không tiền định.** Phần 1 đo
#: được cùng giọng cùng bộ câu ra 3,28 và 2,92 (trải 0,36), gấp 3 lần nhiễu
#: của edge-tts (0,12). Một lượt rồi ghi vào bảng là ghi một con số ngẫu
#: nhiên; bảng phải mang TRUNG BÌNH và phải in kèm TRẢI để người đọc biết
#: con số ấy chắc tới đâu.
SO_VONG = int(os.environ.get("BQ_NN_VONG", "3"))


def phan_2(ra: dict) -> dict:
    """Đo `SO_VONG` lượt mỗi giọng, **ĐAN XEN** (xong 1 vòng cả 20 rồi mới
    sang vòng sau). Chạy 3 lượt liên tiếp cùng một giọng là để nhiễu máy dồn
    hết vào một giọng — đúng bài học "Đo A/B phải đan xen" đã sập 3 lần."""
    from _do_nhan_nha_bang import CAU
    from app.core import giong_vieneu as gv

    print("\n" + "=" * 74)
    print(f"PHẦN 2 — NHẤN NHÁ 20 GIỌNG VieNeu · {SO_VONG} LƯỢT ĐAN XEN")
    print("=" * 74)
    ds = [(gv.TIEN_TO + k, k in gv.GIONG_TIENG_ANH) for k, _m in gv.GIONG_VN]
    for v in range(1, SO_VONG + 1):
        k = (v - 1) % max(1, len(ds))
        thu_tu = ds[k:] + ds[:k]                       # XOAY thứ tự mỗi vòng
        print(f"\n--- VÒNG {v}/{SO_VONG} ---", flush=True)
        for ma, anh in thu_tu:
            nn = "en" if anh else "vi"
            khoa = f"{ma}|v{v}"
            if khoa in ra and not ra[khoa].get("loi"):
                d = ra[khoa]
                print(f"  {ma:26s} cache {d['nhan_nha']:5.2f}", flush=True)
                continue
            d = _do_voi_cau(ma, CAU[nn], f"{nn}_v{v}")
            d["nn"] = nn
            ra[khoa] = d
            SAN.mkdir(parents=True, exist_ok=True)
            KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
            if d.get("loi"):
                print(f"  {ma:26s} LỖI: {d['loi']}", flush=True)
            else:
                print(f"  {ma:26s} {d['nhan_nha']:5.2f} · "
                      f"{d['f0_giua_hz']:6.1f}Hz · {d['so_khung']:4d} khung · "
                      f"{d.get('giay', 0):.0f}s", flush=True)
    return ra


def gom(ra: dict) -> dict[str, list[float]]:
    """`vn:X|vN` -> gom lại thành `vn:X` -> [các lượt]."""
    out: dict[str, list[float]] = {}
    for k, v in ra.items():
        if "|" not in k or not isinstance(v, dict) or v.get("loi"):
            continue
        out.setdefault(k.split("|")[0], []).append(v["nhan_nha"])
    return out


def bang_cuoi(ra: dict) -> None:
    from app.core import giong_vieneu as gv
    from app.core import nhan_nha

    tat = gom(ra)
    viet = {k: xs for k, xs in tat.items()
            if gv.ten_giong(k) not in gv.GIONG_TIENG_ANH}
    anh = {k: xs for k, xs in tat.items()
           if gv.ten_giong(k) in gv.GIONG_TIENG_ANH}
    if not viet:
        return
    print("\n" + "=" * 74)
    print("BẢNG NHẤN NHÁ VieNeu — TRUNG BÌNH và DẢI của "
          f"{SO_VONG} lượt")
    print("=" * 74)
    print(f"{'giọng':24s} {'TB':>6s} {'dải':>13s} {'trải':>6s}  mức")
    print("-" * 74)
    tb = {k: st.mean(xs) for k, xs in viet.items()}
    for k, m in sorted(tb.items(), key=lambda kv: -kv[1]):
        xs = viet[k]
        # `nhan_nha.muc()` nhận MÃ GIỌNG và tra bảng; ở đây đang có GIÁ TRỊ
        # vừa đo (chưa vào bảng) nên phải dùng `chu()`. Gọi nhầm thì cột mức
        # in ra `None` cho cả 19 dòng — nhìn như "chưa phân mức được".
        print(f"{k:24s} {m:6.2f} {min(xs):5.2f}–{max(xs):5.2f} "
              f"{max(xs)-min(xs):6.2f}  {nhan_nha.chu(m)}")
    trai = [max(xs) - min(xs) for xs in viet.values() if len(xs) > 1]
    xs = sorted(tb.values())
    print("-" * 74)
    print(f"{len(viet)}/19 giọng VIỆT · TB thấp nhất {xs[0]:.2f} · "
          f"cao nhất {xs[-1]:.2f} · TRẢI GIỮA CÁC GIỌNG {xs[-1]-xs[0]:.2f}")
    if trai:
        print(f"NHIỄU TRONG CÙNG MỘT GIỌNG: trung vị {st.median(trai):.2f} · "
              f"lớn nhất {max(trai):.2f}   <-- so cái này với TRẢI ở trên "
              f"trước khi tin thứ hạng")
    for k, x in anh.items():
        print(f"[cột RIÊNG - tiếng Anh, CẤM so chéo] {k} "
              f"TB {st.mean(x):.2f} dải {min(x):.2f}–{max(x):.2f}")
    print("\nSO VỚI MỐC CÙNG TIẾNG VIỆT (cùng bộ câu, cùng thước):")
    # **MỐC PHẢI TRA BẰNG KHOÁ THẬT.** `piper:vais1000` là tên GỌN trong tài
    # liệu; khoá trong `nhan_nha.BANG` là `piper:vi_VN-vais1000-medium`. Tra
    # bằng khoá ngắn thì `.get()` trả None và dòng mốc **biến mất khỏi bảng**
    # mà không một dòng báo — đọc bảng ra thì tưởng "chưa đo Piper".
    for ten, ma in (("edge-tts NamMinh", "vi-VN-NamMinhNeural"),
                    ("edge-tts HoaiMy", "vi-VN-HoaiMyNeural"),
                    ("Piper vais1000", "piper:vi_VN-vais1000-medium"),
                    ("OmniVoice nam_tre", "ov:nam_tre"),
                    ("OmniVoice nu_am", "ov:nu_am")):
        m = nhan_nha.BANG.get(ma)
        if m is None:
            print(f"  {ten:22s} KHÔNG CÓ trong `nhan_nha.BANG` (khoá {ma!r}) "
                  f"-> kiểm lại khoá, đừng bỏ qua")
            continue
        tren = sum(1 for v in tb.values() if v > m)
        print(f"  {ten:22s} {m:5.2f} -> {tren:2d}/{len(tb)} giọng VieNeu "
              f"nhấn nhá CAO HƠN")


def main() -> int:
    SAN.mkdir(parents=True, exist_ok=True)
    ra: dict = {}
    if KQ.exists():
        try:
            ra = json.loads(KQ.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra = {}
    if "--in-bang" not in sys.argv:
        b1 = phan_1()
        if b1:
            ra["__bay__"] = b1
            KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        if "--bay-only" in sys.argv:
            return 0
    ra = phan_2(ra)
    bang_cuoi(ra)
    if "--in-bang" in sys.argv:
        print("\n--- dán vào nhan_nha.BANG (TRUNG BÌNH các lượt) ---")
        tot = {k: st.mean(xs) for k, xs in gom(ra).items()}
        for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
            print(f'    "{k}": {v:.2f},')
    print(f"\n-> {KQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
