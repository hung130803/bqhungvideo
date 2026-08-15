# -*- coding: utf-8 -*-
"""LỖI 1 — CHỮ PHẢI HIỆN THEO LỜI NÓI. Chọn TRẦN KÝ TỰ bằng số đo, rồi đo
LỆCH CHỮ-TIẾNG bằng một nguồn ĐỘC LẬP (Groq STT trên chính file giọng).

Ba việc, ba bảng:

  A. TRƯỚC/SAU — bản cũ trả ĐÚNG 1 dòng/câu (khối 3 dòng anh Hùng chụp ảnh),
     bản mới cắt thành cụm. Đo: số ký tự trên màn hình mỗi lần, thời lượng
     mỗi lần hiện.
  B. CHỌN TRẦN — quét nhiều mức trần, xem mức nào vừa KHÔNG còn khối dài,
     vừa không đẻ ra cụm chớp nhoáng.
  C. LỆCH CHỮ-TIẾNG (mili-giây) — KHÔNG tự chấm bằng chính WordBoundary (đó
     là hỏi bị cáo có tội không). Chép lại file GIỌNG bằng Groq lấy mốc từng
     từ THẬT rồi so với mốc chữ hiện.

BẪY: stdout utf-8 · mọi subprocess có timeout · không đụng file gốc.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))


def _thong_ke(cues: list) -> dict:
    if not cues:
        return {"n": 0}
    kt = [len(c[2]) for c in cues]
    dt = [round(c[1] - c[0], 3) for c in cues]
    kt_s, dt_s = sorted(kt), sorted(dt)
    return {
        "n": len(cues),
        "ky_tu_tb": round(sum(kt) / len(kt), 1),
        "ky_tu_trung_vi": kt_s[len(kt_s) // 2],
        "ky_tu_max": max(kt),
        "so_lan_qua_60kt": sum(1 for x in kt if x > 60),
        "giay_tb": round(sum(dt) / len(dt), 2),
        "giay_trung_vi": dt_s[len(dt_s) // 2],
        "giay_max": round(max(dt), 2),
        "so_lan_duoi_04s": sum(1 for x in dt if x < 0.4),
        "so_lan_tren_4s": sum(1 for x in dt if x > 4.0),
    }


def _in(nhan: str, tk: dict) -> None:
    print(f"  {nhan:26} n={tk.get('n', 0):4}  "
          f"ký tự TB {tk.get('ky_tu_tb', 0):5}  "
          f"max {tk.get('ky_tu_max', 0):4}  "
          f">60kt {tk.get('so_lan_qua_60kt', 0):3}  |  "
          f"giây TB {tk.get('giay_tb', 0):5}  max {tk.get('giay_max', 0):5}  "
          f"<0,4s {tk.get('so_lan_duoi_04s', 0):3}  "
          f">4s {tk.get('so_lan_tren_4s', 0):3}")


def bang_ab(kq: dict) -> list:
    from app.core import thay_giong as tg

    moc_tieng = (kq.get("khop") or {}).get("moc_tieng") or []
    moc_tu = (kq.get("khop") or {}).get("moc_tu") or []
    texts = kq.get("loi_cuoi") or []
    if not moc_tieng or not texts:
        print("THIẾU moc_tieng/loi_cuoi trong _kq.json")
        return []

    print(f"\n== A. TRƯỚC / SAU ==  ({len(moc_tieng)} câu, "
          f"{len(moc_tu)} câu có mốc từng-từ)")
    # BẢN CŨ: đúng 1 dòng/câu — dựng lại đúng công thức cũ để so cho sòng
    # phẳng (không đọc số cũ chép tay).
    cu = []
    n = len(moc_tieng)
    for k, (i, a, b) in enumerate(moc_tieng):
        t = str(texts[i]).strip() if 0 <= i < len(texts) else ""
        if not t:
            continue
        b = max(float(b), float(a) + tg.CHU_TOI_THIEU_S)
        if k + 1 < n:
            b = min(b, float(moc_tieng[k + 1][1]) - tg.CHU_CHUA_TRUOC_S)
        if b <= a:
            b = float(a) + 0.20
        cu.append((float(a), b, t))
    _in("CŨ (1 dòng / câu)", _thong_ke(cu))
    moi = tg.dong_chu_theo_giong(moc_tieng, texts, moc_tu=moc_tu)
    _in(f"MỚI (trần {tg.TRAN_KY_TU_CUM} ký tự)", _thong_ke(moi))

    print("\n== B. CHỌN TRẦN KÝ TỰ ==")
    for tran in (18, 22, 26, 30, 36, 42, 55):
        _in(f"trần {tran}",
            _thong_ke(tg.dong_chu_theo_giong(moc_tieng, texts,
                                             moc_tu=moc_tu, tran=tran)))
    return moi


def bang_lech(kq: dict, cues: list, giong_wav: Path) -> None:
    """C. LỆCH CHỮ-TIẾNG — nguồn đối chứng ĐỘC LẬP: Groq chép lại file giọng."""
    from app.core import thay_giong as tg

    if not giong_wav.exists():
        print(f"\n== C. LỆCH CHỮ-TIẾNG == THIẾU {giong_wav.name} -> bỏ qua")
        return
    print(f"\n== C. LỆCH CHỮ-TIẾNG (đối chứng: Groq chép lại "
          f"{giong_wav.name}) ==")
    d = tg.chep_loi(giong_wav)
    words = d.get("words") or []
    print(f"  Groq trả {len(words)} mốc từ · ngôn ngữ {d.get('language')}")
    if not words:
        print("  KHÔNG có mốc từ -> không đo được, ghi thẳng chứ không bịa.")
        return

    def _w(x):
        if isinstance(x, dict):
            return (str(x.get("word") or x.get("text") or "").strip(),
                    float(x.get("start", 0)), float(x.get("end", 0)))
        return (str(x[2]).strip(), float(x[0]), float(x[1]))

    ws = [_w(x) for x in words]
    lech: list[float] = []
    khong_khop = 0
    j = 0
    for ca, _cb, cs in cues:
        dau = (cs.split() or [""])[0].strip(".,!?;:\"'“”…").lower()
        if not dau:
            continue
        # tìm TIẾN từ vị trí hiện tại — cụm đi theo thứ tự thời gian
        k = -1
        for m in range(j, len(ws)):
            if ws[m][0].strip(".,!?;:\"'“”….").lower() == dau:
                k = m
                break
        if k < 0:
            khong_khop += 1
            continue
        lech.append((ca - ws[k][1]) * 1000.0)
        j = k + 1
    if not lech:
        print(f"  không khớp được cụm nào ({khong_khop} cụm) -> không kết luận")
        return
    ab = sorted(abs(x) for x in lech)
    print(f"  khớp {len(lech)}/{len(cues)} cụm (bỏ {khong_khop} cụm không "
          "khớp được từ đầu)")
    print(f"  LỆCH tuyệt đối: TB {sum(ab) / len(ab):7.1f} ms · "
          f"trung vị {ab[len(ab) // 2]:7.1f} ms · "
          f"90% {ab[int(len(ab) * 0.9)]:7.1f} ms · max {ab[-1]:7.1f} ms")
    print(f"  chữ hiện SỚM hơn tiếng: {sum(1 for x in lech if x < -50)} cụm · "
          f"MUỘN hơn: {sum(1 for x in lech if x > 50)} cụm · "
          f"trong ±50 ms: {sum(1 for x in lech if abs(x) <= 50)} cụm")


def main() -> int:
    p = Path(sys.argv[1] if len(sys.argv) > 1
             else REPO / "_do_lt" / "e2e" / "_kq.json")
    if not p.exists():
        print(f"THIẾU {p}")
        return 2
    kq = json.loads(p.read_text(encoding="utf-8"))
    cues = bang_ab(kq)
    bang_lech(kq, cues, p.parent / "tieng_moi.giong.wav")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
