# -*- coding: utf-8 -*-
# TÍNH NĂNG 🔁 Phân tích lại (Cắt cơ bản) — anh Hùng 30/07: "nhiều kênh bị AI
# không phân tích, tự dò hết 100 kênh làm cho tôi; cái nào xoá rồi tìm phần
# khôi phục phân tích lại". Test 2 lõi:
#   1. services.find_basic_cut_videos — quét MỌI kênh, đúng phân loại
#      (cắt cơ bản còn gốc / cắt cơ bản đã xoá / đã qua AI -> bỏ).
#   2. pipeline.index_recycled — lập chỉ mục Thùng rác theo tên file để
#      khôi phục video đã xoá.
# IN ĐƯỢC TIẾNG VIỆT KỂ CẢ KHI stdout BỊ CHUYỂN HƯỚNG RA FILE — xem ghi chú
# đầy đủ ở `_test_lane_starve.py`. PHẢI đặt TRƯỚC lời gọi `print` ĐẦU TIÊN,
# nếu không thì vá cũng như không.
import sys as _sys_utf8
for _f in (_sys_utf8.stdout, _sys_utf8.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

import os
import sys
import tempfile
from pathlib import Path

T = Path(tempfile.mkdtemp(prefix="reanalyze_basic_"))
os.environ["BQ_DB_PATH"] = str(T / "t.db")
os.environ["BQ_DATA_DIR"] = str(T)
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database.db import db  # noqa: E402
from app import services  # noqa: E402
from app.core import pipeline as P  # noqa: E402


FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


def mk_video(pid, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return db.execute("INSERT INTO videos(project_id, src_path, duration) "
                      "VALUES(?,?,120)", (pid, str(path))).lastrowid


def mk_clip(vid, llm, status="suggested", title="Clip"):
    return db.insert(
        "INSERT INTO clips(video_id, start_sec, end_sec, score, title, "
        "signals, status) VALUES(?,0,60,?,?,?,?)",
        (vid, 90 if llm else 50, title,
         db.dumps({"segments": [[0, 60]], "llm_used": llm}), status))


# ── 2 nhóm, 2 kênh mỗi nhóm ──
pA = db.execute("INSERT INTO projects(name,assets_dir,grp) VALUES('KA',?,'Mỹ')",
                (str(T / "a"),)).lastrowid
pB = db.execute("INSERT INTO projects(name,assets_dir,grp) VALUES('KB',?,'Nhật')",
                (str(T / "b"),)).lastrowid

# KA: v1 cắt cơ bản CÒN gốc; v2 đã qua AI; v3 cắt cơ bản ĐÃ XOÁ (gốc mất)
kdir = T / "nguon" / "KA"
v1 = mk_video(pA, kdir / "video1.mp4"); (kdir / "video1.mp4").write_bytes(b"x")
mk_clip(v1, llm=False)
v2 = mk_video(pA, kdir / "video2.mp4"); (kdir / "video2.mp4").write_bytes(b"x")
mk_clip(v2, llm=True, title="Tiêu đề AI")
v3 = mk_video(pA, kdir / "video3.mp4")          # KHÔNG tạo file -> đã xoá
mk_clip(v3, llm=False)
# KB: v4 cắt cơ bản còn gốc (nhóm Nhật)
bdir = T / "nguon" / "KB"
v4 = mk_video(pB, bdir / "clipB.mp4"); (bdir / "clipB.mp4").write_bytes(b"x")
mk_clip(v4, llm=False)
# v5: có cả clip cơ bản (suggested) LẪN clip AI -> coi là ĐÃ AI, bỏ qua
v5 = mk_video(pA, kdir / "video5.mp4"); (kdir / "video5.mp4").write_bytes(b"x")
mk_clip(v5, llm=False); mk_clip(v5, llm=True, title="AI")
# v6: clip cơ bản NHƯNG đã archived (làm lại rồi) -> KHÔNG còn clip hiện -> bỏ
v6 = mk_video(pA, kdir / "video6.mp4"); (kdir / "video6.mp4").write_bytes(b"x")
mk_clip(v6, llm=False, status="archived")

print("== 1. quét MỌI nhóm ==")
allv = services.find_basic_cut_videos(None)
vids = {v["video_id"] for v in allv}
kiem(vids == {v1, v3, v4},
     "đúng 3 video cắt cơ bản (v1 còn gốc, v3 đã xoá, v4 nhóm khác)",
     f"ra {sorted(vids)}")
kiem(v2 not in vids and v5 not in vids, "video đã qua AI -> loại (v2,v5)")
kiem(v6 not in vids, "video clip cũ đã archived -> loại (v6)")

print("== 2. cờ exists đúng (còn gốc / đã xoá) ==")
by = {v["video_id"]: v for v in allv}
kiem(by[v1]["exists"] is True, "v1 còn file gốc -> exists=True")
kiem(by[v3]["exists"] is False, "v3 mất file gốc -> exists=False")
kiem(by[v4]["channel"] == "KB", "v4 gắn đúng kênh KB")

print("== 3. quét 1 nhóm ==")
myv = {v["video_id"] for v in services.find_basic_cut_videos("Mỹ")}
kiem(myv == {v1, v3}, "lọc nhóm 'Mỹ' chỉ ra v1,v3 (không lẫn KB)",
     f"ra {sorted(myv)}")

print("== 4. index_recycled — tra video đã xoá theo tên file ==")
# Thùng rác NỘI BỘ _DaXoa cạnh thư mục kênh (T nằm trong Temp nên thùng rác
# user-chọn bị từ chối — đúng cơ chế thật: video rơi vào <cha kênh>/_DaXoa).
day = T / "nguon" / "_DaXoa" / "2026-07-30" / "KA"
day.mkdir(parents=True, exist_ok=True)
(day / "video3.mp4").write_bytes(b"restored-content")
idx = P.index_recycled("", [str(kdir), str(bdir)])
kiem("video3.mp4" in idx, "tìm thấy video3.mp4 trong Thùng rác", str(list(idx)))
kiem(os.path.exists(idx.get("video3.mp4", "")), "đường dẫn chỉ mục có thật")

print("== 5. khôi phục gốc rồi file về đúng chỗ ==")
new = P.restore_recycled(idx["video3.mp4"], str(kdir))
kiem(new is not None and os.path.exists(str(new)),
     "restore_recycled đưa video3 về thư mục kênh")
# sau khôi phục, quét lại thì v3 chuyển sang 'còn gốc' (nếu cập nhật src_path)
db.execute("UPDATE videos SET src_path=? WHERE id=?", (str(new), v3))
after = {v["video_id"]: v for v in services.find_basic_cut_videos(None)}
kiem(after[v3]["exists"] is True, "quét lại: v3 giờ CÒN gốc (khôi phục xong)")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — quét đúng, phân loại đúng, khôi phục được")
