# -*- coding: utf-8 -*-
r"""ĐO MỤC A (3)+(4) — CHỮ HÁN CÓ HIỆN ĐƯỢC TRÊN VIDEO KHÔNG, VÀ BẰNG FONT NÀO.

    .venv\Scripts\python _do_han_hien.py

Vì sao phải có script này: font thiếu glyph thì libass vẽ Ô VUÔNG (tofu) hoặc
KHÔNG VẼ GÌ, mà ffmpeg **vẫn trả mã 0** và file vẫn đủ khung -> cổng đếm khung /
xem mã thoát PASS OAN. Ở đây:
  (a) đếm ĐIỂM ẢNH TỪNG KÝ TỰ, so với mốc "chắc chắn không font nào có"
      (U+E000 vùng dùng riêng) và mốc "chắc chắn có" (chữ A latin);
  (b) đọc log `-loglevel debug` của libass xem nó CHỌN font nào, thiếu glyph nào;
  (c) xuất ảnh cả câu để MẮT NGƯỜI nhìn.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
(WORK / "han").mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"
import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF = str(REPO / "bin" / "ffmpeg.exe")
_NOWIN = 0x08000000 if os.name == "nt" else 0
FONTS = str(REPO / "app" / "assets" / "fonts")
OUT = WORK / "han"
W, H = 1080, 1920

# câu THẬT lấy từ bản chép lời tiếng Trung (Groq) + tên video của anh Hùng
CAU = "一只手表牵扯出一个巨大的秘密他们借助金属探测仪仔细检查了整片区域"
# 2 mốc đối chứng: U+E000 = vùng DÙNG RIÊNG (không font nào có -> tofu/trắng),
# 'A' = chắc chắn có.
PUA = ""


def _esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def dem(png: Path, nguong: int = 200) -> int:
    import cv2
    im = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    return -1 if im is None else int((im >= nguong).sum())


def _bam(png: Path) -> str:
    """Vân tay ảnh — TOFU của MỌI ký tự thiếu glyph là CÙNG MỘT hình chữ nhật
    rỗng, nên so vân tay với ảnh mốc U+E000 là cách đúng để bắt ô vuông.
    ĐẾM ĐIỂM ẢNH KHÔNG ĐỦ: đo được ô tofu 2.961 px trong khi chữ '一' (một nét
    ngang) chỉ 2.624 px -> ngưỡng theo số px kết luận ngược."""
    import hashlib
    return hashlib.sha1(png.read_bytes()).hexdigest()[:12] if png.exists() \
        else "KHONG_CO"


def kho_font_co_cjk():
    """Font đóng gói trong app/assets/fonts có bao nhiêu glyph CJK?"""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("    (thiếu fontTools -> bỏ qua phép đếm glyph)")
        return None
    ra = []
    for f in sorted(Path(FONTS).glob("*.tt[fc]")):
        try:
            t = TTFont(str(f), fontNumber=0, lazy=True)
            cm = set(t.getBestCmap().keys())
            t.close()
        except Exception as ex:                      # noqa: BLE001
            ra.append((f.name, -1, str(ex)[:40]))
            continue
        n = len([o for o in cm if 0x4E00 <= o <= 0x9FFF
                 or 0x3040 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF])
        ra.append((f.name, n, ""))
    return ra


def _ass_mot_ky_tu(ky_tu: list, dst: Path, font: str) -> None:
    """.ass thủ công: ký tự thứ i hiện trong [i, i+1) giây -> MỘT lượt ffmpeg
    lấy được hết khung (1 fps). Dựng tay để đo ĐÚNG font/cỡ, không lệ thuộc
    preset."""
    dong = []
    for i, c in enumerate(ky_tu):
        a = f"0:00:{i:02d}.00"
        b = f"0:00:{i:02d}.90"
        dong.append(f"Dialogue: 0,{a},{b},Default,,0,0,0,,{c}")
    dst.write_text(
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},220,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,60,60,60,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n" + "\n".join(dong) + "\n",
        encoding="utf-8")


def quet_tung_ky_tu(font: str, nhan: str):
    """Render MỖI ký tự 1 khung -> đếm px. Trả (dict char->px, log libass)."""
    ky_tu = [PUA, "A", "字"] + sorted(set(CAU))
    ass = OUT / f"quet_{nhan}.ass"
    _ass_mot_ky_tu(ky_tu, ass, font)
    thu = OUT / nhan
    thu.mkdir(exist_ok=True)
    for f in thu.glob("*.png"):
        f.unlink()
    r = subprocess.run(
        [FF, "-y", "-loglevel", "debug", "-f", "lavfi",
         "-i", f"color=c=black:s={W}x{H}:r=1:d={len(ky_tu)}",
         "-vf", f"subtitles='{_esc(ass)}':fontsdir='{_esc(FONTS)}'",
         "-fps_mode", "passthrough", str(thu / "k_%03d.png")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=900, creationflags=_NOWIN)
    print(f"    ffmpeg rc={r.returncode} (MÃ THOÁT THẬT) · "
          f"{len(list(thu.glob('*.png')))} khung")
    px, bam = {}, {}
    for i, c in enumerate(ky_tu, 1):
        p = thu / f"k_{i:03d}.png"
        px[c] = dem(p) if p.exists() else -1
        bam[c] = _bam(p)
    fonts_dung, thieu = [], []
    for ln in (r.stderr or "").splitlines():
        m = re.search(r"fontselect: \(.*?\) -> (\S+?),", ln)
        if m and m.group(1) not in fonts_dung:
            fonts_dung.append(m.group(1))
        m2 = re.search(r"Glyph (0x[0-9A-Fa-f]+) not found", ln)
        if m2:
            thieu.append(chr(int(m2.group(1), 16)))
    return px, bam, fonts_dung, thieu


def anh_ca_cau(font: str, nhan: str) -> Path:
    """1 ảnh chứa CẢ CÂU (chia 4 dòng) để MẮT NGƯỜI nhìn."""
    n = 8
    dong = [CAU[i:i + n] for i in range(0, len(CAU), n)]
    txt = "\\N".join(dong)
    ass = OUT / f"cau_{nhan}.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
        "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},110,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H00000000,-1,0,0,0,100,100,0,0,1,4,0,5,40,40,40,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{txt}\n",
        encoding="utf-8")
    png = OUT / f"cau_{nhan}.png"
    subprocess.run(
        [FF, "-y", "-v", "error", "-f", "lavfi",
         "-i", f"color=c=black:s={W}x{H}:d=2",
         "-vf", f"subtitles='{_esc(ass)}':fontsdir='{_esc(FONTS)}'",
         "-frames:v", "1", str(png)],
        capture_output=True, timeout=600, creationflags=_NOWIN)
    return png


#: chữ mà bản NHẬT và bản TRUNG GIẢN THỂ vẽ KHÁC HÌNH (cùng codepoint).
#: Dùng để đo: libass lùi font sang YuGothic (NHẬT) thì người Trung xem ra chữ
#: hơi lạ mắt — ffmpeg vẫn mã 0, đếm điểm ảnh vẫn "có chữ".
KHAC_NHAT_TRUNG = "直骨每画者步海角兔強次令"
#: NHÓM ĐỐI CHỨNG — chữ mà Nhật và Trung vẽ GIỐNG NHAU. Không có nhóm này thì
#: phép đo vô nghĩa: YaHei và YuGothic là 2 kiểu chữ khác nhau nên MỌI ký tự
#: đều lệch điểm ảnh, kể cả ký tự cùng hình.
GIONG_NHAT_TRUNG = "山日人大中小田力口目木火水金土"


def main() -> int:
    print(f"[work] {OUT}")
    print(f"[câu đo] {CAU}  ({len(set(CAU))} ký tự khác nhau)")

    print("\n══ (4a) FONT ĐÓNG GÓI TRONG APP CÓ GLYPH CJK KHÔNG ══")
    kho = kho_font_co_cjk()
    if kho is not None:
        tong = 0
        for ten, n, loi in kho:
            tong += max(0, n)
            print(f"    {ten:<28} glyph CJK = {n}{'  ' + loi if loi else ''}")
        print(f"    -> TỔNG glyph CJK của {len(kho)} font đóng gói: {tong}")

    ket, bam_ref = {}, {}
    for font, nhan in (("Montserrat", "montserrat"),
                       ("Microsoft YaHei", "msyh"),
                       ("SimHei", "simhei")):
        print(f"\n══ FONT KHAI TRONG .ass = '{font}' ══")
        px, bam, fonts_dung, thieu = quet_tung_ky_tu(font, nhan)
        base, base_bam = px.get(PUA, -1), bam.get(PUA, "")
        latin = px.get("A", -1)
        han = {c: v for c, v in px.items() if c not in (PUA, "A")}
        # TOFU THẬT = ảnh GIỐNG HỆT ảnh mốc U+E000 (mọi ký tự thiếu glyph vẽ ra
        # cùng một ô rỗng). Đây mới là bộ dò đúng.
        tofu = [c for c in han if bam.get(c) == base_bam]
        theo_px = [c for c, v in han.items() if v <= max(0, base)]
        print(f"    libass CHỌN font: {fonts_dung}")
        print(f"    glyph BÁO THIẾU (trước khi lùi font): "
              f"{len(thieu)} — {''.join(thieu[:20])}")
        print(f"    mốc U+E000 (tofu) = {base} px vân tay {base_bam}  ·  "
              f"'A' latin = {latin} px")
        vs = sorted(han.values())
        print(f"    chữ Hán: {len(han)} ký tự · px min {vs[0]} · "
              f"trung vị {vs[len(vs)//2]} · max {vs[-1]}")
        print(f"    Ô VUÔNG THẬT (ảnh giống hệt mốc tofu): {len(tofu)} "
              f"{''.join(tofu)}")
        print(f"    (bộ dò NGÂY THƠ 'px <= mốc tofu' báo {len(theo_px)}: "
              f"{''.join(theo_px)} -> ĐẾM PX LÀ SAI, '一' chỉ 1 nét ngang)")
        cau_png = anh_ca_cau(font, nhan)
        print(f"    ảnh CẢ CÂU để nhìn bằng mắt: {cau_png}")
        ket[font] = (base, latin, len(tofu), fonts_dung, cau_png)
        bam_ref[font] = bam

    print("\n══ (4b) LÙI FONT SANG NHẬT: chữ có vẽ KHÁC bản TRUNG không ══")
    import cv2
    CHU = KHAC_NHAT_TRUNG + GIONG_NHAT_TRUNG
    for nhan, font in (("cmp_mont", "Montserrat"),
                       ("cmp_yahei", "Microsoft YaHei")):
        ass = OUT / f"{nhan}.ass"
        _ass_mot_ky_tu(list(CHU), ass, font)
        thu = OUT / nhan
        thu.mkdir(exist_ok=True)
        for f in thu.glob("*.png"):
            f.unlink()
        subprocess.run(
            [FF, "-y", "-v", "error", "-f", "lavfi",
             "-i", f"color=c=black:s={W}x{H}:r=1:d={len(CHU)}",
             "-vf", f"subtitles='{_esc(ass)}':fontsdir='{_esc(FONTS)}'",
             "-fps_mode", "passthrough", str(thu / "k_%03d.png")],
            capture_output=True, timeout=900, creationflags=_NOWIN)

    def _lech(i):
        pa = OUT / "cmp_mont" / f"k_{i+1:03d}.png"
        pb = OUT / "cmp_yahei" / f"k_{i+1:03d}.png"
        if not (pa.exists() and pb.exists()):
            return None
        a = cv2.imread(str(pa), cv2.IMREAD_GRAYSCALE)
        b = cv2.imread(str(pb), cv2.IMREAD_GRAYSCALE)
        if a is None or b is None:
            return None
        d = int((cv2.absdiff(a, b) > 40).sum())
        return 100.0 * d / max(1, int((a >= 200).sum()))

    nhom = {}
    for ten, chuoi, off in (("KHÁC hình JP/CN", KHAC_NHAT_TRUNG, 0),
                            ("GIỐNG hình (đối chứng)", GIONG_NHAT_TRUNG,
                             len(KHAC_NHAT_TRUNG))):
        ds = []
        for j, c in enumerate(chuoi):
            v = _lech(off + j)
            if v is None:
                continue
            ds.append(v)
            print(f"    [{ten:<22}] '{c}'  lệch {v:6.1f}% nét chữ")
        ds.sort()
        nhom[ten] = ds
        print(f"    -> {ten}: trung vị {ds[len(ds)//2]:.1f}% "
              f"(min {ds[0]:.1f} · max {ds[-1]:.1f})")
    a, b = nhom["KHÁC hình JP/CN"], nhom["GIỐNG hình (đối chứng)"]
    print(f"    KẾT LUẬN: nhóm KHÁC-hình {a[len(a)//2]:.1f}% vs nhóm ĐỐI CHỨNG "
          f"{b[len(b)//2]:.1f}% — chênh {a[len(a)//2] - b[len(b)//2]:+.1f} điểm "
          "%. Chênh NHỎ = phép đo chỉ nói 'hai kiểu chữ khác nhau', KHÔNG "
          "chứng minh được lùi-font làm sai HÌNH chữ.")

    print("\n══ (4c) BẢN VÁ `captions.font_cjk`: khai thẳng font CJK có thật ══")
    from app.core import captions as C
    CAU_NHAT = "これは誰も語らなかった話です"
    CAU_HAN = "아무도 말하지 않은 이야기"
    for nhan, cau in (("TRUNG", CAU), ("NHẬT", CAU_NHAT), ("HÀN", CAU_HAN),
                      ("ANH (đối chứng)", "this is the story"),
                      ("VIỆT (đối chứng)", "chuyện này không ai kể")):
        chon = C.font_cjk(cau, "Montserrat")
        print(f"    {nhan:<18} font_cjk('Montserrat') -> '{chon}'")
        if chon == "Montserrat":
            continue
        px, bam, fonts_dung, thieu = quet_tung_ky_tu(
            chon, "vachon_" + nhan.split()[0].lower())
        base = px.get(PUA, -1)
        tofu = [c for c in px if c not in (PUA, "A")
                and bam.get(c) == bam.get(PUA)]
        print(f"        libass CHỌN: {fonts_dung} (số lượt LÙI FONT = "
              f"{max(0, len(fonts_dung) - 1)}) · ô vuông = {len(tofu)}")

    print("\n══ TỔNG ══")
    for k, (b, la, tr, fo, p) in ket.items():
        print(f"  {k:<18} ô-vuông={tr:2d} · mốc tofu={b:5d}px · A={la:5d}px · "
              f"font THẬT={fo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
