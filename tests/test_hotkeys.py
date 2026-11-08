import pytest

pytest.importorskip("PySide6")

from eyecare.core import hotkeys as hk  # noqa: E402
from eyecare.core import winapi  # noqa: E402
from eyecare.hotkeys import HotkeyManager  # noqa: E402


@pytest.fixture
def fake(monkeypatch):
    state = {"registered": {}, "unregistered": [], "reject": set()}

    def register(i, mods, vk):
        if (mods & ~hk.MOD_NOREPEAT, vk) in state["reject"]:
            return False
        state["registered"][i] = (mods, vk)
        return True

    monkeypatch.setattr(winapi, "register_hotkey", register)
    monkeypatch.setattr(winapi, "unregister_hotkey", state["unregistered"].append)
    return state


def test_registers_every_action_with_norepeat(app, fake):
    m = HotkeyManager()
    assert m.register(True, hk.DEFAULTS) == set()
    assert len(fake["registered"]) == 4
    assert all(mods & hk.MOD_NOREPEAT for mods, _ in fake["registered"].values())
    m.shutdown()
    assert len(fake["unregistered"]) == 4


def test_hotkey_message_triggers_the_right_action(app, fake):
    m = HotkeyManager()
    m.register(True, hk.DEFAULTS)
    seen = []
    m.triggered.connect(seen.append)
    ids = {action: i for i, action in m._ids.items()}
    for action in hk.ACTIONS:
        assert m.handle(ids[action]) is True
    assert m.handle(0xBEEF) is False
    assert seen == list(hk.ACTIONS)
    m.shutdown()


def test_disabled_registers_nothing_and_clears_old(app, fake):
    m = HotkeyManager()
    m.register(True, hk.DEFAULTS)
    assert m.register(False, hk.DEFAULTS) == set()
    assert m._ids == {} and len(fake["unregistered"]) >= 4
    m.shutdown()


def test_taken_or_invalid_shortcuts_are_reported(app, fake):
    fake["reject"].add(hk.parse_combo("Ctrl+Alt+B"))   # another app owns it
    m = HotkeyManager()
    mapping = dict(hk.DEFAULTS, pause="P")              # no modifier -> invalid
    assert m.register(True, mapping) == {"break_now", "pause"}
    assert set(m._ids.values()) == {"night_light", "quiet"}
    m.shutdown()


def test_reregistering_replaces_previous_ids(app, fake):
    m = HotkeyManager()
    m.register(True, hk.DEFAULTS)
    m.register(True, dict(hk.DEFAULTS, night_light="Ctrl+Shift+L"))
    assert len(m._ids) == 4 and (hk.MOD_CONTROL | hk.MOD_SHIFT | hk.MOD_NOREPEAT, ord("L")) in \
        fake["registered"].values()
    m.shutdown()
