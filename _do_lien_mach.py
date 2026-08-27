# -*- coding: utf-8 -*-
"""ĐỌC LIỀN HƠI — GỘP CÂU VÀO MỘT LƯỢT GỌI TTS, ĐO GHÉP CẶP 4 CỘT.

Anh Hùng nghe `_NGHE_THU_ANH_HUNG/nhan_nha_them/` rồi phán: *"CÓ NHẤN NHÁ
nhưng phải là nhấn nhá NÓI LIỀN MẠCH luôn ấy, này NGẮT QUÃNG QUÁ NHIỀU"*.

**MỆNH ĐỀ TRUNG TÂM PHẢI TÁCH LÀM ĐÔI, KHÔNG ĐƯỢC GỘP:**
  · gộp câu rồi **CẮT LẠI** đặt về mốc cũ  -> khớp hình ĐÚNG DO CẤU TẠO,
    nhưng khoảng im giữa câu **KHÔNG THỂ giảm** (mỗi câu vẫn về đúng khung
    `start` của nó, mà khung thì không đổi).
  · gộp câu rồi để **CHẢY LIỀN**           -> im giảm thật, nhưng câu thứ 2..n
    **TRÔI khỏi mốc hình**.
Đo cả hai mới nói được "gộp câu chữa được gì"; đo một cái là kết luận nửa vời.

**BỐN CỘT LUÔN ĐI CÙNG NHAU** (bỏ một cột là mở đường cho "thắng cột này thua
cột kia mà không ai biết"):
  1. **% im**       — cái anh Hùng kêu. Dựng TIMELINE ĐẦY ĐỦ rồi `silencedetect`.
  2. **nhấn nhá**   — `_do_nhan_nha.f0_nua_cung` + `pstdev` (NỬA CUNG), đo trên
     bản NỐI LIỀN các mảnh TIẾNG (bỏ khoảng im) để hai arm so được với nhau:
     im lặng không có F0 nên để im vào là đo "arm nào im nhiều hơn".
  3. **đọc sai**    — `doc_lan.soi_loat` (Theil-Sen, ngưỡng 1,5). Gộp dài dễ
     lảm nhảm; đây là bộ dò MIỄN PHÍ đã có sẵn (chỉ dùng ĐỘ DÀI).
  4. **khớp hình**  — hai số khác nhau, đừng lẫn:
       `lech_bien_ms` (arm CHẢY LIỀN) = câu trôi khỏi `start` bao nhiêu;
       `cat_vao_tieng` (arm CẮT LẠI)  = số mối cắt rơi vào chỗ ĐANG CÓ TIẾNG
       (tức cắt vào giữa chữ) — đo bằng RMS quanh mốc cắt, KHÔNG đoán.

**CHỐT CHỐNG-ĐẠT-OAN:** arm A phải ra `%im` > 0 và `cat_vao_tieng` = 0. Nếu
arm A cũng ra 0% im thì corpus không có gì để chữa -> mọi cột dưới vô nghĩa.

Chạy:  .venv\\Scripts\\python -u _do_lien_mach.py [edge|vn|kk|all]
"""
from __future__ import annotations

import json
import math
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from config import settings                                    # noqa: E402
from app.core import thay_giong as tg                          # noqa: E402
from app.core import doc_lan                                   # noqa: E402
import _do_nhan_nha as NN                                      # noqa: E402

NOWIN = 0x08000000
SAN = REPO / "bq_do_lien_mach"
KQ = REPO / "_kq_lienmach"
CACHE = REPO / "_do_lienmach_cache.json"
TG_CACHE = REPO / "_do_tg_cache.json"

#: Cửa sổ câu liền nhau. Bộ 4 câu của bảng 211 là QUÁ NGẮN để nói về ngắt
#: quãng (3 mối nối); phải đủ nhiều câu mới thấy được chỗ nối.
SO_CAU = 12
BAT_DAU = 3

#: Máy đọc. Kokoro **KHÔNG có tiếng Việt** (28/28 giọng là af_/am_/bf_/bm_)
#: nên nó chạy trên corpus TIẾNG ANH — ghi thẳng ra, đừng để ai đọc bảng
#: tưởng ba máy cùng đọc một thứ tiếng.
MAY = {
    "edge": ("vi-VN-NamMinhNeural", "vi"),
    "vn":   ("vn:Thanh Bình", "vi"),
    "kk":   ("kk:af_bella", "en"),
}

ARM = ("A", "B2_CAT", "B2_LIEN", "C4_CAT", "C4_LIEN")
GOP = {"A": 1, "B2_CAT": 2, "B2_LIEN": 2, "C4_CAT": 4, "C4_LIEN": 4}


# ───────────────────────────── thước đo ─────────────────────────────────
def _dur(p) -> float:
    r = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "error", "-show_entries",
         "format=duration", "-of", "default=nk=1:nw=1", str(p)],
        capture_output=True, text=True, creationflags=NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def khoang_im(p, nguong=-45.0, d=0.05) -> tuple[float, list]:
    tong = _dur(p)
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-i", str(p), "-af",
         f"silencedetect=n={nguong}dB:d={d}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NOWIN)
    kh, st = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", r.stderr or ""):
        if m.group(1) == "start":
            st = float(m.group(2))
        elif st is not None:
            kh.append((st, float(m.group(2))))
            st = None
    if st is not None:
        kh.append((st, tong))
    return tong, kh


def rms_quanh(p, t: float, nua: float = 0.03) -> float:
    """RMS dBFS trong cửa sổ ±`nua` giây quanh mốc `t`. Dùng để hỏi *"mối cắt
    này có rơi vào chỗ đang có tiếng không"* — KHÔNG đoán bằng mắt."""
    a = max(0.0, t - nua)
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-ss", f"{a:.3f}",
         "-t", f"{2 * nua:.3f}", "-i", str(p), "-af",
         "astats=measure_overall=RMS_level:measure_perchannel=none",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NOWIN)
    m = re.search(r"RMS level dB:\s*(-?[\d.]+|-?inf)", r.stderr or "")
    if not m:
        return -99.0
    try:
        return float(m.group(1))
    except ValueError:
        return -99.0


def nhan_nha(wav) -> tuple[float, int]:
    """(pstdev F0 theo NỬA CUNG, số mẫu) — ĐÚNG thước bảng 211, không đẻ mới."""
    f0 = NN.f0_nua_cung(wav)
    if len(f0) < 8:
        return (0.0, len(f0))
    return (statistics.pstdev(f0), len(f0))


# ─────────────────────── gộp / cắt lại theo mốc chữ ─────────────────────
def khoi_gop(n: int, k: int) -> list[list[int]]:
    return [list(range(i, min(i + k, n))) for i in range(0, n, k)]


def _chuan(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def bien_theo_moc(moc: list, texts: list[str]) -> list[float | None]:
    """Mốc BẮT ĐẦU của từng câu trong khối, suy từ MỐC TỪNG CHỮ.

    Đi theo **ký tự đã chuẩn hoá** chứ không đếm token: bộ tách từ của
    edge-tts (`WordBoundary`) và của gióng hàng (`_tach_tu`) KHÔNG cắt giống
    nhau, đếm token là lệch ngay câu đầu và lệch dồn về sau.

    Trả list cùng độ dài `texts`; phần tử `None` = không tra được (caller
    PHẢI coi đó là hỏng, đừng lấp bằng số đoán).
    """
    if not moc:
        return [None] * len(texts)
    moc = sorted(moc, key=lambda m: float(m[0]))
    # mốc luỹ kế của TỪNG chữ trong dòng ký tự đã chuẩn hoá
    dong, vitri = "", []          # vitri[j] = (hết ký tự thứ n, thời điểm bắt đầu)
    for m in moc:
        try:
            t0, w = float(m[0]), _chuan(str(m[2]))
        except (TypeError, ValueError, IndexError):
            continue
        if not w:
            continue
        vitri.append((len(dong), t0))
        dong += w
    if not vitri:
        return [None] * len(texts)
    ra: list[float | None] = []
    dat = 0
    for i, t in enumerate(texts):
        if i == 0:
            ra.append(vitri[0][1])
            dat += len(_chuan(t))
            continue
        # chữ ĐẦU TIÊN bắt đầu từ vị trí >= `dat`
        ung = [v for v in vitri if v[0] >= dat - 2]
        ra.append(ung[0][1] if ung else None)
        dat += len(_chuan(t))
    return ra


# ─────────────────────────── chạy một arm ───────────────────────────────
async def _doc(texts, voice, paths, lang):
    from app.core import dubbing
    return await dubbing._synth_all_words(texts, voice, paths, lang=lang)


def chay_arm(arm: str, cau: list[dict], texts: list[str], voice: str,
             lang: str, thu_muc: Path, tong: float) -> dict:
    """Đọc + (gộp) + cắt lề + dựng timeline + đo 4 cột."""
    import asyncio
    thu_muc.mkdir(parents=True, exist_ok=True)
    k = GOP[arm]
    lien = arm.endswith("_LIEN")
    khoi = khoi_gop(len(texts), k)

    # ── 1. GỌI MÁY ĐỌC: mỗi KHỐI một lượt (k=1 => đúng hành vi hiện tại) ──
    goi = [" ".join(texts[i] for i in kh) for kh in khoi]
    paths = [str(thu_muc / f"g_{j:03d}.mp3") for j in range(len(khoi))]
    t0 = time.time()
    ok, moc = asyncio.run(_doc(goi, voice, paths, lang))
    giay_doc = time.time() - t0

    # ── 2. CẮT LỀ IM hai đầu MỖI LƯỢT GỌI (đúng bước 4a của app) ──
    sach, _le = tg.cat_le_loat(paths, list(ok), thu_muc / "sach", moc_tu=moc)

    # ── 3. cắt khối về từng câu theo MỐC TỪNG CHỮ ──
    manh: list[dict] = []          # {i, file, dai, tre} tre = lệch so start[i]
    cat_vao_tieng = 0
    cat_tong = 0
    thieu_moc = 0
    for j, kh in enumerate(khoi):
        if j >= len(ok) or not ok[j] or not Path(sach[j]).exists():
            continue
        d_khoi = _dur(sach[j])
        if len(kh) == 1:
            manh.append(dict(i=kh[0], file=sach[j], dai=d_khoi, off=0.0))
            continue
        bien = bien_theo_moc(moc[j] if j < len(moc) else [],
                             [texts[i] for i in kh])
        if any(b is None for b in bien[1:]):
            thieu_moc += 1
            # KHÔNG đoán: giữ nguyên cả khối như một mảnh, ghi nợ
            manh.append(dict(i=kh[0], file=sach[j], dai=d_khoi, off=0.0,
                             gop_nguyen=len(kh)))
            continue
        moc_cat = [0.0] + [float(b) for b in bien[1:]] + [d_khoi]
        for z, i in enumerate(kh):
            a, b = moc_cat[z], moc_cat[z + 1]
            if b - a < 0.05:
                b = min(d_khoi, a + 0.05)
            if z > 0:                        # mối cắt có rơi vào TIẾNG không
                cat_tong += 1
                if rms_quanh(sach[j], a) > -38.0:
                    cat_vao_tieng += 1
            dst = thu_muc / f"m_{i:03d}.wav"
            subprocess.run(
                [settings.FFMPEG_PATH, "-y", "-v", "error", "-i", sach[j],
                 "-af", f"atrim=start={a:.3f}:end={b:.3f},asetpts=N/SR/TB",
                 "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(dst)],
                capture_output=True, creationflags=NOWIN)
            manh.append(dict(i=i, file=str(dst), dai=_dur(dst), off=a))

    # ── 4. DỰNG TIMELINE ĐẦY ĐỦ ──
    # CẮT LẠI  -> mỗi câu về đúng `start[i]` (khớp hình đúng do cấu tạo)
    # CHẢY LIỀN-> khối đặt ở `start` câu đầu, các câu sau trôi theo giọng đọc
    dat: list[tuple[float, str, int]] = []
    lech: list[float] = []
    if not lien:
        for m in manh:
            dat.append((float(cau[m["i"]]["start"]), m["file"], m["i"]))
    else:
        for j, kh in enumerate(khoi):
            ms = [m for m in manh if m["i"] in kh]
            if not ms:
                continue
            goc = float(cau[kh[0]]["start"])
            for m in sorted(ms, key=lambda x: x["i"]):
                t = goc + m["off"]
                dat.append((t, m["file"], m["i"]))
                lech.append(abs(t - float(cau[m["i"]]["start"])))

    noi_wav = thu_muc / f"{arm}_timeline.wav"
    _dung_timeline(dat, tong, noi_wav)

    # ── 5. bản NỐI LIỀN (bỏ im) để đo NHẤN NHÁ cho công bằng ──
    lien_wav = thu_muc / f"{arm}_lienmanh.wav"
    _noi_thang([m["file"] for m in sorted(manh, key=lambda x: x["i"])],
               lien_wav)

    # ── 6. ĐO ──
    d_tl, kh_tl = khoang_im(noi_wav)
    dau = kh_tl[0][1] if kh_tl and kh_tl[0][0] <= 0.02 else 0.0
    cuoi = (d_tl - kh_tl[-1][0]) if kh_tl and kh_tl[-1][1] >= d_tl - 0.02 else 0.0
    giua = [g for g in kh_tl if g[0] > 0.02 and g[1] < d_tl - 0.02]
    im_giua = sum(b - a for a, b in giua)
    nn_v, nn_n = nhan_nha(lien_wav)

    giay = [m["dai"] for m in sorted(manh, key=lambda x: x["i"])]
    txt = [texts[m["i"]] for m in sorted(manh, key=lambda x: x["i"])]
    try:
        soi = doc_lan.soi_loat(txt, giay)
        n_lan = sum(1 for s in soi if s)
    except Exception:                                    # noqa: BLE001
        n_lan = -1

    return dict(
        arm=arm, so_luot_goi=len(khoi), so_manh=len(manh),
        giay_doc=round(giay_doc, 2), thieu_moc=thieu_moc,
        dai_tl=round(d_tl, 2),
        im_giua=round(im_giua, 2),
        pc_im=round(100 * im_giua / d_tl, 2) if d_tl else 0.0,
        so_im=len(giua),
        im_dai_nhat=round(max((b - a for a, b in giua), default=0.0), 2),
        im_dau=round(dau, 2), im_cuoi=round(cuoi, 2),
        nhan_nha=round(nn_v, 2), nn_mau=nn_n,
        doc_lan=n_lan,
        cat_moi=cat_tong, cat_vao_tieng=cat_vao_tieng,
        lech_bien_tb=round(1000 * (sum(lech) / len(lech)), 1) if lech else 0.0,
        lech_bien_max=round(1000 * max(lech), 1) if lech else 0.0,
        wav=str(noi_wav), wav_lien=str(lien_wav),
    )


def _dung_timeline(dat, tong: float, dst: Path):
    """Đặt từng mảnh vào đúng mốc trên nền im lặng dài `tong` giây."""
    dat = sorted(dat, key=lambda x: x[0])
    if not dat:
        return
    vao, filt, lab = [], [], []
    # `-t` PHẢI là tuỳ chọn ĐẦU VÀO của anullsrc — đặt sai chỗ thì nó ghi vô
    # hạn (đã đầy ổ C 420 GB một lần).
    vao += ["-f", "lavfi", "-t", f"{tong:.3f}",
            "-i", "anullsrc=r=44100:cl=mono"]
    for n, (t, f, _i) in enumerate(dat, start=1):
        vao += ["-i", f]
        filt.append(f"[{n}:a]aresample=44100,adelay={int(t*1000)}"
                    f"|{int(t*1000)}[d{n}]")
        lab.append(f"[d{n}]")
    filt.append(f"[0:a]{''.join(lab)}amix=inputs={len(dat)+1}:"
                f"duration=first:dropout_transition=0:normalize=0[o]")
    subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-v", "error", *vao,
         "-filter_complex", ";".join(filt), "-map", "[o]",
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, creationflags=NOWIN, timeout=600)


def _noi_thang(files, dst: Path):
    files = [f for f in files if f and Path(f).exists()]
    if not files:
        return
    vao = []
    for f in files:
        vao += ["-i", str(f)]
    g = ("".join(f"[{i}:a]aresample=44100[a{i}];" for i in range(len(files)))
         + "".join(f"[a{i}]" for i in range(len(files)))
         + f"concat=n={len(files)}:v=0:a=1[o]")
    subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-v", "error", *vao,
         "-filter_complex", g, "-map", "[o]", "-ac", "1", "-ar", "44100",
         "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, creationflags=NOWIN, timeout=600)


# ───────────────────────────── corpus ───────────────────────────────────
def lay_corpus() -> tuple[list[dict], list[str], list[str]]:
    """(cau, viet, anh) — bản dịch THẬT qua Groq, cache lại để tái lập."""
    if CACHE.exists():
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        return d["cau"], d["vi"], d["en"]
    chep = json.loads(TG_CACHE.read_text(encoding="utf-8"))["chep|lt1|90.0"]
    cau = tg.cau_tu_transcript(chep)
    cua = cau[BAT_DAU:BAT_DAU + SO_CAU]
    print(f"dịch {len(cua)} câu qua Groq THẬT ...")
    vi = tg._dich_loat(cua, "vi", "zh")
    en = tg._dich_loat(cua, "en", "zh")
    d = dict(cau=cua, vi=vi, en=en)
    CACHE.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return cua, vi, en


def main(chon: str = "all"):
    KQ.mkdir(parents=True, exist_ok=True)
    cau, vi, en = lay_corpus()
    tong = float(cau[-1]["end"]) - float(cau[0]["start"]) + 1.0
    goc = float(cau[0]["start"])
    cau = [dict(c, start=float(c["start"]) - goc, end=float(c["end"]) - goc)
           for c in cau]
    print("=" * 104)
    print(f"CORPUS: {len(cau)} câu liền nhau · khung {tong:.2f}s "
          f"· ký tự/câu VI: TB {sum(len(t) for t in vi)/len(vi):.0f}")
    for i, (c, t) in enumerate(zip(cau, vi)):
        print(f"  {i:>2} [{c['start']:>6.2f}-{c['end']:>6.2f}] "
              f"{len(t):>3} kt  {t[:58]}")
    print("=" * 104)

    ten = list(MAY) if chon == "all" else [chon]
    ra = {}
    for m in ten:
        voice, lang = MAY[m]
        texts = vi if lang == "vi" else en
        print(f"\n### MÁY ĐỌC {m} = {voice}  (tiếng {lang})")
        ra[m] = {}
        for luot in (1, 2):
            for arm in ARM:
                tm = SAN / m / f"l{luot}" / arm
                try:
                    r = chay_arm(arm, cau, texts, voice, lang, tm, tong)
                except Exception as e:                    # noqa: BLE001
                    print(f"  {arm} l{luot}: HỎNG {type(e).__name__}: {e}")
                    continue
                ra[m].setdefault(arm, []).append(r)
                print(f"  {arm:<8} l{luot}  gọi {r['so_luot_goi']:>2} "
                      f"· im {r['pc_im']:>5.2f}% ({r['im_giua']:>5.2f}s/"
                      f"{r['so_im']:>2} chỗ, dài nhất {r['im_dai_nhat']:.2f}s)"
                      f" · nhấn nhá {r['nhan_nha']:>5.2f}"
                      f" · lảm nhảm {r['doc_lan']:>2}"
                      f" · cắt vào tiếng {r['cat_vao_tieng']}/{r['cat_moi']}"
                      f" · lệch biên TB {r['lech_bien_tb']:>7.1f}ms"
                      f" max {r['lech_bien_max']:>7.1f}ms"
                      f" · {r['giay_doc']:>5.1f}s")
                (KQ / "F_lien_mach.json").write_text(
                    json.dumps(ra, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    bao_cao(ra)


def bao_cao(ra: dict):
    d = []
    d.append("=" * 104)
    d.append("BẢNG F — GỘP CÂU VÀO MỘT LƯỢT GỌI TTS (ghép cặp, >=2 lượt/arm)")
    d.append("=" * 104)
    for m, arms in ra.items():
        voice, lang = MAY[m]
        d.append(f"\n### {m} = {voice}  (tiếng {lang})")
        d.append(f"{'arm':<9} {'gọi':>4} {'% im':>13} {'nhấn nhá':>15} "
                 f"{'lảm nhảm':>10} {'cắt vào tiếng':>14} {'lệch biên max':>16}")
        d.append("-" * 104)
        for arm in ARM:
            xs = arms.get(arm) or []
            if not xs:
                continue
            def dai(k, f="{:.2f}"):
                v = [x[k] for x in xs]
                return (f.format(min(v)) if min(v) == max(v)
                        else f"{f.format(min(v))}-{f.format(max(v))}")
            d.append(f"{arm:<9} {xs[0]['so_luot_goi']:>4} "
                     f"{dai('pc_im')+'%':>13} {dai('nhan_nha'):>15} "
                     f"{dai('doc_lan','{:.0f}'):>10} "
                     f"{str(max(x['cat_vao_tieng'] for x in xs))+'/'+str(max(x['cat_moi'] for x in xs)):>14} "
                     f"{dai('lech_bien_max','{:.0f}')+' ms':>16}")
    t = "\n".join(d)
    print("\n" + t)
    (KQ / "F_lien_mach.txt").write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
