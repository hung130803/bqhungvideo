# -*- coding: utf-8 -*-
"""CỔNG 117 — CHỌN ĐOẠN BẰNG AGENT MUSE (Meta) QUA CLI RỜI, MẶC ĐỊNH TẮT.

Không mạng, không tài khoản thật: dùng một CLI GIẢ (script python viết ra hộp
cát) nói ĐÚNG khuôn của `muse-ai` thật (đọc từ muse_ai/cli.py + client.py của
github.com/minhquan130599/MuseAI-API): `--state-dir D` đứng TRƯỚC lệnh con;
`upload` in đường dẫn từ xa; `generate` không ra video thì ném
"TimeoutError: No new Muse video appeared within 15s for session S" (mã 1);
`history` in JSON.

Mệnh đề canh:
  1. cờ TẮT -> 0 lượt gọi CLI, Groq chạy y như cũ;
  2. thiếu CLI / chưa đăng nhập / ping hỏng -> rơi về Groq;
  3. JSON tốt -> clip đi qua _normalize_clip/_trim_junk_edges: đủ Min/Max,
     không vượt số Part, đánh dấu ai_nguon=muse, Groq 0 lượt;
  4. trả lời hỏng / trễ quá hạn -> rơi về Groq;
  5. Huỷ lúc đang đợi -> CanceledError nổi lên, không rơi Groq;
  6. bản nhẹ dựng bằng ffmpeg thật: cao 480, 2 khung/giây, tiếng mono;
  7. log không chứa cookie; dọn thư mục tạm + gọi delete từ xa khi CLI có.
"""
import ast
import re
import shutil
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
# Dọn hộp cát của lượt TRƯỚC: SQLite còn giữ s.db lúc thoát nên lượt dọn
# cuối file (rmtree ignore_errors) để lại thư mục. Chỉ đụng tên khớp tiền tố
# và cũ hơn 10 phút (lượt khác đang chạy song song thì không đụng).
for _cu in Path(tempfile.gettempdir()).glob("bq_test_muse_*"):
    try:
        if _cu.is_dir() and time.time() - _cu.stat().st_mtime > 600:
            shutil.rmtree(_cu, ignore_errors=True)
    except OSError:
        pass
TMP = Path(tempfile.mkdtemp(prefix="bq_test_muse_"))
os.environ["BQ_DATA_DIR"] = str(TMP)
os.environ["BQ_DB_PATH"] = str(TMP / "s.db")
for k in list(os.environ):
    if k.startswith("MUSE_"):
        os.environ.pop(k)

from app.ai import llm, muse_agent  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402
from app.queue.worker import CanceledError  # noqa: E402
from config import settings  # noqa: E402

CFG = type(settings)
DAT = HONG = 0


def ok(dk, ten, ct=""):
    global DAT, HONG
    DAT, HONG = DAT + bool(dk), HONG + (not dk)
    print(("  ĐẠT " if dk else "  HỎNG ") + ten + ("" if dk else f"  << {ct}"))


# ───────── CLI GIẢ ─────────
FAKE_DIR = TMP / "fake"
FAKE_DIR.mkdir()
FAKE = FAKE_DIR / "fake_muse.py"
FAKE.write_text(r'''# -*- coding: utf-8 -*-
import json, os, re, shutil, sys
D = os.environ["FAKE_MUSE_DIR"]; MODE = os.environ.get("FAKE_MUSE_MODE", "tot")
a = sys.argv[1:]
sd = None
if a[:1] == ["--state-dir"]:
    sd = a[1]; a = a[2:]
with open(os.path.join(D, "calls.txt"), "a", encoding="utf-8") as f:
    f.write(json.dumps(a[:1] + [x[:60] for x in a[1:3]]) + "\n")
with open(os.path.join(D, "calls_tk.txt"), "a", encoding="utf-8") as f:
    f.write(json.dumps([os.path.basename(sd or ""), a[0] if a else ""]) + "\n")
if sd and os.path.basename(sd) in os.environ.get("FAKE_TK_HONG", "").split(",") and a[:1] and a[0] in ("ping", "upload"):
    sys.stderr.write("muse_ai.errors.MuseAuthError: HTTP 401 login required\n"); sys.exit(1)
if sd and os.path.basename(sd) in os.environ.get("FAKE_TK_HONG_UP", "").split(",") and a[:1] == ["upload"]:
    sys.stderr.write("muse_ai.errors.MuseAuthError: HTTP 401 login required\n"); sys.exit(1)
if a[:1] == ["login"]:
    sys.stdout.write("OTP sent\nMuse OTP: "); sys.stdout.flush()
    code = sys.stdin.readline().strip()
    if code == "123456":
        os.makedirs(sd, exist_ok=True)
        open(os.path.join(sd, "cookies.json"), "w").write("{}")
        print("Login validated. Saved session"); sys.exit(0)
    sys.stderr.write("MuseAuthError: invalid OTP\n"); sys.exit(1)
cmd = a[0] if a else ""
if cmd == "--help":
    subs = "login,ping,model,history,generate,upload" + ("" if MODE == "khong_xoa" else ",delete")
    print("usage: muse-ai [-h] [--state-dir STATE_DIR] {" + subs + "} ..."); sys.exit(0)
if cmd == "ping":
    if MODE == "sai_ping":
        sys.stderr.write("Cookie: abc_SECRET123\nRuntimeError: 401\n"); sys.exit(1)
    print("HTTP 200"); print("{}"); sys.exit(0)
if cmd == "upload":
    src, dst = a[1], a[2]
    p = os.path.join(D, "remote", dst.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
    shutil.copyfile(src, p); print(dst); sys.exit(0)
if cmd == "delete":
    p = os.path.join(D, "remote", a[1].replace("/", os.sep)); shutil.rmtree(p, ignore_errors=True)
    print("deleted"); sys.exit(0)
if cmd == "generate":
    pr = a[a.index("--prompt") + 1]
    open(os.path.join(D, "prompt.txt"), "w", encoding="utf-8").write(pr)
    sys.stderr.write("Traceback (most recent call last):\n  set-cookie: abc_SECRET123\n"
                     "TimeoutError: No new Muse video appeared within 15s for session sess-42\n")
    sys.exit(1)
if cmd == "history":
    p = os.path.join(D, "prompt.txt")
    msgs = []
    if os.path.exists(p):
        pr = open(p, encoding="utf-8").read()
        msgs.append({"role": "user", "content": [{"type": "text", "text": pr}]})
        ma = re.search(r"BQ_LENH_(\S+)", pr).group(1)
        clips = json.loads(os.environ.get("FAKE_MUSE_CLIPS", "[]"))
        if MODE in ("tot", "khong_xoa"):
            body = json.dumps({"job": ma, "clips": clips}, ensure_ascii=False)
            msgs.append({"role": "assistant", "content": [{"type": "text",
                         "text": "Đây là kết quả:\n```json\n" + body + "\n```"}]})
        elif MODE == "rac":
            msgs.append({"role": "assistant", "text": "Mình cần quyền truy cập huggingface.co " + ma})
    print(json.dumps({"session_id": "sess-42", "messages": msgs}, ensure_ascii=False, indent=2))
    sys.exit(0)
sys.stderr.write("unknown"); sys.exit(2)
''', encoding="utf-8")
STATE = TMP / "state"
STATE.mkdir()
(STATE / "cookies.json").write_text('{"c":"SECRETCOOKIE_XYZ"}', encoding="utf-8")


def ffmpeg():
    return str(getattr(settings, "FFMPEG_PATH", "ffmpeg") or "ffmpeg")


# video nguồn lavfi 30 s (dùng cho cả ca proxy lẫn ca chọn đoạn)
SRC = TMP / "nguon.mp4"
subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=30",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-ac", "2",
                "-shortest", str(SRC)], check=True, timeout=120)

# transcript 300 s, câu 3 s
SEGS = [{"start": i * 3.0, "end": i * 3.0 + 3.0, "text": f"câu nội dung số {i}"}
        for i in range(100)]
TR = {"segments": SEGS, "language": "en"}
DUR = 300.0
CFGJOB = {"count": 2, "min_len": 30.0, "max_len": 45.0}
CLIPS_TOT = [
    {"title": "A", "title_pub": "A", "hook": "h", "hook_time": [12, 15], "score": 90,
     "reason": "r", "segments": [[9, 30], [60, 72]]},
    {"title": "B", "title_pub": "B", "hook": "h", "hook_time": [100, 103], "score": 80,
     "reason": "r", "segments": [[99, 200]]},           # quá dài -> phải bị ép <= max
    {"title": "C", "title_pub": "C", "hook": "h", "hook_time": [210, 213], "score": 70,
     "reason": "r", "segments": [[210, 222]]},          # quá ngắn -> phải nới >= min
    {"title": "D", "title_pub": "D", "hook": "h", "hook_time": [260, 263], "score": 60,
     "reason": "r", "segments": [[255, 290]]},
]

GROQ = []


def stage_gia(prompt, ctx=None, deadline=None, **kw):
    GROQ.append(prompt)
    return [{"title": "G", "title_pub": "G", "hook": "h", "hook_time": [150, 153],
             "score": 50, "reason": "groq", "segments": [[150, 185]]}]


M1._stage_json = stage_gia
M1._refine_clip = lambda c, *a, **k: c
llm.is_configured = lambda *a, **k: True


def reset(mode="tot", cli=True, state=True, bat=True, clips=CLIPS_TOT, han=None, bang=0):
    CFG.MUSE_BANG_GIAY = bang   # ca cũ: TẮT ảnh tổng hợp = hành vi trước 13/11 tối
    for f in ("calls.txt", "prompt.txt", "calls_tk.txt"):
        try:
            (FAKE_DIR / f).unlink()
        except OSError:
            pass
    muse_agent._CACHE_CO.clear()
    muse_agent._CACHE_KQ.clear()
    muse_agent._CACHE_HONG.clear()
    GROQ.clear()
    os.environ["FAKE_MUSE_DIR"] = str(FAKE_DIR)
    os.environ["FAKE_MUSE_MODE"] = mode
    os.environ["FAKE_MUSE_CLIPS"] = json.dumps(clips)
    CFG.MUSE_CHON_DOAN = bat
    CFG.MUSE_AI_CLI = (f'"{sys.executable}" "{FAKE}"' if cli
                       else str(TMP / "khong_co" / "muse-ai.exe"))
    CFG.MUSE_STATE_DIR = str(STATE) if state else str(TMP / "rong")
    CFG.MUSE_SESSION_ID = ""
    CFG.MUSE_POLL_GIAY = 2
    CFG.MUSE_TIMEOUT_HE_SO = 2.0
    CFG.MUSE_TIMEOUT_THEM = 600
    CFG.MUSE_TIMEOUT_MAX = han if han is not None else 3600


def calls():
    p = FAKE_DIR / "calls.txt"
    return [json.loads(x)[0] for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def chay(ctx=None, src=SRC, audit=None):
    return M1._llm_select_clips(TR, DUR, ctx, {}, dict(CFGJOB), nguon_video=str(src),
                                video_id=7, audit=audit)


def tong(s):
    return sum(e - a for a, e in s)


def tam_rong():
    d = TMP / "_muse_tam"
    return (not d.exists()) or not any(d.iterdir())


# ───────── CA 1: cờ TẮT ─────────
print("== CA 1: cờ TẮT -> 0 lượt CLI, Groq chạy ==")
reset(bat=False)
clips, _w = chay()
ok(calls() == [], "0 lượt gọi CLI", calls())
ok(len(GROQ) >= 1, f"Groq được gọi ({len(GROQ)} lượt)")
ok(all("ai_nguon" not in c for c in clips), "clip không mang dấu muse")
# 1b: đường Groq khi cờ tắt cho ra kết quả GIỐNG khi không truyền nguon_video
reset(bat=False)
a = M1._llm_select_clips(TR, DUR, None, {}, dict(CFGJOB))
reset(bat=False)
b = chay()
ok(json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str),
   "cờ tắt: kết quả Y HỆT lời gọi không có nguon_video")
# 1c: AST — _thu_muse phải kiểm bat() TRƯỚC mọi lời gọi chon_doan
src_m1 = (REPO / "app/modules/m1_highlight.py").read_text(encoding="utf-8")
fn = next(n for n in ast.walk(ast.parse(src_m1))
          if isinstance(n, ast.FunctionDef) and n.name == "_thu_muse")
dong_bat = min((n.lineno for n in ast.walk(fn) if isinstance(n, ast.Attribute) and n.attr == "bat"),
               default=10**9)
dong_chon = min((n.lineno for n in ast.walk(fn) if isinstance(n, ast.Attribute)
                 and n.attr == "chon_doan"), default=-1)
ok(0 < dong_bat < dong_chon, "_thu_muse kiểm bat() trước chon_doan", (dong_bat, dong_chon))
# 1d: m2_recap gọi _llm_select_clips KHÔNG có nguon_video -> không bao giờ Muse
ok("nguon_video" not in (REPO / "app/modules/m2_recap.py").read_text(encoding="utf-8"),
   "m2_recap không truyền nguon_video")
# 1e: module KHÔNG import thư viện muse_ai
src_ma = (REPO / "app/ai/muse_agent.py").read_text(encoding="utf-8")
imps = [n for n in ast.walk(ast.parse(src_ma)) if isinstance(n, (ast.Import, ast.ImportFrom))]
ten_imp = [getattr(n, "module", None) or n.names[0].name for n in imps]
ok(not any(str(t).startswith("muse_ai") for t in ten_imp), "không import muse_ai vào app", ten_imp)

# ───────── CA 2: thiếu CLI / chưa đăng nhập / ping hỏng ─────────
print("== CA 2: không dùng được Muse -> rơi Groq ==")
reset(cli=False)
c = muse_agent.co_muse()
ok(c["co"] is False and "muse-ai" in c["ly_do"], "thiếu CLI -> co=False", c)
clips, _ = chay()
ok(len(GROQ) >= 1 and calls() == [], "thiếu CLI -> Groq, 0 lượt CLI")
reset(state=False)
c = muse_agent.co_muse()
ok(c["co"] is False and "đăng nhập" in c["ly_do"], "chưa đăng nhập -> co=False", c)
reset(mode="sai_ping")
c = muse_agent.co_muse()
ok(c["co"] is False and "ping" in c["ly_do"], "ping hỏng -> co=False", c)
clips, _ = chay()
ok(len(GROQ) >= 1 and "upload" not in calls(), "ping hỏng -> Groq, không tải lên")
reset()
c = muse_agent.co_muse()
ok(c["co"] is True and c["ho_tro_xoa"] is True, "CLI giả đủ lệnh -> co=True", c)

# ───────── CA 3: JSON tốt ─────────
print("== CA 3: Muse trả JSON tốt ==")
reset()
au = {}
t0 = time.monotonic()
clips, _w = chay(audit=au)
cs = calls()
print(f"   lượt CLI: {cs} · {time.monotonic()-t0:.1f}s")
ok(len(GROQ) == 0, "Groq KHÔNG được gọi", len(GROQ))
ok(au.get("muse") is True, "audit đánh dấu muse")
ok(1 <= len(clips) <= CFGJOB["count"], f"số clip <= {CFGJOB['count']} ({len(clips)})")
ok(all(c.get("ai_nguon") == "muse" for c in clips), "mọi clip mang ai_nguon=muse")
dai = [round(tong(c["segments"]), 1) for c in clips]
ok(all(CFGJOB["min_len"] - 0.5 <= d <= CFGJOB["max_len"] + 2 for d in dai),
   f"độ dài trong Min/Max {dai}")
ok(cs.count("upload") == 2 and "generate" in cs and "history" in cs, "tải 2 file + gửi + đọc lịch sử")
ok("delete" in cs, "gọi delete thư mục từ xa khi CLI có")
rem = FAKE_DIR / "remote" / "workspace" / "bq"
ok((not rem.exists()) or not any(rem.iterdir()), "thư mục từ xa đã xoá")
ok(tam_rong(), "thư mục tạm cục bộ đã dọn")
pr = (FAKE_DIR / "prompt.txt").read_text(encoding="utf-8")
ok("KHÔNG cài thêm gói" in pr and "KHÔNG truy cập" in pr and "KHÔNG xin quyền" in pr,
   "prompt cấm cài gói / vào mạng / xin quyền")
ok("5 ứng viên" in pr and "giữ 2 cái" in pr and "30-45 giây" in pr,
   "prompt mang số Part (đề xuất dư +3 ứng viên, giữ đúng 2) + Min/Max của app")
# lời thoại tải lên đúng khuôn 'bd-kt | lời' — kiểm qua bản gửi lên (lần chạy KHÔNG xoá)
reset(mode="khong_xoa")
clips2, _ = chay()
ok("delete" not in calls() and len(clips2) >= 1, "CLI không có delete -> không gọi, vẫn ra clip")
loi = list((FAKE_DIR / "remote").rglob("loi_thoai.txt"))
ok(bool(loi) and loi[0].read_text(encoding="utf-8").splitlines()[1] == "3.0-6.0 | câu nội dung số 1",
   "file lời đúng khuôn 'bd-kt | lời'")
# 3c: _call_waiting_quota thử lại -> KHÔNG chạy Muse lần 2 (bộ nhớ kết quả)
n1 = calls().count("generate")
chay()
ok(calls().count("generate") == n1, "chạy lại cùng video dùng kết quả đã có, không gửi lại")

# ───────── CA 4: trả lời hỏng / trễ ─────────
print("== CA 4: trả lời hỏng / trễ -> Groq ==")
reset(mode="rac", han=5)
t0 = time.monotonic()
clips, _ = chay()
ok(len(GROQ) >= 1 and all("ai_nguon" not in c for c in clips),
   f"trả lời không phải JSON -> Groq ({time.monotonic()-t0:.1f}s)")
reset(mode="tre", han=5)
clips, _ = chay()
ok(len(GROQ) >= 1, "quá hạn đợi -> Groq")
ok(tam_rong(), "quá hạn vẫn dọn tạm")
reset(clips=[{"title": "x", "segments": [["abc", "def"]]}])
clips, _ = chay()
ok(len(GROQ) >= 1 and all("ai_nguon" not in c for c in clips), "clip Muse loại hết -> Groq")
reset(clips=[])
clips, _ = chay()
ok(len(GROQ) >= 1, "Muse trả 0 clip -> Groq")

# ───────── CA 5: Huỷ ─────────
print("== CA 5: Huỷ lúc đang đợi ==")
reset(mode="tre")


class Ctx:
    def __init__(self):
        self.t = time.monotonic()

    def check_canceled(self):
        if time.monotonic() - self.t > 8:
            raise CanceledError()

    def progress(self, p, m=""):
        self.check_canceled()


bi_huy = False
try:
    chay(ctx=Ctx())
except CanceledError:
    bi_huy = True
ok(bi_huy, "CanceledError nổi lên")
ok(len(GROQ) == 0, "Huỷ không rơi sang Groq")
ok(tam_rong(), "Huỷ vẫn dọn tạm")

# ───────── CA 6: bản nhẹ ─────────
print("== CA 6: bản nhẹ bằng ffmpeg thật ==")
dst = TMP / "prox.mp4"
okp, ly = muse_agent.dung_proxy(str(SRC), str(dst))
ok(okp, "dựng bản nhẹ OK", ly)
pr = subprocess.run([ffmpeg().replace("ffmpeg", "ffprobe") if ffmpeg() != "ffmpeg" else "ffprobe",
                     "-v", "error", "-show_entries",
                     "stream=codec_type,height,r_frame_rate,channels,nb_frames",
                     "-of", "json", str(dst)], capture_output=True, text=True, timeout=60)
st = json.loads(pr.stdout or "{}").get("streams", [])
v = next((s for s in st if s.get("codec_type") == "video"), {})
au_ = next((s for s in st if s.get("codec_type") == "audio"), {})
ok(v.get("height") == 480, f"cao 480 ({v.get('height')})")
ok(v.get("r_frame_rate") == "2/1", f"2 khung/giây ({v.get('r_frame_rate')})")
ok(au_.get("channels") == 1, f"tiếng mono ({au_.get('channels')})")
sz = dst.stat().st_size
print(f"   nguồn {SRC.stat().st_size/1e6:.2f} MB -> bản nhẹ {sz/1e6:.3f} MB (30 s)")
ok(sz < SRC.stat().st_size, "bản nhẹ nhỏ hơn nguồn")

# ───────── CA 7: log không lộ cookie ─────────
print("== CA 7: log ==")
logs = "".join(p.read_text(encoding="utf-8") for p in (TMP / "logs").glob("muse_*.log"))
ok(len(logs) > 0, f"có log muse ({len(logs)} ký tự)")
ok("abc_SECRET123" not in logs and "SECRETCOOKIE_XYZ" not in logs, "log KHÔNG chứa cookie")
ok("rơi về Groq" in logs and "NHẬN trả lời" in logs, "log ghi cả lượt nhận lẫn lý do rơi Groq")

# ───────── CA 8: không đụng chống trùng ─────────
r = subprocess.run(["git", "diff", "--quiet", "--", "app/services.py"], cwd=REPO)
ok(r.returncode == 0, "app/services.py không đổi")
ok("muse" not in (REPO / "app/services.py").read_text(encoding="utf-8").lower(),
   "services.py không nhắc muse (dedup_key nguyên)")
ok('signals["ai"] = "muse"' in src_m1, "Part do Muse chọn mang signals ai=muse")

# ───────── CA 9 (13/11/2026, chạy Muse THẬT lôi ra) ─────────
print("== CA 9: mỗi việc một cuộc chat RIÊNG + đường gửi qua venv MuseAI ==")
_ARGV = []
_chay_that = muse_agent._chay
muse_agent._chay = lambda argv, *a, **k: (_ARGV.append(list(argv)), _chay_that(argv, *a, **k))[1]
reset()
chay()
muse_agent._chay = _chay_that
_gen = [a for a in _ARGV if "generate" in a]
_sid = _gen[0][_gen[0].index("--session-id") + 1] if _gen and "--session-id" in _gen[0] else ""
ok(_gen and "--session-id" not in _gen[0],
   "9a đường lùi `generate` KHÔNG gửi mã cuộc chat mới (mã mới ra 404 vì generate đọc lịch sử trước)",
   _gen[:1])
_his = [a for a in _ARGV if "history" in a]
ok(_his and all(a[a.index("--session-id") + 1] == "sess-42" for a in _his),
   "9b đọc lịch sử đúng cuộc chat CLI báo đã gửi (sess-42)", _his[:1])
_d = TMP / "venv_gia" / "Scripts"
_d.mkdir(parents=True)
(_d / "muse-ai.exe").write_bytes(b"")
(_d / "python.exe").write_bytes(b"")
ok(muse_agent.python_muse([str(_d / "muse-ai.exe")]) == str(_d / "python.exe"),
   "9c tìm python.exe cạnh muse-ai.exe")
ok(muse_agent.python_muse([sys.executable, str(FAKE)]) is None,
   "9d dạng 'python script.py' -> không dùng đường gửi riêng")
(_d / "python.exe").unlink()
ok(muse_agent.python_muse([str(_d / "muse-ai.exe")]) is None, "9e không có python.exe -> None")
ok("generate" not in muse_agent._MA_GUI and "chat_stream" in muse_agent._MA_GUI
   and "session_id=sid" in muse_agent._MA_GUI,
   "9f script gửi gọi thẳng chat_stream kèm session_id (không qua generate đọc lịch sử trước)")

print("== CA 10: Muse ra THIẾU Part -> Groq chọn bổ sung ==")
reset(clips=[CLIPS_TOT[0]])
clips, _w = chay()
ok(len(GROQ) >= 1, "10a Muse 1/2 clip -> Groq được gọi bổ sung", len(GROQ))
ok(any(c.get("ai_nguon") == "muse" for c in clips), "10b clip của Muse vẫn còn")
reset()
chay()
ok(len(GROQ) == 0, "10c Muse đủ 2/2 -> Groq KHÔNG bị gọi (đối chứng)", len(GROQ))

print("== CA 11: TẮT tự chuyển Groq -> đợi rồi thử Muse lại ==")
CFG.MUSE_DOI_GIAY = 0
reset(mode="sai_ping")
CFG.MUSE_LUI_GROQ = False
_vong = M1._con_vong_doi
M1._con_vong_doi = lambda v: True
try:
    chay()
    ok(False, "11a Muse lỗi + TẮT tự chuyển -> phải ném DoiLuotAI")
except M1.DoiLuotAI:
    ok(len(GROQ) == 0, "11a Muse lỗi + TẮT tự chuyển -> DoiLuotAI, 0 lượt Groq", len(GROQ))
M1._con_vong_doi = lambda v: False
reset(mode="sai_ping")
CFG.MUSE_LUI_GROQ = False
try:
    chay()
    ok(len(GROQ) >= 1, "11b hết trần vòng đợi -> vẫn rơi Groq (video không kẹt)", len(GROQ))
except M1.DoiLuotAI:
    ok(False, "11b hết trần vòng đợi -> vẫn rơi Groq (video không kẹt)", "ném DoiLuotAI")
M1._con_vong_doi = _vong
reset(mode="sai_ping")
CFG.MUSE_LUI_GROQ = True
chay()
ok(len(GROQ) >= 1, "11c BẬT tự chuyển (mặc định) -> Groq như cũ", len(GROQ))
ok(getattr(type(settings), "MUSE_LUI_GROQ", None) is True, "11d mặc định MUSE_LUI_GROQ = bật")

print("== CA 12: máy chủ trả HTTP 429 -> đợi rồi thử lại, không bỏ việc ==")
muse_agent.LUI_429_GIAY = 0.0
_mot = muse_agent._chay_mot
_dem = {"n": 0}


def _mot_429(argv, *a, **k):
    if "upload" in argv and _dem["n"] < 2:
        _dem["n"] += 1
        return 1, "", "websockets.exceptions.InvalidStatus: server rejected WebSocket connection: HTTP 429"
    return _mot(argv, *a, **k)


muse_agent._chay_mot = _mot_429
try:
    reset()
    clips, _w = chay()
finally:
    muse_agent._chay_mot = _mot
ok(_dem["n"] == 2 and any(c.get("ai_nguon") == "muse" for c in clips) and len(GROQ) == 0,
   "12a 2 lần 429 rồi qua -> Muse vẫn ra clip, 0 lượt Groq", (_dem["n"], len(GROQ)))
_dem2 = {"n": 0}
muse_agent._chay_mot = lambda argv, *a, **k: (_dem2.__setitem__("n", _dem2["n"] + 1), (1, "", "HTTP 429"))[1]
try:
    rc, _o, _e = muse_agent._chay(["x"], 5)
finally:
    muse_agent._chay_mot = _mot
ok(rc == 1 and _dem2["n"] == muse_agent.THU_429, "12b 429 mãi -> bỏ sau THU_429 lần, không treo", _dem2["n"])
_dem3 = {"n": 0}
muse_agent._chay_mot = lambda argv, *a, **k: (_dem3.__setitem__("n", _dem3["n"] + 1), (1, "", "RuntimeError: 401"))[1]
try:
    muse_agent._chay(["x"], 5)
finally:
    muse_agent._chay_mot = _mot
ok(_dem3["n"] == 1, "12c lỗi KHÁC 429 -> không thử lại", _dem3["n"])
muse_agent.LUI_429_GIAY = 3.0

print("== CA 13: NHIỀU tài khoản ==")
_TK = []
for _n in ("tkA", "tkB"):
    _p = TMP / _n
    _p.mkdir(exist_ok=True)
    (_p / "cookies.json").write_text("{}", encoding="utf-8")
    _TK.append(_p)


def calls_tk():
    p = FAKE_DIR / "calls_tk.txt"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def reset_tk(hong="", ds=None, clips=CLIPS_TOT):
    reset(clips=clips)
    CFG.MUSE_STATE_DIR = ""
    CFG.MUSE_STATE_DIRS = ",".join(str(x) for x in (ds or _TK))
    os.environ["FAKE_TK_HONG"] = hong


reset_tk()
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()
ds = muse_agent.ds_phien(muse_agent.lenh_cli())
ok([x.name for x in ds] == ["tkA", "tkB"], "13a đọc đủ 2 tài khoản từ MUSE_STATE_DIRS", [x.name for x in ds])
a1 = muse_agent.chon_phien(ds)
a2 = muse_agent.chon_phien(ds)
ok({a1.name, a2.name} == {"tkA", "tkB"}, "13b 2 việc cùng lúc -> chia 2 tài khoản khác nhau", (a1.name, a2.name))
muse_agent.tra_phien(a1)
muse_agent.tra_phien(a2)
ok(all(v == 0 for v in muse_agent._TK_TAI.values()), "13c xong việc -> trả tải về 0", muse_agent._TK_TAI)
reset_tk()
chay()
_tk_viec = {t for t, c in calls_tk() if c in ("upload", "history", "generate")}
ok(len(_tk_viec) == 1, "13d MỘT việc dùng đúng MỘT tài khoản cho tải lên + gửi + đọc", calls_tk())
ok(all(v == 0 for v in muse_agent._TK_TAI.values()), "13d' sau việc thật tải về 0", muse_agent._TK_TAI)
reset_tk(hong="tkA")
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()
muse_agent._TK_TAI[str(_TK[1])] = 5          # ép chọn tkA trước (tkB đang bận)
clips, _w = chay()
muse_agent._TK_TAI.clear()
ok(any(c.get("ai_nguon") == "muse" for c in clips) and len(GROQ) == 0,
   "13e tkA hỏng đăng nhập -> tự chuyển tkB, vẫn ra clip Muse, 0 lượt Groq", (len(GROQ), calls_tk()))
_up = [t for t, c in calls_tk() if c == "upload"]
ok(_up and all(t == "tkB" for t in _up) and str(_TK[0]) in muse_agent._TK_HONG,
   "13f bước dò thấy tkA hỏng -> đánh dấu, không giao việc cho tkA", _up)
# hỏng GIỮA CHỪNG: ping tkA vẫn đạt, tới lúc tải lên mới 401
reset_tk()
os.environ["FAKE_TK_HONG_UP"] = "tkA"
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()
muse_agent._TK_TAI[str(_TK[1])] = 5
clips, _w = chay()
muse_agent._TK_TAI.clear()
os.environ["FAKE_TK_HONG_UP"] = ""
_up = [t for t, c in calls_tk() if c == "upload"]
ok(_up[:1] == ["tkA"] and "tkB" in _up and any(c.get("ai_nguon") == "muse" for c in clips)
   and len(GROQ) == 0 and str(_TK[0]) not in muse_agent._TK_HONG,
   "13f' tkA 401 lúc tải lên (ping vẫn tốt) -> làm lại trên tkB, ra clip Muse, 0 lượt Groq, "
   "KHÔNG khoá chung tkA (14/11: 401/wake_vm thoáng qua từng khoá oan tài khoản duy nhất)", (_up, len(GROQ)))
reset_tk(hong="tkA")
chay()
_up = [t for t, c in calls_tk() if c == "upload"]
ok(_up and all(t == "tkB" for t in _up), "13g việc kế tiếp KHÔNG chọn lại tkA đang hỏng", _up)
reset_tk(hong="tkA,tkB")
muse_agent._TK_HONG.clear()
clips, _w = chay()
ok(len(GROQ) >= 1, "13h CẢ HAI tài khoản hỏng -> Groq, video vẫn ra Part", len(GROQ))
reset_tk(hong="tkA", ds=[_TK[0]])
muse_agent._TK_HONG.clear()
muse_agent._CACHE_CO.clear()
c = muse_agent.co_muse()
ok(c["co"] is False, "13i tài khoản DUY NHẤT hỏng -> co=False", c)
reset_tk(hong="tkA")
muse_agent._TK_HONG.clear()
muse_agent._CACHE_CO.clear()
c = muse_agent.co_muse()
ok(c["co"] is True and Path(c["phien"]).name == "tkB", "13j tkA hỏng nhưng tkB tốt -> vẫn dùng được Muse", c)
os.environ["FAKE_TK_HONG"] = ""
CFG.MUSE_STATE_DIRS = ""
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()

print("== CA 14: chỉ lỗi ĐĂNG NHẬP thật mới bỏ tài khoản (không bỏ nhầm vì lỗi mạng) ==")
for _t, _k in [("muse_ai.errors.MuseAuthError: HTTP 401 login required", True),
               ("Hatch RPC returned HTTP 403: forbidden", True), ("unauthorized", True),
               ("ConnectionError: timed out in auth.py login_referer", False),
               ("uploaded 4012 bytes", False), ("HTTP 429", False),
               ("server rejected WebSocket connection: HTTP 404", False), ("http 4013 items", False)]:
    ok(bool(muse_agent._RE_LOI_TK.search(_t.lower())) is _k, f"14 {'BỎ' if _k else 'GIỮ'} tài khoản: {_t[:50]}")

print("== CA 15: các lỗi lượt soát độc lập 13/11/2026 tìm ra ==")
import config as _config
_bk = (CFG.MUSE_CHON_DOAN, CFG.MUSE_LUI_GROQ)
_config._ap_vao_bo_nho({"MUSE_CHON_DOAN": "0", "MUSE_LUI_GROQ": "0"})
ok(muse_agent.bat() is False and CFG.MUSE_CHON_DOAN is False,
   "15a bỏ tích rồi Lưu ('0') -> Muse TẮT thật (trước: bool('0') = True)", CFG.MUSE_CHON_DOAN)
ok(CFG.MUSE_LUI_GROQ is False, "15b MUSE_LUI_GROQ '0' -> False thật", CFG.MUSE_LUI_GROQ)
_config._ap_vao_bo_nho({"MUSE_CHON_DOAN": "1"})
ok(muse_agent.bat() is True, "15c Lưu '1' -> bật")
ok(muse_agent.la_bat("0") is False and muse_agent.la_bat("1") is True and muse_agent.la_bat("") is False,
   "15d la_bat đọc đúng chuỗi")
CFG.MUSE_CHON_DOAN, CFG.MUSE_LUI_GROQ = _bk
for _t, _k in [("server rejected WebSocket connection: HTTP 429", True), ("Too Many Requests", True),
               ("session 4f29-4291-a429 timed out", False), ("uploaded 4290 bytes", False)]:
    ok(bool(muse_agent._RE_429.search(_t)) is _k, f"15e {'thử lại' if _k else 'KHÔNG thử lại'}: {_t}")
# history 401 giữa chừng -> đổi tài khoản ngay, không đợi tới hết giờ
reset_tk()
os.environ["FAKE_TK_HONG"] = ""
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()
muse_agent._TK_TAI[str(_TK[1])] = 5
_mot = muse_agent._chay_mot


def _his401(argv, *a, **k):
    if "history" in argv and str(_TK[0]) in argv:
        return 1, "", "muse_ai.errors.MuseAuthError: HTTP 401"
    return _mot(argv, *a, **k)


muse_agent._chay_mot = _his401
_t0 = time.monotonic()
try:
    clips, _w = chay()
finally:
    muse_agent._chay_mot = _mot
    muse_agent._TK_TAI.clear()
_up = [t for t, c in calls_tk() if c == "upload"]
ok(any(c.get("ai_nguon") == "muse" for c in clips) and "tkB" in _up and time.monotonic() - _t0 < 60,
   "15f history 401 trên tkA -> đổi sang tkB ngay, ra clip Muse", (_up, round(time.monotonic() - _t0)))
# Muse hỏng -> vòng gọi lại kế tiếp KHÔNG làm lại Muse (nhớ 5 phút)
reset(mode="sai_ping")
CFG.MUSE_LUI_GROQ = True
chay()
muse_agent._CACHE_CO.clear()
_n1 = len(calls())
reset_kq = muse_agent._CACHE_HONG.copy()
for f in ("calls.txt",):
    try:
        (FAKE_DIR / f).unlink()
    except OSError:
        pass
os.environ["FAKE_MUSE_MODE"] = "tot"
chay()
ok(not [c for c in calls() if c in ("upload", "generate")], "15g Muse vừa hỏng với video này -> lượt gọi lại không tải lên lần 2",
   calls())
# đường lùi `generate` giữ khoá: 2 việc không chen nhau trong cùng cuộc chat
ok(isinstance(muse_agent._KHOA_CHUNG, type(threading.Lock())), "15h có khoá MỘT-việc-một-lúc cho đường lùi")
ok(muse_agent._KHOA_CHUNG.acquire(blocking=False), "15i khoá đã được trả sau khi việc xong")
muse_agent._KHOA_CHUNG.release()
os.environ["FAKE_TK_HONG"] = ""
CFG.MUSE_STATE_DIRS = ""

print("== CA 16: quản lý tài khoản trong Cài đặt AI ==")
reset()
_goc = TMP / "goc_tk"
_goc.mkdir(exist_ok=True)
(_goc / ".muse-state").mkdir(exist_ok=True)
(_goc / ".muse-state" / "cookies.json").write_text("{}", encoding="utf-8")
CFG.MUSE_STATE_DIR = str(_goc / ".muse-state")
CFG.MUSE_STATE_DIRS = ""
os.environ["FAKE_TK_HONG"] = ""
muse_agent._TK_HONG.clear()
muse_agent._TK_TAI.clear()
ok(muse_agent.goc_tai_khoan() == _goc, "16a tìm đúng thư mục gốc các tài khoản", muse_agent.goc_tai_khoan())
ok([t["ten"] for t in muse_agent.ds_tai_khoan()] == ["chính"], "16b có 1 tài khoản 'chính'")
for _bad in ("", "tk 2", "tài", "a/b", "x" * 30):
    ok(muse_agent.thu_muc_tk_moi(_bad)[0] is None, f"16c từ chối tên xấu {_bad!r}")
_p, _ = muse_agent.thu_muc_tk_moi("tk2")
ok(_p == _goc / ".muse-state-tk2", "16d tên tk2 -> .muse-state-tk2", _p)


def _dn(thu_muc, email, ma):
    dn = muse_agent.DangNhap(thu_muc, email)
    dn.bat_dau()
    t0 = time.monotonic()
    while not (dn.cho_ma or dn.xong) and time.monotonic() - t0 < 30:
        time.sleep(0.1)
    if dn.cho_ma:
        dn.nhap_ma(ma)
    while not dn.xong and time.monotonic() - t0 < 60:
        time.sleep(0.1)
    return dn


dn = _dn(_p, "a@b.c", "000000")
ok(dn.xong and not dn.ok and not (_p / "cookies.json").exists(), "16e mã OTP SAI -> báo lỗi, không tạo tài khoản",
   dn.trang_thai)
ok([t["ten"] for t in muse_agent.ds_tai_khoan()] == ["chính"], "16f thư mục rỗng của lượt hỏng không thành tài khoản")
dn = _dn(_p, "a@b.c", "123456")
ok(dn.xong and dn.ok, "16g mã OTP ĐÚNG -> đăng nhập xong + kiểm đạt", dn.trang_thai)
ok(sorted(t["ten"] for t in muse_agent.ds_tai_khoan()) == ["chính", "tk2"], "16h tài khoản mới hiện trong danh sách")
dn = _dn(_p, "khong-email", "123456")
ok(dn.xong and not dn.ok and "email" in dn.trang_thai, "16i email sai -> báo, không gọi đăng nhập", dn.trang_thai)
ok(muse_agent.doi_ten_tk(str(_goc / ".muse-state"), "x")[0] is False, "16j không cho đổi tên tài khoản chính")
muse_agent._TK_TAI[str(_p)] = 1
ok(muse_agent.doi_ten_tk(str(_p), "tk3")[0] is False and muse_agent.go_tk(str(_p))[0] is False,
   "16k tài khoản ĐANG chạy video -> không cho đổi tên / gỡ")
muse_agent._TK_TAI.clear()
ok(muse_agent.doi_ten_tk(str(_p), "tk3")[0] is True and (_goc / ".muse-state-tk3" / "cookies.json").is_file(),
   "16l đổi tên tk2 -> tk3")
ok(muse_agent.doi_ten_tk(str(_goc / ".muse-state-tk3"), "chinh")[0] is False, "16m không đè lên tài khoản đã có")
_ok, _dich = muse_agent.go_tk(str(_goc / ".muse-state-tk3"))
ok(_ok and Path(_dich).is_dir() and (Path(_dich) / "cookies.json").is_file()
   and not (_goc / ".muse-state-tk3").exists(), "16n gỡ = CẤT vào _tk_da_go (không xoá)", _dich)
ok([t["ten"] for t in muse_agent.ds_tai_khoan()] == ["chính"], "16o tài khoản đã gỡ không còn được dùng")
ok(not any("_tk_da_go" in str(d) for d in muse_agent.ds_phien(muse_agent.lenh_cli())),
   "16p thư mục _tk_da_go KHÔNG bị nhận nhầm là tài khoản")
ok(muse_agent.kiem_tk(str(_goc / ".muse-state")) == (True, "dùng được"), "16q kiểm tài khoản tốt -> dùng được")
os.environ["FAKE_TK_HONG"] = ".muse-state"
_k = muse_agent.kiem_tk(str(_goc / ".muse-state"))
os.environ["FAKE_TK_HONG"] = ""
ok(_k[0] is False and "Đăng nhập lại" in _k[1], "16r tài khoản hết đăng nhập -> gợi ý Đăng nhập lại", _k)
ok(muse_agent.kiem_tk(str(_goc / ".muse-state"))[0] is True and str(_goc / ".muse-state") not in muse_agent._TK_HONG,
   "16s đăng nhập lại/kiểm đạt -> gỡ dấu tạm bỏ qua")
muse_agent._TK_HONG.clear()

print("== CA 17: Muse đề xuất DƯ ứng viên -> app vẫn giữ ĐÚNG số Part ==")
reset(clips=CLIPS_TOT)          # 4 ứng viên, đặt count=2
clips, _w = chay()
ok(len(clips) <= CFGJOB["count"] and len(GROQ) == 0, "17a 4 ứng viên Muse -> cắt về đúng 2 Part, 0 lượt Groq",
   (len(clips), len(GROQ)))

print("== CA 18: máy chủ TỪ CHỐI MỞ KẾT NỐI (400/503/reset) -> thử lại; 401/403 -> không ==")
for _t, _k in [("server rejected WebSocket connection: HTTP 400", True),
               ("server rejected WebSocket connection: HTTP 503", True),
               ("ConnectionResetError: [WinError 10054]", True),
               ("server rejected WebSocket connection: HTTP 401", False),
               ("server rejected WebSocket connection: HTTP 403", False),
               ("RuntimeError: uploaded file failed size validation", False)]:
    ok(bool(muse_agent._RE_KET_NOI.search(_t)) is _k, f"18 {'thử lại' if _k else 'KHÔNG thử lại'}: {_t[:50]}")
muse_agent.LUI_429_GIAY = 0.0
_dem4 = {"n": 0}
_mot = muse_agent._chay_mot


def _mot400(argv, *a, **k):
    if "upload" in argv and _dem4["n"] < 1:
        _dem4["n"] += 1
        return 1, "", "websockets.exceptions.InvalidStatus: server rejected WebSocket connection: HTTP 400"
    return _mot(argv, *a, **k)


muse_agent._chay_mot = _mot400
try:
    reset()
    clips, _w = chay()
finally:
    muse_agent._chay_mot = _mot
    muse_agent.LUI_429_GIAY = 3.0
ok(_dem4["n"] == 1 and any(c.get("ai_nguon") == "muse" for c in clips) and len(GROQ) == 0,
   "18g tải lên dính HTTP 400 một lần -> thử lại, vẫn ra clip Muse, 0 lượt Groq", (_dem4["n"], len(GROQ)))

print("== CA 19: Muse LÀM HẾT (bỏ bước Groq sau) + 9 bản vá lượt soát 13/11 ==")
CFG.MUSE_LAM_HET = True
_mu = [{"ai_nguon": "muse"}, {"ai_nguon": "muse"}]
ok(M1.muse_lam_het(_mu) is True, "19a clip toàn Muse + cờ bật -> Muse làm hết")
ok(M1.muse_lam_het(_mu + [{"score": 1}]) is False, "19a' lẫn 1 clip Groq bổ sung -> Groq làm đủ bước")
CFG.MUSE_LAM_HET = "0"
ok(M1.muse_lam_het(_mu) is False, "19a'' MUSE_LAM_HET='0' (chuỗi .env) -> TẮT, không bị bool('0')")
CFG.MUSE_LAM_HET = True
CFG.MUSE_CHON_DOAN = False
ok(M1.muse_lam_het(_mu) is False, "19a''' Muse tắt -> không bao giờ bỏ bước Groq")
# 19b: chạy thật đường Muse: KHÔNG gọi Groq cắt gọn, clip mang hashtag Muse
_rf = []
_rf_cu = M1._refine_clip
M1._refine_clip = lambda c, *a, **k: (_rf.append(1), c)[1]
_ht = [dict(c, hashtags=["#mot", "hai ba", "#mot", "#bon"]) for c in CLIPS_TOT]
reset(clips=_ht)
_au = {}
clips, _w = chay(audit=_au)
ok(clips and all(c.get("ai_nguon") == "muse" for c in clips) and not _rf and not GROQ,
   "19b Muse làm hết: 0 lượt Groq chọn đoạn, 0 lượt Groq cắt gọn", (len(_rf), len(GROQ)))
ok(_au.get("muse_lam_het") is True, "19b' nhật ký ghi muse_lam_het")
ok(clips and clips[0].get("hashtags_muse") == ["#mot", "#haiba", "#bon"],
   "19b'' hashtag Muse được làm sạch (bỏ trùng, thêm #, bỏ dấu cách)",
   clips[0].get("hashtags_muse") if clips else None)
ok(len(clips) <= CFGJOB["count"], "19b''' vẫn không vượt số Part")
# 19c: TẮT làm hết -> Groq cắt gọn như cũ
CFG.MUSE_LAM_HET = False
_rf.clear()
reset(clips=_ht)
clips, _w = chay()
ok(clips and len(_rf) == len(clips), "19c MUSE_LAM_HET tắt -> Groq cắt gọn từng clip như cũ",
   (len(_rf), len(clips)))
CFG.MUSE_LAM_HET = True
M1._refine_clip = _rf_cu
# 19d: Huỷ lúc ĐỢI chỗ tài khoản -> không rò chỗ song song, không rò tải tài khoản
reset()
CFG.MUSE_MOI_TK = 1
_sem = muse_agent._khoa_song_song()
_v0 = _sem._value
_cli = muse_agent.lenh_cli()
_tk = muse_agent.chon_phien(muse_agent.ds_phien(_cli), 1)      # chiếm chỗ duy nhất
_tai0 = dict(muse_agent._TK_TAI)
_n = [0]


def _huy_sau_3():
    _n[0] += 1
    if _n[0] > 3:
        raise CanceledError("huỷ")


_ra = None
try:
    muse_agent._chon_doan_mot(str(SRC), SEGS, DUR, dict(CFGJOB), "English", 7, _huy_sau_3)
except CanceledError:
    _ra = "huy"
muse_agent.tra_phien(_tk)
ok(_ra == "huy", "19d Huỷ lúc đợi chỗ tài khoản -> CanceledError nổi lên")
ok(_sem._value == _v0, "19d' KHÔNG rò chỗ song song sau Huỷ", (_sem._value, _v0))
ok(muse_agent._TK_TAI.get(str(_tk), 0) == 0, "19d'' tải tài khoản về 0 sau Huỷ",
   muse_agent._TK_TAI)
CFG.MUSE_MOI_TK = 16
# 19e: chạy xong 1 việc tốt -> mọi bộ đếm về đúng chỗ
reset()
clips, _w = chay()
ok(all(v == 0 for v in muse_agent._TK_TAI.values()) and _sem._value == _v0,
   "19e chạy xong: tải mọi tài khoản = 0, chỗ song song trả đủ",
   (muse_agent._TK_TAI, _sem._value, _v0))
# 19f: bước GỬI: 'connection reset' (có thể ĐÃ gửi) -> KHÔNG thử lại; từ chối lúc bắt tay -> thử lại
_goi = []
_cm = muse_agent._chay_mot


def _gia_reset(argv, *a, **k):
    _goi.append(1)
    return 1, "", "ConnectionResetError: [WinError 10054] connection reset"


muse_agent._chay_mot = _gia_reset
muse_agent.LUI_429_GIAY = 0.0
muse_agent._chay(["x"], 5, None, thu_429=True, chi_tu_choi=True)
ok(len(_goi) == 1, "19f GỬI dính connection reset -> KHÔNG gửi lại (tránh prompt 2 lần)", len(_goi))
_goi.clear()
muse_agent._chay(["x"], 5, None, thu_429=True)
ok(len(_goi) > 1, "19f' bước KHÁC (tải lên/đọc) dính reset -> vẫn thử lại", len(_goi))
_goi.clear()
muse_agent._chay_mot = lambda argv, *a, **k: (_goi.append(1), (1, "", "rejected WebSocket connection: HTTP 400"))[1]
muse_agent._chay(["x"], 5, None, thu_429=True, chi_tu_choi=True)
ok(len(_goi) > 1, "19f'' GỬI bị TỪ CHỐI lúc bắt tay (chưa gửi gì) -> thử lại", len(_goi))
muse_agent._chay_mot = _cm
muse_agent.LUI_429_GIAY = 3.0
# 19g: kết quả nhớ có hạn + quên khi job xong
reset()
_k = muse_agent._khoa_viec(str(SRC), dict(CFGJOB))
muse_agent._CACHE_KQ[_k] = (time.monotonic(), [{"x": 1}])
muse_agent.quen_ket_qua(str(SRC))
ok(_k not in muse_agent._CACHE_KQ, "19g quen_ket_qua bỏ kết quả nhớ của video")
muse_agent._CACHE_KQ[_k] = (time.monotonic() - muse_agent.KQ_NHO_GIAY - 5, [{"x": 1}])
_r, _ly, _t = muse_agent._chon_doan_mot(str(SRC), SEGS, DUR, dict(CFGJOB), "English", 7)
ok("dùng lại" not in _ly, "19g' kết quả nhớ QUÁ HẠN -> không dùng lại", _ly)
_src_gh = (REPO / "app" / "modules" / "m1_highlight.py").read_text(encoding="utf-8")
_fn = next(n for n in ast.walk(ast.parse(_src_gh))
           if isinstance(n, ast.FunctionDef) and n.name == "_generate_highlights")
ok(any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "quen_ket_qua"
       for n in ast.walk(_fn)),
   "19g'' generate_highlights GỌI quen_ket_qua (Phân tích lại ra kết quả mới)")
# 19h: Huỷ giết CẢ CÂY tiến trình (vỏ khởi chạy + python thật)
_pidf = TMP / "con_pid.txt"
_cha = subprocess.Popen([sys.executable, "-c",
                         "import subprocess,sys,time;"
                         f"p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);"
                         f"open(r'{_pidf}','w').write(str(p.pid));time.sleep(120)"])
_t0 = time.time()
while not _pidf.exists() and time.time() - _t0 < 20:
    time.sleep(0.2)
import psutil  # noqa: E402
_con = int(_pidf.read_text())
muse_agent._giet_cay(_cha)
time.sleep(1.0)
ok(not psutil.pid_exists(_con) or psutil.Process(_con).status() == psutil.STATUS_ZOMBIE,
   "19h _giet_cay giết luôn tiến trình CON (không bỏ lại python giữ kết nối)")
# 19i: hashtag Muse thay 1 lượt Groq — đúng thứ tự trong jobs
_jsrc = (REPO / "app" / "queue" / "jobs.py").read_text(encoding="utf-8")
_pj = next(n for n in ast.walk(ast.parse(_jsrc))
           if isinstance(n, ast.FunctionDef) and n.name == "_precompute_hashtags")
_goi_ten = [getattr(n.func, "id", getattr(n.func, "attr", "")) for n in ast.walk(_pj)
            if isinstance(n, ast.Call)]
ok("_hashtag_muse" in _goi_ten and "write_hashtags" in _goi_ten,
   "19i hashtag: dùng của Muse trước, Groq chỉ viết khi Muse không có")
from app.ai.social import chuan_hashtag  # noqa: E402
ok(chuan_hashtag(None) == [] and chuan_hashtag(["#a", "b"], 1) == ["#a"],
   "19i' chuan_hashtag chịu dữ liệu rác + cắt trần")
# 19j: bộ đọc tài khoản không ném khi luồng khác xoá bộ nhớ dò giữa chừng
muse_agent._CACHE_CO.clear()
muse_agent._CACHE_CO.update(t=time.monotonic())        # thiếu khoá 'kq'
_r = muse_agent.co_muse(kiem_mang=True)
ok(isinstance(_r, dict) and "co" in _r, "19j bộ nhớ dò thiếu 'kq' -> không KeyError, dò lại")

print("== CA 20: video KHÔNG LỜI -> Muse XEM video thay bước Groq xem hình ==")
_p_kl = muse_agent.dung_prompt("M1", "workspace/bq/M1", "video.mp4", "loi.txt", dict(CFGJOB),
                               "", 300.0, khong_loi=True)
ok("KHÔNG có lời nói" in _p_kl and "KHÔNG chép lời lại" not in _p_kl,
   "20a prompt video không lời bảo Muse XEM hình + NGHE tiếng, không nhắc file lời")
_dg = []
_bvd = M1._vd.build_vision_digest
M1._vd.build_vision_digest = lambda *a, **k: (_dg.append(1), [])[1]
_kl_tr = {"segments": [], "words": [], "language": ""}
reset()
_au = {}
_kq, _w = M1._llm_select_clips(_kl_tr, DUR, None, {}, dict(CFGJOB), nguon_video=str(SRC),
                               video_id=7, audit=_au, nghe_xem="x")
ok(_kq and all(c.get("ai_nguon") == "muse" for c in _kq) and _au.get("mode") == "muse_xem_video",
   "20b video không lời + Muse -> clip do Muse chọn", (len(_kq), _au.get("mode")))
ok(not _dg and not GROQ, "20b' KHÔNG tốn bước Groq xem hình, 0 lượt Groq", (len(_dg), len(GROQ)))
ok(len(_kq) <= CFGJOB["count"] and all(CFGJOB["min_len"] - 0.5 <= tong(c["segments"])
                                       <= CFGJOB["max_len"] + 0.5 for c in _kq),
   "20b'' vẫn đúng số Part + đúng Min/Max", [tong(c["segments"]) for c in _kq])
_tr = sorted((c["segments"][0][0], c["segments"][-1][1]) for c in _kq)
ok(all(_tr[i][1] <= _tr[i + 1][0] + 1e-6 for i in range(len(_tr) - 1)),
   "20b''' các Part không trùng đoạn nhau", _tr)
# Muse hỏng -> dựng digest NGAY rồi đi đường xem hình cũ
reset(mode="rac", han=2)
_dg.clear()
_kq, _w = M1._llm_select_clips(_kl_tr, DUR, None, {}, dict(CFGJOB), nguon_video=str(SRC),
                               video_id=7, audit={}, nghe_xem="x")
ok(len(_dg) == 1, "20c Muse hỏng -> app tự dựng bước xem hình (đường cũ), đúng 1 lần", len(_dg))
# Muse tắt -> 0 lượt CLI, KHÔNG dựng digest lần 2 (generate_highlights đã dựng sẵn)
reset(bat=False)
_dg.clear()
M1._llm_select_clips(_kl_tr, DUR, None, {}, dict(CFGJOB), nguon_video=str(SRC),
                     video_id=7, audit={}, digest=[{"t": 1.0, "mo_ta": "x"}], nghe_xem="x")
ok(calls() == [] and not _dg, "20d Muse tắt -> 0 lượt CLI, không dựng digest trùng", (calls(), len(_dg)))
M1._vd.build_vision_digest = _bvd
_gh = next(n for n in ast.walk(ast.parse(_src_gh))
           if isinstance(n, ast.FunctionDef) and n.name == "_generate_highlights")
ok("_muse_xem" in ast.unparse(_gh) and "nguon_video=(vrow" in ast.unparse(_gh).replace(" ", ""),
   "20e generate_highlights: video không lời vẫn gửi nguồn cho Muse, bỏ xem hình khi Muse bật")

print("== CA 21: Muse hỏng -> phần còn lại của job: Gemini TRƯỚC, Groq sau ==")
llm.uu_tien_gemini(False)
reset(mode="rac", han=2)
chay()
ok(llm.dang_uu_tien_gemini() is True, "21a Muse không ra clip -> bật ưu tiên Gemini cho job này")
llm.uu_tien_gemini(False)
reset()
chay()
ok(llm.dang_uu_tien_gemini() is False, "21b Muse ra đủ clip -> KHÔNG đụng thứ tự (Groq trước như cũ)")
reset(bat=False)
chay()
ok(llm.dang_uu_tien_gemini() is False, "21c Muse TẮT -> thứ tự cũ, không bật ưu tiên Gemini")
llm.uu_tien_gemini(False)

print("== CA 22: ảnh tổng hợp gửi kèm Muse (1 khung/5 s có ghi giây) ==")
reset(bang=5)
clips22, _ = chay()
_c22 = [json.loads(x) for x in (FAKE_DIR / "calls.txt").read_text(encoding="utf-8").splitlines()]
_up22 = [x for x in _c22 if x[0] == "upload"]
_bang22 = [x for x in _up22 if "/bang/bang_" in (x[2] if len(x) > 2 else "")]
ok(len(_bang22) >= 1 and len(_up22) == 2 + len(_bang22),
   "22a tải video + lời + ảnh tổng hợp vào bang/", [x[2] for x in _up22])
_pr22 = (FAKE_DIR / "prompt.txt").read_text(encoding="utf-8") if (FAKE_DIR / "prompt.txt").exists() else ""
ok(f"bang/: {len(_bang22)} ảnh tổng hợp" in _pr22 and "cứ 5 giây 1 khung" in _pr22
   and "Chỉ dùng các file" in _pr22, "22b prompt nói đúng số ảnh + nhịp 5 s")
ok(len(clips22) == CFGJOB["count"] and all(c.get("ai_nguon") == "muse" for c in clips22),
   "22c có ảnh vẫn ra đúng số Part, do Muse chọn", len(clips22))
reset(bang=0)
chay()
_pr0 = (FAKE_DIR / "prompt.txt").read_text(encoding="utf-8") if (FAKE_DIR / "prompt.txt").exists() else ""
ok("ảnh tổng hợp" not in _pr0 and "Chỉ dùng 2 file" in _pr0
   and calls().count("upload") == 2, "22d MUSE_BANG_GIAY=0 -> y như cũ (2 file, prompt không nhắc ảnh)")
_a = muse_agent.dung_prompt("X", "w/x", "video.mp4", "loi_thoai.txt", CFGJOB, "English", 300.0)
_b = muse_agent.dung_prompt("X", "w/x", "video.mp4", "loi_thoai.txt", CFGJOB, "English", 300.0, bang=(0, 0.0))
ok(_a == _b and "ảnh tổng hợp" not in _a, "22e không ảnh -> prompt GIỐNG TỪNG KÝ TỰ bản cũ")
_goc22 = muse_agent._chay


def _chay_hong_bang(argv, *a, **k):
    if any("/bang/" in str(x) for x in argv):
        return 1, "", "HTTP 500 upload failed"
    return _goc22(argv, *a, **k)


muse_agent._chay = _chay_hong_bang
try:
    reset(bang=5)
    clips22f, _ = chay()
    _pr22f = (FAKE_DIR / "prompt.txt").read_text(encoding="utf-8") if (FAKE_DIR / "prompt.txt").exists() else ""
    ok("ảnh tổng hợp" not in _pr22f and len(clips22f) == CFGJOB["count"]
       and all(c.get("ai_nguon") == "muse" for c in clips22f),
       "22f tải ảnh lỗi -> bỏ cả bộ ảnh, Muse vẫn chọn như cũ (không rơi Groq)")
finally:
    muse_agent._chay = _goc22
CFG.MUSE_BANG_GIAY = 5
ok(muse_agent.nhip_bang(300) == 5 and muse_agent.nhip_bang(3600) == 5
   and muse_agent.nhip_bang(7200) == 8, "22g video dài giãn nhịp để <= 40 ảnh",
   [muse_agent.nhip_bang(x) for x in (300, 3600, 7200)])
CFG.MUSE_BANG_GIAY = 0
ok(muse_agent.nhip_bang(3600) == 0, "22h MUSE_BANG_GIAY=0 -> tắt hẳn")

print("== CA 23: 401 thoáng qua lúc đọc lịch sử KHÔNG khoá tài khoản (đo thật 14/11 00:13) ==")
_goc_ping = muse_agent._ping_tot
_d23 = Path(TMP / "tk23")
try:
    muse_agent._ping_tot = lambda d: True
    muse_agent._TK_HONG.pop(str(_d23), None)
    ok(muse_agent._danh_dau_tk(_d23, "HTTP 401 Unauthorized") is True
       and str(_d23) not in muse_agent._TK_HONG,
       "23a lỗi dạng đăng nhập + ping vẫn tốt -> tránh ở lượt này, KHÔNG khoá chung")
    ok(muse_agent._danh_dau_tk(_d23, "muse_ai.errors.MuseAuthError: Muse VM wake failed: HTTP 503") is True
       and str(_d23) not in muse_agent._TK_HONG, "23a' wake_vm lỗi (đo thật 00:50) + ping tốt -> không khoá chung")
    muse_agent._ping_tot = lambda d: False
    ok(muse_agent._danh_dau_tk(_d23, "HTTP 401 Unauthorized") is True
       and str(_d23) in muse_agent._TK_HONG, "23b ping cũng hỏng -> khoá 10 phút như cũ")
    muse_agent._TK_HONG.pop(str(_d23), None)
    ok(muse_agent._danh_dau_tk(_d23, "connection reset by peer") is False
       and str(_d23) not in muse_agent._TK_HONG, "23c lỗi mạng thường -> không đụng tài khoản")
finally:
    muse_agent._ping_tot = _goc_ping
    muse_agent._TK_HONG.pop(str(_d23), None)
for _k in ("MUSE_TIMEOUT_HE_SO", "MUSE_TIMEOUT_THEM", "MUSE_TIMEOUT_MAX"):
    setattr(CFG, _k, type(CFG).__dict__.get(_k, getattr(CFG, _k)))
CFG.MUSE_TIMEOUT_HE_SO, CFG.MUSE_TIMEOUT_THEM, CFG.MUSE_TIMEOUT_MAX = 0.1, 300, 3600
ok(muse_agent._han_cho(1140) < 450 and muse_agent._han_cho(3381) < 700,
   "23d đợi Muse tối đa ~7 phút (19 phút video) thay vì 25 phút", [muse_agent._han_cho(x) for x in (1140, 3381)])

print("== CA 24: video ngắn không đủ chỗ cho count+3 ứng viên -> xin số VỪA độ dài, luôn JSON ==")
_c24 = {"count": 3, "min_len": 100, "max_len": 180}
_p494 = muse_agent.dung_prompt("X", "w/x", "video.mp4", "loi_thoai.txt", _c24, "English", 494.0)
_p1140 = muse_agent.dung_prompt("X", "w/x", "video.mp4", "loi_thoai.txt", _c24, "English", 1140.0)
_p80 = muse_agent.dung_prompt("X", "w/x", "video.mp4", "loi_thoai.txt", _c24, "English", 80.0)
ok("tối đa 4 ứng viên" in _p494 and "KHÔNG BAO GIỜ trả lời bằng chữ" in _p494 and "chọn 6 ứng viên" not in _p494,
   "24a video 494 s (đo thật: Muse trả lời bằng CHỮ khi xin 6) -> xin tối đa 4, dặn luôn JSON")
ok("chọn 6 ứng viên" in _p1140 and "KHÔNG BAO GIỜ trả lời bằng chữ" not in _p1140,
   "24b video đủ dài -> prompt y như cũ (6 ứng viên)")
ok("1 ứng viên" in _p80 and "KHÔNG BAO GIỜ" in _p80, "24c video ngắn hơn Min -> 1 ứng viên, vẫn JSON")

print(f"KETQUA cổng 117: ĐẠT {DAT} · HỎNG {HONG}")
try:
    import gc
    gc.collect()   # nhả kết nối SQLite còn treo trên s.db trước khi xoá
    from app.core.xoa_an_toan import don_thu_muc
    don_thu_muc(TMP, ten_bat_dau="bq_test_muse_")
except Exception:  # noqa: BLE001
    pass
sys.exit(1 if HONG else 0)
