"""GỌI LẺ vs GỌI GỘP. Bài học Piper: mỗi lượt gọi tiến trình rời là nạp lại
model. Ở Kokoro số đó lớn hơn hẳn (đo 60,5s lượt đầu) nên câu hỏi "doc_loat có
gom được không" là câu hỏi về THỜI GIAN THẬT của một video 40-50 câu.

ĐAN XEN + lấy lượt nhanh nhất (luật đo A/B của repo này: máy luôn có việc nền).
"""
import os, sys, time, pathlib, tempfile, shutil, statistics
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core import giong_kokoro as KK

CAU = [f"Sentence number {i} for the batching measurement." for i in range(1, 13)]
MA = "kk:af_bella"
sb = pathlib.Path(tempfile.mkdtemp(prefix="bq_kk_gom_"))

def le(k):
    t0 = time.time(); n = 0
    for i, c in enumerate(CAU):
        p = sb / f"le{k}_{i}.wav"
        r = KK.doc_loat([c], [str(p)], MA)
        n += 1 if (r and r[0] and p.is_file()) else 0
    return time.time() - t0, n

def gom(k):
    ps = [str(sb / f"gom{k}_{i}.wav") for i in range(len(CAU))]
    t0 = time.time()
    r = KK.doc_loat(list(CAU), ps, MA)
    return time.time() - t0, sum(1 for i, p in enumerate(ps)
                                 if r and i < len(r) and r[i]
                                 and pathlib.Path(p).is_file())

print("nap model mot lan cho am (khong tinh vao bang)...")
KK.doc_loat([CAU[0]], [str(sb / "warm.wav")], MA)

LE, GOM = [], []
for k in range(2):                       # ĐAN XEN, xoay thứ tự
    if k % 2 == 0:
        a = le(k);  b = gom(k)
    else:
        b = gom(k); a = le(k)
    LE.append(a); GOM.append(b)
    print(f"  vong {k+1}: le {a[0]:6.2f}s ({a[1]}/{len(CAU)} wav) | "
          f"gom {b[0]:6.2f}s ({b[1]}/{len(CAU)} wav)")

tle = min(x[0] for x in LE); tgom = min(x[0] for x in GOM)
print(f"\n=== {len(CAU)} cau, lay luot NHANH NHAT moi ben ===")
print(f"  goi LE  (1 cau/luot): {tle:6.2f}s  ({tle/len(CAU):.2f}s/cau)")
print(f"  goi GOM (1 luot)    : {tgom:6.2f}s  ({tgom/len(CAU):.2f}s/cau)")
print(f"  GOM nhanh hon: {tle/tgom:.2f} lan")
print(f"  wav ra du: le {min(x[1] for x in LE)}/{len(CAU)} · "
      f"gom {min(x[1] for x in GOM)}/{len(CAU)}")
print(f"\n  suy ra video 45 cau: le ~{tle/len(CAU)*45:.0f}s · "
      f"gom ~{tgom/len(CAU)*45:.0f}s")
shutil.rmtree(sb, ignore_errors=True)
