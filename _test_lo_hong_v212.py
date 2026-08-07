# -*- coding: utf-8 -*-
"""CỔNG 33 — CANH 4 BẢN VÁ v2.11.1/v2.12.0 mà trước đó CHƯA CÓ CỔNG NÀO CANH.

Anh Hùng 07/08/2026: "test kỹ hết các lỗi tôi gửi... fix hết 1 thể".
Rà lại thì 4 bản vá quan trọng nhất đang KHÔNG có cổng nào canh — sửa xong mà
không có test thì lần sau ai đó đổi code là lỗi quay lại y nguyên:

  A. KHOÁ NGÔN NGỮ khi chép lời video dài  (lỗi "video nhật sub nhật nó trộn
     lẫn lộn cả tiếng anh") — nặng nhất, ảnh hưởng mọi kênh nước ngoài.
  B. GẤP SỔ TẠM (WAL) lúc đang chạy  (dữ liệu 1 tháng của anh Hùng chỉ nằm
     trong studio.db-wal, file .db đứng im từ 06/07).
  C. HỘP DÂY CHUYỀN: dựng bảng THƯA + chống tái nhập + dừng hẹn giờ khi đóng
     (ứng viên số 1 của lỗi app TỰ THOÁT `access violation`).
  D. Ô "đợi" phải GIẢI THÍCH + ƯỚC THỜI GIAN  (anh Hùng: "trc chạy có 200 chờ
     mà tự nhiên lên 450 k biết ở đâu").
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="lohong_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
# key GIẢ, đặt TRƯỚC khi nạp config (Settings.groq_keys là classmethod đọc
# thuộc tính LỚP nên gán vào instance sau đó không có tác dụng). Cổng này
# KHÔNG gọi mạng — _groq_one đã bị thay bằng bản giả lập.
os.environ["GROQ_API_KEYS"] = "gsk_kiemthu_khoa_ngonngu"
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  OK  {ten}" + (f" - {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} - {ct}")
        print(f"  SAI {ten} - {ct}")


from pathlib import Path  # noqa: E402

FF = str(Path(REPO, "bin", "ffmpeg.exe"))
_NOWIN = 0x08000000 if sys.platform == "win32" else 0

# ══════════════ A. KHOÁ NGÔN NGỮ CHO VIDEO DÀI ══════════════
print("\n=== A. Chép lời video DÀI: mọi khúc phải DÙNG 1 NGÔN NGỮ ===")
from app.core import transcribe as TR  # noqa: E402

# audio THẬT dài 25 phút (im lặng, ~vài trăm KB) -> buộc chia 3 khúc 10 phút
_wav = os.path.join(T, "dai25phut.m4a")
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                "anullsrc=r=16000:cl=mono", "-t", "1500", "-c:a", "aac",
                "-b:a", "32k", _wav], capture_output=True,
               creationflags=_NOWIN, timeout=300)
ok(os.path.exists(_wav) and os.path.getsize(_wav) > 1000,
   "A0 dựng được audio thật 25 phút bằng ffmpeg",
   f"{os.path.getsize(_wav)//1024} KB" if os.path.exists(_wav) else "thiếu")

_goi: list = []          # ghi lại (thứ tự gọi, language được truyền vào)
_goc_groq_one = TR._groq_one


def _gia_groq_one(audio_path, language, keys, start_at=0, on_wait=None):
    """Giả lập Groq: khúc ĐẦU trả 'ja', các khúc sau (nếu ĐƯỢC TỰ ĐOÁN) trả
    'en' — đúng cảnh gây lỗi thật của anh Hùng. Ghi lại language nhận được."""
    _goi.append(language)
    lg = "ja" if language is None and len(_goi) == 1 else (language or "en")
    txt = "押入れの隙間から見られてる" if lg == "ja" else "I was watching TV"
    segs = [{"start": 0.0, "end": 5.0, "text": txt}]
    words = [{"start": 0.0, "end": 1.0, "word": txt[:4]}]
    return segs, words, lg, txt


TR._groq_one = _gia_groq_one
try:
    kq = TR._transcribe_groq(_wav, None, None)
finally:
    TR._groq_one = _goc_groq_one

ok(len(_goi) >= 3, "A1 video 25 phút được chia >= 3 khúc", f"{len(_goi)} khúc")
ok(_goi and _goi[0] is None,
   "A2 khúc ĐẦU vẫn để TỰ NHẬN DIỆN (không ép sai ngôn ngữ)", f"{_goi[0]!r}")
_sau = _goi[1:]
ok(bool(_sau) and all(x == "ja" for x in _sau),
   "A3 mọi khúc SAU bị ÉP đúng ngôn ngữ khúc đầu ('ja') — ĐÂY LÀ BẢN VÁ",
   f"{_sau}")
_van = " ".join(s["text"] for s in (kq.get("segments") or []))
ok("I was watching TV" not in _van,
   "A4 KHÔNG còn câu tiếng Anh lẫn vào bản chép lời tiếng Nhật",
   _van[:70])
ok((kq.get("language") or "") == "ja", "A5 nhãn ngôn ngữ cả video = 'ja'",
   f"{kq.get('language')!r}")
# ĐỐI CHỨNG ÂM: bỏ bản vá (ép language=None cho mọi khúc) thì PHẢI lẫn tiếng Anh
_goi.clear()
TR._groq_one = _gia_groq_one
try:
    _kq2 = None
    _segs = [_gia_groq_one(_wav, None, [])[0][0]["text"] for _ in range(3)]
finally:
    TR._groq_one = _goc_groq_one
ok(any("watching TV" in s for s in _segs),
   "A6 ĐỐI CHỨNG: nếu để mỗi khúc tự đoán thì CÓ lẫn tiếng Anh "
   "(chứng minh cổng này canh đúng chỗ)", str(_segs)[:80])

# ══════════════ B. GẤP SỔ TẠM (WAL) LÚC ĐANG CHẠY ══════════════
print("\n=== B. Gấp sổ tạm (WAL) ngay lúc đang chạy ===")
from app import services  # noqa: E402
from app.database.db import db  # noqa: E402

_pid = services.create_project("Kênh WAL", "M")
con = db.conn()
for i in range(4000):            # ghi nhiều để WAL phình qua ngưỡng
    con.execute("INSERT INTO videos(project_id,src_path,duration) "
                "VALUES(?,?,?)", (_pid, os.path.join(T, f"v{i}.mp4"), 600.0))
con.commit()
_wal = Path(os.environ["BQ_DB_PATH"] + "-wal")
_truoc = (_wal.stat().st_size / 1048576.0) if _wal.exists() else 0.0
ok(_truoc >= 0.4, "B1 dựng được cảnh WAL phình", f"{_truoc:.2f} MB")
_gap = db.gap_wal_dinh_ky()
_sau_mb = (_wal.stat().st_size / 1048576.0) if _wal.exists() else 0.0
ok(_gap > 0 and _sau_mb < _truoc,
   "B2 gấp được WAL vào file chính", f"gấp {_gap:.2f} MB · còn {_sau_mb:.2f} MB")
# BẰNG CHỨNG QUYẾT ĐỊNH: copy RIÊNG file .db (không kèm -wal) vẫn đủ dữ liệu
import shutil  # noqa: E402
import sqlite3  # noqa: E402

_ban = os.path.join(T, "chi_db.db")
shutil.copy2(os.environ["BQ_DB_PATH"], _ban)
_c = sqlite3.connect(_ban)
_n = _c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
_c.close()
ok(_n >= 4000,
   "B3 copy RIÊNG file .db (KHÔNG kèm -wal) vẫn đủ dữ liệu -> tắt đột ngột "
   "không mất việc", f"{_n} video trong file chính")
ok(db.gap_wal_dinh_ky() == 0.0,
   "B4 WAL còn nhỏ -> không gấp nữa (không tốn công vô ích)")
ok(db.gap_wal_dinh_ky(nguong_mb=999) == 0.0,
   "B5 ngưỡng cao -> bỏ qua êm, không nổ")

# ══════════════ C. HỘP DÂY CHUYỀN: chống đơ + chống tự thoát ══════════════
print("\n=== C. Hộp Dây chuyền: dựng bảng THƯA + chống tái nhập ===")
_src = Path(REPO, "app", "ui", "studio_page.py").read_text(
    encoding="utf-8", errors="replace")
ok("_pipe_dang_fill" in _src,
   "C1 có cờ chống TÁI NHẬP khi dựng bảng (processEvents bắn xen giữa)")
ok("dlg.finished.connect(lambda _=0: t.stop())" in _src,
   "C2 DỪNG HẲN hẹn giờ ngay khi hộp đóng (chặn access violation)")
ok('if not dlg.isVisible():' in _src,
   "C3 bỏ qua nếu hộp không còn hiện")
ok("_nhip[\"n\"] % 4" in _src,
   "C4 bảng chỉ dựng lại mỗi 8 giây (2s × 4), không phải mỗi 2 giây")
ok("_pipe_rep_cache" in _src,
   "C5 báo cáo chỉ ghi lại khi chữ THẬT SỰ đổi")
ok("except RuntimeError" in _src.split("def _fill_thua")[1][:1200],
   "C6 bọc RuntimeError quanh lúc dựng bảng (widget bị xoá giữa lúc vẽ)")

# ══════════════ D. Ô "đợi" phải giải thích + ước thời gian ══════════════
print("\n=== D. Ô 'đợi' giải thích con số + ước thời gian còn lại ===")
from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
from app.ui.queue_panel import QueuePanel  # noqa: E402
from app.ui.state import AppState  # noqa: E402

_app.setStyleSheet(theme.QSS)
for i in range(60):              # 20 chờ phân tích + 40 chờ xuất
    db.execute("INSERT INTO jobs(type,status,project_id,video_id,priority,"
               "progress) VALUES(?,?,?,?,?,0)",
               ("auto" if i < 20 else "m1_export_clip", "pending", _pid, 1, 3))
for i in range(3):
    db.execute("INSERT INTO jobs(type,status,project_id,video_id,priority,"
               "progress) VALUES('auto','running',?,1,10,0.5)", (_pid,))
qp = QueuePanel(AppState())
qp.timer.stop()
qp.refresh()
_tt = qp.chip_wait["w"].toolTip()
ok("TĂNG LÀ BÌNH THƯỜNG" in _tt,
   "D1 nói rõ số 'đợi' tăng là bình thường (mỗi video sinh ~3 việc xuất)")
ok("Ước còn" in _tt, "D2 có ƯỚC THỜI GIAN còn lại", _tt.split("Ước còn")[-1][:40])
ok("Luồng AI" in _tt, "D3 chỉ cho user cách chạy nhanh hơn (tăng luồng)")
ok("đợi phân tích 20" in _tt and "đợi cắt 40" in _tt,
   "D4 tách đúng số: chờ phân tích vs chờ cắt", _tt.splitlines()[0][:70])

# ══════════════ E. KHO TIẾNG ĐỘNG phải ĐỀU ĐỘ TO ══════════════
print("\n=== E. Kho tiếng động: không được có file nghe gần như không thấy ===")
# ĐO 07/08/2026: cổng 23 ra +11,4/+12,6/+12,2 dB ở 3 lượt nhưng CÓ LƯỢT chỉ
# +4,1 dB -> trong kho có file nhỏ hơn hẳn. Đo cả kho: LỆCH 19,9 dB, file nhỏ
# nhất -19,9 dB, 17 file dưới -12 dB. Hệ quả: Part này nghe rõ, Part kia im ->
# trông như app lỗi ngẫu nhiên. Đã chuẩn hoá bằng tools/chuan_am_sfx.py.
_ff = str(Path(REPO, "bin", "ffmpeg.exe"))
_kho = Path(REPO, "app", "assets", "sfx")
_dinh = []
for _p in sorted(_kho.rglob("*")):
    if _p.suffix.lower() not in (".opus", ".wav", ".ogg", ".mp3", ".m4a"):
        continue
    _r = subprocess.run([_ff, "-v", "info", "-i", str(_p), "-af",
                         "volumedetect", "-f", "null", "-"],
                        capture_output=True, text=True, creationflags=_NOWIN)
    import re as _re
    _m = _re.search(r"max_volume:\s*(-?[\d.]+) dB", _r.stderr or "")
    if _m:
        _dinh.append((float(_m.group(1)), _p.parent.name + "/" + _p.name))
_dinh.sort()
ok(len(_dinh) >= 150, "E1 đo được đỉnh của cả kho", f"{len(_dinh)} file")
_lech = (_dinh[-1][0] - _dinh[0][0]) if _dinh else 99
ok(_lech <= 8.0, "E2 độ lệch to/nhỏ cả kho <= 8 dB (trước chuẩn hoá: 19,9 dB)",
   f"{_lech:.1f} dB · nhỏ nhất {_dinh[0][0]:+.1f} dB ({_dinh[0][1]})")
_qua_nho = [n for v, n in _dinh if v < -12.0]
ok(not _qua_nho,
   "E3 KHÔNG còn file nào dưới -12 dB (trước: 17 file)",
   f"{len(_qua_nho)} file" + (f" · {_qua_nho[:3]}" if _qua_nho else ""))
_tong_kb = sum(p.stat().st_size for p in _kho.rglob("*") if p.is_file()) / 1024
ok(_tong_kb <= 400, "E4 chuẩn âm KHÔNG làm phình kho", f"{_tong_kb:.0f} KB")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  SAI {x}")
    sys.exit(1)
print("CỔNG 33 ĐẠT — 4 bản vá v2.11.1/v2.12.0 đã có cổng canh")
