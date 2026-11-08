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


def test_record_max_keeps_the_largest(tmp_path):
    s = Stats(tmp_path / "st.json")
    s.record_max("longest_run_s", 300)
    s.record_max("longest_run_s", 120)
    s.record_max("longest_run_s", 900)
    assert s.get("longest_run_s") == 900
    with pytest.raises(ValueError):
        s.record_max("nope", 1)


def test_deferred_save_writes_nothing_until_saved(tmp_path):
    p = tmp_path / "st.json"
    s = Stats(p)
    s.add("active_s", save=False)
    assert not p.exists()
    s.save()
    assert Stats(p).get("active_s") == 1


def test_streak_counts_consecutive_goal_days(tmp_path):
    s = Stats(tmp_path / "st.json")
    today = date(2026, 11, 8)
    for back in (1, 2, 3):
        s.add("breaks", today - timedelta(days=back), 6)
    assert s.streak(6, today) == 3             # today unfinished: streak not broken
    s.add("breaks", today, 6)
    assert s.streak(6, today) == 4             # today reached the goal: it counts
    s.data.pop((today - timedelta(days=2)).isoformat())
    assert s.streak(6, today) == 2             # a missed day ends it


def test_streak_zero_goal_and_empty(tmp_path):
    s = Stats(tmp_path / "st.json")
    assert s.streak(6, date(2026, 1, 1)) == 0
    assert s.streak(0, date(2026, 1, 1)) == 0


def test_week_summary(tmp_path):
    s = Stats(tmp_path / "st.json")
    today = date(2026, 11, 8)
    s.add("breaks", today, 5)
    s.add("breaks", today - timedelta(days=2), 9)
    s.add("active_s", today, 7 * 3600)
    s.add("water", today - timedelta(days=1), 4)
    s.record_max("longest_run_s", 4000, today - timedelta(days=3))
    w = s.week_summary(today)
    assert w["breaks"] == 14 and w["active_s"] == 7 * 3600 and w["avg_active_s"] == 3600
    assert w["best_day"] == today - timedelta(days=2) and w["best_day_breaks"] == 9
    assert w["longest_run_s"] == 4000 and w["water"] == 4
    assert s.week_summary(date(2020, 1, 1))["best_day"] is None
