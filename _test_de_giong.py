# -*- coding: utf-8 -*-
"""CỔNG 86 — CHẾ ĐỘ "ĐÈ GIỌNG, KHÔNG TÁCH" (19/08/2026).

Anh Hùng đề xuất: *"thêm tính năng KHÔNG tách nhạc nền, chỉ GIẢM tiếng video gốc
rồi ĐÈ giọng lồng tiếng vào, để không bị mất mấy tiếng của video"*.

MỆNH ĐỀ TRUNG TÂM cổng này canh — và nó là mệnh đề về CẤU TẠO, không phải về
một con số hiệu chuẩn: **không bỏ đi gì thì không có gì để mất.** Đường cũ
(`tach`) tách nhạc-giọng rồi BỎ giọng gốc, nên mọi câu bộ chép lời bỏ qua đều
thành khoảng TRỐNG (đo ghép cặp 19/08: **14,75 s / 1,62%** kể cả sau khi đã có
`bu_giong_goc`). Đường mới giữ nguyên tiếng gốc làm nền -> **0 s theo cấu tạo**.

CA 6 CHỨNG MINH ĐIỀU ĐÓ BẰNG ffmpeg THẬT, KHÔNG CẦN MẠNG: dựng một "video gốc"
tổng hợp có HAI cửa sổ giọng gốc, nhưng CHỈ MỘT cửa sổ được lồng tiếng (đúng ca
"câu bị bộ chép lời bỏ qua"), rồi cho hai arm chạy trên CÙNG bộ mảnh giọng:
  · arm TACH: nền = lớp "nhạc" (KHÔNG có giọng gốc) -> cửa sổ không được lồng
    hoá IM -> **MẤT TIẾNG**
  · arm DE:   nền = "audio gốc"  (CÓ giọng gốc)     -> cửa sổ đó vẫn có tiếng
    -> **MẤT 0,00 s**
Đó vừa là phép đo, vừa là CHỐT CHỐNG-ĐẠT-OAN: arm TACH phải ra > 0, không thì
thước không có răng và số của arm DE vô nghĩa.

Cổng KHÔNG gọi mạng, KHÔNG tốn lượt Groq, KHÔNG tốn ký tự ElevenLabs. Phần chạy
thật là ffmpeg (nguồn tự sinh bằng `lavfi` nên không phụ thuộc file trên máy —
bài học cổng 68: `NGUON` ghi cứng tên file làm cổng ĐỎ OAN vì KHO chứ vì mã).

Chạy:  .venv\\Scripts\\python -u _test_de_giong.py
Thử phá: .venv\\Scripts\\python -u _pha_de_giong.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: CÁCH LY MÁY THẬT — phải đặt TRƯỚC mọi import `config`/PyQt. `BQ_QSETTINGS_INI`
#: là bắt buộc: QSettings mặc định ghi vào REGISTRY dùng chung với app thật, và
#: `luu_cai_dat` của CA 8 sẽ làm bẩn cài đặt của anh Hùng (bài học "Cutter: test
#: đừng ghi QSettings").
#: HỘP CÁT ĐẶT TRONG REPO, **KHÔNG trong `%TEMP%`** — và đây là số đo, không
#: phải sở thích: bản đầu dùng `tempfile.mkdtemp` và để lại **13 thư mục
#: `degiong_*`** trên ổ C sau một buổi (mỗi lượt chạy cổng + 9 lượt của
#: `_pha_de_giong.py` một cái). `shutil.rmtree(..., ignore_errors=True)` KHÔNG
#: dọn nổi vì **QSettings còn giữ file `settings.ini` đang mở**, và
#: `ignore_errors` thì nuốt luôn lỗi nên không ai biết. Ổ C của anh Hùng từng
#: đầy 100%. Cùng cách chữa của cổng 55 (`<repo>/bq_test_tgrac_<pid>`).
_T = Path(__file__).resolve().parent / f"bq_test_dg86_{os.getpid()}"
_T.mkdir(parents=True, exist_ok=True)


def _don_mo_coi() -> None:
    """Dọn hộp cát của các lượt chạy TRƯỚC (PID đã chết).

    Cần vì `QSettings` giữ `settings.ini` MỞ suốt đời tiến trình -> lượt chạy
    KHÔNG BAO GIỜ tự dọn nổi hộp cát của chính nó, kể cả sau `sync()`. Quét mồ
    côi ở đây thì tối đa chỉ còn MỘT thư mục sót (của lượt vừa chạy), thay vì
    tích lại 13 cái như bản đầu. Cùng khuôn `ffmpeg_utils.don_seg_mo_coi`:
    **chỉ xoá tên khớp mẫu app đặt VÀ pid đã chết** — thư mục của user thì không
    đụng.
    """
    import shutil as _sh
    for d in _T.parent.glob("bq_test_dg86_*"):
        if d == _T or not d.is_dir():
            continue
        try:
            pid = int(d.name.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            continue
        try:                                # pid còn sống -> ĐỪNG đụng
            os.kill(pid, 0)
            continue
        except OSError:
            pass
        _sh.rmtree(d, ignore_errors=True)


_don_mo_coi()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["BQ_DATA_DIR"] = str(_T)
os.environ["BQ_DB_PATH"] = str(_T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_T / "settings.ini")
os.environ["BQ_FFMPEG_SLOTS"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

import _test_guard                                          # noqa: E402,F401

#: MỐC ĐỐI CHỨNG = bản phát hành NGAY TRƯỚC tính năng này. **KHÔNG dùng `main`**
#: — sau khi gộp thì `main` chính là bản đang test và cổng đối chứng tự PASS OAN
#: vĩnh viễn (bài học cổng 36/51/52/56). Tính năng ra đời sau v2.39.0.
MOC = os.environ.get("BQ_MOC_DG", "v2.39.0")

DAT: list[str] = []
HONG: list[str] = []
#: BỎ QUA ≠ ĐẠT ≠ HỎNG. Mục phụ thuộc HOÀN CẢNH (có file thật trên đĩa hay
#: không) mà đếm là ĐẠT thì cổng phát chứng nhận khống; đếm là HỎNG thì nó đỏ
#: oan và người ta bỏ qua nó — nguy hơn hẳn (bài học cổng 41/47/56 CA17).
BO_QUA: list[str] = []


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> bool:
    (DAT if dieu else HONG).append(nhan)
    print(f"  {'ĐẠT ' if dieu else 'HỎNG'} {nhan}"
          + (f"   [{chi_tiet}]" if chi_tiet else ""))
    return bool(dieu)


# ==================================================================
# tiện ích chung
# ==================================================================
def nap_moc(duong: str, ten: str) -> types.ModuleType:
    """Nạp một file của BẢN MỐC thành module riêng (không đụng bản đang test)."""
    r = subprocess.run(["git", "show", f"{MOC}:{duong}"], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise RuntimeError(f"không lấy được {MOC}:{duong}: {r.stderr[:200]}")
    m = types.ModuleType(f"moc_{ten}")
    m.__dict__["__file__"] = f"<{MOC}:{duong}>"
    exec(compile(r.stdout, f"<{MOC}:{duong}>", "exec"), m.__dict__)
    m.__dict__["_NGUON_"] = r.stdout
    return m


def than_ham(duong: str, ten: str) -> ast.AST:
    """Nút AST của hàm `ten` trong file `duong`.

    Đọc file bằng **utf-8 tường minh** — `inspect.getsource` mở theo bảng mã
    MẶC ĐỊNH của máy (cp1252) nên docstring tiếng Việt ra mojibake rồi
    `ast.parse` nổ (bẫy đã sập ở cổng 71).
    """
    cay = ast.parse((REPO / duong).read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    raise RuntimeError(f"không thấy hàm {ten} trong {duong}")


def goi_trong_ham(nut: ast.AST, ten_goi: str) -> list[ast.Call]:
    """Mọi lời gọi `ten_goi(...)` trong thân một hàm."""
    ra = []
    for n in ast.walk(nut):
        if isinstance(n, ast.Call):
            f = n.func
            t = f.id if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else "")
            if t == ten_goi:
                ra.append(n)
    return ra


def _ten_trong(nut: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(nut) if isinstance(n, ast.Name)}


def goi_co_dieu_kien(cay: ast.AST, ham: str, goi: str,
                     bien: str = "") -> tuple[bool, str]:
    """Lời gọi `goi(...)` trong `ham` có nằm TRONG một `if` không.

    Trả (có, lý do). `bien` != "" thì đòi thêm: điều kiện của `if` phải THẬT SỰ
    nhắc tới tên biến đó. Hỏi mỗi "có nằm trong if không" là mục tự vô hiệu ngay
    khi có một `if` khác tình cờ bọc quanh (bài học cổng 80 LỌT 6).
    """
    n_ham = than_ham(cay, ham) if isinstance(cay, str) else cay
    can = goi_trong_ham(n_ham, goi)
    if not can:
        return False, f"KHÔNG thấy lời gọi {goi}() nào"
    # tìm mọi `if` bọc quanh từng lời gọi
    for c in can:
        bao: list[ast.AST] = []

        def _di(nut, chuoi):
            for con in ast.iter_child_nodes(nut):
                if con is c or c in list(ast.walk(con)):
                    if isinstance(nut, ast.If):
                        chuoi = [*chuoi, nut]
                    _di(con, chuoi)
                    if con is c:
                        bao.extend(chuoi)
                    return
        _di(n_ham, [])
        if not bao:
            return False, f"{goi}() gọi VÔ ĐIỀU KIỆN (không nằm trong if nào)"
        if bien:
            if not any(bien in _ten_trong(b.test) for b in bao):
                return False, (f"{goi}() nằm trong if nhưng KHÔNG if nào nhắc "
                               f"tới `{bien}`")
    return True, f"{len(can)} lời gọi, đều trong if" + (
        f" có `{bien}`" if bien else "")


def kwarg_khong_hang_so(cay: ast.AST, ham: str, goi: str,
                        khoa: str) -> tuple[bool, str]:
    """`goi(..., khoa=<biểu thức>)` — và giá trị KHÔNG được là HẰNG SỐ.

    Quét bằng AST chứ không tìm chuỗi, và đòi giá trị là BIỂU THỨC: quét tĩnh mà
    chỉ hỏi "có mặt không" thì luôn có một phép phá giữ nguyên mặt chữ mà đổi ý
    nghĩa (`de_giong=False`) — bài học cổng 56d, chiều PASS OAN.
    """
    n = than_ham(cay, ham) if isinstance(cay, str) else cay
    for c in goi_trong_ham(n, goi):
        for kw in c.keywords:
            if kw.arg == khoa:
                if isinstance(kw.value, ast.Constant):
                    return False, (f"{goi}({khoa}=) truyền HẰNG SỐ "
                                   f"{kw.value.value!r} — mặt chữ còn mà ý "
                                   f"nghĩa mất")
                return True, f"{goi}({khoa}=<biểu thức>)"
    return False, f"{goi}() KHÔNG truyền `{khoa}=`"


# ==================================================================
# CA 1 — `chuan_cach_tron` là CỬA DUY NHẤT chuẩn hoá tên cách trộn
# ==================================================================
def ca1() -> None:
    from app.core import thay_giong as TG
    print("\n[CA 1] CỬA CHUẨN HOÁ + NHÃN TIẾNG VIỆT")

    ok(TG.CACH_TRON == ("tach", "de"), "1a CACH_TRON đúng 2 cách",
       str(TG.CACH_TRON))
    # LÙI VỀ HÀNH VI CŨ, KHÔNG lùi về cách mới: giá trị này tới từ QSettings,
    # payload job cũ trong DB và tham số hàm — nguồn nào cũng mang được chuỗi lạ.
    xau = [None, "", "  ", "rac", "nhe", "de_giong", "tách", 0, 1, True]
    sai = [x for x in xau if TG.chuan_cach_tron(x) != "tach"]
    ok(not sai, "1b giá trị lạ/rỗng -> lùi về CÁCH CŨ (`tach`), không phải mới",
       f"lệch: {sai}" if sai else f"{len(xau)}/{len(xau)} về `tach`")
    hop = {"de": "de", "DE": "de", " de ": "de", "De": "de",
           "tach": "tach", " TACH ": "tach"}
    sai2 = {k: TG.chuan_cach_tron(k) for k, v in hop.items()
            if TG.chuan_cach_tron(k) != v}
    ok(not sai2, "1c nhận đúng cả hai tên, bỏ hoa/thường + khoảng trắng",
       str(sai2) if sai2 else f"{len(hop)}/{len(hop)}")

    nh = TG.NHAN_CACH_TRON
    ok(set(nh) == {"tach", "de"}, "1d có nhãn cho ĐỦ hai cách", str(list(nh)))
    # NHÃN KHÔNG EMOJI (máy anh Hùng thiếu glyph -> nút ra Ô ĐEN, lỗi v2.6.22).
    emoji = [c for v in nh.values() for c in v
             if ord(c) > 0x2000 and c not in "—·’“”…"]
    ok(not emoji, "1e nhãn KHÔNG EMOJI", f"gặp {emoji}" if emoji else "sạch")
    # NHÃN PHẢI NÓI RÕ ĐÁNH ĐỔI — anh Hùng phải thử được cả hai rồi mới quyết,
    # mà nhãn chỉ khoe cái được thì đó không phải một lựa chọn có thông tin.
    ok("MẤT HẲN" in nh["tach"] and "tách" in nh["tach"].lower(),
       "1f nhãn cách CŨ nói rõ tiếng gốc MẤT HẲN", nh["tach"])
    ok("không tách" in nh["de"].lower() and "gốc" in nh["de"].lower(),
       "1g nhãn cách MỚI nói rõ giữ tiếng gốc bên dưới", nh["de"])


# ==================================================================
# CA 2 — HASH CHỐNG TRÙNG: bất biến khi TẮT, đổi khi BẬT
# ==================================================================
def ca2() -> None:
    from app.core import tg_chay as TC
    print(f"\n[CA 2] HASH — mốc đối chứng {MOC}")

    moc = nap_moc("app/core/tg_chay.py", "tg")
    nay = (REPO / "app/core/tg_chay.py").read_text(encoding="utf-8")
    # CHỐT CHỐNG PASS OAN: mốc TRÙNG bản đang test -> "so nó với chính nó".
    ok(moc.__dict__["_NGUON_"] != nay,
       "2a bản mốc KHÁC bản đang test (chống so-nó-với-chính-nó)",
       f"mốc {MOC}")
    ok("de_giong" not in moc.__dict__["_NGUON_"],
       "2b bản mốc KHÔNG hề có `de_giong` (mốc đúng = bản NGAY TRƯỚC tính năng)")

    # nhiều tổ hợp cờ CŨ — bật hết cờ cũ vẫn phải giống mốc từng ký tự
    bo = [
        (("D:/v/a.mp4", "vi", "vi-VN-NamMinhNeural", "D:/ra"), {}),
        (("D:/v/a.mp4", "en", "", "D:/ra"), {}),
        (("D:/v/b.mp4", "vi", "g1", "E:/x"),
         dict(che_chu=True, che_chu_cach="mo", che_chu_muc=1.0, viet_chu=True)),
        (("D:/v/b.mp4", "vi", "g1", "E:/x"),
         dict(che_chu=True, che_chu_cach="khoi", che_chu_muc=0.3,
              viet_chu=True, kieu_chu={"co_chu": 0.06, "dam": True,
                                       "font": "Anton"})),
        (("D:/v/c.mp4", "vi", "g2", "E:/y"), dict(hinh_theo_giong=True)),
        (("D:/v/c.mp4", "vi", "g2", "E:/y"),
         dict(che_chu=True, viet_chu=True, hinh_theo_giong=True,
              kieu_chu={"vitri": "giua"})),
    ]
    lech = []
    for a, k in bo:
        x = moc.khoa_chong_trung(*a, **k)
        y = TC.khoa_chong_trung(*a, **k)
        if x != y:
            lech.append((k, x, y))
    ok(not lech,
       f"2c cờ TẮT -> khoá GIỐNG TỪNG KÝ TỰ mốc ({len(bo)} tổ hợp cờ cũ)",
       str(lech[:1]) if lech else f"{len(bo)}/{len(bo)} trùng")

    # BẬT phải ĐỔI khoá, không thì bấm Chạy bị SMART-SKIP không một dòng báo
    doi = []
    for a, k in bo:
        tat = TC.khoa_chong_trung(*a, **k)
        bat = TC.khoa_chong_trung(*a, **k, de_giong=True)
        doi.append(tat != bat and bat == tat + ":dg=1")
    ok(all(doi), "2d cờ BẬT -> khoá ĐỔI, và chỉ THÊM ĐUÔI `:dg=1`",
       f"{sum(doi)}/{len(doi)}")
    # "chỉ thêm đuôi" chính là mệnh đề chống "200-300 kênh xuất lại từ đầu":
    # thêm phần tử vào tuple `extra` là đổi hash của MỌI clip cũ.
    a0, k0 = bo[3]
    ok(TC.khoa_chong_trung(*a0, **k0, de_giong=True).startswith(
        TC.khoa_chong_trung(*a0, **k0)),
       "2e khoá BẬT có khoá TẮT làm TIỀN TỐ (nối đuôi, không chèn giữa)")
    ok(TC.khoa_chong_trung(*bo[0][0]) == TC.khoa_chong_trung(*bo[0][0]),
       "2f khoá TIỀN ĐỊNH (gọi hai lần ra một khoá)")


# ==================================================================
# CA 3 — payload job: KHÔNG mọc khoá khi cờ TẮT
# ==================================================================
class PoolGia:
    """Pool GIẢ chỉ ghi sổ — cổng này cần soi PAYLOAD, không cần DB thật.

    Ngữ nghĩa dedup (bấm lại trả ID job CŨ) đã có cổng 56/57 canh bằng
    `WorkerPool` + DB thật; nhân bản nó ở đây chỉ làm cổng chậm mà không thêm
    một mệnh đề nào.
    """

    def __init__(self) -> None:
        self.so: list[dict] = []

    def enqueue(self, loai, payload, **k):
        self.so.append({"loai": loai, "payload": dict(payload), **k})
        return len(self.so)


def _va_tg_so(mod) -> None:
    """Vá `tg_so` để cổng KHÔNG đọc/ghi sổ thật của anh Hùng."""
    mod.tg_so.can_chay = lambda *a, **k: True
    mod.tg_so.xoa = lambda *a, **k: None
    mod.tg_so.trung_thu_muc = lambda *a, **k: False
    mod.tg_so.thu_muc_dich_mac_dinh = lambda d: str(Path(d) / "ra")


def ca3(hop_cat: Path) -> None:
    from app.core import tg_chay as TC
    print("\n[CA 3] PAYLOAD JOB — không mọc khoá khi cờ TẮT")

    moc = nap_moc("app/core/tg_chay.py", "tg3")
    moc.tg_so = TC.tg_so
    for m in (TC, moc):
        _va_tg_so(m)
    v = hop_cat / "a.mp4"
    v.write_bytes(b"x")
    ra = str(hop_cat / "ra")

    p1 = PoolGia()
    TC.xep_mot(p1, v, "vi", "g", ra)
    kh_tat = set(p1.so[0]["payload"])
    p0 = PoolGia()
    moc.xep_mot(p0, v, "vi", "g", ra)
    kh_moc = set(p0.so[0]["payload"])
    ok(kh_tat == kh_moc,
       "3a cờ TẮT -> payload GIỐNG HẲN tập khoá bản mốc (không mọc khoá)",
       f"thêm {sorted(kh_tat - kh_moc)} · thiếu {sorted(kh_moc - kh_tat)}"
       if kh_tat != kh_moc else f"{len(kh_tat)} khoá, trùng")
    ok("de_giong" not in kh_tat, "3b cờ TẮT -> KHÔNG có khoá `de_giong`")

    p2 = PoolGia()
    TC.xep_mot(p2, v, "vi", "g", ra, de_giong=True)
    ok(p2.so[0]["payload"].get("de_giong") is True,
       "3c cờ BẬT -> payload CÓ `de_giong=True`")
    ok(p2.so[0]["dedup_key"].endswith(":dg=1"),
       "3d cờ BẬT -> dedup_key mang đuôi `:dg=1`", p2.so[0]["dedup_key"][-24:])
    ok(p1.so[0]["dedup_key"] != p2.so[0]["dedup_key"],
       "3e hai cách trộn ra HAI dedup_key khác nhau (không bị smart-skip)")


# ==================================================================
# CA 4 — CHẶN Demucs: cách cũ CHẶN, cách mới KHÔNG
# ==================================================================
def ca4() -> None:
    from app.core import thay_giong as TG
    print("\n[CA 4] THIẾU DEMUCS — cách cũ CHẶN, cách mới CHẠY")

    that = TG.tinh_trang_demucs
    TG.tinh_trang_demucs = lambda *a, **k: {   # giả lập MÁY NHÂN VIÊN
        "co": False, "thieu": ["torch", "demucs", "soundfile"],
        "cai_duoc": True, "lib": "x", "thiet_bi": ""}
    try:
        nem = False
        try:
            TG.chot_co_bo_tach_giong("auto")
        except RuntimeError:
            nem = True
        ok(nem, "4a máy KHÔNG có Demucs + cách CŨ -> CHẶN (ném)")

        nem2 = False
        try:
            TG.chot_co_bo_tach_giong("auto", de_giong=True)
        except RuntimeError as e:
            nem2 = True
            print(f"       (ném: {e})")
        ok(not nem2,
           "4b máy KHÔNG có Demucs + cách MỚI -> KHÔNG CHẶN "
           "(đây là mệnh đề 'không cần tải gì')")
    finally:
        TG.tinh_trang_demucs = that

    # TỰ KIỂM BỘ DÒ: bản vá hỏng thì 4a phải kêu. Máy NÀY có Demucs nên nếu
    # không vá `tinh_trang_demucs` thì 4a tự ĐẠT vì lý do SAI.
    ok(bool(that().get("co")),
       "4c TỰ KIỂM: máy này THẬT SỰ có Demucs -> phép vá ở 4a là thứ tạo ra "
       "cảnh 'thiếu', không phải hoàn cảnh")


# ==================================================================
# CA 5 — QUÉT AST: đường mã đi đúng chỗ (không sót cửa nào)
# ==================================================================
def ca5() -> None:
    print("\n[CA 5] QUÉT AST — cửa chung, không sót nhánh")
    f_tg = "app/core/thay_giong.py"

    co, ly = goi_co_dieu_kien(than_ham(f_tg, "thay_giong_video"),
                              "thay_giong_video", "tach_giong", "de_giong")
    ok(co, "5a `tach_giong()` trong thay_giong_video nằm trong `if` có "
           "`de_giong` (cách mới BỎ HẲN bước tách)", ly)

    co, ly = goi_co_dieu_kien(than_ham(f_tg, "thay_giong_video"),
                              "thay_giong_video", "bu_giong_goc", "de_giong")
    ok(co, "5b `bu_giong_goc()` bị chốt bằng `de_giong` (bù ở chế độ đè = cộng "
           "giọng gốc HAI LẦN)", ly)

    co, ly = kwarg_khong_hang_so(than_ham(f_tg, "thay_giong_mot_video"),
                                 "thay_giong_mot_video", "thay_giong_video",
                                 "de_giong")
    ok(co, "5c thay_giong_mot_video CHUYỀN `de_giong=` xuống (thiếu là MỌI job "
           "nổ unexpected keyword argument)", ly)

    co, ly = kwarg_khong_hang_so(than_ham(f_tg, "thay_giong_thu_muc"),
                                 "thay_giong_thu_muc", "chot_co_bo_tach_giong",
                                 "de_giong")
    ok(co, "5d thay_giong_thu_muc chuyền `de_giong=` vào chốt Demucs", ly)

    co, ly = kwarg_khong_hang_so("app/queue/jobs.py", "_thay_giong",
                                 "thay_giong_mot_video", "de_giong")
    ok(co, "5e jobs._thay_giong đọc cờ từ payload (không phải hằng số)", ly)

    # CỬA THỨ BA CỦA CHỐT DEMUCS — **ĐÃ BỊ SÓT MỘT LẦN TRONG CHÍNH BẢN VÁ NÀY.**
    # `jobs._thay_giong` gọi `chot_co_bo_tach_giong` RIÊNG (không đi qua
    # `thay_giong_thu_muc`), nên sót ở đó thì: UI mở nút Chạy -> job được xếp ->
    # **CHẾT NGAY tại chốt** trên máy nhân viên, mà máy dev (có Demucs) xanh
    # hết. Ba cửa phải khớp: UI `_cap_nhat_nut_chay` · `thay_giong_thu_muc` ·
    # `jobs._thay_giong`.
    co, ly = kwarg_khong_hang_so("app/queue/jobs.py", "_thay_giong",
                                 "chot_co_bo_tach_giong", "de_giong")
    ok(co, "5m jobs._thay_giong chuyền `de_giong=` vào CHỐT DEMUCS (cửa thứ ba "
           "— sót là tính năng chết đúng trên máy nhân viên)", ly)

    # CHỐT CỔNG 63: vá phải ở CỬA CHUNG. Sót một chỗ là video ra HAI GIỌNG TRỘN
    # mà mã thoát vẫn 0 -> con số 3 này KHÔNG được đổi.
    n = len(re.findall(r"_synth_all_words\s*\(",
                       (REPO / f_tg).read_text(encoding="utf-8")))
    ok(n == 3, "5f vẫn ĐÚNG 3 chỗ gọi `_synth_all_words` (bản vá không đẻ chỗ "
               "gọi thứ 4 — chốt cổng 63)", f"{n} chỗ")

    # ---- LỜI NHẮN TIẾN ĐỘ PHẢI KHỚP KHOÁ, KHÔNG SỐNG NHỜ ĐƯỜNG LÙI ----
    # LỖI THẬT bản vá này đã mắc và đã sửa: câu *"Trộn giọng lồng lên tiếng
    # gốc…"* KHÔNG chứa cụm khoá "trộn tiếng" nên `buoc_tu_tien_trinh` rơi vào
    # đường LÙI (suy theo KHOẢNG) và chỉ ra đúng bước 9 **nhờ may**. Cách phát
    # hiện: gọi với `p=0.0` — khớp khoá thì vẫn ra 9, sống nhờ đường lùi thì ra
    # 1. Không có mục này thì lần sau ai đổi mốc `prog` là thanh tiến độ chạy
    # NGƯỢC âm thầm (đúng cái anh Hùng từng kêu).
    # ĐỌC BẰNG **AST**, KHÔNG regex trên mã nguồn: bản đầu của mục này dùng
    # `re.findall(r'"(Trộn[^"]*)"')` và **bắt trúng chính DÒNG GHI CHÚ** ngay
    # trên nó (khối chú thích có trích nguyên văn câu CŨ để cảnh báo) -> HỎNG
    # OAN. Đúng cái bẫy đã sập ở cổng 47/51/53/54/73/80, lần này sập lại trong
    # đúng mục viết ra để chống một bẫy khác. Lấy chuỗi từ THAM SỐ của `prog()`
    # thì ghi chú không với tới được.
    from app.core import tg_so
    n_tgv = than_ham(f_tg, "thay_giong_video")
    cau: list[str] = []
    for c in goi_trong_ham(n_tgv, "prog"):
        for tv in c.args:
            for nut in ast.walk(tv):        # phủ cả `A if cond else B`
                if isinstance(nut, ast.Constant) \
                        and isinstance(nut.value, str) \
                        and nut.value.strip().lower().startswith("trộn"):
                    cau.append(nut.value)
    ok(len(cau) >= 2, "5i tìm được lời nhắn bước TRỘN của CẢ HAI cách (đọc "
                      "bằng AST — regex bắt trúng chính dòng ghi chú)",
       f"{len(cau)} câu: {cau}")
    xau = [c for c in cau if tg_so.buoc_tu_tien_trinh(0.0, c)[1] != 9]
    ok(not xau, "5j lời nhắn bước TRỘN của cả hai cách KHỚP KHOÁ bước 9 "
                "(không sống nhờ đường lùi theo khoảng)",
       f"rơi vào đường lùi: {xau}" if xau else f"{len(cau)}/{len(cau)} khớp")
    # và KHÔNG được chứa cụm khoá của bước KHÁC -> thanh tiến độ tụt về sau
    xau2 = [c for c in cau
            if any(k in c.lower() for k in
                   ("tách giọng", "chép lời", "đọc", "dịch", "rút gọn",
                    "khớp thời gian"))]
    ok(not xau2, "5k lời nhắn bước TRỘN KHÔNG chứa cụm khoá của bước TRƯỚC "
                 "(chứa là thanh tiến độ CHẠY NGƯỢC)", str(xau2))
    # TỰ KIỂM BỘ DÒ — không có mục này thì 5j/5k chỉ là con dấu.
    ok(tg_so.buoc_tu_tien_trinh(
        0.0, "Trộn giọng lồng lên tiếng gốc (đè, không tách)...")[1] != 9
       and tg_so.buoc_tu_tien_trinh(0.0, "Trộn tiếng mới...")[1] == 9,
       "5l TỰ KIỂM BỘ DÒ: câu THIẾU cụm 'trộn tiếng' phải bị 5j bắt, câu CÓ thì "
       "không (đây đúng là lỗi bản vá này đã mắc rồi sửa)")

    # TỰ KIỂM BỘ DÒ — bộ dò phải TRƯỢT trên mã hỏng, không thì nó là con dấu.
    xau = ("def f(de_giong=False):\n"
           "    t = tach_giong(w, d)\n"
           "    bu = bu_giong_goc(a, b, c)\n")
    p = REPO / "_tmp_do_de_giong_xau.py"
    p.write_text(xau, encoding="utf-8")
    try:
        c1, _ = goi_co_dieu_kien(than_ham(p.name, "f"), "f", "tach_giong",
                                 "de_giong")
        c2, _ = goi_co_dieu_kien(than_ham(p.name, "f"), "f", "bu_giong_goc",
                                 "de_giong")
        ok(not c1 and not c2,
           "5g TỰ KIỂM BỘ DÒ: mã gọi VÔ ĐIỀU KIỆN thì bộ dò phải TRƯỢT",
           f"tach={c1} bu={c2}")
        xau2 = ("def g(de_giong=False):\n"
                "    if 1:\n        x = thay_giong_video(a, de_giong=False)\n")
        p.write_text(xau2, encoding="utf-8")
        c3, ly3 = kwarg_khong_hang_so(than_ham(p.name, "g"), "g",
                                      "thay_giong_video", "de_giong")
        ok(not c3, "5h TỰ KIỂM BỘ DÒ: `de_giong=False` (hằng số) phải bị BẮT",
           ly3)
    finally:
        p.unlink(missing_ok=True)


# ==================================================================
# CA 6 — CHẠY THẬT: MẤT TIẾNG · ĐỘ TO · ĐỈNH · GIỌNG NỔI TRÊN NỀN
# ==================================================================
#: Dải "giọng" của nguồn tổng hợp. Nhạc là ồn hồng LỌC THẤP 300 Hz (hai tầng)
#: nên gần như không có năng lượng trong dải này -> lọc dải là tách được "giọng"
#: khỏi "nhạc" một cách TIỀN ĐỊNH. Demucs thì KHÔNG tiền định và chậm — cổng
#: không dùng nổi (nó là thước của `_do_de_giong.py`, chạy trên video thật).
DAI_LO, DAI_HI = 700, 1500
BUOC = 0.05
TONG = 12.0
#: Giọng GỐC nói gần khắp bài, NGẮT NHỊP TỪNG TỪ. Hai chỗ này không phải cho
#: đẹp, mỗi cái chữa một phép đo:
#:   · phủ rộng (0,5-10,5 s) = nguồn thật ~93% là lời;
#:   · **ngắt nhịp 0,35 s tiếng / 0,15 s nghỉ** = phải có >20% im lặng, vì
#:     `_do_mat_giong._san_nhieu` lấy SÀN NHIỄU bằng bách phân vị 20. Giọng
#:     LIÊN TỤC làm sàn rơi vào giữa tiếng nói -> `nguong_co = sàn + 12` không
#:     ai vượt -> bộ dò ra **0 khoảng ở CẢ HAI arm** = cổng tự ĐẠT OAN. Đã đo
#:     đúng cảnh đó khi dựng cổng này.
GOC_NOI = (0.5, 10.5)
LONG_DEN = 8.0
#: Nhịp từng "từ" — 70% duty.
NHIP = "lt(mod(t,0.5),0.35)"
#: Cửa sổ giọng gốc **KHÔNG được lồng tiếng** = ca "câu bộ chép lời BỎ QUA",
#: đúng chỗ đường cũ sinh ra khoảng TRỐNG.
CS_BO_QUA = (LONG_DEN, GOC_NOI[1])


def _ff(args: list[str], mo_ta: str) -> None:
    from config import settings as st
    r = subprocess.run([str(st.FFMPEG_PATH), "-y", "-v", "error", "-nostdin",
                        *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{mo_ta}: rc={r.returncode} {(r.stderr or '')[-300:]}")


def dung_nguon(d: Path) -> dict:
    """Dựng 'video gốc' tổng hợp: nhạc dải trầm + giọng gốc ngắt nhịp từng từ.

    Nguồn tự sinh bằng `lavfi` nên cổng KHÔNG phụ thuộc file trên máy (bài học
    cổng 68: ghi cứng tên file làm cổng ĐỎ OAN vì KHO chứ không vì mã).
    **`anoisesrc` BẮT BUỘC có `s=` (seed)** — không có thì mỗi lượt một mẻ ồn
    khác nhau và cổng nhấp nháy (cùng lý do `gradients` phải có seed, cổng 46).
    """
    nhac, giong, goc = d / "nhac.wav", d / "giong_goc.wav", d / "goc.wav"
    _ff(["-f", "lavfi", "-i", f"anoisesrc=d={TONG}:c=pink:a=0.6:s=12345",
         "-af", "lowpass=f=300,lowpass=f=300,volume=0.5,aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(nhac)],
        "dựng lớp nhạc")
    a, b = GOC_NOI
    _ff(["-f", "lavfi", "-i", f"anoisesrc=d={TONG}:c=white:a=0.9:s=777",
         "-af", f"highpass=f={DAI_LO},lowpass=f={DAI_HI},"
                f"volume='if(between(t,{a},{b})*{NHIP},1.0,0)':eval=frame,"
                f"aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(giong)],
        "dựng lớp giọng gốc")
    _ff(["-i", str(nhac), "-i", str(giong), "-filter_complex",
         "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[o]",
         "-map", "[o]", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
         str(goc)], "trộn audio gốc")
    # MẢNH GIỌNG LỒNG — chỉ phủ tới `LONG_DEN`, phần sau là cửa sổ BỎ QUA.
    # CÙNG dải tần với giọng gốc nên thước không thiên vị arm nào.
    manh = d / "long_0.wav"
    _ff(["-f", "lavfi", "-i",
         f"anoisesrc=d={LONG_DEN - a}:c=white:a=0.9:s=555",
         "-af", f"highpass=f={DAI_LO},lowpass=f={DAI_HI},"
                f"volume='if({NHIP},0.9,0)':eval=frame,aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(manh)],
        "dựng mảnh giọng lồng")
    return {"nhac": str(nhac), "giong": str(giong), "goc": str(goc),
            "manh": [(a, str(manh))]}


def bao_dai_giong(wav: str | Path, d: Path, ten: str) -> list[float]:
    """Đường bao mức TRONG DẢI GIỌNG — thước 'có tiếng người hay không'."""
    from app.core import thay_giong as TG
    loc = d / f"loc_{ten}.wav"
    _ff(["-i", str(wav), "-af",
         f"highpass=f={DAI_LO},lowpass=f={DAI_HI},aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(loc)],
        f"lọc dải giọng {ten}")
    return TG.duong_bao_muc(loc, buoc=BUOC)


def ca6(hop_cat: Path) -> None:
    from app.core import thay_giong as TG
    import _do_de_giong as D
    import _do_mat_giong as DM
    print("\n[CA 6] CHẠY THẬT ffmpeg — mất tiếng · độ to · đỉnh · giọng nổi")

    d = hop_cat / "ca6"
    d.mkdir(parents=True, exist_ok=True)
    n = dung_nguon(d)

    ra: dict = {}
    for arm, nen in (("TACH", n["nhac"]), ("DE", n["goc"])):
        out = d / f"tron_{arm}.wav"
        ra[arm] = TG.tron_thay_giong(nen, n["manh"], TONG, out,
                                     goc_wav=n["goc"])
        dd = TG.probe_duration(out)
        ok(abs(dd - TONG) <= 0.05,
           f"6a[{arm}] độ dài ĐÚNG {TONG:.2f}s (chốt apad/atrim — `asplit` "
           f"từng làm độ dài KHÔNG tiền định mà rc vẫn 0)",
           f"{dd:.3f}s")

    b_goc = bao_dai_giong(n["goc"], d, "goc")
    mat: dict = {}
    for arm in ("TACH", "DE"):
        b = bao_dai_giong(d / f"tron_{arm}.wav", d, arm)
        kh, tk = DM.khoang_mat(b_goc, b)
        mat[arm] = tk
        print(f"       {arm}: MẤT {tk['giay_mat']:.2f}s / {tk['so_khoang']} "
              f"khoảng · phân bố {D.phan_bo(kh)}")
        for a, bb in kh:
            print(f"          {a:6.2f} -> {bb:6.2f}  ({bb - a:.2f}s)")

    # CHỐT CHỐNG-ĐẠT-OAN PHẢI ĐỨNG TRƯỚC: thước có răng trên bộ file này không.
    ok(mat["TACH"]["giay_mat"] > 0.5,
       "6b CHỐT CHỐNG-ĐẠT-OAN: arm TACH (cách cũ) MẤT TIẾNG > 0 -> thước CÓ "
       "RĂNG, số của arm DE mới đọc được",
       f"TACH mất {mat['TACH']['giay_mat']:.2f}s")
    ok(mat["DE"]["giay_mat"] == 0.0,
       "6c MẤT TIẾNG arm DE = 0,00 s (mệnh đề trung tâm: không bỏ gì thì "
       "không mất gì)",
       f"DE mất {mat['DE']['giay_mat']:.2f}s / "
       f"TACH {mat['TACH']['giay_mat']:.2f}s")
    # cửa sổ BỊ BỎ QUA chính là chỗ đường cũ mất tiếng — nói ĐÚNG CHỖ, không
    # chỉ nói tổng: mất 2 s ở chỗ khác thì mệnh đề đã sai mà tổng vẫn đẹp.
    trung = any(a <= CS_BO_QUA[0] + 0.3 and bb >= CS_BO_QUA[1] - 0.3
                for a, bb in [(k[0], k[1]) for k in
                              DM.khoang_mat(b_goc, bao_dai_giong(
                                  d / "tron_TACH.wav", d, "TACH2"))[0]])
    ok(trung, "6d chỗ arm TACH mất tiếng ĐÚNG là cửa sổ KHÔNG được lồng "
              f"{CS_BO_QUA} (không phải mất chỗ khác)")

    # ---- ĐỘ TO + ĐỈNH ----
    # THƯỚC CHẤM Ở ĐÂY LÀ `loudnorm` — CÓ LÝ DO, không phải chọn bừa: đó là
    # chính bộ đo mà `chuan_do_to` dùng để quyết định nâng bao nhiêu, nên nó trả
    # lời đúng câu "app có làm được việc nó nói không".
    # Phép ĐỐI CHIẾU HAI THƯỚC nằm ở CA 7, trên NGUỒN THẬT — xem lý do ở đó.
    for arm in ("TACH", "DE"):
        w = d / f"tron_{arm}.wav"
        t = D.do_to_hai_thuoc(w, arm, nem=False)
        print(f"       {arm}: I loudnorm {t['I_loudnorm']:+.2f} · "
              f"ebur128 {t['I_ebur128']:+.2f} (lệch {t['lech_LU']:.3f} LU · "
              f"LRA {t['LRA']}) · đỉnh {t['dinh_dbfs']:+.2f} dBFS · chạm trần "
              f"{t['cham_tran']} mẫu · TP {t['TP_loudnorm']:+.2f} dBTP")
        ok(abs(t["I_loudnorm"] - D.DICH_LUFS) <= 1.0,
           f"6e[{arm}] độ to về đích {D.DICH_LUFS:.0f} LUFS (±1,0, thước "
           f"`loudnorm` — đúng bộ đo `chuan_do_to` dùng)",
           f"{t['I_loudnorm']:+.2f}")
        ok(t["dinh_dbfs"] <= TG.TRAN_DINH_DB + 0.25,
           f"6f[{arm}] đỉnh không vượt trần {TG.TRAN_DINH_DB} dBFS "
           f"(alimiter chặn đỉnh MẪU nên đỉnh thật vọt ~+0,06 dB)",
           f"{t['dinh_dbfs']:+.3f} dBFS · chạm trần {t['cham_tran']} mẫu")

    # ---- GIỌNG LỒNG NỔI TRÊN NỀN bao nhiêu dB LÚC ĐANG NÓI ----
    for arm in ("TACH", "DE"):
        r = ra[arm]
        cb = r.get("can_bang") or {}
        print(f"       {arm}: giọng/nền trước {cb.get('giong_tren_nhac_truoc_db')}"
              f" -> sau {r.get('giong_tren_nhac_tinh_db')} dB "
              f"(kể ducking {r.get('giong_tren_nhac_ke_ne_db')}) · nền hạ "
              f"{r.get('gain_nhac_db')} dB · giọng nâng "
              f"{r.get('gain_giong_db')} dB")
        v = r.get("giong_tren_nhac_ke_ne_db")
        ok(v is not None and v > 0,
           f"6h[{arm}] giọng lồng NỔI TRÊN nền lúc đang nói (> 0 dB)",
           f"{v} dB")
    # DUCKING PHẢI THEO CỬA SỔ, KHÔNG HẠ ĐỀU CẢ BÀI — hạ đều là nhạc chỗ nào
    # cũng nhỏ, mất không khí phim.
    ok(ra["DE"].get("duck_ratio") == TG.DUCK_RATIO,
       f"6i ducking BẬT với ratio ĐÃ ĐO {TG.DUCK_RATIO} (né theo cửa sổ giọng "
       f"lồng, không hạ đều cả bài)", str(ra["DE"].get("duck_ratio")))
    ok(abs(float(ra["DE"].get("gain_nhac_db") or 0)) <= TG.HA_NHAC_TOI_DA_DB
       + 1e-6,
       f"6j nền hạ KHÔNG quá trần {TG.HA_NHAC_TOI_DA_DB} dB (phần còn lại để "
       f"ducking lo)", f"{ra['DE'].get('gain_nhac_db')} dB")


# ==================================================================
# CA 7 — HAI THƯỚC ĐỘ TO PHẢI ĐỒNG Ý, ĐO TRÊN NGUỒN THẬT
# ==================================================================
#: Thư mục nguồn thật. **KHÔNG ghi cứng TÊN FILE** — quét thư mục rồi lấy file
#: đầu (bài học cổng 68: `NGUON` ghi cứng tên file làm cổng ĐỎ OAN vì KHO đổi).
#: `BQ_KHO_THAT` để ép đường khác — có nó thì THỬ ĐƯỢC nhánh BỎ QUA (trỏ vào thư
#: mục không tồn tại), mà nhánh đó phải thử: nó là nhánh chạy trên máy nhân viên.
KHO_THAT = tuple(
    Path(x) for x in (os.environ["BQ_KHO_THAT"].split(os.pathsep)
                      if os.environ.get("BQ_KHO_THAT") else ()))  \
    or (Path(r"C:\Users\Admin\Downloads\longtieng") / "xuất",
        Path(r"C:\Users\Admin\Downloads\longtieng"))


def ca7() -> None:
    """Đối chiếu hai bộ đo độ to trên NỘI DUNG THẬT, không trên nguồn tổng hợp.

    **VÌ SAO PHÉP ĐỐI CHIẾU PHẢI Ở ĐÂY, KHÔNG Ở CA 6 — đây là số đo, không phải
    sở thích.** Ngưỡng 0,5 LU hiệu chuẩn cho nội dung app này xử lý; đo được
    19/08/2026:
      · nguồn THẬT của anh Hùng (LRA 2,1 — Douyin master nén sẵn): lệch **0,08 LU**
      · nguồn tổng hợp LIÊN TỤC (sine / ồn hồng): lệch **0,03-0,05 LU**
      · nguồn tổng hợp DẢI ĐỘNG RỘNG (LRA 10-14): lệch **0,5-1,2 LU**
    Tức trên nguồn tổng hợp ngắt nhịp của CA 6, hai thước lệch nhau vì **cửa
    chặn tương đối của BS.1770** (khối 400 ms lật vào/ra khác nhau), KHÔNG vì
    thước nào hỏng. Chấm ngưỡng 0,5 ở đó là chấm ngoài vùng hiệu chuẩn, mà
    **nới ngưỡng cho hết đỏ thì đúng lúc mất khả năng bắt một thước hỏng thật**.
    Nên phép đối chiếu chạy ở ĐÂY, trên đúng loại nội dung nó được hiệu chuẩn.

    Không có file thật -> **BỎ QUA**, không ĐẠT (đếm là ĐẠT thì đúng bằng "phép
    đo hỏng phát chứng nhận") và không HỎNG (đỏ vì kho đĩa là ĐỎ OAN, mà cổng
    đỏ oan thì người ta bỏ qua nó — bài học cổng 41/47).
    """
    import _do_de_giong as D
    print("\n[CA 7] HAI THƯỚC ĐỘ TO — trên NGUỒN THẬT (vùng hiệu chuẩn)")

    f = None
    for k in KHO_THAT:
        v = sorted(k.glob("*.mp4")) if k.is_dir() else []
        if v:
            f = v[0]
            break
    if f is None:
        # GHI ĐỦ **HAI** MỤC BỊ BỎ, KHÔNG PHẢI MỘT: `_chay_hoi_quy.py` so mốc
        # bằng `ĐẠT + BỎ QUA >= mốc`, nên ghi thiếu một mục là lượt hồi quy trên
        # máy KHÔNG có video thật báo **"TỤT so mốc"** = ĐỎ OAN. Số mục bỏ qua
        # phải bằng đúng số mục lẽ ra được chấm.
        BO_QUA.append("7a hai thước độ to đồng ý trên nguồn THẬT")
        BO_QUA.append("7b nguồn thật nằm trong vùng hiệu chuẩn (LRA hẹp)")
        print(f"  BỎ QUA 7a+7b — không có mp4 nào trong "
              f"{[str(x) for x in KHO_THAT]} (KHÔNG tính là ĐẠT)")
        return
    t = D.do_to_hai_thuoc(f, "THAT", nem=False)
    print(f"       {f.name[:44]} · I loudnorm {t['I_loudnorm']:+.2f} · "
          f"ebur128 {t['I_ebur128']:+.2f} · LRA {t['LRA']}")
    ok(t["lech_LU"] <= D.LECH_LU_MAX,
       f"7a HAI thước độ to đồng ý trên nguồn THẬT (lệch <= {D.LECH_LU_MAX} LU)",
       f"{t['lech_LU']:.3f} LU · LRA {t['LRA']}")
    ok(t["LRA"] <= 6.0,
       "7b nguồn thật NẰM TRONG vùng hiệu chuẩn của ngưỡng 0,5 LU (LRA hẹp) — "
       "mục 7a chỉ có nghĩa khi điều này đúng",
       f"LRA {t['LRA']}")


# ==================================================================
# CA 8 — Ô CHỌN TRONG HỘP THAY GIỌNG (cái anh Hùng thật sự bấm)
# ==================================================================
def ca8(hop_cat: Path) -> None:
    """Ô chọn cách trộn: mặc định GIỮ cách cũ, và mở được nút Chạy khi chọn đè.

    Cổng CA 1-7 kiểm các HÀM; mục này kiểm cái anh Hùng bấm. Không có nó thì
    tính năng có thể đúng hết ở dưới mà **không với tới được** — đúng lỗi đã sập
    ở cổng 19 (mẫu-theo-kênh chỉ áp ở dây chuyền, bấm tay vẫn ăn cấu hình cũ).
    """
    import unicodedata
    from PyQt6.QtWidgets import QApplication, QComboBox, QLabel
    from app.core import thay_giong as TG
    from app.core import tg_chay as TC
    import app.ui.thay_giong_dialog as TGD

    print("\n[CA 8] Ô CHỌN TRONG HỘP THAY GIỌNG")
    app = QApplication.instance() or QApplication([])

    # TỰ KIỂM bản vá cách ly: QSettings phải là FILE INI trong hộp cát, không
    # phải registry thật. Sai chỗ này là cổng làm bẩn cài đặt của anh Hùng.
    from app.ui.appsettings import app_settings
    # `QSettings.fileName()` trả đường dẫn dấu GẠCH XUÔI còn `_T` là gạch
    # NGƯỢC -> so chuỗi thô là HỎNG OAN (đã sập một lần). Chuẩn hoá cả hai.
    _f = str(app_settings().fileName())
    ok(os.path.normcase(os.path.normpath(str(_T)))
       in os.path.normcase(os.path.normpath(_f)),
       "8a TỰ KIỂM: QSettings nằm trong hộp cát (KHÔNG registry thật của anh "
       "Hùng)", _f)

    vao = hop_cat / "vao"
    vao.mkdir(parents=True, exist_ok=True)
    (vao / "a.mp4").write_bytes(b"x" * 2048)
    dlg = TGD.ThayGiongDialog(None, None)
    dlg.ed_thu_muc.setText(str(vao))
    dlg.ed_thu_muc_ra.setText(str(hop_cat / "ra"))
    dlg._quet_thu_muc() if hasattr(dlg, "_quet_thu_muc") else None
    app.processEvents()

    cb = dlg.cb_tron
    ok(cb.count() == 2, "8b ô chọn có ĐÚNG hai cách", f"{cb.count()} mục")
    # MỤC ĐẦU + giá trị mặc định phải là CÁCH CŨ. Đây là mệnh đề quan trọng nhất
    # của cả ô: đổi mặc định là đổi tiếng của MỌI video từ nay trên 200-300 kênh.
    ok(cb.itemData(0) == "tach" and cb.currentData() == "tach",
       "8c MẶC ĐỊNH là CÁCH CŨ (`tach`) — không đổi tiếng của 200-300 kênh sau "
       "lưng anh Hùng", f"mục đầu {cb.itemData(0)!r} · đang chọn "
                        f"{cb.currentData()!r}")
    # nhãn lấy từ MỘT NGUỒN (`NHAN_CACH_TRON`), so TỪNG KÝ TỰ: viết tay hai lần
    # là hai chỗ lệch nhau, rồi nhật ký nói khác cái user thấy.
    ok(cb.itemText(0) == TG.NHAN_CACH_TRON["tach"]
       and cb.itemText(1) == TG.NHAN_CACH_TRON["de"],
       "8d nhãn hai mục lấy TỪNG KÝ TỰ từ `TG.NHAN_CACH_TRON` (một nguồn)")
    nhan = [cb.itemText(i) for i in range(cb.count())]
    nhan += [w.text() for w in dlg.findChildren(QLabel)
             if "trộn" in (w.text() or "").lower()]
    xau = [x for x in nhan
           if any(ord(c) > 0xFFFF or unicodedata.category(c) == "So"
                  for c in x)]
    ok(not xau, f"8e nhãn KHÔNG EMOJI ({len(nhan)} nhãn)", str(xau))
    ok(any("trộn" in (w.text() or "").lower()
           for w in dlg.findChildren(QLabel)),
       "8f có nhãn chữ nói rõ ô này là 'Cách trộn tiếng'")

    # ---- CỜ ĐI TỚI `xep_mot` ĐÚNG như combo đang hiện ----
    that = TC.xep_mot
    thu: list[dict] = []

    def bat(*a, **k):
        thu.append(dict(k))
        return None                     # None = "không có pool", UI tự xử lý
    TGD.tg_chay.xep_mot = bat
    try:
        for gt, cho in (("tach", False), ("de", True)):
            thu.clear()
            cb.setCurrentIndex(cb.findData(gt))
            app.processEvents()
            dlg._chay()
            got = [t.get("de_giong") for t in thu]
            ok(bool(got) and all(x is cho for x in got),
               f"8g chọn {gt!r} -> `xep_mot(de_giong={cho})` "
               f"({len(got)} video)", str(got))
    finally:
        TGD.tg_chay.xep_mot = that

    # ---- NÚT CHẠY: cách mới phải MỞ được trên máy CHƯA có Demucs ----
    dlg._tt_demucs = {"co": False, "thieu": ["torch"], "cai_duoc": True,
                      "lib": "x", "thiet_bi": ""}
    for gt, cho in (("tach", False), ("de", True)):
        cb.setCurrentIndex(cb.findData(gt))
        app.processEvents()
        dlg._cap_nhat_nut_chay()
        ok(dlg.b_chay.isEnabled() is cho,
           f"8h máy CHƯA có Demucs + chọn {gt!r} -> nút Chạy "
           f"{'MỞ' if cho else 'KHOÁ'}",
           f"isEnabled={dlg.b_chay.isEnabled()}")

    # ---- QSettings: nhớ đúng lựa chọn, và đọc lại qua CỬA CHUẨN HOÁ ----
    cb.setCurrentIndex(cb.findData("de"))
    dlg.luu_cai_dat()
    ok(str(app_settings().value(TGD.K_TRON_CACH, "")) == "de",
       "8i `luu_cai_dat` ghi đúng cách đang chọn")
    app_settings().setValue(TGD.K_TRON_CACH, "rac_khong_ton_tai")
    dlg2 = TGD.ThayGiongDialog(None, None)
    ok(dlg2.cb_tron.currentData() == "tach",
       "8j QSettings mang giá trị LẠ -> hộp lùi về CÁCH CŨ, không lùi về cách "
       "mới", str(dlg2.cb_tron.currentData()))
    for x in (dlg, dlg2):
        x.setParent(None)
        x.deleteLater()
    app.processEvents()
    # combo cách trộn KHÔNG được là combo cuộn-chuột-đổi-giá-trị vô tình? — ô
    # này dùng QComboBox chuẩn như `cb_khop`, cùng hành vi, không thêm mệnh đề.
    ok(isinstance(cb, QComboBox), "8k ô chọn là QComboBox (giống `cb_khop`, "
                                  "không đẻ bộ điều khiển kiểu khác)")


# ==================================================================
def main() -> int:
    hop = REPO / f"bq_test_dg_{os.getpid()}"
    shutil.rmtree(hop, ignore_errors=True)
    hop.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("CỔNG 86 — CHẾ ĐỘ ĐÈ GIỌNG, KHÔNG TÁCH")
    print("=" * 78)
    try:
        ca1()
        ca2()
        ca3(hop)
        ca4()
        ca5()
        ca6(hop)
        ca7()
        ca8(hop)
    except Exception as e:                                  # noqa: BLE001
        import traceback
        traceback.print_exc()
        # CHẾT GIỮA CHỪNG ≠ ĐẠT. Cổng phải BÁO HỎNG rồi vẫn in tổng kết —
        # mất dòng tổng kết là đọc ra không phân biệt được với "chưa chạy tới
        # chốt" (bài học cổng 74b).
        HONG.append(f"CỔNG CHẾT GIỮA CHỪNG: {type(e).__name__}: {e}")
    finally:
        # KHÔNG ĐỂ RÁC TRÊN MÁY ANH HÙNG — ổ C từng đầy 100%. `_T` là hộp cát
        # QSettings/DATA_DIR, `hop` là hộp cát ffmpeg.
        # **QSettings CÒN GIỮ `settings.ini` ĐANG MỞ** nên `rmtree` lượt đầu
        # trượt; phải `sync()` rồi thử lại. `ignore_errors=True` một mình là
        # nuốt lỗi im lặng rồi để rác lại (đã để lại 13 thư mục vì đúng thế).
        shutil.rmtree(hop, ignore_errors=True)
        try:
            from app.ui.appsettings import app_settings
            app_settings().sync()
        except Exception:                                   # noqa: BLE001
            pass
        for _ in range(3):
            shutil.rmtree(_T, ignore_errors=True)
            if not _T.exists():
                break
        if _T.exists():
            print(f"  (!) KHÔNG dọn được hộp cát {_T} — dọn tay, đừng để rác")
    print("\n" + "=" * 78)
    print(f"ĐẠT {len(DAT)} · HỎNG {len(HONG)}"
          + (f" · BỎ QUA {len(BO_QUA)}" if BO_QUA else ""))
    for h in HONG:
        print(f"  HỎNG: {h}")
    # liệt kê từng mục BỎ QUA để một lượt bỏ qua KHÔNG THỂ trông giống một lượt
    # chấm đủ (bài học cổng 56 CA17).
    for b in BO_QUA:
        print(f"  BỎ QUA: {b}")
    (REPO / "_kq86.json").write_text(
        json.dumps({"dat": len(DAT), "hong": HONG, "bo_qua": BO_QUA},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if not HONG else 1


if __name__ == "__main__":
    sys.exit(main())
