"""Đọc `_kq_quang_nghi.json` -> BẢNG TRẢ LỜI câu "quãng nghỉ IM hay CÓ NHẠC".

Chia mức trong quãng thành BA BẬC thay vì hai (một ngưỡng đơn thì mọi quãng
nằm giữa bị ép về một phía rồi báo cáo nói quá):
  · GẦN NỀN   : >= nền_p50 − 6 dB      -> nghe như phần còn lại của video
  · NHỎ HƠN   : nền−6 .. −45 dBFS      -> vơi đi nhưng VẪN NGHE ĐƯỢC
  · IM        : <= −45 dBFS            -> coi như không nghe được
(−45 = `thay_giong.SAN_LUFS_CHUAN_HOA`, ngưỡng app đã dùng để từ chối nâng độ
to một bản trộn "gần câm" — không đặt mò một số mới.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
SAN_IM = -45.0
GAN = 6.0


def main() -> int:
    d = json.loads((REPO / "_kq_quang_nghi.json").read_text(encoding="utf-8"))
    print("=" * 92)
    print("QUÃNG NGHỈ SAU KHI TẮT BÙ — ĐO TRÊN BẢN TRỘN CUỐI")
    print("=" * 92)
    tong = {"gan": [0, 0.0], "nho": [0, 0.0], "im": [0, 0.0]}
    for k, v in sorted(d.items()):
        if not v.get("ok"):
            print(f"\nVIDEO {k}: HỎNG — {v.get('loi')}")
            continue
        m, b = v["muc_ban_tron"], v["bu_goc_app_bao"]
        nen = m["nen_TB_p50_dBFS"]
        gan = [q for q in m["quang"] if q["db_SAU"] >= nen - GAN]
        im = [q for q in m["quang"] if q["db_SAU"] <= SAN_IM]
        nho = [q for q in m["quang"]
               if q not in gan and q not in im]
        for ten, ds in (("gan", gan), ("nho", nho), ("im", im)):
            tong[ten][0] += len(ds)
            tong[ten][1] += sum(x["dai"] for x in ds)
        lech = [q["db_TRUOC"] - q["db_SAU"] for q in m["quang"]]
        print(f"\n### VIDEO {k} — {v['video'][:44]}")
        print(f"  dài ra {v['dai_ra_s']} s · k hình {v['he_so_hinh']} · "
              f"chạy {v['giay_chay']} s")
        print(f"  ĐÃ BỎ {b.get('giay_bu')} s tiếng gốc ở {b.get('so_bu')} quãng"
              f"  ({100 * (b.get('giay_bu') or 0) / max(1e-9, v['dai_ra_s']):.2f}"
              f"% thời lượng)")
        print(f"  nền TB (p50) {nen:.2f} dBFS · mức lời (p90) "
              f"{m['muc_loi_p90_dBFS']:.2f} · sàn (p05) {m['san_p05_dBFS']:.2f}")
        print(f"  MỨC TRONG QUÃNG (arm SAU): TB {m['db_quang_TB']:.2f} · "
              f"thấp nhất {m['db_quang_thap_nhat']:.2f} dBFS "
              f"(thấp hơn nền {nen - m['db_quang_TB']:.2f} dB)")
        print(f"    GẦN NỀN (>= {nen - GAN:.1f}) : {len(gan):3d} quãng · "
              f"{sum(x['dai'] for x in gan):6.2f} s")
        print(f"    NHỎ HƠN NHƯNG NGHE ĐƯỢC   : {len(nho):3d} quãng · "
              f"{sum(x['dai'] for x in nho):6.2f} s")
        print(f"    IM (<= {SAN_IM:.0f} dBFS)        : {len(im):3d} quãng · "
              f"{sum(x['dai'] for x in im):6.2f} s")
        print(f"  quãng DÀI NHẤT {m['quang_dai_nhat_s']} s · "
              f"bù to hơn nền quãng TB {sum(lech)/max(1,len(lech)):.2f} dB")
        for n, a in (v.get("asr") or {}).items():
            print(f"  ASR {n:24s} nhãn={str(a.get('nhan_ngon_ngu')):<12s} "
                  f"Hán {a.get('so_ky_tu_HAN')}/{a.get('so_ky_tu')} "
                  f"= {100 * (a.get('ti_le_han') or 0):5.1f}%  "
                  f"({a.get('giay')} s)")
    print("\n" + "=" * 92)
    print(f"CỘNG CẢ {len([1 for v in d.values() if v.get('ok')])} VIDEO: "
          f"GẦN NỀN {tong['gan'][0]} quãng/{tong['gan'][1]:.2f} s · "
          f"NHỎ HƠN {tong['nho'][0]}/{tong['nho'][1]:.2f} s · "
          f"IM {tong['im'][0]}/{tong['im'][1]:.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
