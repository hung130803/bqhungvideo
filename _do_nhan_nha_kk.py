"""ĐO NHẤN NHÁ 28 GIỌNG KOKORO — cùng THƯỚC, cùng BỘ CÂU với bảng 211 giọng.

**VÌ SAO CÓ FILE NÀY.** Anh Hùng nghe rồi báo: *"phần giọng đọc koro tôi thấy
được mà k có nhấn nhá cảm xúc gì"*. Trước lượt này ``nhan_nha.BANG`` **KHÔNG có
một mã ``kk:`` nào** — tức app có bộ đo nhấn nhá (cổng 76) mà chưa chạy cho bộ
giọng này lần nào, và lời anh ấy không có một con số nào để đối chiếu.

═══════════════════════════════════════════════════════════════════════════
BA THỨ PHẢI GIỐNG BẢNG CŨ, NẾU KHÁC MỘT THỨ LÀ SỐ KHÔNG SO ĐƯỢC
═══════════════════════════════════════════════════════════════════════════
1. **THƯỚC**: ``_do_nhan_nha.f0_nua_cung`` + ``statistics.pstdev`` — IMPORT
   chứ không chép lại. Hai bản thước là hai bảng số không so được với nhau
   (đúng lời ``_do_nhan_nha_bang`` đã dặn).
2. **BỘ CÂU**: ``_do_nhan_nha_bang.CAU["en"]`` — **ĐÚNG 4 câu tiếng Anh**
   (kể · hỏi · cảm thán · kể dài) mà toàn bộ giọng ``en-*`` trong
   ``nhan_nha.BANG`` đã đọc. Kokoro **KHÔNG có tiếng Việt** (28/28 giọng là
   ``af_/am_/bf_/bm_`` = Mỹ/Anh), nên bộ câu phải là TIẾNG ANH và mốc đối
   chứng phải là giọng edge-tts **tiếng Anh** — lấy ``vi-VN-HoaiMy`` làm mốc ở
   đây chính là dựng lại phép **so chéo tiếng** mà ``nhan_nha`` cấm.
3. **NGƯỠNG LỌC KHUNG**: ≥20 khung có tiếng mỗi câu · ≥50 khung cả lượt —
   copy đúng ``_do_nhan_nha_bang.do_mot``, không nới cho đủ số.

═══════════════════════════════════════════════════════════════════════════
ĐỐI CHỨNG CHẠY CÙNG LƯỢT — KHÔNG CÓ NÓ THÌ CON SỐ VÔ NGHĨA
═══════════════════════════════════════════════════════════════════════════
3 giọng edge-tts tiếng Anh **đã có số trong bảng**, trải từ đáy tới đỉnh:

    en-US-Aria 3,33  ·  en-US-Andrew 4,49  ·  en-GB-Ryan 5,38

Chúng vừa là **mốc để so** (Kokoro kém/hơn edge-tts bao nhiêu) vừa là **phép
kiểm thước**: nếu 3 số này không tái lập được giá trị trong ``BANG`` thì cả cột
Kokoro phải bỏ, vì lúc đó không biết lệch là do giọng hay do thước/bộ câu.
Đối chứng đi qua **CỬA THẬT** ``dubbing._synth_all`` y hệt lượt sinh bảng cũ.

═══════════════════════════════════════════════════════════════════════════
KOKORO ĐI ``doc_loat`` TRỰC TIẾP — CỐ Ý, KHÔNG PHẢI CHO GỌN
═══════════════════════════════════════════════════════════════════════════
``dubbing._synth_all("kk:...")`` có nhánh **LÙI ÊM về edge-tts**
(``_lui_kokoro``) khi Kokoro hỏng. Đo qua cửa đó là mở đúng cửa cho tai nạn
tệ nhất của một phép đo: **ghi số của edge-tts vào cột Kokoro** mà không một
dòng báo nào. ``doc_loat`` thì trả toàn ``False`` khi hỏng — hỏng là LỘ.

Chốt thêm bằng **BẰNG CHỨNG ĐỊNH DẠNG**, không tin lời hàm: file Kokoro ghi ra
là **WAV 24 kHz** (``giong_kokoro.SR``), edge-tts trả **MP3**. Mỗi file đều bị
soi ``wave.open`` + ``framerate == SR`` trước khi đo; lệch là ghi ``LOI`` chứ
không lặng lẽ nhận.

**GỌI GỘP CẢ LOẠT TRONG MỘT LƯỢT cho mỗi giọng** — đã đo (CLAUDE.md, cổng 87):
gọi lẻ đắt hơn **5,35 lần** (90,44 s so với 16,91 s cho 12 câu) vì mỗi lượt gọi
nạp lại model.

Chạy:  .venv\\Scripts\\python -u _do_nhan_nha_kk.py
       .venv\\Scripts\\python -u _do_nhan_nha_kk.py af_bella am_adam   (lọc)
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import statistics as st
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

#: Thư mục mẻ tạm. Tên bắt đầu bằng `bq_do_nhan_nha` nên đã nằm trong
#: `.gitignore` (`bq_do_nhan_nha*/`) — không cần thêm dòng ignore mới.
SAN = REPO / "bq_do_nhan_nha_kk"

KQ = REPO / "_kq_nhan_nha_kk.json"

#: Giọng edge-tts **TIẾNG ANH** làm mốc, kèm giá trị đang có trong
#: ``nhan_nha.BANG`` để mục "kiểm thước" tự chấm được.
DOI_CHUNG: tuple[tuple[str, float], ...] = (
    ("en-US-AriaNeural", 3.33),
    ("en-US-AndrewNeural", 4.49),
    ("en-GB-RyanNeural", 5.38),
)

#: Lệch tối đa cho phép giữa số đo lại và số trong ``BANG``. Lấy từ dải nhiễu
#: mà chính ``nhan_nha`` đã đo (*"5/8 giọng lệch ĐÚNG 0,00 · lệch lớn nhất
#: 0,10"*, và mục "SỐ NÀY TIỀN ĐỊNH" ghi 0,00..0,12). **KHÔNG nới số này để
#: phép kiểm thước xanh** — nới là bỏ luôn cái chốt duy nhất chống trộn hai
#: thước vào một cột.
LECH_CHO_PHEP = 0.13


def _dai_wav(p: Path) -> float:
    """Độ dài WAV (giây). 0.0 nếu không đọc được."""
    try:
        with wave.open(str(p), "rb") as w:
            sr = w.getframerate()
            return (w.getnframes() / sr) if sr else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _la_wav_kokoro(p: Path) -> tuple[bool, str]:
    """File này CÓ ĐÚNG là WAV do Kokoro ghi ra không?

    Chốt chống nhận oan số của edge-tts (MP3) vào cột Kokoro. Xem docstring
    đầu file, mục "BẰNG CHỨNG ĐỊNH DẠNG".
    """
    from app.core import giong_kokoro as KK
    try:
        with wave.open(str(p), "rb") as w:
            sr, n = w.getframerate(), w.getnframes()
    except Exception as e:  # noqa: BLE001
        return False, f"không mở được như WAV ({type(e).__name__}: {e})"
    if sr != KK.SR:
        return False, f"tần số {sr} Hz khác `giong_kokoro.SR` {KK.SR} Hz"
    if n <= 0:
        return False, "0 mẫu"
    return True, ""


def _do_f0(files: list[Path], tm: Path) -> dict:
    """Đổi ra WAV mono 16 kHz rồi đo F0 -> nhấn nhá. Dùng ĐÚNG thước cổng 76."""
    from _do_nhan_nha import f0_nua_cung
    from _do_nhan_nha_bang import ra_wav

    tat: list[float] = []
    so_cau = 0
    for i, p in enumerate(files):
        w = tm / f"w{i}.wav"
        if not ra_wav(p, w):
            continue
        d = f0_nua_cung(w)
        # ≥20 khung mỗi câu — ngưỡng của `_do_nhan_nha_bang.do_mot`, giữ NGUYÊN.
        if len(d) >= 20:
            tat.extend(d)
            so_cau += 1
    if len(tat) < 50:
        return {"loi": f"quá ít khung có tiếng ({len(tat)})"}
    return {"nhan_nha": round(st.pstdev(tat), 2),
            "so_khung": len(tat), "so_cau": so_cau,
            "f0_giua_hz": round(100.0 * 2 ** (st.median(tat) / 12.0), 1)}


def do_kokoro(ma: str, texts: list[str]) -> dict:
    """Một giọng Kokoro: **MỘT lượt `doc_loat` cho CẢ LOẠT** rồi đo."""
    from app.core import giong_kokoro as KK

    tm = SAN / f"kk_{ma}"
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    paths = [str(tm / f"c{i}.wav") for i in range(len(texts))]
    t0 = time.monotonic()
    try:
        ok = KK.doc_loat(texts, paths, KK.TIEN_TO + ma)
    except Exception as e:  # noqa: BLE001
        return {"loi": f"doc_loat NÉM {type(e).__name__}: {e}"}
    giay = round(time.monotonic() - t0, 1)
    if not any(ok):
        return {"loi": "doc_loat trả FALSE cả loạt (xem logs/kokoro_*.log)",
                "giay": giay}
    files: list[Path] = []
    dai = 0.0
    for p, o in zip(paths, ok):
        if not o:
            continue
        pp = Path(p)
        that, vi_sao = _la_wav_kokoro(pp)
        if not that:
            return {"loi": f"file KHÔNG phải WAV Kokoro: {vi_sao}",
                    "giay": giay}
        files.append(pp)
        dai += _dai_wav(pp)
    d = _do_f0(files, tm)
    d["giay"] = giay
    d["dai_wav"] = round(dai, 2)
    d["so_cau_doc"] = len(files)
    return d


def do_edge(voice: str, texts: list[str]) -> dict:
    """Một giọng edge-tts qua **CỬA THẬT** `dubbing._synth_all` (y hệt cổng 76)."""
    from app.core import dubbing

    tm = SAN / f"edge_{voice}"
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    paths = [str(tm / f"c{i}.mp3") for i in range(len(texts))]
    t0 = time.monotonic()
    try:
        ok = asyncio.run(dubbing._synth_all(texts, voice, paths))
    except Exception as e:  # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    giay = round(time.monotonic() - t0, 1)
    files = [Path(p) for p, o in zip(paths, ok) if o and Path(p).exists()]
    if not files:
        return {"loi": "không đọc được câu nào", "giay": giay}
    d = _do_f0(files, tm)
    d["giay"] = giay
    d["so_cau_doc"] = len(files)
    # MP3 -> độ dài lấy từ bản WAV vừa đổi (khỏi cần thư viện đọc MP3).
    d["dai_wav"] = round(sum(_dai_wav(tm / f"w{i}.wav")
                             for i in range(len(files))), 2)
    return d


def _so_vn(v) -> str:
    """Số kiểu Việt (dấu phẩy thập phân). '—' khi không có số."""
    return f"{v:.2f}".replace(".", ",") if isinstance(v, (int, float)) else "—"


if __name__ == "__main__":
    from app.core import giong_kokoro as KK
    from _do_nhan_nha_bang import CAU

    texts = list(CAU["en"])
    diem = {m: d for m, _mo_ta, d in KK.GIONG_KK}
    loc = [a for a in sys.argv[1:]]
    ma_ds = [m for m, _mo, _d in KK.GIONG_KK if not loc or m in loc]

    tt = KK.tinh_trang()
    print(f"BỘ CÂU: `_do_nhan_nha_bang.CAU['en']` — {len(texts)} câu TIẾNG ANH "
          f"(kể · hỏi · cảm thán · kể dài)")
    print(f"THƯỚC : `_do_nhan_nha.f0_nua_cung` + pstdev (nửa cung, khung 40 ms)")
    print(f"KOKORO: {'CÓ' if tt.get('co') else 'THIẾU ' + str(tt.get('thieu'))}"
          f" · {len(ma_ds)} giọng sẽ đo")
    if not tt.get("co"):
        print("\nTHIẾU BỘ KOKORO -> không đo được. Bấm nút tải trong app trước.")
        sys.exit(2)

    SAN.mkdir(parents=True, exist_ok=True)
    ra: dict = {}
    if KQ.exists():                       # chạy lại thì không đo lại từ đầu
        try:
            ra = json.loads(KQ.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra = {}
    ra.setdefault("bo_cau", texts)
    ra.setdefault("kokoro", {})
    ra.setdefault("doi_chung", {})

    def _luu() -> None:
        KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    print("\n" + "=" * 78)
    print("ĐỐI CHỨNG edge-tts TIẾNG ANH (chạy CÙNG LƯỢT, cùng bộ câu)")
    print("=" * 78)
    print(f"{'giọng':26s} {'đo lại':>8s} {'trong BANG':>11s} {'lệch':>7s} "
          f"{'dài WAV':>8s}")
    for v, moc in DOI_CHUNG:
        d = ra["doi_chung"].get(v)
        if not d or d.get("loi"):
            d = do_edge(v, texts)
            d["moc_bang"] = moc
            ra["doi_chung"][v] = d
            _luu()
        if d.get("loi"):
            print(f"{v:26s} LỖI: {d['loi']}")
            continue
        lech = d["nhan_nha"] - moc
        d["lech"] = round(lech, 2)
        print(f"{v:26s} {_so_vn(d['nhan_nha']):>8s} {_so_vn(moc):>11s} "
              f"{('+' if lech >= 0 else '') + _so_vn(lech):>7s} "
              f"{d.get('dai_wav', 0):7.2f}s")
    _luu()

    xong = [d for d in ra["doi_chung"].values() if not d.get("loi")
            and "lech" in d]
    thuoc_dung = bool(xong) and all(abs(d["lech"]) <= LECH_CHO_PHEP
                                   for d in xong)
    if xong:
        mx = max(abs(d["lech"]) for d in xong)
        loi_ket = ("THƯỚC + BỘ CÂU TÁI LẬP ĐƯỢC BẢNG CŨ" if thuoc_dung
                   else "KHÔNG TÁI LẬP ĐƯỢC — CỘT KOKORO KHÔNG ĐƯỢC TIN")
        print(f"\nKIỂM THƯỚC: lệch lớn nhất {_so_vn(mx)} · cho phép "
              f"{_so_vn(LECH_CHO_PHEP)} -> {loi_ket}")

    print("\n" + "=" * 78)
    print(f"KOKORO — {len(ma_ds)} giọng, mỗi giọng MỘT lượt `doc_loat` cả loạt")
    print("=" * 78)
    print(f"{'mã giọng':16s} {'nhấn nhá':>9s} {'chữ':>16s} {'tác giả':>8s} "
          f"{'dài WAV':>8s} {'F0 giữa':>9s} {'giây':>6s}")
    from app.core import nhan_nha as NN
    for i, m in enumerate(ma_ds, 1):
        d = ra["kokoro"].get(m)
        if not d or d.get("loi"):
            d = do_kokoro(m, texts)
            d["diem_tac_gia"] = diem.get(m, "?")
            ra["kokoro"][m] = d
            _luu()
        if d.get("loi"):
            print(f"{m:16s} LỖI: {d['loi']}")
            continue
        v = d["nhan_nha"]
        print(f"{m:16s} {_so_vn(v):>9s} {NN.chu(round(v, 1)):>16s} "
              f"{d.get('diem_tac_gia', '?'):>8s} {d.get('dai_wav', 0):7.2f}s "
              f"{d.get('f0_giua_hz', 0):8.1f}Hz {d.get('giay', 0):6.1f}")
    _luu()

    tot = {m: d["nhan_nha"] for m, d in ra["kokoro"].items()
           if m in set(ma_ds) and not d.get("loi")}
    print("\n" + "=" * 78)
    print("KẾT LUẬN")
    print("=" * 78)
    if not tot:
        print("KHÔNG đo được giọng nào.")
        sys.exit(1)
    xs = sorted(tot.values())
    tb = st.fmean(xs)
    print(f"ĐO ĐƯỢC {len(tot)}/{len(ma_ds)} giọng · thấp nhất {_so_vn(xs[0])} · "
          f"cao nhất {_so_vn(xs[-1])} · TRẢI {_so_vn(xs[-1] - xs[0])} · "
          f"TB {_so_vn(tb)} · trung vị {_so_vn(st.median(xs))}")
    for v, moc in DOI_CHUNG:
        d = ra["doi_chung"].get(v) or {}
        if d.get("loi"):
            continue
        n = sum(1 for x in xs if x >= d["nhan_nha"])
        print(f"  so với {v} ({_so_vn(d['nhan_nha'])}): {n}/{len(tot)} giọng "
              f"Kokoro ĐẠT HOẶC HƠN · TB Kokoro "
              f"{'+' if tb >= d['nhan_nha'] else ''}"
              f"{_so_vn(tb - d['nhan_nha'])}")
    # Phân bố theo CHỮ của `nhan_nha.chu` — chấm trên SỐ ĐÃ LÀM TRÒN, đúng luật
    # `nhan_nha.nhan` (Jenny 3,06 không được ghi ngược thành "vừa").
    dem: dict[str, int] = {}
    for x in xs:
        dem[NN.chu(round(x, 1))] = dem.get(NN.chu(round(x, 1)), 0) + 1
    print("  phân bố nhãn (chấm trên số ĐÃ LÀM TRÒN, đúng `nhan_nha.chu`): "
          + " · ".join(f"{k} {v}" for k, v in dem.items()))
    top = sorted(tot.items(), key=lambda kv: -kv[1])[:5]
    day = sorted(tot.items(), key=lambda kv: kv[1])[:5]
    print("  CAO NHẤT: " + " · ".join(f"{k} {_so_vn(v)}" for k, v in top))
    print("  THẤP NHẤT: " + " · ".join(f"{k} {_so_vn(v)}" for k, v in day))
    if not thuoc_dung:
        print("\n*** ĐỐI CHỨNG KHÔNG TÁI LẬP ĐƯỢC BẢNG CŨ -> ĐỪNG GHI CỘT NÀY "
              "VÀO NHÃN ***")
    print(f"\n-> {KQ}")
    shutil.rmtree(SAN, ignore_errors=True)   # không để rác trên máy anh Hùng
