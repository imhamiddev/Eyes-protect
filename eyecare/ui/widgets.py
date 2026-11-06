"""Reusable, token-driven components (no default OS look)."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QVariantAnimation, Signal,
    Property,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QToolButton,
    QVBoxLayout, QWidget,
)

from . import icons, tokens
from .theme import current, theme


def qcolor(value: str) -> QColor:
    """Parse '#rrggbb' or 'rgba(r,g,b,a)' (a in 0..1) into a QColor."""
    value = value.strip()
    if value.startswith("rgba"):
        r, g, b, a = [x.strip() for x in value[value.index("(") + 1:value.rindex(")")].split(",")]
        return QColor(int(r), int(g), int(b), round(float(a) * 255))
    return QColor(value)


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t), round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


class _Themed:
    """Mixin: repaint/restyle when the theme changes."""

    def _bind_theme(self) -> None:
        theme.changed.connect(self.on_theme_changed)  # type: ignore[attr-defined]

    def on_theme_changed(self) -> None:
        self.update()  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- basics
def label(text: str = "", kind: str | None = None, wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if kind:
        lab.setObjectName(kind)
    lab.setWordWrap(wrap)
    return lab


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, flat: bool = False):
        super().__init__(parent)
        self.setObjectName("CardFlat" if flat else "Card")


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFixedHeight(1)
    return line


class IconButton(QToolButton, _Themed):
    def __init__(self, name: str, tooltip: str = "", checkable: bool = False,
                 size: int = 18, parent: QWidget | None = None):
        super().__init__(parent)
        self._name, self._size, self._color_key = name, size, "text_muted"
        self.setCheckable(checkable)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        self._bind_theme()
        self._refresh()

    def set_icon_name(self, name: str) -> None:
        self._name = name
        self._refresh()

    def _refresh(self) -> None:
        p = current()
        color = p.accent if self.isChecked() else getattr(p, self._color_key)
        self.setIcon(icons.icon(self._name, color, self._size))

    def on_theme_changed(self) -> None:
        self._refresh()

    def nextCheckState(self) -> None:  # noqa: N802
        super().nextCheckState()
        self._refresh()


def primary_button(text: str, icon_name: str | None = None) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        btn.setIcon(icons.icon(icon_name, current().on_accent, 18))
        btn.setIconSize(QSize(18, 18))
    return btn


def secondary_button(text: str, icon_name: str | None = None) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        btn.setIcon(icons.icon(icon_name, current().text, 18))
        btn.setIconSize(QSize(18, 18))
    return btn


def ghost_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("Ghost")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


# --------------------------------------------------------------------------- toggle
class Toggle(QAbstractButton, _Themed):
    """Animated switch."""

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(tokens.SIZE["toggle_w"], tokens.SIZE["toggle_h"])
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(tokens.MOTION["base"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)
        self._bind_theme()

    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, value: float) -> None:
        self._pos = value
        self.update()

    position = Property(float, _get_pos, _set_pos)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(tokens.SIZE["toggle_w"], tokens.SIZE["toggle_h"])

    def paintEvent(self, _event) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()
        off = qcolor(pal.surface_raised if pal.name == "dark" else "#D9D5CB")
        track = _lerp_color(off, qcolor(pal.accent), self._pos)
        if not enabled:
            track.setAlphaF(0.4)
        rect = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(qcolor(pal.accent), 1.5))
            p.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), rect.height() / 2 + 1, rect.height() / 2 + 1)
        d = rect.height() - 8
        t = 1 - self._pos if self.isRightToLeft() else self._pos
        x = rect.left() + 4 + (rect.width() - d - 8) * t
        knob = qcolor(pal.on_accent) if self._pos > 0.5 else qcolor("#FFFFFF" if pal.name == "light" else pal.text_muted)
        if not enabled:
            knob.setAlphaF(0.6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_lerp_color(qcolor("#FFFFFF" if pal.name == "light" else pal.text_muted),
                               qcolor(pal.on_accent), self._pos) if enabled else knob)
        p.drawEllipse(QRectF(x, rect.top() + 4, d, d))


# --------------------------------------------------------------------------- segmented
class Segmented(QWidget, _Themed):
    changed = Signal(int)

    def __init__(self, options: list[str], index: int = 0, parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._index = index
        self._hl = QRectF()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        for i, text in enumerate(options):
            b = QPushButton(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFlat(True)
            b.setStyleSheet("QPushButton{background:transparent;border:none;padding:0 14px;"
                            "min-height:30px;font-weight:500;}")
            b.clicked.connect(lambda _=False, i=i: self.set_index(i))
            lay.addWidget(b)
            self._buttons.append(b)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(tokens.MOTION["base"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._bind_theme()
        self._style_labels()

    def index(self) -> int:
        return self._index

    def set_index(self, i: int, emit: bool = True) -> None:
        if i == self._index and not self._hl.isNull():
            return
        self._index = i
        self._style_labels()
        target = self._target()
        if self._hl.isNull():
            self._hl = target
        else:
            self._anim.stop()
            self._anim.setStartValue(self._hl)
            self._anim.setEndValue(target)
            self._anim.start()
        self.update()
        if emit:
            self.changed.emit(i)

    def _target(self) -> QRectF:
        return QRectF(self._buttons[self._index].geometry())

    def _on_anim(self, value) -> None:
        self._hl = value
        self.update()

    def _style_labels(self) -> None:
        pal = current()
        for i, b in enumerate(self._buttons):
            color = pal.text if i == self._index else pal.text_muted
            b.setStyleSheet(f"QPushButton{{background:transparent;border:none;padding:0 14px;"
                            f"min-height:30px;font-weight:500;color:{color};}}")

    def on_theme_changed(self) -> None:
        self._style_labels()
        self.update()

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        self._hl = self._target()

    def showEvent(self, e) -> None:  # noqa: N802
        super().showEvent(e)
        self._hl = self._target()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor(pal.surface_raised))
        r = tokens.RADIUS["md"]
        p.drawRoundedRect(QRectF(self.rect()), r, r)
        if not self._hl.isNull():
            p.setBrush(qcolor(pal.surface_hover if pal.name == "dark" else "#FFFFFF"))
            p.drawRoundedRect(self._hl, r - 3, r - 3)
