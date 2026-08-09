# -*- coding: utf-8 -*-
r"""ĐO LẠI SAU KHI SỬA — `build_vision_digest` THẬT, tuần tự vs song song.

    .venv\Scripts\python _do_vision_ss.py

`_do_vision_219.py` đo trên các mảnh rời (trích khung / gọi API) để TÌM nút
thắt. Script này đo **đúng cái app gọi** (`build_vision_digest`) ở hai mức
`VISION_SONG_SONG`, trên CÙNG một video, và **ĐAN XEN** hai mức để máy anh
Hùng đang bận không làm lệch kết quả (bài học "đo A/B phải đan xen").

Kiểm luôn 2 điều quan trọng hơn tốc độ:
  * số mốc digest KHÔNG được ít đi (nhanh mà mất dữ liệu là hỏng);
  * mô tả phải gán ĐÚNG mốc giây (song song rất dễ lẫn `i` giữa các batch).
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="dovss_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USE_VISION"] = "1"
os.environ["VISION_CUT"] = "1"
os.environ["LIGHT_MODE"] = "0"

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

_NOWIN = 0x08000000 if os.name == "nt" else 0


def _so(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def main() -> int:
    print(f"[sandbox] {_SB}")
    import app.queue.jobs  # noqa: F401
    from app.core import vision_digest as VD
    from config import settings

    keys = settings.groq_keys()
    print(f"[key Groq] {len(keys)} key · model={settings.GROQ_VISION_MODEL}")
    if not keys:
        print("0 key -> không đo được"); return 2

    ep = os.environ.get("BQ_VD_SRC", "")
    src = None
    if ep and Path(ep).exists():
        src = Path(ep)
    else:
        ung = []
        for d in (r"D:\video ssmatool\video mỹ", r"D:\video ssmatool\video viêt"):
            p = Path(d)
            if p.is_dir():
                for f in p.rglob("*.mp4"):
                    try:
                        mb = f.stat().st_size / 1048576
                    except OSError:
                        continue
                    if 5.0 <= mb <= 300.0:
                        ung.append((hashlib.sha1(
                            f.name.encode("utf-8", "replace")).hexdigest(), f))
        ung.sort()
        for _h, f in ung:
            r = subprocess.run(
                [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
                 "-show_format", str(f)], capture_output=True, text=True,
                encoding="utf-8", timeout=30, creationflags=_NOWIN)
            try:
                g = float(json.loads(r.stdout or "{}")
                          .get("format", {}).get("duration") or 0)
            except Exception:  # noqa: BLE001
                continue
            if 120.0 <= g <= 1800.0:
                src, dur = f, g
                break
    if src is None:
        print("không tìm được video"); return 2
    r = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
         "-show_format", str(src)], capture_output=True, text=True,
        encoding="utf-8", timeout=30, creationflags=_NOWIN)
    dur = float(json.loads(r.stdout or "{}").get("format", {})
                .get("duration") or 0)
    print(f"[nguồn] {src.name[:60]} · {_so(dur, 1)} giây · "
          f"{VD._CAP} khung / "
          f"{(VD._CAP + VD._BATCH - 1) // VD._BATCH} lượt")

    # ĐAN XEN: TT, SS, TT, SS… — máy anh Hùng luôn có prodown chạy nền, đo
    # liền mạch từng mức đã cho kết luận sai 2 lần (xem MEMORY).
    do: dict = {1: [], 6: []}
    n_moc: dict = {1: [], 6: []}
    vid = 0
    _lan_n = int(os.environ.get("BQ_VD_LAN", "2") or 2)
    for lan in range(_lan_n):
        for ss in (1, 6):
            settings.VISION_SONG_SONG = ss
            vid += 1                     # video_id MỚI -> không đọc cache
            t0 = time.perf_counter()
            dg = VD.build_vision_digest(vid, str(src), dur, bat_buoc=True)
            d = time.perf_counter() - t0
            do[ss].append(d)
            n_moc[ss].append(len(dg))
            print(f"  lượt {lan + 1} · VISION_SONG_SONG={ss}: {_so(d)} giây · "
                  f"{len(dg)} mốc"
                  + (f" · LỖI {VD.LOI_CUOI[:60]}" if VD.LOI_CUOI else ""))
            if lan == 0 and ss == 6 and dg:
                print("       ví dụ mốc:", ", ".join(
                    f"{x['t']:.0f}s act{x['act']}" for x in dg[:6]))
                # mốc phải TĂNG DẦN và không trùng -> gán đúng ảnh, không lẫn
                ts = [x["t"] for x in dg]
                print(f"       mốc tăng dần: {ts == sorted(ts)} · "
                      f"{len(set(ts))} mốc khác nhau / {len(ts)}")

    tt = statistics.median(do[1])
    ss6 = statistics.median(do[6])
    print("\n" + "═" * 68)
    print(f"  TUẦN TỰ (VISION_SONG_SONG=1) : trung vị {_so(tt)} giây · "
          f"min {_so(min(do[1]))} · max {_so(max(do[1]))} · {n_moc[1]} mốc")
    print(f"  SONG SONG (=6)               : trung vị {_so(ss6)} giây · "
          f"min {_so(min(do[6]))} · max {_so(max(do[6]))} · {n_moc[6]} mốc")
    if ss6 > 0:
        print(f"  NHANH HƠN {_so(tt / ss6)}x  ({_lan_n} lượt mỗi mức, ĐAN XEN)")
    # ĐỘ TẢN quyết định có kết luận được không. Groq trả về rất thất thường
    # (đo: cùng mức tuần tự ra 5,65s rồi 47,43s) nên nếu khoảng min-max của hai
    # mức CHỒNG LÊN NHAU thì phép đo này KHÔNG kết luận được gì — phải nói
    # thẳng chứ không được lấy trung vị ra khoe.
    chong = not (max(do[6]) < min(do[1]) or max(do[1]) < min(do[6]))
    print(f"  Hai khoảng min-max CHỒNG NHAU: {chong}"
          + ("  -> KHÔNG kết luận được mức nào nhanh hơn" if chong else ""))
    print(f"  Số mốc KHÔNG ít đi: "
          f"{min(n_moc[6]) >= min(n_moc[1])} "
          f"(song song min {min(n_moc[6])} vs tuần tự min {min(n_moc[1])})")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(rc)
