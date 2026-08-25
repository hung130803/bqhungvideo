# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 90 — mỗi phép gỡ ĐÚNG MỘT CHỐT, cổng phải BẮT HẾT.

Cổng nào không có phép thử phá thì nó chỉ là một CON DẤU: nó xanh vì mã đang
đúng, chứ chưa ai chứng minh nó ĐỎ được khi mã sai. Script này dựng lại đúng
những cách người sau có thể vô tình phá bản vá `a0062b6` / `d4968a6`:

    1-3.  gỡ `on_msg` khỏi TỪNG chỗ trong ba chỗ gọi TTS
    4-6.  đổi `on_msg=_nhac` thành HẰNG SỐ `on_msg=None` ở từng chỗ
          (giữ nguyên MẶT CHỮ, đổi NGHĨA — bài học cổng 56d)
    7.    bỏ chốt KHÔNG TỤT LÙI
    8.    làm `ty_le_tung_cau` NÉM với đầu vào xấu
    9.    bỏ chốt KHÔNG NÉM của hàm nhịp
    10.   thôi chuyển tiếp lời báo KHÔNG CÓ SỐ (mất dấu hiệu "còn sống")
    11.   thôi đọc SỐ THẬT trong lời báo (quay về mốc lùi)

BA LUẬT ĐÃ TRẢ GIÁ, GIỮ NGUYÊN:
  * **"Không tìm thấy chỗ phá" = LỖI CỦA PHÉP THỬ**, tách hẳn khỏi cột LỌT.
    File repo là **CRLF** nên chuỗi tìm nhiều dòng viết `\\n` sẽ KHÔNG khớp;
    lượt phá của cổng 54 từng im lặng không phá được gì mà vẫn đếm vào LỌT =
    báo cáo ngược sự thật. Ở đây mọi chuỗi nhiều dòng đi qua `nhieu_dong()`
    (tự lấy kiểu xuống dòng THẬT của file), và phép nào thay 0 chỗ thì bị
    xếp vào cột riêng.
  * **PHẢI CHẠY ĐỐI CHỨNG TRƯỚC.** Cổng đỏ sẵn (vì lý do khác) thì mọi phép
    phá sau đó đều "BẮT" một cách vô nghĩa.
  * **Phá thì GỠ SẠCH chốt, đừng đổi giá trị bên trong nó** — đổi giá trị có
    thể làm hàm CHẶT HƠN, cổng xanh ĐÚNG mà bảng đọc thành "không bắt được"
    (cổng 80 đã sập, LỌT 7 là lỗi của phép thử).

Sửa file rồi HOÀN NGUYÊN bằng `finally` **và** `atexit` (phép phá có thể làm
tiến trình chết giữa đường), cuối cùng còn so lại TỪNG BYTE.

    .venv\\Scripts\\python -u _pha_nhip_doc.py
"""
from __future__ import annotations

import ast
import atexit
import os
import re
import subprocess
import sys
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
DICH = REPO / "app" / "core" / "thay_giong.py"
CONG = REPO / "_test_nhip_doc.py"
PY = str(REPO / ".venv" / "Scripts" / "python.exe")

GOC = DICH.read_bytes()          # bản gốc TỪNG BYTE, kể cả CRLF


def hoan_nguyen() -> None:
    if DICH.read_bytes() != GOC:
        DICH.write_bytes(GOC)


atexit.register(hoan_nguyen)

NGUON = GOC.decode("utf-8")
XUONG_DONG = "\r\n" if "\r\n" in NGUON else "\n"


def nhieu_dong(*dong: str) -> str:
    """Ghép nhiều dòng bằng kiểu xuống dòng THẬT của file (repo này là CRLF)."""
    return XUONG_DONG.join(dong)


def _pham_vi_ham(nguon: str, ten: str) -> tuple[int, int]:
    """(dòng đầu, dòng cuối) 1-based của hàm — để phá ĐÚNG một chỗ gọi.

    Ba chỗ gọi TTS có những dòng GIỐNG HỆT NHAU (`on_msg=_nhac))` xuất hiện ở
    cả bước 5 lẫn 4c với cùng thụt lề), nên thay theo cả file là phá 2 chỗ
    trong một phép — mất luôn ý nghĩa "gỡ ĐÚNG MỘT chốt".
    """
    for n in ast.walk(ast.parse(nguon)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n.lineno, (n.end_lineno or n.lineno)
    return 0, 0


def sua_trong_ham(nguon: str, ten_ham: str, cu: str, moi: str) -> tuple[str, int]:
    """Thay `cu` -> `moi` CHỈ trong thân `ten_ham`. Trả (nguồn mới, số chỗ)."""
    a, b = _pham_vi_ham(nguon, ten_ham)
    if a == 0:
        return nguon, 0
    dong = nguon.splitlines(keepends=True)
    khuc = "".join(dong[a - 1:b])
    n = khuc.count(cu)
    if n != 1:                      # 0 = không có chỗ phá · >1 = phá quá tay
        return nguon, n
    khuc = khuc.replace(cu, moi)
    return "".join(dong[:a - 1]) + khuc + "".join(dong[b:]), 1


# ── Danh sách phép phá: (tên, hàm nhận nguồn -> (nguồn mới, số chỗ)) ────────
def _bo_onmsg(ten_ham: str):
    # Bỏ HẲN keyword `on_msg` khỏi lời gọi (dấu phẩy thừa trước `)` vẫn hợp lệ
    # trong Python nên đây là phép gỡ SẠCH, không phải đổi giá trị).
    return lambda s: sua_trong_ham(s, ten_ham, "on_msg=_nhac", "")


def _hang_so(ten_ham: str):
    return lambda s: sua_trong_ham(s, ten_ham, "on_msg=_nhac", "on_msg=None")


PHEP = [
    ("1. bỏ `on_msg` ở BƯỚC 5 (doc_ban_dich)", _bo_onmsg("doc_ban_dich")),
    ("2. bỏ `on_msg` ở 4b (rut_gon_vua_khung)",
     _bo_onmsg("rut_gon_vua_khung")),
    ("3. bỏ `on_msg` ở 4c (doc_nhanh_vua_khung)",
     _bo_onmsg("doc_nhanh_vua_khung")),
    ("4. `on_msg=None` (hằng số) ở BƯỚC 5", _hang_so("doc_ban_dich")),
    ("5. `on_msg=None` (hằng số) ở 4b", _hang_so("rut_gon_vua_khung")),
    ("6. `on_msg=None` (hằng số) ở 4c", _hang_so("doc_nhanh_vua_khung")),
    ("7. bỏ chốt KHÔNG TỤT LÙI",
     lambda s: sua_trong_ham(s, "_nhac_tung_cau",
                             'p = max(p, cao["p"])', "p = p")),
    ("8. `ty_le_tung_cau` NÉM với đầu vào xấu",
     lambda s: sua_trong_ham(s, "ty_le_tung_cau",
                             '_RE_TUNG_CAU.search(str(m or ""))',
                             "_RE_TUNG_CAU.search(m)")),
    ("9. bỏ chốt KHÔNG NÉM của hàm nhịp",
     lambda s: sua_trong_ham(
         s, "_nhac_tung_cau",
         nhieu_dong(
             "        try:",
             "            on_progress(max(0.0, min(1.0, dau + rong * p)),"
             " str(m)[:150])",
             "        except Exception:  # noqa: BLE001",
             "            pass"),
         "        on_progress(max(0.0, min(1.0, dau + rong * p)),"
         " str(m)[:150])")),
    ("10. thôi chuyển tiếp lời báo KHÔNG CÓ SỐ",
     lambda s: sua_trong_ham(
         s, "_nhac_tung_cau", "        p = ty_le_tung_cau(m)",
         nhieu_dong("        p = ty_le_tung_cau(m)",
                    "        if p <= 0.0:",
                    "            return"))),
    ("11. thôi đọc SỐ THẬT trong lời báo",
     lambda s: sua_trong_ham(s, "_nhac_tung_cau",
                             "p = ty_le_tung_cau(m)", "p = 0.0")),
]

_RE_TK = re.compile(r"ĐẠT\s+(\d+)\s*·\s*HỎNG\s+(\d+)")


def chay_cong() -> tuple[int, int, int, str]:
    """Chạy cổng 90. Trả (mã thoát, ĐẠT, HỎNG, dòng tổng kết)."""
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    r = subprocess.run([PY, "-u", str(CONG)], cwd=str(REPO), env=e,
                       capture_output=True, timeout=900)
    ra = (r.stdout or b"").decode("utf-8", "replace")
    g = _RE_TK.search(ra)
    if not g:
        return r.returncode, -1, -1, "KHÔNG CÓ DÒNG TỔNG KẾT"
    return r.returncode, int(g.group(1)), int(g.group(2)), g.group(0)


print("=" * 74)
print("THỬ PHÁ CỔNG 90 — _test_nhip_doc.py")
print("=" * 74)

print("\n── ĐỐI CHỨNG: cổng phải XANH TRƯỚC khi phá ──")
rc0, dat0, hong0, tk0 = chay_cong()
print(f"   {tk0}  ·  mã thoát {rc0}")
if rc0 != 0 or hong0 != 0:
    print("\n!! CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ — dừng. Mọi phép sau đó sẽ 'BẮT' vô")
    print("   nghĩa. Chữa cổng/mã trước rồi chạy lại.")
    sys.exit(2)

BAT: list[str] = []
LOT: list[str] = []
KHONG_PHA: list[str] = []

for ten, sua in PHEP:
    print(f"\n── PHÉP {ten} ──")
    try:
        moi, n = sua(NGUON)
    except Exception as e:  # noqa: BLE001
        print(f"   LỖI CỦA PHÉP THỬ: {type(e).__name__}: {e}")
        KHONG_PHA.append(ten)
        continue
    if n != 1 or moi == NGUON:
        print(f"   KHÔNG PHÁ ĐƯỢC — tìm thấy {n} chỗ (cần đúng 1). Đây là "
              f"LỖI CỦA PHÉP THỬ, KHÔNG phải cổng lọt.")
        KHONG_PHA.append(ten)
        continue
    try:
        DICH.write_text(moi, encoding="utf-8", newline="")
        rc, dat, hong, tk = chay_cong()
    finally:
        hoan_nguyen()
    if rc != 0 and hong > 0:
        print(f"   BẮT — {tk} · mã thoát {rc}")
        BAT.append(ten)
    elif rc != 0:
        print(f"   BẮT (cổng chết/không tổng kết) — {tk} · mã thoát {rc}")
        BAT.append(ten)
    else:
        print(f"   *** LỌT *** — {tk} · mã thoát {rc}. Mục cổng THIẾU RĂNG: "
              f"chữa MỤC, đừng chữa phép phá.")
        LOT.append(ten)

hoan_nguyen()
nguyen_ven = DICH.read_bytes() == GOC

print("\n" + "=" * 74)
print(f"THỬ PHÁ CỔNG 90 — BẮT {len(BAT)} · LỌT {len(LOT)} · "
      f"KHÔNG PHÁ ĐƯỢC {len(KHONG_PHA)}")
for t in LOT:
    print(f"   LỌT: {t}")
for t in KHONG_PHA:
    print(f"   KHÔNG PHÁ ĐƯỢC (lỗi phép thử): {t}")
print(f"Hoàn nguyên TỪNG BYTE: {'SẠCH' if nguyen_ven else 'CHƯA SẠCH — SỬA NGAY'}")
print("=" * 74)
sys.exit(0 if (not LOT and not KHONG_PHA and nguyen_ven) else 1)
