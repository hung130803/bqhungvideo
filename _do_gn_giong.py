# -*- coding: utf-8 -*-
"""ĐO GIỌNG NGOÀI BẰNG ĐƯỜNG CHẠY THẬT — 19/08/2026.

Trả lời ĐÚNG ba câu, mỗi câu bằng SỐ chứ không bằng đường dẫn:

  1. **Đọc ra WAV CÓ TIẾNG THẬT chưa** — gọi `giong_ngoai.doc_loat` (cửa app
     dùng), rồi ĐO LẠI file: độ dài + RMS + đỉnh. File 0 byte / 0 giây / im
     lặng đều bị đếm là HỎNG. Không tin cờ `ok` mà tiến trình con trả về.
  2. **BAO NHIÊU GIỌNG THẬT, và CHỌN X CÓ RA X KHÔNG** — bằng **ECAPA**
     (`speechbrain/spkrec-ecapa-voxceleb`, đã có trong kho HF của máy).
     MFCC/cao độ là thước HỎNG cho việc này: đã đo tự-ồn **97,7** trong khi
     khoảng cách giữa hai giọng khác nhau chỉ **48,4** — thước mà nhiễu của
     chính nó to gấp đôi tín hiệu thì mọi kết luận rút ra đều là kết luận về
     nhiễu.
     `ov:nu_am` từng là **giọng CHẾT từ lúc ra đời**: câu tả có chữ `warm`
     không nằm trong bảng từ đóng của model -> `ValueError` -> 0/4 câu, rồi
     `doc_loat` lùi êm về edge-tts, **không một dòng báo trên giao diện**.
     Đúng họ lỗi "chọn X ra Y".
  3. **PHỦ MỐC bằng GIÓNG HÀNG chạy trên CHÍNH file nó vừa đọc** — không
     phải trên bộ WAV cũ. OmniVoice **KHÔNG TIỀN ĐỊNH** (cùng hàm, cùng
     corpus, đo ra 41,8% rồi 99,4% chỉ vì khác MẺ TIẾNG), nên phủ phải đo
     trên đúng mẻ vừa sinh.

═══ SÀN NHIỄU LÀ BẮT BUỘC, KHÔNG PHẢI TRANG TRÍ ═══
Đọc mỗi khoảng cách ECAPA giữa hai giọng rồi kết luận "5 giọng khác nhau" là
chưa đo gì cả — phải biết **cùng MỘT giọng thì lệch bao nhiêu**. Script này
lấy hai sàn:
  · `san_trong_luot`  cùng giọng, cùng lượt gọi, khác câu
  · `san_qua_luot`    cùng giọng, lượt VI so lượt EN (khác lượt + khác tiếng)
Hai giọng chỉ được kể là KHÁC NHAU khi khoảng cách giữa chúng vượt HẲN sàn.
(Cùng bài học "GPU vs CPU −19 dB nhưng CPU vs CPU cũng −19 dB" của cổng 71.)

CHẠY: `.venv\\Scripts\\python.exe -u _do_gn_giong.py`
Kết quả JSON ở `_kq_ov/do_giong.json`, WAV giữ lại ở `_kq_ov/tieng/`.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

from config import settings                                  # noqa: E402

RA = REPO / "_kq_ov"
TIENG = RA / "tieng"
FF = settings.FFMPEG_PATH

#: Môi trường CÓ SẴN speechbrain trên máy này. CHỈ ĐỌC — không sửa gì trong
#: đó (luồng khác đang làm Chatterbox).
VENV_ECAPA = REPO / "_giong_chatter" / "venv" / "Scripts" / "python.exe"

CAU_VI = [
    "Hôm nay trời rất đẹp và chúng ta cùng nhau đi dạo ngoài công viên.",
    "Anh ấy mở cửa rồi bước vào trong căn phòng tối om không một tiếng động.",
    "Cô bé cầm chiếc bánh mì nóng hổi chạy thật nhanh về phía mẹ mình.",
]
CAU_EN = [
    "The old man opened the wooden door and looked at the empty street.",
    "She picked up the small blue book and started reading it slowly.",
    "Nobody knew what happened inside that house on the following morning.",
]


# ---------------------------------------------------------------------------
def do_wav(p: str) -> dict:
    """Độ dài + RMS + đỉnh, đọc THẲNG mẫu. File 0 byte thì mọi số ra 0."""
    try:
        with wave.open(str(p), "rb") as w:
            n, fr, sw, ch = (w.getnframes(), w.getframerate(),
                             w.getsampwidth(), w.getnchannels())
            raw = w.readframes(n)
    except Exception:                                        # noqa: BLE001
        return {"giay": 0.0, "rms": 0.0, "dinh": 0.0, "byte": 0}
    if sw != 2 or not n:
        return {"giay": (n / fr if fr else 0.0), "rms": 0.0, "dinh": 0.0,
                "byte": len(raw)}
    import array
    a = array.array("h")
    a.frombytes(raw)
    if ch > 1:
        a = array.array("h", a[::ch])
    if not len(a):
        return {"giay": 0.0, "rms": 0.0, "dinh": 0.0, "byte": len(raw)}
    s = 0.0
    dinh = 0
    for v in a:
        s += float(v) * v
        if abs(v) > dinh:
            dinh = abs(v)
    return {"giay": round(n / float(fr or 1), 3),
            "rms": round(math.sqrt(s / len(a)) / 32768.0, 5),
            "dinh": round(dinh / 32768.0, 4), "byte": len(raw)}


def sang_16k(src: str, dst: str) -> bool:
    """ECAPA đòi 16 kHz mono. Không đổi được thì BỎ mẫu đó, đừng đoán."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst],
            capture_output=True, timeout=180)
        return r.returncode == 0 and Path(dst).exists() \
            and Path(dst).stat().st_size > 1024
    except Exception:                                        # noqa: BLE001
        return False


_MA_ECAPA = r'''
import json, sys
job = json.load(open(sys.argv[1], encoding="utf-8"))
import numpy as np, torch, soundfile as sf
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb", savedir=job["savedir"],
    run_opts={"device": dev}, local_strategy=LocalStrategy.COPY)
def emb(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != 16000 or x.shape[0] < 1600:
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
        print("LOI %s: %s" % (k, ex), file=sys.stderr)
print("BQJSON\t" + json.dumps({"dev": dev, "emb": ra}))
'''


def ecapa(files: dict) -> dict:
    """{khoá: vector đơn vị}. Chạy ở TIẾN TRÌNH RIÊNG (torch sau Qt = 0xC5)."""
    if not VENV_ECAPA.exists():
        print(f"  KHÔNG có môi trường ECAPA ({VENV_ECAPA}) -> bỏ phần giọng")
        return {}
    runner = RA / "_ecapa_runner.py"
    runner.write_text(_MA_ECAPA, encoding="utf-8")
    job = RA / "_ecapa_job.json"
    job.write_text(json.dumps(
        {"files": files, "savedir": str(RA / "_sb")}, ensure_ascii=False),
        encoding="utf-8")
    try:
        r = subprocess.run([str(VENV_ECAPA), "-u", str(runner), str(job)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        print("  ECAPA quá giờ")
        return {}
    for d in (r.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            k = json.loads(d.split("\t", 1)[1])
            print(f"  ECAPA chạy trên: {k.get('dev')}")
            return {a: b for a, b in (k.get("emb") or {}).items() if b}
    print("  ECAPA hỏng:", (r.stderr or r.stdout or "")[-400:])
    return {}


def cos_kc(a: list, b: list) -> float:
    """Khoảng cách cosin (0 = trùng khít, 2 = ngược hẳn)."""
    return 1.0 - sum(x * y for x, y in zip(a, b))


def tk(v: list) -> str:
    if not v:
        return "—"
    v = sorted(v)
    tb = sum(v) / len(v)
    return (f"TB {tb:.4f} · nhỏ nhất {v[0]:.4f} · lớn nhất {v[-1]:.4f} "
            f"· n={len(v)}")


# ---------------------------------------------------------------------------
def main() -> int:                                          # noqa: C901
    from app.core import giong_ngoai as gn
    from app.core import giong_hang as gh
    from app.ai import recap

    RA.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("ĐO GIỌNG NGOÀI — ĐỌC THẬT · ECAPA · GIÓNG HÀNG")
    print("=" * 74)
    tt = gn.tinh_trang_omnivoice()
    print(f"python : {tt['python']}")
    print(f"model  : {tt['model']}")
    print(f"co     : {tt['co']}  thiếu: {tt['thieu']}")
    if not tt["co"]:
        print("CHƯA dùng được OmniVoice -> dừng, KHÔNG bịa số.")
        return 2

    kq: dict = {"doc": [], "ecapa": {}, "phu": {}}
    dsg = [m for m, _t, _n in gn.GIONG_OV]

    # ═══ 1. ĐỌC THẬT ═══
    for tieng, cau in (("vi", CAU_VI), ("en", CAU_EN)):
        for ma in dsg:
            ten = ma.replace(":", "_")
            paths = [str(TIENG / tieng / ten / f"c{i}.wav")
                     for i in range(len(cau))]
            t0 = time.time()
            ok, _moc = gn.doc_loat(cau, paths, ma, lang=tieng, lay_moc=False,
                                   han_giay=1800)
            giay = round(time.time() - t0, 2)
            do = [do_wav(p) for p in paths]
            co_tieng = [bool(o) and d["giay"] > 0.3 and d["rms"] > 0.005
                        for o, d in zip(ok, do)]
            kq["doc"].append({"tieng": tieng, "ma": ma, "giay": giay,
                              "ok": ok, "do": do, "co_tieng": co_tieng,
                              "paths": paths})
            print(f"  {tieng} {ma:12s} {sum(co_tieng)}/{len(cau)} câu CÓ TIẾNG"
                  f" · {giay:6.1f}s · dài {[d['giay'] for d in do]}"
                  f" · RMS {[d['rms'] for d in do]}")

    tong = sum(len(x["co_tieng"]) for x in kq["doc"])
    duoc = sum(sum(x["co_tieng"]) for x in kq["doc"])
    print(f"\n  TỔNG: {duoc}/{tong} câu ra WAV CÓ TIẾNG THẬT "
          f"(độ dài > 0,3 s VÀ RMS > 0,005)")
    chet = sorted({x["ma"] for x in kq["doc"] if not any(x["co_tieng"])})
    print(f"  GIỌNG CHẾT (0 câu nào đọc được): {chet or 'không có'}")

    # ═══ 2. ECAPA ═══
    print("\nECAPA — bao nhiêu GIỌNG THẬT, và chọn X có ra X không")
    files: dict = {}
    for x in kq["doc"]:
        for i, (p, c) in enumerate(zip(x["paths"], x["co_tieng"])):
            if not c:
                continue
            k = f"{x['tieng']}|{x['ma']}|{i}"
            d16 = str(TIENG / "16k" / (k.replace("|", "_") + ".wav"))
            if sang_16k(p, d16):
                files[k] = d16
    print(f"  {len(files)} mẫu đưa vào ECAPA")
    emb = ecapa(files) if files else {}
    kq["ecapa"]["so_mau"] = len(emb)

    if emb:
        theo: dict = {}
        for k, v in emb.items():
            t, ma, _i = k.split("|")
            theo.setdefault(ma, {}).setdefault(t, []).append(v)

        trong, qua, giua = [], [], []
        for ma, d in theo.items():
            for t, vs in d.items():
                for a in range(len(vs)):
                    for b in range(a + 1, len(vs)):
                        trong.append(cos_kc(vs[a], vs[b]))
            if "vi" in d and "en" in d:
                for a in d["vi"]:
                    for b in d["en"]:
                        qua.append(cos_kc(a, b))
        mas = sorted(theo)
        for a in range(len(mas)):
            for b in range(a + 1, len(mas)):
                for t in ("vi", "en"):
                    for x in theo[mas[a]].get(t, []):
                        for y in theo[mas[b]].get(t, []):
                            giua.append(cos_kc(x, y))
        print(f"  SÀN cùng giọng / cùng lượt : {tk(trong)}")
        print(f"  SÀN cùng giọng / khác lượt : {tk(qua)}")
        print(f"  GIỮA HAI GIỌNG KHÁC NHAU   : {tk(giua)}")
        kq["ecapa"].update({"san_trong": trong, "san_qua": qua,
                            "giua": giua})

        # tâm từng giọng (gộp cả 2 thứ tiếng)
        tam = {}
        for ma, d in theo.items():
            vs = [v for t in d for v in d[t]]
            n = len(vs)
            c = [sum(v[i] for v in vs) / n for i in range(len(vs[0]))]
            nn = math.sqrt(sum(x * x for x in c)) or 1.0
            tam[ma] = [x / nn for x in c]
        dung = 0
        tong_m = 0
        nham: list = []
        for k, v in emb.items():
            t, ma, i = k.split("|")
            gan = min(tam, key=lambda m: cos_kc(v, tam[m]))
            tong_m += 1
            if gan == ma:
                dung += 1
            else:
                nham.append((k, gan))
        print(f"  CHỌN X RA X: {dung}/{tong_m} mẫu gần TÂM CỦA CHÍNH GIỌNG "
              f"MÌNH nhất" + (f" · nhầm: {nham[:4]}" if nham else ""))
        kq["ecapa"]["chon_dung"] = [dung, tong_m]
        kq["ecapa"]["nham"] = nham

        # gộp giọng: hai giọng coi là MỘT nếu tâm cách nhau <= sàn qua-lượt
        nguong = max(qua) if qua else (max(trong) if trong else 0.0)
        cum: list = []
        for ma in mas:
            for c in cum:
                if cos_kc(tam[ma], tam[c[0]]) <= nguong:
                    c.append(ma)
                    break
            else:
                cum.append([ma])
        print(f"  NGƯỠNG GỘP = sàn cùng-giọng lớn nhất = {nguong:.4f}")
        print(f"  SỐ GIỌNG THẬT = {len(cum)} / {len(mas)} mã trong combo"
              f"  {cum}")
        kq["ecapa"]["nguong"] = nguong
        kq["ecapa"]["cum"] = cum
        kq["ecapa"]["so_giong_that"] = len(cum)

    # ═══ 3. GIÓNG HÀNG TRÊN CHÍNH FILE VỪA ĐỌC ═══
    print("\nGIÓNG HÀNG chạy trên CHÍNH file OmniVoice vừa đọc ra")
    if not gh.co_giong_hang():
        print("  máy chưa có bộ gióng hàng -> bỏ qua")
    else:
        for tieng, cau in (("vi", CAU_VI), ("en", CAU_EN)):
            wavs, txts = [], []
            for x in kq["doc"]:
                if x["tieng"] != tieng:
                    continue
                for p, c, t in zip(x["paths"], x["co_tieng"], cau):
                    if c:
                        wavs.append(p)
                        txts.append(t)
            if not wavs:
                continue
            ti: dict = {}
            moc = gh.giong_hang_loat(wavs, txts, lang=tieng, thong_tin=ti)
            co = sum(len(m) for m in moc)
            can = sum(len([w for w in recap._word_tokens(t) if w.strip()])
                      for t in txts)
            pt = 100.0 * co / max(1, can)
            rong = sum(1 for m in moc if not m)
            print(f"  {tieng}: PHỦ {co}/{can} = {pt:.1f}%"
                  f" · câu gióng không nổi {rong}/{len(wavs)}"
                  f" · {ti.get('thiet_bi')} · {ti.get('giay')}s")
            kq["phu"][tieng] = {"co": co, "can": can, "pt": round(pt, 1),
                                "rong": rong, "n": len(wavs),
                                "thiet_bi": ti.get("thiet_bi"),
                                "giay": ti.get("giay")}

    (RA / "do_giong.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + "=" * 74)
    print(f"Đã ghi {RA / 'do_giong.json'} · WAV giữ ở {TIENG}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
