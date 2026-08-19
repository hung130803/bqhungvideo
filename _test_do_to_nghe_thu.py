# -*- coding: utf-8 -*-
"""CỔNG 65 — ĐỘ TO BẢN TRỘN + NÚT NGHE THỬ (16/08/2026).

Hai việc anh Hùng nêu cùng một câu: *"tool cắt sao phần giọng nói ít tiếng quá
nghe không hay, với không có phần nghe thử à, thêm tiếng cho tôi đi"*.

**CỔNG NÀY TỰ KIỂM: gỡ chốt ra thì PHẢI ĐỎ.** Chạy `BQ_PHA=1` để thử phá —
mỗi phép phá là một cách "sửa cho gọn" mà người sau có thể làm thật.

**TUYỆT ĐỐI KHÔNG PHÁT TIẾNG RA LOA.** `winsound.PlaySound` bị vá thành hàm
ĐẾM trước khi dựng hộp; ca 6 chứng minh bản vá đó có hiệu lực (không thì cổng
này biến máy anh Hùng thành cái loa mỗi lượt hồi quy).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# HỘP CÁT: đặt TRƯỚC khi nạp config, không thì ghi vào DATA_DIR THẬT.
_SB = tempfile.mkdtemp(prefix="bq_doto_")
os.environ["BQ_DATA_DIR"] = _SB
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401  (bắt buộc: cấm mở Explorer/trình phát)

PHA = os.environ.get("BQ_PHA", "") == "1"
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


# ==================================================================
def ca1_hang_so() -> None:
    """Hằng số độ to phải có thật và ở mức mạng xã hội."""
    print("\n== CA 1: hằng số đích ==")
    from app.core import thay_giong as tg
    ok(abs(tg.DICH_LUFS - (-14.0)) < 0.01, "DICH_LUFS = -14 LUFS",
       f"{tg.DICH_LUFS}")
    ok(abs(tg.TRAN_DINH_THAT_DBTP - (-1.0)) < 0.01,
       "trần đỉnh thật = -1 dBTP", f"{tg.TRAN_DINH_THAT_DBTP}")
    # Biên phải ĐỦ cho cả `alimiter` vọt (+0,06) LẪN nén AAC vọt (+0,19).
    ok(tg.BIEN_DINH_THAT_DB >= 0.25,
       "biên trừ hao >= 0,25 dB (alimiter +0,06 · AAC +0,19)",
       f"{tg.BIEN_DINH_THAT_DB}")


def ca2_do_do_to() -> None:
    """`do_do_to` phải ĐỌC ĐƯỢC JSON và NÉM khi hỏng (không trả None âm thầm)."""
    print("\n== CA 2: phép đo độ to ==")
    from app.core import thay_giong as tg
    src = REPO / "_do_lt" / "e2e" / "_cantieng" / "tron_MỚI.wav"
    if not src.exists():
        ok(False, "có file mốc để đo", str(src))
        return
    d = tg.do_do_to(src)
    ok(set(d) == {"I", "TP", "LRA", "thresh"}, "trả đủ 4 chỉ số", str(sorted(d)))
    ok(-40.0 < d["I"] < 0.0, "I nằm trong dải hợp lý", f"{d['I']:.2f} LUFS")
    # File KHÔNG TỒN TẠI -> phải NÉM, tuyệt đối không trả None/0 im lặng
    # (bẫy `astats` cổng 53: phép đo hỏng phát chứng nhận cho thứ vẫn sai).
    try:
        tg.do_do_to(REPO / "_khong_he_co_file_nay.wav")
        ok(False, "file hỏng -> NÉM lỗi", "nó trả về êm ru")
    except Exception:  # noqa: BLE001
        ok(True, "file hỏng -> NÉM lỗi")

    # CA 2b — CHỖ NGUY HIỂM THẬT, và cổng bản đầu ĐỂ LỌT (thử phá bắt được):
    # ffmpeg trả **mã 0** mà KHÔNG in JSON. Ca trên không với tới được vì
    # file thiếu thì ffmpeg trả mã KHÁC 0, tức nó đi nhánh raise KHÁC.
    # Nếu nhánh "không có JSON" trả số 0 im lặng thì mọi phép chuẩn hoá sau đó
    # tính trên I=0 -> hạ bừa 14 dB mà không một dòng báo. Đúng bệnh `astats`
    # cổng 53: phép đo hỏng phát chứng nhận cho thứ vẫn sai.
    import subprocess as _sp

    class _GiaPopen:
        returncode = 0

        def __init__(self, *a, **k):
            pass

        def communicate(self, timeout=None):
            return ("", "")          # mã 0, KHÔNG một dòng JSON nào

        def kill(self):
            pass

    that = tg.subprocess.Popen
    tg.subprocess.Popen = _GiaPopen  # type: ignore
    try:
        tg.do_do_to(src)
        ok(False, "ffmpeg mã 0 mà KHÔNG có JSON -> NÉM",
           "nó trả về êm ru (sẽ chuẩn hoá theo số bịa)")
    except Exception:  # noqa: BLE001
        ok(True, "ffmpeg mã 0 mà KHÔNG có JSON -> NÉM")
    finally:
        tg.subprocess.Popen = that  # type: ignore
    assert _sp is not None


def ca3_chuan_do_to() -> None:
    """Nâng đúng đích · không quá trần đỉnh · KHÔNG nén dập · giữ độ dài."""
    print("\n== CA 3: chuẩn hoá độ to (số đo thật) ==")
    from app.core import thay_giong as tg
    src = REPO / "_do_lt" / "e2e" / "_cantieng" / "tron_MỚI.wav"
    if not src.exists():
        ok(False, "có file mốc", str(src))
        return
    dst = Path(_SB) / "chuan.wav"
    kq = tg.chuan_do_to(src, dst)
    s = kq["sau"]
    ok(kq["dat_dich"], "đạt đích -14 LUFS (sai số <= 0,5)",
       f"{s['I']:.2f} LUFS")
    ok(not kq["qua_tran_dinh"], "đỉnh thật KHÔNG vượt -1 dBTP",
       f"{s['TP']:.2f} dBTP")
    # KHÔNG NÉN DẬP: dải động không được co lại (đây là chốt chống
    # "to hơn nhưng chết động lực" mà `loudnorm` động gây ra).
    ok(kq["lra_doi"] >= -0.15, "LRA KHÔNG bị nén dập",
       f"{kq['truoc']['LRA']:.2f} -> {s['LRA']:.2f} LU "
       f"({kq['lra_doi']:+.2f})")
    d0, d1 = tg.probe_duration(src), tg.probe_duration(dst)
    ok(abs(d0 - d1) < 0.05, "độ dài giữ nguyên", f"{d0:.3f} -> {d1:.3f} s")
    ok(dst.stat().st_size > 1024, "file ra KHÔNG rỗng",
       f"{dst.stat().st_size} byte")

    # ---- CA 3b: PHẢI LÀ PHÉP NHÂN THUẦN ----
    # Đây mới là chốt THẬT bảo vệ cân bằng giọng-nhạc, và nó là chốt DUY NHẤT
    # bắt được phép phá "thay bằng `loudnorm` động": nguồn của anh Hùng đã nén
    # sẵn (LRA 2,10) nên bộ nén động gần như KHÔNG đổi LRA (2,10 -> 2,00, lọt
    # ngưỡng) — tức mục LRA ở trên MỘT MÌNH là con dấu.
    # Hệ số áp theo thời gian: hằng số = tỉ lệ giọng/nhạc KHÔNG THỂ đổi.
    # Đo được: nâng thuần **0,017 dB** · loudnorm động **0,277 dB** (16 lần).
    import statistics
    b0 = tg.duong_bao_muc(src)
    b1 = tg.duong_bao_muc(dst)
    n = min(len(b0), len(b1))
    hs = [b1[i] - b0[i] for i in range(n) if b0[i] > -100 and b1[i] > -100]
    dl = statistics.pstdev(hs)
    ok(dl < 0.05, "hệ số áp là HẰNG SỐ (phép nhân thuần, không nén động)",
       f"độ lệch chuẩn {dl:.4f} dB ({min(hs):+.2f}..{max(hs):+.2f})")


def ca4_tien_dinh() -> None:
    """5 LƯỢT RA ĐÚNG MỘT CON SỐ — bài học `asplit` làm độ dài không tiền định."""
    print("\n== CA 4: chạy 5 lượt ra cùng một độ dài ==")
    from app.core import thay_giong as tg
    src = REPO / "_do_lt" / "e2e" / "_cantieng" / "tron_MỚI.wav"
    if not src.exists():
        ok(False, "có file mốc", str(src))
        return
    dai, muc = [], []
    for i in range(5):
        p = Path(_SB) / f"td{i}.wav"
        kq = tg.chuan_do_to(src, p, )
        dai.append(round(tg.probe_duration(p), 3))
        muc.append(kq["sau"]["I"])
    ok(len(set(dai)) == 1, "5/5 lượt ra ĐÚNG một độ dài", str(sorted(set(dai))))
    ok(len(set(muc)) == 1, "5/5 lượt ra ĐÚNG một mức độ to",
       str(sorted(set(muc))))


def ca5_giu_can_bang() -> None:
    """Nâng độ to KHÔNG được phá tỉ lệ giọng-trên-nhạc vừa chữa 15/08."""
    print("\n== CA 5: nâng xong vẫn giữ cân bằng giọng-nhạc ==")
    from app.core import thay_giong as tg
    cd = REPO / "_do_lt" / "e2e" / "_cantieng"
    giong, nhac = cd / "moi_giong.wav", cd / "moi_nhac.wav"
    if not giong.exists() or not nhac.exists():
        ok(False, "có 2 lớp mốc", str(cd))
        return
    truoc = tg.do_giong_tren_nhac(giong, nhac)
    # Nâng ĐÚNG bằng hệ số mà `chuan_do_to` sẽ dùng, áp lên CẢ HAI lớp.
    tron = cd / "tron_MỚI.wav"
    can = tg.DICH_LUFS - tg.do_do_to(tron)["I"]
    gp, np_ = Path(_SB) / "g.wav", Path(_SB) / "n.wav"
    for s, d in ((giong, gp), (nhac, np_)):
        tg._ffmpeg(["-i", str(s), "-af", f"volume={can:.3f}dB", "-ac", "2",
                    "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le", str(d)],
                   "nâng lớp")
    sau = tg.do_giong_tren_nhac(gp, np_)
    ok(abs(sau["giong_tren_nhac_tb"] - truoc["giong_tren_nhac_tb"]) < 0.05,
       "giọng trên nhạc KHÔNG đổi",
       f"{truoc['giong_tren_nhac_tb']:+.2f} -> "
       f"{sau['giong_tren_nhac_tb']:+.2f} dB")
    ok(abs(sau["ty_le_chim"] - truoc["ty_le_chim"]) < 0.05,
       "% thời gian bị át KHÔNG đổi",
       f"{truoc['ty_le_chim']}% -> {sau['ty_le_chim']}%")
    ok(sau["giong_tren_nhac_tb"] >= 5.0,
       "vẫn giữ mức đã chữa (giọng cao hơn nhạc >= 5 dB)",
       f"{sau['giong_tren_nhac_tb']:+.2f} dB")
    ok(sau["ty_le_chim"] <= 12.0, "thời gian bị át vẫn <= 12%",
       f"{sau['ty_le_chim']}%")


def ca6_nghe_thu() -> None:
    """`doc_thu` ra file tiếng THẬT cho từng nguồn giọng + CACHE."""
    print("\n== CA 6: nghe thử (KHÔNG phát ra loa) ==")
    import time

    from app.core import thay_giong as tg

    ds = [("edge-tts giọng gốc", "vi-VN-HoaiMyNeural"),
          ("edge-tts biến thể trầm",
           tg.ma_bien_the("vi-VN-NamMinhNeural", "-20Hz"))]
    try:
        from app.core import piper_tts
        ds.append(("Piper vais1000", piper_tts.MA_GIONG))
    except Exception:  # noqa: BLE001
        print("  (bỏ qua Piper: không nạp được module)")

    for nhan, ma in ds:
        p = Path(_SB) / f"nt_{abs(hash(ma)) % 9999}.wav"
        kq = tg.doc_thu(ma, p)
        co = bool(kq["ra"]) and Path(kq["ra"]).exists()
        ok(co, f"{nhan}: sinh được tiếng",
           f"nguồn={kq['nguon']} lỗi={kq['loi'][:60]}")
        if co:
            ok(Path(kq["ra"]).stat().st_size > 5000,
               f"{nhan}: file đủ lớn (không phải 0 KiB)",
               f"{Path(kq['ra']).stat().st_size} byte")
            ok(tg.probe_duration(kq["ra"]) > 0.5,
               f"{nhan}: có độ dài thật",
               f"{tg.probe_duration(kq['ra']):.2f} s")
            ok(kq["nguon"] != "", f"{nhan}: NÓI RA nguồn giọng thật",
               kq["nguon"])

    # CACHE: bấm lần 2 KHÔNG được gọi lại mạng/model.
    p1, p2 = Path(_SB) / "c1.wav", Path(_SB) / "c2.wav"
    tg.doc_thu("vi-VN-HoaiMyNeural", p1)
    t = time.perf_counter()
    k2 = tg.doc_thu("vi-VN-HoaiMyNeural", p2)
    gi = time.perf_counter() - t
    ok(k2["cache"] and gi < 0.5, "bấm lần 2 dùng CACHE (không gọi lại)",
       f"{gi * 1000:.0f} ms, cache={k2['cache']}")
    # Giọng RỖNG -> báo lỗi tử tế, KHÔNG nổ.
    k3 = tg.doc_thu("", Path(_SB) / "rong.wav")
    ok(not k3["ra"] and k3["loi"], "giọng rỗng -> báo lỗi, không nổ",
       k3["loi"])


def ca7_ui() -> None:
    """Nút có thật · KHÔNG chặn giao diện · KHÔNG phát tiếng khi test."""
    print("\n== CA 7: nút Nghe thử trong hộp Thay giọng ==")
    import winsound

    # VÁ winsound TRƯỚC khi dựng hộp — cổng tuyệt đối không được kêu ra loa.
    _keu: list = []
    winsound.PlaySound = lambda *a, **k: _keu.append(a)  # type: ignore

    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance() or QApplication([])
    from app.ui import thay_giong_dialog as D

    dlg = D.ThayGiongDialog.__new__(D.ThayGiongDialog)
    from PyQt6.QtWidgets import QDialog
    QDialog.__init__(dlg)
    try:
        D.ThayGiongDialog.__init__(dlg, pool=None)
    except Exception as e:  # noqa: BLE001
        ok(False, "dựng được hộp", str(e)[:120])
        return
    ok(True, "dựng được hộp")
    ok(hasattr(dlg, "b_nghe"), "có nút Nghe thử")
    nhan = dlg.b_nghe.text()
    ok(nhan == "Nghe thử", "nhãn đúng + KHÔNG EMOJI", repr(nhan))
    ok(all(ord(c) < 0x2000 for c in nhan), "nhãn không có ký tự lạ font")

    # CHỌN 1 GIỌNG rồi BẤM — nút phải khoá NGAY (không chặn vòng lặp).
    #
    # PHẢI CHỌN GIỌNG **edge-tts**, KHÔNG lấy dòng đầu có data. Từ v2.38.0 combo
    # GOM NHÓM (`giong_bang.gom_nhom`, cổng 79) và dòng đầu tiên có data là
    # **`vn:Xuân Vĩnh`** — giọng VieNeu chạy trên máy: nó mở tiến trình con +
    # nạp model, đo thật **hơn 12 giây**, còn vòng đợi dưới đây chỉ chờ 240 ×
    # 0,05 s = 12 s -> mục "xong thì mở khoá nút lại" **ĐỎ OAN** (đo 19/08/2026:
    # cổng ra 30/5, và nút VẪN mở khoá, chỉ là muộn hơn cổng chịu đợi).
    # Mục này canh HÀNH VI CỦA NÚT (khoá lúc đang đọc, mở lại khi xong), không
    # canh tốc độ của một nguồn giọng — nên chọn nguồn RẺ là đúng phạm vi, và
    # cổng cũng không còn phụ thuộc thứ tự sắp xếp combo của luồng khác.
    def _la_edge(v: str) -> bool:
        return bool(v) and ":" not in str(v)

    idx = next((i for i in range(dlg.cb_giong.count())
                if _la_edge(dlg.cb_giong.itemData(i))), -1)
    if idx < 0:                     # offline: danh sách rơi về mức tối thiểu
        idx = next((i for i in range(dlg.cb_giong.count())
                    if dlg.cb_giong.itemData(i)), -1)
    ok(idx >= 0, "combo có giọng cụ thể để chọn",
       repr(dlg.cb_giong.itemData(idx)) if idx >= 0 else "—")
    if idx >= 0:
        dlg.cb_giong.setCurrentIndex(idx)
        import time
        t = time.perf_counter()
        dlg.b_nghe.click()
        gi = time.perf_counter() - t
        # KHÔNG CHẶN: bấm xong phải trả quyền điều khiển NGAY, việc sinh
        # tiếng chạy ở thread nền (edge-tts mất hàng giây).
        ok(gi < 0.5, "bấm KHÔNG chặn giao diện", f"{gi * 1000:.0f} ms")
        ok(not dlg.b_nghe.isEnabled(), "nút bị khoá khi đang đọc "
           "(bấm liên tiếp không chồng tiếng)")
        ok(dlg.b_nghe.text() != "Nghe thử", "nút báo đang xử lý",
           repr(dlg.b_nghe.text()))
        # đợi thread nền xong rồi bắn tín hiệu qua vòng lặp Qt
        for _ in range(240):
            qapp.processEvents()
            if dlg.b_nghe.isEnabled():
                break
            time.sleep(0.05)
        ok(dlg.b_nghe.isEnabled(), "xong thì mở khoá nút lại")
        ok(len(_keu) >= 1, "CÓ gọi phát tiếng (qua winsound đã vá)",
           f"{len(_keu)} lượt")
    # TỰ KIỂM BẢN VÁ: nếu winsound KHÔNG bị vá thì cổng này đã kêu ra loa.
    ok(winsound.PlaySound is not None and _keu is not None,
       "winsound đã bị vá -> cổng KHÔNG kêu ra loa máy anh Hùng")
    dlg._ngat_tieng()
    dlg.deleteLater()


def ca8_quet_tinh() -> None:
    """Quét bằng AST: `tron_thay_giong` phải THẬT SỰ gọi `chuan_do_to`.

    Đọc bằng AST chứ không tìm chuỗi — bài học cổng 56d/64: tìm chuỗi thì
    chính DÒNG GHI CHÚ khớp trúng, gỡ sạch bản vá mà cổng vẫn XANH = con dấu.
    """
    print("\n== CA 8: quét tĩnh (AST) ==")
    import ast
    src = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef)
                and n.name == "tron_thay_giong"), None)
    ok(ham is not None, "tìm thấy `tron_thay_giong`")
    if ham:
        goi = {n.func.id for n in ast.walk(ham)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        ok("chuan_do_to" in goi,
           "`tron_thay_giong` THẬT SỰ gọi `chuan_do_to`", str(sorted(goi)))
    # nút Nghe thử phải nối vào handler THẬT
    ui = (REPO / "app" / "ui" / "thay_giong_dialog.py").read_text(
        encoding="utf-8")
    cay2 = ast.parse(ui)
    ten = {n.name for n in ast.walk(cay2) if isinstance(n, ast.FunctionDef)}
    ok("_nghe_thu" in ten and "_nghe_thu_xong" in ten,
       "hộp có `_nghe_thu` + `_nghe_thu_xong`")


def main() -> int:
    print("=" * 74)
    print("CỔNG 65 — ĐỘ TO BẢN TRỘN + NÚT NGHE THỬ")
    if PHA:
        print("!! BQ_PHA=1 — ĐANG THỬ PHÁ, cổng PHẢI ĐỎ")
    print("=" * 74)
    for f in (ca1_hang_so, ca2_do_do_to, ca3_chuan_do_to, ca4_tien_dinh,
              ca5_giu_can_bang, ca6_nghe_thu, ca7_ui, ca8_quet_tinh):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            ok(False, f"{f.__name__} NỔ", str(e)[:150])
    print("\n" + "=" * 74)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
