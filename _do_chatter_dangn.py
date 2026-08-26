# -*- coding: utf-8 -*-
"""CHATTERBOX ĐA NGÔN NGỮ — giọng nhân bản của anh Hùng nói được tiếng Anh/
Trung/Nhật không, và nói có CHUẨN không.

═══════════════════════════════════════════════════════════════════════════
CÂU HỎI CỦA ANH HÙNG
═══════════════════════════════════════════════════════════════════════════
*"clone giọng đó không nói đa ngôn ngữ được à, nói không chuẩn được à"* —
và anh ấy trả lời rõ là **CẦN NHIỀU THỨ TIẾNG**, không chỉ tiếng Việt.

Đường nhân bản đang chạy là **VieNeu = model TIẾNG VIỆT** (`sea_g2p` từ chối
`lang="en"`). `nhan_ban_giong.py` ĐÃ CÓ đường `Chatterbox` (`cb:`, 23 thứ
tiếng) nhưng hộp «Giọng của tôi» chỉ mở cửa tiếng Việt. File này đo xem
đường đó có đáng nối không.

═══════════════════════════════════════════════════════════════════════════
MẪU LÀ **GIỌNG MÁY** — RANH GIỚI CỨNG, KHÔNG PHẢI CHO TIỆN
═══════════════════════════════════════════════════════════════════════════
Mẫu sinh bằng edge-tts `vi-VN-*`. Hai lý do, cả hai đều bắt buộc:

  1. **PHÁP LÝ.** App BÁN RA. Không nhân bản giọng người thật nào khác ngoài
     chính anh Hùng, và **không đụng giọng thương mại đang được bán**.
     `_mau_giong/adam_clone.wav` trong máy này lấy từ file
     `ElevenLabs_..._Adam - Dominant, Firm_...mp3` = **giọng thương mại của
     ElevenLabs**, đúng thứ `CANH_BAO_PHAP_LY` xếp vào mức **CẤM**. Tuyệt đối
     không dùng nó làm mẫu đo.
  2. **ĐO ĐƯỢC.** Biết CHẮC hai mẫu là hai "người" khác nhau, và mẫu sạch
     tuyệt đối nên mọi số ở đây là **TRẦN TRÊN** — mẫu điện thoại sẽ tệ hơn.

Mẫu là tiếng **VIỆT** còn đầu ra là Anh/Trung/Nhật — đó ĐÚNG cảnh của anh
Hùng (mẫu Việt, muốn đọc tiếng khác), không phải một phép đo dễ hơn.

═══════════════════════════════════════════════════════════════════════════
HAI MẪU CÁCH XA CAO ĐỘ — BÀI HỌC CỔNG 88, ĐỪNG RÚT XUỐNG MỘT
═══════════════════════════════════════════════════════════════════════════
`_do_giong_toi.py` đã đo: giọng DỰNG SẴN cách mẫu A đúng **0,79** nửa cung,
gần y hệt bản sao thật (**0,69**). Tức **một mẫu thôi thì bảng số không phân
biệt được nhân bản với không nhân bản**. Bằng chứng nằm ở **ĐỘ TRẢI** giữa
hai bản sao. Dùng lại ĐÚNG 2 giọng của `_do_giong_toi.MAU` để số so được.

═══════════════════════════════════════════════════════════════════════════
ARM ĐỐI CHỨNG CHẠY **CÙNG LƯỢT** — KHÔNG CÓ NÓ THÌ MỌI SỐ VÔ NGHĨA
═══════════════════════════════════════════════════════════════════════════
Mỗi ngôn ngữ có một arm **edge-tts BẢN NGỮ** (`en-US-Aria` · `zh-CN-Xiaoxiao`
· `ja-JP-Nanami`) chạy cùng lượt, cùng bộ câu, cùng bộ chấm. Đó là **TRẦN**.
WER 8% là tốt hay tệ chỉ trả lời được khi biết trần của chính bộ câu đó.

═══════════════════════════════════════════════════════════════════════════
DÙNG LẠI BỘ ĐO CŨ, KHÔNG VIẾT BỘ THỨ HAI
═══════════════════════════════════════════════════════════════════════════
`_do_chatter.wer` · `_do_chatter.chay_ecapa` · `_bo_cau_thu_doc.CORPUS` ·
`_do_nhan_nha_bang` (thước nhấn nhá). Hai bảng số dựng bằng hai bộ chấm khác
nhau thì không so được với nhau.

═══════════════════════════════════════════════════════════════════════════
RAM/VRAM PHẢI **POLL TRONG LÚC CHẠY**
═══════════════════════════════════════════════════════════════════════════
Bẫy cổng 71/73 đã sập 2 lần: lấy mẫu TRƯỚC và SAU tiến trình con thì tiến
trình thoát là trả sạch VRAM -> ra đúng mức nền, tức **không đo gì cả**.

═══════════════════════════════════════════════════════════════════════════
KẾT QUẢ ĐO — 25/08/2026, RTX 3060, 8 câu/arm, Groq THẬT
═══════════════════════════════════════════════════════════════════════════
    arm                đọc    WER %   TRẦN %    bịa %   giây/câu
    CLONE_A_nu_en      8/8      4,4      0,0     +4,1       3,46
    CLONE_A_nu_zh      8/8      1,5      1,5     -3,2       6,86
    CLONE_A_nu_ja      8/8      2,1      0,0     -1,8       4,06
    CLONE_B_nam_en     8/8      1,8      0,0     +0,0       2,81
    CLONE_B_nam_zh     8/8      1,5      1,5     -7,1       3,04
    CLONE_B_nam_ja     8/8      2,1      0,0     -3,0       3,25

**48/48 câu đọc được · WER 1,5-4,4% so với TRẦN 0,0-1,5%.** So cho đúng:
`vn:Adam` (VieNeu) đọc tiếng Anh đo được **7,7-12,8%** — Chatterbox tốt hơn
hẳn ở đúng cái anh Hùng cần.

**NHÂN BẢN CHẠY THẬT XUYÊN NGÔN NGỮ** (ECAPA, ngưỡng đã hiệu chuẩn: cùng
giọng ~0,78 · khác giọng <= 0,31):
    arm                cos vs MẪU của nó   cos vs mẫu KIA
    CLONE_A_nu_en                  0,660            0,075
    CLONE_A_nu_zh                  0,789            0,121
    CLONE_A_nu_ja                  0,807            0,148
    CLONE_B_nam_en                 0,586            0,144
    CLONE_B_nam_zh                 0,768            0,236
    CLONE_B_nam_ja                 0,751            0,185
    TB 0,727 vs 0,151 · **ĐỐI CHỨNG ÂM cos(MẪU_A, MẪU_B) = 0,274**
**TIẾNG ANH LÀ CHỖ YẾU NHẤT** (0,586-0,660) còn Trung/Nhật 0,75-0,81 — bản
sao trôi xa mẫu nhất khi đọc tiếng Anh, nhưng vẫn cách rất xa ngưỡng
"khác giọng" 0,31.
ĐỘ TRẢI F0 giữa hai bản sao: en **7,83** · zh **8,33** · ja **8,07** nửa
cung, bám đúng độ trải của MẪU (**7,76**) -> đây mới là bằng chứng nhân bản
chạy thật (bài học cổng 88: một mẫu thôi thì không phân biệt được).

**MÁY:** cuda · torch 2.6.0+cu124 · nạp model 8,13s · **1,14x thời gian
thật** · VRAM đỉnh **4.898 MiB** (nền 808, POLL trong lúc chạy) · RAM đỉnh
**5.143,5 MB**.

**MỐC TỪNG CHỮ:** `generate()` trả ĐÚNG một khối sóng âm, **KHÔNG có mốc
nào**. Nhờ `giong_hang` (MMS_FA) thì phủ: en **100,0%** (74/74) · ja
**92,7%** (153/165) · zh **88,9%** (112/126), **8/8 câu có mốc ở MỌI arm**.

**RỦI RO LỚN NHẤT — ĐỘ DÀI CHẠY LOẠN, KHÔNG PHẢI CHẤT LƯỢNG ĐỌC.**
Độ dài từng câu (giây), so với TRẦN cùng câu:
    CLONE_A_nu_zh    4,0 **12,1** 5,0 **7,9** 3,9 4,4 **8,1** **9,5**
    TRAN_zh          3,9   3,5   4,0   3,0  3,3 4,2   5,0   3,5
    CLONE_B_nam_zh   2,8   3,6   3,7   2,2  2,7 3,6   3,1   2,6
Arm `A_nu × zh` đọc **54,9s** cho bộ câu mà TRẦN chỉ **30,4s** = **1,81x**,
câu tệ nhất **12,1s vs 3,5s = 3,5x**. Nhưng WER của chính arm đó chỉ
**1,5%** và bịa chữ **-3,2%** -> **nó đọc ĐÚNG CHỮ, chỉ sai NHỊP**:
`silencedetect` trên câu 12,1s cho thấy 3 khoảng lặng 0,48 / 0,81 / 0,78 s
dồn ở ĐUÔI (sau khi câu đã hết ~9,5s), còn câu 9,5s có 2 khoảng lặng
**1,12 / 1,22 s ở GIỮA**. `B_nam × zh` thì bình thường -> lỗi đi theo CẶP
(mẫu × ngôn ngữ), không phải tính chất của cả bộ.
**HỆ QUẢ CHO ĐƯỜNG THAY GIỌNG:** `cat_le_loat` cắt được lề im hai đầu
(v2.27.0) nhưng **khoảng lặng GIỮA câu thì không**, và Chatterbox **KHÔNG
có tham số `rate`** nên bước 4c `doc_nhanh_vua_khung` — thứ đã kéo
`tempo_max` về 1,017-1,027 — **không chạy được**, y hệt ca ElevenLabs Adam
(cổng 67 "CHƯA ĐẠT"). Phần dôi sẽ dồn hết sang `atempo` và chạm trần 1,5.

**DUNG LƯỢNG (đo, không ước):** 111 gói python **2.659,7 MB** (riêng torch
cu124 **2.415,0 MB**) + trọng số HF **3.062,1 MB** = **5,59 GB phải tải lần
đầu**; trên đĩa **8,28 GB** (venv 5.420,5 MB / 55.100 file + trọng số
3.062,1 MB / 11 file). Nhãn `NHAN_TAI` ghi "khoảng 5,5 GB" -> **KHỚP**.

═══════════════════════════════════════════════════════════════════════════
BA LỖI CỦA CHÍNH PHÉP ĐO NÀY, LƯỢT ĐẦU SẬP CẢ BA — ĐỌC KẺO LẶP
═══════════════════════════════════════════════════════════════════════════
Lượt đầu in ra **một bảng đủ số trông rất bình thường** trong khi cả ba cột
quan trọng đều là số rác. Không cái nào ném lỗi.
  1. chạy bằng **python HỆ THỐNG** (`C:\\Python314`) thay vì `.venv` ->
     `cannot import name 'OpenAI'` ở MỌI câu -> chép ngược RỖNG -> WER latin
     ra đúng 100,0%, CJK ra 0,0%. -> nay `kiem_groq()` DỪNG cả lượt.
  2. `_do_chatter.wer` **xoá sạch chữ Hán/kana** nên `a` rỗng ->
     `return 0.0` -> mọi arm CJK **0,0% sai vĩnh viễn**. -> nay `wer_nn` +
     `tu_kiem_bo_cham()` in thẳng ra rằng bộ chấm cũ MÙ trên CJK.
  3. `torchaudio` ghi **`pcm_f32le`** mà module `wave` không đọc được ->
     độ dài/F0 trả 0.0 -> `giây/câu 0,00` và `F0 0,00` cho mọi arm nhân bản
     trong khi 48 file tiếng có thật. -> nay `chuan_pcm()` ép PCM16 cho CẢ
     HAI phía trước khi chấm.
Cộng một lỗi thứ tư ở cột ECAPA: `chay_ecapa` trả **`{"dev":…,"emb":{…}}`**
chứ không trả thẳng bảng embedding -> cột ECAPA trống trơn dù 8 file đã vào
tới nơi.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "_lib_giong"))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "_do_chatter_dangn"
FF = str(REPO / "bin" / "ffmpeg.exe")
PY_CB = REPO / "_giong_chatter" / "venv" / "Scripts" / "python.exe"
_NO_WIN = 0x08000000 if os.name == "nt" else 0

from _bo_cau_thu_doc import CORPUS                              # noqa: E402
from _do_chatter import MA_CB, chay_ecapa, cos, wer             # noqa: E402

#: HAI mẫu, cách xa cao độ (nữ Bắc / nam Bắc). ĐÚNG bộ của `_do_giong_toi.MAU`
#: nên cột F0 so thẳng được với bảng giọng nhân bản VieNeu.
MAU = [("A_nu", "vi-VN-HoaiMyNeural"), ("B_nam", "vi-VN-NamMinhNeural")]

#: Câu đọc để LÀM MẪU. Dài để ECAPA có đủ tiếng — mẫu ngắn là nguồn nhiễu lớn
#: nhất của phép đo giống-giọng.
CAU_MAU = ("Đây là đoạn ghi âm ngắn để làm mẫu giọng của tôi. Tôi đọc thêm "
           "vài câu nữa cho đủ dài, để máy có cái mà học theo.")

#: 3 ngôn ngữ anh Hùng cần + giọng BẢN NGỮ edge-tts làm TRẦN.
NN = [("en", "en-US-AriaNeural"),
      ("zh", "zh-CN-XiaoxiaoNeural"),
      ("ja", "ja-JP-NanamiNeural")]

#: Số câu mỗi arm. 8 câu x 6 arm nhân bản = 48 lượt sinh tiếng.
SO_CAU = int(os.environ.get("BQ_CB_CAU", "8"))


#: Chỉ lấy câu NÓI TỰ NHIÊN. Cố ý BỎ `ten_rieng`/`viet_tat`/`so_ngay`/`don_vi`
#: — bốn nhóm đó là câu ĐỐI KHÁNG dựng riêng để bẫy bộ đọc, trộn vào đây là
#: đo lẫn hai thứ. `ban_dia` giữ lại: nó là câu tự nhiên (có tên địa danh),
#: và arm TRẦN cũng đọc đúng bộ ấy nên phép so vẫn công bằng.
LOAI_DUNG = ("cau_thuong", "ban_dia")


def cau_cua(nn: str) -> list[str]:
    """`SO_CAU` câu NÓI TỰ NHIÊN của một ngôn ngữ.

    **Cùng một bộ câu cho MỌI arm cùng tiếng** — arm nhân bản và arm TRẦN phải
    đọc y hệt nhau, nếu không thì hai cột WER không so được với nhau.
    """
    ra = [c for loai in LOAI_DUNG
          for (l, c, _tk) in CORPUS[nn] if l == loai]
    return ra[:SO_CAU]


# --------------------------------------------------------------------- tiện
def chay_ff(args: list[str], han: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run([FF, "-y", "-v", "error"] + args,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", creationflags=_NO_WIN, timeout=han)


def wav16(src: Path, dst: Path) -> bool:
    """-> wav 16 kHz mono (ECAPA đòi 16 kHz)."""
    r = chay_ff(["-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(dst)])
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def wav24(src: Path, dst: Path) -> bool:
    """-> wav 24 kHz mono (tần số cả hai máy nhân bản dùng)."""
    r = chay_ff(["-i", str(src), "-vn", "-ac", "1", "-ar", "24000", str(dst)])
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def noi_wav(ds: list[Path], dst: Path) -> bool:
    """Nối nhiều wav -> 1 file 16 kHz (embedding ECAPA ổn định hơn)."""
    ds = [p for p in ds if p.exists() and p.stat().st_size > 1000]
    if not ds:
        return False
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in ds),
                   encoding="utf-8")
    r = chay_ff(["-f", "concat", "-safe", "0", "-i", str(lst),
                 "-ac", "1", "-ar", "16000", str(dst)])
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 4000


def chuan_pcm(src: Path, dst: Path) -> bool:
    """-> wav 24 kHz mono **PCM16**. MỌI arm phải đi qua đây trước khi chấm.

    ═══ LỖI THẬT CỦA LƯỢT ĐO ĐẦU, 25/08/2026 — ĐỌC KỸ ═══
    `torchaudio.save` ghi ra **`pcm_f32le`** (WAVE_FORMAT_IEEE_FLOAT), mà
    module `wave` của Python **không đọc được** (`Error unknown format: 3`).
    Hàm đo độ dài/F0 nuốt lỗi rồi trả **0.0**, nên bảng in ra `giây/câu 0.00`
    và `F0 0.00` cho MỌI arm nhân bản — trong khi 48 file tiếng có thật, đọc
    được, 2,9 giây/file. Arm TRẦN (do ffmpeg sinh, PCM16) thì có số thật.
    Tức bảng **trông như đã đo** mà một nửa số là số rác — đúng họ bẫy
    "phép đo hỏng phát chứng nhận" (`astats` cổng 53 · `startswith` cổng 44).
    Chuẩn hoá CẢ HAI phía về cùng một dạng thì không còn chỗ cho lỗi đó.
    """
    r = chay_ff(["-i", str(src), "-vn", "-ac", "1", "-ar", "24000",
                 "-c:a", "pcm_s16le", str(dst)])
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def do_dai(p: Path) -> float:
    """Độ dài (giây). Đọc bằng `wave` — chỉ đúng trên file ĐÃ qua `chuan_pcm`."""
    try:
        with wave.open(str(p), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:                                          # noqa: BLE001
        return 0.0


def f0_nua_cung(p: Path) -> list[float]:
    """Dãy F0 (nửa cung) — dùng lại thước của `_do_nhan_nha`."""
    try:
        from _do_nhan_nha import f0_nua_cung as _f
        return list(_f(str(p)))
    except Exception:                                          # noqa: BLE001
        return []


def nhan_nha(p: Path) -> float:
    xs = f0_nua_cung(p)
    return statistics.pstdev(xs) if len(xs) > 2 else 0.0


def f0_tv(p: Path) -> float:
    xs = f0_nua_cung(p)
    return statistics.median(xs) if xs else 0.0


def chep_nguoc(p: Path, lang: str) -> str:
    """Groq chép ngược CHÍNH file vừa đọc. Máy nghe là thước ĐỘC LẬP."""
    try:
        from app.core import transcribe as TR
        return str(TR.transcribe(str(p), language=lang).get("text") or "")
    except Exception as e:                                     # noqa: BLE001
        print(f"    chép ngược hỏng: {type(e).__name__}: {e}")
        return ""


def dem_tu(s: str, nn: str) -> int:
    """Đếm từ — CJK không có dấu cách nên phải qua `recap._word_tokens`."""
    try:
        from app.ai.recap import _word_tokens
        return len(_word_tokens(s or ""))
    except Exception:                                          # noqa: BLE001
        return len((s or "").split())


def _tok(s: str) -> list[str]:
    """Token để chấm — CJK tách TỪNG CHỮ, chữ latin tách theo dấu cách."""
    import re
    s = re.sub(r"[^\w\s]", " ", (s or "").lower(), flags=re.UNICODE)
    try:
        from app.ai.recap import _word_tokens
        return _word_tokens(s)
    except Exception:                                          # noqa: BLE001
        return s.split()


def wer_nn(goc: str, nghe: str) -> tuple[float, int]:
    """Tỉ lệ sai TOKEN (Levenshtein) — chạy được cho CẢ CJK.

    ═══ VÌ SAO KHÔNG DÙNG THẲNG `_do_chatter.wer` — LỖI THẬT LƯỢT ĐẦU ═══
    `_do_chatter.wer` chuẩn hoá bằng `re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\\s]", " ")`,
    tức nó **XOÁ SẠCH chữ Hán/kana**. Chuỗi gốc thành RỖNG -> nhánh
    `if not a: return 0.0` -> **mọi arm tiếng Trung/Nhật ra đúng 0,0% sai
    VĨNH VIỄN**, kể cả khi máy đọc ra chuỗi vô nghĩa. Đó là con dấu, không
    phải phép đo. Lượt đầu của tôi in ra `TRAN_zh 0.0% · TRAN_ja 0.0%` và
    trông rất đẹp.

    Nên: giữ NGUYÊN thuật toán Levenshtein, chỉ đổi bộ TÁCH TOKEN sang
    `recap._word_tokens` (CJK-aware, đã có sẵn trong repo, cổng 52 hiệu
    chuẩn). `tu_kiem_bo_cham()` chốt rằng trên chữ latin nó ra **Y HỆT**
    `_do_chatter.wer` — không có chốt đó thì đây là bộ chấm THỨ HAI và hai
    bảng số không so được với nhau.
    """
    a, b = _tok(goc), _tok(nghe)
    if not a:
        return 0.0, 0
    tr = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        moi = [i]
        for j in range(1, len(b) + 1):
            moi.append(min(tr[j] + 1, moi[-1] + 1,
                           tr[j - 1] + (a[i - 1] != b[j - 1])))
        tr = moi
    return tr[len(b)] / len(a), len(a)


def tu_kiem_bo_cham() -> bool:
    """TỰ KIỂM BỘ CHẤM trước khi đo. Không đạt -> DỪNG, đừng in bảng.

    Ba câu hỏi, và câu thứ ba là câu đã cứu lượt này:
      1. giống hệt -> 0%          (bộ chấm không kêu oan)
      2. khác hẳn  -> cao         (bộ chấm CÓ RĂNG)
      3. **CJK khác hẳn -> cao**  (`_do_chatter.wer` ra 0,0% ở đây)
      4. latin: `wer_nn` == `_do_chatter.wer`  (không đẻ bảng số thứ hai)
    """
    ok = True
    a = "The weather is beautiful today, let us go for a walk."
    b = "A completely different sentence about nothing at all here."
    r_same, _ = wer_nn(a, a)
    r_diff, _ = wer_nn(a, b)
    zh_a, zh_b = "今天天气很好，我们一起出去走走吧。", "他打开门走进了那间黑暗的房间。"
    r_zh_same, _ = wer_nn(zh_a, zh_a)
    r_zh_diff, _ = wer_nn(zh_a, zh_b)
    cu_diff, _ = wer(a, b)
    cu_zh_diff, _ = wer(zh_a, zh_b)
    print(f"    [tự kiểm] latin giống {100 * r_same:.1f}% · "
          f"khác {100 * r_diff:.1f}%")
    print(f"    [tự kiểm] CJK   giống {100 * r_zh_same:.1f}% · "
          f"khác {100 * r_zh_diff:.1f}%   "
          f"(bộ chấm CŨ trên CJK: {100 * cu_zh_diff:.1f}% <- 0,0 = MÙ)")
    if r_same > 0.001 or r_zh_same > 0.001:
        print("    TỰ KIỂM HỎNG: chuỗi giống hệt mà báo sai")
        ok = False
    if r_diff < 0.5 or r_zh_diff < 0.5:
        print("    TỰ KIỂM HỎNG: chuỗi khác hẳn mà báo giống -> bộ chấm KHÔNG RĂNG")
        ok = False
    if abs(r_diff - cu_diff) > 0.001:
        print(f"    TỰ KIỂM HỎNG: latin lệch bộ chấm cũ "
              f"({r_diff:.3f} vs {cu_diff:.3f}) -> hai bảng số không so được")
        ok = False
    return ok


def kiem_groq() -> bool:
    """Groq chép ngược có CHẠY không. Hỏng -> DỪNG, không in bảng số rác.

    Lượt đầu chạy bằng python HỆ THỐNG (`C:\\Python314`) chứ không phải
    `.venv` -> `cannot import name 'OpenAI' from 'openai'` ở MỌI câu -> mọi
    bản chép ngược RỖNG -> WER latin ra đúng 100,0% và CJK ra 0,0%, **bảng
    vẫn in ra đủ số**. Một phép đo không gọi được máy nghe phải NÓI LÀ HỎNG.
    """
    d = SAN / "_kiem"
    d.mkdir(parents=True, exist_ok=True)
    w = sinh_edge(["This is a microphone test."], "en-US-AriaNeural", d, "gq")[0]
    if not (w and w.exists()):
        print("    KIỂM GROQ: không sinh nổi file thử")
        return False
    t = chep_nguoc(w, "en")
    print(f"    [tự kiểm] Groq nghe được: {t.strip()[:60]!r}")
    return bool(t.strip())


# ------------------------------------------------------- edge-tts (mẫu+trần)
def sinh_edge(cau: list[str], voice: str, thu: Path, tien_to: str) -> list[Path]:
    """edge-tts đọc cả loạt -> danh sách wav 24 kHz."""
    import asyncio

    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    mp3 = [thu / f"{tien_to}_{i}.mp3" for i in range(len(cau))]
    can = [i for i, m in enumerate(mp3)
           if not (m.exists() and m.stat().st_size > 1000)]
    if can:
        ok = asyncio.run(dubbing._synth_all([cau[i] for i in can], voice,
                                            [str(mp3[i]) for i in can]))
        if not ok or not all(ok):
            print(f"    edge-tts hỏng {voice}: {ok}")
    ra: list[Path] = []
    for i, m in enumerate(mp3):
        w = thu / f"{tien_to}_{i}.wav"
        if m.exists() and m.stat().st_size > 1000 and wav24(m, w):
            ra.append(w)
        else:
            ra.append(Path(""))
    return ra


# ------------------------------------------------- Chatterbox + POLL RAM/VRAM
def _vram_mib() -> float:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"], capture_output=True, text=True,
            timeout=15, creationflags=_NO_WIN)
        return float((r.stdout or "0").strip().splitlines()[0])
    except Exception:                                          # noqa: BLE001
        return 0.0


def chay_cb_poll(items: list[dict], han: int = 7200) -> dict:
    """Chatterbox ở TIẾN TRÌNH RIÊNG, **POLL RAM/VRAM TRONG LÚC CHẠY**.

    Lấy mẫu 2 đầu là ra mức NỀN (tiến trình thoát là trả sạch) — bẫy cổng
    71/73 đã sập 2 lần. `_sandbox` có ở MỌI đường ra.
    """
    SAN.mkdir(parents=True, exist_ok=True)
    sb = SAN / f"_job_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sb.mkdir(parents=True, exist_ok=True)
    run = sb / "runner.py"
    run.write_text(MA_CB, encoding="utf-8")
    job = sb / "job.json"
    job.write_text(json.dumps({"items": items}, ensure_ascii=False),
                   encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    nen_vram = _vram_mib()
    dinh = {"vram": 0.0, "ram": 0.0}
    dung = threading.Event()

    p = subprocess.Popen([str(PY_CB), "-u", str(run), str(job)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace",
                         env=env, creationflags=_NO_WIN)

    def _poll() -> None:
        try:
            import psutil
            pr = psutil.Process(p.pid)
        except Exception:                                      # noqa: BLE001
            pr = None
        while not dung.is_set():
            dinh["vram"] = max(dinh["vram"], _vram_mib())
            if pr is not None:
                try:
                    r = pr.memory_info().rss
                    for c in pr.children(recursive=True):
                        try:
                            r += c.memory_info().rss
                        except Exception:                      # noqa: BLE001
                            pass
                    dinh["ram"] = max(dinh["ram"], r / 2 ** 20)
                except Exception:                              # noqa: BLE001
                    pass
            dung.wait(0.5)

    th = threading.Thread(target=_poll, daemon=True)
    th.start()
    try:
        out, err = p.communicate(timeout=han)
    except subprocess.TimeoutExpired:
        p.kill()
        dung.set()
        return {"ok": False, "loi": f"quá giờ {han}s", "_sandbox": str(sb)}
    finally:
        dung.set()
        th.join(timeout=5)

    ket = {"ok": False, "loi": f"rc={p.returncode} {(err or '')[-600:]}"}
    for d in (out or "").splitlines():
        if d.startswith("BQJSON\t"):
            try:
                ket = json.loads(d[7:])
            except ValueError:
                pass
    ket["_sandbox"] = str(sb)
    ket["vram_dinh_mib"] = round(dinh["vram"], 1)
    ket["vram_nen_mib"] = round(nen_vram, 1)
    ket["ram_dinh_mb"] = round(dinh["ram"], 1)
    return ket


# --------------------------------------------------------------------- chấm
def cham_arm(ten: str, nn: str, cau: list[str], wavs: list[Path]) -> dict:
    """WER · token sai · bịa chữ · nhấn nhá · F0 · giây/câu cho MỘT arm."""
    wers, tu_vao, tu_ra, giay, doc_duoc = [], 0, 0, [], 0
    for c, w in zip(cau, wavs):
        if not (w and w.exists() and w.stat().st_size > 1000):
            wers.append(1.0)
            tu_vao += dem_tu(c, nn)
            continue
        doc_duoc += 1
        giay.append(do_dai(w))
        nghe = chep_nguoc(w, nn)
        r, _ = wer_nn(c, nghe)
        wers.append(min(1.0, r))
        tu_vao += dem_tu(c, nn)
        tu_ra += dem_tu(nghe, nn)
    return {
        "arm": ten, "nn": nn,
        "doc_duoc": doc_duoc, "tong": len(cau),
        "wer": 100.0 * sum(wers) / max(1, len(wers)),
        "bia": (100.0 * (tu_ra - tu_vao) / max(1, tu_vao)) if tu_ra else 0.0,
        "giay_cau": (sum(giay) / len(giay)) if giay else 0.0,
    }


def main() -> int:                                             # noqa: C901
    t00 = time.time()
    SAN.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("CHATTERBOX ĐA NGÔN NGỮ — nhân bản giọng có nói được Anh/Trung/Nhật?")
    print("=" * 74)
    print(f"mẫu: GIỌNG MÁY edge-tts (sạch giấy phép) · {SO_CAU} câu/arm")
    print(f"sân đo: {SAN}")

    if not PY_CB.exists():
        print(f"\nKHÔNG CÓ python Chatterbox: {PY_CB}")
        return 2

    # ---- 0. TỰ KIỂM BỘ ĐO — trước khi đo, không phải sau -------------------
    # Lượt đầu 25/08 in ra bảng đủ số trong khi Groq chết ở MỌI câu và bộ chấm
    # mù CJK. Bảng số rác nguy hiểm hơn không có bảng.
    print("\n[0] TỰ KIỂM BỘ ĐO (bộ chấm + máy nghe)")
    if not tu_kiem_bo_cham():
        print("    -> DỪNG: bộ chấm không tin được.")
        return 2
    if not kiem_groq():
        print("    -> DỪNG: Groq chép ngược KHÔNG chạy. Chạy bằng "
              r".venv\Scripts\python.exe, đừng dùng python hệ thống.")
        return 2

    # ---- 1. Dựng 2 MẪU ----------------------------------------------------
    print("\n[1] Dựng 2 mẫu giả lập bằng edge-tts (vi-VN, cách xa cao độ)")
    d_mau = SAN / "mau"
    ref: dict[str, str] = {}
    for k, v in MAU:
        w = sinh_edge([CAU_MAU], v, d_mau, k)[0]
        if not (w and w.exists()):
            print(f"    MẪU HỎNG {k}")
            return 2
        r24 = d_mau / f"{k}_ref24.wav"
        wav24(w, r24)
        r16 = d_mau / f"{k}_ref16.wav"
        wav16(w, r16)
        ref[k] = str(r24)
        print(f"    {k:<8} {v:<24} {do_dai(r24):5.2f}s  F0 {f0_tv(r16):5.2f}")

    # ---- 2. Chatterbox: 2 mẫu x 3 tiếng, MỘT lượt nạp model ---------------
    print(f"\n[2] Chatterbox đọc {SO_CAU} câu x 2 mẫu x 3 tiếng "
          f"(1 lượt nạp model)")
    d_cb = SAN / "cb"
    d_cb.mkdir(parents=True, exist_ok=True)
    items, ban_do = [], {}
    i = 0
    for mk, _mv in MAU:
        for nn, _tv in NN:
            cau = cau_cua(nn)
            ten = f"CLONE_{mk}_{nn}"
            ban_do[ten] = {"nn": nn, "cau": cau, "mau": mk, "wav": []}
            for j, c in enumerate(cau):
                out = d_cb / f"{ten}_{j}.wav"
                items.append({"i": i, "text": c, "lang": nn,
                              "ref": ref[mk], "out": str(out), "seed": 1234})
                ban_do[ten]["wav"].append(out)
                i += 1
    print(f"    {len(items)} lượt sinh tiếng · đang chạy (poll RAM/VRAM)...")
    kq = chay_cb_poll(items)
    if not kq.get("ok"):
        print(f"    CHATTERBOX HỎNG: {kq.get('loi')}")
        return 2
    # CHUẨN HOÁ VỀ PCM16 — bắt buộc, xem `chuan_pcm`. torchaudio ghi
    # `pcm_f32le` mà module `wave` không đọc được, và lỗi đó ĐI ÂM THẦM
    # (mọi cột độ dài/F0 ra 0,00 trong khi tiếng có thật).
    n_pcm = 0
    for ten, d in ban_do.items():
        moi = []
        for w in d["wav"]:
            p = w.with_name(w.stem + "_pcm.wav")
            if chuan_pcm(w, p):
                moi.append(p)
                n_pcm += 1
            else:
                moi.append(Path(""))
        d["wav"] = moi
    print(f"    chuẩn hoá PCM16: {n_pcm}/{len(items)} file")
    if n_pcm < len(items):
        print("    CẢNH BÁO: có file không chuẩn hoá được -> cột độ dài/F0 "
              "của arm đó KHÔNG đọc được")

    tong_gen = sum(float(r.get("gen", 0)) for r in kq.get("ra", []))
    tong_giay = sum(float(r.get("giay", 0)) for r in kq.get("ra", []))
    print(f"    thiết bị {kq.get('dev')} · torch {kq.get('torch')} · "
          f"nạp {kq.get('nap')}s")
    print(f"    sinh {tong_gen:.1f}s máy cho {tong_giay:.1f}s tiếng = "
          f"{tong_gen / max(0.01, tong_giay):.2f}x thời gian thật")
    print(f"    VRAM đỉnh {kq.get('vram_dinh_mib')} MiB "
          f"(nền {kq.get('vram_nen_mib')}) · torch báo "
          f"{kq.get('vram')} GiB · RAM đỉnh {kq.get('ram_dinh_mb')} MB")

    # ---- 3. ARM ĐỐI CHỨNG, CÙNG LƯỢT --------------------------------------
    print("\n[3] Arm ĐỐI CHỨNG edge-tts BẢN NGỮ (TRẦN) — chạy cùng lượt")
    d_tr = SAN / "tran"
    for nn, v in NN:
        cau = cau_cua(nn)
        ws = sinh_edge(cau, v, d_tr, f"TRAN_{nn}")
        ban_do[f"TRAN_{nn}"] = {"nn": nn, "cau": cau, "mau": "", "wav": ws}
        print(f"    TRAN_{nn:<4} {v:<24} {sum(1 for w in ws if w and w.exists())}"
              f"/{len(cau)} file")

    # ---- 4. CHẤM ----------------------------------------------------------
    print("\n[4] Chấm: Groq chép ngược + WER + bịa chữ + nhấn nhá")
    rows = []
    for ten, d in ban_do.items():
        r = cham_arm(ten, d["nn"], d["cau"], d["wav"])
        ok = [w for w in d["wav"] if w and w.exists()]
        r["nhan_nha"] = (statistics.mean([nhan_nha(w) for w in ok[:4]])
                         if ok else 0.0)
        r["f0"] = statistics.median([f0_tv(w) for w in ok[:4]]) if ok else 0.0
        r["mau"] = d["mau"]
        rows.append(r)
        print(f"    {ten:<18} đọc {r['doc_duoc']}/{r['tong']} · "
              f"WER {r['wer']:5.1f}% · bịa {r['bia']:+6.1f}%")

    # ---- 5. ECAPA: bản sao có GIỐNG mẫu khi đổi tiếng không? ---------------
    print("\n[5] ECAPA — bản sao nói tiếng LẠ có còn giống MẪU không?")
    files = {}
    for k, _v in MAU:
        files[f"MAU_{k}"] = str(Path(ref[k]).with_name(f"{k}_ref16.wav"))
    for ten, d in ban_do.items():
        if not ten.startswith("CLONE_"):
            continue
        g = SAN / f"_ecapa_{ten}.wav"
        if noi_wav([w for w in d["wav"] if w and w.exists()], g):
            files[ten] = str(g)
        else:
            print(f"    nối file hỏng: {ten} -> arm này KHÔNG có cột ECAPA")
    print(f"    {len(files)} file vào ECAPA "
          f"({sum(1 for k in files if k.startswith('CLONE_'))} arm nhân bản)")
    # `chay_ecapa` trả **`{"dev":…, "emb":{…}}`** chứ KHÔNG trả thẳng bảng
    # embedding — lượt trước lấy nhầm cả bọc ngoài nên `ten not in emb` đúng
    # với MỌI arm và cột ECAPA trống trơn, trong khi 8 file đã vào tới nơi.
    emb = {}
    try:
        emb = {k: v for k, v in (chay_ecapa(files).get("emb") or {}).items()
               if v}
    except Exception as e:                                     # noqa: BLE001
        print(f"    ECAPA hỏng: {type(e).__name__}: {e}")
    print(f"    ECAPA ra {len(emb)}/{len(files)} embedding")

    ec = {}
    if emb:
        for ten in list(ban_do):
            if not ten.startswith("CLONE_") or ten not in emb:
                continue
            mk = ban_do[ten]["mau"]
            kia = [k for k, _ in MAU if k != mk][0]
            if f"MAU_{mk}" in emb and f"MAU_{kia}" in emb:
                ec[ten] = (cos(emb[ten], emb[f"MAU_{mk}"]),
                           cos(emb[ten], emb[f"MAU_{kia}"]))
        print(f"    {'arm':<18}{'cos vs MẪU của nó':>20}{'cos vs mẫu KIA':>18}")
        for ten, (a, b) in ec.items():
            print(f"    {ten:<18}{a:>20.3f}{b:>18.3f}")
    else:
        print("    KHÔNG RA SỐ — bảng trống KHÔNG phải kết luận 'không giống'.")

    # ---- 6. BẢNG ----------------------------------------------------------
    print("\n" + "=" * 74)
    print("BẢNG 1 — ĐỌC ĐƯỢC / WER / BỊA CHỮ  (so với TRẦN cùng lượt)")
    print("=" * 74)
    print(f"{'arm':<18}{'đọc':>7}{'WER %':>9}{'TRẦN %':>9}{'lần trần':>10}"
          f"{'bịa %':>9}{'giây/câu':>10}")
    tran = {r["nn"]: r["wer"] for r in rows if r["arm"].startswith("TRAN_")}
    for r in rows:
        t = tran.get(r["nn"], 0.0)
        lan = (r["wer"] / t) if t > 0.01 else 0.0
        print(f"{r['arm']:<18}{r['doc_duoc']:>3}/{r['tong']:<3}"
              f"{r['wer']:>9.1f}{t:>9.1f}"
              f"{(f'{lan:.2f}x' if lan else '  -'):>10}"
              f"{r['bia']:>+9.1f}{r['giay_cau']:>10.2f}")

    print("\n" + "=" * 74)
    print("BẢNG 2 — NHÂN BẢN CÓ CHẠY THẬT KHÔNG (F0 + nhấn nhá + ECAPA)")
    print("=" * 74)
    print(f"{'arm':<18}{'F0 nửa cung':>14}{'nhấn nhá':>11}"
          f"{'cos MẪU':>10}{'cos KIA':>10}")
    for k, _v in MAU:
        p16 = Path(ref[k]).with_name(f"{k}_ref16.wav")
        print(f"{'MAU_' + k:<18}{f0_tv(p16):>14.2f}{nhan_nha(p16):>11.2f}"
              f"{'-':>10}{'-':>10}")
    for r in rows:
        if not r["arm"].startswith("CLONE_"):
            continue
        a, b = ec.get(r["arm"], (0.0, 0.0))
        print(f"{r['arm']:<18}{r['f0']:>14.2f}{r['nhan_nha']:>11.2f}"
              f"{(f'{a:.3f}' if a else '-'):>10}"
              f"{(f'{b:.3f}' if b else '-'):>10}")

    # ĐỘ TRẢI — bằng chứng THẬT của nhân bản (bài học cổng 88)
    print("\nĐỘ TRẢI F0 giữa hai bản sao (bằng chứng nhân bản CHẠY THẬT):")
    for nn, _v in NN:
        a = [r["f0"] for r in rows if r["arm"] == f"CLONE_A_nu_{nn}"]
        b = [r["f0"] for r in rows if r["arm"] == f"CLONE_B_nam_{nn}"]
        if a and b:
            print(f"  {nn}: A_nu {a[0]:6.2f}  vs  B_nam {b[0]:6.2f}"
                  f"   -> TRẢI {abs(a[0] - b[0]):.2f} nửa cung")
    p16a = Path(ref["A_nu"]).with_name("A_nu_ref16.wav")
    p16b = Path(ref["B_nam"]).with_name("B_nam_ref16.wav")
    print(f"  (MẪU trải {abs(f0_tv(p16a) - f0_tv(p16b)):.2f} nửa cung)")

    kq_json = {"rows": rows, "ecapa": {k: list(v) for k, v in ec.items()},
               "cb": {k: kq.get(k) for k in
                      ("dev", "nap", "torch", "vram", "vram_dinh_mib",
                       "vram_nen_mib", "ram_dinh_mb")},
               "toc_do": round(tong_gen / max(0.01, tong_giay), 3),
               "so_cau": SO_CAU}
    (REPO / "_kq_chatter_dangn.json").write_text(
        json.dumps(kq_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nXONG · {time.time() - t00:.0f} giây · "
          f"kết quả -> _kq_chatter_dangn.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
