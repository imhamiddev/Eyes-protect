import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from eyecare.ui import fonts, tokens  # noqa: E402
from eyecare.ui.theme import ThemeManager, build_qss  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_qss_uses_palette_colours():
    css = build_qss(tokens.DARK)
    for c in (tokens.DARK.bg, tokens.DARK.surface, tokens.DARK.accent, tokens.DARK.text_muted):
        assert c in css
    assert "#111318" in css


def test_light_and_dark_differ():
    assert build_qss(tokens.DARK) != build_qss(tokens.LIGHT)
    assert tokens.LIGHT.bg in build_qss(tokens.LIGHT)


def test_language_changes_font_family():
    assert build_qss(tokens.DARK, "fa").count('"Vazirmatn", "Inter"') > 0


def test_stylesheet_applies_without_warnings(app):
    fonts.load_fonts()
    btn = QPushButton("x")
    btn.setStyleSheet(build_qss(tokens.LIGHT, "fa"))
    btn.ensurePolished()


def test_manager_emits_on_change(app):
    mgr, hits = ThemeManager(), []
    mgr.changed.connect(lambda: hits.append(1))
    mgr.set_palette("light")
    mgr.set_language("fa")
    assert mgr.palette is tokens.LIGHT and len(hits) == 2
    mgr.set_palette("bogus")
    assert mgr.palette is tokens.DARK
