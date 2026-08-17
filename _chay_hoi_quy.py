# -*- coding: utf-8 -*-
"""CHẠY CẢ LƯỢT HỒI QUY, IN **MÃ THOÁT THẬT** CỦA TỪNG CỔNG.

BA CÁI BẪY FILE NÀY CỐ Ý TRÁNH (đều đã sập ít nhất một lần trong repo):
 1. **Nối `| tail` là NUỐT MÃ THOÁT** — mã thoát thấy được sẽ là của `tail`.
    Đây gọi `subprocess.run` rồi in `returncode` nguyên vẹn.
 2. **cp1252**: chạy hồi quy mà đổ ra file thì `print` tiếng Việt nổ
    `UnicodeEncodeError` -> cổng chết trong 0-1 giây, chạy tay lại xanh. Ép
    `PYTHONIOENCODING=utf-8` cho MỌI tiến trình con.
 3. **"xanh" vì chạy chưa tới chốt**: cổng chết sớm cũng có thể rc=0 nếu nó
    thoát trước phần kiểm. Nên in kèm **thời gian chạy** và **dòng tổng kết
    ĐẠT/HỎNG** dò được — rc=0 mà 0 giây / không có dòng tổng kết là ĐÁNG NGỜ.

    .venv\\Scripts\\python -u _chay_hoi_quy.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")

#: (nhãn, file, mốc ĐẠT mong đợi hoặc None)
CONG = [
    ("66 độ to đường xuất", "_test_do_to_xuat.py",       50),
    ("65 độ to + nghe thử", "_test_do_to_nghe_thu.py",   47),
    ("64 Piper",            "_test_piper.py",           47),
    ("63 biến thể giọng",   "_test_bien_the_giong.py",  24),
    ("62 quét cả khung",    "_test_toan_khung.py",      33),
    ("60 chữ theo lời",     "_test_chu_theo_loi.py",    42),
    ("59 đường dài",        "_test_duong_dai.py",       46),
    ("57 bảng tiến độ",     "_test_tg_bang_tiendo.py",  57),
    ("56 che chữ",          "_test_che_chu.py",        123),
    ("55 thay giọng UI",    "_test_thay_giong_ui.py",   48),
    ("54 dubbing CJK",      "_test_dubbing_cjk.py",     44),
    ("53 thay giọng",       "_test_thay_giong.py",      44),
    ("52 CJK vá",           "_test_cjk_va.py",          46),
    ("52b mảnh cuối",       "_test_manh_cuoi.py",     None),
    ("31 nút không cụt",    "_test_nut_khong_cut.py", None),
    ("và/lỡ phụ đề",        "_test_va_lo_sub.py",       16),
    ("không popup",         "_test_no_popup.py",      None),
    ("làn cắt đói",         "_test_lane_starve.py",   None),
    ("smoke",               "_test_app_smoke.py",     None),
]

#: Dòng tổng kết — mỗi cổng viết một kiểu, có cổng bỏ dấu tiếng Việt
#: ("DAT 42 · HONG 0"). Bắt hụt thì cột ĐẠT ra "?" và cổng bị gắn nhãn ĐÁNG
#: NGỜ oan; đã dính một lượt với cổng 60/63.
_RE_TK = re.compile(r"(?:ĐẠT|DAT|OK)\s+(\d+)\s*[·.]\s*"
                    r"(?:HỎNG|HONG|SAI)\s+(\d+)")


def moi_truong() -> dict:
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["BQ_FFMPEG_SLOTS"] = "1"
    # KHÔNG dùng `main`: sau khi gộp thì mốc CHÍNH LÀ bản đang test -> cổng
    # đối chứng tự PASS OAN vĩnh viễn.
    #
    # VÌ SAO `v2.25.0` CHỨ KHÔNG `v2.26.0` (đã chạy nhầm một lượt, cổng bắt
    # được): mục CA23-3'' của cổng 56 đòi **bản mốc phải có TRƯỚC tính năng
    # che chữ** — không thì phép so "bật/tắt che chữ vẫn ra cùng dedup_key"
    # là so với chính tính năng đang test. Mà `che_chu` RA ĐỜI Ở v2.26.0
    # (`git show v2.25.0:app/services.py` có 0 dòng `che_chu`, v2.26.0 có 15).
    # Lấy v2.26.0 làm mốc -> CA23-3'' ĐỎ, và nó đỏ ĐÚNG: cổng đang báo mốc
    # không hợp lệ chứ không phải app hỏng. Mốc đúng = bản phát hành NGAY
    # TRƯỚC tính năng.
    e.setdefault("BQ_MOC_REF", "v2.25.0")
    return e


def main() -> int:
    env = moi_truong()
    print("=" * 78)
    print(f"HỒI QUY — {len(CONG)} cổng · BQ_MOC_REF={env['BQ_MOC_REF']}")
    print("=" * 78)
    kq = []
    for ten, f, moc in CONG:
        p = REPO / f
        if not p.exists():
            print(f"  {ten:<22} KHÔNG CÓ FILE {f}")
            kq.append((ten, f, -1, 0.0, None, None, moc))
            continue
        t0 = time.time()
        r = subprocess.run([PY, "-u", str(p)], cwd=str(REPO), env=env,
                           capture_output=True, timeout=3600)
        gy = time.time() - t0
        out = (r.stdout or b"").decode("utf-8", "replace") + \
              (r.stderr or b"").decode("utf-8", "replace")
        (REPO / "_kq_hq").mkdir(exist_ok=True)
        (REPO / "_kq_hq" / f"{f}.txt").write_text(out, encoding="utf-8")
        m = None
        for m2 in _RE_TK.finditer(out):
            m = m2                            # lấy dòng tổng kết CUỐI CÙNG
        dat = int(m.group(1)) if m else None
        hong = int(m.group(2)) if m else None
        kq.append((ten, f, r.returncode, gy, dat, hong, moc))
        co = "" if moc is None or dat is None else (
            "  (mốc %d)" % moc if dat >= moc else "  << TỤT so mốc %d" % moc)
        print(f"  {ten:<22} rc={r.returncode:<3} {gy:6.1f}s  "
              f"ĐẠT {dat if dat is not None else '?':>4} · "
              f"HỎNG {hong if hong is not None else '?':<4}{co}")

    print("=" * 78)
    do = [k for k in kq if k[2] != 0]
    ngo = [k for k in kq if k[2] == 0 and (k[4] is None or k[3] < 0.3)]
    print(f"ĐỎ: {len(do)} cổng" + (f" -> {[k[0] for k in do]}" if do else ""))
    if ngo:
        print(f"ĐÁNG NGỜ (rc=0 mà không thấy dòng tổng kết / chạy <0,3s): "
              f"{[k[0] for k in ngo]}")
    tut = [k[0] for k in kq if k[6] and k[4] is not None and k[4] < k[6]]
    if tut:
        print(f"TỤT SỐ MỤC so với mốc: {tut}")
    return 1 if do else 0


if __name__ == "__main__":
    raise SystemExit(main())
