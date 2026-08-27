"""ĐO GHÉP CẶP: mẫu giọng **DÀI HƠN / CÓ NHẤN NHÁ HƠN** có làm bản sao bớt
khô khan không?

PHÁT HIỆN CŨ ĐANG KIỂM CHỨNG: *nhấn nhá của bản sao = nhấn nhá của MẪU*
(mẫu A nhạt 3,10 -> sao 3,15 · mẫu B có nhấn 4,01 -> sao 3,73). Mẫu của anh
Hùng chỉ **7 GIÂY**. Câu hỏi: thu mẫu DÀI hơn + ĐỌC CÓ CẢM XÚC thì bản sao
nhấn nhá lên bao nhiêu?

THIẾT KẾ 2x2 + TRẦN — TÁCH *ĐỘ DÀI* KHỎI *ĐỘ NHẤN NHÁ CỦA MẪU*
--------------------------------------------------------------
Đo rời một cặp "7 giây trơ" vs "28 giây có nhấn" thì **trộn hai biến** —
tăng lên cũng không biết nhờ DÀI hay nhờ CÓ NHẤN, mà lời khuyên cho anh Hùng
khác hẳn nhau ("thu dài ra" vs "đọc diễn cảm vào"). Nên 4 ô:

    | mẫu           | 7 giây | 28 giây |
    | nhấn nhá THẤP |  A1    |  A2     |
    | nhấn nhá CAO  |  A3    |  A4     |

    + A5 = TRẦN: mẫu nhấn nhá CAO NHẤT lấy được, 28 giây.

MẪU LÀ **GIỌNG MÁY**, KHÔNG PHẢI NGƯỜI THẬT. Ranh giới cứng của repo: không
nhân bản giọng người thật nào ngoài chính anh Hùng, và **KHÔNG dùng
`adam_clone.wav`**. Mẫu ở đây do edge-tts / VieNeu dựng-sẵn sinh ra.

THƯỚC: **KHÔNG ĐẺ THƯỚC THỨ HAI.** Dùng `_do_nhan_nha.f0_nua_cung` +
`pstdev` và bộ câu `_do_nhan_nha_bang.CAU["vi"]` — đúng thước đã sinh ra bảng
211 giọng. Cả 5 ô ĐỌC CÙNG 4 CÂU ĐÓ nên đây là đo GHÉP CẶP thật.

ĐỐI CHỨNG TÁI LẬP (BẮT BUỘC): đo lại 3 giọng đã có số trong `nhan_nha.BANG`
**CÙNG LƯỢT NÀY**. Lệch quá 0,30 (sàn nhiễu đã đo với bộ 4 câu) thì bảng mới
vô nghĩa và script tự nói ra.

VieNeu **KHÔNG TIỀN ĐỊNH** -> mỗi ô chạy >= 2 lượt, báo cáo ghi DẢI.

Ghi `_kq_mau_dai.json` **NGAY SAU MỖI Ô** (lượt trước bị giết giữa chừng,
mất sạch số).

Chạy:  .venv\\Scripts\\python -u _do_mau_dai.py
       .venv\\Scripts\\python -u _do_mau_dai.py --lam-lai     (bỏ kết quả cũ)
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
SAN = REPO / "bq_do_mau_dai"
KQ = REPO / "_kq_mau_dai.json"
NOWIN = 0x08000000

#: Sàn nhiễu của thước với bộ 4 câu — `nhan_nha` đã ghi (đo lại lệch <= 0,12);
#: 0,30 là ngưỡng NỚI đã dùng ở các lượt trước, giữ nguyên cho so được.
NGUONG_DOI_CHUNG = 0.30

#: 3 giọng đối chứng, trải từ ĐÁY tới ĐỈNH của bảng — lấy giọng ở giữa thì
#: một thước bị nén/giãn vẫn lọt.
DOI_CHUNG = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural", "en-GB-RyanNeural"]

#: Lời cho MẪU giọng. **KHÁC hẳn 4 câu đo** — mẫu và bài đo trùng nhau thì
#: không biết bản sao đang chép nhấn nhá hay chép thẳng câu.
LOI_MAU = [
    "Hôm nay tôi sẽ kể cho các bạn nghe một câu chuyện rất lạ.",
    "Chuyện bắt đầu vào một buổi chiều mưa, ở một ngôi làng nhỏ ven sông.",
    "Không ai trong làng biết rằng, chỉ vài giờ sau đó, mọi thứ sẽ thay đổi.",
    "Người đàn ông ấy bước ra khỏi nhà, tay cầm một chiếc đèn dầu đã tắt.",
    "Ông nhìn về phía cuối con đường, nơi có tiếng động lạ vọng lại.",
    "Rồi ông quay lại, gọi tên đứa con gái nhỏ đang ngủ trong nhà.",
    "Cả làng thức giấc vì tiếng chuông, và không ai dám bước ra ngoài.",
    "Đó là đêm dài nhất mà những người sống ở đó từng trải qua.",
]

#: Năm ô. (tên, giọng nguồn sinh mẫu, số giây mẫu, nhấn nhá mẫu theo BẢNG)
O_DO = [
    ("A1 mẫu THẤP  7 giây", "vi-VN-HoaiMyNeural", 7),
    ("A2 mẫu THẤP 28 giây", "vi-VN-HoaiMyNeural", 28),
    ("A3 mẫu CAO   7 giây", "vi-VN-NamMinhNeural", 7),
    ("A4 mẫu CAO  28 giây", "vi-VN-NamMinhNeural", 28),
    ("A5 TRẦN     28 giây", "vn:Xuân Vĩnh", 28),
]

SO_LUOT = 2                      # VieNeu không tiền định -> >= 2 lượt/ô


def _ghi(kq: dict) -> None:
    """Ghi NGAY, sau MỖI ô. Lượt trước bị giết giữa chừng là mất sạch."""
    KQ.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                  encoding="utf-8")


def _doc(kq_cu: bool) -> dict:
    if not kq_cu or not KQ.exists():
        return {"doi_chung": {}, "o": {}, "mau": {}}
    try:
        d = json.loads(KQ.read_text(encoding="utf-8"))
        d.setdefault("doi_chung", {})
        d.setdefault("o", {})
        d.setdefault("mau", {})
        return d
    except (OSError, ValueError):
        return {"doi_chung": {}, "o": {}, "mau": {}}


def ra_wav(src: Path, dst: Path, sr: int = 16000) -> bool:
    """mp3/wav -> wav mono. `f0_nua_cung` đọc WAV, không đọc mp3."""
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-ac", "1",
                        "-ar", str(sr), "-f", "wav", str(dst)],
                       capture_output=True, creationflags=NOWIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def nhan_nha_cua_file(wavs: list[Path]) -> dict:
    """pstdev F0 (nửa cung) gộp mọi khung có tiếng — ĐÚNG cách
    `_do_nhan_nha_bang.do_mot` làm, không viết thước thứ hai."""
    from _do_nhan_nha import f0_nua_cung
    tat: list[float] = []
    for w in wavs:
        d = f0_nua_cung(w)
        if len(d) >= 20:
            tat.extend(d)
    if len(tat) < 50:
        return {"loi": f"quá ít khung có tiếng ({len(tat)})"}
    return {"nhan_nha": round(st.pstdev(tat), 2), "so_khung": len(tat),
            "f0_giua_hz": round(100.0 * 2 ** (st.median(tat) / 12.0), 1)}


def doc_4_cau(voice: str, tm: Path,
              tieng: str = "") -> tuple[list[Path], float, str]:
    """Đọc ĐÚNG 4 câu bằng CỬA CHUNG `dubbing._synth_all`.

    Trả (danh sách wav 16k, giây, lỗi). Cửa chung = đúng cửa lượt xuất thật
    đi, nên số đo là số của thứ anh Hùng sẽ nghe.

    ═══ `tieng` KHÔNG PHẢI THAM SỐ TRANG TRÍ — BỎ NÓ LÀ SAI SỐ THẬT ═══
    Bản đầu của file này ghi cứng `CAU["vi"]` cho MỌI giọng, kể cả giọng đối
    chứng `en-GB-RyanNeural`. Kết quả: Ryan đọc câu TIẾNG VIỆT -> dò vần sai
    -> đo ra **4,76** trong khi bảng ghi **5,38**, và cột đối chứng kêu
    *"THƯỚC LỆCH, KHÔNG TIN"*. Đo lại Ryan bằng ĐÚNG `CAU["en"]`: **5,38 và
    5,38** — khớp tuyệt đối, hai lượt liền. Tức thước KHÔNG lệch, **phép đo
    sai vì cho giọng đọc sai thứ tiếng** — đúng cái `_do_nhan_nha_bang.
    cau_cho` đã dặn thành lời (*"Bắt giọng Nhật đọc câu tiếng Việt là đo một
    thứ khác hẳn"*) mà tôi vẫn sập.

    Giọng đối chứng -> `cau_cho(voice)` (đúng tiếng của nó). Các ô nhân bản
    -> ép `tieng="vi"` để **CẢ 5 Ô ĐỌC CÙNG MỘT BỘ CÂU** (đo ghép cặp).
    """
    from _do_nhan_nha_bang import CAU, cau_cho
    from app.core import dubbing
    texts = CAU[tieng] if tieng else cau_cho(voice)
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    paths = [str(tm / f"c{i}.mp3") for i in range(len(texts))]
    t0 = time.monotonic()
    try:
        ok = asyncio.run(dubbing._synth_all(texts, voice, paths))
    except Exception as e:                                   # noqa: BLE001
        return [], 0.0, f"{type(e).__name__}: {e}"
    giay = round(time.monotonic() - t0, 1)
    ra: list[Path] = []
    for i, (p, o) in enumerate(zip(paths, ok)):
        if not o or not Path(p).exists():
            continue
        w = tm / f"w{i}.wav"
        if ra_wav(Path(p), w):
            ra.append(w)
    if not ra:
        return [], giay, "không đọc được câu nào"
    return ra, giay, ""


def dung_mau(voice_nguon: str, giay: int, dich: Path) -> str:
    """Sinh FILE MẪU `giay` giây bằng `voice_nguon` (giọng MÁY, không phải
    người thật). Trả "" nếu xong, hoặc chuỗi lỗi.

    Ghép đủ câu cho vượt `giay` rồi CẮT đúng độ dài. **`-t` là tuỳ chọn ĐẦU
    VÀO** — đặt sau `-i` là chuyện `anullsrc` ghi vô hạn 115 MB/s đã làm đầy
    ổ C 420 GB. Ở đây nguồn hữu hạn nên không nổ, nhưng giữ đúng chỗ để
    không ai chép sai khuôn.
    """
    from app.core import dubbing
    tm = dich.parent / (dich.stem + "_tho")
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    # Câu ngắn thì lấy ít, câu dài lấy nhiều — đọc dư rồi cắt.
    n = 2 if giay <= 10 else len(LOI_MAU)
    texts = LOI_MAU[:n]
    paths = [str(tm / f"m{i}.mp3") for i in range(len(texts))]
    try:
        ok = asyncio.run(dubbing._synth_all(texts, voice_nguon, paths))
    except Exception as e:                                   # noqa: BLE001
        return f"{type(e).__name__}: {e}"
    co = [p for p, o in zip(paths, ok) if o and Path(p).exists()]
    if not co:
        return "giọng nguồn không đọc được câu nào"
    ds = tm / "ds.txt"
    ds.write_text("".join(f"file '{Path(p).as_posix()}'\n" for p in co),
                  encoding="utf-8")
    noi = tm / "noi.wav"
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(ds), "-ac", "1", "-ar", "24000", str(noi)],
        capture_output=True, creationflags=NOWIN, timeout=300)
    if r.returncode != 0 or not noi.exists():
        return "ghép mẫu hỏng"
    # `-t` TRƯỚC `-i` = cắt ở ĐẦU VÀO.
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-t", str(giay), "-i", str(noi),
         "-ac", "1", "-ar", "24000", str(dich)],
        capture_output=True, creationflags=NOWIN, timeout=300)
    if r.returncode != 0 or not dich.exists() or dich.stat().st_size < 5000:
        return "cắt mẫu hỏng"
    shutil.rmtree(tm, ignore_errors=True)
    return ""


def _dai(p: Path) -> float:
    r = subprocess.run(
        [str(REPO / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, creationflags=NOWIN, timeout=60)
    try:
        return round(float(r.stdout.strip()), 2)
    except ValueError:
        return 0.0


def _don_san() -> None:
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(SAN, trong=REPO)
    except Exception as e:                                   # noqa: BLE001
        print(f"  (dọn hộp cát lỗi: {e})")


def main() -> int:
    from app.core.nhan_nha import BANG
    lam_lai = "--lam-lai" in sys.argv
    kq = _doc(not lam_lai)
    SAN.mkdir(parents=True, exist_ok=True)

    # ============ ĐỐI CHỨNG TÁI LẬP — CÙNG LƯỢT ============
    print("=" * 74)
    print("ĐỐI CHỨNG TÁI LẬP (cùng lượt) — lệch > 0,30 thì bảng mới VÔ NGHĨA")
    print("=" * 74)
    print(f"{'giọng':30s} {'bảng':>7s} {'đo lại':>8s} {'lệch':>7s}")
    lech_max = 0.0
    for v in DOI_CHUNG:
        if v in kq["doi_chung"] and not kq["doi_chung"][v].get("loi"):
            d = kq["doi_chung"][v]
        else:
            ws, giay, loi = doc_4_cau(v, SAN / ("dc_" + v.replace("-", "_")))  # đúng tiếng
            d = {"loi": loi} if loi else nhan_nha_cua_file(ws)
            d["giay"] = giay
            kq["doi_chung"][v] = d
            _ghi(kq)
        goc = BANG.get(v)
        if d.get("loi") or goc is None:
            print(f"{v:30s} {'?':>7s} {'LỖI':>8s}   {d.get('loi', 'chưa có mốc')}")
            continue
        lech = abs(d["nhan_nha"] - goc)
        lech_max = max(lech_max, lech)
        print(f"{v:30s} {goc:7.2f} {d['nhan_nha']:8.2f} {lech:7.2f}")
    tin_duoc = lech_max <= NGUONG_DOI_CHUNG
    print(f"  lệch lớn nhất {lech_max:.2f} -> "
          f"{'THƯỚC TÁI LẬP ĐƯỢC' if tin_duoc else 'THƯỚC LỆCH, KHÔNG TIN'}")
    kq["doi_chung_lech_max"] = round(lech_max, 2)
    kq["doi_chung_dat"] = tin_duoc
    _ghi(kq)

    # ============ NĂM Ô ============
    print()
    print("=" * 74)
    print(f"NĂM Ô — mỗi ô {SO_LUOT} lượt (VieNeu không tiền định)")
    print("=" * 74)
    print(f"{'ô':22s} {'mẫu(nn)':>8s} {'dài':>6s} "
          f"{'sao lượt 1':>11s} {'lượt 2':>8s} {'giây':>7s}")
    for ten, nguon, giay_mau in O_DO:
        khoa = f"{ten}"
        cu = kq["o"].get(khoa) or {}
        if cu.get("sao") and len(cu["sao"]) >= SO_LUOT:
            _in_o(ten, cu)
            continue
        # --- dựng mẫu ---
        mau = SAN / f"mau_{nguon.replace(':', '_').replace('-', '_')}_{giay_mau}s.wav"
        if not mau.exists():
            loi = dung_mau(nguon, giay_mau, mau)
            if loi:
                kq["o"][khoa] = {"loi": f"dựng mẫu hỏng: {loi}"}
                _ghi(kq)
                print(f"{ten:22s} DỰNG MẪU HỎNG: {loi}")
                continue
        dai_that = _dai(mau)
        # nhấn nhá CỦA CHÍNH MẪU (đo, không tra bảng — mẫu đã bị cắt/ghép)
        wm = SAN / (mau.stem + "_16k.wav")
        mau_nn = nhan_nha_cua_file([wm]) if ra_wav(mau, wm) else {"loi": "wav hỏng"}
        kq["mau"][khoa] = {"nguon": nguon, "giay_dat": giay_mau,
                           "giay_that": dai_that, **mau_nn}
        _ghi(kq)
        # --- nhân bản rồi đo, SO_LUOT lượt ---
        sao: list[dict] = list(cu.get("sao") or [])
        for lan in range(len(sao), SO_LUOT):
            voice = "vnb:" + str(mau)
            ws, gy, loi = doc_4_cau(voice, SAN / f"sao_{khoa.split()[0]}_{lan}",
                                    tieng="vi")
            r = {"loi": loi} if loi else nhan_nha_cua_file(ws)
            r["giay"] = gy
            sao.append(r)
            kq["o"][khoa] = {"nguon": nguon, "giay_mau": giay_mau,
                             "mau_nn": mau_nn.get("nhan_nha"),
                             "mau_giay_that": dai_that, "sao": sao}
            _ghi(kq)                       # GHI NGAY SAU MỖI LƯỢT
        _in_o(ten, kq["o"][khoa])

    print()
    print("=" * 74)
    print("BẢNG GỌN")
    print("=" * 74)
    print(f"{'ô':22s} {'nhấn nhá MẪU':>13s} {'-> nhấn nhá BẢN SAO':>21s}")
    for ten, _n, _g in O_DO:
        d = kq["o"].get(ten) or {}
        if d.get("loi"):
            print(f"{ten:22s} {'LỖI':>13s}  {d['loi']}")
            continue
        xs = [s["nhan_nha"] for s in (d.get("sao") or []) if s.get("nhan_nha")]
        if not xs:
            print(f"{ten:22s} {'?':>13s}  chưa đo được")
            continue
        dai = f"{min(xs):.2f}-{max(xs):.2f}" if len(xs) > 1 else f"{xs[0]:.2f}"
        print(f"{ten:22s} {d.get('mau_nn', 0) or 0:13.2f}  {dai:>21s}")
    print(f"\n  kết quả -> {KQ}")
    return 0 if tin_duoc else 1


def _in_o(ten: str, d: dict) -> None:
    if d.get("loi"):
        print(f"{ten:22s} {d['loi']}")
        return
    xs = [s.get("nhan_nha") for s in (d.get("sao") or [])]
    gy = sum(s.get("giay", 0) for s in (d.get("sao") or []))
    c = [f"{x:.2f}" if x else "LỖI" for x in xs] + ["", ""]
    print(f"{ten:22s} {d.get('mau_nn') or 0:8.2f} "
          f"{d.get('mau_giay_that') or 0:6.1f} {c[0]:>11s} {c[1]:>8s} "
          f"{gy:7.0f}")


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        # KHÔNG dọn hộp cát ở lượt này: file mẫu + file sao còn dùng cho
        # bước sinh file NGHE THỬ. Dọn ở `_nghe_thu_cam_xuc.py`.
        pass
    sys.exit(rc)
