# -*- coding: utf-8 -*-
"""ĐO THẬT (âm thanh, không mô phỏng): **ĐỌC CHẬM LẠI CHO ĐẦY KHUNG**.

Bốn hướng trước đều cố ĐỔI CHỖ khoảng im. `_do_chay_lien.py` chứng minh bằng số
là **không đổi chỗ được**: tổng im = `độ_dài_video − tổng_tiếng`, một phép trừ.
Muốn im NHỎ ĐI thì tiếng phải DÀI RA. Bước 4c của app chỉ biết đọc NHANH lên
(`doc_nhanh_vua_khung`); **chưa có đường nào đọc CHẬM lại**.

Hướng này giữ NGUYÊN khung cố định -> câu vẫn nằm đúng mốc gốc -> **lệch
tiếng-hình = 0 THEO CẤU TẠO**, đúng cột đã giết 3 hướng trước.

**GHÉP CẶP TỪNG BYTE:** mọi arm dùng CHUNG bộ file giọng của lượt chạy THẬT đã
cache (`arm_moi` của lượt `_do_khop_video.py`, đo được `tempo_max = 1.000` nên
độ dài file CHÍNH LÀ độ dài tự nhiên máy đọc). Không LLM, không TTS -> TIỀN
ĐỊNH, chạy lại ra cùng số.

    .venv\\Scripts\\python -u _do_doc_cham.py [ten...]
"""
from __future__ import annotations

import json
import os
import shutil
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

import _do_kho_tg as kho                              # noqa: E402
import _do_rubberband as rb                           # noqa: E402
from _do_khop_video import im_giua_cau                # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
TAM = REPO / "_do_kv_tam"
LAM = REPO / "_do_dc_tam"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "lien_mach_3"
KQ = REPO / "_kq_doc_cham.json"

#: Trần KÉO DÀI mỗi câu. 1,00 = arm ĐỐI CHỨNG (đúng app hôm nay).
MUC = (1.00, 1.15, 1.25, 1.40)

#: Nhịp thở chừa trước câu kế — dùng lại đúng hằng số của app.
NHIP = 0.12


def _tk(xs: list[float]) -> tuple[float, float, float]:
    if len(xs) < 2:
        return (xs[0] if xs else 0.0), 0.0, 0.0
    tb = statistics.fmean(xs)
    sd = statistics.pstdev(xs)
    return tb, sd, (100.0 * sd / tb if tb else 0.0)


def nap(ten: str, giong: str) -> dict | None:
    d = TAM / ten / f"g_{giong}" / "arm_moi" / "khop"
    fs = sorted(d.glob("khop_*.wav")) if d.is_dir() else []
    if not fs:
        return None
    idx, dai, led, lec = [], [], [], []
    for p in fs:
        dn = tg.probe_duration(p)
        if dn <= 0:
            continue
        a, b, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        idx.append(int(p.stem.split("_")[1]))
        dai.append(dn)
        led.append(a)
        lec.append(b)
    return {"file": [str(p) for p in fs], "idx": idx, "dai": dai,
            "le_d": led, "le_c": lec}


def mot_arm(ten: str, giong: str, cham_toi_da: float, k: dict, lc: dict,
            hs: float, lam: Path, nhac: str) -> dict:
    """Dựng THẬT: co giãn từng file, ghép, đo trên chính file đã ghi."""
    lam.mkdir(parents=True, exist_ok=True)
    cau, tong_ra = k["cau"], k["tong"] * hs
    idx, dai, led = lc["idx"], lc["dai"], lc["le_d"]
    a_moc = [float(cau[i]["start"]) * hs for i in idx]

    manh: list[tuple[float, str]] = []
    he_so: list[float] = []
    moc_tieng: list[tuple[int, float, float]] = []
    troi: list[float] = []
    for j, i in enumerate(idx):
        a = a_moc[j]
        ke = a_moc[j + 1] if j + 1 < len(idx) else tong_ra
        khung = max(0.05, ke - a - NHIP)
        # KÉO DÀI cho đầy khung, trần `cham_toi_da`. `tempo < 1` = chậm lại.
        kx = min(cham_toi_da, max(1.0, khung / max(0.05, dai[j])))
        he_so.append(kx)
        src = lc["file"][j]
        if kx > 1.001:
            dst = lam / f"cham_{i:04d}.wav"
            tg._ffmpeg(["-i", src, "-af",
                        f"{tg._co_gian_chuoi(1.0 / kx)},aresample={tg.SR_TACH}",
                        "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                        str(dst)], f"kéo chậm câu #{i}")
        else:
            dst = lam / f"cham_{i:04d}.wav"
            shutil.copy2(src, dst)
        # ĐO LẠI TRÊN FILE ĐÃ GHI — không tin số dự kiến (rubberband/aresample
        # làm tròn khác `d*k`), đúng luật của `khop_thoi_gian`.
        d_fin = tg.probe_duration(dst)
        e_d, e_c, _ = tg.do_le_im(dst, nguong_db=tg.NGUONG_IM_MOC_DB)
        t_a = a + e_d
        t_b = a + max(e_d + 0.05, d_fin - e_c)
        moc_tieng.append((i, round(t_a, 3), round(t_b, 3)))
        manh.append((a, str(dst)))
        # LỆCH TIẾNG-HÌNH: mốc NÓI THẬT so với mốc người GỐC nói câu đó.
        troi.append((t_a - (a + led[j])) * 1000.0)

    # ---- trộn THẬT (đúng cửa app dùng) ----
    au = tg.tron_thay_giong(nhac, manh, tong_ra, lam / "tieng.wav",
                            goc_wav=str(k["wav"]))
    do_to = tg.do_do_to(au["ra"])
    ig = im_giua_cau(moc_tieng, tong_ra)

    # ---- méo phổ THẬT: vòng tròn k rồi 1/k trên chính file giọng ----
    ds = []
    for j, kx in enumerate(he_so):
        if kx <= 1.001:
            ds.append(0.0)
            continue
        p = Path(lc["file"][j])
        a1 = lam / f"m{j:04d}_a.wav"
        b1 = lam / f"m{j:04d}_b.wav"
        try:
            rb.ff(["-i", str(p), "-af", tg._co_gian_chuoi(1.0 / kx), "-ac", "1",
                   "-ar", "16000", "-c:a", "pcm_s16le", str(a1)])
            rb.ff(["-i", str(a1), "-af", tg._co_gian_chuoi(kx), "-ac", "1",
                   "-ar", "16000", "-c:a", "pcm_s16le", str(b1)])
            v = rb.lech_db(p, b1)
            if v >= 0:
                ds.append(v)
        except Exception as e:                          # noqa: BLE001
            print(f"    (méo phổ #{j} bỏ: {type(e).__name__})")

    _tbk, _sdk, cvk = _tk(he_so)
    tr_abs = [abs(x) for x in troi]
    return {
        "cham_toi_da": cham_toi_da,
        **{f"im_{x}": ig[f"im_giua_{x}"] for x in
           ("tong", "so", "dai_nhat", "tb", "pt")},
        "im_so_05": ig["im_giua_so_05"], "im_so_10": ig["im_giua_so_10"],
        "im_so_20": ig["im_giua_so_20"],
        "ti_le_co_tieng": ig["ti_le_co_tieng"],
        # ---- CỘT GIẾT 3 HƯỚNG TRƯỚC ----
        "troi_max_ms": round(max(tr_abs), 1) if tr_abs else 0.0,
        "troi_tb_ms": round(statistics.fmean(tr_abs), 1) if tr_abs else 0.0,
        "so_cau_troi_qua_30ms": sum(1 for x in tr_abs if x > 30.0),
        # ---- giá phải trả ----
        "keo_tb": round(_tbk, 4), "keo_max": round(max(he_so), 4),
        "keo_cv_pt": round(cvk, 2),
        "so_cau_keo": sum(1 for x in he_so if x > 1.001),
        "meo_db_tb": round(statistics.fmean(ds), 3) if ds else 0.0,
        "meo_db_max": round(max(ds), 3) if ds else 0.0,
        "lufs_I": round(do_to.get("I", 0.0), 2),
        "lufs_TP": round(do_to.get("TP", 0.0), 2),
        "_moc_tieng": moc_tieng, "_wav": au["ra"],
    }


def mot(ten: str, giong: str) -> dict | None:
    lc = nap(ten, giong)
    if not lc:
        print(f"  [{ten}/{giong}] chưa có bộ file giọng cache -> bỏ")
        return None
    k = kho.chuan_bi(ten)
    # HỆ SỐ HÌNH phải lấy từ ĐÚNG lượt chạy đã sinh ra bộ file giọng này.
    # **BẢN ĐẦU LÙI IM LẶNG VỀ 1,1988 KHI TRA HỤT — VÀ ĐÃ RA SỐ SAI MỘT LẦN:**
    # `_kq_khop_video.json` bị lượt lt2 ghi đè nên mục lt1/EDGE biến mất, phép
    # đo lấy 1,1988 thay cho 1,1144 THẬT và in ra bảng trông vẫn hợp lý
    # (im 23,85% thay vì 18,29%). Đúng họ "phép đo hỏng phát chứng nhận".
    # Nay tra hụt là NÉM, không lùi.
    hs = None
    p = REPO / "_kq_khop_video.json"
    if p.exists():
        for r in json.loads(p.read_text(encoding="utf-8")):
            if r.get("ten") == ten and r.get("nhan_giong") == giong:
                hs = float((r.get("moi") or {}).get("he_so_hinh") or 0) or None
    if hs is None:
        hs = float(os.environ.get("BQ_DC_HS", "0") or 0) or None
    if hs is None:
        raise RuntimeError(
            f"KHÔNG tra được hệ_số_hình của {ten}/{giong} trong "
            f"{p.name} — lấy số mặc định là đo một cấu hình KHÁC rồi báo như "
            f"thật. Chạy lại _do_khop_video.py, hoặc đặt BQ_DC_HS=<k>.")
    # lớp nhạc ĐÃ GIÃN theo hệ số hình — dựng lại đúng đường thật
    lam0 = LAM / ten / giong
    lam0.mkdir(parents=True, exist_ok=True)
    nhac = str((kho.LAM / ten / "tach_kv" / "nhac.wav"))
    if hs > 1.0 + 1e-6:
        nh = lam0 / "nhac_gian.wav"
        if not nh.exists():
            tg._ffmpeg(["-i", nhac, "-af",
                        f"{tg._co_gian_chuoi(1.0 / hs)},aresample={tg.SR_TACH},"
                        f"apad,atrim=0:{k['tong'] * hs:.3f},asetpts=N/SR/TB",
                        "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a",
                        "pcm_s16le", str(nh)], "giãn nhạc")
        nhac = str(nh)

    print(f"\n{'#' * 74}\n### {ten} · {giong} · k={hs:.4f} · "
          f"{len(lc['idx'])} câu · ra {k['tong'] * hs:.2f}s")
    arms = []
    for m in MUC:
        r = mot_arm(ten, giong, m, k, lc, hs, lam0 / f"m{int(m * 100)}", nhac)
        arms.append(r)
        print(f"  kéo <= {m:.2f}x · im {r['im_pt']:>6.2f}% · "
              f"{r['im_so_05']:>2} quãng>=0,5s · dài nhất {r['im_dai_nhat']:>5.2f}s"
              f" · TRÔI max {r['troi_max_ms']:>6.1f} ms · méo {r['meo_db_tb']:.3f} dB"
              f" · I {r['lufs_I']:.2f} LUFS")
    return {"ten": ten, "giong": giong, "he_so_hinh": hs,
            "so_cau": len(lc["idx"]), "do_dai_ra": round(k["tong"] * hs, 3),
            "arms": arms}


def main() -> int:
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    tens = sys.argv[1:] or ["lt1", "lt2"]
    tat = []
    for ten in tens:
        for giong in ("VNB", "EDGE"):
            try:
                r = mot(ten, giong)
            except Exception as e:                      # noqa: BLE001
                import traceback
                print(f"!!! {ten}/{giong}: {type(e).__name__}: {e}")
                traceback.print_exc()
                continue
            if r:
                tat.append(r)
                KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"\nGhi: {KQ.name}")
    return 0 if tat else 1


if __name__ == "__main__":
    raise SystemExit(main())
