"""Dựng BẢNG DẢI PHỤ ĐỀ để TÔI NHÌN TẬN MẮT rồi tự ghi nhãn.

Mỗi hàng = dải phụ đề (cắt từ khung ở GIỮA đoạn) + số thứ tự đoạn đốt vào ảnh.
Không đếm điểm ảnh để kết luận — số chỉ dùng xếp thứ tự; nhãn do mắt tôi ghi.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_bang.py <ten_video> [moi_bang]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
BANG = SAN / "bang"
FF = str(GOC / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0
#: phông có sẵn trong repo (ffmpeg drawtext cần đường dẫn tường minh)
FONT = (GOC / "app" / "assets" / "fonts" / "BeVietnamPro-Bold.ttf")

RONG = 620          # bề rộng mỗi dải sau khi thu nhỏ
LE = 96            # chỗ trống bên trái để ghi số thứ tự
KHE = 5            # khe trắng giữa 2 dải


def _ff(args: list[str], timeout: int = 300) -> None:
    r = subprocess.run([FF, "-y", "-v", "error", *args], capture_output=True,
                       text=True, creationflags=_NO_WIN, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg {r.returncode}: {(r.stderr or '')[:400]}")


def dai_mot(video: str, t: float, y0: int, y1: int, W: int, nhan: str,
            out: Path, them: int = 26) -> None:
    """Cắt dải phụ đề (nới thêm `them` px mỗi phía cho thấy cả chóp/chân chữ)."""
    yy0 = max(0, y0 - them)
    hh = (y1 - y0) + them * 2
    fpath = str(FONT).replace("\\", "/").replace(":", "\\:")
    vf = (f"crop={W}:{hh}:0:{yy0},scale={RONG}:-1,"
          f"pad=iw+{LE}:ih:{LE}:0:color=white,"
          f"drawtext=fontfile='{fpath}':text='{nhan}':x=4:y=(h-th)/2:"
          f"fontsize=20:fontcolor=black")
    _ff(["-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", vf,
         str(out)])


def main() -> None:
    ten = sys.argv[1] if len(sys.argv) > 1 else "v4_khuyendung"
    moi = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    BANG.mkdir(parents=True, exist_ok=True)
    pd = json.loads((SAN / "phude.json").read_text(encoding="utf-8"))[ten]
    video = str(SAN / "video" / f"{ten}.mp4")
    rows = pd["rows"]
    tam = BANG / f"_tam_{ten}"
    tam.mkdir(exist_ok=True)

    files = []
    for r in rows:
        nhan = f"{r['i']:3d}"
        p = tam / f"{r['i']:04d}.png"
        if not p.exists():
            dai_mot(video, float(r["t"]), pd["y0"], pd["y1"], pd["W"],
                    nhan, p)
        files.append(p)

    n_bang = 0
    for k in range(0, len(files), moi):
        lo = files[k:k + moi]
        ins = []
        for p in lo:
            ins += ["-i", str(p)]
        fc = (f"vstack=inputs={len(lo)}" if len(lo) > 1 else "null")
        chain = "".join(f"[{i}:v]pad=iw:ih+{KHE}:0:0:color=white[p{i}];"
                        for i in range(len(lo)))
        chain += "".join(f"[p{i}]" for i in range(len(lo))) + fc + "[o]"
        out = BANG / f"{ten}_b{n_bang:02d}.png"
        _ff([*ins, "-filter_complex", chain, "-map", "[o]", str(out)])
        print(f"{out}  doan {lo[0].stem.lstrip('0') or '0'}..{lo[-1].stem.lstrip('0')}")
        n_bang += 1
    print(f"XONG {n_bang} bang cho {ten}")


if __name__ == "__main__":
    main()
