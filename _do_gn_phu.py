# -*- coding: utf-8 -*-
r"""ĐO **TỈ LỆ CHỮ CÓ MỐC** của giọng ngoài — chỗ hỏng nặng hơn cả độ lệch.

`_do_gn_moc.py` đo mốc LỆCH bao nhiêu. Nhưng với OmniVoice, chỗ hỏng nặng hơn
là **mốc KHÔNG CÓ**: `giong_ngoai._lay_moc_groq` bỏ mọi từ Groq nghe không
khớp (cố ý — mốc bịa còn tệ hơn thiếu mốc), nên chữ Groq nghe sai là chữ đó
mất mốc. edge-tts phủ 100% do cấu tạo (`WordBoundary` trả mọi từ).

Đồng thời chặn một **BẪY CỦA CHÍNH `_do_gn_moc.py`**: mục T3 ở đó lấy
`moc[0][0]` làm "mốc chữ đầu", nhưng khi mốc bỏ mất mấy từ đầu thì `moc[0]`
là từ THỨ BA — so nó với lúc bắt đầu phát tiếng ra lệch dương rất to, và đó
là lỗi của PHÉP ĐO chứ không phải của OmniVoice. File này chỉ tính lệch cho
những câu mà `moc[0]` **ĐÚNG LÀ** từ đầu câu.

    BQ_LUOT_SAN=l0 .venv\Scripts\python -u _do_gn_phu.py
"""
from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

import importlib.util as _u                                  # noqa: E402

from app.ai import recap                                     # noqa: E402
from app.core import giong_ngoai as gn                       # noqa: E402
from app.core import thay_giong as tg                        # noqa: E402

_sp = _u.spec_from_file_location("m", REPO / "_do_gn_moc.py")
M = _u.module_from_spec(_sp)
_sp.loader.exec_module(M)

LUOT = os.environ.get("BQ_LUOT_SAN", "l0")


def main() -> int:
    goc = REPO / "_do_gn_san"
    if not goc.is_dir():
        print("Chưa có hộp cát `_do_gn_san` — chạy `_do_gn_moc.py` trước.")
        return 2
    print(f"lượt {LUOT} · PHỦ = % chữ CÓ mốc · rung chỉ tính câu mà mốc[0] "
          f"ĐÚNG là từ đầu")
    print(f"  {'nn':<6}{'PHỦ %':>8}{'mốc[0] là từ đầu':>19}{'RUNG ms':>10}"
          f"{'n':>4}")
    for nn in ("vi", "en", "zh", "ja"):
        d = goc / f"{LUOT}_{nn}_OV"
        if not d.is_dir():
            continue
        texts = M.nap_cau(nn)
        phu, dau_dung, lech = [], 0, []
        for i, t in enumerate(texts):
            p = d / f"c{i:03d}.wav"
            if not p.exists():
                continue
            moc = gn._lay_moc_groq(t, str(p))
            tu = [x for x in recap._word_tokens(t) if M._chuan(x)]
            if not tu:
                continue
            phu.append(100.0 * len(moc) / len(tu))
            if moc and M._chuan(moc[0][2]) == M._chuan(tu[0]):
                dau_dung += 1
                im_dau, _c, _t = tg.do_le_im(str(p))
                lech.append((moc[0][0] - im_dau) * 1000.0)
        if not phu:
            continue
        g = statistics.median(lech) if lech else 0.0
        rung = (statistics.mean([abs(x - g) for x in lech]) if lech else 0.0)
        print(f"  {M.NHAN_NN.get(nn, nn):<6}{statistics.mean(phu):>8.1f}"
              f"{dau_dung:>13}/{len(phu):<5}{rung:>10.1f}{len(lech):>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
