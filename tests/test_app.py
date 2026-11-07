import pytest

pytest.importorskip("PySide6")

from eyecare.app import EyeCareApp  # noqa: E402
from eyecare.core import i18n  # noqa: E402
from eyecare.core.config import Settings  # noqa: E402
from eyecare.core.stats import Stats  # noqa: E402
from eyecare.engine import Engine  # noqa: E402
from eyecare.features.rule202020 import Phase  # noqa: E402


@pytest.fixture
def ea(app, tmp_path):
    s = Settings()
    s.rule202020.interval_min = 1
    s.rule202020.break_seconds = 3
    s.blink.enabled = s.hydration.enabled = False
    i18n.set_language("en")
    engine = Engine(s, Stats(tmp_path / "st.json"), tmp_path / "s.json")
    a = EyeCareApp(app, engine)
    yield a
    a.toasts.clear()
    a.overlay.end()
    a._theme_watch.stop()
    a.window.quitting = True
    a.window.close()


def run_ticks(a, n):
    for _ in range(n):
        a.engine.on_tick()


def test_prompt_shows_toast_and_start_runs_break(ea):
    run_ticks(ea, 60)
    assert ea._prompt_toast is not None and ea.toasts.count() == 1
    ea.engine.start_break()
    assert ea._prompt_toast is None
    assert ea._mini_toast is not None  # no break lock: floating mini window
    run_ticks(ea, 3)
    assert ea._mini_toast is None
    assert ea.engine.stats.get("breaks") == 1


def test_break_lock_uses_fullscreen_overlay(ea):
    ea.engine.settings.rule202020.use_break_lock = True
    ea.engine.commit_settings()
    run_ticks(ea, 60)
    assert ea.overlay.active
    ea.overlay.skipped.emit()
    assert not ea.overlay.active
    assert ea.engine.stats.get("skipped") == 1


def test_stale_prompt_toast_is_dismissed_on_snooze(ea):
    run_ticks(ea, 60)
    ea.engine.snooze()
    run_ticks(ea, 1)
    assert ea._prompt_toast is None and ea.engine.rule.phase == Phase.WORKING


def test_language_switch_rebuilds_ui_in_persian(ea):
    ea.engine.settings.general.language = "fa"
    ea.engine.commit_settings()
    assert i18n.language() == "fa" and ea.qt.layoutDirection().name == "RightToLeft"
    assert ea.window.nav[0].text().strip() == "خانه"
    ea.engine.settings.general.language = "en"
    ea.engine.commit_settings()
    assert ea.window.nav[0].text().strip() == "Home"


def test_theme_switch_applies_palette(ea):
    ea.engine.settings.general.theme = "light"
    ea.engine.commit_settings()
    from eyecare.ui.theme import theme

    assert theme.palette.name == "light"
    ea.engine.settings.general.theme = "dark"
    ea.engine.commit_settings()
    assert theme.palette.name == "dark"


def test_blink_and_water_toasts(ea):
    ea.on_blink()
    ea.on_water()
    assert ea.toasts.count() == 2 and ea.engine.stats.get("blinks") == 1


def test_animations_switch_is_applied_globally(ea):
    from eyecare.ui import motion

    ea.engine.settings.general.animations = False
    ea.engine.commit_settings()
    assert motion.enabled() is False
    ea.engine.settings.general.animations = True
    ea.engine.commit_settings()
    assert motion.enabled() is True
