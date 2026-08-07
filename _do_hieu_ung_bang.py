# -*- coding: utf-8 -*-
"""BẢNG ĐO THẬT từng hiệu ứng: có THẤY ĐƯỢC không · lệch màu · chi phí CPU.

Đây là "cổng render THẬT" của việc hiệu ứng. Không tin tên hiệu ứng: render bằng
ffmpeg + video Nhật THẬT, trích khung, ĐẾM PIXEL, đo U/V.

Mỗi hiệu ứng đo ở `dam = DAM_MAX` (25% — trần luật 2, ca XẤU NHẤT cho lệch màu):
  %px_trong : % pixel khác bản KHÔNG hiệu ứng, ở GIỮA cửa sổ  -> phải LỚN
              (đây là "anh Hùng có thấy không", quan trọng nhất)
  %px_ngoai : % pixel khác, ở NGOÀI cửa sổ  -> phải ~0 (không rò ra cả clip)
  dU,dV     : lệch TRUNG BÌNH U/V (bắt lỗi kiểu tim.mp4 V=142 tím cả khung)
  |dU|,|dV| : lệch TỪNG PIXEL (bắt desaturate/đổi hue mà trung bình triệt tiêu:
              `bw0r` làm U,V -> 128, trung bình chỉ lệch 2,8 nhưng từng pixel
              lệch cả chục -> phải bắt được)
  cpu       : CPU-giây RIÊNG của lệnh ffmpeg đó (psutil), trừ nền

Chạy: .venv\\Scripts\\python _do_hieu_ung_bang.py [--lap 3] [--nho]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import _nguon_nhat                                          # noqa: E402
from app.core import hieu_ung as HU                         # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
MOC = 200.0        # giây — CẢNH SÁNG. Bài học: giây 20 của nguồn Nhật sáng TB
                   # chỉ 3,3/255 (gần đen) -> ca đếm pixel FAIL OAN.
DAI = 3.0
BAT = 1.0          # cửa sổ hiệu ứng bắt đầu ở giây 1,0 của đoạn
NGOAI = 0.40       # mốc trích khung NGOÀI cửa sổ


def _ff() -> str:
    return HU._ffmpeg()


def _font() -> str:
    d = os.path.join(ROOT, "app", "assets", "fonts")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".ttf", ".otf")):
                return os.path.join(d, f)
    return ""


def render(src: str, chain: str, dst: str, W: int, H: int, fps: int,
           do_cpu: bool = False) -> tuple[int, str, float, float]:
    """Render đoạn thử. Trả (rc, log_cuoi, wall, cpu_giay)."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},setsar=1")
    if chain:
        vf += "," + chain
    cmd = [_ff(), "-y", "-hide_banner", "-nostats", "-ss", f"{MOC:.3f}",
           "-t", f"{DAI:.3f}", "-i", src, "-an", "-vf", vf, "-r", str(fps),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
           "-pix_fmt", "yuv420p", dst]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, errors="replace",
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    cpu = 0.0
    if do_cpu:
        try:
            pr = psutil.Process(p.pid)
            while p.poll() is None:
                try:
                    c = pr.cpu_times()
                    cpu = c.user + c.system
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                time.sleep(0.02)
        except psutil.NoSuchProcess:
            pass
    out = p.stdout.read() if p.stdout else ""
    p.wait()
    return p.returncode, out[-500:], time.time() - t0, cpu


def khung(path: str, t: float):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        return None
    return cv2.cvtColor(fr, cv2.COLOR_BGR2YUV)


def so(a, b) -> dict:
    """So 2 khung YUV -> chỉ số.

    3 THƯỚC ĐO "THẤY ĐƯỢC" (phải có cả 3 mới không FAIL OAN):
      pct      % pixel lệch SÁNG > 12  — thước chính
      pct_mau  % pixel lệch MÀU  > 12  — `rgbashift`/lệch RGB gần như không đổi
               SÁNG (đo 5,6%) nhưng viền màu thì thấy rõ mồn một
      pct_manh % pixel lệch SÁNG > 60  — CHỮ (đếm ngược) chiếm ít diện tích mà
               mắt thấy ngay; cùng bài học cổng 21 "ngưỡng phải theo bản chất"
    2 THƯỚC ĐO "ĐỔI MÀU DA":
      du/dv          lệch TRUNG BÌNH  (bắt tim.mp4: V 128 -> 142 tím cả khung)
      du_px/dv_px    lệch TỪNG PIXEL  (bắt desaturate: `bw0r` đẩy U,V về 128,
                     trung bình chỉ lệch 2,8 mà từng pixel lệch cả chục)
      du_sd/dv_sd    lệch ĐỘ LỆCH CHUẨN — dùng cho hiệu ứng DỜI CHỖ pixel
                     (zoom/rung/glitch): da vẫn đúng màu, chỉ nằm chỗ khác, nên
                     đo từng pixel là FAIL OAN; phải kiểm PHÂN BỐ chroma còn nguyên
    """
    dy = np.abs(a[:, :, 0].astype(np.int16) - b[:, :, 0].astype(np.int16))
    du = a[:, :, 1].astype(np.int16) - b[:, :, 1].astype(np.int16)
    dv = a[:, :, 2].astype(np.int16) - b[:, :, 2].astype(np.int16)
    return {
        "pct": float((dy > 12).mean() * 100),
        "pct_mau": float(((np.abs(du) > 12) | (np.abs(dv) > 12)).mean() * 100),
        "pct_manh": float((dy > 60).mean() * 100),
        "dy": float(dy.mean()),
        "du": float(du.mean()),
        "dv": float(dv.mean()),
        "du_px": float(np.abs(du).mean()),
        "dv_px": float(np.abs(dv).mean()),
        "du_sd": float(a[:, :, 1].std() - b[:, :, 1].std()),
        "dv_sd": float(a[:, :, 2].std() - b[:, :, 2].std()),
    }


def cham(h, m: dict, mo: dict) -> str:
    """Chấm 1 hiệu ứng: 'OK' hoặc lý do FAIL. Luật 1 + 3 + 'phải THẤY ĐƯỢC'."""
    # luật 3 — đổi màu da
    if abs(m["du"]) >= HU.UV_MAX or abs(m["dv"]) >= HU.UV_MAX:
        return f"LOÈ-MÀU (lệch TB U {m['du']:+.2f} V {m['dv']:+.2f})"
    if h.doi_cho:
        if abs(m["du_sd"]) >= HU.UV_MAX or abs(m["dv_sd"]) >= HU.UV_MAX:
            return f"LOÈ-MÀU (phân bố U {m['du_sd']:+.2f} V {m['dv_sd']:+.2f})"
    elif m["du_px"] >= HU.UV_MAX or m["dv_px"] >= HU.UV_MAX:
        return f"LOÈ-MÀU (từng pixel U {m['du_px']:.2f} V {m['dv_px']:.2f})"
    # phải THẤY ĐƯỢC (điều kiện số 1 của anh Hùng)
    if not (m["pct"] >= h.nguong_thay or m["pct_mau"] >= h.nguong_thay
            or m["pct_manh"] >= h.nguong_manh or m["dy"] >= 6.0):
        return (f"KHÔNG-THẤY (Y {m['pct']:.1f}% · màu {m['pct_mau']:.1f}% · "
                f"mạnh {m['pct_manh']:.1f}%)")
    # luật 1 — không rò ra ngoài cửa sổ
    if mo["pct"] > 1.0 or mo["pct_mau"] > 1.0:
        return f"RÒ-NGOÀI ({mo['pct']:.1f}% / màu {mo['pct_mau']:.1f}%)"
    return "OK"


def may_ranh() -> tuple[bool, str]:
    c = psutil.cpu_percent(interval=3.0)
    la = []
    for pr in psutil.process_iter(["name"]):
        n = (pr.info["name"] or "").lower()
        if n in ("ffmpeg.exe", "bqhungvideo.exe"):
            la.append(n)
    return (c < 20 and not la), f"cpu {c:.1f}% · tiến trình lạ {la or 'không'}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lap", type=int, default=1)
    ap.add_argument("--nho", action="store_true", help="540x960 cho nhanh")
    ap.add_argument("--json", default="_ket_hieu_ung.json")
    a = ap.parse_args()
    W, H, FPS = (540, 960, 30) if a.nho else (1080, 1920, 30)

    src = _nguon_nhat.mot("JP")
    if not src:
        print("KHONG CO nguon Nhat")
        return 2
    ranh, note = may_ranh()
    print(f"[máy] {note} -> {'RẢNH' if ranh else 'BẬN (số CPU sẽ nhiễu)'}")
    print(f"[nguồn] {os.path.basename(src)}")
    print(f"[khung] {W}x{H} @{FPS}  ·  đoạn {MOC}s +{DAI}s  ·  dam={HU.DAM_MAX}")
    print(f"[frei0r] {HU.co_frei0r()} — {HU.thu_muc_frei0r()}")

    td = tempfile.mkdtemp(prefix="_hu_bang_")
    font = _font()
    goc = os.path.join(td, "_goc.mp4")
    rc, log, wall0, cpu0 = render(src, "", goc, W, H, FPS, do_cpu=True)
    if rc != 0:
        print("render GỐC lỗi:", log)
        return 2
    for _ in range(max(0, a.lap - 1)):
        _r, _l, w2, c2 = render(src, "", goc, W, H, FPS, do_cpu=True)
        wall0, cpu0 = min(wall0, w2), min(cpu0, c2)
    print(f"[gốc] wall {wall0:.2f}s · CPU {cpu0:.2f}s")

    ket: list[dict] = []
    print()
    print(f"{'khoá':<13}{'tên':<24}{'%pxY':>7}{'%pxC':>7}{'ngoài':>7}{'|dY|':>6}"
          f"{'dU':>6}{'dV':>6}{'|dU|':>6}{'|dV|':>6}{'cpu':>6}{'x':>6}  KQ")
    for k, h in HU.KHO.items():
        if h.module and not HU.module_co(h.module):
            print(f"{k:<13}{h.ten:<24}  -- BỎ QUA: thiếu plugin {h.module}")
            continue
        b = BAT
        e = min(DAI - 0.05, BAT + max(HU.DAI_MIN, min(HU.DAI_MAX, h.dai)))
        chain = h.chuoi(HU.DAM_MAX, b, e, W, H, FPS, font)
        dst = os.path.join(td, k + ".mp4")
        rc, log, wall, cpu = render(src, chain, dst, W, H, FPS, do_cpu=True)
        for _ in range(max(0, a.lap - 1)):
            _r, _l, w2, c2 = render(src, chain, dst, W, H, FPS, do_cpu=True)
            rc = rc or _r
            wall, cpu = min(wall, w2), min(cpu, c2)
        if rc != 0 or not os.path.exists(dst) or os.path.getsize(dst) < 2000:
            dong = [x for x in log.splitlines() if x.strip()]
            print(f"{k:<13}{h.ten:<24}  ** LỖI FILTER ** {(dong[-1] if dong else '')[:60]}")
            ket.append({"khoa": k, "loi": (dong[-1] if dong else "rc=%d" % rc)})
            continue
        f_tr = khung(dst, (b + e) / 2)
        f_ng = khung(dst, NGOAI)
        g_tr = khung(goc, (b + e) / 2)
        g_ng = khung(goc, NGOAI)
        if any(x is None for x in (f_tr, f_ng, g_tr, g_ng)):
            print(f"{k:<13}{h.ten:<24}  ** không đọc được khung **")
            continue
        m = so(f_tr, g_tr)
        mo = so(f_ng, g_ng)
        kq = cham(h, m, mo)
        ket.append({"khoa": k, "ten": h.ten, "capcut": h.capcut, "nhom": h.nhom,
                    "trong": m, "ngoai": mo, "cpu": cpu, "wall": wall,
                    "cpu_x": cpu / cpu0 if cpu0 else 0, "kq": kq})
        print(f"{k:<13}{h.ten:<24}{m['pct']:7.1f}{m['pct_mau']:7.1f}"
              f"{mo['pct']:7.1f}{m['dy']:6.1f}"
              f"{m['du']:6.2f}{m['dv']:6.2f}{m['du_px']:6.2f}{m['dv_px']:6.2f}"
              f"{cpu:6.2f}{(cpu / cpu0 if cpu0 else 0):6.2f}  {kq}")

    with open(os.path.join(ROOT, a.json), "w", encoding="utf-8") as f:
        json.dump({"goc_cpu": cpu0, "goc_wall": wall0, "W": W, "H": H,
                   "ket": ket}, f, ensure_ascii=False, indent=1)
    ok = [r for r in ket if r.get("kq") == "OK"]
    print(f"\n=== ĐẠT {len(ok)}/{len(ket)} ===")
    for r in ket:
        if r.get("kq") and r["kq"] != "OK":
            print(f"  {r['khoa']:<13} {r['kq']}")
        if r.get("loi"):
            print(f"  {r['khoa']:<13} LỖI: {r['loi'][:70]}")
    print(f"-> {a.json}   (thư mục render: {td})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
