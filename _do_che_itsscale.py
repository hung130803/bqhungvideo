"""ĐO ĐỐI CHỨNG CÓ KIỂM SOÁT: `-itsscale` làm hộp che TRÔI khỏi đoạn cuối.

Anh Hùng: *"sao cứ đến gần cuối video nó k che mờ chữ gì cả"*.

**THƯỚC PHẢI GHÉP CẶP TỪNG KHUNG.** So "gốc tại T" với "xuất tại T" là SAI khi
`he_so_hinh > 1` (bản xuất bị giãn k lần nên giây T của nó là nội dung giây T/k
của gốc — hai cảnh khác nhau). Ở đây mỗi arm có một bản ĐỐI CHỨNG chạy CÙNG hệ
số k nhưng `che_chu=False` -> `-c:v copy` -> **khung giống từng điểm ảnh**. Tỉ
lệ `che/đối_chứng` tại CÙNG một giây T vì thế là số sạch: 1,00 = KHÔNG che gì ·
0,00 = che sạch.

Ba arm, đúng hai ca mà báo cáo cần:
  · `k=1.00` — ĐỐI CHỨNG PHẢI CÓ RĂNG: không giãn thì mọi mốc phải được che.
  · `k=1.20` — đúng chế độ "Chỉnh video theo giọng" anh Hùng đang chạy.
  · `k=1.25` — trần của nguồn 25 fps (video thứ 4 của anh Hùng).

CHẠY:  .venv\\Scripts\\python _do_che_itsscale.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

KHO = Path(r"C:\Users\Admin\Downloads\longtieng")      # CHỈ ĐỌC
RA = Path(__file__).resolve().parent / "_kq_che_cuoi"
HOP = RA / "hop_cat"
#: Độ dài mảnh nguồn. **CỐ Ý KHÔNG chia hết cho `HOP_DOAN`=8** để ca "đoạn lẻ
#: cuối" cũng nằm trong phép đo này (45 = 5x8 + 5).
DAI_NGUON = 45.0
BAT_DAU = 30.0
#: Mốc đo theo % ĐỘ DÀI BẢN XUẤT (dày ở đuôi — chỗ đang hỏng).
MOC_TY = (0.10, 0.30, 0.50, 0.70, 0.80, 0.85, 0.90, 0.94, 0.97, 0.99)


def _ff(args: list, ten: str) -> None:
    from config import settings
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-v", "error", *args],
                       capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"{ten}: {r.stderr.decode('utf-8','replace')[:400]}")


def _dung_nguon() -> Path:
    """Cắt một mảnh nguồn Douyin THẬT (mã hoá lại cho mốc chính xác)."""
    src = next((p for p in sorted(KHO.glob("*.mp4")) if p.is_file()), None)
    if src is None:
        raise SystemExit("KHÔNG có nguồn trong " + str(KHO))
    dst = HOP / "nguon.mp4"
    if dst.is_file():
        return dst
    _ff(["-ss", f"{BAT_DAU:.3f}", "-t", f"{DAI_NGUON:.3f}", "-i", str(src),
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", str(dst)], "cắt nguồn")
    return dst


def _tieng(giay: float, dst: Path) -> Path:
    """WAV im lặng dài `giay`. `-t` đặt TRƯỚC `-i` (bài học: sai chỗ thì
    `anullsrc` ghi vô hạn và đã đầy ổ C một lần)."""
    if not dst.is_file():
        _ff(["-f", "lavfi", "-t", f"{giay:.3f}",
             "-i", "anullsrc=r=44100:cl=stereo", "-c:a", "aac", "-b:a", "96k",
             str(dst)], "sinh tiếng im")
    return dst


def main() -> int:
    from app.core import che_chu as CC
    from app.core import thay_giong as TG
    if HOP.exists():
        shutil.rmtree(HOP, ignore_errors=False)
    HOP.mkdir(parents=True, exist_ok=True)
    RA.mkdir(exist_ok=True)

    nguon = _dung_nguon()
    tt = CC.thong_tin(nguon)
    dur = float(tt["do_dai"] or 0)
    d = CC.dai_theo_video(nguon)
    print("=" * 78)
    print(f"NGUỒN: {nguon.name} {tt['rong']}x{tt['cao']} {dur:.3f}s "
          f"({dur/8:.2f} đoạn 8s -> đoạn lẻ cuối {dur % 8:.2f}s)")
    print(f"  dải: co_chu={d.co_chu} y={d.y0}..{d.y1} · {len(d.hop or [])} mốc")
    if not d.co_chu:
        print("KHÔNG dò ra chữ trên mảnh nguồn -> không đo được"); return 2
    hop_ra = CC.hop_theo_doan(d, [(0.0, dur)])
    print(f"  hộp theo đoạn (segs=[(0,{dur:.2f})]): {len(hop_ra)} mốc, "
          f"phủ tới T = {max(b for _, b, _, _ in hop_ra):.3f}s")

    kq = {"nguon": nguon.name, "dur": dur, "arm": {}}
    for k in (1.00, 1.20, 1.25):
        au = _tieng(dur * k, HOP / f"im_{int(k*100)}.m4a")
        ra_che = HOP / f"CHE_k{int(k*100)}.mp4"
        ra_ref = HOP / f"REF_k{int(k*100)}.mp4"
        t0 = time.time()
        log: list = []
        TG.thay_audio_video(nguon, au, ra_che, che_chu=True, che_chu_cach="mo",
                            che_chu_muc=1.0, che_chu_log=log, he_so_hinh=k)
        TG.thay_audio_video(nguon, au, ra_ref, che_chu=False, he_so_hinh=k)
        tr = CC.thong_tin(ra_che)
        drr = float(tr["do_dai"] or 0)
        print("\n" + "-" * 78)
        print(f"ARM k={k:.2f}  ({time.time()-t0:.1f}s)  xuất {drr:.3f}s "
              f"· che={log[0].get('che')} · {log[0].get('ly_do','')[:70]}")
        kh_c, kh_r = CC.so_khung_hinh(ra_che), CC.so_khung_hinh(ra_ref)
        print(f"  giãn đo được {drr/max(1e-9,dur):.4f} (mong {k:.4f}) · số khung"
              f" che={kh_c} đối_chứng={kh_r} "
              f"({'KHỚP' if kh_c == kh_r else '**LỆCH**'})")
        # VÙNG TỪNG HỎNG: khi phép giãn còn nằm TRƯỚC khối che (`-itsscale`),
        # mọi khung có T > độ_dài_GỐC rơi ra NGOÀI mọi mệnh đề `enable` nên
        # không được che. Đặt `setpts` SAU khối che thì vùng này hết đặc biệt.
        print(f"  VÙNG TỪNG HỎNG (T > {dur:.2f}s) = {max(0.0, drr-dur):.2f}s = "
              f"{max(0.0,1-dur/max(1e-9,drr))*100:.1f}% cuối clip")
        print(f"  {'mốc':>5} {'T':>8} {'ĐỐI CHỨNG':>10} {'CHE':>8} {'còn':>7}"
              f"  kết luận")
        arm = {"k": k, "dur_xuat": drr, "moc": {}}
        y0, y1 = d.y0, d.y1
        xa, xb = (d.x0_dai or d.x0), (d.x1_dai or d.x1)
        for r in MOC_TY:
            T = round(drr * r, 3)
            mref = CC.mat_do_vung(ra_ref, y0, y1, [T], x0=xa, x1=xb)
            mche = CC.mat_do_vung(ra_che, y0, y1, [T], x0=xa, x1=xb)
            giu = mche / max(1e-9, mref)
            kl = ("KHÔNG CHE" if giu > 0.80 else
                  "che một phần" if giu > 0.15 else "đã che")
            print(f"  {int(r*100):4d}% {T:8.3f} {mref:10.4f} {mche:8.4f} "
                  f"{giu*100:6.1f}%  {kl}")
            arm["moc"][f"{int(r*100)}%"] = {
                "T": T, "ref": round(mref, 5), "che": round(mche, 5),
                "ty_giu": round(giu, 4), "duoi_tam": T > dur}
        kq["arm"][f"k{k:.2f}"] = arm
        for r in (0.50, 0.90, 0.99):
            T = round(drr * r, 3)
            CC.trich_khung(ra_che, T, RA / f"CHE_k{int(k*100)}_{int(r*100)}.png")
            CC.trich_khung(ra_ref, T, RA / f"REF_k{int(k*100)}_{int(r*100)}.png")
    (RA / "itsscale.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    # PHÁN QUYẾT — script tự chấm, đừng để người đọc bảng rồi tự suy.
    xau = [(a["k"], m, v["ty_giu"]) for a in kq["arm"].values()
           for m, v in a["moc"].items() if v["ty_giu"] > 0.15]
    print("\n" + "=" * 78)
    if xau:
        print(f"HỎNG — {len(xau)} mốc còn > 15% mật độ nét (mốc nào cũng phải "
              f"được che, kể cả sau khi giãn hình):")
        for kk, m, g in xau:
            print(f"   k={kk:.2f} mốc {m} còn {g*100:.1f}%")
    else:
        print("ĐẠT — 30/30 mốc (3 hệ số × 10 mốc) đều đã che, kể cả vùng "
              "T > độ_dài_gốc từng lọt nguyên chữ.")
    print(f"-> {RA / 'itsscale.json'} · ảnh PNG trong {RA}")
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
