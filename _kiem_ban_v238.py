# -*- coding: utf-8 -*-
"""KIỂM ĐỘC LẬP TRƯỚC KHI DỰNG BẢN — đếm giọng ở ĐÚNG CỬA hộp Thay giọng dùng.

**VÌ SAO CÓ FILE NÀY.** 5 luồng trước chết giữa chừng không kịp báo cáo, nên
ghi chú commit nói "đã xong" KHÔNG phải bằng chứng. File này dựng lại SỐ từ
đầu, và nó cố ý **KHÔNG đọc `_kq*`** của luồng khác.

**CỬA PHẢI ĐÚNG.** Đếm bằng `dubbing.list_recap_voices()` là đếm hộp CÀI ĐẶT
REUP, không phải hộp Thay giọng. Cửa thật (chép từ
`thay_giong_dialog._dung_combo_giong`) là::

    GB.gom_nhom(giong_dung_duoc(list_recap_voices()), nn, loi_tat=True)

`gom_nhom(loi_tat=True)` LẶP LẠI giọng ở nhóm "Khuyên dùng" (lối tắt), nên cột
"lộ" phải đếm mã DUY NHẤT (`set`), đếm dòng là phồng số.

**"HỖ TRỢ" LÀ KHO CỦA NGUỒN, không phải cái đang hiện** — hỏi thẳng từng
module, không chép tay:

* edge-tts  -> `dubbing._fetch_all_voices()` (kho đầy đủ) và `giong_mo.moi_giong_mo()`
* Piper     -> `piper_tts.MA_GIONG` (chỉ 1 giọng được phép, cổng 64)
* OmniVoice -> `giong_ngoai.GIONG_OV`
* IndexTTS  -> `giong_ngoai.GIONG_IX`
* VieNeu    -> `giong_vieneu.GIONG_VN`
* Vbee      -> `giong_vbee.GIONG_VBEE`
* ElevenLabs-> `dubbing._eleven_voices()`
* Chatterbox-> `giong_chatter` là NHÂN BẢN (mã `cb:<lang>|<file>`), kho = số
  mẫu đã đăng ký, KHÔNG phải bảng giọng dựng sẵn.

CHẠY: `.venv\\Scripts\\python.exe -u _kiem_ban_v238.py`
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                            # noqa: BLE001
    pass

SAN = Path(os.environ.get("BQ_DATA_DIR") or (REPO / "_kq_kiem_v238"))
SAN.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(SAN))


def _muon_key() -> dict[str, int]:
    """Mượn key ElevenLabs/Groq của DATA_DIR THẬT qua BIẾN MÔI TRƯỜNG.

    **BẮT BUỘC, không phải tuỳ chọn.** `config.py` nạp `.env` từ `DATA_DIR`,
    mà lượt kiểm này trỏ `BQ_DATA_DIR` vào hộp cát (luật: không đụng dữ liệu
    thật) -> hộp cát 0 key -> `_eleven_available()` False -> **`el:` biến mất
    khỏi combo** và bảng sẽ đọc thành *"ElevenLabs lộ 0/9"* trong khi trên máy
    anh Hùng nó lộ đủ. Đúng bẫy cổng 22 (`transcribe` lùi về whisper máy vì
    sandbox rỗng key) chỉ khác chỗ nó nổ.

    **KHÔNG GHI RA FILE, KHÔNG IN GIÁ TRỊ** — chỉ trả về SỐ LƯỢNG để đọc.
    """
    ra = {"eleven": 0, "groq": 0}
    goc = Path(os.environ.get("LOCALAPPDATA") or "") / "BQHungVideo" / ".env"
    if not goc.is_file():
        return ra
    try:                                    # CHỈ ĐỌC, không mở, không ghi
        chu = goc.read_text(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        return ra
    # `.env` của repo này để giá trị TRẢI NHIỀU DÒNG (key nối bằng dấu phẩy),
    # nên không tách được bằng `splitlines()` rồi `split("=")` — phải cắt theo
    # TÊN KHOÁ tiếp theo.
    ten = ("GROQ_API_KEYS", "ELEVENLABS_API_KEYS")
    for k in ten:
        i = chu.find(k + "=")
        if i < 0:
            continue
        j = len(chu)
        for k2 in ("\nWHISPER", "\nLLM_", "\nGEMINI", "\nECO_", "\nGROQ_",
                   "\nELEVENLABS", "\nRECAP_"):
            n = chu.find(k2, i + len(k) + 1)
            if 0 <= n < j:
                j = n
        gt = chu[i + len(k) + 1:j].strip().strip('"').strip("'")
        gt = ",".join(x.strip() for x in gt.replace("\n", ",").split(",")
                      if x.strip())
        if gt:
            os.environ[k] = gt
            ra["eleven" if k.startswith("ELEVEN") else "groq"] = \
                len(gt.split(","))
    return ra


SO_KEY = _muon_key()

from app.core import dubbing as D                            # noqa: E402
from app.core import giong_bang as GB                        # noqa: E402
from app.core import giong_doc, giong_mo, nhan_nha           # noqa: E402
from app.ui.thay_giong_dialog import giong_dung_duoc         # noqa: E402

#: Ngôn ngữ đích để dựng combo. `gom_nhom` chỉ ĐỔI THỨ TỰ nhóm theo `nn`, tập
#: mã ra phải Y HỆT — nên chạy nhiều `nn` vừa lấy số vừa là phép TỰ KIỂM
#: bất biến "không mất giọng" của cổng 79.
NGON_NGU = ("vi", "en", "zh", "ja", "ko")

# Sàn của lượt kiểm ĐỌC THẬT (`giong_doc`): dưới mức này là giọng CÂM.
SAN_GIAY = 0.80
SAN_RMS = -55.0


def _co(mod: str, ten: str, mac=None):
    """Lấy thuộc tính module, thiếu -> `mac`. KHÔNG ném: một nguồn chưa cài
    trên máy này không được phép giết cả lượt đếm."""
    try:
        m = __import__(f"app.core.{mod}", fromlist=[ten])
        return getattr(m, ten, mac)
    except Exception:                                        # noqa: BLE001
        return mac


def kho_theo_nguon() -> dict[str, tuple[int, str]]:
    """{nguồn: (số giọng KHO, ghi chú)} — hỏi thẳng từng module."""
    ra: dict[str, tuple[int, str]] = {}

    # ---- edge-tts: kho đầy đủ do Microsoft công bố
    try:
        allv = D._fetch_all_voices() or []                   # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        allv = []
    ra[GB.EDGE] = (len(allv), "kho Microsoft (_fetch_all_voices)")

    # ---- Piper: cổng 64 chỉ cho phép ĐÚNG 1 giọng (giấy phép)
    ma_p = _co("piper_tts", "MA_GIONG", "")
    ra[GB.PIPER] = (1 if ma_p else 0, f"chỉ {ma_p} được phép (cổng 64)")

    # ---- OmniVoice / IndexTTS
    ov = _co("giong_ngoai", "GIONG_OV", ()) or ()
    ix = _co("giong_ngoai", "GIONG_IX", ()) or ()
    co_ov = _co("giong_ngoai", "co_omnivoice", lambda: False)()
    co_ix = _co("giong_ngoai", "co_indextts", lambda: False)()
    ra[GB.OMNIVOICE] = (len(ov), f"máy chạy được: {co_ov}")
    ra[GB.INDEXTTS] = (len(ix), f"máy chạy được: {co_ix}")

    # ---- VieNeu
    vn = _co("giong_vieneu", "GIONG_VN", ()) or ()
    co_vn = _co("giong_vieneu", "co_vieneu", lambda: False)()
    ra[GB.VIENEU] = (len(vn), f"đã tải model: {co_vn}")

    # ---- Vbee
    vb = _co("giong_vbee", "GIONG_VBEE", ()) or ()
    co_key = _co("giong_vbee", "co_key", lambda: False)()
    ra[GB.VBEE] = (len(vb), f"có key: {co_key}")

    # ---- ElevenLabs
    try:
        el = D._eleven_voices() or []                        # noqa: SLF001
    except Exception:                                        # noqa: BLE001
        el = []
    ra[GB.ELEVEN] = (len(el), f"có key: {D._eleven_available()}")  # noqa: SLF001

    # ---- Chatterbox: NHÂN BẢN, kho = số mẫu đã đăng ký
    try:
        from app.core import nhan_ban_giong as NB
        mau = NB.danh_sach() if hasattr(NB, "danh_sach") else []
    except Exception:                                        # noqa: BLE001
        mau = []
    co_cb = _co("giong_chatter", "co_chatter", lambda: False)()
    ra[GB.CHATTER] = (len(mau),
                      f"nhân bản giọng, máy chạy được: {co_cb}")
    return ra


def main() -> int:
    # ĐỌC version TỪ MÃ, đừng ghi cứng: bump xong mà tiêu đề còn số cũ thì
    # đọc log của hai lượt khác nhau lại tưởng là một lượt.
    from app.version import __version__ as ver
    print("=" * 78)
    print(f"KIỂM ĐỘC LẬP v{ver} — đếm ở ĐÚNG cửa hộp Thay giọng")
    print("=" * 78)
    print(f"key mượn từ DATA_DIR thật (chỉ đọc, KHÔNG in giá trị): "
          f"Groq={SO_KEY['groq']} · ElevenLabs={SO_KEY['eleven']}")

    tho = D.list_recap_voices()
    loc = giong_dung_duoc(tho)
    print(f"list_recap_voices  : {len(tho):5d} dòng")
    print(f"giong_dung_duoc    : {len(loc):5d} dòng "
          f"({sum(1 for _n, v in loc if v):d} có mã)")

    # ---- BẤT BIẾN cổng 79: tập mã KHÔNG đổi theo ngôn ngữ đích ----
    tap_vao = {v for _n, v in loc if v}
    tap_ra: dict[str, set] = {}
    dong: dict[str, int] = {}
    for nn in NGON_NGU:
        combo = GB.gom_nhom(loc, nn, loi_tat=True)
        tap_ra[nn] = {v for _n, v in combo if v}
        dong[nn] = len(combo)
    lech = {nn: (tap_vao ^ s) for nn, s in tap_ra.items()}
    xau = {nn: v for nn, v in lech.items() if v}
    print("\ngom_nhom (loi_tat=True) — số DÒNG combo theo ngôn ngữ đích:")
    print("   " + " · ".join(f"{nn}={dong[nn]}" for nn in NGON_NGU))
    print(f"mã DUY NHẤT: {len(tap_vao)} (giống nhau ở cả "
          f"{len(NGON_NGU)} ngôn ngữ: {'CÓ' if not xau else 'KHÔNG - ' + str(xau)})")

    # ---- BẢNG: hỗ trợ / lộ ----
    kho = kho_theo_nguon()
    lo: dict[str, set] = {}
    for v in tap_vao:
        lo.setdefault(GB.nguon(v), set()).add(v)

    print(f"\n{'nguồn':12s} {'hỗ trợ':>7s} {'lộ':>5s} {'%':>6s}  ghi chú")
    print("-" * 78)
    thu_tu = [GB.EDGE, GB.VIENEU, GB.PIPER, GB.OMNIVOICE, GB.INDEXTTS,
              GB.CHATTER, GB.ELEVEN, GB.VBEE, GB.GEMINI]
    for ng in thu_tu:
        n_kho, ghi = kho.get(ng, (0, ""))
        n_lo = len(lo.get(ng, ()))
        if ng == GB.GEMINI:
            ghi = "CHẶN CÓ CHỦ Ý: không trả word boundary (giong_dung_duoc)"
            n_kho = sum(1 for _n, v in tho if str(v).startswith("gemini:"))
        pc = (100.0 * n_lo / n_kho) if n_kho else 0.0
        print(f"{GB.TEN_NGUON.get(ng, ng):12s} {n_kho:7d} {n_lo:5d} "
              f"{pc:5.1f}%  {ghi}")
    la = {k: len(v) for k, v in lo.items() if k not in thu_tu}
    print("-" * 78)
    print(f"TỔNG lộ: {len(tap_vao)}" + (f"  (nguồn lạ: {la})" if la else ""))

    # ---- GIỌNG CÂM PHẢI KHÔNG CÓ TRONG DANH SÁCH ----
    print("\n" + "=" * 78)
    print("GIỌNG KHÔNG RA TIẾNG CÓ LỌT VÀO COMBO KHÔNG")
    print("=" * 78)
    cam = {ma for ma, (g, r) in giong_doc.BANG.items()
           if g < SAN_GIAY or r < SAN_RMS}
    print(f"biên bản đọc thật (giong_doc.BANG): {len(giong_doc.BANG)} giọng · "
          f"CÂM theo sàn ({SAN_GIAY}s / {SAN_RMS} dBFS): {len(cam)}")
    lot = sorted(cam & tap_vao)
    print(f"giọng CÂM lọt vào combo: {len(lot)}" +
          (f" -> {lot[:10]}" if lot else "  (ĐÚNG: không có)"))

    edge_lo = lo.get(GB.EDGE, set())
    # mọi mã edge trong combo PHẢI có bằng chứng đọc (giong_mo.nen_mo).
    # **PHẢI BÓC ĐUÔI CAO ĐỘ TRƯỚC** (`vi-VN-HoaiMyNeural|+10Hz`): biến thể
    # pitch do `thay_giong.BIEN_THE_PITCH` sinh ra từ MỘT giọng gốc đã có biên
    # bản đọc, nó không phải mã riêng trong kho Microsoft. Bản đầu của phép
    # kiểm này quên bóc -> báo 8 giọng "không có bằng chứng" = **ĐỎ OAN**, và
    # nó cũng là lý do cột edge-tts ra 330/322 = 102,5%.
    from app.core import thay_giong as TG
    khong_bang = sorted(v for v in edge_lo
                        if not giong_mo.nen_mo(TG.tach_giong_pitch(v)[0]))
    bien_the = sorted(v for v in edge_lo if TG.tach_giong_pitch(v)[0] != v)
    print(f"biến thể CAO ĐỘ (không phải giọng mới trong kho): "
          f"{len(bien_the)} -> edge-tts gốc {len(edge_lo) - len(bien_the)}"
          f"/{kho.get(GB.EDGE, (0, ''))[0]}")
    print(f"mã edge-tts trong combo KHÔNG có bằng chứng đọc: "
          f"{len(khong_bang)}" +
          (f" -> {khong_bang[:10]}" if khong_bang else "  (ĐÚNG: không có)"))
    print(f"giong_mo.so_giong_mo() = {giong_mo.so_giong_mo()} · "
          f"tiếng đã mở = {len(giong_mo.tieng_da_mo())} · "
          f"nhan_nha.BANG = {len(nhan_nha.BANG)}")

    # ---- TỰ KIỂM BỘ DÒ: sàn phải BẮT được một giọng câm dựng sẵn ----
    thu = dict(giong_doc.BANG)
    thu["zz-ZZ-CamNeural"] = (0.0, -99.0)
    bat = [m for m, (g, r) in thu.items() if g < SAN_GIAY or r < SAN_RMS]
    print(f"TỰ KIỂM BỘ DÒ (chèn 1 giọng câm giả): bắt được = "
          f"{'CÓ' if 'zz-ZZ-CamNeural' in bat else 'KHÔNG - bộ dò HỎNG'}")

    cb_ok = kiem_chatter()
    key_ok = kiem_lo_key()

    hong = bool(xau) or bool(lot) or bool(khong_bang) or \
        ("zz-ZZ-CamNeural" not in bat) or not cb_ok or not key_ok
    print("\n" + ("CÓ MỤC HỎNG — đọc bảng trên" if hong else "TẤT CẢ ĐẠT"))
    return 1 if hong else 0


def kiem_lo_key() -> bool:
    """CÓ KEY THẬT NÀO RƠI VÀO PHẦN CHƯA ĐẨY KHÔNG.

    **`grep -c gsk_` LÀ CỔNG SAI, VÀ NÓ ĐANG ĐỎ OAN — đọc kỹ trước khi hoảng.**
    Luật phát hành ghi *"`git log origin/main..HEAD -p | grep -c gsk_` phải =
    0"*. Đo thật hôm nay: **22**. Nhưng cả 22 đều là chuỗi `gsk_` TRẦN (chính
    là MẪU DÒ mà `app/ai/llm.py` và cổng 77 `_test_khong_lo_key.py` dùng để
    BẮT key rơi ra) cộng vài key GIẢ (`gsk_test`, `gsk_abc`). Không một chuỗi
    nào dài tới mức là key thật.

    Tức cổng cũ trừng phạt đúng cái file sinh ra để chống rò key — anh em của
    bẫy *"quét tĩnh bằng chuỗi thì chính DÒNG GHI CHÚ giải thích bản vá bị kể
    là vi phạm"* (cổng 47/51/53/73). Cổng đỏ oan thì người ta thôi đọc nó.

    Cổng ĐÚNG hỏi theo **HÌNH DẠNG KEY THẬT**: key Groq là `gsk_` + 52 ký tự,
    ElevenLabs `sk_` + 48, Google `AIza` + 35. Ngưỡng đặt 40 cho rộng rãi.
    Hàm **KHÔNG BAO GIỜ in giá trị khớp**, chỉ in SỐ ĐẾM và TÊN FILE.
    """
    import subprocess
    print("\n" + "=" * 78)
    print("RÒ KEY: quét phần CHƯA ĐẨY theo HÌNH DẠNG key thật")
    print("=" * 78)
    try:
        r = subprocess.run(["git", "log", "origin/main..HEAD", "-p"],
                           cwd=str(REPO), capture_output=True, timeout=300)
    except Exception as e:                                   # noqa: BLE001
        print(f"KHÔNG CHẤM ĐƯỢC: {type(e).__name__}: {e}")
        return False
    d = (r.stdout or b"").decode("utf-8", "replace")
    import re as _re
    mau = {
        "Groq (gsk_+40)":       _re.compile(r"gsk_[A-Za-z0-9_]{40,}"),
        "ElevenLabs (sk_+40)":  _re.compile(r"\bsk_[A-Za-z0-9]{40,}"),
        "Google (AIza+35)":     _re.compile(r"AIza[A-Za-z0-9_\-]{35}"),
        "OpenAI (sk-+30)":      _re.compile(r"sk-[A-Za-z0-9_\-]{30,}"),
    }
    tong = 0
    for ten, rx in mau.items():
        n = len(rx.findall(d))
        tong += n
        print(f"   {ten:22s} {n}")
    tho = len(_re.findall(r"gsk_", d))
    print(f"   {'(gsk_ TRẦN - cổng cũ)':22s} {tho}  <- mẫu dò + key giả, "
          f"KHÔNG phải key thật")
    print(f"   dòng diff quét: {len(d.splitlines())}")
    print("KẾT: " + ("SẠCH — 0 key thật trong phần chưa đẩy" if tong == 0
                     else f"CÓ {tong} CHUỖI DẠNG KEY THẬT — DỪNG, ĐỪNG ĐẨY"))
    return tong == 0


def kiem_chatter() -> bool:
    """`cb:` CÓ RẼ ĐÚNG NHÁNH KHÔNG — ca mà `_do_re_nhanh.py` KHÔNG chấm được.

    Combo trên máy này có **0 mã `cb:`** vì Chatterbox là nguồn NHÂN BẢN: mã
    chỉ sinh ra sau khi người dùng đăng ký một file mẫu. `_do_re_nhanh.py` lấy
    mẫu TỪ COMBO nên nó in *"(không có trong combo)"* rồi đếm là HỎNG — đọc
    thẳng dòng đó sẽ tưởng đường `cb:` gãy, trong khi cái thiếu là DỮ LIỆU chứ
    không phải MÃ. Đây đúng ca "cổng đỏ vì KHO, không vì mã" (bài học cổng 47).

    Nên dựng mã bằng chính `giong_chatter.ma_nhan_ban()` rồi gọi THẬT
    `_synth_all_words`, đặt gián điệp ở `_chay_chatter` (nhánh tốn GPU) để
    **0 lượt GPU**. Phép kiểm này chấm ĐÚNG một mệnh đề: *"tiền tố `cb:` đã
    được đăng ký ở cửa chung, mã không rơi xuống edge-tts"* — đúng cái lỗi
    `cb: chưa đăng ký` đã bắt được một lần.
    """
    import asyncio
    import subprocess

    from config import settings
    print("\n" + "=" * 78)
    print("CHATTERBOX: tiền tố `cb:` có rẽ đúng nhánh không (0 lượt GPU)")
    print("=" * 78)
    so: list[str] = []

    async def gd(texts, voice, paths, rate=None, on_msg=None):
        so.append("chatter")
        ra = []
        for p in paths:
            try:
                subprocess.run(
                    [settings.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi",
                     "-i", "sine=frequency=220:duration=1.0", "-ar", "24000",
                     "-ac", "1", p], check=True, timeout=60,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                ra.append(True)
            except Exception:                                # noqa: BLE001
                ra.append(False)
        return ra

    D._chay_chatter = gd                                     # noqa: SLF001
    if D._chay_chatter is not gd:                            # noqa: SLF001
        print("DỪNG: gián điệp vá hụt -> sổ rỗng, không phân biệt được với hỏng")
        return False

    import edge_tts
    goc_cm = edge_tts.Communicate

    class GDCom(goc_cm):                                     # type: ignore
        def __init__(self, *a, **k):
            so.append("edge")
            super().__init__(*a, **k)

    edge_tts.Communicate = GDCom
    try:
        from app.core import giong_chatter as gc
        mau = str(SAN / "mau_gia.wav")
        subprocess.run(
            [settings.FFMPEG_PATH, "-y", "-v", "error", "-f", "lavfi", "-i",
             "sine=frequency=180:duration=6", "-ar", "24000", "-ac", "1", mau],
            check=True, timeout=60, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        ket = {}
        for ten, ma in (("đúng dạng", gc.ma_nhan_ban(mau, "en")),
                        ("thiếu ngôn ngữ", "cb:|" + mau),
                        ("tiếng lạ", gc.ma_nhan_ban(mau, "vi"))):
            so.clear()
            p = str(SAN / "cb_thu.wav")
            try:
                asyncio.run(D._synth_all_words(                # noqa: SLF001
                    ["Hello anh Hung, this is a test."], ma, [p], lang="en"))
            except Exception as e:                           # noqa: BLE001
                ket[ten] = f"NỔ {type(e).__name__}"
                continue
            ket[ten] = so[0] if so else "(không nhánh nào)"
        print(f"co_chatter() = {gc.co_chatter()}")
        for k, v in ket.items():
            print(f"   {k:16s} -> rẽ vào: {v}")
        # BẤT BIẾN: mã ĐÚNG DẠNG phải vào chatter; mã HỎNG phải lùi edge (KHÔNG
        # được nổ, KHÔNG được vào chatter với dữ liệu rác).
        ok = (ket.get("đúng dạng") == "chatter"
              and ket.get("thiếu ngôn ngữ") == "edge"
              and ket.get("tiếng lạ") == "edge")
        print("KẾT: " + ("ĐÚNG — tiền tố cb: đã đăng ký, mã hỏng lùi êm"
                         if ok else "HỎNG — xem bảng trên"))
        return ok
    finally:
        edge_tts.Communicate = goc_cm


if __name__ == "__main__":
    raise SystemExit(main())
