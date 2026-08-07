# -*- coding: utf-8 -*-
"""CỔNG 35 — VÁ LỖ PHỤ ĐỀ: lấy lại chữ bị sót mà KHÔNG phá bản chép lời tốt.

Anh Hùng 07/08/2026: "nhiều đoạn nó nói mà k có sub luôn, ví dụ bên capcut oke
lắm gần như hoàn hảo".

ĐO THẬT ra bản vá này: chép cả file 600s bằng transcribe() -> khoảng
300,4-311,9s KHÔNG có câu nào; CẮT RIÊNG đúng đoạn đó gửi lại Groq -> ra
"I got that in pretty well.". Cùng tiếng, cùng model — gửi nguyên khối 10 phút
thì whisper nuốt chỗ giọng nhỏ/lẫn nhạc. CapCut hơn vì nó nhận dạng theo TỪNG
CHỖ CÓ GIỌNG.

SAI LẦM VỀ CÁCH ĐO — GHI ĐỂ ĐỪNG LẶP: bản đầu tôi lấy ffmpeg `silencedetect`
làm thước "chỗ nào có tiếng nói" rồi kết luận phụ đề chỉ phủ 83%. SAI: video
thử là máy xúc, tiếng động cơ cũng là "không im lặng"; cắt riêng 3 lỗ to nhất
gửi Groq nghe lại chỉ ra '.' và 'I'. Nay `_co_giong_nguoi` lọc DẢI TẦN GIỌNG
NGƯỜI (300-3400Hz) rồi mới đo RMS.

BẤT BIẾN SỐNG CÒN (đo trên 3 video Nhật thật của anh Hùng): video KHÔNG có lỗ
thì transcript phải Y HỆT bản cũ — 2/3 video ra 243 câu và 271 câu không đổi;
video thứ 3 được +2 câu, tốn thêm 0,2 giây.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="valo_")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from app.core import transcribe as tr  # noqa: E402
from config import settings  # noqa: E402

LOI: list = []
OK = 0
NW = 0x08000000


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  OK  {ten}" + (f" - {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} - {ct}")
        print(f"  SAI {ten} - {ct}")


FF = settings.FFMPEG_PATH
print("\n=== 1. Nhận diện GIỌNG NGƯỜI, không nhầm với tiếng động/nhạc ===")
# giọng người ~ tổ hợp hài trong 300-3400Hz; tiếng ù máy = 80Hz; nhạc cao = 8kHz
ca = {
    "giong nguoi (300+900+1800Hz)":
        "sine=frequency=300:duration=3[a];sine=frequency=900:duration=3[b];"
        "sine=frequency=1800:duration=3[c];[a][b][c]amix=inputs=3",
    "giong NHO (-25dB, noi khe)":
        "sine=frequency=300:duration=3[a];sine=frequency=900:duration=3[b];"
        "[a][b]amix=inputs=2,volume=-25dB",
    "tieng u may (80Hz)": "sine=frequency=80:duration=3",
    "nhac cao (9000Hz)": "sine=frequency=9000:duration=3",
    "im lang": "anullsrc=r=16000:cl=mono:duration=3",
}
kq = {}
for ten, lav in ca.items():
    p = os.path.join(T, ten.split()[0] + ".wav")
    subprocess.run([FF, "-v", "error", "-y", "-filter_complex", lav,
                    "-t", "3", "-ar", "16000", "-ac", "1", p],
                   capture_output=True, creationflags=NW)
    kq[ten] = tr._co_giong_nguoi(p, 0.0, 3.0)
    print(f"     {ten:34s} -> {kq[ten]}")
ok(kq["giong nguoi (300+900+1800Hz)"], "1a giọng người -> CÓ")
ok(kq["giong NHO (-25dB, noi khe)"],
   "1b giọng NHỎ vẫn phải nhận (đây đúng chỗ whisper hay nuốt chữ nhất)")
ok(not kq["im lang"], "1c im lặng -> KHÔNG")
ok(not kq["tieng u may (80Hz)"],
   "1d tiếng ù máy 80Hz -> KHÔNG (đúng chỗ silencedetect từng đánh lừa tôi)")
ok(not kq["nhac cao (9000Hz)"], "1e nhạc tần cao -> KHÔNG")

print("\n=== 2. Không có lỗ -> transcript GIỮ NGUYÊN TỪNG DÒNG ===")
_g = [{"start": 0.0, "end": 3.0, "text": "câu một"},
      {"start": 3.2, "end": 6.0, "text": "câu hai"},
      {"start": 6.1, "end": 9.0, "text": "câu ba"}]
s2, w2, n2 = tr.va_lo_chep_loi("khong-co-file.m4a", list(_g), [], "vi")
ok(s2 == _g and n2 == 0, "2a khoảng cách < 2s -> không vá, không đụng gì",
   f"{len(s2)} câu · vá {n2}")
ok(tr.va_lo_chep_loi("x.m4a", [], [], "vi") == ([], [], 0),
   "2b transcript rỗng -> trả rỗng, không nổ")

print("\n=== 3. FAIL-SAFE: mọi lỗi phải GIỮ bản gốc (thà thiếu hơn hỏng) ===")
_lo = [{"start": 0.0, "end": 3.0, "text": "a"},
       {"start": 30.0, "end": 33.0, "text": "b"}]      # lỗ 27 giây
s3, w3, n3 = tr.va_lo_chep_loi(os.path.join(T, "KHONG-TON-TAI.m4a"),
                               list(_lo), [], "vi")
ok(s3 == _lo and n3 == 0, "3a file audio không tồn tại -> giữ nguyên, không nổ",
   f"{len(s3)} câu")
_cu = tr._groq_one
try:
    tr._groq_one = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("mạng chết"))
    s4, _, n4 = tr.va_lo_chep_loi("x.m4a", list(_lo), [], "vi")
    ok(s4 == _lo and n4 == 0, "3b Groq chết giữa chừng -> giữ nguyên bản gốc")
finally:
    tr._groq_one = _cu

print("\n=== 4. Trần số lỗ + ngưỡng phải đúng như đã chốt ===")
ok(tr.VA_LO_MIN >= 2.0, "4a chỉ xét lỗ >= 2s (dưới là nghỉ hơi)",
   f"{tr.VA_LO_MIN}s")
ok(1 <= tr.VA_LO_TOI_DA <= 12,
   "4b có TRẦN số lỗ/video (không đội thời gian + hạn mức Groq)",
   f"tối đa {tr.VA_LO_TOI_DA} lỗ")
ok(tr.VA_LO_DEM > 0, "4c có đệm 2 đầu để không cắt cụt từ", f"{tr.VA_LO_DEM}s")

print("\n=== 5. Câu vá vào KHÔNG được chồng lên câu cũ (tránh sub trùng) ===")
_src = open(os.path.join(REPO, "app", "core", "transcribe.py"),
            encoding="utf-8", errors="replace").read()
_than = _src[_src.find("def va_lo_chep_loi("):]
_than = _than[:_than.find("\ndef ", 10)]
ok("se <= a + 0.05 or ss >= b - 0.05" in _than,
   "5a có chặn câu lấn ra ngoài lỗ (đệm dễ lấn sang câu kề)")
ok('max(ss, a)' in _than and 'min(se, b)' in _than,
   "5b mốc câu vá bị KẸP vào đúng trong lỗ")
ok("sorted(" in _than, "5c ghép xong SẮP LẠI theo thời gian")
ok("len(t) < 2" in _than,
   "5d bỏ câu rác 1 ký tự ('.', 'I') — whisper hay bịa khi nghe tiếng động")

print(f"\n{'=' * 62}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  SAI {x}")
    sys.exit(1)
print("CỔNG 35 ĐẠT — vá lỗ lấy lại chữ sót, không phá bản chép lời đang tốt")
