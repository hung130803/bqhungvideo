# -*- coding: utf-8 -*-
"""THỬ PHÁ cổng 56 — chứng minh cổng KHÔNG PHẢI CON DẤU.

Mỗi phép phá gỡ ĐÚNG MỘT mắt xích của đường editor -> mẫu -> m1 ->
export_canvas_clip, chạy lại cổng, rồi TRẢ FILE VỀ NGUYÊN TRẠNG.
Cổng phải HỎNG ở mỗi phép; phép nào cổng vẫn xanh là phép đó KHÔNG được canh.

BÀI HỌC CỦA CỔNG 54 ĐÃ CHÉP LẠI Ở ĐÂY: file repo là **CRLF**, nên chuỗi tìm
nhiều dòng viết `\\n` sẽ KHÔNG khớp và phép phá âm thầm không phá được gì. Nếu
đếm ca đó vào cột "LỌT" thì báo cáo NGƯỢC SỰ THẬT. Nay "không tìm thấy chỗ
phá" = **LỖI CỦA PHÉP THỬ**, in ra riêng một cột.

Chạy: .venv\\Scripts\\python _pha_che_chu.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PY = sys.executable
_NOWIN = 0x0800_0000 if os.name == "nt" else 0

#: (tên, file, chuỗi TÌM, chuỗi THAY, ca cổng cần chạy)
PHEP = [
    ("m1 KHÔNG truyền cờ vào export_canvas_clip",
     "app/modules/m1_highlight.py",
     "            che_chu=_cc_cf[\"bat\"],", "            che_chu=False,",
     "tinh"),
    ("export_canvas_clip nhận cờ rồi BỎ (không chèn filter)",
     "app/core/ffmpeg_utils.py",
     "            parts.append(f\"{content}{_cc_loc}[cche]\")",
     "            pass",
     "tinh"),
    ("gỡ SÀN 0,60 (cho lọt mức 0,30)",
     "app/core/che_chu.py",
     "    return max(MUC_MO_SAN, min(MUC_MO_TRAN, v))",
     "    return max(0.0, min(MUC_MO_TRAN, v))",
     "tinh"),
    ("editor KHÔNG lưu cờ vào mẫu",
     "app/ui/editor.py",
     "        lay[\"che_chu\"] = self.che_chu_chk.isChecked()",
     "        lay[\"che_chu\"] = False",
     "tinh"),
    ("editor cho kéo mức mờ xuống 0,00",
     "app/ui/editor.py",
     "        self.che_chu_muc.setRange(int(CHE_CHU_SAN * 100),",
     "        self.che_chu_muc.setRange(int(0 * 100),",
     "tinh"),
    # PHẢI phá ĐÚNG DÒNG KẸP, không phải dòng tính. Lượt đầu tôi phá dòng
    # `r = max(1, ...)` -> cổng vẫn XANH và tôi suýt ghi "cổng không canh chỗ
    # này": thật ra dòng KẸP mới (`min(r, max(1,w//2), max(1,h//2))`) đã tự kéo
    # bán kính về giá trị hợp lệ, tức phép phá KHÔNG phá được gì. Bản HỎNG thật
    # là dòng kẹp có `max(2, ...)` ở cả hai vế.
    ("trả bán kính boxblur về bản HỎNG (dải nhỏ giết lượt xuất)",
     "app/core/che_chu.py",
     "        r = min(r, max(1, w // 2), max(1, h // 2))",
     "        r = min(r, max(2, w // 2 - 1), max(2, h // 2 - 1))",
     "tinh"),
    ("BẤT BIẾN: chèn filter kể cả khi TẮT",
     "app/core/ffmpeg_utils.py",
     "    if che_chu:\n        _raise_if_job_canceled()",
     "    if True:\n        _raise_if_job_canceled()",
     "batbien"),
    # ---- 3 phép của ĐƯỜNG TRUYỀN CỜ (v2.26.0, xem CA 23) ----
    # Đây là 3 cách "gỡ bản vá mà app vẫn chạy y hệt": clip vẫn ra đúng, chỉ
    # mỗi chuyện anh Hùng bật ô rồi bấm "Xuất cả kênh" là KHÔNG job nào chạy.
    ("studio_page truyền HẰNG SỐ che_chu=False (phép phá của CA19a, lần này ở "
     "mắt xích UI)",
     "app/ui/studio_page.py",
     "                che_chu=bool(self.layout_tpl.get(\"che_chu\", False)),",
     "                che_chu=False,",
     "hash"),
    ("studio_page KHÔNG truyền cờ nữa (quay về đường LÙI của v2.25.0)",
     "app/ui/studio_page.py",
     "                che_chu=bool(self.layout_tpl.get(\"che_chu\", False)),\n",
     "",
     "hash"),
    ("cờ KHÔNG vào `sig` (đúng bệnh smart-skip của v2.25.0)",
     "app/services.py",
     "    _cc_sig = \"\"\n    if che_chu:",
     "    _cc_sig = \"\"\n    if False and che_chu:",
     "hash"),
]


def chay(ca: str) -> tuple:
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               QT_QPA_PLATFORM="offscreen", BQ_FFMPEG_SLOTS="1")
    r = subprocess.run([PY, str(REPO / "_pha_che_chu_chay.py"), ca],
                       capture_output=True, env=env, creationflags=_NOWIN,
                       timeout=1800)
    out = (r.stdout or b"").decode("utf-8", "replace")
    n = out.count("HỎNG ")
    return r.returncode, n, out


def main() -> int:
    (REPO / "_pha_che_chu_chay.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, r'{REPO}')\n"
        "import _test_che_chu as T\n"
        "T.SAN.mkdir(parents=True, exist_ok=True)\n"
        "ca = sys.argv[1]\n"
        "if ca == 'tinh':\n"
        "    T.ca19_pha_duong_truyen()\n"
        "    T.ca21_dai_nho_khong_lam_chet_xuat()\n"
        "    T.ca18_round_trip_ui()\n"
        "    that = T._nguon_that()\n"
        "    if that: T.ca15_bat_tat_co_tac_dung(that)\n"
        "elif ca == 'batbien':\n"
        "    T.ca16_bat_bien(T._nguon_that())\n"
        "elif ca == 'hash':\n"
        "    T.ca23_co_vao_hash_chong_trung()\n"
        "print('DAT', len(T.DAT), 'HONG', len(T.HONG))\n"
        "sys.exit(1 if T.HONG else 0)\n", encoding="utf-8")
    print("=== ĐỐI CHỨNG: chưa phá gì ===")
    for _ca in ("tinh", "hash"):
        rc, n, _ = chay(_ca)
        print(f"  cổng ({_ca}): mã thoát {rc} · {n} mục HỎNG "
              f"-> {'XANH' if rc == 0 else 'ĐỎ'}")
    bat, lot, hong_thu = [], [], []
    for ten, f, tim, thay, ca in PHEP:
        p = REPO / f
        goc = p.open("r", encoding="utf-8", newline="").read()
        # CRLF: chuỗi nhiều dòng viết `\n` KHÔNG khớp file repo -> phải thử cả 2
        t2 = tim if tim in goc else tim.replace("\n", "\r\n")
        if t2 not in goc:
            hong_thu.append(ten)
            print(f"  LỖI PHÉP THỬ (không tìm thấy chỗ phá): {ten}")
            continue
        moi = goc.replace(t2, thay.replace("\n", "\r\n")
                          if "\r\n" in t2 else thay, 1)
        p.open("w", encoding="utf-8", newline="").write(moi)
        try:
            rc, n, out = chay(ca)
        finally:
            p.open("w", encoding="utf-8", newline="").write(goc)
        (bat if rc != 0 else lot).append(ten)
        print(f"  {'BẮT ĐƯỢC' if rc != 0 else '*** LỌT ***'} · {n} mục HỎNG "
              f"· {ten}")
        if rc == 0:
            print("      (cổng vẫn XANH -> mắt xích này KHÔNG được canh)")
    (REPO / "_pha_che_chu_chay.py").unlink(missing_ok=True)
    print(f"\nBẮT ĐƯỢC {len(bat)}/{len(PHEP)} · LỌT {len(lot)} · "
          f"LỖI PHÉP THỬ {len(hong_thu)}")
    for x in lot:
        print(f"  LỌT: {x}")
    for x in hong_thu:
        print(f"  LỖI PHÉP THỬ: {x}")
    return 1 if (lot or hong_thu) else 0


if __name__ == "__main__":
    sys.exit(main())
