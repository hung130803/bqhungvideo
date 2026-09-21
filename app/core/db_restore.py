"""Khôi phục snapshot được chọn, giữ cả bộ DB/WAL/SHM hiện tại để quay lui."""
from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import time
import uuid


def restore_snapshot(backup: Path, target: Path) -> Path:
    backup, target = Path(backup).resolve(), Path(target).resolve()
    if backup == target or not backup.is_file():
        raise ValueError('Chọn file sao lưu khác cơ sở dữ liệu đang dùng.')
    target.parent.mkdir(parents=True, exist_ok=True)
    work = target.parent / ('restore_' + uuid.uuid4().hex)
    work.mkdir()
    source = work / 'source.db'
    staged = work / 'verified.db'
    for suffix in ('', '-wal', '-shm'):
        p = Path(str(backup) + suffix)
        if p.exists():
            shutil.copy2(p, Path(str(source) + suffix))
    # Làm việc trên bản copy: SQLite có thể cần tạo/checkpoint WAL/SHM.
    connection = sqlite3.connect(str(source))
    output = sqlite3.connect(str(staged))
    try:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Bản sao lưu bị hỏng; chưa thay dữ liệu hiện tại.')
        required = {'projects', 'videos', 'clips', 'jobs'}
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(tables):
            raise RuntimeError('File chọn không phải DB đầy đủ của BQHungVideo.')
        connection.backup(output)
        if output.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Không tạo được snapshot khôi phục hợp lệ.')
    finally:
        output.close()
        connection.close()
    old = work / 'previous'
    old.mkdir()
    moved = []
    try:
        # Không để WAL của dữ liệu cũ gắn vào DB vừa khôi phục.
        for suffix in ('-wal', '-shm', ''):
            p = Path(str(target) + suffix)
            if p.exists():
                saved = old / p.name
                p.rename(saved)
                moved.append((saved, p))
        staged.rename(target)
    except Exception:
        for saved, original in reversed(moved):
            saved.rename(original)
        raise
    return old


def main() -> int:
    import argparse
    import os
    import psutil
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=str(Path(os.environ.get('LOCALAPPDATA', '.')) / 'BQHungVideo'))
    parser.add_argument('--backup')
    args = parser.parse_args()
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        if process.pid == os.getpid():
            continue
        name = (process.info['name'] or '').lower()
        command = ' '.join(process.info.get('cmdline') or []).lower()
        if name == 'bqhungvideo.exe' or ('python' in name and 'main.py' in command):
            raise RuntimeError('Đóng hoàn toàn BQHungVideo trước khi khôi phục dữ liệu.')
    data = Path(args.data_dir).resolve()
    if args.backup:
        selected = Path(args.backup)
    else:
        backups = sorted(data.glob('studio_backup*.db'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            raise RuntimeError('Không tìm thấy snapshot. Chỉ định --backup DUONG_DAN.')
        for i, file in enumerate(backups, 1):
            print(f'{i}. {file.name} | {file.stat().st_size / 1048576:.1f} MB | '
                  + time.strftime('%Y-%m-%d %H:%M', time.localtime(file.stat().st_mtime)))
        selected = backups[int(input('Chọn số bản sao muốn khôi phục: ')) - 1]
    print(f'Nguồn: {selected}\nĐích: {data / "studio.db"}')
    if input('Gõ KHOI PHUC để thực hiện (Enter để hủy): ').strip() != 'KHOI PHUC':
        return 0
    old = restore_snapshot(selected, data / 'studio.db')
    print(f'Đã khôi phục. Bộ dữ liệu cũ được giữ tại: {old}')
    return 0
