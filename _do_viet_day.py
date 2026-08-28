# -*- coding: utf-8 -*-
"""VIỆC 0 — ĐO BÀI TOÁN "DỊCH ĐẦY" TRƯỚC KHI VIẾT MỘT DÒNG MÃ NÀO.

Anh Hùng chốt bốn chữ: **đọc LIỀN · NHANH · mà ĐỀU · mà ĐÚNG**. Chúng đá nhau
theo SỐ HỌC: tiếng đọc xong sớm hơn khung phim -> dư chỗ trống -> muốn LIỀN thì
phải lấp. Ba cách: đọc chậm lại (mất NHANH + mất ĐỀU — đã đo ở v2.49.0), cắt
video (mất nội dung), hoặc **DỊCH ĐẦY HƠN** (cùng nghĩa, viết đủ câu).

File này KHÔNG sửa app. Nó trả lời ĐÚNG MỘT câu hỏi:

    Phần HỤT KHUNG có nằm trong tầm "viết đủ ý hơn" không, hay nó đòi BỊA
    thêm nội dung?

**KHUNG ĐO TRÊN TRỤC GỐC, KHÔNG PHỤ THUỘC "CHỈNH HÌNH".** `khung_cho_phep(cau,
i, tong)` chỉ đọc `cau` và `tong` của bản GỐC; `he_so_hinh` được nhân vào SAU,
trong `khop_thoi_gian`. Nên con số hụt ở đây đúng cho CẢ mục 1 lẫn mục 2 của
combo "Khớp tiếng với hình" — chỉnh hình chỉ phóng to phần trống đó lên `k`
lần chứ không đẻ ra nó.

**GHÉP CẶP THEO CẤU TẠO.** Bước dùng chung (dịch + 4a đọc + 4b rút gọn) chạy
ĐÚNG MỘT LƯỢT cho mỗi (video, giọng) rồi cache ra đĩa; mọi arm của VIỆC 2 sau
này nạp lại đúng bộ đó. LLM và VieNeu đều KHÔNG tiền định (CLAUDE.md: cùng mã
cùng video hai lượt lệch 1,81 lần) nên đây là cách DUY NHẤT so được.

Cấu hình = ĐÚNG cấu hình anh Hùng (QSettings 28/08): `vnb:` · đích `vi` ·
`tach` · nhấn nhá BẬT.

    .venv\\Scripts\\python -u _do_viet_day.py [ten...]
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _do_kho_tg as kho                                    # noqa: E402
from app.core import thay_giong as tg                       # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
LAM = REPO / "_do_vd_tam"
KQ = REPO / "_kq_viet_day.json"
DICH_SANG = "vi"
NHAN_NHA = True

_MAU_VNB = (Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo"
            / "_mau_giong" / "test.wav")

#: `VNB` = ĐÚNG đường anh Hùng đi. `EDGE` = TRẦN đối chứng (máy đọc có `rate`
#: thật, tiền định) — bảng nào chỉ có một cột thì không đọc được gì.
GIONG: list[tuple[str, str]] = []
if os.environ.get("BQ_VD_VNB", "1") != "0" and _MAU_VNB.exists():
    GIONG.append(("VNB", f"vnb:{_MAU_VNB}"))
if os.environ.get("BQ_VD_EDGE", "1") != "0":
    GIONG.append(("EDGE", ""))

#: Ngưỡng coi là HỤT — dùng lại ĐÚNG `NGUONG_DOC_NHANH` của app (1,03) theo
#: chiều ngược, vì đó chính là ngưỡng bước 4c dùng để quyết "có đọc lại không".
#: Đặt một số mới ở đây là đo một đường mã không tồn tại.
NGUONG_HUT = tg.NGUONG_DOC_NHANH

#: Bậc thang phân bố phần hụt (giây).
BAC = (0.0, 0.3, 0.5, 1.0, 2.0, 3.0)


def _pt(x: float, mau: float) -> float:
    return round(100.0 * x / mau, 2) if mau else 0.0


# ==================================================================
# BƯỚC DÙNG CHUNG — chạy MỘT LƯỢT rồi cache
# ==================================================================

def chung(ten: str, nhan_g: str, voice_ma: str) -> dict:
    """dịch -> 4a đọc -> 4b rút gọn. Có cache ra đĩa (file giọng vẫn nằm đó)."""
    lam = LAM / ten / f"g_{nhan_g}"
    lam.mkdir(parents=True, exist_ok=True)
    cache = lam / "chung.json"

    k = kho.chuan_bi(ten)
    if cache.exists():
        try:
            c = json.loads(cache.read_text(encoding="utf-8"))
            # File giọng phải CÒN TRÊN ĐĨA thì cache mới dùng được — thiếu một
            # file là mọi phép đo dưới đây đọc `probe_duration` = 0 rồi im lặng
            # ra bảng số trông vẫn hợp lý (đúng họ "phép đo hỏng phát chứng
            # nhận"). Kiểm ĐỦ, không kiểm mẫu.
            fs = [p for p, o in zip(c["rg_files"], c["rg_ok"]) if o]
            if fs and all(Path(p).exists() for p in fs):
                print(f"  [{ten}/{nhan_g}] dùng lại bộ dùng chung đã cache "
                      f"({len(fs)} file giọng)")
                c["k"] = k
                return c
            print(f"  [{ten}/{nhan_g}] cache có mà THIẾU file giọng -> chạy lại")
        except Exception as e:                              # noqa: BLE001
            print(f"  [{ten}/{nhan_g}] cache hỏng ({type(e).__name__}) -> chạy lại")

    goc_ma = (k["chep"].get("language") or "")[:2].lower()
    print(f"  [{ten}] {k['tong']:.2f}s · {len(k['cau'])} câu · "
          f"{goc_ma} -> {DICH_SANG}")
    dd = tg.dich_hau_kiem(k["cau"], DICH_SANG, goc_ma)
    tts = tg.doc_ban_dich(dd["ban_dich"], lam / "tts", voice_ma, DICH_SANG,
                          nhan_nha=NHAN_NHA)
    rg = tg.rut_gon_vua_khung(k["cau"], dd["ban_dich"], tts, k["tong"],
                              lam / "rutgon", DICH_SANG, tts["voice"],
                              nhan_nha=NHAN_NHA)
    print(f"  [{ten}/{nhan_g}] giọng thật {tts['voice']} · "
          f"rút gọn {rg['so_sua']} câu · TTS hỏng {tts['so_hong']}")
    c = {
        "ten": ten, "giong": nhan_g, "giong_ma": voice_ma,
        "voice_that": tts["voice"],
        "ban_dich": list(dd["ban_dich"]),
        "rg_texts": list(rg["texts"]),
        "rg_files": [str(p) for p in rg["files"]],
        "rg_ok": [bool(x) for x in rg["ok"]],
        "rg_moc_tu": rg.get("moc_tu") or [],
        "rg_so_sua": rg["so_sua"],
        "tts_so_hong": tts["so_hong"],
    }
    cache.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    c["k"] = k
    return c


# ==================================================================
# VIỆC 0 — PHÂN BỐ HỤT KHUNG
# ==================================================================

def do_hut(c: dict) -> dict:
    """Đo TỪNG CÂU: khung cho phép vs độ dài tiếng THẬT sau bước 4b."""
    k = c["k"]
    cau, tong = k["cau"], k["tong"]
    texts, files, ok = c["rg_texts"], c["rg_files"], c["rg_ok"]

    # ký tự/giây ĐO ĐƯỢC của CHÍNH giọng này trên CHÍNH lượt đọc này — không
    # dùng hằng số, đúng luật `toc_do_doc` của app.
    kts = tg.toc_do_doc(texts, files, ok)

    rows = []
    for i in range(len(cau)):
        if i >= len(files) or not ok[i] or not Path(files[i]).exists():
            continue
        d = tg.probe_duration(files[i])
        if d <= 0:
            continue
        khung = tg.khung_cho_phep(cau, i, tong)
        n = len((texts[i] if i < len(texts) else "").strip())
        n_goc = len((cau[i].get("text") or "").strip())
        hut = khung - d                       # >0 = HỤT, <0 = TRÀN
        rows.append({
            "i": i, "khung": round(khung, 3), "d": round(d, 3),
            "hut": round(hut, 3),
            "ty_le_khung": round(d / khung, 4) if khung > 0 else 0.0,
            "keo_can": round(khung / d, 4) if d > 0 else 1.0,
            "n_ky_tu": n, "n_ky_tu_goc": n_goc,
            # Ký tự phải THÊM để lấp đúng phần hụt, theo tốc độ đọc ĐO ĐƯỢC.
            "them_kt": int(round(max(0.0, hut) * kts)),
            "text": (texts[i] if i < len(texts) else "")[:200],
            "goc": (cau[i].get("text") or "")[:200],
        })

    n = len(rows)
    hut_r = [r for r in rows if r["keo_can"] > NGUONG_HUT]
    tran_r = [r for r in rows if r["ty_le_khung"] > 1.0]
    tran_rg = [r for r in rows if r["ty_le_khung"] > tg.NGUONG_RUT_GON]

    tong_hut = sum(r["hut"] for r in hut_r)
    tong_them = sum(r["them_kt"] for r in hut_r)
    tong_kt = sum(r["n_ky_tu"] for r in rows)
    tong_kt_goc = sum(r["n_ky_tu_goc"] for r in rows)

    # PHÂN BỐ: vài câu hụt nhiều hay mọi câu hụt ít?
    bac = {}
    for a, b in zip(BAC, list(BAC[1:]) + [9e9]):
        sel = [r for r in hut_r if a <= r["hut"] < b]
        bac[f"{a:.1f}-{b:.1f}" if b < 9e8 else f">={a:.1f}"] = {
            "so_cau": len(sel), "giay": round(sum(x["hut"] for x in sel), 2),
            "them_kt": sum(x["them_kt"] for x in sel)}

    # KHẢ THI hay BỊA — chấm theo TỈ LỆ ký tự phải thêm cho TỪNG câu.
    # "Viết đủ ý" nghĩa là bỏ bớt rút gọn, viết lại trạng ngữ ĐÃ CÓ trong câu
    # nguồn. Cùng một ý mà phải viết dài gấp rưỡi trở lên thì không còn chỗ nào
    # trong câu nguồn để lấy chữ — đó là BỊA.
    def _nhom(r: dict) -> str:
        if r["n_ky_tu"] <= 0:
            return "bia"
        t = r["them_kt"] / r["n_ky_tu"]
        if t <= 0.25:
            return "de"          # thêm <= 25% chữ: viết đủ câu là xong
        if t <= 0.60:
            return "kho"         # 25-60%: phải viết rất đầy, còn trong tầm
        return "bia"             # > 60%: không có chữ ở đâu mà lấy

    nh = {"de": [], "kho": [], "bia": []}
    for r in hut_r:
        nh[_nhom(r)].append(r)

    return {
        "ten": c["ten"], "giong": c["giong"], "voice_that": c["voice_that"],
        "tong_giay": round(tong, 2), "so_cau_do": n,
        "kytu_giay_do": round(kts, 2),
        "tong_ky_tu_dich": tong_kt, "tong_ky_tu_nguon": tong_kt_goc,
        "no_ngan_nguon": round(tong_kt / tong_kt_goc, 3) if tong_kt_goc else 0.0,
        # ---- HỤT ----
        "so_cau_hut": len(hut_r), "pt_cau_hut": _pt(len(hut_r), n),
        "hut_giay_tong": round(tong_hut, 2),
        "hut_pt_video": _pt(tong_hut, tong),
        "hut_giay_tb": round(tong_hut / len(hut_r), 3) if hut_r else 0.0,
        "hut_giay_trung_vi": round(
            statistics.median([r["hut"] for r in hut_r]), 3) if hut_r else 0.0,
        "hut_giay_max": round(max([r["hut"] for r in hut_r]), 3) if hut_r else 0.0,
        "bac_hut": bac,
        # ---- TRÀN ----
        "so_cau_tran": len(tran_r), "pt_cau_tran": _pt(len(tran_r), n),
        "so_cau_tran_rut_gon": len(tran_rg),
        "tran_giay_tong": round(sum(-r["hut"] for r in tran_r), 2),
        # ---- CHỮ PHẢI THÊM ----
        "them_kt_tong": tong_them,
        "them_ty_le": round(tong_them / tong_kt, 4) if tong_kt else 0.0,
        "so_lan_ban_dich": round(
            (tong_kt + tong_them) / tong_kt, 3) if tong_kt else 0.0,
        # ---- CHỐT KHẢ THI ----
        "kha_thi": {
            k2: {"so_cau": len(v),
                 "giay": round(sum(r["hut"] for r in v), 2),
                 "them_kt": sum(r["them_kt"] for r in v)}
            for k2, v in nh.items()},
        "_rows": rows,
    }


def in_mot(d: dict) -> None:
    print(f"\n{'=' * 86}\n### {d['ten']} · {d['giong']} ({d['voice_that']}) · "
          f"{d['tong_giay']}s · {d['so_cau_do']} câu đo được")
    print(f"    tốc độ đọc ĐO ĐƯỢC {d['kytu_giay_do']} ký tự/giây · "
          f"bản dịch {d['tong_ky_tu_dich']} kt / nguồn {d['tong_ky_tu_nguon']} kt"
          f" = {d['no_ngan_nguon']}x")
    print(f"    HỤT KHUNG : {d['so_cau_hut']:>3} câu ({d['pt_cau_hut']}%) · "
          f"tổng {d['hut_giay_tong']}s ({d['hut_pt_video']}% video) · "
          f"TB {d['hut_giay_tb']}s · trung vị {d['hut_giay_trung_vi']}s · "
          f"max {d['hut_giay_max']}s")
    print(f"    TRÀN KHUNG: {d['so_cau_tran']:>3} câu ({d['pt_cau_tran']}%) · "
          f"trong đó {d['so_cau_tran_rut_gon']} câu vượt ngưỡng rút gọn "
          f"{tg.NGUONG_RUT_GON} · tổng {d['tran_giay_tong']}s")
    print(f"    CẦN THÊM  : {d['them_kt_tong']} ký tự = "
          f"+{d['them_ty_le'] * 100:.1f}% -> bản dịch dài gấp "
          f"{d['so_lan_ban_dich']}x")
    print("    phân bố phần hụt:")
    for k2, v in d["bac_hut"].items():
        if v["so_cau"]:
            print(f"      {k2:>9} s : {v['so_cau']:>3} câu · {v['giay']:>6.2f}s"
                  f" · thêm {v['them_kt']:>4} kt")
    kt = d["kha_thi"]
    print("    CHỐT KHẢ THI (theo % chữ phải thêm cho TỪNG câu):")
    print(f"      DỄ   (<=25% chữ): {kt['de']['so_cau']:>3} câu · "
          f"{kt['de']['giay']:>6.2f}s · {kt['de']['them_kt']:>4} kt")
    print(f"      KHÓ  (25-60%)   : {kt['kho']['so_cau']:>3} câu · "
          f"{kt['kho']['giay']:>6.2f}s · {kt['kho']['them_kt']:>4} kt")
    print(f"      BỊA  (>60%)     : {kt['bia']['so_cau']:>3} câu · "
          f"{kt['bia']['giay']:>6.2f}s · {kt['bia']['them_kt']:>4} kt")


def main() -> int:
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    tens = [a for a in sys.argv[1:] if not a.startswith("-")] or ["lt1", "lt2"]
    print(f"VIỆC 0 · GIỌNG {[g[0] for g in GIONG]} · đích {DICH_SANG} · "
          f"nhấn nhá {NHAN_NHA} · ngưỡng hụt {NGUONG_HUT}")
    tat: list[dict] = []
    for ten in tens:
        for nhan_g, ma in GIONG:
            try:
                c = chung(ten, nhan_g, ma)
                d = do_hut(c)
            except Exception as e:                          # noqa: BLE001
                import traceback
                print(f"!!! {ten}/{nhan_g}: {type(e).__name__}: {e}")
                traceback.print_exc()
                continue
            in_mot(d)
            tat.append(d)
            KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    if not tat:
        return 1

    print(f"\n\n{'=' * 86}\nTỔNG — mọi video, mọi giọng\n{'=' * 86}")
    print(f"  {'video/giọng':>12} | {'% câu hụt':>9} {'giây hụt':>9} "
          f"{'% video':>8} | {'câu tràn':>8} | {'+kt':>6} {'gấp':>6} | "
          f"{'DỄ':>4} {'KHÓ':>4} {'BỊA':>4}")
    for d in tat:
        kt = d["kha_thi"]
        print(f"  {d['ten'] + '/' + d['giong']:>12} | {d['pt_cau_hut']:>9.2f} "
              f"{d['hut_giay_tong']:>9.2f} {d['hut_pt_video']:>8.2f} | "
              f"{d['so_cau_tran']:>8} | {d['them_kt_tong']:>6} "
              f"{d['so_lan_ban_dich']:>6.3f} | {kt['de']['so_cau']:>4} "
              f"{kt['kho']['so_cau']:>4} {kt['bia']['so_cau']:>4}")
    print(f"\nGhi: {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
