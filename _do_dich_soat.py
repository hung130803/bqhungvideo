# -*- coding: utf-8 -*-
"""A/B **END-TO-END** đường dịch của app: `thay_giong.dich_hau_kiem`.

VÌ SAO CẦN FILE NÀY DÙ ĐÃ CÓ `_do_dich_ab.py`: file kia so `_dich_loat` với
**`dich_theo_gio`** — KHÔNG phải `dich_va_soat`. Mà việc đang xét là nối
`dich_va_soat` (= `dich_theo_gio` + THƯỚC CHẤM + dịch lại câu trượt) vào app.
Tức phần "thước chấm" **chưa ai đo một lần nào**, và nó là phần ĐẮT nhất
(`cham_ban_dich` = hội đồng 3 model + cửa thuật ngữ 3 model).

Và phải đo ở mức `dich_hau_kiem`, KHÔNG phải mức hàm con: sau khi nối,
`dich_hau_kiem` VẪN chạy tiếp `_dich_nguoc_cham` + vòng dịch lại + vòng CJK
của chính nó. Đo hàm con là bỏ qua phần chồng chéo đó — đúng chỗ tốn thời gian.

HAI ARM, ĐAN XEN BẮT BUỘC (thứ tự xoay vòng mỗi lượt):
  · `MỐC`  — `DUNG_DICH_SOAT=False` (app đang chạy hôm nay)
  · `SOÁT` — `DUNG_DICH_SOAT=True`  (bản định nối)

**CẢNH BÁO ĐỌC SỐ — `dat_%` CỦA ARM `SOÁT` LÀ SỐ ĐƯỢC ƯU ÁI.** Nó được chấm
bằng CHÍNH `cham_dich`, tức chính cái thước mà `dich_va_soat` dùng để chọn câu
đi dịch lại. Dạy đúng bài thi thì điểm phải cao. Vì vậy phải đọc kèm 3 cột
KHÔNG do thước đó quyết định: **cụt / gộp theo SỐ KÝ TỰ**, **sót chữ Hán**, và
**lệch thời gian đọc THẬT** (edge-tts). Thước còn tự nhiễu 18,7% (đo ở DO 3)
nên chênh dưới ~5 điểm % là NHIỄU, không phải tiến bộ.

  .venv\\Scripts\\python -u _do_dich_soat.py             # 3 lượt
  BQ_LUOT=1 BQ_BO_TTS=1 .venv\\Scripts\\python -u _do_dich_soat.py
"""
from __future__ import annotations

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
#: Tên file kết quả đi theo BỘ ARM — chạy bộ arm khác KHÔNG được đè lên số đo
#: của bộ trước (lượt đo SOÁT tốn 126s/lượt, mất là phải chạy lại).
RA = REPO / ("_do_dich_soat.json" if os.environ.get("BQ_ARM", "") == ""
             else "_do_dich_" + "_".join(
                 {"MỐC": "moc", "SOÁT": "soat", "GIỜ": "gio"}.get(x.strip(), "x")
                 for x in os.environ["BQ_ARM"].split(",") if x.strip()) + ".json")
SO_LUOT = int(os.environ.get("BQ_LUOT", "3"))
BO_TTS = os.environ.get("BQ_BO_TTS", "") == "1"

CUT_KY_TU = 20            # câu dưới ngần này ký tự = nghi CỤT (thước CLAUDE.md)
DAI_KY_TU = 60            # câu trên ngần này ký tự = nghi GỘP


def _quet_san_cu() -> None:
    for p in REPO.glob("bq_dichsoat_*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def nap_corpus() -> tuple[list[dict], str]:
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    # ĐÚNG như đường sống: `goc_ma = (language or "")[:2].lower()`
    return d["cau"], (d.get("language") or "")[:2].lower()


# --------------------------------------------------------------------------
#: Đếm lượt gọi LLM. **KHÔNG dùng `llm.get_total_usage()`** — bộ đếm đó chỉ
#: được `_add_usage` cộng ở nhánh GEMINI (llm.py:810 và 1125); đường Groq (thứ
#: app đang chạy) không cộng một lượt nào, nên nó ra 0 và trông như "miễn phí".
_DEM = {"n": 0}


def _bat_dem() -> None:
    """Bọc `llm.complete_json` — CỬA DUY NHẤT của cả 3 module (cham_dich ·
    dich · thay_giong đều gọi qua đó)."""
    from app.ai import llm
    if getattr(llm.complete_json, "_da_boc", False):
        return
    goc = llm.complete_json

    def boc(*a, **k):
        _DEM["n"] += 1
        return goc(*a, **k)

    boc._da_boc = True                                   # type: ignore[attr-defined]
    llm.complete_json = boc                              # type: ignore[assignment]


def chay_arm(ten: str, cau, goc_ma) -> dict:
    """Gọi CHÍNH `dich_hau_kiem` của app, chỉ khác CỜ CHỌN ĐƯỜNG DỊCH.

    Ba arm, cùng đi qua `dich_hau_kiem` (nên phần `_dich_nguoc_cham` + vòng
    dịch lại + vòng CJK của chính nó là CHUNG cho cả ba — chỉ khác bước dịch
    ĐẦU):
      · `MỐC`  — `_dich_loat`      (app đang chạy hôm nay)
      · `SOÁT` — `dich_va_soat`    (ngân sách + THƯỚC CHẤM — đã đo, đã bác)
      · `GIỜ`  — `dich_theo_gio`   (ngân sách, KHÔNG thước — hướng còn lại)
    """
    from app.core import thay_giong as TG

    _bat_dem()
    TG.DUNG_DICH_SOAT = (ten == "SOÁT")
    TG.DUNG_DICH_GIO = (ten == "GIỜ")
    n0 = _DEM["n"]
    t0 = time.time()
    dd = TG.dich_hau_kiem(cau, "vi", goc_ma)
    giay = round(time.time() - t0, 1)
    return {
        "ban_dich": list(dd["ban_dich"]),
        "giay": giay,
        "luot_llm": _DEM["n"] - n0,
        "sot_chu_goc_sau": dd.get("sot_chu_goc_sau"),
    }


#: `BQ_ARM="MỐC,GIỜ"` để chỉ đo 2 arm cần (SOÁT đã đo xong và đã bị bác — chạy
#: lại nó tốn 126s/lượt cho một câu trả lời đã có).
ARM = [x.strip() for x in os.environ.get("BQ_ARM", "MỐC,SOÁT").split(",")
       if x.strip()]
TEN_THU_MUC = {"MỐC": "moc", "SOÁT": "soat", "GIỜ": "gio"}


# --------------------------------------------------------------------------
def tu_kiem_duong() -> bool:
    """**ARM NÀO GỌI ĐÚNG HÀM NẤY** — chạy TRƯỚC mọi lượt đo, 0 lượt LLM.

    Vì sao bắt buộc: lượt đo trước đã báo "đã đo A/B `dich_va_soat`" trong khi
    thật ra nó so `dich_theo_gio` — cờ rẽ nhánh sai một chữ là cả bảng số vô
    nghĩa mà KHÔNG một dòng báo. Ở đây vá cả 3 đích + `_dich_nguoc_cham` nên
    không gọi mạng lần nào.
    """
    from app.ai import dich as _D
    from app.core import thay_giong as TG

    goi: list[str] = []
    cu = (TG._dich_loat, _D.dich_theo_gio, _D.dich_va_soat, TG._dich_nguoc_cham)
    cau = [{"start": 0.0, "end": 2.0, "text": "测试"}]
    try:
        TG._dich_loat = lambda c, d, g: (goi.append("loat"), ["x"] * len(c))[1]
        _D.dich_theo_gio = lambda c, *a, **k: (
            goi.append("gio"), {"ban_dich": ["x"] * len(c)})[1]
        _D.dich_va_soat = lambda c, *a, **k: (
            goi.append("soat"), {"ban_dich": ["x"] * len(c)})[1]
        TG._dich_nguoc_cham = lambda g, d, a, b: [10.0] * len(d)
        cho = {"MỐC": "loat", "SOÁT": "soat", "GIỜ": "gio"}
        ok = True
        for ten in ARM:
            goi.clear()
            TG.DUNG_DICH_SOAT = (ten == "SOÁT")
            TG.DUNG_DICH_GIO = (ten == "GIỜ")
            TG.dich_hau_kiem(cau, "vi", "zh")
            dat = goi == [cho[ten]]
            ok = ok and dat
            print(f"  arm {ten:<5} -> gọi {goi or ['(KHÔNG GỌI GÌ)']}  "
                  f"{'ĐÚNG' if dat else 'SAI — mong ' + cho[ten]}")
        return ok
    finally:
        (TG._dich_loat, _D.dich_theo_gio, _D.dich_va_soat,
         TG._dich_nguoc_cham) = cu
        TG.DUNG_DICH_SOAT = TG.DUNG_DICH_GIO = False


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


def cham_mot_arm(ten: str, cau, goc_ma, ra_arm: dict, san: Path) -> dict:
    from app.ai import cham_dich as CD
    from app.core.thay_giong import con_chu_goc

    ban_dich = ra_arm["ban_dich"]
    goc = [c["text"] for c in cau]
    khung = [float(c["end"]) - float(c["start"]) for c in cau]

    cham = CD.cham_ban_dich(goc, ban_dich, goc_ma=goc_ma or "zh", dich_ma="vi")
    truc = {k: round(sum(float(c.get(k) or 0) for c in cham["cau"])
                     / max(1, len(cham["cau"])), 2)
            for k in ("nghia", "xuoi", "noi", "tron")}

    n = len(ban_dich)
    d = {
        "ten": ten, "n": n,
        "ty_le_dat": cham["ty_le_dat"],
        "diem_tb": cham["diem_tb"],
        "truc": truc,
        "cau_ngan": sum(1 for t in ban_dich if len(t) < CUT_KY_TU),
        "cau_dai": sum(1 for t in ban_dich if len(t) > DAI_KY_TU),
        "ky_tu_tb": round(sum(len(t) for t in ban_dich) / max(1, n), 1),
        "sot_chu_goc": sum(1 for t in ban_dich if con_chu_goc(t, "vi")),
        "giay": ra_arm["giay"],
        "luot_llm": ra_arm["luot_llm"],
    }

    doc = do_tts(ban_dich, san)
    d["tts_do_duoc"] = sum(1 for x in doc if x > 0)
    if any(x > 0 for x in doc):
        lech = [abs(doc[i] - khung[i]) for i in range(n) if doc[i] > 0]
        tran = [doc[i] - khung[i] for i in range(n)
                if doc[i] > 0 and doc[i] > khung[i]]
        d["lech_tuyet_doi_tb"] = round(sum(lech) / max(1, len(lech)), 3)
        d["tran_tong"] = round(sum(tran), 1)
        d["so_cau_tran"] = len(tran)
        d["tong_doc"] = round(sum(x for x in doc if x > 0), 2)
        d["tong_khung"] = round(sum(khung[i] for i in range(n) if doc[i] > 0), 2)
        d["ty_doc_khung"] = round(d["tong_doc"] / max(0.01, d["tong_khung"]), 3)
    return d


def in_arm(d: dict) -> None:
    print(f"  --- {d['ten']} ---")
    print(f"    ĐẠT theo thước       : {d['ty_le_dat']}%  (điểm TB {d['diem_tb']})")
    t = d["truc"]
    print(f"    4 trục TB            : nghia {t['nghia']} · xuoi {t['xuoi']} "
          f"· noi {t['noi']} · tron {t['tron']}")
    print(f"    còn chữ gốc (Hán)    : {d['sot_chu_goc']}/{d['n']}")
    print(f"    câu < {CUT_KY_TU} ký tự (cụt) : {d['cau_ngan']}/{d['n']}"
          f"  · câu > {DAI_KY_TU} ký tự (gộp): {d['cau_dai']}/{d['n']}")
    print(f"    ký tự/câu TB         : {d['ky_tu_tb']}")
    print(f"    GIÁ: {d['giay']}s wall · {d['luot_llm']} lượt LLM")
    if "lech_tuyet_doi_tb" in d:
        print("    THỜI GIAN ĐỌC (edge-tts thật, đã cắt lề im):")
        print(f"      tổng đọc {d['tong_doc']}s / tổng khung {d['tong_khung']}s"
              f"  ({d['ty_doc_khung']}x)")
        print(f"      lệch tuyệt đối TB {d['lech_tuyet_doi_tb']}s/câu")
        print(f"      TRÀN {d['tran_tong']}s · {d['so_cau_tran']} câu")


# --------------------------------------------------------------------------
def main() -> int:
    _quet_san_cu()
    cau, goc_ma = nap_corpus()
    print("=" * 74)
    print(f"A/B END-TO-END `dich_hau_kiem` — {len(cau)} câu · goc_ma={goc_ma!r} "
          f"· {SO_LUOT} lượt ĐAN XEN")
    print(f"TTS: {'BỎ QUA' if BO_TTS else 'edge-tts THẬT'}")
    print(f"ARM: {' · '.join(ARM)}")
    print("=" * 74)
    print("TỰ KIỂM ĐƯỜNG DỊCH (arm nào gọi đúng hàm nấy, 0 lượt LLM):")
    if not tu_kiem_duong():
        print("DỪNG: arm gọi SAI HÀM — mọi số đo sau đây sẽ vô nghĩa.")
        return 2
    print("=" * 74)

    tat_ca: list[dict] = []
    for luot in range(SO_LUOT):
        thu_tu = ARM[luot % len(ARM):] + ARM[:luot % len(ARM)]
        print()
        print("=" * 74)
        print(f"LƯỢT {luot + 1}  (thứ tự chạy: {' -> '.join(thu_tu)})")
        print("=" * 74)
        mot: dict[str, dict] = {}
        for ten in thu_tu:
            san = REPO / f"bq_dichsoat_{os.getpid()}_{luot}_{TEN_THU_MUC[ten]}"
            try:
                ra_arm = chay_arm(ten, cau, goc_ma)
                mot[ten] = cham_mot_arm(ten, cau, goc_ma, ra_arm, san)
                mot[ten]["ban_dich"] = ra_arm["ban_dich"]
            except Exception as e:                       # noqa: BLE001
                print(f"  --- {ten} --- LỖI: {type(e).__name__}: {e}")
                mot[ten] = {"ten": ten, "loi": f"{type(e).__name__}: {e}"}
            finally:
                shutil.rmtree(san, ignore_errors=True)
        for ten in ARM:
            if "loi" not in mot.get(ten, {"loi": 1}):
                in_arm(mot[ten])
        tat_ca.append(mot)
        RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    # ---- TỔNG KẾT: trung bình các lượt CHẠY ĐƯỢC ----
    print()
    print("=" * 74)
    print(f"TỔNG KẾT — trung bình {SO_LUOT} lượt")
    print("=" * 74)

    def tb(ten: str, khoa: str, sau: int = 2):
        v = [m[ten][khoa] for m in tat_ca
             if ten in m and khoa in m[ten] and m[ten].get(khoa) is not None]
        return round(sum(v) / len(v), sau) if v else None

    hang = [
        ("ĐẠT theo thước %", "ty_le_dat", 2),
        ("  điểm TB", "diem_tb", 2),
        ("còn chữ Hán", "sot_chu_goc", 2),
        ("câu < 20 ký tự (cụt)", "cau_ngan", 2),
        ("câu > 60 ký tự (gộp)", "cau_dai", 2),
        ("ký tự/câu TB", "ky_tu_tb", 1),
        ("lệch |s| / câu", "lech_tuyet_doi_tb", 3),
        ("TRÀN (đọc dài hơn)", "tran_tong", 1),
        ("tổng đọc / tổng khung", "ty_doc_khung", 3),
        ("GIÂY (wall)", "giay", 1),
        ("LƯỢT LLM", "luot_llm", 1),
    ]
    print(f"{'chỉ số (TB)':<24}|" + "|".join(f"{a:>12} " for a in ARM))
    print("-" * (25 + 14 * len(ARM)))
    for nhan, khoa, sau in hang:
        o = "|".join(f"{str(tb(a, khoa, sau)):>12} " for a in ARM)
        print(f"{nhan:<24}|{o}")
    for k in ("nghia", "xuoi", "noi", "tron"):
        v = []
        for ten in ARM:
            xs = [m[ten]["truc"][k] for m in tat_ca
                  if ten in m and "truc" in m[ten]]
            v.append(round(sum(xs) / len(xs), 2) if xs else None)
        o = "|".join(f"{str(x):>12} " for x in v)
        print(f"{'  trục ' + k:<24}|{o}")

    # ---- TỪNG LƯỢT (LLM không tiền định: trung bình che mất biến động) ----
    print()
    print("TỪNG LƯỢT — `dat_%` · sót Hán · cụt · lượt LLM")
    for i, m in enumerate(tat_ca):
        o = []
        for a in ARM:
            d = m.get(a) or {}
            if "loi" in d:
                o.append(f"{a}: LỖI")
            else:
                o.append(f"{a}: {d.get('ty_le_dat')}% · {d.get('sot_chu_goc')}"
                         f" · {d.get('cau_ngan')} · {d.get('luot_llm')}")
        print(f"  lượt {i + 1}: " + "   |   ".join(o))

    RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print()
    print(f"Ghi: {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
