"""ĐO GHÉP CẶP: `infer(ref_audio=)` MỖI CÂU vs ENROL MỘT LẦN rồi `infer(voice=)`.

CHẠY BẰNG PYTHON CỦA VENV VieNeu (không phải `.venv` của app).

═══ VÌ SAO ĐO CÁI NÀY ═══
Đo trên lượt chạy THẬT của anh Hùng (`_do_vn_that.py`): **27,4 giây/câu · 141
câu/video** -> một lượt đọc là **64 PHÚT**, và **93% chi phí mỗi câu là PHÍ CỐ
ĐỊNH** (câu 23 ký tự tốn 25,5s, câu 52 ký tự tốn 26,9s — gấp đôi chữ chỉ thêm
1,4s). Tức giá nằm ở **LƯỢT GỌI**, không ở độ dài chữ.

Đọc mã `vieneu/v3turbo.py` ra đúng chỗ: `infer(ref_audio=...)` gọi
`_resolve_ref` -> `_preclean_reference_audio` (librosa trim, ghi file tạm) +
`engine.prepare_reference` (**mã hoá NeuCodec cả mẫu 10 giây**) — **LẶP LẠI CHO
TỪNG CÂU**. Gói CÓ SẴN đường làm một lần: `add_voice(name, ref_audio)` cất
`speaker_emb` + `codes` vào `_preset_voices`, rồi `infer(voice=name)` dùng lại.

═══ KHÔNG ĐỔI CHẤT LƯỢNG — VÌ SAO ═══
`add_voice` chạy **ĐÚNG HAI dòng** mà `_resolve_ref` chạy, cùng tham số
(`denoise=True`, `use_ref_codes=True`), rồi cất kết quả. `speaker_emb` và
`ref_codes` đưa vào model là **CÙNG MỘT MẢNG SỐ**. Cái đổi là số LẦN tính nó.
(Tiếng ra vẫn không giống từng byte vì `infer` lấy mẫu ngẫu nhiên —
`temperature=0.8 · top_k=25 · top_p=0.95` — nhưng đó là bản chất của model,
đúng cái đã đo được là 3,1% vs 12,7% WER trên CÙNG bản mã.)

═══ ĐAN XEN, KHÔNG ĐO LIỀN MẠCH ═══
Máy này LUÔN có việc nền (lúc đo: app anh Hùng đang chạy 2 tiến trình VieNeu).
Đo liền mạch đã ra kết luận NGƯỢC 3 lần trong repo, nên hai arm chạy **XEN KẼ
TỪNG CÂU** và đảo thứ tự theo câu chẵn/lẻ.

MẪU LÀ GIỌNG MÁY (edge-tts) — luật repo cấm `adam_clone.wav`.
"""
from __future__ import annotations

import json
import os
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HOP = Path(__file__).resolve().parent / "_kq_cham_tg"
KQ = Path(__file__).resolve().parent / "_kq_vn_refcache.json"

#: Câu THẬT lấy từ lượt chạy của anh Hùng (bản dịch tiếng Anh của video
#: Douyin) — không bịa câu thử, để độ dài chữ đúng phân bố thật (TB ~39 ký tự).
CAU = [
    "Just how mind-blowing can a death-prediction app be?",
    "I've never seen a movie that made me pee from start to finish.",
    "The latest horror film, personally crafted by Annabelle.",
    "Watch this and your whole perception will be turned upside down.",
    "He opened the door and everything went completely silent.",
    "By morning the entire town had already heard the news.",
]


def main() -> int:
    mau = HOP / "mau_may.wav"
    if not mau.is_file():
        print(f"THIẾU MẪU {mau} — chạy `_do_cham_smoke.py` trước.")
        return 2
    ra = HOP / "refcache"
    ra.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import soundfile as sf
    from vieneu import Vieneu

    t0 = time.time()
    tts = Vieneu()
    nap = time.time() - t0
    print(f"nạp model: {nap:.1f}s", flush=True)

    # --- ENROL MỘT LẦN (arm MỚI trả giá này ĐÚNG MỘT LẦN cho cả video) ---
    t0 = time.time()
    tts.add_voice("_bq_clone", str(mau))
    enrol = time.time() - t0
    print(f"enrol (add_voice) MỘT LẦN: {enrol:.1f}s", flush=True)

    cu: list[float] = []
    moi: list[float] = []
    chi_tiet = []
    for k, c in enumerate(CAU):
        # ĐẢO THỨ TỰ theo câu chẵn/lẻ — arm chạy sau không phải lúc nào cũng
        # gánh phần máy vừa nóng lên.
        thu_tu = ["cu", "moi"] if k % 2 == 0 else ["moi", "cu"]
        d = {"i": k, "ky_tu": len(c), "thu_tu": "/".join(thu_tu)}
        for arm in thu_tu:
            t = time.time()
            if arm == "cu":
                w = tts.infer(text=c, ref_audio=str(mau), apply_watermark=True)
            else:
                w = tts.infer(text=c, voice="_bq_clone", apply_watermark=True)
            g = time.time() - t
            w = np.asarray(w, dtype="float32").reshape(-1)
            sf.write(str(ra / f"{arm}_{k}.wav"), w, int(tts.sample_rate))
            d[arm] = round(g, 2)
            d[f"{arm}_giay_tieng"] = round(len(w) / float(tts.sample_rate), 2)
            (cu if arm == "cu" else moi).append(g)
            print(f"  câu {k} [{arm:>3}] {g:6.1f}s  "
                  f"(tiếng {d[f'{arm}_giay_tieng']:.1f}s)", flush=True)
        chi_tiet.append(d)

    tb_cu, tb_moi = st.mean(cu), st.mean(moi)
    # Với 141 câu/video và 3 lượt đọc, ước cả video (ước THẬN TRỌNG: chỉ tính
    # lượt đọc 4a, hai lượt kia đọc lại một phần).
    N = 141
    d = {
        "mau": str(mau), "so_cau": len(CAU),
        "nap_model_s": round(nap, 2),
        "enrol_mot_lan_s": round(enrol, 2),
        "CU_giay_moi_cau_TB": round(tb_cu, 2),
        "CU_trung_vi": round(st.median(cu), 2),
        "MOI_giay_moi_cau_TB": round(tb_moi, 2),
        "MOI_trung_vi": round(st.median(moi), 2),
        "nhanh_gap": round(tb_cu / max(1e-9, tb_moi), 2),
        "bot_giay_moi_cau": round(tb_cu - tb_moi, 2),
        "ghep_cap_MOI_nhanh_hon": sum(1 for x in chi_tiet
                                      if x["moi"] < x["cu"]),
        "ghep_cap_tong": len(chi_tiet),
        "uoc_1_luot_doc_141_cau_phut_CU": round(N * tb_cu / 60, 1),
        "uoc_1_luot_doc_141_cau_phut_MOI": round(
            (enrol + N * tb_moi) / 60, 1),
        "chi_tiet": chi_tiet,
    }
    print("\n" + "=" * 66)
    print(f"CŨ  (ref_audio mỗi câu): {tb_cu:6.1f} s/câu")
    print(f"MỚI (enrol một lần)   : {tb_moi:6.1f} s/câu   "
          f"-> NHANH GẤP {d['nhanh_gap']}")
    print(f"ghép cặp: MỚI nhanh hơn {d['ghep_cap_MOI_nhanh_hon']}"
          f"/{len(chi_tiet)} câu")
    print(f"ước 1 lượt đọc 141 câu: {d['uoc_1_luot_doc_141_cau_phut_CU']} phút"
          f" -> {d['uoc_1_luot_doc_141_cau_phut_MOI']} phút")
    print("=" * 66)
    KQ.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"Ghi: {KQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
