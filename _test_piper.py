# -*- coding: utf-8 -*-
"""CỔNG 64 — PIPER LÀM LỰA CHỌN THỨ HAI (16/08/2026).

Anh Hùng chê edge-tts "đọc đều đều" và chỉ có 2 giọng Việt cho 200-300 kênh.
Piper thêm MỘT giọng nữa, chạy hẳn trên máy. Nhưng nó **KHÔNG thay** edge-tts:
đo được nhấn nhá Piper **3,24** so với edge-tts **3,96 / 3,40** — đổi hẳn sang
Piper là đi lùi ở đúng cái anh ấy đang chê.

CỔNG NÀY CANH 6 MỆNH ĐỀ:

 1. **RANH GIỚI GIẤY PHÉP** — `piper-tts` là GPL-3.0. App là phần mềm ĐÓNG.
    Gọi như CHƯƠNG TRÌNH RỜI thì không sao; **`import piper` một dòng thôi là
    mất quyền giữ kín mã**. Quét bằng `tokenize` (bỏ COMMENT + STRING) vì
    chính docstring của `piper_tts.py` có chứa mấy chữ đó để cảnh báo người
    sau — quét bằng `in` cả file là ĐỎ OAN VĨNH VIỄN (bài học cổng 47/51/54).

 2. **THIẾU PIPER PHẢI LÙI ÊM VỀ edge-tts, KHÔNG ĐƯỢC NỔ.**

 3. **CHỈ `vais1000` ĐƯỢC CÓ MẶT.** `vivos` cấm thương mại (CC BY-NC-SA) +
    thiếu dấu thanh; `25hours_single` giấy phép "Unknown" — im lặng KHÔNG
    phải là cho phép.

 4. **CẢ 3 CHỖ GỌI `_synth_all_words` PHẢI ĐI QUA PIPER** khi chọn giọng
    Piper. Sót một chỗ = video **lẫn hai giọng** mà mã thoát vẫn 0 (đúng mệnh
    đề cổng 63). Cổng này gọi THẬT cả 3 hàm rồi ĐẾM, không quét chuỗi —
    "quét tĩnh bao nhiêu cũng có đường vòng".

 5. **MỐC TỪNG CHỮ RA THẬT** và không bao giờ gán nhầm chữ.

 6. **`length_scale` BÃO HOÀ** — ghi lại giới hạn bằng số đo, vì app cần ép
    tiếng vừa khung.

    .venv\\Scripts\\python -u _test_piper.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import time
import tokenize
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
_RAC: list[Path] = []


def kiem(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def hop_cat(ten: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"bq_piper_{ten}_"))
    _RAC.append(d)
    return d


def don_rac() -> None:
    for d in _RAC:
        shutil.rmtree(d, ignore_errors=True)


def ma_that(p: Path) -> str:
    """Mã nguồn BỎ chú thích + chuỗi.

    Bắt buộc: `piper_tts.py` cố ý viết `import piper` trong docstring để cảnh
    báo. Quét bằng `in` cả file thì chính lời cảnh báo bị kể là vi phạm.
    """
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
        ra = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
        return " ".join(ra)
    except Exception:  # noqa: BLE001
        return ""


# =====================================================================
def ca1_giay_phep() -> None:
    """MỆNH ĐỀ 1 — không một dòng mã THẬT nào nhúng Piper vào tiến trình app."""
    print("\nCA 1 — RANH GIỚI GIẤY PHÉP (GPL): Piper phải là CHƯƠNG TRÌNH RỜI")
    xau = []
    for py in sorted((REPO / "app").rglob("*.py")):
        m = ma_that(py)
        if not m:
            continue
        # `import piper` / `from piper import` — CHỈ gói GPL, KHÔNG phải
        # `app.core.piper_tts` (module của mình, tên có chữ piper).
        for mau in ("import piper ", "from piper import", "from piper."):
            if mau in m + " ":
                xau.append(f"{py.relative_to(REPO)}: {mau.strip()}")
    kiem("1a KHÔNG file nào trong app/ `import piper` (mã GPL)",
         not xau, f"{xau}" if xau else "0/  đã quét "
         f"{sum(1 for _ in (REPO / 'app').rglob('*.py'))} file")

    from app.core import piper_tts as PT
    m = ma_that(Path(PT.__file__))
    kiem("1b `piper_tts.py` KHÔNG chèn `_piper` vào `sys.path` của app",
         "sys.path" not in m, "sạch" if "sys.path" not in m else "CÓ ĐỤNG")
    # `find_spec` phải NẠP gói cha -> chạm mã GPL trong tiến trình app
    kiem("1c dò 'đã cài chưa' bằng FILE, KHÔNG bằng `find_spec`/`import_module`",
         "find_spec" not in m and "import_module" not in m)
    kiem("1d mọi lượt gọi Piper đều là `subprocess` có `timeout`",
         "subprocess" in m and "timeout" in m)
    # TỰ KIỂM BỘ DÒ: bộ dò phải KÊU khi thật sự có dòng cấm
    thu = hop_cat("dodo") / "x.py"
    thu.write_text('"""import piper trong chú thích"""\nimport os\n',
                   encoding="utf-8")
    sach = "import piper " not in ma_that(thu) + " "
    thu.write_text("import piper\n", encoding="utf-8")
    ban = "import piper " in ma_that(thu) + " "
    kiem("1e TỰ KIỂM bộ dò: bỏ qua chú thích NHƯNG bắt được mã thật",
         sach and ban, f"chú thích->bỏ qua {sach} · mã thật->bắt {ban}")


# =====================================================================
def ca2_chi_vais1000() -> None:
    """MỆNH ĐỀ 3 — hai giọng cấm không được lọt vào bất cứ đâu."""
    print("\nCA 2 — CHỈ `vais1000`; `vivos` và `25hours_single` bị CẤM")
    from app.core import piper_tts as PT
    kiem("2a mã giọng đúng `vais1000`", "vais1000" in PT.MA_GIONG, PT.MA_GIONG)
    kiem("2b nhãn tiếng Việt, KHÔNG EMOJI",
         not any(ord(c) > 0x2100 for c in PT.NHAN_GIONG), PT.NHAN_GIONG)

    # quét MÃ THẬT của cả app: hai tên cấm không được là giá trị chạy được
    lot = []
    for py in sorted((REPO / "app").rglob("*.py")):
        m = ma_that(py)
        for cam in ("vivos", "25hours_single"):
            if cam in m:
                lot.append(f"{py.relative_to(REPO)}:{cam}")
    kiem("2c KHÔNG mã nào nhắc `vivos`/`25hours_single` (chỉ được nằm trong "
         "chú thích giải thích vì sao cấm)", not lot, f"{lot}" if lot else "sạch")

    # combo: đúng MỘT dòng Piper
    import _test_guard  # noqa: F401  (luật: cổng đụng UI phải import)
    from app.ui.thay_giong_dialog import giong_dung_duoc
    vao = [("Tiếng Việt", ""),
           ("Nam - Nam Minh", "vi-VN-NamMinhNeural"),
           ("Nu - Hoai My", "vi-VN-HoaiMyNeural"),
           ("Tieng Anh", ""),
           ("Andrew", "en-US-AndrewNeural")]
    ra = giong_dung_duoc(vao)
    ma = [v for _n, v in ra if v]
    pip = [v for v in ma if v.startswith(PT.TIEN_TO)]
    kiem("2d combo có ĐÚNG 1 giọng Piper", len(pip) == 1, f"{pip}")
    kiem("2e giọng edge-tts CŨ vẫn còn nguyên (Piper là THÊM, không THAY)",
         "vi-VN-NamMinhNeural" in ma and "vi-VN-HoaiMyNeural" in ma
         and "en-US-AndrewNeural" in ma)
    kiem("2f không mã trùng", len(set(ma)) == len(ma), f"{len(ma)} mã")
    kiem("2g nhãn combo KHÔNG EMOJI",
         not any(ord(c) > 0x2100 for n, _v in ra for c in n))
    # Piper KHÔNG chỉnh được cao độ -> không được đẻ biến thể `|<pitch>`
    from app.core import thay_giong as TG
    kiem("2h Piper KHÔNG sinh biến thể cao độ (máy đọc này không có pitch)",
         TG.bien_the_giong(PT.MA_GIONG) == []
         and not any(v.startswith(PT.TIEN_TO) and "|" in v for v in ma))
    kiem("2i mã Piper đi qua `tach_giong_pitch` NGUYÊN VẸN",
         TG.tach_giong_pitch(PT.MA_GIONG) == (PT.MA_GIONG, "+0Hz"),
         f"{TG.tach_giong_pitch(PT.MA_GIONG)}")


# =====================================================================
def ca3_thieu_piper_lui_em() -> None:
    """MỆNH ĐỀ 2 — thiếu Piper thì LÙI ÊM, không ném, không đứng."""
    print("\nCA 3 — THIẾU PIPER -> LÙI ÊM VỀ edge-tts (không nổ)")
    from app.core import dubbing
    from app.core import piper_tts as PT

    trong = hop_cat("trong")            # thư mục RỖNG = máy chưa tải Piper
    goc = PT.thu_muc_piper
    PT.thu_muc_piper = lambda: trong
    try:
        tt = PT.tinh_trang_piper()
        kiem("3a máy chưa tải -> `co_piper()` = False",
             PT.co_piper() is False and not tt["co"], f"thiếu {tt['thieu'][:3]}")

        # cửa rẽ phải trả (False, giọng edge-tts) — KHÔNG ném
        try:
            dung, lui = dubbing._piper_hay_khong(PT.MA_GIONG)
            no = False
        except Exception as e:  # noqa: BLE001
            dung, lui, no = True, f"NÉM {e}", True
        kiem("3b thiếu Piper -> KHÔNG dùng Piper, KHÔNG ném", not no and not dung)
        kiem("3c ... và lùi về ĐÚNG giọng edge-tts hợp lệ",
             isinstance(lui, str) and lui.startswith("vi-") and "|" not in lui,
             f"{lui}")
        kiem("3d giọng KHÔNG phải Piper thì cửa rẽ trả NGUYÊN VẸN "
             "(bất biến: đường cũ không đổi một ký tự)",
             dubbing._piper_hay_khong("vi-VN-NamMinhNeural")
             == (False, "vi-VN-NamMinhNeural"))

        # lùi phải ĐỂ LẠI DẤU VẾT — lùi êm mà im lặng = hỏng âm thầm
        import config
        nk = Path(getattr(config, "DATA_DIR", ".")) / "logs"
        truoc = set(nk.glob("piper_*.log")) if nk.is_dir() else set()
        co_dong = False
        f_log = nk / f"piper_{time.strftime('%Y%m%d')}.log"
        n0 = f_log.stat().st_size if f_log.exists() else 0
        dubbing._piper_hay_khong(PT.MA_GIONG)
        if f_log.exists() and f_log.stat().st_size > n0:
            co_dong = True
        kiem("3e lượt lùi có GHI LÝ DO vào logs/piper_<ngày>.log",
             co_dong, str(f_log) if co_dong else "KHÔNG ghi gì")
        del truoc
    finally:
        PT.thu_muc_piper = goc

    kiem("3f gỡ vá xong máy này vẫn thấy Piper (hộp cát không rò)",
         PT.co_piper() is True)


# =====================================================================
def ca4_ba_cho_goi() -> None:
    """MỆNH ĐỀ 4 — CẢ BA chỗ gọi TTS của `thay_giong.py` phải tới Piper.

    Gọi THẬT từng hàm rồi ĐẾM số lượt Piper được dùng. Quét chuỗi không đủ:
    "quét tĩnh bao nhiêu cũng có đường vòng" — và bản đầu của cổng 56 CA19a
    đã sập đúng kiểu đó (đổi `che_chu=False` mà cổng vẫn xanh).
    """
    print("\nCA 4 — CẢ 3 CHỖ GỌI `_synth_all_words` ĐỀU TỚI PIPER")
    from app.core import piper_tts as PT
    from app.core import thay_giong as TG

    dem = {"n": 0, "giong": []}
    that = PT.doc_loat

    def dem_lai(texts, paths, **kw):
        dem["n"] += 1
        return that(texts, paths, **kw)

    PT.doc_loat = dem_lai
    # `rut_gon_vua_khung` gọi LLM -> chặn lại, cổng này không đo phần dịch
    rg_that = TG._rut_gon_loat
    TG._rut_gon_loat = lambda muc, nn: [str(m["text"])[:14] for m in muc]
    try:
        d = hop_cat("ba_cho")
        texts = ["Hôm nay tôi kể các bạn nghe một chuyện rất lạ và dài dòng.",
                 "Con đường quen thuộc gần nhà bỗng khác hẳn mọi khi rồi đó."]
        # khung CỐ Ý CHẬT để ép cả `rut_gon` lẫn `doc_nhanh` phải đọc lại
        cau = [{"start": 0.0, "end": 1.0}, {"start": 1.0, "end": 2.0}]
        tong = 2.0

        # --- chỗ 1: doc_ban_dich ---
        n0 = dem["n"]
        tts = TG.doc_ban_dich(texts, d / "b1", voice=PT.MA_GIONG,
                              dich_sang="vi")
        kiem("4a `doc_ban_dich` đi qua Piper", dem["n"] > n0,
             f"{dem['n'] - n0} lượt · ok={tts['ok']}")
        kiem("4b ... và ra file tiếng THẬT (có khung hình âm, không phải "
             "file 0 KiB)",
             all(Path(f).exists() and PT.dai_wav(f) > 0.2
                 for f, o in zip(tts["files"], tts["ok"]) if o),
             f"{[round(PT.dai_wav(f), 2) for f in tts['files']]}")

        # --- chỗ 2: rut_gon_vua_khung ---
        n0 = dem["n"]
        rg = TG.rut_gon_vua_khung(cau, texts, tts, tong, d / "b2", "vi",
                                  voice=PT.MA_GIONG)
        kiem("4c `rut_gon_vua_khung` đi qua Piper", dem["n"] > n0,
             f"{dem['n'] - n0} lượt · sửa {rg['so_sua']} câu")

        # --- chỗ 3: doc_nhanh_vua_khung ---
        # DÙNG BẢN CHƯA RÚT GỌN, không dùng `rg`: bước rút gọn vừa làm câu
        # lọt khung nên `doc_nhanh` sẽ THOÁT SỚM (`xau` rỗng) và chẳng gọi TTS
        # lần nào — lúc đó cổng đo phải mục KHÔNG CHẠY TỚI CHỐT chứ không đo
        # được cái nó định đo. Đây đúng bẫy "cổng đạt oan vì lượt chạy chết
        # trước khi tới chốt" (cổng 55 CA4 · 62 CA4), lần này nó ra HỎNG nên
        # lộ ngay.
        n0 = dem["n"]
        dn = TG.doc_nhanh_vua_khung(cau, texts, tts["files"], tts["ok"],
                                    tong, d / "b3", "vi", voice=PT.MA_GIONG,
                                    moc_tu=tts.get("moc_tu"))
        kiem("4d `doc_nhanh_vua_khung` đi qua Piper", dem["n"] > n0,
             f"{dem['n'] - n0} lượt · đọc lại {dn['so_doc_lai']} câu")
        kiem("4d2 ... và nó THẬT SỰ phải đọc lại (chốt có được chạm tới)",
             dn["so_doc_lai"] > 0 or dem["n"] > n0,
             f"đọc lại {dn['so_doc_lai']} câu")
        kiem("4e TỔNG: cả 3 chỗ đều tới Piper (sót 1 chỗ = video LẪN HAI "
             "GIỌNG mà mã thoát vẫn 0)", dem["n"] >= 3, f"{dem['n']} lượt")
    finally:
        PT.doc_loat = that
        TG._rut_gon_loat = rg_that


# =====================================================================
def ca5_moc_tung_chu() -> None:
    """MỆNH ĐỀ 5 — mốc ra THẬT, và thà KHÔNG có còn hơn gán nhầm chữ."""
    print("\nCA 5 — MỐC TỪNG CHỮ")
    from app.core import piper_tts as PT
    d = hop_cat("moc")
    # câu CỐ Ý có `con` (tên THIẾT BỊ Windows -> Piper ghi ra `con_.wav`),
    # dấu chấm cuối (`giờ.` -> Windows nuốt dấu chấm) và chữ LẶP
    texts = ["Con đường gần nhà tôi giờ.",
             "Tôi đi bộ trên con đường đó tới tận bây giờ."]
    ps = [str(d / f"c{i}.wav") for i in range(len(texts))]
    t0 = time.time()
    ok, moc = PT.doc_loat(texts, ps)
    gy = time.time() - t0
    kiem("5a đọc được cả 2 câu", all(ok), f"{ok} · {gy:.2f}s")
    kiem("5b mốc ra ĐÚNG SỐ TỪ của từng câu",
         all(len(m) == len(t.split()) for m, t in zip(moc, texts)),
         f"{[len(m) for m in moc]} vs {[len(t.split()) for t in texts]}")
    kiem("5c mốc TĂNG DẦN, không chồng nhau",
         all(all(m[i][1] <= m[i + 1][0] + 1e-6 for i in range(len(m) - 1))
             for m in moc if m))
    # mốc cuối PHẢI bằng độ dài WAV thật — đây là chỗ `_co_gian` làm việc
    lech = [abs(m[-1][1] - PT.dai_wav(p)) for m, p in zip(moc, ps) if m]
    kiem("5d mốc cuối khớp ĐỘ DÀI TIẾNG THẬT (co giãn có chạy)",
         all(x < 0.02 for x in lech), f"lệch tối đa {max(lech) * 1000:.1f} ms")

    # --- `_co_gian` phải NHẢY QUA chỗ nghỉ giữa câu, không rải đều lên mọi
    # chữ. Câu dưới CỐ Ý có 2 dấu phẩy: Piper nghỉ đúng ở đó (đo được 3 khoảng
    # 100-140 ms = 4,8% câu), và rải đều chỗ nghỉ ấy chính là lỗi +33,0 ms.
    #
    # THỬ LẠI TỚI 3 LƯỢT, CÓ LÝ DO: Piper là VITS, bộ dự đoán độ dài của nó
    # CÓ NHIỄU -> chỗ nghỉ KHÔNG cố định giữa các lượt. Đo 4 lượt/câu:
    # câu 3 dấu phẩy ra nghỉ **4/4 lượt** (2-3 chỗ, 269-359 ms), câu 2 dấu
    # phẩy **4/4** nhưng có lượt ra 0 -> chốt một lượt duy nhất là cổng ĐỎ
    # NHẤP NHÁY. (Ghi thêm: dấu CHẤM giữa dòng ra **0/4** — Piper chỉ nghỉ ở
    # dấu PHẨY, đừng dùng dấu chấm làm câu thử.)
    d2 = hop_cat("nghi")
    cau_nghi = ("Hôm nay, tôi sẽ chia sẻ với các bạn một câu chuyện rất thú "
                "vị, mà tôi đã gặp cách đây ba phút, khi đang đi bộ trên "
                "con đường quen thuộc gần nhà mình.")
    ok2, moc2, kh, tong2, im_giua = [False], [[]], [], 0.0, 0.0
    for _lan in range(3):
        p2 = str(d2 / f"nghi{_lan}.wav")
        ok2, moc2 = PT.doc_loat([cau_nghi], [p2])
        kh, tong2 = PT.khoang_co_tieng(p2)
        im_giua = tong2 - sum(e - s for s, e in kh)
        if len(kh) >= 2 and im_giua > 0.05:
            break
    # TỰ KIỂM BỘ DÒ TRƯỚC ĐÃ: không có chỗ nghỉ nào thì cách cũ và cách mới ra
    # Y HỆT nhau, mọi mục dưới sẽ XANH OAN. Đây đúng bẫy "cổng đạt oan vì lượt
    # chạy chết trước khi tới chốt" (cổng 55 CA4 · 62 CA4).
    kiem("5i TỰ KIỂM: câu thử THẬT SỰ có chỗ nghỉ giữa câu (không có thì mọi "
         "mục dưới xanh oan)", len(kh) >= 2 and im_giua > 0.05,
         f"{len(kh)} khoảng có tiếng · im giữa câu {im_giua * 1000:.0f} ms "
         f"· {[f'{s:.2f}-{e:.2f}' for s, e in kh]}")
    m2 = moc2[0] if moc2 and moc2[0] else []
    kiem("5j mốc ra được cho câu có chỗ nghỉ", bool(m2) and ok2 == [True],
         f"{len(m2)} mốc")
    if m2 and len(kh) >= 2:
        # KHÔNG chữ nào được nằm GỌN trong một chỗ nghỉ
        nghi = [(kh[i][1], kh[i + 1][0]) for i in range(len(kh) - 1)]
        trong_nghi = [w for a, b, w in m2
                      if any(a >= s - 1e-6 and b <= e + 1e-6 for s, e in nghi)]
        kiem("5k KHÔNG chữ nào rơi GỌN vào chỗ nghỉ (rải đều = chữ hiện lúc "
             "máy đang im)", not trong_nghi, f"{trong_nghi}")

    # --- mức ĐƠN VỊ: cùng đầu vào, có/không khoảng có tiếng phải ra KHÁC HẲN.
    # Không có mục này thì xoá sạch phần vá đi cổng vẫn xanh.
    gia = [[0.0, 1.0, "a"], [1.0, 2.0, "b"]]
    cu = PT._co_gian(gia, 3.0, None)                     # cách CŨ: rải đều
    moi = PT._co_gian(gia, 3.0, [(0.0, 1.0), (2.0, 3.0)])  # nghỉ 1s ở giữa
    kiem("5l cách CŨ (rải đều) đặt chữ 'b' vào GIỮA CHỖ NGHỈ — đây là bệnh",
         abs(cu[1][0] - 1.5) < 1e-6, f"cũ: {cu}")
    kiem("5m bản vá NHẢY QUA chỗ nghỉ: 'b' bắt đầu đúng lúc tiếng trở lại",
         abs(moi[1][0] - 2.0) < 1e-6 and abs(moi[0][1] - 1.0) < 1e-6,
         f"mới: {moi}")
    kiem("5n TỰ KIỂM: hai cách LỆCH HẲN nhau (trùng nhau = bản vá chưa nối)",
         abs(moi[1][0] - cu[1][0]) > 0.02,
         f"lệch {abs(moi[1][0] - cu[1][0]) * 1000:.0f} ms")
    # chữ trong mốc phải là CHÍNH chữ của câu, đúng thứ tự
    kiem("5e mốc gán ĐÚNG CHỮ, đúng thứ tự (bẫy `con`/`giờ.` không làm lệch)",
         all([w for _a, _b, w in m] == [x.strip(".,") for x in t.split()]
             for m, t in zip(moc, texts) if m),
         f"{[w for _a, _b, w in moc[0]]}")

    # BẤT BIẾN AN TOÀN: không tra ra file thì BỎ MỐC, KHÔNG đoán.
    #
    # Mục 5g kiểm CHÍNH `_tra_file`, không vá nó. Bản đầu chỉ có 5f (vá
    # `_tra_file` thành `None`) và **THỬ PHÁ ĐÃ LỌT**: sửa `_tra_file` thành
    # "đoán bừa lấy file đầu tiên" thì 5f vẫn xanh vì nó đã vá đè lên đúng
    # hàm vừa bị phá. Phải có mục kiểm chính hàm đó ở mức đơn vị.
    kho = hop_cat("tra")
    (kho / "mot.wav").write_bytes(b"RIFF")
    (kho / "con_.wav").write_bytes(b"RIFF")
    kiem("5g `_tra_file` tra ĐÚNG chữ có thật",
         PT._tra_file(kho, "mot") is not None
         # `con` -> Piper ghi ra `con_.wav` (CON là tên thiết bị Windows)
         and PT._tra_file(kho, "con") is not None)
    kiem("5h `_tra_file` trả None cho chữ KHÔNG có — KHÔNG đoán bừa "
         "(đoán bừa = mốc gán nhầm chữ, rc vẫn 0)",
         PT._tra_file(kho, "khongtontai") is None,
         f"{PT._tra_file(kho, 'khongtontai')}")

    goc = PT._tra_file
    PT._tra_file = lambda thu_muc, chu: None
    try:
        ok2, moc2 = PT.doc_loat(["Một hai ba bốn năm sáu."], [str(d / "z.wav")])
        kiem("5f tra hụt một chữ -> BỎ MỐC cả nhóm, TIẾNG VẪN CÒN "
             "(mốc gán nhầm chữ tệ hơn không có mốc)",
             ok2 == [True] and moc2 == [[]], f"ok={ok2} · mốc={moc2}")
    finally:
        PT._tra_file = goc


# =====================================================================
def ca6_length_scale() -> None:
    """MỆNH ĐỀ 6 — `length_scale` bão hoà, và KHÔNG tỉ lệ thuận."""
    print("\nCA 6 — `length_scale` BÃO HOÀ (app cần ép tiếng vừa khung)")
    from app.core import piper_tts as PT
    d = hop_cat("ls")
    cau = ("Hôm nay tôi sẽ chia sẻ với các bạn một câu chuyện rất thú vị "
           "mà tôi đã gặp cách đây ba phút khi đang đi bộ trên con đường quen.")
    p0 = str(d / "tn.wav")
    ok, _m = PT.doc_loat([cau], [p0], lay_moc=False)
    d0 = PT.dai_wav(p0)
    kiem("6a đọc bản tự nhiên", ok == [True] and d0 > 1.0, f"{d0:.3f}s")

    bang = []
    for ls in (0.8, 0.5, 0.2):
        p = str(d / f"ls{ls}.wav")
        rc, err = PT._chay(["-f", p, "--length-scale", str(ls)], vao=cau,
                           han=300)
        dd = PT.dai_wav(p)
        # KHÔNG im lặng ghi 0: rc hỏng phải lộ ra, không thì bảng số là số rác
        kiem(f"6b length_scale={ls} chạy được (rc=0, file có tiếng)",
             rc == 0 and dd > 0, f"rc={rc} {err[:60]}" if rc else f"{dd:.3f}s")
        if dd > 0:
            bang.append((ls, dd / d0))
    if len(bang) >= 3:
        print("    tỉ lệ so tự nhiên: "
              + " · ".join(f"ls={l}->{t:.3f}×" for l, t in bang))
        t08, t05, t02 = bang[0][1], bang[1][1], bang[2][1]
        kiem("6c ép ngắn CÓ tác dụng ở vùng trên (0,8 ngắn hơn tự nhiên)",
             t08 < 0.99, f"{t08:.3f}×")
        kiem("6d BÃO HOÀ: 0,5 -> 0,2 gần như không ngắn thêm "
             "(tham số giảm 2,5 lần mà độ dài đổi < 10%)",
             (t05 - t02) < 0.10, f"{t05:.3f}× -> {t02:.3f}×")
        kiem("6e KHÔNG TỈ LỆ THUẬN: đặt 0,5 KHÔNG ra 0,5× "
             "(ai tính length_scale = khung/độ_dài sẽ ép hụt rất xa)",
             t05 > 0.65, f"đặt 0,5 ra {t05:.3f}×")
        kiem("6f nén sâu nhất không dưới mức đã ghi trong mã "
             f"(`NEN_SAU_NHAT`={PT.NEN_SAU_NHAT})",
             t02 >= PT.NEN_SAU_NHAT - 0.06, f"{t02:.3f}×")
    # bảng tra `rate` -> `length_scale` phải nằm trong dải Piper làm được
    kiem("6g `_ls_tu_rate` không xin điều Piper không làm được",
         PT._ls_tu_rate("+0%") is None
         and 0.15 <= (PT._ls_tu_rate("+50%") or 1) <= 1.0
         and (PT._ls_tu_rate("+900%") or 1) >= 0.2,
         f"+20%->{PT._ls_tu_rate('+20%')} · +50%->{PT._ls_tu_rate('+50%')}")


# =====================================================================
def ca7_bat_bien() -> None:
    """BẤT BIẾN — chưa chọn Piper thì mọi thứ y hệt trước."""
    print("\nCA 7 — BẤT BIẾN: không chọn Piper thì đường cũ không đổi")
    from app.core import dubbing
    from app.core import piper_tts as PT
    for v in ("vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural|-20Hz",
              "en-US-AndrewNeural", ""):
        if dubbing._piper_hay_khong(v) != (False, v):
            kiem(f"7a giọng {v!r} KHÔNG bị rẽ sang Piper", False,
                 f"{dubbing._piper_hay_khong(v)}")
            break
    else:
        kiem("7a mọi giọng edge-tts (kể cả biến thể pitch) KHÔNG bị rẽ", True,
             "4/4 giọng đi đường cũ")
    kiem("7b `la_giong_piper` không nhận nhầm giọng edge-tts",
         not any(PT.la_giong_piper(v) for v in
                 ("vi-VN-NamMinhNeural", "en-US-AndrewNeural", "", None))
         and PT.la_giong_piper(PT.MA_GIONG))
    # `_synth_all` (cửa KHÔNG mốc) cũng phải rẽ — sót nó là LẪN HAI GIỌNG.
    #
    # PHẢI ĐỌC BẰNG AST, ĐỪNG TÌM CHUỖI. Bản đầu của mục này dùng
    # `"_piper_hay_khong" in inspect.getsource(...)` và **THỬ PHÁ ĐÃ LỌT**:
    # docstring của chính hai hàm đó có câu *"xem `_piper_hay_khong`"*, nên gỡ
    # SẠCH nhánh rẽ ra khỏi `_synth_all` mà cổng vẫn XANH = con dấu. Đúng bài
    # học cổng 56d, lần này ở chiều PASS OAN.
    import ast
    cay = ast.parse(Path(dubbing.__file__).read_text(encoding="utf-8"))
    ham = {n.name: n for n in ast.walk(cay)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for ten in ("_synth_all", "_synth_all_words"):
        n = ham.get(ten)
        goi = [c for c in ast.walk(n)] if n else []
        co_goi = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                     and c.func.id == "_piper_hay_khong" for c in goi)
        co_doc = any(isinstance(c, ast.Call)
                     and isinstance(c.func, ast.Attribute)
                     and c.func.attr == "doc_loat" for c in goi)
        kiem(f"7c `{ten}` THẬT SỰ GỌI cửa rẽ Piper rồi đọc "
             f"(sót 1 cửa = video lẫn hai giọng)", co_goi and co_doc,
             f"gọi cửa rẽ {co_goi} · gọi doc_loat {co_doc}")


# =====================================================================
def main() -> int:
    print("=" * 74)
    print("CỔNG 64 — PIPER LÀM LỰA CHỌN THỨ HAI (không thay edge-tts)")
    print("=" * 74)
    from app.core import piper_tts as PT
    tt = PT.tinh_trang_piper()
    print(f"Piper: {'CÓ' if tt['co'] else 'CHƯA CÓ'} · {tt['thu_muc']}")
    if not tt["co"]:
        print(f"  thiếu: {tt['thieu']}")

    ca1_giay_phep()
    ca2_chi_vais1000()
    ca3_thieu_piper_lui_em()
    ca7_bat_bien()
    if tt["co"]:
        ca4_ba_cho_goi()
        ca5_moc_tung_chu()
        ca6_length_scale()
    else:
        # Không có Piper thì các ca CHẠY THẬT không đo được. Nói THẲNG là bỏ
        # qua, đừng in "ĐẠT" cho việc không làm — cổng đạt oan vì lượt chạy
        # không tới chốt là bẫy đã bắt ở cổng 55 CA4 và 62 CA4.
        print("\n(BỎ QUA CA 4/5/6 — máy chưa tải Piper, không đo thật được)")

    print("\n" + "=" * 74)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        don_rac()
