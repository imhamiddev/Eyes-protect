"""Reusable, token-driven components (no default OS look)."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QVariantAnimation, Signal,
    Property,
)
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton, QComboBox, QFrame, QHBoxLayout, QKeySequenceEdit, QLabel, QPushButton, QSlider,
    QToolButton, QVBoxLayout, QWidget,
)

from . import icons, tokens
from .controls import AnimatedButton, IconButton, SmoothSlider, ValueLabel  # noqa: F401
from .motion import Tween, lerp_color as _lerp_color, qcolor, ms, with_alpha  # noqa: F401
from .theme import current, theme


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
    def __init__(self, parent: QWidget | None = None, flat: bool = False, hoverable: bool = False):
        super().__init__(parent)
        self._hoverable = hoverable and not flat
        self.setObjectName("CardFlat" if flat else ("CardAnim" if self._hoverable else "Card"))
        if self._hoverable:
            self._hover = Tween(self, self.update, 0.0, 200)
            theme.changed.connect(self.update)

    def enterEvent(self, e) -> None:  # noqa: N802
        if self._hoverable:
            self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        if self._hoverable:
            self._hover.to(0.0)
        super().leaveEvent(e)

    def paintEvent(self, e) -> None:  # noqa: N802
        if not self._hoverable:
            return super().paintEvent(e)
        p, pal, h = QPainter(self), current(), self._hover.value
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = _lerp_color(qcolor(pal.surface), qcolor(pal.surface_hover), h * 0.6)
        border = _lerp_color(qcolor(pal.border), qcolor(pal.accent_soft), h)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        r = tokens.RADIUS["lg"]
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), r, r)


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFixedHeight(1)
    return line


def primary_button(text: str, icon_name: str | None = None) -> AnimatedButton:
    return AnimatedButton(text, icon_name, "primary")


def secondary_button(text: str, icon_name: str | None = None) -> AnimatedButton:
    return AnimatedButton(text, icon_name, "secondary")


def ghost_button(text: str) -> AnimatedButton:
    return AnimatedButton(text, None, "ghost")


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
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._hover = Tween(self, self.update, 0.0, 140)
        self._press = Tween(self, self.update, 0.0, 90)
        self.toggled.connect(self._animate)
        self._bind_theme()

    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, value: float) -> None:
        self._pos = value
        self.update()

    position = Property(float, _get_pos, _set_pos)

    def enterEvent(self, e) -> None:  # noqa: N802
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover.to(0.0)
        self._press.to(0.0)
        super().leaveEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        self._press.to(1.0)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._press.to(0.0, 200)
        super().mouseReleaseEvent(e)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setDuration(ms(tokens.MOTION["base"] + 60))
        if self._anim.duration() == 0:
            self._set_pos(1.0 if checked else 0.0)
            return
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
        d = rect.height() - 8 + 1.5 * self._hover.value
        knob_w = d + 5 * self._press.value
        t = 1 - self._pos if self.isRightToLeft() else self._pos
        x = rect.left() + 4 + (rect.width() - knob_w - 8) * t
        y = rect.top() + (rect.height() - d) / 2
        base_knob = qcolor("#FFFFFF" if pal.name == "light" else pal.text_muted)
        color = _lerp_color(base_knob, qcolor(pal.on_accent), self._pos) if enabled else base_knob
        if not enabled:
            color.setAlphaF(0.6)
        halo = max(self._hover.value * 0.5, self._press.value)
        if halo > 0.01 and enabled:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(with_alpha(qcolor(pal.accent), 0.18 * halo))
            p.drawEllipse(QRectF(x - 4, y - 4, knob_w + 8, d + 8))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x, y, knob_w, d), d / 2, d / 2)


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


# --------------------------------------------------------------------------- ring
class Ring(QWidget, _Themed):
    """Animated circular progress with a big centre number."""

    def __init__(self, diameter: int = 220, thickness: int = 10, parent: QWidget | None = None):
        super().__init__(parent)
        self._d, self._t = diameter, thickness
        self._progress, self._text, self._caption = 0.0, "", ""
        self.setFixedSize(diameter, diameter)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(tokens.MOTION["slow"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._bind_theme()

    @property
    def progress(self) -> float:
        return self._progress

    def set_progress(self, value: float, animate: bool = True) -> None:
        value = max(0.0, min(1.0, value))
        if animate and abs(value - self._progress) > 0.002:
            self._anim.stop()
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(value)
            self._anim.start()
        else:
            self._progress = value
            self.update()

    def _on_anim(self, v) -> None:
        self._progress = float(v)
        self.update()

    def set_text(self, text: str, caption: str = "") -> None:
        if (text, caption) != (self._text, self._caption):
            self._text, self._caption = text, caption
            self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = self._t / 2 + 2
        rect = QRectF(m, m, self._d - 2 * m, self._d - 2 * m)
        track = QPen(qcolor(pal.surface_raised if pal.name == "dark" else "#E4E0D6"), self._t)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)
        if self._progress > 0.003:
            arc = QPen(qcolor(pal.accent), self._t)
            arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc)
            p.drawArc(rect, 90 * 16, int(-self._progress * 360 * 16))
        p.setPen(qcolor(pal.text))
        font = QFont(self.font())
        font.setPixelSize(round(self._d * 0.24))
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        box = QRectF(0, self._d * 0.30, self._d, self._d * 0.30)
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, self._text)
        if self._caption:
            p.setPen(qcolor(pal.text_muted))
            font.setPixelSize(tokens.FONT_SIZE["label"])
            font.setWeight(QFont.Weight.Medium)
            p.setFont(font)
            p.drawText(QRectF(0, self._d * 0.60, self._d, 24), Qt.AlignmentFlag.AlignHCenter, self._caption)


# --------------------------------------------------------------------------- slider
class LabeledSlider(QWidget):
    """Slider with a live value label (always laid out left-to-right)."""

    valueChanged = Signal(int)

    def __init__(self, minimum: int = 0, maximum: int = 100, value: int = 0,
                 suffix: str = "%", parent: QWidget | None = None):
        super().__init__(parent)
        self.suffix = suffix
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.slider = SmoothSlider()
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider._shown = float(value)
        self.slider.setFixedHeight(tokens.SIZE["slider_h"] + 10)
        self.value_label = label(f"{value}{suffix}", "Muted")
        self.value_label.setMinimumWidth(52)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(tokens.SP["md"])
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._changed)

    def _changed(self, v: int) -> None:
        self.value_label.setText(f"{v}{self.suffix}")
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self.slider.value()

    def set_value(self, v: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.slider.blockSignals(False)
        self.value_label.setText(f"{v}{self.suffix}")


# --------------------------------------------------------------------------- stepper
class Stepper(QWidget):
    """Compact [-] value [+] control for small integers."""

    valueChanged = Signal(int)

    def __init__(self, minimum: int, maximum: int, value: int, step: int = 1,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._min, self._max, self._step, self._value = minimum, maximum, step, value
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.minus = IconButton("minus", size=16)
        self.plus = IconButton("plus", size=16)
        self.text = ValueLabel(str(value), 40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)
        for w in (self.minus, self.text, self.plus):
            lay.addWidget(w)
        self.setObjectName("CardFlat")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.minus.clicked.connect(lambda: self.set_value(self._value - self._step))
        self.plus.clicked.connect(lambda: self.set_value(self._value + self._step))
        self._refresh()

    def value(self) -> int:
        return self._value

    def set_value(self, v: int, emit: bool = True) -> None:
        v = max(self._min, min(self._max, v))
        if v == self._value:
            return
        self._value = v
        self._refresh()
        if emit:
            self.valueChanged.emit(v)

    def _refresh(self) -> None:
        self.text.setText(str(self._value))
        self.minus.setEnabled(self._value > self._min)
        self.plus.setEnabled(self._value < self._max)

    def wheelEvent(self, e) -> None:  # noqa: N802
        self.set_value(self._value + (self._step if e.angleDelta().y() > 0 else -self._step))


# --------------------------------------------------------------------------- time picker
class TimeField(QWidget):
    """HH:MM picker with up/down chevrons and wheel support."""

    changed = Signal(str)

    def __init__(self, value: str = "00:00", parent: QWidget | None = None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setObjectName("CardFlat")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._h, self._m = 0, 0
        self.set_value(value, emit=False)
        self._hour = self._column(24, 1, lambda: self._h, self._set_h)
        self._min_col = self._column(60, 5, lambda: self._m, self._set_m)
        sep = label(":")
        sep.setObjectName("Title")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(4)
        lay.addWidget(self._hour[0])
        lay.addWidget(sep)
        lay.addWidget(self._min_col[0])
        self._refresh()

    def _column(self, mod: int, step: int, getter, setter):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        up, down = IconButton("plus", size=12), IconButton("minus", size=12)
        for b in (up, down):
            b.setFixedSize(34, 16)
        text = ValueLabel("00", 34)
        up.clicked.connect(lambda: setter((getter() + step) % mod))
        down.clicked.connect(lambda: setter((getter() - step) % mod))
        v.addWidget(up)
        v.addWidget(text)
        v.addWidget(down)
        return box, text

    def _set_h(self, v: int) -> None:
        self._h = v
        self._after()

    def _set_m(self, v: int) -> None:
        self._m = v
        self._after()

    def _after(self) -> None:
        self._refresh()
        self.changed.emit(self.value())

    def _refresh(self) -> None:
        self._hour[1].setText(f"{self._h:02d}")
        self._min_col[1].setText(f"{self._m:02d}")

    def value(self) -> str:
        return f"{self._h:02d}:{self._m:02d}"

    def set_value(self, value: str, emit: bool = False) -> None:
        try:
            h, m = (int(x) for x in value.split(":"))
            self._h, self._m = h % 24, m % 60
        except ValueError:
            self._h = self._m = 0
        if hasattr(self, "_hour"):
            self._refresh()
        if emit:
            self.changed.emit(self.value())


# --------------------------------------------------------------------------- dropdown
class Dropdown(QComboBox, _Themed):
    def __init__(self, items: list[str], index: int = 0, parent: QWidget | None = None):
        super().__init__(parent)
        self.addItems(items)
        self.setCurrentIndex(index)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open = Tween(self, self.update, 0.0, 200)
        self._hover = Tween(self, self.update, 0.0, 140)
        self._bind_theme()

    def showPopup(self) -> None:  # noqa: N802
        self._open.to(1.0)
        super().showPopup()

    def hidePopup(self) -> None:  # noqa: N802
        self._open.to(0.0)
        super().hidePopup()

    def enterEvent(self, e) -> None:  # noqa: N802
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover.to(0.0)
        super().leaveEvent(e)

    def paintEvent(self, e) -> None:  # noqa: N802
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        color = _lerp_color(qcolor(current().text_muted), qcolor(current().accent), self._open.value)
        pm = icons.tinted("chevron-down", color, 16)
        x = 10 if self.isRightToLeft() else self.width() - 26
        cx, cy = x + 8, self.height() / 2
        p.translate(cx, cy)
        p.rotate(180 * self._open.value)
        p.drawPixmap(QPointF(-8, -8), pm)


# --------------------------------------------------------------------------- stats
class AnimatedNumber(QLabel):
    """Number label that counts to its new value."""

    def __init__(self, value: int = 0, parent: QWidget | None = None):
        super().__init__(str(value), parent)
        self._value = value
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(tokens.MOTION["slow"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(lambda v: self.setText(str(int(round(v)))))

    def set_value(self, value: int) -> None:
        if value == self._value:
            return
        self._anim.stop()
        self._anim.setStartValue(float(self._value))
        self._anim.setEndValue(float(value))
        self._value = value
        self._anim.start()


class StatCard(Card, _Themed):
    def __init__(self, icon_name: str, title: str, value: int = 0, parent: QWidget | None = None):
        super().__init__(parent, hoverable=True)
        self._icon_name = icon_name
        self.icon = QLabel()
        self.number = AnimatedNumber(value)
        self.number.setObjectName("H1")
        self.title = label(title, "Muted")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(6)
        lay.addWidget(self.icon)
        lay.addSpacing(6)
        lay.addWidget(self.number)
        lay.addWidget(self.title)
        self._bind_theme()
        self._refresh_icon()

    def set_title(self, text: str) -> None:
        self.title.setText(text)

    def _refresh_icon(self) -> None:
        self.icon.setPixmap(icons.pixmap(self._icon_name, current().accent, 20))

    def on_theme_changed(self) -> None:
        self._refresh_icon()


class BarChart(QWidget, _Themed):
    """Minimal 7-bar chart; bars grow in with a stagger, today uses the accent colour."""

    def __init__(self, labels: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.values: list[int] = []
        self._from: list[float] = []
        self._shown: list[float] = []
        self.labels = labels or []
        self.setMinimumHeight(150)
        self._t = Tween(self, self._advance, 1.0, 700, QEasingCurve.Type.Linear)
        self._bind_theme()

    def set_data(self, values: list[int], labels: list[str] | None = None) -> None:
        if labels is not None:
            self.labels = labels
        if list(values) != self.values:
            self._from = list(self._shown) if len(self._shown) == len(values) else [0.0] * len(values)
            self.values = list(values)
            self._t.jump(0.0)
            self._t.to(1.0)
        self.update()

    def _advance(self) -> None:
        n = len(self.values)
        out = []
        for i, v in enumerate(self.values):
            start = (i / max(1, n)) * 0.45
            local = max(0.0, min(1.0, (self._t.value - start) / 0.55))
            eased = 1 - (1 - local) ** 3
            base = self._from[i] if i < len(self._from) else 0.0
            out.append(base + (v - base) * eased)
        self._shown = out
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        if not self.values:
            return
        shown = self._shown if len(self._shown) == len(self.values) else [float(v) for v in self.values]
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n, top = len(self.values), max(1.0, max(max(shown), float(max(self.values))))
        label_h, w, h = 22, self.width(), self.height()
        slot = w / n
        bar_w = min(30.0, slot * 0.46)
        for i, v in enumerate(shown):
            bh = 6.0 + (h - label_h - 14) * v / top
            x = i * slot + (slot - bar_w) / 2
            rect = QRectF(x, h - label_h - bh, bar_w, bh)
            is_today = i == n - 1
            has = self.values[i] > 0
            if is_today and has:
                color = qcolor(pal.accent)
            elif has:
                color = qcolor(pal.accent_soft)
                color.setAlpha(120 if pal.name == "dark" else 160)
            else:
                color = qcolor(pal.surface_hover if pal.name == "dark" else "#E4E0D6")
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(rect, 6, 6)
            if self.labels and i < len(self.labels):
                p.setPen(qcolor(pal.text_faint))
                f = QFont(self.font())
                f.setPixelSize(tokens.FONT_SIZE["caption"])
                p.setFont(f)
                p.drawText(QRectF(i * slot, h - label_h + 4, slot, label_h),
                           Qt.AlignmentFlag.AlignHCenter, self.labels[i])


class ShortcutEdit(QKeySequenceEdit):
    """Click, then press a key combination. Emits ``committed`` with the portable text."""

    committed = Signal(str)

    def __init__(self, combo: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setMaximumSequenceLength(1)
        self.set_combo(combo)
        self.editingFinished.connect(lambda: self.committed.emit(self.combo()))

    def combo(self) -> str:
        return self.keySequence().toString(QKeySequence.SequenceFormat.PortableText)

    def set_combo(self, combo: str) -> None:
        self.blockSignals(True)
        self.setKeySequence(QKeySequence(combo))
        self.blockSignals(False)


class ProgressBar(QWidget, _Themed):
    """Thin pill progress bar whose fill eases to each new value."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._t = Tween(self, self.update, 0.0, 300)
        self._bind_theme()

    @property
    def value(self) -> float:
        return self._t.value

    def set_value(self, value: float, animate: bool = True) -> None:
        value = max(0.0, min(1.0, value))
        if animate:
            self._t.to(value, 260)
        else:
            self._t.jump(value)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor(pal.surface_raised if pal.name == "dark" else "#E4E0D6"))
        p.drawRoundedRect(QRectF(self.rect()), h / 2, h / 2)
        if self._t.value > 0.001:
            w = max(float(h), self.width() * self._t.value)
            x = self.width() - w if self.isRightToLeft() else 0.0
            p.setBrush(qcolor(pal.accent))
            p.drawRoundedRect(QRectF(x, 0, w, h), h / 2, h / 2)


# --------------------------------------------------------------------------- rows
class SettingRow(QWidget):
    """Title + description on one side, a control on the other."""

    def __init__(self, title: str, description: str = "", control: QWidget | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = label(title, "Title")
        text.addWidget(self.title)
        self.desc = label(description, "Muted", wrap=True)
        self.desc.setVisible(bool(description))
        text.addWidget(self.desc)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(tokens.SP["xl"])
        lay.addLayout(text, 1)
        self.control = control
        if control is not None:
            lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_texts(self, title: str, description: str = "") -> None:
        self.title.setText(title)
        self.desc.setText(description)
        self.desc.setVisible(bool(description))
