"""CỔNG 103 — HẾT LƯỢT AI GIỮA CHỪNG THÌ ĐỢI RỒI PHÂN TÍCH LẠI (01/11/2026).

Anh Hùng (ảnh thanh vàng «0 Part», không một dòng báo lỗi): khi mọi key Groq
cùng hồi lượt, vài lượt gọi con hết ngân sách đợi rồi thất bại; video vẫn được
chốt 'xong' với 0 Part, hoặc 3 Part chọn từ NỬA video. Đo trên máy thật lúc đó:
68 key = 34 bị Groq khoá hẳn (organization_restricted, 30/09-05/10) + 34 key
đang hồi lượt 1-25 phút.

Canh:
  1. `_cut_vi_het_luot`: phân biệt "thiếu vì hết lượt" với key chết hẳn /
     AI trả sai định dạng / phân tích đầy đủ (KHÔNG được đợi oan).
  2. `_doi_luot_roi_lam_lai` đợi rồi ném `DoiLuotAI`, Huỷ thoát được ngay.
  3. Bộ điều phối THẬT + DB THẬT (sandbox): job ném `DoiLuotAI` 4 lần liền vẫn
     KHÔNG thành 'failed' (không ăn lượt thử 3), lần 5 xong 'done'.
  4. Lỗi thường vẫn ăn lượt thử như cũ -> 'failed' sau 3 lần (không sửa quá tay).
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
HOP = Path(tempfile.mkdtemp(prefix="bq_test_hetluot_"))
os.environ["BQ_DATA_DIR"] = str(HOP)
os.environ["BQ_DB_PATH"] = str(HOP / "s.db")
sys.path.insert(0, str(GOC))
import _test_guard  # noqa: E402,F401

from app.modules import m1_highlight as m  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi=""):
    global DAT, HONG
    DAT, HONG = (DAT + 1, HONG) if dk else (DAT, HONG + 1)
    print(("  ĐẠT  " if dk else "  HỎNG ") + ten + (f" — {chi}" if chi else ""))


print("CỔNG 103 — hết lượt AI giữa chừng thì đợi rồi phân tích lại")
print("\n1. Nhận diện đúng nguyên nhân")
LOI_THAT = ("AI chọn 0/3 Part: phân tích chưa đầy đủ; chưa thể kết luận video thiếu đoạn hay — "
            "AI xem hình chọn đoạn lỗi: groq/AI chat: Chưa xử lý được bằng các key đã cấu hình. "
            "Tổng 68 key: 34 bị hạn chế, 0 sai")


def kq(note, complete=False, **sel):
    return {"selection_note": note, "selection": dict(analysis_complete=complete, **sel)}


ok(m._cut_vi_het_luot(kq(LOI_THAT), {}), "lời lỗi THẬT trên máy anh Hùng (0 Part) -> đợi")
ok(m._cut_vi_het_luot(kq("AI chọn 3/3 Part: phân tích chưa đầy đủ"),
                      {"chunk_errors": ["LLMError: 429: Groq shared cooldown; retry in 80s"]}),
   "chép lời từng phần lỗi 429 (3 Part từ NỬA video) -> đợi")
ok(m._cut_vi_het_luot(kq("Mạch chuyện: Hậu kiểm chưa hoàn tất: ... 429 ...", complete=True,
                         continuity_incomplete=True), {}),
   "phân tích đủ nhưng hậu kiểm hụt vì 429 -> đợi")
ok(not m._cut_vi_het_luot(kq("đã chọn đủ", complete=True), {}), "phân tích ĐẦY ĐỦ -> không đợi")
ok(not m._cut_vi_het_luot(kq("phân tích chưa đầy đủ"), {"chunk_errors": ["AI trả danh sách clip sai định dạng"]}),
   "AI trả sai định dạng (không phải hết lượt) -> không đợi")
ok(not m._cut_vi_het_luot(kq("organization_restricted: groq/AI chat: Chưa xử lý được bằng các key "
                             "đã cấu hình. Tổng 68 key: 68 bị hạn chế, 0 sai key, 0 không bị đánh dấu chặn."), {}),
   "MỌI key bị khoá hẳn -> KHÔNG đợi vô hạn")

_soon = m.llm.soonest_ready_wait
m.llm.soonest_ready_wait = lambda *a, **k: 300.0
ok(m._cut_vi_het_luot(kq("critic lỗi hoặc trả sai định dạng", complete=True, critic_incomplete=True), {}),
   "lỗi KHÔNG ghi 429 nhưng lúc đó mọi key đang hồi lượt -> đợi")
m.llm.soonest_ready_wait = lambda *a, **k: 0.0
ok(not m._cut_vi_het_luot(kq("critic lỗi hoặc trả sai định dạng", complete=True, critic_incomplete=True), {}),
   "lỗi định dạng khi CÒN key rảnh -> không đợi")
m.llm.soonest_ready_wait = _soon
m._VONG_DOI.clear()
vong = [m._con_vong_doi(999) for _ in range(m._VONG_DOI_TOI_DA + 1)]
ok(all(vong[:-1]) and not vong[-1], f"trần {m._VONG_DOI_TOI_DA} vòng đợi/video rồi chốt (không quay mãi)")

print("\n1b. Nghỉ key tối đa 5 phút + xoay key lâu chưa dùng")
from app.ai import llm as L  # noqa: E402
w = L.mark_limited("groq", "gsk_thu_tran", "Rate limit ... tokens per day (TPD): ... Please try again in 22m27.84s")
ok(w <= 300.0, "lỗi TPD 'thử lại sau 22 phút' -> chỉ nghỉ tối đa 300 s", f"{w:.0f}s")
w2 = L.mark_limited("groq", "gsk_thu_tran2", "429 ... Please try again in 12.5s")
ok(abs(w2 - 12.5) < 0.01, "lỗi theo phút 12,5 s -> nghỉ đúng 12,5 s (không kéo dài)", f"{w2}")
_ks = [f"gsk_xoay{i}" for i in range(4)]
_seq = []
for _ in range(6):
    _k = L.pick_keys("groq", _ks)[0]
    L.mark_used("groq", _k)
    _seq.append(_k[-1])
ok("".join(_seq) == "012301", "lượt gọi liên tiếp XOAY qua các key rảnh (không dồn 1 key)", "".join(_seq))

print("\n2. Đợi rồi ném, Huỷ thoát ngay")
m.llm.soonest_ready_wait = lambda *a, **k: 0.0
_cu = m._doi_luot_roi_lam_lai.__globals__["time"]


class _NhanhTime:
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += s


nt = _NhanhTime()
m.time = nt
tin = []


class _Ctx:
    def check_canceled(self):
        pass

    def progress(self, p, msg=""):
        tin.append(msg)


try:
    m._doi_luot_roi_lam_lai(_Ctx(), "x")
    ok(False, "phải ném DoiLuotAI")
except m.DoiLuotAI as e:
    ok(getattr(e, "doi_luot", False), "ném DoiLuotAI mang cờ doi_luot")
ok(any("hết lượt AI" in t for t in tin), "có báo tiến trình đang đợi", tin[0][:60] if tin else "")
ok(nt.t - 1000.0 >= 20.0, "đợi tối thiểu 20s (không quay vòng đốt lượt)", f"{nt.t - 1000:.0f}s")


class _Huy(Exception):
    pass


class _CtxHuy(_Ctx):
    def check_canceled(self):
        raise _Huy()


try:
    m._doi_luot_roi_lam_lai(_CtxHuy(), "x")
    ok(False, "Huỷ phải thoát")
except _Huy:
    ok(True, "bấm Huỷ lúc đang đợi -> thoát ngay")
m.time = _cu

print("\n3-4. Bộ điều phối THẬT")
from app.database import db  # noqa: E402
from app.queue import worker as W  # noqa: E402
from app.queue.resource_manager import PROFILE, profile_dict  # noqa: E402

dem = {"a": 0, "b": 0}


def _job_a(payload, ctx):
    dem["a"] += 1
    if dem["a"] <= 4:
        raise m.DoiLuotAI("Hết lượt AI giữa chừng")
    return {"selection_note": "xong"}


def _job_b(payload, ctx):
    dem["b"] += 1
    raise RuntimeError("lỗi thường")


W.register_handler("_t_a", _job_a)
W.register_handler("_t_b", _job_b)
pool = W.WorkerPool(profile_dict(PROFILE), max_cpu=2, max_gpu=0, poll_interval=0.05)
ja = pool.enqueue("_t_a", {}, max_attempts=3)
jb = pool.enqueue("_t_b", {}, max_attempts=3)
pool.start()
t0 = time.time()
while time.time() - t0 < 30:
    ra = db.query_one("SELECT status FROM jobs WHERE id=?", (ja,))["status"]
    rb = db.query_one("SELECT status FROM jobs WHERE id=?", (jb,))["status"]
    if ra in ("done", "failed") and rb in ("done", "failed"):
        break
    time.sleep(0.1)
pool.stop()
ra = db.query_one("SELECT status, attempts FROM jobs WHERE id=?", (ja,))
rb = db.query_one("SELECT status, attempts FROM jobs WHERE id=?", (jb,))
ok(ra["status"] == "done" and dem["a"] == 5,
   "hết lượt 4 lần liền vẫn KHÔNG 'failed', lần 5 xong", f"{ra['status']} sau {dem['a']} lần")
ok(rb["status"] == "failed" and dem["b"] == 3,
   "lỗi thường vẫn ăn lượt thử như cũ (failed sau 3 lần)", f"{rb['status']} sau {dem['b']} lần")

print("\n5. Mở app: tự nhận lại video vàng còn trong thư mục kênh")
import json  # noqa: E402
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402
_qa = QApplication.instance() or QApplication([])
from app.ui import studio_page as SP  # noqa: E402

kenh = HOP / "kenh"
kenh.mkdir()
pid = db.insert("INSERT INTO projects (name, assets_dir, pipe_on, pipe_src) VALUES (?,?,1,?)",
                ("K", str(HOP / "a"), str(kenh)))
pid_tat = db.insert("INSERT INTO projects (name, assets_dir, pipe_on) VALUES (?,?,0)", ("Ktat", str(HOP / "b")))


def video(ten, p, res, co_file=True, so=None):
    f = kenh / ten
    if co_file:
        f.write_bytes(b"x" * 10)
    v = db.insert("INSERT INTO videos (project_id, src_path, file_hash) VALUES (?,?,?)", (p, str(f), "h" + ten))
    db.execute("INSERT INTO jobs (type, project_id, video_id, payload, status, result, finished_at) "
               "VALUES ('auto',?,?,'{}','done',?,datetime('now'))", (p, v, json.dumps(res)))
    if so:
        db.execute("INSERT INTO pipeline_files (project_id, file_name, file_hash, video_id, status, taken_at) "
                   "VALUES (?,?,?,?,?,datetime('now'))", (p, ten, "h" + ten, v, so))
    return v


VANG = {"count": 0, "selection": {"analysis_complete": False}}
CUT3 = {"count": 3, "selection": {"analysis_complete": False}}
TOT = {"count": 3, "selection": {"analysis_complete": True}}
v1 = video("vang0.mp4", pid, VANG)
v2 = video("cut3.mp4", pid, CUT3)
video("tot.mp4", pid, TOT)
video("mat_goc.mp4", pid, VANG, co_file=False)
video("dang_lam.mp4", pid, VANG, so="taken")
video("kenh_tat.mp4", pid_tat, VANG)
sp = SP.StudioPage.__new__(SP.StudioPage)
QWidget.__init__(sp)
sp._pipe_cut, sp._pipe_by_vid, sp._pipe_exports, sp._pipe_intake_q = {}, {}, {}, []
nhat = []
sp._pipe_log = lambda m: None
sp._pipe_root = lambda: ""
sp._pipe_take = lambda p, name, mode, path: nhat.append(Path(path).name) or True
n = sp._pipe_nhan_lai_vang()
ok(sorted(nhat) == ["cut3.mp4", "vang0.mp4"],
   "chỉ nhận lại video CỤT còn gốc, kênh bật, chưa có sổ", str(sorted(nhat)))
ok(n == 2, "trả đúng số video nhận lại", str(n))

print("\n6. File Part ghi dở (tắt app giữa lúc xuất) không còn nằm lại")
import subprocess  # noqa: E402
from config import settings as _st  # noqa: E402
goc = HOP / "video my"
k1 = goc / "kenh 1"
k1.mkdir(parents=True)
lanh = k1 / "Part 1 Lanh.mp4"
subprocess.run([_st.FFMPEG_PATH, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=160x120:d=1",
                "-c:v", "libx264", str(lanh)], check=True)
hong = k1 / "Part 1 Hong.mp4"
hong.write_bytes(b"\x00" * 5000)
co_chu = k1 / "Part 2 CoChu.mp4"
co_chu.write_bytes(lanh.read_bytes())
db.execute("INSERT INTO clips (video_id, start_sec, end_sec, status, export_path) VALUES (?,?,?,?,?)",
           (v1, 0, 1, "exported", str(co_chu)))
dt_chet = k1 / ("_dt_999999_" + hong.name)
dt_chet.write_bytes(b"x")
ok(m._file_hong(hong) and not m._file_hong(lanh), "nhận ra file ghi dở (thiếu moov) vs file lành")
ok(m._file_mo_coi(hong), "file HỎNG -> mồ côi")
ok(m._file_mo_coi(lanh), "file lành mà KHÔNG clip nào nhận -> mồ côi (bản ghi dở của lượt bị ngắt)")
ok(not m._file_mo_coi(co_chu), "file lành CÓ clip trong DB nhận -> KHÔNG đụng (Part của video khác)")
m._cat_file_mo_coi(hong)
cat = goc / "_Loi" / "part_hong" / "kenh 1"
ok(not hong.exists() and (cat / hong.name).exists(), "file hỏng được CẤT (không xoá) vào _Loi/part_hong")
ok(not dt_chet.exists() and (cat / dt_chet.name).exists(), "file tạm _dt_ của tiến trình đã chết cũng được cất")
ok(co_chu.exists() and lanh.exists(), "file khác trong thư mục kênh không bị đụng")

import shutil  # noqa: E402
shutil.rmtree(HOP, ignore_errors=True)
print(f"\nKETQUA: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
