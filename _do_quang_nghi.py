"""QUÃNG NGHỈ SAU KHI TẮT BÙ GIỌNG GỐC: **IM HẲN HAY CÓ NHẠC NỀN?**
(28/08/2026 — câu hỏi anh Hùng cần trả lời trước khi duyệt v2.48.0)

Lượt trước ghi *"tắt bù -> 28,98 giây im"*. Con số đó **CHƯA ĐỦ**: ở cách trộn
"tách nhạc" thì **LỚP NHẠC NỀN vẫn chạy suốt video**, nên "không có giọng" và
"im lặng" là HAI CHUYỆN KHÁC NHAU. Script này đo trên **BẢN TRỘN CUỐI** (đúng
thứ tai anh Hùng nghe), không đo trên lớp giọng.

**ĐO GHÉP CẶP — MỘT lượt dây chuyền, hai arm tách ra ĐÚNG chỗ bản vá tác động**
(`manh_tron = kh["manh"] + bu["manh"]`), nên hai arm dùng CHUNG bản tách /
chép lời / dịch / FILE GIỌNG. Đo rời hai lượt là vô nghĩa: LLM + VieNeu không
tiền định, mốc cũ đã lệch **1,81 lần** trên CÙNG bản mã.

  · `TG.bu_giong_goc` bị bọc: app gọi `chi_do=True` (đo, không cắt) thì bọc
    chạy THÊM một lượt `chi_do=False` bằng CHÍNH hàm đó, cùng tham số -> mảnh
    bù THẬT của arm TRƯỚC.
  · `TG.tron_thay_giong` bị bọc: trộn HAI LẦN từ cùng lớp nhạc, cùng danh sách
    câu, cùng mọi tham số — chỉ khác `+ manh_bu`.

**THƯỚC:**
  (1) mức dB TRONG ĐÚNG các quãng đó trên **bản trộn cuối**, so với nền TB cả
      video (`duong_bao_muc` — chính bộ đo của app, bước 0,05 s).
  (2) "còn tiếng Trung không" bằng **ASR**, KHÔNG bằng RMS, và **CÓ SÀN BỊA**:
      lượt trước chép cả bản trộn ép `language=zh` ra 94,99% chữ Hán trên file
      KHÔNG có một mẩu tiếng gốc nào. Cách đúng: nối RIÊNG vật liệu rồi chép,
      để `language` TỰ NHẬN. Chạy phép đó cho CẢ HAI arm:
        · arm TRƯỚC: nối 31 mảnh bù  -> phải ra tiếng TRUNG (thước CÓ RĂNG)
        · arm SAU:   cắt ĐÚNG 31 cửa sổ đó khỏi bản trộn cuối rồi nối
                     -> đây vừa là phép đo vừa là SÀN BỊA

**KHÔNG ĐỤNG VIDEO GỐC:** chép sang hộp cát rồi làm trên bản sao.

    .venv\\Scripts\\python -u _do_quang_nghi.py [1|2|1,2]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics as st
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ["WHISPER_PROVIDER"] = "groq"
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

GOC = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = Path(r"D:\claude\_hop_cat_quangnghi")
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "bo_tieng_trung"
KQ = REPO / "_kq_quang_nghi.json"

#: ĐỌC THẲNG TỪ QSettings CỦA ANH HÙNG (xem `_do_bu_goc_that.py`), không đoán.
GIONG = r"vnb:C:\Users\Admin\AppData\Local\BQHungVideo\_mau_giong\test.wav"
DICH = "vi"                                   # đã xác minh: TIẾNG VIỆT

VIDEO = {
    1: "#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐.mp4",
    2: "一款可以预测死亡时间的软件有多炸裂#倒忌时.mp4",
}

_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

#: Dưới mức này thì coi là IM (không nghe được trên loa điện thoại). Lấy theo
#: `thay_giong.SAN_LUFS_CHUAN_HOA = -45` — cùng ngưỡng app đã dùng để từ chối
#: nâng độ to một bản trộn "gần câm". KHÔNG đặt mò một số mới.
SAN_IM_DB = -45.0
#: Quãng được coi là CÓ NHẠC khi nó không thấp hơn nền TB cả video quá bấy
#: nhiêu dB. 6 dB = mức "vơi đi một nửa" quen dùng trong file này.
GAN_NEN_DB = 6.0

_KHO: dict = {}


def han(s: str) -> str:
    return "".join(_HAN.findall(s or ""))


def _bpv(xs, q: float) -> float:
    s = sorted(xs)
    return s[max(0, min(len(s) - 1, int(len(s) * q)))] if s else -120.0


def muc_trong(bao: list, a: float, b: float, buoc: float) -> float:
    """Mức (dBFS) TRUNG VỊ của đường bao trong cửa sổ [a, b]."""
    i0 = max(0, int(a / buoc))
    i1 = min(len(bao), max(i0 + 1, int(b / buoc)))
    lat = bao[i0:i1]
    return st.median(lat) if lat else -120.0


def noi_wav(ds: list, ra: Path) -> int:
    """Nối danh sách wav thành một file 16 kHz mono. Trả số mảnh."""
    from app.core.thay_giong import _ffmpeg
    ds = [Path(p) for p in ds if Path(p).exists()]
    if not ds:
        return 0
    lst = ra.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in ds),
                   encoding="utf-8")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst),
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(ra)],
            "nối mảnh để chép lời", timeout=900)
    return len(ds)


def cat_cua_so(wav: Path, khoang: list, thu_muc: Path) -> list:
    """Cắt ĐÚNG các cửa sổ [a, b] khỏi `wav`. Trả danh sách file."""
    from app.core.thay_giong import _ffmpeg
    thu_muc.mkdir(parents=True, exist_ok=True)
    ra = []
    for i, (a, b) in enumerate(khoang):
        p = thu_muc / f"cs_{i:04d}.wav"
        _ffmpeg(["-i", str(wav), "-af",
                 f"atrim=start={a:.3f}:end={b:.3f},asetpts=N/SR/TB",
                 "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(p)],
                f"cắt cửa sổ {a:.2f}-{b:.2f}s", timeout=300)
        if p.exists() and p.stat().st_size > 1024:
            ra.append(p)
    return ra


def chep(wav: Path) -> dict:
    """Groq chép lời, **`language` TỰ NHẬN** — ép `zh` là mở đường cho bịa."""
    from app.core import transcribe as tr
    return tr.transcribe(str(wav))


def do_chep(wav: Path, nhan: str) -> dict:
    d = chep(wav)
    txt = (d.get("text") or "").strip()
    h = han(txt)
    r = {"nhan_ngon_ngu": d.get("language"),
         "giay": round(float(d.get("duration") or 0), 2),
         "so_ky_tu": len(txt), "so_ky_tu_HAN": len(h),
         "ti_le_han": round(len(h) / len(txt), 3) if txt else 0.0,
         "trich": txt[:300]}
    print(f"    [{nhan}] nhãn={r['nhan_ngon_ngu']!r} · Hán {len(h)}/{len(txt)}"
          f" = {r['ti_le_han']*100:.1f}% · trích: {txt[:120]!r}")
    return r


# --------------------------------------------------------------- BỌC HAI CỬA
def dat_boc(TG):
    goc_bu, goc_tron = TG.bu_giong_goc, TG.tron_thay_giong

    def bu_ghi(giong_goc, manh, tong, out_dir, he_so_hinh=1.0, chi_do=False):
        r = goc_bu(giong_goc, manh, tong, out_dir,
                   he_so_hinh=he_so_hinh, chi_do=chi_do)
        if not _KHO.get("da_bu"):
            _KHO["da_bu"] = True
            _KHO["do"] = {k: v for k, v in r.items() if k != "manh"}
            # ARM TRƯỚC: CẮT THẬT bằng CHÍNH hàm đó, CÙNG mọi tham số, khác
            # đúng `chi_do` -> mảnh bù y hệt bản v2.47.1 sẽ trộn vào.
            r2 = goc_bu(giong_goc, manh, tong,
                        Path(out_dir).parent / "bu_goc_ARM_TRUOC",
                        he_so_hinh=he_so_hinh, chi_do=False)
            _KHO["manh_bu"] = list(r2.get("manh") or [])
            _KHO["cat"] = {k: v for k, v in r2.items() if k != "manh"}
            _KHO["hs"] = float(he_so_hinh or 1.0)
        return r

    def tron_ghi(nhac_wav, manh, tong, out_wav, **kw):
        # ARM SAU = ĐÚNG cái app v2.48.0 làm (không cộng mảnh bù).
        kq_sau = goc_tron(nhac_wav, manh, tong, out_wav, **kw)
        if not _KHO.get("da_tron"):
            _KHO["da_tron"] = True
            _KHO["wav_sau"] = str(out_wav)
            _KHO["tong"] = float(tong)
            out2 = Path(out_wav).with_name("tieng_moi_ARM_TRUOC.wav")
            kq_tr = goc_tron(nhac_wav, list(manh) + _KHO.get("manh_bu", []),
                             tong, out2, **kw)
            _KHO["wav_truoc"] = str(out2)
            _KHO["tron_sau"] = kq_sau
            _KHO["tron_truoc"] = kq_tr
        return kq_sau

    TG.bu_giong_goc = bu_ghi
    TG.tron_thay_giong = tron_ghi
    return goc_bu, goc_tron


def mot_video(so: int) -> dict:
    from app.core import thay_giong as TG

    ten = VIDEO[so]
    src = GOC / ten
    if not src.exists():
        return {"video": ten, "ok": False, "loi": "không có file nguồn"}
    SB.mkdir(parents=True, exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    vin = SB / f"nguon_{so}.mp4"
    if not vin.exists():
        shutil.copy2(src, vin)                  # CHỈ ĐỌC bản gốc
    lam = SB / f"lam_{so}"

    _KHO.clear()
    goc_bu, goc_tron = dat_boc(TG)
    print(f"\n{'='*78}\nVIDEO {so}: {ten}  ({TG.probe_duration(vin):.2f}s)")
    print(f"  giọng {GIONG} · đích {DICH!r} · tách nhạc · che chữ + nhấn nhá "
          f"· chỉnh hình theo giọng")
    t0 = time.time()
    try:
        r = TG.thay_giong_video(
            vin, dich_sang=DICH, voice=GIONG, thu_muc_lam=lam,
            cach_tach="auto", giu_file_tam=True,
            che_chu=True, che_chu_cach="mo", che_chu_muc=1.0, viet_chu=True,
            hinh_theo_giong=True, doc_deu=False,
            de_giong=False,                     # cách trộn "tach"
            nhan_nha=True,
            on_progress=lambda p, m: print(f"   {p*100:5.1f}% {m}"))
    finally:
        TG.bu_giong_goc, TG.tron_thay_giong = goc_bu, goc_tron
    giay = time.time() - t0
    if not r.get("ok"):
        return {"video": ten, "ok": False, "loi": str(r.get("loi"))[:400]}

    bu = r.get("bu_goc") or {}
    khoang = [tuple(x) for x in (bu.get("khoang") or [])]
    ket = {"video": ten, "ok": True, "giay_chay": round(giay, 1),
           "dai_ra_s": round(float(_KHO.get("tong") or 0), 2),
           "he_so_hinh": _KHO.get("hs"),
           "bu_goc_app_bao": bu,
           "bu_goc_cat_that": _KHO.get("cat"),
           "so_quang": len(khoang)}
    print(f"\n  XUẤT XONG {giay:.0f}s · {len(khoang)} quãng · "
          f"đã bỏ {bu.get('giay_bu')} s tiếng gốc")
    print(f"  nhãn app báo: {bu.get('nhan')!r}")

    # -------- CHỐT: hai chế độ `chi_do` phải đếm RA CÙNG MỘT SỐ
    ket["chi_do_khop_cat"] = {
        "giay_bu": (bu.get("giay_bu"), (_KHO.get("cat") or {}).get("giay_bu")),
        "so_bu": (bu.get("so_bu"), (_KHO.get("cat") or {}).get("so_bu")),
    }

    # ------------------------------------------------- (1) dB TRONG QUÃNG NGHỈ
    ws, wt = Path(_KHO["wav_sau"]), Path(_KHO["wav_truoc"])
    buoc = TG.BU_GOC_BUOC
    bao_s = TG.duong_bao_muc(ws, buoc=buoc)
    bao_t = TG.duong_bao_muc(wt, buoc=buoc)
    nen = _bpv(bao_s, 0.50)
    loi = _bpv(bao_s, 0.90)
    san_file = _bpv(bao_s, 0.05)
    rows = []
    for (a, b) in khoang:
        ms = muc_trong(bao_s, a, b, buoc)
        mt = muc_trong(bao_t, a, b, buoc)
        rows.append({"a": a, "b": b, "dai": round(b - a, 2),
                     "db_SAU": round(ms, 2), "db_TRUOC": round(mt, 2),
                     "so_nen": round(ms - nen, 2)})
    co_nhac = [x for x in rows if x["db_SAU"] >= nen - GAN_NEN_DB]
    im_han = [x for x in rows if x["db_SAU"] <= SAN_IM_DB]
    ket["muc_ban_tron"] = {
        "nen_TB_p50_dBFS": round(nen, 2),
        "muc_loi_p90_dBFS": round(loi, 2),
        "san_p05_dBFS": round(san_file, 2),
        "quang": rows,
        "db_quang_TB": round(st.mean([x["db_SAU"] for x in rows]), 2)
        if rows else None,
        "db_quang_thap_nhat": round(min([x["db_SAU"] for x in rows]), 2)
        if rows else None,
        "so_quang_CO_NHAC": len(co_nhac),
        "so_quang_IM_HAN": len(im_han),
        "giay_CO_NHAC": round(sum(x["dai"] for x in co_nhac), 2),
        "giay_IM_HAN": round(sum(x["dai"] for x in im_han), 2),
        "quang_dai_nhat_s": round(max((x["dai"] for x in rows), default=0), 2),
    }
    print(f"\n  --- MỨC TRÊN BẢN TRỘN CUỐI ---")
    print(f"  nền TB cả video (p50) {nen:6.2f} dBFS · mức lời (p90) "
          f"{loi:6.2f} · sàn (p05) {san_file:6.2f}")
    if rows:
        print(f"  quãng nghỉ arm SAU : TB {ket['muc_ban_tron']['db_quang_TB']:6.2f}"
              f" dBFS · thấp nhất {ket['muc_ban_tron']['db_quang_thap_nhat']:6.2f}")
        print(f"  CÓ NHẠC {len(co_nhac)}/{len(rows)} quãng "
              f"({ket['muc_ban_tron']['giay_CO_NHAC']} s) · "
              f"IM HẲN (<= {SAN_IM_DB} dBFS) {len(im_han)} quãng")

    # ------------------------------------ (2) ASR + SÀN BỊA, `language` TỰ NHẬN
    ket["asr"] = {}
    if _KHO.get("manh_bu"):
        w = SB / f"chep_TRUOC_manhbu_{so}.wav"
        n = noi_wav([p for _o, p in _KHO["manh_bu"]], w)
        ket["asr"]["TRUOC_manh_bu"] = {"so_manh": n, **do_chep(w, "TRƯỚC")}
        shutil.copy2(w, NGHE / f"C_CHI_MANH_BU_v{so}_{n}manh.wav")
    if khoang:
        cs = cat_cua_so(ws, khoang, SB / f"cs_{so}")
        w2 = SB / f"chep_SAU_cuaso_{so}.wav"
        n2 = noi_wav(cs, w2)
        ket["asr"]["SAU_cua_so_ban_tron"] = {"so_manh": n2,
                                             **do_chep(w2, "SAU/SÀN BỊA")}

    # ---------------------------------------------- (3) FILE NGHE THỬ -14 LUFS
    if rows:
        dn = max(rows, key=lambda x: x["dai"])
        a = max(0.0, dn["a"] - 3.0)
        b = min(float(_KHO.get("tong") or dn["b"]), dn["b"] + 3.0)
        cap = []
        for nhan, wv in (("A_TRUOC_co_bu", wt), ("B_SAU_khong_bu", ws)):
            tho = SB / f"nghe_{so}_{nhan}.wav"
            TG._ffmpeg(["-i", str(wv), "-af",
                        f"atrim=start={a:.3f}:end={b:.3f},asetpts=N/SR/TB",
                        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le",
                        str(tho)], f"cắt đoạn nghe thử {nhan}", timeout=300)
            ten_ra = (NGHE / f"{nhan}_v{so}_{dn['a']:.1f}-{dn['b']:.1f}s"
                             f"_{dn['dai']:.2f}s.wav")
            TG.chuan_do_to(tho, ten_ra)
            cap.append(str(ten_ra))
        ket["nghe_thu"] = {"quang": dn, "cat": [round(a, 2), round(b, 2)],
                           "file": cap}
        print(f"\n  nghe thử: quãng dài nhất {dn['dai']:.2f}s "
              f"[{dn['a']}-{dn['b']}] -> {len(cap)} file")
    return ket


def main() -> int:
    ds = sys.argv[1] if len(sys.argv) > 1 else "1,2"
    sos = [int(x) for x in ds.replace(" ", "").split(",") if x]
    cu = json.loads(KQ.read_text(encoding="utf-8")) if KQ.exists() else {}
    for so in sos:
        try:
            cu[str(so)] = mot_video(so)
        except Exception as e:                              # noqa: BLE001
            import traceback
            traceback.print_exc()
            cu[str(so)] = {"ok": False, "loi": f"{type(e).__name__}: {e}"[:400]}
        KQ.write_text(json.dumps(cu, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
