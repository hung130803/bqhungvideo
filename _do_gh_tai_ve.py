# -*- coding: utf-8 -*-
"""ĐO LƯỢNG TẢI THẬT của bộ gióng hàng — để nhãn nút ghi đúng số GB.

Cách đo: `pip install --dry-run --report` (KHÔNG tải gói) để pip tự giải phép
phụ thuộc rồi trả URL wheel, sau đó **HTTP HEAD** trên chính URL đó lấy
`Content-Length`. Đúng cách cổng 58/71 đã đo — không ước bừa.

Đo với **Python 3.14** vì đó là bản mà bản `.exe` thật sự gọi (`_python_chay`
-> `which python`), và wheel torchaudio gắn thẻ theo bản Python (`cp314`).

Nhãn sai là user bấm xong ngồi đợi một lượt tải khác hẳn cái vừa đọc — đã có
tiền lệ nút ghi 155 MB mà hộp doạ 2 GB.
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

CPU = "https://download.pytorch.org/whl/cpu"
CU126 = "https://download.pytorch.org/whl/cu126"


def _py() -> str:
    for c in (r"C:\Python314\python.exe",):
        if Path(c).is_file():
            return c
    return shutil.which("python.exe") or sys.executable


def bao_cao(py: str, goi: list[str], chi_muc: str | None,
            no_deps: bool) -> list[tuple[str, str]]:
    """Trả [(tên gói, url wheel)] pip SẼ tải — không tải thật."""
    # Report ra FILE, KHÔNG ra stdout: pip trộn cảnh báo vào stdout nên
    # `find("{")` bắt trúng dấu ngoặc trong một dòng cảnh báo rồi nổ
    # JSONDecodeError (đã sập 1 lần khi viết file này).
    rp = Path(__file__).resolve().parent / "_bq_report_gh.json"
    args = [py, "-m", "pip", "install", "--dry-run", "--report", str(rp),
            "--no-input", "--disable-pip-version-check", "--quiet",
            "--target", str(Path(os.environ["TEMP"]) / "_bq_dryrun_gh")]
    if no_deps:
        args.append("--no-deps")
    if chi_muc:
        args += ["--extra-index-url", chi_muc]
    args += goi
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    if not rp.is_file():
        print("   !! pip không trả report:",
              ((r.stderr or "") + (r.stdout or ""))[-300:])
        return []
    try:
        d = json.loads(rp.read_text(encoding="utf-8"))
    finally:
        try:
            rp.unlink()
        except OSError:
            pass
    ra = []
    for it in d.get("install", []):
        url = (it.get("download_info") or {}).get("url") or ""
        ten = ((it.get("metadata") or {}).get("name") or "?")
        ver = ((it.get("metadata") or {}).get("version") or "?")
        ra.append((f"{ten}=={ver}", url))
    return ra


#: **PHẢI ĐẶT User-Agent** — `download.pytorch.org` trả **403** cho UA mặc
#: định của urllib (cùng bẫy đã ghi ở cổng 22: Cloudflare 403 error 1010 vì
#: User-Agent). Không đặt là mọi cỡ ra `?` rồi bảng tự in "0.0 MB" — đúng họ
#: "phép đo hỏng phát chứng nhận".
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def co(url: str) -> int:
    """Content-Length của wheel — HEAD (lùi về GET Range), không tải cả file."""
    if not url.startswith("http"):
        return -1
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        try:
            rq = urllib.request.Request(url, method=method,
                                        headers={**_UA, **extra})
            with urllib.request.urlopen(rq, timeout=90) as f:
                cl = f.headers.get("Content-Length")
                cr = f.headers.get("Content-Range")
                if cr and "/" in cr:
                    return int(cr.rsplit("/", 1)[1])
                if cl and method == "HEAD":
                    return int(cl)
        except Exception as e:  # noqa: BLE001
            print(f"   !! {method} lỗi:", type(e).__name__, e)
    return -1


def mb(n: int) -> str:
    return "?" if n < 0 else f"{n / 1024 / 1024:,.1f} MB".replace(",", ".")


def main() -> int:
    py = _py()
    print("python đo:", py)
    print(subprocess.run([py, "-c", "import sys;print(sys.version)"],
                         capture_output=True, text=True).stdout.strip())

    for nhan, chi_muc in (("torchaudio TỪ CHỈ MỤC cpu", CPU),
                          ("torchaudio TỪ CHỈ MỤC cu126", CU126)):
        print("\n" + "=" * 70)
        print(" " + nhan)
        print("=" * 70)
        tong = 0
        for ten, url in bao_cao(py, ["torchaudio"], chi_muc, no_deps=True):
            n = co(url)
            tong += max(0, n)
            print(f"   {ten:<34} {mb(n):>14}")
        print(f"   {'TỔNG':<34} {mb(tong):>14}")

    print("\n" + "=" * 70)
    print(" uroman (LẤY CẢ phụ thuộc)")
    print("=" * 70)
    tong = 0
    for ten, url in bao_cao(py, ["uroman"], None, no_deps=False):
        n = co(url)
        tong += max(0, n)
        print(f"   {ten:<34} {mb(n):>14}")
    print(f"   {'TỔNG':<34} {mb(tong):>14}")

    print("\n" + "=" * 70)
    print(" MODEL MMS_FA (file đã có trên đĩa dev)")
    print("=" * 70)
    p = Path(__file__).resolve().parent / "_giong_hang/_models/hub/checkpoints/model.pt"
    if p.is_file():
        n = p.stat().st_size
        print(f"   model.pt {n:,} byte = {mb(n)} = {n/1024**3:.2f} GiB"
              .replace(",", "."))
    else:
        print("   (chưa có trên máy này)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
