"""Test the REAL login/instance path on a private Windows desktop, offline.

No self-check shortcut, login bypass, or user desktop windows. The hidden mode
reproduces the startup flags used by the v2.50.2 updater.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import psutil

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
parser = argparse.ArgumentParser()
parser.add_argument('--exe', type=Path)
parser.add_argument('--work-dir', type=Path)
parser.add_argument('--report', type=Path)
parser.add_argument('--expect-hidden', action='store_true')
args = parser.parse_args()
if os.name != 'nt':
    raise SystemExit('This startup regression needs Windows')
root = Path(__file__).resolve().parents[1]
area = (args.work_dir or Path(tempfile.gettempdir())) / ('bq-startup-' + uuid.uuid4().hex)
area.mkdir(parents=True)
command = ([str(args.exe.resolve())] if args.exe else
           [str(Path(sys.executable).with_name('pythonw.exe')), str(root/'main.py')])
desktop_name = 'BQStartup-' + uuid.uuid4().hex
api = ctypes.WinDLL('user32', use_last_error=True)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)

class StartupInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                ('lpReserved2', ctypes.POINTER(wintypes.BYTE)),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE)]

class ProcessInfo(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

kernel.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p,
    ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]

class Child:
    def __init__(self, info):
        self.pid, self.handle, self.returncode = info.dwProcessId, info.hProcess, None
    def poll(self):
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.returncode = None if code.value == 259 else code.value
        return self.returncode
    def wait(self, timeout):
        status = kernel.WaitForSingleObject(self.handle, int(timeout*1000))
        if status == 258:
            raise subprocess.TimeoutExpired(command, timeout)
        if status != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return self.poll()
    def terminate(self):
        if not kernel.TerminateProcess(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

api.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                              wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
api.CreateDesktopW.restype = wintypes.HANDLE
api.CloseDesktop.argtypes = [wintypes.HANDLE]
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
api.EnumDesktopWindows.argtypes = [wintypes.HANDLE, callback_type, wintypes.LPARAM]
api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
api.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
api.IsWindowVisible.argtypes = [wintypes.HWND]
api.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
api.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
desktop = api.CreateDesktopW(desktop_name, None, None, 0, 0x01FF, None)
if not desktop:
    raise ctypes.WinError(ctypes.get_last_error())
processes = []
checks = []

def windows(pid):
    found = []
    owners = {pid}
    try:
        owners.update(p.pid for p in psutil.Process(pid).children(recursive=True))
    except psutil.NoSuchProcess:
        pass
    @callback_type
    def visit(hwnd, extra):
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value in owners:
            title = ctypes.create_unicode_buffer(512)
            api.GetWindowTextW(hwnd, title, 512)
            if title.value == 'BQ Hung Video — Đăng nhập':
                found.append((hwnd, bool(api.IsWindowVisible(hwnd))))
        return True
    ctypes.set_last_error(0)
    if not api.EnumDesktopWindows(desktop, visit, 0) and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return found

def launch(folder, hidden):
    folder.mkdir(exist_ok=True)
    env = dict(os.environ, BQ_DATA_DIR=str(folder), BQ_DB_PATH=str(folder/'studio.db'),
               BQ_QSETTINGS_INI=str(folder/'settings.ini'), QT_QPA_PLATFORM='windows',
               SUPABASE_URL='https://startup-test.invalid', SUPABASE_ANON_KEY='offline-fixture',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', BQ_BO_MANG='1')
    # subprocess.STARTUPINFO does not expose lpDesktop; use CreateProcessW so
    # these real windows never appear on the user's desktop.
    startup = StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    startup.lpDesktop = desktop_name
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0 if hidden else 1
    environment = ctypes.create_unicode_buffer('\0'.join(f'{k}={v}' for k,v in sorted(env.items()))+'\0\0')
    info = ProcessInfo()
    if not kernel.CreateProcessW(command[0], ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),
            None, None, False, subprocess.CREATE_NO_WINDOW | 0x0400, environment, str(root),
            ctypes.byref(startup), ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    kernel.CloseHandle(info.hThread)
    process = Child(info)
    processes.append(process)
    (folder/'test-process.json').write_text(json.dumps({'pid':process.pid, 'desktop':desktop_name}), encoding='utf-8')
    return process

def await_window(process, visible, timeout=25):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        assert process.poll() is None, f'App exited before login: {process.returncode}'
        for hwnd, state in windows(process.pid):
            if state == visible:
                return hwnd
        time.sleep(0.1)
    raise AssertionError(f'Login visible={visible} not reached; windows={windows(process.pid)}')

def close(process):
    for hwnd, _ in windows(process.pid):
        api.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE: close only our fixture login.
    assert process.wait(timeout=15) == 0

try:
    if args.expect_hidden:
        process = launch(area/'baseline', True)
        await_window(process, False)
        time.sleep(1)
        assert windows(process.pid) and not any(v for _, v in windows(process.pid))
        checks.append('baseline reproduced: old updater hides the real login')
        close(process)
    else:
        for hidden in (False, True):
            folder = area/('hidden' if hidden else 'normal')
            process = launch(folder, hidden)
            hwnd = await_window(process, True)
            checks.append(('hidden updater' if hidden else 'normal launch') + ': real login visible')
            if hidden:
                # Hide the existing login, then double-launch the real app.
                # login.exec() first shows the native window; the zero-delay
                # activation callback then posts another ShowWindowAsync. Let
                # that startup event settle before simulating a later user hide.
                time.sleep(1)
                api.ShowWindowAsync(hwnd, 0)
                await_window(process, False)
                duplicate = launch(folder, True)
                assert duplicate.wait(timeout=25) == 0, 'Second instance did not exit normally'
                await_window(process, True)
                checks.append('second launch reveals existing login and exits without duplicate workers')
            close(process)
    result = {'ok': True, 'checks': checks, 'data_dir': str(area)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
finally:
    for process in processes:
        if process.poll() is None:
            try:
                for hwnd, _ in windows(process.pid):
                    api.PostMessageW(hwnd, 0x0010, 0, 0)
            except OSError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()  # Only a test child created above, never the installed app.
                process.wait(timeout=5)
        kernel.CloseHandle(process.handle)
    api.CloseDesktop(desktop)
