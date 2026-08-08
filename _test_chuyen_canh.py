# -*- coding: utf-8 -*-
"""CỔNG 36 — CHUYỂN CẢNH Ở CHỖ GHÉP ĐOẠN (xfade) + CỬA CHỜ ffmpeg.

Chạy: .venv\\Scripts\\python _test_chuyen_canh.py

VÌ SAO CÓ CỔNG NÀY — 4 lỗi/rủi ro THẬT của việc này (07/08/2026):

(a) **LỆCH PHỤ ĐỀ + LỆCH TIẾNG-HÌNH.** `xfade` ĂN BỚT `d` giây ở MỖI chỗ nối
    (output = dài(A)+dài(B)-d). Phụ đề `.ass` và mốc tiếng động đã dựng theo
    timeline "các đoạn nối THẲNG", nên không bù thì clip 4 đoạn × 0,3s lệch
    **0,9 giây** từ chỗ nối đầu trở đi. Đây đúng loại lỗi v1.87 ("hình một đằng
    tiếng một đằng") mà anh Hùng đã báo 1 lần. Cách chữa: lấy THÊM đúng `d` giây
    phim ở cuối đoạn trước rồi đặt `offset = dài_gốc` (xem `_bu_xfade`). Cổng
    này ĐO ĐỘ LỆCH THẬT bằng khung hình + tương quan chéo sóng tiếng, không tin
    vào lý thuyết.

(b) **CỬA CHỜ BỊ XOÁ MÀ KHÔNG AI BIẾT.** Đã xảy ra thật trong lúc làm việc này:
    một lượt sửa khác ghi đè `_run` và **cửa chờ biến mất**; app vẫn chạy, test
    vẫn xanh, chỉ có số đo tố giác (10 lượt vẫn ra 397 luồng = 16,5x số nhân).
    Nay có ca QUÉT TĨNH: `_run` PHẢI đi qua `_xin_cho_ffmpeg`.

(c) **KIỂU xfade BỊ GỠ KHỎI ffmpeg.** Đổi bản ffmpeg trong `bin/` mà kiểu không
    còn thì ffmpeg trả lỗi -> `_run_with_fallback` thử libx264 -> cũng lỗi ->
    ném RuntimeError. Phải FAIL TO, tuyệt đối không im lặng ra clip cắt khô.

(d) **BẤT BIẾN SỐNG CÒN.** Anh Hùng đang chạy sản xuất 200-300 kênh bằng preset
    cũ. Chuyển cảnh TẮT phải ra file GIỐNG bản `main` (đo PSNR, không đoán) —
    kể cả sau khi đã thêm núm `-threads` giải mã / `-filter_threads`.

QUY TẮC: ffmpeg THẬT, video Nhật THẬT, đường hook-first (NGƯỢC thời gian) +
nguồn VFR. Mọi ca FAIL đều in SỐ ĐO.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_xfade_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

import numpy as np  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x08000000
FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH
THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


# ---------------------------------------------------------------- tiện ích đo
def _chay(cmd: list[str], giay: int = 240) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NOWIN, timeout=giay)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def dai_video(p: Path) -> float:
    rc, out = _chay([FP, "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(p)])
    try:
        return float(out.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


def so_khung(p: Path) -> int:
    """Số khung ĐỌC ĐƯỢC (0 nếu hỏng). Dùng cho ca GPU: 0 khung và khung VÔ TẬN
    đều là bệnh thật đã đo được của `xfade_opencl`."""
    rc, out = _chay([FP, "-v", "error", "-select_streams", "v:0",
                     "-count_frames", "-show_entries", "stream=nb_read_frames",
                     "-of", "csv=p=0", str(p)])
    s = (out or "").strip().splitlines()
    return int(s[0]) if s and s[0].strip().isdigit() else 0


def khung(p: Path, t: float, dst: Path) -> bool:
    """Trích 1 khung ở mốc t (giây) ra PNG. `-ss` TRƯỚC `-i` = seek nhanh."""
    rc, _ = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                   "-ss", f"{t:.3f}", "-i", str(p), "-frames:v", "1",
                   "-q:v", "2", str(dst)])
    return rc == 0 and dst.exists() and dst.stat().st_size > 0


def _xam(p: Path):
    import cv2
    im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    return None if im is None else im.astype(np.int16)


def ti_le_khac(a: Path, b: Path, nguong: int = 24) -> float:
    """% pixel lệch mức xám > nguong. 0 = 2 khung như nhau."""
    ia, ib = _xam(a), _xam(b)
    if ia is None or ib is None or ia.shape != ib.shape:
        return -1.0
    return round(float(np.mean(np.abs(ia - ib) > nguong)) * 100.0, 2)


def sang_tb(p: Path) -> float:
    im = _xam(p)
    return -1.0 if im is None else round(float(np.mean(im)), 1)


def psnr(a: Path, b: Path) -> float:
    ia, ib = _xam(a), _xam(b)
    if ia is None or ib is None or ia.shape != ib.shape:
        return -1.0
    mse = float(np.mean((ia - ib) ** 2))
    return 99.0 if mse < 1e-9 else round(10.0 * np.log10(255.0 ** 2 / mse), 1)


def lech_hinh_ms(on: Path, off: Path, t: float, fps: float = 30.0,
                 quet: int = 6) -> tuple[float, float]:
    """ĐỘ LỆCH HÌNH THẬT: khung của `on` ở mốc t khớp nhất với khung của `off`
    ở mốc t + k/fps (k quét -quet..+quet). Trả (lệch_ms, %khác_tại_khớp).

    Đây là phép đo TRỰC TIẾP cái "clip bị ngắn đi vì xfade": timeline trôi bao
    nhiêu khung thì k khớp nhất lệch đúng bấy nhiêu.
    """
    ka = _SB / "lh_on.png"
    if not khung(on, t, ka):
        return (9999.0, -1.0)
    tot_k, tot_v = 0, 1e9
    for k in range(-quet, quet + 1):
        kb = _SB / f"lh_off_{k}.png"
        if not khung(off, t + k / fps, kb):
            continue
        v = ti_le_khac(ka, kb)
        if 0 <= v < tot_v:
            tot_v, tot_k = v, k
    return (round(tot_k / fps * 1000.0, 1), round(tot_v, 2))


def song_tieng(p: Path, tu: float, dai: float):
    """Sóng tiếng mono 8kHz của khoảng [tu, tu+dai] -> mảng float."""
    raw = _SB / "w.raw"
    rc, _ = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                   "-ss", f"{tu:.3f}", "-t", f"{dai:.3f}", "-i", str(p),
                   "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", str(raw)])
    if rc != 0 or not raw.exists():
        return None
    d = np.frombuffer(raw.read_bytes(), dtype="<i2").astype(np.float64)
    raw.unlink(missing_ok=True)
    return d if d.size > 1000 else None


def lech_tieng_ms(on: Path, off: Path, tu: float, dai: float = 2.5) -> float:
    """ĐỘ LỆCH TIẾNG: tương quan chéo sóng tiếng `on` vs `off` cùng khoảng thời
    gian -> độ trễ (ms). 0 = tiếng không trôi so với hình."""
    a, b = song_tieng(on, tu, dai), song_tieng(off, tu, dai)
    if a is None or b is None:
        return 9999.0
    n = min(a.size, b.size)
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    m = int(0.4 * 8000)                     # quét ±400ms là quá đủ cho mốc 80ms
    c = np.correlate(a, b, mode="full")
    mid = n - 1
    lo, hi = max(0, mid - m), min(c.size, mid + m + 1)
    k = int(np.argmax(c[lo:hi])) + lo - mid
    return round(k / 8000.0 * 1000.0, 1)


def ass_moc(dst: Path, moc: float, dai_clip: float) -> Path:
    """.ass CHỈ có 1 khối chữ TRẮNG TO trong [moc, moc+0.4] — dùng để đo LỆCH
    PHỤ ĐỀ: chữ phải hiện ĐÚNG mốc đó trong clip có chuyển cảnh."""
    def hms(v: float) -> str:
        return f"{int(v // 3600)}:{int(v // 60) % 60:02d}:{v % 60:05.2f}"
    dst.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,"
        "SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
        "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: D,Arial,220,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,8,0,5,20,20,20,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,"
        "MarginV,Effect,Text\n"
        f"Dialogue: 0,{hms(moc)},{hms(min(dai_clip, moc + 0.4))},D,,0,0,0,,"
        "{\\an5}MOCMOCMOC\n", encoding="utf-8")
    return dst


def dem_trang(p: Path) -> int:
    """Số pixel gần TRẮNG (>=250) — đếm chữ phụ đề đã đốt vào hình."""
    im = _xam(p)
    return -1 if im is None else int(np.sum(im >= 250))


def xuat(src: Path, dst: Path, segs: list, muc, ass: str = "",
         **kw) -> tuple[bool, str]:
    dst.unlink(missing_ok=True)
    try:
        fu.export_canvas_clip(
            str(src), str(dst), segs, (0.5, 0.42, 0.98), bg="blur",
            out_w=1080, out_h=1920, ass_path=(ass or None),
            fx_fade=False, fx_whoosh=False, chuyen_canh=muc, **kw)
    except Exception as e:                              # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"[:300]
    return dst.exists() and dst.stat().st_size > 0, ""


# ============================== CA 1: CỬA CHỜ ==============================
def ca_cua_cho() -> None:
    print("\n[CA 1] CỬA CHỜ: số lệnh ffmpeg chạy cùng lúc")
    import inspect
    ma = inspect.getsource(fu._run)
    bao("`_run` đi qua cửa chờ (quét tĩnh)",
        "_xin_cho_ffmpeg" in ma and "_tra_cho_ffmpeg" in ma,
        "có `_xin_cho_ffmpeg`" if "_xin_cho_ffmpeg" in ma
        else "KHÔNG THẤY — cửa chờ đã bị ghi đè, 10 lượt sẽ lại 592 luồng")

    n_may = fu.so_ffmpeg_song_song()
    bao("trần tự đo theo máy nằm trong 1..4",
        1 <= n_may <= 4, f"{n_may} (nhân={os.cpu_count()})")

    os.environ["BQ_FFMPEG_SLOTS"] = "3"
    try:
        bao("BQ_FFMPEG_SLOTS ép được trần", fu.so_ffmpeg_song_song() == 3,
            f"{fu.so_ffmpeg_song_song()} (đặt 3)")
        dinh = {"v": 0}
        dang = {"v": 0}
        lk = threading.Lock()

        def viec() -> None:
            if not fu._xin_cho_ffmpeg():
                return
            try:
                with lk:
                    dang["v"] += 1
                    dinh["v"] = max(dinh["v"], dang["v"])
                time.sleep(0.25)
            finally:
                with lk:
                    dang["v"] -= 1
                fu._tra_cho_ffmpeg()

        ths = [threading.Thread(target=viec) for _ in range(12)]
        t0 = time.perf_counter()
        for t in ths:
            t.start()
        for t in ths:
            t.join(timeout=30)
        wall = round(time.perf_counter() - t0, 2)
        bao("12 việc song song KHÔNG vượt trần", dinh["v"] <= 3,
            f"đỉnh {dinh['v']}/3 · wall {wall}s (12 việc × 0,25s / 3 chỗ "
            f"≈ 1,0s)")
        bao("hết việc thì trả hết chỗ", fu.dang_chay_ffmpeg() == 0,
            f"còn giữ {fu.dang_chay_ffmpeg()} chỗ")
    finally:
        os.environ.pop("BQ_FFMPEG_SLOTS", None)

    # ECO_MODE (Tiết kiệm máy) phải kéo trần về 1 — máy nhân viên yếu.
    goc = settings.ECO_MODE
    try:
        settings.ECO_MODE = True
        bao("Tiết kiệm máy -> trần 1", fu.so_ffmpeg_song_song() == 1,
            f"{fu.so_ffmpeg_song_song()}")
        bao("Tiết kiệm máy -> giải mã 2 luồng", fu.decode_threads() == 2,
            f"{fu.decode_threads()}")
    finally:
        settings.ECO_MODE = goc

    # Đang ĐÓNG APP thì KHÔNG được treo ở cửa chờ (bước thoát app sẽ đơ).
    fu._SHUTDOWN.set()
    try:
        t0 = time.perf_counter()
        co = fu._xin_cho_ffmpeg()
        cho = round((time.perf_counter() - t0) * 1000, 1)
        bao("đóng app -> cửa chờ nhả ngay, không treo",
            (not co) and cho < 100, f"trả {co} sau {cho}ms")
    finally:
        fu._SHUTDOWN.clear()


# ====================== CA 2: NÚM LUỒNG + HÀM THUẦN ======================
def ca_ham_thuan() -> None:
    print("\n[CA 2] NÚM LUỒNG + LUẬT CHỌN KIỂU (hàm thuần)")
    g = fu._global_enc_opts()
    bao("`-threads` (giải mã) có trong tuỳ chọn toàn cục", "-threads" in g,
        " ".join(g))
    bao("`-filter_threads` có trong tuỳ chọn toàn cục",
        "-filter_threads" in g, " ".join(g))
    bao("giải mã KHÔNG bị hạ về 1 (đo: 1 luồng chậm 30-155%)",
        fu.decode_threads() >= 2, f"decode_threads={fu.decode_threads()}")
    nv = fu._enc_args("h264_nvenc")
    bao("nhánh nvenc có núm `-threads`", "-threads" in nv, " ".join(nv[-4:]))

    rc, out = _chay([FF, "-hide_banner", "-h", "filter=xfade"])
    co = {ln.strip().split()[0] for ln in out.splitlines()
          if ln.startswith("     ") and ln.strip() and "transition" in ln}
    thieu = [k for k in fu.XFADE_KIEU if k not in co]
    bao("58 kiểu xfade đều CÓ trong ffmpeg của bin/",
        len(fu.XFADE_KIEU) == 58 and not thieu,
        f"{len(fu.XFADE_KIEU)} kiểu, thiếu: {thieu or 'không'}")

    segs = [(60.0, 70.0), (20.0, 30.0), (30.5, 31.8), (200.0, 215.0)]
    bao("loại chỗ nối suy đúng theo nội dung",
        [fu._loai_cho_noi(segs, i) for i in range(3)]
        == ["nguoc", "lien", "xa"],
        str([fu._loai_cho_noi(segs, i) for i in range(3)]))
    bao("mức 'tat' -> KHÔNG chuyển cảnh (bất biến preset cũ)",
        fu.chon_chuyen_canh(segs, "tat") == []
        and fu.chon_chuyen_canh(segs, "") == [], "[] cho 'tat' và ''")
    bao("1 đoạn -> KHÔNG chuyển cảnh",
        fu.chon_chuyen_canh([(0.0, 5.0)], "manh") == [], "[]")
    for m in ("nhe", "vua", "manh"):
        xf = fu.chon_chuyen_canh(segs, m)
        kieus = [k for k, _ in xf]
        dais = [d for _, d in xf]
        bao(f"mức '{m}': không lặp MỘT kiểu ở mọi chỗ nối",
            len(set(kieus)) >= 2, str(kieus))
        bao(f"mức '{m}': thời lượng trong 0,25-0,40s",
            all(0.25 <= d <= 0.40 for d in dais), str(dais))
        # Mức 'manh' được phép dùng KERNEL GPU (kho gl-transitions, MIT) khi máy
        # có OpenCL — kiểu GPU KHÔNG nằm trong 58 kiểu của `xfade`. Máy thiếu
        # OpenCL thì `chon_chuyen_canh` đã tự đổi về kiểu CPU (`GPU_LUI_VE`) nên
        # ca này phải đúng ở CẢ HAI loại máy.
        from app.core import hieu_ung_gpu as _HG
        bao(f"mức '{m}': kiểu đều CÓ THẬT (58 kiểu xfade hoặc kernel GPU)",
            all(k in fu.XFADE_KIEU or k in _HG.KHO_GPU for k in kieus),
            str(kieus))
        _gpu_k = [k for k in kieus if k in _HG.KHO_GPU]
        bao(f"mức '{m}': mọi kiểu GPU đều có đường LÙI về CPU",
            all(fu.GPU_LUI_VE.get(k) in fu.XFADE_KIEU for k in _gpu_k),
            str([f"{k}->{fu.GPU_LUI_VE.get(k, '-')}" for k in _gpu_k])
            if _gpu_k else "(mức này không dùng GPU)")
    bao("chọn kiểu TIỀN ĐỊNH (gọi 2 lần ra y nhau, không bốc thăm)",
        fu.chon_chuyen_canh(segs, "vua") == fu.chon_chuyen_canh(segs, "vua"),
        str(fu.chon_chuyen_canh(segs, "vua")))
    xf = fu.chon_chuyen_canh(segs, "vua")
    bao("HẾT PHIM -> thu ngắn phần bù, không đòi phim không có",
        fu._bu_xfade(segs, xf, 70.1)[0] <= 0.11,
        f"bù={fu._bu_xfade(segs, xf, 70.1)} với phim dài 70,1s "
        f"(đoạn 1 hết ở 70,0s)")
    bao("bù < 0,08s -> chỗ nối đó CẮT THẲNG (0.0), không xfade hỏng",
        fu._bu_xfade(segs, xf, 70.02)[0] == 0.0,
        str(fu._bu_xfade(segs, xf, 70.02)))


# ================== CA 3-6: RENDER THẬT + ĐỒNG BỘ ==================
def ca_render(src: Path, ten: str, segs: list, muc: str = "vua") -> None:
    print(f"\n[CA 3/4] RENDER THẬT — {ten} ({len(segs)} đoạn, mức '{muc}')")
    dai_g = [e - s for s, e in segs]
    tong = sum(dai_g)
    xf = fu.chon_chuyen_canh(segs, muc)
    off, on = _SB / f"{ten}_off.mp4", _SB / f"{ten}_on.mp4"
    t0 = time.perf_counter()
    ok1, e1 = xuat(src, off, segs, "tat")
    w_off = round(time.perf_counter() - t0, 2)
    t0 = time.perf_counter()
    ok2, e2 = xuat(src, on, segs, muc)
    w_on = round(time.perf_counter() - t0, 2)
    bao(f"{ten}: xuất được bản TẮT chuyển cảnh", ok1, e1 or f"wall {w_off}s")
    bao(f"{ten}: xuất được bản CÓ chuyển cảnh {[k for k, _ in xf]}",
        ok2, e2 or f"wall {w_on}s (+{round(w_on - w_off, 2)}s cho pha 1.5)")
    if not (ok1 and ok2):
        return

    d_off, d_on = dai_video(off), dai_video(on)
    lech_dai = abs(d_on - d_off) * 1000
    bao(f"{ten}: ĐỘ DÀI không đổi (xfade không ăn bớt thời lượng)",
        lech_dai < 40, f"tắt {d_off:.3f}s · bật {d_on:.3f}s · lệch "
        f"{lech_dai:.0f}ms (nếu KHÔNG bù sẽ hụt "
        f"{sum(d for _, d in xf) * 1000:.0f}ms)")

    # chỗ nối thứ 1: GIỮA vệt chuyển cảnh -> khung phải KHÁC HẲN bản cắt thẳng
    a = dai_g[0]
    d = xf[0][1]
    kon, koff = _SB / "j_on.png", _SB / "j_off.png"
    if khung(on, a + d / 2, kon) and khung(off, a + d / 2, koff):
        tl = ti_le_khac(kon, koff)
        bao(f"{ten}: CHUYỂN CẢNH CÓ XẢY RA ở chỗ nối 1 (đếm pixel)",
            tl >= 8.0, f"{tl}% pixel khác bản cắt thẳng tại mốc "
            f"{a + d / 2:.2f}s (cần >= 8%)")
        if xf[0][0] == "fadeblack":
            s_on, s_off = sang_tb(kon), sang_tb(koff)
            bao(f"{ten}: 'fadeblack' làm TỐI thật ở giữa vệt",
                s_on < s_off * 0.75,
                f"sáng TB bật {s_on} vs tắt {s_off}")

    # ĐỘ LỆCH HÌNH ở mốc SAU chỗ nối cuối — đây là chỗ lệch tích luỹ lớn nhất
    t_cuoi = tong - 1.0
    lh, kh = lech_hinh_ms(on, off, t_cuoi, quet=8)
    bao(f"{ten}: LỆCH HÌNH sau chỗ nối cuối < 80ms",
        abs(lh) < 80, f"{lh}ms (khớp còn {kh}% khác) ở mốc {t_cuoi:.2f}s · "
        f"không bù thì phải lệch {sum(d for _, d in xf) * 1000:.0f}ms")

    lt = lech_tieng_ms(on, off, max(0.2, tong - 3.0), 2.5)
    bao(f"{ten}: LỆCH TIẾNG sau chỗ nối cuối < 80ms",
        abs(lt) < 80, f"{lt}ms (tương quan chéo sóng 8kHz)")


def ca_phu_de(src: Path, segs: list, muc: str = "vua") -> None:
    print("\n[CA 5] LỆCH PHỤ ĐỀ — chữ phải hiện ĐÚNG mốc dù có chuyển cảnh")
    tong = sum(e - s for s, e in segs)
    xf = fu.chon_chuyen_canh(segs, muc)
    hut = sum(d for _, d in xf)
    moc = tong - 1.2                       # SAU mọi chỗ nối -> lệch tích luỹ
    ass = str(ass_moc(_SB / "moc.ass", moc, tong))
    on, off = _SB / "sub_on.mp4", _SB / "sub_off.mp4"
    ok, e = xuat(src, on, segs, muc, ass=ass)
    ok2, e2 = xuat(src, off, segs, "tat", ass=ass)
    bao("xuất được clip có phụ đề (cả bản TẮT và bản CÓ chuyển cảnh)",
        ok and ok2, (e + " " + e2).strip() or "ok")
    if not (ok and ok2):
        return
    # NGƯỠNG PHẢI THEO TỈ LỆ, ĐỪNG CỨNG: chính khung phim đã có vùng gần trắng
    # (áo/trời sáng) nên khung KHÔNG có chữ vẫn đếm được 4.634 px -> ngưỡng cứng
    # 1.500 px FAIL OAN (đã sập 1 lần). Mốc đúng: chữ phải làm số pixel trắng
    # TĂNG GẤP NHIỀU LẦN, và bản CÓ chuyển cảnh phải giống bản TẮT ở CÙNG mốc.
    d: dict = {}
    for nhan, f in (("on", on), ("off", off)):
        for ten, t in (("tai", moc + 0.2), ("truoc", moc - 0.6)):
            k = _SB / f"s_{nhan}_{ten}.png"
            d[f"{nhan}_{ten}"] = dem_trang(k) if khung(f, t, k) else -1
    bao("chữ HIỆN tại đúng mốc (bản có chuyển cảnh)",
        d["on_tai"] > 3000 and d["on_tai"] > d["on_truoc"] * 4,
        f"{d['on_tai']} px trắng ở {moc + 0.2:.2f}s vs {d['on_truoc']} px ở "
        f"{moc - 0.6:.2f}s (cần gấp > 4 lần)")
    bao("PHỤ ĐỀ KHÔNG LỆCH: bản có chuyển cảnh khớp bản TẮT ở CÙNG mốc",
        d["off_tai"] > 3000
        and abs(d["on_tai"] - d["off_tai"]) <= 0.30 * max(1, d["off_tai"])
        and abs(d["on_truoc"] - d["off_truoc"]) <= 0.50 * max(1, d["off_tai"]),
        f"tại mốc: bật {d['on_tai']} / tắt {d['off_tai']} · trước mốc: bật "
        f"{d['on_truoc']} / tắt {d['off_truoc']} · nếu lệch thì chữ đã nhảy "
        f"sớm {hut * 1000:.0f}ms và 2 số ở CÙNG mốc phải chênh hẳn")


def ca_vfr(src: Path) -> None:
    print("\n[CA 6] NGUỒN VFR (khung hình không đều) + hook-first")
    vfr = _SB / "vfr.mkv"
    # Dựng nguồn VFR THẬT: bỏ khung KHÔNG ĐỀU nhưng **GIỮ NGUYÊN PTS gốc**
    # (`-fps_mode passthrough`, KHÔNG setpts) -> khoảng cách khung biến thiên
    # thật = VFR thật, mà timestamp vẫn hợp lệ.
    # BẪY ĐÃ SẬP: bản đầu dùng `setpts=N/FRAME_RATE/TB` + `-fps_mode vfr` ->
    # file ra có luồng ffmpeg không đọc nổi, xfade nổ "Cannot determine format
    # of input 0:0 after EOF" và tưởng là lỗi chuyển cảnh.
    rc, log = _chay([FF, "-y", "-hide_banner", "-loglevel", "error",
                     "-ss", "100", "-t", "60", "-i", str(src),
                     "-vf", "select='not(mod(n,3))+not(mod(n,11))'",
                     "-fps_mode", "passthrough",
                     "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
                     "-c:a", "aac", str(vfr)], giay=300)
    bao("dựng được nguồn VFR để thử", rc == 0 and vfr.exists(),
        f"rc={rc} {log.strip().splitlines()[-1] if log.strip() else ''}"[:150])
    if rc != 0 or not vfr.exists():
        return
    _r, _i = _chay([FP, "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=nb_read_frames,avg_frame_rate,"
                    "r_frame_rate", "-count_frames", "-of", "csv=p=0",
                    str(vfr)])
    print(f"    [VFR] dài {dai_video(vfr):.2f}s · {_i.strip()[:80]}")
    segs = [(40.0, 50.0), (5.0, 15.0)]      # NGƯỢC thời gian = hook-first
    off, on = _SB / "vfr_off.mp4", _SB / "vfr_on.mp4"
    ok1, e1 = xuat(vfr, off, segs, "tat")
    ok2, e2 = xuat(vfr, on, segs, "vua")
    bao("VFR: xuất được cả 2 bản", ok1 and ok2, (e1 + " " + e2) or "ok")
    if not (ok1 and ok2):
        return
    d_off, d_on = dai_video(off), dai_video(on)
    bao("VFR: độ dài không đổi", abs(d_on - d_off) * 1000 < 60,
        f"tắt {d_off:.3f}s · bật {d_on:.3f}s")
    lh, kh = lech_hinh_ms(on, off, 18.5, quet=8)
    bao("VFR: LỆCH HÌNH < 80ms", abs(lh) < 80, f"{lh}ms (khớp {kh}% khác)")
    lt = lech_tieng_ms(on, off, 16.5, 2.5)
    bao("VFR: LỆCH TIẾNG < 80ms", abs(lt) < 80, f"{lt}ms")


def ca_kieu_sai(src: Path) -> None:
    print("\n[CA 7] KIỂU xfade SAI phải FAIL TO + KHÔNG BỎ LẠI RÁC")
    tmp = Path(tempfile.gettempdir())
    truoc = {p.name for p in tmp.glob("_seg_*")}
    dst = _SB / "sai.mp4"
    ok, e = xuat(src, dst, [(60.0, 66.0), (20.0, 26.0)],
                 [("kieu_khong_ton_tai", 0.3)])
    bao("kiểu lạ -> ném lỗi, KHÔNG trả file êm", (not ok) and bool(e),
        (e or "KHÔNG NÉM LỖI — nguy hiểm: user tưởng có chuyển cảnh")[:160])
    bao("kiểu lạ -> KHÔNG để lại file thành phẩm hỏng",
        not dst.exists() or dst.stat().st_size == 0,
        "không có file" if not dst.exists() else f"{dst.stat().st_size} byte")
    # RÒ RÁC THẬT (có từ `main`): pha 1 lỗi giữa đường -> caller gọi
    # `_cleanup_paths(_seg_temps)` mà `_seg_temps` còn RỖNG (phép gán chưa chạy)
    # -> mảnh `.mkv` nằm lại vĩnh viễn. Đo 07/08/2026: 0,53 GB `_seg_*` trong
    # %TEMP%; cùng loại rác 1,71 GB phải dọn tay hôm 31/07 khi ổ C đầy 100%.
    sot = sorted({p.name for p in tmp.glob("_seg_*")} - truoc)
    mb = sum((tmp / s).stat().st_size for s in sot
             if (tmp / s).exists()) / 1e6
    bao("xuất LỖI vẫn dọn hết mảnh `_seg_*` (không phình %TEMP%)",
        not sot, f"còn sót {len(sot)} file / {mb:.1f} MB: {sot[:4]}"
        if sot else "0 file sót")


def ca_bat_bien(src: Path) -> None:
    """BẤT BIẾN SỐNG CÒN: chuyển cảnh TẮT phải ra file GIỐNG bản `main`.

    Nạp `ffmpeg_utils.py` của `main` THÀNH MODULE RIÊNG (nó chỉ cần
    `from config import settings`, mọi import app khác là import TRỄ) rồi xuất
    cùng tham số -> so PSNR. Cách này so ĐÚNG bản main thật, không phải so
    "lệnh trông giống nhau".
    """
    print("\n[CA 8] BẤT BIẾN: chuyển cảnh TẮT == bản `main` (PSNR >= 50 dB)")
    import importlib.util
    # CHỈ lấy stdout: `git show` hay in kèm cảnh báo "LF will be replaced by
    # CRLF" ra stderr; trộn vào là file .py mở đầu bằng chữ 'warning:' -> nạp nổ.
    # Mốc đối chứng đổi được: SAU KHI gộp vào `main` thì `main` CHÍNH LÀ nhánh
    # này, muốn đo bất biến phải trỏ về mốc TRƯỚC khi gộp (`origin/main`).
    # Đây KHÔNG phải cửa lách: chốt chặn "so-với-chính-mình" ngay dưới so NỘI
    # DUNG, nên trỏ vào bản trùng vẫn FAIL y như cũ.
    _moc = os.environ.get("BQ_MOC_REF", "main")
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{_moc}:app/core/ffmpeg_utils.py"],
                       capture_output=True, creationflags=_NOWIN, timeout=60)
    out = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(out) < 5000:
        bao(f"lấy được ffmpeg_utils.py của {_moc}", False,
            f"git rc={r.returncode} · {len(out)} ký tự")
        return
    # ---- CHỐNG PASS OAN: bản `main` PHẢI KHÁC nhánh này ------------------
    # LỖI THẬT (lượt kiểm ĐỘC LẬP 08/08/2026): giữa lượt kiểm, một tiến trình
    # KHÁC chạy `git checkout main` + `git merge hieu-ung-video` (fast-forward)
    # -> `main` trỏ ĐÚNG commit của nhánh. Từ đó `git show main:...` trả về
    # CHÍNH file đang test: phép so thành "so nó với chính nó" và **PSNR luôn
    # 99 dB mãi mãi** — cổng vẫn xanh trong khi bất biến SỐNG CÒN (200-300 kênh
    # đang chạy preset cũ) KHÔNG còn được kiểm một chút nào.
    # Đúng loại "app vẫn chạy, test vẫn xanh, chỉ SỐ ĐO tố giác" đã ghi ở đầu
    # `VIEC_HIEU_UNG.md`. Vì vậy phải TỰ KIỂM đối chứng trước khi tin kết quả.
    _nay = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    if out.strip() == _nay.strip():
        bao("bản `main` phải KHÁC nhánh này (chống so-với-chính-mình)", False,
            "`git show main:app/core/ffmpeg_utils.py` TRÙNG file đang test -> "
            "`main` đã bị merge/fast-forward tới nhánh này, phép so BẤT BIẾN "
            "vô nghĩa. Chạy `git branch -f main origin/main` rồi kiểm lại.")
        return
    bao("bản `main` KHÁC nhánh này (đối chứng hợp lệ)", True,
        f"main {len(out)} ký tự · nhánh {len(_nay)} ký tự")
    fmain = _SB / "fu_main.py"
    fmain.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("fu_main", str(fmain))
    if spec is None or spec.loader is None:
        bao("nạp được module main", False, "spec/loader None")
        return
    mm = importlib.util.module_from_spec(spec)
    sys.modules["fu_main"] = mm          # dataclass/annotations cần module trong
    try:                                # sys.modules, thiếu là nổ AttributeError
        spec.loader.exec_module(mm)
    except Exception as e:                              # noqa: BLE001
        import traceback
        bao("nạp được module main", False,
            f"{type(e).__name__}: {e} | {traceback.format_exc()[-300:]}")
        return
    segs = [(60.0, 70.0), (20.0, 30.0)]
    a, b = _SB / "bb_main.mp4", _SB / "bb_tat.mp4"
    try:
        mm.export_canvas_clip(str(src), str(a), segs, (0.5, 0.42, 0.98),
                              bg="blur", out_w=1080, out_h=1920,
                              fx_fade=False, fx_whoosh=False)
    except Exception as e:                              # noqa: BLE001
        bao("xuất được bằng mã của main", False, f"{e}"[:200])
        return
    ok, e = xuat(src, b, segs, "tat")
    if not ok:
        bao("xuất được bằng mã nhánh này (TẮT)", False, e)
        return
    d1, d2 = dai_video(a), dai_video(b)
    bao("độ dài giống main", abs(d1 - d2) * 1000 < 40,
        f"main {d1:.3f}s · nhánh {d2:.3f}s")
    ps = []
    for t in (1.0, 5.0, 9.5, 12.0, 18.0):
        ka, kb = _SB / "bb_a.png", _SB / "bb_b.png"
        if khung(a, t, ka) and khung(b, t, kb):
            ps.append(psnr(ka, kb))
    bao("PSNR >= 50 dB ở mọi mốc kiểm (preset cũ KHÔNG bị đổi hình)",
        bool(ps) and min(ps) >= 50.0,
        f"PSNR các mốc = {ps} dB (thấp nhất {min(ps) if ps else '?'})")


def ca_gpu_fallback() -> None:
    """NHÓM GPU: máy KHÔNG kham được thì TỰ TẮT, tuyệt đối không nổ lỗi.

    Máy nhân viên có thể không có OpenCL / không có Vulkan / không GPU rời. Cửa
    duy nhất caller cần là `dung_duoc()` — nó phải trả **[]** chứ không được ném.

    Kèm 2 ca QUÉT TĨNH canh đúng 2 tai nạn ĐÃ ĐO của nhóm này (08/08/2026):
      · `VE_LAI_MOC` phải có `setpts=` và **KHÔNG được có `fps=`**. `xfade_opencl`
        trả PTS rác (AV_NOPTS, in ra `-600479950316066`); ai "chữa" bằng `fps=`
        thì ffmpeg sinh khung vô tận -> đo thật **19,1 GB RSS + 364 CPU-giây
        trong 9 phút** rồi phải giết tay.
      · `dau_vao()` phải có `settb=` — thiếu nó thì chuyển cảnh chạy xong trong
        ĐÚNG 1 khung (đo: khung giữa giống đoạn B 100%, tức nhìn ra là cắt khô).
    """
    print("\n[CA 9] NHÓM GPU (xfade_opencl / libplacebo): fallback ÊM + 2 phanh")
    from app.core import hieu_ung_gpu as GPU

    bao("`VE_LAI_MOC` có `setpts=` (chống PTS rác -> 0 khung)",
        "setpts=" in GPU.VE_LAI_MOC, GPU.VE_LAI_MOC)
    bao("`VE_LAI_MOC` KHÔNG có `fps=` (chống sinh khung vô tận / 19 GB RAM)",
        "fps=" not in GPU.VE_LAI_MOC, GPU.VE_LAI_MOC)
    bao("`dau_vao()` có `settb=` (chống chuyển cảnh xong trong 1 khung)",
        "settb=" in GPU.dau_vao(30), GPU.dau_vao(30))

    # kiểu lạ phải NÉM LỖI (như đường CPU), không im lặng
    try:
        GPU.lenh_vung_chong("a.mp4", "b.mp4", "o.mp4", "khong_co_kieu_nay", 0.3)
        bao("kiểu GPU lạ -> ném lỗi", False, "KHÔNG ném — sẽ ra clip cắt khô")
    except (ValueError, RuntimeError) as e:
        bao("kiểu GPU lạ -> ném lỗi", True, f"{type(e).__name__}: {e}"[:90])

    # GIẢ máy nhân viên: không có file kernel -> tự tắt, KHÔNG ném
    goc = GPU.duong_kernel
    try:
        GPU.duong_kernel = lambda: ""            # type: ignore[assignment]
        GPU._CO.pop("opencl", None)
        ds = GPU.dung_duoc(do_lai=True)
        bao("máy THIẾU kernel -> `dung_duoc()` = [] (tự tắt, không nổ)",
            ds == [], f"trả {ds!r}")
    except Exception as e:                                   # noqa: BLE001
        bao("máy THIẾU kernel -> `dung_duoc()` = [] (tự tắt, không nổ)", False,
            f"NÉM {type(e).__name__}: {e}")
    finally:
        GPU.duong_kernel = goc                   # type: ignore[assignment]
        GPU._CO.pop("opencl", None)

    # GIẢ máy nhân viên: ffmpeg không chạy được -> tự tắt, KHÔNG ném
    goc_ff = GPU._ffmpeg
    try:
        GPU._ffmpeg = lambda: str(_SB / "khong_co_ffmpeg.exe")  # type: ignore
        GPU._CO.clear()
        bao("ffmpeg HỎNG -> `co_opencl()`/`co_libplacebo()` = False, không nổ",
            (GPU.co_opencl(do_lai=True) is False)
            and (GPU.co_libplacebo(do_lai=True) is False), "cả hai False")
    except Exception as e:                                   # noqa: BLE001
        bao("ffmpeg HỎNG -> `co_opencl()`/`co_libplacebo()` = False, không nổ",
            False, f"NÉM {type(e).__name__}: {e}")
    finally:
        GPU._ffmpeg = goc_ff                     # type: ignore[assignment]
        GPU._CO.clear()

    # Máy NÀY có OpenCL thì render thật 1 chuyển cảnh và ĐẾM KHUNG (0 khung và
    # khung vô tận đều là bệnh đã gặp; `-frames:v` trong lệnh là phanh cứng).
    if GPU.co_opencl(do_lai=True):
        d, fps = 0.30, 30
        vao = []
        for i, mau in enumerate(("testsrc2", "smptebars")):
            p = _SB / f"gpu_in{i}.mp4"
            subprocess.run(
                [FF, "-y", "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
                 f"{mau}=s=320x180:r={fps}:d={d}", "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", str(p)],
                capture_output=True, timeout=120, creationflags=_NOWIN)
            vao.append(str(p))
        out = _SB / "gpu_out.mp4"
        kieu = next(iter(GPU.KHO_GPU))
        r = subprocess.run(
            [FF, "-y", "-hide_banner", "-v", "error",
             *GPU.lenh_vung_chong(vao[0], vao[1], str(out), kieu, d, fps=fps)],
            capture_output=True, text=True, errors="replace", timeout=180,
            creationflags=_NOWIN)
        n = int(so_khung(out)) if out.exists() else 0
        ky = int(round(d * fps))
        bao(f"render thật `{kieu}` ra ĐÚNG {ky} khung (không 0, không vô tận)",
            r.returncode == 0 and n == ky,
            f"rc={r.returncode} · {n} khung (kỳ vọng {ky})")
    else:
        bao("máy này không có OpenCL -> nhóm GPU tự tắt (đúng thiết kế)",
            GPU.dung_duoc(do_lai=True) == [], "dung_duoc() = []")


def main() -> int:
    _test_guard.tu_kiem()
    print("=" * 74)
    print("CỔNG 36 — CHUYỂN CẢNH CHỖ GHÉP ĐOẠN (xfade) + CỬA CHỜ ffmpeg")
    print("=" * 74)
    print(f"[ffmpeg] {FF}")
    print(f"[nhân] {os.cpu_count()} · encoder {fu.detect_encoder()} · "
          f"trần ffmpeg song song {fu.so_ffmpeg_song_song()} · "
          f"giải mã {fu.decode_threads()} luồng")

    ca_cua_cho()
    ca_ham_thuan()
    ca_gpu_fallback()

    vids = [p for p in (THUNG.rglob("*.mp4") if THUNG.exists() else [])
            if p.stat().st_size > 5_000_000
            and any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" for c in str(p))]
    if not vids:
        bao("có video Nhật THẬT để render", False,
            f"không thấy .mp4 nào trong {THUNG}")
    else:
        src = vids[0]
        print(f"\n[nguồn] {src.name[:64]}")
        # MỐC CẮT PHẢI Ở CẢNH SÁNG. Đo thật nguồn này: giây 20 sáng TB chỉ
        # **3,3/255** (gần ĐEN) -> ca "đếm pixel ở chỗ nối" ra 0,69% và FAIL OAN
        # vì cả 2 bản đều đen thui, không phải vì chuyển cảnh không xảy ra.
        # Các mốc dùng dưới đây đo được 71-90/255. hook-first = NGƯỢC thời gian.
        ca_render(src, "hookfirst2", [(200.0, 210.0), (100.0, 110.0)], "vua")
        ca_render(src, "baDoan", [(200.0, 208.0), (100.0, 108.0),
                                  (300.0, 306.0)], "manh")
        ca_phu_de(src, [(200.0, 208.0), (100.0, 108.0), (300.0, 306.0)], "vua")
        ca_vfr(src)
        ca_kieu_sai(src)
        ca_bat_bien(src)

    print("\n" + "=" * 74)
    print(f"KẾT QUẢ: {len(_OK)} OK · {len(_LOI)} FAIL")
    for x in _LOI:
        print("  FAIL " + x)
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
