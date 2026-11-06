from eyecare.core.countdown import Countdown


def test_fires_once():
    c = Countdown(3)
    c.start()
    assert [c.tick(), c.tick(), c.tick(), c.tick()] == [False, False, True, False]


def test_pause_blocks_ticks():
    c = Countdown(2)
    c.start()
    c.pause()
    assert not c.tick(5)
    assert c.seconds_left == 2
    c.resume()
    assert c.tick(5)


def test_snooze_restarts_with_new_length():
    c = Countdown(60)
    c.start()
    c.tick(59)
    c.snooze(10)
    assert c.seconds_left == 10 and c.running


def test_progress():
    c = Countdown(10)
    c.start()
    assert c.progress == 0
    c.tick(5)
    assert abs(c.progress - 0.5) < 1e-9
    c.tick(5)
    assert c.progress == 1


def test_restart_with_duration():
    c = Countdown(5)
    c.start(20)
    assert c.seconds_left == 20
