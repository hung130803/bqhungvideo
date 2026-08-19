"""ĐO ĐƯỜNG NHÂN BẢN GIỌNG — đi ĐÚNG cửa ``nhan_ban_giong`` mà anh Hùng sẽ bấm.

Không đo hàm của VieNeu/Chatterbox trực tiếp: đo **cả đường** chọn-mẫu ->
kiểm-mẫu -> lưu-sổ -> đọc. Đo hàm con thì bỏ sót đúng chỗ hay hỏng nhất (bài
học cổng 19: mẫu-theo-kênh chạy đúng ở hàm mà bấm tay vẫn ăn mẫu sai).

BA CÂU HỎI:
  1. Đưa 3 mẫu Việt KHÁC NHAU vào -> có ra 3 giọng KHÁC NHAU không (ECAPA)?
  2. **ĐỐI CHỨNG ÂM**: có khác giọng dựng sẵn của VieNeu không? (nếu bằng
     nhau thì nhân bản KHÔNG chạy — đúng bẫy ``use_ref_codes`` lượt 4.)
  3. Chữ hiện lệch tiếng bao nhiêu ms (``silencedetect``, thước ĐỘC LẬP)?

Mẫu sinh bằng edge-tts nên **sạch giấy phép** (không đụng giọng người thật) và
biết chắc 3 mẫu là 3 giọng khác nhau.

Chạy: .venv\\Scripts\\python -u _do_nhan_ban.py
"""
from __future__ import annotations

import os
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "_lib_giong"))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "_do_chatter" / "nb"
os.environ.setdefault("BQ_DATA_DIR", str(SAN / "data"))
FF = str(REPO / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: 3 giọng edge-tts Việt + 1 biến thể cao độ -> 3 "người" khác nhau.
MAU_VI = [("v0", "vi-VN-NamMinhNeural"), ("v1", "vi-VN-HoaiMyNeural"),
          ("v2", "vi-VN-NamMinhNeural|-30Hz")]

CAU_MAU_VI = ("Đây là đoạn ghi âm ngắn để làm mẫu giọng. Tôi đọc vài câu cho "
              "đủ dài, để máy có thể học được chất giọng của tôi một cách "
              "chính xác nhất.")

CAU_DO_VI = [
    "Một cơn bão chưa từng có trong lịch sử đang ập tới thành phố này.",
    "Bạn có tin được không? Chỉ trong ba phút, cả toà nhà đã biến mất!",
    "Anh ta quay lại, và nhận ra mình đã đi sai đường ngay từ đầu.",
]


def wav16(src: Path, dst: Path) -> bool:
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-vn",
                        "-ac", "1", "-ar", "16000", str(dst)],
                       capture_output=True, creationflags=_NO_WIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def moc_phat_tieng(wav: Path) -> float:
    """Giây đầu tiên THẬT SỰ có tiếng — thước ĐỘC LẬP (không máy nghe)."""
    r = subprocess.run(
        [FF, "-v", "info", "-i", str(wav), "-af",
         "silencedetect=noise=-45dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=180)
    for d in (r.stderr or "").splitlines():
        if "silence_end:" in d:
            try:
                return float(d.split("silence_end:")[1].split()[0])
            except (IndexError, ValueError):
                pass
    return 0.0


def main() -> int:
    import asyncio

    from _do_chatter import chay_ecapa, cos
    from app.core import dubbing, giong_vieneu
    from app.core import nhan_ban_giong as nb

    SAN.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("ĐO NHÂN BẢN GIỌNG TIẾNG VIỆT — qua cửa nhan_ban_giong")
    print("=" * 74)
    tt = giong_vieneu.tinh_trang_vieneu()
    print(f"VieNeu: có={tt['co']} · bản {tt.get('phien_ban')} · "
          f"{tt.get('so_giong')} giọng dựng sẵn")
    if not tt["co"]:
        print("CHƯA CÀI VieNeu -> không đo được. Dừng (không bịa số).")
        return 2

    print("\n[1/4] Sinh 3 mẫu tiếng Việt bằng edge-tts...")
    d = SAN / "mau"
    d.mkdir(parents=True, exist_ok=True)
    mau: dict[str, str] = {}
    for k, v in MAU_VI:
        w = d / f"{k}.wav"
        if not (w.exists() and w.stat().st_size > 4000):
            mp3 = d / f"{k}.mp3"
            ok = asyncio.run(dubbing._synth_all([CAU_MAU_VI], v, [str(mp3)]))
            if not (ok and ok[0] and wav16(mp3, w)):
                print(f"  MẪU HỎNG {k}")
                continue
        mau[k] = str(w)
    print(f"  có {len(mau)}/3 mẫu")
    if len(mau) < 2:
        return 2

    print("\n[2/4] Thêm vào sổ qua nhan_ban_giong.them_giong (có KIỂM mẫu)...")
    ma_theo: dict[str, str] = {}
    for k, p in mau.items():
        nb.xoa(f"Giọng thử {k}")
        r = nb.them_giong(f"Giọng thử {k}", p, lang="vi",
                          nguon="mẫu sinh bằng edge-tts cho phép đo")
        print(f"  {k}: ok={r['ok']} {r['loi']}")
        if r["ok"]:
            ma_theo[k] = r["ma"]
    if len(ma_theo) < 2:
        return 1

    print("\n[3/4] Đọc 3 câu bằng mỗi giọng nhân bản + arm ĐỐI CHỨNG ÂM "
          "(giọng DỰNG SẴN của VieNeu)...")
    d_ra = SAN / "ra"
    d_ra.mkdir(parents=True, exist_ok=True)
    arms = dict(ma_theo)
    ds = giong_vieneu.danh_sach_giong()
    if ds:
        arms["dung_san"] = ds[0][0]
        print(f"  đối chứng âm: {ds[0][0]}")
    tre: list[float] = []
    for a, ma in arms.items():
        outs = [str(d_ra / f"{a}_c{j}.mp3") for j in range(len(CAU_DO_VI))]
        if all(Path(o).exists() and Path(o).stat().st_size > 1000
               for o in outs):
            continue
        t0 = time.monotonic()
        ok, _w = giong_vieneu.doc_loat(CAU_DO_VI, outs, ma, lay_moc=False)
        print(f"  {a:12s} đọc {sum(ok)}/{len(ok)} câu · "
              f"{time.monotonic()-t0:.1f}s")

    print("\n[4/4] ECAPA + mốc phát tiếng")
    files: dict[str, str] = {}
    d16 = SAN / "e16"
    d16.mkdir(parents=True, exist_ok=True)
    for k, p in mau.items():
        files[f"ref_{k}"] = p
    for a in arms:
        for j in range(len(CAU_DO_VI)):
            src = d_ra / f"{a}_c{j}.mp3"
            if not src.exists():
                continue
            w = d16 / f"{a}_{j}.wav"
            if (w.exists() and w.stat().st_size > 4000) or wav16(src, w):
                files[f"{a}#{j}"] = str(w)
                if a != "dung_san":
                    tre.append(moc_phat_tieng(w))
    e = chay_ecapa(files)
    emb = {k: v for k, v in e["emb"].items() if v}
    tb = {}
    for a in arms:
        vs = [emb[f"{a}#{j}"] for j in range(len(CAU_DO_VI))
              if f"{a}#{j}" in emb]
        if not vs:
            continue
        m = [sum(c) / len(vs) for c in zip(*vs)]
        n = sum(x * x for x in m) ** 0.5
        if n:
            tb[a] = [x / n for x in m]
    if not tb:
        print("  ECAPA KHÔNG RA SỐ — phép đo HỎNG, không phải kết luận. Dừng.")
        return 1
    print(f"  {'arm':12s} cos(bản sao, MẪU của nó)  cos(bản sao, DỰNG SẴN)")
    cm_ds, cd_ds = [], []
    for a in ma_theo:
        if a not in tb:
            continue
        cm = cos(tb[a], emb[f"ref_{a}"]) if f"ref_{a}" in emb else float("nan")
        cd = cos(tb[a], tb["dung_san"]) if "dung_san" in tb else float("nan")
        cm_ds.append(cm)
        cd_ds.append(cd)
        print(f"  {a:12s} {cm:22.3f} {cd:22.3f}")
    ks = [a for a in ma_theo if a in tb]
    cap = [cos(tb[ks[i]], tb[ks[j]])
           for i in range(len(ks)) for j in range(i + 1, len(ks))]
    if cap:
        print(f"\n  cặp bản-sao-khác-nhau: TB {st.mean(cap):.3f} · "
              f"max {max(cap):.3f}   (khác giọng <= 0,31)")
    if cm_ds:
        print(f"  cos(bản sao, mẫu của nó): TB {st.mean(cm_ds):.3f}")
    if cd_ds:
        print(f"  cos(bản sao, DỰNG SẴN):   TB {st.mean(cd_ds):.3f}"
              f"   <- ĐỐI CHỨNG ÂM")
    NG = 0.60
    rieng = [ks[0]] if ks else []
    for a in ks[1:]:
        if all(cos(tb[a], tb[b]) <= NG for b in rieng):
            rieng.append(a)
    print(f"  => SỐ GIỌNG THẬT: {len(rieng)}/{len(ks)} mẫu đưa vào")
    if tre:
        print(f"  lề IM đầu file: TB {1000*st.mean(tre):.0f} ms · "
              f"max {1000*max(tre):.0f} ms")
    for k in list(ma_theo):
        nb.xoa(f"Giọng thử {k}")
    print("\nXONG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
