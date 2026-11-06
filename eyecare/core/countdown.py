"""A pausable, snoozable countdown driven by explicit ticks (easy to test)."""
from __future__ import annotations


class Countdown:
    def __init__(self, duration_seconds: int):
        self.duration = max(1, int(duration_seconds))
        self.remaining = float(self.duration)
        self.running = False

    def start(self, duration_seconds: int | None = None) -> None:
        if duration_seconds is not None:
            self.duration = max(1, int(duration_seconds))
        self.remaining = float(self.duration)
        self.running = True

    def stop(self) -> None:
        self.running = False

    def pause(self) -> None:
        self.running = False

    def resume(self) -> None:
        self.running = True

    def reset(self) -> None:
        self.remaining = float(self.duration)

    def snooze(self, seconds: int) -> None:
        self.remaining = float(max(1, int(seconds)))
        self.running = True

    @property
    def progress(self) -> float:
        """0.0 right after a reset, 1.0 when finished."""
        return 1.0 - max(0.0, min(1.0, self.remaining / self.duration))

    @property
    def seconds_left(self) -> int:
        return max(0, int(self.remaining + 0.999))

    def tick(self, dt: float = 1.0) -> bool:
        """Advance time; returns True exactly once, when the countdown elapses."""
        if not self.running:
            return False
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0.0
            self.running = False
            return True
        return False
