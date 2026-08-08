# -*- coding: utf-8 -*-
r"""CỔNG 37 — CA BIÊN CỦA ĐƯỜNG XUẤT (có chuyển cảnh + hiệu ứng).

Chạy: .venv\\Scripts\\python _test_ca_bien_xuat.py

Cổng 36 canh chuyển cảnh chạy ĐÚNG ở ca thường. Cổng này đi tìm chỗ nó VỠ ở ca
XẤU, vì anh Hùng chạy 200-300 kênh nên ca xấu chắc chắn sẽ gặp:

  1. VIDEO KHÔNG CÓ TIẾNG — `_graph_xfade` chỉ thêm `acrossfade` khi `co_tieng`.
     Sai một nhánh là clip câm nổ giữa dây chuyền.
  2. HUỶ GIỮA LÚC XUẤT — phải ném `CanceledError`, **dọn sạch mảnh `_seg_*`**,
     **không để lại file đích dở**, và **không bỏ lại ffmpeg mồ côi**.
  3. KHÔNG GHI ĐƯỢC ĐĨA (mô phỏng HẾT ĐĨA) — phải FAIL TO, không để file 0 byte
     mang tên thành phẩm, không rò rác.
  4. MÁY NHÂN VIÊN — không NVENC / không frei0r / không OpenCL: vẫn xuất bình
     thường, nhóm hỏng TỰ TẮT chứ không nổ lỗi.
  5. CLIP 1 ĐOẠN + MỐC NGOÀI PHIM trong khi chuyển cảnh đang BẬT.

**ĐẾM TIẾN TRÌNH ffmpeg PHẢI THEO `p.name()`, KHÔNG THEO cmdline.** Lọc theo
cmdline sẽ đếm CHÍNH LỆNH KIỂM (mã nguồn có chữ 'ffmpeg') -> luôn báo "đang
chạy". Bẫy này đã báo sai cho anh Hùng 4 lần.

Đo `%TEMP%` TRƯỚC/SAU từng ca: rác `_seg_*.mkv` là thứ đã làm ổ C đầy 100% hôm
31/07 (1,71 GB phải dọn tay).
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

_SB = Path(tempfile.gettempdir()) / f"test_cabien_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

import psutil  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x08000000
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
TMP = Path(tempfile.gettempdir())

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def dem_ffmpeg() -> int:
    """Số tiến trình ffmpeg đang sống — theo TÊN TIẾN TRÌNH, KHÔNG theo cmdline."""
    n = 0
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() in ("ffmpeg.exe", "ffmpeg"):
                n += 1
        except psutil.Error:
            pass
    return n


def rac_seg() -> set:
    return {p.name for p in TMP.glob("_seg_*")}


def dai(p) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       text=True, creationflags=_NOWIN, timeout=60)
    try:
        return float((r.stdout or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


def co_tieng(p) -> bool:
    r = subprocess.run([FP, "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                        str(p)], capture_output=True, text=True,
                       creationflags=_NOWIN, timeout=60)
    return "audio" in (r.stdout or "")


def dung_nguon(ten: str, giay: float, tieng: bool) -> Path:
    """Nguồn thử tự sinh (lavfi) — không phụ thuộc file trên máy."""
    p = _SB / ten
    c = [FF, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=30:d={giay:g}"]
    if tieng:
        c += ["-f", "lavfi", "-i", f"sine=f=440:r=48000:d={giay:g}"]
    c += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
          "-pix_fmt", "yuv420p"]
    if tieng:
        c += ["-c:a", "aac", "-b:a", "96k", "-shortest"]
    c += [str(p)]
    subprocess.run(c, capture_output=True, timeout=300, creationflags=_NOWIN)
    return p


# =====================================================================
def ca_khong_tieng() -> None:
    print("\n[CA 1] VIDEO KHÔNG CÓ TIẾNG + chuyển cảnh BẬT")
    src = dung_nguon("cam.mp4", 30.0, tieng=False)
    bao("dựng được nguồn CÂM", src.exists() and not co_tieng(src),
        f"{src.stat().st_size // 1024} KB · có tiếng = {co_tieng(src)}")
    segs = [(18.0, 24.0), (2.0, 8.0)]           # NGƯỢC thời gian (hook-first)
    truoc = rac_seg()
    for muc in ("tat", "vua"):
        out = _SB / f"cam_{muc}.mp4"
        try:
            fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                                  out_w=540, out_h=960, encoder="libx264",
                                  chuyen_canh=muc)
            e = ""
        except Exception as ex:                              # noqa: BLE001
            e = f"{type(ex).__name__}: {ex}"
        d = dai(out) if out.exists() else -1.0
        bao(f"clip CÂM mức '{muc}' xuất được, dài đúng 12s",
            not e and abs(d - 12.0) < 0.15, f"lỗi={e[:80] or 'không'} · dài {d:.3f}s")
    bao("clip CÂM: KHÔNG rò mảnh `_seg_*`", not (rac_seg() - truoc),
        f"sót {sorted(rac_seg() - truoc)[:4]}")


def ca_huy_giua_chung() -> None:
    """HUỶ giữa lúc xuất: ném CanceledError + dọn sạch + không rò tiến trình."""
    print("\n[CA 2] HUỶ GIỮA LÚC XUẤT")
    from app.queue import worker as W
    src = dung_nguon("huy.mp4", 60.0, tieng=True)
    segs = [(40.0, 55.0), (5.0, 20.0), (25.0, 35.0)]
    out = _SB / "huy_out.mp4"
    truoc_rac, truoc_ff = rac_seg(), dem_ffmpeg()

    goc = W.current_job_canceled
    co_huy = threading.Event()
    W.current_job_canceled = lambda: co_huy.is_set()   # type: ignore[assignment]
    ket: dict = {}

    def chay() -> None:
        try:
            fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                                  out_w=540, out_h=960, encoder="libx264",
                                  chuyen_canh="vua")
            ket["e"] = None
        except Exception as ex:                              # noqa: BLE001
            ket["e"] = ex

    t = threading.Thread(target=chay, daemon=True)
    t.start()
    # ĐỢI CHO TỚI KHI THẤY ffmpeg THẬT rồi mới bấm Huỷ — KHÔNG lấy MỘT mẫu ở
    # giây 1,2.
    # LỖI CỦA CHÍNH CỔNG NÀY (lượt kiểm độc lập 08/08/2026): bản cũ
    # `time.sleep(1.2)` rồi đếm 1 phát. Máy anh Hùng LUÔN có việc chạy nền, và
    # `export_canvas_clip` phải XIN CHỖ ở cửa chờ ffmpeg trước khi spawn — nên
    # ở giây 1,2 lượt xuất có thể vẫn đang XẾP HÀNG. Đo thật trong lượt chạy cả
    # bộ: `0 tiến trình (nền 0)` -> cổng ĐỎ trong khi HUỶ hoàn toàn đúng (4 ca
    # còn lại đều OK); chạy lại một mình thì `1 tiến trình` -> XANH. Cổng nhấp
    # nháy theo tải máy là cổng không tin được.
    dang, _t0 = 0, time.time()
    while time.time() - _t0 < 30.0:
        dang = max(dang, dem_ffmpeg())
        if dang > truoc_ff:
            break
        time.sleep(0.2)
    time.sleep(0.4)                    # để nó vào giữa pha 1 rồi mới huỷ
    co_huy.set()                       # BẤM HUỶ
    t.join(timeout=90)
    W.current_job_canceled = goc       # type: ignore[assignment]

    bao("lúc huỷ có ffmpeg đang chạy thật (phép đo có ý nghĩa)",
        dang > truoc_ff, f"{dang} tiến trình (nền {truoc_ff})")
    e = ket.get("e")
    bao("huỷ -> ném CanceledError (không trả về êm như đã xuất xong)",
        e is not None and type(e).__name__ == "CanceledError",
        f"{type(e).__name__ if e else 'KHÔNG NÉM GÌ'}")
    bao("huỷ -> KHÔNG để lại file đích dở",
        not out.exists(), "không có file" if not out.exists()
        else f"còn {out.stat().st_size} byte")
    sot = sorted(rac_seg() - truoc_rac)
    mb = sum((TMP / s).stat().st_size for s in sot if (TMP / s).exists()) / 1e6
    bao("huỷ -> DỌN SẠCH mảnh `_seg_*` (không phình %TEMP%)", not sot,
        f"sót {len(sot)} file / {mb:.1f} MB: {sot[:4]}" if sot else "0 file sót")
    # rò tiến trình: đợi tối đa 5s cho tiến trình chết hẳn rồi ĐẾM THEO TÊN
    for _ in range(25):
        if dem_ffmpeg() <= truoc_ff:
            break
        time.sleep(0.2)
    bao("huỷ -> KHÔNG bỏ lại ffmpeg mồ côi", dem_ffmpeg() <= truoc_ff,
        f"trước {truoc_ff} · sau {dem_ffmpeg()}")


def ca_khong_ghi_duoc() -> None:
    """Mô phỏng HẾT ĐĨA: đích không ghi được -> phải FAIL TO, dọn sạch."""
    print("\n[CA 3] KHÔNG GHI ĐƯỢC ĐĨA (mô phỏng hết đĩa)")
    src = dung_nguon("dia.mp4", 30.0, tieng=True)
    segs = [(18.0, 24.0), (2.0, 8.0)]
    # đích là 1 THƯ MỤC đang tồn tại -> ffmpeg không mở nổi để ghi, đúng kiểu
    # "không ghi nổi đích" mà hết đĩa cũng rơi vào (rc != 0 + log có 'Error').
    xau = _SB / "la_thu_muc.mp4"
    xau.mkdir(exist_ok=True)
    truoc = rac_seg()
    try:
        fu.export_canvas_clip(src, xau, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="vua")
        e = None
    except Exception as ex:                                  # noqa: BLE001
        e = ex
    bao("ghi đích lỗi -> NÉM LỖI, không im lặng báo xong", e is not None,
        f"{type(e).__name__}: {str(e)[:110]}" if e else "KHÔNG NÉM GÌ")
    bao("ghi đích lỗi -> lời lỗi có log ffmpeg để anh Hùng đọc được",
        bool(e) and len(str(e)) > 40, f"{len(str(e or ''))} ký tự")
    sot = sorted(rac_seg() - truoc)
    bao("ghi đích lỗi -> DỌN SẠCH mảnh `_seg_*`", not sot,
        f"sót {len(sot)}: {sot[:4]}" if sot else "0 file sót")


def ca_may_nhan_vien() -> None:
    """Máy nhân viên: thiếu NVENC / frei0r / OpenCL -> vẫn chạy, tự tắt phần thiếu."""
    print("\n[CA 4] MÁY NHÂN VIÊN: thiếu NVENC + frei0r + OpenCL")
    from app.core import hieu_ung as HU
    from app.core import hieu_ung_gpu as GPU

    # (a) thiếu frei0r -> kho co lại nhưng KHÔNG rỗng, KHÔNG nổ.
    # LƯU Ý PHÉP ĐO: `thu_muc_frei0r()` trả **Path**, stub phải trả Path chứ
    # không phải str — bản đầu của cổng này trả "" và ra `AttributeError: 'str'
    # object has no attribute 'is_dir'`, suýt báo nhầm là lỗi app.
    # Phải xoá cả 2 chỗ NHỚ (`_F0R_OK`, `_MOD_CACHE`), nếu không hàm trả kết quả
    # của lần đo TRƯỚC và ca này PASS OAN.
    goc_tm, goc_ok = HU.thu_muc_frei0r, HU._F0R_OK
    goc_mod = dict(HU._MOD_CACHE)
    tong_truoc = len(HU.dung_duoc(co_font=True))
    try:
        HU.thu_muc_frei0r = lambda: _SB / "khong_co_frei0r"   # type: ignore
        HU._F0R_OK = None
        HU._MOD_CACHE.clear()
        ds = HU.dung_duoc(co_font=True)
        bao("thiếu frei0r -> kho hiệu ứng CO LẠI mà vẫn dùng được (không nổ)",
            isinstance(ds, list) and 0 < len(ds) < tong_truoc,
            f"{tong_truoc} -> {len(ds)} hiệu ứng (chỉ còn nhóm thuần ffmpeg)")
        bao("thiếu frei0r -> `co_frei0r()` False + nêu được LÝ DO",
            HU.co_frei0r() is False and bool(HU.ly_do_khong_co_frei0r()),
            HU.ly_do_khong_co_frei0r()[:90])
    except Exception as ex:                                  # noqa: BLE001
        bao("thiếu frei0r -> kho hiệu ứng CO LẠI mà vẫn dùng được (không nổ)",
            False, f"NÉM {type(ex).__name__}: {ex}")
    finally:
        HU.thu_muc_frei0r = goc_tm                # type: ignore[assignment]
        HU._F0R_OK = goc_ok
        HU._MOD_CACHE.clear()
        HU._MOD_CACHE.update(goc_mod)

    # (b) thiếu OpenCL -> nhóm GPU tắt hẳn
    goc_k = GPU.duong_kernel
    try:
        GPU.duong_kernel = lambda: ""             # type: ignore[assignment]
        GPU._CO.pop("opencl", None)
        bao("thiếu OpenCL -> nhóm chuyển cảnh GPU tắt hẳn (không nổ)",
            GPU.dung_duoc(do_lai=True) == [], "dung_duoc() = []")
    finally:
        GPU.duong_kernel = goc_k                  # type: ignore[assignment]
        GPU._CO.pop("opencl", None)

    # (c) KHÔNG NVENC: ép libx264 -> xuất thật, có chuyển cảnh + hiệu ứng
    src = dung_nguon("nv.mp4", 30.0, tieng=True)
    out = _SB / "nhanvien.mp4"
    log: list = []
    truoc = rac_seg()
    try:
        fu.export_canvas_clip(src, out, [(18.0, 24.0), (2.0, 8.0)],
                              (0.5, 0.45, 0.98), bg="blur", out_w=540,
                              out_h=960, encoder="libx264", chuyen_canh="vua",
                              hieu_ung="vua", hieu_ung_log=log)
        e = ""
    except Exception as ex:                                  # noqa: BLE001
        e = f"{type(ex).__name__}: {ex}"
    d = dai(out) if out.exists() else -1.0
    bao("KHÔNG NVENC (libx264) + chuyển cảnh + hiệu ứng -> vẫn xuất đúng 12s",
        not e and abs(d - 12.0) < 0.15,
        f"lỗi={e[:90] or 'không'} · dài {d:.3f}s · {len(log)} điểm hiệu ứng")
    bao("máy nhân viên: KHÔNG rò mảnh `_seg_*`", not (rac_seg() - truoc),
        f"sót {sorted(rac_seg() - truoc)[:4]}")
    # trần cửa chờ trên máy yếu phải >= 1 (không được ra 0 = treo vĩnh viễn)
    bao("cửa chờ trên máy yếu vẫn >= 1 chỗ (không tự khoá chết)",
        fu.so_ffmpeg_song_song() >= 1, f"{fu.so_ffmpeg_song_song()} chỗ")


def ca_mot_doan_va_ngoai_phim() -> None:
    print("\n[CA 5] CLIP 1 ĐOẠN + MỐC NGOÀI PHIM, chuyển cảnh đang BẬT")
    src = dung_nguon("ngan.mp4", 20.0, tieng=True)
    truoc = rac_seg()
    out = _SB / "motdoan.mp4"
    try:
        fu.export_canvas_clip(src, out, [(2.0, 12.0)], (0.5, 0.45, 0.98),
                              bg="blur", out_w=540, out_h=960,
                              encoder="libx264", chuyen_canh="manh")
        e = ""
    except Exception as ex:                                  # noqa: BLE001
        e = f"{type(ex).__name__}: {ex}"
    d = dai(out) if out.exists() else -1.0
    bao("1 đoạn + chuyển cảnh BẬT -> xuất bình thường (không chỗ nối nào)",
        not e and abs(d - 10.0) < 0.15, f"lỗi={e[:80] or 'không'} · dài {d:.3f}s")

    # mốc VƯỢT độ dài thật: 2 đoạn, đoạn cuối chạm mép phim -> phần bù xfade
    # phải TỰ THU NGẮN chứ không đòi phim không có (bài học `_bu_xfade`).
    out2 = _SB / "ngoaiphim.mp4"
    segs = [(12.0, 19.9), (1.0, 6.0)]
    try:
        fu.export_canvas_clip(src, out2, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="manh")
        e2 = ""
    except Exception as ex:                                  # noqa: BLE001
        e2 = f"{type(ex).__name__}: {ex}"
    d2 = dai(out2) if out2.exists() else -1.0
    bao("đoạn CHẠM MÉP phim + chuyển cảnh -> vẫn ra đúng 12,9s, không nổ",
        not e2 and abs(d2 - 12.9) < 0.25,
        f"lỗi={e2[:80] or 'không'} · dài {d2:.3f}s (kỳ vọng 12,9s)")
    bao("2 ca trên: KHÔNG rò mảnh `_seg_*`", not (rac_seg() - truoc),
        f"sót {sorted(rac_seg() - truoc)[:4]}")


def ca_doan_ke_ngan_hon_chuyen_canh() -> None:
    """ĐOẠN KẾ NGẮN HƠN thời lượng chuyển cảnh -> tiếng dài hơn hình.

    LỖI THẬT tìm được 08/08/2026 khi rà lại (đang chạy trong sản xuất, mức
    'vua'/'manh'): `xfade` (hình) và `acrossfade` (tiếng) xử lý ca "đoạn B ngắn
    hơn `d`" KHÁC NHAU — hình ra `a+b`, tiếng ra `a+d`. Đo trước khi sửa:
    B 0,20s + d 0,40s -> lệch **200 ms** (mốc cho phép 80 ms).

    App TỰ ĐẨY MÌNH VÀO ca này: `_loai_cho_noi` gọi chỗ nối là 'chot' đúng khi
    đoạn kế < 2,5s, mà 'chot' lại có `d` DÀI NHẤT; `_cat_theo_do_dai_that` cho
    đoạn ngắn tới 0,30s (Part cuối bị kẹp vào mép phim).
    """
    print("\n[CA 6] ĐOẠN KẾ NGẮN HƠN thời lượng chuyển cảnh")
    # (a) hàm thuần: `d` phải bị kẹp về <= độ dài đoạn kế
    for muc, ke, tran in (("manh", 0.20, 0.20), ("manh", 0.30, 0.30),
                          ("vua", 0.25, 0.25), ("nhe", 3.0, 0.40)):
        segs = [(10.0, 20.0), (30.0, 30.0 + ke)]
        xf = fu.chon_chuyen_canh(segs, muc)
        bu = fu._bu_xfade(segs, xf, 600.0)
        bao(f"mức '{muc}', đoạn kế {ke}s -> phần bù <= {tran}s",
            bool(bu) and bu[0] <= tran + 1e-6,
            f"kiểu {xf[0][0]} d={xf[0][1]} -> bù {bu[0]}")

    # (b) XUẤT THẬT: đoạn cuối 0,30s, mức 'manh' -> lệch tiếng-hình < 80ms
    src = dung_nguon("ngan_ke.mp4", 40.0, tieng=True)
    out = _SB / "doan_ke_ngan.mp4"
    # đoạn kế 0,31s — vừa TRÊN sàn 0,30s của `_cat_theo_do_dai_that`, và NGẮN
    # hơn d=0,40s của mức 'manh'. (Đúng 0,30s thì sai số dấu phẩy động làm
    # `e-s = 0,2999...` < 0,30 nên đoạn bị LOẠI, ca thử mất ý nghĩa.)
    segs = [(25.0, 33.0), (2.0, 2.31)]
    truoc = rac_seg()
    try:
        fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="manh")
        e = ""
    except Exception as ex:                                  # noqa: BLE001
        e = f"{type(ex).__name__}: {ex}"
    dv = _dai_luong(out, "v:0") if out.exists() else -1.0
    da = _dai_luong(out, "a:0") if out.exists() else -1.0
    bao("xuất được clip có đoạn kế 0,31s ở mức 'manh'", not e, e[:100] or "ok")
    bao("lệch TIẾNG-HÌNH < 80ms (trước khi sửa: 90-200ms)",
        dv > 0 and da > 0 and abs(dv - da) * 1000 < 80,
        f"hình {dv:.3f}s · tiếng {da:.3f}s · lệch {abs(dv - da) * 1000:.0f}ms")
    bao("độ dài clip = tổng đoạn (8,31s), chuyển cảnh không ăn bớt",
        dv > 0 and abs(dv - 8.31) < 0.08, f"{dv:.3f}s (kỳ vọng 8,310s)")
    bao("ca đoạn kế ngắn: KHÔNG rò mảnh `_seg_*`", not (rac_seg() - truoc),
        f"sót {sorted(rac_seg() - truoc)[:4]}")


def ca_lenh_do_phai_siet_luong() -> None:
    """MỌI lệnh ffmpeg NGOÀI CỬA CHỜ đều phải tự siết luồng.

    LỖI THẬT (tổng rà soát 08/08/2026): lượt e2e cả dây chuyền đo **203 luồng
    ffmpeg = 8,46× số nhân**, phá mốc "≤ 2× nhân" của anh Hùng. Cửa chờ
    (`_xin_cho_ffmpeg`) chỉ quản đường XUẤT; 3 lệnh ĐO của pha PHÂN TÍCH
    (`chon_doan.nang_luong`, `chon_doan.chuyen_dong`, `hieu_ung.do_nhip`) **cố ý
    đứng ngoài cửa chờ** — lệnh đo mà xin chỗ sẽ tự khoá lẫn với lệnh xuất đang
    giữ chỗ. Nên chúng PHẢI tự siết. `chuyen_dong` khi đó không núm nào: **một
    mình 70 luồng (2,92× nhân)**, ngốn ~13,5 nhân, cướp CPU của làn xuất.

    Ca này QUÉT TĨNH mã nguồn: lệnh nào có `-f null` (tức lệnh đo) mà thiếu
    `-threads` là FAIL. Rẻ, chạy 0,0s, và bắt đúng lúc ai đó thêm lệnh đo mới.
    """
    print("\n[CA 7] lệnh ĐO (ngoài cửa chờ) phải tự siết luồng")
    can = {
        "chon_doan.nang_luong": (REPO / "app" / "ai" / "chon_doan.py",
                                 "def nang_luong"),
        "chon_doan.chuyen_dong": (REPO / "app" / "ai" / "chon_doan.py",
                                  "def chuyen_dong"),
        "hieu_ung.do_nhip": (REPO / "app" / "core" / "hieu_ung.py",
                             "def do_nhip"),
        # TÁCH TIẾNG cho chép lời: đo được **132 luồng = 5,50× nhân** — đỉnh
        # lớn nhất của cả lượt dây chuyền, còn hơn cả lệnh XUẤT (81).
        "ffmpeg_utils.extract_audio_wav_why":
            (REPO / "app" / "core" / "ffmpeg_utils.py",
             "def extract_audio_wav_why"),
    }
    for ten, (f, moc) in can.items():
        src = f.read_text(encoding="utf-8", errors="replace")
        i = src.find(moc)
        than = src[i:i + 3500] if i >= 0 else ""
        co_threads = "-threads" in than or "_num_luong()" in than
        bao(f"{ten}: lệnh NGOÀI cửa chờ có siết luồng giải mã",
            bool(than) and co_threads,
            f"tìm thấy hàm={bool(than)} · có `-threads`={co_threads}")
        # `-threads` PHẢI đứng TRƯỚC `-i` (sau `-i` là luồng ENCODE — đặt sai
        # chỗ thì ffmpeg IM LẶNG, không báo lỗi, luồng giải mã vẫn mặc định 0).
        # BẪY CỦA CHÍNH PHÉP ĐO NÀY (đã FAIL OAN 1 lần): docstring của
        # `do_nhip` có ví dụ `["-ss", s, "-t", e-s, "-i", <nguồn>]` nên `"-i"`
        # xuất hiện ở vị trí 682 — TRƯỚC lệnh thật. Phải CẮT BỎ DOCSTRING rồi
        # mới so vị trí.
        # BẪY CỦA CHÍNH PHÉP ĐO NÀY — đã FAIL OAN 2 lần, ghi lại cho rõ:
        #  (a) docstring `do_nhip` có ví dụ `["-ss", s, "-t", …, "-i", <nguồn>]`
        #      -> `"-i"` xuất hiện TRƯỚC lệnh thật;
        #  (b) `do_nhip` gán `vao = [… or ["-i", str(path)]]` ở dòng RIÊNG rồi
        #      mới nhét `*vao` vào lệnh -> so vị trí trên CẢ THÂN HÀM vẫn sai.
        # => chỉ so bên trong ĐÚNG DANH SÁCH LỆNH chứa `-threads`.
        _lenh = ""
        _p = than.find('"-threads"')
        if _p > 0:
            _mo = than.rfind("[", 0, _p)       # đầu list literal của lệnh
            _dong = than.find("]", _p)         # cuối list literal
            if _mo >= 0 and _dong > _mo:
                _lenh = than[_mo:_dong]
        i_t, i_i = _lenh.find('"-threads"'), _lenh.find('"-i"')
        bao(f"{ten}: `-threads` đứng TRƯỚC `-i` trong CHÍNH lệnh",
            ("_num_luong()" in than and '"-threads"' not in than)
            or (i_t >= 0 and (i_i < 0 or i_t < i_i)),
            f"trong lệnh: -threads={i_t} · -i={i_i} "
            f"({'không có -i rời, dùng *vao' if i_i < 0 else 'có -i rời'})")

    # ĐO THẬT: chạy `chuyen_dong` trên nguồn tự sinh, đếm đỉnh luồng
    src = dung_nguon("do_luong.mp4", 12.0, True)
    from app.ai import chon_doan as CD
    dinh = [0]
    stop = threading.Event()

    def _soi() -> None:
        me = psutil.Process()
        while not stop.is_set():
            t = 0
            try:
                for c in me.children(recursive=True):
                    try:
                        if "ffmpeg" in (c.name() or "").lower():
                            t += c.num_threads()   # theo TÊN, không theo cmdline
                    except psutil.Error:
                        pass
            except psutil.Error:
                pass
            dinh[0] = max(dinh[0], t)
            time.sleep(0.03)

    th = threading.Thread(target=_soi, daemon=True)
    th.start()
    CD.chuyen_dong(str(src), FF)
    CD.nang_luong(str(src), FF)
    stop.set()
    th.join(timeout=2)
    nhan_ = os.cpu_count() or 1
    bao("ĐO THẬT: 1 lệnh đo ≤ 2× số nhân (trước khi sửa: 70 = 2,92×)",
        0 < dinh[0] <= 2 * nhan_,
        f"đỉnh {dinh[0]} luồng = {dinh[0]/nhan_:.2f}× nhân (trần {2*nhan_})")


def _dai_luong(p, loai: str) -> float:
    """Độ dài LUỒNG hình/tiếng (giây) — ĐẾM THẬT, không đọc tag `duration`.

    LỖI ĐO đã sập 1 lần: Matroska/mp4 có thể KHÔNG ghi `stream=duration` cho
    từng luồng -> ffprobe trả rỗng -> hàm trả -1 ở MỌI ca và bảng ra "lệch 0ms"
    cho tất cả, trông y như không có lỗi.
    """
    r = subprocess.run([FP, "-v", "error", "-select_streams", loai,
                        "-show_entries", "packet=pts_time,duration_time",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       text=True, creationflags=_NOWIN, timeout=120)
    dong = [x for x in (r.stdout or "").strip().splitlines() if "," in x]
    if not dong:
        return -1.0
    try:
        a, b = dong[-1].split(",")[:2]
        return float(a) + float(b)
    except ValueError:
        return -1.0


def main() -> int:
    _test_guard.tu_kiem()
    print("=" * 74)
    print("CỔNG 37 — CA BIÊN CỦA ĐƯỜNG XUẤT (chuyển cảnh + hiệu ứng)")
    print("=" * 74)
    rac0, ff0 = rac_seg(), dem_ffmpeg()
    print(f"[máy] {os.cpu_count()} nhân · encoder {fu.detect_encoder()} · "
          f"ffmpeg đang chạy {ff0} · rác `_seg_*` trong %TEMP% {len(rac0)}")

    ca_khong_tieng()
    ca_huy_giua_chung()
    ca_khong_ghi_duoc()
    ca_may_nhan_vien()
    ca_mot_doan_va_ngoai_phim()
    ca_doan_ke_ngan_hon_chuyen_canh()
    ca_lenh_do_phai_siet_luong()

    print("\n[TỔNG] rò rác đĩa + rò tiến trình sau TOÀN BỘ cổng")
    sot = sorted(rac_seg() - rac0)
    mb = sum((TMP / s).stat().st_size for s in sot if (TMP / s).exists()) / 1e6
    bao("TỔNG: %TEMP% không phình thêm mảnh `_seg_*`", not sot,
        f"sót {len(sot)} file / {mb:.1f} MB" if sot else "0 file sót")
    for _ in range(25):
        if dem_ffmpeg() <= ff0:
            break
        time.sleep(0.2)
    bao("TỔNG: không bỏ lại ffmpeg mồ côi", dem_ffmpeg() <= ff0,
        f"trước {ff0} · sau {dem_ffmpeg()}")

    print("\n" + "=" * 74)
    print(f"KẾT QUẢ: {len(_OK)} OK · {len(_LOI)} FAIL")
    for x in _LOI:
        print("  FAIL " + x)
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
