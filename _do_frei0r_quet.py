# -*- coding: utf-8 -*-
"""Quét TOÀN BỘ plugin frei0r: nạp được không, tên/tác giả/giải thích, tham số.

Chạy:  .venv\\Scripts\\python _do_frei0r_quet.py <thu_muc_plugin>
Ra:    _ket_frei0r.json  +  bảng in ra màn hình

Không tin tên plugin — script này NẠP THẬT bằng ffmpeg trong bin/ rồi đọc log
verbose (vf_frei0r.c in name/author/explanation/num_params + từng tham số).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(ROOT, "bin", "ffmpeg.exe")

RE_HEAD = re.compile(
    r"name:(?P<ten>.*?) author:'(?P<tg>.*?)' explanation:'(?P<gt>.*?)' "
    r"color_model:(?P<cm>\S+) frei0r_version:(?P<fv>\d+) version:(?P<v>\S+) "
    r"num_params:(?P<np>\d+)"
)
RE_PARAM = re.compile(r"idx:(?P<i>\d+) name:'(?P<ten>.*?)' type:(?P<kieu>\S+) explanation:'(?P<gt>.*?)'")


def _thu(ten: str, thu_muc: str, la_src: bool = False) -> dict:
    env = dict(os.environ)
    env["FREI0R_PATH"] = thu_muc
    if la_src:
        vf = ["-f", "lavfi", "-i", f"frei0r_src=size=320x240:framerate=25:filter_name={ten}"]
        cmd = [FFMPEG, "-hide_banner", "-v", "verbose", *vf, "-frames:v", "2", "-f", "null", "-"]
    else:
        cmd = [
            FFMPEG, "-hide_banner", "-v", "verbose",
            "-f", "lavfi", "-i", "testsrc2=s=320x240:r=25:d=0.2",
            "-vf", f"frei0r=filter_name={ten}",
            "-frames:v", "2", "-f", "null", "-",
        ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=40, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"ten_module": ten, "nap": False, "loi": "TIMEOUT"}
    log = (p.stderr or "") + (p.stdout or "")
    m = RE_HEAD.search(log)
    if not m:
        loi = ""
        for dong in log.splitlines():
            d = dong.strip()
            if any(k in d for k in ("Could not find module", "Error", "error", "Invalid", "not found")):
                loi = d
                break
        return {"ten_module": ten, "nap": False, "rc": p.returncode, "loi": loi or "khong doc duoc"}
    d = m.groupdict()
    params = []
    for pm in RE_PARAM.finditer(log):
        g = pm.groupdict()
        if int(g["i"]) < int(d["np"]) and not any(x["idx"] == int(g["i"]) for x in params):
            params.append({"idx": int(g["i"]), "ten": g["ten"], "kieu": g["kieu"], "gt": g["gt"]})
    return {
        "ten_module": ten,
        "nap": p.returncode == 0,
        "rc": p.returncode,
        "ten": d["ten"].strip(),
        "tac_gia": d["tg"],
        "giai_thich": d["gt"],
        "color_model": d["cm"],
        "so_tham_so": int(d["np"]),
        "tham_so": params,
        "la_src": la_src,
    }


def main() -> int:
    thu_muc = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FREI0R_PATH", "")
    if not thu_muc or not os.path.isdir(thu_muc):
        print("Thieu thu muc plugin frei0r")
        return 2
    tens = sorted(f[:-4] for f in os.listdir(thu_muc) if f.lower().endswith(".dll"))
    print(f"[quet] {len(tens)} file .dll trong {thu_muc}")
    ket: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(lambda t: _thu(t, thu_muc), tens):
            ket.append(r)
    # nhung cai khong nap duoc voi tu cach FILTER, thu lai voi tu cach SOURCE
    lai = [r["ten_module"] for r in ket if not r["nap"]]
    src_ok = {}
    if lai:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for r in ex.map(lambda t: _thu(t, thu_muc, True), lai):
                if r.get("nap"):
                    src_ok[r["ten_module"]] = r
    ket = [src_ok.get(r["ten_module"], r) for r in ket]

    ok = [r for r in ket if r["nap"]]
    fail = [r for r in ket if not r["nap"]]
    print(f"\n=== NAP DUOC: {len(ok)}/{len(tens)}  (filter {sum(1 for r in ok if not r.get('la_src'))}, "
          f"source {sum(1 for r in ok if r.get('la_src'))}) ===")
    for r in sorted(ok, key=lambda x: x["ten_module"]):
        kind = "SRC" if r.get("la_src") else "flt"
        print(f"  [{kind}] {r['ten_module']:<28} {r['ten'][:34]:<34} p={r['so_tham_so']:<2} {r['giai_thich'][:52]}")
    print(f"\n=== KHONG NAP DUOC: {len(fail)} ===")
    for r in sorted(fail, key=lambda x: x["ten_module"]):
        print(f"  {r['ten_module']:<28} {str(r.get('loi'))[:96]}")
    with open(os.path.join(ROOT, "_ket_frei0r.json"), "w", encoding="utf-8") as f:
        json.dump(ket, f, ensure_ascii=False, indent=1)
    print("\n-> _ket_frei0r.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
