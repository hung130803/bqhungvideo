# -*- coding: utf-8 -*-
"""NỢ 1 — ĐO GHÉP CẶP: một câu hỏng thì mất gì.

Hai arm chạy CÙNG bộ chữ, CÙNG mẫu giọng, CÙNG máy đọc THẬT:
  · **TRƯỚC** = `app/core/giong_vieneu.py` của mốc phát hành `bde0fc5`
    (v2.46.1) nạp bằng `git show` thành module RIÊNG — KHÔNG so với `main`
    và KHÔNG so bản đang sửa với chính nó (bài học cổng 36/51/52).
  · **SAU** = bản đang sửa.

Ba cảnh, mỗi cảnh là một hình dạng hỏng ĐO ĐƯỢC THẬT ở `_do_bo_loat.py`:
  `lanh`   — 0 câu hỏng            -> hai arm phải GIỐNG NHAU (đối chứng ÂM)
  `mot_han`— 1 câu chữ Hán `现`    -> đúng cảnh 167/168 của anh Hùng
  `mot_dau`— 1 câu chỉ dấu câu `-` -> im lặng là ĐÚNG, không phải hỏng
  `nhieu`  — 8 câu Hán            -> vượt ngưỡng, PHẢI vẫn bỏ cả loạt
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_bo_loat as B                                       # noqa: E402
from app.core import giong_vieneu as SAU                      # noqa: E402

MOC = os.environ.get("BQ_MOC_BOLOAT", "bde0fc5")
HOP = REPO / "_kq_bo_loat"
HOP.mkdir(exist_ok=True)


def nap_moc():
    """Nạp `giong_vieneu.py` của bản mốc thành module RIÊNG."""
    ma = subprocess.run(["git", "show", f"{MOC}:app/core/giong_vieneu.py"],
                        cwd=REPO, capture_output=True, text=True,
                        encoding="utf-8")
    if ma.returncode != 0 or not ma.stdout:
        raise SystemExit(f"không lấy được bản mốc {MOC}: {ma.stderr[:200]}")
    if "BO_LOAT_TU_SO_CAU" in ma.stdout:
        raise SystemExit(f"mốc {MOC} ĐÃ CHỨA bản vá -> so nó với chính nó, "
                         f"phép đo vô nghĩa. Chọn mốc trước bản vá.")
    m = types.ModuleType("_gv_moc")
    m.__file__ = str(REPO / "app" / "core" / "giong_vieneu.py")
    sys.modules["_gv_moc"] = m
    exec(compile(ma.stdout, m.__file__, "exec"), m.__dict__)
    return m


def bo_cau(canh: str) -> list[str]:
    xs = B._doc_that()[:30]
    if canh == "lanh":
        return xs
    if canh == "mot_han":
        return xs + ["现"]
    if canh == "mot_dau":
        return xs + ["-"]
    if canh == "nhieu":
        return xs + ["现", "他", "可", "而", "就", "但", "这", "那"]
    raise ValueError(canh)


def chay(mod, texts: list[str], ref: str, nhan: str) -> dict:
    sb = mod.thu_muc_vieneu() / f"_tam_ab_{os.getpid()}_{abs(hash(nhan)) % 99999}"
    (sb / "out").mkdir(parents=True, exist_ok=True)
    paths = [str(sb / "out" / f"c{i:04d}.wav") for i in range(len(texts))]
    loi = []
    ok, _w = mod.doc_loat(texts, paths, f"vnb:{ref}", lay_moc=False,
                          on_msg=lambda s: loi.append(s))
    mod._don(sb)
    kq = {"nhan": nhan, "so_cau": len(texts), "so_ok": sum(1 for x in ok if x),
          "mat_giong": not any(ok), "on_msg": loi}
    print(f"  [{nhan}] giữ giọng nhân bản {kq['so_ok']}/{len(texts)} câu"
          f"{'  <-- MẤT SẠCH' if kq['mat_giong'] else ''}")
    for s in loi:
        if "MẤT GIỌNG" in s or "đọc hỏng" in s:
            print(f"        báo lên UI: {s}")
    return kq


if __name__ == "__main__":
    canhs = sys.argv[1:] or ["lanh", "mot_han", "mot_dau", "nhieu"]
    TRUOC = nap_moc()
    ref = B._mau()
    ra = []
    for canh in canhs:
        xs = bo_cau(canh)
        print(f"\n== CẢNH {canh} ({len(xs)} câu) ==")
        a = chay(TRUOC, xs, ref, f"TRUOC/{canh}")
        b = chay(SAU, xs, ref, f"SAU/{canh}")
        ra.append({"canh": canh, "truoc": a, "sau": b})
    (HOP / "ab.json").write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    print("\n== BẢNG ==")
    print(f"{'cảnh':<10}{'câu':>5}{'TRƯỚC giữ':>12}{'SAU giữ':>10}")
    for r in ra:
        print(f"{r['canh']:<10}{r['truoc']['so_cau']:>5}"
              f"{r['truoc']['so_ok']:>12}{r['sau']['so_ok']:>10}")
