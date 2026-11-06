"""Daily usage statistics (breaks taken, water, blinks) persisted as JSON."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .config import config_dir

KINDS = ("breaks", "water", "blinks", "skipped")


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

    def add(self, kind: str, day: date | None = None, amount: int = 1) -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown stat: {kind}")
        key = (day or date.today()).isoformat()
        entry = self.data.setdefault(key, {})
        entry[kind] = entry.get(kind, 0) + amount
        self.save()

    def get(self, kind: str, day: date | None = None) -> int:
        key = (day or date.today()).isoformat()
        return int(self.data.get(key, {}).get(kind, 0))

    def last_days(self, kind: str, days: int = 7, today: date | None = None) -> list[int]:
        today = today or date.today()
        return [self.get(kind, today - timedelta(days=i)) for i in range(days - 1, -1, -1)]
