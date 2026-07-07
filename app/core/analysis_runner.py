"""
Chạy LÕI PHÂN TÍCH cho MỘT video trong tiến trình con (subprocess) riêng.

Lý do: faster-whisper / mediapipe là thư viện native. Nếu chúng sập (segfault)
thì chỉ tiến trình con này chết, app chính (GUI) KHÔNG bị kéo theo. Tiến trình
cha (worker) đọc mã thoát + stdout để cập nhật tiến trình và đánh dấu job.

Giao thức stdout (mỗi dòng):
  PROGRESS\t<0..1>\t<thông điệp>
  DONE
  ERROR\t<thông điệp>

Chạy:  python -m app.core.analysis_runner <video_id> [force]
"""
from __future__ import annotations

import os
import sys

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


_limit_native_threads()


def _emit(p: float, msg: str) -> None:
    # Thay tab/newline để không vỡ giao thức
    msg = (msg or "").replace("\t", " ").replace("\n", " ")
    print(f"PROGRESS\t{p:.4f}\t{msg}", flush=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("ERROR\tThiếu video_id", flush=True)
        return 2
    video_id = int(sys.argv[1])
    force = len(sys.argv) > 2 and sys.argv[2] == "force"

    from app.queue.resource_manager import PROFILE, profile_dict
    from app.core.analysis import run_analysis

    try:
        run_analysis(video_id, profile_dict(PROFILE), on_progress=_emit, force=force)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR\t{e}", flush=True)
        return 1

    # run_analysis nuốt lỗi từng bước (đánh dấu 'failed' trong DB) — nhưng bước
    # SỐNG CÒN (chép lời) mà lỗi thì job phải THẤT BẠI, không được báo "Hoàn tất"
    # (các bước phụ scenes/audio/faces lỗi chỉ giảm chất lượng, không chặn).
    from app.core.analysis import analysis_status
    from app.database import db
    if analysis_status(video_id).get("transcript") == "failed":
        row = db.query_one(
            "SELECT error FROM analysis WHERE video_id=? AND kind='transcript'",
            (video_id,))
        err = (row["error"] if row and row["error"] else "không rõ nguyên nhân")
        print(f"ERROR\tChép lời thất bại: {err}", flush=True)
        return 1
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
