# -*- coding: utf-8 -*-
"""ĐO TRÊN ĐƯỜNG XUẤT THẬT: che DẢI NGANG vs che HỘP CHỮ.

Không dựng lệnh ffmpeg riêng — gọi thẳng `ffmpeg_utils.export_canvas_clip`
đúng như app làm, kể cả ghép 2 đoạn HOOK-FIRST (ngược thời gian) để trục
`enable=` bị thử thật.

BỐN CON SỐ:
  1. DIỆN TÍCH CHE (điểm ảnh · giây) — con số chính anh Hùng hỏi
  2. mật độ nét TRONG hộp sau khi che (phải ~0 = chữ biến mất)
  3. PSNR NGOÀI hộp (phải `inf` = không rò một điểm ảnh nào)
  4. chi phí thêm mỗi phút phim (ĐAN XEN, không đo liền mạch)
Kèm trích PNG TRƯỚC/SAU để NGƯỜI TỰ NHÌN.
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
_SB = Path(r"D:\claude\_do_che_chu\_sandbox")
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                              # noqa: BLE001
    pass

from app.core import che_chu as C                              # noqa: E402
from app.core import ffmpeg_utils as FU                        # noqa: E402

KHO = Path(r"D:\claude\_do_che_chu\nguon")
SAN = Path(r"D:\claude\_do_che_chu\_hop")
SAN.mkdir(parents=True, exist_ok=True)
RECT = (0.5, 0.5, 1.0)
OUT_W, OUT_H = 1080, 1920


def _psnr(a: Path, b: Path, vung: list) -> float:
    """PSNR sau khi ĐEN HOÁ mọi hộp trong `vung` = [(x0,y0,w,h), …]."""
    ve = "".join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=black@1:t=fill,"
                 for x, y, w, h in vung) or "null,"
    vf = (f"[0:v]{ve}copy[a];[1:v]{ve}copy[b];[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a), "-i",
                        str(b), "-filter_complex", vf, "-f", "null", "-"],
                       capture_output=True, creationflags=C._CREATE_NO_WINDOW)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


def _dai_ra(d, W: int, H: int) -> tuple:
    """Đổi toạ độ NGUỒN -> toạ độ FILE XUẤT 1080x1920 (khối video giữa khung)."""
    cx, cy, sw = RECT
    vw = max(2, int(round(sw * OUT_W)) // 2 * 2)
    vh = int(round(vw * H / W))
    vh += vh % 2
    top = cy * OUT_H - vh / 2.0
    left = cx * OUT_W - vw / 2.0
    return left, top, vw / float(W), vh / float(H)


def _xuat(src: Path, dst: Path, segs, che: bool, hop: bool,
          xoa_nho: bool = True) -> tuple:
    # `xoa_nho=False` = SỔ NHỚ CÒN NÓNG. Phải đo CẢ HAI cách vì hai chi phí này
    # khác hẳn nhau về bản chất: quét dày là MỘT LẦN CHO MỖI VIDEO (3 Part dùng
    # chung), còn chuỗi filter thì lượt xuất nào cũng trả. Trộn hai thứ vào một
    # con số là báo sai — đúng bẫy "đo nhầm mẫu số" của cổng 46.
    if xoa_nho:
        C._DAI_NHO.clear()
        C._DAI_KHOA.clear()
    C._BAT_HOP = hop
    log: list = []
    t = time.perf_counter()
    FU.export_canvas_clip(str(src), str(dst), segs, RECT, bg="blur",
                          out_w=OUT_W, out_h=OUT_H, fx_fade=False,
                          fx_whoosh=False, hieu_ung="tat", chuyen_canh="tat",
                          che_chu=che, che_chu_cach="mo", che_chu_muc=1.0,
                          che_chu_log=log)
    return time.perf_counter() - t, (log[0] if log else {})


def do_mot(ten: str, segs, vong: int = 3):
    p = KHO / ten
    if not p.exists():
        return
    tt = C.thong_tin(p)
    W, H = tt["rong"], tt["cao"]
    dai_clip = sum(b - a for a, b in segs)
    print(f"\n═══ {ten}  {W}x{H} · clip {dai_clip:.1f}s · segs={segs}")

    ket: dict = {}
    bao: dict = {}
    for v in range(vong):                              # ĐAN XEN
        for ten_c, che, hop in (("tắt", False, False),
                                ("DẢI", True, False),
                                ("HỘP", True, True)):
            o = SAN / f"{Path(ten).stem}_{ten_c[:3]}.mp4"
            # LƯỢT 1 — SỔ NHỚ RỖNG (gồm cả lượt dò). BẮT BUỘC xoá sổ khi ĐỔI
            # CHẾ ĐỘ: bản trước của script này không xoá, nên lượt "HỘP" đọc
            # lại bản DẢI đã nhớ và in ra "giảm 0,0%" — số SAI mà trông rất
            # thuyết phục.
            dt1, lg = _xuat(p, o, segs, che, hop, xoa_nho=True)
            # LƯỢT 2 — SỔ NHỚ CÒN NÓNG (chỉ còn chuỗi filter)
            dt2, _ = _xuat(p, o, segs, che, hop, xoa_nho=False)
            ket.setdefault(ten_c, []).append(dt2)
            ket.setdefault(ten_c + "+dò", []).append(dt1)
            bao[ten_c] = (o, lg)
    ph = dai_clip / 60.0
    tat = statistics.median(ket["tắt"])
    ph_nguon = tt["do_dai"] / 60.0
    for k in ("tắt", "DẢI", "HỘP"):
        m = statistics.median(ket[k])
        md = statistics.median(ket[k + "+dò"])
        them = "" if k == "tắt" else (
            f"  · lượt ĐẦU của video (kèm dò) {md:5.2f}s = "
            f"+{(md-m)/ph_nguon:.2f} s/phút PHIM NGUỒN, MỘT LẦN cho mọi Part")
        print(f"   {k:4s}: sổ nhớ NÓNG {m:6.2f}s  "
              f"(+{(m-tat)/ph:5.2f} s/phút clip){them}")

    # ---- DIỆN TÍCH CHE ----
    left, top, tx, ty = _dai_ra(None, W, H)
    for k in ("DẢI", "HỘP"):
        o, lg = bao[k]
        d = lg.get("dai") or {}
        if not d.get("co_chu"):
            print(f"   {k}: KHÔNG che ({lg.get('ly_do','')[:60]})")
            continue
        cao = d["y1"] - d["y0"]
        hop_ra = C.hop_theo_doan(C.DaiChu(**{q: d[q] for q in
                                             ("co_chu", "y0", "y1", "x0", "x1",
                                              "rong", "cao", "hop")}), segs) \
            if (k == "HỘP" and d.get("hop")) else []
        if hop_ra:
            dt = sum((b - a) * (x1 - x0) for a, b, x0, x1 in hop_ra) * cao
            n_moc = len(hop_ra)
        else:
            dt = dai_clip * (d["x1"] - d["x0"]) * cao
            n_moc = 1
        bao[k] = (o, lg, dt, hop_ra, d)
        print(f"   {k}: {n_moc} hộp · diện tích che "
              f"{dt/1e6:8.2f} triệu điểm-ảnh·giây · {lg.get('ly_do','')[:70]}")
    if len(bao.get("DẢI", ())) < 3 or len(bao.get("HỘP", ())) < 3:
        return
    d_dai, d_hop = bao["DẢI"][2], bao["HỘP"][2]
    print(f"   >>> DIỆN TÍCH CHE GIẢM {(1-d_hop/d_dai)*100:.1f}%")

    # ---- chữ đã bị che chưa · rò ra ngoài chưa ----
    o_tat = bao["tắt"][0]
    for k in ("DẢI", "HỘP"):
        o, lg, dt, hop_ra, d = bao[k]
        y0 = int(top + d["y0"] * ty)
        y1 = int(top + d["y1"] * ty)
        if hop_ra:
            vung = [(int(left + x0 * tx), y0,
                     max(2, int((x1 - x0) * tx)), max(2, y1 - y0))
                    for _, _, x0, x1 in hop_ra]
        else:
            vung = [(int(left + d["x0"] * tx), y0,
                     max(2, int((d["x1"] - d["x0"]) * tx)), max(2, y1 - y0))]
        ps = _psnr(o_tat, o, vung)
        moc = [dai_clip * f for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
        md0 = md1 = 0.0
        for (x, y, w, h) in vung[:6]:
            md0 += C.mat_do_vung(o_tat, y, y + h, moc, x, x + w)
            md1 += C.mat_do_vung(o, y, y + h, moc, x, x + w)
        md0 /= max(1, len(vung[:6]))
        md1 /= max(1, len(vung[:6]))
        print(f"   {k}: mật độ nét TRONG hộp {md0:.4f} -> {md1:.4f}  ·  "
              f"PSNR NGOÀI hộp = {ps}")

    # ---- ảnh để NGƯỜI TỰ NHÌN ----
    for i, f in enumerate((0.15, 0.45, 0.75)):
        t = dai_clip * f
        for k, o in (("tat", o_tat), ("dai", bao["DẢI"][0]),
                     ("hop", bao["HỘP"][0])):
            C.trich_khung(o, t, SAN / f"NHIN_{Path(ten).stem}_{i}_{k}.png")
    print(f"   ảnh: {SAN}\\NHIN_{Path(ten).stem}_*.png")


if __name__ == "__main__":
    # HOOK-FIRST: đoạn sau đứng TRƯỚC -> ép trục `enable=` phải quy đổi đúng
    do_mot("zh_ep12.mp4", [(120.0, 150.0), (40.0, 70.0)])
    do_mot("zh_dongho.mp4", [(100.0, 130.0), (20.0, 50.0)])
