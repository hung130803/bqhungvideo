# -*- coding: utf-8 -*-
"""BẢNG ĐO THẬT từng hiệu ứng + BẢNG MẪU CHO ANH HÙNG XEM (`--demo`).

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

Chạy ĐO   : .venv\\Scripts\\python _do_hieu_ung_bang.py [--lap 3] [--nho]
Chạy DEMO : .venv\\Scripts\\python _do_hieu_ung_bang.py --demo

=== CHẾ ĐỘ `--demo` — BẢNG MẪU anh Hùng XEM ĐƯỢC (anh hỏi 6 lần "hiệu ứng đâu") ===
Ra `D:\\hieu-ung-demo-v3\\`:
  `00_BANG_MAU_TAT_CA_HIEU_UNG.mp4` — MỖI hiệu ứng một ô 3,2 giây LIÊN TIẾP,
      **đốt TÊN TIẾNG VIỆT lên góc trên** + vạch đỏ "ĐANG CHẠY HIỆU ỨNG" hiện
      ĐÚNG lúc hiệu ứng nổ (anh không phải đoán chỗ nào mà nhìn). Ô đầu là GỐC
      không hiệu ứng để so. Cùng MỘT đoạn phim cho mọi ô -> thứ duy nhất đổi
      giữa 2 ô là hiệu ứng.
  4 clip THẬT xuất bằng ĐÚNG `export_canvas_clip` của app (AI tự chọn hiệu ứng
      theo cảnh), mỗi ca kèm bản `_TAT` để mở cạnh nhau mà so.
  `_ghi_chu.txt` — bảng "giây thứ mấy -> hiệu ứng gì -> VÌ SAO chọn".

2 điều BẮT BUỘC của bảng mẫu, đừng sửa mất:
1. Nhãn chữ phải vẽ **SAU** chuỗi hiệu ứng — vẽ trước thì `zoompan`/`rung_lac`
   phóng/lắc luôn cả chữ, trông như lỗi.
2. Chèn `fps=30` **TRƯỚC** chuỗi hiệu ứng: `zoompan` sinh lại mốc thời gian theo
   `fps` của nó; nguồn 29,97 mà zoompan ra 30 là ô đó lệch tiếng, và concat
   demuxer cũng cần mọi ô CÙNG fps.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np
import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

# Sandbox: KHÔNG đụng dữ liệu thật của anh Hùng (quy tắc sắt của repo). Đặt
# TRƯỚC khi `config` được nạp (hieu_ung/ffmpeg_utils nạp config bên trong hàm).
_SB = os.path.join(tempfile.gettempdir(), f"hu_demo_{os.getpid()}")
os.makedirs(_SB, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", _SB)
os.environ.setdefault("BQ_DB_PATH", os.path.join(_SB, "studio.db"))

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


# ======================================================================
#  BẢNG MẪU CHO ANH HÙNG XEM  (`--demo`)
# ======================================================================
RA_DEMO = r"D:\hieu-ung-demo-v3"
O_DAI = 3.2            # mỗi ô bao nhiêu giây (yêu cầu: 2-3 giây liên tiếp)
O_BAT = (0.60, 2.00)   # 2 lần nổ hiệu ứng trong ô -> anh Hùng KHÔNG thể bỏ lỡ
DEMO_FPS = 30


def _font_viet() -> str:
    """Font CÓ dấu tiếng Việt cho nhãn (Anton/Bungee KHÔNG đủ dấu -> ra ô vuông)."""
    d = os.path.join(ROOT, "app", "assets", "fonts")
    for ten in ("BeVietnamPro-Bold.ttf", "Montserrat-Bold.ttf", "Nunito.ttf",
                "Lexend.ttf"):
        p = os.path.join(d, ten)
        if os.path.exists(p):
            return p
    return _font()


def _dt(textfile: str, font: str, y: str, size: int, mau: str = "white",
        en: str = "") -> str:
    """1 mệnh đề drawtext đọc chữ TỪ FILE.

    Dùng `textfile=` chứ KHÔNG `text=`: nhãn tiếng Việt có dấu `:` `'` `(` `)`
    — nhét thẳng vào chuỗi filter là ffmpeg vỡ cú pháp (hoặc mất chữ im lặng).

    **`expansion=none` LÀ BẮT BUỘC — đừng gỡ.** LỖI THẬT 08/08/2026: mặc định
    `drawtext` chạy `expansion=normal`, coi `%` là mở đầu hàm `%{...}`; gặp `%`
    trơ nó **bỏ SẠCH chuỗi và VẪN trả rc=0**. Nhãn dòng 2 `… · đổi 16% khung
    hình` ra **0 pixel trong im lặng** -> cả 25 ô của bảng mẫu v3 mất dòng 2 mà
    không ai biết. Đo: cùng chuỗi, mặc định 0 px vs `expansion=none` 11.744 px;
    `'100%'` 0 px vs 1.512 px. (App thật KHÔNG dính vì
    `ffmpeg_utils._esc_drawtext` đã escape `%` -> `\\%`.)
    """
    f = font.replace("\\", "/").replace(":", "\\:")
    t = textfile.replace("\\", "/").replace(":", "\\:")
    s = (f"drawtext=fontfile='{f}':textfile='{t}':fontsize={size}:"
         f"fontcolor={mau}:borderw={VIEN_CHU}:bordercolor=black@0.9:"
         f"expansion=none:x=(w-text_w)/2:y={y}")
    if en:
        s += f":enable='{en}'"
    return s


# ======================================================================
#  LỖI ANH HÙNG BÁO #1 — NHÃN BỊ CẮT MẤT HAI ĐẦU
# ======================================================================
# Ảnh anh gửi: `...ỐC – KHÔNG HIỆU ỨNG (ô để so sá...`. Nguyên nhân: `_dt` đặt
# `fontsize` CỨNG rồi `x=(w-text_w)/2`; nhãn dài hơn 1080 thì `text_w > w` nên x
# ra ÂM -> chữ tràn CẢ HAI phía. ĐO ĐƯỢC TRƯỚC KHI SỬA (bản v3 cũ, ô 0 ở giây
# 1,5): **329 px chữ ở cột 0-8 + 103 px ở cột (w-8)-w**; 25 ô còn lại 0 px.
#
# SỬA: tự co cỡ chữ + tự xuống 2 dòng, và cỡ chữ do **ĐO BỀ RỘNG THẬT** quyết
# định. Đúng bài học cổng 31 "nút cụt chữ Hav/Nha": **số px cứng KHÔNG BAO GIỜ
# đúng** — phải đo lúc chạy. Ở đây đo bằng chính ffmpeg + đếm pixel (cùng bộ
# chữ, cùng libfreetype, cùng `borderw`), nên không phải PIL cũng không phải
# đếm ký tự (chữ có dấu tiếng Việt rộng khác chữ không dấu).
VIEN_CHU = 6           # borderw — TÍNH VÀO bề rộng, phải đo kèm
LE_NHAN = 26           # lề an toàn 2 bên: chữ KHÔNG được vào vùng này
Y_NHAN = 60            # đỉnh hộp nhãn
CO_REF = 100           # cỡ tham chiếu để suy tuyến tính (rồi kiểm lại bằng đo)
_BE_CHU: dict = {}


def _be_chu(txt: str, font: str, size: int) -> int:
    """Bề rộng THẬT (px) khi CHÍNH ffmpeg vẽ `txt` — render rồi ĐẾM PIXEL.

    Vẽ chữ TRẮNG + viền TRẮNG trên nền ĐEN ở canvas rất rộng (3840) rồi lấy
    khung bao của pixel sáng. Nhờ đo bằng đúng thứ sẽ vẽ ra bảng mẫu nên số này
    là số THẬT, không phải suy đoán. Có cache: mỗi (chữ, cỡ) chỉ render 1 lần.
    """
    key = (txt, font, size)
    if key in _BE_CHU:
        return _BE_CHU[key]
    td = tempfile.mkdtemp(prefix="_bechu_")
    ft, png = os.path.join(td, "t.txt"), os.path.join(td, "o.png")
    with open(ft, "w", encoding="utf-8") as fh:
        fh.write(txt)
    f = font.replace("\\", "/").replace(":", "\\:")
    t = ft.replace("\\", "/").replace(":", "\\:")
    subprocess.run(
        [_ff(), "-y", "-hide_banner", "-v", "error", "-f", "lavfi",
         "-i", f"color=c=black:s=3840x{max(300, size * 4)}", "-frames:v", "1",
         "-vf", f"drawtext=fontfile='{f}':textfile='{t}':fontsize={size}:"
                f"fontcolor=white:borderw={VIEN_CHU}:bordercolor=white:"
                f"expansion=none:x=200:y=60", png],
        capture_output=True, timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    w = 0
    im = cv2.imread(png)
    if im is not None:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        cot = np.where(g.max(axis=0) > 40)[0]
        if len(cot):
            w = int(cot[-1] - cot[0] + 1)
    shutil.rmtree(td, ignore_errors=True)
    _BE_CHU[key] = w
    return w


def _chia2(txt: str) -> list:
    """Cắt thành 2 dòng ở RANH TỪ, cân nhất theo số ký tự (không cắt giữa từ)."""
    tu = txt.split()
    if len(tu) < 2:
        return [txt]
    tot, lech = [txt], 10 ** 9
    for i in range(1, len(tu)):
        a, b = " ".join(tu[:i]), " ".join(tu[i:])
        if abs(len(a) - len(b)) < lech:
            tot, lech = [a, b], abs(len(a) - len(b))
    return tot


def _nhan_gon(txt: str, font: str, w_max: int, co_max: int,
              co_min: int = 30) -> tuple[list, int]:
    """(các dòng, cỡ chữ) sao cho MỌI dòng ĐO THẬT <= `w_max`. Không bao giờ tràn.

    Ưu tiên 1 DÒNG ở cỡ to; chỉ khi 1 dòng phải co nhỏ hơn `co_min` mới xuống
    2 dòng (2 dòng cho cỡ TO hơn nên dễ đọc hơn là co tí hon).
    """
    ket = []
    for dong in ([txt], _chia2(txt)):
        r = max(_be_chu(d, font, CO_REF) for d in dong) or 1
        co = max(10, min(co_max, int(CO_REF * w_max / r)))
        # KIỂM LẠI bằng ĐO THẬT ở cỡ đã chọn: suy tuyến tính không tuyệt đối
        # đúng (hinting/kerning làm lệch vài px) -> hạ dần tới khi VỪA. Đây là
        # chỗ bảo đảm BẤT BIẾN "không tràn", không phải phép chia ở trên.
        while co > 10 and max(_be_chu(d, font, co) for d in dong) > w_max:
            co -= 2
        if len(dong) == 1 and co >= co_min:
            return dong, co
        ket.append((dong, co))
    return max(ket, key=lambda x: x[1])


def _khoi_nhan(nhan1: str, nhan2: str, font: str, W: int, td: str,
               stt: int) -> tuple[str, int, list]:
    """Chuỗi drawtext của NHÃN + CHIỀU CAO hộp đen + DANH SÁCH (chữ, cỡ).

    Hộp đen cũng phải TỰ CO: cố định `h=200` thì nhãn 2 dòng tràn ra ngoài hộp,
    chữ nằm trên phim -> khó đọc.

    Trả thêm danh sách dòng để `_canh_nhan` soi được TỪNG DÒNG — cổng cũ chỉ
    đếm pixel TỔNG nên dòng 2 biến mất mà vẫn PASS oan (lỗi `%` 08/08/2026).
    """
    wmax = W - 2 * LE_NHAN
    d1, c1 = _nhan_gon(nhan1, font, wmax, 62)
    d2, c2 = _nhan_gon(nhan2, font, wmax, 40)
    dem, y, ra, ds = 0, Y_NHAN + 18, [], []
    for dong, co, mau in ((d1, c1, "white"), (d2, c2, "0xC8E6C9")):
        for s in dong:
            p = os.path.join(td, f"n_{stt}_{dem}.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(s)
            ra.append(_dt(p, font, str(y), co, mau))
            ds.append((s, co))
            y += int(co * 1.34)
            dem += 1
        y += 8
    return ",".join(ra), (y + 10) - Y_NHAN, ds


def _o_demo(src: str, moc: float, chain: str, nhan1: str, nhan2: str,
            dst: str, td: str, stt: int, en_hu: str) -> tuple[int, str]:
    """Render 1 Ô của bảng mẫu: phim + hiệu ứng + NHÃN + vạch "đang chạy".

    LỖI ANH HÙNG BÁO #2 — HÌNH BỊ PHÓNG TO. Bản cũ dựng ô bằng
    `scale=…:force_original_aspect_ratio=increase,crop=1080:1920` trên nguồn
    16:9 -> **cắt mất hai bên, phóng to nội dung**, đúng cái anh thấy. Bảng mẫu
    là để anh ĐÁNH GIÁ hiệu ứng nên phải thấy **TOÀN khung**: nay dùng
    `scale=1080:-2` (= `decrease`, không cắt một pixel nào) rồi ĐẶT GIỮA trên
    nền mờ — chính cách `export_canvas_clip(bg="blur")` của app làm, nên ô bảng
    mẫu trông y như clip app xuất thật.
    """
    font = _font_viet()
    f3 = os.path.join(td, "n3.txt")
    with open(f3, "w", encoding="utf-8") as fh:
        fh.write("ĐANG CHẠY HIỆU ỨNG")
    W, H = 1080, 1920
    bw, bh, br = W // 4, H // 4, max(2, 22 // 4)
    # fps TRƯỚC hiệu ứng (zoompan sinh lại mốc theo fps của nó) và trước split
    g = [f"[0:v]fps={DEMO_FPS},split=2[bv][fv]",
         f"[bv]scale={bw}:{bh}:force_original_aspect_ratio=increase,"
         f"crop={bw}:{bh},boxblur={br}:1,scale={W}:{H},setsar=1[base]",
         f"[fv]scale={W}:-2:flags=lanczos,setsar=1[fg]",
         "[base][fg]overlay=(W-w)/2:(H-h)/2[vv]"]
    cuoi = "[vv]"
    if chain:
        g.append(f"{cuoi}{chain}[vhu]")
        cuoi = "[vhu]"
    nhan, cao, _ds = _khoi_nhan(nhan1, nhan2, font, W, td, stt)
    # NHÃN vẽ SAU hiệu ứng -> chữ không bị zoom/lắc theo
    g.append(f"{cuoi}drawbox=x=0:y={Y_NHAN}:w={W}:h={cao}:color=black@0.62:"
             f"t=fill,{nhan},"
             f"drawbox=x=0:y={H - 190}:w={W}:h=120:color=red@0.75:t=fill"
             f":enable='{en_hu}',"
             + _dt(f3, font, str(H - 165), 52, "white", en_hu) + "[vout]")
    cmd = [_ff(), "-y", "-hide_banner", "-nostats", "-v", "error",
           "-ss", f"{moc:.3f}", "-t", f"{O_DAI:.3f}", "-i", src,
           "-filter_complex", ";".join(g), "-map", "[vout]", "-map", "0:a?",
           "-r", str(DEMO_FPS), "-fps_mode:v", "cfr",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2",
           "-b:a", "128k", dst]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       timeout=300,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return p.returncode, (p.stderr or "")[-400:]


def _canh_nhan(nhan1: str, nhan2: str, font: str, W: int, H: int, td: str,
               stt: int) -> tuple[int, int, int, int]:
    """CỔNG nhãn: render nhãn rồi ĐẾM PIXEL CHỮ ở cột 0-8 và (w-8)-w.

    Trả (px trái, px phải, px tổng, SỐ DÒNG TRỐNG). Có px ở mép = **FAIL** (chữ
    tràn); dòng trống > 0 cũng là **FAIL** (chữ mất im lặng).

    Vì sao render trên nền ĐEN chứ không trên khung phim thật: nền mờ của bảng
    mẫu có vùng SÁNG sát mép, đếm pixel sáng trên khung thật sẽ đếm cả PHIM ->
    **FAIL OAN** (đúng bẫy "ngưỡng đếm pixel phải theo TỈ LỆ" của cổng 36). Nhãn
    ở đây vẽ bằng ĐÚNG chuỗi filter mà bảng mẫu dùng, cùng font/cỡ/viền, nên
    hình học chữ là hình học THẬT — chỉ bỏ phim đi cho phép đo sạch.

    **CỔNG DÒNG-TRỐNG** (thêm 08/08/2026): mỗi dòng phải ĐO RA > 0 px. Cổng cũ
    chỉ nhìn pixel TỔNG nên dòng 2 bị `%` nuốt sạch mà vẫn báo "ok" — bảng mẫu
    v3 ra 26/26 ô "ĐẠT" trong khi 25 ô MẤT hẳn dòng 2. Đây đúng loại lỗi "test
    vẫn xanh, chỉ số đo tố giác".
    """
    nhan, cao, ds = _khoi_nhan(nhan1, nhan2, font, W, td, stt)
    trong = [s for s, co in ds if _be_chu(s, font, co) <= 0]
    png = os.path.join(td, f"canh_{stt}.png")
    subprocess.run(
        [_ff(), "-y", "-hide_banner", "-v", "error", "-f", "lavfi",
         "-i", f"color=c=black:s={W}x{H}", "-frames:v", "1", "-vf",
         f"drawbox=x=0:y={Y_NHAN}:w={W}:h={cao}:color=black@0.62:t=fill,{nhan}",
         png], capture_output=True, timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    im = cv2.imread(png)
    if im is None:
        return -1, -1, -1, len(ds)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    m = (g > 40).astype(np.uint8)
    return (int(m[:, :8].sum()), int(m[:, W - 8:].sum()), int(m.sum()),
            len(trong))


def _sang_va_dong(src: str, moc: float) -> tuple[float, float]:
    """Sáng TB + mức chuyển động của 3 giây tại `moc` — CHỌN MỐC, đừng đoán.

    Bài học đã sập: giây 20 của nguồn Nhật sáng TB chỉ 3,3/255 (gần đen) nên ca
    đếm pixel FAIL OAN. Mốc của bảng mẫu phải SÁNG và CÓ chuyển động, nếu không
    glitch/zoom trông như không có gì.
    """
    td = tempfile.mkdtemp(prefix="_moc_")
    fv = os.path.join(td, "v.txt")
    # `HU.duong_filter`: dấu `:` của ổ `C:` phải escape, không thì ffmpeg vỡ cú
    # pháp filter và trả 0 dòng -> "động 0.00" ở MỌI mốc (đã sập 1 lần).
    g = (f"fps=4,scale=160:-2,format=gray,tblend=all_mode=difference,"
         f"signalstats,metadata=print:key=lavfi.signalstats.YAVG:"
         f"file='{HU.duong_filter(fv)}'")
    subprocess.run([_ff(), "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc:.3f}", "-t", "3.0", "-i", src,
                    "-an", "-vf", g, "-f", "null", os.devnull],
                   capture_output=True, timeout=300,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    dong = 0.0
    try:
        import re
        with open(fv, encoding="utf-8", errors="replace") as fh:
            v = [float(m.group(1)) for m in
                 re.finditer(r"signalstats\.YAVG=([0-9.]+)", fh.read())]
        dong = max(v) if v else 0.0
    except OSError:
        pass
    shutil.rmtree(td, ignore_errors=True)
    d2 = os.path.join(tempfile.mkdtemp(prefix="_moc2_"), "a.png")
    subprocess.run([_ff(), "-y", "-hide_banner", "-v", "error",
                    "-ss", f"{moc + 1.5:.3f}", "-i", src, "-frames:v", "1",
                    d2], capture_output=True, timeout=300,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    sang = 0.0
    im = cv2.imread(d2)
    if im is not None:
        sang = float(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).mean())
    shutil.rmtree(os.path.dirname(d2), ignore_errors=True)
    return sang, dong


def _chon_moc(src: str, uv: tuple) -> float:
    """Mốc SÁNG NHẤT + ĐỘNG trong các ứng viên (in số ra để kiểm được)."""
    tot, diem = uv[0], -1.0
    for m in uv:
        s, d = _sang_va_dong(src, m)
        # cần SÁNG (>=45/255) rồi mới xét ĐỘNG
        dm = (min(s, 140.0) / 140.0) * 2.0 + min(d, 20.0) / 20.0
        print(f"    ứng viên giây {m:6.0f}: sáng {s:5.1f}/255 · động {d:5.2f}"
              f" -> điểm {dm:.2f}")
        if s >= 45.0 and dm > diem:
            tot, diem = m, dm
    return tot


#: 4 ca clip THẬT — xuất bằng ĐÚNG `export_canvas_clip` của app.
CA_THAT = [
    ("A_2doan_hookfirst", [(60.0, 70.0), (20.0, 30.0)], "vua",
     "2 ĐOẠN kiểu hook-first (đoạn 60-70s đứng TRƯỚC đoạn 20-30s, NGƯỢC thời "
     "gian) — cảnh app hay dùng nhất."),
    ("B_3doan_manh", [(60.0, 68.0), (20.0, 28.0), (120.0, 126.0)], "manh",
     "3 ĐOẠN, mức MẠNH — xem hiệu ứng ĐẬM NHẤT (25%, đúng trần) trông thế nào."),
    ("C_4doan_lienmach", [(300.0, 308.0), (309.0, 316.0), (316.5, 318.0),
                          (500.0, 512.0)], "nhe",
     "4 ĐOẠN, mức NHẸ — mức kín nhất, để anh xem mức nào vừa mắt."),
    ("D_1doan_dai", [(200.0, 218.0)], "vua",
     "1 ĐOẠN 18 giây (không có chỗ nối) — chứng minh AI chọn điểm nhấn theo "
     "TIẾNG + CHUYỂN ĐỘNG của chính cảnh, không phải cứ chỗ nối mới có."),
]


def _ass_dem_giay(dst: str, dai: float) -> str:
    """Phụ đề đếm giây — LỆCH tiếng/hình là thấy ngay bằng mắt, nhanh hơn số đo."""
    def hms(v: float) -> str:
        return f"{int(v // 3600)}:{int(v // 60) % 60:02d}:{v % 60:05.2f}"
    dong, t = [], 0.0
    while t < dai:
        dong.append(f"Dialogue: 0,{hms(t)},{hms(min(dai, t + 0.5))},D,,0,0,0,,"
                    "{\\an2}" + f"giay {t:.1f}")
        t += 0.5
    with open(dst, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\n"
                "PlayResY: 1920\n\n[V4+ Styles]\nFormat: Name,Fontname,"
                "Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
                "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,"
                "Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,"
                "MarginR,MarginV,Encoding\nStyle: D,Arial,96,&H00FFFFFF,"
                "&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,"
                "2,60,60,200,1\n\n[Events]\nFormat: Layer,Start,End,Style,"
                "Name,MarginL,MarginR,MarginV,Effect,Text\n"
                + "\n".join(dong) + "\n")
    return dst


def _dai_file(p: str) -> float:
    from config import settings
    r = subprocess.run([settings.FFPROBE_PATH, "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", p],
                       capture_output=True, text=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        return float((r.stdout or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1.0


def demo(src: str) -> int:
    """Dựng toàn bộ `D:\\hieu-ung-demo-v3` (bảng mẫu + 4 clip thật + ghi chú)."""
    os.makedirs(RA_DEMO, exist_ok=True)
    td = tempfile.mkdtemp(prefix="_bangmau_")
    do_cu: dict = {}
    try:
        with open(os.path.join(ROOT, "_ket_hieu_ung.json"), encoding="utf-8") as f:
            for r in json.load(f).get("ket", []):
                if r.get("khoa"):
                    do_cu[r["khoa"]] = r
    except (OSError, ValueError):
        pass

    print("[1/3] chọn mốc phim SÁNG + CÓ chuyển động cho bảng mẫu")
    moc = _chon_moc(src, (100.0, 200.0, 300.0, 420.0, 560.0))
    print(f"  -> dùng giây {moc:.0f}")
    en = "+".join(f"between(t,{b:.2f},{b + 0.85:.2f})" for b in O_BAT)

    dung = set(HU.dung_duoc(co_font=bool(_font_viet())))
    ke: list = [("__goc__", "GỐC — KHÔNG HIỆU ỨNG (ô để so sánh)", "")]
    for k, h in HU.KHO.items():
        if k in dung:
            ke.append((k, h.ten, h.capcut))
    print(f"[2/3] render {len(ke)} ô, mỗi ô {O_DAI}s "
          f"(hiệu ứng nổ 2 lần: giây {O_BAT[0]} và {O_BAT[1]})")

    o_files: list = []
    bang: list = []
    tran: list = []            # CỔNG nhãn: ô nào có chữ sát mép
    t_run = 0.0
    for i, (k, ten, cap) in enumerate(ke):
        chain = ""
        if k != "__goc__":
            h = HU.KHO[k]
            dam = HU.DAM_MAX          # bảng mẫu chiếu mức MẠNH NHẤT cho phép
            dai = max(HU.DAI_MIN, min(HU.DAI_MAX, h.dai))
            # 2 lần nổ = 2 bản sao chuỗi, mỗi bản gate 1 cửa sổ riêng
            chain = ",".join(
                h.chuoi(dam, b, b + dai, 1080, 1920, DEMO_FPS, _font_viet())
                for b in O_BAT)
        r = do_cu.get(k, {}).get("trong", {})
        n2 = (f"{i}/{len(ke) - 1}"
              + (f"  ·  CapCut: {cap}" if cap else "")
              + (f"  ·  đổi {r['pct']:.0f}% khung hình" if r.get("pct") else ""))
        # CỔNG NHÃN (lỗi #1 anh Hùng báo): ĐO trước khi render ô cho rẻ
        ptr, pph, ptong, mat = _canh_nhan(ten, n2, _font_viet(), 1080, 1920,
                                          td, i)
        if ptr or pph or ptong <= 0 or mat:
            tran.append((i, ten, ptr, pph, f"{mat} dòng trống"))
        dst = os.path.join(td, f"o{i:02d}.mp4")
        rc, log = _o_demo(src, moc, chain, ten, n2, dst, td, i, en)
        if rc != 0 or not os.path.exists(dst):
            print(f"  ô {i:02d} {ten:<30} ** LỖI ** {log.splitlines()[-1:]}")
            continue
        o_files.append(dst)
        bang.append((t_run, t_run + O_DAI, ten, cap, k,
                     r.get("pct", 0.0), HU.KHO[k].nhom if k in HU.KHO else "-"))
        t_run += O_DAI
        print(f"  ô {i:02d} giây {bang[-1][0]:6.1f}-{bang[-1][1]:5.1f}  "
              f"{ten:<28} nhãn mép L/R {ptr}/{pph} · {ptong} px · "
              f"{mat} dòng trống "
              f"{'** LỖI **' if (ptr or pph or mat) else 'ok'}")
    print(f"  CỔNG NHÃN: {len(ke) - len(tran)}/{len(ke)} ô đạt (không tràn mép,"
          f" không dòng trống)"
          + (f"  ** {len(tran)} Ô LỖI: {tran} **" if tran else "  (ĐẠT)"))

    lst = os.path.join(td, "ds.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in o_files:
            f.write("file '%s'\n" % p.replace("\\", "/"))
    bm = os.path.join(RA_DEMO, "00_BANG_MAU_TAT_CA_HIEU_UNG.mp4")
    p = subprocess.run([_ff(), "-y", "-hide_banner", "-v", "error", "-f",
                        "concat", "-safe", "0", "-i", lst, "-c", "copy", bm],
                       capture_output=True, text=True, errors="replace",
                       timeout=600,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode != 0:
        print("NỐI BẢNG MẪU LỖI:", (p.stderr or "")[-300:])
        return 2
    print(f"  -> {bm}  ({_dai_file(bm):.1f}s · "
          f"{os.path.getsize(bm) // 1024 // 1024} MB)")

    # ---------------- 4 clip THẬT qua ĐÚNG đường xuất của app ----------------
    print("[3/3] xuất 4 clip THẬT bằng `export_canvas_clip` (AI tự chọn)")
    from app.core import ffmpeg_utils as fu
    ghi_ca: list = []
    tyle_ca: list = []          # (tên ca, dài clip, giây CÓ hiệu ứng, %, số điểm)
    for ten, segs, muc, mota in CA_THAT:
        tong = sum(e - s for s, e in segs)
        ass = _ass_dem_giay(os.path.join(td, ten + ".ass"), tong)
        dong = [f"--- {ten} ---", mota,
                f"mốc cắt: {segs}  (tổng {tong:.1f}s) · mức hiệu ứng: {muc}"]
        d_tat = d_bat = -1.0
        for nhan, m in (("TAT", "tat"), (muc, muc)):
            out = os.path.join(RA_DEMO, f"{ten}_{nhan}.mp4")
            log: list = []
            t0 = time.time()
            try:
                fu.export_canvas_clip(
                    src, out, segs, (0.5, 0.42, 0.98), bg="blur",
                    out_w=1080, out_h=1920, ass_path=ass,
                    fx_fade=False, fx_whoosh=False, chuyen_canh="nhe",
                    hieu_ung=m, hieu_ung_log=log)
            except Exception as e:                       # noqa: BLE001
                print(f"  LỖI {ten} {nhan}: {type(e).__name__}: {e}")
                dong.append(f"  LỖI {nhan}: {e}")
                continue
            d = _dai_file(out)
            if nhan == "TAT":
                d_tat = d
            else:
                d_bat = d
            print(f"  {os.path.basename(out):34s} {d:7.3f}s "
                  f"{os.path.getsize(out) // 1024:7d} KB  "
                  f"wall {time.time() - t0:5.1f}s  · {len(log)} hiệu ứng")
            dong.append(f"  {os.path.basename(out)}: dài {d:.3f}s · "
                        f"{os.path.getsize(out) // 1024} KB · "
                        f"xuất {time.time() - t0:.1f}s")
            if log:
                dong.append("  BẢNG: giây thứ mấy -> hiệu ứng gì -> VÌ SAO chọn")
                for c in log:
                    h = HU.KHO.get(c["khoa"])
                    dong.append(
                        f"    giây {c['bat']:6.2f}-{c['het']:5.2f} | "
                        f"{(h.ten if h else c['khoa']):<26} | "
                        f"CapCut {(h.capcut if h else '-'):<18} | "
                        f"{c.get('vi_sao', '')}")
                # ANH HÙNG: *"tuỳ cái, cái nào cần thì hiện thôi"* -> phải CHỨNG
                # MINH BẰNG SỐ là hiệu ứng KHÔNG phủ clip. Mốc: > 10% thời lượng
                # là SAI THIẾT KẾ (giảm số điểm hoặc giảm `DAI_MAX`).
                cong = sum(float(c["het"]) - float(c["bat"]) for c in log)
                ty = cong / max(1e-9, d if d > 0 else tong) * 100.0
                dong.append(
                    f"  CHỐNG LOÈ (đo): clip dài {d:.2f}s · CÓ hiệu ứng "
                    f"{cong:.2f}s ({len(log)} điểm) · tỉ lệ {ty:.1f}% "
                    f"-> {'ĐẠT (<=10%)' if ty <= 10.0 else '** SAI THIẾT KẾ, PHẢI GIẢM **'}")
                tyle_ca.append((ten, d, cong, ty, len(log)))
        if d_tat > 0 and d_bat > 0:
            dong.append(f"  KIỂM LỆCH: TẮT {d_tat:.3f}s vs BẬT {d_bat:.3f}s "
                        f"-> lệch {abs(d_bat - d_tat) * 1000:.0f} ms "
                        f"({'ĐẠT' if abs(d_bat - d_tat) < 0.08 else 'KHÔNG ĐẠT'})")
        ghi_ca.append("\n".join(dong))

    # ------------------------------- ghi chú -------------------------------
    tk = HU.thong_ke()
    g = [
        "BẢNG MẪU HIỆU ỨNG — nhánh hieu-ung-video (nguồn: %s)" % os.path.basename(src),
        "=" * 78, "",
        "MỞ FILE NÀO TRƯỚC: `00_BANG_MAU_TAT_CA_HIEU_UNG.mp4`.",
        f"  · {len(bang) - 1} hiệu ứng, mỗi hiệu ứng MỘT Ô {O_DAI} giây liên tiếp.",
        "  · TÊN TIẾNG VIỆT đốt ở GÓC TRÊN của mỗi ô.",
        f"  · Trong mỗi ô, hiệu ứng NỔ 2 LẦN (giây {O_BAT[0]} và {O_BAT[1]} của ô)"
        " — lúc nổ có VẠCH ĐỎ 'ĐANG CHẠY HIỆU ỨNG' ở dưới đáy, anh nhìn vạch đó"
        " là biết đúng lúc nào mà xem.",
        "  · Ô số 0 là GỐC không hiệu ứng. Mọi ô dùng CÙNG MỘT đoạn phim (giây "
        f"{moc:.0f}) nên thứ duy nhất khác nhau giữa 2 ô là HIỆU ỨNG.",
        f"  · Bảng mẫu chiếu ở độ đậm MẠNH NHẤT ({HU.DAM_MAX:.0%} — trần luật "
        "chống loè). Trong app, mức 'nhẹ' chỉ 12%, 'vừa' 18%.",
        "  · **ĐÂY LÀ KHUNG XEM, KHÔNG PHẢI KHUNG XUẤT.** Bảng mẫu cố ý cho thấy"
        " TOÀN khung phim (không cắt một pixel nào) để anh đánh giá hiệu ứng;"
        " phần trên/dưới là nền mờ. Clip app xuất thật vẫn theo mẫu của anh.",
        "",
        "3 LỖI ĐÃ SỬA Ở BẢN NÀY — có số đo:",
        "  1) 'chữ bị cắt mất hai đầu': nhãn dài hơn khung 1080 nên tràn. Bản cũ"
        " đo được 329 px chữ ở mép TRÁI + 103 px ở mép PHẢI (ô 0). Nay cỡ chữ TỰ"
        " CO và tự xuống 2 dòng, cỡ do ĐO BỀ RỘNG THẬT bằng chính ffmpeg quyết"
        f" định. Cổng kiểm đếm pixel ở cột 0-8 và (w-8)-w: {len(bang)} ô,"
        f" **{len(tran)} ô lỗi**.",
        "  2) 'nó bị phóng to à': bản cũ dùng scale increase + crop nên CẮT MẤT"
        " hai bên. Nay scale decrease (giữ nguyên khung) + đặt giữa trên nền mờ.",
        "  3) (tôi tự tìm ra khi soi lại bản vừa xuất) DÒNG NHÃN THỨ 2 BIẾN MẤT ở"
        " cả 25 ô: ký tự '%' trong 'đổi 16% khung hình' làm ffmpeg bỏ sạch dòng"
        " đó mà KHÔNG báo lỗi. Đo: cùng chuỗi ra 0 px, sau khi sửa ra 11.744 px."
        " Nay mỗi DÒNG đều bị đếm pixel riêng, dòng nào 0 px là cổng báo lỗi.",
        "",
        "4 CLIP THẬT (xuất bằng ĐÚNG đường xuất của app, AI tự chọn hiệu ứng):",
        "  mỗi ca có 2 file — `*_TAT.mp4` (như bản đang chạy) và `*_<mức>.mp4`.",
        "  Mở cạnh nhau mà so. Phụ đề 'giay X.X' đốt vào hình: nếu hiệu ứng làm",
        "  LỆCH tiếng-hình thì số giây trên chữ sẽ không còn khớp giữa 2 file.",
        "",
        f"KHO: {tk['tong_kho']} hiệu ứng · dùng được trên máy này {tk['dung_duoc']}"
        f" ({tk['thuan']} thuần ffmpeg + {tk['frei0r']} frei0r)",
        "", "=" * 78,
        "BẢNG 1 — GIÂY THỨ MẤY TRONG BẢNG MẪU -> HIỆU ỨNG GÌ", "=" * 78,
        f"{'giây':>13}  {'tên tiếng Việt':<27}{'CapCut':<19}{'nhóm':<8}"
        f"{'đổi % khung':>12}",
    ]
    for a1, b1, ten, cap, k, pct, nhom in bang:
        # cắt cho VỪA cột, không thì bảng lệch hết (nhãn ô GỐC dài 36 ký tự)
        t27 = ten if len(ten) <= 26 else ten[:25] + "…"
        g.append(f"{a1:6.1f}-{b1:5.1f}  {t27:<27}{cap:<19}{nhom:<8}"
                 f"{(('%.0f%%' % pct) if pct else '-'):>12}")
    g += ["", "=" * 78,
          "BẢNG 2 — 4 CLIP THẬT: GIÂY THỨ MẤY -> HIỆU ỨNG GÌ -> VÌ SAO CHỌN",
          "=" * 78, ""]
    g += ghi_ca
    if tyle_ca:
        xau = [x for x in tyle_ca if x[3] > 10.0]
        g += ["", "=" * 78,
              'BẢNG 3 — "CÁI NÀO CẦN THÌ HIỆN THÔI": CHỨNG MINH BẰNG SỐ',
              "=" * 78,
              "Mốc thiết kế: tổng thời gian CÓ hiệu ứng phải <= 10% thời lượng",
              "clip. Vượt 10% là SAI THIẾT KẾ (loè), phải giảm.", "",
              f"{'ca':<20}{'clip dài':>10}{'có hiệu ứng':>13}{'số điểm':>9}"
              f"{'tỉ lệ':>8}   kết luận"]
        for ten, d, cong, ty, n in tyle_ca:
            g.append(f"{ten:<20}{d:9.2f}s{cong:12.2f}s{n:9d}{ty:7.1f}%   "
                     + ("ĐẠT" if ty <= 10.0 else "** SAI THIẾT KẾ **"))
        tb = sum(x[3] for x in tyle_ca) / len(tyle_ca)
        g += ["", f"Trung bình {tb:.1f}% thời lượng có hiệu ứng -> "
              + ("ĐẠT mốc 10%." if not xau else
                 f"** {len(xau)} ca VƯỢT 10%, PHẢI GIẢM **"),
              "Nói cách khác: hơn 90% thời lượng clip KHÔNG bị đụng gì. Cảnh TĨNH",
              "và đoạn không cao trào thì AI bỏ qua hẳn — xem cột 'vì sao' ở BẢNG 2,",
              "mỗi dòng đều có SỐ ĐO (âm ?x trung vị, động ?x trung vị)."]
    g += ["", "=" * 78, "LUẬT CHỌN (để anh đánh giá AI thông minh hay bừa)",
          "=" * 78,
          "AI KHÔNG bốc thăm. Nó đo TIẾNG (mức âm từng giây) + HÌNH (mức chuyển",
          "động từng giây) của CHÍNH clip sắp xuất, rồi xếp loại từng giây:",
          "  cao trào (tiếng vọt lên >=1,7x trung vị) -> zoom nhồi / rung lắc / loé sáng",
          "  cảnh động (hình đổi >=1,5x trung vị)     -> glitch khối / ô vuông vỡ / xáo dòng",
          "  cảnh TĨNH (hình gần đứng)                -> CHỈ mood: quầng sáng / hạt phim / tối viền",
          "                                              (KHÔNG BAO GIỜ zoom/rung/glitch)",
          "  câu chốt (3 giây cuối)                   -> sụp tối / nháy sáng",
          "  chỗ ghép đoạn                            -> mờ nét / loé sáng / đếm ngược",
          "4 luật chống loè: mỗi lần <=0,8 giây · độ đậm <=25% · lệch màu da U/V",
          "phải <3 (vượt là TỰ BỎ hiệu ứng đó) · mỗi clip tối đa 3 điểm nhấn.",
          ]
    with open(os.path.join(RA_DEMO, "_ghi_chu.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(g) + "\n")
    shutil.rmtree(td, ignore_errors=True)
    print(f"\nXONG. Mở: {bm}")
    print(f"Ghi chú: {os.path.join(RA_DEMO, '_ghi_chu.txt')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lap", type=int, default=1)
    ap.add_argument("--nho", action="store_true", help="540x960 cho nhanh")
    ap.add_argument("--json", default="_ket_hieu_ung.json")
    ap.add_argument("--demo", action="store_true",
                    help="dựng BẢNG MẪU cho anh Hùng xem (D:\\hieu-ung-demo-v3)")
    a = ap.parse_args()
    if a.demo:
        s = _nguon_nhat.mot("JP")
        if not s:
            print("KHONG CO nguon Nhat")
            return 2
        print(f"[nguồn] {os.path.basename(s)}")
        print(f"[frei0r] {HU.co_frei0r()} — {HU.thu_muc_frei0r()}")
        return demo(s)
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
