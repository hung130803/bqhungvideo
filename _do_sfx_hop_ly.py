# -*- coding: utf-8 -*-
"""ĐO TIẾNG ĐỘNG CŨ vs MỚI trên CLIP THẬT (02/11/2026) — phát lại, KHÔNG xuất.

Đọc `clips.signals['da_ap']` của N clip mới nhất (DB mở `immutable=1`, KHÔNG
ghi một byte). Mỗi clip dựng lại ĐÚNG ứng viên mốc app đã có lúc xuất (điểm nối
thực đã chèn + mọi điểm nhấn hình) rồi chạy 2 cách chọn:
  CŨ = luật trước 02/11 (mọi nối + điểm nhấn cách >= 0,8 s, kiểu lạ -> impact)
       + bốc file trên kho CŨ (bỏ file k2_/s2_), chống lặp theo FILE.
  MỚI = `sfx_chon.chon_moc` + kho mới + chống lặp theo HỌ.
Chốt chống-đạt-oan: số tiếng của arm CŨ phải KHỚP số app đã thật sự chèn.
Không có lời thoại trong phép phát lại -> luật ngữ cảnh lời KHÔNG được đo ở đây
(cổng 105 đo riêng).
"""
import collections
import json
import os
import random
import re
import sqlite3
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import sfx_chon as SC  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
p = os.path.join(os.environ["LOCALAPPDATA"], "BQHungVideo", "studio.db")
db = sqlite3.connect("file:/" + p.replace(os.sep, "/") + "?immutable=1", uri=True)
rows = list(db.execute("select signals from clips where signals like '%da_ap%' "
                       "order by rowid desc limit ?", (N,)))[::-1]

lib_moi = F._sfx_library()
#: so TÊN FILE, không regex đường dẫn: bản đầu dùng regex `[\/]` bị mất
#: dấu `\` -> arm CŨ lẫn file kho MỚI (đo ra họ k2_ trong arm CŨ = tự tố).
lib_cu = {k: [f for f in v if not os.path.basename(f).startswith(("k2_", "s2_"))]
          for k, v in lib_moi.items()}


def cu(cands, dur):
    out = [(t, c, v) for t, c, v, *_ in cands if v == "nối"]
    for t, _c, v, khoa, _ld in cands:
        if v != "nối" and not any(abs(t - x[0]) < 0.8 for x in out):
            out.append((t, F.loai_sfx_theo_hieu_ung(khoa), v))
    return sorted(x for x in out if 0 <= x[0] < dur)


def moi(cands, dur):
    uv = []
    for t, c, v, khoa, ld in cands:
        if v == "nối":
            uv.append({"t": t, "cat": c, "vai": v, "loai_diem": "noi_doan"})
        else:
            cat = SC.nhom_cho_hieu_ung(khoa, ld)
            if cat is None and ld == "hook":
                cat = "transition"
            uv.append({"t": t, "cat": cat, "vai": v, "loai_diem": ld,
                       "khoa": khoa})
    return SC.chon_moc(uv, dur)[0]


def chay(ten, ham, lib, cu_mode):
    os.environ["BQ_SFX_CU"] = "1" if cu_mode else "0"
    F._SFX_LIB_CACHE = lib
    F._SFX_GAN_DAY.clear()
    F._SFX_HO_GAN_DAY.clear()
    rng = random.Random(7)
    cnt, gaps, cats, files, hos, lap_ho, khop = [], [], collections.Counter(), \
        collections.Counter(), collections.Counter(), 0, 0
    vo_duyen = 0
    for (sig,) in rows:
        d = json.loads(sig or "{}")
        da = d.get("da_ap") or {}
        td = da.get("tieng_dong") or []
        try:
            dur = float(d.get("dur") or 0)
        except ValueError:
            continue
        if dur <= 0:
            continue
        noi_by_t = {round(x.get("giay", -1), 2): bool(x.get("noi"))
                    for x in td}
        cands = [(float(x["giay"]), x["loai"], "nối", "", "")
                 for x in td if x.get("vai") == "nối"]
        cands += [(float(h["giay"]), None, "điểm nhấn", h.get("khoa", ""),
                   h.get("loai", "")) for h in (da.get("hieu_ung") or [])]
        sel = ham(cands, dur)
        if cu_mode and len(sel) == len(td):
            khop += 1
        cnt.append(len(sel))
        gaps += [b[0] - a[0] for a, b in zip(sel, sel[1:])]
        for t, c, v in sel:
            if v != "nối":
                k = next((h.get("khoa") for h in da.get("hieu_ung") or []
                          if abs(float(h["giay"]) - t) < 1e-6), "")
                if SC.BANG_HIEU_UNG.get(k, "x") is None:
                    vo_duyen += 1
        picks = F._pick_sfx_by_category([c for _t, c, _v in sel],
                                        seed=rng.randrange(1 << 30),
                                        noi_mocs=[noi_by_t.get(round(t, 2),
                                                               False)
                                                  for t, _c, _v in sel])
        hs = []
        for c, f in picks:
            cats[c] += 1
            if f:
                files[c + "/" + os.path.basename(f)] += 1
                h = SC.ho_tieng(f)
                hos[h] += 1
                hs.append(h)
        if len(hs) != len(set(hs)):
            lap_ho += 1
    tot = sum(cats.values())
    n = len(cnt)
    if cu_mode:
        assert not any(h.startswith(("k2_", "s2_")) for h in hos), (
            "arm CŨ lẫn file kho mới -> phép đo hỏng")
    print(f"\n===== {ten} ({n} clip) =====")
    if cu_mode:
        print(f"chốt: số tiếng phát lại KHỚP app thật ở {khop}/{n} clip")
    print(f"tiếng/clip TB {st.mean(cnt):.2f} · trung vị {st.median(cnt)} · "
          f"max {max(cnt)} · tổng {tot}")
    print(f"cặp liền kề < 2 s: {sum(g < 2 for g in gaps)} / {len(gaps)}")
    print(f"tiếng ở kiểu hình KHÔNG cần tiếng (màu/hạt/thời tiết): {vo_duyen}")
    print("nhóm:", ", ".join(f"{k} {100*v/tot:.1f}%" for k, v in
                              cats.most_common()))
    print(f"file khác nhau: {len(files)} · HỌ khác nhau: {len(hos)}")
    top3 = sum(v for _k, v in hos.most_common(3))
    print(f"3 họ nhiều nhất chiếm {100*top3/tot:.1f}%: {hos.most_common(3)}")
    print(f"họ đứng đầu chiếm {100*hos.most_common(1)[0][1]/tot:.1f}%")
    print(f"clip có >= 2 tiếng CÙNG HỌ: {lap_ho}/{n} "
          f"({100*lap_ho/n:.1f}%)")
    return cnt


chay("CŨ", cu, lib_cu, True)
chay("MỚI", moi, lib_moi, False)
os.environ.pop("BQ_SFX_CU", None)
