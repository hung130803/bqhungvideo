"""LỜI KÊU 3 — ĐỐI CHỨNG CHO BỘ CHẤM DỊCH: 3,02/5 LÀ *DỊCH* XẤU HAY *THƯỚC* XẤU?

`_do_dich_cua_anh_hung.py` chấm bản dịch THẬT của anh Hùng ra **3,02/5** và
**64,29% câu <= 3 điểm**, trong khi bộ chấm CỦA CHÍNH APP ghi trong bản ghi job
là **8,77/10**. Hai thước lệch nhau quá xa để tin cái nào — và một con số
tuyệt đối không có SÀN/TRẦN thì không đọc được. Bài học repo: *"chốt chấm 413
bị nuốt trả 10/10"*, và *"cổng đối chứng tự PASS OAN"*.

BA ARM, **cùng một model chấm, cùng một prompt, cùng một đoạn GỐC**, chỉ khác
bản dịch đem đi chấm:

  · **SÀN** — ghép LỆCH hẳn 7 câu (`goc_i` với `dich_{i+7}`). Đây là bản dịch
    SAI CHẮC CHẮN. Thước nào tử tế cũng phải cho nó ~1 điểm. Ra cao là thước
    không phân biệt được gì, mọi số còn lại vứt đi.
  · **THẬT** — bản dịch anh Hùng đã nghe.
  · **TRẦN** — cho CHÍNH model chấm tự dịch lại đoạn gốc đó, rồi chấm bản dịch
    của chính nó. Đây là điểm CAO NHẤT bộ khung này với tới được: nó gánh cả
    phần thiệt do CỬA SỔ GHÉP (mốc quy về trục gốc bằng `t/k` nên đoạn "GỐC"
    có thể ôm lẹm câu bên cạnh). TRẦN thấp = lỗi của THƯỚC, không phải của app.

Đọc kết quả: THẬT ≈ TRẦN -> bản dịch tốt ngang mức khung này đo được, số 3,02
là tại thước. THẬT ≈ SÀN -> dịch hỏng thật.

    .venv\\Scripts\\python _do_dich_doi_chung.py
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

KQ = REPO / "_kq_dich_doi_chung.json"
MAU = 60          # số câu mỗi arm — đủ tách 3 arm, không đốt hạn mức vô ích
LECH = 7          # ghép lệch bấy nhiêu câu để dựng arm SÀN


def cham(cap: list[tuple[str, str]], ten: str) -> list:
    """Chấm 1-5 bằng ĐÚNG prompt của phép đo chính. `cap` = (gốc, dịch)."""
    ra: list = []
    for i in range(0, len(cap), D.ME):
        lo = cap[i:i + D.ME]
        pr = ("Với mỗi cặp (câu gốc tiếng Trung, bản dịch tiếng Việt), chấm:\n"
              "  \"tt\": độ TRUNG THÀNH của bản dịch, 1-5 "
              "(5 = đúng trọn nghĩa; 1 = sai hẳn/không liên quan)\n"
              "  \"nguon_ok\": câu GỐC tiếng Trung tự nó có đọc hiểu được "
              "không (true/false) — false nếu nó là chuỗi chữ vô nghĩa do "
              "máy nghe nhầm\n"
              "  \"loi\": nếu tt<=3 thì nêu NGẮN lỗi chính, không thì \"\"\n"
              "Trả JSON {\"ket_qua\":[{\"i\":<số>,\"tt\":<1-5>,"
              "\"nguon_ok\":<bool>,\"loi\":\"...\"}]}, ĐÚNG thứ tự.\n\n"
              + "\n".join(f'{j}. GỐC: {g or "(không ghép được)"}\n'
                          f'   DỊCH: {v}' for j, (g, v) in enumerate(lo)))
        d = D._lay(D.goi(pr, "Bạn chấm chất lượng dịch Trung-Việt. "      # noqa: SLF001
                             "Chỉ trả JSON.", f"{ten}{i}"), len(lo))
        ra += [x.get("tt") if isinstance(x, dict) else None for x in d]
    return ra


def tb(xs: list) -> float:
    v = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(v) / len(v), 2) if v else 0.0


def main() -> int:
    vi = json.loads(D.DICH.read_text(encoding="utf-8"))
    gs = (json.loads(D.GOC.read_text(encoding="utf-8")).get("segments") or [])
    D.ghep_goc(vi, gs)

    # Lấy mẫu GIỮA phim (bỏ 10 câu đầu/cuối: intro/outro không đại diện).
    idx = list(range(10, min(10 + MAU, len(vi) - LECH - 10)))
    print(f"mẫu {len(idx)} câu (#{idx[0]}-#{idx[-1]}) · model chấm "
          f"{D.MODEL_CHAM}")

    # ---- kiểm CỬA SỔ GHÉP có ôm lẹm không (nghi phạm số 1 của thước)
    lg = [len(vi[i]["goc"]) for i in idx]
    lv = [len(vi[i]["loi"]) for i in idx]
    print(f"độ dài TB: đoạn GỐC {sum(lg)/len(lg):.1f} ký tự Hán-Việt · "
          f"bản DỊCH {sum(lv)/len(lv):.1f} ký tự")

    ket: dict = {"mau": len(idx), "model_cham": D.MODEL_CHAM, "lech": LECH,
                 "do_dai_goc_TB": round(sum(lg) / len(lg), 1),
                 "do_dai_dich_TB": round(sum(lv) / len(lv), 1)}

    # ---- TRẦN: model chấm TỰ DỊCH đoạn gốc đó
    print("\nTRẦN — bảo chính model chấm tự dịch lại đoạn gốc...")
    tran_vi: list[str] = []
    for i in range(0, len(idx), D.ME):
        lo = [vi[j]["goc"] for j in idx[i:i + D.ME]]
        pr = ("Dịch từng câu tiếng Trung sau sang TIẾNG VIỆT, sát nghĩa, tự "
              "nhiên, dùng cho lồng tiếng. Trả JSON "
              "{\"ket_qua\":[{\"i\":<số>,\"vi\":\"...\"}]}, ĐÚNG thứ tự.\n\n"
              + "\n".join(f"{j}. {g}" for j, g in enumerate(lo)))
        d = D._lay(D.goi(pr, "Bạn là dịch giả Trung-Việt. Chỉ trả JSON.",  # noqa: SLF001
                         f"tran{i}"), len(lo))
        tran_vi += [str((x or {}).get("vi", "") if isinstance(x, dict)
                        else (x or "")) for x in d]

    arm = {
        "SAN_ghep_lech": [(vi[j]["goc"], vi[j + LECH]["loi"]) for j in idx],
        "THAT_ban_anh_Hung": [(vi[j]["goc"], vi[j]["loi"]) for j in idx],
        "TRAN_model_tu_dich": [(vi[j]["goc"], tran_vi[k])
                               for k, j in enumerate(idx)],
    }
    print()
    for ten, cap in arm.items():
        d = cham(cap, ten)
        hl = [x for x in d if isinstance(x, (int, float))]
        ket[ten] = {
            "diem_TB": tb(d), "so_cham_duoc": len(hl),
            "so_cau_<=3": sum(1 for x in hl if x <= 3),
            "ty_le_<=3_%": round(100.0 * sum(1 for x in hl if x <= 3)
                                 / max(1, len(hl)), 2),
            "phan_bo": {str(k): sum(1 for x in hl if round(x) == k)
                        for k in (1, 2, 3, 4, 5)},
        }
        print(f"  {ten:<22} điểm TB {ket[ten]['diem_TB']:>4}/5 · "
              f"<=3 điểm {ket[ten]['ty_le_<=3_%']:>6}% · "
              f"phân bố {ket[ten]['phan_bo']}")
        KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    s = ket["SAN_ghep_lech"]["diem_TB"]
    t = ket["THAT_ban_anh_Hung"]["diem_TB"]
    r = ket["TRAN_model_tu_dich"]["diem_TB"]
    ket["THUOC_CO_RANG"] = bool(r - s >= 1.0)
    ket["THAT_gan_ai_hon"] = "TRẦN" if abs(t - r) <= abs(t - s) else "SÀN"
    print(f"\n  SÀN {s} -> THẬT {t} -> TRẦN {r}")
    print(f"  thước có RĂNG (TRẦN - SÀN >= 1,0): "
          f"{'CÓ' if ket['THUOC_CO_RANG'] else 'KHÔNG — mọi số trên vô nghĩa'}")
    print(f"  bản THẬT gần {ket['THAT_gan_ai_hon']} hơn")
    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
