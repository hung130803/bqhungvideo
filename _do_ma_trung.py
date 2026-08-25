# -*- coding: utf-8 -*-
"""ĐO: hai bản ghi giọng nhân bản KHÁC TÊN có ra CÙNG một mã không.

Chạy trong hộp cát riêng (``BQ_DATA_DIR``) — KHÔNG đụng sổ/mẫu thật của
anh Hùng. Ba phép đo, mỗi phép một đường vào của cùng một lớp bệnh:

  ĐO 1  hai TÊN khác nhau mà ``_slug`` trùng -> ``them_giong`` ghi đè file
        mẫu của bản ghi trước, rồi cả hai trỏ chung một file.
  ĐO 2  sổ đã có sẵn hai bản ghi trỏ chung một file -> ``danh_sach()``
        trả hai dòng CÙNG mã (đúng ca cổng 63 đang đỏ).
  ĐO 3  xoá một bản ghi thì file mẫu dùng chung bị xoá theo -> bản ghi
        còn lại MẤT MẪU, biến khỏi combo mà không một dòng báo.
"""
from __future__ import annotations

import math
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent
HOP = Path(tempfile.mkdtemp(prefix="bq_ma_trung_"))
os.environ["BQ_DATA_DIR"] = str(HOP)
sys.path.insert(0, str(REPO))


def wav(p: Path, giay: float, hz: float) -> None:
    """WAV 24 kHz mono có tiếng thật (sin) — đủ qua `kiem_mau`."""
    sr = 24000
    n = int(sr * giay)
    d = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * hz * i / sr)))
                 for i in range(n))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt " +
                  struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16) +
                  b"data" + struct.pack("<I", len(d)) + d)


def _co(p) -> int:
    q = Path(str(p or "x"))
    return q.stat().st_size if q.is_file() else -1


def main() -> int:
    from app.core import nhan_ban_giong as NB

    a, b = HOP / "src" / "a.wav", HOP / "src" / "b.wav"
    wav(a, 8.0, 180.0)
    wav(b, 8.0, 300.0)

    print("=" * 70)
    print("ĐO 1 — hai TÊN khác nhau, `_slug` TRÙNG nhau")
    print("=" * 70)
    r1 = NB.them_giong("Giọng chị Lan", str(a), lang="vi")
    r2 = NB.them_giong("giọng chị lan", str(b), lang="vi")
    print(f"  thêm 1: ok={r1['ok']}  ma={r1['ma']!r}  loi={r1['loi']!r}")
    print(f"  thêm 2: ok={r2['ok']}  ma={r2['ma']!r}  loi={r2['loi']!r}")
    so = NB._doc_so()
    mas = [m for m in (NB.ma_giong(t) for t in so) if m]
    print(f"  sổ {len(so)} bản ghi · {len(mas)} mã · {len(set(mas))} mã KHÁC nhau")
    for t in so:
        mau = NB._muc(so, t).get("mau") or ""
        print(f"    {t!r} -> {Path(mau).name!r} (cỡ {_co(mau)})")
    trung1 = len(mas) != len(set(mas))
    print(f"  => MÃ TRÙNG: {trung1}")

    print()
    print("=" * 70)
    print("ĐO 2 — sổ đã có sẵn 2 bản ghi trỏ CÙNG một file mẫu")
    print("=" * 70)
    chung = NB.thu_muc_mau() / "chung.wav"
    wav(chung, 8.0, 220.0)
    NB._ghi_so({"Giọng chị Lan": {"mau": str(chung), "may": "vieneu",
                                  "lang": "vi", "giay": 8.0},
                "Giọng của tôi": {"mau": str(chung), "may": "vieneu",
                                  "lang": "vi", "giay": 8.0}})
    ds = NB.danh_sach()
    mas = [m for m, _n in ds]
    print(f"  danh_sach(): {len(mas)} mã / {len(set(mas))} khác nhau")
    for m, _n in ds:
        print(f"    {m!r}")
    if mas:
        print(f"  ten_theo_ma(mã đầu) = {NB.ten_theo_ma(mas[0])!r}")
    trung2 = len(mas) != len(set(mas))
    print(f"  => MÃ TRÙNG: {trung2}")

    print()
    print("=" * 70)
    print("ĐO 3 — xoá bản ghi này có làm MẤT mẫu của bản ghi kia không")
    print("=" * 70)
    # 3a — ĐƯỜNG THẬT (sổ đã đi qua `danh_sach` nên đã được chữa). Thước ĐÚNG
    #      không phải "file dùng chung còn không" mà là "bản ghi KIA còn mã
    #      dùng được không": sau khi chữa, mỗi bản ghi giữ file RIÊNG nên xoá
    #      file của bản ghi bị xoá là ĐÚNG.
    NB.xoa("Giọng chị Lan", xoa_ca_mau=True)
    ma_con = NB.ma_giong("Giọng của tôi")
    print(f"  3a sau khi chữa rồi xoá «Giọng chị Lan»:")
    print(f"       «Giọng của tôi» mã = {ma_con!r}")
    mat_a = not ma_con
    print(f"       => MẤT MẪU OAN: {mat_a}   (rỗng = mất, khỏi combo)")

    # 3b — CHỐT RIÊNG của `xoa`, KHÔNG cho `danh_sach` chữa trước. Sổ chép tay
    #      / bản app cũ vẫn có thể đưa thẳng một sổ dùng chung vào `xoa`.
    wav(chung, 8.0, 220.0)
    NB._ghi_so({"Giọng chị Lan": {"mau": str(chung), "may": "vieneu",
                                  "lang": "vi", "giay": 8.0},
                "Giọng của tôi": {"mau": str(chung), "may": "vieneu",
                                  "lang": "vi", "giay": 8.0}})
    NB.xoa("Giọng chị Lan", xoa_ca_mau=True)
    con = chung.is_file()
    ma_b = NB.ma_giong("Giọng của tôi")
    print(f"  3b xoá THẲNG trên sổ dùng chung (không qua `danh_sach`):")
    print(f"       file dùng chung còn = {con}")
    print(f"       «Giọng của tôi» mã = {ma_b!r}")
    mat_b = not ma_b
    print(f"       => MẤT MẪU OAN: {mat_b}")

    print()
    print("=" * 70)
    print(f"TỔNG: mã trùng do slug đụng = {trung1} · "
          f"mã trùng do sổ sẵn = {trung2} · "
          f"mất mẫu oan khi xoá = {mat_a or mat_b}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(HOP, ignore_errors=True)
