from eyecare.features.interval import IntervalReminder


def fire_count(rem, seconds, **kw):
    return sum(rem.tick(1.0, **kw) for _ in range(seconds))


def test_fires_every_interval():
    rem = IntervalReminder(1)
    assert fire_count(rem, 180) == 3


def test_disabled_never_fires():
    assert fire_count(IntervalReminder(1, enabled=False), 600) == 0


def test_paused_and_away_hold_the_clock():
    rem = IntervalReminder(1)
    assert fire_count(rem, 120, paused=True) == 0
    assert fire_count(rem, 120, idle_seconds=500) == 0
    assert rem.seconds_left == 60


def test_enabling_restarts_clock():
    rem = IntervalReminder(1, enabled=False)
    rem.configure(1, True)
    assert rem.seconds_left == 60 and rem.enabled


def test_interval_change_restarts():
    rem = IntervalReminder(1)
    rem.configure(3, True)
    assert rem.seconds_left == 180
