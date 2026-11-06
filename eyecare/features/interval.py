"""Repeating reminders (blink, hydration)."""
from __future__ import annotations

from eyecare.core.countdown import Countdown

AWAY_AFTER_SECONDS = 90  # don't nag someone who has left the desk


class IntervalReminder:
    def __init__(self, interval_min: int, enabled: bool = True):
        self.enabled = enabled
        self.interval_min = max(1, int(interval_min))
        self.cd = Countdown(self.interval_min * 60)
        self.cd.start()

    def configure(self, interval_min: int, enabled: bool) -> None:
        interval_min = max(1, int(interval_min))
        if interval_min != self.interval_min:
            self.interval_min = interval_min
            self.cd.start(interval_min * 60)
        if enabled and not self.enabled:
            self.cd.start(self.interval_min * 60)
        self.enabled = enabled

    def tick(self, dt: float = 1.0, idle_seconds: float = 0.0, paused: bool = False) -> bool:
        if not self.enabled or paused or idle_seconds >= AWAY_AFTER_SECONDS:
            return False
        if self.cd.tick(dt):
            self.cd.start()
            return True
        return False

    @property
    def seconds_left(self) -> int:
        return self.cd.seconds_left
