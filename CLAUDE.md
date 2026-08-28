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
     **CHỐT CHỐNG-PASS-OAN CỦA CA 8 PHẢI TÁCH 2 NGUYÊN NHÂN "hai bản TRÙNG
     NHAU" (sửa 09/08/2026):** bản đầu FAIL bất cứ khi nào bản mốc trùng file
     đang test, nên **mọi nhánh KHÔNG động tới `ffmpeg_utils.py` đều ĐỎ OAN
     VĨNH VIỄN** (đo: nhánh `xem-hinh-theo-kenh` ra 62 OK · 1 FAIL) — mà cổng
     đỏ oan thì người ta bỏ qua nó, nguy hiểm hơn hẳn (bài học cổng 41 và 47).
     Dấu hiệu tách đúng là **"HEAD có phải TỔ TIÊN của mốc không"**:
     TRÙNG + HEAD là tổ tiên = mốc ĐÃ CHỨA commit của nhánh -> FAIL như cũ ·
     TRÙNG + HEAD KHÔNG phải tổ tiên = nhánh đơn giản không sửa file đó ->
     **bất biến ĐÚNG DO XÂY DỰNG**, vẫn chạy tiếp phép đo PSNR. Thử phá
     (`BQ_MOC_REF=HEAD`) -> vẫn **62 OK · 1 FAIL**; chạy thật
     (`BQ_MOC_REF=378230e`) -> **65 OK · 0 FAIL**, PSNR 99,0 dB × 5 mốc.
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
     **+ `LICENSES.txt` (16/08/2026) — LỖ HỔNG PHÁP LÝ THẬT, không phải tài
     liệu cho đẹp.** Bộ cài đang PHÁT HÀNH `bin/ffmpeg.exe` bản
     `--enable-gpl --enable-version3` (**GPL-3.0-or-later**, có
     `librubberband` GPL-2.0 mà `thay_giong` dùng để co giãn tiếng) nhưng
     **KHÔNG kèm văn bản giấy phép và không chỉ chỗ lấy mã nguồn** — app vẫn
     chạy, không một dòng báo, chỉ có rủi ro. `LICENSES.txt` nay gồm 8 mục:
     ffmpeg/ffprobe · frei0r (trỏ về `NGUON_GIAY_PHEP.md` đã có) · Piper
     GPL-3 + espeak-ng · giọng `vais1000` (khối ghi công CC BY 4.0, **kèm cả
     chỗ CHƯA đối chiếu được** với trang gốc IEEE) · **edge-tts LGPLv3 kèm
     nguyên văn câu tác giả *"It shouldn't be used for commercial reasons"***
     (ghi trung tính: đó KHÔNG phải điều khoản LGPL, rủi ro thật nằm ở điều
     khoản dịch vụ Microsoft — anh Hùng dùng hằng ngày nên cần biết) · yt-dlp
     Unlicense · kho tiếng động CC0 · phông chữ OFL (ghi thẳng là **CHƯA rà
     từng file**). Khai ở **CẢ HAI** cửa đóng gói. Cổng đòi nêu **ĐÍCH DANH**
     từng thành phần — chỉ hỏi "file có tồn tại không" thì để lại file rỗng
     vẫn xanh. THỬ PHÁ 2 phép, bắt được cả 2.
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
     `app/assets/sfx/muc_do.json` (mean/max/**đỉnh RMS 50 ms** từng file, tra
     0 ms); `_do_muc_clip` đo nền + MỨC LỜI + đỉnh của CHÍNH clip sắp xuất
     (ngoài cửa chờ, chỉ giải mã audio); `tinh_gain_sfx` = `đích − đỉnh RMS
     50 ms của file`. Thêm `loai_sfx_theo_hieu_ung` (zoom/rung -> impact · loé
     sáng -> reveal · glitch -> scratch · mờ/tối -> suspense/pop · chữ ->
     drumroll) và **DUCKING** (`_bieu_thuc_duck`, nửa hình sin vào/ra êm).
     **BẢN ĐẦU CỦA CỔNG NÀY LÀ CỔNG VÔ DỤNG — ĐÃ THAY 09/08/2026.** Nó chỉ đo
     trên **MỘT nguồn nền yên** (-23,6 dBFS) rồi kết luận "+10..+17 dB, ĐẠT";
     đo lại trên clip THẬT (nền -15,7) thì **2/5 mốc NHỎ ĐI**. Nó còn lấy
     "nền" = **trung vị CẢ CLIP**, mà trung vị của clip ồn CHÍNH LÀ mức lời ->
     tiếng động chỉ cần bằng lời đã tự cho điểm. Và nó **nhấp nháy** (5 lượt
     hỏng 1) vì file tiếng động bốc ngẫu nhiên.
     **NAY (xem khối "TIẾNG ĐỘNG NGHE ĐƯỢC TRÊN MỌI LOẠI NỀN" bên dưới):** CA 2
     đo trên **3 VIDEO THẬT nền khác hẳn nhau** (mean -25,8 / -16,2 / -16,6
     dBFS, ca yên cố ý để **1 ĐOẠN** = không có điểm nối nào), mọi ngưỡng so
     với **NỀN CỤC BỘ** (bpv20 trong ±1,5 s quanh CHÍNH mốc đó). 4 điều bắt
     buộc: nổi **>= +6 dB** · **không mốc nào nhỏ đi** (sàn -0,5 dB) · lớp SFX
     **<= 1,5x mức lời** · **đỉnh file <= -1 dBFS + 0 mẫu chạm trần** đọc bằng
     `astats`. **SỐ ĐO:** 12/12 mốc đạt, thấp nhất **+8,5 dB**, 0 mốc nhỏ đi,
     đỉnh file -3,99/-1,47/-1,66 dBFS. Chạy **5 lượt liên tiếp ĐẠT cả 5**.
     **BẪY VIẾT CỔNG (sập 1 lần):** mỗi dòng `astats` mở đầu bằng
     `[Parsed_astats_0 @ ...]` nên `startswith("Peak level dB:")` KHÔNG BAO GIỜ
     khớp -> mọi file ra -99 dBFS và ca "không méo" tự PASS vĩnh viễn. Phải
     dùng `in`, không dùng `startswith`.
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
  46. `_test_lop_phu.py` → **NHÓM LỚP PHỦ HẠT + CHỌN THEO NỘI DUNG CẢNH**
     (09/08/2026). Anh Hùng: *"tuyết rơi, trái tim bay, với rất nhiều kiểu khác
     thêm vào — **nhưng phải hợp lý, tuỳ cảnh mới chọn chứ không chọn bừa
     bãi**"*. 27 kiểu cũ đều là CHỈNH MÀU/NÉT/NHIỄU; đây là nhóm đầu tiên
     **chồng VẬT THỂ** lên hình, và cũng là nhóm đầu tiên MANG NGHĨA — nên phải
     có cửa chọn riêng.
     **KIẾN TRÚC (3 quyết định, mỗi cái có số):**
     (a) **SINH 100% BẰNG ffmpeg, 0 BYTE tài nguyên** (`color`+`geq`+
     `alphamerge`+`scale`+`overlay`; confetti lấy màu từ `gradients`). Vì vậy
     `.spec` và `release.yml` **KHÔNG phải sửa** — khác hẳn bẫy cũ "quên khai
     `app/assets/hieu_ung` nên .exe mất sạch hiệu ứng". Mục 3 của
     `NGUON_GIAY_PHEP.md` đã cấm 6 file overlay không rõ nguồn; đường này né
     hẳn chuyện bản quyền.
     (b) **CẮT ĐÚNG CỬA SỔ RỒI `concat`** (cùng khuôn `_SH_MAU` của nhóm
     shader). Đo riêng phần kiến trúc: `split/trim/concat` RỖNG tốn **−0,27
     CPU-giây** (tức không tốn gì), `eq` cũ **+0,56**, còn `geq` sinh hạt là chỗ
     đắt thật.
     (c) **MÀU HẰNG + CHỈ ALPHA ĐỔI**: `geq` chỉ tính 1 mặt phẳng (rẻ hơn ~4
     lần) và phóng to không ra viền bẩn.
     **CHỌN THEO NỘI DUNG (`app/core/lop_phu.py`) — phần khó nhất:**
     Nguồn hiểu nội dung là 2 thứ CÓ SẴN: `vision_digest` (đọc CACHE, **KHÔNG
     gọi thêm LLM** — đo thật 219 giây/video, nhân 300 kênh là không dùng được)
     và **chép lời của chính đoạn đó** (`loi_theo_doan`, không lấy cả video).
     Mốc digest được `loc_digest_theo_doan` đổi sang timeline ĐẦU RA và **bỏ mốc
     rơi ngoài đoạn cắt** — không lọc thì mốc "snowy mountain" ở phút 12 vẫn bật
     tuyết cho clip cắt ở phút 2. Chấm điểm theo **SỐ MỐC** (không phải số lần
     chữ), từ khoá PHỤ một mình trần 3,1/6,0 nên **không bao giờ đủ** ngưỡng
     0,55; mỗi kiểu có danh sách **CẤM** (bếp/nấu ăn cấm tuyết; thi đấu/trọng
     tài/bàn thắng cấm trái tim); hai kiểu KHÁC HỌ điểm sát nhau = nội dung pha
     tạp -> **KHÔNG thêm gì**. Không digest -> bỏ qua nhóm, ghi
     `logs/lop_phu_<ngày>.log`.
     **BẤT BIẾN SỐNG CÒN: KHÔNG kiểu lớp phủ nào có mặt trong
     `hieu_ung._UV_THEO_LOAI`** — đường chọn theo SỐ ĐO không được với tới nó,
     nếu không thì một giây tiếng vọt lên là tuyết rơi trong bếp. Cổng quét tĩnh
     bảng đó + chạy 200 bộ số đo bắt `chon_hieu_ung` không đẻ ra lớp phủ lần
     nào. Lớp phủ vào qua tham số MỚI `chon_hieu_ung(dat_truoc=...)`, nên vẫn ăn
     chung ngân sách `TY_LE_MAX` 10% + trần `DIEM_MAX` + luật `CACH_MIN`.
     **3 BẪY ĐO ĐÃ SẬP KHI VIẾT CỔNG NÀY:**
     · **đo RÒ bằng file nén mất dữ liệu**: `-crf 18` tự nó làm **0,157%** điểm
       ảnh ngoài cửa sổ lệch >12 — không phân biệt nổi với rò thật. `-qp 0` ra
       đúng **0,0000%**.
     · **đo LỆCH MÀU bằng `blend=difference` rồi lấy UAVG**: đó là lệch từng
       điểm ảnh, che 18% khung bằng hạt TRẮNG cho ra **11,6** mà không hề "tím
       cả khung". Thước ĐÚNG (cũng là thước đã loại `rgbashift` U+7,16 và
       `baltan` U−3,08) là **PHÂN BỐ CHROMA cả khung**: UAVG/VAVG/SATAVG trước
       so với sau. Đo lại: cao nhất **dU 2,27** (lá rơi), còn lại < 1,4.
     · **mẫu số của phép đo chi phí**: lấy "bản không lớp phủ" = một lượt mã hoá
       trần (0,32 s) thì phí cố định đọc thành **2,27x**; mẫu số đúng là
       `export_canvas_clip` mức "tat". Và phải **ĐAN XEN + TRUNG VỊ** — đo liền
       mạch ra "lớp phủ NHANH HƠN bản tắt (0,52x)", chuyện không thể xảy ra.
     **SỐ ĐO CHỐT:** 10/10 kiểu ĐẠT · thấy được **9,7 – 27,6%** điểm ảnh · rò
     ngoài cửa sổ **0,0000%** · hai mép cửa sổ **0,0000%** (bao nửa hình sin
     `_LP_SONG` chia cho `d − 1/fps` nên khung đầu VÀ khung cuối đều đúng 0) ·
     lệch màu **dU ≤ 2,27 · dV ≤ 1,37** (trần 3,0) · chi phí thêm **+1,8 đến
     +4,7 CPU-giây/clip** và là **HẰNG SỐ** (clip 2,6s/10s/20s đều +4,4-4,7 ->
     1,90x / 1,26x / 1,12x) vì `geq` chỉ chạy trong cửa sổ 0,8 giây.
     **`geq` + `st()/ld()` chạy đa luồng lát cắt có TIỀN ĐỊNH không?** ĐÃ ĐO:
     2 lượt dựng + 1 lượt `-filter_threads 1` ra **YMAX = 0** (giống từng điểm
     ảnh). Cổng giữ ca này vì bản ffmpeg sau đổi hành vi là ra hạt nhấp nháy mà
     không ai biết. Cùng ca đó canh luôn **`gradients` phải có `seed`** — mặc
     định `seed=-1` là NGẪU NHIÊN mỗi lượt xuất.
     **MỞ RỘNG 10 -> 46 KIỂU / 14 CẢNH (09/08/2026).** Anh Hùng: *"càng nhiều
     kiểu càng tốt, 100 kiểu cũng được, **nhưng AI phải hiểu ngữ cảnh, thêm hợp
     lý, không thêm bừa bãi làm video chất lượng thấp đi**"*.
     **CÁCH MỞ RỘNG ĐÚNG — ĐÃ CHỐT, đừng làm khác:** thêm **BIẾN THỂ NHÌN trong
     CÙNG một cảnh**, KHÔNG bịa thêm ngữ cảnh không nhận ra được. Lý do là số
     học: mỗi CẢNH mới là một cơ hội NHẬN NHẦM (bảng từ khoá phải đoán "cảnh này
     là gì"), còn BIẾN THỂ thì dùng LẠI đúng bằng chứng đã chấm đạt ngưỡng —
     rủi ro thêm bằng **0**, mà 3 Part của một video thôi kêu giống hệt nhau.
     Vì thế 36 kiểu mới đều chỉ là 1 trong 4 phép biến đổi của khuôn đã đo
     (`_lp` + `_luoi`): **cỡ ô · tốc độ rơi · HÌNH hạt · MÀU** — không cơ chế
     mới nào. Bảng: tuyết 4 · trái tim 4 · lấp lánh 4 · confetti 4 · mưa 4 ·
     bokeh 4 · lửa 3 · tia sáng 3 · bụi phim 3 · lá rơi 3, cộng **4 CẢNH MỚI**
     (dưới nước 3 · ma quái 3 · tiền bạc 3 · công nghệ 2) — chỉ nhận cảnh nào
     digest tả bằng từ RẤT khó nhầm; cảnh chỉ đoán được bằng từ chung chung
     ("food", "travel", "sport") thì **KHÔNG thêm**.
     `Luat.bien` = `((khoá, (gợi ý…)), …)`; `_chon_bien` đi 2 đường: **gợi ý
     riêng** ("blizzard" -> bão tuyết dày, "icicle" -> tinh thể) rồi **rải đều
     TIỀN ĐỊNH** theo `crc32` của CHÍNH bằng chứng (KHÔNG `hash()` — nó băm kèm
     `PYTHONHASHSEED` ngẫu nhiên mỗi tiến trình nên 3 làn xuất song song ra 3
     biến thể khác nhau, không tra lại được). Biến thể bị máy nhân viên loại ->
     LÙI sang biến thể khác cùng cảnh, không mất lớp phủ.
     **SỐ ĐO 46/46 ĐẠT** ở đúng 1080x1920: thấy được **8,16 – 36,12%** điểm ảnh
     · rò ngoài cửa sổ **0,0000%** · hai mép **0,0000%** · |dU| ≤ 2,29 ·
     |dV| ≤ 2,55 (trần 3,0) · bão hoà ≥ 0,83 (sàn 0,80) · sáng đỉnh ≤ 1,134
     (trần 1,45). Lần đo ĐẦU 39/46 đạt, 7 kiểu phải sửa theo số:
     · **BÀI HỌC LỚN — MỘT dải rộng thì lệch màu, NHIỀU dải hẹp thì không.**
       `tia_sang_doc` bản 1 dải rộng đo **dU 4,49**, trong khi `nang_xuyen`
       (nhiều tia song song, tổng diện tích còn LỚN HƠN) chỉ **dU 0,74**. `dU`
       là lệch U TRUNG BÌNH CẢ KHUNG: một dải rộng nằm trọn trên MỘT vạch màu
       của `testsrc2` nên kéo lệch hẳn một phía; nhiều dải hẹp rải khắp khung
       thì phần kéo của các vạch màu khác nhau TRIỆT TIÊU nhau. Cùng nguyên
       nhân: `suong_mo` ô 64 px (chỉ 3x6 mảng) dV 3,52 -> ô 40 px còn 0,93;
       `song_nuoc` vân thưa dV 4,39 -> tăng tần số cho vân mịn còn 0,45.
       **Bản 2 của `tia_sang_doc` vẫn hỏng (dV 3,30) vì lý do THỨ HAI: dải DỌC
       cộng hưởng với vạch màu DỌC của `testsrc2`** — phải nghiêng nhẹ
       (X + 0,20·Y) cho mỗi dải cắt ngang nhiều vạch, khi đó còn **0,47**.
     · màu hạt vẫn phải NHẠT: `bong_bay` 4 màu `0xB4…` phủ 24% ra **dV 4,39**;
       nhạt về `0xD8…` + thu bán kính (24% -> 14,7%) thì còn **1,33**.
     · hạt quá nhỏ/thưa thì KHÔNG THẤY: `lap_lanh_bui` **4,43%** ·
       `xuoc_phim` **5,49%** · `la_bay` **7,07%** (ngưỡng 8%).
     **TỐI ƯU BẮT BUỘC — `_quay()`:** hạt XOAY viết thẳng ra là 4 phép lượng
     giác **mỗi ĐIỂM ẢNH** (`cos(g)`/`sin(g)` mỗi cái 2 lần). Cổng 46 CA 5 bắt
     được: `canh_hoa` **+6,27** và `tan_lua_day` **+6,52** CPU-giây/clip trong
     khi trung vị nhóm **4,89**, trần 6,0. `_quay` cất sẵn `cos` vào `ld(3)`,
     `sin` vào `ld(5)` -> còn 2 phép, áp cho cả 8 kiểu có xoay.
     **BẪY ĐI KÈM, ĐÃ SẬP NGAY:** `la_kim_tuyen` là kiểu DUY NHẤT vừa xoay vừa
     nhấp nháy và nó đang để hệ số nhấp nháy ở **`ld(3)`** — ghi đè đúng ô
     `_quay` vừa cất `cos` vào, tức hạt xoay theo… nhịp nhấp nháy. ffmpeg vẫn
     `rc=0`, đủ khung, không một dòng báo; **chỉ số đo tố giác** (diện tích
     12,38% -> 13,27%). Nay nhấp nháy để `ld(4)` và cổng 46 CA 6 có **ca quét
     tĩnh**: kiểu nào gọi `_quay` rồi còn `st(3,`/`st(5,` nữa là FAIL.
     **CỔNG 46 CHẤM THEO *CẢNH*, KHÔNG THEO *KIỂU*** — có biến thể rồi mà vẫn
     ép ra đúng một khoá thì chính là cấm cái đa dạng vừa làm ra (ca "em bé" ra
     `trai_tim_nho`, ca "cảnh đêm" ra `den_nhap_nhay` đều ĐÚNG HƠN). Đổi lại,
     mệnh đề "tuyết không rơi trên video nấu ăn" phải chặn **CẢ HỌ** 4 biến thể,
     chặn mỗi `tuyet_roi` là để lọt `tuyet_bao`/`tuyet_bui`.
  47. `_test_hook_to_mo.py` → **HOOK CHỌN THEO TÒ MÒ, KHÔNG THEO TIẾNG TO**
     (`app/ai/hook_to_mo.py`). v2.20.0 `_pick_hook_seg` dò cửa sổ 2,5 s có
     `_audio_score` lớn nhất = chọn theo ĐỘ ỒN. Nay chấm từng CÂU chép lời (đã
     có sẵn: 0 giây mạng, 0 lượt LLM) theo 5 nhóm tín hiệu "để lại câu hỏi /
     thông tin dở dang", trừ điểm câu chào hỏi. Đếm token bằng
     `recap._word_tokens` (CJK không có dấu cách). **ĐO A/B trên 8 VIDEO THẬT
     4 thứ tiếng, chép lời Groq THẬT:** hook CŨ rơi vào chỗ **KHÔNG MỘT CHỮ
     NÀO** 1/8 video · hook MỚI chọn được 4/8 · tò mò cao hơn CŨ **4**, bằng 0,
     **thấp hơn 0**. Câu "và rồi … phát hiện ra" 4 thứ tiếng đều 0,797; câu
     "xin chào các bạn" đều 0,000 (ngưỡng 0,34). BẤT BIẾN: video KHÔNG LỜI ->
     `_pick_hook_seg` ra Y HỆT cửa sổ cao trào tiếng cũ.
     **3 LỖI CỦA CHÍNH CỔNG (không phải lỗi app) đã sửa:** unpack sai bộ 3 của
     `KHO` · lấy đúng `so//nhóm` video nên 1 video bị loại là ĐỎ OAN (nay lấy
     dư +2/nhóm và **ĐAN XEN theo vòng**, không thì 2 nhóm đầu chiếm hết suất
     và ca "phủ 4 ngôn ngữ" hỏng oan) · quét tĩnh lọc bằng `startswith("#")`
     nên chính dòng ghi chú *"CẤM `.split()`"* bị kể là vi phạm -> ĐỎ OAN vĩnh
     viễn; nay `_ma_that()` dùng `tokenize` bỏ COMMENT+STRING, kèm 2 ca TỰ KIỂM
     BỘ DÒ.
  48. `_test_lop_phu_loi.py` → **LỚP PHỦ ĐOÁN CẢNH BẰNG LỜI THOẠI.** Anh Hùng
     cắt trên v2.20.0 **không thấy tuyết/trái tim nào**: `VISION_CUT` mặc định
     TẮT nên `vision_digest` rỗng -> nhật ký ghi *"không có vision_digest ->
     bỏ qua nhóm lớp phủ"* -> **46 kiểu gần như không bao giờ xuất hiện**. Nay
     `lop_phu.digest_tu_loi()` biến MỖI CÂU chép lời thành 1 mốc digest trên
     timeline ĐẦU RA (cờ `loi=True`); `ffmpeg_utils` chỉ gọi khi digest RỖNG ->
     **XEM HÌNH VẪN ƯU TIÊN**. KHÔNG truyền kèm `loi` -> không đếm MỘT bằng
     chứng HAI lần; bậc thang giữ nguyên ý nghĩa: phải **2 CÂU** nói tới cảnh
     đó (2×2,0/6,0 = 0,667 > 0,55). Chốt chặn giữ nguyên: `NGUONG_TIN` 0,55 ·
     nhóm PHỤ trần 0,52 · danh sách CẤM · 2 họ sát nhau = bỏ · tối đa 1/clip.
     **BẪY BỎ DẤU — ĐO RA 9 CÁI, TẤT CẢ LÀ TỪ KHOÁ MẠNH** (`_do_lop_phu_loi.py`,
     corpus lời thật): `thế là **rồi**`→`la roi` · `rất **tiếc**`→`tiec` ·
     `**anh cứ**`→`anh cu` · `**anh nên**`→`anh nen` · `**nằm mơ**`→`nam mo` ·
     `**có đâu**`→`co dau` · `**lịch sự**`→`lich su` · `mà **ấm**`→`ma am` ·
     `**có điện**`→`co dien`. (3 bẫy anh Hùng nêu đích danh — `tuyết`/`tuyệt
     vời`, `mưa`/`mùa đông`, `máu`/`màu sắc` — đo ra là **ĐÃ SẠCH SẴN** vì từ
     khoá là CỤM 2 CHỮ; cổng vẫn giữ đủ 3 ca đó.) **CHỮA:** `_DAU_VN` (241 từ
     khoá tiếng Việt dạng CÓ DẤU) + `_bien_dau`/`_rd_*` — đường LỜI dò trên
     text CÒN DẤU, đường XEM HÌNH giữ y nguyên bảng bỏ dấu (mô tả digest là
     tiếng Anh). Sửa luôn 1 **BUG CŨ** của đường xem hình: tham số `loi` trước
     đây cũng dò bằng bảng BỎ DẤU. Đo: bẫy bắn nhầm **9/16 -> 0/16**, câu đúng
     nghĩa còn khớp **13/13**.
     **TIẾNG NHẬT / HÀN** (`_CJK`, 14 cảnh × mạnh/phụ/CẤM). Luật sắt: CJK KHÔNG
     CÓ DẤU CÁCH nên từ khoá NGẮN khớp BÊN TRONG từ dài -> **tối thiểu 2 ký
     tự**. 4 bẫy đã canh sẵn: `火` trong 火曜日 (thứ Ba) · `불` trong 불편/불가능
     (bất tiện) · `눈` tiếng Hàn vừa là TUYẾT vừa là MẮT · `비` vừa là MƯA vừa
     là tiền tố so sánh.
     **CA BẮT BUỘC ĐO TRÊN FILE XUẤT THẬT** (ffmpeg thật, clip 10 s): clip nói
     "tuyết rơi" x2 -> lớp phủ **21,66%** điểm ảnh · clip nói **"TUYỆT VỜI"**
     x2 -> **0,00%**.
     **2 LỖI CỦA CHÍNH CỔNG đã sửa:** clip 2,6 s thì ngân sách 10% chỉ 0,26 s <
     `DAI_MIN` 0,8 s nên MỌI lớp phủ bị "nhường điểm nhấn" -> đo ra 0,00% ở CẢ
     HAI ca, suýt kết luận oan là đường lời không chạy (nay clip 10 s); câu chép
     lời phải nằm TRONG đoạn cắt.
  49. `_test_mach_lac.py` → **XEM LẠI BẢN GHÉP CÓ MẠCH LẠC KHÔNG**
     (`app/ai/mach_lac.py`). App chọn 3 đoạn hay rồi ghép và tới v2.20.0 **chưa
     bao giờ xem lại bản ghép**. Nay 1 lượt LLM NGẮN/Part đọc LỜI THOẠI của
     chính các đoạn đã chọn (chỉ dùng `vision_digest` nếu CACHE đã có — không
     bao giờ tự bật AI xem hình), trả `{mach_lac, thu_tu, bo, vi_sao}` -> đổi
     thứ tự / bỏ 1 đoạn. Gọi **TRƯỚC** `_trim_junk_edges`/`_enforce_len` để
     `_enforce_len` vẫn là NGƯỜI NÓI CUỐI về độ dài (bài học cổng 12). Công tắc
     `settings.HAU_KIEM_GHEP`.
     **FAIL-SAFE là điều kiện tiên quyết:** đo 10 kiểu hỏng (mạng chết · hết
     lượt · JSON rác · `thu_tu` thiếu/lặp số · `bo` ngoài phạm vi · chuỗi rỗng ·
     prose · `null` · lỗi lạ) -> **10/10 GIỮ NGUYÊN** lựa chọn ban đầu.
     `LLMTooLarge` NỔI LÊN NGUYÊN VẸN, đo được **0/38 key bị khoá** (cổng 28).
     Chốt an toàn: không bao giờ còn < 2 đoạn · không tụt dưới Min người dùng
     đặt · `mach_lac >= 6` thì KHÔNG ĐỘNG VÀO.
     **LỖI THẬT CỔNG NÀY LÔI RA — đúng loại "chỉ số đo tố giác":** prompt bản
     đầu chỉ ghi `"mach_lac": 0-10` mà **KHÔNG NÓI CHIỀU CỦA THANG**, nên model
     chấm ĐỘ LỦNG CỦNG chứ không phải độ mạch lạc. Đo bằng Groq THẬT: bản XUÔI
     (1-2-3) -> **0/10** lý do *"Mạch chuyện rõ ràng và logic"*; bản ĐẢO LỘN
     (3-1-2) -> **8/10** lý do *"thứ tự thời gian không logic"* — ngược hoàn
     toàn, và vì 8 ≥ ngưỡng nên đề nghị SỬA ĐÚNG của nó bị bỏ đi. Nay prompt
     ghi rõ *"10 = RẤT MẠCH LẠC … 0 = RỜI RẠC, càng cao càng tốt"*. Đo lại:
     XUÔI **10/10** · ĐẢO LỘN **2/10** -> tự đổi về 1-2-0 (đúng thời gian).
     **QUY TẮC CHUNG rút ra: mọi thang điểm đưa cho LLM phải nói rõ CHIỀU.**
  50. `_test_so_lieu.py` → **KHUNG NHẬN SỐ LIỆU VIEW THẬT** (`app/ai/so_lieu.py`
     + bảng `clip_so_lieu`). **NÓI THẲNG: app KHÔNG tự lấy được view** (không
     API, không đăng nhập được kênh anh Hùng) — chỉ dựng ĐƯỜNG NHẬN. Đọc
     CSV/TSV/JSON, tự đoán bảng mã (utf-8/16/cp1258) + dấu phân cách, đọc được
     `1.2K` `88K` `1,234` `1.234.567` `0:21` `1:02:03`, tên cột tiếng Việt LẪN
     tiếng Anh. Khoá theo **TÊN FILE** chứ không theo `clip_id` (clip cũ có thể
     đã archived/xoá, tên file thì còn); nhập lại = GHI ĐÈ.
     Xếp hạng theo **TỈ LỆ XEM HẾT** trước, view thô sau — đo: clip **2.400
     view xem hết 79%** đứng TRÊN clip **12.000 view xem 14%**.
     **BẤT BIẾN**: chưa nhập -> khối prompt `""` -> prompt Y HỆT hiện tại.
     **SÀN**: dưới `TOI_THIEU`=6 clip thì ghi vào DB nhưng KHÔNG dạy AI (2 điểm
     dữ liệu là nhiễu). **KHÔNG BAO GIỜ NÉM LỖI**: 8 kiểu file xấu đều trả
     `([], lý do)`. Cửa nhập ở menu ⋮ hộp Dây chuyền, nhãn KHÔNG EMOJI.
     **ANH HÙNG CẦN XUẤT GÌ:** TikTok *Studio sáng tạo → Phân tích → Nội dung →
     Tải xuống dữ liệu*; YouTube *Studio → Số liệu phân tích → Nâng cao → Xuất
     → CSV*. File cần 3 cột: tên file clip · số lượt xem · thời lượng xem trung
     bình (giây hoặc `0:21`). Có thêm cột thời lượng clip thì tính được tỉ lệ
     xem hết.
  51. `_test_xem_hinh_kenh.py` → **AI XEM HÌNH BẬT/TẮT RIÊNG TỪNG KÊNH**
     (`projects.xem_hinh`). Anh Hùng 09/08/2026: *"cứ thêm phần bật tuỳ chỉnh
     từng kênh đã, tôi test xem sao, nếu oke thì mặc định tất cả"*.
     **ĐO A/B 60 LƯỢT THẬT TRƯỚC KHI LÀM** (6 video × 5 vòng × 2 bên, đan xen):
     bật xem hình **ĐỔI LỰA CHỌN THẬT** — video 728 s chồng lấn **6,8%**
     (p=0,024) · 150 s **23,4%** (p=0,008) · **53 s chọn Y HỆT (100%)**.
     Dấu hiệu KHÔNG phải mật độ lời (hiệu ứng mạnh nhất ở video **4,25 từ/giây**
     — giả thuyết "nói nhiều thì chép lời đủ rồi" **SAI**) mà là **SỐ MỐC
     HÌNH**: cần **>= 8 mốc**. Giá thật chỉ **+1,6 .. +10,6 giây/video**, trừ 1
     video dính Groq **503 'over capacity'** cả 5/5 vòng -> **+244 giây**.
     **BA TRẠNG THÁI, KHÔNG PHẢI HAI** — cột khai `INTEGER` NULLABLE:
     `NULL` = kênh CHƯA ĐỤNG TỚI -> theo mặc định app (`VISION_CUT`, đang TẮT) ·
     `1`/`0` = user đã chọn. Ép `NOT NULL DEFAULT 0` là **mất luôn đường đổi mặc
     định toàn cục** cho ~300 kênh chưa đụng (đúng cái `tpl_name`=`''` né được).
     **CỬA DUY NHẤT**: việc tra ô nằm TRONG `vision_digest.build_vision_digest`
     (`kenh=_TU_TRA` -> `xem_hinh_kenh(video_id)`), KHÔNG bắt caller tự truyền —
     nếu không thì lặp đúng lỗi (a) của cổng 19 (mẫu-theo-kênh chỉ áp ở dây
     chuyền, bấm tay vẫn ăn cấu hình trang chính). Cổng có ca **quét tĩnh bằng
     `tokenize`**: không file nào được gọi thẳng `vision_digest_enabled()`.
     **CÓ HAI CỬA VISION, KHÔNG PHẢI MỘT** (rà soát mới lôi ra): ngoài
     `build_vision_digest` còn `m1._vision_rescore` (chấm điểm TỪNG ĐOẠN bằng
     hình) — nó **chỉ bị chặn bởi `LIGHT_MODE`**, nên máy tắt `LIGHT_MODE` mà
     kênh chọn TẮT thì nó **vẫn bắn**. Nay `generate_highlights` chặn bằng ô của
     kênh: `False` -> `used_vision=False` · `True` -> chỉ bật khi **ĐÃ CÓ
     digest** (không có = app vừa cố ý bỏ qua vì nguồn ngắn/503, đừng vòng ra
     cửa sau tiêu đúng số lượt vừa tiết kiệm) · `None` -> y hệt v2.21.0.
     Đo thật (LIGHT_MODE tắt, `generate_highlights` thật): kênh TẮT **0 lượt**
     vision ở CẢ HAI cửa · kênh CHƯA ĐỤNG **5 lượt** (không sửa quá tay).
     **2 CHỐT TIẾT KIỆM (đo mới có, đừng chỉnh mò):**
     (a) `MOC_TOI_THIEU = 8` — dù kênh BẬT, `len(pick_frame_times())` < 8 thì
     BỎ QUA + ghi `logs/vision_<ngày>.log`. Số mốc app tính ra khớp đúng bộ
     A/B: **53 s -> 3 · 150 s -> 8 · 728 s -> 12**. `bat_buoc` (video KHÔNG
     lời) được đi tiếp: lúc đó hình là căn cứ duy nhất.
     (b) `VISION_HAN_GIAY = 28` + `VISION_503_TOI_DA = 2` + `la_loi_qua_tai()`
     — **503 ≠ 429 ≠ 413**, mỗi loại một đường: 429 phạt key + đợi · 413 thu
     nhỏ · **503 BỎ XEM HÌNH cho video đó, KHÔNG phạt key**. Đo: dừng ở **2/5
     lượt (0,45 s)** thay vì nướng hết, **0/4 key bị khoá**, clip vẫn ra
     (`generate_highlights` thật ra `count=2` dù vision 503 + LLM chữ chết).
     Digest bị CẮT NGANG thì **KHÔNG đóng dấu vào cache** (Groq quá tải là
     chuyện 5 phút; đóng dấu là video mang bản cụt VĨNH VIỄN).
     **UI**: bảng Dây chuyền 9 -> **10 cột**, cột 5 = "AI xem hình" (combo
     `(mặc định: TẮT)` / `BẬT xem hình` / `TẮT xem hình`); nhãn mục đầu phải
     HIỆN mặc định thật (bài học cổng 16 v2.6.25a). Gán 1 lượt: **bấm tiêu đề
     cột 5** hoặc menu 🔧 -> `_pipe_bulk_xem_hinh` -> `_pipe_apply_xem_hinh_all`
     lấy pid từ **BẢNG** (`_pipe_rows_pid`) nên tôn trọng nhóm + ô tìm. Nhãn
     mới KHÔNG EMOJI.
     **BẤT BIẾN ĐO ĐƯỢC**: **16/16** tổ hợp `USE_VISION × VISION_CUT ×
     LIGHT_MODE × bat_buoc` với kênh NULL cho ra ĐÚNG quyết định của mốc
     `378230e`, nạp bằng `git show <mốc>:app/core/vision_digest.py` (**KHÔNG
     dùng `main`** — sau gộp nó trùng mã đang test, PASS OAN), kèm chốt "bản
     mốc phải KHÁC bản đang test". **THỬ PHÁ** (bỏ nhánh `kenh is True/False`):
     cổng FAIL đúng **9 mục** -> không phải con dấu.
     **BẪY ĐÃ SẬP KHI VIẾT CỔNG NÀY (3 cái):** (1) quét tĩnh bằng `in` chuỗi ->
     chính DÒNG GHI CHÚ giải thích bản vá bị kể là vi phạm (đỏ oan, y hệt cổng
     47) — phải `tokenize` bỏ COMMENT+STRING, kèm ca TỰ KIỂM BỘ DÒ; (2)
     `time.monotonic()` trên Windows nhảy ~15 ms nên `_ChotQuaTai(han_giay=0)`
     đo ra `da_ton()=0.0` và `0 > 0` là False -> ca "quá giờ" FAIL OAN; phải
     đẩy lùi `chot.moc` để giả lập thời gian đã trôi; (3) **bản chép lời giả
     thiếu khoá `words`** -> `co_loi_noi_that` tính mật độ `len(words)/giây` ra
     **0,00** -> app gán "video KHÔNG có lời" -> `bat_buoc=True` -> xem hình bật
     BẤT KỂ ô của kênh -> cổng đo ra 5 lượt và suýt kết luận oan là bản vá rò.
  53. `_test_thay_giong.py` → **THAY GIỌNG NÓI: thay LỜI THOẠI sang tiếng
     khác, GIỮ NGUYÊN nhạc nền + tiếng động** (`app/core/thay_giong.py`,
     v2.24.0, 14/08/2026). KHÁC HẲN `dubbing.py`: `dubbing` CHỒNG giọng mới lên
     tiếng gốc (voice-over, tiếng gốc vẫn nghe thấy); ở đây tiếng gốc bị **TÁCH
     BỎ HẲN** rồi đặt giọng đã dịch vào chỗ trống. **ĐẠT 33 · HỎNG 0.**
     **BƯỚC 1 (TÁCH GIỌNG) LÀ NỀN MÓNG — ĐO XONG MỚI ĐƯỢC LÀM TIẾP.** Đo trên
     2 video THẬT 60 giây (Trung + Anh), máy này CPU (torch `2.13.0+cpu` nên
     `cuda.is_available()` = False KỂ CẢ khi máy có RTX 3060):

     | | thời gian/1 phút | RAM đỉnh | giảm giọng | giữ nhạc | **RÒ RỈ TỪ** |
     |---|---|---|---|---|---|
     | demucs (zh) | 24,88s (0,415×) | 1281 MB | 13,79 dB | −3,28 dB | **2,3%** |
     | nhẹ (zh) | 0,09s (0,002×) | 48 MB | 1,76 dB | +0,34 dB | **100%** |
     | demucs (en) | 21,93s (0,366×) | 1298 MB | 25,92 dB | −10,58 dB | **3,4%** |
     | nhẹ (en) | 0,07s (0,001×) | 46 MB | 8,00 dB | −4,59 dB | **86,3%** |

     **THƯỚC "RÒ RỈ TỪ" LÀ THƯỚC DUY NHẤT THẲNG THẮN: CHÉP LẠI CHÍNH LỚP
     "NHẠC" BẰNG GROQ RỒI ĐẾM TỪ.** RMS đẹp vẫn lừa được; whisper thì không.
     Nó **LOẠI HẲN cách nhẹ**: lớp "nhạc" của cách nhẹ chép ra **256/256 từ
     tiếng Trung Y HỆT bản gốc**. Gốc: video thật gần như **DUAL-MONO**
     (tương quan L/R 0,963) nên `(L−R)` vứt ~98% năng lượng gồm cả nhạc -> phải
     cộng lại dải trầm/cao để cứu nhạc -> **cộng lại thì giọng về theo**. Hai
     mục tiêu LOẠI TRỪ NHAU, không tham số nào cứu được.
     **HỆ QUẢ PHẢI NÓI THẲNG VỚI ANH HÙNG: máy nhân viên KHÔNG có torch thì
     đường lui `nhe` ra chất lượng KHÔNG BÁN ĐƯỢC** (giọng gốc còn nghe rõ
     chồng lên giọng mới). Đường lui chỉ để KHÔNG VỠ APP, không phải lựa chọn
     chất lượng. Demucs cài RIÊNG ở `_lib/` (env `BQ_DEMUCS_LIB`), **cố ý
     KHÔNG cài vào `.venv`** — một lượt `pip install demucs` kéo theo
     torch/torchaudio có thể phá app đang chạy sản xuất 300 kênh.
     **BƯỚC 5 (KHỚP THỜI GIAN) LÀ CHỖ VỠ THỨ HAI.** Dịch Trung -> Anh đọc lên
     DÀI HƠN HẲN câu gốc: lượt đầu **15/21 câu phải ép quá 1,30** và `atempo`
     **CHẠM TRẦN 1,50**. **CHỮA Ở CHỮ TRƯỚC, ĐỪNG ĐỤNG TỐC ĐỘ** — bước 4b
     `rut_gon_vua_khung` nhờ LLM viết NGẮN lại, đọc lại, và **chỉ NHẬN bản mới
     khi nó đọc NGẮN HƠN thật** (LLM đôi khi trả câu dài hơn). Đo: tempo cần
     max **2,61 -> 1,83** (lượt khác 2,32 -> 1,41), số câu vượt **15 -> 8**
     (lượt khác 18 -> 4), tempo trung bình khi khớp **1,349 -> 1,206**.
     Thứ tự ưu tiên trong `khop_thoi_gian` (đừng đổi): lọt khung sẵn -> KHÔNG
     đụng tốc độ · tràn -> **MƯỢN khoảng lặng đoạn kế** · mượn hết mới ép.
     **THƯỚC ĐO PHẢI TÁCH 2 THỨ:** "lệch mốc cuối" **GỒM CẢ phần mượn khoảng
     lặng hợp lệ** nên nó to (4.632 ms) mà KHÔNG có nghĩa là sai. Con số thật
     sự nói lên "timeline sai" là **CHỒNG LẤN** = phần liếm sang câu kế:
     **266,1 ms / 4 trong 23 câu**. Đọc nhầm hai cột này là kết luận sai.
     **AN TOÀN VIDEO GỐC (việc nặng nhất của cổng):** anh Hùng nói "làm xong tự
     xoá video gốc" — **TUYỆT ĐỐI KHÔNG xoá hẳn**. Thứ tự BẮT BUỘC:
     `kiem_video_ra` (tồn tại + **có KHUNG HÌNH** + có tiếng + đúng độ dài)
     XONG -> mới `delete_or_recycle` đưa gốc vào thùng rác -> rồi mới đặt file
     mới vào chỗ. Gốc KẸT (Windows còn giữ handle) -> **GIỮ NGUYÊN tất cả**,
     để lượt sau; cấm ghi đè lên gốc lúc đó. Cổng chứng minh bằng **MD5**: gốc
     trong thùng rác trùng TỪNG BYTE với gốc ban đầu.
     **BẪY ĐÃ SẬP THẬT KHI LÀM VIỆC NÀY — `astats` TÊN CHỈ SỐ KHÔNG TỒN TẠI:**
     `do_meo` dùng `Number_of_clipped_samples`, tên này **KHÔNG CÓ trong ffmpeg
     N-121186** -> **cả lệnh ffmpeg CHẾT** ("Unable to parse measure_overall")
     -> hàm trả `{dinh: None, cham_tran: None}` **IM LẶNG** -> mọi phép kiểm
     "có méo không" đọc None rồi cho qua = **TỰ PASS OAN VĨNH VIỄN**. Tên đúng
     là **`Abs_Peak_count`** (in ra dòng `Abs Peak count:`). Nay ffmpeg lỗi thì
     **NÉM**, không trả None âm thầm. Đây là anh em của bẫy `startswith` đã ghi
     ở cổng 44: **phép đo hỏng nguy hiểm hơn không đo**, vì nó phát chứng nhận.
     **LỖI THẬT cổng lôi ra:** `cau_tu_transcript` gộp từ RỒI MỚI kiểm độ dài
     -> câu luôn vượt trần đúng MỘT TỪ (đặt 12s ra **14,5s**). Nay cắt TRƯỚC
     khi vượt: **14,5s -> 9,5s**, không nuốt chữ (6/6 từ).
     **3 LỖI CỦA CHÍNH CỔNG (không phải lỗi app) đã sửa:** sandbox của cổng
     **nằm trong %TEMP%** nên lấy nó làm ví dụ "thư mục thường" thì
     `_is_safe_recycle_root` từ chối là ĐÚNG (đổi sang chuỗi `D:\KhoVideo\…`,
     hàm thuần không cần file có thật); phép đo "không bỏ vào %TEMP%" vô nghĩa
     vì sandbox đã ở đó -> đổi thành bất biến THẬT "không được DÙNG thùng rác
     %TEMP% user lỡ đặt"; và **quét tĩnh bằng `in` cả file** làm chính
     DOCSTRING của `do_meo` (cố ý nhắc tên sai để cảnh báo người sau) bị kể là
     vi phạm -> **ĐỎ OAN VĨNH VIỄN**, phải `tokenize` bỏ COMMENT+STRING đúng
     như bài học cổng 47/51.
     **ĐA LUỒNG**: `thay_giong_thu_muc` mặc định **2 luồng** (env
     `BQ_TG_LUONG`) vì Demucs ăn ~1,3 GB RAM/video — đo 2 video/2 luồng
     **74,97s** so với ~120s chạy lần lượt.
     **CHƯA ĐẠT, GHI THẲNG:** chưa có nút/màn hình trong UI (mới là hàm làm
     nền) · chưa nối vào bộ điều phối job. **KHÔNG hứa "dịch chuẩn 100%"**:
     bước 3 chỉ đo được tỉ lệ câu phải dịch lại và điểm giống nghĩa — đó là số
     thật, không phải lời hứa.
     **ĐO BIẾN ĐỘNG 3 LƯỢT cùng video cùng mã** (LLM không tiền định — chạy 1
     lượt rồi báo số là SAI): tỉ lệ dịch lại **0% · 21,7% · 39,1%** · điểm
     giống nghĩa TB **9,35 · 8,96 · 8,70** (không lượt nào còn câu dưới ngưỡng
     7) · **CHỒNG LẤN 0 ms ở 2/3 lượt và 266 ms / 4 câu ở 1/3 lượt** — lỗi
     timeline là NGẪU NHIÊN theo lượt dịch, không phải luôn luôn. Đáng lo nhất:
     `tempo_max` lượt nào cũng **SÁT TRẦN 1,5** (1,467 · 1,485 · 1,500), tức
     trần atempo bị chạm THƯỜNG XUYÊN — rút gọn giúp nhưng CHƯA đủ.
     **BẢN `.exe` v2.24.0 KHÔNG CHẠY ĐƯỢC TÍNH NĂNG NÀY — PHẢI ĐỌC:**
     `BQHungVideo.spec` **không khai** torch/demucs/`_lib`, và
     `requirements-build.txt` ghi thẳng *"KHÔNG gói torch/whisper/mediapipe/
     opencv (nặng GB)"*. Demucs nằm ở `_lib/` (gitignore) nên **chỉ máy dev này
     có**; trên máy nhân viên `co_demucs()` = False.
     Vì thế `tach_giong(cach="auto")` **KHÔNG TỰ LUI sang `nhe` nữa mà NÉM
     `THIEU_DEMUCS`** — tự lui là âm thầm xuất video hỏng HÀNG LOẠT (giọng cũ
     còn nguyên chồng lên giọng mới) mà không một dòng báo, đúng loại bẫy cả
     repo này đang chống. Muốn lui phải NÓI RA: `cho_phep_nhe=True` hoặc
     `cach="nhe"`; bản lui luôn mang khoá `lui_vi`/`canh_bao` để nhật ký không
     khoe cái mình không làm được. Cổng 53 CA 9 vá `co_demucs` thành False để
     giả lập máy nhân viên và bắt đúng hành vi này.
     **MUỐN BÁN RA THẬT phải chọn 1 trong 3**: gói torch+demucs vào `.exe`
     (nặng thêm ~2 GB) · để app TỰ TẢI Demucs lần đầu · hoặc tách giọng trên
     MỘT máy có cài rồi chia file. Chưa chọn thì tính năng này mới chạy được
     trên máy dev.
  52. `_test_cjk_va.py` → **3 LỖ HỔNG TIẾNG TRUNG ĐÃ VÁ** (14/08/2026). Lượt
     kiểm tiếng Trung end-to-end tìm ra 3 chỗ app **im lặng bỏ rơi tiếng
     Trung** — cả 3 đều "app vẫn chạy, cổng vẫn xanh, chỉ SỐ ĐO tố giác".
     (a) **`lop_phu.py` — bảng từ khoá cảnh chỉ có Nhật/Hàn.** 1.122 từ khoá
     khớp đúng **1** từ trên 1.132 ký tự lời Trung thật (`宝物`, trùng may).
     Nặng hơn: **BẪY CHÉO NGÔN NGỮ** — chữ Hán Nhật và Trung dùng chung MẶT
     CHỮ nhưng khác nghĩa (cùng họ bẫy `tuyết`/`tuyệt vời`, khác cơ chế):
     `料理` Nhật = nấu ăn nhưng **Trung = XỬ LÝ**, mà nó nằm trong danh sách
     CẤM của 5 cảnh -> câu tiếng Trung nói "xử lý chuyện này" bị **cấm oan 5
     cảnh**; `手紙` Nhật = lá thư, **Trung = giấy vệ sinh** -> khớp `bui_phim`.
     CHỮA: bảng `_ZH` **RIÊNG** (không gộp chung rổ `_CJK`), và bảng tiếng
     Trung **KHÔNG thừa hưởng một từ khoá Nhật/Hàn nào** (`_CO_CJK` lọc sạch)
     — đó đúng là chỗ 2 cái bẫy chui vào. Nhãn ngôn ngữ đi THEO MỐC
     (`digest_tu_loi` -> `loc_digest_theo_doan`), cùng đường của cờ `loi=True`.
     `chuan_ngon_ngu` phải nhận **CẢ `zh` LẪN `Chinese`**: Groq trả nhãn CHỮ
     trên video thật của anh Hùng, thiếu dạng nào là bản vá **không bao giờ
     chạy mà không một dòng báo**. Đo: `料理` cấm oan 5 -> **0** cảnh · từ khoá
     khớp **1/1.122 -> 8/912** · `duoi_nuoc` **0,00 -> 1,00** · đoạn cắt thật
     0-60s **0 -> 1 lớp phủ**. Chỉ thêm **BIẾN THỂ NGÔN NGỮ trong 14 cảnh ĐÃ
     dò được**, KHÔNG thêm cảnh mới (luật anh Hùng đã chốt).
     (b) **`recap.py` — `.split()` trên chữ chép lời.** Câu CJK ra **1 token**
     -> mọi tỉ lệ trùng 0.0 -> **bộ dò chống chép lời TẮT IM LẶNG**. **NỬA THỨ
     HAI của lỗi, sửa `.split()` không thôi là vô ích:** lọc `len(w) > 1` vứt
     SẠCH token CJK (mỗi chữ Hán là 1 token, len == 1) -> tập từ-nội-dung vẫn
     RỖNG. Đo thêm 2 lỗ nữa, cả hai đều thật: guard `len(t) < 15 ký tự` của
     `_is_transcript_copy` đếm KÝ TỰ (15 chữ latin ~ 3 từ, 15 CHỮ HÁN ~ 15 từ)
     nên **85/99 câu Trung ngắn hơn ngưỡng** -> chỉ bắt **14/99**; và
     `transcript_norm` nối câu bằng DẤU CÁCH còn LLM chép nhiều câu thì viết
     LIỀN -> `in` trượt. Số đo: chép nguyên văn **14/99 -> 90/99** · kể lại
     (Groq sinh) **0/14 -> 14/14** · sáng tác (Groq sinh) **0/11 bị gut oan** ·
     ghép 4 câu liền **False -> True**.
     **NGƯỠNG PHẢI HIỆU CHUẨN RIÊNG, ĐỪNG DÙNG LẠI HẰNG SỐ CŨ** — chúng đo cho
     ngôn ngữ CÓ dấu cách (1 token = 1 TỪ), còn CJK 1 token = 1 KÝ TỰ.
     `_do_cjk_calib.py` quét trên corpus Groq THẬT (19 câu phải bắt / 11 câu
     không được bắt): tập từ-nội-dung **0,818 vs 0,643** · n-gram **3 vs 4** ·
     fuzzy **0,840 vs 0,643** -> hai nhóm TÁCH RỜI, ngưỡng lấy GIỮA khoảng
     trống (0,72 · 6 · 0,74).
     **NHẬT/HÀN GIỮ NGUYÊN ĐƯỜNG CŨ** (`_la_chu_han` chỉ bắt chữ Hán THUẦN):
     máy **không còn video tiếng Hàn** nào (4 video tên Hàn trong
     `_do_hook_cache.json` được Groq chép ra TIẾNG ANH vì tiếng thật là tiếng
     Anh), không có corpus thì bật mò một lưới có thể gut sạch narrate.
     **ĐÃ CÂN NHẮC RỒI BỎ:** bỏ ngắn mạch của `_is_relevant` — đo ra cả 11 câu
     sáng tác LẪN 3 câu CỐ Ý lạc đề đều ra True, lưới không phân biệt được gì
     với tập token 1-ký-tự.
     (c) **`hook_to_mo.py` — `_HUA_HEN` 26 từ, 0 chữ Hán** (nhóm DUY NHẤT
     trong 5 nhóm rỗng tiếng Trung). Thêm 9 từ. Đo: câu 1 dấu hiệu **0,100 ->
     0,302**, đúng bằng câu Anh/Việt tương đương (0,302 là ĐÚNG thiết kế: 1
     dấu hiệu mờ nhạt thì không qua cửa 0,34, tiếng nào cũng vậy).
     **BẤT BIẾN ĐO ĐƯỢC (mốc `841c773`, nạp bằng `git show`):** 480 phép so
     lớp phủ + **2.274** phép so recap (mọi QUYẾT ĐỊNH + `validate_parts`
     đầu-cuối) + 332 câu `cham_cau`, trên **16 video THẬT 4 nhóm tiếng** ->
     **lệch 0**. Tập token nội bộ chỉ đổi ở tiếng NHẬT (342 chỗ) và **không
     lật một quyết định nào** — phải tách 2 mức này ra, gộp là ĐỎ OAN.
     **THỬ PHÁ 5 phép, cổng FAIL cả 5**: tắt `chuan_ngon_ngu` (FAIL 3) · trả
     lọc token về `len>1` (FAIL 1) · trả `.split()` vào `_content_seq`
     (FAIL 3) · bỏ từ khoá Trung khỏi `_HUA_HEN` (FAIL 4) · nhét lại `料理`
     vào bảng zh (FAIL 1). Chạy `BQ_MOC_CJK=HEAD` -> FAIL 6 (chốt "so nó với
     chính nó").
     **LỖ CÒN LẠI, GHI THẲNG:** (1) câu Nhật/Hàn ngắn hơn 15 ký tự chép nguyên
     văn VẪN LỌT (ca 9e) — chờ corpus lời dẫn Nhật/Hàn; (2) **`dubbing.py`
     dòng 1977 · 2199 · 2312 có ĐÚNG cùng bệnh `.split()`** và đều là chỗ ĐẾM
     TỪ THẬT (chia cụm phụ đề theo số từ · align chữ kịch bản với mốc STT) —
     **ĐÃ VÁ, xem cổng 54.**
  54. `_test_dubbing_cjk.py` → **3 CHỖ `.split()` CỦA `dubbing.py`** (14/08/
     2026) — đúng 3 chỗ cổng 52 bàn giao lại. Cả 3 đều ĐẾM TỪ THẬT nên câu
     Trung/Nhật (không có dấu cách) ra **1 token**:
     (a) `_phrase_groups_by_speech` + (b) `_phrase_groups_even` — chia cụm phụ
     đề narrate theo SỐ TỪ -> **21/21 part ra ĐÚNG 1 CỤM**, cụm dài tới **78 ký
     tự** = một dòng chữ đứng im gần hết part (cue dài nhất đo được **12,15s**).
     (c) `_align_stt_words` — **NGUY HIỂM NHẤT vì hỏng KHÔNG MỘT DÒNG BÁO**:
     `m=1` từ kịch bản vs `k`=41-72 mốc STT -> `abs(m-k)/max(m,k)` = **0,957-
     0,986** > `miss_max` 0,40 -> trả None **21/21 part** -> app lặng lẽ lùi về
     silencedetect, tức đường khớp-từng-từ bằng STT **đã tốn lượt Groq chép lời
     rồi** mà không bao giờ dùng được với tiếng Trung.
     Vá bằng `_tach_tu` (dựa `recap._word_tokens`). Phải vá KÈM
     `_phrase_groups_from_words` — nó NỐI CHUỖI chính kết quả của (c), không vá
     thì phụ đề ra `他 们 发 现`.
     **SỐ ĐO (lời Trung THẬT, 1.230 ký tự · 1.074 mốc từng-từ, 21 part):** part
     ra 1 cụm **21/21 -> 0/21** · tổng cụm **21 -> 197** · ký tự/cụm **78 -> 6**
     · align **0/21 -> 21/21** ghép được · cả bài **None -> 1.132 từ** · cue
     qua `m1._recap_caption_cues` **21 -> 197**, ngắn nhất **0,152s** (trên sàn
     0,12s của cổng 21). **BẤT BIẾN: 272 phép gọi / 12 video chữ latin (Anh ·
     Việt · nhóm `han`) -> CHUỖI KẾT QUẢ giống mốc `841c773` 100%**, tổng cụm
     **770 = 770**. Tiếng NHẬT **38 -> 295 cụm** = CỐ Ý (cũng không có dấu
     cách, cũng đang ra 1 cụm/part).
     **BẪY LỚN NHẤT — HANGUL KHÔNG ĐƯỢC ĐI CHUNG:** `recap._CJK_CHARS` GỒM
     hangul, ở recap thì vô hại (chỉ ĐẾM token). Ở `dubbing` thì KHÔNG: chỗ này
     còn **NỐI LẠI ĐỂ HIỂN THỊ** và còn **SO SỐ TỪ với mốc STT**, mà **tiếng
     Hàn CÓ dùng dấu cách**. Đo trên câu Hàn thật: `recap._word_tokens` ra
     **20 token thay vì 5** -> tỉ lệ lệch **0,75 > 0,40** -> `_align_stt_words`
     sẽ trả None = **làm hỏng tiếng Hàn đang chạy tốt**; và
     `captions._noi_cum` (coi hangul là CJK) nối ra `그런데갑자기눈보라가…` =
     **mất sạch dấu cách, KỂ CẢ khi đưa vào đúng `.split()`**. Nên `dubbing`
     có bộ ký tự RIÊNG `_KHONG_DAU_CACH` (Hán · kana · dấu câu CJK · Thái ·
     Lào · Miến · Khmer — **KHÔNG hangul**), tách theo CỤM-TRẮNG trước, và
     `_noi_tu` viết riêng chứ KHÔNG gọi `captions._noi_cum`. Cổng có 2 ca TỰ
     KIỂM (3b/3d) bắt đúng 2 hàm đó phải TRƯỢT — ai sau này "dọn cho gọn" bằng
     cách gọi thẳng chúng sẽ bị chặn với đúng lý do.
     **DÁN KÝ TỰ THẬT VÀO DẢI REGEX = ĐỌC KHÔNG RA SAI LỆCH:** dòng `"豈-﫿"`
     chép từ `recap._CJK_CHARS` (chú thích "CJK compat ideographs" =
     U+F900-U+FAFF) thì `豈` thật ra là **U+8C48** -> dải thật **U+8C48-U+FAFF**
     — **nuốt trọn hangul** (U+AC00-U+D7A3). Bản vá "chừa tiếng Hàn" KHÔNG hề
     chừa, đo vẫn ra 20 token. Nay viết bằng `\u`. Bẫy anh em: dấu câu CJK
     `、`(U+3001) nằm NGOÀI dải U+3040+ nên câu Nhật nối lại ra `瞬間 、 誰も`
     -> phải mở về **U+3000-U+30FF** và **U+FF01-U+FF9F**. Nay 9 hệ chữ nối
     lại **đúng nguyên văn 9/9**. (`recap._CJK_CHARS` vẫn còn dải rộng đó —
     ĐỂ YÊN: ở recap hangul vốn cố ý nằm trong, thu hẹp lại là đổi hành vi
     tiếng Hàn của cổng 52.)
     **KHÔNG DÙNG `chuan_ngon_ngu` — CỐ Ý, và tốt hơn:** bản vá không đọc NHÃN
     ngôn ngữ một lần nào (quét AST chứng minh), nó dò trên CHÍNH CHỮ. Nên bẫy
     "Groq trả `Chinese` chứ không phải `zh`" (corpus THẬT đúng là `Chinese`)
     không với tới được đường này; đổi nhãn qua **5 dạng** kể cả nhãn SAI
     (`Norwegian Nynorsk` — Groq gán nhầm thật cho video Hàn) đều ra Y HỆT.
     **THỬ PHÁ 8 phép, cổng FAIL cả 8** (`_pha_dubbing_cjk.py`): trả `.split()`
     vào từng chỗ trong 3 chỗ (FAIL 2 · 7 · 4) · `_tach_tu` gọi thẳng
     `recap._word_tokens` (FAIL 4) · `_noi_tu` gọi `captions._noi_cum`
     (FAIL 6) · dải regex nuốt hangul (FAIL 6) · bỏ cỡ cụm CJK (FAIL 2) ·
     `BQ_MOC_DUB=HEAD` (FAIL 9). **CỔNG 54: ĐẠT 44 · HỎNG 0.**
     **3 LỖI CỦA CHÍNH CỔNG/SCRIPT THỬ PHÁ, chỉ lộ ra LÚC PHÁ:** (1) file repo
     là **CRLF** nên chuỗi tìm nhiều dòng viết `\n` KHÔNG khớp -> 4/6 phép phá
     im lặng không phá được gì mà bản đầu còn **đếm vào cột LỌT** = báo cáo
     ngược sự thật; nay "không tìm thấy chỗ phá" = **LỖI CỦA PHÉP THỬ**, tách
     hẳn khỏi LỌT. (2) bỏ `_co_cum` mà cổng vẫn 42/0 — chia NHỎ hơn không làm
     cụm ngắn đi theo hướng trần-ký-tự/sàn-thời-lượng canh, nó làm cụm CUỐI
     part DÀI RA; phải đo THẲNG số cụm (197 = chia 6 · chia 4 ra 291). (3)
     `a == b != _uoc(_RECAP := 4)` — so sánh DÂY short-circuit khi vế đầu SAI
     nên `_RECAP` không bao giờ được gán -> **đúng lúc bản vá hỏng thì cổng nổ
     `NameError`** thay vì in ra mục nào hỏng.
     **LỖ CÒN LẠI, GHI THẲNG:** `captions._gom_cjk`/`_noi_cum` (đường phụ đề
     của VIDEO GỐC, không phải narrate) vẫn coi hangul là CJK -> dán liền các
     từ tiếng Hàn. Cổng 54 ca 3d ĐO ĐƯỢC điều đó nhưng **không sửa** (khác
     file, khác đường, ngoài phạm vi việc này).
  55. `_test_thay_giong_ui.py` → **THAY GIỌNG NÓI ĐÃ NỐI VÀO UI + CHẠY ĐA
     LUỒNG** (14/08/2026). Cổng 53 kiểm các HÀM; cổng này kiểm cái anh Hùng
     thật sự bấm: nút "Thay giọng nói" ở trang chính -> hộp
     `app/ui/thay_giong_dialog.py` -> bộ điều phối -> video mới đúng chỗ, gốc
     trong Thùng rác. **ĐẠT 37 · HỎNG 0.** Thành phần THẬT: ffmpeg · Groq
     (41 key) · edge-tts · Demucs · `WorkerPool`.
     **LỖI THẬT LỚN NHẤT VIỆC NÀY LÔI RA — `torch` CHẾT SAU KHI Qt NẠP:**
     trong tiến trình đã có `QApplication`, `import torch` ném
     `OSError [WinError 1114] ... torch\lib\c10.dll`. Tái hiện 100%: torch
     TRƯỚC Qt -> OK · torch SAU Qt -> 1114. **App này LÀ app Qt**, nên bản
     `thay_giong` v2.24.0 (nhúng thẳng Demucs vào tiến trình app) là tính
     năng **KHÔNG BAO GIỜ chạy được khi bấm từ giao diện** — mà lỗi lại đội
     lốt *"máy chưa cài Demucs"*, đúng loại bẫy dẫn người ta đi cài lại 2 GB
     lần nữa. CHỮA: `_tach_demucs` chạy **SCRIPT ĐỘC LẬP ở TIẾN TRÌNH RIÊNG**
     (không `-m <module>`: bản `.exe` không chạy được và không có cây mã
     nguồn) + `co_demucs`/`tinh_trang_demucs` dò bằng **`find_spec`** chứ
     không import. Lợi kèm: RAM ~1,3 GB trả sạch khi tiến trình thoát, và
     bấm Huỷ **giết được** tiến trình (`register_job_proc`). Vẫn `_kiem_wav`
     file tiến trình con ghi ra — không tin nó báo "ok".
     **LÀN THỨ BA CỦA BỘ ĐIỀU PHỐI** (`worker.LAN_TG`, `LOAI_LAN_TG =
     ("thay_giong",)`): mỗi làn vẫn có cửa sổ **50 dòng RIÊNG**, và hai làn
     cũ phải `type NOT IN (...)` — không loại trừ thì job thay giọng lại ngồi
     chung cửa sổ làn CPU và lỗi "làn cắt chết đói vì LIMIT 50" tái diễn y
     hệt, chỉ đổi tên thủ phạm. `_lane_limit_tg` **CỐ Ý không bị `ECO_MODE`
     khoá về 1** (nếu không thì ô "Số luồng" của user chỉ là cái nhãn); trần
     `TG_TRAN = 4` vì Demucs ~1,3 GB RAM/video. Executor RIÊNG `_tg_pool` —
     job này chạy hàng phút, dùng chung với làn CPU là job xuất hết chỗ.
     **MỖI VIDEO MỘT JOB** (không gộp cả thư mục): tắt app giữa chừng thì
     video chưa làm vẫn nằm trong DB và chạy tiếp; Huỷ được từng video; bảng
     tiến độ đọc thẳng bảng `jobs`, không có sổ RAM riêng.
     **SỐ ĐO (19/08/2026, đo lại — số cũ "1,43×" đã LẠC HẬU):** 2 video /
     **1 luồng 24,81 · 25,56s** · **2 luồng 32,32 · 13,53s** = nhanh
     **1,83×** (cổng lấy lượt NHANH NHẤT mỗi bên). Mốc cũ *2 luồng 18,58s ·
     lần lượt 26,55s = 1,43×* đo ngày 14/08. **Ngưỡng vẫn là 1,20, KHÔNG hạ.**
     **CỘT NÀY NHIỄU RẤT MẠNH VÌ GROQ, ĐỌC CHO ĐÚNG:** hai lượt của cùng một
     arm 2 luồng ra **32,32s và 13,53s** — lệch 2,4 lần trên CÙNG bản mã,
     CÙNG máy, cách nhau vài phút. Đo riêng ở cổng này còn bắt được một arm
     1 luồng **144,86s** trong khi CPU của nó chỉ ~21s (`_do_tg_ab.py`), tức
     **123 giây ngồi ĐỢI MẠNG** chứ không chạy. Gốc: 2 luồng = 2 video cùng
     chép lời + dịch qua Groq, bể key nóng (các luồng khác trên máy cũng đốt
     Groq) thì `_call_waiting_quota` đợi — đúng cơ chế đã ghi ở cổng 70
     *"mệnh đề về MÔI TRƯỜNG, không phải về mã"*. Vì vậy **một lượt đo ra
     "2 luồng chậm hơn" KHÔNG kết luận được gì**; phải đan xen nhiều lượt và
     đọc lượt nhanh nhất (thiết kế sẵn của CA 2), hoặc đo lại lúc bể key nguội.
     **"2 LUỒNG CHẬM HƠN DO BỘ GIÓNG CHỮ" LÀ CHẨN ĐOÁN SAI — ĐÃ BÁC BẰNG SỐ
     (19/08/2026).** Bộ gióng hàng **KHÔNG NẰM TRÊN ĐƯỜNG CHẠY** của cổng này:
     giọng mặc định là edge-tts, mà edge-tts tự trả `WordBoundary` nên
     `dubbing._synth_all_words` đi thẳng nhánh edge, **không gọi
     `giong_hang_loat` lần nào**. Hai phép đo độc lập cùng nói vậy: bọc hàm
     đếm lượt gọi ra **0 lượt / 8 arm** (`_do_tg_ab.py`), và sandbox của cổng
     55 sau lượt chạy **không hề có `logs/giong_hang_*.log`** (mà
     `giong_hang_loat` ghi log ở MỌI đường ra, kể cả đường lùi). Đo A/B bật/
     tắt `BQ_GIONG_HANG` trên chính đường thật: **BẬT 1 luồng 28,83s vs
     2 luồng 17,79s (1,62×)** · **TẮT 1 luồng 27,08s vs 2 luồng 16,31s
     (1,66×)** — hai bên như nhau, và **cả hai đều 2 luồng NHANH HƠN**.
     Ai thấy "tắt gióng hàng thì nhanh lên" thì đó là bể key Groq nguội đi
     giữa hai lượt đo, không phải bộ gióng hàng.
     Đỉnh job chạy cùng lúc **2** (làn 2 luồng) và **1** (làn 1
     luồng); MD5 gốc trong Thùng rác **trùng từng byte**; bản mới 215 khung,
     RMS 0,09. Tách 6 giây audio trong tiến trình ĐÃ NẠP Qt: **7,47s wall**,
     tỉ lệ 0,783×, `torch 2.13.0+cpu` (trước bản vá: 0 dòng chạy được).
     **THIẾU DEMUCS = CHẶN, KHÔNG LÙI**: hộp hiện nút `Tải bộ tách giọng
     (khoảng 2 GB)` (nhãn KHÔNG EMOJI), **khoá nút Chạy**, bấm Chạy xếp **0
     job**, handler NÉM. Quét tĩnh bằng `tokenize` (bỏ COMMENT+STRING — bài
     học cổng 47/51): `thay_giong_dialog.py` · `jobs.py` · `services.py`
     KHÔNG được có `cho_phep_nhe`/`"nhe"`, kèm ca **TỰ KIỂM BỘ DÒ** bắt
     `thay_giong.py` PHẢI còn chữ đó. `cai_demucs()` chỉ chạy khi NGƯỜI DÙNG
     BẤM, cài vào `_lib` RIÊNG (không đụng `.venv` đang chạy 300 kênh), và
     kiểm lại bằng **tiến trình riêng** (máy dev có torch trong `.venv` nên
     kiểm tại chỗ là "tưởng cài xong"). **PHÉP KIỂM ĐÓ ĐÃ SAI VÀ ĐÃ BỊ GỠ ở
     v2.27.1 — xem cổng 58:** tiến trình riêng ấy chính là python của `.venv`
     nên nó mượn torch của `.venv` rồi báo "cài xong" trong khi `_lib` rỗng
     torch. Nay hậu kiểm so `spec.origin` với `_lib` (`do_goi_tach_giong`).
     **2 LỖI CỦA CHÍNH CỔNG (sửa, đừng lặp):** (a) thùng rác của cổng nằm
     trong `%TEMP%` -> `_is_safe_recycle_root` từ chối (ĐÚNG) rồi lùi về
     `_DaXoa` -> mục MD5 **HỎNG OAN**; nay thùng rác đặt NGOÀI `%TEMP%`
     (`<repo>/bq_test_tgrac_<pid>`, dọn sạch cuối lượt). (b) phép THỬ PHÁ bản
     đầu gỡ **MỘT** chốt rồi đợi bất biến vỡ — nó KHÔNG vỡ, vì
     `thay_the_video_goc` còn chốt cỡ file. Nay tách 2 mục: gỡ 1 chốt ->
     **vẫn giữ** (2 lớp chắn, là SỐ ĐO) · gỡ **CẢ HAI** -> **VỠ** (chứng minh
     ca 4 đang đo thật).
     **LỖI THẬT CỦA UI cổng lôi ra:** combo giọng chỉ dựng SAU khi thread nền
     tải xong danh sách -> mở hộp rồi Lưu ngay là **ghi đè giọng user đã chọn
     bằng `""`** (đúng họ lỗi "chọn X ra Y"). Nay dựng combo NGAY với giá trị
     đã lưu, thread nền chỉ bổ sung.
     **`tempo_max` SÁT TRẦN 1,5 — ĐÃ CHỮA TẬN GỐC ở v2.27.0, xem khối
     "BỎ ÉP NHANH" bên dưới.**
     **CHƯA ĐẠT, GHI THẲNG:** bản `.exe` vẫn KHÔNG gói torch nên máy
     nhân viên phải bấm nút tải (~2 GB) và **phải có Python 3 trên máy** thì
     app mới tải/chạy được — không có Python thì hộp báo thẳng, không im lặng.
  56. `_test_che_chu.py` → **CHE CHỮ CHÁY SẴN TRONG HÌNH** (`app/core/
     che_chu.py`, 14/08/2026). Nguồn Douyin/reup **đốt phụ đề VÀO KHUNG**, gỡ
     ra không được — thay tiếng sang ngôn ngữ khác thì dòng chữ Trung cũ vẫn
     nằm đó. App **CHE** dải chữ (làm mờ / phủ khối) rồi viết chữ mới đè lên.
     Chuỗi filter GỘP vào lượt mã hoá SẴN CÓ của `export_canvas_clip`, **không
     thêm lệnh ffmpeg thứ hai** (chạy riêng một lượt = 35-76 giây cho video 10
     phút × 200-300 kênh). **KHÔNG "xoá chữ"/inpaint — đã cân nhắc và LOẠI**:
     nội dung sau chữ không có ở đâu để lấy, inpaint từng khung ra vệt nhoè
     NHẤP NHÁY, mô hình video thì GPU + hàng phút/clip.
     **5 BẪY ĐÃ ĐO — phần giá trị nhất của việc này:**
     (a) **CHI PHÍ: "làm mờ" +1,30 s/phút phim · "phủ khối" −0,01 s/phút**
     (`_do_che_chu_gia.py`, 3 vòng ĐAN XEN). Con số **+0,1-0,2** ghi trong bản
     đầu **CHỈ đúng với phủ khối** — đã sửa lại ở cả 2 docstring. Phần đắt là
     chính **`boxblur` tranh CPU với libx264**, KHÔNG phải kiến trúc filter:
     đo riêng phần lọc (`-f null`) ra +0,34 s/phút, trong đó split/overlay chỉ
     **+0,05**. Nên đừng "tối ưu" bằng cách đổi cách nối filter; muốn rẻ thì
     đổi sang phủ khối. Trần của CA 17 vì thế đặt **2,0 s/phút**, không phải
     0,2 — đặt theo lời hứa thay vì theo số đo là cổng đỏ oan mỗi lượt.
     (b) **SỐ ĐO "SẠCH" MÀ MẮT VẪN ĐỌC ĐƯỢC CHỮ** — đúng loại bẫy cả repo đang
     chống (*phép đo phát chứng nhận cho thứ vẫn hỏng*, anh em của `astats`
     cổng 53 và `startswith` cổng 44). Trên clip Douyin THẬT: mức mờ **0,40**
     đưa mật độ nét trong dải về **0,0030** — MỌI thước máy bảo "dải đã sạch"
     — nhưng trích khung ra PNG **vẫn đọc được bóng chữ** `这时医生灵机一动`.
     Chỉ từ **0,60** mắt mới thật sự không đọc nổi. Vì vậy: mặc định **1,0**,
     **SÀN CỨNG 0,60 nằm TRONG MÃ** (`chuan_muc_mo` — cửa DUY NHẤT, mọi đường
     vào phải qua: UI, mẫu cũ đọc từ đĩa, payload job, test; đặt sàn ở thanh
     kéo thôi thì mẫu lưu sẵn 0,30 vẫn lọt). **CẤM hạ dưới 0,6.** Kèm CA 14
     trích PNG ra để NGƯỜI TỰ NHÌN — cổng không tự phong cho mình quyền kết
     luận "nhìn đẹp".
     (c) **`max(2, …)` Ở CẢ HAI VẾ KẸP BÁN KÍNH = MẤT TRẮNG CLIP.** Dải NHỎ
     làm `boxblur` nhận bán kính KHÔNG HỢP LỆ -> **ffmpeg chết cả lượt xuất, 0
     khung**. Đây không phải "che xấu một chút" mà là mất hẳn clip. Kẹp phải
     bằng `min()` THẬT (`min(r, max(1, w//2), max(1, h//2))`) + chroma theo
     yuv420p. Dải thường 716x36 / 1280x44 **KHÔNG đổi một số nào** (CA 21 canh
     cả hai chiều: dải nhỏ không giết lượt xuất, dải thường không bị đổi).
     (d) **CỔNG TÌM BẰNG CHUỖI THÌ LỌT** (bài học thứ ba của họ 47/51/54, lần
     này ở chiều NGƯỢC: 47/51/54 là **đỏ oan**, đây là **PASS oan**). Bản đầu
     của CA 19a tìm chuỗi `che_chu=` -> phép phá đổi thành `che_chu=False`
     **VẪN XANH** = con dấu. Nay đọc bằng **AST** và đòi **giá trị truyền vào
     phải là BIỂU THỨC, không được là hằng số** (`ast.Constant`). Quy tắc
     chung: quét tĩnh mà chỉ hỏi "có mặt không" thì luôn có một phép phá giữ
     nguyên mặt chữ mà đổi ý nghĩa.
     (e) **CỜ PHẢI VÀO HASH CHỐNG TRÙNG** (v2.26.0, CA 23 — lỗi NGƯỜI DÙNG GẶP
     NGAY). Bản v2.25.0 bị CẤM chạm `studio_page.py`/`services.py` (luồng khác
     đang sửa) nên đi ĐƯỜNG LÙI: `m1.doc_che_chu` tra MẪU theo tên
     `cap_style["_mau"]` lúc xuất. Đường đó **không có trong `dedup_key`** ->
     anh Hùng bật ô trong Chỉnh mẫu rồi bấm "Xuất cả kênh" thì clip đã xuất bị
     **SMART-SKIP**, không job nào chạy, phải bấm "Xuất lại" từng clip. Nay
     `studio_page` truyền thẳng 3 tham số vào `services.enqueue_export`.
     **2 QUYẾT ĐỊNH TINH VI, ĐỪNG "DỌN GỌN" MẤT:**
     · `enqueue_export` mặc định **`che_chu=None`, KHÔNG phải `False`**.
       `doc_che_chu` chọn đường bằng `"che_chu" in payload`, nên `False` nghĩa
       là "đã CHỐT: tắt" và sẽ **bịt đường lùi** của job cũ đã nằm trong DB +
       mọi lối gọi chưa nối. `None` = không truyền -> payload không mang khoá.
     · cờ **chỉ góp vào `sig` KHI THẬT SỰ BẬT**, và nối vào **ĐUÔI chuỗi
       `sig`** chứ KHÔNG thêm phần tử vào tuple `extra`. Thêm vào tuple là đổi
       hash của MỌI clip cũ -> **200-300 kênh xuất lại từ đầu** (đúng lý do
       `ovl_spec` cũng cố ý đứng ngoài hash, cổng 42). Cách này giữ `sig`
       **giống TỪNG KÝ TỰ** bản mốc khi cờ TẮT.
     · mức mờ đi qua `chuan_muc_mo` **TRƯỚC khi băm**: 0,30 và 0,50 đều bị sàn
       kéo về 0,60 nên ra clip GIỐNG HỆT — băm giá trị THÔ là đẻ job xuất lại
       cho một thay đổi KHÔNG TỒN TẠI.
     **SỐ ĐO CA 23 (dùng `WorkerPool` + DB THẬT, không mock — smart-skip là một
     câu lệnh SQL trên bảng `jobs`):** TẮT -> `None` (skip đúng) · BẬT -> job
     id MỚI · bấm lần nữa -> **trả ID job CŨ** (không đẻ trùng, không trả
     None) · đổi sang phủ khối -> job id MỚI nữa. BẤT BIẾN: `dedup_key` khi
     TẮT giống **từng ký tự** bản mốc `v2.25.0` (nạp `git show
     v2.25.0:app/services.py` thành module riêng rồi GỌI THẬT), kèm chốt chống
     PASS OAN "mốc TRÙNG file đang test -> FAIL".
     **MỐC ĐỐI CHỨNG CỦA CỔNG 56 LÀ `BQ_MOC_REF=v2.25.0` — ĐỪNG CHÉP NHẦM
     THÀNH `v2.26.0` (đã chép nhầm suốt một phiên, 16/08/2026).** Lý do là số
     học chứ không phải sở thích: **`che_chu` RA ĐỜI Ở v2.26.0** —
     `git show v2.25.0:app/services.py | grep -c che_chu` -> **0** ·
     `git show v2.26.0:app/services.py | grep -c che_chu` -> **15**. Mà CA23-3''
     đòi *"bản mốc KHÔNG hề có tham số `che_chu`"* thì phép so "bật/tắt che chữ
     vẫn ra cùng `dedup_key`" mới có nghĩa; lấy v2.26.0 làm mốc là **so tính
     năng với CHÍNH NÓ** -> CA23-3'' đỏ, và nó đỏ ĐÚNG (cổng đang báo mốc không
     hợp lệ, KHÔNG phải app hỏng). Quy tắc chung: **mốc đúng = bản phát hành
     NGAY TRƯỚC tính năng đang test**. Và **KHÔNG BAO GIỜ dùng `main`** — sau
     khi gộp thì `main` chính là bản đang test, cổng đối chứng tự PASS OAN vĩnh
     viễn (bài học cổng 36/51/52). `_chay_hoi_quy.py` đã đặt sẵn mặc định này,
     chạy cổng 56 bằng tay thì phải tự truyền.
     **THỬ PHÁ 10 phép (`_pha_che_chu.py`), cổng BẮT ĐƯỢC 10/10** — 7 phép của
     đường filter + 3 phép của đường truyền cờ: `studio_page` truyền hằng số
     `che_chu=False` (FAIL 1) · gỡ hẳn 3 tham số khỏi `studio_page` (FAIL 1) ·
     cờ không vào `sig` (FAIL 6).
     **THU DẢI NGANG VỀ HỘP CHỮ (v2.27.0, CA 24 — con số chính anh Hùng hỏi:
     "che ít đi bao nhiêu?").** `do_hop_chu` dò BỀ NGANG chữ THẬT theo từng
     đoạn 8 giây rồi đổi hộp theo mốc thời gian; `hop_theo_doan` quy về
     timeline ĐẦU RA (chịu được hook-first ngược thời gian). Chỉ chạy SAU khi
     `do_dai_chu` đã kết luận CÓ chữ, và **KHÔNG được phép đổi `co_chu`** —
     nhờ vậy kỉ lục CHE OAN 0/76 không bị đụng tới (CA 24e đo lại: 2 video
     sạch -> chuỗi filter RỖNG kể cả khi bật hộp).
     **SỐ ĐO (đường xuất THẬT, 2 đoạn hook-first, clip 60 s):**
     · `zh_ep12` 1,55 -> 1,21 triệu điểm-ảnh·giây = **GIẢM 21,5%** (6 hộp,
       rộng TB 528 px trên dải 716 px)
     · `zh_dongho` 3,38 -> 2,34 = **GIẢM 30,8%** (6 hộp, 763 px trên 1106 px)
     · clip MỘT đoạn: 1,55 -> 1,30 = **GIẢM 16,0%**
     **HỘP CÒN CHE *KÍN HƠN* DẢI, KHÔNG CHỈ NHỎ HƠN — và đây mới là phần đáng
     giá.** Dải mọc theo ngưỡng 0,40 lần đỉnh nên nó DỪNG ở chỗ nét chữ thưa,
     tức **CHÓP và CHÂN chữ nằm NGOÀI dải**: trích khung ra nhìn thấy rõ một
     HÀNG GẠCH ĐỨT ở hai mép ô mờ. Lỗi này **CÓ SẴN trong bản dải (v2.26.0 anh
     Hùng đang chạy)**, hộp chỉ làm nó dễ thấy nên mới bị bắt. `HOP_CAO_THEM`
     nới tối đa 3 hàng (hệ RONG_DO) mỗi phía, chỉ nới khi hàng đó còn >= 10%
     mật độ nét trong dải. Đo nét ở 9 hàng ngay ngoài dải trên FILE XUẤT
     (`zh_dongho`, 3 mốc): gốc 8,48/10,40 -> **DẢI 10,01/13,77 (CÒN NGUYÊN,
     thậm chí đậm hơn vì thêm mép ô mờ) · HỘP 3,56/3,32 (SẠCH)**.
     **CHE HẾT CHỮ, KHÔNG SÓT Ở RÌA:** phép đo phải lấy **CẢ BỀ NGANG DẢI CŨ**
     chứ không phải trong hộp — đo trong hộp là tự hỏi "chỗ tôi che có sạch
     không" (luôn sạch), câu cần hỏi là "chỗ tôi BỎ RA có sót chữ không". Mật
     độ nét trên cả bề ngang dải: **0,32 -> 0,0000** (`zh_ep12`) ·
     **0,35 -> 0,0020** (`zh_dongho`). Kèm ảnh phóng to 2× (`ZOOM_*.png`) để
     người tự nhìn — CHỮ BIẾN MẤT HẲN, và ở `zh_dongho` nhìn rõ vật thể bên
     phải khung **vẫn SẮC NÉT** trong bản hộp trong khi bản dải đã bôi nhoè nó.
     **GIÁ PHẢI TRẢ, GHI THẲNG (CA 17):** hộp dựng **N split + N crop +
     N boxblur + N overlay** (N = số mốc, đo 6 mốc/clip 60 s) nên **đắt hơn
     dải ~4 lần**. Đo đan xen 3 vòng cùng máy cùng clip, ba lượt thô lệch nhau
     < 0,05 s (tức KHÔNG phải máy bận): **TẮT 6,65 s · DẢI +0,84 s/phút ·
     HỘP +3,31 s/phút**. Vì vậy CA 17 tách thành 3 mục, **mỗi kiến trúc một
     trần** (DẢI 2,0 · HỘP 4,5 · hiệu HỘP−DẢI <= 3,5) thay vì nới một trần
     chung lên 4,0 — trần tồn tại để bắt "ai đó lỡ thêm một lượt ffmpeg THỨ
     HAI" (35-76 giây cho video 10 phút = **3,5-7,6 s/phút**), nới trần chung
     lên 4,0 là vừa đúng chỗ mất khả năng bắt cái đó. Muốn rẻ thì chọn cách
     **"phủ khối"**: `drawbox` có `enable` sẵn nên không cần split/overlay
     (đo −0,01 s/phút), và `BQ_CHE_HOP=0` tắt hẳn bước thu-về-hộp.
     **CHE OAN ĐO LẠI SAU KHI CÓ HỘP: `0/76 = 0,0%` — KHÔNG TĂNG MỘT CỬA SỔ
     NÀO** (`_do_che_chu.py do`, 120 cửa sổ / 22 video: 44 thật CÓ chữ · 76
     thật KHÔNG chữ; đúng 116/120 = 96,7%; bỏ sót 4/44 = 9,1%). Đây là RÀNG
     BUỘC CỨNG của tính năng — che nhầm vào hình là hỏng video, tệ hơn che
     thừa. Lý do nó không thể tăng: `do_hop_chu` **chỉ chạy sau khi
     `do_dai_chu` đã kết luận CÓ chữ** và không được phép đổi `co_chu`; quét
     `git diff v2.26.0..HEAD -- app/core/che_chu.py` cho **0 dòng** đụng tới
     phép gán `co_chu`. **ĐO XONG MỚI NÓI, đừng chỉ lập luận** — cổng 56 CA 24e
     kiểm thêm ở mức đường xuất: 2 video sạch -> chuỗi filter RỖNG kể cả khi
     bật hộp. **CỔNG 56 SAU KHI THÊM CA 24: ĐẠT 122 · HỎNG 0.**
     **CHƯA ĐẠT, GHI THẲNG:** chỉ dò **dải ĐÁY** (`che_chu.py` chỉ quét từ một
     mốc trở xuống) — chữ ở đỉnh/giữa khung KHÔNG che · **Mixed-Cut và mẫu
     "clip đơn" KHÔNG che** (chưa đi qua `export_canvas_clip`) · sổ nhớ dò dải
     (`_DAI_NHO`) **chỉ ở RAM**, tắt app là mất, mở lại phải dò lại từ đầu ·
     hộp làm lượt xuất **chậm thêm 3,3 giây mỗi phút phim** (số ở trên) ·
     **bỏ sót vẫn 9,1%** (4/44 cửa sổ có chữ mà không dò ra — chữ Trung còn
     nguyên trên hình ở những chỗ đó) · chưa ai xem bằng mắt trên máy nhân
     viên thật.
  57. `_test_tg_bang_tiendo.py` → **HỘP THAY GIỌNG: BẢNG TIẾN ĐỘ SỐNG · THƯ
     MỤC VÀO/RA · NHỚ VIDEO ĐÃ XONG** (v2.27.0, 14/08/2026). Anh Hùng dùng
     thật v2.26.0 rồi báo 4 lỗi, cổng này canh đúng 4 cái đó. **ĐẠT 57 ·
     HỎNG 0** (cổng 55 sau khi cập nhật: **ĐẠT 47 · HỎNG 0**, chạy 2 lượt đều
     xanh). Có cả ca **soi PIXEL** (ô Trạng thái vẽ ra **256 điểm ảnh chữ**,
     vùng trống **0**) và ca **quét nhãn KHÔNG EMOJI** (21 nhãn) — đếm MÀU
     kiểu cổng 9 không dùng được ở đây vì chạy offscreen chữ không khử răng
     cưa nên ô CÓ CHỮ cũng chỉ ra đúng 2 màu (ngưỡng ">= 3 màu" FAIL OAN).
     (a) *"ấn chạy thì chỉ hiện thanh tiến trình, không hiện gì cả, xong hay
     gì cũng không báo, đang phân tích như nào cũng không thấy"* -> bảng hiện
     **đủ dòng NGAY** khi bấm Chạy (video chưa tới lượt = "Đang chờ"), trạng
     thái chạy theo BƯỚC THẬT, cột tiến trình `% · bước n/8`, xong lượt thì có
     dòng tổng kết + hộp báo. Đo bằng **BẮT TÍN HIỆU** `doi_trang_thai` /
     `xong_ca_luot` (không nhìn bằng mắt): chuỗi thật bắt được là *Đang chờ ->
     Đang rút tiếng -> Đang tách giọng -> Đang chép lời -> Đang dịch -> Đang
     đọc -> Đang rút gọn -> Đang khớp tiếng -> Đang ghép -> Xong*.
     **LỖI THẬT CỔNG NÀY LÔI RA:** lời nhắn bước 5 là *"Đọc bản dịch..."* —
     nó **CHỨA chữ "dịch"** nên bảng tra bước khớp `("dịch", 4)` trước và
     bước ĐỌC hiện thành "Đang dịch"; bảng **KHÔNG BAO GIỜ** hiện "Đang đọc"
     (bắt được 4/5 nhãn bắt buộc, thiếu đúng 1). Quy tắc chung: **bảng tra
     theo CHUỖI CON phải xếp cụm DÀI/RIÊNG trước cụm ngắn dùng chung chữ.**
     Cổng đọc 9 mốc `prog(...)` **thẳng từ mã nguồn `thay_giong_video`**
     (regex trên thân hàm) rồi phát lại — chép tay nhãn vào test là đo bản
     chữ CŨ, mã đổi thì ngoài đời sai mà cổng vẫn xanh.
     (b) *"cho tôi tự chọn thư mục ĐẦU VÀO thư mục ĐẦU RA, KHÔNG CẦN cái
     thùng rác tự xoá đâu"* -> 2 ô thư mục; **video gốc KHÔNG bị đụng một
     byte** (MD5 3/3 trùng sau 3 lượt chạy), bản mới nằm ở thư mục đích với
     TÊN GỐC. `jobs._thay_giong` **ÉP `thay_goc=False`** — ép ở HANDLER chứ
     không chỉ ở UI, vì job cũ nằm sẵn trong DB từ bản trước mang
     `thay_goc=True`, không ép thì mở app lên nó vẫn dọn gốc. Thư mục làm
     việc tạm chuyển sang nằm TRONG thư mục đích (wav vài trăm MB không được
     đổ vào thư mục anh Hùng dặn đừng đụng) và **dọn cả khi LỖI**. Nguồn
     trùng đích -> cảnh báo + **xếp 0 job** (2 cửa chặn: UI và
     `tg_chay.xep_mot`).
     (c)(d) *"phân tích lỗi phải có mục CHẠY LẠI"* + *"ấn chạy chỉ chạy video
     CHƯA xong"* -> sổ `app/core/tg_so.py` ghi **RA ĐĨA**
     (`DATA_DIR/thay_giong_so.json`, ghi kiểu thay-nguyên-file), khoá theo
     **đường dẫn + CỠ + mtime** (y `che_chu._khoa_video`) nên thay file khác
     cùng tên vào là coi như CHƯA LÀM. Đo: chạy lần 2 xếp **1 job** (đúng
     video LỖI) thay vì 3 · video xong hiện "Đã xong — bỏ qua" · chuột phải
     "Làm lại video này" xếp **đúng 1 job đúng video** · sổ đọc lại được bằng
     **TIẾN TRÌNH KHÁC** (đúng cảnh tắt app/tự cập nhật).
     **THỬ PHÁ (mục 7):** gỡ chốt ở UI -> vẫn **0 job** (lớp 2 chặn — 2 lớp
     chắn là SỐ ĐO, không phải lời hứa); gỡ **CẢ HAI** -> **3 job** = mục 4
     vỡ đúng như phải vỡ.
     **BẪY ĐO ĐÃ SẬP KHI CẬP NHẬT CỔNG 55:** đo đa luồng LIỀN MẠCH (arm 2
     luồng trước, arm 1 luồng sau) ra *"2 luồng CHẬM HƠN 0,62 lần"* — cùng
     bản mã, đo **ĐAN XEN B,A,B,A** ra **18,26s vs 25,09s = nhanh 1,37 lần**
     (khớp 1,43 lần của cổng 55 cũ). Lượt đầu nuốt chi phí nạp model + mạng
     Groq. Đúng bài học "Đo A/B phải đan xen" — đã sập 3 lần trên máy này.
     **MỞ LẠI HỘP GIỮA CHỪNG PHẢI NHẬN LẠI VIỆC** (`_nhan_lai_job_dang_chay`):
     đóng hộp/tắt app thì job vẫn nằm trong bảng `jobs` và vẫn chạy, nên hộp
     mới phải tra lại theo `payload.video` — không nhận lại thì bảng hiện
     "Chưa chạy" trong khi máy đang làm, đúng cái anh Hùng kêu. Đo: **3/3 job
     nhận lại**, bảng hiện *Đang tách giọng · Đang tách giọng · Đang chờ*
     (không dòng nào "Chưa chạy").
     **CHƯA ĐẠT, GHI THẲNG:** chưa có nút "Dừng video này" riêng (chỉ có "Dừng
     tất cả" — chuột phải mới có làm lại/bỏ qua) · bảng chỉ đọc thư mục MỘT
     CẤP (`liet_ke_video` không đệ quy) nên chọn thư mục mẹ chứa 300 thư mục
     kênh thì bảng trống · sổ chỉ ghi lúc job KẾT THÚC, tắt app giữa chừng thì
     video đang dở chạy lại từ bước 0 · chưa ai bấm thử trên máy nhân viên
     thật · `app/services.py:enqueue_thay_giong` nay là **MÃ CHẾT** (không một
     nơi nào gọi — đường thật là `tg_chay.xep_mot`).
  58. `_test_lib_du.py` → **`_lib` PHẢI TỰ ĐỨNG ĐƯỢC + PHÉP DÒ PHẢI NÓI THẬT**
     (v2.27.1, 14/08/2026). Anh Hùng: *"trước tôi nhớ báo cài rồi mà nay nó ghi
     chưa có bộ tách giọng"*. **ĐẠT 21 · HỎNG 0.**
     **GỐC:** `co_demucs`/`tinh_trang_demucs` chèn `_lib` vào `sys.path` rồi hỏi
     `find_spec` *"import được không"*. Máy dev có `.venv` -> **ăn torch của
     `.venv`** -> trả True, `thieu=[]` -> app báo "đã cài". Bản `.exe` không có
     `.venv` để mượn -> cùng `_lib` đó báo "chưa có". **Máy dev XANH, máy thật
     ĐỎ.** Đo trên chính `_lib` anh Hùng: `demucs` -> `_lib\demucs`, còn `torch`
     và **`soundfile`** (thiếu 2 gói chứ không phải 1) -> `.venv\...`.
     **BẰNG CHỨNG NGUYÊN NHÂN LÀ "pip BỎ QUA GÓI ĐÃ CÓ", KHÔNG PHẢI "tải dở":**
     mọi gói CÓ trong `_lib` (antlr4 · demucs · einops · julius · lameenc ·
     omegaconf) đều **KHÔNG có trong `.venv`**; mọi gói THIẾU (torch ·
     soundfile · numpy · tqdm...) đều **`.venv` ĐÃ CÓ**. Một phép chia đôi hoàn
     hảo, và cả thư mục cùng dấu thời gian 00:55 (không phải tải đứt quãng).
     Thêm: `_lib` sinh lúc **00:55** trong khi `cai_demucs()` mới ra đời ở commit
     **11:46** cùng ngày -> `_lib` KHÔNG do nút trong app tạo ra.
     **VIỆC 1 — `--ignore-installed`.** Cờ này ép mọi gói nằm THẬT trong
     `--target`. LƯU Ý ĐO ĐƯỢC: **pip 26.2.1 hiện tại KHÔNG còn bỏ qua nữa**
     (thử `--target` có/không `--upgrade`/`--ignore-installed` đều ra 17 mục y
     hệt) — nhưng `_lib` chứng minh hành vi cũ CÓ THẬT, nên đặt cờ để không bao
     giờ phải phụ thuộc phiên bản pip.
     **DUNG LƯỢNG LÀ SỐ ĐO, KHÔNG PHẢI ƯỚC BỪA** (hỏi metadata chỉ mục +
     `pip install --dry-run --report`, **KHÔNG tải thật**): 33 gói =
     **154,0 MB** tải về (torch 121,9 MB + 32,1 MB còn lại), bung ra đĩa ~700 MB
     (riêng torch **513,6 MB**). Nhãn cũ *"khoảng 2 GB"* **gấp 13 lần** lượng
     tải thật. **BẢN CUDA: ĐO RA KHÔNG CÓ GÌ ĐỂ ĐÁNH ĐỔI** — wheel Windows trên
     PyPI **122,1 MB** vs bản `+cpu` **121,9 MB**, lệch **0,2 MB**, và **cả hai
     đều không kéo theo gói `nvidia-*` nào**. Muốn dùng RTX 3060 phải trỏ hẳn
     sang chỉ mục `cu###` — việc RIÊNG, không tự nhiên có bằng cách bỏ cờ.
     `--extra-index-url` (KHÔNG `--index-url`): chỉ mục cpu không có
     demucs/soundfile nên ép cả lượt vào đó là hỏng phép giải; vẫn ra `+cpu` vì
     `2.13.0+cpu` > `2.13.0` theo PEP 440 (đã kiểm bằng `--report`).
     **VIỆC 2 — dò bằng `PathFinder` trên ĐÚNG `[_lib]`**, so `spec.origin` với
     `_lib` chứ không hỏi "import được không". Dùng `PathFinder` chứ KHÔNG
     `importlib.util.find_spec` vì `find_spec("demucs.pretrained")` **IMPORT gói
     cha** thật (và `find_spec` thì luôn tìm trên `sys.path` nên không trả lời
     được câu "có nằm trong `_lib` không"). **BA KHOÁ, BA CÂU HỎI KHÁC NHAU —
     đọc nhầm là lại tự lừa:** `thieu`/`du_lib` = sự thật của `_lib` = **đúng
     cái bản .exe thấy** · `co` = máy NÀY chạy được không (máy dev mượn `.venv`
     là THẬT, vì bước tách chạy bằng `_python_chay_tach()` = python `.venv`) ·
     `ngoai_lib` = gói đang mượn = *"máy này chạy được, máy anh Hùng thì không"*.
     `co_demucs()` KHÔNG còn chèn `_lib` vào `sys.path` — chèn vào là làm bẩn
     phép đo của mọi lượt dò sau.
     **VIỆC 3 — hộp hiện NGUỒN TỪNG GÓI** (`_lib` / hệ thống / KHÔNG CÓ) + đường
     dẫn `_lib`. Thêm trạng thái **CÀI DỞ** (máy này chạy được nhưng .exe sẽ báo
     thiếu), nút đổi nhãn thành `Cài tiếp phần còn thiếu (torch, soundfile)`.
     Nút bám **`thieu`**, KHÔNG bám `co` — bám `co` chính là cách bản cũ giấu
     mất việc `_lib` thiếu torch (máy dev mượn được -> nút biến mất -> không ai
     bấm -> bản .exe mãi mãi thiếu). Hộp "Đã cài xong" mừng theo `du_lib`.
     **MỆNH ĐỀ TRUNG TÂM CỦA CỔNG (CA 1a):** *danh sách gói THIẾU mà máy DEV nói
     ra phải GIỐNG HỆT danh sách mà một tiến trình KHÔNG có `.venv` nói ra.*
     Cách giả lập `.exe`: import `app` xong **RỒI MỚI** cắt mọi mục
     `site-packages` khỏi `sys.path` — bản `.exe` vẫn có đủ dotenv/PyQt6 trong
     `_internal`, khác biệt duy nhất là chỗ tìm torch. Cắt trước thì chính
     `import config` chết và cổng đo nhầm thứ khác.
     **THỬ PHÁ (CA 4) — chạy lại CHÍNH mã bản cũ ở CẢ HAI môi trường:** dev
     `thiếu=[]` vs .exe `thiếu=['torch','soundfile']` -> CA1a FAIL. Cổng không
     phải con dấu.
     **QUÉT TĨNH PHẢI BẰNG AST:** chính phần ghi chú của `cai_demucs` có chuỗi
     `--ignore-installed`, nên tìm bằng chuỗi thì gỡ cờ khỏi lệnh mà cổng VẪN
     XANH (đúng bài học cổng 56d).
     **ĐÃ GỠ `kiem_lib_bang_tien_trinh_rieng` + `_MA_KIEM_LIB`**: sau bản vá
     chúng thành mã chết, mà để lại còn nguy hơn — tiến trình riêng ấy CHÍNH LÀ
     python `.venv` nên nó mượn torch rồi báo "cài xong". Hậu kiểm sau khi cài
     nay so `spec.origin` với `_lib`.
     **LỖI THỨ HAI CỔNG NÀY LÔI RA — `_lib` CỦA BẢN `.exe` BỊ CHÍNH LƯỢT TỰ CẬP
     NHẬT XOÁ (CA 5).** `lib_demucs()` lấy `Path(__file__).parents[2]`, trong
     bản đóng gói chỗ đó là **`_internal`** — mà `self_update.py` cập nhật bằng
     `ren _internal -> _internal.old` rồi `rmdir /S /Q _internal.old`. Tức anh
     Hùng bấm tải 155 MB, lượt tự cập nhật kế tiếp **xoá sạch**, và app lại báo
     "chưa có bộ tách giọng" — đúng câu anh ấy kêu, nhưng là một nguyên nhân
     KHÁC. Nay nhánh `frozen` trả `DATA_DIR/_lib` (`config.py` đã tách `DATA_DIR`
     sẵn đúng vì lý do này). **CHỈ đổi nhánh `frozen`**: chạy nguồn vẫn
     `<repo>/_lib` nên `_lib` máy dev không bị bỏ rơi (CA5d canh đúng điều đó).
     Đọc `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số (bài học
     `tg_so.duong_so`).
     **CỔNG 55 CA6b NHẤP NHÁY — ĐO ĐƯỢC 1/4 LƯỢT, KHÔNG PHẢI HỒI QUY.** Lượt
     hồi quy v2.27.1 có một lần `_test_thay_giong_ui.py` ra **47/1**, hỏng đúng
     mục *"gỡ CẢ HAI chốt -> bất biến VỠ"* (`gốc còn: True · rác: 0`); 3 lượt
     khác đều **48/0** (lượt ngay sau đó: `gốc còn: False · rác: 1`). Gốc: mục
     THỬ PHÁ đó cần **cả dây chuyền THẬT chạy XONG** (Demucs + Groq + edge-tts)
     rồi mới tới bước thay file — bất kỳ trục trặc tạm nào (Groq 503, mạng
     edge-tts) làm lượt chạy chết SỚM là gốc không bị đụng, và mục này báo HỎNG
     **vì lý do ngược hẳn với cái nó canh**. Chứng minh không phải hồi quy:
     `git diff v2.27.0..HEAD -- app/core/thay_giong.py` **không đụng một dòng
     nào** của `thay_giong_mot_video` / `thay_the_video_goc` / `kiem_video_ra`
     (toàn bộ thay đổi nằm trong vùng dò + cài, và hàm duy nhất bị GỠ là
     `kiem_lib_bang_tien_trinh_rieng`). Thấy mục này đỏ thì **chạy lại trước
     khi nghi bản vá**; muốn hết nhấp nháy phải tách mục THỬ PHÁ khỏi dây
     chuyền thật (chưa làm).
     **CHƯA ĐẠT, GHI THẲNG:** ~~chưa tải torch thật về `_lib`~~ — cơ chế
     `--target`+`--ignore-installed` khi đó mới chứng minh bằng gói NHỎ
     `soundfile` (cố ý chọn nó vì `.venv` ĐÃ CÓ, đúng ca pip có thể bỏ qua)
     rồi **suy ra** cho torch. **ĐÃ TẢI THẬT 18/08/2026** (xem cổng 71): chạy
     chính `cai_demucs()` -> `ok=True`, 168 giây, `thieu=[]`, `_lib` 85 MB ->
     **4,3 GB** và **tự đứng được một mình** — tức cơ chế đó nay là số ĐO chứ
     không còn là suy ra. (Tải bản CUDA vì máy có RTX 3060; máy không GPU vẫn
     lấy bản CPU 155 MB.) · `BQHungVideo.spec` vẫn KHÔNG gói torch/demucs/
     `_lib` nên máy nhân viên vẫn phải bấm nút + phải có Python 3.
  60. `_test_chu_theo_loi.py` → **CHỮ CHẠY THEO LỜI · DỊCH KHÔNG SÓT CHỮ GỐC ·
     CÂN MỨC GIỌNG-NHẠC** (15/08/2026, 3 lỗi anh Hùng báo cùng ngày trên đường
     THAY GIỌNG). **ĐẠT 42 · HỎNG 0**, hàm THUẦN + ffmpeg (không mạng, không
     Groq) nên không nhấp nháy; cổng cần thành phần thật là 53/55/57.
     Video đối chứng: `Downloads\longtieng\近期热播的7部新片推荐…mp4` (107,25 s,
     Trung -> Việt) **và CHÍNH BẢN ANH HÙNG ĐÃ XUẤT** nằm trong `xuất\`.
     (a) **LỖI "chữ hiện hàng loạt"** — *"nói đến đâu chữ hiện đến đó chứ không
     hiện hàng loạt ra chữ như thế kia"*. `dong_chu_theo_giong` trả ĐÚNG 1
     dòng/câu: đo được **41,6 ký tự/lần · dài nhất 127 · 4 lần đứng im quá 4
     giây** (max 6,16 s). Nay cắt thành CỤM <= `TRAN_KY_TU_CUM` (30), mốc lấy
     từ **WordBoundary của edge-tts** — hạ tầng app ĐÃ CÓ (`dubbing.
     _synth_all_words`, đang dùng cho phụ đề recap) mà đường thay tiếng vứt đi.
     Nối qua đủ 5 chặng: `doc_ban_dich` -> `cat_le_loat` (**phải TRỪ số giây
     vừa cắt ở đầu**, quên là lệch đều 0,16-0,20 s) -> `rut_gon_vua_khung` ->
     `doc_nhanh_vua_khung` -> `khop_thoi_gian` (quy về timeline ĐẦU RA; **có
     cắt đuôi thì dùng `1/tempo` + vứt từ rơi ngoài, KHÔNG cắt thì dùng
     `d_fin/d_nat` ĐO THẬT** — hai đường tỉ lệ khác nhau, gộp là chữ chạy
     nhanh hơn tiếng). SỐ SAU: **62 lần hiện · 25,1 ký tự/lần · dài nhất 37 ·
     0 lần quá 60 ký tự · 0 lần quá 4 giây · 0 lần chớp dưới 0,4 giây.**
     **LỆCH CHỮ-TIẾNG, đối chứng ĐỘC LẬP (Groq chép lại chính file giọng, 369
     mốc từ, khớp 58/62 cụm): TB 39,2 ms · trung vị 34,0 ms · 90% 91 ms · max
     181 ms · 41/58 cụm trong ±50 ms.**
     **KARAOKE `\k` — ĐÃ ĐO CẢ HAI RỒI MỚI LOẠI**, đừng ai làm lại: render
     THẬT qua libass rồi đếm điểm ảnh chữ trên câu 156 ký tự của anh Hùng —
     `\k` để **41.487-42.010 px** nằm trên màn hình suốt 9,6 giây (nguyên khối
     4 dòng, chỉ đổi màu dần) còn cụm nối tiếp chỉ **6.945-8.503 px**
     (**ít hơn 5-6 lần**). Tức `\k` KHÔNG giải được câu anh Hùng kêu, nó chỉ tô
     màu cái khối anh ấy đang chê. Thêm: thẻ bị nuốt -> **42.022 px = khối chữ
     cũ**, hỏng ÂM THẦM.
     (b) **LỖI "âm thanh sau khi tách lỗi hết, chỗ có chỗ không nghe không
     được"** — xem khối "GIỌNG MỚI BỊ NHẠC NỀN DÌM" bên dưới.
     (c) **LỖI "dịch còn có cả tiếng Trung không hiểu"**: `con_chu_goc()` dùng
     lại `recap._has_cjk` + **CỬA NGÔN NGỮ ĐÍCH** (`NN_DUNG_CHU_CJK` =
     zh/ja/ko/th/lo/my/km) — thiếu cửa đó là báo động giả 100% khi user dịch
     SANG tiếng Trung. Câu còn sót -> `_dich_lai_sot` gửi kèm CHÍNH BẢN DỊCH
     HỎNG cho model thấy nó vừa sai gì, tối đa 2 vòng, **chỉ NHẬN bản mới khi
     nó thật sự SẠCH** (nhận bừa là đổi câu sót này lấy câu sót khác rồi tự
     khen đã chữa). Còn sót thì BÁO RA (`sot_chu_goc_truoc/sau`), **KHÔNG tự ý
     xoá câu** (xoá là mất tiếng = đúng lỗi (b)). Đo: **1/39 (2,6%) -> 0/38
     (0,0%)**.
     **CA 7 THỬ PHÁ**: đặt trần ký tự vô hạn (= quay về cách cũ) thì bảng phải
     kêu — ra 2 dòng, dòng dài 66 ký tự > trần. Cổng không phải con dấu.
  64. `_test_piper.py` → **PIPER LÀM LỰA CHỌN THỨ HAI, KHÔNG THAY edge-tts**
     (`app/core/piper_tts.py`, 16/08/2026). **ĐẠT 47 · HỎNG 0.** Thử phá
     `_pha_piper.py`: **BẮT 6 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
     **RANH GIỚI GIẤY PHÉP LÀ MỆNH ĐỀ SỐ 1** — `piper-tts` là **GPL-3.0**
     (kho `OHF-Voice/piper1-gpl`; bản MIT cũ dừng ở 1.2.0, `pip install
     piper-tts` hôm nay là nhận bản GPL). App này là phần mềm ĐÓNG. Gọi Piper
     như **CHƯƠNG TRÌNH RỜI** qua `subprocess`, chỉ trao đổi **dòng lệnh +
     file WAV** thì app KHÔNG phải mở mã — y hệt mô hình đã chạy với `ffmpeg`
     (cũng GPL) nhiều năm. **`import piper` MỘT DÒNG THÔI LÀ MẤT QUYỀN GIỮ
     KÍN MÃ**; đóng vào `.exe` PyInstaller cũng vậy. Nên `piper_tts.py`
     KHÔNG import, KHÔNG chèn `_piper` vào `sys.path`, và dò "đã cài chưa"
     bằng **FILE CÓ TỒN TẠI KHÔNG** chứ không `find_spec` (`find_spec` phải
     NẠP gói cha = chạm mã GPL trong tiến trình app). App **TỰ TẢI** từ kho
     GitHub của tác giả, lưu **NGOÀI thư mục cài** (`DATA_DIR/_piper` ở bản
     đóng gói — để cạnh `.exe` là lượt tự cập nhật `rmdir /S /Q _internal.old`
     **xoá sạch**, đúng lỗi `_lib` của Demucs ở cổng 58 CA5).
     **VÌ SAO CHỈ LÀ LỰA CHỌN THÊM, ĐỪNG AI ĐỔI HẲN:** nhấn nhá đo được
     edge-tts NamMinh **3,96** · HoaiMy **3,40** · Piper vais1000 **3,24** —
     đổi sang Piper là **đi lùi ở đúng cái anh Hùng đang chê**, và Piper chỉ
     có **1 giọng Việt** (edge-tts có 2). Cái nó hơn: chạy HẲN TRÊN MÁY và có
     mốc từng chữ không tốn lượt mạng.
     **CỬA DUY NHẤT**: chỗ rẽ nằm NGAY TRONG `dubbing._synth_all` và
     `_synth_all_words`, KHÔNG bắt từng nơi gọi tự kiểm — nhờ vậy phủ cả **3
     chỗ gọi của `thay_giong.py`** LẪN 3 chỗ của `dubbing.py`. Sót một chỗ là
     video **LẪN HAI GIỌNG** mà `rc` vẫn 0 (đúng mệnh đề cổng 63). CA 4 gọi
     THẬT cả 3 hàm rồi ĐẾM, không quét chuỗi.
     **THIẾU PIPER THÌ LÙI ÊM** về edge-tts + ghi `logs/piper_<ngày>.log`.
     Khác ca Demucs (cổng 55 "thiếu là CHẶN"): ở đó lùi ra video HỎNG, ở đây
     lùi ra video ĐÚNG chỉ khác giọng.
     **CHỈ `vais1000`** (trọng số MIT + dữ liệu CC BY 4.0 -> bán được, ghi
     công ở `LICENSES.txt` mục 4). `vivos` CC BY-NC-SA = **cấm thương mại** +
     thiếu dấu thanh; `25hours_single` giấy phép **"Unknown"** — im lặng
     KHÔNG phải là cho phép. CA 2 quét đúng hai tên đó trong MÃ THẬT.
     **MỐC TỪNG CHỮ — 3 BẪY ĐÃ ĐO, cả 3 đều "chạy được, không một dòng báo":**
     (a) **`--output-dir-naming timestamp` LÀM MẤT FILE.** `piper/__main__.py`
     đặt tên bằng `time.monotonic_ns()`, mà `time.monotonic` trên Windows nhảy
     **15,625 ms** -> hai chữ NGẮN liền nhau ghi đè nhau. Đo 48 từ ra **44 ·
     46 · 46** WAV — **NHẤP NHÁY**. Nguy hiểm thật không phải thiếu file mà là
     `zip(wav, tu)` **gán mốc cho SAI CHỮ** từ chỗ mất trở đi.
     (b) **TÊN FILE KHÔNG PHẢI CHỮ MÌNH GỬI**: `con` -> **`con_.wav`** (CON là
     tên THIẾT BỊ Windows) · `giờ.` -> **`giờ.wav`** (Windows nuốt dấu chấm
     cuối). Đoán một dạng tên là tra hụt -> mốc lệch. Nay làm sạch dấu câu
     TRƯỚC khi gửi + bộ khớp nhiều dạng + **ĐỐI SOÁT HAI CHIỀU** (mọi chữ tra
     ra file, mọi file có chủ); lệch một cái là **BỎ MỐC CẢ NHÓM** — mốc gán
     nhầm chữ tệ hơn hẳn không có mốc.
     (c) **chữ đọc RỜI ngắn hơn chữ đọc TRONG CÂU**: **9,427 s vs 9,764 s
     (−3,4%)** -> bắt buộc `_co_gian` về đúng độ dài WAV thật.
     Hệ quả phải nói thẳng: mốc Piper là **SUY RA**, không phải mốc máy đọc
     trả về như `WordBoundary` của edge-tts. Đúng thứ tự, đúng tổng; ranh giới
     từng chữ là ước lượng theo tỉ lệ.
     **`length_scale` BÃO HOÀ — SỐ CŨ LÀ SỐ RÁC.** Bảng trong
     `_do_piper/work/ket_qua.json` ra **TOÀN 0,000 giây**: lượt đo đó KHÔNG HỀ
     CHẠY ĐƯỢC (vòng lặp không kiểm `rc`) nhưng vẫn ghi ra file kết quả trông
     như thật — đúng họ "phép đo hỏng phát chứng nhận" (`astats` cổng 53 ·
     `startswith` cổng 44). Đo lại có kiểm `rc` (`_do_piper_moc2.py`):

     | length_scale | 1.0 | 0.8 | 0.74 | 0.5 | 0.45 | 0.3 | 0.2 |
     |---|---|---|---|---|---|---|---|
     | so tự nhiên | .981 | .937 | .860 | .751 | .744 | .697 | **.692** |

     **HAI ĐIỀU PHẢI NHỚ:** bão hoà ở **~0,69×** (ép dưới 0,5 gần như không
     ngắn thêm), và **`length_scale` KHÔNG TỈ LỆ THUẬN** — đặt **0,45 ra
     0,744×**, ai tính `ls = khung / độ_dài` sẽ ép hụt rất xa rồi tưởng Piper
     hỏng. `_ls_tu_rate` vì thế **tra BẢNG ĐO**, không dùng công thức. So cho
     công bằng: edge-tts `rate=+50%` ra **0,687×** — **hai bên xấp xỉ nhau**,
     nên kiến trúc 4 bước hiện tại dùng được nguyên xi với Piper.
     **CHI PHÍ:** gọi tiến trình rời thì **lượt nào cũng nạp lại model
     (~2,2 s)**. Con số "25,8× nhanh hơn thời gian thật" trong tài liệu là tốc
     độ SAU khi model đã nạp, đo TRONG tiến trình. Đo cả lượt: câu 9,7 s tiếng
     ra trong **2,70 s wall = 3,62×**. Lấy mốc tốn thêm **1,12×**. Vì vậy
     `doc_loat` **GOM CẢ LOẠT VÀO MỘT LƯỢT GỌI**, đừng gọi từng câu.
     **2 LỖI CỦA CHÍNH CỔNG, do THỬ PHÁ lôi ra:** (1) CA7c dùng
     `"_piper_hay_khong" in inspect.getsource(...)` -> **khớp trúng chính
     DOCSTRING** ("xem `_piper_hay_khong`") nên gỡ SẠCH nhánh rẽ khỏi
     `_synth_all` mà cổng vẫn XANH = con dấu (bẫy cổng 56d, chiều **PASS
     OAN**); nay đọc bằng **AST**, đòi hàm THẬT SỰ GỌI. (2) CA5f vá đè lên
     chính `_tra_file` nên phép phá "đoán bừa" không chạm tới được; nay thêm
     5g/5h kiểm chính hàm đó ở mức đơn vị.
  65. `_test_do_to_nghe_thu.py` → **ĐỘ TO BẢN TRỘN + NÚT NGHE THỬ**
     (16/08/2026). Anh Hùng: *"tool cắt sao phần giọng nói ít tiếng quá nghe
     không hay, với không có phần nghe thử à, thêm tiếng cho tôi đi"*.
     **ĐẠT 47 · HỎNG 0.** Thử phá `_pha_do_to.py`: **BẮT 8 · LỌT 0 · KHÔNG
     PHÁ ĐƯỢC 0**.
     **GỐC RỄ: đường thay tiếng CHƯA TỪNG chuẩn hoá độ to** —
     `grep -c loudnorm app/core/thay_giong.py` = **0**. Chỉ có `alimiter` chặn
     ĐỈNH, mà chặn đỉnh KHÔNG nói gì về ĐỘ TO nghe được. Hai thước độc lập
     (`loudnorm` pha đo + `ebur128`, lệch > 0,5 LU thì DỪNG):

     | | I (LUFS) | TP (dBTP) | LRA |
     |---|---|---|---|
     | GỐC Douyin anh Hùng gửi | **−5,07** | +6,16 | 3,30 |
     | bản anh Hùng xuất 16/08 | **−16,00** | −2,26 | 2,10 |
     | trộn cách CŨ (giọng 0 / nhạc −2) | −12,76 | −0,57 | 2,60 |
     | trộn cách MỚI (bản chữa 15/08) | −14,26 | −1,40 | 2,10 |
     | **ĐÍCH** | **−14,00** | **−1,00** | |

     **CÓ HỒI QUY, NHƯNG NÓ KHÔNG PHẢI THỦ PHẠM CHÍNH — nói cả hai vế:** lượt
     chữa "giọng chìm dưới nhạc" làm bản trộn **−12,76 -> −14,26 = nhỏ đi 1,50
     LU**; nhưng gỡ nguyên phần đó ra vẫn còn thiếu ~3 LU nữa so với đích, và
     bản anh Hùng nghe thật đo **−16,00**, tức **thấp hơn GỐC 10,9 LU**. Bệnh
     CÓ TRƯỚC lượt chữa; lượt chữa chỉ cộng thêm.
     Vì sao đó đúng là *"ít tiếng"*: **YouTube/TikTok chỉ chuẩn hoá XUỐNG,
     KHÔNG nâng lên** (YouTube Stats-for-Nerds: `content loudness` âm = KHÔNG
     áp gain). Clip −16 phát ra nhỏ hơn hẳn mọi clip khác trong cùng luồng,
     vì chúng đều bị kéo về ~−14. −14 LUFS cho **mobile** có cơ sở: AES 10268
     (Grimm) đo trên 4,2 triệu album, 80%/38 người nghe chọn mức căn −14.
     **CÁCH ÁP: NÂNG THUẦN + HẠN ĐỈNH — *KHÔNG* dùng `loudnorm` để áp.** Đo cả
     3 cách trên cùng file (vào I −16,00 · LRA 2,10):

     | cách | I | TP | LRA | độ lệch chuẩn hệ số |
     |---|---|---|---|---|
     | `loudnorm` MỘT lượt (động) | −13,81 | −1,00 | 2,00 | **0,277 dB** |
     | `loudnorm` HAI lượt `linear=true` | −14,11 | −0,99 | **1,90** | — |
     | **nâng thuần + hạn đỉnh** | **−14,01** | −1,44 | **2,10** | **0,017 dB** |

     **`linear=true` KHÔNG Ở LẠI TUYẾN TÍNH.** `init()` của `af_loudnorm.c`
     chỉ vào LINEAR_MODE khi **cả ba** điều đúng: đủ 4 `measured_*` (khác giá
     trị mặc định — lưu ý `measured_LRA=0` là số ĐO HỢP LỆ với nguồn đều mà
     vẫn bị coi là "chưa đo") · `measured_LRA <= LRA` đích · **`measured_TP +
     (I − measured_I) <= TP` đích**. Ở đây cần nâng +2,00 dB mà chỗ trống tới
     trần đỉnh chỉ **1,26 dB** -> điều 3 sai -> ffmpeg in *"Normalization
     Type: Dynamic"* rồi làm ĐỘNG: LRA **2,10 -> 1,90** = **NÉN DẬP**, đúng
     cái phải tránh. **rc vẫn 0, không một dòng cảnh báo.** Ai dùng `loudnorm`
     hai lượt thì **phải assert `"normalization_type": "linear"` trong JSON
     lượt 2** — không thì đây là họ bẫy "ffmpeg trả mã 0 mà kết quả sai".
     **HỆ SỐ TĨNH GIỮ CÂN BẰNG THEO TOÁN HỌC:** nhân cả bản trộn với cùng một
     số thì hiệu (giọng − nhạc) ở MỌI cửa sổ không đổi. Đo lại để chắc: giọng
     trên nhạc **+5,99 -> +5,99 dB**, cửa sổ chìm **7,9% -> 7,9%**, y hệt từng
     chữ số. LRA đổi **0,00**.
     **TRẦN ĐỈNH PHẢI TRỪ HAI LẦN — chỗ này trước đây không ai tính:**

     | trần `alimiter` | đỉnh thật WAV | sau nén **AAC 192k** |
     |---|---|---|
     | −1,0 | −0,94 (vượt) | **−0,95 (VẪN VƯỢT)** |
     | **−1,5** | **−1,44** | **−1,27** |

     `alimiter` chặn đỉnh MẪU nên đỉnh THẬT vọt **+0,06 dB**, rồi **AAC vọt
     tiếp tới +0,19 dB**. Đó là lý do bản e2e v2.30.0 ra **+0,04 dBTP** dù lớp
     wav của nó mới −0,57. Biên **0,5 dB** -> AAC cuối −1,27 dBTP, còn dư 0,27
     cho lượt re-encode của TikTok (AES TD1004: coder bit rate thấp vọt nhiều
     hơn). Giá: **0,01 LU**.
     **SÀN CHỐNG NÂNG ĐIÊN** `SAN_LUFS_CHUAN_HOA = -45`: bản trộn gần câm đo
     −60..−70 LUFS, nâng về −14 là +46..+56 dB và thứ được nâng là NỀN NHIỄU.
     `_kiem_wav` KHÔNG bắt được ca này vì nó đo RMS, không đo LUFS.
     **NÚT NGHE THỬ** (`thay_giong.doc_thu`): đi **qua `doc_ban_dich`** = đúng
     bước 4 của lượt xuất thật. **KHÔNG gọi thẳng `_synth_all_words`** — bản
     đầu gọi thẳng và **cổng 63 ĐỎ ngay** (*"tìm thấy ĐÚNG 3 chỗ gọi… 4 chỗ"*,
     chốt báo động cố ý). Chữa bằng cách đổi CHỖ GỌI chứ **không sửa con số
     trong cổng**; đi cửa cấp trên còn được thêm: tự tách `pitch`, tự cắt lề
     im (4,1s -> 3,0s, bấm là kêu ngay). 3 nguồn: edge-tts (+ biến thể cao
     độ) · Piper `vais1000` · ElevenLabs qua `synth_demo` (nhưng
     `giong_dung_duoc` LỌC BỎ `el:`/`gemini:` khỏi combo hộp này từ trước, nên
     thực tế hộp Thay giọng chỉ có 2 nguồn — ElevenLabs nằm ở hộp Lồng tiếng).
     **NÓI RA NGUỒN THẬT**, không nói cái user chọn: Piper chưa tải thì lùi êm
     về edge-tts, không nói ra thì tưởng đang nghe Piper. Không chặn giao diện
     (**0 ms**), cache theo (giọng·pitch·câu) **652 ms -> 1 ms**.
     **CỔNG KHÔNG ĐƯỢC PHÁT TIẾNG RA LOA** — vá `winsound.PlaySound` thành hàm
     ĐẾM TRƯỚC khi dựng hộp, kèm mục tự kiểm chính bản vá đó.
     **HAI LỖ CỦA CHÍNH CỔNG, do THỬ PHÁ lôi ra (lượt phá đầu: LỌT 1 + KHÔNG
     PHÁ ĐƯỢC 2):** (a) ca "đo hỏng phải NÉM" chỉ thử **file KHÔNG TỒN TẠI**,
     mà ca đó đi nhánh raise KHÁC (ffmpeg mã != 0) -> thêm CA 2b giả lập
     **ffmpeg mã 0 mà KHÔNG in JSON**; (b) ca LRA MỘT MÌNH là con dấu — nguồn
     anh Hùng đã nén sẵn (LRA 2,10) nên bộ nén động gần như không đổi LRA
     (2,10 -> 2,00, lọt ngưỡng). Chốt THẬT là **hệ số áp phải là HẰNG SỐ**
     (nâng thuần 0,0035 dB · loudnorm động 0,277 dB) — đó mới là bất biến bảo
     vệ tỉ lệ giọng-nhạc, và nó bắt được phép phá ngay.
     **CHƯA LÀM, GHI THẲNG:** đường CẮT THƯỜNG và GHÉP ĐOẠN vẫn **KHÔNG** có
     chuẩn hoá — xem khối "ĐỘ TO ĐƯỜNG CẮT" bên dưới. **ĐÃ LÀM ở v2.31.0, xem
     cổng 66.**
  66. `_test_do_to_xuat.py` → **CHUẨN HOÁ ĐỘ TO CHO MỌI ĐƯỜNG XUẤT CLIP**
     (v2.31.0). Cổng 65 canh đường THAY TIẾNG; cổng này canh **cắt thường ·
     ghép đoạn · recap · Mixed-Cut · clip đơn**. **ĐẠT 50 · HỎNG 0.**
     Nối ở **CỬA DUY NHẤT** `m1._export_clip_impl` (CA 10 đòi chỗ gọi nằm
     NGOÀI mọi `if/for/while` — nằm trong nhánh là có đường xuất không đi qua).
     **SỐ ĐO THẬT, 4 video / 8 bản xuất:** đỉnh vượt 0 dBTP **3/8 -> 0/8** ·
     trải độ to **15,75 -> 7,40 LU** · đường thay tiếng **−16,00 -> −14,01**.
     **CÒN 1 CLIP DỪNG Ở −21,40 — CỐ Ý, ĐỪNG "SỬA":** LRA 7,0 + đỉnh +0,90
     dBTP, ép đủ to phải gọt quá ngân sách 6 dB = **nén dập**. Bậc thang lùi
     lại là ĐÚNG; ai nới ngân sách cho "đẹp bảng" là đổi tiếng lấy con số.
     Ba chốt: clip **gần câm** (< −45 LUFS) BỎ QUA · clip **đã đúng độ to**
     không mã hoá lại byte nào (không thêm đời AAC) · chuẩn hoá **hỏng** thì
     GIỮ NGUYÊN clip. Hình `-c:v copy` giống từng byte, lệch tiếng-hình 0 mẫu.
  67. `_test_eleven_tg.py` → **ADAM (ElevenLabs) TRONG HỘP THAY GIỌNG**
     (v2.32.0, 17/08/2026). Anh Hùng: *"đâu Adam đâu"*. **ĐẠT 35 · HỎNG 0.**
     Nối ở **CỬA CHUNG** `dubbing._synth_all`/`_synth_all_words` (cạnh cửa
     Piper) nên phủ cả 3 chỗ gọi của `thay_giong.py` mà **không sửa chỗ gọi
     nào** — cổng 63 vẫn 24/0.
     **`gemini:` VẪN CHẶN, có lý do bằng số:** Gemini TTS không trả word
     boundary, mà đường thay tiếng dựng chữ THEO mốc từng chữ (cổng 60) ->
     nhận vào là chữ quay lại kiểu đổ cả cụm.
     **ĐIỀU BẤT NGỜ SỐ 1 — ElevenLabs CÓ TRẢ MỐC THẬT** (`/with-timestamps`,
     `_parse_eleven_alignment` đã có sẵn từ đường recap). KHÔNG phải "mốc suy
     ra" như Piper, không tốn lượt Groq nào. Việc này được giao với giả định
     ngược lại — **đọc mã trước khi tin giả định**.
     **ĐIỀU BẤT NGỜ SỐ 2 — THƯỚC GROQ PHỤ THUỘC GIỌNG. Đây là bài học lớn
     nhất, và nó lật lại một giả định ngầm của MỌI phép đo mốc trước đây.**
     Đo bằng đúng thước Piper (Groq chép ngược), 2 bộ câu Anh thật, arm edge
     đan xen: RUNG Adam **47,2 / 34,0 ms** vs edge **46,0 / 35,0 ms** =
     **1,03× và 0,97× — NGANG NHAU** (Piper 59,1 ms = 1,53×). NHƯNG số THÔ
     lại xấu (70,1 vs 54,9) vì lệch HỆ THỐNG **+58,0 / +61,5 ms** (edge
     −35,0 / −33,5) -> **57,7% chữ hiện muộn**. Lệch hệ thống trừ được bằng
     hằng số, nên **suýt trừ 94 ms**. **THƯỚC THỨ BA CHẶN LẠI:** đo mốc chữ
     đầu so với lúc thật sự phát tiếng (`silencedetect`, KHÔNG dùng Groq) ra
     edge **−47,0 ms** vs Adam **−37,9 ms** = **chỉ lệch ~9 ms**. Tức +58 ms
     là của THƯỚC, không của ElevenLabs; trừ 94 ms là tự tay làm sai thêm
     94 ms rồi khoe đã chữa. Mục Piper ở dưới đã ghi *"chưa ai chứng minh độ
     trễ Groq không phụ thuộc giọng"* — **nay chứng minh được là CÓ phụ
     thuộc**. Quy tắc: **lệch HỆ THỐNG đo bằng Groq KHÔNG được coi là thuộc
     tính của máy đọc** cho tới khi có thước thứ ba.
     **LỖI THẬT CỔNG LÔI RA (CA 4):** `_synth_all_eleven` đồng bộ, mà đường
     lùi của nó gọi `asyncio.run(_synth_all(...))`; gọi thẳng từ trong
     `_synth_all_words` (async, đang trong event loop) -> **`RuntimeError:
     asyncio.run() cannot be called from a running event loop`** = NỔ cả lượt
     thay giọng. Nó **CHỈ nổ ở nhánh LÙI**, tức đúng lúc hết credit giữa mẻ
     300 video — vài video đầu êm ru. Chữa bằng `_chay_eleven` =
     `asyncio.to_thread`.
     **KHÔNG TRỘN HAI GIỌNG:** `cho_lui_edge=False` cho 2 lượt ĐỌC LẠI
     (`rut_gon_vua_khung` · `doc_nhanh_vua_khung`) — hết credit thì trả toàn
     `False` = caller GIỮ bản ElevenLabs cũ. Để nó lùi edge là mấy câu đọc lại
     ra giọng khác phần còn lại (đúng mệnh đề cổng 63). Lượt đọc ĐẦU thì vẫn
     cho lùi: chưa có gì trong tay, video đúng mà khác giọng còn hơn câm.
     **KHÔNG ĐỐT HẠN MỨC THẬT:** cổng vá `_eleven_tts` thành hàm sinh mp3 bằng
     ffmpeg -> chạy trong hồi quy tốn **0 ký tự**. Đo thật tiêu **1.924 ký tự**
     (47.833 -> 45.909 / 5 tài khoản free).
     **BẪY VIẾT CỔNG, SẬP 1 LẦN:** `config.settings` là *instance* còn
     `elevenlabs_keys` là `@classmethod` đọc `cls.ELEVENLABS_API_KEYS` — vá key
     giả lên INSTANCE thì classmethod không thấy -> cửa rẽ đi thẳng edge và ca
     *"phải trả False"* tự ĐẠT vì lý do NGƯỢC HẲN. Phải gán lên `type(settings)`
     + có mục chốt *"vá key giả ĂN được"*, và CA 5 phải đòi thêm
     `đã THỬ ElevenLabs` chứ không chỉ đòi kết quả False.
     **CHƯA ĐẠT, GHI THẲNG:** ElevenLabs **không có tham số `rate`** nên bước
     4c `doc_nhanh_vua_khung` (thứ đã đưa `tempo_max` về 1,017-1,027 ở v2.27.0)
     **không chạy được với Adam** -> câu tràn khung quay lại nhờ `atempo`, có
     thể chạm lại trần 1,5. **CHƯA ĐO** con số đó với Adam (một lượt đo là
     ~2.275 ký tự cho ĐÚNG một video) — nói cơ chế, không bịa số.
  68. `_test_kieu_chu_tg.py` → **KIỂU CHỮ CHỈNH ĐƯỢC TRÊN ĐƯỜNG THAY GIỌNG**
     (v2.32.0, 17/08/2026). Anh Hùng: *"phần chữ sub trong video tôi không điều
     chỉnh được cỡ chữ, kiểu chữ, hay in nghiêng đậm, hay chỉnh viền gì được
     ạ"* — kiểm được bằng một lệnh: `grep "Fontsize|FontName|Outline|Bold|
     Italic" app/core/thay_giong.py` ra **0**. **ĐẠT 43 · HỎNG 0.** Thử phá
     `_pha_kieu_chu.py`: **BẮT 14 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
     **CỬA DUY NHẤT `captions.kieu_chu_ass`** — tách RA TỪ CHÍNH thân
     `build_ass` (không viết mới), nay `build_ass` (cắt thường) và
     `che_chu.ghi_ass(kieu=...)` (thay giọng) đều gọi vào đó, nên đặt cùng tham
     số là ra CÙNG một kiểu chữ. Bất biến sống còn của cổng 21 (18 preset CŨ ×
     4 bộ tham số ra .ass giống TỪNG BYTE) vẫn giữ; `kieu=None` ra .ass giống
     từng byte bản mốc `v2.31.0`.
     **UI: 9 ô trong hộp Thay giọng** (27 preset sẵn có · 13 phông · cỡ % cao
     khung · vị trí · đậm · nghiêng · màu chữ · màu viền · độ viền % cỡ chữ).
     Nút màu dùng lại `editor.nut_chon_mau` (tách ra mức module ở `e4f0414`) —
     KHÔNG đẻ bộ điều khiển thứ hai trông khác.
     **BA QUYẾT ĐỊNH ĐỪNG "DỌN GỌN" MẤT:**
     · **ô để MẶC ĐỊNH thì KHÔNG sinh khoá** (`don_kieu_chu` trả dict RỖNG) ->
       `xep_mot` không ghi `kieu_chu` vào payload -> job giống TỪNG KHOÁ bản
       trước, không đẻ job chạy lại cho 200-300 kênh (cùng lý lẽ `ovl_spec`
       cổng 42 và cờ `che_chu` cổng 56e).
     · **ĐẬM/NGHIÊNG là BA trạng thái**, dùng COMBO 3 mục chứ KHÔNG QCheckBox:
       checkbox chỉ có 2 trạng thái nên mọi job đều mọc thêm khoá
       `dam`/`nghieng` (`gon_kieu_chu` coi `None` = không đặt, `False` = lựa
       chọn THẬT).
     · **ô ghi PHẦN TRĂM, đơn thuốc nhận TỈ LỆ** — để lọt phần trăm xuống .ass
       là `Fontsize: 8.5` = chữ 8 điểm ảnh (bẫy cổng 45c).
     **`fontsdir` LÀ BẮT BUỘC** (`che_chu.chuoi_subtitles`): phông đóng gói
     không cài vào hệ điều hành, thiếu `fontsdir` thì libass **lùi im lặng về
     phông mặc định** mà ffmpeg vẫn mã 0 — ô chọn phông chỉ là cái nhãn. Cổng
     có ca đo CẢ HAI chiều (có/không `fontsdir`).
     **NHÌN TẬN MẮT, KHÔNG ĐẾM ĐIỂM ẢNH** (`_do_kieu_chu_nhin2.py`, ffmpeg +
     libass + video Douyin THẬT, 4 arm, trích PNG rồi phóng 2×): mốc = Arial
     39px trắng viền mỏng · Anton 54px VÀNG đậm (mặt chữ HẸP/CAO khác hẳn) ·
     Be Vietnam Pro 29px ĐỎ NGHIÊNG viền TRẮNG dày · Montserrat 43px XANH
     không đậm đặt GIỮA KHUNG. Tiếng Việt đủ dấu đúng ở CẢ 4 arm, **0 ô vuông
     tofu**. Nhắc lại: **đếm điểm ảnh KHÔNG phát hiện được tofu** (tofu 2.431
     px vs chữ thật 517 px = ngược 4,7 lần) — phải MỞ ẢNH RA XEM.
     **2 LỖI CỦA CHÍNH CỔNG đã sửa (không phải lỗi app):** `NGUON` ghi cứng tên
     file `4月新片海外电影片单.mp4` — file đó KHÔNG CÒN trên đĩa nên cổng ĐỎ OAN
     vì KHO chứ không vì mã (đúng bệnh cổng 47 CA2); nay quét thư mục lấy mp4
     đầu theo thứ tự tên. Và mục 7g đòi nhãn mục đầu "không chứa ngoặc" ->
     **HỎNG OAN 3 nhãn ĐÚNG** ("Kiểu mặc định (trắng viền đen)"); bất biến thật
     là *"bỏ phần trong ngoặc ra vẫn còn chữ có nghĩa"*, kèm ca TỰ KIỂM BỘ DÒ
     bắt "(tự chọn)"/"(mặc định)" phải BỊ BẮT.
  70. `_test_groq_model.py` → **GROQ GỠ MODEL THÌ APP PHẢI SỐNG** (18/08/2026).
     **ĐẠT 42 · HỎNG 0.** Số cổng là **70, KHÔNG phải 69** — 69 đã bị
     `_test_viet_tat.py` lấy ở `964e22b` (sớm hơn ~19 giờ). Trùng số thì
     `_kq69.txt` của hai cổng ghi đè nhau.
     **CỔNG NÀY TỪNG KHÔNG NẰM TRONG `_chay_hoi_quy.py`** — tức bản sửa CHẶN
     SẢN XUẤT được canh bởi một file .py không ai gọi, đúng cái bẫy mà chính
     commit trước đó vừa cảnh báo. Đã nối vào.
     **ĐỎ OAN TRONG LƯỢT HỒI QUY VÌ *THỨ TỰ CỔNG*, KHÔNG PHẢI VÌ MÃ
     (18/08/2026, lượt v2.36.0).** Cổng ra **ĐẠT 41 · HỎNG 1**, hỏng đúng mục
     *"404 THẬT KHÔNG khoá key nào (41 key còn nguyên)"* với **2 key** mang
     `limited`. **KHÔNG phải hồi quy của bản vá JSON:** mục 4 (429 giả) và mục
     5 (413 giả) ĐẠT sạch, tức bảng phân loại lỗi còn nguyên; và chạy cổng
     **MỘT MÌNH** ngay sau đó ra **ĐẠT 42 · HỎNG 0**, `phat_key()` = `{}`,
     mã thoát **0**. Cơ chế: **cổng 74 đứng ĐẦU `_chay_hoi_quy.py` và CA 9 của
     nó gọi Groq THẬT** (30 câu), cổng 70 chạy chỉ **~33 giây** sau đó — rơi
     đúng CÙNG CỬA SỔ TPM một phút của Groq, nên vài key trả **429 THẬT** và
     `mark_limited` đánh dấu **ĐÚNG LUẬT**. Mệnh đề của mục ấy ("41 key còn
     nguyên") ngầm giả định **bể key SẠCH**, điều kiện đó vỡ khi có cổng đốt
     lượt chạy ngay trước. Dấu hiệu nhận ra: thời gian chạy phồng
     **9,4-10,9s -> 15,9s** (thử lại vòng qua key bị khoá), và 3 lượt hồi quy
     cùng ngày TRƯỚC khi có cổng 74 đều **42/0**.
     **CÁCH ĐỌC:** thấy mục này đỏ thì **chạy lại cổng MỘT MÌNH sau khi bể key
     nguội** rồi mới nghi mã — **ĐỪNG hạ mốc 42, ĐỪNG bỏ mục này**. Muốn hết
     nhấp nháy thì tách hẳn hai cổng đốt-lượt-Groq ra xa nhau trong danh sách
     (chưa làm, chưa đo).
     **ĐÍNH CHÍNH 18/08/2026 (lượt hồi quy v2.37.0) — NGUYÊN NHÂN RỘNG HƠN
     "cổng đứng sát nhau", và có PHÉP ĐO DỨT ĐIỂM:** chạy cổng MỘT MÌNH 3 lượt,
     cách lượt Groq gần nhất 4-10 phút, vẫn ra **41 · 1** với **3 key** mang
     `limited`. Phép đo tách bạch: gọi `llm.complete_text` một câu **model
     SỐNG, KHÔNG dính 404 nào** trong tiến trình SẠCH -> `_KEY_STATE` khoá
     **đúng 3 key**, bằng y số cổng báo. Tức 3 key ấy bị khoá vì **429 THẬT**
     (bể key nóng do luồng khác trên máy đang đo giọng bằng Groq), `mark_limited`
     làm **ĐÚNG LUẬT**, và chuyện đó **không liên quan gì tới đường 404**.
     Chứng minh không phải hồi quy, 3 lớp: mục 3 và 3b (stub, tiền định) ra
     `KHÔNG phạt MỘT key nào — {}` · mệnh đề TRUNG TÂM *"404 THẬT của Groq ->
     app vẫn ra kết quả"* ĐẠT · `git diff v2.36.0..HEAD -- app/ai/llm.py` **0
     dòng** đụng `mark_limited`/`is_rate_limit_error`/`limited`/`429`.
     **Vậy mệnh đề "41 key còn nguyên" là mệnh đề về MÔI TRƯỜNG, không phải về
     mã** — nó chỉ chấm được khi bể key sạch. Cách chữa đúng là cho mục ấy tự
     canh bể key (như CA17 cổng 56 canh CPU: bận thì **BỎ QUA, không chấm**),
     chứ không phải hạ mốc. **Chưa làm, chưa đo.**
  71. `_test_demucs_gpu.py` → **TÁCH GIỌNG PHẢI DÙNG GPU KHI MÁY CÓ GPU**
     (18/08/2026). **ĐẠT 22 · HỎNG 0.** Thử phá (ghi cứng lại chỉ mục `whl/cpu`
     như bản cũ): **BẮT 4 mục**, mã thoát 1.
     **GỐC KHÔNG PHẢI Ở MÃ CHỌN THIẾT BỊ** — anh Hùng thấy *"Đang tách
     nhạc/giọng (249 giây, cpu)"* trên máy có RTX 3060, nhưng `_MA_TACH` viết
     đúng từ đầu (`dev = "cuda" if torch.cuda.is_available() else "cpu"`).
     Chỗ hỏng là **GÓI**: `cai_demucs` ghi cứng chỉ mục `whl/cpu` nên `_lib`
     luôn nhận `torch+cpu`, bản dựng đó KHÔNG có CUDA -> `is_available()` False
     vĩnh viễn. Máy có GPU hay không cũng ra một kết quả, **không một dòng báo**.
     Ghi chú cũ trong mã còn chốt nhầm *"bản CUDA không có gì để đánh đổi"* —
     câu đó đúng với chỗ nó nhìn (wheel PyPI 122,1 MB vs `+cpu` 121,9 MB, cả
     hai đều không kèm gói `nvidia-*`) nhưng kết luận SAI: **trên Windows phần
     CUDA nằm THẲNG trong wheel của chỉ mục `cu###`**, không đi qua gói
     `nvidia-*`. Trỏ `--extra-index-url` vào `cu126` là có bản CUDA thật (kiểm
     bằng `pip install --dry-run --report`: chọn đúng `torch==2.13.0+cu126`).
     **SỐ ĐO** (`_do_demucs_gpu.py`, 3 vòng **ĐAN XEN**, 60 giây tiếng THẬT,
     hai arm đi CHUNG runner của app — khác nhau đúng MỘT thứ là torch nào
     được nạp):

     | | CPU (`2.13.0+cpu`) | GPU (`2.13.0+cu126`) | nhanh gấp |
     |---|---|---|---|
     | `apply_model` | 25,06s | **2,70s** | **9,28x** |
     | cả lượt (wall) | 29,27s | **9,28s** | **3,15x** |
     | tỉ lệ so thời gian thật | 0,488x | **0,155x** | |

     **VRAM: đỉnh 1.536/12.288 MiB, Demucs chiếm thêm 893 MiB** -> còn 10,7 GB
     cho NVENC chạy cùng. **Phép đo VRAM đầu tiên của tôi SAI và tự nó ra số
     đẹp**: lấy mẫu TRƯỚC và SAU tiến trình con, mà tiến trình thoát là trả
     sạch VRAM -> ra đúng bằng mức nền (639 MiB) tức **không đo gì cả**. Phải
     POLL trong lúc chạy. Cùng họ "phép đo hỏng phát chứng nhận" (`astats` cổng
     53 · `startswith` cổng 44).
     **CHẤT LƯỢNG KHÔNG ĐỔI — VÀ CHỈ ĐỌC ĐƯỢC ĐIỀU ĐÓ KHI CÓ SÀN NHIỄU.** Đây
     là phần đáng giá nhất của lượt đo:

     | | lớp nhạc | lớp giọng |
     |---|---|---|
     | GPU vs CPU (đang hỏi) | −19,02 / −21,54 / −21,11 dB | −29,92 / −32,92 / −32,70 dB |
     | **CPU vs CPU (SÀN NHIỄU)** | **−19,24 / −22,05 dB** | **−29,65 / −32,63 dB** |

     Hai hàng **TRÙNG DẢI** nhau -> lệch GPU-CPU là **NHIỄU của chính Demucs**
     (nó không tiền định), KHÔNG phải "GPU làm đổi tiếng". Đọc mỗi số thô
     −19 dB rồi kết luận "GPU làm hỏng tách" là sai — đúng bẫy **"số thô là SỐ
     LỪA"** đã sập 3 lần. Tương quan 0,9936-0,9997 ở cả hai cột.
     **GIÁ: wheel CUDA 2.474,4 MB vs `+cpu` 121,9 MB** (đo bằng HTTP HEAD trên
     chính wheel, không ước bừa). Vì vậy **chỉ lấy bản CUDA khi máy THẬT SỰ có
     GPU NVIDIA**: `co_gpu_nvidia()` hỏi `nvidia-smi`, **KHÔNG import torch**
     (import torch trong tiến trình đã nạp Qt là ACCESS VIOLATION, `try/except`
     không chặn — xem `thiet_bi_tach`; mà hỏi torch cũng vô nghĩa vì torch đang
     cài LÀ bản CPU, đời nào cũng trả False = đúng vòng luẩn quẩn). Đoán nhầm
     thì hậu quả chỉ là tải gói to/nhỏ hơn — `_MA_TACH` vẫn tự quyết định thiết
     bị lúc chạy nên **máy nhân viên không GPU KHÔNG BAO GIỜ nổ vì hàm này**.
     **NHÃN PHẢI KHỚP ĐƯỜNG SẼ ĐI** (CA 4): ghi 155 MB rồi tải 2,5 GB là lặp
     đúng lỗi cũ chỉ đổi chiều (trước: nút ghi 155 MB, hộp doạ 2 GB).
     **2 LỖI CỦA CHÍNH CỔNG, lộ ra ngay lượt chạy đầu:** `inspect.getsource`
     mở file theo bảng mã MẶC ĐỊNH của máy (cp1252) -> docstring tiếng Việt ra
     mojibake rồi `ast.parse` nổ; và tự cắt 4 khoảng trắng đầu dòng để bỏ thụt
     lề thì cắt luôn vào THÂN DOCSTRING nhiều dòng -> `IndentationError`. Nay
     đọc thẳng file bằng **utf-8** rồi lấy đúng nút `FunctionDef` theo tên,
     không cắt gì.
     **KIỂM END-TO-END, KHÔNG DỪNG Ở "MÁY LÀM ĐƯỢC"** (`_do_lib_gpu_that.py`):
     phép đo A/B bật GPU bằng cách chèn `PYTHONPATH`, tức nó mới chứng minh
     CÁI MÁY làm được. Cửa thật là `_tach_demucs` -> tiến trình riêng ->
     `sys.path.insert(0, _lib)`. Chạy KHÔNG đặt `PYTHONPATH`: **`thiet_bi =
     cuda` · `torch = 2.13.0+cu126` · ổn định 3 lượt apply 2,65-2,69s / wall
     6,42s**. Cài bằng CHÍNH `cai_demucs()` của app (ok=True · gpu=True ·
     chi_muc=cu126 · 168 giây) nên `_lib` nay **tự đứng được một mình**
     (`thieu=[]`) — trả luôn nợ cổng 58 *"chưa tải torch thật về `_lib`"*.
     `_lib` từ 85 MB -> **4,3 GB**.
     **MÁY NHÂN VIÊN COPY `_lib` SANG THÌ SAO — ĐÃ ĐO, KHÔNG SUY ĐOÁN:** giả
     lập máy không GPU (`CUDA_VISIBLE_DEVICES=-1`) với `_lib` CÓ CUDA torch ->
     **`ok=True · thiet_bi=cpu · 29,66s`**, lùi êm, không nổ. (Bản CPU thuần
     đo 25,06s, tức chạy CPU bằng wheel CUDA chậm hơn ~18% — nói ra để ai copy
     `_lib` sang máy không GPU biết mình đang trả gì.)
     **BẪY ĐO MỚI, ĐÃ SẬP 1 LẦN: `CUDA_VISIBLE_DEVICES=""` (chuỗi RỖNG) KHÔNG
     giấu được GPU** — chạy vẫn ra `thiet_bi=cuda`. Phải dùng **`-1`**. May là
     runner có trả kèm `thiet_bi` và `torch` nên đọc ra ngay; nếu không thì ca
     "giả lập máy không GPU" đã tự ĐẠT trong khi nó đang chạy GPU. (Arm CPU
     của `_do_demucs_gpu.py` KHÔNG dính bẫy này vì lúc đó `_lib` chưa có torch
     nên nó nạp `.venv` bản `+cpu` — bảng số vẫn đúng, và mỗi dòng đều in kèm
     `torch=...` để tự chứng minh arm nào là arm nào.)
  72. `_test_giong_ngoai.py` → **GIỌNG NGOÀI (OmniVoice / IndexTTS)**. Xem
     docstring của chính file + `app/core/giong_ngoai.py`. **ĐẠT 48 · HỎNG 0.**
  73. `_test_giong_hang.py` → **GIÓNG HÀNG CƯỠNG BỨC** (`app/core/
     giong_hang.py`, 18/08/2026; +CA 8 ngày 19/08). **ĐẠT 41 · HỎNG 0.**
     Trước cổng này,
     `giong_hang.py` — chỗ lấy MỐC TỪNG CHỮ cho **mọi máy đọc không tự trả
     mốc** — chỉ có phép đo và bị canh GIÁN TIẾP qua cổng 72.
     **LỖI THẬT CỔNG NÀY TRUY RA (mục "1 câu Việt /12 gióng không nổi" treo từ
     lượt trước):** log ghi thẳng `ValueError: targets Tensor shouldn't contain
     blank index. Found tensor([[20, 5, 21, 2, 13, **0**, ...`. Giải mã theo
     bảng token MMS_FA ra `c o v i d - c h i c o n l a b a i`, tức chuỗi
     `"covid-..."`. Bảng token ánh xạ **`'-' -> 0`**, mà 0 CHÍNH LÀ blank
     truyền cho `forced_align(blank=0)`; `uroman` **giữ nguyên dấu gạch nối**
     (`COVID-19` -> `COVID-19`). Một chữ có gạch nối => torchaudio ném =>
     `except` trả `[]` cho **CẢ CÂU** => câu đó mất sạch mốc, **mã thoát vẫn
     0**. Chữa bằng lọc token theo **ID** (`BO` = mọi ký tự có id == BLANK,
     cộng `*`) chứ không lọc theo mặt chữ — bản torchaudio sau đổi ký tự blank
     thì vẫn đúng. Đo lại: câu có `COVID-19` ra **13/13 mốc** (trước: RỖNG).
     **THỬ PHÁ:** trả riêng dòng `return` của `ma_hoa` về bản cũ -> cổng ĐỎ,
     `5d ... 0/12 mốc`, mã thoát 1.
     **3 LỖI CỦA CHÍNH CỔNG, lộ ra ngay lượt chạy đầu:** (a) mục 5b hỏi thẳng
     `"blank=0" not in _MA_GIONG` -> **ĐỎ OAN NGAY**, vì chính dòng GHI CHÚ
     giải thích bản vá có chuỗi `forced_align(blank=0)` (bẫy 47/51/53/54, sập
     lại lần nữa); (b) mục 6c dùng `ast.unparse` rồi `find("WordBoundary")` ->
     trỏ vào **DOCSTRING** chứ không phải phần MÃ (unparse giữ docstring);
     (c) mục 5a chỉ hỏi hằng `BLANK` có mặt -> phép phá chỉ trả dòng `return`
     về cũ vẫn để `BLANK = 0` nằm đó nên mục ấy **tự ĐẠT OAN**.
     **LỖI THỨ HAI, TÌM RA 19/08/2026 — HAI LUỒNG DÙNG CHUNG FILE VIỆC/KẾT
     QUẢ.** `giong_hang_loat` đặt tên `viec_<pid>.json` / `ket_<pid>.json`
     theo `os.getpid()` **của tiến trình GỌI** — giống hệt nhau cho MỌI luồng
     trong app, mà làn `LAN_TG` mặc định **2 luồng**. Hai luồng ghi đè file
     việc của nhau, ghi đè file kết quả của nhau, và `finally` của luồng xong
     trước **XOÁ** file kết quả của luồng kia. Đo (`_do_gh_luong.py`, 2 mẻ 6
     câu, đan xen): chạy lần lượt **12/12 câu có mốc** · chạy 2 luồng
     **6/12**, đúng một mẻ mất trắng, **2/2 lượt**; log ghi *"tiến trình gióng
     hàng không ghi kết quả (mã 0)"* — **rc = 0**, không một dòng báo trên
     giao diện. Mất mốc mới là ca DỄ THẤY; ca nguy hơn là file việc bị ghi đè
     ĐÚNG LÚC -> tiến trình con gióng mẻ tiếng của luồng KIA rồi trả về ĐỦ số
     mục -> **mốc gán sai chữ, im lặng hoàn toàn**.
     Chữa bằng `_ma_lot()` = `p<pid>t<thread>n<đếm>`, mỗi LƯỢT GỌI một bộ tên
     (giữ `pid` ở đầu để `_don_rac_viec` còn quét mồ côi được).
     **`_viet_runner` CŨNG PHẢI MỘT-FILE-MỘT-LƯỢT — đã thử 2 cách rẻ hơn, cả
     hai hỏng trên Windows:** `write_text` đè lên đường dẫn dùng chung thì mở
     chế độ `w` = CẮT CỤT ngay file mà tiến trình con đang đọc; còn ghi tên
     tạm rồi `os.replace` (nguyên tử trên POSIX) thì Windows **từ chối thay
     file ĐANG MỞ** — ra `PermissionError [WinError 5] Access is denied` ngay
     lượt song song đầu tiên, vì python con đang giữ handle chính script đó.
     **ĐO LẠI SAU VÁ, 3 vòng đan xen: 12/12 · 12/12 · 12/12 câu có mốc** ·
     thời gian tường **lần lượt 15,49s vs 2 luồng 7,73s = 2 luồng NHANH 2,00×**
     · VRAM đỉnh **3.346 / 12.288 MiB** (mỗi tiến trình ~1.455 MiB).
     **KHÔNG serialize bằng khoá:** hai tiến trình gióng hàng song song đo ra
     nhanh gấp đôi và card còn thừa 8,9 GB — khoá lại là vứt đi 2×.
     **VRAM PHẢI POLL TRONG LÚC CHẠY** (bẫy cổng 71): lấy mẫu trước/sau ra
     đúng mức nền 430 MiB vì tiến trình thoát là trả sạch.
     **CA 8 CANH LẠI, có THỬ PHÁ:** 8a `_ma_lot` duy nhất qua 8 luồng
     (250/250) · 8b vẫn mở đầu bằng pid · 8c quét AST: thân `giong_hang_loat`
     gọi `_ma_lot()` và KHÔNG còn `getpid` · 8d 2 luồng THẬT cùng lúc ra
     **4/4 câu có mốc** · **8e vá `_ma_lot` trả hằng số (= bản cũ theo pid) ->
     rơi về 2/4**, tức 8d đang đo thật chứ không phải con dấu.
  74. `_test_json_bao_dung.py` → **JSON CỦA LLM ĐỨT/BỌC/THỪA CHỮ THÌ VẪN PHẢI
     SỐNG** (18/08/2026). **ĐẠT 80 · HỎNG 0.** Thử phá `_pha_json_bao_dung.py`
     (9 phép, mỗi phép gỡ ĐÚNG một chốt): **BẮT 9 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
     **LỖI CHẶN SẢN XUẤT thứ HAI trong hai ngày** (anh Hùng, v2.34.0, đường
     Thay giọng, 2 video ra *1 xong · 1 LỖI*): `LLMError: LLM trả về không phải
     JSON hợp lệ: Expecting value: line 1 column 1838 (char 1837)`.
     **GỐC RỄ — KHÔNG ĐẶT `max_tokens` KHÔNG PHẢI LÀ KHÔNG GIỚI HẠN.** Chú
     thích cũ trong `_call_once` ghi *"KHÔNG giới hạn token cứng: JSON chọn clip
     có thể dài, cắt cụt -> hỏng kết quả"* — đúng ý định, sai sự thật: **Groq
     tự áp trần MẶC ĐỊNH**. Đo `_do_json_dut.py` (Groq THẬT, prompt dịch 50 câu
     thật, 6/6 lượt): `openai/gpt-oss-120b` -> `completion_tokens` **3072** ·
     `openai/gpt-oss-20b` -> **2048**, `finish_reason` = **`length` 6/6**. Bản
     dịch cần **~3.100** token nên mảng JSON đứt giữa chừng. **Hụt ÍT nên bệnh
     CHẬP CHỜN** — video ngắn lọt, video dài chết, đúng ảnh "1 xong 1 lỗi".
     Cộng thêm: gpt-oss là model **SUY LUẬN**, phần "nghĩ" ăn CHUNG ngân sách
     đó, nên chỗ còn cho câu trả lời chỉ ~1.000 token.
     **RÀNG BUỘC TRẦN TRÊN, ĐỌC TỪ CHÍNH LỜI LỖI 413** (đừng đặt bừa):
     *"Request too large … service tier `on_demand` on tokens per minute (TPM):
     Limit 8000"* -> Groq tính **CẢ `max_tokens`** vào cỡ yêu cầu. Đo: prompt
     551 + max_tokens 7168 = **CHẠY** · 551 + 8192 = **413**. Nên `max_tokens`
     phải **TÍNH RA** (`max_tokens_groq`), và đó cũng là lý do **CHIA NHỎ yêu
     cầu** không phải tuỳ hứng mà là ràng buộc số học: prompt dài thì chỗ trả
     lời hẹp lại. 413 chính là bẫy đã đốt sạch 38 key một lần — nới bừa là dẫm
     lại.

     | max_tokens (50 câu, prompt 1413 tok) | out_tok | finish | parse |
     |---|---|---|---|
     | không đặt (= mặc định Groq) | 3072 | **length** | **HỎNG** |
     | 2048 | 2048 | length | HỎNG |
     | 3072 | 3072 | length | HỎNG |
     | **4096** | 3105 | **stop** | **ĐẠT 50/50** |
     | 6144 | 3077 | stop | ĐẠT 50/50 |
     | 8192 | — | — | **413** |

     **`reasoning_effort="low"` LÀ ĐÒN RẺ NHẤT** (max_tokens=4096, cùng prompt):
     mặc định **3.247** token / 7,3s -> low **1.214** token / **3,2s**, vẫn ĐẠT
     đủ 50 câu. Tức nghĩ ít đi thì vừa còn chỗ cho câu trả lời vừa **nhanh 2,3
     lần**. **`"none"` BỊ GROQ TỪ CHỐI** (400 *"must be one of `low`, `medium`,
     or `high`"*) — **khác `qwen3.6` bên vision**, đừng chép tham số từ đó sang
     (mục cổng 26 ghi `reasoning_effort="none"`, chỉ đúng cho qwen).
     **`response_format={"type":"json_object"}` CHẠY trên gpt-oss** (2/2 mỗi
     model) và **KHÔNG đổi HÌNH DẠNG** — vẫn trả MẢNG `[{"i":..,"t":..}]` chứ
     không bị bọc thành object, nên `thay_giong._theo_nhan` lấy đủ 12/12 (đo
     `_do_hinh_dang.py` — phải đo, vì bật json_object mà nó bọc lại thành
     object là hỏng đường lấy-theo-nhãn mà không một dòng báo). `groq/compound`
     thì 413 -> để ngoài.
     **NHƯNG json_object CÓ MẶT TỐI, bắt được đúng lúc chạy cổng với Groq
     THẬT:** Groq dùng bộ giải mã có **RÀNG BUỘC**, model không sinh nổi JSON
     trong ràng buộc đó thì nó trả **400 "Failed to generate JSON. Please
     adjust your prompt."** = KHÔNG trả câu nào. Bật json_object mà thiếu lưới
     là **đổi một bệnh chập chờn lấy một bệnh chập chờn KHÁC**, và bệnh mới tệ
     hơn vì lời lỗi "Gọi groq thất bại" chẳng nói gì. Nay `la_loi_tham_so_them`
     gom cả 3 thân lỗi 400 -> **gọi lại kiểu TRẦN**. Luật chung: **một TUỲ CHỌN
     không bao giờ được phép giết cả lượt.**
     **BỘ BÓC BAO DUNG DÙNG LẠI, KHÔNG VIẾT MỚI:** `llm._extract_json` (alias
     công khai `boc_json`) là cửa DUY NHẤT — `complete_json` và
     `complete_vision_json` vốn đã đi qua nó. Thêm: khối ```` ```json ```` MỞ mà
     chưa đóng · dấu phẩy thừa · **`vot_json_cut`** vớt phần HOÀN CHỈNH của
     JSON bị cắt. **Phần tử mảng dở dang thì BỎ HẲN** (trả `{"i":3}` thiếu
     `"t"` là đẻ ra một mục trông như thật — họ bẫy "phép đo phát chứng nhận");
     riêng giá trị CUỐI của object mà là container thì vớt tầng trong, vì đó là
     hình dạng của recap `{"title":…,"parts":[…]}`.
     **LỖI THỨ TỰ mà chính cổng lôi ra:** phải vớt **cấu trúc NGOÀI CÙNG TRƯỚC**
     bước "ứng viên". Với `{"mach_lac":8,"thu_tu":[1,0,2],"vi_sao":"đảo cho x`
     (object ngoài cùng không có `}` nào), bước ứng viên đi bắt **MẢNH LỒNG BÊN
     TRONG** `[1,0,2]` rồi trả về một **LIST**; `mach_lac.doc_ket` đòi dict nên
     vứt sạch. **Bản mốc KHÔNG NÉM mà trả SAI HÌNH DẠNG** — sai ruột nguy hiểm
     hơn không parse được, vì caller không có cách nào biết mình vừa nhận nhầm.
     **`complete_json`: 2 lượt đầu parse NGHIÊM (`cho_vot=False`), lượt CUỐI mới
     vớt** và lấy bản vớt ĐƯỢC NHIỀU NHẤT trong 3 lượt. Nhờ vậy vẫn còn cơ hội
     đòi bản ĐỦ, mà hết lượt thì trả phần thiếu chứ không TAY TRẮNG —
     `_dich_loat` đếm nhãn thiếu rồi đòi lại đúng phần đó (vòng `VONG_DOI_LAI`
     đã có sẵn, chưa bao giờ chạy tới vì mất sạch dữ liệu).
     **LỜI LỖI PHẢI ĐÚNG BỆNH:** `LLMCatCut` — *"AI trả lời quá dài nên bị CẮT
     giữa chừng"* + *"KHÔNG phải hết hạn mức key"*. Lời cũ *"không phải JSON hợp
     lệ"* chỉ đúng phần NGỌN, nghe như model trả rác nên người đọc đi soi
     prompt/parser trong khi bệnh ở trần token — đúng vết xe 404-model-chết bị
     báo thành "Dữ liệu không hợp lệ" hôm trước. **KHÔNG PHẠT KEY** (lỗi ĐỊNH
     DẠNG, mọi key cùng trần).
     **`_uoc_token` HIỆU CHUẨN, KHÔNG ĐOÁN** (`_do_uoc_token.py`, trên
     `usage.prompt_tokens` THẬT 551/874/1413): hệ CJK 1,1 + phần còn lại chia
     2,2 -> 560/884/1424 = phồng nhiều nhất **1,02x**, **0 mốc hụt**. Ước HỤT là
     `max_tokens` đặt quá tay rồi ăn 413, nên bộ ước phải luôn >= số thật.
     **VIỆC 3 — RÀ CẢ LỚP BỆNH:** 3 chỗ còn tự dò dấu ngoặc bằng regex ĐÒI dấu
     ĐÓNG nên câu trả lời bị cắt là trượt sạch: `chon_doan.cham_mu`
     (`re.search(r"\[.*\]")` -> mất cả bảng chấm, rơi hết về điểm AI tự chấm) ·
     `mach_lac.doc_ket` (`re.search(r"\{.*\}")` -> lượt hậu kiểm im lặng bỏ
     qua) · `recap._director_from_data` (`json.loads` trần trên JSON-trong-
     chuỗi). Cả 3 nay nối vào `boc_json` **ĐẶT SAU đường cũ** nên JSON hợp lệ
     ra kết quả Y HỆT — cổng CA 1 so 9 mẫu hợp lệ với bản mốc, **0 lệch**.
     **TỈ LỆ HỎNG TRƯỚC/SAU trên ĐÚNG đường app đi** (`thay_giong._dich_loat`,
     50 câu THẬT, Groq THẬT): **TRƯỚC 6/6 HỎNG (100%)** · **SAU 18/18 ĐẠT
     (0%)**, 0 câu còn nguyên tiếng gốc.
     **MỐC ĐỐI CHỨNG `v2.35.0`** (bản phát hành NGAY TRƯỚC; đo
     `git diff v2.34.0 v2.35.0 -- app/ai/llm.py` **RỖNG** nên v2.35.0 mang y
     nguyên bệnh của v2.34.0) + chốt *"mốc TRÙNG bản đang test -> HỎNG"*.
     **2 LỖI CỦA CHÍNH CỔNG, do THỬ PHÁ lôi ra:** (a) bỏ `_ghi_ket_thuc(resp)`
     mà cổng **VẪN XANH** — vì mọi ca khác đều tự gán `_LAN.ket_thuc` bằng tay;
     không ai ghi `finish_reason` thì `complete_json` không bao giờ biết mình bị
     CẮT và **lại báo sai bệnh y như v2.34.0**. Nay CA 7 gọi `_call_once` THẬT
     với stub trả `stop`/`length` rồi đòi đọc lại đúng. (b) cổng **CHẾT** giữa
     chừng (`AttributeError` vì `do.get(...)` nằm trong tham số của `ok()`) thay
     vì BÁO HỎNG -> mất luôn dòng tổng kết, đọc ra không phân biệt được với
     "chưa chạy tới chốt".
     **2 GIẢ ĐỊNH CŨ BỊ BÁC BẰNG SỐ, ghi để đừng ai chép lại:** *"không đặt
     max_tokens = không giới hạn"* (SAI, Groq có trần mặc định) và
     *`reasoning_effort="none"`* (SAI với gpt-oss, chỉ đúng với qwen3.6).
     **CHƯA LÀM, GHI THẲNG:** `_dich_loat` vẫn gửi CẢ LOẠT câu trong một lượt —
     nay nó sống nhờ vớt + đòi lại, chứ **chưa tự chia mẻ theo ngân sách
     token**. Video dài hơn corpus 50 câu (prompt > ~2.500 token) sẽ ăn dần vào
     chỗ trả lời; `max_tokens_groq` co lại đúng luật nên không 413, nhưng số
     vòng đòi lại sẽ tăng. Muốn chắc thì chia mẻ ngay từ `_dich_loat` — chưa đo,
     chưa làm.
  75. `_test_clip_mo_duoc.py` → **CLIP XUẤT RA PHẢI MỞ ĐƯỢC** (18/08/2026).
     **ĐẠT 63 · HỎNG 0.** Anh Hùng gửi ảnh trình phát Windows: *"khi phân tích
     cắt các part cứ báo lỗi, video bị trắng"* — `We can't open … It uses
     unsupported encoding settings. 0x80004005`. Gốc: `_enc_args` (hàm sinh
     tham số cho FILE THÀNH PHẨM) có `-pix_fmt yuv420p` ở nhánh `h264_nvenc`
     nhưng nhánh `libx264` thì KHÔNG -> x264 lấy pix_fmt theo ĐẦU RA FILTER
     GRAPH -> nguồn 10-bit ra **High 10**, nguồn 4:4:4 ra **High 4:4:4** =
     đúng lời lỗi + đúng triệu chứng KHUNG TRẮNG, mà ffmpeg vẫn **mã thoát 0,
     đủ khung, đủ `moov`** (họ bẫy *thành công giả*).
     **NVENC KHÔNG PHẢI THỦ PHẠM — ĐỌC KỸ TRƯỚC KHI ĐI SỬA LẠI.** Nhánh nvenc
     **vốn đã có `yuv420p` từ trước bản vá**; `df14b01` chỉ bổ sung thêm
     `-profile:v high`. Đo trên máy này (`_do_nvenc_that.py`): NVENC mã TRƯỚC ra
     `yuv420p / **Main**`, mã NAY ra `yuv420p / **High**` — cả hai đều 8-bit
     4:2:0 nên **cả hai đều mở được**. Tức anh Hùng xuất bằng NVENC thì con
     đường ra file hỏng là những lượt **LÙI VỀ libx264** (`_run_with_fallback`
     lùi khi NVENC lỗi) chứ không phải lượt NVENC.
     **HAI THỨ CHE MẤT BỆNH — biết trước thì khỏi kết luận oan "chốt chỉ là
     trang trí" (chính mục tự-kiểm 7e của cổng đã PASS OAN vì cái này):**
     · **NHIỀU ĐOẠN** đi qua mezzanine `_build_seg`, mà mezz **đã ép `yuv420p`
       sẵn** (vá từ cổng 42) -> đầu vào lượt encode cuối đã là 420p;
     · nền **`blur` dùng `overlay`**, mà `overlay` của ffmpeg mặc định
       **`format=yuv420`** -> nó GHIM 420p bất kể nguồn.
     Đo 12 arm trên nguồn 10-bit THẬT qua chính `export_canvas_clip`: bản gỡ
     chốt ra `yuv420p` ở **MỌI** arm dùng `blur` hoặc nhiều đoạn. Chỉ đường
     **1 ĐOẠN + `bg="fill"`** (không overlay) mới thả nguồn 10-bit xuống thẳng
     encoder: gỡ chốt -> **`yuv420p10le / High 10`** · bản thật -> `yuv420p /
     High`. Mục 7 nay chạy đúng cấu hình đó, nên nó chứng minh chốt **chịu
     lực** chứ không phải con dấu.
     **KHÔNG NHÌN ẢNH MÀ PHÂN BIỆT ĐƯỢC:** ffmpeg giải mã High 10 **bình
     thường**, nên trích khung ra PNG thì file HỎNG và file LÀNH cho ra ảnh
     giống nhau (đã mở cả 12 ảnh ra nhìn: đều là hình thật, không khung trắng).
     Khung trắng là chuyện của **trình phát Windows**, không tái hiện được bằng
     ffmpeg. Thước duy nhất phân biệt được là **`profile` trong ffprobe** — đây
     là ca hiếm mà "mở ảnh ra nhìn" KHÔNG đủ, ngược với bài học tofu cổng 68.
     Cổng vẫn trích PNG (mục 5) để bắt ca hỏng KHÁC: đơn sắc / trắng xoá.
     **CHƯA LÀM, GHI THẲNG:** chưa ai mở thử bằng chính trình phát Windows của
     anh Hùng (luật cấm mở trình phát trên máy anh ấy) — chuỗi suy luận
     High 10/4:4:4 -> 0x80004005 lấy từ lời lỗi, chưa có phép đo tận mắt.
  80. `_test_khong_xoa_nham.py` → **KHÔNG BAO GIỜ XOÁ NHẦM THƯ MỤC ĐANG LÀM
     VIỆC** (19/08/2026). **ĐẠT 69 · HỎNG 0.** Thử phá `_pha_xoa_nham.py`:
     **BẮT 7 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**. Đứng **ĐẦU** `_chay_hoi_quy.py`.
     **ĐÃ MẤT CẢ CÂY MÃ HÔM ĐÓ, KHÔNG PHẢI GIẢ ĐỊNH:**
     `giong_ngoai._doc_omnivoice` gọi `_don(Path(ket.get("_sandbox") or ""))`
     ở nhánh LỖI, mà `_chay_ov` không đặt `_sandbox` ở nhánh quá-giờ ->
     `Path("")`. **`Path("")` KHÔNG RỖNG — nó là `WindowsPath('.')`**:
     `str()` ra `'.'` (truthy, lọt mọi canh `if d`), `.is_dir()` ra True (lọt
     mọi canh `is_dir()`), rồi `rmtree` **xoá sạch thư mục đang làm việc**.
     Mất `.git` (chỉ còn `objects`), `.venv`, `bin`, `_lib`, `_giong_hang`,
     `_piper`, `_giong_ngoai`, **và `.env` 41 key** — **mã thoát vẫn 0**.
     `b5bd003` vá ĐÚNG MỘT cửa. Quét lại toàn `app/` ra **5 cửa nữa cùng hình
     dạng**, xếp theo mức nguy hiểm:
     (a) **`services.delete_project`** — `_project_dir` trả thẳng
     `Path(row["assets_dir"])`; dòng DB có `assets_dir` RỖNG -> `Path("")` ->
     `.exists()` True -> `rmtree('.')`. Nguy nhất vì đây là đường NGƯỜI DÙNG
     BẤM ("Xoá kênh") và dữ liệu vào đến từ **DB — mà DB này đã từng vỡ**.
     (b) **`queue/jobs._don_thu_muc_tam`** — `""` may mà thoát
     (`os.path.isdir("")` False) nhưng **`"."` thì `isdir` trả True**; gốc ổ
     đĩa cũng lọt. `thu_muc_lam` đến từ PAYLOAD trong DB.
     (c) **`core/piper_tts._don`** — `rmtree(d, ignore_errors=True)` TRẦN,
     không một phép kiểm. Chưa nổ CHỈ VÌ nơi gọi hiện thời may mắn truyền
     đường dẫn con — đó là MAY, không phải chốt.
     (d) **`core/tempsweep._xoa`** — `rmtree(ignore_errors=False)` rồi
     `except OSError` nuốt im lặng. An toàn DO XÂY DỰNG (mọi nơi gọi truyền
     con của `glob`/`iterdir`), nhưng một mẫu tên mới vô ý (`"*"`) là đủ.
     (e) `core/thay_giong.doc_thu` finally — đường dẫn suy ra từ tham số.
     **CHỮA BẰNG CỬA CHUNG `app/core/xoa_an_toan.py`, KHÔNG VÁ LẺ** — vá lẻ
     là bỏ sót cửa thứ 6 người sau thêm vào. Bốn chốt: `None`/chuỗi rỗng ·
     **thư mục đang làm việc + mọi thư mục CHA của nó** (chốt bắt `Path("")`
     và `"."`, tức chốt đã cứu cây mã) · gốc ổ đĩa/hệ thống/người dùng/gốc
     cây mã · `trong=` và `ten_bat_dau=` làm lớp thứ hai.
     **CỔNG CHẠY VỚI `os.chdir(<hộp cát>/lam)`** nên bản vá hỏng thì thứ bị
     xoá là hộp cát chứ không phải repo; mồi canary đặt ở **CẢ `lam/` LẪN
     THƯ MỤC CHA** (chỉ đặt trong `lam/` thì ca `".."` đi lọt). **Gốc ổ đĩa
     KHÔNG BAO GIỜ đưa cho `rmtree` thật** — CA 4 vá `shutil.rmtree` thành
     GIÁN ĐIỆP chỉ ghi sổ, nên guard hỏng thì đọc được sổ chứ không phải xoá
     ổ C rồi mới biết. CA 6 quét tĩnh bằng **AST** (quét bằng chuỗi thì chính
     DÒNG GHI CHÚ giải thích bản vá bị kể là vi phạm — bài học 47/51/53/73):
     mọi file `app/` gọi `shutil.rmtree` phải nằm trong **sổ 9 file đã rà**,
     thêm file lạ là ĐỎ.
     **LƯỢT THỬ PHÁ ĐẦU RA `BẮT 5 · LỌT 2` — hai lỗ của CHÍNH CỔNG:**
     · **LỌT 6** — gỡ chốt GỐC Ổ ĐĨA mà cổng vẫn xanh. Lý do là HOÀN CẢNH chứ
       không phải chốt: hộp cát nằm trong `%TEMP%` nên **`C:\` là thư mục CHA
       của cwd**, còn **`D:\` là thư mục CHA của gốc cây mã** -> hai chốt KHÁC
       bắt hộ. **QUY TẮC CHUNG rút ra: mục nào canh MỘT chốt cụ thể thì phải
       đọc LÝ DO cụ thể**, hỏi mỗi "có chặn không" là mục đó tự vô hiệu ngay
       khi có chốt thứ hai tình cờ phủ lên. Nay CA 1 đòi đúng tiền tố
       `GỐC Ổ ĐĨA` / `THƯ MỤC ĐANG LÀM VIỆC` / `thư mục CHA`.
     · **LỌT 7** — phép phá viết SAI: nó đổi `goc` thành đường dẫn không bao
       giờ khớp, mà mệnh đề là `if p == goc or goc not in p.parents: return`
       nên vế hai LUÔN ĐÚNG -> `_don` **TỪ CHỐI MỌI THỨ**, tức "phá" làm hàm
       CHẶT HƠN. Cổng xanh là ĐÚNG nhưng bảng đọc thành "cổng không bắt được".
       **Phá thì phải GỠ SẠCH chốt, đừng đổi giá trị bên trong nó.**
     **CỔNG TREO ~10 PHÚT, PHẢI GIẾT TAY (lỗi của cổng, không của app):** CA 4
     gọi `tempsweep._xoa("C:\")`, mà `_co()` đi `rglob("*")` để đo dung lượng
     **TRƯỚC** khi xoá -> quét cả ổ C 564 GB. Đọc ra là *"mã thoát 4294967295,
     KHÔNG có dòng tổng kết"*. Nay vá `_co` về 0 trong đúng ca đó. Nhân tiện
     đó cũng là lý do chốt `ly_do_cam` phải đứng **TRƯỚC** `_co` trong `_xoa`.
     **BẪY WINDOWS ĐÃ SẬP:** hộp cát bản đầu dùng thư mục tên **`con`** ->
     `NotADirectoryError [WinError 267]` **100% lượt**, kể cả `os.makedirs` +
     5 lần thử lại. `CON` là **TÊN THIẾT BỊ Windows** (họ `PRN`/`AUX`/`NUL`/
     `COM1`/`LPT1`). Bẫy này ĐÃ CÓ SẴN trong repo (`piper_tts._lam_sach` ghi
     đúng nó) mà lượt này vẫn dẫm phải; lời lỗi trông y hệt lỗi tranh chấp AV
     nên suýt bị chữa nhầm bằng "thử lại nhiều lần hơn".
     `app/core/giong_vieneu.py` **CỐ Ý KHÔNG có phép phá** (hai luồng khác
     đang sửa file đó; lượt chạy này đã từng bị giết giữa chừng, giết đúng lúc
     phá là để lại bản hỏng trong file người khác) — cổng vẫn CHẤM
     `giong_vieneu._don` ở chế độ đọc-only qua CA 3 và CA 4.
  85. `_test_nghe_thu_nn.py` → **NGHE THỬ PHẢI ĐỌC ĐÚNG NGÔN NGỮ, VÀ BÁO KHI
     GIỌNG KHÔNG ĐỌC ĐƯỢC TIẾNG ĐÓ** (19/08/2026). **ĐẠT 75 · HỎNG 0.**
     Anh Hùng: *"cái phần nghe thử chọn tiếng Anh ngôn ngữ đó cứ ra tiếng Việt
     lung ta lung tung"*. **GỐC:** `thay_giong.doc_thu` dùng **MỘT câu tiếng
     Việt CỐ ĐỊNH** (`CAU_NGHE_THU`) cho mọi giọng -> chọn giọng tiếng Anh là
     nghe giọng Anh cố đọc chữ Việt, ra tiếng lạ, và người nghe kết luận
     **"giọng này hỏng"**. Cửa nghe thử CŨ (`dubbing.synth_demo`, hộp Lồng
     tiếng) đã chọn câu theo ngôn ngữ của giọng **TỪ LÂU** — chỉ đường Thay
     giọng bị sót, tức lỗi SÓT CHỖ NỐI chứ không phải thiếu ý tưởng.
     **CHỮA:** `cau_nghe_thu(nn)` lấy câu theo NGÔN NGỮ, nguồn là
     `dubbing._DEMO_TEXTS` (**NGUỒN DUY NHẤT**, dùng chung với hộp Lồng tiếng)
     + câu Việt quen của anh Hùng; thêm `de` vào bảng đó (11 ngôn ngữ đích nay
     đủ 11 câu — trước thiếu tiếng Đức nên nó **lùi về câu TIẾNG ANH**, đúng
     bệnh chỉ khác chiều). `nn_cua_giong(voice)` trả ngôn ngữ giọng ĐỌC ĐƯỢC
     (`vn:Adam`->en · `vn:` khác->vi · `piper:vi_VN`->vi · `vbee:`->vi ·
     `el:`/`gemini:`/`ov:`/`cb:`->`""` đa ngữ, **KHÔNG kết luận bừa**).
     `doc_thu(..., nn=)` lấy câu theo NGÔN NGỮ ĐÍCH; `nn` rỗng thì SUY TỪ CHÍNH
     GIỌNG nên **lối gọi cũ không phải sửa mà vẫn hết bệnh**.
     **KHÔNG đọc ngôn ngữ đích từ QSettings** dù làm vậy thì khỏi sửa hộp
     thoại: hộp chỉ ghi cài đặt lúc Chạy/đóng nên setting là lựa chọn **CŨ** —
     đúng lỗi "chạy dây chuyền lấy nhóm từ setting nên chạy sai nhóm". Trạng
     thái đang hiện nằm ở WIDGET (`cb_nn`), phải truyền vào.
     **GIỌNG KHÔNG ĐỌC ĐƯỢC TIẾNG ĐÓ -> BÁO, KHÔNG ĐỌC BỪA:** `canh_bao` nói
     cả hai vế (*"giọng này đọc tiếng «vi», câu mẫu là tiếng «en» ... nghe lạ
     là ĐÚNG theo cấu tạo, KHÔNG phải giọng hỏng"*) + chỉ cách chọn đúng, và
     hộp HIỆN nó lên dòng trạng thái (`_nghe_xong` thêm vế thứ tư). Vẫn ĐỌC:
     đó đúng là thứ lượt xuất thật sẽ ra nếu giữ lựa chọn này.
     **BỆNH THỨ HAI ÍT AI THẤY:** `doc_thu` gọi `doc_ban_dich` mà **để mặc định
     `dich_sang="en"`** -> nghe thử câu TIẾNG VIỆT mà giọng hỏng thì cửa chung
     lùi sang **giọng TIẾNG ANH đọc chữ Việt** = đúng bệnh đang chữa, khác
     đường vào. Nay truyền `dich_sang=nn_cau` (cổng đòi nó là **BIỂU THỨC**,
     hằng số là bản cũ — bài học cổng 56d).
     **VẪN ĐI QUA `doc_ban_dich`**, KHÔNG đẻ chỗ gọi `_synth_all_words` thứ 4
     (cổng 63 vẫn 24/0). Cache khoá theo CÂU nên đổi ngôn ngữ ra file KHÁC
     (đo: MD5 khác nhau) chứ không trả tiếng cũ.
     **TỰ KIỂM (CA 7):** vá `cau_nghe_thu` về bản CŨ (luôn câu Việt) -> mệnh đề
     trung tâm CA 3 **VỠ**; bỏ một ngôn ngữ khỏi bảng -> CA 1 đỏ.
     **0 KÝ TỰ ElevenLabs:** nhánh `el:` vá `synth_demo` thành hàm sinh mp3
     bằng ffmpeg, kèm mục chốt *"bản vá ĂN được"* (thiếu chốt đó thì ca `el:`
     tự ĐẠT vì lý do NGƯỢC HẲN — bẫy cổng 67).
     **SỐ CỔNG LÀ 85, KHÔNG PHẢI 81:** trong cùng ngày một luồng khác đã lấy
     81/82/83/84. Trùng số là hai cổng **ghi đè `_kq81.txt` của nhau** (bài học
     70 vs 69) — cách kiểm số còn trống là đọc `_chay_hoi_quy.CONG`, đừng đếm
     theo trí nhớ.
     **BẢN ĐẦU CỦA CỔNG ĐỎ OAN 1 MỤC** vì quét chuỗi `"Adam"` trúng đúng DÒNG
     GHI CHÚ của bản vá -> nay quét bằng `tokenize` (bỏ COMMENT+STRING) kèm
     mục TỰ KIỂM BỘ DÒ. Mục "nói luôn CÁI GIÁ" cũng đỏ oan một lượt vì so
     nguyên văn `"hạn mức"` trong khi nhãn cố ý VIẾT HOA. Hai cái này là **bài
     học 47/51/53/73 lặp lại lần thứ năm**: quét chuỗi trên file có ghi chú
     tiếng Việt thì kiểu gì cũng tự bắn vào chân.
     **KÈM CA 9 — NHÃN `vn:Adam` PHẢI NÓI THẬT + CHỈ ĐƯỜNG:** xem khối *"Adam
     NGHE LẠ"* ngay dưới.
  86. `_test_de_giong.py` → **CHẾ ĐỘ "ĐÈ GIỌNG, KHÔNG TÁCH"** (`thay_giong.
     CACH_TRON`, 19/08/2026). **ĐẠT 62 · HỎNG 0.** Thử phá `_pha_de_giong.py`
     (8 phép, mỗi phép gỡ ĐÚNG 1 chốt): **BẮT 8 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
     Anh Hùng đề xuất: *"thêm tính năng KHÔNG tách nhạc nền, chỉ GIẢM tiếng
     video gốc rồi ĐÈ giọng lồng tiếng vào, để không bị mất mấy tiếng của
     video"*. Ý đó tốt vì nó **KHÔNG TẠO RA** bệnh: chỗ tách chính là chỗ sinh
     ra mất tiếng · dìm nhạc · cần torch 4,3 GB · cần GPU. Mất tiếng về **0
     THEO CẤU TẠO** — không bỏ gì thì không có gì để mất.
     **DÙNG LẠI, KHÔNG VIẾT MỚI — và đây là phần đáng nói nhất:**
     `tron_thay_giong` đã có ĐỦ ducking theo CỬA SỔ giọng lồng
     (`sidechaincompress`) + cân bằng giọng-nhạc ĐO-rồi-tính + chuẩn hoá −14
     LUFS + `alimiter level=0 latency=1` + chốt độ dài. Chỗ khác nhau duy nhất
     giữa hai cách là **CÁI GÌ được truyền vào làm lớp nền**: lớp nhạc Demucs,
     hay CHÍNH `goc_wav`. Nên bản vá chỉ đổi **3 thứ** trong `thay_giong_video`:
     bỏ bước `tach_giong` · nền = `goc_wav` · **bỏ `bu_giong_goc`** (ở chế độ đè
     giọng gốc còn NGUYÊN trong nền, bù thêm là **cộng cùng một tín hiệu HAI
     LẦN** = vang đôi, và mảnh bù còn kéo lệch cả phép cân bằng).
     **MẶC ĐỊNH GIỮ CÁCH CŨ** — đổi mặc định là đổi tiếng của MỌI video từ nay
     trên 200-300 kênh đang chạy sản xuất. Cờ **chỉ góp vào hash khi THẬT SỰ
     BẬT** và nối vào **ĐUÔI chuỗi `sig`** (`:dg=1`), KHÔNG thêm phần tử vào
     tuple: đo được khoá khi TẮT giống **TỪNG KÝ TỰ** mốc v2.39.0 trên 6 tổ hợp
     cờ cũ (bài học `ovl_spec` cổng 42 · `che_chu` cổng 56e).
     **THƯỚC MẤT TIẾNG CŨ LÀ THƯỚC *THIÊN VỊ* — ĐỌC KỸ TRƯỚC KHI ĐO LẠI.**
     `_do_mat_giong.khoang_mat` gọi một cửa sổ là "IM" khi nó không nổi quá
     `SÀN_NHIỄU_CỦA_CHÍNH_FILE_ĐÓ + 4 dB`, sàn = bách phân vị 20 của chính file.
     Arm đè giữ NGUYÊN tiếng gốc -> lớp giọng ĐẦY HƠN -> ít cửa sổ im hơn ->
     sàn CAO HƠN -> ngưỡng "IM" **khắt khe hơn**. Đo trên video 2, CÙNG lượt
     chạy: arm TACH sàn **−31,91** (ngưỡng IM −27,91) · arm DE sàn **−24,14**
     (ngưỡng IM −20,14) = **khắt khe hơn 7,77 dB**, và nó chấm arm DE ra
     **10,65 s** trong khi arm TACH chỉ 6,40 s. Đọc thẳng *"DE mất nhiều hơn"*
     là đúng bẫy **"số thô là SỐ LỪA"**.
     **THƯỚC ĐÚNG (`_do_mat_tuyet_doi.py`):** MẤT = gốc CÓ tiếng **VÀ**
     `bao_gốc[i] − bao_xuất[i] > TRU_DB`. Cả hai arm dùng **CÙNG sàn (của BẢN
     GỐC)** và CÙNG ngưỡng tụt -> hết thiên vị theo cấu tạo. `TRU_DB = 20` SUY
     TỪ HẰNG SỐ CỦA APP: `HA_NHAC_TOI_DA_DB` 8,0 + `DUCK_DB_DO_DUOC` 3,28 =
     **11,28 dB** là mức tụt HỢP LỆ lớn nhất -> 20 chừa 8,7 dB biên.
     **NGƯỠNG ĐÓ KHÔNG PHẢI CHỖ TINH CHỈNH, VÀ ĐÂY LÀ BẰNG CHỨNG:** phân bố số
     ô theo độ tụt của arm DE = `<5: 1920 · 5-11,28: 1277 · **11,28-20: 0** ·
     **20-30: 0** · >=30: 2`. Hai nhóm **TÁCH RỜI HẲN** (khoảng trống 11,28→30
     dB không có ô nào) nên đặt ngưỡng ở đâu trong khoảng đó cũng ra cùng kết
     quả. (2 ô >=30 dB là ô lẻ 0,05 s, dưới sàn `DAI_MIN` 0,30 s -> không tính.)
     **SỐ ĐO GHÉP CẶP** (một lượt dây chuyền/video, hai arm tách ra ở đúng tham
     số `nhac_wav` -> cùng bản tách/chép lời/dịch/FILE GIỌNG; đo rời hai lượt
     lệch **1,81 lần** vì LLM không tiền định):

     | thước | TACH (cũ, ĐÃ có `bu_giong_goc`) | **DE (mới)** |
     |---|---|---|
     | **TUYỆT ĐỐI (đúng)** | **4,25 s / 0,83%** | **0,00 s / 0,00%** |
     | tương đối (thiên vị) | 6,40 s | 10,65 s |

     Phân bố độ dài khoảng của arm DE: **0,00 ở CẢ BỐN bậc** (<0,5 · 0,5-1 ·
     1-2 · >=2 s). Chốt chống-đạt-oan: arm TACH ra 4,25 s > 0 -> thước CÓ RĂNG.
     **GIÁ PHẢI TRẢ, NÓI THẲNG BẰNG SỐ:** ở chế độ đè, nền CHỨA CẢ GIỌNG GỐC
     nên nó to hơn hẳn lớp nhạc -> **CẢ HAI trần cùng bịnh**. Đo e2e clip 40 s:
     giọng nâng chỉ **+5,12 dB** (trần đỉnh) và nền chỉ hạ được **−8,00 dB**
     (đúng trần `HA_NHAC_TOI_DA_DB`) -> giọng trên nền **+3,77 dB** thay vì đích
     6,0 (kể ducking **+7,05**). Trên video dài hơn thì đủ đích: video 1
     **+4,56** (kể né 7,84) · video 2 **+6,00** (kể né 9,28). **ĐỪNG nới hai
     trần đó để đạt +6** — đó là đổi tiếng gốc lấy con số, mà tiếng gốc chính là
     thứ tính năng này cố ý giữ.
     **ĐỘ TO + ĐỈNH trên file thành phẩm** (sau đời nén AAC, đúng thứ anh Hùng
     nghe): I **−14,02 LUFS**, HAI thước độc lập đồng ý **0,03 LU** (`loudnorm`
     −14,03 · `ebur128` −14,00), LRA 1,5, TP **−1,41 dBTP**, đỉnh −1,448 dBFS ->
     trần trừ HAI LẦN chạy đúng.
     **HAI THƯỚC ĐỘ TO CHỈ ĐỒNG Ý TRONG VÙNG HIỆU CHUẨN — số mới, đáng nhớ:**
     lệch **0,03-0,08 LU** trên nguồn THẬT (LRA 1,8-2,1, Douyin master nén sẵn)
     và trên nguồn LIÊN TỤC, nhưng **0,5-1,3 LU** trên nguồn dải động RỘNG (LRA
     10-14) — cửa chặn TƯƠNG ĐỐI của BS.1770 làm khối 400 ms lật vào/ra khác
     nhau, **KHÔNG phải thước nào hỏng**. Vì vậy cổng 86 chạy phép đối chiếu
     0,5 LU ở **CA 7, trên nguồn THẬT**; trên nguồn tổng hợp thì in cả hai số
     nhưng chấm bằng `loudnorm` (đúng bộ đo `chuan_do_to` dùng). **Nới ngưỡng
     cho hết đỏ là đúng lúc mất khả năng bắt một thước hỏng thật.**
     **BA CỬA CỦA CHỐT DEMUCS PHẢI KHỚP NHAU — ĐÃ SÓT MỘT CỬA:**
     `thay_giong_dialog._cap_nhat_nut_chay` (mở nút Chạy) ·
     `thay_giong.thay_giong_thu_muc` · **`jobs._thay_giong`**. Bản đầu sót cửa
     thứ ba -> UI mở nút, job được xếp, rồi **CHẾT NGAY tại chốt** với lời
     *"thiếu bộ tách giọng"*, tức tính năng chết đúng trên máy NHÂN VIÊN còn máy
     dev (có Demucs) xanh hết. Mục **5m** canh cửa đó.
     **LỜI NHẮN TIẾN ĐỘ PHẢI KHỚP KHOÁ, KHÔNG SỐNG NHỜ ĐƯỜNG LÙI — lỗi chính
     bản vá này đẻ ra:** câu *"Trộn giọng lồng lên tiếng gốc…"* KHÔNG chứa cụm
     khoá `"trộn tiếng"` mà `tg_so.buoc_tu_tien_trinh` tra, nên nó rơi vào đường
     LÙI (suy theo KHOẢNG) và chỉ ra đúng bước 9 **NHỜ MAY** (0,91 lọt khoảng
     cuối). Cách đo phân biệt: gọi với **`p=0.0`** -> câu cũ ra **bước 1**, câu
     có "trộn tiếng" ra **bước 9**. Nay câu là *"Trộn tiếng mới ĐÈ lên tiếng gốc
     (không tách nhạc)…"* — chứa `"trộn tiếng"` và **không** chứa `"tách giọng"`
     (khoá bước 2; viết "không tách giọng" là thanh tiến độ tụt về bước 2).
     Mục 5j/5k/5l canh cả lớp bệnh.
     **BẪY ĐÃ SẬP KHI DỰNG CỔNG (3 cái, ghi để đừng ai lặp):**
     · **giọng gốc LIÊN TỤC làm bộ dò TỰ ĐẠT OAN.** `_san_nhieu` lấy bách phân
       vị 20, nên nguồn không có >20% im lặng thì sàn rơi vào GIỮA tiếng nói ->
       `nguong_co = sàn + 12` không ai vượt -> **0 khoảng ở CẢ HAI arm**. Nguồn
       tổng hợp phải NGẮT NHỊP từng "từ" (0,35 s tiếng / 0,15 s nghỉ).
     · `anoisesrc` **bắt buộc có `s=` (seed)** — không thì mỗi lượt một mẻ ồn
       khác nhau và cổng nhấp nháy (cùng lý do `gradients` phải có seed).
     · mục 5i bản đầu dùng `re.findall(r'"(Trộn[^"]*)"')` và **bắt trúng chính
       DÒNG GHI CHÚ** ngay trên nó (khối chú thích trích nguyên văn câu CŨ để
       cảnh báo) -> HỎNG OAN. Nay đọc chuỗi từ THAM SỐ của `prog()` bằng **AST**
       (phủ cả `A if cond else B`). Bài học 47/51/53/54/73/80 **lặp lại lần thứ
       sáu, và lần này sập ngay trong mục viết ra để chống một bẫy khác.**
     **`bin\ffmpeg.exe` KHÔNG PHẢI ffmpeg APP CHẠY — số đo mới, quan trọng:**
     bản trong `bin/` sau lượt phục hồi từ `dist/` là build **2023-01-12**, còn
     `config.py:310` đặt `FFMPEG_PATH = _env("FFMPEG_PATH", "ffmpeg")` nên app
     lấy bản trên PATH = **N-121186 (2025-09-23)**. Build 2023 **KHÔNG CÓ chỉ số
     `Abs_Peak_count`** (`Unable to parse option value`, rc=1) nên mọi script ghi
     cứng `bin/ffmpeg.exe` đang đo một ffmpeg KHÁC ffmpeg sản xuất — **21 file
     `_test_*.py` đang ghi cứng nó**. Checklist phục hồi `bin/` chỉ kiểm 5
     filter, mà **CẢ HAI build đều có đủ 8/8** nên checklist ĐẠT trong khi build
     vẫn sai. `_do_de_giong.py` dùng `settings.FFMPEG_PATH` + có `kiem_ffmpeg()`
     TỰ KIỂM BỘ ĐO.
     **ĐÃ THAY `bin/` 19/08/2026 — nay là `N-126207-g21bbd98e7b-20260818`.**
     **NGUỒN ĐÚNG là `D:\BQHungVideo\_internal\` (app ĐÃ CÀI của anh Hùng), KHÔNG
     PHẢI `dist\BQHungVideo\_internal\`** — chỗ `dist/` chính là nơi chứa bản
     2023 và là lý do lượt phục hồi trước sai. `D:\BQHungVideo` **CHỈ ĐỌC**.
     Kiểm sau khi copy, đủ **4 phép** (checklist 5-filter cũ ĐẠT OAN nên đừng
     dùng lại): `ffmpeg -version` phải ra `N-126207` · 8 filter
     `acrossover · xfade_opencl · libplacebo · frei0r · rubberband · alimiter ·
     loudnorm · sidechaincompress` đều **1/1** · `ffmpeg -h filter=astats` phải
     có chuỗi `Abs_Peak_count` (đúng phép `kiem_ffmpeg()` dùng — đo được **4**
     lần xuất hiện) · và **CHẠY THẬT** `astats=measure_overall=Peak_level+
     Abs_Peak_count` phải ra **rc=0** kèm dòng `Abs Peak count:` (build 2023 ra
     rc=1 `Unable to parse option value`). **LƯU Ý TÊN IN RA KHÁC TÊN CHỈ SỐ:**
     tham số/metadata là `Abs_Peak_count` (gạch dưới) nhưng dòng in ra là
     `Abs Peak count:` (dấu cách) — grep sai dạng là kết luận oan "thiếu chỉ
     số" trên một ffmpeg CÓ ĐỦ. `bin/` **KHÔNG được git theo dõi**
     (`git ls-files bin/` rỗng) nên lượt thay này không có gì để commit — đừng
     đi tìm commit của nó.
     **CHƯA ĐẠT, GHI THẲNG:** chưa ai NGHE (file thử ở
     `_NGHE_THU_ANH_HUNG/de_giong/`, mỗi video một cặp `TACH_*` / `DE_*` cùng
     một lượt chạy — tai anh Hùng là phán quyết cuối) · mặc định vẫn là cách CŨ,
     **chờ anh Hùng duyệt** · thước tuyệt đối mới chạy trên **2/4** video
     (511,8 s) · chưa có số thời gian CẢ BƯỚC tách trong lượt này (`tach.giay`
     chỉ là `apply_model`; số cả bước lấy ở cổng 71: **0,155x GPU · 0,488x CPU**)
     · cột `trộn` đo LIỀN MẠCH nên chỉ đọc được là *"không chậm hơn"*.
- **"GẦN CUỐI VIDEO KHÔNG CHE MỜ CHỮ GÌ CẢ" — TRUY RA, VÁ, ĐO LẠI, CỔNG 56 CA 25
  (20/08/2026).** Anh Hùng: *"kiểm tra lại cái phần làm mờ sao cứ đến gần cuối
  video nó k che mờ chữ gì cả"*. Anh ấy nói **"cứ đến"** — tức CÓ QUY LUẬT, và
  quy luật đó là `1 − 1/k`.
  **NGUYÊN NHÂN ĐÍCH DANH: `thay_giong.thay_audio_video` nhánh CHE CHỮ dùng
  `-itsscale k` để làm chậm hình cho khớp giọng.** `-itsscale` là tuỳ chọn **ĐẦU
  VÀO** nên khung tới filter đã mang mốc `k*s`, còn hộp che thì `loc_cho_xuat`
  dò trên video **GỐC** (`segs=[(0, dur)]`) nên `a,b` trong
  `enable='between(t,a,b)'` là mốc **CHƯA GIÃN**. Hệ quả: lệch tuyến tính theo
  thời gian, và **mọi khung có `t` > độ_dài_GỐC rơi ra NGOÀI mọi mệnh đề enable
  = KHÔNG CHE GÌ**. Chú thích cũ ngay tại đó khẳng định *"`-itsscale` vẫn dùng
  được (nó đụng mốc ĐẦU VÀO, trước cả filter) nên hộp vẫn bám đúng chỗ chữ cũ"*
  — câu đó nghe hợp lý nên **chưa ai đo**, và nó SAI ở đúng chữ "trước cả
  filter".
  **BA NGHI PHẠM ĐỌC-MÃ ĐẦU TIÊN ĐỀU VÔ TỘI, đo rồi mới nói** (`_do_che_cuoi.py
  phu`): vòng lặp 8 giây của `do_hop_chu` **KHÔNG** bỏ đoạn lẻ cuối · `hop_theo
  _doan` phủ **100,0%** timeline đầu ra ở cả 7 độ dài clip (24 · 32 · 40 · 45 ·
  60 · 61 · 67 s — gồm cả độ dài KHÔNG chia hết cho 8) và cả hook-first ngược
  thời gian · `_DAI_NHO` không liên quan. Trên 4 video của anh Hùng, phần thiếu
  phủ ở đuôi trong thời gian NGUỒN chỉ **0,000-0,206 s**.
  **ĐO TRÊN CHÍNH 4 FILE APP ĐÃ XUẤT CHO ANH HÙNG** (`Downloads\longtieng\xuất`,
  `_do_che_thuc_te.py`) — không dựng lại kịch bản:

  | video | gốc -> xuất | k | đuôi KHÔNG che | mật độ nét còn |
  |---|---|---|---|---|
  | `#强烈推荐…` | 148,61 -> 178,14 s | 1,1987 | **16,6%** (29,5 s) | 99,2-136,8% |
  | `一款…倒忌时` | 363,21 -> 435,39 s | 1,1988 | **16,6%** (72,2 s) | 108,0-178,5% |
  | `从来没有…` | 301,19 -> 361,03 s | 1,1987 | **16,6%** (59,8 s) | 100,0-123,9% |
  | `八位好莱坞…` | 396,34 -> 495,40 s | 1,2499 | **20,0%** (99,1 s) | 99,4-102,2% |

  (`k` = 23,976/20 và 25/20 = **trần `SAN_NHIP_HINH_FPS`** — cả 4 video đều
  CHẠM TRẦN, nên lỗi này bật ở **mọi** video anh Hùng chạy chế độ khớp hình.)
  **HAI BẪY CỦA PHÉP ĐO, BẢN ĐẦU CỦA TÔI SẬP CẢ HAI — đọc trước khi đo lại:**
  (1) **lấy mốc theo độ dài BẢN GỐC** thì mốc 99% chỉ tới giây 147/178, tức **bỏ
  trắng đúng cái đuôi đang hỏng** và bảng ra "che một phần" khắp nơi, không thấy
  lỗi; phải lấy theo độ dài **BẢN XUẤT**. (2) **so "gốc tại T" với "xuất tại T"
  là so HAI CẢNH KHÁC NHAU** (xuất đã giãn `k` nên giây T của nó là nội dung
  giây `T/k` của gốc). Thước sạch: bản **ĐỐI CHỨNG chạy CÙNG `k` nhưng
  `che_chu=False`** -> `-c:v copy` -> khung giống TỪNG ĐIỂM ẢNH -> tỉ lệ
  `che/đối_chứng` tại CÙNG giây T.
  **BẢN VÁ (phiên song song làm, cách này ĐÚNG HƠN cách tôi định làm):** bỏ
  `*its` khỏi lệnh nhánh che chữ, đưa phép giãn vào CHUỖI FILTER bằng
  `setpts=PTS*k` đặt **SAU khối che và TRƯỚC `subtitles`** — trước `setpts` thì
  `t` là mốc NGUỒN (đúng trục hộp che dò được), sau `setpts` thì `t` là mốc ĐẦU
  RA (đúng trục `.ass` dựng từ `moc_tieng`). Đúng thứ tự `export_canvas_clip`
  vẫn dùng, và nhánh này VỐN ĐÃ mã hoá lại luồng hình nên `setpts` **không tốn
  thêm một đời nén nào**. Cách tôi định làm (nhân sẵn mốc hộp bằng tham số
  `he_so`) cũng chạy được nhưng **đã GỠ**: sau bản vá kia nó là **mã chết**, mà
  mã chết ở đây còn nguy hơn — ai nối vào là giãn **HAI LẦN**.
  **ĐO LẠI SAU VÁ, thước ĐỘC LẬP với thước của bản vá** (`_do_che_itsscale.py`,
  chữ Douyin THẬT, mảnh nguồn **45,003 s cố ý không chia hết cho 8**, 3 arm x 10
  mốc): `k=1,00` **10/10 đã che** (đối chứng CÓ RĂNG) · `k=1,20` 5 mốc cuối
  **98,8-101,2% -> 0,0-5,7%** · `k=1,25` **98,2-100,0% -> 0,0-5,0%**. Tổng
  **30/30 mốc còn 0,0-5,7%**. Cột đối chứng tự chứng minh phép đo đúng trục: `T
  = 0,10 x 45k` nên `s = T/k = 4,5` ở CẢ BA arm và mật độ đối chứng ra giống
  nhau từng chữ số (0,0933 / 0,1303 / 0,2117…).
  **NHÌN TẬN MẮT, CÙNG CẢNH CÙNG GIÂY** (`_do_che_anh.py`; TRƯỚC = chính file
  trong `xuất`, SAU = chạy lại bản đã vá với CÙNG `k=1,1987`): mật độ nét
  **0,1911 -> 0,0030** (mốc 86%) · **0,2147 -> 0,0052** (94%) · **0,1520 ->
  0,0060** (99%), độ dài lệch **-0,001 s**. Ảnh TRƯỚC mốc 94% **đọc rõ**
  `岸边已经没有什么物资了` nguyên vẹn kèm phụ đề tiếng Anh mới viết CHỒNG LÊN;
  ảnh SAU dải mờ kín, không đọc được chữ nào.
  **CHE OAN KHÔNG TĂNG MỘT CỬA SỔ NÀO** — bản vá không đụng một dòng nào của
  đường DÒ: CA 1 (nguồn sạch) · CA 3 (watermark đứng im) · CA 12 (`loc_che` trả
  rỗng) · **CA 24e (2 video thật KHÔNG chữ -> chuỗi filter RỖNG kể cả khi bật
  hộp)** đều ĐẠT trong lượt 132/0.
  **CỔNG 56 CA 25: ĐẠT 132 · HỎNG 0** (mốc `_chay_hoi_quy` 123 -> **132**).
  9 mục, nguồn **21 s cố ý không chia hết cho `HOP_DOAN`=8**. CA25d' là mệnh đề
  **KHÔNG khoá vào một cách vá nào**: cửa sổ `enable` cuối phải phủ tới KHUNG
  CUỐI, và trục của khung cuối **tự đổi** theo chỗ đặt phép giãn (`k*dur` nếu
  giãn TRƯỚC khối che, `dur` nếu SAU).
  **THỬ PHÁ 2 phép, BẮT 2/2 — và phép thứ hai LỌT ở lượt đầu, đó là chỗ đáng
  đọc nhất:** `insert(0, setpts)` thay cho `append` (đưa phép giãn lên TRƯỚC
  khối che = dựng lại đúng bản hỏng) -> CA25b ĐỎ, 3 mốc đuôi còn **100,8 / 99,8
  / 99,8%**. Nhưng phép "trả `-itsscale` vào lệnh nhánh che chữ" (giãn HAI LẦN)
  **LỌT**: `-shortest` **CẮT** bản xuất theo độ dài TIẾNG (`k*dur`) nên độ dài
  file vẫn ĐÚNG và **đoạn hỏng đã bị xoá khỏi file**, tức cổng xanh trong khi
  20% cuối THƯỚC PHIM biến mất. Cửa chặn đúng là **SỐ KHUNG** (525 -> ~420) ->
  thêm CA25e, phá lại thì BẮT. **Quy tắc chung: phép đo NỘI DUNG không bao giờ
  bắt được lỗi LÀM MẤT nội dung — phải có thêm một mục đếm khung/độ dài.**
  **BẪY NGUỒN TỰ SINH, sập 2 cái khi viết CA 25:** chữ NGẮN thì mật độ **0,0171**
  < ngưỡng 0,045 và cả ca tự tắt; và 7 dòng GẦN GIỐNG NHAU (`...thu 1...` ..
  `...thu 7...`, cùng bề rộng vì `x=(w-tw)/2`) bị **MẶT NẠ HẰNG** xoá sạch còn
  **0,0180** — đó là bộ dò làm ĐÚNG (chính cửa giữ kỉ lục che oan 0/76), lỗi ở
  nguồn thử. Độ dài **KHÔNG** phải nguyên nhân: cùng 4 dòng của CA 2 thì
  8/12/16/21 s đều dò ra (đậm gấp 17,2 / 16,6 / 17,6 / 17,3 lần nền).
  **CÒN NỢ, GHI THẲNG:** arm dùng `setpts` ra **1078 khung** so với **1079** của
  arm `-itsscale` (lệch ĐÚNG 1 khung = 41 ms, do đổi cơ chế giãn + `-shortest`)
  — chưa truy · **3 file cũ trong `Downloads\longtieng\xuất` vẫn là bản HỎNG**,
  anh Hùng phải xuất lại mới hết chữ Trung ở đuôi · chưa ai xem bằng mắt trên
  máy nhân viên · đường xuất CLIP (`export_canvas_clip`) **KHÔNG** dính lỗi này
  (`setpts=PTS/vspeed` vốn đã đặt sau khối che) nhưng cũng chưa có ca canh riêng
  cho `dub_stretch`.
- **GIỌNG CỦA ANH HÙNG (NHÂN BẢN TỪ MẪU) ĐÃ NỐI VÀO UI — CỔNG 88 (20/08/2026).**
  Anh Hùng: *"ném giọng đọc của tôi khoảng mấy giây Reference Audio, sau đó dán
  bao nhiêu ký tự dùng giọng đó cũng được... không lấy của bất kỳ ai nữa, tự
  động lấy của mình luôn"*.
  **CA THỨ NĂM CỦA "HÀM XONG ≠ TÍNH NĂNG XONG"** sau `giong_bang` ·
  `giong_chatter` · `giong_vbee` · `giong_kokoro`: `app/core/nhan_ban_giong.py`
  dựng xong **564 dòng** (kiểm mẫu · sổ ra đĩa · chép mẫu vào `DATA_DIR` ·
  xoá/đổi tên) **và cổng 81 đã chấm nó XANH 57/0** — nhưng
  `grep -rn "nhan_ban_giong" app/ui/` ra **0 dòng**. Cổng 81 canh HÀM, không
  canh CÁI ANH HÙNG BẤM.
  **KHÔNG ĐẺ TIỀN TỐ `toi:` — ĐO ĐƯỢC, KHÔNG PHẢI SỞ THÍCH.** Mô tả việc gợi ý
  một tiền tố mới; đo ra thì đó là bẫy: `giong_bang.nguon("toi:abc")` trả
  **`'edge'`**, tức tiền tố chưa đăng ký bị coi là edge-tts -> đúng bẫy "chọn X
  ra Y" mà `ov:nu_am`/`vn:`/`cb:`/`kk:` đã sập BỐN lần. Mã giọng giữ **tiền tố
  NGUYÊN BẢN của máy** `vnb:`, thứ đã đăng ký đủ ở `giong_bang._TIEN_TO` (đứng
  TRƯỚC `vn:` vì dài hơn) và **CẢ HAI** cửa `dubbing._synth_all` +
  `_synth_all_words` (kiểm bằng AST **và** GỌI THẬT: cả hai cửa rẽ vào
  `giong_vieneu.doc_loat` với đúng `vnb:`). Cổng 81 CA 7h canh quyết định đó,
  cổng 88 CA 2c' canh mặt còn lại.
  **3 LỖ CỦA SỔ GIỌNG, cả ba "app vẫn chạy, không một dòng báo":**
  (a) **MẤT SẠCH SỔ.** `_doc_so` cố ý trả `{}` khi parse hỏng và không tự ghi
  đè — nhưng chốt đó chặn NỬA đường: lượt ghi kế tiếp lấy `{}` rồi `_ghi_so`
  **thay NGUYÊN FILE**. Nay `_sao_luu_neu_hong` chép ra
  `giong_nhan_ban.hong-<ngày>.json` + ghi log. (b) **MỘT MỤC HỎNG GIẾT CẢ
  COMBO**: `_doc_so` chỉ bảo đảm dict NGOÀI CÙNG, mục lạ (chuỗi/None) làm
  `g.get()` ném `AttributeError` trong `danh_sach()`, và `giay: "4,5"` (dấu
  phẩy tiếng Việt) làm `float()` ném trong `nhan()` — nay `_muc()` + `_so_giay()`.
  (c) **`Path("").exists()` LÀ `True`** nên `sua_mau_mat` coi mục THIẾU khoá
  `mau` là "mẫu còn nguyên" = báo cáo NGƯỢC sự thật; nay hỏi chuỗi RỖNG trước.
  `xoa()` nay đi qua `xoa_an_toan.an_toan_de_xoa` (cửa thứ 6 của lớp bệnh đã
  xoá sạch cây mã 19/08) — đo: xoá mục `mau` rỗng -> TỪ CHỐI, mồi canary còn.
  **SỐ ĐO (`_do_giong_toi.py` -> `_kq_giong_toi.json`; mẫu là edge-tts
  `vi-VN-*` = GIỌNG GIẢ LẬP, sạch giấy phép, và là mẫu SẠCH TUYỆT ĐỐI nên mọi
  số dưới đây là **TRẦN TRÊN** — mẫu điện thoại sẽ tệ hơn, `giong_vieneu` đã
  đo 7,7% vs 21-31%):**

  | | MẪU A (nữ) | MẪU B (nam) | CLONE_A | CLONE_B | VN_PRESET (không clone) |
  |---|---|---|---|---|---|
  | F0 trung vị (nửa cung) | 14,31 | 6,86 | **13,63** | **5,38** | 13,52 |
  | \|Δ vs MẪU A\| | — | 7,45 | **0,69** | 8,93 | 0,79 |
  | \|Δ vs MẪU B\| | 7,45 | — | 6,77 | **1,48** | 6,66 |
  | **nhấn nhá** | 3,10 | 4,01 | **3,15** | **3,73** | 3,18 |
  | phủ mốc | — | — | **100,0%** | **100,0%** | 100,0% |
  | rung mốc chữ đầu | — | — | **18,5 ms** | **17,8 ms** | 11,0 ms |
  | giây / 4 câu | 1,2 | 1,8 | 32,4 | 31,5 | 18,5 |
  | RAM đỉnh | 62 MB | — | **3.045 MB** | 3.004 MB | 3.009 MB |

  **NHÂN BẢN CHẠY THẬT — nhưng MỘT MẪU THÔI thì KHÔNG chứng minh được, và đây
  là phần đáng đọc nhất.** `VN_PRESET` cách MẪU A đúng **0,79** nửa cung, gần
  y hệt `CLONE_A` (**0,69**) — tức nếu chỉ thử với mẫu A thì bảng số **không
  phân biệt được nhân bản với không nhân bản**, đúng loại DƯƠNG TÍNH GIẢ mà
  bẫy `use_ref_codes` lượt 4 đã sập. Bằng chứng thật nằm ở **ĐỘ TRẢI**: hai bản
  sao đứng ở **13,63 và 5,38** = trải **8,25 nửa cung** theo đúng mẫu của
  chúng, trong khi giọng dựng sẵn **không thể xê dịch** (13,52 cố định, cách
  `CLONE_B` **8,14** nửa cung). **Quy tắc: phép đo nhân bản phải có ÍT NHẤT
  HAI mẫu cách nhau xa, và mẫu thứ hai phải xa cao độ mặc định của model.**
  **NHẤN NHÁ — SỐ NÓI NGƯỢC KỲ VỌNG MỘT PHẦN, ghi đúng số:** mô tả việc đoán
  *"giọng clone mang ngữ điệu của mẫu nên khả năng cao là HƠN"*. Đo ra:
  `CLONE_A` **3,15** vs `VN_PRESET` **3,18** = **BẰNG NHAU** (−0,03, nằm TRONG
  nhiễu — xem dưới); chỉ `CLONE_B` **3,73** mới hơn thật (+0,55). Nhìn theo
  chiều khác thì rõ hơn: bản sao **thừa hưởng ngữ điệu của MẪU, hơi bị nén
  lại** (A 3,10 -> 3,15 = +0,05 · B 4,01 -> 3,73 = **−0,28**). Tức **nhấn nhá
  của giọng nhân bản = nhấn nhá của mẫu anh Hùng đưa vào**, không phải một mức
  cố định — đưa mẫu đọc trơ thì ra giọng trơ. So mốc: cả hai bản sao **hơn
  Kokoro `af_bella` 2,33 rất xa**, `CLONE_B` hơn cả Piper 3,24 và HoaiMy 3,40.
  **ĐỐI CHỨNG TÁI LẬP LÀ CHỖ PHẢI ĐỌC TRƯỚC KHI TIN 4 SỐ TRÊN:** arm edge chạy
  CÙNG LƯỢT ra `EDGE_B` **4,01** vs mốc **3,96** (lệch 0,05 — tái lập tốt)
  nhưng `EDGE_A` **3,10** vs mốc **3,40** (lệch **0,30**). Bộ câu ở đây chỉ
  **4 câu** (`_do_nhan_nha_bang.CAU["vi"]`) nên **0,30 chính là sàn nhiễu của
  phép đo này** -> chênh 0,03 giữa `CLONE_A` và `VN_PRESET` **không đọc được**,
  còn +0,55 của `CLONE_B` thì đọc được.
  **MỐC TỪNG CHỮ TỐT HƠN HẲN MỐC ĐANG GHI, nhưng mẫu NHỎ:** VieNeu không tự
  trả mốc nên phải qua `giong_hang`; đo được **phủ 100,0% · rung 17,8-18,5 ms**
  so với mốc đang ghi cho gióng hàng (**98,5-98,6% · 90-119 ms**) và gần
  edge-tts tự trả (**15,7 ms**). Ba lý do tin được: `VN_PRESET` ra **11,0 ms**,
  khớp con số **8,5 ms** `giong_vieneu` đã ghi; lệch hệ thống của arm clone chỉ
  **+1,9/+3,0 ms**; mốc 90-119 ms đo trên tiếng **OmniVoice** (chất lượng thấp
  hơn). **NHƯNG chỉ 4 câu/arm** — chưa đủ để thay mốc cũ, đừng chép số này vào
  nhãn.
  **ĐỌC DÀI 44 CÂU: KHÔNG CỤT CHỮ, KHÔNG TRÔI GIỌNG.** 44/44 câu đọc được ·
  **135 từ vào -> 135 từ ra = 100,0%** (9/9 câu đủ) · F0 độ lệch chuẩn giữa 44
  câu chỉ **0,53** nửa cung, lệch giữa các PHẦN TƯ lớn nhất **0,48** -> **bệnh
  "chia đoạn xong ghép lại thì giọng đổi" của CosyVoice VẮNG MẶT**. Thời gian
  **180,4 s cho 165,4 s tiếng = 1,090x** (chậm hơn thời gian thật), RAM đỉnh
  **3.078 MB**, VRAM **2.434 MiB** (POLL trong lúc chạy — lấy mẫu 2 đầu là ra
  mức nền, bẫy cổng 71/73). **Trần ký tự: `max_chars = 256` mỗi lượt `infer`,
  và GÓI tự chia chunk** (`normalize_to_chunks_v3_with_gaps`) — app KHÔNG tự
  chia, câu 65 ký tự là MỘT chunk. **GIÁ CỦA NHÂN BẢN so với giọng dựng sẵn:
  +13,9 giây cho cùng 4 câu** (32,4 vs 18,5) vì đường `ref_audio` mới đụng
  torch; lượt đọc ĐẦU của tiến trình mất **~38 giây** (phần lớn là nạp model)
  nên nút Nghe thử phải khoá lại và nói "Đang đọc...".
  **UI:** nút **"Giọng của tôi..."** ngay cạnh ô Giọng đọc -> hộp `HopGiongToi`
  (cảnh báo PHÁP LÝ ngay chỗ chọn file · chọn WAV/MP3/video · đặt tên · **2 nút
  nghe thử CỐ Ý KHÁC NHAU**: "Nghe thử mẫu" phát thẳng file mẫu, tức thời;
  "Nghe thử giọng" chạy nhân bản THẬT qua `thay_giong.doc_thu` = đúng cửa lượt
  xuất đi, **KHÔNG** gọi thẳng `_synth_all_words` để cổng 63 vẫn 24/0 · đổi tên
  · xoá). Nhãn dài nhất **96 ký tự** (Kokoro 139-178 đã đẩy mất cảnh báo "cần
  tải") và vào đúng nhóm **TRÊN MÁY**. Đổi tên **KHÔNG đổi mã giọng** nên kênh
  đang gán vẫn đúng. Hộp bắn `so_doi` -> cha dựng lại combo với
  **`giu_dang_chon=True`** (đọc từ WIDGET, không từ QSettings: user vừa lưu mà
  chưa bấm Chạy nên setting còn là giọng CŨ — đúng lỗi thật cổng 55).
  **CỔNG 88 `_test_giong_toi.py`: ĐẠT 66 · HỎNG 0.** Thử phá
  `_pha_giong_toi.py` (9 phép, mỗi phép gỡ ĐÚNG 1 chốt): **BẮT 9 · LỌT 0 ·
  KHÔNG PHÁ ĐƯỢC 0**. Lượt phá ĐẦU ra **BẮT 8 · LỌT 1** và cái LỌT là **lỗi
  của CỔNG**: mục 10c dùng `ast.unparse` rồi tìm chuỗi, mà **`unparse` GIỮ
  DOCSTRING** — docstring của `_mo_giong_toi` cố ý trích chính cụm
  `giu_dang_chon=True` để giải thích chốt, nên gỡ sạch tham số khỏi lời gọi mà
  cổng vẫn XANH. **Bài học cổng 73 lỗi (b) lặp lại**; nay đi tìm NÚT
  `ast.keyword` thật + có mục TỰ KIỂM BỘ DÒ.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa ai NGHE bằng tai** một giọng nhân bản nào —
  mọi số trên là số ĐO, và thước độ giống là **F0 (cao độ)** nên nó trả lời
  được *"bản sao có đi theo mẫu không"* mà **KHÔNG** trả lời được *"nó có
  GIỐNG NGƯỜI ĐÓ không"* (hai người khác nhau vẫn có thể cùng cao độ). Muốn
  câu đó phải dùng **ECAPA-TDNN** như `_do_nhan_ban.py` — `speechbrain` KHÔNG
  có trong `_lib_giong` lẫn `.venv` nên đường đó chưa chạy được lượt này ·
  mẫu là **GIẢ LẬP** (edge-tts), chưa đo trên giọng thật của anh Hùng, và mẫu
  sạch tuyệt đối là ca DỄ NHẤT · nhấn nhá đo trên **4 câu** nên sàn nhiễu 0,30
  · mốc từng chữ cũng chỉ 4 câu/arm · bộ đếm cụt chữ lượt này **lùi về
  faster-whisper-small TRÊN MÁY** (không phải Groq — có dòng tải model HF
  trong log), 9/9 câu khớp đúng nên vẫn tin được nhưng đó là thước KHÁC ·
  `Chatterbox` (`cb:`, 23 tiếng khác) đã có trong `nhan_ban_giong` nhưng hộp
  này **chỉ mở đường tiếng Việt** (`lang="vi"` -> VieNeu) · chưa nối vào
  **giọng RIÊNG THEO KÊNH** (`giong_kenh`) nên chưa gán được giọng nhân bản
  cho từng kênh trong 200-300 kênh · bản `.exe` KHÔNG gói VieNeu nên máy nhân
  viên phải bấm nút tải + phải có Python 3, và đường nhân bản còn cần
  **torch + torchaudio** (nhãn nói đích danh khi thiếu).
- **NÚT TẢI PHẦN NHÂN BẢN GIỌNG — `cai_nhan_ban()` (20/08/2026).** Anh Hùng
  thêm giọng nhân bản của mình ("MQ Idol", mẫu 7 giây), **lưu thành công**, rồi
  dòng giọng ghi *"CHƯA CHẠY ĐƯỢC (thiếu torch, torchaudio)"*. **Nhãn đó NÓI
  THẬT** — nhưng **KHÔNG CÓ NÚT NÀO để cài**. Tính năng thật thà báo hỏng rồi
  bỏ người dùng ở đó; đó là cái được vá.
  **HAI THƯ MỤC, HAI SỰ THẬT KHÁC NHAU** (`thu_muc_vieneu()` đọc
  `config.DATA_DIR` MỖI LẦN GỌI, không cất hằng số): chạy **nguồn** ->
  `<repo>/_giong_vieneu/venv` **CÓ** cả `torch 2.13.0+cpu` lẫn
  `torchaudio 2.11.0+cpu` nên `thieu_de_nhan_ban()` trả `[]`; bản **`.exe`** ->
  `%LOCALAPPDATA%\BQHungVideo\_giong_vieneu\venv`, **KHÔNG có torch**. 20 giọng
  dựng sẵn vẫn chạy vì chúng đi bằng `onnxruntime`; **chỉ đường NHÂN BẢN đụng
  torch**.
  **HÀM NẰM Ở `giong_vieneu`, KHÔNG Ở `nhan_ban_giong`** — cả 4 hàm cài đã có
  đều ở module SỞ HỮU môi trường đích (`cai_demucs`->`_lib` ·
  `cai_piper`->`_piper` · `cai_kokoro`/`cai_omnivoice`->venv riêng); ở đây đích
  là `_giong_vieneu/venv` do chính file đó sở hữu, còn `nhan_ban_giong` là tầng
  ĐIỀU PHỐI (VieNeu vs Chatterbox). Danh sách gói KHÔNG chép lại — đọc
  `nhan_ban_giong._CAN_CHO_NHAN_BAN`, hai bản sao là hai chỗ để quên.
  **DUNG LƯỢNG LÀ SỐ ĐO** (`_do_nhan_ban_tai.py`: `pip install --dry-run
  --report` bằng CHÍNH python 3.12.10 của venv VieNeu, rồi **HTTP HEAD** trên
  đúng wheel pip chọn; lệnh dry-run dựng GIỐNG HỆT lệnh sẽ cài):
  **cpu 11 gói = 126,3 MB** (torch 116,3 · torchaudio 0,3) vs
  **cu126 11 gói = 2.485,6 MB** (torch 2.474,4 · torchaudio 1,4) = chênh
  **19,7 lần**. `co_gpu_nvidia()` (hỏi `nvidia-smi`, **KHÔNG import torch** —
  torch sau Qt là ACCESS VIOLATION) quyết chỉ mục; `BQ_NB_CPU=1` ép bản nhỏ.
  Máy anh Hùng có RTX 3060 nên mặc định đi CUDA, và nhãn nói thẳng **"CHƯA ĐO
  có nhanh hơn"** — Demucs có số 9,28x để hứa, đường nhân bản của VieNeu thì
  **chưa ai đo GPU**.
  **NÚT BÁM `thieu`, KHÔNG BÁM CỜ "CHẠY ĐƯỢC"** — đây là chính cái bẫy đẻ ra
  việc này, và nó đã sập hai lần (cổng 58 `_lib`, rồi hàng Kokoro): bám cờ thì
  trên máy dev (venv ĐÃ có torch) nút **BIẾN MẤT**, không ai bấm, bản `.exe`
  mãi mãi thiếu. Ca **CÀI DỞ** đổi nhãn thành `Cài tiếp phần còn thiếu (...)`,
  và nó **vẫn ghi đủ số MB** vì `--ignore-installed` làm pip tải lại TOÀN BỘ
  danh sách chứ không chỉ cái thiếu. Thiếu Python 3 -> **khoá nút VÀ in lý do**.
  Bộ dò NÉM -> hộp không chết và **nghiêng về HIỆN nút** (ẩn nút là cách tính
  năng đã chết một lần). **CỐ Ý KHÔNG gọi `_dung_combo_giong()`** sau khi tải
  (hàm đó đọc giá trị ĐÃ LƯU nên nuốt lựa chọn user vừa bấm — họ lỗi "chọn X ra
  Y"), chỉ `_nap()` cho tiền tố "CHƯA CHẠY ĐƯỢC" biến đi.
  **ĐÃ CHẠY THẬT** (`_do_cai_nhan_ban.py`, bản CPU, hộp cát riêng — **KHÔNG**
  đụng `_giong_vieneu/venv` đang dùng được): `ok=True` · **69,5s** rồi
  **62,8s** (lượt 2 nhanh hơn nhờ cache wheel) · `thieu` sau = **[]** · venv
  **11,5 -> 603,7 MB = +592,2 MB** bung ra đĩa cho 126,3 MB tải về · `torch
  2.13.0+cpu` + `torchaudio` nằm THẬT trong site-packages hộp cát (đọc file
  trực tiếp, KHÔNG hỏi "import được không"). Mẹo hộp cát rẻ: `_python_vieneu`
  dò bằng **FILE CÓ TỒN TẠI KHÔNG** nên chỉ cần đặt mấy file RỖNG đúng tên là
  `tinh_trang_vieneu()['co']` -> True, không phải chép cả môi trường mấy GB.
  **LỖI LƯỢT CHẠY THẬT BẮT ĐƯỢC — `.replace(",", ".")` TRÊN CẢ CÂU:** dòng tiến
  độ in ra *"(khoảng 126 MB. tải 1 lần)"*, dấu phẩy tiếng Việt thành dấu chấm.
  `giong_kokoro.dau_chua_tai` **đã ghi đúng bài học này** ("một lần, dùng chung"
  -> "một lần. dùng chung") mà tôi vẫn lặp. Nay có `giong_vieneu.so_mb()` đổi
  dấu nghìn **RIÊNG CON SỐ**, và nhãn/tooltip/hộp xác nhận đều gọi nó (một phép
  đo, ba chỗ đọc — cổng 58: nút 155 MB, hộp doạ 2 GB).
  **CÒN LỖI CŨ Ở CHỖ KHÁC, CHƯA VÁ:** `giong_kokoro.py` dòng **817** và **850**
  vẫn `.replace(",", ".")` trên cả câu (cùng file có chỗ 989 làm ĐÚNG kèm ghi
  chú) — việc RIÊNG, không gộp vào lượt này.
  **CỔNG 88 `_test_giong_toi.py`: 66 -> ĐẠT 104 · HỎNG 0** (CA 12, 38 mục mới).
  Thử phá `_pha_giong_toi.py`: 9 -> **20 phép · BẮT 20 · LỌT 0 · KHÔNG PHÁ ĐƯỢC
  0**. **Mệnh đề trung tâm (khuôn CA 1a cổng 58)** có RĂNG nhờ **MỒI CHIA ĐÔI**:
  máy này venv VieNeu đã đủ nên phép so ra `[] == []` (đúng mà vô nghĩa), nên
  cổng vá `_CAN_CHO_NHAN_BAN` thành **`PyQt6`** — gói CÓ trong `.venv`, THIẾU ở
  venv VieNeu, đúng phép chia đôi cổng 58 — rồi đòi bản chạy-nguồn và tiến trình
  KHÔNG có `.venv` nói **GIỐNG HỆT `['PyQt6']`**; bộ dò kiểu `find_spec` sẽ lệch
  ngay đây.
  **BA LỖI CỦA CHÍNH CỔNG, tôi tự mắc rồi tự bắt — đọc kẻo lặp:** (a) mục 12e
  hỏi `"sys.executable" not in _ma_that(...)`, mà `_ma_that` **nối TOKEN bằng
  dấu cách** nên chuỗi đó thành `"sys . executable"` -> mục **TỰ ĐẠT VĨNH VIỄN**;
  nay quét `ast.Attribute`. (b) mục 12d bỏ docstring bằng cách so mặt chữ
  (`startswith("TẢI + CÀI")`) — sửa một chữ trong docstring là phép bỏ trượt,
  docstring (có chứa `--ignore-installed`) lọt vào rồi mục ĐẠT OAN dù cờ đã bị
  gỡ khỏi LỆNH; nay bỏ theo **cấu trúc AST** + có mục 12d0 tự kiểm. (c) mục
  12l''' bản đầu hỏi *"nhãn/tooltip/hộp còn dấu phẩy không"* -> **4 mục ĐỎ OAN**,
  vì với `thieu=['torch']` thì `', '.join` chỉ có MỘT phần tử nên câu không có
  dấu phẩy nào một cách **hoàn toàn chính đáng**; cái cần canh là **bất biến cấu
  trúc** (chỉ `so_mb` được gọi `.replace(",", ".")`).
  Kèm: `_don_hop_cat` của cổng 88 nay đăng ký bằng **`atexit`** — lượt thử phá
  có phép làm cổng chết GIỮA ĐƯỜNG nên dòng gọi thẳng ở cuối file không chạy, đo
  được **2 thư mục `bq_test_giong_toi_*`** đọng lại trong repo.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa tải thật bản CUDA** (2.485,6 MB — chỉ đo bằng
  `--dry-run` + HTTP HEAD, và đó CHÍNH là đường mặc định trên máy có GPU của anh
  Hùng) · chưa ai **NGHE** một giọng nhân bản sau khi cài bằng nút này · chưa đo
  **GPU có nhanh hơn CPU** cho đường nhân bản VieNeu (nhãn nói đúng là chưa đo) ·
  `cai_vieneu()` vẫn **KHÔNG có nút nào trong UI** (ca thứ NĂM của "hàm xong ≠
  tính năng xong", `grep cai_vieneu app/ui/` -> 0 dòng) nên máy chưa có VieNeu
  thì nút này chỉ ghi *"Chưa có bộ giọng VieNeu — tải bộ đó trước"* mà **không
  có chỗ để bấm**.
- **NHÂN BẢN GIỌNG: CHUỖI ĐÃ NỐI XONG + BẮT ĐƯỢC MỘT BÁO ĐỘNG GIẢ ĐẮT
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
  từ lời lỗi chỉ nhận `[A-Za-z0-9_\-]+` — lời lỗi là chuỗi từ **tiến trình
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
  **VIỆC 4 — `%TEMP%`: CHỌN KHÔNG TỰ DỜI, NÓI THẲNG.** Máy này `%TEMP%\
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
  `%TEMP%\bq_giong8` (4,95 GB) đi đâu cả.
- **GIỌNG KOKORO ĐÃ NỐI VÀO UI + ĐO CẢ 28 GIỌNG (v2.41.0, 20/08/2026).**
  `app/core/giong_kokoro.py` viết xong đủ hàm đọc + hàm cài từ trước mà **UI
  không gọi tới một dòng nào** — đo trước khi vá: `grep -c "kk:"
  thay_giong_dialog.py` -> **0**. Ca thứ TƯ của cùng một bệnh sau `giong_bang`,
  `giong_chatter`, `giong_vbee`: hàm xong ≠ tính năng tồn tại.
  **28/28 GIỌNG KÊU, 0 CÂM** (`_do_28_giong_kk.py` -> `_kq_kk28.json`, đọc THẬT
  một câu tiếng Anh rồi đọc mẫu WAV THẲNG chứ không tin `doc_loat` tự chấm —
  `_kiem_wav` chỉ hỏi "có tiếng không"): dài **3,00-4,75 s** · RMS **0,02967
  (af_nova, thấp nhất) - 0,08133 (af_aoede)** = trải 2,7 lần, tất cả trên sàn
  `RMS_TOI_THIEU` 0,002 rất xa. Trước lượt này chỉ `kk:af_bella` từng được đọc
  thử, tức 27 giọng trong combo chưa ai biết có kêu hay không.
  **GỌI GỘP RẺ HƠN GỌI LẺ 5,35 LẦN — VÀ APP ĐANG GỌI ĐÚNG, ĐỪNG AI "DỌN GỌN"
  THÀNH VÒNG LẶP TỪNG CÂU.** Đo 12 câu, 2 vòng ĐAN XEN có xoay thứ tự, lấy lượt
  nhanh nhất mỗi bên (`_do_kk_gom.py`): **lẻ 90,44 s (7,54 s/câu) · gộp 16,91 s
  (1,41 s/câu)**, cả hai ra đủ 12/12 WAV. Suy ra video 45 câu: **~339 s so với
  ~63 s**. Lượt gọi ĐẦU TIÊN của tiến trình mất **60,5 s** (nạp model) so với
  9,2-9,6 s các lượt sau — cùng bệnh Piper "lượt nào cũng nạp lại model ~2,2 s"
  nhưng **đắt hơn 27 lần**. Đã kiểm bằng AST: `dubbing._synth_all` VÀ
  `_synth_all_words` đều truyền `texts` (CẢ LOẠT) vào `_chay_kokoro`, không phải
  `texts[i]` — kiến trúc đang đúng.
  **NÚT TẢI BÁM `thieu`, KHÔNG BÁM `co`** (bài học cổng 58, và đây là chỗ cả
  tính năng có thể chết âm thầm): bám `co` thì trên máy dev nút BIẾN MẤT, không
  ai bấm, bản `.exe` mãi mãi thiếu. Đo bằng cách vá `tinh_trang` trả
  `co=True, thieu=['torch']` -> nút **CÒN HIỆN**. Thiếu Kokoro chỉ LÙI ÊM về
  edge-tts nên hàng này **KHÔNG khoá nút Chạy** (khác Demucs: thiếu là CHẶN, vì
  lùi ra video HỎNG). Không có Python 3 -> khoá nút VÀ nói vì sao. Mừng theo
  `thieu` chứ không theo mã thoát của pip.
  **CỐ Ý KHÔNG dựng lại combo sau khi tải xong** — bản đầu của tôi CÓ gọi
  `_dung_combo_giong()` cho nhãn 28 dòng thôi khoe "CHƯA TẢI", và đó là SAI: hàm
  đó đặt lại combo theo giá trị ĐÃ LƯU nên nuốt mất lựa chọn user vừa bấm mà
  chưa lưu = đúng họ lỗi "chọn X ra Y". `_tai_gh_xong` đã ghi rõ vì sao nó không
  làm; tôi đọc sau khi viết. Nhãn tự đúng ở lần mở hộp sau.
  Tiến độ đi qua dict RIÊNG `_buoc_kokoro` + nhánh trong `_nhip` (khuôn hàng
  Demucs) — **không đụng widget từ thread nền**, và không dùng chung `_buoc_cai`
  vì hai lượt tải song song thì hai tiến trình pip ghi lẫn số của nhau.
  **CHƯA ĐẠT, GHI THẲNG:** chưa có cổng riêng cho Kokoro trong
  `_chay_hoi_quy.py` (số cổng phải lấy bằng cách đọc `_chay_hoi_quy.CONG`, đừng
  đếm theo trí nhớ — bài học 70 vs 69) · **chưa ai NGHE bằng tai** một giọng nào
  trong 28 giọng, mọi số trên là số ĐO · chưa đo mốc từng chữ (Kokoro không tự
  trả mốc, phải nhờ `giong_hang`) · `_giong_kokoro/` bị gitignore nên bản `.exe`
  KHÔNG mang sẵn bộ này, máy nhân viên phải bấm nút + phải có Python 3.
- **NHẤN NHÁ 28 GIỌNG KOKORO: ĐO XONG (20/08/2026, `_do_nhan_nha_kk.py` ->
  `_kq_nhan_nha_kk.json`).** Anh Hùng nghe rồi báo: *"phần giọng đọc koro tôi
  thấy được mà k có nhấn nhá cảm xúc gì"*. Trước lượt này `nhan_nha.BANG` không
  có **một mã `kk:` nào** và `giong_doc.BANG` cũng chưa biết `kk:`, nên
  `nhan_nha.nhan("kk:af_bella")` trả **chuỗi RỖNG** — dòng combo không nói một
  chữ nào về nhấn nhá. (Chữ *"chưa đo tiếng"* trên dòng Kokoro là của
  `da_ngu.nhan_gon`, nó nói *"chưa đo giọng này ĐỌC ĐƯỢC TIẾNG GÌ"* — **một
  phép đo KHÁC**, đừng đọc thành "chưa đo nhấn nhá".)
  Đúng thước cũ (`_do_nhan_nha.f0_nua_cung` + `pstdev`), đúng bộ câu
  `_do_nhan_nha_bang.CAU["en"]` mà mọi giọng `en-*` của bảng 211 đã đọc (Kokoro
  **không có tiếng Việt** — 28/28 là `af_/am_/bf_/bm_` = Mỹ/Anh — nên lấy
  `vi-VN-HoaiMy` làm mốc là dựng lại phép **so chéo tiếng** mà `nhan_nha` cấm).
  **ĐỐI CHỨNG CHẠY CÙNG LƯỢT TÁI LẬP ĐƯỢC BẢNG CŨ** nên cột này so được:
  `en-US-Aria` 3,33 -> **3,33** · `en-US-Andrew` 4,49 -> **4,45** ·
  `en-GB-Ryan` 5,38 -> **5,38**, lệch tối đa **0,04** (dải nhiễu đã đo
  0,00-0,12). Không có 3 dòng này thì 28 số kia vô nghĩa.
  **28/28 đo được · trải 2,24-5,66 · TB 3,75 · trung vị 3,92.**
  **LỜI ANH HÙNG ĐÚNG Ở GIỌNG ANH ẤY BẤM, SAI Ở CẢ BỘ — và phải nói cả hai
  nửa:** *"Kokoro không có nhấn nhá"* nói về CẢ BỘ là **SAI theo số đo** —
  **20/28 giọng ĐẠT HOẶC HƠN `en-US-Aria` (3,33)**, TB hơn Aria **+0,42**, và
  `am_santa` **5,66** hơn **CẢ `en-GB-Ryan` 5,38** = giọng tiếng Anh cao nhất
  của bảng 211. Nhưng nó **ĐÚNG ở đúng giọng người ta bấm**: `af_bella` — tác
  giả chấm **A-** và ghi thẳng *"giọng tốt nhất cả bộ"* — đo ra **2,33**, tức
  **thấp thứ 2 trong 28**, kém Aria **1,00** nửa cung; cùng chùm đáy có
  `bf_isabella` **2,24** (C) và `bf_emma` **2,36** (B-).
  **PHÁT HIỆN ĐÁNG NÓI NHẤT — ĐIỂM TÁC GIẢ KHÔNG DỰ ĐOÁN ĐƯỢC NHẤN NHÁ:**
  Spearman **0,12**. 5 giọng nhấn nhá CAO nhất bị chấm **D- · D+ · D · D · B-**
  (`am_santa` 5,66 · `bm_lewis` 4,67 · `am_liam` 4,60 · `af_jessica` 4,48 ·
  `af_nicole` 4,44); 5 giọng THẤP nhất có cả **A-** và **B-**. Tức chọn giọng
  theo ĐIỂM (hoặc theo thứ tự dòng — `gom_nhom` đang xếp `kk:` theo **thứ tự
  chữ cái** vì mọi mã cùng tắc ở `khoa_sap`) hoàn toàn có thể trúng giọng phẳng
  nhất bộ, và đó đúng là chuyện đã xảy ra. **Hai con số không thay được nhau.**
  **SỐ NẰM Ở `giong_kokoro.NHAN_NHA`, CỐ Ý KHÔNG VÀO `nhan_nha.BANG`** — lý do
  ĐO ĐƯỢC, không phải cho gọn: `gom_nhom` sắp trong nhóm bằng `khoa_sap` nên
  vào `BANG` là `af_bella` tụt gần đáy 28 dòng còn `am_santa` (D-) /`bm_lewis`
  (D+) trèo lên **hai dòng đầu** — đúng lỗi `vn:Xuân Vĩnh` đã sập. Thêm 28 giọng
  vào 211 còn **dịch tứ phân vị** -> đổi nhãn giọng CŨ -> một lượt việc RIÊNG
  qua 4 cổng (76 CA 3a · 79 CA 10 · 81 CA 1c/1d · 83 mục 3f kèm `SO_DOI_NHAN`).
  **THƯỚC vẫn chỉ có MỘT** — đó là thứ không được nhân bản. Đã kiểm một lo ngại
  và nó KHÔNG có thật: `chon_khuyen` chặn bằng `muc() is None`, nhưng `kk:` còn
  trượt **hai** chốt khác (`_dung_duoc_ngay` False · `ma_ngon_ngu` rỗng) nên nó
  không vào nhóm "Khuyên dùng" dù có số hay không.
  **CHƯA ĐẠT, GHI THẲNG — SỐ CHƯA LÊN ĐƯỢC NHÃN COMBO.** Dòng Kokoro đã
  **139-178 ký tự** (đuôi `giong_bang._DUOI[KOKORO]` một mình **85 ký tự**) và
  hộp tìm giọng chỉ còn **dư 12 px** (cổng 84 CA 1 tự in). Đo **3 lần** bằng
  cổng 84 (mốc **ĐẠT 62 · HỎNG 2**): thêm **30 kt** -> 61 (28 mục thiếu) ·
  **15 kt** -> 61 (13 mục) · **15 kt + bỏ "(Kokoro)"** -> 61 (9 mục). Thứ bị
  đẩy ra khỏi dòng **KHÔNG phải con số** mà là ***"cần tải"*** / ***"miễn
  phí"*** — tức cái giá là **đổi một CẢNH BÁO lấy một CON SỐ** (chọn giọng chưa
  tải là ra giọng KHÁC). Đã loại cả 3 đường tắt: hạ mốc cổng · nới trần · rút
  ngắn `TÁC GIẢ CHẤM THẤP` (20 kt, nằm đúng trên 12 dòng dài nhất, và là thứ
  cổng 87 CA 10b canh). **Muốn bật thì lấy lại ~30 ký tự từ
  `giong_bang._DUOI[KOKORO]`** — 2 trong 4 việc nó nói đã trùng chỗ khác trên
  cùng dòng (*"KHÔNG có tiếng Việt"* trùng `Nữ · Mỹ`/`Nam · Anh` của từng giọng;
  *"KHÔNG có mốc từng chữ"* là chi tiết đúng chỗ cho tooltip). Không làm trong
  lượt này vì `giong_bang.py` đang do luồng khác giữ.
  Vẫn **chưa ai NGHE bằng tai** — mọi số trên là số ĐO, và `nhan_nha` đã dặn
  *"số này KHÔNG nói giọng HAY hay DỞ"*. Gợi ý cho anh Hùng nghe thử theo số:
  `am_santa` · `bm_lewis` · `am_liam` · `af_jessica` (nhấn nhá đỉnh, nhưng tác
  giả chấm D-/D+/D/D nên phải nghe mới biết đổi được gì lấy gì).
  Cổng đã chạy: **84 = 62 · 2** (đúng mốc) · **87 = 44 · 0** · **73 = 52 · 0** ·
  **76 = 31 · 0**.
- **"Adam NGHE LẠ": ĐO XONG — **CHỈ KÉM, KHÔNG HỎNG** (19/08/2026,
  `_do_adam_en.py` · `_kq_adam_en.txt`).** Anh Hùng nghe rồi: *"cái adam bị lỗi
  hay sao nghe cứ lạ lạ khác lắm, không như tôi nghĩ"*, và trỏ vào giọng Adam
  THẬT của ElevenLabs: *"ít nhất phải như này mới oke"*.
  Cửa thật `dubbing._synth_all`, corpus + bộ chấm + cache TTS **dùng lại
  `_do_vieneu_en.py`** (bộ chấm thứ hai = hai bảng số không so được), Groq chép
  ngược, VieNeu chạy **2 lượt** vì không tiền định:

  | arm (34 câu) | token sai TRONG CÂU | ĐỌC RỜI | bịa chữ | WER cả bài | lề im | nhãn tiếng |
  |---|---|---|---|---|---|---|
  | **`vn:Adam` × ANH** | **7,7-12,8%** | **16,7-29,2%** | **0,6%** | **5,2-7,0%** | 225/174 ms | **34/34 English** |
  | edge Aria × ANH (TRẦN) | 0,0% | 4,2% | 0,9% | 3,7% | 197/**860** ms | 34/34 |
  | `vn:Ngọc Huyền` × ANH | 17,9% | 8,3% | 1,6% | 8,3% | 112/187 ms | 33/34 (1 câu bị nhận là **Vietnamese**) |
  | `vn:Minh Đức` × ANH | 17,9% | 20,8% | 2,2% | 11,4% | 94/118 ms | 33/34 (**Malay**) |
  | `vn:Trúc Ly` × ANH | 15,4% | — | 3,4% | 11,7% | 104/175 ms | 33/34 (**Vietnamese**) |
  | **`vn:Adam` × VIỆT** | **2,5-5,0%** | 24,0-28,0% | 1,4% | 5,3-5,9% | 117/176 ms | 34/34 |
  | `vn:Ngọc Huyền` × VIỆT | 2,5% | 32,0% | 1,4% | 5,1% | 94/186 ms | 34/34 |
  | edge HoaiMy × VIỆT (TRẦN) | 5,0% | — | 1,6% | 5,1% | 192/**842** ms | 34/34 |

  (Adam chạy **2 lượt** nên là DẢI; arm khác lấy lại cache của lượt sáng nên 1
  lượt — edge-tts tiền định, VieNeu thì KHÔNG, ghi thẳng ra để đừng ai đọc dải
  của Adam thành "Adam nhấp nháy hơn giọng khác".)

  **VÌ SAO KẾT LUẬN LÀ "KÉM", KHÔNG PHẢI "HỎNG" — 6 dấu hiệu, không phải 1:**
  đọc trôi **34/34 câu + 24/24 token** (không câu nào hỏng, không lần nào lùi
  edge) · **bịa chữ 0,6% = THẤP NHẤT cả bảng** · **WER cả bài 5,2-7,0% so với
  trần 3,7%** (chỉ hơn 1,5-3,3 điểm, trong khi 3 giọng VieNeu khác đọc tiếng
  Anh ra **8,3-11,7%** — tức Adam là giọng VieNeu **TỐT NHẤT** ở tiếng Anh) ·
  lề im **225/174 ms** còn gọn hơn edge-tts (edge để **860 ms** ở đuôi) · máy
  nghe dán nhãn **"English" 34/34 ở CẢ HAI LƯỢT** trong khi 3 giọng Việt đọc
  tiếng Anh bị nhận thành **Vietnamese / Malay** · và đó là **giới hạn CỦA CẢ
  BỘ** giọng Việt, không phải lỗi riêng giọng này.
  Cột duy nhất Adam thua hẳn là **ĐỌC RỜI 16,7-29,2%** (trần 4,2%) — token một
  mình, không còn ngữ cảnh cho máy nghe chữa hộ.
  **CHỖ HỤT THẬT SỰ ĐO ĐƯỢC ĐÍCH DANH** (bảng 3 của `_kq_adam_en.txt`): TÊN
  RIÊNG và VIẾT TẮT — `Albuquerque`->"Abakuki" · `Siobhan`->"Sivan" ·
  `CEO`->"CAO" · `AI`->"I" · `OST` bị bỏ hẳn · `250 km/h`->"250 kilometers 10
  hack". **ĐÂY ĐÚNG LÀ LỚP BỆNH `doc_viet_tat.py` ĐÃ CHỮA ĐƯỢC** cho edge-tts
  giọng `vi-*` (cổng 69: `GDP` đọc "dê-dê-pê" -> đổi sang tên chữ cái Anh viết
  bằng âm Việt). Hướng đáng làm tiếp là **mở phạm vi `doc_viet_tat` sang giọng
  đọc tiếng Anh** — nhưng chưa làm, chưa đo, và nó cần cổng riêng vì bản vá cũ
  cố ý hẹp (chỉ `vi-*`).
  **KHÔNG TÌM RA LỖI MÃ/CẤU HÌNH NÀO** (ghi ra để khỏi ai đi tìm lại):
  `_MA_DOC` gọi `infer(text=..., voice="Adam")` đúng tham số, KHÔNG kèm
  `ref_audio`, KHÔNG truyền `style` (v3 Turbo ghi thẳng `style` là **DEPRECATED
  và BỊ BỎ QUA**); `Adam` có **CÙNG BỘ KHOÁ** với 19 giọng Việt.
  **GIẢ THUYẾT "Adam dùng BỘ ÂM TIẾNG VIỆT để đọc tiếng Anh": SAI ở chỗ người
  ta hay nghĩ, ĐÚNG ở một chỗ khác** — và đây là phần đáng đọc nhất.
  Bộ phiên âm ghi cứng `SEAPipeline(lang="vi")` + `G2P(lang="vi")`, `sea_g2p`
  còn **TỪ CHỐI `lang="en"`** (*"lang must be one of ('vi','th','id')"*): đọc
  tới đây thì tưởng đã chứng minh. **NHƯNG CHẠY THẬT** thì chữ tiếng Anh ra
  **âm tiếng Anh ĐÚNG** (`A storm unlike anything` -> `ɐ stˈɔːɹm ʌnlˈaɪk
  ˈɛnɪθˌɪŋ`), chữ Việt ra âm Việt kèm số thanh điệu; docstring của nó ghi
  *"Vietnamese/**bilingual** text"*. Bộ token model là **byte-level BPE 419
  token**, cả hai chuỗi âm ra **0 `<|unk|>`**. Vậy chỗ ĐÚNG của giả thuyết là
  **MODEL ÂM** (checkpoint học `VieNeu-TTS-1000h-in-the-wild` tiếng Việt), và
  bằng chứng sạch nhất nằm ngay trong bảng: **giọng "tiếng Anh" này giỏi TIẾNG
  VIỆT (2,5-5,0%) hơn TIẾNG ANH (12,8%)**, và đọc tiếng Việt **ngang một giọng
  Việt**. Một giọng như thế thì "nghe lạ" là **đúng theo cấu tạo**.
  **QUY TẮC RÚT RA: đọc mã tới `lang="vi"` rồi kết luận là DỪNG QUÁ SỚM** —
  phải chạy chính hàm đó với dữ liệu thật. Cùng họ bẫy "phép đo hỏng phát
  chứng nhận", chỉ khác là ở đây *phép ĐỌC MÃ* phát chứng nhận.
  **HÀNH ĐỘNG: việc của NHÃN, không phải của mã.** `GHI_CHU_ADAM` nay mang số
  đo + nói thẳng "KÉM HƠN, KHÔNG HỎNG" + **chỉ đường sang Adam của ElevenLabs
  đã có sẵn trong app**, KÈM CÁI GIÁ (tốn hạn mức theo ký tự) — chỉ đường mà
  không nói giá là bẫy. **KHÔNG chặn, KHÔNG giấu khỏi combo**: anh Hùng đã chốt
  *"cứ thêm hết, tôi tự trải nghiệm"*, và Adam **không** phải giọng tệ nhất bộ.
  **RANH GIỚI CỨNG:** KHÔNG nhân bản/tinh chỉnh giọng từ mẫu ElevenLabs — app
  này BÁN RA, đó là làm bản sao một giọng thương mại đang được bán.
  **FILE NGHE THỬ:** `_NGHE_THU_ANH_HUNG/adam_v2/` — 2 câu tiếng Anh × 3 giọng
  (`VN_Adam` · `EDGE_Aria` · `EL_Adam`), **chuẩn hoá cùng -14 LUFS** bằng chính
  `chuan_do_to` (không chuẩn hoá thì phép nghe thành "file nào TO hơn": đo được
  EL −16,1 vs VieNeu −20,1 LUFS = lệch 4 LU), MD5 **6/6 khác nhau** (bẫy cache
  `_eleven_tts`). Tốn **103 ký tự** ElevenLabs (còn 44.222/50.000 trên 5 tài
  khoản). **Tai anh Hùng là phán quyết cuối**, số chỉ để loại sớm cái hỏng rõ.
- **GIỌNG **NHÂN BẢN** (`vnb:`) ĐỌC TIẾNG ANH — BỆNH LÀ **KHÔNG ĐỀU**, KHÔNG
  PHẢI "ĐỌC SAI TIẾNG ANH"; VÀ ĐỔI SANG CHATTERBOX LÀM TỆ ĐI (26/08/2026,
  `_do_vnb_en.py` · `_kq_vnb_en.txt` · `_do_vnb_nhip.py` · `_do_vet_goiymay.py`).**
  Anh Hùng: *"âm thanh giọng nói oke mà CÁCH PHÁT ÂM BỊ LỖI rồi, khi clone
  giọng tiếng Anh nó đọc như thằng mới học ấy, nói không lưu loát không chuẩn
  chữ"* — màn hình: **đích Tiếng Anh** + giọng **`vnb:`**.
  Bảng 19/08 ở trên đo `vn:Adam` = giọng **DỰNG SẴN**; anh Hùng dùng giọng
  **NHÂN BẢN**, đường mã khác hẳn (`infer(ref_audio=)`), chưa ai đo. Ba arm
  **GHÉP CẶP trên CÙNG một file mẫu** (mẫu do edge-tts sinh — KHÔNG đụng
  `adam_clone.wav`, đó là bản sao một giọng ElevenLabs thương mại), cùng cửa
  thật `dubbing._synth_all`, cùng bộ chấm, trần lấy lại **đúng file tiếng**
  của bảng 19/08 nên hai bảng so được:

  | arm (cùng mẫu, 34 câu) | tok TRONG CÂU | tok ĐỌC RỜI | bịa chữ | WER | s/câu |
  |---|---|---|---|---|---|
  | **`vnb:` VieNeu** ⇐ đường anh Hùng | **2,6-5,1%** | 29,2-37,5% | **0,3-9,7%** | **3,1-12,7%** | 5,2 |
  | `cb:` Chatterbox | **17,9%** | 33,3% | 2,2% | 6,0% | 4,0 |
  | edge Aria (TRẦN) | 0,0% | 4,2% | 0,9% | 3,7% | 0,3 |
  | `vn:Adam` dựng sẵn (19/08) | 7,7-12,8% | 12,5-25,0% | 0,6% | 5,2-7,0% | 1,2 |

  **CANH ĐỘNG CƠ LÀ THỨ CỨU BẢNG NÀY.** `_synth_all` cố ý **lùi êm về
  edge-tts** khi máy nhân bản hỏng cả loạt — đúng cho người dùng, **thảm hoạ
  cho phép đo** (bảng sẽ ghi "Chatterbox 0,0%" trong khi thứ vừa đọc là
  edge). Nên mỗi arm đếm số câu THẬT SỰ do máy đó trả ra: **58/58 cả bốn
  lượt**, arm nào lệch là đánh dấu KHÔNG HỢP LỆ.
  **KẾT LUẬN 1 — KHÔNG ĐỔI MÁY THEO NGÔN NGỮ ĐÍCH.** Chatterbox sai chữ trong
  câu **17,9%**, tức **3,5-7 lần TỆ HƠN** `vnb:`; đọc rời ngang ngửa. Nó chỉ
  hơn ở chỗ **ĐỀU** (hai lượt ra WER **6,05 vs 6,05** — tiền định thật). Đổi
  lấy cái đều đó phải trả **GPU NVIDIA · dấu chìm Perth không tắt được (anh
  Hùng BÁN video) · nhịp lệch theo tiếng**. Không đáng.
  **KẾT LUẬN 2 — BỆNH THẬT LÀ ĐỘ KHÔNG ĐỀU, VÀ ĐÓ ĐÚNG LÀ THỨ TAI NGHE RA.**
  Cùng một bộ chữ, cùng một file mẫu, chạy hai lượt: lượt 1 **WER 3,1% · bịa
  chữ 0,3%** (**HƠN CẢ TRẦN** edge 3,7%/0,9%), lượt 2 **WER 12,7% · bịa chữ
  9,7%** (31/320 từ máy tự thêm). Nhịp cùng chiều: trung vị chỉ 1,03-1,04x
  trần nhưng câu tệ nhất **1,53x rồi 2,54x**, số câu vượt trần `atempo` là
  **1/34 rồi 3/34**. Token ĐỌC RỜI lộ rõ nhất: «2026» ra `在英雄城的美索`,
  «90%» ra `请你分赞`, «OST» ra một câu tiếng Trung **lặp 3 lần**.
  **`goi_y_may` KHÔNG phải hàm chết — nó chạy SAI LÚC** (truy vết AST + GỌI
  THẬT): đúng **1** nơi gọi (`them_giong`), **0** trong `app/ui/` (grep chuỗi
  ra 2 dòng, **cả hai là GHI CHÚ**), và `_synth_all(voice="vnb:", lang="en")`
  rẽ vào `giong_vieneu.doc_loat` y như `lang="vi"`. Máy đọc bị chốt **một lần
  lúc bấm Lưu giọng**; sổ thật ghi «adam Clone» = `may='vieneu' lang='vi'` dù
  mẫu là ghi âm **tiếng Anh**. Đó là lời giải cho *"sao chọn tiếng Anh mà vẫn
  ra VieNeu"*.
  **`doc_viet_tat` cũng KHÔNG đáng mở** (hướng còn lại): `vnb:` sai **1-2 trên
  39** token trong câu — lớp viết tắt ĐÃ ĐÚNG SẴN, chép âm cho nó là rủi ro
  thuần (đúng lớp bằng chứng đã loại bảng TÊN RIÊNG), và lần vá trước cho
  VieNeu đo ra **TỆ ĐI 2 · TỐT LÊN 0**.
  **HÀNH ĐỘNG: việc của NHÃN** (đúng tiền lệ `vn:Adam`) — `nhan_ban_giong.
  SO_DO_EN` giữ bảng số, `canh_bao_doc_tieng()` dựng câu **TỪ bảng đó** (cổng
  bắt được phép gõ tay số), UI hiện dòng vàng khi `vnb:` + đích ≠ tiếng Việt.
  **KHÔNG đụng `dedup_key`** — `app/services.py` không có một dòng thay đổi
  nào, nên 200-300 kênh không xuất lại.
  **CÒN NỢ, GHI THẲNG:** chỉ **MỘT** file mẫu (mà `giong_chatter` đã đo được
  *"MẪU kéo nhịp đọc"* — cùng câu, hai mẫu ra 1,03x và 1,32x), nên số này đi
  theo mẫu; **2 lượt** đủ để nói "KHÔNG ĐỀU", **không đủ** để nói tỉ lệ hỏng;
  **chưa đo mẫu THẬT của anh Hùng** (`adam_clone.wav` bị ranh giới pháp lý
  chặn); và ~~**chưa thử phép chữa đáng làm nhất** — dò câu lan man rồi **ĐỌC
  LẠI**~~ — **ĐÃ LÀM 26/08/2026, xem mục ngay dưới.**
  Cổng **91: 105 -> 131 · HỎNG 0**, thử phá **BẮT 8/8**.
- **DÒ CÂU LAN MAN RỒI ĐỌC LẠI — ĐÃ NỐI, MẶC ĐỊNH BẬT (26/08/2026,
  `app/core/doc_lan.py` · cổng 92).** Trả nốt món nợ mục trên. Vì cái hỏng của
  `vnb:` là **NGẪU NHIÊN theo lượt** (cùng mã cùng mẫu: WER 3,1% vs 12,7%) nên
  đọc lại là hướng DUY NHẤT còn cơ sở — mọi hướng đã bị bác đều cố sửa một thứ
  hỏng TIỀN ĐỊNH.
  **MỘT BỘ DÒ, KHÔNG PHẢI HAI.** Phép tính nằm ở `doc_lan.lan_vuot`;
  `giong_chatter.nghi_doc_lan` nay GỌI vào đó (số của nó **không đổi**:
  `("Okay.", 7.15)` vẫn ra **8,58**, bất biến cổng 91). Khác nhau chỉ là CHÍNH
  SÁCH: chatter dùng **hằng số** và chỉ soi câu ngắn; VieNeu **khớp mốc từ
  chính loạt đang đọc** và soi mọi câu.
  **HÌNH DẠNG MỐC PHẢI LÀ `a + b*n`, KHÔNG PHẢI `n × (giây/ký tự)` — bản đầu
  của tôi dùng cách sau và nó HỎNG ở đúng chỗ quan trọng nhất.** Mục NGẮN có
  **phí cố định** (lấy hơi, im hai đầu) nên giây/ký tự của chúng cao gấp mấy
  lần mục dài -> bộ dò kêu oan **22-24/58 mục của arm TRẦN edge-tts**, tức kêu
  trên giọng bản ngữ đọc ĐÚNG. Đổi sang `a + b*n` khớp bằng **Theil-Sen**
  (trung vị hệ số góc mọi cặp — KHÔNG phải bình phương tối thiểu, vì chính câu
  lan man là điểm ngoại lai và BPTT thì bị nó kéo, tức bộ dò tự vô hiệu hoá
  mình; đo trên cùng bộ số: **Theil-Sen lệch 0,0% · BPTT lệch 23%**):

  | bộ dò | BẮT/bịa | KÊU OAN/lành | **TRẦN edge kêu oan** |
  |---|---|---|---|
  | `n × trung vị gc` | 23/25 | 15/91 (16%) | **22/58** |
  | **`a + b*n`** | 18/25 | **2/91 (2,2%)** | **0/58** |

  **NGƯỠNG 1,5 CHỌN THEO CỘT TRẦN, KHÔNG PHẢI SỐ ĐẸP:** đó là chỗ **thấp nhất
  mà arm TRẦN không kêu một lần nào** (hạ 0,1 là trần kêu 1/58; nâng lên 2,0
  thì bỏ sót thêm mà không mua lại được gì). Mốc nhịp đo được lệch nhau rất
  xa giữa các loạt — `1,561+0,0328n` · `2,028+0,0261n` (VieNeu hai lượt) ·
  `0,899+0,0470n` (Chatterbox) · `1,860+0,0405n` (edge) — nên **ghim hằng số
  vào là sai theo cấu tạo**, đúng cái `giong_chatter` đã đo (*"MẪU kéo nhịp
  đọc"*).
  **HAI NHÓM **CHỒNG NHAU** — NÓI THẲNG, KHÔNG GIẢ VỜ CÓ ĐƯỜNG KẺ SẠCH.** Riêng
  trên CÂU (thứ lượt xuất thật sự đọc) chỉ có **2 câu bịa / 68**, `lan` **1,90
  và 2,32**, câu lành cao nhất **1,86** — khe hở **0,04** thì đó là TRÙNG HỢP,
  không phải ngưỡng (bài học `ty_giu`: 1 điểm dữ liệu thì KHÔNG đặt ngưỡng).
  Lưới an toàn thật nằm chỗ khác: **chỉ NHẬN bản đọc lại khi nó THẬT SỰ đỡ hơn**
  -> kêu oan chỉ tốn thời gian, không đổi được tiếng.
  **KIỂU HỎNG TRÊN CÂU LÀ "ĐỌC ĐÚNG RỒI NÓI TIẾP"**, không phải đọc sai:
  «The GDP of the whole country grew quite strongly.» -> đọc đúng, rồi thêm
  *"I would just add on there, the GDP of the whole country grew quite
  strongly."* Cả **9,7% bịa** của lượt xấu dồn vào **ĐÚNG 2 câu / 34**.
  **SỰ THẬT ĐỐI CHỨNG CẦN ASR, NÊN NÓ KHÔNG PHẢI LÀ BỘ DÒ.** `_has_cjk` + lặp
  cụm + đếm từ chèn chỉ dùng lúc HIỆU CHUẨN (`_do_vnb_lan.py`); thứ chạy lúc
  sản xuất là tín hiệu **MIỄN PHÍ** — độ dài WAV máy đọc đã trả về sẵn.
  **ĐO GHÉP CẶP, HAI ARM DÙNG CHUNG LƯỢT ĐỌC ĐẦU TỪNG BYTE** (bọc
  `_chay_vieneu` rồi CẤT lượt gọi đầy đủ đầu tiên; lượt đọc LẠI mang bộ chữ
  khác nên không bao giờ trúng kho):

  | vòng | arm | BẮT | đọc lại | NHẬN | bịa % | WER % | +giây |
  |---|---|---|---|---|---|---|---|
  | 1 | TẮT | 1 | 0 | 0 | 3,8 | 6,3 | +0,0 |
  | 1 | **BẬT** | 1 | 2 | 1 | **0,6** | **3,4** | **+15,5** |
  | 2 | TẮT | 1 | 0 | 0 | 0,9 | 4,3 | +0,0 |
  | 2 | **BẬT** | 1 | 1 | 1 | **0,6** | **3,7** | **+14,8** |

  **GIÁ: +15,5 s và +14,8 s trên nền 288 s / 248 s = +5,4% / +6,0%** bước đọc.
  Loạt LÀNH thì giá đúng bằng **0** (0 lượt gọi máy đọc thêm). **CHỐT
  CHỐNG-ĐẠT-OAN:** arm TẮT **vẫn DÒ** (chỉ không đọc lại) và ra 1 câu bắt mỗi
  vòng -> thước CÓ RĂNG.
  **MẶT XẤU, GHI THẲNG:** vòng 2 token sai TRONG CÂU đi **5,1% -> 7,7%** (39
  token = đúng MỘT token) — bản đọc lại chữa được đoạn lan man nhưng đọc sai
  một chữ bản cũ đọc đúng. Có lãi, nhưng không phải bữa trưa miễn phí.
  **BA CHỐT:** không bao giờ BỎ CÂU (hết trần thì GIỮ bản đang có + ghi log) ·
  chỉ NHẬN khi đỡ hơn quá BIÊN (khuôn `rut_gon_vua_khung`) · lượt chấm lại
  **dùng MỐC của loạt gốc**, cấm khớp lại trên chính nhóm nghi ngờ (khớp trên
  3 câu vừa bị bắt thì bản mới luôn trông "bình thường").
  **KHÔNG ĐỤNG `dedup_key`, VÀ ĐÓ LÀ BẢO ĐẢM DO CẤU TẠO:** cờ nằm gọn trong
  `giong_vieneu`, KHÔNG đi qua payload job nên `khoa_chong_trung` **không thể**
  đổi — cố ý KHÔNG làm ô cho user tự bật, vì làm thế là phải nối cờ xuống
  `tg_chay` tức tự tay mở đúng cái cửa đang được đóng. `BQ_VN_DOC_LAI=0` để tắt.
  **GIỚI HẠN ĐO ĐƯỢC (không giấu):** mốc khớp bằng TRUNG VỊ nên **quá nửa loạt
  cùng hỏng một kiểu** thì chính nhóm hỏng thành "bình thường" — đo: 20/30 câu
  hỏng chỉ bắt **9**. Đánh đổi CỐ Ý (thà bỏ sót còn hơn đọc lại cả video), cổng
  92 mục 4e'' giữ đúng con số đó để người sau đừng tưởng bộ dò hỏng.
  **Cổng 92 `_test_doc_lan.py`: ĐẠT 48 · HỎNG 0** (KHÔNG mạng · KHÔNG Groq ·
  KHÔNG GPU · KHÔNG ffmpeg — máy đọc là hàm giả sinh WAV theo nhịp biết trước,
  nên tiền định). Thử phá `_pha_doc_lan.py`: **BẮT 10 · LỌT 0 · KHÔNG PHÁ ĐƯỢC
  0**.
  **BẪY CỦA CHÍNH SCRIPT THỬ PHÁ, SẬP NGAY LƯỢT ĐẦU — bài học mới:** neo
  `except Exception as e:  # noqa: BLE001` có **12 chỗ** trong `giong_vieneu.py`,
  `replace(..., 1)` sửa nhằm chỗ ĐẦU TIÊN (một hàm khác) -> file **SyntaxError**
  -> cổng chết lúc `import` -> mã thoát 1 -> bảng ghi **BẮT**. Tức phép thử
  "bắt được" một chốt mà nó **chưa hề chạm tới**. Nay `_pha_doc_lan.py` đòi neo
  **DUY NHẤT** (có `neo_sau` để tách bạch) và **`compile()` lại bản đã phá** —
  không biên dịch được là **KHÔNG PHÁ ĐƯỢC**, không phải BẮT.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa ai NGHE** một file nào — mọi số trên là số ĐO
  · mẫu vẫn chỉ **2 vòng × 1 câu bị bắt mỗi vòng**, đủ để nói "có ăn", **không
  đủ** để nói tỉ lệ · vẫn **MỘT** file mẫu và vẫn là **giọng MÁY** (ranh giới
  pháp lý chặn `adam_clone.wav`) · bộ dò **chỉ dùng tín hiệu ĐỘ DÀI**; hai dấu
  hiệu mạnh hơn (chữ khác hệ chữ · lặp cụm) vẫn nằm ngoài vì chúng cần ASR —
  chưa đo xem một lượt ASR **cục bộ** (faster-whisper trên máy) có rẻ đủ để
  đưa vào không · chưa đo trên tiếng VIỆT (corpus hiệu chuẩn là tiếng Anh).
- **"2 TIẾNG MỚI ĐƯỢC 1 VIDEO 3 PHÚT" — TRUY RA, VÁ, ĐO LẠI: MẪU GIỌNG BỊ MÃ
  HOÁ LẠI **TỪNG CÂU** (27/08/2026, cổng 88 CA 18).** Anh Hùng: *"làm cực kỳ
  lâu, không hiểu 2 tiếng mới được 1 video lồng tiếng 3 phút"* = **40 lần thời
  gian thật**. Mọi số trong file này nói con số đó không thể đúng
  (`giong_vieneu` ghi **5,2 giây/câu**), nên việc số một là ĐO.
  **ĐO TRÊN CHÍNH LƯỢT CHẠY CỦA ANH HÙNG, KHÔNG DỰNG LẠI KỊCH BẢN** — và đây
  là phần đáng chép lại: app của anh ấy để sẵn đủ dấu vết để đo mà **không đụng
  một byte**. `%LOCALAPPDATA%\BQHungVideo\_giong_vieneu\_job_*/job.json` có ĐỦ
  danh sách câu; `_tam_*/raw/*.wav` có `mtime` = đúng lúc câu đó đọc xong. Hiệu
  hai `mtime` liền nhau = **giây/câu THẬT**, trên máy thật, mẫu thật, dưới đúng
  tải nền thật (`_do_vn_that.py`). Lượt đo bắt được app đang chạy 2 tiến trình
  VieNeu, mỗi cái **143 luồng · 2,6 GB RSS (phình lên 4,5 GB sau 36 phút)**.

  | job | câu | s/câu | ký tự/câu |
  |---|---|---|---|
  | `_job_5148_74210` (xong 103/103) | 103 | **26,2** | 37 |
  | `_job_5148_79772` | 133 | **25,0** | 39 |
  | `_job_27196_26007` | 184 | **26,2** | 40 |
  | `_job_27196_80927` | 143 | **32,3** | 41 |

  **27,4 giây/câu · 141 câu/video -> 64 PHÚT cho MỘT lượt đọc**, mà đường thay
  giọng gọi đọc **3 lượt** (4a · 4b · 4c). Nhân ra đúng 2 tiếng. **Hai con số
  đều gấp ~5 lần thứ đang ghi trong tài liệu**, và số câu (103-184, không phải
  60-70) là nửa bất ngờ thứ hai — `cau_tu_transcript` cắt rất nhỏ, TB **39 ký
  tự/câu**.
  **CHỖ HỎNG ĐO ĐƯỢC ĐÍCH DANH: GIÁ NẰM Ở *LƯỢT GỌI*, KHÔNG Ở ĐỘ DÀI CHỮ.**
  Chia câu làm hai nửa theo số ký tự: câu **23 ký tự -> 25,5s** · câu **52 ký
  tự -> 26,9s**. Gấp đôi chữ chỉ thêm **1,4 giây** -> khớp `a + b*n` ra **phí
  CỐ ĐỊNH 19,5-24,4 giây/câu = 78-93%**. Đọc mã ra đúng thủ phạm:
  `vieneu/v3turbo.py` `infer(ref_audio=...)` -> `_resolve_ref` ->
  `_preclean_reference_audio` (librosa trim + ghi file tạm) +
  `engine.prepare_reference` (**mã hoá NeuCodec CẢ MẪU 10 giây**) — **lặp lại
  CHO TỪNG CÂU**. Tức mỗi câu trả tiền enrol lại giọng từ đầu.
  **VÁ: gói CÓ SẴN đường làm một lần.** `add_voice(name, ref_audio)` chạy ĐÚNG
  hai dòng ấy MỘT LẦN rồi cất `speaker_emb` + `codes` vào `_preset_voices`;
  `infer(voice=name)` dùng lại CHÍNH hai mảng số đó -> **không đổi một tham số
  nào đưa vào model**. Đây là bản vá **TỐC ĐỘ THUẦN, không đánh đổi chất
  lượng** (tiếng ra vẫn không giống từng byte vì `infer` lấy mẫu ngẫu nhiên
  `temperature=0.8 · top_k=25 · top_p=0.95` — bản chất model, đúng cái đã cho
  3,1% vs 12,7% WER trên CÙNG bản mã).
  **ĐO GHÉP CẶP** (`_do_vn_refcache.py` — **đan xen TỪNG CÂU**, đảo thứ tự
  chẵn/lẻ, cùng tiến trình, cùng mẫu, cùng bộ chữ):

  | | CŨ (`ref_audio` mỗi câu) | MỚI (enrol một lần) |
  |---|---|---|
  | giây/câu | 33,5 | **4,4** |
  | ghép cặp | — | **MỚI thắng 6/6 câu** |
  | ước 1 lượt đọc 141 câu | 78,8 phút | **11,2 phút** |

  Qua **cửa thật `doc_loat`**: `gen` **137,72s/3 câu (45,9 s/câu) -> 17,58s/3
  câu (5,86 s/câu)** = **7,8 lần**, mốc từng chữ vẫn lấy đủ (10/11/12 từ).
  **E2E TRÊN ĐÚNG CẤU HÌNH ANH HÙNG SAU VÁ** (`_do_cham_tg.py`; video THẬT
  148,6s trong `Downloads\longtieng` **copy ra hộp cát**, `vnb:` + đích `en` +
  tách nhạc + "Chỉnh video theo giọng" + che chữ BẬT; mẫu là **GIỌNG MÁY**
  edge-tts — luật cấm `adam_clone.wav`): **726,6 giây = 12,1 phút**, `ok=True`,
  **4,89 lần thời gian thật**, 63 câu.

  | bước | giây | % tổng |
  |---|---|---|
  | 0 rút tiếng | 0,8 | 0,1% |
  | 1 TÁCH NHẠC (Demucs, cuda) | 64,7 | 8,9% |
  | 2 chép lời (Groq) | 15,2 | 2,1% |
  | 3 dịch + hậu kiểm (Groq) | 143,5 | 19,8% |
  | **4a ĐỌC bản dịch** | **258,1** | **35,5%** |
  | **4b rút gọn** | **94,7** | **13,0%** |
  | **4c ĐỌC NHANH lại (44/63 câu)** | **92,1** | **12,7%** |
  | 5 khớp thời gian | 20,7 | 2,9% |
  | 5b giãn nhạc · 5c bù giọng gốc | 9,5 | 1,3% |
  | 6 trộn tiếng | 13,9 | 1,9% |
  | 7 che chữ + ghép | 13,3 | 1,8% |

  **Ba bước ĐỌC = 444,9s = 61,2% tổng** -> đó vẫn là chỗ đắt nhất, chỉ khác là
  nay nó đắt **hợp lý**. Kèm: **5 lần spawn VieNeu** (63 · 1 · 13 · 5 · 46
  câu), **16 lượt Groq**, **VRAM đỉnh 2.723 MiB (nền 612 -> +2.111)** đo bằng
  **POLL trong lúc chạy** (lấy mẫu hai đầu ra mức nền — bẫy đã sập ở cổng
  71/73), `doc_lan` bắt **1 câu**.
  **s/câu từng lượt spawn: 2,69 · 5,27 · 0,67 · 0,71 · 0,76.** Lượt **5,27** là
  lượt `doc_lan` đọc lại **1 CÂU** — nó **CỐ Ý đi đường CŨ**, xem ngưỡng dưới.
  **NGƯỠNG `CAU_TOI_THIEU_ENROL = 3`, VÀ ĐÓ KHÔNG PHẢI SỐ ĐẶT MÒ:** enrol tốn
  **46,5s MỘT LẦN**, đổi lại mỗi câu bớt ~29s -> **hoà vốn ~2 câu**. Nút **Nghe
  thử** (`doc_thu` -> `doc_ban_dich([txt], ...)`) đọc **ĐÚNG 1 CÂU**: enrol ở
  đó là biến 29s thành 51s, tức "tối ưu" làm chậm đúng cái người dùng đang ngồi
  đợi. `_doc_lai_lan_man` cũng thường chỉ đọc lại 1-3 câu -> cùng đường.
  **BẢN `vieneu` KHÔNG CÓ `add_voice` -> LÙI ÊM** về đường cũ (mất phần nhanh,
  không mất cả video), và khai `enrol_ok=False` chứ không khoe cái mình không
  làm được.
  **NHẬT KÝ NAY MANG `s/câu` + `nạp mẫu`** — hai con số duy nhất phân biệt được
  *"máy chậm"* với *"đường đọc đang nạp lại mẫu từng câu"*. Thiếu chúng thì lần
  sau lại phải đi đọc `mtime` file WAV để đoán ra, đúng cách phải làm lần này.
  **KHÔNG ĐỤNG `dedup_key`:** cờ nằm gọn trong tiến trình con của
  `giong_vieneu`, KHÔNG đi qua payload job -> 200-300 kênh **không có gì để
  xuất lại**, và đó là bảo đảm DO CẤU TẠO chứ không do một chuỗi `sig` viết
  đúng. `app/services.py` và `tg_chay.py` **không đổi một dòng nào**.
  **`giong_chatter` CÓ CÙNG HÌNH DẠNG NHƯNG *ĐỪNG* SỬA** — đã kiểm: nó truyền
  `audio_prompt_path` vô điều kiện mỗi câu **CÓ CHỦ Ý** (Chatterbox cache
  conditionals lên `self.conds`, gọi `generate()` không kèm mẫu là nó dùng lại
  mẫu của lượt TRƯỚC = rò giọng). Và giá ở đó không giống: `cb:` đo **4,0
  s/câu**, không phải 27.
  **`TG_TRAN` / `tran_luong_tg`: CỐ Ý KHÔNG ĐỘNG VÀO, và lý do là SỐ.** Mốc
  *"4 luồng 1,5 tiếng ra 0 video · 1 luồng 45 phút xong 4 video"* (21/08) đo
  **TRONG LÚC mỗi câu còn mã hoá lại mẫu** — tức nó mô tả một khối lượng công
  việc **không còn tồn tại**. Đo trên đúng 2 tiến trình pre-vá của anh Hùng:
  mỗi cái chỉ ăn **3,63 và 3,75 nhân** (không phải 6,6-8,3 như
  `NHAN_MOI_LUONG_MAY = 8.0` giả định), còn tiến trình **sau vá** của lượt E2E
  ăn **1,03 nhân**. Nên hạ/siết trần theo bằng chứng cũ là siết theo một phép
  đo đã lạc hậu. **CHƯA ĐO LẠI ĐƯỢC 4/2/1 luồng** — xem "chưa đạt".
  **CỔNG 88 CA 18: 233 -> ĐẠT 246 · HỎNG 0.** Cách chấm: **CHẠY THẬT `_MA_DOC`**
  ở tiến trình riêng với một `vieneu` **GIẢ** ghi sổ từng lượt gọi — không
  model, không GPU, không mạng, TIỀN ĐỊNH, vài giây. Nhờ vậy cổng đọc **HÀNH VI
  THẬT** chứ không quét chuỗi (bài học 56d: quét chuỗi thì luôn có phép phá giữ
  nguyên mặt chữ mà đổi ý nghĩa). 6 câu -> `add_voice` **1 lượt / 6 câu**, mọi
  câu `voice=`, **0 câu còn `ref_audio=`**; 1 câu -> **0 enrol**; thiếu
  `add_voice` -> vẫn `ok=True`; giọng DỰNG SẴN `vn:` -> **0 enrol** (bất biến
  cho 20 giọng đang chạy sản xuất). Kèm **TỰ KIỂM BỘ DÒ hai chiều**: gỡ lời gọi
  -> bộ dò PHẢI kêu (bản đã phá vẫn `compile()` được, nên là phép phá THẬT) ·
  chữ nằm trong GHI CHÚ -> KHÔNG được tính là đã gọi.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa ai NGHE** một file nào sau vá — mọi số trên
  là số ĐO, và bản vá không đổi tham số vào model nhưng *chưa có tai người xác
  nhận* · **chưa đo được 4 vs 2 vs 1 luồng**: suốt lượt làm việc, app của anh
  Hùng chạy 2 tiến trình VieNeu nặng (3,6-3,8 nhân mỗi cái, RSS phình tới 4,5
  GB), nên **mọi phép đo song song đều vô nghĩa** — đan xen cũng không cứu
  được một tải nền đổi theo thời gian; phải đo lại lúc máy rảnh · con số E2E
  726,6s vì thế là **TRẦN TRÊN** (đo dưới tải nền), máy rảnh sẽ nhanh hơn ·
  **1 video · 1 mẫu · 1 lượt** — đủ để nói "ăn 7,5 lần", **không đủ** để nói
  phân bố · **RSS phình 2,6 -> 4,5 GB sau 36 phút** trên tiến trình pre-vá là
  chuyện **chưa truy** (có thể là tích luỹ theo số câu; nếu còn sau vá thì
  `RAM_MOI_LUONG_MAY_GB = 4.3` là sát trần, 4 luồng sẽ đảo trang) · `4c` vẫn
  đọc lại **44/63 câu** và vẫn là bước đắt thứ ba — mục 3 combo ("đọc ĐỀU") bỏ
  hẳn nó, **chưa đo lại trên đường `vnb:` sau vá**.
- **"KHÔ KHAN, KHÔNG CÓ CẢM XÚC" — ĐO XONG BA HƯỚNG, VÀ CÂU TRẢ LỜI KHÔNG PHẢI
  MỘT BẢN VÁ MÃ (27/08/2026; `_do_el_camxuc.py` · `_do_mau_dai.py` ·
  `_do_san_vnb.py` · `_nghe_thu_cam_xuc.py`).** Anh Hùng sau 10 bản vá:
  *"thật sự nó chưa được hay, với KHÔNG CÓ CẢM XÚC, KHÔ KHAN, lúc nhanh lúc
  chậm"*. Ba lời kêu, **KHÔNG cùng một bệnh** — đừng gộp.
  **ĐỐI CHỨNG TÁI LẬP CHẠY CÙNG LƯỢT, VÀ NÓ BẮT ĐƯỢC LỖI CỦA CHÍNH PHÉP ĐO:**
  `vi-VN-HoaiMy` 3,18 -> **3,18** · `vi-VN-NamMinh` 4,04 -> **4,04** ·
  `en-GB-Ryan` 5,38 -> **5,38**, lệch tối đa **0,00** trên cả ba. Lượt ĐẦU
  Ryan ra **4,76** (lệch 0,62, cổng tự kêu *"THƯỚC LỆCH, KHÔNG TIN"*) vì
  `doc_4_cau` ghi cứng `CAU["vi"]` cho MỌI giọng -> **giọng Anh đọc câu tiếng
  Việt**, đúng cái `_do_nhan_nha_bang.cau_cho` đã dặn thành lời. Thước KHÔNG
  hỏng; **phép đo sai vì cho giọng đọc sai thứ tiếng**. Bài học: cột đối chứng
  đỏ thì nghi PHÉP ĐO trước khi nghi thước.
  **HƯỚNG (A) MẪU DÀI HAY MẪU CÓ NHẤN NHÁ — 2x2 TÁCH HAI BIẾN, CÙNG 4 CÂU,
  mỗi ô 2 lượt (VieNeu không tiền định):**

  | ô | nhấn nhá MẪU | -> BẢN SAO |
  |---|---|---|
  | A1 mẫu THẤP · **7 giây** | 2,99 | 3,28-3,35 |
  | A2 mẫu THẤP · **28 giây** | 3,19 | 3,24-3,25 |
  | A3 mẫu CAO · **7 giây** | 3,47 | 3,92-4,01 |
  | A4 mẫu CAO · **28 giây** | 3,83 | 3,66-3,98 |
  | **A5 TRẦN · 28 giây** | **5,84** | **5,74-5,92** |

  **ĐỘ DÀI MẪU KHÔNG ĂN.** Giữ nguyên giọng nguồn, 7 -> 28 giây: A1 3,31 ->
  A2 3,25 (**−0,06**) · A3 3,96 -> A4 3,82 (**−0,14**). Cả hai ÂM, nằm trong
  nhiễu. **Thu mẫu dài ra là vô ích.**
  **ĐỘ NHẤN NHÁ CỦA MẪU ĂN GẦN 1:1.** A1(mẫu 2,99) 3,31 vs A3(mẫu 3,47) 3,96
  = **+0,65** · A2(3,19) 3,25 vs A4(3,83) 3,82 = **+0,57** · A2 vs **A5(mẫu
  5,84) 5,83 = +2,58**. Bản sao đi theo mẫu suốt dải **2,99 -> 5,84** mà
  **KHÔNG bão hoà** — tức model không có trần cảm xúc quanh 4 như từng lo;
  nó CHÉP mẫu. Lời khuyên cho anh Hùng vì thế là **THU LẠI MẪU, ĐỌC DIỄN
  CẢM** (không phải thu dài, không phải đổi máy đọc).
  Mẫu do **edge-tts / VieNeu dựng sẵn** sinh ra — **KHÔNG dùng
  `adam_clone.wav`** (bản sao một giọng ElevenLabs thương mại), đúng ranh giới
  cứng của repo.
  **HƯỚNG (B) ElevenLabs v3 + THẺ CẢM XÚC: *CHƯA NỐI* TRÊN ĐƯỜNG THAY GIỌNG —
  CHỨNG MINH BẰNG GỌI THẬT + ĐẾM, có ĐỐI CHỨNG DƯƠNG và ÂM.** Thay
  `dubbing._eleven_tts_once` (cửa HTTP **DUY NHẤT** tới endpoint
  text-to-speech) bằng hàm sinh mp3 bằng ffmpeg rồi GHI SỔ model thật sự gửi
  đi -> **0 ký tự bị tiêu**:

  | arm | số lượt gọi | model gửi đi | text còn thẻ |
  |---|---|---|---|
  | RECAP `emotion=True` (đối chứng DƯƠNG) | 2 | **`eleven_v3`** | CÓ |
  | RECAP `emotion=False` (đối chứng ÂM) | 2 | `eleven_multilingual_v2` | không |
  | **`thay_giong.doc_ban_dich` + `el:`** | **2** | **`eleven_multilingual_v2`** | CÓ (không ai strip) |

  Ba chốt ĐẠT cả ba: **bản vá ĂN được** (arm1>0 và arm3>0 — bằng 0 thì mọi
  kết luận vô nghĩa, đúng bẫy cổng 67) · đối chứng DƯƠNG ra v3 · đối chứng ÂM
  KHÔNG ra v3. Nên *"đường thay giọng không gửi v3"* là **số đo**, không phải
  suy luận từ mã.
  **GỐC CƠ CHẾ:** `_chay_eleven` **không có tham số `model`** ->
  `_synth_all_eleven(model="")` -> `_eleven_effective_model("")` -> mặc định
  v2. `_synth_all`/`_synth_all_words` cũng không có đường nào nhận cảm xúc.
  Tức **hộp Thay giọng KHÔNG có một cửa nào chỉ đạo cảm xúc**, và ElevenLabs
  là máy đọc DUY NHẤT nhận được chỉ đạo đó -> đây là **câu trả lời thật** cho
  *"không có cảm xúc"* trên đường `el:`.
  **NỢ KÈM (chưa vá, ghi thẳng):** arm 3 cho thấy thẻ `[...]` đi NGUYÊN sang
  v2 — `_strip_audio_tags` **không được gọi** ở đường thay giọng. Bình thường
  bản dịch không có thẻ, nhưng chép lời Groq **có** trả `[Music]`/`[Applause]`
  -> lúc đó v2 đọc to cái ngoặc. Chưa đo tần suất.
  **GIÁ, NÓI RA:** ElevenLabs tính **theo KÝ TỰ**. Đo thật 5 tài khoản free:
  **còn 43.804/50.000**. Video 3 phút ~2.275 ký tự -> **~19 video là hết
  sạch**. Với 200-300 kênh thì đó **KHÔNG** phải giải pháp hằng ngày; nó là
  **TRẦN TRÊN** để anh Hùng nghe biết "hay" là hay tới đâu.
  **HƯỚNG (C) KOKORO — CHỌN ĐƯỢC, NHƯNG THỨ TỰ COMBO ĐANG ĐẨY GIỌNG PHẲNG LÊN
  ĐẦU.** Gọi thật `giong_kokoro.danh_sach_giong()`: **28/28 dòng có mặt**,
  nhãn đầy đủ **140-163 ký tự** và **KHÔNG chứa một con số nhấn nhá nào**
  (`duoi_nhan_nha` trả `' · nhấn nhá 5,7'` nhưng **0 nơi gọi** — cố ý, xem
  mục Kokoro ở trên; `giong_bang.duoi_nhan_nha('kk:...')` trả `''`).
  Sắp xếp theo **ĐIỂM TÁC GIẢ**, và điểm đó **không dự đoán được nhấn nhá**
  (Spearman 0,12 đã ghi) nên hàng đầu bảng là chỗ phẳng nhất:
  **dòng 2 = `af_bella` nhấn nhá 2,33** (thấp thứ 2 cả bộ) · **dòng 27 =
  `am_santa` nhấn nhá 5,66** (CAO NHẤT) · dòng 17 `bm_lewis` 4,67 · dòng 22
  `am_liam` 4,60. Anh Hùng bấm từ trên xuống là trúng đúng giọng phẳng —
  **và chưa ai nói cho anh ấy biết 26 dòng dưới có gì**. Kokoro **KHÔNG có
  tiếng Việt** nên hướng này chỉ dùng cho video TIẾNG ANH.
  **HƯỚNG THỨ TƯ, KHÔNG CÓ TRONG ĐỀ BÀI, VÀ LÀ THỨ RẺ NHẤT — 20 GIỌNG VIỆT
  DỰNG SẴN ĐÃ CÓ SỐ MÀ CHƯA AI BẮT CHÉO VỚI ĐỘ ĐỌC SAI.** Tra `nhan_nha.BANG`
  × `nhan_nha.DOC_SAI` (sàn `WER_MOC` = 4,8%):

  | giọng | nhấn nhá | đọc sai % |
  |---|---|---|
  | `vn:Xuân Vĩnh` | **6,26** (cao nhất bảng Việt) | **26,4** (5,5x sàn) |
  | **`vn:Thanh Bình`** | **5,61** | **9,0** |
  | `vn:Adam` | 5,55 | 6,2 |
  | `vn:Quang Sơn` | 4,90 | **29,2** |
  | edge `vi-VN-NamMinh` (đang dùng) | 4,04 | chưa đo |
  | edge `vi-VN-HoaiMy` | 3,18 | 4,8 (sàn) |
  | `vn:Ngọc Linh` | 2,95 | chưa đo |

  **Nhấn nhá cao KHÔNG bắt buộc đi kèm đọc sai** — `Thanh Bình` 5,61/9,0% và
  `Adam` 5,55/6,2% chứng minh điều đó, còn `Quang Sơn` 4,90/29,2% chứng minh
  chiều ngược. **`vn:Thanh Bình` là đánh đổi tốt nhất đo được**: hơn giọng
  anh Hùng đang dùng **+1,57 nửa cung** nhấn nhá, đọc sai 9,0%.
  **VÀ NÓ ĐANG LÀ DÒNG ĐẦU TIÊN của nhóm VieNeu** (gọi thật
  `giong_vieneu.danh_sach_giong` -> `Thanh Bình` hạng **1**, còn 4 giọng đọc
  sai nhiều bị đẩy xuống **16-19**) — tức app **đã** sắp đúng, chỉ là **chưa
  ai nói cho anh Hùng biết**. Ghi chú cũ *"`vn:Xuân Vĩnh` đang là DÒNG ĐẦU"*
  nay **LẠC HẬU**.
  **LỜI KÊU "LÚC NHANH LÚC CHẬM" — SÀN CỦA `vnb:` LÀ MỘT DẢI, KHÔNG PHẢI MỘT
  SỐ.** Đúng thước `_do_khop_video.toc_do_doc` (ký tự/giây TỪNG CÂU trên mốc
  NÓI THẬT bằng `silencedetect`, **không** `probe_duration`), 20 câu **5-102
  ký tự** (bộ câu đều nhau ra CV thấp GIẢ), mọi máy đọc CÙNG bộ câu:

  | máy đọc | SÀN CV % |
  |---|---|
  | edge `HoaiMy` | 13,30 |
  | edge `NamMinh` (đối chứng) | 14,03 |
  | **NHÂN BẢN `vnb:`** | **12,49 và 18,77** (2 lượt) |
  | `vn:Xuân Vĩnh` | 15,90 và 18,23 |
  | `vn:Ngọc Linh` | 19,64 và 21,05 |

  **HAI LƯỢT `vnb:` CÙNG MÃ CÙNG MẪU CÙNG CÂU LỆCH 6,3 ĐIỂM** -> sàn của
  đường nhân bản **KHÔNG TIỀN ĐỊNH**; nói "sàn là X%" là nói sai. So với
  edge-tts (13,3-14,0, tiền định) thì `vnb:` **tốt nhất là bằng, xấu nhất là
  tệ hơn**. Đây là cùng một bệnh "không đều" mà mục `_do_vnb_en` đã đo trên
  chiều đọc sai (WER 3,1% vs 12,7% giữa hai lượt).
  **HỆ QUẢ: KHÔNG chữa được bằng mã.** Mục 3 combo ("đọc ĐỀU", bỏ bước 4c) đo
  trên edge-tts kéo CV **14,29 -> 9,76**; phần dưới 9,76 chính là sàn máy
  đọc. Trên `vnb:` sàn ấy là 12,5-18,8 **và ngẫu nhiên** -> bỏ 4c vẫn giúp
  (và giúp nhiều hơn edge, vì `giong_vieneu._ep_khung` thực thi `rate` bằng
  **rubberband co giãn hậu kỳ** chứ không phải đọc nhanh THẬT như edge, tức 4c
  trên đường clone vừa tạo trải tốc độ vừa thêm méo phổ) **nhưng không thể về
  0**. Chưa đo ghép cặp bật/tắt mục 3 trên `vnb:` — xem "chưa đo được".
  **FILE NGHE THỬ: `_NGHE_THU_ANH_HUNG/cam_xuc/`** — 10 file, **chuẩn hoá
  CÙNG −14 LUFS** bằng chính `thay_giong.chuan_do_to` (I đo lại −14,00 ..
  −14,59 · TP −1,43 .. −1,97 dBTP), **10/10 MD5 KHÁC NHAU** (bẫy cache
  `_eleven_tts` theo `sha1(voice|model|text)`). Cùng MỘT câu tiếng Việt cho
  01-06, cùng MỘT câu tiếng Anh cho 07-08. Tiêu **266 ký tự** ElevenLabs
  (43.804 -> 43.538) cho 2 file cuối.
  **BẪY ĐỌC HẠN MỨC, MỚI:** đọc quota NGAY SAU lượt gọi ra **y nguyên 43.804**
  (tưởng "không tiêu gì"); đọc lại lần 3 mới ra **43.538**. Endpoint
  `/user/subscription` **cập nhật CHẬM** — muốn biết đã tiêu bao nhiêu thì
  phải đọc lại sau vài phút, hoặc đếm file mới trong `_cache/tts` (2 file mới
  đúng giờ chạy = đã gọi thật).
  **THƯỚC NHẤN NHÁ KHÔNG NÓI "HAY" — nhắc lại vì cả mục này đứng trên nó.**
  `nhan_nha` tự dặn vậy; nó chỉ nói ĐỘ TRẢI CAO ĐỘ. Vì thế `Xuân Vĩnh` 6,26
  là giọng "trải" nhất mà **đọc sai 26,4%** — số cao không có nghĩa là chọn
  được. **Tai anh Hùng là phán quyết cuối.**
  **CHƯA ĐO ĐƯỢC, VÀ VÌ SAO:** (1) **ghép cặp bật/tắt mục 3 trên `vnb:`** —
  cần một lượt `thay_giong_video` THẬT/arm, mà đo E2E gần nhất là **726,6
  giây/video** và đường clone không tiền định nên phải >= 2 lượt/arm; không
  đủ thời gian lượt này. (2) **chưa ai NGHE** — 10 file đã sinh, mọi con số
  trên là số ĐO. (3) **mẫu nhỏ**: hướng (A) 2 lượt/ô · sàn 2 lượt/giọng — đủ
  để nói "độ dài không ăn, nhấn nhá ăn", **không đủ** để nói phân bố.
  (4) **`vn:Thanh Bình` chưa có số CV** (chỉ đo Xuân Vĩnh và Ngọc Linh).
  (5) **chưa đo mẫu THẬT của anh Hùng** (7 giây) — ranh giới pháp lý chặn
  `adam_clone.wav`, nên mọi mẫu là giọng MÁY, và mẫu sạch là ca DỄ NHẤT.
  (6) tần suất `[Music]`/`[Applause]` lọt vào text thay giọng: **chưa đếm**.
  **KHÔNG ĐỔI MỘT DÒNG `app/` NÀO trong lượt này** (`git status --porcelain
  app/ config.py main.py` -> RỖNG) nên `dedup_key` của 200-300 kênh **không
  thể** đổi — bảo đảm DO CẤU TẠO, không do một chuỗi `sig` viết đúng.
  **CỔNG (không cổng nào phải nâng vì không có mã mới):** 3 cửa chặn ĐẠT
  (pyflakes **0** dòng "undefined name" · `_test_app_smoke.py` **exit 0** ·
  `_test_pipe_dialogs.py` **exit 0**); 76 **31·0** · 87 **44·0** · 63
  **49·0** · 92 **85·0**. **84 ra 62·2** — đúng mốc *"ĐẠT 62 · HỎNG 2"* mà
  chính CLAUDE.md đã ghi ở mục Kokoro, nhưng `_chay_hoi_quy.CONG` ghi **63**;
  hai mục hỏng (*"gõ chuỗi vô nghĩa"* + *"thử phá LỌT 1 phép"*) **CÓ SẴN**,
  không do lượt này (0 dòng `app/` bị sửa). **KHÔNG hạ mốc 63** — việc đúng
  là chữa 2 mục đó rồi mới sửa số, chưa làm.
- **QUÉT CẢ 20 GIỌNG VieNeu TRÊN CÂU TIẾNG VIỆT — 3 GIỌNG LỆCH HẲN, CẦN ĐO LẠI
  (19/08/2026, `_do_vn_quet.py` · `_kq_vn_quet.txt`).** Anh Hùng chỉ nêu đích
  danh Adam, nhưng câu hỏi thật là *"còn mấy kiểu khác nữa"*. Bộ 8 câu (sàng
  lọc, **không phải bảng chính xác**: 10 token/giọng nên 1 token = 10 điểm %),
  trần là `vi-VN-HoaiMyNeural` chạy cùng bộ câu:
  **token sai: 20 giọng trải 0,0-30,0% (trung vị 0,0%) · trần 0,0%.**
  Vượt trần (> trần + 10 điểm): **`vn:Xuân Vĩnh` 30,0%** · **`vn:Mai Anh`
  20,0%** (bịa chữ **7,9%**, cao nhất bảng) · **`vn:Ngọc Trân` 20,0%**.
  Cột **WER** (mẫu lớn hơn hẳn — ~90 từ/giọng) cùng chiều và mạnh hơn: Mai Anh
  **34,4%** · Xuân Vĩnh **31,4%** · Quang Sơn **22,3%** · Thanh Bình **20,9%**
  so với trần **5,4%** và trung vị bộ ~5-6%.
  **`vn:Adam` đọc tiếng Việt chỉ 10,0% token sai / WER 5,4%** — nằm giữa bộ,
  KHÔNG bị gắn cờ. Tức nếu bấm nhầm Adam cho video Việt thì hậu quả nhẹ hơn
  hẳn 3 giọng vừa nêu.
  **ĐÁNG LO NHẤT: `vn:Xuân Vĩnh` đang là DÒNG ĐẦU TIÊN của nhóm "Khuyên dùng"**
  trong combo (đo thẳng `giong_bang.gom_nhom`), tức giọng người ta bấm nhanh
  nhất lại là giọng lệch nhất trong phép sàng lọc này.
  **ĐÃ ĐO LẠI BẰNG BỘ 34 CÂU (`_kq_vn_quet34.txt`) — 3 GIỌNG XÁC NHẬN LỆCH
  THẬT, 1 GIỌNG LÀ NHIỄU CỦA PHÉP SÀNG LỌC:**

  | giọng (34 câu · 40 token · ~350 từ) | token sai | bịa chữ | **WER** |
  |---|---|---|---|
  | **`vn:Quang Sơn`** | 20,0% | 3,8% | **29,2%** |
  | **`vn:Xuân Vĩnh`** | 20,0% | 4,6% | **26,4%** |
  | **`vn:Mai Anh`** | 17,5% | **7,4%** | **25,5%** |
  | `vn:Ngọc Trân` | 7,5% | 1,9% | **19,9%** |
  | `vn:Thanh Bình` | 0,0% | 3,0% | 9,0% |
  | `vn:Adam` (đọc tiếng VIỆT) | 2,5% | 1,4% | 6,2% |
  | `vn:Ngọc Huyền` | 2,5% | 1,4% | 4,8% |
  | **edge HoaiMy (TRẦN)** | 2,5% | 1,6% | **4,8%** |

  **3 giọng đầu sai gấp 5-6 LẦN TRẦN** trên mẫu ~350 từ/giọng — ngoài vùng
  nhiễu, không phải hiệu ứng mẫu nhỏ. `vn:Ngọc Trân` gấp 4 lần. Ngược lại
  `vn:Thanh Bình` bị bảng 8 câu gắn cờ (WER 20,9%) mà bộ 34 câu ra **9,0%** ->
  đó là **nhiễu của phép sàng lọc**, đúng cái docstring `_do_vn_quet.py` đã
  cảnh báo trước khi đo. **Bài học: bảng 8 câu chỉ để CHỌN AI ĐO LẠI, không
  bao giờ để kết luận.**
  `vn:Adam` đọc tiếng Việt **2,5% / WER 6,2%** = sát trần, tức bấm nhầm Adam
  cho video Việt còn nhẹ hơn hẳn chọn 4 giọng kia cho đúng tiếng của nó.
  **CHƯA LÀM GÌ VỚI 4 GIỌNG ĐÓ — CỐ Ý.** Anh Hùng đã chốt *"cứ thêm hết, tôi
  tự trải nghiệm"*, và số này là **để anh ấy quyết**, không phải để tôi giấu
  giọng khỏi combo. Việc nên làm tiếp (chưa làm, chưa đo): nhãn của 4 giọng đó
  nói ra con số, hoặc xếp chúng xuống dưới trong `giong_bang.gom_nhom` — nhưng
  `vn:Xuân Vĩnh` đang là **DÒNG ĐẦU nhóm "Khuyên dùng"** nên đây là việc đáng
  làm sớm.
- **GIÓNG HÀNG CHỮA ĐƯỢC BỆNH PHỦ CỦA GIỌNG NGOÀI — ĐO 18/08/2026.**
  `dubbing._synth_all_words` nay lấy mốc cho giọng ngoài + Piper bằng gióng
  hàng khi máy có bộ đó. Thứ tự: máy đọc tự trả mốc (edge-tts `WordBoundary`,
  ElevenLabs `/with-timestamps`) -> gióng hàng -> Groq chép ngược.
  **THƯỚC DUY NHẤT: `silencedetect`.** Hai bẫy đã sập: đo OmniVoice bằng Groq
  là **so nó với chính nó** (mốc nó lấy từ Groq -> ra 0,0 ms trên 1.587 mốc),
  và **mọi thước là máy nghe đều thiên vị** (faster-whisper nói OmniVoice tốt
  hơn edge-tts, nhưng cột số mốc khớp tố giác 1.466 vs 1.043).
  **PHÉP ĐO SUÝT KẾT LUẬN SAI — phần đáng giá nhất:** `_do_gn_gh.py` (WAV sinh
  mới) đo đường Groq ra PHỦ tiếng Việt **99,4%** trong khi nhãn đang ghi
  30-56%. Chạy lại `_do_gn_phu.py` trên bộ WAV CŨ vẫn ra **41,8% / 61,4%**.
  Cùng hàm, cùng corpus, khác nhau đúng ở **MẺ TIẾNG**: OmniVoice **KHÔNG TIỀN
  ĐỊNH**, lượt này đọc rõ lượt kia đọc ngọng, Groq chép ngược ăn theo. Tức
  **34-56% không phải hằng số của đường Groq, nó là hằng số của MỘT MẺ ĐỌC
  KÉM** — mục trên đã ghi nhận dao động, nay truy được NGUYÊN NHÂN.
  Vì vậy `_do_gn_cu.py` cho **hai đường lấy mốc chạy trên ĐÚNG MỘT BỘ FILE
  TIẾNG** (bỏ hẳn nhiễu đó). 4 thứ tiếng × 12 câu × 2 lượt ĐAN XEN có xoay thứ
  tự, 2.186 chữ mỗi bộ, arm edge-tts chạy lại trên CÙNG corpus:

  | | OV+Groq | **OV+gióng hàng** | edge-tts |
  |---|---|---|---|
  | PHỦ — bộ WAV CŨ (mẻ đọc kém) | 52,5% | **98,6%** | — |
  | · Việt · Anh · Trung · Nhật | 37,6 · 79,0 · 67,5 · 25,7 | **98,9 · 100,0 · 96,8 · 98,7** | — |
  | PHỦ — bộ WAV MỚI (mẻ đọc tốt) | 82,1% | **98,5%** | 78,2%* |
  | RUNG mốc chữ đầu — CŨ / MỚI | 711,9 / 250,4 ms | **90,4 / 119,2 ms** | **15,7 ms** |
  | mốc[0] đúng là từ đầu | 45/96 | **88/96** | 50/96* |
  | GIÂY cho mẻ 12 câu | 32,49 | **6,30** | 3,54 |

  (*) **edge 78,2% KHÔNG phải chữ mất mốc mà là GIỚI HẠN CỦA MẪU SỐ**: PHỦ đếm
  theo `recap._word_tokens` (CJK tách TỪNG KÝ TỰ) còn `WordBoundary` trả theo
  CỤM -> Trung 56,3% / Nhật 57,1%. Ở Việt/Anh (có dấu cách) edge ra **99,4% /
  100%** đúng như cấu tạo. Cột dùng để kết luận là Việt/Anh và là phép so
  Groq-vs-gióng-hàng (hai bên **cùng một mẫu số**).
  **PHỦ LÊN GẦN 100% Ở CẢ HAI MẺ (98,5 · 98,6) -> là tính chất do CẤU TẠO,
  không phải may.** Gióng hàng không đoán chữ, nó ĐÃ BIẾT chữ. Và nó **rẻ hơn
  5,2 lần** đồng thời **không tốn một lượt Groq nào**.
  **NHƯNG CHƯA BẰNG edge-tts, NÓI THẲNG:** rung còn **90-119 ms** so với
  **15,7 ms**. Nặng nhất là tiếng Anh (lệch hệ thống **+104..+121 ms**, rung
  128 ms). **Chưa truy ra vì sao, và ĐỪNG trừ nó đi bằng một hằng số** — cổng
  67 đã chặn đúng phép trừ kiểu đó (94 ms).
  **CỘT "% chữ hiện muộn >50 ms" KHÔNG ĐỌC THẲNG ĐƯỢC** (Groq 36,5% -> gióng
  hàng 42,7%): nó tính trên lệch **THÔ** nên trừng phạt bên có lệch hệ thống
  DƯƠNG và thưởng bên đánh mốc SỚM — edge ra 0,0% chính vì nó sớm sẵn
  (−88,9 ms). Muốn so chất lượng thuần thì đọc cột **RUNG**.
  **NHÃN ĐỔI THEO MÁY** (`giong_ngoai.canh_bao_chat_luong()`, đúng tiền lệ
  nhãn Piper): máy CÓ gióng hàng -> nói phủ 98,5% + rung 90-119 ms; máy CHƯA
  có -> giữ cảnh báo phủ thấp, nhưng số cũng phải sửa cho đúng (**38-99% tuỳ
  lượt**, không phải "30-56%" — đo được 37,6% và 99,4% thì in 30-56% là biết
  sai vẫn in). **Phần GIẤY PHÉP giữ nguyên** ở cả hai trạng thái. Cổng 72
  CA 7g-7k canh.
- **MÔI TRƯỜNG OmniVoice ĐÃ RA KHỎI `%TEMP%` (18/08/2026).** Lượt 7 dựng môi
  trường Python **7,74 GB / 47.520 file** ở `%TEMP%\bq_tts_rr\venv_ov`. Một
  lượt `tempsweep` / Disk Cleanup / anh Hùng dọn ổ C là **mất sạch**, và triệu
  chứng không phải một dòng lỗi mà là **"giọng tự nhiên biến khỏi combo"** —
  không ai lần ra nguyên nhân từ triệu chứng đó. Cùng bệnh `_lib` bị chính
  lượt tự cập nhật xoá (cổng 58 CA5).
  Đã dời THẬT sang `<repo>/_giong_ngoai/venv` (robocopy 47.520/47.520 file,
  **0 FAILED**), **kiểm bằng cách CHẠY THẬT** chứ không chỉ đọc đường dẫn:
  `doc_loat` ra WAV 3,11 s / 149.324 byte, gióng hàng trên chính file đó
  **11/11 mốc**; rồi đổi tên bản cũ -> kiểm lại `co=True` -> mới xoá. Ổ C:
  370 -> **377 GB** trống.
  Chống tái diễn: `o_thu_muc_tam()` + khoá `o_tam` (để RIÊNG, **không gộp vào
  `thieu`** — máy vẫn chạy được, gộp là nhãn/nút báo sai trạng thái) ·
  `doc_loat` ghi log cảnh báo MỖI LƯỢT · ứng viên `%TEMP%` vẫn giữ ở CUỐI danh
  sách (máy nào còn bản cũ thì chạy được thay vì gãy, nhưng nay nó kêu) ·
  `.gitignore` thêm `_giong_ngoai/`. Cổng 72 CA 7l/7m/7n canh, kèm TỰ KIỂM
  BỘ DÒ.
- **`.spec` VÀ HAI TÍNH NĂNG NÀY: ĐÃ KIỂM, KHÔNG PHẢI SỬA GÌ.** Ghi ra vì mục
  việc từng nêu ".spec chưa khai": `collect_submodules('app')` đã gom cả
  `app.core.giong_hang` lẫn `app.core.giong_ngoai` (kiểm thật, có trong danh
  sách 69 module); hai module **không đọc file tài nguyên nào** (script chạy ở
  tiến trình con được GHI RA từ chuỗi nhúng `_MA_GIONG` / `_MA_DOC` — chính vì
  thế bản `.exe` không có cây mã nguồn mới chạy được). Phần nặng là đồ **TẢI
  RỜI LÚC CHẠY** đúng ràng buộc Demucs/Piper (torch dùng chung `_lib` ~4,3 GB ·
  MMS_FA 1,18 GB · OmniVoice 6,1 GB); gói vào `.exe` là bộ cài phình từ 240 MB
  lên hơn 11 GB. Ghi hẳn khối ghi chú vào `.spec` để người sau đừng "sửa".
- **"MÁY ĐỌC SAI CHỮ NƯỚC NGOÀI / TÊN RIÊNG" — ĐÃ ĐO, ĐÃ CHỐT CÁCH SỬA,
  *CHƯA NỐI VÀO APP* (17/08/2026).** Anh Hùng: *"chọn tiếng Việt, mấy chữ tiếng
  Anh hay tên riêng nó đọc toàn bị lỗi ... **lỗi to đó**"*. Bộ câu thử dùng
  chung ở `_bo_cau_thu_doc.py` (4 ngôn ngữ × 6 loại × ~34 câu, chấm theo
  **TOKEN** chứ không theo cả câu; loại `cau_thuong` là **SÀN ĐỐI CHỨNG** vì
  máy nghe cũng sai).
  **PHÉP ĐO 1 — token TRONG CÂU** (`_do_doc_sai.py`, edge-tts thật qua cửa
  chung + Groq chép ngược): Việt **5%** · Anh **0%** · Trung **3%** · Nhật
  **3%** (sàn `cau_thuong`: Việt 12%, còn lại 0%).
  **NHƯNG PHÉP ĐO 1 QUÁ DỄ DÃI — đây mới là phần đáng giá.** Groq
  whisper-large-v3 là MỘT MÔ HÌNH NGÔN NGỮ: nghe *"nét phờ lích"* trong câu
  *"đứng đầu bảng xếp hạng ___"* thì nó vẫn viết ra `Netflix`. Tức **máy nghe
  CHỮA HỘ máy đọc** và bảng đó đang phát chứng nhận cho thứ vẫn hỏng (họ bẫy
  `astats` cổng 53 · mức mờ 0,40 cổng 56b).
  **PHÉP ĐO 2 — token ĐỌC RỜI, không ngữ cảnh, có ARM ĐỐI CHỨNG giọng bản ngữ
  en-US làm TRẦN** (`_do_doc_roi.py`):

  | Loại | TRẦN en-US | Việt | Trung | Nhật |
  |---|---|---|---|---|
  | Tên riêng nước ngoài | 0% | **33%** | 17% | 17% |
  | Từ viết tắt | 29% | **57%** | 17% | 17% |
  | Số và ngày | 0% | 0% | 0% | 0% |
  | Đơn vị / ký hiệu | 0% | 0% | 0% | 0% |
  | **TỔNG** | **8%** | **24%** | **8%** | **8%** |

  **TIẾNG VIỆT GẤP 3 LẦN TRẦN; Trung và Nhật ĐÚNG BẰNG trần** (trong phân giải
  của phép đo, không có vấn đề thêm). Token hỏng ở arm đích MÀ TRẦN ĐỌC ĐƯỢC:
  Việt 4 (`Marvel`->"Mác vô" · `TikTok`->"でっか" · `GDP`->"DDP" ·
  `view`->"Vư"), Trung 1 (`Marvel`->"マーロ"), Nhật 1 (`Elon Musk`->"異論無粋").
  Trong câu còn thấy `Elon Musk` -> **伊朗马斯克** ("Iran Musk") ở tiếng Trung
  và **イロン息子** ("Iron con trai") ở tiếng Nhật.
  **SỐ / NGÀY / ĐƠN VỊ: 0% ở CẢ 4 NGÔN NGỮ, CẢ 2 PHÉP ĐO** — Azure đã chuẩn
  hoá sẵn (`1.500.000`->"1 triệu 500 nghìn" · `15/08`->"15 tháng 8" ·
  `250 km/h`->"250 km trên giờ" · `38°C`->"38 độ C" · `500$`->"500 đô la").
  Tức việc *"đọc rõ số"* là việc **KHÔNG CẦN LÀM**; làm là sửa thứ đang đúng.
  **edge-tts CÓ CHO SSML QUA KHÔNG: KHÔNG** (`_do_ssml.py`, thí nghiệm chứ
  không suy đoán). `Communicate` escape chữ người dùng TRƯỚC khi dựng SSML nên
  thẻ bị **ĐỌC THÀNH TIẾNG**: `<lang xml:lang="en-US">Netflix</lang>` ra
  *"...bảng xếp hạng Lan Smeller, Lan, NUSF, Netflix, Lan"*;
  `<say-as interpret-as="characters">GDP</say-as>` ra *"CS Interps Charaster
  GDP CS"*. Thử CẢ HAI đường (cửa chung của app **và** API trần) — giống hệt.
  **ĐƯỜNG SSML ĐÓNG, đừng ai đi lại.**
  **CÁCH SỬA — ĐO TRƯỚC KHI VIẾT** (`_do_phien_am.py`, 25 token, 2 arm ĐAN
  XEN, **GHÉP CẶP** từng token vì `_do_co_gian_ab` đã chỉ ra "27 tốt lên mà 32
  TỆ ĐI, tổng lại là hoà"): thô **6/25 (24%)** -> phiên âm **4/25 (16%)**;
  **TỐT LÊN 2 · TỆ ĐI 0 · y nguyên 23**.
  · **LUẬT VIẾT TẮT ĂN, và biết CHÍNH XÁC vì sao:** giọng Việt đánh vần bằng
    TÊN CHỮ CÁI VIỆT (G="dê", D="đê", P="pê") nên `GDP` ra "dê-dê-pê" -> chép
    thành **DDP**; người Việt đọc viết tắt bằng tên chữ cái ANH ("gi-đi-pi").
    Đổi sang tên chữ cái Anh viết bằng âm Việt: `CEO` "See ya."->**CEO** ·
    `GDP` "DDP"->**GDP**, và KHÔNG làm hỏng `AI`/`MV`/`USB` (đúng ở cả 2 arm).
  · **BẢNG TÊN RIÊNG *KHÔNG* ĐƯỢC PHÁT HÀNH**, hai nửa đều nói không:
    `Netflix`/`iPhone`/`Elon Musk`/`YouTube` **ĐANG ĐÚNG SẴN ở bản thô** (chép
    âm cho chúng là rủi ro thuần, 0 lợi ích đo được); còn
    `Marvel`/`TikTok`/`view` **VẪN HỎNG sau khi chép âm** ("Ma-veo"->«Mà về»,
    "Tíc-tóc"->«でっか», "viu"->«Vư») — tức phiên âm ĐOÁN không hơn bản thô.
  · **GIỚI HẠN CỦA PHÉP ĐO, đừng tính vào cột "chưa được":** `OST` hỏng ở cả 2
    arm, **nhưng ARM TRẦN en-US cũng trượt OST** («Westy») — viết tắt 3 chữ đọc
    MỘT MÌNH vốn mơ hồ.
  **VÌ SAO CHƯA NỐI VÀO APP — CHỐT KỸ THUẬT THẬT:** chữ HIỆN LÊN lấy từ `texts`
  GỐC, còn MỐC THỜI GIAN lấy từ WordBoundary của chính chữ ĐÃ GỬI cho máy đọc
  (`dong_chu_theo_giong` -> `chia_cum_theo_tu` -> `_khop_tu_vao_chu`). Đổi chữ
  gửi đi (`GDP`->"gi đi pi") là 3 mốc-từ không còn tìm thấy trong chữ hiện lên.
  `_khop_tu_vao_chu` BỎ QUA từ không khớp nên KHÔNG vỡ — **nhưng nó đẩy con trỏ
  `cur` đi TIẾN**, mà `"gi"` là chuỗi con của rất nhiều chữ Việt (`gì`, `giá`,
  `nghĩ`), nên mốc sẽ dính vào SAI CHỖ rồi kéo con trỏ qua, làm lệch mốc của
  các từ SAU đó = đúng lỗi *"chữ chạy không khớp tiếng"* mà v2.28.0 vừa chữa.
  Bản vá ĐÚNG phải **trả mốc về token gốc** (gộp dãy mốc của phần thay thế lại
  thành MỘT mốc mang chữ gốc) + cổng canh riêng.
  **ĐÃ LÀM XONG Ở `964e22b`, PHÁT HÀNH TRONG v2.33.0 — mục "CHƯA NỐI VÀO APP" ở
  đầu khối trên nay LẠC HẬU, đọc tới đây thì dừng.** `app/core/doc_viet_tat.py`
  (hàm THUẦN): `doi_chu` đổi viết tắt sang tên chữ cái Anh viết bằng âm Việt và
  trả kèm khoảng ký tự từng phần thay thế; `tra_moc_ve_goc` GỘP dãy mốc của
  phần thay thế thành MỘT mốc mang chữ GỐC (đầu của «gi», cuối của «pi», chữ =
  `GDP`) nên `_khop_tu_vao_chu` không bao giờ nhìn thấy chữ đã đổi -> con trỏ
  không bị kéo sai chỗ. Nối ở **CỬA CHUNG** của `dubbing.py` (đủ 3 cửa:
  `_synth_all` · `_synth_all_words` — cửa CÓ mốc nên có gọi `tra_moc_ve_goc` ·
  `synth_demo`, để nghe thử đúng bằng thứ lúc xuất sẽ ra).
  **Cổng 69 `_test_viet_tat.py`: ĐẠT 95 · HỎNG 0**, không gọi mạng, không tốn
  lượt. Tự kiểm đã chạy thật: đổi `words[i] = tra_moc_ve_goc(...)` về
  `words[i] = wb` thì cổng ĐỎ thật (rc=1), 7/7 câu mất mốc và mốc dính vào chữ
  Việt KHÁC.
  Phạm vi vẫn CỐ Ý HẸP đúng như đã chốt ở trên (chỉ edge-tts giọng `vi-*`, chỉ
  2-3 chữ cái HOA, bỏ qua số La Mã / viết tắt gốc Việt / cái đọc thành từ, và
  **KHÔNG làm bảng tên riêng**) — mọi giới hạn đều theo chiều "để nguyên = hành
  vi hôm nay, không thể tệ hơn".
  **KHÔNG CÓ TAI — mọi số trên là SỐ ĐO.** File tiếng thật để anh Hùng tự nghe:
  `_NGHE_THU_ANH_HUNG/doc_sai/<nn>/` (theo câu) và
  `_NGHE_THU_ANH_HUNG/doc_roi/<nn>/` (token đọc rời).
  **`edge-tts` ĐÃ CHỐT TRẦN `<8`** trong `requirements.txt` +
  `requirements-build.txt`: từ 7.x mặc định đổi sang
  `boundary="SentenceBoundary"` = **MẤT MỐC TỪNG CHỮ ÂM THẦM**. App an toàn nhờ
  `dubbing.py:2046` truyền `WordBoundary` tường minh, nhưng chỗ gọi MỚI nào
  quên là chữ lệch mà không ai biết. Máy đang chạy 7.2.8, vẫn lọt trần.
- **ĐỘ TO ĐƯỜNG CẮT TRẢI 15,75 LU — ĐO XONG, *CHƯA SỬA*, CẦN ANH HÙNG DUYỆT
  (16/08/2026, `_do_lufs_duong.py`).** VIỆC 1 đòi "đường nào cũng phải đo".
  Chạy ffmpeg THẬT (`export_canvas_clip`) trên 4 video THẬT:

  | nguồn | NGUỒN | cắt thường | ghép 2 đoạn |
  |---|---|---|---|
  | Douyin (anh Hùng đang làm) | −5,07 | **−6,65 TP +3,94** | −6,15 TP +0,66 |
  | GOING BACK TO OUR OLD HOUSE | −14,25 | −10,78 | −10,02 |
  | DaddyOFive | −15,27 | −15,88 | −15,60 |
  | Kid BREAKS his leg prank | −15,17 | **−22,40 TP +0,94** | **−20,22** |

  **HAI LỖI, cả hai đều thật:** (1) **trải 15,75 LU** (−6,65 .. −22,40) giữa
  các clip — clip ra to hay nhỏ hoàn toàn tuỳ đoạn phim cắt trúng; clip
  −22,40 là **thấp hơn đích 8,4 LU**, đúng chữ *"ít tiếng quá"*. (2) **đỉnh
  thật vượt 0 dBTP ở 3/8 bản xuất** = VỠ TIẾNG thật — `alimiter` sau khi trộn
  CHỈ được thêm khi có tiếng động (`whoosh_on`), nên đường cắt trần không ai
  chặn đỉnh.
  Lệch so với nguồn **KHÔNG một chiều** (+3,47 / +4,23 ở đoạn to hơn TB cả
  phim; −7,23 / −5,05 ở đoạn nhỏ hơn) -> **không "chép mức nguồn" được, phải
  ĐO TỪNG CLIP**.
  **VÌ SAO CHƯA SỬA:** thêm chuẩn hoá vào `export_canvas_clip` là đổi TIẾNG
  CỦA MỌI CLIP từ nay về sau trên 200-300 kênh đang chạy sản xuất. Biện pháp
  đã sẵn sàng (dùng lại `chuan_do_to`, chạy trên file đã xuất với `-c:v copy`
  nên chỉ mã hoá lại audio, ~1 giây/clip). **Đợi anh Hùng duyệt.**
- **MẤT TIẾNG 82,35 s: BẢNG SAU ĐÃ CHẠY — VÀ CON SỐ 82,35 KHÔNG TÁI LẬP ĐƯỢC
  (19/08/2026).** Đọc cả khối này trước khi đo lại, nếu không sẽ mất nửa phiên
  đúng như tôi vừa mất.
  **BỐN CHỖ DỄ KẾT LUẬN NGƯỢC, xếp theo mức nguy hiểm:**
  (a) **`Downloads\longtieng\xuất` ĐÃ BỊ GHI ĐÈ.** mtime cả 4 file là **19/08
  12:52-12:59**; bản xuất sinh ra con số 82,35 s **không còn trên đĩa**. Đo lại
  4 file đang có ra **45,60 s**, và rất dễ kết luận "bản vá ăn 45%" hoặc "thước
  hỏng". Cả hai đều SAI.
  (b) **APP ANH HÙNG ĐANG CHẠY KHÔNG CÓ BẢN VÁ.** `D:\BQHungVideo\
  BQHungVideo.exe` (bản CÀI, KHÁC `dist/`) dựng **18/08 20:01**, còn
  `bu_giong_goc` ra đời ở `063da74` **18/08 22:18** — bản nhị phân không thể
  chứa mã viết sau nó. **Chứng minh trực tiếp, không suy luận:** bóc
  `PYZ-00.pyz` bằng `PyInstaller.archive.readers` rồi quét `co_consts` /
  `co_names` của `app.core.thay_giong` -> `bu_giong_goc` · `BU_GOC_BUOC` ·
  `khoang_khong_giong` **đều False**. Nên cột "file anh Hùng đang có" là số
  **TRƯỚC**, không phải "sau khi vá". Anh Hùng phải cài **v2.39.0** mới có bản
  vá (`git show 73fca2f:app/core/thay_giong.py` -> `BU_GOC_BUOC = 0.05`).
  (c) **THƯỚC KHÔNG PHẢI THỦ PHẠM — đã đo.** Chạy `_do_mat_giong.py` HAI lượt
  trên CÙNG 4 file: **45,60 s vs 45,45 s** (lệch 0,15 s = **0,01%** thời
  lượng), sàn nhiễu lệch ≤ 0,1 dB. Thước TIỀN ĐỊNH.
  (d) **VẬY 82,35 vs 45,60 LÀ NHIỄU CỦA CHÍNH DÂY CHUYỀN** — cùng mã KHÔNG vá,
  cùng 4 video, hai lượt xuất khác nhau ra **82,35 s** và **45,60 s = 1,81
  lần**. Gốc: LLM không tiền định -> mỗi lượt bỏ qua bộ câu khác nhau. **Đừng
  bao giờ so hai lượt xuất RỜI** — commit `4d738e8` đã tố giác chuyện này một
  lần (20,05 s vs 30,65 s trong khi bản vá nằm im) mà tôi vẫn suýt dẫm lại.
  **PHÉP SO ĐÚNG LÀ GHÉP CẶP** (`_do_bang_sau.py`): MỘT lượt chạy dây chuyền
  cho mỗi video, hai arm tách ra ở đúng chỗ bản vá tác động
  (`manh_tron = kh["manh"] + bu["manh"]`), nên cùng bản tách / chép lời / dịch
  / file giọng. Mọi nhiễu LLM bị triệt tiêu **theo cấu tạo**.
  **SỐ ĐO (3/4 video, 908,2 s — video 3 chỉ mất 0,40 s nên không chạy lại):**

  | video | dài | TRƯỚC (file đang có) | TẮT (đối chứng) | **BẬT** | bù |
  |---|---|---|---|---|---|
  | `#强烈推荐…` | 148,6 s | 0,00 s | 3,20 s | **0,00 s** | 9 mảnh / 17,66 s |
  | `一款…倒忌时` | 363,2 s | 21,75 s | 36,40 s | **5,30 s** | 37 / 66,89 s |
  | `八位好莱坞…` | 396,3 s | 20,95 s | 23,55 s | **9,45 s** | 37 / 41,75 s |
  | **TỔNG** | **908,2 s** | **42,70 s** | **63,15 s** | **14,75 s** | |
  | % thời lượng | | 4,70% | 6,95% | **1,62%** | |

  **GHÉP CẶP: 63,15 s -> 14,75 s = giảm 76,6%.**
  **PHÂN BỐ ĐỘ DÀI MỚI LÀ CHỖ ĐÁNG ĐỌC — con số tổng che mất nó:**

  | | <0,5 s | 0,5-1 s | 1-2 s | >=2 s | tổng |
  |---|---|---|---|---|---|
  | file đang có (không vá) | 17,95 | 15,05 | **10,30** | **2,30** | 45,60 |
  | ghép cặp — TẮT | 20,85 | 30,25 | **12,05** | 0,00 | 63,15 |
  | ghép cặp — **BẬT** | 10,20 | 4,55 | **0,00** | **0,00** | 14,75 |

  **MỌI KHOẢNG >= 1 GIÂY VỀ 0** (12,05 -> 0,00 s). Đó đúng là lớp "mất cả cụm
  / cả câu" mà anh Hùng nghe ra là *"bị TẮT TIẾNG"*. Phần còn lại 14,75 s
  **toàn mảnh dưới 1 giây** (10,20 s dưới 0,5 s; dài nhất trong arm BẬT của
  video 4 là **0,65 s**) — đó là chênh nhịp giữa âm tiết tiếng Trung và tiếng
  Việt, không phải mất nội dung. **NÓI THẲNG: KHÔNG về 0, và đừng hứa về 0**:
  thước đếm mọi cửa sổ "gốc có tiếng mà xuất im" ≥ 0,30 s, trong đó có cả chỗ
  hai ngôn ngữ đặt âm tiết lệch nhau.
  **CHỐT CHỐNG-ĐẠT-OAN NẰM TRONG CHÍNH PHÉP ĐO:** arm TẮT ra 3,20 / 36,40 /
  23,55 s -> thước CÓ RĂNG trên đúng bộ file này. Nếu nó ra 0 ở cả hai arm thì
  số của arm BẬT là vô nghĩa.
- **`ai_nguoi_noi`: ANH HÙNG ĐÃ CHỐT **BỎ** (19/08/2026) — *"bỏ cái tính năng
  nhận diện cảnh người nói thật với người lồng tiếng"*. File + số đo GIỮ LẠI,
  KHÔNG xoá (đọc khối dưới trước khi ai định dựng lại).**
  **VÌ SAO BỎ, và lý do KHÔNG phải chất lượng:** module này tồn tại để quyết
  *"chỗ này giữ tiếng gốc, chỗ kia lồng"*. Câu đó chỉ có nghĩa khi tiếng gốc
  **BỊ BỎ ĐI** — tức cách trộn `"tach"`. Cùng ngày anh Hùng đề xuất chế độ
  **ĐÈ GIỌNG, KHÔNG TÁCH** (`thay_giong.CACH_TRON == "de"`): tiếng gốc giữ
  NGUYÊN, chỉ hạ xuống rồi đè giọng lồng lên. Ở chế độ đó tiếng gốc **không bao
  giờ bị bỏ** -> **hết việc phải quyết**. Ý thứ hai của anh Hùng khớp ý thứ nhất.
  **KHÔNG CÓ GÌ ĐỂ GỠ — đã quét, không suy đoán:** module CHƯA TỪNG được nối vào
  đường xuất/UI. `grep -rn "nguoi_noi" app/ config.py main.py` ra **0 lời gọi**
  (chỉ chính file đó + 1 dòng ghi chú ở `giong_chatter.py` nhắc TÊN SCRIPT ĐO);
  `BQHungVideo.spec` không khai đích danh nó. Nơi duy nhất dùng là script đo
  `_do_nguoi_noi_cham.py`. Nên "bỏ" ở đây = **chốt lại rằng sẽ không nối nữa**,
  không phải một lượt gỡ mã.
  Nếu sau này đổi ý (muốn giữ tiếng gốc THEO CẢNH *bên trong* cách `"tach"`) thì
  đọc hết 4 lý do dưới trước khi viết dòng đầu — nặng nhất là ngân sách LLM
  **+3,5 đến +4,7 lần**.
  **SỐ ĐO CŨ (vẫn đúng, giữ nguyên): CHẠY ĐƯỢC, ĐO ĐƯỢC —
  *CHƯA NỐI*, và lý do là THỨ TỰ chứ không phải chất lượng (19/08/2026).**
  Smoke test trên bản chép lời THẬT đã cache (`_do_tg_cache.json` khoá
  `chep|zh|90.0`, 45 đoạn / 398 mốc từ, Groq THẬT): `cham_llm` -> **10 lượt gọi
  LLM / 156 s**, mồi đối chứng **bắt được 1 mẻ sai và gọi lại thành công**,
  nhãn `ke 41 · goc 4`, `quyet_dinh` giữ gốc **4/45 đoạn = 3,48 s** và 4 đoạn
  đó đều là **`你這個混蛋`** — thoại phim gào lên, đúng thứ cần giữ. Không dính
  trần `TRAN_GIU_GOC`. Tức module KHÔNG phải mã chết.
  **BỐN LÝ DO CHƯA NỐI, theo thứ tự nặng:**
  (1) **THỨ TỰ:** "giữ gốc" nghĩa là KHÔNG lồng tiếng đoạn đó -> đường xuất
  sinh thêm khoảng trống -> phần bù trống đó chính là `bu_giong_goc`, mà bản vá
  ấy vừa mới chứng minh được (khối trên) và **anh Hùng còn chưa chạy nó lần
  nào** (app 18/08 20:01 không có bản vá). Nối bộ sinh-thêm-khoảng-trống TRƯỚC
  khi bộ bù-khoảng-trống ra tới máy anh Hùng là đúng cách làm nặng thêm chính
  lỗi "TẮT TIẾNG".
  (2) **GIÁ ĐO ĐƯỢC:** 10 lượt LLM cho 90 s nguồn = **~14 lượt cho video 148 s
  · ~30 lượt cho video 396 s**, so với `_dich_loat` **5,0 lượt/video** ->
  **+3,5 đến +4,7 lần** ngân sách LLM của đường thay tiếng. Hai tính năng đã bị
  bác bằng đúng cột này (`dich_va_soat` 10,9x · `dich_theo_gio` 2,46x với trần
  1,5x) — nhưng KHÁC ở chỗ hai cái đó đo ra chất lượng KHÔNG tăng, còn cái này
  có ích lợi thật. Nên đây là con số để anh Hùng quyết, không phải cửa tự đóng.
  (3) **ĐƯỜNG RẺ (0 lượt Groq) HIỆN KHÔNG CHẠY ĐƯỢC:** `cham_giong` (ECAPA, đo
  được bỏ sót **0/573**) cần `speechbrain`, mà nó KHÔNG có trong `_lib` lẫn
  `.venv`, và `_kq_nn/sb` không còn trên đĩa. `cham_phu_de` thì tự nó là thứ
  đã dùng để DỰNG bộ đối chứng nên không được tự chấm điểm.
  (4) **NGỮ NGHĨA "GIỮ GỐC" CHƯA CÓ CHỖ ĐẶT:** docstring đòi *"không tách,
  không trộn lại"*, nhưng cách nối rẻ nhất hôm nay (bỏ lồng tiếng rồi để
  `bu_giong_goc` lấp) cho ra **giọng gốc khớp mức TTS + nhạc đã bị hạ/ducking**
  — với một cảnh phim thì lớp nhạc của cảnh đó lẽ ra phải còn nguyên. Muốn đúng
  nghĩa phải cho đường trộn **chừa cửa sổ đó ra**, đó là sửa chuỗi trộn chứ
  không phải một cái hook 10 dòng.
  **CÒN NỢ:** ca PHA (3,0 s nhạc phim + 2,7 s người kể trong CÙNG một đoạn
  whisper) = 100% số ca lồng oan còn lại. `cat_theo_tu` đã có và chữa được ca
  `v1_dutu`, nhưng `v2_nieu` thì whisper gán từ từ giây 0,00 nên cắt theo mốc
  từ KHÔNG đổi gì. Hướng chưa thử: dò trong LÒNG một đoạn bằng **đường bao lớp
  giọng Demucs** (`duong_bao_muc` trên `t["giong"]`, đúng thứ `bu_giong_goc`
  đang dùng) — chỗ stem im mà whisper vẫn ra chữ là chỗ nó nghe nhầm nhạc
  thành lời. Chưa đo, đừng ghi là đã biết cách.
- **NHẠC NỀN "DÌM 10,46 dB": ĐO LẠI RA `0,00 dB` TRÊN NGUỒN ANH HÙNG ĐANG LÀM,
  VÀ Ở CA NÓ CÓ CẮN THÌ CỨU ĐƯỢC (19/08/2026, `_do_nhac_dai.py`).**
  **10,46 dB KHÔNG PHẢI HẰNG SỐ CỦA APP.** `can_bang_giong_nhac` ĐO rồi mới
  tính, và trên 2 video vừa chạy dây chuyền thật nó ra `gain_nhac_db =
  **0,00 dB**` ở CẢ HAI: lớp nhạc sau khi tách đã nằm DƯỚI giọng TTS
  **+9,28 dB** (video 1) và **+13,43 dB** (video 4), cao hơn đích
  `DICH_GIONG_TREN_NHAC_DB` = 6 nên hàm không hạ nhạc một dB nào. Con số
  −10,46 dB là của MỘT nguồn khác (nhạc CAO HƠN giọng 10,61 dB). Tức trên nguồn
  anh Hùng đang làm hôm nay **không có gì để cứu**; phần hạ duy nhất là
  ducking, mà ducking chỉ áp lúc đang nói.
  **NHƯNG Ở CA NÓ CÓ CẮN THÌ CỨU ĐƯỢC, và đây là số.** Ép `g_nhac` về trần
  `HA_NHAC_TOI_DA_DB` = −8 dB trên stem THẬT rồi so 17 arm (hai thước độ to
  độc lập, lệch 0,02-0,33 LU — đều dưới 0,5):

  | arm | nhạc trong DẢI LỜI lúc nói | SNR dải | nhạc lúc IM | **I lớp nhạc** |
  |---|---|---|---|---|
  | GỐC | −44,64 | 16,66 | −32,60 | −21,50 |
  | **A = hiện tại** (hạ CẢ DẢI + né cả dải) | **−59,19** | **31,21** | −43,76 | **−28,60** |
  | B (né chỉ dải lời 300-3400) | −54,14 | 26,16 | −33,62 | −21,50 |
  | **F6** (dải lời, tĩnh −4, ratio 6) | −58,19 | 30,21 | −33,63 | **−21,30** |
  | **F9** (dải lời, tĩnh −4, ratio 9) | −58,46 | 30,48 | −33,63 | **−21,30** |

  **F9 giữ được 6,90 LU nhạc (−0,20 thay vì −7,10) và nhạc lúc IM cao hơn
  10,13 dB, đổi lấy 0,73 dB SNR dải lời — trên một SNR đã 31 dB.** 0,73 dB ở
  mức 31 dB không có hệ quả nghe được nào.
  **ĐỐI CHỨNG KIẾN TRÚC BẮT BUỘC PHẢI CÓ (arm D):** cắt 3 dải bằng
  `acrossover=split=300 3400:order=4th` rồi cộng lại NGUYÊN (gain 0) phải ra
  GIỐNG lớp nhạc gốc — đo **dI +0,00 LU · dải lời +0,00 dB · IM +0,03 dB**.
  Không có arm này thì mọi số của B/C/F là số của phép cắt dải, không phải của
  ý tưởng.
  **CHƯA LÀM, GHI THẲNG:** chưa nối vào `tron_thay_giong` · **chưa ai NGHE** —
  hạ riêng dải giữa có thể ra tiếng "rỗng ruột" mà không thước nào ở trên bắt
  được · cột `IM` chỉ có 51 cửa sổ và `IM XA LỜI` chỉ **12 cửa sổ = 2,4 s**
  (video này 93% là lời) nên hai cột đó YẾU; cột đứng vững là **I (LUFS) cả
  file**. Bảng `ratio` phải QUÉT LẠI nếu đổi mức nhạc, đừng suy từ công thức
  (`_do_hieu_chuan_duck.py` đã sai 6 dB vì tính từ công thức nén).
- **GIỌNG MỚI BỊ NHẠC NỀN DÌM 9,3 dB — "chỗ có chỗ không nghe không được"
  (15/08/2026).** Anh Hùng: *"phần tách âm thanh giọng nói, nó nói mà âm thanh
  sau khi tách lỗi hết, chỗ có chỗ không nghe không được"*.
  **BA GIẢ THUYẾT ĐẦU TIÊN ĐỀU SAI — ghi thẳng để đừng ai đi lại đường đó.**
  Chạy `tach_giong(cach="demucs")` THẬT trên video anh Hùng gửi: lớp NHẠC im
  trong khi gốc có tiếng **0 cửa sổ / 0,00 s / 0,0% video**; bảo toàn năng
  lượng `căn(nhạc²+giọng²)` lệch gốc **−0,18 dB**; **không có chu kỳ mất tiếng
  nào** -> KHÔNG phải ranh giới đoạn Demucs, KHÔNG phải chết giữa chừng, KHÔNG
  phải ghép sai. Và bản anh Hùng đã xuất cũng **0,0 s im hẳn / 0,0 s tụt quá
  20 dB** — *"chỗ có chỗ không"* KHÔNG phải im lặng.
  **CHỖ HỎNG THẬT: bước TRỘN dùng HAI HẰNG SỐ đặt mò** `muc_giong_db=0` /
  `muc_nhac_db=-2`, tức giả định lớp nhạc và giọng TTS vốn đã ngang nhau. Đo:

  | | GỐC (Trung) | BẢN THAY TIẾNG |
  |---|---|---|
  | nhạc lúc đang nói | −12,1 dBFS | −11,4 dBFS |
  | giọng lúc đang nói | −8,8 dBFS | **−20,6 dBFS** |
  | **GIỌNG TRÊN NHẠC** | **+3,35 dB** | **−9,27 dB** |
  | cửa sổ giọng chìm dưới nhạc | 8,7% | **93,5%** |

  Nghe ra tiếng ở chỗ nào nhạc tình cờ lặng xuống = đúng chữ *"chỗ có chỗ
  không"*. **PHẢI ĐO LÚC ĐANG NÓI, không phải RMS cả track** — track giọng
  ~30% là im lặng nên RMS toàn bài thấp giả tạo (cùng bài học "nền đo bằng
  `mean_volume`" của nhóm tiếng động).
  **CHỮA:** `duong_bao_muc` + `can_bang_giong_nhac` (đo 2 lớp theo cửa sổ
  0,2 s) -> `nen_lop_giong` -> **ĐO LẠI** -> nâng giọng/hạ nhạc -> nhạc NÉ
  giọng bằng `sidechaincompress`. SỐ SAU: giọng trên nhạc **−7,32 -> +5,99
  dB**, cửa sổ chìm **90,1% -> 7,9%**, đỉnh nhánh giọng đúng trần **−3,00
  dBFS**, chạm trần bản trộn **36 -> 1 mẫu**.
  **GIÁ PHẢI TRẢ, GHI THẲNG:** nhạc nền mất **−10,46 dB** (cũ −2,00) và bản
  trộn nhỏ tiếng hơn **3,8 dB**. Không thể vừa giữ nguyên nhạc vừa nghe rõ lời
  khi nguồn đã master **đỉnh 0,0 dBFS** — không còn chỗ trống nào để thêm
  tiếng vào (đúng ca "BẤT KHẢ THI" đã ghi ở nhóm tiếng động).
  **BỐN BẪY ĐO ĐÃ SẬP TRONG ĐÚNG VIỆC NÀY — mỗi cái một dạng "tự tin vào số
  mình suy ra":**
  · **đỉnh lấy từ đường bao RMS** ra −15,9 dBFS trong khi đỉnh THẬT (`astats
    Peak level`) là **−5,33** — hụt **10,6 dB**. Nâng +12 dB theo số hụt đó
    đẩy lớp giọng lên **+6,67 dBFS**, `alimiter` phải gọt 7,7 dB NGAY TRÊN
    TIẾNG NÓI (chạm trần 36 -> **1.577 mẫu**).
  · **suy ra đỉnh-sau-nén bằng công thức nén** ra −13,54 dBFS, đo thật
    **−2,99** — lệch 10,6 dB, vì `attack=5ms` CHO LỌT đúng những phụ âm bật
    tạo ra đỉnh. Nay nén ra FILE RIÊNG rồi ĐO LẠI (2 vòng đo, không phải 1).
  · **`ratio` của `sidechaincompress` KHÔNG phải số dB tụt xuống.** Đặt đích
    tụt 4 dB bằng công thức -> đo ra nhạc mất **10,42 dB**, giọng vọt
    **+15,48 dB** (đích 10,0). Nay quét thật: ratio **1,3 -> −3,28 dB** · 1,6
    -> −4,79 · 2,0 -> −5,75 · 3,0 -> −6,64. `DUCK_RATIO` là **hằng số ĐÃ ĐO**,
    muốn đổi thì chạy lại bảng, đừng suy từ công thức.
  · **quét 12 tổ hợp tham số nén ra CẢ 12 đều +5,55..+5,99 dB** — nén sâu hơn
    thì vừa hạ đỉnh (được nâng nhiều hơn) vừa hạ luôn mức lời (phải nâng nhiều
    hơn), triệt tiêu nhau. **Không có gì để "tối ưu" ở hai số đó**; cái chặn
    thật là trần đỉnh và trần hạ nhạc, và đó là đánh đổi với NHẠC NỀN.
  **`asplit` LÀM ĐỘ DÀI ĐẦU RA KHÔNG TIỀN ĐỊNH — lỗi thật, `kiem_video_ra`
  bắt được.** Lấy tín hiệu khoá cho `sidechaincompress` bằng
  `[gi]asplit=2[gi1][gikey]` rồi một nhánh vào bộ nén một nhánh vào
  `amix=duration=first`: hai nhánh bị tiêu thụ ở NHỊP KHÁC NHAU nên EOF lan
  tới `amix` sớm muộn tuỳ lượt. Chạy 3 lượt CÙNG một lệnh cùng file ra
  **107,183 · 107,254 · 107,183 giây** (dây chuyền thật: **106,162** ->
  `kiem_video_ra` ném *"lệch 1,093s"* và DỪNG trước khi đụng video gốc). rc=0,
  không một dòng báo. CHỮA 2 lớp: mở CHÍNH FILE ĐÓ thêm một `-i` thứ ba (bỏ
  nhánh dùng chung) + ép `apad,atrim=0:<tổng>` rồi `probe_duration` kiểm lại,
  lệch quá 0,05 s thì NÉM. Đo lại **5/5 lượt ra đúng 107,253991**.
- **BỎ ÉP NHANH (`atempo`) — CHỮA TẬN GỐC "NÓI KHÔNG MƯỢT" (v2.27.0,
  14/08/2026).** Anh Hùng nghe thật và báo *"phần sub thoại giọng lồng tiếng
  cảm giác KHÔNG KHỚP, KHÔNG MƯỢT, nói còn nhiều lỗi"*. Cổng 53/55 chỉ có MỘT
  con số `tempo_max` và lượt nào cũng **sát trần 1,5**.
  **GỐC RỄ ĐO ĐƯỢC (`_do_le_im.py`, `silencedetect` trên chính file edge-tts
  trả về): edge-tts chèn ~0,20 s im ở ĐẦU và ~0,87 s im ở CUỐI MỖI CÂU**, bất
  kể câu dài hay ngắn. Câu dịch 12 ký tự: file **1,848 s** nhưng tiếng THẬT chỉ
  **0,762 s = 58% file là im lặng**. App cũ đo độ dài bằng `probe_duration`
  (TÍNH CẢ LỀ IM) rồi ép `atempo` cho lọt khung -> **ép méo TIẾNG NÓI THẬT chỉ
  để nén KHOẢNG IM**. `atempo` là WSOLA (cắt sóng, dán chồng), đo được **5,357
  dB méo phổ ở 1,20 · 6,765 ở 1,50 · 8,071 ở 1,80** — đúng cái tai nghe ra.
  **BỐN BƯỚC CHỮA, theo thứ tự (đừng đổi):** cắt lề im TRƯỚC khi đo khung
  (`cat_le_loat`, giữ 0,04 s đầu / 0,08 s cuối cho khỏi cụt phụ âm) -> rút NGẮN
  CHỮ theo NGÂN SÁCH KÝ TỰ đo được -> **ĐỌC NHANH bằng `rate` của edge-tts**
  (mô hình tự đọc nhanh, KHÔNG có phép cắt-dán nào nên méo = 0 theo cấu tạo;
  đo `+5% -> 1,046× · +20% -> 1,190 · +50% -> 1,455`, WER không xấu đi) ->
  mượn khoảng lặng -> `atempo` chỉ còn là chốt cuối.
  **BẢNG SỐ — 3 LƯỢT, 2 NGUỒN (LLM KHÔNG TIỀN ĐỊNH, chạy 1 lượt rồi báo là tự
  lừa mình: đã gặp 0% vs 39,1%):**

  | nguồn zh (Douyin 90 s, 43-44 câu, Trung -> Anh) | cũ (lượt 1/2/3) | **v2.27.0 (lượt 1/2/3)** |
  |---|---|---|
  | câu chạm trần 1,5 | 26,8% · 23,3% · 31,7% | **0,0% · 0,0% · 0,0%** |
  | câu vượt 1,30 | 46,3% · 39,5% · 51,2% | **0,0% · 0,0% · 0,0%** |
  | chồng lấn | 574 ms/14 câu · 561/10 · 574/15 | **0 ms / 0 câu (cả 3)** |
  | `tempo_max` | 1,467 · 1,485 · 1,500 | **1,017 · 1,027 · 1,017** |

  Nguồn `en` (19 câu, Anh -> Việt): **0,0% ở MỌI bậc cả 3 lượt**, chồng lấn
  **0 ms**, `tempo_max` **1,002 · 1,000 · 1,000**. Tức **CHỒNG LẤN 0 ms là BẤT
  BIẾN, 6/6 lượt trên 2 nguồn** — không phải may. Lề im cắt được: zh bỏ
  **41,8-42,8 s / 125-129 s** file TTS (33%), en bỏ **18,9 s / 67,7-69,3 s**.
  **RÚT GỌN CÓ LÀM MẤT NGHĨA KHÔNG — CÓ, VÀ ĐÂY LÀ SỐ.** `dich_hau_kiem` chỉ
  chấm bản dịch ĐẦU; bước rút gọn sửa chữ SAU đó nên phải chấm LẠI bản CUỐI
  bằng chính phép dịch-ngược. **BẮT BUỘC có cột ĐỐI CHỨNG "câu KHÔNG bị đổi
  chữ"**: bộ chấm là LLM và nó chấm cả LOẠT, đổi 15 câu là đổi luôn ngữ cảnh
  của 28 câu còn lại — không trừ nhiễu đó ra thì không phân biệt được "rút gọn
  làm mất nghĩa" với "bộ chấm nhấp nháy". Nguồn zh:

  | lượt | câu bị đổi chữ | riêng câu BỊ ĐỔI | nhiễu (câu giữ nguyên) | **TỤT THẬT** |
  |---|---|---|---|---|
  | 1 | 15 | 7,00 -> 6,20 | −0,20 | **−0,60** |
  | 2 | 16 | 7,38 -> 5,31 | −0,83 | **−1,24** |
  | 3 | 12 | 7,00 -> 6,33 | −0,09 | **−0,58** |

  Ví dụ thật: *"Boss Johnny got out of the car immediately"* -> *"Johnny got
  out of the car"* (mất "Boss" và "immediately", chấm 4,0). Nguồn en chỉ 2 câu
  bị đổi nên số ra nhiễu hẳn (+0,18 · +2,21 · −1,68) — **2 điểm dữ liệu không
  kết luận được gì, ghi ra để khỏi ai đọc nhầm là "tiếng Anh không mất nghĩa"**.
  **VÌ SAO `NGUONG_RUT_GON` LÀ 1,38 CHỨ KHÔNG PHẢI 1,30, VÀ `RUT_GON_HE_SO`
  LỚN HƠN 1:** đặt ngưỡng 1,30 + ngân sách nhắm thẳng khung (hệ số 0,92) thì
  bản dịch bị chặt tới mức MẤT NGHĨA — chấm lại ra **7,19 -> 2,38 · 7,00 ->
  4,89 · 7,00 -> 2,00**. Từ khi có bước ĐỌC NHANH, phần dôi tới ~1,45 lần khung
  đã được `rate` nuốt gọn mà không méo tiếng, không mất chữ, nên rút gọn chỉ
  phải lo phần vượt QUÁ tầm với của `rate`. **Ép nhanh làm xấu TIẾNG, chặt chữ
  làm xấu NỘI DUNG — cái sau tệ hơn, và trước đó không ai đo.**
- **"CHỖ CHẬM CHỖ NHANH" *KHÔNG* PHẢI DO ÉP TIẾNG — TRUY RA LÀ BƯỚC 4C.
  KÈM MỘT LỖI THẬT ĐÃ VÁ VÀ CỔNG 89 (20/08/2026).** Anh Hùng: *"cái phần âm
  thanh lồng tiếng nhanh chậm để khớp khung hình à nó nói cực kỳ chậm chỗ thì
  nhanh tôi muốn nó đều hoặc hơi nhanh tí ... điều chỉnh là điều chỉnh VIDEO
  sao cho khớp, KHÔNG PHẢI lồng tiếng mới tạo"*.
  **ĐỌC MỤC NÀY TRƯỚC KHI ĐI SỬA `khop_thoi_gian`/`atempo` LẦN NỮA.**
  **(1) TÍNH NĂNG ANH ẤY XIN ĐÃ CÓ SẴN TỪ 18/08/2026** (commit `063da74`,
  `he_so_hinh`): combo *"Khớp tiếng với hình"* trong hộp Thay giọng, mục thứ
  hai *"Chỉnh video theo giọng (tiếng đều, khuyên dùng)"*. Nó **KHÔNG** đi qua
  `dub_stretch`/`export_canvas_clip` (đường thay giọng không cắt clip) mà có
  cơ chế RIÊNG: `he_so_hinh_can` -> `tran_hinh_theo_fps` -> `khop_thoi_gian
  (he_so_hinh=k)` -> `-itsscale` ở `thay_audio_video`. Mặc định vẫn là cách
  CŨ; cờ chỉ vào hash khi BẬT và nối vào ĐUÔI `sig` (`:htg=1`).
  **(2) LỖI THẬT ĐÃ VÁ — HỘP CHE CHỮ TRÔI.** Nhánh CHE CHỮ có filter, và
  `-itsscale` giãn mốc ĐẦU VÀO nên biến `t` trong `enable='between(t,a,b)'`
  là mốc ĐÃ GIÃN còn `a,b` do `che_chu.loc_cho_xuat` dò trên video GỐC thì
  CHƯA GIÃN -> hộp che trôi `(k−1)·t`, **lệch càng xa về cuối phim** (chữ ở
  giây 80 với k=1,2 thì lệch **16 GIÂY**). Chú thích trong mã khẳng định
  NGƯỢC LẠI nên chưa ai đo. `_do_hop_che_troi.py` đo ĐIỂM ẢNH trên file xuất
  (dải TRẮNG ở đáy chỉ hiện trong một cửa sổ BIẾT TRƯỚC): đối chứng k=1,0 ->
  **128** (che kín) · `-itsscale 1,25` -> **255 (lọt nguyên)** · `setpts` sau
  khối che -> **128**; số khung **240 -> 240 ở cả ba**.
  **VÁ:** nhánh che chữ bỏ `-itsscale`, đặt `setpts=PTS*k` **SAU khối che,
  TRƯỚC `subtitles`** — thứ tự LÀ cả bản vá: trước `setpts` thì `t` = mốc
  NGUỒN (khối che đọc đúng), sau `setpts` thì `t` = mốc ĐẦU RA (`.ass` dựng
  từ `moc_tieng` vốn đã nhân `k`). Đúng thứ tự `export_canvas_clip` dùng, và
  nhánh này VỐN ĐÃ encode lại hình nên `setpts` không thêm đời nén nào.
  **(3) ĐO GHÉP CẶP TRÊN VIDEO THẬT (`_do_khop_video.py`, nguồn
  `Downloads\longtieng`, Demucs + Groq + edge-tts THẬT, dịch Trung -> Việt).**
  Một lượt dây chuyền/video tới hết bước 4c rồi TÁCH arm ở đúng tham số
  `he_so_hinh` -> hai arm cùng bản tách/chép lời/dịch/FILE GIỌNG:

  | | lt1 CŨ | lt1 MỚI | lt2 CŨ | lt2 MỚI |
  |---|---|---|---|---|
  | `tempo_max` | 1,030 | **1,000** | 1,276 | **1,065** |
  | câu ép quá 1,30 | 0 | 0 | 0 | 0 |
  | câu ép quá 1,20 | 0 | 0 | 2 | **0** |
  | TRẢI hệ số ép | 0,030 | **0,000** | 0,276 | **0,065** |
  | méo phổ TB / max (dB) | 0,129 / 2,201 | **0 / 0** | 0,458 / 4,904 | 0,103 / 3,003 |
  | chồng lấn | 0 ms / 0 câu | 0 ms / 0 câu | 0 ms / 0 câu | 0 ms / 0 câu |
  | hệ số làm chậm hình | 1,000 | 1,123 | 1,000 | 1,199 (CHẠM TRẦN) |
  | khung vào -> ra | 2161 -> 2151 | 2161 -> 2151 | 2161 -> 2152 | 2161 -> 2152 |
  | I (LUFS) | −14,37 | −14,37 | −14,00 | −14,01 |

  **NÓI THẲNG: arm CŨ ĐÃ GẦN NHƯ ĐỀU RỒI** (`tempo_max` 1,030 và 1,276 · **0
  câu** vượt 1,30 · chồng lấn 0 ms) — khớp mốc v2.27.0 đã ghi (1,017-1,027).
  Tức chiều "ép tiếng" **KHÔNG còn là thủ phạm**, và nếu chỉ đọc `tempo_max`
  thì sẽ kết luận "không có gì để chữa". Đó là kết luận SAI, xem (4).
  **(4) THƯỚC TỐ GIÁC ĐƯỢC LÀ *TRẢI TỐC ĐỘ ĐỌC GIỮA CÁC CÂU*, và nó chỉ ra
  bước 4C.** `tempo_max` là số ĐỈNH, nó không nói gì về ĐỘ ĐỀU. Thước mới:
  **ký tự/giây của TỪNG CÂU** đo trên mốc NÓI THẬT (`moc_tieng`,
  `silencedetect` — KHÔNG dùng `probe_duration`, nó tính cả lề im), rồi lấy
  độ lệch chuẩn + hệ số biến thiên. **BẮT BUỘC có SÀN ĐỐI CHỨNG** đo trên
  file TTS THÔ, hai arm dùng chung:

  | | SÀN (TTS thô) | arm CŨ | arm MỚI |
  |---|---|---|---|
  | lt1 · CV % | 20,48 | 20,45 | 20,49 |
  | lt2 · CV % | 14,83 | 14,04 | 14,62 |

  **BA CỘT BẰNG NHAU** -> phần "chỗ chậm chỗ nhanh" **ĐÃ NẰM SẴN trong bộ file
  TTS**, không do `atempo` sinh ra, và **arm MỚI không chữa được nó** (còn hơi
  xấu hơn: 14,04 -> 14,62, vì `atempo` của arm CŨ tình cờ ép nhanh đúng mấy
  câu đọc chậm nên làm tốc độ ĐỀU hơn một chút — đổi lại là méo phổ).
  **NGUỒN LÀ BƯỚC 4C `doc_nhanh_vua_khung`**: nó đọc LẠI **22/35** câu (lt1)
  và **33/50** câu (lt2) bằng `rate` của edge-tts, **mỗi câu một tốc độ khác
  nhau, tới +43% và +50%**. Đó đúng là *"chỗ cực kỳ chậm chỗ thì nhanh"*.
  Bước này méo phổ = 0 theo cấu tạo (đúng như v2.27.0 ghi) nên nó **chưa bao
  giờ bị nghi** — mà cái nó phá là ĐỘ ĐỀU, không phải chất tiếng.
  Arm MỚI không chữa vì `he_so_hinh_can` tính **SAU** 4c: nó chỉ đi khớp hình
  với một bộ tiếng ĐÃ nhấp nhô.
  **(5) ARM THỨ BA CHỨNG MINH ĐIỀU ĐÓ BẰNG SỐ** — khớp video + **BỎ bước 4c**
  (khớp với `rg["files"]`, tốc độ TỰ NHIÊN), ghép cặp trên lt2, 50 câu:

  | | CŨ | MỚI | **MỚI-3 (bỏ 4c)** |
  |---|---|---|---|
  | ký tự/giây TB | 20,68 | 20,64 | **18,32** |
  | **độ lệch chuẩn** | 2,945 | 2,949 | **1,788** |
  | **hệ số biến thiên %** | 14,24 | 14,29 | **9,76** |
  | `tempo_max` | 1,029 | 1,000 | 1,236 |
  | méo phổ TB / max (dB) | 0,194 / 2,189 | 0 / 0 | 0,842 / 4,594 |
  | hệ số hình cần -> dùng | — | 1,152 -> 1,152 | **1,606 -> 1,199 (CHẠM TRẦN)** |

  **TRẢI TỤT 31,5%** (CV 14,29 -> 9,76 · SD 2,949 -> 1,788) và tốc độ đọc TB
  chậm lại 11% (20,64 -> 18,32 ký tự/giây) = **"nói đều" đúng nghĩa**.
  **GIÁ, nói thẳng:** bỏ 4c thì hệ số hình cần **1,606** mà trần của nguồn
  23,976 fps chỉ **1,199**, nên phần dư quay lại ép tiếng (`tempo_max` 1,236 ·
  méo phổ 0,842 dB TB). Tức đây là ĐÁNH ĐỔI, không phải bữa trưa miễn phí, và
  **trần mới là chỗ bị chặn** — không phải thuật toán.
  **(6) TRẦN LÀM CHẬM HÌNH: 1,199 cho nguồn 23,976 fps, và nó ĐO ĐƯỢC.**
  `SAN_NHIP_HINH_FPS = 20` · `TRAN_CHINH_HINH = 1,25`. `-itsscale` KHÔNG sinh
  khung mới nên nhịp hình tụt đúng theo hệ số. Cổng 89 mục 8 đo trên file
  xuất: theo trần -> **20,03 fps** (đủ sàn) · gỡ trần (k=2,553) -> **9,46
  fps** = hình vỡ. Đo `số khung / độ dài`, **KHÔNG đọc `do_fps`** — nó lấy
  nhịp hình trong VỎ CHỨA nên ở k=2,55 ra **47,00 fps** (cao HƠN nguồn 24!),
  đúng họ bẫy "phép đo hỏng phát chứng nhận". Quá trần thì `cham_tran=True` +
  `nhip_hinh_con_lai_fps` vào nhật ký — **lùi im lặng là bẫy repo này chống**.
  **(7) GIÁ CÒN LẠI CỦA "KHỚP VIDEO", đo được:** video dài ra `(k−1)·tổng`
  (90,03 -> 100,77 s ở lt1) và **gần như toàn bộ phần thêm là IM LẶNG giữa
  câu** — cột *"chữ chạy khi hết tiếng"* 7,70 -> 17,98 s (lt1) và 10,77 ->
  27,77 s (lt2), tức làm chậm ĐỀU thì giãn cả khoảng lặng. Đây **KHÔNG phải
  chữ lệch tiếng** (`dong_chu_theo_giong` dựng cue TỪ `moc_tieng`), nó là
  nhịp phim thưa ra. Cột *"lệch hình vs tiếng"* 269-354 ms có ở **CẢ HAI arm**
  nên không do bản vá — đó là chênh `duration` giữa luồng hình (`-c:v copy`,
  dừng ở khung cuối) và luồng tiếng; `kiem_video_ra` đo `lech_do_dai = 0,0` ở
  **cả 3 arm**. Khung **2161 -> 2151/2152 ở MỌI arm** (mất 10 khung do
  `-shortest`, không do phép giãn).
  **(8) CỔNG 89 `_test_am_va_hinh.py`: ĐẠT 75 · HỎNG 0.** Thử phá
  `_pha_khop_video.py` (9 phép): **BẮT 9 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0**.
  File này **TRƯỚC ĐÂY tự nhận là "CỔNG 76" và KHÔNG nằm trong
  `_chay_hoi_quy.CONG`** — hai bẫy chồng nhau: 76 đã thuộc
  `_test_nhan_nha.py` (ghi đè `_kq76.txt` của nhau, bài học 70 vs 69) và
  không ai gọi nó nên **nó đã CHẾT mà không ai biết** (`nhan_nha.muc()` đổi
  chữ ký, MỤC 6 cũ gọi `muc(voice, nn)` -> `TypeError` giữa chừng). MỤC 6 cũ
  bỏ (4 hàm nó chấm không còn tồn tại; phần nhãn nhấn nhá đã có cổng 76 canh),
  thay bằng 3 mục mới: hộp che không trôi + phụ đề hiện đúng mốc trục ĐẦU RA
  (đặt [5,00 6,00] đo **[5,05 5,95]**) · TẮT cờ thì lệnh ffmpeg và khoá chống
  trùng GIỐNG TỪNG KÝ TỰ mốc **v2.37.0** · trần có RĂNG + lùi thì GHI LOG.
  **LƯỢT PHÁ ĐẦU RA `BẮT 8 · LỌT 1`, và cái LỌT là LỖ CỦA CỔNG** — đây là giá
  trị thật của phép thử phá: gỡ phép nhân `k` khỏi mốc ĐẦU câu
  (`a = c["start"] * k` -> `a = c["start"]`) thì `khung = b − a` **PHỒNG hơn
  cả `k`** (vì `b` vẫn giãn) nên câu nào cũng lọt khung, `tempo_max` vẫn
  1,000, mọi mục cũ vẫn XANH — trong khi tiếng bị đặt ở mốc CHƯA GIÃN của một
  video ĐÃ GIÃN, tức **tiếng trôi khỏi hình mỗi lúc một xa**, đúng lỗi v1.87.
  Nay cổng chấm THẲNG chỗ đặt mảnh (`manh[i][0]` phải bằng `start * k`) + có
  mục ĐỐI CHỨNG k=1,0. **Quy tắc rút ra: mục nào chấm "hệ số ép về 1,0" thì
  phải chấm KÈM "mốc đặt câu giãn đúng hệ số" — một mình cột tempo có thể
  xanh vì khung phồng, không vì tiếng đúng chỗ.**
  **(9) FILE NGHE THỬ:** `_NGHE_THU_ANH_HUNG/khop_video/lt1/` (`CU_` ·
  `MOI_`) và `lt2/` (`CU_` · `MOI_` · `MOI3_`) — mỗi bộ từ **CÙNG MỘT lượt
  chạy**, đã chuẩn hoá cùng **−14 LUFS** bằng chính `chuan_do_to` trong
  `tron_thay_giong` (không chuẩn hoá thì phép nghe thành "file nào TO hơn").
  **Tai anh Hùng là phán quyết cuối** — mọi số trên là số ĐO.
  **(10) CHƯA LÀM, GHI THẲNG:** **chưa ai NGHE** một file nào ·
  **arm MỚI-3 (bỏ 4c) CHƯA NỐI VÀO APP** — nối được thì phải chọn giữa "nới
  trần" (đã đo là hình vỡ) và "chấp nhận ép lại phần dư", đó là quyết định
  của anh Hùng, không phải của tôi · **KHÔNG có ô cho anh Hùng CHỌN TỐC ĐỘ
  ĐỌC** (anh ấy xin *"đều hoặc hơi nhanh tí"*): `RATE_TOI_DA`/`RATE_BU` là
  hằng số trong mã, `doc_nhanh_vua_khung` chỉ bắn khi câu tràn khung, và
  `grep` hộp Thay giọng ra **0 ô** nào về tốc độ đọc — muốn có thì thêm ô
  "đọc nhanh sẵn +N%" áp ở `doc_ban_dich` cho MỌI câu (đều theo cấu tạo) kèm
  đuôi `sig` riêng · mới đo **2 video × 90 s** (arm 3 chỉ **1 video**), chưa
  đo nguồn 30/60 fps (trần sẽ rộng hơn hẳn) · cột `giây chạy` của lượt này
  **KHÔNG đọc được** (máy có việc khác chạy nền giữa lượt đo).
  **(11) 25/08/2026 — MỤC (10) ĐÃ LÀM XONG PHẦN "NỐI VÀO APP", VÀ BƯỚC 4C
  HOÁ RA CÒN LÀ THỦ PHẠM CỦA LỜI KÊU THỨ HAI: *"tốc độ làm lồng tiếng cực kỳ
  chậm"*.** Cờ `thay_giong.doc_deu` + mục thứ BA trong combo *"Khớp tiếng với
  hình"* (`hinh_deu`, cửa duy nhất `chuan_khop_cach`). **MẶC ĐỊNH VẪN LÀ MỤC
  ĐẦU** (cách cũ); đuôi `sig` là `:dd=1` và nó **LỒNG TRONG nhánh `htg`** — cờ
  không có tác dụng khi chưa chỉnh hình thì không được đổi khoá, đúng bài học
  `chuan_muc_mo` cổng 56e. Đo: TẮT -> `dedup_key` **giống TỪNG KÝ TỰ** mốc
  v2.37.0 (cổng 89 mục 9g/9h).
  **ĐO GHÉP CẶP LẠI, 2 VIDEO THẬT × 90 s** (`_do_khop_video.py`, MỘT lượt
  chạy/video rồi tách 3 arm — 4a/4b dùng chung, arm 3 chỉ bớt đúng 4c):

  | | lt1 CŨ | lt1 MỚI | lt1 **ĐỀU** | lt2 CŨ | lt2 MỚI | lt2 **ĐỀU** |
  |---|---|---|---|---|---|---|
  | **GIÂY bước ĐỌC** | 479,41 | 479,41 | **295,76** | 442,37 | 442,37 | **265,52** |
  | hệ số biến thiên % | 20,11 | 20,77 | **15,64** | 14,08 | 14,26 | **10,88** |
  | độ lệch chuẩn | 4,155 | 4,249 | **2,804** | 2,859 | 2,877 | **1,962** |
  | `tempo_max` | 1,275 | 1,064 | 1,113 | 1,360 | 1,135 | 1,136 |
  | méo phổ TB (dB) | 0,329 | 0,145 | **1,026** | 0,312 | 0,082 | **0,680** |
  | câu ép quá 1,20 | 2 | 0 | 0 | 1 | 0 | 0 |
  | chữ chạy khi hết tiếng (s) | 7,72 | 24,77 | 14,87 | 10,44 | 27,33 | 19,06 |

  **NHANH HƠN BAO NHIÊU — cột chưa ai đo, nay đo rồi: bớt 183,65 s (38,31%)
  và 176,85 s (39,98%) của BƯỚC ĐỌC.** Chi tiết lt1: 4a đọc 163,02 s · 4b rút
  gọn 132,74 s · **4c đọc nhanh 183,65 s**; lt2: 205,56 · 59,97 · **176,85**.
  Tức **4c là bước ĐẮT NHẤT của cả khối đọc** (đắt hơn cả lượt đọc đầu ở lt1)
  — nó đọc lại 23/35 và 31/50 câu RỒI còn cắt lề im từng file. Suy luận thô
  ban đầu ("bớt ~40% việc đọc") **đúng**, nhưng đúng vì lý do khác: không phải
  "bớt 1 trong 2,5 lượt" mà vì lượt bị bỏ chính là lượt nặng nhất.
  **BẤT NGỜ, VÀ NÓ ĐỔI CÁCH ĐỌC BẢNG:** so với **MẶC ĐỊNH ĐANG CHẠY** (arm
  CŨ), đường ĐỀU vừa đều hơn (CV −22,2% và −22,7%) vừa **ÉP NHẸ HƠN**
  (`tempo_max` 1,275 -> 1,113 · 1,360 -> 1,136) vừa nhanh hơn ~39%. Cái nó
  thua arm CŨ chỉ có MỘT: **méo phổ TB 3,1x và 2,2x** — vì nó ép ÍT nhưng ép
  NHIỀU CÂU, còn arm CŨ ép NẶNG vài câu. Và video dài ra 19,9% (89,7 -> 107,5
  s) như mọi đường chỉnh hình.
  **GIÁ ĐÃ ĐỔI SO VỚI LƯỢT 20/08:** lần đó arm MỚI của lt1 **không** chạm
  trần (k_can 1,152); lượt này **CẢ BA cột đều CHẠM TRẦN** (arm MỚI cần
  1,341/1,5009 · arm ĐỀU cần **1,4675/1,5433**, trần vẫn 1,1988). Nguyên nhân
  là bản dịch của lượt này dài hơn — **LLM không tiền định, đó chính là lý do
  phải đo GHÉP CẶP**, và cũng là lý do KHÔNG được chép số cũ sang bảng mới.
  **CHƯA LÀM, GHI THẲNG:** **chưa ai NGHE** (tai anh Hùng vẫn là phán quyết
  cuối) · mẫu **2 video × 90 s, cùng nguồn Douyin 23,976 fps** — quá nhỏ để
  nói "luôn nhanh hơn 39%", và nguồn 30/60 fps chưa đo (trần rộng hơn hẳn nên
  giá sẽ RẺ hơn) · **giây bước đọc phụ thuộc MẠNG** (edge-tts + Groq), máy
  khác/giờ khác ra số khác — phần ghép cặp chỉ bảo đảm HIỆU hai cột, không
  bảo đảm số tuyệt đối · chưa đo trên đường ĐÈ GIỌNG (`de_giong=True`).
  Cổng 89: **75 -> 104 ĐẠT · 0 HỎNG** (mục 9 chạy THẬT `thay_giong_video` để
  chứng minh 4c chạy **0 lần**, không chỉ "mã có nhánh đó").
  **BẪY MỚI, ĐÃ SẬP TRONG CHÍNH LƯỢT NÀY — `QApplication` KHÔNG GIỮ THAM
  CHIẾU LÀM TIẾN TRÌNH CHẾT CỨNG, KHÔNG MỘT DÒNG BÁO.** MỤC 9 bản đầu viết
  `QApplication.instance() or QApplication([])` mà **không gán vào đâu cả**.
  `muc5` giữ app trong biến CỤC BỘ nên nó chết khi `muc5` trả về; tới MỤC 9
  `instance()` ra `None` -> tạo app mới -> Python thu hồi ngay dòng sau ->
  tiến trình tắt với **0xC0000409 (3221226505)**: KHÔNG traceback, KHÔNG dòng
  `KETQUA`, và chạy tay `_test_am_va_hinh.py` thì XANH 100 vì lúc đó chưa có
  mục 9z. Hệ quả: `_pha_khop_video.py` đọc lượt ĐỐI CHỨNG ra *"CỔNG ĐÃ ĐỎ
  TRƯỚC KHI PHÁ"* và **dừng cả 14 phép** — một lỗi của CỔNG giết cả lượt thử
  phá. Vá: `_APP` ở MỨC MODULE + hàm `app_qt()`, mọi mục dùng chung. Quy tắc:
  **cổng nào dựng UI thì QApplication phải sống ở mức module, không phải biến
  cục bộ của mục đầu tiên chạm tới nó.**
  **(12) "ĐƯỢC ĐOẠN RỒI NGHỈ, KHÔNG LIỀN MẠCH" (27/08/2026) — ĐÂY LÀ ĐÁNH ĐỔI
  CỦA CHÍNH Ô "CHỈNH VIDEO THEO GIỌNG", KHÔNG PHẢI BUG. ĐỌC TRƯỚC KHI ĐI VÁ.**
  Anh Hùng: *"nó nói còn KHÔNG LIÊN TIẾP, cứ ĐƯỢC ĐOẠN RỒI NGHỈ, KHÔNG LIỀN
  MẠCH, KHÔNG KHỚP gì cả"*. Mục (7) ở trên đã ghi *"gần như toàn bộ phần thêm
  là IM LẶNG giữa câu"* nhưng **chưa ai nối nó với lời kêu này**, và mọi thước
  cũ đo BÊN TRONG một câu hoặc đo TỪNG FILE WAV RỜI — mà file rời thì không có
  khoảng cách giữa câu để mà đo. Thước mới `_do_khop_video.im_giua_cau` đo trên
  `moc_tieng` (trục ĐẦU RA, `silencedetect` trên file đã ghi).
  **BỐN BẢN XUẤT THẬT ĐỀU CHẠM TRẦN, và đó là số quyết định** (`_do_im_giua_cau.py`,
  `Downloads\longtieng\xuất` CHỈ ĐỌC): `k` = **1,1987 · 1,1988 · 1,1987 ·
  1,2499** = ĐÚNG `fps_nguồn/20`; nhịp hình ra **20,002 · 20,000 · 20,001 ·
  20,000 fps**; **số khung KHÔNG ĐỔI** (3563->3563 · 8708->8708 · 7221->7221 ·
  9908->9908) -> hình chỉ bị GIÃN, video dài thêm **+29,53 · +72,19 · +59,84 ·
  +99,06 giây**.
  **IM ĐẾN TỪ ĐÂU — BA TẦNG, đo ghép cặp trên lt1 90 s** (`_do_gop_cau.py`):
  **(a) CỦA NGUỒN 0,00 s** (segment chép lời liền nhau; đối chứng độc lập: đo
  bao hình trên chính video GỐC ra khoảng im dài nhất chỉ **0,38-0,88 s**) ·
  **(b) bản dịch NGẮN HƠN khung câu: 8,42 s (9,35%)** · **(c) CHỈNH HÌNH:
  +17,42 s (19,35%)**. Đối chiếu: `(k−1)×90,02 = 17,90 s` vs phần im tăng
  **17,42 s** = **97,3% phần video dài thêm rơi VÀO KHOẢNG IM**.
  **GHÉP CẶP 3 ARM × 2 GIỌNG, MỘT bản dịch DÙNG CHUNG** (`_do_khop_video.py`,
  lt1 90,03 s / 35 câu, Trung -> Việt):

  | im GIỮA CÂU | CŨ | MỤC 2 (đang bật) | MỤC 3 (bỏ 4c) |
  |---|---|---|---|
  | **EDGE (TRẦN)** tổng · % · số >=0,5 s · dài nhất | 8,42 s · 9,35% · 2 · 1,27 s | 18,35 s · 18,29% · **15** · 2,00 s | 15,93 s · 14,76% · 10 · 2,54 s |
  | EDGE · tỉ lệ CÓ TIẾNG | **90,43%** | 81,24% | 85,11% |
  | **`vnb:` (ĐƯỜNG ANH HÙNG)** tổng · % · số >=0,5 s · dài nhất | 17,94 s · 19,93% · 8 · 3,69 s | **34,92 s · 32,36% · 30 · 4,96 s** | 31,12 s · 28,84% · 23 · 4,96 s |
  | `vnb:` · tỉ lệ CÓ TIẾNG | 79,70% | **66,89%** | 70,65% |
  | `vnb:` · hệ số hình cần -> dùng | — | 1,2556 -> **1,1988 CHẠM TRẦN** | 1,3275 -> 1,1988 |

  **HAI NGUYÊN NHÂN CHỒNG NHAU, phải tách ra mới chữa đúng chỗ:** (1) giọng
  NHÂN BẢN đọc NHANH hơn edge (**23,16 vs 20,62 ký tự/giây**) nên đọc xong sớm
  hơn trong khung câu CỐ ĐỊNH -> im **9,35% -> 19,93%** *ngay cả khi TẮT chỉnh
  hình*; (2) chỉnh hình đẩy tiếp **19,93% -> 32,36%**. Tức trên đường anh Hùng
  đang đi, **một phần ba thời lượng video là im giữa câu, 30 khoảng nghỉ
  >= 0,5 giây trong 90 giây, khoảng dài nhất 4,96 giây**.
  **GIÃN KHÔNG ĐỀU (giãn nhiều chỗ im, ít chỗ nói): LÀM ĐƯỢC, GẦN NHƯ MIỄN PHÍ,
  NHƯNG *KHÔNG NÊN* — ĐÃ ĐO** (`_do_gian_khong_deu.py`, nguồn Douyin thật
  24,15 s / 579 khung / 23,976 fps, k=1,1988):

  | arm | fps chỗ NÓI | fps chỗ IM | bước nhịp mỗi mối nối | giây | encode |
  |---|---|---|---|---|---|
  | ĐỀU + `-itsscale` (đang chạy) | 20,02 | 20,07 | 0,998 | 0,03 | KHÔNG |
  | ĐỀU + `setpts` (encode lại) | 19,92 | 20,20 | 0,986 | 2,39 | CÓ |
  | KHÔNG ĐỀU, dồn 50% vào chỗ im | 21,89 | **16,11** | 1,359 | 2,37 | CÓ |
  | KHÔNG ĐỀU, dồn 100% | 23,88 | **13,93** | 1,714 | 2,34 | CÓ |

  Độ dài + số khung ra **Y HỆT** ở cả 4 arm (28,946 s · 579 khung) nên phép
  giãn không đều là ĐÚNG, không phải hỏng. Cái chặn là **SÀN `SAN_NHIP_HINH_FPS
  = 20`**, và đây là **CHỨNG MINH SỐ HỌC, không phải sở thích**: trần
  `k_cap = fps_nguồn / 20`, giãn ĐỀU ở `k_cap` đưa CẢ phim về ĐÚNG 20 fps ->
  **mọi phép dồn thêm vào chỗ im đều đẩy chỗ đó XUỐNG DƯỚI 20 fps**, không có
  một chút chỗ trống nào. Mà 4/4 video anh Hùng đều ĐANG chạm trần. Cộng thêm
  **bước nhịp 1,36-1,71 lần tại MỖI mối nối** (~100+ lần/video với 103-184 câu)
  = đúng cái *"hình nhanh-chậm theo nhịp nói"*. **NÓI THẲNG: KHÔNG NÊN NỐI.**
  Ghi thêm cho người sau: giá ENCODE **không** phải lý do từ chối — 4/4 bản
  xuất là **h264 trong khi nguồn là hevc**, tức che chữ đang BẬT và nhánh che
  chữ **vốn đã `setpts` + encode lại**; đo được không đều chỉ tốn 2,37 s so với
  2,39 s của đều-encode = **0 chi phí thêm**.
  **GỘP CÂU NGẮN: KHÔNG ĐÁNG, VÀ CÁI CẦN GẠT KHÔNG TỒN TẠI.**
  `cau_tu_transcript(d, gop_toi_da)` **CHỈ CẮT NHỎ, KHÔNG BAO GIỜ GỘP** — gọi
  thật với `gop_toi_da` = 8 / 12 / 20 / 60 giây đều ra **35 câu**, và **0
  segment gốc dài quá 12 s**. Danh sách câu đi thẳng từ `segments` của Groq
  (đo trên job thật: **103-184 câu/video, TB 39 ký tự/câu**). Mô phỏng một bước
  gộp MỚI (trần ký tự 60/80/100/140, k=1,1988): tổng im **25,84 -> 25,84 ->
  25,84 -> 25,33 -> 22,05 s** = gần như **BẢO TOÀN**; nó chỉ đổi NHIỀU khoảng
  ngắn lấy VÀI khoảng RẤT DÀI — khoảng dài nhất **2,54 -> 8,57 giây**. Với lời
  kêu *"được đoạn rồi nghỉ"* thì đó là **đi lùi**. Mặt hại lo trước (`atempo`
  ép nhiều hơn) **KHÔNG xảy ra**: `tempo_max` = 1,000 ở MỌI trần, vì luật
  "mượn khoảng lặng" cho mỗi khối kéo tới sát khối kế.
  **CHỖ DUY NHẤT GẠT ĐƯỢC LÀ Ô COMBO** — xem phần "anh Hùng đổi ô nào thì hết"
  trong báo cáo: mục 1 (không chỉnh hình) đưa im về **19,93%** và tỉ lệ có
  tiếng lên **79,70%**, đổi lại `tempo_max` 1,000 -> 1,108 (vẫn dưới ngưỡng
  cảnh báo 1,30). Mục 3 chỉ bớt được **32,36% -> 28,84%**.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa ai NGHE** (file ở
  `_NGHE_THU_ANH_HUNG/lien_mach/`, 6 file, MD5 6/6 khác nhau) · mới **1 video ×
  90 s × 1 lượt/giọng**, mà đường `vnb:` KHÔNG tiền định nên đây là *một* điểm
  dữ liệu, không phải phân bố · mẫu nhân bản là `test.wav` (anh Hùng chạy 15
  lượt hôm 27/08) chứ không phải `adam_clone.wav` (14 lượt) — ranh giới pháp lý
  chặn · phép đo bao hình trên BẢN TRỘN CUỐI của 4 file thật **bị NHẠC NỀN che**
  nên cột im tuyệt đối ở đó KHÔNG đọc thẳng được (1/4 video còn ra HIỆU ÂM);
  cột đọc được của bảng A là `k` · nhịp hình · số khung.
  **(13) 28/08/2026 — BỐN LỜI KÊU SAU v2.47.0. HAI LỜI ĐẦU LÀ *MỘT* NGUYÊN
  NHÂN, LỜI 4 CHỈ CẦN ĐỔI Ô, LỜI 3 KHÔNG TÁI HIỆN.** Anh Hùng chạy thật 4 video
  sáng 28/08 rồi kêu: (1) *"giọng đọc KHÔNG LIỀN MẠCH"* · (2) *"vẫn DÍNH TIẾNG
  TRUNG âm thanh gốc"* · (3) *"dịch mấy đoạn lỗi quá"* · (4) *"nó CHỈNH TỐC ĐỘ
  GIỌNG ĐỌC chứ không phải tốc độ video"*.
  **CẤU HÌNH THẬT, ĐỌC TỪ REGISTRY + PAYLOAD JOB (không đoán theo ảnh):**
  `tg_giong=vnb:…test.wav` · `tg_tron_cach=tach` · `tg_khop_cach=hinh` (MỤC 2) ·
  che chữ + nhấn nhá BẬT · 2 luồng · **`dich_sang=vi`, KHÔNG phải `en`** — 4
  nguồn độc lập (sổ `thay_giong_so.json`, payload trong `studio.db-wal`,
  registry, và chữ THẬT được đọc lên) đều ra `vi`; sổ đó ghi được cả `en` (6
  job ngày 18/08) nên đây không phải giá trị mặc định.
  **LỜI 1 + LỜI 2 CHUNG MỘT GỐC: `bu_giong_goc` (bước 5c) LẤY CHÍNH GIỌNG GỐC
  TIẾNG TRUNG LẤP VÀO QUÃNG NGHỈ.** `bu_giong_goc_bat` mặc định **True**; vật
  liệu lấp là `t["giong"]` = lớp vocals Demucs của bản gốc. Chạy THẬT
  `thay_giong_video` trên chính video của anh Hùng, đúng cấu hình trên
  (`_do_bu_goc_that.py`, video 148,61 s -> 178,14 s):

  | arm | giây video | GIÂY BÙ | mảnh | % video | im nếu TẮT | k hình |
  |---|---|---|---|---|---|---|
  | **MỤC 2 + bù BẬT (ĐANG CHẠY)** | 178,14 | **25,57** | **31** | **14,35%** | 28,98 | 1,1988 |
  | MỤC 2 + bù TẮT | 173,46 | 0,00 | 0 | 0,00% | — | 1,1673 |
  | **MỤC 1 (không chỉnh hình)** | 148,61 | **4,40** | 4 | **2,96%** | 13,48 | — |
  | MỤC 3 (chỉnh hình + đọc ĐỀU) | 178,14 | 18,78 | 20 | 10,54% | 24,00 | 1,1988 |

  **THƯỚC DỨT ĐIỂM — CHÉP RIÊNG VẬT LIỆU BÙ, ĐỪNG CHÉP BẢN TRỘN.** Nối 31 mảnh
  bù thành một file rồi đưa Groq chép (tự nhận diện): nhãn **`Chinese`**,
  **131/140 ký tự Hán (93,6%)**. Ở đó không có mẩu giọng Việt nào lẫn vào nên
  whisper không có gì để bịa theo. Mốc 31 mảnh nằm ĐÚNG các quãng nghỉ giữa câu
  (`[11,03-14,43]` dài 3,40 s, `[21,61-22,68]`, `[29,21-30,28]`…) — tức **anh
  Hùng nghe thấy tiếng Trung Ở CHÍNH CHỖ anh ấy kêu "được đoạn rồi nghỉ". Một
  nguyên nhân, hai triệu chứng.**
  **ĐÂY LÀ ĐÁNH ĐỔI CỐ Ý, KHÔNG PHẢI BUG — nhưng nó ĐI NGƯỢC lựa chọn của
  người dùng.** Bù ra đời 18/08 để chữa *"đoạn không đọc thì bị TẮT TIẾNG"*;
  ghép cặp theo cấu tạo trong CÙNG lượt: **bật -> 25,57 s tiếng Trung · tắt ->
  28,98 s IM ở 32 chỗ**. Mà anh Hùng chọn *"Thay hẳn giọng (tách nhạc) — tiếng
  gốc MẤT HẲN"* (`cach_tron="tach"`), nên bù bằng chính tiếng gốc là làm ngược
  ô anh ấy bấm. **CHƯA VÁ** — phải để anh Hùng nghe rồi chọn, xem mục CHƯA LÀM.
  **HAI PHÉP ĐO CỦA CHÍNH LƯỢT NÀY ĐÃ HỎNG VÀ ĐƯỢC BẮT — cả hai đều thuộc họ
  "phép đo hỏng phát chứng nhận", ghi ra kẻo người sau đi lại:**
  **(a) CHÉP BẢN TRỘN ĐỂ ĐẾM TIẾNG TRUNG — HỎNG CẢ HAI CHIỀU** (`_do_tieng_
  trung_con.py`). Thả `language=None`: Groq chấm nhãn CHO CẢ FILE, bản trộn
  phần lớn là giọng Việt -> nhãn "Vietnamese" -> **0 ký tự Hán trên cả 4 video**
  = chứng nhận SẠCH hoàn toàn giả. Ép `language="zh"`: ra **85,72%**. Dựng SÀN
  BỊA bằng cặp sạch nhất có thể (`_do_thuoc_zh_san.py`, cùng video cùng lượt,
  khác đúng cờ bù): bản **KHÔNG có mẩu tiếng gốc nào** ra **94,99%**, bản **có
  25,57 s tiếng Trung thật** ra **99,53%** — **chênh 4,54 điểm %**. Thước MÙ,
  **85,72% là RÁC, đã gạch**. Đối chiếu với lời gốc không cứu được vì bản Việt
  vốn LÀ bản dịch của lời Trung nên chữ bịa vẫn "trùng" theo nghĩa.
  **(b) CỬA SỔ GHÉP CÂU-VỚI-LỜI-GỐC ÔM LẸM CÂU BÊN CẠNH** (`_do_dich_cua_anh_
  hung.ghep_goc`). Bản đầu hốt MỌI segment CHẠM `[bat_dau/k, ket_thuc/k]` với
  lề 0,35 s; mốc lệch chút ít nên cửa sổ gần như luôn ôm THÊM segment liền
  TRƯỚC. Bộ chấm đọc đoạn gốc HAI câu, thấy bản dịch MỘT câu, chấm *"bỏ sót"*
  -> **bản dịch ĐÚNG bị chấm 2 điểm**. Nó kéo theo 3 số sai: điểm 3,02/5 ·
  "23,33% lệch bậc" · arm TRẦN 4,88 (cao vì nó dịch CẢ cửa sổ hai câu). Sửa
  thành **lấy ĐÚNG MỘT segment có TÂM gần tâm câu nhất**, mọi số đảo ngược.
  **LỜI 3 — KHÔNG TÁI HIỆN. Đo trên chính 168 câu anh Hùng đã nghe** (moi từ
  `khop.moc_tu` trong `studio.db-wal`), chấm bằng `qwen/qwen3.8-27b` (KHÁC
  `GROQ_LLM_MODEL=openai/gpt-oss-120b` đã dịch), **có SÀN và TRẦN**:

  | | SÀN (ghép lệch 7 câu) | THẬT (anh Hùng) | TRẦN (model tự dịch) |
  |---|---|---|---|
  | điểm trung thành /5 | **1,00** | **4,67** | 4,87 |
  | câu <= 3 điểm | 100% | **6,67%** | 1,67% |

  Trên cả 168 câu: **4,56/5 · 9,52% câu <=3**. Lệch bậc **0,6%** (chrF đúng chỗ
  **33,58** vs lệch +1 **2,16** vs lệch -1 **2,16** — thước có RĂNG, khác hẳn
  bản cửa sổ hỏng vốn ra 18,65 vs 18,57 = mù). **Còn chữ Hán 0/168 câu**, khớp
  bản ghi job (`sot_chu_goc_truoc/sau = 0`) — và vì nhánh lùi `ra.get(i) or
  c["text"]` trả NGUYÊN VĂN tiếng Trung nên **số câu bị LLM bỏ cũng = 0**.
  **PHẦN CÒN LẠI PHẦN LỚN LÀ LỖI CỦA CHỮ NGUỒN, NÓI THẲNG: sửa dịch vô ích.**
  Model chấm soi riêng: **2,38% câu nguồn tự nó vô nghĩa** (`艳师官` đáng lẽ
  `验尸官` · `劫族先登` không có nghĩa). Nặng hơn và chưa ai ghi: **ASR CẮT ĐÔI
  thành ngữ** — `眼看尸体前脚下葬` / `后脚他就已经开挖了` là cặp 前脚…后脚
  ("vừa mới… thì đã…"), tách ra dịch riêng thì mỗi nửa đều vô nghĩa
  (*"chôn một chân"* / *"chân còn lại anh đã bắt đầu đào"*). Đây là bệnh của
  bước CẮT CÂU, không phải bước dịch.
  **LỜI 4 — ANH HÙNG CHẨN ĐÚNG, VÀ CHỈ CẦN ĐỔI Ô. NHÃN COMBO ĐANG NÓI SAI, ĐÃ
  VÁ.** GỌI THẬT `thay_giong_video` cho cả ba ô rồi ĐẾM lượt gọi bước 4c
  (`_do_o_nao_cua_anh_hung.py`, mượn `_test_am_va_hinh._chay_that`):
  **mục 1 -> 4c chạy 1 lần · MỤC 2 (ô anh Hùng) -> 1 lần · mục 3 -> 0 lần.**
  Ghép với CV tốc độ đọc ở mục (11): **mục 1 20,11/14,08 · mục 2 20,77/14,26 ·
  mục 3 15,64/10,88**. Tức **mục 2 còn KÉM CẢ mục 1 về độ đều**, mà nhãn của nó
  lại ghi *"(tiếng đều, khuyên dùng)"* — chữ "đều" ở đó vốn định nói *hệ số ép
  về 1,000*, nhưng người dùng đọc ra *"đọc đều một nhịp"*. **Chính dòng nhãn đó
  đẩy anh Hùng vào ô sai.** Vá: nhãn `hinh` bỏ hẳn "tiếng đều/khuyên dùng", nêu
  giá thật (*"không ép tiếng, video dài thêm ~20%"*); "khuyên dùng" chuyển sang
  `hinh_deu`. Cổng 89 thêm **9zd** (chữ "đều" chỉ được xuất hiện ở mục thật sự
  có `doc_deu=True`) + **9ze**; **104 -> 106 ĐẠT · 0 HỎNG**; thử phá bằng cách
  trả nhãn cũ về -> **BẮT 2 · LỌT 0**.
  **ĐỔI Ô CHỮA ĐƯỢC MẤY LỜI CÙNG LÚC — đây là cột đáng giá nhất của cả lượt:**
  từ MỤC 2 sang **MỤC 1** thì tiếng Trung chèn vào tụt **25,57 -> 4,40 giây
  (bớt 82,8%)**, số mảnh **31 -> 4**, và video không dài ra. Sang **MỤC 3** thì
  **25,57 -> 18,78 s (bớt 26,6%)** kèm đọc đều hơn. Giá của mục 1: `tempo_max`
  1,000 -> 1,074 (vẫn xa ngưỡng cảnh báo 1,30).
  **FILE NGHE THỬ:** `_NGHE_THU_ANH_HUNG/bon_loi/` — `A_BAT_bu25.57s_35giay.wav`
  · `B_TAT_KHONG_BU_35giay.wav` (CÙNG cửa sổ 10-45 s, cửa sổ này có 6 mảnh bù
  gồm mảnh dài nhất 3,40 s) · `C_CHI_MANH_BU_31manh_25.57s.wav` (chỉ vật liệu
  bù). Cả 3 chuẩn về −14 LUFS bằng chính `chuan_do_to`, **đo lại bằng
  `loudnorm` chạy RIÊNG: −14,04 · −14,03 · −14,37**; MD5 3/3 khác nhau.
  **CHƯA LÀM, GHI THẲNG:** **chưa ai NGHE** một file nào · 4 arm là 4 LƯỢT
  CHẠY RIÊNG (LLM + VieNeu không tiền định) nên chỉ cặp BẬT/TẮT ghép cặp theo
  cấu tạo, ba cột còn lại là **1 điểm dữ liệu/arm**, chưa có DẢI · mới **1
  video × 148 s**, 3 video kia của anh Hùng chưa dựng lại · **chưa vá bù giọng
  gốc** (chọn gì khi `cach_tron="tach"`: im, nhạc nền, hay tắt hẳn — quyết định
  của anh Hùng) · bệnh **ASR cắt đôi thành ngữ** mới thấy 1 ca, chưa đếm được
  tần suất · `studio.db` **CỤT** (WAL trỏ tới trang 102141-102155 = cần file
  ~418 MB, file đang có 118 KB) nên 3/4 job sáng 28/08 mất theo, không dựng lại
  được — bệnh cũ "ổ C đầy" vẫn chưa chữa.
  **(14) 28/08/2026 — ĐÃ TẮT HẲN BÙ GIỌNG GỐC Ở CÁCH TRỘN "TÁCH NHẠC"
  (v2.48.0), VÀ ĐO RA NÓ GẦN NHƯ MIỄN PHÍ: QUÃNG NGHỈ **CÓ NHẠC NỀN**, KHÔNG
  IM.** Anh Hùng nghe rồi chốt: *"Tôi đã bấm 'tiếng gốc MẤT HẲN' thì app không
  được tự chèn tiếng Trung vào."* Đây là **SỬA BỆNH**, không phải tuỳ chọn mới
  — app đang đi ngược LỰA CHỌN TƯỜNG MINH của người dùng — nên **đổi thẳng,
  KHÔNG đẻ cờ mới**, và tham số `bu_giong_goc_bat` bị **GỠ HẲN** khỏi cả
  `thay_giong_video` lẫn `thay_giong_mot_video` (giữ một núm không còn tác dụng
  là mã chết, mà mã chết ở đây nguy hơn: ai bật lại rồi tưởng vừa chữa được lỗi
  mất tiếng). Nhánh **"đè giọng" KHÔNG BỊ ĐỤNG MỘT DÒNG NÀO** — nó vốn đã không
  bù (bù ở đó là cộng giọng gốc hai lần), cổng 86 mục 5b vẫn canh đúng điều đó.
  **`dedup_key` KHÔNG ĐỔI, VÀ ĐÓ LÀ SỐ ĐO CHỨ KHÔNG PHẢI LỜI HỨA:** nạp
  `git show 5154baa:app/core/tg_chay.py` thành module riêng rồi GỌI THẬT
  `khoa_chong_trung` trên **9 tổ hợp cờ** -> **GIỐNG TỪNG KÝ TỰ 9/9**;
  `tg_chay.py` và `services.py` **không đổi một byte** (`git status` sạch, và
  `grep -c bu_giong app/services.py` = 0). Bảo đảm này là **DO CẤU TẠO**: cờ bù
  chưa bao giờ có mặt trong `khoa_chong_trung`. 200-300 kênh **không có gì để
  xuất lại**.
  **BƯỚC BỎ-BÙ VẪN CHẠY, NHƯNG CHỈ ĐỂ ĐO RỒI BÁO (`bu_giong_goc(chi_do=True)`)**
  — đổi hành vi âm thầm là bẫy cả repo này chống. Chế độ `chi_do` dùng **Y
  NGUYÊN một bộ dò** (cùng đường bao, cùng sàn nhiễu, cùng ngưỡng, cùng vòng
  lặp quyết định từng khoảng), chỉ bỏ phần cắt -> **rẻ hơn đường cũ** (bỏ 20-68
  lượt ffmpeg cắt + 8 lượt đo mức). Đo được hai chế độ đếm ra **CÙNG MỘT SỐ**
  trên cả 2 video (16,88 s/20 quãng · 57,70 s/68 quãng) — bắt buộc, vì nhãn "đã
  bỏ N giây" mà đếm bằng bộ dò khác đường cắt thì nó là số bịa. Người dùng thấy
  ở **HAI CHỖ**: dòng `prog(0.907, …)` lúc chạy và
  `logs/bo_tieng_goc_<ngày>.log` (dòng `prog` bị *"Xong — video mới ở thư mục
  đích"* ghi đè ngay khi job xong, nên một mình nó không đủ).
  **ĐO GHÉP CẶP, 2 VIDEO THẬT, MỘT LƯỢT CHẠY/VIDEO** (`_do_quang_nghi.py`; arm
  tách ra ĐÚNG chỗ bản vá tác động `manh_tron = kh["manh"] + bu["manh"]` bằng
  cách bọc `bu_giong_goc` + `tron_thay_giong`, nên hai arm dùng chung bản tách /
  chép lời / dịch / **FILE GIỌNG**). Cấu hình đọc từ QSettings của anh Hùng:
  `vnb:` · đích **`vi`** · `tach` · che chữ + nhấn nhá + chỉnh hình BẬT:

  | | video 1 (169,1 s ra) | video 2 (435,4 s ra) |
  |---|---|---|
  | ĐÃ BỎ | **16,88 s / 20 quãng** (9,98%) | **57,70 s / 68 quãng** (13,25%) |
  | nền TB bản trộn (p50) | −20,30 dBFS | −21,24 dBFS |
  | mức lời (p90) | −14,00 | −13,17 |
  | **mức TRONG quãng, arm SAU** | **−30,94 TB · −52,66 thấp nhất** | **−32,21 TB · −36,74 thấp nhất** |
  | thấp hơn nền | 10,64 dB | 10,97 dB |
  | GẦN NỀN (>= nền−6 dB) | 9 quãng / 8,43 s | 15 quãng / 10,36 s |
  | nhỏ hơn nhưng NGHE ĐƯỢC | 8 quãng / 6,19 s | 53 quãng / 47,33 s |
  | **IM HẲN (<= −45 dBFS)** | **3 quãng / 2,24 s** | **0 quãng / 0,00 s** |
  | quãng dài nhất | 2,73 s | 4,46 s |

  **CÂU TRẢ LỜI CHO ANH HÙNG: quãng nghỉ KHÔNG im — nó CÓ NHẠC NỀN.** Cộng cả
  hai video: **85 quãng / 74,55 giây**, trong đó **chỉ 3 quãng / 2,24 giây
  (3,5% số quãng) thật sự IM**; video 2 **không có quãng nào im**, chỗ nhỏ nhất
  vẫn −36,74 dBFS. Ở cách "tách nhạc" lớp nhạc chạy SUỐT video nên bỏ giọng gốc
  đi chỉ làm quãng đó **vơi ~10,6-11,0 dB**, không thành lỗ đen. **Vì vậy bản
  vá này gần như MIỄN PHÍ** — và điều đó chỉ đọc được khi đo trên **BẢN TRỘN
  CUỐI**; đo trên LỚP GIỌNG (mốc cũ *"28,98 giây im"*) thì lớp nhạc không có
  mặt nên con số đó **nói về một file anh Hùng không bao giờ nghe**.
  **THƯỚC "CÒN TIẾNG TRUNG KHÔNG" LÀ ASR, `language` TỰ NHẬN, CÓ SÀN BỊA:**

  | arm | vật liệu đưa Groq | nhãn | chữ Hán |
  |---|---|---|---|
  | TRƯỚC (v2.47.1) | nối riêng 20 / 68 **mảnh bù** | **Chinese** | **87/96 = 90,6%** · **282/340 = 82,9%** |
  | SAU (v2.48.0) | cắt **ĐÚNG các cửa sổ đó** khỏi bản trộn cuối rồi nối | **English** | **0/10 = 0,0%** · **0/18 = 0,0%** |

  Hàng TRƯỚC là **thước CÓ RĂNG** (ra 0 ở cả hai arm thì phép đo hỏng, không
  phải bản vá tốt); hàng SAU vừa là phép đo vừa là **SÀN BỊA** — cùng số giây
  (16,38 / 57,66 s), cùng cửa sổ, mà whisper nghe nhạc nền ra đúng `"Thank
  you."` chứ không bịa một chữ Hán nào. Nhắc lại bài học lượt trước: chép **CẢ
  BẢN TRỘN** rồi ép `language=zh` ra **94,99%** chữ Hán trên file KHÔNG có một
  mẩu tiếng gốc nào — **ép ngôn ngữ là tự phát chứng nhận cho chính mình**.
  **SỐ ĐO ĐI THEO LƯỢT DỊCH, ĐỪNG CHÉP SANG BẢNG KHÁC:** cùng video 1, cùng bản
  mã, lượt 27/08 ra **25,57 s / 31 quãng** còn lượt này **16,88 s / 20 quãng**
  (LLM + VieNeu không tiền định — đúng lý do phải ghép cặp).
  **CỔNG 86: 62 -> ĐẠT 82 · HỎNG 0** (CA 9, 20 mục: quét AST `manh_tron` không
  bao giờ được cộng thêm — kèm **TỰ KIỂM BỘ DÒ** dựng lại đúng dòng mã CŨ ·
  `chi_do` chạy THẬT bằng ffmpeg: 0 file ghi ra mà số đếm vẫn khớp đường cắt ·
  nhãn dựng TỪ SỐ ĐO · nhãn + lời nhắn không khớp khoá bước nào của
  `buoc_tu_tien_trinh`). **Thử phá `_pha_de_giong.py`: BẮT 13 · LỌT 0 · KHÔNG
  PHÁ ĐƯỢC 0.**
  **HAI LỖI CỦA CHÍNH CỔNG/SCRIPT PHÁ, ghi kẻo lặp:** (a) mục 9j bản đầu lọc
  lời nhắn theo chuỗi `"tiếng gốc"` và **bắt trúng lời nhắn bước TRỘN** (*"Trộn
  tiếng mới ĐÈ lên tiếng gốc…"*) — câu đó khớp khoá bước 9 là ĐÚNG, nên mục
  HỎNG OAN; lọc theo `"quãng nghỉ"` mới đúng (cùng họ bẫy mục 5i). (b) **phép
  phá số 5 của `_pha_de_giong.py` đã CHẾT ÂM THẦM từ lúc thêm hai ô âm lượng**:
  neo của nó là `if de_giong: … return sig`, mà `:mn=`/`:mg=` chen vào giữa nên
  nó tìm thấy **0 chỗ** và im lặng rơi vào cột "KHÔNG PHÁ ĐƯỢC" — tức chốt *"cờ
  phải vào hash"* (chốt CHẶN SẢN XUẤT) **không còn ai thử** suốt từ đó. Neo mới
  chỉ ôm hai dòng của cờ; chạy lại ra **BẮT** (`2d 0/6`). Kèm: script phá nay
  **`compile()` lại bản đã phá** (bài học `_pha_doc_lan.py`).
  **CỔNG 55 ĐỎ LƯỢT ĐẦU RỒI XANH LƯỢT SAU — ĐÚNG MỤC NHẤP NHÁY ĐÃ GHI:** lượt 1
  ra **47 · 1** ở mục *"2 luồng NHANH HƠN chạy lần lượt"* (**0,51 lần**) vì đo
  ngay sau hai lượt dây chuyền dài + 15 lượt cổng 86 (bể key Groq nóng, CPU
  bận); lượt 2 khi máy nguội ra **48 · 0 · nhanh 1,50 lần**. Chứng minh không
  phải hồi quy: `git diff app/core/thay_giong.py` **không đụng một dòng nào**
  của `thay_giong_thu_muc` / `LAN_TG` / `_tg_pool` — toàn bộ thay đổi nằm trong
  `bu_giong_goc` · `thay_giong_video` · `thay_giong_mot_video`.
  **FILE NGHE THỬ:** `_NGHE_THU_ANH_HUNG/bo_tieng_trung/` — `A_TRUOC_co_bu_*` /
  `B_SAU_khong_bu_*` là **CÙNG MỘT ĐOẠN, CÙNG MỘT LƯỢT CHẠY**, lấy quãng bù DÀI
  NHẤT (2,73 s ở giây 89,15-91,88) kèm 3 giây đệm hai đầu; chuẩn về −14 LUFS
  bằng chính `chuan_do_to`, **đo lại bằng `loudnorm` chạy RIÊNG: −14,01 và
  −14,07 LUFS · TP −1,42 / −1,44 dBTP**, MD5 khác nhau. Thêm
  `C_CHI_MANH_BU_v1_20manh.wav` = chỉ vật liệu bù (nghe là ra tiếng Trung).
  **CHƯA LÀM, GHI THẲNG:** **chưa ai NGHE** một file nào — mọi số trên là số
  ĐO · **2 video / 1 lượt mỗi video**, đủ để nói "quãng nghỉ có nhạc", **không
  đủ** để nói phân bố · ngưỡng IM **−45 dBFS** lấy từ `SAN_LUFS_CHUAN_HOA` của
  chính app (không đặt mò một số mới) nhưng **chưa ai kiểm bằng tai** xem
  −36 dBFS trên loa điện thoại có nghe ra không · 2 video kia của anh Hùng chưa
  chạy lại · **chưa đo trên nguồn KHÔNG có nhạc nền** (phim thoại khô) — đó là
  ca DUY NHẤT bản vá này có thể đắt, và nó **chưa có số**; nếu anh Hùng gặp
  video kiểu đó thì phương án 3 (chỉ bù mảnh ngắn dưới X giây) mới cần bàn tới.
  **(15) 28/08/2026 — HƯỚNG "CHẢY LIỀN + NEO Ở RANH GIỚI CẢNH" ĐÃ ĐO: *KHÔNG
  NỐI*, CHẾT Ở ĐÚNG CỘT ĐÃ GIẾT 3 HƯỚNG TRƯỚC. VÀ PHÉP ĐO LÔI RA MỘT TRẦN SỐ
  HỌC MÀ CẢ 4 HƯỚNG ĐỀU KHÔNG BIẾT.**
  Hướng được giao: bỏ khung cố định, câu i+1 bắt đầu ngay khi câu i đọc xong,
  rồi NEO LẠI ở mốc an toàn. Đo bằng `_do_chay_lien.py` (dựng lại timeline từ
  ĐÚNG bộ file giọng của lượt chạy thật đã cache -> **TIỀN ĐỊNH**, không LLM,
  không TTS) + `_do_mat_do_neo.py` (mật độ mốc neo trên 4 video THẬT, ĐẦY ĐỦ).
  **ĐỐI CHỨNG TÁI LẬP ĐƯỢC LƯỢT CHẠY THẬT** (bắt buộc, không có thì mọi số dưới
  vô nghĩa): cho MỌI câu làm câu neo = đúng cách app đang chạy -> ra **32,30%**
  im so với **32,36%** đã công bố (VNB) và **18,22%** so với **18,29%** (EDGE),
  lệch **0,06-0,07 điểm %**.
  **MỘT NGUỒN MỐC NEO CHẾT HẲN, ĐO RA MỚI BIẾT:** *"quãng im DÀI của bản gốc"*
  ra **0 · 1 · 1 · 0 mốc** trên 4 video (ngưỡng 0,35 s / −30 dB) — nguồn Douyin
  thuyết minh phim **nói liền không nghỉ**. Cắt cảnh thì dày: **23,5-28,2
  mốc/phút**, cách nhau trung vị **1,84-2,38 s**, nhưng khoảng thưa nhất tới
  **5,30-14,12 s**.
  **BẢNG QUYẾT ĐỊNH** (lt1 · `vnb:` · k=1,1988 · 35 câu — đúng cấu hình anh Hùng):

  | | im % | >=0,5s | dài nhất | **TRÔI max** |
  |---|---|---|---|---|
  | app hiện tại | 32,30 | 30 | 4,90 s | **0** |
  | neo cắt cảnh (18 neo) · trần 100 ms | 32,30 | 30 | 4,90 s | 100 ms |
  | neo cắt cảnh · trần 300 ms | 32,30 | **28** | 4,90 s | 300 ms |
  | neo cắt cảnh · KHÔNG trần | 32,30 | **16** | 4,90 s | **2 923 ms** |
  | KHÔNG neo · KHÔNG trần | 5,15 | 0 | 0,23 s | **29 300 ms** |

  Ở trần **300 ms** (mức repo đã đo là tồn tại mà không ai kêu: 269-354 ms) nó
  mua được **ĐÚNG 2 quãng trong 30**, tổng im **không đổi một phần trăm nào**,
  quãng dài nhất **không đổi một phần trăm nào**. Muốn 16/30 phải trả **2,9
  GIÂY** trôi. **Tỉ giá đo được là 1:1** — mỗi giây trôi mua đúng ~1 giây bớt
  của quãng dài nhất và ~0,5 điểm % im; đưa quãng dài nhất 4,90 s về 1,00 s cần
  **3,9 giây trôi**.
  **GỐC RỄ LÀ MỘT PHÉP TRỪ, KHÔNG PHẢI MỘT THUẬT TOÁN — đây là thứ đáng nhớ
  nhất của cả 4 hướng:** `im giữa câu = độ_dài_VIDEO − tổng_TIẾNG − im hai đầu`.
  Đo: tiếng thật **72,185 s**, video **107,922 s** -> **im BẮT BUỘC 35,74 s =
  33,11%**, app đang ở 32,30%. **Không phép SẮP XẾP nào giảm được tổng im**;
  gộp câu · gộp lượt TTS · giãn hình không đều · chảy liền + neo đều chỉ ĐỔI
  CHỖ. Hai đường DUY NHẤT làm nó nhỏ đi: **video ngắn lại** (= mục 1 của combo,
  bỏ chỉnh hình: 32,36% -> 19,93%) hoặc **TIẾNG DÀI RA**.
  **HƯỚNG THỨ NĂM, TỪ CHÍNH PHÉP ĐO NÀY: GIỮ NGUYÊN KHUNG CỐ ĐỊNH, ĐỌC CHẬM LẠI
  CHO ĐẦY KHUNG.** Bước 4c của app chỉ biết đọc NHANH lên
  (`doc_nhanh_vua_khung`); **không có đường nào đọc CHẬM lại**. Câu vẫn nằm đúng
  mốc gốc -> **lệch tiếng-hình = 0 THEO CẤU TẠO**. Đo THẬT bằng âm thanh
  (`_do_doc_cham.py`, ghép cặp TỪNG BYTE trên cùng bộ file giọng, chạy 2 lượt ra
  **Y HỆT**):

  | kéo tối đa | im % | >=0,5s | dài nhất | TRÔI max | méo phổ TB |
  |---|---|---|---|---|---|
  | 1,00 (app hiện tại) | 32,36 | 30 | 4,96 s | **0,0 ms** | 0,000 dB |
  | 1,15 | 23,52 | 19 | 4,57 s | 7,7 ms | 3,113 dB |
  | **1,25** | **18,81** | **8** | 4,29 s | **7,3 ms** | 3,435 dB |
  | 1,40 | 15,73 | 6 | 3,94 s | 17,8 ms | 3,530 dB |

  Video thứ hai (lt2 · EDGE · k=1,1519 · 50 câu): **25,31 -> 16,51%** · 15 -> 2
  quãng · dài nhất 4,14 -> 3,57 s · **trôi 10,3 ms**. lt1 EDGE (k=1,1144):
  **18,29 -> 9,69%** · 15 -> 2 quãng · 2,00 -> 0,72 s · **trôi 5,8 ms**.
  Tức ở trôi **7-18 ms** nó mua được thứ mà chảy-liền phải trả **2 923 ms** mới
  mua được một nửa.
  **CÁI PHẢI TRẢ — MÉO PHỔ 3,0-3,9 dB**, vì phép đo kéo bằng `rubberband`. Con
  số 0,061 dB ghi ở khối "chỉnh video theo giọng" là đo trên LỚP NHẠC, không
  phải trên TIẾNG NÓI — **đừng chép nó sang đây**.
  **ĐƯỜNG 0 MÉO ĐÃ ĐO ĐƯỢC:** `rate` ÂM của chính máy đọc, 0 phép xử lý tín
  hiệu (`_do_rate_am.py`, edge-tts THẬT, đo GIÂY NÓI THẬT bằng `do_le_im` chứ
  không phải độ dài file): **−10% -> 1,1106x · −15% -> 1,1763x · −20% ->
  1,2507x · −25% -> 1,3329x · −30% -> 1,4295x · −40% -> 1,6680x**, và **lệch
  giữa các câu chỉ ±0,0008** (1,2500-1,2515 ở −20%) — tuyến tính, không bão hoà,
  khác hẳn `length_scale` của Piper. Tức `rate = −20%` cho ĐÚNG mức 1,25x đo
  được ăn nhất, với **méo phổ = 0 theo cấu tạo**.
  **CHỖ NỐI ĐÚNG LÀ MỘT NHÁNH TRONG `khop_thoi_gian`** (đọc mã, chưa nối):
  nhánh `(1) if d_nat <= khung: tempo = 1.0` chính là chỗ sinh ra khoảng im.
  Nối ở đó được MIỄN PHÍ hai thứ: bất biến **0 ms chồng lấn** vẫn đúng (tiếng
  kéo ra vẫn nằm trong `khung <= tran - CHUA_TRUOC_CAU_KE`), và **mốc TỪNG CHỮ
  tự co giãn đúng** vì `ty_le = d_fin / d_nat` đã đo trên file đã ghi -> `= k`.
  Nối ở tầng khác là phải tự lo cả hai.
  **CHƯA NỐI, VÀ LÝ DO ĐÚNG LUẬT REPO:** **chưa ai NGHE** (file ở
  `_NGHE_THU_ANH_HUNG/lien_mach_3/`, cặp TRƯỚC/SAU cùng lượt, −14 LUFS đo lại
  bằng `loudnorm` chạy riêng, MD5 khác nhau) · ba hướng trước chết đúng vì nối
  trước khi nghe · và **`app/` lượt này KHÔNG đổi một dòng nào** (`git status
  --porcelain app/ config.py main.py` RỖNG) nên `dedup_key` của 200-300 kênh
  **không thể** đổi — bảo đảm DO CẤU TẠO.
  **BẪY CỦA CHÍNH PHÉP ĐO, ĐÃ SẬP 1 LẦN:** `_do_doc_cham.py` bản đầu tra
  `he_so_hinh` trong `_kq_khop_video.json`, **tra hụt thì LÙI IM LẶNG về
  1,1988**. File đó bị lượt lt2 ghi đè -> mục lt1/EDGE biến mất -> phép đo lấy
  1,1988 thay cho **1,1144** THẬT và in ra bảng trông hoàn toàn hợp lý (im
  23,85% thay vì 18,29%). Đúng họ *"phép đo hỏng phát chứng nhận"*. Nay tra hụt
  là **NÉM**.
  **CHƯA ĐẠT, GHI THẲNG:** chưa ai NGHE · `vnb:` mới có **1 video** (lt2/VNB
  hỏng giữa chừng vì VieNeu trả **file 0,000 giây** cho câu #13 — `ok[i]` vẫn
  True nên `_kiem_wav` NÉM và giết cả lượt; lỗ này CÓ THẬT trên đường app) ·
  méo phổ 3,4 dB là số của `rubberband`, đường `rate` âm **chưa đo end-to-end**
  · **chưa đo TRẢI TỐC ĐỘ ĐỌC** sau khi kéo (cần bản dịch, phép đo này chỉ có
  file giọng) — mà đó đúng là cột anh Hùng cũng đã kêu (*"lúc nhanh lúc chậm"*),
  nên **không được hứa** trước khi có số.
  **(16) 28/08/2026 — HƯỚNG THỨ SÁU "DỊCH ĐẦY HƠN": ĐÃ LÀM, ĐÃ ĐO BỐN CỘT
  CÙNG LÚC. KẾT LUẬN: *KHÔNG GIẢI ĐƯỢC*, VÀ CON SỐ NÓI RÕ VÌ SAO.**
  Anh Hùng chốt bằng bốn chữ: *"đọc LIỀN · NHANH · mà ĐỀU · mà ĐÚNG"*. Bốn thứ
  đá nhau theo SỐ HỌC (tiếng xong sớm -> dư chỗ -> muốn LIỀN thì phải lấp).
  Hai cách lấp cũ đều mất một chữ; cách thứ ba — **viết bản dịch ĐẦY HƠN**,
  cùng nghĩa nhưng nhiều chữ hơn — chưa ai thử. Nay đã thử.
  **VIỆC 0 — PHÂN BỐ HỤT KHUNG** (`_do_viet_day.py`, video THẬT
  `Downloads\longtieng` chép sang hộp cát, `vnb:` · đích `vi` · `tach`).
  **Khung đo trên TRỤC GỐC nên số này đúng cho CẢ hai mục** của combo "Khớp
  tiếng với hình" — chỉnh hình chỉ phóng phần trống lên `k` lần chứ không đẻ
  ra nó:

  | video/giọng | % câu HỤT | giây hụt | % video | câu TRÀN | +ký tự | gấp | DỄ · KHÓ · BỊA |
  |---|---|---|---|---|---|---|---|
  | lt1/VNB | 31,43 | 7,41 | 8,23 | 24 (68,6%) | 146 | 1,083x | 8 · 2 · 1 |
  | lt1/EDGE | 11,43 | 1,80 | 2,00 | 28 (80,0%) | 31 | 1,019x | 3 · 1 · 0 |
  | lt2/VNB | 44,00 | 9,66 | 10,73 | 23 (46,0%) | 194 | 1,115x | 16 · 4 · 2 |
  | lt2/EDGE | 14,00 | 4,73 | 5,25 | 40 (80,0%) | 79 | 1,049x | 5 · 1 · 1 |

  **HAI ĐIỀU BẤT NGỜ, VÀ CẢ HAI ĐỔI CÁCH ĐỌC BÀI TOÁN:**
  · **Phần hụt NHỎ** — 2,0-10,7% thời lượng, lấp hết chỉ cần **+1,9% đến
    +11,5% ký tự** cả bài. Tức **KHÔNG phải bịa**, hướng này ĐƯỢC PHÉP làm
    (bậc 0,0-0,5 s gom 8/11 câu ở lt1/VNB; chỉ 1-2 câu rơi vào nhóm BỊA).
  · **Phần lớn câu lại TRÀN khung (46-80%)**, mà `he_so_hinh_can` lấy đúng tỉ
    số TRÀN LỚN NHẤT làm hệ số giãn hình. Nên ở mục 2, video phình `k` lần
    trong khi tiếng thì không — **đó mới là chỗ đẻ ra phần lớn khoảng im, và
    viết đầy KHÔNG với tới nó**.
  **VIỆC 1 — `viet_day_vua_khung` (bước 4b'), khuôn ĐỐI XỨNG `rut_gon_vua_
  khung`.** Ba chốt chống bịa: **TRẦN NỚI 1,45x** · **model KHÁC model dịch
  chấm lại** (`qwen/qwen3.8-27b` vs `openai/gpt-oss-120b`) · **chỉ nhận khi
  đọc lên DÀI HƠN THẬT và KHÔNG tràn khung**. Đọc lại đi CHUNG cửa
  `_doc_lai_loat` với 4b nên `thay_giong.py` vẫn ĐÚNG **3** chỗ gọi
  `_synth_all_words` (cổng 63 giữ 49·0). MẶC ĐỊNH TẮT.
  **VIỆC 2 — BẢNG 4 CỘT × 4 ARM** (`_do_bon_chu.py`; MỘT lượt chạy/video/giọng
  rồi tách arm — mọi arm dùng chung bản dịch + bộ file giọng gốc, ghép cặp
  theo cấu tạo). **A** = app hôm nay · **B** = kéo chậm 1,15 · **C** = dịch
  đầy · **D** = dịch đầy + đọc ĐỀU (bỏ 4c). Cột mục 2 = ĐÚNG cấu hình anh Hùng:

  | video/giọng | arm | LIỀN im% | >=0,5s | NHANH kt/s | ĐỀU CV% | ĐÚNG /5 (bịa) |
  |---|---|---|---|---|---|---|
  | lt1/VNB | A | **30,08** | 31 | **24,26** | 16,64 | 4,90 (0) |
  | | B | **15,43** | 7 | 21,03 | **20,41** | 4,90 (0) |
  | | C | 29,99 | 30 | 24,26 | 16,59 | **4,97** (0) |
  | | D | 22,44 | 16 | 21,54 | **13,28** | 4,97 (0) |
  | lt2/VNB | A | **33,44** | 34 | **24,30** | 16,11 | 4,75 (0) |
  | | B | **20,13** | 8 | 20,15 | 15,50 | 4,75 (0) |
  | | C | 32,18 | 30 | 23,96 | 15,42 | 4,74 (**1**) |
  | | D | 27,97 | 22 | 22,33 | **12,68** | 4,74 (**1**) |
  | lt1/EDGE | A | 19,52 | 19 | 20,36 | 21,53 | 4,87 (0) |
  | | B | **6,91** | 1 | **17,68** | **22,01** | 4,87 (0) |
  | | C | 19,08 | 18 | 20,36 | 21,50 | 4,77 (0) |
  | | D | 14,86 | 11 | 17,96 | **16,97** | 4,77 (0) |
  | lt2/EDGE | A | 26,39 | 16 | 20,88 | 12,38 | 4,73 (0) |
  | | B | **15,14** | 2 | **18,06** | 12,94 | 4,73 (0) |
  | | C | 26,50 | 16 | 20,89 | 12,39 | 4,73 (0) |
  | | D | 19,33 | 11 | 18,45 | **9,96** | 4,73 (0) |

  **ĐỐI CHỨNG "THƯỚC CÓ RĂNG": arm A ra 30,08% im (lt1/VNB)** — khớp mốc
  ~29,01% của v2.49.0. Chồng lấn **0,0 ms ở CẢ 16 arm**.
  **THIẾT KẾ ARM CHO PHÉP TÁCH BẠCH HAI THỨ, VÀ ĐÂY LÀ SỐ ĐÁNG GIÁ NHẤT:**
  · **`C − A` = DỊCH ĐẦY MỘT MÌNH**: −0,09 · −1,26 · −0,44 · **+0,11** điểm %.
    Trung bình **−0,4 điểm %**, và một cột còn ĐI NGƯỢC. Tức **gần bằng 0**.
  · **`D − C` = BỎ 4c một mình** (hai arm đều đã dịch đầy): −7,55 · −4,21 ·
    −4,22 · −7,17 = **−5,8 điểm %**, lớn hơn **14 lần**.
  ⇒ **Toàn bộ phần D hơn A là công của "bỏ 4c" (mục 3 combo, đã có từ
  v2.46.0), KHÔNG phải của dịch đầy.**
  **VÌ SAO DỊCH ĐẦY GẦN NHƯ KHÔNG ĂN — hai nguyên nhân, đều đo được:**
  · **LLM viết đầy rất DÈ, và nó ĐÚNG khi dè.** Dump bản thật: `嘿呀 嘿呀…`
    (tiếng hò) -> trả lại NGUYÊN VĂN vì không có gì để thêm; `凡是被感染的人类
    都会被遗弃到这里` -> thêm đúng chữ *"sẽ"*; `部分幸存的人类…` -> thêm *"của
    họ"*. Mỗi câu **1-3 chữ**, chấm trung thành 5/5. Nguồn Trung đã được dịch
    hết ý (bản Việt vốn đã **3,6x** số ký tự nguồn), nên **không còn chữ nào
    trong nguồn để lấy**.
  · **Cửa chống bịa loại phần lớn phần còn lại**: NHẬN **1/6 · 1/2 · 3/10 ·
    0/3**. Cộng cả 4 lượt: **+22 ký tự được nhận / 450 ký tự cần** =
    **4,9% phần hụt lấp được bằng chữ THẬT**.
  **GIÁ LLM: +2 lượt/video** (1 viết đầy + 1 chấm nghĩa) trên nền `_dich_loat`
  **5,0 lượt/video** = **1,40x** — TRONG trần 1,5x (`dich_va_soat` 10,9x và
  `dich_theo_gio` 2,46x đã bị bác vì vượt).
  **MẶT XẤU, NÓI THẲNG:** lt2/VNB arm C và D có **1 câu bị model chấm là BỊA**
  và **1 câu dưới 4 điểm**, trong khi arm A/B là **0** — tức dịch đầy có lọt
  một câu qua cửa; lt1/EDGE ĐÚNG tụt **4,87 -> 4,77**. Đổi một chút ĐÚNG lấy
  0,4 điểm % LIỀN là **lỗ**.
  **BỐN CHỮ: KHÔNG ARM NÀO ĐƯỢC CẢ BỐN. Cho anh Hùng chọn, đừng tự quyết:**
  · **A (hôm nay)** — được **NHANH** (24,3 kt/s) + **ĐÚNG** (4,90); mất
    **LIỀN** (30,1%).
  · **B (kéo chậm 1,15)** — được **LIỀN** nhất (15,4%) + **ĐÚNG**; mất
    **NHANH** (21,0) và **ĐỀU** (CV 16,64 -> 20,41, xấu đi ở 3/4 cột).
  · **D (bỏ 4c)** — được **ĐỀU** nhất (CV 13,28, tốt hơn CẢ arm A) + LIỀN đỡ
    một phần (22,4%) + ĐÚNG giữ nguyên; mất **NHANH** (21,5).
  · **C (dịch đầy)** — gần như KHÔNG đổi gì so với A, mà tốn thêm 2 lượt LLM.
  **KHUYẾN NGHỊ THEO SỐ: nếu anh Hùng ưu tiên "đều + liền" thì chọn MỤC 3 của
  combo (bỏ 4c) — ô đó ĐÃ CÓ SẴN, không cần bật viết đầy.** Ô viết đầy giữ lại
  vì nó có ích ở nguồn KHÁC (nguồn nào dịch bị lược nhiều thì phần nhận sẽ cao
  hơn 4,9%), nhưng **MẶC ĐỊNH TẮT và đừng hứa nó chữa được "được đoạn rồi
  nghỉ"**.
  **HAI LỖI THẬT CỦA CHÍNH BẢN VÁ, BẮT ĐƯỢC NHỜ TÁCH RIÊNG BỘ ĐẾM — bài học
  đáng nhớ nhất lượt này.** Cửa chấm nghĩa gọi `_mang_llm`, mà model trả về
  **HAI hình dạng** hàm đó không nhận: **bản ghi ĐƠN** `{"i":0,"a":5,…}` (mẻ 1
  câu) và **dict KHOÁ THEO NHÃN** `{"0":{…},"1":{…}}` (mẻ nhiều câu). Cả hai
  ra `[]` -> cửa nghĩa **MÙ HOÀN TOÀN** -> fail-safe vứt sạch bản đầy -> bước
  4b' **không bao giờ nhận nổi một câu**, `rc` vẫn 0, không một dòng báo. Đo
  được `so_bo_vi_khong_cham = 1/1` rồi **5/5** trên video THẬT.
  **Thứ tố giác được là bộ đếm `so_bo_vi_khong_cham` TÁCH RIÊNG khỏi
  `so_bo_vi_nghia`** — gộp làm một thì bảng ghi *"cửa chống-bịa loại 5/5 câu"*,
  nghe như chốt đang làm việc trong khi nó đang mù. Đúng họ bẫy *"phép đo phát
  chứng nhận"* (`astats` cổng 53 · `startswith` cổng 44), chỉ khác là lần này
  nó phát chứng nhận cho CHÍNH NÓ. Chữa bằng `_mang_hoac_mot`; **CỐ Ý KHÔNG
  sửa `_mang_llm`** (nó nằm trên đường DỊCH của 200-300 kênh — việc RIÊNG, cần
  cổng riêng).
  **`dedup_key`: TẮT cờ -> giống mốc `e12208e` TỪNG KÝ TỰ, 128 tổ hợp (cổng đo
  lại 64), lệch 0.** BẬT -> nối `:vd=1` vào ĐUÔI, khoá cũ vẫn là TIỀN TỐ. 200-
  300 kênh KHÔNG có gì để chạy lại.
  **CỔNG 89: 157 -> ĐẠT 190 · HỎNG 0** (MỤC 11, 33 mục — cửa chống bịa được
  chấm bằng cách **GỌI THẬT** `viet_day_vua_khung` với LLM giả trả đúng các ca
  xấu). Thử phá `_pha_khop_video.py` 25 -> **36 phép: BẮT 11 · LỌT 0 · KHÔNG
  PHÁ ĐƯỢC 0** cho 11 phép mới.
  **LƯỢT PHÁ ĐẦU RA `LỌT 1`, VÀ CÁI LỌT LÀ LỖ CỦA CHÍNH CỔNG — chép lại vì nó
  đúng hình dạng lỗi v2.45.0:** gỡ dòng `viet_day=viet_day` khỏi thân
  `thay_giong_mot_video` thì **chữ ký VẪN ĐỦ**, mục "GỌI THẬT bắt TypeError"
  VẪN xanh, cổng VẪN 32/0 — trong khi ô người dùng bấm bị **NUỐT im lặng**.
  `inspect.signature` + gọi thật là **CHƯA ĐỦ**; phải đọc NÚT AST của LỜI GỌI
  (mục 11kaa). Kèm: `_pha_khop_video.py` nay **`compile()` lại bản đã phá** —
  bản phá lỗi cú pháp làm cổng chết lúc `import` và bảng ghi "BẮT" cho một
  chốt chưa hề chạm tới.
  **FILE NGHE THỬ:** `_NGHE_THU_ANH_HUNG/bon_chu/<video>/<giọng>/` — **16
  VIDEO**, 4 arm CÙNG một lượt chạy, tên kèm **cả bốn số** (im% · kt/s · CV% ·
  điểm đúng), **MD5 16/16 khác nhau**, chuẩn hoá cùng −14 LUFS bằng chính
  `chuan_do_to` rồi **đo lại bằng `loudnorm` chạy RIÊNG trên file thành phẩm**:
  I **−14,02 .. −15,35 LUFS**.
  **CHƯA ĐẠT, GHI THẲNG:** **chưa ai NGHE** một file nào — mọi số trên là số
  ĐO · **2 video × 90 giây × 1 lượt/arm**, mà `vnb:` + LLM đều KHÔNG tiền định
  nên đây là *một* điểm dữ liệu mỗi ô, **chưa có DẢI** (cột `C − A` chỉ −0,4
  điểm % thì rất có thể nằm gọn trong nhiễu lượt-khác-lượt, và bản thân dấu
  của nó đã đổi chiều ở lt2/EDGE) · **`lt1/EDGE` arm C đo ra TP `+4,99 dBTP`**
  (arm B `+0,93`) trong khi mọi arm khác âm — đỉnh vượt 0 dBTP là VỠ TIẾNG,
  **CHƯA TRUY RA**, và nó KHÔNG dính arm VNB là đường anh Hùng đi · mẫu là
  `test.wav` (giọng MÁY), **chưa đo trên mẫu thật của anh Hùng** · `diem_moi_
  tb` bị kéo tụt bởi phép ép `them=True -> 0,0` nên **đừng đọc nó là "bản đầy
  chỉ được 1,67/5"** — nó là *"4 câu bị gắn cờ bịa"* · chưa đo trên nguồn mà
  bản dịch bị lược NHIỀU (chỗ hướng này còn cửa).
- **VIỆC "ASR CẮT ĐÔI THÀNH NGỮ": TIỀN ĐỀ SAI — NGỮ CẢNH ĐÃ CÓ SẴN (28/08/2026,
  `_do_gop_dich.py`).** Ca đích danh `前脚…后葬` bị chặt thành #78/#79 và dịch ra
  *"chôn một chân"* / *"chân còn lại"*. Đề nghị là **gộp câu cho BẢN DỊCH** để
  LLM thấy đủ ngữ cảnh. **Đo ra thì không có gì để gộp:** video thật ra 163
  segment -> **167 câu**, chia **6 mẻ × 30 câu**, và **CẢ HAI cặp bị chặt đôi**
  (`刚…就` #12-13 · `前脚…后脚` #78-79) **nằm CÙNG MỘT MẺ** — tức cùng MỘT lượt
  gọi LLM, cùng một prompt. Ranh giới mẻ chỉ cắt ngang **5/166 = 3,0%** chỗ nối
  câu, và mỗi mẻ còn kèm `ME_NGU_CANH_BEN = 3` câu trước/sau + luật đã viết sẵn
  *"Câu ngắn/cụt là MỘT MẨU của câu dài đang nói dở"*.
  ⇒ **Model ĐÃ CÓ cả hai nửa mà vẫn dịch sai.** Gộp thêm là vá vào chỗ KHÔNG có
  bệnh. Bệnh nằm ở **HỢP ĐỒNG ĐẦU RA** (`một "t" cho mỗi "#i"` + *"KHÔNG gộp
  hai câu"*) ép model dịch từng câu như đơn vị độc lập — chữa được thì phải
  chữa ở PROMPT (cho phép dịch cả cụm rồi CHIA theo đúng ranh giới), không phải
  ở tầng cắt câu. **CHƯA LÀM:** tần suất chỉ **2/167 = 1,2%**, quá thấp để đo
  một bản vá prompt cho ra số tin được trong một lượt.
  Số kèm theo, đo trên chính video đó: **26,9% câu <= 8 ký tự** (khớp đúng con
  số đã ghi), ký tự/câu TB **12,2** · trung vị **11** · min **1**, giây/câu TB
  **2,35 s**, và **0 câu dài quá 12 s** -> `cau_tu_transcript` **chưa từng cắt
  một câu nào** trên nguồn này, nó chỉ đi qua.
- **`studio.db` CỤT: ĐO LẠI 28/08/2026 — DỮ LIỆU **CÒN ĐỦ TRONG BẢN SAO LƯU**,
  NHƯNG ĐƯỜNG CỨU BẰNG WAL ĐÃ ĐÓNG. CHỈ ĐO VÀ BÁO, KHÔNG TỰ CHỮA.**
  `%LOCALAPPDATA%\BQHungVideo\studio.db` = **118 KB**, sửa lần cuối **17/08
  08:35**, mở đọc được (10 bảng, không "malformed") nhưng **MỌI BẢNG 0 DÒNG** —
  projects/videos/clips/jobs/analysis/pipeline_files đều rỗng. Tức đây KHÔNG
  phải "DB vỡ", nó là **DB rỗng còn nguyên lược đồ**.
  **`studio.db-wal` nay 0 byte** (sửa 28/08 10:40) — lượt trước đo được nó trỏ
  tới trang 102141-102155 (cần file ~418 MB); WAL đã bị reset từ đó, nên **cứu
  bằng WAL không còn khả thi**. `-shm` 34 KB (28/08 09:20). App CÓ chạy sáng
  28/08 và đã ghi vào cái DB rỗng này.
  **CÒN 3 BẢN SAO LƯU TỰ ĐỘNG, CẢ 3 ĐỌC ĐƯỢC** (`dbmaint` chép trước mỗi lượt
  dọn, `tempsweep` giữ 3 bản):

  | file | cỡ | mtime | projects · videos · clips · jobs · analysis |
  |---|---|---|---|
  | `studio_backup_truoc_don_1787720831.db` | 460,57 MB | 25/08 16:46 | — |
  | `studio_backup_truoc_don_1787798665.db` | 441,74 MB | 27/08 09:44 | 143 · 2.689 · 6.793 · 97 · 14.607 |
  | **`studio_backup_truoc_don_1787881356.db`** | **421,21 MB** | **27/08 20:22** | **143 · 2.689 · 6.793 · 110 · 14.503** |

  Đọc bằng `sqlite3.connect("file:…?immutable=1", uri=True)` nên **không tạo
  `-wal`/`-shm`, không ghi một byte nào** vào thư mục của anh Hùng.
  **MẤT GÌ:** kênh / video / clip / mẫu **KHÔNG MẤT** — bản 27/08 20:22 còn đủ
  **143 kênh · 2.689 video · 6.793 clip · 1.566 pipeline_files**. Cái mất là
  **mọi thứ phát sinh SAU 27/08 20:22**, cụ thể là **4 job thay giọng sáng
  28/08** (job mới nhất trong bản sao lưu là `thay_giong done 27/08 04:56`).
  **Ổ ĐĨA KHÔNG CÒN ĐẦY:** C: còn **345,9 / 931,4 GB (37,1%)** · D: còn
  **251,2 / 931,5 GB (27,0%)** — tức nguyên nhân "ổ C đầy" của lần trước hiện
  KHÔNG tái hiện, và **chưa truy ra** vì sao file .db tụt về 118 KB.
  **KHÔNG TỰ CHỮA — anh Hùng phải TẮT APP thì mới đổi được file.** Việc phải
  làm khi anh ấy tắt app: đổi tên `studio.db` (+ `-wal`/`-shm`) rồi copy
  `studio_backup_truoc_don_1787881356.db` thành `studio.db`.
  (16/08/2026).** Cờ `thay_giong.DUNG_DICH_SOAT` có sẵn nhưng **mặc định TẮT**;
  `BQ_DICH_SOAT=1` chỉ để đo lại. Đường sống vẫn là `_dich_loat`.
  **VÌ SAO PHẢI ĐO LẠI DÙ ĐÃ CÓ "DO 3":** `_do_dich_ab.py` so `_dich_loat` với
  **`dich_theo_gio`** — KHÔNG phải `dich_va_soat`. Tức phần THƯỚC CHẤM
  (`cham_ban_dich` = hội đồng 3 model + cửa thuật ngữ 3 model) **chưa ai đo một
  lần nào**, mà nó chính là phần đắt. Và phải đo ở mức `dich_hau_kiem`, không
  phải mức hàm con: sau khi nối, `dich_hau_kiem` VẪN chạy tiếp
  `_dich_nguoc_cham` + vòng dịch lại + vòng CJK của chính nó.
  **`_do_dich_soat.py` — 3 lượt ĐAN XEN, video THẬT của anh Hùng**
  (`近期热播的7部新片推荐…mp4`, 107,24 s, 50 câu, Trung -> Việt), Groq +
  edge-tts THẬT:

  | chỉ số (TB 3 lượt) | MỐC (`_dich_loat`) | SOÁT (`dich_va_soat`) |
  |---|---|---|
  | ĐẠT theo thước % | 76,0 | 78,0 |
  | **còn chữ Hán** | **0,00** | **0,33** |
  | **câu < 20 ký tự (cụt)** | **1,33** | **3,00** |
  | câu > 60 ký tự (gộp) | 9,67 | 5,33 |
  | lệch \|s\| / câu | 0,762 | 0,511 |
  | TRÀN (đọc dài hơn khung) | 29,8 s | 16,7 s |
  | tổng đọc / tổng khung | 1,206x | 1,075x |
  | **LƯỢT LLM / video** | **5,0** | **54,7** |
  | **GIÂY (wall)** | **9,5** | **126,1** |

  **BỐN LÝ DO KHÔNG NỐI, theo thứ tự nặng:**
  (a) **Chất lượng KHÔNG tăng.** +2,0 điểm % nằm gọn trong **nhiễu 18,7%** của
  chính thước (DO 3 đo: 17/91 chuỗi Y HỆT khi ĐẠT khi TRƯỢT; chênh dưới ~5 điểm
  % là nhiễu). Tệ hơn: `dat_%` của arm SOÁT được chấm bằng **CHÍNH cái thước mà
  `dich_va_soat` dùng để chọn câu đi dịch lại** — dạy đúng bài thi, nên +2,0 còn
  là con số ĐƯỢC ƯU ÁI. Từng lượt: 76->80 · 78->78 · 74->76.
  (b) **Hai chỉ số ĐỘC LẬP (thước không với tới) XẤU ĐI.** `còn chữ Hán` 0,00 ->
  0,33 — MỐC sạch **3/3 lượt**, SOÁT để lọt 1 câu ở lượt 3; đó đúng là lỗi anh
  Hùng đã kêu *"dịch còn có cả tiếng Trung không hiểu"*. `cụt` 1,33 -> 3,00.
  Đổi câu gộp lấy câu cụt — cùng bệnh DO 3 đã ghi.
  (c) **GIÁ: 10,9x lượt Groq và 13,3x thời gian**, ổn định cả 3 lượt (5·5·5 so
  với 54·54·56). Với 200-300 kênh thì đó là 11 lần lượt cho một thứ không đo
  được là tốt hơn.
  (d) **Cái tốt DUY NHẤT (thời gian đọc) không đến từ thước, và app ĐÃ tự lo.**
  Phần lệch/tràn giảm là công của `dich_theo_gio` (dịch theo NGÂN SÁCH), DO 3 đã
  đo riêng nó ra 0,41 s/câu và tràn 10,36 s — **tốt hơn cả SOÁT** mà rẻ hơn
  nhiều. Quan trọng hơn: con số "tràn" ở đây đo trên **TTS THÔ**, trong khi
  đường sống còn bước **4b `rut_gon_vua_khung` + 4c `doc_nhanh_vua_khung`**
  (v2.27.0) xử đúng việc đó ở tầng TIẾNG — đo được `tempo_max` **1,017-1,027**
  và **chồng lấn 0 ms, 6/6 lượt**. Trả 11 lần lượt Groq để giải TRƯỚC một bài
  toán bước sau đã giải xong là lỗ.
  **NẾU SAU NÀY MUỐN ĐỘNG LẠI:** hướng đáng đo là nối **`dich_theo_gio` KHÔNG
  kèm thước** (lấy phần ngân sách thời gian, bỏ phần hội đồng chấm) — đó mới là
  chỗ có số. Nối cả `dich_va_soat` thì đã đo, đã trả lời: KHÔNG.
- **`dich_theo_gio` KHÔNG KÈM THƯỚC: ĐO XONG — *CŨNG KHÔNG NỐI* (16/08/2026).**
  Đây là hướng CUỐI CÙNG của đường dịch mà mục trên còn để ngỏ. Cờ
  `thay_giong.DUNG_DICH_GIO` (env `BQ_DICH_GIO=1`) **mặc định TẮT**, chỉ để đo
  lại. Đường sống vẫn là `_dich_loat`.
  **TỰ KIỂM ĐƯỜNG DỊCH LÀ BẮT BUỘC, ĐỪNG BỎ:** `_do_dich_soat.py` nay chạy
  `tu_kiem_duong()` TRƯỚC mọi lượt (vá 3 đích + `_dich_nguoc_cham`, **0 lượt
  LLM**) và DỪNG với mã thoát 2 nếu arm gọi sai hàm. Lý do: lượt đo trước từng
  báo "đã đo `dich_va_soat`" trong khi thật ra so `dich_theo_gio`. Thử phá (gỡ
  nhánh `elif DUNG_DICH_GIO`) -> ra đúng *"arm GIỜ -> gọi ['loat'] SAI"*, mã
  thoát **2**. Cổng không phải con dấu.
  **3 LƯỢT ĐAN XEN, cùng corpus đóng băng của mục trên** (`_do_dich_cache.json`
  = 50 câu THẬT của `近期热播的7部新片推荐…mp4`, 106,64 s, Trung -> Việt), Groq +
  edge-tts THẬT, đo ở mức `dich_hau_kiem`:

  | chỉ số (TB 3 lượt) | MỐC (`_dich_loat`) | GIỜ (`dich_theo_gio`) |
  |---|---|---|
  | ĐẠT theo thước % | **82,67** | **69,33** |
  | còn chữ Hán | 0,33 | **0,00** |
  | **câu < 20 ký tự (cụt)** | **1,33** | **5,67** |
  | câu > 60 ký tự (gộp) | 6,67 | 5,33 |
  | lệch \|s\| / câu | 0,721 | **0,465** |
  | TRÀN (đọc dài hơn khung) | 26,9 s | **12,7 s** |
  | tổng đọc / tổng khung | 1,166x | **1,021x** |
  | **LƯỢT LLM / video** | **5,0** | **12,3** |
  | GIÂY (wall) | 8,3 | 25,8 |

  **HAI RÀO CHẮN BỊ PHÁ, mỗi cái đủ để dừng:**
  (a) **CÂU CỤT TĂNG 4,3 LẦN** (1,33 -> 5,67) và tăng ở **CẢ 3/3 lượt**
  (1->7 · 1->5 · 2->5) nên KHÔNG phải nhiễu. Ký tự/câu TB tụt 43,0 -> 36,2:
  ngân sách thời gian ép chữ ngắn lại, và chỗ nó cắt vào là NGHĨA. Cùng bệnh
  "đổi câu gộp lấy câu cụt" mà `dich_va_soat` đã mắc.
  (b) **LƯỢT LLM 2,46x** (5,0 -> 12,3), trần đặt trước là 1,5x. Rẻ hơn hẳn
  `dich_va_soat` (10,9x) nhưng vẫn quá trần, và với 200-300 kênh thì đó là
  2,5 lần lượt Groq cho một thứ đo ra là XẤU HƠN.
  **`dat_%` TỤT 13,3 ĐIỂM — NGOÀI VÙNG NHIỄU.** Thước tự nhiễu 18,7% nên chênh
  dưới ~5 điểm % là nhiễu; 13,3 điểm thì không, và GIỜ thua ở **CẢ 3/3 lượt**
  (−18 · −4 · −18). Cả 4 trục đều thua (nghia 7,55 vs 6,86 · xuoi 7,84 vs 7,50 ·
  noi 7,54 vs 7,22 · tron 8,52 vs 7,86).
  **CÁI TỐT CỦA NÓ LÀ THẬT NHƯNG *KHÔNG CẦN NỮA*** — đúng lý lẽ đã dùng để bác
  `dich_va_soat`: tràn 26,9 -> 12,7 s và đọc/khung 1,166 -> 1,021x đo trên
  **TTS THÔ**, trong khi đường sống còn bước **4b `rut_gon_vua_khung` + 4c
  `doc_nhanh_vua_khung`** (v2.27.0) xử đúng việc đó ở tầng TIẾNG với
  `tempo_max` **1,017-1,027** và **chồng lấn 0 ms, 6/6 lượt**. Trả 2,5 lần
  lượt Groq + 4,3 lần câu cụt để giải trước một bài toán bước sau đã giải xong
  là lỗ — y hệt kết luận của `dich_va_soat`, chỉ khác con số.
  **MỘT CHỖ MỐC KHÔNG SẠCH, GHI THẲNG:** lượt này `_dich_loat` để lọt **1 câu
  còn chữ Hán ở lượt 3** (TB 0,33) trong khi lượt đo trước sạch 3/3, còn GIỜ
  sạch 3/3. Tức mệnh đề "mốc sạch 0,00" **KHÔNG tái lập được** — nó là kết quả
  NGẪU NHIÊN theo lượt dịch chứ không phải bất biến. Đừng lấy nó làm rào chắn
  cứng cho lượt sau; rào chắn đứng vững ở đây là CÂU CỤT và LƯỢT LLM.
  **CỘT `GIÂY` CỦA LƯỢT 2-3 BỊ NHIỄU, KHÔNG DÙNG ĐỂ KẾT LUẬN:** lúc đó máy đang
  tải + chạy thử bản `.exe` v2.29.0 song song. Lượt 1 (máy rảnh) ra **14,6 s vs
  9,7 s = 1,5x**; con số KHÔNG phụ thuộc máy là **LƯỢT LLM 2,46x**. Dùng cột đó.
  **ĐƯỜNG DỊCH COI NHƯ ĐÃ ĐÓNG:** cả hai hướng (`dich_va_soat` và
  `dich_theo_gio`) đều đã đo end-to-end và đều bị bác BẰNG SỐ. Muốn cải thiện
  chất lượng dịch thì phải tìm chỗ KHÁC, đừng đo lại hai hướng này.
- **MỐC TỪNG CHỮ CỦA PIPER LỆCH BAO NHIÊU — ĐÃ ĐO (16/08/2026,
  `_do_piper_moc_that.py`).** Cổng 64 chứng minh được mốc Piper *đúng thứ tự ·
  đúng số từ · tổng lệch <= 0,3 ms* nhưng **chưa có con số mili-giây nào so với
  THỰC TẾ** — mà "đúng tổng" vẫn có thể sai chỗ chia. Nay đo bằng ĐÚNG cách
  cổng 60 đã đo edge-tts: **cho Groq chép ngược CHÍNH file tiếng vừa đọc** rồi
  căn hai chuỗi từ bằng `SequenceMatcher`. Hai arm **đi chung cửa
  `dubbing._synth_all_words`** (không dựng đường riêng cho phép đo), 2 lượt ĐAN
  XEN, **426 mốc từ mỗi arm**, 14 câu Việt THẬT (bản dịch của chính video anh
  Hùng).
  **BẮT BUỘC TÁCH *LỆCH HỆ THỐNG* KHỎI *RUNG* — không tách là đọc ngược:**

  | | EDGE (mốc THẬT) | PIPER (mốc SUY RA) |
  |---|---|---|
  | khớp từ | 416/426 (98%) | 409/426 (96%) |
  | lệch \|ms\| TB (SỐ THÔ) | 60,4 | 65,1 (**1,08x**) |
  | trung vị · 90% · max | 52 · 110 · 300 | 52 · 150 · 235 |
  | **lệch HỆ THỐNG** | **−51,0 ms** | **+33,0 ms** |
  | **RUNG (trừ lệch hệ thống)** | **38,6 ms** | **59,1 ms (1,53x)** |
  | rung trung vị · 90% | 26 · 81 | 44 · **138 (1,70x)** |
  | trong ±50 ms sau khi trừ lệch | 311/416 (**75%**) | 228/409 (**56%**) |
  | **hiện MUỘN hơn tiếng >50 ms** | **2/416 (0,5%)** | **170/409 (42%)** |

  **SỐ THÔ 1,08x LÀ SỐ LỪA — hai lỗi NGƯỢC DẤU triệt tiêu nhau.** Đọc mỗi cột
  "TB" rồi kết luận "Piper ngang edge-tts" là sai.
  **−51,0 ms CỦA EDGE LÀ ĐỘ TRỄ *CỦA THƯỚC*, KHÔNG PHẢI LỖI CỦA EDGE-TTS:**
  `WordBoundary` là sự thật của chính máy đọc, nên phần lệch chung ấy là chỗ
  Groq đánh dấu đầu từ MUỘN hơn thực tế. Trừ ra thì rung thật của edge-tts =
  **38,6 ms — KHỚP với 35,1 ms cổng 60 đã ghi bằng một phép đo KHÁC** (cổng 60
  đo mốc ĐẦU CỤM, đây đo TỪNG TỪ). Hai phép đo độc lập gặp nhau = phương pháp
  đứng vững. **Đừng so thẳng 65,1 ms với 35,1 ms** — khác đơn vị đo.
  **NÓI THẲNG: PIPER TỆ HƠN THẬT — rung 1,53x, đuôi 90% 1,70x**, và lệch về
  phía KHÓ CHỊU: **42% số từ hiện MUỘN hơn tiếng** trong khi edge-tts chỉ
  0,5%. Nay hộp chọn giọng GHI THẲNG đánh đổi đó.
  **CHẨN ĐOÁN CŨ VỀ +33 ms LÀ SAI — ĐÃ VÁ, ĐÃ ĐO LẠI, VÀ *KHÔNG* CHỮA ĐƯỢC
  (16/08/2026).** Ghi đầy đủ vì đây đúng loại bẫy repo này hay sập.
  · **Chẩn cũ ("Piper cũng chèn lề im hai đầu như edge-tts") ĐÃ BỊ BÁC BẰNG SỐ.**
    `_do_piper_le_im.py` đo bằng **hai thước độc lập** — đọc thẳng mẫu WAV, và
    ffmpeg `silencedetect` qua `thay_giong.do_le_im` — trên cả câu lẫn **46 chữ
    rời**: lề đầu **0,000 s**, lề cuối **0,000 s**, `0,0 ms/chữ`. Piper **KHÔNG
    chèn lề im**. Vá theo lề im là vá vào chỗ KHÔNG CÓ BỆNH. Bắt được là nhờ
    mục **tự-kiểm 5d3** (bản vá đầu xanh hết, chỉ mục "lề có đủ lớn để hai mục
    trên có răng không" là đỏ) — không có mục tự-kiểm đó thì đã phát hành một
    bản vá rỗng kèm lời khoe.
  · **Im lặng của Piper nằm GIỮA CÂU, đúng chỗ DẤU PHẨY** (3 khoảng 100-140 ms
    = 4,8% câu trên câu 3 dấu phẩy). **Dấu CHẤM giữa dòng KHÔNG tạo nghỉ**
    (0/4 lượt). Và **chỗ nghỉ KHÔNG CỐ ĐỊNH** — Piper là VITS, bộ dự đoán độ
    dài có nhiễu: cùng một câu ra 2 hoặc 3 chỗ nghỉ tuỳ lượt (`_do_piper_nghi.py`,
    4 lượt/câu). Cổng nào chốt vào chỗ nghỉ mà chỉ chạy 1 lượt là **ĐỎ NHẤP
    NHÁY** -> cổng 64 mục 5i thử tới 3 lượt.
  · **BẢN VÁ ĐÃ NỐI:** `_co_gian` nay **trải mốc lên các KHOẢNG CÓ TIẾNG và
    NHẢY QUA chỗ nghỉ** (`khoang_co_tieng`, đọc mẫu chứ không gọi ffmpeg —
    hàng chục file/lượt). Bất biến mới, cổng 64 canh: **không chữ nào rơi gọn
    vào chỗ nghỉ** (5k) — cách cũ rải đều thì có, tức chữ hiện lúc máy đang im.
  · **NHƯNG NÓ KHÔNG CHỮA ĐƯỢC BỆNH — nói thẳng.** `_do_co_gian_ab.py` đo
    **GHÉP CẶP**: cùng một file tiếng, cùng một lượt Groq, chỉ khác phép tính
    (bắt buộc phải ghép cặp — nhiễu VITS + nhiễu Groq nuốt hết hiệu ứng nếu so
    hai lượt chạy rời). **413 mốc mỗi bên:**

  | | CŨ (rải đều) | MỚI (nhảy qua nghỉ) |
  |---|---|---|
  | lệch \|ms\| TB | 60,1 | 59,5 |
  | lệch HỆ THỐNG | +32,0 | **+36,0 (TỆ HƠN)** |
  | RUNG TB · 90% | 53,0 · 114 | 50,6 · **113** |
  | hiện muộn >50 ms | 156/413 (38%) | 161/413 (39%) |
  | **ghép cặp từng mốc** | — | **27 tốt lên · 32 TỆ ĐI · 354 y nguyên** |

    **Lý do rất đơn giản: corpus thật gần như KHÔNG CÓ chỗ nghỉ** — 4 chỗ,
    tổng **0,53 s / 90,64 s = 0,6%**. 354/413 mốc (86%) KHÔNG ĐỔI MỘT LY.
    Cơ chế có thật nhưng gần như không xảy ra trên câu anh Hùng đang dùng.
    **Giữ bản vá vì nó đúng và không làm tệ đi mức nào đáng kể, KHÔNG được
    kể nó là bản chữa.**
  · Cột end-to-end sau khi vá (cùng `_do_piper_moc_that.py`, 2 lượt đan xen,
    409 mốc): lệch hệ thống **+33,0 -> +29,0 ms** · RUNG **59,1 -> 57,7 ms** ·
    hiện muộn **42% -> 37%**. **ĐỪNG KHOE MẤY SỐ NÀY** — phép ghép cặp ở trên
    chứng minh phần lớn chênh lệch đó là **nhiễu chạy-khác-chạy của VITS**,
    không phải công của bản vá. Cột đối chứng EDGE tái lập gần như y hệt
    (hệ thống −51,0 -> −50,0 · rung 38,6 -> 38,7) nên phép đo đứng vững, máy
    rảnh thật; chỉ có phần quy công là không đứng vững.
  · **NGUYÊN NHÂN THẬT — TRUY ĐƯỢC MỘT NỬA, CÒN NỢ MỘT NỬA.** Chia lệch theo
    VỊ TRÍ trong câu (413 mốc, dữ liệu ghép cặp):

        1/5 câu:  thứ 1 → +22 ms · thứ 2 → +31 · thứ 3 → +32 · thứ 4 → +56
                  · thứ 5 → +41

    (a) **CÓ ĐỘ TRÔI THẬT, +22 -> +56 ms theo vị trí.** Trôi trong-câu thì
    thước có lệch hằng số cũng không giải thích được, nên đây là lỗi THẬT của
    `he = dai_that / tong`: nó rải đều phần dôi ra (chữ đọc rời ngắn hơn chữ
    trong câu −3,4%) lên MỌI chữ, trong khi phần dôi thật gần như dồn vào cuối
    câu (kéo dài âm cuối). **Hướng còn lại: đừng co giãn ĐỀU** — nhưng chưa
    thử, chưa đo, đừng ghi là đã biết cách.
    (b) **Ngay 1/5 ĐẦU đã +22 ms rồi**, mà lúc đó `he` mới đẩy được ~10 ms.
    Phần hằng số này **có thể là của THƯỚC chứ không của Piper**: cả bảng đang
    ngầm giả định độ trễ −51 ms của Groq là **không phụ thuộc giọng**, mà điều
    đó **CHƯA AI CHỨNG MINH** (Piper vào tiếng gắt hơn edge-tts thì Groq có thể
    đánh dấu sớm hơn). **Muốn chốt "Piper trễ hơn edge 84 ms" thì phải có
    thước THỨ BA độc lập.** Chưa có -> đừng nói chắc.
- **THỬ BẢN `.exe` v2.29.0 NHƯ MÁY NHÂN VIÊN — CHẠY ĐƯỢC (16/08/2026).**
  Tải asset thật từ GitHub Releases (`BQHungVideo-v2.29.0.zip`, **239.893.572
  byte**, SHA256 khớp `5579748a…15c9d`), giải nén ra thư mục tạm, chạy với
  `BQ_DATA_DIR` trỏ vào thư mục RỖNG (giả lập máy mới **và** để không đụng
  `%LOCALAPPDATA%\BQHungVideo` thật của anh Hùng).
  **KẾT QUẢ:** mở ra màn **Đăng nhập** -> đăng nhập -> cửa sổ chính
  *BQ Hung Video v2.29.0*, 110 MB RAM / 34 luồng. Nhận đúng máy (24 luồng ·
  31,8 GB · RTX 3060 · *ffmpeg Sẵn sàng*). **Không có `error.log`**,
  `crash_native.txt` chỉ có dòng đánh dấu mở app. Đóng bằng Alt+F4 -> thoát
  ÊM, **không hộp lỗi lúc tắt**, không bỏ lại ffmpeg mồ côi.
  · **`LICENSES.txt` CÓ trong bộ cài** — ở `_internal/LICENSES.txt`, 204 dòng,
    nêu ĐÍCH DANH đủ 8 mục (ffmpeg/ffprobe · frei0r · Piper+espeak-ng ·
    vais1000 · edge-tts · yt-dlp · kho tiếng động CC0 · phông OFL).
  · **Bộ đóng gói khớp kho nguồn**: `_internal/app/assets/sfx` = **186 file**,
    đúng bằng `app/assets/sfx` của repo. `ffmpeg.exe`/`ffprobe.exe` có mặt.
  · **NÚT TẢI PIPER BÁO ĐÚNG**: *"CHƯA TẢI (212 MB) — chọn giọng này thì app
    vẫn chạy nhưng sẽ đọc bằng giọng thường (edge-tts)"*. Đúng số đo 212,4 MB.
  · **Ô Demucs báo đúng theo cổng 58**: nêu đích danh *thiếu: torch, demucs,
    soundfile*, liệt kê NGUỒN TỪNG GÓI (đều KHÔNG CÓ), và `_lib` trỏ vào
    **DATA_DIR** chứ không phải `_internal` (bản vá CA5 chạy đúng trong bản
    đóng gói thật).
  · **THIẾU PYTHON 3 THÌ BÁO GÌ** (giả lập `frozen` + PATH rỗng): Demucs ->
    `cai_duoc=False` -> **nút tải BỊ KHOÁ** + câu *"Máy này không có Python/pip
    nên app không tự tải được: cài Python 3 rồi bấm lại, hoặc copy thư mục
    _lib từ máy đã cài sang"*. Piper -> `thieu` có thêm
    *`python3 (máy chưa cài Python)`*, `cai_piper()` trả
    *"Máy chưa cài Python 3 nên không tải được bộ đọc Piper."*
    **KHÁC BIỆT CÒN LẠI (nhỏ):** nút Piper **KHÔNG bị khoá** như nút Demucs —
    user bấm rồi mới nhận lời báo, thay vì thấy nút xám. Không im lặng nên
    không nguy hiểm, nhưng lệch chuẩn với Demucs.
  **2 LỖI GIAO DIỆN TÌM ĐƯỢC (đều CÓ SẴN, không phải hồi quy v2.29.0):**
  (a) **hộp xác nhận tải Demucs vẫn ghi *"khoảng 2 GB"*** trong khi nhãn nút
  ghi *155 MB* — cổng 58 đã đo lại (154,0 MB) và sửa `NHAN_TAI_DEMUCS` nhưng
  **sót 2 chỗ người dùng thấy** (`QMessageBox` + dòng báo tiến độ). Tức bấm nút
  ghi 155 MB rồi bị hộp doạ 2 GB ngay sau đó. **ĐÃ SỬA.**
  (b) nút `Copy` ở hàng Nguồn video **bị cắt chữ** (khung hẹp hơn nhãn), và 2
  nút cạnh nó là EMOJI trần (`✏` U+270F dòng 247 · `📊` U+1F4CA dòng 254 của
  `studio_page.py`). Máy này có phông màu nên hiện được, **nhưng đây đúng họ
  lỗi v2.6.22** ("xấu quá tự nhiên có cái ô đen") mà cổng 27 chỉ quét được vài
  hộp thoại. **CHƯA SỬA — ghi nợ**, vì đụng `studio_page.py` giữa lúc chưa
  duyệt là rủi ro không đáng.
- **CHE OAN TRÊN NGUỒN CAMERA CỐ ĐỊNH: ĐO XONG — *CHƯA ĐỦ CƠ SỞ, GHI NỢ*
  (16/08/2026, `_do_nguon_tinh.py`).** Ý tưởng: cửa tách chữ/nền mạnh nhất của
  quét-cả-khung là GIAO NHAU THEO THỜI GIAN, vốn giả định *"chữ đứng yên, nền
  TRÔI"*; camera cố định làm giả định đó sai. Thước đề xuất **tự chấm điểm
  chính cái cửa đó**: `ty_giu` = tỉ lệ điểm ảnh mặt nạ SỐNG SÓT sau
  `_loc_thoi_gian`. Gần 1,0 = lọc không bỏ đi gì = không còn tác dụng.
  **GIÁ BẰNG 0** (cả hai vế `do_vung_chu` đã tính sẵn, chỉ thêm 2 phép `.sum()`).
  **SỐ ĐO, 11 video có sự thật ghi bằng mắt:**

  | | `ty_giu` | `dong_khung` |
  |---|---|---|
  | jp_tuyet (**che oan 2 vùng**) | **0,9149** | 0,0343 |
  | 10 video sạch (0 oan) | 0,4137 .. **0,8923** | 0,0200 .. 0,1323 |

  **KHÔNG NỐI, VÌ BA LÝ DO — mỗi cái đủ để dừng:**
  (a) **Cả corpus chỉ có ĐÚNG 1 video che oan.** Đặt ngưỡng giữa 0,8923 và
  0,9149 là hiệu chuẩn theo **một điểm dữ liệu**, biên vỏn vẹn **0,023
  (2,3%)** — đúng loại "ngưỡng đặt mò" mà cổng 56/43 đã dặn đừng làm.
  (b) **Thước thứ hai NÓI NGƯỢC.** `dong_khung` (mức đổi giữa 2 khung liền
  nhau) của jp_tuyet là **0,0343**, nằm GỌN trong dải video sạch — không tách
  được gì. Hai thước độc lập không đồng ý thì chưa có kết luận.
  (c) **PHẢN VÍ DỤ GIẾT LUÔN GIẢ THUYẾT "camera tĩnh":** `jp_taxi` có
  `dong_khung` **0,0200 — THẤP NHẤT cả bộ**, tức đứng yên hơn cả jp_tuyet, mà
  nó dò **ĐÚNG 2/2 vùng, 0 oan**. Vậy "nguồn tĩnh" MỘT MÌNH không phải nguyên
  nhân của che oan. `ty_giu` (đo sức phân biệt CÒN LẠI của bộ lọc) là tín hiệu
  đúng hướng hơn — nhưng đúng hướng chưa phải là đủ số.
  **VIỆC TỒN, CẦN GÌ ĐỂ LÀM TIẾP:** thêm video camera-cố-định vào bộ đối chứng
  (hiện chỉ 1 ca xấu / 11). Có >= 4-5 ca xấu mà `ty_giu` vẫn tách rời thì mới
  đặt được ngưỡng; còn không thì **giữ nguyên cách chữa hiện tại: quét cả khung
  MẶC ĐỊNH TẮT** (ô tích trong Chỉnh mẫu + `BQ_CHE_TOAN_KHUNG`).
- **CỔNG 56 CA17a/CA17b HỎNG SẴN VÌ *NGƯỠNG CHI PHÍ*, KHÔNG PHẢI HỒI QUY
  (15/08/2026).** Lượt hồi quy v2.28.0: `_test_che_chu.py` ra **ĐẠT 120 ·
  HỎNG 2** (trước ghi 122/0), hỏng đúng 2 mục NGÂN SÁCH THỜI GIAN:

  | | mốc đã ghi (v2.27.0) | đo lại lượt 1 | lượt 2 | trần |
  |---|---|---|---|---|
  | TẮT | 6,65 s | 6,74 s | 6,79 s | — |
  | DẢI | **+0,84** s/phút | **+2,57** | **+2,54** | 2,0 |
  | HỘP | **+3,31** s/phút | **+5,46** | **+5,52** | 4,5 |

  **KHÔNG PHẢI HỒI QUY — chứng minh bằng git, không bằng lập luận:**
  `git diff v2.27.0..HEAD -- app/core/che_chu.py app/core/ffmpeg_utils.py`
  **RỖNG**, và `_test_che_chu.py` cũng KHÔNG đổi. Tức mã sinh ra con số này
  giống HỆT bản đã đo +0,84/+3,31.
  **CŨNG KHÔNG PHẢI MÁY BẬN:** 3 vòng thô trong mỗi lượt lệch nhau ≤ 0,10 s
  (TẮT [6,74·6,73·6,75] · DẢI [9,33·9,30·9,32]), CPU cả máy 22%, 0 tiến
  trình ffmpeg/prodown; và hai LƯỢT cách nhau vẫn ra ±0,03/±0,06.
  **CHỐT QUAN TRỌNG NHẤT VẪN ĐẠT:** CA17c (HỘP − DẢI ≤ 3,5 s/phút) ĐẠT ở
  +2,88 và +2,98 — đây mới là mục canh *"ai đó lỡ thêm một lượt ffmpeg THỨ
  HAI"* (lượt đó tốn 3,5-7,6 s/phút). Không ai thêm lượt nào.
  Dấu hiệu đáng ngờ nhất: **TẮT chỉ chậm 1,4% mà DẢI chậm 24%** — không phải
  máy chậm đều, nên nghi mốc +0,84 đo trên điều kiện khác (chính CLAUDE.md
  còn ghi một số KHÁC cho cùng việc: `_do_che_chu_gia.py` ra **+1,30**
  s/phút). **CẤM HẠ NGƯỠNG cho hết đỏ** — việc phải làm là đo lại đan xen
  trên máy rảnh rồi hiệu chuẩn lại trần bằng SỐ, đúng cách trần đó ra đời.
  **ĐÃ ĐO LẠI VÀ CHỐT — 16/08/2026: TRẦN ĐẶT ĐÚNG, THỦ PHẠM LÀ MÁY BẬN.**
  Đo trên máy THẬT SỰ RẢNH (CPU nền 2,7-5,4%), `_do_ca17.py` **7 vòng ĐAN XEN
  có XOAY THỨ TỰ** (CA17 chỉ 3 vòng và luôn chạy TẮT trước, nên arm chạy sau
  gánh phần máy đã nóng):

  | lượt                         | DẢI   | HỘP   | HỘP−DẢI |
  |------------------------------|-------|-------|---------|
  | mốc 14/08 (3 vòng)           | +0,84 | +3,31 |  +2,47  |
  | 16/08 cổng 56 (3 vòng)       | +0,78 | +3,20 |  +2,43  |
  | 16/08 `_do_ca17.py` (7 vòng) | +0,70 | +3,14 |  +2,45  |

  **BA lượt độc lập khớp nhau trong ±0,14 (DẢI) · ±0,17 (HỘP) · ±0,04
  (HỘP−DẢI)**; biên độ thô trong 7 vòng chỉ 0,13s / 0,17s. Phép đo TIỀN ĐỊNH
  khi máy rảnh -> `+2,57 / +5,46 / +4,60 / +10,66` là số của MÁY, không phải
  của MÃ.
  **GIỮ NGUYÊN cả 3 trần (2,0 · 4,5 · 3,5).** Biên còn lại: DẢI **2,4-2,9
  lần**, HỘP **1,36-1,43 lần**, HỘP−DẢI **1,42 lần**. Cố ý **KHÔNG siết xuống
  sát số đo** (max×1,25 ra 1,01 / 3,98 / 3,14) — siết là làm cổng dễ đỏ oan
  hơn với nhiễu máy, đúng cái vừa đi chữa. Cũng **KHÔNG nới lên** cho vừa
  +10,66: nới thế là vừa đúng chỗ cổng mất khả năng bắt "ai đó lỡ thêm một
  lượt ffmpeg THỨ HAI" (3,5-7,6 s/phút) — tức giết chính lý do trần tồn tại.
  **CHỮA Ở CHỖ ĐÚNG: `CPU_RANH_MAX` (15%) + `bo_qua()`.** CA17 nay đo CPU nền
  trước khi chạy; máy bận thì 3 mục chi phí **KHÔNG CHẤM** — không ĐẠT (đếm là
  ĐẠT thì đúng bằng "phép đo hỏng phát chứng nhận", bệnh `astats` cổng 53) và
  không HỎNG (đỏ vì máy bận là ĐỎ OAN, mà cổng đỏ oan thì người ta bỏ qua nó —
  bài học cổng 41 và 47). Số vẫn được IN RA để đọc, và dòng tổng kết hiện
  `BỎ QUA n` + liệt kê từng mục ở cuối nên một lượt bỏ qua **không thể trông
  giống** một lượt chấm đủ. Thử phá (`BQ_CPU_MAX=0`): ra đúng **BỎ QUA 3**.
  **QUY TẮC CHUNG rút ra: mục đo THỜI GIAN phải tự canh tải máy.** Không canh
  thì nó là cổng đo MÁY chứ không đo MÃ, và sẽ đỏ/xanh theo việc anh Hùng có
  mở trình duyệt hay không.
- **LỆCH CHỮ-TIẾNG: ĐO LẠI SAU BẢN VÁ — *KHÔNG* GIẢM. CON SỐ CHỈ ĐỔI CỘT
  (15/08/2026).** `c10c68b` đo được **24,2%** thời lượng video "chữ chạy mà
  không nói" (`im_duoi_chu` 22,52s + `lỗ bản chép lời` 9,56s = 32,08s /
  132,3s). `20d2a57` vá xong nhưng **chưa ai đo lại**. Nay đo lại **3 LƯỢT**
  trên ĐÚNG video mốc (`dy2.mp4`, 132,3s, Trung -> Anh, Groq + edge-tts thật;
  lượt 2/3 dùng lại stem Demucs nên rẻ):

  | lượt | `im_duoi_chu` | lỗ chép lời | TỔNG | % video | lệch đầu TB | chồng lấn |
  |---|---|---|---|---|---|---|
  | trước (mốc) | 22,52s | **9,56s** | 32,08s | **24,2%** | (bịa 0,0) | — |
  | l1 | 35,37s | **0,00s** | 35,37s | 26,7% | 43,4 ms | 0,0 ms |
  | l2 | 34,63s | **0,00s** | 34,63s | 26,2% | 43,6 ms | 0,0 ms |
  | l3 | 33,21s | **0,00s** | 33,21s | 25,1% | 42,7 ms | 0,0 ms |

  **NÓI THẲNG: 24,2% -> TB 26,0% = KHÔNG CHỮA ĐƯỢC, còn hơi xấu hơn.** Cột
  "lỗ chép lời" về 0 trông như thắng lợi, nhưng **9,56s đó không biến mất —
  nó CHUYỂN SANG cột `im_duoi_chu`**: câu #1 nay có khung **9,62s** mà tiếng
  chỉ **0,99s** (đúng bằng khoảng trống cũ `cau[1].end=3,06 -> cau[2].start=
  12,62`). Chia số đo làm 2 cột đã che mất điều đó — **thước duy nhất đáng
  tin là TỔNG**.
  Lệch KHÔNG rải đều: **6 câu chiếm 70%** toàn bộ (câu #1 8,63s · #25 3,70s ·
  #37 3,34s), đều là câu KHUNG RẤT DÀI mà tiếng ngắn. Muốn hạ con số này phải
  **chia nhỏ khung câu dài**, không phải chỉnh mốc.
  **CÁI THẬT SỰ CHỮA ĐƯỢC** là đường **che dải chữ cũ + VIẾT LẠI bản dịch
  theo `moc_tieng`** (`ecaaf9d`): chữ mới sinh từ chính giọng đã đọc nên
  không bao giờ chạy khi không có tiếng. Đã chứng minh BẰNG MẮT (xem mục che
  chữ trên đường thay tiếng). Đừng lẫn hai thứ: bản vá mốc làm số ĐO ĐƯỢC,
  bản vá che-và-viết mới làm người XEM hết thấy lệch.
  **CÁI TỐT LÊN VÀ ĐO ĐƯỢC:** `lech_dau_ms` không còn là hằng số bịa `0,0` mà
  là số đo thật **42,7-43,6 ms** (0 câu vượt 150 ms), và **chồng lấn 0,0 ms
  cả 3/3 lượt** — bất biến 0 ms vẫn giữ.
- **CỔNG 47 CA2 HỎNG SẴN VÌ *KHO VIDEO TRÊN ĐĨA ĐỔI*, KHÔNG PHẢI VÌ MÃ
  (14/08/2026).** `_test_hook_to_mo.py` báo `HỎNG 1`: *CA2 hook tò mò chọn
  được trên >= 60% video (**2/8**)* trong khi mục 47 ở trên ghi **4/8**.
  **ĐÃ BISECT, KHÔNG ĐOÁN:** trả CẢ `app/ai/hook_to_mo.py` LẪN `app/ai/
  recap.py` về `841c773` (bản anh Hùng đang chạy, TRƯỚC cả loạt vá CJK của
  cổng 52) -> **vẫn HỎNG 1, y hệt**; trả riêng từng file cũng vậy. Tức không
  phải hồi quy của cổng 52 mà cũng không phải của cổng 54.
  **GỐC: CA2 CHÉP LỜI LẠI BẰNG GROQ MỖI LẦN CHẠY** (41 key · 150 s audio/
  video) trên VIDEO THẬT đọc thẳng từ `D:\video ssmatool\…`. Kho video đó
  **đổi theo thời gian** (thư mục `video hàn` đã bị xoá, video mới thêm vào),
  nên mẫu số 8 video bây giờ KHÔNG còn là 8 video lúc hiệu chuẩn. Lần chạy
  này 6/8 video rơi vào cảnh *"KHÔNG MỘT CHỮ NÀO — nhạc/tiếng động"* hoặc
  không câu nào đủ tò mò -> giữ đường CŨ (đúng thiết kế), nên tỉ lệ tụt.
  Dấu hiệu rõ nhất kho đã lệch: video trong nhóm `han` được Groq chép ra
  **`Chinese`** và **`English`**.
  **ĐỪNG "CHỮA" BẰNG CÁCH HẠ NGƯỠNG 60%** — 3 mệnh đề chất lượng của CA2 vẫn
  ĐẠT sạch (*0 video nào hook mới tò mò THẤP HƠN hook cũ* · *0 video hook mới
  là câu chào/kêu gọi đăng ký*), tức bản thân bộ chọn hook không tệ đi. Cần
  **đóng băng corpus** (cache chép lời như `_do_hook_cache.json` đang làm cho
  các cổng khác) rồi mới nói được 4/8 hay 2/8 là số của MÃ hay của KHO.
  **HỒI QUY v2.27.0 (14/08/2026) — CỔNG NÀY NAY XANH: `TẤT CẢ ĐẠT`, mã thoát
  0, CA2 đo lại đúng `4/8`, phủ đủ 4 nhóm `anh · han · nhat · viet`.** Chính
  điều đó **XÁC NHẬN chẩn đoán ở trên**: không một dòng mã hook nào đổi giữa
  hai lượt, chỉ KHO VIDEO đổi (nhóm `han` đọc lại được). Nói cách khác cổng
  này **nhấp nháy theo kho đĩa** — thấy nó đỏ thì kiểm kho TRƯỚC khi nghi mã,
  và **đừng lấy một lượt xanh làm bằng chứng là đã chữa xong**; việc đóng băng
  corpus vẫn còn nguyên đó.
- **CỔNG 41 CÓ 1 CA HỎNG SẴN TỪ v2.20.0 — `sh_toi_vien` (09/08/2026).**
  `_test_shader.py` báo `51 OK · 1 FAIL`: *sh_toi_vien THẤY ĐƯỢC ở mức 'nhe'
  (>= 8,0%) — **5,07%** điểm ảnh |dY|>12 · PSNR 33,21 dB*.
  **CÁCH CHỨNG MINH "CÓ SẴN, KHÔNG PHẢI HỒI QUY" — DÙNG LẠI CHO LẦN SAU:** tạo
  `git worktree` ở ĐÚNG commit đã phát hành (`git worktree add <tmp> <sha>
  --detach`), nối `bin/` bằng junction (`mklink /J`, vì `bin/` và `.venv` bị
  gitignore) rồi chạy CHÍNH cổng đó bằng python của repo chính — file test tự
  `sys.path.insert(0, Path(__file__).parent)` nên nó nạp `app/` của BẢN MỐC.
  Kết quả ra **GIỐNG TỪNG CHỮ SỐ** (51 OK · 1 FAIL · 5,07% · 33,21 dB) = ca này
  hỏng sẵn trong bản anh Hùng đang chạy, và nó **TIỀN ĐỊNH** (không nhấp nháy).
  **ĐẦU MỐI ĐỂ CHỮA:** cổng 43 đo CHÍNH kiểu đó ra **15,86% (ĐẠT)** ở độ đậm
  0,25 — tức shader chạy tốt, chỉ là mức 'nhe' trên NGUỒN của cổng 41 quá nhạt.
  Vignette chỉ đổi VÙNG VIỀN nên ngưỡng 8% (đặt cho kiểu đổi toàn khung như
  `sh_hat_phim` 42,57%) có thể là ngưỡng SAI CHỖ. Xem thêm bài học cổng 36
  "mốc đo phải ở CẢNH SÁNG" trước khi kết luận là shader hỏng.
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
- **TIẾNG ĐỘNG NGHE ĐƯỢC TRÊN MỌI LOẠI NỀN — ĐÃ CHỮA 09/08/2026** (nhánh
  `sua-tieng-dong`; đo bằng `_do_sfx_3nen.py`, `_do_nen_clip.py`,
  `_do_han_dinh.py`, `_do_sfx_theo_nen.py`).
  **BỆNH**: v2.18.0 báo "+10..+17 dB" nhưng chỉ đo trên MỘT nguồn nền yên. Đo
  lại trên clip THẬT: bật/tắt tiếng động lệch **+0,6 / −1,1 / −0,0 / −1,6 /
  +2,4 dB** — **2/5 mốc NHỎ ĐI**. `tinh_gain_sfx` có 2 vế đá nhau ("đích =
  nền + 8 dB" vs "kẹp đỉnh <= −1 dBFS"); clip ồn thì **74% kho bị kẹp, thiếu
  trung vị 8,9 dB**.
  **5 NGUYÊN NHÂN, mỗi cái một số đo — sửa hết:**
  (a) **NỀN đo bằng `mean_volume`.** Với clip ồn `mean_volume` CHÍNH LÀ mức
  lời: đo −15,7 dBFS trong khi nền thật (bpv20 đường bao RMS 50 ms) là −26..
  −36. Nay `_do_muc_clip` trả **bpv20 = nền · bpv50 · bpv90 = MỨC LỜI · đỉnh**
  trong MỘT lượt ffmpeg (`asetnsamples`+`astats`+`ametadata`, tính trong C).
  (b) **Chuẩn hoá theo `mean` của FILE.** Kho là tiếng ngắn có đuôi ngân nên
  mean bị đuôi kéo xuống -> cùng hệ số mà file này to file kia mất hút (= cổng
  44 **nhấp nháy**, 5 lượt hỏng 1). Nay chuẩn hoá theo **ĐỈNH RMS 50 ms** (cột
  thứ 3 MỚI của `muc_do.json`, sinh bởi `tools/do_muc_sfx.py`). Đo 8 file trải
  crest 1,5..16,6 dB: lệch so đích **−0,4..+0,7 dB** (trước: hàng chục dB).
  (c) **Kẹp gain theo đỉnh giết độ to.** Crest ngắn hạn của kho trung vị
  **11,2 dB** -> "đỉnh lớp <= −1 dBFS" khoá RMS lớp mãi dưới −12 dBFS. Nay
  KHÔNG kẹp gain; giữ đỉnh bằng **`alimiter`** ở nhánh SFX **và một `alimiter`
  SAU KHI TRỘN**. Phải hạn sau khi trộn vì nguồn thật của anh Hùng đo được đỉnh
  **+0,51 dBFS** (bản TẮT của "Parker and Chester" — tức app đang xuất ra file
  MÉO SẴN); không lớp nào kẹp riêng mà cứu được. `alimiter` bắt buộc
  `level=0` (mặc định `level=true` TỰ NÂNG +3,1 dB) + `latency=1` (không có
  thì trễ **0,98 ms**, có thì **0,0 ms**).
  (d) **MẤT ĐÚNG 3,0 dB ÂM THẦM Ở MỌI TIẾNG ĐỘNG.** Kho là file MONO, `amix`
  ra stereo nên ffmpeg tự chèn phép đổi bố cục kênh nhân 1/căn2. App tính hệ số
  theo số đo rồi bị lấy mất 3 dB không một dòng báo (đo trên clip thật: lớp
  tiếng động luôn thấp hơn đích **−2,7..−3,1 dB**). Chữa bằng
  `pan=stereo|FL<FL+FC|FR<FR+FC` — toán tử `<` KHÔNG chuẩn hoá lại (đo: mono
  +3,0 dB · stereo 0,0 dB).
  (e) **DUCKING LÀ THỦ PHẠM CHÍNH của "mốc NHỎ ĐI".** Bướu nửa hình sin
  5 dB / 0,45 s / sớm 0,06 s **sâu nhất ở 0,225 s SAU mốc** — trùm đúng cửa sổ
  ±0,175 s mà tai (và máy đo) nghe cú va, trong khi cú va đã tắt. Nay
  **3 dB / 0,35 s / bắt đầu SAU mốc 0,15 s**: cú va tự xuyên qua, ducking chỉ
  dọn chỗ cho phần ngân (đo ngay tại mốc: **−0,78 dB**, bản cũ −5 dB).
  (f) **TIẾNG VÀO CHẬM KHÔNG ĐÁNH DẤU ĐƯỢC GÌ** (tìm ra khi chạy 5 lượt).
  Kho có tiếng đỉnh rơi **0,60 s SAU** lúc bắt đầu (`ding_soft_04_v2.opus`);
  chèn đúng giây điểm nhấn thì trong cửa sổ ±0,175 s nó chỉ có **−28,3 dBFS**
  thay vì −20,1 = hụt **8,2 dB**, nhật ký vẫn ghi "có tiếng". Nay `muc_do.json`
  có **cột 4 = GIÂY xảy ra đỉnh** (trung vị 0,10 s · bpv90 0,35 s · max
  0,60 s); app **ĐẨY SỚM** tiếng đúng bằng số đó để chỗ to nhất rơi vào đúng
  mốc, và **loại 18/184 file vào chậm hơn 0,35 s** khỏi điểm nhấn. Sau khi
  sửa: 12/12 lượt bốc ngẫu nhiên đều rơi trong **±0,9 dB** quanh đích.
  (g) **TRẦN HẠN ĐỈNH PHẢI BÁM ĐỈNH CỦA CHÍNH NGUỒN.** Hạ cứng về −2 dBFS thì
  lớp hạn đỉnh gọt luôn TIẾNG GỐC ở chỗ nguồn đang to -> đúng mốc điểm nhấn,
  bản BẬT lại thấp hơn bản TẮT (đo −0,9 dB, hỏng 2/5 lượt). Nay trần =
  `max(−2, min(−0,2, đỉnh_nguồn − 0,6))`.
  **BẤT KHẢ THI ĐÃ XÁC NHẬN, KHÔNG BỊA:** với nguồn đã master vượt 0 dBFS
  (bản TẮT của "Parker and Chester" xuất ra **+0,51 dBFS / 1 mẫu chạm trần** —
  app đang ra file méo sẵn TRƯỚC khi có tiếng động nào) thì **không thể vừa
  không hạ mốc điểm nhấn vừa giữ đỉnh <= −1 dBFS**. Luật đã chốt: *bản BẬT
  không bao giờ được méo hơn bản TẮT* (đo: BẬT +0,31 / 1 mẫu · TẮT +0,51 /
  1 mẫu), còn 2 nguồn còn chỗ trống thì **−3,63 và −1,66 dBFS, 0 mẫu**.
  **KẾT QUẢ ĐO trên 3 video THẬT** (nền yên/T.BÌNH/ồn — mean −25,8 / −16,2 /
  −16,6 dBFS): **12/12 mốc nổi ≥ +6 dB trên nền cục bộ** (thấp nhất **+9,0**,
  trước khi sửa có mốc +5,8) · **11/12 mốc to lên, 1 mốc đứng yên (−0,2 dB)** ·
  đỉnh file **−5,65 / +0,02 / −1,66 dBFS**, đều **THẤP HƠN bản TẮT** · lớp SFX
  luôn dưới 1,5x mức lời. Cổng 44 chạy **5 lượt liên tiếp ĐẠT cả 5**.
  **KHÔNG CÓ trên máy (ghi thẳng):** nội dung thật có `mean_volume` tới −10
  dBFS. Quét cả 28 video × 5 cửa sổ, to nhất là **−14,8 dBFS**. Ca "nền ồn"
  dùng đúng mức đó.
- **TIẾNG ĐỘNG BỊ *LỜI NÓI* CHE — ĐÃ CHỮA 09/08/2026** (nhánh `sfx-che-boi-loi`;
  đo bằng `_do_che_loi.py`, mốc đối chứng `BQ_MOC_TRUOC=7b1da35` = v2.19.0).
  **BỆNH**: anh Hùng chạy v2.19.0 vẫn chê *"âm thanh hiệu ứng nhỏ quá, dùng mà
  không nghe thấy luôn, **nói át rồi hay sao**"* — và anh ấy **đoán đúng**.
  v2.19.0 đo "NỔI TRÊN NỀN CỤC BỘ" (bpv20 = lúc IM LẶNG) nên 12/12 mốc đều
  ≥ +6 dB, cổng xanh, tai vẫn không nghe. **Tai không nghe so với nền, tai nghe
  so với THỨ ĐANG PHÁT CÙNG LÚC** — mốc rơi vào lúc đang nói thì thứ đó là
  GIỌNG NÓI, cao hơn nền 10-20 dB.
  **3 THƯỚC, phải phân biệt** (`_do_che_loi.py`): `NOI` = đỉnh(BẬT) − nền cục bộ
  (thước CŨ) · `SMR` = đỉnh(lớp SFX) − đỉnh(bản TẮT) · **`D_CHE` = dải nghe được
  to thêm bao nhiêu dB TẠI MỐC, so với THỨ ĐANG CHE** (bản TẮT đã bị ducking hạ
  — KHÔNG so với nguồn chưa hạ, xem bên dưới). Đo theo **5 DẢI TẦN**
  `<300 · 300-1k · 1k-2,4k · 2,4k-4k · >4k`, không chỉ RMS tổng: cộng 2 nguồn
  không tương quan thì dải to thêm `10log10(1+10^(SMR/10))` -> SMR −6 dB = +1,0
  dB (đúng ngưỡng vừa phân biệt) · SMR 0 = +3,0 dB (nghe rõ). Quy ước:
  **RÕ ≥ 3 dB · mờ ≥ 1 dB · KHÔNG < 1 dB** ở dải tốt nhất.
  **SỐ ĐO 13 mốc / 3 video THẬT** (nền yên −37,0 / T.BÌNH −21,8 / ồn −22,3 dBFS):

  | | ĐANG NÓI (9 mốc) | KHOẢNG LẶNG (4 mốc) |
  |---|---|---|
  | v2.19.0 · D_CHE trung vị / thấp nhất | +3,6 / **−1,5** dB | +26,3 / +9,7 dB |
  | v2.19.0 · nghe được | RÕ 5 · mờ 1 · **KHÔNG 3** | RÕ 4 |
  | NAY · D_CHE trung vị / thấp nhất | **+10,6 / +3,3** dB | **+31,0** / +5,6 dB |
  | NAY · nghe được | **RÕ 9 · mờ 0 · KHÔNG 0** | RÕ 4 |

  **5 NGUYÊN NHÂN, mỗi cái một số đo:**
  (a) **ĐÍCH TÍNH TỪ BÁCH PHÂN VỊ CỦA CẢ CLIP.** Mức lời CỤC BỘ tại mốc cao hơn
  bpv90 cả clip tới **+5,2 dB** (ca YEN: lời cả clip −19,6 nhưng tại mốc −14,4)
  trong khi đích bị trần `bpv90 + 3,5` khoá -> **đích thua giọng nói ngay từ
  công thức**. Nay `muc_tai_moc`/`nen_tai_moc`/`la_moc_dang_noi`: SÀN =
  `lời_cục_bộ + _SFX_TREN_LOI_MOC_DB` (1,5 dB), TRẦN vẫn "1,5× mức lời" nhưng
  lấy `max(lời_clip, lời_cục_bộ)` — bất biến CHỐNG ÁT LỜI giữ nguyên ý nghĩa,
  chỉ thôi tự khoá mình. Phân loại mốc: cục bộ hơn nền cục bộ ≥ `_SFX_DANG_NOI_DB`
  = 7 dB thì là ĐANG NÓI (đo: ca lặng +0,6..+6,2 · ca nói +7,6..+26,0 — 7 dB
  tách sạch 2 nhóm).
  (b) **TRẦN 1,5× MỨC LỜI KHÔNG PHẢI THỦ PHẠM — ĐỪNG NỚI NÓ.** Đã thử đẩy
  `_SFX_TREN_LOI_MOC_DB` lên +3: nguồn của anh Hùng có bản đỉnh −2,45 dBFS nên
  `alimiter` SAU KHI TRỘN gọt đúng vào cú va (lớp SFX mất **7 dB**, SMR tụt về
  **−6,3 dB** = TỆ HƠN lúc chưa sửa). Thủ phạm là cái ĐÍCH lấy theo cả clip, mốc
  (a). **DỌN CHỖ RẺ HƠN KÉO TO.**
  (c) **DUCKING ĐẶT SAI CHỖ Ở CA ĐANG NÓI.** v2.19.0 đẩy bướu ra SAU mốc (để cổng
  hết báo "mốc nhỏ đi") -> đúng lúc cú va đánh xuống thì giọng vẫn to hết cỡ.
  Nay tách 2 ca: mốc KHOẢNG LẶNG giữ nguyên bướu-sau-mốc v2.19.0 (đang tốt,
  +7,5 dB) · mốc ĐANG NÓI dùng `_SFX_DUCK_DB_NOI=6,0` / `_SFX_DUCK_DAI_NOI=0,45`
  / `_SFX_DUCK_SOM_NOI=0,225` = **đỉnh bướu rơi ĐÚNG vào mốc**, giọng đã hạ trọn
  6 dB trước khi cú va tới (cổng đo 4,2 dB ngay tại mốc). Sớm 0,10 s thì nguồn
  NÓNG vẫn hỏng 3/4 mốc — chưa đủ chỗ.
  (d) **CHỌN TIẾNG LỆCH DẢI TẦN VỚI GIỌNG** (`do_sang_sfx`, cột 6 `muc_do.json`):
  độ sáng = năng lượng trên 4 kHz so toàn dải; giọng dồn 300-3400 Hz nên tiếng
  sáng "được nghe không mất tiền". **A/B SẠCH ép đúng 1 file** (cùng clip ỒN,
  cùng mốc đang nói 4,40 s, cùng hệ số): `impactGlass_light` sáng −23,2 ->
  **D_CHE +9,6** · `impactGlass_medium_003` sáng −32,6 -> **+4,2** ·
  `boom_deep_05` sáng −56,3 -> **−0,5 = KHÔNG NGHE RA**. Tức sáng hơn 12 dB
  = nghe rõ hơn **5,4 dB** mà KHÔNG tốn thêm một dB độ to nào. Cửa
  `_SFX_SANG_DU=10` giữ 7/20 file nhóm `impact` (đủ để 3 Part không kêu giống
  nhau); cửa 8 dB còn 5 file (bắt đầu lặp), 15 dB nhận lại 16/20 = gần như
  không lọc. Ưu tiên TƯƠNG ĐỐI theo nhóm, không ngưỡng cứng — nhóm `impact`
  không có file nào ≥ −12 dB.
  (e) **LOA ĐIỆN THOẠI KHÔNG PHÁT ĐƯỢC DƯỚI 300 Hz** (`hut_qua_loa`, cột 5).
  Kho 184 file có **51 file hụt quá 6 dB**, tệ nhất `impact/boom_deep_05.opus`
  hụt **44,7 dB** — trên máy đo "to đúng đích", trên điện thoại **CÂM**. Dấu
  hiệu trong bảng đo: dải `<300` vọt **+22..+38 dB** còn mọi dải từ 300 Hz trở
  lên KHÔNG đổi. `_SFX_LOA_HUT_MAX=−6` loại 51 file, còn 133 để bốc.
  Kèm `_SFX_LOP_DUOI_TRON=3,0` (lớp SFX phải nằm dưới trần bản trộn 3 dB —
  `alimiter` gọt SỚM ở nhánh SFX thì rẻ, để lớp hạn CUỐI gọt thì nó hạ CẢ giọng
  nói đúng vào giây điểm nhấn) và `_SFX_TRAN_TRON_DB` −2,0 -> **−3,0** (đích cao
  hơn = limiter gọt sâu hơn = phần VỌT của AAC nở theo; đo ngay lúc chưa sửa:
  clip YÊN ra **+0,41 dBFS / 1 mẫu chạm trần** trong khi bản TẮT −4,84 / 0 mẫu,
  tức **bản BẬT MÉO HƠN bản TẮT** — phá đúng luật đã chốt).
  **BẪY ĐO ĐÃ SẬP KHI LÀM VIỆC NÀY (bản đầu của `_do_che_loi.py` sai):** thước
  "che lời" phải so với **THỨ ĐANG CHE**, tức bản TẮT **ĐÃ BỊ DUCKING HẠ**,
  không so với nguồn chưa hạ. So nhầm thì chính 6 dB ducking bị tính thành
  "tiếng động nhỏ đi" -> ca ĐANG NÓI ra `D_LOA` trung vị +5,5 dB trong khi thứ
  tai thật sự nghe là **+10,6 dB**. Bảng vẫn in cả 2 cột (`D_LOA` = so nguồn
  chưa hạ · `D_CHE` = so thứ đang che) để không ai lẫn lại.
  **KHÔNG MÉO HƠN BẢN TẮT** (đo cùng lượt): YEN **−3,01** dBFS / 0 mẫu (TẮT
  −4,84 / 0) · TBINH **−0,48** / 0 mẫu (TẮT **+0,11 / 1 mẫu** — nguồn đã master
  vượt 0 dBFS, đúng ca BẤT KHẢ THI đã ghi ở trên) · ON **−2,30** / 0 (TẮT
  −2,45 / 0). **KHÔNG ÁT LỜI**: ngoài cửa sổ mốc, dải giọng 300-4 kHz đổi nhiều
  nhất **+0,27 / +0,14 / +0,29 dB** trên 3 clip.
  **CỔNG 44 chạy 5 LƯỢT LIÊN TIẾP: ĐẠT cả 5** (68 mục/lượt, 0 hỏng, ~2 phút
  mỗi lượt) — không còn nhấp nháy.
  **ĐÃ CÂN NHẮC RỒI BỎ, ghi thẳng để đừng ai làm lại:** *dời điểm nhấn sang chỗ
  KHÔNG có lời*. Điểm nhấn HÌNH do `chon_hieu_ung` đặt theo cao trào CHUYỂN
  ĐỘNG; dời nó đi vài trăm ms để né giọng nói là **bỏ đúng cái khung đáng nhấn**
  và làm hình-tiếng lệch nhau — đắt hơn hẳn 3 cách (c)(d)(e) vốn đã đưa 3 mốc
  "KHÔNG NGHE RA" về 0.
- **CỔNG TEST PHẢI TRỎ VỀ BẢN MÃ CỦA CHÍNH NÓ.** 29 file `_test_*.py` từng ghi
  CỨNG `sys.path.insert(0, r"D:\claude\ai-content-studio")` (và `bin/ffmpeg.exe`,
  và các lần mở file mã nguồn để quét tĩnh). Chạy cổng từ một **git worktree**
  là đang kiểm **BẢN MÃ KHÁC** — nhánh đang sửa không hề được kiểm mà cổng vẫn
  XANH. Đo thật 08/08/2026: 8 cổng dây chuyền đều PASS trong khi chúng nạp
  `app/` từ repo chính, không đụng gì tới bản vá đang làm. Nay dùng
  `str(Path(__file__).resolve().parent)`. Viết cổng mới thì **đừng bao giờ ghi
  cứng đường repo**.
  **`git worktree remove` ĐI XUYÊN JUNCTION VÀ XOÁ `bin/` THẬT — ĐÃ XẢY RA
  19/08/2026, TÔI LÀM.** Cách dựng worktree ở mục cổng 41 dặn nối `bin/` bằng
  `mklink /J` (vì `bin/` bị gitignore). Dọn xong bằng `git worktree remove
  --force <wt>` thì nó theo junction vào và **xoá sạch `<repo>\bin`** —
  `ffmpeg.exe` · `ffprobe.exe` · `yt-dlp.exe` biến khỏi cây mã đang chạy sản
  xuất, trong khi 3 luồng khác đang gọi ffmpeg. Triệu chứng KHÔNG nói gì về
  nguyên nhân: cổng chết giữa MỤC 1b với `FileNotFoundError [WinError 2] The
  system cannot find the file specified`, đọc ra y như "cổng vừa hồi quy".
  **THỨ TỰ DỌN ĐÚNG:** `cmd /c rmdir "<wt>\bin"` (gỡ JUNCTION trước, **KHÔNG**
  `/s`) rồi mới `git worktree remove --force <wt>`.
  **PHỤC HỒI — LẤY TỪ `D:\BQHungVideo\_internal\` (CHỈ ĐỌC), cả 3 file
  `ffmpeg.exe` · `ffprobe.exe` · `yt-dlp.exe`.**
  **ĐỪNG LẤY TỪ `dist\BQHungVideo\_internal\` — lượt phục hồi đầu đã lấy ở đó
  và LẤY VỀ BẢN 2023-01-12**, vì `dist/` là sản phẩm của một lượt build CŨ nên
  nó chỉ chứa đúng cái `bin/` hồi đó có, không phải bản mới nhất. Sai lặng lẽ:
  8/8 filter vẫn đủ nên checklist ĐẠT, chỉ `Abs_Peak_count` là thiếu — xem khối
  cổng 86 để biết đủ 4 phép kiểm sau khi copy.
  Kiểm lại bằng `ffmpeg -filters` phải còn **`acrossover · xfade_opencl ·
  libplacebo · frei0r · rubberband`**; thiếu là mất nhóm hiệu ứng GPU + co giãn
  tiếng mà app vẫn chạy. Đã kiểm 8/8 filter sau khi phục hồi, cổng 78 về 52/0.
- **MỞ RỘNG KHO 09/08/2026 — điểm nhấn 27 -> 43 kiểu · chuyển cảnh GPU 21 -> 31**
  (nhánh `mo-rong-kho`; thước đo `_do_kho_moi.py`, 7 cổng, ở ĐÚNG 1080x1920).
  **16 kiểu điểm nhấn MỚI, tất cả là filter CÓ SẴN của ffmpeg = 0 byte tài
  nguyên**: `xien_hinh`(shear) · `phoi_canh`(perspective) · `nghieng_may`+
  `rung_xoay`(rotate) · `zoom_lui` · `luot_ngang`/`luot_doc`(whip pan) ·
  `meo_kinh_tt`(lenscorrection THUẦN, khác plugin frei0r cùng tên) ·
  `xao_khoi`/`xao_doc`(shufflepixels block/vertical) · `doi_o`(swaprect) ·
  `truot_hinh`(scroll) · `bac_sang`(posterize) · `mo_huong`(tmix) ·
  `mo_khoi_tt`(avgblur), cộng **1 frei0r MỚI** `xe_dong` (`pixs0r.dll`,
  19.408 byte, cùng gói MSYS2/GPL đã kèm).
  **CỔNG 43 chạy lại TOÀN KHO: ĐẠT 15 · HỎNG 0 — 43/43 kiểu ĐẠT**, thấy được
  **6,04 – 100%** điểm ảnh, rò ngoài cửa sổ ≤ 0,73%, không kiểu nào ra khung
  đen. 16 kiểu mới đo được **11,86 – 79,05%**.
  **KIỂU THAM SỐ frei0r phải DÒ, KHÔNG ĐOÁN** (`_do_f0r_thamso.py`):
  `frei0r=filter_params=` nhận 4 mã hoá khác nhau — `0.85`(double) · `y`/`n`
  (bool) · `0.1/0.2/0.3`(màu) · `0.25/0.75`(vị trí). Đưa sai kiểu là ffmpeg
  **chết cả lệnh**, mà ffmpeg KHÔNG in bảng tham số ra ở bất kỳ mức log nào ->
  phải "đầu độc" từng chỉ số rồi đọc tên trong lời lỗi.
  **10 KERNEL CHUYỂN CẢNH GPU MỚI** (gl-transitions, MIT, viết lại tay sang
  OpenCL): `gl_xoay_loc` · `gl_zoom_nhoe` · `gl_mat_ruoi` · `gl_soc_manh` ·
  `gl_cot_roi` · `gl_mo_mang` · `gl_o_gach` · `gl_to_ong` · `gl_kinh_van_hoa` ·
  `gl_song_buom`. **ĐO: 31/31 kernel render thật ra ĐÚNG 9/9 khung, 0 hỏng.**
  **VÌ SAO PHẢI QUÉT CẢ 31 CHỨ KHÔNG 1 (cổng 36 CA 9 đã sửa):** OpenCL biên
  dịch **CẢ FILE `.cl` một lượt** — một kernel mới sai cú pháp là hỏng TOÀN BỘ
  nhóm, `co_opencl()` trả False, nhóm GPU biến mất **IM LẶNG** (đúng bệnh "kho
  tự co 25 -> 14" ở cổng 37). Bản cũ chỉ render `next(iter(KHO_GPU))` nên lỗi
  nằm ở 10 kernel mới sẽ không bao giờ lộ ra.
  **`.spec` KHÔNG phải sửa**: nó đã khai cả thư mục `app/assets/hieu_ung`, nên
  `pixs0r.dll` và `gl_transitions.cl` tự vào bản .exe (đã kiểm, không suy đoán).
  **ANH HÙNG ĐÃ CHỐT: KHÔNG quét hết ~120 plugin frei0r** — phần lớn loè loẹt,
  chỉ lấy vài cái tốt.
- **NHÓM HIỆU ỨNG CHẠY TRÊN GPU (`app/core/hieu_ung_gpu.py`)**: `xfade_opencl` +
  kernel gl-transitions (MIT) **31 kiểu ĐO ĐẠT** (21 + 10 thêm 09/08/2026) ·
  `libplacebo` + shader GLSL tự
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
- **CPU-GIÂY CỦA TIẾN TRÌNH CON: ĐO KHÔNG ĐƯỢC TRONG PHIÊN AGENT — TỰ KIỂM
  BỘ ĐO TRƯỚC KHI IN BẢNG (19/08/2026).** `_do_cpu_probe.py` đốt **1,8 giây
  CPU thuần** trong một tiến trình con rồi hỏi lại ba bộ đo:
  `GetProcessTimes` (ctypes, đã khai đủ `argtypes`, đọc ngay sau `wait()`) ->
  **0,000s** · `psutil.Process.cpu_times()` -> **0,000s** ·
  `psutil.cpu_times()` **CẢ MÁY** -> **11,8s (DÙNG ĐƯỢC)**. Tức môi trường
  không cho đọc số liệu tiến trình con do chính phiên này đẻ ra — **không
  phải tiến trình con không tốn CPU**. Thay bằng CPU-giây cả máy rồi TRỪ NỀN
  đo ngay trước từng arm; nhưng nền phải THẬT SỰ đứng yên, luồng agent khác
  chạy giữa chừng là ra số vô nghĩa (đo được 33,4s và **266,9s** cho hai arm
  y hệt nhau).
  **BẪY ĐI KÈM, ĐÃ SẬP:** bản đầu ghi sổ **MỌI** `Popen` để cộng CPU, mà chính
  vòng poll VRAM gọi `nvidia-smi` bằng `subprocess.run` (= `Popen`) — arm chạy
  LÂU thì poll NHIỀU HƠN, nên cột "CPU-giây" hoá ra đo `nvidia-smi`: **38 tiến
  trình (2 luồng) vs 68 (lần lượt)** cho cùng 2 lượt gióng hàng, tự đẻ ra tỉ
  lệ **1,68×** không có thật. Lọc theo tên lệnh, và **luôn in số tiến trình
  đã ghi sổ** — con số đó là thứ tố giác.
- Quy tắc sắt: test bằng THÀNH PHẦN THẬT (LLM/ffmpeg/DB thật — mock từng giấu
  bug); đường ghép đoạn phải test thứ tự hook-first (ngược thời gian) + nguồn
  VFR; key API chỉ qua ENV, không ghi file, kiểm `git diff | grep gsk_` trước
  commit.
- **MỌI CỔNG PHẢI IN ĐƯỢC TIẾNG VIỆT KHI stdout BỊ CHUYỂN HƯỚNG RA FILE.**
  Chạy hồi quy hàng loạt là `python _test_x.py > file.txt`; lúc đó Python
  không còn console utf-8 nên lấy **cp1252** và dòng `print` tiếng Việt ĐẦU
  TIÊN ném `UnicodeEncodeError` -> cổng báo **mã thoát 1** trong khi mã app
  không sai chỗ nào. Chạy tay trong console thì LUÔN XANH, nên loại lỗi này
  cực dễ bị **đổ oan cho bản vá đang làm**. Đo 14/08/2026 khi chạy đủ 61 cổng:
  `_test_lane_starve.py` (1 giây) và `_test_clip_count_len.py` (0 giây) chết
  đúng kiểu đó. `_test_guard` đã reconfigure sẵn, nhưng cổng KHÔNG dựng UI thì
  không import nó -> phải tự `sys.stdout.reconfigure(encoding="utf-8")`.
- Test sandbox: đặt env `BQ_DB_PATH` + `BQ_DATA_DIR` sang thư mục tạm để không
  đụng dữ liệu thật (`%LOCALAPPDATA%\BQHungVideo` là data bản đóng gói).
- ĐÓNG GÓI: chạy `.venv-build\Scripts\python.exe -m PyInstaller BQHungVideo.spec --noconfirm --clean`. **KHÔNG dùng `.venv`** — venv đó không có PyInstaller, gọi vào là báo "No module named PyInstaller" mà `dist/` VẪN CÒN bản build cũ nên rất dễ tưởng đã build xong (sập bẫy 06/08/2026: dist/ là bản 22/07). Sau build phải KIỂM: đếm file trong `dist/BQHungVideo/_internal/app/assets/sfx` và xem ngày sửa của .exe.
- Chủ app: BQ Hung — trao đổi tiếng Việt; báo cáo phải kèm số đo thật.
