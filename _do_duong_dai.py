# -*- coding: utf-8 -*-
"""ĐO ĐƯỜNG DẪN DÀI của đường THAY GIỌNG — trước khi sửa.

Lỗi thật anh Hùng gặp 14/08/2026: chạy "Thay giọng nói" trên 6 video tiếng
Trung ra **4 Xong · 2 Lỗi**, hai dòng lỗi ghi::

    FileNotFoundError: [WinError 206] The filename or extension is too long

Script này KHÔNG đoán. Nó dựng LẠI đúng từng đường dẫn mà
`tg_chay.thu_muc_lam_cho` + `thay_giong.thay_giong_video` tạo ra cho 6 video
THẬT trong `C:\\Users\\Admin\\Downloads\\longtieng`, đo độ dài từng cái, và
CHẠM THẬT vào đĩa (tạo file trong sandbox) để xem cái nào Windows từ chối.

Chạy: `.venv\\Scripts\\python _do_duong_dai.py`
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")     # cp1252 khi ghi ra file
except Exception:                                 # noqa: BLE001
    pass

NGUON = r"C:\Users\Admin\Downloads\longtieng"
DICH = r"C:\Users\Admin\Downloads\longtieng\xuất"

#: Windows: đường dẫn tối đa 259 ký tự + NUL (MAX_PATH 260). 260 là HỎNG.
MAX_PATH = 260
TRAN = MAX_PATH - 1                              # 259 ký tự còn dùng được


def duong_du_kien(video: Path, thu_muc_ra: str) -> list[tuple[str, str]]:
    """MỌI đường dẫn đường thay giọng tạo ra cho 1 video (bản v2.27.1).

    Nguồn sự thật:
      · `tg_chay.thu_muc_lam_cho`  -> `<ra>/_thaygiong_tam/<stem>`
      · `thay_giong.thay_giong_video` bước 0..6
      · `tg_so.duong_ra`           -> `<ra>/<tên gốc>`
    """
    from app.core.thay_giong import DAU_DA_LAM
    from app.core.tg_chay import thu_muc_lam_cho

    suf = video.suffix
    ra = Path(thu_muc_ra)
    # ĐỌC TỪ MÃ THẬT, đừng chép tay lại quy tắc: chép tay là đo bản chữ CŨ, mã
    # đổi thì ngoài đời sai mà phép đo vẫn đẹp (bài học cổng 57).
    tam = Path(thu_muc_lam_cho(video, thu_muc_ra))
    d: list[tuple[str, str]] = [
        ("0. nguồn (video gốc)", str(video)),
        ("*. ĐÍCH cuối cùng", str(ra / video.name)),
        ("--. thư mục làm việc tạm", str(tam)),
        ("0. rút tiếng", str(tam / "goc.wav")),
        ("1. tách giọng - nhạc", str(tam / "tach" / "lop_nhac.wav")),
        ("1. tách giọng - giọng", str(tam / "tach" / "lop_giong.wav")),
        ("1. demucs stem", str(tam / "tach" / "htdemucs" / "goc" / "other.wav")),
        ("4. TTS câu", str(tam / "tts" / "cau_0000.mp3")),
        ("4. TTS cắt lề", str(tam / "tts" / "sach" / "sach_0000.wav")),
        ("4b. rút gọn đọc lại", str(tam / "rutgon" / "rg1_0000.mp3")),
        ("4b. rút gọn cắt lề", str(tam / "rutgon" / "sach1" / "sach_0000.wav")),
        ("4c. đọc nhanh", str(tam / "docnhanh" / "nhanh_0000.mp3")),
        ("4c. đọc nhanh cắt lề", str(tam / "docnhanh" / "sach" / "sach_0000.wav")),
        ("5. khớp thời gian", str(tam / "khop" / "khop_0000.wav")),
        ("6. trộn tiếng mới", str(tam / "tieng_moi.wav")),
        ("6. GHÉP video (ra)", str(tam / f"ban{DAU_DA_LAM}{suf}")),
    ]
    return d


def cham_that(duong: str, goc_sandbox: Path) -> str:
    """Thử TẠO THẬT một file ở độ dài y hệt -> Windows nói gì.

    Không tin lý thuyết: dựng lại đúng số ký tự trong sandbox rồi mở file.
    """
    n = len(duong)
    goc = str(goc_sandbox)
    if n <= len(goc) + 2:
        return "(ngắn hơn sandbox, bỏ qua)"
    # đệm cho tổng độ dài = n, chia thành các đoạn <= 200 ký tự (giới hạn TÊN)
    con = n - len(goc) - 1
    phan: list[str] = []
    while con > 0:
        lay = min(120, con)
        phan.append("x" * lay)
        con -= lay + 1
    p = os.path.join(goc, *phan) if phan else goc
    p = p[:n] if len(p) > n else p + "x" * (n - len(p))
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x")
        os.remove(p)
        return "TẠO ĐƯỢC"
    except OSError as e:
        return f"HỎNG: {type(e).__name__} WinError {getattr(e, 'winerror', '?')}"


def main() -> int:
    vids = sorted(Path(NGUON).glob("*.mp4"))
    if not vids:
        print(f"KHÔNG thấy video nào trong {NGUON}")
        return 2
    sandbox = Path(__file__).resolve().parent / f"bq_do_dd_{os.getpid()}"
    sandbox.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("ĐO ĐƯỜNG DẪN — đường THAY GIỌNG (bản v2.27.1, CHƯA vá)")
    print(f"  nguồn : {NGUON}  ({len(NGUON)} ký tự)")
    print(f"  đích  : {DICH}  ({len(DICH)} ký tự)")
    print(f"  trần Windows: {TRAN} ký tự (MAX_PATH {MAX_PATH})")
    print("=" * 78)

    tong_vuot = 0
    for v in vids:
        ds = duong_du_kien(v, DICH)
        vuot = [(t, p) for t, p in ds if len(p) > TRAN]
        print(f"\n### {v.name}")
        print(f"    tên file {len(v.name)} ký tự · stem {len(v.stem)}")
        for t, p in ds:
            n = len(p)
            co = "VƯỢT" if n > TRAN else "    "
            print(f"    {co} {n:4d}  {t}")
        if vuot:
            tong_vuot += 1
            print(f"    -> VƯỢT {len(vuot)}/{len(ds)} đường dẫn. Bước đầu tiên "
                  f"vượt: {vuot[0][0]} ({len(vuot[0][1])} ký tự)")
            print(f"       chạm thật: {cham_that(vuot[0][1], sandbox)}")
        else:
            print("    -> KHÔNG đường nào vượt")

    print("\n" + "=" * 78)
    print(f"TỔNG: {tong_vuot}/{len(vids)} video có ít nhất 1 đường dẫn vượt trần")
    # đối chứng: đúng mốc 259/260 Windows từ chối ở đâu
    print("\nĐỐI CHỨNG mốc gãy của Windows (tạo file thật):")
    for n in (255, 258, 259, 260, 261, 300):
        print(f"    {n:4d} ký tự -> {cham_that('x' * n, sandbox)}")
    try:
        import shutil
        shutil.rmtree(sandbox, ignore_errors=True)
    except Exception:                             # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
