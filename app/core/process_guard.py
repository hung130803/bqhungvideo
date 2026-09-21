"""Deadline độc lập với stdout: tiến trình im lặng cũng dừng đúng hạn."""
from __future__ import annotations

import threading


class ProcessDeadline:
    def __init__(self, process, seconds: float):
        self.process = process
        self.expired = threading.Event()
        self.timer = threading.Timer(max(0.01, seconds), self._expire)
        self.timer.daemon = True
        self.timer.start()

    def _expire(self):
        if self.process.poll() is not None:
            return
        self.expired.set()
        terminate_tree(self.process)

    def cancel(self):
        self.timer.cancel()


def terminate_tree(process):
    """Không để tiến trình con giữ pipe mở sau khi tiến trình chính bị dừng."""
    try:
        import psutil
        children = psutil.Process(process.pid).children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.Error:
                pass
    except Exception:
        pass
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    except Exception:
        pass
