"""SINH FILE NGHE THỬ CHO ANH HÙNG — *"khô khan, không cảm xúc"*.

**THƯỚC NHẤN NHÁ KHÔNG NÓI "HAY".** `nhan_nha` tự dặn *"số này KHÔNG nói giọng
HAY hay DỞ"* — nó chỉ nói **độ trải cao độ**. Đọc trải cao mà sai ngữ điệu vẫn
dở. Nên mọi con số của lượt này chỉ để **loại sớm cái phẳng rõ**, còn phán
quyết là **TAI ANH HÙNG**.

CHUẨN HOÁ CÙNG −14 LUFS LÀ BẮT BUỘC, KHÔNG PHẢI CHO ĐẸP
--------------------------------------------------------
Không chuẩn hoá thì phép nghe biến thành *"file nào TO hơn"* — đã đo được
lệch **4 LU** giữa hai máy đọc (ElevenLabs −16,1 vs VieNeu −20,1). Dùng CHÍNH
`thay_giong.chuan_do_to` (nâng thuần + hạn đỉnh, KHÔNG `loudnorm` động), đúng
bộ đo đường xuất thật dùng.

MD5 PHẢI KHÁC NHAU — bẫy cache: `_eleven_tts` có kho theo `sha1(voice|model|
text)`, `thay_giong.doc_thu` có kho theo (giọng·pitch·câu). Hai file trùng MD5
nghĩa là đang nghe CÙNG MỘT tiếng dưới hai cái tên.

Chạy:  .venv\\Scripts\\python -u _nghe_thu_cam_xuc.py
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
RA = REPO / "_NGHE_THU_ANH_HUNG" / "cam_xuc"
TAM = REPO / "bq_nghe_thu_cx"
NOWIN = 0x08000000

#: Câu tiếng VIỆT có chỗ để lên xuống (kể · cảm thán · thì thầm). Cùng MỘT câu
#: cho mọi giọng Việt -> nghe là so được ngay.
CAU_VI = ("Không thể tin được chuyện vừa xảy ra ở đây. "
          "Chỉ trong ba phút, cả toà nhà đã biến mất! "
          "Và không một ai kịp hiểu vì sao.")

#: Bản CÓ THẺ CẢM XÚC — chỉ ElevenLabs v3 đọc được thẻ này.
CAU_VI_THE = ("[curious]Không thể tin được chuyện vừa xảy ra ở đây. "
              "[excited]Chỉ trong ba phút, cả toà nhà đã BIẾN MẤT! "
              "[whispers]Và không một ai kịp hiểu vì sao.")

#: Câu tiếng ANH cho Kokoro (Kokoro KHÔNG có tiếng Việt).
CAU_EN = ("You will not believe what just happened here. "
          "In only three minutes, the whole building was gone! "
          "And nobody had time to understand why.")

ADAM = "el:pNInz6obpgDQGcFmaJgB"


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()[:12]


def _ra_wav(src: Path, dst: Path) -> bool:
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                        "-ac", "2", "-ar", "48000", str(dst)],
                       capture_output=True, creationflags=NOWIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 2000


def _ra_mp3(src: Path, dst: Path) -> bool:
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                        "-c:a", "libmp3lame", "-b:a", "192k", str(dst)],
                       capture_output=True, creationflags=NOWIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 2000


def chuan(src: Path, dich: Path) -> dict:
    """mp3/wav bất kỳ -> mp3 đã chuẩn hoá −14 LUFS bằng CHÍNH `chuan_do_to`."""
    from app.core import thay_giong as tg
    w1 = TAM / (dich.stem + "_vao.wav")
    w2 = TAM / (dich.stem + "_ra.wav")
    if not _ra_wav(src, w1):
        return {"loi": "đổi sang wav hỏng"}
    try:
        kq = tg.chuan_do_to(w1, w2)
    except Exception as e:                                   # noqa: BLE001
        return {"loi": f"chuẩn hoá hỏng: {type(e).__name__}: {e}"}
    if not _ra_mp3(w2, dich):
        return {"loi": "đóng mp3 hỏng"}
    sau = kq.get("sau") or {}
    return {"I": sau.get("I"), "TP": sau.get("TP"),
            "gain": kq.get("nang_db"), "dat": kq.get("dat_dich")}


def doc(voice: str, text: str, dich_tho: Path) -> str:
    """Đọc MỘT câu qua CỬA CHUNG `dubbing._synth_all`. Trả "" nếu xong."""
    from app.core import dubbing
    dich_tho.parent.mkdir(parents=True, exist_ok=True)
    try:
        ok = asyncio.run(dubbing._synth_all([text], voice, [str(dich_tho)]))
    except Exception as e:                                   # noqa: BLE001
        return f"{type(e).__name__}: {e}"
    if not ok or not ok[0] or not dich_tho.exists():
        return "máy đọc không ra file"
    return ""


def doc_el(text: str, model: str, dich_tho: Path) -> str:
    """Đọc bằng ElevenLabs với model CHỈ ĐỊNH (v3 hoặc v2) — TIÊU HẠN MỨC
    THẬT. Đây là chỗ DUY NHẤT của lượt này tốn ký tự; số tiêu in ra ở cuối."""
    from app.core import dubbing
    ok = dubbing._eleven_tts(text, ADAM, str(dich_tho), model=model,
                             on_msg=lambda m: print(f"      · {m}"))
    if not ok or not dich_tho.exists():
        return "ElevenLabs không ra file"
    return ""


#: (thứ tự, tên file, mô tả in ra, cách đọc)
BO = [
    ("01", "DANG_DUNG_edge_NamMinh_nn4-04",
     "GIỌNG ANH ĐANG DÙNG (edge-tts NamMinh, nhấn nhá 4,04)",
     ("edge", "vi-VN-NamMinhNeural", CAU_VI)),
    ("02", "NHAN_BAN_mau_7giay_TRO_nn3-3",
     "NHÂN BẢN từ mẫu 7 GIÂY đọc TRƠ (nhấn nhá ~3,3) — kiểu mẫu hiện tại",
     ("mau", "7", CAU_VI)),
    ("03", "NHAN_BAN_mau_CO_NHAN_NHA_nn5-8",
     "NHÂN BẢN từ mẫu CÓ NHẤN NHÁ (nhấn nhá ~5,8) — mẫu nên thu",
     ("mau", "tran", CAU_VI)),
    ("04", "VIENEU_ThanhBinh_nn5-61_KHUYEN_NGHE_TRUOC",
     "VieNeu «Thanh Bình» — nhấn nhá 5,61 · đọc sai 9,0% · ĐANG LÀ DÒNG ĐẦU "
     "nhóm VieNeu trong combo (đánh đổi tốt nhất đo được)",
     ("edge", "vn:Thanh Bình", CAU_VI)),
    ("05", "VIENEU_XuanVinh_nn6-26_DOC_SAI_26pt4",
     "VieNeu «Xuân Vĩnh» — nhấn nhá 6,26 CAO NHẤT bảng Việt NHƯNG đọc sai "
     "26,4% (gấp 5,5 lần sàn 4,8%) — nghe kỹ chữ, đừng chỉ nghe giọng",
     ("edge", "vn:Xuân Vĩnh", CAU_VI)),
    ("06", "VIENEU_NgocLinh_nn2-95",
     "VieNeu «Ngọc Linh» — nhấn nhá 2,95, THẤP NHẤT (để so đầu dưới)",
     ("edge", "vn:Ngọc Linh", CAU_VI)),
    ("07", "KOKORO_am_santa_nn5-66_TIENG_ANH",
     "Kokoro «am_santa» — nhấn nhá 5,66, cao nhất 28 giọng (TIẾNG ANH)",
     ("edge", "kk:am_santa", CAU_EN)),
    ("08", "KOKORO_af_bella_nn2-33_TIENG_ANH",
     "Kokoro «af_bella» — DÒNG THỨ 2 trong combo mà nhấn nhá chỉ 2,33",
     ("edge", "kk:af_bella", CAU_EN)),
    ("09", "ELEVEN_v3_CO_THE_CAM_XUC",
     "ElevenLabs **v3 + THẺ CẢM XÚC** — TRẦN TRÊN, tốn tiền theo ký tự",
     ("el", "eleven_v3", CAU_VI_THE)),
    ("10", "ELEVEN_v2_KHONG_THE",
     "ElevenLabs v2 KHÔNG thẻ — đúng thứ hộp Thay giọng ĐANG gửi hôm nay",
     ("el", "eleven_multilingual_v2", CAU_VI)),
]


def _mau(loai: str) -> Path | None:
    """File mẫu do `_do_mau_dai.py` dựng (giọng MÁY — luật cấm
    `adam_clone.wav`, đó là bản sao một giọng ElevenLabs thương mại)."""
    d = REPO / "bq_do_mau_dai"
    if loai == "7":
        for p in d.glob("mau_vi_VN_HoaiMyNeural_7s.wav"):
            return p
    for p in d.glob("mau_vn_Xuân*28s.wav"):
        return p
    for p in d.glob("mau_*28s.wav"):
        return p
    return None


def main() -> int:
    from app.core import dubbing
    RA.mkdir(parents=True, exist_ok=True)
    TAM.mkdir(parents=True, exist_ok=True)

    truoc = dubbing.eleven_credit_remain(use_cache=False)
    print(f"ElevenLabs còn TRƯỚC lượt này: {truoc} ký tự")
    print("=" * 78)

    ra: list[tuple[str, Path, str]] = []
    for so, ten, mo_ta, (cach, tham, text) in BO:
        dich = RA / f"{so}_{ten}.mp3"
        tho = TAM / f"{so}_tho.wav"
        print(f"\n[{so}] {mo_ta}")
        if cach == "el":
            loi = doc_el(text, tham, tho)
        elif cach == "mau":
            m = _mau(tham)
            if not m:
                print("      BỎ QUA: chưa có file mẫu (chạy _do_mau_dai.py)")
                continue
            loi = doc("vnb:" + str(m), text, tho)
        else:
            loi = doc(tham, text, tho)
        if loi:
            print(f"      LỖI: {loi}")
            continue
        d = chuan(tho, dich)
        if d.get("loi"):
            print(f"      LỖI chuẩn hoá: {d['loi']}")
            continue
        print(f"      -> {dich.name}  (I={d.get('I')} LUFS · "
              f"TP={d.get('TP')} dBTP · nâng {d.get('gain')} dB)")
        ra.append((so, dich, mo_ta))

    print()
    print("=" * 78)
    print("MD5 PHẢI KHÁC NHAU (bẫy cache)")
    print("=" * 78)
    ms: dict = {}
    for so, p, _m in ra:
        h = _md5(p)
        ms.setdefault(h, []).append(so)
        print(f"  {so}  md5={h}  {p.stat().st_size / 1024:7.1f} KB")
    trung = {h: v for h, v in ms.items() if len(v) > 1}
    print(f"  -> {len(ms)} MD5 cho {len(ra)} file: "
          f"{'KHÁC HẾT' if not trung else f'TRÙNG {trung}'}")

    sau = dubbing.eleven_credit_remain(use_cache=False)
    print(f"\nElevenLabs còn SAU: {sau} ký tự "
          f"(TIÊU {(truoc or 0) - (sau or 0)} ký tự)")
    print(f"\nThư mục nghe thử: {RA}")
    return 0 if (ra and not trung) else 1


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        try:
            from app.core import xoa_an_toan
            xoa_an_toan.don_thu_muc(TAM, trong=REPO)
        except Exception as e:                               # noqa: BLE001
            print(f"  (dọn hộp cát lỗi: {e})")
    sys.exit(rc)
