# -*- coding: utf-8 -*-
"""ĐO GIỌNG NHÂN BẢN CỦA ANH HÙNG — đi ĐÚNG cửa `nhan_ban_giong` + `dubbing`.

Anh Hùng: *"ném giọng đọc của tôi khoảng mấy giây Reference Audio, sau đó dán
bao nhiêu ký tự dùng giọng đó cũng được"*. File này trả lời 5 câu bằng SỐ.

═══════════════════════════════════════════════════════════════════════════
MẪU LÀ **GIẢ LẬP**, NÓI RA NGAY ĐẦU — ĐỪNG ĐỌC THÀNH "GIỌNG ANH HÙNG"
═══════════════════════════════════════════════════════════════════════════
Không có file giọng thật của anh Hùng trên máy này, và **luật cấm nhân bản
giọng người khác** (xem `nhan_ban_giong.CANH_BAO_PHAP_LY`). Nên mẫu được TỰ
SINH bằng edge-tts giọng `vi-VN-*` — sạch giấy phép, và biết CHẮC hai mẫu là
hai "người" khác nhau nên phép đối chứng mới có nghĩa.

**Hệ quả phải nhớ khi đọc bảng:** mẫu edge-tts là mẫu SẠCH TUYỆT ĐỐI (không
nhiễu, không nhạc nền, một người nói). `giong_vieneu` đã đo: mẫu sạch cho
7,7% đọc sai (bằng giọng dựng sẵn) còn **mẫu thu bằng điện thoại lên 21-31%**.
Vậy mọi số ở đây là **TRẦN TRÊN** — giọng thật của anh Hùng thu bằng điện
thoại sẽ TỆ HƠN. Không được đọc bảng này thành lời hứa.

═══════════════════════════════════════════════════════════════════════════
THƯỚC ĐỘ GIỐNG: **F0 (CAO ĐỘ)**, KHÔNG PHẢI ECAPA — VÀ NÓI RÕ NÓ KHÔNG ĐỦ
═══════════════════════════════════════════════════════════════════════════
`_do_nhan_ban.py` dùng ECAPA-TDNN, nhưng `speechbrain` **không có trong
`_lib_giong` lẫn `.venv`** (kiểm bằng thư mục, không bằng `find_spec`) nên
đường đó không chạy được trong lượt này.

Thước dùng ở đây là thước `giong_vieneu` đã dùng cho lượt 9: **trung vị F0
nửa cung** (`_do_nhan_nha.f0_nua_cung`, khung 40 ms). Nó trả lời được ĐÚNG
một câu — *"bản sao có đi theo cao độ của mẫu, hay nó đứng ở cao độ mặc định
của model?"* — và đó chính là câu phân biệt "nhân bản CHẠY" với **DƯƠNG TÍNH
GIẢ** (bẫy `use_ref_codes` đã sập ở lượt 4: truyền đường dẫn vào một cờ bool
thì tiếng vẫn ra bình thường mà giọng là giọng mặc định).

**NÓ KHÔNG trả lời được "bản sao có GIỐNG NGƯỜI ĐÓ không"** — hai người khác
nhau vẫn có thể cùng cao độ. Muốn câu đó thì cần ECAPA. Ghi thẳng vào cột
"CHƯA ĐO".

BA ARM BẮT BUỘC, thiếu một cái là con số vô nghĩa:
  · **ĐỐI CHỨNG DƯƠNG** — bản sao vs CHÍNH mẫu của nó (phải GẦN)
  · **ĐỐI CHỨNG ÂM**   — bản sao vs mẫu của NGƯỜI KHÁC (phải XA)
  · **ĐỐI CHỨNG "KHÔNG CLONE"** — giọng VieNeu dựng sẵn vs cùng mẫu. Đây là
    arm quyết định: nếu nó GẦN bằng arm clone thì clone không làm gì cả.

Chạy: .venv\\Scripts\\python -u _do_giong_toi.py
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics as st
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

SAN = REPO / "_do_giong_toi"
os.environ.setdefault("BQ_DATA_DIR", str(SAN / "data"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
_NO_WIN = 0x08000000 if os.name == "nt" else 0

#: ffmpeg — lấy từ `settings` chứ KHÔNG ghi cứng `bin/ffmpeg.exe`. Bài học cổng
#: 86: `bin/` từng là build 2023 trong khi app chạy bản trên PATH, tức 21 file
#: test đang đo một ffmpeg KHÁC ffmpeg sản xuất.
from config import settings                                    # noqa: E402
FF = settings.FFMPEG_PATH

from _do_nhan_nha import f0_nua_cung                           # noqa: E402
from _do_nhan_nha_bang import CAU                              # noqa: E402
from app.core import dubbing as DUB                            # noqa: E402
from app.core import giong_vieneu as VN                        # noqa: E402
from app.core import nhan_ban_giong as NB                      # noqa: E402

#: Hai "người" giả lập. Giọng edge-tts KHÁC HẲN nhau (nữ Bắc / nam Bắc) để
#: đối chứng ÂM có răng — hai mẫu giống nhau thì phép đo không phân biệt được.
MAU = [("A_nu", "vi-VN-HoaiMyNeural"), ("B_nam", "vi-VN-NamMinhNeural")]

#: Câu để DỰNG MẪU. Phải đủ dài: `nhan_ban_giong.MAU_GIAY_MIN` = 4,0 giây.
CAU_MAU = ("Đây là đoạn ghi âm ngắn để làm mẫu giọng của tôi. Tôi đọc thêm "
           "vài câu nữa cho đủ dài, để máy học được chất giọng chính xác.")

#: Bộ câu ĐO — **dùng đúng `_do_nhan_nha_bang.CAU["vi"]`**, không tự bịa bộ
#: khác: mọi số nhấn nhá của bảng 211 giọng đo trên bộ này, đổi bộ là bảng
#: không so được với 3,40 / 3,96 / 3,24 / 2,33 nữa.
CAU_DO = list(CAU["vi"])

#: Mốc nhấn nhá đã có (`nhan_nha.BANG`) — để so, KHÔNG để chấm đạt/hỏng.
MOC_NN = {"vi-VN-HoaiMyNeural": 3.40, "vi-VN-NamMinhNeural": 3.96,
          "Piper vais1000": 3.24, "Kokoro af_bella": 2.33}

#: Giọng VieNeu dựng sẵn làm ĐỐI CHỨNG "KHÔNG CLONE". `Ngọc Huyền` vì bảng
#: `_kq_vn_quet34.txt` đo nó **2,5% token sai / WER 4,8%** = sát trần edge-tts,
#: tức nó KHÔNG phải một giọng lệch (khác `Xuân Vĩnh` 20,0% / `Quang Sơn`).
VN_PRESET = "Ngọc Huyền"


# ---------------------------------------------------------------------------
# Thước phụ
# ---------------------------------------------------------------------------
def wav24(src: Path, dst: Path) -> bool:
    """Về 24 kHz mono — đúng tần số `nhan_ban_giong.them_giong` chuẩn hoá."""
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-vn",
                        "-ac", "1", "-ar", "24000", str(dst)],
                       capture_output=True, creationflags=_NO_WIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def moc_phat_tieng(wav: Path) -> float:
    """Giây đầu THẬT SỰ có tiếng — thước ĐỘC LẬP, không máy nghe.

    Ngưỡng **−30 dB**, không −40/−45: `giong_vieneu` đã ghi *"−40 dB quá nhạy,
    nó tưởng tiếng HÍT VÀO là bắt đầu nói -> chấm trễ oan"*, và arm edge-tts
    chỉ tái lập được ~15 ms ở ngưỡng −30.
    """
    r = subprocess.run(
        [FF, "-v", "info", "-i", str(wav), "-af",
         "silencedetect=noise=-30dB:d=0.05", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=180)
    for d in (r.stderr or "").splitlines():
        if "silence_end:" in d:
            try:
                return float(d.split("silence_end:")[1].split()[0])
            except (IndexError, ValueError):
                pass
    return 0.0


def f0_tv(wav: Path) -> float:
    """TRUNG VỊ F0 (nửa cung). Trung vị chứ không trung bình: một khung dò
    nhầm bát độ (rất hay xảy ra với F0) kéo trung bình đi hàng nửa cung."""
    try:
        v = [x for x in f0_nua_cung(wav) if x]
        return st.median(v) if v else 0.0
    except Exception:                                          # noqa: BLE001
        return 0.0


def nhan_nha(wav: Path) -> float:
    """ĐỘ LỆCH CHUẨN F0 nửa cung = mức nhấn nhá. Đúng thước bảng 211 giọng."""
    try:
        v = [x for x in f0_nua_cung(wav) if x]
        return st.pstdev(v) if len(v) > 1 else 0.0
    except Exception:                                          # noqa: BLE001
        return 0.0


def tu(s: str) -> list[str]:
    """Đếm từ — dùng lại `recap._word_tokens` (CJK-aware). Tiếng Việt có dấu
    cách nên nó == `.split()`, nhưng đi cửa chung thì khỏi đẻ quy ước thứ hai."""
    from app.ai.recap import _word_tokens
    return list(_word_tokens(s or ""))


class Canh:
    """Canh RAM đỉnh của CẢ CÂY tiến trình — **POLL TRONG LÚC CHẠY**.

    Bẫy đã sập ở cổng 71 VÀ 73: lấy mẫu TRƯỚC/SAU thì tiến trình con đã thoát
    và trả sạch bộ nhớ, nên số ra đúng bằng mức NỀN = **không đo gì cả**.
    """

    def __init__(self) -> None:
        self.ram = 0
        self.vram = 0
        self._on = False
        self._th: threading.Thread | None = None

    def _vong(self) -> None:
        import psutil
        me = psutil.Process()
        while self._on:
            try:
                t = me.memory_info().rss
                for c in me.children(recursive=True):
                    try:
                        t += c.memory_info().rss
                    except Exception:                          # noqa: BLE001
                        pass
                self.ram = max(self.ram, t)
            except Exception:                                  # noqa: BLE001
                pass
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=_NO_WIN)
                if r.returncode == 0:
                    self.vram = max(self.vram, int(r.stdout.strip().split()[0]))
            except Exception:                                   # noqa: BLE001
                pass
            time.sleep(0.25)

    def __enter__(self) -> "Canh":
        self._on = True
        self._th = threading.Thread(target=self._vong, daemon=True)
        self._th.start()
        return self

    def __exit__(self, *a) -> None:
        self._on = False
        if self._th:
            self._th.join(timeout=3)


def doc_arm(ten: str, ma: str, cau: list[str], d: Path,
            lay_moc: bool = True) -> dict:
    """Đọc cả loạt câu bằng MỘT mã giọng, qua CỬA THẬT của app.

    Đi qua `dubbing._synth_all_words` (cửa app dùng khi cần mốc từng chữ) chứ
    KHÔNG gọi `giong_vieneu.doc_loat` trực tiếp — đo hàm con là bỏ sót đúng chỗ
    hay hỏng nhất (bài học cổng 19).
    """
    d.mkdir(parents=True, exist_ok=True)
    ra = [str(d / f"{ten}_{i:03d}.mp3") for i in range(len(cau))]
    with Canh() as c:
        t0 = time.time()
        ok, moc = asyncio.run(
            DUB._synth_all_words(list(cau), ma, ra, lang="vi"))
        giay = time.time() - t0
    return {"ten": ten, "ma": ma, "ok": list(ok), "moc": moc, "ra": ra,
            "giay": round(giay, 2), "ram_mb": round(c.ram / 2 ** 20),
            "vram_mib": c.vram, "cau": list(cau)}


def sang_wav(arm: dict, d: Path) -> list[Path]:
    """mp3 -> wav 24 kHz để đo F0 (`f0_nua_cung` đọc WAV, không đọc mp3)."""
    ws: list[Path] = []
    for i, p in enumerate(arm["ra"]):
        w = d / f"{arm['ten']}_{i:03d}.wav"
        ws.append(w if (Path(p).exists() and wav24(Path(p), w)) else Path(""))
    return ws


def main() -> int:                                             # noqa: C901
    SAN.mkdir(parents=True, exist_ok=True)
    D = SAN / "lam"
    D.mkdir(parents=True, exist_ok=True)
    kq: dict = {"mau_la_gia_lap": True}

    print("=" * 74)
    print("ĐO GIỌNG NHÂN BẢN — mẫu là GIẢ LẬP (edge-tts), không phải giọng thật")
    print("=" * 74)

    # ---- 0. Máy nhân bản có chạy được không -------------------------------
    thieu = NB.thieu_de_nhan_ban(NB.MAY_VIENEU)
    print(f"\n[0] thieu_de_nhan_ban('vieneu') = {thieu or 'KHÔNG THIẾU GÌ'}")
    print(f"    may_chay_duoc = {NB.may_chay_duoc(NB.MAY_VIENEU)}")
    if thieu:
        print("    => đường NHÂN BẢN KHÔNG chạy được trên máy này, DỪNG.")
        return 2

    # ---- 1. Dựng MẪU giả lập bằng edge-tts --------------------------------
    print("\n[1] Dựng mẫu giả lập bằng edge-tts (giọng vi-VN)")
    mau_wav: dict[str, Path] = {}
    for ten, giong in MAU:
        mp3 = D / f"mau_{ten}.mp3"
        if not mp3.exists():
            asyncio.run(DUB._synth_all([CAU_MAU], giong, [str(mp3)],
                                       lang="vi"))
        w = D / f"mau_{ten}.wav"
        if not w.exists():
            wav24(mp3, w)
        mau_wav[ten] = w
        kt = NB.kiem_mau(str(w))
        print(f"    {ten:7} {giong:24} {VN.dai_wav(w):5.2f}s  "
              f"kiểm_mẫu ok={kt['ok']} tỉ_lệ_tiếng={kt['ty_le_tieng']}")

    # ---- 2. Thêm vào SỔ qua cửa thật -------------------------------------
    print("\n[2] Thêm vào sổ qua nhan_ban_giong.them_giong (có KIỂM mẫu)")
    ma_clone: dict[str, str] = {}
    for ten, _g in MAU:
        nb_ten = f"Giọng thử {ten}"
        NB.xoa(nb_ten)                       # chạy lại nhiều lượt cho sạch
        r = NB.them_giong(nb_ten, str(mau_wav[ten]), lang="vi",
                          nguon="mẫu tự sinh bằng edge-tts (giả lập)")
        ma_clone[ten] = r.get("ma") or ""
        print(f"    {nb_ten:18} ok={r['ok']} ma={r.get('ma')!r}")
        if not r["ok"]:
            print(f"      LỖI: {r.get('loi')}")
            return 2
    print(f"    danh_sach() = {NB.danh_sach()}")

    # ---- 3. Đọc 4 ARM trên CÙNG bộ câu -----------------------------------
    # ĐỐI CHỨNG PHẢI CHẠY CÙNG LƯỢT (bài học Kokoro): arm edge-tts ở đây tái
    # lập lại mốc 3,40 / 3,96 của bảng cũ — không có nó thì 2 cột clone kia
    # không so được với bảng nào.
    print(f"\n[3] Đọc {len(CAU_DO)} câu × 5 arm (đối chứng chạy CÙNG LƯỢT)")
    arms: dict[str, dict] = {}
    ke: list[tuple[str, str]] = [
        ("CLONE_A", ma_clone["A_nu"]),
        ("CLONE_B", ma_clone["B_nam"]),
        ("VN_PRESET", VN.TIEN_TO + VN_PRESET),
        ("EDGE_A", MAU[0][1]),
        ("EDGE_B", MAU[1][1]),
    ]
    for ten, ma in ke:
        a = doc_arm(ten, ma, CAU_DO, D)
        a["wav"] = sang_wav(a, D)
        a["f0"] = [f0_tv(w) if str(w) else 0.0 for w in a["wav"]]
        a["nn"] = [nhan_nha(w) if str(w) else 0.0 for w in a["wav"]]
        arms[ten] = a
        print(f"    {ten:10} ok {sum(a['ok'])}/{len(CAU_DO)} · {a['giay']:6.1f}s"
              f" · RAM {a['ram_mb']:5d} MB · VRAM {a['vram_mib']} MiB")

    # ---- 4. MỤC 1 — độ giống mẫu ----------------------------------------
    print("\n" + "=" * 74)
    print("MỤC 1 — BẢN SAO CÓ ĐI THEO CAO ĐỘ CỦA MẪU KHÔNG (F0 trung vị, nửa cung)")
    print("=" * 74)
    f0_mau = {t: f0_tv(w) for t, w in mau_wav.items()}
    print(f"    MẪU A_nu   F0 = {f0_mau['A_nu']:.2f} nửa cung")
    print(f"    MẪU B_nam  F0 = {f0_mau['B_nam']:.2f} nửa cung")
    print(f"    => hai mẫu cách nhau {abs(f0_mau['A_nu']-f0_mau['B_nam']):.2f} "
          f"nửa cung (phép đo có răng khi số này LỚN)")

    def tv(xs: list[float]) -> float:
        v = [x for x in xs if x]
        return st.median(v) if v else 0.0

    bang1 = []
    for arm_ten in ("CLONE_A", "CLONE_B", "VN_PRESET"):
        f0a = tv(arms[arm_ten]["f0"])
        bang1.append((arm_ten, f0a, abs(f0a - f0_mau["A_nu"]),
                      abs(f0a - f0_mau["B_nam"])))
    print(f"\n    {'arm':12} {'F0':>7} {'|Δ vs MẪU A|':>14} {'|Δ vs MẪU B|':>14}")
    for t, f0a, da, db in bang1:
        print(f"    {t:12} {f0a:7.2f} {da:14.2f} {db:14.2f}")
    kq["muc1"] = {"f0_mau": f0_mau, "bang": bang1}

    # ---- 5. MỤC 2 — NHẤN NHÁ -------------------------------------------
    print("\n" + "=" * 74)
    print("MỤC 2 — NHẤN NHÁ (pstdev F0 nửa cung, khung 40 ms) — thứ anh Hùng chê")
    print("=" * 74)
    print(f"    {'arm':12} {'nhấn nhá':>10}   (mốc: HoaiMy 3,40 · NamMinh 3,96"
          f" · Piper 3,24 · Kokoro 2,33)")
    nn: dict[str, float] = {}
    for t in ("CLONE_A", "CLONE_B", "VN_PRESET", "EDGE_A", "EDGE_B"):
        v = [x for x in arms[t]["nn"] if x]
        nn[t] = round(st.mean(v), 2) if v else 0.0
        print(f"    {t:12} {nn[t]:10.2f}")
    print(f"\n    ĐỐI CHỨNG TÁI LẬP: EDGE_A {nn['EDGE_A']:.2f} vs mốc 3,40 "
          f"(lệch {abs(nn['EDGE_A']-3.40):.2f}) · "
          f"EDGE_B {nn['EDGE_B']:.2f} vs mốc 3,96 "
          f"(lệch {abs(nn['EDGE_B']-3.96):.2f})")
    print("    ^ lệch LỚN ở hai dòng này = phép đo KHÔNG so được với bảng cũ")
    kq["muc2"] = nn

    # ---- 6. MỤC 4 — PHỦ MỐC + RUNG -------------------------------------
    print("\n" + "=" * 74)
    print("MỤC 4 — MỐC TỪNG CHỮ (VieNeu KHÔNG tự trả mốc -> qua giong_hang)")
    print("=" * 74)
    print(f"    {'arm':12} {'phủ':>8} {'rung':>10}   (mốc: gióng hàng 98,5-98,6%"
          f" · rung 90-119 ms · edge tự trả 15,7 ms)")
    kq["muc4"] = {}
    for t in ("CLONE_A", "CLONE_B", "VN_PRESET", "EDGE_A"):
        a = arms[t]
        co = tong = 0
        lech: list[float] = []
        for i, m in enumerate(a["moc"] or []):
            if not a["ok"][i]:
                continue
            tong += len(tu(a["cau"][i]))
            co += len(m or [])
            w = a["wav"][i] if i < len(a["wav"]) else Path("")
            if m and str(w):
                lech.append((float(m[0][0]) - moc_phat_tieng(w)) * 1000.0)
        phu = 100.0 * co / tong if tong else 0.0
        rung = st.pstdev(lech) if len(lech) > 1 else 0.0
        he_thong = st.median(lech) if lech else 0.0
        print(f"    {t:12} {phu:7.1f}% {rung:9.1f}ms   "
              f"(lệch hệ thống {he_thong:+.1f} ms, {len(lech)} câu)")
        kq["muc4"][t] = {"phu": round(phu, 1), "rung": round(rung, 1),
                         "he_thong": round(he_thong, 1)}

    # ---- 7. MỤC 3 — ĐỌC DÀI --------------------------------------------
    print("\n" + "=" * 74)
    print("MỤC 3 — ĐỌC DÀI: cụt chữ + lệch chất giọng giữa các đoạn")
    print("=" * 74)
    # ~45 câu: lặp bộ 4 câu cho đủ số, KHÔNG bịa câu mới (bộ này đã hiệu chuẩn)
    dai = [CAU_DO[i % len(CAU_DO)] for i in range(44)]
    print(f"    {len(dai)} câu · trần ký tự MỖI LƯỢT infer = "
          f"max_chars 256 (v3turbo.infer), app KHÔNG tự chia câu — "
          f"`normalize_to_chunks_v3_with_gaps` chia trong GÓI")
    print(f"    câu dài nhất trong bộ: {max(len(c) for c in dai)} ký tự "
          f"(dưới trần 256 -> mỗi câu là MỘT chunk)")
    Dd = SAN / "dai"
    a = doc_arm("DAI_A", ma_clone["A_nu"], dai, Dd)
    a["wav"] = sang_wav(a, Dd)
    a["f0"] = [f0_tv(w) if str(w) else 0.0 for w in a["wav"]]
    print(f"    đọc {sum(a['ok'])}/{len(dai)} câu · {a['giay']:.1f}s · "
          f"RAM đỉnh {a['ram_mb']} MB · VRAM {a['vram_mib']} MiB")
    tong_giay = sum(VN.dai_wav(w) for w in a["wav"] if str(w))
    print(f"    tổng tiếng ra {tong_giay:.1f}s -> tỉ lệ so thời gian thật "
          f"{a['giay']/max(0.01, tong_giay):.3f}x")

    # LỆCH CHẤT GIỌNG GIỮA CÁC ĐOẠN — bệnh đã báo ở CosyVoice
    f0d = [x for x in a["f0"] if x]
    print(f"\n    LỆCH CHẤT GIỌNG giữa {len(f0d)} câu: F0 trung vị "
          f"{st.median(f0d):.2f} · độ lệch chuẩn {st.pstdev(f0d):.2f} nửa cung"
          f" · dải {min(f0d):.2f}..{max(f0d):.2f}")
    n4 = max(1, len(f0d) // 4)
    quy = [st.median(f0d[i:i + n4]) for i in range(0, len(f0d), n4)]
    print(f"    F0 trung vị theo TỪNG PHẦN TƯ: "
          f"{' · '.join(f'{x:.2f}' for x in quy)}")
    print(f"    -> lệch phần-tư lớn nhất {max(quy)-min(quy):.2f} nửa cung")

    # CỤT CHỮ — Groq chép ngược
    print("\n    CỤT CHỮ (Groq chép ngược 8 câu mẫu, so số từ vào/ra):")
    from app.core import transcribe as TR
    vao = ra_ = 0
    n_ok = 0
    for i in range(0, len(dai), max(1, len(dai) // 8)):
        if not a["ok"][i] or not Path(a["ra"][i]).exists():
            continue
        try:
            r = TR.transcribe(a["ra"][i], language="vi")
            chu = (r.get("text") if isinstance(r, dict) else str(r)) or ""
        except Exception as e:                                 # noqa: BLE001
            print(f"      câu {i}: Groq lỗi {type(e).__name__}")
            continue
        v, o = len(tu(dai[i])), len(tu(chu))
        vao += v
        ra_ += o
        n_ok += 1
        print(f"      câu {i:2d}: vào {v:2d} từ -> ra {o:2d} từ  "
              f"{'CỤT' if o < v else 'đủ'}")
    if vao:
        print(f"    TỔNG {n_ok} câu: vào {vao} từ -> ra {ra_} từ = "
              f"{100.0*ra_/vao:.1f}% (dưới 100% là CỤT CHỮ)")
    kq["muc3"] = {"so_cau": len(dai), "doc_duoc": sum(a["ok"]),
                  "giay": a["giay"], "ram_mb": a["ram_mb"],
                  "tong_tieng": round(tong_giay, 1),
                  "f0_lech_pt": round(max(quy) - min(quy), 2),
                  "f0_sd": round(st.pstdev(f0d), 2),
                  "tu_vao": vao, "tu_ra": ra_}

    # ---- 8. MỤC 5 — thời gian + RAM (gom lại) --------------------------
    print("\n" + "=" * 74)
    print("MỤC 5 — THỜI GIAN + RAM/VRAM (POLL trong lúc chạy, không lấy mẫu 2 đầu)")
    print("=" * 74)
    print(f"    {'arm':12} {'giây':>8} {'RAM đỉnh':>10} {'VRAM đỉnh':>11}")
    for t in ("CLONE_A", "CLONE_B", "VN_PRESET", "EDGE_A"):
        x = arms[t]
        print(f"    {t:12} {x['giay']:8.1f} {x['ram_mb']:8d} MB "
              f"{x['vram_mib']:8d} MiB")
    print(f"    {'DAI_A(44 câu)':12} {a['giay']:8.1f} {a['ram_mb']:8d} MB "
          f"{a['vram_mib']:8d} MiB")
    kq["muc5"] = {t: {"giay": arms[t]["giay"], "ram_mb": arms[t]["ram_mb"],
                      "vram_mib": arms[t]["vram_mib"]}
                  for t in arms}
    kq["muc5"]["DAI_A"] = {"giay": a["giay"], "ram_mb": a["ram_mb"],
                           "vram_mib": a["vram_mib"]}

    (REPO / "_kq_giong_toi.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print("\nĐã ghi _kq_giong_toi.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
