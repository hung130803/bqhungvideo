# -*- coding: utf-8 -*-
"""CỔNG 72 — GIỌNG NGOÀI (OmniVoice / IndexTTS) TRONG HỘP THAY GIỌNG.

Anh Hùng 18/08/2026: *"không được OmniVoice vẫn oke mà, thêm hết vào cho tôi,
với Index vào"* — sau khi đã được trình bày rõ hai điều: cả hai bộ **KHÔNG có
mốc từng chữ** (chữ sẽ lệch như Piper) và trọng số OmniVoice là **CC-BY-NC =
cấm thương mại**. Đây là quyết định kinh doanh của anh ấy; việc của cổng này
là canh cho nó **không hỏng âm thầm**.

BỐN MỆNH ĐỀ CỔNG NÀY CANH (mỗi cái đều đã có tiền lệ hỏng thật trong repo):

  1. **CHỌN GIỌNG NGOÀI THÌ THẬT SỰ DÙNG NÓ.** Không được âm thầm lùi
     edge-tts rồi báo thành công — đúng họ lỗi "chọn X ra Y" (việc #110,
     cổng 55 combo giọng, cổng 67 CA 5 "phải đòi thêm *đã THỬ* chứ không chỉ
     đòi kết quả").
  2. **CẢ 6 CHỖ GỌI ĐI ĐÚNG CỬA CHUNG.** `thay_giong.py` có **3 chỗ** gọi
     `_synth_all_words`, `dubbing.py` còn 3 chỗ gọi `_synth_all`. Sót MỘT
     chỗ là video **LẪN HAI GIỌNG** mà mã thoát vẫn 0 (mệnh đề cổng 63).
     Vì vậy chỗ rẽ phải nằm TRONG `_synth_all`/`_synth_all_words`, và cổng
     này GỌI THẬT cả hai hàm rồi ĐẾM, không quét chuỗi.
  3. **THIẾU MODEL THÌ LÙI ÊM + GHI RÕ.** Lùi êm mà im lặng thì đúng bằng
     hỏng âm thầm (luật của `piper_tts._ghi_log` / `_ghi_log_el`).
  4. **KHÔNG NẠP torch/omnivoice VÀO TIẾN TRÌNH APP.** `import torch` sau
     khi Qt đã nạp = ACCESS VIOLATION và `try/except` KHÔNG chặn (cổng 55).

CỘNG BA CHỐT CHỐNG TỰ-LỪA:
  · **KHÔNG dùng núm `duration`/`speed` của model** — đo ở lượt 7: nén 2,0×
    thì núm model sai **37,0%** còn `rubberband` **3,5%**. Quét bằng AST.
  · **NHÃN PHẢI GHI GIẤY PHÉP CC-BY-NC** và KHÔNG EMOJI (máy anh Hùng thiếu
    glyph -> ô đen, bài học v2.6.22 / cổng 27).
  · **ALL-OR-NOTHING**: một câu không đọc được là bỏ cả loạt. Đọc được 18/20
    rồi để 2 câu lùi edge là video lẫn hai giọng.

**TỰ KIỂM: GỠ CHỐT RA THÌ PHẢI ĐỎ** — xem CA 8. Cổng không tự kiểm được thì
chỉ là con dấu (bài học cổng 56d, 64, 65).

KHÔNG TỐN GPU/GROQ TRONG HỒI QUY: `giong_ngoai._chay_ov` và `_lay_moc_groq`
bị VÁ — **đường đi, chỗ rẽ, cách lùi, cách ép khung, cách đếm đều là mã
THẬT**, chỉ mỗi lượt nạp model 6,1 GB và cú gọi Groq là giả. Ca chạy THẬT
bật bằng `BQ_GN_THAT=1` (đã chạy tay, xem `_do_gn_moc.py`).
"""
from __future__ import annotations

import ast
import asyncio
import os
import subprocess
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

from config import settings  # noqa: E402

DAT = 0
HONG = 0
FF = settings.FFMPEG_PATH
MA_OV = "ov:nu_tre"
MA_IX = "ix:mac_dinh"


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))


def _wav(path: str, giay: float = 1.0) -> None:
    """WAV THẬT (ffmpeg) — để `dai_wav`/`probe_duration` của mã thật có cái
    mà đo, không phải file rỗng giả vờ (bài học "ffmpeg mã 0 + file 0 KiB")."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", f"sine=frequency=300:duration={giay:g}", "-c:a", "pcm_s16le",
         path], check=True, timeout=60)


def _ma_that(p: Path) -> str:
    """Mã nguồn BỎ COMMENT + STRING.

    Quét tĩnh bằng `in` cả file thì chính DÒNG GHI CHÚ giải thích bản vá bị
    kể là vi phạm -> ĐỎ OAN VĨNH VIỄN (đã sập ở cổng 47, 51, 53, 54).
    """
    ra = []
    with open(p, "rb") as f:
        for t in tokenize.tokenize(f.readline):
            if t.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(t.string)
    return " ".join(ra)


# ══════════════════════════════════════════════════════════════════
def main() -> int:                                          # noqa: C901
    from app.core import dubbing
    from app.core import giong_ngoai as gn

    print("=" * 74)
    print("CỔNG 72 — GIỌNG NGOÀI (OmniVoice / IndexTTS)")
    print("=" * 74)

    san = Path(tempfile.mkdtemp(prefix="bq_gn_"))
    dem = {"ov": 0, "moc": 0, "texts": [], "hong_cau": None, "lay_moc": []}

    def _chay_ov_gia(items, model, py, instruct, langs, han_giay, on_msg):
        """Thay CÚ NẠP MODEL bằng ffmpeg. Mọi thứ khác vẫn là mã thật."""
        dem["ov"] += 1
        dem["texts"] += [it["text"] for it in items]
        ra = []
        for k, it in enumerate(items):
            if dem["hong_cau"] is not None and k == dem["hong_cau"]:
                continue                    # câu này "đọc hỏng" -> thiếu file
            _wav(it["raw"], 1.0 + 0.1 * k)
            ra.append({"i": it["i"], "p": it["raw"], "giay": 1.0 + 0.1 * k})
        return {"ok": True, "nap": 0.0, "gen": 0.0, "dev": "gia", "sr": 24000,
                "ra": ra, "vram": 0.0, "_sandbox": str(san / "sb")}

    def _moc_gia(text, wav):
        dem["moc"] += 1
        from app.ai import recap
        tu = [t for t in recap._word_tokens(text or "") if t.strip()]
        d = gn.dai_wav(wav) or 1.0
        b = d / max(1, len(tu))
        return [[i * b, (i + 1) * b, t] for i, t in enumerate(tu)]

    that = bool(os.environ.get("BQ_GN_THAT"))
    if not that:
        gn._chay_ov = _chay_ov_gia
        gn._lay_moc_groq = _moc_gia
    # `co_omnivoice` phải trả True để đi được nhánh chính; ca THIẾU MODEL
    # (CA 3) tự vá lại thành False.
    tt_that = gn.tinh_trang_omnivoice()
    if not that:
        gn.tinh_trang_omnivoice = lambda: {
            "co": True, "thieu": [], "python": sys.executable,
            "model": str(san / "model"), "thu_muc": str(san)}
        gn.co_omnivoice = lambda: True

    TEXTS = ["Hôm nay trời rất đẹp và chúng ta cùng đi dạo.",
             "Anh ấy mở cửa rồi bước vào trong căn phòng tối."]

    def _paths(ten: str) -> list:
        return [str(san / ten / f"c{i}.wav") for i in range(len(TEXTS))]

    # ══════════════ CA 1 — CHỌN GIỌNG NGOÀI THÌ THẬT SỰ DÙNG NÓ ══════════
    print("\nCA 1 — chọn giọng ngoài thì THẬT SỰ dùng nó (không lùi âm thầm)")
    dem["ov"] = 0
    p1 = _paths("ca1w")
    ok_w, moc_w = asyncio.run(
        dubbing._synth_all_words(TEXTS, MA_OV, p1, lang="vi"))
    ok(dem["ov"] >= 1, "1a `_synth_all_words` ĐÃ THỬ giọng ngoài "
       "(không chỉ nhìn kết quả — bài học cổng 67 CA 5)",
       f"{dem['ov']} lượt gọi")
    ok(all(ok_w), "1b mọi câu đọc được", f"{ok_w}")
    ok(all(Path(p).exists() and gn.dai_wav(p) > 0.02 for p in p1),
       "1c file ra CÓ TIẾNG THẬT (đo lại, không tin cờ ok)",
       f"{[round(gn.dai_wav(p), 2) for p in p1]}")

    dem["ov"] = 0
    p2 = _paths("ca1s")
    ok_s = asyncio.run(dubbing._synth_all(TEXTS, MA_OV, p2, lang="vi"))
    ok(dem["ov"] >= 1 and all(ok_s),
       "1d `_synth_all` (cửa KHÔNG cần mốc) cũng đi giọng ngoài",
       f"{dem['ov']} lượt · ok={ok_s}")

    # ══════════════ CA 2 — MỐC RA THẬT ══════════════
    print("\nCA 2 — mốc từng chữ ra THẬT (bộ này không trả mốc, phải dò lại)")
    ok(all(len(m) > 0 for m in moc_w), "2a mọi câu có mốc",
       f"{[len(m) for m in moc_w]} từ")
    # 2b CANH BẤT BIẾN, KHÔNG CANH CƠ CHẾ. Bản đầu đòi đích danh
    # `_lay_moc_groq` phải được gọi. Từ khi có `app/core/giong_hang.py`, máy
    # CÓ bộ gióng hàng lấy mốc bằng đường đó và KHÔNG gọi Groq lượt nào (đo
    # được: chính xác hơn 2,1-3,6 lần tuỳ thứ tiếng, và khỏi đốt lượt). Canh
    # cơ chế cũ thì cổng ĐỎ OAN trên đúng cái máy vừa nâng cấp — mà cổng đỏ
    # oan thì người ta bỏ qua nó (bài học cổng 41/47). Bất biến THẬT là:
    # **cửa CÓ mốc phải ra mốc cho MỌI câu**, và **CẢ HAI đường đều phải tự
    # đứng được** — nên kiểm luôn đường lùi thay vì bỏ đi.
    from app.core import giong_hang as _GH
    if _GH.co_giong_hang():
        ok(dem["moc"] == 0,
           "2b có bộ gióng hàng -> KHÔNG đốt lượt Groq nào mà vẫn đủ mốc",
           f"{dem['moc']} lượt Groq · {[len(m) for m in moc_w]} từ")
        dem["moc"] = 0
        _cu = os.environ.get("BQ_GIONG_HANG")
        os.environ["BQ_GIONG_HANG"] = "0"
        try:
            _ok2, _moc2 = asyncio.run(dubbing._synth_all_words(
                TEXTS, MA_OV, _paths("ca2lui"), lang="vi"))
        finally:
            if _cu is None:
                os.environ.pop("BQ_GIONG_HANG", None)
            else:
                os.environ["BQ_GIONG_HANG"] = _cu
        ok(dem["moc"] >= len(TEXTS) and all(len(m) > 0 for m in _moc2),
           "2b' TẮT gióng hàng -> tự quay về Groq chép ngược, VẪN đủ mốc "
           "(đúng cảnh máy nhân viên chưa tải 1,18 GB model)",
           f"{dem['moc']} lượt Groq · {[len(m) for m in _moc2]} từ")
    else:
        ok(dem["moc"] >= len(TEXTS),
           "2b chưa có bộ gióng hàng -> cửa CÓ mốc gọi Groq cho từng câu",
           f"{dem['moc']} lượt")
    tang = all(all(m[i][0] <= m[i + 1][0] for i in range(len(m) - 1))
               for m in moc_w if m)
    ok(tang, "2c mốc TĂNG DẦN theo thời gian")
    trong = all(m[-1][1] <= gn.dai_wav(p) + 0.25
                for m, p in zip(moc_w, p1) if m)
    ok(trong, "2d mốc cuối KHÔNG vượt quá độ dài file tiếng")
    dem["moc"] = 0
    asyncio.run(dubbing._synth_all(TEXTS, MA_OV, _paths("ca2s"), lang="vi"))
    ok(dem["moc"] == 0,
       "2e cửa KHÔNG cần mốc thì KHÔNG đốt lượt Groq nào (lay_moc=False)",
       f"{dem['moc']} lượt")

    # ══════════════ CA 3 — THIẾU MODEL THÌ LÙI ÊM + GHI RÕ ══════════════
    print("\nCA 3 — thiếu model -> LÙI ÊM về edge-tts, KHÔNG nổ, có GHI LÝ DO")
    log = []
    gn_log_that = gn._ghi_log
    gn._ghi_log = lambda d: log.append(d)
    co_that = gn.co_omnivoice
    tt_ca3 = gn.tinh_trang_omnivoice
    # Giả lập ĐÚNG cảnh máy nhân viên: thiếu gói và thiếu trọng số. Vá mỗi
    # `co_omnivoice` -> `thieu` rỗng -> mục 3d nghiệm đúng vì lý do RỖNG
    # (log ghi "thiếu: []"), tức tự cho điểm. Phải dựng trạng thái thật.
    gn.co_omnivoice = lambda: False
    gn.tinh_trang_omnivoice = lambda: {
        "co": False, "thieu": ["torch/__init__.py", "trọng số k2-fsa/OmniVoice"],
        "python": "", "model": "", "thu_muc": str(san)}
    dung, lui = dubbing._ngoai_hay_khong(MA_OV)
    ok(not dung, "3a thiếu model -> KHÔNG đi đường giọng ngoài")
    ok(bool(lui) and not gn.la_giong_ngoai(lui),
       "3b LÙI về giọng edge-tts thật", f"{lui}")
    ok(any("LÙI" in d for d in log),
       "3c có GHI LÝ DO vào log (lùi êm mà im lặng = hỏng âm thầm)",
       f"{len(log)} dòng")
    ok(any("torch" in d and "trọng số" in d for d in log),
       "3d log nêu ĐÍCH DANH còn thiếu gì (không chỉ nói 'chưa có')",
       (log[0][:80] if log else ""))
    gn.co_omnivoice = co_that
    gn.tinh_trang_omnivoice = tt_ca3

    log.clear()
    dung_ix, lui_ix = dubbing._ngoai_hay_khong(MA_IX)
    ok(not dung_ix and not gn.la_giong_ngoai(lui_ix),
       "3e IndexTTS chưa dựng được -> LÙI ÊM (không nổ, không câm)",
       f"{lui_ix}")
    ok_ix, moc_ix = gn.doc_loat(TEXTS, _paths("ca3"), MA_IX, lang="vi")
    ok(not any(ok_ix) and not any(moc_ix),
       "3f `doc_loat` với mã ix: trả toàn False để nơi gọi lùi", f"{ok_ix}")
    gn._ghi_log = gn_log_that

    # ══════════════ CA 4 — ALL-OR-NOTHING ══════════════
    print("\nCA 4 — một câu hỏng thì BỎ CẢ LOẠT (không để video lẫn 2 giọng)")
    if not that:
        dem["hong_cau"] = 1                 # câu thứ 2 "đọc không ra"
        log2 = []
        gn._ghi_log = lambda d: log2.append(d)
        ok_h, moc_h = gn.doc_loat(TEXTS, _paths("ca4"), MA_OV, lang="vi")
        gn._ghi_log = gn_log_that
        dem["hong_cau"] = None
        ok(not any(ok_h),
           "4a 1/2 câu hỏng -> TOÀN BỘ trả False (cả video một giọng edge)",
           f"{ok_h}")
        ok(any("BỎ CẢ LOẠT" in d for d in log2),
           "4b có ghi lý do bỏ cả loạt", f"{len(log2)} dòng")
    else:
        print("  (bỏ qua ở chế độ BQ_GN_THAT=1)")

    # ══════════════ CA 5 — KHÔNG NẠP torch VÀO TIẾN TRÌNH APP ══════════════
    print("\nCA 5 — KHÔNG nạp torch/omnivoice vào tiến trình app")
    ok("torch" not in sys.modules,
       "5a chạy xong CA 1-4 mà `torch` VẪN chưa nạp (Qt + torch = 0xC0000005)")
    ok("omnivoice" not in sys.modules, "5b `omnivoice` chưa nạp")
    ma = _ma_that(Path(gn.__file__))
    xau = [t for t in ("import torch", "import omnivoice",
                       "import transformers") if t in ma]
    ok(not xau, "5c mã THẬT (bỏ comment/chuỗi) không import gói nào của model",
       f"{xau}" if xau else "sạch")
    cay = ast.parse(Path(gn.__file__).read_text(encoding="utf-8"))
    chen = [n.lineno for n in ast.walk(cay)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("insert", "append")
            and isinstance(n.func.value, ast.Attribute)
            and n.func.value.attr == "path"]
    ok(not chen, "5d KHÔNG chèn gì vào `sys.path` của app", f"{chen}")
    # TỰ KIỂM BỘ DÒ — HAI CHIỀU. Bộ dò chỉ-bắt hoặc chỉ-tha đều vô dụng:
    # cổng 47/51/53/54 đỏ oan vì quét bằng `in` cả file, còn cổng 56d/64 pass
    # oan vì quét chuỗi. Nên phải chứng minh cả hai chiều mới dám tin CA 5c.
    mo = san / "dodo"
    mo.mkdir(parents=True, exist_ok=True)
    (mo / "co.py").write_text("import torch\nx = 1\n", encoding="utf-8")
    (mo / "khong.py").write_text(
        '# đừng bao giờ import torch ở đây\nS = "import torch"\nx = 1\n',
        encoding="utf-8")
    ok("import torch" in _ma_that(mo / "co.py"),
       "5e tự kiểm bộ dò (chiều BẮT): file CÓ `import torch` thật thì thấy")
    ok("import torch" not in _ma_that(mo / "khong.py"),
       "5f tự kiểm bộ dò (chiều THA): `import torch` chỉ nằm trong ghi chú/"
       "chuỗi thì KHÔNG kể là vi phạm (chống đỏ oan)")

    # ══════════════ CA 6 — KHÔNG DÙNG NÚM `duration` CỦA MODEL ══════════
    print("\nCA 6 — ép khung bằng `rubberband`, KHÔNG dùng núm của model")
    ok("duration" not in ma and "speed" not in ma,
       "6a mã THẬT không nhắc `duration`/`speed` (núm model: nén 2,0x sai "
       "37,0% vs rubberband 3,5%)")
    ok("_co_gian_chuoi" in ma,
       "6b dùng lại `thay_giong._co_gian_chuoi` (tự lùi atempo khi ffmpeg "
       "máy đó thiếu rubberband), không đẻ đường thứ hai")
    # ÉP KHUNG PHẢI ĐỔI ĐỘ DÀI THẬT — không tin cờ trả về
    src = san / "ep" / "src.wav"
    _wav(str(src), 2.0)
    dst = san / "ep" / "dst.wav"
    ok(gn._ep_khung(src, dst, 2.0), "6c `_ep_khung` chạy được")
    d0, d1 = gn.dai_wav(src), gn.dai_wav(dst)
    ok(0.85 < d1 / max(d0 / 2.0, 1e-6) < 1.15,
       "6d ép 2,0x ra ĐỘ DÀI ĐÚNG (đo lại file, không tin mã thoát)",
       f"{d0:.2f}s -> {d1:.2f}s")
    dst1 = san / "ep" / "dst1.wav"
    gn._ep_khung(src, dst1, 1.0)
    ok(abs(gn.dai_wav(dst1) - d0) < 0.05,
       "6e tempo 1,0 -> KHÔNG đụng file (giữ nguyên độ dài)",
       f"{gn.dai_wav(dst1):.2f}s")

    # ══════════════ CA 7 — NHÃN COMBO: GIẤY PHÉP + KHÔNG EMOJI ══════════
    print("\nCA 7 — nhãn trong hộp chọn giọng")
    from app.ui import thay_giong_dialog as dlg
    ds = dlg.giong_dung_duoc([("Nữ Việt", "vi-VN-HoaiMyNeural"),
                              ("Nam Việt", "vi-VN-NamMinhNeural")])
    ma_ds = [v for _n, v in ds]
    nhan_ov = [n for n, v in ds if str(v).startswith("ov:")]
    ok(any(str(v).startswith("ov:") for v in ma_ds),
       "7a combo CÓ giọng OmniVoice", f"{len(nhan_ov)} dòng")
    thieu_gp = [n for n in nhan_ov if "CC-BY-NC" not in n]
    ok(nhan_ov and not thieu_gp,
       "7b MỌI nhãn OmniVoice ghi rõ trọng số CC-BY-NC",
       f"thiếu ở {thieu_gp}" if thieu_gp else f"{len(nhan_ov)}/{len(nhan_ov)}")
    thieu_tm = [n for n in nhan_ov if "thương mại" not in n]
    ok(nhan_ov and not thieu_tm,
       "7c ... và nói thẳng CẤM DÙNG THƯƠNG MẠI (anh Hùng bán app)")
    thieu_cl = [n for n in nhan_ov if "16,9" not in n]
    ok(nhan_ov and not thieu_cl,
       "7d ... và ghi CẢNH BÁO chất lượng như Piper (tiếng Việt 16,9% vs "
       "edge 6,8%)")
    xau_e = [n for n, _v in ds
             if any(ord(c) > 0xFFFF or __import__("unicodedata")
                    .category(c) == "So" for c in n)]
    ok(not xau_e, "7e KHÔNG nhãn nào có emoji (máy anh Hùng thiếu glyph -> "
       "ô đen, bài học v2.6.22)", f"{xau_e[:2]}")
    ok(MA_IX not in ma_ds,
       "7f IndexTTS CHƯA chạy được -> KHÔNG đưa vào combo (đưa vào là đẩy "
       "người dùng chọn thứ sẽ âm thầm lùi edge)")

    # ---- NHÃN PHẢI ĐỔI THEO MÁY (thêm 18/08/2026) --------------------------
    # Con số PHỦ/RUNG trong nhãn là con số của ĐƯỜNG LẤY MỐC, mà đường đó đổi
    # theo việc máy có bộ gióng hàng hay không. In một câu cố định là: máy đã
    # tải 1,2 GB vẫn bị doạ bằng số cũ (đuổi người dùng khỏi lựa chọn vừa
    # được chữa), hoặc máy chưa tải lại được hứa hão. Đúng tiền lệ nhãn Piper.
    from app.core import giong_hang as _GH
    _co_that = _GH.co_giong_hang
    try:
        _GH.co_giong_hang = lambda: False
        nhan_khong = gn.canh_bao_chat_luong()
        _GH.co_giong_hang = lambda: True
        nhan_co = gn.canh_bao_chat_luong()
    finally:
        _GH.co_giong_hang = _co_that
    ok(nhan_khong != nhan_co,
       "7g nhãn chất lượng ĐỔI THEO MÁY (có/không bộ gióng hàng)")
    ok("gióng hàng" in nhan_co and "98,5" in nhan_co,
       "7h máy CÓ gióng hàng -> nói số MỚI (phủ 98,5%)", nhan_co[-70:])
    ok("38-99" in nhan_khong and "gióng hàng" in nhan_khong,
       "7i máy CHƯA có -> GIỮ cảnh báo phủ thấp + chỉ đường tải",
       nhan_khong[-70:])
    ok("16,9" in nhan_co and "16,9" in nhan_khong,
       "7j phần ĐỌC SAI CHỮ giữ ở CẢ HAI (đo cách model ĐỌC, gióng hàng "
       "không đụng tới)")
    # GIẤY PHÉP KHÔNG ĐƯỢC ĐỔI: trọng số vẫn CC-BY-NC dù có gióng hàng hay
    # không — anh Hùng đã biết và chấp nhận, nhưng nhãn không được im đi.
    ok("CC-BY-NC" not in nhan_co and "CC-BY-NC" not in nhan_khong
       and "CC-BY-NC" in gn.CANH_BAO_GP_OV,
       "7k cảnh báo GIẤY PHÉP nằm RIÊNG, không bị câu chất lượng nuốt")

    # ---- CHỖ ĐỂ ĐỒ: KHÔNG ĐƯỢC NẰM TRONG `%TEMP%` (18/08/2026) -------------
    # Môi trường 7,74 GB từng nằm trong `%TEMP%\bq_tts_rr\venv_ov`: một lượt
    # tempsweep/Disk Cleanup là mất, và triệu chứng là "giọng biến khỏi
    # combo" chứ không phải một dòng lỗi. Cùng bệnh `_lib` bị lượt tự cập
    # nhật xoá (cổng 58 CA5).
    import tempfile as _tf
    ok(_tf.gettempdir().lower() not in str(gn.thu_muc_ngoai()).lower(),
       "7l chỗ để đồ giọng ngoài KHÔNG nằm trong thư mục TẠM",
       str(gn.thu_muc_ngoai()))
    ok(gn.o_thu_muc_tam(str(Path(_tf.gettempdir()) / "x" / "Scripts"
                            / "python.exe")) != "",
       "7m TỰ KIỂM BỘ DÒ: đưa đường dẫn TRONG %TEMP% thì `o_thu_muc_tam` "
       "PHẢI kêu (không thì 7n là con dấu)")
    ok(gn.o_thu_muc_tam() == "" or not gn.co_omnivoice(),
       "7n máy này: môi trường KHÔNG còn nằm trong %TEMP%",
       gn.o_thu_muc_tam() or "sạch")

    # ══════════════ CA 8 — TỰ KIỂM: GỠ CHỐT RA THÌ PHẢI ĐỎ ══════════════
    print("\nCA 8 — TỰ KIỂM: gỡ chốt ra thì cổng PHẢI đỏ")
    ngoai_that = dubbing._ngoai_hay_khong
    dubbing._ngoai_hay_khong = lambda v: (False, v)   # gỡ chốt cửa chung
    dem["ov"] = 0
    try:
        asyncio.run(dubbing._synth_all_words(
            TEXTS, MA_OV, _paths("ca8"), lang="vi"))
    except Exception:                                        # noqa: BLE001
        pass
    ok(dem["ov"] == 0,
       "8a gỡ chốt -> KHÔNG lượt giọng ngoài nào chạy (tức CA 1 đang đo "
       "thật, không phải con dấu)", f"{dem['ov']} lượt")
    dubbing._ngoai_hay_khong = ngoai_that

    ep_that = gn._ep_khung
    gn._ep_khung = lambda a, b, t: False              # gỡ chốt ép khung
    ok_p, _ = gn.doc_loat(TEXTS, _paths("ca8b"), MA_OV, lang="vi")
    ok(not any(ok_p),
       "8b ép khung hỏng -> BỎ CẢ LOẠT (không ra file nửa vời)", f"{ok_p}")
    gn._ep_khung = ep_that

    # ══════════════ CA 9 — 3 CHỖ GỌI CỦA `thay_giong.py` ══════════════
    print("\nCA 9 — cả 3 chỗ gọi của `thay_giong.py` đi qua CỬA CHUNG")
    from app.core import thay_giong as tg
    cay_tg = ast.parse(Path(tg.__file__).read_text(encoding="utf-8"))
    goi_w = [n for n in ast.walk(cay_tg)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_synth_all_words"]
    ok(len(goi_w) == 3,
       "9a vẫn ĐÚNG 3 chỗ gọi (thêm chỗ thứ 4 là cổng 63 đỏ — phải đổi CÁCH "
       "LÀM chứ không sửa con số)", f"{len(goi_w)} chỗ")
    cay_db = ast.parse(Path(dubbing.__file__).read_text(encoding="utf-8"))
    than = {n.name: n for n in ast.walk(cay_db)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for ten_h in ("_synth_all", "_synth_all_words"):
        goi = [n for n in ast.walk(than[ten_h])
               if isinstance(n, ast.Call)
               and ((isinstance(n.func, ast.Name)
                     and n.func.id == "_ngoai_hay_khong")
                    or (isinstance(n.func, ast.Attribute)
                        and n.func.attr == "_ngoai_hay_khong"))]
        ok(bool(goi), f"9b `{ten_h}` GỌI THẬT `_ngoai_hay_khong` (đọc bằng "
           f"AST, không tìm chuỗi — bài học cổng 56d/64)")

    print("\n" + "=" * 74)
    print(f"CỔNG 72: ĐẠT {DAT} · HỎNG {HONG}"
          + ("  (chế độ THẬT)" if that else ""))
    print(f"  máy này: OmniVoice {'CÓ' if tt_that['co'] else 'CHƯA'} "
          f"· IndexTTS {'CÓ' if gn.co_indextts() else 'CHƯA (mới có khung)'}")
    print("=" * 74)
    try:
        import shutil
        shutil.rmtree(san, ignore_errors=True)
    except Exception:                                        # noqa: BLE001
        pass
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
