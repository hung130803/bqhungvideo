# -*- coding: utf-8 -*-
r"""ĐO TRƯỚC — bảng từ khoá `lop_phu.py` bắn NHẦM bao nhiêu khi đọc LỜI THOẠI.

    .venv\Scripts\python _do_lop_phu_loi.py [--so 8] [--giay 150]

Đường lớp phủ hiện nay đọc `vision_digest` (mô tả TIẾNG ANH do model sinh ra).
VIỆC 2 thêm đường đọc **LỜI THOẠI** — tiếng của video, phần lớn là TIẾNG VIỆT
CÓ DẤU. `lop_phu._khong_dau` bỏ dấu trước khi dò, nên mỗi từ khoá tiếng Việt
trong bảng đều có thể đụng một từ KHÁC NGHĨA HẲN:
    `tuyết` -> `tuyet` đụng **tuyệt vời** · `mưa` -> `mua` đụng `mùa đông`
    `máu` -> `mau` đụng `màu sắc`
Đo bằng LỜI THẬT của anh Hùng (Groq chép), KHÔNG đoán:
  1. từ khoá nào bắn trên corpus, câu nào làm nó bắn (người đọc tự phán đúng/sai)
  2. cảnh nào ĐỦ ĐIỂM nếu nối thẳng lời vào `chon_lop_phu` — tức là clip nào sẽ
     bị rơi tuyết/bay tim nếu KHÔNG canh bẫy dấu.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="dolp_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WHISPER_PROVIDER"] = "groq"

_env = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
        / "BQHungVideo" / ".env")
if _env.exists():
    for _ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF = str(REPO / "bin" / "ffmpeg.exe")
FPROBE = str(REPO / "bin" / "ffprobe.exe")
_NOWIN = 0x08000000 if os.name == "nt" else 0
CACHE = REPO / "_do_lop_phu_loi_cache.json"

KHO = {
    "viet": ([r"D:\video ssmatool\video viêt"],
             "[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩị"
             "òóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", 25.0),
    "nhat": ([r"D:\video ssmatool\video nhật dài"], "[぀-ヿ一-鿿]", 60.0),
    "han":  ([r"D:\video ssmatool\video hàn dài",
              r"D:\video ssmatool\video hàn"], "[가-힯]", 40.0),
    "anh":  ([r"D:\video ssmatool\video mỹ"], "", 60.0),
}


def _dai(p: Path) -> float:
    try:
        r = subprocess.run(
            [FPROBE, "-v", "quiet", "-print_format", "json", "-show_format",
             str(p)], capture_output=True, text=True, encoding="utf-8",
            timeout=30, creationflags=_NOWIN)
        return float(json.loads(r.stdout or "{}")
                     .get("format", {}).get("duration") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def chon_nguon(nhom: str, so: int, gmax=1800.0) -> list:
    import re
    ds, chu, gmin = KHO[nhom]
    rx = re.compile(chu, re.I) if chu else None
    ung = []
    for d in ds:
        p = Path(d)
        if not p.is_dir():
            continue
        for f in p.rglob("*.mp4"):
            try:
                mb = f.stat().st_size / 1048576
            except OSError:
                continue
            if not (2.0 <= mb <= 300.0) or (rx and not rx.search(f.name)):
                continue
            ung.append((hashlib.sha1(f.name.encode("utf-8",
                                                   "replace")).hexdigest(), f))
    ung.sort()
    ra = []
    for _h, f in ung:
        g = _dai(f)
        if gmin <= g <= gmax:
            ra.append((f, g))
        if len(ra) >= so:
            break
    return ra


def chep_loi(f: Path, giay: float) -> dict:
    from app.core import transcribe as TR
    wav = _SB / "a.wav"
    g = _dai(f)
    t0 = max(0.0, min(g * 0.25, max(0.0, g - giay - 1)))
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-ss", f"{t0:g}", "-i", str(f),
         "-t", f"{giay:g}", "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(wav)], capture_output=True, timeout=600,
        creationflags=_NOWIN)
    if r.returncode != 0 or not wav.exists():
        return {}
    try:
        return TR.transcribe(str(wav), language=None) or {}
    except Exception:  # noqa: BLE001
        return {}
    finally:
        try:
            wav.unlink()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", type=int, default=8)
    ap.add_argument("--giay", type=float, default=150.0)
    a = ap.parse_args()
    print(f"[sandbox] {_SB}")
    import app.queue.jobs  # noqa: F401
    from app.core import lop_phu as LP

    # ── corpus (cache lại để chạy nhiều lượt không tốn lượt Groq)
    kho_tr = {}
    if CACHE.exists():
        try:
            kho_tr = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            kho_tr = {}
    can = []
    moi = max(2, a.so // len(KHO)) + 2
    theo = {n: chon_nguon(n, moi) for n in KHO}
    for i in range(moi):
        for n in KHO:
            if i < len(theo[n]):
                can.append((n, theo[n][i][0]))
    lay = []
    for n, f in can:
        k = f"{n}|{f.name}"
        if k not in kho_tr:
            if len([x for x in lay if x[0] == n]) >= max(2, a.so // len(KHO)):
                continue
            tr = chep_loi(f, a.giay)
            if len((tr or {}).get("segments") or []) < 4:
                print(f"  (bỏ {f.name[:40]})")
                continue
            kho_tr[k] = tr
            CACHE.write_text(json.dumps(kho_tr, ensure_ascii=False),
                             encoding="utf-8")
        lay.append((n, f.name, kho_tr[k]))
        if len(lay) >= a.so:
            break
    print(f"[corpus] {len(lay)} video · "
          + ", ".join(sorted({x[0] for x in lay})))

    # ── 1. TỪ KHOÁ NÀO BẮN, VÌ CÂU NÀO
    print("\n══ 1. TỪ KHOÁ BẮN TRÊN LỜI THẬT (người đọc tự phán đúng/sai) ══")
    ban = {}
    for nhom, ten, tr in lay:
        for c in (tr or {}).get("segments") or []:
            cau = str(c.get("text") or "").strip()
            if not cau:
                continue
            t = LP._khong_dau(cau)
            for k, l in LP.LUAT.items():
                for nhan, mau, tho in (("MẠNH", l._re_manh, l.manh),
                                       ("phụ", l._re_phu, l.phu),
                                       ("CẤM", l._re_cam, l.cam)):
                    for r, tu in zip(mau, tho):
                        if r.search(t):
                            ban.setdefault((k, nhan, tu), []).append(
                                (nhom, cau[:78]))
    for (k, nhan, tu), vs in sorted(ban.items(),
                                    key=lambda x: (-len(x[1]), x[0])):
        print(f"  {k:12s} {nhan:5s} «{tu}» x{len(vs)}")
        for nhom, cau in vs[:2]:
            print(f"        [{nhom}] {cau}")

    # ── 2. CẢNH NÀO ĐỦ ĐIỂM nếu nối THẲNG lời vào (chưa canh bẫy dấu)
    print("\n══ 2. NẾU NỐI THẲNG LỜI (mỗi CÂU = 1 mốc) — cảnh nào đủ điểm ══")
    n_bat = 0
    for nhom, ten, tr in lay:
        ds = [{"t": float(c.get("start") or 0), "desc": str(c.get("text") or ""),
               "act": 5, "loi": True}
              for c in (tr or {}).get("segments") or []]
        chon, ly = LP.chon_lop_phu(ds, "", 60.0, "vua")
        dau = "*** BẬT" if chon else "   bỏ  "
        if chon:
            n_bat += 1
        print(f"  {dau} [{nhom}] {ten[:42]}")
        print(f"          {ly[:150]}")
    print(f"\n  [số đo] {n_bat}/{len(lay)} clip sẽ được thêm lớp phủ")

    # ── 3. BA BẪY DẤU ANH HÙNG NÊU ĐÍCH DANH
    print("\n══ 3. BẪY BỎ DẤU — 3 ca anh Hùng nêu đích danh ══")
    BAY = [
        ("tuyệt vời quá đi mất", "tuyet_roi", "tuyết"),
        ("mùa đông năm nay", "mua_roi", "mưa"),
        ("màu sắc rất đẹp", "trai_tim", "máu (CẤM)"),
        ("thế là rồi xong", "la_roi", "lá rơi"),
        ("rất tiếc phải nói", "confetti", "tiệc"),
        ("anh cứ làm đi", "tia_sang", "ảnh cũ"),
        ("anh nên nghỉ ngơi", "dom_bokeh", "ánh nến"),
        ("nằm mơ thấy", "mua_roi", "nấm mồ"),
        ("có đâu mà lo", "trai_tim", "cô dâu"),
        ("lịch sự lắm", "bui_phim", "lịch sử"),
        ("trời lạnh mà ấm áp", "ma_quai", "ma ám"),
        ("có điện rồi", "tia_sang", "cổ điển"),
    ]
    n_cu = n_moi = 0
    for cau, canh, y in BAY:
        l = LP.LUAT[canh]
        t_cu, t_moi = LP._khong_dau(cau), LP._ha(cau)
        cu = [tu for r, tu in zip(l._re_manh, l.manh) if r.search(t_cu)]
        moi = [tu for rs, tu in zip(l._rd_manh, l.manh)
               if any(x.search(t_moi) for x in rs)]
        n_cu += bool(cu)
        n_moi += bool(moi)
        print(f"  CŨ {'NHẦM' if cu else 'sạch'} · NAY "
              f"{'NHẦM' if moi else 'sạch'}   «{cau}» -> {canh} "
              f"(ý muốn: {y}){' ' + str(cu) if cu else ''}")
    print(f"\n  [số đo] bẫy bắn NHẦM: bảng BỎ DẤU {n_cu}/{len(BAY)} · "
          f"bảng CÓ DẤU {n_moi}/{len(BAY)}")

    # ── 4. CÂU TIẾNG VIỆT ĐÚNG NGHĨA vẫn phải khớp (không sửa quá tay)
    print("\n══ 4. CÂU ĐÚNG NGHĨA VẪN PHẢI KHỚP (chống sửa quá tay) ══")
    THAT = [("ngoài trời tuyết rơi trắng xoá", "tuyet_roi"),
            ("hôm nay là đám cưới của cô dâu", "trai_tim"),
            ("chúc mừng sinh nhật, bánh kem đây", "confetti"),
            ("trời mưa suốt cả buổi chiều", "mua_roi"),
            ("lá vàng rơi đầy sân mùa thu", "la_roi"),
            ("ngọn lửa cháy rực trong lò sưởi", "tan_lua"),
            ("nghĩa trang lúc nửa đêm rất ghê rợn", "ma_quai")]
    n_ok = 0
    for cau, canh in THAT:
        l = LP.LUAT[canh]
        moi = [tu for rs, tu in zip(l._rd_manh, l.manh)
               if any(x.search(LP._ha(cau)) for x in rs)]
        n_ok += bool(moi)
        print(f"  {'khớp' if moi else 'MẤT'}  «{cau}» -> {canh} {moi}")
    print(f"\n  [số đo] câu đúng nghĩa còn khớp: {n_ok}/{len(THAT)}")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(rc)
