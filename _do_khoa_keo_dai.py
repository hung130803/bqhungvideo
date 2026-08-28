# -*- coding: utf-8 -*-
"""BẤT BIẾN: TẮT cờ kéo dài -> `dedup_key` GIỐNG MỐC **TỪNG KÝ TỰ**.

Vì sao phải có phép đo này chứ không phải một lời hứa: `dedup_key` là thứ
quyết định "job này đã chạy chưa". Đổi một ký tự trong đó là **200-300 kênh
của anh Hùng chạy lại từ đầu** — và chuyện đó đã xảy ra thật một lần (cổng
56e: cờ `che_chu` không vào hash -> bật ô xong bấm Chạy thì mọi clip bị
smart-skip, không một dòng báo).

CÁCH LÀM ĐÚNG (khuôn cổng 56 CA 23 / cổng 86):
  · nạp bản MỐC bằng `git show <mốc>:app/core/tg_chay.py` thành **module
    riêng** rồi **GỌI THẬT** — không so mã nguồn, không đọc chuỗi;
  · mốc = bản phát hành **NGAY TRƯỚC** tính năng (`193794b` = v2.48.0). Lấy
    `main`/`HEAD` là so nó với CHÍNH NÓ -> cổng tự ĐẠT OAN vĩnh viễn;
  · chốt chống ĐẠT OAN: bản mốc phải **KHÁC** bản đang test, và phải **KHÔNG
    HỀ CÓ** tham số `keo_dai_giong` (không thì phép so vô nghĩa).

    .venv\\Scripts\\python -u _do_khoa_keo_dai.py
"""
from __future__ import annotations

import importlib.util
import inspect
import itertools
import subprocess
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

from app.core import tg_chay as MOI                      # noqa: E402
from app.core import thay_giong as TG                    # noqa: E402

#: Bản phát hành NGAY TRƯỚC tính năng kéo dài giọng (v2.48.0).
MOC = "193794b"


def nap_moc(sha: str) -> tuple[types.ModuleType, str]:
    """`git show <sha>:app/core/tg_chay.py` -> (module RIÊNG, MÃ NGUỒN).

    Trả kèm mã nguồn vì file tạm bị xoá ngay sau khi nạp -> `inspect.getsource`
    trên module đó ném `OSError: source code not available`. Giữ chuỗi lại là
    cách duy nhất còn so được "hai bản có KHÁC nhau không" (chốt chống ĐẠT
    OAN), và nó cũng chặt hơn: so CẢ FILE chứ không chỉ một hàm.
    """
    ma = subprocess.run(["git", "show", f"{sha}:app/core/tg_chay.py"],
                        cwd=str(REPO), capture_output=True, timeout=60).stdout
    if not ma:
        raise RuntimeError(f"không lấy được tg_chay.py ở mốc {sha}")
    p = REPO / f"_moc_tgchay_{sha}.py"
    p.write_bytes(ma)
    try:
        spec = importlib.util.spec_from_file_location(f"_moc_tg_{sha}", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)          # type: ignore[union-attr]
        return m, ma.decode("utf-8", "replace")
    finally:
        try:
            p.unlink()
        except OSError:
            pass


#: >= 9 TỔ HỢP CỜ — mỗi cờ cũ phải được bật ít nhất một lần, và phải có ca
#: BẬT NHIỀU CỜ CÙNG LÚC: một cờ mọc sai chỗ trong chuỗi `sig` chỉ lộ ra khi
#: có cờ khác đứng sau nó.
BASE = dict(video=r"D:\kho\a.mp4", dich_sang="vi", voice="vnb:mau.wav",
            thu_muc_ra=r"D:\kho\ra")
TO_HOP = [
    {},
    {"che_chu": True},
    {"che_chu": True, "che_chu_cach": "khoi", "che_chu_muc": 0.3},
    {"che_chu": True, "viet_chu": True},
    {"che_chu": True, "viet_chu": True, "kieu_chu": {"co_pt": 5.5}},
    {"hinh_theo_giong": True},
    {"hinh_theo_giong": True, "doc_deu": True},
    {"de_giong": True},
    {"muc_nen_db": -3.0},
    {"muc_giong_db": 2.5},
    {"nhan_nha": True},
    {"che_chu": True, "viet_chu": True, "hinh_theo_giong": True,
     "doc_deu": True, "de_giong": True, "muc_nen_db": -3.0,
     "muc_giong_db": 2.5, "nhan_nha": True},
]

#: Giá trị "để mặc định" — MỌI dạng phải cho ra CÙNG một khoá. `0.999`, `"rac"`
#: và `nan` nằm đây có chủ đích: payload cũ / lối gọi chưa nối có thể mang rác,
#: mà một hệ số bịa nhân vào ĐỘ DÀI TIẾNG thì không có đường lùi.
TAT = (None, 1.0, 0.0, 0, "", "rac", 0.999, float("nan"))


def main() -> int:
    cu, ma_cu = nap_moc(MOC)
    ma_moi = (REPO / "app/core/tg_chay.py").read_text(encoding="utf-8")
    hong = 0

    # ── chốt chống ĐẠT OAN ────────────────────────────────────────────────
    print(f"CHỐT CHỐNG ĐẠT OAN (mốc {MOC})")
    ps_cu = inspect.signature(cu.khoa_chong_trung).parameters
    ps_moi = inspect.signature(MOI.khoa_chong_trung).parameters
    for nhan, dieu in (
        (f"mốc {MOC} KHÔNG có tham số 'keo_dai_giong'",
         "keo_dai_giong" not in ps_cu),
        ("bản ĐANG TEST CÓ tham số 'keo_dai_giong'",
         "keo_dai_giong" in ps_moi),
        ("hai bản KHÁC NHAU (mốc không trùng bản đang test)",
         ma_cu != ma_moi),
    ):
        if dieu:
            print(f"  ĐẠT  {nhan}")
        else:
            hong += 1
            print(f"  HỎNG {nhan}  <- phép so VÔ NGHĨA, đừng đọc bảng dưới")

    # ── 1) TẮT cờ -> khoá giống MỐC từng ký tự ────────────────────────────
    print(f"\n{'-' * 78}\n1) TẮT cờ kéo dài -> khoá GIỐNG MỐC {MOC} TỪNG KÝ TỰ"
          f"\n{'-' * 78}")
    n_ok = 0
    for i, th in enumerate(TO_HOP):
        a = cu.khoa_chong_trung(**BASE, **th)
        for t in TAT:
            b = MOI.khoa_chong_trung(**BASE, **th, keo_dai_giong=t)
            if a == b:
                n_ok += 1
            else:
                hong += 1
                print(f"  HỎNG tổ hợp #{i} · tắt={t!r}\n"
                      f"       mốc: {a}\n       mới: {b}")
    print(f"  ĐẠT  {n_ok}/{len(TO_HOP) * len(TAT)} phép so "
          f"({len(TO_HOP)} tổ hợp cờ × {len(TAT)} dạng 'để mặc định')")

    # ── 2) BẬT cờ -> khoá PHẢI ĐỔI, và mốc cũ là TIỀN TỐ ──────────────────
    print(f"\n{'-' * 78}\n2) BẬT cờ -> khoá ĐỔI (không thì bấm Chạy bị "
          f"smart-skip) và khoá mốc là TIỀN TỐ (nối ĐUÔI, không đổi ruột)"
          f"\n{'-' * 78}")
    for m in TG.MUC_KEO_DAI:
        if m <= 1.0:
            continue
        xau = 0
        for i, th in enumerate(TO_HOP):
            a = cu.khoa_chong_trung(**BASE, **th)
            b = MOI.khoa_chong_trung(**BASE, **th, keo_dai_giong=m)
            if b == a:
                hong += 1
                xau += 1
                print(f"  HỎNG mức {m} tổ hợp #{i}: khoá KHÔNG đổi")
            elif not b.startswith(a):
                hong += 1
                xau += 1
                print(f"  HỎNG mức {m} tổ hợp #{i}: khoá mốc KHÔNG phải tiền "
                      f"tố\n       mốc: {a}\n       mới: {b}")
        a0 = cu.khoa_chong_trung(**BASE)
        b0 = MOI.khoa_chong_trung(**BASE, keo_dai_giong=m)
        print(f"  ĐẠT  mức {m:.2f} -> đuôi {b0[len(a0):]!r} · "
              f"{len(TO_HOP) - xau}/{len(TO_HOP)} tổ hợp đổi khoá + giữ tiền tố")

    # ── 3) hai mức KHÁC nhau -> khoá KHÁC nhau ────────────────────────────
    print(f"\n{'-' * 78}\n3) Hai mức khác nhau -> khoá khác nhau; cùng một mức "
          f"viết khác kiểu -> khoá GIỐNG\n{'-' * 78}")
    kh = {m: MOI.khoa_chong_trung(**BASE, keo_dai_giong=m)
          for m in TG.MUC_KEO_DAI}
    for x, y in itertools.combinations(TG.MUC_KEO_DAI, 2):
        if kh[x] == kh[y]:
            hong += 1
            print(f"  HỎNG mức {x} và {y} ra CÙNG khoá")
    print(f"  ĐẠT  {len(TG.MUC_KEO_DAI)} mức -> {len(set(kh.values()))} khoá "
          f"khác nhau")
    for a, b in ((1.15, 1.150000001), (1.25, "1.25"), (1.40, 1.4)):
        if MOI.khoa_chong_trung(**BASE, keo_dai_giong=a) != \
                MOI.khoa_chong_trung(**BASE, keo_dai_giong=b):
            hong += 1
            print(f"  HỎNG {a!r} và {b!r} ra khoá KHÁC nhau")
    print("  ĐẠT  cùng một mức viết 3 kiểu khác nhau -> CÙNG một khoá")

    # ── 4) trên trần -> kẹp về trần (không đẻ khoá lạ) ────────────────────
    tran = float(TG.MUC_KEO_DAI[-1])
    if MOI.khoa_chong_trung(**BASE, keo_dai_giong=9.9) != kh[tran]:
        hong += 1
        print(f"  HỎNG mức 9,9 KHÔNG bị kẹp về trần {tran}")
    else:
        print(f"  ĐẠT  mức 9,9 bị kẹp về trần {tran} -> cùng khoá với trần")

    print(f"\n{'=' * 78}\nKETQUA: HỎNG {hong}\n{'=' * 78}")
    return 1 if hong else 0


if __name__ == "__main__":
    raise SystemExit(main())
