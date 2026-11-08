import time

import pytest

pytest.importorskip("PySide6")

from eyecare.core.config import Settings  # noqa: E402
from eyecare.core.stats import Stats  # noqa: E402
from eyecare.engine import Engine  # noqa: E402
from eyecare.ui.pages.home import HomePage  # noqa: E402
from eyecare.ui.tray import Tray  # noqa: E402


@pytest.fixture
def engine(app, tmp_path):
    s = Settings()
    s.rule202020.interval_min = 1
    s.blink.interval_min = 1
    s.blink.enabled = True
    s.hydration.enabled = False
    return Engine(s, Stats(tmp_path / "st.json"), tmp_path / "s.json")


def ticks(e, n):
    for _ in range(n):
        e.on_tick()


def test_quiet_blocks_prompts_and_blinks(engine):
    seen = []
    engine.prompt_requested.connect(lambda: seen.append("prompt"))
    engine.blink_requested.connect(lambda: seen.append("blink"))
    engine.set_quiet(60)
    assert engine.quiet_active and engine.holding
    ticks(engine, 200)
    assert seen == [] and engine.rule.seconds_to_break == 60


def test_ending_quiet_resumes_reminders(engine):
    seen = []
    engine.prompt_requested.connect(lambda: seen.append("prompt"))
    engine.set_quiet(60)
    ticks(engine, 30)
    engine.set_quiet(0)
    assert not engine.quiet_active
    ticks(engine, 60)
    assert seen == ["prompt"]


def test_quiet_expires_by_itself(engine):
    engine.quiet_until = time.time() - 1
    assert not engine.quiet_active
    engine.on_tick()
    assert engine.quiet_until == 0.0


def test_quiet_forever_and_toggle(engine):
    engine.set_quiet(None)
    assert engine.quiet_active and engine.quiet_until == float("inf")
    assert engine.toggle_quiet() is False
    assert engine.toggle_quiet(30) is True


def test_busy_reason_holds_like_quiet(engine):
    seen = []
    engine.prompt_requested.connect(lambda: seen.append(1))
    engine.set_busy("fullscreen")
    ticks(engine, 120)
    assert seen == [] and engine.holding
    engine.set_busy(None)
    ticks(engine, 60)
    assert seen == [1]


def test_quiet_does_not_stop_a_manual_break(engine):
    engine.set_quiet(60)
    engine.start_break()
    done = []
    engine.break_finished.connect(done.append)
    ticks(engine, engine.settings.rule202020.break_seconds)
    assert done == [True]


def test_home_shows_quiet_state_and_button(engine):
    p = HomePage(engine)
    engine.set_quiet(60)
    p.refresh()
    assert "Quiet until" in p.status.text() and "End" in p.quiet_btn.text()
    p.quiet_btn.click()
    assert not engine.quiet_active
    engine.set_busy("meeting")
    p.refresh()
    assert "meeting" in p.status.text().lower()


def test_tray_quiet_menu(engine):
    t = Tray(engine)
    assert len(t.quiet_actions) == 5
    assert t.quiet_end_action.isVisible() is False
    t.meeting_action.trigger()
    assert engine.quiet_active and t.quiet_end_action.isVisible() is True
    t.quiet_end_action.trigger()
    assert not engine.quiet_active and t.quiet_end_action.isVisible() is False
    t.quiet_actions[4][0].trigger()
    assert engine.quiet_until == float("inf")
