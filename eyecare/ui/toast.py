"""Floating, non-focus-stealing toast notifications (the desktop alerts)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import icons, tokens
from .theme import current
from . import motion
from .widgets import IconButton, label, primary_button, qcolor, secondary_button

Action = tuple[str, Callable[[], None], bool]  # (text, callback, is_primary)

MARGIN = 20
WIDTH = 380


class Toast(QWidget):
    def __init__(self, icon_name: str, title: str, body: str, actions: list[Action],
                 timeout_ms: int = 0, on_closed: Callable[["Toast"], None] | None = None):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(WIDTH)
        self._on_closed = on_closed
        self._closing = False
        self._timeout, self._elapsed = timeout_ms, 0
        pal = current()

        icon = QLabel()
        icon.setPixmap(icons.pixmap(icon_name, pal.accent, 22))
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background:{pal.accent_soft};border-radius:12px;")
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(label(title, "Title"))
        self.body_label = label(body, "Muted", wrap=True)
        head.addWidget(self.body_label)
        close = IconButton("x", size=14)
        close.setFixedSize(28, 28)
        close.clicked.connect(self.dismiss)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(head, 1)
        top.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 14, 16)
        root.setSpacing(14)
        root.addLayout(top)
        if actions:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addStretch(1)
            for text, callback, primary in actions:
                b = primary_button(text) if primary else secondary_button(text)
                b.setMinimumHeight(34)
                b.clicked.connect(lambda _=False, cb=callback: self._act(cb))
                row.addWidget(b)
            root.addLayout(row)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setEasingCurve(QEasingCurve.Type.OutBack)
        self._ticker = QTimer(self)
        self._ticker.setInterval(100)
        self._ticker.timeout.connect(self._advance)

    # -- behaviour --------------------------------------------------------
    def set_body(self, text: str) -> None:
        self.body_label.setText(text)

    def _act(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        finally:
            self.dismiss()

    def _advance(self) -> None:
        if self.underMouse():
            return  # don't vanish while being read
        self._elapsed += 100
        self.update()
        if self._timeout and self._elapsed >= self._timeout:
            self.dismiss()

    def present(self, target: QPoint) -> None:
        self.adjustSize()
        start = QPoint(target.x() + 40, target.y())
        self.move(start)
        self.setWindowOpacity(0.0)
        self.show()
        if motion.ms(1) == 0:
            self.move(target)
            self.setWindowOpacity(1.0)
        else:
            self._fade.setDuration(tokens.MOTION["base"])
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
            self._slide.setDuration(420)
            self._slide.setStartValue(start)
            self._slide.setEndValue(target)
            self._slide.start()
        if self._timeout:
            self._ticker.start()

    def move_to(self, target: QPoint) -> None:
        self._slide.stop()
        if motion.ms(1) == 0:
            self.move(target)
            return
        self._slide.setDuration(tokens.MOTION["slow"])
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(target)
        self._slide.start()

    def dismiss(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._ticker.stop()
        self._fade.stop()
        self._fade.finished.connect(self._finish)
        if motion.ms(1) == 0:
            self._finish()
            return
        self._slide.stop()
        self._slide.setDuration(tokens.MOTION["base"])
        self._slide.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(self.pos() + QPoint(40, 0))
        self._slide.start()
        self._fade.setDuration(tokens.MOTION["base"])
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _finish(self) -> None:
        self.close()
        if self._on_closed:
            self._on_closed(self)
        self.deleteLater()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(qcolor(pal.surface))
        p.setPen(qcolor(pal.border))
        p.drawRoundedRect(rect, tokens.RADIUS["lg"], tokens.RADIUS["lg"])
        if self._timeout:
            frac = max(0.0, 1 - self._elapsed / self._timeout)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(pal.accent_soft))
            bar = QRectF(rect.left() + 18, rect.bottom() - 3, (rect.width() - 36) * frac, 2)
            p.drawRoundedRect(bar, 1, 1)


class ToastManager:
    """Stacks toasts in the bottom-right corner of the primary screen."""

    def __init__(self) -> None:
        self._toasts: list[Toast] = []

    def show(self, icon_name: str, title: str, body: str, actions: list[Action] | None = None,
             timeout_ms: int = 0) -> Toast:
        toast = Toast(icon_name, title, body, actions or [], timeout_ms, self._closed)
        toast.adjustSize()
        self._toasts.append(toast)
        toast.present(self._slot(len(self._toasts) - 1, toast))
        return toast

    def _available(self):
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _slot(self, index: int, toast: Toast) -> QPoint:
        area = self._available()
        y = area.bottom() - MARGIN
        for other in self._toasts[:index]:
            y -= other.height() + 12
        return QPoint(area.right() - WIDTH - MARGIN, y - toast.height())

    def _closed(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        for i, t in enumerate(self._toasts):
            t.move_to(self._slot(i, t))

    def clear(self) -> None:
        for t in list(self._toasts):
            t.dismiss()

    def count(self) -> int:
        return len(self._toasts)
