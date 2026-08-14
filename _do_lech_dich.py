# -*- coding: utf-8 -*-
"""ĐO NGUYÊN NHÂN THẬT CỦA "KHÔNG KHỚP" + "NÓI KHÔNG CHUẨN": BẢN DỊCH LỆCH BẬC.

`_do_khop_mieng.py` đo ra câu #29..#33 có tiếng = 0,00s và chữ CÒN NGUYÊN TIẾNG
TRUNG, còn câu #29 lượt 3 lại mang bản dịch của câu #30. Nghi phạm:

    thay_giong.py:1280-1283 (_dich_loat)
        for i, c in enumerate(cau):
            t = data[i] if i < len(data) else None
            out.append(... if isinstance(t, str) ... else c["text"])

Prompt ĐÃ đánh số `#0 #1 #2 …` cho từng câu, nhưng lúc đọc kết quả thì **vứt
nhãn đi và lấy theo VỊ TRÍ trong mảng LLM trả về**. LLM bỏ/gộp đúng MỘT câu là:
  · mọi câu từ đó trở đi LỆCH BẬC — giọng đọc lời của đoạn KHÁC = "không khớp";
  · câu ở cuối rơi vào nhánh `else c["text"]` = **GIỮ NGUYÊN TIẾNG TRUNG** rồi
    đưa cho giọng tiếng Anh đọc = "nói không chuẩn".
Cả hai đều VÔ HÌNH với mọi thước của v2.27.0 (chúng chỉ đo ĐỘ DÀI).

File này KHÔNG sửa gì — chỉ đo. Gọi CHÍNH `tg._dich_loat` / `_dich_nguoc_cham`
/ `_rut_gon_loat` (thành phần THẬT, Groq thật), chặn `llm.complete_json` để ghi
lại ĐỘ DÀI MẢNG LLM trả về.

    .venv\\Scripts\\python _do_lech_dich.py [zh|zh2|en] [số lượt]
"""
from __future__ import annotations

import os
import re
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

import _do_kho_tg as KHO                       # noqa: E402
from app.ai import llm                         # noqa: E402
from app.core import thay_giong as tg          # noqa: E402

#: Chữ Hán + kana. Bản dịch sang tiếng Anh mà còn ký tự này = KHÔNG dịch được,
#: app đã lặng lẽ nhét lại câu GỐC (nhánh `else c["text"]`).
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")

_GHI: list = []


def _bat_llm():
    """Chặn complete_json để ghi ĐỘ DÀI MẢNG LLM trả về (không đổi hành vi)."""
    that = llm.complete_json

    def _bay(*a, **k):
        d = that(*a, **k)
        x = d
        if isinstance(x, dict):
            for v in x.values():
                if isinstance(v, list):
                    x = v
                    break
        _GHI.append(len(x) if isinstance(x, list) else -1)
        return d

    llm.complete_json = _bay
    return that


def main() -> int:
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh"
    so_luot = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    dich_sang = "vi" if ten == "en" else "en"

    k = KHO.chuan_bi(ten, can_nhac=False)
    cau = k["cau"]
    goc_ma = k["ngon_ngu"]
    n = len(cau)
    print(f"[{ten}] {k['tong']:.2f}s · {n} câu · {goc_ma} -> {dich_sang}\n")

    _bat_llm()
    tong_thieu = tong_con_goc = tong_lech = 0

    print(f"{'lượt':>5} {'câu vào':>8} {'LLM trả':>8} {'THIẾU':>6} "
          f"{'còn tiếng gốc':>14} {'LỆCH BẬC':>9}")
    for lan in range(1, so_luot + 1):
        _GHI.clear()
        bd = tg._dich_loat(cau, dich_sang, goc_ma)
        tra = _GHI[0] if _GHI else -1
        thieu = n - tra if tra >= 0 else -1

        # câu nào bị nhét lại nguyên văn câu GỐC (nhánh else c["text"])
        y_het = [i for i in range(n) if bd[i].strip() == cau[i]["text"].strip()]
        con_cjk = [i for i in range(n) if _CJK.search(bd[i])]

        # LỆCH BẬC: bản dịch câu i thật ra là của câu i+1? So bằng chính bản
        # dịch — nếu LLM trả đủ thì không lệch; thiếu k thì k câu cuối hỏng và
        # phần sau điểm bỏ bị đẩy lên. Đếm bằng số câu "còn tiếng gốc" nằm ở
        # ĐUÔI (dấu hiệu chắc chắn của lấy-theo-vị-trí).
        duoi = 0
        for i in range(n - 1, -1, -1):
            if i in con_cjk or i in y_het:
                duoi += 1
            else:
                break
        lech = max(0, thieu) if thieu > 0 else 0
        tong_thieu += max(0, thieu)
        tong_con_goc += len(con_cjk)
        tong_lech += lech
        print(f"{lan:>5} {n:>8} {tra:>8} {thieu:>6} "
              f"{len(con_cjk):>10} câu {lech:>9}")
        if con_cjk:
            print(f"        câu còn nguyên tiếng gốc: {con_cjk}"
                  f"  (đuôi liền mạch {duoi} câu)")
            for i in con_cjk[:3]:
                print(f'          #{i}: "{bd[i][:56]}"')

    print(f"\n===== TỔNG {so_luot} LƯỢT =====")
    print(f"  LLM trả THIẾU tổng cộng      : {tong_thieu} câu")
    print(f"  câu ra còn nguyên tiếng gốc  : {tong_con_goc} câu"
          f"  ({100.0 * tong_con_goc / max(1, n * so_luot):.1f}%)")
    print("  -> mỗi câu thiếu = 1 bậc lệch cho MỌI câu phía sau"
          " + 1 câu đưa tiếng Trung cho giọng Anh đọc")

    # --- 2 hàm CÒN LẠI có cùng bệnh không
    print("\n===== 2 HÀM CÙNG BỆNH (quét mã, không đoán) =====")
    src = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")
    for ten_h, mau in (("_dich_loat", r"t = data\[i\] if i < len\(data\)"),
                       ("_dich_nguoc_cham", r"out\.append\(float\(data\[i\]\)\)"),
                       ("_rut_gon_loat", r"t = data\[j\] if j < len\(data\)")):
        co = "CÓ" if re.search(mau, src) else "không"
        print(f"  {ten_h:<18} lấy theo VỊ TRÍ: {co}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
