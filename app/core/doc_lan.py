# -*- coding: utf-8 -*-
"""DÒ CÂU MÁY ĐỌC **LAN MAN** — một bộ dò, dùng chung cho mọi máy đọc.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ FILE NÀY (thay vì viết bộ dò thứ hai trong `giong_vieneu`)
═══════════════════════════════════════════════════════════════════════════
`giong_chatter.nghi_doc_lan` đã có từ 26/08 và làm đúng một việc: *"câu này
đọc DÀI BẤT THƯỜNG so với số chữ của nó"*. Giọng nhân bản VieNeu (`vnb:`) cần
đúng phép tính ấy, chỉ khác **mốc so sánh**. Chép sang là hai bản sao — tức
hai chỗ để lệch nhau, và lần sau ai sửa một chỗ thì chỗ kia im lặng đi lạc.

Nên phép TÍNH nằm ở đây (`lan_vuot`), còn **CHÍNH SÁCH** thì mỗi máy một kiểu:

  · `giong_chatter` — mốc là **HẰNG SỐ** (`a=0 · b=1/6,0` giây/ký tự) và chỉ
    soi câu **ngắn** (<= 24 ký tự). Đúng với bệnh của nó: đo được câu 5 ký tự
    ra 7,15 giây (**10,8 lần**) còn câu 55-180 ký tự thì 0,80-1,18x.
  · `giong_vieneu` — mốc **KHỚP TỪ CHÍNH LOẠT ĐANG ĐỌC** (`moc_nhip`), soi
    MỌI câu.

═══════════════════════════════════════════════════════════════════════════
MỐC PHẢI THEO LOẠT, KHÔNG PHẢI HẰNG SỐ — ĐO ĐƯỢC, KHÔNG PHẢI SỞ THÍCH
═══════════════════════════════════════════════════════════════════════════
`giong_chatter` đã đo: *"MẪU kéo nhịp đọc"* — cùng 12 câu tiếng Anh, mẫu
`en-US-Andrew` ra 1,03x còn mẫu `A_nu` ra 1,32x. Giọng nhân bản đọc theo BYTE
của mẫu, nên nhịp là thuộc tính của **lượt đọc này**. Ghim hằng số vào là mẫu
đọc chậm thì kêu oan cả loạt, mẫu đọc nhanh thì không bắt được gì.

Đo thật trên 5 loạt (`_do_vnb_lan.py`): mốc khớp ra
`1,561 + 0,0328n` · `2,028 + 0,0261n` (VieNeu hai lượt) · `0,899 + 0,0470n`
(Chatterbox) · `1,860 + 0,0405n` (edge-tts) — **hệ số góc lệch nhau tới 1,8
lần** giữa hai máy, và ngay hai LƯỢT của cùng một máy cũng lệch 1,26 lần.

═══════════════════════════════════════════════════════════════════════════
HÌNH DẠNG PHẢI LÀ `a + b*n`, KHÔNG PHẢI `n * (giây/ký tự)` — ĐÃ ĐO CẢ HAI
═══════════════════════════════════════════════════════════════════════════
Bản đầu của bộ dò này lấy **TRUNG VỊ giây/ký tự** rồi ước `n * gc`. Nó hỏng
đúng ở chỗ quan trọng nhất: **mục NGẮN có phí cố định** (lấy hơi, im đầu/cuối)
nên giây/ký tự của chúng cao gấp mấy lần mục dài — bộ dò kêu oan **22-24/58
mục của arm TRẦN edge-tts**, tức kêu trên giọng bản ngữ đọc ĐÚNG. Một bộ dò
kêu oan 40% thì không ai dùng được.

Đổi sang `a + b*n` (`a` = phí cố định, `b` = nhịp thật) trên **cùng bộ số**:

    bộ dò              | BẮT / bịa | KÊU OAN / lành | TRẦN edge kêu oan
    n * trung vị gc    |   23/25   |   15/91 (16%)  |  **22/58**
    **a + b*n**        |   18/25   |    2/91 (2,2%) |   **0/58**

Hệ số khớp bằng **Theil-Sen** (trung vị hệ số góc của MỌI cặp) chứ không phải
bình phương tối thiểu: chính mấy câu lan man là điểm ngoại lai, mà bình
phương tối thiểu thì bị điểm ngoại lai kéo đường khớp lên — **bộ dò tự vô
hiệu hoá mình**, đúng lý do `moc_nhip` cũng lấy TRUNG VỊ chứ không lấy trung
bình.

═══════════════════════════════════════════════════════════════════════════
BỘ DÒ NÀY **KHÔNG** ĐỌC BẢN CHÉP NGƯỢC — CỐ Ý
═══════════════════════════════════════════════════════════════════════════
Kiểu hỏng đo được của `vnb:` gồm ba dấu hiệu: đọc dài bất thường · ra **chữ
khác hệ chữ** («2026» -> `在英雄城的美索`) · **lặp** một cụm nhiều lần («OST»
ra một câu Trung lặp 3 lần). Hai dấu hiệu sau nhìn thấy rõ nhất trên BẢN CHÉP
NGƯỢC — mà chép ngược là một lượt ASR, tốn lượt Groq **cho từng câu, từng
video, 200-300 kênh**.

Vì vậy chúng chỉ được dùng làm **SỰ THẬT ĐỐI CHỨNG** lúc hiệu chuẩn
(`_do_vnb_lan.py`), còn thứ chạy lúc sản xuất là tín hiệu **MIỄN PHÍ**: độ dài
WAV thì máy đọc đã trả về sẵn trong cùng lượt gọi.
"""
from __future__ import annotations

import statistics as _st
from typing import Optional, Sequence

#: Sàn ước lượng (giây) — chặn chia cho số quá nhỏ khi mốc khớp ra `a` âm.
SAN_GIAY = 0.35

#: Ít hơn ngần này mục thì mốc khớp không có nghĩa -> `moc_nhip` trả
#: `(0.0, 0.0)` và nơi gọi phải hiểu là **không dò được**, chứ đừng lấy bừa
#: mục đầu làm mốc. Loạt 3 câu mà một câu bịa thì chính câu bịa kéo mốc lên.
TOI_THIEU_MUC = 6

#: Trần số mục đem đi khớp mốc. Theil-Sen là O(n²) cặp; 300 câu = 45.000 cặp
#: (vài mili-giây, chấp nhận được) nhưng 2.000 câu thì 2 triệu. Trung vị chịu
#: được lấy mẫu nên rải đều lấy ngần này mục là đủ.
TRAN_MAU_KHOP = 120


def lan_vuot(text: str, giay: float, a: float, b: float,
             san_giay: float = SAN_GIAY) -> float:
    """Câu này đọc dài gấp **bao nhiêu lần** mức đáng lẽ phải có. Hàm THUẦN.

    Mốc nhịp là `ước = a + b*n` (`a` = phí cố định mỗi câu, `b` = giây cho mỗi
    ký tự). Trả **bội số THÔ**, chưa áp ngưỡng — nơi gọi tự quyết định bao
    nhiêu là đáng kêu. Trả `0.0` khi không tính được (chữ rỗng · giây <= 0 ·
    mốc <= 0): **không tính được thì im**, đừng đoán bừa là hỏng.
    """
    try:
        n = len(str(text or "").strip())
        if n <= 0 or float(giay) <= 0:
            return 0.0
        uoc = float(a) + float(b) * n
        if uoc <= 0 and float(b) <= 0:
            return 0.0
        return round(float(giay) / max(san_giay, uoc), 2)
    except (TypeError, ValueError):
        return 0.0


def moc_nhip(texts: Sequence[str], giays: Sequence[float],
             ) -> tuple[float, float]:
    """Khớp `giây ≈ a + b*ký_tự` trên **chính loạt này**. `(0.0, 0.0)` = chịu.

    **Theil-Sen**, không phải bình phương tối thiểu — xem khối ghi chú đầu
    file: điểm ngoại lai chính là thứ ta đang đi tìm, để nó kéo đường khớp là
    bộ dò tự vô hiệu hoá mình.
    """
    try:
        pts: list[tuple[int, float]] = []
        for t, g in zip(texts, giays):
            n = len(str(t or "").strip())
            if n > 0 and float(g) > 0:
                pts.append((n, float(g)))
        if len(pts) < TOI_THIEU_MUC:
            return (0.0, 0.0)
        if len(pts) > TRAN_MAU_KHOP:
            buoc = len(pts) / float(TRAN_MAU_KHOP)
            pts = [pts[int(i * buoc)] for i in range(TRAN_MAU_KHOP)]
        doc: list[float] = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if pts[j][0] != pts[i][0]:
                    doc.append((pts[j][1] - pts[i][1])
                               / (pts[j][0] - pts[i][0]))
        if not doc:
            return (0.0, 0.0)
        b = float(_st.median(doc))
        a = float(_st.median([y - b * x for x, y in pts]))
        # Nhịp đọc ÂM là vô nghĩa (chữ càng dài đọc càng nhanh?) — dấu hiệu
        # loạt quá ít mẫu hoặc gần như cùng độ dài. Chịu, đừng dò bằng mốc rác.
        if b <= 0:
            return (0.0, 0.0)
        return (a, b)
    except (TypeError, ValueError, ZeroDivisionError):
        return (0.0, 0.0)


#: Vượt ngần này lần mốc của loạt thì coi là lan man.
#:
#: **HIỆU CHUẨN TRÊN CORPUS THẬT, KHÔNG ĐẶT MÒ** (`_do_vnb_lan.py`, arm
#: `VNB_en` = đúng đường anh Hùng đi: `vnb:` × 34 câu Anh + 24 token rời × 2
#: lượt; sự thật đối chứng lấy từ bản chép ngược Groq). Số thô ở
#: `_kq_vnb_lan.json`, bảng quét ngưỡng in ra lúc chạy:
#:
#:     ngưỡng | BẮT/bịa | KÊU OAN/lành | **TRẦN edge kêu oan**
#:       1,3  |  18/25  |  9/91 (9,9%) |   5/58
#:     **1,5**|**18/25**| **2/91 (2,2%)** | **0/58**
#:       2,0  |  17/25  |  0/91        |   0/58
#:
#: **1,5 là ngưỡng THẤP NHẤT mà arm TRẦN không kêu một lần nào.** Đó là chỗ
#: đặt có lý do, không phải chỗ đẹp: dưới nó là bắt đầu kêu trên giọng bản ngữ
#: đọc ĐÚNG; trên nó thì bỏ sót thêm mà không mua lại được gì (18/25 -> 17/25).
#:
#: **HAI NHÓM KHÔNG TÁCH RỜI — nói thẳng.** Riêng trên CÂU (thứ lượt sản xuất
#: thật sự đọc) chỉ có **2 câu bịa / 68**, `lan` **1,90 và 2,32**, còn câu lành
#: cao nhất **1,86**. Khe hở **0,04** thì đó là trùng hợp, không phải ngưỡng
#: (đúng bài học `ty_giu`: biên 2,3% trên 1 điểm dữ liệu KHÔNG đặt được
#: ngưỡng). Vì vậy ngưỡng 1,5 được chọn theo **cột TRẦN**, và lưới an toàn
#: thật nằm ở chỗ khác: **chỉ NHẬN bản đọc lại khi nó THẬT SỰ đỡ hơn** — kêu
#: oan thì chỉ tốn thời gian, không đổi được tiếng.
NGUONG_LAN = 1.5


def soi_loat(texts: Sequence[str], giays: Sequence[float],
             nguong: Optional[float] = None,
             moc: Optional[tuple[float, float]] = None,
             ) -> tuple[list[float], tuple[float, float]]:
    """Soi CẢ LOẠT -> `(lan[i], mốc (a, b))`. `lan[i] = 0.0` là câu LÀNH.

    `moc` truyền vào thì DÙNG LẠI thay vì khớp mới — bắt buộc khi chấm lại
    mấy câu vừa đọc lại: khớp mốc trên 3 câu là khớp trên chính nhóm nghi
    ngờ, và bản mới sẽ luôn trông "bình thường" so với chúng.

    Không đủ mẫu -> trả toàn `0.0` (không dò được thì im). **KHÔNG BAO GIỜ NÉM.**
    """
    n = len(texts)
    ra = [0.0] * n
    try:
        ng = float(NGUONG_LAN if nguong is None else nguong)
        a, b = moc if moc is not None else moc_nhip(texts, giays)
        if b <= 0:
            return ra, (0.0, 0.0)
        for i in range(n):
            g = float(giays[i]) if i < len(giays) else 0.0
            lan = lan_vuot(texts[i], g, a, b)
            if lan >= ng:
                ra[i] = lan
        return ra, (a, b)
    except Exception:  # noqa: BLE001
        return [0.0] * n, (0.0, 0.0)
