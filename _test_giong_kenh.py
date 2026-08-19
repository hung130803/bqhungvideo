"""CỔNG 81 — GIỌNG RIÊNG THEO KÊNH · XOAY VÒNG · NHÂN BẢN · CHATTERBOX.

**VIỆC NÀY CANH CÁI GÌ.** Anh Hùng chạy 200-300 kênh kiếm tiền. Lượt
19/08/2026 thêm bốn thứ, và cả bốn đều có một kiểu hỏng ÂM THẦM riêng:

1. ``giong_mo`` — mở khoá 185 giọng edge-tts. Hỏng âm thầm: mở nhầm một giọng
   CHƯA ĐO -> combo hiện một dòng trống số, mà dòng trống số lại đúng là dòng
   rủi ro nhất.
2. ``giong_kenh`` — mỗi kênh một giọng + xoay vòng. Hỏng âm thầm: xoay vòng
   dùng ``hash()`` thì **3 làn xuất song song ra 3 giọng khác nhau CHO CÙNG
   MỘT VIDEO** (``PYTHONHASHSEED`` ngẫu nhiên mỗi tiến trình), phá luật
   all-or-nothing, và **không tra lại được** sau đó. CA 3 chạy phép so ở
   **TIẾN TRÌNH KHÁC có seed khác** — đo trong một tiến trình là tự PASS OAN.
3. ``nhan_ban_giong`` — nhân bản giọng từ mẫu. Hỏng âm thầm: mẫu xấu không
   làm app nổ, nó ra giọng nghe hỏng sau vài chục video.
4. ``giong_chatter`` — Chatterbox. Hỏng âm thầm NẶNG NHẤT: ``import torch``
   trong tiến trình đã nạp Qt là **ACCESS VIOLATION** mà ``try/except`` không
   chặn được, và lỗi lại đội lốt *"máy chưa cài"* (cổng 55 đã sập đúng vậy).
   -> CA 6 quét bằng **AST**, không quét chuỗi.

**KHÔNG GỌI MẠNG, KHÔNG TỐN LƯỢT GROQ, KHÔNG CHẠY MODEL.** Cổng chấm hàm
thuần + DB hộp cát. Phép đo cần model thật nằm ở ``_do_chatter.py`` /
``_do_nhan_ban.py`` (kết quả đã chép vào docstring các module).

**MỌI CA QUÉT TĨNH ĐỀU KÈM CA TỰ KIỂM BỘ DÒ.** Quét bằng chuỗi thì chính DÒNG
GHI CHÚ giải thích bản vá bị kể là vi phạm (đỏ oan — cổng 47/51/53/54 đã sập 4
lần), còn quét kiểu "có mặt không" thì một phép phá giữ nguyên mặt chữ mà đổi
ý nghĩa vẫn lọt (PASS oan — cổng 56d).
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_QSETTINGS_INI", "1")

# HỘP CÁT: đặt TRƯỚC mọi import của app — `config` đọc biến này lúc NẠP, đặt
# sau là cổng ghi thẳng vào DB thật của anh Hùng.
_SB = Path(tempfile.mkdtemp(prefix="bq_c81_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")

DAT = HONG = BOQUA = 0
_HONG: list[str] = []


def ok(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def bo_qua(ten: str, ly_do: str) -> None:
    global BOQUA
    BOQUA += 1
    print(f"  BỎ QUA {ten} — {ly_do}")


def _cay(mod) -> ast.Module:
    """AST của một module — đọc file bằng UTF-8 tường minh.

    ``inspect.getsource`` mở file theo bảng mã MẶC ĐỊNH của máy (cp1252 ở đây)
    nên docstring tiếng Việt ra mojibake rồi ``ast.parse`` nổ (bẫy cổng 71).
    """
    return ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))


def _ten_goi(cay: ast.AST) -> set[str]:
    """Mọi tên hàm ĐƯỢC GỌI trong cây (bỏ comment + chuỗi, vì là AST)."""
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                ra.add(f.id)
            elif isinstance(f, ast.Attribute):
                ra.add(f.attr)
    return ra


def _import_muc_module(cay: ast.Module) -> set[str]:
    """Tên gói được import Ở TẦM MODULE (không tính trong hàm).

    Chỉ duyệt thân module: import NẰM TRONG HÀM là hợp lệ và cố ý (hoãn tới
    lúc thật sự cần), import ở tầm module mới là thứ nổ lúc app khởi động.
    """
    ra: set[str] = set()
    for n in cay.body:
        if isinstance(n, ast.Import):
            ra |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            ra.add(n.module.split(".")[0])
    return ra


# ===========================================================================
print("CA 1 — bảng nhấn nhá sau khi mở khoá")
from app.core import giong_mo, nhan_nha  # noqa: E402

# 191 -> 211 ngày 19/08/2026 (thêm 20 giọng VieNeu, `_do_nhan_nha_vn.py`).
# Con số này CỐ Ý ghi cứng: nó là dây báo động buộc lượt nào đổi bảng cũng
# phải đọc lại CA 1c ngay dưới — chạy lại tứ phân vị, ÁP nó, rồi ĐẾM số giọng
# đổi nhãn. Lượt 19/08 đổi 11 giọng (`VUA` 3,1 -> 3,2), xem `nhan_nha.__doc__`.
SO_GIONG_BANG = 211
ok(f"1a bảng có {SO_GIONG_BANG} giọng", len(nhan_nha.BANG) == SO_GIONG_BANG,
   f"{len(nhan_nha.BANG)}")
ok("1b mọi giá trị là số dương hợp lý (1..8 nửa cung)",
   all(isinstance(v, (int, float)) and 1.0 <= v <= 8.0
       for v in nhan_nha.BANG.values()))
_xs = sorted(nhan_nha.BANG.values())
import statistics as _st  # noqa: E402

_q = _st.quantiles(_xs, n=4)
ok("1c ngưỡng = TỨ PHÂN VỊ CỦA CHÍNH BẢNG (làm tròn 1 chữ số)",
   (round(_q[2], 1), round(_q[1], 1), round(_q[0], 1))
   == (nhan_nha.RAT_CAO, nhan_nha.CAO, nhan_nha.VUA),
   f"đo {_q[0]:.2f}/{_q[1]:.2f}/{_q[2]:.2f} · mã "
   f"{nhan_nha.VUA}/{nhan_nha.CAO}/{nhan_nha.RAT_CAO}")
ok("1d CHỮ tính từ SỐ ĐÃ LÀM TRÒN (Jenny 3,06 không được ghi ngược)",
   all(nhan_nha.chu(round(v, 1)) in nhan_nha.nhan(k)
       for k, v in nhan_nha.BANG.items()))
ok("1e nhãn KHÔNG EMOJI",
   all(ord(c) < 0x2190 for k in nhan_nha.BANG for c in nhan_nha.nhan(k)))
# 19/08/2026 — MỆNH ĐỀ NÀY MẠNH LÊN, KHÔNG PHẢI YẾU ĐI. Trước đây nó chỉ hỏi
# "chưa đo -> nhãn rỗng", tức chỉ có HAI trạng thái. Nay có BA (xem
# `nhan_nha.CHUA_DO`), nên phải chấm cả ba — và chấm luôn điều quan trọng nhất:
# nhánh "chưa đo" **KHÔNG được chứa một chữ số nào**. Bịa số cạnh tên giọng mới
# là cái bẫy mục này sinh ra để chặn, chuỗi rỗng chỉ là một cách chặn.
# `tr-TR-Ahmet` nay ĐÃ có bằng chứng đọc thật (`giong_doc`) nên nó là ca "chưa
# đo"; ca "không biết gì" phải lấy mã KHÔNG có trong cả hai bảng.
_CHUA_DO = "tr-TR-AhmetNeural"      # đọc được thật, chưa đo nhấn nhá
_LA = "xx-YY-KhongTonTaiNeural"     # không có trong bảng nào
ok("1f ba trạng thái nhãn phân biệt được, 'chưa đo' KHÔNG có chữ số",
   nhan_nha.nhan("en-US-AndrewNeural").strip().startswith("- nhấn nhá")
   and nhan_nha.nhan(_CHUA_DO) == nhan_nha.CHUA_DO
   and not any(c.isdigit() for c in nhan_nha.nhan(_CHUA_DO))
   and nhan_nha.muc(_CHUA_DO) is None
   and nhan_nha.nhan(_LA) == "",
   f"đã đo={nhan_nha.nhan('en-US-AndrewNeural')!r} · "
   f"chưa đo={nhan_nha.nhan(_CHUA_DO)!r} · lạ={nhan_nha.nhan(_LA)!r}")

print("\nCA 2 — luật mở khoá: ĐÃ CHỨNG MINH ĐỌC ĐƯỢC THÌ MỞ")
ok("2a mọi giọng edge trong bảng đều được mở",
   all(giong_mo.nen_mo(k) for k in nhan_nha.BANG if ":" not in k))
# Ca "không mở": nay MỌI giọng trong danh mục edge-tts đều đã có biên bản đọc
# thật, nên ca thử phải là mã KHÔNG có trong bảng nào. Mệnh đề vẫn nguyên giá
# trị và là mệnh đề PHÒNG THỦ quan trọng nhất của file: **có tên trong danh mục
# Microsoft KHÔNG phải là vé vào combo** — phải có biên bản. Ngày Microsoft
# thêm giọng mới, chúng KHÔNG được tự lọt vào trước khi ai đó cho chúng đọc thử.
ok("2b mã KHÔNG có biên bản đọc thì KHÔNG mở (kể cả khi trông đúng dạng)",
   not giong_mo.nen_mo(_LA)
   and not giong_mo.nen_mo("pl-PL-KhongCoThatNeural")
   and not giong_mo.nen_mo("en-US-KhongCoThatNeural"))
ok("2c mã KHÔNG phải edge-tts bị từ chối (ov: · piper: · vnb: · cb:)",
   not any(giong_mo.nen_mo(m) for m in
           ("ov:nam_tre", "piper:vi_VN-vais1000-medium", "vnb:a.wav",
            "cb:en|a.wav", "el:Adam", "")))
# 185 -> 322 · 15 -> 75 thứ tiếng (19/08/2026, lượt kiểm ĐỌC THẬT 137 giọng).
# Đây là TOÀN BỘ danh mục edge-tts của Microsoft, không còn giọng nào bị giữ.
# **NÂNG MỐC = CỔNG CHẶT HƠN, KHÔNG PHẢI NỚI RA**: mỗi giọng cộng thêm đều phải
# có biên bản `(độ dài, RMS)` trong `giong_doc.BANG`, và cổng 83 CA 1 đòi lại
# đúng biên bản đó. Con số này KHÔNG được sửa cho khớp mã — nó chỉ đổi khi có
# một lượt `_do_doc_that.py` mới chạy thật.
ok("2d số giọng edge mở ra = 322, phủ 75 thứ tiếng (TRỌN danh mục)",
   giong_mo.so_giong_mo() == 322 and len(giong_mo.tieng_da_mo()) == 75,
   f"{giong_mo.so_giong_mo()} giọng / {len(giong_mo.tieng_da_mo())} tiếng")
_dem = giong_mo.dem_theo_tieng()
ok("2e đủ 47 giọng tiếng Anh (bảng cũ) + tiếng khác đã mở",
   _dem.get("en") == 47 and _dem.get("es", 0) >= 40 and _dem.get("ar", 0) >= 30,
   f"en={_dem.get('en')} es={_dem.get('es')} ar={_dem.get('ar')}")

print("\nCA 3 — giọng theo kênh + XOAY VÒNG TIỀN ĐỊNH")
from app.core import giong_kenh as gk  # noqa: E402
import app.services as SV  # noqa: E402

_p1 = SV.create_project("Kênh A", "nhóm 1")
_p2 = SV.create_project("Kênh B", "nhóm 1")
ok("3a kênh chưa gán -> trả GIỌNG CHUNG (hành vi cũ không đổi)",
   gk.giong_cho_video(_p1, video_id=7, mac_dinh="en-US-AriaNeural")[0]
   == "en-US-AriaNeural")
gk.dat_giong_kenh(_p1, "en-GB-RyanNeural")
ok("3b gán giọng riêng -> đúng giọng đó",
   gk.giong_cho_video(_p1, video_id=7, mac_dinh="en-US-AriaNeural")[0]
   == "en-GB-RyanNeural")
ok("3c kênh KHÁC không bị lây",
   gk.giong_cho_video(_p2, video_id=7, mac_dinh="en-US-AriaNeural")[0]
   == "en-US-AriaNeural")
_ro = ["en-US-AndrewNeural", "en-GB-SoniaNeural", "en-AU-NatashaNeural"]
gk.dat_ro_giong(_p1, _ro)
ok("3d đặt rổ -> đọc lại đúng thứ tự người dùng chọn",
   gk.ro_giong(_p1) == _ro)
_g = [gk.giong_cho_video(_p1, video_id=i)[0] for i in range(30)]
ok("3e xoay vòng: 30 video KHÔNG ra cùng một giọng",
   len(set(_g)) == len(_ro), f"{len(set(_g))} giọng khác nhau")
ok("3f MỘT VIDEO = MỘT GIỌNG (gọi 5 lần ra cùng kết quả)",
   len({gk.giong_cho_video(_p1, video_id=7)[0] for _ in range(5)}) == 1)
ok("3g rổ ĐÈ giọng riêng (đặt rổ là hành động rõ ràng hơn)",
   gk.giong_cho_video(_p1, video_id=7)[0] in _ro)
ok("3h thiếu khoá video -> KHÔNG bốc ngẫu nhiên, và NÓI RA là đã lùi",
   "THIẾU khoá" in gk.giong_cho_video(_p1)[1])

# ---- TIỀN ĐỊNH QUA TIẾN TRÌNH KHÁC — mệnh đề TRUNG TÂM của CA 3 ----
_ma = (
    "import os,sys,json;sys.path.insert(0,r'%s');"
    "from app.core import giong_kenh as gk;"
    "print(json.dumps([gk.giong_cho_video(%d, video_id=i)[0] "
    "for i in range(30)]))" % (str(REPO), _p1))
_kq = []
for _seed in ("0", "1", "12345"):
    _env = dict(os.environ)
    _env["PYTHONHASHSEED"] = _seed
    _r = subprocess.run([sys.executable, "-c", _ma], capture_output=True,
                        text=True, encoding="utf-8", errors="replace",
                        env=_env, timeout=300)
    _d = [l for l in (_r.stdout or "").splitlines() if l.startswith("[")]
    _kq.append(json.loads(_d[-1]) if _d else None)
ok("3i TIỀN ĐỊNH qua 3 TIẾN TRÌNH có PYTHONHASHSEED khác nhau "
   "(crc32, KHÔNG phải hash())",
   all(k == _g for k in _kq if k is not None) and all(_kq),
   f"{sum(1 for k in _kq if k == _g)}/3 tiến trình khớp")

print("\nCA 4 — chia giọng cho 300 kênh")
_chia = gk.chia_giong_cho_kenh(range(1, 301), _ro)
ok("4a 300 kênh chia đều 3 giọng",
   len(_chia) == 300 and len(set(_chia.values())) == 3
   and max(sum(1 for v in _chia.values() if v == g) for g in _ro)
   - min(sum(1 for v in _chia.values() if v == g) for g in _ro) <= 1)
_chia2 = gk.chia_giong_cho_kenh(list(range(1, 401)), _ro)
ok("4b THÊM 100 kênh mới KHÔNG đổi giọng của kênh cũ",
   all(_chia2[p] == _chia[p] for p in _chia))
ok("4c rổ rỗng -> {} (không ném, không đoán)",
   gk.chia_giong_cho_kenh([1, 2], []) == {})
ok("4d rổ gợi ý lấy giọng nhấn nhá cao nhất, đúng ngôn ngữ",
   len(gk.ro_goi_y("en", 5)) == 5
   and all(m.startswith("en-") for m in gk.ro_goi_y("en", 5))
   and gk.ro_goi_y("en", 5)[0] == max(
       (m for m in nhan_nha.BANG if m.startswith("en-")),
       key=lambda m: nhan_nha.BANG[m]))
ok("4e nhãn kênh HIỆN giọng chung THẬT khi chưa gán "
   "(không ghi '(mặc định)' trơn)",
   "en-US-AriaNeural" in gk.nhan_giong_kenh(_p2, "en-US-AriaNeural"))
ok("4f nhãn KHÔNG EMOJI",
   all(ord(c) < 0x2190 for c in gk.nhan_giong_kenh(_p1, "en-US-AriaNeural")))

print("\nCA 5 — chốt giọng lúc XẾP JOB, không tra lại lúc xuất")
_don = gk.chot_giong(_p1, video_id=7, mac_dinh="en-US-AriaNeural")
ok("5a đơn thuốc có mã + lý do", bool(_don["giong"]) and bool(_don["vi_sao"]))
ok("5b payload CÓ khoá -> dùng khoá đó",
   gk.giong_tu_payload(_don, "en-US-AriaNeural") == _don["giong"])
ok("5c payload CŨ (thiếu khoá) -> lùi mặc định, KHÔNG coi là giọng rỗng",
   gk.giong_tu_payload({"video": 1}, "en-US-AriaNeural") == "en-US-AriaNeural")
ok("5d chốt rồi thì đổi rổ KHÔNG đổi job đã xếp",
   (gk.dat_ro_giong(_p1, ["en-US-GuyNeural", "en-US-EmmaNeural"]) or True)
   and gk.giong_tu_payload(_don, "") == _don["giong"])
gk.dat_ro_giong(_p1, _ro)

print("\nCA 6 — Chatterbox: KHÔNG được nạp torch ở tầm module")
from app.core import giong_chatter as gc  # noqa: E402

_cay_gc = _cay(gc)
_imp = _import_muc_module(_cay_gc)
ok("6a KHÔNG import torch/chatterbox/transformers ở tầm module "
   "(Qt + torch = ACCESS VIOLATION)",
   not (_imp & {"torch", "chatterbox", "transformers", "torchaudio",
                "librosa"}),
   f"import tầm module: {sorted(_imp)}")
ok("6b TỰ KIỂM BỘ DÒ: bộ dò phải BẮT được một module có import torch",
   "torch" in _import_muc_module(ast.parse("import torch\nimport os\n")))
ok("6c dò 'đã cài chưa' bằng FILE, KHÔNG bằng find_spec",
   "find_spec" not in _ten_goi(_cay_gc))
_than = {n.name: n for n in ast.walk(_cay_gc)
         if isinstance(n, ast.FunctionDef)}
#: `_chay` phải trả về QUA `_ra` — hàm đóng dấu `_sandbox`. Kiểm "có gọi `_ra`
#: không" chứ không kiểm "có chuỗi `_sandbox` không": bản đầu gán
#: `ket["_sandbox"]` ở DÒNG TRƯỚC `return ket` nên vẫn an toàn mà bộ dò không
#: thấy -> hoặc phải nới bộ dò (mất răng), hoặc sửa mã cho một-cửa. Chọn cách
#: hai: một hàm, một chỗ để hỏng, một chỗ để canh.
def _ret_cua(fn) -> list:
    """`return` THUỘC VỀ hàm này, KHÔNG tính hàm lồng bên trong.

    `ast.walk` đi cả hàm con, nên `return d` của chính `_ra` bị kể là một
    nhánh ra của `_chay` -> cổng đỏ oan 1 mục (đã sập lượt đầu).
    """
    ra = []
    for n in ast.iter_child_nodes(fn):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for c in ast.walk(n):
            if isinstance(c, ast.Return) and c.value is not None:
                ra.append(c)
    return ra


_ret = _ret_cua(_than["_chay"])
def _qua_ra(node) -> bool:
    return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
               and c.func.id == "_ra" for c in ast.walk(node))
ok("6d MỌI đường `return` của _chay đi qua `_ra` (đóng dấu `_sandbox`) "
   "— Path('') = thư mục đang làm việc, đã xoá sạch cây mã một lần",
   len(_ret) >= 3 and all(_qua_ra(r) for r in _ret),
   f"{sum(_qua_ra(r) for r in _ret)}/{len(_ret)} nhánh return")
ok("6d2 `_ra` thật sự gán khoá `_sandbox` (không phải cái tên cho đẹp)",
   any(isinstance(n, ast.Assign)
       and any(isinstance(t, ast.Subscript)
               and isinstance(t.slice, ast.Constant)
               and t.slice.value == "_sandbox" for t in n.targets)
       for f in ast.walk(_than["_chay"]) if isinstance(f, ast.FunctionDef)
       and f.name == "_ra" for n in ast.walk(f)))
ok("6e dọn hộp cát qua CỬA CHUNG xoa_an_toan, không tự rmtree",
   "don_thu_muc" in _ten_goi(_cay_gc)
   and "rmtree" not in _ten_goi(_cay_gc))
ok("6f mã thiếu NGÔN NGỮ bị TỪ CHỐI, không đoán 'en'",
   gc.tach_ma("cb:D:/a.wav") == ("", "")
   and gc.tach_ma("cb:xx|D:/a.wav") == ("", "")
   and gc.tach_ma("cb:en|D:/a.wav") == ("en", "D:/a.wav"))
ok("6g KHÔNG có tiếng Việt trong bảng 23 tiếng (đọc từ gói, không từ quảng cáo)",
   "vi" not in gc.TIENG and len(gc.TIENG) == 23)
ok("6h nhãn mang ĐỦ 3 cảnh báo (giấy phép · chất lượng · máy)",
   all(s in gc.nhan_giong("cb:en|D:/a.wav", "X")
       for s in ("MIT", "KHÔNG có tiếng Việt", "GPU")))
ok("6i nhãn KHÔNG EMOJI",
   all(ord(c) < 0x2190 for c in gc.nhan_giong("cb:en|D:/a.wav", "X")))
ok("6j thiếu Chatterbox -> doc_loat trả toàn False, KHÔNG NÉM",
   gc.doc_loat(["a", "b"], ["x.mp3", "y.mp3"], "cb:sai") == [False, False])

print("\nCA 7 — nhân bản giọng: kiểm mẫu + sổ + cảnh báo pháp lý")
from app.core import nhan_ban_giong as nb  # noqa: E402

ok("7a cảnh báo pháp lý nêu ĐÍCH DANH hãng bán giọng",
   all(s in nb.CANH_BAO_PHAP_LY for s in ("Vbee", "ElevenLabs", "BÁN app")))
ok("7b cảnh báo KHÔNG EMOJI",
   all(ord(c) < 0x2190 for c in nb.CANH_BAO_PHAP_LY))
for _t, _d in (("rỗng", ""), ("None", None), ("không có thật", "D:/k/o.wav"),
               ("thư mục", str(REPO))):
    _r = nb.kiem_mau(_d)
    ok(f"7c mẫu {_t} -> ok=False kèm lý do TIẾNG VIỆT",
       _r["ok"] is False and bool(_r["loi"]))
ok("7d tiếng Việt -> VieNeu · tiếng khác -> Chatterbox",
   nb.goi_y_may("vi") == nb.MAY_VIENEU and nb.goi_y_may("en")
   == nb.MAY_CHATTER and nb.goi_y_may("") == nb.MAY_VIENEU)
ok("7e Chatterbox TỪ CHỐI tiếng Việt (không im lặng đọc bậy)",
   "KHÔNG có tiếng Việt" in
   nb.them_giong("x", "D:/k/o.wav", lang="vi", may=nb.MAY_CHATTER)["loi"]
   or "không đọc được" in
   nb.them_giong("x", "D:/k/o.wav", lang="vi", may=nb.MAY_CHATTER)["loi"])
ok("7f sổ hỏng -> {} chứ KHÔNG ghi đè (mất sạch giọng đã đặt tên)",
   (nb.duong_so().parent.mkdir(parents=True, exist_ok=True) or True)
   and (nb.duong_so().write_text("{ hỏng", encoding="utf-8") or True)
   and nb._doc_so() == {} and nb.duong_so().exists())
nb.duong_so().unlink()
ok("7g tên tiếng Việt -> tên file an toàn, không rỗng",
   nb._slug("Giọng chị Lan") == "giong_chi_lan"
   and nb._slug("Đường ĐẶC BIỆT") == "duong_dac_biet"
   and bool(nb._slug("!!!")))
ok("7h mã giọng dùng tiền tố NGUYÊN BẢN của máy (vnb: / cb:), "
   "không đẻ tiền tố thứ ba",
   nb.la_giong_nhan_ban("vnb:a.wav") and nb.la_giong_nhan_ban("cb:en|a.wav")
   and not nb.la_giong_nhan_ban("en-US-AriaNeural"))
_cay_nb = _cay(nb)
ok("7i xoá mẫu có canh đường dẫn phải nằm TRONG thư mục mẫu",
   "sua_mau_mat" in _than_nb if (_than_nb := {n.name for n in
                                              ast.walk(_cay_nb)
                                              if isinstance(n,
                                                            ast.FunctionDef)})
   else False)
ok("7j mẫu MẤT thì BÁO, KHÔNG tự xoá khỏi sổ",
   "sua_mau_mat" in _than_nb and "unlink" not in _ten_goi(_cay_nb))

print("\nCA 8 — THỬ PHÁ: gỡ chốt thì cổng có ĐỎ không")
_ph = ast.parse("def _chay():\n if x:\n  return {'ok': False}\n return _ra(1)\n")
_ret_ph = _ret_cua([n for n in ast.walk(_ph)
                    if isinstance(n, ast.FunctionDef)][0])
ok("8a bộ dò `_ra` BẮT được nhánh return đi tắt (không đóng dấu _sandbox)",
   len(_ret_ph) == 2 and not all(_qua_ra(r) for r in _ret_ph),
   f"{sum(_qua_ra(r) for r in _ret_ph)}/{len(_ret_ph)} nhánh qua _ra")
ok("8b bộ dò find_spec BẮT được module dùng find_spec",
   "find_spec" in _ten_goi(ast.parse("import importlib\n"
                                     "x = importlib.util.find_spec('a')\n")))


class _Gia:
    """Giả một `giong_cho_video` dùng hash() — CA 3i phải bắt được."""


_ma_hash = (
    "import os,sys,json,zlib;sys.path.insert(0,r'%s');"
    "ro=%r;print(json.dumps([ro[hash('v%%d'%%i)%%len(ro)] "
    "for i in range(30)]))" % (str(REPO), _ro))
_kq_h = []
for _seed in ("0", "1", "12345"):
    _env = dict(os.environ)
    _env["PYTHONHASHSEED"] = _seed
    _r = subprocess.run([sys.executable, "-c", _ma_hash], capture_output=True,
                        text=True, encoding="utf-8", errors="replace",
                        env=_env, timeout=120)
    _d = [l for l in (_r.stdout or "").splitlines() if l.startswith("[")]
    _kq_h.append(json.loads(_d[-1]) if _d else None)
ok("8c TỰ KIỂM CA 3i: bản dùng hash() RA KẾT QUẢ KHÁC NHAU giữa các "
   "tiến trình -> phép đo có răng",
   len({json.dumps(k) for k in _kq_h if k is not None}) > 1,
   f"{len({json.dumps(k) for k in _kq_h if k})} kết quả khác nhau / 3 lượt")

print("\n" + "=" * 72)
print(f"ĐẠT {DAT} · HỎNG {HONG} · BỎ QUA {BOQUA}")
if _HONG:
    print("HỎNG: " + " | ".join(_HONG))
raise SystemExit(1 if HONG else 0)
