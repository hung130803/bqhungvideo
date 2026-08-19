# -*- coding: utf-8 -*-
"""CỔNG 82 — CHATTERBOX ĐÃ NỐI THẬT: `cb:` ĐƯỢC NHẬN · RẼ ĐÚNG CỬA · KHÔNG
TRỘN GIỌNG GIỮA HAI KÊNH.

**VÌ SAO CÓ CỔNG NÀY.** `app/core/giong_chatter.py` viết xong ở `9aa4377` với
đúng hợp đồng `doc_loat` của `piper_tts`/`giong_ngoai`, và trong chính file đó
có một dòng dặn *"luồng lắp giao diện phải thêm `("cb:", CHATTER)` vào
`giong_bang._TIEN_TO`"*. Đo trước khi vá (19/08/2026):

    grep -c "cb:" app/core/giong_bang.py   ->  0
    grep -c "cb:" app/core/dubbing.py      ->  0

Tức **không một dòng nào trong app biết tới tiền tố đó**. Hai hậu quả, cả hai
đều "app vẫn chạy, mã thoát vẫn 0, không một dòng báo":

1. `giong_bang.nguon("cb:en|D:/mau.wav")` trả **`edge`** -> giọng nhân bản rơi
   vào nhóm *"MIỄN PHÍ (edge-tts) - các tiếng khác"*, mất nhãn "cần tải 5,5 GB"
   và mất cảnh báo "cần GPU".
2. `dubbing._synth_all` không có nhánh nào bắt `cb:` -> mã giọng rơi thẳng
   xuống nhánh edge-tts, `edge_tts.Communicate("...", "cb:en|D:\\mau.wav")`
   hỏng -> thử lại 4 lần -> câu RỖNG, HOẶC người dùng chọn giọng nhân bản của
   kênh mình mà **nghe ra Hoài My**.

Đó đúng là "giọng chết CHỌN X RA Y" — lỗi `ov:nu_am` và `vn:` đã sập hai lần.

**CỔNG NÀY GỌI THẬT RỒI XEM NÓ RẼ VÀO ĐÂU, KHÔNG QUÉT CHUỖI.** Quét chuỗi thì
một phép phá giữ nguyên mặt chữ mà đổi ý nghĩa vẫn lọt (PASS oan — cổng 56d),
còn quét kiểu "có mặt không" thì chính DÒNG GHI CHÚ giải thích bản vá bị kể là
vi phạm (ĐỎ oan — cổng 47/51/53/54/73 đã sập 5 lần). Nên CA 3-5 chạy
`asyncio.run(dubbing._synth_all(...))` THẬT rồi đọc SỔ ai bị gọi.

**CA 7 LÀ CA ĐẮT NHẤT — LỖI CHẶN SẢN XUẤT.** `ChatterboxMultilingualTTS` CẤT
mẫu tham chiếu lên chính đối tượng model (`self.conds`); gọi `generate()` mà
không kèm `audio_prompt_path` thì nó **dùng lại mẫu của lượt TRƯỚC**, chứ
không quay về giọng mặc định — và không ném lỗi. Bẫy này đã sập thật một lần
ở `_do_chatter.py`: arm ĐỐI CHỨNG ÂM xếp cuối nên thừa hưởng mẫu m7 và đo ra
`cos(m7, mặc định) = 1,000`, tức **đối chứng âm không hề là đối chứng**, mà
bảng số vẫn đẹp. Với app thì nó là: **đọc kênh A rồi kênh B là kênh B ra giọng
kênh A**. 300 kênh thì đây là lỗi chết người.

CA 7 chạy **CHÍNH script runner `_MA_DOC`** trong **tiến trình con THẬT**, chỉ
thay `chatterbox`/`torch`/`torchaudio` bằng gói GIẢ mô phỏng ĐÚNG cái tính
dính đó. Gói giả **cố ý nhớ mẫu QUA CẢ TIẾN TRÌNH** (cất vào file sổ): thực tế
`_chay` luôn sinh tiến trình mới nên mẫu tự reset, nhưng dựa vào đó là dựa vào
một lớp chắn có thể bị "tối ưu" mất bất cứ lúc nào. Làm chặt hơn thực tế thì
CA 7b (tự kiểm) mới có răng — và CA 7d đo RIÊNG lớp chắn thứ hai (pid khác
nhau) để không lẫn hai lớp vào một.

**KHÔNG GỌI MẠNG · KHÔNG NẠP MODEL THẬT · KHÔNG ĐỐT GPU · KHÔNG TỐN LƯỢT
GROQ.** Toàn bộ là hàm thuần + tiến trình con chạy gói giả.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import shutil
import struct
import sys
import tempfile
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass
os.environ.setdefault("BQ_QSETTINGS_INI", "1")

# HỘP CÁT: đặt TRƯỚC mọi import của app — `config` đọc biến này lúc NẠP, đặt
# sau là cổng ghi log/DB thẳng vào dữ liệu thật của anh Hùng.
_SB = Path(tempfile.mkdtemp(prefix="bq_c82_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")

DAT = HONG = 0
_HONG: list[str] = []


def ok(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def _wav(p: Path, giay: float = 0.4, sr: int = 24000) -> None:
    """WAV im lặng THẬT (>1000 byte) — `doc_loat` đòi `st_size > 1000`."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack("<h", 0) * int(sr * giay))


# ===========================================================================
print("=" * 78)
print("CỔNG 82 — CHATTERBOX ĐÃ NỐI THẬT")
print("=" * 78)

from app.core import dubbing                                    # noqa: E402
from app.core import giong_bang as GB                           # noqa: E402
from app.core import giong_chatter as gc                        # noqa: E402
from app.core import thay_giong as TG                           # noqa: E402

MA_EN = "cb:en|" + str(_SB / "mau_a.wav").replace("\\", "/")
MA_JA = "cb:ja|" + str(_SB / "mau_b.wav").replace("\\", "/")

print("\nCA 1 — `cb:` ĐÃ ĐĂNG KÝ Ở `giong_bang` (nguồn · tên · tiền · tải)")
ok("1a nguon('cb:...') = CHATTER, KHÔNG còn trả 'edge'",
   GB.nguon(MA_EN) == GB.CHATTER, f"nguon={GB.nguon(MA_EN)}")
ok("1b có tên đọc được cho người dùng",
   GB.TEN_NGUON.get(GB.CHATTER) == "Chatterbox")
ok("1c tính là MIỄN PHÍ (giấy phép MIT, chạy trên máy, 0 lượt mạng)",
   GB.mien_phi(MA_EN) is True)
ok("1d có nhãn CẦN TẢI và số khớp `giong_chatter.NHAN_TAI`",
   GB.can_tai(MA_EN) == "5,5 GB" and "5,5 GB" in gc.NHAN_TAI,
   f"can_tai={GB.can_tai(MA_EN)!r}")
ok("1e xếp là giọng CHẠY TRÊN MÁY", GB.tren_may(MA_EN) is True)
ok("1f cột `khop_ms` để RỖNG (76,2 ms đo bằng thước Groq, "
   "đặt cạnh 15,7 ms của silencedetect là TRỘN HAI THƯỚC)",
   GB.khop_ms(MA_EN) == "", f"{GB.khop_ms(MA_EN)!r}")
ok("1g `cb:en|<mẫu>` KHÔNG bị coi là biến thể cao độ",
   GB.la_bien_the(MA_EN) is False)
ok("1h `_bo_pitch` KHÔNG cắt mất đường dẫn mẫu",
   GB._bo_pitch(MA_EN) == MA_EN, GB._bo_pitch(MA_EN))
ok("1i biến thể cao độ THẬT vẫn bị cắt như cũ (không sửa quá tay)",
   GB._bo_pitch("vi-VN-NamMinhNeural|-20Hz") == "vi-VN-NamMinhNeural"
   and GB.la_bien_the("vi-VN-NamMinhNeural|-20Hz") is True)
_duoi = GB.duoi_dong(MA_EN, "Chị Lan")
ok("1j đuôi dòng nói ĐỦ ba điều: cần tải · cần GPU · KHÔNG có tiếng Việt",
   all(s in _duoi for s in ("cần tải", "GPU", "KHÔNG có tiếng Việt")), _duoi)
ok("1k nhãn đã tự nói rồi thì KHÔNG dán thêm (dòng dài gấp đôi vô ích)",
   GB.duoi_dong(MA_EN, gc.nhan_giong(MA_EN, "Chị Lan")) == "")
ok("1l đuôi dòng KHÔNG EMOJI", all(ord(c) < 0x2190 for c in _duoi))

print("\nCA 2 — KHÔNG BAO GIỜ HIỆN Ở NHÓM TIẾNG VIỆT")
ok("2a nhom_cua(cb:, 'vi') = TRÊN MÁY, KHÔNG phải nhóm ngôn ngữ đích",
   GB.nhom_cua(MA_EN, "vi") == GB.N_MAY, GB.nhom_cua(MA_EN, "vi"))
ok("2b kể cả mã ghi lang='ja'/'en' cũng không lọt nhóm đích",
   all(GB.nhom_cua(m, nn) == GB.N_MAY
       for m in (MA_EN, MA_JA) for nn in ("vi", "en", "ja", "zh")))
_ds = [("Hoài My (Nữ)", "vi-VN-HoaiMyNeural"),
       ("Nam Minh (Nam)", "vi-VN-NamMinhNeural"),
       (gc.nhan_giong(MA_EN, "Chị Lan"), MA_EN),
       ("Aria", "en-US-AriaNeural")]
_ra = GB.gom_nhom(_ds, "vi")
_nhom_hien = ""
_nhom_cua_cb = ""
for _n, _v in _ra:
    if not _v:
        _nhom_hien = _n
    elif _v == MA_EN:
        _nhom_cua_cb = _nhom_hien
ok("2c dựng CẢ danh sách rồi đọc lại: dòng Chatterbox nằm dưới nhãn TRÊN MÁY",
   "TRÊN MÁY" in _nhom_cua_cb, _nhom_cua_cb)
ok("2d nhóm 'giọng Tiếng Việt' KHÔNG chứa mã cb:",
   not any(v == MA_EN for n, v in _ra if v)
   or "Tiếng Việt" not in _nhom_cua_cb)
ok("2e KHÔNG mất giọng nào khi gom nhóm (bất biến cổng 79)",
   {v for _n, v in _ra if v} == {v for _n, v in _ds})
_nhan = gc.nhan_giong(MA_EN, "Chị Lan")
ok("2f nhãn mang ĐỦ ba cảnh báo: giấy phép · chất lượng · máy",
   all(s in _nhan for s in ("MIT", "76 ms", "KHÔNG có tiếng Việt", "GPU")))
ok("2g nhãn nói rõ tiếng Việt hỏng KIỂU GÌ (không ném lỗi, vẫn báo xong)",
   "vẫn báo thành công" in _nhan or "chuỗi vô nghĩa" in _nhan)

print("\nCA 3 — GỌI THẬT `_synth_all` / `_synth_all_words`: `cb:` PHẢI RẼ VÀO "
      "CHATTERBOX, KHÔNG RƠI XUỐNG edge-tts")

_goi_cb: list[tuple] = []
_goi_edge: list[str] = []
_that_doc_loat = gc.doc_loat
_that_co = gc.co_chatter


def _gian_diep_doc_loat(texts, paths, voice, rate="+0%", han_giay=3600,
                        on_msg=None):
    """Thay ĐÚNG một lá: phần trên (cửa chung) vẫn chạy mã THẬT."""
    _goi_cb.append((tuple(texts), voice))
    for p in paths:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        Path(p).write_bytes(b"\0" * 4096)
    return [True] * len(texts)


import edge_tts                                                 # noqa: E402
_that_comm = edge_tts.Communicate


class _EdgeGianDiep:
    """edge-tts giả: ghi file HỢP LỆ ngay lượt đầu.

    Cố ý KHÔNG ném: ném thì `_synth_all` thử lại 4 lần với `sleep` cộng dồn
    15 giây MỖI CÂU, và một ca hỏng sẽ mất hàng phút thay vì báo ngay.
    """

    def __init__(self, text, voice, **kw):
        _goi_edge.append(str(voice))
        self._t = str(text or "")

    async def save(self, p):
        Path(p).write_bytes(b"\0" * 4096)

    async def stream(self):
        yield {"type": "audio", "data": b"\0" * 4096}
        yield {"type": "WordBoundary", "offset": 0, "duration": 1_000_000,
               "text": (self._t.split() or ["x"])[0]}


def _dat_gian_diep() -> None:
    gc.doc_loat = _gian_diep_doc_loat
    gc.co_chatter = lambda: True
    edge_tts.Communicate = _EdgeGianDiep


def _tra_ve_that() -> None:
    gc.doc_loat = _that_doc_loat
    gc.co_chatter = _that_co
    edge_tts.Communicate = _that_comm


_dat_gian_diep()
_p3 = [str(_SB / "r0.mp3"), str(_SB / "r1.mp3")]
_goi_cb.clear(); _goi_edge.clear()
_ok3 = asyncio.run(dubbing._synth_all(["một", "hai"], MA_EN, _p3, lang="en"))
ok("3a `_synth_all` gọi ĐÚNG Chatterbox 1 lần, edge-tts 0 lần",
   len(_goi_cb) == 1 and len(_goi_edge) == 0,
   f"chatter={len(_goi_cb)} · edge={len(_goi_edge)}")
ok("3b mã giọng truyền xuống NGUYÊN VẸN (còn cả đường dẫn mẫu)",
   bool(_goi_cb) and _goi_cb[0][1] == MA_EN,
   _goi_cb[0][1] if _goi_cb else "-")
ok("3c trả ok đúng số câu", _ok3 == [True, True], str(_ok3))

_goi_cb.clear(); _goi_edge.clear()
_p3b = [str(_SB / "w0.mp3"), str(_SB / "w1.mp3")]
_ok3b, _moc3b = asyncio.run(
    dubbing._synth_all_words(["một", "hai"], MA_EN, _p3b, lang="en"))
ok("3d `_synth_all_words` cũng rẽ vào Chatterbox, edge-tts 0 lần",
   len(_goi_cb) == 1 and len(_goi_edge) == 0,
   f"chatter={len(_goi_cb)} · edge={len(_goi_edge)}")
ok("3e trả (ok, mốc) đúng hình dạng — mốc rỗng khi máy chưa có bộ gióng hàng",
   _ok3b == [True, True] and isinstance(_moc3b, list)
   and len(_moc3b) == 2)
_dem = {"n": 0}
_goi_cb.clear()
asyncio.run(dubbing._synth_all(["một", "hai"], MA_EN,
                               [str(_SB / "d0.mp3"), str(_SB / "d1.mp3")],
                               on_done=lambda i: _dem.__setitem__(
                                   "n", _dem["n"] + 1), lang="en"))
ok("3f `on_done` được gọi ĐÚNG một lần mỗi câu (thanh tiến trình không "
   "chạy quá 100%)", _dem["n"] == 2, f"{_dem['n']} lượt")

print("\nCA 4 — THIẾU MODEL -> LÙI ÊM VỀ edge-tts, **CÓ GHI LOG**")
_log_d = Path(os.environ["BQ_DATA_DIR"]) / "logs"
for _f in _log_d.glob("giong_chatter_*.log"):
    _f.unlink()
gc.co_chatter = lambda: False
_goi_cb.clear(); _goi_edge.clear()
_ok4 = asyncio.run(dubbing._synth_all(
    ["một", "hai"], MA_EN, [str(_SB / "f0.mp3"), str(_SB / "f1.mp3")],
    lang="en"))
ok("4a KHÔNG gọi Chatterbox, ĐỌC BẰNG edge-tts (video vẫn ra, chỉ khác giọng)",
   len(_goi_cb) == 0 and len(_goi_edge) == 2,
   f"chatter={len(_goi_cb)} · edge={len(_goi_edge)}")
ok("4b giọng lùi về là giọng edge-tts THẬT, không phải chuỗi `cb:...`",
   bool(_goi_edge) and not _goi_edge[0].startswith("cb:"), str(_goi_edge[:1]))
ok("4c lùi về giọng ĐÚNG THỨ TIẾNG của mã (cb:en -> giọng en-*), "
   "không lùi về giọng Việt",
   bool(_goi_edge) and _goi_edge[0].startswith("en-"), str(_goi_edge[:1]))
_dong = "".join(p.read_text(encoding="utf-8")
                for p in _log_d.glob("giong_chatter_*.log"))
ok("4d GHI LOG lý do lùi (lùi êm mà im lặng = hỏng âm thầm)",
   "LÙI về edge-tts" in _dong, _dong.strip().splitlines()[-1:] or ["(rỗng)"])
ok("4e mã giọng SAI DẠNG (thiếu đường dẫn mẫu) cũng lùi êm + ghi log",
   (lambda: (_goi_edge.clear(), gc._ghi_log.__self__ if False else None,
             asyncio.run(dubbing._synth_all(
                 ["x"], "cb:en", [str(_SB / "g0.mp3")], lang="en")),
             len(_goi_edge) == 1)[-1])())
gc.co_chatter = lambda: True

print("\nCA 5 — ĐỌC HỎNG CẢ LOẠT -> ĐỌC LẠI CẢ LOẠT BẰNG edge-tts "
      "(all-or-nothing, KHÔNG trộn hai giọng)")


def _cb_hong(texts, paths, voice, rate="+0%", han_giay=3600, on_msg=None):
    _goi_cb.append((tuple(texts), voice))
    return [False] * len(texts)


gc.doc_loat = _cb_hong
_goi_cb.clear(); _goi_edge.clear()
_dem2 = {"n": 0}
_ok5 = asyncio.run(dubbing._synth_all(
    ["một", "hai", "ba"], MA_EN,
    [str(_SB / f"h{i}.mp3") for i in range(3)],
    on_done=lambda i: _dem2.__setitem__("n", _dem2["n"] + 1), lang="en"))
ok("5a đã THỬ Chatterbox rồi mới lùi (không bỏ qua nó)", len(_goi_cb) == 1)
ok("5b đọc LẠI **CẢ LOẠT** bằng edge-tts (3/3 câu), không chỉ câu hỏng",
   len(_goi_edge) == 3, f"{len(_goi_edge)} câu")
ok("5c chỉ MỘT giọng edge cho cả loạt (không lẫn hai giọng)",
   len(set(_goi_edge)) == 1, str(set(_goi_edge)))
ok("5d video vẫn ra đủ câu", _ok5 == [True] * 3, str(_ok5))
ok("5e `on_done` vẫn ĐÚNG một lần mỗi câu dù đi hai chặng",
   _dem2["n"] == 3, f"{_dem2['n']} lượt")
_goi_cb.clear(); _goi_edge.clear()
_ok5w, _m5w = asyncio.run(dubbing._synth_all_words(
    ["một", "hai"], MA_EN, [str(_SB / f"k{i}.mp3") for i in range(2)],
    lang="en"))
ok("5f `_synth_all_words` lùi y hệt (sót một cửa là video lẫn hai giọng)",
   len(_goi_cb) == 1 and len(_goi_edge) == 2 and _ok5w == [True, True],
   f"chatter={len(_goi_cb)} · edge={len(_goi_edge)}")
_tra_ve_that()

print("\nCA 6 — `tach_giong_pitch` KHÔNG ĐƯỢC NUỐT ĐƯỜNG DẪN MẪU")
ok("6a mã Chatterbox đi qua nguyên vẹn",
   TG.tach_giong_pitch(MA_EN) == (MA_EN, "+0Hz"), str(TG.tach_giong_pitch(MA_EN)))
ok("6b `tach_ma` sau đó vẫn đọc ra ngôn ngữ + đường dẫn mẫu",
   gc.tach_ma(TG.tach_giong_pitch(MA_EN)[0])[0] == "en"
   and gc.tach_ma(TG.tach_giong_pitch(MA_EN)[0])[1].endswith("mau_a.wav"))
ok("6c biến thể cao độ THẬT vẫn tách như cũ (không sửa quá tay)",
   TG.tach_giong_pitch("vi-VN-NamMinhNeural|-20Hz")
   == ("vi-VN-NamMinhNeural", "-20Hz"))
ok("6d luật 'pitch LẠ thì BỎ' vẫn nguyên (cổng 63 CA 1e)",
   TG.tach_giong_pitch("vi-VN-NamMinhNeural|nhanh")
   == ("vi-VN-NamMinhNeural", "+0Hz"))
ok("6e TỰ KIỂM BỘ DÒ: chạy lại CÔNG THỨC CŨ trên mã Chatterbox thì nó "
   "PHẢI nuốt mất mẫu (chứng minh 6a đang đo thật)",
   MA_EN.partition("|")[0] != MA_EN
   and gc.tach_ma(MA_EN.partition("|")[0]) == ("", ""),
   f"cũ -> {MA_EN.partition('|')[0]}")

print("\nCA 7 — KÊNH B KHÔNG ĐƯỢC RA GIỌNG KÊNH A "
      "(chạy CHÍNH runner `_MA_DOC` trong tiến trình con THẬT)")

_STUB = _SB / "stub"
_SO = _SB / "so_generate.json"


def _dung_stub() -> None:
    """Gói GIẢ mô phỏng ĐÚNG tính dính `self.conds` của thư viện thật."""
    (_STUB / "chatterbox").mkdir(parents=True, exist_ok=True)
    (_STUB / "torch.py").write_text(
        "import types\n"
        "__version__ = '0.0-gia'\n"
        "def manual_seed(x):\n    return None\n"
        "cuda = types.SimpleNamespace(\n"
        "    is_available=lambda: False,\n"
        "    max_memory_allocated=lambda: 0)\n",
        encoding="utf-8")
    (_STUB / "torchaudio.py").write_text(
        "import struct, wave\n"
        "def save(p, x, sr):\n"
        "    with wave.open(str(p), 'wb') as w:\n"
        "        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)\n"
        "        w.writeframes(struct.pack('<h', 0) * int(sr * 0.4))\n",
        encoding="utf-8")
    (_STUB / "chatterbox" / "__init__.py").write_text("", encoding="utf-8")
    (_STUB / "chatterbox" / "mtl_tts.py").write_text(
        "import json, os\n"
        "SO = os.environ['BQ_CB_SO']\n"
        "\n"
        "\n"
        "def _doc():\n"
        "    try:\n"
        "        with open(SO, 'r', encoding='utf-8') as f:\n"
        "            return json.load(f)\n"
        "    except Exception:\n"
        "        return {'goi': [], 'dinh': ''}\n"
        "\n"
        "\n"
        "def _ghi(d):\n"
        "    with open(SO, 'w', encoding='utf-8') as f:\n"
        "        json.dump(d, f, ensure_ascii=False)\n"
        "\n"
        "\n"
        "class _T:\n"
        "    def __init__(self, n):\n"
        "        self.shape = (1, n)\n"
        "    def detach(self):\n"
        "        return self\n"
        "    def cpu(self):\n"
        "        return self\n"
        "    def dim(self):\n"
        "        return 2\n"
        "    def __getitem__(self, k):\n"
        "        return self\n"
        "\n"
        "\n"
        "class ChatterboxMultilingualTTS:\n"
        "    sr = 24000\n"
        "\n"
        "    @classmethod\n"
        "    def from_pretrained(cls, device='cpu'):\n"
        "        return cls()\n"
        "\n"
        "    def generate(self, text, language_id='en',\n"
        "                 audio_prompt_path=None):\n"
        "        # BENH THAT CUA THU VIEN: mau duoc CAT lai; thieu tham so thi\n"
        "        # dung lai mau cua luot TRUOC chu khong ve giong mac dinh.\n"
        "        d = _doc()\n"
        "        if audio_prompt_path:\n"
        "            d['dinh'] = audio_prompt_path\n"
        "        d['goi'].append({'text': text, 'lang': language_id,\n"
        "                         'truyen': audio_prompt_path,\n"
        "                         'thuc_dung': d['dinh'],\n"
        "                         'pid': os.getpid()})\n"
        "        _ghi(d)\n"
        "        return _T(9600)\n",
        encoding="utf-8")


_dung_stub()
_wav(_SB / "mau_a.wav")
_wav(_SB / "mau_b.wav")
_SO.write_text(json.dumps({"goi": [], "dinh": ""}), encoding="utf-8")
os.environ["BQ_CB_SO"] = str(_SO)
os.environ["PYTHONPATH"] = str(_STUB)

_that_py = gc._python_chatter
_that_gpu = gc.co_gpu_nvidia
gc._python_chatter = lambda: (sys.executable, [])
gc.co_gpu_nvidia = lambda: False
_MA_GOC = gc._MA_DOC


def _chay_kenh(ma: str, n: int, tag: str) -> list:
    ra = [str(_SB / f"{tag}{i}.mp3") for i in range(n)]
    return gc.doc_loat([f"cau {i}" for i in range(n)], ra, ma, han_giay=180)


def _so_doc() -> dict:
    try:
        return json.loads(_SO.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"goi": [], "dinh": ""}


_okA = _chay_kenh(MA_EN, 2, "A")
_okB = _chay_kenh(MA_JA, 2, "B")
_g = _so_doc()["goi"]
_gA = [x for x in _g if "cau" in x["text"]][:2]
_gB = [x for x in _g if "cau" in x["text"]][2:4]
ok("7a runner chạy THẬT được với gói giả (2 kênh × 2 câu = 4 lượt generate)",
   len(_g) == 4 and _okA == [True, True] and _okB == [True, True],
   f"{len(_g)} lượt · okA={_okA} · okB={_okB}")
ok("7b MỌI lượt generate đều được truyền `audio_prompt_path` "
   "(không lượt nào để thư viện tự nhớ)",
   bool(_g) and all(x["truyen"] for x in _g),
   f"{sum(1 for x in _g if x['truyen'])}/{len(_g)} lượt có mẫu")
ok("7c kênh A đọc bằng mẫu A",
   bool(_gA) and all(x["thuc_dung"].endswith("mau_a.wav") for x in _gA))
ok("7d **KÊNH B ĐỌC BẰNG MẪU B, KHÔNG PHẢI MẪU A** — mệnh đề trung tâm",
   bool(_gB) and all(x["thuc_dung"].endswith("mau_b.wav") for x in _gB),
   str([Path(x["thuc_dung"]).name for x in _gB]))
ok("7e ngôn ngữ đi theo TỪNG mã, không dùng lại của kênh trước",
   bool(_gA) and bool(_gB)
   and all(x["lang"] == "en" for x in _gA)
   and all(x["lang"] == "ja" for x in _gB))
ok("7f LỚP CHẮN THỨ HAI: mỗi lượt đọc là một TIẾN TRÌNH MỚI "
   "(model không sống qua hai kênh)",
   len({x["pid"] for x in _g}) == 2, f"{len({x['pid'] for x in _g})} pid")

# --- 7g: mã thiếu mẫu -> runner phải NÉM, không đọc bằng mẫu cũ ------------
_SO.write_text(json.dumps({"goi": [], "dinh": str(_SB / "mau_a.wav")}),
               encoding="utf-8")
_ket_rong = gc._chay([{"i": 0, "text": "x", "raw": str(_SB / "z.cb.wav")}],
                     "", "en", sys.executable, 120, None)
_g2 = _so_doc()["goi"]
ok("7g `ref` RỖNG -> runner NÉM, KHÔNG đọc một câu nào bằng mẫu còn dính",
   _ket_rong.get("ok") is not True and len(_g2) == 0,
   f"ok={_ket_rong.get('ok')} · loi={str(_ket_rong.get('loi'))[:90]} · "
   f"{len(_g2)} lượt generate")
ok("7h nhánh ném vẫn đóng dấu `_sandbox` (thiếu nó là `Path('')` = "
   "thư mục đang làm việc, đã xoá sạch cây mã một lần)",
   bool(_ket_rong.get("_sandbox")))
# `_chay` CỐ Ý không tự dọn — nơi gọi dọn (xem docstring của nó). CA 7g gọi
# THẲNG `_chay` nên chính cổng này phải dọn, không thì mỗi lượt chạy bỏ lại
# một thư mục `_job_*` trong `_giong_chatter` (đo: 7 lượt = 7 thư mục). Luật
# "test không được để rác trên máy anh Hùng" áp cho cả cổng.
try:
    from app.core import xoa_an_toan as _xa
    _xa.don_thu_muc(_ket_rong.get("_sandbox"), trong=gc.thu_muc_chatter())
except Exception:  # noqa: BLE001
    pass
ok("7h2 cổng tự dọn hộp cát của lượt gọi thẳng `_chay` (không để rác "
   "`_job_*` trong `_giong_chatter`)",
   not Path(str(_ket_rong.get("_sandbox") or _SB)).exists())

# --- 7i/7j: TỰ KIỂM BỘ DÒ — gỡ chốt thì kênh B PHẢI ra GIỌNG KÊNH A -------
# Kịch bản dựng đúng như đời thật sẽ xảy ra: kênh A chạy bằng runner ĐÚNG (mẫu
# A dính lại vào model), rồi một bản vá sau "tối ưu" bằng cách bỏ tham số đi —
# kênh B từ đó đọc bằng mẫu CỦA KÊNH A. Không phép phá nào khác nói được đúng
# câu đó, nên đừng đổi sang phép phá "bỏ mẫu ở câu thứ 2 trở đi": lượt thử đầu
# làm vậy và nó KHÔNG tái hiện được lỗi (câu đầu mỗi kênh vẫn truyền mẫu nên
# `dinh` luôn đúng kênh) — cổng khi ấy tự khen mình nhờ một tín hiệu KHÁC.
_PHA = _MA_GOC.replace(
    "        wav = m.generate(it[\"text\"], language_id=lang,\n"
    "                         audio_prompt_path=ref)",
    "        wav = m.generate(it[\"text\"], language_id=lang)")
_pha_duoc = _PHA != _MA_GOC
_SO.write_text(json.dumps({"goi": [], "dinh": ""}), encoding="utf-8")
_chay_kenh(MA_EN, 2, "PA")                  # kênh A: runner ĐÚNG
gc._MA_DOC = _PHA                           # bản vá sau gỡ mất chốt
_chay_kenh(MA_JA, 2, "PB")                  # kênh B: runner ĐÃ HỎNG
gc._MA_DOC = _MA_GOC
_gp = _so_doc()["goi"]
_gpB = _gp[2:4]
_lay_nham = bool(_gpB) and all(
    x["thuc_dung"].endswith("mau_a.wav") for x in _gpB)
_bat = (not all(x["truyen"] for x in _gp)) or any(
    not x["thuc_dung"].endswith("mau_b.wav") for x in _gpB)
ok("7i TỰ KIỂM BỘ DÒ: phép phá phải TÌM ĐƯỢC CHỖ để phá "
   "(chuỗi không khớp = phép thử HỎNG, KHÔNG phải 'không phá được')",
   _pha_duoc)
ok("7j TỰ KIỂM: gỡ chốt -> **KÊNH B THẬT SỰ RA GIỌNG KÊNH A** "
   "(tái hiện đúng lỗi, không phải một tín hiệu khác)",
   _pha_duoc and _lay_nham,
   f"kênh B thực dùng {[Path(x['thuc_dung']).name for x in _gpB]}")
ok("7k TỰ KIỂM: bộ dò của CA 7b/7d BẮT ĐƯỢC ca đó "
   "(không bắt được thì cổng này chỉ là con dấu)",
   _pha_duoc and _bat,
   f"lượt có mẫu {sum(1 for x in _gp if x['truyen'])}/{len(_gp)}")

gc._python_chatter = _that_py
gc.co_gpu_nvidia = _that_gpu
os.environ.pop("PYTHONPATH", None)

print("\nCA 8 — KHÔNG ĐƯỢC ĐẺ CHỖ GỌI MỚI Ở `thay_giong.py` (mệnh đề cổng 63)")
_cay_tg = ast.parse((REPO / "app" / "core" / "thay_giong.py")
                    .read_text(encoding="utf-8"))
_goi_w = [n for n in ast.walk(_cay_tg)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
          and n.func.attr == "_synth_all_words"]
_goi_s = [n for n in ast.walk(_cay_tg)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
          and n.func.attr == "_synth_all"]
ok("8a vẫn ĐÚNG 3 chỗ gọi `_synth_all_words` — nối ở CỬA CHUNG nên không "
   "phải sửa chỗ gọi nào", len(_goi_w) == 3, f"{len(_goi_w)} chỗ")
ok("8b KHÔNG đẻ chỗ gọi `_synth_all` mới ở `thay_giong.py`",
   len(_goi_s) == 0, f"{len(_goi_s)} chỗ")
_cay_du = ast.parse((REPO / "app" / "core" / "dubbing.py")
                    .read_text(encoding="utf-8"))
_ten_ham = {n.name for n in ast.walk(_cay_du)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
ok("8c cửa rẽ nằm TRONG `dubbing.py` (không bắt nơi gọi tự kiểm)",
   {"_chatter_hay_khong", "_chay_chatter", "_lui_chatter"} <= _ten_ham)


def _goi_trong(ten: str, tim: str) -> int:
    for n in ast.walk(_cay_du):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return sum(1 for c in ast.walk(n)
                       if isinstance(c, ast.Call)
                       and isinstance(c.func, ast.Name) and c.func.id == tim)
    return -1


ok("8d CẢ HAI cửa chung đều có nhánh Chatterbox (sót một cửa là video "
   "lẫn hai giọng mà rc vẫn 0)",
   _goi_trong("_synth_all", "_chatter_hay_khong") == 1
   and _goi_trong("_synth_all_words", "_chatter_hay_khong") == 1,
   f"_synth_all={_goi_trong('_synth_all', '_chatter_hay_khong')} · "
   f"_words={_goi_trong('_synth_all_words', '_chatter_hay_khong')}")
ok("8e `_MA_DOC` truyền `audio_prompt_path` VÔ ĐIỀU KIỆN (không `**kw`, "
   "không `if`) — đọc bằng AST, không dò chuỗi",
   (lambda: any(
       isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "generate"
       and any(k.arg == "audio_prompt_path" for k in n.keywords)
       and not any(k.arg is None for k in n.keywords)
       for n in ast.walk(ast.parse(gc._MA_DOC))))(),
   "quét cây cú pháp của chính chuỗi runner")

# ===========================================================================
print("\n" + "=" * 78)
print(f"TỔNG KẾT CỔNG 82 — ĐẠT {DAT} · HỎNG {HONG}")
if _HONG:
    for t in _HONG:
        print(f"   - {t}")
print("=" * 78)
try:
    shutil.rmtree(_SB, ignore_errors=True)
except Exception:  # noqa: BLE001
    pass
raise SystemExit(1 if HONG else 0)
