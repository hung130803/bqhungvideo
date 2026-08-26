# -*- coding: utf-8 -*-
"""`goi_y_may()` CÓ ĐƯỢC GỌI TRÊN ĐƯỜNG ANH HÙNG ĐI KHÔNG — TRUY VẾT THẬT.

Anh Hùng chọn **Ngôn ngữ đích = Tiếng Anh** + **Giọng đọc = `adam Clone`
(`vnb:`)** rồi báo *"cách phát âm bị lỗi... đọc như thằng mới học"*.
`nhan_ban_giong.goi_y_may()` đã có sẵn luật `vi -> VieNeu · en/zh -> Chatterbox`.
Câu hỏi: **luật đó có chạy trên đường ấy không?**

═══════════════════════════════════════════════════════════════════════════
ĐỌC MÃ RỒI SUY LÀ DỪNG QUÁ SỚM — PHẢI GỌI THẬT
═══════════════════════════════════════════════════════════════════════════
Đúng bài học của chính lượt đo Adam: đọc tới `SEAPipeline(lang="vi")` rồi kết
luận "nó đọc tiếng Anh bằng bộ âm Việt" là SAI, vì chạy thật thì chữ Anh ra âm
Anh. Nên ở đây:
  · phép 1 dùng **AST** (không phải grep chuỗi) để đếm nơi gọi THẬT SỰ, và tự
    kiểm bộ dò bằng một file mồi có cả docstring lẫn ghi chú chứa tên hàm;
  · phép 2 **GỌI THẬT** `dubbing._synth_all` với đúng bộ tham số của anh Hùng
    rồi xem nó rẽ vào máy nào (bọc `giong_vieneu.doc_loat` /
    `giong_chatter.doc_loat` để ghi nhật ký, KHÔNG đọc thật -> không tốn model).

Chạy:  .venv\\Scripts\\python -u _do_vet_goiymay.py
"""
from __future__ import annotations

import ast
import asyncio
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

TEN = "goi_y_may"


# --------------------------------------------------------------- phép 1: AST
def noi_goi(src: str) -> list[str]:
    """Tên hàm bao quanh MỖI nơi gọi ``goi_y_may(...)`` — bằng AST.

    Quét chuỗi thì dòng ghi chú tiếng Việt và docstring cũng trúng: repo này đã
    sập bẫy đó 8 lần, **cả hai chiều**. `ast.parse` bỏ ghi chú hẳn; docstring
    vẫn là node `Constant` nên nó KHÔNG lọt vào `ast.Call`.
    """
    ra: list[str] = []
    cay = ast.parse(src)
    bao: list[str] = []

    class Di(ast.NodeVisitor):
        def _ham(self, n):
            bao.append(n.name)
            self.generic_visit(n)
            bao.pop()

        visit_FunctionDef = _ham          # noqa: N815
        visit_AsyncFunctionDef = _ham     # noqa: N815

        def visit_Call(self, n):          # noqa: N802
            f = n.func
            ten = (getattr(f, "attr", None)
                   or getattr(f, "id", None) or "")
            if ten == TEN:
                ra.append(bao[-1] if bao else "<tầm module>")
            self.generic_visit(n)

    Di().visit(cay)
    return ra


def tu_kiem_bo_do() -> bool:
    """TỰ KIỂM BỘ DÒ — mồi có 3 cái bẫy đã làm repo này sai 8 lần.

    Bẫy 1: ghi chú tiếng Việt nhắc tên hàm · bẫy 2: DOCSTRING nhắc tên hàm
    (`ast.unparse` GIỮ docstring nên bộ dò nào so chuỗi trên mã đã unparse là
    PASS OAN) · bẫy 3: một chuỗi ký tự chứa tên hàm.
    Đáp án đúng: **đúng 1** nơi gọi, nằm trong `that_su_goi`.
    """
    moi = (
        'def khong_goi():\n'
        '    """Hàm này nhắc goi_y_may trong DOCSTRING mà không gọi."""\n'
        '    # ghi chú tiếng Việt: goi_y_may(lang) sẽ quyết máy\n'
        '    s = "goi_y_may"\n'
        '    return s\n'
        '\n'
        'def that_su_goi(lang):\n'
        '    return goi_y_may(lang)\n')
    kq = noi_goi(moi)
    dat = kq == ["that_su_goi"]
    print(f"  TỰ KIỂM BỘ DÒ: {kq} -> {'ĐẠT' if dat else 'HỎNG'} "
          f"(đáp án ['that_su_goi'])")
    return dat


def phep1() -> dict:
    print("\n" + "=" * 74)
    print("PHÉP 1 — AST: `goi_y_may` ĐƯỢC GỌI Ở ĐÂU TRONG `app/`")
    print("=" * 74)
    if not tu_kiem_bo_do():
        print("  DỪNG: bộ dò không tin được")
        return {}
    ra: dict[str, list[str]] = {}
    for p in sorted(REPO.joinpath("app").rglob("*.py")):
        try:
            n = noi_goi(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        if n:
            ra[str(p.relative_to(REPO))] = n
    if not ra:
        print("  KHÔNG nơi nào trong `app/` gọi -> HÀM CHẾT HOÀN TOÀN")
    for f, ns in ra.items():
        print(f"  {f}: gọi trong {ns}")
    ui = {f: n for f, n in ra.items() if f.replace("\\", "/").startswith("app/ui/")}
    print(f"  -> trong `app/ui/`: {len(ui)} nơi gọi THẬT "
          f"(grep chuỗi trả 2 dòng — cả hai là GHI CHÚ)")
    return ra


# ------------------------------------------------------- phép 2: GỌI THẬT
def phep2() -> dict:
    """Gọi THẬT `dubbing._synth_all` với đúng bộ tham số của anh Hùng."""
    print("\n" + "=" * 74)
    print("PHÉP 2 — GỌI THẬT `dubbing._synth_all(voice='vnb:...', lang='en')`")
    print("=" * 74)
    from app.core import dubbing, giong_chatter, giong_vieneu

    log: list[str] = []
    cu_vn, cu_cb = giong_vieneu.doc_loat, giong_chatter.doc_loat

    def gia_vn(*a, **k):
        log.append("giong_vieneu.doc_loat")
        n = len(a[0]) if a else 0
        return ([False] * n, [[] for _ in range(n)])

    def gia_cb(*a, **k):
        log.append("giong_chatter.doc_loat")
        n = len(a[0]) if a else 0
        return ([False] * n, [[] for _ in range(n)])

    giong_vieneu.doc_loat = gia_vn                      # type: ignore[assignment]
    giong_chatter.doc_loat = gia_cb                     # type: ignore[assignment]
    tam = Path(tempfile.mkdtemp(prefix="bq_vet_"))
    ra: dict = {}
    try:
        mau = tam / "mau.wav"
        mau.write_bytes(b"\0" * 8000)                   # không đọc thật -> đủ
        for nhan, voice, lang in (
                ("anh Hùng ĐANG ĐI: vnb: + đích ANH", f"vnb:{mau}", "en"),
                ("đối chứng:        vnb: + đích VIỆT", f"vnb:{mau}", "vi"),
                ("đối chứng:        cb:en| + đích ANH", f"cb:en|{mau}", "en")):
            log.clear()
            try:
                asyncio.run(dubbing._synth_all(["Hello world."], voice,
                                               [str(tam / "ra.mp3")],
                                               lang=lang))
            except Exception as e:                      # noqa: BLE001
                log.append(f"[ném {type(e).__name__}]")
            di = log[0] if log else "edge-tts (không máy nhân bản nào)"
            ra[nhan] = di
            print(f"  {nhan:<40} -> {di}")
    finally:
        giong_vieneu.doc_loat = cu_vn                   # type: ignore[assignment]
        giong_chatter.doc_loat = cu_cb                  # type: ignore[assignment]
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(str(tam))
    return ra


# ------------------------------------------------ phép 3: luật vs thực tế
def phep3() -> None:
    print("\n" + "=" * 74)
    print("PHÉP 3 — LUẬT `goi_y_may` NÓI GÌ, VÀ SỔ GIỌNG THẬT GHI GÌ")
    print("=" * 74)
    from app.core import nhan_ban_giong as NB
    for lg in ("vi", "en", "zh", "ja"):
        print(f"  goi_y_may({lg!r}) = {NB.goi_y_may(lg)!r}")
    import json
    so = Path(NB.duong_so())
    print(f"  sổ giọng thật: {so}")
    if so.exists():
        d = json.loads(so.read_text(encoding="utf-8"))
        for ten, g in d.items():
            print(f"    «{ten}»: may={g.get('may')!r} lang={g.get('lang')!r}"
                  f"  -> mã combo bắt đầu bằng "
                  f"{'cb:' if g.get('may') == NB.MAY_CHATTER else 'vnb:'}")
    else:
        print("    (không có sổ trên máy này)")


def main() -> int:
    print("=" * 74)
    print("`goi_y_may` CÓ SỐNG TRÊN ĐƯỜNG ANH HÙNG ĐI KHÔNG")
    print("=" * 74)
    goi = phep1()
    di = phep2()
    phep3()

    print("\n" + "=" * 74)
    print("KẾT LUẬN")
    print("=" * 74)
    co_ui = any(f.replace("\\", "/").startswith("app/ui/") for f in goi)
    print(f"  · `app/ui/` gọi trực tiếp: {'CÓ' if co_ui else 'KHÔNG'}")
    print(f"  · nơi gọi THẬT trong `app/`: "
          f"{ {f: n for f, n in goi.items()} }")
    d = di.get("anh Hùng ĐANG ĐI: vnb: + đích ANH", "")
    print(f"  · đích ANH + giọng `vnb:` rẽ vào: **{d}**")
    print("  · => luật `en -> Chatterbox` KHÔNG chạy lúc ĐỌC; nó chỉ chạy lúc "
          "THÊM GIỌNG (`them_giong`), với ngôn ngữ khai lúc ấy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
