# -*- coding: utf-8 -*-
"""CỔNG 62 — Ô "QUÉT CẢ KHUNG" TRONG GIAO DIỆN, NỐI ĐỦ XUỐNG ĐƯỜNG XUẤT.

VÌ SAO CÓ CỔNG NÀY (15/08/2026, việc 2):
Đường dò chữ TOÀN KHUNG đã viết xong từ trước nhưng tới nay **chỉ bật được
bằng biến môi trường `BQ_CHE_TOAN_KHUNG=1`** — tức anh Hùng không có cách nào
bật. Nay thành ô tích trong hộp Chỉnh mẫu.

**MẶC ĐỊNH TẮT, và đó là quyết định theo SỐ ĐO chứ không phải cẩn thận thừa:**
  · bỏ sót 33,3% -> 0%                (được)
  · che oan     0 -> 2 ca             (mất)
  · video quay CAMERA CỐ ĐỊNH HỎNG NẶNG: `jp_tuyet` ra 4 vùng thì 2 sai, bôi
    gần hết khung — nền không trôi nên mẹo "giao nhau theo thời gian" (thứ lọc
    vùng giả của cả đường này) mất tác dụng.
  · video dọc chậm thêm 3,38 giây mỗi phút phim.

BA MỆNH ĐỀ CỔNG NÀY CANH:
  1. Ô có thật, MẶC ĐỊNH TẮT, nhãn tiếng Việt KHÔNG EMOJI, chú thích NÓI
     THẲNG đánh đổi (kể cả lời cảnh báo camera cố định).
  2. Round-trip lưu/đọc lại mẫu KHÔNG mất cờ.
  3. **BẤT BIẾN TIỀN**: cờ TẮT -> `dedup_key` giống TỪNG KÝ TỰ bản trước khi
     có cờ. Thêm phần tử vào tuple `extra` là 200-300 kênh xuất lại từ đầu
     (đúng bài học `ovl_spec` cổng 42 và `che_chu` cổng 56e).

  .venv\\Scripts\\python -u _test_toan_khung.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = Path(tempfile.gettempdir()) / f"bq_tk_{os.getpid()}"
SAN.mkdir(parents=True, exist_ok=True)
os.environ["BQ_DB_PATH"] = str(SAN / "t.db")
os.environ["BQ_DATA_DIR"] = str(SAN)

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _test_guard  # noqa: F401,E402  (luật: mọi cổng dựng UI phải import)

DAT = HONG = 0


def kiem(ten: str, dieu_kien: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu_kien:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


#: Dải emoji hay thiếu glyph trên máy anh Hùng (bài học v2.6.22 "ô đen").
def co_emoji(s: str) -> bool:
    return any(ord(c) > 0x2100 for c in s)


def main() -> int:
    print("=" * 70)
    print("CỔNG 62 — Ô 'QUÉT CẢ KHUNG' + NỐI XUỐNG ĐƯỜNG XUẤT")
    print("=" * 70)

    # ═══════════ CA 1 — LÕI: ba trạng thái của `loc_cho_xuat` ═══════════
    print("\nCA 1 — `che_chu.loc_cho_xuat(toan_khung=...)` BA trạng thái")
    import ast
    import inspect
    from app.core import che_chu as CC

    sig = inspect.signature(CC.loc_cho_xuat)
    kiem("1a có tham số `toan_khung`", "toan_khung" in sig.parameters)
    kiem("1b mặc định là `None` (KHÔNG phải False)",
         sig.parameters["toan_khung"].default is None,
         f"{sig.parameters['toan_khung'].default!r}")
    # `None` phải theo env, True/False phải THẮNG env — quét AST cho chắc
    than = Path(CC.__file__).read_text(encoding="utf-8")
    kiem("1c `None` -> theo env `_BAT_TOAN_KHUNG`",
         "_BAT_TOAN_KHUNG if toan_khung is None else bool(toan_khung)" in than)

    # ═══════════ CA 2 — nối đủ chặng (quét AST, không quét chuỗi) ═══════════
    # Bài học cổng 56d: quét bằng chuỗi thì phép phá `che_chu_toan_khung=False`
    # (hằng số) vẫn giữ nguyên mặt chữ và LỌT. Phải đọc bằng AST và đòi giá trị
    # truyền vào là BIỂU THỨC, không được là hằng số.
    print("\nCA 2 — nối đủ chặng UI -> services -> m1 -> ffmpeg -> che_chu")

    def goi_kw(duong: Path, ten_ham: str, kw: str):
        """Trả node giá trị của keyword `kw` ở lời gọi `ten_ham` (hoặc None)."""
        cay = ast.parse(duong.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            ten = (f.attr if isinstance(f, ast.Attribute)
                   else getattr(f, "id", ""))
            if ten != ten_ham:
                continue
            for k in n.keywords:
                if k.arg == kw:
                    return k.value
        return None

    import app.services as SV
    import app.modules.m1_highlight as M1
    import app.core.ffmpeg_utils as FU
    import app.ui.studio_page as SP

    kiem("2a `services.enqueue_export` nhận `che_chu_toan_khung`",
         "che_chu_toan_khung" in inspect.signature(SV.enqueue_export).parameters)
    kiem("2b `export_canvas_clip` nhận `che_chu_toan_khung`",
         "che_chu_toan_khung" in
         inspect.signature(FU.export_canvas_clip).parameters)

    def doc_duoc_co(v) -> bool:
        """Giá trị truyền vào có THẬT SỰ đọc cờ ra không.

        "KHÔNG phải `ast.Constant`" là chốt QUÁ YẾU — thử phá đổi thành
        `False if True` (một `ast.IfExp`, hằng số trá hình) và cổng VẪN XANH.
        Đòi thêm: chuỗi mã của biểu thức phải NHẮC TỚI `toan_khung`, tức nó
        đi lấy giá trị từ mẫu/payload chứ không phải bịa ra tại chỗ.
        """
        if v is None or isinstance(v, ast.Constant):
            return False
        return "toan_khung" in ast.unparse(v)

    v = goi_kw(Path(SP.__file__), "enqueue_export", "che_chu_toan_khung")
    kiem("2c `studio_page` TRUYỀN cờ vào `enqueue_export`", v is not None)

    # QUÉT TĨNH BAO NHIÊU CŨNG CÓ ĐƯỜNG VÒNG — đã đo: `False if True else
    # <biểu thức đọc mẫu>` vượt được CẢ chốt "không phải hằng số" LẪN chốt
    # "chuỗi mã có nhắc toan_khung" (nhánh `else` chết vẫn nằm trong chuỗi).
    # Nên ở đây ĐÁNH GIÁ THẬT biểu thức lấy từ MÃ NGUỒN với 3 mẫu đầu vào và
    # đòi ra ĐÚNG 3 kết quả — đó mới là mệnh đề cần canh.
    class _SelfGia:
        def __init__(self, tpl):
            self.layout_tpl = tpl

    def _chay_bt(tpl):
        return eval(compile(ast.Expression(v), "<sp>", "eval"),  # noqa: S307
                    {}, {"self": _SelfGia(tpl)})

    try:
        r_khong, r_bat, r_tat = _chay_bt({}), _chay_bt(
            {"che_chu_toan_khung": True}), _chay_bt(
            {"che_chu_toan_khung": False})
        ok2d = (r_khong is None and r_bat is True and r_tat is False)
        ct2d = f"mẫu trống->{r_khong!r} · True->{r_bat!r} · False->{r_tat!r}"
    except Exception as _e:                                    # noqa: BLE001
        # Không đánh giá được thì NÓI THẲNG là không đo được, đừng cho qua:
        # phép đo hỏng nguy hiểm hơn không đo.
        ok2d, ct2d = False, f"KHÔNG đánh giá được biểu thức ({_e})"
    kiem("2d ... và biểu thức đó ra ĐÚNG 3 trạng thái khi CHẠY THẬT",
         ok2d, ct2d)

    v2 = goi_kw(Path(M1.__file__), "export_canvas_clip", "che_chu_toan_khung")
    kiem("2e `m1` TRUYỀN cờ vào `export_canvas_clip`", v2 is not None)
    kiem("2f ... và biểu thức đó ĐỌC cờ ra",
         doc_duoc_co(v2),
         ast.unparse(v2)[:60] if v2 is not None else "(không có)")

    v3 = goi_kw(Path(FU.__file__), "loc_cho_xuat", "toan_khung")
    kiem("2g `ffmpeg_utils` TRUYỀN cờ vào `loc_cho_xuat`", v3 is not None)
    kiem("2h ... và biểu thức đó ĐỌC cờ ra",
         doc_duoc_co(v3),
         ast.unparse(v3)[:60] if v3 is not None else "(không có)")

    # ═══════════ CA 3 — `doc_che_chu` giữ ba trạng thái ═══════════
    print("\nCA 3 — `m1.doc_che_chu` giữ NGUYÊN `None` khi không ai chốt")
    r0 = M1.doc_che_chu({"che_chu": True})
    kiem("3a payload không có khoá -> `toan_khung` là None",
         r0.get("toan_khung") is None, f"{r0.get('toan_khung')!r}")
    r1 = M1.doc_che_chu({"che_chu": True, "che_chu_toan_khung": True})
    kiem("3b payload True  -> True", r1.get("toan_khung") is True)
    r2 = M1.doc_che_chu({"che_chu": True, "che_chu_toan_khung": False})
    kiem("3c payload False -> False (KHÔNG rơi về None)",
         r2.get("toan_khung") is False, f"{r2.get('toan_khung')!r}")

    # ═══════════ CA 4 — BẤT BIẾN TIỀN: sig KHÔNG đổi khi cờ TẮT ═══════════
    # Đây là mục đắt nhất nếu sai: đổi hash lúc TẮT = 200-300 kênh xuất lại.
    print("\nCA 4 — BẤT BIẾN: cờ TẮT thì `sig` giống TỪNG KÝ TỰ bản mốc")
    from app.database import db as DB
    DB.init_schema()
    # Cột `assets_dir` là NOT NULL và `videos` dùng `src_path` (không phải
    # `path`) — dựng DB bằng tên cột BỊA thì `sqlite3.IntegrityError` giết
    # lượt chạy NGAY TẠI ĐÂY và CA 5/CA 6 không bao giờ chạy. Đúng bẫy "cổng
    # 55 CA4 ĐẠT OAN vì lượt chạy chết trước khi tới chốt": phải dùng đúng
    # `schema.sql`, và `enqueue_export` còn BĂM CẢ mốc cắt start/end nên clip
    # phải có thật trong DB chứ không chỉ có id.
    _PID = DB.insert("INSERT INTO projects (name, assets_dir) VALUES (?,?)",
                     ("_tk_kenh", str(SAN / "_tk_kenh")))
    _VID = DB.insert(
        "INSERT INTO videos (project_id, src_path, duration) VALUES (?,?,?)",
        (_PID, r"D:\khong-co-that\v.mp4", 120.0))
    _CID = DB.insert(
        "INSERT INTO clips (video_id, start_sec, end_sec, status) "
        "VALUES (?,?,?,?)", (_VID, 12.0, 48.5, "suggested"))

    ghi: list = []

    class _PoolGhi:
        """Không đụng `worker.pool` thật: cổng chỉ cần đọc `dedup_key`."""

        def enqueue(self, kind, payload, **kw):
            ghi.append(kw.get("dedup_key", ""))
            return 1

    def _xep(**kw) -> None:
        SV.enqueue_export(_PoolGhi(), _CID, _VID, _PID, out_w=1080,
                          out_h=1920, part_no=1, **kw)

    _xep()                                                       # (a) cũ
    _xep(che_chu=False)                                          # (b) tắt
    _xep(che_chu=False, che_chu_toan_khung=False)                 # (c) tắt
    _xep(che_chu=True)                                           # (d) bật
    _xep(che_chu=True, che_chu_toan_khung=True)                   # (e) +TK
    a, b, c, d, e = ghi[:5]
    kiem("4a chưa nối cờ == che_chu TẮT (sig KHÔNG đổi)", a == b)
    kiem("4b `toan_khung=False` KHÔNG đổi sig", b == c)
    kiem("4c bật che_chu -> sig ĐỔI", d != b, f"...{d[-24:]}")
    kiem("4d bật thêm QUÉT CẢ KHUNG -> sig ĐỔI NỮA", e != d,
         f"...{e[-24:]}")
    kiem("4e cờ TK nối vào ĐUÔI sig (không chen giữa)", e.endswith("tk"))

    # ═══════════ CA 5 — Ô TÍCH TRONG GIAO DIỆN ═══════════
    print("\nCA 5 — ô tích trong hộp Chỉnh mẫu")
    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance() or QApplication(sys.argv)
    from app.ui import theme
    qapp.setStyleSheet(theme.QSS)          # luật cổng 9: PHẢI áp QSS thật
    from app.ui.editor import EditorDialog

    khung = SAN / "f.png"
    from PyQt6.QtGui import QImage
    QImage(64, 114, QImage.Format.Format_RGB32).save(str(khung))

    d = EditorDialog(str(khung), {}, None)
    kiem("5a có ô `che_chu_tk`", hasattr(d, "che_chu_tk"))
    if hasattr(d, "che_chu_tk"):
        nhan = d.che_chu_tk.text()
        kiem("5b MẶC ĐỊNH TẮT", not d.che_chu_tk.isChecked())
        kiem("5c nhãn KHÔNG EMOJI", not co_emoji(nhan), nhan)
        kiem("5d nhãn tiếng Việt", "khung" in nhan.lower(), nhan)
        tip = d.che_chu_tk.toolTip()
        # chú thích phải NÓI THẲNG cả 3 mặt của đánh đổi
        kiem("5e chú thích nói CHẬM HƠN", "3,38" in tip or "chậm" in tip.lower())
        kiem("5f chú thích nói CHE NHẦM",
             "nhầm" in tip.lower() or "oan" in tip.lower())
        kiem("5g chú thích CẢNH BÁO camera cố định",
             "cố định" in tip.lower())
        kiem("5h chú thích KHÔNG EMOJI", not co_emoji(tip))
        # ô con phải theo ô CHA (che_chu tắt -> mờ hết)
        d.che_chu_chk.setChecked(False)
        d._che_chu_ui()
        kiem("5i che_chu TẮT -> ô quét-cả-khung bị khoá",
             not d.che_chu_tk.isEnabled())
        d.che_chu_chk.setChecked(True)
        d._che_chu_ui()
        kiem("5j che_chu BẬT -> ô quét-cả-khung mở", d.che_chu_tk.isEnabled())

    # ═══════════ CA 6 — ROUND-TRIP lưu/đọc lại ═══════════
    print("\nCA 6 — round-trip: lưu mẫu rồi đọc lại KHÔNG mất cờ")
    d.che_chu_chk.setChecked(True)
    d.che_chu_tk.setChecked(True)
    lay = d._collect() if hasattr(d, "_collect") else None
    if lay is None:                     # tên hàm gom khác -> tìm bằng khoá
        for ten in dir(d):
            if ten.startswith("_") and "collect" in ten:
                lay = getattr(d, ten)()
                break
    kiem("6a gom được layout", isinstance(lay, dict))
    if isinstance(lay, dict):
        kiem("6b layout mang khoá `che_chu_toan_khung`",
             lay.get("che_chu_toan_khung") is True,
             f"{lay.get('che_chu_toan_khung')!r}")
        d2 = EditorDialog(str(khung), dict(lay), None)
        kiem("6c mở lại mẫu -> ô VẪN TÍCH", d2.che_chu_tk.isChecked())
        d2.deleteLater()
        # mẫu CŨ (không có khoá) -> phải TẮT, không được tự bật
        d3 = EditorDialog(str(khung), {"che_chu": True}, None)
        kiem("6d mẫu CŨ chưa có khoá -> TẮT", not d3.che_chu_tk.isChecked())
        d3.deleteLater()
    d.deleteLater()

    print("\n" + "=" * 70)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 70)
    return 1 if HONG else 0


if __name__ == "__main__":
    try:
        ma = main()
    finally:
        shutil.rmtree(SAN, ignore_errors=True)
    raise SystemExit(ma)
