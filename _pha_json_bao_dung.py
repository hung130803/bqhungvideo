# -*- coding: utf-8 -*-
"""THỬ PHÁ cổng 74 — gỡ từng chốt ra thì cổng PHẢI ĐỎ.

Cổng nào cũng xanh dù bản vá bị gỡ thì nó chỉ là CON DẤU. File này gỡ đúng
từng chốt một, chạy lại cổng 74, rồi TRẢ NGUYÊN mã (khôi phục từ BYTE gốc,
không nhờ git — đang có luồng khác làm việc trong repo).

BA CỘT, KHÔNG ĐƯỢC GỘP (bài học cổng 54): BẮT · LỌT · KHÔNG PHÁ ĐƯỢC.
"KHÔNG PHÁ ĐƯỢC" = lỗi của PHÉP THỬ (chuỗi tìm không khớp, thường vì file
CRLF), tuyệt đối đừng đếm nó vào cột BẮT — bản đầu của phép phá cổng 54 từng
báo ngược sự thật đúng vì chuyện đó.

Chạy: .venv\\Scripts\\python.exe -u _pha_json_bao_dung.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
LLM = REPO / "app" / "ai" / "llm.py"
CD = REPO / "app" / "ai" / "chon_doan.py"
ML = REPO / "app" / "ai" / "mach_lac.py"

#: (nhãn, file, chuỗi TÌM, chuỗi THAY) — mỗi phép gỡ ĐÚNG MỘT chốt
PHEP = [
    ("gỡ max_tokens khỏi _call_once", LLM,
     'them: dict = {"max_tokens": mt}', 'them: dict = {}'),
    ("gỡ reasoning_effort=low", LLM,
     'them["reasoning_effort"] = "low"', 'pass'),
    ("gỡ response_format json_object", LLM,
     'them["response_format"] = {"type": "json_object"}', 'pass'),
    ("gỡ hẳn phép VỚT JSON đứt", LLM,
     "        vot = vot_json_cut(text)\n        if vot is not None:\n"
     "            return vot\n    return json.loads(text)",
     "        pass\n    return json.loads(text)"),
    ("gỡ bước vớt CẤU TRÚC NGOÀI CÙNG (để ứng viên cướp mảnh lồng)", LLM,
     "        if text.rfind(dong) < som:", "        if False:"),
    ("gỡ nhận diện finish_reason=length (báo sai bệnh)", LLM,
     'cat = (ly_do_ket_thuc() == "length")', "cat = False"),
    ("bỏ ghi finish_reason sau khi gọi", LLM,
     "            _ghi_ket_thuc(resp)\n            out =",
     "            out ="),
    ("chon_doan KHÔNG nối vào bộ bao dung", CD,
     "            from app.ai.llm import boc_json as _bj\n"
     "            d = _bj(raw)", "            d = None"),
    ("mach_lac KHÔNG nối vào bộ bao dung", ML,
     "            from app.ai.llm import boc_json as _bj\n"
     "            d = _bj(raw)", "            d = None"),
]


def chay_cong() -> tuple[int, str]:
    r = subprocess.run([PY, "-u", str(REPO / "_test_json_bao_dung.py")],
                       cwd=str(REPO), capture_output=True, timeout=900,
                       env={**__import__("os").environ,
                            "PYTHONIOENCODING": "utf-8", "BQ_BO_MANG": "1"})
    out = (r.stdout or b"").decode("utf-8", "replace") \
        + (r.stderr or b"").decode("utf-8", "replace")
    dong = [l for l in out.splitlines() if l.startswith("KẾT QUẢ CỔNG")]
    return r.returncode, (dong[-1] if dong else "(không có dòng tổng kết)")


def main() -> int:
    goc = {p: p.read_bytes() for p in (LLM, CD, ML)}
    bat = lot = kho = 0
    try:
        rc, tk = chay_cong()
        print(f"[nền] chưa phá -> mã thoát {rc} · {tk}")
        if rc != 0:
            print("  DỪNG: cổng đang ĐỎ sẵn, phá nữa thì đọc không ra gì")
            return 2
        for nhan, f, tim, thay in PHEP:
            t = f.read_text(encoding="utf-8")
            # file repo là CRLF: chuỗi nhiều dòng viết '\n' sẽ KHÔNG khớp nếu
            # đọc thô. `read_text` đã quy về '\n' nên khớp được; vẫn kiểm.
            if tim not in t:
                kho += 1
                print(f"[KHÔNG PHÁ ĐƯỢC] {nhan} — không tìm thấy chỗ phá")
                continue
            f.write_text(t.replace(tim, thay, 1), encoding="utf-8",
                         newline="\n")
            try:
                rc, tk = chay_cong()
            finally:
                for p, b in goc.items():
                    p.write_bytes(b)
            if rc != 0:
                bat += 1
                print(f"[BẮT   ] {nhan} -> mã thoát {rc} · {tk}")
            else:
                lot += 1
                print(f"[LỌT!!!] {nhan} -> mã thoát 0 · {tk}")
    finally:
        for p, b in goc.items():
            p.write_bytes(b)
    print()
    print(f"THỬ PHÁ: BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {kho}")
    return 1 if (lot or kho) else 0


if __name__ == "__main__":
    sys.exit(main())
