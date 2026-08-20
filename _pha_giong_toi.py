# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 88 — gỡ ĐÚNG MỘT chốt mỗi lượt, đòi cổng phải ĐỎ.

Cổng xanh KHÔNG chứng minh gì cả nếu chưa ai thử phá nó. Repo này đã có 2 cổng
**PASS OAN** bị lôi ra bằng đúng cách này (`_test_hlbox` so nó với chính nó ·
`_test_hieu_ung_khung` không hỏi CHIỀU).

═══════════════════════════════════════════════════════════════════════════
BA LUẬT CỦA PHÉP PHÁ, cả ba đều từ lỗi THẬT của lượt trước
═══════════════════════════════════════════════════════════════════════════
1. **NEO PHẢI DUY NHẤT.** Kiểm `count()` TRƯỚC khi thay. Chuỗi có ở 2 chỗ thì
   phép phá đánh vào HÀM KHÁC rồi báo cáo ngược sự thật — mất một lượt vì
   chuyện này.
2. **"KHÔNG TÌM THẤY CHỖ PHÁ" = LỖI CỦA PHÉP THỬ**, tách hẳn khỏi "LỌT". File
   repo là **CRLF** nên neo nhiều dòng viết `\\n` KHÔNG khớp; bản đầu của
   `_pha_dubbing_cjk` đếm 4 phép không-phá-được vào cột LỌT (cổng 54).
3. **PHÁ THÌ GỠ SẠCH CHỐT, đừng đổi giá trị bên trong nó.** `_pha_xoa_nham`
   đổi một biến thành đường dẫn không bao giờ khớp -> hàm hoá ra CHẶT HƠN, cổng
   xanh ĐÚNG mà bảng đọc thành "cổng không bắt được" (cổng 80 LỌT 7).

Chạy: .venv\\Scripts\\python -u _pha_giong_toi.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NB = REPO / "app" / "core" / "nhan_ban_giong.py"
UI = REPO / "app" / "ui" / "thay_giong_dialog.py"
CONG = REPO / "_test_giong_toi.py"

#: (tên phép phá, file, neo, thay bằng, mục cổng PHẢI đỏ)
PHEP: list[tuple[str, Path, str, str, str]] = [
    ("1. combo KHÔNG gọi `nhan_ban_giong.danh_sach()` "
     "(giọng lưu được mà không hiện ra)",
     UI, "for j, (ma_g, nhan_g) in enumerate(nhan_ban_giong.danh_sach()):",
     "for j, (ma_g, nhan_g) in enumerate([]):", "1d / 9k"),

    ("2. sổ HỎNG thì KHÔNG sao lưu, ghi đè luôn (mất sạch tên giọng)",
     NB, "        _sao_luu_neu_hong(p)", "        pass", "3b"),

    ("3. `_muc()` trả thẳng mục thô (bản cũ — mục lạ làm nổ cả combo)",
     NB, "    return g if isinstance(g, dict) else {}",
     "    return g", "3c"),

    ("4. `sua_mau_mat` hỏi `Path(...).exists()` mà KHÔNG hỏi chuỗi rỗng "
     "trước (bản cũ — `Path(\"\").exists()` là True)",
     NB, "        if not mau or not Path(mau).exists():",
     "        if not Path(mau).exists():", "3d"),

    ("5. `xoa()` tự canh thay vì đi qua `xoa_an_toan` (cửa thứ 6 của lớp "
     "bệnh `Path(\"\")`)",
     NB, "            from app.core.xoa_an_toan import an_toan_de_xoa",
     "            an_toan_de_xoa = lambda p, trong=None: True", "6a"),

    ("6. `_dung_combo_giong` bỏ tham số `giu_dang_chon` (quay về đọc "
     "QSettings -> nuốt giọng vừa thêm)",
     UI, "    def _dung_combo_giong(self, giu_dang_chon: bool = False) -> None:",
     "    def _dung_combo_giong(self) -> None:", "10a"),

    ("7. `_mo_giong_toi` KHÔNG truyền `giu_dang_chon=True`",
     UI, "        h.so_doi.connect(lambda: self._dung_combo_giong("
         "giu_dang_chon=True))",
     "        h.so_doi.connect(lambda: self._dung_combo_giong())", "10c"),

    ("8. nhãn giọng mang EMOJI (máy anh Hùng thiếu glyph -> Ô ĐEN)",
     NB, '    return (f"{chua}{ten} (giọng nhân bản, {ten_may}, "',
     '    return (f"{chua}\\U0001F4CB {ten} (giọng nhân bản, {ten_may}, "',
     "8b"),

    ("9. nhãn giọng DÀI ra 150 ký tự (đẩy mất cảnh báo 'cần tải' — bệnh "
     "Kokoro 139-178)",
     NB, '            f"mẫu {_so_giay(g):.0f} giây){mat}")',
     '            f"mẫu {_so_giay(g):.0f} giây){mat}"'
     ' + " · " + "x" * 60)', "8d"),
]


def chay_cong() -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-u", str(CONG)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800,
                       creationflags=(0x08000000 if sys.platform == "win32"
                                      else 0))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("=" * 74)
    print("THỬ PHÁ CỔNG 88 — mỗi phép gỡ ĐÚNG MỘT chốt")
    print("=" * 74)

    ma, out = chay_cong()
    if ma != 0:
        print("DỪNG: cổng đang ĐỎ SẴN, phá nữa thì không đọc được gì.")
        print(out[-1500:])
        return 2
    print("Cổng bản GỐC: XANH (mã 0) — bắt đầu phá\n")

    bat: list[str] = []
    lot: list[str] = []
    hong_phep: list[str] = []

    for ten, f, neo, thay, muc in PHEP:
        goc = f.read_text(encoding="utf-8")
        n = goc.count(neo)
        print("-" * 74)
        print(f"PHÉP PHÁ {ten}")
        print(f"  neo xuất hiện {n} lần trong {f.name}")
        # LUẬT 1 + LUẬT 2: neo không duy nhất / không tìm thấy => LỖI CỦA PHÉP
        # THỬ, KHÔNG phải "cổng để lọt".
        if n != 1:
            hong_phep.append(f"{ten} — neo xuất hiện {n} lần (cần ĐÚNG 1)")
            print(f"  LỖI CỦA PHÉP THỬ: neo {n} lần, bỏ qua (KHÔNG tính LỌT)")
            continue
        luu = f.with_suffix(f.suffix + ".pha_bak")
        shutil.copyfile(f, luu)
        try:
            f.write_text(goc.replace(neo, thay), encoding="utf-8")
            ma2, out2 = chay_cong()
            do = ma2 != 0
            print(f"  cổng -> mã {ma2} · {'ĐỎ (BẮT ĐƯỢC)' if do else 'XANH (LỌT)'}"
                  f" · mục canh: {muc}")
            for d in out2.splitlines():
                if d.strip().startswith("HỎNG:"):
                    print(f"      {d.strip()[:130]}")
            (bat if do else lot).append(f"{ten} [mục {muc}]")
        finally:
            shutil.copyfile(luu, f)
            luu.unlink(missing_ok=True)

    print("\n" + "=" * 74)
    print(f"THỬ PHÁ: BẮT {len(bat)} · LỌT {len(lot)} · "
          f"KHÔNG PHÁ ĐƯỢC {len(hong_phep)}")
    for x in lot:
        print("  LỌT (cổng là con dấu ở chỗ này): " + x)
    for x in hong_phep:
        print("  LỖI CỦA PHÉP THỬ: " + x)
    print("=" * 74)

    ma3, _ = chay_cong()
    print(f"Cổng sau khi phục hồi: mã {ma3} "
          f"({'XANH — đã trả nguyên' if ma3 == 0 else 'ĐỎ — CÒN SÓT BẢN PHÁ!'})")
    return 0 if (not lot and not hong_phep and ma3 == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
