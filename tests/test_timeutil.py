from datetime import time

import pytest

from eyecare.core.timeutil import format_mmss, in_window, parse_hhmm


def test_parse_hhmm():
    assert parse_hhmm("07:05") == time(7, 5)
    assert parse_hhmm(" 23:59 ") == time(23, 59)


def test_parse_hhmm_invalid():
    with pytest.raises(ValueError):
        parse_hhmm("nope")


def test_window_same_day():
    assert in_window(time(10), time(9), time(17))
    assert not in_window(time(17), time(9), time(17))
    assert not in_window(time(8, 59), time(9), time(17))


def test_window_wraps_midnight():
    assert in_window(time(23), time(20), time(6))
    assert in_window(time(3), time(20), time(6))
    assert not in_window(time(12), time(20), time(6))


def test_empty_window():
    assert not in_window(time(12), time(8), time(8))


def test_format_mmss():
    assert format_mmss(0) == "00:00"
    assert format_mmss(75) == "01:15"
    assert format_mmss(-5) == "00:00"


def test_format_duration():
    from eyecare.core.timeutil import format_duration

    assert format_duration(0) == "0 min" and format_duration(59) == "0 min"
    assert format_duration(48 * 60) == "48 min"
    assert format_duration(3 * 3600 + 25 * 60) == "3 h 25 min"
    assert format_duration(2 * 3600) == "2 h"
    assert format_duration(90, "ساعت", "دقیقه") == "1 دقیقه"
    assert format_duration(-5) == "0 min"
