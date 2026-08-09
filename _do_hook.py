# -*- coding: utf-8 -*-
r"""ĐO cho VIỆC 1 — gom CHÉP LỜI THẬT nhiều thứ tiếng vào cache rồi chấm.

    .venv\Scripts\python _do_hook.py gom   [--so 16] [--giay 150]
    .venv\Scripts\python _do_hook.py cham  [--n 12]

`gom` gọi Groq THẬT một lần rồi ghi `_do_hook_cache.json`; `cham` chạy lại bộ
chấm trên đúng dữ liệu đó — sửa bảng từ khoá không phải chép lời lại (chép lời
là phần đắt duy nhất). Cache KHÔNG chứa key, chỉ chứa lời + mốc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
_SB = Path(tempfile.mkdtemp(prefix="dohook_"))
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
CACHE = REPO / "_do_hook_cache.json"

KHO = {
    "nhat": ([r"D:\video ssmatool\video nhật dài"], "[぀-ヿ一-鿿]", 60.0),
    "han":  ([r"D:\video ssmatool\video hàn dài",
              r"D:\video ssmatool\video hàn"], "[가-힯]", 40.0),
    "anh":  ([r"D:\video ssmatool\video mỹ"], "", 60.0),
    "viet": ([r"D:\video ssmatool\video viêt"],
             "[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩị"
             "òóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", 25.0),
}


def _dai(p) -> float:
    try:
        r = subprocess.run(
            [FPROBE, "-v", "quiet", "-print_format", "json", "-show_format",
             str(p)], capture_output=True, text=True, encoding="utf-8",
            timeout=30, creationflags=_NOWIN)
        return float(json.loads(r.stdout or "{}")
                     .get("format", {}).get("duration") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def chon(nhom: str, so: int):
    dirs, chu, gmin = KHO[nhom]
    rx = re.compile(chu, re.I) if chu else None
    ung = []
    for d in dirs:
        p = Path(d)
        if not p.is_dir():
            continue
        for f in p.rglob("*.mp4"):
            try:
                mb = f.stat().st_size / 1048576
            except OSError:
                continue
            if not (2.0 <= mb <= 300.0):
                continue
            if rx is not None and not rx.search(f.name):
                continue
            ung.append((hashlib.sha1(
                f.name.encode("utf-8", "replace")).hexdigest(), f))
    ung.sort()
    ra = []
    for _h, f in ung:
        g = _dai(f)
        if g >= gmin:
            ra.append((f, g))
        if len(ra) >= so:
            break
    return ra


def gom(a) -> int:
    from app.core import transcribe as TR
    kho = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else []
    co = {x["file"] for x in kho}
    moi = max(2, a.so // len(KHO))
    for nhom in KHO:
        lay = 0
        for f, g in chon(nhom, moi * 3):
            if lay >= moi:
                break
            if str(f) in co:
                lay += 1
                continue
            wav = _SB / "a.wav"
            giay = min(a.giay, max(20.0, g * 0.8))
            t0 = max(0.0, min(g * 0.25, max(0.0, g - giay - 1)))
            c = [FF, "-y", "-v", "error", "-ss", f"{t0:g}", "-i", str(f),
                 "-t", f"{giay:g}", "-vn", "-ac", "1", "-ar", "16000",
                 "-c:a", "pcm_s16le", str(wav)]
            if subprocess.run(c, capture_output=True, timeout=600,
                              creationflags=_NOWIN).returncode != 0:
                continue
            try:
                tr = TR.transcribe(str(wav), language=None)
            except Exception as e:  # noqa: BLE001
                print(f"  lỗi {f.name[:40]}: {str(e)[:60]}")
                continue
            finally:
                try:
                    wav.unlink()
                except OSError:
                    pass
            segs = [{"start": float(s.get("start", 0)),
                     "end": float(s.get("end", 0)),
                     "text": str(s.get("text") or "")}
                    for s in (tr or {}).get("segments") or []]
            if len(segs) < 4:
                print(f"  bỏ {f.name[:40]} — {len(segs)} câu")
                continue
            kho.append({"nhom": nhom, "file": str(f), "ten": f.name,
                        "lang": str((tr or {}).get("language") or "?"),
                        "giay": giay, "segments": segs})
            lay += 1
            print(f"  + [{nhom}/{kho[-1]['lang']}] {len(segs):3d} câu · "
                  f"{f.name[:56]}")
    CACHE.write_text(json.dumps(kho, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(kho)} video trong cache -> {CACHE.name}")
    return 0


def cham(a) -> int:
    from app.ai import hook_to_mo as HK
    kho = json.loads(CACHE.read_text(encoding="utf-8"))
    n_co = 0
    for v in kho:
        tr = {"segments": v["segments"]}
        segs = [[0.0, float(v["giay"])]]
        r = HK.chon_hook_to_mo(tr, segs, top=a.n)
        print(f"\n─ [{v['nhom']}/{v['lang']}] {v['ten'][:60]}")
        if r:
            n_co += 1
            print(f"   CHỌN {r['diem']:.2f} «{r['cau'][:90]}»")
        else:
            print("   KHÔNG CHỌN ĐƯỢC")
        bang = (r or {}).get("bang") or []
        if not bang:
            cham2 = sorted(((HK.cham_cau(s["text"], s["end"] - s["start"])[0],
                             s["text"]) for s in v["segments"]), reverse=True)
            bang = [{"diem": d, "cau": t, "ly_do": ""} for d, t in cham2[:a.n]]
        for b in bang[:a.n]:
            print(f"      {b['diem']:.2f} «{str(b['cau'])[:76]}» "
                  f"{str(b.get('ly_do', ''))[:52]}")
    print(f"\n[TỔNG] chọn được {n_co}/{len(kho)} video "
          f"({100.0 * n_co / max(1, len(kho)):.0f}%)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("lenh", choices=["gom", "cham"])
    ap.add_argument("--so", type=int, default=16)
    ap.add_argument("--giay", type=float, default=150.0)
    ap.add_argument("--n", type=int, default=8)
    _a = ap.parse_args()
    try:
        rc = gom(_a) if _a.lenh == "gom" else cham(_a)
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(rc)
