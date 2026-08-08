# TÁI HIỆN LỖI NGHIÊM TRỌNG (anh Hùng 2026-07-26): đang chạy dây chuyền nhóm
# "Mỹ" (nhiều kênh) mà bấm chạy tiếp nhóm "Mỹ mới" -> "có phân tích nhưng
# không xuất gì, đứng im luôn", và NHÓM CŨ CŨNG BỊ.
#
# Test này KHÔNG gọi Groq/ffmpeg encode: pool CỐ Ý không start nên mọi job đứng
# 'pending'. Ta chỉ kiểm SỔ THEO DÕI của dây chuyền — đúng chỗ lỗi nằm:
#   1. hàng đợi nhận (_pipe_intake_q) có bị lượt sau XOÁ mất việc lượt trước?
#   2. mỗi dòng sổ 'taken' có ĐÚNG 1 ctx đang được theo dõi? (ctx mồ côi =
#      video phân tích xong không ai xuất = ĐỨNG IM VĨNH VIỄN)
#   3. 1 file có bị NHẬN 2 LẦN khi 2 lượt chồng nhau?
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="pipe_overlap_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry thật
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát trên máy user

FFMPEG = Path(__file__).resolve().parent / "bin" / "ffmpeg.exe"
STABLE = 70          # > STABLE_AGE_SEC để scan_dir coi là "đứng yên"


_SEED = [0]


def lam_video(p: Path, giay: int = 1) -> None:
    """1 video THẬT (ffprobe đọc được) — nhỏ nhất có thể cho nhanh.

    MỖI FILE PHẢI KHÁC NỘI DUNG: import_video/mark_dup gộp theo file_hash, 2
    file giống byte sẽ bị coi là trùng và làm SAI kết quả đo (bài học lần đầu
    chạy test này: 12 dòng sổ nhưng chỉ 6 job vì mọi video y hệt nhau).
    """
    _SEED[0] += 1
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(FFMPEG), "-y", "-v", "quiet", "-f", "lavfi", "-i",
         f"testsrc=size=320x240:rate=15:duration={giay}", "-f", "lavfi",
         "-i", f"sine=frequency={300 + _SEED[0] * 17}:duration={giay}",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-metadata", f"comment=seed{_SEED[0]}", "-shortest", str(p)],
        check=True)
    old = time.time() - STABLE
    os.utime(p, (old, old))


import app.queue.jobs  # noqa: F401,E402 - handler + cv2 TRƯỚC Qt (thứ tự main.py)

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from app.ui.appsettings import app_settings  # noqa: E402

qapp = QApplication(sys.argv)
st_q = app_settings()
_saved = {k: st_q.value(k) for k in
          ("pipe_root", "chan_group", "chan_groups_extra", "pipe_grp_sel",
           "pipe_recycle_dir")}

from app.core import pipeline as P  # noqa: E402
from app.database.db import db  # noqa: E402
from app.ui.state import AppState  # noqa: E402
from app.ui.studio_page import StudioPage  # noqa: E402

FAIL: list[str] = []


def kiem(dieu_kien: bool, nhan: str, chi_tiet: str = "") -> None:
    if dieu_kien:
        print(f"  ✓ {nhan}")
    else:
        FAIL.append(f"{nhan} — {chi_tiet}")
        print(f"  ✗ {nhan}  << {chi_tiet}")


def lam_kenh(ten: str, nhom: str, n_video: int) -> tuple[int, Path]:
    src = T / "nguon" / ten
    out = T / "xuat" / ten
    out.mkdir(parents=True, exist_ok=True)
    for i in range(n_video):
        lam_video(src / f"{ten}_v{i}.mp4")
    pid = db.execute(
        "INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
        "pipe_mode, pipe_daily, pipe_src) VALUES(?,?,?,?,1,'auto',0,?)",
        (ten, str(T / "assets" / ten), nhom, str(out), str(src))).lastrowid
    return int(pid), src


def so_ctx_dang_theo_doi(pg) -> int:
    """Số ctx đang được dõi: chờ cắt + chờ hook xuất + đang xuất. Mỗi dòng sổ
    'taken' phải ứng với ĐÚNG 1 ctx, không thì có ctx mồ côi."""
    ids = set()
    for ctx in list(pg._pipe_cut.values()):
        ids.add(ctx["entry"])
    for ctx in list(pg._pipe_by_vid.values()):
        ids.add(ctx["entry"])
    for ent in list(pg._pipe_exports.values()):
        ids.add(ent["ctx"]["entry"])
    return len(ids)


def bom_nhip(n: int) -> None:
    """Cho event loop chạy n nhịp -> intake nhận n file (mỗi nhịp 1 file)."""
    for _ in range(n):
        qapp.processEvents()
        time.sleep(0.01)
        qapp.processEvents()


def don_sach() -> None:
    db.execute("DELETE FROM pipeline_files")
    db.execute("DELETE FROM jobs")
    db.execute("DELETE FROM videos")
    db.execute("DELETE FROM projects")


def dung_trang() -> StudioPage:
    st_q.setValue("pipe_root", str(T / "nguon"))
    st_q.setValue("chan_group", "Mỹ")
    st_q.setValue("chan_groups_extra", "[]")
    st_q.setValue("pipe_recycle_dir", str(T / "thungrac"))
    st_q.sync()
    state = AppState()
    pg = StudioPage(state)
    pg._pipe_report = []
    # pool KHÔNG start -> job nằm 'pending', không gọi Groq/ffmpeg encode.
    return pg


def bao_cao(pg, ten: str) -> None:
    taken = db.query("SELECT COUNT(*) AS n FROM pipeline_files "
                     "WHERE status='taken'")[0]["n"]
    jobs = db.query("SELECT COUNT(*) AS n FROM jobs")[0]["n"]
    ctx = so_ctx_dang_theo_doi(pg)
    print(f"  [{ten}] sổ taken={taken}  job={jobs}  ctx đang dõi={ctx}")
    return taken, jobs, ctx


# ═══════════════════ CA 1: chồng lượt CÙNG NHÓM ═══════════════════
# Sát nhất với "chạy nhóm Mỹ rồi lại bấm chạy" — file lượt 1 CHƯA kịp nhận vẫn
# nằm trên đĩa và CHƯA có trong sổ -> lượt 2 quét thấy -> NHẬN LẠI.
print("\n══ CA 1: chồng lượt cùng nhóm (Mỹ, 4 kênh × 2 video) ══")
don_sach()
for i in range(4):
    lam_kenh(f"My{i}", "Mỹ", 2)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ"); st_q.sync()
n1 = pg._pipe_run()
bom_nhip(2)                      # mới nhận 2/8 file -> còn 6 file trong hàng đợi
con_lai = len(getattr(pg, "_pipe_intake_q", []) or [])
print(f"  lượt 1 xếp {n1} (0=nhận dần), còn {con_lai} file trong hàng đợi")
n2 = pg._pipe_run()              # ← BẤM CHẠY LẦN 2 GIỮA LÚC ĐANG NHẬN
bom_nhip(40)                     # để cả 2 lượt nhận xong
taken, jobs, ctx = bao_cao(pg, "CA1")
tren_dia = 8
kiem(taken == ctx,
     "mỗi dòng sổ 'taken' có đúng 1 ctx đang dõi (không ctx mồ côi)",
     f"taken={taken} nhưng chỉ dõi {ctx} ctx -> {taken - ctx} video "
     "phân tích xong KHÔNG AI XUẤT = đứng im vĩnh viễn")
kiem(taken <= tren_dia,
     "không file nào bị NHẬN 2 LẦN",
     f"{tren_dia} file trên đĩa mà sổ ghi nhận {taken} lượt")

# ═══════════════════ CA 2: chồng lượt 2 NHÓM RỜI NHAU ═══════════════════
print("\n══ CA 2: chồng lượt 2 nhóm rời nhau (Mỹ 3 kênh, Mỹ mới 3 kênh) ══")
don_sach()
for i in range(3):
    lam_kenh(f"A{i}", "Mỹ", 2)
for i in range(3):
    lam_kenh(f"B{i}", "Mỹ mới", 2)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ"); st_q.sync()
pg._pipe_run()
bom_nhip(2)
con_lai = len(getattr(pg, "_pipe_intake_q", []) or [])
print(f"  lượt 'Mỹ' còn {con_lai} file trong hàng đợi khi bấm nhóm 2")
st_q.setValue("pipe_grp_sel", "Mỹ mới"); st_q.sync()
pg._pipe_run()                   # ← nhóm khác, GIỮA LÚC nhóm Mỹ đang nhận
bom_nhip(60)
taken, jobs, ctx = bao_cao(pg, "CA2")
kiem(taken == 12,
     "KHÔNG mất việc của lượt trước (12 file 2 nhóm đều được nhận)",
     f"chỉ nhận {taken}/12 -> {12 - taken} video của nhóm chạy trước bị "
     "hàng đợi lượt sau xoá mất, nằm im trong thư mục")
kiem(taken == ctx,
     "mỗi dòng sổ 'taken' có đúng 1 ctx đang dõi",
     f"taken={taken} nhưng dõi {ctx} ctx")

# ═══════════════════ CA 3: 2 kênh 2 nhóm DÙNG CHUNG 1 thư mục ═══════════════
print("\n══ CA 3: 2 kênh khác nhóm trỏ CHUNG 1 thư mục nguồn ══")
don_sach()
pid_a, src_chung = lam_kenh("Chung", "Mỹ", 2)
out_b = T / "xuat" / "ChungB"
out_b.mkdir(parents=True, exist_ok=True)
db.execute("INSERT INTO projects(name, assets_dir, grp, export_dir, pipe_on, "
           "pipe_mode, pipe_daily, pipe_src) VALUES(?,?,?,?,1,'auto',0,?)",
           ("ChungB", str(T / "assets" / "ChungB"), "Mỹ mới", str(out_b),
            str(src_chung)))
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ"); st_q.sync()
pg._pipe_run()
bom_nhip(1)
st_q.setValue("pipe_grp_sel", "Mỹ mới"); st_q.sync()
pg._pipe_run()
bom_nhip(30)
taken, jobs, ctx = bao_cao(pg, "CA3")
kiem(taken == ctx,
     "mỗi dòng sổ 'taken' có đúng 1 ctx đang dõi",
     f"taken={taken} nhưng dõi {ctx} ctx")

# ═══════════════════ CA 4: BẤM 3 LƯỢT chồng nhau ═══════════════════
print("\n══ CA 4: bấm ▶ Chạy 3 lần liên tiếp giữa lúc đang nhận ══")
don_sach()
for i in range(3):
    lam_kenh(f"C{i}", "Mỹ", 3)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(2)
pg._pipe_run()
bom_nhip(2)
pg._pipe_run()
bom_nhip(60)
taken, jobs, ctx = bao_cao(pg, "CA4")
kiem(taken == 9 and ctx == 9,
     "9 file / 9 dòng sổ / 9 ctx — bấm 3 lần không sinh trùng, không mất việc",
     f"taken={taken} ctx={ctx} (mong 9/9)")
# Vòng nhận chỉ được CÓ MỘT: hai chuỗi QTimer song song sẽ in tổng kết 2 lần
# (và đó chính là "ban đầu nó báo chạy xong" mà anh Hùng thấy).
n_tong = sum(1 for d in pg._pipe_report if "tổng nhận" in d)
kiem(n_tong == 1,
     "chỉ MỘT vòng nhận chạy (log 'tổng nhận' xuất hiện 1 lần)",
     f"log 'tổng nhận' xuất hiện {n_tong} lần -> có {n_tong} vòng QTimer "
     "song song, bộ đếm sai và báo 'chạy xong' sớm")

# ═══════════ CA 5: bấm lại khi đã nhận HẾT mà job còn đang cắt ═══════════
# File vẫn nằm trên đĩa (chỉ dọn sau khi xuất đủ Part) nên lượt sau QUÉT THẤY.
print("\n══ CA 5: nhận hết rồi bấm lại (job còn chạy, file còn trên đĩa) ══")
don_sach()
lam_kenh("D0", "Mỹ", 3)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(30)                     # nhận hết 3 file, job nằm 'pending'
t1, j1, c1 = bao_cao(pg, "CA5 sau lượt 1")
pg._pipe_run()                   # ← bấm lại: 3 file vẫn còn trong thư mục
bom_nhip(30)
t2, j2, c2 = bao_cao(pg, "CA5 sau lượt 2")
kiem(t2 == t1 == 3 and c2 == c1 == 3,
     "bấm lại KHÔNG nhận lại video đang cắt dở",
     f"lượt 1: {t1} dòng/{c1} ctx → lượt 2: {t2} dòng/{c2} ctx (mong 3/3)")

# ═══════ CA 6: BÀN GIAO XUẤT khi 2 nhóm chồng lượt (đường thật) ═══════
# Ca quan trọng nhất: đúng chỗ anh Hùng thấy "có phân tích nhưng không xuất".
# Không gọi Groq (chậm + tốn lượt): ta ghi thẳng clip vào DB rồi đánh dấu job
# cắt 'done' — từ đó TOÀN BỘ đường thật chạy: _check_auto_export ->
# _export_video (xếp job xuất THẬT) -> _pipe_on_exported -> _pipe_exports.
print("\n══ CA 6: bàn giao XUẤT khi 2 nhóm chồng lượt ══")
don_sach()
lam_kenh("E_my", "Mỹ", 2)
lam_kenh("E_moi", "Mỹ mới", 2)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(2)
st_q.setValue("pipe_grp_sel", "Mỹ mới")
st_q.sync()
pg._pipe_run()
bom_nhip(40)
cut_jobs = dict(pg._pipe_cut)            # jid -> ctx
print(f"  {len(cut_jobs)} job cắt đang dõi")
for jid, ctx in cut_jobs.items():
    for k in range(2):                   # 2 clip/video -> 2 Part
        db.execute(
            "INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
            "status) VALUES(?,?,?,?,?,'ready')",
            (ctx["vid"], k * 0.3, k * 0.3 + 0.4, 0.9, f"Part thu {k}"))
    db.execute("UPDATE jobs SET status='done', progress=100 WHERE id=?", (jid,))
pg._check_auto_export()                  # ← đường thật, gồm cả code vừa sửa
kiem(len(pg._pipe_exports) == len(cut_jobs),
     f"cả {len(cut_jobs)} video đều được bàn giao sang theo dõi XUẤT",
     f"chỉ {len(pg._pipe_exports)}/{len(cut_jobs)} video vào _pipe_exports — "
     "số còn lại không ai xuất = đứng im")
sai_job = []
for vid, ent in pg._pipe_exports.items():
    if not ent["jobs"]:
        sai_job.append(f"video {vid}: KHÔNG có job xuất nào")
        continue
    for j in ent["jobs"]:
        r = db.query_one("SELECT video_id FROM jobs WHERE id=?", (j,))
        if r is None or int(r["video_id"] or 0) != int(vid):
            sai_job.append(
                f"video {vid} bị gán job {j} của video "
                f"{r['video_id'] if r else '?'}")
kiem(not sai_job,
     "mỗi video dõi ĐÚNG bộ job xuất của chính nó (không lẫn video khác)",
     "; ".join(sai_job[:4]))

# ═══════ CA 7: nhịp poll CHEN NGANG giữa lúc đang xuất (tái nhập) ═══════
# _export_video gọi QApplication.processEvents() giữa các clip -> nhịp poll
# 1.5s có thể chạy lại _check_auto_export khi nó chưa xong. Trước khi sửa,
# lần chen ngang pop mất jid mà vòng ngoài đang giữ -> KeyError -> thoát cả
# nhịp poll (kể cả _pipe_poll). Ca này bắt chính tình huống đó.
print("\n══ CA 7: poll chen ngang giữa lúc đang xuất ══")
don_sach()
lam_kenh("F0", "Mỹ", 3)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(30)
cut_jobs = dict(pg._pipe_cut)
for jid, ctx in cut_jobs.items():
    db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
               "status) VALUES(?,?,?,?,?,'ready')",
               (ctx["vid"], 0.0, 0.4, 0.9, "Part chen"))
    db.execute("UPDATE jobs SET status='done', progress=100 WHERE id=?", (jid,))

goc_export = pg._export_video
chen = {"n": 0}


def _export_chen_ngang(vid, only_clip_id=None, tpl=None):
    """Bắt chước processEvents: lần xuất ĐẦU TIÊN gọi lại _check_auto_export.

    PHẢI nhận cả `tpl` — v2.6.27 đưa việc chốt MẪU THEO KÊNH vào chính
    `_export_video(vid, tpl=...)`. Stub thiếu tham số này thì lượt xuất nổ
    TypeError, app báo qua `_pipe_on_export_failed` (không âm thầm) nhưng test
    lại tưởng dây chuyền hỏng."""
    if chen["n"] == 0:
        chen["n"] = 1
        pg._check_auto_export()          # ← nhịp poll chen vào GIỮA lúc xuất
    return goc_export(vid, only_clip_id, tpl=tpl)


pg._export_video = _export_chen_ngang
no = None
try:
    pg._check_auto_export()
except Exception as e:  # noqa: BLE001
    no = f"{type(e).__name__}: {e}"
pg._export_video = goc_export
kiem(no is None,
     "poll chen ngang KHÔNG làm nổ lỗi (trước đây KeyError giết cả nhịp poll)",
     f"nổ {no}")
kiem(len(pg._pipe_exports) == len(cut_jobs) and not pg._pending_export,
     f"cả {len(cut_jobs)} video vẫn được bàn giao xuất đúng 1 lần",
     f"_pipe_exports={len(pg._pipe_exports)}/{len(cut_jobs)}, còn "
     f"{len(pg._pending_export)} job kẹt trong _pending_export")

# ═══════ CA 8: hộp XÁC NHẬN phải báo đúng số khi có video đang bay ═══════
print("\n══ CA 8: hộp xác nhận trước khi chạy — số liệu trung thực ══")
don_sach()
lam_kenh("G0", "Mỹ", 4)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(30)                     # 4 file đã nhận, đang cắt, vẫn nằm trên đĩa

from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton  # noqa: E402

loi_hop = {"txt": None}
goc_dlg_exec = QDialog.exec
goc_msg_exec = QMessageBox.exec


def _dlg_exec(self):             # mở dialog dây chuyền mà không chặn
    return 0


def _msg_exec(self):             # chụp nội dung hộp xác nhận rồi bấm Huỷ
    loi_hop["txt"] = self.text()
    for b in self.buttons():
        if self.buttonRole(b) == QMessageBox.ButtonRole.RejectRole:
            b.click()
            break
    return 0


QDialog.exec = _dlg_exec
QMessageBox.exec = _msg_exec
# Vá ĐÚNG cửa không liên quan: tiền kiểm key AI chặn trước hộp xác nhận (cố ý
# — xem do_run). Sandbox không có key nên phải cho qua để tới được phần đang
# kiểm là SỐ LIỆU của hộp xác nhận.
from app.ai import llm as _llm_mod  # noqa: E402

_goc_cfg = _llm_mod.is_configured
_llm_mod.is_configured = lambda provider=None: True
try:
    pg._pipeline_dialog()
    nut = [b for b in pg._pipe_dlg.findChildren(QPushButton)
           if "Chạy" in b.text()]
    if not nut:
        kiem(False, "tìm được nút ▶ Chạy trong hộp dây chuyền",
             f"chỉ thấy: {[b.text() for b in pg._pipe_dlg.findChildren(QPushButton)]}")
    else:
        nut[0].click()
finally:
    QDialog.exec = goc_dlg_exec
    QMessageBox.exec = goc_msg_exec
    _llm_mod.is_configured = _goc_cfg

txt = loi_hop["txt"] or ""
kiem("4 video" in txt and "đang chạy dở" in txt,
     "hộp xác nhận nói rõ 4 video đang chạy dở, KHÔNG hứa cắt lại",
     f"nội dung hộp: {txt[:300]!r}")
kiem("Sẽ cắt <b>4 video" not in txt,
     "KHÔNG báo sai 'sẽ cắt 4 video' khi cả 4 đang chạy dở",
     f"nội dung hộp: {txt[:300]!r}")

# ═══════ CA 9: HỒI PHỤC sau khi app khởi động lại giữa lúc đang chạy ═══════
# Đúng tình huống anh Hùng gặp 26/07: 72 video nhận, app khởi động lại lúc
# 09:53, 68 video nằm im — gốc còn nguyên, không dòng báo nào.
# Dựng trang MỚI = mất sạch sổ theo dõi trong RAM, y như tắt/mở lại app.
print("\n══ CA 9: hồi phục sau khi khởi động lại app ══")
don_sach()
lam_kenh("H0", "Mỹ", 3)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(30)
cut_jobs = dict(pg._pipe_cut)
# 1 video phân tích XONG (có clip), 1 đang chạy, 1 vẫn chờ
jids = list(cut_jobs)
db.execute("UPDATE jobs SET status='done', progress=100 WHERE id=?", (jids[0],))
for k in range(2):
    db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
               "status) VALUES(?,?,?,?,?,'ready')",
               (cut_jobs[jids[0]]["vid"], k * 0.3, k * 0.3 + 0.4, 0.9, f"P{k}"))
db.execute("UPDATE jobs SET status='running' WHERE id=?", (jids[1],))
t_truoc = db.query("SELECT COUNT(*) n FROM pipeline_files "
                   "WHERE status='taken'")[0]["n"]
goc_con = [Path(c["path"]).exists() for c in cut_jobs.values()]
print(f"  trước khi 'khởi động lại': {t_truoc} dòng taken, "
      f"{sum(goc_con)}/3 video gốc còn trên đĩa")

# ── KHỞI ĐỘNG LẠI: trang mới, sổ RAM trắng ──
pg2 = dung_trang()
print(f"  sau khi mở lại: sổ RAM dõi {so_ctx_dang_theo_doi(pg2)} ctx "
      "(đúng: mất sạch)")
kiem(so_ctx_dang_theo_doi(pg2) == 0,
     "mở lại app thì sổ theo dõi trong RAM trắng (mô phỏng đúng)",
     "sổ không trắng -> ca test không mô phỏng đúng việc khởi động lại")

n = pg2._pipe_resume_taken()
ctx_sau = so_ctx_dang_theo_doi(pg2)
t_sau = db.query("SELECT COUNT(*) n FROM pipeline_files "
                 "WHERE status='taken'")[0]["n"]
print(f"  hồi phục: nối lại {n} video, đang dõi {ctx_sau} ctx, "
      f"còn {t_sau} dòng taken")
kiem(n == 3 and ctx_sau == 3,
     "nối lại ĐỦ 3 video dở (không bỏ sót video nào)",
     f"chỉ nối {n}, dõi {ctx_sau} ctx (mong 3/3)")
kiem(t_sau == ctx_sau,
     "bất biến vàng vẫn giữ: số dòng 'taken' = số ctx đang dõi",
     f"taken={t_sau} nhưng dõi {ctx_sau} ctx")
# Video đã phân tích xong PHẢI được xuất ngay, KHÔNG phân tích lại
job_truoc = db.query("SELECT COUNT(*) n FROM jobs")[0]["n"]
pg2._check_auto_export()
xuat = pg2._pipe_exports.get(cut_jobs[jids[0]]["vid"])
kiem(xuat is not None and bool(xuat["jobs"]),
     "video đã phân tích xong được XUẤT NGAY khi hồi phục",
     f"_pipe_exports cho video đó = {xuat}")
n_auto = db.query("SELECT COUNT(*) n FROM jobs WHERE type IN "
                  "('auto','auto_recap')")[0]["n"]
kiem(n_auto == 3,
     "KHÔNG phân tích lại (vẫn đúng 3 job phân tích, không đốt lượt Groq)",
     f"có {n_auto} job phân tích (mong 3)")

# ── gốc đã bị dọn ở phiên trước -> phải ĐÓNG SỔ, không kẹt mãi ──
don_sach()
lam_kenh("H1", "Mỹ", 1)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(20)
p_goc = Path(list(pg._pipe_cut.values())[0]["path"])
p_goc.unlink()                            # giả lập: gốc đã vào Thùng rác
pg2 = dung_trang()
pg2._pipe_resume_taken()
con = db.query("SELECT COUNT(*) n FROM pipeline_files "
               "WHERE status='taken'")[0]["n"]
kiem(con == 0,
     "gốc đã dọn trước đó -> ĐÓNG SỔ, không để kẹt 'taken' mãi",
     f"còn {con} dòng kẹt 'taken'")

# ═══ CA 10: gốc KẸT (Windows giữ file) phải được THỬ DỌN LẠI thật ═══
# Log thật của anh Hùng 26/07 có dòng "⚠ CHƯA dọn được gốc (file kẹt), sẽ tự
# thử lại lượt sau" — nhưng mark_done chạy vô điều kiện nên seen_before thấy
# 'done' và KHÔNG BAO GIỜ nhận lại: video gốc nằm trong thư mục kênh mãi mãi.
print("\n══ CA 10: video gốc bị kẹt -> phải tự dọn lại được ══")
don_sach()
lam_kenh("K0", "Mỹ", 1)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(20)
ctx = list(pg._pipe_cut.values())[0]
p_goc = Path(ctx["path"])

from app.ui.studio_page import MARK_STUCK  # noqa: E402

# Giả lập đúng hiện trường: Part đã xuất xong, sổ 'done' + dấu GỐC KẸT, gốc còn
P.mark_done(ctx["entry"], video_id=ctx["vid"], note="3 part" + MARK_STUCK)
kiem(p_goc.exists(), "dựng được hiện trường: gốc còn nằm trong thư mục kênh",
     "gốc đã biến mất, ca test vô nghĩa")
# Lượt sau KHÔNG nhận lại (đúng — Part đã xuất rồi, không cắt lại)
pg2 = dung_trang()
pg2._pipe_run()
bom_nhip(10)
nhan_lai = db.query("SELECT COUNT(*) n FROM pipeline_files "
                    "WHERE status='taken'")[0]["n"]
kiem(nhan_lai == 0, "không cắt lại video đã xuất Part (không đốt lượt AI)",
     f"lại nhận {nhan_lai} video nữa")
# ...NHƯNG gốc PHẢI được dọn (đây là chỗ trước đây hứa suông)
con = p_goc.exists()
sach_dau = db.query_one("SELECT note FROM pipeline_files WHERE id=?",
                        (ctx["entry"],))
kiem(not con,
     "gốc kẹt ĐÃ ĐƯỢC DỌN ở lượt sau (không còn nằm lại vĩnh viễn)",
     f"gốc vẫn còn: {p_goc}")
kiem(MARK_STUCK not in (sach_dau["note"] or ""),
     "dọn xong thì BỎ dấu [GỐC KẸT] khỏi sổ",
     f"note vẫn là {sach_dau['note']!r}")

# ═══ CA 11: TẮT hôm nay, MAI mở lại (quá 12 giờ) — phải chạy tiếp ═══
# Câu anh Hùng hỏi 27/07: "đang cắt đang phân tích tôi tắt, mai làm tiếp có
# chạy tiếp không?". Điểm hở: expire_stale_taken(hours=12) đổi dòng 'taken' cũ
# hơn 12 giờ sang 'error' — mà sau khi hồi phục qua đêm, taken_at VẪN LÀ HÔM
# QUA, nên nó đổi luôn cả việc ĐANG ĐƯỢC DÕI: báo cáo sai và file có thể bị
# nhận lại, cắt lần hai, đốt thêm lượt AI. ĐO ĐƯỢC: 3/3 dòng bị đổi sai.
print("\n══ CA 11: tắt hôm nay, mai mở lại (quá 12 giờ) ══")
don_sach()
lam_kenh("Q0", "Mỹ", 3)
pg = dung_trang()
st_q.setValue("pipe_grp_sel", "Mỹ")
st_q.sync()
pg._pipe_run()
bom_nhip(30)
cut = dict(pg._pipe_cut)
js = list(cut)
db.execute("UPDATE jobs SET status='done', progress=100 WHERE id=?", (js[0],))
db.execute("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
           "status) VALUES(?,0.0,0.5,0.9,'C','ready')", (cut[js[0]]["vid"],))
db.execute("UPDATE jobs SET status='canceled' WHERE id=?", (js[1],))
# TẮT APP + tua 13 giờ
db.execute("UPDATE pipeline_files SET taken_at=datetime('now','-13 hours') "
           "WHERE status='taken'")
pg2 = dung_trang()                      # mở lại app hôm sau
n = pg2._pipe_resume_taken()
# v2.6.8 (anh Hùng 30/07: "ấn huỷ rồi mà mở lại nó tự chạy"): video user ĐÃ
# HUỶ (js[1]) KHÔNG được tự chạy lại — chỉ nối 2 video dở thật (done chờ
# xuất + pending). Video huỷ được TRẢ SỔ, gốc giữ nguyên, chờ user tự chạy.
kiem(n == 2, "mở lại app hôm sau NỐI TIẾP đủ 2 video DỞ THẬT "
     "(video đã HUỶ không tự chạy lại)", f"nối {n}, kỳ vọng 2")
pg2._pipe_run()                         # bấm ▶ Chạy -> gọi expire_stale_taken
bom_nhip(30)                            # video huỷ được NHẬN LẠI ở lượt chạy TAY này
n_taken = db.query("SELECT COUNT(*) n FROM pipeline_files "
                   "WHERE status='taken'")[0]["n"]
n_err = db.query("SELECT COUNT(*) n FROM pipeline_files "
                 "WHERE status='error'")[0]["n"]
ctx = so_ctx_dang_theo_doi(pg2)
kiem(n_err == 0,
     "việc đang hồi phục KHÔNG bị đổi sang 'error' dù taken_at là hôm qua",
     f"{n_err} dòng bị đổi oan -> báo cáo sai + có thể cắt lần hai")
kiem(n_taken == ctx, "bất biến vàng vẫn giữ sau khi qua đêm",
     f"taken={n_taken} nhưng dõi {ctx} ctx")
kiem(n_taken == 3, "video huỷ được nhận LẠI khi user CHỦ ĐỘNG bấm ▶ Chạy",
     f"taken={n_taken}, kỳ vọng 3 (2 nối + 1 nhận lại)")

# ───────────────────────── kết ─────────────────────────
for k, v in _saved.items():
    if v is None:
        st_q.remove(k)
    else:
        st_q.setValue(k, v)
st_q.sync()
print("\n" + "=" * 62)
if FAIL:
    print(f"❌ {len(FAIL)} LỖI:")
    for f in FAIL:
        print("   -", f)
else:
    print("✅ TẤT CẢ ĐẠT")
print("=" * 62)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
