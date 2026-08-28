"""LỜI KÊU 3 (tiếp) — LỆCH BẬC ĐO LẠI CHO ĐÚNG, + VÍ DỤ CÂU HỎNG CỤ THỂ.

**VÌ SAO PHẢI ĐO LẠI:** lượt đầu (`_do_dich_cua_anh_hung.py` cột b) dịch NGƯỢC
bản Việt về tiếng Trung rồi so chrF với lời gốc ở 3 chỗ, ra **đúng chỗ 18,65 vs
lệch +1 18,57** — hai cột BẰNG NHAU, tức thước KHÔNG phân biệt được. Lý do đo
được: mốc bản dịch nằm trên trục ĐẦU RA, quy về trục gốc bằng `t/k` rồi hốt mọi
segment CHẠM cửa sổ, nên cửa sổ câu #i đã ôm sẵn phần lớn chữ của câu #i+1.
Cộng thêm hai lần đi qua LLM (dịch xuôi rồi dịch ngược) làm nhiễu nuốt hết tín
hiệu. Một cột 18,65 không có SÀN/TRẦN thì cũng không đọc được.

**THƯỚC MỚI, SẠCH HƠN HẲN — SO TIẾNG VIỆT VỚI TIẾNG VIỆT.** Đã có sẵn bản dịch
TRẦN (chính model chấm tự dịch từng cửa sổ gốc, đã chấm 4,88/5 nên nó ĐÚNG chỗ
theo cấu tạo). Vậy hỏi thẳng: câu Việt THẬT #i giống bản TRẦN của cửa sổ #i,
hay giống bản TRẦN của cửa sổ #i+1 hơn? Cùng một ngôn ngữ, KHÔNG qua lượt dịch
ngược nào, và có sẵn hai cột đối chứng (#i-1, #i+1) làm SÀN.

    .venv\\Scripts\\python _do_dich_lech_bac2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

import _do_dich_cua_anh_hung as D                           # noqa: E402
import _do_dich_doi_chung as DC                             # noqa: E402

KQ = REPO / "_kq_dich_lech_bac2.json"


def main() -> int:
    vi = json.loads(D.DICH.read_text(encoding="utf-8"))
    gs = (json.loads(D.GOC.read_text(encoding="utf-8")).get("segments") or [])
    D.ghep_goc(vi, gs)
    idx = list(range(10, min(10 + DC.MAU, len(vi) - DC.LECH - 10)))

    # bản TRẦN — lấy THẲNG từ cache của `_do_dich_doi_chung` (không gọi lại)
    tran: list[str] = []
    for i in range(0, len(idx), D.ME):
        lo = [vi[j]["goc"] for j in idx[i:i + D.ME]]
        pr = ("Dịch từng câu tiếng Trung sau sang TIẾNG VIỆT, sát nghĩa, tự "
              "nhiên, dùng cho lồng tiếng. Trả JSON "
              "{\"ket_qua\":[{\"i\":<số>,\"vi\":\"...\"}]}, ĐÚNG thứ tự.\n\n"
              + "\n".join(f"{j}. {g}" for j, g in enumerate(lo)))
        d = D._lay(D.goi(pr, "Bạn là dịch giả Trung-Việt. Chỉ trả JSON.",  # noqa: SLF001
                         f"tran{i}"), len(lo))
        tran += [str((x or {}).get("vi", "") if isinstance(x, dict)
                     else (x or "")) for x in d]

    dung, tre, som, lech = [], [], [], []
    for k, j in enumerate(idx):
        that = vi[j]["loi"]
        s0 = D.chrf(that, tran[k])
        s1 = D.chrf(that, tran[k + 1]) if k + 1 < len(tran) else None
        sm = D.chrf(that, tran[k - 1]) if k > 0 else None
        dung.append(s0)
        if s1 is not None:
            tre.append(s1)
        if sm is not None:
            som.append(sm)
        if s1 is not None and s1 > s0 + 5:
            lech.append({"i": j, "chrF_dung": s0, "chrF_+1": s1,
                         "that": that[:70], "tran_i": tran[k][:70],
                         "tran_i1": tran[k + 1][:70]})

    tb = lambda xs: round(sum(xs) / len(xs), 2) if xs else 0.0  # noqa: E731
    ket = {
        "mau": len(idx), "thuoc": "chrF Việt-với-Việt, mốc TRẦN đúng cửa sổ",
        "chrF_DUNG_CHO": tb(dung), "chrF_lech_+1": tb(tre),
        "chrF_lech_-1": tb(som),
        "so_cau_NGHI_LECH_BAC": len(lech),
        "ty_le_%": round(100.0 * len(lech) / max(1, len(idx)), 2),
        "vi_du_lech": lech[:10],
    }
    print(f"mẫu {len(idx)} câu · thước chrF Việt-Việt (mốc = bản TRẦN 4,88/5)")
    print(f"  chrF ĐÚNG CHỖ  {ket['chrF_DUNG_CHO']:>6}")
    print(f"  chrF lệch +1   {ket['chrF_lech_+1']:>6}   <- bệnh lệch bậc thì "
          f"cột này phải THẮNG cột trên")
    print(f"  chrF lệch -1   {ket['chrF_lech_-1']:>6}   (SÀN đối chứng)")
    print(f"  câu NGHI lệch bậc: {len(lech)}/{len(idx)} = {ket['ty_le_%']}%")

    # ---- ví dụ câu ĐIỂM THẤP, lấy từ phép đo chính
    kq = json.loads((REPO / "_kq_dich_anh_hung.json").read_text(
        encoding="utf-8"))
    xau = (kq.get("c_trung_thanh") or {}).get("cau_xau") or []
    ket["vi_du_cau_diem_thap"] = xau[:12]
    print(f"\nVÍ DỤ CÂU ĐIỂM THẤP (<=3), {len(xau)} câu, in 8:")
    for x in xau[:8]:
        print(f"  #{x['i']:>3} [{x['tt']}đ] GỐC: {x['goc']}")
        print(f"          DỊCH: {x['dich']}")
        print(f"          LỖI : {x['loi']}")

    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
