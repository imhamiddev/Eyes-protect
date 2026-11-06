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
