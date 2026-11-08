"""Small, dependency-free helpers for working with times of day."""
from __future__ import annotations

from datetime import datetime, time


def parse_hhmm(value: str) -> time:
    """Parse ``"HH:MM"`` into a :class:`datetime.time` (raises ValueError)."""
    hours, minutes = value.strip().split(":")
    return time(int(hours), int(minutes))


def format_hhmm(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def minutes_of_day(value: time) -> int:
    return value.hour * 60 + value.minute


def in_window(now: time, start: time, end: time) -> bool:
    """True when ``now`` is inside [start, end). Windows may wrap past midnight."""
    n, s, e = minutes_of_day(now), minutes_of_day(start), minutes_of_day(end)
    if s == e:
        return False
    if s < e:
        return s <= n < e
    return n >= s or n < e


def now_time() -> time:
    return datetime.now().time().replace(second=0, microsecond=0)


def format_mmss(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def now_precise() -> time:
    """Current local time including seconds (for smooth schedule fades)."""
    return datetime.now().time().replace(microsecond=0)


def minutes_precise(value: time) -> float:
    return value.hour * 60 + value.minute + value.second / 60


def format_duration(total_seconds: int, hour_unit: str = "h", minute_unit: str = "min") -> str:
    """'3 h 25 min', '48 min', '0 min' (seconds are dropped)."""
    minutes = max(0, int(total_seconds)) // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} {hour_unit} {minutes} {minute_unit}" if minutes else f"{hours} {hour_unit}"
    return f"{minutes} {minute_unit}"
