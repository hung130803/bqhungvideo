# -*- coding: utf-8 -*-
"""ĐO ĐỘ TO TÍCH HỢP (LUFS) — anh Hùng: *"phần giọng nói ít tiếng quá"*.

Nghi vấn: lượt chữa "giọng chìm dưới nhạc" (15/08) hạ MỌI THỨ xuống để tránh
vỡ tiếng mà KHÔNG nâng cả bản lên lại — báo cáo lượt đó tự ghi *"nhạc nền mất
−10,46 dB và bản trộn nhỏ tiếng hơn 3,8 dB"*.

**HAI THƯỚC ĐỘC LẬP, CỐ Ý** (`loudnorm` pha đo + `ebur128`): bài học `astats`
cổng 53 — một phép đo hỏng âm thầm thì phát chứng nhận cho thứ vẫn sai. Hai
thước lệch nhau quá 0,5 LU là DỪNG, đừng tin số nào.

Mọi `subprocess` có `timeout=` (bẫy `-t` sai chỗ ghi vô hạn 115 MB/giây đã làm
đầy ổ C 420 GB).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
FF = REPO / "bin" / "ffmpeg.exe"
HAN = 900  # giây — video 107 s, dư sức; nhưng KHÔNG BAO GIỜ để trống


def _chay(args: list[str], han: int = HAN) -> tuple[int, str]:
    r = subprocess.run([str(FF), "-nostdin", "-hide_banner", *args],
                       capture_output=True, timeout=han,
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


def do_loudnorm(path: Path) -> dict:
    """Pha ĐO của `loudnorm` (print_format=json -> stderr, không phải stdout)."""
    rc, err = _chay(["-i", str(path), "-af",
                     "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                     "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError(f"loudnorm chết trên {path.name}: {err[-400:]}")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        raise RuntimeError(f"loudnorm KHÔNG trả JSON cho {path.name}")
    d = json.loads(m.group(0))
    return {k: float(d[k]) for k in
            ("input_i", "input_tp", "input_lra", "input_thresh")}


def do_ebur128(path: Path) -> dict:
    """`ebur128` — thước THỨ HAI, độc lập với loudnorm."""
    rc, err = _chay(["-i", str(path), "-af", "ebur128=peak=true",
                     "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError(f"ebur128 chết trên {path.name}: {err[-400:]}")
    duoi = err[err.rfind("Summary:"):] if "Summary:" in err else err
    def _lay(nhan: str) -> float:
        m = re.search(nhan + r":\s*\n?\s*(-?\d+\.?\d*)", duoi)
        if not m:
            raise RuntimeError(f"ebur128 thiếu '{nhan}' cho {path.name}")
        return float(m.group(1))
    return {"I": _lay("I"), "LRA": _lay("LRA"), "TP": _lay("Peak")}


def do_ca_hai(nhan: str, path: Path) -> dict | None:
    if not path.exists():
        print(f"  [BỎ QUA] {nhan}: không có {path}")
        return None
    ln, eb = do_loudnorm(path), do_ebur128(path)
    lech = abs(ln["input_i"] - eb["I"])
    if lech > 0.5:
        raise RuntimeError(
            f"HAI THƯỚC LỆCH {lech:.2f} LU trên {nhan} "
            f"(loudnorm {ln['input_i']:.2f} · ebur128 {eb['I']:.2f}) — DỪNG")
    return {"nhan": nhan, "file": str(path), "I": ln["input_i"],
            "TP": ln["input_tp"], "LRA": ln["input_lra"],
            "thresh": ln["input_thresh"], "I_eb": eb["I"], "TP_eb": eb["TP"],
            "LRA_eb": eb["LRA"], "lech_thuoc": round(lech, 3)}


def main() -> int:
    dl = Path.home() / "Downloads" / "longtieng"
    ten = "近期热播的7部新片推荐。 #电影推荐 #新片速递.mp4"
    e2e = REPO / "_do_lt" / "e2e"

    muc = [
        ("GỐC (video anh Hùng gửi)", dl / ten),
        ("XUẤT — bản anh Hùng đã chạy", dl / "xuất" / ten),
        ("XUẤT — bản trộn v2.30.0 (e2e)", e2e / "tieng_moi.wav"),
        ("XUẤT — video e2e v2.30.0", e2e / "ban__thaygiong.mp4"),
        ("lớp GIỌNG thô (chưa nâng)", e2e / "tieng_moi.giong.wav"),
        ("lớp NHẠC gốc (Demucs)", e2e / "tach" / "lop_nhac.wav"),
    ]
    # bản TRƯỚC KHI CHỮA TRỘN: dựng lại đúng hai hằng số cũ (giọng +0 dB,
    # nhạc −2 dB, KHÔNG nén, KHÔNG né giọng) — cùng cách `_do_can_tieng.py`.
    cu = e2e / "_cantieng" / "tron_CŨ.wav"
    if cu.exists():
        muc.insert(4, ("TRỘN — cách CŨ (giọng 0 dB · nhạc −2 dB)", cu))
    moi = e2e / "_cantieng" / "tron_MỚI.wav"
    if moi.exists():
        muc.insert(5, ("TRỘN — cách MỚI (bản đã chữa 15/08)", moi))

    ra = []
    for nhan, p in muc:
        print(f"đang đo: {nhan} ...", flush=True)
        kq = do_ca_hai(nhan, p)
        if kq:
            ra.append(kq)

    print("\n" + "=" * 86)
    print("ĐỘ TO TÍCH HỢP (đích mạng xã hội: I ≈ −14 LUFS · đỉnh thật ≤ −1 dBTP)")
    print("=" * 86)
    print(f"{'':44} {'I (LUFS)':>10} {'TP(dBTP)':>10} {'LRA(LU)':>9}")
    for r in ra:
        co = "" if r["I"] >= -16.0 else "   <-- NHỎ"
        print(f"{r['nhan']:44} {r['I']:10.2f} {r['TP']:10.2f} "
              f"{r['LRA']:9.2f}{co}")
    print("-" * 86)
    print(f"{'ĐÍCH':44} {-14.0:10.2f} {-1.0:10.2f} {'':>9}")

    (REPO / "_kq_lufs.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi: {REPO / '_kq_lufs.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
