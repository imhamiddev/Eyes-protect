"""Shared page scaffolding: scrollable column with a title header."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.engine import Engine

from ..widgets import Card, divider, label


class Page(QWidget):
    def __init__(self, engine: Engine, title_key: str, subtitle: str = ""):
        super().__init__()
        self.engine = engine
        self._loading = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.col = QVBoxLayout(body)
        self.col.setContentsMargins(36, 32, 36, 32)
        self.col.setSpacing(16)
        self.col.addWidget(label(i18n.tr(title_key), "H1"))
        if subtitle:
            self.col.addWidget(label(subtitle, "Muted", wrap=True))
        self.col.addSpacing(8)

    def card(self, *widgets: QWidget, separators: bool = True) -> Card:
        card = Card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 10, 22, 10)
        lay.setSpacing(0)
        for i, w in enumerate(widgets):
            if i and separators:
                lay.addWidget(divider())
            lay.addWidget(w)
        self.col.addWidget(card)
        return card

    def section(self, text: str) -> None:
        self.col.addSpacing(6)
        self.col.addWidget(label(text, "Caption"))

    def finish(self) -> None:
        self.col.addStretch(1)

    def load(self) -> None:
        """Re-read settings into the controls (override)."""

    def refresh(self) -> None:
        """Per-second UI refresh (override if needed)."""
