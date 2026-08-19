# -*- coding: utf-8 -*-
"""CHẠY THẬT `thay_giong_video(de_giong=True)` END-TO-END trên clip THẬT.

Cổng 86 CA 5 quét TĨNH nhánh mã, CA 6 chạy thật bước TRỘN — nhưng không mục nào
đi HẾT dây chuyền ở chế độ mới. Lỗ đó đúng loại đã sập ở cổng 55: `_synth_all_eleven`
CHỈ nổ ở nhánh LÙI, tức vài video đầu êm ru. File này bịt nó: cắt một khúc NGẮN
từ video thật của anh Hùng rồi chạy đủ 6 bước với `de_giong=True`.

KHÔNG ĐỤNG video gốc (chỉ đọc + cắt sang hộp cát); hộp cát dọn ở `finally`.
Chạy:  .venv/Scripts/python -u _do_e2e_de_giong.py [giây]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = REPO / "bq_e2e_dg"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "de_giong"
GIAY = float(sys.argv[1]) if sys.argv[1:] else 40.0


def main() -> int:
    from config import settings as st
    from app.core import thay_giong as TG

    vids = sorted(NGUON.glob("*.mp4"))
    if not vids:
        print(f"KHÔNG có mp4 trong {NGUON}")
        return 2
    goc = vids[0]
    shutil.rmtree(SB, ignore_errors=True)
    SB.mkdir(parents=True, exist_ok=True)
    try:
        vin = SB / "clip.mp4"
        # cắt lại (re-encode) cho khung đầu là keyframe — `-c copy` để lại khung
        # rác đầu clip và `chep_loi` đọc ra câu cụt.
        r = subprocess.run(
            [str(st.FFMPEG_PATH), "-y", "-v", "error", "-nostdin",
             "-ss", "20", "-t", f"{GIAY:.2f}", "-i", str(goc),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-c:a", "aac", "-b:a", "192k", str(vin)],
            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"cắt clip lỗi: {r.stderr[-300:]}")
            return 2
        dai = TG.probe_duration(vin)
        print(f"clip {dai:.2f}s từ {goc.name[:40]}")

        t0 = time.time()
        kq = TG.thay_giong_video(
            vin, dich_sang="vi", thu_muc_lam=SB / "lam",
            voice="vi-VN-NamMinhNeural", de_giong=True, viet_chu=False,
            on_progress=lambda p, m: print(f"   {p * 100:5.1f}% {m}"))
        gy = time.time() - t0
        print("\n" + "=" * 70)
        print(f"ok = {kq.get('ok')} · {gy:.1f}s · cach_tron = "
              f"{kq.get('cach_tron')!r}")
        if not kq.get("ok"):
            print(f"LỖI: {kq.get('loi')}")
            return 1
        # BẤT BIẾN của chế độ mới — kiểm THẲNG trên kết quả trả về, không suy ra
        chot = {
            "cach_tron == 'de'": kq.get("cach_tron") == "de",
            "KHÔNG chạy Demucs (tach.cach == 'de_giong')":
                (kq.get("tach") or {}).get("cach") == "de_giong",
            "KHÔNG có lớp giọng tách (tach.giong rỗng)":
                not (kq.get("tach") or {}).get("giong"),
            "chép lời chạy trên AUDIO GỐC":
                (kq.get("chep") or {}).get("nguon") == "audio_goc",
            "KHÔNG bù giọng gốc (bu_goc.bat == False)":
                (kq.get("bu_goc") or {}).get("bat") is False,
            "kiểm video ra ĐẠT": bool((kq.get("kiem") or {}).get("ok", True)),
            "file ra tồn tại": Path(kq.get("ra") or "x").exists(),
        }
        for k, v in chot.items():
            print(f"  {'ĐẠT ' if v else 'HỎNG'} {k}")
        tr = kq.get("tron") or {}
        print(f"\n  độ dài ra {tr.get('do_dai')}s (clip {dai:.3f}s) · "
              f"I sau chuẩn hoá {(tr.get('do_to') or {}).get('I_sau')} LUFS · "
              f"đỉnh {tr.get('dinh_dbfs')} dBFS")
        print(f"  giọng trên nền lúc nói {tr.get('giong_tren_nhac_tinh_db')} dB "
              f"(kể ducking {tr.get('giong_tren_nhac_ke_ne_db')}) · nền hạ "
              f"{tr.get('gain_nhac_db')} dB · giọng nâng "
              f"{tr.get('gain_giong_db')} dB")
        print(f"  câu: chép {(kq.get('chep') or {}).get('so_cau')} · "
              f"khớp {len((kq.get('khop') or {}).get('moc_tieng') or [])} · "
              f"bỏ qua {(kq.get('khop') or {}).get('bo_qua')}")
        NGHE.mkdir(parents=True, exist_ok=True)
        dich = NGHE / f"E2E_DE_{GIAY:.0f}s_{goc.name}"
        shutil.copy2(kq["ra"], dich)
        print(f"\n  file nghe thử: {dich}")
        (REPO / "_kq_e2e_de_giong.json").write_text(
            json.dumps({k: v for k, v in kq.items()
                        if k not in ("loi_cuoi",)},
                       ensure_ascii=False, indent=1, default=str),
            encoding="utf-8")
        return 0 if all(chot.values()) else 1
    finally:
        shutil.rmtree(SB, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
