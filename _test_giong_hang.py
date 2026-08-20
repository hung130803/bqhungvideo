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
import threading
import tokenize
from concurrent.futures import ThreadPoolExecutor
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
    # 3 -> 4 (v2.41.1): **KOKORO VÀO ĐÚNG NHÓM NÀY**, không phải nới mốc cho hết
    # đỏ. Chốt này nổ ĐÚNG khi Kokoro được nối vào combo, và đó là lý do nó tồn
    # tại — buộc có người đọc lại. Kiểm nhánh thứ 4 trước khi đổi số (AST trên
    # `_synth_all_words`): nó là `_moc_giong_hang(texts, paths, ok_k, [[] for _
    # in texts], lang, _ma_kk)`, tức **`kk:` = Kokoro**. Kokoro **KHÔNG tự trả
    # mốc từng chữ** (`giong_kokoro.doc_loat` chỉ trả True/False; `moc_thu` là
    # đường ĐO, không phải đường chạy) nên nó cùng cảnh Piper/OmniVoice/
    # Chatterbox và PHẢI nằm trong con số này. Tham số mốc là `[[] for _ in
    # texts]` = "không có mốc nào để giữ", đúng như Chatterbox.
    # Vẫn giữ SỐ CỐ ĐỊNH chứ không đổi thành `>= 3`: nới thành bất đẳng thức là
    # mất luôn khả năng bắt "ai đó cho edge-tts/ElevenLabs đi qua đây" — đúng
    # cái mục 6b/6c đang canh.
    ok(goi.count("_moc_giong_hang") == 4,
       "6a `_synth_all_words` gọi `_moc_giong_hang` ĐÚNG 4 nhánh (giọng "
       "ngoài + Piper + Chatterbox + Kokoro) — đọc bằng AST, không tìm chuỗi "
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

    # ══════════════ CA 8 — HAI LUỒNG KHÔNG ĐƯỢC DÙNG CHUNG FILE ═════════
    # LỖI THẬT 19/08/2026. `viec_<pid>.json` / `ket_<pid>.json` lấy
    # `os.getpid()` của tiến trình GỌI -> giống hệt nhau cho MỌI luồng trong
    # app, mà làn `LAN_TG` mặc định 2 luồng. Đo: chạy lần lượt 12/12 câu ra
    # mốc, chạy 2 luồng **6/12** — đúng một mẻ mất trắng, và `rc` vẫn 0 nên
    # không một dòng báo nào lên tới giao diện.
    print("\nCA 8 — 2 luồng gọi cùng lúc: file việc/kết quả phải RIÊNG")
    _ma = [gh._ma_lot() for _ in range(50)]
    _tu_luong: list[str] = []
    _kh = threading.Lock()

    def _sinh() -> None:
        for _ in range(25):
            v = gh._ma_lot()
            with _kh:
                _tu_luong.append(v)

    _ths = [threading.Thread(target=_sinh) for _ in range(8)]
    for _t in _ths:
        _t.start()
    for _t in _ths:
        _t.join()
    ok(len(set(_ma)) == len(_ma) and len(set(_tu_luong)) == len(_tu_luong),
       "8a `_ma_lot` DUY NHẤT mỗi lượt gọi, kể cả gọi từ 8 luồng cùng lúc",
       f"{len(set(_ma))}/{len(_ma)} + {len(set(_tu_luong))}/{len(_tu_luong)}")
    ok(all(x.startswith(f"p{os.getpid()}") for x in _ma),
       "8b mã lượt vẫn MỞ ĐẦU bằng pid — lượt dọn mồ côi phải phân biệt được "
       "'của tiến trình đang sống' với 'của lần chạy trước đã chết'", _ma[0])
    # Quét MÃ THẬT: thân `giong_hang_loat` phải GỌI `_ma_lot`, và KHÔNG được
    # còn `getpid` nào tự đặt tên file. (`ast.unparse` bỏ comment sẵn — bài
    # học 47/51/53/54, chính file này đã sập một lần ở CA 5b.)
    _than = ast.unparse(_ham(NGUON, "giong_hang_loat"))
    ok("_ma_lot()" in _than and "getpid" not in _than,
       "8c `giong_hang_loat` đặt tên qua `_ma_lot()`, KHÔNG tự gọi `getpid`")

    if not gh.co_giong_hang():
        bo_qua("8d 2 luồng gióng hàng THẬT cùng lúc",
               "máy chưa có bộ gióng hàng (đúng cảnh máy nhân viên)")
    else:
        san2 = Path(tempfile.mkdtemp(prefix="bq_gh73_ss_"))
        try:
            C1 = ["Anh ấy mở cánh cửa ra và bước vào trong căn phòng tối.",
                  "Cô gái nhìn quanh rồi bật đèn lên cho sáng cả gian nhà."]
            C2 = ["Hôm nay trời rất đẹp và mọi người đều vui vẻ đi chơi.",
                  "Chúng tôi quyết định ở nhà nấu ăn thay vì đi ra ngoài."]
            p1 = [str(san2 / f"a{i}.wav") for i in range(len(C1))]
            p2 = [str(san2 / f"b{i}.wav") for i in range(len(C2))]
            o1, _w1 = asyncio.run(dubbing._synth_all_words(
                C1, "vi-VN-HoaiMyNeural", p1, lang="vi", el_lui=False))
            o2, _w2 = asyncio.run(dubbing._synth_all_words(
                C2, "vi-VN-HoaiMyNeural", p2, lang="vi", el_lui=False))
            if not (all(o1) and all(o2)):
                bo_qua("8d 2 luồng gióng hàng THẬT cùng lúc",
                       "edge-tts không đọc được (mạng)")
            else:
                TONG = len(C1) + len(C2)

                def _ss() -> int:
                    """2 luồng cùng gọi -> TỔNG số câu ra được mốc."""
                    with ThreadPoolExecutor(max_workers=2) as ex:
                        fs = [ex.submit(gh.giong_hang_loat, w, t, "vi")
                              for w, t in ((p1, C1), (p2, C2))]
                        return sum(1 for f in fs for m in f.result() if m)

                n_ss = _ss()
                ok(n_ss == TONG,
                   "8d 2 luồng gọi CÙNG LÚC -> KHÔNG mẻ nào mất mốc",
                   f"{n_ss}/{TONG} câu có mốc")
                # THỬ PHÁ: dựng lại đúng hành vi bản CŨ (tên theo pid = HẰNG
                # SỐ cho mọi luồng). Không vỡ thì 8d chỉ là con dấu.
                _that_ml = gh._ma_lot
                try:
                    gh._ma_lot = lambda: f"p{os.getpid()}"   # type: ignore
                    n_pha = _ss()
                finally:
                    gh._ma_lot = _that_ml                    # type: ignore
                ok(n_pha < TONG,
                   "8e THỬ PHÁ: trả tên file về kiểu CŨ (chỉ theo pid) thì "
                   "bất biến 8d PHẢI VỠ -> 8d đang đo thật, không phải con dấu",
                   f"{n_pha}/{TONG} câu có mốc")
        finally:
            shutil.rmtree(san2, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════════
    # CA 9 — MÁY DEV VÀ MÁY THẬT PHẢI NÓI CÙNG MỘT CÂU
    # ══════════════════════════════════════════════════════════════════
    # LỖI THẬT (v2.39.0, 19/08/2026): anh Hùng bấm nút tải -> `OSError: Could
    # not load this library: ...libtorchaudio.pyd`, trong khi máy dev chạy
    # gióng hàng bình thường. Đo ra KHÔNG phải "thiếu torch" (torch CÓ trong
    # `_lib`) mà là **LỆCH CÂY BẢN DỰNG**: torchaudio `+cu126` cần
    # `torch_cuda.dll` + `cudart64_12.dll`, mà torch `+cpu` không ship hai DLL
    # đó (bóc bảng nhập DLL của chính `.pyd`: cây `+cpu` 9 DLL · cây `+cu126`
    # 36 DLL).
    #
    # ĐÂY LÀ CA ĐỘC NHẤT VÌ HAI PHÉP DÒ CŨ ĐỀU MÙ VỚI NÓ:
    #   · `_co_goi` hỏi "có thư mục không" -> CÓ (thư mục đúng chỗ, .pyd đủ
    #     byte) -> báo *đã cài* cho một bộ không bao giờ nạp được;
    #   · "import được không" thì máy dev mượn `.venv` rồi trả lời CÓ.
    # Nên mệnh đề phải là: **danh sách THIẾU máy dev nói ra == danh sách mà
    # tiến trình KHÔNG có site-packages nói ra**, và cả hai phải NÊU ĐÍCH DANH
    # chỗ lệch cây.
    print("\nCA 9 — máy dev và bản .exe phải nói CÙNG một danh sách thiếu")
    san9 = Path(tempfile.mkdtemp(prefix="bq_gh9_"))
    # HAI BIẾN MÔI TRƯỜNG NÀY LÀ TRẠNG THÁI DÙNG CHUNG — phải TRẢ LẠI.
    # Bản đầu của CA 9 đặt chúng trỏ vào hộp cát rồi bỏ đó: mục 9j sau đó đo
    # `duong_model()` ra file model.pt GIẢ 1 byte của hộp cát (báo "2,6 MB")
    # và dòng tổng kết in "bộ gióng hàng CHƯA" cho một máy đang CÓ. Đúng luật
    # "test không được làm bẩn trạng thái dùng chung".
    _env9_cu = {k: os.environ.get(k)
                for k in ("BQ_GIONG_HANG_LIB", "BQ_DEMUCS_LIB")}
    try:
        # Hộp cát dựng ĐÚNG trạng thái máy anh Hùng SAU khi tải model xong:
        # torch +cpu · torchaudio +cu126 · uroman · model.pt có mặt. Đây là
        # trạng thái mà bản CŨ gọi là "đã cài đủ".
        LIB9, GH9 = san9 / "_lib", san9 / "_gh"
        (LIB9 / "torch").mkdir(parents=True)
        (LIB9 / "torch" / "version.py").write_text(
            "__version__ = '2.13.0+cpu'\n", encoding="utf-8")
        (GH9 / "torchaudio").mkdir(parents=True)
        (GH9 / "torchaudio" / "version.py").write_text(
            "__version__ = '2.11.0+cu126'\n", encoding="utf-8")
        (GH9 / "uroman").mkdir(parents=True)
        mp = GH9 / "_models" / "hub" / "checkpoints"
        mp.mkdir(parents=True)
        (mp / "model.pt").write_bytes(b"0")      # chỉ cần CÓ FILE
        env9 = {**os.environ, "BQ_GIONG_HANG_LIB": str(GH9),
                "BQ_DEMUCS_LIB": str(LIB9), "PYTHONUTF8": "1"}

        def _thieu_trong_tien_trinh(cat_sp: bool, nguon: str = "") -> dict:
            """`tinh_trang_giong_hang()` chạy ở TIẾN TRÌNH RIÊNG.

            `cat_sp=True` = giả lập bản `.exe`. **Import `app` XONG RỒI MỚI
            cắt `site-packages`** — mẫu đúng ở cổng 58 CA 1a; cắt trước thì
            chính `import config` chết và cổng đo nhầm thứ khác.
            `nguon` != '' = nạp mã bản MỐC từ file đó (dùng cho phép thử phá).
            """
            import json as _js
            import subprocess as _sp
            ma = (
                "import json,sys\n"
                + (f"import importlib.util as _iu\n"
                   f"_sp2=_iu.spec_from_file_location('_gh_moc', r'{nguon}')\n"
                   "_m=_iu.module_from_spec(_sp2)\n"
                   if nguon else
                   "from app.core import giong_hang as _m\n")
                + "import app.core.thay_giong as _tg\n"
                + ("sys.path[:] = [p for p in sys.path if 'site-packages' "
                   "not in p.replace(chr(92),'/').lower()]\n" if cat_sp else "")
                + ("_sp2.loader.exec_module(_m)\n" if nguon else "")
                + "t=_m.tinh_trang_giong_hang()\n"
                + "sys.stdout.write('BQ9'+json.dumps("
                  "{'co':t['co'],'thieu':t['thieu']},ensure_ascii=False))\n")
            r = _sp.run([sys.executable, "-c", ma], capture_output=True,
                        text=True, encoding="utf-8", errors="replace",
                        env=env9, cwd=str(REPO), timeout=300)
            s = r.stdout or ""
            i = s.find("BQ9")
            if i < 0:
                return {"loi": ((r.stderr or s) or "")[-300:]}
            return _js.loads(s[i + 3:])

        dev9 = _thieu_trong_tien_trinh(False)
        exe9 = _thieu_trong_tien_trinh(True)
        ok(dev9.get("thieu") == exe9.get("thieu")
           and "loi" not in dev9 and "loi" not in exe9,
           "9a danh sách THIẾU của máy dev GIỐNG HỆT của tiến trình KHÔNG có "
           "site-packages (mệnh đề trung tâm)",
           f"dev={dev9.get('thieu')} · .exe={exe9.get('thieu')}")
        ok(dev9.get("co") is False
           and any("cùng cây" in x for x in (dev9.get("thieu") or [])),
           "9b LỆCH CÂY BẢN DỰNG bị bắt và NÊU ĐÍCH DANH (đồ có đủ mà vẫn "
           "không nạp được -> phải tính là THIẾU, không được `co=True`)",
           f"co={dev9.get('co')} · {dev9.get('thieu')}")

        # ── THỬ PHÁ: chạy lại CHÍNH mã bản MỐC trên CÙNG hộp cát ────────────
        # `v2.39.0` = bản phát hành NGAY TRƯỚC bản vá (mốc đúng theo luật đã
        # chốt ở cổng 56; KHÔNG dùng `main`/`HEAD` — sau khi gộp thì mốc chính
        # là bản đang test và cổng tự PASS OAN vĩnh viễn).
        MOC = (os.environ.get("BQ_MOC_GH") or "v2.39.0").strip()
        import subprocess as _sp
        _g = _sp.run(["git", "show", f"{MOC}:app/core/giong_hang.py"],
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace", cwd=str(REPO), timeout=120)
        if _g.returncode != 0 or not (_g.stdout or "").strip():
            bo_qua("9c THỬ PHÁ mã bản mốc " + MOC,
                   "không đọc được mốc: " + (_g.stderr or "")[-120:])
        elif (_g.stdout or "").replace("\r\n", "\n") == \
                NGUON.read_text(encoding="utf-8").replace("\r\n", "\n"):
            # Chốt chống PASS OAN: mốc TRÙNG bản đang test = so nó với chính
            # nó, phép thử phá mất hết ý nghĩa.
            ok(False, "9c mốc " + MOC + " TRÙNG bản đang test -> phép thử phá "
               "vô nghĩa, chọn mốc là bản phát hành TRƯỚC bản vá", "")
        else:
            f_moc = san9 / "_gh_moc.py"
            f_moc.write_text(_g.stdout, encoding="utf-8")
            cu_dev = _thieu_trong_tien_trinh(False, str(f_moc))
            cu_exe = _thieu_trong_tien_trinh(True, str(f_moc))
            ok(cu_dev.get("co") is True and not cu_dev.get("thieu"),
               "9c THỬ PHÁ: mã bản mốc " + MOC + " trên CÙNG hộp cát báo "
               "`co=True · thiếu=[]` cho bộ KHÔNG BAO GIỜ NẠP ĐƯỢC "
               "-> 9a/9b đang đo thật, không phải con dấu",
               f"co={cu_dev.get('co')} · thiếu={cu_dev.get('thieu')}")
            ok(cu_dev.get("thieu") == cu_exe.get("thieu"),
               "9d mã bản mốc cũng nói GIỐNG NHAU ở hai môi trường -> bệnh "
               "KHÔNG phải 'dev mượn .venv' mà là PHÉP DÒ MÙ VỚI LỆCH CÂY "
               "(đọc cho đúng bệnh, đừng đổ cho cổng 58)",
               f"dev={cu_dev.get('thieu')} · .exe={cu_exe.get('thieu')}")

        # ── 9e: chọn chỉ mục theo TORCH, KHÔNG theo CARD ─────────────────────
        # Đây đúng chỗ hỏng: máy có RTX 3060 nên bản cũ lấy `+cu126` trong khi
        # `_lib` là `+cpu`. Vá xong thì CARD không được có tiếng nói nào.
        from app.core import thay_giong as _tg9
        _that_gpu = _tg9.co_gpu_nvidia
        try:
            _tg9.co_gpu_nvidia = lambda: True                # type: ignore
            os.environ["BQ_DEMUCS_LIB"] = str(LIB9)
            os.environ["BQ_GIONG_HANG_LIB"] = str(GH9)
            url9, the9 = gh.chi_muc_cho_torchaudio()
            ok(the9 == "cpu" and url9 and url9.endswith("/cpu"),
               "9e torch `+cpu` + máy CÓ GPU -> vẫn phải lấy torchaudio cây "
               "`+cpu` (chỉ mục đi theo TORCH ĐANG CÓ, không theo CARD)",
               f"{the9} · {url9}")
            (LIB9 / "torch" / "version.py").write_text(
                "__version__ = '2.13.0+cu126'\n", encoding="utf-8")
            _tg9.co_gpu_nvidia = lambda: False               # type: ignore
            url9b, the9b = gh.chi_muc_cho_torchaudio()
            ok(the9b == "cu126" and url9b and url9b.endswith("/cu126"),
               "9f torch `+cu126` + `nvidia-smi` KHÔNG trả gì -> vẫn lấy cây "
               "`+cu126` cho khớp torch (chiều ngược lại)",
               f"{the9b} · {url9b}")
        finally:
            _tg9.co_gpu_nvidia = _that_gpu                   # type: ignore

        # ── 9g/9h: quét AST (KHÔNG quét chuỗi — chính ghi chú của bản vá có
        # chữ `co_gpu_nvidia`, quét chuỗi là ĐỎ OAN, bài học 47/51/53/73) ────
        nc9 = _ham(NGUON, "cai_giong_hang")
        goi9 = {n.func.id for n in ast.walk(nc9)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        goi9 |= {n.func.attr for n in ast.walk(nc9)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        ok("chi_muc_cho_torchaudio" in goi9 and "co_gpu_nvidia" not in goi9,
           "9g `cai_giong_hang` gọi `chi_muc_cho_torchaudio` và KHÔNG còn gọi "
           "`co_gpu_nvidia` (đúng chỗ đã hỏng)",
           f"chi_muc_cho_torchaudio={'chi_muc_cho_torchaudio' in goi9} · "
           f"co_gpu_nvidia={'co_gpu_nvidia' in goi9}")
        ok("do_goi_gh" in goi9,
           "9h hậu kiểm phải qua `do_goi_gh` (so `spec.origin` VỚI THƯ MỤC "
           "ĐÍCH ở tiến trình đã cắt site-packages), không hỏi 'import được "
           "không'")
        ok("site-packages" in gh._MA_KIEM_GH
           and "find_spec" in gh._MA_KIEM_GH,
           "9i mã hậu kiểm THẬT SỰ cắt site-packages và hỏi `spec.origin`")

    finally:
        for _k, _v in _env9_cu.items():
            if _v is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _v
        shutil.rmtree(san9, ignore_errors=True)

    # ── 9j/9k: nhãn phải khớp lượng tải THẬT ────────────────────────────────
    # ĐẶT NGOÀI khối hộp cát, SAU khi đã trả lại biến môi trường — nếu không
    # thì `duong_model()` trỏ vào model.pt GIẢ 1 byte của hộp cát.
    # Đo `_do_gh_tai_ve.py` (pip --dry-run --report + HTTP HEAD, Python 3.14):
    # torchaudio 0,3 MB (+cu126 1,4) · uroman 0,9 · regex 0,3 · model
    # 1.203,6 MB -> TỔNG ~1.206 MB = 1,18 GiB ~ 1,2 GB. Đúng vì KHÔNG kèm
    # torch; ai đổi sang tự cài torch thì wheel `+cu126` một mình đã 2.474,4 MB
    # và nhãn này thành sai gấp hơn 2 lần.
    mp_that = Path(gh.duong_model())
    if not mp_that.is_file():
        bo_qua("9j nhãn nút khớp lượng tải thật",
               "máy chưa có model.pt để đo (không chấm khống)")
    else:
        tong_mb = mp_that.stat().st_size / 1024 / 1024 + 1.4 + 0.9 + 0.3
        so = f"{tong_mb:.1f}".replace(".", ",")     # chỉ đổi dấu của SỐ
        ok("1,2 GB" in gh.NHAN_TAI_GH and 1150 <= tong_mb <= 1300,
           "9j nhãn ghi ĐÚNG số GB tải về (model + torchaudio + uroman, "
           "KHÔNG kèm torch)",
           f"nhãn «{gh.NHAN_TAI_GH}» · đo thật {so} MB")
    ok("torch" not in gh.GOI_KHONG_DEPS + gh.GOI_CO_DEPS,
       "9k danh sách gói tải KHÔNG có torch (dùng chung `_lib`) — ngày nào "
       "thêm torch vào đây thì nhãn 1,2 GB thành sai",
       f"{gh.GOI_KHONG_DEPS + gh.GOI_CO_DEPS}")

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
