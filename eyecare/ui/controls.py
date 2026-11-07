"""Interactive controls with hover, press, focus and ripple micro-interactions."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QPushButton, QSlider, QStyle, QWidget

from . import icons, tokens
from .motion import Tween, lerp_color, ms, qcolor, with_alpha
from .theme import current, theme

PRIMARY_HOVER = "#E4F99A"
PRIMARY_PRESS = "#BFDD52"


class AnimatedButton(QPushButton):
    """Button kinds: primary, secondary, ghost, nav. Everything is painted here."""

    def __init__(self, text: str = "", icon_name: str | None = None, kind: str = "secondary",
                 align: str = "center", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.kind, self.icon_name, self.align = kind, icon_name, align
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._hover = Tween(self, self.update, 0.0, 150)
        self._press = Tween(self, self.update, 0.0, 90)
        self._focus = Tween(self, self.update, 0.0, 150)
        self._check = Tween(self, self.update, 0.0, 220)
        self._ripple = Tween(self, self.update, 1.0, 520, QEasingCurve.Type.OutCubic)
        self._ripple_pos = QPointF()
        self.toggled.connect(lambda c: self._check.to(1.0 if c else 0.0))
        theme.changed.connect(self.update)
        self.setMinimumHeight(tokens.SIZE["button_h"])

    # -- events -------------------------------------------------------------
    def enterEvent(self, e) -> None:  # noqa: N802
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover.to(0.0)
        self._press.to(0.0, 180)
        super().leaveEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._press.to(1.0, 80)
            self._ripple_pos = e.position()
            self._ripple.jump(0.0)
            self._ripple.to(1.0)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._press.to(0.0, 220, QEasingCurve.Type.OutBack)
        super().mouseReleaseEvent(e)

    def focusInEvent(self, e) -> None:  # noqa: N802
        self._focus.to(1.0)
        super().focusInEvent(e)

    def focusOutEvent(self, e) -> None:  # noqa: N802
        self._focus.to(0.0)
        super().focusOutEvent(e)

    # -- sizing ---------------------------------------------------------------
    def _font(self) -> QFont:
        f = QFont(self.font())
        f.setPixelSize(tokens.FONT_SIZE["body"])
        f.setWeight(QFont.Weight.DemiBold if self.kind == "primary" else QFont.Weight.Medium)
        return f

    def sizeHint(self) -> QSize:  # noqa: N802
        fm = QFontMetrics(self._font())
        w = fm.horizontalAdvance(self.text()) + (36 if self.kind != "nav" else 32)
        if self.icon_name:
            w += 18 + 8
        return QSize(max(w, 44), tokens.SIZE["button_h"])

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    # -- painting ---------------------------------------------------------------
    def _palette(self):
        pal, h, pr, ck = current(), self._hover.value, self._press.value, self._check.value
        k = self.kind
        border = None
        if k == "primary":
            bg = lerp_color(lerp_color(qcolor(pal.accent), qcolor(PRIMARY_HOVER), h), qcolor(PRIMARY_PRESS), pr)
            fg = icon = qcolor(pal.on_accent)
            if not self.isEnabled():
                bg, fg, icon = qcolor(pal.accent_soft), qcolor(pal.text_faint), qcolor(pal.text_faint)
        elif k == "nav":
            show = max(h * 0.55, ck)
            bg = with_alpha(qcolor(pal.surface), show)
            fg = lerp_color(qcolor(pal.text_muted), qcolor(pal.text), max(h, ck))
            icon = lerp_color(lerp_color(qcolor(pal.text_muted), qcolor(pal.text), h), qcolor(pal.accent), ck)
        elif k == "ghost":
            bg = with_alpha(qcolor(pal.surface_hover), h)
            fg = icon = lerp_color(qcolor(pal.text_muted), qcolor(pal.text), h)
        else:
            bg = lerp_color(lerp_color(qcolor(pal.surface), qcolor(pal.surface_hover), h),
                            qcolor(pal.surface_raised), pr)
            border = lerp_color(qcolor(pal.border), with_alpha(qcolor(pal.accent), 0.5), h * 0.6)
            fg = icon = qcolor(pal.text)
        return pal, bg, fg, icon, border

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal, bg, fg, icon, border = self._palette()
        if not self.isEnabled() and self.kind != "primary":
            p.setOpacity(0.45)
        w, h = self.width(), self.height()
        scale = 1 - 0.035 * self._press.value
        p.translate(w / 2, h / 2)
        p.scale(scale, scale)
        p.translate(-w / 2, -h / 2)
        rect = QRectF(0.5, 0.5, w - 1, h - 1)
        r = tokens.RADIUS["md"]
        p.setPen(QPen(border, 1) if border else Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, r, r)
        # ripple
        if self._ripple.value < 0.999 and self.isEnabled():
            clip = QPainterPath()
            clip.addRoundedRect(rect, r, r)
            p.save()
            p.setClipPath(clip)
            t = self._ripple.value
            color = QColor(255, 255, 255, round(70 * (1 - t))) if self.kind == "primary" \
                else with_alpha(qcolor(pal.accent), 0.28 * (1 - t))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            radius = max(w, h) * 1.1 * t
            p.drawEllipse(self._ripple_pos, radius, radius)
            p.restore()
        # keyboard focus ring
        if self._focus.value > 0.01 and self.kind != "nav":
            ring = with_alpha(qcolor(pal.accent), self._focus.value)
            p.setPen(QPen(ring, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, r, r)
        # nav indicator
        if self.kind == "nav" and self._check.value > 0.01:
            bar_h = 18 * self._check.value
            x = w - 4 if self.isRightToLeft() else 1
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(qcolor(pal.accent))
            p.drawRoundedRect(QRectF(x, (h - bar_h) / 2, 3, bar_h), 1.5, 1.5)
        # content
        font = self._font()
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self.text())
        iw = 18 if self.icon_name else 0
        gap = 8 if (iw and self.text()) else 0
        total = iw + gap + tw
        rtl = self.isRightToLeft()
        if self.align == "center":
            x0 = (w - total) / 2
        else:
            x0 = (w - 16 - total) if rtl else 16
        if iw:
            ix = x0 + total - iw if rtl else x0
            p.drawPixmap(QPointF(ix, (h - iw) / 2), icons.tinted(self.icon_name, icon, 18))
        if self.text():
            tx = x0 if rtl else x0 + iw + gap
            p.setPen(fg)
            p.drawText(QRectF(tx, 0, tw + 2, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       self.text())


class IconButton(QAbstractButton):
    def __init__(self, name: str, tooltip: str = "", checkable: bool = False, size: int = 18,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._name, self._size = name, size
        self.setCheckable(checkable)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._hover = Tween(self, self.update, 0.0, 140)
        self._press = Tween(self, self.update, 0.0, 80)
        self._check = Tween(self, self.update, 0.0, 200)
        self.toggled.connect(lambda c: self._check.to(1.0 if c else 0.0))
        theme.changed.connect(self.update)

    def set_icon_name(self, name: str) -> None:
        self._name = name
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(tokens.SIZE["icon_btn"], tokens.SIZE["icon_btn"])

    def enterEvent(self, e) -> None:  # noqa: N802
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover.to(0.0)
        self._press.to(0.0, 160)
        super().leaveEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._press.to(1.0)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        self._press.to(0.0, 220, QEasingCurve.Type.OutBack)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.35)
        h, ck = self._hover.value, self._check.value
        bg = lerp_color(with_alpha(qcolor(pal.surface_hover), h), qcolor(pal.accent_soft), ck)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        r = tokens.RADIUS["md"]
        p.drawRoundedRect(QRectF(self.rect()), r, r)
        color = lerp_color(lerp_color(qcolor(pal.text_muted), qcolor(pal.text), h), qcolor(pal.accent), ck)
        s = self._size * (1 - 0.14 * self._press.value)
        pm = icons.tinted(self._name, color, self._size)
        p.drawPixmap(QPointF((self.width() - s) / 2, (self.height() - s) / 2),
                     pm.scaled(int(s * 2), int(s * 2), Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                     if self._press.value > 0.01 else pm)
        if self.hasFocus():
            p.setPen(QPen(qcolor(pal.accent), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), r, r)


class SmoothSlider(QSlider):
    """Slider with click-to-jump, animated handle and animated programmatic changes."""

    MARGIN = 12

    def __init__(self, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dragging = False
        self._shown = float(self.value())
        self._hover = Tween(self, self.update, 0.0, 150)
        self._press = Tween(self, self.update, 0.0, 120)
        self._pos = QVariantAnimation(self)
        self._pos.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pos.valueChanged.connect(self._on_pos)
        self.valueChanged.connect(self._follow)
        theme.changed.connect(self.update)

    def _on_pos(self, v) -> None:
        self._shown = float(v)
        self.update()

    def _follow(self, value: int) -> None:
        if self._dragging or ms(220) == 0:
            self._pos.stop()
            self._shown = float(value)
            self.update()
            return
        self._pos.stop()
        self._pos.setDuration(ms(220))
        self._pos.setStartValue(self._shown)
        self._pos.setEndValue(float(value))
        self._pos.start()

    def _value_at(self, x: float) -> int:
        span = max(1, self.width() - 2 * self.MARGIN)
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                                              int(x - self.MARGIN), span)

    def enterEvent(self, e) -> None:  # noqa: N802
        self._hover.to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:  # noqa: N802
        self._hover.to(0.0)
        super().leaveEvent(e)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._press.to(1.0)
            self.setValue(self._value_at(e.position().x()))
            self.setSliderDown(True)
            e.accept()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._dragging:
            self.setValue(self._value_at(e.position().x()))
            e.accept()

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if self._dragging:
            self._dragging = False
            self.setSliderDown(False)
            self._press.to(0.0, 220, QEasingCurve.Type.OutBack)
            e.accept()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        span = max(1, self.maximum() - self.minimum())
        frac = (self._shown - self.minimum()) / span
        x0, x1 = self.MARGIN, self.width() - self.MARGIN
        cx, cy = x0 + (x1 - x0) * frac, self.height() / 2
        track = QRectF(x0 - 3, cy - 3, (x1 - x0) + 6, 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor(pal.surface_raised if pal.name == "dark" else "#E4E0D6"))
        p.drawRoundedRect(track, 3, 3)
        p.setBrush(qcolor(pal.accent))
        p.drawRoundedRect(QRectF(x0 - 3, cy - 3, max(0.0, cx - x0 + 3), 6), 3, 3)
        h, pr = self._hover.value, self._press.value
        halo = 9 + 7 * max(h * 0.6, pr)
        p.setBrush(with_alpha(qcolor(pal.accent), 0.20 * max(h, pr)))
        p.drawEllipse(QPointF(cx, cy), halo, halo)
        r = 8 + 1.5 * h + 0.5 * pr
        p.setBrush(qcolor(pal.surface))
        p.drawEllipse(QPointF(cx, cy), r + 2.5, r + 2.5)
        p.setBrush(lerp_color(qcolor("#FFFFFF" if pal.name == "dark" else pal.text),
                              qcolor(pal.accent), max(h * 0.5, pr)))
        p.drawEllipse(QPointF(cx, cy), r, r)
        if self.hasFocus():
            p.setPen(QPen(qcolor(pal.accent), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r + 4.5, r + 4.5)


class ValueLabel(QWidget):
    """Number/text that rolls vertically when it changes (odometer effect)."""

    def __init__(self, text: str = "", min_width: int = 40, parent: QWidget | None = None):
        super().__init__(parent)
        self._old, self._new, self._dir = text, text, 1
        self._t = Tween(self, self.update, 1.0, 200)
        self.setMinimumWidth(min_width)
        self.setFixedHeight(28)
        theme.changed.connect(self.update)

    def text(self) -> str:
        return self._new

    def setText(self, text: str) -> None:  # noqa: N802
        if text == self._new:
            return
        try:
            self._dir = 1 if float(text) >= float(self._new) else -1
        except ValueError:
            self._dir = 1
        self._old, self._new = self._new, text
        self._t.jump(0.0)
        self._t.to(1.0)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.minimumWidth(), 28)

    def paintEvent(self, _e) -> None:  # noqa: N802
        p, pal = QPainter(self), current()
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        f = QFont(self.font())
        f.setPixelSize(tokens.FONT_SIZE["title"])
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        t, h = self._t.value, self.height()
        flags = Qt.AlignmentFlag.AlignCenter
        base = qcolor(pal.text)
        if t >= 0.999:
            p.setPen(base)
            p.drawText(QRectF(self.rect()), flags, self._new)
            return
        travel = h * 0.55
        p.setPen(with_alpha(base, 1 - t))
        p.drawText(QRectF(0, -self._dir * travel * t, self.width(), h), flags, self._old)
        p.setPen(with_alpha(lerp_color(qcolor(pal.accent), base, t), t))
        p.drawText(QRectF(0, self._dir * travel * (1 - t), self.width(), h), flags, self._new)
