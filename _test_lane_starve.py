# TÁI HIỆN: làn CẮT chết đói vì làn PHÂN TÍCH ngập.
#
# LỖI THẬT (anh Hùng 2026-07-26, ảnh màn Tiến trình): "🔍 1 phân tích ·
# ✂ 0 đang cắt · ⏳ 72 đợi" trong khi Luồng cắt = 2 và có job
# "✂ Xuất Part 3 · 561PC · ... Đang chờ" nằm đó không chạy.
#
# Nguyên nhân: _dispatch_once dùng MỘT query cho cả hai làn:
#     ORDER BY priority DESC, created_at ASC LIMIT 50
# Job phân tích priority=10, job xuất priority=3 → có ≥50 job phân tích chờ là
# 50 dòng lấy về toàn phân tích, job xuất KHÔNG BAO GIỜ được nhìn thấy.
# Chạy 2 nhóm cùng lúc (72 job) là vượt ngưỡng ngay.
import os
import sys
import tempfile
from pathlib import Path

# IN ĐƯỢC TIẾNG VIỆT KỂ CẢ KHI stdout BỊ CHUYỂN HƯỚNG RA FILE. Thiếu dòng này
# thì Python lấy bảng mã cp1252 -> `print` tiếng Việt ném UnicodeEncodeError
# NGAY DÒNG ĐẦU -> cổng "HỎNG" oan, mã thoát 1, trong khi mã app không sai một
# chỗ nào. Chỉ lộ ra khi chạy hồi quy hàng loạt (`> file`); chạy tay trong
# console utf-8 thì luôn xanh, nên loại lỗi này rất dễ bị đổ oan cho bản vá
# đang làm. (`_test_guard` đã làm sẵn việc này nhưng cổng này không dựng UI
# nên không import nó.)
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

T = Path(tempfile.mkdtemp(prefix="lane_"))
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database.db import db  # noqa: E402
from app.queue.worker import WorkerPool  # noqa: E402

FAIL: list[str] = []


def kiem(dk: bool, nhan: str, ct: str = "") -> None:
    print(f"  {'✓' if dk else '✗'} {nhan}" + ("" if dk else f"  << {ct}"))
    if not dk:
        FAIL.append(f"{nhan} — {ct}")


def dat_job(n_gpu: int, n_cpu: int) -> list[int]:
    """n_gpu job phân tích (priority 10) + n_cpu job xuất (priority 3)."""
    db.execute("DELETE FROM jobs")
    for i in range(n_gpu):
        db.insert(
            "INSERT INTO jobs(type, payload, needs_gpu, priority, status) "
            "VALUES('auto','{}',1,10,'pending')")
    ids = []
    for i in range(n_cpu):
        ids.append(db.insert(
            "INSERT INTO jobs(type, payload, needs_gpu, priority, status) "
            "VALUES('m1_export_clip','{}',0,3,'pending')"))
    return ids


class PoolGia(WorkerPool):
    """Pool THẬT nhưng KHÔNG chạy job — chỉ ghi lại job nào được xếp đi chạy.
    Ta chỉ kiểm bộ ĐIỀU PHỐI, không cần ffmpeg/Groq."""

    def __init__(self, max_cpu: int, max_gpu: int):
        super().__init__({}, max_cpu=max_cpu, max_gpu=max_gpu)
        self.da_xep: list[tuple[int, bool]] = []

        class _P:                     # đứng thế ThreadPoolExecutor
            def __init__(s, ghi, la_gpu):
                s.ghi, s.la_gpu = ghi, la_gpu

            def submit(s, fn, jid, *a):
                s.ghi.append((int(jid), s.la_gpu))
        self._gpu_pool = _P(self.da_xep, True)    # type: ignore[assignment]
        self._cpu_pool = _P(self.da_xep, False)   # type: ignore[assignment]


# TẮT "Tiết kiệm máy" cho đúng cấu hình máy anh Hùng (ảnh: ô không tích).
# PHẢI sửa thẳng settings — đặt env sau khi config đã nạp thì KHÔNG có tác dụng
# (bài học: test đầu tiên báo "làn cắt chỉ chạy 1" và tôi tưởng là lỗi sản phẩm,
# thực ra ECO_MODE mặc định BẬT nên khoá mỗi làn về 1 job).
from config import settings  # noqa: E402

settings.ECO_MODE = False

print("\n══ Làn CẮT có bị làn PHÂN TÍCH bỏ đói không? ══")
print("   (Luồng AI = 1, Luồng cắt = 2 — đúng cấu hình trên máy anh Hùng)")

for n_gpu in (10, 49, 50, 72, 200):
    ids_cpu = dat_job(n_gpu, 1)
    p = PoolGia(max_cpu=2, max_gpu=1)
    p._dispatch_once()
    xep_cpu = [j for j, g in p.da_xep if not g]
    xep_gpu = [j for j, g in p.da_xep if g]
    ok = ids_cpu[0] in xep_cpu
    print(f"   {n_gpu:3d} job phân tích chờ + 1 job xuất  ->  "
          f"xếp {len(xep_gpu)} phân tích, {len(xep_cpu)} xuất")
    kiem(ok, f"job XUẤT được chạy khi có {n_gpu} job phân tích đang chờ",
         "job xuất KHÔNG được xếp — làn cắt chết đói, video phân tích xong "
         "nằm im không ai cắt")

print("\n══ Không được vượt hạn mức từng làn ══")
for eco, mong_gpu, mong_cpu in ((False, 1, 2), (True, 1, 1)):
    settings.ECO_MODE = eco
    dat_job(5, 5)
    p = PoolGia(max_cpu=2, max_gpu=1)
    p._dispatch_once()
    n_gpu_run = sum(1 for _, g in p.da_xep if g)
    n_cpu_run = sum(1 for _, g in p.da_xep if not g)
    nhan_eco = "Tiết kiệm máy BẬT " if eco else "Tiết kiệm máy TẮT "
    print(f"   {nhan_eco}-> xếp {n_gpu_run} phân tích, {n_cpu_run} xuất")
    kiem(n_gpu_run == mong_gpu, f"{nhan_eco}: làn phân tích {mong_gpu} job",
         f"chạy {n_gpu_run}")
    kiem(n_cpu_run == mong_cpu, f"{nhan_eco}: làn cắt {mong_cpu} job",
         f"chạy {n_cpu_run}")
settings.ECO_MODE = False

print("\n" + "=" * 62)
if FAIL:
    print(f"❌ {len(FAIL)} LỖI:")
    for f in FAIL:
        print("   -", f)
else:
    print("✅ TẤT CẢ ĐẠT — làn cắt không bao giờ bị bỏ đói")
print("=" * 62)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
