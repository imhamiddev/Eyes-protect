"""Full-screen break screen (Break Lock) shown on every monitor."""
from __future__ import annotations

import math
import random

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRect, QTimer, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QPainter, QRadialGradient
from PySide6.QtWidgets import QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.core.exercises import EXERCISES, Exercise
from eyecare.core.timeutil import format_mmss

from . import motion
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
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._after_fade)
        self._breath = QVariantAnimation(self)
        self._breath.setStartValue(0.0)
        self._breath.setEndValue(1.0)
        self._breath.setDuration(4200)
        self._breath.setLoopCount(-1)
        self._breath.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._breath_v = 0.0
        self._breath.valueChanged.connect(self._on_breath)
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
        self._fade.stop()
        if motion.ms(1):
            self.setWindowOpacity(0.0)
        else:
            self.setWindowOpacity(1.0)
        self.showFullScreen()
        self.activateWindow()
        self.setFocus()
        if motion.ms(1):
            self._fade.setDuration(450)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
            self._breath.start()

    def update_left(self, seconds: int) -> None:
        self._left = max(0, seconds)
        self._refresh()

    def end(self) -> None:
        was_active = self._active
        self._active = False
        self._skip_timer.stop()
        self._breath.stop()
        if was_active and motion.ms(1) and self.isVisible():
            self._fade.stop()
            self._fade.setDuration(300)
            self._fade.setStartValue(self.windowOpacity())
            self._fade.setEndValue(0.0)
            self._fade.start()
        else:
            self._fade.stop()
            self._hide_now()

    def _after_fade(self) -> None:
        if not self._active:
            self._hide_now()

    def _hide_now(self) -> None:
        self.hide()
        self.setWindowOpacity(1.0)
        for c in self._covers:
            c.close()
        self._covers.clear()

    def _on_breath(self, v) -> None:
        self._breath_v = float(v)
        self.update(self._halo_rect())

    def _halo_rect(self) -> QRect:
        c = self.ring.mapTo(self, self.ring.rect().center())
        r = 260
        return QRect(c.x() - r, c.y() - r, 2 * r, 2 * r)

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
        p = QPainter(self)
        p.fillRect(self.rect(), qcolor(current().overlay if self.isFullScreen() else current().bg))
        if self._active and motion.ms(1):
            # slow "breathing" halo behind the ring: inhale/exhale pacing for relaxed eyes
            c = self.ring.mapTo(self, self.ring.rect().center())
            wave = 0.5 - 0.5 * math.cos(self._breath_v * 2 * 3.14159265)
            radius = 150 + 70 * wave
            grad = QRadialGradient(QPointF(c), radius)
            accent = QColor(qcolor(current().accent))
            accent.setAlpha(int(34 + 30 * wave))
            grad.setColorAt(0.55, accent)
            accent.setAlpha(0)
            grad.setColorAt(1.0, accent)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawEllipse(QPointF(c), radius, radius)
