from datetime import time

from eyecare.core.config import AutoDarkMode, Dimmer, NightLight
from eyecare.features.display import (
    compute_display_state,
    effective_profile,
    night_light_active,
    wants_light_theme,
)

NIGHT = time(22, 0)
NOON = time(12, 0)


def test_night_light_off_by_default():
    assert not night_light_active(NightLight(), NIGHT)


def test_night_light_schedule_window():
    cfg = NightLight(enabled=True, schedule=True, start="20:00", end="06:30")
    assert night_light_active(cfg, NIGHT) and not night_light_active(cfg, NOON)


def test_night_light_without_schedule_is_always_on():
    assert night_light_active(NightLight(enabled=True, schedule=False), NOON)


def test_bad_schedule_strings_do_not_crash():
    assert not night_light_active(NightLight(enabled=True, start="x", end="y"), NOON)


def test_dimmer_profiles_follow_clock():
    d = Dimmer(enabled=True, day=100, night=60, schedule=True)
    assert effective_profile(d, NIGHT) == "night" and effective_profile(d, NOON) == "day"


def test_study_profile_is_manual():
    d = Dimmer(enabled=True, profile="study", study=80, schedule=True)
    assert effective_profile(d, NIGHT) == "study"


def test_manual_profile_without_schedule():
    d = Dimmer(enabled=True, profile="night", schedule=False)
    assert effective_profile(d, NOON) == "night"


def test_display_state_combines_both():
    n = NightLight(enabled=True, strength=100, schedule=False)
    d = Dimmer(enabled=True, schedule=False, profile="study", study=85)
    s = compute_display_state(n, d, NOON)
    assert s.kelvin == 1900 and abs(s.brightness - 0.85) < 1e-9 and not s.is_neutral


def test_everything_off_is_neutral():
    assert compute_display_state(NightLight(), Dimmer(), NOON).is_neutral


def test_auto_dark_mode():
    cfg = AutoDarkMode(enabled=True, light_from="07:00", dark_from="19:00")
    assert wants_light_theme(cfg, NOON) is True
    assert wants_light_theme(cfg, NIGHT) is False
    assert wants_light_theme(AutoDarkMode(), NOON) is None


# ---- sunrise/sunset windows and gradual transitions -------------------------
from datetime import date  # noqa: E402

from eyecare.core.cities import city_by_key  # noqa: E402
from eyecare.features.display import Window, resolve_window, schedule_factor  # noqa: E402

TEHRAN = city_by_key("tehran")
WIN = Window(20 * 60, 6 * 60 + 30)  # 20:00 -> 06:30


def test_factor_is_zero_outside_and_full_inside():
    assert schedule_factor(12 * 60, WIN, 30) == 0.0
    assert schedule_factor(23 * 60, WIN, 30) == 1.0
    assert schedule_factor(3 * 60, WIN, 30) == 1.0


def test_factor_ramps_up_after_start_and_down_before_end():
    ramp_up = [schedule_factor(20 * 60 + m, WIN, 30) for m in (0, 5, 15, 25, 30)]
    assert ramp_up[0] == 0.0 and ramp_up[-1] == 1.0
    assert ramp_up == sorted(ramp_up) and 0 < ramp_up[2] < 1
    ramp_down = [schedule_factor(6 * 60 + m, WIN, 30) for m in (0, 15, 25, 30)]
    assert ramp_down[0] == 1.0 and ramp_down[-1] == 0.0
    assert ramp_down == sorted(ramp_down, reverse=True)


def test_zero_transition_is_a_hard_edge():
    assert schedule_factor(20 * 60, WIN, 0) == 1.0
    assert schedule_factor(6 * 60 + 29, WIN, 0) == 1.0
    assert schedule_factor(6 * 60 + 30, WIN, 0) == 0.0


def test_short_window_caps_the_ramp():
    w = Window(600, 620)  # 20 minutes
    assert schedule_factor(610, w, 60) == 1.0
    assert schedule_factor(600, w, 60) == 0.0


def test_window_kinds_and_degenerate_windows():
    assert schedule_factor(100, Window(kind="always"), 30) == 1.0
    assert schedule_factor(100, Window(kind="never"), 30) == 0.0
    assert schedule_factor(100, Window(480, 480), 30) == 0.0


def test_resolve_window_fixed_times_and_bad_input():
    w = resolve_window("21:00", "05:30", False, None, date(2024, 1, 1), 0)
    assert (w.start, w.end, w.kind) == (21 * 60, 5 * 60 + 30, "range")
    assert resolve_window("zz", "05:30", False, None, date(2024, 1, 1), 0).kind == "never"


def test_resolve_window_sun_uses_sunset_to_sunrise():
    w = resolve_window("", "", True, TEHRAN, date(2024, 12, 21), 3.5)
    assert 16 * 60 + 40 < w.start < 17 * 60 + 15 and 6 * 60 + 50 < w.end < 7 * 60 + 30


def test_resolve_window_polar():
    tromso = city_by_key("stockholm")
    assert resolve_window("", "", True, tromso, date(2024, 6, 21), 2).kind == "range"
    from eyecare.core.cities import City

    arctic = City("x", "x", "x", 69.65, 18.96)
    assert resolve_window("", "", True, arctic, date(2024, 6, 21), 2).kind == "never"
    assert resolve_window("", "", True, arctic, date(2024, 12, 21), 1).kind == "always"


def test_night_light_fades_gradually_through_the_evening():
    n = NightLight(enabled=True, strength=100, schedule=True, start="20:00", end="06:30",
                   transition_min=30)
    ks = [compute_display_state(n, Dimmer(), time(20, m)).kelvin for m in (0, 10, 20, 30)]
    assert ks[0] == 6500 and ks[-1] == 1900
    assert ks == sorted(ks, reverse=True) and 1900 < ks[1] < 6500


def test_night_light_follows_sunset_in_winter_vs_summer():
    n = NightLight(enabled=True, strength=100, schedule=True, sun=True, transition_min=0)
    evening = time(18, 30)
    winter = compute_display_state(n, Dimmer(), evening, TEHRAN, date(2024, 12, 21), 3.5)
    summer = compute_display_state(n, Dimmer(), evening, TEHRAN, date(2024, 6, 21), 3.5)
    assert winter.kelvin == 1900 and summer.kelvin == 6500


def test_dimmer_blends_day_and_night_brightness_across_the_transition():
    d = Dimmer(enabled=True, schedule=True, day=100, night=60, night_start="20:00", night_end="06:30")
    n = NightLight(transition_min=30)
    vals = [compute_display_state(n, d, time(20, m)).brightness for m in (0, 15, 30)]
    assert vals[0] == 1.0 and abs(vals[2] - 0.6) < 1e-9 and 0.6 < vals[1] < 1.0
    assert compute_display_state(n, d, time(12, 0)).brightness == 1.0


def test_dimmer_sun_mode():
    d = Dimmer(enabled=True, schedule=True, sun=True, day=100, night=70)
    n = NightLight(transition_min=0)
    s = compute_display_state(n, d, time(18, 30), TEHRAN, date(2024, 12, 21), 3.5)
    assert abs(s.brightness - 0.7) < 1e-9
