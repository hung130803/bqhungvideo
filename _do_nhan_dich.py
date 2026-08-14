# -*- coding: utf-8 -*-
"""ĐO CƠ CHẾ CHÍNH XÁC + THỬ CÁCH CHỮA — TRƯỚC KHI SỬA MỘT DÒNG MÃ NÀO.

`_do_lech_dich.py` chứng minh LLM trả THIẾU câu (37 vào, 29/33/34 ra) và app
lấy theo VỊ TRÍ. Nhưng còn HAI cơ chế khác nhau, và chúng cần cách chữa khác:

  · **CẮT ĐUÔI**  — model dừng sớm, câu 0..k-1 vẫn ĐÚNG chỗ, chỉ mất phần đuôi.
    Chữa = ĐÒI LẠI phần thiếu (hỏi lại riêng những câu chưa có).
  · **GỘP GIỮA**  — model gộp 2 câu ở giữa, mảng ngắn đi 1 và MỌI câu phía sau
    LỆCH BẬC. Chữa = phải MANG NHÃN, đòi lại thôi không đủ.

Phân biệt bằng cách bắt model TRẢ KÈM SỐ THỨ TỰ rồi xem dãy số nó phát ra có
LIỀN MẠCH không. Nếu ra `0..28` liền mạch = cắt đuôi; có LỖ ở giữa = gộp.

Cùng lúc đo luôn cách chữa đề xuất (B) so với cách hiện tại (A). **ĐAN XEN
B,A,B,A** — đo liền mạch đã cho kết luận NGƯỢC 3 lần trên máy này.

    .venv\\Scripts\\python _do_nhan_dich.py [zh|zh2|en] [số lượt]
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

_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")


def cach_A(cau, dich_sang, goc_ma) -> dict:
    """HIỆN TẠI: mảng chuỗi thuần, đọc theo VỊ TRÍ."""
    n = len(cau)
    ghi = {}
    that = llm.complete_json

    def _bay(*a, **k):
        d = that(*a, **k)
        x = d
        if isinstance(x, dict):
            for v in x.values():
                if isinstance(v, list):
                    x = v
                    break
        ghi["n"] = len(x) if isinstance(x, list) else -1
        return d

    llm.complete_json = _bay
    try:
        bd = tg._dich_loat(cau, dich_sang, goc_ma)
    finally:
        llm.complete_json = that
    con = [i for i in range(n) if _CJK.search(bd[i])]
    return {"tra": ghi.get("n", -1), "con_goc": len(con), "chi_so": con,
            "phu": n - len(con)}


def cach_B(cau, dich_sang, goc_ma) -> dict:
    """ĐỀ XUẤT: bắt model trả KÈM SỐ THỨ TỰ, map theo NHÃN, đòi lại phần thiếu."""
    n = len(cau)
    ten_dich = tg._ten_nn(dich_sang)
    con_thieu = list(range(n))
    ra: dict[int, str] = {}
    vong = 0
    day_so: list[list[int]] = []

    while con_thieu and vong < 3:
        vong += 1
        items = []
        for i in con_thieu:
            c = cau[i]
            dur = max(0.1, float(c["end"]) - float(c["start"]))
            items.append(f'#{i} [{dur:.1f} giây]: "{c["text"][:400]}"')
        prompt = (
            f"Dịch các câu thoại sau từ {tg._ten_nn(goc_ma)} sang {ten_dich}.\n"
            f"{chr(10).join(items)}\n\n"
            "QUY TẮC:\n"
            f"- Dịch sang {ten_dich}, văn NÓI tự nhiên.\n"
            "- ĐỌC LÊN phải lọt khung [số giây] của câu đó.\n"
            "- KHÔNG thêm chú thích, không phiên âm.\n"
            f"- Trả MẢNG JSON {len(con_thieu)} đối tượng "
            '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
            "BẮT BUỘC đủ MỌI số #, không bỏ câu nào, không gộp hai câu."
        )
        system = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. Dịch tự nhiên "
                  "như VĂN NÓI. CHỈ trả JSON thuần.")
        try:
            data = llm.complete_json(prompt, system=system)
        except Exception:  # noqa: BLE001
            break
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
        if not isinstance(data, list):
            break
        ds = []
        for o in data:
            if not isinstance(o, dict):
                continue
            try:
                i = int(o.get("i"))
            except (TypeError, ValueError):
                continue
            t = str(o.get("t") or "").strip()
            if 0 <= i < n and t:
                ds.append(i)
                ra.setdefault(i, t)
        day_so.append(ds)
        con_thieu = [i for i in range(n) if i not in ra]

    con = [i for i in range(n) if i not in ra or _CJK.search(ra[i])]
    return {"tra": len(day_so[0]) if day_so else -1, "con_goc": len(con),
            "chi_so": con, "phu": n - len(con), "vong": vong,
            "day_dau": day_so[0] if day_so else []}


def _lien_mach(ds: list[int]) -> str:
    """Dãy số model phát ra có LIỀN MẠCH từ 0 không -> cắt đuôi hay gộp giữa."""
    if not ds:
        return "rỗng"
    lo = [i for i in range(max(ds) + 1) if i not in set(ds)]
    if not lo:
        return f"LIỀN MẠCH 0..{max(ds)} (CẮT ĐUÔI)"
    return f"CÓ LỖ ở {lo[:8]} (GỘP GIỮA)"


def main() -> int:
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh"
    so_luot = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    dich_sang = "vi" if ten == "en" else "en"

    k = KHO.chuan_bi(ten, can_nhac=False)
    cau, goc_ma, n = k["cau"], k["ngon_ngu"], len(k["cau"])
    print(f"[{ten}] {n} câu · {goc_ma} -> {dich_sang}\n")

    kq = {"A": [], "B": []}
    for lan in range(1, so_luot + 1):
        # ĐAN XEN: B trước ở lượt lẻ, A trước ở lượt chẵn
        thu_tu = ("B", "A") if lan % 2 else ("A", "B")
        for nhan in thu_tu:
            r = (cach_B if nhan == "B" else cach_A)(cau, dich_sang, goc_ma)
            kq[nhan].append(r)
            them = ""
            if nhan == "B":
                them = (f" · vòng {r['vong']} · dãy đầu: "
                        f"{_lien_mach(r['day_dau'])}")
            print(f"  lượt {lan} [{nhan}] LLM trả {r['tra']}/{n} · "
                  f"phủ {r['phu']}/{n} · còn tiếng gốc {r['con_goc']}{them}")
        print()

    print("===== SO SÁNH =====")
    print(f"{'cách':>5} {'phủ TB':>8} {'còn tiếng gốc TB':>18} {'tệ nhất':>9}")
    for nhan in ("A", "B"):
        rs = kq[nhan]
        pt = sum(r["phu"] for r in rs) / len(rs)
        cg = sum(r["con_goc"] for r in rs) / len(rs)
        te = max(r["con_goc"] for r in rs)
        ten_c = "HIỆN TẠI" if nhan == "A" else "CÓ NHÃN"
        print(f"{ten_c:>9} {pt:>7.1f}/{n} {cg:>15.1f} câu {te:>8} câu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
