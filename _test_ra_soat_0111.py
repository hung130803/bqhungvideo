"""CỔNG 104 — RÀ SOÁT TOÀN BỘ 01/11/2026 (ghi file · dây chuyền · bot · AI/key).

Anh Hùng: "rà soát cả bot cả phần mềm xem còn trường hợp nào có thể xảy ra lỗi,
test fix luôn 1 thể". 4 mảng rà song song ra ~45 điểm; cổng này canh các điểm
ĐÃ SỬA, mỗi mục = 1 tình huống lỗi thật:

  A. GHI FILE: Part xuất qua file tạm `_xuat_<pid>_…` rồi mới đổi tên (tắt app
     giữa chừng không để file dở mang tên thật; "Xuất lại" không phá bản tốt);
     file cùng tên mồ côi/hỏng được cất, tên được dùng lại; file của Part khác
     thì giữ; dây chuyền bỏ qua file tạm của app + file ghép dở của yt-dlp;
     dọn gốc chỉ khi Part MỞ ĐƯỢC; .env ghi nguyên tử.
  B. DÂY CHUYỀN: mở app không nhận lại video đã có Part xuất / video ngoài thư
     mục kênh / 0 Part do video ngắn; Huỷ lúc dựng lệnh xuất = gỡ sổ (không
     phải lỗi); 0 Part thật = đóng sổ (không lặp); "Xóa lịch sử" giữ job của
     video đang chạy dây chuyền.
  C. AI/KEY: trần nghỉ 5 phút CHỈ cho chat; key vừa dùng < 60 s xếp sau; hết
     làn chung = lỗi tạm; 413 không phải hết lượt; bộ đếm vòng đợi ghi đĩa.
  D. BOT: đếm video chờ khớp dây chuyền (pipe_daily=1 = không giới hạn, 'dup'
     không tính, file đang tải không tính, kênh dùng <gốc>/<tên>); job kẹt vòng
     đợi (lời đếm ngược) vẫn bị phát hiện; "HẾT hàng chờ" cần 2 lượt rỗng và DB
     không hỏng.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
HOP = Path(tempfile.mkdtemp(prefix="bq_test_rasoat_"))
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "s.db")
os.environ["BQ_QSETTINGS_INI"] = str(HOP / "qs.ini")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(GOC))
import _test_guard  # noqa: E402,F401

from config import settings  # noqa: E402
from app.database import db  # noqa: E402
from app.modules import m1_highlight as m  # noqa: E402
from app.core import pipeline as P  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi=""):
    global DAT, HONG
    DAT, HONG = (DAT + 1, HONG) if dk else (DAT, HONG + 1)
    print(("  ĐẠT  " if dk else "  HỎNG ") + ten + (f" — {chi}" if chi else ""))


F = settings.FFMPEG_PATH
SRC = HOP / "goc.mp4"
subprocess.run([F, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=8",
                "-f", "lavfi", "-i", "sine=f=440:d=8", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(SRC)], check=True)


class Ctx:
    profile = {"encoder": "libx264"}
    job_id = 0

    def progress(self, p, msg=""):
        pass

    def check_canceled(self):
        pass


kenh = HOP / "goc_kenh" / "kenh 1"
kenh.mkdir(parents=True)
pid = db.insert("INSERT INTO projects (name, assets_dir, pipe_on, pipe_src) VALUES (?,?,1,?)",
                ("kenh 1", str(HOP / "a"), str(kenh)))
vid = db.insert("INSERT INTO videos (project_id, src_path, duration, file_hash) VALUES (?,?,?,?)",
                (pid, str(SRC), 8.0, "hgoc"))


def clip(a=1.0, b=6.0):
    return db.insert("INSERT INTO clips (video_id,start_sec,end_sec,status,signals) VALUES (?,?,?,?,?)",
                     (vid, a, b, "suggested", json.dumps({"segments": [[a, b]]})))


def xuat(cid, ten):
    return m.export_clip({"clip_id": cid, "video_id": vid, "out_dir": str(kenh), "flat": True,
                          "out_name": ten, "part_no": 1, "hieu_ung": "tat"}, Ctx())


def dur(p):
    from app.core.ffmpeg_utils import probe
    return probe(str(p)).duration


print("CỔNG 104 — rà soát toàn bộ 01/11/2026")
print("\nA. Ghi file")
c1 = clip()
r = xuat(c1, "Part 1 Thu")
dich = kenh / "Part 1 Thu.mp4"
ok(Path(r["export_path"]) == dich and dur(dich) > 4, "xuất ra ĐÚNG tên thật, mở được", r["export_path"][-20:])
ok(not any(f.name.startswith("_xuat_") for f in kenh.iterdir()), "không để file tạm _xuat_ lại")
ok(db.query_one("SELECT export_path FROM clips WHERE id=?", (c1,))["export_path"] == str(dich),
   "DB ghi đường dẫn TÊN THẬT (không phải file tạm)")

# Xuất lại bị NGẮT giữa chừng: bản tốt cũ phải còn nguyên.
import hashlib  # noqa: E402
md5_cu = hashlib.md5(dich.read_bytes()).hexdigest()
from app.core import ffmpeg_utils as FU  # noqa: E402
_goc_dt = FU.chuan_do_to_clip


def _ngat(*a, **k):
    raise m.CanceledError()


FU.chuan_do_to_clip = _ngat
try:
    xuat(c1, "Part 1 Thu")
    ok(False, "phải ném huỷ")
except m.CanceledError:
    pass
FU.chuan_do_to_clip = _goc_dt
ok(hashlib.md5(dich.read_bytes()).hexdigest() == md5_cu,
   "'Xuất lại' bị ngắt giữa chừng -> bản Part TỐT cũ còn nguyên từng byte")
tam = [f for f in kenh.iterdir() if f.name.startswith("_xuat_")]
ok(all(P.is_tmp_file(f.name) for f in tam), "file tạm bị bỏ lại (nếu có) được dây chuyền coi là TẠM",
   f"{len(tam)} file")
for f in tam:
    f.unlink()

# file cùng tên HỎNG (lượt trước bị tắt app) -> cất đi, dùng lại đúng tên
hong = kenh / "Part 1 Hong.mp4"
hong.write_bytes(b"\x00" * 4000)
c2 = clip(2.0, 6.5)
r2 = xuat(c2, "Part 1 Hong")
ok(Path(r2["export_path"]).name == "Part 1 Hong.mp4" and dur(r2["export_path"]) > 3,
   "file cùng tên HỎNG -> ghi lại đúng tên (không đẻ ' (2)')")
ok((kenh.parent / "_Loi" / "part_hong" / "kenh 1" / "Part 1 Hong.mp4").exists(),
   "file hỏng được CẤT vào _Loi/part_hong (không xoá)")

# file cùng tên của Part KHÁC (DB nhận) -> giữ, đặt (2)
c3 = clip(1.5, 6.0)
r3 = xuat(c3, "Part 1 Thu")
ok(Path(r3["export_path"]).name == "Part 1 Thu (2).mp4" and dich.exists(),
   "file cùng tên CỦA PART KHÁC -> giữ nguyên, Part mới đặt ' (2)'")

ok(all(P.is_tmp_file(n) for n in ("_xuat_123_9_1.mp4", "_dt_123_Part 1 x.mp4", "video.temp.mp4",
                                  "video.mp4.part-Frag3")),
   "dây chuyền bỏ qua file tạm của app + file ghép dở của yt-dlp")
ok(not P.is_tmp_file("Video hay.mp4"), "video thường KHÔNG bị coi là tạm")

from app.core.pipeline_safety import parts_problem  # noqa: E402
vid2 = db.insert("INSERT INTO videos (project_id, src_path, duration) VALUES (?,?,?)", (pid, str(SRC), 8.0))
bad = kenh / "Part 9 Bad.mp4"
bad.write_bytes(b"\x00" * 3000)
db.execute("INSERT INTO clips (video_id,start_sec,end_sec,status,export_path) VALUES (?,?,?,?,?)",
           (vid2, 0, 1, "exported", str(bad)))
db.execute("INSERT INTO jobs (type, video_id, payload, status) VALUES ('m1_export_clip',?,?,'done')",
           (vid2, json.dumps({"clip_id": db.query_one("SELECT MAX(id) m FROM clips")["m"]})))
ok(bool(parts_problem(vid2)), "Part có file nhưng KHÔNG MỞ ĐƯỢC -> giữ video gốc", parts_problem(vid2)[:40])

import config as CFG  # noqa: E402
CFG.update_env({"BQ_THU_KHOA": "1"})
CFG.update_env({"BQ_THU_KHOA": "2"})
envf = Path(os.environ["BQ_DATA_DIR"]) / ".env"
ok(envf.read_text(encoding="utf-8").count("BQ_THU_KHOA=2") == 1 and
   (envf.with_name(".env.bak")).exists() and not envf.with_name(".env.tmp").exists(),
   ".env ghi nguyên tử (có .env.bak, không để .env.tmp)")

print("\nB. Dây chuyền")
from app import services as SV  # noqa: E402
vb = db.insert("INSERT INTO videos (project_id, src_path) VALUES (?,?)", (pid, str(SRC)))
db.execute("INSERT INTO pipeline_files (project_id,file_name,file_hash,video_id,status,taken_at) "
           "VALUES (?,?,?,?,'taken',datetime('now'))", (pid, "x.mp4", "hx", vb))
jg = db.insert("INSERT INTO jobs (type, video_id, payload, status) VALUES ('m1_export_clip',?,'{}','done')", (vb,))
jx = db.insert("INSERT INTO jobs (type, video_id, payload, status) VALUES ('m1_export_clip',NULL,'{}','done')")
SV.clear_finished_jobs()
ok(db.query_one("SELECT 1 FROM jobs WHERE id=?", (jg,)) and not db.query_one("SELECT 1 FROM jobs WHERE id=?", (jx,)),
   "'Xóa lịch sử' GIỮ job của video dây chuyền đang làm, xoá job khác")

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402
_qa = QApplication.instance() or QApplication([])
from app.ui import studio_page as SP  # noqa: E402
sp = SP.StudioPage.__new__(SP.StudioPage)
QWidget.__init__(sp)
sp._pipe_cut, sp._pipe_by_vid, sp._pipe_exports, sp._pipe_intake_q = {}, {}, {}, []
log = []
sp._pipe_log = lambda s: log.append(s)
sp._pipe_root = lambda: ""
for loi, mong in (("Đã hủy", None), ("Không có clip để xuất sau phân tích", "done"), ("mẫu hỏng", "error")):
    e = db.insert("INSERT INTO pipeline_files (project_id,file_name,status,taken_at) VALUES (?,?, 'taken', datetime('now'))",
                  (pid, f"f_{loi[:3]}.mp4"))
    sp._pipe_by_vid[777] = {"entry": e, "name": "K", "file": "f.mp4", "vid": 777}
    sp._pipe_on_export_failed(777, loi)
    row = db.query_one("SELECT status FROM pipeline_files WHERE id=?", (e,))
    ok((row is None) if mong is None else (row and row["status"] == mong),
       f"lỗi dựng xuất '{loi[:20]}' -> sổ {'GỠ (huỷ)' if mong is None else mong}")

# nhận lại video vàng: chỉ video cụt, trong thư mục kênh, chưa có Part xuất
def vang(ten, sel, trong_kenh=True, co_part=False):
    f = (kenh if trong_kenh else HOP) / ten
    f.write_bytes(b"x" * 10)
    v = db.insert("INSERT INTO videos (project_id, src_path, file_hash) VALUES (?,?,?)", (pid, str(f), "h" + ten))
    db.execute("INSERT INTO jobs (type, project_id, video_id, payload, status, result, finished_at) "
               "VALUES ('auto',?,?,'{}','done',?,datetime('now'))", (pid, v, json.dumps(sel)))
    if co_part:
        db.execute("INSERT INTO clips (video_id,start_sec,end_sec,status) VALUES (?,0,1,'exported')", (v,))


CUT = {"count": 0, "selection": {"analysis_complete": False}}
vang("cut.mp4", CUT)
vang("ngoai.mp4", CUT, trong_kenh=False)
vang("co_part.mp4", CUT, co_part=True)
vang("ngan.mp4", {"count": 0})
nhan = []
sp._pipe_take = lambda p_, n_, md, path: nhan.append(Path(path).name) or True
sp._pipe_nhan_lai_vang()
ok(nhan == ["cut.mp4"], "mở app chỉ nhận lại video CỤT trong thư mục kênh, chưa có Part xuất", str(nhan))

print("\nC. AI / key")
from app.ai import llm as L  # noqa: E402
ok(L.mark_limited("groq", "gsk_c1", "tokens per day ... try again in 22m27s", scope="chat") <= 300,
   "lượt CHAT hết hạn mức ngày -> nghỉ tối đa 5 phút")
ok(L.mark_limited("groq", "gsk_c2", "audio seconds per hour ... try again in 22m27s",
                  scope="transcription") > 1000, "lượt CHÉP LỜI giữ thời gian nghỉ Groq báo (không thử lại phí)")
_ks = [f"gsk_r{i}" for i in range(3)]
L.mark_used("groq", "gsk_r0")
ok(L.pick_keys("groq", _ks)[0] != "gsk_r0", "key vừa dùng < 60 giây xếp SAU key khác")
ok(L.is_transient_error("Groq đang bận với video khác; đã giữ tiến độ"), "hết làn gọi chung = lỗi TẠM (thử lại)")
ok(not m._cut_vi_het_luot({"selection_note": "x", "selection": {"analysis_complete": False}},
                          {"chunk_errors": ["Error code: 413 - Request too large ... rate_limit_exceeded"]}),
   "lỗi 413 QUÁ LỚN không bị coi là hết lượt (không đợi vô ích)")
m._xoa_vong_doi(4242)
m._con_vong_doi(4242)
m._VONG_DOI.clear()
ok(m._doc_vong_doi().get("4242") == 1, "bộ đếm vòng đợi GHI ĐĨA (mở lại app không reset)")
m._xoa_vong_doi(4242)
ok("4242" not in m._doc_vong_doi(), "chốt kết quả -> xoá bộ đếm")

print("\nD. Bot")
from app.core import tele_bot as T  # noqa: E402
kb = HOP / "goc_kenh" / "kenh B"
kb.mkdir()
pidb = db.insert("INSERT INTO projects (name, assets_dir, pipe_on, pipe_daily) VALUES (?,?,1,1)",
                 ("kenh B", str(HOP / "b")))
from app.ui.appsettings import app_settings  # noqa: E402
app_settings().setValue("pipe_root", str(HOP / "goc_kenh"))
old = time.time() - 120
for n_ in ("a.mp4", "b.mp4", "dup.mp4"):
    (kb / n_).write_bytes(b"v" * 100)
    os.utime(kb / n_, (old, old))
(kb / "dang_tai.mp4").write_bytes(b"v" * 100)
db.execute("INSERT INTO pipeline_files (project_id,file_name,status,taken_at) VALUES (?,?,?,datetime('now'))",
           (pidb, "a.mp4", "done"))
db.execute("INSERT INTO pipeline_files (project_id,file_name,status,taken_at) VALUES (?,?,?,datetime('now'))",
           (pidb, "dup.mp4", "dup"))
c = T.dem_cho_nhan(ttl=0)
ok(c["video"] >= 1 and c["het_suat"] == 0,
   "pipe_daily=1 (mặc định) = KHÔNG giới hạn: không báo 'đợi mai'", str(c))
ok(c["con_suat"] == c["video"] and "b.mp4" and c["loi"] == 0,
   "kênh dùng <gốc>/<tên> vẫn đếm; 'dup' + file đang tải KHÔNG tính", str(c))


class _Pool:
    def dang_tam_dung(self):
        return False

    def _lane_limit(self, x):
        return 1

    def _lane_limit_tg(self):
        return 1


b = T.BotQuanLy.__new__(T.BotQuanLy)
b.__init__("x:y", set(), _Pool())
b._lan_dau = False
b._co_viec = True
_tq = T.tong_quan
T.tong_quan = lambda: {"pending": 0, "running": 0, "hom_nay": {}, "cho": {}, "tb": {}, "chay": [],
                       "loi": [], "so": {}, "corrupt": False}
T.goi_dang_nhan = lambda: 0
t1 = b.soi_mot_lan(now=1000.0)
t2 = b.soi_mot_lan(now=1030.0)
ok(not any("HẾT" in x or "Hết việc" in x for x in t1) and any("HẾT" in x or "Hết việc" in x for x in t2),
   "'HẾT hàng chờ' chỉ báo sau 2 lượt soi rỗng liền nhau")
b._co_viec, b._rong_dem = True, 0
T.tong_quan = lambda: {"pending": 0, "running": 0, "hom_nay": {}, "cho": {}, "tb": {}, "chay": [],
                       "loi": [], "so": {}, "corrupt": True}
t3 = b.soi_mot_lan(now=2000.0) + b.soi_mot_lan(now=2030.0)
ok(not any("HẾT hàng chờ" in x for x in t3), "DB hỏng -> KHÔNG báo 'HẾT' giả")
job = {"id": 5, "progress": 0.86, "message": "⏳ mọi key AI đang hồi lượt — đợi 37s rồi phân tích tiếp",
       "type": "auto", "kenh": "K", "src": "x.mp4"}
T.tong_quan = lambda: {"pending": 0, "running": 1, "hom_nay": {}, "cho": {}, "tb": {}, "chay": [dict(job)],
                       "loi": [], "so": {}, "corrupt": False}
b.soi_mot_lan(now=3000.0)
job["message"] = job["message"].replace("37", "12")
tk = b.soi_mot_lan(now=3000.0 + T.KET_PHUT * 60 + 5)
ok(any("đợi lượt" in x for x in tk), "job kẹt vòng đợi (lời đếm ngược đổi số) vẫn bị báo")
T.tong_quan = _tq

import shutil  # noqa: E402
shutil.rmtree(HOP, ignore_errors=True)
print(f"\nKETQUA: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
