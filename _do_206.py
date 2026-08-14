# -*- coding: utf-8 -*-
"""ĐO CHỖ VỠ THẬT của `WinError 206` trên 6 video của anh Hùng.

`_do_cmdline.py` đã chốt: 206 = **dòng lệnh vượt 32.767 ký tự**, KHÔNG phải
MAX_PATH. Còn lại câu hỏi: lệnh ffmpeg NÀO trong đường thay giọng phình ra?

Hai nghi phạm, cả hai đều phình theo ĐỘ DÀI VIDEO (khớp đúng dấu hiệu "2 video
DÀI NHẤT lỗi"):

  A. `thay_giong._ghep_track_giong` — **mỗi CÂU một `-i <đường dẫn wav>`** rồi
     một `adelay` trong `-filter_complex`. Phình theo `số câu x độ dài đường
     dẫn` (nên tên file dài cũng góp phần, đúng cảm nhận của anh Hùng).
  B. `thay_audio_video` + `che_chu.loc_cho_xuat` — mỗi 8 giây phim một hộp che
     (`HOP_DOAN=8.0`), mỗi hộp là split/crop/boxblur/overlay.

Script này đo CẢ HAI trên video THẬT. Phần A cần chép lời -> dùng Groq THẬT
(41 key trong `<DATA_DIR>\\.env`); KHÔNG chạy Demucs/TTS (không cần: số câu và
đường dẫn là đủ để dựng lại y hệt dòng lệnh).

Chạy: `.venv\\Scripts\\python _do_206.py`
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
DICH = r"C:\Users\Admin\Downloads\longtieng\xuất"
TRAN_CMD = 32767                                 # CreateProcess


def do_dai_cmd(args: list[str]) -> int:
    """Độ dài dòng lệnh Windows dựng từ argv (giống `subprocess.list2cmdline`)."""
    return len(subprocess.list2cmdline(args))


def phan_a(vids: list[Path]) -> None:
    """`_ghep_track_giong`: số câu x đường dẫn wav."""
    from app.core import thay_giong as tg
    from app.core.tg_chay import thu_muc_lam_cho

    print("\n" + "=" * 78)
    print("A. `_ghep_track_giong` — mỗi CÂU một `-i <wav>`")
    print("=" * 78)
    sand = REPO / f"bq_do206_{os.getpid()}"
    sand.mkdir(parents=True, exist_ok=True)
    ket = []
    try:
        for v in vids:
            t0 = time.time()
            wav = sand / "goc.wav"
            try:
                tong = tg.tach_wav(v, wav)
                d = tg.chep_loi(wav)
                cau = tg.cau_tu_transcript(d)
            except Exception as e:               # noqa: BLE001
                print(f"  {v.name[:38]}… -> CHÉP LỜI LỖI: {e}")
                continue
            # dựng lại ĐÚNG `manh` mà bước 5 sẽ trả (mốc + đường dẫn khop_*.wav)
            tam = Path(thu_muc_lam_cho(v, DICH))
            manh = [(float(c["start"]), str(tam / "khop" / f"khop_{i:04d}.wav"))
                    for i, c in enumerate(cau)]
            args = ["-f", "lavfi", "-t", f"{tong:.3f}",
                    "-i", f"anullsrc=r={tg.SR_TACH}:cl=stereo"]
            parts, labels = [], []
            for i, (start, w) in enumerate(manh):
                args += ["-i", str(w)]
                ms = max(0, int(round(start * 1000)))
                parts.append(f"[{i+1}:a]adelay={ms}:all=1[d{i}]")
                labels.append(f"[d{i}]")
            parts.append(f"[0:a]{''.join(labels)}amix=inputs={len(manh)+1}:"
                         f"duration=first:normalize=0[out]")
            args += ["-filter_complex", ";".join(parts), "-map", "[out]",
                     "-ac", "2", "-ar", str(tg.SR_TACH), "-c:a", "pcm_s16le",
                     str(tam / "tieng_moi.giong.wav")]
            full = [str(REPO / "bin" / "ffmpeg.exe"), "-y", "-hide_banner",
                    "-nostdin", "-loglevel", "error", *args]
            n = do_dai_cmd(full)
            duong = len(str(tam / "khop" / "khop_0000.wav"))
            co = "VƯỢT" if n > TRAN_CMD else "    "
            print(f"  {co} {n:6d} ký tự · {len(cau):3d} câu · wav {duong} ký tự"
                  f" · {tong:6.1f}s · {v.name[:30]}…  ({time.time()-t0:.0f}s)")
            ket.append((v, n, len(cau), duong, tong))
    finally:
        shutil.rmtree(sand, ignore_errors=True)
    if ket:
        print(f"\n  -> VƯỢT {sum(1 for k in ket if k[1] > TRAN_CMD)}/{len(ket)}")


def phan_b(vids: list[Path]) -> None:
    """`thay_audio_video` + che_chu: 1 hộp mỗi 8 giây."""
    from app.core import che_chu as CC
    from app.core.thay_giong import probe_duration

    print("\n" + "=" * 78)
    print("B. che chữ — `-filter_complex` 1 hộp mỗi 8 giây (HOP_DOAN=8.0)")
    print("=" * 78)
    for v in vids:
        t0 = time.time()
        try:
            dur = probe_duration(v)
            segs = [(0.0, dur)] if dur > 0 else None
            loc, dai, ly_do = CC.loc_cho_xuat(v, cach="mo", muc=1.0, segs=segs)
        except Exception as e:                   # noqa: BLE001
            print(f"  {v.name[:38]}… -> LỖI: {e}")
            continue
        args = [str(REPO / "bin" / "ffmpeg.exe"), "-y", "-hide_banner",
                "-nostdin", "-loglevel", "error",
                "-i", str(v), "-i", str(Path(DICH) / "tieng_moi.wav"),
                "-filter_complex", f"[0:v]{loc}[vout]",
                "-map", "[vout]", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(Path(DICH) / v.name)]
        n = do_dai_cmd(args) if loc else 0
        co = "VƯỢT" if n > TRAN_CMD else "    "
        print(f"  {co} {n:6d} ký tự · filter {len(loc):6d} · {dur:6.1f}s · "
              f"{v.name[:30]}…  ({time.time()-t0:.0f}s)")
        print(f"         {ly_do[:110]}")


def main() -> int:
    vids = sorted(NGUON.glob("*.mp4"))
    if not vids:
        print(f"KHÔNG thấy video trong {NGUON}")
        return 2
    print("=" * 78)
    print(f"ĐO CHỖ VỠ WinError 206 · trần dòng lệnh {TRAN_CMD} ký tự")
    print(f"đích: {DICH}")
    print("=" * 78)
    lam = (sys.argv[1] if len(sys.argv) > 1 else "ab").lower()
    if "b" in lam:
        phan_b(vids)
    if "a" in lam:
        phan_a(vids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
