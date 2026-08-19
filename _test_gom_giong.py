# -*- coding: utf-8 -*-
"""CỔNG 79 — DANH SÁCH GIỌNG PHẢI GOM NHÓM ĐƯỢC, KHÔNG "LUNG TUNG".

Anh Hùng, ảnh chụp v2.37.0 (combo Giọng đọc): *"phần chọn giọng nó không phân
gì cả, rất lung tung, không biết chọn sao, sắp xếp lại cho tôi"* — kèm ba điều
đọc thẳng ra từ ảnh: **Andrew hiện hai lần** · giọng đa ngôn ngữ trộn lẫn giọng
tiếng Anh · **không biết cái nào miễn phí, cái nào tốn tiền, cái nào phải tải
model**.

**ĐO TRƯỚC KHI SỬA (danh sách THẬT của app, không phải ví dụ bịa):**
combo có **131 dòng · 110 mã · 90 giọng khác nhau** — tức **20 dòng là TRÙNG MÃ
THẬT SỰ**, kể cả ``en-US-AndrewNeural``. Nguyên nhân: nhóm "ĐỀ XUẤT" liệt kê lại
đúng những giọng đã có trong nhóm ngôn ngữ, và biến thể cao độ được chèn sau
**cả hai** bản nên mỗi giọng Việt ra **10 dòng thay vì 5**. Vậy "Andrew hiện hai
lần" không chỉ là chuyện nhãn giống nhau — **cùng một mã thật sự nằm hai chỗ**.

Cổng này chấm ``app/core/giong_bang.py``. Nó KHÔNG gọi mạng, KHÔNG chạy ffmpeg,
KHÔNG đụng Groq -> tiền định, không nhấp nháy.

**BỐN MỆNH ĐỀ, và cả bốn đều phải chống được PHÉP PHÁ** (mục 7 tự phá chính
mình; gỡ chốt mà cổng vẫn xanh thì cổng chỉ là con dấu — bài học cổng 56d,
64, 73):

1. **KHÔNG MẤT GIỌNG NÀO.** Tập mã ra == tập mã vào. Việc này là "đổi cách
   bày", không phải "bỏ bớt".
2. **MỖI MÃ ĐÚNG MỘT LẦN.** Đây là mệnh đề chữa thẳng cái anh Hùng kêu.
3. **GIỌNG ĐÚNG TIẾNG ĐÍCH KHÔNG BỊ CHÔN.** Chọn Tiếng Việt thì giọng Việt
   phải đứng TRƯỚC giọng Anh — đo bằng VỊ TRÍ trong danh sách, không đọc bằng
   mắt.
4. **MỖI DÒNG TỰ NÓI ĐƯỢC TIỀN VÀ VIỆC PHẢI TẢI.** Combo lúc ĐÓNG chỉ hiện
   một dòng, nên nhãn nhóm không cứu được.

**MỘT MỤC ĐẶC BIỆT — CA 1 canh TIỀN TỐ đọc từ CHÍNH MODULE NGUỒN.** Nó ra đời
vì một lỗi thật của chính lượt này: ``giong_bang`` bản đầu "chừa chỗ" cho
VieNeu bằng tiền tố ĐOÁN là ``vieneu:``, trong khi module thật dùng ``vn:`` /
``vnb:``. Hậu quả nếu không bắt: 20 giọng VieNeu bị coi là edge-tts -> rơi vào
nhóm "các tiếng khác", **mất nhãn "cần tải 250 MB"**, và **không một dòng báo
nào**. Nên CA 1 không so với hằng số chép tay mà hỏi thẳng từng module.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _test_guard  # noqa: F401,E402  (utf-8 stdout + chặn mở cửa sổ)

from app.core import giong_bang as GB  # noqa: E402
from app.core import nhan_nha as NN  # noqa: E402

DAT = 0
HONG = 0


def ok(dieu: str, dung: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dung:
        DAT += 1
        print(f"  ĐẠT  {dieu}" + (f" -- {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {dieu}" + (f" -- {chi_tiet}" if chi_tiet else ""))


def _ma(ds):
    return [v for _n, v in ds if v]


# ---------------------------------------------------------------------------
print("=" * 72)
print("CA 1 — TIỀN TỐ MÃ GIỌNG LẤY TỪ CHÍNH MODULE NGUỒN, KHÔNG CHÉP TAY")
print("=" * 72)
# Mỗi mục: (tên module, tên hằng số tiền tố, nguồn mà `giong_bang` phải trả).
# Module chưa có trên máy -> BỎ QUA có ghi ra, KHÔNG tính là ĐẠT (đếm một thứ
# không kiểm được là đúng bệnh "phép đo phát chứng nhận").
CAC_NGUON = [
    ("app.core.piper_tts", "TIEN_TO", GB.PIPER),
    ("app.core.giong_ngoai", "TIEN_TO_OV", GB.OMNIVOICE),
    ("app.core.giong_ngoai", "TIEN_TO_IX", GB.INDEXTTS),
    ("app.core.giong_vbee", "TIEN_TO_VBEE", GB.VBEE),
    ("app.core.giong_vieneu", "TIEN_TO", GB.VIENEU),
    ("app.core.giong_vieneu", "TIEN_TO_NB", GB.VIENEU),
]
bo_qua = 0
for ten_mod, ten_hang, mong in CAC_NGUON:
    try:
        mod = __import__(ten_mod, fromlist=["x"])
        tt = getattr(mod, ten_hang)
    except Exception as e:  # noqa: BLE001
        bo_qua += 1
        print(f"  BỎ QUA {ten_mod}.{ten_hang} -- chưa có "
              f"({e.__class__.__name__})")
        continue
    that = GB.nguon(tt + "x")
    ok(f"{ten_mod}.{ten_hang} = {tt!r} -> nguồn {mong}",
       that == mong, f"giong_bang trả {that!r}")
# `el:` và `gemini:` không có hằng số riêng, chúng nằm trong `dubbing`
ok("el: -> ElevenLabs", GB.nguon("el:abc") == GB.ELEVEN)
ok("gemini: -> Gemini", GB.nguon("gemini:Kore") == GB.GEMINI)
ok("mã edge-tts không tiền tố -> edge",
   GB.nguon("vi-VN-HoaiMyNeural") == GB.EDGE)
# Bẫy tiền tố lồng nhau: `vnb:` phải thắng `vn:` (dài hơn thì thử trước)
ok("`vnb:` KHÔNG bị `vn:` nuốt", GB.nguon("vnb:D:/mau.wav") == GB.VIENEU)
if bo_qua:
    print(f"  (bỏ qua {bo_qua} mục vì module chưa có trên máy)")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 2 — TIỀN / PHẢI TẢI: mỗi nguồn phải trả lời được")
print("=" * 72)
ok("edge-tts miễn phí, không phải tải",
   GB.mien_phi("vi-VN-HoaiMyNeural") and not GB.can_tai("vi-VN-HoaiMyNeural"))
ok("Piper miễn phí NHƯNG phải tải",
   GB.mien_phi("piper:x") and GB.can_tai("piper:x") == "212 MB",
   GB.can_tai("piper:x"))
ok("OmniVoice miễn phí NHƯNG phải tải 6,1 GB",
   GB.mien_phi("ov:nu_tre") and GB.can_tai("ov:nu_tre") == "6,1 GB",
   GB.can_tai("ov:nu_tre"))
ok("VieNeu miễn phí NHƯNG phải tải",
   GB.mien_phi("vn:pham_tuyen") and GB.can_tai("vn:pham_tuyen") == "250 MB",
   GB.can_tai("vn:pham_tuyen"))
ok("ElevenLabs KHÔNG miễn phí", not GB.mien_phi("el:abc"))
ok("Vbee KHÔNG miễn phí", not GB.mien_phi("vbee:ngochuyen"))
ok("Gemini KHÔNG miễn phí", not GB.mien_phi("gemini:Kore"))
# Nhãn nút tải của module thật phải KHỚP con số `giong_bang` in ra (bài học
# cổng 71 CA 4: ghi 155 MB rồi tải 2,5 GB).
try:
    from app.core import giong_vieneu as VN
    ok("số MB của VieNeu khớp nhãn nút thật",
       "250" in VN.NHAN_TAI, VN.NHAN_TAI)
except Exception as e:  # noqa: BLE001
    print(f"  BỎ QUA nhãn nút VieNeu -- {e.__class__.__name__}")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 3 — BA BẤT BIẾN TRÊN DANH SÁCH THẬT CỦA APP")
print("=" * 72)
from app.ui.thay_giong_dialog import giong_dung_duoc  # noqa: E402
from app.core.dubbing import list_recap_voices  # noqa: E402

THO = giong_dung_duoc(list_recap_voices())
vao = _ma(THO)
tap_vao = set(vao)
print(f"  [đo] danh sách THẬT: {len(THO)} dòng · {len(vao)} mã · "
      f"{len(tap_vao)} giọng khác nhau · TRÙNG SẴN {len(vao) - len(tap_vao)}")
ok("bản CŨ quả thật có dòng trùng (nếu không thì cổng này vô nghĩa)",
   len(vao) > len(tap_vao),
   f"{len(vao) - len(tap_vao)} dòng trùng")

for nn in ("vi", "en", "ja", "zh"):
    ra = GB.gom_nhom(THO, nn)
    ma = _ma(ra)
    ok(f"[{nn}] KHÔNG MẤT giọng nào", set(ma) == tap_vao,
       f"thiếu {len(tap_vao - set(ma))} · thừa {len(set(ma) - tap_vao)}")
    ok(f"[{nn}] MỖI MÃ ĐÚNG MỘT LẦN", len(ma) == len(set(ma)),
       f"{len(ma)} dòng / {len(set(ma))} mã")
    # nhấn nhá giảm dần TRONG từng nhóm (nhóm "Khuyên dùng" có luật riêng:
    # đúng tiếng trước, đa ngôn ngữ sau -> bỏ qua, CA 5 chấm riêng)
    loi = []
    nhom, truoc = "", None
    for nhan, vid in ra:
        if not vid:
            nhom, truoc = nhan, None
            continue
        if nhom.startswith("KHUYÊN DÙNG"):
            continue
        m = NN.muc(vid.split("|")[0])
        m = -999.0 if m is None else m
        if truoc is not None and m > truoc + 1e-9:
            loi.append(f"{nhom[:22]}: {vid} {m} > {truoc}")
        truoc = m
    ok(f"[{nn}] trong mỗi nhóm, nhấn nhá CAO đứng trên", not loi,
       "; ".join(loi[:2]) or f"{len(ra)} dòng")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 4 — GIỌNG ĐÚNG TIẾNG ĐÍCH KHÔNG BỊ CHÔN (đo bằng VỊ TRÍ)")
print("=" * 72)
for nn, khac in (("vi", "en"), ("ja", "en")):
    ra = GB.gom_nhom(THO, nn)
    ma = _ma(ra)
    vt_dung = [i for i, v in enumerate(ma) if GB.ma_ngon_ngu(v) == nn]
    vt_khac = [i for i, v in enumerate(ma) if GB.ma_ngon_ngu(v) == khac]
    ok(f"[{nn}] có giọng đúng tiếng trong danh sách", bool(vt_dung))
    ok(f"[{nn}] giọng {nn} đứng TRƯỚC mọi giọng {khac}",
       bool(vt_dung) and bool(vt_khac) and max(vt_dung) < min(vt_khac),
       f"giọng {nn} ở vị trí {min(vt_dung)}-{max(vt_dung)}, "
       f"giọng {khac} bắt đầu ở {min(vt_khac)}")
    # Bản CŨ: giọng đúng tiếng đầu tiên nằm ở đâu?
    cu = [i for i, v in enumerate(vao) if GB.ma_ngon_ngu(v) == nn]
    if cu:
        print(f"  [đo] bản CŨ: giọng {nn} đầu tiên ở vị trí {min(cu)}/"
              f"{len(vao)} · bản MỚI ở vị trí {min(vt_dung)}/{len(ma)}")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 5 — KHUYÊN DÙNG: đúng tiếng TRƯỚC, đa ngôn ngữ SAU")
print("=" * 72)
# Vì sao phải có mục này: `nhan_nha` đo mỗi giọng trên câu ĐÚNG TIẾNG CỦA NÓ
# và dặn "so CHÉO tiếng chỉ là tham khảo". Xếp một hàng chung thì
# en-AU-William 4,73 (câu tiếng Anh) đứng trên vi-VN-NamMinh 4,04 (câu tiếng
# Việt) — tức khuyên anh Hùng đọc tiếng Việt bằng một giọng Tây.
for nn in ("vi", "en"):
    kh = GB.chon_khuyen(THO, nn)
    goc = [i for i, v in enumerate(kh) if GB.ma_ngon_ngu(v) == nn]
    da = [i for i, v in enumerate(kh) if GB.da_ngu(v)]
    ok(f"[{nn}] nhóm khuyên dùng không rỗng", bool(kh), f"{len(kh)} giọng")
    ok(f"[{nn}] giọng đúng tiếng đứng TRƯỚC giọng đa ngôn ngữ",
       not (goc and da) or max(goc) < min(da),
       f"đúng tiếng {goc} · đa ngôn ngữ {da}")
    ok(f"[{nn}] khuyên dùng KHÔNG có giọng phải tải / tốn tiền",
       all(GB.mien_phi(v) and not GB.can_tai(v) for v in kh))
    ok(f"[{nn}] khuyên dùng KHÔNG có biến thể cao độ (số đo là số MƯỢN)",
       not any(GB.la_bien_the(v) for v in kh))
    ok(f"[{nn}] mọi giọng khuyên dùng ĐÃ ĐO nhấn nhá",
       all(NN.muc(v.split("|")[0]) is not None for v in kh))

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 6 — MỖI DÒNG TỰ NÓI ĐƯỢC: tiền · phải tải · Andrew nào là Andrew nào")
print("=" * 72)
ra = GB.gom_nhom(THO, "vi")
TU_TIEN = ("miễn phí", "tốn", "tính tiền", "cần key", "hạn mức")
thieu = [n for n, v in ra if v and not any(t in n.lower() for t in TU_TIEN)]
ok("mọi dòng nói được TIỀN", not thieu,
   f"{len(thieu)} dòng thiếu: {thieu[:2]}")
thieu_tai = [n for n, v in ra
             if v and GB.can_tai(v) and "tải" not in n.lower()]
ok("mọi giọng phải-tải đều nói ra việc tải", not thieu_tai,
   f"{len(thieu_tai)} dòng thiếu: {thieu_tai[:2]}")

# Andrew / Brian: hai mã còn NGUYÊN và hai DÒNG phải khác chữ nhau
for ten, a, b in (("Andrew", "en-US-AndrewNeural",
                   "en-US-AndrewMultilingualNeural"),
                  ("Brian", "en-US-BrianNeural",
                   "en-US-BrianMultilingualNeural")):
    if a not in tap_vao or b not in tap_vao:
        print(f"  BỎ QUA {ten} -- máy này không có đủ hai bản")
        continue
    na = next((n for n, v in ra if v == a), "")
    nb = next((n for n, v in ra if v == b), "")
    ok(f"{ten}: GIỮ CẢ HAI mã (gộp lại là mất một giọng thật)",
       bool(na) and bool(nb))
    ok(f"{ten}: hai dòng KHÁC CHỮ nhau", na != nb, f"{na!r} vs {nb!r}")
    ok(f"{ten}: dòng nói ra bản nào là bản nào",
       ("đa ngôn ngữ" in nb.lower() or "đa ngữ" in nb.lower())
       and ("tiếng anh" in na.lower()),
       f"{na!r} | {nb!r}")
    ma_ = NN.muc(a)
    mb_ = NN.muc(b)
    if ma_ is not None and mb_ is not None:
        print(f"  [đo] {ten}: bản tiếng Anh {ma_:.2f} · "
              f"bản đa ngôn ngữ {mb_:.2f} · lệch {abs(ma_ - mb_):.2f}")

# KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen; bài học v2.6.22)
emoji = [n for n, _v in ra
         if any(ord(c) > 0xFFFF or unicodedata.category(c) == "So" for c in n)]
ok("KHÔNG dòng nào có emoji", not emoji, f"{len(emoji)}: {emoji[:2]}")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 7 — THỬ PHÁ: gỡ chốt thì cổng PHẢI đỏ")
print("=" * 72)
# Phá THẬT bằng cách vá hàm trong module đang chạy, rồi chấm lại đúng mệnh đề
# mà chốt đó bảo vệ. Không phá được = mệnh đề không có chốt nào đỡ.
goc_bien_the = GB.la_bien_the
try:
    # phá 1: coi như KHÔNG có biến thể cao độ nào -> chúng chen vào Khuyên dùng
    GB.la_bien_the = lambda v: False        # noqa: E731
    kh = GB.chon_khuyen(THO, "vi")
    ok("PHÁ 1 (bỏ chốt biến thể) -> mệnh đề CA 5 phải VỠ",
       any(goc_bien_the(v) for v in kh),
       f"{sum(1 for v in kh if goc_bien_the(v))} biến thể lọt vào khuyên dùng")
finally:
    GB.la_bien_the = goc_bien_the

# phá 2: bỏ chốt "hai rổ" trong PHÉP SẮP, giữ nguyên bộ LỌC.
#
# **BẢN ĐẦU CỦA PHÉP PHÁ NÀY SAI VÀ ĐÃ BÁO NGƯỢC** — ghi lại vì đúng loại bẫy
# repo này hay sập: nó vá `GB.da_ngu` thành `False`, nhưng `ma_ngon_ngu` CŨNG
# gọi `da_ngu`, nên `en-AU-WilliamMultilingual` hoá thành giọng "en" và bị bộ
# lọc GẠT HẲN khỏi danh sách ứng viên của tiếng Việt. Tức phép phá vô tình
# làm kết quả ĐÚNG HƠN, rồi cổng kết luận "không phá được". Phá một hàm dùng
# chung là phá cả những chỗ mình không định phá.
#
# Cách đúng: lấy CHÍNH tập ứng viên của `chon_khuyen` rồi sắp lại theo cách
# CŨ (chỉ `khoa_sap`, không chia rổ) và xem đầu bảng đổi thành gì.
ung = GB.chon_khuyen(THO, "vi", so=10_000)
cu = sorted(ung, key=lambda v: NN.khoa_sap(v.split("|")[0]))
ok("PHÁ 2 (bỏ chốt hai rổ) -> đầu bảng KHÔNG còn là giọng Việt",
   bool(cu) and GB.ma_ngon_ngu(cu[0]) != "vi",
   f"cách CŨ đầu bảng: {cu[0] if cu else ''} "
   f"({NN.muc(cu[0]) if cu else '?'}) — cách MỚI: {ung[0] if ung else ''} "
   f"({NN.muc(ung[0]) if ung else '?'})")

# phá 3: bỏ bước dedupe -> bất biến "mỗi mã đúng một lần" phải vỡ. Chứng minh
# bằng chính dữ liệu: danh sách vào ĐÃ có mã trùng sẵn.
ok("PHÁ 3 (không dedupe) -> bất biến CA 3 phải VỠ",
   len(vao) != len(set(vao)),
   f"danh sách vào có {len(vao) - len(set(vao))} dòng trùng")

# chốt tự kiểm: sau khi trả lại, mọi thứ phải xanh như cũ
kh = GB.chon_khuyen(THO, "vi")
ok("TỰ KIỂM: trả chốt lại thì khuyên dùng đúng như cũ",
   bool(kh) and GB.ma_ngon_ngu(kh[0]) == "vi"
   and not any(GB.la_bien_the(v) for v in kh),
   f"đầu bảng: {kh[0] if kh else ''}")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 8 — LỐI TẮT (`loi_tat=True`): luật anh Hùng chốt 19/08/2026")
print("=" * 72)
# Nguyên văn: *"nhiều bên sẽ có nhiều giọng giống nhau nhưng kệ nó cứ thêm vào
# trùng lặp hay sao cũng được cho tôi, tại chỗ free chỗ mất tiền ấy, cứ thêm"*.
# Nhóm "Khuyên dùng" nay là LỐI TẮT: giọng nằm cả ở đầu LẪN trong nhóm gốc.
#
# Bất biến ở chế độ này CHẶT HƠN chứ không lỏng hơn: mã lặp phải lặp ĐÚNG HAI
# LẦN, đúng một lần ở "Khuyên dùng", và dòng lối tắt phải TỰ NÓI nó là cùng
# giọng — vì cạnh nó có ca TRÙNG TÊN MÀ KHÁC GIỌNG THẬT (Andrew/Brian), hai
# loại đó mà lẫn vào nhau thì đúng bằng bệnh cũ.
for nn in ("vi", "en"):
    ra = GB.gom_nhom(THO, nn, loi_tat=True)
    ma = _ma(ra)
    ok(f"[{nn}] lối tắt: KHÔNG MẤT giọng nào", set(ma) == tap_vao,
       f"thiếu {len(tap_vao - set(ma))} · thừa {len(set(ma) - tap_vao)}")
    dem: dict[str, int] = {}
    for v in ma:
        dem[v] = dem.get(v, 0) + 1
    qua = {v: n for v, n in dem.items() if n > 2}
    ok(f"[{nn}] lối tắt: không mã nào quá HAI lần", not qua, f"{qua}")
    # mã lặp phải đúng bằng tập "khuyên dùng"
    lap = {v for v, n in dem.items() if n == 2}
    kh = set(GB.chon_khuyen(THO, nn))
    ok(f"[{nn}] mã lặp ĐÚNG BẰNG nhóm khuyên dùng", lap == kh,
       f"lặp {len(lap)} · khuyên {len(kh)}")
    # dòng lối tắt phải tự nói "cùng giọng"
    nhom, thieu_dau = "", []
    for nhan, vid in ra:
        if not vid:
            nhom = nhan
            continue
        if nhom.startswith("KHUYÊN DÙNG") and GB.DAU_LOI_TAT not in nhan:
            thieu_dau.append(nhan)
    ok(f"[{nn}] mọi dòng lối tắt TỰ NÓI là cùng giọng", not thieu_dau,
       f"{len(thieu_dau)} dòng thiếu: {thieu_dau[:1]}")
    # và dòng ở NHÓM GỐC thì KHÔNG được mang dấu đó (nếu không thì vô nghĩa)
    ban_goc = [n for n, v in ra
               if v and v in lap and GB.DAU_LOI_TAT not in n]
    ok(f"[{nn}] bản trong nhóm gốc KHÔNG mang dấu lối tắt",
       len(ban_goc) == len(lap), f"{len(ban_goc)}/{len(lap)}")

# mặc định vẫn phải là chế độ CHẶT (bất biến cũ còn nguyên người canh)
ra_mac_dinh = GB.gom_nhom(THO, "vi")
ma_md = _ma(ra_mac_dinh)
ok("mặc định `loi_tat=False` -> MỖI MÃ ĐÚNG MỘT LẦN (bất biến cũ còn)",
   len(ma_md) == len(set(ma_md)), f"{len(ma_md)} dòng / {len(set(ma_md))} mã")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 9 — MỖI DÒNG CÓ MỨC NHẤN NHÁ, VÀ KHÔNG NÓI HAI LẦN")
print("=" * 72)
ra = GB.gom_nhom(THO, "vi", loi_tat=True)
# giọng ĐÃ ĐO thì dòng phải mang số; giọng CHƯA ĐO thì TUYỆT ĐỐI không được
# có số (bịa số cạnh tên giọng = "phép đo phát chứng nhận").
#
# **BIẾN THỂ CAO ĐỘ (`...|-20Hz`) LÀ CA RIÊNG, VÀ NÓ PHẢI *KHÔNG* CÓ SỐ.**
# Bản đầu của mục này hỏi "tra được `muc()` theo mã GỐC thì dòng phải có số"
# và ra HỎNG 8 dòng kiểu `Nam Minh — hơi cao`. Đọc kỹ thì **mã đúng, mục
# test sai**: chưa ai đo riêng từng mức cao độ, nên gắn số của giọng gốc lên
# biến thể là MƯỢN số của mã khác — đúng thứ `chon_khuyen` đã từ chối
# ("khuyên bằng một con số mượn của mã khác thì đúng bằng bịa") và đúng thứ
# `nhan_nha.nhan()` tránh khi nó tra bằng mã ĐẦY ĐỦ. Nay tách hẳn hai rổ.
thieu_so, bia_so, noi_hai_lan, muon_so = [], [], [], []
for nhan, vid in ra:
    if not vid:
        continue
    co_so = "nhấn nhá" in nhan.lower()
    if nhan.lower().count("nhấn nhá") > 1:
        noi_hai_lan.append(nhan)
    if GB.la_bien_the(vid):             # biến thể cao độ -> CẤM có số
        if co_so:
            muon_so.append(nhan)
        continue
    da_do = NN.muc(vid) is not None
    if da_do and not co_so:
        thieu_so.append(nhan)
    if not da_do and co_so:
        bia_so.append(nhan)
ok("giọng ĐÃ ĐO -> dòng có số nhấn nhá", not thieu_so,
   f"{len(thieu_so)} thiếu: {thieu_so[:1]}")
ok("giọng CHƯA ĐO -> dòng KHÔNG có số (cấm bịa)", not bia_so,
   f"{len(bia_so)} bịa: {bia_so[:1]}")
ok("BIẾN THỂ CAO ĐỘ KHÔNG mượn số của giọng gốc", not muon_so,
   f"{len(muon_so)} mượn: {muon_so[:1]}")
ok("KHÔNG dòng nào nói 'nhấn nhá' hai lần", not noi_hai_lan,
   f"{len(noi_hai_lan)}: {noi_hai_lan[:1]}")
# TỰ KIỂM BỘ DÒ: `duoi_nhan_nha` phải câm khi nhãn đã tự mang số
ok("TỰ KIỂM: nhãn đã có số -> `duoi_nhan_nha` trả RỖNG",
   GB.duoi_nhan_nha("vi-VN-NamMinhNeural", "X - nhấn nhá 4,0 truyền cảm")
   == "" and GB.duoi_nhan_nha("vi-VN-NamMinhNeural", "X") != "")

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("CA 10 — GIỌNG VieNeu KHÔNG ĐƯỢC LÀ GIỌNG CHẾT (chọn X phải ra X)")
print("=" * 72)
# Đây là mệnh đề DUY NHẤT anh Hùng coi là lỗi trong lượt này: *"chọn X mà ra Y
# (giọng chết, như `ov:nu_am` đã bắt)"*. `giong_vieneu.py` xong từ `a95e0e6`
# nhưng tới v2.37.0 **không một dòng nào trong `dubbing.py` gọi tới nó** — đưa
# `vn:` vào combo mà quên nối cửa đọc thì mã giọng rơi thẳng xuống nhánh
# edge-tts, tức chọn "Minh Đức" nghe ra Hoài My, `rc` vẫn 0.
try:
    from app.core import giong_vieneu as VN2
    ds_vn = VN2.danh_sach_giong(du_chua_tai=True, ngan=True)
    ok("VieNeu có ĐỦ 20 giọng dựng sẵn", len(ds_vn) == 20, f"{len(ds_vn)}")
    ok("mọi mã VieNeu mang tiền tố thật `vn:` (KHÔNG phải `vieneu:`)",
       all(m.startswith("vn:") for m, _n in ds_vn))
    ok("20 giọng VieNeu đều có mặt trong danh sách THẬT của combo",
       all(m in tap_vao for m, _n in ds_vn),
       f"thiếu {[m for m, _n in ds_vn if m not in tap_vao][:2]}")
    # nhãn phải ĐỌC ĐƯỢC trong combo (bản đầy đủ đo được 364-521 ký tự)
    dai = max((len(n) for n, v in ra if v and v.startswith("vn:")), default=0)
    ok("dòng VieNeu đủ ngắn để đọc trong combo (<= 120 ký tự)", dai <= 120,
       f"dài nhất {dai} ký tự")
    ok("dòng VieNeu vẫn nói ra việc phải tải",
       all("tải" in n.lower() for n, v in ra if v and v.startswith("vn:")))

    # --- CHỖ RẼ THẬT: gọi `_synth_all_words` rồi xem nó đi vào đâu ---
    # KHÔNG quét chuỗi (bài học cổng 56d/64: quét chuỗi thì phép phá giữ
    # nguyên mặt chữ mà đổi ý nghĩa vẫn xanh). Vá `giong_vieneu.doc_loat` để
    # GHI LẠI lượt gọi, rồi chạy THẬT cửa chung.
    import asyncio
    from app.core import dubbing as DUB

    goi: list = []

    def _gia(texts, paths, voice, **kw):
        goi.append(voice)
        return [True] * len(texts), [[] for _ in texts]

    goc_doc = VN2.doc_loat
    goc_co = VN2.co_vieneu
    try:
        VN2.doc_loat = _gia
        VN2.co_vieneu = lambda: True
        ok_v, moc_v = asyncio.run(DUB._synth_all_words(
            ["xin chào"], "vn:Minh Đức", ["/tmp/kh.mp3"], lang="vi"))
        ok("`_synth_all_words` RẼ ĐÚNG sang VieNeu (không rơi edge-tts)",
           goi == ["vn:Minh Đức"], f"gọi {goi}")
        goi.clear()
        asyncio.run(DUB._synth_all(
            ["xin chào"], "vn:Minh Đức", ["/tmp/kh.mp3"], lang="vi"))
        ok("`_synth_all` RẼ ĐÚNG sang VieNeu", goi == ["vn:Minh Đức"],
           f"gọi {goi}")
        goi.clear()
        # giọng NHÂN BẢN cũng phải đi cùng cửa
        asyncio.run(DUB._synth_all_words(
            ["xin chào"], "vnb:D:/mau.wav", ["/tmp/kh.mp3"], lang="vi"))
        ok("giọng nhân bản `vnb:` cũng đi qua cửa đó",
           goi == ["vnb:D:/mau.wav"], f"gọi {goi}")
        goi.clear()
        # THIẾU MODEL -> LÙI ÊM về edge-tts, KHÔNG nổ (luật Piper/OmniVoice)
        VN2.co_vieneu = lambda: False
        dung, lui = DUB._vieneu_hay_khong("vn:Minh Đức")
        ok("thiếu model -> LÙI ÊM về edge-tts, không nổ",
           dung is False and lui and not lui.startswith("vn:"),
           f"lùi về {lui!r}")
        # và giọng KHÔNG phải VieNeu thì cửa này phải để yên
        VN2.co_vieneu = lambda: True
        ok("giọng edge-tts KHÔNG bị cửa VieNeu đụng vào",
           DUB._vieneu_hay_khong("vi-VN-HoaiMyNeural")
           == (False, "vi-VN-HoaiMyNeural"))
    finally:
        VN2.doc_loat = goc_doc
        VN2.co_vieneu = goc_co
except Exception as e:  # noqa: BLE001
    ok(f"CA 10 chạy được ({e.__class__.__name__}: {e})", False)

# ---------------------------------------------------------------------------
print()
print("=" * 72)
print(f"TỔNG: ĐẠT {DAT} · HỎNG {HONG}")
print("=" * 72)
sys.exit(1 if HONG else 0)
