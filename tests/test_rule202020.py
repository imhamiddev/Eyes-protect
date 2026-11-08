from eyecare.core.config import Rule202020 as Cfg
from eyecare.features import rule202020 as r


def make(**kw):
    return r.Rule202020(Cfg(interval_min=1, break_seconds=5, snooze_min=1, **kw))


def run(rule, seconds, idle=0.0):
    events = []
    for _ in range(seconds):
        events += rule.tick(1.0, idle)
    return events


def test_prompt_after_interval():
    rule = make()
    assert run(rule, 60) == [r.PROMPT]
    assert rule.phase == r.Phase.PROMPT


def test_full_cycle():
    rule = make()
    run(rule, 60)
    assert rule.start_break() == [r.BREAK_START]
    assert run(rule, 5) == [r.BREAK_DONE]
    assert rule.phase == r.Phase.WORKING and rule.seconds_to_break == 60


def test_snooze_returns_to_working():
    rule = make()
    run(rule, 60)
    assert rule.snooze() == [r.SNOOZED]
    assert rule.phase == r.Phase.WORKING and rule.seconds_to_break == 60


def test_prompt_times_out_into_snooze():
    rule = make()
    run(rule, 60)
    assert r.SNOOZED in run(rule, r.PROMPT_TIMEOUT_SECONDS)
    assert rule.phase == r.Phase.WORKING


def test_break_lock_skips_prompt():
    rule = make(use_break_lock=True)
    assert run(rule, 60) == [r.BREAK_START]
    assert rule.phase == r.Phase.BREAK


def test_skip_break():
    rule = make(use_break_lock=True)
    run(rule, 60)
    assert rule.skip_break() == [r.BREAK_SKIPPED]
    assert rule.phase == r.Phase.WORKING


def test_natural_break_resets_once_and_holds_clock():
    rule = make()
    run(rule, 30)
    assert rule.seconds_to_break == 30
    assert run(rule, 1, idle=6) == [r.NATURAL_BREAK]
    assert rule.seconds_to_break == 60
    assert run(rule, 20, idle=30) == []  # still away
    assert rule.seconds_to_break == 60


def test_natural_break_can_trigger_again_after_return():
    rule = make()
    run(rule, 1, idle=6)
    run(rule, 3, idle=0)
    assert run(rule, 1, idle=6) == [r.NATURAL_BREAK]


def test_natural_break_detection_can_be_disabled():
    rule = make(detect_natural_breaks=False)
    assert run(rule, 1, idle=100) == []


def test_paused_does_nothing():
    rule = make()
    rule.set_paused(True)
    assert run(rule, 120) == []
    assert rule.seconds_to_break == 60


def test_reload_changes_interval():
    rule = make()
    rule.reload(Cfg(interval_min=2, break_seconds=5, snooze_min=1))
    assert rule.seconds_to_break == 120


def test_reload_detects_change_on_shared_settings_object():
    """The UI mutates the live settings object, then calls reload() with it."""
    live = Cfg(interval_min=1, break_seconds=5, snooze_min=1)
    rule = r.Rule202020(live)
    live.interval_min = 3
    rule.reload(live)
    assert rule.seconds_to_break == 180


def test_disabled_rule_never_prompts_or_locks_screen():
    rule = make(enabled=False, use_break_lock=True)
    assert run(rule, 300) == []
    assert rule.phase == r.Phase.WORKING


def test_disabling_cancels_a_pending_prompt():
    rule = make()
    run(rule, 60)
    assert rule.phase == r.Phase.PROMPT
    rule.reload(Cfg(interval_min=1, break_seconds=5, snooze_min=1, enabled=False))
    assert rule.phase == r.Phase.WORKING and run(rule, 120) == []


def test_reenabling_restarts_the_clock():
    rule = make(enabled=False)
    run(rule, 100)
    rule.reload(Cfg(interval_min=1, break_seconds=5, snooze_min=1, enabled=True))
    assert rule.seconds_to_break == 60
    assert run(rule, 60) == [r.PROMPT]


def test_manual_break_still_works_when_disabled():
    rule = make(enabled=False)
    assert rule.start_break() == [r.BREAK_START]
    assert run(rule, 5) == [r.BREAK_DONE]


def test_hold_freezes_clock_and_drops_prompt():
    rule = make()
    for _ in range(30):
        rule.tick(1.0, 0.0, hold=True)
    assert rule.seconds_to_break == 60
    run(rule, 60)
    assert rule.phase == r.Phase.PROMPT
    assert rule.tick(1.0, 0.0, hold=True) == [r.SNOOZED]
    assert rule.phase == r.Phase.WORKING


def test_hold_does_not_interrupt_a_running_break():
    rule = make(use_break_lock=True)
    run(rule, 60)
    assert rule.phase == r.Phase.BREAK
    events = []
    for _ in range(5):
        events += rule.tick(1.0, 0.0, hold=True)
    assert events == [r.BREAK_DONE]
