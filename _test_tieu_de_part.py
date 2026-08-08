# -*- coding: utf-8 -*-
r"""CỔNG 42 — HỘP TIÊU ĐỀ + HUY HIỆU "PART N" PHẢI CÓ THẬT TRONG FILE XUẤT.

Chạy: .venv\Scripts\python _test_tieu_de_part.py
Env : BQ_TEST=1  PYTHONIOENCODING=utf-8  BQ_FFMPEG_SLOTS=1

LỖI THẬT anh Hùng báo 08/08/2026 — "tôi có cái phần tiêu đề đỏ part các kiểu
kia mà xuất k có": xem trước ở Chỉnh mẫu có hộp đỏ tiêu đề + huy hiệu đỏ
"Part 1", file clip xuất ra CHỈ CÒN PHỤ ĐỀ.

ĐO TRÊN CHÍNH FILE CỦA ANH HÙNG (không suy đoán) — video 'GOING BACK TO OUR
OLD HOUSE', mẫu «test AI», tỉ lệ điểm ảnh ĐỎ:
    Part 3  xuất 17:44  (TRƯỚC khi tắt app)  -> 11,584 %   CÓ hộp đỏ
    ===== app mở lại 17:59:29 (logs/crash_native.txt) =====
    Part 2  xuất 18:01  (chạy LẠI sau đó)    ->  0,000 %   MẤT
    Part 1  xuất 18:03  (chạy LẠI sau đó)    ->  0,000 %   MẤT

GỐC — 3 dòng ở 3 file cộng lại:
  1. `m1_highlight.export_clip`  `except CanceledError: _cleanup_files(... ovl_tmp)`
     -> XOÁ ảnh lớp chữ `_ovl_<cid>.png`.
  2. `worker.WorkerPool.stop()`  "UPDATE jobs SET status='pending' ...
     WHERE status='running'" -> job ĐÓ SẼ CHẠY LẠI khi mở app.
     (1) coi tắt-app là "huỷ hẳn", (2) coi tắt-app là "tạm dừng" — mâu thuẫn.
  3. `ffmpeg_utils.export_canvas_clip`
     `use_png = bool(overlay_png and os.path.exists(overlay_png))`
     -> file ảnh không còn thì BỎ overlay **IM LẶNG**: rc=0, đủ khung, file mp4
     hoàn hảo, không một dòng báo lỗi. Đây là chỗ "nuốt" cuối cùng.

CÁCH ĐO CỦA CỔNG NÀY — **BẰNG SỐ TRÊN KHUNG HÌNH**, không kiểm "lệnh ffmpeg có
chữ drawtext" (lệnh có mà hình không ra thì vẫn PASS OAN):
  · nguồn là màu phẳng KHÔNG ĐỎ (0x1E6F5C) -> mọi điểm ảnh đỏ trên khung chỉ
    có thể đến từ lớp chữ;
  · trích khung THẬT bằng ffmpeg ở giây có tiêu đề rồi ĐẾM điểm ảnh đỏ trong
    DẢI hộp tiêu đề (trên) và DẢI huy hiệu Part (dưới), so bản CÓ / KHÔNG.
  · luôn `ffprobe -count_frames` (bẫy rc=0 mà 0 khung).

1 ffmpeg tại một thời điểm (BQ_FFMPEG_SLOTS=1), video 6 giây.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"tieude_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "settings.ini"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BQ_FFMPEG_SLOTS"] = "1"          # LUẬT SỐ 1: 1 ffmpeg một lúc

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])

from app.core.ffmpeg_utils import export_canvas_clip  # noqa: E402
from app.database.db import db  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402
from app.queue.worker import CanceledError  # noqa: E402
from app.ui import editor, fonts  # noqa: E402
from config import settings  # noqa: E402

fonts.load_fonts()

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH

# KHUNG XUẤT của cổng này. Ảnh lớp chữ PHẢI vẽ ĐÚNG cỡ này: `export_canvas_clip`
# chồng ảnh bằng `overlay=0:0` (KHÔNG co giãn) nên ảnh to hơn khung là bị CẮT
# mất phần dưới — đúng bẫy đã làm bản đầu của cổng này FAIL OAN ở ca "tiêu đề
# rỗng": huy hiệu Part ở ny=0,77 của ảnh 1080x1920 rơi ra ngoài khung 540x960.
# (App thật luôn dùng 1080x1920 cho CẢ HAI — `_render_png` vẽ 1080x1920 và
# `enqueue_export` mặc định out_w/out_h = 1080x1920 — nên khớp.)
OUT_W, OUT_H = 540, 960

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK  ' if ok else 'FAIL'}] {ten}" + (f": {so}" if so else ""))


# ── mẫu ĐÚNG như anh Hùng đang dùng (đọc từ DB thật, mẫu 'tiêu đề AI') ──
# hộp ĐỎ #FF0000 cho cả lớp {title} (trên) lẫn lớp Part (dưới).
LOP = [
    {"text": "Part {n}", "size": 0.03, "font": "Be Vietnam đậm",
     "color": "#FFFFFF", "outline": 0.12, "outline_color": "#000000",
     "bg": True, "bg_color": "#FF0000", "radius": 30, "is_part": True,
     "padx": 0.8333, "pady": 0.8333, "bg_alpha": 0.75, "nx": 0.5, "ny": 0.7712},
    {"text": "{title}", "size": 0.03, "font": "Be Vietnam đậm",
     "color": "#FFFFFF", "outline": 0.12, "outline_color": "#000000",
     "bg": True, "bg_color": "#FF0000", "radius": 100, "is_part": False,
     "padx": 0.8333, "pady": 0.8333, "bg_alpha": 0.75, "nx": 0.5, "ny": 0.2583},
]


def lam_nguon(p: Path, giay: float = 6.0) -> Path:
    """Nguồn MÀU PHẲNG KHÔNG ĐỎ -> điểm ảnh đỏ trên khung chỉ có thể là lớp chữ.

    (Bẫy đã sập ở bản đầu: dùng `testsrc2` thì bản KHÔNG lớp chữ vẫn đếm được
    2,387% đỏ vì chính hoạ tiết test có ô đỏ -> ngưỡng nào cũng nhập nhằng.)
    """
    subprocess.run(
        [FF, "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=0x1E6F5C:size=640x360:rate=25:d={giay}",
         "-f", "lavfi", "-i", f"sine=frequency=300:duration={giay}",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(p)], check=True,
        creationflags=0x08000000)
    return p


def dem_khung(mp4: Path) -> int:
    """SỐ KHUNG THẬT (bẫy exit-code-0: rc=0 mà file 0 khung)."""
    r = subprocess.run(
        [FP, "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True, creationflags=0x08000000)
    try:
        return int((r.stdout or "0").strip().split(",")[0])
    except ValueError:
        return -1


def do_do(mp4: Path, giay: float = 2.0):
    """(% điểm ảnh ĐỎ dải TRÊN = hộp tiêu đề, % dải DƯỚI = huy hiệu Part)."""
    from PIL import Image
    png = mp4.with_name(mp4.stem + "_khung.png")
    r = subprocess.run(
        [FF, "-y", "-loglevel", "error", "-ss", f"{giay}", "-i", str(mp4),
         "-frames:v", "1", str(png)], capture_output=True, text=True,
        creationflags=0x08000000)
    if r.returncode or not png.exists():
        return (-1.0, -1.0)
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    tren = duoi = n_tren = n_duoi = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            rr, gg, bb = px[x, y]
            do = rr > 120 and gg < 90 and bb < 90 and rr - max(gg, bb) > 50
            if y < h * 0.45:
                n_tren += 1
                tren += do
            elif y > h * 0.60:
                n_duoi += 1
                duoi += do
    return (100.0 * tren / max(1, n_tren), 100.0 * duoi / max(1, n_duoi))


def xuat(src: Path, dst: Path, ovl):
    export_canvas_clip(str(src), str(dst), [(0.5, 5.0)], (0.5, 0.5, 0.9),
                       bg="blur", out_w=OUT_W, out_h=OUT_H, encoder="libx264",
                       overlay_png=(str(ovl) if ovl else None),
                       hieu_ung="tat", chuyen_canh="tat",
                       fx_whoosh=False, fx_fade=False)
    return dem_khung(dst), do_do(dst)


# ═════════════════ CA 1 — ĐỐI CHỨNG: có lớp chữ / không có ═══════════════════
print("\n═══ CA 1 — đối chứng CÓ / KHÔNG lớp chữ (đếm điểm ảnh đỏ) ═══")
src = lam_nguon(_SB / "src.mp4")
png_co = _SB / "_ovl_1.png"
co_chu = editor.render_overlay_png(LOP, 1, OUT_W, OUT_H, str(png_co),
                                   "Tiêu đề ví dụ của clip", "")
bao("render_overlay_png vẽ được ảnh lớp chữ", bool(co_chu) and png_co.exists(),
    f"{png_co.stat().st_size if png_co.exists() else 0} byte")

k1, (t1, d1) = xuat(src, _SB / "co.mp4", png_co)
k0, (t0, d0) = xuat(src, _SB / "khong.mp4", None)
print(f"      CÓ  lớp chữ: {k1} khung · đỏ TRÊN {t1:6.3f}% · đỏ DƯỚI {d1:6.3f}%")
print(f"      KHÔNG lớp chữ: {k0} khung · đỏ TRÊN {t0:6.3f}% · đỏ DƯỚI {d0:6.3f}%")
bao("clip CÓ lớp chữ: hộp tiêu đề hiện trên khung", t1 >= 2.0, f"{t1:.3f}% >= 2%")
bao("clip CÓ lớp chữ: huy hiệu Part hiện trên khung", d1 >= 1.0, f"{d1:.3f}% >= 1%")
bao("nền sạch: clip KHÔNG lớp chữ phải 0% đỏ", t0 < 0.05 and d0 < 0.05,
    f"trên {t0:.3f}% · dưới {d0:.3f}%")
bao("cả 2 bản đều đủ khung (không dính bẫy rc=0/0 khung)", k1 > 100 and k0 > 100,
    f"{k1} và {k0} khung")

# ═══ CA 2 — TÁI HIỆN LỖI: ảnh lớp chữ bị xoá, KHÔNG có đơn thuốc để dựng ═══
print("\n═══ CA 2 — tái hiện: ảnh `_ovl_` mất -> export_canvas_clip nuốt IM LẶNG ═══")
png_mat = _SB / "_ovl_mat.png"
editor.render_overlay_png(LOP, 1, OUT_W, OUT_H, str(png_mat), "Tiêu đề", "")
png_mat.unlink()
k2, (t2, d2) = xuat(src, _SB / "mat.mp4", png_mat)
print(f"      ảnh mất: {k2} khung · đỏ TRÊN {t2:6.3f}% · đỏ DƯỚI {d2:6.3f}%")
bao("TÁI HIỆN ĐƯỢC: ảnh mất -> 0% đỏ mà ffmpeg vẫn rc=0 + đủ khung",
    t2 < 0.05 and d2 < 0.05 and k2 > 100,
    f"trên {t2:.3f}% · dưới {d2:.3f}% · {k2} khung (đúng cảnh anh Hùng gặp)")

# ═════ CA 3 — BẢN VÁ: job DỰNG LẠI ảnh lớp chữ từ đơn thuốc trong payload ════
print("\n═══ CA 3 — bản vá: `_dung_lai_anh_chu` dựng lại từ ĐƠN THUỐC ═══")
spec = {"layers": LOP, "logo": None, "part_no": 1,
        "title": "Tiêu đề ví dụ của clip", "title_vi": "",
        "video_px": None, "part_case": "", "hook_case": ""}
png_lai = _SB / "_ovl_lai.png"
lam_lai = M1._dung_lai_anh_chu(
    {"ovl_spec": spec, "out_w": OUT_W, "out_h": OUT_H}, str(png_lai))
bao("dựng lại được ảnh lớp chữ khi file đã mất", bool(lam_lai),
    f"{png_lai.stat().st_size if png_lai.exists() else 0} byte")
k3, (t3, d3) = xuat(src, _SB / "lai.mp4", png_lai if lam_lai else None)
print(f"      sau khi dựng lại: {k3} khung · đỏ TRÊN {t3:6.3f}% · đỏ DƯỚI {d3:6.3f}%")
bao("hộp tiêu đề TRỞ LẠI đúng như bản gốc", abs(t3 - t1) < 0.30,
    f"{t2:.3f}% (hỏng) -> {t3:.3f}% · bản gốc {t1:.3f}%")
bao("huy hiệu Part TRỞ LẠI đúng như bản gốc", abs(d3 - d1) < 0.30,
    f"{d2:.3f}% (hỏng) -> {d3:.3f}% · bản gốc {d1:.3f}%")

# ═══════ CA 4 — ĐÚNG CẢNH THẬT: tắt app giữa lượt xuất rồi mở lại ════════════
# `export_clip` phải GIỮ ảnh lớp chữ khi huỷ là do TẮT APP (job sẽ chạy lại),
# và chỉ dọn khi user THẬT SỰ bấm Huỷ (`jobs.cancel_req=1`).
print("\n═══ CA 4 — huỷ do TẮT APP giữ ảnh · user bấm Huỷ mới dọn ═══")


class _Ctx:
    def __init__(self, job_id):
        self.job_id = job_id
        self.profile = {"encoder": "libx264"}

    def progress(self, *_a, **_k):
        pass


def _job(cancel_req: int) -> int:
    return db.insert(
        "INSERT INTO jobs(type, payload, status, cancel_req, attempts, "
        "max_attempts) VALUES('m1_export_clip','{}','running',?,1,3)",
        (cancel_req,))


def _thu_huy(cancel_req: int, ten: str) -> bool:
    p = _SB / f"_ovl_huy{cancel_req}.png"
    editor.render_overlay_png(LOP, 1, OUT_W, OUT_H, str(p), "Tiêu đề", "")
    goc = M1._export_clip_impl
    M1._export_clip_impl = lambda *a, **k: (_ for _ in ()).throw(CanceledError())
    try:
        M1.export_clip({"overlay_png": str(p)}, _Ctx(_job(cancel_req)))
    except CanceledError:
        pass
    finally:
        M1._export_clip_impl = goc
    return p.exists()


con_khi_tat_app = _thu_huy(0, "tắt app")
con_khi_user_huy = _thu_huy(1, "user bấm Huỷ")
bao("TẮT APP giữa lượt xuất: GIỮ ảnh lớp chữ (job còn chạy lại)",
    con_khi_tat_app, "ảnh còn" if con_khi_tat_app else "ảnh ĐÃ BỊ XOÁ = lỗi cũ")
bao("user bấm Huỷ: dọn ảnh lớp chữ (không để rác)", not con_khi_user_huy,
    "đã dọn" if not con_khi_user_huy else "còn rác")

# ═════════════ CA 5 — TIÊU ĐỀ HIỂM: %, :, ', dấu tiếng Việt, dài, rỗng ═══════
print("\n═══ CA 5 — tiêu đề hiểm (%, :, ', tiếng Việt có dấu, rất dài, rỗng) ═══")
CA = [
    ("tiếng Việt có dấu", "Cô gái bí ẩn xuất hiện giữa đêm mưa", True),
    ("chứa %", "Giảm 50% giá — sốc chưa từng thấy 100%", True),
    ("chứa :", "Bí mật: thứ không ai dám nói ra", True),
    ("chứa dấu nháy '", "He's the one who's lying — don't trust 'em", True),
    ("chứa \\ và \"", 'Đường dẫn C:\\Users\\Admin "quan trọng"', True),
    ("rất dài (300 ký tự)", "Chuyện chấn động " * 18, True),
    ("RỖNG", "", False),          # lớp {title} rỗng -> chỉ còn huy hiệu Part
]
for ten, chu, mong_co_hop in CA:
    p = _SB / f"_ovl_ca_{abs(hash(ten)) % 9999}.png"
    try:
        editor.render_overlay_png(LOP, 1, OUT_W, OUT_H, str(p), chu, "")
    except Exception as e:  # noqa: BLE001
        bao(f"tiêu đề {ten}", False, f"render NỔ: {type(e).__name__}: {e}")
        continue
    if not p.exists():
        bao(f"tiêu đề {ten}", False, "không vẽ ra ảnh")
        continue
    dst = _SB / f"ca_{abs(hash(ten)) % 9999}.mp4"
    try:
        k, (t, d) = xuat(src, dst, p)
    except Exception as e:  # noqa: BLE001
        bao(f"tiêu đề {ten}", False, f"ffmpeg NỔ: {type(e).__name__}: {e}")
        continue
    hop_ok = (t >= 2.0) if mong_co_hop else True
    bao(f"tiêu đề {ten}: hộp đỏ + huy hiệu Part vào được file",
        hop_ok and d >= 1.0 and k > 100,
        f"{k} khung · đỏ TRÊN {t:.3f}% · đỏ DƯỚI {d:.3f}%")
bao("tiêu đề RỖNG: huy hiệu Part vẫn phải còn (không mất cả 2)", True,
    "xem dòng trên")

# ═══════════════════════════════ TỔNG KẾT ════════════════════════════════════
print("\n" + "═" * 74)
print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
for x in _LOI:
    print("   ✗ " + x)
print("SỐ ĐO CỐT LÕI: hộp tiêu đề "
      f"{t1:.3f}% (đúng) -> {t2:.3f}% (lỗi) -> {t3:.3f}% (đã vá) · "
      f"huy hiệu Part {d1:.3f}% -> {d2:.3f}% -> {d3:.3f}%")
print("═" * 74)
sys.exit(1 if _LOI else 0)
