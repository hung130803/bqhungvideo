"""THƯỚC NHẤN NHÁ — độ lệch chuẩn cao độ F0 tính bằng NỬA CUNG.

**FILE NÀY LÀ BẢN DỰNG LẠI, KHÔNG PHẢI BẢN GỐC — ĐỌC KỸ TRƯỚC KHI TIN SỐ.**

``app/core/nhan_nha.py`` và ``_do_nhan_nha_bang.py`` đều trỏ về
``_do_nhan_nha.f0_nua_cung`` của "lượt 10", nhưng file đó **CHƯA BAO GIỜ ĐƯỢC
COMMIT** (``git log --all -- _do_nhan_nha.py`` ra rỗng; ``git ls-files`` chỉ có
``_do_nhan_nha_bang.py``). Tức bảng 82 giọng đang chạy trong app được sinh ra
bởi một đoạn mã **không còn trên đĩa** — muốn đo thêm một giọng nào nữa là phải
dựng lại thước.

**DỰNG LẠI TỪ ĐÂU, KHÔNG PHẢI ĐOÁN BỪA:** tham số lấy từ hai nguồn khớp nhau —

1. mô tả trong ``nhan_nha.__doc__``: *"độ lệch chuẩn cao độ F0 tính bằng NỬA
   CUNG (khung 40 ms, tự tương quan)"*;
2. ``_do_bien_the_giong.f0_trung_vi`` — hàm F0 **CÙNG TÁC GIẢ, CÙNG CÁCH**
   (tự tương quan, khung 40 ms, bước 20 ms, dải 70-400 Hz, ngưỡng im
   0,5×RMS, ngưỡng tương quan 0,30) và **vẫn còn trong repo**.
3. mốc quy đổi 100 Hz đọc ngược từ chính ``_do_nhan_nha_bang.py``:
   ``f0_giua_hz = 100.0 * 2 ** (median / 12)`` -> hàm phải trả **nửa cung so
   với 100 Hz**, không phải Hz và không phải nửa cung so với trung vị.

**BẢN DỰNG LẠI KHÔNG ĐƯỢC TIN CHO TỚI KHI TÁI LẬP ĐƯỢC BẢNG CŨ.** Trộn số của
hai thước vào một bảng là đúng cái ``nhan_nha`` đã cấm ("so CHÉO chỉ là tham
khảo"), mà ở đây còn tệ hơn: cùng một cột, không ai nhìn ra. Vì vậy
``_do_kiem_thuoc.py`` đo lại **8 giọng đã có trong bảng**, trải từ đáy
(``es-ES-Elvira`` 2,26) tới đỉnh (``ar-SA-Hamed`` 5,86), rồi so từng con số.
Số đo tái lập nằm trong dải nhiễu mà chính ``nhan_nha`` đã ghi (lệch tối đa
0,12 khi đo lại) thì thước mới được dùng để mở rộng bảng.

Đơn vị: nửa cung. ``f0_nua_cung`` trả **danh sách từng khung có tiếng**;
người gọi tự ``pstdev`` (nhấn nhá) và ``median`` (cao độ giữa) — đúng cách
``_do_nhan_nha_bang.do_mot`` đang dùng.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

#: Khung 40 ms / bước 20 ms — lấy từ mô tả thước trong `nhan_nha.__doc__`.
KHUNG_S = 0.040
BUOC_S = 0.020

#: Dải cao độ giọng người. Ngoài dải này là nhiễu/tiếng động, không phải giọng.
F0_MIN_HZ = 70.0
F0_MAX_HZ = 400.0

#: Khung có RMS dưới `NGUONG_IM` lần RMS cả file coi như IM -> không có cao độ.
NGUONG_IM = 0.5

#: Đỉnh tự tương quan phải đạt tỉ lệ này so với r[0] mới coi là có cao độ thật.
NGUONG_TQ = 0.30

#: Mốc quy đổi Hz -> nửa cung. **ĐỌC NGƯỢC TỪ `_do_nhan_nha_bang.py`**
#: (`f0_giua_hz = 100.0 * 2 ** (median/12)`), không phải chọn cho đẹp. Đổi số
#: này thì `pstdev` KHÔNG đổi (nó là hằng số cộng) nhưng `f0_giua_hz` sai hết.
MOC_HZ = 100.0


def doc_wav(wav: Path | str):
    """Đọc WAV mono 16-bit -> (mẫu float64 trong [-1,1], tần số lấy mẫu).

    Chỉ nhận đúng dạng `_do_nhan_nha_bang.ra_wav` sinh ra (mono 16 kHz PCM).
    Dạng khác thì NÉM chứ không đoán — thước đọc nhầm định dạng là ra một
    bảng số trông như thật (họ bẫy `astats` cổng 53).
    """
    import numpy as np

    with wave.open(str(wav), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"WAV phải 16-bit, file này {w.getsampwidth()*8}")
        if w.getnchannels() != 1:
            raise ValueError(f"WAV phải MONO, file này {w.getnchannels()} kênh")
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return x.astype(np.float64) / 32768.0, sr


def f0_nua_cung(wav: Path | str) -> list[float]:
    """Cao độ từng khung CÓ TIẾNG, đơn vị **nửa cung so với 100 Hz**.

    Tự tương quan trên khung 40 ms, bước 20 ms. Khung im hoặc tương quan yếu
    bị BỎ (không nội suy, không điền 0 — điền 0 là bơm thẳng phương sai giả
    vào `pstdev` rồi mọi giọng đều thành "rất truyền cảm").
    """
    import numpy as np

    x, sr = doc_wav(wav)
    if x.size < sr // 4:                      # dưới 0,25 s: không đủ để đo
        return []
    n = int(KHUNG_S * sr)
    hop = int(BUOC_S * sr)
    lo, hi = int(sr / F0_MAX_HZ), int(sr / F0_MIN_HZ)
    nguong = float(np.sqrt((x ** 2).mean())) * NGUONG_IM
    ra: list[float] = []
    for i in range(0, max(0, x.size - n), hop):
        k = x[i:i + n]
        if float(np.sqrt((k ** 2).mean())) < nguong:
            continue
        k = k - k.mean()
        r = np.correlate(k, k, mode="full")[n - 1:]
        if r[0] <= 0:
            continue
        seg = r[lo:hi]
        if seg.size == 0:
            continue
        j = int(np.argmax(seg)) + lo
        if r[j] / r[0] < NGUONG_TQ:
            continue
        f0 = sr / float(j)
        ra.append(12.0 * math.log2(f0 / MOC_HZ))
    return ra
