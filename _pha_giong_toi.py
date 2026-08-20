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
VNC = REPO / "app" / "core" / "giong_vieneu.py"
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

    # NEO ĐÃ ĐỔI 20/08/2026: VIỆC 1 tách phần đuôi nhãn ra biến `duoi` (để
    # `nhan()` còn đo được dòng THẬT), nên neo cũ (`return (f"{chua}{ten} ...`)
    # còn **0 lần** -> phép này rơi vào cột "KHÔNG PHÁ ĐƯỢC". Đó đúng là LUẬT 2
    # của file này làm việc: neo mất KHÔNG được đếm thành "cổng để lọt".
    ("8. nhãn giọng mang EMOJI (máy anh Hùng thiếu glyph -> Ô ĐEN)",
     NB, '    duoi = (f"{ten} (giọng nhân bản, {ten_may}, "',
     '    duoi = (f"\\U0001F4CB {ten} (giọng nhân bản, {ten_may}, "',
     "8b"),

    ("9. nhãn giọng DÀI ra 150 ký tự (đẩy mất cảnh báo 'cần tải' — bệnh "
     "Kokoro 139-178)",
     NB, '            f"mẫu {_so_giay(g):.0f} giây){mat}")',
     '            f"mẫu {_so_giay(g):.0f} giây){mat}"'
     ' + " · " + "x" * 60)', "8d"),

    # ═══ CA 12 — NÚT TẢI PHẦN NHÂN BẢN ═══
    ("10. nút tải BÁM CỜ \"máy này chạy được\" thay vì bám `thieu` — CHÍNH "
     "cái bẫy đã đẻ ra việc này: máy dev có torch -> nút BIẾN MẤT -> không ai "
     "bấm -> bản .exe mãi mãi thiếu (cổng 58 + hàng Kokoro)",
     UI, "        self.b_tai_nb.setVisible(True)",
     "        self.b_tai_nb.setVisible(not VN_C.co_vieneu())", "12h"),

    ("11. gỡ `--ignore-installed` khỏi LỆNH pip (pip coi gói của môi trường "
     "đang chạy là 'đã thoả mãn' rồi BỎ QUA -> đích rỗng mà báo cài xong)",
     VNC, '                    "--ignore-installed",', "", "12d"),

    ("12. hậu kiểm bị gỡ — tin thẳng mã thoát của pip (đúng cách `_lib` báo "
     "'cài xong' trong khi rỗng torch)",
     VNC, "            thieu = thieu_nhan_ban()", "            thieu = []",
     "12f"),

    ("13. hộp xác nhận + tooltip ghi MỘT SỐ KHÁC nhãn nút (đúng lỗi cổng 58: "
     "nút 155 MB, hộp doạ 2 GB)",
     UI, "            return VN_C.so_mb(VN_C.mb_nhan_ban())",
     '            return "155"', "12l"),

    ("14. nút KHÔNG còn khoá theo `cai_duoc` (máy không có Python 3 vẫn bấm "
     "được rồi im)",
     UI, '            bool(tt.get("cai_duoc")) and not self._dang_cai_nb)',
     "            not self._dang_cai_nb)", "12m"),

    ("15. bộ dò NÉM thì hộp CHẾT theo (bỏ lưới an toàn quanh "
     "`tinh_trang_nhan_ban`)",
     UI, "        except Exception as e:  # noqa: BLE001 - dò hỏng KHÔNG "
         "được giết hộp",
     "        except ZeroDivisionError as e:  # noqa: BLE001", "12o"),

    ("16. nhãn ca CÀI DỞ không nêu tên gói và không nêu số MB (quay về "
     "'chưa cài' trơn — người dùng không biết bấm gì)",
     VNC, "        return f\"Cài tiếp phần còn thiếu "
          "({', '.join(la_goi)} — {duoi})\"",
     '        return "Cài tiếp phần còn thiếu"', "12i / 12l"),

    ("17. cài vào `.venv` CỦA APP thay vì venv VieNeu (một lượt pip install "
     "torch khác bản có thể phá app đang chạy sản xuất 300 kênh)",
     VNC, '            args = [str(vpy), "-m", "pip", "install", "--no-input",',
     '            args = [sys.executable, "-m", "pip", "install", '
     '"--no-input",', "12e"),

    # Gắn emoji vào nhánh "chưa cài lần nào" — nhánh mà mục 12j (chỉ soi ca
    # CÀI DỞ) KHÔNG nhìn tới. Lượt phá đầu chứng minh đúng vậy: 12j LỌT, chỉ
    # có 9c bắt hộ. Nay có 12j'' soi cả ba nhánh nhãn.
    ("18. nhãn nút mang EMOJI ở nhánh 'chưa cài lần nào' (máy anh Hùng thiếu "
     "glyph -> Ô ĐEN)",
     VNC, '    return f"Tải phần nhân bản giọng ({\', \'.join(goi)} — {duoi})"',
     '    return f"\\U0001F4CB Tải phần nhân bản giọng '
     '({\', \'.join(goi)} — {duoi})"', "12j'' / 9c"),

    # LỖI THẬT, bắt được ở lượt CHẠY THẬT đầu tiên (`_do_cai_nhan_ban.py`):
    # `.replace(",", ".")` trên CẢ CÂU làm dấu phẩy tiếng Việt thành dấu chấm
    # -> *"(khoảng 126 MB. tải 1 lần)"*.
    ("20. đổi dấu nghìn trên CẢ CÂU thay vì chỉ con số (dấu phẩy tiếng Việt "
     "thành dấu chấm — đã in ra thật ở lượt tải đầu)",
     VNC, '                        "1 lần)..."))',
     '                        "1 lần)...").replace(",", "."))', "12l'''"),

    # Neo MỘT DÒNG (LUẬT 2 của file này: repo là CRLF nên neo nhiều dòng dễ
    # trượt). `tt = self._do_nhan_ban()` chỉ có ĐÚNG 1 lần — đã đếm trước.
    ("19. tải xong thì DỰNG LẠI COMBO (`_dung_combo_giong` đọc giá trị ĐÃ "
     "LƯU -> nuốt mất giọng user vừa bấm mà chưa lưu = họ lỗi 'chọn X ra Y')",
     UI, "        tt = self._do_nhan_ban()",
     "        tt = self._do_nhan_ban()\n        self._dung_combo_giong()",
     "12s"),

    # ═══ VIỆC 2 — VÒNG TỰ DÒ ═══
    # ĐÂY LÀ MỘT PHÉP PHÁ HAI-CHỐT, VÀ ĐÓ LÀ CỐ Ý — đọc kẻo "sửa cho đúng luật".
    # Lọc tên gói có HAI lớp **thừa nhau có chủ đích**: char class của
    # `_RE_THIEU`, và `re.fullmatch` sau khi `split(".")`. Đo được: gỡ MỘT lớp
    # thì lớp còn lại vẫn chặn sạch cả 4 tên rác -> cổng XANH ĐÚNG, và bảng sẽ
    # đọc thành "LỌT" oan (đúng bẫy LUẬT 3 của file này). Nên phép này gỡ CẢ
    # HAI để chấm đúng cái tính chất *"tên rác không bao giờ tới được pip"*.
    # Gỡ một lớp là chuyện KHÔNG cổng nào bắt, và đó là ĐÁNH ĐỔI ĐÃ BIẾT: hai
    # lớp thừa nhau thì rẻ hơn một lớp có cổng canh.
    ("21. gỡ CẢ HAI lớp lọc tên gói (lời lỗi là chuỗi từ TIẾN TRÌNH CON -> "
     "đưa thẳng vào dòng lệnh pip là một cửa tiêm lệnh)",
     VNC, "    goc = m.group(1).split(\".\")[0].strip()\n"
          "    return goc if re.fullmatch(r\"[A-Za-z0-9_\\-]+\", goc) else \"\"",
     "    return m.group(1).strip()", "13d"),

    ("23. bỏ DANH SÁCH CHẶN (cài cả `gradio`/`triton` — hai thứ không dính gì "
     "tới một lượt ĐỌC TIẾNG, và triton không build được trên Windows)",
     VNC, '    t = ten.lower().replace("-", "_")', '    return ""\n'
     '    t = ten.lower().replace("-", "_")', "13f / 13k"),

    ("22. bỏ TRẦN vòng lặp (`while True` — một vòng lặp không trần trên đường "
     "mạng là treo máy anh Hùng cả đêm)",
     VNC, "                while vong < TRAN_VONG_DO:",
     "                while True:", "13j"),

    ("24. `do_wav` mừng theo ĐỘ DÀI, bỏ ngưỡng RMS (quay về đúng chỗ hổng: "
     "`doc_loat` trả True chỉ nghĩa là file TỒN TẠI, không phải CÓ TIẾNG)",
     VNC, '    ra["co_tieng"] = bool(ra["giay"] >= 0.3 and ra["rms"] >= 0.001)',
     '    ra["co_tieng"] = bool(ra["giay"] >= 0.3)', "13h"),

    ("25. vòng tự dò đi đường GIỌNG DỰNG SẴN (`voice=` thay vì `ref_audio=`) "
     "— đường đó KHÔNG đụng torch nên lượt tự kiểm XANH OAN",
     VNC, '    ket = _chay_vieneu(items, str(vpy), "", mau, han_giay, None)',
     "    ket = _chay_vieneu(items, str(vpy), ma_nhan_ban(mau), '', "
     "han_giay, None)", "13i"),

    # ═══ VIỆC 3 — NÚT TẢI BỘ VieNeu ═══
    ("26. UI KHÔNG gọi `cai_vieneu` nữa (đúng trạng thái TRƯỚC lượt này: "
     "chuỗi ĐỨT, nút nhân bản bảo 'tải bộ đó trước' mà không có chỗ bấm)",
     UI, "                r = VN_C.cai_vieneu(",
     "                r = dict(ok=False, loi='x') or (", "14a"),

    ("27. nút bước 1 luôn ẨN (ẩn nút là CHÍNH cách tính năng đã chết một lần)",
     UI, "        self.b_tai_vn.setVisible(True)\n"
     "        self.b_tai_vn.setText(VN_C.nhan_tai_vieneu(thieu))",
     "        self.b_tai_vn.setVisible(False)\n"
     "        self.b_tai_vn.setText(VN_C.nhan_tai_vieneu(thieu))", "14l"),

    ("28. nút bước 1 KHÔNG còn khoá theo `cai_duoc` (máy không có Python 3 "
     "vẫn bấm được rồi nhận một lời lỗi)",
     UI, "        self.b_tai_vn.setEnabled(\n"
     "            bool(tt.get(\"cai_duoc\")) and not self._dang_cai_vn)",
     "        self.b_tai_vn.setEnabled(True)", "14n"),

    ("29. bước 2 KHÔNG tự chạy khi bước 1 xong (chuỗi đứt giữa: máy trắng "
     "bấm một lần không đi hết được)",
     UI, "            self._tai_nhan_ban(da_dong_y=True)", "            pass",
     "14i"),

    # ═══ VIỆC 4 — RA KHỎI %TEMP% ═══
    ("30. UI KHÔNG hiện cảnh báo `%TEMP%` nữa (chỉ ghi log = không ai đọc; "
     "một lượt Disk Cleanup là giọng biến khỏi combo)",
     UI, '                + (("\\n" + o_tam) if o_tam else ""))',
     "                )", "15g"),
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

    # DỌN HỘP CÁT MỒ CÔI — việc của FILE NÀY, không phải của cổng.
    # `_test_giong_toi._don_hop_cat` đã đăng ký `atexit` mà VẪN sót: phép phá
    # số 15 gỡ lưới an toàn quanh bộ dò nên `HopGiongToi.__init__` NÉM giữa lúc
    # dựng widget, rồi một QDialog dựng dở bị thu gom làm Qt chết CỨNG lúc
    # tiến trình tắt — `atexit` không chạy khi access violation. Đo được: 2 thư
    # mục mỗi lượt phá 20 phép. IN RA SỐ chứ không dọn im lặng (dọn mà không
    # nói thì lần sau lại phải đi đếm thư mục — bài học rò `_seg_*` cổng 42).
    rac = sorted(REPO.glob("bq_test_giong_toi_*"))
    for d in rac:
        shutil.rmtree(d, ignore_errors=True)
    con = [d.name for d in REPO.glob("bq_test_giong_toi_*")]
    if rac:
        print(f"Dọn hộp cát mồ côi do lượt phá để lại: {len(rac)} thư mục"
              + (f" — CÒN SÓT {con}" if con else " (sạch)"))
    return 0 if (not lot and not hong_phep and ma3 == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
