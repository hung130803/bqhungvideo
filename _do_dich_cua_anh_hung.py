"""LỜI KÊU 3 — "dịch mấy đoạn âm thanh gốc lỗi quá": CHẤM TRÊN CHÍNH LƯỢT ANH
HÙNG VỪA CHẠY, KHÔNG DỰNG LẠI KỊCH BẢN (28/08/2026).

Vật liệu là **bản dịch THẬT anh Hùng đã nghe**, moi từ `khop.moc_tu` trong bản
ghi job còn sót trong `studio.db-wal` (168 câu, video `八位好莱坞导演…`), đối
chiếu với **lời gốc tiếng Trung** do Groq `whisper-large-v3` chép lại từ chính
file nguồn.

BỐN CỘT, và cột nào cũng phải có ĐỐI CHỨNG:
  (a) **CÒN NGUYÊN TIẾNG TRUNG** — đếm ký tự Hán trong bản dịch. Đây cũng là
      thước đếm **CÂU BỊ LLM BỎ**: nhánh lùi `ra.get(i) or c["text"]` trả về
      NGUYÊN VĂN tiếng Trung, nên câu bị bỏ *phải* lộ ra ở cột này.
  (b) **LỆCH BẬC** — dịch NGƯỢC bản Việt về tiếng Trung bằng model **KHÁC**
      model đã dịch (`GROQ_LLM_MODEL` = `openai/gpt-oss-120b` -> chấm bằng
      `qwen/qwen3.8-27b`), rồi so chrF với lời gốc ở **ĐÚNG chỗ** và ở **hai
      chỗ bên cạnh**. Câu #i mang lời dịch của #i+1 thì cột "lệch +1" phải
      thắng cột "đúng chỗ" — đó là chữ ký của bệnh, không phải cảm giác.
  (c) **ĐIỂM TRUNG THÀNH 1-5** — model chấm KHÁC model dịch.
  (d) **CHỮ NGUỒN CÓ SAI KHÔNG** — nếu whisper nghe nhầm thì sửa dịch bao nhiêu
      cũng vô ích. Hỏi thẳng model chấm: câu tiếng Trung này tự nó có đọc hiểu
      được không.

    .venv\\Scripts\\python _do_dich_cua_anh_hung.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

DICH = Path(r"D:\claude\_hop_cat_4loi\_moi\ban_dich_168_cau.json")
GOC = Path(r"D:\claude\_hop_cat_4loi\m3\x4\goc_auto.json")
KQ = REPO / "_kq_dich_anh_hung.json"
CACHE = Path(r"D:\claude\_hop_cat_4loi\_cache_dich")

#: Model CHẤM phải KHÁC model DỊCH. `GROQ_LLM_MODEL` mặc định là
#: `openai/gpt-oss-120b` -> chấm và dịch ngược bằng Qwen (mạnh tiếng Trung).
MODEL_CHAM = "qwen/qwen3.8-27b"

#: Hệ số làm chậm hình của ĐÚNG video này, đọc từ bản ghi job
#: (`khop.he_so_hinh = 1.25`, chạm trần). Mốc bản dịch nằm trên trục ĐẦU RA
#: (đã giãn) nên phải chia `k` mới về được trục của lời gốc.
K_HINH = 1.25

_HAN = re.compile(r"[㐀-䶿一-鿿]")
ME = 12                       # số câu mỗi lượt gọi LLM


def han(s: str) -> str:
    return "".join(_HAN.findall(s or ""))


def chrf(a: str, b: str, n: int = 4, beta: float = 2.0) -> float:
    """chrF — F-score trên n-gram KÝ TỰ. Hợp tiếng Trung (không có dấu cách)."""
    a = re.sub(r"\s+", "", a or "")
    b = re.sub(r"\s+", "", b or "")
    if not a or not b:
        return 0.0
    ps, rs = [], []
    for k in range(1, n + 1):
        ca = Counter(a[i:i + k] for i in range(len(a) - k + 1))
        cb = Counter(b[i:i + k] for i in range(len(b) - k + 1))
        if not ca or not cb:
            continue
        trung = sum((ca & cb).values())
        ps.append(trung / max(1, sum(ca.values())))
        rs.append(trung / max(1, sum(cb.values())))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return round(100.0 * (1 + b2) * p * r / (b2 * p + r), 2)


def ghep_goc(vi: list, gs: list) -> None:
    """Gắn `c["goc"]` = lời gốc CỦA RIÊNG câu đó. Sửa tại chỗ.

    **BẢN ĐẦU CỦA HÀM NÀY LÀ MỘT THƯỚC HỎNG, GIỮ LẠI BÀI HỌC:** nó hốt MỌI
    segment CHẠM cửa sổ `[bat_dau/k, ket_thuc/k]` với lề 0,35 s. Mốc câu và mốc
    segment lệch nhau chút ít, nên cửa sổ gần như luôn ôm THÊM segment LIỀN
    TRƯỚC. Bộ chấm đọc đoạn gốc hai câu, thấy bản dịch chỉ có một câu, liền
    chấm *"bỏ sót"* — **bản dịch ĐÚNG bị chấm 2 điểm**. Xem 8 ví dụ in ra ở
    `_do_dich_lech_bac2.py`: câu nào cũng "bỏ sót" đúng phần mà cửa sổ TỰ THÊM
    vào. Nó còn kéo theo hai số sai nữa: arm TRẦN được điểm cao (4,88) chỉ vì
    nó dịch CẢ cửa sổ hai câu, và cột "lệch +1" bằng hệt cột "đúng chỗ" vì hai
    cửa sổ cạnh nhau chồng lên nhau gần hết.

    **CÁCH ĐÚNG: mỗi câu lấy ĐÚNG MỘT segment — segment có TÂM gần tâm câu
    nhất** (quy về trục gốc bằng `t/k`). Không có lề, không cộng dồn, nên cửa
    sổ không thể phình ra ôm câu bên cạnh.
    """
    for c in vi:
        tam = (c["bat_dau"] + c["ket_thuc"]) / 2.0 / K_HINH
        s = min(gs, key=lambda x: abs((x["start"] + x["end"]) / 2.0 - tam))
        c["goc"] = s["text"]
        c["goc_tam"] = round((s["start"] + s["end"]) / 2.0, 2)


def goi(prompt: str, system: str, ten: str) -> object:
    """Gọi LLM có CACHE ra đĩa — lượt đo lại khỏi đốt hạn mức và ra số khác."""
    CACHE.mkdir(parents=True, exist_ok=True)
    import hashlib
    h = hashlib.sha1((MODEL_CHAM + system + prompt).encode("utf-8")).hexdigest()
    p = CACHE / f"{ten}_{h[:16]}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            pass
    from app.ai import llm
    d = llm.complete_json(prompt, system=system, model=MODEL_CHAM)
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _lay(d: object, n: int) -> list:
    """Bóc mảng ra khỏi thứ LLM trả về, chấp nhận vài kiểu bọc."""
    if isinstance(d, list):
        x = d
    elif isinstance(d, dict):
        x = None
        for k in ("ket_qua", "results", "items", "data", "ds", "cau"):
            if isinstance(d.get(k), list):
                x = d[k]
                break
        if x is None:
            x = [d.get(str(i)) for i in range(n)]
    else:
        x = []
    return list(x) + [None] * max(0, n - len(x))


def main() -> int:
    vi = json.loads(DICH.read_text(encoding="utf-8"))
    gs = (json.loads(GOC.read_text(encoding="utf-8")).get("segments") or [])
    print(f"bản dịch THẬT: {len(vi)} câu · lời gốc: {len(gs)} segment")

    # ---- ghép mỗi câu Việt với lời gốc ĐÚNG CHỖ (quy về trục gốc bằng /k)
    ghep_goc(vi, gs)
    print(f"trục ĐẦU RA dài nhất {max(c['ket_thuc'] for c in vi):.1f}s "
          f"-> chia k={K_HINH} -> {max(c['ket_thuc'] for c in vi)/K_HINH:.1f}s "
          f"(lời gốc dài {gs[-1]['end']:.1f}s)")
    co_goc = [c for c in vi if han(c["goc"])]
    print(f"câu ghép được lời gốc: {len(co_goc)}/{len(vi)}")

    ket: dict = {"video": "八位好莱坞导演联手拍的电影有多厉害#电影解说.mp4",
                 "so_cau": len(vi), "model_cham": MODEL_CHAM,
                 "k_hinh": K_HINH}

    # ---- (a) CÒN TIẾNG TRUNG / CÂU BỊ BỎ
    con_han = [c for c in vi if han(c["loi"])]
    ket["a_con_chu_goc"] = {
        "so_cau_con_chu_han": len(con_han),
        "ty_le_%": round(100.0 * len(con_han) / len(vi), 2),
        "tong_ky_tu_han": sum(len(han(c["loi"])) for c in vi),
        "GHI_CHU": ("nhánh lùi `ra.get(i) or c['text']` trả nguyên văn tiếng "
                    "Trung, nên số này CŨNG là số câu bị LLM bỏ"),
        "doi_chung_ban_ghi_job": {"sot_chu_goc_truoc": 0, "sot_chu_goc_sau": 0},
    }
    print(f"\n(a) CÒN CHỮ HÁN trong bản dịch: {len(con_han)}/{len(vi)} câu "
          f"= {ket['a_con_chu_goc']['ty_le_%']}%  -> CÂU BỊ LLM BỎ: {len(con_han)}")

    # ---- (b) LỆCH BẬC: dịch NGƯỢC bằng model KHÁC rồi so chrF 3 chỗ
    print(f"\n(b) LỆCH BẬC — dịch ngược {len(vi)} câu bằng {MODEL_CHAM}...")
    bt: list[str] = []
    for i in range(0, len(vi), ME):
        lo = vi[i:i + ME]
        pr = ("Dịch từng câu tiếng Việt sau sang TIẾNG TRUNG GIẢN THỂ. "
              "Trả về JSON: {\"ket_qua\":[{\"i\":<số>,\"zh\":\"<bản dịch>\"}]}. "
              "Giữ ĐÚNG số câu, ĐÚNG thứ tự, dịch sát nghĩa, không thêm bớt.\n\n"
              + "\n".join(f'{j}. {c["loi"]}' for j, c in enumerate(lo)))
        d = _lay(goi(pr, "Bạn là dịch giả Việt-Trung. Chỉ trả JSON.",
                     f"bt{i}"), len(lo))
        for x in d:
            bt.append(str((x or {}).get("zh", "") if isinstance(x, dict)
                          else (x or "")))
        print(f"    {min(i+ME, len(vi))}/{len(vi)}")

    dung, tre1, som1 = [], [], []
    for i, c in enumerate(vi):
        if not han(c["goc"]) or not han(bt[i]):
            continue
        dung.append(chrf(bt[i], c["goc"]))
        if i + 1 < len(vi) and han(vi[i + 1]["goc"]):
            tre1.append(chrf(bt[i], vi[i + 1]["goc"]))
        if i > 0 and han(vi[i - 1]["goc"]):
            som1.append(chrf(bt[i], vi[i - 1]["goc"]))
    n_lech = sum(1 for i, c in enumerate(vi)
                 if han(c["goc"]) and han(bt[i]) and i + 1 < len(vi)
                 and han(vi[i + 1]["goc"])
                 and chrf(bt[i], vi[i + 1]["goc"]) > chrf(bt[i], c["goc"]) + 5)
    tb = lambda xs: round(sum(xs) / len(xs), 2) if xs else 0.0  # noqa: E731
    ket["b_lech_bac"] = {
        "chrF_DUNG_CHO": tb(dung), "chrF_lech_+1": tb(tre1),
        "chrF_lech_-1": tb(som1), "so_cau_do": len(dung),
        "so_cau_NGHI_LECH_BAC": n_lech,
        "ty_le_lech_%": round(100.0 * n_lech / max(1, len(dung)), 2),
    }
    print(f"    chrF đúng chỗ {tb(dung)} | lệch +1 {tb(tre1)} | "
          f"lệch -1 {tb(som1)}")
    print(f"    câu NGHI lệch bậc: {n_lech}/{len(dung)} = "
          f"{ket['b_lech_bac']['ty_le_lech_%']}%")
    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")

    # ---- (c)+(d) TRUNG THÀNH 1-5 + CHỮ NGUỒN CÓ SAI KHÔNG
    print(f"\n(c)+(d) chấm trung thành 1-5 + soi chữ NGUỒN bằng {MODEL_CHAM}...")
    diem: list = []
    for i in range(0, len(vi), ME):
        lo = vi[i:i + ME]
        pr = ("Với mỗi cặp (câu gốc tiếng Trung, bản dịch tiếng Việt), chấm:\n"
              "  \"tt\": độ TRUNG THÀNH của bản dịch, 1-5 "
              "(5 = đúng trọn nghĩa; 1 = sai hẳn/không liên quan)\n"
              "  \"nguon_ok\": câu GỐC tiếng Trung tự nó có đọc hiểu được "
              "không (true/false) — false nếu nó là chuỗi chữ vô nghĩa do "
              "máy nghe nhầm\n"
              "  \"loi\": nếu tt<=3 thì nêu NGẮN lỗi chính, không thì \"\"\n"
              "Trả JSON {\"ket_qua\":[{\"i\":<số>,\"tt\":<1-5>,"
              "\"nguon_ok\":<bool>,\"loi\":\"...\"}]}, ĐÚNG thứ tự.\n\n"
              + "\n".join(f'{j}. GỐC: {c["goc"] or "(không ghép được)"}\n'
                          f'   DỊCH: {c["loi"]}' for j, c in enumerate(lo)))
        d = _lay(goi(pr, "Bạn chấm chất lượng dịch Trung-Việt. Chỉ trả JSON.",
                     f"cham{i}"), len(lo))
        for j, x in enumerate(d):
            x = x if isinstance(x, dict) else {}
            diem.append({"i": i + j, "tt": x.get("tt"),
                         "nguon_ok": x.get("nguon_ok"),
                         "loi": str(x.get("loi") or "")[:120],
                         "goc": lo[j]["goc"][:60], "dich": lo[j]["loi"][:80]})
        print(f"    {min(i+ME, len(vi))}/{len(vi)}")

    hop_le = [d for d in diem if isinstance(d.get("tt"), (int, float))]
    xau = [d for d in hop_le if d["tt"] <= 3]
    nguon_sai = [d for d in diem if d.get("nguon_ok") is False]
    ket["c_trung_thanh"] = {
        "so_cau_cham_duoc": len(hop_le),
        "diem_TB": tb([d["tt"] for d in hop_le]),
        "so_cau_<=3": len(xau),
        "ty_le_cau_xau_%": round(100.0 * len(xau) / max(1, len(hop_le)), 2),
        "phan_bo": {str(k): sum(1 for d in hop_le if round(d["tt"]) == k)
                    for k in (1, 2, 3, 4, 5)},
        "cau_xau": xau[:25],
    }
    ket["d_chu_nguon"] = {
        "so_cau_NGUON_SAI": len(nguon_sai),
        "ty_le_%": round(100.0 * len(nguon_sai) / max(1, len(diem)), 2),
        "vi_du": nguon_sai[:15],
    }
    print(f"    điểm trung thành TB {ket['c_trung_thanh']['diem_TB']}/5 · "
          f"phân bố {ket['c_trung_thanh']['phan_bo']}")
    print(f"    câu <=3 điểm: {len(xau)}/{len(hop_le)} = "
          f"{ket['c_trung_thanh']['ty_le_cau_xau_%']}%")
    print(f"    CHỮ NGUỒN SAI (máy nghe nhầm): {len(nguon_sai)}/{len(diem)} = "
          f"{ket['d_chu_nguon']['ty_le_%']}%")

    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
