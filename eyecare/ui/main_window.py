"""Main window: sidebar navigation + stacked pages."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget,
)

from eyecare import APP_NAME
from eyecare.core import i18n
from eyecare.core.i18n import tr
from eyecare.engine import Engine

from . import brand, icons, tokens
from .pages.care import CarePage
from .pages.display import DisplayPage
from .pages.exercises import ExercisesPage
from .pages.home import HomePage
from .pages.stats import StatsPage
from .pages.settings import SettingsPage
from . import motion
from .controls import AnimatedButton
from .theme import theme
from .widgets import Toggle, label

NAV = [
    ("nav.home", "dashboard", HomePage),
    ("nav.stats", "chart", StatsPage),
    ("nav.care", "eye", CarePage),
    ("nav.display", "moon", DisplayPage),
    ("nav.exercises", "activity", ExercisesPage),
    ("nav.settings", "sliders", SettingsPage),
]


class NavButton(AnimatedButton):
    def __init__(self, text: str, icon_name: str):
        super().__init__(text, icon_name, "nav", align="start")
        self.setMinimumHeight(40)
        self.setCheckable(True)

    def refresh_icon(self) -> None:
        self.update()


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(brand.app_icon())
        self.resize(tokens.SIZE["window_w"], tokens.SIZE["window_h"])
        self.setMinimumSize(820, 560)
        self.quitting = False
        self._shown_once = False
        self.pages: list[QWidget] = []
        self._build()
        engine.state_changed.connect(self._refresh)
        engine.settings_changed.connect(self._reload_pages)
        theme.changed.connect(self._restyle)

    # -- construction -------------------------------------------------------
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(tokens.SIZE["sidebar"])
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 22, 16, 18)
        sl.setSpacing(4)

        brand_row = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(brand.logo_pixmap(64).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation))
        brand_row.addWidget(mark)
        brand_row.addWidget(label(tr("app"), "Title"), 1)
        sl.addLayout(brand_row)
        sl.addSpacing(18)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.nav: list[NavButton] = []
        self.stack = QStackedWidget()
        for i, (key, icon_name, cls) in enumerate(NAV):
            btn = NavButton(tr(key), icon_name)
            btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().verticalPolicy())
            self.group.addButton(btn, i)
            self.nav.append(btn)
            sl.addWidget(btn)
            page = cls(self.engine)
            self.pages.append(page)
            self.stack.addWidget(page)
        self.group.idClicked.connect(self.go)
        self.nav[0].setChecked(True)
        sl.addStretch(1)

        quick = QFrame()
        quick.setObjectName("CardFlat")
        ql = QHBoxLayout(quick)
        ql.setContentsMargins(14, 10, 12, 10)
        ql.addWidget(label(tr("display.night"), "Muted"), 1)
        self.night_toggle = Toggle()
        self.night_toggle.setChecked(self.engine.settings.night_light.enabled)
        self.night_toggle.clicked.connect(lambda: self.engine.toggle_night_light())
        ql.addWidget(self.night_toggle)
        sl.addWidget(quick)

        row.addWidget(side)
        row.addWidget(self.stack, 1)

    # -- behaviour ----------------------------------------------------------
    def go(self, index: int) -> None:
        changed = self.stack.currentIndex() != index
        self.stack.setCurrentIndex(index)
        self.nav[index].setChecked(True)
        self.pages[index].load()
        self.pages[index].refresh()
        if changed and self.isVisible():
            self.pages[index].play_enter()

    def _refresh(self) -> None:
        if self.isVisible():
            page = self.pages[self.stack.currentIndex()]
            page.refresh()
        self.night_toggle.blockSignals(True)
        self.night_toggle.setChecked(self.engine.settings.night_light.enabled)
        self.night_toggle.blockSignals(False)

    def _reload_pages(self) -> None:
        for page in self.pages:
            page.load()

    def _restyle(self) -> None:
        for btn in self.nav:
            btn.refresh_icon()

    def rebuild(self) -> None:
        """Re-create all UI (used when the language changes)."""
        index = self.stack.currentIndex()
        old = self.centralWidget()
        self.pages = []
        self._build()
        self.go(index)
        self.nav[index].setChecked(True)
        old.deleteLater()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.is_rtl()
                                else Qt.LayoutDirection.LeftToRight)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._shown_once:
            self._shown_once = True
            self.pages[self.stack.currentIndex()].play_enter()
            if motion.ms(1):
                self.setWindowOpacity(0.0)
                self._open_anim = QPropertyAnimation(self, b"windowOpacity", self)
                self._open_anim.setDuration(280)
                self._open_anim.setStartValue(0.0)
                self._open_anim.setEndValue(1.0)
                self._open_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._open_anim.start()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.quitting:
            event.accept()
        else:
            event.ignore()
            self.hide()
