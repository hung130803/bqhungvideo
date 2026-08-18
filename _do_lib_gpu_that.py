# -*- coding: utf-8 -*-
"""KIỂM CUỐI: `_lib` MỘT MÌNH có cho ra GPU không — đi ĐÚNG cửa app dùng.

Phép đo `_do_demucs_gpu.py` chứng minh "GPU nhanh hơn CPU", nhưng nó bật GPU
bằng cách chèn `PYTHONPATH` — tức nó chứng minh CÁI MÁY làm được, chưa chứng
minh CÁI APP làm được. Đây là đúng khoảng cách đã làm sập nhiều lượt trước
("test xanh oan vì tự dựng dữ liệu giả không đi qua đường thật").

Cửa thật: `thay_giong.tach_giong(cach="demucs")` -> `_tach_demucs` -> tiến
trình riêng chạy `_bq_tach_runner.py` với `sys.path.insert(0, _lib)`. Ở đây
KHÔNG đặt PYTHONPATH: nếu `_lib` đã có torch bản CUDA thì nó phải THẮNG torch
`+cpu` của `.venv` và kết quả trả về phải ghi `thiet_bi = cuda`.

    .venv\\Scripts\\python -u _do_lib_gpu_that.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
SAN = REPO / "_do_demucs_gpu_out"


def main() -> int:
    from app.core import thay_giong as TG

    # Chốt: KHÔNG được có PYTHONPATH trỏ vào thư mục đo — nếu còn thì phép
    # kiểm này lại đo cái mẹo chứ không đo `_lib`.
    pp = (os.environ.get("PYTHONPATH") or "")
    print(f"PYTHONPATH = {pp!r}  (phải RỖNG thì phép kiểm mới có nghĩa)")
    if "_do_cuda" in pp:
        print("DỪNG: PYTHONPATH còn trỏ vào thư mục đo -> phép kiểm vô nghĩa")
        return 2

    goi = TG.do_goi_tach_giong(TG.lib_demucs())
    print(f"lib      = {TG.lib_demucs()}")
    for g in TG.GOI_TACH_GIONG:
        print(f"  {g:10} trong _lib: {goi[g]['lib']}")
    thieu = [g for g in TG.GOI_TACH_GIONG if not goi[g]["lib"]]
    if thieu:
        print(f"DỪNG: _lib còn thiếu {thieu}")
        return 1

    wav = SAN / "vao.wav"
    if not wav.exists():
        print("DỪNG: chưa có file đo, chạy _do_demucs_gpu.py trước")
        return 1
    ra = SAN / "lib_that"
    ra.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    r = TG._tach_demucs(wav, ra, "htdemucs", 0, None)
    wall = time.time() - t0
    print()
    print(f"  thiết bị THẬT app chạy : {r.get('thiet_bi')}")
    print(f"  torch app nạp          : {r.get('torch')}")
    print(f"  apply_model            : {r.get('giay')}s")
    print(f"  cả lượt (wall)         : {wall:.2f}s")
    print(f"  độ dài tiếng           : {r.get('do_dai')}s")
    tot = str(r.get("thiet_bi")) == "cuda"
    print()
    print("KẾT LUẬN: " + ("ĐẠT — app tự chạy GPU qua _lib, KHÔNG cần mẹo nào"
                          if tot else
                          "CHƯA ĐẠT — app vẫn chạy " + str(r.get("thiet_bi"))))
    return 0 if tot else 1


if __name__ == "__main__":
    sys.exit(main())
