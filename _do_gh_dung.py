# -*- coding: utf-8 -*-
"""ĐO: bộ gióng hàng có TỰ ĐỨNG ĐƯỢC không, và vì sao máy anh Hùng đỏ.

Chạy MỖI PHÉP Ở TIẾN TRÌNH RIÊNG (bất biến 1 của `giong_hang.py`: `import
torch` trong tiến trình đã nạp Qt là ACCESS VIOLATION). Mỗi phép nhận danh
sách thư mục đặt lên `sys.path` rồi **CẮT SẠCH site-packages** — đó là cách
giả lập bản `.exe` (bài học cổng 58 CA 1a).

Trả lời 3 câu KHÁC NHAU, đừng gộp:
  · `torchaudio` nạp được không (nó cần DLL của torch)
  · gói lấy TỪ ĐÂU (`spec.origin`) — máy dev mượn được rồi báo "đã cài" đúng
    là lỗ hổng cổng 58
  · DLL nào THIẾU
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo"

_MA = r'''
import json, os, sys
duong = json.loads(sys.argv[1])
for d in reversed(duong):
    sys.path.insert(0, d)
# CẮT site-packages: giả lập bản .exe (không có .venv để mượn)
if os.environ.get("BQ_CAT_SP") == "1":
    sys.path[:] = [p for p in sys.path
                   if "site-packages" not in p.replace("\\", "/").lower()]
ra = {"path": list(sys.path)}
try:
    import torch
    ra["torch"] = getattr(torch, "__version__", "?")
    ra["torch_o"] = getattr(torch, "__file__", "?")
    ra["cuda_co"] = bool(torch.cuda.is_available())
except Exception as e:
    ra["torch_loi"] = "%s: %s" % (type(e).__name__, e)
try:
    import torchaudio
    ra["ta"] = getattr(torchaudio, "__version__", "?")
    ra["ta_o"] = getattr(torchaudio, "__file__", "?")
except Exception as e:
    ra["ta_loi"] = "%s: %s" % (type(e).__name__, str(e)[:400])
try:
    from torchaudio.pipelines import MMS_FA
    ra["mms"] = "nap duoc bang ten"
except Exception as e:
    ra["mms_loi"] = "%s: %s" % (type(e).__name__, str(e)[:200])
try:
    import uroman
    ra["uroman_o"] = getattr(uroman, "__file__", "?")
except Exception as e:
    ra["uroman_loi"] = "%s: %s" % (type(e).__name__, str(e)[:200])
sys.stdout.write("BQJSON" + json.dumps(ra, ensure_ascii=False))
'''


def chay(ten: str, duong: list[Path], cat_sp: bool,
         py: str | None = None) -> dict:
    """`py` = python NÀO chạy phép đo.

    **BẮT BUỘC PHẢI ĐÚNG BẢN PYTHON** — `_giong_hang`/`_lib` của máy anh Hùng
    mang `.pyd` gắn thẻ `cp314` còn `.venv` là 3.12, chạy lệch bản là đo ra
    một `ImportError` KHÁC HẲN rồi kết luận sai (bài học "kích thước thư mục
    không chứng minh gì" — phải kiểm bằng ĐƯỜNG CHẠY THẬT).
    """
    r = Path(REPO / "_bq_probe_gh.py")
    r.write_text(_MA, encoding="utf-8")
    env = dict(os.environ)
    env["BQ_CAT_SP"] = "1" if cat_sp else "0"
    env["PYTHONUTF8"] = "1"
    try:
        p = subprocess.run(
            [py or sys.executable, "-u", str(r),
             json.dumps([str(x) for x in duong])],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=300)
    finally:
        try:
            r.unlink()
        except OSError:
            pass
    ra = (p.stdout or "")
    i = ra.find("BQJSON")
    d = json.loads(ra[i + 6:]) if i >= 0 else {"vo_json": ra[-400:],
                                               "err": (p.stderr or "")[-400:]}
    d["_ten"] = ten
    d["_rc"] = p.returncode
    return d


def in_ra(d: dict) -> None:
    print("\n" + "=" * 74)
    print("  " + d["_ten"] + "   (mã thoát %s)" % d.get("_rc"))
    print("=" * 74)
    for k in ("torch", "torch_o", "cuda_co", "torch_loi",
              "ta", "ta_o", "ta_loi", "mms", "mms_loi",
              "uroman_o", "uroman_loi", "vo_json", "err"):
        if k in d:
            print("  %-10s %s" % (k, d[k]))


def _py314() -> str:
    """Python mà bản `.exe` THẬT SỰ dùng (`_python_chay` -> which python)."""
    import shutil
    for c in (r"C:\Python314\python.exe",):
        if Path(c).is_file():
            return c
    return shutil.which("python.exe") or sys.executable


def main() -> int:
    PY314 = _py314()
    print("python .venv (dev) :", sys.executable)
    print("python bản CÀI     :", PY314)
    bo = [
        ("A· MÁY DEV như hôm nay (repo _gh + repo _lib, CÒN .venv) [3.12]",
         [REPO / "_giong_hang", REPO / "_lib"], False, sys.executable),
        ("B· BẢN CÀI giả lập (repo _gh + repo _lib, CẮT site-packages) [3.12]",
         [REPO / "_giong_hang", REPO / "_lib"], True, sys.executable),
        ("C· MÁY ANH HÙNG (DATA_DIR _gh + DATA_DIR _lib, CẮT sp) [3.14]",
         [DATA / "_giong_hang", DATA / "_lib"], True, PY314),
        ("D· _gh MỘT MÌNH, không _lib (CẮT sp) [3.12] — tự đứng được?",
         [REPO / "_giong_hang"], True, sys.executable),
        ("E· DATA_DIR _gh MỘT MÌNH, không _lib (CẮT sp) [3.14]",
         [DATA / "_giong_hang"], True, PY314),
    ]
    kq = []
    for ten, duong, cat, py in bo:
        d = chay(ten, duong, cat, py)
        in_ra(d)
        kq.append(d)

    print("\n" + "=" * 74)
    print("  BẢNG GỌN")
    print("=" * 74)
    print("  %-46s %-9s %s" % ("phép", "torch", "torchaudio"))
    for d in kq:
        ta = d.get("ta") or ("LỖI: " + str(d.get("ta_loi", "?"))[:40])
        print("  %-46s %-9s %s" % (d["_ten"][:46],
                                   d.get("torch", "LỖI"), ta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
