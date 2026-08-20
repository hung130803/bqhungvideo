# -*- coding: utf-8 -*-
"""CHẠY THẬT `giong_vieneu.cai_nhan_ban()` vào một venv HỘP CÁT.

Vì sao phải chạy thật: bài học cổng 58 mục "CHƯA ĐẠT" — cơ chế
`--ignore-installed` + hậu-kiểm-theo-đường-dẫn khi đó chỉ được chứng minh bằng
một gói NHỎ rồi **SUY RA** cho torch, và câu đó phải ghi thẳng là chưa đo. Ở
đây tải THẬT rồi đọc số giây + dung lượng.

**TUYỆT ĐỐI KHÔNG ĐỤNG `_giong_vieneu/venv` ĐANG DÙNG ĐƯỢC** — nó đang chạy cả
20 giọng dựng sẵn lẫn đường nhân bản; hỏng là mất cả hai. Hộp cát dựng riêng ở
`_hopcat_nb/venv` và xoá sau khi đo.

Mẹo làm hộp cát rẻ: `giong_vieneu._python_vieneu()` dò VieNeu bằng **FILE CÓ
TỒN TẠI KHÔNG** (`_CAN_CO`), nên chỉ cần đặt mấy file RỖNG đúng tên là
`tinh_trang_vieneu()['co']` -> True. Không phải chép cả môi trường mấy GB, mà
`cai_nhan_ban` vẫn đi ĐÚNG đường thật của nó: pip vào ĐÚNG python đó, rồi hậu
kiểm bằng CHÍNH `thieu_de_nhan_ban()`.

Mặc định lấy bản **CPU** (126,3 MB). `--cuda` để chạy bản cu126 (2.485,6 MB) —
tốn hơn 19,7 lần nên phải nói ra mới chạy.

Chạy: .venv\\Scripts\\python -u _do_cai_nhan_ban.py [--cuda]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / "_hopcat_nb"
VENV = HOP / "venv"

#: Đúng danh sách `giong_vieneu._CAN_CO` — file RỖNG là đủ vì phép dò hỏi
#: "file có tồn tại không", không hỏi nội dung.
_CAN_CO = ("vieneu/v3turbo.py",
           "vieneu/assets/voices_v3_turbo.json",
           "onnxruntime/__init__.py",
           "soundfile.py",
           "librosa/__init__.py")


def mb_thu_muc(d: Path) -> float:
    t = 0
    for p in d.rglob("*"):
        try:
            if p.is_file():
                t += p.stat().st_size
        except OSError:
            pass
    return t / 1024 / 1024


def main() -> int:
    cuda = "--cuda" in sys.argv
    from app.core import giong_vieneu as VN
    from app.core import nhan_ban_giong as NB

    # CANH CỔNG: nếu vì lý do gì mà hộp cát trỏ vào venv thật thì DỪNG.
    that = (REPO / "_giong_vieneu" / "venv").resolve()
    if VENV.resolve() == that:
        print("DỪNG: hộp cát trùng venv THẬT.")
        return 2

    if HOP.exists():
        shutil.rmtree(HOP, ignore_errors=True)
    HOP.mkdir(parents=True, exist_ok=True)

    py = VN._python_he_thong()
    print(f"python hệ thống: {py}")
    # Bản python phải khớp bản đã ĐO (3.12): `_do_nhan_ban_tai.py` đo bằng
    # 3.12.10, và cổng 87/Kokoro đã đo được 3.14 làm pip chết ở
    # `metadata-generation-failed`. Dựng hộp cát bằng CHÍNH python của venv
    # VieNeu để so được số.
    py312 = REPO / "_giong_vieneu" / "venv" / "Scripts" / "python.exe"
    if py312.is_file():
        py = str(py312)
        print(f"-> dùng python của venv VieNeu để dựng hộp cát: {py}")
    if not py:
        print("DỪNG: máy không có Python 3.")
        return 2

    t0 = time.time()
    r = subprocess.run([py, "-m", "venv", str(VENV)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=900)
    if r.returncode != 0:
        print(f"DỪNG: dựng venv hỏng: {(r.stderr or '')[-300:]}")
        return 2
    print(f"dựng venv hộp cát: {time.time() - t0:.1f}s")

    sp = VENV / "Lib" / "site-packages"
    for t in _CAN_CO:
        p = sp / t
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
    (sp / "vieneu-3.2.8.dist-info").mkdir(parents=True, exist_ok=True)

    # TRỎ app vào hộp cát. `BQ_VN_DIR` là env mà `thu_muc_vieneu()` đọc TRƯỚC
    # mọi thứ khác, nên cả `_python_vieneu` lẫn `cai_nhan_ban` đều đi vào đây.
    os.environ["BQ_VN_DIR"] = str(HOP)
    print(f"BQ_VN_DIR = {HOP}")
    print(f"thu_muc_vieneu() = {VN.thu_muc_vieneu()}")
    print(f"_python_vieneu() = {VN._python_vieneu()[0]}")

    mb0 = mb_thu_muc(VENV)
    thieu_truoc = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
    # Đổi dấu nghìn RIÊNG CON SỐ. Bản đầu `.replace` cả dòng và in ra
    # `['torch'. 'torchaudio']` — dấu phẩy của danh sách thành dấu chấm, đọc
    # như thể danh sách hỏng. Cùng lỗi mà `giong_vieneu.so_mb` vừa vá.
    print(f"\nTRƯỚC:  venv {VN.so_mb(mb0)} MB · thiếu = {thieu_truoc}")
    if not thieu_truoc:
        print("DỪNG: hộp cát đã đủ sẵn?! phép đo vô nghĩa.")
        return 2

    print(f"\nĐang gọi cai_nhan_ban(ban_cuda={cuda}) — TẢI THẬT...")
    moc: list[tuple[float, float, str]] = []
    t1 = time.time()
    kq = VN.cai_nhan_ban(
        on_progress=lambda p, m: moc.append((time.time() - t1, p, m)),
        ban_cuda=cuda)
    giay = time.time() - t1

    mb1 = mb_thu_muc(VENV)
    thieu_sau = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
    print(f"\n=== KẾT QUẢ ===")
    print(f"  ok            = {kq.get('ok')}")
    print(f"  loi           = {str(kq.get('loi') or '(không)')[:300]}")
    print(f"  giây (hàm tự đo) = {kq.get('giay')}")
    print(f"  giây (tường)     = {giay:.1f}")
    print(f"  cuda          = {kq.get('cuda')} · chỉ mục {kq.get('chi_muc')}")
    print(f"  mb_tai (nhãn) = {kq.get('mb_tai')}")
    print(f"  thiếu SAU     = {thieu_sau}")
    print(f"  venv {VN.so_mb(mb0)} MB -> {VN.so_mb(mb1)} MB  "
          f"(+{VN.so_mb(mb1 - mb0)} MB bung ra đĩa)")
    print(f"  lượt báo tiến độ: {len(moc)}")
    for t, p, m in moc[:3] + moc[-3:]:
        print(f"     {t:6.1f}s  {p * 100:5.1f}%  {m[:80]}")

    # HẬU KIỂM ĐỘC LẬP: hỏi thẳng FILE, không tin cả `kq` lẫn pip.
    co_torch = (sp / "torch" / "__init__.py").exists()
    co_ta = (sp / "torchaudio" / "__init__.py").exists()
    print(f"\n  torch/__init__.py trong HỘP CÁT      = {co_torch}")
    print(f"  torchaudio/__init__.py trong HỘP CÁT = {co_ta}")
    ver = ""
    vp = sp / "torch" / "version.py"
    if vp.exists():
        for d in vp.read_text(encoding="utf-8", errors="replace").splitlines():
            if d.startswith("__version__"):
                ver = d.split("=", 1)[1].strip().strip("'\"")
    print(f"  torch.__version__ (đọc file)         = {ver}")

    ra = {"ok": bool(kq.get("ok")), "cuda": cuda, "giay": round(giay, 1),
          "mb_truoc": round(mb0, 1), "mb_sau": round(mb1, 1),
          "mb_them": round(mb1 - mb0, 1), "mb_nhan": kq.get("mb_tai"),
          "thieu_truoc": thieu_truoc, "thieu_sau": thieu_sau,
          "co_torch": co_torch, "co_torchaudio": co_ta, "ban_torch": ver,
          "so_luot_tien_do": len(moc), "loi": str(kq.get("loi") or "")}
    (REPO / "_kq_cai_nhan_ban.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã ghi {REPO / '_kq_cai_nhan_ban.json'}")

    # DỌN — hộp cát mấy trăm MB nằm trong repo là rác thật.
    os.environ.pop("BQ_VN_DIR", None)
    for _ in range(6):
        shutil.rmtree(HOP, ignore_errors=True)
        if not HOP.exists():
            break
        time.sleep(0.5)
    print("đã dọn hộp cát" if not HOP.exists()
          else f"LƯU Ý: KHÔNG dọn được {HOP} — xoá tay")
    return 0 if (kq.get("ok") and not thieu_sau and co_torch and co_ta) else 1


if __name__ == "__main__":
    raise SystemExit(main())
