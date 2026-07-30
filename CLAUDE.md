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
  6. `_test_shutdown_safety.py` → LUỒNG NỀN KHÔNG ĐƯỢC LÀM SẬP APP: mọi emit
     từ thread phải qua `shutdown.safe_emit`, closeEvent bật `set_closing()`
     TRƯỚC khi phá widget, main.py thoát bằng `os._exit` (không finalize
     interpreter khi luồng daemon còn chạy) + bật faulthandler ghi
     `logs/crash_native.txt`. Gốc: crash 0xc0000005 8 lần 28-30/07/2026.
  7. `_test_cancel_persist.py` → HUỶ LÀ HUỶ: bấm Huỷ lúc job đang chạy rồi
     tắt app/cập nhật, mở lại KHÔNG được tự chạy lại (cờ huỷ phải bền
     `jobs.cancel_req`; hồi phục dây chuyền phải trả dòng sổ cho job huỷ).
  8. `_test_ai_gate.py` → video dây chuyền ra "Cắt cơ bản" phải THỬ LẠI 1 lần
     rồi mới xuất; lần 2 vẫn cơ bản thì đóng dấu `[CƠ BẢN]` vào sổ.
  9. `_test_chan_search.py` → ô 🔎 LỌC kênh: combo Kênh phải GIỮ NGUYÊN là
     danh sách bấm mở (v2.6.10 tôi biến nó thành ô-gõ editable => anh Hùng mất
     danh sách + không thấy tên kênh: "này k mở được"). Bất biến: lọc KHÔNG
     ĐƯỢC đổi kênh đang làm; kênh đang chọn luôn còn trong danh sách.
  10. `_test_reanalyze_clean.py` → PHÂN TÍCH LẠI phải ra ĐÚNG số part user
     đặt: clip lần trước ĐÃ XUẤT phải vào kho `status='archived'` (không xoá,
     giữ export_path + tính là "đoạn đã dùng"), `list_clips` bỏ archived. Gốc
     lỗi 30/07: đặt 3 part ra 7-8 part + lẫn clip "Cắt cơ bản" không tiêu đề.
     Kèm canh main.py không lấy `sys.stdout.flush` ngoài try (bản .exe
     windowed có stdout=None -> hộp lỗi mỗi lần tắt app).
  11. `_test_quota_wait.py` → HẾT LƯỢT thì ĐỢI, KHÔNG cắt cơ bản: dây
     chuyền 3 luồng AI nuốt lượt → có lúc cả 27 key cùng cooldown →
     complete_text bỏ cuộc ≤45s → heuristic (bấm tay vài phút sau lại chạy —
     ảnh đối chứng 30/07). `m1._call_waiting_quota` đợi theo
     soonest_ready_wait (ngân sách AI_QUOTA_WAIT_SEC=15ph), ngủ nhịp 5s có
     kiểm HUỶ; lỗi khác/hết ngân sách mới rơi heuristic.
  12. `_test_db_corrupt_guard.py` → **DB VỠ KHÔNG ĐƯỢC LÀM APP ĐƠ**. Đo thật
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
