"""THỬ PHÁ CỔNG 87 — gỡ từng chốt rồi đòi cổng phải ĐỎ.

Cổng nào chưa thử phá thì chỉ là CON DẤU. Ba lần trong repo này đã có cổng
"TẤT CẢ ĐẠT" vĩnh viễn vì nó chỉ hỏi "có mặt không" chứ không hỏi "có tác dụng
không" (cổng 56d · 64 CA7c · 75 mục 7e).

**"KHÔNG TÌM THẤY CHỖ PHÁ" LÀ LỖI CỦA PHÉP THỬ, KHÔNG PHẢI "LỌT".** File repo là
**CRLF** nên chuỗi tìm nhiều dòng viết `\\n` KHÔNG khớp — ở cổng 54 chuyện đó làm
4/6 phép phá im lặng không phá được gì mà bảng vẫn đếm vào cột LỌT, tức **báo
cáo ngược sự thật**. Nên script này tách hẳn ba cột.

**PHÁ THÌ PHẢI GỠ SẠCH CHỐT, đừng đổi giá trị bên trong nó** — cổng 80 có một
phép phá đổi biến thành giá trị không bao giờ khớp, làm hàm CHẶT HƠN, rồi bảng
đọc thành "cổng không bắt được".
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent

DUB = GOC / "app" / "core" / "dubbing.py"
DLG = GOC / "app" / "ui" / "thay_giong_dialog.py"
KOK = GOC / "app" / "core" / "giong_kokoro.py"

#: (tên phép phá, file, chuỗi TÌM, chuỗi THAY, mục cổng phải kêu)
PHEP = [
    ("1. gỡ lượt gọi Kokoro khỏi _synth_all",
     DUB, "ok_k = await _chay_kokoro(texts, _ma_kk, paths, rate, lang, on_msg)",
     "ok_k = False", "1a _synth_all", 1),
    ("2. đổi gọi GỘP thành gọi 1 CÂU",
     DUB, "_chay_kokoro(texts, _ma_kk, paths, rate, lang, on_msg)",
     "_chay_kokoro(texts[0:1], _ma_kk, paths, rate, lang, on_msg)",
     "truyền CẢ LOẠT", 2),
    ("3. gỡ 28 giọng khỏi combo",
     DLG, "for ma_g, nhan_g in giong_kokoro.danh_sach_giong():",
     "for ma_g, nhan_g in []:", "2a combo có ĐỦ", 1),
    # **NEO PHẢI DUY NHẤT.** Bản đầu tìm mỗi dòng `thieu = list(...)`, mà dòng
    # đó có ở **2 chỗ** (`_do_gh` dòng 1619 và `_do_kokoro` dòng 1872) nên
    # `.replace(..., 1)` đánh vào hàm KHÁC — Kokoro không hề bị phá, cổng xanh
    # ĐÚNG, và bảng đọc thành "cổng không bắt được". Đúng lỗi phép-thử của cổng
    # 80 (LỌT 7). Nay neo bằng dòng `self._tt_kokoro = tt` ngay trên nó.
    ("4. nút bám `co` thay vì `thieu` (bệnh cổng 58)",
     DLG,
     "        self._tt_kokoro = tt\n        thieu = list(tt.get(\"thieu\") or [])",
     "        self._tt_kokoro = tt\n        thieu = [] if tt.get(\"co\") "
     "else list(tt.get(\"thieu\") or [])",
     # Chuỗi chờ phải là ĐOẠN CON THẬT của nhãn mục. Bản đầu ghi "4b nút VẪN
     # HIỆN" trong khi nhãn là "4b co=True + thieu=[torch] -> nút VẪN HIỆN" ->
     # báo cáo in "ĐỎ NHƯNG SAI MỤC" cho một phép phá cổng bắt ĐÚNG. Báo cáo
     # sai lệch cũng là một dạng phép đo hỏng.
     "nút VẪN HIỆN", 1),
    ("5. khai TRÙNG hằng số NHAN_TAI",
     KOK, "def nhan_tai() -> str:",
     "NHAN_TAI = \"Tải giọng Kokoro (chưa đo dung lượng)\"\n\n\ndef nhan_tai() -> str:",
     "7", 1),
    ("6. nhét emoji vào nhãn nút (bệnh v2.6.22 ô đen)",
     KOK, "NHAN_TAI = \"Tải giọng Kokoro",
     "NHAN_TAI = \"\\U0001F4E5 Tải giọng Kokoro", "8", 1),
    ("7. bỏ cảnh báo giọng bị chấm thấp",
     KOK, "canh = \" — TÁC GIẢ CHẤM THẤP, nên chọn giọng khác\" if diem in DIEM_KEU else \"\"",
     "canh = \"\"", "10b", 1),
    ("8. bỏ chốt 'thiếu thì lùi êm' -> ép đi Kokoro dù máy không có",
     DUB, "    if kk.co_kokoro():", "    if True:", "11a máy thiếu", 1),
]

BAT, LOT, KHONG_PHA = [], [], []

for ten, f, tim, thay, muc, so_cho in PHEP:
    goc = f.read_text(encoding="utf-8")
    if goc.count(tim) < so_cho:
        KHONG_PHA.append(f"{ten} — tìm thấy {goc.count(tim)}/{so_cho} chỗ "
                         f"trong {f.name} (LỖI CỦA PHÉP THỬ, không phải LỌT)")
        print(f"?? KHÔNG PHÁ ĐƯỢC: {ten}  (thấy {goc.count(tim)}/{so_cho} chỗ)")
        continue
    bak = f.with_suffix(f.suffix + ".pha_bak")
    shutil.copy2(f, bak)
    try:
        f.write_text(goc.replace(tim, thay, so_cho), encoding="utf-8")
        r = subprocess.run([sys.executable, "-u", str(GOC / "_test_kokoro.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=str(GOC), timeout=1800)
        ra = (r.stdout or "") + (r.stderr or "")
        hong = [d for d in ra.splitlines() if d.lstrip().startswith("HỎNG:")]
        keu = r.returncode != 0 and any(muc in d for d in hong)
        if keu:
            BAT.append(f"{ten} -> cổng ĐỎ ({len(hong)} mục)")
            print(f"OK BẮT ĐƯỢC: {ten}")
            for d in hong[:3]:
                print("     ", d.strip()[:110])
        elif r.returncode != 0:
            # Cổng đỏ nhưng KHÔNG phải mục đang canh -> vẫn là lỗ của cổng:
            # nó bắt được nhờ mục KHÁC, tức mục đang canh có thể là con dấu.
            BAT.append(f"{ten} -> cổng ĐỎ nhưng do mục KHÁC, không phải «{muc}»")
            print(f"~~ ĐỎ NHƯNG SAI MỤC: {ten} (chờ «{muc}»)")
            for d in hong[:3]:
                print("     ", d.strip()[:110])
        else:
            LOT.append(f"{ten} -> cổng VẪN XANH = con dấu")
            print(f"!! LỌT: {ten}  <<< cổng KHÔNG bắt được")
    finally:
        shutil.copy2(bak, f)
        bak.unlink(missing_ok=True)

print("\n" + "=" * 62)
print(f"BẮT {len(BAT)} · LỌT {len(LOT)} · KHÔNG PHÁ ĐƯỢC {len(KHONG_PHA)}")
for x in LOT:
    print("  LỌT:", x)
for x in KHONG_PHA:
    print("  KHÔNG PHÁ ĐƯỢC:", x)
print("=" * 62)
# Kiểm file đã hoàn nguyên: bản vá hỏng để lại là phá mã đang chạy sản xuất.
con = [f.name for f in (DUB, DLG, KOK)
       if (f.with_suffix(f.suffix + ".pha_bak")).exists()]
print("file .pha_bak còn sót:", con or "KHÔNG (đã hoàn nguyên sạch)")
sys.exit(1 if (LOT or KHONG_PHA or con) else 0)
