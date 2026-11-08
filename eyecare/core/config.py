"""Typed, JSON-backed application settings."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, get_type_hints


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".config")
    path = Path(base) / "EyeCare"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class General:
    theme: str = "dark"  # dark | light | system
    language: str = "en"  # en | fa
    autostart: bool = True
    start_minimized: bool = True
    animations: bool = True
    auto_update: bool = True
    last_update_check: float = 0.0
    daily_break_goal: int = 6


@dataclass
class Rule202020:
    enabled: bool = True
    interval_min: int = 20
    break_seconds: int = 20
    snooze_min: int = 5
    detect_natural_breaks: bool = True
    use_break_lock: bool = False


@dataclass
class Blink:
    enabled: bool = True
    interval_min: int = 5


@dataclass
class Hydration:
    enabled: bool = True
    interval_min: int = 45


@dataclass
class Posture:
    enabled: bool = True
    interval_min: int = 45


@dataclass
class NightLight:
    enabled: bool = False
    strength: int = 40  # 0..100 warmth
    schedule: bool = True
    start: str = "20:00"
    end: str = "06:30"
    sun: bool = False            # follow sunset/sunrise of the chosen city instead of fixed times
    transition_min: int = 30     # gradual fade in/out at the edges of the schedule


@dataclass
class Dimmer:
    enabled: bool = False
    profile: str = "day"  # day | night | study
    day: int = 100
    night: int = 70
    study: int = 85
    schedule: bool = True
    night_start: str = "20:00"
    night_end: str = "06:30"
    sun: bool = False


@dataclass
class AutoDarkMode:
    enabled: bool = False
    light_from: str = "07:00"
    dark_from: str = "19:00"


@dataclass
class BreakLock:
    skippable: bool = True
    skip_after_seconds: int = 3
    show_exercise: bool = True


@dataclass
class SmartPause:
    enabled: bool = True
    fullscreen: bool = True      # full-screen apps, games, presentations
    meetings: bool = True        # Zoom / Teams / Meet / Webex ...
    focus_assist: bool = True    # respect Windows Focus assist (quiet hours)


@dataclass
class Monitors:
    excluded: str = ""       # comma-separated monitor keys the filters should NOT touch
    brightness: str = ""     # 'DISPLAY1=80;DISPLAY2=100' per-monitor brightness multiplier (%)


@dataclass
class Hotkeys:
    enabled: bool = True
    night_light: str = "Ctrl+Alt+N"
    break_now: str = "Ctrl+Alt+B"
    pause: str = "Ctrl+Alt+P"
    quiet: str = "Ctrl+Alt+Q"


@dataclass
class Location:
    city: str = "tehran"


@dataclass
class Settings:
    general: General = field(default_factory=General)
    rule202020: Rule202020 = field(default_factory=Rule202020)
    blink: Blink = field(default_factory=Blink)
    hydration: Hydration = field(default_factory=Hydration)
    posture: Posture = field(default_factory=Posture)
    night_light: NightLight = field(default_factory=NightLight)
    dimmer: Dimmer = field(default_factory=Dimmer)
    auto_dark: AutoDarkMode = field(default_factory=AutoDarkMode)
    break_lock: BreakLock = field(default_factory=BreakLock)
    smart_pause: SmartPause = field(default_factory=SmartPause)
    location: Location = field(default_factory=Location)
    monitors: Monitors = field(default_factory=Monitors)
    hotkeys: Hotkeys = field(default_factory=Hotkeys)


def _merge(target: Any, data: dict) -> None:
    """Copy known keys from ``data`` into the dataclass, ignoring junk."""
    hints = get_type_hints(type(target))
    for f in fields(target):
        if f.name not in data:
            continue
        current = getattr(target, f.name)
        value = data[f.name]
        if is_dataclass(current) and isinstance(value, dict):
            _merge(current, value)
        elif hints[f.name] is float and isinstance(value, int) and not isinstance(value, bool):
            setattr(target, f.name, float(value))
        elif isinstance(value, hints[f.name]) and not (
            hints[f.name] in (int, float) and isinstance(value, bool)
        ):
            setattr(target, f.name, value)


def settings_from_dict(data: dict) -> Settings:
    settings = Settings()
    if isinstance(data, dict):
        _merge(settings, data)
    return settings


def load_settings(path: Path | None = None) -> Settings:
    path = path or config_dir() / "settings.json"
    try:
        return settings_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Settings()


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or config_dir() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(settings), indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
