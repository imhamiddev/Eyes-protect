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
        self.meeting_action = QAction()
        self.quiet_end_action = QAction()
        self.quiet_menu = QMenu()
        self.quiet_actions: list[tuple[QAction, float | None, str]] = []
        for key, minutes in (("quiet.30", 30), ("quiet.60", 60), ("quiet.120", 120),
                             ("quiet.240", 240), ("quiet.forever", None)):
            act = QAction()
            act.triggered.connect(lambda _=False, m=minutes: engine.set_quiet(m))
            self.quiet_menu.addAction(act)
            self.quiet_actions.append((act, minutes, key))
        for a in (self.open_action, self.pause_action, self.break_action, self.night_action):
            self.menu.addAction(a)
        self.menu.addSeparator()
        self.menu.addAction(self.meeting_action)
        self.quiet_menu_action = self.menu.addMenu(self.quiet_menu)
        self.menu.addAction(self.quiet_end_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.icon.setContextMenu(self.menu)

        self.open_action.triggered.connect(self.open_requested)
        self.pause_action.triggered.connect(lambda: engine.set_paused(not engine.paused))
        self.break_action.triggered.connect(engine.start_break)
        self.night_action.triggered.connect(lambda: engine.toggle_night_light())
        self.meeting_action.triggered.connect(lambda: engine.set_quiet(60))
        self.quiet_end_action.triggered.connect(lambda: engine.set_quiet(0))
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
        self.meeting_action.setText(tr("tray.meeting"))
        self.quiet_menu.setTitle(tr("tray.quiet"))
        self.quiet_menu_action.setText(tr("tray.quiet"))
        for act, _minutes, key in self.quiet_actions:
            act.setText(tr(key))
        self.quiet_end_action.setText(tr("tray.quiet_end"))
        self.quiet_end_action.setVisible(self.engine.quiet_active)

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()
