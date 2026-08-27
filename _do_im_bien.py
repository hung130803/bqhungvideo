# -*- coding: utf-8 -*-
"""VIỆC 0 — ĐO IM Ở BIÊN + % IM trên chính file anh Hùng vừa nghe.

Thước: `silencedetect` (đúng bộ repo đã dùng ở `thay_giong.do_le_im`).
KHÔNG đoán: mọi số đọc thẳng từ ffmpeg.
"""
import sys, subprocess, re, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import settings

CNW = 0x08000000

def _dur(p):
    r = subprocess.run([settings.FFPROBE_PATH if hasattr(settings, "FFPROBE_PATH") else "ffprobe",
                        "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", str(p)],
                       capture_output=True, text=True, creationflags=CNW)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0

def khoang_im(p, nguong=-45.0, d=0.03):
    tong = _dur(p)
    cmd = [settings.FFMPEG_PATH, "-hide_banner", "-i", str(p),
           "-af", f"silencedetect=n={nguong}dB:d={d}", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=CNW)
    kh, st = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", r.stderr or ""):
        if m.group(1) == "start":
            st = float(m.group(2))
        elif st is not None:
            kh.append((st, float(m.group(2))))
            st = None
    if st is not None:
        kh.append((st, tong))
    return tong, kh

def bang(p, nguong=-45.0):
    tong, kh = khoang_im(p, nguong)
    dau = kh[0][1] if kh and kh[0][0] <= 0.02 else 0.0
    cuoi = (tong - kh[-1][0]) if kh and kh[-1][1] >= tong - 0.02 else 0.0
    giua = [k for k in kh if k[0] > 0.02 and k[1] < tong - 0.02]
    t_giua = sum(b - a for a, b in giua)
    t_all = sum(b - a for a, b in kh)
    return dict(tong=tong, dau=dau, cuoi=cuoi, so_giua=len(giua),
                im_giua=t_giua, im_tong=t_all,
                pc_tong=100.0 * t_all / tong if tong else 0,
                pc_giua=100.0 * t_giua / tong if tong else 0,
                dai_nhat=max((b - a for a, b in giua), default=0.0),
                giua=[(round(a, 2), round(b, 2), round(b - a, 2)) for a, b in giua])

if __name__ == "__main__":
    d = Path("_NGHE_THU_ANH_HUNG/nhan_nha_them")
    ra = {}
    print("=" * 100)
    print("BẢNG 0 — IM TRONG CHÍNH FILE ANH HÙNG VỪA NGHE (silencedetect -45 dB)")
    print("=" * 100)
    print(f"{'file':<44} {'dài':>7} {'im ĐẦU':>7} {'im ĐUÔI':>8} {'#giữa':>6} "
          f"{'im GIỮA':>8} {'%im':>7} {'dài nhất':>9}")
    print("-" * 100)
    for f in sorted(d.glob("*.wav")):
        b = bang(f)
        ra[f.name] = b
        print(f"{f.name:<44} {b['tong']:>7.2f} {b['dau']*1000:>6.0f}ms "
              f"{b['cuoi']*1000:>7.0f}ms {b['so_giua']:>6} "
              f"{b['im_giua']:>8.2f} {b['pc_tong']:>6.1f}% {b['dai_nhat']:>9.2f}")
    Path("_kq_im_bien.json").write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("\n### CHI TIẾT 3 file NamMinh (đúng bộ anh Hùng nghe)")
    for k in sorted(ra):
        if "NamMinh" not in k:
            continue
        b = ra[k]
        print(f"\n{k}  ({b['tong']:.2f}s)")
        print(f"  khoảng im GIỮA: {b['so_giua']} chỗ · tổng {b['im_giua']:.2f}s "
              f"({b['pc_giua']:.1f}%)")
        print(f"  {b['giua']}")


def bang_manh():
    """VIỆC 0b — im ở BIÊN của TỪNG MẢNH CÂU (chưa nối, chưa cắt lề)."""
    import _do_nhan_nha_tieng as T
    out = {}
    print("\n" + "=" * 100)
    print("BẢNG 0b — IM Ở BIÊN TỪNG MẢNH CÂU (file TTS THÔ, trước cat_le_loat)")
    print("=" * 100)
    print(f"{'giọng':<24} {'câu':>4} {'dài':>7} {'im ĐẦU':>9} {'im ĐUÔI':>9} "
          f"{'tiếng THẬT':>11} {'%im':>7}")
    print("-" * 100)
    for voice, _nn, _sl in T.GIONG:
        tm = T.SAN / (_sach_ten(voice) + "_l0")
        if not tm.is_dir():
            continue
        rows = []
        for i in range(4):
            f = tm / f"GOC_{i}.wav"
            if not f.exists():
                continue
            tong, kh = khoang_im(f)
            dau = kh[0][1] if kh and kh[0][0] <= 0.02 else 0.0
            cuoi = (tong - kh[-1][0]) if kh and kh[-1][1] >= tong - 0.02 else 0.0
            that = tong - dau - cuoi
            rows.append((i, tong, dau, cuoi, that))
            print(f"{voice:<24} {i:>4} {tong:>7.2f} {dau*1000:>8.0f}ms "
                  f"{cuoi*1000:>8.0f}ms {that:>11.2f} "
                  f"{100*(dau+cuoi)/tong:>6.1f}%")
        if rows:
            n = len(rows)
            md = sum(r[2] for r in rows) / n
            mc = sum(r[3] for r in rows) / n
            out[voice] = dict(n=n, dau_tb=md, cuoi_tb=mc, moi_noi=md + mc)
            print(f"{'  -> TB':<24} {'':>4} {'':>7} {md*1000:>8.0f}ms "
                  f"{mc*1000:>8.0f}ms   MỐI NỐI = {(md+mc)*1000:.0f} ms")
            print("-" * 100)
    return out


def _sach_ten(s):
    import re as _re
    return _re.sub(r"[^\w]", "_", s)
