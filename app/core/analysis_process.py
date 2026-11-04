"""Local status channel for analysis workers, including windowed PyInstaller EXEs.

No stdout dependency: pythonw/windowed builds have sys.stdout=None. The parent
owns one private directory per child and reads atomic, bounded status snapshots.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

STATUS_ENV = 'BQ_ANALYSIS_STATUS_FILE'
PROFILE_ENV = 'BQ_ANALYSIS_PROFILE'
_PUBLISH_LOCK = threading.Lock()


def publish(kind: str, progress: float = 0.0, message: str = '') -> None:
    path = os.environ.get(STATUS_ENV)
    if not path:
        return
    with _PUBLISH_LOCK:
        _publish_locked(Path(path), kind, progress, message)


def _publish_locked(target, kind, progress, message):
    pending = target.with_suffix('.tmp')
    value = dict(kind=kind, progress=progress, message=str(message)[:4000],
                 updated=time.monotonic_ns())
    pending.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    # Windows can briefly hold the destination while the parent reads it.
    for attempt in range(5):
        try:
            os.replace(pending, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.02)


def read_status(path: Path) -> dict:
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.loads(f.read(16384))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _stop(proc) -> None:
    # Only this child's descendants; never touch unrelated download/export jobs.
    descendants = []
    try:
        import psutil
        descendants = psutil.Process(proc.pid).children(recursive=True)
    except Exception:
        pass
    if proc.poll() is None:
        proc.kill()
    for child in reversed(descendants):
        try:
            child.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def supervise(args, cwd, env, ctx, *, base=0., span=1., creationflags=0,
              startup_timeout=180., idle_timeout=1800., exit_timeout=10.,
              heartbeat=5., poll_interval=.25, idle_when_ready=False) -> None:
    from app.core.ffmpeg_utils import register_proc, unregister_proc
    ctx.check_canceled()
    ctx.progress(base, 'Đang khởi động tiến trình phân tích…')
    # ignore_cleanup_errors: tiến trình CHÁU bị giết muộn vẫn giữ stderr.txt ->
    # Windows không cho xoá; lỗi dọn KHÔNG được che mất lỗi/timeout thật.
    with tempfile.TemporaryDirectory(prefix='bqhung-analysis-',
                                     ignore_cleanup_errors=True) as temp:
        status = Path(temp) / 'status.json'
        child_env = dict(env)
        child_env[STATUS_ENV] = str(status)
        profile = getattr(ctx, 'profile', {}) or {}
        child_env[PROFILE_ENV] = json.dumps({k: profile[k] for k in
            ('whisper_model', 'device', 'compute_type') if k in profile})
        # stderr ra FILE (không DEVNULL): tiến trình con chết trước khi kịp ghi
        # status 'error' thì đây là dấu vết DUY NHẤT (27/10/2026: một lượt chết
        # "mã 1" giữa lúc máy cạn RAM mà không còn gì để biết vì sao).
        err_path = Path(temp) / 'stderr.txt'
        err_file = open(err_path, 'wb')
        proc = subprocess.Popen(args, cwd=cwd, env=child_env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=err_file, creationflags=creationflags)
        register_proc(proc)
        started = last_change = last_notice = time.monotonic()
        stamp = None
        record = {}
        ready = False
        terminal_at = None
        p, message = base, 'Khởi động bộ phân tích'
        try:
            while True:
                ctx.check_canceled()
                # Poll before the final read so DONE/ERROR cannot race process exit.
                code = proc.poll()
                new = read_status(status)
                now = time.monotonic()
                if new and new.get('updated') != stamp:
                    record, stamp = new, new.get('updated')
                    last_change = now
                    kind = record.get('kind')
                    if not ready and kind in ('progress', 'done', 'error'):
                        ready = True
                        if idle_when_ready:
                            _ha_uu_tien(proc)
                    if kind in ('done', 'error') and terminal_at is None:
                        terminal_at = now
                    value = float(record.get('progress', 0.))
                    if not math.isfinite(value):
                        value = 0.
                    p = base + span * max(0., min(1., value))
                    message = str(record.get('message') or message)
                    ctx.progress(p, message)
                    last_notice = now
                if code is not None:
                    if record.get('kind') == 'error':
                        raise RuntimeError('Phân tích lỗi: ' + str(record.get('message', '')))
                    if code != 0 or record.get('kind') != 'done':
                        raise RuntimeError(
                            f'analysis_worker_failed: Tiến trình phân tích đã dừng (mã {code}) '
                            'nhưng chưa xác nhận hoàn tất. Kết quả đã lưu được giữ nguyên.'
                            + _duoi_stderr(err_file, err_path))
                    return
                if (not ready and now - started > startup_timeout):
                    raise RuntimeError(
                        f'analysis_worker_timeout: Khởi động phân tích quá {int(startup_timeout)} giây. '
                        f'Bước cuối: {message}. Chưa tự thử lại.')
                if ready and now - last_change > idle_timeout:
                    raise RuntimeError(
                        f'analysis_worker_timeout: Không có tiến độ mới trong {int(idle_timeout)} giây. '
                        f'Bước cuối: {message}. Đã giữ kết quả; chưa tự gửi lại yêu cầu AI.')
                if terminal_at is not None and now - terminal_at > exit_timeout:
                    # 'done' chỉ được ghi SAU khi kết quả đã lưu xong vào DB, nên
                    # kẹt ở bước THOÁT (Python dọn thư viện native lúc ổ D nghẽn)
                    # không phải hỏng: tắt tiến trình, tính là xong. 27/10/2026
                    # bản cũ báo lỗi ở đây cho video đã phân tích xong.
                    if record.get('kind') == 'done':
                        _stop(proc)
                        return
                    raise RuntimeError('analysis_worker_timeout: Tiến trình phân tích không đóng sau khi kết thúc. '
                                       'Lỗi đã báo: ' + str(record.get('message', '')))
                if now - last_notice >= heartbeat:
                    ctx.progress(p, f'{message} · chờ {int(now-last_change)} giây; có thể bấm Hủy')
                    last_notice = now
                time.sleep(poll_interval)
        finally:
            try:
                if proc.poll() is None:
                    _stop(proc)
            finally:
                unregister_proc(proc)
                err_file.close()     # trước khi TemporaryDirectory xoá thư mục


def _ha_uu_tien(proc) -> None:
    """Khởi động xong mới hạ tiến trình con xuống IDLE.

    03/11/2026: 2 video lỗi 'Khởi động phân tích quá 180 giây' khi máy chạy 5
    lượt xuất + 7 luồng AI. Tiến trình con KHÔNG ghi được một dòng nào (log
    nguồn sống trống từ 10:09 tới 10:15) = kẹt trước cả dòng mã đầu tiên. IDLE
    kéo theo ưu tiên đĩa 'rất thấp', nên bước nạp hàng nghìn file .pyc/.dll bị
    5 ffmpeg đang ghi đĩa bỏ đói. Nay mở ở BELOW_NORMAL, sẵn sàng rồi mới IDLE
    (phần việc nặng vẫn nhường máy như cũ). Lỗi ở đây không được làm hỏng job."""
    try:
        import psutil
        psutil.Process(proc.pid).nice(psutil.IDLE_PRIORITY_CLASS)
    except Exception:  # noqa: BLE001
        pass


def _duoi_stderr(err_file, err_path, n=400) -> str:
    """Dòng cuối stderr của tiến trình con, để lời lỗi nói ĐƯỢC vì sao chết."""
    try:
        err_file.flush()
        duoi = err_path.read_bytes()[-n:].decode('utf-8', 'replace').strip()
    except OSError:
        return ''
    return (' Lỗi cuối: ' + ' '.join(duoi.split())) if duoi else ''
