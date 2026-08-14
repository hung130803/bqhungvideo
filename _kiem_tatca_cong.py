# -*- coding: utf-8 -*-
r"""LƯỢT KIỂM ĐỘC LẬP v2.18.0 — chạy **TOÀN BỘ** `_test_*.py` trong repo.

Khác `_ra_cong.py`: file đó chỉ liệt kê 23 cổng chọn tay, còn ở đây quét THẬT
thư mục nên không cổng nào trốn được (48 file `_test_*.py` tại 08/08/2026).

LUẬT SỐ 1 của máy anh Hùng: **tối đa 1 ffmpeg cùng lúc** -> chạy TUẦN TỰ,
`BQ_FFMPEG_SLOTS=1`, không song song, không benchmark.

    .venv\Scripts\python.exe _kiem_tatca_cong.py            # cả bộ
    .venv\Scripts\python.exe _kiem_tatca_cong.py --chi pipe # lọc theo tên
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

# Hạn giờ riêng cho cổng nặng (giây); còn lại 900s.
HAN = {
    "_test_da_quoc_gia.py": 3600,
    "_test_chuyen_canh.py": 3000,
    "_test_hieu_ung_ai.py": 3000,
    "_test_chon_doan.py": 2100,
    "_test_lien_thong.py": 2100,
    "_test_ca_bien_xuat.py": 2100,
    "_test_pipe_e2e.py": 1500,
    "_test_pipe_integ.py": 1500,
    "_test_100_kenh.py": 1500,
    "_test_hieu_ung_khung.py": 2100,
    "_test_tieng_hieu_ung.py": 2100,
    "_test_shader.py": 1500,
    "_test_tieu_de_part.py": 1500,
    "_test_rac_va_bao.py": 1800,
    "_test_hlbox.py": 1200,
    "_test_muot_tram_kenh.py": 1200,
    "_test_pipe_overlap.py": 1200,
}

# ── MỐC ĐỐI CHỨNG RIÊNG TỪNG CỔNG — đặt THEO FILE, KHÔNG đặt chung cả lượt ──
# Hai cách sai đối xứng nhau, cả hai đều đã cắn thật ở repo này:
#  · để cổng so với `main`: gộp nhánh xong thì `main` CHÍNH LÀ bản đang test
#    -> "so nó với chính nó" -> **PASS OAN VĨNH VIỄN** (cổng 36 CA8, cổng 12
#    của `_test_hlbox.py`).
#  · đặt MỘT `BQ_MOC_REF` chung cho cả lượt: cổng nào KHÔNG đụng file nó so
#    sẽ thấy mốc TRÙNG bản đang test rồi **ĐỎ OAN** — mà cổng đỏ oan thì
#    người ta bỏ qua nó, nguy hiểm hơn hẳn (bài học cổng 41 và 47).
# Vì vậy: chỉ ép mốc cho cổng nào mặc định đang trỏ về `main`, và ĐỂ YÊN cổng
# đã có mốc SHA riêng (`_test_lop_phu.py` = 7b1da35/494a541 · `_test_cjk_va` +
# `_test_dubbing_cjk` = 841c773 · `_test_xem_hinh_kenh` = 378230e), cùng cổng
# TỰ TÌM commit đưa tính năng vào rồi lấy CHA (`_test_hlbox`, `_test_rac_va_bao`).
#: Bản ĐÃ PHÁT HÀNH liền trước — đổi mỗi lần phát hành.
MOC_TRUOC = os.environ.get("BQ_MOC_TRUOC_BAN", "v2.25.0")
MOC = {
    # so `app/core/ffmpeg_utils.py`; mặc định trong file là `main` -> phải ép
    "_test_chuyen_canh.py": {"BQ_MOC_REF": MOC_TRUOC},
    "_test_rac_va_bao.py": {"BQ_MOC_REF": MOC_TRUOC},
    # so `app/services.py` + `app/core/ffmpeg_utils.py` (cổng 56 CA16/CA23)
    "_test_che_chu.py": {"BQ_MOC_REF": MOC_TRUOC},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chi", default="")
    ap.add_argument("--bo", default="", help="bỏ qua cổng có tên chứa chuỗi này")
    ap.add_argument("--ra", default="_kiem_ketqua.json")
    a = ap.parse_args()

    ds = sorted(p.name for p in REPO.glob("_test_*.py"))
    if a.chi:
        ds = [f for f in ds if a.chi in f]
    if a.bo:
        ds = [f for f in ds if a.bo not in f]
    py = sys.executable

    env = dict(os.environ)
    env["BQ_TEST"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["BQ_FFMPEG_SLOTS"] = "1"          # LUẬT SỐ 1

    print("=" * 78)
    print(f"TOÀN BỘ CỔNG — {len(ds)} file · {py}")
    print("=" * 78, flush=True)

    ket = []
    for i, f in enumerate(ds, 1):
        han = HAN.get(f, 900)
        t0 = time.time()
        env_f = dict(env, **MOC.get(f, {}))     # mốc RIÊNG cho cổng cần mốc
        try:
            r = subprocess.run([py, f], cwd=str(REPO), capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=han, env=env_f)
            rc, qh = r.returncode, False
            ra = (r.stdout or "") + "\n===STDERR===\n" + (r.stderr or "")
        except subprocess.TimeoutExpired as e:
            rc, qh = -9, True
            ra = "QUÁ HẠN\n" + str(getattr(e, "stdout", "") or "")[-4000:]
        dt = time.time() - t0
        # ── CRASH NATIVE KHÔNG LÀM ĐỔI MÃ THOÁT — PHẢI TỰ ĐI TÌM ──
        # Đo thật 14/08/2026: `_test_app_smoke.py` in ra "✅ KHÔNG LỖI" và
        # **rc=0**, trong khi stderr có *"Windows fatal exception: access
        # violation"* — `import torch` trong tiến trình đã nạp Qt làm
        # `torch/lib/c10.dll` nổ ở tầng native. `faulthandler` (app bật từ
        # cổng 6) CHỘP ĐƯỢC rồi in ra, nhưng nó là VEH: in xong TRẢ QUYỀN cho
        # handler khác, torch tự gượng dậy ném OSError, `except` của app nuốt
        # -> mọi thứ "xanh". Tức lượt kiểm toàn bộ đang PASS OAN cho đúng loại
        # lỗi làm CHẾT APP trên máy anh Hùng.
        # Vì vậy: thấy dấu hiệu crash native trong output là FAIL, bất kể rc.
        _crash = [d for d in ("Windows fatal exception",
                              "Fatal Python error",
                              "Segmentation fault")
                  if d in ra]
        ok = rc == 0 and not qh and not _crash
        dong = [x for x in ra.splitlines() if x.strip()]
        tom = ""
        for x in reversed(dong[-25:]):
            if any(k in x for k in ("ĐẠT", "FAIL", "LỖI", "PASS", "✅", "❌", "hỏng")):
                tom = x.strip()[:90]
                break
        if _crash:      # ĐÈ LÊN dòng tóm tắt: bản thân dòng đó đang nói "ĐẠT"
            tom = f"CRASH NATIVE dù rc={rc}: {_crash[0]}"
        _m = MOC.get(f)
        print(f"[{i:2d}/{len(ds)}] [{'ĐẠT ' if ok else 'FAIL'}] {f:32s} "
              f"{dt:7.1f}s rc={rc}  {tom}"
              + (f"   [mốc {list(_m.values())[0]}]" if _m else ""), flush=True)
        if not ok:
            for x in dong[-18:]:
                print(f"        | {x[:120]}", flush=True)
        ket.append({"file": f, "rc": rc, "giay": round(dt, 1), "dat": ok,
                    "quahan": qh, "crash": bool(_crash), "tom": tom})
        (REPO / "_ketqua_log").mkdir(exist_ok=True)
        (REPO / "_ketqua_log" / f"{f}.txt").write_text(
            ra, encoding="utf-8", errors="replace")

    n = sum(1 for x in ket if x["dat"])
    print("\n" + "=" * 78)
    print(f"ĐẠT {n}/{len(ket)} · tổng {sum(x['giay'] for x in ket)/60:.1f} phút")
    for x in ket:
        if not x["dat"]:
            print(f"   ✗ {x['file']} rc={x['rc']} "
                  f"{'(QUÁ HẠN)' if x['quahan'] else ''} {x['tom']}")
    print("=" * 78)
    (REPO / a.ra).write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    return 0 if n == len(ket) else 1


if __name__ == "__main__":
    sys.exit(main())
