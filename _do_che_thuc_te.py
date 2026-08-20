"""ĐO TRÊN CHÍNH FILE APP ĐÃ XUẤT CHO ANH HÙNG (`Downloads\\longtieng\\xuất`).

Bằng chứng mạnh nhất có được: không dựng lại kịch bản, đo thẳng cái anh Hùng
đang nhìn.

**HAI CÁI BẪY CỦA PHÉP ĐO NÀY — BẢN ĐẦU CỦA TÔI SẬP CẢ HAI:**
(1) **BẢN XUẤT DÀI HƠN BẢN GỐC** (đo: 148,61 -> 178,14 s = **k 1,1987**) vì
    chế độ "Chỉnh video theo giọng" làm CHẬM hình bằng `-itsscale`. Vì vậy
    khung ở giây T của bản xuất là nội dung giây **T/k** của bản gốc — so
    "gốc tại T" với "xuất tại T" là so HAI CẢNH KHÁC NHAU.
(2) **PHẢI LẤY MỐC THEO ĐỘ DÀI BẢN XUẤT**, không phải bản gốc. Lấy theo bản
    gốc thì mốc 99% chỉ tới giây 147/178 — **bỏ trắng đúng cái đuôi 29,5 giây
    mà anh Hùng đang kêu**.

CHỈ ĐỌC hai thư mục nguồn. Ghi ra `_kq_che_cuoi/`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

KHO = Path(r"C:\Users\Admin\Downloads\longtieng")
XUAT = KHO / "xuất"
RA = Path(__file__).resolve().parent / "_kq_che_cuoi"
#: Mốc theo % ĐỘ DÀI BẢN XUẤT. Dày ở đuôi.
MOC_TY = (0.05, 0.15, 0.30, 0.45, 0.60, 0.70, 0.78, 0.82, 0.84, 0.86,
          0.90, 0.94, 0.97, 0.99)
#: Mốc trích PNG cho người tự nhìn (ít file, chọn 2 bên bờ vực).
MOC_ANH = (0.30, 0.60, 0.80, 0.86, 0.94, 0.99)


def main() -> int:
    from app.core import che_chu as CC
    RA.mkdir(exist_ok=True)
    bang = []
    for i_v, goc in enumerate(sorted(KHO.glob("*.mp4")), 1):
        ra_f = XUAT / goc.name
        if not ra_f.is_file():
            print(f"BỎ (chưa xuất): {goc.name[:40]}")
            continue
        tg, tr = CC.thong_tin(goc), CC.thong_tin(ra_f)
        dg, dr = float(tg["do_dai"] or 0), float(tr["do_dai"] or 0)
        k = dr / max(1e-9, dg)
        d = CC.dai_theo_video(goc)
        print("\n" + "=" * 78)
        print(f"V{i_v}. {goc.name[:56]}")
        print(f"  gốc {tg['rong']}x{tg['cao']} {dg:.2f}s -> xuất {dr:.2f}s "
              f"= **k {k:.4f}** (chậm hình {(k-1)*100:.1f}%)")
        print(f"  dải: co_chu={d.co_chu} y={d.y0}..{d.y1} "
              f"x_dải={d.x0_dai}..{d.x1_dai} · {len(d.hop or [])} mốc hộp")
        print(f"  ĐUÔI KHÔNG CÓ MỆNH ĐỀ enable NÀO PHỦ: T = {dg:.1f}..{dr:.1f}s"
              f" = {(1-1/k)*100:.1f}% cuối clip")
        if not d.co_chu:
            continue
        ty = (tr["cao"] or 1) / max(1, tg["cao"])
        y0, y1 = int(d.y0 * ty), int(d.y1 * ty)
        xa = int((d.x0_dai or d.x0) * ty)
        xb = int((d.x1_dai or d.x1) * ty)
        dong = {"ten": goc.name, "dur_goc": dg, "dur_xuat": dr, "k": k,
                "moc": {}}
        print(f"  {'mốc':>5} {'T xuất':>9} {'s gốc':>9} {'GỐC':>8} "
              f"{'XUẤT':>8} {'còn':>6}  vùng")
        for r in MOC_TY:
            T = round(dr * r, 3)
            s = round(min(dg - 0.05, T / k), 3)
            mg = CC.mat_do_vung(goc, d.y0, d.y1, [s],
                                x0=(d.x0_dai or d.x0), x1=(d.x1_dai or d.x1))
            mr = CC.mat_do_vung(ra_f, y0, y1, [T], x0=xa, x1=xb)
            giu = mr / max(1e-9, mg)
            vung = "ĐUÔI-KHÔNG-ENABLE" if T > dg else "trong tầm enable"
            print(f"  {int(r*100):4d}% {T:9.3f} {s:9.3f} {mg:8.4f} {mr:8.4f} "
                  f"{giu*100:5.1f}%  {vung}")
            dong["moc"][f"{int(r*100)}%"] = {
                "T": T, "s": s, "goc": round(mg, 5), "xuat": round(mr, 5),
                "ty_giu": round(giu, 4), "duoi": T > dg}
        for r in MOC_ANH:
            T = round(dr * r, 3)
            CC.trich_khung(ra_f, T, RA / f"V{i_v}_XUAT_{int(r*100)}.png")
        bang.append(dong)
    (RA / "thuc_te.json").write_text(
        json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {RA / 'thuc_te.json'} · ảnh PNG trong {RA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
