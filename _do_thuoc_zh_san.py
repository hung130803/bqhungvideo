"""SÀN BỊA CỦA THƯỚC "ÉP language=zh" — CON SỐ 85,72% CÓ ĐỌC ĐƯỢC KHÔNG?

`_do_tieng_trung_con.py` ép `language="zh"` khi chép bản thành phẩm rồi đối
chiếu với lời gốc, ra **85,72% thời lượng "có tiếng Trung"** trên 4 bản anh
Hùng xuất. Con số đó CHƯA đọc được, vì thiếu đúng cái cột mà chính docstring
của nó đòi: **SÀN BỊA**. Hai lý do nghi ngờ, cả hai đều nặng:
  · ép tiếng Trung lên giọng Việt thì whisper **bịa** chữ Hán;
  · bản Việt vốn LÀ bản dịch của lời Trung, nên chữ bịa ra vẫn "trùng" lời gốc
    theo nghĩa — phép đối chiếu tự nó KHÔNG tách được hai chuyện.

Nay có sẵn cặp SẠCH để dựng sàn, cùng video, cùng lượt dựng, cùng cấu hình,
khác đúng MỘT cờ:
  · `_kq_bu_goc_that_BAT.json` -> bản xuất **CÓ 25,57 giây tiếng Trung thật**
  · `_kq_bu_goc_that_TAT.json` -> bản xuất **KHÔNG có một mẩu tiếng gốc nào**

Chạy ĐÚNG thước đó lên cả hai. Bao nhiêu chữ Hán ra ở arm TẮT là bấy nhiêu chữ
Hán BỊA — đó là SÀN. Hai arm ra gần bằng nhau thì thước mù, và 85,72% phải bị
gạch khỏi báo cáo.

    .venv\\Scripts\\python _do_thuoc_zh_san.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ["WHISPER_PROVIDER"] = "groq"
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

import _do_tieng_trung_con as T                             # noqa: E402

SB = Path(r"D:\claude\_hop_cat_4loi\san_zh")
KQ = REPO / "_kq_thuoc_zh_san.json"


def main() -> int:
    from app.core.thay_giong import probe_duration
    SB.mkdir(parents=True, exist_ok=True)
    ket: dict = {"arm": []}

    for arm, nhan in (("TAT", "SÀN — bản xuất KHÔNG có tiếng gốc"),
                      ("BAT", "bản xuất CÓ 25,57 s tiếng Trung thật")):
        p = REPO / f"_kq_bu_goc_that_{arm}.json"
        if not p.exists():
            print(f"  thiếu {p.name}")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        v = Path(d["nghe_thu"])
        w = SB / f"{arm}.wav"
        T.rut_wav(v, w)
        z = T.chep(w, "zh", SB / f"{arm}_zh.json")
        dh = T.doan_han(z)
        dai = probe_duration(v)
        gh = sum(x["b"] - x["a"] for x in dh)
        r = {"arm": arm, "nhan": nhan, "giay_video": round(dai, 2),
             "giay_bu_THAT": (d.get("bu_goc") or {}).get("giay_bu", 0.0),
             "so_doan_han": len(dh),
             "ky_tu_han": sum(len(x["han"]) for x in dh),
             "giay_doan_co_han": round(gh, 2),
             "phan_tram": round(100.0 * gh / dai, 2) if dai else 0.0}
        ket["arm"].append(r)
        print(f"  {arm:<4} {nhan}")
        print(f"       tiếng Trung THẬT trong file: {r['giay_bu_THAT']} s")
        print(f"       ép zh -> {r['so_doan_han']} đoạn có chữ Hán · "
              f"{r['ky_tu_han']} ký tự · {r['giay_doan_co_han']} s "
              f"({r['phan_tram']}%)")

    if len(ket["arm"]) == 2:
        san, tren = ket["arm"][0], ket["arm"][1]
        ket["SAN_BIA_phan_tram"] = san["phan_tram"]
        ket["CHENH"] = round(tren["phan_tram"] - san["phan_tram"], 2)
        # Thước chỉ dùng được khi arm CÓ tiếng gốc bung ra nhiều chữ Hán HƠN
        # HẲN arm không có. Lấy mốc: chênh phải >= 10 điểm phần trăm.
        ket["THUOC_DUNG_DUOC"] = bool(ket["CHENH"] >= 10.0)
        print(f"\n  SÀN BỊA (arm không có tiếng gốc): {san['phan_tram']}%")
        print(f"  arm có 25,57 s tiếng Trung thật:  {tren['phan_tram']}%")
        print(f"  CHÊNH: {ket['CHENH']} điểm %")
        print(f"  => THƯỚC ÉP-ZH DÙNG ĐƯỢC KHÔNG: "
              f"{'CÓ' if ket['THUOC_DUNG_DUOC'] else 'KHÔNG — nó BỊA gần bằng '
                 'lượng thật, mọi số 85,72% phải GẠCH khỏi báo cáo'}")

    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
