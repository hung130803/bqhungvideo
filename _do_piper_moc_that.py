# -*- coding: utf-8 -*-
"""ĐỘ CHÍNH XÁC MỐC TỪNG CHỮ CỦA PIPER — đo bằng ĐÚNG cách cổng 60 đã đo
edge-tts: **cho Groq chép ngược CHÍNH file tiếng vừa đọc** rồi so mốc từ.

VÌ SAO PHẢI CÓ FILE NÀY (lỗ hổng lớn nhất của Piper):
  · edge-tts **TRẢ VỀ** mốc từng chữ (`WordBoundary` của dịch vụ) -> cổng 60
    đo được lệch trung bình mấy chục mili-giây so với tiếng thật.
  · Piper **KHÔNG có** cờ xuất mốc ở CLI, nên `piper_tts` phải **SUY RA**: đọc
    rời từng chữ, lấy độ dài WAV, rồi co giãn về độ dài câu thật.
  · Cổng 64 chứng minh được mốc đó **đúng thứ tự · đúng số từ · tổng lệch
    <= 0,3 ms**, nhưng **CHƯA có một con số lệch mili-giây nào so với THỰC
    TẾ**. "Đúng tổng" mà sai chỗ chia thì chữ vẫn chạy sai — đúng loại phép đo
    tự phát chứng nhận mà repo này đang chống.

CÁCH ĐO — HAI ARM ĐI CHUNG MỘT CỬA, ĐAN XEN:
  Cả hai arm gọi CHÍNH `dubbing._synth_all_words` (cửa DUY NHẤT của app, cổng
  64 đã chốt), chỉ khác chuỗi `voice`. Không dựng đường riêng cho phép đo —
  đường riêng là đo một thứ người dùng không bao giờ chạy.
     · `EDGE`  — `vi-VN-NamMinhNeural`            (mốc THẬT do dịch vụ trả)
     · `PIPER` — `piper:vi_VN-vais1000-medium`    (mốc SUY RA)

  Với MỖI câu: đọc ra WAV -> Groq chép ngược CHÍNH file WAV đó -> căn hai
  chuỗi từ bằng `SequenceMatcher` -> so mốc BẮT ĐẦU của từng từ khớp được.

DẤU CỦA `lệch` (giữ đúng quy ước `_do_cum_chu.py`):
  **DƯƠNG = mốc MUỘN hơn tiếng** (chữ hiện sau khi đã nói) · ÂM = sớm hơn.
  Chữ hiện muộn khó chịu hơn hẳn hiện sớm, nên phải đếm riêng.

BẪY ĐÃ CANH:
  · Groq chép ngược **đếm sai từ** là chuyện thường -> căn bằng
    `SequenceMatcher` rồi CHỈ so từ khớp được, và **in ra tỉ lệ khớp**. Tỉ lệ
    khớp thấp thì con số lệch không đáng tin, phải nói ra chứ không giấu.
  · Câu Groq không trả `words` -> BỎ, đếm riêng, không bịa 0,0.
  · Mọi thứ chạy trong hộp cát tự dọn; KHÔNG đụng file của anh Hùng.

  .venv\\Scripts\\python -u _do_piper_moc_that.py
  BQ_SO_CAU=8 BQ_LUOT=1 .venv\\Scripts\\python -u _do_piper_moc_that.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                    # noqa: BLE001
        pass

SO_CAU = int(os.environ.get("BQ_SO_CAU", "14"))
SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))
RA = REPO / "_do_piper_moc_that.json"

GIONG = {
    "EDGE": "vi-VN-NamMinhNeural",
    "PIPER": "piper:" + "vi_VN-vais1000-medium",
}
ARM = ["EDGE", "PIPER"]


# --------------------------------------------------------------------------
def nap_cau() -> list[str]:
    """Câu TIẾNG VIỆT THẬT — bản dịch của chính video anh Hùng.

    Lấy từ kết quả đo đường dịch (`_do_dich_soat.json`) chứ không bịa câu mẫu:
    câu mẫu ngắn/sạch làm phép đo đẹp giả tạo.
    """
    p = REPO / "_do_dich_soat.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for luot in d:
        for ten in ("MỐC", "SOÁT"):
            bd = (luot.get(ten) or {}).get("ban_dich") or []
            if bd:
                # câu DÀI mới có đủ từ để so mốc; câu 2-3 từ không nói lên gì
                cau = sorted({t.strip() for t in bd if t and t.strip()},
                             key=lambda t: -len(t.split()))
                return [t for t in cau if len(t.split()) >= 6][:SO_CAU]
    raise SystemExit("KHÔNG lấy được câu từ _do_dich_soat.json")


def doc_mot_arm(ten: str, texts: list[str], san: Path) -> tuple[list, list]:
    """Gọi CHÍNH cửa của app. Trả (ok, words) + ghi WAV vào `san`."""
    from app.core import dubbing
    san.mkdir(parents=True, exist_ok=True)
    paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
    ok, words = asyncio.run(
        dubbing._synth_all_words(texts, GIONG[ten], paths))
    return list(zip(ok, paths)), words


_DAU = ".,!?;:\"'“”…()-–—[]{}"


def _chuan(w: str) -> str:
    return str(w or "").strip().strip(_DAU).lower()


def so_mot_cau(moc_suy: list, wav: str) -> dict:
    """So mốc app tính ra với mốc Groq đọc được TRÊN CHÍNH FILE ĐÓ."""
    from app.core import thay_giong as tg

    d = tg.chep_loi(wav)
    ws = d.get("words") or []
    if not ws:
        return {"bo": "Groq không trả mốc từ"}

    def _w(x):
        if isinstance(x, dict):
            return (_chuan(x.get("word") or x.get("text")),
                    float(x.get("start", 0)))
        return (_chuan(x[2]), float(x[0]))

    that = [_w(x) for x in ws]
    suy = [(_chuan(m[2]), float(m[0])) for m in moc_suy]
    suy = [x for x in suy if x[0]]
    that = [x for x in that if x[0]]
    if not suy or not that:
        return {"bo": "một bên rỗng"}

    sm = SequenceMatcher(None, [x[0] for x in suy], [x[0] for x in that],
                         autojunk=False)
    lech: list[float] = []
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            lech.append((suy[a + k][1] - that[b + k][1]) * 1000.0)
    return {"lech": lech, "n_suy": len(suy), "n_that": len(that)}


def thong_ke(lech: list[float]) -> dict:
    if not lech:
        return {"n": 0}
    ab = sorted(abs(x) for x in lech)
    #: TÁCH LỆCH HỆ THỐNG KHỎI RUNG — hai thứ này chữa bằng hai cách KHÁC HẲN.
    #: Lệch HỆ THỐNG (cả loạt cùng muộn/sớm một lượng) chỉ cần TRỪ MỘT HẰNG SỐ.
    #: RUNG (mỗi chữ lệch một kiểu) thì KHÔNG có cách nào chữa bằng hằng số —
    #: đó mới là chất lượng thật của bộ mốc. Trộn hai cái vào một con số "TB"
    #: là đọc nhầm một lỗi dễ chữa thành một lỗi không chữa được.
    goc = statistics.median(lech)
    rung = sorted(abs(x - goc) for x in lech)
    return {
        "n": len(lech),
        "tb": round(sum(ab) / len(ab), 1),
        "trung_vi": round(statistics.median(ab), 1),
        "p90": round(ab[min(len(ab) - 1, int(len(ab) * 0.9))], 1),
        "max": round(ab[-1], 1),
        "trong_50ms": sum(1 for x in lech if abs(x) <= 50),
        "muon_hon_50": sum(1 for x in lech if x > 50),
        "som_hon_50": sum(1 for x in lech if x < -50),
        "lech_co_dau_tb": round(sum(lech) / len(lech), 1),
        "lech_he_thong": round(goc, 1),
        "rung_tb": round(sum(rung) / len(rung), 1),
        "rung_trung_vi": round(statistics.median(rung), 1),
        "rung_p90": round(rung[min(len(rung) - 1, int(len(rung) * 0.9))], 1),
        "rung_trong_50ms": sum(1 for x in lech if abs(x - goc) <= 50),
    }


def in_tk(ten: str, tk: dict, bo: int, tong_tu: int) -> None:
    if not tk.get("n"):
        print(f"  {ten:<6}: KHÔNG đo được mốc nào")
        return
    n = tk["n"]
    print(f"  {ten:<6}: khớp {n}/{tong_tu} từ  ({100.0 * n / max(1, tong_tu):.0f}%)"
          f"  · bỏ {bo} câu")
    print(f"          lệch |ms|  TB {tk['tb']:6.1f} · trung vị {tk['trung_vi']:6.1f}"
          f" · 90% {tk['p90']:6.1f} · max {tk['max']:6.1f}")
    print(f"          trong ±50 ms: {tk['trong_50ms']}/{n} "
          f"({100.0 * tk['trong_50ms'] / n:.0f}%)"
          f"  · MUỘN hơn tiếng >50ms: {tk['muon_hon_50']}"
          f"  · sớm >50ms: {tk['som_hon_50']}")
    print(f"          lệch CÓ DẤU TB {tk['lech_co_dau_tb']:+.1f} ms "
          f"(dương = mốc muộn hơn tiếng)")
    print(f"          TÁCH RA: lệch HỆ THỐNG {tk['lech_he_thong']:+.1f} ms "
          f"(trừ được bằng 1 hằng số)  ·  RUNG còn lại "
          f"TB {tk['rung_tb']:.1f} · trung vị {tk['rung_trung_vi']:.1f} · "
          f"90% {tk['rung_p90']:.1f} ms")
    print(f"          sau khi trừ lệch hệ thống, trong ±50 ms: "
          f"{tk['rung_trong_50ms']}/{n} "
          f"({100.0 * tk['rung_trong_50ms'] / n:.0f}%)")


def main() -> int:
    for p in REPO.glob("bq_pipermoc_*"):
        shutil.rmtree(p, ignore_errors=True)
    texts = nap_cau()
    tong_tu = sum(len(t.split()) for t in texts)
    print("=" * 74)
    print(f"MỐC TỪNG CHỮ — ĐỐI CHỨNG BẰNG GROQ CHÉP NGƯỢC  ·  {len(texts)} câu "
          f"· ~{tong_tu} từ · {SO_LUOT} lượt ĐAN XEN")
    print("Cửa gọi: dubbing._synth_all_words (ĐÚNG cửa app dùng)")
    print("=" * 74)
    for i, t in enumerate(texts[:3]):
        print(f"  ví dụ câu {i}: {t[:70]}")

    gom: dict[str, list[float]] = {a: [] for a in ARM}
    gom_bo: dict[str, int] = {a: 0 for a in ARM}
    gom_tu: dict[str, int] = {a: 0 for a in ARM}
    tat_ca = []

    for luot in range(SO_LUOT):
        thu_tu = ARM[luot % len(ARM):] + ARM[:luot % len(ARM)]
        print()
        print("=" * 74)
        print(f"LƯỢT {luot + 1}  (thứ tự: {' -> '.join(thu_tu)})")
        print("=" * 74)
        mot = {}
        for ten in thu_tu:
            san = REPO / f"bq_pipermoc_{os.getpid()}_{luot}_{ten.lower()}"
            try:
                t0 = time.time()
                okp, words = doc_mot_arm(ten, texts, san)
                giay = round(time.time() - t0, 1)
                lech: list[float] = []
                bo = 0
                co_moc = 0
                for i, (ok, wav) in enumerate(okp):
                    if not ok or not Path(wav).exists():
                        bo += 1
                        continue
                    if not words[i]:
                        bo += 1
                        continue
                    co_moc += 1
                    r = so_mot_cau(words[i], wav)
                    if "lech" in r:
                        lech.extend(r["lech"])
                    else:
                        bo += 1
                tk = thong_ke(lech)
                print(f"  [{ten}] đọc {giay}s · {co_moc}/{len(texts)} câu CÓ mốc")
                in_tk(ten, tk, bo, tong_tu)
                gom[ten].extend(lech)
                gom_bo[ten] += bo
                gom_tu[ten] += tong_tu
                # GIỮ SỐ THÔ: bảng tổng kết che mất phân bố, và không có số
                # thô thì lượt sau muốn tính lại kiểu khác là phải đọc lại
                # Groq từ đầu.
                mot[ten] = {"tk": tk, "giay": giay, "bo": bo,
                            "co_moc": co_moc,
                            "lech_tho": [round(x, 1) for x in lech]}
            except Exception as e:                       # noqa: BLE001
                print(f"  [{ten}] LỖI: {type(e).__name__}: {e}")
                mot[ten] = {"loi": f"{type(e).__name__}: {e}"}
            finally:
                shutil.rmtree(san, ignore_errors=True)
        tat_ca.append(mot)
        RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    print()
    print("=" * 74)
    print(f"TỔNG KẾT — gộp {SO_LUOT} lượt")
    print("=" * 74)
    for a in ARM:
        in_tk(a, thong_ke(gom[a]), gom_bo[a], gom_tu[a])
    te = thong_ke(gom["EDGE"])
    tp = thong_ke(gom["PIPER"])
    if te.get("n") and tp.get("n"):
        print()
        print(f"  PIPER so với EDGE: TB {tp['tb']:.1f} vs {te['tb']:.1f} ms "
              f"= {tp['tb'] / max(0.1, te['tb']):.2f}x"
              f"  ·  trong ±50ms {100.0 * tp['trong_50ms'] / tp['n']:.0f}% vs "
              f"{100.0 * te['trong_50ms'] / te['n']:.0f}%")
    RA.write_text(json.dumps(tat_ca, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {RA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
