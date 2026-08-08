# -*- coding: utf-8 -*-
# ĐỢI-HỒI-LƯỢT thay vì cắt cơ bản (anh Hùng 30/07, ảnh đối chứng: cùng 1
# video, DÂY CHUYỀN ra 'Cắt cơ bản' còn bấm TAY 'Tạo clip' ra AI 90-92đ).
# Gốc: dây chuyền 3 luồng AI song song nuốt lượt -> có lúc CẢ 27 key cùng
# cooldown -> complete_text bỏ cuộc sau ≤45s -> heuristic. Nay:
# m1_highlight._call_waiting_quota ĐỢI key hồi (ngân sách 15 phút) rồi gọi
# lại — chỉ chịu thua khi hết ngân sách (hết lượt NGÀY) / lỗi không phải
# hết-lượt / user bấm Huỷ.
import os
import sys
from pathlib import Path
import tempfile
import time

T = tempfile.mkdtemp(prefix="quota_wait_")
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ai import llm  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


RATE_MSG = ("Gọi groq thất bại (hết lượt/lỗi tất cả key): Error code: 429 - "
            "rate limit reached, please try again in 12m3s")


class CtxGia:
    """JobContext giả: gom progress + giả lập bấm Huỷ."""
    def __init__(self, huy_sau: int = -1):
        self.msgs = []
        self.n_check = 0
        self.huy_sau = huy_sau

    def progress(self, frac, msg=""):
        self.msgs.append(msg)

    def check_canceled(self):
        self.n_check += 1
        if 0 <= self.huy_sau <= self.n_check:
            raise RuntimeError("DA_HUY")


_orig_wait = llm.soonest_ready_wait

# ── 1. hết lượt 2 lần -> đợi -> lần 3 thành công (KHÔNG rơi heuristic) ──
print("== 1. hết lượt tạm thời -> đợi key hồi -> thành công ==")
llm.soonest_ready_wait = lambda p, keys=None: 0.05   # key hồi sau 0.05s
calls = {"n": 0}


def fn_hoi_sau_2_lan():
    calls["n"] += 1
    if calls["n"] <= 2:
        raise llm.LLMError(RATE_MSG)
    return ("AI_OK", [])


ctx = CtxGia()
t0 = time.time()
out = M1._call_waiting_quota(fn_hoi_sau_2_lan, ctx, "groq", budget=60.0)
kiem(out == ("AI_OK", []), "trả đúng kết quả AI sau khi đợi", str(out))
kiem(calls["n"] == 3, "gọi lại đúng 3 lần (2 fail + 1 ăn)", str(calls["n"]))
kiem(any("hồi lượt" in m and "KHÔNG cắt cơ bản" in m for m in ctx.msgs),
     "progress nói rõ đang đợi, không cắt cơ bản", str(ctx.msgs[-1:]))
kiem(time.time() - t0 < 30, "đợi theo cooldown thật (không treo dài)")

# ── 2. lỗi KHÔNG phải hết lượt -> ném NGAY, không đợi vô ích ──
print("== 2. lỗi khác (key sai/mạng chết) -> ném ngay ==")
calls["n"] = 0


def fn_loi_khac():
    calls["n"] += 1
    raise llm.LLMError("Tất cả key groq đều SAI/không hợp lệ...")


try:
    M1._call_waiting_quota(fn_loi_khac, CtxGia(), "groq", budget=60.0)
    kiem(False, "phải ném LLMError")
except llm.LLMError:
    kiem(calls["n"] == 1, "ném ngay lần đầu, không retry vô ích",
         str(calls["n"]))

# ── 3. hết NGÂN SÁCH (cooldown dài = hết lượt ngày) -> chịu, ném lại ──
print("== 3. cooldown dài hơn ngân sách -> ném (heuristic là lưới cuối) ==")
llm.soonest_ready_wait = lambda p, keys=None: 3600.0   # hồi sau 1 giờ
calls["n"] = 0


def fn_luon_het_luot():
    calls["n"] += 1
    raise llm.LLMError(RATE_MSG)


t0 = time.time()
try:
    M1._call_waiting_quota(fn_luon_het_luot, CtxGia(), "groq", budget=10.0)
    kiem(False, "phải ném LLMError")
except llm.LLMError:
    kiem(True, "ném LLMError khi đợi vô vọng")
kiem(time.time() - t0 < 5, "không ngồi đợi giây nào khi biết vô vọng",
     f"{time.time()-t0:.1f}s")

# ── 4. user bấm HUỶ giữa lúc đang đợi -> thoát NGAY ──
print("== 4. bấm Huỷ giữa lúc đợi -> dừng ngay ==")
llm.soonest_ready_wait = lambda p, keys=None: 30.0
ctx = CtxGia(huy_sau=2)
t0 = time.time()
try:
    M1._call_waiting_quota(fn_luon_het_luot, ctx, "groq", budget=600.0)
    kiem(False, "phải thoát vì huỷ")
except RuntimeError as e:
    kiem("DA_HUY" in str(e), "CanceledError xuyên ra ngoài (job dừng ngay)")
kiem(time.time() - t0 < 15, "không đợi hết 30s cooldown mới chịu dừng",
     f"{time.time()-t0:.1f}s")

# ── 5. không có key nào (None) -> ném ngay ──
print("== 5. không còn key nào để đợi -> ném ngay ==")
llm.soonest_ready_wait = lambda p, keys=None: None
calls["n"] = 0
try:
    M1._call_waiting_quota(fn_luon_het_luot, CtxGia(), "groq", budget=60.0)
    kiem(False, "phải ném LLMError")
except llm.LLMError:
    kiem(True, "ném ngay khi không có key")

# ── 5b. KHÔNG truyền budget (đường thật trong generate_highlights) ──
# pyflakes từng bắt NameError 'settings' đúng nhánh này — test giữ cửa.
print("== 5b. budget mặc định (đọc settings) không nổ ==")
llm.soonest_ready_wait = lambda p, keys=None: 0.05
calls["n"] = 0
out = M1._call_waiting_quota(fn_hoi_sau_2_lan, CtxGia(), "groq")
kiem(out == ("AI_OK", []) and calls["n"] == 3,
     "chạy đường budget mặc định (settings) ra đúng kết quả",
     f"out={out} calls={calls['n']}")

llm.soonest_ready_wait = _orig_wait

# ── 6. bộ đếm UI không tính clip lưu trữ ──
print("== 6. đuôi combo/kho không đếm clip 'archived' ==")
from app.database.db import db  # noqa: E402
from app import services  # noqa: E402

pid = db.execute("INSERT INTO projects(name, assets_dir, grp) "
                 "VALUES('K', ?, '')", (T,)).lastrowid
vid = db.execute("INSERT INTO videos(project_id, src_path, duration) "
                 "VALUES(?,?,600)", (pid, os.path.join(T, "v.mp4"))).lastrowid
db.insert("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
          "signals, status, export_path) VALUES(?,0,50,50,'Clip','{}',"
          "'archived','x.mp4')", (vid,))
db.insert("INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
          "signals, status) VALUES(?,60,120,90,'AI mới','{}','suggested')",
          (vid,))
ca = services.channel_activity().get(pid) or {}
kiem(ca.get("clips") == 1, "đuôi kênh: 1 clip (bỏ archived)", str(ca))
va = services.video_activity(pid).get(vid) or {}
kiem(va.get("clips") == 1, "đuôi video: 1 clip (bỏ archived)", str(va))

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — hết lượt thì ĐỢI, không cắt cơ bản")
