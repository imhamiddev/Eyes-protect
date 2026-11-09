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


def test_update_ready_shows_toast_and_install_quits(ea):
    from eyecare.core import updater

    info = updater.ReleaseInfo("9.9.9", "v9.9.9", "", "https://github.com/x", 3, None, "p")
    ea.on_update_ready(info)
    assert ea.toasts.count() == 1
    quits = []
    ea.engine.updates.quit_requested.connect(lambda: quits.append(1))
    ea.engine.updates.quit_requested.emit()  # the real quit() runs too (shuts the engine down)
    assert quits == [1] and ea.window.quitting is True


def test_posture_toast_and_stretch_runner(ea):
    ea.on_posture()
    assert ea.toasts.count() == 1
    runner = ea.start_stretch()
    assert runner.exercise.kind == "body"
    runner.timer.stop()
    runner.close()


def test_engine_emits_posture_reminder(ea):
    seen = []
    ea.engine.posture_requested.connect(lambda: seen.append(1))
    ea.engine.settings.posture.interval_min = 1
    ea.engine.commit_settings()
    for _ in range(60):
        ea.engine.on_tick()
    assert seen == [1]


def test_hotkey_actions_drive_the_engine(ea):
    e = ea.engine
    before = e.settings.night_light.enabled
    ea.on_hotkey("night_light")
    assert e.settings.night_light.enabled is (not before) and ea.toasts.count() == 1
    ea.on_hotkey("pause")
    assert e.paused is True
    ea.on_hotkey("pause")
    assert e.paused is False
    ea.on_hotkey("quiet")
    assert e.quiet_active
    ea.on_hotkey("quiet")
    assert not e.quiet_active
    ea.on_hotkey("break_now")
    assert e.rule.phase.value == "break"


def test_changed_hotkey_settings_reregister(ea, monkeypatch):
    calls = []
    monkeypatch.setattr(ea.hotkeys, "register", lambda en, m: calls.append((en, dict(m))) or set())
    ea.engine.settings.hotkeys.enabled = False
    ea.engine.commit_settings()
    assert calls and calls[-1][0] is False
    n = len(calls)
    ea.engine.commit_settings()          # nothing changed -> no re-registration
    assert len(calls) == n


def _sound_log(ea, monkeypatch):
    played = []
    monkeypatch.setattr(ea.engine.sounds, "play", lambda kind, vol: played.append((kind, vol)) or True)
    return played


def test_break_chimes_play_at_start_and_end(ea, monkeypatch):
    played = _sound_log(ea, monkeypatch)
    ea.engine.settings.sound.volume = 40
    ea.engine.start_break()
    for _ in range(ea.engine.settings.rule202020.break_seconds):
        ea.engine.on_tick()
    assert played == [("start", 40), ("end", 40)]


def test_skipped_break_has_no_end_chime(ea, monkeypatch):
    played = _sound_log(ea, monkeypatch)
    ea.engine.start_break()
    ea.engine.skip_break()
    assert [k for k, _ in played] == ["start"]


def test_sounds_can_be_switched_off(ea, monkeypatch):
    played = _sound_log(ea, monkeypatch)
    ea.engine.settings.sound.enabled = False
    ea.engine.start_break()
    assert played == []


def test_reminder_pings_need_their_own_switch(ea, monkeypatch):
    played = _sound_log(ea, monkeypatch)
    ea.on_blink()
    ea.on_water()
    ea.on_posture()
    assert played == []
    ea.engine.settings.sound.reminder_sounds = True
    ea.on_blink()
    ea.on_water()
    ea.on_posture()
    assert [k for k, _ in played] == ["notify"] * 3
