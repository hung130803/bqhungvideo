# -*- coding: utf-8 -*-
"""A/B `_co_gian` GHÉP CẶP — cách CŨ và cách MỚI trên CÙNG MỘT FILE TIẾNG.

VÌ SAO PHẢI CÓ FILE NÀY (phép đo cũ không đủ nhạy):
`_do_piper_moc_that.py` so hai LƯỢT CHẠY KHÁC NHAU. Nhưng Piper là VITS, bộ dự
đoán độ dài của nó CÓ NHIỄU — đo được cùng một câu ra **2 hoặc 3 chỗ nghỉ**,
tổng nghỉ 269-359 ms tuỳ lượt. Tiếng khác nhau -> Groq chép ngược cũng khác ->
biến thiên giữa hai lượt NUỐT MẤT hiệu ứng của bản vá. Đó đúng bài học
"đo A/B phải đan xen" nhưng còn chặt hơn: ở đây ghép cặp được HOÀN TOÀN.

CÁCH ĐO — CÙNG TIẾNG, CÙNG THƯỚC, CHỈ KHÁC PHÉP TÍNH:
  1. Đọc Piper MỘT LẦN cho cả loạt câu (đúng cửa app: `piper_tts.doc_loat`).
  2. Rình `_co_gian` để lấy **mốc THÔ** + độ dài + khoảng có tiếng của chính
     lượt đó.
  3. Từ CÙNG mốc thô ấy dựng HAI bộ mốc:
        CŨ  = `_co_gian(thô, dài, None)`      -> rải đều, kể cả lên chỗ nghỉ
        MỚI = `_co_gian(thô, dài, khoảng)`    -> nhảy qua chỗ nghỉ
  4. Groq chép ngược **một lần** trên file tiếng đó -> so CẢ HAI với cùng sự
     thật, bằng `SequenceMatcher` như cổng 60/64.

Nhờ ghép cặp: nhiễu của Piper và nhiễu của Groq TRIỆT TIÊU, chênh lệch còn lại
là của riêng phép tính. Số ở đây KHÔNG so được với cột end-to-end của
`_do_piper_moc_that.py` (khác cách gộp) — chỉ dùng để trả lời đúng một câu:
**bản vá có giảm RUNG không.**

    .venv\\Scripts\\python -u _do_co_gian_ab.py
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SO_CAU = int(os.environ.get("BQ_SO_CAU", "14"))
SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))
RA = REPO / "_do_co_gian_ab.json"
_DAU = ".,!?;:\"'“”…()-–—[]{}"


def _chuan(w: str) -> str:
    return str(w or "").strip().strip(_DAU).lower()


def lech_mot_cau(moc: list, ws: list) -> list[float]:
    """ms lệch của từng từ khớp được. DƯƠNG = mốc MUỘN hơn tiếng."""
    def _w(x):
        if isinstance(x, dict):
            return (_chuan(x.get("word") or x.get("text")),
                    float(x.get("start", 0)))
        return (_chuan(x[2]), float(x[0]))

    that = [x for x in (_w(x) for x in ws) if x[0]]
    suy = [x for x in ((_chuan(m[2]), float(m[0])) for m in moc) if x[0]]
    if not suy or not that:
        return []
    sm = SequenceMatcher(None, [x[0] for x in suy], [x[0] for x in that],
                         autojunk=False)
    out = []
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            out.append((suy[a + k][1] - that[b + k][1]) * 1000.0)
    return out


def thong_ke(lech: list[float]) -> dict:
    if not lech:
        return {"n": 0}
    ab = sorted(abs(x) for x in lech)
    goc = statistics.median(lech)
    rung = sorted(abs(x - goc) for x in lech)
    return {
        "n": len(lech),
        "tb": round(sum(ab) / len(ab), 1),
        "trung_vi": round(statistics.median(ab), 1),
        "p90": round(ab[min(len(ab) - 1, int(len(ab) * 0.9))], 1),
        "lech_he_thong": round(goc, 1),
        "rung_tb": round(sum(rung) / len(rung), 1),
        "rung_trung_vi": round(statistics.median(rung), 1),
        "rung_p90": round(rung[min(len(rung) - 1, int(len(rung) * 0.9))], 1),
        "muon_hon_50": sum(1 for x in lech if x > 50),
        "rung_trong_50ms": sum(1 for x in lech if abs(x - goc) <= 50),
    }


def in_tk(ten: str, tk: dict) -> None:
    if not tk.get("n"):
        print(f"  {ten:<5}: KHÔNG đo được")
        return
    n = tk["n"]
    print(f"  {ten:<5}: {n} mốc · lệch |ms| TB {tk['tb']:6.1f} "
          f"· 90% {tk['p90']:6.1f}")
    print(f"         lệch HỆ THỐNG {tk['lech_he_thong']:+7.1f} ms  ·  RUNG "
          f"TB {tk['rung_tb']:6.1f} · trung vị {tk['rung_trung_vi']:6.1f} "
          f"· 90% {tk['rung_p90']:6.1f} ms")
    print(f"         hiện MUỘN hơn tiếng >50ms: {tk['muon_hon_50']}/{n} "
          f"({100.0 * tk['muon_hon_50'] / n:.0f}%)  ·  sau khi trừ lệch hệ "
          f"thống, trong ±50ms: {100.0 * tk['rung_trong_50ms'] / n:.0f}%")


def main() -> int:
    from app.core import piper_tts as PT
    from app.core import thay_giong as TG
    from _do_piper_moc_that import nap_cau

    texts = nap_cau()
    print("=" * 74)
    print(f"A/B `_co_gian` GHÉP CẶP — {len(texts)} câu · {SO_LUOT} lượt · "
          "CÙNG file tiếng, CÙNG thước Groq")
    print("=" * 74)

    goc_fn = PT._co_gian
    gom: dict[str, list[float]] = {"CŨ": [], "MỚI": []}
    tat_ca = []
    im_tong = tieng_tong = 0.0
    so_nghi = 0

    for luot in range(SO_LUOT):
        san = REPO / f"bq_abcg_{os.getpid()}_{luot}"
        san.mkdir(parents=True, exist_ok=True)
        bat: list[tuple] = []

        def rinh(moc, dai_that, khoang=None, _b=bat):
            ra = goc_fn(moc, dai_that, khoang)
            _b.append(([list(x) for x in moc], dai_that, khoang, ra))
            return ra

        PT._co_gian = rinh
        try:
            paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
            ok, moc_moi = PT.doc_loat(texts, paths)
        finally:
            PT._co_gian = goc_fn

        # ĐỐI SOÁT: rình phải bắt được ĐÚNG số câu có mốc, nếu không thì
        # mọi số dưới là số của một đường khác đường app chạy.
        co_moc = [i for i in range(len(texts)) if moc_moi[i]]
        if len(bat) != len(co_moc):
            print(f"  LƯỢT {luot + 1}: rình bắt {len(bat)} câu nhưng có "
                  f"{len(co_moc)} câu ra mốc -> BỎ LƯỢT, không kết luận")
            shutil.rmtree(san, ignore_errors=True)
            continue

        mot = {"cau": []}
        for k, i in enumerate(co_moc):
            tho, dai, khoang, ra_moi = bat[k]
            if ra_moi != moc_moi[i]:
                print(f"  câu {i}: mốc rình được KHÁC mốc app trả -> BỎ CÂU")
                continue
            ra_cu = goc_fn(tho, dai, None)
            im = dai - sum(e - s for s, e in (khoang or [(0.0, dai)]))
            im_tong += im
            tieng_tong += dai
            so_nghi += max(0, len(khoang or []) - 1)
            try:
                d = TG.chep_loi(paths[i])
            except Exception as e:                       # noqa: BLE001
                print(f"  câu {i}: Groq hỏng ({type(e).__name__}) -> bỏ")
                continue
            ws = d.get("words") or []
            if not ws:
                continue
            l_cu = lech_mot_cau(ra_cu, ws)
            l_moi = lech_mot_cau(ra_moi, ws)
            # CHỈ nhận câu mà CẢ HAI cùng khớp được đúng số mốc — khác số mốc
            # là so hai tập từ khác nhau, số ra vô nghĩa.
            if not l_cu or len(l_cu) != len(l_moi):
                continue
            gom["CŨ"].extend(l_cu)
            gom["MỚI"].extend(l_moi)
            mot["cau"].append({"i": i, "im": round(im, 3),
                               "n": len(l_cu),
                               "cu": [round(x, 1) for x in l_cu],
                               "moi": [round(x, 1) for x in l_moi]})
        tat_ca.append(mot)
        shutil.rmtree(san, ignore_errors=True)
        print(f"  LƯỢT {luot + 1}: gom được {len(mot['cau'])} câu "
              f"· tổng {sum(c['n'] for c in mot['cau'])} mốc")
        RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    print()
    print("=" * 74)
    print(f"TỔNG KẾT — GHÉP CẶP trên cùng tiếng ({len(gom['CŨ'])} mốc mỗi bên)")
    print(f"chỗ nghỉ đo được trong corpus: {so_nghi} chỗ · tổng im "
          f"{im_tong:.2f}s / {tieng_tong:.2f}s tiếng "
          f"= {100 * im_tong / max(tieng_tong, 1e-9):.1f}%")
    print("=" * 74)
    for a in ("CŨ", "MỚI"):
        in_tk(a, thong_ke(gom[a]))
    tc, tm = thong_ke(gom["CŨ"]), thong_ke(gom["MỚI"])
    if tc.get("n") and tm.get("n"):
        # KHÁC BIỆT GHÉP CẶP: từng mốc một, không so hai cột trung bình
        d = [abs(b) - abs(a) for a, b in zip(gom["CŨ"], gom["MỚI"])]
        tot = sum(1 for x in d if x < -1)
        te = sum(1 for x in d if x > 1)
        print()
        print(f"  RUNG   : {tc['rung_tb']:.1f} -> {tm['rung_tb']:.1f} ms "
              f"({tm['rung_tb'] - tc['rung_tb']:+.1f})")
        print(f"  HỆ THỐNG: {tc['lech_he_thong']:+.1f} -> "
              f"{tm['lech_he_thong']:+.1f} ms")
        print(f"  ghép cặp từng mốc: {tot} mốc TỐT LÊN · {te} mốc TỆ ĐI "
              f"· {len(d) - tot - te} như cũ")
    RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
