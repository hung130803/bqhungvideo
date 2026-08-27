# -*- coding: utf-8 -*-
"""ĐO GHÉP CẶP: "ép tiếng cho vừa video" (CŨ) so với "chỉnh video theo giọng"
(MỚI) — trên video THẬT của anh Hùng (20/08/2026).

Anh Hùng: *"cái phần âm thanh lồng tiếng nhanh chậm để khớp khung hình à nó nói
cực kỳ chậm chỗ thì nhanh tôi muốn nó đều hoặc hơi nhanh tí ... điều chỉnh là
điều chỉnh VIDEO sao cho khớp, KHÔNG PHẢI lồng tiếng mới tạo"*.

**PHÉP SO PHẢI GHÉP CẶP, ĐỪNG ĐO RỜI HAI LƯỢT.** LLM không tiền định: CLAUDE.md
đã ghi cùng mã cùng video hai lượt lệch **1,81 lần** (82,35 s vs 45,60 s), và
commit `4d738e8` từng tố giác đúng chuyện đó (20,05 vs 30,65 s trong khi bản vá
nằm im). Nên script này chạy dây chuyền **MỘT LƯỢT cho mỗi video** tới hết bước
4c rồi TÁCH ra hai arm ở **đúng chỗ bản vá tác động** (tham số `he_so_hinh` của
`khop_thoi_gian`): hai arm dùng CÙNG bản tách / chép lời / dịch / rút gọn / FILE
GIỌNG. Mọi nhiễu LLM + nhiễu edge-tts bị triệt tiêu **theo cấu tạo**.

**THƯỚC "TRẢI TỐC ĐỘ ĐỌC" LÀ THƯỚC QUAN TRỌNG NHẤT — và nó là thước MỚI.**
`tempo_max` là số ĐỈNH: nó nói "câu tệ nhất bị ép bao nhiêu" mà **không nói gì
về ĐỘ ĐỀU**. Nếu 43 câu bị ép 1,0 · 1,4 · 1,0 · 1,3 · 1,0 … thì `tempo_max`
= 1,4 nhưng cái tai nghe ra là *"chỗ chậm chỗ nhanh"* — đó là ĐỘ TRẢI, không
phải đỉnh. Thước ở đây: **ký tự/giây của TỪNG CÂU** đo trên chính file đã khớp
(`moc_tieng` = mốc nói thật, đo bằng `silencedetect`), rồi lấy **độ lệch chuẩn**
và **hệ số biến thiên** giữa các câu. Kèm SÀN ĐỐI CHỨNG: cùng phép đo trên file
TTS THÔ (chưa khớp) — đó là phần trải VỐN CÓ của máy đọc, hai arm dùng chung,
nên phần vượt trên sàn đó mới là phần do co giãn tiếng sinh ra.

**MÉO PHỔ dùng ĐÚNG thước của `_do_rubberband.py`** (log-mel, vòng tròn `k` rồi
`1/k`) để số so được với mốc CLAUDE.md đã ghi: `atempo` **5,357 dB ở 1,20** ·
6,765 ở 1,50. Không viết thước thứ hai — hai thước là hai bảng số không so được.

Nguồn: `C:\\Users\\Admin\\Downloads\\longtieng\\` — **CHỈ ĐỌC**, chỉ cắt ra bản
sao trong thư mục làm việc của repo.

    .venv\\Scripts\\python -u _do_khop_video.py [số video] [số giây/video]
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
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

import _do_kho_tg as kho                              # noqa: E402
import _do_rubberband as rb                           # noqa: E402
from config import settings                           # noqa: E402
from app.core import thay_giong as tg                 # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
LAM = REPO / "_do_kv_tam"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "khop_video"
KQ = REPO / "_kq_khop_video.json"
DICH_SANG = "vi"          # nguồn Douyin tiếng Trung -> tiếng Việt (ca thật)
_NW = 0x0800_0000 if os.name == "nt" else 0

#: GIỌNG là biến THỨ HAI (27/08/2026). `vnb:` = ĐÚNG đường anh Hùng đi — nhật
#: ký `giong_vieneu_20260827.log` ghi 15 lượt `vnb:...\_mau_giong\test.wav` và
#: 14 lượt `adam_clone.wav` trong đúng khung giờ 4 video trong `xuất` ra đời.
#: **KHÔNG dùng `adam_clone.wav`** (bản sao một giọng ElevenLabs thương mại) —
#: ranh giới cứng của repo, nên lấy mẫu còn lại mà anh Hùng cũng đã chạy.
#: edge-tts là **TRẦN ĐỐI CHỨNG BẮT BUỘC**: không có nó thì "12 khoảng im" là
#: con số vô nghĩa (không biết bao nhiêu là của cấu trúc câu, bao nhiêu của
#: máy đọc).
_MAU_VNB = (Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo"
            / "_mau_giong" / "test.wav")
GIONG: list[tuple[str, str]] = [("EDGE", "")]
if os.environ.get("BQ_KV_VNB", "1") != "0" and _MAU_VNB.exists():
    GIONG.append(("VNB", f"vnb:{_MAU_VNB}"))


# ══════════════════════════ hạ tầng đo ══════════════════════════
def _probe(path: Path, ent: str, dong: str = "v:0") -> str:
    a = [settings.FFPROBE_PATH, "-v", "error"]
    if dong:
        a += ["-select_streams", dong]
    a += ["-show_entries", ent, "-of", "csv=p=0", str(path)]
    r = subprocess.run(a, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NW, timeout=600)
    return (r.stdout or "").strip().rstrip(",")


def _f(path: Path, ent: str, dong: str = "v:0") -> float:
    try:
        return float(_probe(path, ent, dong) or 0)
    except ValueError:
        return 0.0


def _lech(xs: list[float]) -> tuple[float, float, float]:
    """(trung bình, độ lệch chuẩn, hệ số biến thiên %)."""
    if len(xs) < 2:
        return (xs[0] if xs else 0.0), 0.0, 0.0
    tb = statistics.fmean(xs)
    sd = statistics.pstdev(xs)
    return tb, sd, (100.0 * sd / tb if tb else 0.0)


def toc_do_doc(texts: list[str], moc: list, cau: list[dict]) -> list[float]:
    """KÝ TỰ/GIÂY của TỪNG CÂU, đo trên mốc NÓI THẬT của file đã khớp.

    `moc` = `khop_thoi_gian()["moc_tieng"]` = [(i, giây_BẮT_ĐẦU_NÓI,
    giây_HẾT_NÓI)] — đo bằng `silencedetect` trên chính file vừa ghi, nên nó
    KHÔNG tính phần im lặng hai đầu vào mẫu số. Dùng `probe_duration` ở đây là
    đo cả lề im (bẫy v2.27.0 đã ghi).
    """
    ra = []
    for i, a, b in moc:
        if i >= len(texts):
            continue
        n = len(str(texts[i]).strip())
        d = float(b) - float(a)
        if n >= 8 and d > 0.25:      # câu quá ngắn -> tỉ số nhiễu, bỏ
            ra.append(n / d)
    return ra


#: bề rộng khoảng im mà tai nghe ra là "được đoạn rồi nghỉ"
BAC_IM = (0.5, 1.0, 2.0)


def im_giua_cau(moc: list, tong_ra: float) -> dict:
    """KHOẢNG IM **GIỮA HAI CÂU LIỀN NHAU** trên luồng tiếng lồng.

    **VÌ SAO THƯỚC NÀY RA ĐỜI (anh Hùng 27/08/2026):** *"nó nói còn KHÔNG LIÊN
    TIẾP, cứ ĐƯỢC ĐOẠN RỒI NGHỈ, KHÔNG LIỀN MẠCH"*. Mọi thước có sẵn trong
    repo đều đo **BÊN TRONG một câu** (`tempo_max`, trải ký tự/giây, méo phổ)
    hoặc đo **từng file WAV RỜI** — mà file rời thì **không có khoảng cách
    giữa các câu để mà đo**. Đó đúng là chỗ 4 lượt đo trước bỏ sót.

    Nguồn số: `khop_thoi_gian()["moc_tieng"]` = [(i, giây_BẮT_ĐẦU_NÓI,
    giây_HẾT_NÓI)] trên **TRỤC ĐẦU RA**, đo bằng `silencedetect` trên chính
    file đã ghi. Nên đây là khoảng im trên BẢN ĐÃ GHÉP, không phải trên file
    rời — và nó KHÔNG tính lề im còn sót trong từng file (bẫy `probe_duration`
    của v2.27.0).

    `im_dau`/`im_cuoi` tách riêng: hai đầu phim im là chuyện khác hẳn, gộp vào
    là làm loãng con số ở giữa.
    """
    ms = sorted((float(a), float(b)) for _i, a, b in (moc or []))
    tr = {"so_cau_do": len(ms), "im_giua_tong": 0.0, "im_giua_so": 0,
          "im_giua_dai_nhat": 0.0, "im_giua_tb": 0.0, "im_giua_pt": 0.0,
          "ti_le_co_tieng": 0.0, "im_dau": 0.0, "im_cuoi": 0.0,
          **{f"im_giua_so_{int(m * 10):02d}": 0 for m in BAC_IM}}
    if not ms:
        return tr
    kho: list[float] = []
    for (_a0, b0), (a1, _b1) in zip(ms, ms[1:]):
        g = a1 - b0
        if g > 0.0:
            kho.append(g)
    noi = sum(b - a for a, b in ms)
    tr["im_giua_tong"] = round(sum(kho), 3)
    tr["im_giua_so"] = sum(1 for g in kho if g >= 0.05)
    for m in BAC_IM:
        tr[f"im_giua_so_{int(m * 10):02d}"] = sum(1 for g in kho if g >= m)
    tr["im_giua_dai_nhat"] = round(max(kho), 3) if kho else 0.0
    tr["im_giua_tb"] = round(sum(kho) / len(kho), 3) if kho else 0.0
    tr["im_giua_pt"] = round(100.0 * sum(kho) / max(0.001, tong_ra), 2)
    tr["ti_le_co_tieng"] = round(100.0 * noi / max(0.001, tong_ra), 2)
    tr["im_dau"] = round(max(0.0, ms[0][0]), 3)
    tr["im_cuoi"] = round(max(0.0, tong_ra - ms[-1][1]), 3)
    return tr


def meo_pho(files: list[str], tempos: list[float], lam: Path) -> dict:
    """Méo phổ do CO GIÃN TIẾNG, thước log-mel của `_do_rubberband.py`.

    Đo bằng **vòng tròn `k` rồi `1/k`** trên CHÍNH file giọng của lượt này: đó
    là cách duy nhất so được hai file CÙNG ĐỘ DÀI (co giãn xong thì độ dài đổi,
    log-mel không căn được). Số ra vì thế **so được với mốc CLAUDE.md**
    (`atempo` 5,357 dB ở 1,20).

    Câu nào tempo = 1,0 thì app KHÔNG áp filter nào -> méo **0,000 theo cấu
    tạo**; vẫn đo để bảng có số thật chứ không phải lời khai.
    """
    lam.mkdir(parents=True, exist_ok=True)
    ds, so_ep = [], 0
    for i, (p, k) in enumerate(zip(files, tempos)):
        if not p or not Path(p).exists():
            continue
        if abs(k - 1.0) <= 1e-3:
            ds.append(0.0)
            continue
        so_ep += 1
        a = lam / f"m{i:04d}_a.wav"
        b = lam / f"m{i:04d}_b.wav"
        try:
            rb.ff(["-i", str(p), "-af", tg._co_gian_chuoi(k), "-ac", "1",
                   "-ar", "16000", "-c:a", "pcm_s16le", str(a)])
            rb.ff(["-i", str(a), "-af", tg._co_gian_chuoi(1.0 / k), "-ac", "1",
                   "-ar", "16000", "-c:a", "pcm_s16le", str(b)])
            v = rb.lech_db(Path(p), b)
            if v >= 0:
                ds.append(v)
        except Exception as e:                          # noqa: BLE001
            print(f"    (méo phổ câu #{i} bỏ qua: {type(e).__name__})")
    tb, sd, _ = _lech(ds)
    return {"meo_db_tb": round(tb, 3),
            "meo_db_max": round(max(ds), 3) if ds else 0.0,
            "so_cau_bi_ep": so_ep, "so_cau_do": len(ds)}


# ══════════════════════════ một arm ══════════════════════════
def mot_arm(ten: str, k: dict, dd: dict, rg: dict, dn: dict, hs: float,
            lam: Path, tach: dict, nhan: str = "") -> dict:
    """Chạy từ bước 5 tới file video, với `he_so_hinh = hs`."""
    lam.mkdir(parents=True, exist_ok=True)
    cau, tong = k["cau"], k["tong"]
    t0 = time.time()
    kh = tg.khop_thoi_gian(cau, dn["files"], dn["ok"], tong, lam / "khop",
                           moc_tu=dn.get("moc_tu"), he_so_hinh=hs)
    tong_ra = tong * hs

    # LỚP NỀN phải giãn theo hình — y đường thật (`thay_giong_video`)
    nhac = tach["nhac"]
    if hs > 1.0 + 1e-6:
        nh = lam / "nhac_gian.wav"
        tg._ffmpeg(["-i", str(nhac), "-af",
                    f"{tg._co_gian_chuoi(1.0 / hs)},aresample={tg.SR_TACH},"
                    f"apad,atrim=0:{tong_ra:.3f},asetpts=N/SR/TB",
                    "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                    str(nh)], "giãn lớp nhạc theo hệ số hình")
        nhac = str(nh)

    manh = list(kh["manh"])
    bu = {}
    try:
        bu = tg.bu_giong_goc(tach.get("giong") or "", kh["manh"], tong_ra,
                             lam / "bu_goc", he_so_hinh=hs)
        manh += bu["manh"]
    except Exception as e:                              # noqa: BLE001
        bu = {"ok": False, "loi": f"{type(e).__name__}: {e}"[:120]}

    au = tg.tron_thay_giong(nhac, manh, tong_ra, lam / "tieng.wav",
                            goc_wav=k["wav"])
    dong_chu = tg.dong_chu_theo_giong(kh.get("moc_tieng") or [], rg["texts"],
                                      moc_tu=kh.get("moc_tu"))
    ra = lam / f"{nhan or ('MOI' if hs > 1.0 + 1e-6 else 'CU')}_{ten}.mp4"
    tg.thay_audio_video(k["video"], au["ra"], ra, che_chu=False,
                        dong_chu=dong_chu, he_so_hinh=hs)
    kiem = tg.kiem_video_ra(ra, tong_ra)

    # ---------- SỐ ĐO ----------
    tem = list(kh["tempo_cau"])
    td_khop = toc_do_doc(rg["texts"], kh.get("moc_tieng") or [], cau)
    tb_k, sd_k, cv_k = _lech(td_khop)
    mp = meo_pho(dn["files"], tem, lam / "meo")
    # THƯỚC MỚI 27/08/2026 — xem `im_giua_cau`. Đo trên `moc_tieng` của CHÍNH
    # lượt khớp này, tức trên TRỤC ĐẦU RA đã nhân `k`; nên số của arm chỉnh
    # hình phải to lên đúng phần `(k−1)` mà phép giãn ĐỀU rót vào chỗ đang im.
    ig = im_giua_cau(kh.get("moc_tieng") or [], tong_ra)
    do_to = tg.do_do_to(au["ra"])

    kv = int(_probe(ra, "stream=nb_read_packets").split()[0] or 0) \
        if False else tg.do_khung_hinh(ra)
    kn = tg.do_khung_hinh(k["video"])
    d_hinh = _f(ra, "stream=duration", "v:0") or _f(ra, "format=duration", "")
    d_tieng = _f(ra, "stream=duration", "a:0")

    return {
        "he_so_hinh": round(hs, 4),
        "giay_chay": round(time.time() - t0, 1),
        "tempo_max": kh["tempo_max"],
        "tempo_tb": kh["tempo_tb"],
        "tempo_trai": kh["tempo_trai"],
        "so_cau": kh["so_cau"],
        "so_cau_ep": kh["so_cau_ep"],
        "so_qua_120": sum(1 for t in tem if t > 1.20),
        "so_qua_130": sum(1 for t in tem if t > 1.30),
        "so_qua_140": sum(1 for t in tem if t > 1.40),
        "so_cau_cat": kh.get("so_cau_cat", 0),
        "kytu_giay_tb": round(tb_k, 2),
        "kytu_giay_sd": round(sd_k, 3),
        "kytu_giay_cv": round(cv_k, 2),
        "kytu_giay_n": len(td_khop),
        **ig,
        **mp,
        "chong_lan_ms_max": kh["chong_lan_ms_max"],
        "so_cau_chong_lan": kh["so_cau_chong_lan"],
        "lech_dau_ms_tb": kh["lech_dau_ms_tb"],
        "im_duoi_chu_ms_tb": kh["im_duoi_chu_ms_tb"],
        "im_duoi_chu_giay_tong": kh["im_duoi_chu_giay_tong"],
        "so_cau_im_duoi_1s": kh["so_cau_im_duoi_1s"],
        "so_dong_chu": len(dong_chu),
        "khung_vao": kn, "khung_ra": kv,
        "do_dai_hinh": round(d_hinh, 3),
        "do_dai_tieng": round(d_tieng, 3),
        "lech_hinh_tieng_ms": round(abs(d_hinh - d_tieng) * 1000.0, 1),
        "do_dai_dich": round(tong_ra, 3),
        "lufs_I": round(do_to.get("I", 0.0), 2),
        "lufs_TP": round(do_to.get("TP", 0.0), 2),
        "kiem_video_ra": kiem,
        "bu_goc_giay": bu.get("giay_bu"),
        "ra": str(ra),
    }


def mot_video(ten: str, giay: float) -> dict:
    print(f"\n{'#' * 72}\n##### {ten} #####")
    k = kho.chuan_bi(ten)
    lam = LAM / ten
    if lam.exists():
        shutil.rmtree(lam, ignore_errors=True)
    lam.mkdir(parents=True, exist_ok=True)

    # --- bước 1: TÁCH (đắt, tiền định) — cache theo video ---
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

    # ===== PHẦN DÙNG CHUNG — chạy ĐÚNG MỘT LƯỢT =====
    # **BẤM GIỜ TỪNG BƯỚC ĐỌC** — đây là cột anh Hùng kêu ("tốc độ làm lồng
    # tiếng cực kỳ chậm") và nó ghép cặp THEO CẤU TẠO: cả ba arm dùng CHUNG
    # bước 4a/4b, arm MỚI-3 (bản vá `doc_deu`) chỉ khác ở chỗ **không chạy 4c**.
    # Nên "nhanh hơn bao nhiêu" = ĐÚNG BẰNG giây của 4c đo trong CHÍNH lượt
    # này, không phải hiệu hai lượt chạy rời (LLM không tiền định — CLAUDE.md
    # ghi hai lượt cùng mã lệch 1,81 lần).
    t0 = time.time()
    dd = tg.dich_hau_kiem(k["cau"], DICH_SANG, goc_ma)
    g_dich = time.time() - t0

    # **MỘT bản dịch DÙNG CHUNG cho MỌI GIỌNG.** Giọng là biến THỨ HAI của
    # phép đo (27/08/2026): `vnb:` = đúng đường anh Hùng đi · edge-tts = TRẦN
    # ĐỐI CHỨNG. Dịch lại cho từng giọng là để LLM đổi độ dài câu -> đổi
    # `he_so_hinh_can` -> đổi luôn KHOẢNG IM đang đo. Ghép cặp theo CẤU TẠO.
    ra_giong: list[dict] = []
    for _nhan, _v in GIONG:
        try:
            ra_giong.append(mot_giong(ten, k, lam, tach, goc_ma, dd, g_dich,
                                      _v, _nhan))
        except Exception as e:                          # noqa: BLE001
            import traceback
            print(f"\n!!! giọng {_nhan} HỎNG: {type(e).__name__}: {e}")
            traceback.print_exc()
    return ra_giong


def mot_giong(ten: str, k: dict, lam0: Path, tach: dict, goc_ma: str,
              dd: dict, g_dich: float, giong_ma: str, nhan: str) -> dict:
    """Bước 4 -> 3 arm, cho MỘT giọng. `dd` (bản dịch) DÙNG CHUNG mọi giọng."""
    lam = lam0 / f"g_{nhan}"
    lam.mkdir(parents=True, exist_ok=True)
    print(f"\n{'=' * 68}\n=== GIỌNG {nhan}"
          f"  ({giong_ma or 'edge-tts theo ngôn ngữ'}) ===")

    t0 = time.time()
    tts = tg.doc_ban_dich(dd["ban_dich"], lam / "tts", giong_ma, DICH_SANG)
    g_4a = time.time() - t0

    t0 = time.time()
    rg = tg.rut_gon_vua_khung(k["cau"], dd["ban_dich"], tts, k["tong"],
                              lam / "rutgon", DICH_SANG, tts["voice"])
    g_4b = time.time() - t0

    t0 = time.time()
    dn = tg.doc_nhanh_vua_khung(k["cau"], rg["texts"], rg["files"], rg["ok"],
                                k["tong"], lam / "docnhanh", DICH_SANG,
                                tts["voice"], moc_tu=rg.get("moc_tu"))
    g_4c = time.time() - t0

    g_doc_cu = g_4a + g_4b + g_4c            # arm CŨ và arm MỚI
    g_doc_deu = g_4a + g_4b                  # arm MỚI-3 (bỏ 4c)
    print(f"  dùng chung xong: giọng {tts['voice']}"
          f" · rút gọn {rg['so_sua']} câu · đọc nhanh lại {dn['so_doc_lai']}"
          f" câu (rate max +{dn['rate_max']}%)")
    pt = (100.0 * g_4c / g_doc_cu) if g_doc_cu > 0 else 0.0
    print(f"  GIÂY BƯỚC ĐỌC: 4a đọc {g_4a:.1f}s · 4b rút gọn {g_4b:.1f}s · "
          f"4c đọc nhanh {g_4c:.1f}s")
    print(f"    -> CŨ {g_doc_cu:.1f}s  vs  ĐỀU {g_doc_deu:.1f}s  =  "
          f"BỚT {g_4c:.1f}s ({pt:.1f}%)")
    print(f"  (dịch: {g_dich:.1f}s — CHUNG cả ba arm, không đổi)")

    # SÀN ĐỐI CHỨNG: trải tốc độ đọc VỐN CÓ của máy đọc, trên file TTS THÔ.
    # Hai arm dùng CHUNG bộ file này nên phần trải vượt trên sàn mới là phần
    # do co giãn tiếng sinh ra. Không có sàn thì không đọc được cột trải.
    tho = []
    for i, p in enumerate(dn["files"]):
        if not p or not Path(p).exists() or i >= len(rg["texts"]):
            continue
        le_d, le_c, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        d = tg.probe_duration(p) - le_d - le_c
        n = len(str(rg["texts"][i]).strip())
        if n >= 8 and d > 0.25:
            tho.append(n / d)
    tb_t, sd_t, cv_t = _lech(tho)
    print(f"  SÀN (TTS thô, chưa khớp): {tb_t:.2f} ký tự/giây · "
          f"SD {sd_t:.3f} · CV {cv_t:.2f}%  ({len(tho)} câu)")

    # ===== TÁCH HAI ARM ở ĐÚNG chỗ bản vá tác động =====
    _c = tg.he_so_hinh_can(k["cau"], dn["files"], dn["ok"], k["tong"])
    fps = tg.do_fps(k["video"])
    tran = tg.tran_hinh_theo_fps(fps)
    hs = max(1.0, min(float(_c["k_can"]), tran))
    print(f"  hệ số hình: cần {_c['k_can']} · fps nguồn {fps:.3f} · "
          f"trần {tran:.4f} -> DÙNG {hs:.4f}"
          + ("  [CHẠM TRẦN -> phần dư vẫn phải ép tiếng]"
             if float(_c["k_can"]) > tran + 1e-6 else ""))

    cu = mot_arm(ten, k, dd, rg, dn, 1.0, lam / "arm_cu", tach, "CU")
    moi = mot_arm(ten, k, dd, rg, dn, hs, lam / "arm_moi", tach, "MOI")

    # ===== ARM THỨ BA — **BỎ BƯỚC 4C** khi đã chỉnh hình =====
    # LÝ DO CÓ ARM NÀY (đo lt1 mới lôi ra, không phải ý tưởng suy đoán): trải
    # tốc độ đọc của arm CŨ (CV 20,45%) và arm MỚI (20,49%) đo ra **BẰNG SÀN**
    # (TTS thô 20,48%) -> phần "chỗ chậm chỗ nhanh" **KHÔNG do `atempo`**, nó
    # đã nằm sẵn trong bộ file TTS. Nguồn của nó là bước 4c
    # `doc_nhanh_vua_khung`: nó đọc LẠI 22/35 câu với `rate` KHÁC NHAU (tới
    # **+43%**), mỗi câu một tốc độ. Arm MỚI không chữa được vì
    # `he_so_hinh_can` tính SAU 4c, tức nó chỉ đi khớp hình với một bộ tiếng
    # ĐÃ nhấp nhô.
    # Arm này khớp hình với bộ file TRƯỚC 4c (`rg["files"]` = tốc độ TỰ NHIÊN
    # của máy đọc). Nếu trải TỤT thật thì đó mới là bản chữa đúng bệnh anh
    # Hùng nghe ra; nếu không thì giả thuyết SAI và phải nói ra.
    #
    # **DÒNG DƯỚI PHẢI GIỐNG NHÁNH `_deu` TRONG `thay_giong_video`.** Bản vá
    # `doc_deu=True` dựng đúng dict này (`files`/`ok`/`moc_tu` lấy thẳng từ
    # `rg`) thay cho lời gọi 4c — nên arm MỚI-3 ở đây ĐO ĐÚNG đường mã anh
    # Hùng sẽ chạy khi chọn mục thứ ba. Ai đổi một bên phải đổi cả bên kia;
    # cổng 89 mục 9o canh phía app (bước 4c chạy 0 lần).
    dn3 = {"files": rg["files"], "ok": rg["ok"], "moc_tu": rg.get("moc_tu")}
    _c3 = tg.he_so_hinh_can(k["cau"], rg["files"], rg["ok"], k["tong"])
    hs3 = max(1.0, min(float(_c3["k_can"]), tran))
    print(f"  arm 3 (bỏ 4c): hệ số cần {_c3['k_can']} · trần {tran:.4f} -> "
          f"DÙNG {hs3:.4f}"
          + ("  [CHẠM TRẦN -> phần dư vẫn phải ép tiếng]"
             if float(_c3["k_can"]) > tran + 1e-6 else ""))
    moi3 = mot_arm(ten, k, dd, rg, dn3, hs3, lam / "arm_moi3", tach, "MOI3")

    # ---- file NGHE THỬ (cùng một lượt chạy, cùng -14 LUFS) ----
    ra = NGHE / ten / nhan
    ra.mkdir(parents=True, exist_ok=True)
    for arm in (cu, moi, moi3):
        p = Path(arm["ra"])
        if p.exists():
            shutil.copy2(p, ra / p.name)
            arm["nghe_thu"] = str(ra / p.name)

    return {"ten": ten, "do_dai": round(k["tong"], 2),
            "nhan_giong": nhan, "giong_ma": giong_ma,
            "moi3": moi3,
            # ---- GIÂY BƯỚC ĐỌC (ghép cặp trong CHÍNH lượt này) ----
            "giay_dich": round(g_dich, 2),
            "giay_4a_doc": round(g_4a, 2),
            "giay_4b_rutgon": round(g_4b, 2),
            "giay_4c_docnhanh": round(g_4c, 2),
            "giay_doc_cu": round(g_doc_cu, 2),
            "giay_doc_deu": round(g_doc_deu, 2),
            "giay_bot": round(g_4c, 2),
            "phan_tram_bot": round(pt, 2),
            "k_can_bo_4c": _c3["k_can"], "k_dung_bo_4c": round(hs3, 4),
            "cham_tran_bo_4c": float(_c3["k_can"]) > tran + 1e-6,
            "so_cau_doc_nhanh": dn.get("so_doc_lai"),
            "rate_max_4c": dn.get("rate_max"),
            "so_cau": len(k["cau"]), "ngon_ngu": goc_ma,
            "fps_nguon": round(fps, 3), "tran_fps": round(tran, 4),
            "k_can": _c["k_can"], "k_dung": round(hs, 4),
            "cham_tran": float(_c["k_can"]) > tran + 1e-6,
            "san_kytu_giay_tb": round(tb_t, 2),
            "san_kytu_giay_sd": round(sd_t, 3),
            "san_kytu_giay_cv": round(cv_t, 2),
            "giong": tts["voice"], "cu": cu, "moi": moi}


# ══════════════════════════ bảng ══════════════════════════
_HANG = [
    # ---- IM GIỮA CÂU: lời kêu 27/08 "được đoạn rồi nghỉ, không liền mạch" ----
    ("IM GIỮA CÂU: tổng (giây)", "im_giua_tong", "{:.2f}"),
    ("IM GIỮA CÂU: % thời lượng", "im_giua_pt", "{:.2f}"),
    ("IM GIỮA CÂU: số khoảng >= 0,5 s", "im_giua_so_05", "{:d}"),
    ("IM GIỮA CÂU: số khoảng >= 1,0 s", "im_giua_so_10", "{:d}"),
    ("IM GIỮA CÂU: số khoảng >= 2,0 s", "im_giua_so_20", "{:d}"),
    ("IM GIỮA CÂU: dài nhất (giây)", "im_giua_dai_nhat", "{:.2f}"),
    ("IM GIỮA CÂU: trung bình (giây)", "im_giua_tb", "{:.3f}"),
    ("TỈ LỆ THỜI GIAN CÓ TIẾNG %", "ti_le_co_tieng", "{:.2f}"),
    ("im ĐẦU phim (giây)", "im_dau", "{:.2f}"),
    ("im CUỐI phim (giây)", "im_cuoi", "{:.2f}"),
    ("`tempo_max` (hệ số ép cao nhất)", "tempo_max", "{:.3f}"),
    ("số câu phải ép quá 1,30", "so_qua_130", "{:d}"),
    ("số câu phải ép quá 1,20", "so_qua_120", "{:d}"),
    ("TRẢI hệ số ép (max − min)", "tempo_trai", "{:.3f}"),
    ("TỐC ĐỘ ĐỌC: ký tự/giây TB", "kytu_giay_tb", "{:.2f}"),
    ("TỐC ĐỘ ĐỌC: độ lệch chuẩn", "kytu_giay_sd", "{:.3f}"),
    ("TỐC ĐỘ ĐỌC: hệ số biến thiên %", "kytu_giay_cv", "{:.2f}"),
    ("méo phổ do co giãn tiếng (dB TB)", "meo_db_tb", "{:.3f}"),
    ("méo phổ CAO NHẤT (dB)", "meo_db_max", "{:.3f}"),
    ("chồng lấn max (ms)", "chong_lan_ms_max", "{:.1f}"),
    ("số câu chồng lấn", "so_cau_chong_lan", "{:d}"),
    ("lệch chữ so tiếng: chữ chạy khi hết tiếng (giây)",
     "im_duoi_chu_giay_tong", "{:.2f}"),
    ("lệch mốc đầu câu TB (ms)", "lech_dau_ms_tb", "{:.1f}"),
    ("số câu bị CẮT đuôi", "so_cau_cat", "{:d}"),
    ("hệ số làm chậm video", "he_so_hinh", "{:.3f}"),
    ("số khung VÀO", "khung_vao", "{:d}"),
    ("số khung RA", "khung_ra", "{:d}"),
    ("độ dài HÌNH (s)", "do_dai_hinh", "{:.3f}"),
    ("độ dài TIẾNG (s)", "do_dai_tieng", "{:.3f}"),
    ("lệch hình vs tiếng (ms)", "lech_hinh_tieng_ms", "{:.1f}"),
    ("độ to I (LUFS)", "lufs_I", "{:.2f}"),
    ("đỉnh thật TP (dBTP)", "lufs_TP", "{:.2f}"),
    ("giây chạy (bước 5 -> file)", "giay_chay", "{:.1f}"),
]


def in_bang(r: dict) -> None:
    cu, moi, moi3 = r["cu"], r["moi"], r.get("moi3") or {}
    print(f"\n===== BẢNG GHÉP CẶP · {r['ten']} · GIỌNG {r.get('nhan_giong')}"
          f" ({r.get('giong')}) · {r['do_dai']}s · "
          f"{r['so_cau']} câu · {r['ngon_ngu']} -> {DICH_SANG} =====")
    print(f"| {'chỉ số':<48} | {'arm CŨ (ép tiếng)':>18} | "
          f"{'arm MỚI (khớp video)':>20} | {'MỚI-3 (bỏ 4c)':>19} |")
    print(f"|{'-' * 50}|{'-' * 20}|{'-' * 22}|{'-' * 21}|")
    for nhan, khoa, dang in _HANG:
        vs = []
        for d in (cu, moi, moi3):
            v = d.get(khoa)
            vs.append(dang.format(v) if v is not None else "?")
        print(f"| {nhan:<48} | {vs[0]:>18} | {vs[1]:>20} | {vs[2]:>19} |")
    # ---- CỘT ANH HÙNG KÊU: "tốc độ làm lồng tiếng cực kỳ chậm" ----
    # Ghép cặp theo CẤU TẠO: 4a/4b dùng chung, arm MỚI-3 chỉ bớt đúng 4c.
    print(f"\n  GIÂY BƯỚC ĐỌC (ghép cặp trong CÙNG lượt chạy):")
    print(f"    4a đọc bản dịch      {r.get('giay_4a_doc'):>8.2f} s   (cả 3 arm)")
    print(f"    4b rút gọn câu dài   {r.get('giay_4b_rutgon'):>8.2f} s   "
          f"(cả 3 arm)")
    print(f"    4c đọc nhanh lại     {r.get('giay_4c_docnhanh'):>8.2f} s   "
          f"(CŨ + MỚI có · MỚI-3 BỎ)")
    print(f"    -> TỔNG bước đọc:  CŨ/MỚI {r.get('giay_doc_cu'):.2f} s  vs  "
          f"MỚI-3 {r.get('giay_doc_deu'):.2f} s  =  "
          f"BỚT {r.get('giay_bot'):.2f} s ({r.get('phan_tram_bot'):.2f}%)")
    print(f"    (dịch {r.get('giay_dich'):.2f} s — CHUNG cả 3 arm, không đổi)")
    print(f"\n  SÀN ĐỐI CHỨNG (TTS thô SAU 4c — arm CŨ và MỚI dùng chung): "
          f"{r['san_kytu_giay_tb']:.2f} ký tự/giây · "
          f"SD {r['san_kytu_giay_sd']:.3f} · CV {r['san_kytu_giay_cv']:.2f}%")
    print(f"  bước 4c đã đọc nhanh lại {r.get('so_cau_doc_nhanh')} câu, "
          f"rate max +{r.get('rate_max_4c')}% — NGHI LÀ nguồn của TRẢI")
    print(f"  hệ số hình: cần {r['k_can']} · trần {r['tran_fps']} -> "
          f"dùng {r['k_dung']}"
          + ("  [CHẠM TRẦN]" if r["cham_tran"] else ""))
    print(f"  hệ số hình nếu BỎ 4c: cần {r.get('k_can_bo_4c')} -> "
          f"dùng {r.get('k_dung_bo_4c')}"
          + ("  [CHẠM TRẦN -> phần dư vẫn phải ép tiếng]"
             if r.get("cham_tran_bo_4c") else ""))
    for t, arm in (("CŨ  ", cu), ("MỚI ", moi), ("MỚI3", moi3)):
        kv = arm.get("kiem_video_ra") or {}
        print(f"  kiểm video ra ({t}): {kv}")


def main() -> int:
    so = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    giay = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    kho.GIAY = giay

    if not NGUON_DIR.is_dir():
        print(f"KHÔNG thấy thư mục nguồn: {NGUON_DIR}")
        return 2
    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    if not vids:
        print(f"Thư mục {NGUON_DIR} không có .mp4 nào")
        return 2
    print(f"Nguồn (CHỈ ĐỌC): {NGUON_DIR} — {len(vids)} file, lấy {so} file "
          f"đầu, cắt {giay:g}s mỗi file")

    # `BQ_KV_BO=n` BỎ QUA n file đầu — để đo lại ĐÚNG một video mà không phải
    # chạy lại cả mẻ. Tên `lt<i>` lấy theo chỉ số TUYỆT ĐỐI trong danh sách
    # nên khoá cache chép lời/Demucs GIỮ NGUYÊN (đổi tên là lấy bản chép lời
    # của video KHÁC mà không một dòng báo — bẫy `_do_kho_tg.DU_PHONG`).
    bo = int(os.environ.get("BQ_KV_BO", "0") or 0)
    tens = []
    for i, p in enumerate(vids):
        if i < bo or len(tens) >= so:
            continue
        ten = f"lt{i + 1}"
        kho.NGUON.append((ten, p))     # chỉ trong TIẾN TRÌNH NÀY
        tens.append(ten)
        print(f"  {ten} <- {p.name}")

    print(f"Giọng đo lượt này: {[g[0] for g in GIONG]}")
    tat = []
    for ten in tens:
        try:
            for r in mot_video(ten, giay):
                tat.append(r)
                in_bang(r)
                # GHI NGAY SAU MỖI ARM/GIỌNG — lượt chạy bị giết thì vẫn còn số
                KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        except Exception as e:                          # noqa: BLE001
            import traceback
            print(f"\n!!! {ten} HỎNG: {type(e).__name__}: {e}")
            traceback.print_exc()

    if tat:
        KQ.write_text(json.dumps(tat, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        print(f"\nGhi: {KQ.name} · file nghe thử: {NGHE}")
    return 0 if tat else 1


if __name__ == "__main__":
    sys.exit(main())
