# -*- coding: utf-8 -*-
"""THỬ PHÁ cổng 69 — gỡ ĐÚNG MỘT chốt mỗi phép, cổng phải ĐỎ THẬT.

LUẬT (bài học cổng 80): "không tìm thấy chỗ phá" = LỖI CỦA PHÉP THỬ, phải
tách hẳn khỏi cột LỌT — không thì báo cáo ngược sự thật. File repo là CRLF
nên chuỗi tìm nhiều dòng phải đọc/ghi ở chế độ NHỊ PHÂN-giữ-nguyên
(`newline=""`), đừng viết `\n` rồi tưởng đã phá.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
for f in (sys.stdout, sys.stderr):
    try: f.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

DUB = REPO / "app" / "core" / "dubbing.py"
DVT = REPO / "app" / "core" / "doc_viet_tat.py"

PHEP = [
    # PHÉP CANH HỒI QUY QUAN TRỌNG NHẤT: bật VieNeu lên MẶC ĐỊNH. Số đo đã bác
    # (`_do_viet_tat_vieneu.py`: giọng nhân bản đọc THÔ đúng 12/12, bật vào còn
    # 10/12 — TỐT LÊN 0 · TỆ ĐI 2). Ai bật lại mà không kèm bảng số mới thì
    # cổng PHẢI ĐỎ.
    ("0. bật VieNeu lên MẶC ĐỊNH (bỏ công tắc `bat_cho_vieneu`)",
     DVT,
     "        return bat_cho_vieneu()",
     "        return True"),
    ("1. `words[i]` gán THẲNG `wb` (bỏ gộp mốc — đường edge-tts CŨ)",
     DUB,
     "words[i] = doc_viet_tat.tra_moc_ve_goc(wb, txt, _thay)",
     "words[i] = wb"),
    ("2. nhánh VieNeu trả mốc THÔ (bỏ `tra_moc_loat` — đường MỚI)",
     DUB,
     "return ok_v, doc_viet_tat.tra_moc_loat(moc_v, gui, thay_ds)",
     "return ok_v, moc_v"),
    ("3. nhánh VieNeu KHÔNG đổi chữ (gỡ hẳn `sua_loat` ở cửa CÓ mốc)",
     DUB,
     "gui, thay_ds = doc_viet_tat.sua_loat(texts, voice)",
     "gui, thay_ds = list(texts), [[] for _ in texts]"),
    ("4. `_synth_all` KHÔNG đổi chữ (gỡ `sua_loat` ở cửa KHÔNG mốc)",
     DUB,
     "texts, _tv = doc_viet_tat.sua_loat(texts, voice)",
     "texts, _tv = list(texts), []"),
    # PHÉP QUAN TRỌNG NHẤT: đây là cách vá "trông hợp lý" mà HỎNG ÂM THẦM.
    # Đặt `sua_loat` ở ĐẦU HÀM (trước mọi nhánh) thì ca thường vẫn đúng; chỉ
    # khi máy THIẾU VieNeu -> lùi edge-tts, chữ bị đổi HAI LƯỢT, lượt hai
    # không còn viết tắt để bắt -> `thay` RỖNG -> `tra_moc_ve_goc` thành no-op
    # -> mốc kẹt ở «gi»/«đi»/«pi». rc vẫn 0, không một dòng báo.
    ("5. dời `sua_loat` LÊN ĐẦU `_synth_all_words` (trước mọi nhánh)",
     DUB,
     "    if _eleven_hay_khong(voice):\n"
     "        # MỐC TỪNG CHỮ LẤY THẲNG TỪ API",
     "    texts, _tv0 = doc_viet_tat.sua_loat(texts, voice)\n"
     "    if _eleven_hay_khong(voice):\n"
     "        # MỐC TỪNG CHỮ LẤY THẲNG TỪ API"),
]


def chay() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-u", "_test_viet_tat.py"],
                       cwd=str(REPO), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    dong = [x for x in (r.stdout or "").splitlines() if "TỔNG KẾT" in x]
    return r.returncode, (dong[-1].strip() if dong else "(KHÔNG có dòng tổng kết)")


def main() -> int:
    ma0, tk0 = chay()
    print(f"ĐỐI CHỨNG (chưa phá): mã {ma0} · {tk0}")
    if ma0 != 0:
        print("CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ -> dừng, phép thử vô nghĩa")
        return 2
    bat = lot = hong_phep = 0
    for ten, f, cu, moi in PHEP:
        goc = f.open("r", encoding="utf-8", newline="").read()
        # File repo là CRLF — mẫu tìm nhiều dòng viết `\n` sẽ KHÔNG khớp và
        # phép phá im lặng không phá được gì (bài học cổng 54).
        if "\r\n" in goc:
            cu, moi = cu.replace("\n", "\r\n"), moi.replace("\n", "\r\n")
        if goc.count(cu) != 1:
            print(f"  LỖI PHÉP THỬ  {ten} — tìm thấy {goc.count(cu)} chỗ, cần đúng 1")
            hong_phep += 1
            continue
        try:
            f.open("w", encoding="utf-8", newline="").write(goc.replace(cu, moi))
            ma, tk = chay()
        finally:
            f.open("w", encoding="utf-8", newline="").write(goc)
        if ma != 0:
            bat += 1
            print(f"  BẮT   {ten} — mã {ma} · {tk}")
        else:
            lot += 1
            print(f"  LỌT   {ten} — mã {ma} · {tk}")
    print(f"\nBẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {hong_phep}")
    ma_cuoi, tk_cuoi = chay()
    print(f"HOÀN NGUYÊN: mã {ma_cuoi} · {tk_cuoi}")
    return 0 if (lot == 0 and hong_phep == 0 and ma_cuoi == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
