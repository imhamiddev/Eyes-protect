"""Thin, safe wrappers around the Win32 calls Eye Care needs.

Every function degrades to a harmless no-op on non-Windows platforms, so the
rest of the code (and the test-suite) can import this module anywhere.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

if IS_WINDOWS:
    import ctypes
    import winreg
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _MONITORINFOEXW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", ctypes.c_wchar * 32)]

    _MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HANDLE, wintypes.HDC,
                                          ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    _user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, _MONITORENUMPROC,
                                            wintypes.LPARAM]
    _user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MONITORINFOEXW)]
    _gdi32.CreateDCW.restype = wintypes.HDC
    _gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
    _gdi32.DeleteDC.argtypes = [wintypes.HDC]

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.GetDC.restype = wintypes.HDC
    _user32.GetDC.argtypes = [wintypes.HWND]
    _user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    _gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
    _gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL


def idle_seconds() -> float:
    """Seconds since the last keyboard or mouse input."""
    if not IS_WINDOWS:
        return 0.0
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return max(0.0, (_kernel32.GetTickCount() - info.dwTime) / 1000.0)


def set_gamma_ramp(ramp: list[list[int]]) -> bool:
    """Apply a 3x256 gamma ramp to the primary display. Returns success."""
    if not IS_WINDOWS:
        return False
    array = ((ctypes.c_ushort * 256) * 3)()
    for c in range(3):
        for i in range(256):
            array[c][i] = ramp[c][i]
    hdc = _user32.GetDC(None)
    if not hdc:
        return False
    try:
        return bool(_gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(array)))
    finally:
        _user32.ReleaseDC(None, hdc)


IDENTITY_RAMP = [[min(65535, i * 257) for i in range(256)] for _ in range(3)]


def reset_gamma() -> bool:
    ok = set_gamma_ramp(IDENTITY_RAMP)
    for mon in list_monitors():
        ok = set_monitor_gamma_ramp(mon.device, IDENTITY_RAMP) and ok
    return ok


@dataclass(frozen=True)
class Monitor:
    device: str       # e.g. \\.\DISPLAY1
    width: int
    height: int
    primary: bool


def list_monitors() -> list[Monitor]:
    """All attached displays (a single placeholder off Windows, for the UI and tests)."""
    if not IS_WINDOWS:
        return [Monitor("DISPLAY1", 1920, 1080, True)]
    found: list[Monitor] = []

    def callback(hmon, _hdc, _rect, _data):
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if _user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            found.append(Monitor(info.szDevice, r.right - r.left, r.bottom - r.top,
                                 bool(info.dwFlags & 1)))
        return 1

    cb = _MONITORENUMPROC(callback)
    _user32.EnumDisplayMonitors(None, None, cb, 0)
    found.sort(key=lambda m: (not m.primary, m.device))
    return found


def set_monitor_gamma_ramp(device: str, ramp: list[list[int]]) -> bool:
    """Apply a gamma ramp to one specific display."""
    if not IS_WINDOWS:
        return False
    array = ((ctypes.c_ushort * 256) * 3)()
    for c in range(3):
        for i in range(256):
            array[c][i] = ramp[c][i]
    hdc = _gdi32.CreateDCW("DISPLAY", device, None, None)
    if not hdc:
        return False
    try:
        return bool(_gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(array)))
    finally:
        _gdi32.DeleteDC(hdc)


def set_autostart(enabled: bool, command: str, name: str = "EyeCare") -> bool:
    """Add/remove the app from the current user's Run key."""
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def is_autostart_enabled(name: str = "EyeCare") -> bool:
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, name)
            return True
    except OSError:
        return False


def system_uses_light_theme() -> bool:
    """True if Windows apps are currently in light mode (defaults to False)."""
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY) as key:
            return bool(winreg.QueryValueEx(key, "AppsUseLightTheme")[0])
    except OSError:
        return False


def set_system_light_theme(light: bool) -> bool:
    """Switch Windows apps + system UI between light and dark mode."""
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            for name in ("AppsUseLightTheme", "SystemUsesLightTheme"):
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1 if light else 0)
        # Tell running apps the setting changed.
        HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x001A, 0x0002
        _user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "ImmersiveColorSet",
            SMTO_ABORTIFHUNG, 100, None,
        )
        return True
    except OSError:
        return False


_mutex_handles: list = []


def create_single_instance_mutex(name: str = "EyeCareSingleInstanceMutex") -> bool:
    """Create a named mutex so the installer can detect a running app."""
    if not IS_WINDOWS:
        return False
    handle = _kernel32.CreateMutexW(None, False, name)
    if handle:
        _mutex_handles.append(handle)  # keep it alive for the process lifetime
    return bool(handle)


def notification_state() -> int | None:
    """SHQueryUserNotificationState: 2/3/4/7 = full-screen app, game or presentation,
    6 = quiet time (Focus assist). None when unavailable."""
    if not IS_WINDOWS:
        return None
    state = ctypes.c_int(0)
    try:
        hr = _shell32.SHQueryUserNotificationState(ctypes.byref(state))
    except OSError:
        return None
    return state.value if hr == 0 else None


def foreground_info() -> tuple[int, str, str] | None:
    """(process id, lower-case exe name, window title) of the foreground window."""
    if not IS_WINDOWS:
        return None
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD(0)
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title_buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, title_buf, 512)
    exe = ""
    handle = _kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if handle:
        try:
            size = wintypes.DWORD(1024)
            buf = ctypes.create_unicode_buffer(1024)
            if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                exe = buf.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
        finally:
            _kernel32.CloseHandle(handle)
    return pid.value, exe, title_buf.value


def register_hotkey(hotkey_id: int, modifiers: int, vk: int) -> bool:
    """Register a thread-level global hotkey (WM_HOTKEY goes to the Qt event loop)."""
    if not IS_WINDOWS:
        return False
    return bool(_user32.RegisterHotKey(None, hotkey_id, modifiers, vk))


def unregister_hotkey(hotkey_id: int) -> None:
    if IS_WINDOWS:
        _user32.UnregisterHotKey(None, hotkey_id)


def play_sound_file(path) -> bool:
    """Play a WAV asynchronously (returns immediately). No-op off Windows."""
    if not IS_WINDOWS:
        return False
    import winsound

    try:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return True
    except RuntimeError:
        return False
