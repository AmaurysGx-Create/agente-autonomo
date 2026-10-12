"""Detecta la ventana en primer plano (proceso + título). Devuelve None si no se puede."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    process: str   # nombre del ejecutable, p. ej. "notepad.exe"
    title: str


def get_active_window() -> Window | None:
    try:
        if sys.platform == "win32":
            return _windows()
        if sys.platform.startswith("linux"):
            return _linux()
    except Exception:
        return None
    return None  # macOS: no soportado todavía


def _windows() -> Window | None:
    import ctypes
    from ctypes import wintypes

    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = u.GetForegroundWindow()
    if not hwnd:
        return None
    n = u.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    u.GetWindowTextW(hwnd, buf, n + 1)
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    proc = ""
    if h:
        size = wintypes.DWORD(1024)
        path = ctypes.create_unicode_buffer(1024)
        if k.QueryFullProcessImageNameW(h, 0, path, ctypes.byref(size)):
            proc = os.path.basename(path.value)
        k.CloseHandle(h)
    return Window(proc, buf.value)


def _linux() -> Window | None:
    """Requiere `xdotool` (X11). Sin él devuelve None."""
    def run(*a: str) -> str:
        return subprocess.run(a, capture_output=True, text=True, timeout=1).stdout.strip()

    wid = run("xdotool", "getactivewindow")
    if not wid:
        return None
    title = run("xdotool", "getwindowname", wid)
    pid = run("xdotool", "getwindowpid", wid)
    proc = ""
    if pid.isdigit():
        try:
            proc = open(f"/proc/{pid}/comm").read().strip()
        except OSError:
            pass
    return Window(proc, title)
