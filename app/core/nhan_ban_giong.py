# -*- coding: utf-8 -*-
"""NHÂN BẢN GIỌNG TỪ MẪU — anh Hùng đưa file mẫu vào là ra một giọng mới.

**VIỆC NÀY LÀ GÌ, NÓI CHO DỄ HIỂU:** đưa cho máy vài giây tiếng của một người,
máy đọc bất kỳ câu nào bằng giọng người đó. 8 mẫu khác nhau -> 8 giọng cho 8
kênh, 0 đồng.

**MÁY NHÂN BẢN ĐÃ CÓ SẴN, FILE NÀY KHÔNG VIẾT LẠI CÁI NÀO:**

    tiếng VIỆT   -> ``giong_vieneu``  (``vnb:<đường dẫn>``)
                    đo được: nhân bản chạy THẬT · khớp chữ 14,6-15,4 ms ·
                    **0% bịa chữ** · Apache 2.0
    23 tiếng KHÁC -> ``giong_chatter`` (``cb:<lang>|<đường dẫn>``)
                    MIT · nhưng rung 76 ms · KHÔNG có tiếng Việt · cần GPU

Cái file này làm là **ĐƯỜNG NGƯỜI DÙNG ĐI**, phần trước nay chưa có:
chọn file mẫu -> **KIỂM mẫu có dùng được không** -> đặt TÊN TIẾNG VIỆT ->
**LƯU LẠI ĐỂ DÙNG LẠI**, không phải chọn file lại mỗi lần.

═══════════════════════════════════════════════════════════════════════════
"DÙNG LẠI" NGHĨA LÀ GÌ — NÓI CHÍNH XÁC, ĐỪNG HỨA QUÁ
═══════════════════════════════════════════════════════════════════════════
Cả VieNeu lẫn Chatterbox đều nhân bản **tại lúc đọc** (zero-shot): mỗi lượt
đọc vẫn phải đưa file mẫu vào. Nên "dùng lại" ở đây nghĩa là **anh Hùng chọn
file MỘT LẦN, đặt tên, rồi mãi mãi chỉ chọn cái tên đó** — chứ KHÔNG phải app
nén sẵn giọng thành một file nhỏ. Nói khác đi là hứa một thứ không có.

Đổi lại, có một thứ file này bảo đảm thật: **mẫu được CHÉP VÀO DATA_DIR**. Anh
Hùng xoá/di chuyển/đổi tên file gốc thì giọng vẫn chạy. Không chép thì đúng
một tháng sau cả loạt kênh mất giọng và triệu chứng chỉ là "tự nhiên đổi
giọng" — không ai lần ra.

═══════════════════════════════════════════════════════════════════════════
CẢNH BÁO PHÁP LÝ — ANH HÙNG **BÁN** APP, KHÔNG CHỈ TỰ DÙNG
═══════════════════════════════════════════════════════════════════════════
Đây là chỗ nguy hiểm nhất của cả tính năng, và nó không phải rủi ro kỹ thuật.
Nhân bản giọng người khác mà không có phép là chuyện **pháp lý**, không phải
chuyện chất lượng — và người chịu là người bán app. ``CANH_BAO_PHAP_LY`` phải
hiện **ngay tại chỗ chọn file**, không giấu trong tài liệu.

Ba mức, tự anh Hùng chọn (app không thể tự biết mẫu ở đâu ra):
  · **AN TOÀN** — giọng của chính anh Hùng / nhân viên có ký giấy;
    hoặc giọng hiến vào phạm vi công cộng (Mozilla Common Voice, CC0).
  · **RỦI RO** — giọng lấy từ video trên mạng, kể cả video "ai cũng xem được".
  · **CẤM** — giọng thương mại (Vbee · FPT · Zalo · ElevenLabs) và giọng người
    nổi tiếng. Repo này đã TỪ CHỐI hai model vì lý do đó (*"Ngọc Huyền"* tự
    khai huấn luyện trên giọng Vbee · Kokoro-Vietnamese giấu nguồn dữ liệu).

App **KHÔNG tự chặn được** (không có cách nào nhìn một file wav mà biết nó của
ai), nên nó làm đúng thứ làm được: **nói ra, và ghi lại lựa chọn của người
dùng** (``nguon`` trong sổ) để sau này có chuyện thì tra được.

═══════════════════════════════════════════════════════════════════════════
KIỂM MẪU — VÌ SAO PHẢI KIỂM
═══════════════════════════════════════════════════════════════════════════
Mẫu xấu KHÔNG làm app nổ — nó ra một giọng nghe hỏng, và anh Hùng chỉ biết
sau khi đã xuất vài chục video. Đó đúng loại hỏng âm thầm repo này chống. Nên
``kiem_mau`` chặn trước: quá ngắn · gần như toàn im lặng · vỡ tiếng · nhiều
người nói (chưa đo được thì NÓI LÀ CHƯA ĐO, không đoán).

**KHÔNG BAO GIỜ NÉM** ở mọi hàm — một mẫu hỏng không được phép giết cả lượt.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

_NO_WIN = 0x08000000 if os.name == "nt" else 0

MAY_VIENEU = "vieneu"
MAY_CHATTER = "chatter"

#: Mẫu NGẮN HƠN mức này thì máy không đủ tiếng để bắt chất giọng. VieNeu chạy
#: được với ~5 giây (lượt 9 đo trên mẫu 4-7 giây, 8/8 mẫu ra giọng khác nhau),
#: nên 4,0 là sàn CÓ CĂN CỨ chứ không phải số tròn cho đẹp.
MAU_GIAY_MIN = 4.0

#: Dài hơn mức này KHÔNG tốt hơn, chỉ chậm hơn và tốn chỗ. Cắt bớt là việc
#: của người dùng, app chỉ CẢNH BÁO chứ không tự cắt (tự cắt là tự chọn đoạn
#: nào đại diện cho giọng — app không có tai để chọn).
MAU_GIAY_MAX = 30.0

#: Tỉ lệ thời lượng THẬT SỰ có tiếng. Dưới mức này là mẫu chủ yếu im lặng ->
#: phần "giọng" mà máy học được ít hơn hẳn con số giây trên nhãn.
TY_LE_TIENG_MIN = 0.45

#: Đỉnh (dBFS) trên mức này coi như VỠ TIẾNG (đã chạm trần lúc thu/nén).
DINH_VO_DBFS = -0.5

CANH_BAO_PHAP_LY = (
    "CHỈ dùng giọng anh có quyền: giọng của chính mình, của nhân viên đã đồng "
    "ý, hoặc giọng hiến công khai. KHÔNG nhân bản giọng người nổi tiếng, "
    "giọng phát thanh viên, hay giọng của các hãng bán giọng (Vbee, FPT, "
    "Zalo, ElevenLabs) - anh đang BÁN app nên chuyện này là rủi ro pháp lý "
    "cho cả app, không phải chuyện chất lượng tiếng.")

#: ═══ GIỌNG NHÂN BẢN ĐỌC **TIẾNG ANH** — BẢNG SỐ ĐO 26/08/2026 ═══
#: (`_do_vnb_en.py` -> `_kq_vnb_en.txt` · `_do_vnb_nhip.py` -> `_kq_vnb_nhip.json`)
#:
#: Anh Hùng: *"khi clone giọng tiếng Anh nó đọc như thằng mới học ấy, nói không
#: lưu loát không chuẩn chữ"* — màn hình anh ấy là **đích Tiếng Anh** + giọng
#: **`vnb:`** (nhân bản chạy VieNeu).
#:
#: Ba arm **GHÉP CẶP trên CÙNG một file mẫu** (mẫu do edge-tts
#: `en-US-AndrewMultilingual` sinh — KHÔNG nhân bản giọng thương mại nào), cùng
#: 34 câu + 24 token rời, đi **cửa thật** `dubbing._synth_all`, chấm bằng đúng
#: bộ chấm của `_do_vieneu_en.py`. Trần đối chứng lấy lại **đúng file tiếng**
#: của bảng 19/08 nên hai bảng so được với nhau.
#:
#:   arm (cùng mẫu)      | tok TRONG CÂU | tok ĐỌC RỜI | bịa chữ  | WER
#:   `vnb:` VieNeu       | **2,6-5,1%**  | 29,2-37,5%  | **0,3-9,7%** | **3,1-12,7%**
#:   `cb:` Chatterbox    | **17,9%**     | 33,3%       | 2,2%     | 6,0%
#:   edge Aria (TRẦN)    | 0,0%          | 4,2%        | 0,9%     | 3,7%
#:   `vn:Adam` dựng sẵn  | 7,7-12,8%     | 12,5-25,0%  | 0,6%     | 5,2-7,0%
#:
#: **HAI KẾT LUẬN, CẢ HAI ĐỀU NGƯỢC VỚI CÁI ĐƯỢC CHỜ ĐỢI:**
#:
#: (1) **ĐỔI SANG CHATTERBOX KHÔNG CHỮA ĐƯỢC** — nó sai chữ TRONG CÂU
#: **17,9%**, tức **3,5-7 lần TỆ HƠN** `vnb:`; đọc rời cũng ngang ngửa
#: (33,3% vs 29,2-37,5%). Nó chỉ hơn ở chỗ **ĐỀU**: hai lượt ra số **giống
#: hệt** (WER 6,05 vs 6,05 — tiền định thật, đúng như `giong_chatter` đã ghi).
#: Đổi lấy cái đều đó thì phải trả **GPU NVIDIA bắt buộc · đóng dấu chìm Perth
#: KHÔNG tắt được (anh Hùng BÁN video) · nhịp đọc lệch theo tiếng**. Không
#: đáng, và số nói thẳng là không đáng.
#:
#: (2) **BỆNH THẬT KHÔNG PHẢI "ĐỌC SAI TIẾNG ANH" MÀ LÀ "KHÔNG ỔN ĐỊNH".**
#: `vnb:` chạy **2 lượt trên ĐÚNG một bộ chữ, ĐÚNG một file mẫu** mà ra:
#:     lượt 1: WER **3,1%** · bịa chữ **0,3%** (tức **HƠN CẢ TRẦN** edge 3,7%)
#:     lượt 2: WER **12,7%** · bịa chữ **9,7%** (31/320 từ máy tự thêm vào)
#: Nhịp đọc cùng chiều (`_kq_vnb_nhip.json`): trung vị chỉ 1,03-1,04x trần,
#: nhưng câu tệ nhất **1,53x rồi 2,54x**, và số câu vượt trần `atempo` là
#: **1/34 rồi 3/34** — tức thỉnh thoảng có câu model đọc lan man, đường xuất ép
#: không nổi. Token ĐỌC RỜI lộ rõ nhất: «2026» nghe ra `在英雄城的美索`, «90%»
#: ra `请你分赞`, «OST» ra một câu tiếng Trung **lặp 3 lần**.
#: **Đó đúng là thứ tai nghe ra "như thằng mới học":** phần lớn câu đọc tốt,
#: rồi bỗng một câu bịa chữ / lặp / lan man.
#:
#: **VÌ SAO KHÔNG VÁ BẰNG `doc_viet_tat` (hướng còn lại):** bảng trên đo được
#: token sai TRONG CÂU của `vnb:` chỉ **1-2 trên 39** — lớp viết-tắt ĐÃ ĐÚNG
#: SẴN. Chép âm cho thứ đang đúng là **rủi ro thuần**, đúng lớp bằng chứng đã
#: loại bảng TÊN RIÊNG; và lần vá `doc_viet_tat` cho VieNeu trước đây đo ra
#: **TỆ ĐI 2 · TỐT LÊN 0** (xem `doc_viet_tat.py`). Không lặp lại.
#:
#: **CÒN NỢ, GHI THẲNG:** chỉ đo trên **MỘT** file mẫu. `giong_chatter` đã đo
#: được *"MẪU kéo nhịp đọc, không riêng gì TIẾNG"* (cùng câu, hai mẫu ra 1,03x
#: và 1,32x), nên con số này **đi theo mẫu** — mẫu của anh Hùng có thể khác.
#: Và cỡ mẫu 2 lượt đủ để nói **"KHÔNG ĐỀU"**, KHÔNG đủ để nói tỉ lệ hỏng.
SO_DO_EN: dict[str, dict[str, str]] = {
    # khoá = arm · giá trị = {thước: số}. MỘT NGUỒN cho mọi nhãn/cảnh báo —
    # gõ lại con số ở nhãn là đẻ ra bản sao thứ hai rồi một ngày hai bản lệch.
    #
    # `ngat` / `ngat_tv` THÊM 27/08/2026 — xem khối "NGẮT GIỮA CÂU" ngay dưới.
    "vnb": {"cau": "2,6-5,1%", "roi": "29,2-37,5%", "bia": "0,3-9,7%",
            "wer": "3,1-12,7%", "nhip": "1,53x rồi 2,54x",
            "ngat": "2,65", "ngat_tv": "0,070 s"},
    "cb": {"cau": "17,9%", "roi": "33,3%", "bia": "2,2%", "wer": "6,0%",
           "nhip": "1,57x"},
    "tran": {"cau": "0,0%", "roi": "4,2%", "bia": "0,9%", "wer": "3,7%",
             "nhip": "1,00x",
             "ngat": "1,08", "ngat_tv": "0,190 s"},
}

#: NGẮT GIỮA CÂU — thước của triệu chứng anh Hùng gọi là **"như trẻ con mới
#: đánh vần"** (27/08/2026). ĐỌC KHỐI NÀY TRƯỚC KHI ĐI SỬA TIẾNG.
#:
#: **KHÁC HẲN thước ở `SO_DO_EN` phía trên.** Bảng trên đếm chữ SAI và chữ
#: BỊA — tức lỗi ở CUỐI/TRONG câu. "Đánh vần" mô tả một thứ khác: đọc **rời
#: rạc, ngắt quãng GIỮA câu**. Nên phải có thước riêng, và thước đó là số
#: khoảng lặng nằm GIỮA các khoảng có tiếng (bỏ lề đầu/cuối), quy về
#: **/100 ký tự** cho câu dài ngắn so được với nhau.
#:
#: **ĐO TRÊN CHÍNH TIẾNG MÁY ANH HÙNG VỪA ĐỌC RA**, không phải câu dựng lại:
#: 184 file `_tam_*/raw/*.wav` còn nguyên trong `%LOCALAPPDATA%\BQHungVideo`,
#: ghép với `_job_*/job.json` để biết câu nào ra file nào. TRẦN đối chứng là
#: edge-tts **BẢN NGỮ** đọc **CÙNG bộ câu** — không có trần thì "0,96 ngắt mỗi
#: câu" là con số vô nghĩa.
#:
#:   arm (40 câu đầu, cùng bộ chữ)   | ngắt/100 kt | ngắt/câu | trung vị ngắt
#:   --------------------------------|-------------|----------|--------------
#:   `vnb:` đọc **TIẾNG ANH**        | **2,65**    | 1,07     | **0,070 s**
#:   TRẦN edge `en-US` (bản ngữ)     | 1,08        | 0,53     | 0,190 s
#:   `vnb:` đọc **TIẾNG VIỆT**       | **0,18**    | 0,05     | —
#:   TRẦN edge `vi-VN` (bản ngữ)     | 0,91        | 0,33     | 0,070 s
#:
#: **HAI TỈ SỐ NÀY LÀ CẢ CÂU TRẢ LỜI: tiếng Anh 2,45 LẦN trần bản ngữ · tiếng
#: Việt 0,20 LẦN trần bản ngữ — lệch nhau 12 lần.** Cùng engine, cùng máy,
#: cùng cơ chế nhân bản, hai lượt chạy cách nhau chưa đầy một ngày. Tức triệu
#: chứng là chuyện **model VieNeu (checkpoint TIẾNG VIỆT) đọc TIẾNG ANH**,
#: không phải chuyện cấu hình, không phải chuyện bản vá nào.
#:
#: **DẤU HIỆU ĐẶC TRƯNG NẰM Ở TRUNG VỊ, ĐỪNG BỎ QUA:** chỗ ngắt của `vnb:`
#: **NGẮN** (0,070 s) mà **NHIỀU**; chỗ ngắt của bản ngữ **DÀI** (0,190 s) mà
#: **ÍT**. Ngắt dài và thưa = ngắt nghỉ đúng chỗ; ngắt ngắn và dày = hụt hơi
#: vụn giữa câu — đúng nghĩa "đánh vần".
#:
#: **VÌ SAO KHÔNG VÁ ĐƯỢC BẰNG CÁCH SỬA TIẾNG — ĐÃ ĐO CẢ HAI CHIỀU, CẢ HAI
#: ĐỀU BỊ BÁC** (`_do_siet_ngat.py`, hàm thuần trên chính 184 file đó):
#:   * **cắt ngắt DÀI** (ép mọi khoảng lặng xuống <= trần): ở MỌI trần thử
#:     (0,30 · 0,20 · 0,15 · 0,12 · 0,10 s) thì **TRẦN BẢN NGỮ bị đụng NẶNG
#:     HƠN** giọng đang hỏng — 7,5% vs 3,8% ở trần 0,30, tới 22,5% vs 14,1% ở
#:     trần 0,10. Vá thế là bẻ nhịp nói tự nhiên nhiều hơn là chữa chỗ vụn.
#:   * **gộp ngắt NGẮN** (< 0,15 s): nó xoá **100% (13/13)** khoảng ngắt của
#:     TRẦN bản ngữ tiếng Việt và 38% của trần tiếng Anh. Không có ngưỡng nào
#:     tách được "hụt hơi bệnh lý" khỏi "ngắt hơi tự nhiên".
#: Hai nhóm **CHỒNG NHAU theo ĐỘ DÀI**, chỉ tách nhau theo **MẬT ĐỘ** — mà mật
#: độ thì không sửa được bằng kéo cắt. Cùng bài học `ty_giu` (*"1 điểm dữ liệu
#: thì KHÔNG đặt ngưỡng"*) và `doc_lan` (*"hai nhóm CHỒNG NHAU — nói thẳng,
#: không giả vờ có đường kẻ sạch"*). **Đừng ai đi lại hai đường này.**
SO_DO_NGAT: dict[str, str] = {
    "en_vnb": "2,65", "en_tran": "1,08", "en_ty": "2,45",
    "vi_vnb": "0,18", "vi_tran": "0,91", "vi_ty": "0,20",
}

#: Sổ ghi ở DATA_DIR. Khoá theo TÊN người dùng đặt.
_TEN_SO = "giong_nhan_ban.json"


# ---------------------------------------------------------------------------
# Chỗ để đồ
# ---------------------------------------------------------------------------
def thu_muc_mau() -> Path:
    """Nơi CHÉP mẫu vào. Đọc ``config.DATA_DIR`` MỖI LẦN GỌI.

    Không cất hằng số ở tầm module: cổng test trỏ ``BQ_DATA_DIR`` sang thư mục
    tạm sau khi module đã nạp, cất sẵn là ghi vào DATA_DIR THẬT của anh Hùng
    (bài học ``tg_so.duong_so``).
    """
    try:
        import config
        goc = Path(getattr(config, "DATA_DIR", "") or ".")
    except Exception:                                          # noqa: BLE001
        goc = Path(".")
    return goc / "_mau_giong"


def duong_so() -> Path:
    try:
        import config
        goc = Path(getattr(config, "DATA_DIR", "") or ".")
    except Exception:                                          # noqa: BLE001
        goc = Path(".")
    return goc / _TEN_SO


def _ffmpeg() -> str:
    p = Path(__file__).resolve().parents[2] / "bin" / "ffmpeg.exe"
    return str(p) if p.exists() else "ffmpeg"


# ---------------------------------------------------------------------------
# KIỂM MẪU
# ---------------------------------------------------------------------------
def _do_mau(duong: str) -> dict:
    """Đo mẫu bằng MỘT lượt ffmpeg: độ dài · đỉnh · tỉ lệ có tiếng.

    Dùng ``silencedetect`` (thước độc lập, không máy nghe) + ``astats``.

    **``Abs_Peak_count`` chứ KHÔNG phải ``Number_of_clipped_samples``** — tên
    thứ hai KHÔNG TỒN TẠI trong ffmpeg N-121186 và làm CẢ LỆNH ffmpeg chết,
    rồi hàm trả None âm thầm = tự phát chứng nhận vĩnh viễn (bẫy cổng 53).
    Ở đây chỉ cần ``Peak level dB``, và phải dò bằng ``in`` chứ không
    ``startswith``: mỗi dòng ``astats`` mở đầu bằng ``[Parsed_astats_0 @ ...]``
    nên ``startswith`` KHÔNG BAO GIỜ khớp (bẫy cổng 44).
    """
    r = subprocess.run(
        [_ffmpeg(), "-v", "info", "-i", str(duong), "-af",
         "silencedetect=noise=-40dB:d=0.20,astats=measure_perchannel=none",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NO_WIN, timeout=300)
    txt = (r.stderr or "") + (r.stdout or "")
    if r.returncode != 0:
        return {"loi": f"ffmpeg không đọc được file (mã {r.returncode})"}
    # Lấy mốc `time=` LỚN NHẤT, không lấy cái cuối cùng: ffmpeg in nhiều dòng
    # tiến trình và dòng cuối không bảo đảm là dòng lớn nhất.
    dai = 0.0
    for mm in re.finditer(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", txt):
        dai = max(dai, int(mm.group(1)) * 3600 + int(mm.group(2)) * 60
                  + float(mm.group(3)))
    im = 0.0
    for mm in re.finditer(r"silence_duration:\s*(\d+(?:\.\d+)?)", txt):
        im += float(mm.group(1))
    dinh = None
    for d in txt.splitlines():
        if "Peak level dB:" in d:
            try:
                dinh = float(d.split("Peak level dB:")[1].strip())
            except (IndexError, ValueError):
                pass
    return {"giay": round(dai, 2), "im_giay": round(im, 2),
            "dinh_dbfs": dinh,
            "ty_le_tieng": round(max(0.0, dai - im) / dai, 3) if dai > 0
            else 0.0}


def kiem_mau(duong: str) -> dict:
    """Mẫu này có dùng để nhân bản được không.

    Trả ``{"ok", "giay", "ty_le_tieng", "dinh_dbfs", "loi", "canh_bao"}``.

    ``ok=False`` = **đừng dùng** (có ``loi``). ``ok=True`` kèm ``canh_bao`` =
    dùng được nhưng nên biết trước. Phân biệt hai mức là cố ý: gộp làm một thì
    hoặc chặn oan mẫu dùng được, hoặc cho qua mẫu hỏng.

    **KHÔNG BAO GIỜ NÉM.**
    """
    ra = {"ok": False, "giay": 0.0, "ty_le_tieng": 0.0, "dinh_dbfs": None,
          "loi": "", "canh_bao": []}
    try:
        p = Path(str(duong or "").strip())
        if not str(p) or str(p) in (".", ""):
            ra["loi"] = "Chưa chọn file mẫu"
            return ra
        if not p.exists() or not p.is_file():
            ra["loi"] = "Không tìm thấy file mẫu"
            return ra
        if p.stat().st_size < 4000:
            ra["loi"] = "File mẫu quá nhỏ (gần như rỗng)"
            return ra
        d = _do_mau(str(p))
        if d.get("loi"):
            ra["loi"] = d["loi"]
            return ra
        ra.update({k: d[k] for k in ("giay", "ty_le_tieng", "dinh_dbfs")
                   if k in d})
        if d["giay"] < MAU_GIAY_MIN:
            ra["loi"] = (f"Mẫu chỉ dài {d['giay']:.1f} giây, cần ít nhất "
                         f"{MAU_GIAY_MIN:.0f} giây tiếng nói")
            return ra
        if d["ty_le_tieng"] < TY_LE_TIENG_MIN:
            ra["loi"] = (f"Mẫu chủ yếu là im lặng (chỉ "
                         f"{100 * d['ty_le_tieng']:.0f}% có tiếng)")
            return ra
        if d["giay"] > MAU_GIAY_MAX:
            ra["canh_bao"].append(
                f"Mẫu dài {d['giay']:.0f} giây - dài hơn "
                f"{MAU_GIAY_MAX:.0f} giây không làm giọng giống hơn, chỉ chậm "
                f"hơn. Cắt ngắn lại thì tốt hơn.")
        if d["dinh_dbfs"] is not None and d["dinh_dbfs"] > DINH_VO_DBFS:
            ra["canh_bao"].append(
                f"Mẫu đã chạm trần âm lượng ({d['dinh_dbfs']:.1f} dBFS) - "
                f"tiếng có thể bị vỡ, giọng nhân bản sẽ rè theo.")
        # CHƯA ĐO ĐƯỢC thì NÓI LÀ CHƯA ĐO, không đoán: dò "mẫu có mấy người
        # nói" cần ECAPA + phân đoạn, mà bộ đó chỉ có khi máy đã tải model.
        ra["canh_bao"].append(
            "App KHÔNG kiểm được mẫu có mấy người nói - mẫu lẫn hai giọng thì "
            "giọng nhân bản ra sẽ lai. Nên dùng đoạn chỉ một người nói, không "
            "nhạc nền.")
        ra["ok"] = True
        return ra
    except Exception as e:                                     # noqa: BLE001
        ra["loi"] = f"Không đọc được mẫu: {type(e).__name__}"
        return ra


# ---------------------------------------------------------------------------
# SỔ GIỌNG ĐÃ NHÂN BẢN
# ---------------------------------------------------------------------------
def _doc_so() -> dict:
    """Đọc sổ. Hỏng -> ``{}`` (**không ném, không tự ghi đè**).

    Ghi đè một sổ đọc không được là mất sạch giọng anh Hùng đã đặt tên — đúng
    bài học ``prodown`` "serde default hoặc mất data": file cũ parse hỏng ->
    load rỗng -> lượt ghi kế tiếp xoá hết.
    """
    try:
        p = duong_so()
        if not p.exists():
            return {}
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                          # noqa: BLE001
        return {}


def _muc(so: dict, ten: str) -> dict:
    """Một mục trong sổ, LUÔN là dict. Mục lạ (chuỗi/None/số) -> ``{}``.

    ═══ VÌ SAO PHẢI CÓ, KHÔNG PHẢI CHO GỌN ═══
    ``_doc_so`` chỉ bảo đảm thứ trả về là **dict ngoài cùng**, nó KHÔNG kiểm
    từng mục. Sổ bị sửa tay / bản cũ khác hình dạng / một lượt ghi hỏng là
    ``so[ten]`` thành chuỗi, rồi ``g.get(...)`` ném ``AttributeError`` ngay
    trong ``danh_sach()`` -> **combo giọng chết cả cụm** vì MỘT mục hỏng, mà
    lời lỗi lại không nói gì về sổ. Đây đúng luật "sổ thiếu khoá thì phải đọc
    được, không được nổ".
    """
    g = (so or {}).get(str(ten or "").strip())
    return g if isinstance(g, dict) else {}


def _so_giay(g: dict) -> float:
    """``giay`` của một mục -> float. Khoá thiếu / chữ rác -> ``0.0``.

    ``float(g.get('giay') or 0)`` ném ``ValueError`` khi ``giay`` là chuỗi rác
    (``"4,5"`` — dấu phẩy tiếng Việt là ca RẤT dễ gặp nếu ai sửa sổ bằng tay),
    và ``nhan()`` không có ``try`` nên nó nổ lên tới ``danh_sach()``.
    """
    try:
        return float(g.get("giay") or 0)
    except (TypeError, ValueError):
        return 0.0


def _sao_luu_neu_hong(p: Path) -> str:
    """Sổ trên đĩa ĐỌC KHÔNG RA thì chép riêng một bản. Trả đường bản sao.

    ═══ LỖ THẬT, VÁ 20/08/2026 — ĐỌC KỸ ═══
    ``_doc_so`` cố ý trả ``{}`` khi sổ hỏng và **không tự ghi đè** (đúng bài
    học ``prodown`` "serde default hoặc mất data"). Nhưng chốt đó chỉ chặn
    được NỬA đường: lượt ghi KẾ TIẾP (``them_giong``/``xoa``/``doi_ten``) lấy
    ``so = _doc_so()`` = ``{}``, thêm một mục, rồi ``_ghi_so`` **thay nguyên
    file** — tức nội dung cũ mất SẠCH, đúng cái ``_doc_so`` vừa cố tránh.
    Anh Hùng chạy 200-300 kênh, sổ đó là toàn bộ tên giọng anh ấy đã đặt.

    Nên: ghi đè thì cứ ghi (không ghi được là app không dùng được), **nhưng
    phải để lại bản sao** để còn cứu tay. Không im lặng: ghi cả vào log.
    """
    try:
        if not p.exists():
            return ""
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return ""                  # đọc được -> không có gì phải cứu
    except Exception:                                          # noqa: BLE001
        pass                           # đọc KHÔNG ra -> đi tiếp, cứu file
    try:
        bk = p.with_name(f"{p.stem}.hong-{time.strftime('%Y%m%d-%H%M%S')}.json")
        shutil.copyfile(p, bk)
        _ghi_log(f"Sổ giọng nhân bản ĐỌC KHÔNG RA -> đã sao lưu sang {bk.name} "
                 f"trước khi ghi đè. Mở file đó ra cứu tay nếu cần.")
        return str(bk)
    except Exception:                                          # noqa: BLE001
        return ""


def _ghi_log(dong: str) -> None:
    """Ghi lý do vào log ngày. KHÔNG BAO GIỜ NÉM.

    Cùng luật ``giong_vieneu._ghi_log``: một lượt lùi/cứu ÊM mà im lặng thì
    đúng bằng hỏng âm thầm.
    """
    try:
        import datetime
        from config import DATA_DIR
        p = Path(DATA_DIR) / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        with open(p / f"nhan_ban_giong_{ts:%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{ts:%H:%M:%S}] {dong}\n")
    except Exception:                                          # noqa: BLE001
        pass


def _ghi_so(d: dict) -> bool:
    """Ghi sổ kiểu THAY NGUYÊN FILE (ghi tạm rồi đổi tên).

    Ghi thẳng mà máy tắt giữa chừng là sổ cụt -> mất toàn bộ giọng. Cùng cách
    ``tg_so.py`` đã chốt.

    **SAO LƯU TRƯỚC KHI GHI ĐÈ MỘT SỔ ĐỌC KHÔNG RA** — xem
    ``_sao_luu_neu_hong``. Chốt này phải nằm ở ĐÂY (cửa GHI) chứ không ở
    ``_doc_so``: mọi đường sửa sổ đều đi qua đây, còn ``_doc_so`` bị gọi cả ở
    đường chỉ-đọc (``danh_sach``/``nhan``) nên đặt ở đó là sao lưu mỗi lần vẽ
    lại combo.
    """
    try:
        p = duong_so()
        p.parent.mkdir(parents=True, exist_ok=True)
        _sao_luu_neu_hong(p)
        tam = p.with_suffix(".tmp")
        tam.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tam, p)
        return True
    except Exception:                                          # noqa: BLE001
        return False


def _slug(ten: str) -> str:
    """Tên tiếng Việt -> tên file an toàn. ``Giọng chị Lan`` -> ``giong_chi_lan``.

    Bỏ dấu chứ KHÔNG bỏ chữ: tên file mà rỗng thì hai giọng khác nhau ghi đè
    nhau. Rỗng -> dùng mốc thời gian.

    **``_slug`` MỘT MÌNH KHÔNG ĐỦ ĐỂ ĐẶT TÊN FILE MẪU** — nó cố ý ÁNH XẠ NHIỀU
    THÀNH MỘT (bỏ dấu + gộp mọi ký tự lạ thành ``_``), nên *"Giọng chị Lan"* và
    *"giọng chị lan"* ra CÙNG một chuỗi. Chỗ đặt tên file phải đi qua
    ``_ten_mau_trong`` — xem lý do ở đó.
    """
    s = unicodedata.normalize("NFD", str(ten or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()
    return s or f"giong_{int(time.time())}"


def _khoa_mau(mau) -> str:
    """Khoá so sánh hai đường dẫn mẫu. Rỗng -> ``""`` (KHÔNG so được).

    So bằng chữ THƯỜNG vì Windows không phân biệt hoa/thường: cùng một file mà
    sổ ghi hai kiểu chữ thì vẫn là DÙNG CHUNG, và bỏ sót ca đó là để lọt đúng
    cái mã trùng đang đi chữa.
    """
    return str(mau or "").strip().lower()


def _ten_mau_trong(ten: str, so: dict, bo_qua: str = "") -> Path:
    """Đường dẫn file mẫu **RIÊNG** cho một bản ghi: chưa ai giữ, chưa có trên đĩa.

    ═══ ĐÂY LÀ CHỐT GIỮ CHO MÃ GIỌNG KHÔNG TRÙNG — ĐỌC TRƯỚC KHI SỬA ═══
    Mã giọng nhân bản là ``vnb:<đường dẫn mẫu>`` (``giong_vieneu.ma_nhan_ban``),
    tức **đường dẫn mẫu CHÍNH LÀ danh tính** của giọng. Suy ra một bất biến bắt
    buộc: **mỗi bản ghi trong sổ phải SỞ HỮU RIÊNG một file mẫu**. Hai bản ghi
    dùng chung một file là hai cái tên khác nhau ra MỘT mã — anh Hùng chọn
    *"Giọng chị Lan"* thì app đọc bằng *"Giọng của tôi"*, **không một dòng báo**.
    Đúng họ lỗi "chọn X ra Y" đã sập bốn lần (``ov:nu_am`` · ``vn:`` · ``cb:`` ·
    ``kk:``).

    Bản cũ đặt thẳng ``f"{_slug(ten)}.wav"``, và ĐO ĐƯỢC nó hỏng theo hai đường:
      · ``_slug`` ánh xạ NHIỀU-THÀNH-MỘT nên *"Giọng chị Lan"* và *"giọng chị
        lan"* ra cùng tên file, trong khi ``them_giong`` chỉ chặn TRÙNG TÊN
        nguyên văn -> lượt thêm thứ hai lọt cửa;
      · ffmpeg chạy với ``-y`` nên nó **GHI ĐÈ** file mẫu của bản ghi trước ->
        không chỉ trùng mã mà **mẫu của giọng cũ MẤT HẲN**, giọng cũ nay đọc
        bằng tiếng của giọng mới.

    Nên hàm này hỏi ĐỦ HAI CÂU trước khi trả về một cái tên:
      1. **có bản ghi nào đang giữ tên đó không** (đọc trong sổ) — chốt chống
         trùng mã;
      2. **trên đĩa đã có file đó chưa** — chốt chống ghi đè. File mồ côi (sổ
         không ai nhận, ví dụ ``xoa(xoa_ca_mau=False)`` để lại) vẫn phải được
         chừa ra: nó có thể là mẫu anh Hùng còn cần.

    ``bo_qua`` = tên bản ghi ĐANG được cấp lại tên (nó không tự chặn mình).
    """
    d = thu_muc_mau()
    giu = {_khoa_mau(_muc(so, t).get("mau"))
           for t in (so or {}) if t != bo_qua}
    giu.discard("")
    goc = _slug(ten)
    for i in range(1, 500):
        p = d / (f"{goc}.wav" if i == 1 else f"{goc}_{i}.wav")
        if _khoa_mau(p) in giu or p.exists():
            continue
        return p
    # Không bao giờ tới đây với người dùng thật; vẫn phải trả một tên DÙNG
    # ĐƯỢC chứ không ném — một cái tên xấu còn hơn chết cả lượt thêm giọng.
    return d / f"{goc}_{int(time.time() * 1000)}.wav"


def _nhom_mau_trung(so: dict) -> dict[str, list[str]]:
    """``{khoá mẫu -> [tên bản ghi]}`` cho những file mẫu bị **DÙNG CHUNG**.

    Chỉ trả nhóm từ 2 bản ghi trở lên; sổ lành thì trả ``{}``. Tên trong mỗi
    nhóm **sắp theo thứ tự chữ** — thứ tự đó quyết định ai GIỮ đường dẫn cũ nên
    nó phải TIỀN ĐỊNH, không được phụ thuộc thứ tự khoá trong file JSON.
    """
    theo: dict[str, list[str]] = {}
    for t in sorted(so or {}):
        k = _khoa_mau(_muc(so, t).get("mau"))
        if k:
            theo.setdefault(k, []).append(t)
    return {k: v for k, v in theo.items() if len(v) > 1}


def sua_mau_trung(so: dict | None = None) -> list[tuple[str, str]]:
    """Sổ đã có sẵn hai bản ghi trỏ chung một mẫu -> cho mỗi bản ghi một **BẢN
    SAO RIÊNG**. Trả ``[(tên, đường mẫu mới)]``. **KHÔNG BAO GIỜ NÉM.**

    ═══ VÌ SAO PHẢI CHỮA CẢ SỔ CŨ, KHÔNG CHỈ CHẶN LƯỢT THÊM MỚI ═══
    ``_ten_mau_trong`` chặn được mọi giọng thêm TỪ NAY. Nhưng sổ đã nằm trên đĩa
    máy anh Hùng thì không tự lành: hai bản ghi vẫn ra một mã, combo vẫn nuốt
    mất một dòng, và ``ten_theo_ma`` vẫn trả về cái tên ĐỨNG TRƯỚC chứ không
    phải cái người dùng chọn.

    ═══ VÌ SAO **CHÉP** CHỨ KHÔNG ĐỔI TÊN / KHÔNG XOÁ ═══
    File trong ``_mau_giong`` là mẫu giọng THẬT của anh Hùng. Đổi tên nó là làm
    hỏng mã của bản ghi đang giữ nó (kênh đang gán tra không ra -> rơi về giọng
    mặc định, im lặng). Nên: **bản ghi ĐẦU TIÊN theo thứ tự chữ GIỮ NGUYÊN
    đường dẫn cũ** — mã của nó không đổi một ký tự, tức mọi kênh đang gán mã ấy
    chạy y như hôm nay; những bản ghi còn lại nhận một BẢN SAO. Không file nào
    bị xoá, không file nào bị sửa.

    Hệ quả phải nói thẳng: nhóm có N bản ghi thì **N−1 bản ghi đổi mã**. Không
    tránh được — N cái tên đang chia nhau MỘT mã thì nhiều nhất một cái giữ
    được. Đổi lại, cái giữ mã là cái mà ``ten_theo_ma`` VẪN ĐANG trả về hôm nay
    (cùng phép ``sorted``), nên **không kênh nào đổi hành vi**: kênh nào đang
    đọc ra giọng gì thì sau lượt chữa vẫn đọc ra đúng giọng đó.

    Mẫu dùng chung mà **đã mất trên đĩa** -> BỎ QUA: lúc đó ``ma_giong`` trả
    ``""`` cho cả nhóm nên không có mã trùng nào lọt ra combo, và việc báo mẫu
    mất là của ``sua_mau_mat()``. Chép một file không tồn tại thì được gì.
    """
    try:
        if not _nhom_mau_trung(_doc_so() if so is None else so):
            return []
        # Sắp GHI -> đọc lại bản mới nhất, đừng ghi đè bằng ảnh chụp của caller.
        so = _doc_so()
        nhom = _nhom_mau_trung(so)
        if not nhom:
            return []
        da: list[tuple[str, str]] = []
        for _k, tens in sorted(nhom.items()):
            goc = Path(str(_muc(so, tens[0]).get("mau") or ""))
            if not goc.is_file():
                continue
            for t in tens[1:]:
                moi = _ten_mau_trong(t, so, bo_qua=t)
                try:
                    moi.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(goc, moi)
                except Exception:                              # noqa: BLE001
                    continue                   # chép không được -> để nguyên
                g = dict(_muc(so, t))
                g["mau"] = str(moi)
                so[t] = g
                da.append((t, str(moi)))
        # `_ghi_so` tự sao lưu sổ đọc-không-ra trước khi thay file.
        if not da or not _ghi_so(so):
            return []
        for t, m in da:
            _ghi_log(f"Giọng «{t}» dùng CHUNG file mẫu với một giọng khác nên "
                     f"hai giọng ra CÙNG một mã -> đã chép riêng sang "
                     f"{Path(m).name}. File mẫu cũ GIỮ NGUYÊN, không xoá.")
        return da
    except Exception:                                          # noqa: BLE001
        return []


def goi_y_may(lang: str = "vi") -> str:
    """Ngôn ngữ -> máy nhân bản NÊN dùng, **LÚC TẠO GIỌNG**.

    Tiếng Việt chỉ VieNeu làm được (Chatterbox không có ``vi``, đo thật: câu
    Việt đọc ra thành chuỗi vô nghĩa). Ngoài ra thì Chatterbox — vì đó là bộ
    DUY NHẤT khai 23 thứ tiếng, không phải vì nó đọc hay hơn.

    ═══ HÀM NÀY **KHÔNG NẰM TRÊN ĐƯỜNG ĐỌC** — ĐO ĐƯỢC, ĐỪNG SUY ═══
    Truy vết 26/08/2026 (`_do_vet_goiymay.py`, quét bằng **AST** + **GỌI
    THẬT**, không grep chuỗi):
      · nơi gọi thật trong `app/`: **đúng 1**, là `them_giong()`;
      · trong `app/ui/`: **0** (grep chuỗi ra 2 dòng — cả hai là GHI CHÚ);
      · gọi thật `dubbing._synth_all(voice="vnb:...", lang="en")` -> rẽ vào
        **`giong_vieneu.doc_loat`**, y như khi `lang="vi"`.
    Nghĩa là máy đọc được chốt **MỘT LẦN lúc bấm Lưu giọng**, theo ô *"Giọng
    này để đọc tiếng"*; ô **"Ngôn ngữ đích"** của lượt thay tiếng KHÔNG bao giờ
    hỏi lại hàm này. Sổ thật của anh Hùng: giọng «adam Clone» ghi
    ``may='vieneu' lang='vi'`` (mẫu là một đoạn ghi âm **tiếng Anh**), nên
    chọn đích Tiếng Anh vẫn chạy VieNeu. Đó là lời giải cho câu hỏi *"sao chọn
    tiếng Anh mà vẫn ra VieNeu"*.

    ═══ VÀ **ĐỪNG** NỐI NÓ VÀO ĐƯỜNG ĐỌC — SỐ ĐO BÁC ═══
    Nghe thì hợp lý: *"đích tiếng Anh thì đổi sang Chatterbox cho chuẩn"*.
    Đo rồi thì **ngược**: trên CÙNG một file mẫu, `cb:` sai chữ trong câu
    **17,9%** còn `vnb:` chỉ **2,6-5,1%** (xem ``SO_DO_EN``). Đổi máy lúc đọc
    là **làm tệ đi 3,5-7 lần**, lại thêm ba cái giá (GPU · dấu chìm · nhịp).
    Muốn đổi thì phải có bảng số MỚI nói ngược ``SO_DO_EN``, không phải suy.
    """
    l = (lang or "").strip().lower()[:2]
    return MAY_VIENEU if l in ("", "vi") else MAY_CHATTER


#: Ngôn ngữ mà VieNeu là model BẢN ĐỊA (checkpoint `VieNeu-TTS-1000h`).
_NN_CUA_VIENEU = ("", "vi")


def canh_bao_doc_tieng(ma: str, lang: str) -> str:
    """Câu cảnh báo cho giao diện khi giọng NHÂN BẢN đọc tiếng NGOÀI sở trường.

    Trả ``""`` khi không có gì phải nói — nhãn rỗng là nhãn không gây nhiễu, và
    kêu oan thì lần sau người ta thôi đọc nhãn.

    **VÌ SAO LÀ NHÃN CHỨ KHÔNG PHẢI MÃ** (đúng tiền lệ `vn:Adam` 19/08): thứ đo
    được là *giọng này ĐỌC KHÔNG ĐỀU*, không phải *app chọn sai máy*. Chặn thì
    mất một tính năng đang chạy tốt phần lớn thời gian (lượt 1 đo ra **hơn cả
    trần** edge-tts); tự đổi máy thì làm tệ đi 3,5-7 lần (xem ``goi_y_may``).
    Cái còn lại — và là cái repo này luôn đòi — là **nói thật, kèm số**.

    Mọi con số lấy từ ``SO_DO_EN``, KHÔNG gõ tay: một phép đo, một chỗ sửa.
    """
    try:
        m = str(ma or "").strip()
        l = (lang or "").strip().lower()[:2]
        if not m.startswith("vnb:") or l in _NN_CUA_VIENEU:
            return ""
        v, cb, tr = SO_DO_EN["vnb"], SO_DO_EN["cb"], SO_DO_EN["tran"]
        ng = SO_DO_NGAT
        return (
            f"LƯU Ý về giọng nhân bản này: nó chạy trên VieNeu (model TIẾNG "
            f"VIỆT). Đo 26/08/2026 trên 34 câu tiếng Anh, CÙNG một file mẫu, "
            f"chạy HAI LƯỢT: sai chữ cả bài {v['wer']} và tự bịa thêm chữ "
            f"{v['bia']} — tức có lượt HƠN CẢ giọng bản ngữ edge-tts "
            f"({tr['wer']} / {tr['bia']}), có lượt tệ hẳn. Nó KHÔNG ĐỀU chứ "
            f"không phải lúc nào cũng hỏng, nên câu nào nghe lạ thì chạy lại "
            f"video đó là thường hết.\n"
            f"NGHE RA LÀ \"ĐỌC RỜI RẠC, NHƯ ĐÁNH VẦN\" thì đó là thứ ĐO ĐƯỢC, "
            f"không phải cảm giác: đo 27/08/2026 trên chính tiếng máy đã đọc "
            f"ra, giọng này ngắt GIỮA CÂU {ng['en_vnb']} lần trên 100 ký tự "
            f"so với {ng['en_tran']} của giọng bản ngữ edge-tts đọc CÙNG bộ "
            f"câu — GẤP {ng['en_ty']} LẦN — và chỗ ngắt rất ngắn (trung vị "
            f"{v['ngat_tv']} so với {tr['ngat_tv']} của bản ngữ), tức nhiều "
            f"cú hụt hơi vụn chứ không phải ngắt nghỉ đúng chỗ. Cùng giọng, "
            f"cùng máy, ĐỌC TIẾNG VIỆT thì NGƯỢC LẠI: {ng['vi_vnb']} so với "
            f"{ng['vi_tran']} của bản ngữ = chỉ {ng['vi_ty']} lần. Đây là "
            f"chuyện model tiếng Việt đọc tiếng Anh, KHÔNG phải app đặt sai "
            f"gì cả, và KHÔNG chữa được bằng cách cắt bớt khoảng lặng (đã đo "
            f"cả hai chiều: làm vậy bẻ nhịp giọng bản ngữ nặng hơn).\n"
            f"Đổi sang giọng nhân bản Chatterbox KHÔNG chữa được: cùng mẫu ấy "
            f"nó sai chữ trong câu {cb['cau']} so với {v['cau']} của VieNeu, "
            f"lại bắt buộc GPU NVIDIA và đóng dấu chìm không tắt được.\n"
            f"Muốn CHẮC ĂN cho tiếng Anh thì chọn một giọng bản ngữ (edge-tts "
            f"en-US) — miễn phí và đo được {tr['wer']} sai chữ.")
    except Exception:                                          # noqa: BLE001
        return ""


#: Gói mà **ĐƯỜNG NHÂN BẢN** của VieNeu cần, ngoài những gì `co_vieneu()` đã dò.
#:
#: ═══ LỖI THẬT, ĐO ĐƯỢC 19/08/2026 — ĐỌC KỸ, ĐÂY LÀ LÝ DO HÀM NÀY TỒN TẠI ═══
#: `giong_vieneu.co_vieneu()` trả **True** trên máy này, 20 giọng dựng sẵn đọc
#: **3/3 câu** ngon lành. Nhưng chọn một giọng NHÂN BẢN thì `infer(ref_audio=)`
#: ném `ModuleNotFoundError: No module named 'torch'` -> `doc_loat` trả toàn
#: False -> app **lùi êm về edge-tts**. Tức anh Hùng chọn "giọng chị Lan" và
#: nghe ra giọng edge-tts, **không một dòng báo trên giao diện** (lý do chỉ nằm
#: trong `logs/giong_vieneu_<ngày>.log`). Đúng họ lỗi "chọn X ra Y".
#:
#: GỐC: VieNeu bản CPU chạy bằng **onnxruntime** cho giọng dựng sẵn — không cần
#: torch. Riêng đường NHÂN BẢN mới đụng torch. Nên phép dò "có VieNeu không"
#: đúng cho giọng dựng sẵn và **SAI cho nhân bản**; phải hỏi thêm.
#: Cài xong `torch` thì lộ tiếp `torchaudio` — nên danh sách này có HAI tên,
#: và dò từng tên chứ không dò một cái rồi suy ra.
#:
#: ═══ DANH SÁCH NÀY TỪNG THIẾU, VÀ ĐÂY LÀ CÁCH NÓ ĐƯỢC SỬA (20/08/2026) ═══
#: Anh Hùng tải xong 2,5 GB rồi **vẫn không đọc được**. Log máy anh ấy:
#:     [19:00:39] Cài phần nhân bản XONG vào ...\_giong_vieneu\venv
#:     [19:00:59] VieNeu đọc hỏng: ModuleNotFoundError: No module named 'transformers'
#: Ghi chú ở trên tự nói *"cài xong torch thì lộ tiếp torchaudio"* — tức người
#: viết ĐÃ BIẾT cơ chế lộ-dần mà vẫn dừng ở hai tên. Đó là **đoán, không phải
#: đo**.
#:
#: **VÌ SAO KHÔNG DÒ ĐƯỢC BẰNG PHÉP IMPORT** (đã đo, đừng thử lại): chạy
#: `python -c "import vieneu"` và `import vieneu.v3turbo` trên chính venv của
#: anh Hùng — **CẢ HAI THÀNH CÔNG** trong khi `transformers` đang thiếu. Gói nạp
#: `transformers` **LƯỜI**, chỉ khi đường nhân bản (`ref_audio=`) chạy. Nên phép
#: dò duy nhất nói thật là **ĐỌC THẬT**, y như luật `_kiem_wav` của cả repo:
#: bằng chứng phải là WAV CÓ TIẾNG, không phải "import được".
#:
#: Danh sách dưới đây lấy từ **CHÍNH METADATA của gói `vieneu`**
#: (`importlib.metadata.requires("vieneu")`), không phải trí nhớ. Bản khai đầy đủ
#: có 21 tên; ở đây **CỐ Ý bỏ** `gradio` (giao diện web), `lmdeploy` (máy chủ suy
#: luận), `llama-cpp-python` + `triton` + `triton-windows` (không build được trên
#: Windows), `PyMuPDF` (đọc PDF) — không thứ nào là phụ thuộc của một lượt ĐỌC
#: TIẾNG, và kéo chúng vào là lượt cài chắc chắn gãy.
#: `safetensors`/`einops` KHÔNG cần khai: pip tự kéo theo `transformers`.
#:
#: ═══ ĐO 20/08/2026: DANH SÁCH NÀY TỪNG DÀI QUÁ, VÀ ĐÓ LÀ BÁO ĐỘNG GIẢ ═══
#: Lượt trước thêm `transformers`, `neucodec`, `accelerate` vào đây, suy từ
#: `importlib.metadata.requires("vieneu")` (21 tên khai báo). **Suy luận đó
#: SAI**, và `_do_may_trang.py` đo ra bằng cách ĐỌC THẬT:
#:
#:   · `_giong_vieneu/venv` (vieneu 3.2.8): transformers · neucodec ·
#:     accelerate **ĐỀU KHÔNG CÓ** (`import` cả ba đều `ModuleNotFoundError`,
#:     không có thư mục lẫn `.dist-info`)
#:   · vậy mà đường NHÂN BẢN chạy **RA WAV CÓ TIẾNG**: 2,32 giây · RMS
#:     **0,09761** · 25,1 giây
#:
#: Tức chúng là **phụ thuộc KHAI BÁO của gói**, không phải phụ thuộc của một
#: lượt ĐỌC. Để chúng ở đây thì trên đúng cái máy nhân bản được, dòng combo ghi
#: *"CHƯA CHẠY ĐƯỢC"* và nút mời tải một lượt pip cho thứ KHÔNG CẦN — hồi ấy còn
#: là **2.485,6 MB** vì nút đi chỉ mục CUDA (máy anh Hùng có RTX 3060); nay nút
#: LUÔN đi bản CPU nên con số là **126,3 MB**, nhưng báo động giả vẫn là báo
#: động giả. Báo động giả đắt hơn im lặng.
#:
#: ⇒ Kết luận đúng: **danh sách TĨNH không nói thật được ở CẢ HAI CHIỀU** — nên
#: nó chỉ giữ **mức TỐI THIỂU ĐÃ ĐO là BẮT BUỘC**, còn phần "còn thiếu gì nữa"
#: là việc của **VÒNG TỰ DÒ** (`giong_vieneu.cai_nhan_ban` bước 3): nó ĐỌC THẬT,
#: bóc tên từ lời lỗi, cài đúng tên đó rồi thử lại. Thêm tên vào đây là quay lại
#: lối ĐOÁN.
#: ═══ `transformers` ĐÃ VÀO RA DANH SÁCH NÀY HAI LẦN — ĐỌC HẾT TRƯỚC KHI SỬA ═══
#: v2.42.2 gỡ `transformers`, lý do là một phép ĐO THẬT trên venv máy dev: ba gói
#: `transformers`/`neucodec`/`accelerate` **không có mặt** mà đường nhân bản
#: **vẫn ra WAV có tiếng** (2,32 s · RMS 0,09761). Rồi commit `f37e4a0` TRẢ LẠI,
#: vì log máy anh Hùng SAU KHI cập nhật v2.42.2 (21:25-21:26) có thật:
#:     VieNeu đọc hỏng: ModuleNotFoundError: No module named 'transformers'
#: lặp **5 lượt liền**.
#:
#: **HAI PHÉP ĐO ĐÓ KHÔNG ĐÁ NHAU — chúng chạy trên HAI BẢN TORCH KHÁC NHAU.**
#: Đó là mảnh còn thiếu, và nay đã đo được trên chính máy anh Hùng: lượt 21:25
#: chạy trên torch/torchaudio bản **`+cu126`** mà `cai_nhan_ban()` tự chọn (nó
#: hỏi `co_gpu_nvidia()`, máy có RTX 3060 -> True -> chỉ mục `cu126`). Đường
#: nhân bản chỉ chạy được sau khi anh ấy **GỠ TAY** torch về bản **CPU**, và ở
#: bản CPU thì nó cần **ĐÚNG `torch` + `torchaudio`** — `transformers` KHÔNG
#: CẦN. Xem `giong_vieneu.ban_cuda_se_tai()` để biết đủ 4 bước chuỗi lỗi (ngắn
#: gọn: torchaudio+cu126 nạp audio qua `torchcodec`, `torchcodec` đòi FFmpeg
#: dạng DLL chia sẻ mà app chỉ đóng gói `ffmpeg.exe` TĨNH).
#: ⇒ `giong_vieneu` nay **LUÔN** cài bản CPU, nên môi trường sinh ra lời lỗi
#: `transformers` không còn được dựng ra nữa. Danh sách này về đúng mức ĐÃ ĐO.
#: `transformers` đồng thời vào danh sách CHẶN của vòng tự dò
#: (`giong_vieneu._CHAN_TU_DO`) — nếu không thì vòng đó tự cài lại nó.
#:
#: ═══ LUẬT BẤT ĐỐI XỨNG — VẪN CÒN HIỆU LỰC, ĐỪNG ĐỌC MỤC TRÊN THÀNH "ĐÃ BỎ" ═══
#: HẬU QUẢ CỦA VIỆC KÊ THIẾU nặng hơn hẳn việc kê thừa:
#: `thieu` rỗng -> nhãn ghi "đã đủ phần cần thiết" -> **NÚT TẢI ẨN ĐI**
#: (`thay_giong_dialog._do_nhan_ban`: `if not thieu: b_tai_nb.setVisible(False)`)
#: -> mà vòng tự dò lại nằm TRONG `cai_nhan_ban()` (thân cái nút đó) -> **không
#: còn đường nào chạy tới nó**. Đó là mặt LẬT NGƯỢC của luật "nút bám `thieu`":
#: bám `thieu` chỉ an toàn khi `thieu` không bao giờ BỎ SÓT.
#:   · để THỪA một tên  -> nút hiện thừa, mời tải thứ có thể không cần. Dở, nhưng
#:     người dùng vẫn đi tới đích được -> CHỮA ĐƯỢC.
#:   · để THIẾU một tên -> nút biến mất, tính năng CHẾT, không có đường sửa từ
#:     giao diện -> KHÔNG CHỮA ĐƯỢC.
#: Hai cái đó KHÔNG ngang nhau. Khi chưa biết chắc thì **nghiêng về để thừa**.
#:
#: **LƯỢT NÀY LÀM `thieu` RỖNG TRÊN MÁY DEV — ĐO ĐƯỢC, VÀ ĐÂY LÀ LÝ LẼ:**
#: `_giong_vieneu/venv` của repo CÓ `torch 2.13.0+cpu` + `torchaudio 2.11.0+cpu`
#: nên `thieu_de_nhan_ban()` đi từ `['transformers']` -> `[]`, tức nút tải ẨN
#: trên máy dev. Điều đó **không** phải hồi quy v2.42.2, vì v2.42.2 hại ở chỗ
#: hai điều CÙNG đúng: (a) `thieu` rỗng **VÀ** (b) đường nhân bản THẬT SỰ hỏng.
#: Ở đây (b) đã đo là SAI trên chính cấu hình này (WAV 2,32 s · RMS 0,09761 với
#: torch bản CPU và KHÔNG có transformers) -> ẩn nút là nói THẬT, không phải
#: giấu bệnh. Nhưng cái **LỖ CẤU TRÚC thì vẫn còn nguyên và lượt này KHÔNG vá**:
#: cửa duy nhất vào vòng tự dò vẫn là cái nút ấy, nên một máy có đủ
#: torch+torchaudio mà đọc vẫn gãy vì gói THỨ BA nào đó sẽ lại không có đường
#: sửa từ giao diện. Việc đáng làm tiếp (chưa làm, chưa đo): cho
#: `thieu_de_nhan_ban()` báo cả ca **torch/torchaudio LỆCH CÂY `+cu126`** (đọc
#: `<gói>/version.py` bằng FILE, khuôn `giong_hang._ban_trong_version_py`) — đó
#: đúng là trạng thái làm chết đường nhân bản mà nút này sửa được, và nó KHÔNG
#: phải một tên gói đoán bừa.
#:
#: Chữa tận gốc vẫn là **vòng tự dò** (đọc thật -> bóc tên gói thiếu -> cài ->
#: thử lại), vì danh sách tĩnh đã chứng minh nói sai ở CẢ HAI CHIỀU. Nhưng vòng
#: đó chỉ chạy khi NÚT CÒN HIỆN — nên danh sách này là điều kiện để nó sống,
#: không phải thứ thay nó.
_CAN_CHO_NHAN_BAN = ("torch", "torchaudio")

#: Trần độ dài MỘT DÒNG COMBO giọng. **KHÔNG phải số đặt cho đẹp** — cổng 88 mục
#: 8d chấm đúng con số này, và nó có gốc: nhãn Kokoro 139-178 ký tự đã bị cắt
#: **đúng chỗ cụm "cần tải"** trên máy anh Hùng (20/08/2026), tức phần bị mất là
#: phần quan trọng nhất. Đặt 130 (dưới trần cổng 132) để còn biên.
#: Sửa số này thì phải sửa cả mục 8d và nói rõ lý do — đừng nới cho hết đỏ.
TRAN_NHAN = 130


def thieu_de_nhan_ban(may: str) -> list[str]:
    """Còn thiếu gói nào thì đường NHÂN BẢN của ``may`` mới chạy được.

    Dò bằng **FILE CÓ TỒN TẠI KHÔNG** trong ``site-packages`` của đúng python
    đó, KHÔNG bằng ``find_spec`` — ``find_spec`` tìm trên ``sys.path`` của
    tiến trình ĐANG chạy nên nó sẽ "thấy" torch của ``.venv`` rồi báo đủ,
    trong khi python của VieNeu không có (đúng bài học cổng 58: máy dev xanh,
    máy thật đỏ). **KHÔNG BAO GIỜ NÉM.**
    """
    try:
        if may == MAY_CHATTER:
            from app.core import giong_chatter
            return list(giong_chatter.tinh_trang()["thieu"])
        if may != MAY_VIENEU:
            return ["máy nhân bản không rõ"]
        from app.core import giong_vieneu
        tt = giong_vieneu.tinh_trang_vieneu()
        if not tt.get("co"):
            return list(tt.get("thieu") or ["VieNeu"])
        py = Path(str(tt.get("python") or ""))
        if not py.exists():
            return ["VieNeu"]
        goc = py.parent.parent
        sp = [goc / "Lib" / "site-packages", goc / "lib" / "site-packages"]
        sp = [d for d in sp if d.is_dir()]
        if not sp:
            return ["VieNeu"]
        return [g for g in _CAN_CHO_NHAN_BAN
                if not any((d / g / "__init__.py").exists() for d in sp)]
    except Exception:                                          # noqa: BLE001
        return ["không dò được"]


def may_chay_duoc(may: str) -> bool:
    """Đường **NHÂN BẢN** của máy này chạy được không. KHÔNG BAO GIỜ NÉM.

    Cố ý hỏi *"nhân bản chạy được không"* chứ không phải *"máy đọc có không"*:
    hai câu đó khác nhau với VieNeu, và trả lời nhầm câu là nhãn báo "dùng
    được" cho một giọng sẽ lặng lẽ ra giọng khác. Xem ``_CAN_CHO_NHAN_BAN``.
    """
    try:
        if may == MAY_VIENEU:
            from app.core import giong_vieneu
            if not giong_vieneu.co_vieneu():
                return False
            return not thieu_de_nhan_ban(MAY_VIENEU)
        if may == MAY_CHATTER:
            from app.core import giong_chatter
            return bool(giong_chatter.co_chatter())
    except Exception:                                          # noqa: BLE001
        return False
    return False


def ma_giong(ten: str) -> str:
    """Mã giọng để đưa vào combo / lưu vào cấu hình kênh. "" nếu không có.

    Trả **mã NGUYÊN BẢN của máy** (``vnb:``/``cb:``) chứ không đẻ tiền tố thứ
    ba: ``giong_bang.nguon()`` đã biết ``vnb:``, thêm một quy ước nữa là thêm
    một chỗ để quên (đúng lỗi ``vieneu:`` vs ``vn:`` đã sập ở ``24a3bcf``).
    """
    g = _muc(_doc_so(), ten)
    if not g:
        return ""
    mau = str(g.get("mau") or "")
    if not mau or not Path(mau).exists():
        return ""
    return _ma_tu_muc(g)


def _ma_tu_muc(g: dict) -> str:
    """Mã giọng của MỘT MỤC SỔ, **không hỏi file mẫu còn không**.

    Tách ra khỏi ``ma_giong`` vì hai người gọi cần hai câu trả lời khác nhau:
    ``ma_giong`` (đưa vào combo / lưu cấu hình kênh) **phải** trả "" khi mẫu
    mất — gán một giọng không đọc nổi cho kênh là 300 video ra tiếng sai; còn
    ``_dong_that`` chỉ cần biết **mã thuộc NGUỒN nào** để đo độ dài dòng, và ca
    mất-file-mẫu chính là ca dòng DÀI NHẤT (có thêm " - MẤT FILE MẪU").
    Trả "" ở đó thì ``giong_bang.nguon("")`` lùi về edge-tts -> đuôi ngắn hơn
    -> **đo hụt đúng ca xấu nhất**.
    """
    mau = str(g.get("mau") or "")
    if g.get("may") == MAY_CHATTER:
        from app.core import giong_chatter
        return giong_chatter.ma_nhan_ban(mau, str(g.get("lang") or "en"))
    from app.core import giong_vieneu
    return giong_vieneu.ma_nhan_ban(mau)


def _dong_that(g: dict, nh: str) -> str:
    """Dòng combo THẬT mà người dùng đọc thấy, để ``nhan()`` tự đo mình.

    ``giong_bang.gom_nhom`` dán thêm 4 đuôi vào nhãn này, nên nhãn thô **không
    phải** thứ phải so với trần. Gọi CHUNG ``giong_bang.dong_day_du`` — đúng
    hàm ``gom_nhom`` dùng — nên không có bản sao nào để lệch.

    **KHÔNG BAO GIỜ NÉM**: đây là đường dựng NHÃN, và một combo trống một dòng
    còn tệ hơn một nhãn hơi dài. Hỏng thì trả nguyên nhãn vào (đo hụt phần đuôi
    = nghiêng về GIỮ tên gói đích danh, tức nghiêng về nói thật).
    """
    try:
        from app.core import giong_bang
        return giong_bang.dong_day_du(_ma_tu_muc(g), nh)
    except Exception:                                          # noqa: BLE001
        return nh


def them_giong(ten: str, duong_mau_goc: str, lang: str = "vi",
               may: str = "", nguon: str = "") -> dict:
    """Thêm một giọng nhân bản vào sổ. Trả ``{"ok","ma","loi","canh_bao"}``.

    ``nguon`` = anh Hùng tự khai mẫu ở đâu ra (*"giọng của tôi"* / *"nhân viên
    đã đồng ý"* / ...). App không kiểm được, nhưng GHI LẠI thì sau này có
    chuyện còn tra được — xem ``CANH_BAO_PHAP_LY``.

    **CHÉP MẪU VÀO DATA_DIR** (chuẩn hoá 24 kHz mono wav): người dùng xoá/di
    chuyển file gốc thì giọng vẫn chạy.
    """
    ra = {"ok": False, "ma": "", "loi": "", "canh_bao": []}
    ten = str(ten or "").strip()
    if not ten:
        ra["loi"] = "Chưa đặt tên cho giọng"
        return ra
    so = _doc_so()
    if ten in so:
        ra["loi"] = f"Đã có giọng tên «{ten}» - đặt tên khác hoặc xoá cái cũ"
        return ra
    # KIỂM MÁY + NGÔN NGỮ **TRƯỚC** KIỂM MẪU — cố ý, cổng 81 CA 7e bắt được.
    # Bản đầu kiểm mẫu trước, nên chọn nhầm máy cho tiếng Việt mà file mẫu lại
    # hỏng thì người dùng chỉ nhận lời báo về FILE, sửa file xong mới gặp lời
    # báo thật. Lỗi nào CHẮC CHẮN chặn thì báo trước, và đây là phép kiểm
    # KHÔNG tốn gì (một phép tra bảng, không đọc đĩa).
    may = (may or "").strip() or goi_y_may(lang)
    if may == MAY_CHATTER:
        from app.core import giong_chatter
        if (lang or "").strip().lower()[:2] not in giong_chatter.TIENG:
            ra["loi"] = (f"Chatterbox không đọc được tiếng «{lang}» "
                         f"(nó có 23 thứ tiếng, KHÔNG có tiếng Việt)")
            return ra
    kt = kiem_mau(duong_mau_goc)
    ra["canh_bao"] = list(kt.get("canh_bao") or [])
    if not kt.get("ok"):
        ra["loi"] = kt.get("loi") or "Mẫu không dùng được"
        return ra
    try:
        d = thu_muc_mau()
        d.mkdir(parents=True, exist_ok=True)
        # MỘT BẢN GHI = MỘT FILE MẪU RIÊNG. Đặt thẳng `f"{_slug(ten)}.wav"` thì
        # hai tên khác nhau có thể ra cùng tên file -> ffmpeg `-y` ghi đè mẫu
        # của giọng cũ VÀ hai giọng ra cùng một mã. Xem `_ten_mau_trong`.
        dich = _ten_mau_trong(ten, so)
        # 24 kHz mono: đúng tần số cả hai máy nhân bản dùng, nên không phải
        # đổi lại lúc đọc. KHÔNG chép nguyên file gốc — mp3/m4a/video đều có
        # thể là mẫu, mà hai máy chỉ nhận wav.
        r = subprocess.run(
            [_ffmpeg(), "-y", "-v", "error", "-i", str(duong_mau_goc),
             "-vn", "-ac", "1", "-ar", "24000", str(dich)],
            capture_output=True, creationflags=_NO_WIN, timeout=600)
        # BẪY: ffmpeg mã 0 + file 0 KiB. Kiểm KÍCH THƯỚC, đừng tin mã thoát.
        if r.returncode != 0 or not dich.exists() or dich.stat().st_size < 4000:
            ra["loi"] = "Không chuyển được mẫu sang dạng app dùng được"
            return ra
    except Exception as e:                                     # noqa: BLE001
        ra["loi"] = f"Không chép được mẫu: {type(e).__name__}"
        return ra
    so[ten] = {"mau": str(dich), "may": may,
               "lang": (lang or "vi").strip().lower()[:2],
               "nguon": str(nguon or ""), "goc": str(duong_mau_goc),
               "giay": kt.get("giay", 0.0),
               "tao_luc": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not _ghi_so(so):
        ra["loi"] = "Không ghi được sổ giọng"
        return ra
    ra["ok"] = True
    ra["ma"] = ma_giong(ten)
    return ra


def danh_sach(chi_chay_duoc: bool = False) -> list[tuple[str, str]]:
    """``[(mã, nhãn)]`` để đổ vào combo. Nhãn TIẾNG VIỆT, KHÔNG EMOJI.

    ``chi_chay_duoc=True``: bỏ giọng mà máy này chưa cài được máy nhân bản.
    Mặc định VẪN HIỆN kèm chữ "CHƯA CÀI" — đúng tiền lệ Piper/VieNeu: giấu đi
    thì người dùng không bao giờ biết là có, hiện ra kèm lý do thì họ biết
    phải bấm gì. Điều kiện để việc đó không thành bẫy "chọn X ra Y" là lượt
    đọc phải NÓI RA khi nó lùi — ``giong_chatter.doc_loat`` ghi log rồi lùi.
    """
    ra: list[tuple[str, str]] = []
    so = _doc_so()
    # SỔ CŨ CÓ THỂ ĐANG VI PHẠM BẤT BIẾN "một bản ghi = một file mẫu" (sổ chép
    # tay, sổ do bản app trước ghi đè mẫu). Chữa NGAY TẠI ĐÂY vì đây đúng là
    # chỗ mã trùng gây hại: combo nuốt mất một dòng, và mã ấy tra ngược ra SAI
    # TÊN. Sổ lành thì `sua_mau_trung` chỉ là một phép so tập hợp rồi trả `[]`
    # — KHÔNG đọc thêm đĩa, KHÔNG ghi gì, nên đường vẽ combo không chậm đi.
    if sua_mau_trung(so):
        so = _doc_so()                       # vừa chữa -> đọc lại bản đã sửa
    for ten in sorted(so):
        # `_muc` chứ không `so[ten]`: MỘT mục hỏng không được phép giết cả
        # danh sách (xem `_muc`). Mục hỏng thì `ma_giong` trả "" -> bỏ qua.
        g = _muc(so, ten)
        ma = ma_giong(ten)
        if not ma:
            continue
        chay = may_chay_duoc(str(g.get("may") or ""))
        if chi_chay_duoc and not chay:
            continue
        ra.append((ma, nhan(ten)))
    return ra


def nhan(ten: str) -> str:
    """Nhãn một dòng cho giọng đã nhân bản. TIẾNG VIỆT, KHÔNG EMOJI."""
    g = _muc(_doc_so(), ten)
    if not g:
        return str(ten or "")
    may = str(g.get("may") or "")
    ten_may = "VieNeu" if may == MAY_VIENEU else "Chatterbox"
    # Nói ĐÍCH DANH còn thiếu gì, đừng ghi "chưa cài" trơn — người dùng không
    # biết bấm gì (bài học cổng 58: hộp Demucs phải nêu tên từng gói).
    # NÊU 2 TÊN RỒI THÔI, KHÔNG NÊU 3. Danh sách gói tăng từ 2 lên 5 tên
    # (20/08/2026, sau khi log máy anh Hùng lộ ra `transformers`) làm nhãn phình
    # lên **156 ký tự** — vượt trần 132 mà **cổng 88 mục 8d bắt được**. Đó đúng
    # cái bẫy đã đẩy mất cảnh báo "cần tải" của Kokoro sáng nay: nhãn dài thì
    # phần bị cắt là phần QUAN TRỌNG NHẤT.
    # Cụm "CHƯA CHẠY ĐƯỢC" phải còn — đó là thứ anh Hùng cần thấy; danh sách gói
    # ĐẦY ĐỦ đã có ở nhãn riêng trong hộp «Giọng của tôi» và ở nút tải.
    # Đo thật: liệt kê 3 tên -> **156 ký tự**, 2 tên + "..." -> **147**, vẫn vượt
    # trần 132. Tên gói (`transformers`, `accelerate`, `neucodec`) quá dài để
    # nằm trên MỘT DÒNG COMBO. Nên dòng này chỉ mang **SỐ LƯỢNG** + cụm
    # "CHƯA CHẠY ĐƯỢC"; **danh sách ĐÍCH DANH nằm ở nhãn trong hộp «Giọng của
    # tôi» và trên nút tải** — chỗ có đủ chiều rộng.
    # Luật "nêu đích danh gói thiếu" (cổng 58) vẫn được giữ, chỉ chuyển sang chỗ
    # ĐỌC ĐƯỢC. Nhồi nó vào dòng combo là cắt mất chính cụm cảnh báo — đúng lỗi
    # Kokoro sáng nay.
    _t = thieu_de_nhan_ban(may)
    mat = "" if Path(str(g.get("mau") or "")).exists() else " - MẤT FILE MẪU"
    # Tách `tên` khỏi `phần sau` để `_vua_tran` biết cắt vào đâu khi dòng dài.
    sau = (f" (giọng nhân bản, {ten_may}, "
           f"mẫu {_so_giay(g):.0f} giây){mat}")
    if may == MAY_CHATTER:
        # ═══ CHATTERBOX PHẢI TỰ MANG CẢNH BÁO, KHÔNG MƯỢN ĐUÔI ═══
        # Đo trước khi vá (21/08/2026): dòng cb: **143 ký tự**, vượt trần 130,
        # tức đúng cái bẫy Kokoro (nhãn 139-178 bị cắt mất cụm "cần tải").
        # Và nó vượt ở **nhánh KHÔNG thiếu gói** — nhánh duy nhất trước đây
        # không hề đo mình, nên trần nằm đó mà không bao giờ bập được.
        #
        # 89 ký tự đuôi ấy còn THIẾU đúng thứ anh Hùng cần nhất: nó không nhắc
        # một chữ nào về **ĐÓNG DẤU CHÌM**, mà anh ấy BÁN video ra.
        # `giong_chatter.canh_bao_gon()` nói đủ bốn vế trong 70 ký tự và mang
        # sẵn ba chữ `mit` / `cần tải` / `GPU` mà `giong_bang._DO_TRUNG
        # [CHATTER]` dò — nên `duoi_dong` tự thôi dán đuôi cũ. Đổi được vế
        # đóng dấu chìm lấy chỗ, mà **không đụng một dòng nào của
        # `giong_bang.py`** (file đó đang do luồng khác giữ).
        #
        # NGÔN NGỮ nằm NGAY TRONG nhãn vì đây là bộ **KHÔNG CÓ TIẾNG VIỆT**:
        # người dùng phải thấy "giọng này đọc tiếng gì" TRƯỚC khi gán cho kênh.
        #
        # **VIẾT ĐÚNG CỤM `"chỉ đọc tiếng"`, ĐỪNG RÚT THÀNH `"tiếng"`** — đó là
        # một trong 5 chuỗi `giong_bang.duoi_da_ngu` dò để **thôi dán** đuôi
        # `" - chỉ tiếng Anh"` (16 ký tự nói lại đúng điều nhãn vừa nói). Rút
        # ngắn cụm này là dòng phồng thêm 16 ký tự cho 0 thông tin.
        from app.core import giong_chatter as _gc
        tieng = _gc.TIENG.get(str(g.get("lang") or "").strip().lower()[:2], "?")
        sau = (f" (nhân bản Chatterbox, chỉ đọc tiếng {tieng})"
               f"{mat} - {_gc.canh_bao_gon()}")
    if not _t:
        # ĐO CẢ NHÁNH NÀY — bản cũ chỉ đo nhánh "còn thiếu gói", nên dòng
        # Chatterbox **143 ký tự** đi lọt suốt (đo 21/08/2026).
        return _vua_tran(g, "", ten, sau)

    # ═══ HAI MỤC CỔNG **KHÔNG** XUNG ĐỘT — LƯỢT TRƯỚC ĐO SAI CHUỖI ═══
    # Cổng 88 mục **7c** đòi nhãn *"nói ĐÍCH DANH gói thiếu"* (bài học cổng 58);
    # mục **8d** đòi dòng *"dưới 132 ký tự"* (bài học Kokoro: nhãn 139-178 ký tự
    # **đẩy mất** chính cụm cảnh báo). Lượt trước kết luận hai mục đó xung đột
    # và "hoà" bằng cách tụt về đếm số. **KẾT LUẬN ĐÓ SAI**, và đây là vì sao:
    #
    # `nhan()` đo **CHUỖI CỦA CHÍNH NÓ** (110 ký tự, dưới trần 130 -> giữ đủ
    # tên), nhưng dòng người dùng THẤY là dòng SAU `giong_bang.gom_nhom`, và
    # `gom_nhom` dán thêm **46 ký tự** đuôi -> **156**. Hai chỗ đo HAI CHUỖI
    # KHÁC NHAU, nên cái trần trong hàm này **không bao giờ bập được** và mục
    # 8d cứ đỏ dù hàm này "đã có nhánh tụt về đếm".
    # 46 ký tự đó là `" - chưa đo tiếng"` + `" · miễn phí, cần tải bộ 250 MB"`,
    # mà cụm sau còn là **SỐ SAI**: 250 MB là bộ giọng VieNeu (máy đã phải có
    # sẵn), còn thứ đang thiếu là phần nhân bản 126,3 MB / 2.485,6 MB. Đã vá ở
    # `giong_bang._DO_TRUNG[VIENEU]` (thêm `"chưa chạy được"`).
    #
    # Nay đo **ĐÚNG DÒNG NGƯỜI DÙNG ĐỌC** qua `giong_bang.dong_day_du` — cùng
    # một phép dựng mà `gom_nhom` dùng, nên hai bên không thể lệch nhau nữa.
    # Đo lại sau khi vá: 3 tên -> **126 ký tự**, DƯỚI trần. Tức **cả 7c lẫn 8d
    # cùng đúng**, và không mục nào phải nhường.
    # Nhánh tụt-về-đếm VẪN GIỮ: tên giọng do người dùng tự đặt nên vẫn có thể
    # dài (200-300 kênh, ai đặt tên dài thì dòng vẫn phải vừa). Với danh sách 3
    # gói hiện tại thì dòng ĐI ĐÚNG nhánh này — nên **danh sách đích danh phải
    # có ở nhãn hộp «Giọng của tôi» và trên nút tải**, chỗ đủ rộng.
    # **ĐỪNG đổi thành một trong hai vế cố định** — làm thế là bỏ một mục cổng.
    #
    # ═══ "miễn phí, cần tải" LÀ HAI BẤT BIẾN CỔNG 79, KHÔNG PHẢI CHỮ CHO ĐẸP ═══
    # Cổng 79 CA 6 đòi **mọi dòng** nói được TIỀN (một trong: miễn phí · tốn ·
    # tính tiền · cần key · hạn mức) và **mọi giọng phải-tải** nói ra việc TẢI.
    # Trước đây dòng này mượn đuôi `duoi_dong` để nói hộ hai điều đó — nhưng đuôi
    # ấy ghi *"cần tải bộ 250 MB"*, tức **SAI THỨ PHẢI TẢI**: 250 MB là bộ giọng
    # VieNeu (máy phải có sẵn mới tạo nổi giọng nhân bản), còn thứ đang thiếu là
    # phần nhân bản **126,3 MB bản CPU / 2.485,6 MB bản CUDA**. Đúng lớp lỗi
    # cổng 58 ("nút ghi 155 MB rồi hộp doạ 2 GB").
    # Nay dòng TỰ nói cả hai bằng chữ ĐÚNG. Nhờ chữ "cần tải" mà
    # `giong_bang._DO_TRUNG[VIENEU]` làm `duoi_dong` tự thôi dán đuôi cũ — vừa
    # hết nói sai, vừa trả lại 30 ký tự. **BỎ "miễn phí" hay "cần tải" khỏi câu
    # này là cổng 79 ĐỎ NGAY** (đã đo: 91 · 2).
    dau = f"CHƯA CHẠY ĐƯỢC (miễn phí, cần tải {', '.join(_t)}) - "
    if len(_dong_that(g, dau + ten + sau)) <= TRAN_NHAN:
        return dau + ten + sau
    return _vua_tran(
        g, f"CHƯA CHẠY ĐƯỢC (miễn phí, cần tải {len(_t)} gói) - ", ten, sau)


def _vua_tran(g: dict, truoc: str, ten: str, sau: str) -> str:
    """Ghép ``truoc + ten + sau`` sao cho DÒNG COMBO vừa ``TRAN_NHAN``, bằng
    cách **CẮT TÊN GIỌNG** chứ không cắt cảnh báo. Vừa sẵn -> trả NGUYÊN VĂN,
    không đụng một ký tự nào (bất biến: nhãn đang vừa thì KHÔNG đổi).

    ═══ VÌ SAO CẮT TÊN CHỨ KHÔNG CẮT CẢNH BÁO ═══
    Trần này sinh ra từ một lỗi THẬT: nhãn Kokoro 139-178 ký tự bị combo cắt
    **đúng chỗ cụm "cần tải"**, tức thứ bị mất là thứ quan trọng nhất. Nên khi
    buộc phải bỏ bớt, phải bỏ theo đúng thứ tự ngược lại: **tên giọng là thứ
    hy sinh được** (người dùng vẫn nhận ra qua phần đầu, và tooltip/hộp
    «Giọng của tôi» vẫn có tên đủ), còn *"cần tải"* / *"BẮT BUỘC GPU"* /
    *"ĐÓNG DẤU CHÌM"* thì không.

    Nhờ vậy trần trở thành **bất biến ĐÚNG VỚI MỌI TÊN** — kể cả tên 200 ký tự
    anh Hùng tự gõ — chứ không phải một lời hứa chỉ đúng với tên ngắn. Đó là
    thứ cổng chấm được.

    Đo phần thừa rồi cắt đúng phần đó (không dò từng ký tự): ``_dong_that``
    gọi cả ``nhan_nha`` lẫn ``da_ngu``, dò tuyến tính trên 300 kênh là đường
    làm đơ lượt vẽ combo. Vòng lặp chỉ để chốt lại vì đuôi có thể đổi độ dài
    khi nhãn đổi.

    **KHÔNG BAO GIỜ NÉM** — đây là đường dựng NHÃN; một combo trống một dòng
    còn tệ hơn một dòng hơi dài.
    """
    try:
        t, s = str(ten or ""), str(sau or "")
        for _ in range(6):
            thua = len(_dong_that(g, truoc + t + s)) - TRAN_NHAN
            if thua <= 0:
                return truoc + t + s
            k = len(t) - thua - 1          # `+1` chừa chỗ cho dấu `…`
            # Cắt tới mức không còn nhận ra tên thì THÔI — thà một dòng hơi dài
            # còn hơn một dòng không biết là giọng nào.
            if k < 4:
                return truoc + t + s
            t = t[:k].rstrip() + "…"
        return truoc + t + s
    except Exception:                                          # noqa: BLE001
        return f"{truoc}{ten}{sau}"


def xoa(ten: str, xoa_ca_mau: bool = True) -> bool:
    """Bỏ một giọng khỏi sổ. Trả True nếu sổ đổi.

    ═══ XOÁ FILE MẪU ĐI QUA ``xoa_an_toan``, KHÔNG TỰ CANH ═══
    Bản đầu tự canh ``goc in p.parents`` — đúng, nhưng đó là **cửa thứ 6** của
    đúng cái lớp bệnh mà ``app/core/xoa_an_toan.py`` sinh ra để chặn: một mục
    sổ hỏng (``mau`` = ``""``) cho ra ``Path("")`` = ``WindowsPath('.')``, thứ
    đã **xoá sạch cả cây mã** một lần (19/08/2026). Vá lẻ từng chỗ là bỏ sót
    chỗ thứ 7 người sau thêm vào, nên đi cửa chung — nó có đủ BỐN chốt
    (rỗng · thư mục đang làm việc + cha · gốc ổ đĩa · ``trong=``) thay vì một.

    ``an_toan_de_xoa`` là hàm THUẦN và **không hỏi ``is_dir``** nên dùng được
    cho FILE; ``don_thu_muc`` thì không (nó chỉ xoá thư mục).

    ``xoa_ca_mau=False`` để bỏ giọng khỏi sổ mà GIỮ mẫu — dùng khi người dùng
    chỉ muốn ẩn giọng đi.
    """
    so = _doc_so()
    ten = str(ten or "").strip()
    if ten not in so:
        return False
    mau = str(_muc(so, ten).get("mau") or "")
    so.pop(ten, None)
    ok = _ghi_so(so)
    if ok and xoa_ca_mau and mau:
        try:
            from app.core.xoa_an_toan import an_toan_de_xoa
            p = Path(mau)
            # `so` đã bỏ `ten` ở trên, nên vòng này chỉ hỏi NHỮNG BẢN GHI CÒN
            # LẠI. Sổ cũ có thể còn ca hai bản ghi dùng chung một mẫu (xem
            # `sua_mau_trung`); xoá file lúc đó là bản ghi kia MẤT MẪU, biến
            # khỏi combo mà không một dòng báo — đo được ở `_do_ma_trung.py`.
            con_dung = [t for t in so
                        if _khoa_mau(_muc(so, t).get("mau")) == _khoa_mau(mau)]
            if con_dung:
                _ghi_log(f"GIỮ file mẫu {p.name!r} — giọng {con_dung} vẫn đang "
                         f"dùng chung nó (giọng «{ten}» đã khỏi sổ)")
            elif not an_toan_de_xoa(p, trong=thu_muc_mau()):
                _ghi_log(f"TỪ CHỐI xoá mẫu {mau!r} — nằm ngoài "
                         f"{thu_muc_mau()} (giọng «{ten}» vẫn đã khỏi sổ)")
            elif p.is_file():
                os.remove(p)
        except Exception:                                      # noqa: BLE001
            pass
    return ok


def doi_ten(cu: str, moi: str) -> bool:
    """Đổi tên hiển thị. **KHÔNG đụng file mẫu** nên mã giọng không đổi ->
    cấu hình kênh đang trỏ vào giọng đó vẫn đúng."""
    so = _doc_so()
    cu, moi = str(cu or "").strip(), str(moi or "").strip()
    if cu not in so or not moi or moi in so:
        return False
    so[moi] = so.pop(cu)
    return _ghi_so(so)


def sua_mau_mat() -> list[str]:
    """Tên các giọng có file mẫu đã BIẾN MẤT. Chỉ BÁO, không tự xoá.

    Tự xoá là mất luôn cấu hình kênh đang trỏ vào nó, mà file mẫu có thể chỉ
    tạm không thấy (ổ ngoài chưa cắm). Cùng luật ``_canh_bao_mau_mat`` của
    mẫu-theo-kênh: BÁO, để người dùng quyết.
    """
    so = _doc_so()
    ra: list[str] = []
    for t in so:
        mau = str(_muc(so, t).get("mau") or "")
        # `Path("")` là `WindowsPath('.')` và `.exists()` ra **True** -> mục
        # hỏng (thiếu khoá `mau`) sẽ bị coi là "mẫu còn nguyên". Phải hỏi
        # chuỗi RỖNG trước, đừng để `Path` trả lời hộ.
        if not mau or not Path(mau).exists():
            ra.append(t)
    return ra


def la_giong_nhan_ban(ma: str) -> bool:
    """Mã này có phải giọng nhân bản (của bất kỳ máy nào) không."""
    s = str(ma or "")
    try:
        from app.core import giong_chatter, giong_vieneu
        return (giong_vieneu.la_giong_nhan_ban(s)
                or giong_chatter.la_giong_chatter(s))
    except Exception:                                          # noqa: BLE001
        return s.startswith(("vnb:", "cb:"))


def ten_theo_ma(ma: str) -> str:
    """Mã giọng -> tên tiếng Việt anh Hùng đã đặt. "" nếu không có trong sổ."""
    for ten in _doc_so():
        if ma_giong(ten) == str(ma or ""):
            return ten
    return ""
