# -*- coding: utf-8 -*-
"""CỔNG 63 — BIẾN THỂ GIỌNG (`pitch`) NỐI ĐỦ 3 CHỖ GỌI TTS.

VÌ SAO CÓ CỔNG NÀY (16/08/2026): edge-tts chỉ có 2 giọng tiếng Việt, 200-300
kênh dùng chung 2 giọng thì kênh nào cũng kêu giống nhau. `pitch` sinh thêm
biến thể mà không tốn thêm lượt mạng nào.

**MỆNH ĐỀ ĐẮT NHẤT CỔNG NÀY CANH:** `thay_giong.py` có **BA** chỗ gọi
`dubbing._synth_all_words` — `doc_ban_dich` · `rut_gon_vua_khung` ·
`doc_nhanh_vua_khung`. Sót MỘT chỗ thì những câu đi qua chỗ đó đọc bằng cao
độ GỐC, ra video **lẫn hai giọng**, mà `rc` vẫn 0 và không một dòng nào báo.
Đúng họ bẫy "cửa chờ ffmpeg bị xoá mà không ai biết" (cổng 36b) và "cookie
phải bản-sao-tạm ở MỌI chỗ spawn".

MỆNH ĐỀ 2 — **BẤT BIẾN CHUỖI CŨ**: mã giọng không có `|` phải đi qua
`tach_giong_pitch` ra Y NGUYÊN + `"+0Hz"`, và `+0Hz` phải ghép ngược ra ĐÚNG
chuỗi cũ. Nếu không thì mọi mẫu đã lưu và mọi job đang nằm trong DB đổi nghĩa.

MỆNH ĐỀ 3 — nhãn tiếng Việt, KHÔNG EMOJI, và combo KHÔNG đẻ dòng trùng.

  .venv\\Scripts\\python -u _test_bien_the_giong.py
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

DAT = HONG = 0


def kiem(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def co_emoji(s: str) -> bool:
    return any(ord(c) > 0x2100 for c in s)


def main() -> int:
    print("=" * 70)
    print("CỔNG 63 — BIẾN THỂ GIỌNG (pitch) NỐI ĐỦ 3 CHỖ GỌI TTS")
    print("=" * 70)

    from app.core import thay_giong as TG

    # ═══════════ CA 1 — tách/ghép mã, BẤT BIẾN chuỗi cũ ═══════════
    print("\nCA 1 — `tach_giong_pitch` / `ma_bien_the`")
    cu = "vi-VN-NamMinhNeural"
    kiem("1a mã CŨ (không có `|`) -> nguyên vẹn + `+0Hz`",
         TG.tach_giong_pitch(cu) == (cu, "+0Hz"), f"{TG.tach_giong_pitch(cu)}")
    kiem("1b mã biến thể tách đúng 2 phần",
         TG.tach_giong_pitch(f"{cu}|-20Hz") == (cu, "-20Hz"))
    kiem("1c `+0Hz` ghép ngược ra ĐÚNG chuỗi cũ (không đẻ hậu tố)",
         TG.ma_bien_the(cu, "+0Hz") == cu, TG.ma_bien_the(cu, "+0Hz"))
    kiem("1d ghép rồi tách lại ra chính nó (round-trip)",
         all(TG.tach_giong_pitch(TG.ma_bien_the(cu, p)) == (cu, p)
             for p in ("-20Hz", "-10Hz", "+10Hz", "+20Hz")))
    # mã pitch LẠ không được làm chết lượt thay giọng
    kiem("1e mã pitch LẠ -> bỏ pitch, KHÔNG ném",
         TG.tach_giong_pitch(f"{cu}|nhanh") == (cu, "+0Hz"),
         f"{TG.tach_giong_pitch(f'{cu}|nhanh')}")
    kiem("1f chuỗi rỗng -> không nổ", TG.tach_giong_pitch("") == ("", "+0Hz"))

    # ═══════════ CA 2 — BA chỗ gọi TTS đều truyền `pitch` ═══════════
    # Đây là mục đắt nhất: sót 1 chỗ = video lẫn hai giọng, rc vẫn 0.
    print("\nCA 2 — BA chỗ gọi `_synth_all_words` đều truyền `pitch`")
    than = Path(TG.__file__).read_text(encoding="utf-8")
    cay = ast.parse(than)

    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "_synth_all_words"]
    kiem("2a tìm thấy ĐÚNG 3 chỗ gọi (thêm chỗ thứ 4 thì cổng này phải đỏ "
         "để người thêm biết là còn phải nối pitch)",
         len(goi) == 3, f"{len(goi)} chỗ")

    thieu = []
    hang_so = []
    for n in goi:
        kw = {k.arg: k.value for k in n.keywords}
        if "pitch" not in kw:
            thieu.append(n.lineno)
        elif isinstance(kw["pitch"], ast.Constant):
            # `pitch="+0Hz"` giữ nguyên mặt chữ mà vô hiệu hoá cả tính năng
            hang_so.append(n.lineno)
    kiem("2b MỌI chỗ gọi đều có `pitch=`", not thieu,
         f"thiếu ở dòng {thieu}" if thieu else "3/3")
    kiem("2c ... và truyền BIẾN, không phải hằng số", not hang_so,
         f"hằng số ở dòng {hang_so}" if hang_so else "3/3")

    # ═══════════ CA 3 — bảng biến thể ═══════════
    print("\nCA 3 — bảng biến thể + nhãn")
    ds = TG.bien_the_giong()
    kiem("3a có biến thể cho cả 2 giọng Việt",
         len({TG.tach_giong_pitch(m)[0] for m, _n in ds}) == 2,
         f"{sorted({TG.tach_giong_pitch(m)[0] for m, _n in ds})}")
    nhan = [n for _m, n in ds]
    kiem("3b nhãn KHÔNG EMOJI", not any(co_emoji(x) for x in nhan))
    # "CÓ DẤU TIẾNG VIỆT" LÀ CHỐT SAI BẢN CHẤT — đã hỏng oan 2 lần khi viết
    # cổng này: bản 1 liệt kê tay 15 chữ có dấu nên thiếu `ọ`/`ố` ("giọng
    # gốc"); bản 2 dùng dải `À-ỹ` thì vẫn đỏ vì **"Nam Minh — cao" là tiếng
    # Việt mà không có một dấu nào**. Mệnh đề THẬT cần canh không phải "có
    # dấu" mà là **nhãn không phơi mã máy / chữ tiếng Anh ra cho anh Hùng**.
    XAU = ("hz", "|", "pitch", "high", "low", "male", "female", "neural",
           "vi-vn", "+", "default")
    lo = [x for x in nhan if any(t in x.lower() for t in XAU)]
    kiem("3c nhãn KHÔNG phơi mã máy/chữ tiếng Anh ra giao diện",
         not lo, f"lộ: {lo}" if lo else f"{len(nhan)} nhãn sạch")
    kiem("3d không có nhãn trùng nhau", len(set(nhan)) == len(nhan))
    kiem("3e không có mã trùng nhau",
         len({m for m, _n in ds}) == len(ds))
    kiem("3f giọng KHÔNG phải tiếng Việt -> `[]` (combo giữ nguyên như cũ)",
         TG.bien_the_giong("en-US-AndrewNeural") == [])
    # mọi pitch trong bảng phải hợp lệ (không thì `ma_bien_the` âm thầm bỏ)
    kiem("3g mọi mã trong bảng tách lại ra ĐÚNG pitch của nó",
         all(TG.tach_giong_pitch(m)[1] == p
             for v, b in TG.BIEN_THE_PITCH.items() for p, _n in b
             if (m := TG.ma_bien_the(v, p)) and p != "+0Hz"))

    # ═══════════ CA 4 — COMBO trong hộp Thay giọng ═══════════
    print("\nCA 4 — combo hộp Thay giọng nhận biến thể, KHÔNG đẻ dòng trùng")
    import _test_guard  # noqa: F401  (luật: mọi cổng đụng UI phải import)
    from app.ui.thay_giong_dialog import giong_dung_duoc

    vao = [("Tiếng Việt", ""),
           ("Nam - Nam Minh", "vi-VN-NamMinhNeural"),
           ("Nu - Hoai My", "vi-VN-HoaiMyNeural"),
           ("Tieng Anh", ""),
           ("Andrew", "en-US-AndrewNeural")]
    ra = giong_dung_duoc(vao)
    ma = [v for _n, v in ra if v]
    kiem("4a giọng gốc VẪN CÒN (không bị biến thể thay chỗ)",
         "vi-VN-NamMinhNeural" in ma and "vi-VN-HoaiMyNeural" in ma)
    kiem("4b có mã biến thể trong combo",
         any("|" in v for v in ma), f"{[v for v in ma if '|' in v][:3]}")
    kiem("4c KHÔNG có mã trùng (mục `+0Hz` phải bị bỏ, nó trùng giọng gốc)",
         len(set(ma)) == len(ma),
         f"{len(ma)} mã / {len(set(ma))} khác nhau")
    kiem("4d giọng KHÁC ngôn ngữ không bị chèn biến thể",
         ma.count("en-US-AndrewNeural") == 1
         and not any(v.startswith("en-US") and "|" in v for v in ma))
    kiem("4e biến thể nằm NGAY SAU giọng gốc của nó",
         ma.index("vi-VN-NamMinhNeural") + 1 < len(ma)
         and ma[ma.index("vi-VN-NamMinhNeural") + 1].startswith(
             "vi-VN-NamMinhNeural|"))
    kiem("4f nhãn trong combo KHÔNG EMOJI",
         not any(co_emoji(n) for n, _v in ra))

    # ═══════════ CA 5 — BẤT BIẾN: chưa chọn biến thể thì y hệt cũ ═══════════
    print("\nCA 5 — BẤT BIẾN: mẫu CŨ (mã không có `|`) chạy y hệt trước")
    kiem("5a mọi giọng mặc định theo ngôn ngữ đều KHÔNG có `|`",
         all("|" not in TG.giong_theo_ngon_ngu(x)
             for x in ("vi", "en", "zh", "ja", "ko")))
    kiem("5b `+0Hz` = KHÔNG truyền pitch cho edge-tts (đường cũ nguyên vẹn)",
         TG.tach_giong_pitch("vi-VN-HoaiMyNeural")[1] == "+0Hz")

    print("\n" + "=" * 70)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 70)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
