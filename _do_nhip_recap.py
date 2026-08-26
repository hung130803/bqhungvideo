# -*- coding: utf-8 -*-
"""ĐO NHỊP TIẾN TRÌNH CỦA ĐƯỜNG RECAP (`dubbing.build_recap_track`).

Trả nợ 1 của cổng 90: cổng đó canh 3 chỗ gọi TTS của `thay_giong.py`, nhưng
`dubbing.py` còn **3 chỗ gọi `_synth_all_words` nữa** — đường REUP THUYẾT MINH
(`m1_highlight._export_clip_impl`, nhánh `is_recap`). Câu hỏi phải ĐO chứ
không đọc mã rồi suy: chúng CÓ mắc đúng bệnh "thanh đứng im" không, hay đường
recap có cơ chế báo tiến độ khác?

CÁCH ĐO: giả lập một máy đọc **GỘP CẢ LOẠT** (VieNeu · Kokoro · Chatterbox ·
Vbee · giọng ngoài — mọi giọng KHÔNG phải edge-tts đều đi đường này) rồi GỌI
THẬT `build_recap_track`, bắt TỪNG lần `on_progress`. Máy đọc giả tự đánh dấu
lời gọi nào phát ra TRONG LÚC nó đang đọc (`tu_nhip`), nên phép phân loại
không phụ thuộc nội dung chữ.

RẺ: không mạng · không Groq · không edge-tts · không ffmpeg (mọi hàm đụng
ffmpeg đều bị vá bằng bản GIẢ; `build_recap_track` chạy THẬT).

    .venv\\Scripts\\python -u _do_nhip_recap.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / f"_kq_donhip_{os.getpid()}"
shutil.rmtree(HOP, ignore_errors=True)
(HOP / "data").mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "studio.db")

from app.core import dubbing  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

N_CAU = 6
LOI_NHAN = [
    "Nap model doc...",
    "Doc cau 1/6",
    "Doc cau 2/6",
    "Dang doc cau tiep...",
    "Doc cau 4/6",
    "Doc cau 6/6",
]
#: Tỉ lệ tương ứng của từng lời báo (`None` = lời KHÔNG CÓ SỐ) — để máy đọc
#: giả dựng lại đúng dãy đó cho lượt đọc có SỐ CÂU KHÁC (vd lượt VÉT 3 câu).
TY_LE = [None, 1 / 6, 2 / 6, None, 4 / 6, 1.0]


def so(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


class Ghi:
    """Bắt từng lần `on_progress`, có ĐÁNH DẤU nguồn."""

    def __init__(self) -> None:
        self.moi: list[tuple[float, str, bool]] = []
        self.tu_nhip = False
        self.co_on_msg: bool | None = None
        #: `on_msg` có được truyền xuống ở TỪNG lượt gọi máy đọc (site 1/2/3)
        self.tung_lan: list[bool] = []
        #: số nhịp bắt được ở TỪNG lượt gọi
        self.nhip_lan: list[int] = []
        #: chỉ số trong `moi` lúc MỖI lượt gọi máy đọc bắt đầu -> cắt dãy chữ
        #: theo BƯỚC (bất biến "không lùi" là bất biến TRONG MỘT bước)
        self.moc_lan: list[int] = []

    def __call__(self, p, m="") -> None:
        self.moi.append((float(p), str(m), self.tu_nhip))

    def nhip(self):
        return [(p, m) for p, m, t in self.moi if t]


# ══════════════════════════════════════════════════════════════════════════
# MÁY ĐỌC GIẢ — GỘP CẢ LOẠT, đúng hình dạng `giong_vieneu.doc_loat`
# ══════════════════════════════════════════════════════════════════════════
def _may_doc_gia(ghi: Ghi, xen_ke: bool = False, hong_lan_dau: int = 0,
                 kieu_edge: bool = False):
    dem = {"n": 0}

    async def _gia(texts, voice, paths, on_done=None, rate="+0%",
                   pitch="+0Hz", lang="", el_lui=True, on_msg=None, **kw):
        dem["n"] += 1
        ghi.co_on_msg = on_msg is not None
        ghi.tung_lan.append(on_msg is not None)
        _truoc = len(ghi.nhip())
        ghi.moc_lan.append(len(ghi.moi))
        for p in paths:
            pp = Path(p)
            pp.parent.mkdir(parents=True, exist_ok=True)
            pp.write_bytes(b"\0" * 16)
        # Mẫu số phải theo ĐÚNG số câu lượt này đọc — lượt VÉT chỉ đọc lại
        # mấy câu hỏng, để nguyên `/6` là dựng sai cảnh (ra cả `Doc cau 6/3`)
        # rồi đọc sai số đo.
        _n = max(1, len(texts))
        nhan = [LOI_NHAN[k] if f is None
                else f"Doc cau {max(1, min(_n, int(round(f * _n))))}/{_n}"
                for k, f in enumerate(TY_LE)]
        if kieu_edge:
            # HÌNH DẠNG edge-tts: KHÔNG có `on_msg`, `on_done` nổ TỪNG CÂU.
            if on_done:
                for i in range(len(texts)):
                    on_done(i)
            ghi.nhip_lan.append(len(ghi.nhip()) - _truoc)
            return [True] * len(texts), [[] for _ in texts]
        if xen_ke:
            # XEN KẼ: mỗi lời báo nhịp rồi tới một `on_done` — dựng đúng cảnh
            # "hai nguồn xen kẽ nhau" mà nợ 2 nói tới.
            for i, m in enumerate(nhan):
                if on_msg:
                    ghi.tu_nhip = True
                    try:
                        on_msg(m)
                    finally:
                        ghi.tu_nhip = False
                if on_done and i < len(texts):
                    on_done(i)
            for i in range(len(nhan), len(texts)):
                if on_done:
                    on_done(i)
        else:
            for m in nhan:
                if on_msg:
                    ghi.tu_nhip = True
                    try:
                        on_msg(m)
                    finally:
                        ghi.tu_nhip = False
            # `on_done` NỔ Ở CUỐI cho MỌI câu — đúng `giong_vieneu._xong_het`.
            if on_done:
                for i in range(len(texts)):
                    on_done(i)
        ghi.nhip_lan.append(len(ghi.nhip()) - _truoc)
        # Lượt ĐẦU cho vài câu HỎNG -> `build_recap_track` đi tiếp lượt VÉT
        # (chỗ gọi thứ 2) rồi GIỌNG DỰ PHÒNG (chỗ gọi thứ 3).
        if dem["n"] == 1 and hong_lan_dau > 0:
            return ([False] * min(hong_lan_dau, len(texts))
                    + [True] * max(0, len(texts) - hong_lan_dau),
                    [[] for _ in texts])
        if dem["n"] == 2 and hong_lan_dau > 0:
            return [False] * len(texts), [[] for _ in texts]
        return [True] * len(texts), [[] for _ in texts]

    return _gia


def _fit_gia(src, dst_wav, window, tempo_max=1.28):
    Path(dst_wav).parent.mkdir(parents=True, exist_ok=True)
    Path(dst_wav).write_bytes(b"\0" * 16)
    d = max(0.5, float(window) - 0.2)
    return (d, d, 1.0)


def _va_ffmpeg():
    """Vá MỌI hàm đụng ffmpeg/mạng của `build_recap_track` bằng bản GIẢ."""
    cu = {}
    for ten, moi in (
        ("probe_duration", lambda p: 2.0),
        ("_fit_recap_chunk", _fit_gia),
        ("_detect_speech_segments", lambda w, t, **k: [(0.0, float(t))]),
        ("_stt_part_words", lambda w, l, **k: None),
        ("_mix_track", lambda c, t, o: Path(o).write_bytes(b"\0" * 16)),
        ("measure_loudness", lambda p, start=0.0, dur=0.0: None),
        ("_loudnorm_wav", lambda w, i_lufs=-16.0: None),
        ("_gain_wav", lambda w, gain_db=0.0, factor=1.0: None),
    ):
        cu[ten] = getattr(dubbing, ten)
        setattr(dubbing, ten, moi)
    return cu


def _tra(cu):
    for k, v in cu.items():
        setattr(dubbing, k, v)


def parts_mau(n: int = N_CAU) -> list[dict]:
    """Part narrate cách nhau 6 s, khung 4 s (đủ rộng cho `b - a >= 0.8`)."""
    return [{"start": i * 6.0, "end": i * 6.0 + 4.0, "mode": "narrate",
             "text": f"Doan thuyet minh so {i} du dai de do nhip"}
            for i in range(n)]


def chay_recap(ghi: Ghi, voice: str = "vi-VN-HoaiMyNeural",
               xen_ke: bool = False, hong_lan_dau: int = 0,
               kieu_edge: bool = False):
    cu_synth = dubbing._synth_all_words
    cu = _va_ffmpeg()
    dubbing._synth_all_words = _may_doc_gia(ghi, xen_ke, hong_lan_dau,
                                            kieu_edge)
    try:
        return dubbing.build_recap_track(
            parts_mau(), [(0.0, N_CAU * 6.0 + 4.0)], voice, "vi",
            HOP / "recap.wav", on_progress=ghi)
    finally:
        dubbing._synth_all_words = cu_synth
        _tra(cu)


# ══════════════════════════════════════════════════════════════════════════
_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def dem_lui_chu(moi) -> list[tuple[str, str]]:
    """Dãy CHỮ có lùi không: phần số trong chữ giảm so với lần trước."""
    lui, cao, mau = [], -1.0, 0
    truoc = ""
    for _p, m, _t in moi:
        g = _RE.search(m)
        if not g:
            continue
        a, b = int(g.group(1)), int(g.group(2))
        if b <= 0:
            continue
        if b != mau:            # đổi mẫu số = đổi bộ đếm -> đếm lại
            mau, cao, truoc = b, -1.0, ""
        f = a / b
        if f < cao - 1e-9:
            lui.append((truoc, m))
        cao = max(cao, f)
        truoc = m
    return lui


def lui_theo_buoc(ghi) -> list[tuple[str, str]]:
    """Như `dem_lui_chu` nhưng CẮT dãy theo TỪNG lượt gọi máy đọc.

    Bất biến là *"phần số trong chữ không giảm TRONG CÙNG MỘT BƯỚC"*. Lượt
    VÉT và lượt GIỌNG DỰ PHÒNG là hai bước KHÁC, mỗi bước đếm lại từ 1 trên
    khúc thanh RIÊNG — gộp cả ba lượt vào một dãy rồi kêu "lùi" là bộ đo
    đang chấm sai mệnh đề.
    """
    moc = list(ghi.moc_lan) + [len(ghi.moi)]
    ra = []
    for k in range(len(moc) - 1):
        ra += dem_lui_chu(ghi.moi[moc[k]:moc[k + 1]])
    return ra


def dem_lui_p(moi) -> list[tuple[float, float]]:
    tho = [p for p, _m, _t in moi]
    return [(tho[i], tho[i + 1]) for i in range(len(tho) - 1)
            if tho[i + 1] < tho[i] - 1e-9]


def in_bang(ten: str, ghi: Ghi) -> None:
    nh = ghi.nhip()
    gt = [p for p, _ in nh]
    print(f"\n── {ten}")
    print(f"   caller có truyền `on_msg` xuống máy đọc: "
          f"{'CÓ' if ghi.co_on_msg else 'KHÔNG'}"
          + (f"   (từng lượt gọi: {ghi.tung_lan} · nhịp {ghi.nhip_lan})"
             if len(ghi.tung_lan) > 1 else ""))
    print(f"   {len(ghi.moi)} lời báo thô · {len(nh)} NHỊP trong lúc đang đọc")
    if gt:
        print("   nhịp: " + " ".join(so(x) for x in gt))
    lui_p = dem_lui_p(ghi.moi)
    lui_c = lui_theo_buoc(ghi) if ghi.moc_lan else dem_lui_chu(ghi.moi)
    print(f"   TỤT tỉ lệ p trên dòng thô: {len(lui_p)}"
          + (f" (tệ nhất {so(lui_p[0][0])} -> {so(lui_p[0][1])})"
             if lui_p else ""))
    print(f"   LÙI phần SỐ trong CHỮ (trong CÙNG một bước): {len(lui_c)}")
    for a, b in lui_c[:4]:
        print(f"      «{a}»  ->  «{b}»")


print("=" * 74)
print("ĐO NHỊP — ĐƯỜNG RECAP (dubbing.build_recap_track) + ĐƯỜNG BƯỚC 5")
print("=" * 74)

# ── 1. Đường RECAP với máy đọc gộp cả loạt ──────────────────────────────
g1 = Ghi()
loi = ""
try:
    chay_recap(g1)
except Exception as e:  # noqa: BLE001
    loi = f"{type(e).__name__}: {e}"
in_bang("RECAP · máy đọc GỘP CẢ LOẠT (on_done nổ ở cuối)", g1)
if loi:
    print(f"   NÉM: {loi}")

# Lời báo trong khoảng đọc [0,05 .. 0,65] — chỗ thanh đứng im
doc = [(p, m) for p, m, _t in g1.moi if 0.049 <= p <= 0.651]
print(f"   lời báo nằm trong khúc ĐỌC [0,05..0,65]: {len(doc)}")
for p, m in doc[:12]:
    print(f"      {so(p)}  {m}")

# ── 2. Đường RECAP, máy đọc XEN KẼ hai loại tin ─────────────────────────
g2 = Ghi()
loi2 = ""
try:
    chay_recap(g2, xen_ke=True)
except Exception as e:  # noqa: BLE001
    loi2 = f"{type(e).__name__}: {e}"
in_bang("RECAP · máy đọc XEN KẼ (on_msg và on_done đan nhau)", g2)
if loi2:
    print(f"   NÉM: {loi2}")

# ── 2b. Đường RECAP đi qua CẢ BA chỗ gọi (lượt VÉT + giọng dự phòng) ────
g2b = Ghi()
loi2b = ""
try:
    chay_recap(g2b, hong_lan_dau=3)
except Exception as e:  # noqa: BLE001
    loi2b = f"{type(e).__name__}: {e}"
in_bang("RECAP · 3 câu hỏng -> đi qua CẢ 3 chỗ gọi _synth_all_words", g2b)
if loi2b:
    print(f"   NÉM: {loi2b}")

# ── 2c. ĐỐI CHỨNG: hình dạng edge-tts (on_done từng câu, không on_msg) ──
g2c = Ghi()
try:
    chay_recap(g2c, kieu_edge=True)
except Exception as e:  # noqa: BLE001
    print(f"   NÉM: {e}")
in_bang("RECAP · ĐỐI CHỨNG hình dạng edge-tts (không gộp loạt)", g2c)
print("   DÃY CHỮ THÔ trong khúc đọc:")
for p, m, _t in g2c.moi[:8]:
    print(f"      {so(p)}  {m}")

# ── 3. Bước 5 `doc_ban_dich`, máy đọc XEN KẼ — nợ 2 ─────────────────────
def chay_buoc5(ghi: Ghi, xen_ke: bool = True):
    cu_synth = dubbing._synth_all_words
    cu_cat, cu_probe = tg.cat_le_loat, tg.probe_duration
    dubbing._synth_all_words = _may_doc_gia(ghi, xen_ke)
    tg.cat_le_loat = lambda f, o, d, tien_to="sach", moc_tu=None: (
        (Path(d).mkdir(parents=True, exist_ok=True), (list(f), {}))[1])
    tg.probe_duration = lambda p: 2.0
    try:
        texts = [f"Cau so {i} du dai de do" for i in range(N_CAU)]
        return tg.doc_ban_dich(texts, HOP / "b5", voice="vi-VN-HoaiMyNeural",
                               dich_sang="vi", on_progress=ghi)
    finally:
        dubbing._synth_all_words = cu_synth
        tg.cat_le_loat, tg.probe_duration = cu_cat, cu_probe


g3 = Ghi()
loi3 = ""
try:
    chay_buoc5(g3, xen_ke=True)
except Exception as e:  # noqa: BLE001
    loi3 = f"{type(e).__name__}: {e}"
in_bang("BƯỚC 5 doc_ban_dich · máy đọc XEN KẼ", g3)
if loi3:
    print(f"   NÉM: {loi3}")
print("   DÃY CHỮ THÔ:")
for p, m, t in g3.moi:
    print(f"      {so(p)}  {'nhịp' if t else '    '}  {m}")

g4 = Ghi()
try:
    chay_buoc5(g4, xen_ke=False)
except Exception as e:  # noqa: BLE001
    print(f"   NÉM: {e}")
in_bang("BƯỚC 5 doc_ban_dich · máy đọc GỘP CẢ LOẠT (đối chứng)", g4)
print("   DÃY CHỮ THÔ:")
for p, m, t in g4.moi:
    print(f"      {so(p)}  {'nhịp' if t else '    '}  {m}")

shutil.rmtree(HOP, ignore_errors=True)
print("\n" + "=" * 74)
