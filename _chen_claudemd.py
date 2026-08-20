"""CHÈN một khối mới vào CLAUDE.md — CHỈ CHÈN, không ghi lại cả file.

Luật của repo: có phiên khác chạy song song, nên ghi lại cả file là đè mất khối
người khác vừa thêm. Script này tìm một dòng NEO DUY NHẤT rồi chèn TRƯỚC nó.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[union-attr]

P = Path(__file__).resolve().parent / "CLAUDE.md"
NEO = ("- **GIỌNG KOKORO ĐÃ NỐI VÀO UI + ĐO CẢ 28 GIỌNG "
       "(v2.41.0, 20/08/2026).**")

KHOI = """- **NHÂN BẢN GIỌNG: CHUỖI ĐÃ NỐI XONG + BẮT ĐƯỢC MỘT BÁO ĐỘNG GIẢ ĐẮT
  (20/08/2026).** Yêu cầu gốc của anh Hùng: *"làm nốt đi, làm sao máy khác tôi
  cập nhật là được tích hợp hết vào"*.
  **VIỆC 1 — cổng 88 mục 8d đỏ KHÔNG PHẢI vì hai mục cổng xung đột.** Lượt
  trước kết luận mục **7c** (nhãn nêu đích danh gói thiếu) và mục **8d** (nhãn
  dưới 132 ký tự) *"không thể cùng đúng"* rồi tụt về đếm số. **Kết luận đó
  SAI.** `nhan()` đo **CHUỖI CỦA CHÍNH NÓ** (110 ký tự, dưới trần 130) nhưng
  dòng người dùng THẤY là dòng **SAU `giong_bang.gom_nhom`**, và `gom_nhom` dán
  thêm **46 ký tự** -> **156**. Hai chỗ đo HAI CHUỖI KHÁC NHAU nên cái trần
  trong `nhan()` **không bao giờ bập được**.
  46 ký tự đó còn **SAI SỐ**: `" · miễn phí, cần tải bộ 250 MB"` — 250 MB là bộ
  giọng VieNeu (máy phải có sẵn mới tạo nổi giọng nhân bản), còn thứ đang thiếu
  là phần nhân bản **126,3 MB (CPU) / 2.485,6 MB (CUDA)**. Đúng lớp lỗi cổng 58
  (*"nút ghi 155 MB rồi hộp doạ 2 GB"*).
  Vá: `giong_bang.dong_day_du()` = **MỘT phép dựng 4 đuôi**, `gom_nhom` và mọi
  module muốn tự đo đều gọi CHUNG (hai bản sao là hai chỗ để lệch nhau); `nhan()`
  tự viết `"miễn phí, cần tải <ĐÚNG THỨ>"` nên `_DO_TRUNG[VIENEU]` làm đuôi cũ
  tự thôi dán. **Giữ CẢ HAI bất biến cổng 79 CA 6** (mọi dòng nói TIỀN · giọng
  phải-tải nói việc TẢI) — bỏ một trong hai chữ là cổng 79 **đỏ ngay**, đã đo:
  **91 · 2**. Kết quả: 8d còn **109 ký tự**, 7c vẫn nêu đích danh, **không mục
  nào phải nhường**.
  **VIỆC 2 — VÒNG TỰ DÒ.** `cai_nhan_ban()` sau hậu kiểm tĩnh **ĐỌC THẬT** một
  câu qua đường nhân bản (`voice=""` + `ref_audio=<WAV tự sinh 4 s bằng
  ffmpeg>`; `duration=` nằm TRONG biểu thức lavfi, **cố ý không dùng `-t`** —
  bài học đầy ổ C 420 GB). Hỏng với `No module named 'X'` -> bóc `X`, cài vào
  **đúng venv đang chạy**, thử lại. **Trần 6 vòng** + ghi log TỪNG VÒNG; hết
  trần -> `ok=False` nêu rõ còn thiếu `X`. Danh sách **CHẶN** (`gradio` ·
  `lmdeploy` · `llama-cpp-python` · `triton*` · `PyMuPDF`) có nêu lý do. Tên bóc
  từ lời lỗi chỉ nhận `[A-Za-z0-9_\\-]+` — lời lỗi là chuỗi từ **tiến trình
  con**, đưa thẳng vào dòng lệnh pip là một cửa tiêm lệnh.
  **BẰNG CHỨNG CUỐI CÙNG LÀ `do_wav()` — độ dài + RMS, đọc mẫu THẲNG.**
  `doc_loat` trả True chỉ nghĩa là *"tiến trình chạy xong, file tồn tại"*, cùng
  khoảng cách đã cho ffmpeg trả mã 0 với file 0 KiB.
  **VIỆC 3 — NÚT TẢI BỘ VieNeu, ca thứ SÁU của "hàm xong ≠ tính năng xong".**
  `grep -rn "cai_vieneu" app/ui/` -> **0 dòng** (và `NHAN_TAI` cũng là hằng
  CHẾT, 0 nơi đọc), nên máy chưa có VieNeu thì nút nhân bản chỉ ghi *"Chưa có bộ
  giọng VieNeu — tải bộ đó trước"* mà **không có chỗ nào để bấm**. Nay có hàng
  **BƯỚC 1/2** trong hộp «Giọng của tôi»: nút bám **`thieu`** (không bám `co` —
  bám `co` thì máy dev nút BIẾN MẤT và bản `.exe` mãi mãi không có đường tải) ·
  thiếu Python 3 -> **khoá VÀ in lý do** · bộ dò NÉM -> hộp không chết và
  **nghiêng về HIỆN nút** · tiến độ qua **dict RIÊNG** `_buoc_vieneu` + nhánh
  riêng trong `_nhip` (thread nền KHÔNG đụng widget) · hộp xác nhận nói **CẢ HAI
  bước + tổng dung lượng** rồi bước 2 **tự chạy** (`da_dong_y=True`, mặc định
  vẫn False) · **CỐ Ý KHÔNG** gọi `_dung_combo_giong()`.
  **PHÁT HIỆN ĐẮT NHẤT CỦA LƯỢT NÀY — BÁO ĐỘNG GIẢ, và nó ngược dự đoán.**
  `_do_may_trang.py` đọc thật trên `_giong_vieneu/venv` (vieneu 3.2.8):

  | | trước khi thu gọn | sau |
  |---|---|---|
  | `thieu_de_nhan_ban()` | `[transformers, neucodec, accelerate]` | `[]` |
  | ĐỌC THẬT | **WAV 2,32 s · RMS 0,09761** | 2,56 s · RMS 0,07506 |
  | bất biến hai chiều | **VỠ** | **GIỮ** |

  Kiểm tận gốc: cả ba gói **KHÔNG CÓ THẬT** (`import` -> `ModuleNotFoundError`,
  không thư mục lẫn `.dist-info`) mà đường nhân bản **VẪN RA TIẾNG**. Tức chúng
  là phụ thuộc **KHAI BÁO của gói** (`importlib.metadata.requires("vieneu")` =
  21 tên), **không phải** phụ thuộc của một lượt ĐỌC. Giá của báo động giả, đo
  được: trên đúng cái máy nhân bản ĐƯỢC, dòng combo ghi *"CHƯA CHẠY ĐƯỢC"* và
  nút mời tải **2.485,6 MB** (máy anh Hùng có RTX 3060 nên mặc định đi CUDA) cho
  thứ **KHÔNG CẦN**.
  **NHƯNG ĐỪNG KẾT LUẬN "ba gói đó vô dụng":** log máy anh Hùng có THẬT dòng
  `ModuleNotFoundError: No module named 'transformers'` từ chính đường nhân bản.
  Nhu cầu ấy CÓ THẬT ở môi trường đó mà KHÔNG có ở đây — nghi do **MODEL đã
  cache** nên lượt đọc đi nhánh nhẹ hơn, **CHƯA TRUY RA, đừng ghi như đã biết**.
  ⇒ **Danh sách TĨNH không nói thật được ở CẢ HAI CHIỀU** (ở đây báo thiếu oan,
  ở máy anh Hùng báo đủ oan). Nên `_CAN_CHO_NHAN_BAN` chỉ giữ **mức tối thiểu ĐÃ
  ĐO là bắt buộc** = `("torch", "torchaudio")`, còn *"còn thiếu gì nữa"* là việc
  của VÒNG TỰ DÒ. **Thêm tên vào danh sách đó là quay lại lối ĐOÁN.**
  **VIỆC 4 — `%TEMP%`: CHỌN KHÔNG TỰ DỜI, NÓI THẲNG.** Máy này `%TEMP%\\
  bq_giong8` có **43.836 file / 4.949 MB** và python còn chạy được. Một lượt
  robocopy + chạy thật + đổi tên + xoá trên 4,95 GB là việc dài và nặng đĩa,
  **không được chạy ngầm trong một hộp thoại**. Hai bảo đảm tối thiểu thì ĐÃ ĐO:
  `cai_vieneu()` dựng venv ở **chỗ CHUẨN** `thu_muc_vieneu()/venv` (cổng 15e) và
  `_ung_vien_python()` đặt `%TEMP%` **CUỐI** danh sách (cổng 15f: chuẩn ở chỉ số
  0-1, tạm ở 2-3). Thêm được một thứ thật: cảnh báo `%TEMP%` nay **HIỆN RA TRÊN
  UI** kể cả khi `thieu` rỗng (cổng 15g + phép phá 30), thay vì chỉ ghi log rồi
  vẫn chạy — `o_tam` vẫn để **khoá RIÊNG**, không gộp vào `thieu` (máy vẫn chạy
  được, gộp là nhãn/nút báo sai trạng thái).
  **CỔNG 88 `_test_giong_toi.py`: 104 -> ĐẠT 164 · HỎNG 0** (CA 13 vòng tự dò ·
  CA 14 nút bộ VieNeu · CA 15 `%TEMP%`). Thử phá `_pha_giong_toi.py`: 20 -> **30
  phép · BẮT 30 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
  **BA LỖI CỦA CHÍNH CỔNG, thử phá tự bắt ra — đọc kẻo lặp:** (a) mục 12d hỏi
  *"`--ignore-installed` có trong THÂN hàm không"*; từ khi `cai_nhan_ban` có
  **lệnh pip THỨ HAI** (vòng tự dò) thì mục đó **mất răng** — gỡ cờ khỏi lệnh
  CHÍNH mà lệnh kia vẫn còn cờ nên mục vẫn ĐẠT, đo được phép phá 11 từ BẮT thành
  **LỌT**; nay có 12d'' đòi **MỌI** danh sách lệnh có `"install"` đều mang cờ
  (2/2). (b) mục 14i hỏi *"chuỗi `da_dong_y` có trong file không"* — chuỗi đó còn
  nằm ở chính `def _tai_nhan_ban(self, da_dong_y=...)` nên gỡ **LỜI GỌI** mà mục
  vẫn xanh (phép phá 28 LỌT); nay hỏi trong THÂN `_tai_vieneu_xong`. (c) mục 13m
  áp `ma_pip=1` cho **cả** lệnh cài chính -> `cai_nhan_ban` chết ngay bước 1 và
  lời lỗi nêu `accelerate` (gói CUỐI danh sách chính) chứ không phải gói tự dò
  -> mục ĐỎ vì **lỗi của phép thử**.
  Phép phá 21 **CỐ Ý gỡ HAI chốt**: hai lớp lọc tên gói (char class của
  `_RE_THIEU` + `fullmatch` sau `split(".")`) **thừa nhau có chủ đích**, gỡ MỘT
  lớp thì lớp kia vẫn chặn sạch -> cổng XANH ĐÚNG mà bảng đọc thành "LỌT" oan
  (đúng bẫy LUẬT 3 của file đó). Đánh đổi ĐÃ BIẾT: hai lớp thừa nhau rẻ hơn một
  lớp có cổng canh.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa chạy `cai_nhan_ban()` THẬT từ đầu** trong lượt
  này (venv repo đã đủ torch nên không có gì để cài; vòng tự dò được chấm bằng
  **pip GIẢ + `_chay_vieneu` GIẢ**, không phải một lượt tải thật) · **chưa ai
  bấm nút bộ VieNeu trên một máy TRẮNG thật** — hộp được dựng thật và nút được
  hỏi thật ở cổng 88 CA 14, nhưng `cai_vieneu()` chưa chạy hết một lượt trong
  lượt này · **chưa tải thật bản CUDA** (2.485,6 MB, vẫn chỉ `--dry-run` +
  HTTP HEAD) · **chưa ai NGHE bằng tai** giọng nhân bản (`do_wav` trả lời "có
  tiếng", KHÔNG trả lời "có giống người đó") · `MB_VIENEU = 250.0` là số **tài
  liệu**, chưa đo lại bằng `--dry-run --report` cho `vieneu==3.2.8` · chưa truy
  ra vì sao máy anh Hùng cần `transformers` mà máy này không · **chưa dời**
  `%TEMP%\\bq_giong8` (4,95 GB) đi đâu cả.
"""


def main() -> int:
    s = P.read_text(encoding="utf-8")
    n = s.count(NEO)
    print(f"neo xuất hiện {n} lần")
    if n != 1:
        print("DỪNG: neo phải DUY NHẤT (luật chèn CLAUDE.md)")
        return 1
    if "BÁO ĐỘNG GIẢ ĐẮT" in s:
        print("DỪNG: khối này đã có rồi, không chèn hai lần")
        return 1
    truoc = len(s)
    s = s.replace(NEO, KHOI + NEO, 1)
    P.write_text(s, encoding="utf-8")
    print(f"ĐÃ CHÈN {len(s) - truoc} ký tự (chỉ CHÈN, không ghi lại cả file)")
    return 0


raise SystemExit(main())
