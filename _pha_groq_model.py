# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 69 — gỡ từng chốt ra, cổng PHẢI ĐỎ.

Cổng nào không tự chứng minh được là nó BẮT ĐƯỢC lỗi thì chỉ là con dấu (bài
học cổng 41/47/56d/64). File này gỡ đúng từng bản vá của việc "Groq khai tử
model" rồi chạy lại `_test_groq_model.py`, và đòi mã thoát != 0.

BA CỘT TÁCH BẠCH — bài học cổng 54: `app/ai/llm.py` và `config.py` là **CRLF**
nên chuỗi tìm nhiều dòng viết `\\n` KHÔNG BAO GIỜ khớp; bản đầu của script thử
phá kia im lặng không phá được gì mà vẫn **đếm vào cột LỌT** = báo cáo ngược sự
thật. Nên ở đây "không tìm thấy chỗ phá" = **LỖI CỦA PHÉP THỬ**, đếm riêng.

  .venv\\Scripts\\python -u _pha_groq_model.py
"""
from __future__ import annotations

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

LLM = REPO / "app" / "ai" / "llm.py"
CFG = REPO / "config.py"
CHAM = REPO / "app" / "ai" / "cham_dich.py"

#: (tên phép phá, [(file, chuỗi TÌM, chuỗi THAY), ...])
PHEP = [
    ("P1 · dự phòng TRÙNG model chính (đúng lỗi kiến trúc làm app chết)", [
        (CFG, 'GROQ_LLM_FALLBACK = _env("GROQ_LLM_FALLBACK", "groq/compound")',
              'GROQ_LLM_FALLBACK = _env("GROQ_LLM_FALLBACK", '
              '"openai/gpt-oss-120b")'),
    ]),
    ("P2 · trả model CHÍNH về tên đã chết", [
        (CFG, 'GROQ_LLM_MODEL = _env("GROQ_LLM_MODEL", "openai/gpt-oss-120b")',
              'GROQ_LLM_MODEL = _env("GROQ_LLM_MODEL", '
              '"llama-3.3-70b-versatile")'),
    ]),
    ("P3 · gỡ nhánh 404 -> sang model kế trong _call_once", [
        (LLM, "                if _is_model_missing_error(str(e)):",
              "                if False:"),
    ]),
    ("P4 · coi 404 là HẾT HẠN MỨC rồi khoá key (vết xe 413 đốt 38 key)", [
        (LLM, '                        raise LLMModelMissing(\r\n'
              '                            f"Groq đã bỏ model «{md}» — app cần '
              'cập nhật "',
              '                        raise RuntimeError(\r\n'
              '                            f"Groq đã bỏ model «{md}» — app cần '
              'cập nhật "'),
        (LLM, '        return any(s in m for s in ("429", "quota", '
              '"rate limit", "ratelimit",',
              '        return any(s in m for s in ("429", "quota", '
              '"rate limit", "ratelimit", "model_not_found",'),
        (LLM, "                    if _is_model_missing_error(last):",
              "                    if False:"),
    ]),
    ("P5 · trả lời báo 404 về kiểu CŨ (trông như hết hạn mức)", [
        (LLM, "                    if _is_model_missing_error(last):",
              "                    if False:"),
        (LLM, "    if _is_model_missing_error(last):",
              "    if False:"),
    ]),
    ("P6 · trả hội đồng chấm dịch về model đã chết", [
        (CHAM, '    "openai/gpt-oss-120b",\n    "groq/compound",',
               '    "llama-3.3-70b-versatile",\n    "groq/compound",'),
    ]),
]


def doc(p: Path) -> str:
    with open(p, encoding="utf-8", newline="") as f:   # GIỮ NGUYÊN CRLF
        return f.read()


def ghi(p: Path, t: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)


def main() -> int:
    goc = {p: doc(p) for p in (LLM, CFG, CHAM)}
    bat = lot = khong_pha = 0
    try:
        for ten, sua in PHEP:
            print("\n" + "=" * 70)
            print(f"PHÁ: {ten}")
            for p in goc:
                ghi(p, goc[p])                      # về bản sạch trước mỗi phép
            hong_pha = ""
            for p, tim, thay in sua:
                t = doc(p)
                if tim not in t:
                    hong_pha = f"KHÔNG tìm thấy chỗ phá trong {p.name}"
                    break
                ghi(p, t.replace(tim, thay, 1))
            if hong_pha:
                khong_pha += 1
                print(f"  [LỖI PHÉP THỬ] {hong_pha}")
                print("  (KHÔNG đếm là LỌT — phép thử này chưa đụng được vào mã)")
                continue
            r = subprocess.run(
                [sys.executable, "-u", str(REPO / "_test_groq_model.py")],
                cwd=str(REPO), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=900)
            hong = [l for l in (r.stdout or "").splitlines() if "[HỎNG]" in l]
            tong = [l for l in (r.stdout or "").splitlines()
                    if l.startswith("CỔNG 69")]
            print(f"  mã thoát = {r.returncode}"
                  + (f"   |   {tong[-1]}" if tong else ""))
            for l in hong[:6]:
                print(f"    {l.strip()}")
            if r.returncode != 0:
                bat += 1
                print("  => BẮT ĐƯỢC (cổng đỏ đúng như phải đỏ)")
            else:
                lot += 1
                print("  => *** LỌT *** cổng vẫn xanh: chốt này KHÔNG được canh")
    finally:
        for p in goc:
            ghi(p, goc[p])
        print("\n(đã trả mọi file về bản sạch)")

    print("\n" + "=" * 70)
    print(f"THỬ PHÁ CỔNG 69 — BẮT {bat} · LỌT {lot} · "
          f"KHÔNG PHÁ ĐƯỢC {khong_pha}")
    print("=" * 70)
    return 1 if (lot or khong_pha) else 0


if __name__ == "__main__":
    sys.exit(main())
