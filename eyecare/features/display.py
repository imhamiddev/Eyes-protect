"""Decides the screen colour/brightness and system theme from settings + time."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from eyecare.core.cities import City
from eyecare.core.colortemp import NEUTRAL_KELVIN, strength_to_kelvin
from eyecare.core.config import AutoDarkMode, Dimmer, NightLight
from eyecare.core.sun import sun_times
from eyecare.core.timeutil import in_window, minutes_precise, parse_hhmm

PROFILES = ("day", "night", "study")


@dataclass(frozen=True)
class DisplayState:
    kelvin: int = NEUTRAL_KELVIN
    brightness: float = 1.0

    @property
    def is_neutral(self) -> bool:
        return self.kelvin >= NEUTRAL_KELVIN and self.brightness >= 1.0


@dataclass(frozen=True)
class Window:
    """A daily window in minutes after midnight. ``kind``: range | always | never."""
    start: float = 0.0
    end: float = 0.0
    kind: str = "range"


def local_utc_offset_hours() -> float:
    offset = datetime.now().astimezone().utcoffset()
    return offset.total_seconds() / 3600 if offset else 0.0


def resolve_window(start: str, end: str, sun: bool, city: City | None, today: date,
                   utc_offset: float) -> Window:
    if sun and city is not None:
        st = sun_times(today, city.lat, city.lon, utc_offset)
        if st.polar == "day":
            return Window(kind="never")
        if st.polar == "night":
            return Window(kind="always")
        return Window(st.sunset, st.sunrise)
    try:
        return Window(minutes_of(parse_hhmm(start)), minutes_of(parse_hhmm(end)))
    except ValueError:
        return Window(kind="never")


def minutes_of(t: time) -> float:
    return t.hour * 60 + t.minute


def schedule_factor(now_min: float, window: Window, transition_min: float = 0.0) -> float:
    """0..1 strength of a scheduled effect: fades in after ``start`` and out before ``end``."""
    if window.kind == "never":
        return 0.0
    if window.kind == "always":
        return 1.0
    length = (window.end - window.start) % 1440
    if length == 0:
        return 0.0
    pos = (now_min - window.start) % 1440
    if pos >= length:
        return 0.0
    ramp = min(float(transition_min), length / 2)
    if ramp <= 0:
        return 1.0
    f = min(1.0, pos / ramp) * min(1.0, (length - pos) / ramp)
    return f * f * (3 - 2 * f)  # smoothstep: gentle at both ends


def _safe_window(now: time, start: str, end: str) -> bool:
    try:
        return in_window(now, parse_hhmm(start), parse_hhmm(end))
    except ValueError:
        return False


def night_light_active(cfg: NightLight, now: time) -> bool:
    if not cfg.enabled:
        return False
    return _safe_window(now, cfg.start, cfg.end) if cfg.schedule else True


def effective_profile(cfg: Dimmer, now: time) -> str:
    """The profile in force: study is always manual; day/night follow the clock."""
    if cfg.profile == "study" or not cfg.schedule:
        return cfg.profile if cfg.profile in PROFILES else "day"
    return "night" if _safe_window(now, cfg.night_start, cfg.night_end) else "day"


def profile_brightness(cfg: Dimmer, profile: str) -> int:
    return int(getattr(cfg, profile, 100))


def compute_display_state(night: NightLight, dimmer: Dimmer, now: time, city: City | None = None,
                          today: date | None = None, utc_offset: float | None = None) -> DisplayState:
    today = today or date.today()
    tz = local_utc_offset_hours() if utc_offset is None else utc_offset
    now_min = minutes_precise(now)

    f_night = 0.0
    if night.enabled:
        if night.schedule:
            win = resolve_window(night.start, night.end, night.sun, city, today, tz)
            f_night = schedule_factor(now_min, win, night.transition_min)
        else:
            f_night = 1.0
    warm = strength_to_kelvin(night.strength)
    kelvin = round(NEUTRAL_KELVIN - (NEUTRAL_KELVIN - warm) * f_night)

    brightness = 1.0
    if dimmer.enabled:
        if dimmer.profile == "study" or not dimmer.schedule:
            profile = dimmer.profile if dimmer.profile in PROFILES else "day"
            brightness = profile_brightness(dimmer, profile) / 100.0
        else:
            win = resolve_window(dimmer.night_start, dimmer.night_end, dimmer.sun, city, today, tz)
            f = schedule_factor(now_min, win, night.transition_min)
            brightness = (dimmer.day + (dimmer.night - dimmer.day) * f) / 100.0
    return DisplayState(kelvin=kelvin, brightness=max(0.0, min(1.0, brightness)))


def wants_light_theme(cfg: AutoDarkMode, now: time) -> bool | None:
    """True/False for the desired Windows theme, or None when the feature is off."""
    if not cfg.enabled:
        return None
    try:
        light_from, dark_from = parse_hhmm(cfg.light_from), parse_hhmm(cfg.dark_from)
    except ValueError:
        return None
    return in_window(now, light_from, dark_from)
