"""Tải có SHA256, kiểm archive, thay đồng bộ exe/thư viện và giữ bản rollback."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from typing import Callable, Optional

from config import DATA_DIR

ProgressFn = Optional[Callable[[int, int], None]]
UPDATES_DIR = DATA_DIR / 'updates'


class UpdateCanceled(Exception):
    pass


def can_auto_update() -> bool:
    return bool(getattr(sys, 'frozen', False) and
                (Path(sys.executable).parent / '_internal').is_dir())


def cleanup_leftovers() -> None:
    # Không xóa bản rollback hoặc staging: helper có thể vẫn đang dùng chúng.
    return None


def download(url: str, tag: str, on_progress: ProgressFn = None,
             is_canceled: Optional[Callable[[], bool]] = None,
             expected_digest: str = '', expected_size: int = 0) -> Path:
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', expected_digest):
        raise RuntimeError('Release chưa có SHA256 để kiểm tra. Mở trang tải hoặc chờ gói phát hành hợp lệ.')
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPDATES_DIR / ('update_' + uuid.uuid4().hex + '.zip')
    partial = destination.with_suffix('.partial')
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={'User-Agent': 'BQHungVideo-updater'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, partial.open('wb') as stream:
            header_size = int(response.headers.get('Content-Length') or 0)
            total = expected_size or header_size
            got = 0
            while True:
                if is_canceled and is_canceled():
                    raise UpdateCanceled()
                chunk = response.read(1 << 18)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
                got += len(chunk)
                if on_progress:
                    on_progress(got, total)
        if (total and got != total) or got < 1 << 20:
            raise RuntimeError('Gói tải về thiếu dữ liệu; giữ nguyên ứng dụng hiện tại.')
        if digest.hexdigest() != expected_digest.split(':', 1)[1].lower():
            raise RuntimeError('SHA256 không khớp; không cài gói cập nhật này.')
        partial.replace(destination)
        return destination
    finally:
        partial.unlink(missing_ok=True)


def extract(zip_path: Path) -> Path:
    output = UPDATES_DIR / ('new_' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        seen = set()
        members = archive.infolist()
        if sum(info.file_size for info in members) > 20 * (1 << 30):
            raise RuntimeError('Gói cập nhật vượt giới hạn 20 GB.')
        for info in members:
            path = PurePosixPath(info.filename.replace('\\', '/'))
            if (path.is_absolute() or '..' in path.parts or
                    any(':' in p or p.rstrip(' .') != p for p in path.parts) or
                    (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise RuntimeError('Gói cập nhật có đường dẫn không hợp lệ.')
            name = str(path).lower()
            if name in seen:
                raise RuntimeError('Gói cập nhật có tên file trùng.')
            seen.add(name)
        archive.extractall(output)
    for exe in output.rglob('BQHungVideo.exe'):
        if (exe.parent / '_internal').is_dir():
            return exe.parent
    raise RuntimeError('Gói cập nhật thiếu BQHungVideo.exe hoặc _internal.')


def launch_swap_script(new_dir: Path, zip_path: Path) -> None:
    from app.core.update_swap import SWAP_SCRIPT
    app_dir = Path(sys.executable).resolve().parent
    new_dir = new_dir.resolve()
    if not new_dir.is_relative_to(UPDATES_DIR.resolve()):
        raise RuntimeError('Nguồn cập nhật nằm ngoài vùng staging.')
    token = uuid.uuid4().hex
    script = UPDATES_DIR / f'apply_{token}.ps1'
    plan = UPDATES_DIR / f'apply_{token}.json'
    files = {}
    for p in new_dir.rglob('*'):
        if p.is_file():
            with p.open('rb') as stream:
                files[str(p.relative_to(new_dir))] = hashlib.file_digest(stream, 'sha256').hexdigest()
    plan.write_text(json.dumps({'source': str(new_dir), 'destination': str(app_dir),
        'exe': Path(sys.executable).name, 'processId': os.getpid(),
        'token': token, 'files': files, 'relaunch': True}, ensure_ascii=False), encoding='utf-8')
    script.write_text(SWAP_SCRIPT, encoding='utf-8-sig')
    subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive',
        '-ExecutionPolicy', 'Bypass', '-File', str(script), '-PlanFile', str(plan)],
        cwd=str(UPDATES_DIR), creationflags=subprocess.CREATE_NO_WINDOW |
        subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
