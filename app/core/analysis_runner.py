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

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


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
        print("DONE", flush=True)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR\t{e}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
