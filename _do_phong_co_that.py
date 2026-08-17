"""PHÔNG NÀO THẬT SỰ VẼ RA ĐƯỢC — đo, không đoán.

Cách đo: vẽ CÙNG một câu tiếng Việt lên nền phẳng bằng từng tên phông, rồi so
với arm ĐỐI CHỨNG dùng một tên phông BỊA. Trùng từng byte với arm bịa = libass
KHÔNG tìm thấy phông đó, nó lùi về phông mặc định **mà vẫn trả mã 0** — đúng
cái làm ô "chọn phông" thành cái nhãn vô nghĩa.

Kèm đo TOFU: đếm điểm ảnh chữ. Ô vuông tofu ĐẶC hơn chữ thật nên số ĐẾM cao
BẤT THƯỜNG (đo 14/08: tofu 2.431 px vs chữ thật 517 px) — số này chỉ để KHOANH
VÙNG nghi ngờ, chốt cuối vẫn là MỞ ẢNH RA NHÌN.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
FF = REPO / "bin" / "ffmpeg.exe"
FONTS = REPO / "app" / "assets" / "fonts"
HOP = REPO / "_kc_phong"
CAU = "Chào bạn, chữ Việt đủ dấu: ăâêôơư ĐỀU ỔN 123"
BIA = "PhongBiaKhongTonTai12345"


def esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def ve(ten_phong: str, ra: Path) -> tuple[str, int]:
    """Vẽ CAU bằng `ten_phong` lên nền đen 1400x200 -> (md5, số điểm ảnh chữ)."""
    ass = HOP / "t.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 2\n"
        "ScaledBorderAndShadow: yes\nPlayResX: 1400\nPlayResY: 200\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: T,{ten_phong},56,&H00FFFFFF,&H00FFFFFF,&H00000000,"
        "&H64000000,0,0,0,0,100,100,0,0,1,3,0,5,10,10,10,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,"
        f"{{\\an5\\pos(700,100)}}{CAU}\n", encoding="utf-8")
    r = subprocess.run(
        [str(FF), "-y", "-v", "error", "-f", "lavfi", "-t", "1",
         "-i", "color=c=black:s=1400x200:r=5",
         "-vf", f"subtitles='{esc(ass)}':fontsdir='{esc(FONTS)}'",
         "-frames:v", "1", str(ra)], capture_output=True, timeout=120)
    if r.returncode != 0 or not ra.exists():
        return ("LOI", -1)
    from PIL import Image
    im = Image.open(ra).convert("L")
    px = im.load()
    w, h = im.size
    n = sum(1 for y in range(h) for x in range(w) if px[x, y] > 200)
    return (hashlib.md5(ra.read_bytes()).hexdigest(), n)


def main() -> int:
    HOP.mkdir(exist_ok=True)
    ung = ["Montserrat", "Be Vietnam Pro", "Anton", "Bungee", "Baloo 2",
           "Baloo2", "Oswald", "Lexend", "Pattaya", "Nunito", "Lobster",
           "Pacifico", "Arial", "Segoe UI", "Tahoma", "Verdana",
           "Times New Roman"]
    md5_bia, px_bia = ve(BIA, HOP / "_bia.png")
    print(f"ĐỐI CHỨNG (tên phông BỊA): {md5_bia[:12]} · {px_bia} px chữ\n")
    print(f"{'phông':<20}{'px chữ':>8}  kết luận")
    co, khong = [], []
    for f in ung:
        md5, n = ve(f, HOP / f"{f.replace(' ', '_')}.png")
        if md5 == "LOI":
            print(f"{f:<20}{'-':>8}  ffmpeg LỖI")
            khong.append(f)
        elif md5 == md5_bia:
            print(f"{f:<20}{n:>8}  KHÔNG CÓ (trùng từng byte arm bịa)")
            khong.append(f)
        else:
            print(f"{f:<20}{n:>8}  CÓ THẬT")
            co.append(f)
    print(f"\nDÙNG ĐƯỢC ({len(co)}): {co}")
    print(f"KHÔNG CÓ  ({len(khong)}): {khong}")
    print(f"\nẢNH ở {HOP} — MỞ RA NHÌN xem có ô vuông tofu không.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
