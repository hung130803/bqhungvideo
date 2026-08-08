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
  9. `_test_chan_search.py` → TÌM KÊNH, đã sai 2 lần, đừng lặp: v2.6.10 biến
     combo thành ô-gõ => mất danh sách bấm mở ("này k mở được"); v2.6.12 tách ô
     "Lọc kênh" rời => chỉ lọc TRONG NHÓM đang chọn nên gõ tên kênh nhóm khác
     không ra ("có hoạt động đâu"). ĐÚNG (v2.6.18): bấm combo -> popup
     [ô tìm + danh sách] (`_open_chan_picker`); gõ -> `services.search_channels`
     tìm TRÊN MỌI NHÓM, nhãn ghi "· nhóm X"; chọn kênh nhóm khác thì
     `_select_project` tự đổi nhóm. Enter = chọn dòng đầu.
     v2.6.21: popup KHÔNG được dùng kiểu `Qt.WindowType.Popup` — kiểu đó Qt
     TỰ ĐÓNG khi mất focus (anh Hùng: sang trình duyệt rồi quay lại là mất
     danh sách). Phải là `Tool | FramelessWindowHint` (đi theo app, không tự
     đóng), đóng bằng chọn kênh / nút ✕ / Esc. LƯU Ý KHI TEST: `Qt.Tool =
     Popup | Dialog` nên bit Popup LUÔN có — phải so KIỂU
     `flags & WindowType_Mask`, đừng so bit. Mỗi dòng có nút 📋 copy TÊN GỐC
     (không kèm STT/đuôi trạng thái), bấm copy KHÔNG đổi kênh + KHÔNG đóng.
     v2.6.22: **NÚT TRONG POPUP PHẢI LÀ CHỮ, KHÔNG EMOJI** — máy anh Hùng
     thiếu glyph 📋/✕ nên nút ra Ô ĐEN trơ ("xấu quá tự nhiên có cái ô đen").
     Dùng "Copy" / "Đóng" + style rõ (viền + chữ màu accent). Cổng test 9 có ca
     quét mọi QPushButton trong popup, thấy emoji dễ-thiếu-font là FAIL.
     v2.6.23 — 2 BÀI HỌC LỚN:
     (a) **TEST UI PHẢI ÁP QSS THẬT** `qapp.setStyleSheet(theme.QSS)`. QSS chung
     có `QListWidget::item{padding:9px 10px;margin:2px}` — với dòng dùng
     `setItemWidget` nó BÓP widget con còn ~0 => DÒNG TRỐNG TRƠN trên máy user
     mà test không QSS vẫn PASS (lỗi thật v2.6.22). Nay cổng 9 áp QSS + SOI
     PIXEL (render viewport ra QImage, đếm màu trong dòng đầu >= 3) + kiểm
     chiều cao dòng/nhãn. Dòng phải tự đặt `setSizeHint(QSize(10, >=32))`.
     (b) Đóng danh sách = nút Đóng · Esc · BẤM RA NGOÀI bất cứ đâu trong app
     (event filter MouseButtonPress trên QApplication; bỏ qua cú bấm vào chính
     combo — combo tự bật/tắt). Cửa sổ vẫn KHÔNG tự đóng khi app mất focus.
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
  12. `_test_clip_count_len.py` → ĐÚNG SỐ PART + ĐÚNG ĐỘ DÀI: (A) chốt cứng
     `ai_clips = ai_clips[:count]` trước vòng lưu — fail-safe refine (JSON hỏng
     giữ nguyên list) từng để lọt 5-6 part khi đặt 3. (B) trong vòng lưu, gọi
     `_trim_junk_edges` TRƯỚC rồi `_enforce_len` SAU (cả đường AI lẫn
     heuristic) — trước đây enforce nới lên 60s xong trim cắt tụt <60s. enforce
     phải là NGƯỜI NÓI CUỐI về độ dài. Gốc 30/07: đặt 60-80s/3part ra 5-6 part
     dưới 60s.
  13. `_test_reanalyze_basic.py` → 🔁 QUÉT MỌI KÊNH tìm video lỡ 'Cắt cơ
     bản' rồi phân tích lại AI. `services.find_basic_cut_videos(grp)`: video
     có clip hiện (không archived) mà KHÔNG clip nào llm_used=True; cờ exists
     phân biệt còn-gốc / đã-xoá. `pipeline.index_recycled`: chỉ mục Thùng rác
     theo tên file để khôi phục video đã xoá. Nút ở dialog 🤖 Dây chuyền.
  14. `_test_ui_smooth.py` → MƯỢT + KHÔNG ĐỨNG IM. (A) `_poll_tick` chỉ được
     dừng HẲN khi `_modal_busy` (hộp chọn file native); khi có QDialog modal
     (vd 🤖 Dây chuyền mở bằng exec) vẫn PHẢI chạy `_check_auto_export` +
     `_pipe_poll` — ĐO TRƯỚC SỬA: 0/2 nhịp => "bấm chạy mà không chạy, phải X
     dialog nó mới chạy". (B) 1 clip đổi trạng thái -> `_rows_in_place` thay
     ĐÚNG dòng đó, giữ nguyên widget thanh tiến trình (trước: đập cả danh sách
     9,1ms + bar bị xoá/tạo lại => "mất rồi lại có"). Ngân sách: poll < 30ms
     với 100 kênh (đo 0,59ms).
  15. `_test_db_corrupt_guard.py` → **DB VỠ KHÔNG ĐƯỢC LÀM APP ĐƠ**. Đo thật
     30/07 trên máy user: studio.db malformed nhưng không ai ngắt → app đọc
     đĩa **24,7 MB/s + 6.176 lệnh/s + ~50% CPU lúc ĐỨNG YÊN**. Nay `db.query`
     phát hiện malformed → `corrupt_live=True` → trả rỗng NGAY (đo: 6.000 truy
     vấn = 0 ms), UI dừng poll + báo "khởi động lại app để tự chữa".
  16. `_test_tpl_per_channel.py` → MẪU RIÊNG THEO KÊNH (`projects.tpl_name`).
     Bất biến: kênh CÓ gán -> dùng đúng mẫu đó; CHƯA gán -> mẫu đang chọn (y
     như cũ); mẫu bị XOÁ -> lùi mẫu đang chọn, KHÔNG chết dây chuyền (vẫn giữ
     tên trong DB + hiện ⚠ trong ô chọn để user sửa); `_tpl_for_project` luôn
     trả BẢN SAO (sửa nó không hỏng mẫu app); job đã chốt mẫu thì đổi mẫu sau
     KHÔNG ảnh hưởng. Bảng dây chuyền 9 cột — cột 4 = "Mẫu".
     v2.6.25 (anh Hùng: "giờ tôi bấm từng kênh thì chết gần 200 kênh cơ nó
     toàn chưa chọn"): (a) nhãn ô chọn phải là `(mẫu đang chọn: <TÊN>)` — ghi
     "(mẫu đang chọn)" trơn thì user tưởng kênh CHƯA có mẫu; (b) phải có đường
     GÁN 1 LƯỢT: `_pipe_bulk_tpl` (menu 🔧 + bấm tiêu đề cột "Mẫu") ->
     `_pipe_apply_tpl_all` chỉ đụng kênh ĐANG HIỆN, lấy pid từ BẢNG
     (`_pipe_rows_pid`) nên tự tôn trọng nhóm + ô tìm; sau khi gán phải gọi
     `self._pipe_fill()` để bảng hiện mẫu mới ngay. Ca test bắt buộc: Huỷ ở
     hộp chọn · No ở hộp xác nhận · kênh bị lọc ra KHÔNG bị đụng.
  17. `_test_no_popup.py` + `_test_guard.py` → **TEST KHÔNG ĐƯỢC ĐỤNG MÁY
     USER**. Lỗi thật 31/07/2026 (anh Hùng: "sao mỗi lần tôi yêu cầu bạn làm
     hay hỏi gì cái thư mục kia đều nhảy lên là sao thế rất nhiều lần" + ảnh
     Explorer `%TEMP%\pipe_dlg_xxxx\logs`): `_test_pipe_dialogs.py` bấm MỌI nút
     hộp 🤖 Dây chuyền, trong đó nút "📂 Mở thư mục log" gọi `os.startfile` mà
     file test đó KHÔNG vá — `_test_app_smoke.py` có vá nhưng vá RIÊNG nên test
     khác không thừa hưởng. Nay MỌI test dựng UI/bấm nút PHẢI
     `import _test_guard` (cổng 17 quét tĩnh, thiếu là FAIL). Guard chặn
     os.startfile · webbrowser · QDesktopServices · Popen/run khi lệnh là
     explorer/start/cmd/powershell/ffplay…, nhưng CHO QUA ffmpeg (quy tắc sắt:
     thành phần thật). 2 BẪY ĐÃ SẬP, đừng lặp: (a) guard KHÔNG được tự import
     PyQt6 lúc nạp — repo cần cv2 (app.queue.jobs) nạp TRƯỚC Qt, nên vá
     QDesktopServices phải hoãn tới `tu_kiem()`; (b) đo "có cửa sổ bật lên
     không" phải đếm CỬA SỔ qua COM `Shell.Application` và gọi bằng
     `_test_guard.chay_that` — đếm tiến trình explorer.exe là kiểm hớ (Windows
     dùng chung 1 tiến trình) còn `subprocess.run` thì bị chính guard nuốt (đo
     ra -1). Guard cũng tự dọn `%TEMP%` của lần chạy trước (đo lần đầu: 189 thư
     mục / 158 MB rác trên ổ C từng đầy 100%) và ép stdout utf-8.
  18. `_test_don_rac.py` → **APP PHẢI TỰ DỌN RÁC ĐĨA + GẤP WAL KHI THOÁT**.
     Đo thật 31/07/2026 (ổ C còn 3,19/926 GB): `%TEMP%` 11,6 GB, trong đó
     `_MEI*` **4,69 GB / 339 mục** — KHÔNG phải app ghi mà là **yt-dlp bản
     onefile** tự giải nén ~22 MB mỗi lần chạy, chỉ dọn khi thoát êm; huỷ
     tải/đóng app là bỏ lại. Cộng `_seg_*.mkv` **1,71 GB** (mảnh ghép đoạn,
     `finally` không chạy vì app thoát bằng `os._exit`). Dọn xong: 10,94 GB
     (+7,75 GB). Nay `app/core/tempsweep.py` chạy ở luồng nền 5s sau khi mở
     app; yt-dlp con được truyền `env` với TEMP trỏ vào `DATA_DIR/_ytdlp_temp`
     nên rác gom 1 chỗ. BẤT BIẾN: chỉ xoá tên khớp danh sách, BỎ QUA mọi thứ
     mới hơn 2h (đang tải/đang xuất), bỏ qua `sys._MEIPASS` của chính mình, bị
     khoá thì im lặng, KHÔNG BAO GIỜ ném lỗi. Giữ 3 bản `studio_*.db`, log 14
     ngày, `error.log` ≤ 2 MB (giữ ĐUÔI).
     Kèm `db.gap_wal()` gọi trong bước thoát: `os._exit` khiến SQLite không bao
     giờ checkpoint → đo thật studio.db 80 KB / WAL 1,78 MB tồn từ 06/07, sao
     lưu file .db thiếu WAL thì **chỉ có 93/201 dòng** (máy anh Hùng báo
     'malformed' khi đọc từ ngoài). Cách kiểm ĐÚNG: copy riêng file .db (không
     kèm -wal) rồi đếm dòng.
  19. `_test_tpl_export_path.py` → **MẪU THEO KÊNH PHẢI ĐÚNG TỚI PAYLOAD
     ffmpeg, quy mô 200 KÊNH**. Cổng 16 chỉ kiểm tới `_tpl_for_project` (cửa
     "chốt mẫu"); cổng này chặn `services.enqueue_export` và đọc
     `cap_style["font"]` — đúng thứ ffmpeg vẽ. 4 LỖI THẬT tìm được 31/07/2026
     khi anh Hùng yêu cầu rà lại ("chạy hàng loạt 200 kênh, đừng để lỗi đến lúc
     xuất"):
     (a) mẫu-theo-kênh CHỈ áp ở đường dây chuyền tự động (caller tự đổi
     `self.layout_tpl`); **bấm tay 'Xuất video này' / 'Xuất cả kênh' / xuất lại
     1 Part vẫn ăn mẫu TRANG CHÍNH** → kênh đã gán vẫn ra clip sai mẫu.
     (b) đổi `layout_tpl` ở CALLER nên lượt xuất chen ngang (vòng lặp sự kiện
     lồng) trộn mẫu giữa 2 kênh.
     (c) mẫu đã gán bị XOÁ/đổi tên → âm thầm lùi mẫu, không một dòng báo.
     (d) `save_template` KHÔNG cắt khoảng trắng còn `set_project_template` thì
     CÓ → mẫu tên ' mẫu A ' gán thành 'mẫu A' → tra không thấy → rơi mẫu chính.
     SỬA GỐC: việc chọn mẫu nằm TRONG `_export_video(video_id, only_clip_id,
     tpl=None)` — cửa duy nhất mọi đường xuất đi qua; `tpl` != None = mẫu ĐÃ
     CHỐT lúc xếp job; thân cũ đổi tên `_export_video_inner`. Thêm
     `_canh_bao_mau_mat` (báo 1 lần/kênh vào status + báo cáo dây chuyền);
     `get_template`/`delete_template` so `TRIM(name)=TRIM(?)` để mẫu cũ lưu kèm
     khoảng trắng vẫn tra ra. LƯU Ý: stub `_export_video` trong test khác PHẢI
     nhận `tpl=None`, thiếu là lượt xuất nổ TypeError. Ngân sách đo: 200 kênh
     xuất loạt < 20s (đo 0,0s), mở hộp dây chuyền 212 dòng < 4s (đo 1,5s).
  20. `_test_db_maint.py` → **DỌN BẢN CHÉP LỜI KHÔNG ĐƯỢC LÀM MẤT VIỆC USER**.
     Đo 02/08/2026: `analysis.data` = **378 KB/video, giữ MÃI MÃI** (99% chỗ
     trong DB; clips.signals 0,4 KB · jobs 1,0 KB · pipeline_files 0,1 KB) →
     ~100 video/ngày = +37 MB/ngày ≈ **13 GB/năm**, và DB phình là đúng đường
     dẫn tới vỡ DB khi ổ đầy. NHƯNG `m1_highlight.py:2820` lấy `words` TỪ
     analysis['transcript'] để VẼ PHỤ ĐỀ **lúc xuất clip** → xoá bừa = "Xuất
     lại" clip cũ ra clip KHÔNG PHỤ ĐỀ (tôi đã suýt làm, phải đọc code trước).
     Nên `dbmaint.don_chep_loi_cu` chỉ dọn video **mất gốc trên đĩa** + không
     còn clip `suggested` + clip mới nhất quá 30 ngày; sao lưu DB trước lượt
     đầu; chỉ xoá `kind='transcript'` (scenes/faces/audio nhẹ → giữ).
     **BẪY ĐÃ SẬP 1 LẦN:** `clips.created_at` khai TEXT nên số ghi vào thành
     chuỗi '1785000000.0'; bản đầu parse lỗi → trả 0.0 → điều kiện coi là "chưa
     biết" rồi ĐI XOÁ luôn video vừa làm. Nay `_thoi_diem()` trả **None =
     không đọc được → GIỮ**. Quy tắc chung: không xác định được thì GIỮ.
  21. `_test_hlbox.py` → **Ô NỀN SÁNG CHẠY THEO TỪ (mode `hlbox`, Submagic)**.
     ASS không đo được bề rộng chữ nên không vẽ được hình chữ nhật khớp chữ →
     ô = **viền cực dày + chữ tô ĐẶC cùng màu** (thành viên thuốc bo góc). Phải
     dùng **2 DÒNG/1 TỪ**: Layer 0 = miếng ô (các từ khác `\alpha&HFF&` ẩn),
     Layer 1 = chữ vẽ đè. Bản đầu nhúng ô giữa dòng chung với chữ và ĐÃ SAI:
     libass gộp mọi viền của 1 dòng vào 1 lớp nên viền đen của từ bên cạnh **đè
     lên ô, chặt phẳng 1 cạnh**, cỡ chữ lớn thì 2 từ dính liền ("TRỌNGCHUYỆN").
     6 lỗi khác bắt được khi rà đối kháng 05/08/2026, mỗi lỗi = 1 mục canh:
     `cap_ow` ≥ 0,17 → viền chữ dày hơn ô, ô bị nuốt (nay `bord_box` = max(…,
     `ow`+5%)); `color` user chọn bị bỏ trong khi XEM TRƯỚC hiện đúng (lỗi
     "chọn X ra Y", đã từng sửa ở việc #110); bỏ dòng <60 ms làm **mất 4-6% chữ**
     với lời nhanh và **mất gần hết** khi chép lời không có mốc từng-từ (bước
     0,05 s → 1/20 dòng) → nay GOM từ dày + LẤP LỖ, tối thiểu 0,12 s; `delay`
     âm mất dòng đầu; ô bọc dấu phẩy lẻ; CJK bị chèn dấu cách; `\fscx` (phồng
     NGANG) làm cả khối chữ xuống dòng lại trong 160 ms → chỉ phồng `\fscy`.
     Cụm hlbox dùng `max_words=3` (5 từ + chữ HOA hay tràn 3-4 dòng, cỡ 6,5%
     thì CẮT ĐÁY KHUNG). Cổng render THẬT + **đếm pixel** đúng màu palette từng
     từ (ngưỡng phải tính theo **số chữ**: đo ở 540×960 "ai" = 1.437 px, "không"
     = 4.887 px → ngưỡng cứng 2.000 px là sai) + đo tâm khối để chắc ô DI CHUYỂN
     + đo hàng pixel cuối để so **PARITY với kiểu cũ** (ca cỡ 6,5% + ny 0,88 thì
     MỌI kiểu đều bị cắt đáy — lỗi CŨ của app, dùng ny ≤ 0,80 là an toàn).
     BẤT BIẾN SỐNG CÒN: 18 preset CŨ × 4 bộ tham số phải ra .ass **giống từng
     byte** bản `git show HEAD:app/core/captions.py` (anh Hùng đang chạy sản
     xuất 200-300 kênh bằng preset cũ) — vì vậy nhánh `active` giữ nguyên code,
     `hlbox` viết thành nhánh RIÊNG chứ không gộp.
  22. `_test_pipe_e2e.py` **phải chuyền key Groq vào sandbox**. Key nằm trong
     `<DATA_DIR>\.env` (`config.py:46 load_dotenv(DATA_DIR/".env")`), mà test
     trỏ `BQ_DATA_DIR` vào thư mục TẠM → sandbox 0 key → `transcribe()` lùi về
     whisper MÁY → tải model large-v3 ~3 GB vào cache rỗng → job `transcript`
     kẹt > 420 s → cổng **FAIL oan** (đo 05/08/2026: job 'running', thư mục
     `models--Systran--faster-whisper-large-v3` vừa tạo). Nay test đọc `.env`
     thật và chuyền `GROQ_API_KEYS` qua BIẾN MÔI TRƯỜNG (không ghi ra file):
     38 key → cả dây chuyền xong trong **20 giây**. Đặt `BQ_E2E_PRESET="Ô sáng
     chạy từ (đa màu)"` để chạy e2e với mẫu-theo-kênh đúng cảnh sản xuất.
     LƯU Ý khi Groq lỗi thật: app tụt về whisper máy — chậm hơn hàng chục lần
     chứ không báo lỗi, nên nghi "dây chuyền chậm" thì kiểm key TRƯỚC (dùng SDK
     OpenAI, đừng dùng urllib: Cloudflare trả 403 error 1010 vì User-Agent).
  23. `_test_sfx_kho.py` → kho tiếng động 184 file / 330 KB, kêu ĐÚNG mốc.
  24. `_test_chon_doan.py` → AI NGHE + XEM + trọng tài chấm mù + hội đồng 3 góc
     nhìn + sàn thích ứng + đúng số Part + video KHÔNG LỜI.
  25. `_test_tieng_va_mau.py` → **TIẾNG ĐỘNG THEO NỘI DUNG CHỖ NỐI + TÊN MẪU
     THẬT.** 2 lỗi thật từ nhật ký anh Hùng 06/08/2026 (Part 1 và Part 2 cùng
     ra `reveal/…confirmation_003.opus`):
     (a) luật cũ "điểm nối CUỐI = reveal" mà clip 2 ĐOẠN chỉ có ĐÚNG 1 điểm nối
     -> điểm nối đó vừa đầu vừa cuối -> **mọi Part đều tiếng "ding"**. Nay
     `_loai_theo_khoang_nhay` suy theo NỘI DUNG chỗ nối: nhảy NGƯỢC thời gian
     (hook-first) -> impact · gần liền mạch ≤1,2s -> pop · đoạn kế <2,5s (câu
     chốt) -> impact · còn lại -> transition; reveal CHỈ khi ≥2 điểm nối VÀ nền
     là 'transition'. Đo: 6 Part clip-2-đoạn ra 3 loại (trước: 1 loại).
     (b) nhật ký ghi `mẫu «(mẫu đã chốt lúc xếp job)»` = vô dụng. Nay
     `_tpl_for_project` ĐÓNG DẤU `_ten_mau` vào bản sao mẫu -> mẫu CHỤP lúc xếp
     job vẫn ghi tên thật (dây chuyền chụp mẫu rồi xuất sau hàng phút, đọc lại
     tên ở lúc xuất là đọc mẫu kênh KHÁC).
  26. `_test_xem_hinh.py` → **AI XEM HÌNH + 413 KHÔNG ĐƯỢC ĐỐT KEY.** 3 lỗi
     thật 06/08/2026:
     (a) `meta-llama/llama-4-scout…` **Groq ĐÃ GỠ** -> 404 mọi lượt -> digest 0
     mốc mà app im lặng (fail-safe che mất). Hỏi `/models` rồi thử ảnh thật
     từng model: chỉ còn **`qwen/qwen3.6-27b`** nhìn được. Nó là model SUY LUẬN
     -> phải `reasoning_effort="none"` (đo: 527 -> 104 token trả về, mô tả vẫn
     đúng) + `llm.bo_khoi_suy_nghi` bỏ khối `<think>` trước khi dò dấu ngoặc.
     (b) Groq trả **413** "Request too large … tokens per minute" KÈM
     `code: rate_limit_exceeded` -> `is_rate_limit_error` khớp -> `mark_limited`
     khoá key 120s. **1 yêu cầu quá to = đốt sạch 38 key = cả dây chuyền cắt
     đứng.** Nay `is_too_large_error` + `LLMTooLarge`: KHÔNG phạt key, caller tự
     THU NHỎ (vision gửi lẻ từng ảnh). Bẫy này có từ trước, không riêng vision
     (gpt-oss-120b prompt chọn đoạn cũng 413).
     (c) model chỉ nhận **3 ảnh/lượt** (400) mà app gửi 6 và 4 -> mất trắng cả
     batch. Nay chia theo `llm.vision_max_images()`; vision_digest dùng 2
     (đo: 1 ảnh ĐẠT · 2 ĐẠT · 3 -> 413 "Requested 8632 > Limit 8000").
     **Số đo phải nhớ:** 12 khung/video · 384px · ~796 token/ảnh (hạn mức tính
     ~2.410/ảnh) · **219 giây/video** · digest 12/12 mốc, mô tả đúng ("Chef
     shouts excitedly with arm raised" act=8). VISION_CUT vẫn mặc định TẮT vì
     3,7 phút/video là nhiều với 300 kênh — NHƯNG video **KHÔNG CÓ LỜI NÓI** thì
     m1 TỰ BẬT (`bat_buoc=True`): lúc đó hình là căn cứ duy nhất còn lại.
     Digest rỗng -> ghi `logs/vision_<ngày>.log` nêu lý do + tên model.
  27. `_test_hoc_gu.py` → **AI HỌC GU CHỦ KÊNH** (nút Hay/Nhạt trên thẻ clip ->
     bảng `clip_gu` -> `chon_doan.khoi_prompt_gu` đưa ví dụ vào prompt của KÊNH
     ĐÓ). Bất biến: chưa đánh giá -> prompt Y HỆT cũ; gu kênh A KHÔNG rò sang
     kênh B; bấm lại -> GHI ĐÈ (UNIQUE theo clip_id); clip bị xoá -> bài học
     VẪN CÒN (lưu tóm tắt tiêu đề/thoại/độ dài/số đoạn, không lưu id); khối
     prompt chặn trần 900 ký tự (prompt chọn đoạn đã sát mức 413). Cổng này
     quét MỌI nhãn nút tìm emoji dễ thiếu font và **đã lôi ra 2 nút sót từ
     v2.6.22**: `QPushButton("📋")` ở thanh trên + `"✕ Tắt tất cả"`.
     LƯU Ý: chỉ soi NHÃN NÚT, đừng soi cả file — emoji trong dòng ghi chú thì
     user không thấy (bản đầu của cổng này FAIL oan vì thế).
  28. `_test_lien_thong.py` → **LIÊN THÔNG: 2 bản vá ĐÚNG cộng lại có thể ra
     SAI.** Cổng 25/26/27 kiểm từng tính năng; cổng này đi tìm chỗ chúng phá
     nhau. Viết nó ra **4 LỖI THẬT** (06/08/2026):
     (a) `LLMTooLarge` mang lời lỗi CÓ chứa `rate_limit_exceeded` -> vòng
     ĐỢI-HẾT-LƯỢT `m1._call_waiting_quota` tưởng hết lượt và **đợi thật tới 15
     PHÚT/video** cho yêu cầu không bao giờ thành công. Nay chặn `LLMTooLarge` +
     `is_too_large_error` TRƯỚC nhánh đợi (đo: 0ms thay vì đợi).
     (b) đường **CHÉP LỜI** (mọi video đều đi qua) cũng `mark_limited` khi gặp
     413 -> đốt key. Nay ném `LLMTooLarge`; nơi gọi vẫn `except Exception` nên
     tụt về whisper MÁY, video KHÔNG vào `_Loi`.
     (c) `save_template` LƯU CẢ dấu tạm `_ten_mau` vào mẫu trên đĩa (lúc xuất,
     `layout_tpl` mang bản sao có dấu; user mở Chỉnh mẫu + Lưu là dấu đi theo).
     Nay gỡ mọi khoá bắt đầu bằng `_` trước khi lưu.
     (d) `bo_khoi_suy_nghi` cắt ở MỌI chỗ có `<think>` -> mô tả khung hình chứa
     đúng chữ đó bị **chặt đôi JSON**. Nay chỉ coi là khối nghĩ khi nó nằm
     TRƯỚC mọi dấu mở JSON.
     Còn kiểm: nâng cấp DB trên **300 kênh / 1.800 clip / 207 mẫu** (0 dòng mất,
     0ms, mở app 4 lần chỉ 1 chỉ mục) · Huỷ giữa lúc AI xem hình phải nổi
     `CanceledError` (không bị `except Exception` nuốt) · 5 mẫu JSON của model
     CŨ vẫn bóc đúng · 429 THẬT vẫn phải đợi rồi thử lại (không sửa quá tay).
     BẪY KHI VIẾT CỔNG NÀY: `soonest_ready_wait` CHỈ xét key có trong
     `settings`, nên muốn dựng bẫy "mọi key đang cooldown" phải đặt
     `GROQ_API_KEYS` (key GIẢ cũng được, cổng không gọi mạng) — key bịa ngoài
     settings thì hàm trả None và test PASS oan.
  29. `_test_chon_kenh_mau.py` → **SAU KHI LƯU MẪU: đổi ĐÚNG kênh muốn đổi.**
     Anh Hùng 06/08/2026 (ảnh hộp "19 kênh đang gán mẫu RIÊNG…"): "những nhóm
     tôi k muốn thay cái mẫu đó thì làm như nào". Hộp bản đầu chỉ có GÁN-HẾT /
     ĐỂ-NGUYÊN -> 200 kênh nhiều nhóm thì gán hết là phá mẫu nhóm khác. Nay có
     đường thứ 3 `_chon_kenh_gan_mau`: TÍCH Ô từng kênh, mỗi dòng ghi
     `tên · nhóm · mẫu đang dùng`, có Ô TÌM (tên kênh/nhóm/mẫu) + 2 nút chọn
     nhanh **CHỈ ĐỤNG PHẦN ĐANG LỌC** (gõ tên nhóm -> "Chọn hết đang hiện" =
     gán cả nhóm đó, nhóm khác nguyên). Mặc định KHÔNG tích gì; nút MẶC ĐỊNH của
     hộp cảnh báo là "Chọn từng kênh…" nên bấm Enter KHÔNG đổi hết.
     LỖI THẬT trong bản đầu: nó tra id kênh **THEO TÊN**
     (`SELECT id FROM projects WHERE name=?`) -> 2 kênh TRÙNG TÊN khác nhóm là
     gán mẫu cho kênh SAI. Nay query lấy luôn `id`. Ca test bắt buộc: 2 kênh
     trùng tên khác nhóm, chỉ 1 cái được đổi.
     LƯU Ý KHI TEST: dựng StudioPage bằng `__new__` PHẢI gọi
     `QWidget.__init__(sp)`, thiếu là `QMessageBox(self)` nổ "super-class
     __init__ never called"; và vá `QMessageBox.exec` để tự gán `clickedButton`
     mới mô phỏng được "user bấm nút nào".
  30-35. `_test_muot_tram_kenh.py` · `_test_nut_khong_cut.py` ·
     `_test_luoi_an_toan.py` · `_test_lo_hong_v212.py` ·
     `_test_moc_ngoai_phim.py` · `_test_va_lo_sub.py` (mỗi file tự ghi số cổng +
     lý do ở docstring — đọc ở đó).
  36. `_test_chuyen_canh.py` → **CHUYỂN CẢNH CHỖ GHÉP ĐOẠN (xfade) + CỬA CHỜ
     ffmpeg.** 53 ca, chạy ffmpeg + video Nhật THẬT. 4 thứ nó canh:
     (a) **`xfade` ĂN BỚT thời lượng** — `out = dài(A)+dài(B)-d` — mà phụ đề
     `.ass` + mốc tiếng động dựng theo timeline "nối THẲNG" nên không bù là lệch
     `(n-1)×d` (clip 4 đoạn = **0,9 s**), đúng loại lỗi v1.87 "hình một đằng
     tiếng một đằng". Cách chữa (`ffmpeg_utils._bu_xfade`): LẤY THÊM đúng `d`
     giây phim ở cuối đoạn trước rồi đặt `offset = độ_dài_GỐC` -> mọi khung của
     đoạn sau rơi ĐÚNG mốc cũ, **KHÔNG phải sửa `.ass`**. Cổng ĐO THẬT: lệch độ
     dài 0 ms · lệch hình −33 ms · lệch tiếng 0,0 ms (tương quan chéo sóng
     8 kHz) · phụ đề ở cùng mốc 75.006 px vs 75.045 px. Kiểm cả **hook-first
     (NGƯỢC thời gian)** và **nguồn VFR**.
     (b) **CỬA CHỜ BỊ XOÁ MÀ KHÔNG AI BIẾT** — đã xảy ra thật 07/08/2026: một
     lượt sửa khác ghi đè `_run`, cửa chờ biến mất, app vẫn chạy, test vẫn xanh,
     chỉ SỐ ĐO tố giác (10 lượt ra 397 luồng thay vì 44). Nay có ca **quét
     tĩnh**: `_run` phải chứa `_xin_cho_ffmpeg`.
     (c) **KIỂU xfade bị gỡ khỏi ffmpeg** -> phải FAIL TO, không im lặng ra clip
     cắt khô. Cổng so danh sách 58 kiểu với `ffmpeg -h filter=xfade` của `bin/`.
     (d) **BẤT BIẾN**: chuyển cảnh TẮT phải ra file GIỐNG `main` — nạp
     `git show main:app/core/ffmpeg_utils.py` thành module riêng rồi xuất song
     song, đo **PSNR 99 dB** ở 5 mốc.
     **2 BẪY ĐO ĐÃ SẬP, ĐỪNG LẶP:** mốc cắt phải ở **CẢNH SÁNG** (nguồn Nhật ở
     giây 20 sáng TB chỉ **3,3/255** = gần đen -> ca đếm pixel ra 0,69% và FAIL
     OAN vì cả 2 bản đều đen; đổi sang mốc 100/200/300s thì ra 57-83%); ngưỡng
     đếm pixel phải **THEO TỈ LỆ** (khung phim đã có vùng gần trắng nên khung
     KHÔNG chữ vẫn đếm 4.634 px -> ngưỡng cứng 1.500 px FAIL OAN).
  37. `_test_ca_bien_xuat.py` → **CA BIÊN CỦA ĐƯỜNG XUẤT** (cổng 36 canh ca
     thường, cổng này đi tìm chỗ VỠ ở ca xấu — 200-300 kênh thì ca xấu chắc
     chắn gặp). 23 ca, ffmpeg thật, nguồn tự sinh bằng `lavfi` nên không phụ
     thuộc file trên máy: **video KHÔNG TIẾNG** (`_graph_xfade` chỉ thêm
     `acrossfade` khi `co_tieng` — sai nhánh là clip câm nổ giữa dây chuyền) ·
     **HUỶ giữa lúc xuất** (phải ném `CanceledError` + dọn hết `_seg_*` + không
     để file đích dở + **không bỏ lại ffmpeg mồ côi**) · **không ghi được đĩa**
     (mô phỏng hết đĩa: phải FAIL TO, lời lỗi có log để đọc, không để file 0
     byte) · **máy nhân viên** thiếu NVENC + frei0r + OpenCL (đo: kho hiệu ứng
     tự co **25 → 14**, nhóm GPU trả `[]`, vẫn xuất đúng 12,000s) · **clip 1
     đoạn** và **đoạn CHẠM MÉP phim** khi chuyển cảnh đang BẬT.
     **BẪY ĐẾM TIẾN TRÌNH:** lọc `ffmpeg` theo **cmdline** sẽ đếm CHÍNH LỆNH
     KIỂM (mã nguồn có chữ 'ffmpeg') -> luôn báo "đang chạy"; đã báo sai 4 lần.
     Phải lọc theo `p.name()` (hoặc `Get-Process ffmpeg`).
     **BẪY VIẾT CỔNG NÀY (sập 1 lần):** stub `thu_muc_frei0r` phải trả **Path**
     chứ không phải `str` (hàm thật trả Path) — trả `""` ra `AttributeError:
     'str' object has no attribute 'is_dir'`, suýt báo nhầm là lỗi app. Và phải
     xoá CẢ 2 chỗ nhớ `_F0R_OK` + `_MOD_CACHE`, không thì đọc kết quả lần đo
     trước rồi PASS OAN.
  38. `_test_hieu_ung_ai.py` → hiệu ứng điểm nhấn + AI chọn theo SỐ ĐO.
  39. `_test_dong_goi.py` → BẢN ĐÓNG GÓI đủ tài nguyên (bẫy `.exe` cũ hơn mã).
  40. `_test_da_quoc_gia.py` → **ĐA QUỐC GIA: AI phải hiểu MỌI loại nội dung.**
     Video THẬT của anh Hùng theo nhóm ngôn ngữ (Nhật `video nhật dài` · Hàn
     `video hàn` · Anh `video mỹ` · Việt `video viêt`), chép lời bằng **Groq
     THẬT**. Mỗi nhóm chứng minh 5 điều: (1) `language` khớp MÃ ISO + số câu > 0
     (2) `generate_highlights` ra `llm_used=True`, KHÔNG rơi "Cắt cơ bản"
     (3) phụ đề render khung THẬT + đếm pixel **TỪNG DÒNG** + không cắt đáy /
     không tràn mép (4) >= 3 Part, **không phải Part nào cũng cùng một tiếng**,
     và tiếng động KHÔNG át lời (RMS đỉnh 0,25s <= 12× RMS nền) (5) đổi NHÃN
     ngôn ngữ -> `chon_hieu_ung` + `chon_chuyen_canh` ra **Y HỆT**.
     **LỖI THẬT cổng này tìm ra:** `chon_doan.co_loi_noi_that` đếm từ bằng
     `.split()` -> câu Nhật/Trung KHÔNG CÓ DẤU CÁCH ra 1 token -> video short
     1-2 đoạn bị gán nhầm **KHÔNG LỜI** -> app bỏ transcript, ép XEM HÌNH
     (~3-4 phút/video) và **KHÔNG đốt phụ đề**. Đo (mật độ 2,00 từ/giây): Nhật
     1 đoạn / Nhật 2 đoạn / Trung 1 đoạn đều SAI; Anh/Việt/Hàn đúng. Chữa bằng
     `recap._word_tokens` (CJK-aware, bất biến `== .split()` khi không có CJK).
     **KHÔNG CÓ trên máy (ghi thẳng, không bịa):** video tiếng **Trung · Thái ·
     Ả Rập · Do Thái** — đã quét toàn bộ `D:\` + `C:\Users\Admin`. Với các nhóm
     đó cổng chỉ kiểm được điều 3 và 5 (không cần tiếng thật).
  41. `_test_shader.py` → **6 SHADER `libplacebo` — ĐÃ NỐI VÀO ĐƯỜNG XUẤT**
     (trước 08/08/2026 chúng nằm trong bản `.exe` mà **không một dòng mã nào
     gọi tới**). Kẹt cũ: `libplacebo` **không có timeline `enable`** nên áp là
     áp TOÀN CLIP, trái luật chống loè số 1. **Chữa: cắt ĐÚNG cửa sổ điểm nhấn
     bằng `trim`, chỉ mảnh đó lên GPU, `concat` nối lại** (`hieu_ung._SH_MAU`)
     — cùng kiến trúc "cắt mảnh" của `_tach_va_noi_manh`. Đã đo cả 2 cách trên
     clip THẬT 24s/1080x1920/722 khung: `split`+`overlay` cả clip **2,18×
     wall · 1,41× CPU-giây** (LOẠI) · `trim`+`concat` **1,16× wall · 1,01×
     CPU-giây** (ĐANG DÙNG; phần dư là phí MỞ thiết bị Vulkan ~0,4s/lệnh, cố
     định, không theo độ dài clip). Số khung + độ dài **giữ nguyên tuyệt đối**
     (722/722 · 24,066667s) nên `.ass` và mốc tiếng động không phải sửa.
     Kho hiệu ứng **25 -> 31**; `sh_net_hon` là kiểu MỚI (bản CPU `unsharp` đã
     bị loại vì ở trần chỉ đổi 6,3% pixel, bản shader đo **12,58%**).
     **BẪY "THÀNH CÔNG GIẢ" THỨ 2 (mới, khác 2 bẫy `xfade_opencl`):** `.hook`
     có `//!HOOK` đúng mà thân GLSL chạy không được thì libplacebo in *"Failed
     executing hook, **disabling**"* rồi **CHO QUA KHUNG NGUYÊN VẸN** — `rc=0`,
     đủ 92/92 khung, file bình thường, **không hiệu ứng nào**. Đếm khung KHÔNG
     bắt được. Vì vậy `co_libplacebo()` gọi thêm **`_shader_chay_that()`**: đẩy
     nền TRẮNG qua `toi_vien.hook` rồi đo DẢI SÁNG — chạy = **107**, bị tắt =
     **1** (ngưỡng 40). Ngược lại `.hook` sai CÚ PHÁP / đường dẫn hỏng thì FAIL
     TO (rc != 0, 0 khung) — chỉ ca "biên dịch được nhưng chạy không được" mới
     im lặng. **BẪY `blend`:** `[shader][gốc]blend=…:enable=…` lúc `enable=0`
     cho qua đầu vào **THỨ NHẤT** = bản CÓ shader -> hiệu ứng phủ TOÀN CLIP còn
     trong cửa sổ lại nhạt (đo: ngoài **34,45%**, trong **4,29%** — đúng
     ngược), rc=0 im lặng. Dùng `overlay`/`trim`, đừng dùng `blend`.
  42. `_test_rac_va_bao.py` → **HẾT RÒ RÁC TẠM · THẤY ĐƯỢC HIỆU ỨNG · ĐANG ĐỢI
     THÌ PHẢI NÓI** (65 ca, ffmpeg thật, 3 việc anh Hùng nêu 08/08/2026).
     (A) **RÒ `_seg_*` KHI XUẤT LỖI/HUỶ.** Đo trước sửa (`_do_ro_seg.py`, mảnh
     còn bị Windows khoá 2 giây đúng như lúc ffmpeg vừa bị kill): **6 file /
     8,9 MB** nằm lại vĩnh viễn. Gốc: `_cleanup_dst` xoá 1 phát rồi
     `except OSError: pass` — nuốt PermissionError IM LẶNG; và đường "lùi nối cả
     clip" `del temps[:]` VÔ ĐIỀU KIỆN nên mảnh chưa xoá được bị **xoá khỏi sổ**
     -> caller hết đường dọn. Nay đủ 3 lớp: **THỬ LẠI** (`_XOA_CHO`, tổng ~2,1s
     — chỉ chờ khi file THẬT SỰ còn đó nên đường xuất bình thường không chậm đi
     ms nào) · **SỔ NỢ** `_RAC_TON` + `don_rac_ton()` gọi ở đầu mỗi lượt xuất ·
     **QUÉT MỒ CÔI** `don_seg_mo_coi()` lúc mở app. Mảnh nay mang tên
     `_seg_p<pid>h<hex>_…` (`_tag_moi`) nên quét mồ côi phân biệt được "mảnh của
     lượt ĐANG chạy" với "mảnh của lần chạy trước đã chết" — KHÔNG phải đợi đủ
     2 giờ như `tempsweep` (app thoát bằng `os._exit`, tự cập nhật liên tục).
     BẤT BIẾN AN TOÀN: chỉ xoá tên khớp mẫu app đặt + PID đã chết; file của
     user, tên kiểu cũ, tên gần giống -> KHÔNG ĐỤNG.
     (B) **NHÌN THẤY HIỆU ỨNG.** Anh Hùng: *"làm sao để biết có thêm hiệu ứng
     hay âm thanh gì k"*. Thẻ clip hiện `3 hiệu ứng · 2 tiếng động` (0 -> "không
     hiệu ứng"), bấm ra hộp chi tiết giây/kiểu/LÝ DO KÈM SỐ. Số lấy từ
     `hieu_ung_log` + **`tieng_dong_log` (MỚI — trả RIÊNG từng lượt; biến toàn
     cục `_SFX_LAST_PICK` là của lượt nào xong sau cùng, 3 làn song song là đọc
     nhầm clip)**; `m1._luu_da_ap` ghi vào `clips.signals['da_ap']`. Nhãn KHÔNG
     EMOJI. Clip CHƯA xuất -> KHÔNG hiện nhãn (cấm đoán bừa).
     **LỖI THẬT cổng này lôi ra (có từ `main`):** `_enc_mezz` thiếu
     `-pix_fmt yuv420p` ở nhánh **libx264** (nhánh nvenc thì có) -> mảnh CHUYỂN
     CẢNH (qua `filter_complex`) ra **yuv444p** còn mảnh THÂN ra yuv420p ->
     ffmpeg **dựng lại filter graph** mỗi mảnh -> `metadata=print:file=` GHI ĐÈ
     file mỗi lần dựng lại -> `hieu_ung.do_nhip` chỉ còn số của MẢNH CUỐI
     (**4s/16s**) -> clip "phẳng" -> **0 ĐIỂM NHẤN**. Đo cùng clip cùng máy:
     libx264 **0 điểm** · nvenc **3 điểm**. Tức **máy nhân viên (không NVENC) và
     mọi lượt NVENC lùi về CPU mất sạch hiệu ứng, im lặng**.
     (C) **ĐANG ĐỢI THÌ PHẢI NÓI.** Anh Hùng: *"xuất đến 1 ngưỡng r đứng im k
     báo gì cả, phải 3 4 phút k hiện 1%"*. `_run` xin chỗ ở cửa chờ TRƯỚC khi
     spawn ffmpeg; lúc đợi chưa có `time=` nào nên % không nhích và chữ không
     đổi. Nay `_xin_cho_ffmpeg` gọi hàm báo THEO THREAD (`dat_bao_cho`, job gắn
     ở `m1` / `analysis` và GỠ ở `finally` — quên gỡ là job sau ghi tiến trình
     vào job cũ): *"đang đợi lượt ffmpeg (N việc trước)"* mỗi 0,5s, tới lượt thì
     báo tiếp. Đo: 2 giây chờ ra **4 thông báo** (bản `main`: **0**).
     Kèm **ƯU TIÊN**: `UT_XUAT` < `UT_PHAN_TICH` (tách audio chạy nền, xuất là
     việc anh Hùng đang nhìn). **VAN CHỐNG ĐÓI BẮT BUỘC** `_DOI_TOI_DA = 20s`:
     chờ quá mức đó thì việc phân tích được NÂNG ngang hàng xuất, trong cùng
     hàng thì FIFO -> chắc chắn tới lượt. Ưu tiên trần trụi chính là lỗi "làn
     cắt chết đói vì LIMIT 50" đã sập một lần, nên cổng ĐO CẢ HAI CHIỀU (đo với
     van 1,5s: phân tích đợi 1,55s giữa dòng xuất chảy liên tục).
     `_tra_cho_ffmpeg` phải `notify_all` (không phải `notify`): có ưu tiên nên
     người được đánh thức ngẫu nhiên có thể KHÔNG phải người xếp đầu hàng.
     **BẪY KHI VIẾT CỔNG NÀY (FAIL OAN 2 lượt):** nguồn `lavfi` mặc định
     (`testsrc2` + `sine`) là **PHẲNG TUYỆT ĐỐI** -> `chon_hieu_ung` trả 0 điểm
     **ĐÚNG LUẬT** ("clip phẳng không thêm gì ngớ ngẩn") -> tưởng app hỏng. Phải
     dựng nguồn có cao trào thật (`nguon_dong`: nền 0,04 + 2 cú nổ 1,0 -> dải
     động 24,8×, ngưỡng `hieu_ung.PHANG` = 1,35).
  42. `_test_tieu_de_part.py` → **HỘP TIÊU ĐỀ + HUY HIỆU "PART N" PHẢI CÓ THẬT
     TRONG FILE XUẤT.** Anh Hùng 08/08/2026: *"tôi có cái phần tiêu đề đỏ part
     các kiểu kia mà xuất k có"* — xem trước có, file xuất chỉ còn phụ đề.
     **ĐO TRÊN CHÍNH FILE CỦA ANH HÙNG** (tỉ lệ điểm ảnh ĐỎ, video 'GOING BACK
     TO OUR OLD HOUSE', mẫu «test AI»): Part 3 xuất 17:44 TRƯỚC khi tắt app =
     **11,584%**; app mở lại 17:59:29; Part 2 (18:01) và Part 1 (18:03) chạy
     LẠI = **0,000%**. GỐC = 3 dòng ở 3 file **mâu thuẫn nhau**:
     (a) `m1_highlight.export_clip` `except CanceledError:` dọn luôn ảnh lớp
     chữ `_ovl_<cid>.png` — coi tắt-app là "huỷ hẳn";
     (b) `worker.WorkerPool.stop()` `UPDATE jobs SET status='pending' WHERE
     status='running'` — coi tắt-app là "tạm dừng, mở app chạy tiếp";
     (c) `ffmpeg_utils.export_canvas_clip`
     `use_png = bool(overlay_png and os.path.exists(overlay_png))` — thiếu file
     thì **bỏ overlay IM LẶNG**: rc=0, đủ khung, mp4 hoàn hảo, không một dòng
     báo. Đây là chỗ nuốt cuối cùng, và **đếm khung KHÔNG bắt được**.
     CHỮA: `_user_da_huy` (chỉ user bấm Huỷ, `jobs.cancel_req=1`, mới dọn ảnh)
     + `_dung_lai_anh_chu` DỰNG LẠI ảnh từ **đơn thuốc `ovl_spec`** đi trong
     payload (`services.enqueue_export`, `studio_page._ovl_spec`) — `ovl_spec`
     **KHÔNG vào hash chống trùng**, nếu không 200-300 kênh xuất lại từ đầu.
     `render_overlay_png` vẽ logo bằng **QImage** (QPixmap không dùng được ở
     luồng nền). Nhật ký dây chuyền nay có mục **`lớp chữ: CÓ / dựng lại /
     ⚠ KHÔNG CÓ`** — trước đây không hề nhắc tới lớp chữ nên không cách nào
     biết Part nào thiếu. Đo: hộp tiêu đề **11,692% -> 0,000% -> 11,692%**,
     huy hiệu Part **5,825% -> 0,000% -> 5,825%**.
     **2 BẪY ĐO ĐÃ SẬP khi viết cổng này:** (1) nguồn `testsrc2` **tự có ô đỏ**
     nên bản KHÔNG lớp chữ vẫn đếm 2,387% — phải dùng màu phẳng không đỏ
     (`color=c=0x1E6F5C`) thì mới ra 0,000% sạch; (2) ảnh lớp chữ phải vẽ
     **ĐÚNG CỠ KHUNG XUẤT** — `overlay=0:0` KHÔNG co giãn, nên ảnh 1080x1920
     chồng lên khung 540x960 là **cắt mất huy hiệu Part** ở ny=0,77 -> ca "tiêu
     đề rỗng" FAIL OAN. (App thật luôn 1080x1920 cả hai đầu nên khớp.)
     Ca bắt buộc: tiếng Việt có dấu · `%` · `:` · `'` · `\` và `"` · tiêu đề
     300 ký tự · tiêu đề RỖNG (mất hộp tiêu đề là đúng, **nhưng huy hiệu Part
     phải còn**).
  43. `_test_hieu_ung_khung.py` → **QUÉT ĐỘ SÁNG TỪNG KHUNG CỦA MỌI KIỂU HIỆU
     ỨNG.** Anh Hùng xem clip THẬT 08/08/2026: *"ví dụ zoom nhồi gì đó thấy nó
     TỐI ĐEN không thấy gì rồi lại hiện"* · *"hiệu ứng lỏ quá"*. Cổng 38/41 kiểm
     CHỌN ĐÚNG KIỂU và KHÔNG RÒ, nhưng **không ai đo độ sáng** -> hiệu ứng làm
     MẤT HÌNH mà mọi cổng vẫn xanh. Cổng này đo ở ĐÚNG 1080x1920 bằng chính
     ffmpeg (`blend=difference` -> `lutyuv` nhị phân -> `signalstats`).
     **3 LỖI THẬT nó lôi ra:**
     (a) **`sup_toi` = KHUNG ĐEN TUYỆT ĐỐI.** `eq=brightness=-0.34` là phép TRỪ
     THẲNG trên thang 0..1: cảnh sáng trung bình 0,27 (69/255) trừ 0,34 ra ÂM ->
     kẹp về 0. Đo: khung ngay mốc bật **YAVG = 0,0/255**, 18 khung sau chỉ
     **17,7** trong khi gốc 96,8 (= **18%**) — 0,6 giây MẤT HÌNH. Mức "nhẹ" vẫn
     ra 10/255. CHỮA: NHÂN chứ không TRỪ — `eq` tính `(in-0,5)*contrast+0,5+
     brightness`, đặt `contrast=k` và `brightness=0,5*(k-1)` cho ra ĐÚNG
     `out = k*in`, tối theo TỈ LỆ nên KHÔNG BAO GIỜ về 0. Đo lại: thấp nhất
     **44%** độ sáng gốc, 0 khung đen.
     (b) **`sang_diu` (frei0r `softglow`) TÊN LÀ SÁNG NHƯNG LÀM TỐI** — cửa sổ
     tụt còn **29-33%** bản gốc. Quét 3 bộ tham số đều tối như nhau -> **GỠ**.
     (`quang_sang` frei0r `glow` mới là kiểu sáng thật: 142,3/96,8.)
     (c) **3 shader GPU KHÔNG THẤY ĐƯỢC**: `sh_net_hon` **1,87%** ·
     `sh_quang_sang` **0,47%** · `sh_mo_net` **2,16%** (bảng cũ trong mã ghi
     12,58/22,99/11,51% — đo trên nguồn KHÁC). Đã thử cứu `net_hon` (bán kính
     1,8->3,2 px, 4->8 điểm, cường độ 1,9->3,2) chỉ lên **6,00%**, vẫn dưới
     ngưỡng thấy được 8%. Gốc: cả 3 là phép LÂN CẬN VÀI PIXEL, vô hình trên
     khung 1080x1920 (cùng bài học `mo_net` CPU). 2/3 lại là bản sao GPU của
     kiểu CPU đang tốt -> **GỠ cả 3 + xoá luôn file `.hook`**. Kho **31 -> 27**.
     **NÂNG CẤP KÈM: "ÊM VÀO — ÊM RA".** `enable=` bật/tắt filter PHÁT MỘT nên
     khung bật và khung tắt lệch **>45% độ sáng** — mắt đọc ra là "cụp một cái".
     Nay biên độ nhân nửa hình sin `sin(pi*(t-a)/(b-a))` (`hieu_ung._SONG`): hai
     mép cửa sổ biên độ = 0 nên khung đầu/cuối GIỐNG HỆT bản không hiệu ứng (đo
     `vignette=a='0'` -> **0,00% pixel đổi**). Áp cho `loe_sang` · `sup_toi` ·
     `nhay_sang` · `tuong_phan` · `toi_vien`. `nhay_sang` còn phải `abs(sin)`:
     bản cũ `sin` chạy cả ÂM nên nửa số nháy là nháy TỐI (38/97 = 39%).
     **2 BẪY ĐO ĐÃ SẬP KHI VIẾT CỔNG NÀY:** (1) **đừng thu nhỏ khung rồi mới
     đo** — thu về 160 px là TRUNG BÌNH 45 pixel thành 1, hạt nhiễu/độ nét bị
     san phẳng: `hat_nhieu` ra **0,00%** và bị kết luận oan "không hoạt động";
     đo ở 1080x1920 ra **27,64%**. (2) **đừng `format=gray` giữa chuỗi đo** —
     gray là dải ĐẦY (0..255), yuv420p dải HẸP (16..235), ffmpeg tự chèn scale
     nên mức 0 (2 khung GIỐNG HỆT) thành **16**, `gt(val,12)` đúng -> MỌI kiểu
     ra **100% pixel đổi**, kể cả so file với CHÍNH NÓ. Cổng có ca đối chứng
     "so gốc với gốc = 0,00%" để tự bắt lại. Và có ca **TỰ KIỂM BỘ DÒ**: dựng
     lại công thức CŨ, bắt bộ dò phải kêu (không thì cổng chỉ là con dấu).
  44. `_test_tieng_hieu_ung.py` → **MỖI ĐIỂM NHẤN HÌNH PHẢI CÓ TIẾNG, ĐO BẰNG
     dB.** Anh Hùng: *"âm thanh hiệu ứng … thậm chí còn không nghe được gì cả
     luôn"* · *"có hiệu ứng mà không có âm thanh cứ sao sao ấy"*. **ĐO RA ĐÚNG
     2 LỖI** (`_do_tieng.py`, clip THẬT 10 s / 2 đoạn / 2 điểm nhấn):
     (a) **ĐIỂM NHẤN HÌNH KHÔNG HỀ CÓ TIẾNG** — bật/tắt tiếng động lệch
     **0,0 dB / -0,2 dB** = không một mẫu âm nào. Đúng thiết kế cũ: tiếng chỉ
     chèn ở ĐIỂM NỐI đoạn (`whoosh_offsets`), mà điểm nối do CẮT GHÉP quyết
     định, chẳng liên quan điểm nhấn. **Clip 1 ĐOẠN thì câm tuyệt đối** dù có 3
     hiệu ứng.
     (b) **TIẾNG Ở ĐIỂM NỐI QUÁ NHỎ** — chỉ nhô hơn nền **+0,7 dB** (nền -23,6;
     đỉnh -19,3 -> -18,6). Gốc: `_SFX_CAT_VOL` là hệ số TUYỆT ĐỐI (0,24-0,42)
     trong khi 184 file trong kho trải **26,5 dB** mức nghe được (-3,3 ..
     -29,8 dB) -> cùng nhóm, file này nghe rõ file kia mất hút.
     **CHỮA (đo được, không chỉnh mò):** `tools/do_muc_sfx.py` sinh bảng
     `app/assets/sfx/muc_do.json` (mean/max dB từng file, tra 0 ms);
     `_muc_nen_dB` đo nền của CHÍNH clip sắp xuất (80-126 ms, ngoài cửa chờ, chỉ
     giải mã audio); `tinh_gain_sfx` = `(nền + 8 dB + bù nhóm) - mean file`, kẹp
     để đỉnh <= -1 dBFS. Thêm `loai_sfx_theo_hieu_ung` (zoom/rung -> impact ·
     loé sáng -> reveal · glitch -> scratch · mờ/tối -> suspense/pop · chữ ->
     drumroll) và **DUCKING** hạ tiếng gốc 5 dB đúng lúc tiếng động kêu, cửa sổ
     0,45 s vào/ra êm bằng nửa hình sin (`_bieu_thuc_duck`).
     **SỐ ĐO SAU KHI SỬA:** điểm nhấn **0,0 -> +10,6 / +12,8 / +11,9 dB** trên
     nền · điểm nối **+0,7 -> +6,5..+9,6 dB** · so với MỨC LỜI NÓI (bách phân vị
     90) là **+0,3..+3,4 dB** (nghe rõ, không đè) · ducking đo **-5,1/-4,9/-4,8
     dB** trong cửa sổ và **-0,21 dB** ngoài cửa sổ.
     **BẪY ĐO ĐÃ SẬP:** đo ducking bằng cách so bản BẬT với bản TẮT ở giây
     (mốc+0,30) là SAI — chính TIẾNG ĐỘNG còn đang ngân (file 0,17-0,62 s) nên
     hiệu ra DƯƠNG (+2,7 / +10,7 / +3,7) và cổng FAIL OAN. ĐÚNG: dựng thêm 1
     lượt có ĐỦ mốc nhưng file tiếng gần IM LẶNG (`fx_sfx_dir` chứa 1 file
     -66 dBFS) -> ducking vẫn chạy, lớp tiếng động không nghe thấy -> hiệu với
     bản TẮT là **DUCKING THUẦN**.
     **HOOK MỞ ĐẦU** (anh Hùng: *"phần hook mở đầu cứ thêm sao cho phù hợp gây
     ấn tượng"*): `chon_hieu_ung(..., hook=True)` đặt SẴN 1 điểm nhấn ở giây
     **0,12** lấy từ hàng `_UV_THEO_LOAI["hook"]` (chỉ kiểu MẠNH, không mood).
     Nhận diện hook-first bằng **mốc NGƯỢC THỜI GIAN** (`_la_hook_first`:
     `segs[0][0] > segs[1][0]`) — cùng dấu hiệu `_loai_theo_khoang_nhay` dùng.
     Vì sao phải đặt sẵn: `_diem_hap_dan` cần một giây VỌT LÊN so với giây
     trước, mà giây 0 không có "trước" để so -> đoạn đắt nhất clip lại trần
     trụi nhất. Vẫn ăn cùng ngân sách 10% và trần `DAM_MAX` — đo 8,6%/10%.
  45. `_test_kiem_218.py` → **3 LỖI ÂM THẦM của LƯỢT KIỂM ĐỘC LẬP v2.18.0**
     (08/08/2026). Tất cả đều "app vẫn chạy, cổng vẫn xanh, chỉ SỐ ĐO tố giác".
     (a) **ĐO NHỊP BỊ CỤT -> MẤT SẠCH ĐIỂM NHẤN, IM LẶNG.** `do_nhip` trả 1 giá
     trị/giây và KHÔNG báo lỗi khi chỉ đo được mấy giây đầu; `chon_hieu_ung`
     coi đó là số đo THẬT của cả clip. Đo trên chính hàm (clip 16 s, cao trào
     giây 7/11/14, mức "vua"): đo ĐỦ 16/16 -> **3 điểm** (7,0·11,0·14,0) · đo
     cụt 8/16 -> 3 điểm nhưng DỒN vào 0,0·3,0·7,0 · đo cụt 4/16 -> **0 điểm** ·
     KHÔNG đo được -> **3 điểm** (đường CẤU TRÚC). Tức **đo cụt TỆ HƠN không
     đo**. Tái hiện end-to-end bằng danh sách concat lệch thông số: cùng
     `pix_fmt` -> nl=16/cd=16; **lệch pix_fmt 420→444 -> nl=8/cd=8**; **lệch
     KÍCH THƯỚC 540x960→480x854 -> nl=8/cd=8** (bản vá `-pix_fmt yuv420p` hôm
     08/08 chỉ bịt nguyên nhân THỨ NHẤT). Nay `hieu_ung.do_du(nl, cd, giây)`
     (phủ >= 70%) + `export_canvas_clip` vứt số đo cụt -> đi đường CẤU TRÚC.
     Kiểm KHÔNG kêu oan: 3 hình dạng clip thật (16s/10s/7s) đều nl=cd=int(dur),
     `do_du=True`, số điểm nhấn 3/2/1 KHÔNG đổi.
     (b) **NHẬT KÝ DÂY CHUYỀN ĐỌC TIẾNG ĐỘNG CỦA CLIP KHÁC.**
     `m1_highlight._ghi_cong_thuc` đọc biến TOÀN CỤC `_SFX_LAST_PICK`, đúng cái
     mà chính file đó đã ghi "đừng đọc — 3 làn xuất song song thì nó là của clip
     nào xong sau cùng". Thẻ clip (`_luu_da_ap`) đã dùng `tieng_dong_log` riêng
     từ v2.17 nhưng NHẬT KÝ thì bị sót. Máy anh Hùng chạy **3 chỗ ffmpeg song
     song** -> dòng của Part A có thể là tiếng của Part B. Nay truyền `td_log`.
     (c) `captions.build_ass(size=…)` là **PIXEL**; truyền tỉ lệ (0,055) thì
     .ass ghi `Fontsize: 0.055` -> chữ dưới 1 điểm ảnh = **KHÔNG THẤY GÌ** mà
     hàm vẫn trả True + ffmpeg rc=0 + đủ khung. `m1` quy đổi `int(csize*out_h)`;
     ca này chốt quy ước để lối gọi mới không sập lại.
- **2 CỔNG PASS OAN ĐÃ CHỨNG MINH BẰNG PHÉP THỬ PHÁ (08/08/2026)** — sửa xong,
  đừng để tái diễn:
  * `_test_hlbox.py` mục 12 so với `git show **HEAD**:app/core/captions.py`. Cây
    làm việc sạch thì HEAD = chính file đang chạy -> "so nó với chính nó", câu
    "18 preset CŨ … KHÔNG đổi 1 byte" ĐÚNG VĨNH VIỄN. Thử phá: đổi màu preset CŨ
    "Trắng đơn giản" `#FFFFFF -> #FF00FF` rồi **COMMIT** -> cổng vẫn "TẤT CẢ
    ĐẠT", mã 0. Nay mốc = CHA của commit đưa `hlbox` vào (`git log -S`) + chốt
    chặn "bản mốc phải KHÁC bản đang test"; thử phá lại -> **FAIL đúng 1 mục**.
  * `_test_hieu_ung_khung.py` chỉ hỏi "có đen / có tối quá / có đổi >= 3% / có
    rò", KHÔNG hỏi **CHIỀU**. Thử phá: bỏ `eval=frame` ở `sup_toi` -> "Sụp tối"
    **LÀM SÁNG THÊM 43%** (tỉ lệ sáng đáy **0,409 -> 1,434**) mà cổng vẫn "ĐẠT
    14 · HỎNG 0". Nay có bảng `CHIEU` + cột `sáng đỉnh`; thử phá lại -> trạng
    thái **SAI-CHIỀU**, mã 1.
  * `_test_cancel_persist.py` chỉ canh **DÒNG SỔ**, không canh FILE. Thử phá:
    giữ `unmark_taken` nhưng thêm `_pipe_quarantine_ctx` vào NHÁNH HUỶ (tức
    video của anh Hùng bị đẩy vào `_Loi` mỗi lần bấm Huỷ) -> `_test_cancel_
    persist.py` + `_test_pipe_overlap.py` + `_test_luoi_an_toan.py` **CẢ BA VẪN
    XANH**. Bất biến "huỷ ≠ lỗi, KHÔNG đổi tên/chỗ file gốc" chỉ nằm trong lời
    ghi chú. Nay có ca 2e (video gốc còn trong thư mục kênh + `_Loi` rỗng);
    thử phá lại -> **2 FAIL**.
  * `_test_ca_bien_xuat.py` CA 2 lấy MỘT mẫu ở `sleep(1.2)` rồi hỏi "lúc huỷ có
    ffmpeg đang chạy không". Máy bận (đúng cảnh sản xuất) thì lượt xuất còn đang
    XẾP HÀNG ở cửa chờ -> đo `0 tiến trình` -> cổng ĐỎ oan (chạy một mình lại
    XANH). Nay ĐỢI tới khi thấy ffmpeg thật rồi mới bấm Huỷ.
- **TIẾNG ĐỘNG CHỈ NGHE ĐƯỢC TRÊN CLIP CÓ NỀN YÊN — CHƯA CHỮA, ĐÃ BÁO**
  (`_do_sfx_theo_nen.py`). `tinh_gain_sfx` có 2 vế đá nhau: "đích = nền + 8 dB"
  và "kẹp đỉnh <= −1 dBFS". Kho 184 file là tiếng ngắn đã chuẩn hoá ĐỈNH (hệ số
  đỉnh trung vị **15,3 dB**) nên kẹp đỉnh gần như luôn thắng khi clip ồn:
  nền −23,6 dBFS (nguồn cổng 44) -> 53% file bị kẹp, thiếu trung vị 1,0 dB;
  nền **−15,7 dBFS** (clip THẬT đo hôm nay: xe tải nổ máy) -> **74% file bị kẹp,
  thiếu trung vị 8,9 dB, tối đa 21,8 dB**. Đo trên clip thật 16 s: bật/tắt tiếng
  động chênh **+0,6 / −1,1 / −0,0 / −1,6 / +2,4 dB** — 2/5 mốc còn NHỎ ĐI vì
  ducking hạ tiếng gốc 5 dB mà lớp tiếng động không bù nổi. Cổng 44 không thấy
  vì nó chỉ đo trên MỘT nguồn có nền yên. **Chưa tự sửa** (đổi độ to của mọi
  clip trên 200-300 kênh) — hướng đề xuất ghi trong docstring file đo.
- **CỔNG TEST PHẢI TRỎ VỀ BẢN MÃ CỦA CHÍNH NÓ.** 29 file `_test_*.py` từng ghi
  CỨNG `sys.path.insert(0, r"D:\claude\ai-content-studio")` (và `bin/ffmpeg.exe`,
  và các lần mở file mã nguồn để quét tĩnh). Chạy cổng từ một **git worktree**
  là đang kiểm **BẢN MÃ KHÁC** — nhánh đang sửa không hề được kiểm mà cổng vẫn
  XANH. Đo thật 08/08/2026: 8 cổng dây chuyền đều PASS trong khi chúng nạp
  `app/` từ repo chính, không đụng gì tới bản vá đang làm. Nay dùng
  `str(Path(__file__).resolve().parent)`. Viết cổng mới thì **đừng bao giờ ghi
  cứng đường repo**.
- **NHÓM HIỆU ỨNG CHẠY TRÊN GPU (`app/core/hieu_ung_gpu.py`)**: `xfade_opencl` +
  kernel gl-transitions (MIT) **21 kiểu ĐO ĐẠT** · `libplacebo` + shader GLSL tự
  viết **6/6 ĐẠT và ĐÃ NỐI vào đường xuất** (xem cổng 41). Nhóm shader chỉ bật
  khi `hieu_ung.co_shader()` = True (`BQ_SHADER=0` tắt tay); `ffmpeg_utils` chỉ
  thêm `-init_hw_device vulkan=vk` khi `hieu_ung.can_vulkan(<bộ đã chọn>)` =
  True, nên mức "tat" ra lệnh ffmpeg **không khác một ký tự nào** so với bản cũ
  (cổng 36 đo lại PSNR **99 dB** ở 5/5 mốc). Lượt xuất có shader mà ffmpeg chết
  -> `hieu_ung.bo_shader()` rồi xuất LẠI 1 lần không shader (lùi êm, nhật ký
  cũng bỏ shader để không khoe cái không có trong file).
  **2 bẫy của `xfade_opencl`, cả hai IM LẶNG (rc=0):**
  (a) nó trả PTS rác `AV_NOPTS` (in ra `pts_time:-600479950316066`) -> muxer bỏ
  hết khung -> **file ra 0 KHUNG dù có kích thước**; ai "chữa" bằng `fps=` sau
  `hwdownload` thì ffmpeg **sinh khung vô tận — đo 19,1 GB RSS + 364 CPU-giây
  trong 9 phút, phải giết tay**. Chữa: `setpts=N/FR/TB` (KHÔNG dùng
  `PTS-STARTPTS`, nó mất khung: 6/8 · 7/9 · 11/15).
  (b) nó quy đổi `duration` theo timebase KHUNG-HÌNH trong khi mp4 mang
  `1/15360` -> lệch 512 lần -> chuyển cảnh xong trong 1 khung (kiểu DỰNG SẴN của
  ffmpeg cũng dính, không phải kernel sai). Chữa: `settb=1/<fps>` trước
  `hwupload`. **`co_opencl()` phải ĐẾM KHUNG, không chỉ xem rc + kích thước file**
  — cửa fallback báo nhầm thì máy user bật nhóm GPU hỏng.
  **GPU KHÔNG rẻ hơn CPU ở quy mô này:** CPU-giây 0,484 vs 0,469 = **1,03×**
  (phí mở thiết bị OpenCL 0,094 CPU-giây/lệnh, cố định). Giá trị của nhóm GPU là
  **thêm 21 kiểu chuyển cảnh**, không phải tiết kiệm CPU.
- **CỬA CHỜ ffmpeg (`so_ffmpeg_song_song`)**: số lệnh ffmpeg chạy CÙNG LÚC do
  app tự đo theo máy, **độc lập với "số làn" user đặt**. **08/08/2026 anh Hùng
  chốt ƯU TIÊN THÔNG LƯỢNG** -> chia theo **SỐ NHÂN** (NVENC 8 nhân/lệnh, CPU
  12 nhân/lệnh), trần 4, `ECO_MODE` -> 1: **24 nhân + NVENC ra 3** · 16 -> 2 ·
  8 -> 1 · 4 -> 1. `BQ_FFMPEG_SLOTS=<N>` ép cứng để đo / gỡ rối máy user.
  Công thức CŨ (ngân sách "tổng luồng ≤ 2× nhân" chia cho SÀN ~40 luồng/tiến
  trình) ra N=1 — êm nhưng **máy bỏ không 85%** và job thứ 50 đợi 15,4 phút.
  2 mốc đó LOẠI TRỪ NHAU. Đo 50 kênh / 10 làn / 110 job (máy rảnh 12,7%):

  | | N=1 | N=3 |
  |---|---|---|
  | xong 50 clip | 1088s (18,1 ph) | **429s (7,1 ph)** |
  | CPU cả máy TB | 14,3% | **29,5%** |
  | CPU-giây ffmpeg | 1492 | 1511 (**+1,3%** — không đốt thêm) |
  | luồng đỉnh | 35 (1,46×) | 64 (**2,67×** — đã chấp nhận vượt mốc 2×) |
  | trễ UI trung vị / đỉnh | 13,7 / 37,3 ms | **13,7 / 50,3 ms** |
  | job cuối đợi | 925s (15,4 ph) | **367s (6,1 ph)** |
  | RAM cây đỉnh | 0,49 GB | 1,24 GB |

  SIẾT NÚM LUỒNG KHÔNG ĐỦ: bịt hết núm mà không có cửa chờ vẫn 397 luồng, vì 1
  ffmpeg + NVENC có **SÀN ~36-40 luồng**. Cũng đo được **N=4 KHÔNG nhanh hơn
  N=3** (37,85 vs 37,71 s) -> nút cổ chai là GPU, **đừng nới trần**.
- **CHUYỂN CẢNH DÙNG KIẾN TRÚC "2n−1 MẢNH" cho MỌI mức** (`_tach_va_noi_manh`):
  chỉ encode lại **cửa sổ chuyển cảnh 0,25-0,4s** rồi `concat` demuxer nối,
  thay vì nối n mezzanine bằng 1 lệnh `xfade` (= encode lại TOÀN CLIP). A/B cùng
  máy cùng script (3 đoạn 24s, nvenc, lặp 3): mặc định `nhe+nhe` **2,30× ->
  1,98× wall**, CPU-giây **44,48 -> 32,77 (−26%)**; riêng chuyển cảnh 1,65× ->
  **1,32×**. **Vẫn CHƯA đạt mốc ≤ 1,4×** — phần dư là hiệu ứng ĐIỂM NHẤN ở pha 2
  (một mình 1,61×). `BQ_XFADE_NOI_CA_CLIP=1` ép về đường cũ để đo A/B / gỡ rối.
  **BẪY**: đi đường cũ thì PHẢI đổi kiểu GPU `gl_*` -> kiểu CPU (`GPU_LUI_VE`),
  bỏ sót là ffmpeg báo "Not yet implemented in FFmpeg" rồi chết cả lượt xuất.
- **`-threads` TRƯỚC `-i` là luồng GIẢI MÃ, SAU `-i` là luồng ENCODE** — đặt sai
  chỗ thì ffmpeg im lặng, không báo lỗi. `decode_threads()` = 4 (ECO 2). Đo pha 1
  (`_build_seg`, bước duy nhất không có filter nên GIẢI-MÃ-BOUND): mức 4 giữ
  nguyên wall (0,99×) mà hạ 61 -> 49 luồng; **mức 1 chậm THẬT** (nvenc +30%,
  libx264 +155%) — đừng hạ về 1 dù cột luồng đẹp hơn. Kết luận cũ *"chặn luồng
  làm chậm 3,4 lần"* là **NHIỄU**: mốc đó đo lúc app chạy 96,7% CPU.
- Model suy luận cho khâu CHẤM: **ĐÃ ĐO, ĐỪNG DÙNG** (`_do_trongtai.py`):
  llama-3.3-70b xếp đúng 3/3 lượt, 1,2 giây; qwen3.6-27b **0/3 lượt**, 19,5
  giây (tiêu hết max_tokens cho khối `<think>`). Muốn chấm chắc tay thì dùng
  HỘI ĐỒNG 3 TRỌNG TÀI (`JUDGE_PANEL=1`, đang bật).
- Quy tắc sắt: test bằng THÀNH PHẦN THẬT (LLM/ffmpeg/DB thật — mock từng giấu
  bug); đường ghép đoạn phải test thứ tự hook-first (ngược thời gian) + nguồn
  VFR; key API chỉ qua ENV, không ghi file, kiểm `git diff | grep gsk_` trước
  commit.
- Test sandbox: đặt env `BQ_DB_PATH` + `BQ_DATA_DIR` sang thư mục tạm để không
  đụng dữ liệu thật (`%LOCALAPPDATA%\BQHungVideo` là data bản đóng gói).
- ĐÓNG GÓI: chạy `.venv-build\Scripts\python.exe -m PyInstaller BQHungVideo.spec --noconfirm --clean`. **KHÔNG dùng `.venv`** — venv đó không có PyInstaller, gọi vào là báo "No module named PyInstaller" mà `dist/` VẪN CÒN bản build cũ nên rất dễ tưởng đã build xong (sập bẫy 06/08/2026: dist/ là bản 22/07). Sau build phải KIỂM: đếm file trong `dist/BQHungVideo/_internal/app/assets/sfx` và xem ngày sửa của .exe.
- Chủ app: BQ Hung — trao đổi tiếng Việt; báo cáo phải kèm số đo thật.
