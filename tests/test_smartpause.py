import pytest

from eyecare.core.config import SmartPause
from eyecare.features import smartpause as sp

ON = SmartPause()
FG = (100, "chrome.exe", "Docs - Chrome")


def test_nothing_busy_by_default():
    assert sp.classify(ON, 5, FG) is None
    assert sp.classify(ON, None, None) is None


@pytest.mark.parametrize("state", [2, 3, 4, 7])
def test_fullscreen_states(state):
    assert sp.classify(ON, state, FG) == "fullscreen"


def test_focus_assist():
    assert sp.classify(ON, 6, FG) == "focus"
    assert sp.classify(SmartPause(focus_assist=False), 6, FG) is None


def test_master_switch_and_sub_switches():
    assert sp.classify(SmartPause(enabled=False), 2, FG) is None
    assert sp.classify(SmartPause(fullscreen=False), 2, FG) is None
    meet = (1, "zoom.exe", "Zoom Meeting")
    assert sp.classify(SmartPause(meetings=False), 5, meet) is None


@pytest.mark.parametrize("exe,title", [
    ("zoom.exe", "Zoom Meeting"),
    ("ms-teams.exe", "Weekly sync | Meeting | Microsoft Teams"),
    ("chrome.exe", "Meet - abc-defg-hij - Google Chrome"),
    ("msedge.exe", "Google Meet"),
    ("webex.exe", "Team call"),
])
def test_meetings_detected(exe, title):
    assert sp.classify(ON, 5, (1, exe, title)) == "meeting"


@pytest.mark.parametrize("exe,title", [
    ("teams.exe", "Chat | Anna | Microsoft Teams"),
    ("chrome.exe", "How to hold a meeting - Wikipedia"),
    ("notepad.exe", "meeting notes.txt"),
    ("zoom.exe", "Zoom"),
])
def test_non_meetings_ignored(exe, title):
    assert sp.classify(ON, 5, (1, exe, title)) is None


def test_own_break_screen_is_not_busy():
    assert sp.classify(ON, 2, (4242, "eyecare.exe", "Eye Care"), own_pid=4242) is None
    assert sp.classify(ON, 2, (4242, "eyecare.exe", "Eye Care"), own_pid=1) == "fullscreen"
    assert sp.classify(ON, 6, (4242, "eyecare.exe", ""), own_pid=4242) == "focus"


def test_debouncer_enters_slowly_and_leaves_fast():
    d = sp.Debouncer(2)
    assert d.update("fullscreen") is None
    assert d.update("fullscreen") == "fullscreen"
    assert d.update("fullscreen") == "fullscreen"
    assert d.update(None) is None
    assert d.update("meeting") is None


def test_debouncer_resets_candidate_on_change():
    d = sp.Debouncer(2)
    d.update("fullscreen")
    assert d.update("meeting") is None
    assert d.update("meeting") == "meeting"
