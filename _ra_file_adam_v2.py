# -*- coding: utf-8 -*-
"""FILE NGHE THỬ CHO ANH HÙNG — `vn:Adam` vs `en-US-AriaNeural` vs `el:Adam`.

Anh Hùng: *"cái adam bị lỗi hay sao nghe cứ lạ lạ khác lắm"* + trỏ vào
`_NGHE_THU_ANH_HUNG\\adam\\EL_Adam_A.wav` nói *"ít nhất phải như này mới oke"*.
**TAI ANH HÙNG LÀ PHÁN QUYẾT CUỐI** — số đo chỉ để loại sớm cái hỏng rõ ràng.
File ra: `_NGHE_THU_ANH_HUNG\\adam_v2\\`.

═══════════════════════════════════════════════════════════════════════════
CÙNG MỘT CÂU, BA GIỌNG — VÀ CÙNG MỘT ĐỘ TO
═══════════════════════════════════════════════════════════════════════════
Chuẩn hoá cả ba về **-14 LUFS** bằng CHÍNH `thay_giong.chuan_do_to` (nâng
thuần + hạn đỉnh, cổng 65/66). Không chuẩn hoá thì phép nghe biến thành "file
nào TO hơn" — tai người chấm điểm to hơn là hay hơn, và ba nguồn này đo ra lệch
nhau nhiều LU. Ghi rõ ở đây vì đó là **can thiệp vào file**: chất giọng không
đổi, chỉ mức to đổi.

═══════════════════════════════════════════════════════════════════════════
KHÔNG SINH LẠI THỨ ĐÃ CÓ — VÀ KHÔNG NHÂN BẢN GÌ TỪ MẪU ElevenLabs
═══════════════════════════════════════════════════════════════════════════
`vn:Adam` và `en-US-AriaNeural` lấy lại từ chính file `_do_adam_en.py` vừa đo
(`_do_vn_en/AD_en_v1`, `_do_vn_en/edge_en_v1`) -> nghe đúng thứ đã ra số, không
phải một mẻ đọc khác. Chỉ `el:Adam` phải gọi mạng (tốn ký tự, in ra ở cuối).

Mẫu ElevenLabs ở đây dùng ĐÚNG MỘT việc: để anh Hùng nghe so. KHÔNG dùng làm
`ref_audio` nhân bản, KHÔNG tinh chỉnh — đó là làm bản sao một giọng thương mại
đang được bán, trong app BÁN RA.

═══════════════════════════════════════════════════════════════════════════
BẪY `_eleven_tts` CÓ CACHE THEO `sha1(voice|model|text)`
═══════════════════════════════════════════════════════════════════════════
Cùng câu + cùng giọng -> trả lại **file y hệt** (cos = 1,000). Nên script đối
soát **MD5 ba file ra** và kêu nếu có hai file trùng byte.

Chạy:  .venv\\Scripts\\python -u _ra_file_adam_v2.py
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from _bo_cau_thu_doc import CORPUS                              # noqa: E402
from app.core import dubbing, thay_giong as TG                  # noqa: E402
from config import settings                                     # noqa: E402

RA = REPO / "_NGHE_THU_ANH_HUNG" / "adam_v2"
NGUON = REPO / "_do_vn_en"
EL_ADAM = "pNInz6obpgDQGcFmaJgB"        # id giọng Adam (dùng lại `_do_adam.py`)
SO_CAU = 2                              # 2 câu là đủ để nghe; ~101 ký tự EL


def _wav(vao: Path, ra: Path) -> bool:
    r = subprocess.run(
        [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(vao), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le",
         str(ra)], capture_output=True, timeout=300)
    return r.returncode == 0 and ra.exists() and ra.stat().st_size > 1024


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    RA.mkdir(parents=True, exist_ok=True)
    cau = [c for _l, c, _t in CORPUS["en"][:SO_CAU]]
    print("=" * 74)
    print("FILE NGHE THỬ `adam_v2` — cùng câu tiếng Anh, ba giọng, cùng độ to")
    print("=" * 74)
    for i, c in enumerate(cau, 1):
        print(f"  câu {i}: {c}")

    ton_ky_tu = 0
    ds: list[tuple[str, Path]] = []
    for i, c in enumerate(cau, 1):
        # 1) vn:Adam + 2) edge Aria — LẤY LẠI file của lượt đo, không sinh mới
        for ten, thu in (("VN_Adam", "AD_en_v1"), ("EDGE_Aria", "edge_en_v1")):
            vao = NGUON / thu / f"c{i-1:03d}.mp3"
            if not vao.exists():
                print(f"  THIẾU {vao} -> chạy `_do_adam_en.py` trước")
                continue
            tho = RA / f"_tho_{ten}_{i}.wav"
            if _wav(vao, tho):
                ds.append((f"{ten}_EN_{i}", tho))
        # 3) el:Adam — lượt gọi mạng DUY NHẤT
        mp3 = RA / f"_tho_EL_Adam_{i}.mp3"
        try:
            got = dubbing._eleven_tts(c, f"el:{EL_ADAM}", str(mp3))  # noqa: SLF001
        except Exception as e:                                      # noqa: BLE001
            print(f"  el:Adam câu {i} HỎNG: {type(e).__name__}: {e}")
            got = False
        if got and mp3.exists():
            ton_ky_tu += len(c)
            tho = RA / f"_tho_EL_Adam_{i}.wav"
            if _wav(mp3, tho):
                ds.append((f"EL_Adam_EN_{i}", tho))
        mp3.unlink(missing_ok=True)

    print("\n-- CHUẨN HOÁ ĐỘ TO (-14 LUFS, nâng thuần + hạn đỉnh) --")
    xong: list[tuple[str, Path]] = []
    for ten, tho in ds:
        dich = RA / f"{ten}.wav"
        try:
            kq = TG.chuan_do_to(tho, dich)
            tr = kq.get("truoc") or {}
            sa = kq.get("sau") or {}
            print(f"  {ten:<18} I {tr.get('I')} -> {sa.get('I')} LUFS · "
                  f"nâng {kq.get('nang_db')} dB · đỉnh {sa.get('TP')} dBTP"
                  + ("  (BỎ QUA: " + str(kq.get("vi_sao"))[:50] + ")"
                     if kq.get("bo_qua") else ""))
        except Exception as e:                                  # noqa: BLE001
            shutil.copyfile(tho, dich)
            print(f"  {ten:<18} chuẩn hoá HỎNG ({type(e).__name__}: "
                  f"{str(e)[:60]}) -> giữ nguyên bản thô")
        tho.unlink(missing_ok=True)
        if dich.exists():
            xong.append((ten, dich))

    print("\n-- ĐỐI SOÁT MD5 (bẫy cache `_eleven_tts` trả file y hệt) --")
    bam: dict[str, str] = {}
    trung = []
    for ten, p in xong:
        m = _md5(p)
        if m in bam:
            trung.append((bam[m], ten))
        bam[m] = ten
        print(f"  {ten:<18} {m[:12]} · {p.stat().st_size:>8} byte · "
              f"{TG.probe_duration(p):.2f} s")
    if trung:
        print(f"  TRÙNG BYTE: {trung} -> file KHÔNG dùng để so được")
    else:
        print("  không cặp nào trùng byte")

    print(f"\nRA: {RA}")
    print(f"ElevenLabs đã tiêu: **{ton_ky_tu} ký tự** "
          f"({SO_CAU} câu; cache của `_eleven_tts` làm lượt chạy lại tốn 0)")
    return 0 if xong else 1


if __name__ == "__main__":
    raise SystemExit(main())
