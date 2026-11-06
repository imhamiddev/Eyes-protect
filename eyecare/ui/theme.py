"""Theme manager: owns the active palette and builds the global stylesheet."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from . import tokens
from .fonts import font_family
from .tokens import FONT_SIZE as F
from .tokens import RADIUS as R
from .tokens import Palette


def build_qss(p: Palette, language: str = "en") -> str:
    family = font_family(language)
    return f"""
* {{ font-family: {family}; font-size: {F['body']}px; color: {p.text}; outline: none; }}
QWidget {{ background: transparent; }}
QMainWindow, QDialog, #Root {{ background: {p.bg}; }}
QToolTip {{ background: {p.surface_raised}; color: {p.text}; border: 1px solid {p.border};
  border-radius: {R['sm']}px; padding: 6px 10px; font-size: {F['label']}px; }}

QLabel#H1 {{ font-size: {F['h1']}px; font-weight: 600; }}
QLabel#H2 {{ font-size: {F['h2']}px; font-weight: 600; }}
QLabel#Title {{ font-size: {F['title']}px; font-weight: 600; }}
QLabel#Muted {{ color: {p.text_muted}; }}
QLabel#Caption {{ color: {p.text_faint}; font-size: {F['caption']}px; font-weight: 500; }}
QLabel#Accent {{ color: {p.accent}; }}
QLabel#Display {{ font-size: {F['display']}px; font-weight: 600; }}

QFrame#Card {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: {R['lg']}px; }}
QFrame#CardFlat {{ background: {p.surface_raised}; border-radius: {R['md']}px; }}
QFrame#Sidebar {{ background: {p.bg}; border-right: 1px solid {p.border}; }}
QFrame#Divider {{ background: {p.border}; max-height: 1px; min-height: 1px; border: none; }}

QPushButton {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: {R['md']}px;
  padding: 0 18px; min-height: {tokens.SIZE['button_h']}px; font-weight: 500; }}
QPushButton:hover {{ background: {p.surface_hover}; }}
QPushButton:pressed {{ background: {p.surface_raised}; }}
QPushButton:focus {{ border: 1px solid {p.accent}; }}
QPushButton:disabled {{ color: {p.text_faint}; background: {p.surface_raised}; }}
QPushButton#Primary {{ background: {p.accent}; color: {p.on_accent}; border: none; font-weight: 600; }}
QPushButton#Primary:hover {{ background: #DDF88A; }}
QPushButton#Primary:pressed {{ background: #C2E357; }}
QPushButton#Primary:disabled {{ background: {p.accent_soft}; color: {p.text_faint}; }}
QPushButton#Ghost {{ background: transparent; border: none; color: {p.text_muted}; }}
QPushButton#Ghost:hover {{ background: {p.surface_hover}; color: {p.text}; }}
QPushButton#Danger {{ color: {p.danger}; }}

QToolButton {{ background: transparent; border: none; border-radius: {R['md']}px;
  min-width: {tokens.SIZE['icon_btn']}px; min-height: {tokens.SIZE['icon_btn']}px; }}
QToolButton:hover {{ background: {p.surface_hover}; }}
QToolButton:pressed {{ background: {p.surface_raised}; }}
QToolButton:checked {{ background: {p.accent_soft}; }}
QToolButton:focus {{ border: 1px solid {p.accent}; }}
QToolButton:disabled {{ opacity: .4; }}

QPushButton#NavItem {{ background: transparent; border: none; text-align: left; color: {p.text_muted};
  padding: 0 14px; min-height: 40px; border-radius: {R['md']}px; font-weight: 500; }}
QPushButton#NavItem:hover {{ background: {p.surface}; color: {p.text}; }}
QPushButton#NavItem:checked {{ background: {p.surface}; color: {p.text}; }}

QSlider::groove:horizontal {{ height: 6px; background: {p.surface_raised}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {p.accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {p.text}; width: 18px; height: 18px; margin: -6px 0;
  border-radius: 9px; border: 3px solid {p.surface}; }}
QSlider::handle:horizontal:hover {{ background: {p.accent}; }}
QSlider::handle:horizontal:pressed {{ background: {p.accent}; border-color: {p.accent_soft}; }}
QSlider:disabled {{ opacity: .4; }}

QComboBox {{ background: {p.surface_raised}; border: 1px solid {p.border}; border-radius: {R['md']}px;
  padding: 0 12px; min-height: {tokens.SIZE['control_h']}px; }}
QComboBox:hover {{ background: {p.surface_hover}; }}
QComboBox:focus, QComboBox:on {{ border: 1px solid {p.accent}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{ background: {p.surface}; border: 1px solid {p.border};
  border-radius: {R['md']}px; padding: 4px; selection-background-color: {p.accent_soft};
  selection-color: {p.text}; outline: none; }}

QSpinBox {{ background: {p.surface_raised}; border: 1px solid {p.border}; border-radius: {R['md']}px;
  padding: 0 10px; min-height: {tokens.SIZE['control_h']}px; min-width: 64px; }}
QSpinBox:focus {{ border: 1px solid {p.accent}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.text_faint}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}

QMenu {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: {R['md']}px; padding: 6px; }}
QMenu::item {{ padding: 8px 18px; border-radius: {R['sm']}px; }}
QMenu::item:selected {{ background: {p.surface_hover}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 6px 8px; }}
"""


class ThemeManager(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._palette = tokens.DARK
        self._language = "en"

    @property
    def palette(self) -> Palette:
        return self._palette

    @property
    def language(self) -> str:
        return self._language

    def set_palette(self, name: str) -> None:
        self._palette = tokens.PALETTES.get(name, tokens.DARK)
        self.changed.emit()

    def set_language(self, language: str) -> None:
        self._language = language
        self.changed.emit()

    def qss(self) -> str:
        return build_qss(self._palette, self._language)


theme = ThemeManager()


def current() -> Palette:
    return theme.palette
