from datetime import date

import pytest

from eyecare.core.cities import CITIES, city_by_key, city_name
from eyecare.core.sun import format_minutes, sun_times


def hm(h, m):
    return h * 60 + m


def close(a, b, tol=8):
    return abs(((a - b + 720) % 1440) - 720) <= tol


def test_tehran_summer_and_winter():
    s = sun_times(date(2024, 6, 21), 35.6892, 51.3890, 3.5)
    # Iran has used a fixed UTC+3:30 since 2022 (no daylight saving)
    assert close(s.sunrise, hm(4, 48)) and close(s.sunset, hm(19, 25))
    w = sun_times(date(2024, 12, 21), 35.6892, 51.3890, 3.5)
    assert close(w.sunrise, hm(7, 12)) and close(w.sunset, hm(16, 55))
    assert w.sunset < s.sunset


def test_london_equinox_is_about_twelve_hours():
    s = sun_times(date(2024, 3, 20), 51.5072, -0.1276, 0)
    assert close(s.sunrise, hm(6, 0), 15) and close(s.sunset, hm(18, 12), 15)


def test_equator_is_always_about_twelve_hours():
    for d in (date(2024, 3, 1), date(2024, 9, 1)):
        s = sun_times(d, 0.0, 0.0, 0)
        assert 11.9 * 60 < (s.sunset - s.sunrise) < 12.3 * 60


def test_polar_day_and_night():
    assert sun_times(date(2024, 6, 21), 69.65, 18.96, 2).polar == "day"
    assert sun_times(date(2024, 12, 21), 69.65, 18.96, 1).polar == "night"
    assert sun_times(date(2024, 6, 21), 69.65, 18.96, 2).sunrise is None


def test_southern_hemisphere_flips_seasons():
    dec = sun_times(date(2024, 12, 21), -33.87, 151.21, 11)
    jun = sun_times(date(2024, 6, 21), -33.87, 151.21, 10)
    assert dec.sunset - dec.sunrise > jun.sunset - jun.sunrise


def test_format_minutes_wraps():
    assert format_minutes(hm(17, 8)) == "17:08"
    assert format_minutes(1440 + 5) == "00:05"


def test_cities_are_unique_and_sane():
    keys = [c.key for c in CITIES]
    assert len(keys) == len(set(keys)) and "tehran" in keys
    assert all(-90 <= c.lat <= 90 and -180 <= c.lon <= 180 and c.fa and c.en for c in CITIES)
    assert city_by_key("nope").key == "tehran"
    assert city_name(city_by_key("tehran"), "fa") == "تهران"
    assert city_name(city_by_key("tehran"), "en") == "Tehran"
