# 🎬 BQ Hung Video

App desktop (PyQt6) **cắt highlight video thành clip dọc ngắn** kiểu Opus Clip:
dán link YouTube hoặc chọn file → bấm **"Tạo clip"** → AI nghe-chép lời, chọn
đoạn hay, đặt tiêu đề → duyệt/sửa → xuất hàng loạt clip 9:16 kèm phụ đề karaoke,
tên file `Part 1, 2, 3...` sẵn sàng đăng.

Phát hành cho khách dạng **`.exe` đóng gói PyInstaller** qua GitHub Release
(kho `hung130803/bqhungvideo`) — app **tự kiểm tra và tự cập nhật** bản mới.

---

## ✨ Đã có gì

- **Một màn hình Studio duy nhất**, mọi thứ kỹ thuật chạy ngầm:
  - Quản lý theo **Kênh** (mỗi kênh TikTok = 1 mục riêng, clip xuất vào đúng thư mục kênh)
  - **Thêm video**: chọn file / kéo-thả, hoặc **dán link YouTube** — nút *Tải về*
    (1 link) hoặc *Tải nhiều* (mỗi dòng 1 link, tải xong tự phân tích/cắt luôn).
    Tải bằng `yt-dlp` + **hồ sơ cookie** (lưu nhiều tài khoản) + **PO-token**
    (bgutil) để né màn "Sign in to confirm you're not a bot"
  - **Tạo clip**: 1 video / *Tất cả video* / *Chọn nhiều* — phân tích + AI cắt
    tự chạy, ra danh sách clip có **điểm viral, tiêu đề, thanh đoạn giữ/bỏ**
  - **Editor** chỉnh từng clip; **Mẫu** khung/nền/chữ/phụ đề (có sẵn mẫu *Pro*
    giật tít + phụ đề vàng kiểu TikTok); **Tùy chỉnh cắt** (ngôn ngữ, độ dài
    min/max, số clip, mục đích, phong cách)
  - **Mixed-Cut**: nút ghép các **khoảnh khắc hay nhất khắp video** thành 1 clip
    dài kiểu "best moments"
  - **Xuất**: *Xuất video này* / *Xuất cả kênh*, hoặc bật **"Phân tích xong tự
    động xuất"**. File ra tại `<Kho video>/Đã xuất/<Kênh>/<video>/Part N <tiêu đề>.mp4`
- **Nâng chất clip** (bật trong Mẫu):
  - **Hook-first**: tự đưa 2-4s **cao trào nhất** lên đầu clip giữ chân người xem
  - **Nhạc nền tự động**: tắt / **ngẫu nhiên** từ thư mục nhạc của bạn (mỗi clip 1
    bài) / cố định — tự lặp+cắt khớp độ dài, trộn nhỏ dưới tiếng gốc
  - **Logo/watermark kênh**: đóng ảnh PNG lên góc mọi clip (chọn góc/cỡ/độ mờ)
  - **13 kiểu phụ đề** chạy chữ khớp lời (vàng nhảy, karaoke, neon, hồng Reels,
    đậm bóng đổ, hộp đen/trắng...) — bấm **Demo** xem trước ngay trong editor
  - **AI viết caption + hashtag**: nút *Caption* mỗi clip → tiêu đề giật tít +
    caption + hashtag để dán thẳng lên TikTok/Reels/Shorts (lưu được `.txt`)
- **AI cắt (LLM)**: 5 provider chọn được — **Groq (mặc định, free)** / Ollama
  (local) / Gemini / OpenAI / DeepSeek. Dán **nhiều key** (mỗi dòng 1 key) app
  tự **xoay vòng** khi hết quota; không có key vẫn chạy bằng heuristic
- **Nghe-chép lời (whisper)**: `WHISPER_PROVIDER=groq` (gửi lên mây, free,
  máy yếu nên dùng) hoặc `local` (faster-whisper chạy trên máy)
- **Queue + worker**: hàng đợi hiện tiến trình ở dock dưới; chỉnh số **Luồng AI /
  Luồng cắt** chạy song song ngay trên sidebar (kèm thông tin CPU/RAM/GPU/ffmpeg)
- **Đăng nhập tài khoản** (Supabase): bản phát hành nướng sẵn cấu hình → bắt
  đăng nhập; admin tạo/khóa/xóa tài khoản ngay trong app. Chưa cấu hình → mở thẳng
- **Tự cập nhật**: app tự thấy Release mới, tự tải, tự thay file, tự mở lại
  (xem mục [Cập nhật phiên bản](#-cập-nhật-phiên-bản))

---

## ⚙️ Hai chế độ chạy (`LIGHT_MODE`)

| | `LIGHT_MODE=1` (mặc định) | `LIGHT_MODE=0` |
|---|---|---|
| Dành cho | **Máy yếu** — dồn việc lên mây | Máy khỏe (nên có GPU) |
| Cần | Key **Groq** (free, lấy tại console.groq.com) | Cài đủ `requirements.txt` (faster-whisper, mediapipe, librosa, PySceneDetect...) |
| Làm gì | Groq chép lời + AI cắt; **bỏ** dò cảnh / phân tích âm thanh / bám mặt / chấm điểm bằng hình | **Full phân tích cục bộ**: crop 9:16 **bám mặt người nói**, chấm điểm audio/cảnh chính xác hơn, chấm viral bằng hình (Ollama vision) |

Bản `.exe` phát hành cho khách chạy chế độ nhẹ (build bằng `requirements-build.txt`,
không gói torch/mediapipe cho nhẹ). Đổi chế độ trong file `.env`.

---

## 📁 Dữ liệu nằm ở đâu?

- **Bản `.exe`**: `%LOCALAPPDATA%\BQHungVideo` — chứa `.env`, `studio.db`,
  projects, cookie, kho video mặc định. Tách khỏi thư mục app nên **cập nhật
  phiên bản không mất dữ liệu**.
- **Chạy từ mã nguồn (dev)**: ngay trong thư mục dự án.
- **Kho video**: nút *Kho video* chọn 1 thư mục gốc, app tự tạo `Đã tải`
  (video YouTube) và `Đã xuất` (clip thành phẩm) bên trong.

---

## 🚀 Cài đặt cho dev (Windows)

> Dùng **Python 3.12** (setup.bat gọi `py -3.12`). Tránh 3.13/3.14 — `mediapipe`
> chưa hỗ trợ (chỉ ảnh hưởng chế độ full `LIGHT_MODE=0`).

### ⭐ Cách dễ nhất — bấm đúp
1. Bấm đúp **`setup.bat`** → tự tạo `.venv` + cài `requirements.txt` + tạo `.env`
   (chạy 1 lần, lần đầu hơi lâu), cuối cùng tự chạy `check_env.py` kiểm tra.
2. Mở **`.env`** bằng Notepad, điền key (xem mục dưới).
3. Bấm đúp **`run.bat`** → mở app.

### Thủ công
```powershell
winget install Gyan.FFmpeg        # cài ffmpeg (bản .exe cho khách đã kèm sẵn)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # hoặc requirements-build.txt nếu chỉ cần chế độ nhẹ
copy .env.example .env            # rồi mở .env điền key
python check_env.py               # kiểm tra ffmpeg / lib / GPU
python main.py
```

### Cấu hình `.env` (chi tiết xem `.env.example`)
- `LLM_PROVIDER` — `groq` (mặc định) | `ollama` | `gemini` | `openai` | `deepseek`
- `GROQ_API_KEYS` — key Groq free; **nhiều key** mỗi dòng/dấu phẩy 1 key, tự xoay vòng
- `LIGHT_MODE` — `1` máy yếu (mặc định) / `0` full phân tích cục bộ
- `WHISPER_PROVIDER` — `local` | `groq`; `WHISPER_LANGUAGE` để trống = tự nhận
- `FFMPEG_PATH`/`FFPROBE_PATH` — chỉ cần khi ffmpeg không có trong PATH
- `AI_WORKERS` / `EXPORT_WORKERS` / `VIDEO_ENCODER` — để trống = app tự đề xuất

Dùng Ollama (LLM local, free, cần GPU): cài từ https://ollama.com/download,
`ollama pull qwen2.5vl:7b`, đặt `LLM_PROVIDER=ollama`.

Ngoài `.env`, khách chỉnh trực tiếp trong app qua nút **Cài đặt AI** và
**Tùy chỉnh cắt** — app tự ghi ngược vào `.env`.

---

## 🔄 Cập nhật phiên bản

### Phía khách (tự động)
Mỗi lần mở app, app tự hỏi GitHub Release (nền, im lặng nếu lỗi mạng). Có bản
mới → hiện hộp thoại kèm ghi chú phát hành:
- **Cập nhật ngay** → app tự tải zip (có thanh tiến trình), tự đóng, script nền
  thay file (`_internal` hoán đổi, có khôi phục nếu lỗi), rồi **tự mở lại bản
  mới**. Dữ liệu trong `%LOCALAPPDATA%\BQHungVideo` giữ nguyên.
- **Để sau** → đóng, không phiền.
- Bản dev / Release thiếu file zip → nút chuyển thành *Mở trang tải* (tải tay).

### Phía dev (phát hành)
1. Tăng `__version__` trong **`app/version.py`** (kho GitHub cũng khai báo ở đây).
2. Commit, tạo tag trùng phiên bản và đẩy lên:
   ```powershell
   git tag v1.2.2
   git push origin v1.2.2
   ```
3. CI (`.github/workflows/release.yml`) tự chạy trên `windows-latest`: cài
   `requirements-build.txt` + PyInstaller, tải kèm `ffmpeg/ffprobe/yt-dlp.exe`,
   đóng gói onedir `BQHungVideo`, nén `BQHungVideo-vX.Y.Z.zip` và tạo **Release**
   (release notes tự sinh). Máy khách sẽ tự thấy thông báo và tự cập nhật.

Cũng có thể bấm chạy tay workflow trên GitHub (`workflow_dispatch`).

---

## 🗂️ Cấu trúc dự án

```
ai-content-studio/
├── main.py                    # khởi động app (+ chế độ tiến trình con --analyze)
├── config.py                  # đường dẫn ROOT/DATA, đọc-ghi .env, Settings
├── requirements.txt           # đầy đủ (chế độ full LIGHT_MODE=0)
├── requirements-build.txt     # bản gọn để build .exe (chế độ nhẹ)
├── setup.bat / run.bat        # cài đặt / chạy 1 chạm cho dev
├── check_env.py               # kiểm tra môi trường
├── .github/workflows/release.yml  # tag v* -> build .exe -> GitHub Release
└── app/
    ├── version.py             # __version__ + owner/repo GitHub (tự cập nhật)
    ├── auth_config.py         # cấu hình Supabase (đăng nhập)
    ├── database/              # schema.sql + SQLite (projects, jobs, clips...)
    ├── core/                  # ffmpeg, phân tích, yt-dlp + potoken, updater,
    │                          #   self_update (tải zip + hoán đổi file)
    ├── ai/                    # llm.py (groq/ollama/gemini/openai/deepseek)
    ├── queue/                 # resource_manager + worker pool + jobs
    ├── modules/               # m1_highlight.py (Module 1)
    ├── services.py            # API mức cao cho UI
    └── ui/                    # main_window, studio_page (màn hình chính),
                               #   editor, login, update_dialog, queue_panel...
```

---

## 🧩 Lộ trình module tiếp theo

| Module | Nội dung | Trạng thái |
|--------|----------|-----------|
| M1 | Cắt highlight + face-track | ✅ Xong |
| M2 | Phụ đề karaoke + nhạc + beat sync | ⬜ |
| M3 | Dịch & lồng tiếng đa ngôn ngữ | ⬜ |
| M4 | Xóa nền thông minh | ⬜ |
| M5 | Voiceover & kịch bản AI | ⬜ |
| M6 | Digital human (gọi API) | ⬜ |
| M7 | Xuất đa tỷ lệ + đăng đa nền tảng | ⬜ |

Khung đã chừa sẵn chỗ: thêm file trong `app/modules/`, đăng ký handler qua
`register_handler()`, thêm UI vào `app/ui/`.

---

## 🛠️ Khắc phục sự cố

- **`ffmpeg not found`** (dev) → cài ffmpeg hoặc điền `FFMPEG_PATH` trong `.env`.
- **YouTube đòi đăng nhập** → nút **Cookie** trong app, dán cookie theo hướng dẫn
  (tiện ích "Get cookies.txt LOCALLY"), lưu 1 lần dùng mãi.
- **`pip install` lỗi mediapipe** → do Python 3.13+; dùng 3.12. Hoặc chỉ cần
  chế độ nhẹ thì cài `requirements-build.txt` là đủ.
- **Chép lời chậm/máy yếu** → đặt `WHISPER_PROVIDER=groq` (kèm `GROQ_API_KEYS`).
- **Treo máy / hết RAM** → giảm *Luồng AI* / *Luồng cắt* trên sidebar.

---

## 📜 Nguyên tắc nội dung
App chỉ xử lý **tư liệu bạn có quyền sử dụng**. Đăng bài qua **API chính thức**
của nền tảng (M7 sau này), không dùng bot trái phép.
