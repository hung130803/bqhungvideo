# -*- coding: utf-8 -*-
r"""ĐO PHÉP 4 — TỪ KHOÁ KHỚP CẢNH GẶP TIẾNG TRUNG THÌ SAO.

    .venv\Scripts\python _do_lp_trung.py

3 cửa quyết định "thêm gì vào clip" và mỗi cửa dùng một CĂN CỨ khác nhau:
  · `hieu_ung.chon_hieu_ung`  -> SỐ ĐO (RMS tiếng, độ động hình) — không đọc chữ
  · `hieu_ung.chon_chuyen_canh` -> SỐ ĐO
  · `lop_phu.chon_lop_phu`    -> **TỪ KHOÁ** (bảng tiếng VIỆT + bảng Nhật/Hàn)
Câu hỏi: gặp tiếng TRUNG thì cửa thứ 3 có rơi về mặc định (không thêm gì) không.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"
import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def main() -> int:
    from app.core import lop_phu as LP
    from app.core import hieu_ung as HU

    print("══ (a) BẢNG TỪ KHOÁ CÓ CHỮ TRUNG KHÔNG ══")
    han_only = kana = hangul = latin = 0
    vd_han = []
    for khoa, l in LP.LUAT.items():
        for t in tuple(l.manh) + tuple(l.phu) + tuple(l.cam):
            co_kana = any(0x3040 <= ord(c) <= 0x30FF for c in t)
            co_hang = any(0xAC00 <= ord(c) <= 0xD7AF for c in t)
            co_han = any(0x4E00 <= ord(c) <= 0x9FFF for c in t)
            if co_kana:
                kana += 1
            elif co_hang:
                hangul += 1
            elif co_han:
                han_only += 1
                if len(vd_han) < 25:
                    vd_han.append(f"{t}({khoa})")
            else:
                latin += 1
    print(f"  tổng từ khoá: {len(LP.LUAT)} cảnh")
    print(f"    có KANA (chắc chắn Nhật)          : {kana}")
    print(f"    có HANGUL (chắc chắn Hàn)         : {hangul}")
    print(f"    CHỈ chữ Hán (Nhật/Trung dùng chung): {han_only}")
    print(f"    latin/Việt                        : {latin}")
    print(f"  25 từ CHỈ-chữ-Hán đầu: {', '.join(vd_han)}")

    print("\n══ (b) TỪ TRUNG THÔNG DỤNG CÓ TRONG BẢNG KHÔNG ══")
    #: cùng NGHĨA với từ khoá đã có, nhưng viết theo tiếng TRUNG GIẢN THỂ
    THU = [("tuyet_roi", "下雪"), ("tuyet_roi", "雪花"), ("tuyet_roi", "暴雪"),
           ("trai_tim", "婚礼"), ("trai_tim", "新娘"), ("trai_tim", "宝宝"),
           ("confetti", "生日"), ("confetti", "蛋糕"), ("confetti", "庆祝"),
           ("mua_roi", "下雨"), ("mua_roi", "暴雨"),
           ("tien_bac", "钱"), ("tien_bac", "金钱"), ("tien_bac", "钞票"),
           ("tan_lua", "火灾"), ("tan_lua", "爆炸"),
           ("duoi_nuoc", "潜水"), ("duoi_nuoc", "海底"), ("duoi_nuoc", "水下")]
    thieu = []
    for khoa, tu in THU:
        l = LP.LUAT.get(khoa)
        if l is None:
            print(f"    (không có cảnh '{khoa}')")
            continue
        co = LP._co(tu, l._rd_manh) or LP._co(tu, l._rd_phu)
        print(f"    cảnh {khoa:<12} từ TRUNG '{tu}' -> "
              f"{'CÓ trong bảng' if co else 'KHÔNG có'}")
        if not co:
            thieu.append(f"{khoa}/{tu}")
    print(f"  -> {len(thieu)}/{len(THU)} từ tiếng Trung thông dụng KHÔNG có "
          "trong bảng")

    print("\n══ (c) BẪY DÙNG CHUNG CHỮ HÁN: cùng chữ, KHÁC NGHĨA ══")
    BAY = [("料理", "Nhật = NẤU ĂN (nằm trong danh sách CẤM của tuyet_roi); "
                   "Trung = XỬ LÝ/giải quyết"),
           ("汽車", "Nhật = TÀU HOẢ; Trung phồn thể = Ô TÔ"),
           ("手紙", "Nhật = LÁ THƯ (bui_phim/phụ); Trung = GIẤY VỆ SINH"),
           ("大家", "Nhật = chủ nhà; Trung = MỌI NGƯỜI"),
           ("勉強", "Nhật = HỌC; Trung = miễn cưỡng")]
    for tu, y in BAY:
        khop = [k for k, l in LP.LUAT.items()
                if LP._co(tu, l._rd_manh) or LP._co(tu, l._rd_phu)
                or LP._co(tu, l._rd_cam)]
        print(f"    '{tu}' — {y}")
        print(f"        bảng hiện khớp cảnh: {khop or 'không cảnh nào'}")

    print("\n══ (d) TRÊN BẢN CHÉP LỜI TIẾNG TRUNG THẬT ══")
    tj = WORK / "trung_transcript.json"
    if not tj.exists():
        print("  BỎ QUA: chưa có bản chép lời (chạy _do_trung.py trước).")
        return 1
    tr = json.loads(tj.read_text(encoding="utf-8"))
    segs = [[0.0, 187.27]]
    dg = LP.digest_tu_loi(tr, segs)
    loi = " ".join(str(s.get("text", "")) for s in (tr.get("segments") or []))
    print(f"  digest_tu_loi -> {len(dg)} mốc · lời {len(loi)} ký tự")
    bang = []
    for khoa, l in LP.LUAT.items():
        d = LP._diem(l, dg, loi)
        if d:
            bang.append((d.get("tin", 0.0), khoa, d))
    bang.sort(reverse=True)
    for tin, khoa, d in bang[:6]:
        print(f"    {khoa:<14} tin={tin:.2f} "
              f"(ngưỡng {LP.NGUONG_TIN}) · {d.get('vi_sao', '')[:90]}")
    ra, ly_do = LP.chon_lop_phu(dg, loi, 32.6)
    print(f"  chon_lop_phu -> {len(ra)} lớp phủ · lý do: {ly_do}")
    # TRUY: TỪ KHOÁ NÀO khớp — để biết là khớp ĐÚNG THEO THIẾT KẾ hay TRÙNG MAY
    print("  từ khoá nào khớp lời tiếng Trung:")
    n_kh = 0
    for khoa, l in LP.LUAT.items():
        for nhan, ds, rd in (("MẠNH", l.manh, l._rd_manh),
                             ("PHỤ", l.phu, l._rd_phu),
                             ("CẤM", l.cam, l._rd_cam)):
            for i, tu in enumerate(ds):
                if LP._co(loi, [rd[i]]):
                    n_kh += 1
                    print(f"    {khoa:<12} {nhan:<5} '{tu}'")
    print(f"    -> {n_kh} từ khoá khớp trên {len(loi)} ký tự lời tiếng Trung")

    print("\n══ (e) 2 CỬA CÒN LẠI CÓ ĐỌC CHỮ KHÔNG (đổi NHÃN ngôn ngữ) ══")
    import inspect
    from app.core import ffmpeg_utils as FU
    for mod, ten in ((HU, "chon_hieu_ung"), (FU, "chon_chuyen_canh"),
                     (HU, "chon_tieng_dong")):
        f = getattr(mod, ten, None)
        if f is None:
            print(f"    {ten}: KHÔNG CÓ")
            continue
        ts = list(inspect.signature(f).parameters)
        co_chu = [p for p in ts if p in ("loi", "lang", "ngon_ngu", "text",
                                         "transcript", "language")]
        print(f"    {ten}({', '.join(ts)})")
        print(f"        tham số mang CHỮ/ngôn ngữ: {co_chu or 'KHÔNG CÓ'} -> "
              f"{'có thể lệ thuộc tiếng' if co_chu else 'chấm theo SỐ ĐO, tiếng gì cũng như nhau'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
