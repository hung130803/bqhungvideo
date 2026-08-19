# -*- coding: utf-8 -*-
"""KOKORO-82M — 54 giọng, Apache 2.0, chạy HẲN trên máy.

**TRẠNG THÁI: mới là MODULE, CHƯA NỐI VÀO `dubbing`/`giong_bang`.**
Đọc mục "CÒN PHẢI LÀM" ở cuối docstring trước khi tin nó chạy.

═══════════════════════════════════════════════════════════════════════════
GIẤY PHÉP — ĐÃ XÁC MINH TẠI KHO GỐC 19/08/2026, ĐỪNG TRA LẠI
═══════════════════════════════════════════════════════════════════════════
Kho `hexgrad/Kokoro-82M`, model card ghi **`apache-2.0`** → dùng thương mại
được, KHÁC hẳn `F5-TTS` (CC-BY-NC = cấm thương mại, đã LOẠI).
Dữ liệu huấn luyện **có KHAI RÕ**: public domain + audio giấy phép Apache/MIT
+ **audio tổng hợp từ TTS đóng của nhà cung cấp lớn**; kèm Koniwa (CC BY 3.0,
<1h) và SIWIS (CC BY 4.0, <11h) → phải ghi công ở `LICENSES.txt`.
Dòng "audio tổng hợp từ TTS đóng" ghi ra để không ai tưởng tôi giấu — tác giả
tự khai, giấy phép vẫn Apache 2.0, rất nhiều nơi dùng thương mại.

**KHÁC HẲN `Kokoro-Vietnamese` (đã LOẠI)** — bản đó GIẤU nguồn dữ liệu và có
3 tên trùng dàn giọng Vbee. Cùng chữ "Kokoro" nhưng hai thứ khác nhau; đừng
lấy nhầm.

`espeak-ng` là **GPL** → gọi như **CHƯƠNG TRÌNH RỜI** qua `subprocess`, đúng
khuôn `piper_tts.py`. **`import espeakng` MỘT DÒNG là mất quyền giữ kín mã.**
Máy này ĐÃ CÓ SẴN ở `_piper/piper/espeak-ng-data` — không phải tải.

═══════════════════════════════════════════════════════════════════════════
ĐIỂM CHẤT LƯỢNG DO CHÍNH TÁC GIẢ CHẤM (`VOICES.md`) — dùng làm nhãn, ĐỪNG BỊA
═══════════════════════════════════════════════════════════════════════════
    af_bella                      A-   <- CAO NHẤT CẢ BỘ
    am_fenrir · am_michael · am_puck   C+
    bm_fable · bm_george               C
    am_echo · am_eric · am_liam · am_onyx · bm_daniel   D
    bm_lewis                           D+
    am_santa                           D-
    **am_adam                          F+  <- THẤP NHẤT nam Mỹ**

**ANH HÙNG MUỐN KOKORO VÌ TƯỞNG NÓ CÓ ADAM HAY.** Nhãn PHẢI nói thẳng F+,
nếu không anh ấy lại thất vọng đúng như lần `vn:Adam` của VieNeu (*"nghe lạ
lạ, khác lắm"*). Cả bộ **không có giọng nam nào khá** — cao nhất chỉ C+.
Thứ đáng dùng ở đây là **`af_bella` (A-)**, không phải Adam.

Mốc so đã đo trong repo: `en-GB-Ryan` nhấn nhá **5,38** · edge-tts khớp chữ
**15,7 ms** · sai chữ **6,2%**. Kokoro **KHÔNG trả mốc từng chữ** → chữ chạy
theo tiếng phải nhờ `giong_hang` (phủ 98,6%) hoặc Groq chép ngược (tốn lượt,
phủ 38-99% tuỳ lượt). **Nhãn phải nói ra điều đó** — đây là chỗ Kokoro KÉM
HƠN cái anh Hùng đang có, ở đúng thứ anh ấy kêu nhiều nhất.

═══════════════════════════════════════════════════════════════════════════
CÒN PHẢI LÀM — 4 VIỆC, THIẾU BẤT KỲ CÁI NÀO LÀ "CHỌN X RA Y" IM LẶNG
═══════════════════════════════════════════════════════════════════════════
1. **`giong_bang`**: thêm hằng `KOKORO`, `("kk:", KOKORO)` vào `_TIEN_TO`,
   tên vào `TEN_NGUON`, xếp vào nhóm "Trên máy".
2. **`dubbing._synth_all` VÀ `_synth_all_words`** — cửa CHUNG, cạnh cửa
   Piper/VieNeu/Chatterbox. **KHÔNG sửa từng chỗ gọi**: cổng 63 phải vẫn đếm
   đúng 3 chỗ gọi của `thay_giong.py`; sót một chỗ là video ra **HAI GIỌNG
   TRỘN** mà mã thoát vẫn 0.
3. **Cổng mới**: GỌI THẬT `_synth_all_words` với `kk:...` rồi xem nó rẽ vào
   đâu — **đừng quét chuỗi** (quét chuỗi thì `x=False` vẫn khớp `x=`). Kèm
   tự-kiểm: gỡ chốt PHẢI đỏ. Nối `_chay_hoi_quy.py`.
4. **Đo 54 giọng**: mỗi giọng đọc thật ra WAV CÓ TIẾNG (độ dài + RMS, không
   phải 0 byte). **Câm thì KHÔNG cho vào combo**, ghi tên + lý do. Đếm giọng
   THẬT bằng **ECAPA** (Kani quảng cáo 18, đo ra 2; MFCC/cao độ là thước HỎNG:
   tự-ồn 97,7 > khoảng cách thật 48,4).

Ba lần đã sập vì thiếu bước 1-2: `ov:nu_am` chọn X ra Y · `vn:` module xong mà
`dubbing` không biết nên chọn "Minh Đức" ra giọng khác · `cb:` đăng ký thiếu
nên rơi nhóm `edge`. **Cả ba đều `rc=0`, không một dòng báo.**

═══════════════════════════════════════════════════════════════════════════
BA BẪY MÔI TRƯỜNG — mỗi cái đã cắn thật một lần
═══════════════════════════════════════════════════════════════════════════
· **`import torch` SAU khi Qt nạp = ACCESS VIOLATION** (`WinError 1114`),
  `try/except` KHÔNG chặn được → buộc chạy TIẾN TRÌNH RIÊNG. Dò "đã cài chưa"
  bằng **file có tồn tại không**, đừng `find_spec` (nó NẠP gói cha).
· **KHÔNG cài vào `.venv`** — anh Hùng đang chạy sản xuất 300 kênh; một lượt
  `pip install` kéo torch có thể phá app đang chạy.
· **KHÔNG để môi trường ở `%TEMP%`** (một lượt dọn ổ C là mất sạch, mà triệu
  chứng chỉ là *"giọng biến khỏi combo"* — không ai lần ra) và **KHÔNG cạnh
  `.exe`** (lượt tự cập nhật `rmdir /S /Q _internal.old` xoá mất). Bản đóng
  gói → `DATA_DIR`.
· Hậu kiểm sau khi cài phải **so `spec.origin` với thư mục đích**, đừng hỏi
  "import được không": máy dev mượn `.venv` rồi báo "cài xong" trong khi bản
  `.exe` rỗng. Bộ gióng hàng vừa dính đúng lỗi này hôm nay
  (`libtorchaudio.pyd` không nạp được vì thiếu torch trong `_giong_hang`).

Anh Hùng **KHÔNG chạy được lệnh cài** → mọi thứ phải qua **NÚT trong app**.
Nhãn ghi ĐÚNG số GB thật (`pip install --dry-run --report`, đừng ước) — đã có
2 lỗi nhãn: `250 MB` lặp 20 dòng và `6,1 GB` lặp 5 dòng làm anh Hùng đọc
thành 30,5 GB.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

#: Mã giọng trong combo: ``kk:af_bella``. Cùng quy ước ``vn:`` / ``cb:``.
TIEN_TO = "kk:"

#: 54 giọng + ĐIỂM DO TÁC GIẢ CHẤM. Điểm là chuỗi để in thẳng ra nhãn — đừng
#: quy sang số rồi so với `nhan_nha` (hai thang khác nhau, so là số lừa).
GIONG_KK: tuple[tuple[str, str, str], ...] = (
    # (mã, "giới tính · tiếng · mô tả", điểm tác giả chấm)
    ("af_bella",    "Nữ · Mỹ · giọng tốt nhất cả bộ",     "A-"),
    ("af_heart",    "Nữ · Mỹ · ấm",                       "A"),
    ("af_nicole",   "Nữ · Mỹ · thì thầm",                 "B-"),
    ("af_aoede",    "Nữ · Mỹ",                            "C+"),
    ("af_kore",     "Nữ · Mỹ",                            "C+"),
    ("af_sarah",    "Nữ · Mỹ",                            "C+"),
    ("af_alloy",    "Nữ · Mỹ",                            "C"),
    ("af_jessica",  "Nữ · Mỹ",                            "D"),
    ("af_nova",     "Nữ · Mỹ",                            "C"),
    ("af_river",    "Nữ · Mỹ",                            "D"),
    ("af_sky",      "Nữ · Mỹ",                            "C-"),
    ("am_fenrir",   "Nam · Mỹ",                           "C+"),
    ("am_michael",  "Nam · Mỹ",                           "C+"),
    ("am_puck",     "Nam · Mỹ",                           "C+"),
    ("am_echo",     "Nam · Mỹ",                           "D"),
    ("am_eric",     "Nam · Mỹ",                           "D"),
    ("am_liam",     "Nam · Mỹ",                           "D"),
    ("am_onyx",     "Nam · Mỹ",                           "D"),
    ("am_santa",    "Nam · Mỹ",                           "D-"),
    ("am_adam",     "Nam · Mỹ",                           "F+"),
    ("bf_emma",     "Nữ · Anh",                           "B-"),
    ("bf_isabella", "Nữ · Anh",                           "C"),
    ("bf_alice",    "Nữ · Anh",                           "D"),
    ("bf_lily",     "Nữ · Anh",                           "D"),
    ("bm_fable",    "Nam · Anh",                          "C"),
    ("bm_george",   "Nam · Anh",                          "C"),
    ("bm_daniel",   "Nam · Anh",                          "D"),
    ("bm_lewis",    "Nam · Anh",                          "D+"),
)

#: Giọng bị tác giả chấm dưới mức này thì nhãn phải KÊU. Không CHẶN — anh Hùng
#: đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*; chỉ nói thật.
DIEM_KEU = {"D", "D-", "D+", "F", "F+", "F-"}

#: Nhãn nút tải. **PHẢI KHỚP ĐƯỜNG SẼ ĐI** — đo bằng `--dry-run --report`
#: trước khi điền số, đừng ước (cổng 71 CA 4).
NHAN_TAI = "Tải giọng Kokoro (chưa đo dung lượng)"

CANH_BAO = (
    "Kokoro KHÔNG trả mốc từng chữ — chữ chạy theo tiếng phải nhờ bộ gióng "
    "chữ (phủ 98,6%) hoặc máy nghe (tốn lượt mạng). Kém hơn edge-tts "
    "(15,7 ms, tự trả mốc) ở đúng chỗ đó."
)


def la_giong_kokoro(voice: str) -> bool:
    """Giọng này có thuộc file này không. KHÔNG BAO GIỜ NÉM."""
    return str(voice or "").startswith(TIEN_TO)


def tach_ma(voice: str) -> str:
    """``kk:af_bella`` -> ``af_bella``. Trả "" nếu không phải giọng Kokoro."""
    v = str(voice or "")
    return v[len(TIEN_TO):] if v.startswith(TIEN_TO) else ""


def thu_muc() -> Path:
    """Môi trường Kokoro. **KHÔNG `%TEMP%`, KHÔNG cạnh `.exe`** — xem docstring.

    Bản đóng gói dùng ``DATA_DIR`` vì lượt tự cập nhật xoá cả ``_internal``
    (bài học `_lib` cổng 58 CA5). Đọc `config.DATA_DIR` MỖI LẦN GỌI, đừng cất
    hằng số (bài học `tg_so.duong_so`).
    """
    if getattr(sys, "frozen", False):
        from config import DATA_DIR
        return Path(DATA_DIR) / "_giong_kokoro"
    return Path(__file__).resolve().parents[2] / "_giong_kokoro"


def python_rieng() -> Path:
    """Python của môi trường riêng. Chưa cài thì đường dẫn không tồn tại."""
    return thu_muc() / "venv" / "Scripts" / "python.exe"


def espeak_data() -> Path | None:
    """`espeak-ng-data` mượn từ bộ Piper đã có. None = chưa có.

    Gọi espeak như CHƯƠNG TRÌNH RỜI (GPL) — xem docstring.
    """
    p = Path(__file__).resolve().parents[2] / "_piper" / "piper" / "espeak-ng-data"
    return p if p.is_dir() else None


def tinh_trang() -> dict:
    """{co, thieu, thu_muc, so_giong, espeak}. **KHÔNG BAO GIỜ NÉM.**

    Dò bằng **FILE CÓ TỒN TẠI KHÔNG**, không `find_spec` — `find_spec` phải
    NẠP gói cha, mà nạp torch trong tiến trình đã có Qt là ACCESS VIOLATION.
    """
    d = thu_muc()
    thieu: list[str] = []
    py = python_rieng()
    if not py.is_file():
        thieu.append("môi trường Python riêng")
    if not (d / "venv" / "Lib" / "site-packages" / "kokoro").is_dir():
        thieu.append("kokoro")
    if espeak_data() is None:
        thieu.append("espeak-ng-data (lấy từ bộ Piper)")
    return {
        "co": not thieu,
        "thieu": thieu,
        "thu_muc": str(d),
        "so_giong": len(GIONG_KK),
        "espeak": str(espeak_data() or ""),
    }


def co_kokoro() -> bool:
    """Có chạy được không. KHÔNG BAO GIỜ NÉM."""
    try:
        return bool(tinh_trang()["co"])
    except Exception:
        return False


def nhan_giong(ma: str) -> str:
    """Nhãn một dòng cho combo — **nói thật điểm tác giả chấm**.

    Giọng bị chấm dưới `DIEM_KEU` thì nhãn KÊU. Không chặn, không giấu: anh
    Hùng đã chốt *"cứ thêm hết, tôi tự trải nghiệm"*.
    """
    for m, mo_ta, diem in GIONG_KK:
        if m != ma:
            continue
        canh = " — TÁC GIẢ CHẤM THẤP, nên chọn giọng khác" if diem in DIEM_KEU else ""
        return f"{m} — {mo_ta} (Kokoro) · điểm {diem}{canh} · miễn phí"
    return ma


def danh_sach_giong() -> list[tuple[str, str]]:
    """[(mã, nhãn)] để đổ vào combo. Giọng điểm cao lên trên."""
    thang = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-",
             "D+", "D", "D-", "F+", "F", "F-"]
    def khoa(r: tuple[str, str, str]) -> tuple[int, str]:
        try:
            return (thang.index(r[2]), r[0])
        except ValueError:
            return (len(thang), r[0])
    return [(TIEN_TO + m, nhan_giong(m))
            for m, _mo_ta, _d in sorted(GIONG_KK, key=khoa)]


#: Kho trọng số trên Hugging Face. GHIM tường minh — thư viện tự mặc định về
#: đúng kho này nhưng in ra một dòng ``WARNING`` mỗi lượt, mà dòng đó lẫn vào
#: stdout của tiến trình con (nơi `_chay_kokoro` đang dò `BQP`/`BQJSON`).
KHO_HF = "hexgrad/Kokoro-82M"

#: Tần số mẫu Kokoro sinh ra. HẰNG SỐ CỦA MODEL (`KModel` 24 kHz) — đừng đọc
#: từ đâu khác rồi ghi vào WAV sai nhịp: sai `sr` là tiếng nhanh/chậm mà file
#: vẫn hợp lệ, `_kiem_wav` KHÔNG bắt được (nó chỉ hỏi có tiếng không).
SR = 24000

#: Câm thì phải KÊU: RMS dưới mức này coi như không có tiếng. `thay_giong.
#: _kiem_wav` đã chặn ca RMS == 0; ngưỡng này bắt thêm ca "có tiếng nhưng nhỏ
#: đến mức không nghe ra" (giọng hỏng thường ra nhiễu nền chứ không im hẳn).
RMS_TOI_THIEU = 0.002


def _ghi_log(dong: str) -> None:
    """Ghi lý do LÙI vào `logs/kokoro_<ngày>.log`. KHÔNG BAO GIỜ NÉM.

    **Lùi êm mà im lặng thì đúng bằng hỏng âm thầm** — cùng luật với
    `piper_tts._ghi_log` / `giong_vieneu._ghi_log` / `giong_ngoai._ghi_log`.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"kokoro_{ts:%Y%m%d}.log", "a", encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


def ma_tieng(ma: str) -> str:
    """Mã giọng -> `lang_code` của `KPipeline`. `af_/am_` -> `a`, `bf_/bm_` -> `b`.

    **KHÔNG ĐOÁN, ĐỌC TỪ CHÍNH MÃ GIỌNG.** `KPipeline` `assert lang_code in
    LANG_CODES` nên đưa sai là NÉM ngay; nhưng nguy hơn là đưa `a` cho giọng
    Anh-Anh: lúc đó thư viện in *"Language mismatch, loading b voice into a
    pipeline"* rồi **VẪN ĐỌC** bằng bộ phiên âm Mỹ — tiếng ra được, chỉ là sai
    trọng âm, và không một dòng nào tố giác.
    """
    return "b" if str(ma or "")[:1].lower() == "b" else "a"


# ---------------------------------------------------------------------------
# Tiến trình con — SCRIPT ĐỘC LẬP, KHÔNG `-m <module>`
# ---------------------------------------------------------------------------
#: **BẮT BUỘC CHẠY Ở TIẾN TRÌNH RIÊNG, KHÔNG PHẢI ĐỂ CHO GỌN.** `import torch`
#: trong tiến trình đã nạp Qt ném `OSError [WinError 1114] ... c10.dll` và
#: `try/except` KHÔNG chặn được (cổng 55 tái hiện 100%). App này LÀ app Qt.
#:
#: Không `-m app.core...`: bản `.exe` không có cây mã nguồn để `-m` bám vào
#: (bài học cổng 55). Việc và kết quả đi qua FILE JSON chứ không qua dòng lệnh.
#:
#: **espeak-ng LÀ GPL — nó chỉ được phép sống TRONG script này.** App không
#: `import` một dòng nào của nó; dữ liệu phiên âm truyền vào bằng BIẾN MÔI
#: TRƯỜNG (`BQ_ESPEAK_DATA`). Lưu ý đã đo: `misaki/espeak.py` gọi
#: `EspeakWrapper.set_data_path(espeakng_loader.get_data_path())` NGAY LÚC
#: IMPORT, và `_ESPEAK_DATA_PATH` của lớp ĐÈ LÊN mọi biến môi trường
#: (`wrapper.py:214` xét nó TRƯỚC `PHONEMIZER_ESPEAK_DATA_PATH`) -> muốn dùng
#: bộ dữ liệu dùng chung của Piper thì phải đặt LẠI SAU khi import, đúng như
#: dưới đây. Đặt env mà không đặt lại là bản vá không bao giờ chạy.
_MA_DOC = r'''
import json, os, sys, time

with open(sys.argv[1], "r", encoding="utf-8") as f:
    J = json.load(f)


def bao(p, m):
    sys.stdout.write("BQP\t%.4f\t%s\n" % (p, m))
    sys.stdout.flush()


try:
    bao(0.02, "Nap model Kokoro...")
    _dat = (J.get("espeak_data") or "").strip()
    if _dat and os.path.isdir(_dat):
        os.environ["PHONEMIZER_ESPEAK_DATA_PATH"] = _dat
        os.environ["ESPEAK_DATA_PATH"] = _dat

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    # SAU khi kokoro/misaki da import (misaki ghi cung data_path luc import).
    if _dat and os.path.isdir(_dat):
        try:
            from phonemizer.backend.espeak.wrapper import EspeakWrapper
            EspeakWrapper.set_data_path(_dat)
        except Exception:
            pass

    t0 = time.time()
    pipe = KPipeline(lang_code=J["lang_code"], repo_id=J["repo_id"])
    t_nap = time.time() - t0
    sr = int(J.get("sr", 24000))

    items = J["items"]
    ra = []
    t1 = time.time()
    for k, it in enumerate(items):
        manh = []
        moc = []
        loi = ""
        try:
            for r in pipe(it["text"], voice=J["voice"],
                          speed=float(J.get("speed", 1.0))):
                a = getattr(r, "audio", None)
                if a is None:
                    continue
                a = np.asarray(a, dtype="float32").reshape(-1)
                # Mot cau co the ra NHIEU manh -> moc cua manh sau phai
                # CONG DON offset, khong thi moi manh lai bat dau tu 0.
                off = sum(len(x) for x in manh) / float(sr)
                for t in (getattr(r, "tokens", None) or []):
                    a0 = getattr(t, "start_ts", None)
                    a1 = getattr(t, "end_ts", None)
                    w = str(getattr(t, "text", "") or "").strip()
                    if a0 is None or a1 is None or not w:
                        continue
                    moc.append([round(off + float(a0), 3),
                                round(off + float(a1), 3), w])
                manh.append(a)
        except Exception as e:
            loi = "%s: %s" % (type(e).__name__, e)
        if not manh:
            ra.append({"i": it["i"], "p": "", "giay": 0.0,
                       "loi": loi or "khong sinh duoc am nao"})
            continue
        a = np.concatenate(manh) if len(manh) > 1 else manh[0]
        sf.write(it["raw"], a, sr)
        ra.append({"i": it["i"], "p": it["raw"],
                   "giay": round(len(a) / float(sr), 4),
                   "manh": len(manh), "moc": moc})
        bao(0.10 + 0.85 * (k + 1) / max(1, len(items)),
            "Doc cau %d/%d" % (k + 1, len(items)))
    t_gen = time.time() - t1

    ket = {"ok": True, "nap": round(t_nap, 2), "gen": round(t_gen, 2),
           "sr": sr, "ra": ra}
except Exception as e:
    ket = {"ok": False, "loi": "%s: %s" % (type(e).__name__, e)}
sys.stdout.write("BQJSON\t" + json.dumps(ket) + "\n")
sys.stdout.flush()
'''

_NO_WIN = 0x08000000 if os.name == "nt" else 0


def _viet_runner(ma_lot: str) -> Path:
    """Ghi script chạy ra `<thu_muc>/_bq_kokoro_runner_<mã lượt>.py`.

    **MỘT FILE MỘT LƯỢT GỌI — đã hỏng thật ở `giong_hang`, đừng "dọn gọn".**
    Dùng chung một đường dẫn thì `write_text` mở chế độ `w` = **CẮT CỤT ngay**
    file mà tiến trình con của luồng kia đang đọc; còn ghi tên tạm rồi
    `os.replace` (nguyên tử trên POSIX) thì **Windows từ chối thay file ĐANG
    MỞ** (`PermissionError [WinError 5]`, đo được ngay lượt song song đầu). Làn
    thay giọng mặc định **2 luồng**, nên đây là ca chắc chắn gặp.
    """
    d = thu_muc()
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"_bq_kokoro_runner_{ma_lot}.py"
    p.write_text(_MA_DOC, encoding="utf-8")
    return p


def _ma_lot() -> str:
    """Mã DUY NHẤT cho MỘT lượt gọi. Dùng lại `giong_hang._ma_lot`.

    KHÔNG viết bộ sinh mã thứ hai: `giong_hang._ma_lot` đã mang đúng bài học
    (`p<pid>t<luồng>n<đếm>` — `pid` một mình là giống hệt nhau cho mọi luồng
    trong app). Module đó không kéo theo torch nên import ở đây an toàn.
    Hỏng thì tự lo bằng pid+luồng+đồng hồ, không được ném.
    """
    try:
        from app.core import giong_hang as _gh
        return _gh._ma_lot()
    except Exception:  # noqa: BLE001
        import threading
        return (f"p{os.getpid()}t{threading.get_ident()}"
                f"n{int(time.time() * 1000) % 1000000}")


def _don(d: Path | None) -> None:
    """Dọn hộp cát. KHÔNG BAO GIỜ NÉM, và KHÔNG BAO GIỜ ra ngoài `thu_muc()`.

    **`Path("")` KHÔNG RỖNG — nó là `WindowsPath('.')`**, tức THƯ MỤC ĐANG LÀM
    VIỆC: `str()` ra `'.'` (truthy), `is_dir()` ra True, rồi `rmtree('.')`
    **xoá sạch cây mã** với mã thoát 0. Đã xảy ra thật 19/08/2026
    (`giong_ngoai._don`). Đi qua cửa chung `xoa_an_toan` + còn tự kẹp trong
    `thu_muc()` (hai lớp, cố ý thừa — lớp trong là lớp chịu lực).
    """
    try:
        if d is None or not str(d).strip():
            return
        p = Path(d).resolve()
        goc = thu_muc().resolve()
        if p == goc or goc not in p.parents:
            _ghi_log(f"TỪ CHỐI dọn {p} — nằm ngoài {goc}")
            return
        try:
            from app.core import xoa_an_toan
            xoa_an_toan.don_thu_muc(p, trong=goc, ghi_log=_ghi_log)
            return
        except Exception:  # noqa: BLE001
            pass
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def _gan_job(p) -> None:
    """Đăng ký tiến trình con để bấm Huỷ GIẾT ĐƯỢC nó. KHÔNG BAO GIỜ NÉM."""
    try:
        from app.queue.worker import register_job_proc
        register_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


def _bo_gan_job(p) -> None:
    try:
        from app.queue.worker import unregister_job_proc
        unregister_job_proc(p)
    except Exception:  # noqa: BLE001
        pass


def _chay_kokoro(items: list[dict], ma: str, han_giay: int,
                 on_msg: Optional[Callable[[str], None]] = None,
                 speed: float = 1.0) -> dict:
    """Gọi tiến trình con đọc CẢ LOẠT một lượt. Trả dict (KHÔNG ném)."""
    ma_lot = _ma_lot()
    runner = _viet_runner(ma_lot)
    sb = thu_muc() / f"_job_{ma_lot}"
    (sb / "raw").mkdir(parents=True, exist_ok=True)
    # Đường ghi ra do ĐÂY đặt (nơi biết hộp cát), nơi gọi chỉ đưa chữ. Để nơi
    # gọi tự đặt là mở đường cho hai lượt ghi chung một tên file.
    items = [dict(it, raw=str(sb / "raw" / f"c{int(it['i']):04d}.wav"))
             for it in items]
    job = sb / "job.json"
    job.write_text(json.dumps(
        {"items": items, "voice": ma, "lang_code": ma_tieng(ma),
         "repo_id": KHO_HF, "sr": SR, "speed": float(speed),
         "espeak_data": str(espeak_data() or "")},
        ensure_ascii=False), encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Trọng số để CẠNH môi trường, KHÔNG trong `%TEMP%`: một lượt dọn ổ C là
    # "giọng tự nhiên biến khỏi combo" và không ai lần ra (bài học `_lib` cổng
    # 58 CA5, và môi trường OmniVoice 7,74 GB từng nằm ở đó).
    env.setdefault("HF_HOME", str(thu_muc() / "hf"))
    dat = espeak_data()
    if dat:
        # Truyền qua BIẾN MÔI TRƯỜNG — app KHÔNG import gì của espeak (GPL).
        env["BQ_ESPEAK_DATA"] = str(dat)
        env["PHONEMIZER_ESPEAK_DATA_PATH"] = str(dat)
        env["ESPEAK_DATA_PATH"] = str(dat)

    ket: dict = {}
    duoi: list[str] = []
    ma_thoat: Optional[int] = None
    p = None
    try:
        p = subprocess.Popen(
            [str(python_rieng()), "-u", str(runner), str(job)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, env=env,
            creationflags=_NO_WIN)
        _gan_job(p)
        han = time.time() + han_giay
        for dong in p.stdout or ():
            dong = dong.rstrip("\n")
            if dong.startswith("BQP\t"):
                phan = dong.split("\t", 2)
                if on_msg and len(phan) > 2:
                    try:
                        on_msg(phan[2])
                    except Exception:  # noqa: BLE001
                        pass
                continue
            if dong.startswith("BQJSON\t"):
                try:
                    ket = json.loads(dong.split("\t", 1)[1])
                except ValueError:
                    ket = {}
                continue
            if dong.strip():
                duoi.append(dong[-300:])
            if time.time() > han:
                p.kill()
                # `_sandbox` PHẢI có ở MỌI đường ra — thiếu nó thì nơi gọi
                # nhận `Path("")` = `rmtree('.')`. Đúng chỗ đã xoá cây mã.
                return {"ok": False, "loi": f"quá {han_giay}s (bỏ cuộc)",
                        "_sandbox": str(sb), "_runner": str(runner)}
        ma_thoat = p.wait(timeout=120)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "loi": f"{type(e).__name__}: {e}",
                "_sandbox": str(sb), "_runner": str(runner)}
    finally:
        if p is not None:
            _bo_gan_job(p)
    if not ket:
        ket = {"ok": False,
               "loi": (f"mã thoát {ma_thoat}: "
                       + (" | ".join(duoi[-4:]) or "không rõ"))}
    ket["_sandbox"] = str(sb)
    ket["_runner"] = str(runner)
    return ket


def _do_wav(p: Path) -> tuple[float, float]:
    """(độ dài giây, RMS) của WAV. `(0.0, 0.0)` nếu đọc không được.

    Đọc THẲNG mẫu bằng `wave` + `audioop` thay vì gọi ffmpeg: hàm này chạy cho
    TỪNG câu (hàng chục lượt/video) và chỉ cần trả lời "có tiếng không".
    """
    try:
        import audioop
        import wave
        with wave.open(str(p), "rb") as w:
            fr = w.getframerate() or 0
            n = w.getnframes()
            if not fr or not n:
                return 0.0, 0.0
            raw = w.readframes(n)
            rms = audioop.rms(raw, w.getsampwidth()) / 32768.0
            return n / float(fr), rms
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def _kiem_wav(p: Path) -> tuple[bool, str]:
    """(dùng được không, lý do nếu không). **ĐỪNG TIN TIẾN TRÌNH CON BÁO OK.**

    Ba lớp, mỗi lớp bắt một ca đã xảy ra thật trong repo: file KHÔNG CÓ · file
    RỖNG (mã thoát 0 mà 0 byte) · file CÓ mà **CÂM** (đúng bẫy *thành công
    giả*: `sf.write` ghi ra một mảng toàn 0 thì file hợp lệ hoàn hảo).
    """
    if not p.exists():
        return False, "không có file"
    try:
        cỡ = p.stat().st_size
    except OSError as e:
        return False, f"không đọc được ({e})"
    if cỡ < 1024:
        return False, f"file rỗng ({cỡ} byte)"
    d, rms = _do_wav(p)
    if d < 0.05:
        return False, f"chỉ {d:.3f} giây"
    if rms < RMS_TOI_THIEU:
        return False, f"CÂM (RMS {rms:.5f} < {RMS_TOI_THIEU})"
    return True, ""


def _speed_tu_rate(rate) -> float:
    """`"+25%"` -> 1,25. Không đọc được -> 1,0.

    Kokoro có núm `speed` THẬT trong `KPipeline.__call__` (nhân vào `pred_dur`
    của bộ dự đoán độ dài) nên đọc nhanh bằng núm model, KHÔNG phải `atempo`
    cắt-dán (đo được 5,4-8,1 dB méo phổ, cổng 53).

    `rate` là LIST (mỗi câu một tốc độ) thì lấy **1,0 cho cả loạt**: một lượt
    gọi chỉ nạp model một lần và núm `speed` áp cho cả lượt, nên ép từng câu
    phải làm ở tầng khác. Trả 1,0 là "không đụng gì" — an toàn, không bịa.
    """
    if isinstance(rate, (list, tuple)):
        return 1.0
    try:
        s = str(rate or "").strip().rstrip("%")
        return max(0.5, min(2.0, 1.0 + float(s) / 100.0))
    except (TypeError, ValueError):
        return 1.0


#: Đọc được dưới tỉ lệ này thì BỎ CẢ LOẠT. Xem "ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE" ở
#: `doc_loat`. `BQ_KK_TY_LE` chỉ để đo/gỡ rối, đừng hạ trong sản xuất.
TY_LE_TOI_THIEU = 1.0


def doc_loat(texts: list[str], paths: list[str], voice: str,
             on_done: Optional[Callable[[int], None]] = None,
             rate: str | list = "+0%",
             lang: str = "en",
             han_giay: int = 1800,
             on_msg: Optional[Callable[[str], None]] = None,
             **_kw) -> list[bool]:
    """Đọc cả loạt trong MỘT lượt gọi tiến trình con. Trả `ok[i]` từng câu.

    **KHÔNG BAO GIỜ NÉM.** Hỏng thì trả toàn `False` để nơi gọi
    (`dubbing._synth_all` / `_synth_all_words`) lùi êm về edge-tts, và **ghi
    lý do** vào `logs/kokoro_<ngày>.log` — lùi êm mà im lặng thì đúng bằng
    hỏng âm thầm.

    **MỐC TỪNG CHỮ KHÔNG ĐI QUA ĐÂY.** Hàm trả `list[bool]` chứ không
    `(ok, words)`: mốc lấy ở cửa chung `dubbing._moc_giong_hang` (gióng hàng
    cưỡng bức, cổng 73) — cùng đường Chatterbox đang đi. Xem `moc_thu` nếu cần
    đọc mốc do CHÍNH Kokoro dự đoán (đã đo, chưa dùng — xem docstring hàm đó).

    ═══ ĐƯỢC ĂN CẢ, NGÃ VỀ EDGE ═══
    Đọc được 18/20 câu rồi để 2 câu kia lùi edge-tts thì video ra **LẪN HAI
    GIỌNG** giữa chừng, mà `rc` vẫn 0 nên không ai biết — đúng mệnh đề cổng 63
    canh. Nên một câu hỏng là trả `False` cả loạt: cả video một giọng, xấu hơn
    nhưng ĐỀU.

    ═══ GOM CẢ LOẠT VÀO MỘT LƯỢT ═══
    Mỗi lượt gọi nạp lại model (~2,2 s đo ở `piper_tts`), nên gọi từng câu là
    trả cái giá đó nhân số câu. Ở đây còn đắt hơn vì tiến trình con phải nạp
    cả torch.
    """
    n = len(texts)
    ok = [False] * n

    def _xong_het() -> None:
        # Báo XONG cho MỌI câu kể cả câu rỗng/hỏng: nơi gọi ĐẾM số lần
        # `on_done` để chạy thanh tiến trình, thiếu một nhịp là thanh đứng mãi.
        for i in range(n):
            if on_done:
                try:
                    on_done(i)
                except Exception:  # noqa: BLE001
                    pass

    if n == 0 or len(paths) < n:
        if n:
            _ghi_log(f"số câu ({n}) khác số file ({len(paths)}) -> bỏ qua")
        _xong_het()
        return ok

    ma = tach_ma(voice)
    if not ma:
        _ghi_log(f"Mã giọng lạ {voice!r} -> LÙI về edge-tts")
        _xong_het()
        return ok

    tt = tinh_trang()
    if not tt["co"]:
        _ghi_log(f"Chưa dùng được Kokoro (thiếu: {tt['thieu']}) -> LÙI về "
                 f"edge-tts")
        _xong_het()
        return ok

    can = [i for i in range(n) if str(texts[i] or "").strip()]
    if not can:
        _xong_het()
        return ok

    ket: dict = {}
    try:
        items = [{"i": i,
                  "text": str(texts[i]).strip().replace("\n", " ")}
                 for i in can]
        ket = _doc(items, ma, paths, rate, han_giay, on_msg)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"Kokoro hỏng ({type(e).__name__}: {e}) -> LÙI về edge-tts")
        ket = {}

    for i in ket.get("ok_i") or ():
        if 0 <= i < n:
            ok[i] = True

    duoc = [i for i in can if ok[i]]
    try:
        nguong = float(os.environ.get("BQ_KK_TY_LE", TY_LE_TOI_THIEU))
    except ValueError:
        nguong = TY_LE_TOI_THIEU
    if len(duoc) < nguong * len(can):
        _ghi_log(f"Chỉ đọc được {len(duoc)}/{len(can)} câu bằng {voice} -> BỎ "
                 f"CẢ LOẠT, lùi edge-tts (không để video lẫn hai giọng)")
        ok = [False] * n

    _xong_het()
    return ok


def _doc(items: list[dict], ma: str, paths: list[str], rate,
         han_giay: int, on_msg: Optional[Callable[[str], None]]) -> dict:
    """Thân thật: chạy tiến trình con, KIỂM từng file, chép về `paths`.

    Có thể ném — `doc_loat` bắt. Trả `{"ok_i": [...], "moc": {...}}`.
    """
    ket = _chay_kokoro(items, ma, han_giay, on_msg, _speed_tu_rate(rate))
    sb = Path(ket.get("_sandbox") or "")
    runner = ket.get("_runner") or ""
    try:
        if not ket.get("ok"):
            _ghi_log(f"Kokoro đọc hỏng ({ma}): {ket.get('loi')}")
            return {"ok_i": [], "moc": {}}

        ok_i: list[int] = []
        moc: dict[int, list] = {}
        for r in ket.get("ra") or []:
            i = int(r.get("i", -1))
            raw = Path(r.get("p") or "")
            if not r.get("p"):
                _ghi_log(f"Kokoro không sinh được câu {i} ({ma}): "
                         f"{r.get('loi')}")
                continue
            # **KHÔNG TIN TIẾN TRÌNH CON BÁO OK** — đo lại file nó ghi ra.
            dung, vi_sao = _kiem_wav(raw)
            if not dung:
                _ghi_log(f"Kokoro ghi ra file không dùng được cho câu {i} "
                         f"({ma}): {vi_sao}")
                continue
            dich = Path(paths[i])
            try:
                dich.parent.mkdir(parents=True, exist_ok=True)
                if dich.exists():
                    dich.unlink()
                shutil.copyfile(raw, dich)
            except OSError as e:
                _ghi_log(f"Không chép được câu {i} về {dich}: {e}")
                continue
            # KIỂM LẠI BẢN ĐÍCH: chép trên Windows có thể ra file cụt khi hết
            # đĩa mà `copyfile` không ném (đúng bẫy "ffmpeg mã 0 file rỗng").
            dung2, vi_sao2 = _kiem_wav(dich)
            if not dung2:
                _ghi_log(f"Bản chép của câu {i} không dùng được: {vi_sao2}")
                continue
            ok_i.append(i)
            if r.get("moc"):
                moc[i] = r["moc"]

        _ghi_log(f"Kokoro đọc {len(ok_i)}/{len(items)} câu bằng {ma} · "
                 f"nạp {ket.get('nap')}s · sinh {ket.get('gen')}s")
        return {"ok_i": ok_i, "moc": moc}
    finally:
        _don(sb)
        try:
            if runner:
                Path(runner).unlink(missing_ok=True)
        except OSError:
            pass


def moc_thu(texts: list[str], paths: list[str], voice: str,
            han_giay: int = 1800) -> dict:
    """Đọc cả loạt VÀ trả kèm mốc do CHÍNH Kokoro dự đoán. **CHỈ ĐỂ ĐO.**

    ═══ VÌ SAO CÓ HÀM NÀY, VÀ VÌ SAO ĐƯỜNG SẢN XUẤT KHÔNG DÙNG NÓ ═══
    Mục "CÒN PHẢI LÀM" ở đầu file (và cả nhãn) chốt rằng *"Kokoro KHÔNG trả
    mốc từng chữ"*. **ĐỌC MÃ THÌ CÂU ĐÓ SAI**: `KPipeline.join_timestamps`
    điền `MToken.start_ts/end_ts` cho MỌI giọng tiếng Anh (`lang_code in
    'ab'`), tức toàn bộ 28 giọng của bảng này. Đây đúng họ *"đọc mã tới
    `lang="vi"` rồi kết luận là DỪNG QUÁ SỚM"* — nên hàm này tồn tại để phép
    đo có đường vào, thay vì tôi khẳng định suông theo cả hai chiều.

    **NHƯNG ĐÓ LÀ MỐC *SUY RA*, KHÔNG PHẢI MỐC ĐO** — cùng loại với Piper,
    KHÁC hẳn `WordBoundary` của edge-tts và `/with-timestamps` của ElevenLabs.
    Nó cộng dồn `pred_dur` (bộ dự đoán độ dài phát ra, chính nó cũng ước
    lượng), và ngay trong mã thư viện còn một dòng `# TODO: Is -3 an
    appropriate offset?` ở phép bù mốc đầu. Vì vậy đường sản xuất đi
    `giong_hang` (gióng hàng cưỡng bức trên CHÍNH file tiếng, cổng 73), còn
    con số của đường này phải **ĐO rồi mới được tin** — và phải đo bằng thước
    thứ ba, không bằng Groq chép ngược (cổng 67 đã chứng minh thước Groq phụ
    thuộc giọng).
    """
    n = len(texts)
    ra = {"ok": [False] * n, "moc": [[] for _ in range(n)]}
    ma = tach_ma(voice)
    if not ma or not tinh_trang()["co"]:
        return ra
    can = [i for i in range(n) if str(texts[i] or "").strip()]
    items = [{"i": i, "text": str(texts[i]).strip().replace("\n", " "),
              "raw": ""} for i in can]
    try:
        kq = _doc(items, ma, paths, "+0%", han_giay, None)
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"moc_thu hỏng: {type(e).__name__}: {e}")
        return ra
    for i in kq.get("ok_i") or ():
        if 0 <= i < n:
            ra["ok"][i] = True
    for i, m in (kq.get("moc") or {}).items():
        if 0 <= int(i) < n:
            ra["moc"][int(i)] = m
    return ra
