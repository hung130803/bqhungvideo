# Soi thuoc tinh nguon Nhat that: thoi luong, fps mode (VFR/CFR), co tieng khong,
# muc am thanh (de doan "khong loi"). CHI DOC, khong sua gi.
import json
import subprocess
import sys
from pathlib import Path

FF = Path(r"D:\claude\ai-content-studio\bin\ffprobe.exe")
FM = Path(r"D:\claude\ai-content-studio\bin\ffmpeg.exe")
ROOT = Path(r"C:\Users\Admin\Downloads\thùng rác")


def jp(p: Path) -> bool:
    return any("぀" <= c <= "ヿ" or "一" <= c <= "龯" for c in str(p))


def probe(p: Path) -> dict:
    r = subprocess.run(
        [str(FF), "-v", "quiet", "-print_format", "json", "-show_streams",
         "-show_format", str(p)], capture_output=True, text=True,
        encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def vfr(p: Path, giay: float = 30.0) -> str:
    """Doc 30s dau, xem khoang cach khung co deu khong -> CFR hay VFR."""
    r = subprocess.run(
        [str(FF), "-v", "quiet", "-select_streams", "v:0", "-show_entries",
         "packet=pts_time", "-of", "csv=p=0", "-read_intervals", f"%+{giay}",
         str(p)], capture_output=True, text=True, encoding="utf-8",
        errors="replace")
    ts = []
    for ln in r.stdout.splitlines():
        ln = ln.strip().rstrip(",")
        try:
            ts.append(float(ln))
        except Exception:
            pass
    ts.sort()
    if len(ts) < 20:
        return "?"
    d = [round(ts[i + 1] - ts[i], 5) for i in range(len(ts) - 1)]
    return f"CFR({len(set(d))} buoc)" if len(set(d)) <= 2 else f"VFR({len(set(d))} buoc)"


def am(p: Path, giay: float = 120.0) -> float:
    """Muc RMS trung binh (dBFS) trong `giay` dau. -inf = cam tieng."""
    r = subprocess.run(
        [str(FM), "-v", "error", "-t", str(giay), "-i", str(p), "-map", "a:0?",
         "-af", "astats=metadata=1:reset=0", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    val = None
    for ln in r.stderr.splitlines():
        if "RMS level dB" in ln:
            try:
                val = float(ln.split(":")[-1].strip())
            except Exception:
                pass
    return val if val is not None else float("-inf")


def main():
    vids = sorted(x for x in ROOT.rglob("*.mp4") if jp(x))
    print(f"{len(vids)} video Nhat\n")
    print(f"{'MB':>6} {'giay':>7} {'fps':>7} {'CFR/VFR':<14} {'tieng':<20} ten")
    for v in vids:
        d = probe(v)
        if not d:
            print(f"{'?':>6} PROBE HONG {v.name[:40]}")
            continue
        dur = float(d.get("format", {}).get("duration", 0))
        vs = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
        aus = [s for s in d["streams"] if s["codec_type"] == "audio"]
        fps = vs.get("r_frame_rate", "?")
        mb = v.stat().st_size / 1024 / 1024
        tieng = "KHONG CO LUONG TIENG"
        if aus:
            a = aus[0]
            tieng = f"{a.get('codec_name')} {a.get('channels')}ch"
        print(f"{mb:6.0f} {dur:7.0f} {fps:>7} {vfr(v):<14} {tieng:<20} {v.name[:46]}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
