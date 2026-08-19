# -*- coding: utf-8 -*-
"""CỔNG 73 — GIÓNG HÀNG CƯỠNG BỨC (`app/core/giong_hang.py`).

VÌ SAO CÓ CỔNG NÀY (18/08/2026). `giong_hang.py` là chỗ lấy MỐC TỪNG CHỮ cho
**mọi máy đọc không tự trả mốc** (Piper, OmniVoice, và mọi bộ thêm sau) —
tức nó nằm trên đường đi của phụ đề thay tiếng. Nhưng tới hôm nay nó mới chỉ
có **phép đo** (`_do_giong_hang.py`) và bị canh **GIÁN TIẾP** qua cổng 72.
Cổng không nằm trong `_chay_hoi_quy.py` thì chỉ là một file .py nằm đó (cổng
70 vừa dính đúng bẫy này), mà không có cổng nào thì còn tệ hơn.

NĂM MỆNH ĐỀ CỔNG NÀY CANH — mỗi cái đều có tiền lệ hỏng THẬT:

  1. **KHÔNG NẠP torch VÀO TIẾN TRÌNH APP.** `import torch` sau khi Qt đã nạp
     là ACCESS VIOLATION và `try/except` KHÔNG chặn được (cổng 55). Mã torch
     nằm trong `_MA_GIONG` dạng CHUỖI — nên quét tĩnh **bắt buộc phải bỏ
     STRING**, không thì chính bản vá đúng bị kể là vi phạm (bài học 47/51/54).
  2. **THIẾU ĐỒ THÌ LÙI ÊM, KHÔNG NỔ, VÀ KHÔNG NUỐT MỐC CŨ.** Máy nhân viên
     chưa tải 1,2 GB thì mọi thứ phải chạy y như trước. Trả mốc RỖNG giữa mẻ
     là chữ biến mất ở đúng mấy câu đó.
  3. **DẤU GẠCH NỐI KHÔNG ĐƯỢC GIẾT CẢ CÂU** — LỖI THẬT, log ghi
     `ValueError: targets Tensor shouldn't contain blank index` ngày 18/08.
     Bảng token MMS_FA ánh xạ `'-' -> 0`, mà 0 chính là blank truyền cho
     `forced_align`; uroman giữ nguyên gạch nối ("COVID-19" -> "COVID-19").
     Một chữ có gạch nối => cả câu mất sạch mốc, mã thoát vẫn 0.
  4. **MỐC VÔ LÝ PHẢI BỊ BỎ, KHÔNG ĐƯỢC CHẠY TIẾP XUỐNG PHỤ ĐỀ.** Mốc lùi về
     sau = chữ nhảy ngược trên màn hình, và `rc` vẫn 0.
  5. **NÚT TẢI KHÔNG ĐƯỢC LẶP LỖI `_lib` CỦA DEMUCS** (cổng 58): thiếu
     `--ignore-installed` là pip BỎ QUA gói máy đã có -> máy dev xanh, máy
     anh Hùng đỏ. Và `cai_giong_hang` KHÔNG BAO GIỜ được ghi vào `_lib`.

**TỰ KIỂM: GỠ CHỐT RA THÌ PHẢI ĐỎ** — CA 2c và CA 5b dựng lại mã bản CŨ rồi
bắt bộ dò phải kêu. Cổng không tự kiểm được thì chỉ là con dấu (bài học cổng
56d/64/65).

KHÔNG ĐỐT GÌ TRONG HỒI QUY: cổng KHÔNG gọi Groq, KHÔNG chạy pip, KHÔNG tải
gì. Phần chạy THẬT (CA 5c) chỉ dùng edge-tts + model đã có trên máy; máy chưa
có model thì mục đó **BỎ QUA** (không ĐẠT — chấm ĐẠT là phát chứng nhận
khống, đúng bệnh `astats` cổng 53).
"""
from __future__ import annotations

import ast
import asyncio
import os
import shutil
import sys
import tempfile
import tokenize
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

import _test_guard  # noqa: E402,F401  (bắt buộc: cấm mở Explorer/trình phát)

DAT = 0
HONG = 0
BO_QUA = 0
_BO: list[str] = []
NGUON = REPO / "app" / "core" / "giong_hang.py"


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))


def bo_qua(nhan: str, ly_do: str) -> None:
    """KHÔNG chấm. Không ĐẠT (khỏi phát chứng nhận khống) và không HỎNG (đỏ
    oan thì người ta thôi đọc cổng — bài học cổng 41/47). Dòng tổng kết in
    riêng nên một lượt bỏ qua không thể trông giống lượt chấm đủ."""
    global BO_QUA
    BO_QUA += 1
    _BO.append(nhan)
    print(f"  BỎ QUA {nhan} — {ly_do}")


def _ma_that(p: Path) -> str:
    """Mã nguồn BỎ COMMENT + STRING.

    BẮT BUỘC ở file này: `_MA_GIONG` là một CHUỖI chứa `import torch`, nên
    quét bằng `in` cả file sẽ báo vi phạm cho chính kiến trúc ĐÚNG.
    """
    ra = []
    with open(p, "rb") as f:
        for t in tokenize.tokenize(f.readline):
            if t.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(t.string)
    return " ".join(ra)


def _ham(p: Path, ten: str) -> ast.AST:
    """Nút AST của một hàm — đọc file bằng utf-8 TƯỜNG MINH.

    `inspect.getsource` mở file theo bảng mã MẶC ĐỊNH của máy (cp1252) nên
    docstring tiếng Việt ra mojibake rồi `ast.parse` nổ — cổng 71 đã sập
    đúng chỗ này.
    """
    cay = ast.parse(p.read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    raise AssertionError(f"không thấy hàm {ten}")


# ══════════════════════════════════════════════════════════════════
def main() -> int:                                          # noqa: C901
    from app.core import dubbing
    from app.core import giong_hang as gh

    print("=" * 74)
    print("CỔNG 73 — GIÓNG HÀNG CƯỠNG BỨC")
    print("=" * 74)

    # ══════════════ CA 1 — DÒ MÁY: NÓI THẬT, KHÔNG MƯỢN ═════════════════
    print("\nCA 1 — dò máy có đủ đồ chưa")
    tt = gh.tinh_trang_giong_hang()
    ok(set(tt) >= {"co", "thieu", "ngoai_lib", "lib_torch", "thu_muc",
                   "model", "cai_duoc", "vi_sao_khong_cai"},
       "1a `tinh_trang_giong_hang` trả đủ khoá", f"{sorted(tt)}")
    ok(isinstance(gh.co_giong_hang(), bool),
       "1b `co_giong_hang()` trả bool, KHÔNG ném", f"{tt['co']}")
    cu = os.environ.get("BQ_GIONG_HANG")
    try:
        os.environ["BQ_GIONG_HANG"] = "0"
        tat = gh.co_giong_hang()
    finally:
        os.environ.pop("BQ_GIONG_HANG", None)
        if cu is not None:
            os.environ["BQ_GIONG_HANG"] = cu
    ok(tat is False,
       "1c `BQ_GIONG_HANG=0` TẮT HẲN (cần cho đo A/B + gỡ rối máy user mà "
       "không phải xoá 1,2 GB)")
    # `thieu` phải là sự thật của thư mục MÌNH, không phải "import được
    # không" — máy dev mượn `.venv` rồi báo đã cài là đúng lỗ hổng cổng 58.
    with tempfile.TemporaryDirectory(prefix="bq_gh73_") as tam:
        os.environ["BQ_GIONG_HANG_LIB"] = tam
        try:
            t2 = gh.tinh_trang_giong_hang()
        finally:
            os.environ.pop("BQ_GIONG_HANG_LIB", None)
    ok(not t2["co"] and "torchaudio" in t2["thieu"]
       and any("MMS_FA" in x for x in t2["thieu"]),
       "1d thư mục RỖNG -> nói ĐÍCH DANH thứ còn thiếu (không chỉ 'chưa có')",
       f"{t2['thieu']}")
    ok(t2["thu_muc"] == tam,
       "1e `BQ_GIONG_HANG_LIB` ép được chỗ để đồ (test + gỡ rối)")

    # BẢN ĐÓNG GÓI PHẢI RA `DATA_DIR`, KHÔNG CẠNH `.exe` — lượt tự cập nhật
    # `rmdir /S /Q _internal.old` xoá sạch (cổng 58 CA 5, đã xảy ra thật).
    import config
    goc_frozen = getattr(sys, "frozen", None)
    try:
        sys.frozen = True                                    # type: ignore
        d_frozen = gh.thu_muc_gh()
    finally:
        if goc_frozen is None:
            del sys.frozen                                   # type: ignore
        else:
            sys.frozen = goc_frozen                          # type: ignore
    ok(Path(d_frozen) == Path(config.DATA_DIR) / "_giong_hang",
       "1f bản .exe để đồ ở DATA_DIR, KHÔNG cạnh .exe (bài học cổng 58 CA5: "
       "tự cập nhật xoá sạch _internal)", d_frozen)
    ok(Path(gh.thu_muc_gh()) == REPO / "_giong_hang",
       "1g chạy NGUỒN vẫn dùng `<repo>/_giong_hang` (chỉ đổi nhánh `frozen` "
       "— không bỏ rơi `_giong_hang` của máy dev, đúng chốt cổng 58 CA5d)",
       gh.thu_muc_gh())

    # ══════════════ CA 2 — KHÔNG NẠP torch VÀO TIẾN TRÌNH APP ═══════════
    print("\nCA 2 — bất biến 1: app KHÔNG BAO GIỜ import torch")
    ma = _ma_that(NGUON)
    xau = [g for g in ("torch", "torchaudio", "uroman")
           if f"import {g}" in ma]
    ok(not xau,
       "2a `giong_hang.py` KHÔNG import torch/torchaudio/uroman ở tầng app "
       "(access violation sau khi Qt nạp, try/except KHÔNG chặn)", f"{xau}")
    ok("import torch" in gh._MA_GIONG,
       "2b ... mã torch VẪN CÓ, nhưng nằm trong `_MA_GIONG` dạng CHUỖI (chỉ "
       "tiến trình con chạy)")
    # TỰ KIỂM BỘ DÒ: quét bằng `in` cả file thì `_MA_GIONG` làm 2a đỏ oan.
    tho = NGUON.read_text(encoding="utf-8")
    ok("import torch" in tho and "import torch" not in ma,
       "2c TỰ KIỂM BỘ DÒ: quét THÔ thấy `import torch` mà quét-bỏ-STRING thì "
       "không -> bộ dò đang thật sự bỏ chuỗi (không thì 2a đỏ oan vĩnh viễn)")

    # ══════════════ CA 3 — THIẾU ĐỒ THÌ LÙI ÊM ══════════════════════════
    print("\nCA 3 — thiếu đồ: lùi êm, không nổ, không nuốt mốc cũ")
    with tempfile.TemporaryDirectory(prefix="bq_gh73_") as tam:
        os.environ["BQ_GIONG_HANG_LIB"] = tam
        try:
            r = gh.giong_hang_loat(["a.wav", "b.wav"], ["x", "y"], "vi")
            ok(r == [[], []],
               "3a thiếu đồ -> list RỖNG ĐỦ ĐỘ DÀI, không ném", f"{r}")
            r2 = gh.giong_hang_loat(["a.wav"], ["x", "y"], "vi")
            ok(r2 == [[]],
               "3b số wav khác số câu -> rỗng đủ độ dài (không lệch chỉ số)",
               f"{r2}")
            ok(gh.giong_hang_loat([], [], "vi") == [],
               "3c loạt rỗng -> [] (không nổ ở phép chia)")
            # CỬA CHUNG: thiếu đồ thì mốc CŨ phải về nguyên vẹn.
            moc_cu = [[[0.0, 0.5, "xin"]], [[0.0, 0.4, "chào"]]]
            ra = asyncio.run(dubbing._moc_giong_hang(
                ["xin", "chào"], ["a.wav", "b.wav"], [True, True],
                moc_cu, "vi", "piper:x"))
            ok(ra == moc_cu,
               "3d cửa chung `_moc_giong_hang` thiếu đồ -> trả NGUYÊN mốc cũ "
               "(trả rỗng là chữ biến mất ở đúng mấy câu đó)")
        finally:
            os.environ.pop("BQ_GIONG_HANG_LIB", None)

    # ══════════════ CA 4 — MỐC VÔ LÝ PHẢI BỊ BỎ ═════════════════════════
    print("\nCA 4 — `_don_moc`: mốc vô lý không được chạy tiếp xuống phụ đề")
    ok(gh._don_moc([[0.0, 0.3, "a"], [0.3, 0.6, "b"]])
       == [[0.0, 0.3, "a"], [0.3, 0.6, "b"]],
       "4a mốc hợp lệ -> giữ nguyên")
    ok(gh._don_moc([[0.5, 0.8, "a"], [0.1, 0.3, "b"]]) == [],
       "4b mốc LÙI VỀ SAU -> bỏ CẢ CÂU (để lọt là chữ nhảy ngược, rc vẫn 0)")
    ok(gh._don_moc([[-0.9, 0.3, "a"]]) == [],
       "4c mốc ÂM -> bỏ (dấu hiệu tính sai tỉ lệ khung)")
    ok(gh._don_moc([[0.0, 0.3, "a"], "rác"]) == [[0.0, 0.3, "a"]],
       "4d phần tử rác -> bỏ phần tử đó, không nổ")

    # ══════════════ CA 5 — DẤU GẠCH NỐI (LỖI THẬT 18/08/2026) ═══════════
    print("\nCA 5 — dấu gạch nối KHÔNG được giết cả câu")
    # Đòi ĐÚNG DÒNG `return` của `ma_hoa` dùng bộ lọc, không chỉ đòi hằng
    # `BLANK` có mặt: phép phá chỉ trả riêng dòng `return` về bản cũ vẫn để
    # `BLANK = 0` nằm nguyên đó -> hỏi cho có thì mục này tự ĐẠT oan.
    ok("v == BLANK" in gh._MA_GIONG and "c not in BO" in gh._MA_GIONG,
       "5a `ma_hoa` LỌC token blank theo **ID** (lọc theo mặt chữ là bản "
       "torchaudio sau đổi ký tự blank thì hỏng lại)")
    # BỎ DÒNG GHI CHÚ TRƯỚC KHI DÒ. Bản đầu của mục này hỏi thẳng
    # `"blank=0" not in _MA_GIONG` và **ĐỎ OAN NGAY**: chính dòng ghi chú
    # giải thích bản vá có chuỗi `forced_align(blank=0)`. Đúng cái bẫy cổng
    # 47/51/53/54 đã ghi — và tôi vừa tự sập lại lần nữa.
    ma_chay = "\n".join(d.split("#")[0] for d in gh._MA_GIONG.splitlines())
    ok(ma_chay.count("blank=BLANK") == 2 and "blank=0" not in ma_chay,
       "5b cùng một hằng `BLANK` dùng cho CẢ `forced_align` lẫn `merge_tokens` "
       "(hai chỗ lệch nhau là lỗi im lặng)",
       f"{ma_chay.count('blank=BLANK')} chỗ")
    # TỰ KIỂM BỘ DÒ: dựng lại đúng dòng mã CŨ, bắt 5a phải trượt.
    ma_cu = gh._MA_GIONG.replace(
        "return [BANG[c] for c in r if c in BANG and c not in BO]",
        'return [BANG[c] for c in r if c in BANG and c != "*"]')
    ok("c not in BO" not in ma_cu and ma_cu != gh._MA_GIONG,
       "5c TỰ KIỂM: dựng lại mã CŨ thì chốt 5a mất -> cổng đang đo thật, "
       "không phải con dấu")

    if not gh.co_giong_hang():
        bo_qua("5d gióng hàng THẬT câu có `COVID-19`",
               "máy chưa có bộ gióng hàng (đúng cảnh máy nhân viên)")
    else:
        san = Path(tempfile.mkdtemp(prefix="bq_gh73_wav_"))
        try:
            CAU = ["Dịch COVID-19 đã làm thay đổi cả thế giới trong hai năm.",
                   "Hôm nay trời rất đẹp và mọi người đều vui vẻ."]
            p = [str(san / f"c{i}.wav") for i in range(len(CAU))]
            okd, _w = asyncio.run(dubbing._synth_all_words(
                CAU, "vi-VN-HoaiMyNeural", p, lang="vi", el_lui=False))
            if not all(okd):
                bo_qua("5d gióng hàng THẬT câu có `COVID-19`",
                       "edge-tts không đọc được (mạng) -> không có tiếng để "
                       "gióng")
            else:
                tin: dict = {}
                moc = gh.giong_hang_loat(p, CAU, "vi", thong_tin=tin)
                n_tu = [len(dubbing._tach_tu(c)) for c in CAU]
                ok(bool(moc[0]) and len(moc[0]) >= n_tu[0] - 1,
                   "5d câu có `COVID-19` VẪN RA MỐC (trước bản vá: RỖNG cả "
                   "câu vì '-' là token blank)",
                   f"{len(moc[0])}/{n_tu[0]} mốc")
                ok(bool(moc[1]),
                   "5e câu thường vẫn ra mốc (bản vá không phá ca đang tốt)",
                   f"{len(moc[1])}/{n_tu[1]} mốc")
                ok(all(moc[0][i][0] <= moc[0][i + 1][0]
                       for i in range(len(moc[0]) - 1)),
                   "5f mốc TĂNG DẦN theo thời gian")
                ok(set(tin) >= {"thiet_bi", "giay", "giay_align", "torch"},
                   "5g trả kèm cột thời gian TÁCH RIÊNG (phí nạp model là "
                   "HẰNG SỐ mỗi lượt — gộp vào là đo ra 'gióng hàng chậm')",
                   f"{tin.get('thiet_bi')} · {tin.get('giay_align')}s gióng "
                   f"/ {tin.get('giay')}s cả lượt")
        finally:
            shutil.rmtree(san, ignore_errors=True)

    # ══════════════ CA 6 — CỬA CHUNG + THỨ TỰ ƯU TIÊN MỐC ═══════════════
    print("\nCA 6 — cửa chung `_synth_all_words`: ai được lấy mốc gióng hàng")
    n = _ham(REPO / "app" / "core" / "dubbing.py", "_synth_all_words")
    goi = [x.func.id for x in ast.walk(n)
           if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)]
    # 2 -> 3 (v2.38.0): **CHATTERBOX VÀO ĐÚNG NHÓM NÀY**, không phải nới mốc
    # cho hết đỏ. Mệnh đề của mục là *"mọi máy đọc KHÔNG trả mốc thật đều phải
    # đi qua cửa chung"*, mà API công khai của Chatterbox trả đúng một khối
    # sóng âm — mốc chỉ moi được từ thuộc tính RIÊNG TƯ
    # `t3.patched_model.alignment_stream_analyzer` (bản sau đổi là gãy im
    # lặng). Nó cùng cảnh Piper/OmniVoice nên phải nằm trong con số này.
    # Vẫn giữ SỐ CỐ ĐỊNH chứ không đổi thành `>= 2`: nới thành bất đẳng thức là
    # mất luôn khả năng bắt "ai đó cho edge-tts/ElevenLabs đi qua đây" — đúng
    # cái mục 6b/6c đang canh.
    ok(goi.count("_moc_giong_hang") == 3,
       "6a `_synth_all_words` gọi `_moc_giong_hang` ĐÚNG 3 nhánh (giọng "
       "ngoài + Piper + Chatterbox) — đọc bằng AST, không tìm chuỗi "
       "(bài học 56d/64)",
       f"{goi.count('_moc_giong_hang')} chỗ")
    # edge-tts và ElevenLabs trả mốc THẬT -> KHÔNG được thay bằng mốc suy ra.
    # Đổi mốc của chúng là đụng phụ đề 200-300 kênh đang chạy sản xuất.
    # **BỎ DOCSTRING TRƯỚC KHI DÒ VỊ TRÍ**: `ast.unparse` giữ nguyên
    # docstring, mà docstring của hàm này có nhắc `WordBoundary` ngay dòng
    # đầu -> `find("WordBoundary")` trỏ vào phần GHI CHÚ chứ không phải phần
    # MÃ, và mục 6c đỏ oan (đúng họ bẫy 47/51/53/54, lần này ở dạng vị trí).
    than_n = ast.parse(ast.unparse(n)).body[0]
    if (than_n.body and isinstance(than_n.body[0], ast.Expr)
            and isinstance(than_n.body[0].value, ast.Constant)):
        than_n.body.pop(0)
    than = ast.unparse(than_n)
    vi_tri_el = than.find("_chay_eleven")
    vi_tri_gh = than.find("_moc_giong_hang")
    ok(0 <= vi_tri_el < vi_tri_gh,
       "6b nhánh ElevenLabs TRẢ THẲNG mốc API, nằm TRƯỚC mọi nhánh gióng "
       "hàng (mốc thật không được thay bằng mốc suy ra)")
    vi_tri_wb = than.find("WordBoundary")
    ok(vi_tri_wb > vi_tri_gh > 0
       and "_moc_giong_hang" not in than[vi_tri_wb:],
       "6c nhánh edge-tts (WordBoundary) nằm SAU CÙNG và KHÔNG đi qua gióng "
       "hàng — mốc `WordBoundary` là mốc THẬT của chính máy đọc")
    # `lay_moc` của giọng ngoài phải BÁM `co_giong_hang()`, KHÔNG ghi cứng:
    # ghi cứng `False` là máy chưa tải model ra KHÔNG MỘT MỐC NÀO (cổng 72
    # CA 2b đã bắt được lỗi này một lần).
    ok("lay_moc=not co_gh" in than or "lay_moc=(not co_gh)" in than,
       "6d giọng ngoài: `lay_moc` BÁM theo máy có gióng hàng hay không "
       "(ghi cứng là mất sạch mốc trên máy chưa tải model)")

    # ══════════════ CA 7 — NÚT TẢI: ĐỪNG LẶP LỖI `_lib` CỦA DEMUCS ══════
    print("\nCA 7 — `cai_giong_hang`: nút tải 1,2 GB")
    nc = _ham(NGUON, "cai_giong_hang")
    hs = [x.value for x in ast.walk(nc)
          if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    ok("--ignore-installed" in hs,
       "7a có `--ignore-installed` — thiếu là pip BỎ QUA gói máy đã có, thư "
       "mục đích rỗng, máy dev xanh máy anh Hùng đỏ (cổng 58)")
    ok("--no-deps" in hs,
       "7b có `--no-deps` cho torchaudio — không thì pip kéo THÊM một bản "
       "torch 2,5 GB vào thư mục gióng hàng")
    ok("--target" in hs and "--extra-index-url" in hs,
       "7c cài vào `--target` riêng + cùng chỉ mục torch đang có")
    goi_nc = [x.func.id for x in ast.walk(nc)
              if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)]
    ok("tinh_trang_giong_hang" in goi_nc,
       "7d HẬU KIỂM bằng đường dẫn, KHÔNG tin 'pip trả mã 0' (pip trả 0 mà "
       "thư mục vẫn thiếu là chuyện ĐÃ XẢY RA)")
    ok("lib_torch" in ast.unparse(nc) and "--target" in hs
       and "lib_torch()" not in ast.unparse(nc).split("--target")[1][:80],
       "7e KHÔNG ghi vào `_lib` của Demucs (một lượt pip vào đó có thể thay "
       "numpy/torch mà Demucs đang chạy sản xuất phụ thuộc)")
    # Chạy THẬT nhánh "thiếu torch" — KHÔNG gọi mạng, KHÔNG chạy pip.
    that = gh.lib_torch
    with tempfile.TemporaryDirectory(prefix="bq_gh73_") as tam:
        try:
            gh.lib_torch = lambda: tam
            r = gh.cai_giong_hang()
        finally:
            gh.lib_torch = that
    ok(r["ok"] is False and "tách giọng" in r["loi"],
       "7f thiếu torch -> KHÔNG tải gì, CHỈ ĐƯỜNG sang nút tách giọng "
       "(kéo bản torch thứ hai về là đúng cách phá Demucs)", r["loi"][:60])
    tt2 = gh.tinh_trang_giong_hang()
    ok(isinstance(tt2["cai_duoc"], bool)
       and (tt2["cai_duoc"] or tt2["vi_sao_khong_cai"]),
       "7g `cai_duoc` = False thì PHẢI nói vì sao (nút xám không lời giải "
       "thích chỉ là câu đố — cổng 58/16/51)",
       f"cai_duoc={tt2['cai_duoc']} · {tt2['vi_sao_khong_cai']!r}")

    print("\n" + "=" * 74)
    print(f"CỔNG 73: ĐẠT {DAT} · HỎNG {HONG}"
          + (f" · BỎ QUA {BO_QUA}" if BO_QUA else ""))
    for x in _BO:
        print(f"  (bỏ qua) {x}")
    print(f"  máy này: bộ gióng hàng {'CÓ' if gh.co_giong_hang() else 'CHƯA'}"
          f" · {gh.thu_muc_gh()}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
