# -*- coding: utf-8 -*-
"""CỔNG 105 — TIẾNG ĐỘNG: KHO ĐA DẠNG + CHỌN HỢP LÝ (02/11/2026).

Anh Hùng: *"có vài kiểu ít quá mà đơn điệu ... thêm nhiều đoạn cũng buồn cười"*.
Số đo gốc (nhật ký 1.317 Part thật): 3 họ tiếng = 51% mọi lượt chèn, 70/97 kiểu
hiệu ứng không có trong bảng -> 'impact', Part tới 17 tiếng, 341 cặp < 2 s.

Cổng canh (thành phần THẬT: ffmpeg + kho thật + bảng đo thật):
  CA 1  bảng kiểu hình -> tiếng phủ ĐỦ `hieu_ung.KHO`, giá trị hợp lệ
  CA 2  kho: bảng mức khớp file trên đĩa · file mới có nguồn + sha256 + CC0 ·
        đủ HỌ dùng được (qua lọc loa điện thoại + vào chậm) cho từng nhóm
  CA 3  `chon_moc` — 5 luật (mood không kêu · nối liền mạch không kêu · ngân
        sách · cách >= 2 s · 3 cùng nhóm liền · comedy <= 1 · hook luôn giữ)
  CA 4  ngữ cảnh lời: chuyện nặng bỏ ding/pop · "chết cười" là VUI ·
        "deadline" KHÔNG phải chết · đổi mốc câu sang timeline đầu ra (hook-first)
  CA 5  bốc file: KHÔNG lặp HỌ trong 1 clip; `BQ_SFX_CU=1` vẫn chạy đường cũ
  CA 6  xuất THẬT bằng ffmpeg: nhật ký tiếng động tuân luật, đỉnh <= trần,
        độ dài đúng; tắt tiếng động -> lệnh KHÔNG có nhánh tiếng động nào
  CA 7  không đụng khoá chống trùng (services.py không biết gì về module mới)
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_DATA_DIR", tempfile.mkdtemp(prefix="bq105_"))
os.environ.setdefault("BQ_DB_PATH",
                      os.path.join(os.environ["BQ_DATA_DIR"], "t.db"))
os.environ.pop("BQ_SFX_CU", None)

from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import hieu_ung as H  # noqa: E402
from app.core import sfx_chon as SC  # noqa: E402

DAT = HONG = 0
#: khoảng cách tối thiểu ĐÃ CHỐT giữa 2 tiếng (giây) — hằng số của CỔNG.
CACH_CHOT = 2.0


def ok(dk: bool, ten: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


# ---------------------------------------------------------------------------
def ca1() -> None:
    print("\n[CA 1] BẢNG KIỂU HÌNH -> TIẾNG phủ đủ kho hiệu ứng")
    thieu = [k for k in H.KHO if k not in SC.BANG_HIEU_UNG]
    ok(not thieu, "mọi kiểu trong hieu_ung.KHO đều có dòng", f"thiếu {thieu}")
    sai = {k: v for k, v in SC.BANG_HIEU_UNG.items()
           if v is not None and v not in F.SFX_CATEGORIES}
    ok(not sai, "mọi giá trị là nhóm hợp lệ hoặc None", str(sai))
    for k in ("mau_am_diu", "tuyet_roi", "hat_phim", "mua_roi"):
        ok(SC.nhom_cho_hieu_ung(k) is None, f"kiểu dịu '{k}' KHÔNG kêu")
    ok(SC.nhom_cho_hieu_ung("luot_ngang") == "transition",
       "lướt ngang -> tiếng vút")
    ok(SC.nhom_cho_hieu_ung("kieu_moi_chua_khai", "tinh") is None
       and SC.nhom_cho_hieu_ung("kieu_moi_chua_khai", "caotrao") == "impact",
       "kiểu LẠ theo nhóm điểm (không còn 'impact cho mọi thứ')")
    n_none = sum(1 for k in H.KHO if SC.nhom_cho_hieu_ung(k) is None)
    n_imp = sum(1 for k in H.KHO if SC.nhom_cho_hieu_ung(k) == "impact")
    n_cu = sum(1 for k in H.KHO if F.loai_sfx_theo_hieu_ung(k) == "impact")
    ok(n_imp < n_cu, "số kiểu ra 'impact' giảm so với bảng cũ",
       f"cũ {n_cu} -> mới {n_imp}; {n_none} kiểu không kêu")


# ---------------------------------------------------------------------------
def ca2() -> None:
    print("\n[CA 2] KHO: bảng mức · nguồn/giấy phép · số HỌ dùng được")
    kho = REPO / "app" / "assets" / "sfx"
    bang = json.loads((kho / "muc_do.json").read_text("utf-8"))
    tren_dia = {p.relative_to(kho).as_posix() for p in kho.rglob("*")
                if p.suffix.lower() in (".opus", ".wav", ".ogg", ".mp3")}
    ok(set(bang) == tren_dia, "bảng mức khớp ĐÚNG file trên đĩa",
       f"thiếu đo {len(tren_dia - set(bang))} · thừa {len(set(bang) - tren_dia)}")
    ok(all(len(v) >= 6 for v in bang.values()), "mọi file đủ 6 cột đo")
    pv = json.loads((kho / "v2-provenance.json").read_text("utf-8"))
    ghi = {x["file"]: x for x in pv["files"]}
    moi = {f for f in tren_dia if re.search(r"/(k2_|s2_)", f)}
    ok(moi and moi == set(ghi), "mọi file mới có dòng nguồn",
       f"{len(moi)} file mới · {len(ghi)} dòng")
    import hashlib
    lech = [f for f in moi if ghi.get(f, {}).get("sha256") !=
            hashlib.sha256((kho / f).read_bytes()).hexdigest()]
    ok(not lech, "sha256 khớp từng file", str(lech[:3]))
    ok(all(x.get("license") == "CC0-1.0" for x in pv["files"]),
       "mọi file mới giấy phép CC0")
    for ten in ("NGUON.md",):
        t = (kho / ten).read_text("utf-8")
        ok("them_sfx_v2" in t and "rpg-audio" in t,
           f"{ten} ghi nguồn lượt 2 (đích danh gói)")
    lic = (REPO / "LICENSES.txt").read_text("utf-8")
    ok("rpg-audio" in lic and "them_sfx_v2" in lic,
       "LICENSES.txt nêu đích danh nguồn lượt 2")

    def dung_duoc(f):
        v = bang[f]
        return v[4] >= F._SFX_LOA_HUT_MAX and v[3] <= F._SFX_DICH_TOI_DA

    ho = {}
    ho_cu = {}
    for f in bang:
        if not dung_duoc(f):
            continue
        c = f.split("/")[0]
        ho.setdefault(c, set()).add(SC.ho_tieng(f))
        if f not in moi:
            ho_cu.setdefault(c, set()).add(SC.ho_tieng(f))
    for c, can in (("impact", 12), ("transition", 12), ("pop", 15),
                   ("comedy", 6), ("reveal", 8), ("scratch", 4)):
        n, n0 = len(ho.get(c, ())), len(ho_cu.get(c, ()))
        ok(n >= can and n > n0, f"nhóm {c}: >= {can} HỌ dùng được",
           f"cũ {n0} -> mới {n}")


# ---------------------------------------------------------------------------
def _uv(t, cat, vai="điểm nhấn", ld="caotrao"):
    return {"t": t, "cat": cat, "vai": vai, "loai_diem": ld}


def ca3() -> None:
    print("\n[CA 3] chon_moc — 5 luật")
    g, bo = SC.chon_moc([_uv(0.12, "impact", ld="hook"),
                         _uv(5.0, "pop", "nối", "noi_doan"),
                         _uv(9.0, None, ld="tinh")], 30.0)
    ok([x[0] for x in g] == [0.12], "nối gần liền mạch + kiểu dịu bị bỏ",
       f"giữ {g} · bỏ {bo}")
    dense = [_uv(0.12, "impact", ld="hook")] + [
        _uv(1.0 + i * 1.1, "transition", "nối", "noi_doan") for i in range(40)]
    g, bo = SC.chon_moc(dense, 60.0)
    gaps = [b[0] - a[0] for a, b in zip(g, g[1:])]
    ok(len(g) <= SC.ngan_sach(60.0), "không vượt ngân sách",
       f"{len(g)} <= {SC.ngan_sach(60.0)}")
    # SO VỚI HẰNG SỐ ĐÃ CHỐT, KHÔNG so với `SC.CACH_MIN`: so với chính nó là
    # tự chấm — thử phá đổi CACH_MIN về 0,8 mà cổng vẫn xanh (LỌT, 02/11).
    ok(SC.CACH_MIN >= CACH_CHOT and min(gaps) >= CACH_CHOT - 1e-9,
       "2 tiếng cách >= 2 s",
       f"min {min(gaps):.2f}")
    ok(g[0][0] == 0.12, "hook luôn được giữ")
    run = max((sum(1 for _ in grp) for _k, grp in
               __import__("itertools").groupby(c for _t, c, _v in g)),
              default=0)
    ok(run <= 2, "không quá 2 tiếng cùng nhóm liền nhau", f"chuỗi dài {run}")
    ok(SC.ngan_sach(20) == 3 and SC.ngan_sach(140) == SC.TOI_DA
       and SC.ngan_sach(3) == SC.TOI_THIEU, "ngân sách theo độ dài",
       f"20s:{SC.ngan_sach(20)} 140s:{SC.ngan_sach(140)} 3s:{SC.ngan_sach(3)}")
    g, _bo = SC.chon_moc([_uv(2, "comedy"), _uv(8, "comedy"),
                          _uv(14, "comedy")], 60.0)
    ok(sum(1 for x in g if x[1] == "comedy") <= 1, "comedy tối đa 1/clip",
       str(g))
    # ưu tiên: quá ngân sách thì bỏ nối 'transition' trước cao trào
    uu = [_uv(0.12, "impact", ld="hook")] + [
        _uv(4 + 3 * i, "transition", "nối", "noi_doan") for i in range(5)] + [
        _uv(27.0, "impact", ld="caotrao")]
    g, _bo = SC.chon_moc(uu, 30.0)
    ok(any(abs(x[0] - 27.0) < 1e-6 for x in g),
       "quá ngân sách thì cao trào được giữ trước nối thường",
       f"{[x[0] for x in g]}")


def ca4() -> None:
    print("\n[CA 4] ngữ cảnh lời thoại")
    ok(SC.ngu_canh_cau("Ông ấy đã qua đời sau tai nạn") == "nang",
       "câu tiếng Việt nặng")
    ok(SC.ngu_canh_cau("He died in the crash") == "nang", "câu Anh nặng")
    ok(SC.ngu_canh_cau("cười chết mất haha") == "vui", "'cười chết' là VUI")
    ok(SC.ngu_canh_cau("The deadline is tomorrow") == "",
       "'deadline' không phải 'dead'")
    ok(SC.ngu_canh_cau("他去世了") == "nang", "câu Trung nặng")
    cau = [(0.0, 4.0, "Bà ấy khóc nức nở vì mất con")]
    g, bo = SC.chon_moc([_uv(2.0, "reveal"), _uv(3.0, "pop", ld="dong")],
                        20.0, cau)
    ok(not g, "đang nói chuyện nặng -> bỏ ding/pop", f"bỏ {bo}")
    g, _bo = SC.chon_moc([_uv(2.0, "impact")], 20.0, cau)
    ok(g and g[0][1] == "suspense", "chuyện nặng: cú nhấn đổi sang suspense",
       str(g))
    g, _bo = SC.chon_moc([_uv(2.0, "impact")], 20.0,
                         [(1.0, 3.0, "haha buồn cười quá")])
    ok(g and g[0][1] == "comedy", "đang cười: cú nhấn -> comedy", str(g))
    tr = {"segments": [{"start": 100.0, "end": 102.0, "text": "A"},
                       {"start": 10.0, "end": 12.0, "text": "B"}]}
    m = SC.cau_ra_timeline(tr, [(100.0, 103.0), (9.0, 15.0)], 1.0)
    ok([(round(a, 2), round(b, 2), c) for a, b, c in m]
       == [(0.0, 2.0, "A"), (4.0, 6.0, "B")],
       "mốc câu sang timeline đầu ra đúng cả khi hook-first", str(m))
    m2 = SC.cau_ra_timeline(tr, [(100.0, 103.0)], 2.0)
    ok(m2 and abs(m2[0][1] - 1.0) < 1e-9, "chia đúng tốc độ video")


def ca5() -> None:
    print("\n[CA 5] bốc file: không lặp HỌ trong 1 clip")
    F._SFX_GAN_DAY.clear()
    F._SFX_HO_GAN_DAY.clear()
    lap = 0
    for s in range(40):
        pk = F._pick_sfx_by_category(["impact"] * 5, seed=s,
                                     noi_mocs=[True] * 5)
        hs = [SC.ho_tieng(f) for _c, f in pk if f]
        lap += len(hs) != len(set(hs))
    ok(lap == 0, "40 clip x 5 cú impact (đang nói) — 0 clip lặp họ",
       f"{lap} clip lặp")
    os.environ["BQ_SFX_CU"] = "1"
    try:
        F._SFX_GAN_DAY.clear()
        lap_cu = 0
        for s in range(40):
            pk = F._pick_sfx_by_category(["impact"] * 5, seed=s,
                                         noi_mocs=[True] * 5)
            hs = [SC.ho_tieng(f) for _c, f in pk if f]
            lap_cu += len(hs) != len(set(hs))
        ok(lap_cu > 0, "đối chứng: đường CŨ (BQ_SFX_CU=1) CÓ lặp họ",
           f"{lap_cu}/40 clip — thước có răng")
    finally:
        os.environ.pop("BQ_SFX_CU", None)


# ---------------------------------------------------------------------------
FF = str(REPO / "bin" / "ffmpeg.exe")
NW = 0x08000000 if os.name == "nt" else 0


def _nguon(p: str) -> None:
    """Nguồn 40 s CÓ cao trào (nền 0,04 + cú nổ) để `chon_hieu_ung` có điểm."""
    a = ("aevalsrc='0.04*sin(2*PI*220*t)+0.9*sin(2*PI*330*t)"
         "*(between(t,6,6.4)+between(t,17,17.4)+between(t,29,29.4))':"
         "s=48000:d=40")
    subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc2=s=540x960:r=25:d=40",
                    "-f", "lavfi", "-i", a, "-shortest", "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", p],
                   check=True, creationflags=NW, stdin=subprocess.DEVNULL)


def _dinh(p: str) -> float:
    r = subprocess.run([FF, "-nostdin", "-hide_banner", "-i", p, "-af",
                        "astats=measure_overall=Peak_level:measure_perchannel=0",
                        "-f", "null", "-"], capture_output=True,
                       creationflags=NW, stdin=subprocess.DEVNULL)
    t = r.stderr.decode("utf-8", "replace")
    m = re.findall(r"Peak level dB:\s*(-?[\d.]+|-inf)", t)
    if r.returncode != 0 or not m:
        raise RuntimeError("đo đỉnh hỏng: " + t[-300:])
    return float(m[-1]) if m[-1] != "-inf" else -99.0


def ca6() -> None:
    print("\n[CA 6] xuất THẬT bằng ffmpeg")
    d = tempfile.mkdtemp(prefix="bq105x_")
    src = os.path.join(d, "src.mp4")
    _nguon(src)
    # 6 đoạn: nối liền mạch (pop) + nhảy xa + hook-first
    segs = [(29.0, 31.5), (2.0, 6.5), (6.8, 12.0), (20.0, 24.0),
            (24.5, 28.0), (33.0, 38.0)]
    cats = ["impact", "pop", "transition", "pop", "transition"]
    log: list = []
    dst = os.path.join(d, "moi.mp4")
    F.export_canvas_clip(src, dst, segs, (0.5, 0.5, 1.0), bg="blur",
                         out_w=540, out_h=960, encoder="libx264",
                         fx_whoosh=True, join_categories=cats,
                         hieu_ung="vua", tieng_dong_log=log,
                         chuyen_canh="tat")
    dur = float(F.probe(dst).duration)
    tong = sum(e - s for s, e in segs)
    ok(abs(dur - tong) < 0.2, "độ dài đúng", f"{dur:.2f} vs {tong:.2f}")
    t = [x["giay"] for x in log]
    ok(len(log) <= SC.ngan_sach(tong), "số tiếng <= ngân sách",
       f"{len(log)} tiếng: {[(x['giay'], x['loai']) for x in log]}")
    ok(all(b - a >= CACH_CHOT - 0.02 for a, b in zip(t, t[1:])),
       "các tiếng cách >= 2 s trên file thật")
    ok(not any(x["vai"] == "nối" and x["loai"] == "pop" for x in log),
       "không tiếng ở chỗ nối liền mạch")
    ok(len({SC.ho_tieng(x["ten"]) for x in log}) == len(log),
       "không lặp họ tiếng trong clip")
    ok(len(log) >= 1, "vẫn có tiếng (không câm hết)")
    pk = _dinh(dst)
    ok(pk <= -0.5, "đỉnh file không chạm trần", f"{pk:.2f} dBFS")
    # đối chứng: đường cũ vẫn chạy được, và chèn NHIỀU hơn ở cùng clip
    os.environ["BQ_SFX_CU"] = "1"
    try:
        log_cu: list = []
        F.export_canvas_clip(src, os.path.join(d, "cu.mp4"), segs,
                             (0.5, 0.5, 1.0), bg="blur", out_w=540,
                             out_h=960, encoder="libx264", fx_whoosh=True,
                             join_categories=cats, hieu_ung="vua",
                             tieng_dong_log=log_cu, chuyen_canh="tat")
    finally:
        os.environ.pop("BQ_SFX_CU", None)
    ok(len(log_cu) > len(log), "đối chứng: đường CŨ chèn nhiều hơn",
       f"cũ {len(log_cu)} -> mới {len(log)}")


def ca7() -> None:
    print("\n[CA 7] không đụng khoá chống trùng")
    sv = (REPO / "app" / "services.py").read_text("utf-8")
    ok("sfx_chon" not in sv and "BQ_SFX_CU" not in sv,
       "services.py không biết module mới (khoá job không đổi)")
    tree = ast.parse((REPO / "app" / "core" / "sfx_chon.py").read_text("utf-8"))
    imp = {n.module for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom) and n.module}
    imp |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
            for a in n.names}
    ok(not any(m.startswith("app.") for m in imp),
       "sfx_chon thuần (không import app khác)", str(imp))


if __name__ == "__main__":
    for ca in (ca1, ca2, ca3, ca4, ca5, ca6, ca7):
        try:
            ca()
        except Exception as e:  # noqa: BLE001 — chết giữa chừng = HỎNG, có tên
            HONG += 1
            print(f"  HỎNG {ca.__name__} NỔ: {type(e).__name__}: {e}")
    print(f"\nCỔNG 105: ĐẠT {DAT} · HỎNG {HONG}")
    sys.exit(1 if HONG else 0)
