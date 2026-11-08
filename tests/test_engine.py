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
