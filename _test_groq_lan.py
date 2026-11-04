"""CỔNG 101 — GỌI AI GROQ SONG SONG CÓ GIỚI HẠN (31/10/2026).

Đo thật lúc chạy 7 luồng AI: bộ điều tiết `groq_dispatch.slot` cho ĐÚNG 1 lượt
gọi chat/cả máy -> làn bận 81% thời gian trong khi luôn có 7-16 key rảnh, mỗi
video chờ ~56 phút mới được phân tích. Nay làn chat mở `so_lan('chat')` = 3.

Cổng chạy TIẾN TRÌNH THẬT (bộ điều tiết là SQLite dùng chung nhiều tiến trình,
mock trong một tiến trình là giấu đúng chỗ có thể vỡ) và canh:
  * chat: đỉnh đúng 3 lượt cùng lúc, KHÔNG bao giờ 4;
  * vision: vẫn 1 (không đổi);
  * GROQ_SONG_SONG=1: về đúng hành vi cũ (1);
  * tiến trình bị giết khi đang giữ làn -> làn tự nhả (lease hết hạn / release).
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
HOP = Path(tempfile.mkdtemp(prefix="bq_test_groqlan_"))
DAT = HONG = 0


def ok(dk, ten, chi=""):
    global DAT, HONG
    DAT, HONG = (DAT + 1, HONG) if dk else (DAT, HONG + 1)
    print(("  ĐẠT  " if dk else "  HỎNG ") + ten + (f" — {chi}" if chi else ""))


CON = r"""
import os, sys, time, json
sys.path.insert(0, sys.argv[1])
from app.ai import groq_dispatch as g
with g.slot(sys.argv[2]):
    vao = time.time(); time.sleep(float(sys.argv[4])); ra = time.time()
with open(sys.argv[3] + "." + str(os.getpid()), "w") as h:
    h.write(json.dumps([vao, ra]))
"""
con_py = HOP / "tien_trinh_lan.py"
con_py.write_text(CON, encoding="utf-8")


def chay(scope, n, giu, env_them=None, ten="d"):
    env = dict(os.environ, BQ_DATA_DIR=str(HOP / ten), BQ_DB_PATH=str(HOP / ten / "s.db"),
               PYTHONIOENCODING="utf-8")
    env.update(env_them or {})
    so = HOP / f"so_{ten}"
    t0 = time.time()
    ps = [subprocess.Popen([sys.executable, str(con_py), str(GOC), scope, str(so), str(giu)],
                           env=env) for _ in range(n)]
    for p in ps:
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:   # TREO = HỎNG, không được chết cả cổng
            p.kill()
            p.wait()
    ev = []
    for f in HOP.glob(f"so_{ten}.*"):
        a, b = json.loads(f.read_text())
        ev += [(a, 1), (b, -1)]
    dong = cao = 0
    for _, d in sorted(ev, key=lambda e: (e[0], e[1])):
        dong += d
        cao = max(cao, dong)
    return cao, len(ev) // 2, time.time() - t0


print("CỔNG 101 — gọi AI Groq song song có giới hạn")
cao, n, dt = chay("chat", 7, 1.5, ten="chat")
ok(n == 7, "chat: cả 7 tiến trình đều vào và ra", f"{n}/7")
ok(cao == 3, "chat: đỉnh ĐÚNG 3 lượt cùng lúc (không 1, không 4)", f"đỉnh {cao} · {dt:.1f}s")
ok(dt < 7 * 1.5, "chat: nhanh hơn xếp hàng một-một", f"{dt:.1f}s < {7*1.5:.1f}s")

cao, n, _ = chay("vision", 4, 0.8, ten="vision")
ok(cao == 1 and n == 4, "vision: vẫn 1 lượt/lúc như cũ", f"đỉnh {cao}")

cao, n, _ = chay("chat", 4, 0.8, {"GROQ_SONG_SONG": "1"}, ten="cu")
ok(cao == 1 and n == 4, "GROQ_SONG_SONG=1 -> về đúng hành vi cũ", f"đỉnh {cao}")

# tiến trình chết khi đang giữ làn -> làn khác vẫn dùng được, không kẹt cả máy
env = dict(os.environ, BQ_DATA_DIR=str(HOP / "chet"), BQ_DB_PATH=str(HOP / "chet" / "s.db"))
ps = [subprocess.Popen([sys.executable, str(con_py), str(GOC), "chat", str(HOP / "so_x"), "60"], env=env)
      for _ in range(3)]
time.sleep(4)
for p in ps:
    p.kill()
    p.wait()
cao, n, dt = chay("chat", 2, 0.5, ten="chet")
ok(n == 2, "giết 3 tiến trình đang giữ làn -> việc sau vẫn chạy được", f"{n}/2 sau {dt:.1f}s")

sys.path.insert(0, str(GOC))
os.environ["BQ_DATA_DIR"] = str(HOP / "t")
from app.ai import groq_dispatch as G  # noqa: E402
ok(G._ten_lan("chat", 0) == "chat", "làn 0 giữ ĐÚNG tên cũ (bản cũ còn chạy vẫn tôn trọng)")
ok(G.so_lan("audio") == 1 and G.so_lan("vision") == 1, "chỉ làn chat được mở rộng")

import shutil  # noqa: E402
shutil.rmtree(HOP, ignore_errors=True)
print(f"KETQUA: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
