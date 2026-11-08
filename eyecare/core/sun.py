"""Sunrise/sunset from latitude/longitude (NOAA solar-position equations)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SunTimes:
    sunrise: float | None   # minutes after local midnight
    sunset: float | None
    polar: str | None       # "day" (sun never sets), "night" (never rises) or None


def sun_times(day: date, lat: float, lon: float, utc_offset_hours: float) -> SunTimes:
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat_r = math.radians(lat)
    cos_ha = (math.cos(math.radians(90.833)) / (math.cos(lat_r) * math.cos(decl))
              - math.tan(lat_r) * math.tan(decl))
    if cos_ha > 1:
        return SunTimes(None, None, "night")
    if cos_ha < -1:
        return SunTimes(None, None, "day")
    ha = math.degrees(math.acos(cos_ha))
    offset = utc_offset_hours * 60
    sunrise = 720 - 4 * (lon + ha) - eqtime + offset
    sunset = 720 - 4 * (lon - ha) - eqtime + offset
    return SunTimes(sunrise % 1440, sunset % 1440, None)


def format_minutes(minutes: float) -> str:
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"
