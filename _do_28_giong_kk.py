"""ĐỌC THẬT cả 28 giọng Kokoro rồi ĐO WAV. Giọng CÂM phải lộ ra.

Vì sao phải đo: `giong_kokoro.doc_loat` trả True/False, nhưng "trả True" KHÔNG
đồng nghĩa "nghe được" — `_kiem_wav` chỉ hỏi có tiếng không. Trước lượt này chỉ
`kk:af_bella` từng được đọc thử; 27 giọng còn lại nằm trong combo mà chưa ai
biết chúng có kêu hay không.
"""
import os, sys, json, time, wave, math, array, pathlib, tempfile, shutil
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core import giong_kokoro as KK

CAU = "This is a short test sentence to measure the voice."
sb = pathlib.Path(tempfile.mkdtemp(prefix="bq_kk28_"))
ds = KK.danh_sach_giong()
print(f"so giong trong combo: {len(ds)}\n")

def do_wav(p: pathlib.Path):
    """(giay, rms, dinh) — đọc mẫu THẲNG, không nhờ hàm của app tự chấm."""
    with wave.open(str(p), "rb") as w:
        n, sr, sw = w.getnframes(), w.getframerate(), w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2 or n == 0:
        return (n / sr if sr else 0.0), 0.0, 0.0
    a = array.array("h"); a.frombytes(raw)
    s = sum(float(v) * v for v in a)
    return n / sr, math.sqrt(s / len(a)) / 32768.0, max(abs(v) for v in a) / 32768.0

bang = []
for i, (ma, nhan) in enumerate(ds, 1):
    out = sb / f"{ma.replace(':', '_')}.wav"
    t0 = time.time()
    try:
        ok = KK.doc_loat([CAU], [str(out)], ma)
        ok1 = bool(ok and ok[0])
    except Exception as e:
        ok1 = False; nhan += f" [NEM {type(e).__name__}]"
    giay = time.time() - t0
    if ok1 and out.is_file():
        d, rms, dinh = do_wav(out)
    else:
        d, rms, dinh = 0.0, 0.0, 0.0
    cam = (not ok1) or d < 0.5 or rms < KK.RMS_TOI_THIEU
    bang.append({"ma": ma, "ok": ok1, "giay_wav": round(d, 2),
                 "rms": round(rms, 5), "dinh": round(dinh, 3),
                 "giay_doc": round(giay, 1), "CAM": cam})
    print(f"{i:2}/{len(ds)} {ma:16} ok={ok1!s:5} dai={d:5.2f}s "
          f"rms={rms:.5f} dinh={dinh:.3f} ({giay:.1f}s)"
          + ("   <<< CAM/HONG" if cam else ""))

cam = [b for b in bang if b["CAM"]]
print(f"\n=== TONG: {len(bang) - len(cam)}/{len(bang)} KEU · {len(cam)} CAM ===")
for b in cam:
    print("  CAM:", b["ma"], b)
if bang:
    kd = [b for b in bang if not b["CAM"]]
    if kd:
        print(f"  rms thap nhat trong so giong keu: "
              f"{min(b['rms'] for b in kd):.5f} (san {KK.RMS_TOI_THIEU})")
        print(f"  dai: {min(b['giay_wav'] for b in kd):.2f} - "
              f"{max(b['giay_wav'] for b in kd):.2f} s")
        print(f"  giay doc/cau: {min(b['giay_doc'] for b in kd):.1f} - "
              f"{max(b['giay_doc'] for b in kd):.1f} s")
pathlib.Path("_kq_kk28.json").write_text(
    json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.rmtree(sb, ignore_errors=True)
print("\nghi _kq_kk28.json")
