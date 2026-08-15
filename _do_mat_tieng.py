# -*- coding: utf-8 -*-
"""ĐO "GIÂY NÀO MẤT TIẾNG" — lỗi 2 (tách giọng hỏng).

Anh Hùng: *"phần tách âm thanh giọng nói, nó nói mà âm thanh sau khi tách lỗi
hết, chỗ có chỗ không nghe không được"*.

Cách đo: dựng ĐƯỜNG BAO RMS theo cửa sổ `BUOC` giây cho từng file audio, rồi
so bản GỐC với bản ĐÃ THAY TIẾNG **trên cùng trục thời gian**. Chỗ nào gốc CÓ
tiếng mà bản mới IM (hoặc tụt sâu) là chỗ mất tiếng — in ra thành BẢNG KHOẢNG
THỜI GIAN, không nói chung chung "có vẻ ổn".

BẪY ĐÃ GHI TRONG CLAUDE.md, tránh sẵn:
· `astats` in mỗi dòng kèm tiền tố `[Parsed_astats_0 @ ...]` -> dùng `in`,
  KHÔNG `startswith`.
· `RMS level dB: -inf` cho cửa sổ im -> phải bắt, không nổ ValueError.
· mọi `subprocess` có `timeout=`.
· stdout utf-8 (chạy `> file.txt` là cp1252 giết cổng trong 0-1 giây).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
FFMPEG = str(REPO / "bin" / "ffmpeg.exe")
FFPROBE = str(REPO / "bin" / "ffprobe.exe")

#: Cửa sổ đo (giây). 0,25 s đủ nhỏ để thấy "mất một câu", đủ lớn để không
#: biến mỗi khoảng lặng giữa hai từ thành một "lỗi".
BUOC = 0.25

#: Dưới mức này coi là IM (dBFS). -60 là ngưỡng "tai không nghe thấy gì" trên
#: nền phim; -inf (cửa sổ digital silence) tất nhiên cũng rơi vào đây.
IM_DB = -60.0

#: Gốc có tiếng ở mức này trở lên thì mới tính là "đáng lẽ phải nghe thấy".
CO_TIENG_DB = -45.0

#: Tụt sâu hơn bấy nhiêu dB so với gốc thì coi là MẤT TIẾNG (dù chưa im hẳn).
TUT_DB = 20.0


def duration(path: str | Path) -> float:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=120)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def duong_bao(path: str | Path, buoc: float = BUOC, sr: int = 44100
              ) -> list[float]:
    """[dBFS] mỗi `buoc` giây. `-inf` -> -120.0 (số hữu hạn để còn vẽ/so)."""
    n = max(1, int(round(sr * buoc)))
    r = subprocess.run(
        [FFMPEG, "-v", "error", "-nostdin", "-i", str(path),
         "-map", "0:a:0", "-af",
         f"aresample={sr},asetnsamples=n={n}:p=0,"
         "astats=metadata=1:reset=1:measure_overall=none:"
         "measure_perchannel=RMS_level,"
         "ametadata=print:key=lavfi.astats.1.RMS_level:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=1800)
    ra: list[float] = []
    for dong in (r.stdout or "").splitlines():
        if "lavfi.astats.1.RMS_level=" not in dong:
            continue
        v = dong.split("=", 1)[1].strip()
        try:
            ra.append(float(v))
        except ValueError:
            ra.append(-120.0)          # '-inf' = im tuyệt đối
    return ra


def gom_khoang(cs: list[int], buoc: float = BUOC) -> list[tuple[float, float]]:
    """[chỉ số cửa sổ] -> [(giây bắt đầu, giây kết thúc)] đã gộp liền kề."""
    ra: list[tuple[float, float]] = []
    for i in cs:
        if ra and abs(ra[-1][1] - i * buoc) < 1e-6:
            ra[-1] = (ra[-1][0], (i + 1) * buoc)
        else:
            ra.append((i * buoc, (i + 1) * buoc))
    return ra


def bang_mat_tieng(goc: list[float], moi: list[float],
                   buoc: float = BUOC) -> dict:
    """So 2 đường bao -> khoảng nào GỐC CÓ tiếng mà BẢN MỚI mất."""
    n = min(len(goc), len(moi))
    im: list[int] = []
    tut: list[int] = []
    for i in range(n):
        g, m = goc[i], moi[i]
        if g < CO_TIENG_DB:
            continue                    # gốc cũng im -> không phải lỗi
        if m < IM_DB:
            im.append(i)
        elif g - m > TUT_DB:
            tut.append(i)
    return {
        "so_cua_so": n,
        "im_han": gom_khoang(im, buoc),
        "tut_sau": gom_khoang(tut, buoc),
        "giay_im": round(len(im) * buoc, 2),
        "giay_tut": round(len(tut) * buoc, 2),
    }


def in_bang(ten: str, kq: dict, tong: float) -> None:
    print(f"\n--- {ten} ---")
    print(f"  cửa sổ đo   : {kq['so_cua_so']} × {BUOC}s")
    print(f"  IM HẲN      : {kq['giay_im']}s "
          f"({100.0 * kq['giay_im'] / max(0.001, tong):.1f}% video)")
    print(f"  TỤT >{TUT_DB:.0f}dB   : {kq['giay_tut']}s "
          f"({100.0 * kq['giay_tut'] / max(0.001, tong):.1f}% video)")
    for nhan, ds in (("IM HẲN", kq["im_han"]), ("TỤT SÂU", kq["tut_sau"])):
        if not ds:
            continue
        print(f"  {nhan}:")
        for a, b in ds:
            if b - a < 0.4:             # bỏ nhiễu 1 cửa sổ lẻ
                continue
            print(f"    {a:7.2f}s -> {b:7.2f}s   ({b - a:5.2f}s)")


def main() -> int:
    if len(sys.argv) < 3:
        print("Dùng: python -u _do_mat_tieng.py <goc.mp4> <moi.mp4> [...]")
        return 2
    goc_p = sys.argv[1]
    tong = duration(goc_p)
    print(f"GỐC: {Path(goc_p).name}  ({tong:.2f}s)")
    goc = duong_bao(goc_p)
    print(f"  đường bao gốc: {len(goc)} cửa sổ, "
          f"cao nhất {max(goc):.1f} dB, thấp nhất {min(goc):.1f} dB")

    for p in sys.argv[2:]:
        moi = duong_bao(p)
        print(f"\nSO VỚI: {Path(p).name}  ({duration(p):.2f}s, "
              f"{len(moi)} cửa sổ)")
        in_bang(Path(p).name, bang_mat_tieng(goc, moi), tong)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
