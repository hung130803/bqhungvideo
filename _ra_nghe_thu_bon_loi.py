"""SINH FILE NGHE THỬ CHO 4 LỜI KÊU — CẶP TRƯỚC/SAU CÙNG MỘT ĐOẠN.

Tai anh Hùng là phán quyết cuối; mọi số trong báo cáo chỉ để CHỈ CHỖ MÀ NGHE.

Ba file, đều cắt/dựng từ CÙNG một lượt chạy `_do_bu_goc_that.py` trên **video
gốc của chính anh Hùng**, cấu hình đọc từ QSettings (`vnb:` nhân bản · tách
nhạc · mục 2 "Chỉnh video theo giọng" · che chữ · nhấn nhá):

  · `A_BUGOC_BAT_...`  — ĐÚNG thứ anh Hùng vừa nghe (bù giọng gốc BẬT, mặc định)
  · `B_BUGOC_TAT_...`  — cùng đoạn, cùng lượt, CHỈ khác `bu_giong_goc_bat=False`
  · `C_CHI_MANH_BU_...`— **chỉ riêng vật liệu bù**, 31 mảnh nối lại. Đây là thứ
    app chèn vào các quãng nghỉ; nghe file này là biết ngay nó là tiếng gì.

**CẢ HAI FILE A/B CHUẨN VỀ CÙNG −14 LUFS bằng chính `chuan_do_to`** — không
chuẩn thì phép nghe biến thành "file nào TO hơn". Rồi **ĐO LẠI bằng `loudnorm`
chạy RIÊNG**: bài học lượt trước là cột LUFS do chính hàm in ra bị đọc sai khoá
nên hiện 0,00; số nào tự khai thì phải có người thứ hai kiểm.

    .venv\\Scripts\\python _ra_nghe_thu_bon_loi.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "bon_loi"
SB = Path(r"D:\claude\_hop_cat_4loi\nghe")
FF = REPO / "bin" / "ffmpeg.exe"

#: Cửa sổ nghe: 10-45 s của bản xuất. Chọn theo `bu_goc.khoang` của arm BẬT —
#: trong 35 giây này có **6 mảnh bù**, gồm mảnh DÀI NHẤT cả video (3,40 s ở
#: 11,03-14,43). Đây là chỗ đáng nghe nhất, không phải chỗ đẹp nhất.
A, B = 10.0, 45.0


def lufs(p: Path) -> float:
    """ĐO ĐỘC LẬP bằng `loudnorm` — không tin số do bước chuẩn hoá tự khai."""
    r = subprocess.run(
        [str(FF), "-hide_banner", "-nostats", "-i", str(p), "-af",
         "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r'"input_i"\s*:\s*"(-?[\d.]+)"', r.stderr or "")
    return float(m[-1]) if m else float("nan")


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def main() -> int:
    from app.core import thay_giong as TG
    NGHE.mkdir(parents=True, exist_ok=True)
    SB.mkdir(parents=True, exist_ok=True)

    ket: dict = {"cua_so_giay": [A, B], "file": []}
    for nhan, arm in (("A_BAT", "BAT"), ("B_TAT", "TAT")):
        kq = REPO / f"_kq_bu_goc_that_{arm}.json"
        if not kq.exists():
            print(f"  bỏ qua {arm}: chưa có {kq.name}")
            continue
        d = json.loads(kq.read_text(encoding="utf-8"))
        src = Path(d["nghe_thu"])
        bu = d.get("bu_goc") or {}
        gb = bu.get("giay_bu", 0.0)
        # -ss/-t đặt TRƯỚC -i = tuỳ chọn ĐẦU VÀO (bài học `-t` đặt sai làm
        # anullsrc ghi vô hạn, đã đầy ổ C 420 GB).
        cat = SB / f"{nhan}.wav"
        TG._ffmpeg(["-ss", f"{A}", "-t", f"{B-A}", "-i", str(src),        # noqa: SLF001
                    "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
                    str(cat)], f"cắt {A}-{B}s arm {arm}", timeout=600)
        chuan = SB / f"{nhan}_14.wav"
        TG.chuan_do_to(cat, chuan)          # CÙNG một cửa chuẩn hoá của app
        ten = (f"{nhan}_bu{gb:g}s_{int(B-A)}giay.wav" if gb
               else f"{nhan}_KHONG_BU_{int(B-A)}giay.wav")
        ra = NGHE / ten
        ra.write_bytes(chuan.read_bytes())
        i = lufs(ra)
        ket["file"].append({"ten": ten, "arm": arm, "giay_bu": gb,
                            "LUFS_do_lai": round(i, 2), "md5": md5(ra)})
        print(f"  {ten}\n      LUFS đo lại {i:.2f} · md5 {md5(ra)}")

    # file C — vật liệu bù, đã có sẵn từ lượt BẬT
    c = NGHE / "CHI_MANH_BU_31manh.wav"
    if c.exists():
        cc = SB / "C14.wav"
        TG.chuan_do_to(c, cc)
        ra = NGHE / "C_CHI_MANH_BU_31manh_25.57s.wav"
        ra.write_bytes(cc.read_bytes())
        c.unlink()
        i = lufs(ra)
        ket["file"].append({"ten": ra.name, "arm": "chỉ mảnh bù",
                            "LUFS_do_lai": round(i, 2), "md5": md5(ra)})
        print(f"  {ra.name}\n      LUFS đo lại {i:.2f} · md5 {md5(ra)}")

    ms = [f["md5"] for f in ket["file"]]
    ket["MD5_KHAC_NHAU"] = len(set(ms)) == len(ms)
    ket["LUFS_deu_ve_-14"] = all(abs(f["LUFS_do_lai"] + 14.0) <= 0.6
                                 for f in ket["file"])
    print(f"\n  MD5 khác nhau: {'CÓ' if ket['MD5_KHAC_NHAU'] else 'KHÔNG'} "
          f"({len(set(ms))}/{len(ms)})")
    print(f"  LUFS đều về -14 (±0,6): "
          f"{'CÓ' if ket['LUFS_deu_ve_-14'] else 'KHÔNG'}")
    (REPO / "_kq_nghe_thu_bon_loi.json").write_text(
        json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n=> {NGHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
