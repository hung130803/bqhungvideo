# -*- coding: utf-8 -*-
"""ĐO HƯỚNG "BỎ KHUNG CỐ ĐỊNH — CHO CÂU CHẢY LIỀN, NEO LẠI Ở RANH GIỚI CẢNH".

Anh Hùng kêu BA LẦN: *"nói còn không liên tiếp, cứ được đoạn rồi nghỉ, không
liền mạch"*. Ba hướng trước (gộp câu · gộp lượt TTS · giãn hình không đều) đều
**chết ở cột LỆCH TIẾNG-HÌNH** hoặc ở chốt `SAN_NHIP_HINH_FPS`. Hướng này bỏ
khung cố định: câu i+1 bắt đầu ngay khi câu i đọc xong (cộng một nhịp thở), rồi
**NEO LẠI** ở mốc an toàn.

**PHÉP ĐO NÀY CỐ Ý *KHÔNG* GỌI LLM/TTS/ffmpeg-mã-hoá.** Nó dựng lại timeline từ
ĐÚNG dữ liệu của lượt chạy thật đã cache (`_do_kv_tam/<ten>/g_<GIỌNG>/arm_moi/
khop/khop_*.wav` + bản chép lời trong `_do_tg_cache.json`), nên:
  · TIỀN ĐỊNH — chạy lại ra cùng số, khác hẳn mọi phép đo có LLM trong đường
  · GHÉP CẶP THEO CẤU TẠO — mọi arm dùng CHUNG một bộ file giọng, từng byte
  · rẻ (vài chục giây) nên chạy được đủ lưới tham số thay vì đoán 1 điểm

**CỘT ĐO TRƯỚC TIÊN LÀ LỆCH TIẾNG-HÌNH** (`troi_*`), đúng cột đã giết 2/3 hướng
trước. Ra vượt trần thì DỪNG, không nối.

    .venv\\Scripts\\python -u _do_chay_lien.py
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
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
from config import settings                           # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
TAM = REPO / "_do_kv_tam"          # thư mục lượt chạy thật (đã có sẵn khop_*)
KQ = REPO / "_kq_chay_lien.json"
_NW = 0x0800_0000 if os.name == "nt" else 0

#: Trần trôi để QUÉT. Hai mốc có sẵn trong repo, trần thật nằm ở GIỮA:
#:   · `LECH_TOI_DA = 30 ms` (lớp nhấn nhá) = chuẩn "KHÔNG được xê dịch"
#:   · 269-354 ms = lệch hình-tiếng ĐANG tồn tại ở CẢ arm cũ mà không ai kêu
#: Quét cả dải rồi đọc, KHÔNG chép một số vào rồi báo.
TRAN_TROI = (0.05, 0.10, 0.20, 0.30, 0.50, 1.00, 1e9)

#: Nhịp thở giữa hai câu. Mốc có sẵn: `cat_le_loat` giữ 0,04 s đầu / 0,08 s
#: cuối, và app thật đo ra 5,26% im ở mức đó -> 0,12 s là "dính sát".
NHIP_THO = (0.12, 0.20, 0.30)

#: Bao nhiêu giây im TRONG BẢN GỐC thì coi là "người ta ngừng nói" -> mốc neo.
IM_GOC_MOC = 0.35
NGUONG_IM_GOC_DB = -30.0


# ══════════════════════════ hạ tầng ══════════════════════════
def _ff_loi(args: list[str]) -> str:
    r = subprocess.run([settings.FFMPEG_PATH, "-hide_banner", "-nostdin",
                        *args, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NW, timeout=900)
    return r.stderr or ""


def _tk(xs: list[float]) -> dict:
    """Thống kê gọn cho một dãy số."""
    if not xs:
        return {"n": 0, "tb": 0.0, "max": 0.0, "p90": 0.0, "tong": 0.0}
    s = sorted(xs)
    return {"n": len(xs), "tb": round(statistics.fmean(xs), 4),
            "max": round(max(xs), 4),
            "p90": round(s[min(len(s) - 1, int(0.9 * len(s)))], 4),
            "tong": round(sum(xs), 3)}


def im_dai_goc(wav: Path) -> list[tuple[float, float]]:
    """Khoảng IM DÀI của bản GỐC — nguồn mốc neo thứ hai."""
    out = _ff_loi(["-i", str(wav), "-af",
                   f"silencedetect=n={NGUONG_IM_GOC_DB}dB:d={IM_GOC_MOC}"])
    ra, dau = [], None
    for m in re.finditer(r"silence_(start|end):\s*(-?[\d.]+)", out):
        if m.group(1) == "start":
            dau = float(m.group(2))
        elif dau is not None:
            ra.append((dau, float(m.group(2))))
            dau = None
    return ra


def cat_canh(video: Path) -> list[float]:
    """Mốc CHUYỂN CẢNH — nguồn mốc neo RẺ NHẤT (mắt không bắt được độ trôi
    xuyên qua ranh giới cảnh). Dùng đúng bộ dò đã có trong repo."""
    from app.core import scene_detect
    if not scene_detect.is_available():
        print("  (KHÔNG có PySceneDetect -> bỏ nguồn mốc CẮT CẢNH)")
        return []
    return list(scene_detect.detect_scenes(str(video))["cut_points"])


# ══════════════════════════ dựng lại lượt chạy thật ══════════════════════════
def nap_lan_chay(ten: str, giong: str) -> dict | None:
    """Đọc lại bộ file giọng của lượt chạy THẬT đã cache.

    `arm_moi` của giọng `vnb:` đo được `tempo_max = 1.000` -> **không câu nào
    bị ép**, nên độ dài file `khop_*.wav` CHÍNH LÀ độ dài tự nhiên của máy đọc.
    Đó là lý do lấy arm này chứ không lấy `arm_cu` (có ép 1,108).
    """
    d = TAM / ten / f"g_{giong}" / "arm_moi" / "khop"
    if not d.is_dir():
        return None
    fs = sorted(d.glob("khop_*.wav"))
    if not fs:
        return None
    cau_i, dai, led, lec = [], [], [], []
    for p in fs:
        i = int(p.stem.split("_")[1])
        dn = tg.probe_duration(p)
        if dn <= 0:
            continue
        a, b, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        cau_i.append(i)
        dai.append(dn)
        led.append(a)
        lec.append(b)
    return {"idx": cau_i, "dai": dai, "le_d": led, "le_c": lec}


# ══════════════════════════ mô phỏng ══════════════════════════
def mo_phong(a_moc: list[float], dai: list[float], led: list[float],
             lec: list[float], tong_ra: float, neo: set[int],
             troi_max: float, nhip: float) -> dict:
    """Đặt lại từng câu theo luật CHẢY LIỀN + NEO. Hàm THUẦN.

    `a_moc[i]` = mốc gốc của câu i **trên trục ĐẦU RA** (đã nhân hệ số hình).
    Trả mốc đặt, độ trôi, và bảng khoảng im giữa câu.

    Ba luật, theo thứ tự ưu tiên:
      1. **0 ms chồng lấn file** — bất biến của repo, không bao giờ nhường.
      2. **neo** -> đặt lại đúng mốc gốc (`troi = 0`).
      3. **trần trôi** -> không được chạy trước mốc gốc quá `troi_max`.
    """
    n = len(dai)
    t = [0.0] * n
    troi = [0.0] * n
    het_truoc = 0.0                 # mốc KẾT THÚC FILE của câu trước
    noi_truoc = 0.0                 # mốc HẾT TIẾNG của câu trước
    for i in range(n):
        a = a_moc[i]
        # chảy liền: tiếng câu này bắt đầu ngay sau tiếng câu trước + nhịp thở
        t_chay = noi_truoc + nhip - led[i]
        t_som = max(het_truoc, t_chay)              # (1) không chồng file
        if i in neo:
            t_i = max(t_som, a)                     # (2) neo lại
        else:
            t_i = max(t_som, a - troi_max)          # (3) trần trôi
        t[i] = t_i
        troi[i] = t_i - a
        het_truoc = t_i + dai[i]
        noi_truoc = t_i + max(led[i] + 0.05, dai[i] - lec[i])

    # ---- khoảng im GIỮA CÂU trên bản đã ghép (đúng thước `im_giua_cau`) ----
    ms = sorted((t[i] + led[i], t[i] + max(led[i] + 0.05, dai[i] - lec[i]))
                for i in range(n))
    kho_im = [a1 - b0 for (_a0, b0), (a1, _b1) in zip(ms, ms[1:]) if a1 - b0 > 0]
    noi = sum(b - a for a, b in ms)
    het = max((t[i] + dai[i]) for i in range(n)) if n else 0.0
    tr_abs = [abs(x) for x in troi]
    return {
        "im_tong": round(sum(kho_im), 3),
        "im_pt": round(100.0 * sum(kho_im) / max(0.001, tong_ra), 2),
        "im_so_05": sum(1 for g in kho_im if g >= 0.5),
        "im_so_10": sum(1 for g in kho_im if g >= 1.0),
        "im_so_20": sum(1 for g in kho_im if g >= 2.0),
        "im_dai_nhat": round(max(kho_im), 3) if kho_im else 0.0,
        "ti_le_co_tieng": round(100.0 * noi / max(0.001, tong_ra), 2),
        "troi_max_ms": round(max(tr_abs) * 1000.0, 1) if tr_abs else 0.0,
        "troi_tb_ms": round(statistics.fmean(tr_abs) * 1000.0, 1) if tr_abs else 0.0,
        "troi_p90_ms": round(sorted(tr_abs)[min(n - 1, int(0.9 * n))] * 1000.0, 1)
        if n else 0.0,
        "so_cau_troi_qua_100ms": sum(1 for x in tr_abs if x > 0.10),
        "so_cau_troi_qua_300ms": sum(1 for x in tr_abs if x > 0.30),
        "so_neo": len(neo),
        "tran_phim_giay": round(het - tong_ra, 3),   # >0 = tràn khỏi phim
        "troi": [round(x, 4) for x in troi],
    }


def mo_phong_cham(a_moc: list[float], dai: list[float], led: list[float],
                  lec: list[float], tong_ra: float, nhip: float,
                  cham_toi_da: float) -> dict:
    """ARM 5 — **GIỮ NGUYÊN KHUNG CỐ ĐỊNH, ĐỌC CHẬM LẠI CHO ĐẦY KHUNG.**

    Vì sao có arm này: bốn hướng trước (gộp câu · gộp lượt TTS · giãn hình
    không đều · chảy liền + neo) đều cố ĐỔI CHỖ khoảng im, mà tổng im thì
    **KHÔNG ĐỔI ĐƯỢC** — nó bằng `độ_dài_video − tổng_tiếng`, một phép trừ.
    Muốn tổng im NHỎ ĐI thì chỉ có hai đường: video ngắn lại, hoặc **TIẾNG DÀI
    RA**. Bước 4c của app chỉ biết đọc NHANH lên (`doc_nhanh_vua_khung`); chưa
    có đường nào đọc CHẬM lại.

    Đọc chậm giữ được cả ba thứ mà bốn hướng kia phải đánh đổi:
      · câu vẫn bắt đầu ĐÚNG mốc gốc -> **trôi = 0 THEO CẤU TẠO**
      · không gộp câu -> không có quãng RẤT DÀI
      · không đụng nhịp hình -> không chạm sàn `SAN_NHIP_HINH_FPS`

    Cái phải trả: mỗi câu một tốc độ đọc khác nhau -> **TRẢI tốc độ đọc rộng
    ra**, đúng cột anh Hùng cũng đã kêu (*"lúc nhanh lúc chậm"*). Nên hàm này
    trả CẢ HAI cột để đọc cùng nhau, và `cham_toi_da` là núm đánh đổi.

    `cham_toi_da` = hệ số kéo dài LỚN NHẤT cho phép (1,00 = không kéo).
    """
    n = len(dai)
    ms, he_so = [], []
    for i in range(n):
        a = a_moc[i]
        ke = a_moc[i + 1] if i + 1 < n else tong_ra
        khung = max(0.05, ke - a - nhip)
        noi = max(0.05, dai[i] - led[i] - lec[i])       # thời gian CÓ TIẾNG
        k = min(cham_toi_da, max(1.0, khung / max(0.05, dai[i])))
        he_so.append(k)
        ms.append((a + led[i] * k, a + (led[i] + noi) * k))
    ms.sort()
    kho_im = [a1 - b0 for (_a0, b0), (a1, _b1) in zip(ms, ms[1:]) if a1 - b0 > 0]
    return {
        "im_tong": round(sum(kho_im), 3),
        "im_pt": round(100.0 * sum(kho_im) / max(0.001, tong_ra), 2),
        "im_so_05": sum(1 for g in kho_im if g >= 0.5),
        "im_so_10": sum(1 for g in kho_im if g >= 1.0),
        "im_so_20": sum(1 for g in kho_im if g >= 2.0),
        "im_dai_nhat": round(max(kho_im), 3) if kho_im else 0.0,
        "ti_le_co_tieng": round(100.0 * sum(b - a for a, b in ms)
                                / max(0.001, tong_ra), 2),
        "troi_max_ms": 0.0,                 # theo CẤU TẠO — câu ở đúng mốc gốc
        "cham_tb": round(statistics.fmean(he_so), 4),
        "cham_max": round(max(he_so), 4),
        "so_cau_cham": sum(1 for k in he_so if k > 1.001),
        "so_cau_cham_qua_125": sum(1 for k in he_so if k > 1.25),
    }


def neo_tu_moc(a_moc: list[float], moc: list[float], lech_toi_da: float = 0.60
               ) -> set[int]:
    """Câu nào bắt đầu GẦN một mốc neo thì thành câu neo.

    `lech_toi_da` = câu phải nằm trong ngần này giây quanh mốc mới tính — mốc
    cắt cảnh rơi vào GIỮA một câu thì neo ở đó là cắt ngang câu, vô nghĩa.
    """
    if not moc:
        return set()
    ra = set()
    for m in moc:
        best, bd = -1, 1e9
        for i, a in enumerate(a_moc):
            d = abs(a - m)
            if d < bd:
                best, bd = i, d
        if best >= 0 and bd <= lech_toi_da:
            ra.add(best)
    return ra


# ══════════════════════════ một video ══════════════════════════
def mot_video(ten: str, giong: str) -> dict | None:
    k = kho.chuan_bi(ten)
    lc = nap_lan_chay(ten, giong)
    if not lc:
        print(f"  [{ten}/{giong}] KHÔNG có bộ file giọng đã cache -> bỏ qua")
        return None
    cau = k["cau"]
    idx, dai, led, lec = lc["idx"], lc["dai"], lc["le_d"], lc["le_c"]

    # hệ số hình của lượt chạy thật (đọc từ kết quả đã công bố)
    hs = 1.1988
    kq_cu = REPO / "_kq_khop_video.json"
    if kq_cu.exists():
        for r in json.loads(kq_cu.read_text(encoding="utf-8")):
            if r.get("ten") == ten and r.get("nhan_giong") == giong:
                hs = float((r.get("moi") or {}).get("he_so_hinh") or hs)
    tong_ra = k["tong"] * hs
    a_moc = [float(cau[i]["start"]) * hs for i in idx]

    print(f"\n{'#' * 76}\n### {ten} · giọng {giong} · nguồn {k['tong']:.2f}s"
          f" · k={hs:.4f} -> ra {tong_ra:.2f}s · {len(idx)} câu")

    # ---------- NGUỒN MỐC NEO ----------
    canh = cat_canh(k["video"])
    im_g = im_dai_goc(k["wav"])
    im_moc = [round((a + b) / 2.0 * hs, 3) for a, b in im_g]
    canh_ra = [round(c * hs, 3) for c in canh]
    seg_moc = list(a_moc)
    phut = tong_ra / 60.0
    nguon = {
        "cat_canh": {"so": len(canh_ra), "moc": canh_ra,
                     "moc_moi_phut": round(len(canh_ra) / max(0.01, phut), 1)},
        "im_goc": {"so": len(im_moc), "moc": im_moc,
                   "moc_moi_phut": round(len(im_moc) / max(0.01, phut), 1),
                   "im_dai_nhat": round(max((b - a for a, b in im_g), default=0.0), 3)},
        "segment": {"so": len(seg_moc),
                    "moc_moi_phut": round(len(seg_moc) / max(0.01, phut), 1)},
    }
    print(f"  MỐC NEO: cắt cảnh {nguon['cat_canh']['so']} "
          f"({nguon['cat_canh']['moc_moi_phut']}/phút) · "
          f"im gốc >= {IM_GOC_MOC}s: {nguon['im_goc']['so']} "
          f"({nguon['im_goc']['moc_moi_phut']}/phút, dài nhất "
          f"{nguon['im_goc']['im_dai_nhat']}s) · "
          f"segment {nguon['segment']['so']} "
          f"({nguon['segment']['moc_moi_phut']}/phút)")

    # ---------- ĐỐI CHỨNG: arm CŨ dựng lại bằng CHÍNH bộ mô phỏng ----------
    # Mọi câu là câu neo -> mỗi câu về đúng mốc gốc = ĐÚNG cách app đang chạy.
    # Ra ~32% im thì THƯỚC CÓ RĂNG; ra 0 là phép đo hỏng, mọi số dưới vô nghĩa.
    doi_chung = mo_phong(a_moc, dai, led, lec, tong_ra,
                         set(range(len(idx))), 0.0, 0.12)
    print(f"  ĐỐI CHỨNG (mọi câu neo = arm CŨ): im {doi_chung['im_pt']}% · "
          f"{doi_chung['im_so_05']} quãng >=0,5s · dài nhất "
          f"{doi_chung['im_dai_nhat']}s · trôi max "
          f"{doi_chung['troi_max_ms']} ms")

    # ---------- LƯỚI ----------
    bo_neo = {
        "KHONG_NEO": set(),
        "CANH": neo_tu_moc(a_moc, canh_ra),
        "IM_GOC": neo_tu_moc(a_moc, im_moc),
        "CANH+IM": neo_tu_moc(a_moc, canh_ra) | neo_tu_moc(a_moc, im_moc),
    }
    # ---------- ARM 5: ĐỌC CHẬM VỪA KHUNG (trôi = 0 theo cấu tạo) ----------
    cham = []
    for c_max in (1.00, 1.10, 1.15, 1.25, 1.40, 1.60, 99.0):
        r = mo_phong_cham(a_moc, dai, led, lec, tong_ra, 0.12, c_max)
        cham.append({"cham_toi_da": c_max, **r})
    print("  ĐỌC CHẬM VỪA KHUNG (khung CỐ ĐỊNH, trôi = 0):")
    for r in cham:
        cm = "∞" if r["cham_toi_da"] > 90 else f"{r['cham_toi_da']:.2f}"
        print(f"    kéo tối đa {cm:>5}x -> im {r['im_pt']:>6.2f}% · "
              f"{r['im_so_05']:>2} quãng>=0,5s · dài nhất "
              f"{r['im_dai_nhat']:>5.2f}s · {r['so_cau_cham']:>2}/{len(dai)} "
              f"câu bị kéo · kéo TB {r['cham_tb']:.3f}x max {r['cham_max']:.3f}x")

    bang = []
    for ten_neo, neo in bo_neo.items():
        for tran in TRAN_TROI:
            for nhip in NHIP_THO:
                r = mo_phong(a_moc, dai, led, lec, tong_ra, neo, tran, nhip)
                r.pop("troi", None)
                bang.append({"neo": ten_neo, "tran_troi_s": tran,
                             "nhip_tho_s": nhip, **r})
    return {"ten": ten, "giong": giong, "so_cau": len(idx),
            "do_dai_nguon": round(k["tong"], 3), "he_so_hinh": hs,
            "do_dai_ra": round(tong_ra, 3),
            "tieng_tong": round(sum(
                max(led[i] + 0.05, dai[i] - lec[i]) - led[i]
                for i in range(len(dai))), 3),
            "nguon_moc": nguon, "doi_chung": doi_chung, "bang": bang,
            "doc_cham": cham}


def in_bang(r: dict) -> None:
    print(f"\n===== LƯỚI · {r['ten']} · {r['giong']} =====")
    print(f"| {'mốc neo':<10} | {'trần trôi':>9} | {'thở':>5} | {'im %':>6} "
          f"| {'>=0,5s':>6} | {'dài nhất':>8} | {'TRÔI max (ms)':>13} "
          f"| {'trôi>300ms':>10} | {'tràn phim':>9} |")
    print("|" + "-" * 12 + "|" + "-" * 11 + "|" + "-" * 7 + "|" + "-" * 8
          + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 15 + "|" + "-" * 12
          + "|" + "-" * 11 + "|")
    for b in r["bang"]:
        tr = "∞" if b["tran_troi_s"] > 1e8 else f"{b['tran_troi_s']:.2f}s"
        print(f"| {b['neo']:<10} | {tr:>9} | {b['nhip_tho_s']:>5.2f} "
              f"| {b['im_pt']:>6.2f} | {b['im_so_05']:>6d} "
              f"| {b['im_dai_nhat']:>8.2f} | {b['troi_max_ms']:>13.1f} "
              f"| {b['so_cau_troi_qua_300ms']:>10d} "
              f"| {b['tran_phim_giay']:>9.2f} |")


def main() -> int:
    if not NGUON_DIR.is_dir():
        print(f"KHÔNG thấy thư mục nguồn: {NGUON_DIR}")
        return 2
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    for i, p in enumerate(vids[:2]):
        kho.NGUON.append((f"lt{i + 1}", p))
    tat = []
    for ten in ("lt1", "lt2"):
        for giong in ("VNB", "EDGE"):
            try:
                r = mot_video(ten, giong)
            except Exception as e:                      # noqa: BLE001
                import traceback
                print(f"!!! {ten}/{giong} HỎNG: {type(e).__name__}: {e}")
                traceback.print_exc()
                continue
            if r:
                tat.append(r)
                in_bang(r)
                KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"\nGhi: {KQ.name}")
    return 0 if tat else 1


if __name__ == "__main__":
    raise SystemExit(main())
