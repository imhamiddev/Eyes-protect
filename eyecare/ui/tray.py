"""System-tray icon and menu."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from eyecare import APP_NAME
from eyecare.core.i18n import tr
from eyecare.engine import Engine

from . import brand


class Tray(QObject):
    open_requested = Signal()
    quit_requested = Signal()

    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.icon = QSystemTrayIcon(brand.app_icon())
        self.icon.setToolTip(APP_NAME)
        self.menu = QMenu()
        self.open_action = QAction()
        self.pause_action = QAction()
        self.break_action = QAction()
        self.night_action = QAction()
        self.night_action.setCheckable(True)
        self.quit_action = QAction()
        for a in (self.open_action, self.pause_action, self.break_action, self.night_action):
            self.menu.addAction(a)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.icon.setContextMenu(self.menu)

        self.open_action.triggered.connect(self.open_requested)
        self.pause_action.triggered.connect(lambda: engine.set_paused(not engine.paused))
        self.break_action.triggered.connect(engine.start_break)
        self.night_action.triggered.connect(lambda: engine.toggle_night_light())
        self.quit_action.triggered.connect(self.quit_requested)
        self.icon.activated.connect(self._activated)
        engine.state_changed.connect(self.retranslate)
        self.retranslate()

    def _activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_requested.emit()

    def retranslate(self) -> None:
        self.open_action.setText(tr("tray.open"))
        self.pause_action.setText(tr("tray.resume" if self.engine.paused else "tray.pause"))
        self.break_action.setText(tr("tray.break"))
        self.night_action.setText(tr("tray.night"))
        self.night_action.setChecked(self.engine.settings.night_light.enabled)
        self.quit_action.setText(tr("tray.quit"))

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()
