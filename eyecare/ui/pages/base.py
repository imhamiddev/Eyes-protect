"""Shared page scaffolding: scrollable column with a title header."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtWidgets import QFrame, QLayout, QScrollArea, QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.engine import Engine

from .. import motion
from ..widgets import Card, divider, label


class SmoothScrollArea(QScrollArea):
    """Mouse-wheel scrolling that eases to its target instead of jumping."""

    def __init__(self) -> None:
        super().__init__()
        self._target = 0
        self._anim = QVariantAnimation(self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(lambda v: self.verticalScrollBar().setValue(int(v)))

    def wheelEvent(self, e) -> None:  # noqa: N802
        bar = self.verticalScrollBar()
        if motion.ms(1) == 0 or e.angleDelta().y() == 0:
            return super().wheelEvent(e)
        base = self._target if self._anim.state() == QVariantAnimation.State.Running else bar.value()
        self._target = max(bar.minimum(), min(bar.maximum(), int(base - e.angleDelta().y() * 0.9)))
        self._anim.stop()
        self._anim.setDuration(260)
        self._anim.setStartValue(float(bar.value()))
        self._anim.setEndValue(float(self._target))
        self._anim.start()
        e.accept()


def _collect_widgets(layout: QLayout, out: list[QWidget]) -> None:
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is not None:
            out.append(item.widget())
        elif item.layout() is not None:
            _collect_widgets(item.layout(), out)


class Page(QWidget):
    def __init__(self, engine: Engine, title_key: str, subtitle: str = ""):
        super().__init__()
        self.engine = engine
        self._loading = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = SmoothScrollArea()
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

    def play_enter(self) -> None:
        """Staggered fade-in of the page's blocks."""
        blocks: list[QWidget] = []
        _collect_widgets(self.col, blocks)
        for i, w in enumerate(blocks):
            motion.fade_in(w, delay=min(i, 8) * 45, duration=320)
