# -*- coding: utf-8 -*-
r"""ĐO MỤC A (1)+(2) — BẤT BIẾN EN/VI + CÓ GOM CHỮ HÁN THẬT KHÔNG.

    .venv\Scripts\python _do_bb_cjk.py

(1) BẤT BIẾN: `_gom_cjk` chỉ được đụng đường CJK. Dựng .ass cho MỌI preset ×
    nhiều bộ tham số × lời ANH và lời VIỆT, so TỪNG BYTE với bản mã TRƯỚC khi
    sửa (mặc định = CHA của commit đưa `_gom_cjk` vào; `BQ_MOC_REF` ép tay).
    CHỐNG PASS OAN (bài học cổng 21/36): bản mốc phải KHÁC bản đang test, và
    nếu TRÙNG thì chỉ tha khi HEAD không phải hậu duệ của mốc.

(2) CÓ GOM THẬT: câu tiếng Trung THẬT -> đếm số cụm/số dòng Dialogue TRƯỚC và
    SAU khi sửa, in ra để nhìn bằng mắt.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
T = tempfile.mkdtemp(prefix="bbcjk_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
import _test_guard  # noqa: E402,F401 - CẤM test đụng máy anh Hùng

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import captions as C  # noqa: E402

FAIL: list[str] = []
W, H = 1080, 1920
SIZE = int(H * 0.055)


def kiem(ok, nhan, ct=""):
    print(("  DAT  " if ok else "  HONG ") + nhan + ("" if ok else f"   << {ct}"))
    if not ok:
        FAIL.append(nhan)


# lời ANH và lời VIỆT — đúng thứ anh Hùng đang chạy sản xuất
TU_EN = ["this", "is", "the", "story", "nobody", "ever", "told", "you",
         "but", "it", "changed", "everything", "for", "me", "today"]
TU_VI = ["chuyện", "này", "không", "ai", "dám", "kể", "cho", "bạn", "nghe",
         "nhưng", "nó", "đổi", "hết", "mọi", "thứ"]
# câu tiếng TRUNG THẬT — whisper trả TỪNG KÝ TỰ nên mỗi ký tự là 1 "từ"
CAU_TRUNG = "他们发现东丝为丽借助金属探测仪仔细检查了整片区域"
CAU_NHAT = "これは誰も語らなかった話ですが全てを変えました"


def _words(tu, buoc=0.36, t0=0.2):
    t, ws = t0, []
    for w in tu:
        ws.append({"start": round(t, 3), "end": round(t + buoc - 0.03, 3),
                   "word": w})
        t += buoc
    return ws, round(t + 0.5, 3)


def dung(mod, preset, tu, buoc=0.36, **kw):
    ws, dur = _words(tu, buoc)
    p = os.path.join(T, re.sub(r"\W+", "_", preset)[:30]
                     + f"_{abs(hash(str(sorted(kw.items())) + str(tu[:2])))%99999}.ass")
    ok = mod.build_ass(ws, [(0.0, dur)], p, out_w=W, out_h=H,
                       font="Montserrat", size=SIZE, ny=0.70, preset=preset,
                       **kw)
    txt = open(p, encoding="utf-8").read() if ok else ""
    return ok, txt


BO_THAM_SO = (
    {},
    {"cap_case": "upper", "hook": "GIẬT TÍT", "hook_dur": 1.5},
    {"color": "#00FF88", "cap_ow": 0.2, "delay": -0.1},
    {"extra_cues": [(0.4, 1.2, "ai kể", "word"),
                    (1.5, 2.4, "cả câu", "sent")],
     "narr_preset": "Karaoke hồng"},
)


def moc_doi_chung() -> str:
    m = os.environ.get("BQ_MOC_REF", "")
    if m:
        return m
    r = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H",
                        "--reverse", "-S", "_gom_cjk", "--",
                        "app/core/captions.py"], capture_output=True)
    ds = (r.stdout or b"").decode().split()
    return f"{ds[0]}^" if ds else "HEAD"


def main() -> int:
    print(f"[work] {T}")

    # ═══════════════ (1) BẤT BIẾN EN/VI ═══════════════
    moc = moc_doi_chung()
    print(f"\n== A1. BẤT BIẾN: EN + VI ra .ass GIỐNG TỪNG BYTE bản "
          f"`{moc[:12]}` ==")
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{moc}:app/core/captions.py"], capture_output=True)
    nay = (REPO / "app" / "core" / "captions.py").read_bytes()
    kiem(r.returncode == 0 and len(r.stdout) > 3000,
         f"lấy được captions.py của mốc `{moc[:12]}`",
         f"rc={r.returncode} · {len(r.stdout)} byte")
    if r.returncode != 0:
        return 2
    trung = r.stdout.strip() == nay.strip()
    if trung:
        # cùng chốt như cổng 36 CA 8: trùng + HEAD là hậu duệ của mốc = mốc ĐÃ
        # chứa bản sửa -> phép so vô nghĩa. Trùng mà KHÔNG phải hậu duệ thì
        # nhánh này không đụng file -> bất biến đúng do xây dựng.
        hd = subprocess.run(["git", "-C", str(REPO), "merge-base",
                             "--is-ancestor", moc.rstrip("^") or "HEAD", "HEAD"],
                            capture_output=True).returncode == 0
        kiem(not hd, "CHỐNG PASS OAN: bản mốc phải KHÁC bản đang test",
             f"mốc {len(r.stdout)} byte == nay {len(nay)} byte và HEAD là hậu "
             f"duệ -> so nó với chính nó (đặt BQ_MOC_REF)")
    else:
        print(f"  (mốc {len(r.stdout)} byte · nay {len(nay)} byte — KHÁC nhau, "
              "phép so có nghĩa)")
    cu_py = os.path.join(T, "captions_cu.py")
    open(cu_py, "wb").write(r.stdout)
    spec = importlib.util.spec_from_file_location("captions_cu", cu_py)
    CU = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(CU)   # type: ignore

    for nhan, tu in (("ANH", TU_EN), ("VIỆT", TU_VI)):
        khac, n = [], 0
        for ten in CU.CAPTION_PRESETS:
            for kw in BO_THAM_SO:
                for buoc in (0.36, 0.09):     # lời thường + lời RẤT nhanh
                    n += 1
                    _, a = dung(C, ten, tu, buoc, **kw)
                    _, b = dung(CU, ten, tu, buoc, **kw)
                    if a != b:
                        khac.append(f"{ten}/buoc={buoc}/{list(kw)[:2]}")
        kiem(not khac, f"lời {nhan}: {n} lượt dựng .ass "
                       f"({len(CU.CAPTION_PRESETS)} preset × {len(BO_THAM_SO)} "
                       f"bộ × 2 nhịp) KHÔNG đổi 1 byte",
             f"{len(khac)} lượt KHÁC: {khac[:5]}")

    # bất biến ở tầng HÀM: không có ký tự CJK -> trả Y HỆT list vào
    ws_vi = [[0.2, 0.5, w, 0] for w in TU_VI]
    kiem(C._gom_cjk(list(ws_vi)) == ws_vi,
         "_gom_cjk(lời VIỆT) trả Y HỆT list vào")
    kiem(C._noi_cum(TU_EN) == " ".join(TU_EN),
         "_noi_cum(lời ANH) == ' '.join(...)")

    # ═══════════════ (2) CÓ GOM THẬT ═══════════════
    print("\n== A2. CÓ GOM THẬT: chữ Hán 1 ký tự -> CỤM ĐỌC ĐƯỢC ==")
    for ten_ngon, cau in (("TRUNG", CAU_TRUNG), ("NHẬT", CAU_NHAT)):
        ky_tu = list(cau)
        ws = [[round(0.2 + i * 0.175, 3), round(0.2 + i * 0.175 + 0.145, 3),
               c, 0] for i, c in enumerate(ky_tu)]
        print(f"\n  --- {ten_ngon} ({len(ky_tu)} ký tự, whisper trả TỪNG KÝ "
              f"TỰ, bước 0,175 s) ---")
        print(f"    câu: {cau}")
        for mode, mx in sorted(C._CJK_MAX.items()):
            ra = C._gom_cjk([list(x) for x in ws], mx)
            cum = [x[2] for x in ra]
            dai = [round(x[1] - x[0], 3) for x in ra]
            print(f"    mode {mode:<8} max={mx}: {len(ws):3d} -> {len(ra):3d} "
                  f"cụm · dài TB {sum(dai)/max(1,len(dai)):.3f}s "
                  f"(trước {0.145:.3f}s) · {cum[:6]}")
            kiem(len(ra) < len(ws),
                 f"{ten_ngon}/{mode}: {len(ws)} -> {len(ra)} cụm (có gom)")

    # ĐO TRÊN FILE .ass THẬT: số dòng Dialogue + số ký tự/dòng, trước vs sau
    print("\n  --- .ass THẬT: số dòng phụ đề + ký tự/dòng (TRƯỚC vs SAU) ---")
    ky_tu = list(CAU_TRUNG)
    ws_tr = [{"start": round(0.2 + i * 0.175, 3),
              "end": round(0.2 + i * 0.175 + 0.145, 3), "word": c}
             for i, c in enumerate(ky_tu)]
    dur = 0.2 + len(ky_tu) * 0.175 + 0.5
    print(f"    {'preset':<34} {'mode':<8} {'dòng CŨ':>8} {'dòng NAY':>9} "
          f"{'kt/dòng CŨ':>11} {'kt/dòng NAY':>12} {'giây/dòng NAY':>14}")
    xau_cu = xau_nay = 0
    for ten in CU.CAPTION_PRESETS:
        ra = {}
        for nhan, mod in (("cu", CU), ("nay", C)):
            p = os.path.join(T, f"tr_{nhan}_{abs(hash(ten))%99999}.ass")
            mod.build_ass(ws_tr, [(0.0, dur)], p, out_w=W, out_h=H,
                          font="Montserrat", size=SIZE, ny=0.70, preset=ten)
            txt = open(p, encoding="utf-8").read()
            dl = [ln for ln in txt.splitlines() if ln.startswith("Dialogue:")]
            chu = [re.sub(r"\{[^}]*\}", "", ln.split(",", 9)[9]) for ln in dl]
            han = [len([c for c in x if "一" <= c <= "鿿"])
                   for x in chu]
            ra[nhan] = (len(dl), sum(han) / max(1, len(han)))
        mode = C.preset_mode(ten)
        gi = dur / max(1, ra["nay"][0])
        print(f"    {ten[:33]:<34} {mode:<8} {ra['cu'][0]:>8d} "
              f"{ra['nay'][0]:>9d} {ra['cu'][1]:>11.2f} {ra['nay'][1]:>12.2f} "
              f"{gi:>14.3f}")
        if ra["cu"][1] < 1.6:
            xau_cu += 1
        if ra["nay"][1] < 1.6:
            xau_nay += 1
    kiem(xau_nay == 0,
         f"số preset còn dưới 1,6 chữ Hán/dòng: CŨ {xau_cu}/"
         f"{len(CU.CAPTION_PRESETS)} -> NAY {xau_nay}", f"{xau_nay} preset")

    print(f"\n{'=' * 70}\nTỔNG: {'TẤT CẢ ĐẠT' if not FAIL else str(len(FAIL)) + ' HỎNG'}")
    for f in FAIL:
        print("  HONG:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
