"""Global keyboard shortcuts via RegisterHotKey + a Qt native event filter (Windows)."""
from __future__ import annotations

import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

from eyecare.core import hotkeys as hk
from eyecare.core import winapi

WM_HOTKEY = 0x0312
_BASE_ID = 0x4543  # arbitrary, keeps our ids away from other components


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, manager: "HotkeyManager"):
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            import ctypes
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and self._manager.handle(int(msg.wParam)):
                return True, 0
        return False, 0


class HotkeyManager(QObject):
    triggered = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._ids: dict[int, str] = {}
        self._filter = _Filter(self)
        self._installed = False
        self.failed: set[str] = set()

    def register(self, enabled: bool, mapping: dict[str, str]) -> set[str]:
        """(Re)register shortcuts; returns the actions that could not be registered."""
        self.unregister_all()
        self.failed = set()
        if not enabled:
            return self.failed
        if not self._installed and QCoreApplication.instance() is not None:
            QCoreApplication.instance().installNativeEventFilter(self._filter)
            self._installed = True
        for index, action in enumerate(hk.ACTIONS):
            combo = mapping.get(action, "")
            try:
                mods, vk = hk.parse_combo(combo)
            except ValueError:
                self.failed.add(action)
                continue
            hotkey_id = _BASE_ID + index
            if winapi.register_hotkey(hotkey_id, mods | hk.MOD_NOREPEAT, vk):
                self._ids[hotkey_id] = action
            else:
                self.failed.add(action)
        return self.failed

    def unregister_all(self) -> None:
        for hotkey_id in list(self._ids):
            winapi.unregister_hotkey(hotkey_id)
        self._ids.clear()

    def handle(self, hotkey_id: int) -> bool:
        action = self._ids.get(hotkey_id)
        if action is None:
            return False
        self.triggered.emit(action)
        return True

    def shutdown(self) -> None:
        self.unregister_all()
        if self._installed and QCoreApplication.instance() is not None:
            QCoreApplication.instance().removeNativeEventFilter(self._filter)
            self._installed = False
