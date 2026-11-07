"""Full-screen break screen (Break Lock) shown on every monitor."""
from __future__ import annotations

import random

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.core.exercises import EXERCISES, Exercise
from eyecare.core.timeutil import format_mmss

from .theme import current
from .widgets import Ring, label, qcolor, secondary_button


class _ScreenCover(QWidget):
    """Dim cover for secondary monitors."""

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)

    def paintEvent(self, _e) -> None:  # noqa: N802
        QPainter(self).fillRect(self.rect(), qcolor(current().overlay))


class BreakOverlay(QWidget):
    skipped = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._covers: list[_ScreenCover] = []
        self._total = 20
        self._left = 20
        self._skippable = True
        self._skip_after = 3
        self._exercise: Exercise | None = None
        self._active = False

        self.title = label("", "H1")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint = label("", "Muted", wrap=True)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ring = Ring(260, 12)
        self.step = label("", "Title", wrap=True)
        self.step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step.setMaximumWidth(560)
        self.skip_btn = secondary_button("", "skip")
        self.skip_btn.clicked.connect(self._skip)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(18)
        for w in (self.title, self.hint):
            lay.addWidget(w, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(8)
        lay.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(8)
        lay.addWidget(self.step, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(16)
        lay.addWidget(self.skip_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        self._skip_timer = QTimer(self)
        self._skip_timer.setSingleShot(True)
        self._skip_timer.timeout.connect(lambda: self.skip_btn.setEnabled(True))

    # -- API ----------------------------------------------------------------
    @property
    def active(self) -> bool:
        return self._active

    def begin(self, seconds: int, skippable: bool, skip_after: int, show_exercise: bool) -> None:
        self._total = self._left = max(1, seconds)
        self._skippable, self._skip_after = skippable, skip_after
        self._exercise = random.choice(EXERCISES) if show_exercise else None
        self.title.setText(i18n.tr("break.title"))
        self.hint.setText(i18n.tr("break.hint"))
        self.skip_btn.setText(i18n.tr("break.skip"))
        self.skip_btn.setVisible(skippable)
        self.skip_btn.setEnabled(skip_after <= 0)
        if skippable and skip_after > 0:
            self._skip_timer.start(skip_after * 1000)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.is_rtl()
                                else Qt.LayoutDirection.LeftToRight)
        self._refresh()
        self._cover_screens()
        self._active = True
        self.showFullScreen()
        self.activateWindow()
        self.setFocus()

    def update_left(self, seconds: int) -> None:
        self._left = max(0, seconds)
        self._refresh()

    def end(self) -> None:
        self._active = False
        self._skip_timer.stop()
        self.hide()
        for c in self._covers:
            c.close()
        self._covers.clear()

    # -- internals ------------------------------------------------------------
    def _refresh(self) -> None:
        self.ring.set_progress(1 - self._left / self._total)
        self.ring.set_text(format_mmss(self._left))
        self.step.setVisible(self._exercise is not None)
        if self._exercise:
            elapsed, acc = self._total - self._left, 0
            text = ""
            for s in self._exercise.steps:
                text = s.fa if i18n.language() == "fa" else s.en
                acc += s.seconds
                if elapsed < acc:
                    break
            title = self._exercise.title_fa if i18n.language() == "fa" else self._exercise.title_en
            self.step.setText(f"{title}\n{text}")

    def _cover_screens(self) -> None:
        primary = QGuiApplication.primaryScreen()
        self.setScreen(primary)
        self.setGeometry(primary.geometry())
        for screen in QGuiApplication.screens():
            if screen is primary:
                continue
            cover = _ScreenCover()
            cover.setGeometry(screen.geometry())
            cover.show()
            self._covers.append(cover)

    def _skip(self) -> None:
        if self._skippable and self.skip_btn.isEnabled():
            self.skipped.emit()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self._skip()
        else:
            super().keyPressEvent(e)

    def paintEvent(self, _e) -> None:  # noqa: N802
        QPainter(self).fillRect(self.rect(), qcolor(current().overlay if self.isFullScreen() else current().bg))
