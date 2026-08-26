# -*- coding: utf-8 -*-
"""CỔNG 92 — DÒ CÂU **LAN MAN** RỒI ĐỌC LẠI (giọng nhân bản VieNeu `vnb:`).

Anh Hùng (26/08/2026): *"khi clone giọng tiếng Anh nó đọc như thằng mới học
ấy, nói không lưu loát không chuẩn chữ"*. Lượt đo ghép cặp đã **BÁC** chẩn
đoán "model tiếng Việt nên đọc tiếng Anh kém" và chỉ ra bệnh thật là **KHÔNG
ĐỀU**: cùng mã, cùng file mẫu, cùng bộ chữ, hai lượt ra `WER 3,1% · bịa 0,3%`
và `WER 12,7% · bịa 9,7%`. Ngẫu nhiên theo lượt -> **đọc lại** có cơ sở ăn.

Cổng này canh ba thứ, mỗi thứ là một chỗ đã trả giá ở nơi khác trong repo:

 1. **MỘT bộ dò, không phải hai.** Phép tính nằm ở `app/core/doc_lan.py`;
    `giong_chatter.nghi_doc_lan` GỌI vào đó chứ không chép lại. Hai bản sao là
    hai chỗ để lệch nhau.
 2. **Ngưỡng HIỆU CHUẨN trên corpus thật, không đặt mò.** CA 3 đọc thẳng
    `_kq_vnb_lan.json` và đòi ngưỡng đang dùng phải là **chỗ thấp nhất mà arm
    TRẦN (giọng bản ngữ đọc ĐÚNG) không kêu một lần nào** — hạ một bậc là
    TRẦN bắt đầu kêu oan. Cổng cũng ghi nhận thẳng rằng **hai nhóm CHỒNG
    NHAU**, không giả vờ có một đường kẻ sạch (bài học `ty_giu`).
 3. **Đọc lại có TRẦN, KHÔNG BAO GIỜ BỎ CÂU, và CHỈ NHẬN KHI ĐỠ HƠN THẬT.**
    Bỏ câu = mất tiếng (đúng lỗi anh Hùng từng kêu). Nhận bừa = đổi câu hỏng
    này lấy câu hỏng khác rồi tự khen đã chữa (khuôn `rut_gon_vua_khung`).

**KHÔNG GỌI MẠNG · KHÔNG GROQ · KHÔNG GPU · KHÔNG ffmpeg.** Máy đọc bị thay
bằng hàm giả sinh WAV theo một mô hình nhịp BIẾT TRƯỚC, nên cổng TIỀN ĐỊNH —
nó chấm bản vá, không chấm cái máy.

Chạy:  .venv\\Scripts\\python -u _test_doc_lan.py
"""
from __future__ import annotations

import ast
import atexit
import io
import math
import os
import shutil
import struct
import sys
import tokenize
import wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from app.core import doc_lan as DL             # noqa: E402
from app.core import giong_chatter as CB       # noqa: E402
from app.core import giong_vieneu as GV        # noqa: E402

T = REPO / f"bq_test_doclan_{os.getpid()}"
_DAT = 0
_HONG: list[str] = []


def ok(ten: str, dieu: bool, ghi: str = "") -> bool:
    global _DAT
    if dieu:
        _DAT += 1
        print(f"  ĐẠT  {ten}" + (f"  [{ghi}]" if ghi else ""))
    else:
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f"  [{ghi}]" if ghi else ""))
    return bool(dieu)


# --------------------------------------------------------------- công cụ
def wav(p: Path, giay: float) -> str:
    """WAV 24 kHz mono dài đúng `giay`. Dùng `wave` chứ KHÔNG gọi ffmpeg.

    (`dai_wav` đọc thẳng mẫu nên không cần ffmpeg; và nhắc lại luật repo:
    `-t` là tuỳ chọn ĐẦU VÀO của ffmpeg, đặt sai chỗ đã đầy ổ C 420 GB một
    lần — ở đây né hẳn bằng cách không dùng ffmpeg.)
    """
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        n = max(1, int(24000 * giay))
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i * 0.05)))
                               for i in range(n)))
    return str(p)


def _ma_that(f: Path) -> str:
    """Mã NGUỒN đã bỏ COMMENT + STRING (docstring), nối token bằng KHOẢNG TRẮNG.

    Quét bằng chuỗi trên file có ghi chú tiếng Việt là tự bắn vào chân — repo
    đã sập bẫy đó **8 lần**, cả hai chiều (đỏ oan vì trúng dòng ghi chú; PASS
    oan vì `ast.unparse` GIỮ DOCSTRING). CA 5f tự kiểm chính bộ dò này.
    """
    ra = []
    with open(f, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING,
                            tokenize.NL, tokenize.NEWLINE,
                            tokenize.INDENT, tokenize.DEDENT):
                continue
            ra.append(tok.string)
    return " ".join(ra)


def _nut_ham(f: Path, ten: str):
    """Nút AST của hàm `ten` trong file `f` (đọc utf-8, KHÔNG theo bảng mã máy).

    (`inspect.getsource` mở file theo bảng mã MẶC ĐỊNH — cp1252 trên máy này
    -> docstring tiếng Việt ra mojibake rồi `ast.parse` nổ. Bẫy cổng 71.)
    """
    cay = ast.parse(f.read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    return None


def _goi_ten(nut) -> set[str]:
    """Tên MỌI hàm được GỌI trong một nút AST (kể cả `a.b.c(...)`)."""
    ra: set[str] = set()
    for x in ast.walk(nut):
        if isinstance(x, ast.Call):
            f = x.func
            if isinstance(f, ast.Name):
                ra.add(f.id)
            elif isinstance(f, ast.Attribute):
                ra.add(f.attr)
    return ra


# =========================================================== CA 1
def ca1() -> None:
    """Phép tính THUẦN của `doc_lan` — và nó không được đoán bừa."""
    print("\nCA 1 — PHÉP TÍNH THUẦN")
    # ước = a + b*n = 1.0 + 0.1*10 = 2.0 -> 5s/2s = 2.5
    ok("1a `lan_vuot` đúng công thức a + b*n",
       DL.lan_vuot("x" * 10, 5.0, 1.0, 0.1) == 2.5,
       str(DL.lan_vuot("x" * 10, 5.0, 1.0, 0.1)))
    ok("1b SÀN chặn chia cho số quá nhỏ (a+b*n âm)",
       DL.lan_vuot("x", 0.35, -5.0, 0.01) == 1.0,
       f"san={DL.SAN_GIAY}")
    ok("1c không tính được thì IM (không đoán bừa là hỏng)",
       DL.lan_vuot("", 5.0, 1.0, 0.1) == 0.0
       and DL.lan_vuot("abc", 0.0, 1.0, 0.1) == 0.0
       and DL.lan_vuot("abc", 5.0, 0.0, 0.0) == 0.0)

    # dựng loạt theo mô hình BIẾT TRƯỚC rồi bắt `moc_nhip` khớp lại đúng nó
    A, B = 0.5, 0.06
    ts = ["x" * (12 + 7 * i) for i in range(12)]
    gs = [A + B * len(t) for t in ts]
    a, b = DL.moc_nhip(ts, gs)
    ok("1d `moc_nhip` khớp lại ĐÚNG mô hình đã dựng",
       abs(a - A) < 1e-6 and abs(b - B) < 1e-9, f"{a:.4f} + {b:.5f}n")

    # ĐIỂM NGOẠI LAI: 3 câu lan man gấp 5. Theil-Sen phải đứng yên.
    ts2 = ts + ["x" * 30, "x" * 44, "x" * 58]
    gs2 = gs + [5 * (A + B * 30), 5 * (A + B * 44), 5 * (A + B * 58)]
    a2, b2 = DL.moc_nhip(ts2, gs2)
    lech_ts = abs(b2 - B) / B
    # ĐỐI CHỨNG: bình phương tối thiểu trên CÙNG bộ số -> lệch bao nhiêu?
    n = len(ts2)
    sx = sum(len(t) for t in ts2)
    sy = sum(gs2)
    sxx = sum(len(t) ** 2 for t in ts2)
    sxy = sum(len(t) * g for t, g in zip(ts2, gs2))
    b_bp = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    lech_bp = abs(b_bp - B) / B
    ok("1e Theil-Sen ĐỨNG YÊN trước điểm ngoại lai (lệch < 5%)",
       lech_ts < 0.05, f"{100 * lech_ts:.1f}%")
    # ĐỐI CHỨNG — không có mục này thì 1e chỉ nói "hàm chạy", không nói "chọn
    # Theil-Sen là ĐÚNG". Số đo: Theil-Sen **0,0%** · bình phương tối thiểu
    # **23%** trên CÙNG bộ số. (Trần 15% đặt theo SỐ ĐO, không theo lời hứa —
    # bản đầu của mục này đòi > 50% và ĐỎ OAN vì tôi gõ một con số chưa đo.)
    ok("1e' ...còn bình phương tối thiểu thì BỊ KÉO (đối chứng, lệch > 15%)",
       lech_bp > 0.15, f"BPTT lệch {100 * lech_bp:.0f}% · Theil-Sen "
                       f"{100 * lech_ts:.1f}%")

    ok("1f ít mẫu hơn TOI_THIEU_MUC -> CHỊU, không dò bừa",
       DL.moc_nhip(ts[:3], gs[:3]) == (0.0, 0.0))
    ok("1g mọi câu CÙNG độ dài -> CHỊU (không có hệ số góc để khớp)",
       DL.moc_nhip(["abc"] * 10, [1.0] * 10) == (0.0, 0.0))
    ok("1h nhịp đọc ÂM là vô nghĩa -> CHỊU",
       DL.moc_nhip(ts, [10.0 - 0.05 * len(t) for t in ts]) == (0.0, 0.0))

    lan, moc = DL.soi_loat(ts2, gs2)
    ok("1i `soi_loat` bắt đúng 3 câu ngoại lai, 12 câu lành IM",
       sum(1 for v in lan if v > 0) == 3
       and all(v == 0.0 for v in lan[:12]),
       f"{[round(v, 2) for v in lan if v]}")
    lan_m, _ = DL.soi_loat(ts2, gs2, moc=(99.0, 99.0))
    ok("1i' truyền `moc=` thì DÙNG LẠI, không khớp mới",
       all(v == 0.0 for v in lan_m))
    rac = DL.soi_loat([None, "a", 3], ["x", -1, None])   # type: ignore[list-item]
    ok("1j dữ liệu rác -> KHÔNG NÉM, trả toàn 0", rac[0] == [0.0, 0.0, 0.0])


# =========================================================== CA 2
def ca2() -> None:
    """MỘT bộ dò dùng chung — không đẻ bản sao thứ hai."""
    print("\nCA 2 — MỘT BỘ DÒ, KHÔNG PHẢI HAI")
    # BẤT BIẾN cổng 91: hai con số này KHÔNG được đổi.
    ok("2a `nghi_doc_lan('Okay.', 7.15)` giữ nguyên 8.58 (bất biến cổng 91)",
       CB.nghi_doc_lan("Okay.", 7.15) == 8.58,
       str(CB.nghi_doc_lan("Okay.", 7.15)))
    ok("2a' câu dài đọc đúng nhịp -> vẫn KHÔNG kêu oan",
       CB.nghi_doc_lan("The storm knocked out power to the village.", 3.1)
       == 0.0)

    f_cb = REPO / "app" / "core" / "giong_chatter.py"
    nut = _nut_ham(f_cb, "nghi_doc_lan")
    ok("2b `giong_chatter.nghi_doc_lan` GỌI `doc_lan.lan_vuot`",
       nut is not None and "lan_vuot" in _goi_ten(nut))
    ma_cb = _ma_that(f_cb)
    ok("2c `giong_chatter` KHÔNG đẻ bản sao `lan_vuot`/`moc_nhip`",
       "def lan_vuot" not in ma_cb and "def moc_nhip" not in ma_cb)

    f_vn = REPO / "app" / "core" / "giong_vieneu.py"
    nut_v = _nut_ham(f_vn, "_doc_lai_lan_man")
    ok("2d `giong_vieneu` cũng đi qua `doc_lan` (soi_loat + lan_vuot)",
       nut_v is not None
       and {"soi_loat", "lan_vuot"} <= _goi_ten(nut_v))
    ma_vn = _ma_that(f_vn)
    ok("2e `giong_vieneu` KHÔNG tự chép công thức",
       "def lan_vuot" not in ma_vn and "def moc_nhip" not in ma_vn)

    # TỰ KIỂM BỘ DÒ — không có mục này thì 2b/2d chỉ là con dấu.
    gia = ast.parse("def f():\n    return 1\n").body[0]
    ok("2f TỰ KIỂM: bộ dò AST TRƯỢT trên hàm không gọi gì",
       "lan_vuot" not in _goi_ten(gia))


# =========================================================== CA 3
def ca3() -> None:
    """NGƯỠNG phải HIỆU CHUẨN trên corpus thật — và nói thẳng nó không sạch."""
    print("\nCA 3 — NGƯỠNG HIỆU CHUẨN TRÊN CORPUS THẬT")
    # ĐỌC BẢN GỌN CÓ THEO DÕI GIT, **KHÔNG** đọc `_kq_vnb_lan.json`:
    # `_kq*.json` bị `.gitignore` nên trên máy vừa clone cổng sẽ ĐỎ OAN vì KHO
    # chứ không vì MÃ (bệnh cổng 47 CA2 và cổng 68). Ngưỡng được hiệu chuẩn
    # trên MỘT lượt đo, nên bằng chứng của lượt ấy phải đi kèm mã.
    kq = REPO / "_moc_doc_lan.json"
    if not kq.exists():
        ok("3a có bảng hiệu chuẩn `_moc_doc_lan.json`", False,
           "chạy `_do_vnb_lan.py` trước")
        return
    import json
    d = json.loads(kq.read_text(encoding="utf-8"))
    vn = d["arm"].get("VNB_en") or []
    tran = d["arm"].get("edge_en") or []
    bia = [h for h in vn if h["bia"]]
    lanh = [h for h in vn if not h["bia"]]
    ok("3a bảng có ĐỦ HAI NHÓM + arm TRẦN",
       len(bia) >= 10 and len(lanh) >= 50 and len(tran) >= 30,
       f"bịa {len(bia)} · lành {len(lanh)} · trần {len(tran)}")

    ng = DL.NGUONG_LAN
    t_oan = sum(1 for h in tran if h["lan"] >= ng)
    ok("3b tại ngưỡng đang dùng, arm TRẦN (bản ngữ đọc ĐÚNG) kêu oan = 0",
       t_oan == 0, f"ngưỡng {ng} · trần kêu {t_oan}/{len(tran)}")

    # ...và HẠ MỘT BẬC thì TRẦN BẮT ĐẦU kêu -> ngưỡng nằm đúng chỗ thấp nhất
    # còn sạch, chứ không phải một số đẹp ai đó gõ vào.
    duoi = sum(1 for h in tran if h["lan"] >= ng - 0.1)
    ok("3c hạ 0,1 là TRẦN BẮT ĐẦU kêu oan -> ngưỡng KHÔNG đặt mò",
       duoi > 0, f"ngưỡng {ng - 0.1:.1f} · trần kêu {duoi}/{len(tran)}")

    bat = sum(1 for h in bia if h["lan"] >= ng)
    ok("3d bắt được >= 70% nhóm bịa",
       bat >= 0.70 * len(bia), f"{bat}/{len(bia)}")
    oan = sum(1 for h in lanh if h["lan"] >= ng)
    ok("3e kêu oan trên nhóm lành <= 5%",
       oan <= 0.05 * len(lanh), f"{oan}/{len(lanh)}")

    # SỰ THẬT KHÓ CHỊU, cổng phải ghi nhận chứ không giả vờ:
    chong = max(h["lan"] for h in lanh) >= min(h["lan"] for h in bia)
    ok("3f cổng GHI NHẬN hai nhóm CHỒNG NHAU (không giả vờ có đường kẻ sạch)",
       chong, f"lành max {max(h['lan'] for h in lanh):.2f} · "
              f"bịa min {min(h['lan'] for h in bia):.2f}")


# =========================================================== CA 4
class MayGia:
    """Máy đọc GIẢ: sinh WAV theo nhịp `a + b*n`, cho phép ép câu nào lan man.

    `hong` = {chỉ số: bội số} cho lượt đọc ĐẦU · `hong_lai` cho lượt ĐỌC LẠI
    (mặc định 1.0 = đọc lại thì lành). Đếm số lượt gọi để chấm TRẦN.
    """

    def __init__(self, hong: dict, hong_lai: dict | None = None,
                 ok_lai: bool = True, nem: bool = False) -> None:
        self.A, self.B = 0.5, 0.06
        self.hong = hong
        self.hong_lai = hong_lai or {}
        self.ok_lai = ok_lai
        self.nem = nem
        self.luot = 0
        self._cu = None

    def uoc(self, t: str) -> float:
        return self.A + self.B * len(t)

    def __enter__(self) -> "MayGia":
        self._cu = GV._chay_vieneu

        def _g(items, py, voice, ref, han, on_msg):
            self.luot += 1
            if self.luot > 1:
                if self.nem:
                    raise RuntimeError("tiến trình con bùm")
                if not self.ok_lai:
                    return {"ok": False, "loi": "quá giờ", "_sandbox": ""}
            ra = []
            for it in items:
                i = int(it["i"])
                he = (self.hong.get(i, 1.0) if self.luot == 1
                      else self.hong_lai.get(i, 1.0))
                ra.append({"i": i, "p": wav(Path(it["raw"]),
                                            self.uoc(it["text"]) * he),
                           "giay": 0.0})
            return {"ok": True, "ra": ra, "nap": 1, "gen": 1, "sr": 24000,
                    "watermark": False, "_sandbox": ""}

        GV._chay_vieneu = _g                                    # type: ignore
        return self

    def __exit__(self, *_a) -> None:
        GV._chay_vieneu = self._cu                              # type: ignore


def _loat(n: int = 14) -> tuple[list[str], list[dict]]:
    ts = ["x" * (12 + 7 * i) + "." for i in range(n)]
    it = [{"i": i, "text": ts[i], "raw": str(T / f"raw/c{i}.wav")}
          for i in range(n)]
    return ts, it


def _chay(may: MayGia, items: list[dict], bat: bool) -> dict:
    os.environ["BQ_VN_DOC_LAI"] = "1" if bat else "0"
    ket = GV._chay_vieneu(items, "py", "", "", 600, None)
    return GV._doc_lai_lan_man(items, ket, {"python": "py"}, "vnb:x", True,
                               600, None, T)


def ca4() -> None:
    """ĐỌC LẠI: có trần · không bỏ câu · chỉ nhận khi ĐỠ HƠN THẬT."""
    print("\nCA 4 — ĐỌC LẠI (máy đọc GIẢ, tiền định)")
    _ts, items = _loat()

    # (a) bắt -> đọc lại -> bản mới lành hẳn -> NHẬN, và FILE bị thay
    with MayGia({13: 4.0}) as m:
        k = _chay(m, items, True)
    b = k["_lan_man"]
    moi = [r["p"] for r in k["ra"] if r["i"] == 13][0]
    ok("4a bắt 1 câu · đọc lại 1 · NHẬN 1 · file ĐÃ ĐỔI sang bản mới",
       b["bat"] == 1 and b["doc_lai"] == 1 and b["an"] == 1
       and "lai1" in moi, f"{b['bat']}/{b['doc_lai']}/{b['an']}")
    ok("4a' vẫn đủ câu — KHÔNG BỎ CÂU NÀO", len(k["ra"]) == len(items))

    # (b) đọc lại KHÔNG đỡ hơn -> GIỮ bản cũ
    with MayGia({13: 4.0}, hong_lai={13: 4.0}) as m:
        k = _chay(m, items, True)
    b = k["_lan_man"]
    ok("4b bản mới KHÔNG đỡ hơn -> NHẬN 0, GIỮ bản đang có",
       b["bat"] == 1 and b["doc_lai"] == 2 and b["an"] == 0,
       f"đọc lại {b['doc_lai']} lượt")
    ok("4b' ...và vẫn đủ câu", len(k["ra"]) == len(items))

    # (c) đỡ hơn nhưng CHƯA QUÁ BIÊN -> vẫn giữ (biên có răng)
    with MayGia({13: 4.0}, hong_lai={13: 3.99}) as m:
        k = _chay(m, items, True)
    ok("4c đỡ hơn nhưng dưới BIÊN -> vẫn GIỮ bản cũ",
       k["_lan_man"]["an"] == 0, f"biên {GV.DOC_LAI_BIEN}")

    # (d) TRẦN số lần đọc lại mỗi câu
    with MayGia({13: 4.0}, hong_lai={13: 4.0}) as m:
        k = _chay(m, items, True)
        goi_lai = m.luot - 1
    ok("4d TRẦN đọc lại/câu = DOC_LAI_TOI_DA (đếm lượt gọi máy đọc)",
       goi_lai == GV.DOC_LAI_TOI_DA and k["_lan_man"]["vong"]
       == GV.DOC_LAI_TOI_DA, f"{goi_lai} lượt")

    # (e) TRẦN theo LOẠT: 12/30 câu hỏng (40%, DƯỚI điểm gãy của trung vị)
    ts30, it30 = _loat(30)
    tran = min(GV.DOC_LAI_TRAN_LOAT,
               max(1, int(round(GV.DOC_LAI_TY_LE_LOAT * 30))))
    with MayGia({i: 4.0 for i in range(12)}, hong_lai={}) as m:
        k = _chay(m, it30, True)
    b = k["_lan_man"]
    ok("4e bắt nhiều hơn TRẦN LOẠT -> chỉ đọc lại phần trần",
       b["bat"] >= 10 and 0 < b["doc_lai"] <= tran,
       f"bắt {b['bat']} · đọc lại {b['doc_lai']} · trần {tran}")
    ok("4e' ...và số câu KHÔNG đổi (phần dư GIỮ NGUYÊN, không bỏ)",
       len(k["ra"]) == len(it30), f"{len(k['ra'])}/{len(it30)}")

    # (e'') GIỚI HẠN THẬT CỦA BỘ DÒ, ghi thẳng thay vì giả vờ không có: mốc
    # khớp bằng TRUNG VỊ nên khi **quá nửa loạt cùng hỏng một kiểu**, chính
    # nhóm hỏng thành "bình thường" và bộ dò chỉ còn thấy vài câu lệch nhất.
    # Đo: 20/30 câu hỏng -> bắt 9, KHÔNG phải 20. Đây là đánh đổi CỐ Ý (thà
    # bỏ sót còn hơn kêu oan cả loạt rồi đọc lại cả video), và ca này tồn tại
    # để người sau đọc ra con số đó thay vì tưởng bộ dò hỏng.
    with MayGia({i: 4.0 for i in range(20)}, hong_lai={}) as m:
        k = _chay(m, it30, True)
    b2 = k["_lan_man"]
    ok("4e'' quá nửa loạt cùng hỏng -> bộ dò BỎ SÓT (giới hạn của trung vị)",
       0 < b2["bat"] < 20 and len(k["ra"]) == len(it30),
       f"20 câu hỏng -> chỉ bắt {b2['bat']}")

    # (f) máy đọc lại HỎNG / NÉM -> giữ nguyên, không mất câu
    with MayGia({13: 4.0}, ok_lai=False) as m:
        k = _chay(m, items, True)
    ok("4f lượt đọc lại trả ok=False -> GIỮ nguyên, đủ câu",
       k["_lan_man"]["an"] == 0 and len(k["ra"]) == len(items))
    with MayGia({13: 4.0}, nem=True) as m:
        k = _chay(m, items, True)
    ok("4f' lượt đọc lại NÉM -> KHÔNG nổi lên, đủ câu",
       k["_lan_man"]["an"] == 0 and len(k["ra"]) == len(items))

    # (g) TẮT -> vẫn DÒ (cột đối chứng của phép đo A/B) nhưng KHÔNG đọc lại
    with MayGia({13: 4.0}) as m:
        k = _chay(m, items, False)
        goi = m.luot
    b = k["_lan_man"]
    ok("4g TẮT: vẫn DÒ và vẫn ghi số (thước CÓ RĂNG), nhưng 0 lượt đọc lại",
       b["bat"] == 1 and b["doc_lai"] == 0 and b["an"] == 0
       and goi == 1 and b["bat_co"] is False)

    # (h) loạt LÀNH -> 0 lượt gọi thêm = 0 giây thêm
    with MayGia({}) as m:
        k = _chay(m, items, True)
        goi = m.luot
    ok("4h loạt LÀNH -> KHÔNG gọi máy đọc thêm lần nào (giá = 0)",
       k["_lan_man"]["bat"] == 0 and goi == 1)

    # (i) mốc KHÔNG được khớp lại trên nhóm nghi ngờ
    src = ast.unparse(_nut_ham(REPO / "app" / "core" / "giong_vieneu.py",
                               "_doc_lai_lan_man"))
    ok("4i lượt chấm lại dùng MỐC của loạt gốc (`moc[0], moc[1]`)",
       "lan_vuot(chu[i], g2, moc[0], moc[1])" in src)


# =========================================================== CA 5
def ca5() -> None:
    """KHÔNG đẻ cửa thứ tư · KHÔNG đụng khoá chống trùng."""
    print("\nCA 5 — KHÔNG ĐẺ CỬA MỚI, KHÔNG ĐỔI KHOÁ CHỐNG TRÙNG")
    # ĐẾM ĐÚNG CÁI CỔNG 63 ĐẾM: chỗ gọi trong **`thay_giong.py`**. (Bản đầu
    # của mục này quét cả `app/` và ra **6** rồi ĐỎ OAN — 3 chỗ còn lại là
    # đường recap NỘI BỘ của `dubbing.py`, chưa bao giờ nằm trong mốc "đúng 3
    # chỗ". Quét rộng hơn cổng gốc là tự đẻ ra một mốc khác rồi tưởng hồi quy.)
    # Đếm CẢ HAI dạng gọi: `dubbing._synth_all_words(...)` (Attribute, dạng
    # `thay_giong.py` dùng) và `_synth_all_words(...)` trần (Name — dạng
    # `dubbing.py` tự gọi trong chính nó). Chỉ đếm một dạng là bỏ sót nửa kia.
    def _dem(f: Path) -> int:
        cay = ast.parse(f.read_text(encoding="utf-8"))
        return sum(1 for x in ast.walk(cay)
                   if isinstance(x, ast.Call)
                   and "_synth_all_words" in (getattr(x.func, "attr", ""),
                                              getattr(x.func, "id", "")))

    dem = _dem(REPO / "app" / "core" / "thay_giong.py")
    ok("5a `thay_giong.py` vẫn ĐÚNG 3 chỗ gọi `_synth_all_words` (mốc cổng 63)",
       dem == 3, f"{dem} chỗ")
    ok("5a' `dubbing.py` cũng không mọc thêm chỗ gọi nào (3 chỗ recap nội bộ)",
       _dem(REPO / "app" / "core" / "dubbing.py") == 3)

    # Cờ đọc-lại nằm TRONG `giong_vieneu`, KHÔNG đi qua payload job -> khoá
    # chống trùng không thể đổi. Chứng minh bằng cả hai chiều.
    for ten in ("app/services.py", "app/core/tg_chay.py", "app/queue/jobs.py"):
        ma = _ma_that(REPO / ten)
        ok(f"5b {ten} không nhắc tới cờ đọc lại",
           "BAT_DOC_LAI" not in ma and "_bat_doc_lai" not in ma
           and "doc_lai_lan_man" not in ma)

    from app.core import tg_chay
    import inspect
    sig = inspect.signature(tg_chay.khoa_chong_trung)
    ok("5c `khoa_chong_trung` KHÔNG mọc thêm tham số nào cho việc này",
       not any("lan" in p or "doc_lai" in p for p in sig.parameters))
    a1 = tg_chay.khoa_chong_trung("D:/v.mp4", "en", "vnb:mau", "")
    os.environ["BQ_VN_DOC_LAI"] = "1"
    a2 = tg_chay.khoa_chong_trung("D:/v.mp4", "en", "vnb:mau", "")
    os.environ["BQ_VN_DOC_LAI"] = "0"
    a3 = tg_chay.khoa_chong_trung("D:/v.mp4", "en", "vnb:mau", "")
    ok("5d khoá chống trùng GIỐNG TỪNG KÝ TỰ dù bật hay tắt",
       a1 == a2 == a3, a1[:48])

    # TỰ KIỂM BỘ DÒ QUÉT TĨNH — bỏ COMMENT+STRING có thật sự ăn không.
    tam = T / "tu_kiem.py"
    tam.parent.mkdir(parents=True, exist_ok=True)
    tam.write_text('# BAT_DOC_LAI trong ghi chú\ns = "BAT_DOC_LAI trong chuỗi"\n'
                   'z = 1\n', encoding="utf-8")
    ok("5f TỰ KIỂM BỘ DÒ: `BAT_DOC_LAI` ở GHI CHÚ và CHUỖI phải bị BỎ QUA",
       "BAT_DOC_LAI" not in _ma_that(tam))
    tam.write_text("BAT_DOC_LAI = 1\n", encoding="utf-8")
    ok("5f' ...nhưng ở MÃ THẬT thì phải BẮT ĐƯỢC",
       "BAT_DOC_LAI" in _ma_that(tam))


def main() -> int:
    print("=" * 74)
    print("CỔNG 92 — DÒ CÂU LAN MAN RỒI ĐỌC LẠI (giọng nhân bản VieNeu)")
    print("=" * 74)
    T.mkdir(parents=True, exist_ok=True)
    for f in (ca1, ca2, ca3, ca4, ca5):
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
    """Dọn hộp cát. Đăng ký bằng `atexit` — lượt THỬ PHÁ có phép làm cổng chết
    giữa đường, gọi thẳng ở cuối file thì rác đọng lại trong repo."""
    try:
        shutil.rmtree(T, ignore_errors=True)
    except Exception:                                          # noqa: BLE001
        pass


atexit.register(_don)

if __name__ == "__main__":
    raise SystemExit(main())
