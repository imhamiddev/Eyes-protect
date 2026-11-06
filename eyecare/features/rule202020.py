"""20-20-20 rule state machine (pure logic, no Qt)."""
from __future__ import annotations

from enum import Enum

from eyecare.core.config import Rule202020 as Rule202020Settings
from eyecare.core.countdown import Countdown

PROMPT_TIMEOUT_SECONDS = 30

# Events returned from tick()/actions
PROMPT = "prompt"
BREAK_START = "break_start"
BREAK_DONE = "break_done"
BREAK_SKIPPED = "break_skipped"
NATURAL_BREAK = "natural_break"
SNOOZED = "snoozed"


class Phase(Enum):
    WORKING = "working"
    PROMPT = "prompt"
    BREAK = "break"


class Rule202020:
    def __init__(self, cfg: Rule202020Settings):
        self.cfg = cfg
        self.phase = Phase.WORKING
        self.paused = False
        self.work = Countdown(cfg.interval_min * 60)
        self.work.start()
        self.rest = Countdown(cfg.break_seconds)
        self.prompt_left = 0.0
        self._idle_credited = False

    # -- configuration ----------------------------------------------------
    def reload(self, cfg: Rule202020Settings) -> None:
        old = self.cfg
        self.cfg = cfg
        if cfg.interval_min != old.interval_min:
            self.work.start(cfg.interval_min * 60)
            self.work.running = self.phase == Phase.WORKING
        if cfg.break_seconds != old.break_seconds:
            self.rest.duration = max(1, cfg.break_seconds)

    # -- queries ----------------------------------------------------------
    @property
    def seconds_to_break(self) -> int:
        return self.work.seconds_left

    @property
    def break_seconds_left(self) -> int:
        return self.rest.seconds_left

    @property
    def work_progress(self) -> float:
        return self.work.progress

    # -- actions ----------------------------------------------------------
    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def start_break(self) -> list[str]:
        self.phase = Phase.BREAK
        self.rest.start(self.cfg.break_seconds)
        return [BREAK_START]

    def snooze(self) -> list[str]:
        self.phase = Phase.WORKING
        self.work.snooze(self.cfg.snooze_min * 60)
        return [SNOOZED]

    def skip_break(self) -> list[str]:
        self._back_to_work()
        return [BREAK_SKIPPED]

    def _back_to_work(self) -> None:
        self.phase = Phase.WORKING
        self.rest.stop()
        self.work.start(self.cfg.interval_min * 60)

    # -- time -------------------------------------------------------------
    def tick(self, dt: float = 1.0, idle_seconds: float = 0.0) -> list[str]:
        if self.paused:
            return []
        if self.phase == Phase.WORKING:
            return self._tick_working(dt, idle_seconds)
        if self.phase == Phase.PROMPT:
            self.prompt_left -= dt
            if self.prompt_left <= 0:
                return self.snooze()
            return []
        if self.rest.tick(dt):
            self._back_to_work()
            return [BREAK_DONE]
        return []

    def _tick_working(self, dt: float, idle: float) -> list[str]:
        if self.cfg.detect_natural_breaks and idle >= self.cfg.break_seconds:
            if not self._idle_credited:
                self._idle_credited = True
                self.work.start(self.cfg.interval_min * 60)
                return [NATURAL_BREAK]
            return []  # still away: the clock is held at full
        if idle < 2:
            self._idle_credited = False
        if not self.work.tick(dt):
            return []
        if self.cfg.use_break_lock:
            return self.start_break()
        self.phase = Phase.PROMPT
        self.prompt_left = PROMPT_TIMEOUT_SECONDS
        return [PROMPT]
