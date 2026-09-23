"""Read-only file presence checks, off the GUI thread. No media/DB mutations."""
from datetime import datetime
import os
from pathlib import Path
import stat
import threading

from PyQt6.QtCore import QObject, pyqtSignal


def presence(path):
    if not path:
        return 'unset'
    if not Path(path).is_absolute():
        return 'unknown'
    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode):
            return 'invalid'
        return 'present' if info.st_size > 0 else 'empty'
    except FileNotFoundError:
        return 'missing'
    except (OSError, ValueError):
        return 'unknown'


def fingerprint(record):
    return (record['path'], tuple(record.get('export_paths', ())))


def inspect_record(record):
    paths = record.get('export_paths', ())
    parts = [(path, presence(path)) for path in paths]
    return dict(key=fingerprint(record), source=presence(record['path']), parts=parts,
                checked_at=datetime.now().strftime('%H:%M:%S'))


SOURCE_LABELS = {'present': 'Còn file gốc', 'missing': 'Không thấy ở đường dẫn cũ',
                 'unknown': 'Không kiểm tra được', 'unset': 'Chưa có đường dẫn gốc',
                 'empty': 'File gốc 0 byte', 'invalid': 'Đường dẫn không phải file'}


def file_labels(record, result):
    if result is None or result['key'] != fingerprint(record):
        return 'Chưa kiểm tra file', record['parts']+' đã ghi', 'Bấm Kiểm tra file để đối chiếu các đường dẫn đã lưu.'
    counts = {}
    for _, status in result['parts']:
        counts[status] = counts.get(status, 0) + 1
    n = len(result['parts'])
    part_text = record['parts']+' đã ghi'
    if n:
        part_text += f"\n{counts.get('present', 0)}/{n} còn file"
    message = (f"Kiểm tra lúc {result['checked_at']}. Chỉ kiểm tra tồn tại/kích thước; "
               'chưa kiểm tra nội dung video. File không thấy có thể đã di chuyển hoặc ổ đĩa chưa kết nối.')
    if counts.get('unknown'):
        message += f" {counts['unknown']} Part không kiểm tra được quyền truy cập/đường dẫn."
    if counts.get('empty') or counts.get('invalid'):
        message += f" {counts.get('empty', 0)+counts.get('invalid', 0)} Part rỗng hoặc không phải file."
    return SOURCE_LABELS[result['source']], part_text, message


class FileInspector(QObject):
    """One bounded daemon worker; new requests replace queued work, stale results ignored."""
    result = pyqtSignal(int, int, object)
    finished = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending = None
        self._generation = 0
        self._working = False
        self._closed = False
        self.destroyed.connect(lambda: self.stop())

    def request(self, records):
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._pending = (generation, [dict(r) for r in records])
            if not self._working and not self._closed:
                self._working = True
                threading.Thread(target=self._run, daemon=True).start()
        return generation

    def stop(self):
        with self._lock:
            self._closed = True
            self._pending = None
            self._generation += 1

    def _run(self):
        while True:
            with self._lock:
                if self._closed or self._pending is None:
                    self._working = False
                    return
                generation, records = self._pending
                self._pending = None
            try:
                for record in records:
                    with self._lock:
                        if self._closed or generation != self._generation:
                            break
                    value = inspect_record(record)
                    self.result.emit(generation, record['id'], value)
                self.finished.emit(generation)
            except RuntimeError:
                # Parent window may have been destroyed while stat was blocked.
                self.stop()
