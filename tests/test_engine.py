import pytest

pytest.importorskip("PySide6")


from eyecare.core.config import Settings  # noqa: E402
from eyecare.core.stats import Stats  # noqa: E402
from eyecare.engine import Engine  # noqa: E402



def make(tmp_path, **rule):
    s = Settings()
    s.rule202020.interval_min = 1
    s.rule202020.break_seconds = 3
    for k, v in rule.items():
        setattr(s.rule202020, k, v)
    s.blink.enabled = s.hydration.enabled = False
    return Engine(s, Stats(tmp_path / "st.json"), tmp_path / "s.json")


def test_prompt_then_break_updates_stats(app, tmp_path):
    e = make(tmp_path)
    seen = []
    e.prompt_requested.connect(lambda: seen.append("prompt"))
    e.break_started.connect(lambda n: seen.append(f"start{n}"))
    e.break_finished.connect(lambda ok: seen.append(f"done{ok}"))
    for _ in range(60):
        e.on_tick()
    e.start_break()
    for _ in range(3):
        e.on_tick()
    assert seen == ["prompt", "start3", "doneTrue"]
    assert e.stats.get("breaks") == 1


def test_skip_is_counted(app, tmp_path):
    e = make(tmp_path, use_break_lock=True)
    for _ in range(60):
        e.on_tick()
    e.skip_break()
    assert e.stats.get("skipped") == 1


def test_pause_stops_prompts(app, tmp_path):
    e = make(tmp_path)
    got = []
    e.prompt_requested.connect(lambda: got.append(1))
    e.set_paused(True)
    for _ in range(120):
        e.on_tick()
    assert got == []


def test_quick_night_light_toggle(app, tmp_path):
    e = make(tmp_path)
    assert e.toggle_night_light() is True
    assert e.settings.night_light.schedule is False
    assert e.toggle_night_light() is False


def test_commit_settings_persists(app, tmp_path):
    e = make(tmp_path)
    e.settings.hydration.interval_min = 33
    e.commit_settings()
    assert (tmp_path / "s.json").exists()
    assert e.water.interval_min == 33


def test_manual_night_light_toggle_fades_smoothly(app, tmp_path, monkeypatch):
    import time as _t

    from eyecare.core import winapi
    from eyecare.ui import motion

    ramps = []
    monkeypatch.setattr(winapi, "set_gamma_ramp", lambda r: ramps.append(r) or True)
    motion.set_enabled(True)
    e = make(tmp_path)
    e.settings.night_light.strength = 100
    e.apply_display(force=True)
    start = len(ramps)
    e.toggle_night_light()
    assert e._tween.state() == e._tween.State.Running  # eased, not an instant jump
    end = _t.time() + 3
    while e._tween.state() == e._tween.State.Running and _t.time() < end:
        app.processEvents()
        _t.sleep(0.01)
    assert e._shown.kelvin == 1900 and len(ramps) - start > 3
    assert e.display_state.kelvin == 1900


def test_manual_toggle_is_instant_without_animations(app, tmp_path):
    from eyecare.ui import motion

    motion.set_enabled(False)
    try:
        e = make(tmp_path)
        e.settings.night_light.strength = 100
        e.apply_display(force=True)
        e.toggle_night_light()
        assert e._tween.state() != e._tween.State.Running and e._shown.kelvin == 1900
    finally:
        motion.set_enabled(True)


def _two_monitors(monkeypatch):
    from eyecare.core import winapi

    mons = [winapi.Monitor("\\\\.\\DISPLAY1", 1920, 1080, True),
            winapi.Monitor("\\\\.\\DISPLAY2", 2560, 1440, False)]
    calls = {}
    monkeypatch.setattr(winapi, "list_monitors", lambda: mons)
    monkeypatch.setattr(winapi, "set_monitor_gamma_ramp",
                        lambda device, ramp: calls.__setitem__(device, ramp) or True)
    return mons, calls


def test_filters_apply_to_every_monitor_by_default(app, tmp_path, monkeypatch):
    from eyecare.core import winapi
    from eyecare.ui import motion

    motion.set_enabled(False)
    _mons, calls = _two_monitors(monkeypatch)
    e = make(tmp_path)
    e.settings.night_light.enabled, e.settings.night_light.strength = True, 100
    e.settings.night_light.schedule = False
    e.commit_settings()
    assert set(calls) == {"\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"}
    for ramp in calls.values():
        assert ramp[2][255] < ramp[0][255]  # blue reduced -> warm
    motion.set_enabled(True)


def test_excluded_monitor_stays_neutral_and_brightness_is_per_monitor(app, tmp_path, monkeypatch):
    from eyecare.core import winapi
    from eyecare.ui import motion

    motion.set_enabled(False)
    _mons, calls = _two_monitors(monkeypatch)
    e = make(tmp_path)
    nl = e.settings.night_light
    nl.enabled, nl.strength, nl.schedule = True, 100, False
    e.settings.monitors.excluded = "DISPLAY2"
    e.settings.monitors.brightness = "DISPLAY1=50"
    e.commit_settings()
    assert calls["\\\\.\\DISPLAY2"] == winapi.IDENTITY_RAMP
    warm, identity = calls["\\\\.\\DISPLAY1"], winapi.IDENTITY_RAMP
    assert warm[0][255] < identity[0][255]  # dimmed to ~50% -> clamped to 30%+ range
    motion.set_enabled(True)


def test_neutral_monitor_factor_dims_even_without_filters(app, tmp_path, monkeypatch):
    from eyecare.core import winapi
    from eyecare.ui import motion

    motion.set_enabled(False)
    _mons, calls = _two_monitors(monkeypatch)
    e = make(tmp_path)
    e.settings.monitors.brightness = "DISPLAY2=60"
    e.commit_settings()
    assert calls["\\\\.\\DISPLAY1"] == winapi.IDENTITY_RAMP
    assert calls["\\\\.\\DISPLAY2"][0][255] < 65535
    motion.set_enabled(True)


def test_monitor_hotplug_is_detected(app, tmp_path, monkeypatch):
    from eyecare.core import winapi

    mons, calls = _two_monitors(monkeypatch)
    e = make(tmp_path)
    assert len(e.monitors) == 2
    monkeypatch.setattr(winapi, "list_monitors", lambda: mons[:1])
    assert e.refresh_monitors() is True and len(e.monitors) == 1
    assert e.refresh_monitors() is False


def test_active_time_and_longest_stretch_are_tracked(app, tmp_path):
    e = make(tmp_path, detect_natural_breaks=False)
    for _ in range(90):
        e.on_tick()
    assert e.stats.get("active_s") == 90 and e.stats.get("longest_run_s") == 90


def test_idle_time_is_not_counted_and_resets_the_run(app, tmp_path, monkeypatch):
    from eyecare.core import winapi

    e = make(tmp_path, detect_natural_breaks=False)
    for _ in range(40):
        e.on_tick()
    monkeypatch.setattr(winapi, "idle_seconds", lambda: 300.0)
    for _ in range(30):
        e.on_tick()
    monkeypatch.setattr(winapi, "idle_seconds", lambda: 0.0)
    for _ in range(10):
        e.on_tick()
    assert e.stats.get("active_s") == 50           # 40 + 10, the idle 30 s excluded
    assert e.stats.get("longest_run_s") == 40      # the run restarted after the rest


def test_taking_a_break_restarts_the_stretch(app, tmp_path):
    e = make(tmp_path, detect_natural_breaks=False)
    for _ in range(30):
        e.on_tick()
    e.start_break()
    for _ in range(3):
        e.on_tick()
    assert e._run_seconds <= 1
