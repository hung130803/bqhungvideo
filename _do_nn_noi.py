# -*- coding: utf-8 -*-
"""VIỆC 3 — ĐO LỚP NHẤN NHÁ **SAU KHI ĐÃ NỐI VÀO `dubbing._synth_all_words`**.

Không đo lại bảng liều (bảng 211 đã có, và anh Hùng đã duyệt bằng tai). Ở đây
chỉ hỏi đúng bốn câu mà việc NỐI đẻ ra:

  1. **Cửa có ăn không** — bật cờ thì file TTS có THẬT SỰ đổi không (MD5), và
     nhấn nhá có nhích lên đúng chiều không.
  2. **TẮT thì y hệt bản cũ** — MD5 phải TRÙNG TỪNG BYTE với arm không bật.
     Đây là chốt quan trọng nhất với 200-300 kênh.
  3. **ĐỘ DÀI KHÔNG ĐỔI** — `tempo=1,0` + hậu kiểm `LECH_TOI_DA`. Đổi độ dài
     là dời mọi mốc sau nó = lệch tiếng-hình (lỗi v1.87).
  4. **ĐỌC SAI không xấu đi** — tiếng Việt có THANH ĐIỆU, nâng cao độ là đổi
     dấu. Liều mạnh đã đo `3,33% -> 11,67%`; liều nhẹ phải KHÔNG như thế.

**GHÉP CẶP TUYỆT ĐỐI:** cả hai arm dùng CHUNG một bộ file TTS gốc (đọc MỘT
lần rồi chép ra hai chỗ), nên mọi nhiễu của máy đọc bị triệt tiêu theo cấu tạo.

Chạy:  .venv\\Scripts\\python -u _do_nn_noi.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import _do_nhan_nha as NN                                      # noqa: E402
from _do_lien_mach import _dur, _noi_thang, lay_corpus, MAY    # noqa: E402
from _do_xen_bien import chep_nguoc, wer                       # noqa: E402

SAN = REPO / "bq_do_nn_noi"
KQ = REPO / "_kq_lienmach"


def md5(p) -> str:
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:12]


def main():
    import asyncio
    from app.core import dubbing, nhan_chu

    cau, vi, en = lay_corpus()
    KQ.mkdir(parents=True, exist_ok=True)
    ra = {}
    for may in ("edge", "vn"):
        voice, lang = MAY[may]
        texts = vi if lang == "vi" else en
        tm = SAN / may
        tho = tm / "tho"
        tho.mkdir(parents=True, exist_ok=True)
        p0 = [str(tho / f"c{i:03d}.mp3") for i in range(len(texts))]
        if not all(Path(x).exists() for x in p0):
            print(f"[{may}] đọc {len(texts)} câu bằng {voice} ...")
        # đọc MỘT lần, LẤY MỐC — hai arm dùng chung bộ này
        ok, moc = asyncio.run(
            dubbing._synth_all_words(texts, voice, p0, lang=lang))

        arms = {}
        for ten, bat in (("TAT", False), ("BAT", True)):
            d = tm / ten
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
            ps = []
            for i, s in enumerate(p0):
                dst = d / f"c{i:03d}.wav"
                # đổi sang wav để MD5 so được (mp3 nguồn giữ nguyên byte)
                import subprocess
                subprocess.run(
                    [__import__("config").settings.FFMPEG_PATH, "-y", "-v",
                     "error", "-i", s, "-ac", "1", "-ar", "44100",
                     "-c:a", "pcm_s16le", str(dst)],
                    capture_output=True, creationflags=0x08000000)
                ps.append(str(dst))
            dai0 = [_dur(x) for x in ps]
            m0 = [md5(x) for x in ps]
            n_doi = nhan_chu.ap_loat(texts, ps, list(ok), moc, lang, bat=bat)
            dai1 = [_dur(x) for x in ps]
            m1 = [md5(x) for x in ps]
            noi = tm / f"{ten}.wav"
            _noi_thang(ps, noi)
            f0 = NN.f0_nua_cung(noi)
            nn_v = statistics.pstdev(f0) if len(f0) >= 8 else 0.0
            lech = [abs(a - b) for a, b in zip(dai0, dai1)]
            nghe = chep_nguoc(noi, lang)
            arms[ten] = dict(
                so_cau_doi=n_doi,
                so_file_khac_md5=sum(1 for a, b in zip(m0, m1) if a != b),
                lech_dai_max_ms=round(1000 * max(lech), 1),
                lech_dai_tb_ms=round(1000 * statistics.mean(lech), 1),
                dai_tong=round(sum(dai1), 3),
                nhan_nha=round(nn_v, 2),
                wer=round(wer(" ".join(texts), nghe), 2) if nghe else -1.0,
                md5_noi=md5(noi), wav=str(noi))
        ra[may] = arms
        (KQ / "H_nhan_nha_noi.json").write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 96)
    print("BẢNG H — LỚP NHẤN NHÁ SAU KHI NỐI VÀO `_synth_all_words` (ghép cặp)")
    print("=" * 96)
    print(f"{'máy':<6} {'arm':<5} {'câu đổi':>8} {'file khác MD5':>14} "
          f"{'lệch dài max':>13} {'tổng dài':>10} {'nhấn nhá':>9} {'WER':>7}")
    print("-" * 96)
    for may, arms in ra.items():
        for ten in ("TAT", "BAT"):
            a = arms[ten]
            print(f"{may:<6} {ten:<5} {a['so_cau_doi']:>8} "
                  f"{a['so_file_khac_md5']:>14} "
                  f"{a['lech_dai_max_ms']:>12.1f}ms {a['dai_tong']:>10.3f} "
                  f"{a['nhan_nha']:>9.2f} {a['wer']:>6.2f}%")
        t, b = arms["TAT"], arms["BAT"]
        print(f"       -> nhấn nhá {t['nhan_nha']:.2f} -> {b['nhan_nha']:.2f} "
              f"({b['nhan_nha']-t['nhan_nha']:+.2f})  ·  "
              f"WER {t['wer']:.2f}% -> {b['wer']:.2f}% "
              f"({b['wer']-t['wer']:+.2f})  ·  "
              f"MD5 bản nối {'TRÙNG (CỬA KHÔNG ĂN!)' if t['md5_noi']==b['md5_noi'] else 'KHÁC (cửa ĂN)'}")
        print("-" * 96)
    print("\nCHỐT: arm TAT phải có `câu đổi = 0` và `file khác MD5 = 0` "
          "(tắt cờ -> KHÔNG đụng một byte nào).")
    print("CHỐT: arm BAT phải có `lệch dài max` <= "
          f"{1000*__import__('app.core.nhan_chu', fromlist=['x']).LECH_TOI_DA:.0f} ms "
          "(khớp hình không đổi DO CẤU TẠO).")


if __name__ == "__main__":
    main()
