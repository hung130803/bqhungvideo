# -*- coding: utf-8 -*-
"""CHẠY DÂY CHUYỀN THAY GIỌNG THẬT trên video anh Hùng, GIỮ file tạm, dump SỐ.

Một lượt này cho số liệu của CẢ BA lỗi:
  · lỗi 1 — `khop.moc_tieng` + `loi_cuoi` -> lệch chữ/tiếng, độ dài mỗi lần
    hiện chữ.
  · lỗi 2 — `tron.rms_giong` / `rms_nhac` / `giong_tren_nhac_db` = số của
    CHÍNH APP (không phụ thuộc Demucs đo lại), cộng `khop.bo_qua` = câu bị
    rơi mất tiếng.
  · lỗi 3 — `loi_cuoi` -> đếm câu còn ký tự Hán.

Thành phần THẬT: ffmpeg · Demucs · Groq · edge-tts.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))


def main() -> int:
    from app.core import thay_giong as tg
    from app.ai import recap

    video = Path(sys.argv[1] if len(sys.argv) > 1
                 else REPO / "_do_lt" / "goc.mp4")
    lam = Path(sys.argv[2] if len(sys.argv) > 2 else REPO / "_do_lt" / "e2e")
    dich = sys.argv[3] if len(sys.argv) > 3 else "vi"
    lam.mkdir(parents=True, exist_ok=True)

    moc = [time.time()]

    def prog(p: float, m: str) -> None:
        print(f"  [{p * 100:5.1f}%] {m}", flush=True)

    print(f"VIDEO {video.name} -> {dich}")
    kq = tg.thay_giong_video(video, dich_sang=dich, thu_muc_lam=str(lam),
                             cach_tach="demucs", giu_file_tam=True,
                             viet_chu=False, on_progress=prog)
    print(f"\nXONG sau {time.time() - moc[0]:.1f}s  ok={kq.get('ok')}")
    if not kq.get("ok"):
        print("LỖI:", kq.get("loi"))

    for k in ("do_dai", "tach", "chep", "dich", "doc", "rut_gon",
              "doc_nhanh", "khop", "tron", "kiem"):
        v = kq.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items()
                 if kk not in ("tempo_cau", "chong_cau_ms", "moc_tieng")}
        print(f"\n[{k}] {json.dumps(v, ensure_ascii=False)[:1400]}")

    loi = kq.get("loi_cuoi") or []
    con_han = [i for i, t in enumerate(loi) if recap._has_cjk(str(t))]
    print(f"\n== LỖI 3: CÂU CÒN CHỮ HÁN/CJK ==")
    print(f"  {len(con_han)}/{len(loi)} câu "
          f"({100.0 * len(con_han) / max(1, len(loi)):.1f}%)")
    for i in con_han[:15]:
        print(f"    #{i}: {loi[i][:110]}")

    print(f"\n== LỖI 1: ĐỘ DÀI MỖI LẦN HIỆN CHỮ ==")
    do_dai = [len(str(t)) for t in loi]
    if do_dai:
        s = sorted(do_dai)
        print(f"  ký tự/câu: TB {sum(do_dai) / len(do_dai):.1f} · "
              f"trung vị {s[len(s) // 2]} · dài nhất {max(do_dai)}")
        print(f"  câu > 60 ký tự: {sum(1 for x in do_dai if x > 60)}/{len(loi)}")
        print(f"  câu > 90 ký tự: {sum(1 for x in do_dai if x > 90)}/{len(loi)}")

    (lam / "_kq.json").write_text(
        json.dumps(kq, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nĐã ghi {lam / '_kq.json'}")
    return 0 if kq.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
