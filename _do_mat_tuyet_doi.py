# -*- coding: utf-8 -*-
"""MẤT TIẾNG ĐO BẰNG **ĐỘ TỤT TUYỆT ĐỐI** — chữa một phép đo THIÊN VỊ
(19/08/2026).

──────────────────────────────────────────────────────────────────────────
VÌ SAO PHẢI CÓ FILE NÀY — thước cũ CHẤM HAI ARM BẰNG HAI CÂY THƯỚC KHÁC NHAU
──────────────────────────────────────────────────────────────────────────
`_do_mat_giong.khoang_mat` gọi một cửa sổ là "IM" khi nó không nổi quá
`SÀN_NHIỄU_CỦA_CHÍNH_FILE_ĐÓ + 4 dB`, mà sàn nhiễu = **bách phân vị 20 của
chính file**. Cái đó đúng cho đường `"tach"` (tiếng gốc bị BỎ HẲN -> chỗ mất tụt
về đáy), nhưng nó **THIÊN VỊ** khi đem so hai arm:

  arm DE giữ NGUYÊN tiếng gốc -> lớp giọng của nó ĐẦY HƠN -> ít cửa sổ im hơn
  -> bách phân vị 20 CAO HƠN -> ngưỡng "IM" cao hơn -> **những cửa sổ chỉ NHỎ
  ĐI (bị ducking/hạ nền) bị chấm thành MẤT.**

ĐO ĐƯỢC trên video 2 (`一款…倒忌时`, 363,2 s), CÙNG lượt chạy, CÙNG bản gốc:
    arm TACH: sàn xuất **-31,91** dBFS -> ngưỡng IM **-27,91** -> MẤT 5,90 s
    arm DE:   sàn xuất **-24,14** dBFS -> ngưỡng IM **-20,14** -> MẤT 10,30 s
Ngưỡng của arm DE **KHẮT KHE HƠN 7,77 dB**. Đọc thẳng "DE mất nhiều hơn" là
đúng cái bẫy *"số thô là SỐ LỪA"* đã sập 3 lần trên máy này.

──────────────────────────────────────────────────────────────────────────
THƯỚC ĐÚNG: **ĐỘ TỤT so với CHÍNH BẢN GỐC tại CÙNG cửa sổ**
──────────────────────────────────────────────────────────────────────────
"Mất tiếng" = *nội dung biến mất*, không phải *nội dung nhỏ đi*. Nên:

    MẤT(i)  <=>  gốc CÓ tiếng tại i   VÀ   bao_gốc[i] - bao_xuất[i] > TRU_DB

Cả hai arm dùng **CÙNG sàn nhiễu (của BẢN GỐC)** và **CÙNG ngưỡng tụt** -> hết
thiên vị theo cấu tạo.

`TRU_DB` **SUY TỪ CHÍNH HẰNG SỐ CỦA APP, không phải số đặt cho bảng đẹp**: ở chế
độ đè, tiếng gốc chỉ bị hạ tối đa `HA_NHAC_TOI_DA_DB` (**8 dB**, hạ tĩnh) cộng
`DUCK_DB_DO_DUOC` (**3,28 dB**, ducking lúc đang nói) = **11,28 dB**. Đó là mức
tụt HỢP LỆ LỚN NHẤT mà thiết kế cho phép. Đặt `TRU_DB = 20` chừa **8,7 dB** biên
trên mức đó, trong khi chỗ tiếng bị BỎ HẲN tụt xuống sàn nhiễu (đo được 25-40
dB). Hai nhóm cách nhau rất xa nên ngưỡng không phải chỗ tinh chỉnh — và bảng
PHÂN BỐ ĐỘ TỤT in ra để tự kiểm điều đó (nếu hai nhóm dính nhau thì ngưỡng này
vô nghĩa và bảng phải nói ra).

CHẠY LẠI TRÊN CHÍNH FILE HAI ARM ĐÃ XUẤT (`_NGHE_THU_ANH_HUNG/de_giong/
TACH_*.mp4` và `DE_*.mp4`) nên **không phải chạy lại dây chuyền** — vẫn đúng
tinh thần GHÉP CẶP vì hai file đó ra từ MỘT lượt chạy.

Chạy:  .venv/Scripts/python -u _do_mat_tuyet_doi.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "de_giong"
SB = REPO / "bq_mat_tuyet_doi"
KQ = REPO / "_kq_mat_tuyet_doi.json"

BUOC = 0.05
DAI_MIN = 0.30
NOI_CO = 12.0
#: Xem docstring: 8,0 (hạ tĩnh tối đa) + 3,28 (ducking đo được) = 11,28 dB là
#: mức tụt HỢP LỆ lớn nhất -> 20 dB chừa 8,7 dB biên.
TRU_DB = 20.0
BAC = ((0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 1e9))
TEN_BAC = ("<0,5s", "0,5-1s", "1-2s", ">=2s")


def khoang_tut(bao_g: list[float], bao_x: list[float],
               tru_db: float = TRU_DB) -> tuple[list, dict]:
    """Cửa sổ gốc CÓ tiếng mà bản xuất TỤT quá `tru_db` dB so với gốc."""
    import _do_mat_giong as DM
    sg = DM._san_nhieu(bao_g)                # SÀN CỦA BẢN GỐC cho CẢ HAI arm
    ng = sg + NOI_CO
    n = min(len(bao_g), len(bao_x))
    co = [bao_g[i] > ng for i in range(n)]
    tut = [bao_g[i] - bao_x[i] for i in range(n)]
    mat = [co[i] and tut[i] > tru_db for i in range(n)]

    kh: list[list[float]] = []
    i = 0
    while i < n:
        if not mat[i]:
            i += 1
            continue
        j, ho, k = i, 0, i
        while k < n:
            if mat[k]:
                j, ho = k, 0
            else:
                ho += 1
                if ho > 2:
                    break
            k += 1
        kh.append([i * BUOC, (j + 1) * BUOC])
        i = k
    kh = [x for x in kh if (x[1] - x[0]) >= DAI_MIN]
    # PHÂN BỐ ĐỘ TỤT ở các cửa sổ gốc CÓ tiếng — để tự kiểm ngưỡng 20 dB: hai
    # nhóm ("nhỏ đi" và "biến mất") phải TÁCH RỜI, không thì ngưỡng vô nghĩa.
    tut_co = sorted(tut[i] for i in range(n) if co[i])
    pb_tut = {}
    for lo, hi in ((-1e9, 5), (5, 11.28), (11.28, 20), (20, 30), (30, 1e9)):
        ten = (f"<5" if hi == 5 else f"5-11,28" if hi == 11.28
               else f"11,28-20" if hi == 20 else f"20-30" if hi == 30
               else ">=30")
        pb_tut[ten] = sum(1 for x in tut_co if lo <= x < hi)
    return kh, {
        "san_goc_db": round(sg, 2), "nguong_co_db": round(ng, 2),
        "tru_db": tru_db, "so_o": n,
        "giay_co_tieng_goc": round(sum(co) * BUOC, 2),
        "giay_mat": round(sum(x[1] - x[0] for x in kh), 2),
        "so_khoang": len(kh),
        "tut_tb_db": round(sum(tut_co) / max(1, len(tut_co)), 2),
        "tut_bpv90_db": round(tut_co[int(len(tut_co) * 0.9)], 2)
        if tut_co else None,
        "tut_max_db": round(max(tut_co), 2) if tut_co else None,
        "phan_bo_tut_o": pb_tut,
        "khoang": [[round(a, 2), round(b, 2)] for a, b in kh],
        "phan_bo": _pb(kh),
    }


def _pb(kh: list) -> dict:
    ra = {t: 0.0 for t in TEN_BAC}
    for a, b in kh:
        d = b - a
        for (lo, hi), t in zip(BAC, TEN_BAC):
            if lo <= d < hi:
                ra[t] += d
                break
    return {k: round(v, 2) for k, v in ra.items()}


def bao(video: Path, lam: Path, ten: str) -> list[float]:
    import _do_mat_giong as DM
    from app.core import thay_giong as TG
    w = lam / f"w_{ten}.wav"
    DM.rut_wav(video, w)
    t = TG.tach_giong(w, lam / f"t_{ten}", cach="demucs")
    return TG.duong_bao_muc(t["giong"], buoc=BUOC)


def main() -> int:
    import _do_mat_giong as DM
    from app.core import thay_giong as TG

    cap = []
    for g in sorted(NGUON.glob("*.mp4")):
        a, b = NGHE / f"TACH_{g.name}", NGHE / f"DE_{g.name}"
        if a.exists() and b.exists():
            cap.append((g, a, b))
    if not cap:
        print(f"KHÔNG có cặp TACH_*/DE_* nào trong {NGHE} — chạy "
              f"_do_de_giong.py trước")
        return 2
    print(f"{len(cap)} cặp arm · TRU_DB = {TRU_DB} dB "
          f"(hạ tĩnh {TG.HA_NHAC_TOI_DA_DB} + ducking {TG.DUCK_DB_DO_DUOC} "
          f"= {TG.HA_NHAC_TOI_DA_DB + TG.DUCK_DB_DO_DUOC:.2f} dB hợp lệ)")
    SB.mkdir(exist_ok=True)
    ket: dict = {}
    if KQ.exists():
        try:
            ket = json.loads(KQ.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            ket = {}
    try:
        for i, (g, va, vb) in enumerate(cap, 1):
            if ket.get(g.name, {}).get("ok"):
                print(f"\n[{i}] ĐÃ CÓ, bỏ qua: {g.stem[:34]}")
                continue
            print(f"\n{'=' * 74}\n[{i}/{len(cap)}] {g.stem[:44]}")
            lam = SB / f"v{i}"
            shutil.rmtree(lam, ignore_errors=True)
            lam.mkdir(parents=True, exist_ok=True)
            try:
                dai = TG.probe_duration(g)
                print("  Demucs: gốc...")
                bg = bao(g, lam, "goc")
                r: dict = {"ok": True, "dai": round(dai, 2)}
                for nhan, v in (("TACH", va), ("DE", vb)):
                    print(f"  Demucs: {nhan}...")
                    bx = bao(v, lam, nhan)
                    # thước CŨ (sàn theo TỪNG file) để đối chiếu
                    _kh_cu, tk_cu = DM.khoang_mat(bg, bx)
                    kh, tk = khoang_tut(bg, bx)
                    r[nhan] = {"tuyet_doi": tk, "tuong_doi_cu": {
                        "giay_mat": tk_cu["giay_mat"],
                        "san_xuat_db": tk_cu["san_xuat_db"],
                        "nguong_im_db": tk_cu["nguong_im_db"]}}
                    print(f"    >>> {nhan}: TUYỆT ĐỐI MẤT {tk['giay_mat']:.2f}s"
                          f" / {tk['so_khoang']} khoảng "
                          f"({100 * tk['giay_mat'] / max(1e-9, dai):.2f}%)"
                          f"  · thước CŨ (thiên vị) {tk_cu['giay_mat']:.2f}s")
                    print(f"        độ tụt ở ô gốc-có-tiếng: TB "
                          f"{tk['tut_tb_db']} · 90% {tk['tut_bpv90_db']} · max "
                          f"{tk['tut_max_db']} dB")
                    print(f"        phân bố số ô theo độ tụt: "
                          f"{tk['phan_bo_tut_o']}")
                    for a2, b2 in kh[:12]:
                        print(f"          {a2:7.2f} -> {b2:7.2f} "
                              f"({b2 - a2:.2f}s)")
                ket[g.name] = r
            except Exception as e:                          # noqa: BLE001
                import traceback
                traceback.print_exc()
                ket[g.name] = {"ok": False, "loi": f"{type(e).__name__}: {e}"}
            KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                          encoding="utf-8")
            shutil.rmtree(lam, ignore_errors=True)
    finally:
        shutil.rmtree(SB, ignore_errors=True)

    print(f"\n{'=' * 74}\nBẢNG — MẤT TIẾNG, HAI THƯỚC ĐẶT CẠNH NHAU")
    print(f"{'video':<26}{'dài':>9}"
          f"{'TACH tđối':>11}{'DE tđối':>10}{'TACH cũ':>10}{'DE cũ':>8}")
    t = {"TACH": 0.0, "DE": 0.0, "TACHc": 0.0, "DEc": 0.0}
    tv = 0.0
    pb = {a: {x: 0.0 for x in TEN_BAC} for a in ("TACH", "DE")}
    for ten, v in ket.items():
        if not v.get("ok"):
            print(f"{ten[:24]:<26}  LỖI {str(v.get('loi'))[:36]}")
            continue
        tv += v["dai"]
        for a in ("TACH", "DE"):
            t[a] += v[a]["tuyet_doi"]["giay_mat"]
            t[a + "c"] += v[a]["tuong_doi_cu"]["giay_mat"]
            for x in TEN_BAC:
                pb[a][x] += v[a]["tuyet_doi"]["phan_bo"].get(x, 0.0)
        print(f"{ten[:24]:<26}{v['dai']:>8.1f}s"
              f"{v['TACH']['tuyet_doi']['giay_mat']:>10.2f}s"
              f"{v['DE']['tuyet_doi']['giay_mat']:>9.2f}s"
              f"{v['TACH']['tuong_doi_cu']['giay_mat']:>9.2f}s"
              f"{v['DE']['tuong_doi_cu']['giay_mat']:>7.2f}s")
    print(f"{'TỔNG':<26}{tv:>8.1f}s{t['TACH']:>10.2f}s{t['DE']:>9.2f}s"
          f"{t['TACHc']:>9.2f}s{t['DEc']:>7.2f}s")
    if tv > 0:
        print(f"{'% thời lượng':<26}{'':>9}{100 * t['TACH'] / tv:>10.2f}%"
              f"{100 * t['DE'] / tv:>9.2f}%{100 * t['TACHc'] / tv:>9.2f}%"
              f"{100 * t['DEc'] / tv:>7.2f}%")
    print(f"\nPHÂN BỐ ĐỘ DÀI KHOẢNG (thước TUYỆT ĐỐI, giây)")
    print(f"{'arm':<8}" + "".join(f"{x:>10}" for x in TEN_BAC) + f"{'tổng':>10}")
    for a in ("TACH", "DE"):
        print(f"{a:<8}" + "".join(f"{pb[a][x]:>10.2f}" for x in TEN_BAC)
              + f"{t[a]:>10.2f}")
    print(f"\nĐÍCH mất tiếng = 0,00 s -> arm DE (thước tuyệt đối) ra "
          f"{t['DE']:.2f}s" + ("  ĐẠT" if t["DE"] <= 0.0 else "  CHƯA ĐẠT"))
    if t["TACH"] <= 0.0:
        print("!! arm TACH cũng 0,00s -> THƯỚC KHÔNG CÓ RĂNG, số của DE vô nghĩa")
    else:
        print(f"chốt chống-đạt-oan: arm TACH ra {t['TACH']:.2f}s > 0 -> thước "
              f"CÓ RĂNG")
    print(f"=> {KQ.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
