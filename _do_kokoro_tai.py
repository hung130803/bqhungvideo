# -*- coding: utf-8 -*-
"""ĐO LƯỢNG TẢI THẬT của bộ giọng Kokoro — để nhãn nút ghi ĐÚNG số GB.

Cách đo: `pip install --dry-run --report` (**KHÔNG tải gói**) để pip tự giải
phép phụ thuộc rồi trả URL wheel, sau đó **HTTP HEAD** trên chính URL đó lấy
`Content-Length`. Đúng cách cổng 58/71/73 đã đo — không ước bừa.

Đo với CẢ HAI bản Python vì `cai_kokoro()` dựng venv bằng `_python_he_thong()`:
chạy từ nguồn thì đó là python của `.venv` (**3.12**), bản `.exe` thì là
`py`/`python` trên PATH (**3.14** trên máy này). Wheel torch gắn thẻ theo bản
Python (`cp312`/`cp314`) nên hai bản có thể ra hai con số — và nếu bản nào
KHÔNG có wheel thì đó là phát hiện quan trọng hơn cả con số.

Đo CẢ chỉ mục `cpu` và `cu126`: máy anh Hùng có RTX 3060 nên nút sẽ đi đường
CUDA, mà wheel CUDA đã đo được là **2.474,4 MB** so với `+cpu` 121,9 MB (cổng
71). Nhãn ghi số của đường KHÔNG đi là đúng lỗi đã mắc một lần (nút ghi
155 MB, hộp doạ 2 GB).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
CPU = "https://download.pytorch.org/whl/cpu"
CU126 = "https://download.pytorch.org/whl/cu126"

#: Đúng bộ gói mà `giong_kokoro.cai_kokoro()` đưa cho pip.
GOI = ["kokoro", "soundfile"]

#: **PHẢI ĐẶT User-Agent** — `download.pytorch.org` trả 403 cho UA mặc định của
#: urllib (bẫy đã ghi ở cổng 22 và `_do_gh_tai_ve.py`). Không đặt là mọi cỡ ra
#: `?` rồi bảng tự in "0.0 MB" = phép đo hỏng phát chứng nhận.
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _pythons() -> list[tuple[str, str]]:
    ra: list[tuple[str, str]] = []
    v312 = REPO / "_giong_kokoro" / "venv" / "Scripts" / "python.exe"
    if v312.is_file():
        ra.append(("venv Kokoro (3.12)", str(v312)))
    elif (REPO / ".venv" / "Scripts" / "python.exe").is_file():
        ra.append((".venv app (3.12)", str(REPO / ".venv/Scripts/python.exe")))
    p = shutil.which("python.exe") or shutil.which("python")
    if p:
        ra.append(("python trên PATH", p))
    return ra


def bao_cao(py: str, chi_muc: str) -> tuple[list[tuple[str, str]], str]:
    """[(tên==bản, url)] pip SẼ tải. Không tải thật."""
    # Report ra FILE, KHÔNG ra stdout: pip trộn cảnh báo vào stdout nên
    # `find("{")` bắt trúng dấu ngoặc của dòng cảnh báo rồi nổ JSONDecodeError.
    rp = REPO / "_bq_report_kk.json"
    try:
        rp.unlink()
    except OSError:
        pass
    args = [py, "-m", "pip", "install", "--dry-run", "--report", str(rp),
            "--no-input", "--disable-pip-version-check", "--quiet",
            "--ignore-installed",
            "--target", str(Path(os.environ.get("TEMP", ".")) / "_bq_dry_kk"),
            "--extra-index-url", chi_muc, *GOI]
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    if not rp.is_file():
        return [], ((r.stderr or "") + (r.stdout or ""))[-400:]
    try:
        d = json.loads(rp.read_text(encoding="utf-8"))
    except ValueError as e:
        return [], f"report hỏng: {e}"
    finally:
        try:
            rp.unlink()
        except OSError:
            pass
    ra = []
    for it in d.get("install", []):
        url = (it.get("download_info") or {}).get("url") or ""
        md = it.get("metadata") or {}
        ra.append((f"{md.get('name', '?')}=={md.get('version', '?')}", url))
    return ra, ""


def co(url: str) -> int:
    """Content-Length của wheel — HEAD, lùi về GET Range. Không tải cả file."""
    if not url.startswith("http"):
        return -1
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        try:
            rq = urllib.request.Request(url, method=method,
                                        headers={**_UA, **extra})
            with urllib.request.urlopen(rq, timeout=90) as f:
                cr = f.headers.get("Content-Range")
                if cr and "/" in cr:
                    return int(cr.rsplit("/", 1)[1])
                cl = f.headers.get("Content-Length")
                if cl and method == "HEAD":
                    return int(cl)
        except Exception as e:  # noqa: BLE001
            print(f"   !! {method} {type(e).__name__}: {e}")
    return -1


def mb(n: int) -> str:
    return "?" if n < 0 else f"{n / 1024 / 1024:,.1f} MB".replace(",", ".")


def main() -> int:
    kq: dict[str, float] = {}
    for nhan_py, py in _pythons():
        ver = subprocess.run([py, "-c", "import sys;print(sys.version.split()[0])"],
                             capture_output=True, text=True).stdout.strip()
        for nhan, chi_muc in (("cpu", CPU), ("cu126", CU126)):
            print("\n" + "=" * 74)
            print(f" {nhan_py} [{ver}]  ·  chỉ mục {nhan}  ·  {' '.join(GOI)}")
            print("=" * 74)
            ds, loi = bao_cao(py, chi_muc)
            if not ds:
                print("   !! pip KHÔNG trả report:", loi)
                continue
            tong = 0
            for ten, url in sorted(ds, key=lambda x: x[0].lower()):
                n = co(url)
                tong += max(0, n)
                if n < 0 or n > 20 * 1024 * 1024:      # in gói to + gói lỗi
                    print(f"   {ten:<36} {mb(n):>14}")
            print(f"   {'... ' + str(len(ds)) + ' gói, TỔNG':<36} {mb(tong):>14}")
            kq[f"{ver} · {nhan}"] = tong / 1024 / 1024

    print("\n" + "=" * 74)
    print(" BẢNG CHỐT (số để điền vào nhãn nút)")
    print("=" * 74)
    for k, v in kq.items():
        print(f"   {k:<28} {v:>10,.1f} MB  =  {v/1024:.2f} GB"
              .replace(",", "."))
    print("\nTRỌNG SỐ MODEL (tải riêng lúc chạy lần đầu, KHÔNG qua pip):")
    hf = REPO / "_giong_kokoro" / "hf"
    if hf.is_dir():
        n = sum(f.stat().st_size for f in hf.rglob("*") if f.is_file())
        print(f"   {hf} = {mb(n)}")
    else:
        print("   (chưa có trên đĩa)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
