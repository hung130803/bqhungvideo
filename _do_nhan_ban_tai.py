# -*- coding: utf-8 -*-
"""ĐO dung lượng nút "tải phần nhân bản giọng" SẼ tải — torch + torchaudio.

Vì sao có file này: nhãn nút / tooltip / hộp xác nhận phải nói **SỐ ĐO**, không
phải ước bừa. Bài học cổng 58: nhãn Demucs từng ghi *"khoảng 2 GB"* trong khi
tải thật **154 MB** (gấp 13 lần), và một lượt khác nút ghi 155 MB rồi hộp xác
nhận doạ 2 GB — hai chỗ lấy số khác nhau.

Cách đo: `pip install --dry-run --report` (**KHÔNG tải gói**) để pip tự giải
phép phụ thuộc rồi trả URL wheel, sau đó **HTTP HEAD** trên chính URL đó lấy
`Content-Length`. Đúng cách cổng 58/71/73 đã đo.

Lệnh dry-run dựng **giống hệt** lệnh `nhan_ban_giong.cai_nhan_ban()` sẽ chạy
(cùng cờ, cùng `--extra-index-url`, cùng python) — đo một lệnh rồi cài một lệnh
KHÁC thì con số vô nghĩa.

Chạy: `python _do_nhan_ban_tai.py` -> `_kq_nhan_ban_tai.json`
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent

#: Đúng hai gói `nhan_ban_giong._CAN_CHO_NHAN_BAN` đang dò.
GOI = ("torch", "torchaudio")

CHI_MUC = {
    "cpu": "https://download.pytorch.org/whl/cpu",
    "cu126": "https://download.pytorch.org/whl/cu126",
}

#: Không có UA thì một số CDN trả 403 cho HEAD rồi hàm `co()` trả -1, bảng in
#: "?" — phép đo hỏng mà vẫn phát chứng nhận.
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _python_vieneu() -> str:
    """Python của venv VieNeu — ĐÚNG cái `cai_nhan_ban` sẽ gọi pip bằng.

    Phải đo bằng CHÍNH bản python đó: cổng 88/Kokoro đã đo được cùng một lệnh
    pip ra 92 gói/211,5 MB với 3.12 mà `metadata-generation-failed` với 3.14.
    """
    for p in (REPO / "_giong_vieneu" / "venv" / "Scripts" / "python.exe",
              REPO / "_giong_vieneu" / "venv" / "bin" / "python"):
        if p.is_file():
            return str(p)
    return ""


def bao_cao(py: str, chi_muc: str) -> tuple[list[tuple[str, str]], str]:
    """[(tên==bản, url)] pip SẼ tải. KHÔNG tải thật."""
    # Report ra FILE, KHÔNG ra stdout: pip trộn cảnh báo vào stdout nên
    # `find("{")` bắt trúng dấu ngoặc của dòng cảnh báo rồi nổ JSONDecodeError.
    rp = REPO / "_bq_report_nb.json"
    try:
        rp.unlink()
    except OSError:
        pass
    args = [py, "-m", "pip", "install", "--dry-run", "--report", str(rp),
            "--no-input", "--disable-pip-version-check", "--quiet",
            "--upgrade", "--ignore-installed",
            "--extra-index-url", chi_muc, *GOI]
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        return [], "dry-run quá 1800s"
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


def mb(n: float) -> str:
    return "?" if n < 0 else f"{n / 1024 / 1024:,.1f} MB".replace(",", ".")


def main() -> int:
    py = _python_vieneu()
    if not py:
        print("KHÔNG thấy python của venv VieNeu — chưa cài VieNeu?")
        return 1
    ver = subprocess.run([py, "-c", "import sys;print(sys.version.split()[0])"],
                         capture_output=True, text=True, timeout=120)
    print(f"python venv VieNeu: {py}  ({(ver.stdout or '').strip()})")
    print(f"gói xin pip: {' '.join(GOI)}\n")

    kq: dict = {"python": py, "ban_python": (ver.stdout or "").strip(),
                "goi": list(GOI), "chi_muc": {}}
    for ten, url_ci in CHI_MUC.items():
        print(f"=== chỉ mục {ten} ({url_ci}) ===")
        t0 = time.time()
        ds, loi = bao_cao(py, url_ci)
        if loi:
            print(f"  HỎNG: {loi}")
            kq["chi_muc"][ten] = {"loi": loi}
            continue
        tong = 0
        rieng: dict[str, float] = {}
        for nb, u in ds:
            n = co(u)
            if n > 0:
                tong += n
            ten_goi = nb.split("==")[0].lower()
            if ten_goi in ("torch", "torchaudio"):
                rieng[nb] = n
                print(f"  {nb:<28} {mb(n)}")
        print(f"  -> {len(ds)} gói = {mb(tong)}   "
              f"(giải phép phụ thuộc {time.time() - t0:.1f}s)\n")
        kq["chi_muc"][ten] = {
            "so_goi": len(ds),
            "byte": tong,
            "mb": round(tong / 1024 / 1024, 1),
            "rieng_mb": {k: round(v / 1024 / 1024, 1) for k, v in rieng.items()},
            "goi": [n for n, _ in ds],
        }

    p = REPO / "_kq_nhan_ban_tai.json"
    p.write_text(json.dumps(kq, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"Đã ghi {p}")
    a = kq["chi_muc"].get("cpu", {}).get("mb")
    b = kq["chi_muc"].get("cu126", {}).get("mb")
    if a and b:
        print(f"\nCPU {a:,.1f} MB  vs  CUDA {b:,.1f} MB  = chênh {b / a:.1f} lần"
              .replace(",", "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
