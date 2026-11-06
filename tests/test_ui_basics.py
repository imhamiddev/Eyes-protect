import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from eyecare.ui import fonts, icons, tokens  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_palettes_are_complete_and_share_accent():
    d, l = tokens.DARK.__dict__, tokens.LIGHT.__dict__
    assert d.keys() == l.keys()
    assert tokens.DARK.accent == tokens.LIGHT.accent == "#D2F36B"
    assert tokens.DARK.bg == "#111318" and tokens.DARK.surface == "#1C2028"
    assert tokens.DARK.text_muted == "#A1A1AA" and tokens.DARK.text == "#FFFFFF"


def test_every_icon_renders(app):
    for name in icons.NAMES:
        img = icons.pixmap(name, "#ffffff", 20).toImage()
        assert not img.isNull()
        assert any(
            img.pixelColor(x, y).alpha() > 0
            for x in range(0, img.width(), 2) for y in range(0, img.height(), 2)
        ), name


def test_fonts_load(app):
    from PySide6.QtGui import QFontDatabase

    fonts.load_fonts()
    families = QFontDatabase.families()
    assert "Inter" in families and "Vazirmatn" in families
    assert fonts.font_family("fa").startswith('"Vazirmatn"')
    assert fonts.font_family("en").startswith('"Inter"')
