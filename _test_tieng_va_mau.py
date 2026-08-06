# -*- coding: utf-8 -*-
"""CỔNG 25 — TIẾNG ĐỘNG THEO NỘI DUNG CHỖ NỐI + TÊN MẪU THẬT TRONG NHẬT KÝ.

Gốc: nhật ký THẬT của anh Hùng 06/08/2026, 2 dòng liền nhau ghi
    Part 1 ... tiếng động: reveal/k_interfacesounds_confirmation_003.opus
    Part 2 ... tiếng động: reveal/k_interfacesounds_confirmation_003.opus
=> 2 lỗi:
  (1) clip 2 đoạn chỉ có ĐÚNG 1 điểm nối, mà luật cũ "điểm nối CUỐI = reveal"
      nên điểm nối duy nhất đó luôn thành 'reveal' -> MỌI Part đều tiếng "ding";
  (2) dòng nhật ký ghi mẫu «(mẫu đã chốt lúc xếp job)» thay vì TÊN mẫu thật ->
      không đối chiếu được "chọn kiểu X ra kiểu Y".

Cổng này chặn cả 2, dùng THÀNH PHẦN THẬT: DB thật (sandbox), kho tiếng động
thật trong app/assets/sfx, file nhật ký thật.
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="tiengmau_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dieu_kien, ten: str, chi_tiet: str = "") -> None:
    global OK
    if dieu_kien:
        OK += 1
        print(f"  ✅ {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        LOI.append(f"{ten} — {chi_tiet}")
        print(f"  ❌ {ten} — {chi_tiet}")


# ══════════════ PHẦN A — LOẠI TIẾNG THEO NỘI DUNG CHỖ NỐI ══════════════
print("\n=== A. Loại tiếng suy theo NỘI DUNG chỗ nối ===")
from app.modules import m1_highlight as M  # noqa: E402

_nhay = M._loai_theo_khoang_nhay
_ctx = M._context_join_categories

# A1 — LỖI GỐC: clip 2 đoạn KHÔNG được ra 'reveal'
for ten, segs in (
    ("hook-first (nhảy ngược)", [(300.0, 305.0), (10.0, 60.0)]),
    ("liền mạch (bỏ 0,5s)", [(10.0, 40.0), (40.5, 80.0)]),
    ("nhảy xa, đoạn kế dài", [(10.0, 40.0), (200.0, 250.0)]),
    ("nhảy xa, đoạn kế NGẮN", [(10.0, 40.0), (200.0, 202.0)]),
):
    cats = _ctx(segs, {}, seed=1)
    ok(cats == cats[:1] and cats[0] != "reveal",
       f"A1 clip 2 đoạn — {ten}", f"ra {cats}")

# A2 — từng luật một
ok(_nhay([(300.0, 305.0), (10.0, 60.0)], 0) == "impact",
   "A2a nhảy NGƯỢC thời gian -> impact")
ok(_nhay([(10.0, 40.0), (40.5, 80.0)], 0) == "pop",
   "A2b gần liền mạch (0,5s) -> pop")
ok(_nhay([(10.0, 40.0), (41.0, 80.0)], 0) == "pop",
   "A2c cách 1,0s vẫn coi là liền mạch -> pop")
ok(_nhay([(10.0, 40.0), (200.0, 202.0)], 0) == "impact",
   "A2d đoạn kế < 2,5s (câu chốt) -> impact")
ok(_nhay([(10.0, 40.0), (200.0, 250.0)], 0) == "transition",
   "A2e nhảy xa, đoạn kế dài -> transition")

# A3 — reveal VẪN CÒN cho clip nhiều đoạn (không được sửa quá tay)
segs4 = [(10.0, 40.0), (100.0, 130.0), (200.0, 230.0), (300.0, 340.0)]
c4 = _ctx(segs4, {}, seed=1)
ok(len(c4) == 3 and c4[-1] == "reveal",
   "A3 clip 4 đoạn — điểm nối CUỐI vẫn 'reveal' (chốt nhẹ)", f"ra {c4}")

# A4 — reveal KHÔNG được đè lên loại đã rõ tính chất
segs_kn = [(10.0, 40.0), (100.0, 130.0), (130.4, 170.0)]
c_kn = _ctx(segs_kn, {}, seed=1)
ok(c_kn[-1] == "pop",
   "A4 chỗ nối cuối LIỀN MẠCH -> giữ 'pop', không dán ding", f"ra {c_kn}")

# A5 — cao trào vẫn ghi đè được (không phá tính năng cũ)
sig_m = {"moments": [{"score": 1.0}, {"score": 9.9}, {"score": 2.0}]}
c_m = _ctx([(10.0, 40.0), (100.0, 130.0), (200.0, 240.0)], sig_m, seed=1)
ok(c_m[0] == "impact", "A5a Mixed-Cut: nối VÀO moment cao nhất -> impact",
   f"ra {c_m}")
sig_h = {"hook_seg": [205.0, 208.0]}
c_h = _ctx([(10.0, 40.0), (100.0, 130.0), (200.0, 240.0)], sig_h, seed=3)
ok(c_h[1] in ("impact", "riser"),
   "A5b clip thường: nối VÀO đoạn chứa hook -> impact/riser", f"ra {c_h}")

# A6 — đầu vào rác KHÔNG được nổ
ok(_ctx([], {}) == [] and _ctx([(1.0, 2.0)], {}) == [],
   "A6a 0/1 đoạn -> [] (không có chỗ nối)")
try:
    xau = _ctx([("a", "b"), (1.0, 2.0), None], {})
    ok(len(xau) == 2 and all(isinstance(x, str) for x in xau),
       "A6b segs rác -> vẫn trả loại hợp lệ, không nổ", f"ra {xau}")
except Exception as e:  # noqa: BLE001
    ok(False, "A6b segs rác -> vẫn trả loại hợp lệ, không nổ",
       f"{type(e).__name__}: {e}")

# A7 — MỌI loại trả về phải có TIẾNG THẬT trong kho (không thì im lặng mất tiếng)
from app.core import ffmpeg_utils as FU  # noqa: E402

kho = FU._sfx_library() or {}
moi_loai = set()
for segs in (
    [(300.0, 305.0), (10.0, 60.0)],
    [(10.0, 40.0), (40.5, 80.0)],
    [(10.0, 40.0), (200.0, 250.0)],
    [(10.0, 40.0), (200.0, 202.0)],
    segs4, segs_kn,
):
    moi_loai.update(_ctx(segs, {}, seed=1))
moi_loai.update(c_m)
moi_loai.update(c_h)
thieu = [c for c in sorted(moi_loai)
         if c != "none" and not (kho.get(c) or [])]
ok(not thieu, "A7a mọi loại tiếng dùng đến đều CÓ FILE trong kho",
   f"loại dùng: {sorted(moi_loai)}" if not thieu else f"THIẾU FILE: {thieu}")
ok(moi_loai <= set(M._AI_SFX_LABELS),
   "A7b không sinh nhãn lạ ngoài _AI_SFX_LABELS", f"{sorted(moi_loai)}")

# A8 — ĐO ĐA DẠNG THẬT: 6 Part kiểu anh Hùng đang chạy (2 đoạn, hook-first)
bo_part = [
    [(300.0, 305.0), (10.0, 60.0)],      # hook-first
    [(120.0, 124.0), (30.0, 95.0)],      # hook-first
    [(20.0, 50.0), (50.4, 110.0)],       # liền mạch
    [(15.0, 45.0), (400.0, 460.0)],      # nhảy xa
    [(15.0, 45.0), (400.0, 401.8)],      # đoạn kế ngắn
    [(500.0, 504.0), (100.0, 160.0)],    # hook-first
]
ra = [_ctx(s, {}, seed=1)[0] for s in bo_part]
ok(len(set(ra)) >= 3,
   "A8 6 Part clip-2-đoạn -> >= 3 loại tiếng khác nhau (trước: 1 loại 'reveal')",
   f"{ra} = {len(set(ra))} loại")

# ══════════════ PHẦN B — TÊN MẪU THẬT TRONG NHẬT KÝ ══════════════
print("\n=== B. Nhật ký phải ghi TÊN MẪU THẬT ===")
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

pid = services.create_project("Kênh Thử B", "M")
services.save_template("Mẫu Kênh B", {"cap_preset": "Ô sáng chạy từ (đa màu)",
                                      "video_rect": [0, 0, 1, 1]})
services.set_project_template(pid, "Mẫu Kênh B")
vid = db.execute("INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,?)",
                 (pid, os.path.join(T, "x.mp4"), 100.0)).lastrowid

# dựng StudioPage KHÔNG qua __init__ (dựng UI đầy đủ = chậm/treo trong sandbox)
sp = StudioPage.__new__(StudioPage)
sp.layout_tpl = {"cap_preset": "Trắng đơn giản"}

# B1 — mẫu RIÊNG của kênh: bản sao phải mang đúng TÊN
t1 = sp._tpl_for_project(pid)
ok(t1.get("_ten_mau") == "Mẫu Kênh B",
   "B1 mẫu riêng của kênh -> bản sao đóng dấu đúng tên",
   f"_ten_mau={t1.get('_ten_mau')!r}")

# B2 — kênh CHƯA gán: lấy tên mẫu trang chính (chưa dựng combo -> tên mặc định)
pid2 = services.create_project("Kênh Chưa Gán", "M")
t2 = sp._tpl_for_project(pid2)
ok(t2.get("_ten_mau") == "Mặc định (không mẫu)",
   "B2 kênh chưa gán -> tên mẫu trang chính, KHÔNG rỗng",
   f"_ten_mau={t2.get('_ten_mau')!r}")

# B3 — MẪU CHỤP LÚC XẾP JOB (đúng đường dây chuyền) vẫn ra TÊN THẬT
sp._export_video_inner = lambda *a, **k: 0
sp._export_video(vid, tpl=t1)
ok(sp._ten_mau_hien == "Mẫu Kênh B",
   "B3 mẫu CHỤP lúc xếp job -> ghi TÊN THẬT",
   f"_ten_mau_hien={sp._ten_mau_hien!r}")
ok("chốt lúc xếp job" not in str(sp._ten_mau_hien),
   "B3b không còn chuỗi vô dụng '(mẫu đã chốt lúc xếp job)'")

# B4 — đường bấm tay (tpl=None) vẫn đúng tên mẫu của kênh
sp._export_video(vid)
ok(sp._ten_mau_hien == "Mẫu Kênh B",
   "B4 bấm tay 'Xuất video này' -> vẫn tên mẫu RIÊNG của kênh",
   f"_ten_mau_hien={sp._ten_mau_hien!r}")

# B5 — dòng nhật ký thật phải chứa tên mẫu
from pathlib import Path  # noqa: E402

payload = {"cap_style": {"preset": "Ô sáng chạy từ (đa màu)",
                         "_mau": "Mẫu Kênh B"},
           "captions": True, "fx_fade": True, "speed": 1.0}
M._ghi_cong_thuc(payload, os.path.join(T, "a.ass"),
                 ["impact", "reveal"], False, "blur", " Part 1 ")
logs = sorted(Path(T, "logs").glob("pipeline_*.log"))
dong = logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1] if logs else ""
ok("mẫu «Mẫu Kênh B»" in dong,
   "B5 dòng CÔNG THỨC trong nhật ký chứa TÊN MẪU thật", dong[:130])
ok("(không rõ)" not in dong and "(mẫu đã chốt" not in dong,
   "B5b không còn tên mẫu giả trong nhật ký")

# ══════════════ KẾT ══════════════
print(f"\n{'='*60}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 25 ĐẠT — tiếng động theo nội dung chỗ nối + tên mẫu thật")
