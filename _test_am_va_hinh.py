"""CỔNG 76 — ÂM THANH KHÔNG BỊ BÉ · CHỈNH VIDEO THEO GIỌNG · HỘP BỚT RỐI ·
NHÃN NHẤN NHÁ.

Bốn việc anh Hùng nêu 18/08/2026 (ảnh v2.36.0, hộp Thay giọng, `ov:nam_tre`):
  1. *"lỗi quan trọng: âm thanh video bị lỗi hay sao cứ bị bé"*
  2. *"giọng cứ lúc nhanh lúc chậm không đều — đáng nhẽ chỉ chỉnh video sao
     cho khớp giọng nói chứ"*
  3. *"cái phần edit chữ kia nhiều quá, không gom vào làm 1 được à"*
  4. *"giọng chả có hồn gì, không có cảm xúc, rất là trơ"*

CỔNG NÀY CANH 6 ĐIỀU:
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
6. **NHÃN NHẤN NHÁ:** giọng ĐÃ ĐO thì hiện số, giọng CHƯA ĐO thì KHÔNG bịa;
   không so số giữa hai ngôn ngữ khác nhau (bẫy đã sập: Aria đo trên câu
   tiếng Anh ra 5,89 nhưng trên corpus tiếng Việt chỉ 2,72).

TỰ KIỂM: `_pha_am_va_hinh.py` gỡ từng chốt ra và cổng phải ĐỎ.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# PHẢI đặt TRƯỚC mọi import chạm `app.ui` — `app_settings()` mặc định đọc
# REGISTRY THẬT của anh Hùng, và cổng 68 đã ĐỎ OAN một lần vì đúng chuyện đó.
_INI = Path(tempfile.gettempdir()) / f"bq_cong76_{os.getpid()}.ini"
os.environ["BQ_QSETTINGS_INI"] = str(_INI)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TG_BO_QUA_CHI_PHI", "1")

import _test_guard  # noqa: E402,F401  (chặn mở Explorer/trình phát, stdout utf-8)

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FF = REPO / "bin" / "ffmpeg.exe"
FP = REPO / "bin" / "ffprobe.exe"
NOWIN = 0x08000000

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
        _HOP = REPO / f"_am76_{os.getpid()}"
        _HOP.mkdir(exist_ok=True)
    return _HOP


def don() -> None:
    for d in REPO.glob("_am76_*"):
        shutil.rmtree(d, ignore_errors=True)


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
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
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


def muc6() -> None:
    """NHÃN NHẤN NHÁ: có số thì hiện, chưa đo thì KHÔNG bịa."""
    print("\nMỤC 6 — nhãn nhấn nhá: chỉ nói cái đã đo")
    from app.core import nhan_nha as NN
    ok(NN.muc("vi-VN-NamMinhNeural", "vi") is not None,
       "giọng ĐÃ ĐO có số", str(NN.muc("vi-VN-NamMinhNeural", "vi")))
    ok(NN.muc("vi-VN-KhongCoGiongNay", "vi") is None,
       "giọng CHƯA ĐO -> None (không bịa)")
    ok(NN.nhan_kem("vi-VN-KhongCoGiongNay", "vi") == "",
       "giọng chưa đo -> nhãn RỖNG")
    ok("nhấn nhá" in NN.nhan_kem("vi-VN-NamMinhNeural", "vi"),
       "giọng đã đo -> nhãn có số",
       NN.nhan_kem("vi-VN-NamMinhNeural", "vi"))
    # BẪY ĐÃ SẬP: số của corpus tiếng Việt KHÔNG nói được gì về tiếng khác
    ok(NN.muc("vi-VN-NamMinhNeural", "en") is None,
       "ngôn ngữ KHÁC corpus -> None (cấm so số giữa 2 ngôn ngữ)")
    ok(NN.nhan_kem("vi-VN-NamMinhNeural", "ja") == "",
       "đổi ngôn ngữ đích -> KHÔNG dán số tiếng Việt vào")
    g = NN.goi_y_giong("vi")
    ok(g is not None and g[1] == max(NN.BANG_VI.values()),
       "gợi ý ĐÚNG giọng nhấn nhá cao nhất", str(g))
    ok(NN.goi_y_giong("en") is None,
       "ngôn ngữ chưa có bảng -> KHÔNG gợi ý bừa")
    ok(bool(NN.cau_goi_y("vi")) and not NN.cau_goi_y("en"),
       "câu gợi ý chỉ hiện cho ngôn ngữ đã đo")
    # Nhãn KHÔNG EMOJI (bài học v2.6.22 — máy anh Hùng thiếu glyph -> ô đen)
    import unicodedata
    xau = [c for c in NN.cau_goi_y("vi") + NN.nhan_kem("vi-VN-NamMinhNeural")
           if ord(c) > 0xFFFF or unicodedata.category(c) == "So"]
    ok(not xau, "nhãn KHÔNG EMOJI", str(xau))
    # Combo hộp thoại phải THẬT SỰ mang nhãn đó
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from app.ui.thay_giong_dialog import ThayGiongDialog
    d = ThayGiongDialog(None)
    try:
        d.cb_nn.setCurrentIndex(max(0, d.cb_nn.findData("vi")))
        app.processEvents()
        nh = [d.cb_giong.itemText(i) for i in range(d.cb_giong.count())]
        ok(any("nhấn nhá" in t for t in nh),
           "combo giọng THẬT SỰ hiện mức nhấn nhá",
           next((t for t in nh if "nhấn nhá" in t), ""))
        ok(bool(d.lb_goi_y.text()),
           "hộp hiện dòng gợi ý giọng nhiều cảm xúc", d.lb_goi_y.text()[:70])
    finally:
        d.deleteLater()


def main() -> int:
    print("CỔNG 76 — âm thanh bị bé · chỉnh hình theo giọng · hộp gọn · "
          "nhãn nhấn nhá")
    muc1(); muc2(); muc3(); muc4(); muc5(); muc6()
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
