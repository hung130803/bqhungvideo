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
     **SỐ ĐO:** 2 video / **2 luồng 18,58s** · **lần lượt 26,55s** = nhanh
     **1,43×**; đỉnh job chạy cùng lúc **2** (làn 2 luồng) và **1** (làn 1
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
     **CHƯA ĐẠT, GHI THẲNG:** **chưa tải torch thật về `_lib`** (155 MB, máy anh
     Hùng đang chạy sản xuất) — cơ chế `--target`+`--ignore-installed` chứng
     minh bằng gói NHỎ `soundfile` (cố ý chọn nó vì `.venv` ĐÃ CÓ, đúng ca pip
     có thể bỏ qua) rồi **suy ra** cho torch · `BQHungVideo.spec` vẫn KHÔNG gói
     torch/demucs/`_lib` nên máy nhân viên vẫn phải bấm nút + phải có Python 3.
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
- **THƯỚC CHẤM DỊCH (`dich_va_soat`): ĐO END-TO-END XONG — *KHÔNG NỐI*
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
