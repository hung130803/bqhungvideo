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
def do_wav(p: str, _thu_lai: bool = True) -> dict:
    """Độ dài + RMS + đỉnh, đọc THẲNG mẫu. File 0 byte thì mọi số ra 0.

    **BẪY ĐÃ SẬP 19/08/2026 — ĐUÔI FILE NÓI DỐI.** `dubbing._synth_all` ghi
    ra `.wav` nhưng RUỘT LÀ MP3 (edge-tts trả mp3, app để ffmpeg lo ở bước
    sau). `wave.open` ném -> hàm này trả 0,0 giây -> arm ĐỐI CHỨNG đo ra
    **0/3 câu có tiếng** trong khi `_synth_all` báo `[True, True, True]`.
    Nếu tin con số đó thì kết luận sẽ là *"edge-tts đọc không ra"* — sai
    hoàn toàn, và tệ hơn: mất luôn cái SÀN dùng để đọc phần ECAPA.
    Nay `wave` không đọc được thì giải mã bằng ffmpeg rồi đo lại.
    """
    try:
        with wave.open(str(p), "rb") as w:
            n, fr, sw, ch = (w.getnframes(), w.getframerate(),
                             w.getsampwidth(), w.getnchannels())
            raw = w.readframes(n)
    except Exception:                                        # noqa: BLE001
        try:
            co = Path(p).stat().st_size
        except OSError:
            co = 0
        if _thu_lai and co > 1024:
            tam = Path(p).with_suffix(".pcm16.wav")
            if sang_16k(str(p), str(tam)):
                d = do_wav(str(tam), _thu_lai=False)
                d["qua_ffmpeg"] = True
                return d
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


def doc(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, sr


def emb(x):
    with torch.no_grad():
        e = m.encode_batch(torch.from_numpy(x)[None].to(dev))
    v = e.squeeze().detach().cpu().numpy().astype(float)
    n = float(np.linalg.norm(v))
    return (v / n).tolist() if n > 0 else None


def f0(x, sr):
    """Cao do trung vi (Hz) bang tu tuong quan qua FFT. 0 = khong do duoc.

    Day la thuoc DOC LAP voi ECAPA va no tra loi mot cau KHAC: khong phai
    "co phai cung mot nguoi noi khong" ma "cai giong nay co TRAM hon cai kia
    khong" — dung thu ma cau ta cua model hua (low pitch / high pitch).
    """
    w, h = int(0.04 * sr), int(0.01 * sr)
    lo, hi = int(sr / 400.0), int(sr / 60.0)
    ra = []
    n = 1
    while n < 2 * w:
        n *= 2
    for i in range(0, max(0, len(x) - w), h):
        f = x[i:i + w].astype(np.float64)
        f -= f.mean()
        if np.sqrt((f * f).mean()) < 0.01:
            continue
        S = np.fft.rfft(f, n)
        r = np.fft.irfft(S * np.conj(S), n)[:w]
        if r[0] <= 0 or hi <= lo or hi > len(r):
            continue
        k = int(np.argmax(r[lo:hi])) + lo
        if r[k] / r[0] < 0.35:
            continue
        ra.append(sr / float(k))
    return float(np.median(ra)) if ra else 0.0


ra_e, ra_f = {}, {}
for k, p in job["files"].items():
    try:
        x, sr = doc(p)
        if sr != 16000 or x.shape[0] < 1600:
            raise RuntimeError("sai tan so %d / qua ngan" % sr)
        ra_e[k] = emb(x)
        ra_f[k] = round(f0(x, sr), 2)
    except Exception as ex:
        ra_e[k] = None
        ra_f[k] = 0.0
        print("LOI %s: %s" % (k, ex), file=sys.stderr)
print("BQJSON\t" + json.dumps({"dev": dev, "emb": ra_e, "f0": ra_f}))
'''


def ecapa(files: dict) -> tuple:
    """({khoá: vector đơn vị}, {khoá: F0}). TIẾN TRÌNH RIÊNG (torch sau Qt)."""
    if not VENV_ECAPA.exists():
        print(f"  KHÔNG có môi trường ECAPA ({VENV_ECAPA}) -> bỏ phần giọng")
        return {}, {}
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
        return {}, {}
    for d in (r.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            k = json.loads(d.split("\t", 1)[1])
            print(f"  ECAPA chạy trên: {k.get('dev')}")
            return ({a: b for a, b in (k.get("emb") or {}).items() if b},
                    k.get("f0") or {})
    print("  ECAPA hỏng:", (r.stderr or r.stdout or "")[-400:])
    return {}, {}


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
    # `--lai` = dùng lại ĐÚNG bộ WAV cũ. Bắt buộc phải có: OmniVoice KHÔNG
    # TIỀN ĐỊNH (cùng hàm, cùng corpus, đo ra 41,8% rồi 99,4% chỉ vì khác mẻ
    # tiếng), nên sửa PHÉP ĐO rồi chạy lại trên mẻ MỚI là trộn hai thay đổi
    # vào nhau, không đọc ra được cái nào gây ra chênh lệch.
    lai = "--lai" in sys.argv
    if lai:
        print("  (--lai: dùng lại bộ WAV cũ, KHÔNG đọc lại)")

    # ═══ 1. ĐỌC THẬT ═══
    for tieng, cau in (("vi", CAU_VI), ("en", CAU_EN)):
        for ma in dsg:
            ten = ma.replace(":", "_")
            paths = [str(TIENG / tieng / ten / f"c{i}.wav")
                     for i in range(len(cau))]
            t0 = time.time()
            if lai and all(Path(p).exists() for p in paths):
                ok = [True] * len(cau)
            else:
                ok, _moc = gn.doc_loat(cau, paths, ma, lang=tieng,
                                       lay_moc=False, han_giay=1800)
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

    # ═══ 1b. ARM ĐỐI CHỨNG: edge-tts ═══
    # BẮT BUỘC, KHÔNG PHẢI TRANG TRÍ. Nếu ECAPA nói "5 mã OmniVoice không
    # phải 5 người nói", câu hỏi tiếp theo LUÔN LÀ *"hay là thước hỏng trên
    # tiếng máy đọc?"*. edge-tts chắc chắn là MỘT người nói ổn định (một bộ
    # trọng số, một giọng), nên nó là SÀN: thước nào không tách nổi edge-tts
    # khỏi chính nó thì mọi con số phía trên là con số về nhiễu.
    # (Đúng bài học cổng 71: GPU vs CPU −19 dB chỉ đọc được khi biết CPU vs
    # CPU cũng −19 dB.)
    import asyncio as _aio
    from app.core import dubbing as _db
    for tieng, cau, giong in (("vi", CAU_VI, "vi-VN-HoaiMyNeural"),
                              ("en", CAU_EN, "en-US-AriaNeural")):
        paths = [str(TIENG / tieng / "edge" / f"c{i}.wav")
                 for i in range(len(cau))]
        # `_synth_all` KHÔNG tự tạo thư mục cha (khác `_doc_omnivoice`) ->
        # thiếu dòng này thì nó trả toàn False mà KHÔNG ném, và arm đối chứng
        # ra "0/3 câu" trông y hệt "edge-tts đọc không được".
        Path(paths[0]).parent.mkdir(parents=True, exist_ok=True)
        if lai and all(Path(p).exists() for p in paths):
            okd = [True] * len(cau)
        else:
            try:
                okd = _aio.run(_db._synth_all(cau, giong, paths, lang=tieng))
            except Exception as e:                           # noqa: BLE001
                print(f"  edge-tts {tieng} hỏng: {e}")
                okd = [False] * len(cau)
        do = [do_wav(p) for p in paths]
        ct = [bool(o) and d["giay"] > 0.3 and d["rms"] > 0.005
              for o, d in zip(okd, do)]
        kq["doc"].append({"tieng": tieng, "ma": "edge", "giay": 0.0,
                          "ok": okd, "do": do, "co_tieng": ct,
                          "paths": paths})
        print(f"  {tieng} edge (ĐỐI CHỨNG) {sum(ct)}/{len(cau)} câu CÓ TIẾNG")

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
    emb, tanso = ecapa(files) if files else ({}, {})
    kq["ecapa"]["so_mau"] = len(emb)
    kq["ecapa"]["f0"] = tanso

    if tanso:
        print("\n  CAO ĐỘ (F0 trung vị, Hz) — thước ĐỘC LẬP với ECAPA, trả "
              "lời câu KHÁC:")
        theo_f: dict = {}
        for k, v in tanso.items():
            if v > 0:
                theo_f.setdefault(k.split("|")[1], []).append(v)
        for m, ten in ([(a, c) for a, _b, c in gn.GIONG_OV]
                       + [("edge", "edge-tts (ĐỐI CHỨNG)")]):
            vs = sorted(theo_f.get(m, []))
            if not vs:
                continue
            tb = sum(vs) / len(vs)
            print(f"    {m:12s} {ten:22s} TB {tb:6.1f} Hz "
                  f"· dải {vs[0]:5.1f}–{vs[-1]:5.1f} · n={len(vs)}")
        kq["ecapa"]["f0_theo_giong"] = {m: theo_f.get(m, []) for m in theo_f}

    if emb:
        theo: dict = {}
        for k, v in emb.items():
            t, ma, _i = k.split("|")
            theo.setdefault(ma, {}).setdefault(t, []).append(v)

        trong, qua, giua = [], [], []
        tr_edge, qua_edge = [], []
        for ma, d in theo.items():
            t1 = tr_edge if ma == "edge" else trong
            t2 = qua_edge if ma == "edge" else qua
            for _t, vs in d.items():
                for a in range(len(vs)):
                    for b in range(a + 1, len(vs)):
                        t1.append(cos_kc(vs[a], vs[b]))
            if "vi" in d and "en" in d:
                for a in d["vi"]:
                    for b in d["en"]:
                        t2.append(cos_kc(a, b))
        mas = sorted(m for m in theo if m != "edge")
        print(f"  ĐỐI CHỨNG edge-tts / cùng lượt : {tk(tr_edge)}")
        print(f"  ĐỐI CHỨNG edge-tts / khác lượt : {tk(qua_edge)}"
              "   (khác lượt = khác GIỌNG edge, không phải sàn)")
        kq["ecapa"]["edge_trong"] = tr_edge
        kq["ecapa"]["edge_qua"] = qua_edge
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

        # ── AUC: THƯỚC KHÔNG THIÊN VỊ ────────────────────────────────────
        # Đây là câu hỏi đúng và là con số đáng tin nhất trong cả khối này,
        # vì nó KHÔNG dùng tâm nào cả nên không dính bias của phép gán nhãn:
        # lấy MỌI cặp cùng-giọng và MỌI cặp khác-giọng, hỏi "bốc ngẫu nhiên
        # một cặp mỗi loại thì cặp cùng-giọng có gần nhau hơn không".
        #   1,00 = tách hoàn hảo · 0,50 = KHÔNG phân biệt được gì
        cung = trong + qua
        if cung and giua:
            thang = sum((1.0 if a < b else 0.5 if a == b else 0.0)
                        for a in cung for b in giua)
            auc = thang / (len(cung) * len(giua))
            print(f"  AUC cùng-giọng vs khác-giọng = **{auc:.3f}** "
                  f"(1,00 = tách hoàn hảo · 0,50 = không phân biệt được)")
            kq["ecapa"]["auc"] = auc

        # ── CHỒNG LẤN: hai phân bố có TÁCH RỜI nhau không ────────────────
        # Đây mới là câu hỏi đúng. Trung bình đẹp mà hai phân bố chồng nhau
        # thì ECAPA KHÔNG phân biệt được — và mọi con số rút ra sau đó là con
        # số về NHIỄU. (Cùng bài học "GPU vs CPU −19 dB, mà CPU vs CPU cũng
        # −19 dB" của cổng 71: phải có sàn mới đọc được.)
        moc_t = sorted(trong)[len(trong) // 2] if trong else 0.0
        gan_hon = sum(1 for g in giua if g < moc_t)
        print(f"  CHỒNG LẤN: {gan_hon}/{len(giua)} = "
              f"{100.0 * gan_hon / max(1, len(giua)):.1f}% cặp KHÁC GIỌNG còn "
              f"gần nhau hơn trung vị cặp CÙNG GIỌNG ({moc_t:.4f})")
        kq["ecapa"]["chong_lan"] = [gan_hon, len(giua), moc_t]

        # ── CHỌN X RA X: TÂM BỎ-CHÍNH-MÌNH (leave-one-out) ───────────────
        # BẢN ĐẦU CỦA PHÉP ĐO NÀY SAI VÀ TỰ RA SỐ ĐẸP (30/30): tâm mỗi giọng
        # tính từ 6 mẫu, TRONG ĐÓ CÓ CHÍNH MẪU ĐANG CHẤM -> mỗi mẫu góp 1/6
        # vào tâm của chính nó, tức bài thi có sẵn đáp án. Đúng họ "phép đo
        # phát chứng nhận cho thứ chưa được kiểm" (`astats` cổng 53).
        def _tam(vs: list) -> list:
            n = len(vs)
            c = [sum(v[i] for v in vs) / n for i in range(len(vs[0]))]
            nn = math.sqrt(sum(x * x for x in c)) or 1.0
            return [x / nn for x in c]

        goi_mau: dict = {}
        for k, v in emb.items():
            if k.split("|")[1] == "edge":
                continue                    # arm đối chứng, không phải combo
            goi_mau.setdefault(k.split("|")[1], []).append((k, v))
        tam = {m: _tam([v for _k, v in vs]) for m, vs in goi_mau.items()}

        dung = 0
        tong_m = 0
        nham: list = []
        for ma, vs in goi_mau.items():
            for k, v in vs:
                con = [y for kk, y in vs if kk != k]
                if not con:
                    continue
                tam_loo = dict(tam)
                tam_loo[ma] = _tam(con)
                gan = min(tam_loo, key=lambda m: cos_kc(v, tam_loo[m]))
                tong_m += 1
                if gan == ma:
                    dung += 1
                else:
                    nham.append([k, gan])
        # Số này LỆCH XUỐNG và phải nói ra: n=6/giọng, phương sai nội lớp rất
        # lớn, nên bỏ chính mẫu ra khỏi tâm là kéo tâm chạy xa hẳn -> phạt
        # đúng lớp ĐÚNG. Bản KHÔNG bỏ-chính-mình thì lệch LÊN (ra 30/30 =
        # 100%, vì mỗi mẫu góp 1/6 vào đáp án của chính nó). **Hai số cùng
        # sai, ngược chiều nhau — con số đáng tin là AUC ở trên**, nó không
        # dùng tâm nào cả.
        print(f"  CHỌN X RA X (tâm BỎ-CHÍNH-MÌNH): {dung}/{tong_m} = "
              f"{100.0 * dung / max(1, tong_m):.1f}% mẫu gần tâm giọng MÌNH "
              f"nhất (bốc ngẫu nhiên = {100.0 / max(1, len(goi_mau)):.0f}%)")
        if nham:
            print(f"    nhầm: {[f'{a}->{b}' for a, b in nham[:6]]}")
        kq["ecapa"]["chon_dung_loo"] = [dung, tong_m]
        kq["ecapa"]["nham"] = nham

        # ── SỐ GIỌNG THẬT ────────────────────────────────────────────────
        # Ngưỡng gộp = TRUNG VỊ sàn cùng-giọng-khác-lượt, KHÔNG phải max: lấy
        # max là lấy đúng cái đuôi nhiễu tệ nhất rồi tuyên bố mọi thứ là một
        # giọng — bản đầu ra "1/5" chính vì thế, và đó là số của NGƯỠNG chứ
        # không phải của MODEL.
        nen = qua or trong
        nguong = sorted(nen)[len(nen) // 2] if nen else 0.0
        cum: list = []
        for ma in sorted(tam):
            for c in cum:
                if cos_kc(tam[ma], tam[c[0]]) <= nguong:
                    c.append(ma)
                    break
            else:
                cum.append([ma])
        kc_tam = [cos_kc(tam[a], tam[b]) for i, a in enumerate(sorted(tam))
                  for b in sorted(tam)[i + 1:]]
        print(f"  KHOẢNG CÁCH GIỮA CÁC TÂM: {tk(kc_tam)}")
        print(f"  NGƯỠNG GỘP = trung vị sàn cùng-giọng = {nguong:.4f}")
        print(f"  SỐ GIỌNG THẬT = {len(cum)} / {len(mas)} mã trong combo"
              f"  {cum}")
        kq["ecapa"].update({"nguong": nguong, "cum": cum,
                            "kc_tam": kc_tam, "so_giong_that": len(cum),
                            "tam_kc_min": min(kc_tam) if kc_tam else 0.0})
        kq["ecapa"]["emb"] = emb

    # ═══ 3. GIÓNG HÀNG TRÊN CHÍNH FILE VỪA ĐỌC ═══
    print("\nGIÓNG HÀNG chạy trên CHÍNH file OmniVoice vừa đọc ra")
    if not gh.co_giong_hang():
        print("  máy chưa có bộ gióng hàng -> bỏ qua")
    else:
        for arm in ("ov", "edge"):
            for tieng, cau in (("vi", CAU_VI), ("en", CAU_EN)):
                wavs, txts = [], []
                for x in kq["doc"]:
                    la_edge = x["ma"] == "edge"
                    if x["tieng"] != tieng or la_edge != (arm == "edge"):
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
                print(f"  {arm:4s} {tieng}: PHỦ {co}/{can} = {pt:.1f}%"
                      f" · câu gióng không nổi {rong}/{len(wavs)}"
                      f" · {ti.get('thiet_bi')} · {ti.get('giay')}s")
                kq["phu"][f"{arm}_{tieng}"] = {
                    "co": co, "can": can, "pt": round(pt, 1), "rong": rong,
                    "n": len(wavs), "thiet_bi": ti.get("thiet_bi"),
                    "giay": ti.get("giay")}

    (RA / "do_giong.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n" + "=" * 74)
    print(f"Đã ghi {RA / 'do_giong.json'} · WAV giữ ở {TIENG}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
