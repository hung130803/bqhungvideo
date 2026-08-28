# -*- coding: utf-8 -*-
"""ĐO TRÊN ĐƯỜNG **THẬT** — KÉO DÀI GIỌNG CHO ĐẦY KHUNG (v2.49.0).

`_do_doc_cham.py` là phép MÔ PHỎNG: nó lấy bộ file giọng đã cache rồi tự co
giãn bằng `rubberband`. File này chạy **CHÍNH ĐƯỜNG MÃ CỦA APP** — bước 4c
`doc_nhanh_vua_khung(keo_dai_toi_da=)` (đọc CHẬM bằng `rate` âm) rồi bước 5
`khop_thoi_gian(keo_dai_toi_da=)` (kéo giãn phần dư) — nên số ra là số anh Hùng
sẽ nghe, không phải số của một đường mã song song.

**GHÉP CẶP LÀ BẮT BUỘC.** LLM + VieNeu đều KHÔNG tiền định (CLAUDE.md: cùng mã
cùng video hai lượt lệch **1,81 lần**). Nên script chạy dây chuyền **MỘT LƯỢT
cho mỗi (video, giọng)** tới hết bước 4b rồi TÁCH arm ở **đúng chỗ cờ tác
động**: mọi arm dùng CHUNG bản tách / chép lời / dịch / rút gọn / bộ file giọng
gốc. Mọi nhiễu bị triệt tiêu THEO CẤU TẠO.

**NĂM CỘT ĐO** (đọc kỹ cột 2 và 3 — ba hướng trước chết đúng ở đó):
  1. **% im giữa câu + số quãng >= 0,5 s** — `_do_khop_video.im_giua_cau`.
  2. **TRÔI tiếng-hình** = `lệch_đầu(arm) − lệch_đầu(arm TẮT)` TỪNG CÂU.
     **KHÔNG so mốc tuyệt đối `t_a`**: hai arm có thể có `he_so_hinh` khác nhau
     nên mốc danh nghĩa `a = start*hs` vốn đã khác — so thẳng là đọc phép GIÃN
     HÌNH thành "trôi". Trừ `a` đi thì cột này độc lập với `hs`.
  3. **LỆCH CHỮ-TIẾNG** = mốc TỪNG CHỮ so với mốc NÓI THẬT của chính câu đó
     (`moc_tu[0][0]` vs `t_a`, `moc_tu[-1][1]` vs `t_b`). Hai nguồn ĐỘC LẬP:
     mốc chữ do máy đọc trả rồi nhân `ty_le`, mốc nói do `silencedetect` đo
     trên file ĐÃ GHI. `ty_le` sai là cột này lộ ngay.
  4. **MÉO PHỔ** — `_do_khop_video.meo_pho` (log-mel, vòng tròn `k` rồi `1/k`),
     cùng thước với mốc CLAUDE.md (`atempo` 5,357 dB ở 1,20).
  5. **TRẢI TỐC ĐỘ ĐỌC (CV)** — anh Hùng cũng kêu *"lúc nhanh lúc chậm"*, và
     kéo chậm có thể làm CV tốt lên HOẶC xấu đi. Kèm **SÀN ĐỐI CHỨNG** đo trên
     file TTS THÔ (dùng chung mọi arm) — không có sàn thì con số CV vô nghĩa.

Cấu hình = ĐÚNG cấu hình anh Hùng (đọc từ QSettings 28/08): `vnb:` · đích `vi`
· `tach` · chỉnh hình BẬT · nhấn nhá BẬT.

    .venv\\Scripts\\python -u _do_cham_that.py [ten...]
"""
from __future__ import annotations

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

import _do_kho_tg as kho                                  # noqa: E402
from _do_khop_video import _lech, im_giua_cau, meo_pho, toc_do_doc  # noqa: E402
from app.core import thay_giong as tg                     # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
LAM = REPO / "_do_ct_tam"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "doc_cham"
KQ = REPO / "_kq_cham_that.json"
DICH_SANG = "vi"
NHAN_NHA = True

#: MỨC KÉO — `1.00` LUÔN ĐỨNG ĐẦU = arm TẮT = đối chứng ghép cặp.
MUC = tuple(float(x) for x in
            (os.environ.get("BQ_CT_MUC") or "1.00,1.15,1.25").split(","))

_MAU_VNB = (Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo"
            / "_mau_giong" / "test.wav")
#: `vnb:` = ĐÚNG đường anh Hùng đi (máy đọc KHÔNG thực thi `rate` thật ->
#: đường LÙI `rubberband`). `EDGE` = máy đọc CÓ `rate` thật -> đường méo = 0.
#: Phải có CẢ HAI thì câu hỏi *"máy đọc không có `rate` thì đi đường nào"* mới
#: có số, chứ không phải một lời khai.
GIONG: list[tuple[str, str]] = []
if os.environ.get("BQ_CT_VNB", "1") != "0" and _MAU_VNB.exists():
    GIONG.append(("VNB", f"vnb:{_MAU_VNB}"))
if os.environ.get("BQ_CT_EDGE", "1") != "0":
    GIONG.append(("EDGE", ""))


def _tb(xs: list[float]) -> float:
    return round(statistics.fmean(xs), 1) if xs else 0.0


def lech_dau_tung_cau(moc: list, cau: list[dict], hs: float) -> dict:
    """`{chỉ_số_câu: lệch_đầu_ms}` — phần IM trước khi câu đó thật sự nói.

    `a = start*hs` là mốc DANH NGHĨA câu được đặt vào; `t_a` là mốc NÓI THẬT
    (`silencedetect`). Hiệu hai số này độc lập với `hs`, nên nó so được giữa
    hai arm có hệ số hình khác nhau.
    """
    ra = {}
    for i, a_noi, _b in (moc or []):
        if i < len(cau):
            ra[i] = (float(a_noi) - float(cau[i]["start"]) * hs) * 1000.0
    return ra


def lech_chu_tieng(moc: list, moc_tu: list) -> dict:
    """LỆCH CHỮ-TIẾNG (ms): mốc TỪNG CHỮ so mốc NÓI THẬT của chính câu đó.

    Hai nguồn ĐỘC LẬP — mốc chữ do máy đọc trả rồi nhân `ty_le`; mốc nói do
    `silencedetect` đo trên file ĐÃ GHI. `ty_le` sai (bẫy "cắt đuôi thì phải
    dùng `1/tempo`") là cột này lộ ngay, còn `tempo_max` thì không thấy gì.
    """
    m = {i: (float(a), float(b)) for i, a, b in (moc or [])}
    dau, cuoi = [], []
    for i, ds in (moc_tu or []):
        if i not in m or not ds:
            continue
        a, b = m[i]
        dau.append(abs(float(ds[0][0]) - a) * 1000.0)
        cuoi.append(abs(float(ds[-1][1]) - b) * 1000.0)
    het = dau + cuoi
    return {"chu_tieng_ms_tb": _tb(het),
            "chu_tieng_ms_max": round(max(het), 1) if het else 0.0,
            "chu_dau_ms_tb": _tb(dau), "chu_cuoi_ms_tb": _tb(cuoi),
            "chu_tieng_n": len(het)}


def mot_arm(ten: str, k: dict, rg: dict, keo: float, lam: Path,
            tach: dict, voice: str, nhan: str) -> dict:
    """4c -> 5 -> trộn -> video, với `keo_dai_toi_da = keo`.

    **ĐI ĐÚNG THỨ TỰ CỦA `thay_giong_video`**: 4c chạy TRƯỚC, rồi `he_so_hinh_
    can` mới đọc `dn["files"]`. Tính `hs` trước 4c là đo một đường mã KHÔNG
    TỒN TẠI (và sẽ giấu mất chuyện kéo dài có đẩy `k_can` lên hay không).
    """
    lam.mkdir(parents=True, exist_ok=True)
    cau, tong = k["cau"], k["tong"]
    t0 = time.time()
    dn = tg.doc_nhanh_vua_khung(
        cau, rg["texts"], list(rg["files"]), list(rg["ok"]), tong,
        lam / "docnhanh", DICH_SANG, voice, moc_tu=list(rg.get("moc_tu") or []),
        nhan_nha=NHAN_NHA, keo_dai_toi_da=keo)
    g_4c = time.time() - t0

    _c = tg.he_so_hinh_can(cau, dn["files"], dn["ok"], tong)
    _fps = tg.do_fps(k["video"])
    _tran = tg.tran_hinh_theo_fps(_fps)
    hs = max(1.0, min(float(_c["k_can"]), _tran))
    tong_ra = tong * hs

    t1 = time.time()
    kh = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop",
                           moc_tu=dn.get("moc_tu"), he_so_hinh=hs,
                           keo_dai_toi_da=keo)
    g_5 = time.time() - t1

    # LỚP NỀN giãn theo hình — y đường thật.
    nhac = tach["nhac"]
    if hs > 1.0 + 1e-6:
        nh = lam / "nhac_gian.wav"
        tg._ffmpeg(["-i", str(nhac), "-af",
                    f"{tg._co_gian_chuoi(1.0 / hs)},aresample={tg.SR_TACH},"
                    f"apad,atrim=0:{tong_ra:.3f},asetpts=N/SR/TB",
                    "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                    str(nh)], "giãn lớp nhạc theo hệ số hình")
        nhac = str(nh)

    # **KHÔNG `bu_giong_goc`** — v2.48.0 đã bỏ hẳn ở cách trộn "tách nhạc"
    # (chèn lại chính tiếng Trung vào quãng nghỉ). Gọi nó ở đây là đo một
    # đường mã KHÔNG CÒN TỒN TẠI, và nó sẽ lấp mất đúng cột đang đo.
    au = tg.tron_thay_giong(nhac, list(kh["manh"]), tong_ra, lam / "tieng.wav",
                            goc_wav=k["wav"])
    dong_chu = tg.dong_chu_theo_giong(kh.get("moc_tieng") or [], rg["texts"],
                                      moc_tu=kh.get("moc_tu"))
    ra = lam / f"{nhan}_{ten}.mp4"
    tg.thay_audio_video(k["video"], au["ra"], ra, che_chu=False,
                        dong_chu=dong_chu, he_so_hinh=hs)

    td = toc_do_doc(rg["texts"], kh.get("moc_tieng") or [], cau)
    tb_k, sd_k, cv_k = _lech(td)
    ig = im_giua_cau(kh.get("moc_tieng") or [], tong_ra)
    mp = meo_pho(dn["files"], list(kh["tempo_cau"]), lam / "meo")
    do_to = tg.do_do_to(au["ra"])
    return {
        "nhan": nhan, "keo": round(keo, 2),
        "he_so_hinh": round(hs, 4), "k_can": _c["k_can"],
        "cham_tran": float(_c["k_can"]) > _tran + 1e-6,
        "do_dai_ra": round(tong_ra, 3),
        "giay_4c": round(g_4c, 1), "giay_5": round(g_5, 1),
        # --- bước 4c nói gì ---
        "so_cau_ngan": dn.get("so_cau_ngan", 0),
        "so_doc_cham": dn.get("so_doc_cham", 0),
        "rate_am_min": dn.get("rate_am_min", 0),
        "so_doc_lai": dn.get("so_doc_lai", 0),
        "rate_max": dn.get("rate_max", 0),
        # --- bước 5 nói gì ---
        "so_cau_keo_dai": kh.get("so_cau_keo_dai", 0),
        "keo_dai_max": kh.get("keo_dai_max", 1.0),
        "keo_dai_tb": kh.get("keo_dai_tb", 1.0),
        "so_cau_qua_ngan": kh.get("so_cau_qua_ngan", 0),
        "so_cau_loi": kh.get("so_cau_loi", 0),
        "loi_cau": kh.get("loi_cau", []),
        # --- CỘT 1 ---
        **{f"im_{x}": ig[f"im_giua_{x}"] for x in
           ("tong", "so", "dai_nhat", "tb", "pt")},
        "im_so_05": ig["im_giua_so_05"], "im_so_10": ig["im_giua_so_10"],
        "im_so_20": ig["im_giua_so_20"],
        "ti_le_co_tieng": ig["ti_le_co_tieng"],
        # --- CỘT 3 ---
        **lech_chu_tieng(kh.get("moc_tieng") or [], kh.get("moc_tu") or []),
        # --- CỘT 4 ---
        **mp,
        # --- CỘT 5 ---
        "kytu_giay_tb": round(tb_k, 2), "kytu_giay_sd": round(sd_k, 3),
        "kytu_giay_cv": round(cv_k, 2), "kytu_giay_n": len(td),
        # --- bất biến cũ, không được vỡ ---
        "tempo_max": kh["tempo_max"], "tempo_tb": kh["tempo_tb"],
        "chong_lan_ms_max": kh["chong_lan_ms_max"],
        "so_cau_chong_lan": kh["so_cau_chong_lan"],
        "im_duoi_chu_giay_tong": kh["im_duoi_chu_giay_tong"],
        "lufs_I": round(do_to.get("I", 0.0), 2),
        "lufs_TP": round(do_to.get("TP", 0.0), 2),
        "kiem_video_ra": tg.kiem_video_ra(ra, tong_ra),
        "_lech_dau": lech_dau_tung_cau(kh.get("moc_tieng") or [], cau, hs),
        "ra": str(ra),
    }


def mot_giong(ten: str, k: dict, lam0: Path, tach: dict, goc_ma: str,
              dd: dict, voice_ma: str, nhan_g: str) -> dict:
    lam = lam0 / f"g_{nhan_g}"
    lam.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 70}\n=== {ten} · GIỌNG {nhan_g} "
          f"({voice_ma or 'edge-tts theo ngôn ngữ'}) ===")

    tts = tg.doc_ban_dich(dd["ban_dich"], lam / "tts", voice_ma, DICH_SANG,
                          nhan_nha=NHAN_NHA)
    rg = tg.rut_gon_vua_khung(k["cau"], dd["ban_dich"], tts, k["tong"],
                              lam / "rutgon", DICH_SANG, tts["voice"],
                              nhan_nha=NHAN_NHA)
    print(f"  giọng thật: {tts['voice']} · rút gọn {rg['so_sua']} câu"
          f" · máy đọc thực thi `rate` THẬT: "
          f"{tg.rate_la_doc_that(tts['voice'])}")

    # SÀN ĐỐI CHỨNG: trải tốc độ đọc VỐN CÓ của máy đọc, trên file TTS THÔ.
    tho = []
    for i, p in enumerate(rg["files"]):
        if not p or not Path(p).exists() or i >= len(rg["texts"]):
            continue
        le_d, le_c, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        d = tg.probe_duration(p) - le_d - le_c
        n = len(str(rg["texts"][i]).strip())
        if n >= 8 and d > 0.25:
            tho.append(n / d)
    tb_t, sd_t, cv_t = _lech(tho)
    print(f"  SÀN (TTS thô): {tb_t:.2f} ký tự/giây · SD {sd_t:.3f} · "
          f"CV {cv_t:.2f}%  ({len(tho)} câu)")

    arms = []
    for m in MUC:
        nh = f"KEO{int(round(m * 100)):03d}"
        try:
            a = mot_arm(ten, k, rg, m, lam / nh, tach, tts["voice"], nh)
        except Exception as e:                            # noqa: BLE001
            import traceback
            print(f"!!! arm {nh} HỎNG: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        arms.append(a)
        print(f"  {nh} (kéo <= {m:.2f}) · im {a['im_pt']:>6.2f}% · "
              f"{a['im_so_05']:>2} quãng>=0,5s · dài nhất {a['im_dai_nhat']:>5.2f}s"
              f" · CV {a['kytu_giay_cv']:>5.2f}% · {a['kytu_giay_tb']:>5.2f} kt/s"
              f" · méo {a['meo_db_tb']:.3f} dB · chữ-tiếng {a['chu_tieng_ms_tb']:.1f} ms")

    # ---- TRÔI GHÉP CẶP so arm TẮT (cột 2) ----
    if arms:
        goc = arms[0]["_lech_dau"]
        for a in arms:
            d = [abs(v - goc[i]) for i, v in a["_lech_dau"].items()
                 if i in goc]
            a["troi_ms_tb"] = _tb(d)
            a["troi_ms_max"] = round(max(d), 1) if d else 0.0
            a["so_cau_troi_qua_50ms"] = sum(1 for x in d if x > 50.0)
            a.pop("_lech_dau", None)

    # ---- file NGHE THỬ: VIDEO, cùng một lượt chạy ----
    ra = NGHE / ten / nhan_g
    ra.mkdir(parents=True, exist_ok=True)
    for a in arms:
        p = Path(a["ra"])
        if not p.exists():
            continue
        ten_moi = (f"{a['nhan']}_im{a['im_pt']:.2f}pt_"
                   f"{a['im_so_05']}quang_cv{a['kytu_giay_cv']:.1f}_{ten}.mp4"
                   ).replace(".", ",").replace(",mp4", ".mp4")
        shutil.copy2(p, ra / ten_moi)
        a["nghe_thu"] = str(ra / ten_moi)
    return {"ten": ten, "giong": nhan_g, "giong_ma": voice_ma,
            "voice_that": tts["voice"],
            "rate_that": tg.rate_la_doc_that(tts["voice"]),
            "so_cau": len(k["cau"]), "do_dai_goc": round(k["tong"], 2),
            "san_kytu_giay_tb": round(tb_t, 2), "san_kytu_giay_sd": round(sd_t, 3),
            "san_kytu_giay_cv": round(cv_t, 2),
            "arms": arms}


def mot_video(ten: str) -> list[dict]:
    print(f"\n{'#' * 74}\n##### {ten} #####")
    k = kho.chuan_bi(ten)
    lam = LAM / ten
    lam.mkdir(parents=True, exist_ok=True)

    tach_dir = kho.LAM / ten / "tach_kv"
    nhac, giong = tach_dir / "nhac.wav", tach_dir / "giong.wav"
    if not (nhac.exists() and giong.exists()):
        print("  tách giọng bằng Demucs (lần đầu, sẽ cache)...")
        tach_dir.mkdir(parents=True, exist_ok=True)
        t = tg.tach_giong(k["wav"], tach_dir / "raw", cach="demucs")
        shutil.copy2(t["nhac"], nhac)
        shutil.copy2(t["giong"], giong)
    tach = {"nhac": str(nhac), "giong": str(giong)}

    goc_ma = (k["chep"].get("language") or "")[:2].lower()
    print(f"  {k['tong']:.2f}s · {len(k['cau'])} câu · {goc_ma} -> {DICH_SANG}")
    # MỘT bản dịch DÙNG CHUNG mọi giọng mọi arm.
    dd = tg.dich_hau_kiem(k["cau"], DICH_SANG, goc_ma)

    ra = []
    for nhan_g, ma in GIONG:
        try:
            ra.append(mot_giong(ten, k, lam, tach, goc_ma, dd, ma, nhan_g))
        except Exception as e:                            # noqa: BLE001
            import traceback
            print(f"\n!!! giọng {nhan_g} HỎNG: {type(e).__name__}: {e}")
            traceback.print_exc()
    return ra


def in_bang(rs: list[dict]) -> None:
    print(f"\n\n{'=' * 96}\nBẢNG TỔNG — GHÉP CẶP, arm TẮT (kéo 1,00) LÀ ĐỐI "
          f"CHỨNG\n{'=' * 96}")
    for r in rs:
        print(f"\n### {r['ten']} · {r['giong']} · {r['so_cau']} câu · "
              f"máy đọc có `rate` thật: {r['rate_that']}")
        print(f"    SÀN TTS thô: {r['san_kytu_giay_tb']:.2f} kt/s · "
              f"CV {r['san_kytu_giay_cv']:.2f}%")
        print(f"    {'kéo':>5} | {'im %':>6} {'>=0,5s':>7} {'dài nhất':>9} | "
              f"{'TRÔI tb':>8} {'TRÔI max':>9} | {'chữ-tiếng tb':>13} "
              f"{'max':>7} | {'méo dB':>7} | {'kt/s':>6} {'CV %':>6} | "
              f"{'tempo':>6} {'chồng':>6} | {'k hình':>7}")
        for a in r["arms"]:
            print(f"    {a['keo']:>5.2f} | {a['im_pt']:>6.2f} "
                  f"{a['im_so_05']:>7} {a['im_dai_nhat']:>9.2f} | "
                  f"{a.get('troi_ms_tb', 0):>8.1f} {a.get('troi_ms_max', 0):>9.1f} | "
                  f"{a['chu_tieng_ms_tb']:>13.1f} {a['chu_tieng_ms_max']:>7.1f} | "
                  f"{a['meo_db_tb']:>7.3f} | {a['kytu_giay_tb']:>6.2f} "
                  f"{a['kytu_giay_cv']:>6.2f} | {a['tempo_max']:>6.3f} "
                  f"{a['chong_lan_ms_max']:>6.1f} | {a['he_so_hinh']:>7.4f}")
        for a in r["arms"]:
            print(f"      {a['nhan']}: 4c đọc CHẬM {a['so_doc_cham']}/"
                  f"{a['so_cau_ngan']} câu (rate {a['rate_am_min']}%) · "
                  f"bước 5 kéo giãn {a['so_cau_keo_dai']} câu "
                  f"(max {a['keo_dai_max']}) · 4c {a['giay_4c']}s · "
                  f"câu quá ngắn {a['so_cau_qua_ngan']} · lỗi {a['so_cau_loi']}"
                  f" · I {a['lufs_I']} LUFS")


def main() -> int:
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    tens = [a for a in sys.argv[1:] if not a.startswith("-")] or ["lt1", "lt2"]
    print(f"MỨC KÉO: {MUC} · GIỌNG: {[g[0] for g in GIONG]} · "
          f"nhấn nhá {NHAN_NHA} · đích {DICH_SANG}")
    tat: list[dict] = []
    for ten in tens:
        try:
            tat += mot_video(ten)
        except Exception as e:                            # noqa: BLE001
            import traceback
            print(f"!!! {ten}: {type(e).__name__}: {e}")
            traceback.print_exc()
        KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    in_bang(tat)
    print(f"\nGhi: {KQ.name} · nghe thử: {NGHE}")
    return 0 if tat else 1


if __name__ == "__main__":
    raise SystemExit(main())
