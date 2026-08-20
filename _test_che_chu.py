# -*- coding: utf-8 -*-
"""CỔNG 56 — CHỮ CHÁY SẴN TRONG HÌNH (`app/core/che_chu.py`).

Chạy ffmpeg THẬT. Nguồn tự sinh bằng `lavfi` (tiền định, không phụ thuộc file
trên máy) + video THẬT của anh Hùng khi có.

BỐN CÁI BẪY CỔNG NÀY CỐ Ý PHÒNG (đều đã cắn thật ở repo này):
 1. ffmpeg trả **mã 0 mà file 0 KiB / 0 khung** -> mọi ca đều đo ĐỘ DÀI + SỐ
    KHUNG, không tin mã thoát. CA 10 dựng đúng ca đó để chứng minh cổng bắt.
 2. Nối `| tail` làm mã thoát thành của `tail` -> cổng in **MÃ THOÁT THẬT**.
 3. **ĐẾM ĐIỂM ẢNH KHÔNG ĐỦ ĐỂ KẾT LUẬN CHỮ HIỆN ĐÚNG.** Đo được ngay trong
    cổng này: ô vuông tofu vẽ **2.431 px** cho chữ `一` trong khi glyph THẬT
    chỉ **517 px** — đếm pixel thì kết luận NGƯỢC (tofu "đậm" gấp 4,7 lần chữ
    thật). Cách đúng: so **MỘT chữ ĐƠN GIẢN với MỘT chữ PHỨC TẠP** (`一` vs
    `鬱`); font có glyph -> tỉ số 4,4 · tofu -> tỉ số **1,00** (hai ô vuông y
    hệt nhau). CA 9 tự dựng tofu để chứng minh bộ dò không phải con dấu.
 4. **Số đo "sạch" mà mắt vẫn đọc được chữ.** Đo trên clip Douyin thật: làm mờ
    mức 0,40 cho mật độ nét **0,0030** (gần 0) nhưng khung trích ra vẫn ĐỌC
    ĐƯỢC bóng chữ. Vì vậy cổng lấy mức 1,0 làm mặc định và CA 6 bắt buộc mức
    yếu phải TRƯỢT — kèm CA 14 trích PNG ra để NGƯỜI TỰ NHÌN, cổng không tự
    phong cho mình quyền kết luận "nhìn đẹp".
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)                      # KHÔNG ghi cứng đường repo
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
# SANDBOX DB + DATA_DIR — PHẢI đặt TRƯỚC mọi `import app.*`. Từ khi cổng này
# dựng UI (CA 18) và tra mẫu (CA 19) thì nó CÓ đụng DB; không tách ra là test
# đọc/ghi thẳng dữ liệu thật của anh Hùng (luật: test không được đụng máy user).
_SB = Path(r"D:\claude\_do_che_chu\_sandbox")
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))

import _test_guard                            # noqa: E402,F401  chặn cửa sổ ngoài
import numpy as np                            # noqa: E402
from app.core import che_chu as C             # noqa: E402

#: Sandbox nằm trên D:, KHÔNG dùng %TEMP% (luật: không để rác %TEMP% máy user).
SAN = Path(os.environ.get("BQ_CHE_CHU_TEST", r"D:\claude\_do_che_chu\_test"))
KHO = Path(r"D:\claude\_do_che_chu\nguon")     # video thật đã copy ra sandbox

DAT: list = []
HONG: list = []
BO_QUA: list = []       # mục KHÔNG chấm được vì máy bận — xem `bo_qua()`
_QAPP = None            # PHẢI giữ tham chiếu QApplication — xem CA 18

#: CPU nền tối đa còn đo được CHI PHÍ. Trên ngưỡng này thì CA17 KHÔNG chấm.
#: Số này không phải đặt bừa: cùng một dòng mã, đo lúc máy rảnh ra HỘP +3,14
#: .. +3,31 mà lúc máy bận ra **+10,66** — xem khối ghi chú trần trong
#: `ca17_chi_phi`.
CPU_RANH_MAX = float(os.environ.get("BQ_CPU_MAX", "15"))


def cpu_nen() -> float:
    """CPU nền cả máy (%). Không có psutil -> trả -1 = 'không biết, cứ đo'."""
    try:
        import psutil                                   # noqa: PLC0415
    except Exception:                                    # noqa: BLE001
        return -1.0
    return max(psutil.cpu_percent(interval=1.0) for _ in range(3))


def kiem(ten: str, ok: bool, chi_tiet: str = "") -> bool:
    (DAT if ok else HONG).append(ten)
    print(f"  {'ĐẠT ' if ok else 'HỎNG'} {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return ok


def bo_qua(ten: str, ly_do: str, chi_tiet: str = "") -> None:
    """KHÔNG chấm mục này — và NÓI TO vì sao.

    Chỉ dùng cho mục mà phép đo KHÔNG CÒN TIN ĐƯỢC (xem chốt máy-bận của CA17).
    Cố tình KHÔNG cộng vào `DAT`: mục bỏ qua mà đếm là ĐẠT thì đúng bằng "phép
    đo hỏng phát chứng nhận" — bệnh `astats` cổng 53 và `startswith` cổng 44.
    Cũng KHÔNG cộng vào `HONG`: đỏ vì máy bận là ĐỎ OAN, mà cổng đỏ oan thì
    người ta bỏ qua nó (bài học cổng 41 và 47), nguy hiểm hơn hẳn.
    """
    BO_QUA.append(ten)
    print(f"  BỎ QUA {ten} — {ly_do}" + (f" — {chi_tiet}" if chi_tiet else ""))


def ff(args: list, what: str = "", cho_loi: bool = False):
    """Chạy ffmpeg, TRẢ mã thoát THẬT (không nuốt qua ống)."""
    r = subprocess.run([C._bin("ffmpeg"), "-y", "-hide_banner", "-loglevel",
                        "error", *args], capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    if r.returncode != 0 and not cho_loi:
        raise RuntimeError(f"ffmpeg {what} MÃ THOÁT THẬT={r.returncode}: "
                           f"{r.stderr.decode('utf-8', 'replace')[-500:]}")
    return r


# ───────────────────────── nguồn tự sinh (tiền định) ────────────────────────
def _esc_dt(t: str) -> str:
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def nguon(dst: Path, chu: list | None = None, cd_chu: str = "",
          giay: int = 8, w: int = 640, h: int = 360, ny: float = 0.86) -> Path:
    """Nguồn lavfi. `chu` = các dòng ĐỔI theo thời gian (giả phụ đề cháy);
    `cd_chu` = một dòng ĐỨNG IM suốt clip (giả watermark)."""
    vf = []
    n = max(1, len(chu or []))
    b = giay / n
    for i, t in enumerate(chu or []):
        vf.append(
            f"drawtext=text='{_esc_dt(t)}':fontsize={int(h*0.075)}:"
            f"fontcolor=white:borderw=2:bordercolor=black:x=(w-tw)/2:"
            f"y={ny}*h:enable='between(t,{i*b:.2f},{(i+1)*b:.2f})'")
    if cd_chu:
        vf.append(f"drawtext=text='{_esc_dt(cd_chu)}':fontsize={int(h*0.075)}:"
                  f"fontcolor=white:borderw=2:bordercolor=black:"
                  f"x=(w-tw)/2:y={ny}*h")
    ff(["-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r=25:d={giay}",
        "-f", "lavfi", "-i", f"sine=f=300:d={giay}",
        "-vf", ",".join(vf) if vf else "null",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(dst)],
       f"dựng nguồn {dst.name}")
    return dst


def _ink(png: Path, w: int, h: int) -> int:
    raw = subprocess.run([C._bin("ffmpeg"), "-v", "error", "-i", str(png),
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True,
                         creationflags=C._CREATE_NO_WINDOW).stdout
    return int((np.frombuffer(raw, np.uint8).reshape(h, w) > 128).sum())


def _psnr_ngoai(a: Path, b: Path, d) -> float:
    """PSNR phần NGOÀI dải. inf = KHÔNG rò một điểm ảnh nào."""
    vf = (f"[0:v]drawbox=x=0:y={d.y0}:w=iw:h={d.cao_dai}:color=black@1:t=fill[a];"
          f"[1:v]drawbox=x=0:y={d.y0}:w=iw:h={d.cao_dai}:color=black@1:t=fill[b];"
          "[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a),
                        "-i", str(b), "-filter_complex", vf, "-f", "null", "-"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


# ─────────────────────────────── các ca ─────────────────────────────────────
def ca1_khong_chu():
    print("\nCA 1 — nguồn KHÔNG chữ: TUYỆT ĐỐI không được kêu (che oan = hỏng hình)")
    p = nguon(SAN / "n_sach.mp4")
    d = C.do_dai_chu(p, so_khung=12)
    kiem("CA1 nguồn sạch -> co_chu=False", not d.co_chu, d.ly_do)


def ca2_co_chu():
    print("\nCA 2 — nguồn CÓ chữ cháy đổi theo thời gian: phải kêu, ĐÚNG CHỖ")
    p = nguon(SAN / "n_chu.mp4",
              chu=["Dong chu thu nhat", "Dong chu thu hai",
                   "Dong chu thu ba", "Dong chu thu tu"])
    d = C.do_dai_chu(p, so_khung=12)
    kiem("CA2 dò ra chữ", d.co_chu, d.ly_do)
    if d.co_chu:
        # chữ đốt ở y = 0,86*h, cao ~0,075*h -> tâm chữ ~ 0,90*h
        tam = (d.y0 + d.y1) / 2 / d.cao
        kiem("CA2 dải đúng chỗ (tâm 0,86..0,96 chiều cao)",
             0.86 <= tam <= 0.96, f"tâm dải ở {tam*100:.1f}% chiều cao")
        kiem("CA2 dải MỎNG (<= 16% chiều cao)",
             d.cao_dai / d.cao <= C.CAO_MAX,
             f"{d.cao_dai}px = {d.cao_dai/d.cao*100:.1f}%")
    return p, d


def ca3_watermark():
    print("\nCA 3 — WATERMARK ĐỨNG IM ≠ phụ đề: KHÔNG được che (mặt nạ HẰNG)")
    p = nguon(SAN / "n_wm.mp4", cd_chu="@kenh cua toi 2026")
    d = C.do_dai_chu(p, so_khung=12)
    kiem("CA3 watermark đứng im -> co_chu=False", not d.co_chu, d.ly_do)


def ca4_video_that():
    print("\nCA 4 — VIDEO THẬT của anh Hùng (bỏ qua nếu không có file)")
    bo = [("zh_ep12.mp4", True), ("zh_dongho.mp4", True),
          ("en_d5.mp4", False), ("en_bus.mp4", False)]
    co = 0
    for ten, that in bo:
        p = KHO / ten
        if not p.exists():
            continue
        co += 1
        d = C.do_dai_chu(p)
        kiem(f"CA4 {ten} -> {'CÓ' if that else 'KHÔNG'} chữ",
             d.co_chu == that,
             f"dò={'CÓ' if d.co_chu else 'KHÔNG'} · {d.ly_do[:60]}")
    if not co:
        print("      (không có video thật trong kho — bỏ qua)")


def ca5_che(p: Path, d):
    print("\nCA 5 — CHE: chữ biến mất TRONG dải, KHÔNG rò một điểm ảnh RA NGOÀI")
    moc = [C.thong_tin(p)["do_dai"] * f for f in (0.15, 0.4, 0.65, 0.9)]
    md0 = C.mat_do_vung(p, d.y0, d.y1, moc, d.x0, d.x1)
    ra = {}
    for cach in ("mo", "khoi"):
        o = SAN / f"che_{cach}.mp4"
        ff(["-i", str(p), "-filter_complex", C.loc_che(d, cach=cach),
            "-c:v", "libx264", "-preset", "veryfast", "-qp", "0",
            "-pix_fmt", "yuv420p", "-c:a", "copy", str(o)], f"che {cach}")
        md = C.mat_do_vung(o, d.y0, d.y1, moc, d.x0, d.x1)
        ps = _psnr_ngoai(p, o, d)
        ra[cach] = (o, md, ps)
        kiem(f"CA5 '{cach}' xoá được chữ (mật độ {md0:.4f} -> {md:.4f})",
             md <= 0.02 and md < md0 * 0.15, f"còn {md:.4f}")
        kiem(f"CA5 '{cach}' KHÔNG rò ra ngoài dải (PSNR = inf)",
             ps == float("inf"), f"PSNR ngoài dải = {ps}")
        # bẫy số 1: mã 0 nhưng file rỗng
        kiem(f"CA5 '{cach}' file ra đủ khung + đúng độ dài",
             bool(C.kiem_video_ra(o, C.thong_tin(p)["do_dai"], co_tieng=False)),
             f"{C.so_khung_hinh(o)} khung")
    return ra


def ca6_che_hong(p: Path, d):
    """PHÁ: che HỎNG phải bị BẮT — nếu không, CA 5 chỉ là con dấu.

    Hai kiểu hỏng dựng thật, mỗi cái một nguyên nhân khác nhau:
      (a) `hat` (thu nhỏ rồi phóng lại) — ĐO TRÊN CLIP DOUYIN THẬT còn **0,2022**
          mật độ và MẮT VẪN ĐỌC ĐƯỢC chữ. Đây là lý do `hat` bị loại.
      (b) che LỆCH CHỖ (dải đặt cao lên 3 lần chiều cao dải) — chữ còn nguyên.
    (Hạ `do_manh` KHÔNG dựng được ca yếu: bán kính bị kẹp sàn 2 px nên mức 0,2
     và 0,4 ra CÙNG một bán kính trên dải mỏng — ghi lại để đừng ai thử lại.)
    """
    print("\nCA 6 — PHÁ: che HỎNG phải bị BẮT (nếu không, CA 5 chỉ là con dấu)")
    moc = [C.thong_tin(p)["do_dai"] * f for f in (0.15, 0.4, 0.65, 0.9)]
    md0 = C.mat_do_vung(p, d.y0, d.y1, moc, d.x0, d.x1)
    lech = C.DaiChu(co_chu=True, y0=max(0, d.y0 - 3 * d.cao_dai),
                    y1=max(2, d.y1 - 3 * d.cao_dai), x0=d.x0, x1=d.x1,
                    rong=d.rong, cao=d.cao)
    for ten, loc in (("hat (thu nhỏ-phóng lại)", C.loc_che(d, cach="hat")),
                     ("mờ nhưng LỆCH CHỖ", C.loc_che(lech, cach="mo"))):
        o = SAN / f"che_hong_{ten[:3]}.mp4"
        ff(["-i", str(p), "-filter_complex", loc, "-c:v", "libx264",
            "-preset", "veryfast", "-qp", "0", "-pix_fmt", "yuv420p",
            "-an", str(o)], f"che hỏng {ten}")
        md = C.mat_do_vung(o, d.y0, d.y1, moc, d.x0, d.x1)
        kiem(f"CA6 '{ten}' KHÔNG qua nổi tiêu chí CA 5",
             not (md <= 0.02 and md < md0 * 0.15),
             f"còn {md:.4f} / gốc {md0:.4f}")


def ca7_viet(p: Path, d):
    print("\nCA 7 — VIẾT chữ mới: mã thoát THẬT + đủ khung + đúng dài + chữ HIỆN")
    dong = [(0.5, 3.0, "Nguoi ta chi lan xuong thoi"),
            (3.0, 5.5, "男人只是在潜水时"),
            (5.5, 7.5, "Chiếc đồng hồ lộ ra bí mật lớn")]
    o = SAN / "che_viet.mp4"
    bao = C.che_va_viet(p, o, dong, dai=d, cach="mo", thu_muc_tam=SAN)
    kiem("CA7 mã thoát THẬT = 0", bao["ma_thoat"] == 0, str(bao["ma_thoat"]))
    kiem("CA7 có che + có ghi .ass", bao["che"] and bao["so_dong"] == 3)
    k = bao["kiem"]
    kiem("CA7 file ra CÓ KHUNG HÌNH (không tin mã thoát)", k["khung"] > 0,
         f"{k['khung']} khung")
    kiem("CA7 đúng độ dài (lệch <= 1s)", k["lech_do_dai"] <= 1.0,
         f"lệch {k['lech_do_dai']}s")
    moc_chu = [1.5, 4.0, 6.5]
    md = C.mat_do_vung(o, d.y0, d.y1, moc_chu, d.x0, d.x1)
    kiem("CA7 chữ MỚI hiện trong dải (mật độ nét > 0,05)", md > 0.05,
         f"mật độ {md:.4f}")
    # khoảng KHÔNG có dòng nào -> dải phải SẠCH (che vẫn còn tác dụng)
    md_trong = C.mat_do_vung(o, d.y0, d.y1, [7.9], d.x0, d.x1)
    kiem("CA7 chỗ KHÔNG có dòng nào -> dải vẫn sạch chữ cũ",
         md_trong <= 0.02, f"mật độ {md_trong:.4f}")
    return o, bao


def ca8_cjk():
    print("\nCA 8 — CJK: .ass khai FONT CÓ GLYPH + render KHÔNG ra ô vuông tofu")
    from app.core.captions import font_cjk
    d = C.DaiChu(co_chu=True, y0=280, y1=330, x0=0, x1=640, rong=640, cao=360)
    a = SAN / "cjk.ass"
    C.ghi_ass([(0.0, 5.0, "男人只是在潜水时")], a, d, font="Montserrat")
    txt = a.read_text(encoding="utf-8")
    mong = font_cjk("男人只是在潜水时", "Montserrat")
    kiem("CA8 .ass khai đúng font do captions.font_cjk chọn",
         f",{mong}," in txt, f"mong đợi «{mong}»")
    kiem("CA8 KHÔNG khai font Latin gốc cho chữ Hán",
         ",Montserrat," not in txt or mong == "Montserrat")
    ti, a1, a2 = _ti_so_glyph(font_ass=mong)
    kiem("CA8 render ra GLYPH THẬT, không phải tofu (tỉ số 一/鬱 >= 2,0)",
         ti >= 2.0, f"一={a1}px · 鬱={a2}px · tỉ số {ti:.2f}")
    return ti


def _ti_so_glyph(font_ass: str = "") -> tuple:
    """Vẽ `一` và `鬱` bằng libass -> (tỉ số ink, ink一, ink鬱).

    Chữ THẬT: `一` một nét (ít mực) · `鬱` 29 nét (nhiều mực) -> tỉ số lớn.
    TOFU: hai ô vuông Y HỆT -> tỉ số ~1,00. Đây là lý do KHÔNG đếm pixel trần.
    """
    ra = []
    for i, ch in enumerate(("一", "鬱")):
        d = C.DaiChu(co_chu=True, y0=60, y1=160, x0=0, x1=400,
                     rong=400, cao=200)
        a = SAN / f"g{i}.ass"
        C.ghi_ass([(0.0, 2.0, ch)], a, d, font=font_ass or "Arial", co_chu=100)
        o = SAN / f"g{i}.png"
        ff(["-f", "lavfi", "-i", "color=c=black:s=400x200:d=1",
            "-vf", f"subtitles='{C._esc_loc(str(a))}'", "-frames:v", "1",
            str(o)], f"vẽ {ch}")
        ra.append(_ink(o, 400, 200))
    return ra[1] / max(1, ra[0]), ra[0], ra[1]


def ca9_tu_kiem_tofu():
    print("\nCA 9 — TỰ KIỂM BỘ DÒ TOFU: dựng tofu THẬT, bộ dò phải kêu")
    fs = sorted(Path(REPO, "app", "assets", "fonts").glob("*.ttf"))
    if not fs:
        print("      (không có font Latin đóng gói — bỏ qua)")
        return
    f = str(fs[0]).replace("\\", "/").replace(":", "\\:")
    ink = []
    for i, ch in enumerate(("一", "鬱")):
        o = SAN / f"tofu{i}.png"
        # drawtext KHÔNG lùi font -> font Latin gặp chữ Hán là ra Ô VUÔNG
        ff(["-f", "lavfi", "-i", "color=c=black:s=400x200:d=1", "-vf",
            f"drawtext=fontfile='{f}':text='{ch}':fontsize=100:"
            "fontcolor=white:x=(w-tw)/2:y=(h-th)/2", "-frames:v", "1", str(o)],
           f"tofu {ch}")
        ink.append(_ink(o, 400, 200))
    ti = ink[1] / max(1, ink[0])
    kiem("CA9 tofu bị bắt (tỉ số ~1,0 < 2,0)", ti < 2.0,
         f"一={ink[0]}px · 鬱={ink[1]}px · tỉ số {ti:.2f}")
    kiem("CA9 và ĐẾM PIXEL TRẦN thì kết luận NGƯỢC — chứng minh tại chỗ",
         ink[0] > 1500, f"tofu vẽ {ink[0]}px cho chữ 一 "
                        f"(glyph thật chỉ vài trăm px)")


def ca10_pha_file_rong():
    print("\nCA 10 — PHÁ: ffmpeg mã 0 mà file 0 khung -> phải NÉM, không cho qua")
    o = SAN / "rong.mp4"
    p = SAN / "n_chu.mp4"
    # -t 0 -> ffmpeg trả MÃ 0 nhưng không ghi khung nào
    r = ff(["-i", str(p), "-t", "0", "-c:v", "libx264", "-an", str(o)],
           "dựng file rỗng", cho_loi=True)
    khung = C.so_khung_hinh(o) if o.exists() else 0
    print(f"      ffmpeg MÃ THOÁT THẬT = {r.returncode}, file có {khung} khung")
    if r.returncode == 0 and khung == 0:
        try:
            C.kiem_video_ra(o, 8.0, co_tieng=False)
            kiem("CA10 kiem_video_ra bắt được file 0 khung", False,
                 "cho qua = THẢM HOẠ")
        except RuntimeError as e:
            kiem("CA10 kiem_video_ra bắt được file 0 khung", True, str(e)[:70])
    else:
        # ffmpeg bản này từ chối luôn -> cũng an toàn, nhưng nói rõ
        kiem("CA10 ffmpeg từ chối dựng file rỗng (cũng an toàn)",
             r.returncode != 0 or khung > 0,
             f"mã {r.returncode}, {khung} khung")


def ca11_pha_nguong():
    print("\nCA 11 — PHÁ: gỡ HẾT ngưỡng -> phải KÊU OAN trên nguồn sạch")
    p = SAN / "n_sach.mp4"
    goc = (C.NGUONG_HANG, C.NGUONG_NET, C.CAO_MAX)
    try:
        C.NGUONG_HANG, C.NGUONG_NET, C.CAO_MAX = 0.0, 3, 0.99
        d = C.do_dai_chu(p, so_khung=12, ty_le_khung_min=0.0,
                         ty_so_nen_min=0.0, mat_do_min=0.0)
    finally:
        C.NGUONG_HANG, C.NGUONG_NET, C.CAO_MAX = goc
    kiem("CA11 gỡ ngưỡng -> dò KÊU OAN (tức ngưỡng CHÍNH LÀ thứ đang chặn, "
         "không phải may)", d.co_chu, f"co_chu={d.co_chu} · {d.ly_do[:60]}")
    # và ngưỡng thật phải trả lại kết quả đúng ngay sau đó
    d2 = C.do_dai_chu(p, so_khung=12)
    kiem("CA11 trả ngưỡng về -> lại im", not d2.co_chu, d2.ly_do[:60])


def ca12_khong_chu_thi_khong_che():
    print("\nCA 12 — dò ra KHÔNG chữ -> KHÔNG được che một điểm ảnh nào")
    p = SAN / "n_sach.mp4"
    d = C.do_dai_chu(p, so_khung=12)
    kiem("CA12 loc_che trả rỗng khi không có chữ", C.loc_che(d) == "")
    o = SAN / "sach_ra.mp4"
    bao = C.che_va_viet(p, o, [(0.5, 3.0, "Chu moi")], dai=d, thu_muc_tam=SAN)
    kiem("CA12 che_va_viet KHÔNG che, nhưng VẪN viết được chữ mới "
         "(đặt ở dải đáy mặc định)",
         bao["che"] is False and bao["so_dong"] == 1 and o.exists(),
         f"che={bao['che']} · {bao['so_dong']} dòng")
    # phần hình NGOÀI dải chữ mới phải y hệt gốc
    dv = C.DaiChu(co_chu=True, **{k: bao["dai_viet"][k]
                                  for k in ("y0", "y1", "x0", "x1",
                                            "rong", "cao")})
    ps = _psnr_ngoai(p, o, dv)
    kiem("CA12 ngoài chỗ viết chữ, hình KHÔNG bị đụng (PSNR > 40 dB)",
         ps > 40 or ps == float("inf"), f"PSNR {ps}")


def ca13_khong_tieng():
    print("\nCA 13 — nguồn KHÔNG CÓ TIẾNG vẫn chạy (đừng đòi RMS)")
    p = SAN / "n_cam.mp4"
    ff(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=5", "-vf",
        "drawtext=text='Dong chu cam':fontsize=27:fontcolor=white:borderw=2:"
        "x=(w-tw)/2:y=0.86*h:enable='between(t,0,2.5)',"
        "drawtext=text='Dong chu cam hai':fontsize=27:fontcolor=white:"
        "borderw=2:x=(w-tw)/2:y=0.86*h:enable='between(t,2.5,5)'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(p)], "nguồn câm")
    d = C.do_dai_chu(p, so_khung=10)
    o = SAN / "cam_ra.mp4"
    bao = C.che_va_viet(p, o, [(0.5, 4.0, "Chu moi")], dai=d, thu_muc_tam=SAN)
    kiem("CA13 nguồn câm: chạy xong, mã thoát 0, có khung",
         bao["ma_thoat"] == 0 and bao["kiem"]["khung"] > 0,
         f"{bao['kiem']['khung']} khung")


def ca14_trich_khung_de_nhin(p: Path, o: Path, d):
    print("\nCA 14 — TRÍCH PNG ĐỂ NGƯỜI TỰ NHÌN (cổng KHÔNG tự chấm 'nhìn đẹp')")
    t = 4.0
    a = SAN / "NHIN_TRUOC.png"
    b = SAN / "NHIN_SAU.png"
    C.trich_khung(p, t, a)
    C.trich_khung(o, t, b)
    kiem("CA14 có đủ ảnh TRƯỚC + SAU để soi bằng mắt",
         a.exists() and b.exists() and a.stat().st_size > 1000)
    print(f"      TRƯỚC: {a}")
    print(f"      SAU  : {b}")


# ══════════════ PHẦN 2 — ĐÃ NỐI VÀO ĐƯỜNG XUẤT (14/08/2026) ═════════════════
# CA 15..20 kiểm cái KHÁC HẲN CA 1..14: không còn là "module có dò đúng không"
# mà là "**bấm nút trong app thì file .mp4 có đổi không, và mẫu KHÔNG bật thì
# có còn giống hệt bản cũ không**".
_MOC_MAC_DINH = "v2.25.0"          # mốc đối chứng (đổi bằng env BQ_MOC_REF)
_RECT = (0.5, 0.5, 1.0)            # khối video ĐẦY BỀ NGANG, tâm khung
_OUT_W, _OUT_H = 1080, 1920


def _nguon_that() -> Path | None:
    """Video THẬT có chữ cháy để đo đường xuất. Không có -> bỏ qua CA 15-17."""
    for ten in ("zh_ep12.mp4", "zh_dongho.mp4"):
        p = KHO / ten
        if p.exists():
            return p
    return None


def _dai_ra(d, src_w: int, src_h: int) -> tuple:
    """Đổi dải (toạ độ NGUỒN) sang toạ độ FILE XUẤT 1080x1920.

    Khối video: `scale={vw}:-2` rồi `overlay=x=cx*W-w/2 : y=cy*H-h/2`. Phải
    tính đúng chỗ này, nếu không phép đo "mật độ nét trong dải" đo nhầm vùng
    khác rồi ra 0 ở CẢ HAI bản -> cổng tự PASS OAN.
    """
    cx, cy, sw = _RECT
    vw = max(2, int(round(sw * _OUT_W)) // 2 * 2)
    vh = int(round(vw * src_h / src_w))
    vh += vh % 2
    y_top = cy * _OUT_H - vh / 2.0
    x_left = cx * _OUT_W - vw / 2.0
    ty = vh / float(src_h)
    tx = vw / float(src_w)
    return (max(0, int(y_top + d.y0 * ty)), min(_OUT_H, int(y_top + d.y1 * ty)),
            max(0, int(x_left + d.x0 * tx)), min(_OUT_W, int(x_left + d.x1 * tx)),
            max(0, int(y_top)))


def _xuat(src: Path, dst: Path, segs: list, che: bool, cach: str = "mo",
          muc: float = 1.0, log: list | None = None, mod=None) -> tuple:
    """Gọi ĐÚNG `export_canvas_clip` của app (không dựng lệnh ffmpeg riêng)."""
    fu = mod
    if fu is None:
        from app.core import ffmpeg_utils as fu   # noqa: PLC0415
    t0 = __import__("time").perf_counter()
    try:
        k = {}
        if che or mod is None:      # bản MỐC không có tham số này -> đừng truyền
            k = dict(che_chu=che, che_chu_cach=cach, che_chu_muc=muc,
                     che_chu_log=log)
        fu.export_canvas_clip(
            str(src), str(dst), segs, _RECT, bg="blur",
            out_w=_OUT_W, out_h=_OUT_H, fx_fade=False, fx_whoosh=False,
            hieu_ung="tat", chuyen_canh="tat", **k)
    except Exception as e:                                     # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"[:250], 0.0
    return True, "", __import__("time").perf_counter() - t0


def _kiem_file(p: Path, dai_mong: float) -> tuple:
    """(ok, mô tả) — BẪY 'mã 0 nhưng file 0 KiB / 0 khung' (xem docstring đầu)."""
    if not p.exists():
        return False, "KHÔNG có file"
    co = p.stat().st_size
    kh = C.so_khung_hinh(p)
    dai = C.thong_tin(p)["do_dai"]
    ok = co > 10240 and kh > 0 and abs(dai - dai_mong) < 0.6
    return ok, f"{co/1e6:.2f} MB · {kh} khung · {dai:.3f}s (mong {dai_mong:.3f}s)"


def ca15_bat_tat_co_tac_dung(src: Path):
    """CỔNG 1 — bật/tắt phải ĐỔI FILE THẬT, đo bằng mật độ nét TRONG DẢI."""
    print("\nCA 15 — BẬT/TẮT có tác dụng thật trên FILE XUẤT (video có chữ cháy)")
    d = C.dai_theo_video(src)
    if not d.co_chu:
        kiem("CA15 nguồn thật phải dò ra chữ", False, d.ly_do)
        return None, None, None
    segs = [(30.0, 40.0)]
    dai_mong = 10.0
    a, b = SAN / "x_tat.mp4", SAN / "x_bat.mp4"
    lg_a, lg_b = [], []
    ok_a, e_a, _ = _xuat(src, a, segs, False, log=lg_a)
    ok_b, e_b, _ = _xuat(src, b, segs, True, log=lg_b)
    kiem("CA15 xuất được bản TẮT", ok_a, e_a)
    kiem("CA15 xuất được bản BẬT", ok_b, e_b)
    if not (ok_a and ok_b):
        return None, None, None
    for ten, p in (("TẮT", a), ("BẬT", b)):
        ok, mo = _kiem_file(p, dai_mong)
        kiem(f"CA15 file {ten} có khung hình + đúng độ dài", ok, mo)
    y0, y1, x0, x1, y_top = _dai_ra(d, d.rong, d.cao)
    moc = [1.0, 3.5, 6.0, 8.5]
    m_a = C.mat_do_vung(a, y0, y1, moc, x0, x1)
    m_b = C.mat_do_vung(b, y0, y1, moc, x0, x1)
    kiem("CA15 bản TẮT GIỮ NGUYÊN chữ trong dải (mật độ >= 0,05)",
         m_a >= 0.05, f"mật độ nét {m_a:.4f}")
    kiem("CA15 bản BẬT xoá sạch nét trong dải (mật độ <= 0,02)",
         m_b <= 0.02, f"mật độ nét {m_b:.4f}")
    kiem("CA15 giảm ít nhất 5 lần", m_b * 5 <= m_a,
         f"{m_a:.4f} -> {m_b:.4f} (giảm {m_a/max(m_b,1e-9):.1f} lần)")
    # ---- RÒ: PHẢI ĐO ĐÚNG THỨ, nếu không cổng đỏ oan ----
    # (1) RÒ CỦA CHÍNH FILTER — đo LOSSLESS (-qp 0) trên NGUỒN. `-crf` TỰ NÓ
    #     làm lệch điểm ảnh khắp khung (bài học cổng 46) nên đo rò trên file
    #     nén là không phân biệt nổi rò thật với nhiễu mã hoá.
    kiem("CA15 filter KHÔNG đụng một điểm ảnh nào ngoài dải (lossless = inf)",
         _psnr_lossless_ngoai(src, d) == float("inf"),
         f"PSNR ngoài dải (-qp 0) = {_psnr_lossless_ngoai(src, d)}")
    # (2) TRÊN FILE XUẤT: chỉ đòi KHỐI VIDEO (phần khán giả nhìn là hình thật)
    #     ngoài dải không đổi. **NỀN MỜ THÌ CÓ ĐỔI, VÀ ĐÓ LÀ ĐÚNG**: nền là
    #     bản phóng to đã làm mờ của CHÍNH khung nguồn, nên dải chữ cũng nằm
    #     trong đó — che ở nguồn thì nền cũng sạch theo. Đòi "cả khung không
    #     đổi" là đòi một điều SAI (đo được: nền dưới 30,7 dB, khối video trên
    #     dải 51,6 dB — hai con số nói hai chuyện khác nhau).
    ps = _psnr_vung(a, b, y_top, y0 - y_top)
    kiem("CA15 KHỐI VIDEO phía trên dải KHÔNG đổi (PSNR >= 45 dB)",
         ps >= 45.0, f"PSNR khối video (hàng {y_top}..{y0}) = {ps} dB")
    kiem("CA15 nhật ký nói ĐÚNG: TẮT = không che, BẬT = có che",
         bool(lg_a) and not lg_a[0]["che"] and bool(lg_b) and lg_b[0]["che"],
         f"TẮT che={lg_a[0]['che'] if lg_a else '?'} | "
         f"BẬT ly_do={lg_b[0]['ly_do'] if lg_b else '?'}")
    return a, b, (y0, y1, x0, x1)


def _psnr_vung(a: Path, b: Path, y: int, h: int) -> float:
    """PSNR CHỈ trong dải hàng [y, y+h) của 2 file xuất."""
    h = max(2, h)
    vf = (f"[0:v]crop={_OUT_W}:{h}:0:{y}[a];[1:v]crop={_OUT_W}:{h}:0:{y}[b];"
          "[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a),
                        "-i", str(b), "-filter_complex", vf, "-f", "null", "-"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


def _psnr_lossless_ngoai(src: Path, d) -> float:
    """Che THẲNG trên nguồn ở `-qp 0` rồi so phần NGOÀI dải. inf = 0 rò."""
    f = C.loc_che(d, cach="mo", do_manh=1.0)
    l1, l2 = SAN / "ll_goc.mkv", SAN / "ll_che.mkv"
    for dst, vf in ((l1, ""), (l2, f)):
        cmd = [C._bin("ffmpeg"), "-y", "-v", "error", "-ss", "30", "-t", "2",
               "-i", str(src)]
        if vf:
            cmd += ["-filter_complex", vf]
        cmd += ["-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", "-an",
                str(dst)]
        subprocess.run(cmd, capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    return _psnr_ngoai(l1, l2, d)


def _psnr_ngoai_khung(a: Path, b: Path, y0: int, y1: int) -> float:
    """PSNR phần NGOÀI dải trên FILE XUẤT (che dải lại bằng drawbox rồi so)."""
    h = max(1, y1 - y0)
    vf = (f"[0:v]drawbox=x=0:y={y0}:w=iw:h={h}:color=black@1:t=fill[a];"
          f"[1:v]drawbox=x=0:y={y0}:w=iw:h={h}:color=black@1:t=fill[b];"
          "[a][b]psnr")
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a),
                        "-i", str(b), "-filter_complex", vf, "-f", "null", "-"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


def _psnr(a: Path, b: Path) -> float:
    r = subprocess.run([C._bin("ffmpeg"), "-hide_banner", "-i", str(a),
                        "-i", str(b), "-lavfi", "psnr", "-f", "null", "-"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW)
    for ln in r.stderr.decode("utf-8", "replace").splitlines():
        if "average:" in ln and "PSNR" in ln:
            v = ln.split("average:")[1].split()[0]
            return float("inf") if v == "inf" else float(v)
    return -1.0


def ca16_bat_bien(src: Path):
    """CỔNG 2 — QUAN TRỌNG NHẤT: mẫu KHÔNG bật che chữ phải ra file GIỐNG HỆT
    bản trước khi có tính năng này. 200-300 kênh đang chạy, không được đổi gì.

    Cách làm mượn nguyên của cổng 36 CA 8 (đã chứng minh chống PASS OAN): nạp
    `git show <mốc>:app/core/ffmpeg_utils.py` thành MODULE RIÊNG rồi xuất song
    song bằng CÙNG tham số, so PSNR — so ĐÚNG bản mã cũ, không phải so "lệnh
    trông giống nhau".
    """
    print("\nCA 16 — BẤT BIẾN: che chữ TẮT == bản mốc (đây là ca quan trọng nhất)")
    import importlib.util
    moc = os.environ.get("BQ_MOC_REF", _MOC_MAC_DINH)
    r = subprocess.run(["git", "-C", REPO, "show",
                        f"{moc}:app/core/ffmpeg_utils.py"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW, timeout=60)
    out = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(out) < 5000:
        kiem(f"CA16 lấy được ffmpeg_utils.py của {moc}", False,
             f"git rc={r.returncode} · {len(out)} ký tự")
        return
    nay = (Path(REPO) / "app" / "core" / "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    # CHỐNG PASS OAN — cùng lý lẽ cổng 36: mốc TRÙNG file đang test thì phép so
    # là "so nó với chính nó" và 99 dB VĨNH VIỄN. Tách 2 nguyên nhân: HEAD là
    # TỔ TIÊN của mốc = mốc đã nuốt nhánh này (NGUY HIỂM, FAIL); không phải tổ
    # tiên = nhánh đơn giản chưa sửa file (LÀNH). Ở việc này file CHẮC CHẮN đã
    # sửa nên trùng là dấu hiệu hỏng thật.
    la_to_tien = subprocess.run(
        ["git", "-C", REPO, "merge-base", "--is-ancestor", "HEAD", moc],
        capture_output=True, creationflags=C._CREATE_NO_WINDOW,
        timeout=60).returncode == 0
    if out.strip() == nay.strip():
        kiem("CA16 mốc đối chứng phải KHÁC nhánh này", False,
             f"`git show {moc}:app/core/ffmpeg_utils.py` TRÙNG file đang test"
             + (" VÀ HEAD là tổ tiên của mốc -> mốc đã nuốt nhánh này"
                if la_to_tien else "") +
             " -> phép so BẤT BIẾN vô nghĩa. Đặt BQ_MOC_REF về bản ĐÃ PHÁT HÀNH.")
        return
    kiem(f"CA16 bản mốc `{moc}` KHÁC nhánh này (đối chứng hợp lệ)", True,
         f"mốc {len(out)} ký tự · nhánh {len(nay)} ký tự")
    fm = SAN / "fu_moc.py"
    fm.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("fu_moc", str(fm))
    if spec is None or spec.loader is None:
        kiem("CA16 nạp được module mốc", False, "spec/loader None")
        return
    mm = importlib.util.module_from_spec(spec)
    sys.modules["fu_moc"] = mm
    try:
        spec.loader.exec_module(mm)
    except Exception as e:                                     # noqa: BLE001
        kiem("CA16 nạp được module mốc", False, f"{type(e).__name__}: {e}")
        return
    # 2 ĐOẠN + hook-first (đoạn sau NGƯỢC thời gian) = đường ghép đoạn thật,
    # đúng cảnh sản xuất; đây cũng là chỗ dễ vỡ nhất nếu filter chèn sai chỗ.
    segs = [(60.0, 66.0), (20.0, 26.0)]
    a, b = SAN / "bb_moc.mp4", SAN / "bb_tat.mp4"
    ok_a, e_a, _ = _xuat(src, a, segs, False, mod=mm)
    ok_b, e_b, _ = _xuat(src, b, segs, False)
    kiem("CA16 xuất được bằng mã của MỐC", ok_a, e_a)
    kiem("CA16 xuất được bằng mã NHÁNH này (che chữ TẮT)", ok_b, e_b)
    if not (ok_a and ok_b):
        return
    d1 = C.thong_tin(a)["do_dai"]
    d2 = C.thong_tin(b)["do_dai"]
    k1, k2 = C.so_khung_hinh(a), C.so_khung_hinh(b)
    kiem("CA16 độ dài + số khung giống mốc",
         abs(d1 - d2) * 1000 < 40 and k1 == k2,
         f"mốc {d1:.3f}s/{k1} khung · nhánh {d2:.3f}s/{k2} khung")
    ps = _psnr(a, b)
    kiem("CA16 PSNR >= 50 dB (mẫu KHÔNG bật che chữ ra file y hệt bản cũ)",
         ps >= 50.0, f"PSNR = {ps} dB")


def ca17_chi_phi(src: Path):
    """CỔNG 3 — chi phí THÊM mỗi phút phim. Đo ĐAN XEN + lấy TRUNG VỊ.

    Đo liền mạch (chạy hết 3 lượt TẮT rồi mới 3 lượt BẬT) đã ra kết luận sai 2
    lần ở repo này — máy anh Hùng luôn có việc nền chạy. Phải đan xen.
    Dò dải được HÂM NÓNG trước: con số cần chứng minh là chi phí của CHUỖI
    FILTER trong lượt mã hoá, còn dò là chi phí MỘT LẦN cho cả video (3 Part
    dùng chung) — trộn 2 thứ vào nhau là báo cáo sai bản chất.
    """
    print("\nCA 17 — CHI PHÍ THÊM: gộp vào lượt mã hoá phải ~0,1-0,2 giây/phút")
    import time
    # ---- CHỐT MÁY-BẬN (16/08/2026). ĐỌC TRƯỚC KHI ĐỘNG VÀO TRẦN. ----
    # Ba mục CA17a/b/c là phép đo THỜI GIAN, nên số của chúng nói về MÁY nhiều
    # ngang nói về MÃ. Bằng chứng: cùng một dòng mã (`git diff v2.27.0..HEAD --
    # app/core/che_chu.py app/core/ffmpeg_utils.py` RỖNG) mà HỘP ra +3,31
    # (14/08, máy rảnh) · +5,46 (15/08) · +4,60 (16/08) · **+10,66 (máy bận)**.
    # Đo lại trên máy THẬT SỰ RẢNH thì con số quay về đúng mốc — xem bảng ở
    # khối trần bên dưới. Nên lúc máy bận, việc đúng là **KHÔNG CHẤM**, không
    # phải nới trần: nới trần cho vừa +10,66 là vừa đúng chỗ cổng mất khả năng
    # bắt "ai đó lỡ thêm một lượt ffmpeg THỨ HAI" (3,5-7,6 s/phút).
    cpu0 = cpu_nen()
    may_ban = cpu0 > CPU_RANH_MAX
    print(f"  CPU nền trước khi đo: "
          f"{'không đo được (thiếu psutil)' if cpu0 < 0 else f'{cpu0:.1f}%'}"
          f"  (trần {CPU_RANH_MAX:.0f}%)"
          + ("  -> MÁY BẬN, 3 mục chi phí sẽ KHÔNG chấm" if may_ban else ""))
    # XOÁ SỔ NHỚ TRƯỚC KHI ĐO. CA 15/16 chạy trước đã hâm nóng, nên bản đầu của
    # ca này in "dò dải: 0,00s" — con số ĐẸP nhưng VÔ NGHĨA (đang đo lần TRA
    # SỔ, không phải lần DÒ). Đo nhầm thì tệ hơn không đo.
    C._DAI_NHO.clear()
    t0 = time.perf_counter()
    C.dai_theo_video(src)              # chi phí DÒ THẬT (một lần / video)
    t_do = time.perf_counter() - t0
    t0 = time.perf_counter()
    C.dai_theo_video(src)              # lần 2 = tra sổ nhớ
    t_nho = time.perf_counter() - t0
    giay = 60.0
    segs = [(30.0, 30.0 + giay)]
    # ĐO BA BÊN, ĐAN XEN — TẮT · DẢI NGANG · HỘP CHỮ. Đo hai bên (TẮT/BẬT) rồi
    # in MỘT con số là gộp hai kiến trúc KHÁC HẲN nhau vào một mẫu số: dải là
    # 1 `split`+`boxblur`+`overlay`, hộp là N cái (N = số mốc). Gộp lại thì
    # không ai biết phần vượt trần đến từ đâu.
    tat: list = []
    thanh: dict = {"DẢI": [], "HỘP": []}
    cu_hop = C._BAT_HOP
    try:
        for i in range(3):
            _, _, ta = _xuat(src, SAN / f"c_tat{i}.mp4", segs, False)
            tat.append(ta)
            for ten, bat_hop in (("DẢI", False), ("HỘP", True)):
                # PHẢI xoá sổ nhớ khi ĐỔI CHẾ ĐỘ, nếu không lượt sau đọc lại
                # bản dò của lượt trước rồi đo nhầm.
                C._DAI_NHO.clear()
                C._DAI_KHOA.clear()
                C._BAT_HOP = bat_hop
                C.dai_theo_video(src)          # hâm nóng: chỉ đo CHUỖI FILTER
                _, _, tb = _xuat(src, SAN / f"c_{ten[:1]}{i}.mp4", segs, True)
                thanh[ten].append(tb)
    finally:
        C._BAT_HOP = cu_hop
    tv = lambda xs: sorted(xs)[len(xs) // 2]                   # noqa: E731
    m_tat = tv(tat)
    m_dai, m_hop = tv(thanh["DẢI"]), tv(thanh["HỘP"])
    ph = giay / 60.0
    them_dai = (m_dai - m_tat) / ph
    them_hop = (m_hop - m_tat) / ph
    # ---- TRẦN: ĐÃ HIỆU CHUẨN LẠI 16/08/2026 — GIỮ NGUYÊN SỐ, có căn cứ mới.
    # HAI TRẦN, MỖI KIẾN TRÚC MỘT CÁI — cố ý KHÔNG nới trần chung lên cho hộp
    # lọt, vì trần tồn tại để bắt "ai đó lỡ thêm một lượt ffmpeg THỨ HAI"
    # (35-76 giây cho video 10 phút = **3,5-7,6 s/phút**); nới trần chung lên
    # 4,0 là vừa đúng chỗ mất khả năng bắt cái đó.
    #
    # **VÌ SAO TRẦN KHÔNG ĐỔI DÙ SỐ TỪNG "TRÔI".** Nghi vấn 15/08 là "trần đặt
    # sai từ đầu vì nó là số của MỘT lượt". Đã đo lại để trả lời bằng số, trên
    # máy THẬT SỰ RẢNH (CPU nền 2,7-5,4%), `_do_ca17.py` **7 vòng ĐAN XEN có
    # XOAY THỨ TỰ** (CA17 chỉ 3 vòng và luôn chạy TẮT trước — arm chạy sau gánh
    # phần máy đã nóng):
    #
    #   | lượt                         | DẢI   | HỘP   | HỘP−DẢI |
    #   |------------------------------|-------|-------|---------|
    #   | mốc 14/08 (3 vòng)           | +0,84 | +3,31 |  +2,47  |
    #   | 16/08 cổng 56 (3 vòng)       | +0,78 | +3,20 |  +2,43  |
    #   | 16/08 `_do_ca17.py` (7 vòng) | +0,70 | +3,14 |  +2,45  |
    #
    # BA lượt độc lập trên máy rảnh khớp nhau trong **±0,14 (DẢI)** và
    # **±0,17 (HỘP)**; biên độ thô trong 7 vòng chỉ 0,13s (DẢI) / 0,17s (HỘP).
    # Tức phép đo TIỀN ĐỊNH khi máy rảnh, và trần cũ **đặt đúng**. Các con số
    # +2,57 / +5,46 / +4,60 / +10,66 là số của MÁY BẬN, không phải của mã —
    # nay chốt máy-bận ở đầu hàm này chặn hẳn đường đó.
    # **KHÔNG hạ trần xuống sát số đo** (max×1,25 ra 1,01 / 3,98 / 3,14): siết
    # lại là làm cổng dễ đỏ oan hơn với nhiễu máy, đúng cái vừa đi chữa.
    #  · DẢI: 2,0 s/phút — đo 0,70-0,84, biên **2,4-2,9 lần**. Phần đắt là
    #    `boxblur` tranh CPU với libx264, KHÔNG phải kiến trúc filter
    #    (micro-benchmark `-f null`: chuỗi che +0,34, split/overlay chỉ +0,05).
    #  · HỘP: 4,5 s/phút — đo 3,14-3,31, biên **1,36-1,43 lần**. Hộp dựng
    #    **N split + N crop + N boxblur + N overlay** (N = số mốc, 6 mốc/clip
    #    60 s) nên đắt hơn dải ~4 lần. Đây là GIÁ THẬT của việc che ít đi
    #    16-31% diện tích. Muốn rẻ thì chọn "phủ khối" (`drawbox` có `enable`
    #    sẵn, không cần split/overlay — đo −0,01 s/phút).
    #  · HỘP−DẢI: 3,5 s/phút — đo 2,43-2,47. Đây mới là mục canh lượt ffmpeg
    #    thứ hai, và nó ổn định nhất trong ba (lệch 0,04 giữa 3 lượt).
    def _cham(ten, ok, ct):
        if may_ban:
            bo_qua(ten, f"máy bận (CPU nền {cpu0:.1f}% > {CPU_RANH_MAX:.0f}%) "
                        "— phép đo THỜI GIAN không tin được", ct)
        else:
            kiem(ten, ok, ct)

    _cham("CA17a DẢI NGANG: chi phí thêm <= 2,0 giây/phút phim (số hứa 0,1-0,2 "
          "KHÔNG đúng với cách 'làm mờ' — xem ghi chú)",
          them_dai <= 2.0,
          f"TẮT {m_tat:.2f}s · DẢI {m_dai:.2f}s trên clip {giay:.0f}s -> "
          f"**{them_dai:+.2f} giây/phút** · thô TẮT={[round(x,2) for x in tat]} "
          f"DẢI={[round(x,2) for x in thanh['DẢI']]}")
    _cham("CA17b HỘP CHỮ: chi phí thêm <= 4,5 giây/phút phim (hộp dựng N chuỗi "
          "split/blur/overlay nên đắt hơn dải ~4 lần — đó là giá của việc che "
          "ít đi 16-31% diện tích)",
          them_hop <= 4.5,
          f"TẮT {m_tat:.2f}s · HỘP {m_hop:.2f}s -> **{them_hop:+.2f} giây/phút** "
          f"(riêng phần HỘP thêm so với DẢI: {them_hop - them_dai:+.2f}) · "
          f"thô HỘP={[round(x,2) for x in thanh['HỘP']]} · "
          f"dò dải {t_do:.2f}s MỘT LẦN cho cả video, 3 Part dùng chung")
    _cham("CA17c HỘP không được đắt hơn DẢI quá 3,5 giây/phút (chốt bắt 'ai đó "
          "lỡ thêm một lượt ffmpeg thứ hai' — lượt đó tốn 3,5-7,6 s/phút)",
          them_hop - them_dai <= 3.5,
          f"DẢI {them_dai:+.2f} -> HỘP {them_hop:+.2f} giây/phút")
    kiem("CA17 dò dải được NHỚ (Part 2,3 của cùng video KHÔNG dò lại)",
         len(C._DAI_NHO) >= 1 and t_nho * 100 < t_do,
         f"dò lần đầu {t_do:.2f}s · lần sau {t_nho*1000:.2f} ms "
         f"-> 3 Part tốn {t_do:.2f}s chứ không phải {t_do*3:.2f}s")


def ca21_dai_nho_khong_lam_chet_xuat():
    """LỖI THẬT tìm ra 14/08/2026 (khi đo giá từng mảnh): dải NHỎ làm `boxblur`
    nhận bán kính KHÔNG HỢP LỆ -> ffmpeg **chết cả lượt xuất, 0 khung**.

    Đây không phải "che xấu một chút" mà là MẤT TRẮNG clip. Ca này chạy ffmpeg
    THẬT với các cỡ dải hiểm để bản sau không sập lại.
    """
    print("\nCA 21 — DẢI NHỎ/HẸP KHÔNG ĐƯỢC LÀM CHẾT LƯỢT XUẤT (lỗi thật)")
    p = nguon(SAN / "n_nho.mp4", chu=["a", "b"], giay=3)
    tt = C.thong_tin(p)
    W, H = tt["rong"], tt["cao"]
    for w, h in ((2, 2), (4, 4), (10, 10), (W, 2), (2, H // 4)):
        d = C.DaiChu(co_chu=True, y0=0, y1=h, x0=0, x1=w, rong=W, cao=H)
        f = C.loc_che(d, cach="mo", do_manh=1.0)
        if not f:
            kiem(f"CA21 dải {w}x{h} -> trả rỗng (không che, không chết)", True)
            continue
        o = SAN / f"nho_{w}x{h}.mp4"
        r = ff(["-i", str(p), "-filter_complex", f"[0:v]{f}[v]", "-map", "[v]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-an", str(o)], cho_loi=True)
        kh = C.so_khung_hinh(o) if o.exists() else 0
        kiem(f"CA21 dải {w}x{h} -> ffmpeg CHẠY ĐƯỢC + có khung hình",
             r.returncode == 0 and kh > 0,
             f"mã thoát THẬT={r.returncode} · {kh} khung"
             + ("" if r.returncode == 0 else
                " · " + r.stderr.decode("utf-8", "replace")[-160:]))


def ca18_round_trip_ui():
    """CỔNG 4 — mở Chỉnh mẫu offscreen, đặt giá trị, LƯU, mở lại -> đúng số.
    Kèm ca hạ mức mờ xuống 0,3 -> PHẢI bị chặn về 0,6."""
    print("\nCA 18 — ROUND-TRIP UI (Chỉnh mẫu) + SÀN 0,60 chặn cứng")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtWidgets import QApplication
        from app.ui.editor import EditorDialog
    except Exception as e:                                     # noqa: BLE001
        kiem("CA18 nạp được UI", False, f"{type(e).__name__}: {e}")
        return
    # GIỮ THAM CHIẾU vào biến TOÀN CỤC. `QApplication.instance() or
    # QApplication([])` mà không gán đi đâu thì Python thu hồi ngay đối tượng
    # vừa tạo -> Qt sập 0xC0000409 (STATUS_STACK_BUFFER_OVERRUN) NGAY LÚC dựng
    # dialog, KHÔNG một dòng traceback, và stdout chưa kịp xả nên nhìn như
    # "test chạy không ra gì". Đã sập đúng 1 lần khi viết cổng này.
    global _QAPP
    _QAPP = QApplication.instance() or QApplication([])
    ed = EditorDialog("", layout={})
    kiem("CA18 mặc định TẮT (anh Hùng phải tự bật)",
         not ed.che_chu_chk.isChecked())
    kiem("CA18 ô con MỜ ĐI khi chưa bật (nhưng vẫn HIỆN, không ẩn)",
         not ed.che_chu_cach.isEnabled() and ed.che_chu_cach.isVisible()
         is not None)
    ed.che_chu_chk.setChecked(True)
    ed.che_chu_cach.setCurrentIndex(ed.che_chu_cach.findData("khoi"))
    ed.che_chu_muc.setValue(140)
    kiem("CA18 bật ô -> ô con dùng được", ed.che_chu_cach.isEnabled())
    lay = ed._collect_layout()
    kiem("CA18 lưu đúng 3 khoá",
         lay.get("che_chu") is True and lay.get("che_chu_cach") == "khoi"
         and abs(float(lay.get("che_chu_muc", 0)) - 1.40) < 1e-6,
         f"che_chu={lay.get('che_chu')} cach={lay.get('che_chu_cach')} "
         f"muc={lay.get('che_chu_muc')}")
    ed2 = EditorDialog("", layout=lay)
    kiem("CA18 mở lại -> ĐÚNG giá trị vừa lưu",
         ed2.che_chu_chk.isChecked()
         and ed2.che_chu_cach.currentData() == "khoi"
         and ed2.che_chu_muc.value() == 140,
         f"bật={ed2.che_chu_chk.isChecked()} "
         f"cach={ed2.che_chu_cach.currentData()} muc={ed2.che_chu_muc.value()}")
    # ---- SÀN: mẫu lưu sẵn 0,30 (bản thử / sửa tay) phải bị kẹp về 0,60 ----
    xau = dict(lay)
    xau["che_chu_muc"] = 0.30
    ed3 = EditorDialog("", layout=xau)
    kiem("CA18 mẫu ghi 0,30 -> UI chặn về 0,60", ed3.che_chu_muc.value() == 60,
         f"thanh kéo = {ed3.che_chu_muc.value()/100:.2f}")
    kiem("CA18 lưu lại cũng ra 0,60 (sàn nằm trong MÃ, không chỉ ở widget)",
         abs(float(ed3._collect_layout().get("che_chu_muc", 0)) - 0.60) < 1e-6,
         f"{ed3._collect_layout().get('che_chu_muc')}")
    kiem("CA18 thanh kéo KHÔNG cho kéo dưới 0,60", ed.che_chu_muc.minimum() == 60,
         f"min={ed.che_chu_muc.minimum()}")
    # nhãn KHÔNG EMOJI (máy anh Hùng thiếu font -> ô vuông đen)
    txt = (ed.che_chu_chk.text() + ed.che_chu_cach.itemText(0)
           + ed.che_chu_cach.itemText(1) + ed.che_chu_note.text())
    xau_ky = [c for c in txt if ord(c) > 0x2000 and not (
        0x2010 <= ord(c) <= 0x203A)]
    kiem("CA18 nhãn KHÔNG có emoji/ký tự dễ thiếu font", not xau_ky,
         f"ký tự lạ: {xau_ky}")
    for e in (ed, ed2, ed3):
        e.deleteLater()


def _tim_goi(ham, ten: str):
    """AST của lời gọi `ten(...)` ĐẦU TIÊN trong thân `ham`. None = không có.

    Đọc bằng AST chứ không `in` chuỗi — bài học cổng 47/51/54: quét tĩnh bằng
    chuỗi vừa ĐỎ OAN (dính dòng ghi chú) vừa PASS OAN (đổi giá trị mà chuỗi
    vẫn còn). Ở đây nó bắt được đúng phép phá `che_chu=False`.
    """
    import inspect
    import textwrap
    try:
        cay = ast.parse(textwrap.dedent(inspect.getsource(ham)))
    except (OSError, SyntaxError):
        return None
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            nm = getattr(f, "id", None) or getattr(f, "attr", None)
            if nm == ten:
                return n
    return None


def ca19_pha_duong_truyen():
    """CỔNG 5 — CỐ TÌNH PHÁ: bỏ cờ khỏi đường truyền thì cổng PHẢI kêu.

    Cổng không kêu khi bản vá bị gỡ thì nó chỉ là con dấu. Ở đây phá 3 chỗ,
    mỗi chỗ là một mắt xích thật của đường editor -> mẫu -> m1 -> ffmpeg.
    """
    print("\nCA 19 — CỐ TÌNH PHÁ đường truyền: mỗi mắt xích đứt phải LỘ RA")
    from app.core import ffmpeg_utils as FU
    from app.modules import m1_highlight as M1
    import inspect
    # (a) m1 phải THẬT SỰ truyền 4 tham số che_chu vào export_canvas_clip.
    #     ĐỌC BẰNG AST, KHÔNG `in` chuỗi: phép thử phá đổi
    #     `che_chu=_cc_cf["bat"]` thành `che_chu=False` mà bản kiểm cũ (chỉ tìm
    #     chuỗi "che_chu=") **VẪN XANH** — tức nó chỉ là con dấu. Nay đòi giá
    #     trị truyền vào phải là BIỂU THỨC (đọc từ `doc_che_chu`), không được
    #     là HẰNG SỐ đóng cứng.
    goi = _tim_goi(M1._export_clip_impl, "export_canvas_clip")
    kw = {k.arg: k.value for k in (goi.keywords if goi else []) if k.arg}
    thieu = [k for k in ("che_chu", "che_chu_cach", "che_chu_muc",
                         "che_chu_log") if k not in kw]
    kiem("CA19a m1 truyền đủ 4 tham số che chữ vào export_canvas_clip",
         bool(goi) and not thieu, f"thiếu: {thieu}" if thieu else "đủ 4")
    hang = [k for k in ("che_chu", "che_chu_cach", "che_chu_muc")
            if k in kw and isinstance(kw[k], ast.Constant)]
    kiem("CA19a' giá trị truyền vào KHÔNG phải hằng số đóng cứng "
         "(phải lấy từ `doc_che_chu`)", not hang,
         f"đóng cứng: {[(k, ast.unparse(kw[k])) for k in hang]}"
         if hang else "cả 3 đều là biểu thức")
    # và `doc_che_chu` phải THẬT SỰ được gọi trong thân hàm xuất
    kiem("CA19a'' `doc_che_chu` được gọi trong `_export_clip_impl`",
         bool(_tim_goi(M1._export_clip_impl, "doc_che_chu")))
    # (b) export_canvas_clip phải CÓ tham số + phải DÙNG nó (không nhận rồi bỏ)
    sig = inspect.signature(FU.export_canvas_clip).parameters
    kiem("CA19b export_canvas_clip có đủ tham số",
         all(k in sig for k in ("che_chu", "che_chu_cach", "che_chu_muc",
                                "che_chu_log")),
         f"có: {[k for k in sig if k.startswith('che_chu')]}")
    ma2 = inspect.getsource(FU.export_canvas_clip)
    kiem("CA19b' và THẬT SỰ chèn vào chuỗi filter (`_cc_loc` vào `parts`)",
         "loc_cho_xuat" in ma2 and "parts.append(f\"{content}{_cc_loc}" in ma2,
         "có `loc_cho_xuat` + `parts.append`")
    # (c) sàn 0,60 phải nằm trong MÃ — gỡ `chuan_muc_mo` là lọt 0,30
    kiem("CA19c `chuan_muc_mo` kẹp 0,30 -> 0,60", C.chuan_muc_mo(0.30) == 0.60,
         f"chuan_muc_mo(0.30) = {C.chuan_muc_mo(0.30)}")
    kiem("CA19c doc_che_chu cũng đi qua sàn",
         M1.doc_che_chu({"che_chu": True, "che_chu_muc": 0.3})["muc"] == 0.60)
    # (d) mặc định phải TẮT ở MỌI cửa
    kiem("CA19d mặc định TẮT ở export_canvas_clip",
         sig["che_chu"].default is False)
    kiem("CA19d mặc định TẮT ở doc_che_chu (payload rỗng / mẫu không có khoá)",
         M1.doc_che_chu({})["bat"] is False
         and M1.doc_che_chu({"cap_style": {"_mau": "khong-ton-tai"}})["bat"]
         is False)
    # (e) TỰ KIỂM BỘ DÒ: bịa một `export_canvas_clip` KHÔNG có tham số ->
    #     ca (b) phải TRƯỢT. Không có ca này thì (b) chỉ là con dấu.
    def _gia(src, dst, segments, video_rect, bg="blur"):
        return True
    _sig_gia = inspect.signature(_gia).parameters
    kiem("CA19e TỰ KIỂM: bản GIẢ thiếu tham số -> phép kiểm (b) TRƯỢT đúng",
         not all(k in _sig_gia for k in ("che_chu", "che_chu_cach")))
    # (f) ĐƯỜNG LÙI "tra MẪU theo TÊN" — hiện là đường DUY NHẤT đưa cờ từ
    #     Chỉnh mẫu tới lượt xuất (studio_page/services đang có luồng khác sửa
    #     nên chưa nối được payload). Nó ĐỌC DB THẬT nên phải kiểm bằng DB
    #     THẬT (sandbox), không mock: mock ở đây là giấu đúng chỗ có thể vỡ.
    from app import services as _sv
    _ten = "_test_che_chu_mau"
    try:
        _sv.save_template(_ten, {"che_chu": True, "che_chu_cach": "khoi",
                                 "che_chu_muc": 0.30})
        _r = M1.doc_che_chu({"cap_style": {"_mau": _ten}})
        # `toan_khung` là khoá THỨ TƯ, thêm ở v2.28.x (ô "Quét cả khung", cổng
        # 62). Mẫu này KHÔNG đặt cờ -> phải ra `None` = "không ai chốt, theo
        # env" chứ KHÔNG phải False. Giữ so khớp TUYỆT ĐỐI (đừng đổi sang so
        # tập con cho khỏi phải sửa): mất nó là khoá thứ năm nào đó lọt vào mà
        # không ai biết.
        kiem("CA19f đường LÙI: tra MẪU theo tên -> lấy đúng cờ (và qua sàn)",
             _r == {"bat": True, "cach": "khoi", "muc": 0.60,
                    "toan_khung": None}, f"{_r}")
        _sv.save_template(_ten, {"che_chu": False})
        kiem("CA19f' mẫu TẮT -> TẮT",
             M1.doc_che_chu({"cap_style": {"_mau": _ten}})["bat"] is False)
        # PAYLOAD phải THẮNG mẫu (khi studio_page nối xong thì cờ đã chốt lúc
        # xếp job mới là nguồn đúng — mẫu có bị sửa sau đó cũng không đổi clip)
        _sv.save_template(_ten, {"che_chu": False})
        kiem("CA19f'' payload ƯU TIÊN hơn mẫu",
             M1.doc_che_chu({"che_chu": True,
                             "cap_style": {"_mau": _ten}})["bat"] is True)
    finally:
        try:
            _sv.delete_template(_ten)
        except Exception:                                      # noqa: BLE001
            pass


def ca23_co_vao_hash_chong_trung():
    """CỔNG 6 — CỜ PHẢI NẰM TRONG HASH CHỐNG TRÙNG (lỗi NGƯỜI DÙNG GẶP NGAY).

    Tới v2.25.0 cờ che chữ chỉ đi ĐƯỜNG LÙI (`doc_che_chu` tra mẫu theo tên
    lúc xuất), mà đường đó KHÔNG có trong `dedup_key`. Hậu quả THẬT: anh Hùng
    bật ô trong Chỉnh mẫu rồi bấm "Xuất cả kênh" -> clip đã xuất y hệt trước
    đó bị **SMART-SKIP**, không job nào chạy, phải bấm "Xuất lại" từng clip.

    Ca này dùng **WorkerPool + DB THẬT** (không mock) vì smart-skip là một
    câu lệnh SQL trên bảng `jobs`, mock đi là giấu đúng chỗ có thể vỡ.

    BA ĐIỀU PHẢI CHỨNG MINH, theo đúng yêu cầu:
      (a) đổi cờ -> `dedup_key` ĐỔI -> job xuất được đẻ ra thật;
      (b) đường LÙI cũ vẫn chạy (mẫu cũ không hỏng);
      (c) BẤT BIẾN: mẫu KHÔNG bật che chữ -> `dedup_key` giống TỪNG KÝ TỰ bản
          mốc, tức 200-300 kênh KHÔNG bị xuất lại từ đầu.
    """
    print("\nCA 23 — cờ che chữ nằm trong HASH CHỐNG TRÙNG (chống smart-skip)")
    import inspect
    from app import services as SV
    from app.database import db as DB
    from app.queue.worker import WorkerPool

    # ---- (0) chữ ký hàm: mặc định phải là None, KHÔNG phải False -----------
    # `False` nghĩa là "đã CHỐT: tắt" -> payload luôn mang khoá `che_chu` ->
    # `doc_che_chu` không bao giờ đi đường lùi nữa -> job cũ trong DB và mọi
    # lối gọi chưa nối mất đường. Đây là khác biệt tinh vi, phải canh bằng ca.
    sg = inspect.signature(SV.enqueue_export).parameters
    kiem("CA23-0 enqueue_export có đủ 3 tham số che chữ",
         all(k in sg for k in ("che_chu", "che_chu_cach", "che_chu_muc")),
         f"có: {[k for k in sg if k.startswith('che_chu')]}")
    kiem("CA23-0' mặc định `che_chu` là None (KHÔNG phải False — False bịt "
         "đường lùi)", sg["che_chu"].default is None,
         f"default = {sg['che_chu'].default!r}")

    # ---- (1) studio_page phải THẬT SỰ truyền, đọc bằng AST -----------------
    # Bài học đã cắn ở CA19a: tìm bằng CHUỖI thì phép phá `che_chu=False` vẫn
    # XANH. Ở đây đòi giá trị truyền vào là BIỂU THỨC (đọc từ mẫu), không được
    # là hằng số đóng cứng.
    from app.ui import studio_page as SP
    goi = _tim_goi(SP.StudioPage._export_video_inner, "enqueue_export")
    kw = {k.arg: k.value for k in (goi.keywords if goi else []) if k.arg}
    thieu = [k for k in ("che_chu", "che_chu_cach", "che_chu_muc")
             if k not in kw]
    kiem("CA23-1 studio_page truyền đủ 3 tham số vào enqueue_export",
         bool(goi) and not thieu, f"thiếu: {thieu}" if thieu else "đủ 3")
    hang = [k for k in ("che_chu", "che_chu_cach", "che_chu_muc")
            if k in kw and isinstance(kw[k], ast.Constant)]
    kiem("CA23-1' giá trị truyền vào KHÔNG phải hằng số đóng cứng "
         "(phải đọc từ `layout_tpl`)", not hang,
         f"đóng cứng: {[(k, ast.unparse(kw[k])) for k in hang]}"
         if hang else "cả 3 đều là biểu thức")

    # ---- (2) dedup_key: bật/tắt/đổi cách/đổi mức -> ĐỔI --------------------
    ghi: list = []

    class _PoolGhi:
        def enqueue(self, kind, payload, **kw):
            ghi.append((payload, kw["dedup_key"]))
            return 1

    def _key(**kw) -> tuple:
        ghi.clear()
        SV.enqueue_export(_PoolGhi(), _CID, _VID, _PID, **kw)
        return ghi[0]

    # clip THẬT trong DB sandbox: `enqueue_export` băm cả mốc cắt start/end
    _PID = DB.insert(
        "INSERT INTO projects (name, assets_dir) VALUES (?,?)",
        ("_cc_hash_kenh", str(SAN / "_cc_kenh")))
    _VID = DB.insert(
        "INSERT INTO videos (project_id, src_path, duration) VALUES (?,?,?)",
        (_PID, r"D:\khong-co-that\a.mp4", 120.0))
    _CID = DB.insert(
        "INSERT INTO clips (video_id, start_sec, end_sec, status) "
        "VALUES (?,?,?,?)", (_VID, 12.0, 48.5, "suggested"))

    p_lui, k_lui = _key()                                   # KHÔNG truyền
    p_tat, k_tat = _key(che_chu=False)                      # CHỐT tắt
    p_bat, k_bat = _key(che_chu=True)                       # CHỐT bật
    _, k_khoi = _key(che_chu=True, che_chu_cach="khoi")     # đổi cách
    _, k_m07 = _key(che_chu=True, che_chu_muc=0.7)          # đổi mức
    _, k_m03 = _key(che_chu=True, che_chu_muc=0.3)          # dưới sàn
    _, k_m05 = _key(che_chu=True, che_chu_muc=0.5)          # cũng dưới sàn

    kiem("CA23-2a BẬT -> dedup_key ĐỔI (đây là chỗ chữa smart-skip)",
         k_bat != k_tat, f"tắt …{k_tat[-24:]} · bật …{k_bat[-24:]}")
    kiem("CA23-2b đổi CÁCH che (mờ -> khối) -> dedup_key ĐỔI", k_khoi != k_bat)
    kiem("CA23-2c đổi MỨC mờ (1,0 -> 0,7) -> dedup_key ĐỔI", k_m07 != k_bat)
    # Chiều NGƯỢC LẠI cũng phải đúng: hai mức đều bị SÀN 0,60 kéo về cùng một
    # chỗ thì ra clip GIỐNG HỆT -> băm giá trị THÔ là đẻ job xuất lại cho một
    # thay đổi KHÔNG TỒN TẠI (300 kênh × mỗi lần user kéo nhầm thanh trượt).
    kiem("CA23-2d mức 0,30 và 0,50 đều bị sàn kéo về 0,60 -> KHÔNG đẻ job "
         "xuất lại oan", k_m03 == k_m05, f"…{k_m03[-16:]} / …{k_m05[-16:]}")
    kiem("CA23-2d' nhưng 0,60 vẫn KHÁC mặc định 1,0", k_m03 != k_bat)

    # ---- (3) BẤT BIẾN dedup_key: phải GIỐNG TỪNG KÝ TỰ bản MỐC -------------
    kiem("CA23-3 CHỐT TẮT ra dedup_key y hệt lối gọi KHÔNG truyền cờ",
         k_tat == k_lui, f"…{k_tat[-28:]}")
    moc = os.environ.get("BQ_MOC_REF", _MOC_MAC_DINH)
    r = subprocess.run(["git", "-C", REPO, "show", f"{moc}:app/services.py"],
                       capture_output=True,
                       creationflags=C._CREATE_NO_WINDOW, timeout=60)
    src_moc = (r.stdout or b"").decode("utf-8", errors="replace")
    nay = (Path(REPO) / "app" / "services.py").read_text(
        encoding="utf-8", errors="replace")
    if r.returncode != 0 or len(src_moc) < 3000:
        kiem(f"CA23-3' lấy được services.py của {moc}", False,
             f"git rc={r.returncode} · {len(src_moc)} ký tự")
    elif src_moc.strip() == nay.strip():
        # Chống PASS OAN, đúng bài học cổng 36 CA 8: mốc TRÙNG file đang test
        # có HAI nguyên nhân khác hẳn nhau, gộp lại là ĐỎ OAN VĨNH VIỄN cho
        # mọi bản phát hành sau không động tới `services.py`.
        #  · HEAD là TỔ TIÊN của mốc = mốc ĐÃ NUỐT nhánh này (thường là đặt
        #    nhầm `BQ_MOC_REF=main` sau khi gộp) -> "so nó với chính nó", FAIL.
        #  · KHÔNG phải tổ tiên = bản phát hành này đơn giản không sửa
        #    `services.py` -> bất biến `dedup_key` đúng DO XÂY DỰNG (hai bản
        #    giống nhau TỪNG BYTE thì không thể ra hash khác), ĐẠT.
        to_tien = subprocess.run(
            ["git", "-C", REPO, "merge-base", "--is-ancestor", "HEAD", moc],
            capture_output=True, creationflags=C._CREATE_NO_WINDOW,
            timeout=60).returncode == 0
        kiem("CA23-3' mốc đối chứng KHÔNG được là chính nhánh này",
             not to_tien,
             f"`git show {moc}:app/services.py` TRÙNG file đang test"
             + (" VÀ HEAD là TỔ TIÊN của mốc -> mốc đã nuốt nhánh này, phép "
                "so BẤT BIẾN vô nghĩa. Đặt BQ_MOC_REF về bản ĐÃ PHÁT HÀNH."
                if to_tien else
                " nhưng HEAD KHÔNG phải tổ tiên của mốc -> bản này KHÔNG SỬA "
                "`services.py`, nên `dedup_key` giống mốc TỪNG BYTE do xây "
                "dựng (không phải do đo hớ)."))
    else:
        import importlib.util
        fm = SAN / "sv_moc.py"
        fm.write_text(src_moc, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("sv_moc", str(fm))
        mm = importlib.util.module_from_spec(spec)     # type: ignore[arg-type]
        sys.modules["sv_moc"] = mm
        try:
            spec.loader.exec_module(mm)                # type: ignore[union-attr]
            ghi.clear()
            mm.enqueue_export(_PoolGhi(), _CID, _VID, _PID)
            k_moc = ghi[0][1]
            kiem(f"CA23-3' dedup_key giống TỪNG KÝ TỰ bản mốc `{moc}` khi che "
                 "chữ TẮT (200-300 kênh KHÔNG xuất lại từ đầu)",
                 k_moc == k_tat, f"mốc …{k_moc[-28:]} · nay …{k_tat[-28:]}")
            kiem("CA23-3'' và bản mốc KHÔNG hề có tham số che_chu "
                 "(đối chứng hợp lệ)",
                 "che_chu" not in inspect.signature(mm.enqueue_export).parameters)
        except Exception as e:                                 # noqa: BLE001
            kiem(f"CA23-3' nạp được services.py của {moc}", False,
                 f"{type(e).__name__}: {e}")

    # ---- (4) SMART-SKIP THẬT trên bảng `jobs` ------------------------------
    # Đây là phép đo CUỐI CÙNG, đúng thứ anh Hùng gặp: job cũ đã 'done' thì
    # bấm "Xuất cả kênh" lần nữa có đẻ job mới không.
    pool = WorkerPool({}, max_cpu=1, max_gpu=0)      # KHÔNG start() -> 0 luồng
    j0 = SV.enqueue_export(pool, _CID, _VID, _PID)   # lượt xuất ĐẦU (mẫu tắt)
    DB.execute("UPDATE jobs SET status='done' WHERE id=?", (j0,))
    j_lap = SV.enqueue_export(pool, _CID, _VID, _PID)
    kiem("CA23-4a xuất lại y hệt -> SMART-SKIP đúng (không đẻ job trùng)",
         j_lap is None, f"trả {j_lap!r}")
    # ĐƯỜNG LÙI (v2.25.0): mẫu bật che chữ nhưng cờ KHÔNG vào payload ->
    # vẫn bị skip. GIỮ ca này để số đo nói ra ĐÚNG cái đã hỏng, không giấu.
    j_lui = SV.enqueue_export(pool, _CID, _VID, _PID)
    kiem("CA23-4b (số đo của LỖI CŨ) đường LÙI không đưa cờ vào hash -> "
         "vẫn bị smart-skip", j_lui is None, f"trả {j_lui!r}")
    j_bat = SV.enqueue_export(pool, _CID, _VID, _PID, che_chu=True)
    kiem("CA23-4c ĐƯỜNG MỚI: bật che chữ -> ĐẺ JOB THẬT, không bị smart-skip",
         isinstance(j_bat, int) and j_bat != j0, f"job id = {j_bat!r}")
    j_bat2 = SV.enqueue_export(pool, _CID, _VID, _PID, che_chu=True)
    kiem("CA23-4d bấm lần nữa -> trả ID JOB CŨ, không đẻ trùng "
         "(bài học 'enqueue trả jid CŨ, không trả None')", j_bat2 == j_bat,
         f"{j_bat} vs {j_bat2}")
    j_khoi = SV.enqueue_export(pool, _CID, _VID, _PID, che_chu=True,
                               che_chu_cach="khoi")
    kiem("CA23-4e đổi sang PHỦ KHỐI -> job KHÁC nữa",
         isinstance(j_khoi, int) and j_khoi != j_bat, f"job id = {j_khoi!r}")

    # ---- (5) payload -> doc_che_chu: mắt xích cuối -------------------------
    from app.modules import m1_highlight as M1
    # Khoá thứ tư `toan_khung` (cổng 62): payload này KHÔNG chốt cờ quét cả
    # khung nên phải là `None` — `False` ở đây sẽ BỊT đường theo env.
    kiem("CA23-5a payload CHỐT BẬT -> doc_che_chu đọc ra BẬT",
         M1.doc_che_chu(p_bat) == {"bat": True, "cach": "mo", "muc": 1.0,
                                   "toan_khung": None},
         f"{M1.doc_che_chu(p_bat)}")
    kiem("CA23-5b payload CHỐT TẮT -> TẮT (không tra mẫu nữa)",
         M1.doc_che_chu(p_tat)["bat"] is False and "che_chu" in p_tat)
    kiem("CA23-5c KHÔNG truyền -> payload KHÔNG mang khoá -> đường LÙI còn "
         "nguyên (job cũ trong DB vẫn chạy đúng)", "che_chu" not in p_lui,
         f"khoá che chữ trong payload: "
         f"{[k for k in p_lui if k.startswith('che_chu')]}")


def ca22_ghep_doan(src: Path):
    """ĐƯỜNG SẢN XUẤT THẬT: clip GHÉP NHIỀU ĐOẠN + CÓ CHUYỂN CẢNH.

    CA 15 chỉ xuất 1 đoạn. Clip của anh Hùng gần như luôn 2-3 đoạn và có
    chuyển cảnh, mà đường đó đi qua `_extract_segments_to_temp` (mảnh mezzanine
    + concat) chứ không phải `-ss/-t` thẳng trên nguồn. Nếu mảnh mezzanine đổi
    KÍCH THƯỚC thì toạ độ dải (tính theo pixel NGUỒN) sẽ che LỆCH CHỖ — và sẽ
    lệch IM LẶNG, ffmpeg vẫn rc=0. Ca này chốt cả 2 điều: che ĐÚNG CHỖ và
    độ dài/số khung KHÔNG lệch (bài học v1.87 "hình một đằng tiếng một đằng").
    Có cả thứ tự HOOK-FIRST (đoạn sau ngược thời gian).
    """
    print("\nCA 22 — GHÉP NHIỀU ĐOẠN + CHUYỂN CẢNH (đường sản xuất thật)")
    d = C.dai_theo_video(src)
    if not d.co_chu:
        kiem("CA22 nguồn thật dò ra chữ", False, d.ly_do)
        return
    y0, y1, x0, x1, _ = _dai_ra(d, d.rong, d.cao)
    for ten, segs, xf in (("2 đoạn HOOK-FIRST (ngược thời gian)",
                           [(60.0, 66.0), (20.0, 26.0)], "nhe"),
                          ("3 đoạn + chuyển cảnh mức mạnh",
                           [(30.0, 35.0), (80.0, 85.0), (10.0, 15.0)],
                           "manh")):
        o = SAN / f"m_{len(segs)}doan.mp4"
        lg: list = []
        try:
            from app.core import ffmpeg_utils as fu
            fu.export_canvas_clip(
                str(src), str(o), segs, _RECT, bg="blur", out_w=_OUT_W,
                out_h=_OUT_H, fx_fade=False, fx_whoosh=False, hieu_ung="tat",
                chuyen_canh=xf, che_chu=True, che_chu_cach="mo",
                che_chu_muc=1.0, che_chu_log=lg)
        except Exception as e:                                 # noqa: BLE001
            kiem(f"CA22 xuất được: {ten}", False, f"{type(e).__name__}: {e}")
            continue
        mong = sum(e - s for s, e in segs)
        ok, mo = _kiem_file(o, mong)
        kiem(f"CA22 {ten}: có khung + ĐÚNG độ dài (chuyển cảnh KHÔNG ăn bớt)",
             ok, mo)
        md = C.mat_do_vung(o, y0, y1, [1.0, 3.0, 5.0], x0, x1)
        kiem(f"CA22 {ten}: che ĐÚNG CHỖ trên clip đã ghép (mật độ <= 0,02)",
             md <= 0.02, f"mật độ nét trong dải = {md:.4f}")
        kiem(f"CA22 {ten}: nhật ký ghi có che", bool(lg) and lg[0]["che"],
             lg[0]["ly_do"] if lg else "(rỗng)")


def _he_ra(src_w: int, src_h: int) -> tuple:
    """(x_trái, y_trên, tx, ty) quy toạ độ NGUỒN -> FILE XUẤT 1080x1920."""
    cx, cy, sw = _RECT
    vw = max(2, int(round(sw * _OUT_W)) // 2 * 2)
    vh = int(round(vw * src_h / src_w))
    vh += vh % 2
    return (cx * _OUT_W - vw / 2.0, cy * _OUT_H - vh / 2.0,
            vw / float(src_w), vh / float(src_h))


def ca24_hop_chu(src: Path):
    """HỘP CHỮ — con số CHÍNH: che ÍT ĐI bao nhiêu % mà VẪN che hết chữ.

    `do_hop_chu` thu dải ngang về HỘP bám mép chữ thật, đổi theo mốc thời
    gian. Ba mệnh đề phải đúng CÙNG LÚC, thiếu một cái là phải lùi về dải:
      (1) DIỆN TÍCH che giảm thật — đo theo **điểm ảnh × giây** trên đường
          xuất có `segs` hook-first, KHÔNG đọc `ty_le_thu` (thuộc tính đó chỉ
          tính BỀ NGANG, mà hộp còn được nới CAO thêm ở chóp/chân chữ — báo
          cáo bề ngang thôi là giấu mất phần diện tích tăng).
      (2) vẫn CHE HẾT CHỮ — mật độ nét đo trên **CẢ BỀ NGANG DẢI CŨ**, không
          phải chỉ trong hộp. Đo trong hộp là tự hỏi "chỗ tôi che có sạch
          không" (luôn sạch); câu cần hỏi là "chỗ tôi BỎ RA có sót chữ không".
      (3) KHÔNG che oan thêm: hộp không bao giờ RỘNG hơn dải, phần nới CAO
          nằm trong mức `HOP_CAO_THEM`, và video KHÔNG chữ vẫn KHÔNG bị đụng.
    """
    print("\nCA 24 — HỘP CHỮ: che ÍT ĐI bao nhiêu %, mà có còn che HẾT chữ không")
    segs = [(120.0, 135.0), (40.0, 55.0)]        # HOOK-FIRST (ngược thời gian)
    dai_clip = sum(e - s for s, e in segs)
    cu = C._BAT_HOP
    try:
        # PHẢI xoá sổ nhớ khi ĐỔI CHẾ ĐỘ. Quên xoá thì lượt "HỘP" đọc lại bản
        # DẢI đã nhớ và in ra "giảm 0,0%" — số SAI mà trông rất thuyết phục.
        C._DAI_NHO.clear()
        C._DAI_KHOA.clear()
        C._BAT_HOP = False
        d_dai = C.dai_theo_video(src)
        C._DAI_NHO.clear()
        C._DAI_KHOA.clear()
        C._BAT_HOP = True
        d_hop = C.dai_theo_video(src)
    finally:
        C._BAT_HOP = cu
    if not (d_dai.co_chu and d_hop.co_chu):
        kiem("CA24 nguồn thật dò ra chữ ở CẢ HAI chế độ", False,
             f"dải co_chu={d_dai.co_chu} · hộp co_chu={d_hop.co_chu}")
        return
    kiem("CA24a HỘP không được đổi kết luận 'có chữ' (đây là cửa giữ kỉ lục "
         "CHE OAN 0/76)",
         d_hop.co_chu is d_dai.co_chu and bool(d_hop.hop),
         f"co_chu {d_dai.co_chu} -> {d_hop.co_chu} · {len(d_hop.hop or [])} mốc")
    # BỀ NGANG HỢP của mọi hộp CÓ THỂ RỘNG HƠN DẢI, và đó KHÔNG phải lỗi —
    # đo được 14/08: dải x=122..838 (716px) · hộp x=86..874 (**788px, +10%**).
    # Hai bộ dò lấy mẫu KHÁC HẲN nhau: dải xem `SO_KHUNG=16` khung cho CẢ
    # video, hộp xem `HOP_FPS=2` khung/giây (video 5 phút = 600 khung) nên nó
    # THẤY dòng phụ đề dài nhất mà 16 khung kia bỏ sót, cộng `HOP_DEM=10` px
    # đệm mỗi bên. Nới ra ở đó là che ĐÚNG chỗ có chữ.
    # Cái phải canh là (a) đừng nới quá tay (dấu hiệu bắt nhiễu) và (b) bề
    # ngang TRUNG BÌNH THEO THỜI GIAN vẫn phải NHỎ HƠN dải — đó mới là mệnh
    # đề "che ít đi", còn hợp-của-mọi-hộp thì không nói lên điều gì.
    rong_dai = max(1, d_dai.x1 - d_dai.x0)
    du = (d_hop.x1 - d_hop.x0) / rong_dai - 1.0
    kiem("CA24a' bề ngang HỢP của mọi hộp không được vượt dải quá 15% (hộp dò "
         "2 khung/giây nên THẤY dòng dài nhất mà 16 khung của dải bỏ sót — nới "
         "ra là đúng; vượt nhiều mới là dấu hiệu bắt nhiễu)",
         du <= 0.15,
         f"dải x={d_dai.x0}..{d_dai.x1} ({rong_dai}px) · "
         f"hộp x={d_hop.x0}..{d_hop.x1} ({d_hop.x1-d_hop.x0}px) = "
         f"{du*100:+.1f}%")
    kiem("CA24a''' bề ngang TRUNG BÌNH THEO THỜI GIAN phải NHỎ HƠN dải (đây "
         "mới là mệnh đề 'che ít đi' trên trục ngang)",
         d_hop.ty_le_thu < 1.0,
         f"trung bình theo thời lượng = {d_hop.ty_le_thu*100:.0f}% bề ngang dải")
    # Nới chóp/chân: hộp CÓ QUYỀN cao hơn dải, nhưng chỉ trong mức đã khai.
    # Cao hơn nữa = đang ăn vào HÌNH, tức che oan kiểu mới.
    tran = int(round(C.HOP_CAO_THEM * d_dai.rong / float(C.RONG_DO))) + 2
    tren, duoi = d_dai.y0 - d_hop.y0, d_hop.y1 - d_dai.y1
    kiem(f"CA24a'' nới chóp/chân nằm trong mức khai báo (<= {tran}px mỗi phía, "
         "cao hơn nữa là ăn vào HÌNH)",
         0 <= tren <= tran and 0 <= duoi <= tran,
         f"trên +{tren}px · dưới +{duoi}px · cao dải {d_dai.cao_dai}px -> "
         f"hộp {d_hop.cao_dai}px")

    # ---- (1) CON SỐ CHÍNH: DIỆN TÍCH CHE (điểm ảnh × giây) ----
    hop_ra = C.hop_theo_doan(d_hop, segs)
    dt_dai = dai_clip * (d_dai.x1 - d_dai.x0) * d_dai.cao_dai
    dt_hop = (sum((b - a) * (x1 - x0) for a, b, x0, x1 in hop_ra)
              * d_hop.cao_dai) if hop_ra else \
        dai_clip * (d_hop.x1 - d_hop.x0) * d_hop.cao_dai
    giam = (1.0 - dt_hop / max(1.0, dt_dai)) * 100.0
    kiem("CA24b DIỆN TÍCH CHE GIẢM THẬT (> 0%; hộp mà che NHIỀU HƠN dải thì "
         "tính năng này phản tác dụng, phải lùi về dải ngang)",
         giam > 0.0,
         f"dải {dt_dai/1e6:.2f} -> hộp {dt_hop/1e6:.2f} triệu điểm-ảnh·giây "
         f"= **GIẢM {giam:.1f}%** · {len(hop_ra)} hộp theo mốc · "
         f"bề ngang riêng {d_hop.ty_le_thu*100:.0f}% dải")

    # ---- (2) CHE HẾT CHỮ + KHÔNG SÓT Ở RÌA ----
    a, b = SAN / "hop_tat.mp4", SAN / "hop_bat.mp4"
    ok_a, e_a, _ = _xuat(src, a, segs, False)
    lg: list = []
    C._DAI_NHO.clear()
    C._DAI_KHOA.clear()
    ok_b, e_b, _ = _xuat(src, b, segs, True, log=lg)
    kiem("CA24c xuất được cả bản TẮT và bản BẬT-HỘP", ok_a and ok_b,
         f"{e_a}|{e_b}")
    if not (ok_a and ok_b):
        return
    for ten, p in (("TẮT", a), ("BẬT-HỘP", b)):
        o, mo = _kiem_file(p, dai_clip)
        kiem(f"CA24c file {ten} có khung hình + đúng độ dài", o, mo)
    left, top, tx, ty = _he_ra(d_dai.rong, d_dai.cao)
    # ĐO TRÊN BỀ NGANG DẢI CŨ (không phải trong hộp) — đây mới là phép kiểm
    # "sót ký tự ở rìa". Dùng luôn y của HỘP để phần nới cao cũng được tính.
    yy0 = max(0, int(top + d_hop.y0 * ty))
    yy1 = min(_OUT_H, int(top + d_hop.y1 * ty))
    xx0 = max(0, int(left + (d_dai.x0_dai or d_dai.x0) * tx))
    xx1 = min(_OUT_W, int(left + (d_dai.x1_dai or d_dai.x1) * tx))
    moc = [dai_clip * f for f in (0.08, 0.25, 0.42, 0.58, 0.75, 0.92)]
    md_a = C.mat_do_vung(a, yy0, yy1, moc, xx0, xx1)
    md_b = C.mat_do_vung(b, yy0, yy1, moc, xx0, xx1)
    kiem("CA24d bản TẮT còn nguyên chữ trên bề ngang dải (đối chứng, >= 0,05)",
         md_a >= 0.05, f"mật độ nét {md_a:.4f}")
    kiem("CA24d' HỘP che HẾT chữ — mật độ nét trên **CẢ BỀ NGANG DẢI CŨ** về "
         "~0 (<= 0,02). Đây là phép kiểm 'không sót ký tự ở RÌA': phần dải bị "
         "hộp BỎ RA vẫn nằm trong vùng đo.",
         md_b <= 0.02,
         f"{md_a:.4f} -> {md_b:.4f} (giảm {md_a/max(md_b,1e-9):.0f} lần) · "
         f"vùng đo y={yy0}..{yy1} x={xx0}..{xx1} (bề ngang DẢI, "
         f"hộp chỉ che {d_hop.ty_le_thu*100:.0f}% chỗ đó)")
    kiem("CA24d'' nhật ký nói rõ là che HỘP CHỮ",
         bool(lg) and lg[0]["che"] and "HỘP" in (lg[0].get("ly_do") or ""),
         lg[0]["ly_do"] if lg else "(rỗng)")

    # ---- (3) CHE OAN: video KHÔNG chữ phải KHÔNG bị đụng ----
    sach = [KHO / t for t in ("en_d5.mp4", "en_bus.mp4")]
    sach = [p for p in sach if p.exists()]
    if not sach:
        HONG.append("CA24e KHÔNG có video sạch trong kho -> không đo được "
                    "CHE OAN (đừng coi là ĐẠT)")
    for p in sach:
        C._DAI_NHO.clear()
        C._DAI_KHOA.clear()
        C._BAT_HOP = True
        try:
            f, d, ly = C.loc_cho_xuat(p, segs=segs)
        finally:
            C._BAT_HOP = cu
        kiem(f"CA24e CHE OAN — {p.name} không chữ -> chuỗi filter RỖNG kể cả "
             "khi bật hộp (hộp chỉ chạy sau khi ĐÃ kết luận có chữ)",
             f == "" and (d is None or not d.co_chu), f"ly_do: {ly[:80]}")

    # ---- (4) ẢNH ĐỂ NGƯỜI/LLM TỰ NHÌN — phóng to đúng dải ----
    ch = max(2, (yy1 - yy0 + 24) // 2 * 2)
    yc = max(0, yy0 - 12)
    for ten, p in (("TAT", a), ("HOP", b)):
        for i, f in enumerate((0.18, 0.50, 0.82)):
            dst = SAN / f"ZOOM_{ten}_{i}.png"
            subprocess.run(
                [C._bin("ffmpeg"), "-y", "-v", "error", "-ss",
                 f"{dai_clip*f:.3f}", "-i", str(p), "-frames:v", "1", "-vf",
                 f"crop={_OUT_W}:{ch}:0:{yc},scale=iw*2:ih*2:flags=neighbor",
                 str(dst)], capture_output=True,
                creationflags=C._CREATE_NO_WINDOW)
    n_anh = len(list(SAN.glob("ZOOM_*.png")))
    kiem("CA24f có ảnh PHÓNG TO vùng dải để NGƯỜI TỰ NHÌN (cổng không tự chấm "
         "'nhìn đẹp' — số đo 'sạch' mà mắt vẫn đọc được chữ đã xảy ra)",
         n_anh >= 6, f"{n_anh} ảnh · {SAN}\\ZOOM_*.png")


# ════════ CA 25 — ĐOẠN CUỐI VIDEO (lỗi anh Hùng báo 20/08/2026) ═════════════
# *"kiểm tra lại cái phần làm mờ sao cứ đến gần cuối video nó k che mờ chữ gì
# cả"*.
#
# GỐC: đường THAY TIẾNG làm chậm hình để khớp giọng. Hộp che thì dò trên video
# GỐC nên mốc của nó là mốc CHƯA GIÃN, còn `enable='between(t,a,b)'` đọc biến
# `t` của KHUNG ĐANG CHẠY. Phép giãn nằm TRƯỚC khối che (`-itsscale` là tuỳ chọn
# ĐẦU VÀO) thì `t` đã bị nhân `k` -> lệch dần, và **mọi khung có `t` > độ dài
# GỐC rơi ra NGOÀI mọi mệnh đề enable = KHÔNG CHE GÌ**. Đuôi đó dài đúng
# `(1 − 1/k)` clip: k=1,1987 -> 16,6% · k=1,25 -> 20,0%.
#
# BA MỆNH ĐỀ, mỗi cái chặn một kiểu hỏng KHÁC nhau:
#  (a) ĐỐI CHỨNG PHẢI CÓ RĂNG — k=1,0 thì mọi mốc phải được che. Thiếu mục này
#      thì mục (b) có thể ĐẠT vì bộ dò không dò ra gì (tự ĐẠT OAN).
#  (b) ĐO ĐIỂM ẢNH TRÊN FILE ĐÃ XUẤT ở k lớn nhất, **lấy mốc theo độ dài BẢN
#      XUẤT** — lấy theo bản GỐC là bỏ trắng đúng cái đuôi đang hỏng (bản đầu
#      của phép đo tôi viết đã sập bẫy này).
#  (c) BẤT BIẾN TRÊN LỆNH ffmpeg, KHÔNG PHỤ THUỘC CÁCH VÁ: cửa sổ `enable` cuối
#      cùng phải phủ tới KHUNG CUỐI, mà mốc của khung cuối là `k*dur` khi phép
#      giãn đứng TRƯỚC khối che và `dur` khi nó đứng SAU. Viết theo mệnh đề đó
#      thì vá bằng `setpts` sau khối che, hay vá bằng cách nhân sẵn mốc hộp,
#      cổng đều chấm được — không khoá cứng vào một bản vá.
#: ĐỘ DÀI NGUỒN CỦA CA 25 — **CỐ Ý KHÔNG chia hết cho `HOP_DOAN`=8**
#: (21 = 2x8 + 5). Vòng chia đoạn của `do_hop_chu` là nghi phạm số 1 khi đọc mã,
#: nên ca này phải đi qua đúng cảnh "đoạn lẻ cuối" chứ không chọn 24 hay 40 cho
#: dễ. (Nghi phạm đó đo ra là VÔ TỘI — xem CA 25c.)
_CA25_GIAY = 21
_CA25_K = 1.25          # trần `thay_giong.TRAN_CHINH_HINH`
_CA25_MOC = (0.20, 0.50, 0.75, 0.85, 0.92, 0.97)


def _ca25_phu(hop, dai: float) -> tuple:
    """(phủ được bao nhiêu giây, thiếu ở ĐUÔI) của danh sách cửa sổ."""
    gop: list = []
    for a, b, *_ in sorted((float(x[0]), float(x[1]), *x[2:]) for x in hop):
        a, b = max(0.0, a), min(dai, b)
        if b <= a:
            continue
        if gop and a <= gop[-1][1] + 1e-6:
            gop[-1][1] = max(gop[-1][1], b)
        else:
            gop.append([a, b])
    het = max((b for _, b in gop), default=0.0)
    return sum(b - a for a, b in gop), max(0.0, dai - het)


def _ca25_tieng(giay: float, dst: Path) -> Path:
    """WAV im lặng. `-t` đặt TRƯỚC `-i` — sai chỗ thì `anullsrc` ghi VÔ HẠN
    (đã đầy ổ C một lần, xem bài học `-t` là tuỳ chọn ĐẦU VÀO)."""
    ff(["-f", "lavfi", "-t", f"{giay:.3f}", "-i",
        "anullsrc=r=44100:cl=stereo", "-c:a", "aac", "-b:a", "96k", str(dst)],
       f"tiếng im {dst.name}")
    return dst


def _ca25_moc_enable(lenh: list) -> tuple:
    """(mốc CUỐI của mọi cửa sổ enable, có `-itsscale` không, giãn SAU khối che
    không) — đọc THẲNG từ lệnh ffmpeg sắp chạy."""
    import re
    fc = ""
    for i, a in enumerate(lenh):
        if a == "-filter_complex" and i + 1 < len(lenh):
            fc = str(lenh[i + 1])
    b_max = 0.0
    for m in re.finditer(r"between\(t,([-\d.]+),([-\d.]+)\)", fc):
        b_max = max(b_max, float(m.group(2)))
    # "giãn SAU khối che" = `setpts` nằm SAU phép che cuối cùng trong chuỗi.
    p_che = max(fc.rfind("overlay="), fc.rfind("drawbox="), fc.rfind("boxblur="))
    p_gian = fc.rfind("setpts=")
    return b_max, ("-itsscale" in lenh), (p_gian > p_che >= 0)


def ca25_doan_cuoi_video():
    """ĐOẠN CUỐI VIDEO phải được che — kể cả khi hình bị làm CHẬM để khớp giọng.
    """
    print("\nCA 25 — ĐOẠN CUỐI VIDEO vẫn phải được che (lỗi anh Hùng 20/08/2026)")
    from app.core import thay_giong as TG                      # noqa: PLC0415
    # BA BẪY CỦA NGUỒN TỰ SINH, đã sập 2 cái khi viết ca này (ghi để đừng lặp):
    #  · chữ NGẮN thì mật độ nét trong dải không đủ ngưỡng — 7 dòng CJK 5 ký tự
    #    đo ra **0,0171** (cần >= `NGUONG_HANG` 0,045) rồi cả CA 25 tự tắt;
    #  · **DÒNG GẦN GIỐNG NHAU BỊ MẶT NẠ HẰNG XOÁ SẠCH** — `Dong chu thu 1 chay
    #    o day` .. `thu 7 chay o day` chỉ khác MỘT chữ số và `x=(w-tw)/2` cho
    #    bề rộng y hệt, nên >= 85% điểm ảnh chữ bật ở MỌI khung -> luật (2) của
    #    `do_dai_chu` coi đó là WATERMARK và trừ đi, còn **0,0180**. Đó là bộ dò
    #    làm ĐÚNG (đúng cái giữ kỉ lục che oan 0/76), lỗi ở nguồn thử. Dòng phải
    #    khác nhau CẢ NỘI DUNG lẫn BỀ RỘNG;
    #  · độ dài KHÔNG phải nguyên nhân — cùng 4 dòng của CA 2 thì 8/12/16/21 s
    #    đều dò ra (đậm gấp 17,2 / 16,6 / 17,6 / 17,3 lần nền).
    src = nguon(SAN / "cuoi_nguon.mp4", giay=_CA25_GIAY,
                chu=["Anh ay noi rang khong the tin duoc",
                     "Co gai buoc vao phong",
                     "Bac si nghi ra mot cach",
                     "Ket qua that bat ngo",
                     "Ong chu goi dien ngay lap tuc",
                     "Khong ai biet chuyen gi da xay ra",
                     "Cuoi cung su that duoc phoi bay"])
    dur = float(C.thong_tin(src)["do_dai"] or 0)
    d = C.dai_theo_video(src)
    if not d.co_chu:
        kiem("CA25 nguồn tự sinh phải dò ra chữ (không dò ra thì mọi mục dưới "
             "tự ĐẠT OAN)", False, d.ly_do)
        return
    # ---- (c) ĐOẠN LẺ CUỐI: nghi phạm số 1 khi ĐỌC MÃ, đo ra là VÔ TỘI ----
    le = dur % C.HOP_DOAN
    phu, thieu = _ca25_phu(C.hop_theo_doan(d, [(0.0, dur)]), dur)
    kiem(f"CA25c độ dài KHÔNG chia hết cho HOP_DOAN={C.HOP_DOAN:g} (đoạn lẻ "
         f"cuối {le:.2f}s) mà cửa sổ hộp vẫn phủ TỚI HẾT clip",
         le > 0.5 and thieu <= 0.05,
         f"dài {dur:.3f}s · {len(d.hop or [])} mốc nguồn · phủ {phu:.2f}s · "
         f"thiếu ở đuôi {thieu:.3f}s")
    # ---- (a)(b) ĐO ĐIỂM ẢNH TRÊN FILE ĐÃ XUẤT, hai hệ số ----
    for k in (1.0, _CA25_K):
        au = _ca25_tieng(dur * k, SAN / f"cuoi_im_{int(k*100)}.m4a")
        p_che, p_ref = (SAN / f"cuoi_che_{int(k*100)}.mp4",
                        SAN / f"cuoi_ref_{int(k*100)}.mp4")
        lg: list = []
        TG.thay_audio_video(src, au, p_che, che_chu=True, che_chu_muc=1.0,
                            che_chu_log=lg, he_so_hinh=k)
        # ĐỐI CHỨNG chạy CÙNG hệ số nhưng KHÔNG che -> `-c:v copy` -> khung
        # giống TỪNG ĐIỂM ẢNH, nên tỉ lệ che/đối_chứng tại CÙNG giây T là số
        # sạch. So "gốc tại T" với "xuất tại T" là SAI: bản xuất giãn k lần nên
        # giây T của nó là nội dung giây T/k của gốc — HAI CẢNH KHÁC NHAU.
        TG.thay_audio_video(src, au, p_ref, che_chu=False, he_so_hinh=k)
        d_ra = float(C.thong_tin(p_che)["do_dai"] or 0)
        ok_f, mo_ta = _kiem_file(p_che, dur * k)
        kiem(f"CA25 k={k:.2f} file xuất mở được + đúng độ dài", ok_f, mo_ta)
        # ---- (e) KHÔNG ĐƯỢC MẤT KHUNG — mục này ra đời TỪ MỘT PHÉP PHÁ LỌT.
        # Phép phá "trả `-itsscale` vào lệnh nhánh che chữ" làm hình giãn HAI
        # LẦN (k*k), rồi `-shortest` CẮT bản xuất theo độ dài TIẾNG (k*dur) ->
        # độ dài file vẫn ĐÚNG `k*dur` nên mục trên ĐẠT, và phần đuôi hỏng thì
        # **đã bị xoá khỏi file** nên phép đo điểm ảnh cũng không thấy gì:
        # cổng XANH trong khi 20% cuối THƯỚC PHIM biến mất. Cửa chặn đúng là
        # SỐ KHUNG — `setpts` giữ nguyên từng khung, giãn hai lần thì mất
        # (đo: 525 -> ~420). Lề 2 khung: đổi cơ chế giãn lệch đúng 1 khung
        # (đo `_do_che_itsscale.py`: 1078 so với 1079).
        kh_c, kh_r = C.so_khung_hinh(p_che), C.so_khung_hinh(p_ref)
        kiem(f"CA25e k={k:.2f} KHÔNG mất khung nào so với bản đối chứng "
             "(giãn hai lần thì `-shortest` cắt mất đoạn cuối THƯỚC PHIM, mà "
             "cắt rồi thì phép đo điểm ảnh không còn thấy chỗ hỏng)",
             abs(kh_c - kh_r) <= 2,
             f"che {kh_c} khung · đối chứng {kh_r} khung "
             f"(lệch {kh_c - kh_r:+d})")
        if not lg or not lg[0].get("che"):
            kiem(f"CA25 k={k:.2f} lượt xuất PHẢI có che (log nói không che thì "
                 "mục dưới tự ĐẠT OAN)", False, str(lg[:1])[:200])
            continue
        xa, xb = (d.x0_dai or d.x0), (d.x1_dai or d.x1)
        xau = []
        for r in _CA25_MOC:
            T = round(d_ra * r, 3)
            mr = C.mat_do_vung(p_ref, d.y0, d.y1, [T], x0=xa, x1=xb)
            mc = C.mat_do_vung(p_che, d.y0, d.y1, [T], x0=xa, x1=xb)
            giu = mc / max(1e-9, mr)
            print(f"        {int(r*100):3d}%  T={T:7.3f}s  đối chứng={mr:.4f}  "
                  f"che={mc:.4f}  còn {giu*100:5.1f}%"
                  + ("   <- vùng T > độ dài GỐC" if T > dur else ""))
            if giu > 0.15:
                xau.append((int(r * 100), round(giu, 3), T > dur))
        ten = ("CA25a ĐỐI CHỨNG k=1,00: mọi mốc phải được che (mục này giữ cho "
               "CA25b không tự ĐẠT OAN)" if k == 1.0 else
               f"CA25b k={k:.2f} (hình chậm {(k-1)*100:.0f}%): mọi mốc vẫn "
               f"được che, KỂ CẢ {(1-1/k)*100:.1f}% cuối clip")
        kiem(ten, not xau,
             f"{len(_CA25_MOC)}/{len(_CA25_MOC)} mốc còn <= 15% mật độ nét"
             if not xau else f"mốc còn nguyên chữ: {xau}")
    # ---- (d) BẤT BIẾN TRÊN CHÍNH LỆNH ffmpeg (không chạy ffmpeg) ----
    lenh: list = []
    cu = TG._ffmpeg
    try:
        TG._ffmpeg = lambda a, *x, **y: lenh.append(list(a))    # noqa: ARG005
        TG.thay_audio_video(src, SAN / "cuoi_im_125.m4a",
                            SAN / "cuoi_ast.mp4", che_chu=True,
                            che_chu_muc=1.0, he_so_hinh=_CA25_K)
    finally:
        TG._ffmpeg = cu
    kiem("CA25d bắt được lệnh ffmpeg của nhánh che chữ", bool(lenh),
         f"{len(lenh)} lệnh")
    if lenh:
        b_max, co_its, gian_sau = _ca25_moc_enable(lenh[-1])
        # Mốc của KHUNG CUỐI theo trục mà `enable=` đọc: giãn TRƯỚC khối che
        # thì khung cuối mang mốc `k*dur`; giãn SAU (hoặc không giãn) thì `dur`.
        t_cuoi = dur * _CA25_K if (co_its and not gian_sau) else dur
        kiem("CA25d' cửa sổ `enable` CUỐI phải phủ tới KHUNG CUỐI của clip "
             "(mệnh đề này không khoá vào một cách vá nào: nó tự đổi trục theo "
             "chỗ đặt phép giãn)",
             b_max >= t_cuoi - 0.1,
             f"mốc enable cuối {b_max:.3f}s · khung cuối ở {t_cuoi:.3f}s · "
             f"-itsscale={co_its} · giãn SAU khối che={gian_sau}")
        C.trich_khung(SAN / f"cuoi_che_{int(_CA25_K*100)}.mp4",
                      dur * _CA25_K * 0.97, SAN / "CUOI_CHE_97.png")
        C.trich_khung(SAN / f"cuoi_ref_{int(_CA25_K*100)}.mp4",
                      dur * _CA25_K * 0.97, SAN / "CUOI_REF_97.png")
        print(f"      ảnh mốc 97% để tự nhìn: {SAN / 'CUOI_CHE_97.png'} "
              f"(và ..._REF_97.png)")


def ca20_nhin_bang_mat(src: Path, a: Path, b: Path, vung) -> None:
    """Trích khung TRƯỚC/SAU của FILE XUẤT để NGƯỜI/LLM tự nhìn.

    Cổng KHÔNG tự chấm "nhìn đẹp" — bài học đã đo: mức 0,40 cho mật độ 0,0030
    (máy bảo sạch) mà mắt vẫn đọc được chữ.
    """
    print("\nCA 20 — TRÍCH KHUNG FILE XUẤT ĐỂ NGƯỜI TỰ NHÌN")
    if not (a and b and a.exists() and b.exists()):
        kiem("CA20 có file xuất để trích", False, "thiếu file từ CA 15")
        return
    p1, p2 = SAN / "XUAT_TAT.png", SAN / "XUAT_BAT.png"
    C.trich_khung(a, 5.0, p1)
    C.trich_khung(b, 5.0, p2)
    kiem("CA20 có đủ ảnh XUẤT-TẮT + XUẤT-BẬT",
         p1.exists() and p2.exists() and p1.stat().st_size > 1000)
    print(f"      TẮT: {p1}")
    print(f"      BẬT: {p2}")
    if vung:
        print(f"      (dải chữ trên file xuất: y={vung[0]}..{vung[1]} "
              f"x={vung[2]}..{vung[3]})")


def main() -> int:
    if SAN.exists():
        shutil.rmtree(SAN, ignore_errors=True)
    SAN.mkdir(parents=True, exist_ok=True)
    try:
        ca1_khong_chu()
        p, d = ca2_co_chu()
        ca3_watermark()
        ca4_video_that()
        if d.co_chu:
            ca5_che(p, d)
            ca6_che_hong(p, d)
            o, _ = ca7_viet(p, d)
        else:
            HONG.append("CA2 không dò ra -> bỏ qua CA5/6/7")
            o = p
        ca8_cjk()
        ca9_tu_kiem_tofu()
        ca10_pha_file_rong()
        ca11_pha_nguong()
        ca12_khong_chu_thi_khong_che()
        ca13_khong_tieng()
        ca14_trich_khung_de_nhin(p, o, d)
        ca25_doan_cuoi_video()
        # ---- PHẦN 2: ĐÃ NỐI VÀO ĐƯỜNG XUẤT ----
        ca19_pha_duong_truyen()      # quét tĩnh, rẻ -> chạy trước
        ca23_co_vao_hash_chong_trung()
        ca21_dai_nho_khong_lam_chet_xuat()
        ca18_round_trip_ui()
        that = _nguon_that()
        if that is None:
            HONG.append("KHÔNG có video thật có chữ cháy trong kho -> "
                        "CA15/16/17/20 KHÔNG chạy được (đừng coi là ĐẠT)")
        else:
            print(f"\n(nguồn thật cho CA 15-17-20: {that})")
            xa, xb, vung = ca15_bat_tat_co_tac_dung(that)
            ca22_ghep_doan(that)
            ca24_hop_chu(that)
            ca16_bat_bien(that)
            if os.environ.get("BQ_BO_DO_CHI_PHI", "") != "1":
                ca17_chi_phi(that)
            ca20_nhin_bang_mat(that, xa, xb, vung)
    except Exception:                                          # noqa: BLE001
        traceback.print_exc()
        HONG.append("NGOẠI LỆ giữa chừng")
    print(f"\n{'='*70}\nĐẠT {len(DAT)} · HỎNG {len(HONG)}"
          + (f" · BỎ QUA {len(BO_QUA)}" if BO_QUA else "")
          + f" · cửa sổ ngoài bị chặn: {len(_test_guard.DA_CHAN)}")
    for h in HONG:
        print(f"  HỎNG: {h}")
    # BỎ QUA phải HIỆN RA ở dòng cuối, không được chìm giữa log: mục không
    # chấm mà im lặng thì lượt chạy trông y hệt lượt chấm đủ.
    for b in BO_QUA:
        print(f"  BỎ QUA (máy bận, không chấm): {b}")
    print(f"Ảnh để soi bằng mắt: {SAN}")
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
