from datetime import date, timedelta

import pytest

from eyecare.core.stats import Stats


def test_add_and_get(tmp_path):
    s = Stats(tmp_path / "st.json")
    s.add("breaks")
    s.add("breaks")
    s.add("water", amount=3)
    assert s.get("breaks") == 2 and s.get("water") == 3 and s.get("blinks") == 0


def test_persists(tmp_path):
    p = tmp_path / "st.json"
    Stats(p).add("blinks")
    assert Stats(p).get("blinks") == 1


def test_last_days_order(tmp_path):
    s = Stats(tmp_path / "st.json")
    today = date(2026, 11, 6)
    s.add("breaks", today, 4)
    s.add("breaks", today - timedelta(days=2), 1)
    assert s.last_days("breaks", 3, today) == [1, 0, 4]


def test_unknown_kind(tmp_path):
    with pytest.raises(ValueError):
        Stats(tmp_path / "st.json").add("coffee")
