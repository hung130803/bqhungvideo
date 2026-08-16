# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 66 — cổng phải ĐỎ khi gỡ từng chốt ra.

*"Cổng nào không thử phá thì chỉ là con dấu"*. Lượt phá của cổng 65 từng ra
**LỌT 1 + KHÔNG PHÁ ĐƯỢC 2**, tức bản thân cổng có lỗ. Ở đây mỗi phép phá là
một cách "sửa cho gọn" mà người sau có thể làm thật.

**BA TRẠNG THÁI, ĐỪNG GỘP** (bài học `_pha_dubbing_cjk.py`): BẮT (cổng đỏ =
tốt) · **LỌT** (cổng vẫn xanh = cổng có lỗ) · **KHÔNG PHÁ ĐƯỢC** (không tìm
thấy chỗ thay chữ = LỖI CỦA PHÉP THỬ, tuyệt đối không được đếm vào cột LỌT —
bản đầu của phép thử cổng 54 làm thế và **báo cáo ngược sự thật**).

File repo là **CRLF**; đọc bằng `read_text()` (Python quy về `\\n`) rồi ghi lại
bằng `newline="\\r\\n"`, khôi phục bằng chính BYTE gốc.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
FU = REPO / "app" / "core" / "ffmpeg_utils.py"
M1 = REPO / "app" / "modules" / "m1_highlight.py"

#: (tên, file, chuỗi TÌM, chuỗi THAY, ca dự kiến bắt)
PHEP = [
    ("bỏ QUÁ MẪU quanh alimiter (dọn cho gọn)", FU,
     'f"aresample={QUA_MAU_HAN_DINH},"\n            + _han_dinh(tran_lim_db, nha=10)\n            + ",aresample=48000")',
     '+ _han_dinh(tran_lim_db, nha=10))',
     "CA 1 (chuỗi) — và trên bản ffmpeg cũ còn phá cả trần đỉnh"),

    ("dùng `loudnorm` để ÁP thay cho nâng thuần", FU,
     '"-af", _chuoi_do_to(nang_db, tran_lim_db),',
     '"-af", f"loudnorm=I={DICH_LUFS_CLIP}:TP={tran_lim_db}:LRA=11",',
     "CA 3 — hệ số không còn là HẰNG SỐ"),

    ("bỏ `level=0` của alimiter (mặc định TỰ NÂNG +3,1 dB)", FU,
     'f"alimiter=limit={min(1.0, max(0.0625, _lin(tran_db))):.4f}"\n            f":level=0:latency=1:attack=1:release={int(nha)}")',
     'f"alimiter=limit={min(1.0, max(0.0625, _lin(tran_db))):.4f}"\n            f":latency=1:attack=1:release={int(nha)}")',
     "CA 1"),

    ("bỏ SÀN chống nâng điên (nâng cả clip gần câm)", FU,
     'if truoc["I"] < SAN_LUFS_CLIP:',
     'if False:',
     "CA 7 — clip gần câm bị nâng +56 dB nền nhiễu"),

    ("bỏ chốt 'clip đã đúng thì đừng đụng'", FU,
     'if abs(can) <= NGUONG_BO_QUA_LU and truoc["TP"] <= tran_tp:',
     'if False:',
     "CA 6 — file bị mã hoá lại thêm một đời AAC"),

    ("bỏ BẬC THANG, ép luôn đủ đích", FU,
     '            if (qua or tut > LRA_TUT_TOI_DA + 1e-6) and buoc < len(bac):',
     '            if False:',
     "CA 4 (đỉnh vượt trần) hoặc CA 5 (LRA tụt)"),

    ("`do_do_to_clip` trả số mặc định thay vì NÉM", FU,
     '        raise RuntimeError(f"ebur128 KHÔNG in Summary cho {p.name} "\n                           f"(file không có tiếng?): {err[-400:]}")',
     '        return {"I": -14.0, "LRA": 0.0, "TP": -1.0}',
     "CA 2 — phép đo hỏng phát chứng nhận"),

    ("gỡ hẳn lời gọi chuẩn hoá khỏi đường xuất", M1,
     '        _dt_log = _chuan_dt(out_path)',
     '        _dt_log = None',
     "CA 10 — đường xuất không còn chuẩn hoá"),

    # PHẢI RA PYTHON HỢP LỆ. Bản đầu thụt lề lệch -> cổng đỏ vì
    # IndentationError chứ KHÔNG phải vì bắt được — cổng ĐỎ OAN thì phép phá
    # không chứng minh được gì (họ bẫy "chết trước khi tới chốt").
    ("đẩy lời gọi VÀO nhánh canvas (Mixed-Cut/clip đơn mất phần)", M1,
     '        _dt_log = _chuan_dt(out_path)',
     '        if (result_extra or {}).get("canvas"):\n            _dt_log = _chuan_dt(out_path)',
     "CA 10 — CỬA DUY NHẤT bị phá"),

    ("nuốt luôn CanceledError (huỷ không còn là huỷ)", FU,
     '        if _lop_huy() and isinstance(e, _lop_huy()):\n            raise               # HUỶ LÀ HUỶ, không nuốt',
     '        if False:\n            raise',
     "CA 12"),
]


def _chay_cong() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-u", str(REPO / "_test_do_to_xuat.py")],
                       capture_output=True, timeout=3000, cwd=str(REPO),
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace")


def main() -> int:
    goc = {p: p.read_bytes() for p in (FU, M1)}
    bat = lot = khong_pha = 0
    print("=" * 78)
    print("THỬ PHÁ CỔNG 66 — mỗi phép gỡ MỘT chốt, cổng phải ĐỎ")
    print("=" * 78)
    try:
        for i, (ten, f, tim, thay, ca) in enumerate(PHEP, 1):
            for p, b in goc.items():
                p.write_bytes(b)
            s = f.read_text(encoding="utf-8")
            if tim not in s:
                khong_pha += 1
                print(f"\n[{i}] {ten}\n     ⚠ KHÔNG PHÁ ĐƯỢC — không tìm thấy "
                      f"chỗ thay chữ (LỖI CỦA PHÉP THỬ, không phải của cổng)")
                continue
            f.write_text(s.replace(tim, thay, 1), encoding="utf-8",
                         newline="\r\n")
            rc, out = _chay_cong()
            n_hong = 0
            for d in out.splitlines():
                if d.strip().startswith("ĐẠT ") and " · HỎNG " in d:
                    try:
                        n_hong = int(d.split("HỎNG")[1].strip())
                    except ValueError:
                        pass
            if rc != 0:
                bat += 1
                print(f"\n[{i}] {ten}\n     BẮT — cổng đỏ (mã thoát {rc}, "
                      f"HỎNG {n_hong}) · dự kiến: {ca}")
                for d in out.splitlines():
                    if d.strip().startswith("HỎNG"):
                        print(f"        {d.strip()[:110]}")
            else:
                lot += 1
                print(f"\n[{i}] {ten}\n     ❌ LỌT — cổng VẪN XANH. Cổng có lỗ "
                      f"ở chỗ này (dự kiến bắt: {ca})")
    finally:
        for p, b in goc.items():
            p.write_bytes(b)
        print("\n(đã khôi phục nguyên trạng 2 file)")

    print("\n" + "=" * 78)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong_pha}")
    print("=" * 78)
    return 1 if (lot or khong_pha) else 0


if __name__ == "__main__":
    raise SystemExit(main())
