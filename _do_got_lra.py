# -*- coding: utf-8 -*-
"""HIỆU CHUẨN: NÂNG THUẦN + HẠN ĐỈNH GỌT BAO NHIÊU THÌ BẮT ĐẦU **NÉN DẬP**?

VIỆC 1 đòi *"phải chứng minh KHÔNG nén dập: LRA trước/sau, đổi quá 0,2 là có
vấn đề"*. Với đường THAY TIẾNG chuyện đó dễ (bản trộn LRA 2,10, cần nâng 2 dB,
chỗ trống thừa). Với đường CẮT THƯỜNG thì **KHÔNG**: `_kq_lufs_duong.json` có
clip đo được **I −22,40 LUFS mà đỉnh thật +0,94 dBTP** — hệ số đỉnh/độ to
**23,3 dB**. Nâng nó về −14 là `alimiter` phải gọt **10,84 dB**.

Nên câu hỏi KHÔNG phải "có được gọt không" mà là **"gọt tới đâu thì LRA bắt
đầu đổi"** — và đó là câu hỏi phải ĐO, không được suy.

Cách đo: giữ nguyên trần `alimiter`, quét NGÂN SÁCH GỌT (kẹp hệ số nâng lại
sao cho `TP + nâng` không vượt `trần + ngân sách`), rồi đo lại I/TP/LRA.

**THƯỚC CHÍNH LÀ `ebur128`, KHÔNG PHẢI `loudnorm` — ĐÃ TRUY RA, xem
`_do_hai_thuoc.py`.** Lượt đầu của chính file này DỪNG vì hai thước lệch 0,58
LU. Truy tiếp bằng **thước THỨ BA tự viết** (ITU-R BS.1770-4 bằng numpy, không
qua ffmpeg) thì thước 3 đứng cách `ebur128` **0,008 LU** và cách `loudnorm`
**0,572 LU** -> `loudnorm` pha đo ĐỌC THẤP, cả 8 bản xuất đều lệch cùng chiều
ÂM (−0,12 .. −0,58 LU). Nền tảng nhận clip (YouTube/TikTok) đo theo BS.1770,
nên lấy `loudnorm` làm đích là ĐẨY CLIP TO HƠN đích thật tới 0,6 LU.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _do_lufs import do_ebur128, do_loudnorm  # noqa: E402

FF = REPO / "bin" / "ffmpeg.exe"
DICH = -14.0
TRAN_TP = -1.0
BIEN = 0.5                      # trừ hao 2 lớp: alimiter +0,06 · AAC +0,19
TRAN_LIM = TRAN_TP - BIEN       # = -1,5
NGAN_SACH = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 99.0]   # dB gọt cho phép


def _lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _ap(src: Path, dst: Path, nang: float) -> None:
    """Nâng thuần + hạn đỉnh, GIỮ NGUYÊN hình (`-c:v copy`)."""
    cmd = [str(FF), "-y", "-hide_banner", "-nostdin", "-i", str(src),
           "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
           "-af", (f"volume={nang:.3f}dB,"
                   f"alimiter=limit={_lin(TRAN_LIM):.6f}"
                   f":level=0:latency=1:attack=1:release=10"),
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, timeout=900,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg mã {r.returncode}: "
                           f"{(r.stderr or b'').decode('utf-8', 'replace')[-400:]}")
    if not dst.exists() or dst.stat().st_size < 1024:
        raise RuntimeError(f"ffmpeg mã 0 mà file rỗng: {dst}")


def main() -> int:
    tam = REPO / "_do_duong"
    files = sorted(tam.glob("*.mp4"))
    if not files:
        print("KHÔNG có file trong _do_duong/ — chạy _do_lufs_duong.py trước.")
        return 2

    print("=" * 92)
    print("BƯỚC 1 — ĐO LẠI 8 BẢN XUẤT, tính hệ số cần nâng + phần phải GỌT")
    print("=" * 92)
    print(f"{'file':16} {'I':>8} {'TP':>7} {'LRA':>6} {'nâng':>7} "
          f"{'đỉnh sau nâng':>14} {'phải gọt':>9}")
    bang = []
    for f in files:
        eb = do_ebur128(f)                    # THƯỚC CHÍNH
        ln = do_loudnorm(f)                   # thước thứ 2, chỉ để đối chiếu
        nang = DICH - eb["I"]
        dinh = eb["TP"] + nang
        got = max(0.0, dinh - TRAN_LIM)
        bang.append({"file": f.name, "I": eb["I"], "TP": eb["TP"],
                     "LRA": eb["LRA"], "I_ln": ln["input_i"],
                     "nang": nang, "got": got})
        print(f"{f.name:16} {eb['I']:8.2f} {eb['TP']:7.2f} "
              f"{eb['LRA']:6.2f} {nang:+7.2f} {dinh:+14.2f} {got:9.2f}")

    xau = max(bang, key=lambda r: r["got"])
    print(f"\nCA XẤU NHẤT: {xau['file']} — phải gọt {xau['got']:.2f} dB "
          f"(hệ số đỉnh/độ to {xau['TP'] - xau['I']:.1f} dB)")

    print("\n" + "=" * 92)
    print("BƯỚC 2 — QUÉT NGÂN SÁCH GỌT trên ca xấu nhất: LRA đổi từ mốc nào?")
    print("=" * 92)
    src = tam / xau["file"]
    ra = []
    print(f"{'ngân sách':>10} {'nâng thật':>10} {'I sau':>8} {'TP sau':>8} "
          f"{'LRA sau':>8} {'ΔLRA':>7} {'ΔI so đích':>11}")
    for ns in NGAN_SACH:
        # kẹp hệ số nâng: TP + nâng <= TRAN_LIM + ngân sách
        nang = min(xau["nang"], (TRAN_LIM + ns) - xau["TP"])
        out = REPO / "_do_duong" / f"_got_{int(ns * 10):03d}.mp4"
        _ap(src, out, nang)
        eb = do_ebur128(out)
        d_lra = eb["LRA"] - xau["LRA"]
        ra.append({"ngan_sach": ns, "nang": round(nang, 2),
                   "I": round(eb["I"], 2), "TP": round(eb["TP"], 2),
                   "LRA": round(eb["LRA"], 2), "d_LRA": round(d_lra, 2)})
        print(f"{ns:10.1f} {nang:+10.2f} {eb['I']:8.2f} "
              f"{eb['TP']:8.2f} {eb['LRA']:8.2f} {d_lra:+7.2f} "
              f"{eb['I'] - DICH:+11.2f}")
        out.unlink(missing_ok=True)

    (REPO / "_kq_got_lra.json").write_text(
        json.dumps({"bang": bang, "quet": ra, "ca_xau": xau["file"]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_got_lra.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
