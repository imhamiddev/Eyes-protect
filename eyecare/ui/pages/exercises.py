"""Exercises: guided, auto-advancing eye exercises."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from eyecare.core import i18n
from eyecare.core.exercises import EXERCISES, STRETCHES, Exercise
from eyecare.core.i18n import tr
from eyecare.core.timeutil import format_mmss

from .. import icons, motion
from ..theme import current
from ..widgets import Card, Ring, label, primary_button, secondary_button
from .base import Page


def _title(e: Exercise) -> str:
    return e.title_fa if i18n.language() == "fa" else e.title_en


def _step_text(step) -> str:
    return step.fa if i18n.language() == "fa" else step.en


class ExerciseRunner(QDialog):
    """Modal guided session; steps advance on their own."""

    completed = Signal()

    def __init__(self, exercise: Exercise, parent: QWidget | None = None, engine=None):
        super().__init__(parent)
        self.exercise = exercise
        self.engine = engine
        if parent is None:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setObjectName("Root")
        self.setModal(True)
        self.setWindowTitle(_title(exercise))
        self.setMinimumSize(460, 520)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.is_rtl()
                                else Qt.LayoutDirection.LeftToRight)
        self.step_index = 0
        self.step_left = exercise.steps[0].seconds
        self.total_left = exercise.total_seconds
        self.finished = False

        self.title = label(_title(exercise), "H2")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ring = Ring(220, 10)
        self.text = label("", "Title", wrap=True)
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter = label("", "Caption")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.close_btn = secondary_button(tr("ex.done"))
        self.close_btn.clicked.connect(self.accept)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(16)
        lay.addWidget(self.title)
        lay.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.text)
        lay.addWidget(self.counter)
        lay.addStretch(1)
        lay.addWidget(self.close_btn)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self._render()
        self.timer.start(1000)
        motion.fade_in(self.ring, 0, 360)
        motion.fade_in(self.title, 80, 360)
        motion.fade_in(self.text, 160, 360)

    def _render(self) -> None:
        step = self.exercise.steps[self.step_index]
        self.text.setText(_step_text(step))
        self.counter.setText(f"{self.step_index + 1} / {len(self.exercise.steps)}")
        self.ring.set_progress(1 - self.step_left / step.seconds)
        self.ring.set_text(format_mmss(self.step_left))

    def tick(self) -> None:
        if self.finished:
            return
        self.step_left -= 1
        self.total_left -= 1
        if self.step_left <= 0:
            if self.step_index + 1 >= len(self.exercise.steps):
                self.finished = True
                self.timer.stop()
                if self.engine is not None and self.exercise.kind == "body":
                    self.engine.record_stretch()
                self.completed.emit()
                self.text.setText(tr("ex.done"))
                self.ring.set_progress(1.0)
                self.ring.set_text("✓")
                motion.fade_in(self.text, 0, 380)
                return
            self.step_index += 1
            self.step_left = self.exercise.steps[self.step_index].seconds
            motion.fade_in(self.text, 0, 380)
        self._render()


class ExercisesPage(Page):
    def __init__(self, engine):
        super().__init__(engine, "ex.title", tr("ex.subtitle"))
        self.runner: ExerciseRunner | None = None
        self.section(tr("ex.eyes"))
        for exercise in EXERCISES:
            self._add_row(exercise)
        self.section(tr("ex.body"))
        for exercise in STRETCHES:
            self._add_row(exercise)
        self.finish()

    def _add_row(self, exercise: Exercise) -> None:
        card = Card()
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 16, 20, 16)
        row.setSpacing(16)
        icon = QLabel()
        icon.setFixedSize(46, 46)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(icons.pixmap(exercise.icon, current().accent, 24))
        icon.setStyleSheet(f"background:{current().accent_soft};border-radius:14px;")
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(_title(exercise), "Title"))
        text.addWidget(label(f"{exercise.total_seconds} {tr('ex.seconds')}", "Muted"))
        start = primary_button(tr("ex.start"), "play")
        start.clicked.connect(lambda _=False, e=exercise: self.run(e))
        row.addWidget(icon)
        row.addLayout(text, 1)
        row.addWidget(start)
        self.col.addWidget(card)

    def run(self, exercise: Exercise) -> ExerciseRunner:
        self.runner = ExerciseRunner(exercise, self.window(), self.engine)
        self.runner.show()
        return self.runner
