"""ĐO A/B BẢN VÁ "BÙ GIỌNG GỐC" — xuất THẬT rồi đo lại bằng đúng thước cũ
(18/08/2026).

Hai arm chạy trên CÙNG một video, CÙNG một lượt tách/chép lời/dịch/đọc, khác
nhau ĐÚNG một cờ `bu_giong_goc_bat`. Sau đó đo "mất tiếng người" bằng CHÍNH
hàm của `_do_mat_giong.py` (so LỚP GIỌNG với LỚP GIỌNG) để con số đứng cùng một
thước với bảng đã đo trên bản anh Hùng xuất.

**KHÔNG ĐỤNG VIDEO GỐC** — copy ra sandbox rồi làm trên bản sao.

**VÌ SAO PHẢI XUẤT THẬT, KHÔNG ĐO BẰNG HÀM THUẦN:** `khoang_khong_giong` là
hàm thuần và đã có ca đơn vị, nhưng câu hỏi của anh Hùng là *"còn bị tắt tiếng
nữa không"* — chỉ file xuất ra trả lời được. Bù mà lệch mốc, hay lọt vào chỗ
gốc cũng im, thì hàm thuần vẫn xanh mà tai vẫn nghe sai.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = REPO / "bq_do_bu_goc"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "mat_tieng"

#: Video ĐO ĐƯỢC mất nhiều nhất (50,4 s = 12,7%) trong 4 bản anh Hùng đã xuất.
TEN = "八位好莱坞导演联手拍的电影有多厉害#电影解说.mp4"

DICH = "vi"
GIONG = "vi-VN-NamMinhNeural"


def do_mat(goc_video: Path, xuat_video: Path, lam: Path) -> dict:
    """Dùng ĐÚNG thước của `_do_mat_giong.py`."""
    import _do_mat_giong as DM
    from app.core import thay_giong as TG
    wg, wx = lam / "m_goc.wav", lam / "m_xuat.wav"
    DM.rut_wav(goc_video, wg)
    DM.rut_wav(xuat_video, wx)
    tg = TG.tach_giong(wg, lam / "mtg", cach="demucs")
    tx = TG.tach_giong(wx, lam / "mtx", cach="demucs")
    bg = TG.duong_bao_muc(tg["giong"], buoc=DM.BUOC)
    bx = TG.duong_bao_muc(tx["giong"], buoc=DM.BUOC)
    kh, tk = DM.khoang_mat(bg, bx)
    tk["khoang"] = [[round(a, 2), round(b, 2)] for a, b in kh]
    return tk


# ============================================================================
# **SCRIPT NÀY ĐÃ LẠC HẬU TỪ v2.48.0 — ĐỌC TRƯỚC KHI CHẠY.**
# Tham số `bu_giong_goc_bat` đã bị GỠ HẲN khỏi `thay_giong_video` /
# `thay_giong_mot_video`: ở cách trộn "tách nhạc" app KHÔNG CÒN chèn lại tiếng
# gốc vào quãng nghỉ (xem `thay_giong.VI_SAO_BO_BU` + cổng 86 CA 9). Chạy
# nguyên xi là `TypeError: unexpected keyword argument`.
# Phép đo thay thế — GHÉP CẶP trong MỘT lượt chạy, và đo cả mức dB trong quãng
# nghỉ trên BẢN TRỘN CUỐI: **`_do_quang_nghi.py`**.
# Giữ file lại để tra số cũ, KHÔNG xoá; chặn ở đây để không ai mất một lượt
# chạy dài rồi mới thấy nó nổ giữa chừng.
# ============================================================================
if __name__ == "__main__":
    print("*** SCRIPT LẠC HẬU: `bu_giong_goc_bat` đã bị gỡ ở v2.48.0. ***")
    print("    Dùng `_do_quang_nghi.py` (ghép cặp + đo dB quãng nghỉ).")
    sys.exit(2)


def main() -> int:
    from app.core import thay_giong as TG

    src = NGUON / TEN
    if not src.exists():
        print(f"KHÔNG CÓ video: {src}")
        return 2
    SB.mkdir(exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    ket: dict = {"video": TEN}
    try:
        vin = SB / "nguon.mp4"
        shutil.copy2(src, vin)           # làm trên BẢN SAO
        print(f"video: {TEN}  ({TG.probe_duration(vin):.2f}s)")
        print(f"Demucs: {TG.tinh_trang_demucs()}")

        for nhan, bat in (("TAT", False), ("BAT", True)):
            print(f"\n{'='*72}\nARM {nhan} — bu_giong_goc_bat={bat}")
            lam = SB / f"arm_{nhan}"
            lam.mkdir(exist_ok=True)
            t0 = time.time()
            r = TG.thay_giong_video(
                vin, dich_sang=DICH, thu_muc_lam=lam, voice=GIONG,
                cach_tach="demucs", viet_chu=False,
                bu_giong_goc_bat=bat,
                on_progress=lambda p, m: print(f"    {p*100:5.1f}% {m}"))
            gy = time.time() - t0
            if not r.get("ok"):
                print(f"  LỖI: {r.get('loi')}")
                ket[nhan] = {"ok": False, "loi": str(r.get("loi"))[:300]}
                continue
            ra = Path(r["ra"])
            giu = NGHE / f"{nhan}_{ra.name}"
            shutil.copy2(ra, giu)
            print(f"  xuất xong {gy:.0f}s -> {giu.name} "
                  f"({giu.stat().st_size/1024/1024:.0f} MB)")
            print(f"  khớp: {r.get('khop', {}).get('bo_qua')} câu bỏ qua · "
                  f"bù gốc: {r.get('bu_goc')}")
            print("  đo lại mất tiếng...")
            m = do_mat(vin, ra, lam)
            print(f"  >>> MẤT {m['giay_mat']}s / {m['so_khoang']} khoảng")
            ket[nhan] = {"ok": True, "giay": round(gy, 1),
                         "file_nghe": str(giu),
                         "khop_bo_qua": r.get("khop", {}).get("bo_qua"),
                         "bu_goc": r.get("bu_goc"), "do": m}
            (REPO / "_kq_bu_goc_ab.json").write_text(
                json.dumps(ket, ensure_ascii=False, indent=1),
                encoding="utf-8")
    finally:
        shutil.rmtree(SB, ignore_errors=True)

    print(f"\n{'='*72}\nA/B — MẤT TIẾNG NGƯỜI")
    for nhan in ("TAT", "BAT"):
        k = ket.get(nhan) or {}
        if not k.get("ok"):
            print(f"  {nhan:<5} LỖI {k.get('loi', 'chưa chạy')}")
            continue
        d = k["do"]
        print(f"  {nhan:<5} MẤT {d['giay_mat']:>6.1f}s / "
              f"{d['so_khoang']:>3} khoảng · bù "
              f"{(k.get('bu_goc') or {}).get('so_bu', 0)} mảnh / "
              f"{(k.get('bu_goc') or {}).get('giay_bu', 0)}s · {k['giay']}s")
    a = (ket.get("TAT") or {}).get("do") or {}
    b = (ket.get("BAT") or {}).get("do") or {}
    if a and b:
        print(f"\n  => {a['giay_mat']}s -> {b['giay_mat']}s "
              f"(giảm {a['giay_mat'] - b['giay_mat']:.1f}s)")
    print(f"File nghe thử: {NGHE}")
    print("=> _kq_bu_goc_ab.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
