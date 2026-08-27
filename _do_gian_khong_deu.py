# -*- coding: utf-8 -*-
"""GIÃN **KHÔNG ĐỀU** ĐỂ BỚT IM GIỮA CÂU — ĐO CẢ HAI MẶT TRƯỚC KHI VIẾT.

Ý tưởng (anh Hùng 27/08/2026, mục C): chế độ *"Chỉnh video theo giọng"* làm
chậm hình ĐỀU `k` lần nên nó giãn cả chỗ ĐANG IM -> khoảng nghỉ giữa câu dài
ra `(k−1)×` -> *"được đoạn rồi nghỉ"*. Vậy giãn NHIỀU ở chỗ im, ÍT ở chỗ nói
thì vẫn đủ tổng thời lượng mà tiếng nghe liền mạch hơn.

**HAI CÁI GIÁ, ĐO CẢ HAI — bỏ một cái là báo cáo nửa vời:**

  (1) **NHỊP HÌNH CỤC BỘ.** `setpts`/`-itsscale` KHÔNG sinh khung mới; giãn
      chỗ nào thì chỗ đó nhịp hình tụt đúng theo hệ số CỤC BỘ. Repo đã có SÀN
      **`SAN_NHIP_HINH_FPS = 20`** (cổng 89 mục 8 đo: gỡ trần -> 9,46 fps =
      hình vỡ). Giãn đều k=1,199 đưa CẢ phim về đúng 20,0 fps — tức **đã nằm
      NGAY TRÊN SÀN**, không còn chỗ để dồn phần giãn vào riêng khoảng im.
      Script này đo nhịp hình THẬT trong TỪNG cửa sổ (đọc mốc từng khung bằng
      ffprobe), không suy từ công thức.

  (2) **PHẢI MÃ HOÁ LẠI CẢ LUỒNG HÌNH.** Đường hiện tại dùng `-itsscale` —
      một SỐ VÔ HƯỚNG, nhân mốc lúc remux, `-c:v copy`, **0 khung bị nén
      lại**. Giãn không đều thì bắt buộc `setpts` = filter = encode lại. Với
      200-300 kênh đó là một đời nén nữa + hàng giờ máy. Arm ĐỀU-ENCODE tách
      riêng phần giá này ra khỏi phần "không đều".

Phép map thời gian dùng dạng ĐÓNG, không lồng `if`:
    f(T) = T + C · Σ max(0, min(T, b_i) − a_i)      với C = k_im − 1
tức cộng thêm phần giãn của MỌI khoảng im đã trôi qua. Đơn điệu theo cấu tạo.

Nguồn `Downloads\\longtieng` **CHỈ ĐỌC** — cắt ra bản sao trong hộp cát.
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from config import settings                            # noqa: E402
from app.core import thay_giong as tg                  # noqa: E402

NGUON_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
KQ = REPO / "_kq_lienmach"
SB = KQ / "_sb_gian"
_NW = 0x0800_0000 if os.name == "nt" else 0

GIAY = 24.0               # mảnh nguồn đem đo
K = 1.1988                # ĐÚNG hệ số 4/4 video anh Hùng đang chạy (chạm trần)

#: nhịp câu giả lập theo SỐ ĐO THẬT trên job anh Hùng: 103-184 câu / video,
#: tức ~2,2-3,5 giây một câu. Lấy 2,0 s nói + 0,8 s nghỉ = chu kỳ 2,8 s.
NOI = 2.0
NGHI = 0.8


def _chay(args: list[str], timeout: int = 900) -> tuple[int, str, float]:
    t0 = time.time()
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-v", "error", *args],
                       capture_output=True, creationflags=_NW, timeout=timeout)
    return (r.returncode, r.stderr.decode("utf-8", "replace")[-600:],
            time.time() - t0)


def moc_khung(path: Path) -> list[float]:
    """Mốc TỪNG KHUNG của luồng hình đầu ra (giây). Đây là số ĐO, không suy."""
    r = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, creationflags=_NW, timeout=900)
    ra = []
    for d in r.stdout.decode("utf-8", "replace").splitlines():
        d = d.strip().rstrip(",")
        try:
            ra.append(float(d))
        except ValueError:
            pass
    return sorted(ra)


def nhip_trong(moc: list[float], a: float, b: float) -> float:
    """Nhịp hình THẬT trong cửa sổ [a,b] của trục ĐẦU RA = số khung / giây."""
    n = sum(1 for t in moc if a <= t < b)
    return n / max(1e-6, b - a)


def khoang_nghi(tong: float) -> list[tuple[float, float]]:
    """Các khoảng IM trên trục NGUỒN, theo nhịp câu giả lập."""
    ra, t = [], NOI
    while t + NGHI <= tong:
        ra.append((round(t, 3), round(t + NGHI, 3)))
        t += NOI + NGHI
    return ra


def bieu_thuc(ims: list[tuple[float, float]], c: float) -> str:
    """`setpts` dạng ĐÓNG: T + C·Σ max(0, min(T,b)−a). Đơn điệu theo cấu tạo.

    **DẤU PHẨY PHẢI ESCAPE `\\,`** — trong chuỗi filtergraph, `,` là DẤU NỐI
    HAI FILTER. Viết thẳng `min(T,b)` thì ffmpeg cắt đôi ngay đó và báo
    *"No such filter: 'min(T'"*. Đã sập một lần trong chính lượt đo này.
    """
    ve = "+".join(f"max(0\\,min(T\\,{b:.4f})-{a:.4f})" for a, b in ims)
    return f"setpts=(T+{c:.6f}*({ve}))/TB"


def main() -> int:
    KQ.mkdir(parents=True, exist_ok=True)
    if SB.exists():
        shutil.rmtree(SB, ignore_errors=True)
    SB.mkdir(parents=True, exist_ok=True)

    vids = sorted(p for p in NGUON_DIR.glob("*.mp4") if p.is_file())
    if not vids:
        print(f"KHÔNG có mp4 trong {NGUON_DIR}")
        return 2
    goc = SB / "goc.mp4"
    # `-t` LÀ TUỲ CHỌN ĐẦU VÀO — đặt sau `-i` là ffmpeg ghi tới khi đầy ổ.
    rc, err, _ = _chay(["-t", f"{GIAY:g}", "-i", str(vids[0]),
                        "-an", "-c:v", "copy", str(goc)])
    if rc != 0:
        print(f"cắt nguồn hỏng: {err}")
        return 2

    dur = tg.probe_duration(goc)
    kn = tg.do_khung_hinh(goc)
    fps_goc = kn / max(1e-6, dur)
    ims = khoang_nghi(dur)
    t_im = sum(b - a for a, b in ims)
    t_noi = dur - t_im
    # giữ NÓI ở tốc độ thật (hệ số 1,0), dồn TOÀN BỘ phần giãn vào chỗ IM
    k_im = (dur * K - t_noi) / max(1e-6, t_im)
    print(f"nguồn {dur:.3f}s · {kn} khung · {fps_goc:.3f} fps")
    print(f"  nói {t_noi:.2f}s · im {t_im:.2f}s ({100*t_im/dur:.1f}%)"
          f" · {len(ims)} khoảng nghỉ")
    print(f"  giãn ĐỀU k = {K}  ->  giãn KHÔNG ĐỀU: nói 1,000 · "
          f"**im {k_im:.4f}**")

    arms: list[dict] = []

    # ARM 1 — ĐANG CHẠY: `-itsscale` + `-c:v copy` (0 khung nén lại)
    ra1 = SB / "A1_deu_copy.mp4"
    rc, err, gy = _chay(["-itsscale", f"{K:.6f}", "-i", str(goc),
                         "-an", "-c:v", "copy", str(ra1)])
    arms.append({"ten": "ĐỀU + itsscale (ĐANG CHẠY)", "ra": ra1, "kn": K,
                 "kim": K, "giay": gy, "rc": rc, "err": err, "encode": False})

    # ARM 2 — ĐỀU nhưng ENCODE LẠI: tách riêng GIÁ CỦA VIỆC ENCODE khỏi giá
    # của việc "không đều". **Đây cũng là đường anh Hùng ĐANG chạy**: 4/4 bản
    # xuất là h264 trong khi nguồn là hevc -> che chữ BẬT -> nhánh che chữ vốn
    # đã `setpts` + encode lại (xem `thay_audio_video`).
    ra2 = SB / "A2_deu_encode.mp4"
    rc, err, gy = _chay(["-i", str(goc), "-an", "-vf", f"setpts=PTS*{K:.6f}",
                         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                         "-pix_fmt", "yuv420p", str(ra2)])
    arms.append({"ten": "ĐỀU + setpts (encode lại)", "ra": ra2, "kn": K,
                 "kim": K, "giay": gy, "rc": rc, "err": err, "encode": True})

    # ARM 3-4 — KHÔNG ĐỀU, hai mức DỒN. `f=1,0` = dồn HẾT phần giãn vào chỗ im
    # (nói chạy tốc độ thật); `f=0,5` = dồn một nửa. Hai mức để thấy ĐƯỜNG
    # CONG đánh đổi chứ không phải một điểm.
    for i, f in ((3, 0.5), (4, 1.0)):
        k_n = 1.0 + (K - 1.0) * (1.0 - f)
        kim = (dur * K - t_noi * k_n) / max(1e-6, t_im)
        bt = bieu_thuc(ims, (kim - k_n))
        # nói giãn `k_n`, im giãn `kim`: f(T) = k_n·T + (kim−k_n)·G(T)
        bt = bt.replace("setpts=(T+", f"setpts=({k_n:.6f}*T+")
        ra = SB / f"A{i}_khongdeu_{int(f*100)}.mp4"
        rc, err, gy = _chay(["-i", str(goc), "-an", "-vf", bt,
                             "-c:v", "libx264", "-preset", "medium",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(ra)])
        arms.append({"ten": f"KHÔNG ĐỀU dồn {int(f*100)}% vào chỗ im",
                     "ra": ra, "kn": k_n, "kim": kim, "giay": gy, "rc": rc,
                     "err": err, "encode": True, "bt_dai": len(bt)})

    for a in arms:
        p: Path = a["ra"]
        if a["rc"] != 0 or not p.exists():
            a["loi"] = a["err"] or "không ra file"
            continue
        moc = moc_khung(p)
        a["khung"] = len(moc)
        a["dai"] = round(tg.probe_duration(p), 3)
        a["fps_tb"] = round(len(moc) / max(1e-6, a["dai"]), 3)
        # nhịp hình trong TỪNG cửa sổ NÓI / IM trên trục ĐẦU RA
        n_noi, n_im = [], []
        kn_, kim_ = float(a["kn"]), float(a["kim"])

        def _f(t: float) -> float:
            """Map thời gian NGUỒN -> ĐẦU RA của ĐÚNG arm này."""
            g = sum(max(0.0, min(t, y) - x) for x, y in ims)
            return kn_ * t + (kim_ - kn_) * g

        for a0, b0 in ims:
            fa, fb = _f(a0), _f(b0)
            n_im.append(nhip_trong(moc, fa, fb))
            n_noi.append(nhip_trong(moc, _f(max(0.0, a0 - NOI)), fa))
        a["fps_noi_tb"] = round(statistics.fmean(n_noi), 2) if n_noi else 0.0
        a["fps_im_tb"] = round(statistics.fmean(n_im), 2) if n_im else 0.0
        a["fps_im_min"] = round(min(n_im), 2) if n_im else 0.0
        a["buoc_nhip"] = (round(a["fps_noi_tb"] / max(0.01, a["fps_im_tb"]), 3)
                          if n_im else 0.0)

    L = ["", "BẢNG C — GIÃN KHÔNG ĐỀU: HAI CÁI GIÁ", "=" * 92,
         f"nguồn {dur:.3f}s · {kn} khung · {fps_goc:.3f} fps · k = {K}",
         f"nói {t_noi:.2f}s / im {t_im:.2f}s ({100*t_im/dur:.1f}%) · "
         f"{len(ims)} khoảng · hệ số CỤC BỘ chỗ im = {k_im:.4f}",
         f"SÀN NHỊP HÌNH CỦA REPO: {tg.SAN_NHIP_HINH_FPS:g} fps", "",
         f"{'arm':<32}{'dài':>9}{'khung':>7}{'fps TB':>9}"
         f"{'fps chỗ NÓI':>13}{'fps chỗ IM':>12}{'bước nhịp':>11}{'giây':>8}"
         f"{'encode':>8}"]
    L.append("-" * 111)
    for a in arms:
        if "khung" not in a:
            L.append(f"{a['ten']:<32}  HỎNG: {a.get('loi','')[:60]}")
            continue
        L.append(f"{a['ten']:<32}{a['dai']:>9.3f}{a['khung']:>7d}"
                 f"{a['fps_tb']:>9.2f}{a['fps_noi_tb']:>13.2f}"
                 f"{a['fps_im_tb']:>12.2f}{a['buoc_nhip']:>11.3f}"
                 f"{a['giay']:>8.2f}{('CÓ' if a['encode'] else 'KHÔNG'):>8}")
    L.append("")
    a3 = arms[2]
    if "fps_im_tb" in a3:
        L.append(f"CHỖ IM của arm KHÔNG ĐỀU chạy {a3['fps_im_tb']:.2f} fps"
                 f" — sàn repo là {tg.SAN_NHIP_HINH_FPS:g} fps"
                 f"  -> {'ĐẠT' if a3['fps_im_tb'] >= tg.SAN_NHIP_HINH_FPS else 'DƯỚI SÀN'}")
        L.append(f"BƯỚC NHỊP tại MỖI mối nối: {a3['buoc_nhip']:.3f} lần"
                 f" ({len(ims)} lần trong {dur:.0f} giây nguồn)")
    if all("giay" in x for x in arms):
        L.append(f"GIÁ ENCODE: {arms[0]['giay']:.2f}s (copy) -> "
                 f"{arms[1]['giay']:.2f}s (đều+encode) -> "
                 f"{arms[2]['giay']:.2f}s (không đều) = "
                 f"{arms[2]['giay'] / max(0.01, arms[0]['giay']):.1f} lần")
    txt = "\n".join(L)
    print(txt)
    (KQ / "C_gian_khong_deu.txt").write_text(txt, encoding="utf-8")
    (KQ / "C_gian_khong_deu.json").write_text(
        json.dumps([{k2: (str(v) if isinstance(v, Path) else v)
                     for k2, v in a.items()} for a in arms],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    # GIỮ file để xem bằng mắt -> chép ra chỗ nghe/nhìn thử
    nhin = REPO / "_NGHE_THU_ANH_HUNG" / "lien_mach" / "gian_khong_deu"
    nhin.mkdir(parents=True, exist_ok=True)
    for a in arms:
        p = a["ra"]
        if isinstance(p, Path) and p.exists():
            shutil.copy2(p, nhin / p.name)
    print(f"\n-> {KQ / 'C_gian_khong_deu.txt'}\n-> video xem thử: {nhin}")
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        try:
            if SB.exists() and SB.name == "_sb_gian":
                shutil.rmtree(SB, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
    sys.exit(rc)
