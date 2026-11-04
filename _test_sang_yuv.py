"""CỔNG 102 — NÂNG SÁNG NHẸ + DỰNG NỀN CONG Ở YUV (31/10/2026).

Hai thay đổi anh Hùng duyệt sau khi xem cùng 1 Part xuất 2 cách:
  * `template_backgrounds.dung_yuv()` MẶC ĐỊNH BẬT: khung cong + lớp sau dựng ở
    YUV thay vì RGB -> cả lượt xuất nhanh ~28% (174 -> 125 s/Part 108 s), đủ
    khung, chỉ lệch vị trí 1 điểm ảnh.
  * `ffmpeg_utils.loc_do_sang` + khoá mẫu `do_sang` (% gamma, trần 20).

Canh bằng ffmpeg THẬT + DB THẬT (sandbox), không mock đường ffmpeg:
  1. `loc_do_sang`: 0/rác -> chuỗi rỗng; kẹp trần; gamma đúng.
  2. BẤT BIẾN 200-300 kênh: do_sang=0 -> lệnh ffmpeg + `dedup_key` GIỐNG TỪNG KÝ
     TỰ như không truyền; >0 -> khoá ĐỔI (không bị smart-skip).
  3. Nâng sáng: khung video sáng hơn, KHÔNG thêm điểm cháy trắng.
  4. YUV vs RGB trên nền cong nhiều lớp: đủ khung, đúng độ dài, sau khi bù 1 điểm
     ảnh thì giống (PSNR >= 38 dB) — tức chỉ là dịch vị trí, không giảm chất lượng.
  5. Ô Chỉnh mẫu lưu/nạp `do_sang` đúng.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
HOP = Path(tempfile.mkdtemp(prefix="bq_test_sang_"))
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "s.db")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(GOC))
import _test_guard  # noqa: E402,F401

import numpy as np  # noqa: E402
from config import settings  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402
from app.core import template_backgrounds as tb  # noqa: E402

DAT = HONG = 0
F = settings.FFMPEG_PATH


def ok(dk, ten, chi=""):
    global DAT, HONG
    DAT, HONG = (DAT + 1, HONG) if dk else (DAT, HONG + 1)
    print(("  ĐẠT  " if dk else "  HỎNG ") + ten + (f" — {chi}" if chi else ""))


print("CỔNG 102 — nâng sáng nhẹ + dựng nền cong ở YUV")
print("\n1. loc_do_sang")
ok(fu.loc_do_sang(0) == "" and fu.loc_do_sang(None) == "" and fu.loc_do_sang(-5) == "",
   "0 / None / âm -> không thêm bộ lọc")
ok(fu.loc_do_sang("abc") == "" and fu.loc_do_sang(float("nan")) == "", "rác / NaN -> không nổ, không thêm")
ok(fu.loc_do_sang(8) == "eq=gamma=1.080", "8% -> eq=gamma=1.080", fu.loc_do_sang(8))
ok(fu.loc_do_sang(99) == "eq=gamma=1.200", "quá trần -> kẹp 20% (không loá)", fu.loc_do_sang(99))

# nguồn thử: có vùng tối + vùng sáng + chuyển động
SRC = HOP / "nguon.mp4"
HOP.mkdir(exist_ok=True)
subprocess.run([F, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=6",
                "-f", "lavfi", "-i", "sine=f=440:d=6", "-vf", "eq=brightness=-0.12",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(SRC)],
               check=True)


def xuat(ten, **kw):
    dst = HOP / f"{ten}.mp4"
    lenh = []
    goc = fu._run

    def _run(cmd, *a, **k):
        lenh.append(list(map(str, cmd)))
        return goc(cmd, *a, **k)
    fu._run = _run
    try:
        fu.export_canvas_clip(str(SRC), str(dst), [(0.0, 6.0)], (0.5, 0.5, 0.97), **kw)
    finally:
        fu._run = goc
    return dst, lenh


def khung(f, t=3.0):
    r = subprocess.run([F, "-v", "error", "-ss", str(t), "-i", str(f), "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(1920, 1080, 3).astype(float)


def dem(f):
    r = subprocess.run([str(Path(F).with_name("ffprobe.exe")) if Path(F).with_name("ffprobe.exe").exists() else "ffprobe",
                        "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-show_entries", "format=duration", "-of", "json", str(f)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    return int(d["streams"][0]["nb_read_frames"]), round(float(d["format"]["duration"]), 3)


print("\n2. BẤT BIẾN: do_sang=0 không đổi một ký tự")
_, l0 = xuat("khong_truyen", bg="blur")
_, l1 = xuat("sang0", bg="blur", do_sang=0)
an = lambda L: [[x for x in c if HOP.name not in x] for c in L]  # noqa: E731
ok(an(l0) == an(l1) and len(l0) > 0, "lệnh ffmpeg với do_sang=0 GIỐNG TỪNG KÝ TỰ khi không truyền",
   f"{len(l0)} lệnh")

from app import services as SV  # noqa: E402
from app.database import db as DB  # noqa: E402
_P = DB.insert("INSERT INTO projects (name, assets_dir) VALUES (?,?)", ("k", str(HOP / "k")))
_V = DB.insert("INSERT INTO videos (project_id, src_path, duration) VALUES (?,?,?)", (_P, str(SRC), 6.0))
_C = DB.insert("INSERT INTO clips (video_id, start_sec, end_sec, status) VALUES (?,?,?,?)", (_V, 0.0, 6.0, "suggested"))
ghi = []


class _Pool:
    def enqueue(self, kind, payload, **kw):
        ghi.append((payload, kw["dedup_key"]))
        return 1


def key(**kw):
    ghi.clear()
    SV.enqueue_export(_Pool(), _C, _V, _P, **kw)
    return ghi[0]


p0, k0 = key()
p1, k1 = key(do_sang=0)
p8, k8 = key(do_sang=8)
ok(k0 == k1 and "do_sang" not in p1, "dedup_key do_sang=0 GIỐNG TỪNG KÝ TỰ, payload không mang khoá")
ok(k8 != k0 and k8.startswith(k0) and p8.get("do_sang") == 8.0,
   "do_sang=8 -> khoá ĐỔI (nối ĐUÔI), payload mang 8", k8[len(k0):])
_, k99 = key(do_sang=99)
ok(k99.endswith(":ds20.0"), "rác quá trần vào hash ở dạng ĐÃ KẸP (20)", k99[-8:])

print("\n3. Nâng sáng: sáng hơn, không cháy trắng")
a0, _ = xuat("s0", bg="blur")
a8, l8 = xuat("s8", bg="blur", do_sang=8)
ok(any("eq=gamma=1.080" in " ".join(c) for c in l8), "lệnh xuất THẬT mang eq=gamma=1.080")
f0, f8 = khung(a0), khung(a8)
y = lambda a: (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[700:1240]  # noqa: E731
ok(y(f8).mean() > y(f0).mean() + 2, "khung video SÁNG hơn", f"{y(f0).mean():.1f} -> {y(f8).mean():.1f}")
chay = lambda a: (a[700:1240] >= 254).all(2).mean() * 100  # noqa: E731
ok(chay(f8) <= chay(f0) + 0.5, "KHÔNG thêm điểm cháy trắng", f"{chay(f0):.2f}% -> {chay(f8):.2f}%")
ok(dem(a8) == dem(a0), "đủ khung + đúng độ dài như bản không nâng sáng", str(dem(a8)))

print("\n4. Nền cong nhiều lớp: YUV (mới) vs RGB (cũ)")
BG = "layer:blur:curve:echo:opacity70:scale107:ngang102"
os.environ["BQ_NEN_CONG_YUV"] = "0"
c0, lc0 = xuat("rgb", bg=BG)
os.environ["BQ_NEN_CONG_YUV"] = "1"
c1, lc1 = xuat("yuv", bg=BG)
os.environ.pop("BQ_NEN_CONG_YUV", None)
ok(tb.dung_yuv() is True, "mặc định = cách MỚI (YUV)")
ok(any("format=yuv420" in " ".join(c) for c in lc1) and not any("lutrgb" in " ".join(c) for c in lc1),
   "lệnh mới thật sự dựng ở YUV (không còn lutrgb/RGBA)")
ok(dem(c1) == dem(c0), "đủ khung + đúng độ dài như cách cũ", f"{dem(c1)} vs {dem(c0)}")
r0, r1 = khung(c0), khung(c1)


def psnr(a, b):
    m = ((a - b) ** 2).mean()
    return 99.0 if m == 0 else 10 * np.log10(255 ** 2 / m)


Y = lambda a: 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]  # noqa: E731
_bu = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
tot = max(psnr(r0[700:1240, 20:-20], np.roll(np.roll(r1, dy, 0), dx, 1)[700:1240, 20:-20]) for dy, dx in _bu)
toty = max(psnr(Y(r0)[700:1240, 20:-20], np.roll(np.roll(Y(r1), dy, 0), dx, 1)[700:1240, 20:-20]) for dy, dx in _bu)
print(f"       (khung video sau bù 1 điểm ảnh: ĐỘ SÁNG {toty:.1f} dB · cả màu {tot:.1f} dB)")
ok(toty >= 40, "sau khi bù 1 điểm ảnh, ĐỘ SÁNG khung video giống (chỉ dịch vị trí)", f"{toty:.1f} dB")
ok(psnr(r0[:600], r1[:600]) >= 38, "nền mờ phía trên giống", f"{psnr(r0[:600], r1[:600]):.1f} dB")

print("\n5. Ô Chỉnh mẫu lưu/nạp do_sang")
from PyQt6.QtWidgets import QApplication  # noqa: E402
_qa = QApplication.instance() or QApplication([])
from app.ui.editor import EditorDialog  # noqa: E402
d = EditorDialog("", {"bg": "blur", "do_sang": 8})
ok(d.do_sang_spin.value() == 8, "nạp mẫu có do_sang=8 -> ô hiện 8")
lay = d._collect_layout()
ok(isinstance(lay, dict) and lay.get("do_sang") == 8, "lưu mẫu -> mang do_sang=8",
   str((lay or {}).get("do_sang")))
d2 = EditorDialog("", {"bg": "blur"})
ok(d2.do_sang_spin.value() == 0, "mẫu cũ không có khoá -> ô = 0 (không đổi gì)")

import shutil  # noqa: E402
shutil.rmtree(HOP, ignore_errors=True)
print(f"\nKETQUA: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
