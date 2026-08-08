# -*- coding: utf-8 -*-
"""CỔNG 23 — KHO TIẾNG ĐỘNG NÉN PHẢI THẬT SỰ KÊU TRONG CLIP.

LỖI THẬT ĐÃ BẮT (05/08/2026): `_sfx_library()` chỉ nhận `.wav`
(`ffmpeg_utils.py:857`). Tải kho CC0 về lưu Opus 32k (nhẹ hơn WAV 21 lần) thì
app **KHÔNG THẤY FILE NÀO** và lùi im lặng sang tiếng tổng hợp — kho gộp vào
coi như vô ích mà không ai biết. Nay nhận .wav/.opus/.ogg/.mp3/.m4a.

BẤT BIẾN CANH Ở ĐÂY:
  1. Mọi nhóm trong SFX_CATEGORIES đều có file (không nhóm nào rỗng).
  2. Kho ĐỦ ĐA DẠNG: >= 150 file, >= 8 nhóm có >= 3 file (300 kênh không
     nghe ra trùng tiếng).
  3. DUNG LƯỢNG: toàn kho <= 700 KB (mốc: kho WAV cũ 1 598 KB) — cấm phình
     bản cài cho nhân viên.
  4. MỌI file trong kho ffmpeg ĐỌC ĐƯỢC (probe ra audio, độ dài > 0).
  5. Chọn theo ngữ cảnh vẫn đúng nhóm, và KHÔNG lặp file 2 lần liên tiếp.
  6. XUẤT CLIP THẬT: tiếng động phải NGHE ĐƯỢC đúng mốc ghép — đo RMS quanh
     điểm nối phải CAO HƠN hẳn lúc không bật tiếng (không chỉ "chạy không lỗi").
  7. Âm lượng có kiểm soát: đỉnh clip không vượt 0 dBFS (tiếng động không
     được làm vỡ tiếng gốc).
"""
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile

T = tempfile.mkdtemp(prefix="sfxkho_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from app.core import ffmpeg_utils as FU  # noqa: E402

FF = os.path.join(REPO, "bin", "ffmpeg.exe")
FP = os.path.join(REPO, "bin", "ffprobe.exe")
FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


print("\n══ 1. Kho: đủ nhóm · đủ đa dạng · đủ nhẹ ══")
lib = FU._sfx_library()
tong_file = sum(len(v) for v in lib.values())
rong = [k for k, v in lib.items() if not v]
kiem(not rong, f"cả {len(lib)} nhóm đều có file", str(rong))
kiem(tong_file >= 150, f"kho có {tong_file} file (cần >= 150)")
du3 = [k for k, v in lib.items() if len(v) >= 3]
kiem(len(du3) >= 8, f"{len(du3)} nhóm có >= 3 file (cần >= 8)")
print("     " + " · ".join(f"{k} {len(v)}" for k, v in sorted(lib.items())))
base = FU._assets_sfx_dir()
cỡ = sum(f.stat().st_size for f in base.rglob("*.*") if f.suffix != ".md")
kiem(cỡ <= 700 * 1024, f"toàn kho = {cỡ/1024:.0f} KB (trần 700 KB · WAV cũ "
                       f"1 598 KB)")
n_wav = len(list(base.rglob("*.wav")))
print(f"     định dạng: {len(list(base.rglob('*.opus')))} opus · {n_wav} wav")

print("\n══ 2. ffmpeg ĐỌC ĐƯỢC mọi file trong kho ══")
loi, tong_dai = [], 0.0
for cat, fs in lib.items():
    for f in fs:
        r = subprocess.run([FP, "-v", "error", "-select_streams", "a:0",
                            "-show_entries", "stream=codec_name:format=duration",
                            "-of", "json", f], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            d = float(j["format"]["duration"])
            assert j["streams"] and d > 0.02
            tong_dai += d
        except Exception:  # noqa: BLE001
            loi.append(os.path.basename(f))
kiem(not loi, f"{tong_file}/{tong_file} file đọc được "
              f"(tổng {tong_dai:.0f}s tiếng động)", str(loi[:5]))

print("\n══ 3. Chọn theo ngữ cảnh: đúng nhóm, không lặp liên tiếp ══")
cats = ["transition", "impact", "transition", "reveal", "transition"]
pick = FU._pick_sfx_by_category(cats, seed=7)
kiem([c for c, _ in pick] == cats, "trả đúng thứ tự nhóm yêu cầu")
kiem(all(p for _c, p in pick), "nhóm nào cũng ra file (không rơi về tổng hợp)")
tr = [p for c, p in pick if c == "transition"]
kiem(len(set(tr)) == len(tr), "3 lần 'transition' ra 3 file KHÁC nhau", str(tr))
kiem(FU._pick_sfx_by_category(["nhom_la_hoac_sai"])[0][0] == "transition",
     "nhóm lạ -> lùi 'transition', không nổ")

print("\n══ 4. XUẤT CLIP THẬT: tiếng động phải NGHE ĐƯỢC đúng mốc ══")
src = os.path.join(T, "nguon.mp4")
_r = subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                     "testsrc2=s=1280x720:r=30:d=24", "-f", "lavfi", "-i",
                     "sine=f=180:d=24:sample_rate=48000", "-shortest", "-c:v",
                     "libx264", "-preset", "ultrafast", "-c:a", "aac", src],
                    capture_output=True, text=True, errors="replace")
kiem(os.path.exists(src), f"dựng video nguồn 24s", (_r.stderr or "")[-200:])
SEG = [(1.0, 7.0), (10.0, 16.0)]      # nối ở giây 6.0 của clip đầu ra


def rms_quanh(mp4, moc, cua=0.35):
    """RMS dB trong cửa sổ quanh mốc (đo bằng ffmpeg volumedetect)."""
    r = subprocess.run([FF, "-hide_banner", "-ss", f"{max(0, moc-cua):.2f}",
                        "-t", f"{cua*2:.2f}", "-i", mp4, "-vn",
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    out = {"mean": None, "max": None}
    for ln in (r.stderr or "").splitlines():
        if "mean_volume:" in ln:
            out["mean"] = float(ln.split("mean_volume:")[1].split("dB")[0])
        if "max_volume:" in ln:
            out["max"] = float(ln.split("max_volume:")[1].split("dB")[0])
    return out


kq = {}
for ten, whoosh in (("KHÔNG tiếng động", False), ("CÓ tiếng động", True)):
    dst = os.path.join(T, f"ra_{int(whoosh)}.mp4")
    ok = FU.export_canvas_clip(src, dst, SEG, (0.5, 0.42, 1.0), bg="blur",
                               out_w=1080, out_h=1920, fx_whoosh=whoosh,
                               join_categories=["impact"] if whoosh else None)
    kiem(bool(ok) and os.path.exists(dst), f"xuất clip {ten}")
    kq[whoosh] = rms_quanh(dst, 6.0)
    print(f"     {ten}: RMS quanh mốc ghép = {kq[whoosh]['mean']} dB · "
          f"đỉnh {kq[whoosh]['max']} dB")
if kq.get(True, {}).get("mean") is not None and kq.get(False, {}).get("mean"):
    # ĐO BẰNG ĐỈNH, KHÔNG PHẢI RMS TRUNG BÌNH: tiếng động chỉ dài 0,2-0,4s nằm
    # trong cửa sổ 0,7s nên RMS trung bình chỉ nhích +0,30 dB (đo thật) — dùng
    # ngưỡng RMS là cổng báo FAIL oan dù tiếng kêu rất rõ. Đỉnh nhảy +12,4 dB.
    d_dinh = kq[True]["max"] - kq[False]["max"]
    d_rms = kq[True]["mean"] - kq[False]["mean"]
    kiem(d_dinh >= 5.0, f"bật tiếng động -> ĐỈNH quanh mốc tăng {d_dinh:+.1f} dB "
                        f"(RMS trung bình {d_rms:+.2f} dB — tiếng ngắn nên RMS "
                        f"gần như không đổi, phải đo đỉnh)")
    kiem(kq[True]["max"] <= 0.0,
         f"đỉnh {kq[True]['max']} dB <= 0 (không làm vỡ tiếng gốc)")
    kiem(FU._SFX_LAST_PICK and FU._SFX_LAST_PICK[0][1] not in (None, ""),
         f"đã dùng FILE trong kho, không phải tiếng tổng hợp: "
         f"{FU._SFX_LAST_PICK}")
    dung = str(FU._SFX_LAST_PICK[0][1] if FU._SFX_LAST_PICK else "")
    kiem(dung.lower().endswith((".opus", ".wav", ".ogg", ".mp3")),
         f"file dùng là file kho thật ({os.path.basename(dung)})")

print("\n══ 5. Kho user riêng (fx_sfx_dir) vẫn hoạt động ══")
ud = os.path.join(T, "sfx_user")
os.makedirs(ud, exist_ok=True)
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                "sine=f=900:d=0.3", os.path.join(ud, "cua_toi.wav")],
               capture_output=True)
kiem(len(FU._list_sfx_files(ud)) == 1, "đọc được thư mục tiếng động của user")
kiem(FU._list_sfx_files(None) == [], "không đặt thư mục -> rỗng, không nổ")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print(f"KẾT QUẢ: TẤT CẢ ĐẠT — kho {tong_file} file / {cỡ/1024:.0f} KB, "
      f"tiếng động kêu thật đúng mốc")
sys.stdout.flush()
os._exit(0)
