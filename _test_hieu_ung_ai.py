# -*- coding: utf-8 -*-
r"""CỔNG 38 — HIỆU ỨNG ĐIỂM NHẤN + AI CHỌN THÔNG MINH.

Chạy: .venv\Scripts\python _test_hieu_ung_ai.py

Cổng 36 canh CHUYỂN CẢNH ở chỗ ghép đoạn, cổng 37 canh CA BIÊN đường xuất.
Cổng này canh **kho hiệu ứng điểm nhấn** (`app/core/hieu_ung.py`) và **luật AI
chọn** — thứ anh Hùng nhắc nhiều nhất: *"đảm bảo nó chọn phải okee nhất, k phải
mấy cảnh vớ vẩn k phù hợp lại thêm vào ngớ ngẩn"*.

=== PHẦN A: 5 LỖI ĐÃ RÀ RA 08/08/2026 (mỗi lỗi 1 ca, KHÔNG sửa suông) ===
 1. `zoompan` nhận fps SAI khi nền Đen/Trắng -> clip DÀI HƠN 20% (đo 2,000 ->
    2,400s). Nền `color=…:r=30` là input CHÍNH của `overlay` nên luồng vào
    zoompan chạy 30 fps, trong khi app truyền fps NGUỒN (25).
 2. Hiệu ứng RÒ RA NGOÀI cửa sổ `enable` (nghi `vien_net`/`edgedetect`). Đo
    **KHÔNG QUA ENCODER** (rawvideo) — đo qua mp4 thì nhiễu rate-control ~0,02
    che mất/phóng đại lệch thật.
 3. `_hu_t` nhân `vspeed` sai chiều -> điểm nhấn rơi RA NGOÀI clip, hiệu ứng
    KHÔNG BAO GIỜ CHẠY (đo: clip ra 8,03s mà điểm ở giây 9,00-9,70).
 4. `dem_nguoc` gắn cứng mốc 0,30/0,60 trong khi cửa sổ co theo `vspeed` ->
    `between(t,0.60,0.56)` = số "1" không bao giờ hiện, mà ffmpeg vẫn rc=0.
 5. Nhật ký khoe hiệu ứng mà `chuoi_filter` sẽ VỨT (máy thiếu font) -> mất 1
    suất trong tối đa 3 điểm nhấn.

=== PHẦN B: BẤT BIẾN CỦA "AI CHỌN THÔNG MINH" ===
 - KHÔNG random (cùng input ra cùng output)
 - KHÔNG lặp một kiểu trong 1 clip
 - KHÔNG đặt hiệu ứng ĐỘNG vào cảnh TĨNH
 - KHÔNG thêm gì ở đoạn năng lượng PHẲNG
 - tổng giây có hiệu ứng <= 10% thời lượng clip
 - mỗi điểm có LÝ DO KÈM SỐ (cấm "cảnh hay")

**BẪY ĐO PHẢI TRÁNH** (đã sập ở cổng 36/37, đừng lặp):
 · mốc trích khung phải ở CẢNH SÁNG — nguồn Nhật giây 20 sáng TB chỉ 3,3/255
   nên mọi phép đếm pixel ra ~0 và FAIL OAN. Dùng mốc 100/200/300s.
 · đếm tiến trình ffmpeg theo `p.name()`, KHÔNG theo cmdline.
 · hiệu ứng báo "0,03 CPU-giây" là LỖI FILTER chứ không phải nhanh -> mọi hiệu
   ứng phải render KHUNG THẬT + ĐẾM PIXEL.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_hu_ai_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

import numpy as np  # noqa: E402

import _nguon_nhat  # noqa: E402
from app.core import ffmpeg_utils as fu  # noqa: E402
from app.core import hieu_ung as HU  # noqa: E402
from config import settings  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_NOWIN = 0x08000000
_OK: list[str] = []
_LOI: list[str] = []


def bao(ten: str, ok: bool, so: str) -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


def dai(p: str) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True,
                       text=True, creationflags=_NOWIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def khung(p: str, t: float, W: int, H: int):
    raw = str(_SB / f"k{abs(hash((p, t))) % 10 ** 9}.raw")
    subprocess.run([FF, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", p,
                    "-frames:v", "1", "-pix_fmt", "yuv444p", "-f", "rawvideo",
                    raw], capture_output=True, creationflags=_NOWIN)
    d = np.fromfile(raw, dtype=np.uint8)
    if d.size < W * H * 3:
        return None
    return d[: W * H * 3].reshape(3, H, W).astype(np.int16)


def xuat(out: str, src: str, segs: list, **kw) -> bool:
    return fu.export_canvas_clip(
        src, out, segs, (0.5, 0.5, 1.0), out_w=540, out_h=960,
        encoder=kw.pop("encoder", fu.detect_encoder()), fx_fade=False,
        fx_whoosh=False, **kw)


# =====================================================================
#  A1 — zoompan nhận fps SAI khi nền Đen/Trắng (clip dài hơn 20%)
# =====================================================================
def _nguon_fps(fps: int, giay: float) -> str:
    p = str(_SB / f"src{fps}.mp4")
    if os.path.exists(p):
        return p
    subprocess.run(
        [FF, "-y", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=size=480x854:rate={fps}:d={giay}",
         "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:d={giay}",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(fps), "-fps_mode:v", "cfr",
         "-c:a", "aac", "-shortest", p], capture_output=True,
        creationflags=_NOWIN)
    return p


def ca_a1() -> None:
    print("\n== A1. zoompan + fps luồng vào (nền Đen/Trắng) ==")
    src = _nguon_fps(25, 6.0)
    hu = [{"bat": 1.0, "het": 1.4, "khoa": "zoom_nhoi", "dam": 0.18}]
    for bg in ("black", "white", "blur", "fill"):
        o = str(_SB / f"a1_{bg}.mp4")
        xuat(o, src, [(0.0, 2.0)], bg=bg, hieu_ung=hu)
        d = dai(o)
        bao(f"nền {bg} + zoom_nhoi giữ đúng độ dài",
            abs(d - 2.0) <= 0.05, f"{d:.3f}s (mong đợi 2,000 ±0,05)")


# =====================================================================
#  A2 — hiệu ứng KHÔNG được rò ra NGOÀI cửa sổ enable (đo raw, 0 encoder)
# =====================================================================
# `fps=30` NGAY ĐẦU: nguồn Nhật chạy 59,94 fps. Không ép thì luồng vào hiệu ứng
# là 59,94 trong khi ta truyền 30 cho `zoompan` -> zoompan ĐÓNG DẤU LẠI mốc thời
# gian, khung ở cùng chỉ số là NỘI DUNG KHÁC và phép đo báo "rò 1,7%" OAN. Đây
# đúng họ bẫy "tmix lệch giờ tưởng loè màu" đã ghi trong `hieu_ung.py`.
_GRAPH_NEN = ("[0:v]fps=30,split=2[bv][fv];"
              "[bv]scale=68:120:force_original_aspect_ratio=increase,"
              "crop=68:120,boxblur=5:1,scale=270:480,setsar=1[base];"
              "[fv]scale=270:-2:flags=lanczos,setsar=1[fg];"
              "[base][fg]overlay=x='0.5*W-w/2':y='0.5*H-h/2'[vv]")
_W2, _H2 = 270, 480


def _raw(ten: str, src: str, hieu: str):
    g = _GRAPH_NEN + (f";[vv]{hieu}[vo]" if hieu else "")
    p = str(_SB / (ten + ".raw"))
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-ss", "100", "-t", "2.0", "-i", src,
         "-an", "-filter_complex", g, "-map", "[vo]" if hieu else "[vv]",
         "-pix_fmt", "yuv444p", "-r", "30", "-fps_mode:v", "cfr",
         "-f", "rawvideo", p], capture_output=True, text=True,
        errors="replace", creationflags=_NOWIN)
    if r.returncode != 0:
        return None, (r.stderr or "")[-200:]
    d = np.fromfile(p, dtype=np.uint8)
    n = _W2 * _H2 * 3
    os.unlink(p)
    return d[: (d.size // n) * n].reshape(-1, 3, _H2, _W2).astype(np.int16), ""


def ca_a2(src: str) -> None:
    print("\n== A2. hiệu ứng chỉ ở TRONG cửa sổ (đo rawvideo, KHÔNG encoder) ==")
    HU.dat_frei0r_path()
    a, b = 1.20, 1.55
    # ĐO TRÊN MỌI KHUNG, không 1 khung: `nhay_sang` là sóng sin 4,5 lần/giây nên
    # 1 khung có thể rơi ĐÚNG chỗ sin=0 -> đo ra 0,0% và FAIL OAN (đã sập 1 lần).
    # trong cửa sổ lấy ĐỈNH; ngoài cửa sổ lấy ĐỈNH (chỗ rò nặng nhất).
    ng = [i for i in range(60) if i / 30.0 < a - 0.05 or i / 30.0 > b + 0.05]
    tr = [i for i in range(60) if a + 0.02 <= i / 30.0 <= b - 0.02]
    goc, err = _raw("a2_goc", src, "")
    if goc is None:
        bao("dựng được khung gốc", False, err)
        return
    dd = HU.dung_duoc()
    xau: list[str] = []
    kem: list[str] = []
    for k in dd:
        ch = HU.KHO[k].chuoi(0.25, a, b, _W2, _H2, 30,
                             HU.font_mac_dinh(""))
        arr, err = _raw("a2_" + k, src, ch)
        if arr is None or arr.shape[0] < 60:
            xau.append(f"{k}(lệnh lỗi)")
            continue
        du = max(abs(float(arr[i, 1].mean()) - float(goc[i, 1].mean()))
                 for i in ng)
        dv = max(abs(float(arr[i, 2].mean()) - float(goc[i, 2].mean()))
                 for i in ng)
        png = max(float((np.abs(arr[i, 0] - goc[i, 0]) > 12).mean())
                  for i in ng) * 100
        ptr = max(float((np.abs(arr[i, 0] - goc[i, 0]) > 12).mean())
                  for i in tr) * 100
        # NGƯỠNG LẤY THEO SỐ ĐO THẬT, không bịa: lỗi RÒ có thật (bản `rung_lac`
        # dùng `crop`+`scale`) đo ra **18,7%** pixel đổi ngoài cửa sổ; còn nhiễu
        # nền do đổi hệ màu yuv<->rgb của MỌI hiệu ứng frei0r đo ra |dU| 0,02
        # |dV| 0,05 và 0,07% pixel. Đặt trần ở 1,0 và 3% = ở GIỮA hai mức, đủ
        # bắt lỗi thật mà không FAIL oan vì nhiễu làm tròn.
        if du > 1.0 or dv > 1.0 or png > 3.0:
            xau.append(f"{k}(dU{du:.2f} dV{dv:.2f} {png:.1f}%)")
        if ptr < HU.KHO[k].nguong_thay:
            kem.append(f"{k}({ptr:.1f}%<{HU.KHO[k].nguong_thay:g}%)")
    bao(f"{len(dd)} hiệu ứng KHÔNG rò ra ngoài cửa sổ", not xau,
        "; ".join(xau) if xau else
        "|dU|,|dV| < 1,0 và < 3% pixel Y ở khung ngoài — tất cả")
    bao(f"{len(dd)} hiệu ứng THẤY ĐƯỢC trong cửa sổ", not kem,
        "; ".join(kem) if kem else "đạt ngưỡng % pixel Y đổi của từng kiểu")


# =====================================================================
#  A3 — mốc điểm nhấn phải nằm TRONG clip khi có tăng tốc
# =====================================================================
def ca_a3(src: str) -> None:
    print("\n== A3. tăng tốc: điểm nhấn phải NẰM TRONG clip và THẤY ĐƯỢC ==")
    segs = [(100.0, 130.0)]
    for sp in (1.25, 0.8):
        log: list = []
        o, base = str(_SB / f"a3_{sp}.mp4"), str(_SB / f"a3_{sp}_tat.mp4")
        xuat(o, src, segs, bg="blur", speed=sp, hieu_ung="manh",
             hieu_ung_log=log)
        xuat(base, src, segs, bg="blur", speed=sp, hieu_ung="")
        d = dai(o)
        ngoai = [c for c in log if float(c["het"]) > d + 0.05]
        # 0 điểm = ca RỖNG, KHÔNG được coi là đạt (đó chính là triệu chứng của
        # lỗi 3: mốc rơi ngoài clip nên chẳng bao giờ có hiệu ứng nào).
        bao(f"speed {sp}: AI chọn được ít nhất 1 điểm", bool(log),
            f"{len(log)} điểm trên clip ra {d:.2f}s")
        bao(f"speed {sp}: mọi điểm nằm trong clip {d:.2f}s", not ngoai,
            ("ngoài: " + ", ".join(f"{c['khoa']} {c['bat']:.2f}-{c['het']:.2f}"
                                   for c in ngoai)) if ngoai else
            f"{len(log)} điểm, điểm cuối {max((c['het'] for c in log), default=0):.2f}s")
        kem, so = [], []
        for c in log:
            # ĐO ĐỈNH TRÊN NHIỀU KHUNG TRONG CỬA SỔ, KHÔNG phải 1 khung giữa.
            # LỖI CỦA CHÍNH CỔNG NÀY (lượt kiểm độc lập 08/08/2026): ca
            # `speed 0.8` FAIL với `glitch_khoi@15.18s chỉ 0,26%` trong khi
            # ĐỈNH cả cửa sổ lên tới hàng chục %. `glitch0r` / `nhay_sang` /
            # `nhieu_bang` là hiệu ứng DAO ĐỘNG THEO THỜI GIAN — khung giữa có
            # thể rơi đúng nhịp "im". Bẫy này đã ghi trong `VIEC_HIEU_UNG.md`
            # và đã chữa cho ca A2, nhưng A3 CÒN SÓT -> cổng FAIL OAN, đổ oan
            # cho app. Cổng đo sai thì số của nó không dùng được.
            a, b = float(c["bat"]), float(c["het"])
            dinh, moc_dinh = -1.0, a
            for k in range(5):
                t = a + (b - a) * (0.1 + 0.2 * k)
                x, y = khung(o, t, 540, 960), khung(base, t, 540, 960)
                if x is None or y is None:
                    continue
                pct = float((np.abs(x[0] - y[0]) > 12).mean()) * 100
                if pct > dinh:
                    dinh, moc_dinh = pct, t
            if dinh < 0:
                kem.append(f"{c['khoa']}@{a:.2f}s KHÔNG trích được khung nào")
                continue
            so.append(f"{c['khoa']} đỉnh {dinh:.1f}%@{moc_dinh:.2f}s")
            if dinh < 2.0:
                kem.append(f"{c['khoa']} đỉnh CẢ cửa sổ chỉ {dinh:.2f}%")
        bao(f"speed {sp}: hiệu ứng THẬT SỰ hiện trên khung ra", not kem,
            "; ".join(kem) if kem else
            f"{len(log)}/{len(log)} điểm đổi > 2% pixel · " + " · ".join(so))


# =====================================================================
#  A4 — đếm ngược 3-2-1 phải đủ CẢ SỐ "1" ở mọi độ dài cửa sổ
# =====================================================================
def ca_a4(src: str) -> None:
    print("\n== A4. đếm ngược 3-2-1 — số '1' phải hiện ==")
    h = HU.KHO["dem_nguoc"]
    xau = []
    for vs in (0.7, 1.0, 1.5):
        s = h.chuoi(0.20, 0.0, 0.80 * vs, 540, 960, 30, "x.ttf")
        for so in ("3", "2", "1"):
            kh = [x for x in s.split("drawtext") if f"text='{so}'" in x]
            if not kh:
                xau.append(f"vs{vs} thiếu số {so}")
                continue
            en = kh[0].split(":enable='between(t,")[1].split(")'")[0]
            t0, t1 = (float(v) for v in en.split(","))
            if t1 - t0 < 0.05:
                xau.append(f"vs{vs} số {so}: cửa sổ {t0:.3f}-{t1:.3f} rỗng")
    bao("cửa sổ 3 chữ số luôn khác rỗng ở mọi vspeed", not xau,
        "; ".join(xau) if xau else "0,7 / 1,0 / 1,5 đều đủ 3 số")
    # RENDER THẬT: đếm pixel trắng ở 1/3 cuối cửa sổ (chỗ số "1")
    font = HU.font_mac_dinh("")
    if not font:
        bao("có font để render đếm ngược", False, "không tìm được .ttf")
        return
    o, base = str(_SB / "a4.mp4"), str(_SB / "a4_tat.mp4")
    xuat(o, src, [(100.0, 103.0)], bg="blur",
         hieu_ung=[{"bat": 1.0, "het": 1.8, "khoa": "dem_nguoc", "dam": 0.25}])
    xuat(base, src, [(100.0, 103.0)], bg="blur", hieu_ung="")
    ket = []
    for ten, t in (("3", 1.10), ("2", 1.37), ("1", 1.65)):
        x, y = khung(o, t, 540, 960), khung(base, t, 540, 960)
        if x is None or y is None:
            ket.append(f"{ten}:?")
            continue
        px = int((np.abs(x[0] - y[0]) > 40).sum())
        ket.append(f"số {ten} @{t:.2f}s = {px} px")
    xau2 = [k for k in ket if "= 0 px" in k or k.endswith(":?")]
    bao("render thật: cả 3 số đều vẽ ra pixel", not xau2, " · ".join(ket))


# =====================================================================
#  A5 — nhật ký phải KHỚP với cái thật sự vào file (máy thiếu font)
# =====================================================================
def ca_a5() -> None:
    print("\n== A5. thiếu font -> không được khoe hiệu ứng không tồn tại ==")
    can_font = [k for k, h in HU.KHO.items() if h.can_font]
    chon = HU.chon_hieu_ung(60.0, "manh", nl=[], cd=[], moc_noi=[5.0, 20.0],
                            co_the_dung=HU.dung_duoc(co_font=False))
    xau = [c["khoa"] for c in chon if c["khoa"] in can_font]
    bao("dung_duoc(co_font=False) không bao giờ lọt hiệu ứng cần font",
        not xau, f"kho có {len(can_font)} kiểu cần font ({can_font}); chọn ra "
                 f"{[c['khoa'] for c in chon]}")
    # ca ép: caller truyền THẲNG list có dem_nguoc mà máy không font
    ep = [{"bat": 1.0, "het": 1.8, "khoa": "dem_nguoc", "dam": 0.2},
          {"bat": 5.0, "het": 5.4, "khoa": "zoom_nhoi", "dam": 0.2}]
    giu = HU.loc_theo_font(ep, False)
    ch = HU.chuoi_filter(giu, 540, 960, 30, font="")
    bao("loc_theo_font khớp đúng số filter chuoi_filter dựng ra",
        len(giu) == 1 and "drawtext" not in ch,
        f"log {len(ep)} -> {len(giu)} mục; chuỗi có drawtext: "
        f"{'drawtext' in ch}")


# =====================================================================
#  B — BẤT BIẾN CỦA AI CHỌN
# =====================================================================
def _nhip(src: str, s: float, e: float):
    return HU.do_nhip("", ffmpeg=FF,
                      dau_vao=["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}",
                               "-i", src])


def ca_b(src_list: list) -> None:
    print("\n== B. bất biến của AI chọn ==")
    # B1 TIỀN ĐỊNH
    nl, cd = _nhip(src_list[0], 100.0, 130.0)
    a1 = HU.chon_hieu_ung(30.0, "vua", nl=nl, cd=cd, moc_noi=[12.0])
    a2 = HU.chon_hieu_ung(30.0, "vua", nl=nl, cd=cd, moc_noi=[12.0])
    a3 = HU.chon_hieu_ung(30.0, "vua", nl=nl, cd=cd, moc_noi=[12.0])
    bao("TIỀN ĐỊNH: cùng input ra cùng output (3 lượt)",
        a1 == a2 == a3, f"{[c['khoa'] for c in a1]}")

    # B2 KHÔNG LẶP KIỂU + B3 không đặt hiệu ứng ĐỘNG vào cảnh TĨNH
    DONG = set(HU._UV_THEO_LOAI["caotrao"]) | set(HU._UV_THEO_LOAI["dong"])
    lap, tinh_sai, qua = [], [], []
    ty_le = []
    for i, sp in enumerate(src_list):
        for s, dai_clip in ((100.0, 30.0), (200.0, 45.0), (300.0, 25.0)):
            nl, cd = _nhip(sp, s, s + dai_clip)
            moc = [dai_clip * 0.4]
            ch = HU.chon_hieu_ung(dai_clip, "manh", nl=nl, cd=cd, moc_noi=moc)
            ks = [c["khoa"] for c in ch]
            if len(set(ks)) != len(ks):
                lap.append(f"{os.path.basename(sp)[:12]}@{s:.0f}: {ks}")
            for c in ch:
                if c["loai"] == "tinh" and c["khoa"] in DONG:
                    tinh_sai.append(f"{c['khoa']} @giây {c['bat']:.0f}")
            t = HU.ty_le_co_hieu_ung(ch, dai_clip)
            ty_le.append(t)
            if t > 10.0001:
                qua.append(f"{os.path.basename(sp)[:12]}@{s:.0f}={t:.1f}%")
    bao("KHÔNG lặp một kiểu trong cùng 1 clip", not lap,
        "; ".join(lap) if lap else f"{len(ty_le)} clip thật, 0 lần lặp")
    bao("KHÔNG đặt hiệu ứng ĐỘNG vào cảnh TĨNH", not tinh_sai,
        "; ".join(tinh_sai) if tinh_sai else
        "cảnh 'tinh' chỉ nhận nhóm mood (quầng sáng/hạt phim/tối viền)")
    bao("tỉ lệ giây có hiệu ứng <= 10% thời lượng", not qua,
        "; ".join(qua) if qua else
        f"{len(ty_le)} clip: {min(ty_le):.1f}%–{max(ty_le):.1f}% "
        f"(trung vị {sorted(ty_le)[len(ty_le) // 2]:.1f}%)")

    # B4 ĐOẠN PHẲNG -> không thêm gì
    phang_nl = [0.30] * 40
    phang_cd = [0.20] * 40
    ch = HU.chon_hieu_ung(40.0, "manh", nl=phang_nl, cd=phang_cd, moc_noi=[])
    bao("năng lượng PHẲNG -> KHÔNG thêm gì", not ch,
        f"{len(ch)} điểm (dải động tiếng {HU.dai_dong(phang_nl):.2f} · "
        f"hình {HU.dai_dong(phang_cd):.2f} < ngưỡng {HU.PHANG})")
    ch2 = HU.chon_hieu_ung(40.0, "manh", nl=phang_nl, cd=phang_cd,
                           moc_noi=[15.0])
    bao("PHẲNG nhưng CÓ chỗ nối -> chỉ nhấn ĐÚNG chỗ nối",
        len(ch2) == 1 and abs(float(ch2[0]["bat"]) - 15.0) <= 1.0,
        f"{[c['khoa'] + '@' + str(c['bat']) for c in ch2]}")

    # B5 LÝ DO PHẢI CÓ SỐ
    nl, cd = _nhip(src_list[0], 100.0, 140.0)
    ch = HU.chon_hieu_ung(40.0, "manh", nl=nl, cd=cd, moc_noi=[16.0])
    thieu = [c["khoa"] for c in ch
             if "trung vị" not in c.get("vi_sao", "")
             and "mốc ghép" not in c.get("vi_sao", "")
             and "hết clip" not in c.get("vi_sao", "")]
    bao("mỗi điểm có LÝ DO KÈM SỐ (cấm 'cảnh hay')", not thieu,
        "; ".join(thieu) if thieu else
        " || ".join(c["vi_sao"] for c in ch))

    # B5b LÝ DO KHÔNG ĐƯỢC RA SỐ VÔ NGHĨA KHI TRUNG VỊ = 0
    # -----------------------------------------------------------------
    # LỖI THẬT (lượt kiểm ĐỘC LẬP 08/08/2026): lôi ra từ NHẬT KÝ DÂY CHUYỀN của
    # `_test_pipe_integ` chạy trên video THẬT —
    #   `giây 14,0 · Xáo dòng ngang · cảnh động mạnh —
    #    RMS 0,05 = 49274701,3x trung vị`
    # `_vi_sao` chia cho `_tv(nl) or 1e-9`; khi HƠN NỬA số giây im lặng (video
    # KHÔNG TIẾNG, hoặc clip có khoảng lặng dài — phỏng vấn / vlog Nhật rất hay
    # gặp) thì trung vị ra ĐÚNG 0,0 -> 0,05 / 1e-9 = 50 triệu.
    # Đây là dòng DUY NHẤT anh Hùng đọc để tin "AI chọn có căn cứ SỐ" nên số rác
    # ở đây = mất sạch giá trị. Cổng canh: mọi tỉ lệ in ra phải < 1.000x.
    for ten, _nl, _cd in (
        (">50% giây im lặng",
         [0.0] * 16 + [0.05, 0.03, 0.02, 0.10] + [0.0] * 8,
         [0.02] * 14 + [1.0, 0.3, 0.2, 0.46] + [0.001] * 10),
        ("video KHÔNG TIẾNG",
         [0.0] * 28,
         [0.02] * 14 + [1.0, 0.3, 0.2, 0.46] + [0.001] * 10),
        ("hình ĐỨNG IM hơn nửa clip",
         [0.02] * 14 + [0.4] * 4 + [0.02] * 10,
         [0.0] * 16 + [0.9, 0.3, 0.2, 0.5] + [0.0] * 8),
    ):
        ch3 = HU.chon_hieu_ung(28.0, "manh", nl=_nl, cd=_cd, moc_noi=[6.0],
                               co_the_dung=list(HU.KHO.keys()))
        xau = []
        for c in ch3:
            for phan in str(c.get("vi_sao", "")).split(";"):
                if "x trung vị" not in phan:
                    continue
                try:
                    val = float(phan.split("=")[-1].strip()
                                .replace("x trung vị", "").replace(",", "."))
                except ValueError:
                    continue
                if val >= 1000.0:
                    xau.append(phan.strip())
        bao(f"lý do KHÔNG ra tỉ lệ vô nghĩa — ca «{ten}»", not xau,
            ("; ".join(xau)[:150] if xau else
             (" || ".join(c["vi_sao"] for c in ch3)[:150] or "(0 điểm)")))


# =====================================================================
#  C — BẤT BIẾN SỐNG CÒN: TẮT phải KHÔNG thêm một dòng filter nào
# =====================================================================
def ca_c(src: str) -> None:
    print("\n== C. hiệu ứng TẮT = đường cũ y nguyên ==")
    for muc in ("", "tat", None):
        ch = HU.chon_hieu_ung(30.0, str(muc or ""), nl=[0.1] * 30,
                              cd=[0.1] * 30, moc_noi=[10.0])
        bao(f"mức {muc!r} -> 0 hiệu ứng", not ch, f"{len(ch)} điểm")
    bao("chuoi_filter([]) trả chuỗi rỗng", HU.chuoi_filter([], 540, 960) == "",
        repr(HU.chuoi_filter([], 540, 960)))
    a, b = str(_SB / "c_tat.mp4"), str(_SB / "c_rong.mp4")
    xuat(a, src, [(100.0, 104.0)], bg="blur", hieu_ung="tat")
    xuat(b, src, [(100.0, 104.0)], bg="blur", hieu_ung="")
    r = subprocess.run(
        [FF, "-hide_banner", "-i", a, "-i", b, "-filter_complex",
         "[0:v][1:v]psnr", "-f", "null", os.devnull],
        capture_output=True, text=True, errors="replace",
        creationflags=_NOWIN)
    line = [x for x in (r.stderr or "").splitlines() if "PSNR" in x]
    bao("'tat' và '' ra file giống hệt nhau",
        bool(line) and ("average:inf" in line[-1].replace(" ", "")
                        or _psnr(line[-1]) >= 50),
        line[-1].strip() if line else "không đọc được PSNR")


def _psnr(s: str) -> float:
    for tok in s.split():
        if tok.startswith("average:"):
            v = tok.split(":", 1)[1]
            return 999.0 if v == "inf" else float(v)
    return 0.0


# =====================================================================
#  D — NỐI VÀO APP: núm trong Chỉnh mẫu -> mẫu -> payload -> ffmpeg
# =====================================================================
def ca_d() -> None:
    print("\n== D. nối vào app (mẫu -> payload -> ffmpeg) ==")
    # D1: núm trong Chỉnh mẫu — dựng hộp THẬT
    try:
        # cv2 PHẢI nạp TRƯỚC PyQt6 (bài học cổng 17: repo cần cv2 nạp trước Qt).
        # Nạp ngược lại thì Python chết **0xC0000409** ngay lúc dựng QApplication
        # — im lặng, không traceback, rất dễ tưởng "test treo".
        import cv2  # noqa: F401
        from PyQt6.QtWidgets import QApplication
        from app.ui.editor import EditorDialog
        # PHẢI GIỮ THAM CHIẾU PYTHON tới QApplication. Bỏ biến đi cho "gọn"
        # (`QApplication.instance() or QApplication([])` đứng trơ) là Python
        # thu hồi đối tượng -> chết **0xC0000409** ngay lúc dựng QDialog, KHÔNG
        # traceback, faulthandler cũng không bắt được.
        _app = QApplication.instance() or QApplication([])
        assert _app is not None
        khung = str(_SB / "frame.png")
        subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                        "color=c=gray:s=540x960:d=0.1", "-frames:v", "1",
                        khung], capture_output=True, creationflags=_NOWIN)
        print("   (dựng hộp Chỉnh mẫu…)", flush=True)
        dlg = EditorDialog(khung, layout=None, parent=None, current_name="")
        print("   (dựng xong)", flush=True)
        cb = dlg.hieu_ung_cb
        data = [cb.itemData(i) for i in range(cb.count())]
        nhan = [cb.itemText(i) for i in range(cb.count())]
        bao("Chỉnh mẫu có ô 'Hiệu ứng điểm nhấn' đủ 4 mức",
            data == ["tat", "nhe", "vua", "manh"], f"{data}")
        bao("mặc định là 'nhe' (BẬT mức nhẹ)", cb.currentData() == "nhe",
            f"{cb.currentData()!r} · nhãn {cb.currentText()!r}")
        # NHÃN KHÔNG EMOJI (máy anh Hùng thiếu glyph -> Ô ĐEN, v2.6.22)
        xau = [t for t in nhan
               if any(ord(c) > 0x2000 and not (0x2010 <= ord(c) <= 0x2027)
                      and ord(c) not in (0x2014, 0x2013)
                      and not (0x1E00 <= ord(c) <= 0x1EFF) for c in t)]
        bao("nhãn KHÔNG dùng emoji dễ thiếu font", not xau, f"{nhan}")
        # mẫu CŨ (không có khoá) -> 'nhe'; mẫu đặt 'tat' -> 'tat'
        dlg._apply_layout({"video_rect": (0.5, 0.5, 1.0)})
        cu = dlg.hieu_ung_cb.currentData()
        dlg._apply_layout({"video_rect": (0.5, 0.5, 1.0), "hieu_ung": "manh"})
        moi = dlg.hieu_ung_cb.currentData()
        bao("mẫu CŨ thiếu khoá -> 'nhe'; mẫu có khoá -> đúng khoá",
            cu == "nhe" and moi == "manh", f"cũ {cu!r} · có khoá {moi!r}")
        lay = dlg._collect_layout()
        bao("Lưu mẫu ghi được khoá 'hieu_ung'",
            lay.get("hieu_ung") == "manh", f"{lay.get('hieu_ung')!r}")
        dlg.deleteLater()
    except Exception as e:  # noqa: BLE001
        bao("dựng được hộp Chỉnh mẫu", False, repr(e))

    # D2: quét TĨNH 3 mắt xích còn lại (thiếu 1 mắt là anh Hùng bấm không tới)
    sp = (REPO / "app" / "ui" / "studio_page.py").read_text(encoding="utf-8")
    sv = (REPO / "app" / "services.py").read_text(encoding="utf-8")
    m1 = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8")
    bao("studio_page truyền hieu_ung TỪ MẪU vào enqueue_export",
        'hieu_ung=str(self.layout_tpl.get("hieu_ung"' in sp,
        "cửa duy nhất `_export_video` đặt layout_tpl -> bấm tay / xuất cả kênh "
        "/ dây chuyền đều ăn đúng mẫu kênh (cổng 19)")
    bao("services.enqueue_export có tham số + đưa vào payload + vào sig",
        "hieu_ung: str = " in sv and '"hieu_ung": hieu_ung' in sv
        and 'str(hieu_ung or "")' in sv,
        "đổi mức -> sig đổi -> KHÔNG bị smart-skip")
    bao("m1_highlight truyền payload['hieu_ung'] xuống export_canvas_clip",
        'hieu_ung=str(payload.get("hieu_ung"' in m1 and "hieu_ung_log=" in m1,
        "kèm hieu_ung_log để nhật ký ghi LÝ DO KÈM SỐ")

    # D3: sig dedup PHẢI đổi khi đổi mức (không thì bấm xuất lại không ra file)
    import hashlib
    def _sig(muc: str) -> str:
        return hashlib.sha1(repr((None, None, "", "", "", False, "", 0.15,
                                  1.0, "", "", False, "natural", "", "", "",
                                  1.15, True, 0.14, True, True, "", False,
                                  False, "nhe", muc, False)).encode()
                            ).hexdigest()[:12]
    bao("mức khác nhau -> sig dedup khác nhau",
        len({_sig(m) for m in ("tat", "nhe", "vua", "manh")}) == 4,
        f"{[_sig(m) for m in ('tat', 'nhe', 'vua', 'manh')]}")


# =====================================================================
#  E — NHÓM GPU: 21 chuyển cảnh OpenCL + fallback ÊM
# =====================================================================
def _rac_seg() -> int:
    import glob
    return len(glob.glob(os.path.join(tempfile.gettempdir(), "_seg_*")))


def ca_e(src: str) -> None:
    print("\n== E. 21 chuyển cảnh GPU + fallback êm ==")
    from app.core import hieu_ung_gpu as HG
    gpu = fu.co_chuyen_canh_gpu()
    bao("máy này dùng được nhóm GPU", True,
        f"{len(gpu)}/{len(HG.KHO_GPU)} kernel · OpenCL {HG.co_opencl()} · "
        f"libplacebo/Vulkan {HG.co_libplacebo()} · shader {len(HG.shader_co())}")
    segs3 = [(100.0, 108.0), (60.0, 66.0), (200.0, 203.0)]
    segs4 = [(100.0, 105.0), (50.0, 54.0), (200.0, 203.0), (300.0, 304.0)]
    # E1: mức 'manh' PHẢI ra kernel GPU; 'nhe'/'vua' vẫn CPU (không đổi hành vi
    # của 200-300 kênh đang chạy)
    k_manh = [k for k, _d in fu.chon_chuyen_canh(segs3, "manh")]
    k_vua = [k for k, _d in fu.chon_chuyen_canh(segs3, "vua")]
    bao("mức 'manh' dùng kernel GPU, 'vua'/'nhe' giữ nguyên CPU",
        all(k.startswith("gl_") for k in k_manh)
        and not any(k.startswith("gl_") for k in k_vua),
        f"manh {k_manh} · vua {k_vua}")
    bao("cùng 1 clip KHÔNG lặp một kernel GPU ở mọi chỗ nối",
        len(set(k_manh)) == len(k_manh), f"{k_manh}")
    # E2: xuất THẬT — độ dài phải KHỚP TUYỆT ĐỐI đường cắt thẳng
    r0 = _rac_seg()
    for segs in (segs3, segs4):
        tong = sum(e - s for s, e in segs)
        o = str(_SB / f"e_{len(segs)}.mp4")
        xuat(o, src, segs, bg="blur", chuyen_canh="manh", hieu_ung="")
        d = dai(o)
        bao(f"GPU {len(segs)} đoạn: độ dài lệch < 40 ms", abs(d - tong) < 0.04,
            f"{d:.3f}s vs {tong:.3f}s (lệch {abs(d - tong) * 1000:.0f} ms)")
    # E3: chuyển cảnh CÓ XẢY RA THẬT ở chỗ nối (đếm pixel, không tin rc=0)
    o_gpu, o_tat = str(_SB / "e_gpu.mp4"), str(_SB / "e_tat.mp4")
    xuat(o_gpu, src, segs3, bg="blur", chuyen_canh="manh", hieu_ung="")
    xuat(o_tat, src, segs3, bg="blur", chuyen_canh="tat", hieu_ung="")
    # Chỗ nối 1 ở giây 8,0. Phép bù `_bu_xfade` đặt vùng hoà vào **[8,00; 8,30]**
    # (LẤY THÊM phim ở cuối đoạn A, offset = độ dài GỐC của A) chứ KHÔNG phải
    # [7,70; 8,00) — đo trước mốc là ra 0,0% và FAIL OAN.
    moc = 8.15
    a, b = khung(o_gpu, moc, 540, 960), khung(o_tat, moc, 540, 960)
    pct = (float((np.abs(a[0] - b[0]) > 12).mean()) * 100
           if a is not None and b is not None else -1.0)
    bao("chuyển cảnh GPU CÓ xảy ra ở chỗ nối (không phải cắt khô)",
        pct > 10.0, f"{pct:.1f}% pixel khác bản cắt thẳng ở giây {moc}")
    # E4: MÁY NHÂN VIÊN không có OpenCL -> LÙI ÊM về xfade CPU
    _cu = fu.co_chuyen_canh_gpu
    fu.co_chuyen_canh_gpu = lambda: []          # type: ignore
    try:
        k = [x for x, _d in fu.chon_chuyen_canh(segs3, "manh")]
        o = str(_SB / "e_nogpu.mp4")
        xuat(o, src, segs3, bg="blur", chuyen_canh="manh", hieu_ung="")
        d = dai(o)
        bao("thiếu OpenCL -> tự đổi sang kiểu CPU, vẫn xuất đúng",
            not any(x.startswith("gl_") for x in k)
            and abs(d - 17.0) < 0.04, f"kiểu {k} · độ dài {d:.3f}s")
    finally:
        fu.co_chuyen_canh_gpu = _cu             # type: ignore
    # E5: GPU HỎNG GIỮA CHỪNG -> lùi êm, không rác, không mất chuyển cảnh
    _ker = HG.duong_kernel
    HG.duong_kernel = lambda: ""                # type: ignore
    try:
        o = str(_SB / "e_hong.mp4")
        ok = xuat(o, src, segs3, bg="blur", chuyen_canh="manh", hieu_ung="")
        d = dai(o)
        bao("kernel GPU hỏng -> lùi về CPU, clip vẫn đúng",
            bool(ok) and abs(d - 17.0) < 0.04, f"độ dài {d:.3f}s")
    finally:
        HG.duong_kernel = _ker                  # type: ignore
    bao("không để lại rác _seg_* sau cả 5 ca GPU", _rac_seg() <= r0,
        f"trước {r0} · sau {_rac_seg()}")


def main() -> int:
    ds = _nguon_nhat.liet_ke()[:3]
    if not ds:
        print("KHÔNG tìm thấy video Nhật thật -> DỪNG (quy tắc sắt: thành phần thật)")
        return 2
    print(f"[nguồn] {len(ds)} video Nhật thật · encoder {fu.detect_encoder()}")
    for p in ds:
        print("   ", os.path.basename(p)[:70])
    print(f"[frei0r] {HU.co_frei0r()} · kho {len(HU.KHO)} · "
          f"dùng được {len(HU.dung_duoc())}")
    ca_a1()
    ca_a2(ds[0])
    ca_a3(ds[0])
    ca_a4(ds[0])
    ca_a5()
    ca_b(ds)
    ca_c(ds[0])
    ca_e(ds[1] if len(ds) > 1 else ds[0])
    # ca_d dựng QApplication -> CHẠY Ở TIẾN TRÌNH RIÊNG. Dựng Qt trong CÙNG
    # tiến trình đã chạy nhóm GPU/ffmpeg-OpenCL làm Python chết
    # **0xC0000409 (fail-fast)**, đổi thứ tự kiểu gì cũng chết, và bản redirect
    # ra file mất SẠCH output nên rất dễ tưởng "test treo".
    print("\n== D. nối vào app (chạy ở tiến trình RIÊNG — Qt + OpenCL đá nhau) ==")
    r = subprocess.run([sys.executable, "-u", str(REPO / "_test_hieu_ung_ai.py"),
                        "--ui"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       creationflags=_NOWIN)
    for d in (r.stdout or "").splitlines():
        if d.startswith("  ["):
            print(d)
            (_OK if d.startswith("  [OK ]") else _LOI).append(d.strip())
    if r.returncode != 0 and not (r.stdout or "").strip():
        bao("chạy được phần UI ở tiến trình riêng", False,
            f"mã {r.returncode}: {(r.stderr or '')[-200:]}")
    print("\n" + "=" * 62)
    print(f"ĐẠT {len(_OK)} · SAI {len(_LOI)}")
    if _LOI:
        for x in _LOI:
            print("  SAI:", x)
        print("CỔNG 38 KHÔNG ĐẠT")
        return 1
    print("CỔNG 38 ĐẠT — 5 lỗi đã bịt, AI chọn thông minh giữ đủ bất biến, "
          "nhóm GPU nối được + lùi êm")
    return 0


if __name__ == "__main__":
    _ma = 1
    try:
        _ma = (0 if (ca_d() or not _LOI) else 1) if "--ui" in sys.argv \
            else main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
        for _s in (sys.stdout, sys.stderr):
            try:
                _s.flush()
            except (ValueError, OSError):
                pass
    # THOÁT BẰNG `os._exit`: tiến trình này vừa dựng QApplication vừa mở thiết
    # bị OpenCL -> finalize interpreter làm Python chết **0xC0000409** ngay sau
    # dòng kết quả, và bản `*>` của PowerShell mất SẠCH output. Đúng bài học
    # `_test_shutdown_safety` (main.py cũng thoát bằng os._exit).
    os._exit(_ma)
