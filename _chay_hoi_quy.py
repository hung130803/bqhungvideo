# -*- coding: utf-8 -*-
"""CHẠY CẢ LƯỢT HỒI QUY, IN **MÃ THOÁT THẬT** CỦA TỪNG CỔNG.

BA CÁI BẪY FILE NÀY CỐ Ý TRÁNH (đều đã sập ít nhất một lần trong repo):
 1. **Nối `| tail` là NUỐT MÃ THOÁT** — mã thoát thấy được sẽ là của `tail`.
    Đây gọi `subprocess.run` rồi in `returncode` nguyên vẹn.
 2. **cp1252**: chạy hồi quy mà đổ ra file thì `print` tiếng Việt nổ
    `UnicodeEncodeError` -> cổng chết trong 0-1 giây, chạy tay lại xanh. Ép
    `PYTHONIOENCODING=utf-8` cho MỌI tiến trình con.
 3. **"xanh" vì chạy chưa tới chốt**: cổng chết sớm cũng có thể rc=0 nếu nó
    thoát trước phần kiểm. Nên in kèm **thời gian chạy** và **dòng tổng kết
    ĐẠT/HỎNG** dò được — rc=0 mà 0 giây / không có dòng tổng kết là ĐÁNG NGỜ.

    .venv\\Scripts\\python -u _chay_hoi_quy.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
# `line_buffering=True` LÀ BẮT BUỘC, KHÔNG PHẢI CHO GỌN — **`reconfigure()` XOÁ
# MẤT TÁC DỤNG CỦA `python -u`.** `-u` bật `write_through` cho lớp chữ; gọi
# `reconfigure(encoding=...)` mà không nói gì về đệm là dựng lại lớp chữ với
# `write_through=False`, tức stdout quay về **ĐỆM THEO KHỐI** khi đổ ra file.
# ĐO ĐƯỢC (19/08/2026, lượt hồi quy v2.40.0): `_kq_hq/` đã có **12 cổng** chạy
# xong mà file `> HOIQUY.txt` mới chỉ có **4 dòng**. Hệ quả đúng bằng cái bẫy
# chính file này ra đời để chống (bẫy số 3 ở docstring): lượt chạy bị giết giữa
# chừng — đã xảy ra 3 lần trong MỘT phiên — thì **mất sạch** báo cáo, và người
# đọc không phân biệt được "cổng đang chạy" với "cổng đã chết". Log từng cổng
# trong `_kq_hq/` vẫn còn, nhưng dòng ĐỎ/TỤT/ĐÁNG NGỜ thì chỉ có ở đây.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace",
                       line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")

#: (nhãn, file, mốc ĐẠT mong đợi hoặc None)
CONG = [
    # 70, 69 và 68 PHẢI nằm trong danh sách này: cổng không được gọi thì nó chỉ
    # là một file .py nằm đó, và lượt hồi quy "xanh" mà không chạy cổng mới
    # chính là bẫy "ĐẠT OAN vì lượt chạy chưa tới chốt".
    #
    # Cổng 70 canh bản sửa CHẶN SẢN XUẤT (Groq khai tử `llama-3.3-70b-
    # versatile` -> 404 hàng loạt -> chết cả dây chuyền). Nó CÓ gọi Groq thật ở
    # mục 9 để chứng minh bảng phân loại lỗi khớp thân lỗi Groq trả về HÔM NAY;
    # muốn chạy offline thì đặt `BQ_BO_MANG=1`.
    # Cổng 72 canh nhóm GIỌNG NGOÀI (OmniVoice / IndexTTS). Nó KHÔNG đốt GPU
    # hay lượt Groq nào trong hồi quy (vá `_chay_ov` + `_lay_moc_groq`); ca
    # chạy THẬT bật bằng `BQ_GN_THAT=1`.
    # Mốc 40 -> 48 (18/08/2026): CA 7 thêm 5 mục canh NHÃN ĐỔI THEO MÁY (có bộ
    # gióng hàng thì con số PHỦ/RUNG trong nhãn phải khác hẳn lúc chưa có, và
    # phần GIẤY PHÉP CC-BY-NC giữ nguyên ở CẢ HAI) + 3 mục canh CHỖ ĐỂ ĐỒ
    # không nằm trong `%TEMP%` (môi trường 7,74 GB từng nằm ở đó: một lượt dọn
    # đĩa là giọng biến khỏi combo, đúng bệnh `_lib` cổng 58 CA5).
    # Cổng 74 canh bản sửa CHẶN SẢN XUẤT thứ HAI trong hai ngày: Groq áp trần
    # token đầu ra MẶC ĐỊNH (3072/2048) khi app không đặt `max_tokens`, làm JSON
    # bản dịch ĐỨT giữa chừng -> "LLM trả về không phải JSON hợp lệ". Nó nằm
    # ĐÂY vì đúng hôm qua cổng 70 vừa dính bẫy "cổng không ai gọi thì chỉ là
    # một file .py nằm đó". Không đốt lượt Groq đáng kể: chỉ CA 9 gọi thật
    # (30 câu, 1 lượt); `BQ_BO_MANG=1` để chạy hoàn toàn offline.
    # Cổng 77 canh LỖ HỔNG BẢO MẬT THẬT (18/08/2026): cổng 70 in `str(phat_key
    # ())` = NGUYÊN VĂN key Groq ra `_kq70*.txt`. Nó đứng ĐẦU danh sách vì nó
    # KHÔNG gọi mạng, chạy vài giây, và nếu có key rơi ra đĩa thì phải biết
    # NGAY chứ không đợi hết 30 cổng. Nó cũng là cổng duy nhất quét ĐĨA — chạy
    # sau các cổng khác thì nó còn bắt được key do CHÍNH LƯỢT NÀY vừa ghi ra,
    # nên đặt thêm một lượt nữa ở CUỐI (xem `CONG_CUOI`).
    # Cổng 80 ĐỨNG ĐẦU, trước cả 77 — không phải vì nó quan trọng hơn, mà vì
    # nó canh đúng cái NỀN mà 30 cổng còn lại đứng lên. Hôm nay
    # `giong_ngoai._don(Path(""))` = `rmtree('.')` đã **xoá sạch cây mã** (mất
    # `.git`, `.venv`, `bin`, `_lib`, `_giong_hang`, `_piper`, `_giong_ngoai`)
    # với mã thoát 0. Gần như cổng nào trong danh sách này cũng dựng hộp cát
    # rồi `rmtree` nó, nên chạy chúng trên một bản mã còn cửa hở là đánh cược
    # cả cây mã mỗi lượt hồi quy. Nó cũng rẻ (~15 giây, không mạng, không
    # ffmpeg, không Groq) nên đứng đầu không tốn gì.
    ("80 không xoá nhầm",   "_test_khong_xoa_nham.py",   69),
    ("77 không lộ key",     "_test_khong_lo_key.py",     27),
    # Cổng 78 canh lỗi MẤT NỘI DUNG: đoạn không được đọc lại thì mất luôn giọng
    # gốc -> chỉ còn nhạc -> im tiếng người. Đo trên 4 bản anh Hùng đã xuất:
    # 82,3s/1.209,3s = 6,8%, dồn vào 2/4 video. Cổng KHÔNG gọi Demucs/Groq/mạng
    # (nguồn dựng bằng `lavfi`) nên tiền định, không nhấp nháy.
    ("78 bù giọng gốc",     "_test_bu_giong_goc.py",     52),
    ("74 JSON bao dung",    "_test_json_bao_dung.py",     80),
    # Cổng 75 canh bản sửa CHẶN SẢN XUẤT thứ BA: clip xuất ra KHÔNG MỞ ĐƯỢC,
    # hình trắng (`0x80004005 — unsupported encoding settings`). Nó phải nằm
    # ĐÂY, không được để làm "một file .py nằm đó" — đúng bẫy cổng 70 dính hôm
    # qua. Nó KHÔNG gọi mạng (chỉ ffmpeg thật), và vì chạy vài phút nên nó còn
    # làm QUÃNG NGHỈ cho bể key Groq giữa cổng 74 (CA 9 gọi thật) và cổng 70
    # (mục "41 key còn nguyên") — đúng chỗ cổng 70 từng ĐỎ OAN vì 429 thật do
    # hai cổng đốt lượt đứng sát nhau.
    ("75 clip mở được",     "_test_clip_mo_duoc.py",     63),
    # Cổng 76 canh việc "mức nhấn nhá hiện cạnh mỗi giọng + giọng truyền cảm
    # lên trên". Nó KHÔNG gọi Groq và KHÔNG chạy ffmpeg (chấm bảng số + hàm
    # thuần) nên đứng đâu cũng được; để cạnh nhóm cổng giọng cho dễ đọc.
    ("76 nhấn nhá từng giọng", "_test_nhan_nha.py",      29),
    # Cổng 79 canh việc GOM NHÓM danh sách giọng (anh Hùng: "không phân gì cả,
    # rất lung tung"). Đo trước khi sửa: combo có 110 mã cho 90 giọng, tức
    # 20 dòng TRÙNG MÃ THẬT SỰ. Nó cũng KHÔNG gọi mạng/ffmpeg/Groq nên tiền
    # định; để cạnh cổng 76 vì hai cổng đọc chung `nhan_nha.BANG`.
    # 58 -> 84 (v2.38.0): thêm CA 8 (nhóm "khuyên dùng" làm LỐI TẮT) · CA 9
    # (mức nhấn nhá trên TỪNG dòng; biến thể cao độ KHÔNG được mượn số của
    # giọng gốc) · CA 10 (20 giọng VieNeu không phải giọng chết — gọi THẬT
    # `_synth_all_words` rồi xem nó rẽ vào đâu). NÂNG mốc = cổng CHẶT HƠN.
    # 84 -> **87** (19/08/2026): mốc 84 đã LẠC HẬU — cổng thật có 87 mục, và vì
    # bộ so chỉ kêu khi `ĐẠT < mốc` nên 3 mục dư đó chưa bao giờ được canh.
    # Lượt này cổng ra 86/1 (đuôi nhãn VieNeu dài 142 > trần 132 sau khi sửa
    # nhãn "250 MB"); đã chữa bằng cách viết ngắn lại ĐUÔI, **KHÔNG nới trần**.
    ("79 gom nhóm giọng",   "_test_gom_giong.py",        87),
    # Cổng 81 canh lượt 19/08/2026: MỞ KHOÁ 185 giọng edge-tts (`giong_mo`) ·
    # giọng RIÊNG THEO KÊNH + XOAY VÒNG (`giong_kenh`) · NHÂN BẢN giọng từ mẫu
    # (`nhan_ban_giong`) · Chatterbox (`giong_chatter`). Cũng KHÔNG gọi mạng,
    # KHÔNG chạy model, KHÔNG tốn lượt Groq — nó chấm hàm thuần + DB hộp cát,
    # nên để cạnh cổng 76/79 (ba cổng cùng đọc `nhan_nha.BANG`).
    # MỆNH ĐỀ TRUNG TÂM (CA 3i): xoay vòng giọng phải TIỀN ĐỊNH qua NHIỀU
    # TIẾN TRÌNH có `PYTHONHASHSEED` KHÁC NHAU — app chạy 3 làn xuất song song
    # nên dùng `hash()` là 3 Part của CÙNG một video ra 3 giọng, và không tra
    # lại được. THỬ PHÁ (đổi `crc32` -> `hash()`): cổng ĐỎ đúng mục đó,
    # `0/3 tiến trình khớp`, mã thoát 1.
    ("81 giọng theo kênh",  "_test_giong_kenh.py",       57),
    # Cổng 82 canh lượt NỐI Chatterbox vào app (v2.38.0). Trước nó,
    # `giong_chatter.py` là 623 dòng mã mà **không một dòng nào trong
    # `giong_bang.py`/`dubbing.py` gọi tới** — đúng bẫy "cổng/tính năng không ai
    # gọi thì chỉ là một file .py nằm đó" mà cổng 70 đã dính. Nó KHÔNG gọi
    # mạng, KHÔNG nạp model thật, KHÔNG đốt GPU: phần đắt nhất (CA 7) chạy
    # CHÍNH script runner trong tiến trình con với gói `chatterbox` GIẢ mô
    # phỏng đúng tính dính `self.conds` — thứ biến "đọc kênh A rồi kênh B"
    # thành "kênh B ra giọng kênh A" mà mã thoát vẫn 0.
    ("82 Chatterbox đã nối", "_test_chatter_noi.py",     59),
    # Cổng 83 canh lượt 19/08/2026: MỞ HẾT giọng edge-tts (**76 -> 322 giọng /
    # 75 thứ tiếng**) sau khi TÁCH "đọc được" khỏi "đo nhấn nhá". Nó lôi ra hai
    # lỗi thật: `giong_mo.nen_mo` là **MÃ CHẾT** (quét AST: chỉ `loc_mo` gọi,
    # mà `loc_mo` không ai gọi -> 185 giọng "đã mở khoá" chưa bao giờ ra tới
    # combo), và 4 giọng Inuktitut chết vì regex của **thư viện khách**
    # `edge_tts` không bóc nổi locale 4 đoạn — chết TRƯỚC KHI chạm mạng.
    # Nó **KHÔNG tốn lượt Groq** và **KHÔNG đốt hạn mức ElevenLabs** (nhánh
    # `el:` chấm bằng cách vá điểm đến rồi xem nó rẽ vào đâu). CA 2 CÓ gọi mạng
    # edge-tts thật nhưng chỉ **3 giọng** (mẻ tiền định theo `crc32`, KHÔNG
    # `hash()`) — mẻ đó là thứ giữ cho bảng biên bản khỏi thành lời tự khai;
    # mạng hỏng thì nó BỎ QUA từng giọng, chỉ ĐỎ khi hỏng CẢ MẺ.
    # THỬ PHÁ nằm ngay trong cổng (CA 9, BẮT 3/3), và chốt chống-PASS-OAN của
    # mục 3f đã thử thật: `BQ_MOC_GIONG=HEAD` -> ĐỎ đúng mục đó, mã thoát 1.
    ("83 mở hết giọng",     "_test_mo_giong_het.py",     41),
    # Cổng 84 canh CÁCH BÀY danh sách 392 mã giọng (anh Hùng 19/08/2026:
    # *"nhiều giọng hơn mà không có phân chia gì à, LOẠN QUÁ"* và *"không có
    # mục tìm kiếm giọng à, thêm vào"*). Cổng 79 đã canh việc GOM NHÓM đúng;
    # chỗ hỏng nằm ở BÀY: ô danh sách hẹp nên `QComboBox` elide kiểu
    # **ElideMiddle** ăn đúng khúc GIỮA mang thông tin, và tiêu đề nhóm trông y
    # hệt dòng giọng.
    # **CỔNG NÀY TỪNG KHÔNG NẰM Ở ĐÂY** — 4 bản vá (4332367 · 8156dac ·
    # 574731c · e6738b3) đã lên `main` kèm ghi chú *"0 nhãn bị cắt"* mà cổng
    # canh chúng là một file `.py` KHÔNG AI GỌI, đúng bẫy cổng 70 đã dính.
    # Nó KHÔNG gọi mạng, KHÔNG tốn lượt Groq, KHÔNG đụng registry
    # (`BQ_QSETTINGS_INI`); phần đắt nhất là dựng 6 hộp thoại offscreen (~40 s).
    # THỬ PHÁ nằm TRONG chính cổng (CA 8, BẮT 4/4: gỡ `nhan_gon` -> 24 nhãn bị
    # cắt · gỡ `NoItemFlags` -> tiêu đề nhóm CHỌN ĐƯỢC · gỡ `rong_vua_chu` ->
    # hộp co về 300 px · gỡ nguồn tìm toàn-danh-sách -> gõ tên giọng nhóm KHÁC
    # không ra). Cổng còn LƯU ẢNH `_ANH_O_TIM_GIONG.png` để người tự mở ra
    # nhìn: **đếm điểm ảnh KHÔNG phát hiện được ô vuông tofu** (tofu 2.431 px
    # vs chữ thật 517 px = ngược 4,7 lần).
    # Mốc 48 -> **59**: thêm CA 9 canh *"con số ĐÚNG mà đặt chỗ SAI thì người
    # đọc NHÂN LÊN"* (anh Hùng: *"sao có cái giọng 1 giọng tận 250mb á tốn
    # thế"*). Đo lúc chưa sửa: `250 MB` trên **20 dòng** VieNeu = đọc thành
    # 5 GB · `6,1 GB` trên **5 dòng** OmniVoice = đọc thành 30,5 GB. CA 9 canh
    # CẢ LỚP BỆNH (mọi dòng có số dung lượng phải nói "dùng chung"), kèm 3 mục
    # TỰ KIỂM BỘ DÒ — thiếu chúng thì "0 dòng bệnh" có thể là bộ dò đã chết.
    ("84 ô tìm giọng",      "_test_o_tim_giong.py",      63),
    # CỔNG 86 — chế độ "ĐÈ GIỌNG, KHÔNG TÁCH" (anh Hùng đề xuất 19/08/2026).
    # Nối vào ĐÂY chứ không để rời: bản sửa CHẶN SẢN XUẤT mà chỉ được canh bởi
    # một file `.py` không ai gọi thì đúng bằng không được canh (bẫy cổng 70).
    # Mốc 62 gồm: CA 6 chạy ffmpeg THẬT chứng minh mất tiếng arm DE = 0,00 s
    # trong khi arm TACH mất 2,40 s ĐÚNG tại cửa sổ không được lồng (chốt
    # chống-đạt-oan nằm trong chính phép đo) · CA 2 khoá chống trùng khi TẮT cờ
    # giống TỪNG KÝ TỰ mốc v2.39.0 · CA 8 ô chọn trong hộp (mặc định GIỮ cách
    # cũ, nút Chạy MỞ khi chọn đè trên máy chưa có Demucs) · 5j/5k/5l canh lời
    # nhắn tiến độ phải KHỚP KHOÁ bước 9 (bản vá này từng làm thanh tiến độ
    # sống nhờ đường lùi) · 5m cửa thứ ba của chốt Demucs ở `jobs.py`.
    # THỬ PHÁ `_pha_de_giong.py`: BẮT 8 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0.
    ("86 đè giọng",         "_test_de_giong.py",         62),
    # Mốc 48 -> 98 (19/08/2026, lượt dựng lại `_giong_ngoai/`). Thêm 3 khối:
    # CA 10 môi trường nằm ĐÚNG CHỖ (không %TEMP%, không cạnh `.exe`) · CA 11
    # `cai_omnivoice` — nút dựng lại mà repo THIẾU, nên khi `_don(Path(""))`
    # xoá sạch cây mã thì 7,74 GB đó là thứ DUY NHẤT không dựng lại được ·
    # CA 12 CHỌN X RA X (câu tả phải nằm trong BẢNG TỪ ĐÓNG của model — chữ
    # ngoài bảng đã giết `ov:nu_am` một lần; mã lạ phải LÙI chứ không đọc
    # bằng giọng mặc định).
    # CA 10d LÔI RA MỘT LỖI THẬT: `goc or Path.home()` KHÔNG BAO GIỜ lùi được
    # vì `Path("")` là `WindowsPath('.')` (truthy) -> bản đóng gói có
    # DATA_DIR hỏng thì thư mục 7,7 GB rơi vào THƯ MỤC ĐANG LÀM VIỆC. Cùng họ
    # bẫy đã xoá sạch cây mã sáng nay, chỉ khác là GHI nhầm chỗ chứ không
    # XOÁ nhầm chỗ. Bản đầu của chính mục 10d ĐẠT OAN vì chỉ hỏi "có cạnh
    # .exe không" — ĐẠT vì lý do SAI.
    # THỬ PHÁ `_pha_giong_ngoai.py` (10 phép, mỗi phép gỡ ĐÚNG 1 chốt).
    ("72 giọng ngoài",      "_test_giong_ngoai.py",      98),
    # Cổng 73 canh chính `giong_hang.py`. Trước hôm nay nó chỉ được canh GIÁN
    # TIẾP qua cổng 72 — tức phần lấy mốc cho MỌI máy đọc không có cổng riêng.
    # Mốc `None` -> **52** (19/08/2026): cổng thêm CA 9 canh bản vá `e6738b3`
    # (chọn chỉ mục torchaudio theo TORCH ĐANG CÓ, KHÔNG theo CARD). Để `None`
    # là cổng chỉ canh mã thoát — mất sạch khả năng bắt "một mục âm thầm biến
    # thành BỎ QUA". Đã chạy thật: ĐẠT 52 · HỎNG 0.
    ("73 gióng hàng",       "_test_giong_hang.py",       52),
    ("71 tách giọng GPU",   "_test_demucs_gpu.py",       22),
    # Mốc 42 -> 44: mục 4 thêm 2 chốt cho phép CHE KEY (che vẫn tách được từng
    # key · bản in KHÔNG chứa nguyên văn key) — xem cổng 77.
    ("70 model Groq còn sống", "_test_groq_model.py",    44),
    # Mốc 95 -> 160: CA 9 (20/08/2026). Việc đặt ra là mở bộ chữa viết tắt
    # sang **giọng NHÂN BẢN `vnb:` / VieNeu `vn:`** — đường đó chạy
    # `giong_vieneu` nên không rơi xuống nhánh edge-tts. Đường ĐÃ NỐI và mốc
    # trả về token gốc đã chứng minh trên GIÓNG HÀNG THẬT (12/12), **nhưng
    # MẶC ĐỊNH TẮT vì số đo BÁC**: `_do_viet_tat_vieneu.py` (6 token × 2 vòng
    # đan xen, Groq chép ngược) ra giọng nhân bản đọc THÔ đúng **12/12**, bật
    # bộ chữa vào còn 10/12 — **TỐT LÊN 0 · TỆ ĐI 2**. Vì vậy bất biến CA 9 là
    # *"mặc định KHÔNG đụng VieNeu"*; công tắc `BQ_VIET_TAT_VN=1` chỉ để đo.
    # Thử phá `_pha_viet_tat_vnb.py`: BẮT 6 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0.
    ("69 viết tắt + mốc",   "_test_viet_tat.py",        160),
    # Mốc 43 -> 44: thêm mục 7a' TỰ KIỂM bản vá cách ly QSettings (18/08/2026,
    # cổng từng ĐỎ OAN vì đọc trúng registry thật của anh Hùng).
    # 44 -> 45: thêm mục TỰ KIỂM cho phép đo cỡ chữ (phải có NỀN để trừ, và cỡ
    # nhỏ vẫn phải đếm ra chữ). Trước đó phép đo cộng cả ĐỘ SÁNG CỦA PHIM vào
    # số điểm ảnh chữ nên cổng đỏ oan mỗi khi kho video đổi sang phim sáng.
    ("68 kiểu chữ thay giọng", "_test_kieu_chu_tg.py",    45),
    # Cổng 85 canh lỗi anh Hùng gặp 19/08: nghe thử chọn tiếng Anh mà đọc câu
    # TIẾNG VIỆT. Nó rẻ (4-5 lượt edge-tts, KHÔNG Groq, KHÔNG ElevenLabs — vá
    # `synth_demo` nên 0 ký tự) và đứng cạnh cổng 65 vì cùng canh nút nghe thử.
    # Số 85 chứ không phải 81: 81-84 vừa bị luồng khác lấy trong cùng ngày.
    ("85 nghe thử đúng tiếng", "_test_nghe_thu_nn.py",    67),
    # Cổng 87 — giọng Kokoro. Đứng cạnh nhóm giọng vì cùng canh cửa
    # `dubbing._synth_all` / `_synth_all_words`. Số **87** lấy bằng cách đọc
    # chính `CONG` này (max đang là 86), KHÔNG đếm theo trí nhớ: bảng này đã có
    # **52 và 77 trùng số**, mà trùng số thì hai cổng ghi đè `_kqNN.txt` của
    # nhau (bài học 70 vs 69, 85 vs 81).
    # Nó rẻ: KHÔNG gọi mạng, KHÔNG tốn lượt Groq/ElevenLabs. Có đọc THẬT nhưng
    # chỉ **4/28 giọng** (mỗi giọng là một tiến trình rời ~9 giây; 28 giọng ≈
    # 4,4 phút thì quá đắt cho một lượt 42 cổng) — bảng đủ 28 giọng nằm ở
    # `_do_28_giong_kk.py`, đo được **28/28 KÊU, 0 CÂM**. Máy chưa tải Kokoro
    # thì CA 9 tự **BỎ QUA** (không tự cho ĐẠT — đó là "phép đo phát chứng
    # nhận"; cũng không báo HỎNG — đỏ oan thì người ta bỏ qua cổng).
    # Thử phá `_pha_kokoro.py`: **BẮT 8 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
    ("87 giọng Kokoro",     "_test_kokoro.py",           44),
    # Cổng 88 — GIỌNG CỦA ANH HÙNG (nhân bản từ mẫu). Số **88** lấy bằng cách
    # đọc chính `CONG` này (max đang là 87), KHÔNG đếm theo trí nhớ: bảng này
    # đã có **52 và 77 trùng số**, mà trùng số thì hai cổng ghi đè `_kqNN.txt`
    # của nhau (bài học 70 vs 69, 85 vs 81).
    #
    # Nó nằm ĐÂY vì `app/core/nhan_ban_giong.py` là **ca thứ NĂM** của bệnh
    # "hàm xong ≠ tính năng xong": 564 dòng đã có cổng 81 chấm XANH mà
    # `grep -rn "nhan_ban_giong" app/ui/` ra **0 dòng** — cổng 81 canh HÀM,
    # không canh CÁI ANH HÙNG BẤM. Để cổng này ngoài danh sách thì lần "dọn
    # gọn" sau có thể gỡ nút mà mọi cổng vẫn xanh (đúng bẫy cổng 70/84).
    #
    # RẺ: KHÔNG gọi mạng, KHÔNG tốn lượt Groq/ElevenLabs, KHÔNG nạp model
    # VieNeu (CA 2 vá `giong_vieneu.doc_loat` rồi xem cửa rẽ vào đâu; CA 7 vá
    # `co_vieneu` để giả lập máy thiếu model). Phần đắt nhất là 4 lượt ffmpeg
    # sinh WAV mẫu + 1 tiến trình con đọc lại sổ (~30 giây). Máy chưa tải bộ
    # VieNeu thì CA 11 tự **BỎ QUA** — không tự cho ĐẠT (đó là "phép đo phát
    # chứng nhận") và không báo HỎNG (đỏ oan thì người ta bỏ qua cổng).
    # Thử phá `_pha_giong_toi.py`: 20 phép, mỗi phép gỡ ĐÚNG một chốt.
    # 66 -> 104 (20/08/2026): thêm CA 12 — NÚT TẢI PHẦN NHÂN BẢN (torch +
    # torchaudio vào venv VieNeu). NÂNG mốc, không hạ: mốc là SÀN, hạ nó cho
    # cổng xanh là bỏ cổng.
    # 170 -> 233 (26/08/2026): CA 16 + CA 17 canh việc APP TỰ DỜI môi trường
    # VieNeu ra khỏi `%TEMP%`. Để mốc cũ thì 63 mục mới KHÔNG được sàn nào
    # canh — bộ so chỉ kêu khi `ĐẠT < mốc`, nên mốc lạc hậu là cổng câm một
    # nửa (đúng bệnh chính file này đã ghi ở dòng 111-112).
    ("88 giọng của tôi",    "_test_giong_toi.py",       233),
    # Cổng 89 — CHỈNH VIDEO THEO GIỌNG (`he_so_hinh`) + độ to bản trộn + hộp
    # Thay giọng gọn. Số **89** lấy bằng cách đọc chính `CONG` này (max đang là
    # 88), KHÔNG đếm theo trí nhớ.
    #
    # **FILE NÀY ĐÃ NẰM NGOÀI DANH SÁCH TỪ 18/08/2026 VÀ ĐÃ CHẾT MÀ KHÔNG AI
    # BIẾT** — đúng bẫy cổng 70 ("cổng không ai gọi thì chỉ là một file .py
    # nằm đó"), cộng thêm bẫy TRÙNG SỐ: nó tự nhận là "CỔNG 76" trong khi 76
    # đã thuộc `_test_nhan_nha.py` ở ngay trên, tức hai cổng ghi đè
    # `_kq76.txt` của nhau (bài học 70 vs 69, 85 vs 81). Hệ quả ĐO ĐƯỢC:
    # `nhan_nha.muc()` đổi chữ ký còn MỤC 6 cũ vẫn gọi `muc(voice, nn)` ->
    # cổng nổ `TypeError` giữa chừng suốt nhiều lượt hồi quy. MỤC 6 cũ nay bỏ
    # (phần nhãn nhấn nhá đã có cổng 76 canh), thay bằng 3 mục MỚI canh đúng
    # chỗ dễ vỡ nhất của tính năng.
    #
    # Nó RẺ: KHÔNG gọi mạng, KHÔNG tốn lượt Groq/ElevenLabs, KHÔNG nạp model.
    # Phần đắt nhất là ffmpeg thật + 2 hộp thoại offscreen (~2-3 phút).
    # Thử phá `_pha_khop_video.py`: **BẮT 9 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
    # Mốc 73 -> **75**: lượt phá ĐẦU ra `BẮT 8 · LỌT 1` và cái LỌT là LỖ CỦA
    # CỔNG — gỡ phép nhân `k` khỏi mốc ĐẦU câu (`a = c["start"] * k`) thì
    # `khung = b − a` PHỒNG hơn cả `k` (vì `b` vẫn giãn) nên câu nào cũng lọt,
    # `tempo_max` vẫn 1,000, cổng vẫn XANH — trong khi tiếng bị đặt ở mốc CHƯA
    # GIÃN của một video ĐÃ GIÃN, tức tiếng TRÔI khỏi hình mỗi lúc một xa
    # (đúng lỗi v1.87). Nay chấm THẲNG chỗ đặt mảnh + có mục ĐỐI CHỨNG k=1,0.
    #
    # 75 -> **100** (25/08/2026): thêm MỤC 9 — ĐỌC ĐỀU MỘT TỐC ĐỘ (`doc_deu`,
    # bỏ bước 4c `doc_nhanh_vua_khung`). Mục này canh: cửa chuẩn hoá
    # `chuan_khop_cach` · khoá chống trùng TẮT thì giống TỪNG KÝ TỰ mốc và BẬT
    # thì mọc đuôi `:dd=1` ở CUỐI · **CHẠY THẬT** `thay_giong_video` để chứng
    # minh bước 4c chạy **0 lần** (không chỉ "mã có nhánh đó" — bài học *"hàm
    # xong ≠ tính năng xong"*, repo này đã 4 lần có module lõi nằm chết) · và
    # cả chuỗi chuyền cờ UI -> `xep_mot` -> payload -> job -> lõi.
    # NÂNG mốc, không hạ — mốc là SÀN.
    ("89 chỉnh hình theo giọng", "_test_am_va_hinh.py",  104),
    # Cổng 90 — NHỊP TIẾN TRÌNH CỦA MÁY ĐỌC GỘP CẢ LOẠT. Số **90** lấy bằng
    # cách ĐỌC chính `CONG` này (max đang là 89), KHÔNG đếm theo trí nhớ: bảng
    # này đã có **52 và 77 trùng số**, mà trùng số thì hai cổng ghi đè
    # `_kqNN.txt` của nhau (bài học 70 vs 69, 85 vs 81).
    #
    # Nó canh MÓN NỢ ĐÃ GÂY RA MỘT NGÀY MẤT LÒNG TIN (21/08/2026): anh Hùng
    # hỏi **4 LẦN** *"nó vẫn dừng ở 62% BƯỚC 5, có lỗi không"* và **suýt bấm
    # Dừng**, mất hơn một tiếng máy chạy ĐÚNG. Bản vá `a0062b6` (bước 5) và
    # `d4968a6` (4b/4c) đã ra, nhưng **không có cổng nào canh** — cả hai
    # commit đó tự ghi thẳng trong phần "CHƯA LÀM" rằng đây là món nợ ĐẮNG
    # NHẤT, vì người sau bỏ `on_msg` đi thì không ai biết.
    #
    # MỆNH ĐỀ: **SÁU** chỗ gọi TTS phải báo **>= 2 nhịp KHÁC NHAU TRONG LÚC
    # ĐANG ĐỌC** — ba chỗ của `thay_giong.py` (`doc_ban_dich` ·
    # `rut_gon_vua_khung` · `doc_nhanh_vua_khung`, đường THAY GIỌNG) và ba chỗ
    # của `dubbing.build_recap_track` (lượt đọc CHÍNH · lượt VÉT · giọng dự
    # phòng, đường REUP THUYẾT MINH). Đây là mệnh đề về HÀNH VI: cổng giả lập
    # một máy đọc gộp-cả-loạt phát `Doc cau N/M` rồi GỌI THẬT cả bốn hàm và
    # BẮT từng lần `on_progress` — quét tĩnh "có chữ `on_msg` không" thì luôn
    # có phép phá giữ nguyên mặt chữ mà đổi nghĩa (`on_msg=None`, bài học cổng
    # 56d). Phần quét tĩnh có nhưng bằng **AST** và kèm **ca TỰ KIỂM BỘ DÒ**.
    #
    # MỐC 65 -> **113** (26/08/2026) — trả HAI MÓN NỢ mà chính cổng này ghi ra:
    #  (1) `dubbing.py` còn 3 chỗ gọi mà cổng KHÔNG có ca nào. ĐO
    #      (`_do_nhip_recap.py`): cả ba đều KHÔNG truyền `on_msg` -> **0 nhịp
    #      / 3 lượt gọi**, thanh đứng ở **5%** suốt lượt đọc. Đã vá bằng CỬA
    #      CHUNG `thay_giong._nhac_tung_cau` (không chép bộ thứ hai).
    #  (2) DÒNG CHỮ vẫn đi lùi được: máy đọc gộp cả loạt nổ `on_done` cho MỌI
    #      câu ở CUỐI nên `xong/N` hiện sau `6/6` rồi nhảy về `1/6` — đo được
    #      **5 lần lùi** và tỉ lệ thô tụt **1,0000 -> 0,1667**. Nay mọi lời báo
    #      đi qua `_nhac`, thêm `chu_khong_lui` (chỉ viết đè khi CÙNG mẫu số).
    #      Sau vá: **0 lần lùi** trên cả 4 đường.
    #
    # RẺ NHẤT DANH SÁCH: **~1 giây**, KHÔNG mạng · KHÔNG Groq · KHÔNG
    # edge-tts · KHÔNG ffmpeg · KHÔNG nạp model (máy đọc, `cat_le_loat`,
    # `probe_duration`, lượt LLM rút gọn và mọi hàm ffmpeg của
    # `build_recap_track` đều là bản GIẢ; bốn hàm ĐANG TEST chạy THẬT). Tiền
    # định — chạy bao nhiêu lượt cũng ra một con số.
    # Thử phá `_pha_nhip_doc.py`: **18 phép** (11 cũ + 7 mới), mỗi phép gỡ
    # ĐÚNG một chốt, trên CẢ HAI file đích ->
    # **BẮT 18 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
    ("90 nhịp lúc đang đọc", "_test_nhip_doc.py",        113),
    #
    # CỔNG 91 — nhân bản giọng ĐA NGÔN NGỮ (Chatterbox) đã nối vào hộp
    # «Giọng của tôi», và BỐN CHỐT của bộ đó đều có răng: đọc loạn nhịp (CA 3)
    # · BẮT BUỘC GPU (CA 4) · ĐÓNG DẤU CHÌM (CA 5) · KHÔNG có tiếng Việt nên
    # nó BỔ SUNG VieNeu chứ không thay (CA 1).
    # Không mạng · không nạp model · không đốt GPU · không tốn lượt Groq —
    # hàm thuần + ffmpeg THẬT trên WAV `lavfi` tự sinh. Thử phá
    # `_pha_da_ngu.py`: 14 phép, mỗi phép gỡ ĐÚNG một chốt.
    # Mốc 76 -> **79** (26/08/2026): mốc 76 đã LẠC HẬU (cổng thật ra 77), và
    # vì bộ so chỉ kêu khi `ĐẠT < mốc` nên mục dư đó chưa bao giờ được canh —
    # đúng lớp lỗi cổng 79 đã dính. Lượt thử phá còn lôi ra **một LỖ THẬT của
    # cổng**: mục 4f cũ hỏi *"thân hàm có chữ `_ghi_log` không"*, mà
    # `_chatter_hay_khong` có **HAI** nhánh lùi cùng gọi `_ghi_log`, nên phép
    # phá 7 (bỏ log của nhánh THIẾU BỘ = lùi IM LẶNG trên máy nhân viên)
    # **LỌT**. Nay 4f GỌI THẬT nhánh đó rồi bắt sổ lời gọi (+2 mục).
    # Mốc 79 -> **100** (26/08/2026, CA 10 — TIẾNG TRUNG): con số báo động đầu
    # tiên của bộ này là arm `A_nu × zh` **1,81x**, và lượt đo lại đã kết luận
    # *"không tái hiện được"* rồi HẠ nó khỏi nhãn — trong khi bộ đo lúc ấy
    # **thiếu đúng bộ câu `zh`** và còn dùng một MẪU khác hẳn. Dựng lại đúng
    # arm thì tật **CÓ tái hiện**: dùng lại CHÍNH FILE MẪU của lượt cũ ra
    # **1,798x** (bảng cũ 1,806x — khớp tới TỪNG CÂU), còn mẫu SINH LẠI hôm nay
    # ra 1,665x; arm đối chứng `B_nam × zh` vẫn **0,789x** y như bảng cũ.
    # Hai con số 1,67/1,80 khác nhau đúng ở **BYTE của file mẫu** (edge-tts
    # không trả audio giống từng byte qua các ngày), nên nhãn ghi DẢI chứ không
    # ghi một số. (Ba con số trên là thước CŨ — chưa cắt lề — để so thẳng với
    # bảng 25/08; nhãn thì ghi theo thước ĐÚNG CHO APP là **0,81x/1,85x**, xem
    # `giong_chatter.NHIP_THEO_TIENG`.)
    # CA 10 canh hai thứ: bộ đo KHÔNG được thiếu `zh` lần nữa, và nhãn phải nói
    # ra số ĐÍCH DANH theo TIẾNG ở chỗ người dùng đang QUYẾT (không phải chỉ
    # trong một hằng số không ai đọc — `giong_chatter.nhan_giong()` quét AST ra
    # **0 chỗ gọi** trong `app/ui`).
    # Mốc 105 -> 131: thêm **CA 11** (26/08/2026). Anh Hùng báo giọng nhân bản
    # đọc tiếng Anh *"như thằng mới học"*; nghi phạm số một là `goi_y_may`
    # (`en`->Chatterbox) đã thành hàm chết. Đo ra **hai chuyện ngược dự đoán**:
    # nó KHÔNG chết (gọi trong `them_giong`, tức lúc TẠO giọng chứ không phải
    # lúc ĐỌC), và **nối nó vào đường đọc là LÀM TỆ ĐI** — cùng một file mẫu,
    # `cb:` sai chữ trong câu **17,9%** so với **2,6-5,1%** của `vnb:`
    # (`_kq_vnb_en.txt`). CA 11 canh cả hai chiều: đường đọc không tự đổi máy
    # (AST **và** GỌI THẬT), bảng `SO_DO_EN` còn nguyên và nói đúng chiều, câu
    # cảnh báo đã nối tới giao diện (repo có 6 ca "hàm xong ≠ tính năng xong"),
    # và `dedup_key` của `enqueue_thay_giong` KHÔNG đổi một ký tự nào.
    ("91 nhân bản đa ngôn ngữ", "_test_nhan_ban_da_ngu.py", 131),
    # Cổng 92 là bước TIẾP THEO của đúng việc cổng 91 vừa đo. Cổng 91 kết luận
    # bệnh của `vnb:` đọc tiếng Anh là **KHÔNG ĐỀU** (cùng mã cùng mẫu: lượt 1
    # WER 3,1% · lượt 2 WER 12,7%) và ghi nợ *"chưa thử phép chữa đáng làm nhất
    # — dò câu lan man rồi ĐỌC LẠI"*. Cổng này canh đúng phép chữa đó.
    # Nó **KHÔNG gọi mạng · KHÔNG Groq · KHÔNG GPU · KHÔNG ffmpeg** (máy đọc bị
    # thay bằng hàm giả sinh WAV theo nhịp BIẾT TRƯỚC) nên TIỀN ĐỊNH và chỉ mất
    # vài giây — đứng đâu trong danh sách cũng được.
    # Số **92** lấy bằng cách ĐỌC chính `CONG` này (max đang là 91), KHÔNG đếm
    # theo trí nhớ: trùng số là hai cổng ghi đè `_kq<n>.txt` của nhau (bài học
    # 70 vs 69, rồi 85 vs 81).
    # Mốc 48 -> 85 (27/08): lượt đo LAN MAN THEO NGÔN NGỮ thêm CA 6 (hiệu
    # chuẩn ngưỡng 4 tiếng, có arm TRẦN bản ngữ) · CA 7 (tiếng đọc không được)
    # · CA 8 (bộ đếm từ CJK-aware) · **CA 9** (hệ chữ ngoài tầm phiên âm ->
    # CHẶN trước khi đốt GPU). CA 9 là chốt CHẶN thật, không phải nhãn.
    ("92 đọc lại câu lan man", "_test_doc_lan.py",       85),
    ("67 Adam ElevenLabs",  "_test_eleven_tg.py",        35),
    ("66 độ to đường xuất", "_test_do_to_xuat.py",       50),
    ("65 độ to + nghe thử", "_test_do_to_nghe_thu.py",   47),
    # Mốc 47 -> 57: cổng đã mọc thêm mục từ lâu (đo 53) và 18/08 thêm CA 3g
    # (nút tải Piper phải KHOÁ khi máy thiếu Python 3, như nút Demucs). Để mốc
    # thấp hơn số thật là mất khả năng bắt "mục lặng lẽ biến mất".
    ("64 Piper",            "_test_piper.py",           57),
    # Mốc 24 -> 36 (26/08/2026): cổng thật ra 36 từ lâu (lượt nối Chatterbox đo
    # lại vẫn 36/0). Bộ so CHỈ kêu khi `ĐẠT < mốc`, nên 12 ca dôi ra đó **chưa
    # bao giờ được canh** — ai vô tình xoá một mục thì cổng vẫn xanh. Đây đúng
    # bệnh vừa vá cho cổng 88 (170 -> 233) tuần này. NÂNG mốc = cổng CHẶT HƠN.
    # Mốc 36 -> 49 (26/08/2026): CA 7 MỚI — "hàm ghi file tiếng phải chịu được
    # đích đuôi `.mp3`". Đo ra **3/3 hàm HỎNG** trên đúng đường thật
    # (`giong_ngoai._ep_khung` phục vụ `ov:`+`cb:` · `giong_vieneu._ep_khung`
    # phục vụ `vn:`+`vnb:` · `giong_vbee._ghi_wav` phục vụ `vbee:`), cả ba đều
    # dẫn tới all-or-nothing -> lùi edge-tts = **chọn X ra Y**, `rc` vẫn 0.
    # Nó thuộc cổng NÀY vì mệnh đề trung tâm của cổng 63 đúng là "sót một cửa
    # là video LẪN HAI GIỌNG". THỬ PHÁ: gỡ `-f wav` khỏi cả ba -> **40 · 9**.
    ("63 biến thể giọng",   "_test_bien_the_giong.py",  49),
    ("62 quét cả khung",    "_test_toan_khung.py",      33),
    ("60 chữ theo lời",     "_test_chu_theo_loi.py",    42),
    ("59 đường dài",        "_test_duong_dai.py",       46),
    ("57 bảng tiến độ",     "_test_tg_bang_tiendo.py",  57),
    # Mốc 123 -> 132: thêm CA 25 **ĐOẠN CUỐI VIDEO** (9 mục), canh đúng lỗi anh
    # Hùng báo 20/08/2026 *"cứ đến gần cuối video nó k che mờ chữ gì cả"*. Gốc:
    # đường THAY TIẾNG làm chậm hình để khớp giọng bằng `-itsscale` — tuỳ chọn
    # ĐẦU VÀO, tức giãn TRƯỚC filter — nên `t` mà `enable='between(t,a,b)'` đọc
    # đã bị nhân k, còn hộp che thì dò trên video GỐC. Mọi khung có t > độ dài
    # GỐC rơi ra NGOÀI mọi cửa sổ enable = KHÔNG CHE GÌ; đuôi đó dài đúng
    # `(1 − 1/k)` clip (đo trên 4 file app đã xuất cho anh Hùng: **16,6%** với
    # k=1,1987 và **20,0%** với k=1,25, mật độ nét còn **98,2-101,2%** bản gốc).
    # CA 25 dùng nguồn 21 s — **CỐ Ý không chia hết cho `HOP_DOAN`=8** — và có
    # arm ĐỐI CHỨNG k=1,00 để mục chính không tự ĐẠT OAN.
    # Thử phá 2 phép (`_pha_che_chu.py`, mục `cuoi`): **BẮT 2/2**.
    ("56 che chữ",          "_test_che_chu.py",        132),
    ("55 thay giọng UI",    "_test_thay_giong_ui.py",   48),
    ("54 dubbing CJK",      "_test_dubbing_cjk.py",     44),
    ("53 thay giọng",       "_test_thay_giong.py",      44),
    ("52 CJK vá",           "_test_cjk_va.py",          46),
    ("52b mảnh cuối",       "_test_manh_cuoi.py",     None),
    ("31 nút không cụt",    "_test_nut_khong_cut.py", None),
    ("và/lỡ phụ đề",        "_test_va_lo_sub.py",       16),
    ("không popup",         "_test_no_popup.py",      None),
    ("làn cắt đói",         "_test_lane_starve.py",   None),
    ("smoke",               "_test_app_smoke.py",     None),
    # `_test_pipe_dialogs.py` là **CỬA CHẶN SỐ 3 của CLAUDE.md** ("mở MỌI hộp
    # thoại dây chuyền + bấm MỌI nút") mà nó **KHÔNG hề nằm trong danh sách
    # này** — tức mỗi lượt hồi quy "đủ 3 cửa chặn" từ trước tới nay chỉ chạy
    # được 2. Đúng bẫy cổng 70: cổng không ai gọi thì chỉ là một file .py nằm
    # đó. Nó cũng là cổng đã lôi ra lỗi "nút 📂 Mở thư mục log gọi
    # `os.startfile` nhảy Explorer trên máy anh Hùng", nên để nó ngoài danh
    # sách là bỏ luôn phép canh đó.
    ("cửa chặn: hộp dây chuyền", "_test_pipe_dialogs.py", None),
    # LƯỢT THỨ HAI của cổng 77, CỐ Ý đặt ở CUỐI. Lượt đầu chứng minh đĩa sạch
    # TRƯỚC khi chạy; lượt này quét lại sau khi **29 cổng vừa ghi ra `_kq_hq/`
    # và hàng loạt file tạm** — tức nó bắt được key do CHÍNH LƯỢT HỒI QUY NÀY
    # làm rơi ra, đúng kịch bản đã xảy ra hôm nay. Quét đĩa mất vài giây nên
    # chạy hai lượt gần như không tốn gì.
    ("77 không lộ key (lượt cuối)", "_test_khong_lo_key.py", 27),
]

#: Dòng tổng kết — mỗi cổng viết một kiểu, có cổng bỏ dấu tiếng Việt
#: ("DAT 42 · HONG 0"). Bắt hụt thì cột ĐẠT ra "?" và cổng bị gắn nhãn ĐÁNG
#: NGỜ oan; đã dính một lượt với cổng 60/63.
_RE_TK = re.compile(r"(?:ĐẠT|DAT|OK)\s+(\d+)\s*[·.]\s*"
                    r"(?:HỎNG|HONG|SAI)\s+(\d+)")

#: Mục cổng CỐ Ý KHÔNG CHẤM. Hiện chỉ cổng 56 có (CA17a/b/c đo THỜI GIAN, máy
#: bận thì `bo_qua()` — chấm ĐẠT là phát chứng nhận khống, chấm HỎNG là đỏ oan).
#: Không trừ phần này ra thì cổng 56 bị gắn nhãn "TỤT so mốc 123" MỖI LẦN máy
#: bận, và nhãn TỤT xuất hiện thường xuyên thì người ta thôi đọc nó — đúng cái
#: bẫy "cổng đỏ oan còn nguy hơn không có cổng" (bài học cổng 41 và 47).
_RE_BQ = re.compile(r"(?:BỎ QUA|BO QUA)\s+(\d+)")


def moi_truong() -> dict:
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["BQ_FFMPEG_SLOTS"] = "1"
    # KHÔNG dùng `main`: sau khi gộp thì mốc CHÍNH LÀ bản đang test -> cổng
    # đối chứng tự PASS OAN vĩnh viễn.
    #
    # VÌ SAO `v2.25.0` CHỨ KHÔNG `v2.26.0` (đã chạy nhầm một lượt, cổng bắt
    # được): mục CA23-3'' của cổng 56 đòi **bản mốc phải có TRƯỚC tính năng
    # che chữ** — không thì phép so "bật/tắt che chữ vẫn ra cùng dedup_key"
    # là so với chính tính năng đang test. Mà `che_chu` RA ĐỜI Ở v2.26.0
    # (`git show v2.25.0:app/services.py` có 0 dòng `che_chu`, v2.26.0 có 15).
    # Lấy v2.26.0 làm mốc -> CA23-3'' ĐỎ, và nó đỏ ĐÚNG: cổng đang báo mốc
    # không hợp lệ chứ không phải app hỏng. Mốc đúng = bản phát hành NGAY
    # TRƯỚC tính năng.
    e.setdefault("BQ_MOC_REF", "v2.25.0")
    return e


def main() -> int:
    env = moi_truong()
    print("=" * 78)
    print(f"HỒI QUY — {len(CONG)} cổng · BQ_MOC_REF={env['BQ_MOC_REF']}")
    print("=" * 78)
    kq = []
    for i_cong, (ten, f, moc) in enumerate(CONG):
        p = REPO / f
        if not p.exists():
            print(f"  {ten:<22} KHÔNG CÓ FILE {f}")
            kq.append((ten, f, -1, 0.0, None, None, moc, 0))
            continue
        t0 = time.time()
        r = subprocess.run([PY, "-u", str(p)], cwd=str(REPO), env=env,
                           capture_output=True, timeout=3600)
        gy = time.time() - t0
        out = (r.stdout or b"").decode("utf-8", "replace") + \
              (r.stderr or b"").decode("utf-8", "replace")
        (REPO / "_kq_hq").mkdir(exist_ok=True)
        # Tên log mang SỐ THỨ TỰ khi một file chạy nhiều lượt (cổng 77 chạy 2
        # lượt: đầu và cuối). Không có số thì lượt sau ghi đè lượt trước và mất
        # đúng cái log cần đọc.
        _lap = sum(1 for _, f2, _ in CONG if f2 == f) > 1
        _ten_log = f"{f}.{i_cong:02d}.txt" if _lap else f"{f}.txt"
        (REPO / "_kq_hq" / _ten_log).write_text(out, encoding="utf-8")
        m = None
        for m2 in _RE_TK.finditer(out):
            m = m2                            # lấy dòng tổng kết CUỐI CÙNG
        dat = int(m.group(1)) if m else None
        hong = int(m.group(2)) if m else None
        mbq = None
        for m3 in _RE_BQ.finditer(out):
            mbq = m3                          # dòng tổng kết CUỐI CÙNG
        bq = int(mbq.group(1)) if mbq else 0
        # So mốc theo ĐẠT + BỎ QUA: mục bỏ qua là mục KHÔNG CHẤM, không phải
        # mục mất đi. Vẫn in ra số bỏ qua để một lượt bỏ qua không bao giờ
        # trông giống một lượt chấm đủ.
        kq.append((ten, f, r.returncode, gy, dat, hong, moc, bq))
        co = "" if moc is None or dat is None else (
            "  (mốc %d)" % moc if dat + bq >= moc else "  << TỤT so mốc %d" % moc)
        if bq:
            co = f"  · BỎ QUA {bq}{co}"
        print(f"  {ten:<22} rc={r.returncode:<3} {gy:6.1f}s  "
              f"ĐẠT {dat if dat is not None else '?':>4} · "
              f"HỎNG {hong if hong is not None else '?':<4}{co}")

    print("=" * 78)
    do = [k for k in kq if k[2] != 0]
    ngo = [k for k in kq if k[2] == 0 and (k[4] is None or k[3] < 0.3)]
    print(f"ĐỎ: {len(do)} cổng" + (f" -> {[k[0] for k in do]}" if do else ""))
    if ngo:
        print(f"ĐÁNG NGỜ (rc=0 mà không thấy dòng tổng kết / chạy <0,3s): "
              f"{[k[0] for k in ngo]}")
    tut = [k[0] for k in kq
           if k[6] and k[4] is not None and k[4] + k[7] < k[6]]
    if tut:
        print(f"TỤT SỐ MỤC so với mốc: {tut}")
    bqua = [(k[0], k[7]) for k in kq if k[7]]
    if bqua:
        print(f"MỤC KHÔNG CHẤM (máy bận, không phải ĐẠT cũng không phải "
              f"HỎNG): {bqua}")
    return 1 if do else 0


if __name__ == "__main__":
    raise SystemExit(main())
