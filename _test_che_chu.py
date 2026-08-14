# -*- coding: utf-8 -*-
"""CỔNG 54 — CHỮ CHÁY SẴN TRONG HÌNH (`app/core/che_chu.py`).

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

import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)                      # KHÔNG ghi cứng đường repo
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard                            # noqa: E402,F401  chặn cửa sổ ngoài
import numpy as np                            # noqa: E402
from app.core import che_chu as C             # noqa: E402

#: Sandbox nằm trên D:, KHÔNG dùng %TEMP% (luật: không để rác %TEMP% máy user).
SAN = Path(os.environ.get("BQ_CHE_CHU_TEST", r"D:\claude\_do_che_chu\_test"))
KHO = Path(r"D:\claude\_do_che_chu\nguon")     # video thật đã copy ra sandbox

DAT: list = []
HONG: list = []


def kiem(ten: str, ok: bool, chi_tiet: str = "") -> bool:
    (DAT if ok else HONG).append(ten)
    print(f"  {'ĐẠT ' if ok else 'HỎNG'} {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return ok


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
    except Exception:                                          # noqa: BLE001
        traceback.print_exc()
        HONG.append("NGOẠI LỆ giữa chừng")
    print(f"\n{'='*70}\nĐẠT {len(DAT)} · HỎNG {len(HONG)}"
          f" · cửa sổ ngoài bị chặn: {len(_test_guard.DA_CHAN)}")
    for h in HONG:
        print(f"  HỎNG: {h}")
    print(f"Ảnh để soi bằng mắt: {SAN}")
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
