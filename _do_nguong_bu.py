"""HIỆU CHUẨN NGƯỠNG "GỐC CÓ TIẾNG" CỦA `bu_giong_goc` TRÊN LỚP GIỌNG THẬT
(18/08/2026).

**VÌ SAO PHẢI ĐO LẠI:** bản đầu đặt `nguong = sàn(p20) + 10 dB`, hiệu chuẩn
trên NGUỒN THỬ TỰ DỰNG (sàn thấp hơn tiếng 22 dB). Trên lớp giọng Demucs THẬT
thì phép A/B end-to-end đo ra `so_bu = 0 · bo_qua = 44` — tức **bản vá KHÔNG
CHẠY MỘT LẦN NÀO**, `sàn -20,04 -> ngưỡng -10,04 dBFS` nằm CAO HƠN cả tiếng
nói. Cổng 78 vẫn xanh vì nguồn thử của nó không giống thực tế.

Đây đúng là bài học đã ghi nhiều lần trong repo: **hằng số hiệu chuẩn trên
nguồn tự dựng thì phải đo lại trên dữ liệu thật trước khi tin.**

Script này in PHÂN BỐ mức của lớp giọng thật ở CẢ HAI bước đo (0,05 s và
0,20 s) rồi thử vài công thức ngưỡng, cho biết mỗi công thức nhận ra bao nhiêu
giây "đang nói" so với con số tham chiếu của `_do_mat_giong.py`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
TEN = "八位好莱坞导演联手拍的电影有多厉害#电影解说.mp4"
SB = REPO / "bq_do_nguong_bu"
GIAY = 150.0            # lấy 150 s đầu là đủ để có phân bố, đỡ 6 phút Demucs


def _bpv(x, q):
    s = sorted(x)
    return s[max(0, min(len(s) - 1, int(len(s) * q)))]


def main() -> int:
    from app.core import thay_giong as TG
    import _do_mat_giong as DM

    src = NGUON / TEN
    if not src.exists():
        print(f"KHÔNG CÓ: {src}")
        return 2
    shutil.rmtree(SB, ignore_errors=True)
    SB.mkdir(parents=True)
    try:
        w = SB / "goc.wav"
        DM._ff(["-t", f"{GIAY}", "-i", str(src), "-vn", "-ac", "2",
                "-ar", "44100", "-c:a", "pcm_s16le", str(w)], "rút audio")
        print(f"đã rút {TG.probe_duration(w):.1f}s · tách Demucs...")
        t = TG.tach_giong(w, SB / "tach", cach="demucs")
        gi = t["giong"]

        for buoc, nhan in ((0.05, "0,05 s (thước _do_mat_giong)"),
                           (0.20, "0,20 s (BUOC_DO_MUC — bu_giong_goc dùng)")):
            bao = TG.duong_bao_muc(gi, buoc=buoc)
            n = len(bao)
            huu = [v for v in bao if v > -119.0]
            print(f"\n=== bước {nhan} · {n} ô ===")
            print(f"  số ô im tuyệt đối (-120) : {n - len(huu)}")
            print("  p05 %6.2f · p20 %6.2f · p50 %6.2f · p80 %6.2f · "
                  "p90 %6.2f · p99 %6.2f · max %6.2f"
                  % (_bpv(bao, .05), _bpv(bao, .20), _bpv(bao, .50),
                     _bpv(bao, .80), _bpv(bao, .90), _bpv(bao, .99),
                     max(bao)))
            san_all = _bpv(bao, .20)
            san_huu = _bpv(huu, .20) if huu else -120.0
            dinh = _bpv(bao, .90)
            print(f"  sàn(mọi ô) {san_all:6.2f} · sàn(hữu hạn) {san_huu:6.2f}"
                  f" · đỉnh(p90) {dinh:6.2f}")
            print("  --- thử ngưỡng: bao nhiêu GIÂY được coi là ĐANG NÓI ---")
            for ten, ng in (
                ("sàn(mọi)+10  [bản đang dùng]", san_all + 10),
                ("sàn(mọi)+6", san_all + 6),
                ("sàn(mọi)+3", san_all + 3),
                ("sàn(hữu hạn)+12 [_do_mat_giong]", san_huu + 12),
                ("đỉnh(p90)-10", dinh - 10),
                ("đỉnh(p90)-15", dinh - 15),
                ("đỉnh(p90)-20", dinh - 20),
                ("min(sàn+10, đỉnh-15)", min(san_all + 10, dinh - 15)),
            ):
                gy = sum(buoc for v in bao if v > ng)
                print(f"    {ten:<34} ngưỡng {ng:7.2f} dBFS -> "
                      f"{gy:7.2f}s ({100*gy/max(1e-9, n*buoc):5.1f}%)")
    finally:
        shutil.rmtree(SB, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
