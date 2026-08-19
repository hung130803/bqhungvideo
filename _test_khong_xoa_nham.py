# -*- coding: utf-8 -*-
"""CỔNG 80 — KHÔNG BAO GIỜ ĐƯỢC XOÁ NHẦM THƯ MỤC ĐANG LÀM VIỆC.

═══════════ VÌ SAO CỔNG NÀY RA ĐỜI: ĐÃ MẤT CẢ CÂY MÃ, 19/08/2026 ═══════════
`giong_ngoai._doc_omnivoice` gọi ``_don(Path(ket.get("_sandbox") or ""))`` ở
nhánh LỖI. `_chay_ov` không đặt `_sandbox` ở nhánh quá-giờ -> `.get` trả None
-> ``or ""`` -> ``Path("")``. Và **``Path("")`` KHÔNG RỖNG**:

    Path("")            ->  WindowsPath('.')
    str(Path(""))       ->  '.'        (truthy: lọt mọi canh `if d`)
    Path("").is_dir()   ->  True       (lọt mọi canh `is_dir()`)
    shutil.rmtree(...)  ->  XOÁ SẠCH THƯ MỤC ĐANG LÀM VIỆC

Mất `.git` (chỉ còn `objects`), `.venv`, `bin`, `_lib`, `_giong_hang`,
`_piper`, `_giong_ngoai`. **Mã thoát vẫn 0.** `b5bd003` vá ĐÚNG MỘT cửa
(`giong_ngoai` + `giong_vieneu`). Cổng này canh **cả lớp bệnh**, vì quét
19/08/2026 tìm được thêm **5 cửa cùng hình dạng** trong `app/`.

CỔNG NÀY CHẤM GÌ (7 ca):
  1. `xoa_an_toan.ly_do_cam` — hàm THUẦN, cửa chung.
  2. `xoa_an_toan.don_thu_muc` — xoá THẬT, có mồi canary.
  3. 6 hàm dọn SẢN XUẤT × 8 đầu vào nguy hiểm, `rmtree` THẬT.
  4. Cùng 6 hàm × 4 đầu vào KHÔNG THỬ THẬT ĐƯỢC (gốc ổ đĩa, thư mục người
     dùng, gốc cây mã) — chạy với `rmtree` bị vá thành GIÁN ĐIỆP.
  5. `services.delete_project` — đường NGƯỜI DÙNG BẤM, dữ liệu vào từ DB.
  6. QUÉT TĨNH: không được có `shutil.rmtree` MỚI ở `app/` ngoài danh sách
     đã rà. Đây là ca duy nhất bắt được cửa hở người sau THÊM VÀO.
  7. **TỰ KIỂM BỘ DÒ** — dựng lại đúng mã CŨ (`if d and str(d) and
     d.is_dir(): rmtree(d)`) rồi bắt bộ dò phải KÊU. Cổng nào không tự phá
     được chính mình thì nó chỉ là con dấu (bài học cổng 56d · 64 · 73).

BA CHỐT AN TOÀN CỦA CHÍNH CỔNG NÀY (đọc trước khi sửa):
  · **CWD ĐƯỢC ĐỔI SANG HỘP CÁT.** Mọi ca "xoá thật" đều chạy với
    `os.chdir(<hộp cát>/lam)`, nên nếu bản vá hỏng thì thứ bị xoá là hộp cát
    chứ không phải repo. **TUYỆT ĐỐI KHÔNG chạy cổng này với cwd = repo.**
  · **GỐC Ổ ĐĨA KHÔNG BAO GIỜ ĐƯỢC ĐƯA CHO `rmtree` THẬT.** Ca 4 vá
    `shutil.rmtree` thành hàm CHỈ GHI SỔ. Guard hỏng thì cổng đọc được sổ và
    báo HỎNG — chứ không phải xoá ổ C rồi mới biết.
  · **MỒI CANARY ĐẶT Ở CẢ `lam/` LẪN THƯ MỤC CHA.** Chỉ đặt trong `lam/` thì
    `".."` (xoá thư mục cha) đi lọt.

CỔNG KHÔNG gọi mạng · KHÔNG chạy ffmpeg · KHÔNG đụng Groq · KHÔNG đụng
`%LOCALAPPDATA%\\BQHungVideo` -> tiền định, không nhấp nháy.

    .venv\\Scripts\\python -u _test_khong_xoa_nham.py
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

for _f in (sys.stdout, sys.stderr):
    # cp1252 khi `> file.txt`: dòng print tiếng Việt ĐẦU TIÊN ném
    # UnicodeEncodeError -> cổng chết trong 0 giây và bị đổ oan cho bản vá.
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

# ---------------------------------------------------------------------------
# HỘP CÁT — dựng TRƯỚC khi import app, và đổi CWD sang đó.
# ---------------------------------------------------------------------------
def _tao(p: Path) -> Path:
    """`mkdir -p` CHỊU ĐƯỢC MÁY NÀY.

    Có vòng THỬ LẠI vì `mkdir` trong `%TEMP%` thỉnh thoảng ném ngay sau khi
    vừa tạo thư mục cha; cổng CHẾT giữa chừng (rc != 0, KHÔNG có dòng tổng
    kết) khó đọc hơn hẳn cổng báo HỎNG tử tế.

    **BẪY ĐÃ SẬP KHI VIẾT CỔNG NÀY — TÊN THƯ MỤC `con`:** hộp cát bản đầu
    dùng ``_SB/"goc_khac"/"con"`` và ``NotADirectoryError [WinError 267]``
    nổ **100% lượt**, kể cả với `os.makedirs` + 5 lần thử lại. `CON` là **TÊN
    THIẾT BỊ của Windows** (cùng họ `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`) nên
    KHÔNG BAO GIỜ tạo được. Bẫy này đã có sẵn trong repo —
    `piper_tts._lam_sach` ghi đúng nó (`con` -> `con_.wav`) — mà lượt này vẫn
    dẫm phải. Lời lỗi trông y hệt lỗi tranh chấp AV nên suýt bị chữa nhầm
    bằng "thử lại nhiều lần hơn".
    """
    for _ in range(5):
        try:
            os.makedirs(p, exist_ok=True)
        except OSError:
            pass
        if p.is_dir():
            return p
    os.makedirs(p, exist_ok=True)
    return p


def _don_rac_luot_truoc() -> int:
    """Dọn hộp cát của những lượt chạy TRƯỚC bị giết giữa chừng.

    Lượt chạy êm thì `finally` tự dọn, nhưng lượt bị `taskkill` thì không —
    và cổng này ĐÃ bị giết hai lần trong ngày làm ra nó, để lại **25 thư mục
    / 25 MB** trong `%TEMP%`. Máy dev CHÍNH LÀ máy anh Hùng và ổ C đã từng
    đầy 100%, nên "test không để rác trên máy user" là luật, không phải phép
    lịch sự (cùng lý do `_test_guard` tự dọn `%TEMP%` của lần trước).

    CHỈ xoá thư mục khớp `xoanham_*` nằm THẲNG trong `%TEMP%` và đã cũ hơn
    1 giờ — thư mục của một lượt ĐANG chạy song song không bị đụng.
    """
    n = 0
    try:
        goc = Path(tempfile.gettempdir()).resolve()
        han = time.time() - 3600
        for p in goc.glob("xoanham_*"):
            try:
                if not p.is_dir() or p.parent != goc or p.stat().st_mtime > han:
                    continue
                shutil.rmtree(p, ignore_errors=True)
                n += 1
            except OSError:
                continue
    except OSError:
        pass
    return n


_RAC_CU = _don_rac_luot_truoc()

_SB = Path(tempfile.mkdtemp(prefix="xoanham_")).resolve()
LAM = _SB / "lam"                    # đây sẽ là CWD của cả lượt chạy
_tao(LAM / "moi_con")

#: Mồi canary. `_SB/MOI_CHA.txt` nằm ở THƯ MỤC CHA của cwd — nó bắt ca `".."`.
MOI = (
    _SB / "MOI_CHA.txt",
    LAM / "MOI_GOC.txt",
    LAM / "moi_con" / "MOI_CON.txt",
)
for _m in MOI:
    _m.write_text("mồi canary cổng 80 — mất file này nghĩa là đã xoá nhầm\n",
                  encoding="utf-8")

os.environ["BQ_DATA_DIR"] = str(_SB / "data")
os.environ["BQ_DB_PATH"] = str(_SB / "data" / "studio.db")
_tao(_SB / "data")

_CWD_CU = os.getcwd()
os.chdir(LAM)

from app.core import xoa_an_toan as XA          # noqa: E402
from app.core import giong_ngoai as GN          # noqa: E402
from app.core import giong_vieneu as GV         # noqa: E402
from app.core import piper_tts as PT            # noqa: E402
from app.core import tempsweep as TS            # noqa: E402
from app.core import thay_giong as TG           # noqa: E402
from app.queue import jobs as JOBS              # noqa: E402
from app import services as SV                  # noqa: E402

DAT = 0
HONG = 0
_HONG_TEN: list[str] = []


def ok(ten: str, dieu_kien: bool, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if dieu_kien:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        _HONG_TEN.append(ten)
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return dieu_kien


# ---------------------------------------------------------------------------
# Bộ đầu vào nguy hiểm
# ---------------------------------------------------------------------------
def dau_vao_that() -> list[tuple[str, object]]:
    """Đầu vào THỬ THẬT ĐƯỢC: xấu nhất cũng chỉ phá trong hộp cát."""
    return [
        ('chuỗi rỗng ""', ""),
        ("None", None),
        ('chuỗi "."', "."),
        ('Path("")  <- THỦ PHẠM THẬT', Path("")),
        ('chuỗi "   " (toàn khoảng trắng)', "   "),
        ('chuỗi ".." (thư mục CHA)', ".."),
        ('Path(".")', Path(".")),
        ("đường dẫn không tồn tại", str(_SB / "khong_he_ton_tai_xyz")),
    ]


def dau_vao_gian_diep() -> list[tuple[str, object]]:
    """Đầu vào KHÔNG được đưa cho `rmtree` thật — chỉ chạy với gián điệp."""
    ds = [
        ("gốc ổ đĩa của repo", REPO.anchor),
        ("gốc ổ C", "C:\\"),
        ("thư mục người dùng", str(Path.home())),
        ("gốc cây mã (repo)", str(REPO)),
    ]
    return [(t, v) for t, v in ds if str(v).strip()]


def moi_con_du() -> list[str]:
    return [m.name for m in MOI if not m.exists()]


class GianDiep:
    """Thay `shutil.rmtree`: CHỈ GHI SỔ, không xoá một byte nào."""

    def __init__(self) -> None:
        self.goi: list[str] = []

    def __call__(self, p, *a, **k):
        self.goi.append(str(p))
        return None


# ---------------------------------------------------------------------------
# Các hàm dọn SẢN XUẤT đang được canh
# ---------------------------------------------------------------------------
def _goi_jobs(d) -> None:
    JOBS._don_thu_muc_tam({"thu_muc_lam": d})


def _goi_tempsweep(d) -> None:
    TS._xoa(Path(d) if d is not None else Path(""))


HAM_DON = (
    ("xoa_an_toan.don_thu_muc", lambda d: XA.don_thu_muc(d)),
    ("giong_ngoai._don", lambda d: GN._don(Path(d) if d is not None
                                           else Path(""))),
    ("giong_vieneu._don", lambda d: GV._don(Path(d) if d is not None
                                            else Path(""))),
    ("piper_tts._don", lambda d: PT._don(Path(d) if d is not None
                                         else Path(""))),
    ("queue.jobs._don_thu_muc_tam", _goi_jobs),
    ("tempsweep._xoa", _goi_tempsweep),
)


# ═══════════════════════════════════════════════════════════════════════════
def ca1_ly_do_cam() -> None:
    print("\n--- CA 1: `xoa_an_toan.ly_do_cam` (hàm thuần, cửa chung) ---")
    for ten, v in dau_vao_that() + dau_vao_gian_diep():
        if "không tồn tại" in ten:
            continue          # không tồn tại là VÔ HẠI, không phải CẤM
        ly = XA.ly_do_cam(v)
        ok(f"1 · CẤM {ten}", bool(ly), ly[:90] or "KHÔNG CẤM (!)")

    # ── HỎI ĐÚNG LÝ DO, KHÔNG CHỈ HỎI "CÓ CẤM KHÔNG" ────────────────────────
    # Phép phá "gỡ chốt GỐC Ổ ĐĨA" ĐÃ ĐI LỌT ở lượt thử phá đầu tiên
    # (`_pha_xoa_nham.py` phép 6: BẮT 5 · LỌT 2). Lý do là hoàn cảnh chứ không
    # phải chốt: hộp cát nằm trong `%TEMP%` nên **`C:\` là thư mục CHA của
    # cwd**, còn **`D:\` là thư mục CHA của gốc cây mã** -> hai chốt KHÁC vẫn
    # bắt hộ, và cổng vẫn xanh dù chốt cần đo đã biến mất.
    # Bài học chung: **mục nào canh một chốt cụ thể thì phải đọc LÝ DO cụ thể**
    # — hỏi mỗi "có chặn không" là mục đó tự vô hiệu ngay khi có chốt thứ hai
    # tình cờ phủ lên. Cùng họ với bẫy "quét tĩnh chỉ hỏi có mặt không" (cổng
    # 56d) và "so bản mốc với chính nó" (cổng 36/51).
    for ten, v in (("gốc ổ C", "C:\\"), ("gốc ổ đĩa của repo", REPO.anchor)):
        ly = XA.ly_do_cam(v)
        ok(f"1 · {ten} chặn ĐÚNG bởi chốt GỐC Ổ ĐĨA",
           ly.startswith("GỐC Ổ ĐĨA"), ly[:90] or "KHÔNG CẤM (!)")
    for ten, v in ((' Path("")', Path("")), (' chuỗi "."', ".")):
        ly = XA.ly_do_cam(v)
        ok(f"1 ·{ten} chặn ĐÚNG bởi chốt THƯ MỤC ĐANG LÀM VIỆC",
           ly.startswith("THƯ MỤC ĐANG LÀM VIỆC"), ly[:90] or "KHÔNG CẤM (!)")
    ly_cha = XA.ly_do_cam("..")
    ok("1 · `..` chặn ĐÚNG bởi chốt THƯ MỤC CHA",
       ly_cha.startswith("thư mục CHA"), ly_cha[:90] or "KHÔNG CẤM (!)")

    tam = _tao(_SB / "hop_cat_hop_le")
    ok("1 · thư mục tạm hợp lệ KHÔNG bị cấm", XA.ly_do_cam(tam) == "",
       XA.ly_do_cam(tam) or "cho qua (đúng)")
    ok("1 · `an_toan_de_xoa(trong=)` chặn thứ NGOÀI gốc",
       not XA.an_toan_de_xoa(_SB / "ngoai", trong=_SB / "goc_khac"))
    _tao(_SB / "goc_khac" / "ben_trong")
    ok("1 · `an_toan_de_xoa(trong=)` cho qua thứ TRONG gốc",
       XA.an_toan_de_xoa(_SB / "goc_khac" / "ben_trong", trong=_SB / "goc_khac"))
    ok("1 · `trong=` CẤM xoá chính cái gốc",
       not XA.an_toan_de_xoa(_SB / "goc_khac", trong=_SB / "goc_khac"))


def ca2_don_thu_muc_that() -> None:
    print("\n--- CA 2: `don_thu_muc` xoá THẬT, mồi canary phải còn ---")
    for ten, v in dau_vao_that():
        XA.don_thu_muc(v)
        thieu = moi_con_du()
        ok(f"2 · {ten} -> mồi còn nguyên", not thieu,
           "MẤT MỒI: " + ",".join(thieu) if thieu else "3/3 mồi còn")
        ok(f"2 · {ten} -> cwd còn sống", Path.cwd().is_dir())

    that = _SB / "xoa_that_1"
    _tao(that / "sau")
    (that / "sau" / "a.txt").write_text("x", encoding="utf-8")
    da = XA.don_thu_muc(that)
    ok("2 · thư mục tạm HỢP LỆ vẫn xoá được (không chặn quá tay)",
       da and not that.exists(), f"trả {da} · còn tồn tại {that.exists()}")


def ca3_ham_san_xuat_that() -> None:
    print("\n--- CA 3: 6 hàm dọn SẢN XUẤT × 8 đầu vào, `rmtree` THẬT ---")
    for ten_ham, ham in HAM_DON:
        xau = []
        for ten_v, v in dau_vao_that():
            try:
                ham(v)
            except Exception as e:                       # noqa: BLE001
                xau.append(f"{ten_v}: NÉM {type(e).__name__}")
                continue
            thieu = moi_con_du()
            if thieu:
                xau.append(f"{ten_v}: MẤT {','.join(thieu)}")
                for m in MOI:                            # dựng lại để chấm tiếp
                    _tao(m.parent)
                    m.write_text("mồi dựng lại\n", encoding="utf-8")
        ok(f"3 · {ten_ham}: 8/8 đầu vào KHÔNG xoá gì + KHÔNG ném",
           not xau, "; ".join(xau)[:200] if xau else "mồi 3/3 còn, 0 lần ném")


def ca4_gian_diep() -> None:
    print("\n--- CA 4: gốc ổ đĩa / nhà / gốc cây mã (rmtree = GIÁN ĐIỆP) ---")
    that = shutil.rmtree
    # `tempsweep._co` ĐI QUÉT CẢ CÂY để đo dung lượng TRƯỚC khi xoá. Gián điệp
    # chỉ thay `rmtree`, nên `_xoa(Path("C:\\"))` sẽ `rglob("*")` **toàn bộ ổ
    # C (564 GB)** — lượt thử phá đầu tiên treo ở đúng chỗ này và phải giết
    # tay (đọc ra "mã thoát 4294967295, KHÔNG có dòng tổng kết"). Đây KHÔNG
    # phải mục cần đo của CA 4 (câu hỏi duy nhất là "có chạm `rmtree` không"),
    # nên vá `_co` về 0 trong đúng ca này.
    # Nhân tiện, đó cũng là lý do chốt `ly_do_cam` phải đứng TRƯỚC `_co` trong
    # `_xoa`: đặt sau thì một đường dẫn rác vẫn tốn một lượt quét cả ổ đĩa.
    co_that = TS._co
    TS._co = lambda p: 0                                 # type: ignore[assignment]
    for ten_ham, ham in HAM_DON:
        gd = GianDiep()
        shutil.rmtree = gd                               # type: ignore[assignment]
        try:
            for ten_v, v in dau_vao_gian_diep():
                try:
                    ham(v)
                except Exception:                        # noqa: BLE001
                    pass
        finally:
            shutil.rmtree = that                         # type: ignore[assignment]
        ok(f"4 · {ten_ham}: 0 lần chạm `rmtree`", not gd.goi,
           ("ĐÃ ĐỊNH XOÁ: " + " | ".join(gd.goi)[:180]) if gd.goi
           else "gián điệp không ghi được lần nào")

    # Chốt chống-con-dấu: gián điệp PHẢI bắt được khi thật sự có lượt xoá.
    gd = GianDiep()
    shutil.rmtree = gd                                   # type: ignore[assignment]
    try:
        shutil.rmtree(_SB / "bat_ky")
    finally:
        shutil.rmtree = that                             # type: ignore[assignment]
    ok("4 · TỰ KIỂM gián điệp: có gọi thì phải ghi sổ", len(gd.goi) == 1)
    TS._co = co_that                                     # type: ignore[assignment]


def ca5_delete_project() -> None:
    print("\n--- CA 5: `services.delete_project` (đường NGƯỜI DÙNG BẤM) ---")

    class _DbGia:
        def __init__(self) -> None:
            self.duong = ""

        def query_one(self, sql, args=None):
            return {"assets_dir": self.duong}

        def execute(self, sql, args=None):
            return None

        def query(self, *a, **k):
            return []

    db_that, huy_that = SV.db, SV._cancel_jobs
    dbg = _DbGia()
    SV.db = dbg                                          # type: ignore[assignment]
    SV._cancel_jobs = lambda *a, **k: None               # type: ignore[assignment]
    try:
        for ten_v, v in dau_vao_that():
            if v is None:
                continue          # cột TEXT NOT NULL, DB không trả None
            dbg.duong = v
            try:
                SV.delete_project(1)
            except Exception as e:                       # noqa: BLE001
                ok(f"5 · assets_dir={ten_v} -> không ném", False,
                   f"NÉM {type(e).__name__}: {e}")
                continue
            thieu = moi_con_du()
            ok(f"5 · assets_dir={ten_v} -> mồi còn nguyên", not thieu,
               "MẤT MỒI: " + ",".join(thieu) if thieu else "3/3 mồi còn")

        gd = GianDiep()
        that = shutil.rmtree
        shutil.rmtree = gd                               # type: ignore[assignment]
        try:
            for ten_v, v in dau_vao_gian_diep():
                dbg.duong = v
                try:
                    SV.delete_project(1)
                except Exception:                        # noqa: BLE001
                    pass
        finally:
            shutil.rmtree = that                         # type: ignore[assignment]
        ok("5 · gốc ổ đĩa/nhà/gốc mã -> 0 lần chạm `rmtree`", not gd.goi,
           ("ĐÃ ĐỊNH XOÁ: " + " | ".join(gd.goi)[:180]) if gd.goi else "sạch")

        kenh = _SB / "kenh_that"
        _tao(kenh / "assets")
        dbg.duong = str(kenh)
        SV.delete_project(1)
        ok("5 · thư mục kênh THẬT vẫn xoá được (không chặn quá tay)",
           not kenh.exists(), f"còn tồn tại: {kenh.exists()}")
    finally:
        SV.db, SV._cancel_jobs = db_that, huy_that


def ca6_quet_tinh() -> None:
    print("\n--- CA 6: QUÉT TĨNH — không được có `rmtree` MỚI ngoài sổ ---")
    # Danh sách ĐÃ RÀ 19/08/2026. Thêm chỗ gọi `rmtree` mới mà không ghi vào
    # đây thì cổng ĐỎ — cố ý: đó là lúc phải có người đọc lại đường dẫn.
    SO_DA_RA = {
        "app/core/xoa_an_toan.py": "CỬA CHUNG — chính nó là chốt",
        "app/core/giong_ngoai.py": "_don có chốt riêng (b5bd003) + trong=",
        "app/core/giong_vieneu.py": "_don có chốt riêng (b5bd003) + trong=",
        "app/core/tempsweep.py": "_xoa đã gọi ly_do_cam (39e92c6)",
        "app/core/transcribe.py": "đường dẫn từ tempfile.mkdtemp",
        "app/core/hieu_ung.py": "đường dẫn từ tempfile.mkdtemp",
        "app/core/hieu_ung_gpu.py": "đường dẫn từ tempfile.mkdtemp",
        "app/core/self_update.py": "hằng số UPDATES_DIR / _internal.old",
        "app/core/ytdlp_potoken.py": "hằng số _POTOKEN_DIR",
    }
    la = []
    for f in sorted((REPO / "app").rglob("*.py")):
        try:
            ma = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            cay = ast.parse(ma)
        except SyntaxError:
            continue
        # Đọc bằng AST, KHÔNG bằng `in` chuỗi: chính DÒNG GHI CHÚ giải thích
        # bản vá có chữ `shutil.rmtree` -> quét bằng chuỗi là ĐỎ OAN vĩnh viễn
        # (bài học cổng 47 · 51 · 53 · 73).
        co = False
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            h = nut.func
            if (isinstance(h, ast.Attribute) and h.attr == "rmtree"
                    and isinstance(h.value, ast.Name) and h.value.id == "shutil"):
                co = True
                break
        if co:
            key = f.relative_to(REPO).as_posix()
            if key not in SO_DA_RA:
                la.append(key)
    ok("6 · không có file `app/` nào gọi `shutil.rmtree` ngoài sổ đã rà",
       not la, ("CHƯA RÀ: " + ", ".join(la)) if la
       else f"{len(SO_DA_RA)} file trong sổ, 0 file lạ")

    # 3 cửa đã vá phải THẬT SỰ hết `shutil.rmtree` (đi qua cửa chung).
    for f in ("app/services.py", "app/queue/jobs.py", "app/core/piper_tts.py"):
        ma = (REPO / f).read_text(encoding="utf-8")
        cay = ast.parse(ma)
        con = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "rmtree"
                  and isinstance(n.func.value, ast.Name)
                  and n.func.value.id == "shutil"
                  for n in ast.walk(cay))
        goi_cua = "don_thu_muc" in ma
        ok(f"6 · {f}: hết `shutil.rmtree` trần + đi qua cửa chung",
           (not con) and goi_cua,
           f"còn rmtree={con} · gọi don_thu_muc={goi_cua}")

    # `thay_giong.doc_thu` đi qua cửa chung.
    ma_tg = (REPO / "app/core/thay_giong.py").read_text(encoding="utf-8")
    ok("6 · thay_giong.py dùng cửa chung `don_thu_muc`",
       "don_thu_muc" in ma_tg and "xoa_an_toan" in ma_tg)
    ok("6 · module cửa chung có mặt trong `app/core`",
       (REPO / "app/core/xoa_an_toan.py").is_file())


def ca7_tu_kiem_bo_do() -> None:
    print("\n--- CA 7: TỰ KIỂM BỘ DÒ — dựng lại mã CŨ, bộ dò phải KÊU ---")

    def _don_cu(d) -> None:
        """ĐÚNG mã trước `b5bd003`. KHÔNG được gọi với `rmtree` thật ngoài
        hộp cát dùng-một-lần bên dưới."""
        try:
            if d and str(d) and Path(d).is_dir():
                shutil.rmtree(d, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass

    # 7a — với GIÁN ĐIỆP: mã cũ PHẢI chạm `rmtree` ở `.` và `Path("")`.
    that = shutil.rmtree
    gd = GianDiep()
    shutil.rmtree = gd                                   # type: ignore[assignment]
    try:
        for _t, v in dau_vao_that():
            _don_cu(v)
    finally:
        shutil.rmtree = that                             # type: ignore[assignment]
    ok("7a · mã CŨ chạm `rmtree` với bộ đầu vào của cổng", len(gd.goi) >= 2,
       f"{len(gd.goi)} lần: " + " | ".join(gd.goi)[:120])

    # 7b — xoá THẬT trong hộp cát dùng-một-lần: mồi PHẢI biến mất. Không có
    # mục này thì cả cơ chế canary chỉ là niềm tin.
    pha = _SB / "hop_cat_pha"
    _tao(pha / "ben_trong")
    moi_pha = [pha / "MOI_A.txt", pha / "ben_trong" / "MOI_B.txt"]
    for m in moi_pha:
        m.write_text("mồi của ca phá\n", encoding="utf-8")
    cu = os.getcwd()
    os.chdir(pha)
    try:
        _don_cu(Path(""))                                # <- rmtree THẬT
    finally:
        os.chdir(cu)
    con_lai = [m.name for m in moi_pha if m.exists()]
    ok("7b · mã CŨ xoá THẬT sạch mồi (bộ dò canary có răng)", not con_lai,
       f"còn sót: {con_lai}" if con_lai else "2/2 mồi đã bị xoá đúng như dự đoán")

    # 7c — mã MỚI ở đúng chỗ đó thì mồi phải CÒN.
    moi2 = _tao(pha / "sau_nua")
    (moi2 / "MOI_C.txt").write_text("mồi 2\n", encoding="utf-8")
    os.chdir(moi2)
    try:
        XA.don_thu_muc(Path(""))
        XA.don_thu_muc(".")
        XA.don_thu_muc("")
    finally:
        os.chdir(cu)
    ok("7c · cùng chỗ đó, cửa chung MỚI giữ nguyên mồi",
       (moi2 / "MOI_C.txt").exists())

    ok("7d · mồi chính của cổng vẫn còn sau CA 7", not moi_con_du())


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    print("CỔNG 80 — KHÔNG XOÁ NHẦM THƯ MỤC ĐANG LÀM VIỆC")
    print(f"hộp cát : {_SB}")
    print(f"cwd     : {os.getcwd()}")
    print(f"repo    : {REPO}")
    print(f"rác lượt trước đã dọn: {_RAC_CU} thư mục")
    if Path(os.getcwd()).resolve() == REPO:
        print("DỪNG: cwd đang là REPO — cổng này xoá thật, không chạy ở đây.")
        return 2

    ca1_ly_do_cam()
    ca2_don_thu_muc_that()
    ca3_ham_san_xuat_that()
    ca4_gian_diep()
    ca5_delete_project()
    ca6_quet_tinh()
    ca7_tu_kiem_bo_do()

    print("\n" + "=" * 62)
    print(f"TỔNG KẾT CỔNG 80: ĐẠT {DAT} · HỎNG {HONG}")
    if _HONG_TEN:
        for t in _HONG_TEN:
            print("   HỎNG:", t)
    print("=" * 62)
    return 1 if HONG else 0


if __name__ == "__main__":
    ma = 3
    try:
        ma = main()
    finally:
        os.chdir(_CWD_CU)
        # Dọn hộp cát của CHÍNH cổng — không để rác trên máy anh Hùng.
        # Dùng `shutil.rmtree` gốc, có kiểm: hộp cát luôn nằm trong %TEMP%.
        try:
            if _SB.is_dir() and _SB.parent == Path(
                    tempfile.gettempdir()).resolve():
                shutil.rmtree(_SB, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
    sys.exit(ma)
