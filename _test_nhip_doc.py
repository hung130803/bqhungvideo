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

MỆNH ĐỀ TRUNG TÂM (MỤC 3):
    **Ba chỗ gọi TTS — `doc_ban_dich` (bước 5) · `rut_gon_vua_khung` (4b) ·
    `doc_nhanh_vua_khung` (4c) — phải báo ÍT NHẤT 2 NHỊP KHÁC NHAU TRONG LÚC
    ĐANG ĐỌC, không phải chỉ ở cuối.**

ĐÂY LÀ MỆNH ĐỀ VỀ **HÀNH VI**, KHÔNG PHẢI VỀ MẶT CHỮ. Cổng KHÔNG dừng ở chỗ
hỏi "mã có chữ `on_msg` không" — quét kiểu đó luôn có phép phá giữ nguyên mặt
chữ mà đổi nghĩa (bài học cổng 56d: `che_chu=` -> `che_chu=False` vẫn xanh).
Cách đo ĐÚNG, và là cách cổng này dùng: **giả lập một máy đọc GỘP CẢ LOẠT**
phát ra chuỗi `Doc cau 1/6` … `Doc cau 6/6` qua `on_msg`, GỌI THẬT cả ba hàm,
rồi BẮT từng lần `on_progress` được gọi. Bỏ `on_msg` -> máy đọc giả không có
ai để gọi -> **0 nhịp** -> HỎNG. Đổi thành hằng số `None` -> y hệt.

TIỀN ĐỊNH VÀ RẺ: KHÔNG gọi mạng · KHÔNG Groq · KHÔNG edge-tts · KHÔNG ffmpeg ·
KHÔNG nạp model. `dubbing._synth_all_words`, `cat_le_loat`, `probe_duration`
và `_rut_gon_loat` (lượt LLM) đều được vá bằng bản GIẢ; ba hàm ĐANG TEST thì
chạy THẬT, không mock.

VÌ SAO CHỐT "KHÔNG TỤT LÙI" CHẤM TRÊN DÃY NHỊP CHỨ KHÔNG TRÊN CẢ DÒNG BÁO —
đọc kỹ kẻo sửa nhầm: `doc_ban_dich` còn hai lời báo TRỰC TIẾP không đi qua
`_nhac` (`_done` và `on_progress(0.95, "Cắt lề im lặng...")`). Máy đọc gộp cả
loạt gọi `on_done` cho MỌI câu **ở cuối** (xem `giong_vieneu._xong_het`), nên
dòng báo THÔ có tụt thật — MỤC 6 ĐO và IN con số đó ra như một **lỗ còn lại**,
cố ý KHÔNG chấm. Chấm nó là cổng đỏ oan trên bản mã ĐÚNG, mà cổng đỏ oan thì
người ta thôi đọc nó (bài học cổng 41 và 47).

    .venv\\Scripts\\python -u _test_nhip_doc.py
"""
from __future__ import annotations

import ast
import atexit
import contextlib
import os
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

    def __call__(self, p, m) -> None:
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


def _may_doc_gia(ghi: Ghi):
    """`dubbing._synth_all_words` GIẢ: đọc CẢ LOẠT trong MỘT lượt gọi."""

    async def _gia(texts, voice, paths, on_done=None, rate="+0%",
                   pitch="+0Hz", lang="", el_lui=True, on_msg=None, **kw):
        ghi.tu_nhip = False
        for m in LOI_NHAN:
            if on_msg:
                ghi.tu_nhip = True
                try:
                    on_msg(m)
                finally:
                    ghi.tu_nhip = False
        for p in paths:
            pp = Path(p)
            pp.parent.mkdir(parents=True, exist_ok=True)
            pp.write_bytes(b"\0" * 16)
        # `on_done` NỔ Ở CUỐI cho MỌI câu — đúng `giong_vieneu._xong_het`,
        # tức đúng cái đã làm thanh đứng chết. Giữ nguyên hình dạng đó thì
        # MỤC 6 mới đo được phần còn sót.
        if on_done:
            for i in range(len(texts)):
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass
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
    goi = [n for n in ast.walk(fn)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "_synth_all_words"]
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

# ══ MỤC 6 — SỐ ĐO + LỖ CÒN LẠI (in ra, CỐ Ý KHÔNG CHẤM) ══
print("\n══ MỤC 6. Số đo · lỗ còn lại (không chấm) ══")
for ten, _ in BA_CHO:
    g = GHI_CHO[ten]
    tho = [p for p, _m, _t in g.moi]
    tut = [(tho[i], tho[i + 1]) for i in range(len(tho) - 1)
           if tho[i + 1] < tho[i] - 1e-9]
    print(f"  · {ten}: {len(g.moi)} lời báo thô · {len(g.gia_tri())} nhịp · "
          f"{len(tut)} lần TỤT trên dòng thô"
          + (f" (tệ nhất {so(tut[0][0])} -> {so(tut[0][1])})" if tut else ""))
print("  LỖ CÒN LẠI (đo được, chưa canh): máy đọc gộp cả loạt gọi `on_done`")
print("  cho MỌI câu Ở CUỐI, mà `doc_ban_dich._done` báo thẳng `xong/N` nên")
print("  dòng báo THÔ vẫn tụt một nhịp sau khi nhịp đã tới 1,0. Không kéo dài")
print("  (nổ liên tiếp trong vài ms) nhưng CHƯA có chốt nào chặn.")

print("\n" + "=" * 74)
print(f"KẾT QUẢ CỔNG 90 — ĐẠT {DAT} · HỎNG {len(HONG)}")
for h in HONG:
    print(f"   HỎNG: {h}")
print("=" * 74)
sys.exit(1 if HONG else 0)
