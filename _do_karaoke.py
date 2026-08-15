# -*- coding: utf-8 -*-
"""LỖI 1 — ĐO HAI CÁCH LÀM "CHỮ CHẠY THEO LỜI": thẻ karaoke `\\k` vs CỤM NỐI TIẾP.

Yêu cầu là ĐO cả hai rồi chọn, không chọn theo cảm tính. Thước đúng cho câu
anh Hùng kêu (*"không hiện hàng loạt ra chữ như thế kia"*) là:

    **BAO NHIÊU CHỮ ĐANG NẰM TRÊN MÀN HÌNH tại một thời điểm.**

Đo bằng cách RENDER THẬT qua libass (`ffmpeg -vf subtitles=`) trên nền phẳng
rồi ĐẾM ĐIỂM ẢNH CHỮ — không suy luận từ mã.

Đo thêm ca hỏng của `\\k`: nền tảng/trình phát NUỐT thẻ (hoặc style chỉ có 1
màu) thì còn lại đúng cái khối chữ cũ. Mô phỏng bằng cách bỏ thẻ `\\k` — đó
chính là thứ người xem thấy khi thẻ không được hiểu.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
FFMPEG = str(REPO / "bin" / "ffmpeg.exe")

W, H = 1080, 1920
#: Câu THẬT lấy từ ảnh anh Hùng gửi 15/08 — đúng khối 3 dòng đang bị kêu.
CAU = ("Bộ đầu tiên là Chiến binh ngầm, nói về một võ sĩ xuống đáy xã hội "
       "bước vào đấu trường bất hợp pháp, chiến đấu để sống sót trong môi "
       "trường không có quy tắc.")
BAT_DAU, KET_THUC = 0.0, 9.6


def _head(mau2: str = "&H0000FFFF") -> str:
    return (
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {W}\nPlayResY: {H}\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: T,Arial,58,&H00FFFFFF,{mau2},&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,3,0,2,60,60,120,1\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n")


def _tg(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_karaoke(p: Path, bo_the: bool = False) -> None:
    """MỘT dòng duy nhất cho cả câu, tô dần bằng `\\k` (đơn vị 1/100 giây)."""
    tu = CAU.split()
    d = (KET_THUC - BAT_DAU) / max(1, len(tu))
    if bo_the:
        than = " ".join(tu)          # trình phát nuốt thẻ = còn đúng khối chữ
    else:
        than = "".join(f"{{\\k{int(round(d * 100))}}}{w} " for w in tu).strip()
    p.write_text(_head() + f"Dialogue: 0,{_tg(BAT_DAU)},{_tg(KET_THUC)},T,,"
                 f"0,0,0,,{than}\n", encoding="utf-8")


def ass_cum(p: Path, tran: int = 30) -> None:
    """NHIỀU dòng nối tiếp, mỗi dòng <= `tran` ký tự (cách app đang dùng)."""
    from app.core import thay_giong as tg
    cum = tg.chia_cum_theo_ty_le(CAU, BAT_DAU, KET_THUC, tran)
    dong = []
    for i, (a, _b, s) in enumerate(cum):
        ket = cum[i + 1][0] if i + 1 < len(cum) else KET_THUC
        dong.append(f"Dialogue: 0,{_tg(a)},{_tg(ket)},T,,0,0,0,,{s}")
    p.write_text(_head() + "\n".join(dong) + "\n", encoding="utf-8")


def _duong_loc(p: Path) -> str:
    r"""Đường dẫn cho filter `subtitles=`. BẪY WINDOWS: dấu `:` của ổ đĩa là
    KÝ TỰ NGĂN THAM SỐ của ffmpeg -> `D:/...` làm cả filter chết IM LẶNG (đo
    ra 0 file PNG, cột đếm toàn -1). Phải thoát thành `D\:/...`."""
    return p.as_posix().replace(":", "\\:")


def dem_pixel_chu(ass: Path, t: float, png: Path) -> int:
    """Số điểm ảnh KHÁC nền tại giây `t` — nền phẳng nên đếm được thẳng.

    CHỌN KHUNG BẰNG `select=between(t,...)` NGAY SAU `subtitles`, không dùng
    `-ss`: `-ss` seek TRƯỚC bộ lọc nên libass vẫn vẽ mốc 0 và **cả 4 cột ra
    số y hệt nhau** — bản đầu của phép đo này đã ra đúng như thế và trông
    hoàn toàn hợp lý (karaoke đứng im là đúng, nên không ai nghi cột kia).
    """
    subprocess.run(
        [FFMPEG, "-y", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
         f"color=c=0x101820:s={W}x{H}:d=12:r=10",
         "-vf", f"subtitles='{_duong_loc(ass)}',"
                f"select='between(t,{t:.2f},{t + 0.09:.2f})'",
         "-fps_mode", "passthrough", "-frames:v", "1", str(png)],
        capture_output=True, text=True, timeout=300)
    if not png.exists():
        return -1
    r2 = subprocess.run(
        [FFMPEG, "-v", "error", "-nostdin", "-i", str(png), "-vf",
         "format=gray,lutyuv=y='if(gt(val,90),255,0)',"
         "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
         "-f", "null", "-"], capture_output=True, text=True, timeout=180)
    for dong in (r2.stdout or "").splitlines():
        if "YAVG=" in dong:
            try:
                return int(round(float(dong.split("=")[1]) / 255.0 * W * H))
            except ValueError:
                return -1
    return -1


def main() -> int:
    tam = REPO / "_do_lt" / "_kara"
    tam.mkdir(parents=True, exist_ok=True)
    print(f"CÂU THẬT ({len(CAU)} ký tự, khung {KET_THUC - BAT_DAU:.1f} giây):")
    print(f"  {CAU}\n")

    bo = {
        "karaoke \\k (thẻ CHẠY)": (tam / "kara.ass", ass_karaoke, {}),
        "karaoke \\k (thẻ BỊ NUỐT)": (tam / "kara_nuot.ass", ass_karaoke,
                                      {"bo_the": True}),
        "cụm nối tiếp (trần 30)": (tam / "cum.ass", ass_cum, {}),
    }
    for ten, (p, fn, kw) in bo.items():
        fn(p, **kw)

    moc = [1.0, 3.0, 5.0, 8.0]
    print(f"{'cách làm':30} " + " ".join(f"{f'{t:.0f}s':>9}" for t in moc)
          + "   ghi chú")
    for ten, (p, _fn, _kw) in bo.items():
        cot = []
        for t in moc:
            cot.append(dem_pixel_chu(p, t, tam / f"{p.stem}_{int(t)}.png"))
        so_dong = sum(1 for x in p.read_text(encoding="utf-8").splitlines()
                      if x.startswith("Dialogue:"))
        print(f"{ten:30} " + " ".join(f"{c:>9}" for c in cot)
              + f"   {so_dong} dòng Dialogue")
    print("\nSố ở trên = ĐIỂM ẢNH CHỮ đang nằm trên màn hình tại giây đó.")
    print("Ảnh để tự nhìn:", tam)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
