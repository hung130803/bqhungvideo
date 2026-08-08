# -*- coding: utf-8 -*-
r"""Chạy CẢ BỘ CỔNG CHẶN rồi in 1 bảng ĐẠT/FAIL + thời gian + rác để lại.

    .venv\Scripts\python _ra_cong.py                 # bộ đầy đủ (venv dev)
    .venv-build\Scripts\python.exe _ra_cong.py --khach   # bộ chạy được ở venv KHÁCH

VÌ SAO CÓ FILE NÀY: 20+ cổng chạy tay thì dễ bỏ sót và dễ tự lừa ("chắc nó
pass"). Ở đây mã thoát là sự thật duy nhất: != 0 là FAIL.

Đo luôn **rác %TEMP%** trước/sau CẢ BỘ — cổng test từng để lại **887,7 MB**
(commit 4352ac6), và ổ C của anh Hùng đã từng đầy 100%.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

# Cổng chạy được ở MỌI venv (không cần cv2/torch).
CHUNG = [
    ("5  làn cắt không bị bỏ đói", "_test_lane_starve.py", 180),
    ("6  luồng nền không làm sập app", "_test_shutdown_safety.py", 180),
    ("7  HUỶ là HUỶ (không tự chạy lại)", "_test_cancel_persist.py", 300),
    ("8  video 'Cắt cơ bản' phải thử lại AI", "_test_ai_gate.py", 300),
    ("14 mượt + không đứng im", "_test_ui_smooth.py", 300),
    ("17 test không đụng máy user", "_test_no_popup.py", 300),
    ("17b guard tự kiểm", "_test_guard.py", 240),
    ("18 tự dọn rác đĩa + gấp WAL", "_test_don_rac.py", 300),
    ("23 kho tiếng động kêu đúng mốc", "_test_sfx_kho.py", 300),
    ("34 mốc ngoài phim", "_test_moc_ngoai_phim.py", 420),
    ("35 vá lỗ phụ đề", "_test_va_lo_sub.py", 420),
    ("30 chạy hàng trăm kênh phải mượt", "_test_muot_tram_kenh.py", 600),
    ("37 CA BIÊN đường xuất (máy nhân viên)", "_test_ca_bien_xuat.py", 1800),
    ("39 BẢN ĐÓNG GÓI đủ tài nguyên", "_test_dong_goi.py", 300),
    ("-- chồng lượt / hồi phục dây chuyền", "_test_pipe_overlap.py", 900),
]
# Cổng cần venv DEV (cv2 để đếm pixel, PyQt6 dựng UI đầy đủ, Groq…).
# ƯU TIÊN: 24/25/28 đi thẳng qua `chon_doan.nang_luong` + `chuyen_dong` —
# đúng 2 hàm vừa sửa núm luồng, nên PHẢI chạy lại.
CHI_DEV = [
    ("24 AI nghe + xem + trọng tài chấm mù", "_test_chon_doan.py", 1800),
    ("25 tiếng động theo chỗ nối + tên mẫu", "_test_tieng_va_mau.py", 1200),
    ("28 LIÊN THÔNG (2 bản vá đúng -> sai)", "_test_lien_thong.py", 1800),
    ("2  smoke toàn app (66 nút)", "_test_app_smoke.py", 900),
    ("3  mọi hộp thoại dây chuyền", "_test_pipe_dialogs.py", 600),
    ("36 CHUYỂN CẢNH xfade + cửa chờ", "_test_chuyen_canh.py", 2700),
    ("38 HIỆU ỨNG điểm nhấn + AI chọn", "_test_hieu_ung_ai.py", 2700),
]


def rac() -> tuple[int, int]:
    tmp = Path(tempfile.gettempdir())
    n = b = 0
    for k in ("_seg_*", "_MEI*", "_nhip_*", "_gpuchk_*", "test_*", "do_*"):
        for p in tmp.glob(k):
            try:
                if p.is_file():
                    n += 1
                    b += p.stat().st_size
                else:
                    for q in p.rglob("*"):
                        if q.is_file():
                            n += 1
                            b += q.stat().st_size
            except OSError:
                pass
    return n, b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--khach", action="store_true",
                    help="chỉ chạy bộ cổng venv KHÁCH chạy được")
    ap.add_argument("--chi", default="", help="lọc theo tên file")
    a = ap.parse_args()

    ds = CHUNG if a.khach else (CHI_DEV + CHUNG)
    if a.chi:
        ds = [x for x in ds if a.chi in x[1]]
    py = sys.executable
    print("=" * 78)
    print(f"BỘ CỔNG CHẶN — {len(ds)} cổng · python {py}")
    print("=" * 78)
    n0, b0 = rac()
    print(f"rác %TEMP% trước: {n0} file · {b0/1024/1024:.1f} MB\n")

    ket = []
    for ten, f, han in ds:
        if not (REPO / f).exists():
            print(f"  [BỎ ] {ten:44s} — không có file {f}")
            continue
        t0 = time.time()
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            r = subprocess.run([py, f], cwd=str(REPO), capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=han, env=env)
            rc, hethan = r.returncode, False
            ra = (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, hethan, ra = -9, True, "QUÁ HẠN"
        dt = time.time() - t0
        ok = rc == 0 and not hethan
        # lấy dòng tóm tắt cuối cho dễ đọc
        dong = [x for x in ra.splitlines() if x.strip()]
        tom = ""
        for x in reversed(dong[-12:]):
            if any(k in x for k in ("ĐẠT", "OK", "FAIL", "LỖI", "PASS", "✅", "❌")):
                tom = x.strip()[:74]
                break
        print(f"  [{'ĐẠT ' if ok else 'FAIL'}] {ten:44s} {dt:6.1f}s  {tom}")
        if not ok:
            for x in dong[-14:]:
                print(f"         | {x[:100]}")
        ket.append({"ten": ten, "file": f, "rc": rc, "giay": round(dt, 1),
                    "dat": ok, "tom": tom})
        (REPO / f"_ket_{f.replace('.py', '')}.txt").write_text(
            ra, encoding="utf-8", errors="replace")

    n1, b1 = rac()
    n_dat = sum(1 for x in ket if x["dat"])
    print("\n" + "=" * 78)
    print(f"ĐẠT {n_dat}/{len(ket)} cổng · "
          f"tổng {sum(x['giay'] for x in ket)/60:.1f} phút")
    for x in ket:
        if not x["dat"]:
            print(f"   ✗ {x['ten']} (rc={x['rc']})")
    print(f"rác %TEMP% sau: {n1} file · {b1/1024/1024:.1f} MB "
          f"({n1-n0:+d} file · {(b1-b0)/1024/1024:+.1f} MB)")
    print("=" * 78)
    ten_ra = "_ket__ra_cong_khach.json" if a.khach else "_ket__ra_cong.json"
    (REPO / ten_ra).write_text(json.dumps(
        {"cong": ket, "dat": n_dat, "tong": len(ket),
         "rac_truoc_mb": round(b0/1024/1024, 1),
         "rac_sau_mb": round(b1/1024/1024, 1), "python": py},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[đã ghi] {ten_ra}")
    return 0 if n_dat == len(ket) else 1


if __name__ == "__main__":
    sys.exit(main())
