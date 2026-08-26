# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 91 — mỗi phép gỡ ĐÚNG **MỘT** chốt rồi hỏi cổng có kêu không.

Cổng xanh **không chứng minh được gì** nếu chưa ai thử làm nó đỏ. File này là
phép đo đó: gỡ từng chốt, chạy lại cổng 91, đọc kết quả, rồi TRẢ LẠI NGUYÊN
VĂN.

═══════════════════════════════════════════════════════════════════════════
BA LUẬT CỦA PHÉP PHÁ — cả ba đều học từ lượt phá đã sai
═══════════════════════════════════════════════════════════════════════════
1. **NEO PHẢI DUY NHẤT.** Khớp 0 hoặc >1 chỗ thì đó là **LỖI CỦA PHÉP THỬ**,
   KHÔNG phải "cổng để lọt" — cột riêng. Bản đầu của `_pha_dubbing_cjk` đếm
   nhầm 4 phép "không phá được gì" vào cột LỌT và **báo cáo ngược sự thật**.
2. **PHẢI GỠ SẠCH CHỐT, đừng đổi giá trị bên trong nó.** `_pha_xoa_nham` đổi
   một biến bên trong mệnh đề canh, làm hàm CHẶT HƠN, rồi bảng đọc thành
   "cổng không bắt được" (LỌT 7 oan).
3. **FILE REPO LÀ CRLF.** Chuỗi tìm nhiều dòng viết `\\n` thì KHÔNG KHỚP, và
   phép phá im lặng không phá được gì. Ở đây mọi neo là **MỘT DÒNG**, và phép
   thay đọc/ghi bằng `newline=""` để không đụng tới dấu xuống dòng của file.

Chạy:  .venv\\Scripts\\python.exe _pha_da_ngu.py
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent
PY = REPO / ".venv" / "Scripts" / "python.exe"
CONG = REPO / "_test_nhan_ban_da_ngu.py"

GC = REPO / "app" / "core" / "giong_chatter.py"
NB = REPO / "app" / "core" / "nhan_ban_giong.py"
DUB = REPO / "app" / "core" / "dubbing.py"
UI = REPO / "app" / "ui" / "thay_giong_dialog.py"

#: (tên, file, neo MỘT DÒNG, thay bằng, mục cổng phải ĐỎ)
PHEP: list[tuple[str, Path, str, str, str]] = [
    ("1. UI ghi cứng lang='vi' (bản CŨ, chỉ mở cửa tiếng Việt)", UI,
     "        r = NB.them_giong(ten, self._mau, lang=self.nn_dang_chon(),",
     '        r = NB.them_giong(ten, self._mau, lang="vi",',
     "1h"),
    ("2. `doc_loat` thôi gọi `cat_lang_giua` (bỏ CHỐT 1)", GC,
     "                kq = cat_lang_giua(raw, gon)",
     "                kq = {'ok': False, 'giay_sau': 0.0}",
     "3h/3i"),
    ("3. `khoang_lang_giua` KHÔNG chừa lề hai đầu", GC,
     "                     if a > me and b < dai - me",
     "                     if True",
     "3e"),
    ("4. bỏ LƯỚI AN TOÀN cắt-quá-tay", GC,
     "        if sau < dai * LANG_GIUA_CON_TOI_THIEU:",
     "        if False:",
     "3g"),
    ("5. bộ dò ĐỌC LAN MAN luôn im", GC,
     "        return round(lan, 2) if lan > LAN_MAN_LAN else 0.0",
     "        return 0.0",
     "3k"),
    ("6. `vi_sao_khong_cai` bỏ nhánh KHÔNG GPU (bỏ CHỐT 2)", GC,
     "    if not co_gpu_nvidia():",
     "    if False:",
     "4c/4d/4e"),
    # Neo phải khớp **NGUYÊN VĂN** cả phần thụt lề: dòng này thụt 4 khoảng
    # trắng, không phải 8. Bản đầu ghi 8 -> khớp 0 chỗ -> "KHÔNG PHÁ ĐƯỢC".
    ("7. `_chatter_hay_khong` LÙI IM LẶNG (bỏ ghi log)", DUB,
     '    gc._ghi_log(f"Chưa dùng được giọng {voice} (thiếu: {tt[\'thieu\']}) -> "',
     '    _bo_log = (f"Chưa dùng được giọng {voice} (thiếu: {tt[\'thieu\']}) -> "',
     "4f"),
    ("8. `canh_bao_gon` bỏ vế ĐÓNG DẤU CHÌM (bỏ CHỐT 3)", GC,
     '            f"có ĐÓNG DẤU CHÌM")',
     '            f"chạy trên máy")',
     "5c/5e"),
    ("9. `CANH_BAO_CL` trả về bản CŨ (tả một đường KHÔNG CÓ trong mã)", GC,
     'CANH_BAO_CL = ("mốc từng chữ do BỘ GIÓNG HÀNG dựng chứ máy đọc KHÔNG tự trả "',
     'CANH_BAO_CL = ("mốc chữ phải MOI CỬA SAU của thư viện nên rung 76 ms; "',
     "6a/6b/6c/6d"),
    ("10. gỡ `_vua_tran` (nhãn thôi ép trần)", NB,
     "        return _vua_tran(g, \"\", ten, sau)",
     "        return ten + sau",
     "7b"),
    ("11. nghe thử ghi cứng nn='vi' (bản CŨ)", UI,
     "                kq = TGC.doc_thu(ma, wav, nn=nn_doc)",
     '                kq = TGC.doc_thu(ma, wav, nn="vi")',
     "8b/8c"),
    # `if not thieu:` có mặt ở CẢ BA hàng tải (VieNeu · nhân bản · Chatterbox)
    # nên nó KHÔNG phải neo duy nhất. Neo đúng là hai dòng liền kề chỉ có ở
    # `_do_chatter`, và phép phá đổi cách TÍNH `thieu` -> hàng bám `co`.
    #
    # ═══ `thay_giong_dialog.py` LÀ **LF**, KHÔNG PHẢI CRLF ═══
    # LUẬT 3 ở đầu file nói *"FILE REPO LÀ CRLF"* — câu đó ĐÚNG với
    # `giong_chatter.py` / `nhan_ban_giong.py` / `dubbing.py` (đo: 1228 · 1107
    # · 4134 CRLF, 0 LF trần) nhưng **SAI với đúng file này** (0 CRLF, 4997 LF
    # trần; `git` còn cảnh báo *"LF will be replaced by CRLF"*). Bản đầu viết
    # `\r\n` -> khớp **0 chỗ** -> phép phá im lặng không phá được gì. Nó không
    # bị đếm nhầm vào cột LỌT (LUẬT 1 đã chặn) nhưng chốt 9j vì thế **chưa
    # từng được thử một lần nào**.
    # Neo nhiều dòng phải theo dấu xuống dòng CỦA CHÍNH FILE ĐÓ, đừng theo
    # "quy ước repo".
    ("12. nút tải bám `co` thay vì `thieu`", UI,
     "        thieu = list(tt.get(\"thieu\") or [])\n"
     "        vi_sao = CB_C.vi_sao_khong_cai()",
     "        thieu = [] if tt.get(\"co\") else list(tt.get(\"thieu\") or [])\n"
     "        vi_sao = CB_C.vi_sao_khong_cai()",
     "9j"),
    ("13. bỏ `--ignore-installed` khỏi `cai_chatter`", GC,
     '           "--disable-pip-version-check", "--ignore-installed"]',
     '           "--disable-pip-version-check"]',
     "9e"),
    # `_synth_all` và `_synth_all_words` có khối `cb:` GIỐNG NHAU tới 6 dòng
    # đầu -> neo ngắn khớp 2 chỗ. Phải kéo dài tới dòng chỉ có ở
    # `_synth_all_words` (`on_done(_i)` không kèm chú thích + dòng `# MỐC:`).
    ("14. `_synth_all_words` thôi nhận `cb:` (sót MỘT cửa)", DUB,
     "    dung_cb, voice = _chatter_hay_khong(voice)\r\n    if dung_cb:\r\n"
     "        _ma_cb = voice\r\n        ok_c = await _chay_chatter(texts, "
     "_ma_cb, paths, rate, on_msg)\r\n        if any(ok_c):\r\n"
     "            if on_done:\r\n"
     "                for _i in range(len(texts)):\r\n"
     "                    on_done(_i)\r\n"
     "            # MỐC: API công khai của Chatterbox",
     "    dung_cb, voice = False, voice\r\n    if dung_cb:\r\n"
     "        _ma_cb = voice\r\n        ok_c = await _chay_chatter(texts, "
     "_ma_cb, paths, rate, on_msg)\r\n        if any(ok_c):\r\n"
     "            if on_done:\r\n"
     "                for _i in range(len(texts)):\r\n"
     "                    on_done(_i)\r\n"
     "            # MỐC: API công khai của Chatterbox",
     "2b/2e"),
]


def doc(p: Path) -> str:
    with io.open(p, encoding="utf-8", newline="") as f:
        return f.read()


def ghi(p: Path, s: str) -> None:
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def chay_cong() -> tuple[int, int, int, str]:
    """Chạy cổng 91. Trả ``(mã thoát, đạt, hỏng, dòng KETQUA)``."""
    r = subprocess.run([str(PY), str(CONG)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(REPO),
                       timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    dat = hong = -1
    dong = ""
    for d in out.splitlines():
        if d.startswith("KETQUA:"):
            dong = d.strip()
            try:
                dat = int(d.split("ĐẠT")[1].split("·")[0].strip())
                hong = int(d.split("HỎNG")[1].strip())
            except (IndexError, ValueError):
                pass
    return r.returncode, dat, hong, dong


def main() -> int:
    print("=" * 74)
    print("THỬ PHÁ CỔNG 91 — mỗi phép gỡ ĐÚNG MỘT chốt")
    print("=" * 74)
    ma0, dat0, hong0, dong0 = chay_cong()
    print(f"\nĐỐI CHỨNG (chưa phá): {dong0}  ·  mã thoát {ma0}")
    if ma0 != 0:
        print("CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ -> dừng, sửa cổng trước.")
        return 2

    bat = lot = khong_pha = 0
    for ten, f, neo, thay, muc in PHEP:
        goc = doc(f)
        if goc.count(neo) != 1:
            print(f"\n-- {ten}\n   KHÔNG PHÁ ĐƯỢC: neo khớp {goc.count(neo)} "
                  f"chỗ (phải đúng 1) -> LỖI CỦA PHÉP THỬ, không tính LỌT")
            khong_pha += 1
            continue
        ghi(f, goc.replace(neo, thay, 1))
        try:
            ma, dat, hong, dong = chay_cong()
        finally:
            ghi(f, goc)                       # TRẢ LẠI NGUYÊN VĂN, luôn luôn
        if ma != 0:
            bat += 1
            print(f"\n-- {ten}\n   BẮT  (chờ đỏ ở {muc}) · {dong}")
        else:
            lot += 1
            print(f"\n-- {ten}\n   *** LỌT *** (chờ đỏ ở {muc}) · {dong}")

    print("\n" + "=" * 74)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha} "
          f"/ {len(PHEP)} phép")
    ma, dat, hong, dong = chay_cong()
    print(f"KIỂM LẠI SAU KHI TRẢ FILE: {dong} · mã thoát {ma}")
    if (dat, hong) != (dat0, hong0):
        print("!!! FILE CHƯA VỀ NGUYÊN VĂN — kiểm tay ngay.")
        return 2
    return 0 if (lot == 0 and khong_pha == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
