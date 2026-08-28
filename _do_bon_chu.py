# -*- coding: utf-8 -*-
"""BỐN CHỮ — đo **LIỀN · NHANH · ĐỀU · ĐÚNG** CÙNG LÚC, 4 arm, trên đường THẬT.

Anh Hùng chốt bốn chữ: *"đọc LIỀN · NHANH · mà ĐỀU · mà ĐÚNG"*. Mọi lượt đo
trước chỉ nhìn MỘT hoặc HAI cột nên lượt nào cũng "thắng" — v2.49.0 khoe im
29,01 -> 16,73% mà giấu mất CV tốc độ đọc 15,87 -> 18,44%. File này bắt buộc
in **CẢ BỐN** cột cho **MỌI** arm.

**BỐN ARM** (`_do_viet_day.chung` lo phần dùng chung: dịch + 4a đọc + 4b rút
gọn, chạy ĐÚNG MỘT LƯỢT rồi cache — LLM và VieNeu đều KHÔNG tiền định nên
ghép cặp theo cấu tạo là cách DUY NHẤT so được):

    A  app hôm nay                       (4c keo=1,00)            — MỐC
    B  kéo chậm 1,15  (v2.49.0)          (4c keo=1,15)
    C  DỊCH ĐẦY       (bước 4b' mới)     (4b' -> 4c keo=1,00)
    D  DỊCH ĐẦY + đọc ĐỀU                (4b' -> BỎ 4c)

**HAI CỘT HÌNH, KHÔNG PHẢI MỘT — đọc kỹ chỗ này.** `khung_cho_phep` tính trên
TRỤC GỐC, còn `he_so_hinh_can` lấy tỉ số TRÀN LỚN NHẤT rồi giãn CẢ video. Nên
mỗi arm được đo ở CẢ HAI mục của combo "Khớp tiếng với hình":
    · **mục 1** (`hs = 1,0`, không chỉnh hình) — chỗ "viết đầy" ăn nhất;
    · **mục 2** (`hs = k_can` kẹp trần) — ĐÚNG cấu hình anh Hùng đang chạy,
      và là chỗ arm A ra ~29% im (đối chứng "thước CÓ RĂNG" của v2.49.0).
Gộp hai cột này làm một là đọc nhầm phép GIÃN HÌNH thành công của bản vá.

Cấu hình = ĐÚNG cấu hình anh Hùng (QSettings 28/08): `vnb:` · đích `vi` ·
`tach` · nhấn nhá BẬT.

    .venv\\Scripts\\python -u _do_bon_chu.py [ten...]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import sys
import time
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
import _do_viet_day as vd0                                  # noqa: E402
from _do_khop_video import _lech, im_giua_cau, toc_do_doc   # noqa: E402
from app.core import thay_giong as tg                       # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
LAM = REPO / "_do_bc_tam"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "bon_chu"
CACHE = REPO / "_do_bc_cache"
KQ = REPO / "_kq_bon_chu.json"
DICH_SANG = "vi"
NHAN_NHA = True
KEO_B = 1.15

#: Model CHẤM — phải KHÁC model DỊCH. Dùng lại đúng hằng số của bản vá để
#: bảng số và app không bao giờ chấm bằng hai model khác nhau.
MODEL_CHAM = tg.MODEL_CHAM_VIET_DAY

ARMS = os.environ.get("BQ_BC_ARM", "A,B,C,D").split(",")


def _tb(xs) -> float:
    return round(statistics.fmean(xs), 2) if xs else 0.0


# ==================================================================
# CỘT "ĐÚNG" — chấm bằng model KHÁC, có CACHE ra đĩa
# ==================================================================

def cham_dung(goc: list[str], dich: list[str], goc_ma: str) -> dict:
    """Điểm TRUNG THÀNH 1-5 + ĐẾM CÂU BỊA THÊM Ý, chấm bằng `MODEL_CHAM`.

    Cache theo BĂM của chính bộ chữ: arm A và B dùng CHUNG bộ chữ (chúng chỉ
    đổi tốc độ đọc, không đổi một chữ nào) nên chấm lại là vừa tốn lượt vừa
    đẻ ra hai con số khác nhau cho cùng một thứ.
    """
    from app.ai import llm
    CACHE.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(("|".join(dich) + MODEL_CHAM).encode("utf-8")).hexdigest()
    p = CACHE / f"dung_{h[:16]}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass

    chi = [i for i in range(len(dich))
           if str(dich[i]).strip() and str(goc[i]).strip()]
    gia = [{"text": f'{goc[i][:300]}\n{dich[i][:300]}'} for i in range(len(dich))]
    diem: dict[int, float] = {}
    bia: dict[int, bool] = {}
    for phan in tg.chia_me_dich(gia, chi, token_ra_moi_cau=16):
        items = [f'#{i}\n  GỐC ({tg._ten_nn(goc_ma)}): "{goc[i][:300]}"\n'
                 f'  BẢN DỊCH: "{dich[i][:300]}"' for i in phan]
        prompt = (
            "Với mỗi cặp dưới đây, chấm ĐỘ TRUNG THÀNH của bản dịch so với "
            "câu gốc, thang 1-5 (5 = đúng trọn nghĩa, không thừa không "
            "thiếu; 1 = sai hẳn hoặc bịa).\n"
            "Kèm `them`: bản dịch có THÊM thông tin KHÔNG CÓ trong câu gốc "
            "không (true/false) — chi tiết, tên, con số, suy diễn, bình luận "
            "mà câu gốc không hề nói.\n\n"
            f"{chr(10).join(items)}\n\n"
            f"Trả MẢNG JSON {len(phan)} đối tượng "
            '{"i": <đúng số sau dấu #>, "tt": <1-5>, "them": <true/false>}. '
            "BẮT BUỘC đủ MỌI số #.")
        try:
            data = llm.complete_json(
                prompt, system="Bạn chấm chất lượng dịch. Chỉ trả JSON.",
                model=MODEL_CHAM)
        except Exception as e:  # noqa: BLE001
            print(f"    (chấm mẻ {phan[0]}..{phan[-1]} hỏng: {type(e).__name__})")
            continue
        for o in tg._mang_llm(data):
            if not isinstance(o, dict):
                continue
            try:
                i = int(o.get("i"))
                t = float(o.get("tt"))
            except (TypeError, ValueError):
                continue
            if i in phan:
                diem[i] = t
                bia[i] = bool(o.get("them"))
    ra = {"diem_tb": _tb(list(diem.values())),
          "so_cau_cham": len(diem),
          "so_cau_duoi_4": sum(1 for v in diem.values() if v < 4),
          "so_cau_bia": sum(1 for v in bia.values() if v),
          "model": MODEL_CHAM,
          "_diem": {str(k): v for k, v in diem.items()}}
    p.write_text(json.dumps(ra, ensure_ascii=False), encoding="utf-8")
    return ra


# ==================================================================
# MỘT ARM
# ==================================================================

def mot_arm(ten: str, nhan: str, k: dict, rg: dict, keo: float, bo_4c: bool,
            lam: Path, tach: dict, voice: str, goc_ma: str) -> dict:
    """4b' (nếu có) -> 4c -> hệ số hình -> khớp (CẢ mục 1 lẫn mục 2) -> video."""
    lam.mkdir(parents=True, exist_ok=True)
    cau, tong = k["cau"], k["tong"]
    ra: dict = {"nhan": nhan, "keo": round(keo, 2), "bo_4c": bool(bo_4c)}

    t0 = time.time()
    if bo_4c:
        # PHẢI GIỐNG NHÁNH `_deu` TRONG `thay_giong_video` — dựng đúng dict đó
        # thay cho lời gọi 4c. Ai đổi một bên phải đổi cả bên kia.
        dn = {"files": list(rg["files"]), "ok": list(rg["ok"]),
              "moc_tu": rg.get("moc_tu"), "so_doc_lai": 0, "rate_max": 0,
              "so_doc_cham": 0, "so_cau_ngan": 0, "rate_am_min": 0}
    else:
        dn = tg.doc_nhanh_vua_khung(
            cau, rg["texts"], list(rg["files"]), list(rg["ok"]), tong,
            lam / "docnhanh", DICH_SANG, voice,
            moc_tu=list(rg.get("moc_tu") or []), nhan_nha=NHAN_NHA,
            keo_dai_toi_da=keo)
    ra["giay_4c"] = round(time.time() - t0, 1)
    ra.update({x: dn.get(x, 0) for x in
               ("so_doc_lai", "rate_max", "so_doc_cham", "so_cau_ngan",
                "rate_am_min")})

    _c = tg.he_so_hinh_can(cau, dn["files"], dn["ok"], tong)
    _tran = tg.tran_hinh_theo_fps(tg.do_fps(k["video"]))
    hs2 = max(1.0, min(float(_c["k_can"]), _tran))
    ra.update({"k_can": _c["k_can"], "he_so_hinh": round(hs2, 4),
               "cham_tran": float(_c["k_can"]) > _tran + 1e-6})

    # ---- MỤC 1 (hs = 1,0): KHÔNG trộn, KHÔNG dựng video — chỉ đo mốc tiếng.
    kh1 = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop1",
                            moc_tu=dn.get("moc_tu"), he_so_hinh=1.0,
                            keo_dai_toi_da=keo)
    ra["muc1"] = _bon_cot(kh1, rg["texts"], cau, tong)
    ra["muc1"]["tempo_max"] = kh1["tempo_max"]
    ra["muc1"]["chong_lan_ms_max"] = kh1["chong_lan_ms_max"]

    # ---- MỤC 2 (hs = k_can, ĐÚNG cấu hình anh Hùng): trộn + dựng VIDEO thật.
    tong_ra = tong * hs2
    kh2 = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop2",
                            moc_tu=dn.get("moc_tu"), he_so_hinh=hs2,
                            keo_dai_toi_da=keo)
    ra["muc2"] = _bon_cot(kh2, rg["texts"], cau, tong_ra)
    ra["muc2"]["tempo_max"] = kh2["tempo_max"]
    ra["muc2"]["chong_lan_ms_max"] = kh2["chong_lan_ms_max"]

    nhac = tach["nhac"]
    if hs2 > 1.0 + 1e-6:
        nh = lam / "nhac_gian.wav"
        tg._ffmpeg(["-i", str(nhac), "-af",
                    f"{tg._co_gian_chuoi(1.0 / hs2)},aresample={tg.SR_TACH},"
                    f"apad,atrim=0:{tong_ra:.3f},asetpts=N/SR/TB",
                    "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                    str(nh)], "giãn lớp nhạc theo hệ số hình")
        nhac = str(nh)
    # KHÔNG `bu_giong_goc` — v2.48.0 đã bỏ hẳn ở cách trộn "tách nhạc".
    au = tg.tron_thay_giong(nhac, list(kh2["manh"]), tong_ra,
                            lam / "tieng.wav", goc_wav=k["wav"])
    dong_chu = tg.dong_chu_theo_giong(kh2.get("moc_tieng") or [], rg["texts"],
                                      moc_tu=kh2.get("moc_tu"))
    vid = lam / f"{nhan}_{ten}.mp4"
    tg.thay_audio_video(k["video"], au["ra"], vid, che_chu=False,
                        dong_chu=dong_chu, he_so_hinh=hs2)
    # ĐỘ TO đo trên FILE THÀNH PHẨM bằng lượt `loudnorm` RIÊNG (không đọc lại
    # số mà `chuan_do_to` tự khai trong lúc trộn — đó là tự chấm điểm mình).
    do_to = tg.do_do_to(vid)
    ra["lufs_I"] = round(do_to.get("I", 0.0), 2)
    ra["lufs_TP"] = round(do_to.get("TP", 0.0), 2)
    ra["do_dai_ra"] = round(tong_ra, 3)
    ra["kiem_video_ra"] = tg.kiem_video_ra(vid, tong_ra)
    ra["ra"] = str(vid)
    ra["_texts"] = list(rg["texts"])
    return ra


def _bon_cot(kh: dict, texts: list[str], cau: list[dict],
             tong_ra: float) -> dict:
    """Ba cột đo được từ mốc tiếng (LIỀN · NHANH · ĐỀU). Cột ĐÚNG chấm riêng."""
    moc = kh.get("moc_tieng") or []
    ig = im_giua_cau(moc, tong_ra)
    td = toc_do_doc(texts, moc, cau)
    tb, sd, cv = _lech(td)
    return {
        # LIỀN
        "im_pt": ig["im_giua_pt"], "im_so_05": ig["im_giua_so_05"],
        "im_dai_nhat": ig["im_giua_dai_nhat"], "im_tong": ig["im_giua_tong"],
        "ti_le_co_tieng": ig["ti_le_co_tieng"],
        # NHANH + ĐỀU
        "kytu_giay_tb": round(tb, 2), "kytu_giay_sd": round(sd, 3),
        "kytu_giay_cv": round(cv, 2), "kytu_giay_n": len(td),
    }


def mot_giong(ten: str, nhan_g: str, voice_ma: str) -> dict | None:
    k = kho.chuan_bi(ten)
    c = vd0.chung(ten, nhan_g, voice_ma)
    c["k"] = k
    voice = c["voice_that"]
    goc_ma = (k["chep"].get("language") or "")[:2].lower()

    tach_dir = kho.LAM / ten / "tach_kv"
    nhac, giong = tach_dir / "nhac.wav", tach_dir / "giong.wav"
    if not (nhac.exists() and giong.exists()):
        print("  tách giọng bằng Demucs (lần đầu, sẽ cache)...")
        tach_dir.mkdir(parents=True, exist_ok=True)
        t = tg.tach_giong(k["wav"], tach_dir / "raw", cach="demucs")
        shutil.copy2(t["nhac"], nhac)
        shutil.copy2(t["giong"], giong)
    tach = {"nhac": str(nhac), "giong": str(giong)}

    rg = {"texts": c["rg_texts"], "files": c["rg_files"], "ok": c["rg_ok"],
          "moc_tu": c["rg_moc_tu"]}
    lam0 = LAM / ten / f"g_{nhan_g}"
    print(f"\n{'=' * 74}\n=== {ten} · {nhan_g} ({voice}) · {len(k['cau'])} câu "
          f"· {k['tong']:.2f}s ===")

    # ---- BƯỚC 4b' chạy ĐÚNG MỘT LƯỢT, dùng chung cho arm C và D ----
    vdr = None
    rg_day = rg
    if "C" in ARMS or "D" in ARMS:
        t0 = time.time()
        vdk = tg.viet_day_vua_khung(
            k["cau"], rg["texts"], rg["files"], rg["ok"], k["tong"],
            lam0 / "vietday", DICH_SANG, goc_ma, voice,
            moc_tu=rg.get("moc_tu"), nhan_nha=NHAN_NHA)
        vdr = {x: vdk[x] for x in vdk if x not in
               ("texts", "files", "ok", "moc_tu")}
        vdr["giay"] = round(time.time() - t0, 1)
        rg_day = {"texts": vdk["texts"], "files": vdk["files"],
                  "ok": vdk["ok"], "moc_tu": vdk["moc_tu"]}
        print(f"  4b' VIẾT ĐẦY: {vdk['so_cau_hut']} câu hụt -> xin "
              f"{vdk['so_xin']} -> LLM đổi chữ {vdk['so_doi_chu']} -> NHẬN "
              f"{vdk['so_sua']}\n"
              f"       bỏ: nghĩa TỤT {vdk['so_bo_vi_nghia']} · KHÔNG chấm "
              f"được {vdk['so_bo_vi_khong_cham']} · đọc không dài hơn "
              f"{vdk['so_bo_vi_ngan']} · tràn khung {vdk['so_bo_vi_tran']}\n"
              f"       điểm cũ {vdk['diem_cu_tb']} -> mới {vdk['diem_moi_tb']}"
              f" · hụt {vdk['hut_truoc_giay']}s -> {vdk['hut_sau_giay']}s"
              f" · +{vdk['them_kytu']} kt · {vdk['so_lan_llm']} lượt LLM"
              f" · {vdr['giay']}s")

    cong_thuc = {"A": (rg, 1.0, False), "B": (rg, KEO_B, False),
                 "C": (rg_day, 1.0, False), "D": (rg_day, 1.0, True)}
    arms = []
    for nhan in ARMS:
        nguon, keo, bo = cong_thuc[nhan]
        try:
            a = mot_arm(ten, nhan, k, nguon, keo, bo, lam0 / nhan, tach,
                        voice, goc_ma)
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"!!! arm {nhan} HỎNG: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        # ---- CỘT ĐÚNG ----
        a["dung"] = cham_dung([str(x.get("text") or "") for x in k["cau"]],
                              a.pop("_texts"), goc_ma)
        arms.append(a)
        m1, m2 = a["muc1"], a["muc2"]
        print(f"  {nhan} | mục1 im {m1['im_pt']:>6.2f}% · mục2 im "
              f"{m2['im_pt']:>6.2f}% | {m2['kytu_giay_tb']:>5.2f} kt/s | "
              f"CV {m2['kytu_giay_cv']:>5.2f}% | ĐÚNG "
              f"{a['dung']['diem_tb']:.2f}/5 (bịa {a['dung']['so_cau_bia']})")

    # ---- FILE NGHE THỬ: VIDEO, 4 arm CÙNG một lượt chạy ----
    out = NGHE / ten / nhan_g
    out.mkdir(parents=True, exist_ok=True)
    for a in arms:
        p = Path(a["ra"])
        if not p.exists():
            continue
        m2 = a["muc2"]
        # Tên kèm CẢ BỐN SỐ — nghe mà không có số thì không nối lại được với
        # bảng, và bốn chữ thì phải thấy đủ bốn.
        ten_moi = (f"{a['nhan']}_im{m2['im_pt']:.1f}pt"
                   f"_{m2['kytu_giay_tb']:.1f}kts"
                   f"_cv{m2['kytu_giay_cv']:.1f}"
                   f"_dung{a['dung']['diem_tb']:.2f}_{ten}.mp4"
                   ).replace(".", ",").replace(",mp4", ".mp4")
        shutil.copy2(p, out / ten_moi)
        a["nghe_thu"] = str(out / ten_moi)
        a["md5"] = hashlib.md5((out / ten_moi).read_bytes()).hexdigest()[:16]
    return {"ten": ten, "giong": nhan_g, "voice_that": voice,
            "so_cau": len(k["cau"]), "do_dai_goc": round(k["tong"], 2),
            "viet_day": vdr, "arms": arms}


def in_bang(rs: list[dict]) -> None:
    print(f"\n\n{'=' * 108}\nBẢNG 4 CỘT × 4 ARM — GHÉP CẶP (mọi arm dùng chung "
          f"bản dịch + bộ file giọng gốc)\n{'=' * 108}")
    for r in rs:
        print(f"\n### {r['ten']} · {r['giong']} ({r['voice_that']}) · "
              f"{r['so_cau']} câu · {r['do_dai_goc']}s")
        if r.get("viet_day"):
            v = r["viet_day"]
            print(f"    4b' viết đầy: hụt {v['so_cau_hut']} câu -> xin "
                  f"{v['so_xin']} -> NHẬN {v['so_sua']} · hụt "
                  f"{v['hut_truoc_giay']}s -> {v['hut_sau_giay']}s · "
                  f"+{v['them_kytu']} kt · {v['so_lan_llm']} lượt LLM")
        for muc in ("muc1", "muc2"):
            ten_muc = ("MỤC 1 — không chỉnh hình" if muc == "muc1"
                       else "MỤC 2 — chỉnh video theo giọng (cấu hình anh Hùng)")
            print(f"    {ten_muc}")
            print(f"      {'arm':>3} | {'LIỀN im%':>8} {'>=0,5s':>7} "
                  f"{'dài nhất':>9} | {'NHANH kt/s':>10} | {'ĐỀU CV%':>8} | "
                  f"{'ĐÚNG /5':>8} {'bịa':>4} {'<4đ':>4} | {'tempo':>6} "
                  f"{'chồng':>6} | {'k hình':>7}")
            for a in r["arms"]:
                m = a[muc]
                d = a["dung"]
                print(f"      {a['nhan']:>3} | {m['im_pt']:>8.2f} "
                      f"{m['im_so_05']:>7} {m['im_dai_nhat']:>9.2f} | "
                      f"{m['kytu_giay_tb']:>10.2f} | {m['kytu_giay_cv']:>8.2f} | "
                      f"{d['diem_tb']:>8.2f} {d['so_cau_bia']:>4} "
                      f"{d['so_cau_duoi_4']:>4} | {m['tempo_max']:>6.3f} "
                      f"{m['chong_lan_ms_max']:>6.1f} | "
                      f"{a['he_so_hinh'] if muc == 'muc2' else 1.0:>7.4f}")
        print("    độ to file thành phẩm (loudnorm chạy RIÊNG): " + " · ".join(
            f"{a['nhan']} {a['lufs_I']:.2f} LUFS / {a['lufs_TP']:.2f} dBTP"
            for a in r["arms"]))
        print("    MD5 file nghe thử: " + " · ".join(
            f"{a['nhan']} {a.get('md5', '-')}" for a in r["arms"]))


def main() -> int:
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    tens = [a for a in sys.argv[1:] if not a.startswith("-")] or ["lt1", "lt2"]
    giongs = [g for g in vd0.GIONG
              if g[0] in os.environ.get("BQ_BC_GIONG", "VNB,EDGE").split(",")]
    print(f"ARM {ARMS} · GIỌNG {[g[0] for g in giongs]} · đích {DICH_SANG} · "
          f"nhấn nhá {NHAN_NHA} · model chấm {MODEL_CHAM}")
    tat: list[dict] = []
    for ten in tens:
        for nhan_g, ma in giongs:
            try:
                r = mot_giong(ten, nhan_g, ma)
            except Exception as e:  # noqa: BLE001
                import traceback
                print(f"!!! {ten}/{nhan_g}: {type(e).__name__}: {e}")
                traceback.print_exc()
                continue
            if r:
                tat.append(r)
                KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    if not tat:
        return 1
    in_bang(tat)
    print(f"\nGhi: {KQ.name} · nghe thử: {NGHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
