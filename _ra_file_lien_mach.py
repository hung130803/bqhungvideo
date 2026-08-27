# -*- coding: utf-8 -*-
"""SINH FILE NGHE THỬ CHO LỜI KÊU "KHÔNG LIÊN TIẾP, ĐƯỢC ĐOẠN RỒI NGHỈ".

Lấy đúng 3 arm mà `_do_khop_video.py` vừa dựng TRONG MỘT LƯỢT CHẠY (cùng bản
tách / chép lời / dịch / FILE GIỌNG — nhiễu LLM triệt tiêu theo cấu tạo) rồi
gom vào `_NGHE_THU_ANH_HUNG/lien_mach/`.

**CHUẨN HOÁ CÙNG −14 LUFS LÀ BẮT BUỘC**, và nó đã do chính `tron_thay_giong`
-> `chuan_do_to` làm trong lượt dựng. Script này **ĐO LẠI** trên file cuối
(sau đời nén AAC — đúng thứ tai nghe) chứ không tin lời hứa; không chuẩn hoá
thì phép nghe thành *"file nào TO hơn"*.

**MD5 PHẢI KHÁC NHAU** — bẫy cache đã sập một lần: hai arm ra cùng một file
thì bảng nghe thử là ba bản sao của một thứ.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from app.core import thay_giong as tg                  # noqa: E402

NGUON = REPO / "_NGHE_THU_ANH_HUNG" / "khop_video"
RA = REPO / "_NGHE_THU_ANH_HUNG" / "lien_mach"
KQ = REPO / "_kq_lienmach"

NHAN = {
    "CU": "1_CU__khong chinh hinh (k=1,000)",
    "MOI": "2_MUC2__chinh video theo giong (ANH HUNG DANG BAT)",
    "MOI3": "3_MUC3__chinh video + doc deu (bo buoc 4c)",
}


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for kh in iter(lambda: f.read(1 << 20), b""):
            h.update(kh)
    return h.hexdigest()


def main() -> int:
    if not NGUON.is_dir():
        print(f"Chưa có {NGUON} — chạy _do_khop_video.py trước")
        return 2
    RA.mkdir(parents=True, exist_ok=True)
    KQ.mkdir(parents=True, exist_ok=True)

    ra: list[dict] = []
    for vid in sorted(p for p in NGUON.iterdir() if p.is_dir()):
        for giong in sorted(p for p in vid.iterdir() if p.is_dir()):
            for f in sorted(giong.glob("*.mp4")):
                arm = f.stem.split("_")[0]
                nhan = NHAN.get(arm, arm)
                dich = RA / f"{vid.name}__{giong.name}__{nhan}.mp4"
                shutil.copy2(f, dich)
                dt = tg.do_do_to(dich)
                ra.append({
                    "video": vid.name, "giong": giong.name, "arm": arm,
                    "file": dich.name,
                    "dai": round(tg.probe_duration(dich), 3),
                    "khung": tg.do_khung_hinh(dich),
                    "I_LUFS": round(dt.get("I", 0.0), 2),
                    "TP_dBTP": round(dt.get("TP", 0.0), 2),
                    "md5": md5(dich),
                })
                print(f"  {dich.name}  I={ra[-1]['I_LUFS']}"
                      f" TP={ra[-1]['TP_dBTP']}  {ra[-1]['md5'][:12]}")

    if not ra:
        print("KHÔNG có file nào — lượt đo B chưa ra video")
        return 1
    ms = [r["md5"] for r in ra]
    trung = len(ms) - len(set(ms))
    L = ["", "FILE NGHE THỬ — LIỀN MẠCH", "=" * 96,
         f"{'file':<62}{'dài':>9}{'I':>8}{'TP':>8}{'md5':>10}"]
    L.append("-" * 97)
    for r in ra:
        L.append(f"{r['file'][:60]:<62}{r['dai']:>9.2f}"
                 f"{r['I_LUFS']:>8.2f}{r['TP_dBTP']:>8.2f}"
                 f"{r['md5'][:8]:>10}")
    L.append("")
    L.append(f"MD5 khác nhau: {len(set(ms))}/{len(ms)}"
             f"  -> {'ĐẠT' if trung == 0 else f'HỎNG ({trung} file TRÙNG)'}")
    xa = max(abs(r["I_LUFS"] + 14.0) for r in ra)
    L.append(f"Lệch xa nhất so đích −14,0 LUFS: {xa:.2f} LU"
             f"  -> {'ĐẠT' if xa <= 1.0 else 'ĐÁNG NGỜ'}")
    L.append(f"Đỉnh thật cao nhất: "
             f"{max(r['TP_dBTP'] for r in ra):.2f} dBTP")
    txt = "\n".join(L)
    print(txt)
    (KQ / "E_nghe_thu.txt").write_text(txt, encoding="utf-8")
    (KQ / "E_nghe_thu.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {RA}")
    return 0 if trung == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
