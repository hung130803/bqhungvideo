# -*- coding: utf-8 -*-
"""CỔNG 91 — NHÂN BẢN GIỌNG **ĐA NGÔN NGỮ** ĐÃ NỐI VÀO GIAO DIỆN, VÀ BỐN CHỐT
ĐỀU CÓ RĂNG.

**SỐ CỔNG LÀ 91 — lấy bằng cách ĐỌC `_chay_hoi_quy.CONG`, không đếm theo trí
nhớ.** Danh sách đó đang dùng tới 90; trùng số là hai cổng **ghi đè
`_kq<N>.txt` của nhau** (bài học 70 vs 69, rồi 85 vs 81).

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ CỔNG NÀY
═══════════════════════════════════════════════════════════════════════════
Anh Hùng cần **NHIỀU THỨ TIẾNG** (Anh/Trung/Nhật...), không chỉ tiếng Việt.
Đường nhân bản đang có trong hộp «Giọng của tôi» là **VieNeu**, và VieNeu là
model TIẾNG VIỆT: bộ phiên âm của nó **từ chối `lang="en"`**, còn giọng "Adam"
của nó đọc tiếng Việt sai **2,5-5,0%** trong khi đọc tiếng Anh sai **12,8%**.
Tức hộp đó **chỉ mở đúng một cửa** — `grep 'lang="vi"' thay_giong_dialog.py`.

`Chatterbox` (`cb:`) bù đúng chỗ đó: MIT sạch (bán được), 23 thứ tiếng, nhân
bản chạy xuyên ngôn ngữ THẬT (ECAPA cos 0,727 vs 0,151). Nhưng nó mang **bốn
cái giá**, và cổng này canh đúng bốn cái đó — không canh "tính năng có chạy
không", mà canh **"app có NÓI THẬT về giá không"**.

    CHỐT 1  ĐỌC LOẠN NHỊP  — CA 3
    CHỐT 2  BẮT BUỘC GPU   — CA 4
    CHỐT 3  ĐÓNG DẤU CHÌM  — CA 5
    CHỐT 4  KHÔNG có `vi`  — CA 1

═══════════════════════════════════════════════════════════════════════════
KHÔNG GỌI MẠNG · KHÔNG NẠP MODEL · KHÔNG ĐỐT GPU · KHÔNG TỐN LƯỢT GROQ
═══════════════════════════════════════════════════════════════════════════
Toàn bộ là hàm thuần + **ffmpeg THẬT** (thành phần thật, quy tắc sắt của
repo) trên WAV tự sinh bằng `lavfi`. Không file nào của anh Hùng bị đụng.

**RANH GIỚI CỨNG:** cổng này KHÔNG nhân bản giọng người thật nào. Mọi "mẫu"
ở đây là WAV `sine` do ffmpeg sinh ra; cổng **không hề chạm** tới
`_mau_giong/adam_clone.wav` (nguồn của file đó là bản sao một giọng ElevenLabs
thương mại).

═══════════════════════════════════════════════════════════════════════════
QUÉT TĨNH BẰNG **AST**, VÀ ĐỌC **GIÁ TRỊ HẰNG** THAY VÌ QUÉT MÃ
═══════════════════════════════════════════════════════════════════════════
Repo này đã sập bẫy quét-chuỗi **tám lần**, theo cả hai chiều:
  · ĐỎ OAN  — chính DÒNG GHI CHÚ giải thích bản vá bị kể là vi phạm (47/51/
    53/54/73/80/86);
  · PASS OAN — quét "có mặt không" thì một phép phá giữ nguyên mặt chữ mà đổi
    ý nghĩa vẫn lọt (56d/64).
Nên: mục nào chấm **NỘI DUNG MỘT HẰNG SỐ** thì đọc thẳng giá trị hằng đó
(`gc.CANH_BAO_CL`) — ghi chú quanh nó không với tới được. Mục nào chấm **MÃ**
thì đi bằng `ast`, và đòi giá trị truyền vào phải là **BIỂU THỨC** chứ không
được là hằng số.

Chạy:  .venv\\Scripts\\python.exe _test_nhan_ban_da_ngu.py
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: Hộp cát NGOÀI `%TEMP%` — cùng lý do cổng 88: `%TEMP%` là một trong các thư
#: mục `xoa_an_toan` cấm, đặt hộp cát vào đó là để một chốt KHÁC bắt hộ và mục
#: sẽ ĐẠT vì lý do SAI (bài học cổng 80 LỌT 6).
T = REPO / f"bq_test_nbdn_{os.getpid()}"
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

import config  # noqa: E402

# `config.DATA_DIR` là **Path**, không phải str — `dubbing.py` làm
# `DATA_DIR / "..."` ngay lúc NẠP MODULE, gán chuỗi vào là nổ `TypeError`
# trước cả khi cổng chạy được mục nào.
config.DATA_DIR = T

from PyQt6.QtWidgets import QMessageBox       # noqa: E402

# ---------------------------------------------------------------------------
# HỘP THOẠI PHẢI BỊ VÔ HIỆU **TRƯỚC** KHI DỰNG UI — không phải cho gọn.
# `_nghe_giong_xong` gọi `QMessageBox.warning(...)` khi đọc thử hỏng, mà
# `warning` là MODAL: nó chạy vòng lặp sự kiện riêng và **TREO CỔNG VĨNH
# VIỄN**. Đã sập thật khi viết cổng này — 3 tiến trình python đọng lại, và
# đọc ra thì giống hệt "cổng chạy lâu" chứ không giống "cổng treo".
# Vá thành hàm **ĐẾM** chứ không phải hàm rỗng: hàm rỗng thì mọi mục hỏi
# "app có báo cho người dùng không" tự ĐẠT vì lý do NGƯỢC HẲN (bẫy cổng 67).
# ---------------------------------------------------------------------------
_HOP: list[tuple[str, str]] = []


def _gia_hop(kieu):
    def _f(parent=None, tieu_de="", loi="", *a, **k):
        _HOP.append((kieu, str(tieu_de)))
        return QMessageBox.StandardButton.No
    return staticmethod(_f)


QMessageBox.warning = _gia_hop("warning")          # type: ignore[assignment]
QMessageBox.information = _gia_hop("information")  # type: ignore[assignment]
QMessageBox.question = _gia_hop("question")        # type: ignore[assignment]
QMessageBox.critical = _gia_hop("critical")        # type: ignore[assignment]

# ...và CẤM PHÁT TIẾNG RA LOA (luật cổng 65) — cũng vá thành hàm ĐẾM.
_PHAT: list = []
try:
    import winsound  # noqa: E402

    def _gia_phat(*a, **k):
        _PHAT.append(a)
        return None

    winsound.PlaySound = _gia_phat             # type: ignore[assignment]
except Exception:                                              # noqa: BLE001
    pass

from app.core import dubbing as DUB           # noqa: E402
from app.core import giong_bang as GB         # noqa: E402
from app.core import giong_chatter as CB      # noqa: E402
from app.core import nhan_ban_giong as NB     # noqa: E402

_DAT = 0
_HONG: list[str] = []
_NO_WIN = 0x08000000 if os.name == "nt" else 0


def ok(ten: str, dieu: bool, ghi: str = "") -> bool:
    global _DAT
    if dieu:
        _DAT += 1
        print(f"  ĐẠT  {ten}" + (f"  [{ghi}]" if ghi else ""))
    else:
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f"  [{ghi}]" if ghi else ""))
    return bool(dieu)


def ffmpeg() -> str:
    from config import settings
    return str(getattr(settings, "FFMPEG_PATH", "") or "ffmpeg")


def wav(ten: str, phan: list[tuple[str, float]]) -> Path:
    """Dựng WAV từ danh sách ``[("tieng"|"im", giây)]``. ffmpeg THẬT.

    **`duration=` nằm TRONG biểu thức lavfi, KHÔNG dùng `-t`** — `-t` là tuỳ
    chọn ĐẦU VÀO, đặt sai chỗ làm `anullsrc` ghi vô hạn 115 MB/s và đã đầy ổ C
    420 GB một lần.
    """
    p = T / ten
    vao: list[str] = []
    for kieu, giay in phan:
        vao += ["-f", "lavfi", "-i",
                (f"sine=frequency=320:duration={giay:.3f}:sample_rate=24000"
                 if kieu == "tieng"
                 else f"anullsrc=r=24000:cl=mono:d={giay:.3f}")]
    loc = ("".join(f"[{i}:a]" for i in range(len(phan)))
           + f"concat=n={len(phan)}:v=0:a=1[o]")
    r = subprocess.run(
        [ffmpeg(), "-y", "-v", "error"] + vao
        + ["-filter_complex", loc, "-map", "[o]", "-ac", "1", "-ar", "24000",
           str(p)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=120)
    if r.returncode != 0 or not p.exists():
        raise RuntimeError(f"ffmpeg dựng wav hỏng: {(r.stderr or '')[-300:]}")
    return p


def than_ham(mod, ten: str) -> ast.AST:
    """Nút AST của một hàm, đọc file bằng **utf-8** (không theo bảng mã máy).

    `inspect.getsource` mở file theo bảng mã MẶC ĐỊNH (cp1252 trên máy này)
    nên docstring tiếng Việt ra mojibake rồi `ast.parse` nổ — bài học cổng 71.
    """
    src = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    raise LookupError(f"không thấy hàm {ten} trong {mod.__name__}")


def goi_ten(nut: ast.AST) -> set:
    """Tập tên hàm được GỌI trong một nút AST (cả `a.b()` lẫn `b()`)."""
    ra = set()
    for n in ast.walk(nut):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                ra.add(f.attr)
            elif isinstance(f, ast.Name):
                ra.add(f.id)
    return ra


def them_mau(ten: str, lang: str, may: str = "") -> str:
    """Ghi thẳng một bản ghi vào sổ (không chạy ffmpeg chép mẫu cho nhanh).

    Tên FILE mẫu đặt theo **băm ngắn**, KHÔNG theo `_slug(ten)`: CA 7 cố ý
    dùng tên giọng 200+ ký tự và `_slug` giữ nguyên độ dài đó -> vượt
    MAX_PATH của Windows, cổng chết vì `FileNotFoundError` chứ không phải vì
    mã sai. (Đường THẬT không dính: `_ten_mau_trong` cũng dùng `_slug` nhưng
    người dùng không đặt tên 200 ký tự — và nếu có thì đó là việc RIÊNG, ghi
    ở báo cáo.)
    """
    import hashlib
    # CẮT KHOẢNG TRẮNG HAI ĐẦU y như `them_giong` — `_muc()` tra sổ bằng khoá
    # ĐÃ `.strip()`, nên ghi thẳng một khoá còn khoảng trắng là mọi phép tra
    # sau đó TRƯỢT, `nhan()` trả về nguyên cái tên và mục đo NHẦM một đường
    # khác. (Đã sập một lần khi viết cổng: CA 7b ra 233 ký tự và mục TỰ KIỂM
    # 7e cũng ra 233 — tức nó "ĐẠT" vì lý do sai.)
    ten = str(ten or "").strip()
    d = NB.thu_muc_mau()
    d.mkdir(parents=True, exist_ok=True)
    p = d / (hashlib.md5(ten.encode("utf-8")).hexdigest()[:12] + ".wav")
    p.write_bytes(b"\0" * 5000)
    so = NB._doc_so()
    so[ten] = {"mau": str(p), "may": may or NB.goi_y_may(lang), "lang": lang,
               "giay": 8.0, "nguon": "cổng test"}
    NB._ghi_so(so)
    return str(p)


# ===========================================================================
def ca1() -> None:
    """CHỐT 4 — `vi` -> VieNeu · tiếng khác -> Chatterbox, ĐƯỜNG CHỌN TỰ LÀM."""
    print("\nCA 1 — CHỐT 4: hai bộ BỔ SUNG nhau, app tự chọn")
    ok("1a vi -> VieNeu", NB.goi_y_may("vi") == NB.MAY_VIENEU)
    ok("1a' rỗng -> VieNeu (mặc định an toàn)",
       NB.goi_y_may("") == NB.MAY_VIENEU)
    ok("1b en/ja/zh -> Chatterbox",
       all(NB.goi_y_may(x) == NB.MAY_CHATTER for x in ("en", "ja", "zh")))
    ok("1c Chatterbox KHÔNG có `vi` trong bảng tiếng", "vi" not in CB.TIENG,
       f"{len(CB.TIENG)} thứ tiếng")

    them_mau("G Anh", "en")
    them_mau("G Việt", "vi")
    ok("1d lang=en -> mã `cb:en|`",
       NB.ma_giong("G Anh").startswith("cb:en|"), NB.ma_giong("G Anh")[:24])
    ok("1e lang=vi -> mã `vnb:`",
       NB.ma_giong("G Việt").startswith("vnb:"), NB.ma_giong("G Việt")[:24])

    # Ép SAI máy phải bị CHẶN, không im lặng nhận rồi đọc ra chuỗi vô nghĩa.
    r = NB.them_giong("G Sai", str(T / "khong_co.wav"), lang="vi",
                      may=NB.MAY_CHATTER)
    ok("1f ép Chatterbox đọc tiếng Việt -> BỊ CHẶN, có lý do",
       (not r.get("ok")) and "Chatterbox" in str(r.get("loi")),
       str(r.get("loi"))[:60])

    # UI: `_luu` phải lấy `lang` TỪ WIDGET, không ghi cứng. Quét AST và đòi
    # giá trị truyền vào là BIỂU THỨC — hằng số `"vi"` là bản CŨ (cổng 56d:
    # quét "có mặt không" thì phép phá đổi thành hằng vẫn lọt).
    from app.ui import thay_giong_dialog as TGD
    nut = than_ham(TGD, "_luu")
    dat_lang = [k for n in ast.walk(nut) if isinstance(n, ast.Call)
                for k in n.keywords if k.arg == "lang"]
    ok("1g `_luu` có truyền `lang=`", len(dat_lang) == 1, f"{len(dat_lang)} chỗ")
    ok("1h `lang=` là BIỂU THỨC, KHÔNG phải hằng số",
       bool(dat_lang) and not isinstance(dat_lang[0].value, ast.Constant),
       ast.dump(dat_lang[0].value)[:48] if dat_lang else "-")
    # ...và KHÔNG được tự chọn máy lần thứ hai ở tầng UI: hai bản sao của luật
    # chọn máy là hai chỗ để lệch nhau.
    ok("1i `_luu` KHÔNG tự truyền `may=` (để `goi_y_may` quyết)",
       not [k for n in ast.walk(nut) if isinstance(n, ast.Call)
            for k in n.keywords if k.arg == "may"])


def ca2() -> None:
    """Tiền tố `cb:` đăng ký ĐỦ BA CỬA — kiểm bằng AST **và** GỌI THẬT."""
    print("\nCA 2 — `cb:` phải được nhận ở CẢ BA cửa (sót 1 = LẪN HAI GIỌNG)")
    ok("2a `giong_bang.nguon('cb:...')` -> chatter",
       GB.nguon("cb:en|D:/m.wav") == GB.CHATTER, GB.nguon("cb:en|D:/m.wav"))

    for ten in ("_synth_all", "_synth_all_words"):
        ok(f"2b AST: `{ten}` GỌI `_chatter_hay_khong`",
           "_chatter_hay_khong" in goi_ten(than_ham(DUB, ten)))
    ok("2c AST: `_synth_all_words` lấy mốc qua BỘ GIÓNG HÀNG",
       "_moc_giong_hang" in goi_ten(than_ham(DUB, "_synth_all_words")))

    # GỌI THẬT — quét chuỗi thì một phép phá giữ mặt chữ mà đổi ý nghĩa vẫn
    # lọt. Vá `giong_chatter.doc_loat` thành hàm ĐẾM: nó phải được gọi.
    goi: list[str] = []
    that = CB.doc_loat

    def gia(texts, paths, voice, rate="+0%", han_giay=3600, on_msg=None):
        goi.append(voice)
        for p in paths:
            Path(p).write_bytes(b"\0" * 4000)
        return [True] * len(texts)

    CB.doc_loat = gia                          # type: ignore[assignment]
    co = CB.co_chatter
    CB.co_chatter = lambda: True               # type: ignore[assignment]
    # BỘ GIÓNG HÀNG bị vá TẮT trong mục này — CỐ Ý, và đây là lý do: nó nạp
    # model MMS_FA 1,18 GB ở tiến trình con, tức mục sẽ đo THỜI GIAN NẠP
    # MODEL chứ không đo cửa rẽ, và nó nhấp nháy theo việc máy đã tải model
    # hay chưa. Việc "cửa `cb:` có đi qua bộ gióng hàng không" đã được mục 2c
    # chấm bằng AST — hai mục, hai mệnh đề, không cái nào gánh hộ cái nào.
    moc_that = DUB._moc_giong_hang

    async def moc_gia(texts, paths, ok_, moc, lang, voice):
        return list(moc)

    DUB._moc_giong_hang = moc_gia              # type: ignore[assignment]
    try:
        mau = str(wav("mau_cb.wav", [("tieng", 1.0)]))
        ma = CB.ma_nhan_ban(mau, "en")
        # THỨ TỰ THAM SỐ LÀ `(texts, voice, paths)` — đảo `voice`/`paths` thì
        # mã giọng thành đường dẫn, mọi cửa rẽ trượt, và lượt chạy rơi xuống
        # nhánh edge-tts **GỌI MẠNG THẬT** rồi TREO. Đã sập một lần khi viết
        # cổng này (3 tiến trình đọng lại).
        p1 = [str(T / "r1.wav")]
        r1 = asyncio.run(DUB._synth_all(["hello"], ma, p1))
        n1 = len(goi)
        p2 = [str(T / "r2.wav")]
        r2 = asyncio.run(DUB._synth_all_words(["hello"], ma, p2))
        ok("2d GỌI THẬT `_synth_all` rẽ vào Chatterbox",
           n1 == 1 and goi[0] == ma and all(r1), f"{n1} lượt")
        ok("2e GỌI THẬT `_synth_all_words` rẽ vào Chatterbox",
           len(goi) == 2 and goi[1] == ma and all(r2[0]),
           f"{len(goi)} lượt")
    finally:
        CB.doc_loat = that                     # type: ignore[assignment]
        CB.co_chatter = co                     # type: ignore[assignment]
        DUB._moc_giong_hang = moc_that         # type: ignore[assignment]

    # TỰ KIỂM BỘ DÒ: mã KHÔNG phải `cb:` thì cửa rẽ KHÔNG được nhận —
    # nếu không, mục 2d/2e chỉ là con dấu.
    # Hỏi thẳng `_chatter_hay_khong` chứ KHÔNG chạy `_synth_all` với giọng
    # edge-tts: đường đó gọi MẠNG THẬT (4 lượt thử lại), làm cổng vừa chậm
    # vừa NHẤP NHÁY theo đường truyền — mà mệnh đề cần chấm chỉ là cửa rẽ.
    dung_e, lui_e = DUB._chatter_hay_khong("vi-VN-HoaiMyNeural")
    ok("2f TỰ KIỂM: giọng edge-tts KHÔNG rẽ vào Chatterbox",
       (not dung_e) and lui_e == "vi-VN-HoaiMyNeural", f"{dung_e} · {lui_e}")

    # MỆNH ĐỀ CỔNG 63 — đừng đẻ chỗ gọi `_synth_all_words` thứ tư.
    from app.core import thay_giong as TG
    src = Path(inspect.getfile(TG)).read_text(encoding="utf-8")
    n = sum(1 for x in ast.walk(ast.parse(src))
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
            and x.func.attr == "_synth_all_words")
    ok("2g `thay_giong.py` vẫn ĐÚNG 3 chỗ gọi `_synth_all_words`", n == 3,
       f"{n} chỗ")


def ca3() -> None:
    """CHỐT 1 — cắt khoảng lặng GIỮA CÂU (ffmpeg THẬT)."""
    print("\nCA 3 — CHỐT 1: đọc loạn nhịp, cắt lặng GIỮA CÂU")
    p = wav("giua.wav", [("tieng", 1.0), ("im", 1.2), ("tieng", 1.0)])
    dai, ds = CB.khoang_lang_giua(p)
    ok("3a dò ĐÚNG 1 khoảng lặng giữa câu", len(ds) == 1,
       f"{len(ds)} khoảng, dài {dai:.2f}s")
    ok("3b khoảng đó dài ~1,2 giây",
       bool(ds) and 1.0 <= (ds[0][1] - ds[0][0]) <= 1.4,
       f"{(ds[0][1] - ds[0][0]):.2f}s" if ds else "-")

    ra = T / "giua_cat.wav"
    kq = CB.cat_lang_giua(p, ra)
    ok("3c cắt được, file ra dùng được",
       kq["ok"] and ra.exists() and ra.stat().st_size > 1024, str(kq)[:70])
    ok("3d bỏ đúng phần chết, CHỪA lại khoảng nghỉ tự nhiên",
       kq["ok"] and 0.85 <= kq["giay_cat"] <= 1.15,
       f"bỏ {kq.get('giay_cat')}s, còn {kq.get('giay_sau')}s")

    # LỀ HAI ĐẦU LÀ VIỆC CỦA `cat_le_loat` — cắt ở đây nữa là làm hai lần một
    # việc, mà lần này thì không ai DỜI MỐC TỪNG CHỮ theo.
    p2 = wav("le.wav", [("im", 1.5), ("tieng", 1.0), ("im", 1.5)])
    _d2, ds2 = CB.khoang_lang_giua(p2)
    ok("3e lề HAI ĐẦU KHÔNG bị đụng (chừa cho `cat_le_loat`)", not ds2,
       f"{len(ds2)} khoảng")

    # Nghỉ ở dấu phẩy (0,25s) phải GIỮ — cắt nó là nghe dồn chữ.
    p3 = wav("ngan.wav", [("tieng", 1.0), ("im", 0.25), ("tieng", 1.0)])
    _d3, ds3 = CB.khoang_lang_giua(p3)
    ok("3f khoảng lặng NGẮN (0,25s) KHÔNG bị cắt", not ds3,
       f"{len(ds3)} khoảng")

    # LƯỚI AN TOÀN: bộ dò hiểu nhầm cả đoạn nói nhỏ là "im" thì bản "đã chữa"
    # là một file MẤT CHỮ mà rc vẫn 0 — họ bẫy "phép đo hỏng phát chứng nhận".
    p4 = wav("gan_im.wav", [("tieng", 0.2), ("im", 3.0), ("tieng", 0.2),
                            ("im", 3.0), ("tieng", 0.2)])
    kq4 = CB.cat_lang_giua(p4, T / "gan_im_cat.wav")
    ok("3g cắt QUÁ TAY -> TỪ CHỐI, giữ nguyên bản gốc",
       (not kq4["ok"]) and "quá tay" in str(kq4.get("ly_do")),
       str(kq4.get("ly_do"))[:60])

    # `doc_loat` phải THẬT SỰ gọi nó, và gọi TRƯỚC `_ep_khung`.
    nut = than_ham(CB, "doc_loat")
    ok("3h `doc_loat` GỌI `cat_lang_giua`", "cat_lang_giua" in goi_ten(nut))
    src_dl = ast.unparse(nut)
    ok("3i cắt TRƯỚC khi ép khung (cắt sau là ép méo rồi mới bỏ chỗ trống)",
       src_dl.find("cat_lang_giua") < src_dl.find("_ep_khung"))

    # TỰ KIỂM BỘ DÒ — không có mục này thì 3a/3c chỉ là con dấu.
    cu = CB.LANG_GIUA_CAT_TU
    CB.LANG_GIUA_CAT_TU = 99.0                 # type: ignore[assignment]
    try:
        _d5, ds5 = CB.khoang_lang_giua(p)
        kq5 = CB.cat_lang_giua(p, T / "tu_kiem.wav")
    finally:
        CB.LANG_GIUA_CAT_TU = cu               # type: ignore[assignment]
    ok("3j TỰ KIỂM: nới ngưỡng -> bộ dò TRƯỢT (mục 3a có răng)",
       (not ds5) and (not kq5["ok"]))

    # ĐỌC LAN MAN: cắt lặng KHÔNG chữa được, nên phải KÊU chứ đừng im.
    ok("3k câu 5 ký tự đọc 7,15 giây -> bị KÊU",
       CB.nghi_doc_lan("Okay.", 7.15) > 3.0, f"x{CB.nghi_doc_lan('Okay.', 7.15)}")
    ok("3l câu dài đọc đúng nhịp -> KHÔNG kêu oan",
       CB.nghi_doc_lan("The storm knocked out power to the village.", 3.1)
       == 0.0)
    ok("3m `doc_loat` có ghi log ca lan man",
       "nghi_doc_lan" in goi_ten(than_ham(CB, "doc_loat")))


def ca4() -> None:
    """CHỐT 2 — BẮT BUỘC GPU, và KHÔNG lùi im lặng."""
    print("\nCA 4 — CHỐT 2: máy không GPU thì tính năng KHÔNG TỒN TẠI")
    ok("4a nhãn máy nói ĐÍCH DANH GPU NVIDIA", "GPU NVIDIA" in CB.CANH_BAO_MAY)
    ok("4b nhãn máy mang SỐ ĐO của CPU (0,25)", "0,25" in CB.CANH_BAO_MAY,
       CB.CANH_BAO_MAY[:56])

    # Không GPU -> KHÔNG mời tải 5,59 GB, và phải NÓI VÌ SAO.
    cu = CB.co_gpu_nvidia
    CB.co_gpu_nvidia = lambda: False           # type: ignore[assignment]
    try:
        vs = CB.vi_sao_khong_cai()
    finally:
        CB.co_gpu_nvidia = cu                  # type: ignore[assignment]
    ok("4c không GPU -> `vi_sao_khong_cai` khác rỗng", bool(vs))
    ok("4d ...và nêu ĐÍCH DANH lý do GPU + số 0,25",
       "GPU NVIDIA" in vs and "0,25" in vs, vs[:64])
    ok("4e ...và chỉ đường sang VieNeu (tiếng Việt vẫn dùng được)",
       "VieNeu" in vs)

    # LÙI THÌ PHẢI GHI LOG. Lùi êm mà im lặng = hỏng âm thầm.
    #
    # ═══ 4f HỎI *HÀNH VI*, KHÔNG HỎI "THÂN HÀM CÓ CHỮ `_ghi_log` KHÔNG" ═══
    # Bản cũ hỏi `"_ghi_log" in goi_ten(nut)` và **ĐÃ ĐỂ LỌT** phép phá số 7
    # (`_pha_da_ngu.py`: bỏ đúng lời gọi log của nhánh THIẾU BỘ). Lý do:
    # `_chatter_hay_khong` có **HAI** nhánh lùi, mỗi nhánh một lời gọi
    # `_ghi_log` — gỡ nhánh THIẾU BỘ thì nhánh "mã giọng sai dạng" vẫn còn
    # chữ đó, nên mục tự ĐẠT trong khi máy nhân viên thiếu bộ lùi IM LẶNG.
    # Đây đúng bẫy cổng 80 LỌT 6: **mục canh MỘT chốt cụ thể phải hỏi ĐÚNG
    # chốt đó**; hỏi "có chặn không" chung chung là tự vô hiệu ngay khi có
    # một chốt thứ hai tình cờ phủ lên. Nay BẮT SỔ lời gọi rồi GỌI THẬT đúng
    # nhánh thiếu bộ — hành vi, không phải mặt chữ.
    nut = than_ham(DUB, "_chatter_hay_khong")
    ok("4f' thân hàm có gọi `_ghi_log`", "_ghi_log" in goi_ten(nut))
    # ...và lùi về giọng ĐÚNG THỨ TIẾNG, không lùi về giọng Việt.
    co = CB.co_chatter
    cu_log = CB._ghi_log
    so_log: list = []
    CB.co_chatter = lambda: False              # type: ignore[assignment]
    CB._ghi_log = lambda d: so_log.append(str(d))   # type: ignore[assignment]
    try:
        dung, lui = DUB._chatter_hay_khong("cb:ja|D:/m.wav")
    finally:
        CB.co_chatter = co                     # type: ignore[assignment]
        CB._ghi_log = cu_log                   # type: ignore[assignment]
    ok("4f THIẾU BỘ -> lùi mà VẪN GHI LOG (gọi THẬT, không quét chuỗi)",
       len(so_log) == 1,
       (so_log[0][:60] if so_log else "KHÔNG ghi một dòng nào"))
    ok("4f'' ...và dòng log nói ĐÍCH DANH là đang LÙI",
       bool(so_log) and "LÙI" in so_log[0].upper())
    ok("4g thiếu bộ -> KHÔNG dùng Chatterbox", not dung)
    ok("4h ...lùi về giọng ĐÚNG TIẾNG (ja), không phải giọng Việt",
       lui.startswith("ja-"), lui)

    # ALL-OR-NOTHING: 18/20 câu cũng phải bỏ cả loạt, không trộn hai giọng.
    nut2 = than_ham(CB, "doc_loat")
    src = ast.unparse(nut2)
    ok("4i `doc_loat` all-or-nothing (thiếu câu -> trả toàn False)",
       "[False] * n" in src.replace("  ", " "))


def ca5() -> None:
    """CHỐT 3 — ĐÓNG DẤU CHÌM: anh Hùng BÁN video, phải cho biết."""
    print("\nCA 5 — CHỐT 3: đóng dấu chìm Perth, không tắt được")
    ok("5a hằng `DONG_DAU_CHIM` nói KHÔNG TẮT ĐƯỢC",
       "KHÔNG TẮT ĐƯỢC" in CB.DONG_DAU_CHIM)
    ok("5b nhãn đầy đủ mang vế đóng dấu chìm",
       "ĐÓNG DẤU CHÌM" in CB.nhan_giong("cb:en|D:/m.wav", "G"))
    ok("5c bản GỌN (dòng combo) cũng mang vế đó",
       "ĐÓNG DẤU CHÌM" in CB.canh_bao_gon(), CB.canh_bao_gon())
    ok("5d cảnh báo chất lượng cũng nhắc",
       "ĐÓNG DẤU CHÌM" in CB.CANH_BAO_CL)

    them_mau("G Anh", "en")
    dong = GB.dong_day_du(NB.ma_giong("G Anh"), NB.nhan("G Anh"))
    ok("5e DÒNG COMBO THẬT của giọng `cb:` mang vế đóng dấu chìm",
       "ĐÓNG DẤU CHÌM" in dong, dong[-46:])


def ca6() -> None:
    """NHÃN PHẢI KHỚP ĐƯỜNG MÃ THẬT SỰ ĐI (`CANH_BAO_CL` từng nói sai)."""
    print("\nCA 6 — nhãn nói THẬT về đường lấy mốc")
    # Đọc GIÁ TRỊ HẰNG, không quét mã: ghi chú quanh nó không với tới được,
    # nên mục này không thể ĐỎ OAN kiểu 47/51/53/73.
    s = CB.CANH_BAO_CL
    ok("6a KHÔNG còn tả 'moi cửa sau'", "CỬA SAU" not in s.upper())
    ok("6b KHÔNG còn con số 76 ms của đường không tồn tại", "76 ms" not in s)
    ok("6c NÓI RA đường thật: bộ gióng hàng", "GIÓNG HÀNG" in s.upper())
    ok("6d mang SỐ ĐO phủ mốc của đường thật", "100,0%" in s, s[:70])

    # ...và chứng minh "cửa sau" đó THẬT SỰ không có trong mã app.
    xau: list[str] = []
    for f in sorted((REPO / "app").rglob("*.py")):
        try:
            cay = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(cay):
            if isinstance(n, ast.Attribute) and \
                    n.attr == "alignment_stream_analyzer":
                xau.append(f.name)
    ok("6e KHÔNG file nào của app moi `alignment_stream_analyzer`", not xau,
       ", ".join(xau) or "0 file")
    # TỰ KIỂM BỘ DÒ — không có mục này thì 6e tự ĐẠT vĩnh viễn.
    gia = ast.parse("x.t3.patched_model.alignment_stream_analyzer\n")
    ok("6f TỰ KIỂM: bộ dò BẮT được một file giả có cửa sau đó",
       any(isinstance(n, ast.Attribute)
           and n.attr == "alignment_stream_analyzer" for n in ast.walk(gia)))


def ca7() -> None:
    """TRẦN NHÃN — bài học Kokoro: dòng dài thì phần bị cắt là CẢNH BÁO."""
    print("\nCA 7 — dòng combo phải vừa TRAN_NHAN với MỌI tên")
    them_mau("G Anh", "en")
    d1 = GB.dong_day_du(NB.ma_giong("G Anh"), NB.nhan("G Anh"))
    ok("7a dòng `cb:` tên thường vừa trần", len(d1) <= NB.TRAN_NHAN,
       f"{len(d1)}/{NB.TRAN_NHAN}")

    ten_dai = ("Giọng " + "rất dài " * 25).strip()
    them_mau(ten_dai, "zh")
    d2 = GB.dong_day_du(NB.ma_giong(ten_dai), NB.nhan(ten_dai))
    ok("7b tên 200+ ký tự VẪN vừa trần (bất biến với MỌI tên)",
       len(d2) <= NB.TRAN_NHAN, f"{len(d2)}/{NB.TRAN_NHAN}")
    ok("7c ...và thứ bị cắt là TÊN, cảnh báo còn nguyên",
       "ĐÓNG DẤU CHÌM" in d2 and "cần tải" in d2)

    them_mau("G Việt", "vi")
    d3 = GB.dong_day_du(NB.ma_giong("G Việt"), NB.nhan("G Việt"))
    ok("7d dòng VieNeu KHÔNG bị đụng (nhãn đang vừa thì giữ nguyên)",
       len(d3) <= NB.TRAN_NHAN and "mẫu 8 giây" in d3, f"{len(d3)} ký tự")

    # TỰ KIỂM: gỡ `_vua_tran` thì 7b phải VỠ.
    cu = NB._vua_tran
    NB._vua_tran = lambda g, truoc, ten, sau: truoc + ten + sau  # type: ignore
    try:
        d4 = GB.dong_day_du(NB.ma_giong(ten_dai), NB.nhan(ten_dai))
    finally:
        NB._vua_tran = cu                      # type: ignore[assignment]
    ok("7e TỰ KIỂM: gỡ chốt -> 7b VỠ (mục 7b có răng)",
       len(d4) > NB.TRAN_NHAN, f"{len(d4)} ký tự")


def ca8() -> None:
    """NGHE THỬ PHẢI ĐỌC ĐÚNG NGÔN NGỮ CỦA GIỌNG (bài học cổng 85)."""
    print("\nCA 8 — nghe thử giọng `cb:` không được đọc câu tiếng Việt")
    from app.ui import thay_giong_dialog as TGD
    nut = than_ham(TGD, "_nghe_giong")
    dat_nn = [k for n in ast.walk(nut) if isinstance(n, ast.Call)
              for k in n.keywords if k.arg == "nn"]
    ok("8a `_nghe_giong` truyền `nn=` cho `doc_thu`", len(dat_nn) == 1)
    ok("8b `nn=` là BIỂU THỨC, KHÔNG phải hằng `\"vi\"`",
       bool(dat_nn) and not isinstance(dat_nn[0].value, ast.Constant),
       ast.dump(dat_nn[0].value)[:48] if dat_nn else "-")

    # GỌI THẬT: dựng hộp, chọn giọng `cb:en`, vá `doc_thu` để đọc `nn` nhận
    # được. Quét tĩnh một mình thì một phép phá đổi biểu thức vẫn lọt.
    from PyQt6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    assert _app is not None                    # giữ tham chiếu ở tầm hàm
    them_mau("G Anh", "en")
    from app.core import thay_giong as TG
    nhan: dict = {}
    that = TG.doc_thu

    def gia(voice, out_wav, text="", dung_cache=True, nn=""):
        nhan["nn"] = nn
        nhan["voice"] = voice
        return {"ra": "", "nguon": "", "loi": "cổng test", "canh_bao": ""}

    TG.doc_thu = gia                           # type: ignore[assignment]
    try:
        h = TGD.HopGiongToi()
        for i in range(h.ds.count()):
            if h.ds.item(i).data(32) == "G Anh" or \
                    "G Anh" in h.ds.item(i).text():
                h.ds.setCurrentRow(i)
                break
        h._nghe_giong()
        for _ in range(60):
            _app.processEvents()
            if "nn" in nhan:
                break
            import time as _t
            _t.sleep(0.05)
    finally:
        TG.doc_thu = that                      # type: ignore[assignment]
    ok("8c GỌI THẬT: giọng `cb:en` -> nghe thử bằng câu tiếng `en`",
       nhan.get("nn") == "en", str(nhan.get("nn")))
    ok("8d ...và vẫn đi qua `doc_thu` (không đẻ chỗ gọi thứ 4 cho cổng 63)",
       str(nhan.get("voice", "")).startswith("cb:en|"))


def ca9() -> None:
    """NÚT TẢI BÁM `thieu` — bám `co` là tính năng chết trên máy nhân viên."""
    print("\nCA 9 — nút tải: bám `thieu`, nói đủ giá, một phép đo nhiều chỗ đọc")
    ok("9a `nhan_tai([])` = nhãn đầy đủ", CB.nhan_tai([]) == CB.NHAN_TAI)
    ok("9b cài dở -> đổi thành 'Cài tiếp'",
       "Cài tiếp" in CB.nhan_tai(["torch"]), CB.nhan_tai(["torch"]))
    ok("9c nhãn nút mang SỐ ĐO qua `so_gb()` (không gõ tay)",
       CB.so_gb() in CB.NHAN_TAI and CB.so_gb() == "5,59", CB.so_gb())
    ok("9d `so_gb` chỉ đổi dấu CON SỐ, không đổi cả câu",
       CB.so_gb(1234.5) == "1234,50")

    nut = than_ham(CB, "cai_chatter")
    # ═══ MỤC NÀY TỪNG LÀ CON DẤU — PHÉP PHÁ 13 LỌT, ĐÃ VÁ ═══
    # Bản đầu hỏi `"--ignore-installed" in ast.unparse(nut)`. **`unparse` GIỮ
    # DOCSTRING**, mà docstring của `cai_chatter` cố ý trích nguyên văn cụm đó
    # để giải thích chốt -> gỡ SẠCH cờ khỏi LỆNH mà mục vẫn XANH. Đúng lỗi
    # cổng 73 (b) và cổng 88 mục 10c, lặp lại lần thứ ba.
    # Nay: bỏ docstring theo CẤU TRÚC, rồi đòi **MỌI danh sách lệnh có
    # `"install"`** đều mang cờ — bài học cổng 88 phép phá 11: hàm có HAI lệnh
    # pip thì hỏi "thân hàm có cờ không" là mất răng.
    than = list(nut.body)
    if than and isinstance(than[0], ast.Expr) and \
            isinstance(than[0].value, ast.Constant):
        than = than[1:]                        # bỏ DOCSTRING theo cấu trúc
    ds_lenh = []
    for x in than:
        for n in ast.walk(x):
            if isinstance(n, ast.List):
                gt = [e.value for e in n.elts if isinstance(e, ast.Constant)]
                if "install" in gt:
                    ds_lenh.append(gt)
    ok("9e MỌI danh sách lệnh pip mang `--ignore-installed`",
       bool(ds_lenh) and all("--ignore-installed" in g for g in ds_lenh),
       f"{len(ds_lenh)} lệnh")
    src = "\n".join(ast.unparse(x) for x in than)
    ok("9e' TỰ KIỂM BỘ DÒ: docstring KHÔNG được tính là mã",
       "--ignore-installed" in ast.unparse(nut)
       and "ép mọi gói nằm THẬT" not in src)
    ok("9f dùng chỉ mục CUDA (GPU là điều kiện tồn tại, không phải cho nhanh)",
       "CHI_MUC_TORCH_CU124" in src)
    ok("9g HẬU KIỂM bằng chính phép dò, không tin lời pip báo",
       "tinh_trang" in goi_ten(nut))
    ok("9h ghim BẢN torch 2.6.0 (2.9+ kéo theo torchcodec đòi FFmpeg DLL)",
       all("2.6.0+cu124" in g for g in CB.GOI_TORCH), str(CB.GOI_TORCH))
    ok("9i ghim setuptools < 81 (>=81 bỏ `pkg_resources`, perth chết lúc nạp)",
       "81" in CB.GOI_SETUPTOOLS, CB.GOI_SETUPTOOLS)

    # UI: nút phải CÒN HIỆN khi máy đã cài đủ nhưng `thieu` khác rỗng.
    from PyQt6.QtWidgets import QApplication
    from app.ui import thay_giong_dialog as TGD
    _app = QApplication.instance() or QApplication([])
    assert _app is not None
    cu = CB.tinh_trang
    CB.tinh_trang = lambda: {                  # type: ignore[assignment]
        "co": True, "thieu": ["torch"], "python": "x", "gpu": True,
        "thu_muc": str(T)}
    try:
        h = TGD.HopGiongToi()
        h.cb_nn.setCurrentIndex(1)             # một tiếng KHÁC tiếng Việt
        hien = h.b_tai_cb.isVisible() or not h.b_tai_cb.isHidden()
        nhan_nut = h.b_tai_cb.text()
    finally:
        CB.tinh_trang = cu                     # type: ignore[assignment]
    ok("9j `co=True` mà `thieu` khác rỗng -> nút VẪN HIỆN (bám `thieu`)",
       hien, f"nhãn: {nhan_nut[:40]}")
    ok("9k ...và nhãn nút nói 'Cài tiếp'", "Cài tiếp" in nhan_nut)

    # Chọn tiếng KHÁC tiếng Việt phải HIỆN đủ ba cái giá ngay lúc đang QUYẾT.
    h2 = TGD.HopGiongToi()
    h2.cb_nn.setCurrentIndex(0)
    t_vi = h2.lb_nn.text()
    h2.cb_nn.setCurrentIndex(1)
    t_cb = h2.lb_nn.text()
    ok("9l chọn tiếng Việt -> nói rõ KHÔNG cần GPU, KHÔNG đóng dấu chìm",
       "KHÔNG cần GPU" in t_vi and "KHÔNG bị đóng dấu chìm" in t_vi,
       t_vi[:56])
    ok("9m chọn tiếng khác -> hiện ĐỦ ba giá (GPU · dấu chìm · không có vi)",
       "GPU NVIDIA" in t_cb and "ĐÓNG DẤU CHÌM" in t_cb
       and "KHÔNG đọc được tiếng Việt" in t_cb, t_cb[:56])
    ok("9n combo ngôn ngữ có đủ 1 (Việt) + 23 (Chatterbox) mục",
       h2.cb_nn.count() == 1 + len(CB.TIENG), f"{h2.cb_nn.count()} mục")
    ok("9o mục ĐẦU là tiếng Việt (đường không cần GPU)",
       h2.cb_nn.itemData(0) == "vi")

    # NHÃN KHÔNG EMOJI — máy anh Hùng thiếu glyph nên nút ra Ô ĐEN (v2.6.22).
    xau = [t for t in (nhan_nut, t_vi, t_cb, CB.NHAN_TAI, CB.canh_bao_gon())
           if any(ord(c) > 0x2100 for c in t)]
    ok("9p nhãn KHÔNG EMOJI", not xau, str(xau)[:60])


def ca10() -> None:
    """CHỐT 1 (phần TIẾNG TRUNG) — BỘ ĐO PHẢI CÓ `zh`, NHÃN PHẢI NÓI RA SỐ.

    ═══════════════════════════════════════════════════════════════════════
    VÌ SAO CÓ CA NÀY — MỘT KẾT LUẬN ĐÃ SUÝT ĐÓNG SỔ MỘT TẬT CÓ THẬT
    ═══════════════════════════════════════════════════════════════════════
    Con số báo động đầu tiên của Chatterbox (`_kq_chatter_dangn.json`) đến từ
    arm **`A_nu × zh`**: đọc 54,9 s cho bộ câu mà trần chỉ 30,4 s = **1,81x**.
    Lượt đo lại (`_do_chatter_nhip.py`) kết luận *"không tái hiện được"* rồi
    HẠ con số đó khỏi nhãn — nhưng bộ đo lúc ấy chỉ có `en_ngan` / `en_dai` /
    `ja`, **THIẾU ĐÚNG `zh`**, và còn dùng một MẪU khác hẳn. Tức nó bác một
    arm bằng cách đo ba arm KHÁC.
    Dựng lại đúng arm thì tật **CÓ tái hiện** (số đo trong docstring
    `giong_chatter`). Nên ca này canh hai thứ:
      · bộ đo **không được thiếu `zh` lần nữa** — thiếu một arm là một cửa để
        kết luận "không tái hiện được" mọc lại;
      · nhãn phải nói ra tật ấy **và nói ĐÍCH DANH tiếng nào**, ở CHỖ NGƯỜI
        DÙNG ĐANG QUYẾT chứ không phải chỉ trong một hằng số.

    Quét tĩnh ở đây đi bằng **AST** và đọc **GIÁ TRỊ HẰNG**, không quét chuỗi
    trên cả file (bài học 47/51/53/54/73/80/86 — repo đã sập tám lần).
    """
    print("\nCA 10 — CHỐT 1 phần TIẾNG TRUNG: bộ đo có `zh`, nhãn nói ra số")
    try:
        import _do_chatter_nhip as DN
    except Exception as e:                                     # noqa: BLE001
        ok("10a nạp được bộ đo `_do_chatter_nhip`", False, f"{type(e).__name__}")
        return
    ok("10a bộ đo CÓ bộ câu `zh` và `zh_goc`",
       "zh" in DN.BO and "zh_goc" in DN.BO, ", ".join(DN.BO))

    # 10b — `zh_goc` phải là ĐÚNG bộ câu của arm cũ. Dựng lại độc lập ở đây
    # (không gọi `DN.tu_kiem_bo_cau`): cổng đi hỏi bộ đo *"anh tự chấm anh có
    # đúng không"* thì bộ đo hỏng là cổng hỏng theo.
    from _bo_cau_thu_doc import CORPUS
    goc = [c for loai in ("cau_thuong", "ban_dia")
           for (l, c, _t) in CORPUS["zh"] if l == loai][:8]
    ok("10b `zh_goc` khớp TỪNG CÂU với corpus chuẩn (arm cũ bị đóng băng)",
       list(DN.BO["zh_goc"]["cau"]) == goc, f"{len(goc)} câu")
    ok("10b' ...và đọc bằng ĐÚNG mẫu `A_nu` của bảng cũ",
       DN.BO["zh_goc"].get("mau") == "A_nu"
       and DN.MAU.get("A_nu") == "vi-VN-HoaiMyNeural",
       str(DN.BO["zh_goc"].get("mau")))

    # 10c — BẰNG CHỨNG CHO KẾT LUẬN "arm cũ TOÀN CÂU NGẮN". Đây không phải
    # chi tiết vụn: nó là thứ tách được hai giả thuyết *"tiếng Trung hỏng"* và
    # *"câu ngắn hỏng"*, và nếu ai đó sửa `zh_goc` cho "phong phú hơn" thì
    # bằng chứng ấy bốc hơi mà không ai thấy.
    dai_goc = [len(c) for c in DN.BO["zh_goc"]["cau"]]
    ok("10c arm cũ TOÀN câu ngắn (mọi câu <= `LAN_MAN_CHU_TOI_DA`)",
       max(dai_goc) <= CB.LAN_MAN_CHU_TOI_DA,
       f"{min(dai_goc)}-{max(dai_goc)} ký tự, trần {CB.LAN_MAN_CHU_TOI_DA}")

    dai_mix = sorted(len(c) for c in DN.BO["zh"]["cau"])
    ok("10d bộ `zh` TRỘN ngắn và dài (nếu không thì nó là `zh_goc` viết dài)",
       dai_mix[0] <= 20 and dai_mix[-1] >= 40,
       f"{dai_mix[0]}-{dai_mix[-1]} ký tự")
    ok("10d' ...và số câu ngang hai bộ `en_*` (8-12 câu)",
       8 <= len(DN.BO["zh"]["cau"]) <= 12, f"{len(DN.BO['zh']['cau'])} câu")

    # 10e — ĐỐI CHỨNG PHẢI CHẠY CÙNG LƯỢT. Không có nó thì mọi phép so với
    # bảng cũ là so hai môi trường khác nhau (bài học "đo A/B phải đan xen").
    arm = [DN.tach_arm(a) for a in DN.ARM_MAC_DINH]
    tieng = {DN.BO[b]["lang"] for b, _m in arm}
    ok("10e arm mặc định có ĐỐI CHỨNG tiếng Anh chạy cùng lượt",
       "en" in tieng, ", ".join(sorted(tieng)))
    mau_zh = {m for b, m in arm if b == "zh_goc"}
    ok("10e' ...và CÙNG bộ `zh_goc` chạy với >= 2 MẪU (tật đi theo CẶP)",
       len(mau_zh) >= 2, ", ".join(sorted(mau_zh)))

    # 10f — TỰ KIỂM BỘ DÒ. Thiếu mục này thì 10b/10c/10d chỉ là con dấu.
    cu_goc = DN.BO["zh_goc"]["cau"]
    cu_mix = DN.BO["zh"]["cau"]
    try:
        DN.BO["zh_goc"]["cau"] = list(cu_goc[:-1]) + ["今天天气很好。"]
        DN.BO["zh"]["cau"] = list(cu_goc)          # bỏ hết câu dài
        lech = list(DN.BO["zh_goc"]["cau"]) != goc
        d2 = sorted(len(c) for c in DN.BO["zh"]["cau"])
        het_dai = not (d2[0] <= 20 and d2[-1] >= 40)
    finally:
        DN.BO["zh_goc"]["cau"] = cu_goc
        DN.BO["zh"]["cau"] = cu_mix
    ok("10f TỰ KIỂM: đổi 1 câu -> phép so 10b TRƯỢT", lech)
    ok("10f' TỰ KIỂM: bỏ câu dài -> phép so 10d TRƯỢT", het_dai)

    # ═══ NHÃN ═══
    s = CB.CANH_BAO_CL
    ok("10g nhãn nói ĐÍCH DANH tiếng Trung", "Trung" in s)
    ok("10h nhãn mang SỐ ĐO của cả bộ câu, không nói chung chung",
       "1,85" in s, s[-120:])
    ok("10i nhãn nói tật này KHÔNG phải đọc sai chữ (WER thấp)",
       "ĐÚNG CHỮ" in s.upper() or "đúng chữ" in s)

    # 10h' — GHI CẢ HAI ĐẦU, KHÔNG GHI MỘT SỐ. Cùng 8 câu, cùng tiếng, đổi
    # MẪU thì ra **0,81x** (`B_nam`) và **1,85x** (`A_nu`); và ngay trong cùng
    # một mẫu `A_nu`, đổi FILE mẫu (edge-tts sinh lại) đã đủ đổi từ 1,67x sang
    # 1,80x trên thước thô. Chatterbox tiền định theo BYTE của mẫu, nên con số
    # đi theo MẪU anh Hùng đưa vào và một số lẻ là lời hứa không giữ được.
    nhip_zh = CB.canh_bao_nhip("zh")
    ok("10h' nhãn ghi CẢ HAI ĐẦU (0,81x mẫu này · 1,85x mẫu kia)",
       "0,81" in nhip_zh and "1,85" in nhip_zh, nhip_zh[:70])
    ok("10h'' ...và nói rõ con số đi theo MẪU người dùng đưa vào",
       "MẪU" in nhip_zh and "tệ hơn" in nhip_zh)
    ok("10n `NHIP_DA_DO` SUY TỪ bảng số, không phải danh sách gõ tay thứ hai",
       tuple(CB.NHIP_DA_DO) == tuple(CB.NHIP_THEO_TIENG),
       f"{CB.NHIP_DA_DO}")
    ok("10o tiếng CHƯA ĐO -> nói thẳng 'CHƯA AI ĐO', không im lặng",
       "CHƯA AI ĐO" in CB.canh_bao_nhip("ko"), CB.canh_bao_nhip("ko")[:50])
    # NGƯỠNG PHẢI NẰM GIỮA HAI NHÓM ĐÃ ĐO — đặt mò thì mục 10k/10l chỉ là
    # con dấu. Đây là chốt "đừng nới ngưỡng cho hết kêu".
    xau = [v[0] for v in CB.NHIP_THEO_TIENG.values() if v[0] >= CB.NHIP_KEU_TU]
    tot = [v[0] for v in CB.NHIP_THEO_TIENG.values() if v[0] < CB.NHIP_KEU_TU]
    ok("10p ngưỡng kêu nằm GIỮA nhóm ổn và nhóm hỏng (không đặt mò)",
       bool(xau) and bool(tot) and max(tot) < CB.NHIP_KEU_TU <= min(xau),
       f"ổn <= {max(tot) if tot else '-'} | ngưỡng {CB.NHIP_KEU_TU} | "
       f"hỏng >= {min(xau) if xau else '-'}")

    # 10j — NÓI Ở CHỖ ĐANG QUYẾT, không chỉ trong một hằng số. `nhan_giong()`
    # (nơi `CANH_BAO_CL` đi ra) **KHÔNG có một chỗ gọi nào trong `app/ui`** —
    # quét AST ở dưới chứng minh điều đó — nên nhãn ấy một mình là nhãn không
    # ai đọc. Cửa người dùng THẬT SỰ đọc là dòng cảnh báo của `_nn_doi`.
    from app.ui import thay_giong_dialog as TGD
    nut = than_ham(TGD, "_nn_doi")
    than = list(nut.body)
    if than and isinstance(than[0], ast.Expr) and \
            isinstance(than[0].value, ast.Constant):
        than = than[1:]                            # bỏ DOCSTRING theo cấu trúc
    src = "\n".join(ast.unparse(x) for x in than)
    ok("10j' lấy từ BẢNG SỐ của `giong_chatter` (một phép đo, nhiều chỗ đọc)",
       "canh_bao_nhip" in goi_ten(nut))

    # 10j — TÍNH RA RỒI VỨT ĐI thì mục 10j' vẫn xanh mà người dùng không thấy
    # gì. Nên phải đòi: cái tên nhận kết quả `canh_bao_nhip(...)` **có mặt
    # trong đối số của một lời gọi `setText`**. Đây là chốt chống "gọi cho
    # có" — đúng họ bẫy cổng 56d (quét "có mặt không" thì luôn có phép phá
    # giữ nguyên mặt chữ mà đổi ý nghĩa).
    ten_nhan = ""
    for n in ast.walk(nut):
        if isinstance(n, ast.Assign) and "canh_bao_nhip" in goi_ten(n.value) \
                and n.targets and isinstance(n.targets[0], ast.Name):
            ten_nhan = n.targets[0].id
    dung_o_settext = any(
        ten_nhan and any(ten_nhan in ast.unparse(a) for a in n.args)
        for n in ast.walk(nut)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "setText")
    ok("10j kết quả `canh_bao_nhip` THẬT SỰ đi vào `setText` (không tính "
       "rồi vứt)", bool(ten_nhan) and dung_o_settext, f"biến «{ten_nhan}»")
    ok("10j'' TỰ KIỂM BỘ DÒ: docstring KHÔNG được tính là mã",
       "BẮT BUỘC GPU NVIDIA" in ast.unparse(nut)
       and "Máy không GPU thì tính năng này KHÔNG TỒN TẠI" not in src)

    # 10k — cảnh báo phải ĐỔI THEO TIẾNG đang chọn, không phải một câu chung.
    from PyQt6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    assert _app is not None
    h = TGD.HopGiongToi()
    ds = {}
    for i in range(h.cb_nn.count()):
        h.cb_nn.setCurrentIndex(i)
        ds[str(h.cb_nn.itemData(i))] = h.lb_nn.text()
    t_zh = ds.get("zh", "")
    t_en = ds.get("en", "")
    # SO BẰNG `.upper()` — nhãn viết **"ĐỌC LOẠN NHỊP"** và **"SAI NHỊP"** in
    # HOA, nên tìm chuỗi thường `"nhịp"` là TRƯỢT trên một nhãn ĐANG ĐÚNG.
    # Bản đầu của mục này đã ĐỎ OAN đúng vì thế (bài học cổng 85: nhãn cố ý
    # viết hoa mà mục so nguyên văn chữ thường).
    ok("10k chọn tiếng TRUNG -> cảnh báo nhịp đọc HIỆN RA",
       "NHỊP" in t_zh.upper(), t_zh[-70:])
    ok("10k' ...và nêu SỐ ĐO", "1,85" in t_zh)
    ok("10l chọn tiếng ANH -> KHÔNG kêu oan (đo được 0,99-1,24x)",
       "NHỊP" not in t_en.upper(), t_en[-70:])
    ok("10l' TỰ KIỂM BỘ DÒ: hai dòng đó THẬT SỰ khác nhau",
       bool(t_zh) and bool(t_en) and t_zh != t_en)
    ok("10m nhãn tiếng Trung KHÔNG EMOJI",
       not any(ord(c) > 0x2100 for c in t_zh + CB.canh_bao_nhip("zh")))


def _noi_goi_ham(src: str, ten_ham: str) -> list[str]:
    """Tên hàm BAO QUANH mỗi nơi gọi ``ten_ham(...)`` — bằng **AST**.

    Quét chuỗi thì DÒNG GHI CHÚ tiếng Việt và DOCSTRING nhắc tên hàm cũng
    trúng; repo này đã sập bẫy đó **tám lần**, cả hai chiều. `ast.parse` bỏ
    hẳn ghi chú, còn docstring là node `Constant` nên không lọt vào `ast.Call`
    (`ast.unparse` thì GIỮ docstring — đó đúng cách mục 9e' từng PASS OAN).
    """
    ra: list[str] = []
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
            if (getattr(f, "attr", None) or getattr(f, "id", None)) == ten_ham:
                ra.append(bao[-1] if bao else "<tầm module>")
            self.generic_visit(n)

    Di().visit(ast.parse(src))
    return ra


def ca11() -> None:
    """CHỐT 5 — `goi_y_may` KHÔNG nằm trên đường ĐỌC, và **đừng nối nó vào**.

    ═══ VIỆC NÀY TỪ ĐÂU RA ═══
    Anh Hùng 26/08/2026: *"âm thanh giọng nói oke mà CÁCH PHÁT ÂM BỊ LỖI rồi,
    khi clone giọng tiếng Anh nó đọc như thằng mới học ấy, nói không lưu loát
    không chuẩn chữ"*. Màn hình: **Ngôn ngữ đích = Tiếng Anh** + giọng
    **`vnb:`**. Nghi ngờ đầu tiên là `goi_y_may` (`vi`->VieNeu · `en`->
    Chatterbox) đã thành **hàm chết** — repo có **6 ca** "hàm xong ≠ tính năng
    xong" nên nghi ngờ đó chính đáng.

    ═══ ĐO RỒI, VÀ CẢ HAI NỬA ĐỀU NGƯỢC VỚI DỰ ĐOÁN ═══
      (a) Nó **KHÔNG chết**: đúng 1 nơi gọi thật (`them_giong`). Nhưng nó chạy
          lúc **TẠO GIỌNG**, không phải lúc **ĐỌC** — nên ô "Ngôn ngữ đích"
          không với tới được nó.
      (b) Nối nó vào đường đọc là **LÀM TỆ ĐI**: cùng một file mẫu, `cb:` sai
          chữ trong câu **17,9%** còn `vnb:` chỉ **2,6-5,1%**
          (`_kq_vnb_en.txt`, 34 câu, cửa thật `dubbing._synth_all`).
    Nên chốt này canh **HAI CHIỀU**: đường đọc không được tự đổi máy, VÀ bảng
    số + câu cảnh báo không được biến mất khỏi mã. Bỏ chiều thứ hai thì lần
    sau lại có người "sửa" bằng cách nối `goi_y_may` vào `_synth_all`.
    """
    import inspect as _ins
    import re as _re

    from app.core import dubbing as DUB

    # ---- 11a TỰ KIỂM BỘ DÒ TRƯỚC (bộ dò sai thì mọi mục dưới vô nghĩa)
    moi = ('def khong_goi():\n'
           '    """Docstring nhắc goi_y_may mà KHÔNG gọi."""\n'
           '    # ghi chú tiếng Việt: goi_y_may(lang) quyết máy\n'
           '    return "goi_y_may"\n'
           '\n'
           'def that_su_goi(l):\n'
           '    return goi_y_may(l)\n')
    ok("11a TỰ KIỂM BỘ DÒ: docstring + ghi chú + chuỗi KHÔNG bị tính là gọi",
       _noi_goi_ham(moi, "goi_y_may") == ["that_su_goi"],
       str(_noi_goi_ham(moi, "goi_y_may")))

    goi: dict[str, list[str]] = {}
    for p in sorted(REPO.joinpath("app").rglob("*.py")):
        try:
            n = _noi_goi_ham(p.read_text(encoding="utf-8", errors="replace"),
                             "goi_y_may")
        except SyntaxError:
            continue
        if n:
            goi[str(p.relative_to(REPO)).replace("\\", "/")] = n
    ok("11b `goi_y_may` KHÔNG phải hàm chết — có nơi gọi thật", bool(goi),
       str(goi))
    ok("11c ...và nơi gọi ấy là `them_giong` (lúc TẠO giọng, không phải đọc)",
       goi == {"app/core/nhan_ban_giong.py": ["them_giong"]}, str(goi))
    ok("11d `app/ui/` gọi TRỰC TIẾP: 0 (grep chuỗi ra 2 — cả hai là GHI CHÚ)",
       not [f for f in goi if f.startswith("app/ui/")])

    # ---- 11e-g ĐƯỜNG ĐỌC KHÔNG TỰ ĐỔI MÁY — **GỌI THẬT**, không đọc mã.
    # Đọc mã rồi suy là DỪNG QUÁ SỚM (bài học `SEAPipeline(lang="vi")`: đọc
    # tới đó tưởng đã chứng minh, chạy thật thì chữ Anh ra âm Anh).
    from app.core import giong_chatter as _GC
    from app.core import giong_vieneu as _GV
    _cu_vn, _cu_cb = _GV.doc_loat, _GC.doc_loat
    di: dict[str, str] = {}
    _log: list[str] = []

    def _bao(ten):
        def _g(*a, **k):
            _log.append(ten)
            n = len(a[0]) if a else 0
            return ([False] * n, [[] for _ in range(n)])
        return _g

    mau = wav("ca11_mau.wav", [("tieng", 5.0)])
    try:
        _GV.doc_loat = _bao("vieneu")              # type: ignore[assignment]
        _GC.doc_loat = _bao("chatter")             # type: ignore[assignment]
        for nhan, v, lg in (("vnb_en", f"vnb:{mau}", "en"),
                            ("vnb_vi", f"vnb:{mau}", "vi"),
                            ("cb_en", f"cb:en|{mau}", "en")):
            _log.clear()
            try:
                asyncio.run(DUB._synth_all(["Hello."], v,
                                           [str(T / f"ca11_{nhan}.mp3")],
                                           lang=lg))
            except Exception as e:                             # noqa: BLE001
                _log.append(f"[nổ {type(e).__name__}: {e}]")
            di[nhan] = _log[0] if _log else "edge"
    finally:
        _GV.doc_loat = _cu_vn                      # type: ignore[assignment]
        _GC.doc_loat = _cu_cb                      # type: ignore[assignment]
    ok("11e GỌI THẬT: đích ANH + giọng `vnb:` VẪN chạy VieNeu (không tự đổi)",
       di.get("vnb_en") == "vieneu", str(di))
    ok("11f ...và `cb:` vẫn chạy Chatterbox (bộ dò mục 11e có răng)",
       di.get("cb_en") == "chatter", str(di))
    ok("11g ...đích VIỆT rẽ y hệt đích ANH (tiếng KHÔNG đổi máy, hai chiều)",
       di.get("vnb_en") == di.get("vnb_vi"), str(di))

    # ---- 11h-k BẢNG SỐ phải CÒN, và phải nói ĐÚNG CHIỀU nó đã đo
    so = getattr(NB, "SO_DO_EN", {})
    ok("11h `SO_DO_EN` có đủ 3 arm (vnb · cb · trần)",
       set(so) == {"vnb", "cb", "tran"}, str(sorted(so)))
    ok("11i mỗi arm có đủ 5 thước",
       bool(so) and all(set(v) == {"cau", "roi", "bia", "wer", "nhip"}
                        for v in so.values()))

    def _dau(s: str) -> float:
        """Số ĐẦU của ô kiểu ``"2,6-5,1%"`` -> 2.6. Đọc **SỐ**, không so chữ.

        So chuỗi thì đổi `"17,9%"` thành `"1,79%"` vẫn "có mặt" và mục PASS
        OAN — đúng bẫy 56d/64.
        """
        return float(_re.split(r"[-–%]", str(s).replace(",", "."))[0])

    ok("11j SỐ nói Chatterbox TỆ HƠN ở token trong câu (đọc SỐ, không chữ)",
       _dau(so["cb"]["cau"]) > _dau(so["vnb"]["cau"]),
       f"cb {so['cb']['cau']} vs vnb {so['vnb']['cau']}")
    ok("11k ...và TRẦN vẫn thấp nhất (bảng không bị đảo lộn)",
       _dau(so["tran"]["cau"]) <= _dau(so["vnb"]["cau"]))

    # ---- 11l-s CÂU CẢNH BÁO: đúng ca, đủ số, không kêu oan
    t = NB.canh_bao_doc_tieng("vnb:D:/m.wav", "en")
    ok("11l `vnb:` + tiếng NGOÀI tiếng Việt -> CÓ cảnh báo", bool(t), t[:60])
    ok("11m `vnb:` + tiếng VIỆT -> IM (không kêu oan)",
       NB.canh_bao_doc_tieng("vnb:D:/m.wav", "vi") == "")
    ok("11n `cb:` -> IM (chốt này nói về VieNeu, không nói về Chatterbox)",
       NB.canh_bao_doc_tieng("cb:en|D:/m.wav", "en") == "")
    ok("11o giọng edge-tts -> IM",
       NB.canh_bao_doc_tieng("en-US-AriaNeural", "en") == "")
    ok("11p rác/None -> IM, KHÔNG NÉM",
       NB.canh_bao_doc_tieng(None, None) == ""      # type: ignore[arg-type]
       and NB.canh_bao_doc_tieng("", "") == "")
    ok("11q cảnh báo mang SỐ ĐO của CẢ BA arm (không nói chung chung)",
       all(so[k][c] in t for k, c in (("vnb", "wer"), ("vnb", "bia"),
                                      ("vnb", "cau"), ("cb", "cau"),
                                      ("tran", "wer"))), t[:80])
    # CHỐNG GÕ TAY: đổi bảng thì câu phải đổi theo. Không có mục này thì ai đó
    # gõ thẳng "17,9%" vào câu và `SO_DO_EN` thành đồ trang trí.
    _luu = dict(so["cb"])
    try:
        so["cb"] = dict(_luu, cau="99,9%")
        t2 = NB.canh_bao_doc_tieng("vnb:D:/m.wav", "en")
    finally:
        so["cb"] = _luu
    ok("11r TỰ KIỂM: đổi `SO_DO_EN` -> câu ĐỔI THEO (số không bị gõ tay)",
       "99,9%" in t2 and "99,9%" not in t)
    ok("11s cảnh báo KHÔNG EMOJI", not any(ord(c) > 0x2100 for c in t))

    # ---- 11t-w UI: "hàm xong ≠ tính năng xong" (repo đã sập 6 lần)
    from app.ui import thay_giong_dialog as TGD
    src_ui = Path(_ins.getfile(TGD)).read_text(encoding="utf-8")
    ok("11t `_ve_goi_y` GỌI `_ve_canh_bao_nhan_ban` (nối vào cửa CHUNG)",
       "_ve_goi_y" in _noi_goi_ham(src_ui, "_ve_canh_bao_nhan_ban"))
    ok("11u `_ve_canh_bao_nhan_ban` GỌI `canh_bao_doc_tieng`",
       "_ve_canh_bao_nhan_ban" in _noi_goi_ham(src_ui, "canh_bao_doc_tieng"))

    from PyQt6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    assert _app is not None
    d = TGD.ThayGiongDialog(None)
    d.cb_giong.addItem("giọng nhân bản thử", "vnb:D:/m.wav")
    d.cb_giong.setCurrentIndex(d.cb_giong.count() - 1)
    d.cb_nn.setCurrentIndex(max(0, d.cb_nn.findData("en")))
    d._ve_goi_y()
    t_en = d.lb_nb_tieng.text()
    d.cb_nn.setCurrentIndex(max(0, d.cb_nn.findData("vi")))
    d._ve_goi_y()
    t_vi = d.lb_nb_tieng.text()
    d.deleteLater()
    ok("11v GỌI THẬT trên hộp thoại: đích ANH + `vnb:` -> dòng vàng HIỆN",
       bool(t_en), t_en[:60])
    ok("11w ...đổi đích sang VIỆT -> dòng TẮT (bộ dò mục 11v có răng)",
       t_vi == "", t_vi[:60])

    # ---- 11x KHÔNG ĐẺ CHỖ GỌI `_synth_all_words` THỨ TƯ trên ĐƯỜNG THAY TIẾNG
    # (mệnh đề cổng 63, đang canh ĐÚNG 3 chỗ của `thay_giong.py`).
    # **ĐẾM THEO FILE, KHÔNG ĐẾM TỔNG**: cả `app/` có 6 chỗ — 3 của
    # `thay_giong.py` (đường THAY TIẾNG) + 3 của `dubbing.build_recap_track`
    # (đường RECAP, họ khác). Gộp lại thành một con số là mốc sai ngay từ đầu,
    # và mốc sai thì hoặc đỏ oan hoặc không bao giờ bập.
    n_theo_file: dict[str, int] = {}
    for p in sorted(REPO.joinpath("app").rglob("*.py")):
        try:
            n = len(_noi_goi_ham(
                p.read_text(encoding="utf-8", errors="replace"),
                "_synth_all_words"))
        except SyntaxError:
            continue
        if n:
            n_theo_file[p.name] = n
    ok("11x `thay_giong.py` vẫn gọi `_synth_all_words` ĐÚNG 3 chỗ (không đẻ 4)",
       n_theo_file.get("thay_giong.py") == 3, str(n_theo_file))
    ok("11x' ...và bản vá này KHÔNG thêm chỗ gọi ở file nào khác",
       set(n_theo_file) == {"thay_giong.py", "dubbing.py"}, str(n_theo_file))

    # ---- 11y DEDUP_KEY KHÔNG ĐƯỢC ĐỔI — 200-300 kênh không xuất lại.
    # Bản vá này CỐ Ý không đụng `sig`; mục này là bằng chứng, không phải lời.
    import inspect as _i2

    from app import services as SV
    src_sv = _i2.getsource(SV.enqueue_thay_giong)
    ok("11y `enqueue_thay_giong` vẫn khoá bằng ĐÚNG 4 phần cũ (sig không đổi)",
       'khoa = f"thaygiong:{duong.lower()}:{dich_sang}:{voice}"' in src_sv,
       "dedup_key phải giống TỪNG KÝ TỰ bản mốc")


def main() -> int:
    print("=" * 74)
    print("CỔNG 91 — NHÂN BẢN GIỌNG ĐA NGÔN NGỮ (Chatterbox) ĐÃ NỐI VÀO UI")
    print("=" * 74)
    for f in (ca1, ca2, ca3, ca4, ca5, ca6, ca7, ca8, ca9, ca10, ca11):
        try:
            f()
        except Exception as e:                                 # noqa: BLE001
            import traceback
            traceback.print_exc()
            _HONG.append(f"{f.__name__} NỔ: {type(e).__name__}: {e}")
    print("\n" + "=" * 74)
    print(f"KETQUA: ĐẠT {_DAT} · HỎNG {len(_HONG)}")
    for h in _HONG:
        print(f"   - {h}")
    return 1 if _HONG else 0


def _don() -> None:
    """Dọn hộp cát của LƯỢT NÀY. **KHÔNG BAO GIỜ NÉM.**

    ═══ `rmtree(ignore_errors=True)` MỘT PHÁT LÀ KHÔNG ĐỦ — ĐO ĐƯỢC ═══
    Sau lượt dựng cổng này, repo còn đọng **69 thư mục `bq_test_nbdn_*`**,
    mỗi cái chứa **đúng một file `studio.db`**. Gốc: `app.database.db.db` giữ
    handle SQLite MỞ, Windows không cho xoá file đang mở, mà
    `ignore_errors=True` **NUỐT LỖI IM LẶNG** -> `atexit` chạy xong, không
    một dòng báo, và không xoá được gì. Đúng họ bẫy *"phép dọn hỏng phát
    chứng nhận"* (`astats` cổng 53 · `startswith` cổng 44).
    Nên thứ tự bắt buộc: **NHẢ HANDLE trước** -> `rmtree` -> **THỬ LẠI** vài
    nhịp (Windows còn giữ file một lúc sau khi đóng, đúng khuôn `_XOA_CHO`
    của `ffmpeg_utils`) -> rồi mới chịu thua.
    """
    try:
        from app.database.db import db as _db
        _db._reset_conn()
    except Exception:                                          # noqa: BLE001
        pass
    import time as _t
    for _ in range(6):
        shutil.rmtree(T, ignore_errors=True)
        if not T.exists():
            return
        _t.sleep(0.25)


def _don_mo_coi() -> None:
    """Quét hộp cát MỒ CÔI của những lượt chạy TRƯỚC đã chết.

    Một lượt thử phá gọi cổng **15 lần**, và bất kỳ lượt nào chết giữa đường
    (hoặc bị giết) là một thư mục nằm lại vĩnh viễn — đó là cách 69 thư mục
    kia tích lại. `_don` chỉ lo được lượt ĐANG chạy, nên phải có cửa thứ hai.

    **BẤT BIẾN AN TOÀN (cùng luật `don_seg_mo_coi`):** chỉ đụng thư mục mang
    ĐÚNG tiền tố của chính cổng này VÀ có **PID KHÔNG CÒN SỐNG** — không bao
    giờ xoá hộp cát của một lượt đang chạy song song. Đọc PID không được thì
    **GIỮ** (quy tắc chung của repo: không xác định được thì giữ).
    """
    try:
        import psutil
    except Exception:                                          # noqa: BLE001
        return
    for d in REPO.glob("bq_test_nbdn_*"):
        try:
            if not d.is_dir():
                continue
            pid = int(d.name.rsplit("_", 1)[1])
            if pid == os.getpid() or psutil.pid_exists(pid):
                continue
            shutil.rmtree(d, ignore_errors=True)
        except (ValueError, IndexError, OSError):
            continue


_don_mo_coi()

import atexit  # noqa: E402

# `atexit` chứ không gọi thẳng ở cuối: lượt THỬ PHÁ có phép làm cổng chết giữa
# đường, và cổng 88 đã đo được 2 thư mục hộp cát đọng lại trong repo vì thế.
atexit.register(_don)

if __name__ == "__main__":
    raise SystemExit(main())
