# -*- coding: utf-8 -*-
"""CỔNG 90 — NHỊP TIẾN TRÌNH LÚC MÁY ĐỌC **GỘP CẢ LOẠT**.

MÓN NỢ NÀY GÂY RA MỘT NGÀY MẤT LÒNG TIN (21/08/2026). Anh Hùng hỏi **4 LẦN**
*"nó vẫn dừng ở 62% BƯỚC 5, có lỗi không, rà soát lại đi"* và **suýt bấm Dừng**,
mất hơn một tiếng máy chạy ĐÚNG.

GỐC: MỌI máy đọc gộp-cả-loạt (VieNeu · Kokoro · Piper · ElevenLabs · Vbee ·
Chatterbox) đọc hết trong MỘT lượt gọi, nên `on_done` chỉ nổ Ở CUỐI -> thanh
tiến trình đứng chết ở đúng một con số 15-30 phút. Thông tin CÓ ĐỦ ở mọi tầng
(`giong_vieneu._MA_DOC` in `Doc cau N/M` MỖI CÂU · `_chay_vieneu` VỐN ĐÃ gọi
`on_msg`) rồi **bị bỏ đúng ở bước cuối** vì không ai truyền `on_msg` xuống.
Đã vá ở `a0062b6` (bước 5) và `d4968a6` (4b/4c + hàm chung `ty_le_tung_cau` /
`_nhac_tung_cau`). **NHƯNG KHÔNG CÓ CỔNG NÀO CANH** — người sau bỏ `on_msg` đi
thì không ai biết, đúng cái vừa xảy ra. Đây là cái cổng đó.

MỆNH ĐỀ TRUNG TÂM (MỤC 3 + MỤC 3b):
    **SÁU chỗ gọi TTS phải báo ÍT NHẤT 2 NHỊP KHÁC NHAU TRONG LÚC ĐANG ĐỌC,
    không phải chỉ ở cuối** — ba chỗ của `thay_giong.py` (`doc_ban_dich` bước
    5 · `rut_gon_vua_khung` 4b · `doc_nhanh_vua_khung` 4c, đường THAY GIỌNG)
    và **ba chỗ của `dubbing.build_recap_track`** (lượt đọc CHÍNH · lượt VÉT
    đoạn lỗi mạng · lượt GIỌNG DỰ PHÒNG, đường REUP THUYẾT MINH mà
    `m1_highlight._export_clip_impl` nhánh `is_recap` gọi).

BA CỬA CỦA `dubbing.py` LÀ NỢ CŨ CỦA CHÍNH CỔNG NÀY. Bản đầu chỉ canh
`thay_giong.py`, tức đúng cái bệnh vừa chữa vẫn sống nguyên ở đường recap mà
không cổng nào kêu. ĐO RA (`_do_nhip_recap.py`, máy đọc giả gộp cả loạt, GỌI
THẬT `build_recap_track`): cả ba lượt đều KHÔNG truyền `on_msg` -> **0 nhịp /
3 lượt gọi**; suốt lượt đọc (hàng phút với VieNeu · Kokoro · Chatterbox ·
Vbee · giọng ngoài) thanh đứng ở **5%** với đúng một dòng chữ.

MỆNH ĐỀ THỨ HAI (MỤC 1b · 2b · 6) — **PHẦN SỐ TRONG DÒNG CHỮ KHÔNG BAO GIỜ
GIẢM TRONG CÙNG MỘT BƯỚC.** Dãy tỉ lệ `p` đã được canh không lùi từ trước,
nhưng người dùng đọc CHỮ chứ không đọc số thực: máy đọc gộp cả loạt bắn
`Doc cau 1/6 … 6/6` qua `on_msg` rồi mới nổ `on_done` cho MỌI câu ở cuối
(`giong_vieneu._xong_het`), nên nơi gọi nào báo thêm `xong/N` sẽ hiện `6/6`
rồi **nhảy ngược về `1/6`**. Đo được **5 lần lùi** và tỉ lệ thô tụt
**1,0000 -> 0,1667** trên một lượt 6 câu. Nay `_done`/`_tts_done` đi QUA
`_nhac`, và `chu_khong_lui` kéo số lên cho khớp mốc cao nhất.

ĐÂY LÀ MỆNH ĐỀ VỀ **HÀNH VI**, KHÔNG PHẢI VỀ MẶT CHỮ. Cổng KHÔNG dừng ở chỗ
hỏi "mã có chữ `on_msg` không" — quét kiểu đó luôn có phép phá giữ nguyên mặt
chữ mà đổi nghĩa (bài học cổng 56d: `che_chu=` -> `che_chu=False` vẫn xanh).
Cách đo ĐÚNG, và là cách cổng này dùng: **giả lập một máy đọc GỘP CẢ LOẠT**
phát ra chuỗi `Doc cau 1/6` … `Doc cau 6/6` qua `on_msg`, GỌI THẬT cả ba hàm,
rồi BẮT từng lần `on_progress` được gọi. Bỏ `on_msg` -> máy đọc giả không có
ai để gọi -> **0 nhịp** -> HỎNG. Đổi thành hằng số `None` -> y hệt.

TIỀN ĐỊNH VÀ RẺ: KHÔNG gọi mạng · KHÔNG Groq · KHÔNG edge-tts · KHÔNG ffmpeg ·
KHÔNG nạp model. `dubbing._synth_all_words`, `cat_le_loat`, `probe_duration`,
`_rut_gon_loat` (lượt LLM) và mọi hàm đụng ffmpeg/Groq của `build_recap_track`
(`_fit_recap_chunk` · `_mix_track` · `_detect_speech_segments` ·
`_stt_part_words` · `measure_loudness` · `_loudnorm_wav` · `_gain_wav`) đều
được vá bằng bản GIẢ; BỐN hàm ĐANG TEST thì chạy THẬT, không mock.

CÒN MỘT CHỖ TỈ LỆ THÔ VẪN TỤT, CỐ Ý KHÔNG CHẤM — đọc kỹ kẻo sửa nhầm:
`doc_ban_dich` báo THẲNG `on_progress(0.95, "Cắt lề im lặng...")` sau khi nhịp
đã tới 1,0. Lời báo đó KHÔNG mang số nào nên bất biến CHỮ vẫn giữ, và nó là
một BƯỚC KHÁC (cắt lề, không phải đọc). MỤC 6 vẫn IN con số ra. Chấm nó là
cổng đỏ oan trên bản mã ĐÚNG, mà cổng đỏ oan thì người ta thôi đọc nó (bài
học cổng 41 và 47).

    .venv\\Scripts\\python -u _test_nhip_doc.py
"""
from __future__ import annotations

import ast
import atexit
import contextlib
import os
import re
import shutil
import sys
import traceback
from pathlib import Path

# Cổng chạy với stdout CHUYỂN HƯỚNG ra file (`_chay_hoi_quy.py`): không ép
# utf-8 thì dòng `print` tiếng Việt ĐẦU TIÊN nổ `UnicodeEncodeError`, cổng
# chết trong 0-1 giây và bị đổ oan cho bản vá đang làm.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except Exception:  # noqa: BLE001
        pass

# KHÔNG ghi cứng đường repo — chạy từ `git worktree` mà trỏ về repo chính là
# đang kiểm BẢN MÃ KHÁC (29 file test từng dính, cổng vẫn XANH).
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# Hộp cát nằm TRONG repo và mang tên khớp mẫu `_kq*/` của `.gitignore` nên
# không bao giờ làm bẩn `git status`; đặt trong `%TEMP%` thì lượt bị giết giữa
# chừng để lại rác trên máy anh Hùng (ổ C đã từng đầy 100%).
HOP = REPO / f"_kq_nhipdoc_{os.getpid()}"
shutil.rmtree(HOP, ignore_errors=True)
(HOP / "data").mkdir(parents=True, exist_ok=True)

# `atexit` chứ KHÔNG gọi thẳng ở cuối file: lượt THỬ PHÁ có phép làm cổng chết
# giữa đường, lúc đó dòng dọn ở cuối không bao giờ chạy (cổng 88 đo được 2 thư
# mục đọng lại trong repo vì đúng lỗi này).
atexit.register(lambda: shutil.rmtree(HOP, ignore_errors=True))

# Sandbox TRƯỚC khi `config` được nạp — không được đụng dữ liệu/QSettings thật.
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "studio.db")

import _test_guard  # noqa: E402  — chặn Explorer/trình phát + dọn rác lần trước

from app.core import dubbing  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

DAT = 0
HONG: list[str] = []


def ok(nhan: str, dieu_kien: bool, chi_tiet: str = "") -> bool:
    global DAT
    if dieu_kien:
        DAT += 1
        print(f"  ĐẠT  {nhan}")
    else:
        HONG.append(nhan)
        print(f"  HỎNG {nhan}   << {chi_tiet}")
    return bool(dieu_kien)


def so(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


# ══════════════════════════════════════════════════════════════════════════
# MÁY ĐỌC GIẢ — GỘP CẢ LOẠT, ĐÚNG HÌNH DẠNG CỦA `giong_vieneu.doc_loat`
# ══════════════════════════════════════════════════════════════════════════
#
# 6 lời báo, cố ý gồm ĐỦ 3 hình dạng đã gặp ngoài đời:
#   * lời KHÔNG CÓ SỐ ở ĐẦU (nạp model) — lúc này chưa đọc câu nào;
#   * số NHẢY CÓC 2 -> 4 -> 6 (không tuần tự!). Đây là cái RĂNG chống bản vá
#     giả: ai thay `ty_le_tung_cau` bằng một bộ ĐẾM nội bộ thì tỉ lệ ra sai
#     chỗ ngay, vì bộ đếm không biết máy đọc vừa nhảy mấy câu;
#   * lời KHÔNG CÓ SỐ ở GIỮA — dấu hiệu "còn sống", phải được chuyển tiếp và
#     KHÔNG được kéo thanh về 0.
LOI_NHAN = [
    "Nap model doc...",
    "Doc cau 1/6",
    "Doc cau 2/6",
    "Dang doc cau tiep...",
    "Doc cau 4/6",
    "Doc cau 6/6",
]
KHONG_SO_GIUA = LOI_NHAN[3]
#: Tỉ lệ tương ứng của từng lời báo (`None` = lời KHÔNG CÓ SỐ). Máy đọc giả
#: dựng lại đúng dãy đó cho lượt đọc có SỐ CÂU KHÁC — lượt VÉT của đường
#: recap chỉ đọc lại mấy câu HỎNG, để nguyên `/6` là ra `Doc cau 6/3` (mẫu số
#: bịa) rồi chấm nhầm. Ba hàm của `thay_giong.py` thì lượt nào cũng ĐÚNG 6 câu
#: (đã đo), nên chuỗi `/6` mà mục 3 tra vẫn ra y hệt.
TY_LE = [None, 1 / 6, 2 / 6, None, 4 / 6, 1.0]
N_CAU = 6
TONG = 18.0


def cau_mau(n: int = N_CAU) -> list[dict]:
    """Câu cách nhau 3 s, dài 2 s -> `khung_cho_phep` ≈ 2,88 s."""
    return [{"start": i * 3.0, "end": i * 3.0 + 2.0} for i in range(n)]


def tao_file(thu_muc: Path, n: int) -> list[str]:
    thu_muc.mkdir(parents=True, exist_ok=True)
    ra = []
    for i in range(n):
        p = thu_muc / f"cu_{i:04d}.mp3"
        p.write_bytes(b"\0" * 16)
        ra.append(str(p))
    return ra


class Ghi:
    """Bắt TỪNG lần `on_progress` được gọi, có ĐÁNH DẤU nguồn.

    `tu_nhip` do chính máy đọc giả bật/tắt quanh lời gọi `on_msg`, nên phép
    phân loại KHÔNG phụ thuộc vào nội dung chữ (đổi lời nhắn không làm cổng
    đỏ oan). Đây là cách duy nhất tách được nhịp-trong-lúc-đọc khỏi các lời
    báo trực tiếp của chính hàm.
    """

    def __init__(self, nem_khi: tuple = ()) -> None:
        self.moi: list[tuple] = []
        self.tu_nhip = False
        self.nem_khi = tuple(nem_khi)
        self.so_nem = 0
        #: `on_msg` CÓ được truyền xuống không — ghi RIÊNG TỪNG lượt gọi máy
        #: đọc. Đường recap gọi `_synth_all_words` tới BA lần (đọc chính ·
        #: lượt VÉT · giọng dự phòng); hỏi mỗi lượt cuối là bỏ lọt hai lượt kia.
        self.tung_lan: list[bool] = []
        #: số nhịp bắt được ở TỪNG lượt gọi
        self.nhip_lan: list[int] = []
        #: chỉ số trong `moi` lúc MỖI lượt gọi bắt đầu -> cắt dãy chữ theo
        #: BƯỚC (bất biến "chữ không lùi" là bất biến TRONG MỘT bước)
        self.moc_lan: list[int] = []

    def __call__(self, p, m="") -> None:
        self.moi.append((float(p), str(m), self.tu_nhip))
        if self.nem_khi and str(m) in self.nem_khi:
            self.so_nem += 1
            raise RuntimeError("on_progress CỦA CALLER ném (cố ý)")

    def nhip(self) -> list[tuple]:
        return [(p, m) for p, m, t in self.moi if t]

    def gia_tri(self) -> list[float]:
        return [p for p, _ in self.nhip()]

    def tra(self, msg: str):
        for p, m in self.nhip():
            if m == msg:
                return p
        return None


def _may_doc_gia(ghi: Ghi, hong_lan_dau: int = 0, kieu_edge: bool = False):
    """`dubbing._synth_all_words` GIẢ: đọc CẢ LOẠT trong MỘT lượt gọi.

    `hong_lan_dau` > 0 -> lượt ĐẦU trả `False` cho mấy câu đầu, để đường recap
    đi tiếp lượt VÉT rồi lượt GIỌNG DỰ PHÒNG (chỗ gọi thứ 2 và thứ 3).
    `kieu_edge=True` -> hình dạng edge-tts (KHÔNG gọi `on_msg` lần nào,
    `on_done` nổ TỪNG CÂU) — dùng làm ĐỐI CHỨNG chống hồi quy.
    """
    dem = {"n": 0}

    async def _gia(texts, voice, paths, on_done=None, rate="+0%",
                   pitch="+0Hz", lang="", el_lui=True, on_msg=None, **kw):
        dem["n"] += 1
        ghi.tung_lan.append(on_msg is not None)
        ghi.moc_lan.append(len(ghi.moi))
        _n_truoc = len(ghi.nhip())
        ghi.tu_nhip = False
        for p in paths:
            pp = Path(p)
            pp.parent.mkdir(parents=True, exist_ok=True)
            pp.write_bytes(b"\0" * 16)
        # Mẫu số theo ĐÚNG số câu lượt này đọc — lượt VÉT chỉ đọc lại mấy câu
        # hỏng, để nguyên `/6` là dựng ra `Doc cau 6/3` (mẫu số bịa).
        _n = max(1, len(texts))
        nhan = [LOI_NHAN[k] if f is None
                else f"Doc cau {max(1, min(_n, int(round(f * _n))))}/{_n}"
                for k, f in enumerate(TY_LE)]
        if not kieu_edge:
            for m in nhan:
                if on_msg:
                    ghi.tu_nhip = True
                    try:
                        on_msg(m)
                    finally:
                        ghi.tu_nhip = False
        # `on_done` NỔ Ở CUỐI cho MỌI câu — đúng `giong_vieneu._xong_het`,
        # tức đúng cái đã làm thanh đứng chết. Giữ nguyên hình dạng đó thì
        # MỤC 6 mới đo được phần còn sót.
        if on_done:
            for i in range(len(texts)):
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass
        ghi.nhip_lan.append(len(ghi.nhip()) - _n_truoc)
        if hong_lan_dau > 0 and dem["n"] == 1:
            return ([False] * min(hong_lan_dau, len(texts))
                    + [True] * max(0, len(texts) - hong_lan_dau),
                    [[] for _ in texts])
        if hong_lan_dau > 0 and dem["n"] == 2:   # lượt VÉT vẫn hỏng -> dự phòng
            return [False] * len(texts), [[] for _ in texts]
        return [True] * len(texts), [[] for _ in texts]

    return _gia


def _cat_le_gia(files, ok_, out_dir, tien_to="sach", moc_tu=None):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    return list(files), {}


@contextlib.contextmanager
def may_doc_gia(ghi: Ghi):
    cu = (dubbing._synth_all_words, tg.cat_le_loat, tg.probe_duration,
          tg._rut_gon_loat)
    dubbing._synth_all_words = _may_doc_gia(ghi)
    tg.cat_le_loat = _cat_le_gia
    tg.probe_duration = lambda p: 9.0        # 9,0 s / khung 2,88 s -> 3,13x
    tg._rut_gon_loat = lambda muc, nn: [f"Ngan {m['i']}" for m in muc]
    try:
        yield
    finally:
        (dubbing._synth_all_words, tg.cat_le_loat, tg.probe_duration,
         tg._rut_gon_loat) = cu


# ── Ba chỗ gọi TTS, GỌI THẬT (không mock hàm đang test) ──────────────────
def chay_buoc5(ghi: Ghi):
    texts = [f"Cau so {i} du dai de do" for i in range(N_CAU)]
    return tg.doc_ban_dich(texts, HOP / "b5", voice="vi-VN-HoaiMyNeural",
                           dich_sang="vi", on_progress=ghi)


def chay_4b(ghi: Ghi):
    texts = [f"Cau so {i} du dai de do" for i in range(N_CAU)]
    files = tao_file(HOP / "in4b", N_CAU)
    tts = {"files": files, "ok": [True] * N_CAU,
           "moc_tu": [[] for _ in range(N_CAU)]}
    return tg.rut_gon_vua_khung(cau_mau(), texts, tts, TONG, HOP / "b4b",
                                "vi", voice="vi-VN-HoaiMyNeural",
                                vong_toi_da=1, on_progress=ghi)


def chay_4c(ghi: Ghi):
    texts = [f"Cau so {i} du dai de do" for i in range(N_CAU)]
    files = tao_file(HOP / "in4c", N_CAU)
    return tg.doc_nhanh_vua_khung(cau_mau(), texts, files, [True] * N_CAU,
                                  TONG, HOP / "b4c", "vi",
                                  voice="vi-VN-HoaiMyNeural",
                                  moc_tu=[[] for _ in range(N_CAU)],
                                  on_progress=ghi)


BA_CHO = [
    ("bước 5  doc_ban_dich", chay_buoc5),
    ("bước 4b rut_gon_vua_khung", chay_4b),
    ("bước 4c doc_nhanh_vua_khung", chay_4c),
]


# ══════════════════════════════════════════════════════════════════════════
# BA CỬA CÒN LẠI — `dubbing.build_recap_track` (ĐƯỜNG REUP THUYẾT MINH)
# ══════════════════════════════════════════════════════════════════════════
#
# `m1_highlight._export_clip_impl` nhánh `is_recap` gọi hàm này để dựng track
# giọng AI kể. Nó có ĐÚNG 3 chỗ gọi `_synth_all_words`: lượt đọc CHÍNH · lượt
# VÉT các đoạn lỗi mạng · lượt GIỌNG DỰ PHÒNG. Trước bản vá, ĐO ĐƯỢC cả ba
# đều KHÔNG truyền `on_msg` -> **0 nhịp / 3 lượt gọi**, thanh đứng ở 5% suốt
# lượt đọc (`_do_nhip_recap.py`).
#
# Ffmpeg/Groq bị vá bằng bản GIẢ — `build_recap_track` thì chạy THẬT.
def _fit_gia(src, dst_wav, window, tempo_max=1.28):
    Path(dst_wav).parent.mkdir(parents=True, exist_ok=True)
    Path(dst_wav).write_bytes(b"\0" * 16)
    d = max(0.5, float(window) - 0.2)
    return (d, d, 1.0)


_VA_RECAP = (
    ("probe_duration", lambda p: 2.0),
    ("_fit_recap_chunk", _fit_gia),
    ("_detect_speech_segments", lambda w, t, **k: [(0.0, float(t))]),
    ("_stt_part_words", lambda w, l, **k: None),      # noqa: E741
    ("_mix_track", lambda c, t, o: Path(o).write_bytes(b"\0" * 16)),
    ("measure_loudness", lambda p, start=0.0, dur=0.0: None),
    ("_loudnorm_wav", lambda w, i_lufs=-16.0: None),
    ("_gain_wav", lambda w, gain_db=0.0, factor=1.0: None),
)


def parts_mau(n: int = N_CAU) -> list[dict]:
    """Part narrate cách nhau 6 s, khung 4 s (thoả `b - a >= 0.8`)."""
    return [{"start": i * 6.0, "end": i * 6.0 + 4.0, "mode": "narrate",
             "text": f"Doan thuyet minh so {i} du dai de do nhip"}
            for i in range(n)]


def chay_recap(ghi: Ghi, hong_lan_dau: int = 0, kieu_edge: bool = False):
    cu = {t: getattr(dubbing, t) for t, _ in _VA_RECAP}
    cu_synth = dubbing._synth_all_words
    for t, f in _VA_RECAP:
        setattr(dubbing, t, f)
    dubbing._synth_all_words = _may_doc_gia(ghi, hong_lan_dau, kieu_edge)
    try:
        return dubbing.build_recap_track(
            parts_mau(), [(0.0, N_CAU * 6.0 + 4.0)], "vi-VN-HoaiMyNeural",
            "vi", HOP / "recap.wav", on_progress=ghi)
    finally:
        dubbing._synth_all_words = cu_synth
        for t, f in cu.items():
            setattr(dubbing, t, f)


def lui_chu(moi) -> list[tuple[str, str]]:
    """Các lần phần SỐ trong CHỮ đi LÙI (đổi mẫu số = đổi bộ đếm -> đếm lại).

    Bộ dò của cổng đọc bằng regex RIÊNG, KHÔNG gọi `tg.ty_le_tung_cau` — dùng
    chính hàm đang test làm thước đo thì gỡ hàm đó đi cổng vẫn xanh.
    """
    lui, cao, mau, truoc = [], -1.0, 0, ""
    for _p, m, _t in moi:
        g = re.search(r"(\d+)\s*/\s*(\d+)", str(m))
        if not g:
            continue
        a, b = int(g.group(1)), int(g.group(2))
        if b <= 0:
            continue
        if b != mau:
            mau, cao, truoc = b, -1.0, ""
        f = a / b
        if f < cao - 1e-9:
            lui.append((truoc, str(m)))
        cao = max(cao, f)
        truoc = str(m)
    return lui


def lui_theo_buoc(ghi: Ghi) -> list[tuple[str, str]]:
    """Như `lui_chu` nhưng CẮT dãy theo TỪNG lượt gọi máy đọc.

    Bất biến là *"phần số trong chữ không giảm TRONG CÙNG MỘT BƯỚC"*. Lượt
    VÉT và lượt GIỌNG DỰ PHÒNG là hai bước KHÁC, mỗi bước đếm lại từ 1 trên
    khúc thanh RIÊNG của nó — gộp cả ba lượt vào một dãy rồi kêu "lùi" là bộ
    đo đang chấm SAI MỆNH ĐỀ (đã đo: gộp ra 3 lần lùi giả).
    """
    moc = list(ghi.moc_lan) + [len(ghi.moi)]
    ra: list[tuple[str, str]] = []
    for k in range(len(moc) - 1):
        ra += lui_chu(ghi.moi[moc[k]:moc[k + 1]])
    return ra


# ══════════════════════════════════════════════════════════════════════════
print("=" * 74)
print("CỔNG 90 — NHỊP TIẾN TRÌNH CỦA MÁY ĐỌC GỘP CẢ LOẠT")
print("=" * 74)

# ══ MỤC 1 — `ty_le_tung_cau` đọc SỐ THẬT, đầu vào xấu -> 0,0 và KHÔNG NÉM ══
print("\n══ MỤC 1. ty_le_tung_cau ══")
try:
    v = tg.ty_le_tung_cau("Doc cau 12/59")
    ok("'Doc cau 12/59' -> 0,2034", abs(v - 12 / 59) < 1e-9, so(v))
    v = tg.ty_le_tung_cau("Doc cau 59/59")
    ok("'Doc cau 59/59' -> 1,0", abs(v - 1.0) < 1e-9, so(v))
    v = tg.ty_le_tung_cau("Doc cau 1/6")
    ok("'Doc cau 1/6' -> 0,1667", abs(v - 1 / 6) < 1e-9, so(v))
    v = tg.ty_le_tung_cau("Doc cau 70/59")
    ok("số vượt mẫu -> kẹp về 1,0 (không quá 100%)", abs(v - 1.0) < 1e-9,
       so(v))
except Exception as e:  # noqa: BLE001
    ok("ty_le_tung_cau chạy được", False, f"{type(e).__name__}: {e}")

# Đầu vào XẤU: phải ra 0,0 và TUYỆT ĐỐI không ném — hàm này nằm trên đường
# báo tiến trình, nó nổ là giết cả lượt đọc (bản vá HIỂN THỊ đi làm hỏng việc
# THẬT).
XAU = [(None, "None"), ("", "chuỗi rỗng"), ("5/0", "'5/0' chia 0"),
       ("abc", "'abc'"), ("N/M", "'N/M'"), ("Doc cau", "thiếu số hẳn"),
       (12, "số nguyên 12"), ([], "list rỗng")]
for gt, nhan in XAU:
    try:
        r = tg.ty_le_tung_cau(gt)  # type: ignore[arg-type]
        ok(f"đầu vào xấu {nhan} -> 0,0 · KHÔNG ném", r == 0.0, so(r))
    except Exception as e:  # noqa: BLE001
        ok(f"đầu vào xấu {nhan} -> 0,0 · KHÔNG ném", False,
           f"NÉM {type(e).__name__}: {e}")

# ══ MỤC 1b — `mau_tung_cau` + `chu_khong_lui` (nợ 2: CHỮ không đi lùi) ══
print("\n══ MỤC 1b. chu_khong_lui — phần SỐ trong chữ không bao giờ giảm ══")
ok("mau_tung_cau('Doc cau 12/59') -> 59", tg.mau_tung_cau("Doc cau 12/59") == 59,
   str(tg.mau_tung_cau("Doc cau 12/59")))
ok("mau_tung_cau lời KHÔNG CÓ SỐ -> 0", tg.mau_tung_cau("Nap model...") == 0,
   str(tg.mau_tung_cau("Nap model...")))
ok("mau_tung_cau 'N/M' (không phải số) -> 0", tg.mau_tung_cau("N/M") == 0,
   str(tg.mau_tung_cau("N/M")))
ok("mau_tung_cau mẫu 0 -> 0", tg.mau_tung_cau("5/0") == 0,
   str(tg.mau_tung_cau("5/0")))

r = tg.chu_khong_lui("Đang đọc câu 1/6...", 1.0, 6)
ok("kéo '1/6' lên '6/6' khi mốc đã tới 1,0", r == "Đang đọc câu 6/6...", r)
r = tg.chu_khong_lui("Thu giọng đoạn 2/6...", 4 / 6, 6)
ok("kéo '2/6' lên '4/6' khi mốc là 4/6", r == "Thu giọng đoạn 4/6...", r)
r = tg.chu_khong_lui("Doc cau 6/6", 0.5, 6)
ok("KHÔNG hạ số đang cao hơn mốc", r == "Doc cau 6/6", r)
r = tg.chu_khong_lui("Doc cau 3/6", 3 / 6, 6)
ok("đúng bằng mốc -> giữ nguyên", r == "Doc cau 3/6", r)
# CHỐT HẸP: chỉ viết đè khi CÙNG mẫu số. Lời báo của cửa khác đi chung đường
# này (ElevenLabs, Gemini) có thể mang con số chẳng liên quan bộ đếm câu.
r = tg.chu_khong_lui("🎧 ElevenLabs: còn 2/5 tài khoản", 1.0, 6)
ok("KHÁC mẫu số -> KHÔNG đụng vào (không sửa chỗ không hỏng)",
   r == "🎧 ElevenLabs: còn 2/5 tài khoản", r)
r = tg.chu_khong_lui("Đang đọc câu 1/6...", 1.0, 0)
ok("chưa có bộ đếm (mau=0) -> giữ nguyên", r == "Đang đọc câu 1/6...", r)
r = tg.chu_khong_lui("Nap model doc...", 1.0, 6)
ok("lời KHÔNG CÓ SỐ -> giữ nguyên", r == "Nap model doc...", r)
r = tg.chu_khong_lui("Doc cau 9/6", 1.0, 6)
ok("số > mẫu (dữ liệu lạ) -> KHÔNG đụng", r == "Doc cau 9/6", r)
for gt, nhan in [(None, "None"), ("", "chuỗi rỗng"), (12, "số nguyên 12"),
                 ([], "list rỗng"), ("5/0", "'5/0' chia 0")]:
    try:
        tg.chu_khong_lui(gt, 1.0, 6)      # type: ignore[arg-type]
        ok(f"chu_khong_lui đầu vào xấu {nhan} -> KHÔNG ném", True, "")
    except Exception as e:  # noqa: BLE001
        ok(f"chu_khong_lui đầu vào xấu {nhan} -> KHÔNG ném", False,
           f"NÉM {type(e).__name__}: {e}")

# ── TỰ KIỂM BỘ DÒ `lui_chu`: nó phải KÊU đúng dãy hỏng, và IM đúng dãy tốt ──
_HONG = [(0.0, "Doc cau 6/6", True), (0.0, "Đang đọc câu 1/6...", False)]
_TOT = [(0.0, "Doc cau 1/6", True), (0.0, "Đang đọc câu 6/6...", False)]
_KHAC_MAU = [(0.0, "Doc cau 6/6", True), (0.0, "còn 1/5 key", False)]
ok("TỰ KIỂM BỘ DÒ · dãy 6/6 -> 1/6 bị KÊU", len(lui_chu(_HONG)) == 1,
   str(lui_chu(_HONG)))
ok("TỰ KIỂM BỘ DÒ · dãy 1/6 -> 6/6 KHÔNG bị kêu", not lui_chu(_TOT),
   str(lui_chu(_TOT)))
ok("TỰ KIỂM BỘ DÒ · đổi mẫu số -> đếm lại, KHÔNG kêu oan",
   not lui_chu(_KHAC_MAU), str(lui_chu(_KHAC_MAU)))

# ══ MỤC 2 — `_nhac_tung_cau` ở mức ĐƠN VỊ ══
print("\n══ MỤC 2. _nhac_tung_cau (đơn vị) ══")
g2 = Ghi()
g2.tu_nhip = True
nhac = tg._nhac_tung_cau(g2, lambda: 0.0)
for m in LOI_NHAN:
    nhac(m)
gt2 = g2.gia_tri()
ok("mọi lời báo đều được chuyển tiếp (6/6)", len(gt2) == 6, str(len(gt2)))
ok("dãy KHÔNG BAO GIỜ tụt lùi",
   all(gt2[i] <= gt2[i + 1] + 1e-9 for i in range(len(gt2) - 1)),
   " ".join(so(x) for x in gt2))
ok("có >= 2 giá trị KHÁC NHAU", len(set(gt2)) >= 2, str(sorted(set(gt2))))
v_giua = g2.tra(KHONG_SO_GIUA)
ok("lời KHÔNG CÓ SỐ ở giữa: vẫn báo, KHÔNG kéo thanh về 0",
   v_giua is not None and v_giua >= 2 / 6 - 1e-9,
   f"nhận {so(v_giua) if v_giua is not None else 'KHÔNG BÁO'}")

# `moc_lui()` ném thì hàm nhịp vẫn phải im lặng đi tiếp.
g2b = Ghi()
g2b.tu_nhip = True


def _moc_nem() -> float:
    raise RuntimeError("mốc lùi ném (cố ý)")


try:
    nhac_b = tg._nhac_tung_cau(g2b, _moc_nem)
    nhac_b("Nap model doc...")
    nhac_b("Doc cau 3/6")
    ok("`moc_lui()` ném -> KHÔNG lọt ra ngoài", True,
       "")
    ok("`moc_lui()` ném -> vẫn báo đủ 2 nhịp", len(g2b.gia_tri()) == 2,
       str(len(g2b.gia_tri())))
except Exception as e:  # noqa: BLE001
    ok("`moc_lui()` ném -> KHÔNG lọt ra ngoài", False,
       f"{type(e).__name__}: {e}")
    ok("`moc_lui()` ném -> vẫn báo đủ 2 nhịp", False, "không chạy tới")

# `on_progress` của caller ném thì hàm nhịp cũng phải nuốt.
g2c = Ghi(nem_khi=tuple(LOI_NHAN))
g2c.tu_nhip = True
try:
    nhac_c = tg._nhac_tung_cau(g2c, lambda: 0.0)
    for m in LOI_NHAN:
        nhac_c(m)
    ok("`on_progress` của caller NÉM -> hàm nhịp KHÔNG ném ra ngoài", True, "")
    ok("`on_progress` ném vẫn được gọi đủ 6 lần (không bỏ cuộc giữa chừng)",
       g2c.so_nem == 6, str(g2c.so_nem))
except Exception as e:  # noqa: BLE001
    ok("`on_progress` của caller NÉM -> hàm nhịp KHÔNG ném ra ngoài", False,
       f"{type(e).__name__}: {e}")
    ok("`on_progress` ném vẫn được gọi đủ 6 lần", False, "không chạy tới")

# Khúc thanh: mọi nhịp phải nằm gọn trong [dau, dau+rong] — tràn ra là nhịp
# của bước này đè lên ô của bước sau.
g2d = Ghi()
g2d.tu_nhip = True
nhac_d = tg._nhac_tung_cau(g2d, lambda: 0.0, dau=0.2, rong=0.6)
for m in LOI_NHAN:
    nhac_d(m)
gt2d = g2d.gia_tri()
ok("nhịp nằm gọn trong khúc [dau, dau+rong]",
   all(0.2 - 1e-9 <= x <= 0.8 + 1e-9 for x in gt2d),
   " ".join(so(x) for x in gt2d))

# ══ MỤC 2b — HAI NGUỒN qua CÙNG một `_nhac`: chữ KHÔNG được nhảy ngược ══
print("\n══ MỤC 2b. hai nguồn (nhịp + xong/N) qua CÙNG một _nhac ══")
g2e = Ghi()
g2e.tu_nhip = True
_xong = {"n": 0}
nhac_e = tg._nhac_tung_cau(g2e, lambda: _xong["n"] / N_CAU)
for m in LOI_NHAN:                      # máy đọc gộp cả loạt: nhịp trước...
    nhac_e(m)
for _k in range(N_CAU):                 # ...rồi `on_done` nổ CHO MỌI CÂU ở cuối
    _xong["n"] += 1
    nhac_e(f"Đang đọc câu {_xong['n']}/{N_CAU}...")
gt2e = [p for p, _m, _t in g2e.moi]
ok("hai nguồn -> dãy tỉ lệ KHÔNG tụt",
   all(gt2e[i] <= gt2e[i + 1] + 1e-9 for i in range(len(gt2e) - 1)),
   " ".join(so(x) for x in gt2e))
_l2e = lui_chu(g2e.moi)
ok("hai nguồn -> phần SỐ trong CHỮ KHÔNG lùi lần nào", not _l2e,
   f"{len(_l2e)} lần, đầu tiên {_l2e[0] if _l2e else ''}")
ok("lời `xong/N` bắn sau khi nhịp đã tới 1,0 -> hiện `6/6`",
   all("6/6" in m for _p, m, _t in g2e.moi[len(LOI_NHAN):]),
   " | ".join(m for _p, m, _t in g2e.moi[len(LOI_NHAN):][:3]))

# ══ MỤC 3 — MỆNH ĐỀ TRUNG TÂM: ba chỗ gọi TTS, chạy THẬT ══
print("\n══ MỤC 3. BA CHỖ GỌI TTS phải báo >= 2 nhịp KHÁC NHAU LÚC ĐANG ĐỌC ══")
GHI_CHO: dict = {}
for ten, ham in BA_CHO:
    g = Ghi()
    loi = ""
    try:
        with may_doc_gia(g):
            ham(g)
    except Exception as e:  # noqa: BLE001
        loi = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    GHI_CHO[ten] = g
    gt = g.gia_tri()
    print(f"  · {ten}: {len(g.moi)} lời báo, {len(gt)} nhịp -> "
          + " ".join(so(x) for x in gt))
    ok(f"[{ten}] chạy xong không ném", loi == "", loi)
    ok(f"[{ten}] báo >= 2 NHỊP trong lúc đang đọc", len(gt) >= 2,
       f"chỉ {len(gt)} nhịp — `on_msg` KHÔNG được truyền xuống?")
    ok(f"[{ten}] các nhịp KHÁC NHAU (>= 2 giá trị)", len(set(gt)) >= 2,
       str(sorted(set(gt))))
    ok(f"[{ten}] dãy nhịp KHÔNG BAO GIỜ tụt lùi",
       all(gt[i] <= gt[i + 1] + 1e-9 for i in range(len(gt) - 1)),
       " ".join(so(x) for x in gt))
    vg = g.tra(KHONG_SO_GIUA)
    v2 = g.tra("Doc cau 2/6")
    ok(f"[{ten}] lời không-có-số vẫn được chuyển tiếp (dấu hiệu còn sống)",
       vg is not None, "KHÔNG BÁO")
    ok(f"[{ten}] lời không-có-số KHÔNG kéo thanh về 0",
       vg is not None and v2 is not None and vg >= v2 - 1e-9,
       f"sau {so(v2) if v2 is not None else '?'} tụt về "
       f"{so(vg) if vg is not None else '?'}")
    # RĂNG chống bản vá giả: tỉ lệ phải ĐỌC TỪ SỐ trong lời báo. Chấm bằng
    # phép so TƯƠNG ĐỐI nên nó đúng với MỌI khúc thanh (dau/rong đổi vẫn ăn):
    #   (v4 - v2) / (v6 - v2) == (4/6 - 2/6) / (6/6 - 2/6) == 0,5
    # Một bộ ĐẾM nội bộ (báo nhịp thứ 3/4/5 trên 6) ra 0,667 -> HỎNG.
    v4, v6 = g.tra("Doc cau 4/6"), g.tra("Doc cau 6/6")
    if None in (v2, v4, v6) or abs(v6 - v2) < 1e-12:
        ok(f"[{ten}] tỉ lệ đọc từ SỐ THẬT trong lời báo", False,
           f"thiếu nhịp để chấm: v2={v2} v4={v4} v6={v6}")
    else:
        ti = (v4 - v2) / (v6 - v2)
        ok(f"[{ten}] tỉ lệ đọc từ SỐ THẬT trong lời báo (không tự đếm)",
           abs(ti - 0.5) < 1e-6, f"tỉ lệ {so(ti)} thay vì 0,5000")

# Bước 5 chiếm CẢ khúc thanh của bước (dau=0,0 · rong=1,0) — chấm riêng một
# mục để nếu khúc thanh đổi hợp lệ thì chỉ mục này đỏ, kèm lý do rõ.
g5 = GHI_CHO["bước 5  doc_ban_dich"]
v6_5 = g5.tra("Doc cau 6/6")
ok("bước 5: nhịp câu CUỐI = 1,0 (khúc thanh 0,0..1,0)",
   v6_5 is not None and abs(v6_5 - 1.0) < 1e-9,
   so(v6_5) if v6_5 is not None else "KHÔNG BÁO")

# ══ MỤC 3b — BA CỬA CỦA `dubbing.py` (đường REUP THUYẾT MINH), chạy THẬT ══
print("\n══ MỤC 3b. dubbing.build_recap_track — BA chỗ gọi _synth_all_words ══")
g3b = Ghi()
loi3b = ""
try:
    chay_recap(g3b, hong_lan_dau=3)
except Exception as e:  # noqa: BLE001
    loi3b = f"{type(e).__name__}: {e}"
    traceback.print_exc()
gt3b = g3b.gia_tri()
print(f"  · recap: {len(g3b.moi)} lời báo · {len(gt3b)} nhịp · "
      f"lượt gọi {g3b.tung_lan} · nhịp/lượt {g3b.nhip_lan}")
ok("[recap] chạy xong không ném", loi3b == "", loi3b)
ok("[recap] đi qua ĐÚNG 3 lượt gọi máy đọc (đọc chính · vét · dự phòng)",
   len(g3b.tung_lan) == 3, str(g3b.tung_lan))
ok("[recap] CẢ BA lượt đều truyền `on_msg` xuống",
   len(g3b.tung_lan) == 3 and all(g3b.tung_lan), str(g3b.tung_lan))
ok("[recap] CẢ BA lượt đều báo >= 2 nhịp lúc đang đọc",
   len(g3b.nhip_lan) == 3 and all(x >= 2 for x in g3b.nhip_lan),
   str(g3b.nhip_lan))
ok("[recap] dãy nhịp KHÔNG BAO GIỜ tụt lùi",
   all(gt3b[i] <= gt3b[i + 1] + 1e-9 for i in range(len(gt3b) - 1)),
   " ".join(so(x) for x in gt3b))
ok("[recap] các nhịp KHÁC NHAU (>= 2 giá trị)", len(set(gt3b)) >= 2,
   str(sorted(set(gt3b))[:6]))
# Nhịp phải nằm GỌN trong khúc thu giọng [0,05 .. 0,65]; tràn ra là đè lên ô
# của bước sau (`0.65 + 0.25 * ...` là khúc khớp thời gian).
ok("[recap] mọi nhịp nằm gọn trong khúc thu giọng [0,05 .. 0,65]",
   all(0.05 - 1e-9 <= x <= 0.65 + 1e-9 for x in gt3b),
   f"min {so(min(gt3b)) if gt3b else '?'} max "
   f"{so(max(gt3b)) if gt3b else '?'}")
# RĂNG chống bản vá giả: tỉ lệ phải ĐỌC TỪ SỐ, không tự đếm (xem mục 3).
v2b, v4b, v6b = (g3b.tra("Doc cau 2/6"), g3b.tra("Doc cau 4/6"),
                 g3b.tra("Doc cau 6/6"))
if None in (v2b, v4b, v6b) or abs(v6b - v2b) < 1e-12:
    ok("[recap] tỉ lệ đọc từ SỐ THẬT trong lời báo", False,
       f"thiếu nhịp để chấm: v2={v2b} v4={v4b} v6={v6b}")
else:
    ti_b = (v4b - v2b) / (v6b - v2b)
    ok("[recap] tỉ lệ đọc từ SỐ THẬT trong lời báo (không tự đếm)",
       abs(ti_b - 0.5) < 1e-6, f"tỉ lệ {so(ti_b)} thay vì 0,5000")
_l3b = lui_theo_buoc(g3b)
ok("[recap] phần SỐ trong CHỮ KHÔNG lùi trong cùng một bước", not _l3b,
   f"{len(_l3b)} lần, đầu tiên {_l3b[0] if _l3b else ''}")

# ── ĐỐI CHỨNG CHỐNG HỒI QUY: giọng edge-tts (KHÔNG gộp loạt) phải giữ ──────
# nguyên hành vi cũ — `on_done` từng câu, chữ đếm 1/6 .. 6/6 y như trước.
g3c = Ghi()
loi3c = ""
try:
    chay_recap(g3c, kieu_edge=True)
except Exception as e:  # noqa: BLE001
    loi3c = f"{type(e).__name__}: {e}"
ok("[recap · edge-tts] chạy xong không ném", loi3c == "", loi3c)
_chu_edge = [m for _p, m, _t in g3c.moi if "Thu giọng đoạn" in m]
ok("[recap · edge-tts] vẫn đếm ĐỦ 1/6 .. 6/6 (không bị kẹp lên 6/6)",
   _chu_edge[:2] == ["Thu giọng đoạn 1/6...", "Thu giọng đoạn 2/6..."]
   and len(_chu_edge) == N_CAU, str(_chu_edge[:3]))
_p_edge = [p for p, m, _t in g3c.moi if "Thu giọng đoạn" in m]
ok("[recap · edge-tts] thanh vẫn NHÍCH đều theo từng câu",
   len(set(_p_edge)) == N_CAU, " ".join(so(x) for x in _p_edge))

# ══ MỤC 4 — QUÉT TĨNH BẰNG AST (kèm TỰ KIỂM BỘ DÒ) ══
print("\n══ MỤC 4. Quét AST: `on_msg` là BIỂU THỨC, không phải hằng số ══")
# Đọc thẳng file bằng utf-8 (`inspect.getsource` mở theo bảng mã MẶC ĐỊNH của
# máy -> docstring tiếng Việt ra mojibake rồi `ast.parse` nổ — cổng 71).
NGUON = (REPO / "app" / "core" / "thay_giong.py").read_text(encoding="utf-8")


def _tim_ham(nguon: str, ten: str):
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return None
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    return None


def _la_goi_tts(n) -> bool:
    """Nút AST này có phải lời gọi `_synth_all_words` không?

    Phải nhận CẢ HAI mặt chữ: `dubbing._synth_all_words(...)` (`ast.Attribute`
    — cách `thay_giong.py` gọi) và `_synth_all_words(...)` (`ast.Name` — cách
    `dubbing.py` gọi CHÍNH nó). Bộ dò chỉ biết một dạng thì nửa số cửa vô hình
    với cổng, mà nó vẫn báo "ĐẠT" cho nửa kia = con dấu.
    """
    if not isinstance(n, ast.Call):
        return False
    f = n.func
    return ((isinstance(f, ast.Attribute) and f.attr == "_synth_all_words")
            or (isinstance(f, ast.Name) and f.id == "_synth_all_words"))


def soi_cho_goi(nguon: str, ten_ham: str) -> dict:
    """Thân `ten_ham` có gọi `_synth_all_words` với `on_msg` là BIỂU THỨC?

    Quét bằng AST nên **ghi chú và docstring không tồn tại** với bộ dò — đúng
    chỗ 7 lần quét-chuỗi của repo này tự bắn vào chân. Và nó đòi giá trị
    KHÔNG phải `ast.Constant`: hỏi mỗi "có mặt không" thì luôn có phép phá
    giữ nguyên mặt chữ mà đổi nghĩa (`on_msg=None`).
    """
    fn = _tim_ham(nguon, ten_ham)
    if fn is None:
        return {"co_ham": False, "so_goi": 0, "co_on_msg": False,
                "hang_so": False}
    goi = [n for n in ast.walk(fn) if _la_goi_tts(n)]
    co = hang = False
    for c in goi:
        for kw in c.keywords:
            if kw.arg == "on_msg":
                co = True
                if isinstance(kw.value, ast.Constant):
                    hang = True
    return {"co_ham": True, "so_goi": len(goi), "co_on_msg": co,
            "hang_so": hang}


for ten_ham in ("doc_ban_dich", "rut_gon_vua_khung", "doc_nhanh_vua_khung"):
    d = soi_cho_goi(NGUON, ten_ham)
    ok(f"AST · {ten_ham} có gọi `_synth_all_words`",
       d["co_ham"] and d["so_goi"] >= 1, str(d))
    ok(f"AST · {ten_ham} truyền keyword `on_msg`", d["co_on_msg"], str(d))
    ok(f"AST · {ten_ham}: `on_msg` là BIỂU THỨC, không phải hằng số",
       d["co_on_msg"] and not d["hang_so"], str(d))

# Thân `_nhac_tung_cau` phải THẬT SỰ gọi `on_progress`, và lời gọi đó phải
# nằm trong `try/except` (chốt KHÔNG BAO GIỜ NÉM — mục 2/5 chấm động, mục này
# nói ra LÝ DO).
fn_nhac = _tim_ham(NGUON, "_nhac_tung_cau")
goi_op = []
if fn_nhac is not None:
    goi_op = [n for n in ast.walk(fn_nhac) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name) and n.func.id == "on_progress"]
ok("AST · thân `_nhac_tung_cau` THẬT SỰ gọi `on_progress`",
   len(goi_op) >= 1, f"{len(goi_op)} lời gọi")
trong_try = False
if fn_nhac is not None:
    for t in ast.walk(fn_nhac):
        if isinstance(t, ast.Try):
            for con in ast.walk(ast.Module(body=t.body, type_ignores=[])):
                if con in goi_op:
                    trong_try = True
ok("AST · lời gọi `on_progress` nằm trong try/except", trong_try,
   "không có -> caller ném là giết cả lượt đọc")

# ── TỰ KIỂM BỘ DÒ: bộ dò phải KÊU đúng chỗ, và KHÔNG bị ghi chú lừa ──
MAU_TOT = ("def f(a, b):\n"
           "    x = dubbing._synth_all_words(a, b, on_msg=_nhac)\n"
           "    return x\n")
MAU_THIEU = ('def f(a, b):\n'
             '    """Ghi chú: phải truyền on_msg=_nhac xuống."""\n'
             '    # on_msg=_nhac  <- chỉ là ghi chú\n'
             '    x = dubbing._synth_all_words(a, b)\n'
             '    return x\n')
MAU_HANG = ("def f(a, b):\n"
            "    x = dubbing._synth_all_words(a, b, on_msg=None)\n"
            "    return x\n")
d_tot, d_thieu, d_hang = (soi_cho_goi(MAU_TOT, "f"),
                          soi_cho_goi(MAU_THIEU, "f"),
                          soi_cho_goi(MAU_HANG, "f"))
ok("TỰ KIỂM BỘ DÒ · mẫu ĐÚNG -> bộ dò cho qua",
   d_tot["co_on_msg"] and not d_tot["hang_so"], str(d_tot))
ok("TỰ KIỂM BỘ DÒ · mẫu THIẾU `on_msg` -> bộ dò KÊU",
   not d_thieu["co_on_msg"], str(d_thieu))
ok("TỰ KIỂM BỘ DÒ · mẫu `on_msg=None` (hằng số) -> bộ dò KÊU",
   d_hang["hang_so"], str(d_hang))
# Bằng chứng vì sao KHÔNG được quét chuỗi: cùng mẫu THIẾU đó, phép `in` nói
# "có on_msg" (nó trúng docstring + dòng ghi chú) còn AST nói KHÔNG.
ok("TỰ KIỂM BỘ DÒ · quét CHUỖI bị ghi chú lừa, AST thì không",
   ("on_msg" in MAU_THIEU) and not d_thieu["co_on_msg"],
   "mẫu thử không dựng đúng bẫy")
# Mặt chữ THỨ HAI: `dubbing.py` gọi CHÍNH NÓ nên không có tiền tố module.
MAU_TRAN = ("def f(a, b):\n"
            "    x = _synth_all_words(a, b, on_msg=_nhac)\n"
            "    return x\n")
d_tran = soi_cho_goi(MAU_TRAN, "f")
ok("TỰ KIỂM BỘ DÒ · gọi TRẦN `_synth_all_words(...)` cũng bị bắt",
   d_tran["so_goi"] == 1 and d_tran["co_on_msg"], str(d_tran))

# ── AST trên `dubbing.py`: BA cửa của đường recap ────────────────────────
NGUON_DUB = (REPO / "app" / "core" / "dubbing.py").read_text(encoding="utf-8")
d_rec = soi_cho_goi(NGUON_DUB, "build_recap_track")
ok("AST · build_recap_track gọi `_synth_all_words` ĐÚNG 3 lần",
   d_rec["co_ham"] and d_rec["so_goi"] == 3, str(d_rec))
ok("AST · build_recap_track truyền keyword `on_msg`", d_rec["co_on_msg"],
   str(d_rec))
ok("AST · build_recap_track: `on_msg` là BIỂU THỨC, không phải hằng số",
   d_rec["co_on_msg"] and not d_rec["hang_so"], str(d_rec))


def _so_goi_co_on_msg(nguon: str, ten_ham: str) -> int:
    """Đếm lời gọi `_synth_all_words` CÓ `on_msg` là biểu thức."""
    fn = _tim_ham(nguon, ten_ham)
    if fn is None:
        return 0
    n = 0
    for c in ast.walk(fn):
        if not _la_goi_tts(c):
            continue
        for kw in c.keywords:
            if kw.arg == "on_msg" and not isinstance(kw.value, ast.Constant):
                n += 1
    return n


ok("AST · CẢ BA lời gọi đều mang `on_msg` (không sót lượt VÉT/dự phòng)",
   _so_goi_co_on_msg(NGUON_DUB, "build_recap_track") == 3,
   str(_so_goi_co_on_msg(NGUON_DUB, "build_recap_track")))

# CỬA DUY NHẤT: `build_recap_track` phải DÙNG LẠI `_nhac_tung_cau` của
# `thay_giong.py`, KHÔNG chép bộ nhắc thứ hai (hai bản sao = hai chỗ lệch).
fn_rec = _tim_ham(NGUON_DUB, "build_recap_track")
goi_nhac = [n for n in ast.walk(fn_rec) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "_nhac_tung_cau"] if fn_rec else []
ok("AST · build_recap_track DÙNG LẠI `_nhac_tung_cau` (>= 3 lượt)",
   len(goi_nhac) >= 3, f"{len(goi_nhac)} lời gọi")


def _prog_hang_so(nguon: str, ten_ham: str) -> list[float]:
    """Các `prog(<hằng số>, m)` dùng làm `on_msg` — mốc CHẾT của thanh.

    `on_msg=lambda m: prog(0.06, m)` là bản CŨ: hằng 0,06 nằm DƯỚI mọi mốc
    `_tts_done` báo, nên hai nguồn xen kẽ là thanh chạy giật lùi.
    """
    fn = _tim_ham(nguon, ten_ham)
    ra: list[float] = []
    if fn is None:
        return ra
    for c in ast.walk(fn):
        if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr in ("_synth_all_eleven", "_synth_all_gemini",
                                    "_synth_all_words")):
            continue
        for kw in c.keywords:
            if kw.arg != "on_msg" or not isinstance(kw.value, ast.Lambda):
                continue
            for n2 in ast.walk(kw.value):
                if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Name)
                        and n2.func.id == "prog" and n2.args
                        and isinstance(n2.args[0], ast.Constant)):
                    ra.append(n2.args[0].value)
    return ra


ok("AST · KHÔNG còn `on_msg=lambda m: prog(<hằng số>, m)`",
   not _prog_hang_so(NGUON_DUB, "build_recap_track"),
   str(_prog_hang_so(NGUON_DUB, "build_recap_track")))

# ── TỰ KIỂM BỘ DÒ (hai bộ dò mới) ──────────────────────────────────────
MAU_3 = ("def f(a):\n"
         "    dubbing._synth_all_words(a, on_msg=_n)\n"
         "    dubbing._synth_all_words(a, on_msg=_n)\n"
         "    dubbing._synth_all_words(a)\n")
ok("TỰ KIỂM BỘ DÒ · mẫu 3 lời gọi mà 1 lời THIẾU on_msg -> đếm ra 2",
   _so_goi_co_on_msg(MAU_3, "f") == 2, str(_so_goi_co_on_msg(MAU_3, "f")))
MAU_PROG = ("def f(a):\n"
            "    dubbing._synth_all_eleven(a, on_msg=lambda m: prog(0.06, m))\n")
ok("TỰ KIỂM BỘ DÒ · mẫu `prog(0.06, m)` -> bộ dò KÊU",
   _prog_hang_so(MAU_PROG, "f") == [0.06], str(_prog_hang_so(MAU_PROG, "f")))
MAU_NHAC = ('def f(a):\n'
            '    """Ghi chú: trước đây dùng lambda m: prog(0.06, m)."""\n'
            '    dubbing._synth_all_eleven(a, on_msg=_nhac)\n')
ok("TỰ KIỂM BỘ DÒ · ghi chú nhắc `prog(0.06, m)` KHÔNG làm bộ dò kêu oan",
   _prog_hang_so(MAU_NHAC, "f") == [], str(_prog_hang_so(MAU_NHAC, "f")))

# ══ MỤC 5 — caller ném thì CẢ BA chỗ vẫn phải chạy trót lọt (e2e) ══
print("\n══ MỤC 5. `on_progress` của caller NÉM — cả ba chỗ vẫn chạy ══")
for ten, ham in BA_CHO:
    # CHỈ ném ở đúng các lời báo đi qua đường nhịp; các lời báo TRỰC TIẾP của
    # hàm (vd `on_progress(0.95, "Cắt lề im lặng...")`) cố ý KHÔNG ném, vì
    # chúng không nằm trong mệnh đề đang chấm và chấm chúng là đỏ oan.
    g = Ghi(nem_khi=tuple(LOI_NHAN))
    loi = ""
    try:
        with may_doc_gia(g):
            ham(g)
    except Exception as e:  # noqa: BLE001
        loi = f"{type(e).__name__}: {e}"
    ok(f"[{ten}] caller ném {g.so_nem} lần -> KHÔNG lọt ra ngoài", loi == "",
       loi)
    ok(f"[{ten}] vẫn thử báo đủ 6 nhịp dù lần nào cũng ném",
       g.so_nem == 6, str(g.so_nem))

# ══ MỤC 5b — CỔNG KHÔNG ĐƯỢC ĐỤNG VÀO MÁY THẬT ══
print("\n══ MỤC 5b. Cổng không đụng máy thật ══")
ok("không cú mở Explorer/trình phát nào bị canh cổng chặn (tức không có cú "
   "nào)", len(_test_guard.DA_CHAN) == 0, str(_test_guard.DA_CHAN))

# ══ MỤC 6 — DÃY CHỮ THÔ KHÔNG ĐƯỢC ĐI LÙI (nợ 2 — nay CÓ CHẤM) ══
#
# Trước bản vá mục này chỉ IN RA rồi ghi "lỗ còn lại, chưa canh": máy đọc gộp
# cả loạt nổ `on_done` cho MỌI câu Ở CUỐI, mà `doc_ban_dich._done` báo THẲNG
# `xong/N` -> đo được **5 lần chữ nhảy ngược** («Doc cau 6/6» -> «Đang đọc câu
# 1/6») và tỉ lệ thô tụt **1,0000 -> 0,1667**. Nay `_done` đi qua `_nhac` nên
# lỗ đó đóng và mục này thành CHỐT.
#
# CHẤM TRÊN CHỮ, KHÔNG CHẤM TRÊN TỈ LỆ THÔ — đọc kỹ kẻo sửa nhầm:
# `doc_ban_dich` còn một lời báo TRỰC TIẾP `on_progress(0.95, "Cắt lề im
# lặng...")` sau khi nhịp đã tới 1,0. Nó KHÔNG mang số nào nên không phá bất
# biến "số trong chữ không giảm", và nó là một BƯỚC KHÁC (cắt lề, không phải
# đọc) — chấm nó là cổng đỏ oan trên bản mã ĐÚNG. Con số vẫn được IN ra.
print("\n══ MỤC 6. Dãy CHỮ THÔ không được đi lùi ══")
for ten, _ in BA_CHO:
    g = GHI_CHO[ten]
    tho = [p for p, _m, _t in g.moi]
    tut = [(tho[i], tho[i + 1]) for i in range(len(tho) - 1)
           if tho[i + 1] < tho[i] - 1e-9]
    lui = lui_theo_buoc(g)
    print(f"  · {ten}: {len(g.moi)} lời báo thô · {len(g.gia_tri())} nhịp · "
          f"{len(tut)} lần TỤT tỉ lệ · {len(lui)} lần LÙI CHỮ"
          + (f" (tỉ lệ tệ nhất {so(tut[0][0])} -> {so(tut[0][1])})"
             if tut else ""))
    ok(f"[{ten}] phần SỐ trong CHỮ không lùi lần nào", not lui,
       f"{len(lui)} lần, đầu tiên {lui[0] if lui else ''}")
_lui_rec = lui_theo_buoc(g3b)
print(f"  · recap build_recap_track: {len(g3b.moi)} lời báo thô · "
      f"{len(g3b.gia_tri())} nhịp · {len(_lui_rec)} lần LÙI CHỮ")
print("  CÒN LẠI, CỐ Ý KHÔNG CHẤM: `doc_ban_dich` báo thẳng 0,95 «Cắt lề im")
print("  lặng...» sau khi nhịp đã tới 1,0 -> tỉ lệ THÔ tụt đúng 1 lần. Lời báo")
print("  đó KHÔNG mang số nên bất biến chữ vẫn giữ, và nó là BƯỚC KHÁC.")

print("\n" + "=" * 74)
print(f"KẾT QUẢ CỔNG 90 — ĐẠT {DAT} · HỎNG {len(HONG)}")
for h in HONG:
    print(f"   HỎNG: {h}")
print("=" * 74)
sys.exit(1 if HONG else 0)
