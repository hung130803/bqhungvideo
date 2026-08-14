# -*- coding: utf-8 -*-
r"""ĐO PHÉP 5 — RÀ ĐƯỜNG DỰ PHÒNG IM LẶNG KHI GẶP TIẾNG TRUNG.

    .venv\Scripts\python _do_ra_soat.py

"Im lặng" = app vẫn chạy, ffmpeg vẫn mã 0, nhật ký không một dòng báo, chỉ
CHẤT LƯỢNG tụt. Ở đây rà 4 chỗ:
  (a) `hook_to_mo` — 6 nhóm từ khoá, nhóm nào KHÔNG có chữ Trung thì video
      tiếng Trung mất hẳn tín hiệu của nhóm đó (không ai báo).
  (b) `hook_to_mo` chạy trên bản chép lời TRUNG THẬT: chọn được hook hay
      trả None (None = LÙI VỀ đường cao trào TIẾNG của v2.20.0).
  (c) quét TĨNH: chỗ nào còn đếm từ bằng `.split()` trên chữ chép lời — với
      CJK là ra 1 token (đúng lỗi cổng 40 đã bắt ở `co_loi_noi_that`).
  (d) log của lượt chạy thật: dòng nào là "bỏ qua/không chọn/mặc định".
"""
from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def _loai(t: str) -> str:
    kana = any(0x3040 <= ord(c) <= 0x30FF for c in t)
    hang = any(0xAC00 <= ord(c) <= 0xD7AF for c in t)
    han = any(0x4E00 <= ord(c) <= 0x9FFF for c in t)
    if kana:
        return "nhat"
    if hang:
        return "han"
    if han:
        return "chi-han"          # Trung, HOẶC từ Nhật viết bằng kanji
    return "latin"


def main() -> int:
    from app.ai import hook_to_mo as HK

    print("══ (a) hook_to_mo — nhóm nào KHÔNG có chữ Trung ══")
    trong = []
    for tap, trong_so, ten in HK._NHOM:
        d = {}
        for t in tap:
            d[_loai(t)] = d.get(_loai(t), 0) + 1
        n_han = d.get("chi-han", 0)
        print(f"    {ten:<22} hệ số {trong_so:.2f} · {len(tap):3d} từ · "
              f"latin {d.get('latin', 0):3d} · Nhật(kana) {d.get('nhat', 0):3d}"
              f" · Hàn {d.get('han', 0):3d} · chỉ-chữ-Hán {n_han:3d}")
        if n_han == 0:
            trong.append(ten)
    print(f"  -> nhóm KHÔNG có một chữ Hán nào: {trong or 'không nhóm nào'}")

    print("\n══ (b) hook_to_mo TRÊN LỜI TRUNG THẬT ══")
    tj = WORK / "trung_transcript.json"
    if not tj.exists():
        print("  BỎ QUA: chưa có bản chép lời.")
        return 1
    tr = json.loads(tj.read_text(encoding="utf-8"))
    segs = [[0.0, 187.27]]
    ra = HK.chon_hook_to_mo(tr, segs, top=5)
    if not ra:
        print("  chon_hook_to_mo -> None  ==> LÙI VỀ đường cao trào TIẾNG "
              "(im lặng, không dòng log nào)")
    else:
        for x in (ra if isinstance(ra, list) else [ra]):
            print(f"    {x}")
    n_co = n_khong = 0
    for s in (tr.get("segments") or [])[:400]:
        t = str(s.get("text", ""))
        d, ly = HK.cham_cau(t, float(s.get("start", 0)))
        if d >= HK.NGUONG:
            n_co += 1
            if n_co <= 5:
                print(f"    ĐẠT {d:.3f} · {ly[:70]} · «{t[:38]}»")
        else:
            n_khong += 1
    print(f"  câu ĐẠT ngưỡng {HK.NGUONG}: {n_co} · dưới ngưỡng: {n_khong} "
          f"(tổng {n_co + n_khong} câu tiếng Trung)")

    print("\n══ (c) QUÉT TĨNH: còn chỗ nào đếm từ bằng `.split()` ══")
    #: dùng AST nên KHÔNG kể dòng ghi chú / chuỗi tài liệu (bài học cổng 47)
    #: PHÂN LOẠI, không gộp một cục: `" ".join(x.split())` chỉ CHUẨN HOÁ
    #: KHOẢNG TRẮNG (CJK không hề hấn), còn `len(x.split())` / `for w in
    #: x.split()` mới là ĐẾM TỪ THẬT -> CJK ra 1 token = hỏng im lặng.
    that, vo_hai = [], []
    for f in sorted((REPO / "app").rglob("*.py")):
        try:
            cay = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        cha = {}
        for n in ast.walk(cay):
            for c in ast.iter_child_nodes(n):
                cha[c] = n
        for n in ast.walk(cay):
            if not (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "split" and not n.args):
                continue
            src = ast.unparse(n.func.value)
            if not any(k in src.lower() for k in
                       ("text", "loi", "cau", "txt", "script", "noi_dung",
                        "title", "tieu_de", "word")):
                continue
            p = cha.get(n)
            chuan_hoa = (isinstance(p, ast.Call)
                         and isinstance(p.func, ast.Attribute)
                         and p.func.attr == "join")
            (vo_hai if chuan_hoa else that).append(
                (str(f.relative_to(REPO)), n.lineno, src[:52],
                 ast.unparse(p)[:60] if p is not None else ""))
    print("  -- ĐẾM TỪ THẬT (CJK -> 1 token, HỎNG IM LẶNG) --")
    for p, ln, src, ctx in that:
        print(f"    {p}:{ln}  `{ctx}`")
    print("  -- chỉ chuẩn hoá khoảng trắng (VÔ HẠI với CJK) --")
    for p, ln, src, ctx in vo_hai:
        print(f"    {p}:{ln}  `{ctx}`")
    print(f"  -> ĐẾM TỪ THẬT: {len(that)} chỗ · vô hại: {len(vo_hai)} chỗ")

    print("\n══ (d) LOG LƯỢT CHẠY THẬT ══")
    lg = WORK / "data" / "logs"
    if lg.is_dir():
        for f in sorted(lg.rglob("*.log")):
            t = f.read_text(encoding="utf-8", errors="replace")
            for ln in t.splitlines():
                if any(k in ln.lower() for k in (
                        "bỏ qua", "không thêm", "không chọn", "mặc định",
                        "cơ bản", "fallback", "lùi", "thiếu", "không có",
                        "không rõ", "lỗi", "error", "warn")):
                    print(f"    [{f.name}] {ln.strip()[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
