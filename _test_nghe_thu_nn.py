# -*- coding: utf-8 -*-
"""CỔNG 81 — NGHE THỬ PHẢI ĐỌC ĐÚNG NGÔN NGỮ, VÀ BÁO KHI GIỌNG KHÔNG ĐỌC ĐƯỢC.

Anh Hùng 19/08/2026: *"cái phần nghe thử chọn tiếng Anh ngôn ngữ đó cứ ra tiếng
Việt lung ta lung tung"*.

**GỐC:** `thay_giong.doc_thu` dùng **một câu tiếng Việt CỐ ĐỊNH**
(`CAU_NGHE_THU`) cho MỌI giọng. Chọn giọng tiếng Anh -> nghe giọng Anh cố đọc
chữ Việt = ra tiếng lạ, mà người nghe lại kết luận **"giọng này hỏng"**. Cửa
nghe thử CŨ (`dubbing.synth_demo`, hộp Lồng tiếng) đã chọn câu theo ngôn ngữ
của giọng từ lâu — **chỉ đường Thay giọng bị sót**, nên đây là lỗi SÓT CHỖ NỐI,
không phải thiếu ý tưởng.

Số cổng là **81**: 80 đã là `_test_khong_xoa_nham.py`. Trùng số thì hai cổng
ghi đè file kết quả của nhau (bài học cổng 70 vs 69).

═══════════════════════════════════════════════════════════════════════════
CỔNG NÀY TỰ KIỂM — GỠ CHỐT RA PHẢI ĐỎ
═══════════════════════════════════════════════════════════════════════════
CA 7 vá `thay_giong.cau_nghe_thu` trả về **đúng hành vi bản CŨ** (luôn câu
tiếng Việt) rồi đòi mệnh đề trung tâm của CA 3 phải VỠ. Không có mục đó thì
CA 3 chỉ là con dấu: nó vẫn xanh với một hàm chọn câu hỏng.

═══════════════════════════════════════════════════════════════════════════
KHÔNG ĐỐT HẠN MỨC ElevenLabs — 0 KÝ TỰ
═══════════════════════════════════════════════════════════════════════════
Nhánh `el:`/`gemini:` của `doc_thu` đi qua `dubbing.synth_demo`. Cổng **vá
`synth_demo` thành hàm sinh mp3 bằng ffmpeg** (đúng khuôn cổng 67 đã vá
`_eleven_tts`) nên chạy trong hồi quy tốn **0 ký tự** của 5 tài khoản free.
Có mục chốt "bản vá ĂN được" — vá mà cửa rẽ không đi qua đó thì ca `el:` tự
ĐẠT vì lý do NGƯỢC HẲN (bẫy đã sập ở cổng 67).

Cổng KHÔNG phát tiếng ra loa: `doc_thu` chỉ SINH file, phần phát nằm ở hộp
thoại (cổng 65 canh, có vá `winsound`).
"""
from __future__ import annotations

import ast
import hashlib
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# HỘP CÁT: đặt TRƯỚC khi nạp config, không thì ghi vào DATA_DIR THẬT của app.
_SB = tempfile.mkdtemp(prefix="bq_nnthu_")
os.environ["BQ_DATA_DIR"] = _SB
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401  (bắt buộc: cấm mở Explorer/trình phát)

DAT = 0
HONG = 0


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))


def _don() -> None:
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)


import atexit  # noqa: E402

atexit.register(_don)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _ma_that(src: str) -> str:
    """Chỉ phần **MÃ CHẠY ĐƯỢC** — bỏ COMMENT và mọi CHUỖI.

    Chép đúng cách `_test_hook_to_mo._ma_that` làm (bài học cổng 47/51/53/73):
    lọc bằng `startswith('#')` thì ghi chú thụt lề, ghi chú đuôi dòng và
    docstring đều lọt, nên chính câu ghi chú nhắc tên một giọng bị kể là "ghi
    cứng tên giọng" -> mục ĐỎ OAN vĩnh viễn.
    """
    import io
    import tokenize
    ra = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src              # không phân tích được -> đừng phát chứng nhận
    return " ".join(ra)


# ==================================================================
def ca1_bang_cau() -> None:
    """Có câu mẫu cho ĐỦ mọi ngôn ngữ đích, và không tiếng nào lùi câu Anh."""
    print("\n== CA 1: bảng câu mẫu phủ đủ ngôn ngữ đích ==")
    from app.core import dubbing
    from app.core import thay_giong as TG

    ma_ds = [m for _n, m in TG.NGON_NGU_DICH]
    thieu = [m for m in ma_ds if not TG.cau_nghe_thu(m)]
    ok(not thieu, f"đủ câu cho {len(ma_ds)}/{len(ma_ds)} ngôn ngữ đích",
       f"thiếu: {thieu}" if thieu else ", ".join(ma_ds))

    # LÙI VỀ CÂU TIẾNG ANH LÀ BỆNH, KHÔNG PHẢI GIẢI PHÁP: nó làm phép nghe thử
    # "vẫn chạy" trong khi chứng nhận sai thứ (bài học `_cau_doc_thu.py`).
    cau_en = TG.cau_nghe_thu("en")
    trung = [m for m in ma_ds if m != "en" and TG.cau_nghe_thu(m) == cau_en]
    ok(not trung, "không ngôn ngữ nào bị lùi về câu TIẾNG ANH",
       f"lùi: {trung}" if trung else "0")

    rieng = {TG.cau_nghe_thu(m) for m in ma_ds}
    ok(len(rieng) == len(ma_ds), "mỗi ngôn ngữ một câu RIÊNG",
       f"{len(rieng)} câu / {len(ma_ds)} ngôn ngữ")
    ok(TG.cau_nghe_thu("") == "", "ngôn ngữ rỗng -> trả RỖNG (không đoán bừa)")
    ok(TG.cau_nghe_thu("xx") == "", "ngôn ngữ lạ -> trả RỖNG")

    # NGUỒN DUY NHẤT: câu (trừ tiếng Việt) phải LẤY TỪ `dubbing._DEMO_TEXTS`.
    # Hai bảng câu mẫu là hai chỗ để lệch nhau rồi hai hộp nghe thử đọc hai
    # câu khác nhau mà không ai biết vì sao.
    lech = [m for m in ma_ds if m != "vi"
            and TG.cau_nghe_thu(m) != dubbing._DEMO_TEXTS.get(m)]  # noqa: SLF001
    ok(not lech, "câu lấy THẲNG từ `dubbing._DEMO_TEXTS` (nguồn duy nhất)",
       f"lệch: {lech}" if lech else "khớp từng ký tự")
    ok(TG.cau_nghe_thu("vi") == TG.CAU_NGHE_THU,
       "tiếng Việt vẫn là câu quen của anh Hùng (đủ 6 dấu thanh)")


def ca2_nn_giong() -> None:
    """`nn_cua_giong` phải đúng cho MỌI họ giọng có trong combo."""
    print("\n== CA 2: suy ngôn ngữ TỪ GIỌNG ==")
    from app.core import thay_giong as TG

    CA = [
        ("en-US-AriaNeural", "en", "edge-tts giọng Anh"),
        ("vi-VN-HoaiMyNeural", "vi", "edge-tts giọng Việt"),
        ("ko-KR-SunHiNeural", "ko", "edge-tts giọng Hàn"),
        ("vi-VN-NamMinhNeural|-20Hz", "vi", "biến thể cao độ vẫn ra `vi`"),
        ("vn:Adam", "en", "VieNeu Adam là giọng TIẾNG ANH"),
        ("vn:Ngọc Huyền", "vi", "VieNeu giọng Việt"),
        ("vnb:D:/mau.wav", "vi", "VieNeu nhân bản (model Việt)"),
        ("piper:vi_VN-vais1000-medium", "vi", "Piper vais1000"),
        ("vbee:hn_female_ngochuyen", "vi", "Vbee"),
        ("el:21m00Tcm4TlvDq8ikWAM", "", "ElevenLabs đa ngữ -> KHÔNG kết luận"),
        ("gemini:Kore", "", "Gemini đa ngữ -> KHÔNG kết luận"),
        ("ov:x", "", "OmniVoice đa ngữ -> KHÔNG kết luận"),
        ("cb:y", "", "Chatterbox đa ngữ -> KHÔNG kết luận"),
        ("", "", "giọng rỗng"),
    ]
    for ma, cho, mo in CA:
        ra = TG.nn_cua_giong(ma)
        ok(ra == cho, f"{mo}", f"{ma!r} -> {ra!r} (chờ {cho!r})")

    # `Adam` KHÔNG được ghi cứng ở `thay_giong.py`: nguồn duy nhất là bảng
    # `giong_vieneu.GIONG_TIENG_ANH`, thêm giọng Anh thứ hai vào bộ là chỗ
    # này phải tự đúng theo.
    # QUÉT BẰNG `tokenize`, KHÔNG QUÉT CHUỖI: chính DÒNG GHI CHÚ giải thích
    # bản vá có chữ `vn:Adam`, nên hỏi `"Adam" in src` là mục này ĐỎ OAN ngay
    # (bài học cổng 47/51/53/73 — và bản đầu của cổng này đã sập đúng vậy).
    src = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")
    than = src[src.index("def nn_cua_giong"):]
    than = than[:than.index("\ndef ")]
    ma = _ma_that(than)
    ok("GIONG_TIENG_ANH" in ma and "Adam" not in ma,
       "không ghi cứng tên giọng — đọc bảng `GIONG_TIENG_ANH`",
       f"mã thật {len(ma)} ký tự")
    # TỰ KIỂM BỘ DÒ: bộ lọc phải THẬT SỰ bỏ ghi chú, không thì mục trên tự ĐẠT.
    ok("Adam" in than and "Adam" not in ma,
       "bộ dò bỏ đúng phần GHI CHÚ (tự kiểm)")


def ca3_doc_that() -> bool:
    """MỆNH ĐỀ TRUNG TÂM: giọng nào thì câu tiếng đó, ĐỌC THẬT ra file."""
    print("\n== CA 3: đọc THẬT — giọng Anh ra câu Anh, giọng Việt ra câu Việt ==")
    from app.core import thay_giong as TG

    tot = True
    for ma, nn_cho, mo in (("en-US-AriaNeural", "en", "giọng ANH"),
                           ("vi-VN-HoaiMyNeural", "vi", "giọng VIỆT")):
        p = Path(_SB) / f"ca3_{nn_cho}.wav"
        kq = TG.doc_thu(ma, p, dung_cache=False)
        dung_cau = kq.get("cau") == TG.cau_nghe_thu(nn_cho)
        ok(dung_cau, f"{mo} (KHÔNG truyền ngôn ngữ đích): câu đúng tiếng "
                     f"«{nn_cho}»", str(kq.get("cau"))[:56])
        ok(kq.get("nn") == nn_cho, f"{mo}: khoá `nn` báo đúng",
           repr(kq.get("nn")))
        ok(bool(kq.get("ra")) and p.exists() and p.stat().st_size > 1024,
           f"{mo}: ra file tiếng THẬT",
           f"{p.stat().st_size if p.exists() else 0} byte · lỗi="
           f"{str(kq.get('loi'))[:40]}")
        ok(not kq.get("canh_bao"), f"{mo}: KHÔNG cảnh báo oan",
           str(kq.get("canh_bao"))[:60])
        tot = tot and dung_cau
    return tot


def ca4_bao_khi_lech() -> None:
    """Giọng không đọc được tiếng đó -> BÁO, mà vẫn ĐỌC (không chặn)."""
    print("\n== CA 4: giọng đọc tiếng A, đích tiếng B -> phải BÁO ==")
    from app.core import thay_giong as TG

    CA = [("vi-VN-HoaiMyNeural", "en", "vi", "giọng VIỆT + đích ANH"),
          ("en-US-AriaNeural", "vi", "en", "giọng ANH + đích VIỆT")]
    for ma, nn, nn_giong, mo in CA:
        p = Path(_SB) / f"ca4_{ma[:5]}_{nn}.wav"
        kq = TG.doc_thu(ma, p, nn=nn, dung_cache=False)
        cb = str(kq.get("canh_bao") or "")
        ok(bool(cb), f"{mo}: CÓ cảnh báo", cb[:70])
        # Nói ĐỦ HAI VẾ + nói rõ "không phải giọng hỏng" — đó chính là điều
        # anh Hùng kết luận sai khi nghe tiếng lạ.
        ok(f"«{nn_giong}»" in cb and f"«{nn}»" in cb,
           f"{mo}: cảnh báo nói CẢ HAI tiếng", f"có «{nn_giong}» và «{nn}»")
        ok("KHÔNG phải giọng hỏng" in cb,
           f"{mo}: nói thẳng KHÔNG phải giọng hỏng")
        ok(kq.get("cau") == TG.cau_nghe_thu(nn),
           f"{mo}: câu theo NGÔN NGỮ ĐÍCH (đúng thứ lượt xuất sẽ đọc)")
        ok(bool(kq.get("ra")) and Path(p).exists(),
           f"{mo}: VẪN đọc, không chặn", f"lỗi={str(kq.get('loi'))[:40]}")


def ca5_da_ngu_va_cache() -> None:
    """Giọng đa ngữ: KHÔNG cảnh báo oan · cache phải theo CÂU."""
    print("\n== CA 5: giọng đa ngữ (0 ký tự ElevenLabs) + cache theo câu ==")
    from app.core import dubbing
    from app.core import thay_giong as TG

    # ---- vá `synth_demo` -> sinh mp3 bằng ffmpeg: 0 ký tự ElevenLabs
    dem = {"n": 0}
    that = dubbing.synth_demo

    def gia(voice, out_mp3, text=None, rate="+0%", pitch="+0Hz",
            emotion=False):
        dem["n"] += 1
        import subprocess
        from config import settings
        subprocess.run(
            [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2",
             "-ac", "1", "-ar", "24000", str(out_mp3)],
            capture_output=True, timeout=120)
        return Path(out_mp3).exists()

    dubbing.synth_demo = gia
    try:
        p = Path(_SB) / "ca5_el.wav"
        kq = TG.doc_thu("el:21m00Tcm4TlvDq8ikWAM", p, nn="ja",
                        dung_cache=False)
        ok(dem["n"] >= 1, "bản vá `synth_demo` ĂN ĐƯỢC (nếu không thì ca này "
                          "tự ĐẠT vì lý do ngược hẳn)", f"{dem['n']} lượt")
        ok(kq.get("cau") == TG.cau_nghe_thu("ja"),
           "giọng đa ngữ + đích Nhật -> câu TIẾNG NHẬT")
        ok(not kq.get("canh_bao"),
           "giọng đa ngữ -> KHÔNG cảnh báo oan", str(kq.get("canh_bao"))[:50])
    finally:
        dubbing.synth_demo = that

    # ---- CACHE THEO CÂU: đổi ngôn ngữ phải ra file KHÁC
    v = "en-US-AndrewMultilingualNeural"
    p1 = Path(_SB) / "ca5_en.wav"
    p2 = Path(_SB) / "ca5_vi.wav"
    k1 = TG.doc_thu(v, p1, nn="en")
    k2 = TG.doc_thu(v, p2, nn="vi")
    co_ca_hai = bool(k1.get("ra")) and bool(k2.get("ra"))
    ok(co_ca_hai, "đọc được cả hai ngôn ngữ bằng cùng một giọng",
       f"lỗi1={str(k1.get('loi'))[:30]} lỗi2={str(k2.get('loi'))[:30]}")
    if co_ca_hai:
        ok(_md5(p1) != _md5(p2),
           "đổi ngôn ngữ -> FILE KHÁC (cache không trả tiếng cũ)",
           f"{_md5(p1)[:8]} vs {_md5(p2)[:8]}")
    p3 = Path(_SB) / "ca5_en_lan2.wav"
    k3 = TG.doc_thu(v, p3, nn="en")
    ok(bool(k3.get("cache")), "bấm lại đúng cấu hình -> DÙNG CACHE",
       f"cache={k3.get('cache')}")


def ca6_quet_tinh() -> None:
    """Quét bằng AST (không quét chuỗi — chính ghi chú cũng khớp chuỗi)."""
    print("\n== CA 6: quét tĩnh (AST) ==")
    src = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = {n.name: n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef)}
    ok("doc_thu" in ham and "cau_nghe_thu" in ham and "nn_cua_giong" in ham,
       "có đủ 3 hàm")
    dt = ham.get("doc_thu")
    goi = {n.func.id for n in ast.walk(dt) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Name)} if dt else set()
    ok("cau_nghe_thu" in goi,
       "`doc_thu` THẬT SỰ gọi `cau_nghe_thu` (không tự chọn câu)",
       ", ".join(sorted(goi))[:90])
    ok("nn_cua_giong" in goi, "`doc_thu` THẬT SỰ gọi `nn_cua_giong`")

    # `dich_sang` phải là BIỂU THỨC, không được là hằng số: hằng `"en"` chính
    # là bản cũ — nghe thử câu Việt mà giọng hỏng thì LÙI sang giọng tiếng Anh
    # đọc chữ Việt. Đòi "có mặt tham số" thôi là phép phá giữ nguyên mặt chữ
    # mà đổi ý nghĩa vẫn lọt (bài học cổng 56d).
    hs = None
    for n in ast.walk(dt) if dt else []:
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "doc_ban_dich"):
            hs = [k for k in n.keywords if k.arg == "dich_sang"]
    ok(bool(hs), "`doc_thu` truyền `dich_sang` cho `doc_ban_dich`")
    ok(bool(hs) and not isinstance(hs[0].value, ast.Constant),
       "`dich_sang` là BIỂU THỨC, không phải hằng số ghi cứng",
       type(hs[0].value).__name__ if hs else "—")

    # `_synth_all_words` vẫn ĐÚNG 3 chỗ gọi trong `thay_giong.py` (cổng 63) —
    # nghe thử phải đi qua cửa CẤP TRÊN, không đẻ chỗ gọi thứ 4.
    n4 = sum(1 for n in ast.walk(cay) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_synth_all_words")
    ok(n4 == 3, "vẫn ĐÚNG 3 chỗ gọi `_synth_all_words` (cổng 63 không đỏ)",
       str(n4))


def ca7_tu_kiem(ca3_that: bool) -> None:
    """GỠ CHỐT PHẢI ĐỎ — trả `cau_nghe_thu` về hành vi bản CŨ."""
    print("\n== CA 7: TỰ KIỂM — dựng lại bản CŨ thì CA 3 phải VỠ ==")
    from app.core import thay_giong as TG

    ok(ca3_that, "CA 3 đang ĐẠT trên bản đang test (điều kiện của phép thử)")
    that = TG.cau_nghe_thu
    TG.cau_nghe_thu = lambda nn="": TG.CAU_NGHE_THU   # bản CŨ: luôn câu Việt
    try:
        p = Path(_SB) / "ca7.wav"
        kq = TG.doc_thu("en-US-AriaNeural", p, dung_cache=False)
        vo = kq.get("cau") != that("en")
        ok(vo, "bản CŨ -> giọng ANH nhận câu TIẾNG VIỆT = mệnh đề CA 3 VỠ",
           str(kq.get("cau"))[:56])
    finally:
        TG.cau_nghe_thu = that

    # Chốt thứ hai: thiếu một ngôn ngữ trong bảng thì CA 1 phải kêu.
    from app.core import dubbing
    giu = dubbing._DEMO_TEXTS.pop("ko", None)               # noqa: SLF001
    try:
        ok(not TG.cau_nghe_thu("ko"),
           "bỏ tiếng Hàn khỏi bảng -> `cau_nghe_thu` trả RỖNG (CA 1 sẽ đỏ)")
    finally:
        if giu is not None:
            dubbing._DEMO_TEXTS["ko"] = giu                 # noqa: SLF001


def main() -> int:
    print("=" * 74)
    print("CỔNG 81 — NGHE THỬ ĐỌC ĐÚNG NGÔN NGỮ + BÁO KHI GIỌNG KHÔNG ĐỌC ĐƯỢC")
    print("=" * 74)
    ca1_bang_cau()
    ca2_nn_giong()
    ca3 = ca3_doc_that()
    ca4_bao_khi_lech()
    ca5_da_ngu_va_cache()
    ca6_quet_tinh()
    ca7_tu_kiem(ca3)
    print("\n" + "=" * 74)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
