# -*- coding: utf-8 -*-
"""XUẤT FILE TIẾNG cho anh Hùng TỰ NGHE — `_NGHE_THU_ANH_HUNG/da_ngon_ngu/`.

**TÔI KHÔNG CÓ TAI.** Mọi con số trong `_ra_bang_5_tieng.py` đều là số ĐO
(Groq chép ngược), và Groq cũng sai — nên bảng nói được *"chữ ra có đúng
không"* nhưng KHÔNG nói được *"nghe có hay không"*, *"có ngọng không"*,
*"nghe ra người Việt hay người nước ngoài nói tiếng Việt"*. Ba câu đó chỉ
tai người trả lời được.

Sắp theo **TIẾNG rồi tới GIỌNG** (không phải giọng rồi tiếng): anh Hùng nghe
để chọn giọng cho MỘT kênh MỘT thứ tiếng, nên mở đúng một thư mục là so được
mọi giọng trên cùng một câu.

Tên file mang sẵn KẾT LUẬN ĐO ĐƯỢC (`DAT`/`HONG`) + % sai, để nghe xong đối
chiếu ngay với số mà không phải tra bảng.

Chạy: .venv\\Scripts\\python -u _ra_file_nghe_5_tieng.py
"""
from __future__ import annotations


import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

from _bo_cau_thu_doc import NHAN_NN                             # noqa: E402
from _ra_bang_5_tieng import (NN5, chon_cot, doc_duoc,           # noqa: E402
                              gom, nap, nguong)

HOP = REPO / "bq_do_5_tieng"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "da_ngon_ngu"

#: Bao nhiêu giọng mỗi tiếng. Xuất hết 30+ giọng × 5 tiếng là 150 thư mục,
#: anh Hùng không nghe nổi — mà mục đích là CHỌN, không phải lưu trữ. Lấy
#: nhóm ĐẠT tốt nhất + toàn bộ nhóm HỎNG (nhóm hỏng mới là thứ cần nghe để
#: xác nhận "đúng là không dùng được").
SO_DAT_MOI_TIENG = 8


def _sach(s: str, n: int = 40) -> str:
    return re.sub(r"[^0-9A-Za-zÀ-ỹ]+", "_", s)[:n].strip("_") or "x"


def main() -> int:
    tat = nap()
    g = gom(tat)
    ng_tr, ng_cau = nguong(g, "tr"), nguong(g, "cau")
    cot_cua = chon_cot(ng_tr, ng_cau)
    NG = {"tr": ng_tr, "cau": ng_cau}

    NGHE.mkdir(parents=True, exist_ok=True)
    tong = 0
    for nn in NN5:
        cot = cot_cua[nn] or "tr"
        arms = [(ten, v) for ten, v in g.items() if v["nn"] == nn]
        if not arms:
            continue
        # ĐẠT tốt nhất trước, rồi toàn bộ HỎNG.
        dat, hong, chua = [], [], []
        for ten, v in arms:
            kq = doc_duoc(v[cot], NG[cot][nn]) if cot_cua[nn] else None
            (dat if kq == "CÓ" else hong if kq == "KHÔNG" else chua).append(
                (ten, v, kq))
        dat.sort(key=lambda x: (x[1][cot], x[1]["cau"]))
        lay = dat[:SO_DAT_MOI_TIENG] + hong + chua
        thu_nn = NGHE / f"{nn}_{_sach(NHAN_NN[nn])}"
        shutil.rmtree(thu_nn, ignore_errors=True)
        thu_nn.mkdir(parents=True, exist_ok=True)
        for ten, v, kq in lay:
            nhan = {"CÓ": "DAT", "KHÔNG": "HONG", None: "CHUA_KL"}[kq]
            so = "NA" if v[cot] != v[cot] else f"{v[cot]:03.0f}"
            dich = thu_nn / f"{nhan}_{so}pt_{_sach(v['voice'], 34)}"
            dich.mkdir(parents=True, exist_ok=True)
            src = HOP / f"{ten}_v1"
            if not src.is_dir():
                continue
            for f in sorted(src.glob("*.mp3")):
                if f.stat().st_size < 1000:
                    continue          # file 0 byte của lượt đọc hỏng
                loai = {"s": "cau", "b": "cau_ban_dia", "t": "doc_roi"}.get(
                    f.name[0], f.name[0])
                shutil.copy2(f, dich / f"{loai}_{f.stem[1:]}.mp3")
                tong += 1
        print(f"  {NHAN_NN[nn]:6s}: {len(dat)} ĐẠT (lấy "
              f"{min(len(dat), SO_DAT_MOI_TIENG)}) · {len(hong)} HỎNG · "
              f"{len(chua)} chưa kết luận -> {thu_nn.name}")

    (NGHE / "DOC_TRUOC_KHI_NGHE.txt").write_text(
        "FILE TIẾNG CỦA PHÉP ĐO 5 THỨ TIẾNG (Việt · Anh · Hàn · Nhật · Trung)\n"
        "=" * 70 + "\n\n"
        "Xếp theo TIẾNG rồi tới GIỌNG. Mỗi thư mục giọng có 3 loại file:\n"
        "  cau_*          câu bản ngữ thường (nghe xem có đọc nổi tiếng đó)\n"
        "  cau_ban_dia_*  câu có TÊN RIÊNG bản địa (phần khó nhất)\n"
        "  doc_roi_*      TÊN RIÊNG đọc MỘT MÌNH, không ngữ cảnh\n\n"
        "Tên thư mục giọng ghi sẵn kết luận ĐO ĐƯỢC:\n"
        "  DAT_xxxpt_...     đo ra ĐỌC ĐƯỢC tiếng này, xxx = % token sai\n"
        "  HONG_xxxpt_...    đo ra KHÔNG đọc được\n"
        "  CHUA_KL_...       chưa kết luận được (xem bảng)\n\n"
        "SỐ LÀ SỐ ĐO, KHÔNG PHẢI TAI. Máy chỉ trả lời được 'chữ ra có đúng\n"
        "không'. Ba câu chỉ tai anh trả lời được:\n"
        "  1. nghe có HAY không\n"
        "  2. có NGỌNG / sai dấu không\n"
        "  3. nghe ra người bản ngữ, hay người nước ngoài đọc tiếng đó\n\n"
        "Nghe nhóm HONG trước — đó là nhóm app sẽ CẢNH BÁO, cần anh xác nhận\n"
        "đúng là không dùng được.\n",
        encoding="utf-8")
    print(f"\n{tong} file -> {NGHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
