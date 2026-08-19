# -*- coding: utf-8 -*-
"""ĐO DỨT ĐIỂM: giọng `Adam` của VieNeu CÓ PHẢI giọng Adam của ElevenLabs không.

Chạy: .venv\\Scripts\\python -u _do_adam.py

═══════════════════════════════════════════════════════════════════════════
VÌ SAO PHẢI ĐO, KHÔNG TRANH LUẬN
═══════════════════════════════════════════════════════════════════════════
`giong_vieneu._NGO_NGUON` chặn giọng thứ 20 (`Adam`) khỏi combo với bằng chứng
DUY NHẤT là **cái tên trùng** một giọng dựng sẵn thương mại của ElevenLabs.
Nhưng cùng file đó kết luận về `Ngọc Huyền`: *"trùng tên KHÔNG phải bằng
chứng"*. **Cùng một lập luận, áp hai kiểu** — đó là mâu thuẫn, không phải
thận trọng. Anh Hùng nói đúng: "Adam" cũng là tên người rất phổ biến.

Máy có **5 key ElevenLabs**, tức lấy được giọng Adam THẬT. Vậy thì đo.

═══════════════════════════════════════════════════════════════════════════
THƯỚC: ECAPA-TDNN — VÀ VÌ SAO KHÔNG PHẢI MFCC/CAO ĐỘ
═══════════════════════════════════════════════════════════════════════════
MFCC/cao độ là thước **HỎNG** cho câu hỏi này: đo được tự-ồn **97,7** trong
khi khoảng cách thật giữa hai giọng khác nhau chỉ **48,4** — thước ồn hơn thứ
nó đo thì mọi con số nó phát ra là số rác.

ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`) là **HỆ THỨ BA**: không phải
ElevenLabs, không phải VieNeu. Đây là điều kiện tiên quyết — đo giọng bằng
chính hệ sinh ra nó là "so nó với chính nó" (đã ra 0,0 ms hoàn hảo trên 1.587
mốc một lần rồi).

MỐC ĐỌC KẾT QUẢ (đã hiệu chuẩn trong repo, dùng lại — KHÔNG đặt mốc mới):
    hai giọng KHÁC người          ~ **0,19**   (`_do_nguoi_noi_ecapa`: <= 0,31)
    bản sao so với chính mẫu       ~ **0,81-0,83**
    cặp edge-tts dính nhau nhất    **0,759**   (`en-GB-Ryan` – `en-CA-Liam`)

═══════════════════════════════════════════════════════════════════════════
ĐỐI CHỨNG LÀ BẮT BUỘC — THIẾU THÌ CON SỐ VÔ NGHĨA
═══════════════════════════════════════════════════════════════════════════
Một con số cos đứng một mình không nói gì: không biết 0,45 là "giống" hay
"khác" nếu không biết thước hôm nay đang đo ra bao nhiêu cho hai đầu đã biết.

  · **ĐỐI CHỨNG DƯƠNG** — ElevenLabs Adam lượt 1 so lượt 2 -> phải CAO.
  · **ĐỐI CHỨNG ÂM**   — `vn:Adam` so giọng ElevenLabs KHÁC -> phải THẤP.
    Lấy **HAI** giọng: `Rachel` (nữ — dễ) và `Josh` (NAM MỸ — khó, đây mới là
    sàn thật cho câu hỏi "hai người đàn ông khác nhau thì bao nhiêu").

**BẪY `cos = 1,000` — ĐÃ SẬP MỘT LẦN, ĐÂY LÀ CHỖ NÓ CHUI VÀO LẦN NÀY:**
`dubbing._eleven_tts` có **CACHE theo `sha1(voice|model|text)`** — gọi lại
CÙNG một câu là nó trả lại **ĐÚNG FILE CŨ, không gọi API**. Nếu đối chứng
dương dùng cùng câu cho cả 2 lượt thì hai file GIỐNG TỪNG BYTE -> cos =
**1,000 chính xác** -> "đối chứng dương ĐẠT" trong khi nó chưa đo gì cả.
Nên: mỗi lượt dùng **NHÓM CÂU KHÁC NHAU**. ECAPA là thước speaker
text-independent nên khác nội dung là ĐÚNG cách dùng, không phải nhân nhượng.
Ca 0 (`kiem_khac_file`) đối soát MD5 để chốt điều đó bằng số.

**VieNeu KHÔNG TIỀN ĐỊNH** (OmniVoice từng ra 41,8% và 99,4% trên cùng một
hàm) -> chạy **nhiều lượt**, báo **DẢI**, không báo một số.

═══════════════════════════════════════════════════════════════════════════
CONFOUNDER ĐÃ LOẠI: DẤU CHÌM (watermark Perth) CỦA VieNeu
═══════════════════════════════════════════════════════════════════════════
VieNeu bật `apply_watermark=True` MẶC ĐỊNH, tức mọi file `vn:` trong phép đo
đều mang dấu chìm còn file ElevenLabs thì không. Nghi vấn hợp lý: **dấu chìm
có tự nó kéo cos xuống, làm hai giọng GIỐNG nhau trông thành KHÁC nhau
không?** Nếu có thì kết luận "khác người" là do thước, không do giọng.

ĐO THẲNG (`BQ_VN_WATERMARK=0`, sinh lại `vn:Adam` rồi so lại):

    vn:Adam KHÔNG watermark  x  ElevenLabs Adam    0,112 – 0,330 (TV 0,263)
    vn:Adam KHÔNG watermark  x  vn:Adam CÓ watermark
                                                   0,764 – 0,932 (TV 0,832)

Hàng 1 **trùng dải** với bản có watermark (0,115 – 0,346) -> dấu chìm KHÔNG
kéo con số. Hàng 2 nằm gọn trong vùng **cùng-một-người** -> dấu chìm không hề
làm ECAPA mất dấu người nói. **Confounder này đã loại, kết luận đứng nguyên.**
Chạy lại: xem lệnh trong `docs/DANH_SACH_GIONG.md` mục 6.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "_do_adam"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "adam"
FF = str(REPO / "bin" / "ffmpeg.exe")
PY_ECAPA = REPO / "_giong_chatter" / "venv" / "Scripts" / "python.exe"
MODEL_ECAPA = REPO / "_do_chatter" / "ecapa_model"
_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: SỐ LƯỢT VieNeu. 1 lượt rồi báo số là tự lừa mình — bộ này không tiền định.
#: Để 5 vì lượt VieNeu **KHÔNG tốn một ký tự ElevenLabs nào** (chạy trên máy):
#: dải rộng ra thì kết luận chắc thêm mà giá bằng 0.
SO_LUOT_VN = 5

# ---------------------------------------------------------------------------
# CÂU ĐO — TIẾNG ANH, vì `vn:Adam` là giọng TIẾNG ANH duy nhất của bộ VieNeu
# ---------------------------------------------------------------------------
#: 6 câu, chia **3 NHÓM 2 CÂU**. Chia nhóm KHÔNG phải cho gọn: nó là thứ làm
#: đối chứng dương có nghĩa (xem bẫy cos=1,000 ở docstring). 3 nhóm -> 3 cặp
#: đối chứng dương (AB · AC · BC) thay vì đúng một cặp.
CAU = [
    "The morning train was late again, and the platform was full of tired people.",
    "She opened the small wooden box and found a letter written many years ago.",
    "Nobody expected the storm to arrive so quickly on such a calm afternoon.",
    "He counted the coins twice, then put them back into his coat pocket.",
    "The old bridge across the river has been standing there for two centuries.",
    "They walked home in silence, listening to the sound of rain on the roof.",
]
NHOM = {"A": [0, 1], "B": [2, 3], "C": [4, 5]}

#: Giọng ElevenLabs. `pNInz6obpgDQGcFmaJgB` là Adam THẬT — id này có ở CẢ hai
#: chỗ: bảng premade công khai (`dubbing._ELEVEN_PREMADE[0]`) VÀ danh sách
#: account thật của anh Hùng (`_eleven_voices.json`: "Adam - Dominant, Firm").
EL_ADAM = "pNInz6obpgDQGcFmaJgB"

#: ĐỐI CHỨNG ÂM — **PHẢI LẤY GIỌNG CÓ THẬT TRONG THƯ VIỆN CỦA TÀI KHOẢN.**
#: Lượt đầu lấy `Rachel` (21m00Tcm4TlvDq8ikWAM) và `Josh`
#: (TxGEqnHWrfWFTfGW9XjX) theo bảng premade công khai -> **6/6 câu HỎNG mỗi
#: giọng**: hai id đó là giọng legacy KHÔNG có trong thư viện 5 tài khoản này
#: (`_eleven_voices.json` liệt kê 26 giọng, không có chúng). Nếu không kiểm thì
#: cả hai cột đối chứng âm ra RỖNG và mục 5 thành con số đứng một mình.
EL_NU = "EXAVITQu4vr4xnSDxMaL"      # Sarah — NỮ, đối chứng âm DỄ
#: Brian là đối chứng âm **KHÓ** và là cột đáng giá nhất: cùng ElevenLabs,
#: cùng NAM, cùng kiểu "trầm/ấm" như Adam. Nữ khác nam thì ECAPA tách quá dễ,
#: sàn đó không trả lời được câu "hai người đàn ông khác nhau thì bao nhiêu".
EL_NAM = "nPczCjzI2devNBz1zQrb"     # Brian — NAM trầm, đối chứng âm KHÓ

#: Giọng VieNeu khác để hỏi "chọn X có ra X không" + sàn "khác người cùng bộ".
#: **PHẢI CÓ ÍT NHẤT HAI** giọng đối chiếu, không phải một: với đúng một giọng
#: khác thì ca "chọn X ra X" có thể ĐẠT do may (bộ lùi bừa sang giọng thứ ba
#: vẫn ra "khác Minh Đức"). Lấy 1 nam (`Minh Đức`) + 1 nữ (`Trúc Ly`).
VN_KHAC = "Minh Đức"
VN_KHAC2 = "Trúc Ly"


def sec(t: str) -> None:
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74)


# ---------------------------------------------------------------------------
# HẠN MỨC ElevenLabs — ĐO THẬT, KHÔNG ƯỚC
# ---------------------------------------------------------------------------
def han_muc() -> tuple[int, int]:
    """(đã tiêu, trần) cộng dồn 5 tài khoản. (-1,-1) nếu không hỏi được.

    Hỏi API chứ không đếm ký tự mình gửi: `_eleven_tts` có CACHE nên số ký tự
    trong mã KHÔNG bằng số ký tự thật sự bị trừ.
    """
    from config import settings
    dung = tran = 0
    try:
        keys = settings.elevenlabs_keys()
    except Exception:                                        # noqa: BLE001
        return -1, -1
    for k in keys:
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/user/subscription",
                headers={"xi-api-key": k}, method="GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            dung += int(d.get("character_count") or 0)
            tran += int(d.get("character_limit") or 0)
        except Exception:                                    # noqa: BLE001
            pass                     # key chết thì bỏ qua, đừng giết phép đo
    return dung, tran


# ---------------------------------------------------------------------------
# SINH TIẾNG
# ---------------------------------------------------------------------------
def ra_wav16(src: Path, dst: Path) -> bool:
    """-> wav mono 16 kHz (ECAPA đòi đúng 16k). Kiểm KÍCH THƯỚC, không tin rc."""
    if dst.exists() and dst.stat().st_size > 4000:
        return True
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-vn",
                        "-ac", "1", "-ar", "16000", str(dst)],
                       capture_output=True, creationflags=_NO_WIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def noi_wav(ds: list[Path], dst: Path) -> bool:
    """Nối các wav 16k thành một file (ECAPA ăn cả nhóm trong 1 embedding)."""
    if dst.exists() and dst.stat().st_size > 4000:
        return True
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in ds),
                   encoding="utf-8")
    # `-c copy` trên WAV có lượt chỉ chép header file ĐẦU -> file dài sai mà
    # rc vẫn 0. Mã hoá lại PCM là KHÔNG MẤT DỮ LIỆU, nên không có gì để tiếc.
    r = subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c:a", "pcm_s16le", "-ar", "16000",
                        "-ac", "1", str(dst)],
                       capture_output=True, creationflags=_NO_WIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def sinh_el(vid: str, ten: str, chi_nhom_A: bool = False) -> dict[str, Path]:
    """ElevenLabs -> {nhóm: wav16}. Bỏ qua nhóm đã có file (khỏi tốn hạn mức).

    `chi_nhom_A` lọc TỪ ĐẦU chứ không lọc kết quả — lọc sau là đã trót gọi API
    cho nhóm B/C rồi vứt đi, tức đốt hạn mức cho thứ không dùng tới.
    """
    from app.core import dubbing
    d = SAN / "el" / ten
    d.mkdir(parents=True, exist_ok=True)
    ra: dict[str, Path] = {}
    cac_nhom = {"A": NHOM["A"]} if chi_nhom_A else NHOM
    for g, idx in cac_nhom.items():
        w16 = d / f"{g}.wav"
        if w16.exists() and w16.stat().st_size > 4000:
            ra[g] = w16
            continue
        phan: list[Path] = []
        for i in idx:
            mp3 = d / f"c{i}.mp3"
            wv = d / f"c{i}.wav"
            if not (wv.exists() and wv.stat().st_size > 4000):
                if not mp3.exists():
                    okk = dubbing._eleven_tts(CAU[i], f"el:{vid}", str(mp3))
                    if not okk:
                        print(f"  [!] ElevenLabs {ten} câu {i} HỎNG")
                        continue
                if not ra_wav16(mp3, wv):
                    print(f"  [!] đổi wav hỏng: {mp3.name}")
                    continue
            phan.append(wv)
        if len(phan) == len(idx) and noi_wav(phan, w16):
            ra[g] = w16
        else:
            print(f"  [!] ElevenLabs {ten} nhóm {g} THIẾU CÂU -> bỏ nhóm")
    return ra


def sinh_vn(ten_giong: str, luot: int, nhan: str) -> dict[str, Path]:
    """VieNeu -> {nhóm: wav16}. `luot` chỉ để tách thư mục (bộ không tiền định
    nên cùng câu vẫn ra tiếng khác — ca 0 đối soát MD5 chứng minh điều đó)."""
    from app.core import giong_vieneu as gv
    d = SAN / "vn" / f"{nhan}_L{luot}"
    d.mkdir(parents=True, exist_ok=True)
    thieu = [i for i in range(len(CAU))
             if not (d / f"c{i}.wav").exists()
             or (d / f"c{i}.wav").stat().st_size <= 4000]
    if thieu:
        paths = [str(d / f"c{i}.wav") for i in thieu]
        t0 = time.time()
        ok, _ = gv.doc_loat([CAU[i] for i in thieu], paths,
                            gv.TIEN_TO + ten_giong, lay_moc=False,
                            han_giay=1800)
        print(f"  VieNeu «{ten_giong}» lượt {luot}: {sum(ok)}/{len(thieu)} câu "
              f"· {time.time() - t0:.1f}s")
        # CHỌN X PHẢI RA X: `doc_loat` trả toàn False khi nó LÙI về edge-tts.
        # Bỏ qua chỗ này là đo giọng edge rồi gọi nó là VieNeu.
        if not all(ok):
            print(f"  [!] «{ten_giong}» LÙI edge-tts -> KHÔNG dùng lượt này")
            return {}
    ra: dict[str, Path] = {}
    for g, idx in NHOM.items():
        w16 = d / f"{g}.wav"
        phan = []
        for i in idx:
            wv = d / f"c{i}_16.wav"
            if ra_wav16(d / f"c{i}.wav", wv):
                phan.append(wv)
        if len(phan) == len(idx) and noi_wav(phan, w16):
            ra[g] = w16
    return ra


# ---------------------------------------------------------------------------
# ECAPA — dùng lại NGUYÊN VĂN runner đã hiệu chuẩn của `_do_chatter`
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
ra, giay = {}, {}
for k, p in job["files"].items():
    try:
        x, sr = sf.read(p, dtype="float32")
        giay[k] = round(len(x) / float(sr), 2)
        ra[k] = emb(p)
    except Exception as ex:
        ra[k] = None
        print("LOI %s: %s" % (k, ex), file=sys.stderr)
print("BQJSON\t" + json.dumps({"dev": dev, "emb": ra, "giay": giay}))
'''


def chay_ecapa(files: dict[str, str]) -> dict:
    SAN.mkdir(parents=True, exist_ok=True)
    run = SAN / "_ecapa_runner.py"
    run.write_text(MA_ECAPA, encoding="utf-8")
    job = SAN / "_ecapa_job.json"
    job.write_text(json.dumps({"files": files,
                               "savedir": str(MODEL_ECAPA)}),
                   encoding="utf-8")
    p = subprocess.run([str(PY_ECAPA), "-u", str(run), str(job)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NO_WIN, timeout=3600)
    for d in (p.stdout or "").splitlines():
        if d.startswith("BQJSON\t"):
            return json.loads(d[7:])
    raise RuntimeError(f"ECAPA rc={p.returncode}\n{(p.stderr or '')[-1500:]}")


def cos(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()[:12]


def dai(ds: list[float]) -> str:
    """"x,xxx – y,yyy (TV z,zzz, n cặp)" — báo DẢI, không báo một số."""
    if not ds:
        return "(không có cặp nào)"
    tv = statistics.median(ds)
    return (f"{min(ds):.3f} – {max(ds):.3f} (trung vị {tv:.3f}, "
            f"{len(ds)} cặp)".replace(".", ","))


# ---------------------------------------------------------------------------
def main() -> int:
    t_all = time.time()
    SAN.mkdir(parents=True, exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)

    sec("HẠN MỨC ElevenLabs TRƯỚC KHI ĐO")
    d0, tr0 = han_muc()
    print(f"  đã tiêu {d0} / trần {tr0} ký tự (cộng 5 tài khoản)")

    sec("1. SINH TIẾNG — ElevenLabs (giọng THẬT)")
    el = {}
    for vid, ten in ((EL_ADAM, "Adam"), (EL_NAM, "Brian"), (EL_NU, "Sarah")):
        # Đối chứng âm chỉ cần nhóm A — cần SÀN, không cần dải.
        gs = sinh_el(vid, ten, chi_nhom_A=(ten != "Adam"))
        el[ten] = gs
        print(f"  ElevenLabs {ten}: {sorted(gs)}")
        if not gs:
            print(f"  [!] {ten} KHÔNG sinh được câu nào — nhiều khả năng giọng "
                  f"này KHÔNG có trong thư viện tài khoản. Đối chứng sẽ RỖNG.")

    sec("2. SINH TIẾNG — VieNeu `vn:Adam` (và giọng khác để đối chứng)")
    vn: dict[str, dict[str, Path]] = {}
    for L in range(1, SO_LUOT_VN + 1):
        g = sinh_vn("Adam", L, "Adam")
        if g:
            vn[f"VN_Adam_L{L}"] = g
    gk = sinh_vn(VN_KHAC, 1, "Khac")
    if gk:
        vn["VN_MinhDuc_L1"] = {"A": gk["A"]} if "A" in gk else {}
    gk2 = sinh_vn(VN_KHAC2, 1, "Khac2")
    if gk2:
        vn["VN_TrucLy_L1"] = {"A": gk2["A"]} if "A" in gk2 else {}

    # ---- gom file -> khoá phẳng ------------------------------------------
    files: dict[str, str] = {}
    for ten, gs in el.items():
        for g, p in gs.items():
            files[f"EL_{ten}_{g}"] = str(p)
    for k, gs in vn.items():
        for g, p in gs.items():
            files[f"{k}_{g}"] = str(p)

    sec("CA 0 — CHỐNG BẪY «THƯ VIỆN DÙNG LẠI MẪU LƯỢT TRƯỚC» (cos = 1,000)")
    hs: dict[str, list[str]] = {}
    for k, p in files.items():
        hs.setdefault(md5(Path(p)), []).append(k)
    trung = {h: v for h, v in hs.items() if len(v) > 1}
    print(f"  {len(files)} file tiếng · {len(hs)} MD5 khác nhau")
    if trung:
        print("  [!] CÓ FILE TRÙNG TỪNG BYTE — mọi cos dính tới chúng là VÔ NGHĨA:")
        for h, v in trung.items():
            print(f"      {h}: {v}")
    else:
        print("  ĐẠT: không file nào trùng byte -> mỗi lượt là một lượt sinh THẬT")

    sec("3. ECAPA-TDNN")
    kq = chay_ecapa(files)
    emb = {k: v for k, v in (kq.get("emb") or {}).items() if v}
    giay = kq.get("giay") or {}
    print(f"  thiết bị {kq.get('dev')} · {len(emb)}/{len(files)} file có embedding")
    for k in sorted(files):
        print(f"    {k:<18} {giay.get(k, 0):>6.2f}s"
              + ("" if k in emb else "   [!] KHÔNG CÓ EMBEDDING"))

    def nhom_cos(ta: str, tb: str) -> list[float]:
        """Mọi cặp (khoá bắt đầu ta) × (khoá bắt đầu tb), bỏ cặp trùng khoá."""
        A = [k for k in emb if k.startswith(ta)]
        B = [k for k in emb if k.startswith(tb)]
        ra = []
        for a in A:
            for b in B:
                if a < b or (ta != tb and a != b):
                    ra.append(cos(emb[a], emb[b]))
        return ra

    def trong_nhom(t: str) -> list[float]:
        A = sorted(k for k in emb if k.startswith(t))
        return [cos(emb[a], emb[b]) for a, b in itertools.combinations(A, 2)]

    sec("4. ĐỐI CHỨNG — thiếu hai cột này thì mọi con số ở mục 5 là số rác")
    duong_el = trong_nhom("EL_Adam_")
    duong_vn = trong_nhom("VN_Adam_")
    am_nu = nhom_cos("VN_Adam_", "EL_Sarah_")
    am_nam = nhom_cos("VN_Adam_", "EL_Brian_")
    am_el = nhom_cos("EL_Adam_", "EL_Brian_") + nhom_cos("EL_Adam_", "EL_Sarah_")
    am_vn = nhom_cos("VN_Adam_", "VN_MinhDuc_")
    print(f"  DƯƠNG  ElevenLabs Adam × chính nó (khác câu)   : {dai(duong_el)}")
    print(f"  DƯƠNG  VieNeu Adam   × chính nó (khác lượt)    : {dai(duong_vn)}")
    print(f"  ÂM     VieNeu Adam   × ElevenLabs Sarah (NỮ)   : {dai(am_nu)}")
    print(f"  ÂM     VieNeu Adam   × ElevenLabs Brian (NAM)  : {dai(am_nam)}")
    print(f"  ÂM     ElevenLabs Adam × Brian/Sarah (cùng bộ) : {dai(am_el)}")
    print(f"  ÂM     VieNeu Adam   × VieNeu «{VN_KHAC}»        : {dai(am_vn)}")

    sec("5. CÂU HỎI CHÍNH — VieNeu Adam  ×  ElevenLabs Adam")
    chinh = nhom_cos("VN_Adam_", "EL_Adam_")
    print(f"  {dai(chinh)}")

    sec("6. ĐỌC KẾT QUẢ")
    ok_duong = bool(duong_el) and min(duong_el) >= 0.60
    ok_am = bool(am_nam) and max(am_nam) <= 0.45
    print(f"  đối chứng DƯƠNG có răng (>= 0,60): "
          f"{'ĐẠT' if ok_duong else 'KHÔNG ĐẠT'}")
    print(f"  đối chứng ÂM có răng   (<= 0,45): "
          f"{'ĐẠT' if ok_am else 'KHÔNG ĐẠT'}")
    if not (ok_duong and ok_am and chinh):
        ket = ("KHÔNG KẾT LUẬN ĐƯỢC — đối chứng chưa đứng vững, "
               "đừng đọc mục 5 thành kết luận")
    else:
        tv = statistics.median(chinh)
        lo, hi = min(chinh), max(chinh)
        sanam = max(am_nam + am_nu + am_vn)
        sanduong = min(duong_el + duong_vn)
        if hi < sanduong and tv <= sanam + 0.10:
            ket = ("KHÁC NGƯỜI — `vn:Adam` KHÔNG phải giọng Adam của "
                   "ElevenLabs. Anh Hùng ĐÚNG.")
        elif lo > sanam and tv >= 0.70:
            ket = ("GIỐNG — nghi ĐÚNG LÀ giọng ElevenLabs bán. "
                   "RỦI RO BẢN QUYỀN THẬT, phải báo anh Hùng.")
        else:
            ket = ("KHÔNG KẾT LUẬN ĐƯỢC — nằm giữa hai mốc, đừng chọn bừa "
                   "một phía.")
    print(f"\n  ==> {ket}")

    sec("CA 9 — CHỌN X RA X: `vn:Adam` có ra ĐÚNG Adam không")
    # Vì sao ca này phải có: lỗi `ov:nu_am` đã bắt được một lần — combo hiện
    # giọng X, lượt đọc lặng lẽ trả về giọng Y, `rc` vẫn 0. Ở đây có 5 lượt
    # `doc_loat(voice="vn:Adam")` GỌI RIÊNG BIỆT; nếu bộ lùi bừa thì các lượt
    # ấy không thể tụ lại quanh cùng một người.
    tu_tu = trong_nhom("VN_Adam_")
    print(f"  5 lượt chọn `vn:Adam` có tụ về CÙNG MỘT người không: {dai(tu_tu)}")
    for ten, tien in (("Minh Đức", "VN_MinhDuc_"), ("Trúc Ly", "VN_TrucLy_")):
        d2 = nhom_cos("VN_Adam_", tien)
        print(f"  `vn:Adam` × `vn:{ten}` (phải THẤP)          : {dai(d2)}")
    khac = nhom_cos("VN_Adam_", "VN_MinhDuc_") + nhom_cos("VN_Adam_",
                                                          "VN_TrucLy_")
    ok_x = bool(tu_tu) and bool(khac) and min(tu_tu) > max(khac)
    print(f"  ==> {'ĐẠT' if ok_x else 'KHÔNG ĐẠT'}: "
          f"lượt-Adam-với-nhau thấp nhất {min(tu_tu):.3f} "
          f"{'>' if ok_x else '<='} Adam-với-giọng-khác cao nhất "
          f"{max(khac):.3f}".replace(".", ","))
    if not ok_x:
        print("  [!] CHỌN X KHÔNG RA X — combo và lượt đọc đang lệch nhau.")

    # ---- file để anh Hùng TỰ NGHE ---------------------------------------
    sec("7. FILE TIẾNG ĐỂ ANH HÙNG TỰ NGHE (tai anh ấy là phán quyết cuối)")
    import shutil
    dem = 0
    for k, p in files.items():
        if k.startswith(("EL_Adam_", "VN_Adam_L1_", "EL_Brian_", "VN_MinhDuc_")):
            dst = NGHE / f"{k}.wav"
            shutil.copyfile(p, dst)
            dem += 1
    print(f"  {dem} file -> {NGHE}")
    print("  cùng câu, cùng nội dung; tên file nói rõ nguồn nào.")

    d1, tr1 = han_muc()
    sec("HẠN MỨC ElevenLabs SAU KHI ĐO")
    print(f"  đã tiêu {d1} / trần {tr1}  ->  LƯỢT NÀY TIÊU {d1 - d0} KÝ TỰ")

    (REPO / "_kq_adam.json").write_text(json.dumps({
        "chinh": chinh, "duong_el": duong_el, "duong_vn": duong_vn,
        "am_nu_sarah": am_nu, "am_nam_brian": am_nam, "am_el": am_el,
        "am_vn": am_vn, "giay": giay, "ket": ket,
        "ky_tu_tieu": d1 - d0, "trung_byte": trung,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nXong trong {time.time() - t_all:.1f}s · số thô -> _kq_adam.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
