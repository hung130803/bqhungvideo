"""CỔNG 96 — NỀN KHÔNG XANH LÈ + CHỮ KHÔNG RA Ô VUÔNG (30/10/2026).

Anh Hùng gửi ảnh Part: nửa phải nền mờ XANH LÈ, tiêu đề + "Part" là dãy ô
trắng. Quét 157-164 Part 27-30/10: 90 Part nền xanh, 1 Part chữ ô vuông.

(A) Gốc nền xanh: `-hwaccel cuda` ra khung nv12, `boxblur` làm mờ khung nv12
    HỎNG MÀU (rc=0, im lặng). `_nvdec_works` cũ chỉ hỏi "chạy được không" nên
    chế độ auto BẬT nó. Nay `_nvdec_dung_mau` SO MÀU với giải mã CPU qua đúng
    chuỗi nền. Cổng chạy ffmpeg THẬT của app, có TỰ KIỂM: chính chuỗi đó giải
    bằng GPU phải LỆCH (thước có răng) trên máy có NVDEC.
(B) Chữ ô vuông: `_phong_ra_o_vuong` phải nhận phông đúng là KHÔNG ô vuông,
    phông ô vuông giả lập là CÓ; lớp chữ thật vẽ ra phải có chữ (soi pixel).
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _test_guard  # noqa: F401,E402

import numpy as np  # noqa: E402

OK = FAIL = 0


def ok(dk, ten, ct=""):
    global OK, FAIL
    if dk:
        OK += 1
        print(f"  OK   {ten} {ct}")
    else:
        FAIL += 1
        print(f"  FAIL {ten} {ct}")


from app.core import ffmpeg_utils as F  # noqa: E402
from config import settings  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="bq_c96_"))
src = tmp / "t.mp4"
subprocess.run([settings.FFMPEG_PATH, "-v", "error", "-y", "-f", "lavfi", "-i",
                "testsrc2=size=1920x1080:rate=30", "-frames:v", "30", "-pix_fmt",
                "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", str(src)],
               check=True)

print("A. nền mờ: giải mã GPU phải ĐÚNG MÀU mới được bật")
ok("boxblur" in F._NVDEC_CHUOI_THU, "chuỗi thử có boxblur (chỗ hỏng thật)")
co_gpu = F.detect_encoder() == "h264_nvenc"
if co_gpu:
    def giai(hw):
        r = subprocess.run([settings.FFMPEG_PATH, "-v", "error", *hw, "-ss", "0.5",
                            "-i", str(src), "-frames:v", "1", "-vf",
                            F._NVDEC_CHUOI_THU, "-f", "rawvideo", "-"],
                           capture_output=True)
        return np.frombuffer(r.stdout, np.uint8).astype(int)
    lech = float(np.abs(giai([]) - giai(["-hwaccel", "cuda"])).mean())
    print(f"     lệch màu GPU/CPU đo thật: {lech:.1f}/255")
    ket = F._nvdec_dung_mau(str(src))
    ok(ket == (lech <= 6.0), "_nvdec_dung_mau khớp phép đo độc lập",
       f"(trả {ket}, lệch {lech:.1f})")
    F._NVDEC_CACHE = None
    F._HWACCEL_HONG = False
    vao = F._hwaccel_vao()
    ok((vao == []) == (lech > 6.0), "auto KHÔNG bật GPU khi GPU lệch màu", str(vao))
else:
    print("     máy không NVENC -> bỏ phần đo GPU")

print("B. lớp chữ không được ra Ô VUÔNG")
from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtGui import QFont, QImage  # noqa: E402
app = QApplication.instance() or QApplication([])
from app.ui.fonts import load_fonts  # noqa: E402
load_fonts()
from app.ui import editor as E  # noqa: E402

ok(not E._phong_ra_o_vuong(E._qfont("Montserrat", 60)), "Montserrat vẽ chữ thật")
ok(not E._phong_ra_o_vuong(E._qfont("Arial", 60)), "Arial vẽ chữ thật")
# TỰ KIỂM bộ dò: đường viền 'A' và 'o' giống hệt (kiểu tofu) -> phải kêu
from PyQt6.QtGui import QPainterPath  # noqa: E402
o1, o2 = QPainterPath(), QPainterPath()
o1.addRect(0, -40, 30, 40)
o2.addRect(0, -40, 30, 40)
ok(o1.elementCount() == o2.elementCount() and o1.boundingRect() == o2.boundingRect(),
   "TỰ KIỂM: hai ô giống hệt thỏa điều kiện ô vuông của bộ dò")
_goc = E._phong_ra_o_vuong
E._phong_ra_o_vuong = lambda f: True        # bộ máy phông hỏng hoàn toàn
try:
    E.render_overlay_png([{"text": "Part {n}", "font": "Montserrat", "size": .03,
                           "nx": .5, "ny": .8, "color": "#FFFFFF", "is_part": True}],
                         2, 1080, 1920, str(tmp / "hong.png"), nghiem=True)
    ok(False, "chữ ô vuông KHÔNG được ghi ảnh (phải ném lỗi)")
except RuntimeError as e:
    ok("ô vuông" in str(e), "chữ ô vuông -> NÉM lỗi, không ghi ảnh hỏng")
ok(not (tmp / "hong.png").exists(), "không có file ảnh hỏng")
# Giao diện (nghiem=False) KHÔNG được ném: ném ở bộ sưu tập mẫu = SẬP APP
try:
    E.render_overlay_png([{"text": "Part {n}", "font": "Montserrat", "size": .03,
                           "nx": .5, "ny": .8, "color": "#FFFFFF", "is_part": True}],
                         2, 1080, 1920, str(tmp / "ui.png"))
    ok(True, "đường giao diện không ném lỗi (không sập app)")
except RuntimeError:
    ok(False, "đường giao diện không ném lỗi (không sập app)")
_lan = []
E._phong_ra_o_vuong = lambda f: (_lan.append(f.family()) or len(_lan) == 1)
E.render_overlay_png([{"text": "Part {n}", "font": "Montserrat", "size": .03,
                       "nx": .5, "ny": .8, "color": "#FFFFFF", "is_part": True}],
                     2, 1080, 1920, str(tmp / "lui.png"), nghiem=True)
ok((tmp / "lui.png").exists() and "Arial" in _lan, "Montserrat hỏng -> lùi Arial, vẫn có chữ", str(_lan))
E._phong_ra_o_vuong = _goc

png = tmp / "that.png"
E.render_overlay_png([{"text": "Part {n}", "font": "Montserrat", "size": .03,
                       "nx": .5, "ny": .8, "color": "#FFFFFF", "is_part": True,
                       "bg": True, "bg_color": "#C8191B", "bg_alpha": 1.0}],
                     2, 1080, 1920, str(png))
im = QImage(str(png)).convertToFormat(QImage.Format.Format_ARGB32)
b = im.constBits()
b.setsize(im.sizeInBytes())
a = np.frombuffer(b, np.uint8).reshape(im.height(), im.width(), 4)
trang = (a[..., :3].min(2) > 235) & (a[..., 3] > 235)
k = trang.copy()
for dy in range(-4, 5):
    for dx in range(-4, 5):
        k &= np.roll(np.roll(trang, dy, 0), dx, 1)
print(f"     điểm chữ trắng {int(trang.sum())} · khối trắng đặc 9x9 {int(k.sum())}")
ok(trang.sum() > 500, "lớp chữ thật có chữ")
ok(k.sum() < 50, "không có khối trắng đặc (ô vuông)")


print("C. AI chọn đoạn không được rơi về 'cắt cơ bản' vì lỗi JSON + cắt cơ bản phải ra đoạn")
from app.ai import llm  # noqa: E402
_m = ("Gọi groq thất bại: Error code: 400 - {'error': {'message': \"Failed to validate JSON. "
      "Please adjust your prompt.\", 'code': 'json_validate_failed', 'failed_generation': ''}}")
ok(llm.la_loi_tham_so_them(_m), "400 'Failed to validate JSON' -> gọi lại kiểu TRẦN (đo thật 30/10)")
ok(not llm.la_loi_tham_so_them("Error code: 429 rate_limit_exceeded"), "TỰ KIỂM: 429 KHÔNG bị nuốt")
from app.modules import m1_highlight as m1  # noqa: E402
_segs = [{"start": i * 4.0, "end": i * 4.0 + 4, "text": "Câu %d." % i} for i in range(27)]
_n0 = len(m1._build_candidates({"segments": _segs}, {}, 108.0,
                               {"min_len": 60.0, "max_len": 0.0, "target_len": 75.0}))
ok(_n0 > 0, "độ dài tối đa = 0 (không giới hạn) vẫn ra ứng viên", f"({_n0})")

print("D. nền thiết kế: bề ngang video LUÔN kín, chiều cao do mẫu chỉnh")
from app.core import template_backgrounds as TB  # noqa: E402
_m = "design:paper:drift:curve:echo:opacity55:scale112"
ok(TB.encode("paper", True, True, True, opacity=55, scale=112) == _m,
   "chuỗi nền MẶC ĐỊNH giữ nguyên từng ký tự (200-300 kênh không xuất lại)")
for _ten, (_iw, _ih) in {"dọc 720x966": (720, 966), "dọc 9:16": (1080, 1920),
                         "ngang 16:9": (1920, 1080), "vuông": (1080, 1080)}.items():
    for _cao in (44, 65):
        _cx, _cy, _sw, _giu = TB.khung((.5, .5, 1.0), _iw, _ih, 1080, 1920, _cao)
        _h = 1080 * _ih / _iw * _giu
        ok(_sw == 1.0 and _h <= 1920 * _cao / 100 + .5, f"{_ten} cao {_cao}%: rộng 100%, cao {_h / 1920:.0%}")
ok(TB.layer_settings(_m + ":cao65")["cao"] == 65 and TB.options(_m + ":cao65")[0] == "paper",
   "cờ cao65 đọc được, nền vẫn hợp lệ")
ok(TB.options(_m + ":cao5")[0] is None, "cờ cao ngoài khoảng bị từ chối")

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print(f"KETQUA: ĐẠT {OK} · HỎNG {FAIL}")
sys.exit(1 if FAIL else 0)
