# -*- coding: utf-8 -*-
"""CHỖ NGHỈ GIỮA CÂU CỦA PIPER CÓ ỔN ĐỊNH KHÔNG — đo nhiều lượt, nhiều câu.

VÌ SAO: bộ tự-kiểm 5i của cổng 64 bắt được một câu 2 dấu phẩy ra **0 chỗ
nghỉ**, trong khi câu 3 dấu phẩy trước đó ra **3 chỗ nghỉ**. Piper là VITS —
bộ dự đoán độ dài của nó có NHIỄU, nên chỗ nghỉ KHÔNG cố định giữa các lượt.
Cổng nào chốt vào chỗ nghỉ mà không đo trước thì sẽ ĐỎ NHẤP NHÁY.

Đo: mỗi câu chạy N lượt, đếm số lượt CÓ chỗ nghỉ >= 60 ms.

    .venv\\Scripts\\python -u _do_piper_nghi.py
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

N = int(os.environ.get("BQ_LUOT", "3"))

UNG_VIEN = {
    "3 phẩy (câu đã ra 3 chỗ nghỉ)":
        "Hôm nay, tôi sẽ chia sẻ với các bạn một câu chuyện rất thú vị, "
        "mà tôi đã gặp cách đây ba phút, khi đang đi bộ trên con đường "
        "quen thuộc gần nhà mình.",
    "2 phẩy ngắn (câu vừa ra 0 chỗ nghỉ)":
        "Hôm nay, tôi sẽ chia sẻ với các bạn một câu chuyện rất thú vị, "
        "mà tôi đã gặp cách đây ba phút khi đang đi bộ.",
    "2 CHẤM giữa dòng":
        "Con đường gần nhà tôi giờ đã khác xưa. Người ta xây thêm rất "
        "nhiều nhà cao tầng. Tôi đi bộ ở đó mỗi buổi sáng sớm.",
    "chấm + phẩy dài":
        "Hôm nay tôi kể các bạn nghe một chuyện rất lạ. Sáng sớm, khi tôi "
        "vừa mở cửa ra, có một con mèo trắng ngồi im ở bậc thềm, nhìn tôi "
        "chằm chằm. Tôi đứng lặng một lúc lâu.",
}


def main() -> int:
    from app.core import piper_tts as PT
    d = REPO / f"bq_nghi_{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    try:
        print(f"{N} lượt/câu · ngưỡng nghỉ {PT.IM_TOI_THIEU * 1000:.0f} ms")
        print("=" * 74)
        for ten, cau in UNG_VIEN.items():
            co = 0
            chi_tiet = []
            for k in range(N):
                p = str(d / f"{abs(hash(ten)) % 9999}_{k}.wav")
                ok, _m = PT.doc_loat([cau], [p], lay_moc=False)
                if not ok or not ok[0]:
                    chi_tiet.append("ĐỌC HỎNG")
                    continue
                kh, tong = PT.khoang_co_tieng(p)
                im = tong - sum(e - s for s, e in kh)
                if len(kh) >= 2 and im > 0.05:
                    co += 1
                chi_tiet.append(f"{len(kh) - 1} nghỉ/{im * 1000:.0f}ms")
            print(f"  {ten:<38} {co}/{N} lượt CÓ nghỉ  · {chi_tiet}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
