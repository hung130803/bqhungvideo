# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 89 — mỗi phép gỡ ĐÚNG MỘT chốt, cổng phải ĐỎ.

**CỔNG KHÔNG PHẢI CON DẤU.** Cổng 89 ra `ĐẠT 73 · HỎNG 0` chẳng chứng minh gì
nếu gỡ chốt ra mà nó vẫn xanh. File này gỡ từng chốt, chạy lại cổng, rồi PHỤC
HỒI nguyên trạng.

**BA LUẬT ĐÃ HỌC BẰNG MÁU, ĐỪNG VI PHẠM:**
 1. **"KHÔNG TÌM THẤY CHỖ PHÁ" ≠ "LỌT".** Bản đầu của `_pha_dubbing_cjk.py`
    đếm chúng vào cùng một cột nên **báo cáo NGƯỢC SỰ THẬT**: 4/6 phép im lặng
    không phá được gì mà bảng ghi là "cổng để lọt". Ở đây tách hẳn ba cột
    **BẮT · LỌT · KHÔNG PHÁ ĐƯỢC**.
 2. **NEO PHẢI DUY NHẤT** — kiểm `count()` TRƯỚC khi thay. Neo khớp 2 chỗ là
    phá cả hai, cổng đỏ vì lý do KHÁC cái đang thử.
 3. **PHÁ THÌ GỠ SẠCH CHỐT, đừng đổi giá trị bên trong nó.** Bài học cổng 80
    LỌT 7: phép phá đổi `goc` thành đường dẫn không bao giờ khớp, làm hàm
    CHẶT HƠN chứ không hở ra — cổng xanh là ĐÚNG, nhưng bảng đọc thành "cổng
    không bắt được".

Repo là **CRLF** nên file đọc/ghi bằng `newline=""` để không đổi cả dòng kết
thúc của file người khác đang sửa (neo vì thế chỉ dùng MỘT dòng).

    .venv\\Scripts\\python -u _pha_khop_video.py [số phép]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
TG = REPO / "app" / "core" / "thay_giong.py"
TC = REPO / "app" / "core" / "tg_chay.py"

#: Chạy ĐÚNG các mục liên quan thay vì cả cổng: cả cổng ~3 phút × 9 phép là 27
#: phút, mà mục 1/2/3/5 (độ to + hộp thoại) không dính bản vá này.
_RUNNER = r"""
import sys, os
sys.path.insert(0, r"{repo}")
import _test_am_va_hinh as G
G.don()
try:
    for t in "{muc}".split(","):
        getattr(G, "muc" + t)()
finally:
    print("KETQUA ĐẠT %d HỎNG %d" % (G.DAT, G.HONG))
    G.don()
sys.exit(0 if G.HONG == 0 else 1)
"""

#: (tên, file, neo, thay bằng, mục cần chạy, chốt đang gỡ là gì)
PHEP = [
    ("1. trả `-itsscale` về nhánh CHE CHỮ (đúng bản cũ)", TG,
     '    _ffmpeg(["-i", str(video_goc), "-i", str(audio_moi),',
     '    _ffmpeg([*its, "-i", str(video_goc), "-i", str(audio_moi),',
     "6", "hộp che phải đọc mốc NGUỒN"),

    ("2. GỠ HẲN `setpts` khỏi chuỗi filter", TG,
     '        chuoi.append(f"setpts=PTS*{k:.6f}")',
     '        pass  # PHA: gỡ setpts',
     "6", "phép giãn phải nằm trong chuỗi filter"),

    ("3. ĐẢO THỨ TỰ: `setpts` TRƯỚC khối che", TG,
     "    chuoi = [loc]",
     '    chuoi = ([f"setpts=PTS*{k:.6f}"] if k > 1.0 + 1e-6 else []) + [loc]',
     "6", "thứ tự che -> setpts -> phụ đề"),

    ("4. GỠ TRẦN theo fps (trả thẳng trần cứng)", TG,
     "    return max(1.0, min(TRAN_CHINH_HINH, fps / SAN_NHIP_HINH_FPS))",
     "    return 99.0  # PHA: gỡ trần",
     "4,8", "trần làm chậm hình theo nhịp hình còn lại"),

    ("5. `khop_thoi_gian` KHÔNG nhân hệ số vào mốc câu", TG,
     '        a = float(c["start"]) * k',
     '        a = float(c["start"])  # PHA',
     "4,8", "mốc câu phải giãn theo k để tempo về 1,0"),

    ("6. GỠ khoá `cham_tran` khỏi nhật ký (lùi IM LẶNG)", TG,
     '                "cham_tran": float(_c["k_can"]) > _tran + 1e-6,',
     '                "da_kep": float(_c["k_can"]) > _tran + 1e-6,',
     "8", "lùi về cách cũ thì phải GHI LOG"),

    # NEO PHẢI HAI DÒNG: `if hinh_theo_giong:` khớp **2 chỗ** (một ở
    # `khoa_chong_trung`, một ở `xep_mot`) -> neo một dòng là phá cả hai và
    # cổng đỏ vì lý do KHÁC cái đang thử. Đã kiểm `count()` trước, đúng luật 2.
    ("7. nối `htg` VÔ ĐIỀU KIỆN (đổi hash MỌI job cũ)", TC,
     '    if hinh_theo_giong:\n        sig += ":htg=1"',
     '    if True:  # PHA\n        sig += ":htg=1"',
     "7", "cờ chỉ vào hash KHI THẬT SỰ BẬT"),

    ("8. nối `htg` vào GIỮA chuỗi sig thay vì ĐUÔI", TC,
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:{r}"',
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:'
     '{\'htg=1:\' if hinh_theo_giong else \'\'}{r}"',
     "7", "đuôi nối vào CUỐI, khoá cũ là TIỀN TỐ"),

    ("9. payload ghi khoá `hinh_theo_giong` VÔ ĐIỀU KIỆN", TC,
     '    if hinh_theo_giong:\n        tt["hinh_theo_giong"] = True',
     '    if True:\n        tt["hinh_theo_giong"] = bool(hinh_theo_giong)',
     "7", "ô để mặc định thì KHÔNG sinh khoá trong payload"),
]

BAT: list[str] = []
LOT: list[str] = []
KHONG_PHA: list[str] = []


def _doc(p: Path) -> str:
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _ghi(p: Path, s: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def chay_cong(muc: str) -> tuple[int, str]:
    ma = _RUNNER.format(repo=str(REPO), muc=muc)
    t0 = time.time()
    r = subprocess.run([PY, "-u", "-c", ma], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8",
                            "PYTHONUTF8": "1", "BQ_FFMPEG_SLOTS": "1"},
                       timeout=1800)
    ra = (r.stdout or "") + (r.stderr or "")
    tk = [x for x in ra.splitlines() if x.startswith("KETQUA")]
    hong = [x for x in ra.splitlines() if x.strip().startswith("HỎNG")]
    return r.returncode, (f"{time.time() - t0:.0f}s · "
                          f"{tk[-1] if tk else 'KHÔNG có dòng tổng kết'}"
                          + (f" · đỏ: {hong[0].strip()[:78]}" if hong else ""))


def mot_phep(ten: str, f: Path, neo: str, thay: str, muc: str,
             chot: str) -> None:
    print(f"\n{'=' * 74}\n[PHÁ] {ten}\n  chốt đang gỡ: {chot}")
    goc = _doc(f)
    # neo trong file là CRLF nên neo nhiều dòng phải đổi `\n` -> `\r\n`
    neo_f = neo.replace("\n", "\r\n") if "\r\n" in goc else neo
    thay_f = thay.replace("\n", "\r\n") if "\r\n" in goc else thay
    n = goc.count(neo_f)
    if n != 1:
        KHONG_PHA.append(f"{ten} (neo khớp {n} chỗ, cần ĐÚNG 1)")
        print(f"  KHÔNG PHÁ ĐƯỢC — neo khớp {n} chỗ trong {f.name}, cần ĐÚNG 1."
              f"\n  (đây là LỖI CỦA PHÉP THỬ, KHÔNG phải cổng để lọt)")
        return
    try:
        _ghi(f, goc.replace(neo_f, thay_f, 1))
        rc, tt = chay_cong(muc)
        if rc != 0:
            BAT.append(ten)
            print(f"  BẮT ĐƯỢC (cổng ĐỎ, mã {rc}) — {tt}")
        else:
            LOT.append(ten)
            print(f"  *** LỌT *** cổng vẫn XANH — {tt}")
    finally:
        _ghi(f, goc)
        print(f"  đã phục hồi {f.name}")


def main() -> int:
    so = int(sys.argv[1]) if len(sys.argv) > 1 else len(PHEP)
    print(f"THỬ PHÁ CỔNG 89 — {min(so, len(PHEP))} phép\n"
          f"Mốc trước khi phá: chạy cổng đầy đủ phải ra ĐẠT 73 · HỎNG 0")
    rc0, tt0 = chay_cong("1,2,3,4,5,6,7,8")
    print(f"  ĐỐI CHỨNG (chưa phá): mã {rc0} — {tt0}")
    if rc0 != 0:
        print("  !!! CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ — dừng, không đọc được bảng nào")
        return 2
    for p in PHEP[:so]:
        mot_phep(*p)
    print(f"\n{'=' * 74}\nTỔNG: BẮT {len(BAT)} · LỌT {len(LOT)} · "
          f"KHÔNG PHÁ ĐƯỢC {len(KHONG_PHA)}")
    for x in LOT:
        print(f"  LỌT: {x}")
    for x in KHONG_PHA:
        print(f"  KHÔNG PHÁ ĐƯỢC: {x}")
    return 0 if not LOT else 1


if __name__ == "__main__":
    sys.exit(main())
