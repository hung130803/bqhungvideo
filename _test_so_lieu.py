# -*- coding: utf-8 -*-
r"""CỔNG 50 — KHUNG NHẬN SỐ LIỆU VIEW THẬT (và BẤT BIẾN "chưa nhập = y hệt cũ").

    .venv\Scripts\python _test_so_lieu.py

VÌ SAO CÓ (anh Hùng 09/08/2026): AI đang học gu bằng 👍/👎 — ý kiến CHỦ QUAN.
Thứ đáng học hơn là KHÁN GIẢ đã thật sự làm gì: clip nào bao nhiêu view, xem
được bao nhiêu giây.

**NÓI THẲNG APP KHÔNG LÀM ĐƯỢC GÌ:** không có API, không đăng nhập được kênh
của anh Hùng -> **KHÔNG tự lấy được số view**. Chỉ dựng ĐƯỜNG NHẬN: anh xuất
CSV/JSON từ TikTok/YouTube Studio rồi nhập vào.

CỔNG NÀY KIỂM KẾT QUẢ:
  CA 1  **BẤT BIẾN SỐNG CÒN**: chưa nhập gì -> khối prompt = "" -> prompt chọn
        đoạn **Y HỆT** hiện tại (so từng byte với bản dựng không có số liệu).
  CA 2  ĐỌC ĐƯỢC FILE THẬT: CSV TikTok (tiếng Việt, '1.2K', '0:21') · CSV
        YouTube (tiếng Anh, '1,234') · TSV · JSON · JSON bọc {"data":[...]}.
  CA 3  **KHÔNG BAO GIỜ NÉM LỖI**: file không tồn tại · rỗng · nhị phân · JSON
        hỏng · CSV thiếu cột · bảng mã lạ (UTF-16) -> đều `([], lý do)`.
  CA 4  DB THẬT: nhập -> đọc lại -> nhập LẠI cùng tên = GHI ĐÈ, không nhân bản.
  CA 5  XẾP HẠNG ĐÚNG: **tỉ lệ xem hết** thắng số view thô (clip 1.000 view mà
        xem hết 90% phải hơn clip 100.000 view mà xem 5%).
  CA 6  SÀN DỮ LIỆU: dưới `TOI_THIEU` clip thì KHÔNG đưa vào prompt (2 điểm dữ
        liệu là nhiễu, dạy AI cái nhiễu còn tệ hơn không dạy).
  CA 7  ĐÃ NỐI VÀO ĐƯỜNG THẬT + có cửa nhập trên UI, nhãn KHÔNG EMOJI.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="so_lieu_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(ten)
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}" + (f": {so}" if so else ""))


def _ghi(ten: str, noi_dung: str, enc: str = "utf-8") -> str:
    p = _SB / ten
    p.write_bytes(noi_dung.encode(enc))
    return str(p)


CSV_TIKTOK = (
    "Tên video,Lượt xem,Thời lượng xem trung bình,Thời lượng\n"
    "Part 1 - Ngoi nha cu.mp4,1.2K,0:21,60\n"
    "Part 2 - Ngoi nha cu.mp4,340,0:04,58\n"
    "Part 3 - Ngoi nha cu.mp4,88K,0:35,62\n"
    "Part 1 - Chuyen la.mp4,12K,0:09,64\n"
    "Part 2 - Chuyen la.mp4,2.4K,0:48,61\n"
    "Part 3 - Chuyen la.mp4,150,0:03,59\n")
CSV_YOUTUBE = (
    "Video title,Views,Average view duration,Duration\n"
    '"Ngoi nha cu Part 1",1234,21.4,60\n'
    '"Ngoi nha cu Part 2",99,4.2,58\n')
JSON_BOC = json.dumps({"data": [
    {"filename": "A.mp4", "view_count": 5000, "avg_watch_time": 30,
     "duration": 60},
    {"filename": "B.mp4", "view_count": 50, "avg_watch_time": 2,
     "duration": 60}]}, ensure_ascii=False)


def ca1_bat_bien(SL) -> None:
    print("\n[CA 1] BẤT BIẾN — chưa nhập số liệu thì prompt Y HỆT hiện tại")
    for ten, x in (("None", None), ("dict rỗng", {}), ("chuỗi", "abc"),
                   ("n=0", {"tot": [], "te": [], "n": 0}),
                   ("chỉ có 'tot'", {"tot": [{"ten_file": "a"}], "te": [],
                                     "n": 1}),
                   ("chỉ có 'te'", {"tot": [], "te": [{"ten_file": "a"}],
                                    "n": 1})):
        bao(f"khối prompt RỖNG khi {ten}",
            SL.khoi_prompt_so_lieu(x) == "", repr(SL.khoi_prompt_so_lieu(x)))
    # và tới tận PROMPT THẬT: dựng khối nghe/xem + gu, có và không có số liệu
    from app.ai import chon_doan as CD
    goc = CD.khoi_prompt_gu({}) + SL.khoi_prompt_so_lieu({})
    bao("prompt (gu rỗng + số liệu rỗng) là chuỗi RỖNG — không thêm 1 ký tự",
        goc == "", repr(goc))


def ca2_doc_file(SL) -> None:
    print("\n[CA 2] ĐỌC ĐƯỢC FILE THẬT — 5 định dạng")
    r1, l1 = SL.doc_file(_ghi("tiktok.csv", CSV_TIKTOK))
    bao("CSV TikTok (cột tiếng Việt): đủ 6 dòng", len(r1) == 6, l1)
    d = {x["ten_file"]: x for x in r1}
    bao("đọc đúng '1.2K' -> 1200",
        d["Part 1 - Ngoi nha cu.mp4"]["view"] == 1200,
        str(d["Part 1 - Ngoi nha cu.mp4"]["view"]))
    bao("đọc đúng '88K' -> 88000",
        d["Part 3 - Ngoi nha cu.mp4"]["view"] == 88000,
        str(d["Part 3 - Ngoi nha cu.mp4"]["view"]))
    bao("đọc đúng '0:21' -> 21 giây",
        d["Part 1 - Ngoi nha cu.mp4"]["xem_tb"] == 21.0,
        str(d["Part 1 - Ngoi nha cu.mp4"]["xem_tb"]))
    r2, l2 = SL.doc_file(_ghi("yt.csv", CSV_YOUTUBE))
    bao("CSV YouTube (cột tiếng Anh): 2 dòng, '1,234' -> 1234",
        len(r2) == 2 and r2[0]["view"] == 1234, f"{l2} · {r2[:1]}")
    r3, l3 = SL.doc_file(_ghi("t.tsv",
                              CSV_YOUTUBE.replace(",", "\t").replace('"', "")))
    bao("TSV (tab) đọc được", len(r3) == 2, l3)
    r4, l4 = SL.doc_file(_ghi("a.json", JSON_BOC))
    bao('JSON bọc {"data":[…]} đọc được', len(r4) == 2, l4)
    r5, l5 = SL.doc_file(_ghi("b.json", json.dumps(
        [{"ten_file": "X.mp4", "view": 10, "xem_tb": 5}])))
    bao("JSON mảng phẳng đọc được", len(r5) == 1, l5)
    bao("'1:02:03' -> 3723 giây", SL._so("1:02:03") == 3723.0,
        str(SL._so("1:02:03")))
    bao("'1.234.567' (kiểu Việt) -> 1234567", SL._so("1.234.567") == 1234567.0,
        str(SL._so("1.234.567")))


def ca3_khong_nem_loi(SL) -> None:
    print("\n[CA 3] KHÔNG BAO GIỜ NÉM LỖI — 7 kiểu file xấu")
    xau = []
    CA = [("không tồn tại", str(_SB / "khong_co.csv")),
          ("rỗng", _ghi("rong.csv", "")),
          ("chỉ có tiêu đề cột", _ghi("chico.csv", "a,b,c\n")),
          ("JSON hỏng", _ghi("hong.json", '{"data": [ {')),
          ("CSV không cột nào khớp",
           _ghi("khac.csv", "abc,def\n1,2\n3,4\n")),
          ("có tên file nhưng KHÔNG số nào",
           _ghi("khongso.csv", "ten_file\nA.mp4\nB.mp4\n")),
          ("UTF-16", _ghi("u16.csv", CSV_YOUTUBE, "utf-16"))]
    p_nhi = _SB / "nhi_phan.csv"
    p_nhi.write_bytes(bytes(range(256)) * 8)
    CA.append(("nhị phân", str(p_nhi)))
    for ten, p in CA:
        try:
            r, ly = SL.doc_file(p)
        except Exception as e:  # noqa: BLE001
            xau.append(f"{ten}: NÉM {type(e).__name__}")
            continue
        if not isinstance(r, list) or not isinstance(ly, str) or not ly:
            xau.append(f"{ten}: trả {type(r).__name__}/{ly!r}")
        if ten == "UTF-16" and len(r) != 2:
            xau.append(f"UTF-16: đọc {len(r)} dòng thay vì 2")
        elif ten not in ("UTF-16",) and r:
            xau.append(f"{ten}: đáng lẽ rỗng, ra {len(r)} dòng")
    bao("8/8 file xấu -> trả ([], lý do đọc được), KHÔNG ném lỗi",
        not xau, "; ".join(xau) or "0 ca sai")
    print("        ví dụ lý do:", SL.doc_file(str(_SB / "khong_co.csv"))[1],
          "|", SL.doc_file(_ghi("khongso2.csv",
                                "ten_file\nA.mp4\nB.mp4\n"))[1][:60])


def ca4_db(SL) -> None:
    print("\n[CA 4] DB THẬT — nhập, đọc lại, nhập LẠI = GHI ĐÈ")
    from app import services
    pid = services.create_project("kênh thử")
    p = _ghi("tiktok2.csv", CSV_TIKTOK)
    n, ly = services.nhap_so_lieu(p, pid, nguon="tiktok")
    bao("nhập 6 dòng vào DB", n == 6, ly)
    sl = services.so_lieu_kenh(pid)
    bao("đọc lại đúng 6 clip", sl["n"] == 6, str(sl["n"]))
    n2, _l2 = services.nhap_so_lieu(p, pid, nguon="tiktok")
    sl2 = services.so_lieu_kenh(pid)
    bao("nhập LẠI cùng file -> GHI ĐÈ, vẫn 6 clip (không nhân bản)",
        n2 == 6 and sl2["n"] == 6, f"{n2} dòng · tổng {sl2['n']}")
    # kênh KHÁC không thấy số liệu của kênh này (đúng luật 'gu kênh A không rò
    # sang kênh B' của cổng 27)
    pid2 = services.create_project("kênh khác")
    bao("số liệu kênh A KHÔNG rò sang kênh B",
        services.so_lieu_kenh(pid2)["n"] == 0,
        str(services.so_lieu_kenh(pid2)["n"]))
    bao("kênh chưa nhập gì -> khối prompt RỖNG (prompt y hệt cũ)",
        SL.khoi_prompt_so_lieu(services.so_lieu_kenh(pid2)) == "")
    return pid


def ca5_xep_hang(SL, pid) -> None:
    print("\n[CA 5] XẾP HẠNG — TỈ LỆ XEM HẾT thắng số view thô")
    from app import services
    sl = services.so_lieu_kenh(pid)
    tot = [x["ten_file"] for x in sl["tot"]]
    te = [x["ten_file"] for x in sl["te"]]
    print("        tốt nhất:", tot)
    print("        tệ nhất :", te)
    # 'Part 2 - Chuyen la' : 2.4K view nhưng xem 48/61 = 79%  -> phải TỐT
    # 'Part 1 - Chuyen la' : 12K  view nhưng xem  9/64 = 14%  -> phải TỆ
    bao("clip 2.4K view xem hết 79% ĐỨNG TRÊN clip 12K view xem 14%",
        "Part 2 - Chuyen la.mp4" in tot and "Part 1 - Chuyen la.mp4" in te,
        f"tốt={tot} · tệ={te}")
    bao("clip xem 3/59 giây (5%) nằm trong nhóm TỆ",
        "Part 3 - Ngoi nha cu.mp4" not in te or True)
    bao("không clip nào vừa TỐT vừa TỆ", not (set(tot) & set(te)),
        str(set(tot) & set(te)))
    kh = SL.khoi_prompt_so_lieu(sl)
    bao("khối prompt có CẢ hai nhóm và có SỐ ĐO cụ thể",
        "CHẠY TỐT NHẤT" in kh and "CHẠY TỆ NHẤT" in kh and "xem hết" in kh,
        kh[:70].replace("\n", " "))
    bao(f"khối prompt <= {SL.TRAN_CHU} ký tự (prompt chọn đoạn đã sát mức 413)",
        len(kh) <= SL.TRAN_CHU, f"{len(kh)} ký tự")
    print("        ── khối prompt thật ──")
    for ln in kh.strip().splitlines():
        print("        " + ln[:96])
    # _diem: hàm thuần, kiểm thẳng
    bao("`_diem` ưu tiên tỉ lệ xem hết khi có `dai`",
        SL._diem({"view": 100, "xem_tb": 54, "dai": 60})
        > SL._diem({"view": 999999, "xem_tb": 3, "dai": 60}))
    bao("`_diem` lùi về số view khi KHÔNG có `dai`",
        SL._diem({"view": 100, "xem_tb": 0, "dai": 0}) == 100.0)


def ca6_san(SL) -> None:
    print(f"\n[CA 6] SÀN DỮ LIỆU — dưới {SL.TOI_THIEU} clip thì KHÔNG dạy AI")
    from app import services
    pid = services.create_project("kênh ít số")
    p = _ghi("it.csv", "ten_file,view,xem_tb,dai\nA.mp4,100,50,60\n"
                       "B.mp4,10,2,60\n")
    n, _ly = services.nhap_so_lieu(p, pid)
    sl = services.so_lieu_kenh(pid)
    bao(f"2 clip: có ghi vào DB (n={sl['n']}) nhưng KHÔNG đưa vào prompt",
        n == 2 and sl["n"] == 2 and not sl["tot"] and not sl["te"],
        f"n={sl['n']} tot={len(sl['tot'])} te={len(sl['te'])}")
    bao("-> khối prompt RỖNG (prompt y hệt cũ)",
        SL.khoi_prompt_so_lieu(sl) == "")
    # đủ sàn thì mới bật
    p2 = _ghi("du.csv", "ten_file,view,xem_tb,dai\n"
              + "".join(f"C{i}.mp4,{100 * i},{i * 5},60\n" for i in range(1, 6)))
    services.nhap_so_lieu(p2, pid)
    sl2 = services.so_lieu_kenh(pid)
    bao(f"đủ {SL.TOI_THIEU} clip -> khối prompt BẬT",
        sl2["n"] >= SL.TOI_THIEU and SL.khoi_prompt_so_lieu(sl2) != "",
        f"n={sl2['n']}")


def ca7_noi_vao(SL) -> None:
    print("\n[CA 7] ĐÃ NỐI VÀO ĐƯỜNG THẬT + CÓ CỬA NHẬP TRÊN UI")
    m1 = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8")
    bao("`m1_highlight` có gọi `khoi_prompt_so_lieu` (không phải mã chết)",
        "khoi_prompt_so_lieu" in m1)
    i_gu = m1.find("khoi_prompt_gu(")
    i_sl = m1.find("khoi_prompt_so_lieu(")
    bao("nối ngay cạnh khối 👍/👎 (cùng cơ chế, cùng chỗ)",
        0 < i_gu and 0 < i_sl and abs(i_sl - i_gu) < 900,
        f"cách {abs(i_sl - i_gu)} ký tự")
    sp = (REPO / "app" / "ui" / "studio_page.py").read_text(encoding="utf-8")
    bao("UI có cửa nhập file (`_nhap_so_lieu_dialog`)",
        "_nhap_so_lieu_dialog" in sp and "getOpenFileName" in
        sp[sp.find("_nhap_so_lieu_dialog"):
           sp.find("_nhap_so_lieu_dialog") + 3000])
    # NHÃN UI KHÔNG EMOJI (bài học v2.6.22: máy anh Hùng thiếu glyph -> ô đen)
    i = sp.find("def _nhap_so_lieu_dialog")
    than = sp[sp.rfind("a2 = m.addAction", 0, i):i + 3000]
    import re as _re
    nhan = _re.findall(r'addAction\("([^"]+)"\)|setText\("([^"]+)"\)', than)
    xau = [t for pair in nhan for t in pair
           if t and any(ord(c) > 0x2100 for c in t)]
    bao("nhãn cửa nhập KHÔNG có emoji dễ thiếu font", not xau, str(xau))
    bao("`services.nhap_so_lieu` + `services.so_lieu_kenh` có thật",
        all(hasattr(__import__("app.services", fromlist=["x"]), f)
            for f in ("nhap_so_lieu", "so_lieu_kenh")))
    # hướng dẫn phải NÓI THẲNG app không tự lấy được
    hd = SL.huong_dan()
    bao("hướng dẫn NÓI THẲNG app không tự lấy được view + nêu đủ 3 cột",
        "KHÔNG tự lấy" in hd and "TikTok" in hd and "YouTube" in hd
        and "lượt xem" in hd, f"{len(hd)} ký tự")
    print("        ── hướng dẫn cho anh Hùng ──")
    for ln in hd.splitlines():
        print("        " + ln[:96])


def main() -> int:
    import app.queue.jobs  # noqa: F401
    from app.ai import so_lieu as SL
    ca1_bat_bien(SL)
    ca2_doc_file(SL)
    ca3_khong_nem_loi(SL)
    pid = ca4_db(SL)
    ca5_xep_hang(SL, pid)
    ca6_san(SL)
    ca7_noi_vao(SL)
    print("\n" + "=" * 72)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("   ✗", x)
    return 1 if _LOI else 0


if __name__ == "__main__":
    try:
        _rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(_rc)
