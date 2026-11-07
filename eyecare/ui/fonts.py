"""Loads the bundled Inter (English) and Vazirmatn (Persian) fonts."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase

_loaded = False


def assets_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" if (base / "assets").exists() else base / "eyecare" / "assets"


def load_fonts() -> None:
    global _loaded
    if _loaded:
        return
    for path in sorted((assets_dir() / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))
    _loaded = True


def font_family(language: str) -> str:
    """CSS font-family list; Vazirmatn first for Persian so digits/glyphs match."""
    if language == "fa":
        return '"Vazirmatn", "Inter", "Segoe UI"'
    return '"Inter", "Vazirmatn", "Segoe UI"'
