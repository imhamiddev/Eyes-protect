import pytest

from eyecare.core import hotkeys as hk


def test_parse_basic_combos():
    assert hk.parse_combo("Ctrl+Alt+N") == (hk.MOD_CONTROL | hk.MOD_ALT, ord("N"))
    assert hk.parse_combo("shift+ctrl+f5") == (hk.MOD_SHIFT | hk.MOD_CONTROL, 0x74)
    assert hk.parse_combo("Win+Space") == (hk.MOD_WIN, 0x20)
    assert hk.parse_combo("Meta+9") == (hk.MOD_WIN, ord("9"))
    assert hk.parse_combo("Ctrl+Left")[1] == 0x25


@pytest.mark.parametrize("bad", ["N", "Ctrl", "Ctrl+Alt", "Ctrl+N+M", "Ctrl+Nope", "Alt+F25", "", "+"])
def test_invalid_combos(bad):
    with pytest.raises(ValueError):
        hk.parse_combo(bad)
    assert not hk.is_valid(bad)


def test_normalize_orders_modifiers_and_cases_the_key():
    assert hk.normalize("alt + ctrl + n") == "Ctrl+Alt+N"
    assert hk.normalize("Meta+Shift+f12") == "Shift+Win+F12"
    assert hk.normalize("Ctrl+Alt+Space") == "Ctrl+Alt+Space"
    with pytest.raises(ValueError):
        hk.normalize("N")


def test_defaults_are_valid_and_unique():
    assert set(hk.DEFAULTS) == set(hk.ACTIONS)
    parsed = [hk.parse_combo(v) for v in hk.DEFAULTS.values()]
    assert len(set(parsed)) == len(parsed)
