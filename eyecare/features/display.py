"""Decides the screen colour/brightness and system theme from settings + time."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from eyecare.core.colortemp import NEUTRAL_KELVIN, strength_to_kelvin
from eyecare.core.config import AutoDarkMode, Dimmer, NightLight
from eyecare.core.timeutil import in_window, parse_hhmm

PROFILES = ("day", "night", "study")


@dataclass(frozen=True)
class DisplayState:
    kelvin: int = NEUTRAL_KELVIN
    brightness: float = 1.0

    @property
    def is_neutral(self) -> bool:
        return self.kelvin >= NEUTRAL_KELVIN and self.brightness >= 1.0


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


def compute_display_state(night: NightLight, dimmer: Dimmer, now: time) -> DisplayState:
    kelvin = strength_to_kelvin(night.strength) if night_light_active(night, now) else NEUTRAL_KELVIN
    brightness = 1.0
    if dimmer.enabled:
        brightness = profile_brightness(dimmer, effective_profile(dimmer, now)) / 100.0
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
