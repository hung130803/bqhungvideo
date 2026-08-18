"""CỔNG 77 — KHÔNG CỔNG NÀO ĐƯỢC IN NGUYÊN VĂN KEY API (18/08/2026).

**LỖ HỔNG THẬT, KHÔNG PHẢI GIẢ ĐỊNH.** Lượt hồi quy v2.37.0 phát hiện cổng 70
(`_test_groq_model.py`) in `str(phat_key())` vào lời báo, mà `phat_key()` dựng
dict từ `llm._KEY_STATE` — **khoá của sổ đó là KEY THẬT**. Mục 9 của cổng 70
khôi phục `settings_cls.GROQ_API_KEYS = goc_keys` trước khi gọi Groq thật, nên
đúng lúc đó sổ key mang key thật của anh Hùng; key nào ăn 429 là bị `limited`
là bị in NGUYÊN VĂN ra `_kq70*.txt` nằm trên đĩa.

**CHẶN `_kq*` KHỎI GIT CHỈ LÀ LỚP NGOÀI.** File vẫn nằm trên đĩa, vẫn đi vào
mọi bản sao lưu / mọi lượt đồng bộ thư mục, và **lượt chạy sau vẫn in ra**.
Cổng này canh cái GỐC: không dòng mã nào được dựng chuỗi có key nguyên văn.

BA THƯỚC ĐỘC LẬP (một thước hỏng thì hai thước kia còn nói):
  1. **QUÉT TĨNH bằng AST** — mọi file cổng/đo, tìm đường từ NGUỒN KEY tới CHỖ
     IN. Dùng AST chứ KHÔNG tìm chuỗi: chính docstring này có chữ
     `_KEY_STATE`/`groq_keys`, tìm bằng chuỗi là **ĐỎ OAN VĨNH VIỄN** (bài học
     cổng 47 · 51 · 53 · 54 · 73 — đã sập 5 lần, đừng lần thứ 6).
  2. **QUÉT ĐĨA bằng CHÍNH KEY THẬT làm kim** — đọc key từ `settings` rồi tìm
     nguyên văn nó trong mọi file văn bản của repo. Đây là thước MẠNH NHẤT vì
     nó không cần đoán mẫu key.
  3. **QUÉT ĐĨA bằng MẪU `gsk_…`** — bắt được key của tài khoản KHÁC, key cũ
     đã xoá khỏi `.env`, key ElevenLabs… tức những key mà thước 2 không có kim.

**CỔNG NÀY TUYỆT ĐỐI KHÔNG ĐƯỢC IN KEY** (nó mà lộ thì nó chính là lỗ hổng nó
đi canh). Mọi lời báo chỉ mang: đường dẫn · số dòng · dạng ĐÃ CHE · số lượng.
Mục 5 có ca TỰ KIỂM chứng minh chính điều đó.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# In được tiếng Việt khi stdout bị chuyển hướng ra file (lượt hồi quy chạy
# `python _test_x.py > _kq77.txt`; không có dòng này là cp1252 ném
# UnicodeEncodeError ở dòng print đầu tiên rồi cổng "đỏ" vì lý do không liên
# quan tới mã app — đã dính 2 cổng hôm 14/08).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

DAT = HONG = 0
_HONG: list[str] = []


def ok(ten: str, dieu: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  [HỎNG] {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


# ───────────────────────────────────────────────────────────────────────────
# BỘ DÒ TĨNH
# ───────────────────────────────────────────────────────────────────────────

#: Tên gợi ra KEY NGUYÊN VĂN. `key_status` CỐ Ý KHÔNG có ở đây: nó đã tự che
#: (`"…" + k[-6:]`, xem `llm.key_status`) nên là nguồn SẠCH — kể nó vào là đỏ
#: oan cho mọi cổng đọc trạng thái key trên UI.
NGUON_KEY = {
    "_KEY_STATE", "groq_keys", "elevenlabs_keys", "llm_keys_for",
    "GROQ_API_KEYS", "ELEVENLABS_API_KEYS", "GEMINI_API_KEYS",
}

#: Hàm BỌC AN TOÀN: key đi qua nó thì cái ra KHÔNG còn là key.
#: `len`/`bool`/`sum`/`any`/`all`/`sorted`+`set` là các phép chỉ lấy SỐ LƯỢNG —
#: `print(f"{len(keys)} key")` là lối viết đúng và rất phổ biến trong repo
#: (`_ra_chep_loi.py`, `_test_mach_lac.py`…), chặn nó là đỏ oan hàng loạt.
BOC_AN_TOAN = {
    "che_key", "che_so_do", "len", "bool", "sum", "any", "all", "count",
    "key_masked", "enumerate",
}

#: Chỗ chữ ĐI RA NGOÀI (ra màn hình hoặc ra file).
SINK_GOI = {"print", "str", "repr", "format", "dumps", "write", "write_text",
            "writelines", "error", "warning", "info", "debug", "exception"}


def _ten_goi(node: ast.AST) -> str:
    """Tên cuối của một `Call.func` (`json.dumps` -> `dumps`)."""
    f = getattr(node, "func", None)
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _ten_trong(node: ast.AST) -> set[str]:
    """Mọi tên/thuộc tính xuất hiện trong một cây con."""
    ra: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            ra.add(n.id)
        elif isinstance(n, ast.Attribute):
            ra.add(n.attr)
    return ra


def _bi_danh(cay: ast.AST) -> set[str]:
    """Biến được GÁN TRỰC TIẾP từ một nguồn key -> cũng là nguồn key.

    `keys = settings.groq_keys()` rồi `print(keys)` là đúng cách lỗ hổng này
    tái sinh mà bộ dò chỉ soi tên gốc sẽ không thấy. Chỉ lần một tầng (gán
    thẳng) — đủ cho lối viết trong repo, và không lần sâu thì bộ dò không tự
    biến thành bộ suy luận kiểu.
    """
    ra: set[str] = set()
    for n in ast.walk(cay):
        if not isinstance(n, (ast.Assign, ast.AnnAssign)):
            continue
        gt = n.value
        if gt is None or not (_ten_trong(gt) & NGUON_KEY):
            continue
        dich = n.targets if isinstance(n, ast.Assign) else [n.target]
        for t in dich:
            for nn in ast.walk(t):
                if isinstance(nn, ast.Name):
                    ra.add(nn.id)
    return ra


def _cha_map(cay: ast.AST) -> dict:
    m = {}
    for n in ast.walk(cay):
        for c in ast.iter_child_nodes(n):
            m[c] = n
    return m


def _co_lo(goc: ast.AST, den: ast.AST, nguon: set[str], cha: dict) -> str:
    """Tên nguồn key LỘ RA trong cây con `den`, hoặc "" nếu sạch.

    "Lộ" = có một tham chiếu tới nguồn key mà trên đường đi từ nó lên `den`
    KHÔNG gặp phép bọc an toàn nào.
    """
    for con in ast.walk(den):
        ten = ""
        if isinstance(con, ast.Name):
            ten = con.id
        elif isinstance(con, ast.Attribute):
            ten = con.attr
        if ten not in nguon:
            continue
        cur = con
        an = False
        # **PHẢI XÉT CẢ CHÍNH `den`**, không dừng trước nó: `print(che_so_do(
        # _KEY_STATE))` có phép bọc an toàn nằm ĐÚNG ở nút ngoài cùng của cây
        # con, thoát vòng trước khi xét nó là BÁO OAN (đã sập 1 lần, và nó báo
        # oan đúng lối viết mà bản vá này vừa dựng lên).
        while cur is not None and cur is not goc:
            if isinstance(cur, ast.Call) and _ten_goi(cur) in BOC_AN_TOAN:
                an = True
                break
            # **CHỈ PHÉP CẮT LÁT mới là che.** `k[-4:]` cắt đuôi -> an toàn (lối
            # viết `_ra_key_groq.py`, `llm.key_status` đang dùng). Nhưng
            # `keys[0]` là **TRỌN MỘT KEY** — coi Subscript nào cũng an toàn là
            # để lọt đúng cái đáng bắt nhất (bản đầu của cổng này đã lọt).
            if isinstance(cur, ast.Subscript) and isinstance(cur.slice,
                                                            ast.Slice):
                an = True
                break
            # Cái RA là BOOLEAN, không phải key: `keys == x`, `not keys`, và
            # nhánh ĐIỀU KIỆN của `a if keys else b`.
            # **CỐ Ý KHÔNG kể `BoolOp`**: `print(keys or "khong")` trả về
            # CHÍNH `keys` khi nó không rỗng -> vẫn lộ.
            if isinstance(cur, (ast.Compare, ast.UnaryOp)):
                an = True
                break
            me = cha.get(cur)
            if isinstance(me, ast.IfExp) and me.test is cur:
                an = True
                break
            if cur is den:
                break
            cur = me
        if not an:
            return ten
    return ""


def _ham_tra_key(cay: ast.AST, nguon: set[str], cha: dict) -> set[str]:
    """Hàm nào TRẢ VỀ key thì CHÍNH TÊN HÀM cũng là nguồn key.

    **ĐÂY LÀ HÌNH DẠNG THẬT CỦA LỖ HỔNG 18/08/2026, đừng bỏ:** cổng 70 không
    hề `print(_KEY_STATE)`. Nó có `def phat_key(): return {k[1]: ...}` rồi ở
    tám chỗ khác viết `str(phat_key())`. Bộ dò chỉ soi tên gốc thì thấy cổng 70
    "sạch" — và phép THỬ PHÁ đã chứng minh đúng điều đó (gỡ phép che ra, mục
    quét tĩnh vẫn xanh, chỉ mục 6 kêu).

    Lặp tới điểm bất động để bắt cả chuỗi `a` gọi `b` gọi nguồn key.
    """
    ra: set[str] = set()
    for _ in range(4):
        truoc = len(ra)
        for n in ast.walk(cay):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if n.name in ra:
                continue
            for r in ast.walk(n):
                if isinstance(r, ast.Return) and r.value is not None and \
                        _co_lo(n, r.value, nguon | ra, cha):
                    ra.add(n.name)
                    break
        if len(ra) == truoc:
            break
    return ra


def do_mot_file(p: Path) -> list[tuple[int, str]]:
    """Trả [(dòng, mô tả)] các chỗ CÓ THỂ in key nguyên văn."""
    try:
        src = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        cay = ast.parse(src)
    except SyntaxError:
        return []

    cha = _cha_map(cay)
    nguon = NGUON_KEY | _bi_danh(cay)
    nguon |= _ham_tra_key(cay, nguon, cha)
    loi: list[tuple[int, str]] = []

    # SINK = mọi lời gọi ra-ngoài + mọi f-string (f-string tự nó là chỗ dựng
    # chuỗi; `print` bọc ngoài hay không thì chuỗi đó đã có key trong ruột).
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            if _ten_goi(n) not in SINK_GOI:
                continue
            phan = list(n.args) + [k.value for k in n.keywords]
            nhan = _ten_goi(n)
        elif isinstance(n, ast.JoinedStr):
            # NGOẠI LỆ DUY NHẤT, có lý do: f-string dựng HEADER `Authorization:
            # Bearer <key>` phải mang key TRỌN VẸN — đó là cách gửi key cho
            # Groq, không phải cách in ra. Nhận diện bằng chính phần chữ HẰNG
            # của f-string (`f"Bearer {k}"`), phạm vi hẹp nhất có thể.
            # Rủi ro còn lại được nói thẳng: ai viết `print(f"Bearer {k}")` thì
            # bộ dò tĩnh bỏ qua — nhưng MỤC 3/4 (quét đĩa bằng chính key thật)
            # vẫn bắt được, và đó mới là thước không phụ thuộc hình dạng mã.
            chu = "".join(v.value for v in n.values
                          if isinstance(v, ast.Constant)
                          and isinstance(v.value, str))
            if "Bearer" in chu or "Authorization" in chu:
                continue
            phan = [v.value for v in n.values
                    if isinstance(v, ast.FormattedValue)]
            nhan = "f-string"
        else:
            continue

        for arg in phan:
            ten = _co_lo(n, arg, nguon, cha)
            if ten:
                loi.append((getattr(arg, "lineno", getattr(n, "lineno", 0)),
                            f"{nhan}(... {ten} ...)"))
                break
    return loi


FILE_COng = ("_test_*.py", "_do_*.py", "_ra_*.py", "_pha_*.py", "_kiem_*.py",
             "_soi_*.py", "_bo_*.py", "_chay_*.py")


def liet_ke_cong() -> list[Path]:
    ra: set[Path] = set()
    for mau in FILE_COng:
        ra.update(REPO.glob(mau))
    return sorted(ra)


# ───────────────────────────────────────────────────────────────────────────
# BỘ DÒ ĐĨA
# ───────────────────────────────────────────────────────────────────────────

BO_QUA_DIR = {".git", ".venv", ".venv-build", "_lib", "_giong_ngoai", "_piper",
              "dist", "build", "node_modules", "__pycache__", ".pytest_cache",
              ".mypy_cache", "bin", "_giong_hang"}
DUOI_VAN_BAN = {".py", ".txt", ".json", ".md", ".yml", ".yaml", ".cfg", ".ini",
                ".bat", ".ps1", ".sh", ".csv", ".log", ".ass", ".srt", ".vtt",
                ".spec", ".toml", ".html", ".xml", ".env"}
CO_TOI_DA = 20 * 1024 * 1024


def file_van_ban():
    """Mọi file VĂN BẢN của repo, TRỪ `.env` (nơi key được phép nằm)."""
    for goc, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in BO_QUA_DIR]
        for f in files:
            p = Path(goc) / f
            if p.name == ".env" or p.name.startswith(".env."):
                continue
            if p.suffix.lower() not in DUOI_VAN_BAN:
                continue
            try:
                if p.stat().st_size > CO_TOI_DA:
                    continue
            except OSError:
                continue
            yield p


def main() -> int:
    print("=" * 70)
    print("CỔNG 77 — KHÔNG LỘ KEY API")
    print("=" * 70)

    from app.ai import llm

    # ─── MỤC 1: `che_key` làm đúng việc ───────────────────────────────────
    print("\nMỤC 1 — phép che (`llm.che_key`) làm đúng việc")
    THAT = "gsk_" + "Ab3" * 17 + "x"          # 56 ký tự, đúng dạng key thật
    assert len(THAT) == 56, len(THAT)
    che = llm.che_key(THAT)
    ok("key thật -> chuỗi NGẮN, giữ 4 đầu / 4 cuối",
       che == THAT[:4] + "…" + THAT[-4:] and len(che) == 9, che)
    ok("bản che KHÔNG chứa nguyên văn key", THAT not in che, che)
    ok("bản che KHÔNG chứa quá 8 ký tự liên tiếp của key",
       not any(THAT[i:i + 9] in che for i in range(len(THAT) - 8)), che)
    ok("key NGẮN bị che HẾT (không để lộ gần trọn)",
       llm.che_key("gsk_abc") == "*******", llm.che_key("gsk_abc"))
    ok("hai key khác đuôi -> hai chuỗi KHÁC nhau (còn phân biệt được)",
       llm.che_key("gsk_" + "0" * 48 + "_kA")
       != llm.che_key("gsk_" + "0" * 48 + "_kB"))
    ok("rỗng/None -> nhãn đọc được, không phải chuỗi trống",
       llm.che_key(None) == "(rỗng)" and llm.che_key("") == "(rỗng)")
    d = llm.che_so_do({("groq", THAT): "limited", THAT: "invalid"})
    ok("`che_so_do` che CẢ khoá tuple LẪN khoá chuỗi",
       THAT not in str(d) and len(d) == 2, str(d))
    ok("`che_so_do` giữ HÌNH DẠNG (rỗng vẫn rỗng -> phép so `== {}` còn đúng)",
       llm.che_so_do({}) == {})

    # ─── MỤC 2: quét tĩnh mọi cổng ────────────────────────────────────────
    print("\nMỤC 2 — QUÉT TĨNH (AST): không cổng nào in key nguyên văn")
    fs = liet_ke_cong()
    ok("quét được danh sách cổng/đo", len(fs) >= 40, f"{len(fs)} file")
    xau: list[str] = []
    for p in fs:
        for ln, mo in do_mot_file(p):
            xau.append(f"{p.name}:{ln} {mo}")
    ok("KHÔNG file nào có đường từ NGUỒN KEY tới CHỖ IN",
       not xau, "; ".join(xau[:6]) if xau else f"0/{len(fs)} file vi phạm")

    print("\nMỤC 2b — TỰ KIỂM BỘ DÒ TĨNH (bộ dò phải KÊU, không phải con dấu)")
    sb = REPO / f"_sb_lokey_{os.getpid()}"
    sb.mkdir(exist_ok=True)
    try:
        # (a) ca vi phạm TRỰC TIẾP
        pa = sb / "_test_via_a.py"
        pa.write_text(
            "from app.ai import llm\n"
            "def f():\n"
            "    print(str({k[1]: v for k, v in llm._KEY_STATE.items()}))\n",
            encoding="utf-8")
        ok("bắt được ca in thẳng `_KEY_STATE`", bool(do_mot_file(pa)),
           str(do_mot_file(pa)))
        # (b) ca vi phạm qua BÍ DANH (đúng cách lỗ hổng tái sinh)
        pb = sb / "_test_via_b.py"
        pb.write_text(
            "from config import settings\n"
            "def f():\n"
            "    keys = settings.groq_keys()\n"
            "    print(f'key: {keys}')\n",
            encoding="utf-8")
        ok("bắt được ca in qua BÍ DANH (`keys = groq_keys()` rồi in `keys`)",
           bool(do_mot_file(pb)), str(do_mot_file(pb)))
        # (b2) HÌNH DẠNG THẬT CỦA LỖ HỔNG: hàm phụ TRẢ VỀ key, chỗ khác mới in.
        # Phép THỬ PHÁ đã chứng minh bản đầu của bộ dò KHÔNG bắt được ca này.
        pb2 = sb / "_test_via_b2.py"
        pb2.write_text(
            "from app.ai import llm\n"
            "def phat_key():\n"
            "    return {k[1]: v for k, v in llm._KEY_STATE.items()}\n"
            "def f():\n"
            "    print('phat:', str(phat_key()))\n",
            encoding="utf-8")
        ok("bắt được ca hàm phụ TRẢ VỀ key rồi chỗ khác in (đúng lỗ hổng 70)",
           bool(do_mot_file(pb2)), str(do_mot_file(pb2)))
        # (b3) `keys[0]` là TRỌN MỘT KEY -> phải bắt. Bản đầu coi mọi Subscript
        # là "đã cắt đuôi" nên lọt đúng ca này.
        pb3 = sb / "_test_via_b3.py"
        pb3.write_text(
            "from config import settings\n"
            "def f():\n"
            "    keys = settings.groq_keys()\n"
            "    print('key dau:', keys[0])\n",
            encoding="utf-8")
        ok("bắt được `keys[0]` (trọn một key, KHÔNG phải phép cắt lát)",
           bool(do_mot_file(pb3)), str(do_mot_file(pb3)))
        # (c) ca SẠCH — bộ dò KHÔNG được kêu (chống đỏ oan)
        pc = sb / "_test_sach_c.py"
        pc.write_text(
            "from config import settings\n"
            "from app.ai import llm\n"
            "def f():\n"
            "    keys = settings.groq_keys()\n"
            "    print(f'so key = {len(keys)}')\n"
            "    print(llm.che_key(keys[0]) if keys else '')\n"
            "    print(llm.che_so_do(llm._KEY_STATE))\n"
            "    for k in keys:\n"
            "        print(f'...{k[-4:]}')\n",
            encoding="utf-8")
        ok("KHÔNG kêu oan với lối viết ĐÚNG (len / che_key / che_so_do / [-4:])",
           not do_mot_file(pc), str(do_mot_file(pc)))
        # (d) chính DOCSTRING/ghi chú có chữ `_KEY_STATE` -> KHÔNG được kêu
        pd = sb / "_test_sach_d.py"
        pd.write_text(
            '"""Ghi chú: đừng bao giờ print(_KEY_STATE) hay groq_keys()."""\n'
            "# print(settings.GROQ_API_KEYS)  <- ví dụ SAI, chỉ là ghi chú\n"
            "def f():\n"
            "    print('xong')\n",
            encoding="utf-8")
        ok("KHÔNG kêu oan vì DOCSTRING/GHI CHÚ (bài học cổng 47·51·53·54·73)",
           not do_mot_file(pd), str(do_mot_file(pd)))
        # (e) header `Bearer` phải được đi qua — đó là cách GỬI key, không phải
        # cách IN key. Chặn nó là đỏ oan cho mọi script gọi API bằng urllib.
        pe = sb / "_test_sach_e.py"
        pe.write_text(
            "from config import settings\n"
            "import urllib.request\n"
            "def f():\n"
            "    keys = settings.groq_keys()\n"
            "    urllib.request.Request('https://x',\n"
            "        headers={'Authorization': f'Bearer {keys[0]}'})\n",
            encoding="utf-8")
        ok("KHÔNG kêu oan với header `Bearer <key>` (cách GỬI, không phải IN)",
           not do_mot_file(pe), str(do_mot_file(pe)))
    finally:
        import shutil
        shutil.rmtree(sb, ignore_errors=True)

    # ─── MỤC 3: quét đĩa bằng CHÍNH KEY THẬT ──────────────────────────────
    print("\nMỤC 3 — QUÉT ĐĨA bằng CHÍNH KEY THẬT làm kim")
    from config import settings
    kim: list[str] = []
    for ten in ("groq_keys", "elevenlabs_keys"):
        try:
            kim += [k for k in (getattr(settings, ten)() or []) if len(k) >= 20]
        except Exception:                                   # noqa: BLE001
            pass
    print(f"  (kim: {len(kim)} key, độ dài {sorted({len(k) for k in kim})})")
    if not kim:
        print("  (BỎ QUA: máy này chưa cấu hình key -> không có kim để tìm)")
    else:
        lo: list[str] = []
        n_file = 0
        for p in file_van_ban():
            n_file += 1
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for k in kim:
                if k in t:
                    ln = t[:t.index(k)].count("\n") + 1
                    lo.append(f"{p.relative_to(REPO)}:{ln} "
                              f"[{llm.che_key(k)}]")
                    break
        ok("KHÔNG file văn bản nào chứa key THẬT",
           not lo, "; ".join(lo[:8]) if lo else f"0 chỗ / {n_file} file")

    # ─── MỤC 4: quét đĩa bằng MẪU (bắt key tài khoản KHÁC) ────────────────
    print("\nMỤC 4 — QUÉT ĐĨA bằng MẪU `gsk_…` (thước độc lập với mục 3)")
    import re
    # Key Groq thật: `gsk_` + 52 ký tự. Ngưỡng 40 để bắt cả key bị cắt cụt,
    # nhưng vẫn TRÊN mọi key giả trong repo (dài nhất `gsk_test`+45+`_kA` = 56
    # nhưng có chữ `test` -> loại bằng danh sách dưới).
    RE_KEY = re.compile(r"gsk_[A-Za-z0-9_]{40,}")
    # Key GIẢ được phép: phải nói rõ mình là giả.
    GIA = ("test", "kiemthu", "fake", "gia", "example", "xxxx", "0000")
    lo2: list[str] = []
    for p in file_van_ban():
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in RE_KEY.finditer(t):
            s = m.group(0)
            if any(g in s.lower() for g in GIA):
                continue
            ln = t[:m.start()].count("\n") + 1
            lo2.append(f"{p.relative_to(REPO)}:{ln} [{llm.che_key(s)}]")
    ok("KHÔNG file nào chứa chuỗi dạng key thật",
       not lo2, "; ".join(lo2[:8]) if lo2 else "0 chỗ")

    print("\nMỤC 4b — TỰ KIỂM BỘ DÒ ĐĨA")
    sb2 = REPO / f"_sb_lokey2_{os.getpid()}"
    sb2.mkdir(exist_ok=True)
    try:
        gia_that = "gsk_" + "Zq7" * 17 + "w"        # 56 ký tự, KHÔNG chữ 'test'
        (sb2 / "roi.txt").write_text(f"phat_key -> {gia_that}\n",
                                     encoding="utf-8")
        thay = [str(p.relative_to(REPO)) for p in file_van_ban()
                if gia_that in p.read_text(encoding="utf-8", errors="ignore")]
        ok("bộ quét đĩa TÌM RA được file có chuỗi dạng key",
           len(thay) == 1, str(thay))
        ok("bộ quét đĩa CÓ ĐI QUA `_kq*.txt` (đúng chỗ lỗ hổng đã xảy ra)",
           any(p.name.startswith("_kq") for p in file_van_ban()))
    finally:
        import shutil
        shutil.rmtree(sb2, ignore_errors=True)

    # ─── MỤC 5: git không được theo dõi chỗ có key ────────────────────────
    print("\nMỤC 5 — git KHÔNG được theo dõi `.env` và `_kq*`")

    def _git(*a) -> tuple[int, str]:
        try:
            r = subprocess.run(["git", *a], cwd=str(REPO), capture_output=True,
                               text=True, timeout=60)
            return r.returncode, (r.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return -1, str(e)

    rc, _ = _git("check-ignore", "-q", ".env")
    ok("`.env` bị .gitignore chặn", rc == 0, f"rc={rc}")
    rc2, _ = _git("check-ignore", "-q", "_kq70.txt")
    ok("`_kq*` bị .gitignore chặn (lớp ngoài của lỗ hổng)", rc2 == 0,
       f"rc={rc2}")
    rc3, out3 = _git("ls-files", "--", ".env", "_kq*", "_ket_*")
    ok("git KHÔNG theo dõi file nào trong nhóm đó", rc3 == 0 and not out3,
       out3[:200] or "0 file")

    # ─── MỤC 6: cổng 70 — đúng chỗ lỗ hổng — phải dùng phép che ───────────
    print("\nMỤC 6 — cổng 70 (`_test_groq_model.py`) phải che ở NGUỒN")
    p70 = REPO / "_test_groq_model.py"
    ok("cổng 70 còn trên đĩa", p70.exists())
    if p70.exists():
        cay = ast.parse(p70.read_text(encoding="utf-8"))
        # `phat_key` phải THẬT SỰ GỌI `che_so_do`/`che_key` (đòi lời GỌI, không
        # đòi mặt chữ — bài học cổng 56d/64: quét chuỗi thì phép phá giữ nguyên
        # mặt chữ mà đổi ý nghĩa vẫn lọt).
        goi: set[str] = set()
        for n in ast.walk(cay):
            if isinstance(n, ast.FunctionDef) and n.name == "phat_key":
                goi = {_ten_goi(c) for c in ast.walk(n)
                       if isinstance(c, ast.Call)}
        ok("`phat_key` GỌI phép che (che_so_do/che_key)",
           bool(goi & {"che_so_do", "che_key"}), str(sorted(goi)))
        ok("cổng 70 sạch theo bộ dò tĩnh", not do_mot_file(p70),
           str(do_mot_file(p70)))

    print("\n" + "=" * 70)
    print(f"CỔNG 77 — ĐẠT {DAT} · HỎNG {HONG}")
    for d in _HONG:
        print(f"   HỎNG: {d}")
    print("=" * 70)
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
