# -*- coding: utf-8 -*-
"""ĐO **IM GIỮA CÂU** TRÊN CHÍNH FILE ANH HÙNG ĐÃ XUẤT, KÈM CỘT VIDEO GỐC.

VÌ SAO PHẢI CÓ CỘT GỐC: nguồn Douyin VỐN ĐÃ có chỗ im (người dẫn nghỉ, cảnh
không lời). Đo mỗi bản xuất rồi kêu "12 khoảng im" là con số VÔ NGHĨA — phải
lấy HIỆU hai bên mới ra phần **app tự đẻ thêm**. Đây là mệnh đề trung tâm.

VÌ SAO KHÔNG DÙNG `silencedetect` MỘT NGƯỠNG: bản xuất có NHẠC NỀN (Demucs
tách rồi trộn lại, `sidechaincompress` chỉ HẠ nhạc chứ không tắt), nên ngưỡng
tuyệt đối kiểu −40 dBFS có thể ra **0 khoảng im ở CẢ HAI** cột và ta không học
được gì. Nên đây:
  1. đo bao hình RMS 20 ms bằng numpy (không phụ thuộc ngưỡng),
  2. QUÉT một DẢI ngưỡng và in cả bảng — người đọc thấy được kết luận có đổi
     theo ngưỡng hay không (nếu đổi thì kết luận là RÁC, phải nói ra),
  3. thêm ngưỡng THEO CHÍNH FILE (`đỉnh − X dB`) để trừ chênh mức tổng thể
     giữa hai file (bản xuất chuẩn hoá −14 LUFS, bản gốc thì không).

CHỈ ĐỌC nguồn. Không sửa, không xoá gì trong `Downloads\\longtieng`.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

REPO = Path(__file__).resolve().parent
FFMPEG = str(REPO / "bin" / "ffmpeg.exe")
FFPROBE = str(REPO / "bin" / "ffprobe.exe")

GOC_DIR = Path(r"C:\Users\Admin\Downloads\longtieng")
XUAT_DIR = GOC_DIR / "xuất"

SB = REPO / "_kq_lienmach" / "_sb"
KQ = REPO / "_kq_lienmach"

HOP = 0.020          # bước nhảy bao hình (giây)
WIN = 0.040          # cửa sổ RMS (giây)
SR = 16000

#: các mốc bề rộng khoảng im mà anh Hùng nghe ra ("được đoạn rồi nghỉ")
BAC = (0.5, 1.0, 2.0)

#: quét ngưỡng TUYỆT ĐỐI (dBFS) — in cả bảng, không chọn sẵn một số
NGUONG_TUYET = (-50.0, -45.0, -40.0, -35.0, -30.0, -25.0)
#: ngưỡng THEO CHÍNH FILE: mức nói (bách phân vị 90) trừ đi X dB
NGUONG_TUONG_DOI = (20.0, 25.0, 30.0)


def _chay(args: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout)


def probe(path: Path) -> dict:
    """(dài_format, dài_video, dài_tiếng, số_khung, fps_vỏ) — ĐỌC, không sửa."""
    cp = _chay([FFPROBE, "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", str(path)])
    d = json.loads(cp.stdout.decode("utf-8", "replace") or "{}")
    ra = {"dai": float(d.get("format", {}).get("duration") or 0.0),
          "dai_v": 0.0, "dai_a": 0.0, "khung": 0, "fps_vo": 0.0}
    for s in d.get("streams", []):
        if s.get("codec_type") == "video":
            ra["dai_v"] = float(s.get("duration") or 0.0)
            ra["khung"] = int(s.get("nb_frames") or 0)
            try:
                a, b = str(s.get("avg_frame_rate", "0/1")).split("/")
                ra["fps_vo"] = float(a) / float(b) if float(b) else 0.0
            except Exception:  # noqa: BLE001
                pass
        elif s.get("codec_type") == "audio":
            ra["dai_a"] = float(s.get("duration") or 0.0)
    return ra


def rut_tieng(video: Path, wav: Path) -> bool:
    """Rút luồng tiếng ra mono 16 kHz vào HỘP CÁT. Nguồn CHỈ ĐỌC."""
    wav.parent.mkdir(parents=True, exist_ok=True)
    cp = _chay([FFMPEG, "-y", "-v", "error", "-i", str(video),
                "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le",
                str(wav)])
    return cp.returncode == 0 and wav.exists() and wav.stat().st_size > 1024


def bao_hinh(wav: Path) -> tuple[np.ndarray, float]:
    """Bao hình RMS theo dBFS, bước `HOP`. Trả (dãy dB, giây/khung)."""
    import wave
    with wave.open(str(wav), "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    h = int(round(HOP * SR))
    win = int(round(WIN * SR))
    if len(x) < win:
        return np.zeros(0, dtype=np.float32), HOP
    # RMS trượt bằng tổng tích luỹ của x^2 -> O(n), không vòng lặp Python
    p = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
    idx = np.arange(0, len(x) - win, h)
    ms = (p[idx + win] - p[idx]) / win
    db = 10.0 * np.log10(np.maximum(ms, 1e-12))
    return db.astype(np.float32), HOP


def khoang_im(db: np.ndarray, nguong: float, hop: float,
              toi_thieu: float = 0.30) -> list[tuple[float, float]]:
    """Các đoạn LIÊN TIẾP dưới ngưỡng, dài hơn `toi_thieu` giây."""
    duoi = db < nguong
    ra: list[tuple[float, float]] = []
    i = 0
    n = len(duoi)
    while i < n:
        if not duoi[i]:
            i += 1
            continue
        j = i
        while j < n and duoi[j]:
            j += 1
        d = (j - i) * hop
        if d >= toi_thieu:
            ra.append((i * hop, j * hop))
        i = j
    return ra


def thong_ke(db: np.ndarray, nguong: float, hop: float,
             tong: float) -> dict:
    """Bảng số cho MỘT ngưỡng. Tách IM ĐẦU/CUỐI khỏi IM GIỮA."""
    ks = khoang_im(db, nguong, hop)
    mep = 0.05
    giua = [(a, b) for a, b in ks if a > mep and b < tong - mep]
    dau = [(a, b) for a, b in ks if a <= mep]
    cuoi = [(a, b) for a, b in ks if b >= tong - mep]
    dai = [b - a for a, b in giua]
    return {
        "tong_im_giua": round(sum(dai), 3),
        "so_khoang": len(giua),
        **{f"so_>={m}s": sum(1 for x in dai if x >= m) for m in BAC},
        "dai_nhat": round(max(dai), 3) if dai else 0.0,
        "pt_thoi_luong": round(100.0 * sum(dai) / max(0.001, tong), 2),
        "im_dau": round(sum(b - a for a, b in dau), 3),
        "im_cuoi": round(sum(b - a for a, b in cuoi), 3),
    }


def do_mot_file(video: Path, ten_sb: str) -> dict:
    pr = probe(video)
    wav = SB / f"{ten_sb}.wav"
    if not rut_tieng(video, wav):
        return {"loi": "không rút được tiếng", **pr}
    db, hop = bao_hinh(wav)
    if db.size == 0:
        return {"loi": "tiếng quá ngắn", **pr}
    tong = len(db) * hop
    # mức NÓI của chính file (bách phân vị 90) — để dựng ngưỡng tương đối
    muc_noi = float(np.percentile(db, 90))
    ra = {**pr, "muc_noi_db": round(muc_noi, 2),
          "muc_tb_db": round(float(np.mean(db)), 2),
          "bang": {}}
    for ng in NGUONG_TUYET:
        ra["bang"][f"tuyet{ng:.0f}"] = thong_ke(db, ng, hop, tong)
    for x in NGUONG_TUONG_DOI:
        ra["bang"][f"tuongdoi-{x:.0f}"] = thong_ke(db, muc_noi - x, hop, tong)
    try:
        wav.unlink()
    except Exception:  # noqa: BLE001
        pass
    return ra


def main() -> int:
    KQ.mkdir(parents=True, exist_ok=True)
    SB.mkdir(parents=True, exist_ok=True)
    out = KQ / "A_im_giua_cau.json"
    txt = KQ / "A_im_giua_cau.txt"

    cap: list[tuple[Path, Path]] = []
    for x in sorted(XUAT_DIR.glob("*.mp4")):
        g = GOC_DIR / x.name
        if g.exists():
            cap.append((g, x))
    print(f"Tìm được {len(cap)} cặp gốc/xuất")

    kq: list[dict] = []
    for i, (g, x) in enumerate(cap):
        t0 = time.time()
        print(f"\n[{i+1}/{len(cap)}] {x.name}")
        a = do_mot_file(g, f"goc{i}")
        print(f"   gốc:  {a.get('dai',0):.3f}s  khung={a.get('khung')}")
        b = do_mot_file(x, f"xuat{i}")
        print(f"   xuất: {b.get('dai',0):.3f}s  khung={b.get('khung')}")
        k = (b.get("dai", 0) / a["dai"]) if a.get("dai") else 0.0
        kq.append({"ten": x.name, "goc": a, "xuat": b,
                   "k": round(k, 4),
                   "fps_that_goc": round(a.get("khung", 0)
                                         / max(0.001, a.get("dai_v", 0)), 3),
                   "fps_that_xuat": round(b.get("khung", 0)
                                          / max(0.001, b.get("dai_v", 0)), 3),
                   "giay": round(time.time() - t0, 1)})
        # GHI NGAY SAU MỖI FILE — lượt chạy bị giết thì vẫn còn số
        out.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print(f"   k={k:.4f}  ({time.time()-t0:.1f}s)  -> đã ghi {out.name}")

    # bảng chữ
    L: list[str] = []
    L.append("BẢNG A — IM GIỮA CÂU TRÊN FILE THẬT ANH HÙNG ĐÃ XUẤT")
    L.append("=" * 100)
    for r in kq:
        L.append("")
        L.append(f"### {r['ten']}")
        L.append(f"  gốc  {r['goc'].get('dai',0):8.3f} s · {r['goc'].get('khung')} khung"
                 f" · nhịp thật {r['fps_that_goc']:.3f} fps"
                 f" · mức nói {r['goc'].get('muc_noi_db')} dB")
        L.append(f"  xuất {r['xuat'].get('dai',0):8.3f} s · {r['xuat'].get('khung')} khung"
                 f" · nhịp thật {r['fps_that_xuat']:.3f} fps"
                 f" · mức nói {r['xuat'].get('muc_noi_db')} dB")
        L.append(f"  HỆ SỐ GIÃN k = {r['k']:.4f}"
                 f"   (video dài thêm {r['xuat'].get('dai',0)-r['goc'].get('dai',0):+.2f} s)")
        L.append("")
        hdr = (f"  {'ngưỡng':<14}{'':2}"
               f"{'GỐC: tổng/số/≥1s/dài nhất/%':<46}"
               f"{'XUẤT: tổng/số/≥1s/dài nhất/%':<46}{'HIỆU tổng':>10}")
        L.append(hdr)
        L.append("  " + "-" * 116)
        for key in r["goc"].get("bang", {}):
            a = r["goc"]["bang"][key]
            b = r["xuat"]["bang"][key]
            ca = (f"{a['tong_im_giua']:7.2f}s /{a['so_khoang']:4d} /"
                  f"{a['so_>=1.0s']:4d} /{a['dai_nhat']:6.2f}s /{a['pt_thoi_luong']:6.2f}%")
            cb = (f"{b['tong_im_giua']:7.2f}s /{b['so_khoang']:4d} /"
                  f"{b['so_>=1.0s']:4d} /{b['dai_nhat']:6.2f}s /{b['pt_thoi_luong']:6.2f}%")
            L.append(f"  {key:<16}{ca:<46}{cb:<46}"
                     f"{b['tong_im_giua']-a['tong_im_giua']:+9.2f}s")
    txt.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n-> {txt}")
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        # DỌN HỘP CÁT KỂ CẢ KHI LỖI — và tuyệt đối không đụng thư mục nguồn
        try:
            if SB.exists() and SB.name == "_sb" and SB.parent.name == "_kq_lienmach":
                shutil.rmtree(SB, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
    sys.exit(rc)
