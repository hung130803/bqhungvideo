# BQ Hung Video — tool CẮT clip viral tự động (PyQt6 + ffmpeg + Groq)

- **ĐỌC `INTEGRATION.md` TRƯỚC KHI SỬA DÂY CHUYỀN** — repo này là 1 nửa của
  dây chuyền với tool tải "bqhungdown" (`C:\Users\Admin\Downloads\prodowwn`).
- Chạy từ nguồn: `.venv\Scripts\python main.py` · Phát hành: bump
  `app/version.py` → commit "Phát hành vX.Y.Z" → push main → tag `vX.Y.Z`
  (GitHub Actions build exe). KHÔNG bump/tag khi user chưa duyệt — máy nhân
  viên tự cập nhật theo release.
- **CỬA CHẶN TRƯỚC MỖI LẦN PHÁT HÀNH — chạy đủ 3 cái, không được bỏ:**
  1. `.venv\Scripts\python -m pyflakes app config.py main.py` → **KHÔNG được
     còn dòng "undefined name"**. `studio_page.py` import CỤC BỘ TỪNG HÀM, nên
     dùng tên đã import ở hàm khác sẽ nổ NameError CHỈ KHI bấm nút —
     `compileall` và import-module đều KHÔNG bắt được (lỗi thật v2.5.0: bấm
     🗑 Thùng rác nổ `NameError: NoWheelComboBox`, đã ra tới máy user).
  2. `_test_app_smoke.py` → dựng cửa sổ chính THẬT, đổi mọi combo/spin, **bấm
     mọi nút ở mọi trang + mọi hộp thoại** (66 nút), chạy 40 nhịp poll.
     Nó TỰ KIỂM bản vá của chính nó trước khi chạy — nếu QColorDialog/
     QFileDialog chưa bị vô hiệu thì dừng ngay (exit 2), vì hộp thoại thật sẽ
     treo test và làm tưởng app crash.
  3. `_test_pipe_dialogs.py` → mở MỌI hộp thoại dây chuyền + bấm MỌI nút.
  4. `_test_pipe_overlap.py` → 10 ca chồng lượt / hồi phục / gốc kẹt.
  5. `_test_lane_starve.py` → làn CẮT không bị làn PHÂN TÍCH bỏ đói. Bộ điều
     phối lấy job theo TỪNG LÀN riêng; gộp 1 query `LIMIT 50` là job xuất
     (priority 3) chết đói khi ≥50 job phân tích (priority 10) đang chờ.
  6. `_test_cancel_persist.py` → HUỶ LÀ HUỶ: bấm Huỷ lúc job đang chạy rồi
     tắt app/cập nhật, mở lại KHÔNG được tự chạy lại (cờ huỷ phải bền
     `jobs.cancel_req`; hồi phục dây chuyền phải trả dòng sổ cho job huỷ).
  7. `_test_ai_gate.py` → video dây chuyền ra "Cắt cơ bản" phải THỬ LẠI 1 lần
     rồi mới xuất; lần 2 vẫn cơ bản thì đóng dấu `[CƠ BẢN]` vào sổ.
  8. `_test_chan_search.py` → ô Kênh gõ-để-tìm không phá `_on_proj`.
  9. `_test_db_corrupt_guard.py` → **DB VỠ KHÔNG ĐƯỢC LÀM APP ĐƠ**. Đo thật
     30/07 trên máy user: studio.db malformed nhưng không ai ngắt → app đọc
     đĩa **24,7 MB/s + 6.176 lệnh/s + ~50% CPU lúc ĐỨNG YÊN**. Nay `db.query`
     phát hiện malformed → `corrupt_live=True` → trả rỗng NGAY (đo: 6.000 truy
     vấn = 0 ms), UI dừng poll + báo "khởi động lại app để tự chữa".
- Quy tắc sắt: test bằng THÀNH PHẦN THẬT (LLM/ffmpeg/DB thật — mock từng giấu
  bug); đường ghép đoạn phải test thứ tự hook-first (ngược thời gian) + nguồn
  VFR; key API chỉ qua ENV, không ghi file, kiểm `git diff | grep gsk_` trước
  commit.
- Test sandbox: đặt env `BQ_DB_PATH` + `BQ_DATA_DIR` sang thư mục tạm để không
  đụng dữ liệu thật (`%LOCALAPPDATA%\BQHungVideo` là data bản đóng gói).
- Chủ app: BQ Hung — trao đổi tiếng Việt; báo cáo phải kèm số đo thật.
