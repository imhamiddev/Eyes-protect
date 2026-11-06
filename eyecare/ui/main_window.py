"""Main window: sidebar navigation + stacked pages."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
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
from .pages.settings import SettingsPage
from .theme import current, theme
from .widgets import Toggle, label

NAV = [
    ("nav.home", "dashboard", HomePage),
    ("nav.care", "eye", CarePage),
    ("nav.display", "moon", DisplayPage),
    ("nav.exercises", "activity", ExercisesPage),
    ("nav.settings", "sliders", SettingsPage),
]


class NavButton(QPushButton):
    def __init__(self, text: str, icon_name: str):
        super().__init__(f"  {text}")
        self.setObjectName("NavItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_name = icon_name
        self.setIconSize(QSize(18, 18))
        self.toggled.connect(lambda _: self.refresh_icon())
        self.refresh_icon()

    def refresh_icon(self) -> None:
        p = current()
        self.setIcon(icons.icon(self._icon_name, p.accent if self.isChecked() else p.text_muted, 18))


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(brand.app_icon())
        self.resize(tokens.SIZE["window_w"], tokens.SIZE["window_h"])
        self.setMinimumSize(820, 560)
        self.quitting = False
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
        self.stack.setCurrentIndex(index)
        self.pages[index].load()
        self.pages[index].refresh()

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

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.quitting:
            event.accept()
        else:
            event.ignore()
            self.hide()
