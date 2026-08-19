# -*- coding: utf-8 -*-
"""CHỌN X CÓ RA X KHÔNG — gọi THẬT `dubbing._synth_all_words` rồi xem nó rẽ
vào nhánh nào (19/08/2026).

**VÌ SAO KHÔNG ĐỌC MÃ MÀ PHẢI GỌI.** Lỗi "chọn X ra Y" đã bắt được 3 lần chỉ
trong phiên này (`ov:nu_am` câu tả ngoài bảng từ đóng · `vn:` chưa nối vào cửa
chung · `cb:` chưa đăng ký tiền tố) và **cả 3 lần mã trông đều đúng**: nhánh
có mặt trong file, tên hàm có mặt trong cửa chung, nhưng lượt chạy thật lại
rơi xuống edge-tts, im lặng, mã thoát 0. Vì vậy đây là phép đo HÀNH VI: đặt
gián điệp lên TỪNG nhánh lá rồi đếm nhánh nào nổ.

**KHÔNG ĐỐT HẠN MỨC THẬT.** Nhánh tốn tiền / tốn GPU (ElevenLabs · Vbee ·
Chatterbox) bị thay bằng gián điệp SINH WAV BẰNG ffmpeg -> 0 ký tự
ElevenLabs, 0 đồng Vbee, 0 lượt GPU. Nhánh MIỄN PHÍ và chạy trên máy
(edge-tts · Piper · VieNeu · OmniVoice) chạy THẬT rồi ĐO LẠI file.

**GIÁN ĐIỆP PHẢI CÓ CA TỰ KIỂM.** Vá mà vá hụt (sai tên hàm, sai module) thì
sổ gián điệp rỗng và bảng sẽ đọc thành "không nhánh nào nổ" — không phân biệt
được với "app hỏng". Nên có mục `tu_kiem` bắt buộc từng bản vá phải ĂN.

CHẠY: `.venv\\Scripts\\python.exe -u _do_re_nhanh.py`
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

SAN = Path(os.environ.get("BQ_DATA_DIR") or (REPO / "_kq_re_nhanh"))
SAN.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(SAN))

from config import settings                                  # noqa: E402
from app.core import dubbing as D                            # noqa: E402
from app.core import giong_bang as GB                        # noqa: E402
from app.ui.thay_giong_dialog import giong_dung_duoc         # noqa: E402

CAU = "Xin chào anh Hùng, đây là phép đọc thật."
SO: list[str] = []          # sổ gián điệp: nhánh nào nổ


def _wav_gia(path: str, giay: float = 1.2) -> bool:
    """Sinh WAV CÓ TIẾNG bằng ffmpeg (thay cho nhánh tốn tiền/tốn GPU)."""
    try:
        subprocess.run(
            [settings.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi", "-i",
             f"sine=frequency=220:duration={giay}", "-ar", "24000", "-ac", "1",
             path], check=True, timeout=60,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def do_wav(p: str) -> dict:
    """Đo lại file: 0 byte / 0 giây / im lặng đều bị kể là HỎNG."""
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        return {"co": False, "byte": 0, "giay": 0.0, "dinh_db": None}
    byte = os.path.getsize(p)
    giay = 0.0
    try:
        with wave.open(p, "rb") as w:
            giay = w.getnframes() / float(w.getframerate() or 1)
    except Exception:                                        # noqa: BLE001
        pass
    dinh = None
    try:
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-v", "info", "-i", p, "-af",
             "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120, errors="replace")
        for d in (r.stderr or "").splitlines():
            if "max_volume:" in d:
                dinh = float(d.split("max_volume:")[1].split("dB")[0].strip())
    except Exception:                                        # noqa: BLE001
        pass
    if giay <= 0.0:
        try:
            r = subprocess.run(
                [settings.FFMPEG_PATH.replace("ffmpeg", "ffprobe"), "-v",
                 "error", "-show_entries", "format=duration", "-of",
                 "default=nw=1:nk=1", p],
                capture_output=True, text=True, timeout=60)
            giay = float((r.stdout or "0").strip() or 0)
        except Exception:                                    # noqa: BLE001
            pass
    return {"co": True, "byte": byte, "giay": giay, "dinh_db": dinh}


# ══════════════════ GIÁN ĐIỆP ══════════════════
def dat_gian_diep() -> dict:
    """Vá nhánh TỐN TIỀN / TỐN GPU. Trả sổ để mục tự kiểm đối chiếu."""
    da_va: dict[str, bool] = {}

    # THỨ TỰ THAM SỐ PHẢI CHÉP TỪ CHỮ KÝ THẬT, ĐỪNG ĐOÁN:
    # `_chay_eleven(texts, voice, paths, lang, on_done, on_msg, edge_rate,
    #               cho_lui_edge, words_out)` — bản đầu của gián điệp này viết
    # `(texts, paths, voice)` nên nó ghi WAV vào CHUỖI MÃ GIỌNG; nhánh vẫn nổ
    # đúng, chỉ có file là không có, và bảng đọc thành "ElevenLabs HỎNG".
    # `words_out` là danh sách ĐƯỢC ĐIỀN TẠI CHỖ (out-param), không phải trả về.
    async def gd_eleven(texts, voice, paths, lang=None, on_done=None,
                        on_msg=None, edge_rate="+0%", cho_lui_edge=True,
                        words_out=None):
        SO.append("el")
        ok = [_wav_gia(p) for p in paths]
        if words_out is not None:
            for t in texts:
                tu = (t or "").split()
                words_out.append([[0.0, 0.5, tu[0] if tu else "x"]])
        return ok

    async def gd_vbee(texts, paths, voice, *a, **k):
        SO.append("vbee")
        ok = [_wav_gia(p) for p in paths]
        return ok, [[] for _ in texts]

    async def gd_chatter(texts, ma, paths, *a, **k):
        SO.append("chatter")
        return [_wav_gia(p) for p in paths]

    D._chay_eleven = gd_eleven                              # noqa: SLF001
    D._chay_vbee = gd_vbee                                  # noqa: SLF001
    D._chay_chatter = gd_chatter                            # noqa: SLF001
    da_va["el"] = D._chay_eleven is gd_eleven               # noqa: SLF001
    da_va["vbee"] = D._chay_vbee is gd_vbee                 # noqa: SLF001
    da_va["chatter"] = D._chay_chatter is gd_chatter        # noqa: SLF001

    # ---- KEY GIẢ cho ElevenLabs: `elevenlabs_keys` là @classmethod đọc
    # `cls.ELEVENLABS_API_KEYS`, nên phải gán lên TYPE chứ không lên instance
    # (bẫy đã sập ở cổng 67). Key giả KHÔNG gọi mạng vì `_chay_eleven` đã bị
    # vá ở trên; nó chỉ để `_eleven_hay_khong` mở cửa.
    # `ELEVENLABS_API_KEYS` là CHUỖI (nối bằng `+`), không phải list — gán list
    # thì phép nối ném TypeError và bị `except` của `_eleven_keys` nuốt IM
    # LẶNG, sổ ra rỗng. Đúng lý do mục tự kiểm này tồn tại (nó đã bắt).
    try:
        type(settings).ELEVENLABS_API_KEYS = "sk_gia_khong_goi_mang"
        da_va["el_key"] = bool(D._eleven_available())        # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        da_va["el_key"] = False

    # ---- gián điệp ĐẾM cho nhánh chạy THẬT (không đổi hành vi) ----
    from app.core import giong_ngoai as GN
    from app.core import piper_tts as PT

    goc_gn, goc_pt = GN.doc_loat, PT.doc_loat

    def gd_gn(*a, **k):
        SO.append("ov")
        return goc_gn(*a, **k)

    def gd_pt(*a, **k):
        SO.append("piper")
        return goc_pt(*a, **k)

    GN.doc_loat, PT.doc_loat = gd_gn, gd_pt
    da_va["ov"] = GN.doc_loat is gd_gn
    da_va["piper"] = PT.doc_loat is gd_pt

    goc_vn = D._chay_vieneu                                  # noqa: SLF001

    async def gd_vn(*a, **k):
        SO.append("vieneu")
        return await goc_vn(*a, **k)

    D._chay_vieneu = gd_vn                                   # noqa: SLF001
    da_va["vieneu"] = D._chay_vieneu is gd_vn                # noqa: SLF001

    # ---- edge-tts: bắt nhánh LÙI. Vá `edge_tts.Communicate` để đếm.
    import edge_tts
    goc_cm = edge_tts.Communicate

    class GDCom(goc_cm):                                     # type: ignore
        def __init__(self, *a, **k):
            SO.append("edge")
            super().__init__(*a, **k)

    edge_tts.Communicate = GDCom
    da_va["edge"] = edge_tts.Communicate is GDCom
    return da_va


def mau_theo_nguon() -> dict[str, str]:
    """Lấy MẪU mã giọng của từng nguồn TỪ CHÍNH COMBO hộp Thay giọng dựng ra
    (không chép tay — chép tay là đo bảng trong đầu mình, không đo app)."""
    ds = giong_dung_duoc(D.list_recap_voices())
    theo: dict[str, str] = {}
    for _n, v in ds:
        if not v:
            continue
        ng = GB.nguon(v)
        theo.setdefault(ng, v)
    return theo


def main() -> int:
    print("=" * 78)
    print("CHỌN X CÓ RA X KHÔNG — gọi THẬT `_synth_all_words`, đếm nhánh nổ")
    print("=" * 78)
    da_va = dat_gian_diep()
    thieu = [k for k, v in da_va.items() if not v]
    print("tự kiểm bản vá gián điệp:",
          "ĐỦ" if not thieu else f"THIẾU {thieu}")
    if thieu:
        print("DỪNG: gián điệp vá hụt thì sổ rỗng và bảng đọc thành "
              "'không nhánh nào nổ' — không phân biệt được với app hỏng.")
        return 2

    mau = mau_theo_nguon()
    print(f"\nmẫu lấy từ combo thật: "
          + " · ".join(f"{GB.TEN_NGUON.get(k, k)}={v}" for k, v in mau.items()))

    thu_tu = ["edge", "vieneu", "ov", "piper", "chatter", "el", "vbee"]
    print(f"\n{'nguồn':11s} {'mã gửi vào':28s} {'rẽ vào':10s} {'ok':4s} "
          f"{'mốc':5s} {'giây':6s} {'đỉnh dB':8s} kết")
    print("-" * 78)
    ket: list[tuple[str, bool]] = []
    for ng in thu_tu:
        ma = mau.get(ng)
        if not ma:
            print(f"{GB.TEN_NGUON.get(ng, ng):11s} {'(không có trong combo)':28s}")
            ket.append((ng, False))
            continue
        SO.clear()
        p = str(SAN / f"re_{ng}.wav")
        if os.path.exists(p):
            os.remove(p)
        try:
            ok, words = asyncio.run(
                D._synth_all_words([CAU], ma, [p], lang="vi"))  # noqa: SLF001
        except Exception as e:                               # noqa: BLE001
            print(f"{GB.TEN_NGUON.get(ng, ng):11s} {ma[:28]:28s} "
                  f"NỔ {type(e).__name__}: {e}")
            ket.append((ng, False))
            continue
        d = do_wav(p)
        re_vao = SO[0] if SO else "(không nhánh nào)"
        dung = (re_vao == ng)
        # "CÓ TIẾNG THẬT" phải đo bằng SÀN IM LẶNG (đỉnh > -60 dBFS), KHÔNG
        # phải bằng trần chống méo. Bản đầu viết `dinh_db < -0.01` (= phép đo
        # CHẠM TRẦN) rồi đếm nó vào cột ĐÚNG/HỎNG -> Piper ra -0,0 dBFS và bị
        # kể là "chọn X ra Y" trong khi nó rẽ ĐÚNG nhánh. Hai câu hỏi khác
        # nhau thì phải hai cột khác nhau.
        tot = dung and any(ok) and d["co"] and d["giay"] > 0.05 \
            and (d["dinh_db"] is not None and d["dinh_db"] > -60.0)
        print(f"{GB.TEN_NGUON.get(ng, ng):11s} {ma[:28]:28s} {re_vao:10s} "
              f"{str(any(ok)):4s} {len(words[0]):<5d} {d['giay']:<6.2f} "
              f"{('' if d['dinh_db'] is None else '%.1f' % d['dinh_db']):8s} "
              f"{'ĐÚNG' if tot else ('LÙI ' + re_vao if not dung else 'HỎNG')}")
        ket.append((ng, tot))

    print("-" * 78)
    dung_n = sum(1 for _n, t in ket if t)
    print(f"CHỌN X RA X: {dung_n}/{len(ket)} nguồn")
    print("sổ đầy đủ mỗi lượt in ở cột 'rẽ vào' (nhánh NỔ ĐẦU TIÊN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
