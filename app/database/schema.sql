-- ============================================================
-- AI Content Studio - SQLite schema
-- Điểm tích hợp TRUNG TÂM: lõi phân tích ghi vào đây 1 lần,
-- mọi module sau ĐỌC LẠI (không phân tích lại cùng 1 video).
-- ============================================================

PRAGMA journal_mode = WAL;      -- cho phép đọc khi đang ghi (queue chạy nền)
PRAGMA foreign_keys = ON;

-- ---- Project: một phiên làm việc / một video gốc ----
CREATE TABLE IF NOT EXISTS projects (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    assets_dir    TEXT NOT NULL,          -- thư mục riêng chứa file của project
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---- Video import vào một project ----
CREATE TABLE IF NOT EXISTS videos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    src_path      TEXT NOT NULL,          -- đường dẫn file gốc
    file_hash     TEXT,                   -- hash để smart-skip (cùng input)
    duration      REAL,                   -- giây
    width         INTEGER,
    height        INTEGER,
    fps           REAL,
    has_audio     INTEGER DEFAULT 1,
    imported_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_videos_project ON videos(project_id);
CREATE INDEX IF NOT EXISTS idx_videos_hash ON videos(file_hash);

-- ============================================================
-- LÕI PHÂN TÍCH DÙNG CHUNG - cache theo video_id + kind.
-- kind: transcript | diarization | scenes | audio | faces
-- data: JSON. status: pending|running|done|failed|skipped.
-- Mỗi (video_id, kind) là duy nhất => không phân tích lại.
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id      INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    data          TEXT,                   -- JSON kết quả
    engine        TEXT,                   -- ví dụ: faster-whisper:small
    error         TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(video_id, kind)
);
CREATE INDEX IF NOT EXISTS idx_analysis_video ON analysis(video_id);

-- ============================================================
-- JOB QUEUE bền vững - tắt app mở lại chạy tiếp.
-- type: ví dụ "analyze", "m1_highlights", "m1_export_clip".
-- payload: JSON tham số. status: pending|running|done|failed|skipped|canceled.
-- dedup_key: cùng input + cùng preset => smart-skip.
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT NOT NULL,
    project_id    INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    video_id      INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    payload       TEXT,                   -- JSON
    status        TEXT NOT NULL DEFAULT 'pending',
    progress      REAL NOT NULL DEFAULT 0,    -- 0..1
    message       TEXT,                   -- dòng trạng thái hiển thị UI
    needs_gpu     INTEGER NOT NULL DEFAULT 0, -- 1 => xếp vào hàng đợi GPU riêng
    priority      INTEGER NOT NULL DEFAULT 0, -- số lớn chạy trước
    attempts      INTEGER NOT NULL DEFAULT 0,
    max_attempts  INTEGER NOT NULL DEFAULT 3,
    dedup_key     TEXT,
    result        TEXT,                   -- JSON kết quả khi xong
    error         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    started_at    TEXT,
    finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
-- UI poll mỗi 1.5s: _video_busy (video_id+status) + _video_status_marks
-- (project_id+status) — index để bảng jobs nhiều dòng lịch sử vẫn nhẹ tênh.
CREATE INDEX IF NOT EXISTS idx_jobs_video ON jobs(video_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id, status);

-- ============================================================
-- MODULE 1 - clip highlight đề xuất từ một video.
-- score: điểm viral 0..100. status: suggested|approved|rejected|exported.
-- ============================================================
CREATE TABLE IF NOT EXISTS clips (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id      INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_sec     REAL NOT NULL,
    end_sec       REAL NOT NULL,
    score         REAL,                   -- điểm viral tổng hợp
    reason        TEXT,                   -- LLM giải thích vì sao hay
    title         TEXT,                   -- tiêu đề gợi ý
    transcript    TEXT,                   -- lời thoại trong đoạn
    signals       TEXT,                   -- JSON: điểm audio/scene/llm thành phần
    status        TEXT NOT NULL DEFAULT 'suggested',
    export_path   TEXT,                   -- file 9:16 sau khi xuất
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_clips_video ON clips(video_id);

-- ---- Preset: combo cấu hình tái dùng (M1 và các module sau) ----
CREATE TABLE IF NOT EXISTS presets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    module        TEXT NOT NULL,          -- "m1", "m2"...
    data          TEXT NOT NULL,          -- JSON
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
