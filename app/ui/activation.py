"""Show the interactive app, including launches from older hidden updaters."""
from __future__ import annotations

import os


def _windows_api():
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.IsIconic.argtypes = [wintypes.HWND]
    api.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    api.SetForegroundWindow.argtypes = [wintypes.HWND]
    return api


def _reveal(api, hwnd) -> bool:
    # Preserve a maximized window; restore only if minimized. A second native
    # show overrides STARTUPINFO(SW_HIDE) inherited from v2.50.1/2 updaters.
    shown = api.ShowWindowAsync(hwnd, 9 if api.IsIconic(hwnd) else 5)
    api.SetForegroundWindow(hwnd)
    return bool(shown)


def show_interactive_window(widget) -> None:
    from PyQt6.QtWidgets import QApplication
    if widget.isMinimized():
        widget.showNormal()
    else:
        widget.show()
    widget.raise_()
    widget.activateWindow()
    if os.name == 'nt' and QApplication.platformName() == 'windows':
        _reveal(_windows_api(), int(widget.winId()))


def activate_existing(pid: int) -> bool:
    """Raise the existing login/main window without starting another worker."""
    if os.name != 'nt' or not pid:
        return False
    import ctypes
    from ctypes import wintypes
    api = _windows_api()
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    api.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    candidates = []

    @callback_type
    def visit(hwnd, extra):
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            title, cls = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(128)
            api.GetWindowTextW(hwnd, title, 512)
            api.GetClassNameW(hwnd, cls, 128)
            if (cls.value.startswith('Qt') and 'Popup' not in cls.value
                    and (title.value == 'BQ Hung Video — Đăng nhập'
                         or title.value.startswith('BQ Hung Video v'))):
                candidates.append(hwnd)
        return True

    api.EnumWindows(visit, 0)
    return any(_reveal(api, hwnd) for hwnd in candidates)
