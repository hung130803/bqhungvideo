# -*- coding: utf-8 -*-
"""CỔNG 19 — MẪU RIÊNG THEO KÊNH: SOI TẬN PAYLOAD TỚI ffmpeg, quy mô 200 KÊNH.

Anh Hùng 31/07/2026: "rà soát kỹ cái phần mẫu từng kênh… đừng để lỗi đến lúc
xuất lỗi này lọ mệt lắm, chạy hàng loạt 200 kênh cơ".

Cổng 16 (`_test_tpl_per_channel.py`) chỉ kiểm tới `_tpl_for_project` — tức MỚI
tới cửa "chốt mẫu". Cổng này đi TIẾP tới cửa cuối: chặn
`services.enqueue_export` và đọc `cap_style["font"]` / `blur_amt` trong payload
— đúng cái ffmpeg vẽ ra clip. Mẫu sai ở đây = 200 kênh ra clip sai mà chỉ biết
khi mở file lên xem.

BẤT BIẾN KIỂM Ở ĐÂY:
  1. 200 kênh 200 mẫu chạy hàng loạt -> mỗi payload mang ĐÚNG mẫu của kênh nó.
  2. Bấm tay (Xuất video này / Xuất cả kênh) cũng theo mẫu CỦA KÊNH đó, không
     ăn theo mẫu đang chọn ở trang chính.
  3. Job đã chốt mẫu: đổi mẫu kênh / đổi mẫu trang chính giữa lúc chạy KHÔNG
     làm lệch job đang chờ xuất.
  4. Mẫu bị XOÁ giữa loạt -> lùi mẫu trang chính, KHÔNG chết dây chuyền, và
     phải GHI CẢNH BÁO vào báo cáo (không âm thầm).
  5. Xuất lồng nhau (re-entrancy) KHÔNG được trộn mẫu giữa 2 video.
  6. self.layout_tpl phải được TRẢ NGUYÊN sau mỗi lượt xuất.
  7. Mở hộp dây chuyền 200 kênh: ngân sách < 4s (đo thật).
"""
import os
import sys
from pathlib import Path
import tempfile
import time

T = tempfile.mkdtemp(prefix="tplexp_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

import app.queue.jobs  # noqa: F401,E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

qapp = QApplication(sys.argv)
from app.database.db import db  # noqa: E402
from app import services  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

QDialog.exec = lambda self: 0
QMessageBox.exec = lambda self: 0
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


# ── CHẶN CỬA CUỐI: mọi payload xuất đi qua đây ──────────────────────────────
BAT: list[dict] = []
_goc_enq = services.enqueue_export


def _enq_gia(pool, clip_id, video_id, project_id, **kw):
    BAT.append({"clip": clip_id, "vid": video_id, "pid": project_id,
                "font": (kw.get("cap_style") or {}).get("font"),
                "size": (kw.get("cap_style") or {}).get("size"),
                "blur": kw.get("blur_amt")})
    return 900000 + len(BAT)


services.enqueue_export = _enq_gia

pg = StudioPage(AppState())
pg.layout_tpl = {"cap_font": "FONT_TRANG_CHINH", "cap_size": 11, "blur_amt": 5,
                 "captions": True}


def tao_mau(ten, font, size):
    services.save_template(ten, {"cap_font": font, "cap_size": size,
                                 "blur_amt": size, "captions": True})


def tao_kenh(ten, mau=""):
    pid = db.execute(
        "INSERT INTO projects(name,assets_dir,grp,pipe_on) VALUES(?,?,'Mỹ',1)",
        (ten, os.path.join(T, ten))).lastrowid
    if mau:
        services.set_project_template(pid, mau)
    return pid


def tao_video(pid, ten="v.mp4", n_clip=1):
    p = os.path.join(T, ten)
    open(p, "wb").write(b"x" * 10)          # gốc PHẢI tồn tại, kẻo _export_video bỏ
    vid = db.execute("INSERT INTO videos(project_id,src_path,duration,width,"
                     "height) VALUES(?,?,600,1920,1080)", (pid, p)).lastrowid
    for i in range(n_clip):
        db.execute("INSERT INTO clips(video_id,start_sec,end_sec,score,title,"
                   "status) VALUES(?,?,?,0.9,'T','ready')",
                   (vid, i * 70.0, i * 70.0 + 65.0))
    return vid


print("\n══ 1. CHẠY HÀNG LOẠT 200 KÊNH — mỗi payload đúng mẫu của kênh mình ══")
N = 200
t0 = time.time()
kenh = []
for i in range(N):
    tao_mau(f"mau{i}", f"FONT{i}", 20 + i)
    pid = tao_kenh(f"Kenh{i}", f"mau{i}")
    vid = tao_video(pid, f"v{i}.mp4")
    kenh.append((pid, vid, f"FONT{i}", 20 + i))
print(f"  (dựng {N} kênh + {N} mẫu + {N} video trong {time.time()-t0:.1f}s)")

pg.auto_export_chk.setChecked(True)
for k, (pid, vid, _f, _s) in enumerate(kenh):
    jid = 500000 + k
    db.execute("INSERT INTO jobs(id,type,status,video_id,project_id,priority) "
               "VALUES(?,'auto','done',?,?,10)", (jid, vid, pid))
    pg._track_auto(jid, vid, pid)
BAT.clear()
t0 = time.time()
pg._check_auto_export_inner()
dt = time.time() - t0
sai = []
for pid, vid, font, size in kenh:
    ps = [b for b in BAT if b["vid"] == vid]
    if not ps:
        sai.append(f"vid{vid}: KHÔNG có payload nào")
    elif any(p["font"] != font or p["size"] != size for p in ps):
        sai.append(f"vid{vid}: mong {font}/{size}, ra "
                   f"{ps[0]['font']}/{ps[0]['size']}")
kiem(len(BAT) == N, f"xuất đủ {N} clip (ra {len(BAT)})")
kiem(not sai, f"cả {N} payload mang ĐÚNG mẫu của kênh mình",
     "; ".join(sai[:4]) + (f" … tổng {len(sai)} sai" if len(sai) > 4 else ""))
kiem(dt < 20.0, f"xuất loạt {N} kênh trong {dt:.1f}s (< 20s)")
kiem(pg.layout_tpl.get("cap_font") == "FONT_TRANG_CHINH",
     "mẫu trang chính được TRẢ NGUYÊN sau loạt xuất", str(pg.layout_tpl))
kiem(not getattr(pg, "_auto_tpl", {}),
     f"sổ mẫu-đã-chốt được dọn sạch, không phình RAM "
     f"(còn {len(getattr(pg, '_auto_tpl', {}))})")

print("\n══ 2. BẤM TAY: 'Xuất video này' phải theo mẫu CỦA KÊNH ══")
pid_a = tao_kenh("KenhTay", "mau7")          # mau7 -> FONT7 / 27
vid_a = tao_video(pid_a, "tay.mp4")
BAT.clear()
pg._export_video(vid_a)
kiem(bool(BAT) and BAT[0]["font"] == "FONT7",
     "bấm tay xuất -> dùng mẫu RIÊNG của kênh (không phải mẫu trang chính)",
     str(BAT[0] if BAT else None))
kiem(pg.layout_tpl.get("cap_font") == "FONT_TRANG_CHINH",
     "bấm tay xong mẫu trang chính vẫn nguyên")

print("\n══ 3. Kênh CHƯA gán -> mẫu trang chính (hành vi CŨ, không phá) ══")
pid_b = tao_kenh("KenhChuaGan")
vid_b = tao_video(pid_b, "chuagan.mp4")
BAT.clear()
pg._export_video(vid_b)
kiem(bool(BAT) and BAT[0]["font"] == "FONT_TRANG_CHINH",
     "kênh chưa gán -> ăn mẫu đang chọn ở trang chính",
     str(BAT[0] if BAT else None))

print("\n══ 4. Job ĐÃ CHỐT mẫu: đổi mẫu giữa lúc chạy KHÔNG lệch ══")
pid_c = tao_kenh("KenhDoiGiuaDuong", "mau3")     # FONT3
vid_c = tao_video(pid_c, "doi.mp4")
jid_c = 600001
db.execute("INSERT INTO jobs(id,type,status,video_id,project_id,priority) "
           "VALUES(?,'auto','done',?,?,10)", (jid_c, vid_c, pid_c))
pg._track_auto(jid_c, vid_c, pid_c)              # chốt FONT3
services.set_project_template(pid_c, "mau9")     # user đổi sang FONT9 SAU đó
pg.layout_tpl = {"cap_font": "DOI_TRANG_CHINH", "cap_size": 1}
BAT.clear()
pg._check_auto_export_inner()
kiem(bool(BAT) and BAT[0]["font"] == "FONT3",
     "job đã chốt vẫn xuất bằng FONT3 (không nhận mẫu đổi sau)",
     str(BAT[0] if BAT else None))
pg.layout_tpl = {"cap_font": "FONT_TRANG_CHINH", "cap_size": 11, "blur_amt": 5}

print("\n══ 5. Mẫu bị XOÁ giữa loạt -> lùi mẫu chính + PHẢI ghi cảnh báo ══")
tao_mau("mau_sap_xoa", "FONT_SAP_XOA", 77)
pid_d = tao_kenh("KenhMauBiXoa", "mau_sap_xoa")
vid_d = tao_video(pid_d, "bixoa.mp4")
services.delete_template("mau_sap_xoa")          # xoá SAU khi đã gán
pg._pipe_report = []
BAT.clear()
pg._export_video(vid_d)
kiem(bool(BAT) and BAT[0]["font"] == "FONT_TRANG_CHINH",
     "mẫu đã xoá -> lùi mẫu trang chính, vẫn xuất được",
     str(BAT[0] if BAT else None))
bao = " ".join(pg._pipe_report) + " " + (pg.status.text() or "")
kiem("mau_sap_xoa" in bao,
     "có CẢNH BÁO nêu tên mẫu đã xoá (không âm thầm ra clip sai)", bao[:160])

print("\n══ 6. XUẤT LỒNG NHAU không được trộn mẫu giữa 2 kênh ══")
pid_e = tao_kenh("KenhNgoai", "mau1")            # FONT1
vid_e = tao_video(pid_e, "ngoai.mp4")
pid_f = tao_kenh("KenhTrong", "mau2")            # FONT2
vid_f = tao_video(pid_f, "trong.mp4")
BAT.clear()
_lan = {"n": 0}


def _enq_long(pool, clip_id, video_id, project_id, **kw):
    """Giả cảnh xấu nhất: giữa lúc xuất video A, có lượt xuất video B chen vào
    (vòng lặp sự kiện lồng: hộp thoại, processEvents, timer...)."""
    ra = _enq_gia(pool, clip_id, video_id, project_id, **kw)
    _lan["n"] += 1
    if _lan["n"] == 1:
        pg._export_video(vid_f)                  # chen ngang
    return ra


services.enqueue_export = _enq_long
try:
    pg._export_video(vid_e)
finally:
    services.enqueue_export = _enq_gia
p_e = [b for b in BAT if b["vid"] == vid_e]
p_f = [b for b in BAT if b["vid"] == vid_f]
kiem(bool(p_e) and all(b["font"] == "FONT1" for b in p_e),
     "video NGOÀI giữ FONT1 dù bị chen ngang", str(p_e))
kiem(bool(p_f) and all(b["font"] == "FONT2" for b in p_f),
     "video CHEN NGANG dùng FONT2 của kênh nó", str(p_f))
kiem(pg.layout_tpl.get("cap_font") == "FONT_TRANG_CHINH",
     "sau lồng nhau, mẫu trang chính vẫn nguyên (không rò)",
     str(pg.layout_tpl.get("cap_font")))

print("\n══ 7. Xuất cả kênh: mỗi video theo mẫu của KÊNH nó ══")
pid_g = tao_kenh("KenhNhieuVideo", "mau5")       # FONT5
v1 = tao_video(pid_g, "g1.mp4")
v2 = tao_video(pid_g, "g2.mp4")
BAT.clear()
pg._export_video(v1)
pg._export_video(v2)
kiem(len(BAT) == 2 and all(b["font"] == "FONT5" for b in BAT),
     "mọi video của kênh dùng cùng mẫu kênh đó", str(BAT))

print("\n══ 8. TÊN MẪU LẠ (dấu, emoji, dài, khoảng trắng) vẫn phải đúng ══")
# (Bỏ ca 'video mồ côi': DB có KHOÁ NGOẠI videos.project_id -> hàng như vậy
#  KHÔNG thể tồn tại; kiểm pid rác đã có ở cổng 16 qua _tpl_for_project.)
LA = ["Mẫu chữ vàng — viền dày", "mẫu 😀 emoji", "  mẫu thừa khoảng trắng  ",
      "MẪU" * 30]
for i, ten in enumerate(LA):
    tao_mau(ten, f"FONTLA{i}", 90 + i)
    pid_l = tao_kenh(f"KenhLa{i}", ten)
    vid_l = tao_video(pid_l, f"la{i}.mp4")
    BAT.clear()
    pg._export_video(vid_l)
    kiem(bool(BAT) and BAT[0]["font"] == f"FONTLA{i}",
         f"tên mẫu lạ #{i} ({ten.strip()[:18]}…) vẫn ra đúng font",
         str(BAT[0] if BAT else None))

print("\n══ 8b. ĐỔI TÊN mẫu (xoá + lưu tên mới) -> báo rõ, không ra clip sai ══")
tao_mau("ten_cu", "FONT_TEN_CU", 55)
pid_r = tao_kenh("KenhDoiTenMau", "ten_cu")
vid_r = tao_video(pid_r, "doiten.mp4")
services.delete_template("ten_cu")
tao_mau("ten_moi", "FONT_TEN_MOI", 56)     # user "đổi tên" = xoá + lưu mới
pg._pipe_report = []
BAT.clear()
pg._export_video(vid_r)
kiem(bool(BAT) and BAT[0]["font"] == "FONT_TRANG_CHINH",
     "mẫu bị đổi tên -> lùi mẫu trang chính (không lấy bừa mẫu khác)",
     str(BAT[0] if BAT else None))
kiem("ten_cu" in (" ".join(pg._pipe_report) + pg.status.text()),
     "báo rõ tên mẫu đã mất + tên kênh")

print("\n══ 9. MỞ HỘP DÂY CHUYỀN với 200 kênh — ngân sách < 4s ══")
t0 = time.time()
pg._pipeline_dialog()
qapp.processEvents()
dt_mo = time.time() - t0
n_dong = pg._pipe_tbl.rowCount()
kiem(dt_mo < 4.0, f"mở hộp {n_dong} dòng trong {dt_mo*1000:.0f}ms (< 4s)")
cb = pg._pipe_tbl.cellWidget(0, 4)
kiem(cb is not None and cb.count() >= 200,
     f"ô chọn mẫu liệt kê đủ mẫu (có {cb.count() if cb else 0})")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — mẫu theo kênh đúng tới payload ffmpeg, 200 kênh")
sys.stdout.flush()
os._exit(0)
