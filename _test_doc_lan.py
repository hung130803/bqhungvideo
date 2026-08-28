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
import re
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


# =========================================================== CA 6
def _bang_nn() -> dict:
    """Bảng hiệu chuẩn THEO TIẾNG. `{}` = chưa có (mục gọi tự báo HỎNG)."""
    import json
    f = REPO / "_moc_doc_lan_nn.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def ca6() -> None:
    """NGƯỠNG 1,5 CÓ ĐÚNG CHO TIẾNG KHÁC KHÔNG — hay nó kêu oan / bỏ sót.

    Ngưỡng `NGUONG_LAN` được hiệu chuẩn trên **MỘT** thứ tiếng (Anh) nhưng bản
    vá chạy trên **MỌI** ngôn ngữ của 200-300 kênh. CA 3 canh cột tiếng Anh;
    CA này canh đúng câu hỏi còn lại, bằng cùng một cách chọn ngưỡng:
    **chỗ thấp nhất mà arm TRẦN (giọng bản ngữ đọc ĐÚNG) không kêu lần nào.**

    Số đo ở `_do_lan_nn.py` -> `_moc_doc_lan_nn.json` (bản gọn, CÓ theo dõi
    git — `_kq*.json` bị `.gitignore` nên đọc thẳng nó là ĐỎ OAN vì KHO trên
    máy vừa clone, bệnh cổng 47 CA2 / cổng 68).
    """
    print("\nCA 6 — NGƯỠNG CÓ PHẢI ĐỔI THEO NGÔN NGỮ KHÔNG")
    d = _bang_nn()
    if not d:
        ok("6a có bảng hiệu chuẩn theo tiếng `_moc_doc_lan_nn.json`", False,
           "chạy `_do_lan_nn.py` trước")
        return
    arm = d.get("arm") or {}
    co_tran = [k[4:] for k in arm if k.startswith("EDG_") and len(arm[k]) >= 30]
    ok("6a bảng có arm TRẦN cho >= 3 tiếng ngoài tiếng Anh",
       len(co_tran) >= 3, "trần: " + ", ".join(sorted(co_tran)))

    ng = DL.NGUONG_LAN
    for nn in sorted(co_tran):
        tran = arm[f"EDG_{nn}"]
        oan = sum(1 for h in tran if h["lan"] >= ng)
        # MỆNH ĐỀ CHẶN: kêu trên giọng bản ngữ đọc ĐÚNG là kêu OAN, và kêu oan
        # thì lượt xuất thật đi đọc lại một câu KHÔNG hỏng — tốn giờ của
        # 200-300 kênh cho không.
        ok(f"6b[{nn}] tại ngưỡng {ng} arm TRẦN KHÔNG kêu oan lần nào",
           oan == 0, f"{oan}/{len(tran)}")

    # ...và ngưỡng đang dùng phải NẰM TRÊN chỗ thấp nhất mà trần im, với MỌI
    # tiếng đã đo. Đây là mệnh đề TRUNG TÂM của CA này: nó chính là thứ nói
    # "KHÔNG phải đổi ngưỡng theo tiếng", và nó sẽ ĐỎ ngay khi một lượt hiệu
    # chuẩn sau đo ra một tiếng cần ngưỡng CAO HƠN.
    chon = d.get("chon_nguong") or {}
    xau = {k: v for k, v in chon.items() if v and v > ng}
    ok("6c ngưỡng đang dùng >= chỗ thấp nhất mà TRẦN im, ở MỌI tiếng đã đo",
       not xau, "cần cao hơn: " + str(xau) if xau
       else " · ".join(f"{k} {v:.1f}" for k, v in sorted(chon.items())))

    # NÓI THẲNG tiếng nào KHÔNG đặt được ngưỡng, thay vì im lặng bỏ qua.
    # (bài học `ty_giu`: 1 điểm dữ liệu thì KHÔNG đặt ngưỡng — cổng phải GHI
    # NHẬN chỗ chưa biết, không được để nó trông như đã biết.)
    trong = [nn for nn in sorted(co_tran) if not (arm.get(f"VNB_{nn}") or [])]
    ok("6d cổng GHI NHẬN tiếng nào giọng nhân bản KHÔNG đọc được (0 mục)",
       True, ("không có" if not trong else ", ".join(trong)
              + " -> câu hỏi ngưỡng KHÔNG áp dụng"))

    # BẤT BIẾN: mặc định vẫn là hành vi tiếng Anh hôm nay. Không có mục này
    # thì ai đó "chỉnh cho vừa" một tiếng khác sẽ đổi luôn tiếng Anh.
    ok("6e mặc định GIỮ NGUYÊN ngưỡng tiếng Anh = 1.5", ng == 1.5, str(ng))
    # BẢN ĐẦU CỦA MỤC NÀY CẤM HẲN `NGUONG_THEO_NN` TỒN TẠI — cấm quá tay và
    # cấm sai chỗ. Thứ phải chặn KHÔNG phải cái NÚM mà là **SỐ GÕ TAY**: bảng
    # RỖNG thì `nguong_cho` trả 1,5 cho mọi tiếng, tức hành vi giống hệt lúc
    # chưa có núm (mục 6e'' chấm bằng cách GỌI THẬT, không quét chuỗi). Còn
    # cấm núm thì lượt hiệu chuẩn sau buộc phải đi sửa CHỖ GỌI trong
    # `giong_vieneu` — đắt hơn và dễ sai hơn hẳn thêm một dòng vào bảng.
    ok("6e' bảng ngưỡng theo tiếng phải RỖNG — cấm SỐ GÕ TAY không có phép đo",
       DL.NGUONG_THEO_NN == {},
       "rỗng" if not DL.NGUONG_THEO_NN else f"có số bịa: {DL.NGUONG_THEO_NN}")

    thu = ["en", "vi", "zh", "ja", "ko", "vi-VN", "zh_CN", "", None, "xx"]
    lech = {t: DL.nguong_cho(t) for t in thu if DL.nguong_cho(t) != 1.5}
    ok("6e'' `nguong_cho` trả ĐÚNG 1.5 cho mọi tiếng (kể cả nhãn lạ/rỗng)",
       not lech, f"{len(thu)}/{len(thu)} nhãn = 1.5" if not lech else str(lech))

    # TỰ KIỂM BỘ DÒ: 6e' chỉ có nghĩa nếu nó THẬT SỰ bắt được số gõ tay. Thiếu
    # mục này thì 6e' là con dấu — nó vẫn ĐẠT kể cả khi `nguong_cho` bỏ qua
    # bảng hoàn toàn (tức núm là đồ trang trí).
    _cu = dict(DL.NGUONG_THEO_NN)
    try:
        DL.NGUONG_THEO_NN["zh"] = 1.2
        ok("6e''' TỰ KIỂM: nhét số bịa vào bảng thì `nguong_cho` ĂN ngay "
           "(6e' có răng)",
           DL.nguong_cho("zh") == 1.2 and DL.nguong_cho("zh-CN") == 1.2
           and DL.nguong_cho("en") == 1.5,
           f"zh {DL.nguong_cho('zh')} · zh-CN {DL.nguong_cho('zh-CN')} · "
           f"en {DL.nguong_cho('en')}")
    finally:
        DL.NGUONG_THEO_NN.clear()
        DL.NGUONG_THEO_NN.update(_cu)


# =========================================================== CA 7
def ca7() -> None:
    """GIỌNG NHÂN BẢN KHÔNG ĐỌC ĐƯỢC MỘT TIẾNG -> KHÔNG ĐƯỢC LẪN HAI GIỌNG."""
    print("\nCA 7 — TIẾNG MÀ GIỌNG NHÂN BẢN KHÔNG ĐỌC ĐƯỢC")
    d = _bang_nn()
    arm = (d.get("arm") or {}) if d else {}
    cam = [k[4:] for k in arm
           if k.startswith("VNB_") and not arm[k]
           and arm.get("EDG_" + k[4:])]
    ok("7a bảng nêu ĐÍCH DANH tiếng giọng nhân bản đọc ra 0 mục dùng được",
       bool(d), ("không có tiếng nào" if not cam else ", ".join(sorted(cam))))
    # ALL-OR-NOTHING vẫn còn, chỉ thôi bập ở MỘT câu hỏng. Ca "không đọc được
    # tiếng đó" ra 0/N -> vẫn BỎ CẢ LOẠT (hỏng TO, không hỏng ÂM THẦM); ca
    # "1/168 hỏng" thì cứu phần còn lại. Xem khối `BO_LOAT_TU_SO_CAU`.
    ok("7b ngưỡng bỏ loạt đếm theo SỐ CÂU (chùm lẻ tẻ đo được 1-2 câu)",
       GV.BO_LOAT_TU_SO_CAU == 3, str(GV.BO_LOAT_TU_SO_CAU))
    ok("7b' loạt NGẮN vẫn có chốt theo tỉ lệ",
       0.0 < GV.BO_LOAT_TY_LE < 1.0, str(GV.BO_LOAT_TY_LE))
    ok("7b'' `TY_LE_TOI_THIEU` đã GỠ (đổi thẳng, không để hằng số chết)",
       not hasattr(GV, "TY_LE_TOI_THIEU"), "còn" if hasattr(
           GV, "TY_LE_TOI_THIEU") else "đã gỡ")
    # Câu CHỈ DẤU CÂU: WAV 0 giây là kết quả ĐÚNG, không được tính là hỏng —
    # đo thật `"-"` -> 0 giây (`_do_bo_loat.py phep_bien`).
    ok("7c `khong_co_gi_de_doc` bắt đúng câu chỉ có dấu câu",
       all(GV.khong_co_gi_de_doc(t) for t in ("-", "...", "?", " ", "", "!!")),
       "6/6")
    ok("7c' và KHÔNG kêu oan câu có nội dung (kể cả chữ Hán)",
       not any(GV.khong_co_gi_de_doc(t)
               for t in ("Xin chào", "hi", "1", "现", "OK.")),
       "0/5 bị kêu")
    # `现` là chữ THẬT (có trong transcript anh Hùng) mà VieNeu ra 0 âm vị ->
    # đọc lại vô ích, nhưng nó vẫn là câu HỎNG, không phải câu được tha.
    ok("7d chữ ngoài tầm phiên âm KHÔNG bị coi là 'không có gì để đọc'",
       (not GV.khong_co_gi_de_doc("现")
        and GV.ty_le_chu_bo("现") > GV.TY_LE_CHU_BO_TOI_DA), "1.0 > 0.5")


# =========================================================== CA 8
def ca8() -> None:
    """BỘ ĐẾM TỪ CỦA CHÍNH PHÉP HIỆU CHUẨN — CJK-aware, và KHÔNG đổi latin.

    Ngưỡng của `doc_lan` được hiệu chuẩn bằng `_do_vnb_lan` / `_do_lan_nn`, mà
    hai file đó chấm "câu này có bịa không" bằng bộ đếm từ của
    `_do_vieneu_en.chuan_tu`. Bộ đếm cũ dùng regex CHỈ GIỮ chữ latin nên câu
    **Trung · Nhật · Hàn** ra **0 token** -> mọi tỉ lệ ra 0 -> bảng hiệu chuẩn
    **TỰ ĐẠT OAN** và ngưỡng đặt ra từ đó là ngưỡng của một bảng số rỗng.
    Đúng lỗi đã sập ở cổng 52/54, và đúng họ *"phép đo hỏng phát chứng nhận"*
    (`astats` cổng 53 · `startswith` cổng 44).
    """
    print("\nCA 8 — BỘ ĐẾM TỪ CỦA PHÉP HIỆU CHUẨN (CJK-aware)")
    import re as _re
    import _do_vieneu_en as DV

    def _cu(s: str) -> list:
        """Bộ chuẩn hoá CŨ, dựng lại nguyên xi — dùng làm ĐỐI CHỨNG."""
        s = _re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\s]", " ", (s or "").lower())
        return _re.sub(r"\s+", " ", s).strip().split()

    ZH = "今天天气很好，我们一起出去走走吧。"
    JA = "今日はとてもいい天気なので、一緒に散歩しましょう。"
    KO = "오늘은 날씨가 아주 좋으니까 같이 산책하러 가요."
    ok("8a câu TRUNG ra nhiều token (không phải 0)",
       len(DV.chuan_tu(ZH)) >= 10, f"{len(DV.chuan_tu(ZH))} token")
    ok("8b câu NHẬT ra nhiều token",
       len(DV.chuan_tu(JA)) >= 10, f"{len(DV.chuan_tu(JA))} token")
    # TIẾNG HÀN CÓ DẤU CÁCH — đừng gộp chung với Trung/Nhật. `recap.
    # _word_tokens` coi hangul là CJK nên nó cắt câu 7 từ thành 20 ÂM TIẾT;
    # cắt kiểu đó là đổi MẪU SỐ, mọi tỉ lệ tiếng Hàn thành số khác hẳn.
    from app.ai.recap import _word_tokens
    ko = DV.chuan_tu(KO)
    ok("8c câu HÀN tách theo TỪ, KHÔNG theo âm tiết",
       len(ko) == 7 and ko[0] == "오늘은",
       f"{len(ko)} token · recap._word_tokens ra {len(_word_tokens(KO))}")

    # BẤT BIẾN: chữ latin phải ra Y HỆT bản cũ -> mọi con số tiếng Anh/Việt đã
    # công bố không đổi một chữ số nào.
    from _bo_cau_thu_doc import CORPUS
    n = lech = 0
    for l_nn in ("en", "vi"):
        for _l, c, toks in CORPUS[l_nn]:
            for s in [c] + list(toks):
                n += 1
                lech += int(_cu(s) != DV.chuan_tu(s))
    ok("8d BẤT BIẾN latin: chữ Anh/Việt tách Y HỆT bản cũ",
       lech == 0, f"{n - lech}/{n} chuỗi")

    # TỰ KIỂM BỘ DÒ — không có mục này thì 8a/8b/8c chỉ là con dấu: chúng
    # không chứng minh được rằng bộ CŨ thật sự hỏng ở đúng chỗ ấy.
    ok("8e TỰ KIỂM: bộ chuẩn hoá CŨ thật sự ra 0 token cho Trung/Nhật/Hàn",
       _cu(ZH) == [] and _cu(JA) == [] and _cu(KO) == [],
       f"cũ: zh {len(_cu(ZH))} · ja {len(_cu(JA))} · ko {len(_cu(KO))}")

    # MỘT bộ tách cho MỌI cột số. `dem_op` từng CHÉP LẠI biểu thức của `wer`,
    # và bản sao ấy đã lệch thật (vá `wer` mà `dem_op` vẫn cắt sạch chữ Hán).
    nut = _nut_ham(REPO / "_do_adam_en.py", "dem_op")
    ok("8f `dem_op` GỌI `chuan_tu`, không tự đẻ bộ chuẩn hoá thứ hai",
       nut is not None and "chuan_tu" in _goi_ten(nut)
       and "def chuan" not in ast.unparse(nut))
    ok("8f' ...và `wer` cũng đi qua đúng bộ đó",
       "chuan_tu" in _goi_ten(_nut_ham(REPO / "_do_vieneu_en.py", "wer")))

    # ÉP ĐÚNG NGÔN NGỮ khi chép ngược. Bản cũ ghi cứng `"en" if nn=="en" else
    # "vi"` (lúc đó chỉ có hai tiếng) -> ép whisper chép tiếng Trung/Nhật/Hàn
    # bằng tiếng VIỆT, tức đo một thứ khác hẳn rồi báo như thật.
    #
    # BẢN ĐẦU CỦA MỤC NÀY LÀ CON DẤU — phép phá 14 LỌT và đó là cách phát
    # hiện ra. Nó tìm chuỗi `ep = "en" if nn == "en" else "vi"` TRONG
    # `_ma_that(...)`, mà `_ma_that` bỏ COMMENT **và STRING** nên chính mấy
    # chữ `"en"`/`"vi"` bị xoá: mã đã phá đọc ra `ep = if nn == else` và phép
    # tìm KHÔNG BAO GIỜ khớp -> mục ĐẠT vĩnh viễn.
    # Đây là biến thể MỚI của họ bẫy quét-chuỗi (47/51/53/73/80/86): mấy lần
    # trước là ĐỎ OAN vì quét trên mã CÒN ghi chú, lần này là PASS OAN vì
    # quét trên mã ĐÃ BỎ chuỗi. Rút ra: **mệnh đề nào nói về GIÁ TRỊ chuỗi
    # thì không được kiểm bằng `_ma_that` — phải đi bằng AST.**
    cay = ast.parse(_doc_nguon(REPO / "_do_vieneu_en.py"))
    gan = [n for n in ast.walk(cay) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "ep" for t in n.targets)]
    xau = [ast.unparse(n) for n in gan if not isinstance(n.value, ast.Name)]
    ok("8g `chay_arm` KHÔNG còn ghi cứng hai ngôn ngữ khi chép ngược "
       "(`ep` phải là BIẾN, không phải biểu thức điều kiện)",
       bool(gan) and not xau,
       f"{len(gan)} phép gán `ep`, đều là biến" if gan and not xau
       else (f"ghi cứng: {xau}" if xau else "KHÔNG tìm thấy phép gán `ep`"))
    ok("8g' bảng nhãn ngôn ngữ đủ 5 tiếng của corpus",
       set(DV.TEN_NN) >= {"en", "vi", "zh", "ja", "ko"},
       ", ".join(sorted(DV.TEN_NN)))


# =========================================================== CA 9
def ca9() -> None:
    """HỆ CHỮ VieNeu KHÔNG PHIÊN ÂM ĐƯỢC -> CHẶN TRƯỚC KHI ĐỌC.

    Đo nền (`_do_am_vieneu.py`, chạy CHÍNH `phonemize_text` trong CHÍNH venv
    VieNeu): chữ Hán · kana · hangul ra **0 ký tự âm**. Hệ quả đo được
    end-to-end (`_kq_lan_nn.txt`): Trung/Nhật lùi edge sau 192-297 giây GPU;
    **Hàn thì KHÔNG lùi** — `vieneu trả 58/58 HỢP LỆ` mà WER 308-351% và Groq
    dán nhãn tiếng Hàn cho 0-1/34 câu, tức 17-21 giây LẢM NHẢM mỗi câu với
    mã thoát 0.
    """
    print("\nCA 9 — HỆ CHỮ NGOÀI TẦM PHIÊN ÂM: CHẶN TRƯỚC KHI ĐỐT GPU")
    try:
        import _bo_cau_thu_doc as B
    except Exception as e:                                     # noqa: BLE001
        ok("9 corpus dùng chung nạp được", False, f"{type(e).__name__}: {e}")
        return

    def _cau(nn: str) -> list:
        return [c for _l, c, _t in B.CORPUS[nn]]

    # BẤT BIẾN SỐNG CÒN: tiếng gốc của model KHÔNG BAO GIỜ bị chốt này đụng.
    # Chốt chặn mà bắn vào tiếng Việt là hỏng nặng hơn hẳn bệnh nó đi chữa.
    xau = {nn: max(GV.ty_le_chu_bo(c) for c in _cau(nn)) for nn in ("vi", "en")}
    ok("9a BẤT BIẾN: mọi câu Việt/Anh ra tỉ lệ chữ-bị-xoá = 0,000",
       all(v == 0.0 for v in xau.values()),
       " · ".join(f"{k} max {v:.3f}" for k, v in xau.items()))
    ok("9b ...nên loạt Việt/Anh KHÔNG BAO GIỜ bị chặn",
       not GV.khong_doc_duoc(_cau("vi"))[0]
       and not GV.khong_doc_duoc(_cau("en"))[0],
       f"vi {GV.khong_doc_duoc(_cau('vi'))[1]:.3f} · "
       f"en {GV.khong_doc_duoc(_cau('en'))[1]:.3f}")

    ba = {nn: GV.khong_doc_duoc(_cau(nn)) for nn in ("zh", "ja", "ko")}
    ok("9c loạt Trung/Nhật/Hàn BỊ CHẶN (G2P xoá sạch, đo 0 ký tự âm)",
       all(v[0] for v in ba.values()),
       " · ".join(f"{k} {v[1]:.3f}" for k, v in ba.items()))

    # KHÔNG ĐƯỢC CHẶN OAN câu tiếng Việt có chen chữ Hán (tên riêng, trích
    # dẫn). Đây đúng họ bẫy `料理` của cổng 52, chỉ khác chiều: ở đó là gán
    # oan theo mặt chữ, ở đây là CHẶN oan theo mặt chữ.
    pha = ["Bộ phim 料理 rất hay nhé các bạn",
           "Anh ấy tên là 山田 và sống ở Hà Nội nhiều năm rồi",
           "Kênh YouTube này có 2026 người theo dõi mỗi ngày"]
    ok("9d câu Việt chen vài chữ Hán/Nhật KHÔNG bị chặn oan",
       not GV.khong_doc_duoc(pha)[0],
       f"{GV.khong_doc_duoc(pha)[1]:.3f} (trần {GV.TY_LE_CHU_BO_TOI_DA})")

    # KHÔNG BAO GIỜ NÉM, và nghi ngờ thì NHƯỜNG đường cũ.
    biên = [[], [None, "", "   "], ["..."], ["今天天气很好", "他打开门"]]
    try:
        ra = [GV.khong_doc_duoc(x) for x in biên]
        ok("9e ca biên (rỗng · None · toàn dấu câu · loạt QUÁ NGẮN) -> KHÔNG "
           "chặn, KHÔNG ném",
           all(not r[0] for r in ra), " · ".join(str(r) for r in ra))
    except Exception as e:                                     # noqa: BLE001
        ok("9e ca biên -> KHÔNG chặn, KHÔNG ném", False,
           f"NÉM {type(e).__name__}: {e}")
    ok("9e' câu lẻ toàn chữ Hán vẫn ra 1,000 (hàm THUẦN vẫn nói thật)",
       GV.ty_le_chu_bo("今天天气很好") == 1.0
       and GV.ty_le_chu_bo("안녕하세요") == 1.0,
       f"zh {GV.ty_le_chu_bo('今天天气很好')} · "
       f"ko {GV.ty_le_chu_bo('안녕하세요')}")

    # ═══ MỆNH ĐỀ TRUNG TÂM: CHẶN **TRƯỚC** KHI GỌI MÁY ĐỌC ═══
    # Không đủ nếu chỉ hỏi "có nhánh đó không" — phải chứng minh `_chay_vieneu`
    # KHÔNG được gọi. Đó là khác biệt giữa "lùi edge sau 5 phút GPU" và "lùi
    # edge ngay", và với 200-300 kênh thì 5 phút đó là tiền thật.
    goi: list = []

    def _giandiep(*a, **k):
        goi.append(1)
        return {"ok": False, "loi": "GIÁN ĐIỆP: lẽ ra KHÔNG được gọi"}

    _cu = GV._chay_vieneu
    try:
        GV._chay_vieneu = _giandiep                            # type: ignore
        n = 6
        okz, wz = GV._doc(_cau("zh")[:n], [""] * n, "vnb:x",
                          {"python": "KHONG-DUOC-DUNG"}, "+0%", "zh",
                          False, 60, None)
        ok("9f loạt Trung: `_chay_vieneu` KHÔNG được gọi lần nào",
           not goi, f"{len(goi)} lượt gọi")
        ok("9f' ...và trả `ok` TOÀN FALSE (all-or-nothing -> lùi edge cả video)",
           len(okz) == n and not any(okz) and wz == [[] for _ in range(n)],
           f"ok={okz}")

        goi.clear()
        okk, _ = GV._doc(_cau("ko")[:n], [""] * n, "vnb:x",
                         {"python": "KHONG-DUOC-DUNG"}, "+0%", "ko",
                         False, 60, None)
        ok("9g loạt HÀN cũng bị chặn — ca NGUY NHẤT vì nó KHÔNG tự lùi edge "
           "(đo: 58/58 HỢP LỆ · WER 308-351% · nhãn tiếng đúng 0-1/34)",
           not goi and not any(okk), f"{len(goi)} lượt gọi · ok={okk}")

        # TỰ KIỂM BỘ DÒ: gỡ hệ chữ khỏi bộ dò thì loạt Trung phải ĐI TIẾP tới
        # máy đọc. Thiếu mục này thì 9f/9g là con dấu — chúng vẫn ĐẠT kể cả
        # khi `_doc` từ chối MỌI thứ vì một lý do khác.
        goi.clear()
        _re_cu = GV._CHU_G2P_BO
        try:
            GV._CHU_G2P_BO = re.compile(r"(?!x)x")             # type: ignore
            GV._doc(_cau("zh")[:n], [""] * n, "vnb:x",
                    {"python": "KHONG-DUOC-DUNG"}, "+0%", "zh",
                    False, 60, None)
        finally:
            GV._CHU_G2P_BO = _re_cu                            # type: ignore
        ok("9h TỰ KIỂM: gỡ hệ chữ khỏi bộ dò -> loạt Trung ĐI TIẾP tới máy "
           "đọc (9f/9g có răng)",
           len(goi) == 1, f"{len(goi)} lượt gọi")
    finally:
        GV._chay_vieneu = _cu                                  # type: ignore

    # Quét tĩnh: chốt phải nằm trong `_doc` và phải đứng TRƯỚC lượt gọi máy
    # đọc. Đọc bằng AST — quét chuỗi thì trúng chính khối ghi chú giải thích
    # bản vá (bài học 47/51/53/73/80/86, đã sập sáu lần).
    cay = ast.parse(_doc_nguon(REPO / "app" / "core" / "giong_vieneu.py"))
    than = next((x for x in ast.walk(cay)
                 if isinstance(x, ast.FunctionDef) and x.name == "_doc"), None)
    ok("9i tìm thấy hàm `_doc`", than is not None)
    if than is not None:
        d_chan = d_doc = -1
        for nut in ast.walk(than):
            if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name):
                if nut.func.id == "khong_doc_duoc" and d_chan < 0:
                    d_chan = nut.lineno
                if nut.func.id == "_chay_vieneu" and d_doc < 0:
                    d_doc = nut.lineno
        ok("9j `_doc` GỌI `khong_doc_duoc` (không phải chỉ khai hàm rồi bỏ đó)",
           d_chan > 0, f"dòng {d_chan}")
        ok("9k ...và gọi nó TRƯỚC `_chay_vieneu`",
           0 < d_chan < d_doc, f"chặn dòng {d_chan} · đọc dòng {d_doc}")

    # Bộ dò phải bắt ĐÚNG ba hệ chữ đo được là ra 0 âm, và KHÔNG bắt chữ
    # Latin/số (nếu không thì nó chặn cả tiếng Việt).
    bat = {"Hán": "今", "hira": "こ", "kata": "コ", "hangul": "안"}
    khong = {"latin": "a", "việt": "ế", "số": "7", "hoa": "A"}
    ok("9l bộ dò bắt ĐỦ Hán · hiragana · katakana · hangul",
       all(GV._CHU_G2P_BO.search(v) for v in bat.values()),
       " · ".join(k for k, v in bat.items() if GV._CHU_G2P_BO.search(v)))
    ok("9m ...và KHÔNG bắt chữ Latin/tiếng Việt/chữ số",
       not any(GV._CHU_G2P_BO.search(v) for v in khong.values()),
       "sạch" if not any(GV._CHU_G2P_BO.search(v) for v in khong.values())
       else str([k for k, v in khong.items() if GV._CHU_G2P_BO.search(v)]))


def _doc_nguon(f: Path) -> str:
    """Đọc file mã bằng UTF-8 — KHÔNG để Python lấy bảng mã mặc định của máy.

    `inspect.getsource` mở theo cp1252 nên docstring tiếng Việt ra mojibake
    rồi `ast.parse` nổ (bài học cổng 71).
    """
    return io.open(f, encoding="utf-8").read()


def main() -> int:
    print("=" * 74)
    print("CỔNG 92 — DÒ CÂU LAN MAN RỒI ĐỌC LẠI (giọng nhân bản VieNeu)")
    print("=" * 74)
    T.mkdir(parents=True, exist_ok=True)
    for f in (ca1, ca2, ca3, ca4, ca5, ca6, ca7, ca8, ca9):
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
