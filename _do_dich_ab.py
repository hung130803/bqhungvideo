# -*- coding: utf-8 -*-
"""A/B ĐƯỜNG DỊCH — MỐC (`thay_giong._dich_loat`) vs MỚI (`app.ai.dich`).

Đo trên VIDEO THẬT của anh Hùng (`_do_dich_cache.json` — 50 câu tiếng Trung,
107,24 s, nhãn Groq trả về là `'Chinese'` chứ không phải `zh`).

BỐN NHÓM SỐ, mỗi nhóm trả lời đúng một việc CLAUDE.md giao:
  1. **CHẤT LƯỢNG** — chấm bằng `app.ai.cham_dich` (4 trục tách bạch + cửa
     thuật ngữ + luật máy). `nghia` bắt *sai thuật ngữ*, `xuoi` bắt *ngược
     tai*, `tron` + luật máy bắt *cụt/gộp*.
  2. **CỤT / GỘP theo SỐ KÝ TỰ** — đúng thước CLAUDE.md đã dùng (câu < 20 ký
     tự · câu > 60 ký tự), để so được với con số cũ 8%/15% và 6/38, 6/40.
  3. **CHÊNH THỜI GIAN ĐỌC so với KHUNG CÂU GỐC** — đây là VIỆC 3. Đọc THẬT
     bằng edge-tts rồi **cắt lề im** (đo trên file thô là sai ~1,07 s/câu),
     so với `end - start` của câu gốc.
  4. **SÓT CHỮ GỐC** — câu còn chữ Hán đi thẳng vào giọng Việt.

**ĐAN XEN BẮT BUỘC.** Mỗi lượt chạy MỐC rồi MỚI rồi mới sang lượt sau, và
lượt CHẴN đảo thứ tự. Máy này luôn có luồng khác chạy nền + Groq có lúc quá
tải; đo liền mạch (tất cả lượt MỐC trước) đã ra kết luận sai 3 lần trong repo.

  .venv\\Scripts\\python -u _do_dich_ab.py            # 3 lượt
  BQ_LUOT=1 .venv\\Scripts\\python -u _do_dich_ab.py  # thử nhanh
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

CACHE = REPO / "_do_dich_cache.json"
RA = REPO / "_do_dich_ab.json"
SO_LUOT = int(os.environ.get("BQ_LUOT", "3"))
#: bỏ hẳn bước đọc TTS (chỉ đo chất lượng chữ) — dùng khi mạng edge-tts hỏng
BO_TTS = os.environ.get("BQ_BO_TTS", "") == "1"

CUT_KY_TU = 20            # câu dưới ngần này ký tự = nghi CỤT (thước CLAUDE.md)
DAI_KY_TU = 60            # câu trên ngần này ký tự = nghi GỘP


def _don(p: Path) -> None:
    shutil.rmtree(p, ignore_errors=True)


def _quet_san_cu() -> None:
    for p in REPO.glob("bq_dichab_*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def nap_corpus() -> tuple[list[dict], str]:
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    return d["cau"], d.get("language") or "zh"


# --------------------------------------------------------------------------
def arm_moc(cau, goc_ma) -> dict:
    """MỐC — đúng hàm app đang chạy, KHÔNG sửa gì."""
    from app.core.thay_giong import _dich_loat
    t0 = time.time()
    bd = _dich_loat(cau, "vi", goc_ma)
    return {"ban_dich": bd, "giay": round(time.time() - t0, 1)}


def arm_moi(cau, goc_ma) -> dict:
    from app.ai.dich import dich_theo_gio
    t0 = time.time()
    kq = dich_theo_gio(cau, "vi", goc_ma)
    kq["giay"] = round(time.time() - t0, 1)
    return kq


# --------------------------------------------------------------------------
def do_tts(texts: list[str], san: Path) -> list[float]:
    """Đọc THẬT rồi trả độ dài TIẾNG (đã cắt lề im) từng câu. Hỏng -> 0.0."""
    if BO_TTS:
        return [0.0] * len(texts)
    from app.core.thay_giong import doc_ban_dich, probe_duration
    san.mkdir(parents=True, exist_ok=True)
    kq = doc_ban_dich(texts, san, dich_sang="vi")
    ra = []
    for i in range(len(texts)):
        f = kq["files"][i] if i < len(kq["files"]) else ""
        if kq["ok"][i] and f and Path(f).exists():
            ra.append(probe_duration(f))
        else:
            ra.append(0.0)
    return ra


def do_mot_arm(ten: str, cau, goc_ma, ban_dich: list[str], san: Path) -> dict:
    from app.ai import cham_dich as CD

    goc = [c["text"] for c in cau]
    khung = [float(c["end"]) - float(c["start"]) for c in cau]

    kq = CD.cham_ban_dich(goc, ban_dich, goc_ma=goc_ma, dich_ma="vi")
    tts = do_tts(ban_dich, san)

    # --- chênh thời gian ---
    lech = [tts[i] - khung[i] for i in range(len(cau)) if tts[i] > 0]
    thua = [x for x in lech if x < 0]            # đọc NGẮN hơn khung = trống
    tran = [x for x in lech if x > 0]            # đọc DÀI hơn khung = phải ép
    tong_trong = -sum(thua)
    tong_khung = sum(khung)

    ky_tu = [len(t) for t in ban_dich]
    tr = {
        "ten": ten,
        "n": len(cau),
        "ty_le_dat": kq["ty_le_dat"],
        "diem_tb": kq["diem_tb"],
        "so_loi_may": kq["so_loi_may"],
        "so_thuat_ngu": kq["so_thuat_ngu"],
        "loi_may_chi_tiet": {},
        "truc": {},
        "cau_ngan": sum(1 for k in ky_tu if k < CUT_KY_TU),
        "cau_dai": sum(1 for k in ky_tu if k > DAI_KY_TU),
        "ky_tu_tb": round(sum(ky_tu) / max(1, len(ky_tu)), 1),
        "sot_chu_goc": sum(1 for i, c in enumerate(kq["cau"])
                           if "con_chu_goc" in c["loi"]),
        "tts_do_duoc": len(lech),
        "lech_tuyet_doi_tb": round(sum(abs(x) for x in lech) / max(1, len(lech)), 3),
        "trong_tong": round(tong_trong, 2),
        "trong_ty_le": round(100.0 * tong_trong / max(0.01, tong_khung), 1),
        "tran_tong": round(sum(tran), 2),
        "so_cau_trong_1s": sum(1 for x in thua if x < -1.0),
        "so_cau_tran": len(tran),
        "tong_khung": round(tong_khung, 2),
        "tong_doc": round(sum(x for x in tts if x > 0), 2),
    }
    for k in CD.TIEU_CHI:
        v = [c[k] for c in kq["cau"] if c.get(k) is not None]
        tr["truc"][k] = round(sum(v) / len(v), 2) if v else None
    for c in kq["cau"]:
        for m in c["loi"]:
            tr["loi_may_chi_tiet"][m] = tr["loi_may_chi_tiet"].get(m, 0) + 1
    tr["cau_cham"] = kq["cau"]
    return tr


def in_arm(t: dict) -> None:
    print(f"  --- {t['ten']} ---")
    print(f"    ĐẠT theo thước       : {t['ty_le_dat']:.1f}%  "
          f"(điểm TB {t['diem_tb']})")
    print(f"    4 trục TB            : " +
          " · ".join(f"{k} {v}" for k, v in t["truc"].items()))
    print(f"    cửa thuật ngữ bắt    : {t['so_thuat_ngu']}/{t['n']}")
    print(f"    luật máy bắt         : {t['so_loi_may']}/{t['n']} "
          f"{t['loi_may_chi_tiet'] or ''}")
    print(f"    còn chữ gốc (Hán)    : {t['sot_chu_goc']}/{t['n']}")
    print(f"    câu < {CUT_KY_TU} ký tự (cụt) : {t['cau_ngan']}/{t['n']} = "
          f"{100.0*t['cau_ngan']/max(1,t['n']):.0f}%  · "
          f"câu > {DAI_KY_TU} ký tự (gộp): {t['cau_dai']}/{t['n']}")
    print(f"    ký tự/câu TB         : {t['ky_tu_tb']}")
    if t["tts_do_duoc"]:
        print(f"    THỜI GIAN ĐỌC (edge-tts thật, đã cắt lề im):")
        print(f"      tổng đọc {t['tong_doc']:.1f}s / tổng khung "
              f"{t['tong_khung']:.1f}s")
        print(f"      lệch tuyệt đối TB {t['lech_tuyet_doi_tb']:.3f}s/câu")
        print(f"      TRỐNG (đọc ngắn hơn khung) {t['trong_tong']:.1f}s = "
              f"{t['trong_ty_le']:.1f}% khung · "
              f"{t['so_cau_trong_1s']} câu trống quá 1s")
        print(f"      TRÀN (đọc dài hơn khung)   {t['tran_tong']:.1f}s · "
              f"{t['so_cau_tran']} câu")


# --------------------------------------------------------------------------
def main() -> int:
    _quet_san_cu()
    if not CACHE.exists():
        print("Chưa có corpus. Chạy `_do_dich_corpus.py` trước.")
        return 2
    cau, goc_ma = nap_corpus()
    print("=" * 74)
    print(f"A/B ĐƯỜNG DỊCH — {len(cau)} câu · nhãn ngôn ngữ {goc_ma!r} · "
          f"{SO_LUOT} lượt ĐAN XEN")
    print(f"TTS: {'TẮT (chỉ đo chữ)' if BO_TTS else 'edge-tts THẬT'}")
    print("=" * 74)

    san = REPO / f"bq_dichab_{os.getpid()}"
    san.mkdir(parents=True, exist_ok=True)
    atexit.register(_don, san)

    tat_ca = []
    for lu in range(SO_LUOT):
        thu_tu = [("MỐC", arm_moc), ("MỚI", arm_moi)]
        if lu % 2 == 1:
            thu_tu.reverse()                     # ĐAN XEN: đảo thứ tự lượt chẵn
        print(f"\n{'=' * 74}\nLƯỢT {lu + 1}  (thứ tự chạy: "
              f"{' -> '.join(t for t, _ in thu_tu)})\n{'=' * 74}")
        mot = {}
        for ten, f in thu_tu:
            try:
                r = f(cau, goc_ma)
            except Exception as e:               # noqa: BLE001
                print(f"  {ten}: LỖI {type(e).__name__}: {e}")
                continue
            mot[ten] = {"raw": r}
        for ten in ("MỐC", "MỚI"):
            if ten not in mot:
                continue
            bd = mot[ten]["raw"]["ban_dich"]
            t = do_mot_arm(ten, cau, goc_ma, bd,
                           san / f"l{lu}_{'moc' if ten == 'MỐC' else 'moi'}")
            t["ban_dich"] = bd
            if ten == "MỚI":
                r = mot[ten]["raw"]
                t["so_lech_truoc"] = r["so_lech_truoc"]
                t["so_lech_sau"] = r["so_lech_sau"]
                t["so_viet_lai"] = r["so_viet_lai"]
                t["thieu_cau"] = r["thieu_cau"]
            mot[ten] = t
            in_arm(t)
            if ten == "MỚI":
                print(f"    ngân sách: lệch TRƯỚC hậu kiểm "
                      f"{t['so_lech_truoc']}/{t['n']} -> SAU "
                      f"{t['so_lech_sau']}/{t['n']} "
                      f"(viết lại được {t['so_viet_lai']} câu"
                      f", thiếu {t['thieu_cau']} câu)")
        tat_ca.append(mot)

    # ---------------- TỔNG ----------------
    print(f"\n{'=' * 74}\nTỔNG {SO_LUOT} LƯỢT\n{'=' * 74}")
    cot = [("ĐẠT thước %", "ty_le_dat"), ("điểm TB", "diem_tb"),
           ("thuật ngữ bắt", "so_thuat_ngu"), ("luật máy bắt", "so_loi_may"),
           ("còn chữ Hán", "sot_chu_goc"),
           (f"câu<{CUT_KY_TU}kt", "cau_ngan"), (f"câu>{DAI_KY_TU}kt", "cau_dai"),
           ("lệch |s|/câu", "lech_tuyet_doi_tb"),
           ("TRỐNG s", "trong_tong"), ("TRỐNG %khung", "trong_ty_le"),
           ("TRÀN s", "tran_tong")]
    print(f"  {'chỉ số':<16} | " +
          " | ".join(f"MỐC l{i+1}" for i in range(SO_LUOT)) + " || " +
          " | ".join(f"MỚI l{i+1}" for i in range(SO_LUOT)) + " || TB MỐC -> TB MỚI")
    for ten, k in cot:
        va, vb = [], []
        for m in tat_ca:
            va.append(m.get("MỐC", {}).get(k))
            vb.append(m.get("MỚI", {}).get(k))
        sa = [x for x in va if x is not None]
        sb = [x for x in vb if x is not None]
        f = lambda v: ("  -  " if v is None else f"{v:6.2f}")   # noqa: E731
        tb_a = sum(sa) / len(sa) if sa else float("nan")
        tb_b = sum(sb) / len(sb) if sb else float("nan")
        print(f"  {ten:<16} | " + " | ".join(f(x) for x in va) + " || " +
              " | ".join(f(x) for x in vb) +
              f" || {tb_a:7.2f} -> {tb_b:7.2f}")

    RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nđã ghi {RA.name} (kèm TOÀN BỘ bản dịch từng lượt để đọc tay)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
