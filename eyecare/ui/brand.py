"""Brand mark: a lime eye on a soft dark tile (used for the window, tray and exe)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap

from . import icons
from .tokens import ACCENT, DARK


def logo_pixmap(size: int = 256, tile: bool = True) -> QPixmap:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if tile:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(DARK.surface))
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    glyph = int(size * (0.58 if tile else 0.9))
    pm = icons.pixmap("eye", ACCENT, glyph, stroke=1.9, dpr=1.0)
    off = (size - glyph) / 2
    p.drawPixmap(int(off), int(off), pm)
    p.end()
    return QPixmap.fromImage(image)


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(size))
    return icon
