"""CỔNG 67 — KIỂU CHỮ CHỈNH ĐƯỢC TRÊN ĐƯỜNG THAY GIỌNG.

Anh Hùng 17/08/2026: *"phần chữ sub ở trong video tôi không điều chỉnh được cỡ
chữ, kiểu chữ, hay in nghiêng đậm, hay chỉnh viền gì được à"*. Đường CẮT
THƯỜNG đã có đủ trong Chỉnh mẫu từ việc #104-#108; đường THAY GIỌNG thì
`grep "Fontsize|FontName|Outline|Bold|Italic" app/core/thay_giong.py` ra **0
kết quả** — kiểu chữ cứng, không một ô nào chỉnh được.

CỔNG NÀY CANH 5 ĐIỀU:
1. BẤT BIẾN: `ghi_ass(kieu=None)` ra .ass GIỐNG TỪNG BYTE bản mốc -> mọi lối
   gọi cũ (và job đã nằm trong DB) không đổi hành vi.
2. BẤT BIẾN: tách `kieu_chu_ass` ra khỏi `build_ass` không đổi 1 byte .ass của
   đường CẮT THƯỜNG (đây là bất biến sống còn của cổng 21: anh Hùng đang chạy
   sản xuất 200-300 kênh bằng preset cũ).
3. DÙNG CHUNG THẬT: hai đường đi qua CÙNG một cửa `captions.kieu_chu_ass`, đặt
   cùng tham số thì ra cùng màu/viền/độ dày — kiểm bằng cách GỌI cả hai rồi so
   trường, không quét chuỗi.
4. TỪNG Ô ĐỔI THẬT: mỗi ô (cỡ · phông · đậm · nghiêng · màu chữ · màu viền ·
   độ dày viền · vị trí) phải làm .ass KHÁC ĐI. Ô không đổi được gì = cái nhãn.
5. RENDER THẬT bằng ffmpeg + video THẬT: kiểm KÍCH THƯỚC + ĐỘ DÀI đầu ra (mã 0
   + file 0 KiB là bẫy đã ghi), đếm điểm ảnh chữ, và **PHÔNG PHẢI ĐỔI ĐƯỢC
   MẶT CHỮ** — thiếu `fontsdir` thì libass lùi im lặng về phông mặc định.

BẪY ĐÃ SẬP KHI VIẾT CỔNG NÀY (bản đầu là CON DẤU): mục 2 truyền `words` dạng
TUPLE trong khi `captions._remap_words` đọc `w["start"]`/`w["word"]` và bỏ qua
IM LẶNG thứ nó không tra được -> `build_ass` trả False, KHÔNG ghi file, 108
phép so đều so HAI CHUỖI RỖNG rồi báo "giống từng byte". Nay có chốt tự kiểm
"phải có Style Default + Dialogue trong .ass" trước khi so.

Mốc đối chứng: `BQ_MOC_KIEU` (mặc định `v2.31.0` = bản phát hành NGAY TRƯỚC
việc này). KHÔNG dùng `main`/`HEAD`: sau khi gộp thì mốc chính là bản đang
test, cổng tự PASS OAN vĩnh viễn (bài học cổng 36/51/52/56).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import _test_guard  # noqa: F401  (chặn mở Explorer/trình phát, ép stdout utf-8)

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

FF = REPO / "bin" / "ffmpeg.exe"
FFPROBE = REPO / "bin" / "ffprobe.exe"
FONTS = REPO / "app" / "assets" / "fonts"
NGUON = Path(r"C:\Users\Admin\Downloads\longtieng") / "4月新片海外电影片单.mp4"
MOC = os.environ.get("BQ_MOC_KIEU", "v2.31.0")
CAU = "Chào các bạn, đây là chữ mới thay giọng"

DAT = HONG = 0
_HOP: Path | None = None


def ok(dieu: bool, ten: str, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return dieu


def hop() -> Path:
    global _HOP
    if _HOP is None:
        _HOP = REPO / f"_kc67_{os.getpid()}"
        _HOP.mkdir(exist_ok=True)
    return _HOP


def don() -> None:
    for d in REPO.glob("_kc67_*"):          # gồm cả hộp của lần chạy TRƯỚC
        shutil.rmtree(d, ignore_errors=True)


def _nap_moc(ref: str, duong: str):
    r = subprocess.run(["git", "show", f"{ref}:{duong}"], cwd=REPO,
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"không nạp được {ref}:{duong}")
    src = r.stdout.decode("utf-8")
    ten = f"moc_{Path(duong).stem}_{abs(hash(ref)) % 9973}"
    m = types.ModuleType(ten)
    m.__file__ = f"<{ref}:{duong}>"
    # PHẢI đăng ký vào sys.modules TRƯỚC khi exec: `@dataclass` (DaiChu) tra
    # `sys.modules[cls.__module__].__dict__` để nhận diện KW_ONLY, thiếu là nổ
    # AttributeError ngay lúc nạp mốc.
    sys.modules[ten] = m
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    return m, src


def esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


# ─────────────────────────── MỤC 1 — BẤT BIẾN ghi_ass ────────────────────────
def muc1() -> None:
    print("\n[1] BẤT BIẾN: ghi_ass(kieu=None) giống TỪNG BYTE bản mốc")
    from app.core import che_chu as CC
    moc, src_moc = _nap_moc(MOC, "app/core/che_chu.py")
    src_nay = (REPO / "app" / "core" / "che_chu.py").read_text(encoding="utf-8")
    if not ok(src_moc != src_nay, "bản mốc KHÁC bản đang test",
              f"mốc {MOC}"):
        return
    dai = CC.DaiChu(co_chu=True, y0=648, y1=720, x0=0, x1=1274, rong=1280,
                    cao=720, ty_le_khung=0.875, mat_do=0.11, mat_do_nen=0.01,
                    ty_so_nen=9.7, so_khung=16, ly_do="thử", moc=[], hop=[])
    dong = [(0.6, 5.6, CAU), (6.0, 9.0, "Dòng thứ hai")]
    h = hop()
    n = 0
    for i, kw in enumerate([{}, {"co_chu": 48.0}, {"font": "Anton"},
                            {"do_vien": 5.0},
                            {"mau": "&H0000FFFF", "vien": "&H00FF0000"}]):
        fa, fb = h / f"bb_a{i}.ass", h / f"bb_b{i}.ass"
        ra = CC.ghi_ass(dong, fa, dai, **kw)
        rb = moc.ghi_ass(dong, fb, dai, **kw)
        ta = fa.read_text(encoding="utf-8")
        tb = fb.read_text(encoding="utf-8")
        if not (ra and "Style: CheChu," in ta and "Dialogue:" in ta):
            ok(False, f"bộ {i}: .ass dựng được", "rỗng -> phép so vô nghĩa")
            return
        if ta == tb and ra == rb:
            n += 1
        else:
            ok(False, f"bộ {i}: giống mốc", f"{ta[:0]}LỆCH")
            for la, lb in zip(ta.splitlines(), tb.splitlines()):
                if la != lb:
                    print(f"       NAY: {la}\n       MỐC: {lb}")
                    break
            return
    ok(n == 5, "5/5 bộ tham số CŨ ra .ass giống từng byte", f"{n}/5")


# ─────────────────────── MỤC 2 — BẤT BIẾN build_ass (cổng 21) ────────────────
def muc2() -> None:
    print("\n[2] BẤT BIẾN: build_ass (đường CẮT THƯỜNG) không đổi 1 byte")
    from app.core import captions as nay
    moc, src_moc = _nap_moc(MOC, "app/core/captions.py")
    src_nay = (REPO / "app" / "core" / "captions.py").read_text(encoding="utf-8")
    if not ok(src_moc != src_nay, "bản mốc KHÁC bản đang test", f"mốc {MOC}"):
        return
    # ĐỊNH DẠNG TỪ PHẢI LÀ DICT — xem khối BẪY ở docstring.
    words = [{"start": a, "end": b, "word": t} for a, b, t in (
        (0.0, 0.4, "xin"), (0.4, 0.9, "chào"), (0.9, 1.5, "các"),
        (1.5, 2.2, "bạn"), (2.2, 3.0, "hôm"), (3.0, 3.6, "nay"))]
    segs = [(0.0, 5.0)]
    bo = [{}, {"size": 72, "color": "#00FF88"},
          {"cap_outline": "#FF00FF", "ny": 0.55},
          {"cap_ow": 0.22, "size": 96, "cap_case": "upper"}]
    h = hop()
    giong = lech = rong = 0
    for ten in nay.CAPTION_PRESETS:
        if ten not in moc.CAPTION_PRESETS:
            continue
        for i, kw in enumerate(bo):
            fa, fb = h / "ba.ass", h / "bb.ass"
            ra = nay.build_ass(words, segs, fa, preset=ten, **kw)
            rb = moc.build_ass(words, segs, fb, preset=ten, **kw)
            ta = fa.read_text(encoding="utf-8") if fa.exists() else ""
            tb = fb.read_text(encoding="utf-8") if fb.exists() else ""
            if not (ra and "Style: Default," in ta and "Dialogue:" in ta):
                rong += 1
                continue
            if ta == tb and ra == rb:
                giong += 1
            else:
                lech += 1
                if lech == 1:
                    print(f"       LỆCH ĐẦU: «{ten}» bộ {i}")
    ok(rong == 0, "mọi phép so đều dựng được .ass THẬT (không so chuỗi rỗng)",
       f"rỗng {rong}")
    ok(lech == 0 and giong > 0, "preset CŨ ra .ass giống từng byte",
       f"giống {giong} · lệch {lech}")


# ───────────────────── MỤC 3 — HAI ĐƯỜNG DÙNG CHUNG MỘT CỬA ──────────────────
def muc3() -> None:
    print("\n[3] DÙNG CHUNG: cắt thường và thay giọng ra CÙNG kiểu chữ")
    from app.core import captions as C
    from app.core import che_chu as CC
    import ast
    # (a) build_ass phải THẬT SỰ GỌI kieu_chu_ass — đọc bằng AST, không tìm
    # chuỗi: chính docstring có nhắc tên hàm nên tìm chuỗi là PASS OAN
    # (bài học cổng 56d / 64).
    cay = ast.parse((REPO / "app" / "core" / "captions.py").read_text("utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "build_ass")
    goi = {n.func.id for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ok("kieu_chu_ass" in goi, "build_ass GỌI THẬT kieu_chu_ass (đọc AST)")
    cay2 = ast.parse((REPO / "app" / "core" / "che_chu.py").read_text("utf-8"))
    ham2 = next(n for n in ast.walk(cay2)
                if isinstance(n, ast.FunctionDef) and n.name == "ghi_ass")
    goi2 = {n.func.id for n in ast.walk(ham2)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ok("kieu_chu_ass" in goi2, "ghi_ass GỌI THẬT kieu_chu_ass (đọc AST)")
    # (b) cùng tham số -> cùng màu/viền/độ dày, đo bằng CHÍNH .ass hai bên
    dai = CC.DaiChu(co_chu=True, y0=800, y1=900, x0=0, x1=1074, rong=1080,
                    cao=1920, ty_le_khung=0.9, mat_do=0.11, mat_do_nen=0.01,
                    ty_so_nen=9.7, so_khung=16, ly_do="", moc=[], hop=[])
    h = hop()
    lech = []
    for pre in ("Vàng nhảy (TikTok)", "Nền hộp đen", "Viền neon",
                "Hồng nổi (Reels)"):
        k = C.kieu_chu_ass(pre, 96, "", "", 0.0, 1920)
        fa = h / "chung.ass"
        CC.ghi_ass([(0.0, 2.0, "abc")], fa, dai,
                   kieu={"preset": pre, "co_chu": 96 / 1920})
        st = [l for l in fa.read_text("utf-8").splitlines()
              if l.startswith("Style: CheChu,")][0].split(",")
        # CỘT của [V4+ Styles] (đếm từ 0, cột 0 gộp "Style: <Name>"):
        # 0 Name · 1 Fontname · 2 Fontsize · 3 Primary · 4 Secondary ·
        # 5 OutlineColour · 6 Back · 7 Bold · 8 Italic · 9 Underline ·
        # 10 StrikeOut · 11 ScaleX · 12 ScaleY · 13 Spacing · 14 Angle ·
        # 15 BorderStyle · 16 Outline(ĐỘ DÀY) · 17 Shadow · 18 Alignment.
        # Bản đầu của cổng đếm lệch 1 cột (lấy 16 làm BorderStyle) -> báo HỎNG
        # OAN cả 4 preset trong khi app đúng.
        if not (st[3] == k["primary"] and st[5] == k["outline"]
                and st[6] == k["back"] and int(st[15]) == k["border_style"]
                and float(st[16]) == float(k["ow"])):
            lech.append(f"{pre}(có {st[3]}/{st[5]}/{st[15]}/{st[16]} "
                        f"cần {k['primary']}/{k['outline']}/"
                        f"{k['border_style']}/{k['ow']})")
    ok(not lech, "4 preset: màu chữ/viền/nền/độ dày KHỚP giữa hai đường",
       f"lệch: {lech}" if lech else "")


# ───────────────────── MỤC 4 — TỪNG Ô PHẢI ĐỔI THẬT .ass ─────────────────────
def muc4() -> None:
    print("\n[4] TỪNG Ô đổi thật (ô không đổi được gì = cái nhãn)")
    from app.core import che_chu as CC
    dai = CC.DaiChu(co_chu=True, y0=648, y1=720, x0=0, x1=1274, rong=1280,
                    cao=720, ty_le_khung=0.875, mat_do=0.11, mat_do_nen=0.01,
                    ty_so_nen=9.7, so_khung=16, ly_do="", moc=[], hop=[])
    h = hop()
    goc_k = {"preset": "Trắng viền đen", "co_chu": 0.075}

    def ve(k: dict, ten: str) -> str:
        f = h / f"o_{ten}.ass"
        CC.ghi_ass([(0.6, 5.6, CAU)], f, dai, kieu=k)
        return f.read_text(encoding="utf-8")

    goc = ve(goc_k, "goc")
    for ten, k in (
            ("cỡ chữ", {**goc_k, "co_chu": 0.11}),
            ("phông", {**goc_k, "font": "Anton"}),
            ("in đậm", {**goc_k, "dam": False}),
            ("in nghiêng", {**goc_k, "nghieng": True}),
            ("màu chữ", {**goc_k, "mau": "#FFD83D"}),
            ("màu viền", {**goc_k, "vien": "#C00000"}),
            ("độ dày viền", {**goc_k, "do_vien": 0.22}),
            ("vị trí", {**goc_k, "vi_tri": "tren"}),
            ("kiểu (preset)", {**goc_k, "preset": "Nền hộp đen"})):
        ok(ve(k, ten.replace(" ", "_")) != goc, f"ô «{ten}» làm .ass ĐỔI")
    # chốt riêng: đổi vị trí phải đổi NEO `\anN`, không phải chỉ đổi toạ độ
    tren = ve({**goc_k, "vi_tri": "tren"}, "vt_tren")
    duoi = ve({**goc_k, "vi_tri": "duoi"}, "vt_duoi")
    ok("\\an8" in tren and "\\an2" in duoi, "vị trí đổi NEO ASS thật",
       "trên=an8 · dưới=an2")
    # chốt CẮT ĐÁY: cỡ to + dải sát mép dưới -> điểm neo phải bị kéo vào trong
    to = ve({**goc_k, "co_chu": 0.11}, "to")
    y = int(to.split("\\pos(")[1].split(")")[0].split(",")[1])
    cs = int([l for l in to.splitlines()
              if l.startswith("Style: CheChu,")][0].split(",")[2])
    ok(y + cs * 0.9 <= 720 + 1, "cỡ TO không đẩy chữ ra ngoài đáy khung",
       f"neo y={y} · cỡ={cs} · khung cao 720")


# ─────────────────── MỤC 5 — RENDER THẬT + PHÔNG ĐỔI ĐƯỢC ────────────────────
def muc5() -> None:
    print("\n[5] RENDER THẬT bằng ffmpeg trên video THẬT")
    from app.core import che_chu as CC
    if not NGUON.exists():
        ok(False, "có video nguồn thật", f"thiếu {NGUON}")
        return
    h = hop()
    src = h / "nguon.mp4"
    shutil.copy2(NGUON, src)            # COPY — không đụng bản gốc anh Hùng
    loc, dai, ly = CC.loc_cho_xuat(str(src), cach="mo", muc=1.0,
                                   segs=[(0.0, 6.0)])
    if not ok(bool(loc) and dai is not None and dai.co_chu,
              "dò ra dải chữ của nguồn", ly[:60]):
        return

    def xuat(ten: str, kieu: dict, fontsdir: bool = True) -> dict:
        ass = h / f"r_{ten}.ass"
        CC.ghi_ass([(0.6, 5.6, CAU)], ass, dai, kieu=kieu)
        vf = f"{loc},{CC.chuoi_subtitles(ass)}" if fontsdir else \
             f"{loc},subtitles='{esc(ass)}'"
        ra = h / f"r_{ten}.mp4"
        r = subprocess.run([str(FF), "-y", "-v", "error", "-t", "6",
                            "-i", str(src), "-vf", vf, "-an", "-c:v",
                            "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                            str(ra)], capture_output=True, timeout=600)
        if r.returncode != 0 or not ra.exists():
            return {"rc": r.returncode, "co": 0, "dai": 0.0}
        p = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1",
                            str(ra)], capture_output=True, timeout=60)
        try:
            d = float(p.stdout.decode().strip())
        except ValueError:
            d = 0.0
        png = h / f"r_{ten}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", "2", "-i",
                        str(ra), "-frames:v", "1", str(png)],
                       capture_output=True, timeout=60)
        return {"rc": r.returncode, "co": ra.stat().st_size, "dai": d,
                "png": png}

    goc = {"preset": "Trắng viền đen", "co_chu": 0.075}
    r_nho = xuat("nho", {**goc, "co_chu": 0.045})
    r_to = xuat("to", {**goc, "co_chu": 0.105})
    # MÃ 0 + FILE 0 KiB là bẫy đã ghi -> kiểm CỠ và ĐỘ DÀI, không kiểm mã thoát
    for ten, r in (("cỡ nhỏ", r_nho), ("cỡ to", r_to)):
        ok(r["co"] > 100_000 and r["dai"] > 5.0,
           f"xuất được video THẬT ({ten})",
           f"{r['co']//1024} KB · {r['dai']:.2f}s")
    from PIL import Image

    def dem(png: Path) -> int:
        im = Image.open(png).convert("L")
        w, hh = im.size
        px = im.load()
        return sum(1 for y in range(hh) for x in range(w) if px[x, y] > 200)

    n_nho, n_to = dem(r_nho["png"]), dem(r_to["png"])
    ok(n_to > n_nho * 1.3, "cỡ TO vẽ ra NHIỀU điểm ảnh chữ hơn cỡ NHỎ",
       f"nhỏ {n_nho} · to {n_to}")
    # PHÔNG: có fontsdir thì mặt chữ PHẢI đổi; thiếu fontsdir thì KHÔNG đổi
    a = xuat("ph_anton_co", {**goc, "font": "Anton"}, fontsdir=True)
    b = xuat("ph_bia_co", {**goc, "font": "PhongBiaKhongCo"}, fontsdir=True)
    c = xuat("ph_anton_khong", {**goc, "font": "Anton"}, fontsdir=False)
    d = xuat("ph_bia_khong", {**goc, "font": "PhongBiaKhongCo"}, fontsdir=False)
    ok(a["co"] != b["co"], "CÓ fontsdir: phông Anton đổi được mặt chữ",
       f"anton {a['co']//1024} KB vs bịa {b['co']//1024} KB")
    ok(c["co"] == d["co"],
       "THIẾU fontsdir: phông KHÔNG có tác dụng (lý do phải kèm fontsdir)",
       f"cả hai {c['co']//1024} KB")
    print(f"       ẢNH để NGƯỜI tự nhìn: {h}")


# ────────────── MỤC 6 — KIỂU CHỮ PHẢI VÀO KHOÁ CHỐNG TRÙNG ──────────────────
def muc6() -> None:
    print("\n[6] Đổi kiểu chữ rồi bấm Chạy: KHÔNG được bị smart-skip")
    from app.core import tg_chay as T
    a = ("D:/a/v.mp4", "vi", "giong", "D:/ra")
    khong_che = T.khoa_chong_trung(*a)
    che = T.khoa_chong_trung(*a, True, "mo", 1.0, True)
    # BẤT BIẾN: không đặt ô nào -> khoá GIỐNG TỪNG KÝ TỰ bản trước khi có
    # tính năng (không đẻ job chạy lại cho 200-300 kênh).
    ok(T.khoa_chong_trung(*a, True, "mo", 1.0, True,
                          {"co_chu": 0, "font": "", "dam": None}) == che,
       "kiểu chữ để MẶC ĐỊNH -> khoá không đổi 1 ký tự")
    moc, _ = _nap_moc(MOC, "app/core/tg_chay.py")
    ok(moc.khoa_chong_trung(*a) == khong_che
       and moc.khoa_chong_trung(*a, True, "mo", 1.0, True) == che,
       "khoá của job CŨ khớp bản mốc", f"mốc {MOC}")
    k1 = T.khoa_chong_trung(*a, True, "mo", 1.0, True, {"co_chu": 0.075})
    doi = {
        "cỡ chữ": {"co_chu": 0.11},
        "phông": {"co_chu": 0.075, "font": "Anton"},
        "in đậm": {"co_chu": 0.075, "dam": False},
        "in nghiêng": {"co_chu": 0.075, "nghieng": True},
        "màu chữ": {"co_chu": 0.075, "mau": "#FFD83D"},
        "màu viền": {"co_chu": 0.075, "vien": "#C00000"},
        "độ dày viền": {"co_chu": 0.075, "do_vien": 0.2},
        "vị trí": {"co_chu": 0.075, "vi_tri": "tren"},
        "kiểu (preset)": {"co_chu": 0.075, "preset": "Nền hộp đen"},
    }
    xau = [t for t, k in doi.items()
           if T.khoa_chong_trung(*a, True, "mo", 1.0, True, k) == k1]
    ok(not xau, "đổi BẤT KỲ ô nào cũng làm khoá ĐỔI", f"không đổi: {xau}")
    # khoá phải TIỀN ĐỊNH: cùng nội dung, khác thứ tự dict -> cùng khoá.
    # Tính tiền định đến từ `gon_kieu_chu` duyệt TUPLE CỐ ĐỊNH `KHOA_KIEU_CHU`
    # (không phải từ `sorted`), nên phải thử với NHIỀU ô mới có răng.
    ok(T.khoa_chong_trung(*a, True, "mo", 1.0, True,
                          {"vi_tri": "tren", "font": "Anton", "co_chu": 0.075})
       == T.khoa_chong_trung(*a, True, "mo", 1.0, True,
                             {"co_chu": 0.075, "vi_tri": "tren",
                              "font": "Anton"}),
       "khoá TIỀN ĐỊNH (không phụ thuộc thứ tự khoá trong dict)")
    # KHOÁ LẠ (UI đổi tên ô, mẫu cũ trên đĩa) KHÔNG được lọt vào chữ ký —
    # lọt là job cũ đổi khoá vì một thứ app không hề dùng tới.
    ok(T.khoa_chong_trung(*a, True, "mo", 1.0, True,
                          {"co_chu": 0.075, "khoa_la_hoac_o_cu": "xyz"}) == k1,
       "khoá LẠ trong đơn thuốc KHÔNG lọt vào chữ ký")
    # KHÔNG viết chữ mới -> kiểu chữ vô nghĩa, không được lọt vào khoá
    ok(T.khoa_chong_trung(*a, True, "mo", 1.0, False, {"co_chu": 0.11})
       == T.khoa_chong_trung(*a, True, "mo", 1.0, False),
       "tắt 'viết chữ mới' -> kiểu chữ KHÔNG vào khoá")


def main() -> int:
    print(f"CỔNG 67 — kiểu chữ đường THAY GIỌNG · mốc {MOC}")
    try:
        muc1(); muc2(); muc3(); muc4(); muc5(); muc6()
    finally:
        pass
    print(f"\nĐẠT {DAT} · HỎNG {HONG}")
    return 0 if HONG == 0 else 1


if __name__ == "__main__":
    don()
    try:
        sys.exit(main())
    finally:
        if os.environ.get("BQ_GIU_HOP") != "1":
            don()
