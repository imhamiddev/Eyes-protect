"""Daily usage statistics (breaks taken, water, blinks) persisted as JSON."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .config import config_dir

KINDS = ("breaks", "water", "blinks", "skipped", "active_s", "longest_run_s", "stretches")


class Stats:
    def __init__(self, path: Path | None = None):
        self.path = path or config_dir() / "stats.json"
        self.data: dict[str, dict[str, int]] = {}
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            self.data = {}

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data), encoding="utf-8")
        except OSError:
            pass

    def add(self, kind: str, day: date | None = None, amount: int = 1, save: bool = True) -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown stat: {kind}")
        key = (day or date.today()).isoformat()
        entry = self.data.setdefault(key, {})
        entry[kind] = entry.get(kind, 0) + amount
        if save:
            self.save()

    def record_max(self, kind: str, value: int, day: date | None = None, save: bool = True) -> None:
        """Keep the largest value seen for the day (e.g. the longest stretch without a break)."""
        if kind not in KINDS:
            raise ValueError(f"unknown stat: {kind}")
        entry = self.data.setdefault((day or date.today()).isoformat(), {})
        if value > entry.get(kind, 0):
            entry[kind] = int(value)
            if save:
                self.save()

    def get(self, kind: str, day: date | None = None) -> int:
        key = (day or date.today()).isoformat()
        return int(self.data.get(key, {}).get(kind, 0))

    def last_days(self, kind: str, days: int = 7, today: date | None = None) -> list[int]:
        today = today or date.today()
        return [self.get(kind, today - timedelta(days=i)) for i in range(days - 1, -1, -1)]

    def streak(self, goal: int, today: date | None = None) -> int:
        """Consecutive days with at least ``goal`` breaks. A day still in progress never breaks it."""
        today = today or date.today()
        day = today if self.get("breaks", today) >= goal else today - timedelta(days=1)
        count = 0
        while self.get("breaks", day) >= goal > 0:
            count += 1
            day -= timedelta(days=1)
        return count

    def week_summary(self, today: date | None = None) -> dict:
        today = today or date.today()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        breaks = [self.get("breaks", d) for d in days]
        active = [self.get("active_s", d) for d in days]
        best = max(range(7), key=lambda i: (breaks[i], i)) if any(breaks) else None
        return {
            "breaks": sum(breaks),
            "active_s": sum(active),
            "avg_active_s": sum(active) // 7,
            "best_day": days[best] if best is not None else None,
            "best_day_breaks": breaks[best] if best is not None else 0,
            "longest_run_s": max((self.get("longest_run_s", d) for d in days), default=0),
            "water": sum(self.get("water", d) for d in days),
            "stretches": sum(self.get("stretches", d) for d in days),
        }
