# -*- coding: utf-8 -*-
"""XÁC MINH `WinError 206` ĐÃ HẾT — TRÊN ĐÚNG 2 VIDEO THẬT ĐÃ LỖI.

`_do_206.py` chỉ ĐO ĐỘ DÀI dòng lệnh (chứng minh nó vượt trần). Script này đi
nốt nửa còn lại: **CHẠY THẬT `_ghep_track_giong` đã vá** với số câu THẬT và
đường dẫn THẬT của 2 video anh Hùng, rồi kiểm file wav ra.

VÌ SAO ĐÚNG 2 VIDEO NÀY: thư mục nguồn có 6 video, thư mục `xuất\\` chỉ có 4 —
2 cái thiếu chính là 2 dòng "Lỗi" trên màn hình 14/08/2026.

AN TOÀN: video gốc **CHỈ ĐỌC**, và còn được COPY ra chỗ khác trước khi đụng
tới (anh Hùng đã dặn đừng xoá/sửa gì trong `Downloads\\longtieng`). Không chạy
Demucs/TTS — không cần: thứ làm nổ `CreateProcess` là SỐ CÂU x ĐỘ DÀI ĐƯỜNG
DẪN, cả hai đều có thật ở đây.

Chạy: `.venv\\Scripts\\python -u _do_206_that.py`
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
TRAN_CMD = 32767

#: 2 video KHÔNG có mặt trong `xuất\` = 2 video đã lỗi thật.
TEN_LOI = ("（完整）夫妻俩被困峡谷之内", "（完整）男孩励志要出去闯荡一番")


def dai_cmd(args: list[str]) -> int:
    return len(subprocess.list2cmdline(args))


def main() -> int:
    from app.core import thay_giong as tg
    from app.core.tg_chay import thu_muc_lam_cho

    vids = [p for p in sorted(NGUON.glob("*.mp4"))
            if any(p.name.startswith(t) for t in TEN_LOI)]
    print("=" * 78)
    print("XÁC MINH WinError 206 TRÊN 2 VIDEO THẬT ĐÃ LỖI")
    print(f"trần CreateProcess {TRAN_CMD} ký tự · tìm thấy {len(vids)}/2 video")
    print("=" * 78)
    if len(vids) != 2:
        print("KHÔNG đủ 2 video — dừng, không đoán.")
        return 2

    san = REPO / f"bq_do206t_{os.getpid()}"
    (san / "goc").mkdir(parents=True, exist_ok=True)
    ket = []
    try:
        for v in vids:
            t0 = time.time()
            # COPY RA CHỖ KHÁC — không đụng bản gốc của anh Hùng
            ban_sao = san / "goc" / v.name
            shutil.copy2(v, ban_sao)

            wav = san / "rut.wav"
            tong = tg.tach_wav(ban_sao, wav)
            d = tg.chep_loi(wav)
            cau = tg.cau_tu_transcript(d)

            # đường dẫn THẬT mà app sẽ dùng (đích = `xuất\` như lượt đã lỗi)
            tam = Path(thu_muc_lam_cho(v, str(NGUON / "xuất")))
            khop = san / "khop"
            khop.mkdir(parents=True, exist_ok=True)

            # 1 wav ngắn rồi nhân bản ra ĐÚNG số câu, đặt ở ĐÚNG tên app dùng
            mau = san / "_mau.wav"
            subprocess.run([str(REPO / "bin" / "ffmpeg.exe"), "-y",
                            "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-t", "0.40",
                            "-i", "sine=frequency=300:r=44100",
                            "-ac", "2", "-c:a", "pcm_s16le", str(mau)],
                           check=True, timeout=120)
            manh = []
            for i, c in enumerate(cau):
                p = khop / f"khop_{i:04d}.wav"
                shutil.copy2(mau, p)
                manh.append((float(c["start"]), str(p)))

            # (1a) ĐƯỜNG DẪN KIỂU v2.27.1 — thư mục tạm mang NGUYÊN tên video.
            #      Phải dựng lại đúng cái này thì mới thấy được 2 bản vá là
            #      HAI thứ khác nhau: rút ngắn đường dẫn, và chia mẻ.
            tam_cu = (Path(NGUON / "xuất") / tg.TEN_THU_MUC_TAM / v.stem)
            manh_cu = [(s, str(tam_cu / "khop" / Path(w).name))
                       for s, w in manh]
            args_cu = tg._args_ghep(manh_cu, tong,
                                    tam_cu / "tieng_moi.giong.wav")
            n_cu = dai_cmd([str(REPO / "bin" / "ffmpeg.exe"), "-y",
                            "-hide_banner", "-loglevel", "error", *args_cu])
            duong_cu = len(str(tam_cu / "khop" / "khop_0000.wav"))

            # (1b) ĐƯỜNG DẪN HÔM NAY
            args_moi = tg._args_ghep(manh, tong, tam / "tieng_moi.giong.wav")
            n_moi = dai_cmd([str(REPO / "bin" / "ffmpeg.exe"), "-y",
                             "-hide_banner", "-loglevel", "error", *args_moi])
            duong = len(str(tam / "khop" / "khop_0000.wav"))

            # (2) CHẠY THẬT hàm ĐÃ VÁ
            ra = san / f"ra_{len(ket)}.wav"
            loi = ""
            try:
                tg._ghep_track_giong(manh, tong, ra)
            except Exception as e:               # noqa: BLE001
                loi = f"{type(e).__name__}: {e}"
            d_ra = tg.probe_duration(ra) if ra.exists() else 0.0
            kib = ra.stat().st_size // 1024 if ra.exists() else 0
            me = len(tg._chia_me(manh, tong, tam / "tieng_moi.giong.wav"))

            # (3) DƯ ĐỊA: đích còn sâu thêm bao nhiêu ký tự thì vượt trần —
            #     và lúc đó chia mẻ có cứu được không.
            du = (TRAN_CMD - n_moi) // max(1, len(cau))
            sau = Path(str(tam) + "x" * (du + 12))
            manh_sau = [(s, str(sau / "khop" / Path(w).name)) for s, w in manh]
            n_sau = dai_cmd([str(REPO / "bin" / "ffmpeg.exe"), "-y",
                             "-hide_banner", "-loglevel", "error",
                             *tg._args_ghep(manh_sau, tong, sau / "g.wav")])
            me_sau = len(tg._chia_me(manh_sau, tong, sau / "g.wav"))

            print(f"\n  {v.name[:52]}…")
            print(f"    {tong:7.1f}s · {len(cau):3d} câu")
            print(f"    ĐƯỜNG DẪN kiểu v2.27.1 ({duong_cu} ký tự/wav): "
                  f"{n_cu:6d} ký tự -> "
                  f"{'VƯỢT TRẦN = ĐÚNG 2 DÒNG LỖI CỦA ANH HÙNG' if n_cu > TRAN_CMD else 'vừa trần'}")
            print(f"    ĐƯỜNG DẪN hôm nay   ({duong} ký tự/wav): "
                  f"{n_moi:6d} ký tự -> "
                  f"{'VẪN VƯỢT' if n_moi > TRAN_CMD else 'DƯỚI TRẦN'} "
                  f"({100.0 * n_moi / TRAN_CMD:.0f}% trần), chia {me} mẻ")
            print(f"    CHẠY THẬT hàm đã vá -> "
                  f"{'LỖI: ' + loi if loi else f'XONG, {kib} KiB, {d_ra:.3f}s'}")
            print(f"    dư địa: đích sâu thêm ~{du} ký tự là vượt; thử "
                  f"{n_sau} ký tự -> chia {me_sau} mẻ "
                  f"({'CHIA MẺ ĐỠ ĐƯỢC' if me_sau > 1 else 'KHÔNG chia — LO'})")
            print(f"    ({time.time() - t0:.0f}s)")
            ket.append((v.name, tong, len(cau), n_cu, n_moi, me, loi, d_ra,
                        me_sau))
    finally:
        shutil.rmtree(san, ignore_errors=True)

    print("\n" + "=" * 78)
    vuot = sum(1 for k in ket if k[3] > TRAN_CMD)
    duoi = sum(1 for k in ket if k[4] <= TRAN_CMD)
    xong = sum(1 for k in ket if not k[6] and abs(k[7] - k[1]) < 0.5)
    me_ok = sum(1 for k in ket if k[8] > 1)
    print(f"đường dẫn kiểu v2.27.1 VƯỢT trần : {vuot}/2  (= 2 dòng 'Lỗi')")
    print(f"đường dẫn hôm nay DƯỚI trần      : {duoi}/2")
    print(f"chạy THẬT xong + đúng độ dài     : {xong}/2")
    print(f"đích sâu hơn -> chia mẻ đỡ được  : {me_ok}/2")
    print("=" * 78)
    return 0 if (vuot == 2 and duoi == 2 and xong == 2 and me_ok == 2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
