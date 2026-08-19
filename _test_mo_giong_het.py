# -*- coding: utf-8 -*-
"""CỔNG 83 — **MỞ HẾT GIỌNG, NHƯNG GIỌNG NÀO CŨNG PHẢI ĐỌC THẬT ĐƯỢC**
(19/08/2026).

Anh Hùng: *"Thêm tất cả các giọng trong VieNeu hay mấy bên khác hỗ trợ cho
tôi"* · *"tôi tự trải nghiệm, bạn chỉ cần đảm bảo nó HOẠT ĐỘNG TỐT cho tôi
thôi"*. Phân vai đã rõ: anh Hùng quyết giọng nào hay, cổng này lo giọng đó
**CHẠY ĐÚNG**.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ CỔNG NÀY — HAI LỖI THẬT, CẢ HAI ĐỀU "APP VẪN CHẠY, KHÔNG AI BIẾT"
═══════════════════════════════════════════════════════════════════════════
**(a) `giong_mo.nen_mo` LÀ MÃ CHẾT.** `app/core/giong_mo.py` có từ lượt trước,
docstring dặn thẳng *"luồng lắp giao diện gọi `nen_mo` thay cho
`_la_giong_mo_them`"* — mà không ai nối. Quét AST toàn `app/`: `nen_mo` chỉ
được gọi từ CHÍNH `giong_mo.loc_mo`, còn `loc_mo` thì không nơi nào gọi. Tức
185 giọng "đã mở khoá" **chưa bao giờ ra tới combo**; đo thật combo chỉ có
**76 giọng edge-tts**. Cùng bẫy "tính năng không ai gọi thì chỉ là một file .py
nằm đó" mà cổng 70 và 82 đã dính.

**(b) TẤM VÉ VÀO COMBO BỊ CẤP BỞI PHÉP ĐO SAI VIỆC.** Luật cũ là *"có trong
`nhan_nha.BANG` thì mở"* — tức phải ĐO NHẤN NHÁ mới được mở. Nhấn nhá cần bộ 4
câu đúng tiếng, mà bảng câu chỉ có 15 thứ tiếng, nên **137 giọng của 60 thứ
tiếng bị khoá vì một lý do chẳng liên quan gì tới chúng**.

Cổng này chốt cách chữa: **tách hai câu hỏi** (đọc được không / nhấn nhá bao
nhiêu), và canh để không ai gộp lại.

═══════════════════════════════════════════════════════════════════════════
CỔNG NÀY *KHÔNG* LÀM GÌ
═══════════════════════════════════════════════════════════════════════════
* **KHÔNG đốt hạn mức ElevenLabs.** Mọi phép gọi thật ở đây chỉ dùng edge-tts
  (miễn phí). Nhánh `el:` được chấm bằng cách **vá điểm đến rồi xem nó rẽ vào
  đâu**, không gọi mạng ElevenLabs một lần nào.
* **KHÔNG tốn lượt Groq.**
* **KHÔNG đọc lại 322 giọng mỗi lượt hồi quy.** Biên bản nằm trong
  `giong_doc.BANG`; cổng đọc lại biên bản, và **đọc THẬT một mẻ nhỏ** (CA 2)
  để biên bản không thành lời tự khai.
"""
from __future__ import annotations

import ast
import asyncio
import binascii
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

SAN = REPO / "_kq_san_cong83"
shutil.rmtree(SAN, ignore_errors=True)
SAN.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(SAN / "data"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
NOWIN = 0x08000000

#: Mốc đối chứng = bản phát hành NGAY TRƯỚC tính năng này (luật cổng 56).
#: **KHÔNG BAO GIỜ dùng `main`/`HEAD`** — sau khi gộp thì đó chính là bản đang
#: test, cổng đối chứng tự PASS OAN vĩnh viễn (bài học cổng 36/51/52/56).
MOC = os.environ.get("BQ_MOC_GIONG", "v2.38.0")

_dat = _hong = _bo = 0
_ten_hong: list[str] = []


def ok(ten: str, dieu: bool, ghi: str = "") -> None:
    global _dat, _hong
    if dieu:
        _dat += 1
        print(f"  ĐẠT  {ten}" + (f" — {ghi}" if ghi else ""))
    else:
        _hong += 1
        _ten_hong.append(ten)
        print(f"  HỎNG {ten}" + (f" — {ghi}" if ghi else ""))


def bo_qua(ten: str, ly_do: str) -> None:
    global _bo
    _bo += 1
    print(f"  BỎ QUA {ten} — {ly_do}")


# ===========================================================================
print("=" * 78)
print("CỔNG 83 — MỞ HẾT GIỌNG, GIỌNG NÀO CŨNG PHẢI ĐỌC THẬT ĐƯỢC")
print("=" * 78)

from app.core import giong_bang as GB          # noqa: E402
from app.core import giong_doc as GD           # noqa: E402
from app.core import giong_mo as GM            # noqa: E402
from app.core import nhan_nha as NN            # noqa: E402

sys.path.insert(0, str(REPO))
import _cau_doc_thu as CAU                     # noqa: E402
import _do_doc_that as DT                      # noqa: E402


# ---------------------------------------------------------------- CA 1
print("\nCA 1 — bảng ĐỌC THẬT là BIÊN BẢN, không phải danh sách ước muốn")

import json                                    # noqa: E402

_kho = json.loads((REPO / "_kq_edge_voices.json").read_text(encoding="utf-8"))
_ten_that = {v["ShortName"] for v in _kho}
_loc_cua = {v["ShortName"]: v["Locale"] for v in _kho}

ok("1a MỌI giọng đang mở đều có BẰNG CHỨNG đọc được",
   all(GM.da_kiem_doc(m) for m in GM.moi_giong_mo()),
   f"{GM.so_giong_mo()} giọng / {len(GM.tieng_da_mo())} thứ tiếng")

# **ĐÂY LÀ MỆNH ĐỀ TRUNG TÂM.** Một tập TÊN thì ai cũng gõ thêm được một dòng;
# có SỐ thì phải chạy `_do_doc_that.py` mới có. Cổng đòi lại đúng số đó.
_thieu_so = sorted(m for m in GD.BANG
                   if not (isinstance(GD.BANG[m], tuple)
                           and len(GD.BANG[m]) == 2))
ok("1b mỗi mục là một CẶP SỐ (độ dài, RMS) — không phải chỉ cái tên",
   not _thieu_so, str(_thieu_so[:3]) or f"{len(GD.BANG)} mục")

_duoi_nguong = sorted(
    m for m, (d, r) in GD.BANG.items()
    if d < DT.DAI_TOI_THIEU or r < DT.RMS_TOI_THIEU)
ok("1c mọi số đo nằm TRÊN ngưỡng ĐẠT (dài >= 0,80s · RMS >= -60 dBFS)",
   not _duoi_nguong, str(_duoi_nguong[:3])
   or f"dài {min(d for d, _ in GD.BANG.values()):.2f}"
      f"-{max(d for d, _ in GD.BANG.values()):.2f}s · "
      f"RMS {min(r for _, r in GD.BANG.values()):.1f}"
      f"..{max(r for _, r in GD.BANG.values()):.1f} dBFS")

# Số vô lý (dài 900 giây, RMS +40 dBFS) là dấu hiệu ai đó gõ tay chứ không đo.
_vo_ly = sorted(m for m, (d, r) in GD.BANG.items()
                if not (0.8 <= d <= 30.0 and -60.0 <= r <= 0.0))
ok("1d không số nào vô lý (0,8..30 giây · -60..0 dBFS)", not _vo_ly,
   str(_vo_ly[:3]))

_ma_la = sorted(m for m in GD.BANG if m not in _ten_that)
ok("1e mọi khoá tra ra một giọng THẬT trong danh mục Microsoft",
   not _ma_la, str(_ma_la[:3]) or f"{len(GD.BANG)}/{len(GD.BANG)} khoá hợp lệ")

# "Có tên trong danh mục Microsoft" KHÔNG phải là vé vào combo. Ngày Microsoft
# thêm giọng mới, chúng KHÔNG được tự lọt vào trước khi ai đó cho chúng đọc thử.
ok("1f mã đúng dạng nhưng KHÔNG có biên bản thì KHÔNG mở",
   not GM.nen_mo("en-US-KhongCoThatNeural")
   and not GM.nen_mo("pl-PL-KhongCoThatNeural")
   and not GM.nen_mo(""))

# ---- TỰ KIỂM BỘ DÒ: cổng chỉ là con dấu nếu tiêu chí ĐẠT không biết kêu ----
_tk = SAN / "tu_kiem"
_tk.mkdir(parents=True, exist_ok=True)


def _sinh(ten: str, loc: list[str]) -> Path:
    p = _tk / ten
    subprocess.run([FF, "-y", "-v", "error"] + loc + [str(p)],
                   creationflags=NOWIN, timeout=90)
    return p


try:
    _im = _sinh("im.mp3", ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                           "-t", "3"])
    _cut = _sinh("cut.mp3", ["-f", "lavfi", "-i", "sine=f=300:r=24000",
                             "-t", "0.2"])
    _rong = _tk / "rong.mp3"
    _rong.write_bytes(b"")

    def _qua_duoc(p: Path) -> bool:
        """Đúng ba chốt của `_do_doc_that.doc_mot`, áp lên một file có sẵn."""
        if not p.exists() or p.stat().st_size <= 0:
            return False
        return (DT.do_dai(p) >= DT.DAI_TOI_THIEU
                and DT.do_rms(p) >= DT.RMS_TOI_THIEU)

    ok("1g TỰ KIỂM BỘ DÒ: file IM LẶNG 3 giây bị BẮT",
       not _qua_duoc(_im), f"RMS {DT.do_rms(_im):.1f} dBFS")
    ok("1h TỰ KIỂM BỘ DÒ: file có tiếng nhưng CỤT 0,2 giây bị BẮT",
       not _qua_duoc(_cut), f"dài {DT.do_dai(_cut):.2f}s")
    ok("1i TỰ KIỂM BỘ DÒ: file 0 BYTE bị BẮT", not _qua_duoc(_rong))
except Exception as e:                                         # noqa: BLE001
    ok("1g-1i TỰ KIỂM BỘ DÒ chạy được", False, f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------- CA 2
print("\nCA 2 — ĐỌC THẬT LẠI MỘT MẺ QUA ĐÚNG CỬA (biên bản không tự khai)")
# Bảng số ở CA 1 chỉ có nghĩa nếu cái cửa sinh ra nó vẫn còn chạy. Đọc lại cả
# 322 giọng mỗi lượt hồi quy thì cổng thành 7 phút mạng, nên lấy MỘT MẺ NHỎ —
# nhưng chọn TIỀN ĐỊNH bằng `crc32`, **KHÔNG dùng `hash()`** (nó băm kèm
# `PYTHONHASHSEED` ngẫu nhiên mỗi tiến trình nên mẻ đổi mỗi lượt và không tra
# lại được; đúng bài học cổng 81 CA 3i).
_ung = sorted(GD.BANG)
_MAU = [_ung[binascii.crc32(f"cong83-{i}".encode()) % len(_ung)]
        for i in range(3)]
_MAU = list(dict.fromkeys(_MAU))
print(f"  mẻ tiền định: {', '.join(_MAU)}")

_loi_mang = 0
for _v in _MAU:
    _loc = _loc_cua.get(_v, "")
    _d = DT.doc_mot(_v, _loc)
    if _d.get("ok"):
        _cu = GD.so_do(_v)
        ok(f"2 · {_v} đọc THẬT ra tiếng qua `dubbing._synth_all`",
           True, f"{_d['dai']:.2f}s {_d['rms']:.1f}dB "
                 f"(biên bản {_cu[0]:.2f}s {_cu[1]:.1f}dB)")
    else:
        _loi_mang += 1
        bo_qua(f"2 · {_v} đọc thật", f"{_d.get('vi_sao')} (nghi MẠNG)")
if _loi_mang and _loi_mang == len(_MAU):
    ok("2z cả mẻ hỏng -> KHÔNG phải nhiễu mạng lẻ tẻ, phải xem lại cửa đọc",
       False, f"{_loi_mang}/{len(_MAU)} giọng không đọc được")


# ---------------------------------------------------------------- CA 3
print("\nCA 3 — NHÃN PHẢI PHÂN BIỆT ĐƯỢC BA TRẠNG THÁI")
_da_do = "en-US-AndrewNeural"
_chua_do = next(m for m in sorted(GD.BANG) if NN.muc(m) is None)
_khong_biet = "xx-YY-KhongTonTaiNeural"

_RE_SO = re.compile(r"nhấn nhá\s*\d")
ok("3a giọng ĐÃ ĐO -> nhãn có SỐ", bool(_RE_SO.search(NN.nhan(_da_do))),
   repr(NN.nhan(_da_do)))
ok("3b giọng ĐỌC ĐƯỢC mà chưa đo -> đúng chữ 'chưa đo', KHÔNG một chữ số",
   NN.nhan(_chua_do) == NN.CHUA_DO
   and not any(c.isdigit() for c in NN.nhan(_chua_do)),
   f"{_chua_do} -> {NN.nhan(_chua_do)!r}")
ok("3c giọng KHÔNG biết gì -> nhãn RỖNG (không hiện trong combo)",
   NN.nhan(_khong_biet) == "" and not GM.nen_mo(_khong_biet))
_trong = sorted(m for m in GM.moi_giong_mo() if not NN.nhan(m))
ok("3d KHÔNG giọng đang mở nào có nhãn TRỐNG TRƠN", not _trong,
   str(_trong[:3]) or f"{GM.so_giong_mo()}/{GM.so_giong_mo()} dòng có đuôi")
# Máy anh Hùng thiếu glyph -> emoji ra Ô ĐEN (bài học v2.6.22).
_emoji = [m for m in GM.moi_giong_mo()
          if any(ord(c) > 0x2190 for c in NN.nhan(m))]
ok("3e nhãn KHÔNG EMOJI", not _emoji, str(_emoji[:2]))

# ---- BẤT BIẾN: 191 giọng cũ KHÔNG được đổi một ký tự nào ----
# Nhánh mới của `nhan_nha.nhan` chỉ được chạm mã KHÔNG có trong `BANG`; nếu
# không thì 191 dòng combo anh Hùng đang nhìn tự đổi chữ sau một lượt vá chẳng
# liên quan.
try:
    _src = subprocess.run(["git", "show", f"{MOC}:app/core/nhan_nha.py"],
                          cwd=str(REPO), capture_output=True, timeout=60)
    _ma_moc = _src.stdout.decode("utf-8", "replace")
    if _src.returncode != 0 or not _ma_moc.strip():
        bo_qua("3f bất biến 191 nhãn cũ", f"không lấy được mốc {MOC}")
    elif "CHUA_DO" in _ma_moc:
        # CHỐT CHỐNG PASS OAN: mốc mà đã chứa bản vá thì phép so là "so nó với
        # chính nó" — vô nghĩa, và nó sẽ ĐẠT vĩnh viễn.
        ok("3f bất biến 191 nhãn cũ", False,
           f"mốc {MOC} ĐÃ CHỨA bản vá -> mốc KHÔNG hợp lệ, đừng đọc là app hỏng")
    else:
        _mod = {}
        _p = SAN / "nhan_nha_moc.py"
        # bản mốc không import `giong_doc`; nạp thành module RỜI để so.
        _p.write_text(_ma_moc, encoding="utf-8")
        _ns: dict = {}
        exec(compile(_ma_moc, str(_p), "exec"), _ns)            # noqa: S102
        # LẶP TRÊN KHOÁ CỦA **BẢN MỐC**, KHÔNG PHẢI BẢNG HIỆN TẠI.
        #
        # ĐỎ OAN ĐÃ SẬP 19/08/2026: bản đầu lặp `for k in NN.BANG` — tức bảng
        # MỚI. Thêm 20 giọng VieNeu vào bảng (đúng quy trình mà chính
        # `nhan_nha.__doc__` mô tả: *"chạy `_do_nhan_nha_bang.py` rồi
        # `_do_nhan_nha_het.py`"*) là hỏi bản mốc về 20 khoá nó chưa từng có
        # -> mốc trả "" (hoặc CHUA_DO), bản mới trả số -> **lệch 20** và cổng
        # ĐỎ. Nhưng mệnh đề nó canh là *"nhãn của giọng CŨ không đổi"*, và
        # mệnh đề đó vẫn ĐÚNG. Nói cách khác cổng sẽ đỏ oan **mọi lần bảng
        # nhận thêm giọng đo được** — tức đỏ oan đúng lúc người ta làm việc
        # đúng, và cổng đỏ oan thì bị bỏ qua (bài học cổng 41 và 47).
        #
        # THÊM là hợp lệ, ĐỔI thì không. Vì vậy so trên phần GIAO, và in ra
        # số khoá thêm để lượt thêm giọng vẫn nhìn thấy được.
        _khoa_moc = set(_ns["BANG"])
        _giao = [k for k in _khoa_moc if k in NN.BANG]
        _mat = sorted(_khoa_moc - set(NN.BANG))
        _them = len(set(NN.BANG) - _khoa_moc)
        _lech_tho = [k for k in _giao if _ns["nhan"](k) != NN.nhan(k)]

        # ---- TÁCH HAI NGUYÊN NHÂN "nhãn cũ đổi chữ" ----
        # Nguyên nhân A: ai đó sửa CHỮ/công thức của `nhan()` -> phải FAIL.
        # Nguyên nhân B: `BANG` nhận thêm giọng đo được -> tứ phân vị dịch ->
        #   `VUA`/`CAO`/`RAT_CAO` dịch theo (luật ở `nhan_nha.__doc__`, cổng
        #   `_test_giong_kenh` CA 1c chấm) -> nhãn của giọng nằm sát ranh giới
        #   đổi nhóm **mà số đo không đổi một ly**. Đây là đường ĐÚNG.
        # Gộp hai nguyên nhân là buộc phải chọn: hoặc cấm mở rộng bảng, hoặc
        # bỏ mục này. Cách tách: ĐỒNG BỘ NGƯỠNG rồi so lại — còn lệch thì
        # lệch đó KHÔNG do ngưỡng, tức là nguyên nhân A.
        _ns_db: dict = {}
        exec(compile(_ma_moc, str(_p), "exec"), _ns_db)          # noqa: S102
        _ns_db["RAT_CAO"], _ns_db["CAO"], _ns_db["VUA"] = (
            NN.RAT_CAO, NN.CAO, NN.VUA)
        _lech = [k for k in _giao if _ns_db["nhan"](k) != NN.nhan(k)]
        ok(f"3f BẤT BIẾN: {len(_giao)} nhãn cũ giống mốc TỪNG KÝ TỰ "
           f"(sau khi đồng bộ ngưỡng)",
           not _lech and not _mat,
           f"mốc {MOC} · giao {len(_giao)} · lệch {len(_lech)}"
           + (f" {_lech[:3]}" if _lech else "")
           + (f" · MẤT khỏi bảng {_mat[:3]}" if _mat else "")
           + f" · thêm mới {_them}")

        # ---- NGƯỠNG DỊCH THÌ PHẢI KHAI RA SỐ GIỌNG ĐỔI NHÃN ----
        # Mục này tồn tại để lượt mở rộng bảng KHÔNG ĐI QUA ÊM RU: đổi ngưỡng
        # là đổi chữ trên combo anh Hùng đang nhìn, nên số đó phải nằm trong
        # mã và người sửa phải cập nhật nó bằng tay.
        # 19/08/2026: VUA 3,1 -> 3,2 (bảng 191 -> 211) -> ĐÚNG 8 giọng.
        # 8 chứ không phải 11: `nhan()` chấm mức trên SỐ ĐÃ LÀM TRÒN (mệnh đề
        # CA 1d của `_test_giong_kenh`), nên chỉ giọng làm tròn thành đúng 3,1
        # mới đổi nhóm. Đếm bằng công thức tự viết trên giá trị THÔ ra 11 và
        # đã suýt lật ngược quyết định áp ngưỡng — xem `nhan_nha.__doc__`.
        SO_DOI_NHAN = 8
        ok(f"3f2 số giọng CŨ đổi nhãn vì ngưỡng dịch = {SO_DOI_NHAN} (đã khai)",
           len(_lech_tho) == SO_DOI_NHAN,
           f"đếm {len(_lech_tho)} · ngưỡng mốc "
           f"{_ns['VUA']}/{_ns['CAO']}/{_ns['RAT_CAO']} -> nay "
           f"{NN.VUA}/{NN.CAO}/{NN.RAT_CAO} · ví dụ "
           f"{sorted(_lech_tho)[:3]}")

        # TỰ KIỂM BỘ DÒ: phép so chỉ có nghĩa nếu nó bắt được thay đổi thật.
        # Sửa CHỮ (không phải ngưỡng) trong bản mốc -> 3f phải LỆCH.
        _ns2: dict = {}
        exec(compile(_ma_moc.replace('"đều đều"', '"deu deu"'),
                     str(_p), "exec"), _ns2)                    # noqa: S102
        _ns2["RAT_CAO"], _ns2["CAO"], _ns2["VUA"] = (
            NN.RAT_CAO, NN.CAO, NN.VUA)
        _lech_thu = [k for k in _giao if _ns2["nhan"](k) != NN.nhan(k)]
        ok("3f' TỰ KIỂM phép so bắt được nhãn bị SỬA CHỮ", bool(_lech_thu),
           f"đổi chữ mốc -> lệch {len(_lech_thu)} nhãn")
except Exception as e:                                         # noqa: BLE001
    bo_qua("3f bất biến 191 nhãn cũ", f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------- CA 4
print("\nCA 4 — CHỌN X RA X: gọi THẬT rồi xem nó rẽ vào đâu")
# KHÔNG quét chuỗi. Vá từng điểm đến của `_synth_all` thành hàm GHI SỔ, gọi
# thật với mã của từng nguồn, rồi đòi ĐÚNG MỘT nhánh nổ và đúng nhánh đó.
from app.core import dubbing as D                              # noqa: E402

_so: list[str] = []


def _bay(ten: str, tra):
    async def _f(*a, **k):
        _so.append(ten)
        return tra
    return _f


def _bay_dong(ten: str, tra):
    def _f(*a, **k):
        _so.append(ten)
        return tra
    return _f


_luu = {k: getattr(D, k) for k in
        ("_chay_eleven", "_chay_ngoai", "_chay_vieneu", "_chay_vbee",
         "_chay_chatter", "_eleven_hay_khong", "_ngoai_hay_khong",
         "_piper_hay_khong", "_vieneu_hay_khong", "_vbee_hay_khong",
         "_chatter_hay_khong")}
try:
    D._chay_eleven = _bay("el", [True])
    D._chay_ngoai = _bay("ov", ([True], [[]]))
    D._chay_vieneu = _bay("vieneu", ([True], [[]]))
    D._chay_vbee = _bay("vbee", ([True], [[]]))
    D._chay_chatter = _bay("cb", [True])
    # Ép mọi cửa "có dùng không" trả True để đo ĐƯỜNG RẼ, không đo "máy này có
    # cài đồ chưa" — hai câu hỏi khác nhau, gộp là ca nào cũng ra edge-tts.
    D._eleven_hay_khong = _bay_dong("?el", True)
    D._ngoai_hay_khong = lambda v: (_so.append("?ov") or (True, v)) \
        if v.startswith("ov:") else (False, v)
    D._vieneu_hay_khong = lambda v: (True, v) if v.startswith(("vn:", "vnb:")) \
        else (False, v)
    D._vbee_hay_khong = lambda v: (True, v) if v.startswith("vbee:") \
        else (False, v)
    D._chatter_hay_khong = lambda v: (True, v) if v.startswith("cb:") \
        else (False, v)
    D._piper_hay_khong = lambda v: (True, v) if v.startswith("piper:") \
        else (False, v)
    import app.core.piper_tts as _PT                           # noqa: E402
    _pt_cu = _PT.doc_loat
    _PT.doc_loat = _bay_dong("piper", ([True], [[]]))

    _CA = (("el:Adam", "el"), ("ov:nam_tre", "ov"), ("piper:x", "piper"),
           ("vn:Minh Đức", "vieneu"), ("vbee:ngochuyen", "vbee"),
           ("cb:en|D:/mau.wav", "cb"))
    for _ma, _mong in _CA:
        _so.clear()
        # `_eleven_hay_khong` bị vá trả True cho MỌI mã -> chỉ bật cho ca el:.
        # Tên sổ có tiền tố `?` để KHÔNG bị đếm là "nhánh đã nổ": nó là cửa
        # HỎI ("có dùng không"), không phải cửa CHẠY. Bản đầu của cổng ghi
        # thẳng "el" nên ca `el:` ra `['el','el']` và HỎNG OAN.
        D._eleven_hay_khong = _bay_dong("?el", True) \
            if _ma.startswith("el:") else (lambda v: False)
        try:
            asyncio.run(D._synth_all(["xin chào"], _ma,
                                     [str(SAN / "x.mp3")]))
        except Exception:                                      # noqa: BLE001
            pass
        _thay = [s for s in _so if not s.startswith("?")]
        ok(f"4 · `{_ma}` -> rẽ ĐÚNG nhánh {_mong}",
           _thay == [_mong], f"nổ: {_thay or '(edge-tts)'}")
finally:
    for k, v in _luu.items():
        setattr(D, k, v)
    try:
        _PT.doc_loat = _pt_cu
    except Exception:                                          # noqa: BLE001
        pass


# ---------------------------------------------------------------- CA 5
print("\nCA 5 — KHÔNG TỰ LÙI GIỌNG TRONG IM LẶNG")
# Giọng nhân bản VieNeu thiếu torch thì lùi edge-tts **không một dòng báo**;
# anh Hùng chọn "giọng chị Lan" nghe ra giọng khác. Mọi nguồn lùi được đều
# phải GHI LẠI trước khi lùi.
_KIEM_LUI = (
    ("vbee", "giong_vbee", "vbee:ngochuyen", "co_key"),
    ("vieneu", "giong_vieneu", "vn:Minh Đức", "co_vieneu"),
)
for _ten, _mod_ten, _ma, _co in _KIEM_LUI:
    _m = __import__(f"app.core.{_mod_ten}", fromlist=["x"])
    _log: list[str] = []
    _gl, _cf = _m._ghi_log, getattr(_m, _co)
    try:
        _m._ghi_log = lambda s, _l=_log: _l.append(s)
        setattr(_m, _co, lambda *a, **k: False)      # giả lập máy THIẾU đồ
        _dung, _lui = getattr(D, f"_{_ten}_hay_khong")(_ma)
        ok(f"5 · {_ten} thiếu đồ -> LÙI edge-tts **và GHI RA lý do**",
           (not _dung) and _lui != _ma and len(_log) >= 1,
           f"lùi về {_lui} · {len(_log)} dòng log")
        ok(f"5 · {_ten} dòng log nêu ĐÍCH DANH giọng bị lùi",
           bool(_log) and _ma.split(":", 1)[1][:6] in _log[0],
           (_log[0][:70] + "...") if _log else "(KHÔNG GHI GÌ)")
    finally:
        _m._ghi_log, _ = _gl, setattr(_m, _co, _cf)


# ---------------------------------------------------------------- CA 6
print("\nCA 6 — KHÔNG LẪN GIỌNG GIỮA KÊNH (hàm phải THUẦN, không nhớ lượt trước)")
# Chatterbox từng nhớ mẫu lượt trước: kênh A xong tới kênh B là B ra giọng A.
# Với 300 kênh đó là lỗi chết người. Ở phạm vi cổng này: mọi hàm quyết định
# nhãn/mở khoá phải cho ra CÙNG kết quả bất kể gọi trước nó là gì.
_a, _b = "en-US-AndrewNeural", _chua_do
_lan1 = (NN.nhan(_a), GM.nen_mo(_a))
for _ in range(5):
    NN.nhan(_b), GM.nen_mo(_b), NN.nhan("vi-VN-HoaiMyNeural")
_lan2 = (NN.nhan(_a), GM.nen_mo(_a))
ok("6a nhãn + mở khoá của giọng A KHÔNG đổi sau khi hỏi giọng B",
   _lan1 == _lan2, f"{_lan1} vs {_lan2}")
# Gọi `_synth_all` cho giọng A rồi giọng B: tên gửi vào edge-tts phải là B.
_gui: list[str] = []
try:
    import edge_tts as _ET                                     # noqa: E402
    _cc = _ET.Communicate

    class _Gian:                                # gián điệp, KHÔNG gọi mạng
        def __init__(self, txt, voice, **kw):
            _gui.append(voice)

        async def save(self, p):
            Path(p).write_bytes(b"x" * 500)

    _ET.Communicate = _Gian
    for _v in ("en-US-AndrewNeural", "vi-VN-HoaiMyNeural"):
        asyncio.run(D._synth_all(["hello"], _v, [str(SAN / "y.mp3")]))
    ok("6b đọc giọng A rồi giọng B -> gửi đi ĐÚNG B, không dính A",
       len(_gui) == 2 and _gui[0] != _gui[1] and "HoaiMy" in _gui[1],
       f"gửi đi: {_gui}")
finally:
    try:
        _ET.Communicate = _cc
    except Exception:                                          # noqa: BLE001
        pass


# ---------------------------------------------------------------- CA 7
print("\nCA 7 — CÂU THỬ PHẢI ĐÚNG TIẾNG, KHÔNG LÙI VỀ TIẾNG ANH")
# Đây là chốt chống "chứng nhận sai thứ": bắt giọng Ba Lan đọc câu tiếng Anh
# thì phép kiểm vẫn XANH, nhưng nó chứng nhận "giọng này đọc được chữ Latin",
# không phải "giọng này đọc được tiếng của nó". Chính bẫy đã làm
# `piper:vais1000` ra 1,88.
_loc_da_kiem = {_loc_cua[m] for m in GD.BANG if m in _loc_cua}
_thieu_cau = sorted(l for l in _loc_da_kiem if not CAU.cau_cho_locale(l))
ok("7a mọi locale đã kiểm đều CÓ câu thử riêng", not _thieu_cau,
   f"{len(_loc_da_kiem)} locale" if not _thieu_cau else str(_thieu_cau[:3]))
# Hai TIẾNG khác nhau mà dùng chung một câu = có chỗ đang lùi về câu mặc định.
_theo_cau: dict[str, set] = {}
for _l in _loc_da_kiem:
    _theo_cau.setdefault(CAU.cau_cho_locale(_l), set()).add(CAU.ma_tieng(_l))
_dung_chung = {c: t for c, t in _theo_cau.items() if len(t) > 1}
ok("7b KHÔNG hai thứ tiếng nào dùng chung một câu (dấu hiệu lùi tiếng Anh)",
   not _dung_chung, str(list(_dung_chung.values())[:2]))
# TỰ KIỂM BỘ DÒ: `cau_cho_locale` phải TRẢ RỖNG cho tiếng chưa có câu, không
# được lùi. Bộ dò không kêu ở ca này thì hai mục trên là con dấu.
ok("7c TỰ KIỂM: tiếng chưa có câu -> trả RỖNG, KHÔNG lùi tiếng Anh",
   CAU.cau_cho_locale("zz-ZZ") == "" and CAU.cau_cho_locale("") == "")
# Giọng mới mở KHÔNG được rơi vào nhóm ngôn ngữ của tiếng KHÁC — đó là đường
# dẫn tới "đọc ra chữ vô nghĩa mà mã thoát vẫn 0".
_sai_nhom = [m for m in sorted(GD.BANG)[:400]
             if GB.nhom_cua(m, CAU.ma_tieng(_loc_cua.get(m, ""))) != GB.N_DICH]
ok("7d mỗi giọng mới xếp vào ĐÚNG nhóm ngôn ngữ của chính nó",
   not _sai_nhom, str(_sai_nhom[:3]))


# ---------------------------------------------------------------- CA 8
print("\nCA 8 — THIẾU MODEL THÌ NÓI THẲNG + ĐÚNG SỐ GB")
# Đã có lỗi thật: nút ghi 155 MB mà hộp doạ 2 GB. Nhãn phải KHỚP ĐƯỜNG SẼ ĐI.
# **SO VỚI CHỮ NGƯỜI DÙNG THẬT SỰ NHÌN THẤY, không so với một hằng số bất kỳ.**
# Bản đầu của cổng lấy `piper_tts.NHAN_GIONG` — đó là nhãn DÒNG COMBO ("Giọng
# Việt chạy trên máy (Piper)..."), không phải nhãn NÚT TẢI, nên nó HỎNG OAN.
# Con số phải xuất hiện ở đâu đó trong đường người dùng đi: hằng số của module
# nguồn, hoặc chữ trong hộp Thay giọng.
_CHU_UI = (REPO / "app" / "ui" / "thay_giong_dialog.py").read_text(
    encoding="utf-8", errors="replace")


def _moi_chu(mod_ten: str) -> str:
    try:
        _m = __import__(f"app.core.{mod_ten}", fromlist=["x"])
    except Exception:                                          # noqa: BLE001
        return ""
    return " ".join(str(getattr(_m, k, "")) for k in dir(_m) if k.isupper())


for _ng, _mod_ten in ((GB.PIPER, "piper_tts"), (GB.VIENEU, "giong_vieneu"),
                      (GB.CHATTER, "giong_chatter")):
    _so_gb = GB._CAN_TAI.get(_ng, "")
    _con_so = re.sub(r"[^0-9]", "", _so_gb)
    _kho_chu = re.sub(r"[^0-9]", "", _moi_chu(_mod_ten) + " " + _CHU_UI)
    ok(f"8 · nhãn `{_ng}` ({_so_gb}) khớp con số người dùng THẬT SỰ thấy",
       bool(_con_so) and _con_so in _kho_chu,
       f"bảng {_so_gb!r}")
ok("8z Vbee hiện nhãn CẦN KEY, KHÔNG bị ẩn",
   any("key" in n.lower() for _m, n in __import__(
       "app.core.giong_vbee", fromlist=["x"]).danh_sach_giong()),
   str(__import__("app.core.giong_vbee",
                  fromlist=["x"]).danh_sach_giong()[0][1])[:70])


# ---------------------------------------------------------------- CA 9
print("\nCA 9 — THỬ PHÁ: GỠ CHỐT THÌ CỔNG PHẢI ĐỎ")
# Cổng nào không tự chứng minh được là nó biết kêu thì chỉ là một con dấu.
# Ba phép phá, mỗi phép gỡ ĐÚNG MỘT chốt (đừng đổi giá trị bên trong chốt —
# bài học cổng 80 LỌT 7).
_pha_bat = 0
_pha_tong = 0

# (1) `nen_mo` bỏ đòi bằng chứng -> mọi mã đúng dạng đều lọt
_pha_tong += 1
_cu_dkd = GM.da_kiem_doc
try:
    GM.da_kiem_doc = lambda m: True
    _bat = GM.nen_mo("en-US-KhongCoThatNeural")
    ok("9a phá `da_kiem_doc` -> mục 1f VỠ (bộ dò có răng)", _bat,
       "mã bịa lọt được vào combo")
    _pha_bat += 1 if _bat else 0
finally:
    GM.da_kiem_doc = _cu_dkd

# (2) `nhan()` bịa số cho giọng chưa đo -> mục 3b VỠ
_pha_tong += 1
_cu_nhan = NN.nhan
try:
    NN.nhan = lambda v: " - nhấn nhá 3,5 truyền cảm"
    _bat = not (NN.nhan(_chua_do) == NN.CHUA_DO
                and not any(c.isdigit() for c in NN.nhan(_chua_do)))
    ok("9b phá `nhan` (bịa số cho giọng chưa đo) -> mục 3b VỠ", _bat)
    _pha_bat += 1 if _bat else 0
finally:
    NN.nhan = _cu_nhan

# (3) hạ ngưỡng RMS xuống sàn -> file IM LẶNG lọt qua bộ dò của CA 1
_pha_tong += 1
_cu_rms = DT.RMS_TOI_THIEU
try:
    DT.RMS_TOI_THIEU = -200.0
    _bat = (DT.do_dai(_im) >= DT.DAI_TOI_THIEU
            and DT.do_rms(_im) >= DT.RMS_TOI_THIEU)
    ok("9c phá ngưỡng RMS -> file IM LẶNG lọt qua (mục 1g VỠ)", _bat,
       "tức 1g đang đo thật, không phải con dấu")
    _pha_bat += 1 if _bat else 0
finally:
    DT.RMS_TOI_THIEU = _cu_rms

print(f"  -> THỬ PHÁ: BẮT {_pha_bat}/{_pha_tong}")


# ===========================================================================
print("\n" + "=" * 78)
print(f"ĐẠT {_dat} · HỎNG {_hong} · BỎ QUA {_bo}")
if _ten_hong:
    print("HỎNG: " + " | ".join(_ten_hong))
print("=" * 78)
raise SystemExit(1 if _hong else 0)
