"""ĐO TÍN HIỆU (b): đặc trưng giọng ECAPA-TDNN — người kể là MỘT giọng chiếm
phần lớn thời lượng, thu phòng sạch; tiếng trong phim là giọng khác + có nền.

BẮT BUỘC TỰ KIỂM BỘ DÒ TRƯỚC (luật đã ghi trong CLAUDE.md): chạy chính thước
này trên edge-tts, nơi biết chắc giọng nào là giọng nào. Mốc phải đạt:
cùng giọng ~0,78 · khác giọng <= 0,31. Không đạt thì mọi số sau là vô nghĩa.

torch nằm ở `_giong_ngoai/venv`, speechbrain ở `_kq_nn/sb` -> chạy Ở TIẾN
TRÌNH RIÊNG (import torch sau khi Qt nạp là ACCESS VIOLATION; ở đây không có
Qt nhưng vẫn giữ khuôn tiến trình riêng cho giống đường app đi).

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_ecapa.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
PY_TORCH = GOC / "_giong_ngoai" / "venv" / "Scripts" / "python.exe"
SB = GOC / "_kq_nn" / "sb"
FF = str(GOC / "bin" / "ffmpeg.exe")
_NO_WIN = 0x08000000 if os.name == "nt" else 0

MA_RUNNER = r'''
import json, sys, os
sys.path.insert(0, sys.argv[1])          # _kq_nn/sb (speechbrain)
sys.stdout.reconfigure(encoding="utf-8")
job = json.load(open(sys.argv[2], encoding="utf-8"))
import numpy as np, torch, soundfile as sf
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy
dev = "cuda" if torch.cuda.is_available() else "cpu"
# BẪY WINDOWS: speechbrain mặc định SYMLINK từ cache HF sang savedir ->
# WinError 1314 "A required privilege is not held" vì máy không bật Developer
# Mode. Phải ép COPY.
m = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=job["savedir"], run_opts={"device": dev},
    local_strategy=LocalStrategy.COPY)
def emb(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != 16000:
        raise RuntimeError(f"sai tan so {sr}")
    if x.shape[0] < 1600:                 # < 0,1 giay
        return None
    with torch.no_grad():
        e = m.encode_batch(torch.from_numpy(x)[None].to(dev))
    v = e.squeeze().detach().cpu().numpy().astype(float)
    n = float(np.linalg.norm(v))
    return (v / n).tolist() if n > 0 else None
ra = {}
for k, p in job["files"].items():
    try:
        ra[k] = emb(p)
    except Exception as ex:
        ra[k] = None
        print(f"LOI {k}: {type(ex).__name__} {ex}", file=sys.stderr)
print("BQJSON\t" + json.dumps({"dev": dev, "torch": torch.__version__,
                               "emb": ra}))
'''


def chay_emb(files: dict[str, str]) -> dict:
    run = SAN / "_ecapa_runner.py"
    run.write_text(MA_RUNNER, encoding="utf-8")
    job = SAN / "_ecapa_job.json"
    job.write_text(json.dumps({"files": files,
                               "savedir": str(SAN / "ecapa_model")}),
                   encoding="utf-8")
    p = subprocess.run([str(PY_TORCH), "-u", str(run), str(SB), str(job)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NO_WIN, timeout=3600)
    for dong in (p.stdout or "").splitlines():
        if dong.startswith("BQJSON\t"):
            return json.loads(dong[7:])
    raise RuntimeError(f"runner that bai rc={p.returncode}\n"
                       f"{(p.stdout or '')[-800:]}\n{(p.stderr or '')[-1500:]}")


def cat(src: str, a: float, b: float, out: Path) -> bool:
    """Cắt [a,b] ra wav 16k mono. Trả False nếu file rỗng/ngắn."""
    if b - a < 0.35:
        return False
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}",
         "-i", src, "-vn", "-ac", "1", "-ar", "16000", str(out)],
        capture_output=True, creationflags=_NO_WIN, timeout=180)
    # BẪY: ffmpeg mã 0 + file 0 KiB -> kiểm KÍCH THƯỚC
    return r.returncode == 0 and out.exists() and out.stat().st_size > 4000


def tu_kiem() -> float:
    """Sinh edge-tts 2 giọng x 3 câu rồi đo — thước phải tách 2 nhóm."""
    from app.core import thay_giong as tg
    import numpy as np
    d = SAN / "tukiem"
    d.mkdir(parents=True, exist_ok=True)
    CAU = ["Hôm nay trời rất đẹp, chúng ta cùng đi dạo một chút nhé.",
           "Cơn bão lớn nhất trong lịch sử đang tiến vào thành phố này.",
           "Anh ấy mở cửa ra và thấy một người lạ đang đứng ngoài sân."]
    GIONG = ["vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"]
    files = {}
    for gi, v in enumerate(GIONG):
        for ci, c in enumerate(CAU):
            w = d / f"g{gi}_c{ci}.wav"
            if not w.exists():
                raw = d / f"g{gi}_c{ci}_raw.wav"
                tg.doc_thu(v, raw, text=c)
                subprocess.run([FF, "-y", "-v", "error", "-i", str(raw),
                                "-ac", "1", "-ar", "16000", str(w)],
                               check=True, creationflags=_NO_WIN, timeout=180)
            files[f"g{gi}_c{ci}"] = str(w)
    kq = chay_emb(files)
    E = {k: np.array(v) for k, v in kq["emb"].items() if v}
    print(f"   thiet bi={kq['dev']} torch={kq['torch']} "
          f"emb={len(E)}/{len(files)}")
    trong, cheo = [], []
    ks = sorted(E)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            s = float(E[ks[i]] @ E[ks[j]])
            (trong if ks[i][:2] == ks[j][:2] else cheo).append(s)
    print(f"   CUNG giong (n={len(trong)}): "
          f"{min(trong):.3f} .. {max(trong):.3f}  TB {sum(trong)/len(trong):.3f}")
    print(f"   KHAC giong (n={len(cheo)}): "
          f"{min(cheo):.3f} .. {max(cheo):.3f}  TB {sum(cheo)/len(cheo):.3f}")
    if min(trong) <= max(cheo):
        print("   -> THUOC KHONG TACH DUOC. DUNG.")
        sys.exit(1)
    ng = (min(trong) + max(cheo)) / 2
    print(f"   -> TACH ROI. khoang trong {min(trong)-max(cheo):.3f}, "
          f"nguong giua {ng:.3f}")
    return ng


def main() -> None:
    import numpy as np
    print("== TU KIEM BO DO tren edge-tts ==")
    ng = tu_kiem()

    print("== DO 4 VIDEO ==")
    ket = {}
    for ten in ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung"):
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        cau = d["cau"]
        w16 = str(SAN / "wav" / f"{ten}_16k.wav")
        dd = SAN / "doan" / ten
        dd.mkdir(parents=True, exist_ok=True)
        files = {}
        for i, c in enumerate(cau):
            p = dd / f"{i:04d}.wav"
            if p.exists() and p.stat().st_size > 4000:
                files[str(i)] = str(p)
            elif cat(w16, float(c["start"]), float(c["end"]), p):
                files[str(i)] = str(p)
        kq = chay_emb(files)
        E = {int(k): np.array(v) for k, v in kq["emb"].items() if v}
        if len(E) < 10:
            print(f"   {ten}: chi {len(E)} emb -> bo qua")
            continue
        # TÂM giọng chiếm phần lớn THỜI LƯỢNG: lặp 5 vòng, mỗi vòng chỉ giữ
        # các đoạn gần tâm (bỏ ngoại lai) rồi tính lại tâm, trọng số = giây.
        ids = sorted(E)
        M = np.stack([E[i] for i in ids])
        w = np.array([float(cau[i]["end"]) - float(cau[i]["start"])
                      for i in ids])
        giu = np.ones(len(ids), dtype=bool)
        for _ in range(5):
            tam = (M[giu] * w[giu, None]).sum(axis=0)
            tam /= max(1e-9, float(np.linalg.norm(tam)))
            s = M @ tam
            giu = s >= float(np.quantile(s[giu], 0.15))
        s = M @ tam
        ket[ten] = {"nguong_tu_kiem": ng,
                    "diem": {str(i): round(float(v), 4)
                             for i, v in zip(ids, s)},
                    "thieu": [i for i in range(len(cau)) if i not in E]}
        q = np.quantile(s, [0.01, 0.05, 0.25, 0.5, 0.95])
        print(f"   {ten}: {len(ids)}/{len(cau)} doan do duoc | "
              f"giong voi TAM: 1% {q[0]:.3f} 5% {q[1]:.3f} 25% {q[2]:.3f} "
              f"trung vi {q[3]:.3f} 95% {q[4]:.3f}")
        thap = sorted(zip(s, ids))[:8]
        for v, i in thap:
            print(f"      #{i:3d} [{cau[i]['start']:7.2f}] {v:+.3f}  "
                  f"{cau[i]['text'][:44]}")
    (SAN / "ecapa.json").write_text(json.dumps(ket, ensure_ascii=False),
                                    encoding="utf-8")
    print("GHI: _kq_nn/ecapa.json")


if __name__ == "__main__":
    main()
