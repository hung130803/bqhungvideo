# 🎬 BQ Hung Video

Desktop app (PyQt6) sản xuất video ngắn từ **nội dung gốc của bạn** —
cắt highlight tự động, crop dọc 9:16 bám mặt người nói, và (các bước sau) phụ đề
karaoke, dịch đa ngôn ngữ, xuất đa tỷ lệ, đăng đa nền tảng.

Kiến trúc kiểu **pipeline agent, human-in-the-loop**: Input → AI phân tích →
từng bước xử lý, **mỗi bước bạn Duyệt / Sửa / Làm lại** trước khi sang bước sau.

> Trạng thái hiện tại: **Khung dự án + Lõi phân tích dùng chung + Queue/Worker pool
> + MODULE 1 (cắt highlight + face-track)** đã chạy end-to-end. Các module sau
> (M2–M7) sẽ bổ sung dần.

---

## ✨ Đã có gì

- **Lõi phân tích dùng chung** chạy **một lần** khi import video, cache vào SQLite,
  mọi module sau đọc lại (không phân tích lại):
  - Chép lời word-level (`faster-whisper`)
  - Dò chuyển cảnh (`PySceneDetect`)
  - Phân tích nhạc/beat/khoảng lặng (`librosa`)
  - Bám khuôn mặt theo frame (`mediapipe`)
  - Tách người nói (`pyannote`, **tùy chọn** — cần token HuggingFace)
- **Module 1 — Cắt highlight + Face-track**:
  - Chọn đoạn hay bằng **3 tín hiệu**: audio peak + chuyển cảnh + LLM chấm điểm viral
  - Crop dọc **9:16 bám mặt người nói** (không crop cứng giữa khung)
  - UI: danh sách clip kèm điểm, chỉnh in/out tay, Duyệt, Xuất, Xuất hàng loạt
- **Queue + Worker pool**:
  - Hàng đợi GPU riêng (2 job không tranh GPU)
  - **Bền vững**: tắt app/treo máy → mở lại chạy tiếp job dở
  - **Smart-skip** (trùng input + preset → bỏ qua), **retry** tự động khi lỗi, **hủy** giữa chừng
- **Resource manager**: tự dò CPU/RAM/GPU, tự đề xuất whisper model + encoder +
  số worker để **không treo máy** (cho phép override trong `.env`)
- **3 LLM provider** chọn được: OpenAI / Gemini / DeepSeek

---

## ⚠️ QUAN TRỌNG — Phiên bản Python

Hãy dùng **Python 3.11 hoặc 3.12** (đã kiểm tra cài được hết thư viện).
**TRÁNH 3.13/3.14**: `mediapipe` chưa có bản cài cho các phiên bản này, sẽ lỗi khi
`pip install`.

> Máy này đã có sẵn Python 3.12 → cứ dùng 3.12, không cần cài thêm.

Nếu cần tải mới: https://www.python.org/downloads/
(chọn **Windows installer 64-bit**, khi cài nhớ tick **"Add Python to PATH"**).
Kiểm tra: mở PowerShell gõ `py -3.12 --version`.

---

## 🚀 Cài đặt (Windows)

### ⭐ Cách dễ nhất — bấm đúp (khuyên dùng)
1. Bấm đúp **`setup.bat`** → tự tạo môi trường + cài thư viện + tạo `.env` (chạy 1 lần, lần đầu hơi lâu).
2. Mở **`.env`** bằng Notepad, điền API key (xem mục 3 bên dưới).
3. Bấm đúp **`run.bat`** → mở app.

Nếu `setup.bat` báo lỗi, làm theo cách thủ công bên dưới và gửi ảnh lỗi.

---

### 1. Cài ffmpeg
Cách dễ nhất, mở PowerShell:
```powershell
winget install Gyan.FFmpeg
```
Đóng và mở lại PowerShell, kiểm tra: `ffmpeg -version`.
(Nếu không dùng winget: tải ffmpeg, giải nén, rồi điền đường dẫn vào `FFMPEG_PATH`
trong file `.env`.)

### 2. Tạo môi trường ảo + cài thư viện
Mở PowerShell tại thư mục dự án (`D:\claude\ai-content-studio`):
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
> Lần đầu cài hơi lâu (mediapipe, torch...). Nếu một gói lỗi, xem mục **Khắc phục** bên dưới.

### ⭐ AI chấm điểm "viral" MIỄN PHÍ bằng Ollama (khuyên dùng nếu có GPU)

Thay vì gọi API tính phí/giới hạn (Gemini free chỉ 20 lượt/ngày), bạn chạy LLM
**ngay trên máy** — free vĩnh viễn, không giới hạn, không cần mạng:

1. Tải & cài Ollama: **https://ollama.com/download** (chọn Windows).
2. Mở PowerShell, tải model (RTX 3060 12GB chạy mượt):
   ```powershell
   ollama pull qwen2.5:7b
   ```
   (Muốn chấm thông minh hơn, hơi chậm hơn: `ollama pull qwen2.5:14b` rồi đổi
   `OLLAMA_MODEL=qwen2.5:14b` trong `.env`.)
3. Trong `.env` để `LLM_PROVIDER=ollama` (đã đặt sẵn). Xong — app tự dùng.

Ollama tự chạy nền sau khi cài. Kiểm tra: `python check_env.py` sẽ báo Ollama OK.

### 3. (Tùy chọn) Cấu hình API key đám mây
```powershell
copy .env.example .env
notepad .env
```
Điền `GEMINI_API_KEY` (hoặc OpenAI/DeepSeek) và chọn `LLM_PROVIDER`.
> Không có key vẫn chạy được M1 — app sẽ chấm điểm bằng heuristic (audio + cảnh)
> thay cho LLM, nhưng có key thì chọn đoạn "viral" thông minh hơn nhiều.

### 4. (Tùy chọn) Kiểm tra môi trường
```powershell
python check_env.py
```
Báo cho biết ffmpeg, các lib, GPU... đã sẵn sàng chưa.

### 5. Chạy app
```powershell
python main.py
```

---

## 🧭 Dùng thử (end-to-end)

1. **Bước 1 — Nhập video**: bấm *+ Project mới*, đặt tên → *+ Thêm video...* chọn
   file gốc → *Phân tích video đang chọn* (hoặc *Phân tích TẤT CẢ* để chạy hàng loạt).
2. Theo dõi **Hàng đợi công việc** ở dưới. Lõi phân tích chạy tuần tự trong 1 video,
   nhưng nhiều video chạy **song song** qua queue.
3. **Bước 2 — Lõi phân tích**: kiểm tra trạng thái từng bước, xem nhanh transcript.
   Cần thì *Phân tích lại*.
4. **Bước 3 — Module 1**: bấm *Tìm highlight* → AI đề xuất các clip kèm điểm và lý do.
   Chỉnh in/out nếu muốn → *Duyệt* → *Xuất clip (9:16)* hoặc *Xuất hàng loạt*.
5. Clip xuất ra nằm trong `projects/<tên-project>/clips/`.

---

## 🗂️ Cấu trúc dự án

```
ai-content-studio/
├── main.py                  # khởi động app
├── config.py                # cấu hình + đường dẫn + đọc .env
├── requirements.txt
├── .env.example
├── check_env.py             # kiểm tra môi trường
├── studio.db                # SQLite (tự tạo) — projects, jobs, kết quả phân tích, clips
├── projects/<project>/      # assets riêng mỗi project (audio, clips...)
└── app/
    ├── database/            # schema.sql + lớp truy cập SQLite
    ├── core/                # ffmpeg, transcribe, scene, audio, face, diarization,
    │                        #   analysis.py = orchestrator lõi phân tích dùng chung
    ├── ai/                  # llm.py (OpenAI/Gemini/DeepSeek)
    ├── queue/               # resource_manager, worker pool, jobs (đăng ký handler)
    ├── modules/             # m1_highlight.py (Module 1)
    ├── services.py          # API mức cao cho UI (project/video/enqueue)
    └── ui/                  # PyQt6: cửa sổ chính + các trang pipeline + panel queue
```

**Điểm tích hợp trung tâm là SQLite** (`app/database/schema.sql`): lõi phân tích ghi
vào bảng `analysis`, Module 1 đọc lại từ đó. Đây là cách các module liên kết mà
không phân tích lại hay mâu thuẫn nhau.

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
`register_handler()`, và thêm trang vào `app/ui/`.

---

## 🛠️ Khắc phục sự cố

- **`ffmpeg not found`** → cài ffmpeg (mục 1) hoặc điền `FFMPEG_PATH` trong `.env`.
- **`pip install` lỗi mediapipe/PyQt6** → gần như chắc do dùng Python 3.12+.
  Cài lại bằng Python 3.11 (mục ⚠️ ở trên).
- **Transcribe rất chậm** → máy chỉ có CPU. App đã tự chọn model nhỏ; có thể đặt
  `WHISPER_MODEL=tiny` trong `.env`. Có GPU NVIDIA sẽ nhanh hơn nhiều.
- **Bỏ qua "Tách người nói"** → bình thường nếu chưa đặt `HUGGINGFACE_TOKEN`.
  Diarization là tùy chọn, không ảnh hưởng M1.
- **Treo máy / hết RAM** → giảm `MAX_CPU_WORKERS` trong `.env` (vd `=1`).

---

## 📜 Nguyên tắc nội dung
App chỉ xử lý **tư liệu gốc do bạn sở hữu**. Nhạc nền do bạn tự nạp (free-to-use).
Đăng bài qua **API chính thức** của nền tảng (M7), không dùng bot trái phép.
