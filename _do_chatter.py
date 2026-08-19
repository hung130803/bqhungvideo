"""ĐO CHATTERBOX (Resemble AI) — anh Hùng hỏi đích danh: *"chatter oke hơn à
bạn test ky đi hay lỗi thôi nếu có nhiều giọng hay"*.

**CÂU HỎI CHÍNH LÀ CÂU HỎI SỐ GIỌNG, VÀ NÓ PHẢI ĐO BẰNG ECAPA.** Chatterbox
**không có một giọng đặt tên nào** — nó là máy NHÂN BẢN: đưa mẫu tiếng nào thì
đọc bằng giọng đó. Nên "có bao nhiêu giọng" không đọc được từ tài liệu, phải
đo: đưa **8 mẫu KHÁC NHAU** vào rồi đếm xem ra **mấy giọng thật sự khác nhau**.

**ĐỐI CHỨNG ÂM LÀ BẮT BUỘC** — đây đúng chỗ lượt 4 của repo này đã sập với
Kani (*"quảng cáo 18 giọng, đo ra 2"*) và với chính đường nhân bản
(``use_ref_codes`` là **cờ bật/tắt** nên truyền đường dẫn vào chỉ làm nó thành
"bật", giọng ra vẫn y hệt giọng mặc định). Vì vậy có thêm một arm **KHÔNG đưa
mẫu nào** (``mac_dinh``): 8 bản sao mà đều bằng giọng mặc định -> nhân bản
KHÔNG chạy, dù bảng số trông đẹp tới đâu.
Ở Chatterbox tham số là ``audio_prompt_path=<đường dẫn>`` chứ không phải cờ
bool — nhưng vẫn phải đo, vì "chữ ký hàm trông đúng" chưa bao giờ là bằng
chứng.

**MẪU LẤY TỪ ĐÂU:** sinh bằng **8 giọng edge-tts khác nhau**. Ba cái lợi:
sạch giấy phép (không đụng giọng người thật của ai), tái lập được, và **có
SỰ THẬT ĐI KÈM** — biết chắc 8 mẫu là 8 giọng khác nhau, nên đo ra ít hơn 8
là lỗi của Chatterbox chứ không phải của nguyên liệu.

**THƯỚC — ĐỀU LÀ THƯỚC ĐÃ CÓ, KHÔNG CHẾ CÁI MỚI:**
  · số giọng thật -> **ECAPA-TDNN** (``_do_nguoi_noi_ecapa`` đã hiệu chuẩn:
    cùng giọng ~0,78 · khác giọng <= 0,31). MFCC/cao độ là thước HỎNG cho
    việc này (tự-ồn 97,7 > khoảng cách thật 48,4) — đừng dùng.
  · nhấn nhá -> ``_do_nhan_nha.f0_nua_cung`` (thước cổng 76).
  · khớp tiếng -> ``silencedetect`` (thước ĐỘC LẬP duy nhất; đo bằng chính máy
    nghe sinh ra mốc là "so nó với chính nó", đã ra 0,0 ms trên 1.587 mốc).
  · đọc sai chữ -> Groq chép ngược + WER trên TỪ.

Chạy: .venv\\Scripts\\python -u _do_chatter.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "_lib_giong"))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "_do_chatter"
FF = str(REPO / "bin" / "ffmpeg.exe")
PY_CB = REPO / "_giong_chatter" / "venv" / "Scripts" / "python.exe"
_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: 8 giọng edge-tts làm MẪU. Chọn trải nam/nữ + nhiều vùng cho khoảng cách
#: giọng thật sự xa nhau — mẫu na ná nhau thì phép đo "có mấy giọng" mất răng.
MAU_EDGE = [
    ("m0", "en-US-AndrewNeural"),      # nam Mỹ
    ("m1", "en-US-AriaNeural"),        # nữ Mỹ
    ("m2", "en-GB-RyanNeural"),        # nam Anh
    ("m3", "en-GB-SoniaNeural"),       # nữ Anh
    ("m4", "en-AU-WilliamNeural"),     # nam Úc
    ("m5", "en-IN-NeerjaNeural"),      # nữ Ấn
    ("m6", "en-US-AnaNeural"),         # nữ trẻ (cao độ rất khác)
    ("m7", "en-CA-LiamNeural"),        # nam Canada
]

#: Câu cho MẪU — dài để ECAPA có đủ tiếng (mẫu ngắn là nguồn nhiễu lớn nhất).
CAU_MAU = ("This is a short recording of my voice, used only as a reference "
           "sample for testing. I am reading a few sentences so that there "
           "is enough audio to work with.")

#: 4 câu ĐO — dùng ĐÚNG bộ câu tiếng Anh của thước nhấn nhá, không viết bộ
#: thứ hai (hai bộ câu là hai bảng số không so được với nhau).
from _do_nhan_nha_bang import CAU  # noqa: E402

CAU_DO = CAU["en"]

#: Câu tiếng Việt — để trả lời "nói tiếng Việt được không". Chatterbox khai
#: 23 thứ tiếng và KHÔNG có `vi`; vẫn phải thử thật chứ không đọc tài liệu rồi
#: kết luận (bản thân việc nó ném hay đọc ngọng là hai kết quả rất khác nhau).
CAU_VI = ("Một cơn bão chưa từng có trong lịch sử đang ập tới thành phố này.")


# ---------------------------------------------------------------------------
# TIẾN TRÌNH CON — Chatterbox (torch CUDA nằm ở `_giong_chatter/venv`)
# ---------------------------------------------------------------------------
MA_CB = r'''
import json, os, sys, time
job = json.load(open(sys.argv[1], encoding="utf-8"))
out = {"ok": False}
try:
    import numpy as np, torch, torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    t0 = time.time()
    m = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    t_nap = time.time() - t0

    ra = []
    for it in job["items"]:
        # DONG SEED: Chatterbox tu do thi cung cau cung tham so lech do dai
        # 33,7% giua cac luot (do o luot 6). Dong seed -> tien dinh 0,0%.
        torch.manual_seed(int(it.get("seed", 0)))
        t1 = time.time()
        kw = {}
        if it.get("ref"):
            kw["audio_prompt_path"] = it["ref"]
        wav = m.generate(it["text"], language_id=it["lang"], **kw)
        gi = time.time() - t1
        x = wav.detach().cpu()
        if x.dim() == 1:
            x = x[None]
        ta.save(it["out"], x, m.sr)
        ra.append({"i": it["i"], "out": it["out"], "gen": round(gi, 3),
                   "giay": round(x.shape[-1] / float(m.sr), 4)})
        print("BQP\t%d/%d" % (len(ra), len(job["items"])), flush=True)
    out = {"ok": True, "dev": dev, "nap": round(t_nap, 2), "sr": int(m.sr),
           "torch": torch.__version__, "ra": ra,
           "vram": (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                    if dev == "cuda" else 0.0)}
except Exception as e:
    out = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
print("BQJSON\t" + json.dumps(out), flush=True)
'''


def chay_cb(items: list[dict], han: int = 5400) -> dict:
    """Gọi Chatterbox ở TIẾN TRÌNH RIÊNG. Luôn trả `_sandbox`.

    `_sandbox` PHẢI có ở MỌI đường ra — nơi gọi dọn bằng
    `_don(Path(ket.get("_sandbox") or ""))`, mà `Path("")` là **thư mục đang
    làm việc** (commit `b5bd003` đã xoá sạch cây mã đúng vì lỗ này).
    """
    SAN.mkdir(parents=True, exist_ok=True)
    sb = SAN / f"_job_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sb.mkdir(parents=True, exist_ok=True)
    run = sb / "runner.py"
    run.write_text(MA_CB, encoding="utf-8")
    job = sb / "job.json"
    job.write_text(json.dumps({"items": items}, ensure_ascii=False),
                   encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run([str(PY_CB), "-u", str(run), str(job)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=han,
                           creationflags=_NO_WIN)
    except subprocess.TimeoutExpired:
        return {"ok": False, "loi": f"quá giờ {han}s", "_sandbox": str(sb)}
    for d in (p.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            k = json.loads(d[7:])
            k["_sandbox"] = str(sb)
            return k
    return {"ok": False, "_sandbox": str(sb),
            "loi": f"rc={p.returncode} {(p.stderr or '')[-600:]}"}


# ---------------------------------------------------------------------------
# ECAPA — dùng lại runner của `_do_nguoi_noi_ecapa`, chạy bằng python Chatterbox
# ---------------------------------------------------------------------------
MA_ECAPA = r'''
import json, sys
job = json.load(open(sys.argv[1], encoding="utf-8"))
import numpy as np, torch, soundfile as sf
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy
dev = "cuda" if torch.cuda.is_available() else "cpu"
# BAY WINDOWS: speechbrain mac dinh SYMLINK tu cache HF sang savedir ->
# WinError 1314 vi may khong bat Developer Mode. Phai ep COPY.
m = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb", savedir=job["savedir"],
    run_opts={"device": dev}, local_strategy=LocalStrategy.COPY)
def emb(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != 16000:
        raise RuntimeError("sai tan so %d" % sr)
    if x.shape[0] < 1600:
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


def chay_ecapa(files: dict[str, str]) -> dict:
    SAN.mkdir(parents=True, exist_ok=True)
    run = SAN / "_ecapa_runner.py"
    run.write_text(MA_ECAPA, encoding="utf-8")
    job = SAN / "_ecapa_job.json"
    job.write_text(json.dumps({"files": files,
                               "savedir": str(SAN / "ecapa_model")}),
                   encoding="utf-8")
    p = subprocess.run([str(PY_CB), "-u", str(run), str(job)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NO_WIN, timeout=3600)
    for d in (p.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            return json.loads(d[7:])
    raise RuntimeError(f"ECAPA rc={p.returncode}\n{(p.stderr or '')[-1200:]}")


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------
def ra_wav16(src: Path, dst: Path) -> bool:
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-vn",
                        "-ac", "1", "-ar", "16000", str(dst)],
                       capture_output=True, creationflags=_NO_WIN, timeout=300)
    # BẪY: ffmpeg mã 0 + file 0 KiB -> phải kiểm KÍCH THƯỚC, không tin mã thoát
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def moc_phat_tieng(wav: Path) -> float:
    """Giây đầu tiên THẬT SỰ có tiếng (`silencedetect`) — thước ĐỘC LẬP."""
    r = subprocess.run(
        [FF, "-v", "info", "-i", str(wav), "-af",
         "silencedetect=noise=-45dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=180)
    txt = (r.stderr or "")
    if "silence_end:" in txt:
        for d in txt.splitlines():
            if "silence_end:" in d:
                try:
                    return float(d.split("silence_end:")[1].split()[0])
                except (IndexError, ValueError):
                    pass
    return 0.0


def cos(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def sinh_mau() -> dict[str, str]:
    """8 mẫu tiếng bằng 8 giọng edge-tts -> wav 16 kHz. Trả {khoá: đường dẫn}."""
    import asyncio

    from app.core import dubbing

    d = SAN / "mau"
    d.mkdir(parents=True, exist_ok=True)
    ra: dict[str, str] = {}
    for k, v in MAU_EDGE:
        w = d / f"{k}.wav"
        if w.exists() and w.stat().st_size > 4000:
            ra[k] = str(w)
            continue
        mp3 = d / f"{k}.mp3"
        ok = asyncio.run(dubbing._synth_all([CAU_MAU], v, [str(mp3)]))
        if ok and ok[0] and ra_wav16(mp3, w):
            ra[k] = str(w)
        else:
            print(f"  MẪU HỎNG: {k} ({v})")
    return ra


def chep_nguoc(wav: str) -> str:
    """Groq chép ngược chính file vừa đọc -> chuỗi chữ. "" nếu hỏng."""
    try:
        from app.core import transcribe as TR
        return str(TR.transcribe(str(wav), language="en").get("text") or "")
    except Exception as e:                                    # noqa: BLE001
        print(f"  chép ngược hỏng: {type(e).__name__}: {e}")
        return ""


def wer(goc: str, nghe: str) -> tuple[float, int]:
    """Tỉ lệ sai TỪ (Levenshtein trên TỪ). Trả (tỉ lệ, số từ gốc)."""
    import re
    def chuan(s):
        s = re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\s]", " ", (s or "").lower())
        return re.sub(r"\s+", " ", s).strip().split()
    a, b = chuan(goc), chuan(nghe)
    if not a:
        return 0.0, 0
    tr = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        moi = [i]
        for j in range(1, len(b) + 1):
            moi.append(min(tr[j] + 1, moi[-1] + 1,
                           tr[j - 1] + (a[i - 1] != b[j - 1])))
        tr = moi
    return tr[len(b)] / len(a), len(a)


def main() -> int:
    import statistics as st

    from _do_nhan_nha import f0_nua_cung

    SAN.mkdir(parents=True, exist_ok=True)
    t_all = time.monotonic()
    print("=" * 74)
    print("ĐO CHATTERBOX — 8 mẫu edge-tts + 1 arm ĐỐI CHỨNG ÂM (không mẫu)")
    print("=" * 74)

    print("\n[1/5] Sinh 8 mẫu tiếng bằng edge-tts...")
    mau = sinh_mau()
    print(f"  có {len(mau)}/8 mẫu")
    if len(mau) < 4:
        print("  KHÔNG ĐỦ MẪU -> dừng (đo với <4 mẫu là vô nghĩa)")
        return 2

    print("\n[2/5] Chatterbox đọc 4 câu cho MỖI arm (8 bản sao + 1 mặc định)...")
    d_ra = SAN / "ra"
    d_ra.mkdir(parents=True, exist_ok=True)
    items, ban_do = [], {}
    n = 0
    for k in list(mau) + ["mac_dinh"]:
        for j, t in enumerate(CAU_DO):
            out = d_ra / f"{k}_c{j}.wav"
            ban_do[n] = (k, j, str(out))
            items.append({"i": n, "text": t, "lang": "en", "out": str(out),
                          "ref": ("" if k == "mac_dinh" else mau[k]),
                          "seed": 1234})
            n += 1
    # tiếng VIỆT: chữ Việt nhưng language_id='en' (Chatterbox KHÔNG có 'vi')
    out_vi = d_ra / "vi_test.wav"
    items.append({"i": n, "text": CAU_VI, "lang": "en", "out": str(out_vi),
                  "ref": mau[list(mau)[0]], "seed": 1234})
    i_vi = n

    # ═══ ĐỐI CHỨNG ÂM PHẢI CHẠY Ở TIẾN TRÌNH RIÊNG — LỖI THẬT ĐÃ SẬP ═══
    # Chatterbox CẤT `self.conds` trên chính đối tượng model: gọi `generate()`
    # KHÔNG kèm `audio_prompt_path` thì nó **dùng lại mẫu của lượt TRƯỚC**,
    # không quay về giọng mặc định. Lượt đo đầu xếp `mac_dinh` ở CUỐI nên nó
    # thừa hưởng mẫu m7 -> đo ra `cos(m7, mặc định) = 1,000`, tức đối chứng âm
    # KHÔNG hề là đối chứng. Bảng vẫn đẹp, không một dòng báo.
    # Nay arm `mac_dinh` chạy bằng MỘT LƯỢT GỌI RIÊNG (model mới tinh, chưa
    # từng thấy mẫu nào). Đây cũng là lý do `giong_chatter._chay` chỉ nhận
    # ĐÚNG MỘT `ref` cho cả loạt và luôn sinh tiến trình mới.
    md = [it for it in items if not it["ref"]]
    khac = [it for it in items if it["ref"]]
    for nhom in (md, khac):
        can = [it for it in nhom
               if not (Path(it["out"]).exists()
                       and Path(it["out"]).stat().st_size > 4000)]
        if not can:
            continue
        kq = chay_cb(can)
        if not kq.get("ok"):
            print(f"  CHATTERBOX HỎNG: {kq.get('loi')}")
            return 1
        print(f"  thiết bị {kq['dev']} · torch {kq['torch']} · "
              f"nạp model {kq['nap']}s · VRAM {kq.get('vram')} GiB · "
              f"{len(kq['ra'])} file")
        gen = [r["gen"] for r in kq["ra"]]
        gi = [r["giay"] for r in kq["ra"]]
        if gen:
            print(f"  tốc độ: {sum(gi)/max(1e-9,sum(gen)):.2f}x thời gian thật "
                  f"(bỏ lượt hâm máy: "
                  f"{sum(gi[1:])/max(1e-9,sum(gen[1:])):.2f}x)")
        (SAN / "cb_raw.json").write_text(
            json.dumps(kq, ensure_ascii=False), encoding="utf-8")

    print("\n[3/5] ECAPA — có mấy giọng THẬT SỰ khác nhau?")
    # ECAPA đòi 16 kHz; Chatterbox trả 24 kHz -> phải HẠ TẦN SỐ TRƯỚC.
    # Bỏ bước này thì runner ném "sai tần số" cho TỪNG file, `emb` rỗng, và
    # bảng ra TRỐNG TRƠN — trông y hệt một phép đo "không tách được giọng".
    # Đúng họ bẫy "phép đo hỏng phát chứng nhận" (`astats` cổng 53).
    d16 = SAN / "e16"
    d16.mkdir(parents=True, exist_ok=True)
    files = {f"ref_{k}": v for k, v in mau.items()}
    for i, (k, j, p) in ban_do.items():
        if not Path(p).exists():
            continue
        w = d16 / f"{k}_{j}.wav"
        if (w.exists() and w.stat().st_size > 4000) or ra_wav16(Path(p), w):
            files[f"{k}#{j}"] = str(w)
    e = chay_ecapa(files)
    emb = {k: v for k, v in e["emb"].items() if v}
    arms = list(mau) + ["mac_dinh"]
    tb = {}
    for a in arms:
        vs = [emb[f"{a}#{j}"] for j in range(len(CAU_DO))
              if f"{a}#{j}" in emb]
        if not vs:
            continue
        m = [sum(c) / len(vs) for c in zip(*vs)]
        nn = sum(x * x for x in m) ** 0.5
        tb[a] = [x / nn for x in m] if nn else None
    tb = {k: v for k, v in tb.items() if v}

    print(f"  {'arm':10s} cos(bản sao, MẪU của nó)   cos(bản sao, MẶC ĐỊNH)")
    giong_mau, giong_md = [], []
    for a in arms:
        if a == "mac_dinh" or a not in tb:
            continue
        cm = cos(tb[a], emb[f"ref_{a}"]) if f"ref_{a}" in emb else float("nan")
        cd = cos(tb[a], tb["mac_dinh"]) if "mac_dinh" in tb else float("nan")
        giong_mau.append(cm)
        giong_md.append(cd)
        print(f"  {a:10s} {cm:22.3f} {cd:22.3f}")

    cap = []
    ks = [a for a in arms if a in tb and a != "mac_dinh"]
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            cap.append(cos(tb[ks[i]], tb[ks[j]]))
    NG_KHAC = 0.31          # hiệu chuẩn `_do_nguoi_noi_ecapa`: khác giọng <=0,31
    NG_CUNG = 0.60          # giữa 0,31 và 0,78 — nghi ngờ
    rieng = 1
    da = [ks[0]] if ks else []
    for a in ks[1:]:
        if all(cos(tb[a], tb[b]) <= NG_CUNG for b in da):
            da.append(a)
    if not cap or not giong_mau:
        print("  ECAPA KHÔNG RA SỐ NÀO. Bảng trống KHÔNG phải kết luận "
              "'không tách được giọng' — nó là PHÉP ĐO HỎNG, dừng ở đây.")
        print(f"  (lấy được {len(emb)}/{len(files)} embed)")
        return 1
    print(f"\n  cặp bản-sao-khác-nhau: TB {st.mean(cap):.3f} · "
          f"max {max(cap):.3f} · min {min(cap):.3f}  (ngưỡng khác giọng "
          f"<= {NG_KHAC})")
    print(f"  cos(bản sao, mẫu của nó): TB {st.mean(giong_mau):.3f}")
    print(f"  cos(bản sao, MẶC ĐỊNH):   TB {st.mean(giong_md):.3f}"
          f"   <- ĐỐI CHỨNG ÂM")
    print(f"  => SỐ GIỌNG THẬT (gộp cụm ở {NG_CUNG}): "
          f"{len(da)}/{len(ks)} mẫu đưa vào")

    print("\n[4/5] Nhấn nhá (thước cổng 76) + mốc phát tiếng (silencedetect)")
    nn_arm, tre = {}, []
    for a in arms:
        tat = []
        for j in range(len(CAU_DO)):
            p = Path(d_ra / f"{a}_c{j}.wav")
            if not p.exists():
                continue
            w = SAN / "tmp16.wav"
            if ra_wav16(p, w):
                tat.extend(f0_nua_cung(w))
                if a != "mac_dinh":
                    tre.append(moc_phat_tieng(w))
        if len(tat) >= 50:
            nn_arm[a] = round(st.pstdev(tat), 2)
    for a, v in sorted(nn_arm.items(), key=lambda kv: -kv[1]):
        print(f"  {a:10s} nhấn nhá {v:.2f}")
    if nn_arm:
        xs = sorted(nn_arm.values())
        print(f"  TRẢI {xs[-1]-xs[0]:.2f} (thấp {xs[0]:.2f} · cao {xs[-1]:.2f})")
    if tre:
        print(f"  lề IM đầu file: TB {1000*st.mean(tre):.0f} ms · "
              f"max {1000*max(tre):.0f} ms")

    print("\n[5/5] Đọc sai chữ (Groq chép ngược) + tiếng Việt")
    sai, tong = 0.0, 0
    for a in list(mau)[:3] + ["mac_dinh"]:
        for j, t in enumerate(CAU_DO):
            p = d_ra / f"{a}_c{j}.wav"
            if not p.exists():
                continue
            r, nw = wer(t, chep_nguoc(str(p)))
            sai += r * nw
            tong += nw
    print(f"  ĐỌC SAI CHỮ (tiếng Anh): {100*sai/max(1,tong):.1f}% "
          f"trên {tong} từ")
    if Path(out_vi).exists():
        nghe = chep_nguoc(str(out_vi))
        r, nw = wer(CAU_VI, nghe)
        print(f"  TIẾNG VIỆT: sai {100*r:.1f}% / {nw} từ")
        print(f"    gửi vào : {CAU_VI}")
        print(f"    đọc ra  : {nghe[:200]}")

    print(f"\nXONG · {time.monotonic()-t_all:.0f} giây · sân đo: {SAN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
