# -*- coding: utf-8 -*-
"""CỔNG 88 — GIỌNG CỦA ANH HÙNG (nhân bản từ mẫu) ĐÃ NỐI VÀO APP.

Anh Hùng: *"ném giọng đọc của tôi khoảng mấy giây Reference Audio, sau đó dán
bao nhiêu ký tự dùng giọng đó cũng được... đảm bảo giọng đó lưu được với thêm
được nhiều giọng... không lấy của bất kỳ ai nữa, tự động lấy của mình luôn"*.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CỔNG NÀY TỒN TẠI: CA THỨ NĂM CỦA "HÀM XONG ≠ TÍNH NĂNG XONG"
═══════════════════════════════════════════════════════════════════════════
`app/core/nhan_ban_giong.py` dựng xong **564 dòng** (kiểm mẫu · sổ ra đĩa ·
chép mẫu vào `DATA_DIR` · xoá/đổi tên · nhãn) và cổng 81 chấm nó XANH — nhưng
**không một dòng nào trong `app/ui/` gọi tới**. Đo trước khi vá:
`grep -rn "nhan_ban_giong" app/ui/` -> **0 dòng**. Tức với người không đọc mã
thì tính năng KHÔNG TỒN TẠI. Cùng bệnh `giong_bang` · `giong_chatter` ·
`giong_vbee` · `giong_kokoro`. **Cổng 81 canh HÀM; cổng này canh CÁI ANH HÙNG
BẤM** — thiếu nó thì lần "dọn gọn" sau có thể gỡ nút mà mọi cổng vẫn xanh.

═══════════════════════════════════════════════════════════════════════════
MỆNH ĐỀ TRUNG TÂM: MÃ GIỌNG PHẢI ĐI QUA **CẢ HAI** CỬA ĐỌC
═══════════════════════════════════════════════════════════════════════════
Sót MỘT cửa là video ra **HAI GIỌNG TRỘN** mà `rc` vẫn 0, không một dòng báo.
Bẫy này đã cắn **4 lần** (`ov:nu_am` · `vn:` · `cb:` · `kk:`). Nên CA 2 kiểm
bằng **AST + GỌI THẬT**, không đọc mắt.

**VÀ ĐÂY LÀ LÝ DO KHÔNG ĐẺ TIỀN TỐ `toi:`** — mô tả việc gợi ý tiền tố mới,
nhưng đo ra thì đó là bẫy: `giong_bang.nguon("toi:x")` trả **`'edge'`**, tức
một tiền tố chưa đăng ký bị coi là edge-tts. Mã giọng ở đây giữ **tiền tố
NGUYÊN BẢN của máy** (`vnb:`), thứ đã đăng ký đủ ở `giong_bang._TIEN_TO` và
cả hai cửa `dubbing`. Cổng 81 CA 7h canh đúng quyết định đó; CA 2c dưới đây
canh mặt còn lại (tiền tố lạ KHÔNG được nhận diện thành edge).

Chạy: .venv\\Scripts\\python -u _test_giong_toi.py
"""
from __future__ import annotations

import ast
import asyncio
import json
import math
import os
import shutil
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: Hộp cát NGOÀI %TEMP%: cổng 55 đã sập vì thùng rác nằm trong %TEMP% rồi
#: `_is_safe_recycle_root` từ chối (ĐÚNG) làm mục MD5 hỏng oan. Ở đây còn một
#: lý do nữa: CA 6 đặt mồi canary rồi hỏi "guard có từ chối xoá không", mà
#: `%TEMP%` chính là một trong các thư mục `xoa_an_toan` cấm — đặt hộp cát vào
#: đó là hai chốt KHÁC nhau bắt hộ, mục sẽ ĐẠT vì lý do SAI (bài học cổng 80
#: LỌT 6: "mục nào canh MỘT chốt cụ thể thì phải đọc LÝ DO cụ thể").
T = REPO / f"bq_test_giong_toi_{os.getpid()}"
if T.exists():
    shutil.rmtree(T, ignore_errors=True)
T.mkdir(parents=True, exist_ok=True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")   # KHÔNG chạm registry
os.environ["BQ_FFMPEG_SLOTS"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát

# ---------------------------------------------------------------------------
# CỔNG KHÔNG ĐƯỢC PHÁT TIẾNG RA LOA — vá TRƯỚC khi dựng hộp (luật cổng 65).
# Vá thành hàm ĐẾM để còn chấm được "nút có thật sự gọi phát tiếng không";
# vá thành hàm rỗng thì mọi ca nghe thử tự ĐẠT vì lý do NGƯỢC HẲN.
# ---------------------------------------------------------------------------
_PHAT: list = []
try:
    import winsound

    def _gia_phat(*a, **k):
        _PHAT.append(a)
        return None

    winsound.PlaySound = _gia_phat            # type: ignore[assignment]
except Exception:                                              # noqa: BLE001
    winsound = None                            # type: ignore[assignment]

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication, QFileDialog, QMessageBox, QPushButton,
)

from app.core import dubbing as DUB           # noqa: E402
from app.core import giong_bang as GB         # noqa: E402
from app.core import giong_vieneu as VN       # noqa: E402
from app.core import nhan_ban_giong as NB     # noqa: E402
from app.core import xoa_an_toan as XA        # noqa: E402

_DAT = 0
_HONG: list[str] = []
_BOQUA: list[str] = []


def ok(ten: str, dieu: bool, ghi: str = "") -> None:
    global _DAT
    if dieu:
        _DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ghi}" if ghi else ""))
    else:
        _HONG.append(f"{ten}" + (f" [{ghi}]" if ghi else ""))
        print(f"  HỎNG {ten}" + (f" — {ghi}" if ghi else ""))


def bo_qua(ten: str, ly_do: str) -> None:
    _BOQUA.append(f"{ten} ({ly_do})")
    print(f"  BỎ QUA {ten} — {ly_do}")


def _ma_that(p: Path) -> str:
    """Mã NGUỒN đã BỎ ghi chú + chuỗi.

    Quét tĩnh bằng `in` trên cả file là tự bắn vào chân: chính DÒNG GHI CHÚ
    giải thích bản vá cũng chứa cụm đang tìm -> **ĐỎ OAN**. Bài học này đã lặp
    ở cổng 47 · 51 · 53 · 54 · 73 · 80 · 85 và **lần thứ sáu nó sập ngay trong
    mục viết ra để chống một bẫy khác** (cổng 86 mục 5i).
    """
    import io
    import tokenize
    ra: list[str] = []
    with open(p, "rb") as f:
        for t in tokenize.tokenize(io.BytesIO(f.read()).readline):
            if t.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(t.string)
    return " ".join(ra)


def _wav_gia(p: Path, giay: float = 8.0, hz: int = 220) -> bool:
    """Sinh WAV nói-được-coi-là-tiếng bằng ffmpeg. KHÔNG dùng file người thật.

    Phải là tiếng NGẮT NHỊP, không phải sóng sin liên tục: `kiem_mau` đòi
    `ty_le_tieng >= 0,45` đo bằng `silencedetect`, mà sóng liên tục thì 100%
    có tiếng — nghe qua thì tưởng đạt, nhưng nó KHÔNG đại diện cho mẫu thật.
    Ngắt nhịp cũng là điều `_do_de_giong` đã phải làm để bộ dò khỏi tự đạt oan.
    """
    import subprocess
    from config import settings as _st
    p.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [_st.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency={hz}:duration={giay}", "-af",
         "tremolo=f=2.2:d=0.9", "-ac", "1", "-ar", "24000", str(p)],
        capture_output=True, timeout=180,
        creationflags=(0x08000000 if os.name == "nt" else 0))
    return r.returncode == 0 and p.exists() and p.stat().st_size > 4000


# ===========================================================================
print("=" * 74)
print("CỔNG 88 — GIỌNG CỦA ANH HÙNG (nhân bản từ mẫu) ĐÃ NỐI VÀO APP")
print("=" * 74)

# ---------------------------------------------------------------------------
print("\n[CA 1] TÍNH NĂNG CÓ CỬA VÀO — không phải 564 dòng nằm chết")
# ---------------------------------------------------------------------------
ui_src = (REPO / "app" / "ui" / "thay_giong_dialog.py")
ma_ui = _ma_that(ui_src)
ok("1a `app/ui/` CÓ gọi `nhan_ban_giong` (đo trước khi vá: 0 dòng)",
   "nhan_ban_giong" in ma_ui)
ok("1b có lớp hộp `HopGiongToi`", "HopGiongToi" in ma_ui)
ok("1c có nút mở hộp (`_mo_giong_toi`)", "_mo_giong_toi" in ma_ui)

cay_ui = ast.parse(ui_src.read_text(encoding="utf-8"))
# `giong_dung_duoc` là hàm dựng DANH SÁCH giọng cho combo. Nó phải gọi
# `nhan_ban_giong.danh_sach()` — không gọi thì giọng đã lưu KHÔNG BAO GIỜ hiện
# ra ô Giọng đọc, tức lưu được mà không dùng được.
_goi_ds = False
for n in ast.walk(cay_ui):
    if isinstance(n, ast.FunctionDef) and n.name == "giong_dung_duoc":
        for c in ast.walk(n):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) \
                    and c.func.attr == "danh_sach":
                _goi_ds = True
ok("1d `giong_dung_duoc` gọi `nhan_ban_giong.danh_sach()` (quét AST, "
   "không đọc mắt)", _goi_ds)

# TỰ KIỂM BỘ DÒ: bộ dò trên phải BẮT được bản KHÔNG có lời gọi. Thiếu mục này
# thì "1d ĐẠT" có thể là bộ dò đã chết.
_gia = ast.parse("def giong_dung_duoc(ds):\n    return ds\n")
_bat = False
for n in ast.walk(_gia):
    if isinstance(n, ast.FunctionDef) and n.name == "giong_dung_duoc":
        for c in ast.walk(n):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) \
                    and c.func.attr == "danh_sach":
                _bat = True
ok("1d' TỰ KIỂM BỘ DÒ: bản KHÔNG gọi `danh_sach` thì bộ dò phải TRƯỢT",
   not _bat)

# ---------------------------------------------------------------------------
print("\n[CA 2] CẢ HAI CỬA ĐỌC PHẢI NHẬN MÃ GIỌNG — sót 1 cửa = HAI GIỌNG TRỘN")
# ---------------------------------------------------------------------------
cay_dub = ast.parse((REPO / "app" / "core" / "dubbing.py")
                    .read_text(encoding="utf-8"))
for cua in ("_synth_all", "_synth_all_words"):
    thay = False
    for n in ast.walk(cay_dub):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == cua:
            goi = {c.func.id for c in ast.walk(n)
                   if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            thay = "_vieneu_hay_khong" in goi
    ok(f"2a cửa `{cua}` gọi `_vieneu_hay_khong` (AST)", thay)

# GỌI THẬT — quét AST chỉ chứng minh có LỜI GỌI, không chứng minh nó RẼ ĐÚNG.
_goi_vn: list[str] = []
_that_dl = VN.doc_loat


def _bat_dl(texts, paths, voice, **kw):
    _goi_vn.append(voice)
    return [False] * len(texts), [[] for _ in texts]


VN.doc_loat = _bat_dl                          # type: ignore[assignment]
try:
    MA_THU = VN.ma_nhan_ban(str(T / "khong_co.wav"))
    asyncio.run(DUB._synth_all(["xin chào"], MA_THU, [str(T / "a.mp3")],
                               lang="vi"))
    _a = list(_goi_vn)
    _goi_vn.clear()
    asyncio.run(DUB._synth_all_words(["xin chào"], MA_THU,
                                     [str(T / "b.mp3")], lang="vi"))
    _b = list(_goi_vn)
finally:
    VN.doc_loat = _that_dl                     # type: ignore[assignment]
ok("2b GỌI THẬT: `_synth_all` rẽ vào giọng nhân bản", _a == [MA_THU],
   f"gọi {_a}")
ok("2b GỌI THẬT: `_synth_all_words` rẽ vào giọng nhân bản", _b == [MA_THU],
   f"gọi {_b}")

# Mặt còn lại của quyết định "không đẻ tiền tố thứ ba".
ok("2c `vnb:` được `giong_bang` nhận là VieNeu (không rơi vào edge)",
   GB.nguon("vnb:D:/mau.wav") == GB.VIENEU, GB.nguon("vnb:D:/mau.wav"))
ok("2c' tiền tố LẠ (`toi:`) bị nhận thành edge -> ĐÚNG LÝ DO không đẻ thêm "
   "tiền tố", GB.nguon("toi:abc") == GB.EDGE, GB.nguon("toi:abc"))
ok("2d `vnb:` KHÔNG bị `vn:` nuốt (tiền tố dài phải thử trước)",
   VN.la_giong_nhan_ban("vnb:x.wav") and not VN.la_giong_dung_san("vnb:x.wav"))

# ---------------------------------------------------------------------------
print("\n[CA 3] SỔ GIỌNG — thiếu khoá KHÔNG NỔ, hỏng thì SAO LƯU trước ghi đè")
# ---------------------------------------------------------------------------
so_p = NB.duong_so()
so_p.parent.mkdir(parents=True, exist_ok=True)
so_p.write_text('{"Giọng cũ": {"mau":"x.wav"  <<< RÁC KHÔNG PARSE ĐƯỢC',
                encoding="utf-8")
ok("3a sổ HỎNG -> `_doc_so()` trả rỗng, KHÔNG nổ", NB._doc_so() == {})
NB._ghi_so({"moi": {"mau": "y.wav"}})
_bk = sorted(so_p.parent.glob("giong_nhan_ban.hong-*.json"))
ok("3b ghi đè sổ hỏng thì SAO LƯU bản cũ trước (không im lặng mất sổ)",
   len(_bk) == 1, f"{len(_bk)} bản sao")
ok("3b' bản sao còn NGUYÊN VĂN nội dung cũ",
   bool(_bk) and "RÁC" in _bk[0].read_text(encoding="utf-8"))

so_p.write_text(json.dumps({
    "thieu_het": {},
    "mau_rong": {"mau": "", "may": "vieneu"},
    "giay_rac": {"mau": "a.wav", "giay": "4,5"},     # dấu phẩy tiếng Việt
    "muc_la": "tôi là chuỗi chứ không phải dict",
    "muc_none": None,
}, ensure_ascii=False), encoding="utf-8")
_no = ""
try:
    NB.danh_sach()
    NB.sua_mau_mat()
    for _t in ("thieu_het", "giay_rac", "muc_la", "muc_none", "khong_co"):
        NB.nhan(_t)
        NB.ma_giong(_t)
except Exception as e:                                         # noqa: BLE001
    _no = f"{type(e).__name__}: {e}"
ok("3c sổ THIẾU KHOÁ / mục lạ (chuỗi/None/số rác) -> KHÔNG hàm nào nổ",
   not _no, _no)
ok("3d mục thiếu khoá `mau` phải bị kể là MẤT MẪU "
   "(`Path(\"\").exists()` là True nên chỗ này rất dễ báo ngược)",
   "thieu_het" in NB.sua_mau_mat())

# ---------------------------------------------------------------------------
print("\n[CA 4] SỔ ĐỌC LẠI ĐƯỢC BẰNG **TIẾN TRÌNH KHÁC** (đúng cảnh tắt app)")
# ---------------------------------------------------------------------------
import subprocess
mau_ok = T / "mau" / "mau_ok.wav"
if not _wav_gia(mau_ok, 8.0, 220):
    bo_qua("4 dựng WAV mẫu", "ffmpeg không sinh được file mẫu")
else:
    so_p.unlink(missing_ok=True)
    r = NB.them_giong("Giọng của tôi", str(mau_ok), lang="vi",
                      nguon="mẫu tổng hợp của cổng test")
    ok("4a `them_giong` nhận mẫu hợp lệ", r.get("ok"), str(r.get("loi")))
    ok("4b mã giọng là `vnb:` (tiền tố NGUYÊN BẢN của máy)",
       str(r.get("ma", "")).startswith("vnb:"), str(r.get("ma"))[:40])
    ok("4c mẫu được CHÉP vào DATA_DIR (xoá file gốc thì giọng vẫn chạy)",
       str(NB.thu_muc_mau()) in str(r.get("ma", "")))
    # `reconfigure(utf-8)` LÀ BẮT BUỘC, không phải cho đẹp: cổng này chạy
    # tiến trình con rồi ĐỌC stdout của nó, tức stdout bị CHUYỂN HƯỚNG. Lúc đó
    # Python lấy **cp1252**, và dòng `print` mang chữ Việt (`ensure_ascii=
    # False`) ném `UnicodeEncodeError` -> tiến trình con chết, cổng đọc ra
    # "không có BQJSON" rồi báo HỎNG **oan cho bản vá**. Đúng bẫy đã ghi:
    # *"test hỏng oan vì cp1252 khi ghi ra file"* — chạy tay trong console thì
    # LUÔN XANH nên loại lỗi này cực dễ bị đổ oan.
    ma_kt = r"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["BQ_DATA_DIR"] = sys.argv[1]
sys.path.insert(0, sys.argv[2])
from app.core import nhan_ban_giong as NB
print("BQJSON\t" + json.dumps(
    {"ds": NB.danh_sach(), "ten": list(NB._doc_so())}, ensure_ascii=False))
"""
    kt_py = T / "_kiem_tien_trinh_khac.py"
    kt_py.write_text(ma_kt, encoding="utf-8")
    p = subprocess.run([sys.executable, "-u", str(kt_py), str(T), str(REPO)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300,
                       creationflags=(0x08000000 if os.name == "nt" else 0))
    _kq = {}
    for d in (p.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            _kq = json.loads(d.split("\t", 1)[1])
    ok("4d TIẾN TRÌNH KHÁC đọc lại được sổ (tắt app không mất giọng)",
       _kq.get("ten") == ["Giọng của tôi"], str(_kq.get("ten")))
    ok("4e tiến trình khác thấy ĐÚNG 1 giọng trong `danh_sach()`",
       len(_kq.get("ds") or []) == 1, f"{len(_kq.get('ds') or [])} giọng")

# ---------------------------------------------------------------------------
print("\n[CA 5] MẪU HỎNG PHẢI BÁO TỬ TẾ — không để tới lúc xuất 30 video")
# ---------------------------------------------------------------------------
xau = T / "xau"
xau.mkdir(parents=True, exist_ok=True)
(xau / "rong.wav").write_bytes(b"")
(xau / "khong_audio.wav").write_bytes(b"day khong phai audio" * 400)
_wav_gia(xau / "qua_ngan.wav", 1.0, 220)
for ten, f in (("0 byte", "rong.wav"), ("không phải audio", "khong_audio.wav"),
               ("quá ngắn (1 giây)", "qua_ngan.wav"),
               ("không tồn tại", "khong_he_co.wav")):
    kt = NB.kiem_mau(str(xau / f))
    ok(f"5 mẫu {ten} -> từ chối KÈM LÝ DO đọc được",
       (not kt.get("ok")) and len(str(kt.get("loi") or "")) > 8,
       str(kt.get("loi"))[:64])
kt = NB.kiem_mau("")
ok("5e đường dẫn RỖNG -> từ chối, không nổ, không coi `Path(\"\")` là file",
   not kt.get("ok"), str(kt.get("loi"))[:48])

# ---------------------------------------------------------------------------
print("\n[CA 6] XOÁ GIỌNG KHÔNG ĐƯỢC XOÁ LUNG TUNG (đi qua `xoa_an_toan`)")
# ---------------------------------------------------------------------------
ok("6a `nhan_ban_giong` đi qua cửa chung `xoa_an_toan`, không tự canh",
   "xoa_an_toan" in _ma_that(REPO / "app" / "core" / "nhan_ban_giong.py"))
# Bốn chốt của cửa chung, mỗi mục đọc ĐÚNG LÝ DO chứ không chỉ hỏi "có chặn
# không" — bài học cổng 80 LỌT 6: hỏi chung thì một chốt khác bắt hộ và mục
# tự vô hiệu.
ok("6b chốt CHUỖI RỖNG: `Path(\"\")` bị từ chối vì là THƯ MỤC ĐANG LÀM VIỆC",
   "THƯ MỤC ĐANG LÀM VIỆC" in XA.ly_do_cam(Path("")),
   XA.ly_do_cam(Path("")))
ok("6c chốt GỐC Ổ ĐĨA", "GỐC Ổ ĐĨA" in XA.ly_do_cam(Path(REPO.anchor)),
   XA.ly_do_cam(Path(REPO.anchor)))
ok("6d mẫu NGOÀI thư mục mẫu bị từ chối (`trong=`)",
   not XA.an_toan_de_xoa(REPO / "main.py", trong=NB.thu_muc_mau()))
ok("6e mẫu TRONG thư mục mẫu thì cho xoá",
   XA.an_toan_de_xoa(NB.thu_muc_mau() / "x.wav", trong=NB.thu_muc_mau()))

# THỬ THẬT: mục sổ có `mau` RỖNG -> xoá phải bỏ mục khỏi sổ mà KHÔNG đụng
# thư mục đang làm việc. Mồi canary đặt ở CẢ cwd LẪN thư mục CHA (chỉ đặt
# trong cwd thì ca `".."` đi lọt — bài học cổng 80).
NB._ghi_so({"rong": {"mau": "", "may": "vieneu"}})
moi1 = Path.cwd() / "_canary_cong88.txt"
moi2 = Path.cwd().parent / "_canary_cong88_cha.txt"
for m in (moi1, moi2):
    try:
        m.write_text("còn sống", encoding="utf-8")
    except OSError:
        pass
_xoa_ok = NB.xoa("rong")
ok("6f xoá mục có `mau` RỖNG: bỏ khỏi sổ được", _xoa_ok and
   "rong" not in NB._doc_so())
ok("6g ... mà KHÔNG xoá thư mục đang làm việc (mồi canary còn)",
   moi1.exists() and (moi2.exists() or not moi2.parent.exists()))
for m in (moi1, moi2):
    m.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
print("\n[CA 7] THIẾU MODEL -> LÙI ÊM về edge-tts + GHI LOG (khác Demucs: CHẶN)")
# ---------------------------------------------------------------------------
# Giọng nhân bản thiếu model thì lùi ra video ĐÚNG chỉ khác giọng, nên LÙI là
# đúng (luật Piper/Kokoro). Demucs thì lùi ra video HỎNG nên phải CHẶN.
_that_co = VN.co_vieneu
VN.co_vieneu = lambda: False                   # type: ignore[assignment]
_that_tt = VN.tinh_trang_vieneu
VN.tinh_trang_vieneu = lambda: {                # type: ignore[assignment]
    "co": False, "thieu": ["vieneu"], "python": "", "thu_muc": str(T),
    "phien_ban": "", "so_giong": 20, "o_tam": "", "cai_duoc": False}
try:
    _lg = T / "logs"
    _truoc = len(list(_lg.glob("giong_vieneu_*.log"))) if _lg.is_dir() else 0
    okv, _mv = VN.doc_loat(["xin chào"], [str(T / "lui.mp3")],
                           VN.ma_nhan_ban(str(mau_ok)), lang="vi")
    ok("7a thiếu model -> `doc_loat` trả toàn False (nơi gọi LÙI edge-tts), "
       "KHÔNG NÉM", okv == [False])
    _sau = list(_lg.glob("giong_vieneu_*.log")) if _lg.is_dir() else []
    _co_dong = any("LÙI" in p.read_text(encoding="utf-8", errors="replace")
                   for p in _sau)
    ok("7b ... và NÓI RA trong log (lùi êm mà im lặng = hỏng âm thầm)",
       bool(_sau) and _co_dong, f"{len(_sau)} file log")
finally:
    VN.co_vieneu = _that_co                    # type: ignore[assignment]
    VN.tinh_trang_vieneu = _that_tt            # type: ignore[assignment]

# `nhan()` phải NÓI ĐÍCH DANH gói còn thiếu, đừng ghi "chưa cài" trơn.
_that_thieu = NB.thieu_de_nhan_ban
NB.thieu_de_nhan_ban = lambda m: ["torch", "torchaudio"]  # type: ignore
try:
    NB._ghi_so({"G": {"mau": str(mau_ok), "may": "vieneu", "lang": "vi",
                      "giay": 8.0}})
    _nh = NB.nhan("G")
    ok("7c nhãn nói ĐÍCH DANH gói thiếu (không phải 'chưa cài' trơn)",
       "torch" in _nh and "CHƯA CHẠY ĐƯỢC" in _nh, _nh[:70])
    ok("7d giọng CHƯA CHẠY ĐƯỢC vẫn HIỆN trong danh sách (tiền lệ "
       "Piper/VieNeu/Kokoro — giấu đi thì không ai biết là có)",
       len(NB.danh_sach()) == 1)
    ok("7e `chi_chay_duoc=True` thì LỌC BỎ nó",
       len(NB.danh_sach(chi_chay_duoc=True)) == 0)
finally:
    NB.thieu_de_nhan_ban = _that_thieu         # type: ignore[assignment]

# ---------------------------------------------------------------------------
print("\n[CA 8] NHÃN — KHÔNG EMOJI, và NGẮN (cổng 84 chỉ còn dư 12 px)")
# ---------------------------------------------------------------------------
NB._ghi_so({
    "Giọng của tôi": {"mau": str(mau_ok), "may": "vieneu", "lang": "vi",
                      "giay": 8.4},
    "Giọng chị Lan": {"mau": str(mau_ok), "may": "vieneu", "lang": "vi",
                      "giay": 5.0},
})


def _co_emoji(s: str) -> list[str]:
    """Ký hiệu dễ THIẾU GLYPH trên máy anh Hùng -> ra Ô ĐEN (lỗi thật
    v2.6.22). Chỉ soi NHÃN, không soi cả file: emoji trong ghi chú thì người
    dùng không thấy (bản đầu cổng 27 FAIL oan vì thế)."""
    return [c for c in s
            if unicodedata.category(c) == "So" or ord(c) > 0x2500]


ds_nb = NB.danh_sach()
ok("8a có 2 giọng trong danh sách", len(ds_nb) == 2, f"{len(ds_nb)}")
for _ma, _nh in ds_nb:
    ok(f"8b nhãn KHÔNG EMOJI: {_nh[:34]}", not _co_emoji(_nh),
       "".join(_co_emoji(_nh)))
# TỰ KIỂM BỘ DÒ: thiếu mục này thì "0 emoji" có thể là bộ dò đã chết.
ok("8b' TỰ KIỂM BỘ DÒ emoji: chuỗi CÓ emoji phải BỊ BẮT",
   len(_co_emoji("Giọng 📋 của tôi")) > 0)

nhom = GB.gom_nhom([(n, m) for m, n in ds_nb], "vi", loi_tat=True)
dong = [(n, v) for n, v in nhom if v]
ok("8c nhãn qua `gom_nhom` vẫn KHÔNG EMOJI",
   all(not _co_emoji(n) for n, _v in dong))
_dai = max((len(n) for n, _v in dong), default=0)
# Trần 132 = đúng trần đuôi nhãn mà cổng 79 đang canh. Dòng Kokoro đo được
# 139-178 ký tự và đã đẩy mất cảnh báo "cần tải"; nhãn giọng của anh Hùng
# phải NGẮN HƠN HẲN, nếu không nó ăn vào chỗ của chính cảnh báo đó.
ok("8d nhãn NGẮN — dài nhất phải dưới 132 ký tự (Kokoro 139-178 đã đẩy mất "
   "cảnh báo 'cần tải')", _dai < 132, f"dài nhất {_dai} ký tự")
ok("8e giọng nhân bản vào nhóm TRÊN MÁY, không rơi vào nhóm edge-tts",
   any("TRÊN MÁY" in n for n, v in nhom if not v),
   " | ".join(n[:30] for n, v in nhom if not v))

# ---------------------------------------------------------------------------
print("\n[CA 9] HỘP THOẠI THẬT — dựng được, nút có, sổ đổi thì combo đổi")
# ---------------------------------------------------------------------------
qapp = QApplication.instance() or QApplication([])
try:
    from app.ui import theme
    qapp.setStyleSheet(theme.QSS)              # QSS THẬT (bài học cổng 9)
except Exception:                                              # noqa: BLE001
    pass

# Hộp thật sẽ mở QFileDialog/QMessageBox -> vá TRƯỚC khi bấm, nếu không hộp
# thoại thật TREO cổng và làm tưởng app crash (luật `_test_app_smoke`).
QFileDialog.getOpenFileName = staticmethod(       # type: ignore[assignment]
    lambda *a, **k: (str(mau_ok), ""))
QMessageBox.information = staticmethod(lambda *a, **k: None)   # type: ignore
QMessageBox.warning = staticmethod(lambda *a, **k: None)       # type: ignore
QMessageBox.exec = lambda self, *a, **k: QMessageBox.StandardButton.Yes  # type: ignore

from app.ui.thay_giong_dialog import (  # noqa: E402
    HopGiongToi, giong_dung_duoc,
)

h = HopGiongToi()
ok("9a hộp dựng được, có danh sách giọng", h.ds.count() == 2,
   f"{h.ds.count()} dòng")
nut = [b.text() for b in h.findChildren(QPushButton)]
ok("9b có đủ nút: chọn mẫu · nghe thử mẫu · nghe thử giọng · lưu · đổi tên "
   "· xoá", all(any(k in t for t in nut) for k in
                ("Chọn file mẫu", "Nghe thử mẫu", "Nghe thử giọng",
                 "Lưu giọng", "Đổi tên", "Xoá giọng")), " | ".join(nut))
ok("9c MỌI nhãn nút KHÔNG EMOJI",
   all(not _co_emoji(t) for t in nut),
   "".join(c for t in nut for c in _co_emoji(t)))

# THÊM giọng qua ĐÚNG đường người dùng đi: bấm Chọn file -> gõ tên -> bấm Lưu
h._chon_mau()
h.o_ten.setText("Giọng mới toanh")
_bao = []
h.so_doi.connect(lambda: _bao.append(1))
h._luu()
ok("9d bấm Lưu -> giọng vào sổ", "Giọng mới toanh" in NB._doc_so())
ok("9e ... và hộp BẮN tín hiệu `so_doi` để combo cha dựng lại",
   len(_bao) == 1, f"{len(_bao)} tín hiệu")
ok("9f danh sách trong hộp tự nạp lại (3 dòng)", h.ds.count() == 3,
   f"{h.ds.count()}")

# ĐỔI TÊN không được đổi mã giọng -> kênh đang gán giọng đó vẫn đúng
_ma_truoc = NB.ma_giong("Giọng mới toanh")
h.ds.setCurrentRow([i for i in range(h.ds.count())
                    if h.ds.item(i).data(0x0100) == "Giọng mới toanh"][0])
h.o_ten.setText("Giọng đổi tên rồi")
h._doi_ten()
ok("9g đổi tên: tên mới vào sổ", "Giọng đổi tên rồi" in NB._doc_so())
ok("9h đổi tên KHÔNG đổi mã giọng (kênh đang gán vẫn đúng)",
   NB.ma_giong("Giọng đổi tên rồi") == _ma_truoc)

# NGHE THỬ MẪU phải THẬT SỰ gọi phát tiếng (vá ĐẾM, không vá rỗng — vá rỗng
# thì mục này tự ĐẠT vì lý do NGƯỢC HẲN, bẫy cổng 67).
# PHẢI CHỌN LẠI MẪU TRƯỚC: `_luu()` cố ý xoá `_mau` (dọn ô để thêm giọng kế
# tiếp), nên gọi `_nghe_mau()` ngay sau `_luu()` sẽ rơi vào nhánh "chưa chọn
# file" -> 0 lượt phát. Lượt chạy đầu của cổng đã HỎNG OAN đúng vì thế; đây là
# lỗi CỦA PHÉP THỬ, không phải của hộp.
_PHAT.clear()
h._chon_mau()
ok("9i0 chọn lại mẫu được (`_luu` cố ý xoá ô mẫu)", bool(h._mau))
h._nghe_mau()
ok("9i nút Nghe thử mẫu THẬT SỰ phát tiếng (1 lượt gọi PlaySound)",
   len(_PHAT) >= 1, f"{len(_PHAT)} lượt")
# ... và khi CHƯA chọn mẫu thì KHÔNG phát bừa, chỉ báo.
_PHAT.clear()
h._mau = ""
h._nghe_mau()
ok("9i' chưa chọn mẫu -> KHÔNG phát bừa (chỉ báo)", len(_PHAT) == 0,
   f"{len(_PHAT)} lượt")

# XOÁ đi qua hộp xác nhận có nút MẶC ĐỊNH là KHÔNG
h.ds.setCurrentRow([i for i in range(h.ds.count())
                    if h.ds.item(i).data(0x0100) == "Giọng đổi tên rồi"][0])
h._xoa()
ok("9j xoá được qua hộp (đã vá exec -> Yes)",
   "Giọng đổi tên rồi" not in NB._doc_so())

# GIỌNG ĐÃ LƯU PHẢI HIỆN TRONG Ô GIỌNG ĐỌC — đây là mệnh đề "lưu được VÀ
# dùng được". Đo trên chính `giong_dung_duoc` mà combo gọi.
_ds_combo = giong_dung_duoc([("Giọng thường", "vi-VN-HoaiMyNeural")])
_ma_combo = [v for _n, v in _ds_combo if str(v).startswith("vnb:")]
ok("9k giọng đã lưu CÓ trong danh sách combo (`giong_dung_duoc`)",
   len(_ma_combo) == 2, f"{len(_ma_combo)} mã vnb:")
h.close()

# ---------------------------------------------------------------------------
print("\n[CA 10] MỞ HỘP RỒI LƯU KHÔNG ĐƯỢC GHI ĐÈ GIỌNG ĐANG CHỌN BẰNG \"\"")
# ---------------------------------------------------------------------------
# Lỗi thật cổng 55: combo dựng sau thread nền -> mở hộp rồi Lưu ngay là ghi đè
# lựa chọn của user bằng "". Ở đây rủi ro cùng hình dạng: hộp con lưu giọng
# xong bắn `so_doi` -> cha dựng lại combo. Dựng theo QSettings là nuốt mất
# giọng đang hiện (user chưa bấm Chạy nên setting còn là giọng CŨ).
cay = ast.parse(ui_src.read_text(encoding="utf-8"))
_co_tham_so = _dung_theo_widget = False
for n in ast.walk(cay):
    if isinstance(n, ast.FunctionDef) and n.name == "_dung_combo_giong":
        _co_tham_so = any(a.arg == "giu_dang_chon" for a in n.args.args)
        # phải có nhánh ĐỌC TỪ WIDGET, không chỉ đọc QSettings
        _dung_theo_widget = "currentData" in ast.unparse(n)
ok("10a `_dung_combo_giong` có tham số `giu_dang_chon`", _co_tham_so)
ok("10b ... và nhánh đó đọc từ WIDGET (`currentData`), không từ QSettings",
   _dung_theo_widget)
# **KHÔNG dùng `ast.unparse` rồi tìm chuỗi** — `unparse` GIỮ NGUYÊN DOCSTRING,
# mà docstring của `_mo_giong_toi` cố ý trích chính cụm `giu_dang_chon=True`
# để giải thích chốt. Bản đầu của mục này làm vậy và **THỬ PHÁ ĐÃ LỌT**: gỡ
# sạch tham số khỏi lời gọi mà cổng vẫn XANH vì nó khớp trúng docstring. Đúng
# bài học cổng 73 lỗi (b), và là lần thứ hai `unparse`-rồi-tìm-chuỗi sập.
# Cách ĐÚNG: đi tìm NÚT `ast.keyword` thật trong thân hàm.
def _co_kw(ten_ham: str, ten_kw: str, gia_tri=True) -> bool:
    for n in ast.walk(cay):
        if isinstance(n, ast.FunctionDef) and n.name == ten_ham:
            for c in ast.walk(n):
                if isinstance(c, ast.keyword) and c.arg == ten_kw \
                        and isinstance(c.value, ast.Constant) \
                        and c.value.value is gia_tri:
                    return True
    return False


ok("10c `_mo_giong_toi` nối `so_doi` với `giu_dang_chon=True` "
   "(tìm NÚT ast.keyword, KHÔNG tìm chuỗi trong `unparse` — unparse giữ "
   "docstring nên phép phá đã LỌT một lượt)",
   _co_kw("_mo_giong_toi", "giu_dang_chon", True))
# TỰ KIỂM BỘ DÒ: bản KHÔNG truyền tham số phải bị BẮT.
_gia2 = ast.parse("def f():\n    '''giu_dang_chon=True trong docstring'''\n"
                  "    g(lambda: self._dung_combo_giong())\n")
_bat2 = False
for n in ast.walk(_gia2):
    if isinstance(n, ast.FunctionDef):
        for c in ast.walk(n):
            if isinstance(c, ast.keyword) and c.arg == "giu_dang_chon":
                _bat2 = True
ok("10c' TỰ KIỂM BỘ DÒ: hàm chỉ NHẮC cụm đó trong DOCSTRING thì phải TRƯỢT",
   not _bat2)

# ---------------------------------------------------------------------------
print("\n[CA 11] TRẦN KÝ TỰ + CHIA ĐOẠN — nói ra, đừng để người dùng tự đoán")
# ---------------------------------------------------------------------------
_v3 = None
for c in (REPO / "_giong_vieneu" / "venv" / "Lib" / "site-packages" / "vieneu"
          / "v3turbo.py",):
    if c.exists():
        _v3 = c
if _v3 is None:
    bo_qua("11 trần ký tự", "máy này chưa tải bộ VieNeu")
else:
    _s = _v3.read_text(encoding="utf-8", errors="replace")
    ok("11a `infer` có tham số `ref_audio` (đường NHÂN BẢN có thật trong bản "
       "model đang dùng)", "ref_audio" in _s)
    ok("11b trần ký tự MỖI LƯỢT là `max_chars` = 256, và GÓI tự chia chunk "
       "(`normalize_to_chunks_v3`)", "max_chars: int = 256" in _s
       and "normalize_to_chunks_v3" in _s)
    # BẪY SỐ 1: `use_ref_codes` là cờ BOOL, KHÔNG phải chỗ để đường dẫn.
    ma_vn = _ma_that(REPO / "app" / "core" / "giong_vieneu.py")
    ok("11c app KHÔNG nhét đường dẫn vào `use_ref_codes` (bẫy DƯƠNG TÍNH GIẢ "
       "lượt 4)", "use_ref_codes" not in ma_vn)

# ---------------------------------------------------------------------------
print("\n[CA 12] NÚT TẢI PHẦN NHÂN BẢN — bám `thieu`, KHÔNG bám \"chạy được\"")
# ---------------------------------------------------------------------------
# LỖI THẬT: anh Hùng lưu giọng "MQ Idol" xong, dòng giọng ghi **CHƯA CHẠY ĐƯỢC
# (thiếu torch, torchaudio)** — nhãn NÓI THẬT (bản `.exe` có venv VieNeu ở
# `%LOCALAPPDATA%` mà không có torch) nhưng **KHÔNG CÓ NÚT NÀO để cài**. Tính
# năng thật thà báo hỏng rồi bỏ người dùng ở đó.
_tt_nb = VN.tinh_trang_nhan_ban()
ok("12a `tinh_trang_nhan_ban` trả đủ khoá cho UI",
   all(k in _tt_nb for k in ("thieu", "co", "cai_duoc", "vi_sao", "nhan",
                             "mb_tai", "cuda", "thu_muc")),
   str(sorted(_tt_nb))[:80])

# ═══ MỆNH ĐỀ TRUNG TÂM (khuôn cổng 58 CA 1a) ═══
# Danh sách gói THIẾU mà bản CHẠY-NGUỒN nói ra phải GIỐNG HỆT danh sách một
# tiến trình KHÔNG có `.venv` nói ra. Nếu lệch thì phép dò đang mượn gói của
# `.venv` -> máy dev XANH, máy anh Hùng ĐỎ, đúng cái bẫy đã cắn hai lần.
# Cách giả lập `.exe`: import `app` xong **RỒI MỚI** cắt mọi mục
# `site-packages` khỏi `sys.path`. Cắt TRƯỚC thì chính `import config` chết và
# cổng đo nhầm thứ khác (bản `.exe` vẫn có đủ dotenv/PyQt6 trong `_internal`;
# khác biệt duy nhất là chỗ tìm torch).
_ma_exe = r"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["BQ_DATA_DIR"] = sys.argv[1]
sys.path.insert(0, sys.argv[2])
# 1) import ĐỦ TRƯỚC — đúng như bản .exe đã có sẵn mọi thứ trong `_internal`
import config                                          # noqa: F401
from app.core import giong_vieneu as VN
from app.core import nhan_ban_giong as NB
# 2) RỒI MỚI cắt `site-packages` — từ giờ tiến trình này không còn `.venv` để
#    mượn torch, y hệt máy anh Hùng.
sys.path[:] = [p for p in sys.path if "site-packages" not in p.replace("\\", "/")]
ra = {
    "thieu": NB.thieu_de_nhan_ban(NB.MAY_VIENEU),
    "thieu_vn": VN.thieu_nhan_ban(),
    "co_sp": [p for p in sys.path if "site-packages" in p],
}
# MỒI CHIA ĐÔI kiểu cổng 58: `sys.argv[3]` là gói CÓ trong `.venv` mà KHÔNG có
# trong venv VieNeu. Bộ dò đúng (theo FILE) phải kể nó là THIẾU ở CẢ hai tiến
# trình; bộ dò kiểu `find_spec` thì bản chạy-nguồn "thấy" nó của `.venv` rồi
# trả rỗng -> hai bên LỆCH và mục 12c'' bắt được.
NB._CAN_CHO_NHAN_BAN = (sys.argv[3],)
ra["thieu_moi"] = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
print("BQJSON\t" + json.dumps(ra, ensure_ascii=False))
"""
#: Gói CÓ trong `.venv` của app, KHÔNG có trong `_giong_vieneu/venv` — đo
#: trước khi dùng, đừng tin trí nhớ.
_MOI = "PyQt6"
_exe_py = T / "_gia_lap_exe.py"
_exe_py.write_text(_ma_exe, encoding="utf-8")
_p = subprocess.run([sys.executable, "-u", str(_exe_py), str(T), str(REPO),
                     _MOI],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=600,
                    creationflags=(0x08000000 if os.name == "nt" else 0))
_kq_exe: dict = {}
for _d in (_p.stdout or "").splitlines():
    if _d.startswith("BQJSON\t"):
        _kq_exe = json.loads(_d.split("\t", 1)[1])
if not _kq_exe:
    ok("12b giả lập bản `.exe` chạy được", False,
       ((_p.stderr or "") + (_p.stdout or ""))[-200:])
else:
    # Bộ dò phải THẬT SỰ mất `.venv` — không thì 12c tự ĐẠT vì lý do SAI.
    ok("12b giả lập `.exe`: đã cắt sạch `site-packages` khỏi `sys.path`",
       not _kq_exe.get("co_sp"), str(_kq_exe.get("co_sp"))[:70])
    _thieu_dev = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
    ok("12c MỆNH ĐỀ TRUNG TÂM: danh sách thiếu của bản CHẠY-NGUỒN GIỐNG HỆT "
       "của tiến trình KHÔNG có `.venv` (dò bằng FILE, không mượn `.venv`)",
       list(_kq_exe.get("thieu") or []) == list(_thieu_dev),
       f"nguồn={_thieu_dev} · .exe={_kq_exe.get('thieu')}")
    ok("12c' `giong_vieneu.thieu_nhan_ban` nói CÙNG một câu với "
       "`nhan_ban_giong.thieu_de_nhan_ban` (một bộ dò, không hai)",
       list(_kq_exe.get("thieu_vn") or []) == list(_kq_exe.get("thieu") or []),
       f"{_kq_exe.get('thieu_vn')} vs {_kq_exe.get('thieu')}")

    # ═══ MỒI CHIA ĐÔI — 12c mới có RĂNG nhờ mục này ═══
    # Trên máy này venv VieNeu ĐÃ có cả torch lẫn torchaudio, nên 12c so
    # `[] == []`: ĐÚNG nhưng KHÔNG phân biệt được bộ dò tốt với bộ dò hỏng.
    # `_MOI` là gói CÓ trong `.venv` của app mà KHÔNG có trong venv VieNeu —
    # đúng phép chia đôi cổng 58 đã tìm ra ("mọi gói THIẾU đều là gói `.venv`
    # ĐÃ CÓ"). Bộ dò theo FILE phải kể nó THIẾU ở CẢ hai tiến trình; bộ dò kiểu
    # `find_spec` thì bản chạy-nguồn mượn `.venv` rồi trả RỖNG -> hai bên lệch.
    _sp_venv = REPO / ".venv" / "Lib" / "site-packages" / _MOI
    _sp_vn = (REPO / "_giong_vieneu" / "venv" / "Lib" / "site-packages" / _MOI)
    if not _sp_venv.is_dir() or _sp_vn.is_dir():
        bo_qua("12c'' mồi chia đôi",
               f"{_MOI} không còn đúng thế 'có ở .venv, thiếu ở venv VieNeu'")
    else:
        _that_can = NB._CAN_CHO_NHAN_BAN
        NB._CAN_CHO_NHAN_BAN = (_MOI,)          # type: ignore[assignment]
        try:
            _moi_dev = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
        finally:
            NB._CAN_CHO_NHAN_BAN = _that_can    # type: ignore[assignment]
        _moi_exe = list(_kq_exe.get("thieu_moi") or [])
        ok(f"12c''0 mồi `{_MOI}` THẬT SỰ thiếu ở venv VieNeu (nếu không thì "
           "12c'' tự ĐẠT vì lý do SAI)", _moi_dev == [_MOI] != [],
           f"nguồn nói {_moi_dev}")
        ok(f"12c'' MỆNH ĐỀ TRUNG TÂM CÓ RĂNG: mồi `{_MOI}` (CÓ trong `.venv`, "
           "THIẾU ở venv VieNeu) -> bản chạy-nguồn và tiến trình KHÔNG có "
           "`.venv` nói GIỐNG HỆT. Bộ dò kiểu `find_spec` sẽ lệch ở đây.",
           _moi_dev == _moi_exe == [_MOI],
           f"nguồn={_moi_dev} · .exe={_moi_exe}")

# ═══ LỆNH CÀI: `--ignore-installed` + KHÔNG cài vào `.venv` ═══
# QUÉT BẰNG AST, KHÔNG QUÉT CHUỖI: chính phần GHI CHÚ của `cai_nhan_ban` có
# cụm `--ignore-installed` (nó giải thích vì sao cờ đó phải ở đó), nên tìm
# bằng `in` thì gỡ cờ khỏi LỆNH mà cổng vẫn XANH — đúng bài học cổng 58/56d.
_cay_vn = ast.parse((REPO / "app" / "core" / "giong_vieneu.py")
                    .read_text(encoding="utf-8"))
_hang_cai: list[str] = []
for _n in ast.walk(_cay_vn):
    if isinstance(_n, ast.FunctionDef) and _n.name == "cai_nhan_ban":
        # BỎ DOCSTRING BẰNG CẤU TRÚC AST, KHÔNG so mặt chữ. Bản đầu của mục
        # này hỏi `_hang_cai[0].startswith("TẢI + CÀI")` — sửa một chữ trong
        # docstring là phép bỏ đó trượt, docstring (có chứa
        # `--ignore-installed` vì nó GIẢI THÍCH cờ ấy) lọt vào danh sách, rồi
        # mục này ĐẠT OAN kể cả khi cờ đã bị gỡ khỏi LỆNH. Đúng bẫy cổng
        # 47/51/53/54/73 lặp lần thứ bảy, lần này trong chính mục viết ra để
        # chống nó.
        _than = list(_n.body)
        if _than and isinstance(_than[0], ast.Expr) \
                and isinstance(_than[0].value, ast.Constant) \
                and isinstance(_than[0].value.value, str):
            _than.pop(0)
        for _st in _than:
            for _c in ast.walk(_st):
                if isinstance(_c, ast.Constant) and isinstance(_c.value, str):
                    _hang_cai.append(_c.value)
ok("12d0 TỰ KIỂM PHÉP BỎ DOCSTRING: docstring của `cai_nhan_ban` CÓ chứa "
   "`--ignore-installed` (nên nếu không bỏ nó thì 12d vô nghĩa)",
   "--ignore-installed" in (ast.get_docstring(next(
       n for n in ast.walk(_cay_vn)
       if isinstance(n, ast.FunctionDef) and n.name == "cai_nhan_ban")) or ""))
ok("12d lệnh cài CÓ `--ignore-installed` (quét AST trong THÂN hàm, đã bỏ "
   "docstring — quét chuỗi cả file là gỡ cờ mà cổng vẫn xanh)",
   "--ignore-installed" in _hang_cai, str(_hang_cai[:6])[:90])
# ═══ MỖI LỆNH pip PHẢI CÓ CỜ, KHÔNG PHẢI "ở đâu đó trong hàm có cờ" ═══
# LỖI THẬT CỦA CHÍNH CỔNG NÀY, bắt được bằng thử phá 20/08/2026: từ khi
# `cai_nhan_ban` có LỆNH pip THỨ HAI (vòng tự dò), mục 12d ở trên **mất răng** —
# gỡ cờ khỏi lệnh CHÍNH thì lệnh của vòng tự dò vẫn còn cờ, `_hang_cai` vẫn
# chứa chuỗi đó, mục vẫn ĐẠT. Đo được: phép phá 11 từ BẮT chuyển thành **LỌT**.
# Bất biến đúng là: **MỌI** danh sách dòng lệnh có `"install"` đều phải mang cờ.
_ds_pip = [
    [c.value for c in ast.walk(_l)
     if isinstance(c, ast.Constant) and isinstance(c.value, str)]
    for _st in _than for _l in ast.walk(_st)
    if isinstance(_l, ast.List)
    and any(isinstance(e, ast.Constant) and e.value == "install"
            for e in _l.elts)]
ok("12d'' MỌI lệnh pip trong `cai_nhan_ban` đều mang cờ (có 2 lệnh: cài chính "
   "+ vòng tự dò; hỏi 'ở đâu đó có cờ' là gỡ 1 lệnh mà cổng vẫn xanh)",
   len(_ds_pip) >= 2 and all("--ignore-installed" in d for d in _ds_pip),
   f"{len(_ds_pip)} lệnh pip · có cờ: "
   f"{[('--ignore-installed' in d) for d in _ds_pip]}")
ok("12d' TỰ KIỂM BỘ DÒ: bản KHÔNG có cờ thì bộ dò phải TRƯỢT",
   "--khong-he-co-co-nay" not in _hang_cai)

def _than_ham(cay, ten: str):
    """Các nút AST trong THÂN một hàm (đã bỏ docstring)."""
    for n in ast.walk(cay):
        if isinstance(n, ast.FunctionDef) and n.name == ten:
            than = list(n.body)
            if than and isinstance(than[0], ast.Expr) \
                    and isinstance(than[0].value, ast.Constant) \
                    and isinstance(than[0].value.value, str):
                than.pop(0)
            for st in than:
                yield from ast.walk(st)


def _dung_sys_executable(cay, ten: str) -> bool:
    """Thân hàm `ten` có đụng `sys.executable` không (quét AST).

    **KHÔNG quét chuỗi trên `_ma_that`**: hàm đó nối TOKEN bằng dấu cách nên
    `sys.executable` biến thành `"sys . executable"` — tìm `"sys.executable"`
    thì KHÔNG BAO GIỜ khớp và mục này tự ĐẠT vĩnh viễn. Bản đầu của tôi làm
    đúng vậy; đây là cùng lớp bệnh "phép đo hỏng phát chứng nhận".
    """
    for c in _than_ham(cay, ten):
        if isinstance(c, ast.Attribute) and c.attr == "executable" \
                and isinstance(c.value, ast.Name) and c.value.id == "sys":
            return True
    return False


ok("12e KHÔNG cài vào `.venv` của app: thân `cai_nhan_ban` không đụng "
   "`sys.executable` (bản `.exe` thì đó là chính BQHungVideo.exe, còn ở mã "
   "nguồn thì đó là `.venv` đang chạy sản xuất 300 kênh)",
   not _dung_sys_executable(_cay_vn, "cai_nhan_ban"))
ok("12e' TỰ KIỂM BỘ DÒ: hàm CÓ đụng `sys.executable` thì phải BỊ BẮT",
   _dung_sys_executable(
       ast.parse("def f():\n    return [sys.executable, '-m', 'pip']\n"), "f"))
ok("12f hậu kiểm gọi lại `thieu_nhan_ban()` — SO ĐƯỜNG DẪN, không hỏi "
   "\"import được không\"",
   any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
       and c.func.id == "thieu_nhan_ban"
       for n in ast.walk(_cay_vn)
       if isinstance(n, ast.FunctionDef) and n.name == "cai_nhan_ban"
       for c in ast.walk(n)))

# ═══ NÚT: HIỆN khi thiếu, ẨN khi đủ — và BÁM `thieu` ═══
_ghi_hop: list[str] = []
QMessageBox.question = staticmethod(          # type: ignore[assignment]
    lambda *a, **k: (_ghi_hop.append(str(a[2]) if len(a) > 2 else ""),
                     QMessageBox.StandardButton.No)[1])

h2 = HopGiongToi()
h2.show()
_du = not VN.thieu_nhan_ban()
ok("12g máy này ĐỦ torch -> nút ẨN" if _du else
   "12g máy này THIẾU -> nút HIỆN",
   h2.b_tai_nb.isVisible() is (not _du),
   f"thieu={VN.thieu_nhan_ban()} · hiện={h2.b_tai_nb.isVisible()}")
h2.close()

# **CÁI BẪY ĐÃ LÀM RA VIỆC NÀY.** Vá phép dò trả ['torch'] rồi đòi nút CÒN
# HIỆN. Nút bám cờ "máy này chạy được không" thì trên máy dev (venv ĐÃ có
# torch) nút BIẾN MẤT, không ai bấm, bản `.exe` mãi mãi thiếu — y hệt cách
# `_lib` của Demucs thiếu torch mà nút không bao giờ hiện (cổng 58).
_that_thieu2 = NB.thieu_de_nhan_ban
NB.thieu_de_nhan_ban = lambda m: ["torch"]     # type: ignore[assignment]
try:
    h3 = HopGiongToi()
    h3.show()
    ok("12h vá `thieu_de_nhan_ban` -> ['torch'] thì nút CÒN HIỆN "
       "(nút bám `thieu`, KHÔNG bám cờ 'chạy được')",
       h3.b_tai_nb.isVisible(), f"hiện={h3.b_tai_nb.isVisible()}")
    _nhan_nut = h3.b_tai_nb.text()
    ok("12i nhãn nêu ĐÍCH DANH gói thiếu (không phải 'chưa cài' trơn)",
       "torch" in _nhan_nut, _nhan_nut[:70])
    ok("12i' ca CÀI DỞ trông KHÁC ca chưa cài lần nào ('Cài tiếp')",
       "Cài tiếp" in _nhan_nut, _nhan_nut[:70])
    ok("12j nhãn nút KHÔNG EMOJI", not _co_emoji(_nhan_nut),
       "".join(_co_emoji(_nhan_nut)))
    # Phải soi CẢ HAI nhánh nhãn: mục trên chỉ thấy nhánh CÀI DỞ, nên gắn
    # emoji vào nhánh "chưa cài lần nào" thì nó KHÔNG bắt được (đo thật: phép
    # phá 18 đi lọt mục này, may có 9c bắt hộ — mà dựa vào mục khác bắt hộ là
    # đúng bẫy cổng 80 LỌT 6).
    for _nh_b, _ten_b in ((VN.nhan_tai_nhan_ban([]), "chưa cài lần nào"),
                          (VN.nhan_tai_nhan_ban(["torch", "torchaudio"]),
                           "thiếu cả hai"),
                          (VN.nhan_tai_nhan_ban(["vieneu/v3turbo.py"]),
                           "chưa có bộ VieNeu")):
        ok(f"12j'' nhãn nhánh «{_ten_b}» KHÔNG EMOJI", not _co_emoji(_nh_b),
           "".join(_co_emoji(_nh_b)) or _nh_b[:44])
    ok("12j' nhãn dòng trạng thái KHÔNG EMOJI",
       not _co_emoji(h3.lb_nb.text()), "".join(_co_emoji(h3.lb_nb.text())))

    # MỘT CON SỐ, BA CHỖ ĐỌC. Cổng 58: nút ghi 155 MB rồi hộp xác nhận doạ
    # 2 GB — hai con số cho CÙNG một lượt tải. Ở đây lấy con số của
    # `mb_nhan_ban()` rồi đòi nó có mặt ở CẢ nhãn, tooltip VÀ hộp xác nhận.
    _so = f"{VN.mb_nhan_ban():,.0f}".replace(",", ".")
    _ghi_hop.clear()
    h3._tai_nhan_ban()          # hộp đã vá -> trả No, KHÔNG tải thật
    _hop = " ".join(_ghi_hop)
    ok("12k hộp xác nhận có hiện ra (và cổng trả No nên KHÔNG tải thật)",
       bool(_ghi_hop) and not h3._dang_cai_nb, f"{len(_ghi_hop)} hộp")
    ok(f"12l nhãn nút / tooltip / hộp xác nhận CÙNG một con số ({_so} MB)",
       _so in _nhan_nut and _so in h3.b_tai_nb.toolTip() and _so in _hop,
       f"nhãn={_so in _nhan_nut} tooltip={_so in h3.b_tai_nb.toolTip()} "
       f"hộp={_so in _hop}")
    ok("12l' con số đó là SỐ ĐO của đúng bản sẽ tải "
       "(cpu 126,3 · cu126 2.485,6)",
       VN.mb_nhan_ban() in (VN.MB_NB_CPU, VN.MB_NB_CUDA),
       f"{VN.mb_nhan_ban()} · cuda={VN.ban_cuda_se_tai()}")
    # DẤU PHẨY CỦA CÂU KHÔNG ĐƯỢC BIẾN THÀNH DẤU CHẤM. Lỗi thật, bắt được ở
    # lượt CHẠY THẬT đầu tiên: `.replace(",", ".")` trên CẢ CÂU ra
    # *"(khoảng 126 MB. tải 1 lần)"*. `giong_kokoro.dau_chua_tai` đã ghi bài
    # học này rồi mà tôi vẫn lặp — nên khoá lại bằng cổng.
    ok("12l'' `so_mb` chỉ đổi dấu nghìn CỦA SỐ (2485.6 -> '2.486')",
       VN.so_mb(2485.6) == "2.486" and VN.so_mb(126.3) == "126",
       f"{VN.so_mb(2485.6)} · {VN.so_mb(126.3)}")
    # LỖI CỦA PHÉP THỬ, ghi lại để không ai lặp: bản đầu của mục này hỏi
    # *"nhãn/tooltip/hộp còn dấu phẩy không"*. SAI — với `thieu=['torch']` thì
    # phép `', '.join` chỉ có MỘT phần tử nên câu KHÔNG có dấu phẩy nào một
    # cách hoàn toàn chính đáng (câu dùng "—" và ":"), và 4 mục ĐỎ OAN. Cái
    # cần canh là BẤT BIẾN CẤU TRÚC: chỉ `so_mb` được phép đổi dấu nghìn.
    _xau_replace: list[str] = []
    for _n in ast.walk(_cay_vn):
        if not (isinstance(_n, ast.FunctionDef) and _n.name != "so_mb"):
            continue
        for _c in ast.walk(_n):
            if isinstance(_c, ast.Call) \
                    and isinstance(_c.func, ast.Attribute) \
                    and _c.func.attr == "replace" \
                    and [getattr(a, "value", None) for a in _c.args] \
                    == [",", "."]:
                _xau_replace.append(_n.name)
    ok("12l''' CHỈ `so_mb` được đổi dấu nghìn — không hàm nào khác gọi "
       "`.replace(\",\", \".\")` (gọi trên CẢ CÂU thì dấu phẩy tiếng Việt "
       "thành dấu chấm: lượt chạy thật in ra «khoảng 126 MB. tải 1 lần»)",
       not _xau_replace, f"còn ở: {sorted(set(_xau_replace))}")
    # Mặt DƯƠNG: nhãn có dấu phẩy THẬT (2 gói -> `', '.join`) phải giữ được nó.
    _nh_2 = VN.nhan_tai_nhan_ban(["torch", "torchaudio"])
    ok("12l'''' nhãn 2 gói giữ nguyên dấu phẩy của `', '.join`",
       "torch, torchaudio" in _nh_2, _nh_2[:60])
    h3.close()

    # THIẾU PYTHON 3 -> KHOÁ NÚT **VÀ NÓI VÌ SAO**. Nút xám không một lời là
    # câu đố (bài học cổng 58/16/51), mà đây là ca rất dễ gặp: bản `.exe`
    # không mang Python.
    _that_pyht = VN._python_he_thong
    VN._python_he_thong = lambda: ""            # type: ignore[assignment]
    try:
        h4 = HopGiongToi()
        h4.show()
        ok("12m thiếu Python 3 -> nút vẫn HIỆN nhưng bị KHOÁ",
           h4.b_tai_nb.isVisible() and not h4.b_tai_nb.isEnabled(),
           f"hiện={h4.b_tai_nb.isVisible()} bật={h4.b_tai_nb.isEnabled()}")
        ok("12n ... VÀ nói vì sao ngay trên nhãn (Python)",
           "Python" in h4.lb_nb.text(), h4.lb_nb.text()[-90:])
        # bấm vào nút đã khoá (gọi thẳng handler) cũng KHÔNG được tải bừa
        _ghi_hop.clear()
        h4._tai_nhan_ban()
        ok("12n' gọi thẳng handler lúc chưa cài được -> KHÔNG bắt đầu tải",
           not h4._dang_cai_nb)
        h4.close()
    finally:
        VN._python_he_thong = _that_pyht        # type: ignore[assignment]
finally:
    NB.thieu_de_nhan_ban = _that_thieu2         # type: ignore[assignment]

# BỘ DÒ NÉM -> HỘP KHÔNG ĐƯỢC CHẾT, và phải nghiêng về HIỆN nút (ẩn nút chính
# là cách tính năng đã chết một lần).
_that_ttnb = VN.tinh_trang_nhan_ban


def _no_tung(*_a, **_k):
    raise RuntimeError("ổ mạng rút giữa lượt dò")


VN.tinh_trang_nhan_ban = _no_tung               # type: ignore[assignment]
try:
    _loi_dung = ""
    try:
        h5 = HopGiongToi()
        h5.show()
        _hien5, _nhan5 = h5.b_tai_nb.isVisible(), h5.lb_nb.text()
        h5.close()
    except Exception as e:                                     # noqa: BLE001
        _loi_dung = f"{type(e).__name__}: {e}"
        _hien5, _nhan5 = False, ""
    ok("12o bộ dò NÉM -> hộp vẫn dựng được, KHÔNG chết", not _loi_dung,
       _loi_dung[:90])
    ok("12p ... và nghiêng về HIỆN nút (ẩn nút là cách tính năng đã chết)",
       _hien5, f"hiện={_hien5}")
    ok("12q ... và NÓI RA là chưa dò được", "dò được" in _nhan5,
       _nhan5[:90])
finally:
    VN.tinh_trang_nhan_ban = _that_ttnb         # type: ignore[assignment]

# ═══ CỐ Ý KHÔNG dựng lại combo sau khi tải xong ═══
# `_dung_combo_giong` đặt lại combo theo giá trị ĐÃ LƯU, nên gọi nó ở đây là
# NUỐT MẤT giọng user vừa bấm mà chưa lưu — đúng họ lỗi "chọn X ra Y".
# `_tai_gh_xong` và `_tai_kokoro_xong` đã cố ý không gọi; hàng này phải giống.
_goi_combo = any(
    isinstance(c, ast.Attribute) and c.attr == "_dung_combo_giong"
    for c in _than_ham(cay_ui, "_tai_nhan_ban_xong"))
ok("12s `_tai_nhan_ban_xong` CỐ Ý KHÔNG gọi `_dung_combo_giong` (hàm đó đọc "
   "giá trị ĐÃ LƯU nên nuốt lựa chọn user vừa bấm — họ lỗi 'chọn X ra Y')",
   not _goi_combo)
ok("12s' ... mà VẪN nạp lại danh sách (`_nap`) để tiền tố 'CHƯA CHẠY ĐƯỢC' "
   "biến đi",
   any(isinstance(c, ast.Attribute) and c.attr == "_nap"
       for c in _than_ham(cay_ui, "_tai_nhan_ban_xong")))
ok("12s'' TỰ KIỂM BỘ DÒ: hàm CÓ gọi `_dung_combo_giong` thì phải BỊ BẮT",
   any(isinstance(c, ast.Attribute) and c.attr == "_dung_combo_giong"
       for c in _than_ham(
           ast.parse("def f(self):\n    self._dung_combo_giong()\n"), "f")))

# `cai_nhan_ban` KHÔNG BAO GIỜ NÉM — kể cả khi không có môi trường nào.
os.environ["BQ_VN_PYTHON"] = str(T / "khong_he_co_python.exe")
_that_pv = VN._python_vieneu
VN._python_vieneu = lambda: ("", ["VieNeu"], ())   # type: ignore[assignment]
try:
    _r_cai = VN.cai_nhan_ban()
    ok("12r `cai_nhan_ban` không có môi trường -> trả {ok:False, loi} chứ "
       "KHÔNG NÉM", isinstance(_r_cai, dict) and _r_cai.get("ok") is False
       and len(str(_r_cai.get("loi") or "")) > 15,
       str(_r_cai.get("loi"))[:80])
    ok("12r' ... và lời lẽ nói được phải làm gì (nêu VieNeu hoặc Python)",
       any(k in str(_r_cai.get("loi") or "") for k in ("VieNeu", "Python")),
       str(_r_cai.get("loi"))[:60])
finally:
    VN._python_vieneu = _that_pv                # type: ignore[assignment]
    os.environ.pop("BQ_VN_PYTHON", None)

# ---------------------------------------------------------------------------
print("\n[CA 13] VÒNG TỰ DÒ — bóc tên gói từ lời lỗi, CHẶN, TRẦN vòng")
# ---------------------------------------------------------------------------
# Vì sao CA này tồn tại: hậu kiểm TĨNH chỉ nói "5 gói tôi BIẾT đều có mặt".
# Trên máy anh Hùng, `import vieneu` VÀ `import vieneu.v3turbo` đều THÀNH CÔNG
# trong khi `transformers` thiếu — gói nạp nó LƯỜI. Nên chỉ ĐỌC THẬT nói thật.
ok("13a bóc đúng tên gói từ ModuleNotFoundError",
   VN._ten_thieu("ModuleNotFoundError: No module named 'transformers'")
   == "transformers")
ok("13b lấy gói GỐC, không lấy module con (pip cài theo gói phát hành)",
   VN._ten_thieu("No module named 'neucodec.models.x'") == "neucodec")
ok("13c lời lỗi KHÔNG phải thiếu gói -> trả '' (đừng cài bừa)",
   VN._ten_thieu("RuntimeError: CUDA out of memory") == "")
# Lời lỗi là chuỗi từ TIẾN TRÌNH CON -> đưa thẳng vào dòng lệnh pip là một cửa
# tiêm lệnh. Tên rác phải bị loại HẲN, không được "làm sạch rồi vẫn cài".
for _rac in ("../../evil", "a b; rm -rf /", "x&&calc", "'; DROP TABLE"):
    ok(f"13d tên RÁC bị loại: {_rac[:18]}", VN._ten_thieu(
        f"No module named '{_rac}'") == "", VN._ten_thieu(
        f"No module named '{_rac}'"))
ok("13e tên-import khác tên-pip thì ánh xạ (sklearn -> scikit-learn)",
   VN._ten_pip("sklearn") == "scikit-learn")
ok("13e' không biết thì thử ĐÚNG TÊN, không đoán bừa "
   "(đoán ra một gói LẠ mang đúng tên đó, tệ hơn báo lỗi)",
   VN._ten_pip("neucodec") == "neucodec")
# DANH SÁCH CHẶN: mỗi tên phải có LÝ DO đọc được, không phải một set trơn.
for _c, _vi in (("gradio", "web"), ("lmdeploy", "máy chủ"),
                ("triton", "Windows"), ("triton_windows", "Windows"),
                ("llama_cpp", "Windows"), ("fitz", "PDF")):
    ok(f"13f CHẶN `{_c}` và NÓI RA lý do", bool(VN._bi_chan(_c)),
       VN._bi_chan(_c)[:52])


def _bi_chan_nao(ten_ds) -> list[str]:
    """Tên nào trong `ten_ds` đang bị `_bi_chan` chặn. Dùng cho CẢ HAI chiều.

    MỘT hàm cho cả 13f' và 13f'' là CỐ Ý: mục đòi *"2 tên này PHẢI bị chặn"*
    chính là **TỰ KIỂM BỘ DÒ** của mục đòi *"danh sách cần KHÔNG bị chặn"*.
    Thiếu nó thì `_bi_chan` trả `""` cho MỌI thứ (đúng phép phá 23 "bỏ danh
    sách CHẶN") vẫn làm 13f' XANH — một mục xanh vì bộ dò đã chết.
    """
    return [t for t in ten_ds if VN._bi_chan(t)]


#: Tên gói dùng để GIẢ LẬP vòng tự dò (13i · 13m). **BẮT BUỘC không nằm trong
#: `_CHAN_TU_DO`.** Bản trước dùng `transformers`, rồi bản vá 20/08 chặn đúng
#: tên đó, và hai ca kia hoá ra đo sang nhánh CHẶN: 13i ĐỎ, còn **13m XANH VÌ
#: LÝ DO NGƯỢC HẲN** (nó sinh ra để đo nhánh "pip trả mã khác 0"). 13f' canh
#: chính điều kiện này nên chặn một trong ba tên dưới đây là **13f' đỏ TRƯỚC**,
#: không để 13i/13m đỏ mà không ai biết vì sao.
#: Ba tên đều tự-ánh-xạ qua `_ten_pip` (không có trong `_TEN_PIP`) nên pip GIẢ
#: của hộp cát so `cmd[-1]` được — đổi sang `sklearn` là hỏng phép thử.
_GOI_KHONG_CHAN = ("neucodec", "accelerate", "soundfile")

#: Gói mà LƯỢT CÀI CHÍNH đòi. Đọc từ `_goi_nhan_ban()` — cửa THẬT của lượt cài
#: — chứ KHÔNG chép tay danh sách: chép tay là dựng bản sao thứ hai, đúng cái
#: `_goi_nhan_ban` viết ra để tránh.
_CAN_THAT = tuple(VN._goi_nhan_ban())
_CHAN_OAN = _bi_chan_nao(_CAN_THAT + _GOI_KHONG_CHAN)
ok("13f' gói THẬT SỰ cần thì KHÔNG bị chặn — một tên vừa BẮT BUỘC (bước 1 "
   "khai là phải có) vừa BỊ CHẶN (vòng tự dò từ chối cài) là bế tắc theo cấu "
   "tạo, và `_bi_chan` dùng `startswith` nên rút khoá về `torch` là chặn cả "
   "`torchaudio`",
   _CHAN_OAN == [],
   f"cần={list(_CAN_THAT)} · giả lập={list(_GOI_KHONG_CHAN)} · "
   f"bị chặn oan={_CHAN_OAN}")
ok("13f'' ĐỐI XỨNG — BẤT BIẾN MỚI (bản vá 20/08): `torchcodec` VÀ "
   "`transformers` PHẢI bị chặn. Đây cũng là TỰ KIỂM BỘ DÒ của 13f': bộ dò "
   "chết thì mục này đỏ chứ không để 13f' xanh oan",
   _bi_chan_nao(("torchcodec", "transformers"))
   == ["torchcodec", "transformers"],
   f"bắt được={_bi_chan_nao(('torchcodec', 'transformers'))}")
ok("13f''' ... và lý do NÊU ĐÍCH DANH nguyên nhân ĐÃ ĐO, không phải một câu "
   "chung chung (torchcodec: cần FFmpeg dạng DLL CHIA SẺ mà app chỉ có "
   "ffmpeg.exe TĨNH · transformers: phụ thuộc KHAI BÁO của gói vieneu, đường "
   "nhân bản vẫn ra WAV 2,32s · RMS 0,09761 khi nó KHÔNG có mặt)",
   "DLL" in VN._bi_chan("torchcodec")
   and "vieneu" in VN._bi_chan("transformers"),
   VN._bi_chan("torchcodec")[:40] + " ¦ " + VN._bi_chan("transformers")[:40])
ok("13g có TRẦN vòng lặp (không trần = treo máy cả đêm trên đường mạng)",
   isinstance(VN.TRAN_VONG_DO, int) and 2 <= VN.TRAN_VONG_DO <= 10,
   f"{VN.TRAN_VONG_DO}")
# `do_wav` là BẰNG CHỨNG CUỐI CÙNG. `doc_loat` trả True chỉ nghĩa là "tiến
# trình chạy xong, file tồn tại" — cùng khoảng cách đã cho ffmpeg trả mã 0 với
# file 0 KiB.
_w_cam = T / "cam.wav"
with wave.open(str(_w_cam), "wb") as _w:
    _w.setnchannels(1)
    _w.setsampwidth(2)
    _w.setframerate(24000)
    _w.writeframes(b"\x00\x00" * 24000)        # 1 giây LẶNG HOÀN TOÀN
_d_cam = VN.do_wav(_w_cam)
ok("13h WAV dài 1 giây mà LẶNG -> `co_tieng` phải là False "
   "(đây đúng ca 'chạy xong mà câm')",
   _d_cam["giay"] >= 0.9 and not _d_cam["co_tieng"],
   f"dài {_d_cam['giay']}s · RMS {_d_cam['rms']}")
_w_keu = T / "keu.wav"
with wave.open(str(_w_keu), "wb") as _w:
    _w.setnchannels(1)
    _w.setsampwidth(2)
    _w.setframerate(24000)
    _w.writeframes(b"".join(
        int(9000 * math.sin(i * 0.15)).to_bytes(2, "little", signed=True)
        for i in range(24000)))
_d_keu = VN.do_wav(_w_keu)
ok("13h' ... còn WAV CÓ TIẾNG thì True (TỰ KIỂM BỘ DÒ: thiếu mục này thì "
   "'câm' có thể là bộ dò đã chết)",
   _d_keu["co_tieng"] and _d_keu["rms"] > 0.05,
   f"dài {_d_keu['giay']}s · RMS {_d_keu['rms']}")
ok("13h'' file không đọc được -> 0.0, KHÔNG NÉM",
   VN.do_wav(T / "khong-he-co.wav")["giay"] == 0.0)

# ── VÒNG TỰ DÒ CHẠY THẬT, bằng cách VÁ `_chay_vieneu` để GIẢ LẬP lỗi ──
# Đây là mục có RĂNG nhất của CA: nó chấm chính cái VÒNG, không chấm mấy hàm
# con. Giả lập đúng cảnh anh Hùng gặp: vá 2 tên thì lộ tên thứ 3.
_that_cv = VN._chay_vieneu
_that_ctd = VN._chay_theo_dong
_that_mau = VN._mau_thu
_that_dw = VN.do_wav
_that_tnb = VN.thieu_nhan_ban
_that_pvn = VN._python_vieneu


def _dung_gia_lap(thieu_dan: list[str], **kw):
    """Dựng hộp cát cho vòng tự dò: pip GIẢ, đọc GIẢ lỗi theo danh sách."""
    _da_cai: list[str] = []
    _con = list(thieu_dan)

    def _cv(items, py, voice, ref, han, on_msg):
        # ĐÒI ĐÚNG ĐƯỜNG NHÂN BẢN: `voice=""` + `ref_audio=<file mẫu>`.
        # Không kiểm hai tham số này thì phép phá "đi đường giọng DỰNG SẴN"
        # LỌT — đo được ở lượt phá đầu (phép 25). Đường dựng sẵn KHÔNG đụng
        # torch nên lượt tự kiểm sẽ XANH OAN.
        if voice or not ref:
            return {"ok": False, "_sandbox": "",
                    "loi": ("SAI ĐƯỜNG: vòng tự dò phải đi đường NHÂN BẢN "
                            f"(voice='' + ref_audio=...), nhận voice={voice!r} "
                            f"ref={ref!r}")}
        if _con:
            return {"ok": False, "_sandbox": "",
                    "loi": ("Traceback...\nModuleNotFoundError: No module "
                            f"named '{_con[0]}'")}
        return {"ok": True, "_sandbox": "",
                "ra": [{"i": 0, "p": items[0]["raw"]}]}

    def _ctd(cmd, han, prog=None, lo=0.0, hi=0.9, nhip=900.0):
        # pip GIẢ: gói cuối dòng lệnh chính là gói đang cài.
        goi = cmd[-1]
        _da_cai.append(goi)
        # Pop **kể cả khi `ma_pip != 0`** — cố ý, và có hệ quả đáng biết: gỡ
        # chốt "pip trả mã khác 0" (phép phá 34) làm lượt chạy HOÁ RA THÀNH
        # CÔNG ở vòng sau, nên 13m đỏ ở vế `ok is False` chứ không ở vế lời
        # lỗi. Không đụng vào đây: 13m' đo lời lỗi, 13m'' đo `tu_do`, cả hai
        # vẫn chấm đúng nhánh, còn sửa cái pop này là đổi hành vi của 13i/13j.
        if _con and goi == _con[0]:
            _con.pop(0)
        # `ma_pip` CHỈ áp cho lượt pip của VÒNG TỰ DÒ, không áp cho lượt cài
        # CHÍNH ở bước 1. Bản đầu của mục này áp cho cả hai -> `cai_nhan_ban`
        # chết ngay bước 1 và lời lỗi nêu `accelerate` (gói CUỐI danh sách
        # chính) chứ không phải gói tự dò -> mục 13m ĐỎ vì **lỗi của phép thử**,
        # không phải lỗi của mã. Lượt cài chính là lượt DUY NHẤT có `--upgrade`.
        if "--upgrade" in cmd:
            return 0, [f"Successfully installed {goi}"]
        return kw.get("ma_pip", 0), [f"Successfully installed {goi}"]

    VN._chay_vieneu = _cv                       # type: ignore[assignment]
    VN._chay_theo_dong = _ctd                   # type: ignore[assignment]
    VN._mau_thu = lambda d: str(_w_keu)         # type: ignore[assignment]
    # Đọc "thành công" -> trả WAV CÓ TIẾNG; hỏng -> file không có.
    VN.do_wav = lambda p: (_that_dw(_w_keu) if not _con     # type: ignore
                           else {"giay": 0.0, "rms": 0.0, "co_tieng": False})
    VN.thieu_nhan_ban = lambda: []              # type: ignore[assignment]
    VN._python_vieneu = lambda: (               # type: ignore[assignment]
        str(_py_gia), [], (3, 2, 8))
    return _da_cai


# python GIẢ chỉ cần TỒN TẠI (`cai_nhan_ban` dò bằng `is_file`)
_py_gia = T / "venvgia" / "Scripts" / "python.exe"
_py_gia.parent.mkdir(parents=True, exist_ok=True)
_py_gia.write_bytes(b"")
try:
    # (1) thiếu 2 tên rồi lộ tên thứ 3 -> phải cài CẢ BA rồi mới xong.
    # Tên lấy từ `_GOI_KHONG_CHAN`, KHÔNG ghi tay: danh sách cũ mở đầu bằng
    # `transformers` nên từ bản vá 20/08 nó dừng ở nhánh CHẶN ngay vòng 1 và ca
    # này thôi đo cái nó muốn đo (đo được: ok=False · tự cài=[] · vòng=1).
    _cai = _dung_gia_lap(list(_GOI_KHONG_CHAN))
    _r = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
    ok("13i vòng tự dò: lỗi 'No module named X' -> CÀI X rồi THỬ LẠI, "
       "lộ tên thứ 3 vẫn đi tiếp",
       _r.get("ok") is True and _r.get("tu_do") == list(_GOI_KHONG_CHAN),
       f"ok={_r.get('ok')} · tự cài={_r.get('tu_do')} · vòng={_r.get('vong')}")
    ok("13i' ... và bằng chứng cuối là WAV CÓ TIẾNG (độ dài + RMS)",
       bool(_r.get("doc_thu", {}).get("co_tieng") is None
            or _r.get("doc_thu", {}).get("rms", 0) > 0.05),
       str(_r.get("doc_thu"))[:70])

    # (2) HẾT TRẦN -> ok=False và NÊU RÕ còn thiếu gì
    _dung_gia_lap([f"goi{i}" for i in range(VN.TRAN_VONG_DO + 3)])
    _r2 = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
    ok("13j hết TRẦN -> ok=False, KHÔNG lặp vô tận",
       _r2.get("ok") is False and _r2.get("vong") == VN.TRAN_VONG_DO,
       f"ok={_r2.get('ok')} · vòng={_r2.get('vong')}")
    ok("13j' ... và lời lỗi NÊU ĐÍCH DANH gói còn thiếu",
       "goi" in str(_r2.get("loi") or ""), str(_r2.get("loi"))[:90])

    # (3) tên trong danh sách CHẶN -> KHÔNG được cài, phải nói lý do
    _cai3 = _dung_gia_lap(["gradio"])
    _r3 = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
    ok("13k gói trong danh sách CHẶN -> KHÔNG cài",
       _r3.get("ok") is False and not any("gradio" in c for c in _cai3),
       f"ok={_r3.get('ok')} · đã cài={_cai3}")
    ok("13k' ... và nói RA lý do chặn", "giao diện web"
       in str(_r3.get("loi") or ""), str(_r3.get("loi"))[:90])

    # (3b) ĐỐI XỨNG với 13f'', nhưng ở mức VÒNG chứ không mức dict. Dict đúng
    # mà vòng vẫn đi cài thì bản vá 20/08 chỉ là trang trí — `_bi_chan` dùng
    # `startswith` nên một khoá viết sai vẫn "có mặt" trong dict mà không khớp
    # tên thật. Đây là vế GỌI THẬT của cặp AST/dict + chạy thật.
    for _tc, _khoa in (("torchcodec", "DLL"), ("transformers", "vieneu")):
        _cai_x = _dung_gia_lap([_tc])
        _rx = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
        ok(f"13k'' vòng tự dò đòi `{_tc}` -> KHÔNG cài, và nêu lý do ĐÃ ĐO",
           _rx.get("ok") is False and _rx.get("bi_chan") == _tc
           and _khoa in str(_rx.get("bi_chan_vi") or "")
           and not any(_tc in c for c in _cai_x),
           f"bị chặn={_rx.get('bi_chan')} · đã cài={_cai_x} · "
           f"vì={str(_rx.get('bi_chan_vi'))[:44]}")

    # (4) "cài đủ danh sách mà ĐỌC vẫn hỏng" -> ĐỎ. ĐÚNG CẢNH ANH HÙNG GẶP.
    _dung_gia_lap(["transformers"])
    VN._chay_vieneu = lambda *a, **k: {         # type: ignore[assignment]
        "ok": False, "_sandbox": "",
        "loi": "RuntimeError: model chưa tải xong"}
    _r4 = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
    ok("13l 'cài đủ danh sách nhưng ĐỌC THẬT vẫn hỏng' -> ok=False "
       "(hậu kiểm tĩnh xanh mà đọc đỏ = đúng cảnh anh Hùng gặp)",
       _r4.get("ok") is False and "ĐỌC THẬT" in str(_r4.get("loi") or ""),
       str(_r4.get("loi"))[:90])

    # (5) pip trả mã KHÁC 0 -> báo thẳng, đừng mừng.
    # ═══ MỤC NÀY TỪNG **XANH VÌ LÝ DO NGƯỢC HẲN** (20/08/2026) ═══
    # Bản trước giả lập thiếu `transformers`. Từ lúc tên đó vào `_CHAN_TU_DO`,
    # vòng dừng ở nhánh CHẶN **trước khi** chạm tới lượt pip nào, nên lời lỗi
    # là *"nằm trong danh sách CHẶN"* — vẫn `ok=False`, vẫn CHỨA tên gói, nên
    # mục ĐẠT trong khi nhánh nó sinh ra để đo (`ma2 != 0`) KHÔNG hề chạy. Một
    # mục xanh vì lý do ngược hẳn còn tệ hơn một mục đỏ: nó phát chứng nhận.
    # Nay dùng tên KHÔNG bị chặn, và 13m'/13m'' đòi ĐÚNG nhánh đó chạy.
    _goi5 = _GOI_KHONG_CHAN[0]
    _cai5 = _dung_gia_lap([_goi5], ma_pip=1)
    _r5 = VN.cai_nhan_ban(han_giay=30, ban_cuda=False)
    _loi5 = str(_r5.get("loi") or "")
    ok("13m pip trả mã khác 0 khi cài gói tự dò -> ok=False, nêu tên gói",
       _r5.get("ok") is False and _goi5 in _loi5, _loi5[:90])
    ok("13m' CHỐT CHỐNG PASS OAN: lời lỗi nói ĐÚNG BỆNH (`pip trả mã 1`) và "
       "KHÔNG phải nhánh CHẶN — đọc mỗi 'ok=False + có tên gói' thì hai nhánh "
       "khác hẳn nhau trông y như nhau",
       "pip trả mã 1" in _loi5 and _r5.get("bi_chan") is None
       and "CHẶN" not in _loi5,
       f"vòng={_r5.get('vong')} · bị chặn={_r5.get('bi_chan')!r}")
    ok("13m'' ... và pip THẬT SỰ được gọi cho gói đó (chứng minh nhánh có "
       "chạy) trong khi gói đó KHÔNG được đếm vào `tu_do` (pip hỏng mà kể là "
       "đã cài thì lượt sau bỏ qua nó vĩnh viễn)",
       _goi5 in _cai5 and _r5.get("tu_do") == [],
       f"pip đã gọi={_cai5} · tự cài={_r5.get('tu_do')}")
finally:
    VN._chay_vieneu = _that_cv                  # type: ignore[assignment]
    VN._chay_theo_dong = _that_ctd              # type: ignore[assignment]
    VN._mau_thu = _that_mau                     # type: ignore[assignment]
    VN.do_wav = _that_dw                        # type: ignore[assignment]
    VN.thieu_nhan_ban = _that_tnb               # type: ignore[assignment]
    VN._python_vieneu = _that_pvn               # type: ignore[assignment]

# ---------------------------------------------------------------------------
print("\n[CA 14] NÚT TẢI BỘ VieNeu — chuỗi KHÔNG được đứt ở đây")
# ---------------------------------------------------------------------------
# Ca thứ SÁU của "hàm xong ≠ tính năng xong": `cai_vieneu()` có sẵn mà
# `grep -rn "cai_vieneu" app/ui/` ra 0 dòng -> nút nhân bản ghi "tải bộ đó
# trước" mà KHÔNG có chỗ nào để bấm.
_ui_src = Path("app/ui/thay_giong_dialog.py").read_text(
    encoding="utf-8", errors="replace")
ok("14a UI GỌI `cai_vieneu` (mệnh đề trung tâm của CA này)",
   "cai_vieneu" in _ui_src, f"{_ui_src.count('cai_vieneu')} chỗ")
ok("14a' ... và gọi qua AST chứ không phải chỉ nằm trong ghi chú",
   "cai_vieneu" in _ma_that(Path("app/ui/thay_giong_dialog.py")))
ok("14b nhãn nút nêu SỐ MB và lấy từ `mb_vieneu()` (một phép đo, ba chỗ đọc)",
   str(int(VN.mb_vieneu())) in VN.nhan_tai_vieneu([]),
   VN.nhan_tai_vieneu([])[:70])
ok("14b' ca CẬP NHẬT (bản quá cũ) trông KHÁC ca chưa có gì",
   VN.nhan_tai_vieneu(["vieneu >= 3.2.8 (đang có 3.1.0)"])
   != VN.nhan_tai_vieneu(["vieneu"]),
   VN.nhan_tai_vieneu(["vieneu >= 3.2.8 (đang có 3.1.0)"])[:60])
ok("14c nhãn nút KHÔNG EMOJI", not _co_emoji(VN.NHAN_TAI)
   and not _co_emoji(VN.nhan_tai_vieneu([])),
   "".join(_co_emoji(VN.NHAN_TAI + VN.nhan_tai_vieneu([]))))
ok("14d thiếu Python 3 -> NÓI RA vì sao (nút xám không một lời là câu đố)",
   "Python 3" in VN.vi_sao_khong_cai_vieneu()
   or VN.vi_sao_khong_cai_vieneu() == "",
   VN.vi_sao_khong_cai_vieneu()[:60])

_that_phs = VN._python_he_thong
try:
    VN._python_he_thong = lambda: ""            # type: ignore[assignment]
    ok("14d' máy KHÔNG có Python 3 -> `cai_duoc` False VÀ có lý do",
       VN.tinh_trang_vieneu()["cai_duoc"] is False
       and "Python 3" in VN.vi_sao_khong_cai_vieneu())
    _r6 = VN.cai_vieneu()
    ok("14e `cai_vieneu` không có Python -> trả ok=False chứ KHÔNG NÉM",
       isinstance(_r6, dict) and _r6.get("ok") is False
       and "Python 3" in str(_r6.get("loi") or ""),
       str(_r6.get("loi"))[:70])
finally:
    VN._python_he_thong = _that_phs             # type: ignore[assignment]

# Nút bám `thieu`, KHÔNG bám `co` — bám `co` thì máy dev nút BIẾN MẤT và bản
# `.exe` mãi mãi không có đường tải (đã sập 2 lần: cổng 58, hàng Kokoro).
_ui_ast = _ma_that(Path("app/ui/thay_giong_dialog.py"))
ok("14f nút bước 1 bám `thieu` (có nhánh đọc `thieu` trong `_do_vieneu`)",
   "_do_vieneu" in _ui_ast and "thieu" in _ui_ast)
ok("14g tiến độ đi qua dict RIÊNG `_buoc_vieneu`, không dùng chung với "
   "bước 2 (dùng chung là hai lượt ghi lẫn số của nhau)",
   "_buoc_vieneu" in _ui_ast and "_buoc_nhan_ban" in _ui_ast)
ok("14h có tín hiệu riêng `_vn_xong` (thread nền KHÔNG đụng widget — "
   "luật shutdown.safe_emit, gốc 8 lần crash 0xc0000005)",
   "_vn_xong" in _ui_ast)
# Hỏi ĐÚNG CHỖ GỌI, không hỏi "chuỗi `da_dong_y` có trong file không": chuỗi
# đó còn nằm ở chính `def _tai_nhan_ban(self, da_dong_y=...)` nên gỡ LỜI GỌI mà
# mục vẫn xanh — đo được ở lượt phá đầu (phép 28 LỌT).
_than_vnx = _ui_src.split("def _tai_vieneu_xong")[1].split("\n    def ")[0]
ok("14i NỐI CHUỖI: `_tai_vieneu_xong` GỌI bước 2 với `da_dong_y=True` "
   "(máy trắng bấm một lần phải đi hết)",
   "self._tai_nhan_ban(da_dong_y=True)" in _than_vnx)
ok("14j ... mà mặc định `da_dong_y` VẪN LÀ False (một tham số mặc-định-True "
   "là cách 'app tự tải 2,5 GB sau lưng' lẻn vào)",
   "def _tai_nhan_ban(self, da_dong_y: bool = False)" in _ui_src)
ok("14k `_tai_vieneu_xong` CỐ Ý KHÔNG gọi `_dung_combo_giong` (hàm đó đọc "
   "giá trị ĐÃ LƯU nên nuốt lựa chọn user vừa bấm)",
   "_dung_combo_giong" not in _ui_src.split("def _tai_vieneu_xong")[1]
   .split("def ")[0])

# Đường dẫn python GIẢ nằm trong %TEMP%, đúng cảnh máy anh Hùng
# (`%TEMP%\bq_giong8\venv`). Dựng ở ĐÂY vì cả CA 14 lẫn CA 15 đều dùng.
_tam_gia = str(Path(tempfile.gettempdir()) / "bq_giong8" / "venv" /
               "Scripts" / "python.exe")

# ═══ BEHAVIOURAL: DỰNG HỘP THẬT rồi hỏi cái NÚT, không đọc mặt chữ ═══
# Mấy mục trên quét mã; mấy mục dưới BẤM. Chỉ quét mã thì một lượt "dọn gọn"
# đổi luồng mà chuỗi vẫn đứt, cổng vẫn xanh.
_that_ttvn = VN.tinh_trang_vieneu
try:
    # (a) THIẾU bộ VieNeu -> nút phải HIỆN (đây là ca máy TRẮNG)
    VN.tinh_trang_vieneu = lambda: {            # type: ignore[assignment]
        "co": False, "thieu": ["vieneu"], "python": "", "phien_ban": "",
        "so_giong": 20, "thu_muc": str(VN.thu_muc_vieneu()), "o_tam": "",
        "cai_duoc": True}
    h5 = HopGiongToi()
    h5.show()
    ok("14l máy TRẮNG (thiếu bộ VieNeu) -> nút tải bộ VieNeu HIỆN "
       "(trước lượt này KHÔNG có nút nào -> chuỗi ĐỨT)",
       h5.b_tai_vn.isVisible() and h5.b_tai_vn.isEnabled(),
       f"hiện={h5.b_tai_vn.isVisible()} · bật={h5.b_tai_vn.isEnabled()}")
    ok("14l' ... và nhãn nói rõ đang ở BƯỚC NÀO",
       "BƯỚC 1" in h5.lb_vn.text(), h5.lb_vn.text()[:60])
    h5.close()

    # (b) ĐỦ -> ẩn nút (nhưng xem 15g: cảnh báo %TEMP% vẫn phải hiện)
    VN.tinh_trang_vieneu = lambda: {            # type: ignore[assignment]
        "co": True, "thieu": [], "python": "x", "phien_ban": "3.2.8",
        "so_giong": 20, "thu_muc": str(VN.thu_muc_vieneu()), "o_tam": "",
        "cai_duoc": True}
    h6 = HopGiongToi()
    h6.show()
    ok("14m đã có bộ VieNeu -> nút ẨN", not h6.b_tai_vn.isVisible())
    h6.close()

    # (c) KHÔNG có Python 3 -> nút VẪN HIỆN nhưng KHOÁ, và NÓI VÌ SAO.
    # Ẩn nút là cách tính năng đã chết một lần; nút xám không một lời là câu đố.
    VN.tinh_trang_vieneu = lambda: {            # type: ignore[assignment]
        "co": False, "thieu": ["vieneu"], "python": "", "phien_ban": "",
        "so_giong": 20, "thu_muc": str(VN.thu_muc_vieneu()), "o_tam": "",
        "cai_duoc": False}
    _that_pht2 = VN._python_he_thong
    VN._python_he_thong = lambda: ""            # type: ignore[assignment]
    try:
        h7 = HopGiongToi()
        h7.show()
        ok("14n thiếu Python 3 -> nút VẪN HIỆN nhưng bị KHOÁ",
           h7.b_tai_vn.isVisible() and not h7.b_tai_vn.isEnabled(),
           f"hiện={h7.b_tai_vn.isVisible()} · bật={h7.b_tai_vn.isEnabled()}")
        ok("14n' ... VÀ nói vì sao ngay trên nhãn (Python)",
           "Python 3" in h7.lb_vn.text(), h7.lb_vn.text()[-90:])
        _truoc = len(_ghi_hop)
        h7._tai_vieneu()
        ok("14n'' bấm lúc chưa cài được -> KHÔNG bắt đầu tải",
           not h7._dang_cai_vn)
        h7.close()
    finally:
        VN._python_he_thong = _that_pht2        # type: ignore[assignment]

    # (d) bộ dò NÉM -> hộp KHÔNG chết và nghiêng về HIỆN nút
    def _nem():
        raise RuntimeError("ổ mạng rút")
    VN.tinh_trang_vieneu = _nem                 # type: ignore[assignment]
    h8 = HopGiongToi()
    h8.show()
    ok("14o bộ dò NÉM -> hộp vẫn dựng được, KHÔNG chết", True)
    ok("14p ... và nghiêng về HIỆN nút (ẩn nút là cách tính năng đã chết)",
       h8.b_tai_vn.isVisible())
    ok("14q ... và NÓI RA là chưa dò được", "CHƯA DÒ ĐƯỢC" in h8.lb_vn.text(),
       h8.lb_vn.text()[:70])
    h8.close()

    # (e) %TEMP%: máy VẪN chạy được (`thieu=[]`) nên nút ẩn — nhưng cảnh báo
    # PHẢI hiện ra. Đây là mục "bị BẮT, không phải chỉ ghi log".
    VN.tinh_trang_vieneu = lambda: {            # type: ignore[assignment]
        "co": True, "thieu": [], "python": _tam_gia, "phien_ban": "3.2.8",
        "so_giong": 20, "thu_muc": str(VN.thu_muc_vieneu()),
        "o_tam": VN.o_thu_muc_tam(_tam_gia), "cai_duoc": True}
    h9 = HopGiongToi()
    h9.show()
    ok("15g môi trường ở %TEMP% -> UI HIỆN cảnh báo dù `thieu` RỖNG "
       "(chỉ ghi log thì không ai đọc; một lượt Disk Cleanup là giọng biến "
       "khỏi combo)",
       "TẠM" in h9.lb_vn.text().upper() or "TEMP" in h9.lb_vn.text().upper(),
       h9.lb_vn.text()[-100:])
    h9.close()
finally:
    VN.tinh_trang_vieneu = _that_ttvn           # type: ignore[assignment]

# ---------------------------------------------------------------------------
print("\n[CA 15] MÔI TRƯỜNG Ở `%TEMP%` PHẢI BỊ BẮT, không chỉ ghi log")
# ---------------------------------------------------------------------------
# Bệnh: máy anh Hùng chạy VieNeu từ `%TEMP%\bq_giong8\venv`. Một lượt Disk
# Cleanup là **giọng biến khỏi combo**, và triệu chứng đó không ai lần ra.
# CLAUDE.md đã chữa đúng lớp bệnh này cho OmniVoice (7,74 GB trong %TEMP%).
ok("15a python nằm trong %TEMP% -> `o_thu_muc_tam` PHẢI kêu",
   bool(VN.o_thu_muc_tam(_tam_gia)), VN.o_thu_muc_tam(_tam_gia)[:70])
ok("15a' ... và nói ĐÚNG đường dẫn đang dùng (để còn lần ra)",
   "bq_giong8" in VN.o_thu_muc_tam(_tam_gia)
   or "Temp" in VN.o_thu_muc_tam(_tam_gia),
   VN.o_thu_muc_tam(_tam_gia)[:80])
ok("15b python ở CHỖ CHUẨN -> KHÔNG kêu oan (TỰ KIỂM BỘ DÒ)",
   not VN.o_thu_muc_tam(str(VN.thu_muc_vieneu() / "venv" / "Scripts" /
                            "python.exe")))
# `o_tam` để RIÊNG khỏi `thieu`: máy VẪN chạy được nên gộp vào là nhãn/nút báo
# sai trạng thái. Nhưng nó PHẢI hiện ra ở UI.
ok("15c `o_tam` là khoá RIÊNG, KHÔNG gộp vào `thieu`",
   "o_tam" in VN.tinh_trang_vieneu()
   and not any("Temp" in str(t) for t in VN.tinh_trang_vieneu()["thieu"]))
ok("15d UI HIỆN cảnh báo `o_tam` (chỉ ghi log thì không ai đọc)",
   "o_tam" in _ui_ast, "có nhánh đọc o_tam trong thay_giong_dialog")
# MÁY TRẮNG phải dựng môi trường ở CHỖ CHUẨN, không phải %TEMP%.
_cv_src = _ma_that(Path("app/core/giong_vieneu.py"))
ok("15e `cai_vieneu` dựng venv ở CHỖ CHUẨN (`thu_muc_vieneu`), "
   "KHÔNG ở %TEMP%",
   "thu_muc_vieneu" in _cv_src and "gettempdir" not in
   _cv_src.split("def cai_vieneu")[1].split("def ")[0])
# Ứng viên %TEMP% giữ ở CUỐI: máy nào còn bản cũ thì chạy được thay vì gãy,
# nhưng chỗ chuẩn phải được chọn TRƯỚC.
_uv = VN._ung_vien_python()
_i_tam = [i for i, p in enumerate(_uv)
          if str(Path(tempfile.gettempdir())).lower() in str(p).lower()]
_i_chuan = [i for i, p in enumerate(_uv)
            if str(VN.thu_muc_vieneu()).lower() in str(p).lower()]
ok("15f ứng viên %TEMP% đứng SAU chỗ chuẩn trong `_ung_vien_python` "
   "(chỗ ĐÚNG trước, chỗ TẠM sau)",
   not (_i_tam and _i_chuan) or min(_i_chuan) < min(_i_tam),
   f"chuẩn ở {_i_chuan} · tạm ở {_i_tam} · tổng {len(_uv)}")

# ---------------------------------------------------------------------------
print("\n[CA 16] APP TỰ DỜI MÔI TRƯỜNG RA KHỎI `%TEMP%`")
# ---------------------------------------------------------------------------
# CA 15 chấm "có KÊU không". Cổng này chấm "có CHỮA không" — vì kêu suốt một
# tuần mà `%TEMP%\bq_giong8\venv` (43.702 file / 1.411 MB) vẫn nằm nguyên đó.
# Đây là chỗ DỄ LÀM MẤT DỮ LIỆU nhất của cả file, nên mọi ca dưới đây đều hỏi
# thêm MỘT câu: *sau lượt đó máy còn chạy được không.*


def _dung_venv_gia(d: Path) -> None:
    """venv GIẢ: đủ file để `_python_vieneu()` nhận ra. Khuôn hộp cát của
    CA 12 — `_python_vieneu` dò bằng FILE CÓ TỒN TẠI KHÔNG (cố ý không
    `find_spec`), nên vài file RỖNG đúng tên là đủ, không phải chép GB nào."""
    sp = d / "Lib" / "site-packages"
    for t in VN._CAN_CO:
        p = sp / t
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    (sp / "vieneu-3.2.8.dist-info").mkdir(parents=True, exist_ok=True)
    (d / "Scripts").mkdir(parents=True, exist_ok=True)
    (d / "Scripts" / "python.exe").write_bytes(b"MZ" + b"\0" * 64)


def _wav_that(p: Path, giay: float) -> None:
    """WAV 16-bit CÓ TIẾNG thật (để `do_wav` đọc ra RMS khác 0)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"".join(
            (8000 if (i // 60) % 2 else -8000).to_bytes(2, "little", signed=True)
            for i in range(int(24000 * giay))))


_VN_DIR_CU = os.environ.get("BQ_VN_DIR")
_TAM_CU = tempfile.tempdir
_DOC_LOAT_THAT = VN.doc_loat
_DIA_THAT = VN._dia_trong_mb
_CPT_THAT = shutil.copytree
_XA_THAT = XA.don_thu_muc
try:
    _T16 = T / "ca16"
    _VNDIR = _T16 / "_giong_vieneu"
    _TAM16 = _T16 / "temp"
    _TAM16.mkdir(parents=True, exist_ok=True)
    # `thu_muc_vieneu()` chạy-nguồn trỏ THẲNG vào `<repo>/_giong_vieneu` THẬT
    # (chỉ bản `.exe` mới đọc DATA_DIR). Thiếu hai dòng này là cổng đo lên
    # chính môi trường VieNeu của máy — và CA 16 có ca XOÁ.
    os.environ["BQ_VN_DIR"] = str(_VNDIR)
    tempfile.tempdir = str(_TAM16)
    _NGUON = _TAM16 / "bq_giong8" / "venv"
    _DICH = _VNDIR / "venv"

    def _moi16() -> None:
        for d in (_NGUON.parent, _VNDIR):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        _dung_venv_gia(_NGUON)
        _VNDIR.mkdir(parents=True, exist_ok=True)

    def _gia_doc(kieu: str):
        """`doc_loat` giả. `ok` = đọc ra WAV có tiếng · `cam` = trả True mà
        WAV rỗng tiếng · `hong` = trả False."""
        def f(texts, paths, voice, **kw):
            if kieu == "hong":
                return [False], [[]]
            _wav_that(Path(paths[0]), 0.01 if kieu == "cam" else 1.0)
            return [True], [[]]
        return f

    # --- (a) chỗ chuẩn ĐÃ có venv -> KHÔNG LÀM GÌ -------------------------
    # Dựng ĐÚNG ca duy nhất chốt này thật sự chạy tới: chỗ chuẩn có venv nhưng
    # THIẾU FILE nên `_python_vieneu()` rơi xuống `%TEMP%`. Nếu chỗ chuẩn ĐỦ
    # file thì `o_tam` rỗng và ca sẽ ĐẠT vì một chốt KHÁC bắt hộ — đúng lỗi
    # "LỌT 6" của cổng 80 (*mục nào canh MỘT chốt thì phải đọc LÝ DO cụ thể*).
    _moi16()
    _dung_venv_gia(_DICH)
    (_DICH / "Lib" / "site-packages" / "librosa" / "__init__.py").unlink()
    _r = VN.doi_khoi_tam()
    ok("16a chỗ chuẩn ĐÃ có venv -> KHÔNG LÀM GÌ (`da_lam=False`)",
       not _r["da_lam"], _r["ly_do"][:60])
    ok("16a' ... và nói ĐÚNG LÝ DO đó (không phải chốt khác bắt hộ)",
       "ĐÃ có venv" in _r["ly_do"], _r["ly_do"][:70])
    ok("16a'' CHỐT CHỐNG ĐẠT-OAN: ca này máy THẬT SỰ đang ở %TEMP% "
       "(o_tam khác rỗng), nên chốt 'đã có venv' mới là chốt đang chạy",
       bool(VN.o_thu_muc_tam()), str(VN.o_thu_muc_tam())[:60])
    ok("16a''' ... và KHÔNG đè lên bản ở chỗ chuẩn", VN._co_venv(_DICH))
    ok("16a'''' ... và KHÔNG đụng bản %TEMP%", VN._co_venv(_NGUON))

    # --- (b) không ở %TEMP% / (c) công tắc tắt ----------------------------
    _moi16()
    _dung_venv_gia(_DICH)
    _r = VN.doi_khoi_tam()
    ok("16b máy KHÔNG chạy từ %TEMP% -> KHÔNG LÀM GÌ",
       not _r["da_lam"] and "KHÔNG nằm trong thư mục tạm" in _r["ly_do"],
       _r["ly_do"][:60])
    _moi16()
    os.environ["BQ_VN_KHONG_DOI"] = "1"
    _r = VN.doi_khoi_tam()
    ok("16c `BQ_VN_KHONG_DOI=1` -> KHÔNG LÀM GÌ (có công tắc tắt)",
       not _r["da_lam"], _r["ly_do"][:50])
    ok("16c' ... và KHÔNG đụng gì tới bản đang chạy", VN._co_venv(_NGUON))
    os.environ.pop("BQ_VN_KHONG_DOI", None)

    # --- (d) CA THÀNH CÔNG -----------------------------------------------
    _moi16()
    _so_truoc = VN._dem_cay(_NGUON)[0]
    VN.doc_loat = _gia_doc("ok")
    _r = VN.doi_khoi_tam()
    ok("16d chép được + chạy được -> ok=True", _r["ok"], str(_r["loi"])[:70])
    ok("16d' bản mới nằm ở CHỖ CHUẨN và dùng được",
       VN._co_venv(_DICH) and VN.tinh_trang_vieneu()["co"])
    ok("16d'' ... và python máy sẽ dùng chính là bản mới",
       VN._nam_trong(VN._python_vieneu()[0], _DICH),
       VN._python_vieneu()[0][-58:])
    ok("16d''' bản cũ trong %TEMP% MỚI bị xoá (bước 6, sau khi đã chứng minh)",
       not _NGUON.exists() and _r["da_dep_cu"])
    ok(f"16d'''' log/kết quả có SỐ FILE đã chép ({_r['so_file']})",
       _r["so_file"] == _so_truoc > 0, f"trước {_so_truoc}")
    ok(f"16d''''' bằng chứng là HAI CON SỐ đọc từ WAV, không phải cờ của "
       f"`doc_loat` (dài {_r['giay']}s · RMS {_r['rms']})",
       _r["giay"] > 0 and _r["rms"] > 0)

    # --- (e) BẢN MỚI KHÔNG ĐỌC ĐƯỢC -> giữ cũ, bỏ mới --------------------
    _moi16()
    VN.doc_loat = _gia_doc("hong")
    _r = VN.doi_khoi_tam()
    ok("16e bản mới KHÔNG đọc được -> ok=False", not _r["ok"] and _r["da_lam"],
       str(_r["loi"])[:60])
    ok("16e' BẢN CŨ CÒN NGUYÊN (tuyệt đối không để 'cả hai đều hỏng')",
       VN._co_venv(_NGUON))
    ok("16e'' bản vừa chép BỊ BỎ, không còn thư mục tên `venv` ở chỗ chuẩn",
       not _DICH.exists())
    ok("16e''' ... nên máy VẪN chạy được VieNeu (dò lại ra bản %TEMP%)",
       VN.tinh_trang_vieneu()["co"]
       and VN._nam_trong(VN._python_vieneu()[0], _NGUON))
    ok("16e'''' CHÉP chứ không MOVE: nguồn còn NGUYÊN VẸN số file",
       VN._dem_cay(_NGUON)[0] == _so_truoc,
       f"{VN._dem_cay(_NGUON)[0]} vs {_so_truoc}")

    # --- (f) WAV CÂM tuy `doc_loat` trả True ------------------------------
    # `doc_loat` trả True chỉ nghĩa là "tiến trình chạy xong, file tồn tại" —
    # cùng khoảng cách đã cho ffmpeg trả mã 0 với file 0 KiB.
    _moi16()
    VN.doc_loat = _gia_doc("cam")
    _r = VN.doi_khoi_tam()
    ok("16f `doc_loat` trả True mà WAV KHÔNG CÓ TIẾNG -> vẫn HỎNG",
       not _r["ok"], str(_r["loi"])[:60])
    ok("16f' ... và lời lỗi nêu ĐÚNG hai con số đã đo",
       "KHÔNG CÓ TIẾNG" in str(_r["loi"]), str(_r["loi"])[:80])
    ok("16f'' ... bản cũ vẫn CÒN NGUYÊN", VN._co_venv(_NGUON))

    # --- (g) DƯƠNG TÍNH GIẢ: bản chép THIẾU FILE --------------------------
    # Bản chép thiếu file thì `_python_vieneu()` LẶNG LẼ rơi xuống `%TEMP%`,
    # lượt đọc vẫn ra WAV có tiếng -> phép thử sẽ CẤP CHỨNG NHẬN CHO BẢN CŨ
    # rồi ta đi xoá đúng bản cũ đó. Đây là ca nguy hiểm nhất của cả CA 16.
    _moi16()
    VN.doc_loat = _gia_doc("ok")
    _sau16 = [0]

    def _cp_thieu(*a, **k):
        # `copytree` GỌI LẠI CHÍNH NÓ cho thư mục con và truyền POSITIONAL ->
        # stub `(src, dst, **k)` ném TypeError rồi bị đọc nhầm thành "chép
        # hỏng" (đã sập 1 lần khi viết ca này).
        _sau16[0] += 1
        try:
            _kq = _CPT_THAT(*a, **k)
        finally:
            _sau16[0] -= 1
        if _sau16[0] == 0:
            _p = Path(a[1]) / "Lib" / "site-packages" / "vieneu" / "v3turbo.py"
            if _p.exists():
                _p.unlink()
        return _kq

    shutil.copytree = _cp_thieu
    _r = VN.doi_khoi_tam()
    shutil.copytree = _CPT_THAT
    ok("16g bản chép THIẾU FILE -> BẮT ĐƯỢC, không cấp chứng nhận oan",
       not _r["ok"], str(_r["loi"])[:60])
    ok("16g' ... và lời lỗi nói đúng bệnh (chạy bằng python KHÁC)",
       "python KHÁC" in str(_r["loi"]), str(_r["loi"])[:90])
    ok("16g'' ... bản cũ CÒN NGUYÊN", VN._co_venv(_NGUON))

    # --- (h) ĐĨA / NGUỒN HỎNG -> KHÔNG BAO GIỜ NÉM ------------------------
    _moi16()
    VN._dia_trong_mb = lambda d: 1.0
    _r = VN.doi_khoi_tam()
    VN._dia_trong_mb = _DIA_THAT
    ok("16h đĩa đầy -> KHÔNG NÉM, trả loi", not _r["ok"] and bool(_r["loi"]))
    ok("16h' ... và nói ra CÒN BAO NHIÊU / CẦN BAO NHIÊU",
       "trống" in str(_r["loi"]) and "cần" in str(_r["loi"]),
       str(_r["loi"])[:80])
    ok("16h'' ... bản cũ CÒN NGUYÊN", VN._co_venv(_NGUON))

    _moi16()
    VN._dia_trong_mb = lambda d: -1.0
    _r = VN.doi_khoi_tam()
    VN._dia_trong_mb = _DIA_THAT
    ok("16h''' KHÔNG hỏi được đĩa (-1) -> ĐỪNG CHẶN (không đo được thì "
       "không phán) — lượt dời vẫn chạy tới cùng", _r["ok"], str(_r["loi"])[:60])

    _moi16()
    shutil.copytree = lambda *a, **k: (_ for _ in ()).throw(
        FileNotFoundError("nguồn biến mất giữa chừng"))
    _r = VN.doi_khoi_tam()
    shutil.copytree = _CPT_THAT
    ok("16i nguồn biến mất giữa chừng -> KHÔNG NÉM",
       not _r["ok"] and "chép hỏng" in str(_r["loi"]), str(_r["loi"])[:60])
    ok("16i' ... bản cũ CÒN NGUYÊN", VN._co_venv(_NGUON))
    ok("16i'' ... và KHÔNG bỏ lại thư mục chép dở nào ở chỗ chuẩn",
       not any(p.name.startswith(VN.TIEN_TO_MOI) for p in _VNDIR.iterdir()),
       str([p.name for p in _VNDIR.iterdir()])[:70])

    _moi16()
    shutil.rmtree(_NGUON.parent, ignore_errors=True)
    _r = VN.doi_khoi_tam()
    ok("16i''' không có môi trường nào -> KHÔNG NÉM, chỉ nói không có việc",
       not _r["da_lam"] and not _r["loi"], _r["ly_do"][:55])

    # --- (j) XOÁ PHẢI ĐI QUA `xoa_an_toan` -------------------------------
    _moi16()
    VN.doc_loat = _gia_doc("ok")
    _dem_xa = [0]

    def _xa_gian_diep(d, **k):
        _dem_xa[0] += 1
        return False                       # TỪ CHỐI -> không gì bị xoá

    XA.don_thu_muc = _xa_gian_diep         # type: ignore[assignment]
    _r = VN.doi_khoi_tam()
    XA.don_thu_muc = _XA_THAT              # type: ignore[assignment]
    # Bản cũ đã bị ĐỔI TÊN ở bước 5 nên `_NGUON` không còn — nhưng DỮ LIỆU thì
    # phải còn nguyên dưới tên `venv_cu_*`. Đòi `_NGUON.exists()` là đọc "đổi
    # tên" thành "đã xoá"; chính ca này bắt được nhầm lẫn đó khi viết cổng.
    _con_cu = [p for p in _NGUON.parent.iterdir()
               if p.name.startswith(VN.TIEN_TO_CU)]
    ok("16j lượt xoá ĐI QUA `xoa_an_toan.don_thu_muc` (vá nó thành TỪ CHỐI "
       "thì KHÔNG byte nào của bản cũ mất — nó chỉ bị đổi tên)",
       _dem_xa[0] > 0 and len(_con_cu) == 1 and VN._co_venv(_con_cu[0]),
       f"{_dem_xa[0]} lượt gọi · còn {[p.name for p in _con_cu]}")
    ok("16j' ... và `xoa_an_toan` từ chối cũng KHÔNG làm lượt dời hỏng "
       "(bản mới vẫn đứng, bản cũ chỉ tốn đĩa)", _r["ok"] and not _r["da_dep_cu"])
    shutil.rmtree(_NGUON.parent, ignore_errors=True)

    VN.doc_loat = _DOC_LOAT_THAT
finally:
    VN.doc_loat = _DOC_LOAT_THAT
    VN._dia_trong_mb = _DIA_THAT
    shutil.copytree = _CPT_THAT
    XA.don_thu_muc = _XA_THAT              # type: ignore[assignment]
    tempfile.tempdir = _TAM_CU
    os.environ.pop("BQ_VN_KHONG_DOI", None)
    if _VN_DIR_CU is None:
        os.environ.pop("BQ_VN_DIR", None)
    else:
        os.environ["BQ_VN_DIR"] = _VN_DIR_CU

# --- (k) QUÉT TĨNH bằng AST + TỰ KIỂM BỘ DÒ ------------------------------
_cay_vn2 = ast.parse((REPO / "app" / "core" / "giong_vieneu.py")
                     .read_text(encoding="utf-8"))


def _than(ten: str):
    for n in ast.walk(_cay_vn2):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    return None


def _co_rmtree(ten: str) -> bool:
    """Hàm này có gọi `shutil.rmtree` TRẦN không (đọc AST, không đọc chuỗi)."""
    n = _than(ten)
    return bool(n) and any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
        and c.func.attr == "rmtree" for c in ast.walk(n))


def _goi_trong(ten: str) -> set:
    n = _than(ten)
    return set() if n is None else {
        c.func.id for c in ast.walk(n)
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


for _h in ("doi_khoi_tam", "_bo_ban_moi", "_xoa_qua_cua", "don_job_mo_coi",
           "_than_doi_nen", "tu_doi_nen"):
    ok(f"16k `{_h}` KHÔNG gọi `shutil.rmtree` trần (đó là lớp bệnh đã xoá "
       f"sạch cây mã 19/08)", not _co_rmtree(_h))
# BỘ DÒ PHẢI CÓ RĂNG: `_don` là hàm CÓ `rmtree` thật (nó tự canh bằng chốt
# riêng). Bộ dò không bắt được nó thì 6 mục trên chỉ là con dấu.
ok("16k' TỰ KIỂM BỘ DÒ: bộ dò BẮT được `_don` (hàm thật sự có `rmtree`)",
   _co_rmtree("_don"))
ok("16k'' `_xoa_qua_cua` gọi `don_thu_muc` của `xoa_an_toan`",
   "don_thu_muc" in _ma_that(Path("app/core/giong_vieneu.py")))
ok("16l `doc_loat` THẬT SỰ GỌI `tu_doi_nen` (AST — ghi chú nhắc tên nó thì "
   "không tính; đây là chỗ duy nhất nối tính năng vào đường chạy thật)",
   "tu_doi_nen" in _goi_trong("doc_loat"))
ok("16l' TỰ KIỂM BỘ DÒ: hàm KHÔNG gọi thì bộ dò phải nói KHÔNG",
   "tu_doi_nen" not in _goi_trong("do_wav"))
ok("16l'' `doc_loat` ĐẾM lượt đọc đang chạy (để luồng dời đợi máy rảnh — "
   "đổi tên venv lúc python của nó đang chạy là Windows từ chối)",
   {"_vao_doc", "_ra_doc"} <= _goi_trong("doc_loat"))

# --- (m) luồng nền: 1 lần/tiến trình, KHÔNG chặn -------------------------
import time as _tm  # noqa: E402

os.environ["BQ_VN_KHONG_DOI"] = "1"
ok("16m công tắc tắt chặn được CẢ luồng nền", not VN.tu_doi_nen(0.0))
os.environ.pop("BQ_VN_KHONG_DOI", None)
_t0 = _tm.time()
_l1 = VN.tu_doi_nen(0.0)
_gy = _tm.time() - _t0
_l2 = VN.tu_doi_nen(0.0)
ok("16m' `tu_doi_nen` khởi luồng ĐÚNG MỘT LẦN trong cả tiến trình",
   _l1 and not _l2)
ok(f"16m'' ... và KHÔNG CHẶN chỗ gọi ({_gy * 1000:.1f} ms) — nó nằm trên "
   f"đường đọc sản xuất", _gy < 0.5)
ok("16m''' sổ đếm lượt đọc về 0 sau khi đọc xong (kẹt ở 1 là luồng dời đợi "
   "vô hạn)", VN.dang_doc() == 0, f"đang đọc {VN.dang_doc()}")

# ---------------------------------------------------------------------------
print("\n[CA 17] DỌN RÁC `_job_<pid>_<n>` MỒ CÔI — CHỈ RÁC CỦA APP, PID ĐÃ CHẾT")
# ---------------------------------------------------------------------------
# Đo 25/08/2026 trên `%LOCALAPPDATA%\BQHungVideo\_giong_vieneu`: **11 `_job_*`
# + 11 `_tam_*`** của những tiến trình đã chết. Khuôn `don_seg_mo_coi` (cổng
# 42). Đây là thư mục DỮ LIỆU của người dùng nên mọi ca dưới đây hỏi cùng một
# câu: *cái KHÔNG phải rác của app có còn nguyên không.*
_VN_DIR_CU2 = os.environ.get("BQ_VN_DIR")
try:
    _T17 = T / "ca17" / "_giong_vieneu"
    _T17.mkdir(parents=True, exist_ok=True)
    os.environ["BQ_VN_DIR"] = str(_T17)

    _MO_COI = ("_job_999997_123", "_tam_999998_9", "_doi_999999_1")
    #: Tên GẦN GIỐNG + đồ thật của app/người dùng. Không cái nào được đụng.
    _PHAI_CON = ("_job_cua_toi", "_tam_1", "_jobs_1_2", "_job_abc_1",
                 "_job_1_2_ba", "hf", "venv", f"_job_{os.getpid()}_5")
    for _t in _MO_COI + _PHAI_CON:
        (_T17 / _t).mkdir(parents=True, exist_ok=True)
        (_T17 / _t / "job.json").write_text("{}", encoding="utf-8")
    (_T17 / "_bq_vieneu_runner.py").write_text("x", encoding="utf-8")

    _n17, _mb17 = VN.don_job_mo_coi()
    ok(f"17a rác MỒ CÔI (pid đã chết) bị dọn — {_n17} thư mục · {_mb17} MB",
       _n17 == len(_MO_COI)
       and not any((_T17 / t).exists() for t in _MO_COI), f"{_n17}")
    ok(f"17b pid CÒN SỐNG (chính mình) -> KHÔNG ĐỤNG "
       f"(`_job_{os.getpid()}_5`)", (_T17 / f"_job_{os.getpid()}_5").exists())
    for _t in ("_job_cua_toi", "_tam_1", "_jobs_1_2", "_job_abc_1",
               "_job_1_2_ba"):
        ok(f"17c tên GẦN GIỐNG `{_t}` -> KHÔNG ĐỤNG", (_T17 / _t).exists())
    ok("17d đồ thật của app/người dùng (`hf`, `venv`, runner) -> KHÔNG ĐỤNG",
       (_T17 / "hf").exists() and (_T17 / "venv").exists()
       and (_T17 / "_bq_vieneu_runner.py").exists())
    # TỰ KIỂM BỘ DÒ: mẫu phải khớp TOÀN BỘ tên. `search` (không có `$`) sẽ cho
    # `_job_1_2_ba` lọt — mà đó chính là một trong 5 tên ca 17c vừa canh.
    ok("17e TỰ KIỂM BỘ DÒ: mẫu khớp TOÀN BỘ tên, `_job_1_2_ba` KHÔNG khớp",
       VN._MAU_JOB.fullmatch("_job_1_2_ba") is None
       and VN._MAU_JOB.fullmatch("_job_12_3") is not None)
    ok("17e' ... và bộ dò CÓ RĂNG: nó khớp đúng 3 tên mồ côi vừa dọn",
       all(VN._MAU_JOB.fullmatch(t) for t in _MO_COI))

    # Không đọc được pid / thiếu psutil -> BỎ QUA (nghi ngờ thì GIỮ).
    _pid_that = VN._pid_con_song
    VN._pid_con_song = lambda pid: True    # type: ignore[assignment]
    for _t in _MO_COI:
        (_T17 / _t).mkdir(parents=True, exist_ok=True)
    _n17b, _ = VN.don_job_mo_coi()
    VN._pid_con_song = _pid_that           # type: ignore[assignment]
    ok("17f không dám phán pid đã chết -> BỎ QUA hết (nghi ngờ thì GIỮ)",
       _n17b == 0 and all((_T17 / t).exists() for t in _MO_COI), f"{_n17b}")

    # Đi qua `xoa_an_toan`.
    _dem17 = [0]

    def _xa17(d, **k):
        _dem17[0] += 1
        return False

    XA.don_thu_muc = _xa17                 # type: ignore[assignment]
    _n17c, _ = VN.don_job_mo_coi()
    XA.don_thu_muc = _XA_THAT              # type: ignore[assignment]
    ok("17g lượt dọn ĐI QUA `xoa_an_toan` (vá nó TỪ CHỐI thì 0 thư mục mất)",
       _dem17[0] >= len(_MO_COI) and _n17c == 0
       and all((_T17 / t).exists() for t in _MO_COI),
       f"{_dem17[0]} lượt gọi · dọn {_n17c}")

    ok("17h thư mục không tồn tại -> KHÔNG NÉM, trả (0, 0.0)",
       VN.don_job_mo_coi(str(T / "khong_he_co")) == (0, 0.0))
finally:
    XA.don_thu_muc = _XA_THAT              # type: ignore[assignment]
    if _VN_DIR_CU2 is None:
        os.environ.pop("BQ_VN_DIR", None)
    else:
        os.environ["BQ_VN_DIR"] = _VN_DIR_CU2

# ---------------------------------------------------------------------------
print("\n" + "=" * 74)
print(f"ĐẠT {_DAT} · HỎNG {len(_HONG)} · BỎ QUA {len(_BOQUA)}")
for x in _HONG:
    print("  HỎNG: " + x)
for x in _BOQUA:
    print("  BỎ QUA: " + x)
print("=" * 74)


def _don_hop_cat() -> None:
    """Dọn hộp cát — NHẢ HANDLE DB TRƯỚC, thử lại, và KÊU nếu không dọn được.

    ═══ LỖI THẬT CỦA CHÍNH CỔNG NÀY, VÁ 20/08/2026 ═══
    Bản đầu chỉ `shutil.rmtree(T, ignore_errors=True)`. Đo được: **25 thư mục
    `bq_test_giong_toi_*` nằm lại NGAY TRONG REPO** sau ~11 lượt chạy (mỗi lượt
    một cái). Thứ còn lại luôn là **đúng một file `studio.db`** — sqlite chưa
    nhả handle lúc cổng thoát, `rmtree` chết ở file đó, và `ignore_errors=True`
    **nuốt im lặng**. Xoá bằng tay thì được ngay, tức handle nhả sau đó.

    Đúng ba bệnh mà repo này chống, gộp trong hai dòng mã: rác test đọng trên
    máy anh Hùng (cổng 17) · phép dọn hỏng mà không nói gì (rò `_seg_*`, cổng
    42) · `ignore_errors` che mất `PermissionError`.

    Nên: (1) gọi `_reset_conn()` để nhả handle — đúng cách `db` tự làm trước khi
    copy file; (2) THỬ LẠI vài nhịp (khuôn `_XOA_CHO` của `ffmpeg_utils`);
    (3) không dọn được thì **IN RA**, đừng để lần sau lại phải đi đếm thư mục.
    """
    try:
        from app.database import db as _db
        for _t in (getattr(_db, "db", None), _db):
            _r = getattr(_t, "_reset_conn", None)
            if callable(_r):
                _r()
    except Exception:                                          # noqa: BLE001
        pass
    import gc
    import time as _tm
    gc.collect()
    for _ in range(6):
        shutil.rmtree(T, ignore_errors=True)
        if not T.exists():
            return
        _tm.sleep(0.35)
    print(f"  LƯU Ý: KHÔNG dọn được hộp cát {T} — còn "
          f"{[p.name for p in T.rglob('*') if p.is_file()][:5]}. "
          f"Xoá tay để repo không đọng rác.")


# ĐĂNG KÝ chứ không gọi thẳng: lượt THỬ PHÁ có phép làm cổng chết GIỮA ĐƯỜNG
# (vd gỡ lưới an toàn quanh bộ dò -> `HopGiongToi()` ném ở CA 3), và khi đó
# dòng gọi thẳng ở cuối file KHÔNG BAO GIỜ chạy -> hộp cát đọng lại trong repo.
# ĐO ĐƯỢC: lượt phá 19 phép để lại **2 thư mục `bq_test_giong_toi_*`**. Đúng
# bệnh mà `_don_hop_cat` sinh ra để chống (25 thư mục sau ~11 lượt), chỉ khác
# đường vào. `atexit` chạy cả khi thoát bình thường lẫn khi ném.
import atexit  # noqa: E402
atexit.register(_don_hop_cat)
sys.exit(1 if _HONG else 0)
