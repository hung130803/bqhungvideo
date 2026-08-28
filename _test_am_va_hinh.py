"""CỔNG 89 — ÂM THANH KHÔNG BỊ BÉ · CHỈNH VIDEO THEO GIỌNG · HỘP BỚT RỐI.

**SỐ CỔNG LÀ 89, VÀ FILE NÀY TRƯỚC ĐÂY TỰ NHẬN LÀ "CỔNG 76" — HAI LỖI CHỒNG
NHAU, ĐỌC TRƯỚC KHI SỬA:**
  · số **76 đã thuộc `_test_nhan_nha.py`** (đang nằm trong `_chay_hoi_quy.CONG`
    với mốc 29). Trùng số thì hai cổng **ghi đè `_kq76.txt` của nhau** — đúng
    bài học 70 vs 69 và 85 vs 81.
  · và file này **KHÔNG HỀ nằm trong `CONG`**, tức nó chỉ là *"một file .py
    nằm đó"* (bẫy cổng 70). Hệ quả ĐO ĐƯỢC: `nhan_nha.muc()` đã đổi chữ ký
    thành **một tham số**, mà MỤC 6 cũ gọi `muc(voice, nn)` -> cổng **CHẾT**
    với `TypeError` giữa chừng và **không ai biết**, vì không lượt hồi quy nào
    gọi nó. Số 89 lấy bằng cách đọc chính `_chay_hoi_quy.CONG` (max đang là
    88), KHÔNG đếm theo trí nhớ.

**MỤC 6 CŨ (nhãn nhấn nhá) ĐÃ BỎ, CÓ LÝ DO:** nó chấm `nhan_nha.nhan_kem` /
`goi_y_giong` / `cau_goi_y` / `BANG_VI` — **cả bốn nay KHÔNG CÒN TỒN TẠI**
trong `app/core/nhan_nha.py`. Phần nhãn nhấn nhá đang được canh bởi cổng **76
`_test_nhan_nha.py` (ĐẠT 31 · HỎNG 0)** cùng 79/84; viết lại ở đây là đẻ bản
sao thứ hai của cùng một phép canh — đúng chỗ đã sinh ra vụ trùng số.

Ba việc anh Hùng nêu 18/08/2026 (ảnh v2.36.0, hộp Thay giọng, `ov:nam_tre`):
  1. *"lỗi quan trọng: âm thanh video bị lỗi hay sao cứ bị bé"*
  2. *"giọng cứ lúc nhanh lúc chậm không đều — đáng nhẽ chỉ chỉnh video sao
     cho khớp giọng nói chứ"*
  3. *"cái phần edit chữ kia nhiều quá, không gom vào làm 1 được à"*
và một việc anh ấy nêu LẠI 20/08/2026: *"điều chỉnh là điều chỉnh VIDEO sao
cho khớp, KHÔNG PHẢI lồng tiếng mới tạo"* -> MỤC 6/7/8 bên dưới.

CỔNG NÀY CANH 8 ĐIỀU:
1. **BÙ DẢI CAO đúng chiều và có TRẦN.** `do_do_sang` phải trả số ÂM cho file
   đục hơn (dấu bị lật là app đi CẮT dải cao đúng lúc cần NÂNG — bẫy đã sập
   thật, xem `do_do_sang`). Bù không bao giờ vượt `BU_SANG_TOI_DA_DB`, và
   nguồn đã sáng bằng gốc thì KHÔNG bù (`BU_SANG_TOI_THIEU_DB`).
2. **HAI THƯỚC ĐỘC LẬP phải khớp** (`astats` của app vs `ebur128`): lệch quá
   0,5 dB là DỪNG, không phải "làm tròn".
3. **BẤT BIẾN `he_so_hinh=1.0`:** lệnh ffmpeg của `thay_audio_video` KHÔNG
   được có `-itsscale`, tức giống TỪNG KÝ TỰ bản trước -> 200-300 kênh đang
   chạy không đổi hành vi.
4. **CHỈNH VIDEO THEO GIỌNG làm ĐÚNG CHIỀU:** `he_so_hinh_can` tính đúng hệ
   số, `tran_hinh_theo_fps` chặn theo fps THẬT, và ffmpeg `-itsscale` phải
   giãn đúng độ dài mà **KHÔNG mã hoá lại một khung nào**.
5. **HỘP THAY GIỌNG:** 9 ô kiểu chữ mặc định GẬP, mở ra là ĐỦ 9, round-trip
   lưu/đọc lại giữ đủ giá trị, và KHÔNG bỏ ô nào.
6. **HỘP CHE CHỮ KHÔNG ĐƯỢC TRÔI KHI LÀM CHẬM HÌNH, VÀ PHỤ ĐỀ PHẢI ĐI THEO.**
   Đây là chỗ dễ vỡ nhất của cả tính năng, và nó **đã vỡ thật**: nhánh che chữ
   dùng `-itsscale`, mà `-itsscale` giãn mốc ĐẦU VÀO nên biến `t` trong
   `enable='between(t,a,b)'` là mốc ĐÃ GIÃN, còn `a,b` do
   `che_chu.loc_cho_xuat` dò trên video GỐC thì CHƯA GIÃN -> hộp che trôi
   `(k−1)·t`, chữ cháy sẵn hiện NGUYÊN từ giữa phim. Chú thích trong mã khẳng
   định NGƯỢC LẠI nên chưa ai đo. Mục này đo bằng **ĐIỂM ẢNH trên file xuất**,
   có ĐỐI CHỨNG `k=1,0` để chứng minh bộ dò có răng.
7. **TẮT CỜ -> RA FILE GIỐNG BẢN MỐC** (nạp `git show <mốc>:…` thành module
   riêng rồi CHẠY THẬT), và **khoá chống trùng khi TẮT giống TỪNG KÝ TỰ** —
   không thì 200-300 kênh xuất lại từ đầu. Kèm chốt *"mốc TRÙNG bản đang test
   -> HỎNG"* chống PASS OAN.
8. **TRẦN LÀM CHẬM HÌNH CÓ RĂNG + LÙI VỀ CÁCH CŨ THÌ GHI LOG.** Quá trần thì
   phần dư vẫn phải ép tiếng, và việc lùi đó phải NÓI RA (`cham_tran`) — lùi
   im lặng là bẫy cả repo này chống.

TỰ KIỂM: `_pha_khop_video.py` gỡ từng chốt ra và cổng phải ĐỎ.
"""
from __future__ import annotations

import ast
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

# PHẢI đặt TRƯỚC mọi import chạm `app.ui` — `app_settings()` mặc định đọc
# REGISTRY THẬT của anh Hùng, và cổng 68 đã ĐỎ OAN một lần vì đúng chuyện đó.
_INI = Path(tempfile.gettempdir()) / f"bq_cong89_{os.getpid()}.ini"
os.environ["BQ_QSETTINGS_INI"] = str(_INI)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TG_BO_QUA_CHI_PHI", "1")

import _test_guard  # noqa: E402,F401  (chặn mở Explorer/trình phát, stdout utf-8)

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: **ĐỌC TỪ `settings`, KHÔNG ghi cứng `bin/ffmpeg.exe`** — `bin/` từng là build
#: 2023 THIẾU `Abs_Peak_count`, tức đo một ffmpeg KHÁC ffmpeg sản xuất (bài học
#: cổng 86). 21 file `_test_*.py` còn ghi cứng nó; file này thì không.
from config import settings  # noqa: E402

FF = Path(str(settings.FFMPEG_PATH))
FP = Path(str(settings.FFPROBE_PATH))
NOWIN = 0x08000000

#: MỐC ĐỐI CHỨNG = bản phát hành **NGAY TRƯỚC** tính năng "Chỉnh video theo
#: giọng". Đã kiểm bằng số, không đoán: `git show v2.37.0:app/core/thay_giong.py
#: | grep -c he_so_hinh` -> **0** · `v2.41.1` -> **19**; `tg_chay.py` cũng
#: 0 (v2.37.0) so với 1 (v2.38.0). **KHÔNG BAO GIỜ dùng `main`** — sau khi gộp
#: thì `main` chính là bản đang test, cổng đối chứng tự PASS OAN vĩnh viễn
#: (bài học cổng 36/51/52/56).
MOC = os.environ.get("BQ_MOC_KV", "v2.37.0")

DAT = HONG = 0
_HOP: Path | None = None


def ok(dieu: bool, ten: str, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return dieu


def hop() -> Path:
    global _HOP
    if _HOP is None:
        _HOP = REPO / f"_am89_{os.getpid()}"
        _HOP.mkdir(exist_ok=True)
    return _HOP


def don() -> None:
    for d in list(REPO.glob("_am89_*")) + list(REPO.glob("_am76_*")):
        shutil.rmtree(d, ignore_errors=True)


def nap_moc(duong: str, ten: str) -> types.ModuleType:
    """Nạp một file của BẢN MỐC thành module riêng (không đụng bản đang test)."""
    r = subprocess.run(["git", "show", f"{MOC}:{duong}"], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise RuntimeError(f"không lấy được {MOC}:{duong}: {r.stderr[:200]}")
    m = types.ModuleType(f"moc_{ten}")
    m.__dict__["__file__"] = f"<{MOC}:{duong}>"
    exec(compile(r.stdout, f"<{MOC}:{duong}>", "exec"), m.__dict__)
    m.__dict__["_NGUON_"] = r.stdout
    return m


#: **`QApplication` PHẢI CÓ THAM CHIẾU Ở MỨC MODULE.** Bản đầu của MỤC 9 viết
#: `QApplication.instance() or QApplication([])` mà KHÔNG giữ lại kết quả:
#: `muc5` tạo app trong một biến CỤC BỘ, biến đó chết khi `muc5` trả về, nên
#: tới MỤC 9 `instance()` trả `None` -> tạo app mới -> Python thu hồi ngay dòng
#: sau -> **tiến trình CHẾT CỨNG (mã 0xC0000409), KHÔNG traceback, KHÔNG dòng
#: tổng kết**. `_pha_khop_video.py` đọc ra "CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ" và dừng
#: hẳn — tức một lỗi của CỔNG làm hỏng cả lượt thử phá mà không nói vì sao.
_APP = None


def app_qt():
    """QApplication dùng chung cho MỌI mục — giữ tham chiếu, xem `_APP`."""
    global _APP
    from PyQt6.QtWidgets import QApplication
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


def than_ham(duong: str, ten: str) -> ast.AST:
    """Nút AST của hàm `ten`. Đọc file bằng **utf-8 tường minh** —
    `inspect.getsource` mở theo bảng mã MẶC ĐỊNH của máy (cp1252) nên docstring
    tiếng Việt ra mojibake rồi `ast.parse` nổ (bẫy đã sập ở cổng 71)."""
    cay = ast.parse((REPO / duong).read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    raise RuntimeError(f"không thấy hàm {ten} trong {duong}")


def _ff(args: list[str], timeout: int = 900) -> int:
    r = subprocess.run([str(FF), "-y", "-hide_banner", "-nostdin", *args],
                       capture_output=True, creationflags=NOWIN,
                       timeout=timeout)
    return r.returncode


def _probe(path: Path, ent: str, vid: bool = True) -> str:
    a = [str(FP), "-v", "error"]
    if vid:
        a += ["-select_streams", "v:0"]
    a += ["-show_entries", ent, "-of", "csv=p=0", str(path)]
    r = subprocess.run(a, capture_output=True, text=True,
                       creationflags=NOWIN, timeout=300)
    return (r.stdout or "").strip()


def _ebur_i(path: Path, af: str) -> float:
    """I (LUFS) qua `ebur128` — THƯỚC ĐỘC LẬP với `astats` mà app dùng."""
    import re
    r = subprocess.run(
        [str(FF), "-y", "-hide_banner", "-nostdin", "-i", str(path),
         "-map", "0:a:0", "-af", f"{af},ebur128=peak=true:framelog=verbose",
         "-f", "null", "-"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", creationflags=NOWIN, timeout=900)
    tom = (r.stderr or "").rsplit("Summary:", 1)[-1]
    m = re.search(r"I:\s*(-?\d+\.?\d*)", tom)
    return float(m.group(1)) if m else float("nan")


# ==================================================================
def nguon_tieng(ten: str, sang: bool) -> Path:
    """WAV 8 giây tự sinh: `sang=True` có dải cao, `False` bị cắt trên 3,5 kHz.

    Tự sinh bằng `lavfi` nên KHÔNG phụ thuộc kho video trên đĩa (bài học cổng
    47 CA2 / 68: ghi cứng tên file là cổng ĐỎ OAN vì KHO chứ không vì mã).
    """
    p = hop() / ten
    # Tiếng nói giả: nhiều hoà âm để có năng lượng cả dải trầm lẫn dải cao.
    # BẪY: với `-f lavfi -i "<graph>"` thì đầu ra CUỐI phải KHÔNG có nhãn —
    # đặt `[m]` rồi `-map "[m]"` là ffmpeg báo *"Invalid outpad name"* và chết
    # cả lệnh (đã sập 1 lần khi viết cổng này).
    src = ("sine=f=180:d=8[a];sine=f=900:d=8[b];sine=f=2500:d=8[c];"
           "sine=f=6000:d=8[d];sine=f=11000:d=8[e];"
           "[a][b][c][d][e]amix=inputs=5:normalize=0")
    # `poles` của `lowpass` chỉ nhận 1-2 — đặt 4 là ffmpeg CHẾT cả lệnh
    # ("Value 4.000000 for parameter 'poles' out of range"). Xếp tầng 3 lượt
    # `poles=2` để dốc cắt đủ sâu.
    af = "" if sang else (",lowpass=f=3500:poles=2" * 3)
    rc = _ff(["-f", "lavfi", "-i", f"{src}",
              "-af", f"volume=0.2{af}", "-ac", "2", "-ar", "44100",
              "-c:a", "pcm_s16le", str(p)])
    if rc != 0 or not p.exists() or p.stat().st_size < 10000:
        raise RuntimeError(f"không dựng được nguồn {ten}")
    return p


def muc1() -> None:
    """BÙ DẢI CAO — chiều, trần, và sàn bỏ qua."""
    print("\nMỤC 1 — bù dải cao đúng chiều, có trần")
    from app.core import thay_giong as tg
    sang = nguon_tieng("sang.wav", True)
    duc = nguon_tieng("duc.wav", False)

    s_sang = tg.do_do_sang(sang)
    s_duc = tg.do_do_sang(duc)
    ok(s_sang == s_sang and s_duc == s_duc,      # không phải nan
       "`do_do_sang` đo được cả hai file", f"{s_sang:.2f} / {s_duc:.2f}")
    # CHIỀU: file bị cắt dải cao phải ra số NHỎ HƠN. Dấu lật là app đi CẮT dải
    # cao đúng lúc cần NÂNG — bẫy đã sập thật khi viết `do_do_sang`.
    ok(s_duc < s_sang - 3.0,
       "file ĐỤC ra độ sáng THẤP HƠN file sáng (đúng CHIỀU)",
       f"đục {s_duc:.2f} < sáng {s_sang:.2f}")

    # THƯỚC THỨ HAI: `ebur128` phải cho cùng kết luận, lệch <= 0,5 dB.
    def sang_ebur(p: Path) -> float:
        hi = "highpass=f=4000:poles=2,highpass=f=4000:poles=2"
        mid = ("highpass=f=300:poles=2,highpass=f=300:poles=2,"
               "lowpass=f=3000:poles=2,lowpass=f=3000:poles=2")
        return _ebur_i(p, hi) - _ebur_i(p, mid)
    e_sang, e_duc = sang_ebur(sang), sang_ebur(duc)
    d1 = abs((s_sang - s_duc) - (e_sang - e_duc))
    ok(d1 <= 0.5,
       "HAI THƯỚC ĐỘC LẬP khớp (astats vs ebur128) trong 0,5 dB",
       f"astats {s_sang - s_duc:+.2f} · ebur128 {e_sang - e_duc:+.2f} "
       f"· lệch {d1:.2f}")

    # TRẦN: thiếu bao nhiêu cũng không bù quá `BU_SANG_TOI_DA_DB`
    thieu = s_sang - s_duc
    ok(thieu > tg.BU_SANG_TOI_DA_DB,
       "nguồn thử thiếu NHIỀU HƠN trần -> ca chạm trần có răng",
       f"thiếu {thieu:.2f} > trần {tg.BU_SANG_TOI_DA_DB}")
    ra = hop() / "duc_bu.wav"
    tg.bu_sang(duc, ra, min(thieu, tg.BU_SANG_TOI_DA_DB))
    s_sau = tg.do_do_sang(ra)
    ok(s_sau > s_duc + 1.0, "bù xong thì SÁNG HƠN thật",
       f"{s_duc:.2f} -> {s_sau:.2f}")
    ok(s_sau - s_duc <= tg.BU_SANG_TOI_DA_DB + 1.0,
       "KHÔNG bù quá trần", f"nâng {s_sau - s_duc:.2f} dB")
    # ĐỘ DÀI không đổi (bẫy "ffmpeg mã 0 mà file sai")
    ok(abs(tg.probe_duration(ra) - tg.probe_duration(duc)) < 0.05,
       "bù sáng KHÔNG đổi độ dài",
       f"{tg.probe_duration(duc):.3f} -> {tg.probe_duration(ra):.3f}")
    # SÀN: file so với CHÍNH NÓ thì thiếu 0 -> phải bỏ qua
    ok(abs(tg.do_do_sang(sang) - s_sang) < 0.6,
       "đo lại cùng file ra cùng số (thước TIỀN ĐỊNH)")
    ok(tg.BU_SANG_TOI_THIEU_DB > 0,
       "có SÀN bỏ qua (nguồn đã sáng bằng gốc thì không bù)",
       f"{tg.BU_SANG_TOI_THIEU_DB} dB")


def muc2() -> None:
    """`tron_thay_giong` phải THẬT SỰ gọi bù sáng, và trước chuẩn hoá độ to."""
    print("\nMỤC 2 — bù sáng nối vào đúng chỗ (quét AST, không quét chuỗi)")
    import ast
    src = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef)
                and n.name == "tron_thay_giong"), None)
    ok(ham is not None, "tìm thấy `tron_thay_giong`")
    if ham is None:
        return
    goi = [n.func.id for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    ok("bu_sang" in goi, "`tron_thay_giong` THẬT SỰ gọi `bu_sang`",
       str(sorted(set(goi))))
    ok("chuan_do_to" in goi, "vẫn gọi `chuan_do_to` (chốt cổng 65 còn nguyên)")
    # THỨ TỰ: bù sáng đổi độ to, nên phải bù XONG rồi mới đo-và-nâng.
    d_bu = min((n.lineno for n in ast.walk(ham) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "bu_sang"),
               default=10 ** 9)
    d_do = min((n.lineno for n in ast.walk(ham) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "chuan_do_to"), default=-1)
    ok(d_bu < d_do, "BÙ SÁNG đứng TRƯỚC chuẩn hoá độ to",
       f"dòng bù {d_bu} < dòng chuẩn hoá {d_do}")
    # `thay_giong_video` phải truyền `goc_wav` — thiếu là bước bù TỰ TẮT im lặng
    hv = next((n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)
               and n.name == "thay_giong_video"), None)
    kw = set()
    for n in ast.walk(hv) if hv else []:
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "tron_thay_giong":
            kw = {k.arg for k in n.keywords}
    ok("goc_wav" in kw,
       "`thay_giong_video` truyền `goc_wav` (thiếu là bù TỰ TẮT im lặng)",
       str(sorted(kw)))


def muc3() -> None:
    """BẤT BIẾN: he_so_hinh=1.0 -> KHÔNG có `-itsscale` trong lệnh ffmpeg."""
    print("\nMỤC 3 — BẤT BIẾN: không bật chỉnh hình thì lệnh ffmpeg y như cũ")
    from app.core import thay_giong as tg
    bat: list[list[str]] = []
    that = tg._ffmpeg

    def ghi(args, what, timeout=900):        # noqa: ANN001
        bat.append(list(args))
        return None
    tg._ffmpeg = ghi
    try:
        tg.thay_audio_video("v.mp4", "a.wav", "r.mp4", che_chu=False)
        tg.thay_audio_video("v.mp4", "a.wav", "r.mp4", che_chu=False,
                            he_so_hinh=1.0)
        tg.thay_audio_video("v.mp4", "a.wav", "r2.mp4", che_chu=False,
                            he_so_hinh=1.2)
    finally:
        tg._ffmpeg = that
    ok(len(bat) == 3, "bắt được 3 lệnh ffmpeg", str(len(bat)))
    if len(bat) != 3:
        return
    ok("-itsscale" not in bat[0],
       "KHÔNG truyền he_so_hinh -> lệnh KHÔNG có `-itsscale`")
    ok(bat[0] == bat[1],
       "he_so_hinh=1.0 ra lệnh GIỐNG TỪNG KÝ TỰ lối gọi cũ")
    ok("-itsscale" in bat[2] and bat[2][bat[2].index("-itsscale") + 1]
       .startswith("1.2"),
       "he_so_hinh=1.2 -> CÓ `-itsscale 1.2`",
       " ".join(bat[2][:4]))
    ok(bat[2].index("-itsscale") < bat[2].index("-i"),
       "`-itsscale` đứng TRƯỚC `-i` (đặt sau thì ffmpeg bỏ qua im lặng)")


def muc4() -> None:
    """`he_so_hinh_can` + `tran_hinh_theo_fps` + itsscale chạy THẬT."""
    print("\nMỤC 4 — chỉnh video theo giọng: hệ số, trần, và ffmpeg thật")
    from app.core import thay_giong as tg

    # --- hàm THUẦN: trần theo fps ---
    ok(abs(tg.tran_hinh_theo_fps(23.976) - 23.976 / 20.0) < 1e-6,
       "trần theo fps: nguồn 23,976 -> k <= 1,199",
       f"{tg.tran_hinh_theo_fps(23.976):.4f}")
    ok(tg.tran_hinh_theo_fps(60.0) == tg.TRAN_CHINH_HINH,
       "nguồn 60 fps bị TRẦN CỨNG chặn (không cho chậm 3 lần)",
       f"{tg.tran_hinh_theo_fps(60.0)}")
    ok(tg.tran_hinh_theo_fps(0.0) == tg.TRAN_CHINH_HINH,
       "đọc fps hỏng -> lùi về trần cứng, KHÔNG chia cho 0")

    # --- hệ số cần: dựng câu + file tiếng độ dài BIẾT TRƯỚC ---
    d = hop() / "hs"
    d.mkdir(exist_ok=True)
    fs = []
    for i, giay in enumerate((1.0, 2.4, 1.0)):
        p = d / f"c{i}.wav"
        _ff(["-f", "lavfi", "-i", f"sine=f=300:d={giay}", "-ac", "2",
             "-ar", "44100", "-c:a", "pcm_s16le", str(p)])
        fs.append(str(p))
    # khung câu: 0-2s, 2-4s, 4-6s -> câu giữa cần 2,4/(2-0,12) = 1,277
    cau = [{"start": 0.0, "end": 2.0}, {"start": 2.0, "end": 4.0},
           {"start": 4.0, "end": 6.0}]
    c = tg.he_so_hinh_can(cau, fs, [True] * 3, 6.0)
    ok(1.25 < c["k_can"] < 1.31,
       "hệ số cần tính ĐÚNG theo câu chật nhất",
       f"k_can {c['k_can']} · câu {c['cau_chat_nhat']}")
    ok(c["cau_chat_nhat"] == 1, "chỉ ra ĐÚNG câu chật nhất (câu 2,4 giây)")
    c2 = tg.he_so_hinh_can(cau, fs, [False] * 3, 6.0)
    ok(c2["k_can"] == 1.0, "không câu nào đọc được -> k = 1,0 (không chậm hình)")

    # --- khớp thời gian: he_so_hinh làm hệ số ép về 1,0 ---
    o1 = hop() / "k1"
    o2 = hop() / "k2"
    o1.mkdir(exist_ok=True)
    o2.mkdir(exist_ok=True)
    a = tg.khop_thoi_gian(cau, fs, [True] * 3, 6.0, o1)
    b = tg.khop_thoi_gian(cau, fs, [True] * 3, 6.0, o2,
                          he_so_hinh=float(c["k_can"]))
    ok(a["tempo_max"] > 1.05,
       "KHÔNG chỉnh hình -> vẫn phải ÉP giọng", f"tempo_max {a['tempo_max']}")
    ok(b["tempo_max"] <= 1.001,
       "CÓ chỉnh hình -> hệ số ép về 1,000 cho MỌI câu",
       f"tempo_max {b['tempo_max']} · trải {b['tempo_trai']}")
    ok(b["tempo_trai"] <= a["tempo_trai"],
       "TRẢI hệ số ép không tăng",
       f"{a['tempo_trai']} -> {b['tempo_trai']}")
    ok(b["chong_lan_ms_max"] <= 1.0,
       "BẤT BIẾN 0 ms chồng lấn vẫn giữ",
       f"{b['chong_lan_ms_max']} ms")
    ok(abs(b["do_dai_ra"] - 6.0 * float(c["k_can"])) < 0.01,
       "độ dài đầu ra = tổng × hệ số", f"{b['do_dai_ra']}")
    # MỐC ĐẶT CÂU PHẢI GIÃN THEO `k` — mục này do THỬ PHÁ lôi ra (phép 5 của
    # `_pha_khop_video.py` LỌT ở lượt đầu). Gỡ phép nhân `k` khỏi mốc ĐẦU câu
    # (`a = float(c["start"]) * k` -> `a = float(c["start"])`) thì `khung =
    # b − a` PHỒNG TO HƠN cả `k` (vì `b` vẫn giãn), câu nào cũng lọt khung nên
    # `tempo_max` vẫn 1,000 và mọi mục trên vẫn XANH — trong khi tiếng bị đặt
    # ở mốc CHƯA GIÃN của một video ĐÃ GIÃN, tức **tiếng trôi khỏi hình mỗi
    # lúc một xa**. Đúng lỗi v1.87. Vì vậy phải chấm THẲNG chỗ đặt mảnh.
    lech_moc = [abs(off - float(cau[i]["start"]) * float(c["k_can"]))
                for i, (off, _p) in enumerate(b["manh"])]
    ok(lech_moc and max(lech_moc) < 0.01,
       "mốc ĐẶT từng câu giãn ĐÚNG hệ số (tiếng không trôi khỏi hình)",
       f"lệch max {max(lech_moc) * 1000:.1f} ms / {len(lech_moc)} câu"
       if lech_moc else "KHÔNG có mảnh nào")
    # ĐỐI CHỨNG: arm KHÔNG chỉnh hình thì mốc phải trùng mốc GỐC. Thiếu mục
    # này thì phép so trên có thể đúng vì một lý do khác.
    lech_1 = [abs(off - float(cau[i]["start"]))
              for i, (off, _p) in enumerate(a["manh"])]
    ok(lech_1 and max(lech_1) < 0.01,
       "ĐỐI CHỨNG k=1,0: mốc đặt câu trùng mốc GỐC",
       f"lệch max {max(lech_1) * 1000:.1f} ms")

    # --- ffmpeg THẬT: itsscale giãn đúng, KHÔNG mã hoá lại khung nào ---
    v = hop() / "v.mp4"
    _ff(["-f", "lavfi", "-i", "testsrc2=size=320x240:rate=24:d=5",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         str(v)])
    au = hop() / "a6.wav"
    _ff(["-f", "lavfi", "-i", "sine=f=300:d=6", "-ac", "2", "-ar", "44100",
         "-c:a", "pcm_s16le", str(au)])
    ok(v.exists() and int(_probe(v, "stream=nb_frames") or 0) > 0,
       "dựng được video thử", f"{_probe(v, 'stream=nb_frames')} khung")
    r = hop() / "r.mp4"
    tg.thay_audio_video(v, au, r, che_chu=False, he_so_hinh=1.2)
    kn = int(_probe(v, "stream=nb_frames") or 0)
    kr = int(_probe(r, "stream=nb_frames") or 0)
    dur = float(_probe(r, "format=duration", vid=False) or 0)
    ok(r.exists() and r.stat().st_size > 5000 and kr > 0,
       "ra file có khung hình (bẫy mã 0 + 0 KiB)",
       f"{r.stat().st_size} byte · {kr} khung · {dur:.3f}s")
    ok(kr == kn, "KHÔNG mã hoá lại một khung nào (số khung TRÙNG nguồn)",
       f"{kn} -> {kr}")
    ok(abs(dur - 5.0 * 1.2) < 0.15,
       "độ dài giãn ĐÚNG hệ số", f"5,000 × 1,2 = 6,000 · đo {dur:.3f}")
    fps = tg.do_fps(r)
    ok(abs(fps * 1.2 - 24.0) < 0.6 or abs(tg.do_fps(v) / 1.2 - fps) < 0.6,
       "nhịp hình tụt ĐÚNG theo hệ số (đây là GIÁ, phải đo được)",
       f"{tg.do_fps(v):.3f} -> {fps:.3f} fps")


def muc5() -> None:
    """HỘP THAY GIỌNG: gập mặc định, mở ra đủ 9 ô, round-trip giữ đủ."""
    print("\nMỤC 5 — hộp Thay giọng: gọn mà KHÔNG bỏ ô nào")
    app = app_qt()
    from app.ui.thay_giong_dialog import ThayGiongDialog
    d = ThayGiongDialog(None)
    try:
        ok(len(d._o_kieu_chu) == 9, "vẫn đủ 9 ô kiểu chữ",
           str(len(d._o_kieu_chu)))
        ok(hasattr(d, "b_kc_gap") and not d.b_kc_gap.isChecked(),
           "mặc định GẬP")
        ok(not d._khung_kc.isVisible() or not d._khung_kc.isVisibleTo(d),
           "khu 9 ô đang ẨN ở trạng thái mặc định")
        # mở ra: phải hiện
        d.ck_che.setChecked(True)
        d.ck_viet.setChecked(True)
        d.b_kc_gap.setChecked(True)
        app.processEvents()
        ok(d._khung_kc.isVisibleTo(d), "bấm nút thì khu 9 ô HIỆN ra")
        ok(all(o.isEnabled() for o in d._o_kieu_chu),
           "mở ra thì cả 9 ô chỉnh được")
        # nhãn tóm tắt phải NÓI RA trạng thái
        d.b_kc_gap.setChecked(False)
        app.processEvents()
        ok(bool(d.lb_kc_tt.text()),
           "gập lại vẫn có nhãn tóm tắt (không che mất thông tin)",
           d.lb_kc_tt.text())
        # --- ROUND-TRIP: đặt đủ 9 ô, lưu, dựng lại, phải còn đủ ---
        d.cb_kc_preset.setCurrentIndex(1)
        d.cb_kc_font.setCurrentIndex(2)
        d.sp_kc_co.setValue(8.5)
        d.cb_kc_vitri.setCurrentIndex(3)
        d.cb_kc_dam.setCurrentIndex(1)
        d.cb_kc_nghieng.setCurrentIndex(2)
        d._kc_mau = "#FF0000"
        d._kc_vien = "#FFFFFF"
        d.sp_kc_dovien.setValue(14.0)
        truoc = dict(d.don_kieu_chu())
        ok(len(truoc) == 9, "đặt đủ 9 ô -> đơn thuốc có 9 khoá",
           str(sorted(truoc)))
        d.luu_cai_dat()
        d.deleteLater()
        d2 = ThayGiongDialog(None)
        try:
            sau = dict(d2.don_kieu_chu())
            ok(sau == truoc, "ROUND-TRIP lưu/đọc lại giữ ĐỦ 9 giá trị",
               f"{len(sau)} khoá")
            ok(not d2.b_kc_gap.isChecked(),
               "mở lại vẫn GẬP (gập là cách bày, không phải giá trị)")
            ok(bool(d2.lb_kc_tt.text()) and "9" in d2.lb_kc_tt.text(),
               "nhãn tóm tắt nói ĐÚNG số ô đã đổi", d2.lb_kc_tt.text())
        finally:
            d2.deleteLater()
    finally:
        d.deleteLater()


#: bề cao "dải chữ" ở đáy khung nguồn thử (điểm ảnh)
_DAY = 40
#: cửa sổ mà dải TRẮNG hiện ở đáy khung — mốc BIẾT TRƯỚC trên trục NGUỒN
_CHU_A, _CHU_B = 3.0, 4.0
#: cửa sổ của cue phụ đề — mốc BIẾT TRƯỚC trên trục **ĐẦU RA** (đã nhân `k`),
#: đúng như `khop_thoi_gian.moc_tieng` trả về.
_SUB_A, _SUB_B = 5.0, 6.0


#: ngưỡng "điểm ảnh TRẮNG" — nền nguồn là XÁM (#808080, luma ~126) nên 200 tách
#: sạch hai bên. Đếm TỈ LỆ điểm ảnh trắng chứ không lấy TRUNG BÌNH: hộp chữ chỉ
#: phủ một phần dải nên trung bình bị nền xám kéo về giữa, không đọc được.
_NG_TRANG = 200


def _ty_trang(vid: Path, t: float, w: int, y0: int, cao: int) -> float:
    """Tỉ lệ điểm ảnh TRẮNG trong dải `y0..y0+cao` tại mốc `t` giây (0..1).

    Đọc ĐIỂM ẢNH, không đọc `rc` của ffmpeg — cả bản TRÔI lẫn bản ĐÚNG đều cho
    `rc=0` và đủ khung, nên `rc` không phân biệt được gì.
    """
    r = subprocess.run(
        [str(FF), "-v", "error", "-ss", f"{t:.3f}", "-i", str(vid),
         "-frames:v", "1", "-vf", f"crop={w}:{cao}:0:{y0}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, creationflags=NOWIN, timeout=120)
    b = r.stdout
    if not b:
        return -1.0
    return sum(1 for v in b if v >= _NG_TRANG) / len(b)


def _quet(vid: Path, w: int, y0: int, cao: int,
          buoc: float = 0.2) -> list[tuple[float, float]]:
    """[(mốc giây, tỉ lệ trắng)] — quét dày `buoc` giây suốt cả file."""
    d = float(_probe(vid, "format=duration", vid=False) or 0)
    ra, t = [], 0.05
    while t < d - 0.05:
        ra.append((t, _ty_trang(vid, t, w, y0, cao)))
        t += buoc
    return ra


def _cua_so_trang(xs: list[tuple[float, float]],
                  nguong: float = 0.10) -> tuple[float, float]:
    """(mốc ĐẦU, mốc CUỐI) của khoảng có tỉ lệ trắng vượt `nguong`."""
    co = [t for t, v in xs if v >= nguong]
    return (min(co), max(co)) if co else (-1.0, -1.0)


def muc6() -> None:
    """HỘP CHE CHỮ KHÔNG TRÔI KHI LÀM CHẬM HÌNH + PHỤ ĐỀ ĐI THEO."""
    print("\nMỤC 6 — che chữ + làm chậm hình: hộp phải BÁM, chữ phải ĐI THEO")
    from app.core import che_chu as CC
    from app.core import thay_giong as tg

    W, H, FPS, DAI = 320, 240, 24.0, 6.0
    K = 1.25
    d = hop() / "che"
    d.mkdir(exist_ok=True)

    # NGUỒN: nền XÁM (không đen — phải phân biệt được "bị hộp phủ đen" với
    # "vốn không có chữ"), dải TRẮNG ở đáy chỉ trong [_CHU_A, _CHU_B].
    src = d / "goc.mp4"
    _ff(["-f", "lavfi", "-i", f"color=c=gray:s={W}x{H}:r={FPS:g}:d={DAI:g}",
         "-vf", (f"drawbox=x=0:y={H - _DAY}:w={W}:h={_DAY}:color=white:"
                 f"t=fill:enable='between(t,{_CHU_A},{_CHU_B})'"),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
         "-pix_fmt", "yuv420p", str(src)])
    au = d / "a.wav"
    _ff(["-f", "lavfi", "-i", f"sine=f=300:d={DAI * K:g}", "-ac", "2",
         "-ar", "44100", "-c:a", "pcm_s16le", str(au)])
    ok(src.exists() and int(_probe(src, "stream=nb_frames") or 0) > 0,
       "6a dựng được nguồn có dải chữ ở đáy",
       f"{_probe(src, 'stream=nb_frames')} khung")

    # Chuỗi che GIẢ — đúng khuôn `che_chu` sinh ra: `drawbox` phủ khối kèm
    # `enable='between(t,a,b)'`, với a,b là mốc dò được trên video GỐC.
    _LOC = (f"drawbox=x=0:y={H - _DAY}:w={W}:h={_DAY}:color=black:"
            f"t=fill:enable='between(t,{_CHU_A},{_CHU_B})'")

    class _Dai:            # đủ để `thay_audio_video` chịu viết chữ mới
        co_chu, cao_dai, y0, y1 = True, _DAY, H - _DAY, H

        def dict(self) -> dict:
            return {"y0": self.y0, "y1": self.y1}

    # PHỤ ĐỀ THẬT: khối TRẮNG ĐẶC ở ĐỈNH khung, chỉ hiện trong cửa sổ
    # `_SUB_A.._SUB_B` **trên trục ĐẦU RA** (đúng như `khop_thoi_gian.moc_tieng`
    # trả về — nó đã nhân `k`). Đặt ở ĐỈNH để phép đo phụ đề không lẫn với phép
    # đo hộp che ở ĐÁY. `BorderStyle: 3` + `BackColour` trắng cho ra một khối
    # ĐẶC, đếm điểm ảnh chắc tay hơn hẳn nét chữ mảnh.
    _ASS = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,34,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,"
        "&H00FFFFFF,0,0,0,0,100,100,0,0,3,3,0,8,0,0,2,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:0{_SUB_A:.2f},0:00:0{_SUB_B:.2f},Default,"
        "0,0,0,,MMMMMMMMMMMMMM\n")

    goc_loc, goc_ass = CC.loc_cho_xuat, CC.ghi_ass
    goc_ff = tg._ffmpeg
    lenh: list[list[str]] = []

    def _ghi_lenh(args, what, timeout=900):     # noqa: ANN001
        lenh.append(list(args))
        return goc_ff(args, what, timeout=timeout)

    def _ghi_ass(dong, duong, dai, **k):        # noqa: ANN001
        # Ghi file .ass THẬT rồi để `chuoi_subtitles` THẬT lo phần thoát ký tự
        # đường dẫn — vá cả hai là mất luôn phép canh chỗ dễ sai đó.
        Path(duong).write_text(_ASS, encoding="utf-8")
        return True

    try:
        CC.loc_cho_xuat = lambda *a, **k: (_LOC, _Dai(), "giả lập")
        CC.ghi_ass = _ghi_ass

        # ---- lệnh ffmpeg: KHÔNG `-itsscale`, CÓ `setpts`, ĐÚNG THỨ TỰ ----
        tg._ffmpeg = _ghi_lenh
        r1 = d / "ra_k125.mp4"
        tg.thay_audio_video(src, au, r1, che_chu=True,
                            dong_chu=[(0.5, 1.5, "chữ")], he_so_hinh=K)
        lc = lenh[-1]
        fc = lc[lc.index("-filter_complex") + 1] if "-filter_complex" in lc \
            else ""
        ok("-itsscale" not in lc,
           "6b nhánh che chữ KHÔNG dùng `-itsscale` (nó giãn mốc TRƯỚC filter)",
           "sạch" if "-itsscale" not in lc else " ".join(lc[:4]))
        ok(f"setpts=PTS*{K:.6f}" in fc,
           "6c phép giãn nằm TRONG chuỗi filter (`setpts`)",
           f"setpts=PTS*{K:.6f}")
        i_loc, i_sp, i_sub = (fc.find("drawbox"), fc.find("setpts=PTS*"),
                              fc.find("subtitles="))
        ok(0 <= i_loc < i_sp < i_sub,
           "6d THỨ TỰ: che (mốc NGUỒN) -> setpts -> phụ đề (mốc ĐẦU RA)",
           f"che@{i_loc} · setpts@{i_sp} · sub@{i_sub}")

        # ---- BẤT BIẾN: he_so_hinh=1,0 -> KHÔNG setpts, KHÔNG itsscale ----
        lenh.clear()
        r0 = d / "ra_k1.mp4"
        tg.thay_audio_video(src, au, r0, che_chu=True,
                            dong_chu=[(0.5, 1.5, "chữ")], he_so_hinh=1.0)
        lc0 = lenh[-1]
        fc0 = lc0[lc0.index("-filter_complex") + 1]
        ok("-itsscale" not in lc0 and "setpts" not in fc0,
           "6e BẤT BIẾN k=1,0: không setpts, không itsscale (giống bản trước)")
    finally:
        tg._ffmpeg = goc_ff
        CC.loc_cho_xuat, CC.ghi_ass = goc_loc, goc_ass

    # ---- ĐO ĐIỂM ẢNH trên FILE XUẤT THẬT ----
    # dải TRẮNG ~235-255 · nền XÁM ~126 · bị phủ đen ~16
    q1 = _quet(r1, W, H - _DAY, _DAY)
    q0 = _quet(r0, W, H - _DAY, _DAY)
    t1 = max(v for _, v in q1)
    t0 = max(v for _, v in q0)
    ok(t0 < 0.10,
       "6f ĐỐI CHỨNG k=1,0 -> hộp che KÍN (dải trắng không lọt)",
       f"trắng nhiều nhất {t0 * 100:.1f}%")
    ok(t1 < 0.10,
       "6g k=1,25 -> hộp che VẪN KÍN (không trôi)",
       f"trắng nhiều nhất {t1 * 100:.1f}%")
    d1 = float(_probe(r1, "format=duration", vid=False) or 0)
    ok(abs(d1 - DAI * K) < 0.2,
       "6h độ dài ra ĐÚNG hệ số", f"{DAI:g}×{K} = {DAI * K:g} · đo {d1:.3f}")
    kn = int(_probe(src, "stream=nb_frames") or 0)
    k1 = int(_probe(r1, "stream=nb_frames") or 0)
    ok(k1 == kn and kn > 0,
       "6i KHÔNG MẤT KHUNG khi giãn bằng setpts", f"{kn} -> {k1}")

    # ---- PHỤ ĐỀ ĐI THEO: cue trên trục ĐẦU RA phải hiện ĐÚNG mốc đó ----
    # Đây là phép canh chống LỖI v1.87 "hình một đằng tiếng một đằng": đặt
    # `setpts` SAU `subtitles` thì cue [5,6] rơi vào output [6,25 · 7,50].
    sa, sb = _cua_so_trang(_quet(r1, W, 0, _DAY, buoc=0.1), nguong=0.10)
    ok(abs(sa - _SUB_A) < 0.35 and abs(sb - _SUB_B) < 0.35,
       "6k PHỤ ĐỀ hiện ĐÚNG mốc trên trục ĐẦU RA (chữ không trôi khỏi tiếng)",
       f"đặt [{_SUB_A:.2f}, {_SUB_B:.2f}] · đo [{sa:.2f}, {sb:.2f}]")

    # ---- CHỐT CHỐNG ĐẠT-OAN: dựng lại LỆNH CŨ, bộ dò PHẢI kêu ----
    # Không có mục này thì 6f/6g có thể ĐẠT chỉ vì phép đo không thấy gì —
    # đúng bệnh "phép đo phát chứng nhận" (`astats` cổng 53).
    rc = d / "ra_cu.mp4"
    _ff(["-itsscale", f"{K:.6f}", "-i", str(src), "-filter_complex",
         f"[0:v]{_LOC}[v]", "-map", "[v]", "-c:v", "libx264",
         "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
         str(rc)])
    tc = max(v for _, v in _quet(rc, W, H - _DAY, _DAY))
    ok(tc > 0.50,
       "6l BỘ DÒ CÓ RĂNG: dựng lại cách CŨ (-itsscale) thì dải trắng LỌT",
       f"trắng nhiều nhất {tc * 100:.1f}%")


def muc7() -> None:
    """TẮT CỜ -> GIỐNG BẢN MỐC: cả lệnh ffmpeg lẫn khoá chống trùng."""
    print(f"\nMỤC 7 — bất biến khi TẮT, mốc đối chứng {MOC}")
    from app.core import tg_chay as TC
    from app.core import thay_giong as tg

    moc_tg = nap_moc("app/core/thay_giong.py", "tg")
    nay_tg = (REPO / "app/core/thay_giong.py").read_text(encoding="utf-8")
    ok(moc_tg.__dict__["_NGUON_"] != nay_tg,
       "7a bản mốc KHÁC bản đang test (chống so-nó-với-chính-nó)", f"mốc {MOC}")
    ok("he_so_hinh" not in moc_tg.__dict__["_NGUON_"],
       "7b mốc KHÔNG hề có `he_so_hinh` (mốc đúng = bản NGAY TRƯỚC tính năng)")

    # --- lệnh ffmpeg của `thay_audio_video` khi TẮT: giống TỪNG KÝ TỰ ---
    d = hop() / "bb"
    d.mkdir(exist_ok=True)
    v = d / "v.mp4"
    _ff(["-f", "lavfi", "-i", "color=c=gray:s=160x120:r=24:d=3",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         str(v)])
    a = d / "a.wav"
    _ff(["-f", "lavfi", "-i", "sine=f=300:d=3", "-ac", "2", "-ar", "44100",
         "-c:a", "pcm_s16le", str(a)])

    def _bat(mod, ra: Path, **kw) -> list[str]:
        got: list[list[str]] = []
        goc = mod._ffmpeg
        mod._ffmpeg = lambda args, what, timeout=900: got.append(list(args))
        try:
            mod.thay_audio_video(v, a, ra, che_chu=False, **kw)
        finally:
            mod._ffmpeg = goc
        return got[-1] if got else []

    l_moc = _bat(moc_tg, d / "m.mp4")
    l_nay = _bat(tg, d / "n.mp4")
    # Tham số CUỐI là đường ra, cố ý khác nhau -> so phần trước nó.
    ok(bool(l_nay) and len(l_moc) == len(l_nay) and l_moc[:-1] == l_nay[:-1],
       "7c TẮT -> lệnh ffmpeg GIỐNG TỪNG KÝ TỰ bản mốc",
       f"{len(l_nay)} tham số")
    ok("-itsscale" not in l_nay, "7d TẮT -> KHÔNG có `-itsscale`")

    # --- khoá chống trùng ---
    moc_tc = nap_moc("app/core/tg_chay.py", "tc")
    ok("htg" not in moc_tc.__dict__["_NGUON_"],
       "7e mốc `tg_chay` KHÔNG hề có đuôi `htg`")
    bo = [
        (("D:/v/a.mp4", "vi", "vi-VN-NamMinhNeural", "D:/ra"), {}),
        (("D:/v/a.mp4", "en", "", "D:/ra"), {}),
        (("D:/v/b.mp4", "vi", "g1", "E:/x"),
         dict(che_chu=True, che_chu_cach="mo", che_chu_muc=1.0,
              viet_chu=True)),
        (("D:/v/b.mp4", "vi", "g1", "E:/x"),
         dict(che_chu=True, che_chu_cach="khoi", che_chu_muc=0.3,
              viet_chu=True, kieu_chu={"co_chu": 0.06, "dam": True})),
    ]
    lech = [(k, moc_tc.khoa_chong_trung(*x, **k), TC.khoa_chong_trung(*x, **k))
            for x, k in bo
            if moc_tc.khoa_chong_trung(*x, **k) != TC.khoa_chong_trung(*x, **k)]
    ok(not lech,
       f"7f TẮT -> khoá GIỐNG TỪNG KÝ TỰ mốc ({len(bo)} tổ hợp cờ cũ)",
       str(lech[:1]) if lech else f"{len(bo)}/{len(bo)} trùng")

    x = ("D:/v/c.mp4", "vi", "g2", "E:/y")
    k_tat = TC.khoa_chong_trung(*x)
    k_bat = TC.khoa_chong_trung(*x, hinh_theo_giong=True)
    ok(k_bat != k_tat, "7g BẬT -> khoá ĐỔI (không bị smart-skip)")
    ok(k_bat == k_tat + ":htg=1",
       "7h đuôi nối vào CUỐI chuỗi, khoá cũ là TIỀN TỐ (không đổi hash cũ)",
       k_bat[-8:])

    # --- payload: ô để mặc định thì KHÔNG sinh khoá (quét AST) ---
    nut = than_ham("app/core/tg_chay.py", "xep_mot")
    trong_if = False
    for n in ast.walk(nut):
        if isinstance(n, ast.If) and isinstance(n.test, ast.Name) \
                and n.test.id == "hinh_theo_giong":
            for c in ast.walk(n):
                if isinstance(c, ast.Subscript) \
                        and isinstance(c.slice, ast.Constant) \
                        and c.slice.value == "hinh_theo_giong":
                    trong_if = True
    ok(trong_if,
       "7i payload chỉ mọc khoá `hinh_theo_giong` KHI BẬT (nằm trong `if`)")


def muc8() -> None:
    """TRẦN LÀM CHẬM HÌNH CÓ RĂNG + LÙI VỀ CÁCH CŨ THÌ GHI LOG."""
    print("\nMỤC 8 — trần làm chậm hình: có răng, và lùi thì phải NÓI RA")
    from app.core import thay_giong as tg

    d = hop() / "tran"
    d.mkdir(exist_ok=True)
    # Câu GIỮA cần k = 3,2/(2−0,12) = 1,70 — VƯỢT trần của nguồn 24 fps (1,20)
    fs = []
    for i, giay in enumerate((1.0, 3.2, 1.0)):
        p = d / f"c{i}.wav"
        _ff(["-f", "lavfi", "-i", f"sine=f=300:d={giay}", "-ac", "2",
             "-ar", "44100", "-c:a", "pcm_s16le", str(p)])
        fs.append(str(p))
    cau = [{"start": 0.0, "end": 2.0}, {"start": 2.0, "end": 4.0},
           {"start": 4.0, "end": 6.0}]
    c = tg.he_so_hinh_can(cau, fs, [True] * 3, 6.0)
    tran = tg.tran_hinh_theo_fps(24.0)
    hs = max(1.0, min(float(c["k_can"]), tran))
    cham = float(c["k_can"]) > tran + 1e-6
    ok(float(c["k_can"]) > 1.6, "8a dựng được ca VƯỢT TRẦN",
       f"k_can {c['k_can']}")
    ok(cham and abs(hs - tran) < 1e-6,
       "8b quá trần -> KẸP về trần, không chậm hình quá tay",
       f"k_can {c['k_can']} -> k_dung {hs:.4f} (trần {tran:.4f})")

    o = d / "kh"
    o.mkdir(exist_ok=True)
    kh = tg.khop_thoi_gian(cau, fs, [True] * 3, 6.0, o, he_so_hinh=hs)
    ok(kh["tempo_max"] > 1.001,
       "8c chạm trần -> phần dư VẪN ép tiếng (lùi về cách cũ, không giấu)",
       f"tempo_max {kh['tempo_max']}")
    ok(kh["chong_lan_ms_max"] <= 1.0,
       "8d lùi rồi thì BẤT BIẾN 0 ms chồng lấn vẫn giữ",
       f"{kh['chong_lan_ms_max']} ms")

    # --- LÙI PHẢI GHI LOG: `cham_tran` có thật trong nhật ký bước 5 ---
    nut = than_ham("app/core/thay_giong.py", "thay_giong_video")
    ok(any(isinstance(n, ast.Constant) and n.value == "cham_tran"
           for n in ast.walk(nut)),
       "8e nhật ký lượt chạy có khoá `cham_tran` (lùi im lặng là bẫy)")
    ok(any(isinstance(n, ast.Constant)
           and n.value == "nhip_hinh_con_lai_fps" for n in ast.walk(nut)),
       "8f nhật ký nói cả GIÁ: nhịp hình còn lại bao nhiêu fps")

    # --- TRẦN TỒN TẠI VÌ LÝ DO THẬT: gỡ trần -> nhịp hình vỡ ---
    # **ĐO `số khung / độ dài`, KHÔNG đọc `do_fps`.** `do_fps` lấy nhịp hình
    # trong VỎ CHỨA, mà `-itsscale` chỉ giãn MỐC nên trường đó có thể giữ
    # nguyên hoặc bị ffprobe đoán lệch hẳn — đo thử ở k=2,55 nó ra **47,00
    # fps** (cao HƠN nguồn 24!) trong khi nhịp thật là 9,4. Đọc số đó rồi kết
    # luận là đúng bệnh "phép đo hỏng phát chứng nhận".
    k_pha = float(c["k_can"]) * 1.5
    v = d / "v.mp4"
    _ff(["-f", "lavfi", "-i", "testsrc2=size=160x120:rate=24:d=4",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         str(v)])
    # Tiếng phải DÀI HƠN cả hai bản giãn — `-shortest` cắt video theo tiếng,
    # cắt rồi thì `số khung / độ dài` đo ra nhịp của phần bị cắt, không phải
    # nhịp thật (bẫy đã sập khi viết mục này).
    au = d / "a.wav"
    _ff(["-f", "lavfi", "-i", f"sine=f=300:d={4.0 * k_pha + 2:.2f}",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(au)])

    def _nhip(p: Path) -> float:
        n = int(_probe(p, "stream=nb_frames") or 0)
        s = float(_probe(p, "format=duration", vid=False) or 0)
        return (n / s) if s > 0 else -1.0

    r_tran, r_pha = d / "r_tran.mp4", d / "r_pha.mp4"
    tg.thay_audio_video(v, au, r_tran, che_chu=False, he_so_hinh=tran)
    tg.thay_audio_video(v, au, r_pha, che_chu=False, he_so_hinh=k_pha)
    f_tran, f_pha = _nhip(r_tran), _nhip(r_pha)
    ok(f_tran >= tg.SAN_NHIP_HINH_FPS - 0.5,
       "8g theo TRẦN -> nhịp hình còn >= sàn đã chốt",
       f"{f_tran:.2f} fps (sàn {tg.SAN_NHIP_HINH_FPS:g})")
    ok(f_pha < tg.SAN_NHIP_HINH_FPS - 1.0,
       "8h GỠ TRẦN -> nhịp hình VỠ (trần có lý do đo được, không đặt mò)",
       f"k={k_pha:.3f} -> {f_pha:.2f} fps")


def _sin(d: Path, ten: str, giay: float) -> str:
    """Một câu TTS GIẢ — file wav thật, độ dài biết trước."""
    p = d / ten
    _ff(["-f", "lavfi", "-i", f"sine=f=440:d={giay:.3f}", "-ac", "1",
         "-ar", "24000", "-c:a", "pcm_s16le", str(p)])
    return str(p)


#: SỔ THAM SỐ bước 4c nhận được ở lượt `_chay_that` gần nhất — xem `_4c_gia`.
_4C_KW: list[dict] = []


def _chay_that(tmp: Path, **kw) -> tuple[dict, int]:
    """CHẠY THẬT `thay_giong_video` với 5 bước RA MẠNG bị thay bằng bản giả.

    Vì sao phải chạy thật chứ không chỉ quét AST: bài học *"hàm xong ≠ tính
    năng xong"* — repo này đã 4 lần có module lõi nằm chết không ai gọi. Quét
    AST chỉ chứng minh **mã CÓ nhánh đó**; chỉ lượt chạy mới chứng minh **nhánh
    đó ĐƯỢC ĐI VÀO** và bước 4c không chạy một lần nào.

    Năm bản giả (chép lời · dịch · đọc · rút gọn · đọc nhanh) đều là cửa ra
    MẠNG (Groq + edge-tts) — giả để cổng chạy được OFFLINE và TIỀN ĐỊNH, đúng
    luật "test không được đụng máy thật / mạng thật". Bản giả của bước 4c
    **có ĐẾM** và **bắt chước đúng cái 4c làm**: trả file NGẮN HƠN cho câu tràn
    khung. Nhờ vậy cột "hệ số hình cần" của hai arm khác nhau THẬT, đo được cái
    GIÁ chứ không chỉ khai. Còn phần 4c làm việc đó đúng hay không thì đã có
    mốc đo trên video thật (`_do_khop_video.py`) — ở đây chỉ hỏi MỘT câu: đường
    mã có gọi nó không.

    `de_giong=True` để bỏ Demucs (4,3 GB, cần card NVIDIA).
    Trả `(kq, số lần bước 4c bị gọi)`.
    """
    from app.core import thay_giong as tg

    d = tmp
    d.mkdir(parents=True, exist_ok=True)
    v = d / "v.mp4"
    _ff(["-f", "lavfi", "-i", "testsrc2=size=160x120:rate=24:d=9",
         "-f", "lavfi", "-i", "sine=f=200:d=9", "-c:v", "libx264",
         "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-shortest", str(v)])
    # Câu GIỮA đọc 3,2 s trong khung ~2,9 s -> TRÀN khung, đúng ca bước 4c bắn.
    cau = [{"start": 0.0, "end": 2.0, "text": "mot"},
           {"start": 3.0, "end": 5.0, "text": "hai"},
           {"start": 6.0, "end": 8.0, "text": "ba"}]
    fs = [_sin(d, f"t{i}.wav", g) for i, g in enumerate((1.0, 3.2, 1.0))]
    #: bản "đã đọc nhanh lại" của câu giữa — NGẮN HƠN, y việc 4c làm thật
    nhanh = _sin(d, "t1_nhanh.wav", 2.0)
    texts = ["Cau mot ngan", "Cau hai dai hon han cac cau khac trong bai",
             "Cau ba ngan"]

    dem = {"n": 0}
    goc = {k: getattr(tg, k) for k in
           ("chep_loi", "dich_hau_kiem", "doc_ban_dich", "rut_gon_vua_khung",
            "doc_nhanh_vua_khung")}

    def _4c_gia(_cau, _texts, files, _ok, *a, **k):
        dem["n"] += 1
        # GHI SỔ THAM SỐ bước 4c NHẬN ĐƯỢC. MỤC 10 đọc sổ này để chứng minh
        # `keo_dai_giong` **đi tới được máy đọc**, chứ không dừng ở chữ ký hàm
        # — bài học "hàm xong ≠ tính năng xong" (v2.45.0 nối đủ chuỗi nhưng
        # sót cửa NGOÀI CÙNG -> 4/4 video LỖI). Sổ ở MỨC MODULE nên
        # `_chay_that` giữ NGUYÊN giá trị trả về và MỤC 9 không phải sửa dòng
        # nào.
        _4C_KW.append(dict(k))
        f2 = list(files)
        f2[1] = nhanh                      # đúng câu tràn khung, ngắn lại
        return {"files": f2, "ok": [True] * 3, "moc_tu": [[] for _ in f2],
                "so_doc_lai": 1, "rate_max": 43,
                "can_truoc": [0.35, 1.11, 0.35], "can_sau": [0.35, 0.69, 0.35]}

    tg.chep_loi = lambda *a, **k: {
        "language": "en", "words": [],
        "segments": [dict(s) for s in cau], "_nguon": "gia"}
    tg.dich_hau_kiem = lambda *a, **k: {"ban_dich": list(texts)}
    tg.doc_ban_dich = lambda *a, **k: {
        "files": list(fs), "ok": [True] * 3, "voice": "gia", "giay": 0.0,
        "so_hong": 0, "moc_tu": [[] for _ in fs]}
    tg.rut_gon_vua_khung = lambda *a, **k: {
        "texts": list(texts), "files": list(fs), "ok": [True] * 3,
        "so_sua": 0, "moc_tu": [[] for _ in fs]}
    tg.doc_nhanh_vua_khung = _4c_gia
    try:
        kq = tg.thay_giong_video(v, dich_sang="vi", thu_muc_lam=d / "lam",
                                 de_giong=True, viet_chu=False, **kw)
    finally:
        for k, f in goc.items():
            setattr(tg, k, f)
    return kq, dem["n"]


def muc9() -> None:
    """ĐỌC ĐỀU (bỏ bước 4c) — cửa chuẩn hoá · khoá chống trùng · CHẠY THẬT."""
    print("\nMỤC 9 — đọc ĐỀU một tốc độ: bỏ bước 4c `doc_nhanh_vua_khung`")
    from app.core import tg_chay as TC
    from app.core import thay_giong as tg

    # ---- 9a: CỬA DUY NHẤT chuẩn hoá tên cách khớp ----
    bang = {"": (False, False), "hinh": (True, False),
            "hinh_deu": (True, True), " HINH_DEU ": (True, True),
            "rac": (False, False), None: (False, False), "0": (False, False)}
    sai = [(k, tg.chuan_khop_cach(k), v) for k, v in bang.items()
           if tg.chuan_khop_cach(k) != v]
    ok(not sai, f"9a `chuan_khop_cach` đúng cả {len(bang)} ca (kể cả rác)",
       str(sai[:2]) if sai else "rác/None -> lùi về cách CŨ")

    # ---- 9b: `doc_deu` KHÔNG BAO GIỜ ra True một mình ----
    # Bỏ 4c mà không làm chậm hình thì phần dôi rơi hết xuống `atempo`, ép
    # NẶNG HƠN cả cách cũ — tức "chữa" xong còn tệ hơn lúc chưa chữa.
    mot_minh = [x for x in list(bang) + ["deu", "hinh_deu ", "HINH", 1, 0]
                if tg.chuan_khop_cach(x)[1] and not tg.chuan_khop_cach(x)[0]]
    ok(not mot_minh,
       "9b không giá trị nào cho `doc_deu` bật MỘT MÌNH (không có hình chậm)",
       str(mot_minh[:3]) if mot_minh else "0/13 ca")

    # ---- 9c: MẶC ĐỊNH VẪN LÀ CÁCH CŨ ----
    ok(tg.KHOP_CACH[0] == "" and tg.chuan_khop_cach(tg.KHOP_CACH[0])
       == (False, False),
       "9c mục ĐẦU của combo = cách CŨ (đổi mặc định là đổi tiếng 200-300 kênh)")
    ok(len(tg.KHOP_CACH) == 3 and set(tg.NHAN_KHOP_CACH) == set(tg.KHOP_CACH),
       "9d đủ 3 mục và mục nào cũng có nhãn tiếng Việt",
       " · ".join(tg.NHAN_KHOP_CACH[m] for m in tg.KHOP_CACH))
    ok("ép" in tg.NHAN_KHOP_CACH["hinh_deu"].lower()
       and "đều" in tg.NHAN_KHOP_CACH["hinh_deu"].lower(),
       "9e nhãn mục mới nêu CẢ HAI chiều: được 'đều' · giá 'ép phần dư'",
       tg.NHAN_KHOP_CACH["hinh_deu"])

    # ---- 9zd-9ze: NHÃN KHÔNG ĐƯỢC HỨA "ĐỀU" Ở MỤC VẪN CHẠY BƯỚC 4C ----
    # LỖI THẬT, ĐÃ ĐẨY NGƯỜI DÙNG ĐI NHẦM Ô (28/08/2026): nhãn mục `"hinh"`
    # ghi *"(tiếng đều, khuyên dùng)"*. Chữ "đều" ở đó định nói "hệ số ép về
    # 1,000", nhưng anh Hùng đọc ra "đọc đều một nhịp" — thứ mục đó KHÔNG làm,
    # vì nó vẫn chạy 4c `doc_nhanh_vua_khung` (mục 9o dưới đây ĐẾM: mục 2 gọi
    # 4c, mục 3 gọi 0 lần). Anh ấy chọn mục 2 rồi kêu *"nó CHỈNH TỐC ĐỘ GIỌNG
    # ĐỌC"* — đúng, và cái đẩy anh ấy vào đó là dòng nhãn.
    # Chốt: chữ "đều" chỉ được xuất hiện ở mục mà `chuan_khop_cach` trả
    # `doc_deu=True`. Đây là cổng CÓ RĂNG — trả nhãn cũ về là nó đỏ ngay.
    hua_deu = [m for m in tg.KHOP_CACH
               if "đều" in tg.NHAN_KHOP_CACH[m].lower()]
    sai = [m for m in hua_deu if not tg.chuan_khop_cach(m)[1]]
    ok(not sai,
       "9zd nhãn chỉ hứa 'đều' ở mục THẬT SỰ bỏ bước 4c (không dụ nhầm ô)",
       f"mục hứa 'đều' mà vẫn chạy 4c: {sai}" if sai
       else f"hứa 'đều': {hua_deu} — đều có doc_deu=True")
    ok("khuyên dùng" not in tg.NHAN_KHOP_CACH["hinh"].lower(),
       "9ze mục `hinh` KHÔNG còn tự nhận 'khuyên dùng' (đo ra nó KÉM mục 1 về "
       "độ đều: CV 20,77/14,26 so với 20,11/14,08)",
       tg.NHAN_KHOP_CACH["hinh"])

    # ---- 9f-9i: KHOÁ CHỐNG TRÙNG ----
    moc_tc = nap_moc("app/core/tg_chay.py", "tc")
    ok("dd=1" not in moc_tc.__dict__["_NGUON_"],
       "9f mốc `tg_chay` KHÔNG hề có đuôi `dd` (mốc đúng, không tự PASS OAN)")
    x = ("D:/v/d.mp4", "vi", "g3", "E:/z")
    k_tat = TC.khoa_chong_trung(*x)
    k_htg = TC.khoa_chong_trung(*x, hinh_theo_giong=True)
    k_deu = TC.khoa_chong_trung(*x, hinh_theo_giong=True, doc_deu=True)
    ok(k_tat == moc_tc.khoa_chong_trung(*x),
       "9g TẮT -> khoá GIỐNG TỪNG KÝ TỰ bản mốc (không xuất lại 200-300 kênh)")
    ok(TC.khoa_chong_trung(*x, doc_deu=True) == k_tat,
       "9h bật `doc_deu` mà KHÔNG chỉnh hình -> khoá KHÔNG đổi "
       "(cờ vô nghĩa thì không đẻ lượt chạy lại)")
    ok(k_deu == k_htg + ":dd=1" and k_deu.startswith(k_tat),
       "9i BẬT -> đuôi `:dd=1` nối vào CUỐI, khoá cũ vẫn là TIỀN TỐ",
       k_deu[-12:])

    # ---- 9j: payload chỉ mọc khoá khi BẬT, và LỒNG trong nhánh `htg` ----
    nut = than_ham("app/core/tg_chay.py", "xep_mot")

    def _long(goc_ten: str, trong_ten: str, khoa: str) -> bool:
        """`tt[khoa]` phải nằm trong `if trong_ten:` mà `if` đó lại nằm trong
        `if goc_ten:` — quét LỒNG NHAU, không chỉ "nằm trong một if nào đó"."""
        for n in ast.walk(nut):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                    and n.test.id == goc_ten):
                continue
            for c in ast.walk(n):
                if not (isinstance(c, ast.If) and isinstance(c.test, ast.Name)
                        and c.test.id == trong_ten):
                    continue
                for e in ast.walk(c):
                    if isinstance(e, ast.Subscript) \
                            and isinstance(e.slice, ast.Constant) \
                            and e.slice.value == khoa:
                        return True
        return False

    ok(_long("hinh_theo_giong", "doc_deu", "doc_deu"),
       "9j payload mọc khoá `doc_deu` LỒNG trong nhánh `hinh_theo_giong`")
    # TỰ KIỂM BỘ DÒ: cùng bộ dò, tên KHÔNG có trong mã -> phải trả False.
    # Thiếu ca này thì `_long` chỉ cần `return True` là mục trên xanh vĩnh viễn.
    ok(not _long("hinh_theo_giong", "doc_deu", "khong_he_co_khoa_nay")
       and not _long("khong_he_co_co_nay", "doc_deu", "doc_deu"),
       "9k TỰ KIỂM BỘ DÒ: khoá/cờ bịa ra thì bộ dò trả HỎNG (dò có răng)")

    # ---- 9l: chốt `and hinh_theo_giong` nằm TRONG lõi, không ở lời gọi ----
    than = than_ham("app/core/thay_giong.py", "thay_giong_video")

    def _co_chot(a: str, b: str) -> bool:
        for n in ast.walk(than):
            if not (isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And)):
                continue
            ten = {m.id for v in n.values for m in ast.walk(v)
                   if isinstance(m, ast.Name)}
            if a in ten and b in ten:
                return True
        return False

    ok(_co_chot("doc_deu", "hinh_theo_giong"),
       "9l lõi chốt `doc_deu AND hinh_theo_giong` (không bắt người gọi tự nhớ)")
    ok(not _co_chot("doc_deu", "khong_he_co_bien_nay"),
       "9m TỰ KIỂM BỘ DÒ: biến bịa ra thì bộ dò `_co_chot` trả HỎNG")

    # ---- 9n-9r: CHẠY THẬT — bước 4c có bị bỏ thật không ----
    d = hop() / "deu"
    kq_cu, n_cu = _chay_that(d / "cu", hinh_theo_giong=True, doc_deu=False)
    kq_deu, n_deu = _chay_that(d / "deu", hinh_theo_giong=True, doc_deu=True)
    kq_le, n_le = _chay_that(d / "le", hinh_theo_giong=False, doc_deu=True)

    ok(n_cu == 1, "9n arm CŨ vẫn chạy bước 4c ĐÚNG 1 lần (đối chứng có răng)",
       f"{n_cu} lần")
    ok(n_deu == 0, "9o BẬT đọc đều -> bước 4c chạy 0 lần (bỏ THẬT, "
                   "không phải chỉ có nhánh trong mã)", f"{n_deu} lần")
    ok(n_le == 1,
       "9p `doc_deu` không kèm chỉnh hình -> 4c VẪN chạy (chốt lõi có tác dụng)",
       f"{n_le} lần")
    # `kiem_video_ra` NÉM khi file hỏng (không trả cờ), nên nó chạy tới đây tức
    # đã ĐẠT: có khung hình · có tiếng · đúng độ dài ĐÍCH (đã nhân hệ số hình).
    _kv = kq_deu.get("kiem") or {}
    ok(bool(kq_deu.get("ok")) and Path(kq_deu.get("ra") or "x").exists()
       and int(_kv.get("khung") or 0) > 0 and float(_kv.get("rms") or 0) > 0,
       "9q bỏ 4c vẫn RA VIDEO hợp lệ (không phải xanh vì chết sớm)",
       f"{_kv.get('khung')} khung · {_kv.get('do_dai')}s · "
       f"lệch {_kv.get('lech_do_dai')}s")
    ok(kq_deu["hinh"].get("doc_deu") is True
       and kq_cu["hinh"].get("doc_deu") is False
       and kq_le["hinh"].get("doc_deu") is False,
       "9r nhật ký lượt chạy NÓI RA đang đi đường nào (không lặng lẽ đổi)")
    ok(kq_deu["doc_nhanh"].get("bo_qua") is True
       and "so_doc_lai" in kq_deu["doc_nhanh"],
       "9s nhật ký bước 4c ghi rõ 'bỏ qua' + số câu đọc lại = 0",
       str(kq_deu["doc_nhanh"].get("so_doc_lai")))
    # GIÁ PHẢI TRẢ, đo ngay trong cổng: bỏ 4c thì hệ số hình CẦN cao hơn hẳn,
    # nên chạm trần và phần dư quay lại ép tiếng. Nói ra bằng SỐ, không bằng lời.
    ok(float(kq_deu["hinh"]["k_can"]) > float(kq_cu["hinh"]["k_can"]) + 1e-6,
       "9t bỏ 4c -> hệ số làm chậm hình CẦN cao hơn (đánh đổi, đo được)",
       f"CŨ {kq_cu['hinh']['k_can']} -> ĐỀU {kq_deu['hinh']['k_can']}")

    # ---- 9u: LỜI NHẮN tiến trình không làm thanh CHẠY NGƯỢC ----
    # `tg_so.buoc_tu_tien_trinh` tra bước bằng CHUỖI CON. Nhánh mới thêm một
    # lời nhắn mới ở mốc 0,79 — nếu nó không chứa cụm "đọc nhanh" thì cụm
    # "đọc" khớp trước và bảng tiến độ tụt 7 -> 5 = CHẠY NGƯỢC. Lời nhắn lấy
    # bằng AST từ CHÍNH thân hàm (không chép tay, không grep chuỗi).
    from app.core import tg_so
    nhan = []
    for n in ast.walk(than):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "prog" and len(n.args) == 2 \
                and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[1], ast.Constant) \
                and "TỰ NHIÊN" in str(n.args[1].value):
            nhan.append((float(n.args[0].value), str(n.args[1].value)))
    ban = [(m, tg_so.buoc_tu_tien_trinh(p, m)[1]) for p, m in nhan
           if tg_so.buoc_tu_tien_trinh(p, m)[1] != 7]
    ok(bool(nhan) and not ban,
       "9u lời nhắn nhánh đọc đều tra ra ĐÚNG bước 7 (thanh không chạy ngược)",
       str(ban) if ban else f"{len(nhan)} lời nhắn -> bước 7/9")

    # ---- 9v-9x: CHUỖI CHUYỀN CỜ — "hàm xong ≠ tính năng xong" ----
    # Repo này đã 4 lần có module lõi nằm chết không ai gọi. Cờ phải đi hết
    # chặng: combo -> `xep_mot` -> payload -> `jobs._thay_giong` ->
    # `thay_giong_mot_video` (cửa DUY NHẤT job đi qua) -> `thay_giong_video`.
    # Đứt một mắt là ô bấm xong KHÔNG LÀM GÌ mà không một dòng báo.
    bat: list = []
    _that = tg.thay_giong_video
    tg.thay_giong_video = lambda *a, **k: (bat.append(dict(k)),
                                           {"ok": False, "loi": "chỉ để bắt"})[1]
    try:
        for c in (True, False):
            tg.thay_giong_mot_video("x.mp4", doc_deu=c, thay_goc=False)
    finally:
        tg.thay_giong_video = _that
    ok(len(bat) == 2 and bat[0].get("doc_deu") is True
       and bat[1].get("doc_deu") is False,
       "9v `thay_giong_mot_video` CHUYỀN `doc_deu` xuống lõi (cửa job đi qua)",
       str([b.get("doc_deu") for b in bat]))

    def _co_kw(duong: str, ham: str, goi: str, kw: str) -> bool:
        for n in ast.walk(than_ham(duong, ham)):
            if isinstance(n, ast.Call) and (
                    getattr(n.func, "id", "") == goi
                    or getattr(n.func, "attr", "") == goi):
                if any(k.arg == kw for k in n.keywords):
                    return True
        return False

    ok(_co_kw("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
              "doc_deu"),
       "9w `jobs._thay_giong` đọc `doc_deu` từ payload rồi chuyền tiếp")
    ok(_co_kw("app/ui/thay_giong_dialog.py", "_chay", "xep_mot", "doc_deu"),
       "9x hộp Thay giọng chuyền `doc_deu` cho `xep_mot` (ô bấm CÓ tác dụng)")
    ok(not _co_kw("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
                  "khong_he_co_kw_nay")
       and not _co_kw("app/ui/thay_giong_dialog.py", "_chay", "xep_mot",
                      "khong_he_co_kw_nay"),
       "9y TỰ KIỂM BỘ DÒ: tham số bịa ra thì bộ dò `_co_kw` trả HỎNG")

    # ---- 9z: Ô TRONG HỘP THAY GIỌNG — anh Hùng phải CHỌN được ----
    app_qt()                                  # giữ tham chiếu — xem `_APP`
    from app.ui.thay_giong_dialog import ThayGiongDialog
    dl = ThayGiongDialog(None)
    try:
        dat = [dl.cb_khop.itemData(i) for i in range(dl.cb_khop.count())]
        ok(dat == list(tg.KHOP_CACH),
           "9z combo 'Khớp tiếng với hình' có ĐỦ 3 mục, đúng thứ tự", str(dat))
        ok(dl.cb_khop.currentIndex() == 0
           and tg.chuan_khop_cach(dl.cb_khop.currentData()) == (False, False),
           "9za MỞ HỘP LÊN mặc định vẫn là CÁCH CŨ (không đổi sau lưng ai)",
           dl.cb_khop.currentText())
        dl.cb_khop.setCurrentIndex(2)
        ok(tg.chuan_khop_cach(dl.cb_khop.currentData()) == (True, True),
           "9zb chọn mục 3 -> (chỉnh hình BẬT · đọc đều BẬT)")
        tip = dl.cb_khop.toolTip()
        ok(all(x in tip for x in ("ĐÁNH ĐỔI", "ép", "NHANH HƠN", "nghe")),
           "9zc chú thích nói CẢ cái được, CẢ cái mất, CẢ 'chưa ai nghe thử'",
           f"{len(tip)} ký tự")
    finally:
        dl.deleteLater()


def muc10() -> None:
    """KÉO DÀI GIỌNG CHO ĐẦY KHUNG (v2.49.0) + lỗ VieNeu trả file 0 giây.

    Anh Hùng kêu BA LẦN qua nhiều bản: *"giọng đọc không liền mạch, cứ được
    đoạn rồi nghỉ"*. Gốc rễ là một PHÉP TRỪ (`im = độ_dài_video − tổng_tiếng`)
    nên bốn hướng "đổi chỗ khoảng im" đều bị bác bằng số; đường thứ năm là
    **kéo dài chính TIẾNG cho đầy khung**, và vì câu vẫn nằm ĐÚNG mốc gốc nên
    lệch tiếng-hình = 0 THEO CẤU TẠO.

    Mục này canh 6 điều, và điều 5 là món nợ CHẶN SẢN XUẤT:
      1. `chuan_keo_dai` là CỬA DUY NHẤT (rác/None/NaN -> 1,0 = TẮT).
      2. `rate_am_cho` **không bao giờ VƯỢT** hệ số xin (đọc chậm quá khung là
         phải cắt đuôi = MẤT CHỮ, hoặc ép nhanh lại = méo HAI LẦN).
      3. NHÃN dựng TỪ BẢNG SỐ ĐO, không gõ tay một con số nào.
      4. **CHẠY THẬT** (ffmpeg thật): kéo có ăn, và bất biến **0 ms chồng lấn**
         + **mốc BẮT ĐẦU NÓI không đổi** vẫn giữ.
      5. **LỖ VieNeu TRẢ FILE 0 GIÂY** — họ hàng của lỗ đã vá ở v2.47.0 nhưng
         lọt qua cửa KHÁC: `khop_thoi_gian` bỏ câu khi `d <= 0` rồi lại đòi
         `>= 0,05 s` ở `_kiem_wav` -> câu dài 0,021..0,049 s lọt cả hai chốt,
         `_kiem_wav` NÉM giữa vòng lặp và **GIẾT CẢ VIDEO** thay vì mất 1 câu.
      6. Chuỗi 6 chặng + khoá chống trùng: TẮT -> giống mốc TỪNG KÝ TỰ.
    """
    print("\nMỤC 10 — kéo dài giọng cho đầy khung + lỗ file 0 giây")
    from app.core import tg_chay as TC
    from app.core import thay_giong as tg

    # ---- 10a: CỬA DUY NHẤT chuẩn hoá mức kéo ----
    tran = float(tg.MUC_KEO_DAI[-1])
    bang = {None: 1.0, "rac": 1.0, "": 1.0, 0: 1.0, -5: 1.0, 0.999: 1.0,
            1.0: 1.0, 1.15: 1.15, 1.153: 1.15, 1.2549: 1.25, 9.9: tran,
            float("nan"): 1.0, float("inf"): tran, "1.15": 1.15}
    sai = [(k, tg.chuan_keo_dai(k), v) for k, v in bang.items()
           if abs(tg.chuan_keo_dai(k) - v) > 1e-9]
    ok(not sai, f"10a `chuan_keo_dai` đúng cả {len(bang)} ca (kể cả NaN/inf/rác)",
       str(sai[:2]) if sai else "rác/None/NaN -> 1,0 = TẮT · trên trần -> kẹp")

    # ---- 10b: MẶC ĐỊNH LÀ TẮT ----
    ok(abs(float(tg.MUC_KEO_DAI[0]) - 1.0) < 1e-9
       and list(tg.MUC_KEO_DAI) == sorted(tg.MUC_KEO_DAI),
       "10b mục ĐẦU của combo = 1,00 = TẮT (đổi mặc định là đổi tiếng "
       "200-300 kênh, và CHƯA AI NGHE)", str(tg.MUC_KEO_DAI))

    # ---- 10c: `rate_am_cho` KHÔNG BAO GIỜ VƯỢT ----
    vuot = [(x, tg.rate_am_cho(x)) for x in
            (1.0, 1.05, 1.11, 1.15, 1.18, 1.25, 1.30, 1.40, 1.67, 9.9)
            if tg.rate_am_cho(x)[0] > x + 1e-9]
    ok(not vuot, "10c `rate_am_cho` lấy mức ĐO ĐƯỢC lớn nhất mà KHÔNG vượt "
       "(kéo hụt rồi để bước 5 bù, còn hơn đọc chậm quá khung rồi cắt đuôi)",
       str(vuot[:2]) if vuot else "10/10 ca không vượt")
    hs = [m[0] for m in tg.BANG_RATE_AM]
    ok(hs == sorted(hs) and len(set(hs)) == len(hs)
       and all(m[1].startswith(("-", "+")) for m in tg.BANG_RATE_AM),
       "10ca BẢNG ĐO `rate` âm tăng dần, không trùng, mọi mức có chuỗi rate",
       f"{len(tg.BANG_RATE_AM)} mức · trần {hs[-1]}")

    # ---- 10d: NHÃN DỰNG TỪ BẢNG SỐ ĐO, KHÔNG GÕ TAY ----
    # Bẫy đã sập ở `giong_bang._DUOI[KOKORO]` (nhãn ghi 250 MB trong khi thứ
    # phải tải là 126,3 MB). Quét AST thân `nhan_keo_dai`: hằng số thực duy
    # nhất được phép là 1.0 (dùng để so "có kéo hay không").
    # `1.0` được phép (so "có kéo hay không"), và mọi số **nhỏ hơn 0,01** cũng
    # được phép: đó là BIÊN so sánh dấu phẩy động (`< 1e-9`), không phải số đo.
    # Mọi con số của `SO_DO_KEO_DAI` đều >= 1,0 nên chừa khoảng đó KHÔNG làm
    # bộ dò mất răng — mục 10dc tự kiểm lại đúng điều đó.
    so_go_tay = [n.value for n in ast.walk(than_ham(
        "app/core/thay_giong.py", "nhan_keo_dai"))
        if isinstance(n, ast.Constant) and isinstance(n.value, float)
        and abs(n.value - 1.0) > 1e-9 and abs(n.value) >= 0.01]
    ok(not so_go_tay,
       "10d `nhan_keo_dai` KHÔNG gõ tay một con số đo nào (đọc `SO_DO_KEO_DAI`)",
       str(so_go_tay[:3]) if so_go_tay else "0 hằng số lạ trong thân hàm")
    nh = tg.nhan_keo_dai(1.25)
    d25 = tg.SO_DO_KEO_DAI[1.25]
    ok(f"{d25['im_pt']:.2f}".replace(".", ",") in nh
       and str(d25["quang_05"]) in nh,
       "10da nhãn mức 1,25 NÓI ĐÚNG số của bảng (im % + số quãng nghỉ)", nh)
    ok(all(x not in tg.nhan_keo_dai(1.0).lower() for x in ("ms", "lệch")),
       "10db nhãn mức TẮT không khoe con số lệch nào (nó không đổi gì cả)",
       tg.nhan_keo_dai(1.0))
    # TỰ KIỂM BỘ DÒ: hàm CÓ gõ tay số thì bộ dò phải bắt.
    _gia = ast.parse("def f(m):\n    return 'im %s' % (23.52,) if m < 1e-9"
                     " else '%s' % (18.81,)\n")
    _bat = [n.value for n in ast.walk(_gia)
            if isinstance(n, ast.Constant) and isinstance(n.value, float)
            and abs(n.value - 1.0) > 1e-9 and abs(n.value) >= 0.01]
    ok(sorted(_bat) == [18.81, 23.52],
       "10dc TỰ KIỂM BỘ DÒ: hàm gõ tay số thì bộ dò 10d PHẢI kêu ĐÚNG hai số "
       "đó, và KHÔNG kêu oan biên so sánh `1e-9`", str(sorted(_bat)))

    # ---- 10dd-10df: NHÃN PHẢI NÓI CẢ HAI CHIỀU + KHÔNG KHOE SỐ CHƯA ĐO ----
    # LÝ DO CÓ BA MỤC NÀY (28/08/2026): phép đo trên ĐƯỜNG THẬT lôi ra một
    # MẶT XẤU mà bảng mô phỏng không thấy — **kéo chậm làm TRẢI tốc độ đọc XẤU
    # ĐI** (CV 15,87 -> 18,44 -> 19,93%). "Lúc nhanh lúc chậm" cũng là lời anh
    # Hùng kêu, nên nhãn khoe mỗi "im giảm" là đúng cái đã đẩy anh ấy vào ô
    # sai một lần (nhãn `hinh` hứa "tiếng đều" — mục 9zd).
    for _m in tg.MUC_KEO_DAI:
        if _m <= 1.0 or not tg.SO_DO_KEO_DAI[_m].get("that"):
            continue
        _n = tg.nhan_keo_dai(_m)
        ok("XẤU ĐI" in _n and "im giữa câu" in _n,
           f"10dd nhãn mức {_m:.2f} nói CẢ cái được (im giảm) CẢ cái mất "
           f"(trải tốc độ đọc xấu đi)", _n[:60])
    _chua = [m for m in tg.MUC_KEO_DAI if not tg.SO_DO_KEO_DAI[m].get("that")]
    ok(all("CHƯA ĐO" in tg.nhan_keo_dai(m) for m in _chua),
       "10de mức CHƯA đo trên đường thật thì nhãn NÓI RA (cấm khoe số mô phỏng "
       "như số thật — mô phỏng lệch 7,8 điểm % ở mức 1,25)", str(_chua))
    ok(tg.MUC_KHUYEN_KEO_DAI in tg.MUC_KEO_DAI
       and tg.SO_DO_KEO_DAI[tg.MUC_KHUYEN_KEO_DAI].get("that")
       and "khuyên" in tg.nhan_keo_dai(tg.MUC_KHUYEN_KEO_DAI).lower(),
       "10df mức KHUYÊN có thật trong combo, ĐÃ đo đường thật, và nhãn nói ra",
       f"{tg.MUC_KHUYEN_KEO_DAI}")
    # Mức khuyên phải là mức SÂU NHẤT mà tốc độ đọc còn >= nhịp edge-tts
    # (20,63-20,70 ký tự/giây đo cùng lượt) — dưới mức đó là bắt đầu "lê thê".
    _sau_hon = [m for m in tg.MUC_KEO_DAI
                if m > tg.MUC_KHUYEN_KEO_DAI
                and tg.SO_DO_KEO_DAI[m].get("that")
                and tg.SO_DO_KEO_DAI[m]["kytu_giay"]
                >= tg.SO_DO_KEO_DAI[tg.MUC_KHUYEN_KEO_DAI]["kytu_giay"]]
    ok(not _sau_hon,
       "10dg mức KHUYÊN là mức sâu nhất còn giữ được tốc độ đọc (mức sâu hơn "
       "đều đọc CHẬM HƠN nó -> nguy cơ lê thê)",
       f"kt/s {tg.SO_DO_KEO_DAI[tg.MUC_KHUYEN_KEO_DAI]['kytu_giay']}")

    # ---- 10e: NHẬT KÝ NÓI ĐÚNG ĐƯỜNG NÀO ĐÃ ĐI ----
    ok(tg.rate_la_doc_that("vi-VN-HoaiMyNeural") is True
       and tg.rate_la_doc_that("vnb:D:/a.wav") is False
       and tg.rate_la_doc_that("kk:af_bella") is False
       and tg.rate_la_doc_that("el:Adam") is False,
       "10e `rate_la_doc_that`: chỉ edge-tts thực thi `rate` THẬT (méo = 0); "
       "VieNeu/Kokoro/ElevenLabs đi đường LÙI `rubberband` (CÓ MÉO)")

    # ---- 10f: CHẠY THẬT (ffmpeg thật) — kéo có ăn, bất biến không vỡ ----
    d = hop() / "keo"
    d.mkdir(parents=True, exist_ok=True)
    cau = [{"start": 0.0, "end": 3.0, "text": "a"},
           {"start": 4.0, "end": 7.0, "text": "b"},
           {"start": 8.0, "end": 11.0, "text": "c"}]
    fs = [_sin(d, f"k{i}.wav", 1.2) for i in range(3)]   # 1,2 s / khung 3,0 s
    kh0 = tg.khop_thoi_gian(cau, list(fs), [True] * 3, 12.0, d / "a0",
                            keo_dai_toi_da=1.0)
    kh1 = tg.khop_thoi_gian(cau, list(fs), [True] * 3, 12.0, d / "a1",
                            keo_dai_toi_da=1.25)
    ok(kh0["so_cau_keo_dai"] == 0 and kh0["keo_dai_max"] == 1.0
       and all(abs(t - 1.0) < 1e-3 for t in kh0["tempo_cau"]),
       "10f TẮT -> KHÔNG câu nào bị kéo, `tempo` giữ nguyên 1,000 "
       "(bất biến 'tắt = giống bản cũ')",
       f"tempo {kh0['tempo_cau']}")
    ok(kh1["so_cau_keo_dai"] == 3 and kh1["keo_dai_max"] > 1.2,
       "10fa BẬT 1,25 -> cả 3 câu ngắn được kéo",
       f"{kh1['so_cau_keo_dai']} câu · max {kh1['keo_dai_max']}")
    d0 = [tg.probe_duration(p) for _a, p in kh0["manh"]]
    d1 = [tg.probe_duration(p) for _a, p in kh1["manh"]]
    ok(len(d1) == len(d0) and all(b > a * 1.15 for a, b in zip(d0, d1)),
       "10fb FILE RA THẬT SỰ DÀI HƠN (đo trên file đã ghi, không tin lời hứa)",
       f"{[round(x, 3) for x in d0]} -> {[round(x, 3) for x in d1]}")
    ok(kh1["chong_lan_ms_max"] <= 1.0 and kh1["so_cau_chong_lan"] == 0,
       "10fc BẤT BIẾN 0 ms CHỒNG LẤN vẫn giữ khi kéo dài",
       f"{kh1['chong_lan_ms_max']} ms")
    m0 = {i: a for i, a, _b in kh0["moc_tieng"]}
    m1 = {i: a for i, a, _b in kh1["moc_tieng"]}
    troi = [abs(m1[i] - m0[i]) * 1000.0 for i in m0 if i in m1]
    ok(troi and max(troi) <= 50.0,
       "10fd MỐC BẮT ĐẦU NÓI KHÔNG ĐỔI -> lệch tiếng-hình = 0 theo cấu tạo "
       "(đúng cột đã giết 3 hướng trước)",
       f"trôi max {max(troi):.1f} ms (ngưỡng 50)")

    # ---- 10g: LỖ "FILE 0 GIÂY" — MỘT CÂU HỎNG KHÔNG ĐƯỢC GIẾT CẢ VIDEO ----
    ok(abs(tg.DAI_CAU_TOI_THIEU - 0.05) < 1e-9,
       "10g SÀN độ dài câu là MỘT NGUỒN DUY NHẤT `DAI_CAU_TOI_THIEU`",
       f"{tg.DAI_CAU_TOI_THIEU} s")
    mac_dinh = inspect.signature(tg._kiem_wav).parameters["toi_thieu_giay"]
    ok(mac_dinh.default == tg.DAI_CAU_TOI_THIEU,
       "10ga `_kiem_wav` LẤY sàn từ hằng số đó, không gõ lại số "
       "(hai bản sao là hai chỗ để lệch nhau -> DẢI CHẾT)")
    hong = d / "hong.wav"
    hong.write_bytes(b"")                       # đúng ca VieNeu trả 0,000 s
    ngan = _sin(d, "ngan.wav", 0.03)            # nằm GIỮA dải chết cũ
    fs2 = [fs[0], ngan, fs[2]]
    kh2 = tg.khop_thoi_gian(cau, list(fs2), [True] * 3, 12.0, d / "a2",
                            keo_dai_toi_da=1.25)
    ok(kh2["so_cau"] == 2 and kh2["so_cau_qua_ngan"] == 1 and kh2["loi_cau"],
       "10gb câu 0,03 s (DẢI CHẾT cũ) -> BỎ ĐÚNG CÂU ĐÓ, 2 câu kia vẫn ra, "
       "KHÔNG ném giết cả video",
       f"{kh2['so_cau']} câu ra · quá ngắn {kh2['so_cau_qua_ngan']} · "
       f"{kh2['loi_cau'][:1]}")
    ok(tg.cat_le_im_moc(hong, d / "hong_out.wav") == (0.0, 0.0)
       and not (d / "hong_out.wav").exists(),
       "10gc `cat_le_im_moc` gặp nguồn HỎNG -> trả (0,0), KHÔNG đưa cho ffmpeg "
       "(ffmpeg mã thoát != 0 làm `_ffmpeg` NÉM = giết cả video ở bước 4a)")
    ra, le = tg.cat_le_loat([str(hong), fs[0]], [True, True], d / "sach")
    ok(le.get("so_cau_hong") == 1 and ra[0] == str(hong)
       and Path(ra[1]).exists(),
       "10gd `cat_le_loat` ĐẾM câu hỏng (cấm giấu) và GIỮ đường dẫn cũ "
       "— cấm trỏ vào file chưa từng ghi ra",
       f"so_cau_hong={le.get('so_cau_hong')}")

    # ---- 10h: CHẠY THẬT `thay_giong_video` — cờ ĐI TỚI ĐƯỢC máy đọc ----
    _4C_KW.clear()
    kq_t, _n0 = _chay_that(hop() / "ct_tat", hinh_theo_giong=True)
    kw_tat = list(_4C_KW)
    _4C_KW.clear()
    kq_b, _n1 = _chay_that(hop() / "ct_bat", hinh_theo_giong=True,
                           keo_dai_giong=1.25)
    kw_bat = list(_4C_KW)
    ok(kq_t.get("ok") and kq_b.get("ok"),
       "10h CHẠY THẬT `thay_giong_video` xong cả hai arm",
       f"tắt={kq_t.get('ok')} · bật={kq_b.get('ok')}")
    ok(kw_tat and abs(float(kw_tat[0].get("keo_dai_toi_da", 0)) - 1.0) < 1e-9,
       "10ha TẮT -> bước 4c nhận `keo_dai_toi_da = 1,0` (không đọc chậm câu nào)",
       str(kw_tat[0].get("keo_dai_toi_da")) if kw_tat else "KHÔNG GỌI 4c")
    ok(kw_bat and float(kw_bat[0].get("keo_dai_toi_da", 0)) > 1.2,
       "10hb BẬT -> cờ ĐI TỚI bước 4c (không dừng ở chữ ký hàm — bài học "
       "v2.45.0 sót cửa NGOÀI CÙNG, 4/4 video LỖI)",
       str(kw_bat[0].get("keo_dai_toi_da")) if kw_bat else "KHÔNG GỌI 4c")
    # **CHỐT NÀY TỪNG LÀ MỘT PHÉP ĐẠT OAN.** Bản đầu chỉ hỏi *"lời `duong` có
    # chứa chữ 'méo' không"* — mà CẢ HAI nhánh đều chứa (`"méo = 0"` và
    # `"CÓ MÉO"`), nên nó ĐẠT bất kể app đi đường nào. Đúng bẫy cổng 56d:
    # quét chuỗi mà chỉ hỏi "có mặt không" thì luôn có phép phá giữ nguyên mặt
    # chữ mà đổi ý nghĩa. Nay hỏi HAI vế: cờ `rate_that` phải KHỚP
    # `rate_la_doc_that` của CHÍNH giọng lượt đó, và lời văn phải khớp cờ đó.
    kd = kq_b.get("keo_dai") or {}
    v_that = str((kq_b.get("tts") or {}).get("voice") or "gia")
    mong = tg.rate_la_doc_that(v_that)
    duong = str(kd.get("duong", ""))
    ok(kd.get("bat") is True and kd.get("rate_that") is mong
       and (("méo = 0" in duong) if mong else ("CÓ MÉO" in duong)),
       "10hc NHẬT KÝ nói ĐÚNG đường đã đi — cờ `rate_that` khớp máy đọc THẬT "
       "và lời văn khớp cờ đó",
       f"{v_that} · rate_that={mong} · {duong[:40]}")
    # NỬA CÒN LẠI: lượt chạy trên chỉ đi được MỘT nhánh, nên nhánh kia phải
    # đọc bằng HẰNG SỐ trong thân hàm. Khoe "méo = 0" trong khi đi
    # `rubberband` chính là bẫy "phép đo phát chứng nhận".
    hs_kd = [n.value for n in ast.walk(than_ham(
        "app/core/thay_giong.py", "thay_giong_video"))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    ok(any("CÓ MÉO" in s for s in hs_kd),
       "10hc2 nhánh LÙI có sẵn lời nói THẲNG là CÓ MÉO (cấm lùi im lặng)")
    ok((kq_t.get("keo_dai") or {}).get("bat") is False,
       "10hd TẮT -> nhật ký ghi `bat=False` (không khoe cái không làm)")

    # ---- 10i: KHOÁ CHỐNG TRÙNG ----
    moc_tc = nap_moc("app/core/tg_chay.py", "tc")
    ok("keo_dai_giong" not in moc_tc.__dict__["_NGUON_"],
       f"10i mốc `tg_chay` ({MOC}) KHÔNG hề có `keo_dai_giong` "
       "(mốc đúng, phép so có nghĩa)")
    x = ("D:/v/d.mp4", "vi", "g3", "E:/z")
    k_tat = TC.khoa_chong_trung(*x)
    ok(k_tat == moc_tc.khoa_chong_trung(*x)
       and TC.khoa_chong_trung(*x, keo_dai_giong=1.0) == k_tat
       and TC.khoa_chong_trung(*x, keo_dai_giong=0.0) == k_tat
       and TC.khoa_chong_trung(*x, keo_dai_giong=None) == k_tat,
       "10ia TẮT (kể cả 0,0/None) -> khoá GIỐNG TỪNG KÝ TỰ bản mốc "
       "(không đẻ lượt xuất lại cho 200-300 kênh)")
    k_b = TC.khoa_chong_trung(*x, keo_dai_giong=1.25)
    ok(k_b == k_tat + ":kd=1.25" and k_b.startswith(k_tat),
       "10ib BẬT -> đuôi `:kd=` nối vào CUỐI, khoá cũ vẫn là TIỀN TỐ "
       "(KHÔNG thêm phần tử tuple = KHÔNG đổi hash job cũ)", k_b[-9:])
    ok(TC.khoa_chong_trung(*x, keo_dai_giong=1.15) != k_b
       and TC.khoa_chong_trung(*x, keo_dai_giong=1.2549) == k_b,
       "10ic hai mức KHÁC -> khoá khác; cùng mức viết khác kiểu -> khoá GIỐNG")

    # ---- 10j: CHUỖI 6 CHẶNG — 3 phép bắt buộc của mọi tham số mới ----
    for ham in (tg.thay_giong_mot_video, tg.thay_giong_video):
        ok("keo_dai_giong" in inspect.signature(ham).parameters,
           f"10j (a) `inspect.signature` cửa {ham.__name__} CÓ `keo_dai_giong`")
    try:
        tg.thay_giong_mot_video(r"D:/_khong_ton_tai_89.mp4", dich_sang="vi",
                                keo_dai_giong=1.15, thay_goc=False)
        _te = ""
    except TypeError as e:
        _te = str(e)
    except Exception:                                     # noqa: BLE001
        _te = ""
    ok(not _te, "10ja (b) GỌI THẬT cửa NGOÀI CÙNG -> KHÔNG `TypeError` "
       "(đúng chỗ v2.45.0 đã nổ, 4/4 video LỖI)", _te[:80])

    def _co_kw(duong: str, ham: str, goi: str, kw: str) -> bool:
        for n in ast.walk(than_ham(duong, ham)):
            if isinstance(n, ast.Call) and (
                    getattr(n.func, "id", "") == goi
                    or getattr(n.func, "attr", "") == goi):
                if any(k.arg == kw for k in n.keywords):
                    return True
        return False

    ok(_co_kw("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
              "keo_dai_giong"),
       "10jb `jobs._thay_giong` đọc `keo_dai_giong` từ payload rồi chuyền tiếp")
    ok(_co_kw("app/ui/thay_giong_dialog.py", "_chay", "xep_mot",
              "keo_dai_giong"),
       "10jc hộp Thay giọng chuyền `keo_dai_giong` cho `xep_mot` "
       "(ô bấm CÓ tác dụng)")
    ok(_co_kw("app/core/thay_giong.py", "thay_giong_mot_video",
              "thay_giong_video", "keo_dai_giong"),
       "10jd `thay_giong_mot_video` chuyền tiếp xuống lõi")
    ok(not _co_kw("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
                  "khong_he_co_kw_nay"),
       "10je TỰ KIỂM BỘ DÒ: tham số bịa ra thì `_co_kw` trả HỎNG")
    # payload chỉ mọc khoá khi BẬT — job cũ trong DB không mọc thêm khoá nào.
    #
    # **BẢN ĐẦU CỦA MỤC NÀY ĐỂ LỌT MỘT PHÉP PHÁ, ĐỌC KẺO LẶP.** Nó chỉ hỏi
    # *"phép gán có nằm trong MỘT `ast.If` nào đó không"* — mà `if True:` CŨNG
    # là một `ast.If`, nên phép phá số 24 (`if kd > 1.0:` -> `if True:`) đi
    # lọt và cổng vẫn XANH 50/0, tức khoá chống trùng của 200-300 kênh mất
    # người canh. Đúng bài học cổng 80 LỌT 6: *mục nào canh MỘT chốt cụ thể
    # thì phải đọc LÝ DO cụ thể*, hỏi mỗi "có chặn không" là tự vô hiệu.
    # Nay đòi mệnh đề `if` phải THẬT SỰ SO SÁNH một biến (`ast.Compare` với vế
    # trái là `ast.Name`), không nhận hằng số.
    nut = than_ham("app/core/tg_chay.py", "xep_mot")

    def _if_that(n: ast.If) -> bool:
        return (isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name))

    trong_if = any(
        isinstance(e, ast.Subscript) and isinstance(e.slice, ast.Constant)
        and e.slice.value == "keo_dai_giong"
        for n in ast.walk(nut) if isinstance(n, ast.If) and _if_that(n)
        for e in ast.walk(n))
    ok(not any(_if_that(n) for n in ast.walk(ast.parse("if True:\n    x=1\n"))
               if isinstance(n, ast.If)),
       "10jf0 TỰ KIỂM BỘ DÒ: `if True:` KHÔNG được tính là một chốt thật "
       "(phép phá 24 từng đi lọt đúng chỗ này)")
    ngoai = [e for e in ast.walk(nut)
             if isinstance(e, ast.Subscript)
             and isinstance(e.slice, ast.Constant)
             and e.slice.value == "keo_dai_giong"]
    ok(trong_if and len(ngoai) == 1,
       "10jf payload CHỈ ghi khoá `keo_dai_giong` khi BẬT (nằm trong `if`), "
       "và chỉ ĐÚNG MỘT chỗ ghi", f"{len(ngoai)} chỗ ghi")

    def _qua_cua(duong: str, ham: str, goi: str, kw: str, cua: str) -> bool:
        """Giá trị truyền cho `kw` phải là một LỜI GỌI `cua`, không phải giá
        trị THÔ. Payload/QSettings mang được rác (chuỗi, NaN, số ngoài trần);
        một hệ số BỊA nhân vào ĐỘ DÀI TIẾNG thì không có đường lùi."""
        for n in ast.walk(than_ham(duong, ham)):
            if not (isinstance(n, ast.Call) and (
                    getattr(n.func, "id", "") == goi
                    or getattr(n.func, "attr", "") == goi)):
                continue
            for k in n.keywords:
                if k.arg != kw:
                    continue
                if isinstance(k.value, ast.Call) and (
                        getattr(k.value.func, "id", "") == cua
                        or getattr(k.value.func, "attr", "") == cua):
                    return True
                # UI gán ra biến trước rồi mới truyền -> tra biến đó.
                if isinstance(k.value, ast.Name):
                    for g in ast.walk(than_ham(duong, ham)):
                        if (isinstance(g, ast.Assign)
                                and any(getattr(t, "id", "") == k.value.id
                                        for t in g.targets)
                                and isinstance(g.value, ast.Call)
                                and (getattr(g.value.func, "id", "") == cua
                                     or getattr(g.value.func, "attr", "")
                                     == cua)):
                            return True
        return False

    ok(_qua_cua("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
                "keo_dai_giong", "chuan_keo_dai"),
       "10jg `jobs._thay_giong` đọc payload QUA `chuan_keo_dai` "
       "(payload cũ/rác không được nhân thẳng vào độ dài tiếng)")
    ok(_qua_cua("app/ui/thay_giong_dialog.py", "_chay", "xep_mot",
                "keo_dai_giong", "chuan_keo_dai"),
       "10jh hộp Thay giọng cũng đi QUA `chuan_keo_dai` (CỬA DUY NHẤT)")
    ok(not _qua_cua("app/queue/jobs.py", "_thay_giong", "thay_giong_mot_video",
                    "keo_dai_giong", "ham_bia_ra_khong_ton_tai"),
       "10ji TỰ KIỂM BỘ DÒ: cửa bịa ra thì `_qua_cua` trả HỎNG")

    # ---- 10k: Ô TRONG HỘP THAY GIỌNG ----
    app_qt()
    from app.ui.thay_giong_dialog import ThayGiongDialog
    dl = ThayGiongDialog(None)
    try:
        dat = [dl.cb_keo.itemData(i) for i in range(dl.cb_keo.count())]
        ok([float(x) for x in dat] == [float(x) for x in tg.MUC_KEO_DAI],
           "10k combo 'Kéo dài giọng' có ĐỦ mức, đúng thứ tự", str(dat))
        ok(dl.cb_keo.currentIndex() == 0
           and tg.chuan_keo_dai(dl.cb_keo.currentData()) == 1.0,
           "10ka MỞ HỘP LÊN mặc định vẫn TẮT (không đổi tiếng sau lưng ai)",
           dl.cb_keo.currentText())
        nhan_het = [dl.cb_keo.itemText(i) for i in range(dl.cb_keo.count())]
        ok(all(n == tg.nhan_keo_dai(float(dl.cb_keo.itemData(i)))
               for i, n in enumerate(nhan_het)),
           "10kb nhãn combo DỰNG TỪ `nhan_keo_dai` (một phép đo, một chỗ đọc)")
        tip = dl.cb_keo.toolTip()
        ok(all(x in tip for x in ("méo", "nghe")),
           "10kc chú thích nói CẢ cái giá (méo tiếng) CẢ 'chưa ai nghe thử'",
           f"{len(tip)} ký tự")
        ok(not any(ord(c) > 0x2500 for c in "".join(nhan_het) + tip),
           "10kd nhãn + chú thích KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen)")
    finally:
        dl.deleteLater()


def main() -> int:
    print("CỔNG 89 — âm thanh bị bé · chỉnh hình theo giọng · hộp gọn · "
          "che chữ không trôi · đọc ĐỀU một tốc độ · KÉO DÀI cho đầy khung")
    muc1(); muc2(); muc3(); muc4(); muc5(); muc6(); muc7(); muc8(); muc9()
    muc10()
    print(f"\nĐẠT {DAT} · HỎNG {HONG}")
    return 0 if HONG == 0 else 1


if __name__ == "__main__":
    don()
    try:
        sys.exit(main())
    finally:
        if os.environ.get("BQ_GIU_HOP") != "1":
            don()
        try:
            _INI.unlink(missing_ok=True)
        except OSError:
            pass
