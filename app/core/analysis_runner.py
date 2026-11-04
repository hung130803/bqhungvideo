"""
Chạy LÕI PHÂN TÍCH cho MỘT video trong tiến trình con (subprocess) riêng.

Lý do: faster-whisper / mediapipe là thư viện native. Nếu chúng sập (segfault)
thì chỉ tiến trình con này chết, app chính (GUI) KHÔNG bị kéo theo. Tiến trình
cha (worker) đọc mã thoát và file trạng thái riêng để cập nhật tiến độ.
File trạng thái cũng hoạt động với bản windowed không có stdout.

Giao thức stdout dự phòng khi chạy từ dòng lệnh (mỗi dòng):
  PROGRESS\t<0..1>\t<thông điệp>
  DONE
  ERROR\t<thông điệp>

Chạy:  python -m app.core.analysis_runner <video_id> [force]
"""
from __future__ import annotations

import json
import os
import sys

from app.core.analysis_process import PROFILE_ENV, publish

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def _limit_native_threads() -> None:
    """NGÂN SÁCH LUỒNG cho lib native (numpy/torch/ctranslate2/onnx/mediapipe).

    Mặc định chúng mở luồng = SỐ NHÂN MÁY -> phân tích 1 video ăn 50-100% CPU.
    Phải set TRƯỚC khi import lib nặng (OpenMP đọc env lúc nạp DLL). Tôn trọng
    giá trị user tự đặt sẵn trong môi trường."""
    try:
        from config import settings
        eco = getattr(settings, "ECO_MODE", True)
    except Exception:  # noqa: BLE001
        eco = True
    cores = os.cpu_count() or 4
    n = max(2, min(4, cores // 4)) if eco else max(2, min(8, cores // 2))
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                "CT2_INTRA_THREADS"):
        os.environ.setdefault(var, str(n))



def _emit(p: float, msg: str) -> None:
    # Thay tab/newline để không vỡ giao thức
    msg = (msg or "").replace("\t", " ").replace("\n", " ")
    publish('progress', p, msg)
    if sys.stdout is not None:
        print(f"PROGRESS\t{p:.4f}\t{msg}", flush=True)


def main() -> int:
    try:
        publish('starting', 0., 'Đã mở tiến trình; đang nạp cấu hình phân tích')
        if len(sys.argv) < 2:
            raise ValueError('Thiếu video_id')
        video_id = int(sys.argv[1])
        force = len(sys.argv) > 2 and sys.argv[2] == 'force'
        _limit_native_threads()
        # Reuse the GUI's measured profile instead of running GPU/FFmpeg probes
        # again for every video in a forty-video queue.
        raw = os.environ.get(PROFILE_ENV)
        if raw is not None:
            profile = json.loads(raw)
            if not isinstance(profile, dict):
                raise ValueError('Cấu hình tiến trình phân tích không hợp lệ')
        else:
            publish('starting', 0., 'Đang kiểm tra phần cứng cho phân tích độc lập')
            from app.queue.resource_manager import PROFILE, profile_dict
            profile = profile_dict(PROFILE)
        publish('starting', 0., 'Đang mở dữ liệu và nạp bộ phân tích')
        from app.core.analysis import run_analysis, analysis_status
        from app.database import db
        _emit(0., 'Đã sẵn sàng; đang kiểm tra dữ liệu video')
        from app.core.job_resume import scope
        job_id = int(os.environ.get('BQ_RESUME_JOB_ID', '0') or 0)
        with scope(job_id, {'video_id': video_id, 'force': force, 'phase': 'analysis'}):
            run_analysis(video_id, profile, on_progress=_emit, force=force)
        if analysis_status(video_id).get('transcript') == 'failed':
            row = db.query_one(
                "SELECT error FROM analysis WHERE video_id=? AND kind='transcript'", (video_id,))
            err = row['error'] if row and row['error'] else 'không rõ nguyên nhân'
            raise RuntimeError(f'Chép lời thất bại: {err}')
        publish('done', 1., 'Phân tích dữ liệu video hoàn tất')
        if sys.stdout is not None:
            print('DONE', flush=True)
        return 0
    except Exception as e:
        publish('error', 0., str(e))
        if sys.stdout is not None:
            print(f'ERROR\t{e}', flush=True)
        return 1


if __name__ == '__main__':
    rc = main()
    # Thoát THẲNG, không để Python dọn thư viện native (whisper/mediapipe/torch):
    # bước dọn đó từng kẹt >10 s lúc ổ đĩa nghẽn -> cha báo "không đóng sau khi
    # kết thúc" dù kết quả đã lưu (27/10/2026). Cùng lý do main.py dùng os._exit.
    try:
        sys.stdout and sys.stdout.flush()
        sys.stderr and sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass
    os._exit(rc)
