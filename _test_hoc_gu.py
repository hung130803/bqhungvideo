# -*- coding: utf-8 -*-
"""CỔNG 27 — AI HỌC GU CHỦ KÊNH (nút Hay/Nhạt trên clip).

Anh Hùng 06/08/2026: "nhiều đoạn nó lấy hài quá k cần thiết k hay". Thang điểm
chung mãi ra gu chung -> ghi lại chính lựa chọn của anh rồi đưa vào prompt của
KÊNH ĐÓ làm ví dụ mẫu. Bất biến phải giữ:
  - chưa đánh giá clip nào -> prompt Y HỆT cũ (không đổi hành vi 300 kênh);
  - gu của kênh A KHÔNG rò sang kênh B;
  - bấm lại 1 clip -> GHI ĐÈ, không nhân bản ý kiến;
  - clip bị xoá/phân tích lại -> bài học VẪN CÒN (lưu tóm tắt, không lưu id);
  - nút phải là CHỮ, không emoji (máy anh Hùng thiếu glyph -> ô đen, cổng 9).
"""
from __future__ import annotations

import os
import sys
import tempfile

T = tempfile.mkdtemp(prefix="hocgu_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  ✅ {ten}" + (f" — {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} — {ct}")
        print(f"  ❌ {ten} — {ct}")


from pathlib import Path  # noqa: E402

from app import services  # noqa: E402
from app.ai import chon_doan as CD  # noqa: E402
from app.database.db import db  # noqa: E402

print("\n=== 1. khối prompt: CHƯA có đánh giá -> KHÔNG đổi prompt ===")
ok(CD.khoi_prompt_gu({}) == "", "1a gu rỗng -> chuỗi rỗng")
ok(CD.khoi_prompt_gu({"thich": [], "khong": []}) == "",
   "1b 2 danh sách rỗng -> chuỗi rỗng")
ok(CD.khoi_prompt_gu(None) == "" and CD.khoi_prompt_gu("rác") == "",
   "1c đầu vào rác -> chuỗi rỗng, không nổ")

print("\n=== 2. khối prompt: có đánh giá -> nêu ĐÚNG 2 phía ===")
_g = {"thich": [{"title": "Bị bóc mẽ, cãi nhau to", "thoai": "You lied to me",
                 "dai": 72.0, "n_seg": 2}],
      "khong": [{"title": "Chào kênh + kêu đăng ký", "thoai": "subscribe",
                 "dai": 40.0, "n_seg": 1}]}
_k = CD.khoi_prompt_gu(_g)
ok("Bị bóc mẽ" in _k and "THÍCH" in _k, "2a nêu ví dụ THÍCH")
ok("Chào kênh" in _k and "KHÔNG THÍCH" in _k, "2b nêu ví dụ KHÔNG THÍCH")
ok("72s" in _k and "2 đoạn" in _k, "2c nêu độ dài + số đoạn (AI bắt chước được)")
ok(len(_k) <= 900, "2d khối bị chặn trần độ dài (prompt chọn đoạn đã sát 413)",
   f"{len(_k)} ký tự")
_nhieu = {"thich": [{"title": "x" * 200, "thoai": "y" * 300, "dai": 60,
                     "n_seg": 3} for _ in range(20)], "khong": []}
ok(len(CD.khoi_prompt_gu(_nhieu)) <= 900,
   "2e 20 ví dụ dài -> vẫn không phình prompt",
   f"{len(CD.khoi_prompt_gu(_nhieu))} ký tự")

print("\n=== 3. ghi/đọc gu trên DB THẬT ===")
pidA = services.create_project("Kênh A", "M")
pidB = services.create_project("Kênh B", "M")


def _tao_clip(pid, ten, a, b, segs):
    vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                     "VALUES(?,?,?)", (pid, os.path.join(T, "v.mp4"),
                                       600.0)).lastrowid
    return db.execute(
        "INSERT INTO clips(video_id,title,start_sec,end_sec,status,signals,"
        "transcript) VALUES(?,?,?,?,'suggested',?,?)",
        (vid, ten, a, b, db.dumps({"segments": segs}),
         "You lied to my face, I heard the whole thing")).lastrowid


cA1 = _tao_clip(pidA, "Cãi nhau to ở cửa hàng", 300.0, 372.0,
                [[300.0, 340.0], [340.0, 372.0]])
cA2 = _tao_clip(pidA, "Chào kênh kêu đăng ký", 0.0, 40.0, [[0.0, 40.0]])
cB1 = _tao_clip(pidB, "Clip của kênh B", 10.0, 70.0, [[10.0, 70.0]])

services.dat_gu_clip(cA1, 1)
services.dat_gu_clip(cA2, -1)
ok(services.gu_clip(cA1) == 1 and services.gu_clip(cA2) == -1,
   "3a đọc lại đúng 1 / -1")
ok(services.gu_clip(cB1) == 0, "3b clip chưa đánh giá -> 0")
gA = services.gu_cua_kenh(pidA)
ok(len(gA["thich"]) == 1 and len(gA["khong"]) == 1,
   "3c kênh A có đúng 1 thích + 1 không", str(gA))
ok(gA["thich"][0]["n_seg"] == 2 and abs(gA["thich"][0]["dai"] - 72.0) < 0.1,
   "3d lưu đúng số đoạn + độ dài từ clip thật",
   f"n_seg={gA['thich'][0]['n_seg']} dai={gA['thich'][0]['dai']}")

print("\n=== 4. KHÔNG rò gu giữa các kênh (300 kênh dùng chung app) ===")
gB = services.gu_cua_kenh(pidB)
ok(not gB["thich"] and not gB["khong"], "4a kênh B KHÔNG thấy gu của kênh A",
   str(gB))
ok(CD.khoi_prompt_gu(gB) == "", "4b kênh B -> prompt y hệt cũ")
services.dat_gu_clip(cB1, 1)
ok(len(services.gu_cua_kenh(pidB)["thich"]) == 1
   and len(services.gu_cua_kenh(pidA)["thich"]) == 1,
   "4c đánh giá ở kênh B không cộng dồn vào kênh A")

print("\n=== 5. bấm lại -> GHI ĐÈ, không nhân bản ===")
services.dat_gu_clip(cA1, -1)
ok(services.gu_clip(cA1) == -1, "5a đổi Hay -> Nhạt")
_n = db.query_one("SELECT COUNT(*) AS n FROM clip_gu WHERE clip_id=?",
                  (cA1,))["n"]
ok(_n == 1, "5b vẫn chỉ 1 dòng cho clip đó (không nhân bản)", f"{_n} dòng")
services.dat_gu_clip(cA1, 0)
ok(services.gu_clip(cA1) == 0, "5c bấm lại nút đang chọn -> BỎ đánh giá")

print("\n=== 6. clip bị XOÁ -> bài học vẫn còn ===")
services.dat_gu_clip(cA2, -1)
db.execute("DELETE FROM clips WHERE id=?", (cA2,))
_g2 = services.gu_cua_kenh(pidA)
ok(len(_g2["khong"]) == 1 and "Chào kênh" in _g2["khong"][0]["title"],
   "6a xoá clip rồi vẫn giữ bài học (lưu tóm tắt, không lưu id)", str(_g2))
services.dat_gu_clip(999999, 1)          # clip không tồn tại
ok(services.gu_clip(999999) == 0, "6b clip không tồn tại -> bỏ qua êm")

print("\n=== 7. NỐI VÀO PROMPT chọn đoạn (đường thật của m1) ===")
_src = Path(REPO, "app", "modules", "m1_highlight.py").read_text(
    encoding="utf-8", errors="replace")
ok("khoi_prompt_gu" in _src, "7a m1 có gọi khối gu")
ok("gu_cua_kenh" in _src, "7b m1 lấy gu THEO KÊNH của video")
_ui = Path(REPO, "app", "ui", "studio_page.py").read_text(
    encoding="utf-8", errors="replace")
ok('QPushButton(_nhan)' in _ui and '("Hay", 1' in _ui and '("Nhạt", -1' in _ui,
   "7c thẻ clip có 2 nút Hay/Nhạt")
# chỉ được soi NHÃN NÚT, không soi ghi chú: emoji trong comment thì user không
# thấy. (Bản đầu của cổng này soi cả file -> FAIL oan vì dòng ghi chú.)
_dong_nut = [ln for ln in _ui.splitlines()
             if "QPushButton(" in ln or "setText(" in ln]
_emoji_nut = [ln.strip()[:70] for ln in _dong_nut
              if any(ch in ln for ch in "👍👎📋✕")]
ok(not _emoji_nut,
   "7d nhãn nút KHÔNG dùng emoji dễ thiếu font (máy anh Hùng ra ô đen)",
   str(_emoji_nut[:2]))

print("\n=== 8. UI THẬT: bấm nút Hay trên thẻ clip ===")
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app.ui.studio_page import StudioPage  # noqa: E402

sp = StudioPage.__new__(StudioPage)


class _St:
    project_id = pidA
    video_id = None


sp.state = _St()
sp.status = QPushButton("")          # có setText, đủ cho hàm dùng
sp._refresh_clips = lambda *a, **k: None
cA3 = _tao_clip(pidA, "Đoạn rượt đuổi", 100.0, 160.0, [[100.0, 160.0]])
sp._dat_gu(cA3, 1)
ok(services.gu_clip(cA3) == 1, "8a bấm Hay -> ghi được gu")
ok("HAY" in sp.status.text() and "ví dụ" in sp.status.text(),
   "8b báo cho user biết đã dạy + đang có bao nhiêu ví dụ", sp.status.text())
sp._dat_gu(cA3, 0)
ok(services.gu_clip(cA3) == 0 and "bỏ đánh giá" in sp.status.text().lower(),
   "8c bấm lại -> bỏ đánh giá + báo rõ")

print(f"\n{'='*60}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 27 ĐẠT — AI học gu chủ kênh, không rò giữa kênh")
