# -*- coding: utf-8 -*-
"""CHỨNG MINH BẰNG FILE THẬT: đường xuất ÉP NVENC ra clip mở được, không trắng.

Chạy CHÍNH `export_canvas_clip` (cửa xuất thật của app), ca GHÉP 3 PART trên
video THẬT của anh Hùng (bản COPY, KHÔNG đụng gốc). 4 arm:

  A  nguồn  8-bit · h264_nvenc · mã HIỆN TẠI      -> đường anh Hùng đang đi
  B  nguồn 10-bit · h264_nvenc · mã HIỆN TẠI      -> nguồn yt-dlp bestvideo
  C  nguồn 10-bit · libx264    · mã TRƯỚC bản vá  -> ca HỎNG (đường LÙI)
  D  nguồn 10-bit · libx264    · mã HIỆN TẠI      -> ca đã chữa

Đo: pix_fmt · profile · WxH · nb_frames (metadata VÀ giải mã thật) · duration ·
moov ở đầu file · mở được không (decode HẾT khung, đọc stderr) · trích PNG.
KHÔNG kết luận bằng mã thoát ffmpeg.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FFMPEG = str(REPO / "bin" / "ffmpeg.exe")
FFPROBE = str(REPO / "bin" / "ffprobe.exe")

SAN = Path(r"D:\claude\_do_nvenc")
NGUON8 = SAN / "nguon" / "goc.mp4"          # BẢN SAO video anh Hùng
NGUON10 = SAN / "nguon" / "goc10.mp4"       # bản 10-bit dựng từ chính nó
RA = SAN / "ra"
PNG = SAN / "png"
for d in (SAN / "nguon", RA, PNG):
    d.mkdir(parents=True, exist_ok=True)

SEGS = [(12.0, 20.0), (40.0, 48.0), (70.0, 76.0)]   # GHÉP 3 PART


def soi(p) -> dict:
    """ffprobe: mọi thứ cần để kết luận, KHÔNG dựa vào mã thoát lượt xuất."""
    p = str(p)
    if not os.path.exists(p):
        return {"co": False}
    r = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", p], capture_output=True, timeout=300)
    d = json.loads(r.stdout.decode("utf-8", "replace") or "{}")
    o = {"co": True, "byte": os.path.getsize(p)}
    o["dur"] = float(d.get("format", {}).get("duration") or 0)
    for s in d.get("streams", []):
        if s.get("codec_type") == "video":
            o.update(pix_fmt=s.get("pix_fmt"), profile=s.get("profile"),
                     codec=s.get("codec_name"), w=s.get("width"),
                     h=s.get("height"), nb=s.get("nb_frames"))
        elif s.get("codec_type") == "audio":
            o["a"] = s.get("codec_name")
    with open(p, "rb") as f:
        head = f.read(1 << 16)
    # `-movflags +faststart` -> `moov` phải nằm NGAY ĐẦU file
    o["moov_dau"] = b"moov" in head
    return o


def giai_ma_het(p) -> tuple[int, str]:
    """MỞ ĐƯỢC KHÔNG: giải mã HẾT khung, trả (số khung, lỗi đọc được).

    Thay cho `ffplay -autoexit` — không được mở trình phát trên máy anh Hùng.
    """
    r = subprocess.run([FFMPEG, "-v", "error", "-xerror", "-i", str(p),
                        "-f", "null", "-"], capture_output=True, timeout=900)
    err = r.stderr.decode("utf-8", "replace").strip()
    r2 = subprocess.run([FFPROBE, "-v", "error", "-count_frames",
                         "-select_streams", "v:0", "-show_entries",
                         "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
                        capture_output=True, timeout=900)
    t = r2.stdout.decode("utf-8", "replace").strip().strip(",")
    try:
        n = int(t)
    except ValueError:
        n = -1
    return n, err[:300]


def trich_png(p, ten: str, giay: float) -> Path:
    """Trích 1 KHUNG ra PNG để NGƯỜI TỰ NHÌN (đếm pixel không đủ kết luận)."""
    out = PNG / f"{ten}_{giay:g}s.png"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", f"{giay:.2f}",
                    "-i", str(p), "-frames:v", "1", str(out)],
                   capture_output=True, timeout=300)
    return out


def dung_nguon_10bit() -> None:
    """Dựng nguồn 10-bit từ CHÍNH video anh Hùng (ca yt-dlp bestvideo)."""
    if NGUON10.exists() and NGUON10.stat().st_size > 1 << 20:
        return
    print("… dựng nguồn 10-bit (High 10) từ bản sao …", flush=True)
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-t", "80",
                        "-i", str(NGUON8), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p10le", "-profile:v", "high10",
                        "-preset", "ultrafast", "-crf", "20",
                        "-c:a", "aac", "-b:a", "128k", str(NGUON10)],
                       capture_output=True, timeout=1800)
    if r.returncode != 0:
        raise SystemExit("dựng nguồn 10-bit HỎNG: "
                         + r.stderr.decode("utf-8", "replace")[:400])


# ---- mã TRƯỚC bản vá: `_enc_args` nhánh libx264 KHÔNG có pix_fmt/profile ----
def _enc_args_TRUOC(encoder: str, quality: str = "high") -> list:
    from app.core.ffmpeg_utils import encode_threads
    if encoder == "h264_nvenc":
        cq = "19" if quality == "high" else "23"
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", cq,
                "-pix_fmt", "yuv420p", "-threads", str(encode_threads())]
    crf = "20" if quality == "high" else "23"
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
            "-threads", str(encode_threads())]


def chay(ten: str, src: Path, enc: str, truoc: bool = False,
         segs=None, bg: str = "blur") -> dict:
    from app.core import ffmpeg_utils as fu
    dst = RA / f"{ten}.mp4"
    if dst.exists():
        dst.unlink()
    goc_fn = fu._enc_args
    if truoc:
        fu._enc_args = _enc_args_TRUOC
    ok, loi = True, ""
    try:
        fu.export_canvas_clip(src=str(src), dst=str(dst),
                              segments=SEGS if segs is None else segs,
                              video_rect=(0.5, 0.5, 1.0), bg=bg,
                              out_w=1080, out_h=1920, encoder=enc)
    except Exception as e:                                    # noqa: BLE001
        ok, loi = False, f"{type(e).__name__}: {e}"[:500]
    finally:
        fu._enc_args = goc_fn
    d = soi(dst)
    d.update(ten=ten, enc_xin=enc, ok=ok, loi=loi)
    if d.get("co"):
        d["nb_that"], d["loi_doc"] = giai_ma_het(dst)
        d["png"] = str(trich_png(dst, ten, 4.0))
    return d


def in_bang(rows) -> None:
    print()
    print(f"{'arm':<26}{'enc xin':<12}{'pix_fmt':<14}{'profile':<26}"
          f"{'WxH':<12}{'giây':<8}{'MB':<7}{'moov':<7}")
    print("-" * 114)
    for r in rows:
        if not r.get("co"):
            print(f"{r['ten']:<26}{r['enc_xin']:<12}KHÔNG RA FILE — "
                  f"{r.get('loi', '')[:52]}")
            continue
        print(f"{r['ten']:<26}{r['enc_xin']:<12}{str(r.get('pix_fmt')):<14}"
              f"{str(r.get('profile')):<26}"
              f"{r.get('w')}x{str(r.get('h')):<7}{r.get('dur', 0):<8.2f}"
              f"{r['byte'] / 1e6:<7.1f}{'CÓ' if r.get('moov_dau') else 'KHÔNG':<7}")
    print()
    print(f"{'arm':<26}{'nb_frames(meta)':<18}{'GIẢI MÃ THẬT':<16}"
          f"{'lỗi khi mở':<40}")
    print("-" * 100)
    for r in rows:
        if r.get("co"):
            print(f"{r['ten']:<26}{str(r.get('nb')):<18}"
                  f"{str(r.get('nb_that')):<16}"
                  f"{(r.get('loi_doc') or 'không') :<40}")


if __name__ == "__main__":
    from app.core import ffmpeg_utils as fu
    print("ffmpeg  :", fu.settings.FFMPEG_PATH)
    print("nguồn 8 :", soi(NGUON8))
    dung_nguon_10bit()
    print("nguồn 10:", soi(NGUON10))

    # 1 ĐOẠN: nguồn vào THẲNG filter graph, KHÔNG qua mezzanine -> đây mới là
    # chỗ `_enc_args` tự chọn pix_fmt theo nguồn. Đường GHÉP NHIỀU PART đã được
    # mezzanine (`_build_seg`) ép 420p từ trước nên nó KHÔNG tái hiện được bệnh.
    MOT = [(12.0, 26.0)]
    rows = [
        chay("A_8bit_nvenc_NAY", NGUON8, "h264_nvenc"),
        chay("B_10bit_nvenc_NAY", NGUON10, "h264_nvenc"),
        chay("C_10bit_x264_TRUOC", NGUON10, "libx264", truoc=True),
        chay("D_10bit_x264_NAY", NGUON10, "libx264"),
        chay("E_1doan_10bit_x264_TRUOC", NGUON10, "libx264", truoc=True,
             segs=MOT),
        chay("F_1doan_10bit_x264_NAY", NGUON10, "libx264", segs=MOT),
        chay("G_1doan_10bit_nvenc_TRUOC", NGUON10, "h264_nvenc", truoc=True,
             segs=MOT),
        chay("H_1doan_10bit_nvenc_NAY", NGUON10, "h264_nvenc", segs=MOT),
        # nền `fill` = crop cho đầy khung, KHÔNG có `overlay`. `overlay` của
        # ffmpeg mặc định `format=yuv420` nên nó GHIM 420p — đó là lý do mọi
        # arm nền `blur` ở trên không tái hiện được bệnh dù chạy mã TRƯỚC.
        chay("I_fill_10bit_x264_TRUOC", NGUON10, "libx264", truoc=True,
             segs=MOT, bg="fill"),
        chay("J_fill_10bit_x264_NAY", NGUON10, "libx264", segs=MOT, bg="fill"),
        chay("K_fill_10bit_nvenc_TRUOC", NGUON10, "h264_nvenc", truoc=True,
             segs=MOT, bg="fill"),
        chay("L_fill_10bit_nvenc_NAY", NGUON10, "h264_nvenc", segs=MOT,
             bg="fill"),
    ]
    in_bang(rows)

    print("\nẢNH ĐỂ NHÌN TẬN MẮT:")
    for r in rows:
        if r.get("png"):
            print("   ", r["png"])

    xau = [r for r in rows
           if r.get("co") and (r.get("pix_fmt") != "yuv420p"
                               or str(r.get("profile")) not in ("High",))]
    print(f"\nARM RA KHÁC yuv420p/High: {len(xau)}/{len(rows)}")
    for r in xau:
        print("   ", r["ten"], "->", r.get("pix_fmt"), "|", r.get("profile"))
