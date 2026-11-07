"""Motion helpers: global on/off switch, tweens, colour maths and fade-ins."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

_enabled = True


def set_enabled(value: bool) -> None:
    global _enabled
    _enabled = bool(value)


def enabled() -> bool:
    return _enabled


def ms(base: int) -> int:
    """Scale a duration: 0 when animations are switched off."""
    return int(base) if _enabled else 0


def qcolor(value: str) -> QColor:
    """Parse '#rrggbb' or 'rgba(r,g,b,a)' (a in 0..1) into a QColor."""
    value = value.strip()
    if value.startswith("rgba"):
        r, g, b, a = [x.strip() for x in value[value.index("(") + 1:value.rindex(")")].split(",")]
        return QColor(int(r), int(g), int(b), round(float(a) * 255))
    return QColor(value)


def lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t), round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def with_alpha(color: QColor, alpha: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)) * color.alphaF())
    return c


class Tween(QObject):
    """An animated float that calls ``on_change`` on every frame."""

    def __init__(self, parent: QObject, on_change: Callable[[], None], initial: float = 0.0,
                 duration: int = 160, easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic):
        super().__init__(parent)
        self.value = float(initial)
        self._on_change = on_change
        self._duration = duration
        self._anim = QVariantAnimation(self)
        self._anim.setEasingCurve(easing)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, v) -> None:
        self.value = float(v)
        self._on_change()

    def to(self, target: float, duration: int | None = None,
           easing: QEasingCurve.Type | None = None) -> None:
        self._anim.stop()
        d = ms(self._duration if duration is None else duration)
        if d <= 0 or abs(target - self.value) < 1e-4:
            self.value = float(target)
            self._on_change()
            return
        if easing is not None:
            self._anim.setEasingCurve(easing)
        self._anim.setDuration(d)
        self._anim.setStartValue(self.value)
        self._anim.setEndValue(float(target))
        self._anim.start()

    def jump(self, value: float) -> None:
        self._anim.stop()
        self.value = float(value)
        self._on_change()

    @property
    def running(self) -> bool:
        return self._anim.state() == QVariantAnimation.State.Running


def fade_in(widget: QWidget, delay: int = 0, duration: int = 280) -> None:
    """Fade a widget from transparent to opaque (the effect removes itself)."""
    duration = ms(duration)
    if duration <= 0 or widget is None:
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def done() -> None:
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)

    anim.finished.connect(done)
    timer = QTimer(widget)
    timer.setSingleShot(True)
    timer.timeout.connect(anim.start)
    timer.start(max(0, delay))
