# -*- coding: utf-8 -*-
"""DUMP PHIẾU THÔ của thước chấm dịch — để quét luật OFFLINE, không gọi lại LLM.

VÌ SAO TÁCH LÀM HAI BƯỚC (dump ở đây · quét luật ở `_do_dich_luat.py`):
thước hiện tại kêu oan ~30%. Muốn hạ nó thì phải thử NHIỀU luật gộp khác nhau
(ngưỡng theo từng trục · trọng số · cần mấy model đồng ý ở cửa thuật ngữ).
Nếu mỗi luật lại gọi LLM một lượt thì hiệu số giữa hai luật LẪN NHIỄU của LLM
— và LLM ở repo này đã đo được nhấp nháy tới 0% vs 39,1% trên CÙNG một mã.
Dump phiếu thô MỘT LẦN rồi chấm mọi luật trên CÙNG bộ phiếu thì hiệu số là của
LUẬT, không phải của tâm trạng model.

Mỗi lượt lưu:
  · `cham[model][trục]` — điểm THÔ của từng model, chưa lấy trung vị
  · `tn[model]`         — danh sách khoá lỗi thuật ngữ THÔ của từng model
  · `loi_may`           — luật máy (tiền định, tính lại được nhưng lưu cho gọn)
Mỗi lượt XÁO KHÁC NHAU (seed = SEED + số lượt): thứ tự bài trong prompt là một
biến thật (khối toàn-hỏng mồi model chấm gắt), giữ nguyên một thứ tự cho mọi
lượt là đo cùng một điều kiện nhiều lần rồi tưởng là đã đo nhiều điều kiện.

  .venv\\Scripts\\python -u _do_dich_calib.py            # 3 lượt -> file mặc định
  BQ_LUOT=3 BQ_RA=_do_dich_calib_kiem.json ... _do_dich_calib.py
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

from _do_bo_hong import HONG, TOT                        # noqa: E402
from app.ai import cham_dich as CD                       # noqa: E402

SEED = 20260816
SO_LUOT = int(os.environ.get("BQ_LUOT", "3"))
RA = REPO / os.environ.get("BQ_RA", "_do_dich_calib.json")
#: lượt đầu tiên đánh số mấy — để chạy thêm lượt KIỂM mà không trùng seed
BAT_DAU = int(os.environ.get("BQ_LUOT_TU", "0"))


def dung_bo(seed: int):
    bo = [(g, d, ma) for ma, g, d in HONG] + [(g, d, "TOT") for g, d in TOT]
    random.Random(seed).shuffle(bo)
    return [x[0] for x in bo], [x[1] for x in bo], [x[2] for x in bo]


def mot_luot(so: int) -> dict:
    goc, dich, nhan = dung_bo(SEED + so)
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=6) as ex:
        f_cham = {m: ex.submit(CD._cham_mot_model, goc, dich, "zh", "vi", m)
                  for m in CD.MODEL_HOI_DONG}
        f_tn = {m: ex.submit(CD._soat_mot_model, goc, dich, "zh", "vi", m)
                for m in CD.MODEL_HOI_DONG}
        cham = {m: f.result() for m, f in f_cham.items()}
        tn = {m: f.result() for m, f in f_tn.items()}

    cau = []
    for i in range(len(goc)):
        cau.append({
            "goc": goc[i], "dich": dich[i], "nhan": nhan[i],
            "loi_may": CD.loi_may(goc[i], dich[i], "vi"),
            "cham": {m: cham[m].get(i, {}) for m in CD.MODEL_HOI_DONG},
            "tn": {m: tn[m][i] for m in CD.MODEL_HOI_DONG},
        })
    giay = time.time() - t0
    thieu = sum(1 for c in cau
                if not any(c["cham"][m] for m in CD.MODEL_HOI_DONG))
    print(f"  lượt {so}: {len(cau)} câu · {giay:.0f}s · "
          f"{thieu} câu không model nào chấm được")
    return {"so": so, "seed": SEED + so, "giay": round(giay, 1), "cau": cau}


def main() -> int:
    print("=" * 72)
    print(f"DUMP PHIẾU THÔ — {len(HONG)} bản HỎNG + {len(TOT)} bản TỐT, "
          f"{SO_LUOT} lượt (từ lượt {BAT_DAU})")
    print(f"hội đồng: {CD.MODEL_HOI_DONG}")
    print("=" * 72)
    luot = [mot_luot(BAT_DAU + i) for i in range(SO_LUOT)]
    RA.write_text(json.dumps({"models": list(CD.MODEL_HOI_DONG),
                              "luot": luot}, ensure_ascii=False),
                  encoding="utf-8")
    print(f"\nĐã ghi {RA.name} ({RA.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
