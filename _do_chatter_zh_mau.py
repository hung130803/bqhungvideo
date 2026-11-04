# -*- coding: utf-8 -*-
r"""ATTRIBUTION — 1,81x thành 1,67x là do **MẪU THAM CHIẾU**, không do máy.

Chạy ĐÚNG 8 câu `zh_goc` bằng **CHÍNH FILE MẪU của lượt đo 25/08**
(`_do_chatter_dangn/mau/A_nu_ref24.wav`, còn nguyên trên đĩa) rồi so với arm
vừa đo bằng mẫu SINH LẠI hôm nay.

VÌ SAO PHÉP NÀY CÓ NGHĨA: đã đo được rằng Chatterbox **TIỀN ĐỊNH** theo bộ
`(chữ, mẫu, tiếng, seed)` — 6 câu ngắn dùng chung giữa bộ `zh_goc` và bộ `zh`
cho ra tỉ lệ GIỐNG NHAU tới 2 chữ số thập phân, ở HAI tiến trình khác nhau và
HAI vị trí khác nhau trong mẻ. Vậy thứ duy nhất còn khác giữa hôm nay và
25/08 là **BYTE của file mẫu**: cùng `CAU_MAU`, cùng giọng
`vi-VN-HoaiMyNeural`, mà mp3 edge-tts trả về hôm nay **khác MD5** bản 25/08
(cùng cỡ 49.824 byte, khác ruột).

Chạy:  .venv\Scripts\python.exe _do_chatter_zh_mau.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

MAU_CU = GOC / "_do_chatter_dangn" / "mau" / "A_nu_ref24.wav"
HOP = GOC / "_do_chatter_nhip"
SAN = HOP / "zh_goc__A_nu_MAUCU" / "v0"


def dai(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return 0.0


def main() -> int:
    import _do_chatter_nhip as DN
    from app.core import giong_chatter as gc

    if not MAU_CU.exists():
        print(f"KHÔNG còn file mẫu cũ {MAU_CU} -> không đo được, không bịa số.")
        return 2
    tt = gc.tinh_trang()
    if not tt["co"]:
        print("KHÔNG có môi trường Chatterbox -> dừng.")
        return 2

    tran = sorted((HOP / "tran__zh_goc").glob("tran_[0-9]*.wav"))
    if len(tran) != 8:
        print(f"Chưa có đủ trần zh_goc ({len(tran)}/8) -> chạy "
              f"_do_chatter_nhip.py trước.")
        return 2
    d_tran = [dai(p) for p in tran]

    SAN.mkdir(parents=True, exist_ok=True)
    cau = list(DN.BO["zh_goc"]["cau"])
    items = [{"i": i, "text": t, "raw": str(SAN / f"cb_{i:02d}.wav")}
             for i, t in enumerate(cau)]
    print(f"Đọc 8 câu zh_goc bằng MẪU CŨ {MAU_CU.name} ...")
    ket = gc._chay(items, str(MAU_CU), "zh", tt["python"], 3600, None)
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(ket.get("_sandbox"), trong=gc.thu_muc_chatter())
    except Exception:                                          # noqa: BLE001
        pass
    if not ket.get("ok"):
        print(f"HỎNG: {ket.get('loi')}")
        return 2

    d_cb = [dai(Path(it["raw"])) for it in items]
    print("\n i | chữ |  trần |  MẪU CŨ | tỉ lệ | (bảng 25/08)")
    cu = [4.0, 12.1, 5.0, 7.9, 3.9, 4.4, 8.1, 9.5]
    for i, (t, a, b) in enumerate(zip(cau, d_cb, d_tran)):
        print(f"{i:2d} | {len(t):3d} | {b:5.2f} | {a:7.2f} | "
              f"{a / b if b else 0:5.2f} | {cu[i]:5.2f}")
    print(f"\nTỔNG mẫu CŨ  {sum(d_cb):6.2f}s / trần {sum(d_tran):6.2f}s = "
          f"{sum(d_cb) / sum(d_tran):.3f}x")
    print(f"BẢNG 25/08   {sum(cu):6.2f}s / 30,40s = {sum(cu) / 30.4:.3f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
