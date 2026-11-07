"""Thin, safe wrappers around the Win32 calls Eye Care needs.

Every function degrades to a harmless no-op on non-Windows platforms, so the
rest of the code (and the test-suite) can import this module anywhere.
"""
from __future__ import annotations

import sys

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

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

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


def reset_gamma() -> bool:
    identity = [[min(65535, i * 257) for i in range(256)] for _ in range(3)]
    return set_gamma_ramp(identity)


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
